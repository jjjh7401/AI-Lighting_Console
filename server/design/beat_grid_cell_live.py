"""칸 편집을 콘솔에 바로 반영할 때 쓰는 순수 규칙 — 옮기기 (SPEC-LDRHYTHM-001).

이 파일은 순수 함수만 둔다. 콘솔에 아무것도 쓰지 않고 읽지도 않으며, 웹·안전 계층도 모른다.
호출자가 방금 읽은 값(소유 기록 · 트랙 TARGET · 이벤트 시각)과 보내려는 명령 줄을 넘기면, 이 파일은
다음 넷만 가려 준다.

- 이 곡이 쓰는 타임코드와, 그룹의 시퀀스를 가리키는 콘솔 트랙. 트랙 번호를 짐작하지 않고 읽은
  TARGET 으로만 찾는다 — 찾지 못한 그룹은 건드리지 않고, 둘 이상이면 거절한다.
- 이벤트 시각. 유한하고 0 이상인 수만 받는다.
- 보내려는 명령 줄. 옮기기가 허용하는 단 한 가지 꼴(이 곡이 쓰는 트랙의 이벤트 시각 고치기)과 글자
  하나까지 같을 때만 통과시킨다. 지우기·만들기(Store)·``cd`` 같은 그 밖의 줄은 모두 거절한다.
- 옮긴 뒤의 장부. 소유 기록(``tracks[줄]["cues"]``)과 칸 기록(스냅샷)에서 옮긴 칸의 마디 열쇠만
  새 마디로 바꾼 사본이다. 입력은 고치지 않는다.

명령 줄은 ``beat_grid_tc_cell`` 이 만든다. 이 파일은 그 꼴을 믿지 않고 콘솔로 나가기 직전에 한 번 더
걸러 내는 마지막 안전핀이다. 거절 메시지는 감독에게 그대로 보여도 되는 한국어 사유다.
"""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping, Sequence
from typing import TypeGuard

from server.design.beat_grid_send import BeatGridCellKey, PartialCellSnapshot, parse_track_target

__all__ = [
    "SCOPE_CREATE_DELETE",
    "SCOPE_MOVE",
    "CellLiveRefused",
    "command_track_index",
    "console_tracks_for_groups",
    "move_bundle_allowed",
    "move_record_tracks",
    "move_snapshot_keys",
    "owned_timecode_numbers",
    "parse_event_seconds",
    "scope_covers",
]

#: 감독이 허락할 수 있는 일의 범위. 허락한 범위가 이번 일에 필요한 범위를 덮어야 한다.
SCOPE_MOVE = "move"
SCOPE_CREATE_DELETE = "create_delete"

#: 옮기기가 허용하는 명령 줄의 유일한 꼴 — ``Set Timecode <tc>.1.<k>.1.1.<N> Property 'Time' <S>``.
#: 숫자는 ASCII ``[0-9]`` 만 받는다(``\d`` 는 다른 문자 체계의 숫자까지 받는다).
_MOVE_LINE = re.compile(
    r"Set Timecode (?P<timecode>[0-9]+)\.1\.(?P<track>[0-9]+)\.1\.1\.[0-9]+"
    r" Property 'Time' [0-9]+(?:\.[0-9]+)?"
)


class CellLiveRefused(ValueError):
    """칸 편집을 콘솔에 바로 반영하는 일을 거절한다. 메시지는 감독에게 그대로 보여도 되는 한국어
    사유다(`beat_grid_edit.BeatGridEditError` 와 같은 계약)."""


def _is_int(value: object) -> TypeGuard[int]:
    """정수인가 — ``bool`` 은 정수로 치지 않는다(``True`` 가 1번 타임코드로 읽히지 않게)."""
    return isinstance(value, int) and not isinstance(value, bool)


def scope_covers(granted: frozenset[str], needed: frozenset[str]) -> bool:
    """허락한 범위(``granted``)가 이번 일에 필요한 범위(``needed``)를 모두 덮는가."""
    return needed <= granted


