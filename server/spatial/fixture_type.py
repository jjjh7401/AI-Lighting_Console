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
class FixtureTypeAnalysis:
    """The type-axis verdict for one set of fixtures.

    ``type_axis_groups`` is empty exactly when ``reason`` is set (REQ-030):
    an empty tuple with ``reason is None`` would be indistinguishable from
    "this analysis was never run", which is the silent-zero this field
    exists to rule out.
    """

    type_axis_groups: tuple[FixtureTypeGroup, ...]
    fixture_count: int
    reason: str | None = None


def _field(record: Mapping[str, object], key: str, fid: object) -> str:
    if key not in record:
        raise FixtureTypeAnalysisError(f"fixture {fid!r} is missing field {key!r}")
    value = record[key]
    if not isinstance(value, str) or not value:
        raise FixtureTypeAnalysisError(
            f"fixture {fid!r} field {key!r} must be a non-empty string, got {value!r}"
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
) -> tuple[FixtureTypeGroup, ...]:
    values: dict[str, list[int]] = {}
    for fixture in fixtures:
        value = fixture.type_name if axis == "type_name" else fixture.manufacturer
        values.setdefault(value, []).append(fixture.fid)
    if len(values) <= 1:
        # This axis alone divides nothing; the caller decides overall
        # homogeneity from BOTH axes, not from one axis in isolation.
        return ()
    return tuple(
        FixtureTypeGroup(axis=axis, value=value, fids=tuple(sorted(fids)))
        for value, fids in sorted(values.items())
    )


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
        return FixtureTypeAnalysis(type_axis_groups=(), fixture_count=0, reason="no_fixtures")

    count = len(fixtures)
    groups: list[FixtureTypeGroup] = []
    for axis in FIXTURE_TYPE_AXES:
        groups.extend(_groups_for_axis(fixtures, axis))

    if not groups:
        # Neither structured field varies across the rig: REQ-030's
        # homogeneous case, measured live (Patch/FixtureTypes childCount 1).
        return FixtureTypeAnalysis(
            type_axis_groups=(), fixture_count=count, reason="homogeneous_rig"
        )

    return FixtureTypeAnalysis(
        type_axis_groups=tuple(groups), fixture_count=count, reason=None
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
    }
