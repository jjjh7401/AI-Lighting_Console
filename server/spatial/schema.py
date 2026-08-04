"""Spatial data shapes — fixtures, rows and the analysis verdict
(SPEC-COPILOT-SPATIAL-001, REQ-SPATIAL-009/010/012).

The whole spatial layer speaks these shapes and nothing else. They are frozen
dataclasses over plain numbers: no console handle, no port, no transport
reference anywhere in this package (REQ-SPATIAL-013).

Two CLOSED vocabularies live here:

* ``SPATIAL_SORTS`` — the four sort names (design.md §3.2). A caller cannot ask
  for an arbitrary ordering: an unknown name raises instead of falling back to
  a default. A silent fallback would emit a selection chain in the wrong order,
  and the stage effect of a selection order is NOT machine-readable
  (spec.md §C.1) — nothing downstream would catch it.
* ``SPATIAL_LOW_CONFIDENCE_REASONS`` — why a row verdict is not trustworthy.
  The reason is a first-class field on the result, never a log line, because
  the caller has to be able to branch on it (REQ-SPATIAL-012).

``fid`` is the identifier throughout. List position is never an identifier
(AC-SPATIAL-007), and a duplicate fid is refused at parse time: it would make
two fixtures indistinguishable and break the documented tie-break that the
determinism guarantee rests on (AC-SPATIAL-010).

Coordinates are read, never invented. A record missing an axis is refused
rather than defaulted to 0.0 (REQ-SPATIAL-004) — and note that a fixture whose
coordinates really ARE ``(0, 0, 0)`` is a successful read of an unpositioned
rig, not missing data (acceptance.md §D). The two cases must not converge on
the same value, so only one of them can be allowed to produce zeros.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

#: The four sort names, in the order design.md §3.2 tabulates them. A tuple
#: rather than a set: the order is the canonical order for reports and for the
#: exhaustiveness assertions that pin the vocabulary shut.
SPATIAL_SORTS: tuple[str, ...] = ("left_to_right", "right_to_left", "center_out", "diagonal")

#: Inter-row ordering. Stated as a value on every result rather than left to a
#: reader of the code: "row 0" is meaningless until you know which end of the
#: stage it sits at (design.md §3.2 — y ascending is stage front -> back).
SPATIAL_ROW_ORDER = "y_ascending"

#: Why a row verdict carries ``low_confidence``. Closed, because the caller
#: branches on it and an unrecognised reason reaching a user as a raw
#: identifier is the failure `server/prechk/verdicts.py` exists to prevent.
SPATIAL_LOW_CONFIDENCE_REASONS = frozenset(
    {
        # Nothing was read at all — there is no layout to have an opinion about.
        "no_fixtures",
        # Every fixture occupies the same point on ALL THREE axes. The
        # all-(0,0,0) rig lands here: a genuine read of an unpositioned rig,
        # which is exactly why it must be flagged rather than silently declared
        # a single row (acceptance.md §D).
        "no_spatial_spread",
        # Flat in the x/y plane the analysis sorts on, but the rig IS spread out
        # — vertically. A hung column or ladder of fixtures lands here.
        #
        # This is deliberately NOT "no_spatial_spread": that reason claims the
        # rig has no spatial structure, and saying it about a 5 m vertical
        # column is simply false (live-measured, progress.md §E.2.18). It would
        # also collapse two situations a caller must tell apart — an
        # unpositioned showfile, versus a deliberate vertical rig the sorting
        # vocabulary has no word for. Both are low confidence; only one means
        # "your coordinates are missing".
        "vertical_spread_only",
        # Depth varies, but no gap stands out from the typical spacing. Rows may
        # or may not exist; asserting a count here would be invention.
        "weak_gap_separation",
    }
)


class SpatialAnalysisError(ValueError):
    """A record is malformed, or a caller asked for something outside a closed set."""


@dataclass(frozen=True)
class SpatialFixture:
    """One fixture at one point in stage coordinates.

    Negative values are normal on every axis: the origin is stage centre, so
    half the rig sits at negative ``x`` by construction (acceptance.md §D).
    """

    fid: int
    name: str
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class SpatialRow:
    """One detected row: the fixtures that share a depth band.

    ``fixtures`` is held in ``(x, fid)`` ascending order — the canonical order
    for a row, since a row is by definition a set whose ``y`` values have
    collapsed, leaving ``x`` as the only meaningful axis within it. ``fid``
    ascending is the documented tie-break (AC-SPATIAL-010).

    ``center_x`` is the MIDPOINT of the row's x extent, not the mean of its
    fixture positions. ``center_out`` means "outward from the middle of the
    truss", and a mean would be dragged off the physical middle by an uneven
    fixture density (twenty pars stage-left, two stage-right).
    """

    index: int
    center_x: float
    center_y: float
    fixtures: tuple[SpatialFixture, ...]

    @property
    def fids(self) -> tuple[int, ...]:
        return tuple(fixture.fid for fixture in self.fixtures)


@dataclass(frozen=True)
class SpatialGapProfile:
    """The y-axis gap statistics a row split was decided on.

    Carried on the result so the verdict is auditable rather than an opaque
    boolean: a user told "low confidence" can be shown that the largest depth
    gap was 0.9 against a typical 0.7, which is a different conversation from
    "the analysis declined to answer".
    """

    max_gap: float
    median_gap: float
    split_threshold: float


@dataclass(frozen=True)
class SpatialAnalysis:
    """The row-detection verdict for one set of fixtures.

    ``low_confidence`` is a field, not a log line. When it is set the ``rows``
    tuple still holds a usable 1-row fallback, so a caller may proceed — but it
    proceeds knowing the structure was not established (REQ-SPATIAL-012).

    **``rows`` are DEPTH rows.** They are cut on the y axis and ordered front to
    back (:data:`SPATIAL_ROW_ORDER`); height plays no part in the cut and no
    part in any sort. That is the design (design.md §3.1), and on a floor plan
    it is the right one — but it means a 2-high x 3-wide vertical wall is ONE
    depth row, and a reply that said only "row_count: 1" would let a reader
    conclude the rig is a flat bar. ``vertical_span`` is therefore reported
    alongside: measured, stated, and explicitly not used for the cut. Silence
    about an axis the analysis chose to ignore is what makes the verdict look
    more complete than it is.
    """

    rows: tuple[SpatialRow, ...]
    fixture_count: int
    low_confidence: bool
    confidence_reason: str | None
    #: ``None`` when the gap analysis never ran (no fixtures, or no depth
    #: spread to analyse) — distinct from "it ran and found nothing".
    gaps: SpatialGapProfile | None
    #: max(z) - min(z) over every fixture read, in metres. Observation only:
    #: never an input to row detection or to any sort. ``0.0`` on a rig hung at
    #: one height, which is the ordinary truss case.
    vertical_span: float = 0.0
    row_order: str = SPATIAL_ROW_ORDER

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def fixtures(self) -> tuple[SpatialFixture, ...]:
        """Every fixture, in row order then within-row order."""
        return tuple(fixture for row in self.rows for fixture in row.fixtures)


def _coordinate(record: Mapping[str, object], axis: str, fid: int) -> float:
    if axis not in record:
        # Absence is refused, never defaulted. A zero written in here is
        # indistinguishable from a real (0,0,0) patch (REQ-SPATIAL-004).
        raise SpatialAnalysisError(f"fixture {fid} is missing coordinate {axis!r}")
    value = record[axis]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpatialAnalysisError(
            f"fixture {fid} coordinate {axis!r} must be a number, got {value!r}"
        )
    return float(value)


def spatial_fixture_from_record(record: Mapping[str, object]) -> SpatialFixture:
    """Parse one wire record ``{"fid", "name", "x", "y", "z"}``.

    Unknown keys are IGNORED rather than rejected. The closed-key discipline of
    `server/fx/loader.py` guards a repo-shipped asset against per-show values
    being smuggled in; this record is an internal hand-off from the read tool,
    which owns the wire shape and may carry provenance fields alongside the
    coordinates. Rejecting those would couple this layer to the tool's version.
    """
    if not isinstance(record, Mapping):
        raise SpatialAnalysisError(f"fixture record must be a mapping, got {record!r}")
    fid = record.get("fid")
    if isinstance(fid, bool) or not isinstance(fid, int):
        raise SpatialAnalysisError(f"fixture 'fid' must be an int, got {fid!r}")
    name = record.get("name", "")
    if not isinstance(name, str):
        raise SpatialAnalysisError(f"fixture {fid} 'name' must be a string, got {name!r}")
    return SpatialFixture(
        fid=fid,
        name=name,
        x=_coordinate(record, "x", fid),
        y=_coordinate(record, "y", fid),
        z=_coordinate(record, "z", fid),
    )


def spatial_fixtures_from_records(
    records: Sequence[Mapping[str, object]],
) -> tuple[SpatialFixture, ...]:
    """Parse the read tool's fixture list; refuse duplicate fids.

    A duplicate fid is a read defect, not a layout: two records claiming the
    same console identifier make the last-resort tie-break non-total, and a
    non-total key is exactly the "silent arbitrary choice" AC-SPATIAL-010
    forbids. It fails here, once, instead of producing a plausible order.
    """
    fixtures = tuple(spatial_fixture_from_record(record) for record in records)
    counts = Counter(fixture.fid for fixture in fixtures)
    duplicates = sorted(fid for fid, seen in counts.items() if seen > 1)
    if duplicates:
        raise SpatialAnalysisError(f"duplicate fid(s) in fixture records: {duplicates}")
    return fixtures


def spatial_analysis_to_dict(analysis: SpatialAnalysis) -> dict:
    """Serialise a verdict for a tool reply.

    Single source of the reply shape: the tool layer renders this, it does not
    re-derive it. ``row_order`` ships on every reply — the inter-row direction
    is part of the answer, not a convention the reader is expected to know. So
    does ``vertical_span``: ``row_count`` alone reads as a full description of
    the rig, and on a vertical wall it is not one.
    """
    return {
        "row_order": analysis.row_order,
        "row_count": analysis.row_count,
        "vertical_span": analysis.vertical_span,
        "fixture_count": analysis.fixture_count,
        "low_confidence": analysis.low_confidence,
        "confidence_reason": analysis.confidence_reason,
        "gaps": (
            None
            if analysis.gaps is None
            else {
                "max_gap": analysis.gaps.max_gap,
                "median_gap": analysis.gaps.median_gap,
                "split_threshold": analysis.gaps.split_threshold,
            }
        ),
        "rows": [
            {
                "index": row.index,
                "center_x": row.center_x,
                "center_y": row.center_y,
                "fids": list(row.fids),
            }
            for row in analysis.rows
        ],
    }