def owned_timecode_numbers(record: Mapping[str, object]) -> tuple[int, ...]:
    """이 곡의 소유 기록이 가리키는 타임코드 번호 — 주 타임코드, 이어서 나눠 담은 추가 타임코드들.

    중복은 한 번만 두고 적힌 순서를 지킨다. 주 ``timecode_number`` 가 없거나 정수가 아니면
    ``CellLiveRefused``. ``extra_timecodes`` 는 없어도 되고, 번호를 못 읽는 항목은 건너뛴다
    (소유로 치는 번호가 줄어드는 쪽이라 안전하다)."""
    main = record.get("timecode_number")
    if not _is_int(main):
        raise CellLiveRefused(
            "이 곡의 소유 기록에 타임코드 번호가 없어 콘솔에 바로 반영할 수 없습니다"
        )
    numbers = [main]
    extras = record.get("extra_timecodes")
    for entry in extras if isinstance(extras, list | tuple) else ():
        number = entry.get("timecode_number") if isinstance(entry, Mapping) else None
        if _is_int(number):
            numbers.append(number)
    return tuple(dict.fromkeys(numbers))


# @MX:NOTE: [AUTO] 타임코드의 자식 1 은 마커라서 트랙은 2번 자리부터 시작하고, 명령에 쓰는 트랙
#   번호는 1부터 센다(``Timecode <tc>.1.<k>.1.1``). 그래서 번호는 자리 - 1 이다.
def command_track_index(state_index: int) -> int:
    """콘솔 상태에서 읽은 트랙 자리(``state_index``)를 명령에 쓰는 트랙 번호로 바꾼다.

    자리 3 이면 번호 2 다. 2 미만은 트랙이 아니다(자리 1 은 마커) — ``CellLiveRefused``."""
    if state_index < 2:
        raise CellLiveRefused(
            f"상태 자리 {state_index} 에는 트랙이 없습니다 "
            "— 트랙은 2번 자리부터이고 1번은 마커입니다"
        )
    return state_index - 1


def console_tracks_for_groups(
    record: Mapping[str, object], reads: Sequence[tuple[int, int, object]]
) -> dict[str, tuple[int, int]]:
    """그룹 이름 -> ``(타임코드 번호, 명령용 트랙 번호)`` — 그 그룹의 시퀀스를 가리키는 콘솔 트랙.

    ``reads`` 는 소유한 타임코드마다 트랙 자식을 읽은 ``(타임코드 번호, 상태 자리, TARGET 원값)``
    이다. 소유 기록의 ``tracks`` 에서 시퀀스 번호·이름을 모아 TARGET 을 시퀀스 번호로 풀고
    (:func:`parse_track_target`), 그룹의 시퀀스와 같은 읽기를 찾는다. 정확히 하나면 그 그룹을 그
    트랙에 대응시키고, 없으면 그 그룹은 결과에서 뺀다. 둘 이상이면 어느 트랙인지 정할 수 없어
    ``CellLiveRefused``. 시퀀스 번호가 없는 그룹은 대응시킬 수 없어 뺀다."""
    groups = record.get("tracks")
    sequence_numbers: dict[str, int] = {}
    sequence_names: dict[int, str | None] = {}
    for name, track in groups.items() if isinstance(groups, Mapping) else ():
        if not isinstance(track, Mapping):
            continue
        number = track.get("sequence_number")
        if not _is_int(number):
            continue
        label = track.get("sequence_name")
        sequence_numbers[name] = number
        sequence_names[number] = label if isinstance(label, str) else None
    targets = [
        (timecode, state_index, parse_track_target(raw, sequence_names)[0])
        for timecode, state_index, raw in reads
    ]
    found: dict[str, tuple[int, int]] = {}
    for name, number in sequence_numbers.items():
        hits = [
            (timecode, state_index) for timecode, state_index, target in targets if target == number
        ]
        if len(hits) > 1:
            raise CellLiveRefused(
                f"그룹 '{name}' 의 시퀀스는 {number}번인데, 그 시퀀스를 가리키는 트랙이 "
                f"{len(hits)}개라 어느 트랙인지 정할 수 없습니다 — 콘솔에 바로 반영하지 않습니다"
            )
        if hits:
            timecode, state_index = hits[0]
            found[name] = (timecode, command_track_index(state_index))
    return found


def _as_float(text: object) -> float | None:
    """글자나 수를 ``float`` 로. 수가 아니거나(``bool`` 포함) 읽을 수 없으면 ``None``."""
    if isinstance(text, bool) or not isinstance(text, str | int | float):
        return None
    try:
        return float(text)
    except (ValueError, OverflowError):
        return None


