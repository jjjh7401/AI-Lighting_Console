"""칸 옮기기와 반영 준비(MIB) 사전이동 큐를 함께 본다 — 순수 규칙 (SPEC-LDRHYTHM-001).

칸을 옮기면 그 줄의 사전이동 큐도 옮긴 자리에 맞춰 옮겨야 한다. 큐는 칸이 아니라서
칸을 따라가지 않는다. 그래서 옮긴 뒤의 줄에서 큐를 다시 짓고(``beat_grid_mib.mib_plan``),
같은 자리의 옛 큐와 짝지어 마디가 바뀐 큐만 콘솔 이벤트 시각을 옮긴다 — 옮기기 = 다시 반영.

이 파일은 순수 함수만 둔다. 콘솔에 아무것도 쓰지 않고 읽지도 않으며, 웹·안전 계층도 모른다
(``beat_grid_cell_live`` 와 같은 계약).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from server.design.beat_grid_cell_live import CellLiveRefused
from server.design.beat_grid_mib import (
    MIB_DARK_SHORT,
    MIB_LIT_MOVE,
    MIB_LIT_START,
    MIB_NO_GAP,
    BarClock,
    mib_plan,
)

__all__ = ["move_mib_premoves"]

# 옮기기 뒤 새로 생기면 「켜진 채 시작」으로 거절하는 안내 갈래다.
# 어두운 시간이 모자라 사전이동 큐를 세울 수 없는 자리다.
# 「켜진 채 움직임 시작」과 「켜진 채 이동」은 옮겨도 생기지 않는다.
# 그래서 옮기기 전부터 있던 안내는 거절하지 않는다(D3(a) 경고와 같다).
_LIT_START_KINDS = frozenset({MIB_LIT_START, MIB_LIT_MOVE, MIB_NO_GAP, MIB_DARK_SHORT})


def move_mib_premoves(
    before: Sequence[Mapping[str, object]],
    after: Sequence[Mapping[str, object]],
    timing: BarClock,
) -> list[tuple[Mapping[str, object], Mapping[str, object]]]:
    """옮긴 줄의 사전이동(MIB 선행) 큐 — 옮기기 전과 옮긴 뒤를 자리로 짝지어 본다.

    ``before`` 와 ``after`` 는 마디순으로 정렬한 같은 줄의 칸이다. 사전이동 큐는
    넣지 않는다. 옮기기는 칸의 순서를 바꾸지 않으므로 같은 자리의 칸이 같은 칸이다.
    옮긴 뒤에 새로 생긴 「켜진 채 시작」 안내가 있거나 큐를 새로 세우거나 지워야
    하면 ``CellLiveRefused`` 다. 그 밖에 큐가 같은 자리에 살아 있고 마디만 바뀌었으면
    ``(옛 큐, 새 큐)`` 쌍을 돌려준다. 콘솔에서는 그 큐의 이벤트 시각만 옮기면 된다.
    """
    old = mib_plan(before, timing)
    new = mib_plan(after, timing)
    seen = {(note.index, note.kind) for note in old.notes}
    for note in new.notes:
        if note.kind in _LIT_START_KINDS and (note.index, note.kind) not in seen:
            raise CellLiveRefused(
                f"옮긴 자리에서 켜진 채 움직임이 시작됩니다 ({note.text}) — 옮기지 않았습니다"
            )
    old_queues = dict(old.premoves)
    new_queues = dict(new.premoves)
    relocated: list[tuple[Mapping[str, object], Mapping[str, object]]] = []
    for index in sorted(old_queues.keys() | new_queues.keys()):
        old_queue, new_queue = old_queues.get(index), new_queues.get(index)
        if old_queue is None and new_queue is not None:
            raise CellLiveRefused(
                f"{new_queue['bar']}마디 앞에 사전이동 큐를 새로 세워야 합니다 "
                "— 칸 옮기기는 큐를 새로 만들지 않습니다. ⇪ 전체 반영을 사용해 주세요"
            )
        if old_queue is not None and new_queue is None:
            raise CellLiveRefused(
                f"{old_queue['bar']}마디 앞의 사전이동 큐가 없어져야 합니다 "
                "— 칸 옮기기는 큐를 지우지 않습니다. ⇪ 전체 반영을 사용해 주세요"
            )
        if old_queue is not None and new_queue is not None and old_queue["bar"] != new_queue["bar"]:
            relocated.append((old_queue, new_queue))
    return relocated
