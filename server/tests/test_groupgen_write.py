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
    DEFAULT_GROUP_PLAN_CAP,
    FIXTURE_LIST_TRUNCATED,
    GROUP_PLAN_TOO_LARGE,
    GROUP_POOL_TRUNCATED,
    GROUP_POOL_UNAVAILABLE,
    GROUP_SLOT_OCCUPIED,
    GroupSlotError,
    build_group_write_plan,
    guard_fixture_list_truncation,
    guard_plan_size,
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


def test_build_group_write_plan_proceeds_on_truncated_fixture_list() -> None:
    """REQ-GROUPGEN-024 amendment (2026-08-04, user decision): the write path
    consumes caller-supplied ``fids``, not the re-queried fixture listing —
    a truncated listing (39-fixture rig, 18 returned) never blocks an
    explicit-fids group write. This is a LIVE-shape regression: the scenario
    is exactly ``{"ok": True, "truncated": True, "objects": [18 entries]}``
    against a rig whose real ``childCount`` is 39."""
    live_shape_truncated_fixtures = {"ok": True, "truncated": True, "childCount": 39}
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=live_shape_truncated_fixtures,
    )
    assert len(plan.steps) == 1
    assert plan.steps[0].fids == (1, 2)


def test_build_group_write_plan_structurally_flags_fixture_list_truncation() -> None:
    """Mutation-required: removing the population of ``fixture_list_truncated``
    on the returned plan must turn this test RED — the fact is a STRUCTURAL
    field, never docstring-only prose (함정 6)."""
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=TRUNCATED_FIXTURES_SECTION,
    )
    assert plan.fixture_list_truncated is True
    assert plan.fixture_list_truncated_reason  # non-empty human-readable string


def test_build_group_write_plan_flags_no_truncation_when_list_was_complete() -> None:
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    assert plan.fixture_list_truncated is False
    assert plan.fixture_list_truncated_reason == ""


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


# -- guard_plan_size / grid slot-explosion cap (D-Q6 discipline: reject, ------
#    never warn-and-proceed; never silently truncate) -------------------------


def _wide_grid_buckets(depth: int, lateral: int) -> dict[str, tuple[int, ...]]:
    """A synthetic axis-separated grid bucket set (design.md §D-Q2): depth +
    lateral buckets, ``depth + lateral`` groups total — one fixture per
    bucket is enough, only the bucket *count* matters for the cap."""
    fid = 1
    buckets: dict[str, tuple[int, ...]] = {}
    for i in range(depth):
        buckets[f"depth{i}"] = (fid,)
        fid += 1
    for i in range(lateral):
        buckets[f"lateral{i}"] = (fid,)
        fid += 1
    return buckets


def test_guard_plan_size_accepts_a_request_at_or_below_the_cap() -> None:
    guard_plan_size(DEFAULT_GROUP_PLAN_CAP, cap=DEFAULT_GROUP_PLAN_CAP)  # must not raise


def test_guard_plan_size_rejects_a_request_above_the_cap() -> None:
    with pytest.raises(GroupSlotError) as excinfo:
        guard_plan_size(DEFAULT_GROUP_PLAN_CAP + 1, cap=DEFAULT_GROUP_PLAN_CAP)
    assert excinfo.value.code == GROUP_PLAN_TOO_LARGE
    # error message states what the caller needs and what the cap is
    assert str(DEFAULT_GROUP_PLAN_CAP + 1) in excinfo.value.message
    assert str(DEFAULT_GROUP_PLAN_CAP) in excinfo.value.message


def test_3x10_grid_axis_separated_groups_pass_under_the_default_cap() -> None:
    """3x10 그리드(축별 분리 3+10=13그룹, design.md §D-Q2) — 기본 상한(16) 이하이므로
    거부 없이 전량 발화된다. 이 테스트 이름/독스트링이 곧 '통과가 의도'라는 명세다.
    """
    buckets = _wide_grid_buckets(depth=3, lateral=10)
    names = {key: f"GEO Bucket {key}" for key in buckets}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    assert len(buckets) == 13
    # 조용한 절단 0: 계획의 step 수 == 요청된 버킷 수 == 할당 슬롯 수.
    assert len(plan.steps) == len(buckets)
    assert len({step.slot for step in plan.steps}) == len(buckets)


def test_5x20_grid_axis_separated_groups_are_rejected_by_the_default_cap() -> None:
    """5x20 그리드(축별 분리 5+20=25그룹) — 기본 상한(16)을 넘으므로 **거부**된다.
    이 테스트 이름/독스트링이 곧 '거부가 의도'라는 명세다 — 부분 계획으로 조용히
    절단하는 대신 GROUP_PLAN_TOO_LARGE 로 전량 거부한다(D-Q6 규율 계승).
    """
    buckets = _wide_grid_buckets(depth=5, lateral=20)
    names = {key: f"GEO Bucket {key}" for key in buckets}
    assert len(buckets) == 25
    with pytest.raises(GroupSlotError) as excinfo:
        build_group_write_plan(
            buckets=buckets,
            names=names,
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )
    assert excinfo.value.code == GROUP_PLAN_TOO_LARGE


def test_plan_size_cap_is_reachable_and_never_silently_truncates() -> None:
    """A plan above the DEFAULT cap must be entirely refused, never demoted to
    a partial plan covering only the first ``cap`` buckets — mutating
    ``build_group_write_plan`` to silently slice ``buckets`` to ``cap`` and
    proceed would make this RED (no exception, and the plan would carry a
    step count smaller than the requested bucket count, both of which the
    surrounding cap tests already pin)."""
    buckets = _wide_grid_buckets(depth=5, lateral=20)
    names = {key: f"GEO Bucket {key}" for key in buckets}
    with pytest.raises(GroupSlotError):
        build_group_write_plan(
            buckets=buckets,
            names=names,
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )


def test_max_plan_size_is_an_explicit_per_call_override() -> None:
    """The cap is a policy DEFAULT, not a ceiling baked into the code — a
    caller may explicitly raise it for one call (design.md-mandated
    keyword-only override on build_group_write_plan)."""
    buckets = _wide_grid_buckets(depth=5, lateral=20)
    names = {key: f"GEO Bucket {key}" for key in buckets}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        max_plan_size=30,
    )
    assert len(plan.steps) == len(buckets) == 25
