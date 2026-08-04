"""Tests for server/spatial/topology.py (SPEC-COPILOT-GROUPGEN-001, M1).

Golden scenarios per design.md §2.5. AC-GROUPGEN-003's non-vacuousness
mutation is the load-bearing test in this file: the real classifier must
tell a two-ring concentric rig apart from a 3x10 grid, AND a stub that
always answers ``depth_rows`` must visibly fail to do so.
"""

from __future__ import annotations

import math

import pytest

from server.spatial.schema import SpatialFixture
from server.spatial.topology import (
    TopologyClassification,
    TopologyResult,
    classify,
    detect_bilateral_pairs,
    detect_concentric,
    detect_depth_rows,
    detect_grid,
    detect_lateral_split,
    detect_vertical_levels,
)


def _fx(fid: int, x: float, y: float, z: float = 0.0, name: str = "") -> SpatialFixture:
    return SpatialFixture(fid=fid, name=name or f"Fx{fid}", x=x, y=y, z=z)


# ---------------------------------------------------------------------------
# Golden fixture builders (design.md §2.5)
# ---------------------------------------------------------------------------


def _golden_bar(count: int = 10) -> tuple[SpatialFixture, ...]:
    """1xN bar: y flat, x spread evenly. Expect depth_rows (1 row).

    Deliberately NOT centred on x=0: a symmetric spread would also read as a
    perfect mirror on the radius axis (|x| repeats in pairs), which is a
    different accidental structure this golden must not exercise.
    """
    return tuple(_fx(i + 1, x=i * 1.0, y=0.0, z=0.0) for i in range(count))


def _golden_grid() -> tuple[SpatialFixture, ...]:
    """3x10 grid: y in {0, 3, 6}, x in 10 evenly-spaced columns. Expect grid."""
    fixtures = []
    fid = 1
    for y in (0.0, 3.0, 6.0):
        for col_index in range(10):
            x = (col_index - 4.5) * 1.0
            fixtures.append(_fx(fid, x=x, y=y, z=0.0))
            fid += 1
    return tuple(fixtures)


def _golden_concentric() -> tuple[SpatialFixture, ...]:
    """Two-ring concentric: inner 6 @ r=2.0, outer 12 @ r=5.0
    (research.md §3 exact figures — the fixture set that reproduces the
    rows=9 misread)."""
    fixtures = []
    fid = 1
    for i in range(6):
        angle = 2 * math.pi * i / 6
        fixtures.append(_fx(fid, x=2.0 * math.cos(angle), y=2.0 * math.sin(angle)))
        fid += 1
    for i in range(12):
        angle = 2 * math.pi * i / 12
        fixtures.append(_fx(fid, x=5.0 * math.cos(angle), y=5.0 * math.sin(angle)))
        fid += 1
    return tuple(fixtures)


def _golden_lateral_split() -> tuple[SpatialFixture, ...]:
    """Left/right 2-way split: x gap-separated, y uniform."""
    left = [_fx(i + 1, x=-5.0 - i * 0.3, y=0.0) for i in range(4)]
    right = [_fx(i + 5, x=5.0 + i * 0.3, y=0.0) for i in range(4)]
    return tuple(left + right)


def _golden_vertical_levels() -> tuple[SpatialFixture, ...]:
    """3-tier vertical: z gap-separated, x/y uniform per tier."""
    fixtures = []
    fid = 1
    for z in (0.0, 3.0, 6.0):
        for i in range(4):
            fixtures.append(_fx(fid, x=i * 0.5, y=0.0, z=z))
            fid += 1
    return tuple(fixtures)


def _golden_irregular() -> tuple[SpatialFixture, ...]:
    """Scattered, no axis structurally clear. Expect kind=None, low_confidence."""
    coords = [
        (0.0, 0.0),
        (1.3, 0.7),
        (-2.1, 1.9),
        (0.4, -1.6),
        (2.8, 2.2),
        (-1.1, -0.4),
        (1.9, -2.3),
    ]
    return tuple(_fx(i + 1, x=x, y=y, z=(i % 3) * 0.02) for i, (x, y) in enumerate(coords))


