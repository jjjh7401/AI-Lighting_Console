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
    COLLISION,
    NOT_ASSESSED,
    OBSERVED_CLEAR,
    RANGE_OVERLAP,
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
