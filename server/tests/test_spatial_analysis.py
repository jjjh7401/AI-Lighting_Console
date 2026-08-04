"""Spatial analysis layer tests — M2 (AC-SPATIAL-009/010/011/012/013).

SPEC-COPILOT-SPATIAL-001 REQ-SPATIAL-009 through -013.

The load-bearing test in this file is the 1x30 vs 3x10 pair. It is the reason
the SPEC exists: the same instruction must produce a different selection chain
on a bar than on a grid, and the difference has to be MACHINE-readable
(scenario 1). Everything else here defends that claim's preconditions —
determinism, a documented tie-break, an honest low-confidence signal, and a
closed sort vocabulary.

Two goldens mirror measured reality rather than a convenient shape:

* the all-(0,0,0) 19-fixture rig is the live console rig as M0 read it. It is a
  SUCCESSFUL read of a patched-but-unpositioned show, so it must come back
  flagged, not empty and not silently declared one row (acceptance.md §D);
* the negative-coordinate golden exists because stage coordinates are centred
  on the stage, so half of a normal rig sits at negative x. Every one of the
  four sorts is checked against hand-computed orders on it.

The threshold constants are pinned twice over: by value, and by behaviour just
either side of each boundary. design.md §3.1 leaves the numbers to
implementation on the explicit condition that goldens fix them, so a test that
only asserted the current behaviour without straddling the boundary would let
the constant drift silently.

Nothing here touches a console: the whole package is pure arithmetic over
in-memory records.
"""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

import pytest

from server.spatial import (
    SPATIAL_LOW_CONFIDENCE_REASONS,
    SPATIAL_ROW_GAP_RATIO,
    SPATIAL_ROW_NOISE_SPAN,
    SPATIAL_ROW_ORDER,
    SPATIAL_SORTS,
    SpatialAnalysisError,
    analyze_spatial_records,
    spatial_analysis_to_dict,
    spatial_fixtures_from_records,
    spatial_sorted_fids,
)

SPATIAL_DIR = Path(__file__).resolve().parents[1] / "spatial"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# design.md §3.2 — the vocabulary as the SPEC tabulates it. Restated here so a
# rename in the implementation has to be a deliberate two-file edit.
EXPECTED_SORTS = ("left_to_right", "right_to_left", "center_out", "diagonal")


def _rec(fid: int, x: float, y: float, z: float = 3.0) -> dict:
    return {"fid": fid, "name": f"PAR {fid}", "x": x, "y": y, "z": z}


def _bar_1x30() -> list[dict]:
    """30 fixtures on one bar: x from -14.5 to 14.5 at 1.0 spacing, flat depth."""
    return [_rec(i + 1, -14.5 + i, 0.0) for i in range(30)]


def _grid_3x10() -> list[dict]:
    """3 rows of 10 at y = -3.0 / 0.0 / 3.0; fids run row-major 1..30."""
    return [
        _rec(row * 10 + column + 1, -4.5 + column, -3.0 + 3.0 * row)
        for row in range(3)
        for column in range(10)
    ]


def _irregular() -> list[dict]:
    """Non-uniform depths: every gap is 0.4-0.9, so none stands out as a row edge."""
    depths = (0.0, 0.7, 1.3, 2.2, 2.6, 3.5, 4.0, 4.9)
    return [_rec(i + 1, float(i), y) for i, y in enumerate(depths)]


def _unpositioned_rig_19() -> list[dict]:
    """The live rig as M0 measured it: fid 1..19, every coordinate exactly 0.0."""
    return [{"fid": i + 1, "name": f"PAR {i + 1}", "x": 0.0, "y": 0.0, "z": 0.0} for i in range(19)]


def _negative_2x4() -> list[dict]:
    """Two rows entirely in negative depth, straddling the origin on x.

    Row 0 (y = -6.0): fids 1-4 at x = -3, -1, 1, 3   -> center_x  0.0
    Row 1 (y = -2.0): fids 5-8 at x = -4, -2, 0, 2   -> center_x -1.0
    """
    front = [_rec(1, -3.0, -6.0), _rec(2, -1.0, -6.0), _rec(3, 1.0, -6.0), _rec(4, 3.0, -6.0)]
    back = [_rec(5, -4.0, -2.0), _rec(6, -2.0, -2.0), _rec(7, 0.0, -2.0), _rec(8, 2.0, -2.0)]
    return front + back


