"""곡별 영구 오디오 링크 (카드 t571, SPEC-LDBEAT-001 REQ-LDBEAT-024(c) 후속).

``ChatSession._song_audio`` (``server/web/session.py``)는 **세션 하나**의
수명을 산다 — 서버/앱이 재시작되면 운영자가 같은 곡을 다시 올려야 했다. 이
저장소는 ``PinStore``·``SongTimelineStore``·``SongTimelineLibrary`` 와 같은
형태로 그 오디오 바이트 자체를 재시작 사이에도 남긴다.

설계:

- **곡 열쇠**는 새 id 체계를 짓지 않는다 — ``ChatSession._beat_grid_song_key``
  가 이미 두 곡을 가르는 데 쓰는 ``(song_title, sequence_number)`` 쌍 그대로다.
- **내용 주소화**(content-addressed): 파일은 ``sha256(bytes) + 원본 확장자``
  이름으로 저장된다. 같은 바이트가 다시 올라오면(다른 곡이든 같은 곡
  재업로드든) 이미 있는 파일을 건드리지 않는다 — 디스크에 중복이 쌓이지
  않고, 쓰기 자체가 멱등이다.
- **색인**은 "이 곡 → 어느 sha256·파일 이름·MIME" 매핑만 담는 작은 JSON
  리스트다(``SongTimelineLibrary`` 의 엔트리 리스트와 같은 모양) — 조회가
  디코드 하나 없이 끝난다.
- **원자적 쓰기**: 색인·오디오 파일 둘 다 "같은 디렉터리 임시 파일 +
  ``os.replace``" (``PinStore._save`` 가 세운 관례) — 중간에 죽어도 이전
  파일이 그대로 남는다.
- **fail-open 읽기**: 색인이 깨졌거나 가리키는 파일이 없거나 해시가 안
  맞으면 예외 대신 ``SongAudioLinkResult(status="missing")`` 를 돌려준다 —
  이 링크를 잃어도 콘솔에는 아무 영향이 없다(읽기 전용 편의 기능).
- **경로 없는 인스턴스는 메모리 전용**(시험·``WebDeps`` 기본값) — 다른
  저장소들과 같은 관례.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["UNBOUND_SONG_KEY", "SongAudioLinkResult", "SongAudioLinkStore"]

#: 아직 곡 작업본이 없는 업로드(새 곡을 올렸고 분석 전)를 보관하는 열쇠. 분석이 새 작업본을
#: 열면 그 곡 열쇠로 다시 묶고, 그 전에도 해시(``resolve_sha``)로 찾을 수 있다
#: (카드 WT-audio-other-browser).
UNBOUND_SONG_KEY: tuple[object, object] = (None, "unbound-upload")

_INDEX_FILE_VERSION = 1
# 색인 파일 바로 곁에 두는 오디오 보관 디렉터리 이름. ``pin_store_path`` 가
# 돌려주는 경로(사용자 데이터 디렉터리 안)의 형제 디렉터리라, 색인 하나의
# 경로만 알면 둘 다 안다 — 생성자 인자를 하나로 유지하는 이유.
_FILES_DIRNAME = "song_audio_files"


@dataclass(frozen=True)
class SongAudioLinkResult:
    """``resolve`` 의 응답 — 셋 중 정확히 하나.

    ``status``:
    - ``"none"``: 이 곡에 대해 저장된 링크가 아예 없다(한 번도 안 올렸음).
    - ``"missing"``: 색인에는 링크가 있는데 파일이 없거나 해시가 안 맞는다
      — 디스크가 사람 손이나 다른 과정으로 건드려진 경우. ``record`` 는
      색인이 기억하는 메타데이터(파일 이름 등)를 그대로 담아, 호출자가
      "무엇이 없어졌는지"는 말할 수 있게 한다.
    - ``"found"``: 링크가 있고 파일도 있고 해시도 맞는다. ``data`` 에 실제
      바이트가 담긴다.
    """

    status: str
    record: dict | None = None
    data: bytes | None = None


class SongAudioLinkStore:
    """곡별(``song_title``, ``sequence_number``) 영구 오디오 링크.

    ``PinStore``/``SongTimelineLibrary`` 와 같은 생성자 관례: ``path`` 가
    색인 JSON 파일을 가리키고, 오디오 바이트는 그 옆 ``song_audio_files/``
    디렉터리에 내용 주소화로 쌓인다. ``path`` 가 ``None`` 이면(시험,
    ``WebDeps`` 기본값) 색인과 바이트 전부 메모리에만 머문다 — 디스크를
    건드리지 않는다.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._index_path = Path(path) if path is not None else None
        self._files_dir = (
            self._index_path.parent / _FILES_DIRNAME if self._index_path is not None else None
        )
        # 메모리 전용 모드(``_index_path is None``)의 오디오 바이트 보관처.
        # sha256 로 키를 잡아 디스크 모드와 같은 내용-주소화 중복 제거를
        # 메모리에서도 그대로 재현한다.
        self._memory_blobs: dict[str, bytes] = {}
        self._entries: list[dict] = self._load_index()

    # -- reads -------------------------------------------------------------

    @property
    def path(self) -> Path | None:
        return self._index_path

    def resolve(self, song_key: tuple[object, object]) -> SongAudioLinkResult:
        """``song_key`` 에 저장된 링크를 찾아 바이트까지 읽어 돌려준다."""
        entry = self._find(song_key)
        if entry is None:
            return SongAudioLinkResult(status="none")
        return self._resolve_entry(entry)

    def resolve_sha(self, sha256: str) -> SongAudioLinkResult:
        """바이트 해시로 보관된 음원을 찾는다 — 어느 곡 열쇠에 묶였든 상관없다(가장 최근 기록부터).

        카드 WT-audio-other-browser — 분석한 곡은 작업본이 그 음원의 해시를 들고 있다. 업로드가
        엉뚱한 곡 열쇠에 묶였어도(새 곡을 올릴 때 열려 있던 앞 곡) 해시로 바른 음원을 찾는다.
        """
        found = SongAudioLinkResult(status="none")
        for entry in reversed(self._entries):
            if entry.get("sha256") != sha256:
                continue
            found = self._resolve_entry(entry)
            if found.status == "found":
                return found
        return found

    def _resolve_entry(self, entry: dict) -> SongAudioLinkResult:
        sha256 = entry.get("sha256")
        data = self._read_blob(sha256, str(entry.get("file_name", "")))
        if data is None:
            return SongAudioLinkResult(status="missing", record=dict(entry))
        # 디스크(또는 메모리)의 바이트가 색인이 기억하는 해시와 실제로
        # 일치하는지 다시 잰다 — 색인은 믿어도 그 자리의 파일이 다른 과정에
        # 의해 바뀌었을 수 있다(사람 손, 디스크 정리 등).
        if hashlib.sha256(data).hexdigest() != sha256:
            return SongAudioLinkResult(status="missing", record=dict(entry))
        return SongAudioLinkResult(status="found", record=dict(entry), data=data)

    # -- writes --------------------------------------------------------------

    def link(
        self,
        song_key: tuple[object, object],
        *,
        file_name: str,
        mime_type: str,
        data: bytes,
    ) -> dict:
        """``song_key`` 의 링크를 ``data`` 로 (교체하며) 저장한다.

        이 곡에 이미 링크가 있으면 색인에서 그 엔트리를 빼고 새 것을
        붙인다 — ``SongTimelineLibrary`` 가 아니라 "이 곡은 링크 하나만
        가진다"는 ``PinStore`` 류의 wholesale-replace 규약이다(여러 버전을
        쌓는 라이브러리가 아니다).
        """
        sha256 = hashlib.sha256(data).hexdigest()
        self._write_blob(sha256, file_name, data)
        record = {
            "song_title": song_key[0],
            "sequence_number": song_key[1],
            "file_name": file_name,
            "mime_type": mime_type,
            "sha256": sha256,
            "byte_length": len(data),
            "saved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        entries = [e for e in self._entries if self._entry_song_key(e) != tuple(song_key)]
        entries.append(record)
        self._persist_index(entries)
        self._entries = entries  # 파일 교체가 끝난 뒤에만 커밋한다
        return dict(record)

    # -- internals -------------------------------------------------------------

    @staticmethod
    def _entry_song_key(entry: dict) -> tuple[object, object]:
        return (entry.get("song_title"), entry.get("sequence_number"))

    def _find(self, song_key: tuple[object, object]) -> dict | None:
        target = tuple(song_key)
        for entry in self._entries:
            if self._entry_song_key(entry) == target:
                return entry
        return None

    @staticmethod
    def _blob_suffix(file_name: str) -> str:
        return Path(file_name).suffix.lower()

    def _blob_path(self, sha256: str, file_name: str) -> Path:
        assert self._files_dir is not None  # 호출부가 디스크 모드에서만 부른다
        return self._files_dir / f"{sha256}{self._blob_suffix(file_name)}"

    def _write_blob(self, sha256: str, file_name: str, data: bytes) -> None:
        if self._files_dir is None:
            # 메모리 전용 — 내용 주소화 중복 제거를 그대로 재현한다(이미
            # 있는 sha256 이면 다시 쓰지 않는다. bytes 는 불변이라 "다시
            # 쓴다"와 "그대로 둔다"의 결과가 같지만, 아래 디스크 분기와
            # 같은 모양을 유지해 두 분기가 같은 계약을 진다는 것을
            # 분명히 한다).
            if sha256 not in self._memory_blobs:
                self._memory_blobs[sha256] = data
            return
        blob_path = self._blob_path(sha256, file_name)
        if blob_path.exists():
            # 내용 주소화 중복 제거 — 같은 바이트가 이미 디스크에 있으면
            # 다시 쓰지 않는다(임시 파일조차 만들지 않는다). 손상된
            # 파일을 "고쳐 쓰기"로 되살리지도 않는다 — 그건 ``resolve``가
            # 해시 불일치로 정직하게 ``missing`` 을 내는 것이 맞다.
            return
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(blob_path.parent), prefix=".song-audio-blob-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp_name, blob_path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise

    def _read_blob(self, sha256: object, file_name: str) -> bytes | None:
        if not isinstance(sha256, str) or not sha256:
            return None
        if self._files_dir is None:
            return self._memory_blobs.get(sha256)
        blob_path = self._blob_path(sha256, file_name)
        try:
            return blob_path.read_bytes()
        except OSError:
            return None

    def _load_index(self) -> list[dict]:
        if self._index_path is None:
            return []
        try:
            raw = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(raw, dict):
            return []
        entries = raw.get("entries")
        if not isinstance(entries, list):
            return []
        kept: list[dict] = []
        for entry in entries:
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("file_name"), str)
                and isinstance(entry.get("mime_type"), str)
                and isinstance(entry.get("sha256"), str)
                and isinstance(entry.get("byte_length"), int)
            ):
                kept.append(entry)
        return kept

    def _persist_index(self, entries: list[dict]) -> None:
        if self._index_path is None:
            return
        body = json.dumps({"version": _INDEX_FILE_VERSION, "entries": entries}, ensure_ascii=False)
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self._index_path.parent), prefix=".song-audio-index-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(body)
            os.replace(tmp_name, self._index_path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise
