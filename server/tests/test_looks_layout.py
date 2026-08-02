"""Executor layout planner (T-F) — pure-module unit tests.

Covers the three claims the task text asks for machine evidence on: (1) the
slot -> console-real-executor-number conversion (the "실행기 번호 함정"), (2)
deterministic, testable ordering, and (3) that the generated command bundle
never uses anything beyond the two rulebook-validated forms.
"""

from __future__ import annotations

import re

import pytest

from server.looks.layout import (
    OCCUPIED,
    PAGE_CAPACITY_EXHAUSTED,
    SEQUENCE_NOT_PROVIDED,
    UNCONFIRMED,
    build_layout_commands,
    console_executor_no,
    mark_occupancy_conflicts,
    plan_layout,
)
from server.tests.busking_fixtures import make_bundle, make_look

_ROCK_LOOKS = (
    make_look("intro", "Intro Wash", dynamics=1),
    make_look("verse", "Verse Groove", dynamics=2),
    make_look("chorus", "Chorus Burst", dynamics=4),
)


def _bundle():
    return make_bundle(_ROCK_LOOKS, genre="rock")


# -- console_executor_no — the "실행기 번호 함정" conversion ---------------------


class TestConsoleExecutorNo:
    def test_page1_slot1_is_101(self):
        assert console_executor_no(1, 1) == 101

    def test_page1_slot8_is_108(self):
        assert console_executor_no(1, 8) == 108

    def test_the_slot_index_is_never_the_address(self):
        # The exact defect SHOWUI-001 measured: slot 1 must NOT collide with
        # console object "1" (which live-measurement showed fires an
        # unrelated executor with no console error).
        for slot in range(1, 9):
            assert console_executor_no(1, slot) != slot

    def test_page2_slot1_is_201(self):
        assert console_executor_no(2, 1) == 201

    @pytest.mark.parametrize("page_no,slot_no", [(0, 1), (1, 0), (-1, 1), (1, -1)])
    def test_rejects_non_positive_inputs(self, page_no, slot_no):
        with pytest.raises(ValueError):
            console_executor_no(page_no, slot_no)

    def test_rejects_bool_masquerading_as_int(self):
        with pytest.raises(ValueError):
            console_executor_no(True, 1)


# -- plan_layout — deterministic placement --------------------------------------


class TestPlanLayoutOrdering:
    def test_items_preserve_the_bundle_look_order(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12, "chorus": 13})
        assert [item.look_id for item in plan.items] == [look.look_id for look in bundle.looks]

    def test_slots_and_executor_numbers_are_sequential_from_start_slot(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12, "chorus": 13}, start_slot=3)
        assert [item.slot for item in plan.items] == [3, 4, 5]
        assert [item.executor_no for item in plan.items] == [103, 104, 105]

    def test_two_calls_with_the_same_input_produce_the_same_plan(self):
        bundle = _bundle()
        numbers = {"intro": 11, "verse": 12, "chorus": 13}
        first = plan_layout(bundle, numbers)
        second = plan_layout(bundle, numbers)
        assert first == second

    def test_labels_are_ascii_sanitised(self):
        bundle = make_bundle((make_look("kr", "따뜻한 앰버", dynamics=1),), genre="rock")
        plan = plan_layout(bundle, {"kr": 21})
        assert plan.items[0].label
        assert "'" not in plan.items[0].label
        plan.items[0].label.encode("ascii")  # raises if non-ascii survived


class TestPlanLayoutSkips:
    def test_missing_sequence_number_is_skipped_not_guessed(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "chorus": 13})  # "verse" omitted
        assert [item.look_id for item in plan.items] == ["intro", "chorus"]
        assert len(plan.skipped) == 1
        assert plan.skipped[0].look_id == "verse"
        assert plan.skipped[0].reason == SEQUENCE_NOT_PROVIDED

    def test_page_capacity_exhaustion_skips_the_overflow(self):
        bundle = _bundle()
        plan = plan_layout(
            bundle, {"intro": 11, "verse": 12, "chorus": 13}, page_capacity=2
        )
        assert [item.look_id for item in plan.items] == ["intro", "verse"]
        assert len(plan.skipped) == 1
        assert plan.skipped[0].look_id == "chorus"
        assert plan.skipped[0].reason == PAGE_CAPACITY_EXHAUSTED

    def test_complete_is_false_when_anything_was_skipped(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12, "chorus": 13}, page_capacity=1)
        assert plan.complete is False

    def test_complete_is_true_when_every_look_landed(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12, "chorus": 13})
        assert plan.complete is True

    def test_empty_bundle_is_not_complete(self):
        bundle = make_bundle((), genre="rock")
        plan = plan_layout(bundle, {})
        assert plan.items == ()
        assert plan.complete is False