# -- AC-SPATIAL-009: 1x30 vs 3x10 are structurally distinguished -----------------


class TestRowDetectionDistinguishesTheTwoRigs:
    def test_a_single_bar_and_a_three_row_grid_yield_different_row_counts(self):
        # The one assertion the whole SPEC turns on: same 30 fixtures, same
        # instruction, structurally different answer.
        one = analyze_spatial_records(_bar_1x30())
        three = analyze_spatial_records(_grid_3x10())
        assert (one.row_count, three.row_count) == (1, 3)

    def test_the_single_bar_row_holds_all_thirty_fixtures_left_to_right(self):
        analysis = analyze_spatial_records(_bar_1x30())
        assert analysis.rows[0].fids == tuple(range(1, 31))
        assert analysis.fixture_count == 30

    def test_the_grid_rows_hold_exactly_their_own_ten_members(self):
        # Membership, not just the count — a 3-row verdict with the wrong
        # fixtures in each row produces a wrong chain that still "has 3 rows".
        analysis = analyze_spatial_records(_grid_3x10())
        assert [row.fids for row in analysis.rows] == [
            tuple(range(1, 11)),
            tuple(range(11, 21)),
            tuple(range(21, 31)),
        ]

    def test_rows_are_ordered_stage_front_to_back_and_say_so(self):
        # Row 0 is meaningless until the result states which end of the stage
        # it sits at (design.md §3.2).
        analysis = analyze_spatial_records(_grid_3x10())
        assert analysis.row_order == SPATIAL_ROW_ORDER == "y_ascending"
        assert [row.center_y for row in analysis.rows] == [-3.0, 0.0, 3.0]

    def test_row_detection_survives_hanging_slop_within_a_row(self):
        # A real 3x10 rig is not laser-aligned. Jitter well inside the noise
        # span must not shatter a row into ten rows of one.
        jittered = [
            {**record, "y": record["y"] + (0.01 if index % 2 else -0.01)}
            for index, record in enumerate(_grid_3x10())
        ]
        analysis = analyze_spatial_records(jittered)
        assert analysis.row_count == 3
        assert analysis.low_confidence is False


# -- AC-SPATIAL-011: the low-confidence signal ----------------------------------


class TestLowConfidenceSignal:
    def test_the_unpositioned_live_rig_is_flagged_not_declared_one_row(self):
        # 19 fixtures at (0,0,0) — the rig M0 actually read. This is a genuine
        # read of a patched-but-unpositioned show, NOT missing data, and the
        # 1-row fallback must arrive wearing the flag (acceptance.md §D).
        analysis = analyze_spatial_records(_unpositioned_rig_19())
        assert analysis.low_confidence is True
        assert analysis.confidence_reason == "no_spatial_spread"
        assert analysis.row_count == 1
        assert analysis.rows[0].fids == tuple(range(1, 20))
        assert analysis.fixture_count == 19

    def test_an_irregular_rig_falls_back_to_one_row_with_the_flag_set(self):
        analysis = analyze_spatial_records(_irregular())
        assert analysis.low_confidence is True
        assert analysis.confidence_reason == "weak_gap_separation"
        assert analysis.row_count == 1

    def test_the_flag_is_absent_on_both_regular_layouts(self):
        # The other half of AC-SPATIAL-011: a signal that is always on carries
        # no information.
        for records in (_bar_1x30(), _grid_3x10(), _negative_2x4()):
            analysis = analyze_spatial_records(records)
            assert analysis.low_confidence is False
            assert analysis.confidence_reason is None

    def test_an_empty_read_is_flagged_rather_than_returning_a_confident_nothing(self):
        analysis = analyze_spatial_records([])
        assert (analysis.rows, analysis.fixture_count) == ((), 0)
        assert analysis.low_confidence is True
        assert analysis.confidence_reason == "no_fixtures"

    def test_a_lone_fixture_establishes_no_structure(self):
        # One point has zero spread by definition; claiming a confident row of
        # one would be asserting a structure that was never observed.
        analysis = analyze_spatial_records([_rec(4, 2.0, 5.0)])
        assert analysis.low_confidence is True
        assert analysis.confidence_reason == "no_spatial_spread"
        assert analysis.rows[0].fids == (4,)

    def test_every_reason_emitted_belongs_to_the_closed_set(self):
        for records in (_unpositioned_rig_19(), _irregular(), [], _bar_1x30()):
            reason = analyze_spatial_records(records).confidence_reason
            assert reason is None or reason in SPATIAL_LOW_CONFIDENCE_REASONS

    def test_the_flag_is_a_field_on_the_serialised_reply_not_an_out_of_band_note(self):
        reply = spatial_analysis_to_dict(analyze_spatial_records(_unpositioned_rig_19()))
        assert reply["low_confidence"] is True
        assert reply["confidence_reason"] == "no_spatial_spread"
        assert reply["row_order"] == "y_ascending"
        assert reply["row_count"] == 1


