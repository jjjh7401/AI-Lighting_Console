"""칸 줄 편집 규칙 — 칸 만들기 · 옮기기 · 지우기 (SPEC-LDRHYTHM-001, 순수 함수).

콘솔 접촉 0건. 칸은 ``bar`` 만 뜻이 있는 일반 사전이다(곡·리그 고유값 없음). 시험이 재는 것:

1. 만들기 — 새 칸은 원본 칸 하나를 깊게 복사하고 ``bar`` 만 바꾼다. 원본은 그 마디를 덮는 칸
   (바로 앞 칸)이고, 첫 칸 앞 빈 자리(앞 공백)에서는 바로 뒤의 첫 칸이다. 마디가 1 미만이거나
   줄이 비었거나 그 마디에서 이미 칸이 시작하면 거절한다. ``evidence`` 는 있는 그대로 따라가서
   복사한 칸이 새로 승인 대기가 되지 않는다.
2. 옮기기 — 이웃 칸 사이로만 옮긴다(양 끝은 열려 있다). 다른 칸에 올라타거나 넘으면 거절한다.
3. 지우기 — 그 마디에서 시작하는 칸만 지우고, 없으면 거절한다.
4. 입력 순서와 상관없이 같은 결과이고(안에서 정렬한다), 입력은 고치지 않으며, 거절 메시지는
   감독에게 보여도 되는 한국어 사유다.
5. 이 모듈은 웹·안전 계층을 import 하지 않는다.
"""

from __future__ import annotations

import ast
import copy
import inspect
import re

import pytest

from server.design import beat_grid_cell_edit as cell_edit_module
from server.design.beat_grid_cell_edit import (
    BeatGridCellEditError,
    row_create,
    row_delete,
    row_move,
)

HANGUL = re.compile(r"[가-힣]")


def _cue(bar: int, label: str | None = None, **fields: object) -> dict:
    """시험용 칸 — 라벨 · 안쪽 사전(``entry``) · 번호 필드를 가진 일반 칸. 매번 새 사전이다."""
    return {
        "bar": bar,
        "label": label or f"칸 {bar}",
        "entry": {"trigger_beat": 1},
        "color_preset_no": bar * 10,
        **fields,
    }


def _row(*bars: int) -> list[dict]:
    return [_cue(bar) for bar in bars]


def _bars(cues: list[dict]) -> list[int]:
    return [cue["bar"] for cue in cues]


def _without_bar(cue: dict) -> dict:
    return {key: value for key, value in cue.items() if key != "bar"}


# == 만들기 ===========================================================================


class TestRowCreate:
    def test_a_bar_inside_a_held_cell_copies_the_previous_cell(self) -> None:
        cues = [_cue(1, "A"), _cue(5, "B")]
        new = row_create(cues, 3)
        assert new["bar"] == 3
        assert _without_bar(new) == _without_bar(cues[0])

    @pytest.mark.parametrize(
        ("bar", "source_label"),
        [(2, "A"), (4, "A"), (6, "B"), (99, "B")],
        ids=["just-after-A", "just-before-B", "just-after-B", "far-after-the-last-cell"],
    )
    def test_the_source_is_the_cell_that_covers_the_bar(self, bar: int, source_label: str) -> None:
        cues = [_cue(1, "A"), _cue(5, "B")]
        assert row_create(cues, bar)["label"] == source_label

    @pytest.mark.parametrize(
        "later_bars",
        [(), (9,), (9, 14)],
        ids=["only-cell", "one-later-cell", "two-later-cells"],
    )
    def test_a_bar_in_the_lead_gap_copies_the_first_cell(self, later_bars: tuple[int, ...]) -> None:
        cues = [_cue(4, "B"), *(_cue(bar) for bar in later_bars)]
        new = row_create(cues, 2)
        assert new["bar"] == 2
        assert _without_bar(new) == _without_bar(cues[0])

    @pytest.mark.parametrize("bar", [1, 5])
    def test_a_bar_where_a_cell_already_starts_is_refused(self, bar: int) -> None:
        with pytest.raises(BeatGridCellEditError):
            row_create([_cue(1, "A"), _cue(5, "B")], bar)

    def test_an_empty_row_has_nothing_to_copy_from(self) -> None:
        with pytest.raises(BeatGridCellEditError):
            row_create([], 3)

    @pytest.mark.parametrize("bar", [0, -1])
    def test_a_bar_below_one_is_refused_even_inside_the_lead_gap(self, bar: int) -> None:
        with pytest.raises(BeatGridCellEditError):
            row_create([_cue(1, "A"), _cue(5, "B")], bar)

    def test_the_copy_is_independent_of_the_source(self) -> None:
        cues = [_cue(1, "A"), _cue(5, "B")]
        before = copy.deepcopy(cues)
        new = row_create(cues, 3)
        assert cues == before
        new["entry"]["trigger_beat"] = 99
        new["label"] = "changed"
        assert cues == before

    def test_evidence_is_kept_exactly_so_the_copy_is_not_newly_pending(self) -> None:
        evidence = {
            "grade": "A",
            "approval": {"by": "supervisor", "date": "2026-10-01", "source": "console"},
        }
        expected = copy.deepcopy(evidence)
        cues = [_cue(1, "A", evidence=evidence), _cue(5, "B")]
        new = row_create(cues, 3)
        assert new["evidence"] == expected
        new["evidence"]["approval"]["by"] = "someone else"
        assert cues[0]["evidence"] == expected

    @pytest.mark.parametrize(
        ("bars_given", "bar", "source_bar"),
        [
            pytest.param((9, 1, 5), 3, 1, id="split-the-first-cell"),
            pytest.param((9, 1, 5), 7, 5, id="split-the-middle-cell"),
            pytest.param((9, 1, 5), 12, 9, id="after-the-last-cell"),
            pytest.param((9, 5), 2, 5, id="lead-gap-takes-the-earliest-not-the-first-listed"),
        ],
    )
    def test_the_source_does_not_depend_on_the_order_given(
        self, bars_given: tuple[int, ...], bar: int, source_bar: int
    ) -> None:
        cues = [_cue(given) for given in bars_given]
        source = next(cue for cue in cues if cue["bar"] == source_bar)
        new = row_create(cues, bar)
        assert new["bar"] == bar
        assert _without_bar(new) == _without_bar(source)


