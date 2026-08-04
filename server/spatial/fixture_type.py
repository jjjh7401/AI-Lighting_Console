"""Fixture-type axis — patch structured-field grouping (REQ-008/009/013/030,
design.md §5, spec.md §D).

v1 scope is deliberately narrow (D-Q9/D-Q11, user-approved): this module reads
the three structured fields the console already carries under
``Patch/FixtureTypes/<n>`` — ``Manufacturer``, ``name`` (type name), and
``ShortName`` — and groups fixtures whose values match, with ZERO string
processing beyond equality (REQ-009). It does not classify fixtures into
industry categories (Spot/Wash/Beam/...): GDTF's FixtureType node carries no
``Categories`` field, so a category call would be a guess dressed as a fact,
and this module never makes that guess. See the module-level exclusion list
below for the full "not in v1" set.

Excluded from v1 (see TASK M1b brief for the full rationale):

* Category token matching (Spot/Wash/Beam/PAR/Fresnel/Profile/Strobe/
  Blinder/Effect/Follow Spot) — no console-side field backs this; it would be
  inference from a free-text type name, which is exactly what REQ-009
  forbids for THIS axis.
* Type x position-row cross grouping — empty executor/group slots are a
  finite resource (design.md §5); crossing axes multiplies candidates and
  this module does not manufacture that multiplication.
* Blinder separation. Identifying a blinder requires the category call this
  module does not make; this module carries no code or comment implying that
  separation happens here or anywhere downstream of it.

This module does not talk to the console. It is a pure function over already-
read records: no transport-layer import, no safety-gate import, no new
runtime dependency (REQ-006 boundary — enforced globally by
``server/tests/test_architecture.py``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

#: Why ``type_axis_groups`` came back empty. A first-class field, never a log
#: line — REQ-030 forbids a silent zero: the rig may genuinely have one
#: fixture type (our measured rig does — ``Patch/FixtureTypes`` childCount 1),
#: and that must be reported as a verdict, not mistaken for an unread input.
FIXTURE_TYPE_NO_GROUPS_REASONS = frozenset(
    {
        "no_fixtures",
        # Every fixture shares BOTH structured fields this axis reads
        # (manufacturer and type name). Nothing on this axis can divide them.
        "homogeneous_rig",
    }
)

#: The two structured-field axes this module groups on (design.md §5,
#: research.md §7.3.1 2-hop path). Closed on purpose: adding an axis means
#: adding a field this module reads from the patch, not inferring one.
FIXTURE_TYPE_AXES: tuple[str, ...] = ("type_name", "manufacturer")

#: Why one axis alone did not split the rig, distinct from the
#: rig-level ``FIXTURE_TYPE_NO_GROUPS_REASONS`` above (SPEC amendment
#: v0.4.0, defect 1 — a silent per-axis ``()`` used to carry no signal at
#: all: a reader could not tell "this axis was examined and found uniform"
#: from "this axis was never looked at"). Two distinct sub-reasons:
FIXTURE_TYPE_AXIS_UNSPLIT_REASON_UNIFORM = "uniform_across_rig"
FIXTURE_TYPE_AXIS_UNSPLIT_REASON_ALL_UNREADABLE = "all_values_unreadable"

#: Why one fixture is excluded from one axis's grouping (SPEC amendment
#: v0.4.0, defect 2). The only case v1 recognises: the console's structured
#: field for this fixture reads as the empty string (measured live —
#: ``Patch/FixtureTypes/2`` on the real console has ``Manufacturer: ''``).
#: A missing key or a non-string value is still a caller contract violation
#: and still raises ``FixtureTypeAnalysisError`` — this reason covers ONLY
#: the "field present, typed correctly, but empty" case.
FIXTURE_TYPE_EMPTY_FIELD_REASON = "empty_structured_field"


class FixtureTypeAnalysisError(ValueError):
    """A record is malformed for this axis."""


@dataclass(frozen=True)
class FixtureTypeRecord:
    """One fixture's structured type fields, read from ``Patch/FixtureTypes``.

    ``short_name`` is carried through (research.md §7.3.1 measured it
    alongside ``name``/``Manufacturer``) but is NOT a grouping axis in v1 —
    it is the same string family as ``type_name`` and grouping on both would
    double-count the same distinction under two labels.
    """

    fid: int
    manufacturer: str
    type_name: str
    short_name: str = ""


@dataclass(frozen=True)
class FixtureTypeGroup:
    """One candidate group: fixtures sharing a value on one structured axis."""

    axis: str
    value: str
    fids: tuple[int, ...]


@dataclass(frozen=True)
class FixtureTypeAxisReport:
    """Per-axis verdict, reported for EVERY axis in ``FIXTURE_TYPE_AXES`` —
    including one that did not split the rig (SPEC amendment v0.4.0,
    defect 1). ``split`` is False exactly when ``reason`` is set, mirroring
    the rig-level ``FixtureTypeAnalysis.reason`` invariant one level down.
    """

    axis: str
    distinct_value_count: int
    split: bool
    reason: str | None = None


@dataclass(frozen=True)
class FixtureTypeUnreadable:
    """One fixture excluded from one axis because its structured field for
    that axis reads as the empty string (SPEC amendment v0.4.0, defect 2).
    The fixture still participates normally in every OTHER axis.
    """

    fid: int
    axis: str
    reason: str


@dataclass(frozen=True)
class FixtureTypeAnalysis:
    """The type-axis verdict for one set of fixtures.

    ``type_axis_groups`` is empty exactly when ``reason`` is set (REQ-030):
    an empty tuple with ``reason is None`` would be indistinguishable from
    "this analysis was never run", which is the silent-zero this field
    exists to rule out. ``reason``'s existing meaning (``no_fixtures`` /
    ``homogeneous_rig``) is unchanged by this amendment — ``axis_reports``
    and ``unreadable`` are additive fields reporting a finer grain.
    """

    type_axis_groups: tuple[FixtureTypeGroup, ...]
    fixture_count: int
    reason: str | None = None
    axis_reports: tuple[FixtureTypeAxisReport, ...] = ()
    unreadable: tuple[FixtureTypeUnreadable, ...] = ()


def _field(record: Mapping[str, object], key: str, fid: object) -> str:
    """Read one structured field. Raises on a missing key or a non-string
    value — those are caller contract violations, not MA3 data. An empty
    string IS valid MA3 data (measured live: ``Patch/FixtureTypes/2``'s
    ``Manufacturer`` is ``''`` on a generic MA3 type) and passes through
    here; per-axis exclusion of empty values happens in ``_groups_for_axis``,
    not here — this function's contract is "is this readable at all", not
    "is this non-empty".
    """
    if key not in record:
        raise FixtureTypeAnalysisError(f"fixture {fid!r} is missing field {key!r}")
    value = record[key]
    if not isinstance(value, str):
        raise FixtureTypeAnalysisError(
            f"fixture {fid!r} field {key!r} must be a string, got {value!r}"
        )
    return value


def fixture_type_record_from_record(record: Mapping[str, object]) -> FixtureTypeRecord:
    """Parse one wire record ``{"fid", "manufacturer", "type_name", "short_name"?}``.

    Unknown keys are ignored (same rationale as
    ``server/spatial/schema.py::spatial_fixture_from_record`` — this is an
    internal hand-off from the read tool, not a repo-shipped asset).
    """
    if not isinstance(record, Mapping):
        raise FixtureTypeAnalysisError(f"fixture record must be a mapping, got {record!r}")
    fid = record.get("fid")
    if isinstance(fid, bool) or not isinstance(fid, int):
        raise FixtureTypeAnalysisError(f"fixture 'fid' must be an int, got {fid!r}")
    short_name = record.get("short_name", "")
    if not isinstance(short_name, str):
        raise FixtureTypeAnalysisError(
            f"fixture {fid} 'short_name' must be a string, got {short_name!r}"
        )
    return FixtureTypeRecord(
        fid=fid,
        manufacturer=_field(record, "manufacturer", fid),
        type_name=_field(record, "type_name", fid),
        short_name=short_name,
    )


def fixture_type_records_from_records(
    records: Sequence[Mapping[str, object]],
) -> tuple[FixtureTypeRecord, ...]:
    """Parse the read tool's fixture list for the type axis."""
    return tuple(fixture_type_record_from_record(record) for record in records)


