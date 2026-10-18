"""칸 줄 하나의 칸 만들기 · 옮기기 · 지우기 규칙 (순수 함수, SPEC-LDRHYTHM-001).

격자의 한 줄(트랙 하나)은 ``bar`` 오름차순의 칸들이다. 칸은 자기 ``bar`` 부터 다음 칸의 ``bar``
직전까지를 덮고, 마지막 칸은 끝이 열려 있다. 첫 칸 앞 마디는 비어 있다(앞 공백).

칸은 ``bar`` 말고는 들여다보지 않는다. 나머지 키(``entry``·프리셋 번호·``evidence`` 따위)는 그대로
실어 나른다. 입력은 고치지 않고 새 칸·새 목록을 돌려주며, 입력 순서는 상관없다(안에서 ``bar`` 로
정렬한다). 규칙을 어기는 편집은 ``BeatGridCellEditError`` 로 거절한다.

콘솔에도 웹·안전 계층에도 닿지 않는다 — 입출력이 없다.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import cast

__all__ = ["BeatGridCellEditError", "row_create", "row_delete", "row_move"]


class BeatGridCellEditError(ValueError):
    """칸 편집을 거절한다. 메시지는 감독에게 그대로 보여도 되는 한국어 사유다
    (`beat_grid_edit.BeatGridEditError`와 같은 계약)."""


def _bar(cue: Mapping[str, object]) -> int:
    return cast(int, cue["bar"])


def _sorted(cues: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """입력 순서와 상관없이 같은 결과를 내려고 ``bar`` 오름차순으로 먼저 정렬한다."""
    return sorted(cues, key=_bar)


def _index_at(ordered: Sequence[Mapping[str, object]], bar: int) -> int | None:
    """정렬된 줄에서 ``bar`` 마디에 시작하는 칸의 자리. 없으면 ``None``."""
    return next((index for index, cue in enumerate(ordered) if _bar(cue) == bar), None)


# @MX:NOTE: [AUTO] 바뀌는 것은 bar 뿐이다 — evidence 까지 원본 그대로라서 복사한 칸이 새로 승인
#   대기가 되지 않는다. 원본은 그 마디를 덮는 앞 칸이고, 앞 공백이면 바로 뒤의 첫 칸이다.
def row_create(cues: Sequence[Mapping[str, object]], bar: int) -> dict[str, object]:
    """``bar`` 마디에서 시작하는 새 칸 — 원본 칸 하나를 깊게 복사하고 ``bar`` 만 바꾼 새 사전.

    원본은 ``bar`` 보다 앞에서 시작한 칸 가운데 가장 뒤의 것이다(칸 안쪽을 나누거나 마지막 칸
    뒤에 잇는 경우). 앞 칸이 하나도 없으면(앞 공백) 바로 뒤의 첫 칸이다. 마디가 1 미만이거나,
    줄에 칸이 없거나, 그 마디에서 이미 칸이 시작하면 ``BeatGridCellEditError``. 원본은 고치지
    않는다."""
    if bar < 1:
        raise BeatGridCellEditError(
            f"{bar}마디에는 칸을 만들 수 없습니다 — 마디는 1부터 시작합니다"
        )
    ordered = _sorted(cues)
    if not ordered:
        raise BeatGridCellEditError("이 줄에는 칸이 하나도 없어 복사해 올 칸이 없습니다")
    if _index_at(ordered, bar) is not None:
        raise BeatGridCellEditError(f"{bar}마디에서는 이미 칸이 시작합니다")
    earlier = [cue for cue in ordered if _bar(cue) < bar]
    source = earlier[-1] if earlier else ordered[0]
    new = copy.deepcopy(dict(source))
    new["bar"] = bar
    return new


def row_move(
    cues: Sequence[Mapping[str, object]], from_bar: int, to_bar: int
) -> list[dict[str, object]]:
    """``from_bar`` 마디에서 시작하는 칸을 ``to_bar`` 마디로 옮긴 새 목록(``bar`` 오름차순).

    옮긴 칸은 ``bar`` 말고는 그대로다. ``to_bar`` 는 이웃 두 칸(옮기는 칸을 뺀 줄에서 바로 앞·뒤)의
    ``bar`` 사이에 엄격하게 들어와야 한다 — 다른 칸을 넘어 순서가 바뀌면 거절한다. 이웃이 없는
    쪽은 끝이 열려 있다(첫 칸은 앞 공백으로, 마지막 칸은 얼마든지 뒤로). ``to_bar`` 가 1 미만이거나
    ``from_bar`` 와 같거나, ``from_bar`` 에서 시작하는 칸이 없거나, ``to_bar`` 에서 이미 칸이
    시작해도 ``BeatGridCellEditError``."""
    if to_bar < 1:
        raise BeatGridCellEditError(f"{to_bar}마디로는 옮길 수 없습니다 — 마디는 1부터 시작합니다")
    if to_bar == from_bar:
        raise BeatGridCellEditError(f"{from_bar}마디의 칸을 같은 마디로 옮길 수는 없습니다")
    ordered = _sorted(cues)
    index = _index_at(ordered, from_bar)
    if index is None:
        raise BeatGridCellEditError(f"{from_bar}마디에서 시작하는 칸이 없어 옮길 수 없습니다")
    if _index_at(ordered, to_bar) is not None:
        raise BeatGridCellEditError(f"{to_bar}마디에서는 이미 다른 칸이 시작합니다")
    below = _bar(ordered[index - 1]) if index > 0 else -math.inf
    above = _bar(ordered[index + 1]) if index + 1 < len(ordered) else math.inf
    if not below < to_bar < above:
        raise BeatGridCellEditError(
            f"{from_bar}마디의 칸을 {to_bar}마디로 옮기면 이웃 칸을 넘어갑니다 "
            "— 칸의 순서는 바꿀 수 없습니다"
        )
    moved = [dict(cue) for cue in ordered]
    moved[index]["bar"] = to_bar
    return moved


def row_delete(cues: Sequence[Mapping[str, object]], bar: int) -> list[dict[str, object]]:
    """``bar`` 마디에서 시작하는 칸만 뺀 새 목록(``bar`` 오름차순). 그런 칸이 없으면 거절한다."""
    ordered = _sorted(cues)
    index = _index_at(ordered, bar)
    if index is None:
        raise BeatGridCellEditError(f"{bar}마디에서 시작하는 칸이 없어 지울 수 없습니다")
    return [dict(cue) for position, cue in enumerate(ordered) if position != index]
