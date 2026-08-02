"""Natural-language fx matching (REQ-FXLIB-006/007/008).

Two axes, both read from the library itself: the **pattern kind** and the
entry's own surface text (**display name**, **aliases**, **mood keywords**). No
embedding index and no new dependency — a closed set of six pattern kinds is a
size keyword matching handles outright, and it is the same shape
``server/looks/matching.py`` already proved on the look library.

The one surface table this layer adds is ``PATTERN_ALIASES``, and it exists for
a reason the library could not cover: the library's ``pattern`` field holds
ENGLISH slugs (``sweep`` / ``wave`` / ``circle`` / ``diagonal`` / ``pulse`` /
``chase``) because it is a machine axis paired with the English ``fx_id``, while
every operator-facing pattern name in spec.md §A is Korean (스윕 / 웨이브 /
서클 / 대각선 / 펄스 / 체이스). Nothing in the assets bridges the two, so a user
typing 웨이브 would match nothing at all. The bridge belongs HERE and not in the
assets: it is presentation vocabulary, the loader's schema is CLOSED (an alias
field would be a schema change rippling into the library assets and the bundle
builder), and REQ-FXLIB-002 makes Korean first-class at the surface, not in the
data. The bridge can only ever point INTO ``PATTERN_KINDS``; it can name no
pattern the schema does not have, and it can conjure no entry the library does
not carry — a pattern that resolves with no entry behind it is an honest miss.

Two shapes here differ deliberately from the looks original, and both tighten it:

``fallback_reason`` is set EXACTLY when ``selected`` is ``None``
    The looks matcher leaves a constrained tie with no reason and no selection,
    which is a mushy state for a caller to read. Here the two fields are one
    fact: a caller can trust either alone. Nothing is lost — a constrained miss
    still reports the whole band in ``matches``, it just does not pretend the
    band is an answer.

a lone entry in the named band IS selected
    The looks matcher refuses to select on a zero score, so naming only a genre
    never picks a look. With six pattern kinds, naming the pattern is the
    primary way an operator asks for an fx, and refusing to answer it would make
    the axis decorative.

# @MX:WARN: [AUTO] matching must never manufacture an fx — a query that hits
#   nothing returns a fallback signal, never the nearest neighbour
# @MX:REASON: REQ-FXLIB-008 degrades to the rulebook mood table
#   (31_choreography_patterns.md:236-241) precisely so the miss stays visible.
#   The tempting edits are all the same edit: lower the confidence bar, widen a
#   term to a substring, or return "the closest fx anyway" — each turns an
#   honest miss into a confident wrong answer (design.md AP-2). The cost is
#   higher on this SPEC than on looks: an fx's effect is NOT machine-readable
#   (M0 measured that a stored cue holding a phaser is indistinguishable from an
#   empty one), so a wrong-but-confident match reaches the stage as motion
#   nobody asked for and no runtime signal contradicts it.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from server.fx.schema import Fx, FxLibrary

__all__ = [
    "EMPTY_QUERY",
    "LOW_CONFIDENCE",
    "MAX_TOOL_MATCHES",
    "NO_MATCH",
    "PATTERN_ALIASES",
    "FxMatch",
    "FxScore",
    "match_fx",
    "resolve_pattern",
]

# Why a match was not made. Three reasons, kept apart because they are different
# facts and the operator can act on them differently.
EMPTY_QUERY = "empty_query"  # nothing was asked
NO_MATCH = "no_match"  # asked, and no fx answered
LOW_CONFIDENCE = "low_confidence"  # several answered equally, nothing narrows them

# Ceiling on how many matches a single tool result carries. The report says
# ``total`` and ``truncated`` alongside, so a cut list is never presented as a
# complete one (the get_rig_context ``drilldown_capped`` discipline).
MAX_TOOL_MATCHES = 8

PATTERN_ALIASES: Mapping[str, str] = {
    # Korean first. The axis words come straight from spec.md §A's pattern
    # table: sweep is the Pan (좌우) spread, wave the Tilt (상하) one.
    "스윕": "sweep",
    "쓸어": "sweep",
    "쓸기": "sweep",
    "좌우": "sweep",
    "웨이브": "wave",
    "파도": "wave",
    "물결": "wave",
    "상하": "wave",
    "서클": "circle",
    "원형": "circle",
    "발리후": "circle",
    "대각선": "diagonal",
    "대각": "diagonal",
    "사선": "diagonal",
    "펄스": "pulse",
    "점멸": "pulse",
    "깜빡": "pulse",
    "체이스": "chase",
    "체이싱": "chase",
    "색변화": "chase",
    # The slug itself must keep resolving: a model that read a pattern out of a
    # previous tool result will type it back verbatim.
    "sweep": "sweep",
    "wave": "wave",
    "circle": "circle",
    "ballyhoo": "circle",
    "diagonal": "diagonal",
    "pulse": "pulse",
    "chase": "chase",
}

# Word characters for boundary purposes. Hangul counts as a word character on
# purpose — Python's ``\b`` would happily find 웨이브 inside 웨이브펌 and `wave`
# inside `microwave`, because both sides are ``\w``.
_WORD = r"[0-9A-Za-zㄱ-ㆎ가-힣]"

# Korean is agglutinative: the operator writes `웨이브로 돌려줘`, not `웨이브`.
# A CLOSED list of particles is allowed to follow a term — closed, because the
# alternative (accepting any trailing syllables) is substring matching wearing a
# hat, and 웨이브 would swallow 웨이브펌. Longest forms first; the trailing
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

# Movement words are VERBS in the field ("좌우로 쓸어줘"), which the nominal
# particle list above cannot reach. A second CLOSED group covers the endings.
# Closed for the same reason and with the same cost of being wrong: an open
# ending rule would let 쓸어 swallow 쓸어담아.
#
# TWO shapes live here, and the difference is why the list is enumerated
# rather than derived:
#   * 주세요·줄래·줄까·다오·보자·줘·봐 attach to an 어/아 verb stem (쓸어 + 줘);
#   * 하는 is the adnominal of a 하다-verb and attaches to a NOUN stem
#     (웨이브 + 하는), added 2026-08-02 for the SCENE headline sentence.
# Adding one is a decision, not a pattern to extend — the exact length is
# pinned in `test_matching_endings_parity.py`.
_ENDINGS = (
    "주세요",
    "줄래",
    "줄까",
    "다오",
    "보자",
    "줘",
    "봐",
    "하는",
)

_SUFFIX = "(?:" + "|".join(_PARTICLES + _ENDINGS) + ")?"


@lru_cache(maxsize=2048)
def _term_pattern(term: str) -> re.Pattern[str]:
    """A term occupies whole tokens, optionally followed by one suffix."""
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(f"(?<!{_WORD}){body}{_SUFFIX}(?!{_WORD})", re.IGNORECASE)


def _normalise(text: str) -> str:
    # macOS hands over NFD Hangul often enough to matter, and NFD 웨이브 is a
    # different string from NFC 웨이브 to every regex here.
    return unicodedata.normalize("NFC", text)


def _found(term: str, query: str) -> bool:
    return _term_pattern(term).search(query) is not None


def resolve_pattern(query: str) -> str | None:
    """The single pattern kind this query names, or ``None``.

    Two patterns named is NOT half a constraint: the query is ambiguous on this
    axis, so the axis reports nothing and the keyword axis decides. That is the
    same discipline the looks resolver applies to a group name claimed by two
    roles — ambiguity is reported, never resolved by picking first.
    """
    text = _normalise(query)
    hits = {pattern for alias, pattern in PATTERN_ALIASES.items() if _found(alias, text)}
    return next(iter(hits)) if len(hits) == 1 else None


def _terms_of(fx: Fx) -> tuple[str, ...]:
    """The entry's matchable surface text, de-duplicated case-insensitively.

    A display name is usually also an alias; counting it twice would inflate
    that entry's score for no extra evidence. The pattern slug is in here as
    well as being a filter, so an English pattern word typed back from a
    previous tool result still scores rather than only narrowing.
    """
    seen: dict[str, str] = {}
    for raw in (fx.display_name, fx.pattern, *fx.aliases, *fx.mood_keywords):
        term = _normalise(raw)
        seen.setdefault(term.casefold(), term)
    return tuple(seen.values())


@dataclass(frozen=True)
class FxScore:
    """One fx and the evidence that put it in the result."""

    fx: Fx
    score: int
    matched: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "fx_id": self.fx.fx_id,
            "display_name": self.fx.display_name,
            "pattern": self.fx.pattern,
            "attributes": list(self.fx.attributes),
            "speed": self.fx.speed,
            "reverse": self.fx.reverse,
            "score": self.score,
            "matched": list(self.matched),
        }


@dataclass(frozen=True)
class FxMatch:
    """What the library had to say about one instruction.

    ``selected`` is set only when ONE entry outscored every other. ``matches``
    is what was seen — on a low-confidence result it is reported so the tie is
    visible, and it is NOT a selection: reading matches[0] as "the answer" is
    exactly the nearest-neighbour guess ``fallback_reason`` exists to prevent.
    """

    query: str
    pattern: str | None = None
    matches: tuple[FxScore, ...] = ()
    selected: Fx | None = None
    fallback_reason: str | None = None

    @property
    def fallback(self) -> bool:
        return self.fallback_reason is not None

    def to_dict(self, limit: int = MAX_TOOL_MATCHES) -> dict:
        shown = self.matches[:limit]
        return {
            "query": self.query,
            "pattern": self.pattern,
            "selected": self.selected.fx_id if self.selected is not None else None,
            "fallback": self.fallback,
            "fallback_reason": self.fallback_reason,
            "total": len(self.matches),
            "truncated": len(shown) < len(self.matches),
            "matches": [scored.to_dict() for scored in shown],
        }


def _ranked(scored: list[FxScore]) -> tuple[FxScore, ...]:
    # Score first, then the id — deterministic, so the same query never returns
    # two different orders and the library's own ordering cannot leak in.
    return tuple(sorted(scored, key=lambda s: (-s.score, s.fx.fx_id)))


def _unique_top(matches: tuple[FxScore, ...]) -> Fx | None:
    if not matches:
        return None
    if len(matches) > 1 and matches[1].score == matches[0].score:
        return None
    return matches[0].fx


def match_fx(query: str, library: FxLibrary) -> FxMatch:
    """Match one natural-language instruction against the fx library.

    Pure: the only inputs are the query and the library handed in, so the same
    pair always yields the same result, nothing is mutated, and no provider
    adapter is involved (REQ-FXLIB-021).
    """
    text = _normalise(query or "").strip()
    if not text:
        return FxMatch(query="", fallback_reason=EMPTY_QUERY)

    pattern = resolve_pattern(text)
    survivors = [fx for fx in library.fx if pattern is None or fx.pattern == pattern]

    scored = []
    for fx in survivors:
        matched = tuple(term for term in _terms_of(fx) if _found(term, text))
        if matched:
            scored.append(FxScore(fx=fx, score=len(matched), matched=matched))

    if scored:
        matches = _ranked(scored)
    elif pattern is not None:
        # The user named a pattern and no keyword landed. The band itself is
        # what was asked for, so it is reported — but it is reported as a band,
        # not as an answer: a band of two or more still selects nothing.
        matches = _ranked([FxScore(fx=fx, score=0, matched=()) for fx in survivors])
    else:
        matches = ()

    selected = _unique_top(matches)
    if not matches:
        reason: str | None = NO_MATCH
    elif selected is None:
        reason = LOW_CONFIDENCE
    else:
        reason = None

    return FxMatch(
        query=text,
        pattern=pattern,
        matches=matches,
        selected=selected,
        fallback_reason=reason,
    )