def _groups_for_axis(
    fixtures: Sequence[FixtureTypeRecord], axis: str
) -> tuple[tuple[FixtureTypeGroup, ...], int, tuple[FixtureTypeUnreadable, ...]]:
    """Group fixtures on one axis, excluding — per-item, not per-call — any
    fixture whose value on THIS axis is empty (SPEC amendment v0.4.0,
    defect 2). A fixture excluded here still groups normally on the other
    axis (an empty ``manufacturer`` does not touch ``type_name``).

    Returns ``(groups, distinct_value_count, unreadable)`` — the caller
    builds the per-axis :class:`FixtureTypeAxisReport` from all three so a
    "this axis divides nothing" verdict is never silent (defect 1).
    """
    values: dict[str, list[int]] = {}
    unreadable: list[FixtureTypeUnreadable] = []
    for fixture in fixtures:
        value = fixture.type_name if axis == "type_name" else fixture.manufacturer
        if not value:
            unreadable.append(
                FixtureTypeUnreadable(
                    fid=fixture.fid, axis=axis, reason=FIXTURE_TYPE_EMPTY_FIELD_REASON
                )
            )
            continue
        values.setdefault(value, []).append(fixture.fid)
    if len(values) <= 1:
        # This axis alone divides nothing; the caller decides overall
        # homogeneity from BOTH axes, not from one axis in isolation.
        return (), len(values), tuple(unreadable)
    groups = tuple(
        FixtureTypeGroup(axis=axis, value=value, fids=tuple(sorted(fids)))
        for value, fids in sorted(values.items())
    )
    return groups, len(values), tuple(unreadable)