def parse_event_seconds(text: object) -> float:
    """콘솔이 읽어 준 이벤트 시각(``"83.784000"`` 같은 글자이거나 수)을 초로 — 유한하고 0 이상이어야
    한다. 아니면 ``CellLiveRefused``."""
    seconds = _as_float(text)
    if seconds is None:
        raise CellLiveRefused(f"이벤트 시각을 읽을 수 없습니다: {text!r}")
    if not math.isfinite(seconds) or seconds < 0:
        raise CellLiveRefused(f"이벤트 시각은 0 이상의 유한한 수여야 합니다: {text!r}")
    return seconds


# @MX:NOTE: [AUTO] 콘솔로 나가는 명령 줄의 마지막 안전핀 — 허용 목록(allow-list)이다. 목록 밖은 전부
#   거절하고, 번들에 어긋난 줄이 하나라도 있으면 아무것도 허용하지 않는다(호출자는 이 함수가 돌아온
#   뒤에만 보낸다). ';'·줄바꿈 검사는 꼴 검사와 겹치지만 일부러 따로 둔다 — 꼴을 나중에 느슨하게
#   고쳐도 명령 이어 붙이기는 계속 막히고, 사유도 따로 남는다.
def move_bundle_allowed(commands: Sequence[str], owned: Mapping[int, frozenset[int]]) -> None:
    """보내려는 명령 줄 전부가 옮기기 허용 꼴이고 소유한 트랙의 것인지 본다 — 아니면 거절한다.

    허용 꼴은 정확히 하나다: ``Set Timecode <tc>.1.<k>.1.1.<N> Property 'Time' <S>`` (``N`` 은
    숫자, ``S`` 는 숫자에 소수부가 하나까지 붙을 수 있는 초). ``tc`` 가 ``owned`` 의 키이고 ``k``
    가 ``owned[tc]`` 안에 있어야 한다. 그 밖의 모든 줄 — 지우기(``Delete``)·만들기(``Store``)·
    ``cd``·다른 동사, 앞뒤 공백, ``;``·줄바꿈으로 이은 줄 — 은 거절한다. 빈 목록은 통과한다.

    모든 줄을 검사하고, 어긋난 첫 줄을 대며 ``CellLiveRefused``. 통과하면 ``None`` 이다."""
    # 번호는 글자 그대로 견준다 — int() 로 바꾸면 «05»·아주 긴 숫자가 같은 번호로 읽혀서, 검사한
    # 번호와 콘솔로 나가는 글자가 달라진다.
    owned_text = {
        str(timecode): frozenset(str(k) for k in tracks) for timecode, tracks in owned.items()
    }
    for line in commands:
        if not isinstance(line, str):
            raise CellLiveRefused(f"명령 줄이 글자가 아닙니다: {line!r}")
        if ";" in line or "\n" in line or "\r" in line:
            raise CellLiveRefused(
                "한 줄에는 명령 하나만 둘 수 있습니다 "
                f"— 줄바꿈이나 ';' 로 명령을 이었습니다: {line!r}"
            )
        match = _MOVE_LINE.fullmatch(line)
        if match is None:
            raise CellLiveRefused(f"옮기기에 허용된 명령 꼴이 아닙니다: {line!r}")
        tracks = owned_text.get(match["timecode"])
        if tracks is None:
            raise CellLiveRefused(
                f"이 곡이 쓰지 않는 타임코드 {match['timecode']} 의 줄이라 "
                f"건드릴 수 없습니다: {line!r}"
            )
        if match["track"] not in tracks:
            raise CellLiveRefused(
                f"이 곡이 쓰지 않는 타임코드 {match['timecode']} 의 트랙 {match['track']} 줄이라 "
                f"건드릴 수 없습니다: {line!r}"
            )


def _bar_renames(moves: Sequence[tuple[str, int, int]]) -> dict[str, dict[int, int]]:
    """줄마다 ``{옛 마디: 새 마디}`` — 같은 칸을 두 번 옮기거나 두 칸이 한 마디로 가면 거절한다."""
    renames: dict[str, dict[int, int]] = {}
    for group, old_bar, new_bar in moves:
        if not (_is_int(old_bar) and _is_int(new_bar)):
            raise CellLiveRefused(
                f"'{group}' 줄의 마디는 정수여야 합니다: {old_bar!r} -> {new_bar!r}"
            )
        row = renames.setdefault(group, {})
        if old_bar in row:
            raise CellLiveRefused(f"'{group}' 줄의 {old_bar}마디 칸을 두 번 옮길 수는 없습니다")
        if new_bar in row.values():
            raise CellLiveRefused(f"'{group}' 줄의 {new_bar}마디로 옮기는 칸이 둘 이상입니다")
        row[old_bar] = new_bar
    return renames


