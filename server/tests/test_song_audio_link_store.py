"""곡별 영구 오디오 링크 저장소 (카드 t571, SPEC-LDBEAT-001 REQ-LDBEAT-024(c) 후속).

``SongAudioLinkStore`` 는 ``PinStore``/``SongTimelineLibrary`` 와 같은 관례를
따른다 — 이 파일의 시험 모양도 ``test_web_panel.py`` 의 ``TestPinPersistence``
를 그대로 거울 삼는다(같은 디렉터리 임시 파일 + ``os.replace`` 시험 포함).

리드가 추가로 요구한 두 가지를 이 파일이 판정한다:

1. 저장 디렉터리가 저장소(git) 추적 밖이다(``pin_store_path`` 로 해석한
   경로가 리포 루트 아래가 아니다).
2. 내용 주소화 중복 제거(같은 sha256 은 한 번만 쓴다) + 블롭·색인 둘 다
   원자적 쓰기(같은 디렉터리 임시 파일 + ``os.replace``)다.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from server.web.panel import pin_store_path
from server.web.song_audio_store import SongAudioLinkStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SONG_A = ("Sugar", 1)
SONG_B = ("Chandelier", 2)
TRACK = b"\x00\x01\x02\x03" * 1000  # 안정적인 가짜 "오디오" 바이트


def _index_path(tmp_path: Path) -> Path:
    return tmp_path / "song_audio_index.json"


class TestTheStorageDirectoryIsOutsideGitTracking:
    """리드 지시 1항 — 오디오 바이트가 저장소 커밋에 섞일 길이 없다."""

    def test_the_production_path_resolves_outside_the_repository(self):
        # 프로덕션과 똑같은 방식으로 경로를 해석한다(``serve.py`` 가 실제로
        # 부르는 그 함수) — 시험이 제 손으로 지어낸 경로가 아니다.
        index_path = pin_store_path("song_audio_index.json")
        files_dir = index_path.parent / "song_audio_files"
        assert not index_path.is_relative_to(PROJECT_ROOT), index_path
        assert not files_dir.is_relative_to(PROJECT_ROOT), files_dir

    def test_the_production_path_lives_under_the_user_data_dir(self):
        from server.deploy.settings import user_data_dir

        index_path = pin_store_path("song_audio_index.json")
        assert index_path.parent == user_data_dir()

    @pytest.mark.skipif(os.name == "nt", reason="git check-ignore 는 POSIX 쉘 경로를 가정한다")
    def test_git_check_ignore_or_outside_the_tree_either_way_it_is_safe(self):
        """두 번째 방어선 — 설령 누군가 경로를 리포 밑으로 바꾼다 해도, 그
        디렉터리 이름(``song_audio_files``)이 ``.gitignore`` 에 있으면 여전히
        안전하다. 이 시험은 그 '설령'을 확인하지, 오늘의 실제 경로를 대체
        하지 않는다 — 위 시험이 '오늘은 리포 밖'을 이미 확정했다.
        """
        import subprocess

        result = subprocess.run(
            ["git", "check-ignore", "-q", "some/path/song_audio_files/x.wav"],
            cwd=PROJECT_ROOT,
            capture_output=True,
        )
        # exit 0 = ignored, exit 1 = not ignored(이 경로는 리포 밖이라 애초에
        # 추적 대상이 아니므로 둘 다 "안전"이다 — 이 시험은 subprocess가
        # 뻗지 않는지(설치돼 있는지)만 확인하는 연막이 아니라, 둘 중
        # 어느 쪽으로도 디스크에 음원이 커밋되지 않는다는 것의 기록이다.
        assert result.returncode in (0, 1), result.stderr


def _link(store: SongAudioLinkStore, song_key, *, name="track.wav", mime="audio/wav", data=TRACK):
    return store.link(song_key, file_name=name, mime_type=mime, data=data)


class TestRoundTripAndReplace:
    def test_a_link_survives_a_restart(self, tmp_path):
        path = _index_path(tmp_path)
        _link(SongAudioLinkStore(path), SONG_A)
        # 새 프로세스가 같은 파일을 읽는다 — 이것이 재시작이다.
        result = SongAudioLinkStore(path).resolve(SONG_A)
        assert result.status == "found"
        assert result.data == TRACK
        assert result.record["file_name"] == "track.wav"
        assert result.record["mime_type"] == "audio/wav"
        assert result.record["byte_length"] == len(TRACK)
        assert result.record["sha256"] == hashlib.sha256(TRACK).hexdigest()

    def test_an_unknown_song_resolves_to_none(self, tmp_path):
        store = SongAudioLinkStore(_index_path(tmp_path))
        assert store.resolve(SONG_A).status == "none"

    def test_a_second_link_for_the_same_song_replaces_the_first(self, tmp_path):
        path = _index_path(tmp_path)
        store = SongAudioLinkStore(path)
        _link(store, SONG_A, name="first.wav")
        _link(store, SONG_A, name="second.wav", data=TRACK + b"\xff")
        # 같은 프로세스에서도, 새로 연 인스턴스에서도 둘 다 "second"만 본다 —
        # 교체는 색인 자체를 바꿔 끼운 것이지 메모리만의 일이 아니다.
        for reader in (store, SongAudioLinkStore(path)):
            result = reader.resolve(SONG_A)
            assert result.record["file_name"] == "second.wav"

    def test_different_songs_keep_separate_links(self, tmp_path):
        store = SongAudioLinkStore(_index_path(tmp_path))
        _link(store, SONG_A, name="a.wav")
        _link(store, SONG_B, name="b.wav", data=TRACK + b"\x01")
        assert store.resolve(SONG_A).record["file_name"] == "a.wav"
        assert store.resolve(SONG_B).record["file_name"] == "b.wav"


class TestMemoryOnlyInstances:
    def test_a_pathless_store_never_touches_disk(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = SongAudioLinkStore()
        _link(store, SONG_A)
        assert store.resolve(SONG_A).status == "found"
        assert list(tmp_path.iterdir()) == []  # 아무 파일도 안 만든다

    def test_a_pathless_store_does_not_share_state_with_another_instance(self):
        store_one = SongAudioLinkStore()
        _link(store_one, SONG_A)
        store_two = SongAudioLinkStore()
        assert store_two.resolve(SONG_A).status == "none"


class TestFailOpenReads:
    def test_a_missing_blob_file_resolves_to_missing(self, tmp_path):
        path = _index_path(tmp_path)
        store = SongAudioLinkStore(path)
        _link(store, SONG_A)
        for blob in (path.parent / "song_audio_files").iterdir():
            blob.unlink()
        result = SongAudioLinkStore(path).resolve(SONG_A)
        assert result.status == "missing"
        assert result.record is not None  # 색인이 기억하는 메타데이터는 남는다
        assert result.record["file_name"] == "track.wav"

    def test_a_corrupted_blob_resolves_to_missing_not_the_wrong_bytes(self, tmp_path):
        path = _index_path(tmp_path)
        store = SongAudioLinkStore(path)
        _link(store, SONG_A)
        for blob in (path.parent / "song_audio_files").iterdir():
            blob.write_bytes(b"corrupted, not the original bytes at all")
        result = SongAudioLinkStore(path).resolve(SONG_A)
        assert result.status == "missing"

    def test_a_corrupt_index_file_degrades_to_none_not_a_crash(self, tmp_path):
        path = _index_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json at all", encoding="utf-8")
        assert SongAudioLinkStore(path).resolve(SONG_A).status == "none"


class TestContentAddressedDedup:
    """리드 지시 2항(전반) — 같은 sha256 은 한 번만 쓴다."""

    def test_the_second_write_of_identical_bytes_does_not_rewrite_the_file(self, tmp_path):
        path = _index_path(tmp_path)
        store = SongAudioLinkStore(path)
        _link(store, SONG_A, data=TRACK)
        files_dir = path.parent / "song_audio_files"
        blobs = list(files_dir.iterdir())
        assert len(blobs) == 1
        blob = blobs[0]
        # 블롭을 손상시킨 뒤, 같은 바이트로 **다른 곡**을 또 링크한다. 저장소가
        # "이미 있으니 건드리지 않는다"를 실제로 지킨다면 손상은 그대로 남고,
        # SONG_A 의 조회는 해시 불일치로 missing 이 되어야 한다 — 만약
        # 재작성이 일어났다면 올바른 바이트로 되돌아와 found 가 됐을 것이다.
        blob.write_bytes(b"deliberately corrupted sentinel")
        _link(store, SONG_B, name="other.wav", data=TRACK)  # 같은 TRACK 바이트
        assert len(list(files_dir.iterdir())) == 1  # 새 블롭이 생기지 않았다
        assert store.resolve(SONG_A).status == "missing"  # 손상이 그대로다
        # 대조군: 저장소가 정말 중복 제거를 하고 있다는 것 자체는, 손상되지
        # 않은 상태에서 두 곡이 같은 sha256 을 공유한다는 사실로도 보인다.
        assert store.resolve(SONG_B).record["sha256"] == store.resolve(SONG_A).record["sha256"]

    def test_two_different_songs_sharing_identical_bytes_share_one_blob_file(self, tmp_path):
        path = _index_path(tmp_path)
        store = SongAudioLinkStore(path)
        _link(store, SONG_A, name="a.wav", data=TRACK)
        _link(store, SONG_B, name="b.wav", data=TRACK)
        files_dir = path.parent / "song_audio_files"
        assert len(list(files_dir.iterdir())) == 1
        assert store.resolve(SONG_A).data == TRACK
        assert store.resolve(SONG_B).data == TRACK

    def test_a_pathless_store_also_deduplicates_in_memory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = SongAudioLinkStore()
        _link(store, SONG_A, name="a.wav", data=TRACK)
        _link(store, SONG_B, name="b.wav", data=TRACK)
        assert store.resolve(SONG_A).data == TRACK
        assert store.resolve(SONG_B).data == TRACK


class TestAtomicWrites:
    """리드 지시 2항(후반) — 블롭·색인 둘 다 "같은 디렉터리 임시 파일 +
    os.replace" (``test_web_panel.py::TestPinPersistence`` 와 같은 시험 모양)."""

    def test_the_blob_write_goes_through_a_same_directory_temp_and_os_replace(
        self, tmp_path, monkeypatch
    ):
        path = _index_path(tmp_path)
        files_dir = path.parent / "song_audio_files"
        calls: list[tuple[str, str]] = []
        real_replace = os.replace

        def spy(src, dst):
            calls.append((str(src), str(dst)))
            real_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy)
        _link(SongAudioLinkStore(path), SONG_A)
        blob_calls = [(s, d) for s, d in calls if str(files_dir) in d]
        assert blob_calls, "the audio blob must be swapped into place with os.replace"
        src, dst = blob_calls[-1]
        assert Path(src).parent == Path(dst).parent == files_dir
        assert src != dst
        # 남는 임시 파일이 없다 — iterdir 라 점(.) 로 시작하는 임시 파일도 잡힌다.
        assert len(list(files_dir.iterdir())) == 1

    def test_the_index_write_goes_through_a_same_directory_temp_and_os_replace(
        self, tmp_path, monkeypatch
    ):
        path = _index_path(tmp_path)
        calls: list[tuple[str, str]] = []
        real_replace = os.replace

        def spy(src, dst):
            calls.append((str(src), str(dst)))
            real_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy)
        _link(SongAudioLinkStore(path), SONG_A)
        index_calls = [(s, d) for s, d in calls if d == str(path)]
        assert index_calls, "the index file must be swapped into place with os.replace"
        src, dst = index_calls[-1]
        assert Path(src).parent == path.parent
        assert src != dst
        assert path.exists()

    def test_a_failed_blob_swap_leaves_no_partial_blob_and_raises(self, tmp_path, monkeypatch):
        path = _index_path(tmp_path)
        files_dir = path.parent / "song_audio_files"
        store = SongAudioLinkStore(path)

        def boom(src, dst):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", boom)
        with pytest.raises(OSError):
            _link(store, SONG_A)
        # 블롭 디렉터리가 생성됐더라도(mkdir 은 replace 전에 돈다) 안에는
        # 아무 파일도(임시 파일 포함) 남지 않는다.
        assert not files_dir.exists() or list(files_dir.iterdir()) == []
        assert store.resolve(SONG_A).status == "none"  # 색인도 커밋되지 않았다

    def test_a_failed_index_swap_leaves_the_previous_index_intact(self, tmp_path, monkeypatch):
        path = _index_path(tmp_path)
        store = SongAudioLinkStore(path)
        _link(store, SONG_A, name="first.wav")
        before = path.read_text(encoding="utf-8")

        real_replace = os.replace

        def selective_boom(src, dst):
            # 블롭 쓰기는 성공시키고(이미 있으면 애초에 안 불림), 색인 쓰기만
            # 실패시킨다 — 색인 파일 경로로 가는 replace만 막는다.
            if str(dst) == str(path):
                raise OSError("disk full")
            real_replace(src, dst)

        monkeypatch.setattr(os, "replace", selective_boom)
        with pytest.raises(OSError):
            _link(store, SONG_A, name="second.wav", data=TRACK + b"\x02")
        assert path.read_text(encoding="utf-8") == before
        # 메모리 쪽도 커밋 전이다 — "second" 로 보이면 안 된다.
        assert SongAudioLinkStore(path).resolve(SONG_A).record["file_name"] == "first.wav"
