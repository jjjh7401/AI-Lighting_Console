"""PRECHK patch consistency tests (AC-PRECHK-005 · 006 · 007 · 008 · 009).

The rigs live in ``test_prechk_inventory.py`` because they are port doubles for
the inventory reader; this module drives them through the judgement.

Every rig here is SYNTHETIC. A consistent rig alone proves nothing -- all
verdicts converge on "nothing wrong", which is what a scanner that never fires
also produces -- so each defect class is planted deliberately and the live
session is left to show only the absence of false positives.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from server.prechk.footprint import ModeFootprint, WalkOutcome
from server.prechk.inventory import (
    COMPLETE,
    INCOMPLETE,
    PROPERTY_UNREADABLE,
    SHAPE_INVALID,
    read_inventory,
)
from server.prechk.patch import (
    ADDRESS_DUPLICATE,
    ADDRESS_PARSE_FAILED,
    ASSUMPTION_27,
    BOUND_INCONCLUSIVE,
    BOUND_PROVES_CLEAR,
    COLLISION,
    EXACT_WIDTHS,
    NOT_ASSESSED,
    NOT_PERFORMED,
    OBSERVED_CLEAR,
    RANGE_OVERLAP,
    RANGE_OVERLAP_BOUND_INCONCLUSIVE,
    RANGE_OVERLAP_DESCOPE,
    READ_FAILED,
    SCOPE_QUALIFIER,
    TYPE_MODE_UNRESOLVED,
    FootprintPolicy,
    evaluate_patch,
    normalize_address,
)
from server.prechk.verdicts import (
    COLLISION_KIND,
    FIXTURE_VERDICT,
    OVERLAP_BASIS,
    READ_FAILURE_KIND,
    SKIPPED_CHECK_KIND,
)

from .test_prechk_inventory import (
    FOOTPRINT_SOURCE,
    MEASURED_FUNCTION_REF,
    RANGE_OVERLAP_WIDTHS,
    UNREADABLE,
    FixturePool,
    bad_patch_value,
    clean_rig_18,
    duplicate_address_pair,
    duplicate_address_triple,
    fixture_props,
    function_ref_property,
    none_string_property,
    range_descope,
    range_overlap_go,
    same_address_other_universe,
    truncated_parent,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: The injected footprint that turns the range-overlap branch on. The width 29
#: is the measured ``DMXChannels`` child count; the LINKAGE from a fixture to it
#: is what ``ASSUMPTION-27`` refuted, so a caller supplies it.
GO_FOOTPRINT = FootprintPolicy(enabled=True, widths=RANGE_OVERLAP_WIDTHS, source=FOOTPRINT_SOURCE)

# Field names that assert something the pre-check cannot observe.
_VACUOUS_ASSERTION = re.compile(
    r"verified|all_clear|no_conflict|responded|fixture_ok|patch_ok|proven", re.IGNORECASE
)


def _keys(payload) -> list[str]:
    """Every key in a nested payload, so a scan cannot miss a buried field."""
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.append(str(key))
            found.extend(_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(_keys(item))
    return found


class TestAddressNormalization:
    """AC-PRECHK-005 — two integers, or a parse failure with no default."""

    def test_the_measured_samples_become_integer_pairs(self):
        for raw, expected in (("1.001", (1, 1)), ("2.351", (2, 351)), ("2.401", (2, 401))):
            parse = normalize_address(raw)
            assert parse.ok, raw
            assert (parse.universe, parse.address) == expected

    @pytest.mark.parametrize(
        "raw", ["", "abc", "1", "1.2.3", "   ", "1.", ".1", "-1.5", "1,001", "1.a"]
    )
    def test_an_unparseable_value_is_never_filled_with_a_default(self, raw):
        parse = normalize_address(raw)
        assert parse.ok is False
        # No 0, no 1: a fabricated default would collide with a real address.
        assert parse.universe is None
        assert parse.address is None
        assert parse.error

    def test_a_missing_value_is_a_parse_failure(self):
        parse = normalize_address(None)
        assert parse.ok is False
        assert (parse.universe, parse.address) == (None, None)

    def test_leading_zeros_do_not_change_the_address(self):
        assert normalize_address("1.001").address == 1
        assert normalize_address("1.1").address == 1
        assert normalize_address("1.001").universe == normalize_address("1.1").universe

    def test_duplicates_are_matched_on_integers_not_strings(self):
        pool = FixturePool(
            {
                1: fixture_props("1.001", name="정수 A"),
                2: fixture_props("1.1", name="정수 B"),
            }
        )
        evaluation = evaluate_patch(read_inventory(pool))
        assert len(evaluation.address_duplicates) == 1
        assert [m.slot for m in evaluation.address_duplicates[0].members] == [1, 2]

    @pytest.mark.parametrize("raw", ["abc", "1", "1.2.3"])
    def test_a_pipeline_parse_failure_is_its_own_class(self, raw):
        evaluation = evaluate_patch(read_inventory(bad_patch_value(raw)))
        rows = {row.record.slot: row for row in evaluation.rows}
        assert rows[1].universe is None
        assert rows[1].address is None
        assert rows[1].verdict == READ_FAILED
        assert ADDRESS_PARSE_FAILED in rows[1].reasons
        assert [f.kind for f in evaluation.read_failures if f.slot == 1] == [ADDRESS_PARSE_FAILED]
        assert rows[1].record.patch_raw == raw, "원문은 보존한다"
        # Non-vacuity: the sibling fixture is still judged normally.
        assert rows[2].verdict == OBSERVED_CLEAR
        payload = json.dumps(rows[1].to_dict(), ensure_ascii=False)
        assert '"universe": null' in payload
        assert '"address": null' in payload

    def test_an_empty_patch_value_is_caught_by_the_shape_gate_first(self):
        evaluation = evaluate_patch(read_inventory(bad_patch_value("")))
        assert [f.kind for f in evaluation.read_failures if f.slot == 1] == [SHAPE_INVALID]
        # The parser rejects it too; the classes stay distinct because the shape
        # gate runs first and the report must name the actual fault.
        assert normalize_address("").ok is False


class TestAddressDuplicates:
    """AC-PRECHK-006 — one collision per shared start point, all members named."""

    def test_a_pair_is_one_collision_carrying_both_members(self):
        evaluation = evaluate_patch(read_inventory(duplicate_address_pair()))
        assert len(evaluation.address_duplicates) == 1
        collision = evaluation.address_duplicates[0]
        assert collision.kind == ADDRESS_DUPLICATE
        assert (collision.universe, collision.address) == (1, 10)
        assert [(m.slot, m.name) for m in collision.members] == [(1, "워시 1"), (2, "워시 2")]
        rows = {row.record.slot: row for row in evaluation.rows}
        assert rows[1].verdict == COLLISION
        assert rows[2].verdict == COLLISION
        assert ADDRESS_DUPLICATE in rows[1].reasons
        # Non-vacuity: the unique fixture is not swept into the collision.
        assert rows[3].verdict == OBSERVED_CLEAR

    def test_three_at_one_address_is_one_collision_not_three_pairs(self):
        evaluation = evaluate_patch(read_inventory(duplicate_address_triple()))
        assert len(evaluation.address_duplicates) == 1
        assert [m.slot for m in evaluation.address_duplicates[0].members] == [1, 2, 3]
        assert evaluation.verdict_counts[COLLISION] == 3
        assert evaluation.verdict_counts[OBSERVED_CLEAR] == 1

    def test_the_same_address_in_another_universe_is_not_a_collision(self):
        evaluation = evaluate_patch(read_inventory(same_address_other_universe()))
        assert evaluation.address_duplicates == ()
        assert len(evaluation.rows) == 2
        assert {row.verdict for row in evaluation.rows} == {OBSERVED_CLEAR}
        assert {(row.universe, row.address) for row in evaluation.rows} == {(1, 1), (2, 1)}

    def test_a_consistent_rig_produces_no_false_positive(self):
        evaluation = evaluate_patch(read_inventory(clean_rig_18()))
        assert evaluation.address_duplicates == ()
        assert len(evaluation.rows) == 18
        assert evaluation.verdict_counts[OBSERVED_CLEAR] == 18
        assert evaluation.inventory.completeness == COMPLETE
        assert evaluation.scope_qualified is False

    def test_zero_collisions_on_a_truncated_rig_stays_qualified(self):
        evaluation = evaluate_patch(read_inventory(truncated_parent()))
        assert evaluation.address_duplicates == ()
        assert evaluation.inventory.completeness == INCOMPLETE
        assert evaluation.scope_qualified is True
        assert evaluation.verdict_counts[NOT_ASSESSED] == 22


class TestRangeOverlapBranches:
    """AC-PRECHK-007 — both branches are kept, and both actually run.

    ``ASSUMPTION-27`` is NEGATIVE, which refutes the LINKAGE from a fixture to
    its own footprint -- not the interval comparison. Footprints are a
    caller-injected input, so the GO branch is exercised in memory instead of
    being skipped: nothing is deleted, and nothing is asserted about a linkage
    that does not exist.
    """

    def test_the_go_branch_finds_the_overlap(self):
        evaluation = evaluate_patch(read_inventory(range_overlap_go()), GO_FOOTPRINT)
        assert GO_FOOTPRINT.widths, "점유폭 입력이 비면 GO 구간이 공허하다"
        assert len(evaluation.range_overlaps) == 1
        overlap = evaluation.range_overlaps[0]
        assert overlap.kind == RANGE_OVERLAP
        assert overlap.universe == 1
        assert [m.slot for m in overlap.members] == [1, 2]
        assert overlap.span == (1, 43)
        assert evaluation.skipped_checks == ()

    def test_the_go_branch_leaves_a_42_channel_gap_alone(self):
        evaluation = evaluate_patch(read_inventory(range_overlap_go()), GO_FOOTPRINT)
        involved = {m.slot for c in evaluation.range_overlaps for m in c.members}
        assert involved == {1, 2}
        rows = {row.record.slot: row for row in evaluation.rows}
        assert rows[3].address == 101
        assert rows[4].address == 143
        assert rows[3].verdict == OBSERVED_CLEAR
        assert rows[4].verdict == OBSERVED_CLEAR

    def test_the_negative_branch_performs_no_overlap_check_and_says_so(self):
        evaluation = evaluate_patch(read_inventory(range_descope()))
        assert evaluation.range_overlaps == ()
        skipped = [c for c in evaluation.skipped_checks if c.kind == RANGE_OVERLAP_DESCOPE]
        assert len(skipped) == 1
        assert skipped[0].assumption == ASSUMPTION_27
        assert skipped[0].reason
        assert set(skipped[0].to_dict()) == {"kind", "reason", "assumption"}

    def test_supplying_widths_without_enabling_the_axis_changes_nothing(self):
        policy = FootprintPolicy(enabled=False, widths=RANGE_OVERLAP_WIDTHS)
        evaluation = evaluate_patch(read_inventory(range_overlap_go()), policy)
        assert evaluation.range_overlaps == ()
        assert [c.kind for c in evaluation.skipped_checks] == [RANGE_OVERLAP_DESCOPE]

    def test_address_duplicates_run_in_either_branch(self):
        for policy in (None, GO_FOOTPRINT):
            evaluation = evaluate_patch(read_inventory(duplicate_address_pair()), policy)
            assert len(evaluation.address_duplicates) == 1
            assert [m.slot for m in evaluation.address_duplicates[0].members] == [1, 2]

    def test_a_fixture_with_an_unresolved_mode_is_left_out_of_the_overlap_check(self):
        pool = FixturePool(
            {
                1: fixture_props("1.001", name="폭 있음"),
                2: fixture_props("1.015", name="모드 불명", mode=UNREADABLE),
            }
        )
        evaluation = evaluate_patch(read_inventory(pool), GO_FOOTPRINT)
        assert evaluation.range_overlaps == ()
        rows = {row.record.slot: row for row in evaluation.rows}
        assert rows[2].verdict == READ_FAILED
        assert TYPE_MODE_UNRESOLVED in rows[2].reasons

    def test_a_fixture_with_no_width_is_announced_not_silently_excluded(self):
        # `_range_overlaps` drops a width-less fixture with a bare `continue`,
        # leaving no trace in `reasons`, `skipped_checks` or any row field — while
        # the sibling exclusion (unresolved mode, above) leaves a code AND drops
        # the verdict. So the fixture was never compared and the report called it
        # clear. `widths` carries no totality constraint and its designed source
        # is a per-type read that can fail: a PARTIAL map is a normal result.
        pool = FixturePool(
            {
                1: fixture_props("1.001", name="폭 있음"),
                2: fixture_props("1.011", name="폭 없음"),
                3: fixture_props("1.021", name="폭 없음 2"),
            }
        )
        policy = FootprintPolicy(enabled=True, widths={1: 29}, source="DMXChannels child count")
        evaluation = evaluate_patch(read_inventory(pool), policy)
        skipped = [c for c in evaluation.skipped_checks if c.kind == RANGE_OVERLAP_DESCOPE]
        assert len(skipped) == 1, (
            "two fixtures were never compared and the report said nothing: "
            f"{[c.kind for c in evaluation.skipped_checks]}"
        )
        assert "2" in skipped[0].reason and "3" in skipped[0].reason, skipped[0].reason

    def test_an_enabled_axis_with_no_widths_at_all_is_not_a_clean_bill(self):
        # The worst shape of the same defect: every fixture is excluded, zero
        # collisions are found, and without the notice the user reads that the
        # range-overlap check ran and the rig is clean.
        evaluation = evaluate_patch(
            read_inventory(range_overlap_go()), FootprintPolicy(enabled=True, widths={})
        )
        assert evaluation.range_overlaps == ()
        assert [c.kind for c in evaluation.skipped_checks] == [RANGE_OVERLAP_DESCOPE]

    def test_full_width_coverage_announces_nothing(self):
        # Non-vacuity: the notice must not fire whenever the axis is enabled.
        evaluation = evaluate_patch(read_inventory(range_overlap_go()), GO_FOOTPRINT)
        assert evaluation.skipped_checks == ()

    def test_the_descope_prefix_line_exists_in_progress(self):
        text = (
            PROJECT_ROOT / ".moai" / "specs" / "SPEC-COPILOT-PRECHK-001" / "progress.md"
        ).read_text(encoding="utf-8")
        lines = [
            line for line in text.splitlines() if line.startswith(f"DESCOPE: {ASSUMPTION_27} ")
        ]
        assert len(lines) == 1, "DESCOPE: ASSUMPTION-27 접두 행이 정확히 1건이어야 한다"


class TestReadFailureIsItsOwnClass:
    """AC-PRECHK-008 — neither consistent nor inconsistent, and never merged."""

    def test_a_type_read_failure_is_neither_clear_nor_a_collision(self):
        evaluation = evaluate_patch(read_inventory(function_ref_property()))
        rows = {row.record.slot: row for row in evaluation.rows}
        assert rows[3].verdict == READ_FAILED
        assert TYPE_MODE_UNRESOLVED in rows[3].reasons
        assert rows[1].verdict == READ_FAILED
        assert rows[2].verdict == OBSERVED_CLEAR
        counts = evaluation.verdict_counts
        assert (
            counts[OBSERVED_CLEAR] + counts[COLLISION] + counts[READ_FAILED]
            == evaluation.inventory.observed_count
        )
        assert counts[NOT_ASSESSED] == evaluation.inventory.missing_count

    def test_the_failure_classes_are_counted_separately(self):
        pool = FixturePool(
            {
                1: fixture_props(MEASURED_FUNCTION_REF, name="형태 불만족"),
                2: fixture_props("abc", name="주소 파싱 불가"),
                3: fixture_props("1.003", name="타입 판독 실패", fixture_type=UNREADABLE),
                4: fixture_props("1.004", name="정상"),
            }
        )
        evaluation = evaluate_patch(read_inventory(pool))
        counts = evaluation.read_failure_counts
        assert counts[SHAPE_INVALID] == 1
        assert counts[ADDRESS_PARSE_FAILED] == 1
        assert counts[PROPERTY_UNREADABLE] == 1
        # Distinct keys, not one merged bucket: the user action differs.
        assert set(counts) == set(READ_FAILURE_KIND)
        assert sum(counts.values()) == len(evaluation.read_failures) == 3
        rows = {row.record.slot: row for row in evaluation.rows}
        assert [rows[slot].verdict for slot in (1, 2, 3)] == [READ_FAILED] * 3
        assert rows[4].verdict == OBSERVED_CLEAR

    def test_no_read_failure_leaves_the_class_empty(self):
        evaluation = evaluate_patch(read_inventory(clean_rig_18()))
        assert len(evaluation.rows) == 18, "픽스처가 0개면 '판독 실패 0건'이 공허하다"
        assert evaluation.read_failures == ()
        assert set(evaluation.read_failure_counts.values()) == {0}

    def test_a_none_string_patch_is_excluded_from_the_judgement(self):
        evaluation = evaluate_patch(read_inventory(none_string_property()))
        rows = {row.record.slot: row for row in evaluation.rows}
        assert rows[1].verdict == READ_FAILED
        assert rows[1].universe is None
        assert SHAPE_INVALID in rows[1].reasons
        assert rows[2].verdict == OBSERVED_CLEAR

    def test_a_determined_collision_outranks_an_unreadable_sibling_property(self):
        pool = FixturePool(
            {
                1: fixture_props("1.010", name="중복 A"),
                2: fixture_props("1.010", name="중복 B", mode=UNREADABLE),
            }
        )
        evaluation = evaluate_patch(read_inventory(pool))
        rows = {row.record.slot: row for row in evaluation.rows}
        assert rows[2].verdict == COLLISION
        # The read failure is still reported -- it is not lost, only outranked.
        assert TYPE_MODE_UNRESOLVED in rows[2].reasons
        assert ADDRESS_DUPLICATE in rows[2].reasons
        assert [f.kind for f in evaluation.read_failures] == [PROPERTY_UNREADABLE]


class TestNoConsistencyClaimOnIncompleteReads:
    """AC-PRECHK-009 — zero collisions is not a consistency proof."""

    def test_an_incomplete_read_qualifies_the_result(self):
        evaluation = evaluate_patch(read_inventory(truncated_parent()))
        assert evaluation.inventory.completeness == INCOMPLETE
        assert evaluation.scope_qualified is True
        assert SCOPE_QUALIFIER in evaluation.scope_note
        assert str(evaluation.inventory.missing_count) in evaluation.scope_note
        assert evaluation.verdict_counts[NOT_ASSESSED] == 22

    def test_a_complete_read_with_no_collision_is_unqualified(self):
        evaluation = evaluate_patch(read_inventory(clean_rig_18()))
        assert evaluation.scope_qualified is False
        # Non-vacuity: the qualifier is not glued to every result.
        assert SCOPE_QUALIFIER not in evaluation.scope_note
        assert evaluation.verdict_counts[NOT_ASSESSED] == 0

    def test_recovery_does_not_lift_the_qualifier(self):
        evaluation = evaluate_patch(read_inventory(truncated_parent(hidden=(19, 20))))
        assert evaluation.inventory.recovered_count == 2
        assert evaluation.inventory.index_domain_unknown is True
        assert evaluation.scope_qualified is True
        assert SCOPE_QUALIFIER in evaluation.scope_note

    def test_the_payload_carries_no_vacuous_assertion_field(self):
        payload = evaluate_patch(read_inventory(clean_rig_18())).to_dict()
        keys = _keys(payload)
        assert len(keys) >= 8, "키를 모으지 못하면 금지 필드 0건이 공허하다"
        assert [key for key in keys if _VACUOUS_ASSERTION.search(key)] == []
        planted = {**payload, "patch_verified": True}
        assert [key for key in _keys(planted) if _VACUOUS_ASSERTION.search(key)] == [
            "patch_verified"
        ]

    def test_verdicts_and_kinds_stay_inside_the_closed_vocabularies(self):
        pools = (
            clean_rig_18(),
            duplicate_address_triple(),
            function_ref_property(),
            truncated_parent(),
            range_overlap_go(),
        )
        for pool in pools:
            evaluation = evaluate_patch(read_inventory(pool), GO_FOOTPRINT)
            assert {row.verdict for row in evaluation.rows} <= set(FIXTURE_VERDICT)
            collisions = evaluation.address_duplicates + evaluation.range_overlaps
            assert {c.kind for c in collisions} <= set(COLLISION_KIND)
            assert {f.kind for f in evaluation.read_failures} <= set(READ_FAILURE_KIND)
            assert {c.kind for c in evaluation.skipped_checks} <= set(SKIPPED_CHECK_KIND)
            assert set(evaluation.verdict_counts) == set(FIXTURE_VERDICT)
            reasons = {reason for row in evaluation.rows for reason in row.reasons}
            assert reasons <= set(READ_FAILURE_KIND) | set(COLLISION_KIND)

    def test_the_payload_carries_the_report_schema_blocks(self):
        payload = evaluate_patch(read_inventory(truncated_parent())).to_dict()
        assert {
            "inventory",
            "fixtures",
            "collisions",
            "read_failures",
            "skipped_checks",
        } <= set(payload)
        assert set(payload["collisions"]) == {"address_duplicates", "range_overlaps"}
        assert payload["fixtures"]
        assert set(payload["fixtures"][0]) == {
            "slot",
            "name",
            "patch_raw",
            "universe",
            "address",
            "fixture_type",
            "mode",
            "fid_note",
            "verdict",
            "reasons",
        }

    def test_every_observed_fixture_appears_exactly_once(self):
        evaluation = evaluate_patch(read_inventory(truncated_parent(hidden=(19, 20))))
        slots = [row.record.slot for row in evaluation.rows]
        assert len(slots) == len(set(slots)) == evaluation.inventory.observed_count
        counts = evaluation.verdict_counts
        assert counts[OBSERVED_CLEAR] + counts[COLLISION] + counts[READ_FAILED] == len(slots)


#: A bound the walk "enumerated". Deliberately not a measured width: a verdict
#: that came from a constant instead of this value would disagree.
BOUND = 23


#: Where the bound's evidence points. The shape matches the exact-width axis's
#: ``source`` so a reader can compare the two origins.
WALK_ROOT = "Patch/FixtureTypes/1/DMXModes"


def _walked(bound: int = BOUND, *, complete: bool = True) -> WalkOutcome:
    return WalkOutcome(
        complete=complete,
        footprints=(
            ModeFootprint(path=f"{WALK_ROOT}/1/DMXChannels", width=bound - 4),
            ModeFootprint(path=f"{WALK_ROOT}/2/DMXChannels", width=bound),
        ),
    )


def _pair(gap: int, *, universe: int = 1, first: int = 100) -> FixturePool:
    """Two fixtures in one universe, ``gap`` channels apart."""
    return FixturePool(
        {
            1: fixture_props(f"{universe}.{first:03d}", name="앞"),
            2: fixture_props(f"{universe}.{first + gap:03d}", name="뒤"),
        }
    )


class TestBoundBasisGrades:
    """AC-OVERLAP-008 · AC-OVERLAP-011 — the predicate, and what it must not say."""

    def _basis(self, gap: int) -> str:
        return evaluate_patch(read_inventory(_pair(gap)), walk=_walked()).overlap_basis

    def test_a_gap_below_the_bound_is_unsettled(self):
        assert self._basis(BOUND - 1) == BOUND_INCONCLUSIVE

    def test_a_gap_exactly_at_the_bound_is_clear(self):
        """The off-by-one boundary, at the judgement layer.

        A predecessor note wrote this as "at or below the bound, unsettled". On
        the measured rig the gap is far wider than the bound, so that spelling
        gives the same answer and the error waits for a rig that lands exactly
        here.
        """
        assert self._basis(BOUND) == BOUND_PROVES_CLEAR

    def test_a_gap_above_the_bound_is_clear(self):
        assert self._basis(BOUND + 1) == BOUND_PROVES_CLEAR

    def test_only_the_narrow_case_differs(self):
        below, at, above = self._basis(BOUND - 1), self._basis(BOUND), self._basis(BOUND + 1)
        assert below != at
        assert at == above

    def test_an_incomplete_walk_performs_no_comparison(self):
        evaluation = evaluate_patch(read_inventory(_pair(BOUND - 1)), walk=_walked(complete=False))
        assert evaluation.overlap_basis == NOT_PERFORMED

    def test_no_walk_at_all_performs_no_comparison(self):
        assert evaluate_patch(read_inventory(_pair(BOUND - 1))).overlap_basis == NOT_PERFORMED

    def test_the_four_grades_are_the_closed_vocabulary(self):
        assert {EXACT_WIDTHS, BOUND_PROVES_CLEAR, BOUND_INCONCLUSIVE, NOT_PERFORMED} == set(
            OVERLAP_BASIS
        )


class TestUnsettledIsNotACollision:
    """AC-OVERLAP-011 — an upper bound cannot prove that an overlap EXISTS."""

    def _unsettled(self):
        return evaluate_patch(read_inventory(_pair(BOUND - 1)), walk=_walked())

    def test_the_unsettled_grade_is_actually_produced(self):
        # ⑤ first: the three assertions below are vacuous if nothing fired.
        assert self._unsettled().overlap_basis == BOUND_INCONCLUSIVE

    def test_no_range_overlap_is_reported(self):
        assert self._unsettled().range_overlaps == ()

    def test_the_collision_total_stays_zero(self):
        assert self._unsettled().collision_total == 0

    def test_no_fixture_is_given_a_collision_verdict(self):
        evaluation = self._unsettled()
        assert [row.verdict for row in evaluation.rows] == [OBSERVED_CLEAR, OBSERVED_CLEAR]
        assert COLLISION not in [row.verdict for row in evaluation.rows]

    def test_the_state_is_announced_rather_than_swallowed(self):
        evaluation = self._unsettled()
        kinds = [check.kind for check in evaluation.skipped_checks]
        assert RANGE_OVERLAP_BOUND_INCONCLUSIVE in kinds
        row = next(
            c for c in evaluation.skipped_checks if c.kind == RANGE_OVERLAP_BOUND_INCONCLUSIVE
        )
        assert str(BOUND) in row.reason
        assert "충돌이 아니다" in row.reason
        assert row.assumption

    def test_the_notice_names_the_universe_and_the_slots(self):
        row = next(
            c
            for c in self._unsettled().skipped_checks
            if c.kind == RANGE_OVERLAP_BOUND_INCONCLUSIVE
        )
        assert "유니버스 1" in row.reason
        assert "슬롯 1" in row.reason
        assert "슬롯 2" in row.reason

    def test_a_clear_rig_raises_no_notice(self):
        # Contrast: the notice is a consequence of the grade, not a fixture.
        evaluation = evaluate_patch(read_inventory(_pair(BOUND)), walk=_walked())
        assert RANGE_OVERLAP_BOUND_INCONCLUSIVE not in [
            check.kind for check in evaluation.skipped_checks
        ]


class TestUniverseDisjointnessOnBothAxes:
    """AC-OVERLAP-009 ③④ — the mutation that was alive at the start of this SPEC.

    Nothing walked ``_range_overlaps`` with two universes, so collapsing the
    per-universe buckets into one address space broke no test. Closing that hole
    needs a rig where the collapse CHANGES the answer, which is stricter than a
    rig where the two addresses merely look adjacent: ``1.500`` and ``2.001`` are
    one apart as bare numbers, yet the intervals ``500..539`` and ``1..40`` miss
    each other even in one shared space, so such a rig proves nothing. The rig
    below overlaps under a collapse and cannot overlap without one.
    """

    #: Universe 2's address sits INSIDE universe 1's interval once the spaces are
    #: merged: 100..139 against 110..149. The distance, 10, is also under the
    #: bound, so one rig exercises both axes.
    def _cross_universe(self) -> FixturePool:
        return FixturePool(
            {
                1: fixture_props("1.100", name="유니버스 1"),
                2: fixture_props("2.110", name="유니버스 2"),
            }
        )

    def test_the_collapse_would_be_visible(self):
        """Non-vacuity for the two tests below, asserted rather than asserted-in-prose.

        The same two addresses inside ONE universe produce a finding on both
        axes. So if the axes keyed by address alone, the cross-universe rig would
        produce those findings too -- and the tests below would fail.
        """
        merged = FixturePool(
            {
                1: fixture_props("1.100", name="같은 유니버스 A"),
                2: fixture_props("1.110", name="같은 유니버스 B"),
            }
        )
        policy = FootprintPolicy(enabled=True, widths={1: 40, 2: 40}, source=FOOTPRINT_SOURCE)
        assert len(evaluate_patch(read_inventory(merged), policy).range_overlaps) == 1
        assert evaluate_patch(read_inventory(merged), walk=_walked()).overlap_basis == (
            BOUND_INCONCLUSIVE
        )

    def test_the_exact_width_axis_keeps_the_universes_apart(self):
        policy = FootprintPolicy(enabled=True, widths={1: 40, 2: 40}, source=FOOTPRINT_SOURCE)
        evaluation = evaluate_patch(read_inventory(self._cross_universe()), policy)
        assert all(row.universe is not None for row in evaluation.rows)
        assert evaluation.range_overlaps == ()

    def test_the_bound_axis_keeps_the_universes_apart(self):
        evaluation = evaluate_patch(read_inventory(self._cross_universe()), walk=_walked())
        assert evaluation.overlap_basis == BOUND_PROVES_CLEAR
        assert RANGE_OVERLAP_BOUND_INCONCLUSIVE not in [
            check.kind for check in evaluation.skipped_checks
        ]


class TestBoundAxisTakesUnresolvedTypeMode:
    """AC-OVERLAP-010 ③④ — the two axes have deliberately different filters."""

    def _mixed(self) -> FixturePool:
        return FixturePool(
            {
                1: fixture_props("1.100", name="타입 확정"),
                # No FixtureType, no Mode: the reads fail, so the exact-width axis
                # cannot judge this fixture. The bound argument does not need to
                # know which mode it uses.
                2: {"Patch": "1.110", "Name": "타입 미확정"},
            }
        )

    def test_an_unresolved_fixture_is_inside_the_gap_set(self):
        evaluation = evaluate_patch(read_inventory(self._mixed()), walk=_walked())
        unresolved = next(row for row in evaluation.rows if row.record.slot == 2)
        assert TYPE_MODE_UNRESOLVED in unresolved.reasons
        # 110 - 100 = 10, under the bound, and it could only have been measured
        # if slot 2 entered the gap set.
        assert evaluation.overlap_basis == BOUND_INCONCLUSIVE

    def test_the_same_fixture_is_excluded_from_the_exact_width_axis(self):
        policy = FootprintPolicy(enabled=True, widths={1: 40, 2: 40}, source=FOOTPRINT_SOURCE)
        evaluation = evaluate_patch(read_inventory(self._mixed()), policy)
        # Intervals 100..139 and 110..149 overlap by 30 channels. The finding is
        # absent only because slot 2 is excluded for an unresolved type/mode.
        assert evaluation.range_overlaps == ()
        assert (
            TYPE_MODE_UNRESOLVED
            in next(row for row in evaluation.rows if row.record.slot == 2).reasons
        )

    def test_both_filters_run_on_one_rig(self):
        policy = FootprintPolicy(enabled=True, widths={1: 40, 2: 40}, source=FOOTPRINT_SOURCE)
        evaluation = evaluate_patch(read_inventory(self._mixed()), policy, walk=_walked())
        assert evaluation.range_overlaps == ()
        assert evaluation.overlap_basis == BOUND_INCONCLUSIVE


class TestAddressRangeValidation:
    """AC-OVERLAP-012 — a floor and a form, and deliberately no ceiling."""

    @pytest.mark.parametrize("raw", ["0.0", "1.0", "0.1", "0.100", "12.0"])
    def test_an_index_below_one_is_a_parse_failure(self, raw):
        parse = normalize_address(raw)
        assert parse.ok is False
        assert parse.universe is None
        assert parse.address is None
        assert parse.error

    @pytest.mark.parametrize("raw", ["1.001", "2.401", "1.99999"])
    def test_a_valid_address_still_passes(self, raw):
        # ``1.99999`` is the ceiling case: capacity is unmeasured, so inventing a
        # limit would reject an address the console accepts.
        assert normalize_address(raw).ok is True

    def test_an_out_of_range_address_never_enters_the_gap_set(self):
        """Two valid addresses exactly ``BOUND`` apart, plus one meaningless one.

        Two things must hold at once. The bound settles the valid pair, so no
        unsettled notice appears. And the meaningless address is not silently
        dropped: its slot was never compared by either axis, so the RIG-WIDE grade
        falls to ``not_performed`` -- the weakest of the comparisons performed.
        Reporting ``bound_proves_clear`` for this rig would let an uncompared slot
        ride on a compared one.
        """
        valid = {
            2: fixture_props("1.100", name="유효 A"),
            3: fixture_props(f"1.{100 + BOUND:03d}", name="유효 B"),
        }
        with_junk = evaluate_patch(
            read_inventory(FixturePool({1: fixture_props("1.0", name="무의미"), **valid})),
            walk=_walked(),
        )
        without_junk = evaluate_patch(read_inventory(FixturePool(valid)), walk=_walked())

        # Non-vacuity: the valid pair on its own IS settled, so the grade below
        # comes from the uncompared slot and not from a failed comparison.
        assert without_junk.overlap_basis == BOUND_PROVES_CLEAR
        assert with_junk.overlap_basis == NOT_PERFORMED
        assert RANGE_OVERLAP_BOUND_INCONCLUSIVE not in [
            check.kind for check in with_junk.skipped_checks
        ]
        assert next(row for row in with_junk.rows if row.record.slot == 1).address is None
        assert 1 not in with_junk.overlap.bound_slots
        assert set(with_junk.overlap.bound_slots) == {2, 3}

    def test_an_out_of_range_address_is_reported_as_a_read_failure(self):
        pool = FixturePool({1: fixture_props("0.0", name="무의미")})
        evaluation = evaluate_patch(read_inventory(pool), walk=_walked())
        kinds = [failure.kind for failure in evaluation.read_failures]
        assert ADDRESS_PARSE_FAILED in kinds
        row = next(row for row in evaluation.rows if row.record.slot == 1)
        assert row.verdict == READ_FAILED
        # NOT "no such fixture": the fixture was observed, its address was not.
        assert row.record.name == "무의미"
        assert evaluation.inventory.observed_count == 1

    def test_a_meaningless_address_would_otherwise_produce_a_meaningless_gap(self):
        # Non-vacuity for the pair above: without the floor, ``1.0`` parses and
        # its distance to 1.001 is 1, which is under any bound.
        assert normalize_address("1.001").address == 1
        assert normalize_address("1.0").ok is False

    def test_no_address_ceiling_is_written_down(self):
        """AC-OVERLAP-012 ④ — the ceiling depends on an unmeasured assumption.

        Behavioural rather than lexical: a hardcoded ceiling of any plausible
        size would reject one of these.
        """
        for address in (512, 1024, 65535):
            assert normalize_address(f"1.{address}").ok is True


class TestOverlapBasisPayload:
    """AC-OVERLAP-016 — the grade travels with its evidence, and the key is locked."""

    #: The one new top-level key's exact key set. Written down HERE because the
    #: existing top-level assertion is a SUBSET check: laying a key on it breaks
    #: nothing, which is precisely why nobody guards it. This closes that.
    EVIDENCE_KEYS = {
        "basis",
        "bound",
        "bound_source",
        "mode_widths",
        "exact_width_slots",
        "bound_slots",
        "observation_note",
    }

    def test_the_new_top_level_key_has_an_exact_key_set(self):
        payload = evaluate_patch(read_inventory(_pair(BOUND)), walk=_walked()).to_dict()
        assert set(payload["overlap_basis"]) == self.EVIDENCE_KEYS

    def test_the_key_set_is_locked_in_every_grade(self):
        # A grade-dependent key set would let one branch ship a field no consumer
        # expects and another drop one it needs.
        for evaluation in (
            evaluate_patch(read_inventory(_pair(BOUND))),
            evaluate_patch(read_inventory(_pair(BOUND - 1)), walk=_walked()),
            evaluate_patch(read_inventory(_pair(BOUND)), walk=_walked()),
            evaluate_patch(read_inventory(_pair(BOUND)), GO_FOOTPRINT),
        ):
            assert set(evaluation.to_dict()["overlap_basis"]) == self.EVIDENCE_KEYS

    def test_the_bound_and_its_origin_both_reach_the_payload(self):
        block = evaluate_patch(read_inventory(_pair(BOUND)), walk=_walked()).to_dict()[
            "overlap_basis"
        ]
        assert block["bound"] == BOUND
        assert block["mode_widths"] == [BOUND - 4, BOUND]

    def test_the_origin_names_a_path_and_the_field_read_on_it(self):
        block = evaluate_patch(read_inventory(_pair(BOUND)), walk=_walked()).to_dict()[
            "overlap_basis"
        ]
        # Not free prose: the string carries the path of the WIDEST mode and the
        # field name, so a reader can re-query it and disagree.
        assert block["bound_source"] == f"{WALK_ROOT}/2/DMXChannels childCount"
        assert block["bound_source"].startswith(WALK_ROOT)
        assert block["bound_source"].endswith("childCount")

    def test_a_walk_with_no_bound_offers_no_origin(self):
        block = evaluate_patch(
            read_inventory(_pair(BOUND)), walk=_walked(complete=False)
        ).to_dict()["overlap_basis"]
        assert block["bound"] is None
        assert block["bound_source"] == ""

    def test_the_note_is_a_non_empty_korean_string_in_every_grade(self):
        for evaluation in (
            evaluate_patch(read_inventory(_pair(BOUND))),
            evaluate_patch(read_inventory(_pair(BOUND - 1)), walk=_walked()),
            evaluate_patch(read_inventory(_pair(BOUND)), walk=_walked()),
            evaluate_patch(read_inventory(_pair(BOUND)), GO_FOOTPRINT),
        ):
            note = evaluation.to_dict()["overlap_basis"]["observation_note"]
            assert note.strip()
            assert any("\uac00" <= character <= "\ud7a3" for character in note)

    def test_the_existing_top_level_assertion_still_holds(self):
        # The subset shape is deliberately left alone; this milestone ADDS a lock
        # rather than tightening the old one.
        payload = evaluate_patch(read_inventory(clean_rig_18())).to_dict()
        assert {"inventory", "fixtures", "collisions", "skipped_checks"} <= set(payload)


class TestExactWidthsOutrankTheBound:
    """AC-OVERLAP-013 — a real footprint is stronger evidence than a ceiling."""

    def _all_exact(self) -> FootprintPolicy:
        return FootprintPolicy(enabled=True, widths={1: 4, 2: 4, 3: 4}, source=FOOTPRINT_SOURCE)

    def _rig(self) -> FixturePool:
        return FixturePool(
            {
                1: fixture_props("1.100", name="A"),
                2: fixture_props("1.110", name="B"),
                3: fixture_props("1.120", name="C"),
            }
        )

    def test_a_slot_with_a_real_width_is_graded_by_it(self):
        evaluation = evaluate_patch(read_inventory(self._rig()), self._all_exact(), _walked())
        assert evaluation.overlap_basis == EXACT_WIDTHS
        assert set(evaluation.overlap.exact_width_slots) == {1, 2, 3}
        assert evaluation.overlap.bound_slots == ()

    def test_the_bound_would_otherwise_have_left_the_rig_unsettled(self):
        """Non-vacuity for the test above.

        The same rig with NO widths is unsettled: the gaps are 10 and the bound is
        23. So the ``exact_widths`` grade above is the priority rule at work, not
        a rig that happened to be clear either way.
        """
        bound_only = evaluate_patch(read_inventory(self._rig()), walk=_walked())
        assert bound_only.overlap_basis == BOUND_INCONCLUSIVE

    def test_an_unread_population_drags_the_rig_wide_grade_down(self):
        """AC-OVERLAP-013 · CONTRACT D-4 정직성 제약 1 — 미관측 개체도 미비교다.

        ``assessed`` holds only the OBSERVED fixtures, so every clause that walks
        it is blind to a truncated enumeration. A rig whose pool DECLARES more
        children than it returned has fixtures nobody compared -- they have no
        slot to compare -- and stamping ``bound_proves_clear`` over them is the
        one error direction this axis can produce (`spec.md` §A 제약 4). The
        run-audit measured exactly this: missing_count 22, grade
        ``bound_proves_clear``, qualifier naming only the mode set.
        """
        spaced = FixturePool(
            {1: fixture_props("1.100", name="A"), 2: fixture_props(f"1.{100 + BOUND}", name="B")}
        )
        whole = evaluate_patch(read_inventory(spaced), walk=_walked())
        # Non-vacuity: the SAME rig read wholly really does clear, so the
        # downgrade below is the unread population talking and not a rig that
        # was unsettled anyway.
        assert whole.overlap_basis == BOUND_PROVES_CLEAR
        assert whole.inventory.missing_count == 0

        spaced.child_count = 4
        spaced.truncated = True
        partial = evaluate_patch(read_inventory(spaced), walk=_walked())
        assert partial.inventory.missing_count == 2
        assert partial.overlap.bound == BOUND, "상계는 여전히 산출된다 — 순회는 성공했다"
        assert partial.overlap_basis == NOT_PERFORMED
        # And the qualifier must say so: naming only the mode set would leave the
        # unread fixtures unmentioned in the one string the user reads.
        assert "미관측" in partial.overlap.observation_note

    def test_a_collision_the_exact_axis_found_forbids_a_clearance_grade(self):
        """AC-OVERLAP-011 · CONTRACT D-4 — 등급은 리그 전역이므로 한 축이 겹침을
        증명한 뒤에는 어느 부분도 *"증명된 청결"*을 말할 수 없다.

        ``_BASIS_ORDER``가 ``exact_widths``를 ``bound_proves_clear`` 위에 두는데
        둘은 **같은 종류의 진술이 아니다** — 앞은 *어떻게 비교했나*(결과가 충돌일
        수도 있다)이고 뒤는 *결과*다. 그래서 최약 규칙이 method를 result로
        끌어내려 **충돌이 실재하는 리그에 청결 주장을 만들어 냈다.**

        PR 시점 독립 코드 리뷰가 찾았다. 감사도, 그 앞의 R-2 수정도 놓쳤다 —
        R-2는 ``bound_slots`` 문을 닫았는데 이 경로는 ``exact_set``으로 들어와
        참여 검사를 우회한다. 출하 핸들러는 ``FootprintPolicy``를 만들지 않아
        **잠복**이지만 그 어휘는 공개 API이고 스위트가 상시 발화시킨다.
        """
        both_at_one_address = FixturePool(
            {
                1: fixture_props("1.100", name="A"),
                2: fixture_props("1.100", name="B"),
                3: fixture_props("2.200", name="C"),
            }
        )
        policy = FootprintPolicy(enabled=True, widths={1: 4, 2: 4}, source=FOOTPRINT_SOURCE)
        evaluation = evaluate_patch(read_inventory(both_at_one_address), policy, _walked())
        # 비공허성: 정확폭 축이 실제로 겹침을 찾았고, 상계 축도 실제로 돌았다.
        # 둘 중 하나라도 비면 이 판정이 공허하다.
        assert len(evaluation.range_overlaps) == 1
        assert set(evaluation.overlap.exact_width_slots) == {1, 2}
        assert evaluation.overlap.bound_slots == (3,)
        # 등급이 청결을 주장하지 않는다 — method 라벨로 남는다.
        assert evaluation.overlap_basis == EXACT_WIDTHS
        assert evaluation.overlap_basis != BOUND_PROVES_CLEAR
        # 그리고 사용자가 읽는 문장에 "겹침이 불가능"이 없다.
        from server.prechk.report import build_report

        assert "겹침이 불가능" not in build_report(evaluation).summary_ko()

    def test_a_mixed_rig_runs_both_axes_and_reports_each_origin(self):
        partial = FootprintPolicy(enabled=True, widths={1: 4, 2: 4}, source=FOOTPRINT_SOURCE)
        evaluation = evaluate_patch(read_inventory(self._rig()), partial, _walked())
        assert set(evaluation.overlap.exact_width_slots) == {1, 2}
        assert set(evaluation.overlap.bound_slots) == {3}
        # Weakest of the two grades: slot 3's neighbour pair is 10 apart, under
        # the bound, so the bound axis did not settle it.
        assert evaluation.overlap_basis == BOUND_INCONCLUSIVE
        assert evaluation.overlap.bound == BOUND
        assert evaluation.overlap.bound_source

    def test_a_gap_between_two_exact_slots_is_left_to_the_other_axis(self):
        # Slots 1 and 2 both carry real widths of 4: intervals 100..103 and
        # 110..113 do not meet, and the bound must not overrule that with an
        # unsettled verdict just because 10 < 23.
        exact_pair = FootprintPolicy(enabled=True, widths={1: 4, 2: 4}, source=FOOTPRINT_SOURCE)
        pair = FixturePool(
            {1: fixture_props("1.100", name="A"), 2: fixture_props("1.110", name="B")}
        )
        evaluation = evaluate_patch(read_inventory(pair), exact_pair, _walked())
        assert evaluation.overlap_basis == EXACT_WIDTHS
        assert evaluation.range_overlaps == ()
        assert RANGE_OVERLAP_BOUND_INCONCLUSIVE not in [
            check.kind for check in evaluation.skipped_checks
        ]

    def test_the_rig_wide_grade_is_the_weakest_comparison_performed(self):
        """D-4 honesty rule 1 — three uncompared slots sink the grade.

        The two valid addresses are exactly ``BOUND`` apart and settled. Three
        further fixtures have unreadable addresses, so neither axis compared them.
        Stamping ``bound_proves_clear`` rig-wide would report them as clear.
        """
        slots = {
            1: fixture_props("1.100", name="유효 A"),
            2: fixture_props(f"1.{100 + BOUND:03d}", name="유효 B"),
        }
        for slot in (3, 4, 5):
            slots[slot] = fixture_props("판독불가", name=f"미판정 {slot}")
        evaluation = evaluate_patch(read_inventory(FixturePool(slots)), walk=_walked())
        assert set(evaluation.overlap.bound_slots) == {1, 2}
        assert evaluation.overlap_basis == NOT_PERFORMED

    def test_a_rig_with_no_fixture_at_all_grades_not_performed(self):
        """D-4 정직성 제약 1 — 비교가 0건이면 최약 등급이고, 문구도 그렇게 말한다.

        픽스처 0개는 오류가 아니라 **정상 리그**다
        (``.moai/specs/SPEC-COPILOT-PRECHK-001/acceptance.md`` — "픽스처 0개 |
        거부가 아니라 정상이다"). 이 SPEC의 문서 네 곳이 그 근거를
        "``acceptance.md`` §D"로 적었으나 이 SPEC의 ``acceptance.md``에는 §D가
        없다 — 실제 출처는 위 PRECHK 경로다.

        여기가 ``_weakest``의 **빈 등급 집합 대비**에 도달하는 유일한 경로다.
        ``assessed``가 비면 ``exact``도 ``bound_slots``도 비고 미관측도 0건이라
        어떤 절도 등급을 넣지 못한다. 그 대비를 ``exact_widths``로 뒤집어도
        스위트 전량이 통과하던 자리이고, 뒤집히면 비교를 한 번도 하지 않은 리그가
        "실제 점유폭으로 비교했다 — 비교된 슬롯에 대해 한정이 없다."라는
        **한정 없는 거짓 문장**을 사용자 요약으로 받는다(``CONTRACT.md`` §6
        결함군 1).
        """
        evaluation = evaluate_patch(read_inventory(FixturePool({})), self._all_exact(), _walked())
        # 비공허성 ①: 등급이 미비교 슬롯 절에서 온 것이 아님을 고정한다. 비교 대상
        # 자체가 0개이므로 그 절은 빈 순회로 False이고, 미관측 population도 없다.
        assert evaluation.inventory.completeness == COMPLETE
        assert evaluation.inventory.observed_count == 0
        assert evaluation.inventory.missing_count == 0
        assert evaluation.rows == ()
        assert evaluation.overlap.exact_width_slots == ()
        assert evaluation.overlap.bound_slots == ()
        # 비공허성 ②: 상계는 살아 있다 — 등급이 낮은 이유가 순회 실패가 아니다.
        assert evaluation.overlap.bound == BOUND

        assert evaluation.overlap_basis == NOT_PERFORMED
        assert (
            evaluation.overlap.observation_note
            == "겹침 비교를 수행하지 않았다 — 겹침이 없다는 뜻이 아니다."
        )

    def test_the_partial_coverage_notice_still_fires(self):
        """AC-OVERLAP-013 ⑤ — the pre-existing skip notice is not swallowed."""
        partial = FootprintPolicy(enabled=True, widths={1: 4}, source=FOOTPRINT_SOURCE)
        evaluation = evaluate_patch(read_inventory(self._rig()), partial)
        kinds = [check.kind for check in evaluation.skipped_checks]
        assert RANGE_OVERLAP_DESCOPE in kinds


class TestWalkFailureKeepsTheReport:
    """AC-OVERLAP-007 — a failed walk costs the bound, not the rest."""

    def _dead_walk(self) -> WalkOutcome:
        from server.prechk.footprint import REASON_UNREACHABLE

        return WalkOutcome(
            complete=False,
            failure=REASON_UNREACHABLE,
            failure_detail="경로 조회에 어느 응답도 오지 않았다 — 콘솔이 답하지 않는다.",
        )

    def test_the_inventory_block_is_unchanged(self):
        healthy = evaluate_patch(read_inventory(duplicate_address_triple()), walk=_walked())
        failed = evaluate_patch(read_inventory(duplicate_address_triple()), walk=self._dead_walk())
        assert failed.inventory.observed_count == healthy.inventory.observed_count
        assert failed.inventory.observed_count >= 1

    def test_address_duplicates_are_still_detected(self):
        failed = evaluate_patch(read_inventory(duplicate_address_triple()), walk=self._dead_walk())
        # Non-vacuity: the rig really does carry a duplicate.
        assert len(failed.address_duplicates) == 1
        assert len(failed.address_duplicates[0].members) == 3

    def test_the_grade_falls_back_and_the_failure_is_stated(self):
        failed = evaluate_patch(read_inventory(duplicate_address_triple()), walk=self._dead_walk())
        assert failed.overlap_basis == NOT_PERFORMED
        assert "응답" in failed.overlap.observation_note
        assert RANGE_OVERLAP_DESCOPE in [check.kind for check in failed.skipped_checks]

    def test_the_summary_does_not_claim_an_unqualified_zero(self):
        from server.prechk.report import build_report, label

        clean = FixturePool({1: fixture_props("1.100", name="혼자")})
        summary = build_report(
            evaluate_patch(read_inventory(clean), walk=self._dead_walk())
        ).to_dict()["summary_ko"]
        assert "충돌 0건" in summary
        # ...but never on its own: the not-performed notice rides alongside.
        assert label("skipped_check_kind", RANGE_OVERLAP_DESCOPE) in summary
