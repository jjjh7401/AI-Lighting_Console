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
    _compute_depth,
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

    MUTATION: this rig is covered TWICE over, and the measured discrimination
    says so — it goes RED only when BOTH the ``median_gap > 0`` guard is
    restored in ``_compute_depth`` AND ``vertical`` goes back into ``scored``
    unconditionally. Restoring either one alone leaves it GREEN, because
    un-zeroing the depth score also happens to put depth ahead here (60.00 to
    z's 30.00). That is a fact about this rig, not a redundancy in the policy:
    ``test_depth_rows_beats_a_vertical_reading_that_merges_two_rows`` is the
    rig where the score genuinely favours z, and it isolates the policy alone.
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
    """The same policy where the two readings DISAGREE about the partition.

    Three rows across two trims: the z reading answers [10,5] — two depth rows
    fused into one group — and it outscored depth 80.00 to 0.00 before the fix.
    Losing a row boundary is a worse error than naming a level "mid".

    MUTATION: put ``vertical`` back into ``scored`` unconditionally and this
    goes RED with ``vertical_levels`` and ``buckets=[10, 5]``.
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