# @MX:NOTE: [AUTO] 옮김을 쌍마다가 아니라 묶음 전체로 본다 — 새 마디가 같은 묶음의 다른 옮김이
#   비우는 마디(5→7·7→9 의 7)면 겹침이 아니다. 격자의 ``row_move_many`` 와 같은 판정이어야 한다.
#   격자는 받는데 기록이 거절하면 콘솔 이벤트만 옮겨진 채 장부가 어긋난다.
def move_record_tracks(
    record: Mapping[str, object], moves: Sequence[tuple[str, int, int]]
) -> dict[str, object]:
    """소유 기록의 깊은 사본 — ``moves`` (줄, 옛 마디, 새 마디)대로 ``tracks[줄]["cues"]`` 의 마디
    열쇠(글자)만 바꾼다. 큐 번호는 그대로다(콘솔의 큐는 그대로이고 이벤트 시각만 달라진다).

    줄이 기록에 없거나, 옛 마디에 큐가 없거나, 새 마디에 (같은 묶음이 비우지 않는) 다른 큐가 있거나,
    옮김끼리 겹치면 ``CellLiveRefused``. 입력은 고치지 않고, 거절하면 아무것도 돌려주지 않는다."""
    renames = _bar_renames(moves)
    moved = copy.deepcopy(dict(record))
    tracks = moved.get("tracks")
    for group, row in renames.items():
        track = tracks.get(group) if isinstance(tracks, dict) else None
        if not isinstance(track, dict):
            raise CellLiveRefused(f"소유 기록에 '{group}' 줄이 없어 칸을 옮길 수 없습니다")
        listed = track.get("cues")
        recorded = listed if isinstance(listed, dict) else {}
        for old_bar in row:
            if str(old_bar) not in recorded:
                raise CellLiveRefused(
                    f"소유 기록에 '{group}' 줄의 {old_bar}마디 칸이 없어 옮길 수 없습니다"
                )
        vacated = {str(old_bar) for old_bar in row}
        for new_bar in row.values():
            if str(new_bar) in recorded and str(new_bar) not in vacated:
                raise CellLiveRefused(
                    f"소유 기록에 '{group}' 줄의 {new_bar}마디에 이미 다른 칸이 있어 "
                    "옮길 수 없습니다"
                )
        renamed = {str(old_bar): str(new_bar) for old_bar, new_bar in row.items()}
        track["cues"] = {renamed.get(key, key): number for key, number in recorded.items()}
    return moved


def move_snapshot_keys(
    snapshot: Mapping[BeatGridCellKey, object], moves: Sequence[tuple[str, int, int]]
) -> dict[BeatGridCellKey, object]:
    """칸 기록(스냅샷)의 새 사전 — 있는 열쇠 ``(줄, 옛 마디)`` 만 ``(줄, 새 마디)`` 로 옮긴다.

    칸 사전이 ``bar`` 를 품고 있으면 그것도 새 마디로 바꾼다(안 바꾸면 옮긴 칸이 지금 격자와 달라
    보여 계속 「미반영」으로 센다). 기록에 없는 옛 열쇠는 새로 만들지 않고, 그때 새 마디에 있던
    기록은 건드리지 않는다. 부분 기록(``PartialCellSnapshot``)은 부분 기록으로 남는다 — 일반 사전이
    되면 기록에 없는 칸이 전부 미반영으로 세어진다. 새 마디에 (같은 묶음이 비우지 않는) 다른 칸
    기록이 있거나 옮김끼리 겹치면 ``CellLiveRefused``. 입력은 고치지 않는다."""
    renames = _bar_renames(moves)
    moved: dict[BeatGridCellKey, object] = {}
    for (group, bar), body in snapshot.items():
        new_bar = renames.get(group, {}).get(bar)
        key = (group, bar if new_bar is None else new_bar)
        value = body
        if new_bar is not None and isinstance(body, Mapping) and "bar" in body:
            value = {**body, "bar": new_bar}
        if key in moved:
            raise CellLiveRefused(
                f"칸 기록에 '{key[0]}' 줄의 {key[1]}마디 칸이 이미 있어 옮길 수 없습니다"
            )
        moved[key] = value
    return PartialCellSnapshot(moved) if isinstance(snapshot, PartialCellSnapshot) else moved
