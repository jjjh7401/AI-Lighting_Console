"""Row detection — y-axis gap clustering (REQ-SPATIAL-011/012, design.md §3.1).

Standard-library arithmetic only. No sklearn, no numpy, no new dependency of
any kind: the whole method is "sort the depths, look at the gaps between
neighbours, cut where a gap stands out". That is a handful of subtractions and
one median, and a clustering library would hide the one decision that actually
matters — WHERE the cut goes — behind a fitted model nobody can pin with a
golden test.

The method, in order:

1. **No fixtures** -> nothing to say. Low confidence, zero rows.
2. **No spread on either axis the analysis uses** (``x`` and ``y`` both flat
   within :data:`SPATIAL_ROW_NOISE_SPAN`) -> every fixture is on the same
   point. Low confidence, one-row fallback. This is the all-(0,0,0) rig: a
   SUCCESSFUL read of a patched-but-unpositioned show, not missing data
   (acceptance.md §D). ``z`` is deliberately excluded — height is used by
   neither row detection nor any of the four sorts, so a vertical stack of pars
   at one ``(x, y)`` has no more usable structure than a single point.
3. **Depth flat, width not** -> the rig is a line along ``x``. Exactly one row,
   and CONFIDENT: this is the 1x30 golden, and AC-SPATIAL-011 requires the
   low-confidence signal to be ABSENT on a regular layout.
4. **Depth varies** -> gap analysis. Cut at every gap wider than the split
   threshold. If no gap clears it, the structure was not established: low
   confidence, one-row fallback (REQ-SPATIAL-012 — never force a single-row
   assumption through quietly).

The split threshold is one expression, used both to decide WHETHER rows exist
and WHERE they divide::

    split_threshold = max(SPATIAL_ROW_GAP_RATIO * median_gap, SPATIAL_ROW_NOISE_SPAN)

Applying the same number to both questions is what keeps them consistent: "rows
exist" means precisely "at least one gap is a row boundary". A separate
confidence statistic could report high confidence while no gap qualified to cut
on, which is a verdict with no rows behind it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import median

from server.spatial.schema import (
    SpatialAnalysis,
    SpatialFixture,
    SpatialGapProfile,
    SpatialRow,
    spatial_fixtures_from_records,
)

#: How far apart two depths may be and still count as the same row.
#:
#: Stage coordinates are metres (design.md §2.3 samples them as ``x: -4.5``,
#: ``z: 3.0`` — a room, not a millimetre grid), so 5 cm is rigging tolerance:
#: a bar hung a finger's width out of true is the same row, and no rig has rows
#: 5 cm apart. It is an ABSOLUTE floor on purpose. A purely relative threshold
#: cannot distinguish "thirty fixtures on one bar with 2 cm of hanging slop"
#: from "thirty fixtures in rows 2 cm apart", because the two are numerically
#: identical and only the physical scale tells them apart.
SPATIAL_ROW_NOISE_SPAN = 0.05

#: How many times the typical gap a gap must exceed to be a row boundary.
#:
#: The two populations this separates are not close. In a real multi-row rig the
#: fixtures of a row SHARE a depth, so within-row gaps collapse to zero (or to
#: hanging slop) while the inter-row gap is metres — the observed ratio is in
#: the hundreds, and unbounded when rows are exactly aligned, which is the
#: ordinary case. In a rig with no rows the gaps are all of a size and the ratio
#: sits near 1. Anything in between is genuinely ambiguous, and REQ-SPATIAL-012
#: puts ambiguity on the low-confidence side rather than guessing a count.
#:
#: 4.0 is chosen inside that empty band: high enough that the uneven spacing of
#: a scattered rig does not manufacture a row boundary (independently spaced
#: points produce max/median gap ratios of roughly 3-6 for a rig of this size),
#: low enough that a real rig with sloppy hanging still clears it by an order of
#: magnitude. Both constants are pinned by golden tests, which is where the
#: choice actually lives — design.md §3.1 leaves the value to implementation and
#: requires exactly that pinning.
SPATIAL_ROW_GAP_RATIO = 4.0


def _row(index: int, members: Sequence[SpatialFixture]) -> SpatialRow:
    """Build one row with its members in canonical ``(x, fid)`` order."""
    ordered = tuple(sorted(members, key=lambda fixture: (fixture.x, fixture.fid)))
    xs = [fixture.x for fixture in ordered]
    ys = [fixture.y for fixture in ordered]
    return SpatialRow(
        index=index,
        center_x=(min(xs) + max(xs)) / 2.0,
        center_y=(min(ys) + max(ys)) / 2.0,
        fixtures=ordered,
    )


def analyze_spatial_rows(fixtures: Sequence[SpatialFixture]) -> SpatialAnalysis:
    """Detect rows by y-axis gap clustering.

    Rows come back in ``y`` ascending order — stage front to back — and the
    result carries ``row_order`` saying so, rather than leaving the direction
    to a reader of this docstring.

    Deterministic by construction: fixtures are ordered on the total key
    ``(y, x, fid)`` before anything is measured, and ``fid`` ascending is the
    documented final tie-break, so two fixtures at identical coordinates always
    come out in the same order (AC-SPATIAL-010). The tie-break is a stated rule,
    not an arbitrary choice — what is forbidden is resolving a tie SILENTLY.
    """
    if not fixtures:
        return SpatialAnalysis(
            rows=(),
            fixture_count=0,
            low_confidence=True,
            confidence_reason="no_fixtures",
            gaps=None,
        )

    ordered = sorted(fixtures, key=lambda fixture: (fixture.y, fixture.x, fixture.fid))
    count = len(ordered)
    xs = [fixture.x for fixture in ordered]
    x_span = max(xs) - min(xs)
    ys = [fixture.y for fixture in ordered]
    y_span = ys[-1] - ys[0]
    # Height is MEASURED but never used to cut a row or order a sort. It is
    # reported so the verdict cannot imply an axis was flat when it was not.
    zs = [fixture.z for fixture in ordered]
    vertical_span = max(zs) - min(zs)

    if max(x_span, y_span) <= SPATIAL_ROW_NOISE_SPAN:
        # Flat in the plane this analysis sorts on. Whether that means "no rig
        # information" or "a vertical rig" depends on z, and the two must not
        # share a reason: one says the showfile is unpositioned, the other says
        # the rig is real and this vocabulary has no word for its shape.
        # Live-measured both ways (progress.md §E.2.18).
        #
        # Note this is also the n == 1 case: a single fixture has zero spread by
        # definition and establishes no structure, so it is honestly reported as
        # unstructured rather than as a confident row of one.
        vertical = vertical_span > SPATIAL_ROW_NOISE_SPAN
        return SpatialAnalysis(
            rows=(_row(0, ordered),),
            fixture_count=count,
            low_confidence=True,
            confidence_reason="vertical_spread_only" if vertical else "no_spatial_spread",
            gaps=None,
            vertical_span=vertical_span,
        )

    if y_span <= SPATIAL_ROW_NOISE_SPAN:
        # Flat depth, real width: a single bar. `gaps` stays None because the
        # gap analysis was short-circuited, which is a different fact from
        # "it ran and found no boundary".
        #
        # Confidence is NOT lowered when this bar also has height. A real truss
        # hangs with centimetres of variation, and treating that as ambiguity
        # would cry wolf on the commonest rig there is. The vertical extent
        # rides on `vertical_span` instead, where a caller that cares can see
        # it: one DEPTH row is the true answer to the question actually asked.
        return SpatialAnalysis(
            rows=(_row(0, ordered),),
            fixture_count=count,
            low_confidence=False,
            confidence_reason=None,
            gaps=None,
            vertical_span=vertical_span,
        )

    gaps = [ys[i + 1] - ys[i] for i in range(count - 1)]
    median_gap = median(gaps)
    profile = SpatialGapProfile(
        max_gap=max(gaps),
        median_gap=median_gap,
        split_threshold=max(SPATIAL_ROW_GAP_RATIO * median_gap, SPATIAL_ROW_NOISE_SPAN),
    )
    boundaries = [i for i, gap in enumerate(gaps) if gap > profile.split_threshold]

    if not boundaries:
        return SpatialAnalysis(
            rows=(_row(0, ordered),),
            fixture_count=count,
            low_confidence=True,
            confidence_reason="weak_gap_separation",
            gaps=profile,
            vertical_span=vertical_span,
        )

    rows: list[SpatialRow] = []
    start = 0
    for boundary in [*boundaries, count - 1]:
        rows.append(_row(len(rows), ordered[start : boundary + 1]))
        start = boundary + 1
    return SpatialAnalysis(
        rows=tuple(rows),
        fixture_count=count,
        low_confidence=False,
        confidence_reason=None,
        gaps=profile,
        vertical_span=vertical_span,
    )


def analyze_spatial_records(records: Sequence[Mapping[str, object]]) -> SpatialAnalysis:
    """Parse the read tool's fixture records, then detect rows over them."""
    return analyze_spatial_rows(spatial_fixtures_from_records(records))
