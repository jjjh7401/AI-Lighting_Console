"""Bind the six position roles to the rig's real groups (REQ-LOOKLIB-007/008/009).

Input is one ``get_rig_context`` groups section — the shape
``server/orchestrator/tools.py`` builds with ``rig_object`` / ``rig_section``
(``:185-230``). Output is a report: which roles found a group, which did not,
and why not.

# @MX:NOTE: [AUTO] the role layer resolves to GROUPS, never to fixture numbers.
#   A fixtures entry's number is its position in that container and is NOT
#   established to be a fixture id (tools.py:33-36), so a `Fixture a Thru b`
#   range built from it would aim at whatever happens to sit at those slots.
#   Groups are the only surface where the number IS the address. This module
#   therefore never reads the fixtures section — the absence is the design.

Three properties this module exists to hold:

* Only groups the rig listed may come back. Nothing is synthesised — not a
  number, not a name, not a substitute for a role that found nothing.
* An unmapped role is output, not failure. A rig with no naming convention
  maps zero roles and that resolve still succeeded; the report says so and the
  layers above emit no command for those roles.
* The two ways a section can fail to arrive stay apart. ``path_not_resolved``
  is a configuration defect and ``console_unreachable`` is an operating
  condition; this module propagates whatever the section said, verbatim, and
  never normalises them into one soft "unavailable" (tools.py:92-105).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.looks.roles import AMBIGUOUS, NO_MATCH, ROLES, match_role_by_name

__all__ = [
    "AMBIGUOUS",
    "NO_MATCH",
    "UNADDRESSABLE",
    "AmbiguousGroup",
    "GroupCandidate",
    "RoleResolution",
    "UnmappedRole",
    "resolve_roles",
]

# A role whose only match is a group the responder could not number. Distinct
# from NO_MATCH on purpose: "there is no backlight in this rig" and "there is
# one and it has no address" call for different fixes, and only the second one
# is repaired by giving the group a slot.
UNADDRESSABLE = "unaddressable"


@dataclass(frozen=True)
class GroupCandidate:
    """A group that exists in the rig AND carries the number that addresses it."""

    number: int
    name: str


@dataclass(frozen=True)
class AmbiguousGroup:
    """A group name claimed by two or more roles — left unassigned by all."""

    name: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class UnmappedRole:
    """A role no group was bound to, and the reason.

    ``groups`` names the rig groups behind the reason where there are any: the
    ambiguous names that claimed this role, or the unnumbered ones that matched
    it. It is empty for ``no_match`` and for an unavailable section, because in
    those cases no group is implicated.
    """

    role: str
    reason: str
    groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoleResolution:
    """What the rig could and could not answer about the six roles."""

    mapped: Mapping[str, tuple[GroupCandidate, ...]]
    unmapped: tuple[UnmappedRole, ...]
    ambiguous_groups: tuple[AmbiguousGroup, ...] = ()
    unaddressable_groups: tuple[str, ...] = ()
    unmatched_groups: tuple[str, ...] = ()
    truncated: bool = False
    unavailable_reason: str | None = None

    def groups_for(self, role: str) -> tuple[GroupCandidate, ...]:
        """Bound groups for this role — empty when it is unmapped."""
        return self.mapped.get(role, ())

    def unmapped_for(self, role: str) -> UnmappedRole | None:
        """The unmapped entry for this role, or ``None`` when it is bound."""
        for entry in self.unmapped:
            if entry.role == role:
                return entry
        return None

    def reason_for(self, role: str) -> str | None:
        """Why this role is unmapped, or ``None`` when it is bound."""
        entry = self.unmapped_for(role)
        return entry.reason if entry else None


# @MX:WARN: [AUTO] this is the only place a group reaches the look layer — the
#   candidate lists below are built EXCLUSIVELY from what the rig listed, and
#   nothing here may fabricate a number or a name for a role that found none.
# @MX:REASON: REQ-LOOKLIB-008 + rulebook 31_choreography_patterns.md:184-191.
#   The tempting repairs are all wrong: substituting a nearby group for an
#   unmapped role, taking the first hit of an ambiguous name, or numbering an
#   unnumbered group from its listing position (tools.py:180-184). Each turns a
#   report the operator can act on into a command aimed at the wrong lights.
def resolve_roles(groups_section: Mapping[str, object]) -> RoleResolution:
    """Resolve the six roles against one rig groups section.

    ``groups_section`` is either a resolved section
    (``{"objects": [...], "truncated": bool, ...}``) or the failure shape the
    tool emits when the console did not deliver it (``{"reason": ..., ...}``).
    """
    unavailable = groups_section.get("reason")
    if isinstance(unavailable, str):
        # Nothing was observed, so no role can be judged against this rig. Every
        # role carries the section's own reason rather than a matching verdict —
        # "no group matched" would be a claim about a rig we never saw.
        return RoleResolution(
            mapped={},
            unmapped=tuple(UnmappedRole(role=role.name, reason=unavailable) for role in ROLES),
            unavailable_reason=unavailable,
        )

    objects = groups_section.get("objects")
    listed: Sequence[object] = objects if isinstance(objects, list) else ()

    bound: dict[str, list[GroupCandidate]] = {}
    claimed_by_ambiguity: dict[str, list[str]] = {}
    matched_but_unnumbered: dict[str, list[str]] = {}
    ambiguous_groups: list[AmbiguousGroup] = []
    unaddressable_groups: list[str] = []
    unmatched_groups: list[str] = []

    for entry in listed:
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name", ""))
        number = entry.get("no")
        if number is None:
            # The responder positively declined to guess this slot, so the
            # rig-level fact is recorded whatever the name matched.
            unaddressable_groups.append(name)

        match = match_role_by_name(name)
        if match.reason == AMBIGUOUS:
            ambiguous_groups.append(AmbiguousGroup(name=name, roles=match.candidates))
            for role_name in match.candidates:
                claimed_by_ambiguity.setdefault(role_name, []).append(name)
            continue
        if match.role is None:
            unmatched_groups.append(name)
            continue
        if number is None:
            matched_but_unnumbered.setdefault(match.role, []).append(name)
            continue
        bound.setdefault(match.role, []).append(GroupCandidate(number=number, name=name))

    mapped: dict[str, tuple[GroupCandidate, ...]] = {}
    unmapped: list[UnmappedRole] = []
    for role in ROLES:
        candidates = bound.get(role.name)
        if candidates:
            mapped[role.name] = tuple(candidates)
            continue
        # Precedence: an unnumbered exact match is more specific — and more
        # actionable — than a name that could not decide between roles.
        unnumbered = matched_but_unnumbered.get(role.name)
        if unnumbered:
            unmapped.append(
                UnmappedRole(role=role.name, reason=UNADDRESSABLE, groups=tuple(unnumbered))
            )
            continue
        contested = claimed_by_ambiguity.get(role.name)
        if contested:
            unmapped.append(UnmappedRole(role=role.name, reason=AMBIGUOUS, groups=tuple(contested)))
            continue
        unmapped.append(UnmappedRole(role=role.name, reason=NO_MATCH))

    return RoleResolution(
        mapped=mapped,
        unmapped=tuple(unmapped),
        ambiguous_groups=tuple(ambiguous_groups),
        unaddressable_groups=tuple(unaddressable_groups),
        unmatched_groups=tuple(unmatched_groups),
        truncated=bool(groups_section.get("truncated", False)),
    )
