"""Tests for server/spatial/topology.py (SPEC-COPILOT-GROUPGEN-001, M1).

Golden scenarios per design.md §2.5. AC-GROUPGEN-003's non-vacuousness
mutation is the load-bearing test in this file: the real classifier must
tell a two-ring concentric rig apart from a 3x10 grid, AND a stub that
always answers ``depth_rows`` must visibly fail to do so.
"""

from __future__ import annotations

import math

import pytest

from server.spatial.rows import (
    SPATIAL_ROW_GAP_RATIO,
    SPATIAL_ROW_NOISE_SPAN,
    analyze_spatial_rows,
)
from server.spatial.schema import SpatialFixture
from server.spatial.topology import (
    AXIS_TIE_BREAK_ORDER,
    TopologyClassification,
    TopologyResult,
    _compute_bilateral,
    _compute_concentric,
    _compute_depth,
    _compute_lateral,
    _compute_vertical,
    _partition_score,
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

    The demotion keys on the COLLAPSE — a rig flat in y, where
    ``math.hypot(x, y)`` is just ``|x|``. A real 2-ring rig spreads over y
    (here -5.0..5.0), so the radius it measures is a real radius and the
    demotion never fires: the candidate comes back confident, not set aside.
    """
    fixtures = _golden_concentric()
    classification = classify(fixtures)
    selected = classification.selected

    assert selected.kind == "concentric"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [6, 12]

    # and the demotion demonstrably did NOT fire here
    assert all(
        c.reason != "concentric_reading_is_a_mirror_artefact" for c in classification.candidates
    )


def _concentric_candidate(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult:
    """The radius reading as ``classify`` finally reported it (post-demotion)."""
    candidates = classify(fixtures).candidates
    radius = [
        c
        for c in candidates
        if c.kind == "concentric" or c.reason == "concentric_reading_is_a_mirror_artefact"
    ]
    assert len(radius) == 1, f"expected exactly one radius candidate, got {radius}"
    return radius[0]


def test_flat_mirror_rig_plus_one_spare_fixture_is_still_lateral_not_rings():
    """Review-found: the demotion must key on the COLLAPSE, not on the M6
    rig's fingerprint.

    The first version of the guard required every radius bucket to hold
    exactly 2 AND ``bilateral_pairs`` to be confident. Both are accidents of
    that particular 18-fixture rig. Adding ONE spare fixture at x=-3.0 breaks
    both at once — the r=3 bucket now holds 3, and ``bilateral_pairs`` drops
    to ``partial_bilateral_symmetry`` — so the guard stopped firing and
    ``concentric`` came back with ``buckets=[3,2,2,2,2,2,2,2,2]``
    (live-measured: score 20.00 against ``lateral_split``'s 0.75).

    MUTATION: key the demotion on the fingerprint again (all buckets == 2 and
    a confident ``bilateral_pairs``) and this goes RED with ``concentric``.
    """
    fixtures = _flat_row([*_MIRRORED_LEFT_RIGHT, -3])
    classification = classify(fixtures)
    selected = classification.selected

    assert selected.kind == "lateral_split"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [10, 9]

    # the two fingerprint conditions really are both broken on this rig — so
    # this test cannot pass by accidentally still matching the old guard.
    radius = _concentric_candidate(fixtures)
    assert radius.reason == "concentric_reading_is_a_mirror_artefact"
    assert radius.kind is None
    assert radius.low_confidence is True
    raw_radius = detect_concentric(fixtures)
    assert [len(bucket) for bucket in raw_radius.fids_by_bucket] == [3, 2, 2, 2, 2, 2, 2, 2, 2]
    bilateral = detect_bilateral_pairs(fixtures)
    assert bilateral.kind is None
    assert bilateral.reason == "partial_bilateral_symmetry"


def test_flat_mirror_rig_plus_a_centre_fixture_is_not_rings():
    """The second independent escape from the fingerprint.

    One fixture at x=0.0 gives the radius axis a bucket of 1 (r=0) against a
    bucket of 18, so ``all(len(bucket) == 2)`` fails again — and this time it
    also softens the x gaps enough that ``lateral_split`` itself goes
    low-confidence, so no other confident axis is left to outscore the radius
    reading. Live-measured before the fix: ``concentric`` with
    ``buckets=[1, 18]``. The honest answer is the one depth row the rig
    actually is.

    MUTATION: key the demotion on the fingerprint again and this goes RED with
    ``concentric`` and ``buckets=[1, 18]``.
    """
    fixtures = _flat_row([*_MIRRORED_LEFT_RIGHT, 0])
    classification = classify(fixtures)

    assert classification.selected.kind == "depth_rows"
    assert _concentric_candidate(fixtures).reason == "concentric_reading_is_a_mirror_artefact"
    # non-vacuity: lateral really is out of the running here, so the verdict
    # rests on the demotion rather than on lateral outscoring the radius.
    assert detect_lateral_split(fixtures).kind is None


@pytest.mark.parametrize(
    "xs",
    [
        pytest.param([*_MIRRORED_LEFT_RIGHT, -3], id="m6-spare-left"),
        pytest.param([*_MIRRORED_LEFT_RIGHT, 11], id="m6-spare-right"),
        pytest.param([*_MIRRORED_LEFT_RIGHT, 0], id="m6-centre"),
        pytest.param([-4, -3, -2, -1, 1, 2, 3, 4, -2], id="mirror-4x2-dup"),
        pytest.param([-10, -8, -6, -4, -2, 2, 4, 6, 8, 10, -6], id="mirror-5x2-dup"),
        pytest.param([-9, -8, -7, -3, -2, -1, 1, 2, 3, 7, 8, 9, -8], id="mirror-gapped-dup"),
    ],
)
def test_no_flat_mirror_bar_variant_is_ever_read_as_rings(xs):
    """Breadth: the fingerprint guard let SIX of fifteen measured flat
    mirror-bar swatches back through as ``concentric``. A rig with no depth at
    all has no rings to find, whatever its x values are.

    MUTATION: key the demotion on the fingerprint again and every case here
    goes RED.
    """
    fixtures = _flat_row(xs)

    # non-vacuity: the radius axis DOES answer confidently on each of these —
    # the demotion is what keeps it from winning, not a lack of separation.
    assert detect_concentric(fixtures).kind == "concentric"

    assert classify(fixtures).selected.kind != "concentric"
    assert _concentric_candidate(fixtures).reason == "concentric_reading_is_a_mirror_artefact"


def _electrics_three_bars() -> tuple[SpatialFixture, ...]:
    """Three electrics: three depth rows (y=0/3/6) hung at three trims
    (z=5.0/6.5/8.0), x staggered per bar so no lateral gap is clean.

    ``depth_rows`` and ``vertical_levels`` answer with the SAME partition
    ([5,5,5]) here, so the only thing at stake is which vocabulary the
    operator is handed.
    """
    fixtures = []
    fid = 1
    for row, (y, z) in enumerate(((0.0, 5.0), (3.0, 6.5), (6.0, 8.0))):
        for column in range(5):
            fixtures.append(_fx(fid, x=column * 2.0 + row * 0.7, y=y, z=z))
            fid += 1
    return tuple(fixtures)


def _three_rows_two_trims() -> tuple[SpatialFixture, ...]:
    """Three depth rows (y=0/3/6) crossed with only TWO trim heights — the
    front two rows share z=5.0. The z reading therefore MERGES two rows into
    one bucket ([10,5]) where the y reading keeps all three ([5,5,5])."""
    fixtures = []
    fid = 1
    for row, (y, z) in enumerate(((0.0, 5.0), (3.0, 5.0), (6.0, 9.0))):
        for column in range(5):
            fixtures.append(_fx(fid, x=column * 2.0 + row * 0.7, y=y, z=z))
            fid += 1
    return tuple(fixtures)


def test_perfectly_aligned_rows_outscore_a_ring_rigs_spurious_rows():
    """Review-found: the depth score was zeroed on exactly the rigs
    ``depth_rows`` answers best.

    The scoring branch used to also require ``median_gap > 0``, but
    ``rows.py``'s own docstring says a real multi-row rig collapses its
    within-row gaps to zero — so a clean 3x10 grid scored 0.0 while the
    two-ring rig whose nine "rows" are an artefact scored 36.60. The ranking
    ran backwards.

    MUTATION: restore ``and analysis.gaps.median_gap > 0`` in
    ``_compute_depth`` and this goes RED (aligned score back to 0.0).
    """
    aligned_score = _compute_depth(_golden_grid())[1]
    spurious_score = _compute_depth(_golden_concentric())[1]

    assert aligned_score > 0.0
    assert spurious_score > 0.0, "non-vacuity: the artefact rig must still score something"
    assert aligned_score > spurious_score


def test_three_electrics_are_depth_rows_not_vertical_levels():
    """User-settled policy: an electrics rig is named front/mid/back, and its
    trim heights are incidental.

    Both readings are confident and produce the IDENTICAL partition [5,5,5],
    so nothing about the grouping is at stake — only which vocabulary the
    operator is handed. z won the live measurement 30.00 to depth's 0.00.

    AXISCORE-001 deleted the exclusion rule this test was written against, so
    ``vertical`` is now permanently in contention. The rig is unchanged and the
    answer is unchanged, but the reason is different: the two readings score an
    EXACT tie (0.3333 each — both partition perfectly, both leave a 5-of-15
    smallest bucket) and ``AXIS_TIE_BREAK_ORDER`` picks depth. The live
    measurement that motivated the policy, z winning on 30.00 against depth's
    60.00, is no longer expressible: neither number is in metres any more.

    MUTATION: reverse ``AXIS_TIE_BREAK_ORDER`` and this goes RED. So does
    restoring the ``median_gap > 0`` guard in ``_compute_depth``, which zeroes
    the depth score and hands the rig to z outright.
    """
    fixtures = _electrics_three_bars()
    classification = classify(fixtures)
    selected = classification.selected

    assert selected.kind == "depth_rows"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [5, 5, 5]

    # the z reading is set aside, never falsified: it stays in candidates,
    # confident, with the same partition it measured.
    vertical = [c for c in classification.candidates if c.kind == "vertical_levels"]
    assert len(vertical) == 1
    assert vertical[0].low_confidence is False
    assert [len(bucket) for bucket in vertical[0].fids_by_bucket] == [5, 5, 5]


def test_depth_rows_beats_a_vertical_reading_that_merges_two_rows():
    """The same rig where the two readings DISAGREE about the partition.

    Three rows across two trims: the z reading answers [10,5] — two depth rows
    fused into one group — and it outscored depth 80.00 to 60.00 in raw metres.
    Losing a row boundary is a worse error than naming a level "mid".

    This is THE test the whole exclusion rule was carrying: deleting that rule
    without normalising the scores fails this one test and no other in the
    corpus (measured on the pre-AXISCORE tree: 1 failed, 59 passed). After
    normalisation the same rig scores 0.3333 against 0.3333 — an exact tie,
    because both partitions separate perfectly and leave the same 5-of-15
    smallest share — and the documented axis order picks depth. Nothing is
    struck out of contention any more.

    MUTATION: reverse ``AXIS_TIE_BREAK_ORDER`` and this goes RED with
    ``vertical_levels`` and ``buckets=[10, 5]``.
    """
    fixtures = _three_rows_two_trims()
    classification = classify(fixtures)
    selected = classification.selected

    assert selected.kind == "depth_rows"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [5, 5, 5]

    vertical = [c for c in classification.candidates if c.kind == "vertical_levels"]
    assert len(vertical) == 1
    assert [len(bucket) for bucket in vertical[0].fids_by_bucket] == [10, 5]


def test_a_genuine_vertical_rig_still_wins_as_vertical_levels():
    """Non-vacuity guard for the depth-over-vertical policy: >=2 depth buckets
    is the whole condition, and it is load-bearing.

    A rig flat in y answers ``depth_rows`` CONFIDENTLY with a single bucket —
    one row, the true answer to the depth question, but a partition of
    nothing. If the policy keyed on confidence alone it would silence
    ``vertical_levels`` on every tiered rig there is.
    """
    fixtures = _golden_vertical_levels()
    selected = classify(fixtures).selected

    assert selected.kind == "vertical_levels"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [4, 4, 4]

    # exactly the state the condition has to survive: confident, one bucket
    depth = detect_depth_rows(fixtures)
    assert depth.kind == "depth_rows"
    assert depth.low_confidence is False
    assert len(depth.fids_by_bucket) == 1


def test_grid_two_axis_contract_survives_the_vertical_policy():
    """The depth<->lateral contract is decided BEFORE either demotion, so a
    grid stays a grid even when its rows are also at distinct trims — which
    would otherwise be three confident readings competing at once.
    """
    fixtures = tuple(
        _fx(row * 10 + column + 1, x=(column - 4.5) * 1.0, y=row * 3.0, z=row * 3.0)
        for row in range(3)
        for column in range(10)
    )
    selected = classify(fixtures).selected

    assert selected.kind == "grid"
    assert selected.grid_axes is not None
    assert [len(bucket) for bucket in selected.grid_axes["depth"]] == [10, 10, 10]
    assert len(selected.grid_axes["lateral"]) == 10
    # non-vacuity: the z reading really is confident on this rig too
    assert detect_vertical_levels(fixtures).kind == "vertical_levels"


# ---------------------------------------------------------------------------
# SPEC-COPILOT-AXISCORE-001 — axis score comparability
#
# Everything above is green with NO rule striking `vertical_levels` out of
# contention. That is this SPEC's entire claim, and it holds only because the
# scores below are comparable: on the pre-AXISCORE tree, deleting the rule
# alone failed exactly one test in this file (1 failed, 59 passed), and a
# parameter sweep over that one test's rig shape flipped 126 of 252 rigs. One
# golden fixture was standing in for a phenomenon it covered a sliver of.
#
# So these tests bind to the FORMULA, not to a rig. This repository has twice
# shipped a fix pinned to the rig where a defect happened to surface
# (GROUPGEN progress.md:778-779), and the founding misread of this SPEC family
# is still only ONE METRE of radial gap away from a golden fixture that passes:
# `_golden_concentric` is inner r=2.0 and reads `concentric`, while inner
# r=3.0 with the same outer ring read `depth_rows` until this change. Nothing
# in the corpus looked in between.
# ---------------------------------------------------------------------------


#: Boundary gap at which `_partition_score`'s separation term saturates.
#:
#: Derived, never written as a number: it is the point at which the boundary
#: detector itself has already said "this is a boundary", so past it every axis
#: is equally well separated and only partition quality can still discriminate.
#: Retuning either constant moves this bound and these tests with it.
_SATURATION_GAP = SPATIAL_ROW_GAP_RATIO * SPATIAL_ROW_NOISE_SPAN

_AXIS_DETECTORS = (_compute_depth, _compute_lateral, _compute_concentric, _compute_vertical)


def _rig_rows_by_trims(
    rows: int, cols: int, trims: int, ypitch: float, zgap: float
) -> tuple[SpatialFixture, ...]:
    """``_three_rows_two_trims`` generalised over its five degrees of freedom.

    The FRONT rows share the lowest trim, which is golden #17's shape (rows 0
    and 1 at z=5.0, row 2 at z=9.0). When ``trims < rows`` the z reading
    therefore fuses depth rows, which is the error the deleted rule existed to
    prevent; when ``trims == rows`` the two readings agree on the partition and
    only the vocabulary differs.
    """
    fixtures = []
    fid = 1
    for row in range(rows):
        trim = max(0, row - (rows - trims))
        for col in range(cols):
            fixtures.append(_fx(fid, x=col * 2.0 + row * 0.7, y=row * ypitch, z=5.0 + trim * zgap))
            fid += 1
    return tuple(fixtures)


def _rig_flat_lattice(
    cols: int, trims: int, zgap: float, xpit: float
) -> tuple[SpatialFixture, ...]:
    """A lighting bird: no depth at all (y == 0), so `lateral` and `vertical`
    are SYMMETRIC hypotheses about the same fixtures and the corpus pins only
    one of them. The user settled the default here (`plan.md` D1)."""
    fixtures = []
    fid = 1
    for trim in range(trims):
        for col in range(cols):
            fixtures.append(_fx(fid, x=col * xpit, y=0.0, z=5.0 + trim * zgap))
            fid += 1
    return tuple(fixtures)


def _rig_two_rings(
    inner: int, outer: int, r_inner: float, r_outer: float
) -> tuple[SpatialFixture, ...]:
    fixtures = []
    fid = 1
    for count, radius in ((inner, r_inner), (outer, r_outer)):
        for i in range(count):
            angle = 2 * math.pi * i / count
            fixtures.append(_fx(fid, x=radius * math.cos(angle), y=radius * math.sin(angle)))
            fid += 1
    return tuple(fixtures)


#: Sweep A — the shape of golden #17, shaken on all five axes. `ypitch` and
#: `zgap` move INDEPENDENTLY so the physical gap ratio between the two axes
#: runs from 0.05x (ypitch=6, zgap=0.5) to 10x (ypitch=1, zgap=10): the old
#: score was that ratio, so a sweep that moved them together would have missed
#: the defect entirely.
_SWEEP_A_PARAMS = tuple(
    (rows, cols, trims, ypitch, zgap)
    for rows in (2, 3, 4, 5)
    for cols in (3, 5, 8)
    for trims in (2, 3)
    if trims <= rows
    for ypitch in (1.0, 3.0, 6.0)
    for zgap in (0.5, 2.0, 4.0, 10.0)
)

_SWEEP_B_PARAMS = tuple(
    (cols, trims, zgap, xpit)
    for cols in (3, 4, 6, 10)
    for trims in (2, 3, 4)
    for zgap in (0.5, 3.0, 8.0)
    for xpit in (0.5, 2.0)
)

_SWEEP_C_PARAMS = tuple(
    (ni, no, ri, ro)
    for ni in (4, 6, 8)
    for no in (8, 12, 16)
    for ri in (1.0, 2.0, 3.0)
    for ro in (5.0, 7.0, 9.0)
)


def test_the_sweeps_are_run_in_full():
    """The sweeps are ordinary tests with no ``slow`` marker and no
    representative subset, because 405 rigs classify in ~0.03 s and shrinking
    them would re-create the exact trap they defend against (`plan.md` D4).

    This guard exists so that shrinking one is a visible edit rather than a
    quiet one.
    """
    assert len(_SWEEP_A_PARAMS) == 252
    assert len(_SWEEP_B_PARAMS) == 72
    assert len(_SWEEP_C_PARAMS) == 81


# --------------------------------------------------------------------------
# The formula itself
# --------------------------------------------------------------------------


def test_the_separation_term_saturates_at_the_detectors_own_threshold():
    """Why saturation exists, stated as a number.

    Below the bound a bigger physical gap still buys a bigger score, which is
    what made 4 m of trim beat 3 m of depth. At and above it every axis is
    equally separated and only partition quality can discriminate — and that
    term is a ratio of COUNTS, so it carries no units at all.

    The bound is not a new constant: it is where the boundary detector already
    decided a gap was a boundary.

    MUTATION: drop the ``min(..., 1.0)`` and the last two assertions go RED,
    because a 100x gap would then score 100x.
    """
    sizes = [5, 5]
    under = _partition_score(
        min_boundary_gap=_SATURATION_GAP / 2, within_bucket_span=0.0, bucket_sizes=sizes
    )
    at_bound = _partition_score(
        min_boundary_gap=_SATURATION_GAP, within_bucket_span=0.0, bucket_sizes=sizes
    )
    far_over = _partition_score(
        min_boundary_gap=_SATURATION_GAP * 100, within_bucket_span=0.0, bucket_sizes=sizes
    )

    assert under < at_bound, "below the bound, separation still discriminates"
    assert at_bound == 0.5, "at the bound the score is pure partition quality"
    assert far_over == at_bound, "100x the gap buys nothing past the bound"


def test_partition_quality_separates_two_equally_well_separated_readings():
    """The term the old score had no equivalent for.

    Same separation on both sides, so the only difference is HOW the rig was
    cut: nine buckets of two against two buckets of nine. The old formula
    could not tell them apart at all — it never looked at bucket sizes — which
    is how reading 18 fixtures as nine rings of two came to outscore reading
    them as the left/right split they are.

    MUTATION: drop the ``min(bucket_sizes) / count`` factor and both
    assertions go RED (the two scores become identical at 1.0).
    """
    fold = _partition_score(min_boundary_gap=1.0, within_bucket_span=0.0, bucket_sizes=[2] * 9)
    split = _partition_score(min_boundary_gap=1.0, within_bucket_span=0.0, bucket_sizes=[9, 9])

    assert split > fold
    assert (fold, split) == (2 / 18, 9 / 18)


def test_an_axis_that_partitions_nothing_scores_zero_however_clean_its_gaps():
    """One bucket is not a partition. Without this the "gap" of a rig with no
    boundary would be scored as though it were a structure."""
    assert _partition_score(min_boundary_gap=99.0, within_bucket_span=0.0, bucket_sizes=[30]) == 0.0
    assert _partition_score(min_boundary_gap=99.0, within_bucket_span=0.0, bucket_sizes=[]) == 0.0


# --------------------------------------------------------------------------
# AC-AXISCORE-003/004 — one order statistic, one interval
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rig",
    [
        _golden_bar(),
        _golden_grid(),
        _golden_concentric(),
        _golden_lateral_split(),
        _golden_vertical_levels(),
        _golden_irregular(),
        _golden_all_origin(),
        _golden_bilateral(),
        _flat_row(_MIRRORED_LEFT_RIGHT),
        _electrics_three_bars(),
        _three_rows_two_trims(),
        _rig_two_rings(6, 12, 3.0, 5.0),
    ],
    ids=[
        "bar",
        "grid",
        "concentric",
        "lateral",
        "vertical",
        "irregular",
        "all_origin",
        "bilateral",
        "mirror_flat",
        "electrics",
        "rows_by_trims",
        "narrow_rings",
    ],
)
def test_every_detector_scores_inside_one_closed_interval(rig):
    """Scores are only comparable if they share a scale, and "shares a scale"
    has to be checkable. ``_compute_bilateral`` is in this list deliberately:
    it used to return ``float(len(pairs))``, which is 15.0 on the 30-fixture
    grid — a raw count sitting in a field called ``score`` next to values that
    were ratios.

    MUTATION: restore ``float(len(pairs))`` and the grid and mirror rigs go
    RED.
    """
    for detector in (*_AXIS_DETECTORS, _compute_bilateral):
        _, score = detector(rig)
        assert math.isfinite(score)
        assert 0.0 <= score <= 1.0, f"{detector.__name__} returned {score}"


@pytest.mark.parametrize(
    "inner,outer,r_inner,r_outer",
    [(6, 12, 2.0, 5.0), (6, 12, 3.0, 5.0), (6, 8, 3.0, 5.0)],
)
def test_depth_is_graded_on_its_weakest_boundary_like_every_other_axis(
    inner, outer, r_inner, r_outer
):
    """``_compute_depth`` used ``analysis.gaps.max_gap`` — the BEST gap in the
    whole y sequence, not even restricted to gaps that became boundaries —
    while `_axis_buckets` used the WEAKEST boundary gap. Depth was graded on
    its best and its rivals on their worst.

    On a ring rig that asymmetry is enormous, because the y projection of a
    circle has one wide gap in the middle and hairline gaps at the poles:
    ``6@r=3.0 + 12@r=5.0`` measures max_gap 2.500 where its weakest boundary
    is 0.098, a factor of 25.

    MUTATION: restore the ``max_gap`` numerator and this goes RED.
    """
    fixtures = _rig_two_rings(inner, outer, r_inner, r_outer)
    analysis = analyze_spatial_rows(fixtures)
    assert not analysis.low_confidence and analysis.gaps is not None

    extents = [
        (min(f.y for f in row.fixtures), max(f.y for f in row.fixtures)) for row in analysis.rows
    ]
    sizes = [len(row.fids) for row in analysis.rows]
    weakest = min(extents[i + 1][0] - extents[i][1] for i in range(len(extents) - 1))
    spread = max(hi - lo for lo, hi in extents)

    # non-vacuity: the two order statistics really do disagree on this rig
    assert analysis.gaps.max_gap > weakest

    on_weakest = _partition_score(
        min_boundary_gap=weakest, within_bucket_span=spread, bucket_sizes=sizes
    )
    on_best = _partition_score(
        min_boundary_gap=analysis.gaps.max_gap, within_bucket_span=spread, bucket_sizes=sizes
    )
    assert _compute_depth(fixtures)[1] == on_weakest
    assert on_weakest <= on_best


# --------------------------------------------------------------------------
# AC-AXISCORE-005/006 — partition quality, and the founding misread
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "r_inner,r_outer", [(2.0, 5.0), (3.0, 5.0), (1.0, 5.0), (2.0, 7.0), (3.0, 9.0)]
)
def test_a_rings_real_split_outscores_the_y_projection_artefact(r_inner, r_outer):
    """The founding misread, scored rather than argued.

    A two-ring rig's y projection produces real gaps — nine of them for an
    18-fixture rig — so the row detector answers confidently with buckets like
    ``[1,2,2,2,4,2,2,2,1]``. Two readings, both confident; the question is
    which explains more of the rig. Shaving singletons off the poles of a
    circle explains almost nothing, and the ``[6,12]`` radius split explains
    all of it.

    The radii are swept so the inequality cannot rest on one radial gap: the
    corpus' own fixture is (2.0, 5.0) and the rig that was misread is
    (3.0, 5.0), which differ by ONE METRE.

    MUTATION: drop the partition-quality factor and this goes RED.
    """
    fixtures = _rig_two_rings(6, 12, r_inner, r_outer)
    depth_score = _compute_depth(fixtures)[1]
    concentric_score = _compute_concentric(fixtures)[1]

    # non-vacuity: the artefact reading is confident, not disqualified
    assert detect_depth_rows(fixtures).kind == "depth_rows"
    assert len(detect_depth_rows(fixtures).fids_by_bucket) > 2
    assert concentric_score > depth_score


@pytest.mark.parametrize(
    "inner,outer,r_inner,r_outer",
    [(6, 8, 3.0, 5.0), (6, 12, 3.0, 5.0)],
)
def test_two_ring_rigs_with_a_narrow_radial_gap_are_concentric(inner, outer, r_inner, r_outer):
    """AC-AXISCORE-006 — a latent defect this SPEC delivers a fix for, not a
    side effect it tolerates (user decision, `plan.md` D2).

    These two rigs read ``depth_rows`` with buckets ``[1,2,2,4,2,2,1]`` and
    ``[1,2,2,2,4,2,2,2,1]`` before this change: the founding misread of this
    SPEC family, alive OUTSIDE the golden corpus. They sit one metre of radial
    gap from ``_golden_concentric`` (inner r=2.0), which passes — the corpus
    never looked in between.

    ``low_confidence`` was explicitly considered and rejected as the answer
    (D2), so it is asserted against here.
    """
    fixtures = _rig_two_rings(inner, outer, r_inner, r_outer)
    selected = classify(fixtures).selected

    assert selected.kind == "concentric"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [inner, outer]
    assert selected.low_confidence is False


def test_the_flat_mirror_folds_27x_score_advantage_is_gone():
    """The same defect seen from the other side.

    On the M6 rig the WRONG reading (nine rings of two, a fold of ``|x|``)
    scored 20.00 against the right one's 0.75 — 27x — because only gap sizes
    were compared and the fold's gaps were tidier. Both readings are now on
    one scale and the gap is 1.18x.

    The fold still edges ahead on the number, which is exactly why the mirror
    artefact demotion has to stay: normalisation narrows this, it does not
    close it, and pretending otherwise would delete a rule that is still
    load-bearing.

    MUTATION: drop the partition-quality factor and the ratio returns to 5.3x.
    """
    fixtures = _flat_row(_MIRRORED_LEFT_RIGHT)
    fold = _compute_concentric(fixtures)[1]
    real = _compute_lateral(fixtures)[1]

    assert fold > real, "non-vacuity: the demotion, not the score, is what saves this rig"
    assert fold / real < 1.5, f"fold {fold} vs real split {real}"
    assert classify(fixtures).selected.kind == "lateral_split"


# --------------------------------------------------------------------------
# AC-AXISCORE-001/008 — the deleted rule, and what replaced it
# --------------------------------------------------------------------------


def test_a_better_vertical_reading_beats_a_partitioning_depth():
    """The rule is gone and this is the test that keeps it gone.

    Two depth rows of 2 and 8 — a lopsided cut — crossed with two trims of 5
    and 5, which is the balanced one. Both readings separate perfectly, so the
    only discriminator is which partition explains more of the rig, and z wins
    it 0.5 to 0.2.

    The deleted rule struck ``vertical_levels`` out of contention whenever
    ``depth_rows`` had >=2 buckets, with no reference to either score. It would
    hand this rig to ``depth_rows`` [2, 8].

    MUTATION: re-add the exclusion rule in any form and this goes RED. That is
    what makes the deletion durable rather than merely done.
    """
    fixtures = tuple(
        _fx(fid, x=fid * 1.0, y=0.0 if fid <= 2 else 5.0, z=1.0 if fid in (1, 3, 4, 5, 6) else 9.0)
        for fid in range(1, 11)
    )
    depth = detect_depth_rows(fixtures)
    vertical = detect_vertical_levels(fixtures)

    # the struck-out rule's precondition holds: depth is confident and splits
    assert depth.kind == "depth_rows"
    assert [len(b) for b in depth.fids_by_bucket] == [2, 8]
    # and the reading it would have struck out is the better one
    assert [len(b) for b in vertical.fids_by_bucket] == [5, 5]
    assert _compute_vertical(fixtures)[1] > _compute_depth(fixtures)[1]

    assert classify(fixtures).selected.kind == "vertical_levels"


@pytest.mark.parametrize(
    "builder,expected",
    [(_three_rows_two_trims, [5, 5, 5]), (_electrics_three_bars, [5, 5, 5])],
    ids=["rows_by_trims", "electrics"],
)
def test_the_axis_order_fires_only_on_an_exact_tie(builder, expected):
    """The tie has to be asserted BEFORE the winner, or this test would be
    confirming an accidental inequality and calling it a documented order.

    Both rigs partition perfectly on both axes and leave the same smallest
    share, so the two scores are equal by construction rather than by luck.

    MUTATION: reverse ``AXIS_TIE_BREAK_ORDER`` and both go RED.
    """
    fixtures = builder()
    assert _compute_depth(fixtures)[1] == _compute_vertical(fixtures)[1]

    selected = classify(fixtures).selected
    assert selected.kind == "depth_rows"
    assert [len(b) for b in selected.fids_by_bucket] == expected


def test_the_axis_order_never_overrides_a_higher_score():
    """The difference between a tie-break and the exclusion rule it replaced.

    ``AXIS_TIE_BREAK_ORDER`` ranks ``lateral_split`` above ``vertical_levels``.
    On this rig ``vertical`` scores strictly higher and must win anyway — if
    the order could override a score it would be the old rule pointed the
    other way, and this fixture is in the corpus precisely to catch that.
    """
    fixtures = _golden_vertical_levels()
    lateral_score = _compute_lateral(fixtures)[1]
    vertical_score = _compute_vertical(fixtures)[1]

    assert AXIS_TIE_BREAK_ORDER.index("lateral_split") < AXIS_TIE_BREAK_ORDER.index(
        "vertical_levels"
    )
    assert vertical_score > lateral_score
    assert classify(fixtures).selected.kind == "vertical_levels"


def test_bilateral_is_normalised_onto_the_shared_scale_and_still_never_wins():
    """D-Q10 survives the rescale, and is now under more pressure than before.

    On the M6 mirror rig every fixture is paired, so ``bilateral`` scores 1.0 —
    the maximum the interval allows, higher than every axis on the rig. If it
    were in contention it would win outright. It is reported in full and left
    out of ``scored``, because ``naming.py`` has no vocabulary for symmetry and
    a win here would hand the operator zero groups.

    MUTATION: add ``(bilateral, bilateral_score)`` to ``contenders`` and this
    goes RED.
    """
    fixtures = _flat_row(_MIRRORED_LEFT_RIGHT)
    classification = classify(fixtures)
    bilateral_score = _compute_bilateral(fixtures)[1]

    assert bilateral_score == 1.0
    assert bilateral_score > max(detector(fixtures)[1] for detector in _AXIS_DETECTORS)
    assert classification.selected.kind == "lateral_split"

    reported = [c for c in classification.candidates if c.kind == "bilateral_pairs"]
    assert len(reported) == 1 and reported[0].low_confidence is False


# --------------------------------------------------------------------------
# AC-AXISCORE-007 — the sweeps, run in full
# --------------------------------------------------------------------------


@pytest.mark.parametrize("rows,cols,trims,ypitch,zgap", _SWEEP_A_PARAMS)
def test_sweep_a_a_trim_reading_never_fuses_depth_rows(rows, cols, trims, ypitch, zgap):
    """252 rigs, the exclusion rule deleted, and not one of them lets the z
    reading merge two depth rows into a group.

    The golden fixture this generalises covered 1 of the 126 rigs that flip
    when the rule is deleted without normalising — 0.8% of the phenomenon.
    ``ypitch`` and ``zgap`` are swept INDEPENDENTLY because the old score WAS
    their ratio; sweeping them together would reproduce the blind spot.
    """
    fixtures = _rig_rows_by_trims(rows, cols, trims, ypitch, zgap)
    selected = classify(fixtures).selected

    assert selected.kind == "depth_rows"
    assert len(selected.fids_by_bucket) == rows

    # non-vacuity: the z reading is a confident competitor on every one of
    # these rigs, and when trims < rows it really does fuse rows together.
    vertical = detect_vertical_levels(fixtures)
    assert vertical.kind == "vertical_levels"
    assert len(vertical.fids_by_bucket) == trims

    # determinism: input order is not part of the answer
    assert classify(tuple(reversed(fixtures))).selected.kind == "depth_rows"


@pytest.mark.parametrize("cols,trims", [(c, t) for c in (3, 4, 6, 10) for t in (2, 3, 4)])
def test_sweep_b_a_flat_lattices_verdict_ignores_how_big_the_gaps_are(cols, trims):
    """The unit error, refuted directly.

    Same lattice, four combinations of column pitch and trim spacing spanning
    16x. Under the old score the verdict tracked whichever physical gap was
    larger, so the same rig answered differently at different scales. The
    answer is now a property of the lattice.
    """
    verdicts = {
        (zgap, xpit): classify(_rig_flat_lattice(cols, trims, zgap, xpit)).selected.kind
        for zgap in (0.5, 3.0, 8.0)
        for xpit in (0.5, 2.0)
    }
    assert len(set(verdicts.values())) == 1, verdicts


@pytest.mark.parametrize("cols,trims,zgap,xpit", _SWEEP_B_PARAMS)
def test_sweep_b_lateral_is_a_tie_break_default_not_a_preference(cols, trims, zgap, xpit):
    """The user's "flat lattice reads left/right" decision (`plan.md` D1),
    implemented as it was decided.

    A flat lattice makes ``lateral`` and ``vertical`` symmetric hypotheses, and
    the corpus pins only one of the 72 rigs. The default therefore had to be
    settled by a person — and it lands as a TIE-BREAK, never as a thumb on the
    scale. Implemented as an unconditional preference it would turn
    ``_golden_vertical_levels`` red and rebuild the exclusion rule pointing the
    other way, which REQ-AXISCORE-008 forbids.
    """
    fixtures = _rig_flat_lattice(cols, trims, zgap, xpit)
    lateral_score = _compute_lateral(fixtures)[1]
    vertical_score = _compute_vertical(fixtures)[1]
    selected = classify(fixtures).selected.kind

    if vertical_score > lateral_score:
        assert selected == "vertical_levels", "a higher score is never overridden"
    else:
        assert selected == "lateral_split"

    assert classify(tuple(reversed(fixtures))).selected.kind == selected


def test_sweep_b_exercises_both_the_tie_and_the_score_branch():
    """Non-vacuity for the test above: neither branch is dead.

    Measured on this tree — 12 exact ties (all won by ``lateral``), 6 rigs
    where ``lateral`` wins on score, 54 where ``vertical`` does. Zero rigs
    where the tie-break overrode a higher score, which is the evidence that
    D1 was implemented as decided.
    """
    ties = strictly_lateral = strictly_vertical = 0
    for cols, trims, zgap, xpit in _SWEEP_B_PARAMS:
        fixtures = _rig_flat_lattice(cols, trims, zgap, xpit)
        lateral_score = _compute_lateral(fixtures)[1]
        vertical_score = _compute_vertical(fixtures)[1]
        if lateral_score == vertical_score:
            ties += 1
        elif lateral_score > vertical_score:
            strictly_lateral += 1
        else:
            strictly_vertical += 1

    assert (ties, strictly_lateral, strictly_vertical) == (12, 6, 54)


@pytest.mark.parametrize("ni,no,ri,ro", _SWEEP_C_PARAMS)
def test_sweep_c_a_two_ring_rig_is_never_read_as_depth_rows(ni, no, ri, ro):
    """81 rigs across ring counts and both radii. Two of them read
    ``depth_rows`` before this change; the rest passed for reasons that had
    nothing to do with being right — the radial gap happened to be wide.
    """
    fixtures = _rig_two_rings(ni, no, ri, ro)
    selected = classify(fixtures).selected

    assert selected.kind in {"concentric", "grid"}
    if selected.kind == "concentric":
        assert [len(b) for b in selected.fids_by_bucket] == [ni, no]
    assert classify(tuple(reversed(fixtures))).selected.kind == selected.kind


# --------------------------------------------------------------------------
# AC-AXISCORE-002 — scale invariance, and the exact bound on it
# --------------------------------------------------------------------------


def _all_sweep_rigs():
    for params in _SWEEP_A_PARAMS:
        yield f"A{params}", _rig_rows_by_trims(*params)
    for params in _SWEEP_B_PARAMS:
        yield f"B{params}", _rig_flat_lattice(*params)
    for ni, no, ri, ro in _SWEEP_C_PARAMS:
        yield f"C{(ni, no, ri, ro)}", _rig_two_rings(ni, no, ri, ro)


def _scaled(fixtures, axis, factor):
    return tuple(
        _fx(
            f.fid,
            f.x * (factor if axis in ("x", "all") else 1.0),
            f.y * (factor if axis in ("y", "all") else 1.0),
            f.z * (factor if axis in ("z", "all") else 1.0),
        )
        for f in fixtures
    )


def _dimensionless_profile(fixtures):
    """``(bucket shapes, every partitioned axis is saturated)``.

    Saturation is read off the PUBLIC score: when the separation term is
    1.0 the score is exactly ``min(bucket)/n``, a ratio of counts with no
    length in it. Below that the score still carries metres, because a rig
    whose buckets have zero internal spread offers no second length on that
    axis to divide by — the denominator falls back to ``rows.py``'s absolute
    floor, which is a physical constant that SPEC deliberately owns.
    """
    n = len(fixtures)
    shapes = []
    saturated = True
    for detector in _AXIS_DETECTORS:
        result, score = detector(fixtures)
        sizes = tuple(len(bucket) for bucket in result.fids_by_bucket)
        shapes.append(sizes)
        if result.kind is not None and not result.low_confidence and len(sizes) >= 2:
            saturated = saturated and score == min(sizes) / n
    return tuple(shapes), saturated


@pytest.mark.parametrize("factor", [0.1, 0.5, 2.0, 10.0, 100.0])
def test_scaling_an_axis_cannot_change_a_verdict_the_score_no_longer_measures(factor):
    """Scale invariance, stated with the bound it actually has.

    The old score was ``20 x metres-on-this-axis``, so shrinking one axis'
    coordinates changed the verdict on a rig inside the golden corpus
    (``_golden_vertical_levels`` with z x0.1 answered ``lateral_split``).

    The guarantee here is CONDITIONAL and the condition is asserted, not
    assumed. Once every partitioned axis is saturated the score is a ratio of
    counts and nothing about it can move under scaling. Below saturation it is
    still metres-proportional and the verdict CAN move — 165 of these
    combinations do, all of them outside the regime. That is not a defect in
    the formula: with zero within-bucket spread there is no second length on
    the axis to form a ratio from, and inventing a reference length is exactly
    what REQ-AXISCORE-008 forbids. In practice the bound is
    ``SPATIAL_ROW_GAP_RATIO * SPATIAL_ROW_NOISE_SPAN`` of separation, far below
    any real rig's row spacing.

    Cases where the scaling re-cut the PARTITION are excluded separately and
    counted: below the absolute floor a rig becomes a different rig, which is
    a question about ``rows.py``'s threshold rather than about invariance.
    """
    exercised = repartitioned = unsaturated = 0
    changed = []
    for label, fixtures in _all_sweep_rigs():
        base_shapes, base_saturated = _dimensionless_profile(fixtures)
        base_kind = classify(fixtures).selected.kind
        for axis in ("x", "y", "z", "all"):
            scaled = _scaled(fixtures, axis, factor)
            shapes, saturated = _dimensionless_profile(scaled)
            if shapes != base_shapes:
                repartitioned += 1
                continue
            if not (base_saturated and saturated):
                unsaturated += 1
                continue
            exercised += 1
            kind = classify(scaled).selected.kind
            if kind != base_kind:
                changed.append((label, axis, base_kind, kind))

    assert changed == []
    assert exercised > 400, (
        f"the regime must not be empty, or this test proves nothing "
        f"(exercised={exercised} repartitioned={repartitioned} unsaturated={unsaturated})"
    )


@pytest.mark.parametrize("factor", [0.1, 0.5, 2.0, 10.0, 100.0])
@pytest.mark.parametrize("axis", ["x", "y", "z", "all"])
def test_the_golden_vertical_rig_survives_the_scaling_that_used_to_flip_it(axis, factor):
    """AC-AXISCORE-002's named case. ``z x0.1`` answered ``lateral_split`` on
    the pre-AXISCORE tree — a rig in the golden corpus, structurally
    unchanged, reclassified because one axis was measured in different units.
    """
    fixtures = _golden_vertical_levels()
    scaled = _scaled(fixtures, axis, factor)
    selected = classify(scaled).selected

    assert selected.kind == "vertical_levels"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [4, 4, 4]


@pytest.mark.parametrize("factor", [0.5, 2.0, 10.0])
def test_scaling_a_ring_rig_uniformly_leaves_it_concentric(factor):
    """The weaker uniform case, kept because it is the one a reader assumes.

    Uniform scaling cancels even under the OLD score — every competing axis
    derives from the same coordinates, so the ratio between them is preserved
    and the metres divide out. It is therefore not evidence that the score is
    dimensionless, and it must not be mistaken for the per-axis test above.
    It still pins a property worth keeping.
    """
    fixtures = _rig_two_rings(6, 12, 3.0, 5.0)
    scaled = _scaled(fixtures, "all", factor)
    selected = classify(scaled).selected

    assert selected.kind == "concentric"
    assert [len(bucket) for bucket in selected.fids_by_bucket] == [6, 12]


def test_the_normalisation_left_the_two_pinned_constants_alone():
    """``rows.py`` owns both, and this SPEC reuses them rather than inventing
    a scale of its own (REQ-AXISCORE-011). The saturation bound is derived
    from them, so if either moves the bound moves with it."""
    assert SPATIAL_ROW_NOISE_SPAN == 0.05
    assert SPATIAL_ROW_GAP_RATIO == 4.0
    assert _SATURATION_GAP == 0.2
