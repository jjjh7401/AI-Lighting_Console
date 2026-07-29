"""Natural-language look matching (REQ-LOOKLIB-015..018).

Four axes, all read from the library itself: **genre**, **section dynamics**,
**mood keywords** and **aliases** (the display name counts as an alias). No
embedding index and no new dependency — 32 looks is a size keyword matching
handles outright (research.md §7 rejection (b)).

The two surface tables below are the only place this layer adds vocabulary of
its own, and each exists for a reason the library could not cover:

``GENRE_ALIASES``
    The library's ``genre`` field holds ENGLISH slugs (``worship`` / ``rock`` /
    ``ballad`` / ``edm``) because it is a machine axis paired with the English
    ``look_id``. Every operator-facing genre name in spec.md §A is Korean
    (워십 / 록 / 발라드 / EDM). Nothing in the assets bridges the two, so a user
    typing 워십 would match nothing at all. The bridge belongs HERE and not in
    the assets: it is presentation vocabulary, the loader's schema is closed
    (an alias field would be a schema change rippling into P1-1/P1-2), and
    REQ-LOOKLIB-018 makes Korean first-class at the surface, not in the data.

``DYNAMICS_TERMS``
    Song-section words map onto the 1..5 dynamics scale of spec.md §A
    (1 static/ambient · 2 calm · 3 build · 4 lift · 5 climax). Bands are
    deliberately WIDE where the SPEC's own label spans two levels: this table
    FILTERS, and an over-narrow filter drops a good look silently, which is the
    failure direction this SPEC keeps refusing.

# @MX:WARN: [AUTO] matching must never manufacture a look — a query that hits
#   nothing returns a fallback signal, never the nearest neighbour
# @MX:REASON: REQ-LOOKLIB-017 degrades to the rulebook mood section
#   (31_choreography_patterns.md:173-206) precisely so the miss stays visible.
#   The tempting edits are all the same edit: lower the confidence bar, widen a
#   term to a substring, or return "the closest look anyway" — each turns an
#   honest miss into a confident wrong answer (design.md AP-2).
"""

from __future__ import annotations


import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from server.looks.schema import Look, LookLibrary

__all__ = [
    "DYNAMICS_TERMS",
    "EMPTY_QUERY",
    "GENRE_ALIASES",
    "LOW_CONFIDENCE",
    "MAX_TOOL_MATCHES",
    "NO_MATCH",
    "LookMatch",
    "LookScore",
    "match_looks",
    "resolve_dynamics",
    "resolve_genre",
]

# Why a match was not made. Three reasons, kept apart for the same purpose the
# resolver keeps its five unmapped reasons apart: they are different facts and
# the operator can act on them differently.
EMPTY_QUERY = "empty_query"  # nothing was asked
NO_MATCH = "no_match"  # asked, and no look answered
LOW_CONFIDENCE = "low_confidence"  # several looks answered equally, nothing narrows them

# Ceiling on how many matches a single tool result carries. The report says
# ``total`` and ``truncated`` alongside, so a cut list is never presented as a
# complete one (the get_rig_context ``drilldown_capped`` discipline).
MAX_TOOL_MATCHES = 8

GENRE_ALIASES: Mapping[str, str] = {
    # Korean first (REQ-LOOKLIB-018). 예배 / 찬양 are the ordinary field words
    # for the service and for praise; 록 and 락 are both standard Korean
    # transliterations of "rock".
    "워십": "worship",
    "예배": "worship",
    "찬양": "worship",
    "록": "rock",
    "락": "rock",
    "발라드": "ballad",
    "이디엠": "edm",
    # The slug itself must keep resolving: a model that read a genre out of a
    # previous tool result will type it back verbatim.
    "worship": "worship",
    "rock": "rock",
    "ballad": "ballad",
    "edm": "edm",
}