# -- mark_occupancy_conflicts — task item 4 --------------------------------------


def _executor_state(sequence_no: int | None) -> dict:
    node: dict = {}
    if sequence_no is not None:
        node["sequenceNo"] = sequence_no
    return {"node": node}


class TestMarkOccupancyConflicts:
    def test_an_assigned_executor_is_flagged_occupied(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12, "chorus": 13})
        target = plan.items[0].executor_no
        marked = mark_occupancy_conflicts(plan, {target: _executor_state(99)})
        assert marked.items[0].conflict is True
        assert marked.items[0].conflict_reason == OCCUPIED
        assert "99" in marked.items[0].conflict_detail

    def test_an_unassigned_executor_is_not_a_conflict(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11})
        target = plan.items[0].executor_no
        marked = mark_occupancy_conflicts(plan, {target: _executor_state(None)})
        assert marked.items[0].conflict is False

    def test_a_never_queried_executor_is_unconfirmed_not_free(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11})
        marked = mark_occupancy_conflicts(plan, {})  # nothing fetched
        assert marked.items[0].conflict is True
        assert marked.items[0].conflict_reason == UNCONFIRMED

    def test_marking_never_drops_or_reorders_items(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12, "chorus": 13})
        marked = mark_occupancy_conflicts(plan, {})
        assert [item.look_id for item in marked.items] == [item.look_id for item in plan.items]
        assert len(marked.items) == len(plan.items)


# -- build_layout_commands — rulebook-validated forms only -----------------------

_ASSIGN = re.compile(r"^Assign Sequence \d+ At Executor \d+$")
_LABEL_SEQUENCE = re.compile(r"^Label Sequence \d+ '.*'$")
_FORBIDDEN = re.compile(r"Label Executor|/trig=|/Overwrite|/overwrite", re.IGNORECASE)
_DOTTED = re.compile(r"\b(?:Page|Executor)\s+\d+\.\d+")


class TestBuildLayoutCommandsShape:
    def test_emits_only_the_two_validated_forms(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12, "chorus": 13})
        commands = build_layout_commands(plan)
        assert commands, "non-vacuity: the fixture bundle produces something"
        for command in commands:
            assert _ASSIGN.match(command) or _LABEL_SEQUENCE.match(command), command

    def test_never_emits_a_forbidden_or_dotted_form(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12, "chorus": 13})
        commands = build_layout_commands(plan)
        offenders = [c for c in commands if _FORBIDDEN.search(c) or _DOTTED.search(c)]
        assert offenders == []

    def test_the_forbidden_scan_would_catch_a_planted_violation(self):
        # Non-vacuity control for the two scans above.
        planted = ["Label Executor 101 'x'", "Assign Sequence 3 At Page 1.101"]
        assert all(_FORBIDDEN.search(c) or _DOTTED.search(c) for c in planted)

    def test_assign_precedes_label_for_each_item(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12})
        commands = build_layout_commands(plan)
        assert commands[0].startswith("Assign Sequence 11 At Executor")
        assert commands[1].startswith("Label Sequence 11 '")
        assert commands[2].startswith("Assign Sequence 12 At Executor")
        assert commands[3].startswith("Label Sequence 12 '")

    def test_conflicted_items_never_generate_commands(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11, "verse": 12})
        occupied_target, free_target = plan.items[0].executor_no, plan.items[1].executor_no
        conflicted = mark_occupancy_conflicts(
            plan, {occupied_target: _executor_state(1), free_target: _executor_state(None)}
        )
        commands = build_layout_commands(conflicted)
        assert not any("Sequence 11" in c for c in commands)
        assert any("Sequence 12" in c for c in commands)

    def test_all_conflicted_yields_an_empty_bundle_not_an_error(self):
        bundle = _bundle()
        plan = plan_layout(bundle, {"intro": 11})
        target = plan.items[0].executor_no
        conflicted = mark_occupancy_conflicts(plan, {target: _executor_state(1)})
        assert build_layout_commands(conflicted) == ()
