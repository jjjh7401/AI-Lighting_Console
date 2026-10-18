"""곡마다 스피드 마스터 번호 — 앱이 기록하고 빈 번호를 자동으로 고른다.

``Master 3.N At BPM`` 은 쇼 전체가 공유하는 스피드 마스터의 BPM 을 바꾼다. 곡이 같은 번호를
쓰면 한 곡의 BPM 줄이 다른 곡의 효과·웨이브 속도를 덮는다. 그래서 곡마다 번호를 하나씩 기록한다.

- 기록: 앱 데이터 폴더의 ``speed_masters.json`` — ``{"version": 1, "songs": [...]}``,
  항목은 ``{"title", "master"}``.
- 배정: 기록이 없는 곡은 아직 어느 곡에도 없는 번호 가운데 **가장 큰 번호**를 골라 적는다.
  15 부터 — 16 은 콘솔 오디오 입력 BPM 마스터라 쓰지 않는다(REQ-LDRHYTHM-010).
- 곡 이름은 설정 파일(preset_pools.yaml)에 적지 않는다. 곡이 늘어도 설정을 고칠 일이 없다.
- 기록을 읽지 못했거나 모양이 틀리면 배정하지 않는다(번호를 지어내지 않는다).
  번호가 모두 찼어도 배정하지 않는다.

한계: 기록은 이 앱이 배정한 번호만 안다. 콘솔에 다른 경로로 묶인 스피드 마스터는 읽지 않는다.
배정된 번호가 콘솔에서 비어 있는지는 승인 카드의 ``Master 3.N At BPM`` 줄로 리드가 확인한다.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from pathlib import Path

REGISTRY_FILE_NAME = "speed_masters.json"

#: 배정할 수 있는 스피드 마스터 번호. 16 은 오디오 입력 BPM 마스터라 쓰지 않는다(REQ-LDRHYTHM-010).
SPEED_MASTER_NUMBERS = range(1, 16)

_REGISTRY_VERSION = 1


class RegistryError(ValueError):
    """기록 파일을 읽을 수 없거나 모양이 틀리다 — 배정하지 않는다."""


def song_key(title: str) -> str:
    """대소문자·공백·밑줄만 다른 제목은 같은 곡이다(``LOVE ATTACK`` = ``love_attack``)."""
    return re.sub(r"[\s_]+", "", title).upper()


def is_speed_master(value: object) -> bool:
    """1~15 의 정수인가 — ``bool`` 은 정수가 아니다."""
    return isinstance(value, int) and not isinstance(value, bool) and value in SPEED_MASTER_NUMBERS


def read_registry(path: Path) -> list[dict[str, object]]:
    """기록된 곡 목록. 파일이 없으면 빈 목록(처음 배정).

    읽지 못하거나 모양이 틀리면 ``RegistryError``.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as error:
        raise RegistryError(f"기록 파일을 읽지 못했습니다: {error}") from error
    try:
        document = json.loads(text)
    except ValueError as error:
        raise RegistryError("기록 파일이 JSON 으로 읽히지 않습니다") from error
    songs = document.get("songs") if isinstance(document, Mapping) else None
    if not isinstance(songs, list):
        raise RegistryError("기록 파일에 songs 목록이 없습니다")
    entries: list[dict[str, object]] = []
    for entry in songs:
        title = entry.get("title") if isinstance(entry, Mapping) else None
        master = entry.get("master") if isinstance(entry, Mapping) else None
        if not isinstance(title, str) or not song_key(title) or not is_speed_master(master):
            raise RegistryError("기록 파일의 곡 항목이 틀렸습니다")
        entries.append({"title": title, "master": master})
    return entries


def _write_registry(path: Path, songs: list[dict[str, object]]) -> None:
    """임시 파일에 쓰고 바꿔 놓는다 — 쓰다 끊겨도 옛 기록이 남는다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    body = {"version": _REGISTRY_VERSION, "songs": songs}
    temporary.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def assign_speed_master(path: Path, song_title: str) -> int | None:
    """이 곡의 스피드 마스터 번호.

    기록이 있으면 그 번호를 돌려준다. 없으면 빈 번호 가운데 가장 큰 번호를 골라 적는다.
    기록을 읽거나 쓰지 못했거나 빈 번호가 없으면 ``None`` — 그때 아무것도 바뀌지 않는다.
    """
    wanted = song_key(song_title)
    if not wanted:
        return None
    try:
        songs = read_registry(path)
    except RegistryError:
        return None
    for entry in songs:
        if song_key(str(entry["title"])) == wanted:
            return int(entry["master"])  # type: ignore[call-overload]
    taken = {int(entry["master"]) for entry in songs}  # type: ignore[call-overload]
    free = [number for number in sorted(SPEED_MASTER_NUMBERS, reverse=True) if number not in taken]
    if not free:
        return None
    master = free[0]
    songs.append({"title": song_title.strip(), "master": master})
    try:
        _write_registry(path, songs)
    except OSError:
        return None
    return master


#: 곡의 스피드 마스터를 가리키는 정책 키 — 이름·기록 위치(문자열)만 싣는다.
SONG_POLICY_KEYS = ("speed_master", "speed_master_song", "speed_master_registry")


def with_song_speed_master(
    policy: Mapping[str, object], song_title: object, *, registry_path: Path
) -> dict[str, object]:
    """정책 사본에 이 곡을 얹는다. 번호는 여기서 배정하지 않는다.

    번호는 ``beat_grid_edit.speed_master_of`` 가 처음 필요할 때 배정·기록한다. 마스터를 쓰지 않는
    곡(디머·색만 저장하는 곡)은 번호를 쓰지 않아, 15개 번호를 헛되이 줄이지 않는다.
    싣는 값은 문자열뿐이라 정책을 그대로 직렬화할 수 있다.
    """
    resolved = {key: value for key, value in policy.items() if key not in SONG_POLICY_KEYS}
    if isinstance(song_title, str):
        resolved["speed_master_song"] = song_title
        resolved["speed_master_registry"] = str(registry_path)
    return resolved