def analyze_fixture_types(fixtures: Sequence[FixtureTypeRecord]) -> FixtureTypeAnalysis:
    """Group fixtures by the console's structured type fields.

    Groups come back per-axis (``type_name`` then ``manufacturer``,
    :data:`FIXTURE_TYPE_AXES` order) rather than merged into one combined key:
    a caller asking "what manufacturers are on this rig" and a caller asking
    "what types are on this rig" are different questions, and merging the
    axes would force one reader to unpick the other's answer out of a
    compound label.
    """
    if not fixtures:
        # No fixtures at all: every axis is reported "no_fixtures" too — the
        # rig-level reason and the per-axis reason agree, rather than the
        # per-axis report going missing for the one case with zero input.
        axis_reports = tuple(
            FixtureTypeAxisReport(
                axis=axis, distinct_value_count=0, split=False, reason="no_fixtures"
            )
            for axis in FIXTURE_TYPE_AXES
        )
        return FixtureTypeAnalysis(
            type_axis_groups=(),
            fixture_count=0,
            reason="no_fixtures",
            axis_reports=axis_reports,
            unreadable=(),
        )

    count = len(fixtures)
    groups: list[FixtureTypeGroup] = []
    axis_reports: list[FixtureTypeAxisReport] = []
    unreadable: list[FixtureTypeUnreadable] = []
    for axis in FIXTURE_TYPE_AXES:
        axis_groups, distinct_count, axis_unreadable = _groups_for_axis(fixtures, axis)
        unreadable.extend(axis_unreadable)
        split = bool(axis_groups)
        if split:
            axis_reason = None
        elif distinct_count == 0:
            axis_reason = FIXTURE_TYPE_AXIS_UNSPLIT_REASON_ALL_UNREADABLE
        else:
            axis_reason = FIXTURE_TYPE_AXIS_UNSPLIT_REASON_UNIFORM
        axis_reports.append(
            FixtureTypeAxisReport(
                axis=axis, distinct_value_count=distinct_count, split=split, reason=axis_reason
            )
        )
        groups.extend(axis_groups)

    if not groups:
        # Neither structured field varies across the rig: REQ-030's
        # homogeneous case, measured live (Patch/FixtureTypes childCount 1).
        # (Rig-level reason meaning is unchanged by this amendment.)
        return FixtureTypeAnalysis(
            type_axis_groups=(),
            fixture_count=count,
            reason="homogeneous_rig",
            axis_reports=tuple(axis_reports),
            unreadable=tuple(unreadable),
        )

    return FixtureTypeAnalysis(
        type_axis_groups=tuple(groups),
        fixture_count=count,
        reason=None,
        axis_reports=tuple(axis_reports),
        unreadable=tuple(unreadable),
    )


def analyze_fixture_type_records(records: Sequence[Mapping[str, object]]) -> FixtureTypeAnalysis:
    """Parse the read tool's fixture records, then group them on the type axis."""
    return analyze_fixture_types(fixture_type_records_from_records(records))


def fixture_type_analysis_to_dict(analysis: FixtureTypeAnalysis) -> dict:
    """Serialise a verdict for a tool reply — single source of the reply shape."""
    return {
        "fixture_count": analysis.fixture_count,
        "reason": analysis.reason,
        "type_axis_groups": [
            {"axis": group.axis, "value": group.value, "fids": list(group.fids)}
            for group in analysis.type_axis_groups
        ],
        "axis_reports": [
            {
                "axis": report.axis,
                "distinct_value_count": report.distinct_value_count,
                "split": report.split,
                "reason": report.reason,
            }
            for report in analysis.axis_reports
        ],
        "unreadable": [
            {"fid": item.fid, "axis": item.axis, "reason": item.reason}
            for item in analysis.unreadable
        ],
    }