# -- The vertical axis: measured, reported, never a row cut ---------------------
#
# Every earlier live run wrote z = 0.0 constant, so the height axis reached
# production having been verified only as a PROPERTY (one fixture written and
# read back) and never as an ARRANGEMENT. Verifying it found a real defect: a
# 5 m vertical column was reported as `no_spatial_spread` -- the reason claims
# the rig has no spatial structure, which was simply false, and it collided with
# the genuinely unpositioned all-(0,0,0) rig. Live-measured both ways, and the
# 3D view confirmed `posz` is height with +z up (progress.md §E.2.18).


class TestVerticalAxisIsMeasuredAndReported:
    def _column(self) -> list[dict]:
        """Six fixtures stacked vertically: only z varies. Half below origin."""
        return [
            {"fid": 11 + i, "name": f"MMX {11 + i}", "x": 0.0, "y": 0.0, "z": -2.5 + i}
            for i in range(6)
        ]

    def _wall_2x3(self) -> list[dict]:
        """A 2-high x 3-wide vertical wall: x and z vary, y is flat."""
        return [
            {
                "fid": 11 + level * 3 + column,
                "name": "w",
                "x": -1.0 + column,
                "y": 0.0,
                "z": -0.5 + level,
            }
            for level in range(2)
            for column in range(3)
        ]

    def test_a_vertical_column_is_not_called_spatially_flat(self):
        # The defect this class exists for. 5 m of vertical spread is spread.
        analysis = analyze_spatial_records(self._column())
        assert analysis.low_confidence is True
        assert analysis.confidence_reason == "vertical_spread_only"
        assert analysis.vertical_span == pytest.approx(5.0)

    def test_a_vertical_rig_and_an_unpositioned_rig_do_not_share_a_reason(self):
        # One means "this vocabulary has no word for your rig's shape", the
        # other means "your showfile has no coordinates". A caller that cannot
        # tell them apart cannot act on either.
        column = analyze_spatial_records(self._column())
        unpositioned = analyze_spatial_records(_unpositioned_rig_19())
        assert column.confidence_reason != unpositioned.confidence_reason
        assert unpositioned.confidence_reason == "no_spatial_spread"
        assert unpositioned.vertical_span == 0.0

    def test_a_vertical_wall_reports_its_height_beside_the_depth_row_count(self):
        # `rows` are DEPTH rows, so ONE row is the true answer for a wall. The
        # bug would be reporting only that: `row_count: 1` alone reads as a flat
        # bar. The preset that builds this asks for rows=2 (in the x/z plane),
        # and a reader must be able to see where that second dimension went.
        analysis = analyze_spatial_records(self._wall_2x3())
        assert analysis.row_count == 1
        assert analysis.vertical_span == pytest.approx(1.0)

    def test_height_never_cuts_a_row(self):
        # The design is y-based rows (design.md §3.1) and this pins it: adding
        # metres of height to a flat bar must not manufacture rows.
        flat = _bar_1x30()
        stacked = [{**record, "z": 3.0 + (index % 4) * 2.0} for index, record in enumerate(flat)]
        assert analyze_spatial_records(stacked).row_count == analyze_spatial_records(flat).row_count

    def test_a_hanging_tolerance_does_not_cry_wolf(self):
        # A real truss hangs with centimetres of variation. If that tripped the
        # vertical signal, the flag would be on for the commonest rig there is.
        bar = [
            {"fid": 11 + i, "name": "b", "x": float(i), "y": 0.0, "z": 3.0 + (0.03 if i % 2 else 0)}
            for i in range(6)
        ]
        analysis = analyze_spatial_records(bar)
        assert analysis.low_confidence is False
        assert analysis.vertical_span == pytest.approx(0.03)

    def test_the_vertical_span_ships_on_the_serialised_reply(self):
        reply = spatial_analysis_to_dict(analyze_spatial_records(self._wall_2x3()))
        assert reply["vertical_span"] == pytest.approx(1.0)
        assert reply["row_count"] == 1

    def test_an_ordinary_flat_rig_reports_zero_height(self):
        # Non-vacuity: the field must be able to be 0.0, or it proves nothing
        # when it is 1.0.
        for records in (_bar_1x30(), _grid_3x10(), _negative_2x4()):
            assert analyze_spatial_records(records).vertical_span == 0.0

    def test_the_new_reason_belongs_to_the_closed_set(self):
        assert "vertical_spread_only" in SPATIAL_LOW_CONFIDENCE_REASONS
        reason = analyze_spatial_records(self._column()).confidence_reason
        assert reason in SPATIAL_LOW_CONFIDENCE_REASONS