def _golden_all_origin(count: int = 5) -> tuple[SpatialFixture, ...]:
    """All fixtures at the exact same coordinates. Expect kind=None,
    low_confidence (gap analysis cannot run — zero spread on every axis)."""
    return tuple(_fx(i + 1, x=0.0, y=0.0, z=0.0) for i in range(count))


def _golden_bilateral() -> tuple[SpatialFixture, ...]:
    """x=0 mirror-symmetric placement. Expect bilateral_pairs signal."""
    fixtures = []
    fid = 1
    for i in range(5):
        x = 1.0 + i * 0.8
        y = i * 0.5
        fixtures.append(_fx(fid, x=x, y=y))
        fid += 1
        fixtures.append(_fx(fid, x=-x, y=y))
        fid += 1
    return tuple(fixtures)


# ---------------------------------------------------------------------------
# Type invariant (design.md §2.2 [HARD] — the M1/M2 cross-contract)
# ---------------------------------------------------------------------------


class TestTypeInvariant:
    def test_grid_requires_empty_fids_by_bucket(self):
        with pytest.raises(ValueError):
            TopologyResult(
                kind="grid",
                fids_by_bucket=((1, 2),),
                low_confidence=False,
                grid_axes={"depth": ((1,), (2,)), "lateral": ((1,), (2,))},
            )

    def test_grid_requires_grid_axes(self):
        with pytest.raises(ValueError):
            TopologyResult(kind="grid", fids_by_bucket=(), low_confidence=False, grid_axes=None)

    def test_non_grid_forbids_grid_axes(self):
        with pytest.raises(ValueError):
            TopologyResult(
                kind="depth_rows",
                fids_by_bucket=((1, 2),),
                low_confidence=False,
                grid_axes={"depth": ((1,), (2,))},
            )

    def test_none_kind_forbids_grid_axes(self):
        with pytest.raises(ValueError):
            TopologyResult(
                kind=None, fids_by_bucket=(), low_confidence=True, reason="x", grid_axes={}
            )

    def test_valid_grid_result_constructs(self):
        result = TopologyResult(
            kind="grid",
            fids_by_bucket=(),
            low_confidence=False,
            grid_axes={"depth": ((1,), (2,)), "lateral": ((1,), (2,))},
        )
        assert result.grid_axes is not None

    def test_valid_non_grid_result_constructs(self):
        result = TopologyResult(kind="depth_rows", fids_by_bucket=((1, 2),), low_confidence=False)
        assert result.grid_axes is None

    def test_classify_output_satisfies_invariant_on_every_golden(self):
        for fixtures in (
            _golden_bar(),
            _golden_grid(),
            _golden_concentric(),
            _golden_lateral_split(),
            _golden_vertical_levels(),
            _golden_irregular(),
            _golden_all_origin(),
            _golden_bilateral(),
        ):
            result = classify(fixtures).selected
            if result.kind == "grid":
                assert result.fids_by_bucket == ()
                assert result.grid_axes is not None
            else:
                assert result.grid_axes is None


# ---------------------------------------------------------------------------
# Golden scenarios (design.md §2.5)
# ---------------------------------------------------------------------------


class TestGoldenScenarios:
    def test_bar_is_depth_rows(self):
        result = classify(_golden_bar()).selected
        assert result.kind == "depth_rows"
        assert result.low_confidence is False

    def test_grid_is_grid(self):
        result = classify(_golden_grid()).selected
        assert result.kind == "grid"
        assert result.low_confidence is False
        assert result.fids_by_bucket == ()
        assert result.grid_axes is not None
        assert len(result.grid_axes["depth"]) == 3
        assert len(result.grid_axes["lateral"]) == 10

    def test_concentric_is_concentric(self):
        result = classify(_golden_concentric()).selected
        assert result.kind == "concentric"
        assert result.low_confidence is False
        assert len(result.fids_by_bucket) == 2
        bucket_sizes = sorted(len(bucket) for bucket in result.fids_by_bucket)
        assert bucket_sizes == [6, 12]

    def test_lateral_split_is_lateral_split(self):
        result = classify(_golden_lateral_split()).selected
        assert result.kind == "lateral_split"
        assert result.low_confidence is False
        assert len(result.fids_by_bucket) == 2

    def test_vertical_levels_is_vertical_levels(self):
        result = classify(_golden_vertical_levels()).selected
        assert result.kind == "vertical_levels"
        assert result.low_confidence is False
        assert len(result.fids_by_bucket) == 3

    def test_irregular_is_low_confidence_none(self):
        result = classify(_golden_irregular()).selected
        assert result.kind is None
        assert result.low_confidence is True

    def test_all_origin_is_low_confidence_none(self):
        result = classify(_golden_all_origin()).selected
        assert result.kind is None
        assert result.low_confidence is True

    def test_bilateral_pairs_signal_detected(self):
        result = detect_bilateral_pairs(_golden_bilateral())
        assert result.kind == "bilateral_pairs"
        assert result.low_confidence is False
        assert len(result.fids_by_bucket) == 5
        for pair in result.fids_by_bucket:
            assert len(pair) == 2


