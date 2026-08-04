"""Topology classification — pure, structural detection over fixture positions
(SPEC-COPILOT-GROUPGEN-001, REQ-GROUPGEN-001/002/003/004/005/006/007).

Six independent hypotheses run over the same fixture set, and a contention
rule picks a single winner (or ``None`` when nothing is structurally clear).
No console handle, no port, no transport reference anywhere in this module
(REQ-GROUPGEN-006) — the input is already-read fixture coordinates
(:class:`server.spatial.schema.SpatialFixture`), and nothing here writes
anything back.

**Why one hypothesis is not enough** (design.md §3, research.md §3):
``server/spatial/rows.py`` runs y-axis gap clustering alone, and a two-ring
concentric rig (inner 6 @ r=2.0, outer 12 @ r=5.0) happens to produce nine
real y-axis gaps — the row detector answers ``rows=9, low_confidence=False``
with full confidence, because nothing in that single-axis view can see the
radius split that actually explains the rig. This module never replaces
``rows.py`` (REQ-GROUPGEN-005: depth-row detection is *incorporated* as one
candidate among six, not superseded) — it adds five more hypotheses that run
in parallel, so a rig whose real structure lives on another axis has a
detector that can see it.

Determinism (REQ-GROUPGEN-002): every detector sorts on a total key
(axis value, then ``fid``) before measuring anything, so ties never resolve
by insertion order. Standard ``math`` only — no clustering library, no new
runtime dependency (REQ-GROUPGEN-007).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import median
from typing import Literal

from server.spatial.rows import (
    SPATIAL_ROW_GAP_RATIO,
    SPATIAL_ROW_NOISE_SPAN,
    analyze_spatial_rows,
)
from server.spatial.schema import SpatialFixture

TopologyKind = Literal[
    "depth_rows",
    "lateral_split",
    "concentric",
    "vertical_levels",
    "grid",
    "bilateral_pairs",
    None,
]

GridAxis = Literal["depth", "lateral"]


@dataclass(frozen=True)
class TopologyResult:
    """One topology candidate's verdict — one per detector; the contention
    rule (:func:`classify`) picks a single winner from the set.

    ``fids_by_bucket`` order is the naming order that ``naming.py`` consumes
    (design.md §2.2): ascending on the axis the detector measured. When
    ``kind == "grid"`` this field is REQUIRED to be empty — the per-axis
    buckets live in ``grid_axes`` instead, because a single field cannot hold
    two shapes (one flat tuple of buckets vs. two axes of buckets) without
    the downstream reader having to guess which shape it received.
    """

    kind: TopologyKind
    fids_by_bucket: tuple[tuple[int, ...], ...]
    low_confidence: bool
    reason: str | None = None
    grid_axes: Mapping[GridAxis, tuple[tuple[int, ...], ...]] | None = None

    def __post_init__(self) -> None:
        # [HARD] type invariant (design.md §2.2) — the M1/M2 cross-contract:
        #   kind == "grid"  <=>  fids_by_bucket == () and grid_axes is not None
        #   kind != "grid"  <=>  grid_axes is None
        if self.kind == "grid":
            if self.fids_by_bucket != ():
                raise ValueError(
                    "grid TopologyResult must carry fids_by_bucket == () "
                    "-- per-axis buckets belong in grid_axes"
                )
            if self.grid_axes is None:
                raise ValueError("grid TopologyResult must carry grid_axes")
        elif self.grid_axes is not None:
            raise ValueError(
                f"non-grid TopologyResult (kind={self.kind!r}) must not carry grid_axes"
            )


@dataclass(frozen=True)
class TopologyClassification:
    """``classify()``'s final answer: one selected topology (or ``None``),
    plus every candidate the contention rule weighed (audit + golden
    comparison — design.md §2.2)."""

    selected: TopologyResult
    candidates: tuple[TopologyResult, ...]


def _axis_buckets(
    fixtures: Sequence[SpatialFixture], value_fn
) -> tuple[tuple[tuple[int, ...], ...], bool, str | None, float]:
    """Gap-cluster fixtures on one scalar axis (design.md §2.3 — the same
    "sort, look at neighbour gaps, cut where one stands out" method
    ``rows.py`` uses for y, generalised to any axis via ``value_fn``).

    Returns ``(buckets, low_confidence, reason, score)``. ``buckets`` is
    ascending on the axis value. ``score`` ranks competing confident
    detectors against each other (higher = cleaner separation) and is
    otherwise meaningless — it is the weakest surviving boundary gap over the
    widest within-bucket spread, i.e. "how many noise-spans of daylight
    separates the closest two buckets, relative to how much a bucket
    internally sprawls on this axis". A perfect ring (zero within-bucket
    radius spread) scores far higher than a same-shaped-but-noisy row band,
    which is exactly the asymmetry §3's non-vacuousness argument needs.
    """
    if not fixtures:
        return (), True, "no_fixtures", 0.0

    ordered = sorted(fixtures, key=lambda fixture: (value_fn(fixture), fixture.fid))
    values = [value_fn(fixture) for fixture in ordered]
    count = len(ordered)
    span = values[-1] - values[0]

    if count == 1 or span <= SPATIAL_ROW_NOISE_SPAN:
        return (
            (tuple(fixture.fid for fixture in ordered),),
            True,
            "no_spatial_spread",
            0.0,
        )

    gaps = [values[i + 1] - values[i] for i in range(count - 1)]
    median_gap = median(gaps)
    threshold = max(SPATIAL_ROW_GAP_RATIO * median_gap, SPATIAL_ROW_NOISE_SPAN)
    boundaries = [i for i, gap in enumerate(gaps) if gap > threshold]

    if not boundaries:
        return (
            (tuple(fixture.fid for fixture in ordered),),
            True,
            "weak_gap_separation",
            0.0,
        )

    buckets: list[tuple[int, ...]] = []
    bucket_spans: list[float] = []
    start = 0
    for boundary in [*boundaries, count - 1]:
        chunk = ordered[start : boundary + 1]
        chunk_values = [value_fn(fixture) for fixture in chunk]
        buckets.append(tuple(sorted(fixture.fid for fixture in chunk)))
        bucket_spans.append(max(chunk_values) - min(chunk_values))
        start = boundary + 1

    within_spread = max(bucket_spans)
    min_boundary_gap = min(gaps[i] for i in boundaries)
    score = min_boundary_gap / max(within_spread, SPATIAL_ROW_NOISE_SPAN)

    return tuple(buckets), False, None, score


def _compute_depth(fixtures: tuple[SpatialFixture, ...]) -> tuple[TopologyResult, float]:
    """``depth_rows`` — the y-axis candidate, incorporated (not
    reimplemented) from ``rows.py`` (REQ-GROUPGEN-005)."""
    analysis = analyze_spatial_rows(fixtures)
    buckets = tuple(row.fids for row in analysis.rows)
    if analysis.low_confidence:
        return (
            TopologyResult(
                kind=None,
                fids_by_bucket=buckets,
                low_confidence=True,
                reason=analysis.confidence_reason,
            ),
            0.0,
        )
    score = 0.0
    if analysis.gaps is not None and analysis.gaps.median_gap > 0:
        within_spread = max((row.fixtures[-1].y if row.fixtures else 0.0) for row in analysis.rows)
        # Match _axis_buckets' scoring shape: weakest boundary gap over the
        # widest within-row spread, using the gap profile rows.py already
        # measured rather than re-deriving one.
        row_spans = [
            max((f.y for f in row.fixtures), default=0.0)
            - min((f.y for f in row.fixtures), default=0.0)
            for row in analysis.rows
        ]
        within_spread = max(row_spans) if row_spans else 0.0
        score = analysis.gaps.max_gap / max(within_spread, SPATIAL_ROW_NOISE_SPAN)
    return (
        TopologyResult(kind="depth_rows", fids_by_bucket=buckets, low_confidence=False),
        score,
    )


def _compute_lateral(fixtures: tuple[SpatialFixture, ...]) -> tuple[TopologyResult, float]:
    """``lateral_split`` — x-axis gap clustering."""
    buckets, low_confidence, reason, score = _axis_buckets(fixtures, lambda f: f.x)
    kind: TopologyKind = "lateral_split" if not low_confidence else None
    return (
        TopologyResult(
            kind=kind,
            fids_by_bucket=buckets,
            low_confidence=low_confidence,
            reason=reason,
        ),
        score,
    )


def _compute_vertical(fixtures: tuple[SpatialFixture, ...]) -> tuple[TopologyResult, float]:
    """``vertical_levels`` — z-axis gap clustering. ``vertical_span`` is
    "measured but never used" in ``rows.py``; here it is promoted to an
    actual classification input (research.md §3.1)."""
    buckets, low_confidence, reason, score = _axis_buckets(fixtures, lambda f: f.z)
    kind: TopologyKind = "vertical_levels" if not low_confidence else None
    return (
        TopologyResult(
            kind=kind,
            fids_by_bucket=buckets,
            low_confidence=low_confidence,
            reason=reason,
        ),
        score,
    )


def _compute_concentric(fixtures: tuple[SpatialFixture, ...]) -> tuple[TopologyResult, float]:
    """``concentric`` — radius-from-origin gap clustering
    (``math.hypot(x, y)``, design.md §2.3)."""
    buckets, low_confidence, reason, score = _axis_buckets(fixtures, lambda f: math.hypot(f.x, f.y))
    kind: TopologyKind = "concentric" if not low_confidence else None
    return (
        TopologyResult(
            kind=kind,
            fids_by_bucket=buckets,
            low_confidence=low_confidence,
            reason=reason,
        ),
        score,
    )


def _compute_bilateral(fixtures: tuple[SpatialFixture, ...]) -> tuple[TopologyResult, float]:
    """``bilateral_pairs`` — x=0 mirror-symmetric pairs. Detected and
    returned only: the group-write path never consumes this candidate
    (design.md §5.3, contract D-Q10)."""
    if not fixtures:
        return (
            TopologyResult(kind=None, fids_by_bucket=(), low_confidence=True, reason="no_fixtures"),
            0.0,
        )

    tol = SPATIAL_ROW_NOISE_SPAN
    remaining: dict[int, SpatialFixture] = {f.fid: f for f in fixtures}
    pairs: list[tuple[int, int]] = []
    on_axis = 0

    # Deterministic scan order: ascending |x|, then y, then fid — so the
    # first candidate a mirror match is sought for is always the same one.
    scan_order = sorted(remaining, key=lambda fid: (abs(remaining[fid].x), remaining[fid].y, fid))
    for fid in scan_order:
        fixture = remaining.get(fid)
        if fixture is None:
            continue
        del remaining[fid]
        if abs(fixture.x) <= tol:
            on_axis += 1
            continue
        partner_fid = None
        for other_fid in sorted(remaining):
            other = remaining[other_fid]
            if abs(other.x + fixture.x) <= tol and abs(other.y - fixture.y) <= tol:
                partner_fid = other_fid
                break
        if partner_fid is not None:
            del remaining[partner_fid]
            pairs.append(tuple(sorted((fid, partner_fid))))  # type: ignore[arg-type]

    if not pairs:
        return (
            TopologyResult(
                kind=None, fids_by_bucket=(), low_confidence=True, reason="no_bilateral_symmetry"
            ),
            0.0,
        )

    paired_count = 2 * len(pairs) + on_axis
    low_confidence = paired_count < len(fixtures)
    buckets = tuple(sorted(pairs))
    score = float(len(pairs)) if not low_confidence else 0.0
    return (
        TopologyResult(
            kind="bilateral_pairs" if not low_confidence else None,
            fids_by_bucket=buckets,
            low_confidence=low_confidence,
            reason=None if not low_confidence else "partial_bilateral_symmetry",
        ),
        score,
    )


def _compute_grid(depth: TopologyResult, lateral: TopologyResult) -> TopologyResult:
    """``grid`` — the contention outcome when BOTH depth and lateral are
    confident with >=2 buckets each (design.md §2.4, contract D-Q2). Output
    stays split per axis; no 9-cell cross product is ever built."""
    if (
        not depth.low_confidence
        and not lateral.low_confidence
        and len(depth.fids_by_bucket) >= 2
        and len(lateral.fids_by_bucket) >= 2
    ):
        return TopologyResult(
            kind="grid",
            fids_by_bucket=(),
            low_confidence=False,
            grid_axes={"depth": depth.fids_by_bucket, "lateral": lateral.fids_by_bucket},
        )
    return TopologyResult(
        kind=None,
        fids_by_bucket=(),
        low_confidence=True,
        reason="no_grid_structure",
    )


def detect_depth_rows(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult:
    return _compute_depth(fixtures)[0]


def detect_lateral_split(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult:
    return _compute_lateral(fixtures)[0]


def detect_concentric(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult:
    return _compute_concentric(fixtures)[0]


def detect_vertical_levels(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult:
    return _compute_vertical(fixtures)[0]


def detect_bilateral_pairs(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult:
    return _compute_bilateral(fixtures)[0]


def detect_grid(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult:
    depth, _ = _compute_depth(fixtures)
    lateral, _ = _compute_lateral(fixtures)
    return _compute_grid(depth, lateral)


def classify(fixtures: tuple[SpatialFixture, ...]) -> TopologyClassification:
    """Run all six detectors and resolve contention to a single winner.

    Priority (design.md §2.4, §3):
    1. Both ``depth_rows`` and ``lateral_split`` confident with >=2 buckets
       each -> ``grid`` wins outright (the two-axis contract).
    2. Otherwise, among every OTHER confident detector, the one with the
       highest separation score (:func:`_axis_buckets`) wins — the axis that
       explains the rig's structure most cleanly, not the first one that
       happens to answer confidently (§3's non-vacuousness argument: a
       spurious y-axis gap on a circle scores far below the circle's own
       radius split, because the row bands sprawl on y while the rings do
       not).
    3. Nothing confident -> ``kind=None``, ``low_confidence=True``.
    """
    depth, depth_score = _compute_depth(fixtures)
    lateral, lateral_score = _compute_lateral(fixtures)
    concentric, concentric_score = _compute_concentric(fixtures)
    vertical, vertical_score = _compute_vertical(fixtures)
    bilateral, bilateral_score = _compute_bilateral(fixtures)
    grid = _compute_grid(depth, lateral)

    candidates = (depth, lateral, concentric, vertical, grid, bilateral)

    if grid.kind == "grid":
        return TopologyClassification(selected=grid, candidates=candidates)

    # @MX:ANCHOR: [SPEC] degenerate mirror artefact (REQ-GROUPGEN-003, live-found
    #   in M6 stage 3, mutation-required).
    # @MX:REASON: On a rig that is mirror-symmetric about the origin with y and z
    #   flat — 9 fixtures stage-right, 9 stage-left, which a designer calls
    #   "left/right" — the radius from origin collapses to |x|, so EVERY radius
    #   holds exactly one pair. The concentric reading then scores a perfect
    #   separation (live-measured 20.0 against lateral_split's 0.75) and answers
    #   "9 rings of 2". That is the MIRROR IMAGE of the defect this SPEC exists to
    #   fix (research.md §3: a 2-ring rig misread as 9 rows) — a confident answer
    #   that describes pairs instead of structure. `bilateral_pairs` being
    #   confident at the same time is the algebraic signature of that symmetry,
    #   and D-Q10 already says symmetry is a SIGNAL, never a group. So the radius
    #   reading is demoted out of contention here rather than allowed to win on a
    #   score that measures a symmetry it is not entitled to name.
    if (
        concentric.kind == "concentric"
        and not concentric.low_confidence
        and bilateral.kind == "bilateral_pairs"
        and not bilateral.low_confidence
        and len(concentric.fids_by_bucket) > 2
        and all(len(bucket) == 2 for bucket in concentric.fids_by_bucket)
    ):
        concentric = TopologyResult(
            kind=None,
            fids_by_bucket=(),
            low_confidence=True,
            reason="concentric_reading_is_a_mirror_artefact",
        )
        concentric_score = 0.0
        candidates = (depth, lateral, concentric, vertical, grid, bilateral)

    # @MX:ANCHOR: [SPEC] `bilateral_pairs` is a SIGNAL, never a selected topology
    #   (`.plan-contract.md` §2 D-Q10, mutation-required).
    # @MX:REASON: D-Q10 settled that symmetry is reported and never grouped —
    #   "미러링 가능" is a property, not a member set, and MAtricks already owns
    #   runtime mirroring (§C.0 axis E). So `naming.py` deliberately has NO
    #   vocabulary for it. Letting it WIN contention therefore produces a dead
    #   end: `selected.kind == "bilateral_pairs"` yields zero suggested groups,
    #   which reads to the operator as "the tool found nothing" when in truth it
    #   found a symmetric rig it simply must not name. Live-found in M6 stage 3,
    #   where the mirror-artefact demotion above handed it the win. It stays in
    #   `candidates` (fully reported) and out of `scored`.
    scored: list[tuple[float, TopologyResult]] = [
        (score, result)
        for result, score in (
            (depth, depth_score),
            (lateral, lateral_score),
            (concentric, concentric_score),
            (vertical, vertical_score),
        )
        if result.kind is not None and not result.low_confidence
    ]

    if not scored:
        fallback = TopologyResult(
            kind=None, fids_by_bucket=(), low_confidence=True, reason="no_topology_structure"
        )
        return TopologyClassification(selected=fallback, candidates=candidates)

    scored.sort(key=lambda item: item[0], reverse=True)
    return TopologyClassification(selected=scored[0][1], candidates=candidates)