# -- The threshold constants, pinned by value AND by behaviour -------------------


class TestThresholdConstantsArePinned:
    def test_the_constants_are_the_chosen_values(self):
        assert SPATIAL_ROW_NOISE_SPAN == 0.05
        assert SPATIAL_ROW_GAP_RATIO == 4.0

    def test_depth_variation_inside_the_noise_span_is_one_row(self):
        # 0.04 apart is hanging tolerance, not two rows.
        records = [_rec(i + 1, float(i), 0.0 if i < 5 else 0.04) for i in range(10)]
        analysis = analyze_spatial_records(records)
        assert analysis.row_count == 1
        assert analysis.low_confidence is False

    def test_depth_variation_just_outside_the_noise_span_splits(self):
        records = [_rec(i + 1, float(i), 0.0 if i < 5 else 0.06) for i in range(10)]
        analysis = analyze_spatial_records(records)
        assert analysis.row_count == 2
        assert [row.fids for row in analysis.rows] == [(1, 2, 3, 4, 5), (6, 7, 8, 9, 10)]

    def test_a_gap_below_the_ratio_threshold_does_not_cut(self):
        # Nine fixtures at 1.0 pitch (median gap 1.0) plus one 3.0 away: the
        # ratio is 3.0, under 4.0, so the structure is not established.
        records = [_rec(i + 1, float(i), float(i)) for i in range(9)]
        records.append(_rec(10, 9.0, 11.0))
        analysis = analyze_spatial_records(records)
        assert analysis.gaps.median_gap == 1.0
        assert analysis.gaps.split_threshold == 4.0
        assert analysis.low_confidence is True
        assert analysis.row_count == 1

    def test_the_same_gap_above_the_ratio_threshold_cuts(self):
        records = [_rec(i + 1, float(i), float(i)) for i in range(9)]
        records.append(_rec(10, 9.0, 13.0))  # gap 5.0 against a median of 1.0
        analysis = analyze_spatial_records(records)
        assert analysis.gaps.max_gap == 5.0
        assert analysis.low_confidence is False
        assert [row.fids for row in analysis.rows] == [tuple(range(1, 10)), (10,)]

    def test_the_gap_profile_is_absent_when_the_analysis_short_circuited(self):
        # "the gap analysis never ran" is a different fact from "it ran and
        # found no boundary" — the None distinguishes them.
        assert analyze_spatial_records(_bar_1x30()).gaps is None
        assert analyze_spatial_records(_unpositioned_rig_19()).gaps is None
        assert analyze_spatial_records(_irregular()).gaps is not None


# -- AC-SPATIAL-010: determinism and the documented tie-break --------------------