# ---------------------------------------------------------------------------
# AC-GROUPGEN-003 — non-vacuousness (the SPEC's reason to exist)
# ---------------------------------------------------------------------------


def _stub_always_depth_rows(fixtures: tuple[SpatialFixture, ...]) -> TopologyClassification:
    """A classifier that only ever consults the depth_rows detector — the
    exact shape of the pre-existing rows.py-only bug (research.md §3).
    Reproducing that bug here, and showing the real classifier does NOT
    reproduce it, is the non-vacuousness proof AC-GROUPGEN-003 requires.
    """
    depth = detect_depth_rows(fixtures)
    return TopologyClassification(selected=depth, candidates=(depth,))


class TestNonVacuousness:
    def test_concentric_and_grid_are_structurally_distinct(self):
        concentric_fixtures = _golden_concentric()
        grid_fixtures = _golden_grid()

        real_concentric = classify(concentric_fixtures).selected
        real_grid = classify(grid_fixtures).selected

        # (a) the real classifier answers with two different tokens.
        assert real_concentric.kind == "concentric"
        assert real_grid.kind == "grid"
        assert real_concentric.kind != real_grid.kind

        # (b) a classifier stubbed down to "always depth_rows" reproduces
        # the known rows=9 misread instead of "concentric" — proven by
        # showing the would-be assertion goes RED.
        stub_result = _stub_always_depth_rows(concentric_fixtures)
        assert stub_result.selected.kind == "depth_rows"
        with pytest.raises(AssertionError):
            assert stub_result.selected.kind == "concentric"


# ---------------------------------------------------------------------------
# Determinism (REQ-GROUPGEN-002)
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.mark.parametrize(
        "builder",
        [
            _golden_bar,
            _golden_grid,
            _golden_concentric,
            _golden_lateral_split,
            _golden_vertical_levels,
            _golden_irregular,
            _golden_all_origin,
            _golden_bilateral,
        ],
    )
    def test_same_input_same_output(self, builder):
        fixtures = builder()
        first = classify(fixtures)
        second = classify(fixtures)
        assert first.selected == second.selected
        assert first.candidates == second.candidates

    def test_shuffled_input_order_same_output(self):
        fixtures = _golden_concentric()
        shuffled = tuple(reversed(fixtures))
        assert classify(fixtures).selected == classify(shuffled).selected


# ---------------------------------------------------------------------------
# Individual detectors are independently callable (design.md §2.2)
# ---------------------------------------------------------------------------


class TestIndividualDetectors:
    def test_detect_depth_rows_on_bar(self):
        result = detect_depth_rows(_golden_bar())
        assert result.kind == "depth_rows"

    def test_detect_lateral_split_on_split(self):
        result = detect_lateral_split(_golden_lateral_split())
        assert result.kind == "lateral_split"

    def test_detect_concentric_on_rings(self):
        result = detect_concentric(_golden_concentric())
        assert result.kind == "concentric"

    def test_detect_vertical_levels_on_tiers(self):
        result = detect_vertical_levels(_golden_vertical_levels())
        assert result.kind == "vertical_levels"

    def test_detect_grid_on_grid(self):
        result = detect_grid(_golden_grid())
        assert result.kind == "grid"

    def test_detect_grid_on_bar_is_not_grid(self):
        result = detect_grid(_golden_bar())
        assert result.kind is None

    def test_empty_fixtures_every_detector_is_low_confidence(self):
        empty: tuple[SpatialFixture, ...] = ()
        for detector in (
            detect_depth_rows,
            detect_lateral_split,
            detect_concentric,
            detect_vertical_levels,
            detect_bilateral_pairs,
            detect_grid,
        ):
            result = detector(empty)
            assert result.low_confidence is True
            assert result.kind is None


