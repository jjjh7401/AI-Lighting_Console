"""RED-GREEN-REFACTOR coverage for server/groupgen/write.py (design.md §6).

The measured pool fixture below is the M0 live-probe result
(progress.md §E.2.3): occupied slots {1, 11, 12, 13, 15}, empty
{2..10, 14, 16+}, truncated:false.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from server.groupgen.write import (
    FIXTURE_LIST_TRUNCATED,
    GROUP_POOL_TRUNCATED,
    GROUP_POOL_UNAVAILABLE,
    GROUP_SLOT_OCCUPIED,
    GroupSlotError,
    build_group_write_plan,
    guard_fixture_list_truncation,
    measure_empty_slots,
    select_group_slot,
)

MEASURED_GROUPS_SECTION = {
    "ok": True,
    "truncated": False,
    "objects": [{"no": n} for n in (1, 11, 12, 13, 15)],
}
MEASURED_OCCUPIED = frozenset({1, 11, 12, 13, 15})

UNTRUNCATED_FIXTURES_SECTION = {"ok": True, "truncated": False, "childCount": 19}
TRUNCATED_FIXTURES_SECTION = {"ok": True, "truncated": True, "childCount": 19}


# -- select_group_slot -------------------------------------------------------


@pytest.mark.parametrize("occupied", sorted(MEASURED_OCCUPIED))
def test_select_group_slot_statically_blocks_every_occupied_slot(occupied: int) -> None:
    with pytest.raises(GroupSlotError) as excinfo:
        select_group_slot(MEASURED_GROUPS_SECTION, requested=occupied)
    assert excinfo.value.code == GROUP_SLOT_OCCUPIED


def test_select_group_slot_accepts_a_measured_empty_slot() -> None:
    assert select_group_slot(MEASURED_GROUPS_SECTION, requested=2) == 2
    assert select_group_slot(MEASURED_GROUPS_SECTION, requested=14) == 14


def test_select_group_slot_rejects_truncated_pool() -> None:
    truncated = {"ok": True, "truncated": True, "objects": []}
    with pytest.raises(GroupSlotError) as excinfo:
        select_group_slot(truncated, requested=2)
    assert excinfo.value.code == GROUP_POOL_TRUNCATED


def test_select_group_slot_rejects_unreadable_pool() -> None:
    unreadable = {"ok": False, "reason": "timeout"}
    with pytest.raises(GroupSlotError) as excinfo:
        select_group_slot(unreadable, requested=2)
    assert excinfo.value.code == GROUP_POOL_UNAVAILABLE


# -- measure_empty_slots ------------------------------------------------------


def test_measure_empty_slots_matches_the_measured_noncontiguous_pool() -> None:
    assert measure_empty_slots(MEASURED_GROUPS_SECTION, count=12) == (
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        14,
        16,
        17,
    )


def test_measure_empty_slots_never_returns_an_occupied_slot() -> None:
    measured = measure_empty_slots(MEASURED_GROUPS_SECTION, count=20)
    assert MEASURED_OCCUPIED.isdisjoint(measured)


def test_measure_empty_slots_rejects_truncated_pool() -> None:
    truncated = {"ok": True, "truncated": True, "objects": []}
    with pytest.raises(GroupSlotError) as excinfo:
        measure_empty_slots(truncated, count=1)
    assert excinfo.value.code == GROUP_POOL_TRUNCATED


def test_measure_empty_slots_rejects_unreadable_pool() -> None:
    unreadable = {"reason": "no response"}
    with pytest.raises(GroupSlotError) as excinfo:
        measure_empty_slots(unreadable, count=1)
    assert excinfo.value.code == GROUP_POOL_UNAVAILABLE


# -- guard_fixture_list_truncation -------------------------------------------


def test_guard_fixture_list_truncation_rejects_truncated_list() -> None:
    with pytest.raises(GroupSlotError) as excinfo:
        guard_fixture_list_truncation(TRUNCATED_FIXTURES_SECTION)
    assert excinfo.value.code == FIXTURE_LIST_TRUNCATED


def test_guard_fixture_list_truncation_passes_untruncated_list() -> None:
    guard_fixture_list_truncation(UNTRUNCATED_FIXTURES_SECTION)  # must not raise


# -- build_group_write_plan ---------------------------------------------------


def test_build_group_write_plan_happy_path_emits_the_fixed_chain() -> None:
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert step.slot == 2  # first measured empty slot
    assert step.fids == (1, 2)
    assert step.commands == (
        "ClearAll",
        "Fixture 1 + Fixture 2",
        "Store Group 2",
        "Label Group 2 'GEO Downstage'",
        "ClearAll",
    )
    assert step.verification == (
        "state DataPool/Groups/2",
        "prop DataPool/Groups/2 Name",
    )


def test_build_group_write_plan_always_flags_membership_unverified() -> None:
    plan = build_group_write_plan(
        buckets={"a": (1,)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    assert plan.unverified == ("membership",)
    assert plan.unverified_reason  # non-empty human-readable string
    assert plan.human_check_commands == ("Group 2",)


def test_build_group_write_plan_rejects_truncated_fixture_list() -> None:
    with pytest.raises(GroupSlotError) as excinfo:
        build_group_write_plan(
            buckets={"a": (1, 2)},
            names={"a": "GEO Downstage"},
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=TRUNCATED_FIXTURES_SECTION,
        )
    assert excinfo.value.code == FIXTURE_LIST_TRUNCATED


def test_build_group_write_plan_rejects_truncated_group_pool() -> None:
    truncated_pool = {"ok": True, "truncated": True, "objects": []}
    with pytest.raises(GroupSlotError) as excinfo:
        build_group_write_plan(
            buckets={"a": (1, 2)},
            names={"a": "GEO Downstage"},
            groups_section=truncated_pool,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )
    assert excinfo.value.code == GROUP_POOL_TRUNCATED


def test_build_group_write_plan_never_targets_an_occupied_slot() -> None:
    buckets = {f"b{i}": (i,) for i in range(1, 13)}
    names = {key: f"Bucket {key}" for key in buckets}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    written_slots = {step.slot for step in plan.steps}
    assert written_slots.isdisjoint(MEASURED_OCCUPIED)


def test_write_scope_matches_measured_empty_slots_exactly() -> None:
    """§6.5 정적 단언 — 발화 슬롯 집합 == 실측 빈 슬롯 집합."""
    buckets = {f"b{i}": (i,) for i in range(1, 5)}
    names = {key: f"Bucket {key}" for key in buckets}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    written_slot_numbers = {
        int(match.group(1))
        for step in plan.steps
        for command in step.commands
        if (match := re.fullmatch(r"Store Group (\d+)", command))
    }
    expected = set(measure_empty_slots(MEASURED_GROUPS_SECTION, count=len(buckets)))
    assert written_slot_numbers == expected


def test_no_double_quote_appears_in_any_emitted_command() -> None:
    plan = build_group_write_plan(
        buckets={"a": (1, 2, 3)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    for step in plan.steps:
        for command in step.commands:
            assert '"' not in command


def test_label_name_with_single_quote_has_pinned_behavior() -> None:
    """No escape convention exists (00_grammar.md:66) — refusal is pinned."""
    with pytest.raises(ValueError):
        build_group_write_plan(
            buckets={"a": (1,)},
            names={"a": "GEO O'Brien"},
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )


def test_label_name_with_double_quote_has_pinned_behavior() -> None:
    with pytest.raises(ValueError):
        build_group_write_plan(
            buckets={"a": (1,)},
            names={"a": 'GEO "Downstage"'},
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )


# -- layering: no transport / safety import ----------------------------------


def test_module_source_imports_no_transport_or_safety() -> None:
    source = Path("server/groupgen/write.py").read_text(encoding="utf-8")
    assert not re.search(r"\bserver\.bridge\b", source)
    assert not re.search(r"\bpythonosc\b", source)
    assert not re.search(r"\bserver\.safety\b", source)