class TestDeterminismAndTies:
    def test_the_same_input_produces_an_identical_result_every_time(self):
        records = _grid_3x10()
        first = analyze_spatial_records(records)
        for _ in range(5):
            assert analyze_spatial_records(records) == first

    def test_the_sorted_chains_repeat_exactly(self):
        analysis = analyze_spatial_records(_grid_3x10())
        for sort in SPATIAL_SORTS:
            assert spatial_sorted_fids(analysis, sort) == spatial_sorted_fids(analysis, sort)

    def test_shuffling_the_input_does_not_change_the_output(self):
        # The ordering key is total, so record arrival order cannot leak in.
        records = _grid_3x10()
        expected = analyze_spatial_records(records)
        shuffled = list(records)
        random.Random(20260803).shuffle(shuffled)
        assert shuffled != records
        assert analyze_spatial_records(shuffled) == expected

    def test_two_fixtures_on_one_truss_point_order_by_fid_ascending(self):
        # Identical x and y, fids out of order in the input. The tie-break is a
        # DOCUMENTED key, not an arbitrary pick — that is what AC-SPATIAL-010
        # and the §D edge case reconcile on.
        records = [_rec(7, 2.0, 0.0), _rec(3, 2.0, 0.0)]
        analysis = analyze_spatial_records(records)
        assert analysis.rows[0].fids == (3, 7)
        assert analyze_spatial_records(list(reversed(records))).rows[0].fids == (3, 7)

    def test_a_tie_inside_a_populated_bar_resolves_by_fid_in_every_sort(self):
        # fids 11 and 12 share the truss point at x = 0.0.
        records = [_rec(1, -2.0, 0.0), _rec(2, 2.0, 0.0), _rec(12, 0.0, 0.0), _rec(11, 0.0, 0.0)]
        analysis = analyze_spatial_records(records)
        assert spatial_sorted_fids(analysis, "left_to_right") == (1, 11, 12, 2)
        assert spatial_sorted_fids(analysis, "right_to_left") == (2, 11, 12, 1)
        # center_x is 0.0, so the tied pair sits at distance 0 and leads.
        assert spatial_sorted_fids(analysis, "center_out") == (11, 12, 1, 2)
        assert spatial_sorted_fids(analysis, "diagonal") == (1, 11, 12, 2)

    def test_a_mirrored_center_out_pair_resolves_by_fid_not_by_side(self):
        # Equal |x - center_x| is a tie on the sort key even though the
        # coordinates differ; the same single rule settles it.
        records = [_rec(9, -3.0, 0.0), _rec(4, 3.0, 0.0), _rec(1, 0.0, 0.0)]
        analysis = analyze_spatial_records(records)
        assert spatial_sorted_fids(analysis, "center_out") == (1, 4, 9)

    def test_a_duplicate_fid_is_refused_rather_than_ordered_arbitrarily(self):
        # A repeated console id makes the last-resort key non-total, which is
        # precisely the silent arbitrary choice the AC forbids.
        with pytest.raises(SpatialAnalysisError, match="duplicate fid"):
            spatial_fixtures_from_records([_rec(5, 0.0, 0.0), _rec(5, 1.0, 0.0)])


# -- AC-SPATIAL-012: the four sorts, against hand-computed orders ----------------


class TestSortVocabularyIsClosed:
    def test_the_vocabulary_is_exactly_the_four_names_from_the_design(self):
        assert SPATIAL_SORTS == EXPECTED_SORTS

    def test_an_unknown_sort_name_raises_instead_of_falling_back(self):
        analysis = analyze_spatial_records(_grid_3x10())
        for name in ("Left_To_Right", "clockwise", "", "back_to_front"):
            with pytest.raises(SpatialAnalysisError, match="is not a spatial sort"):
                spatial_sorted_fids(analysis, name)

    def test_every_sort_returns_every_fixture_exactly_once(self):
        analysis = analyze_spatial_records(_grid_3x10())
        for sort in SPATIAL_SORTS:
            chain = spatial_sorted_fids(analysis, sort)
            assert sorted(chain) == list(range(1, 31))


