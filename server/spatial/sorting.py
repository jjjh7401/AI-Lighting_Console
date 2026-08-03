"""The four sort orders (REQ-SPATIAL-009, design.md §3.2, AC-SPATIAL-012).

A sort turns a detected row structure into ONE ordered chain of fixtures. That
chain is the whole realisation axis of spatial choreography: downstream, the
fids are emitted as a selection chain and the existing phaser grammar rides on
top of it (REQ-SPATIAL-014). Coordinates never reach a command — only the order
they implied.

The vocabulary is closed. ``spatial_sorted_fixtures`` raises on any name outside
:data:`SPATIAL_SORTS` rather than falling back to a default order, because the
stage effect of a selection order is not machine-readable (spec.md §C.1): a
wrong-but-plausible chain would execute silently and look fine in every log.

**The tie-break, stated once and applied identically in all four:** the last
component of every sort key is ``fid`` ascending. Two fixtures at the same
coordinates therefore always come out in the same order, and so do two fixtures
that merely tie on a derived metric — a ``center_out`` pair mirrored either
side of the row centre resolves by fid, not by side. AC-SPATIAL-010 forbids
resolving a tie by SILENT ARBITRARY choice; a documented total key is the
remedy, not the violation (acceptance.md §D reconciles the two).

Row-scoped sorts (``left_to_right``, ``right_to_left``, ``center_out``) run
within each row and concatenate the rows in the analysis's own row order, which
is ``y`` ascending — stage front to back. ``diagonal`` is the one sort that
re-orders across rows.
"""

from __future__ import annotations

from collections.abc import Callable

from server.spatial.schema import (
    SPATIAL_SORTS,
    SpatialAnalysis,
    SpatialAnalysisError,
    SpatialFixture,
    SpatialRow,
)

# Within-row keys. Each is (coordinate metric, fid) — the fid component is the
# documented tie-break and the reason every key is total.
_WITHIN_ROW_KEYS: dict[str, Callable[[SpatialFixture, SpatialRow], tuple[float, int]]] = {
    "left_to_right": lambda fixture, _row: (fixture.x, fixture.fid),
    "right_to_left": lambda fixture, _row: (-fixture.x, fixture.fid),
    "center_out": lambda fixture, row: (abs(fixture.x - row.center_x), fixture.fid),
}


def _diagonal(analysis: SpatialAnalysis) -> tuple[SpatialFixture, ...]:
    """Combine row order and within-row x order into one diagonal chain.

    The chain is the anti-diagonal wavefront: fixtures are ordered by
    ``row index + column index``, where the column index is a fixture's
    position in its row's x-ascending order. Everything on one wavefront leaves
    together, front row first.

    On a 3-row rig that is ``(r0,c0)``, then ``(r0,c1) (r1,c0)``, then
    ``(r0,c2) (r1,c1) (r2,c0)``, ... — a line sweeping across the rig at 45
    degrees. On a single-row rig every column index equals its diagonal, so the
    order degenerates to ``left_to_right``, which is the right answer: a line
    has no second axis to be diagonal across.

    Rows of unequal length need no special case — the column index is a
    position within the row, not a grid coordinate.
    """
    keyed = [
        ((row.index + column, row.index, fixture.fid), fixture)
        for row in analysis.rows
        for column, fixture in enumerate(row.fixtures)
    ]
    keyed.sort(key=lambda entry: entry[0])
    return tuple(fixture for _key, fixture in keyed)


def spatial_sorted_fixtures(analysis: SpatialAnalysis, sort: str) -> tuple[SpatialFixture, ...]:
    """Order every fixture in ``analysis`` by one of the four closed sorts.

    Works unchanged on a low-confidence analysis: the one-row fallback is a
    real row, so the chain is still produced. Whether to USE it is the caller's
    call, made against the ``low_confidence`` field (REQ-SPATIAL-012) — this
    layer neither hides the flag nor refuses to compute.
    """
    if sort not in SPATIAL_SORTS:
        raise SpatialAnalysisError(f"{sort!r} is not a spatial sort (allowed: {SPATIAL_SORTS})")
    if sort == "diagonal":
        return _diagonal(analysis)
    key = _WITHIN_ROW_KEYS[sort]
    chain: list[SpatialFixture] = []
    for row in analysis.rows:
        keyed = [(key(fixture, row), fixture) for fixture in row.fixtures]
        keyed.sort(key=lambda entry: entry[0])
        chain.extend(fixture for _key, fixture in keyed)
    return tuple(chain)


def spatial_sorted_fids(analysis: SpatialAnalysis, sort: str) -> tuple[int, ...]:
    """The sorted chain as bare fids — what a selection chain is built from."""
    return tuple(fixture.fid for fixture in spatial_sorted_fixtures(analysis, sort))
