"""칸 옮기기의 사전이동(MIB 선행) 큐 짝짓기 — 순수 규칙 시험 (SPEC-LDRHYTHM-001).

``move_mib_premoves`` 는 옮기기 전과 옮긴 뒤의 같은 줄 칸을 자리로 짝지어,
마디가 바뀐 큐만 돌려준다. 옮긴 뒤 새로 생긴 「켜진 채 시작」이나 큐를 새로 세워야 하는
옮기기는 ``CellLiveRefused`` 로 거절한다. 웹 경로 시험(``test_web_beat_grid_cell_move``)과
겹치지 않게 규칙만 본다. 콘솔 접촉 0건.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from server.design import beat_grid_cell_mib as cell_mib_module
from server.design.beat_grid_cell_live import CellLiveRefused
from server.design.beat_grid_cell_mib import move_mib_premoves


class _Clock:
    """마디 시작(초) — 첫 다운비트 1.5초, 한 마디 2초다. 어둠은 마디 차이 × 2초다."""

    def bar_start_seconds(self, bar: int) -> float | None:
        return 1.5 + (bar - 1) * 2.0


CLOCK = _Clock()


def _lit(bar: int, preset: str) -> dict:
    return {"bar": bar, "label": "FOH", "position_preset_no": preset}


def _unlit(bar: int, preset: str) -> dict:
    return {"bar": bar, "label": "—", "position_preset_no": preset}


def test_a_queue_moves_with_the_cell_in_front_of_it_when_that_cell_moves():
    # 5마디(꺼짐) 뒤의 10마디 칸은 6마디에 큐가 서 있다(어둠 8초).
    # 5마디를 4마디로 옮기면 큐는 5마디로 간다.
    before = [_lit(3, "1.1"), _unlit(5, "1.2"), _lit(10, "1.3")]
    after = [_lit(3, "1.1"), _unlit(4, "1.2"), _lit(10, "1.3")]

    moves = move_mib_premoves(before, after, CLOCK)

    assert [(old["bar"], new["bar"]) for old, new in moves] == [(6, 5)]


def test_nothing_moves_when_no_queue_changes_its_bar():
    cues = [_lit(3, "1.1"), _unlit(5, "1.2"), _lit(10, "1.3")]

    assert move_mib_premoves(cues, cues, CLOCK) == []


def test_a_move_that_would_need_a_new_queue_is_refused():
    # 7마디 칸 앞의 어둠은 2초라 큐가 없다.
    # 10마디로 옮기면 어둠이 8초가 되어 6마디에 큐가 서야 한다.
    before = [_lit(3, "1.1"), _unlit(5, "1.2"), _lit(7, "1.3")]
    after = [_lit(3, "1.1"), _unlit(5, "1.2"), _lit(10, "1.3")]

    with pytest.raises(CellLiveRefused) as caught:
        move_mib_premoves(before, after, CLOCK)

    assert "6마디 앞에 사전이동 큐를 새로 세워야 합니다" in str(caught.value)
    assert "⇪ 전체 반영을 사용해 주세요" in str(caught.value)


def test_a_move_that_leaves_no_dark_gap_before_a_queued_cell_is_refused_as_a_lit_start():
    # 5마디 칸을 9마디로 옮기면 10마디 칸 앞에 어둠이 없다.
    # 큐를 세울 자리가 없어 10마디가 켜진 채 움직인다.
    before = [_lit(3, "1.1"), _unlit(5, "1.2"), _lit(10, "1.3")]
    after = [_lit(3, "1.1"), _unlit(9, "1.2"), _lit(10, "1.3")]

    with pytest.raises(CellLiveRefused) as caught:
        move_mib_premoves(before, after, CLOCK)

    assert "옮긴 자리에서 켜진 채 움직임이 시작됩니다" in str(caught.value)
    assert "10마디 MIB 불가 — 앞 큐 바로 다음 마디라 어두운 시간이 없습니다" in str(caught.value)


def test_a_dark_gap_that_was_already_too_short_does_not_refuse_the_move():
    # 7마디 칸 앞의 어둠(2초)은 옮기기 전부터 모자랐다.
    # 8마디로 옮겨도 여전히 모자랄 뿐 새로 생긴 것이 아니다.
    before = [_lit(3, "1.1"), _unlit(5, "1.2"), _lit(7, "1.3")]
    after = [_lit(3, "1.1"), _unlit(5, "1.2"), _lit(8, "1.3")]

    assert move_mib_premoves(before, after, CLOCK) == []


def test_a_lit_move_that_was_already_there_does_not_refuse_the_move():
    # 앞 칸이 켜져 있어 위치가 바뀌는 칸은 옮기기 전부터 켜진 채 움직인다.
    # 마디를 옮겨도 달라지지 않는다.
    before = [_lit(3, "1.1"), _lit(5, "1.2")]
    after = [_lit(3, "1.1"), _lit(6, "1.2")]

    assert move_mib_premoves(before, after, CLOCK) == []


def test_the_module_imports_only_pure_rules_and_no_input_output():
    tree = ast.parse(inspect.getsource(cell_mib_module))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    pure = {
        "__future__",
        "collections.abc",
        "server.design.beat_grid_cell_live",
        "server.design.beat_grid_mib",
    }

    assert imported <= pure
