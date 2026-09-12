"""역할 어휘를 리그의 실제 그룹에 묶는다 (REQ-LOOKLIB-007/008/009).

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

from server.looks.roles import (
    AMBIGUOUS,
    NO_MATCH,
    ROLES,
    match_role_by_name,
    resolve_role_token,
)

__all__ = [
    "ALIAS_UNKNOWN_ROLE",
    "AMBIGUOUS",
    "NO_MATCH",
    "UNADDRESSABLE",
    "AliasRejection",
    "AmbiguousGroup",
    "GroupCandidate",
    "RoleResolution",
    "UnmappedRole",
    "normalize_aliases",
    "resolve_roles",
]

# 쇼 단위 별칭 표가 모르는 역할 이름을 들었다. 그룹은 매핑되지 않고 이 코드로
# 보고된다 — 힌트 매칭으로 되돌리지 **않는다**: 운영자는 그 그룹을 특정 역할에
# 주기로 정했고, 오타를 자동 해석하면 운영자가 지정하지 않은 조명이 켜진다.
ALIAS_UNKNOWN_ROLE = "alias_unknown_role"

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
class AliasRejection:
    """쇼 별칭 표의 한 줄이 거절됐다 — 그룹명과 그 줄이 요구한 역할 토큰."""

    group: str
    requested: str


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
    """리그가 역할들에 대해 답한 것과 답하지 못한 것."""

    mapped: Mapping[str, tuple[GroupCandidate, ...]]
    unmapped: tuple[UnmappedRole, ...]
    ambiguous_groups: tuple[AmbiguousGroup, ...] = ()
    unaddressable_groups: tuple[str, ...] = ()
    unmatched_groups: tuple[str, ...] = ()
    alias_rejections: tuple[AliasRejection, ...] = ()
    """모르는 역할 이름을 든 별칭 줄. 해당 그룹은 ``unmatched_groups`` 에도 들어간다 —
    「모든 그룹이 어느 한 칸에는 계상된다」는 불변식을 이 갈래도 지킨다."""

    unused_aliases: tuple[str, ...] = ()
    """리그가 올린 어느 그룹명과도 안 맞은 별칭 키. 표의 오타는 이쪽으로 나온다."""

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
def normalize_aliases(aliases: Mapping[str, str] | None) -> dict[str, str]:
    """쇼 별칭 표를 대조용 키로 정규화한다 — 앞뒤 공백 제거 + casefold.

    리그 그룹명은 대소문자·여백이 제각각이라(`WASH-U` 대 `wash-u `) 키를 글자
    그대로 두면 표가 리그의 표기를 따라다녀야 한다. 값(역할 토큰)은 건드리지
    않고 그대로 넘긴다 — 해석은 :func:`resolve_role_token` 의 몫이다.
    """
    if not aliases:
        return {}
    return {str(key).strip().casefold(): value for key, value in aliases.items()}


def resolve_roles(
    groups_section: Mapping[str, object],
    *,
    aliases: Mapping[str, str] | None = None,
) -> RoleResolution:
    """역할들을 리그 groups 섹션 하나에 대고 해석한다.

    ``groups_section`` 은 해석된 섹션
    (``{"objects": [...], "truncated": bool, ...}``)이거나, 콘솔이 주지 못했을 때
    도구가 내는 실패 형태(``{"reason": ..., ...}``)다.

    ``aliases`` 는 **쇼 단위** 그룹명 → 역할 이름 표다(그룹명은 대소문자 무시).
    힌트 목록보다 **먼저** 보고 이긴다 — 다음 리그의 그룹명이 이 저장소의 힌트와
    맞을 이유가 없으므로, 리그마다 코드를 고치지 않고 붙이는 자리가 필요하다.
    """
    alias_map = normalize_aliases(aliases)
    unavailable = groups_section.get("reason")
    if isinstance(unavailable, str):
        # Nothing was observed, so no role can be judged against this rig. Every
        # role carries the section's own reason rather than a matching verdict —
        # "no group matched" would be a claim about a rig we never saw.
        # 관측 자체가 없었으므로 별칭 표에 대해서도 아무것도 주장하지 않는다 —
        # 안 본 리그를 두고 「이 별칭은 안 쓰였다」고 말할 수 없다.
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
    alias_rejections: list[AliasRejection] = []
    consumed_aliases: set[str] = set()

    for entry in listed:
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name", ""))
        number = entry.get("no")
        if number is None:
            # The responder positively declined to guess this slot, so the
            # rig-level fact is recorded whatever the name matched.
            unaddressable_groups.append(name)

        alias_key = name.strip().casefold()
        if alias_key in alias_map:
            consumed_aliases.add(alias_key)
            requested = alias_map[alias_key]
            forced = resolve_role_token(requested)
            if forced is None:
                alias_rejections.append(AliasRejection(group=name, requested=str(requested)))
                unmatched_groups.append(name)
                continue
            if number is None:
                matched_but_unnumbered.setdefault(forced, []).append(name)
                continue
            bound.setdefault(forced, []).append(GroupCandidate(number=number, name=name))
            continue

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
        alias_rejections=tuple(alias_rejections),
        unused_aliases=tuple(key for key in alias_map if key not in consumed_aliases),
        truncated=bool(groups_section.get("truncated", False)),
    )