DYNAMICS_TERMS: Mapping[str, tuple[int, ...]] = {
    # 1 — static / ambient
    "앰비언트": (1,),
    "ambient": (1,),
    "정적": (1,),
    "암전": (1,),
    # 1-2 — the room before, and the opening
    "인트로": (1, 2),
    "intro": (1, 2),
    "도입": (1, 2),
    # 2-3 — verse into the first lift
    "벌스": (2, 3),
    "verse": (2, 3),
    # 3 — the build
    "빌드업": (3,),
    "빌드": (3,),
    "build": (3,),
    "buildup": (3,),
    "프리코러스": (3,),
    "prechorus": (3,),
    "라이저": (3,),
    "riser": (3,),
    # 4-5 — lift and climax. spec.md §A puts 코러스 at 4 and 드랍/엔딩 at 5, but
    # the library authored an EDM drop at 4 (``edm-drop-acid``), so a
    # single-level band here would hide a look the user plainly asked for.
    "코러스": (4, 5),
    "chorus": (4, 5),
    "후렴": (4, 5),
    "고조": (4, 5),
    "드랍": (4, 5),
    "drop": (4, 5),
    "클라이맥스": (4, 5),
    "climax": (4, 5),
    "절정": (4, 5),
    "최고조": (4, 5),
    "엔딩": (4, 5),
    "ending": (4, 5),
    "피날레": (4, 5),
    "finale": (4, 5),
}

# Word characters for boundary purposes. Hangul counts as a word character on
# purpose — Python's ``\b`` would happily find `밤` inside `밤하늘` and `록`
# inside `블록`, because both sides are ``\w`` (the same trap roles.py hit with
# `백` inside `백색`).
_WORD = r"[0-9A-Za-zㄱ-ㆎ가-힣]"

# Korean is agglutinative: the operator writes `코러스로 가자`, not `코러스`.
# A CLOSED list of particles is allowed to follow a term — closed, because the
# alternative (accepting any trailing syllables) is substring matching wearing a
# hat, and `밤` would swallow `밤하늘` again. Longest forms first; the trailing
# boundary assertion rejects a wrong pick and forces the engine to retry.
_PARTICLES = (
    "으로써",
    "으로서",
    "이라는",
    "으로",
    "에서",
    "에게",
    "까지",
    "부터",
    "처럼",
    "같이",
    "이랑",
    "라는",
    # The alternation connective, in both forms: `워십이나 발라드`, `록이나 EDM`.
    # Same family as 와 / 과 / 랑 below, and it was missing until a two-genre
    # test went looking for it.
    "이나",
    "나",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "로",
    "에",
    "도",
    "만",
    "와",
    "과",
    "랑",
)
_PARTICLE = "(?:" + "|".join(_PARTICLES) + ")?"


@lru_cache(maxsize=2048)
def _term_pattern(term: str) -> re.Pattern[str]:
    """A term occupies whole tokens, optionally followed by one particle."""
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(f"(?<!{_WORD}){body}{_PARTICLE}(?!{_WORD})", re.IGNORECASE)


def _normalise(text: str) -> str:
    # macOS hands over NFD Hangul often enough to matter, and NFD `코러스` is a
    # different string from NFC `코러스` to every regex here.
    return unicodedata.normalize("NFC", text)


def _found(term: str, query: str) -> bool:
    return _term_pattern(term).search(query) is not None


def resolve_genre(query: str) -> str | None:
    """The single genre this query names, or ``None``.

    Two genres named is NOT half a constraint: the query is ambiguous on this
    axis, so the axis reports nothing and the mood axis decides. That is the
    same discipline roles.py applies to a group name claimed by two roles —
    ambiguity is reported, never resolved by picking first.
    """
    text = _normalise(query)
    hits = {genre for alias, genre in GENRE_ALIASES.items() if _found(alias, text)}
    return next(iter(hits)) if len(hits) == 1 else None


def resolve_dynamics(query: str) -> tuple[int, ...] | None:
    """The dynamics band this query names, or ``None``.

    Several section words UNION their bands, because a band is already a range
    and widening one is the fail-open direction.
    """
    text = _normalise(query)
    levels: set[int] = set()
    for term, band in DYNAMICS_TERMS.items():
        if _found(term, text):
            levels.update(band)
    return tuple(sorted(levels)) if levels else None