# == 옮기기 ===========================================================================


class TestRowMove:
    def test_move_changes_only_the_bar_and_keeps_the_order(self) -> None:
        cues = _row(1, 5, 9)
        before = copy.deepcopy(cues)
        out = row_move(cues, 5, 7)
        assert _bars(out) == [1, 7, 9]
        assert _without_bar(out[1]) == _without_bar(before[1])
        assert cues == before

    def test_move_sorts_whatever_order_it_is_given(self) -> None:
        assert _bars(row_move([_cue(9), _cue(1), _cue(5)], 5, 7)) == [1, 7, 9]

    @pytest.mark.parametrize(
        ("from_bar", "to_bar"),
        [
            pytest.param(5, 1, id="onto-the-previous-cell"),
            pytest.param(5, 9, id="onto-the-next-cell"),
            pytest.param(5, 10, id="past-the-next-cell"),
            pytest.param(9, 3, id="past-the-previous-cell-onto-a-free-bar"),
            pytest.param(6, 7, id="no-cell-starts-at-from"),
            pytest.param(5, 5, id="same-bar"),
            pytest.param(1, 0, id="below-one"),
        ],
    )
    def test_a_refused_move_leaves_the_input_alone(self, from_bar: int, to_bar: int) -> None:
        cues = _row(1, 5, 9)
        before = copy.deepcopy(cues)
        with pytest.raises(BeatGridCellEditError):
            row_move(cues, from_bar, to_bar)
        assert cues == before

    def test_crossing_is_judged_by_bar_order_not_by_list_order(self) -> None:
        with pytest.raises(BeatGridCellEditError):
            row_move([_cue(9), _cue(1), _cue(5)], 5, 10)

    @pytest.mark.parametrize("to_bar", [1, 2, 6])
    def test_the_first_cell_may_move_into_the_lead_gap_or_up_to_the_next_cell(
        self, to_bar: int
    ) -> None:
        assert _bars(row_move(_row(3, 7), 3, to_bar)) == [to_bar, 7]

    def test_the_last_cell_may_move_any_distance_later(self) -> None:
        assert _bars(row_move(_row(1, 5, 9), 9, 50)) == [1, 5, 50]


# == 지우기 ===========================================================================


class TestRowDelete:
    def test_delete_removes_only_the_cell_that_starts_at_the_bar(self) -> None:
        cues = _row(1, 5, 9)
        before = copy.deepcopy(cues)
        assert row_delete(cues, 5) == [before[0], before[2]]
        assert row_delete(cues, 1) == [before[1], before[2]]
        assert cues == before

    @pytest.mark.parametrize("cues", [[], _row(1, 5, 9)], ids=["empty-row", "no-cell-there"])
    def test_delete_refuses_when_no_cell_starts_at_the_bar(self, cues: list[dict]) -> None:
        with pytest.raises(BeatGridCellEditError):
            row_delete(cues, 6)

    def test_delete_sorts_whatever_order_it_is_given(self) -> None:
        assert _bars(row_delete([_cue(9), _cue(1), _cue(5)], 5)) == [1, 9]


# == 거절 메시지 · 모듈 경계 ===========================================================

_REFUSALS = [
    pytest.param(lambda: row_create(_row(1, 5), 0), id="create-below-one"),
    pytest.param(lambda: row_create([], 3), id="create-empty-row"),
    pytest.param(lambda: row_create(_row(1, 5), 5), id="create-occupied"),
    pytest.param(lambda: row_move(_row(1, 5, 9), 1, 0), id="move-below-one"),
    pytest.param(lambda: row_move(_row(1, 5, 9), 5, 5), id="move-same-bar"),
    pytest.param(lambda: row_move(_row(1, 5, 9), 6, 7), id="move-no-cell"),
    pytest.param(lambda: row_move(_row(1, 5, 9), 5, 9), id="move-occupied"),
    pytest.param(lambda: row_move(_row(1, 5, 9), 5, 10), id="move-crossing"),
    pytest.param(lambda: row_delete(_row(1, 5, 9), 6), id="delete-no-cell"),
]


def _imported_modules(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class TestContract:
    def test_the_error_is_a_value_error(self) -> None:
        assert issubclass(BeatGridCellEditError, ValueError)

    @pytest.mark.parametrize("refuse", _REFUSALS)
    def test_every_refusal_is_a_korean_sentence_for_the_operator(self, refuse) -> None:
        with pytest.raises(BeatGridCellEditError) as caught:
            refuse()
        assert HANGUL.search(str(caught.value))

    def test_the_module_reaches_neither_web_nor_safety(self) -> None:
        imported = _imported_modules(inspect.getsource(cell_edit_module))
        assert not [name for name in imported if name.startswith(("server.web", "server.safety"))]
