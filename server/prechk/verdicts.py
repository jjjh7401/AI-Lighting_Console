"""Closed judgement vocabularies for the rig pre-check (design.md slot C).

Every judgement the pre-check emits comes from one of these sets. They are code
constants, not free strings, for two reasons:

  * a free-string reason cannot be aggregated, and the report has to count
    verdicts per class (REQ-PRECHK-015, REQ-PRECHK-016);
  * an unknown code must FAIL LOUDLY rather than reach the user as a raw
    identifier -- :func:`validate` is the single place that decision lives
    (AC-PRECHK-012 ⑤ d).

Korean labels are NOT here. Labels are a presentation concern and live in the
report layer, which asserts that its label table's key set equals these sets
exactly (AC-PRECHK-012 ⑤ a).
"""

from __future__ import annotations

from types import MappingProxyType

COMPLETENESS = frozenset({"complete", "incomplete"})

FIXTURE_VERDICT = frozenset({"observed_clear", "collision", "read_failed", "not_assessed"})

COLLISION_KIND = frozenset({"address_duplicate", "range_overlap"})

READ_FAILURE_KIND = frozenset(
    {"property_unreadable", "shape_invalid", "address_parse_failed", "type_mode_unresolved"}
)

SKIPPED_CHECK_KIND = frozenset(
    {
        "range_overlap_descope",
        "range_overlap_bound_inconclusive",
        "macro_descope",
        "macro_no_groups",
        "gate_unapproved",
    }
)

#: How a range-overlap judgement was reached. Four grades ordered by claim
#: strength: ``not_performed`` (no comparison) < ``bound_inconclusive`` (the
#: gap is smaller than the widest enumerable footprint, so nothing is settled --
#: NOT a collision) < ``bound_proves_clear`` (the gap exceeds that upper bound,
#: so no overlap is possible ACROSS THE OBSERVED MODE SET) < ``exact_widths``
#: (the real footprints were joined, so the verdict is unqualified).
#: The asymmetry is the point: an upper bound can prove absence, never presence.
OVERLAP_BASIS = frozenset(
    {"exact_widths", "bound_proves_clear", "bound_inconclusive", "not_performed"}
)

CLOSED_VOCABULARIES = MappingProxyType(
    {
        "completeness": COMPLETENESS,
        "fixture_verdict": FIXTURE_VERDICT,
        "collision_kind": COLLISION_KIND,
        "read_failure_kind": READ_FAILURE_KIND,
        "skipped_check_kind": SKIPPED_CHECK_KIND,
        "overlap_basis": OVERLAP_BASIS,
    }
)


class UnknownVerdict(ValueError):
    """A value outside its closed vocabulary reached a judgement surface."""


def validate(vocabulary: str, value: str) -> str:
    """Return ``value`` if it belongs to ``vocabulary``; otherwise raise.

    Raises :class:`UnknownVerdict` -- never returns a fallback and never lets an
    unrecognized code pass through silently.
    """
    try:
        allowed = CLOSED_VOCABULARIES[vocabulary]
    except KeyError:
        raise UnknownVerdict(
            f"no such vocabulary {vocabulary!r} (known: {sorted(CLOSED_VOCABULARIES)})"
        ) from None
    if value not in allowed:
        raise UnknownVerdict(f"{value!r} is not a {vocabulary} (allowed: {sorted(allowed)})")
    return value