def _terms_of(look: Look) -> tuple[str, ...]:
    """The look's matchable surface text, de-duplicated case-insensitively.

    A display name is usually also an alias; counting it twice would inflate
    that look's score for no extra evidence.
    """
    seen: dict[str, str] = {}
    for raw in (look.display_name, *look.aliases, *look.mood_keywords):
        term = _normalise(raw)
        seen.setdefault(term.casefold(), term)
    return tuple(seen.values())


@dataclass(frozen=True)
class LookScore:
    """One look and the evidence that put it in the result."""

    look: Look
    score: int
    matched: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "look_id": self.look.look_id,
            "display_name": self.look.display_name,
            "genre": self.look.genre,
            "dynamics": self.look.dynamics,
            "roles": list(self.look.roles),
            "attributes": {value.name: value.value for value in self.look.attributes},
            "score": self.score,
            "matched": list(self.matched),
        }


@dataclass(frozen=True)
class LookMatch:
    """What the library had to say about one instruction.

    ``selected`` is set only when ONE look outscored every other. ``matches``
    is what was seen — on a low-confidence result it is reported so the tie is
    visible, and it is NOT a selection: reading matches[0] as "the answer" is
    exactly the nearest-neighbour guess ``fallback_reason`` exists to prevent.
    """

    query: str
    genre: str | None = None
    dynamics: tuple[int, ...] = ()
    matches: tuple[LookScore, ...] = ()
    selected: Look | None = None
    fallback_reason: str | None = None

    @property
    def fallback(self) -> bool:
        return self.fallback_reason is not None

    def to_dict(self, limit: int = MAX_TOOL_MATCHES) -> dict:
        shown = self.matches[:limit]
        return {
            "query": self.query,
            "genre": self.genre,
            "dynamics": list(self.dynamics),
            "selected": self.selected.look_id if self.selected is not None else None,
            "fallback": self.fallback,
            "fallback_reason": self.fallback_reason,
            "total": len(self.matches),
            "truncated": len(shown) < len(self.matches),
            "matches": [scored.to_dict() for scored in shown],
        }


def _ranked(scored: list[LookScore]) -> tuple[LookScore, ...]:
    # Score first, then the quieter look, then the id — deterministic, so the
    # same query never returns two different orders.
    return tuple(sorted(scored, key=lambda s: (-s.score, s.look.dynamics, s.look.look_id)))


def _unique_top(matches: tuple[LookScore, ...]) -> Look | None:
    if not matches or matches[0].score == 0:
        return None
    if len(matches) > 1 and matches[1].score == matches[0].score:
        return None
    return matches[0].look


def match_looks(query: str, library: LookLibrary) -> LookMatch:
    """Match one natural-language instruction against the look library.

    Pure: the only inputs are the query and the library handed in, so the same
    pair always yields the same result and no provider adapter is involved
    (AC-LOOKLIB-017).
    """
    text = _normalise(query or "").strip()
    if not text:
        return LookMatch(query="", fallback_reason=EMPTY_QUERY)

    genre = resolve_genre(text)
    dynamics = resolve_dynamics(text) or ()
    constrained = genre is not None or bool(dynamics)

    survivors = [
        look
        for look in library.looks
        if (genre is None or look.genre == genre) and (not dynamics or look.dynamics in dynamics)
    ]

    scored = []
    for look in survivors:
        matched = tuple(term for term in _terms_of(look) if _found(term, text))
        if matched:
            scored.append(LookScore(look=look, score=len(matched), matched=matched))

    if scored:
        matches = _ranked(scored)
    elif constrained:
        # The user named a genre or a section and no keyword landed. The band
        # itself is the answer — returning it is not a guess, it is what was
        # asked for (AC-LOOKLIB-010's "기대 장르·다이내믹스 대역의 룩").
        matches = _ranked([LookScore(look=look, score=0, matched=()) for look in survivors])
    else:
        matches = ()

    selected = _unique_top(matches)
    if not matches:
        reason: str | None = NO_MATCH
    elif selected is None and not constrained:
        reason = LOW_CONFIDENCE
    else:
        reason = None

    return LookMatch(
        query=text,
        genre=genre,
        dynamics=dynamics,
        matches=matches,
        selected=selected,
        fallback_reason=reason,
    )