class TestSortOrdersOnTheThreeRowGrid:
    """Layout 1 of the two AC-SPATIAL-012 requires per sort."""

    @pytest.fixture
    def analysis(self):
        return analyze_spatial_records(_grid_3x10())

    def test_left_to_right_walks_each_row_from_stage_left(self, analysis):
        assert spatial_sorted_fids(analysis, "left_to_right") == tuple(range(1, 31))

    def test_right_to_left_reverses_within_each_row_but_not_across_rows(self, analysis):
        # Rows stay front-to-back; only the within-row direction flips.
        assert spatial_sorted_fids(analysis, "right_to_left") == (
            10, 9, 8, 7, 6, 5, 4, 3, 2, 1,
            20, 19, 18, 17, 16, 15, 14, 13, 12, 11,
            30, 29, 28, 27, 26, 25, 24, 23, 22, 21,
        )  # fmt: skip

    def test_center_out_leaves_the_row_middle_and_alternates_outward(self, analysis):
        # Row x runs -4.5..4.5, so center_x is 0.0 and the innermost pair
        # (x = -0.5 / +0.5) ties at distance 0.5, settled by fid.
        assert spatial_sorted_fids(analysis, "center_out") == (
            5, 6, 4, 7, 3, 8, 2, 9, 1, 10,
            15, 16, 14, 17, 13, 18, 12, 19, 11, 20,
            25, 26, 24, 27, 23, 28, 22, 29, 21, 30,
        )  # fmt: skip

    def test_diagonal_sweeps_an_anti_diagonal_wavefront_across_the_rows(self, analysis):
        # Ordered by (row index + column index), front row first inside each
        # wavefront: 1 | 2,11 | 3,12,21 | 4,13,22 | ... | 20,29 | 30.
        assert spatial_sorted_fids(analysis, "diagonal") == (
            1,
            2, 11,
            3, 12, 21,
            4, 13, 22,
            5, 14, 23,
            6, 15, 24,
            7, 16, 25,
            8, 17, 26,
            9, 18, 27,
            10, 19, 28,
            20, 29,
            30,
        )  # fmt: skip

    def test_the_single_bar_gives_a_different_chain_for_the_same_sort(self, analysis):
        # Scenario 1, at the chain level rather than the row-count level.
        bar = analyze_spatial_records(_bar_1x30())
        assert spatial_sorted_fids(bar, "diagonal") != spatial_sorted_fids(analysis, "diagonal")
        # On one row a diagonal has no second axis to cross, so it degenerates
        # to left_to_right — the right answer, not a missing case.
        assert spatial_sorted_fids(bar, "diagonal") == spatial_sorted_fids(bar, "left_to_right")


class TestSortOrdersOnNegativeCoordinates:
    """Layout 2 — signs carried through every sort (acceptance.md §D)."""

    @pytest.fixture
    def analysis(self):
        return analyze_spatial_records(_negative_2x4())

    def test_negative_depths_still_cluster_into_two_rows_front_to_back(self, analysis):
        assert [row.fids for row in analysis.rows] == [(1, 2, 3, 4), (5, 6, 7, 8)]
        assert [row.center_y for row in analysis.rows] == [-6.0, -2.0]
        assert analysis.low_confidence is False

    def test_the_row_center_is_the_midpoint_of_its_x_extent_sign_included(self, analysis):
        # Row 1 spans -4.0..2.0, so its centre is at -1.0 — a negative centre
        # is normal and center_out must measure from it, not from the origin.
        assert [row.center_x for row in analysis.rows] == [0.0, -1.0]

    def test_left_to_right_ascends_x_through_the_negative_half(self, analysis):
        assert spatial_sorted_fids(analysis, "left_to_right") == (1, 2, 3, 4, 5, 6, 7, 8)

    def test_right_to_left_descends_x_and_ends_on_the_most_negative(self, analysis):
        assert spatial_sorted_fids(analysis, "right_to_left") == (4, 3, 2, 1, 8, 7, 6, 5)

    def test_center_out_measures_absolute_distance_from_each_rows_own_centre(self, analysis):
        # Row 0 (centre 0.0): |−1|=|1|=1 -> fids 2,3; then |−3|=|3|=3 -> 1,4.
        # Row 1 (centre −1.0): |−2−(−1)|=|0−(−1)|=1 -> 6,7; then 3 -> 5,8.
        assert spatial_sorted_fids(analysis, "center_out") == (2, 3, 1, 4, 6, 7, 5, 8)

    def test_diagonal_combines_row_order_with_within_row_x_order(self, analysis):
        # (row + column): 0 | 1 -> 2,5 | 2 -> 3,6 | 3 -> 4,7 | 4 -> 8.
        assert spatial_sorted_fids(analysis, "diagonal") == (1, 2, 5, 3, 6, 4, 7, 8)

    def test_a_low_confidence_analysis_still_sorts(self):
        # The fallback row is a real row; refusing to compute would push the
        # caller into inventing its own order.
        analysis = analyze_spatial_records(_unpositioned_rig_19())
        assert spatial_sorted_fids(analysis, "left_to_right") == tuple(range(1, 20))
        assert spatial_sorted_fids(analysis, "right_to_left") == tuple(range(1, 20))