# ---------------------------------------------------------------------------
# M6 live-found contention defects (REQ-GROUPGEN-003 · D-Q10)
# ---------------------------------------------------------------------------


def _flat_row(xs: list[float]) -> tuple[SpatialFixture, ...]:
    """A rig spread on x only — y and z flat."""
    return tuple(
        SpatialFixture(fid=index, name=f"F{index}", x=float(value), y=0.0, z=0.0)
        for index, value in enumerate(xs, start=1)
    )


#: The exact arrangement M6 stage 3 wrote to the live console: 9 fixtures
#: stage-right, 9 stage-left, mirror-symmetric about the origin, y and z flat.
_MIRRORED_LEFT_RIGHT = [-11, -10, -9, -8, -7, -6, -5, -4, -3, 3, 4, 5, 6, 7, 8, 9, 10, 11]


def test_mirrored_left_right_rig_is_lateral_not_nine_rings():
    """A rig a designer calls "left/right" must not come back as 9 rings of 2.

    Live-measured in M6 stage 3 BEFORE the fix: radius-from-origin collapses to
    ``|x|`` on a mirror-symmetric flat rig, so every radius held exactly one
    pair and ``concentric`` scored 20.0 against ``lateral_split``'s 0.75 —
    winning with ``buckets=[2]*9``. That is the MIRROR IMAGE of the defect this
    SPEC exists to fix (research.md §3: a 2-ring rig misread as 9 rows).

    MUTATION: remove the mirror-artefact demotion in ``classify`` and this goes
    RED with ``concentric`` and nine 2-member buckets.
    """
    classification = classify(_flat_row(_MIRRORED_LEFT_RIGHT))
    selected = classification.selected

    assert selected.kind == "lateral_split"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [9, 9]

    # the radius reading is still REPORTED, and says why it was set aside
    concentric = [
        c
        for c in classification.candidates
        if c.reason == "concentric_reading_is_a_mirror_artefact"
    ]
    assert len(concentric) == 1
    assert concentric[0].kind is None
    assert concentric[0].low_confidence is True


def test_bilateral_pairs_is_reported_but_never_selected():
    """D-Q10 — symmetry is a SIGNAL, never a group, so it must not win.

    ``naming.py`` deliberately has no vocabulary for ``bilateral_pairs``, so a
    selected ``bilateral_pairs`` yields zero suggested groups — which reads as
    "found nothing" when the tool in fact found a symmetric rig it must not
    name. Live-found in M6 stage 3, where demoting the mirror artefact handed
    ``bilateral_pairs`` the win.

    MUTATION: put ``(bilateral, bilateral_score)`` back into ``scored`` and this
    goes RED.
    """
    classification = classify(_flat_row(_MIRRORED_LEFT_RIGHT))

    assert classification.selected.kind != "bilateral_pairs"
    # but it IS reported, confidently, among the candidates
    bilateral = [c for c in classification.candidates if c.kind == "bilateral_pairs"]
    assert len(bilateral) == 1
    assert bilateral[0].low_confidence is False


def test_a_genuine_two_ring_rig_still_wins_as_concentric():
    """Non-vacuity guard for the demotion: it must not eat real rings.

    The demotion is narrow on purpose — it fires only when EVERY radius bucket
    holds exactly 2 and ``bilateral_pairs`` is confident. A real 2-ring rig has
    6 and 12 members, so it is untouched.
    """
    fixtures = _golden_concentric()
    selected = classify(fixtures).selected

    assert selected.kind == "concentric"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [6, 12]
