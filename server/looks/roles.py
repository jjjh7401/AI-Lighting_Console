"""Closed position-role vocabulary + name-matching discipline (REQ-LOOKLIB-006/009).

Six roles, confirmed as a closed set (spec.md §A, 사용자 확정 ⑨ / plan.md §A.4a
decision J). Each carries one Korean primary name, at least one English alias
and at least one mapping hint — the hints are what a rig's group names are
matched against.

This vocabulary is NEW. It does not extend ``20_korean_terms.md``: that file's
showfile rows are fixture TYPE classes (워시 / 스팟 / 빔), not stage positions,
and it is a PRESERVE target. Only its naming STYLE is inherited.

Fixture type-class words are deliberately absent from every hint set. One Wash
fixture can be a backlight in one rig and a front in another, so a type-class
hint mis-aims systematically rather than occasionally.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

AMBIGUOUS = "ambiguous"
NO_MATCH = "no_match"

# Characters that count as "inside a word" for boundary purposes. Hangul is a
# word character here on purpose: Python's ``\b`` would happily match `백`
# inside `백색`, because both sides are ``\w``.
_WORD = r"[0-9A-Za-zㄱ-ㆎ가-힣]"


@dataclass(frozen=True)
class Role:
    """One position role: Korean primary name + aliases + group-name hints."""

    name: str
    aliases: tuple[str, ...]
    hints: tuple[str, ...]
    abbreviations: tuple[str, ...]


# The hint strings are verbatim from spec.md §A. M0 measured them against a live
# showfile (progress.md §E.2 measurement 3): 2/6 roles matched, 0 ambiguous
# matches, 0 false positives — so the set entered M1 unadjusted.
ROLES: tuple[Role, ...] = (
    Role(
        name="백라이트",
        aliases=("back", "backlight"),
        hints=("Back", "Backlight", "BackLight", "Rear", "BL", "백", "백라이트", "뒤"),
        abbreviations=("BL",),
    ),
    Role(
        name="프론트",
        aliases=("front", "FOH"),
        hints=("Front", "FOH", "F.O.H", "FR", "프론트", "전면", "앞"),
        abbreviations=("FR",),
    ),
    Role(
        name="사이드",
        aliases=("side",),
        hints=("Side", "SL", "SR", "Wing", "사이드", "측면"),
        abbreviations=("SL", "SR"),
    ),
    Role(
        name="탑",
        aliases=("top", "downlight"),
        hints=("Top", "Down", "Downlight", "TP", "탑", "다운", "상부"),
        abbreviations=("TP",),
    ),
    Role(
        name="배경",
        aliases=("cyc", "backdrop"),
        hints=("Cyc", "Cyclorama", "Backdrop", "BD", "배경", "샤막", "호리"),
        abbreviations=("BD",),
    ),
    Role(
        name="스페셜",
        aliases=("special", "key"),
        hints=("Special", "Spc", "Key", "KeyLight", "스페셜", "키라이트"),
        abbreviations=("Spc",),
    ),
)

ROLE_NAMES = frozenset(role.name for role in ROLES)

_BY_NAME = {role.name: role for role in ROLES}


@dataclass(frozen=True)
class RoleNameMatch:
    """The outcome of matching one group name against the role hints.

    ``role`` is set only on an unambiguous single hit. Otherwise ``reason`` is
    ``ambiguous`` (two or more roles claimed the name) or ``no_match``, and
    ``candidates`` records what was seen so the caller can report it.
    """

    role: str | None
    reason: str | None
    candidates: tuple[str, ...]


def role_by_name(name: str) -> Role:
    """Return the role with this Korean primary name, or raise ``KeyError``."""
    return _BY_NAME[name]


def _strict_pattern(hint: str) -> re.Pattern[str]:
    """Hint must occupy a whole token (case-insensitive)."""
    return re.compile(f"(?<!{_WORD}){re.escape(hint)}(?!{_WORD})", re.IGNORECASE)


def _camel_pattern(hint: str) -> re.Pattern[str] | None:
    """Hint may also open or close a CamelCase hump (case-SENSITIVE).

    This is what makes ``FrontBack Truss`` report as ambiguous instead of
    matching nothing: a reader sees both words in it, so the matcher must too.
    The case sensitivity is the whole point — it is the capital letter that
    marks the hump — so this pass cannot be folded into the strict one.
    """
    left = f"(?<!{_WORD})"
    right = f"(?!{_WORD})"
    relaxed = False
    if hint[0].isascii() and hint[0].isupper():
        left = f"(?:(?<!{_WORD})|(?<=[a-z]))"
        relaxed = True
    if hint[-1].isascii() and hint[-1].islower():
        right = f"(?:(?!{_WORD})|(?=[A-Z]))"
        relaxed = True
    if not relaxed:
        return None
    return re.compile(left + re.escape(hint) + right)


# Abbreviations are matched by the strict pass only. `SP` was rejected as a
# hint for exactly this reason (it would prefix Spot-family names); `Spc`
# survives because nothing but the token itself can produce it.
_STRICT: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (role.name, _strict_pattern(hint)) for role in ROLES for hint in role.hints
)
_CAMEL: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (role.name, pattern)
    for role in ROLES
    for hint in role.hints
    if hint not in role.abbreviations
    for pattern in (_camel_pattern(hint),)
    if pattern is not None
)


# @MX:WARN: [AUTO] name-convention heuristic — a rig with no naming convention
#   maps zero roles, and that is correct behaviour, not a failure to paper over
# @MX:REASON: REQ-LOOKLIB-009 requires an explicit unmapped report; the danger
#   when extending these hints is inventing a group the rig never listed
#   (31_choreography_patterns.md:184-191). Widen hints only against measured
#   group names, and keep ambiguity reported rather than resolved by guess.
def match_role_by_name(group_name: str) -> RoleNameMatch:
    """Match one rig group name against the closed role vocabulary.

    A name claimed by two or more roles is reported as ``ambiguous`` and left
    unmapped — never assigned to whichever role happened to be checked first.
    """
    hit: list[str] = []
    for role_name, pattern in _STRICT:
        if role_name not in hit and pattern.search(group_name):
            hit.append(role_name)
    for role_name, pattern in _CAMEL:
        if role_name not in hit and pattern.search(group_name):
            hit.append(role_name)

    ordered = tuple(role.name for role in ROLES if role.name in hit)
    if len(ordered) == 1:
        return RoleNameMatch(role=ordered[0], reason=None, candidates=ordered)
    if not ordered:
        return RoleNameMatch(role=None, reason=NO_MATCH, candidates=())
    return RoleNameMatch(role=None, reason=AMBIGUOUS, candidates=ordered)