# -- Coordinates are read, never invented (REQ-SPATIAL-004 at this layer) --------


class TestRecordParsing:
    def test_a_missing_coordinate_is_refused_rather_than_defaulted_to_zero(self):
        # A zero written in here is indistinguishable from a real (0,0,0)
        # patch, and the two must never converge.
        with pytest.raises(SpatialAnalysisError, match="missing coordinate 'z'"):
            spatial_fixtures_from_records([{"fid": 1, "name": "PAR 1", "x": 0.0, "y": 0.0}])

    def test_a_non_numeric_coordinate_is_refused(self):
        with pytest.raises(SpatialAnalysisError, match="must be a number"):
            spatial_fixtures_from_records([{"fid": 1, "x": "0.0", "y": 0.0, "z": 0.0}])

    def test_a_boolean_is_not_accepted_as_a_fid_or_a_coordinate(self):
        with pytest.raises(SpatialAnalysisError, match="'fid' must be an int"):
            spatial_fixtures_from_records([_rec(True, 0.0, 0.0)])  # type: ignore[arg-type]
        with pytest.raises(SpatialAnalysisError, match="must be a number"):
            spatial_fixtures_from_records([{"fid": 1, "x": False, "y": 0.0, "z": 0.0}])

    def test_integer_coordinates_are_accepted_and_normalised_to_float(self):
        fixture = spatial_fixtures_from_records([{"fid": 2, "x": -4, "y": 0, "z": 3}])[0]
        assert (fixture.x, fixture.y, fixture.z) == (-4.0, 0.0, 3.0)
        assert isinstance(fixture.x, float)

    def test_extra_keys_from_the_read_tool_pass_through_without_rejection(self):
        # The read tool owns the wire shape and may carry provenance alongside
        # the coordinates; closing the key set here would couple this layer to
        # the tool's version.
        record = {"fid": 3, "name": "PAR 3", "x": 1.0, "y": 2.0, "z": 3.0, "source": "patch3d"}
        assert spatial_fixtures_from_records([record])[0].fid == 3


# -- AC-SPATIAL-013: the boundary ------------------------------------------------


class TestAnalysisLayerBoundary:
    """`server/spatial/` reaches no transport and no gate surface."""

    _IMPORT_LINE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.MULTILINE)
    _FORBIDDEN = ("server.bridge", "server.safety", "server.orchestrator", "pythonosc")

    def _modules(self) -> dict[str, list[str]]:
        return {
            source.name: self._IMPORT_LINE.findall(source.read_text(encoding="utf-8"))
            for source in sorted(SPATIAL_DIR.glob("*.py"))
        }

    def test_the_package_has_modules_to_scan(self):
        # Positive control: an empty scan would pass every assertion below.
        assert set(self._modules()) >= {"__init__.py", "schema.py", "rows.py", "sorting.py"}

    def test_no_module_imports_transport_or_gate_surfaces(self):
        violations = [
            f"{name} imports {module}"
            for name, modules in self._modules().items()
            for module in modules
            if module.startswith(self._FORBIDDEN)
        ]
        assert violations == []

    def test_the_package_has_no_third_party_imports_at_all(self):
        # design.md §3.1 — row detection is standard-library arithmetic. A
        # clustering library appearing here is a dependency AND a hidden
        # threshold that no golden can pin.
        foreign = [
            f"{name} imports {module}"
            for name, modules in self._modules().items()
            for module in modules
            if module.split(".")[0] not in sys.stdlib_module_names
            and not module.startswith("server.spatial")
        ]
        assert foreign == []

    def test_the_global_architecture_scan_covers_this_package_without_an_exemption(self):
        # AC-SPATIAL-013 requires automatic inclusion, not a whitelist entry:
        # the sweep is `SERVER_DIR.rglob("*.py")`, so a new package is covered
        # the moment it exists. Named exemptions must not mention it.
        architecture = (SPATIAL_DIR.parent / "tests" / "test_architecture.py").read_text(
            encoding="utf-8"
        )
        assert 'SERVER_DIR.rglob("*.py")' in architecture
        assert "spatial" not in architecture
