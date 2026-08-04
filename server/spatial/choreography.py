"""Spatial choreography — a qualifier becomes a sort, a sort becomes an order
(SPEC-COPILOT-SPATIAL-001, REQ-SPATIAL-014 / REQ-SPATIAL-015).

Two pure operations, both downstream of the analysis layer:

**Qualifier matching.** A chat instruction carries a spatial qualifier
(`왼쪽에서 오른쪽`, `가운데부터 바깥으로`, `대각선`) and this module resolves it
onto the CLOSED four-name vocabulary of :data:`~server.spatial.SPATIAL_SORTS`.
The discipline is `server/looks/matching.py`'s, applied verbatim: a closed term
list, whole-token boundaries with Hangul counted as a word character, one
optional trailing 조사, NFC normalisation, and — the load-bearing rule — a query
that names two sorts returns ``None`` with a reason rather than the first hit.

**Utterance building.** A sorted chain of fids becomes the additive selection
line, and the live-validated two-step dimmer phaser rides on top of it. The
direction of the wave is carried by the ORDER of that chain and by nothing else.

Pure: the strings are built here, screened and sent elsewhere. No transport, no
gate, no third-party import (the package boundary, REQ-SPATIAL-013).

# @MX:WARN: [AUTO] no coordinate value may appear in ANY command this module
#   emits. The only numbers it writes are fids, the two dimmer levels, the step
#   index, the phase span and the phaser speed — every one of them an integer.
# @MX:REASON: REQ-SPATIAL-014 / AC-SPATIAL-014. M0 measured the premise live:
#   with the coordinates and the phaser grammar held IDENTICAL, reversing the
#   selection chain reversed the observed wave (progress.md §E.2.7). Direction
#   is therefore an ordering fact, not a value fact, and a coordinate reaching a
#   command line would be both meaningless to MA3 and — since the stage effect
#   is not machine-readable (spec.md §C.1) — invisible in every log.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache

from server.spatial.schema import SPATIAL_SORTS, SpatialAnalysis, SpatialAnalysisError
from server.spatial.sorting import spatial_sorted_fids

__all__ = [
    "SPATIAL_QUALIFIER_AMBIGUOUS",
    "SPATIAL_QUALIFIER_EMPTY",
    "SPATIAL_QUALIFIER_NO_MATCH",
    "SPATIAL_QUALIFIER_REASONS",
    "SPATIAL_WAVE_ATTRIBUTE",
    "SPATIAL_WAVE_DEFAULT_SPEED",
    "SPATIAL_WAVE_HIGH",
    "SPATIAL_WAVE_LOW",
    "SPATIAL_WAVE_PHASE_SPAN",
    "SpatialQualifierMatch",
    "build_spatial_selection_chain",
    "build_spatial_wave_commands",
    "match_spatial_qualifier",
    "resolve_spatial_sort",
]

# -- Why a qualifier did not resolve ------------------------------------------
#
# Three reasons, kept apart because the caller can act on them differently: an
# instruction with no spatial content at all is not the same event as one that
# named a direction the vocabulary has no sort for, and neither is the same as
# one that named two. Closed, for the reason `SPATIAL_LOW_CONFIDENCE_REASONS` is
# closed — a raw identifier reaching a user is the failure to avoid.
SPATIAL_QUALIFIER_EMPTY = "empty_query"  # nothing was asked
SPATIAL_QUALIFIER_NO_MATCH = "no_match"  # asked, and no sort answered
SPATIAL_QUALIFIER_AMBIGUOUS = "ambiguous"  # two sorts answered; nothing narrows them

SPATIAL_QUALIFIER_REASONS = frozenset(
    {SPATIAL_QUALIFIER_EMPTY, SPATIAL_QUALIFIER_NO_MATCH, SPATIAL_QUALIFIER_AMBIGUOUS}
)

# Word characters for boundary purposes. Hangul counts as a word character on
# purpose — Python's ``\b`` would find `좌` inside `좌측` and `우` inside `우선`,
# because both sides are ``\w`` (the trap `server/looks/matching.py:133` names).
_WORD = r"[0-9A-Za-zㄱ-ㆎ가-힣]"

# Korean is agglutinative: the operator writes `대각선으로 돌려`, not `대각선`. A
# CLOSED list of particles may follow a term — closed, because accepting any
# trailing syllables is substring matching wearing a hat. Longest forms first;
# the trailing boundary assertion rejects a wrong pick and forces a retry.
_PARTICLES = (
    "에서부터",
    "으로부터",
    "쪽으로",
    "로부터",
    "이라는",
    "으로",
    "에서",
    "까지",
    "부터",
    "처럼",
    "같이",
    "이나",
    "라는",
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

# The particles that mark a STARTING point rather than any old grammatical role.
# This is the whole reason the matcher is robust against `오른쪽 무버를 왼쪽에서
# 오른쪽으로`: the leading `오른쪽` carries an object particle, not an origin one,
# so it names a target and not the end the wave starts from. Longest first.
_ORIGIN_PARTICLES = ("에서부터", "으로부터", "로부터", "에서", "부터")
_ORIGIN_MARKER = "(?:" + "|".join(_ORIGIN_PARTICLES) + ")"

# The four ends of a stage axis. Internal kinds, never surfaced — the closed
# vocabulary a caller sees is SPATIAL_SORTS.
_LEFT = "left"
_RIGHT = "right"
_CENTER = "center"
_OUTWARD = "outward"

# Endpoint surface words. Closed, and deliberately narrow: `라이트` is omitted
# because it is also 조명, and a bare `안` is omitted because it is one syllable
# away from half the language. Every entry here is unambiguously positional.
_ENDPOINT_TERMS: Mapping[str, str] = {
    "왼쪽": _LEFT,
    "왼편": _LEFT,
    "좌측": _LEFT,
    "좌": _LEFT,
    "오른쪽": _RIGHT,
    "오른편": _RIGHT,
    "우측": _RIGHT,
    "우": _RIGHT,
    "가운데": _CENTER,
    "중앙": _CENTER,
    "중심": _CENTER,
    "센터": _CENTER,
    "안쪽": _CENTER,
    "바깥": _OUTWARD,
    "바깥쪽": _OUTWARD,
    "외곽": _OUTWARD,
    "가장자리": _OUTWARD,
    "양옆": _OUTWARD,
    "양쪽": _OUTWARD,
}

# An (origin, destination) pair, and the ONE sort it names. Three rows, because
# the vocabulary has three directed sorts; `diagonal` is not directed and lives
# in the standalone table below.
#
# What is absent is as deliberate as what is present: `(outward, center)` —
# `바깥에서 가운데로` — has no row, so an outside-in instruction resolves to
# nothing at all rather than to its mirror image. Inventing a mapping is exactly
# what REQ-SPATIAL-015 forbids.
_DIRECTED_SORTS: Mapping[tuple[str, str], str] = {
    (_LEFT, _RIGHT): "left_to_right",
    (_RIGHT, _LEFT): "right_to_left",
    (_CENTER, _OUTWARD): "center_out",
}

# The destination an origin implies when the instruction names only where the
# wave STARTS (`왼쪽에서 웨이브`). `outward` is absent for the same reason it is
# absent above.
_IMPLIED_DESTINATION: Mapping[str, str] = {
    _LEFT: _RIGHT,
    _RIGHT: _LEFT,
    _CENTER: _OUTWARD,
}

# Terms that name a sort on their own, with no endpoint pair to read. The
# canonical sort names are included so the vocabulary answers to itself.
_STANDALONE_TERMS: Mapping[str, str] = {
    "대각선": "diagonal",
    "대각": "diagonal",
    "사선": "diagonal",
    "diagonal": "diagonal",
    "left to right": "left_to_right",
    "left-to-right": "left_to_right",
    "left_to_right": "left_to_right",
    "right to left": "right_to_left",
    "right-to-left": "right_to_left",
    "right_to_left": "right_to_left",
    "center out": "center_out",
    "centre out": "center_out",
    "center-out": "center_out",
    "center_out": "center_out",
}


@lru_cache(maxsize=512)
def _term_pattern(term: str) -> re.Pattern[str]:
    """A term occupies whole tokens, optionally followed by one particle."""
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(f"(?<!{_WORD}){body}{_PARTICLE}(?!{_WORD})", re.IGNORECASE)


@lru_cache(maxsize=512)
def _origin_pattern(term: str) -> re.Pattern[str]:
    """A term carrying an origin particle — `왼쪽에서`, `가운데부터`.

    The origin particle is MANDATORY here, which is what separates "the end the
    wave starts from" out of every other mention of the word.
    """
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(f"(?<!{_WORD}){body}{_ORIGIN_MARKER}{_PARTICLE}(?!{_WORD})", re.IGNORECASE)


def _normalise(text: str) -> str:
    # macOS hands over NFD Hangul often enough to matter, and NFD `왼쪽` is a
    # different string from NFC `왼쪽` to every regex here.
    return unicodedata.normalize("NFC", text)


def _found(term: str, text: str) -> bool:
    return _term_pattern(term).search(text) is not None


def _origin_found(term: str, text: str) -> bool:
    return _origin_pattern(term).search(text) is not None


@dataclass(frozen=True)
class SpatialQualifierMatch:
    """What one instruction had to say about spatial order.

    ``sort`` is set only when the text named EXACTLY ONE of the four. Otherwise
    it is ``None`` and ``reason`` says which of the three misses happened, with
    ``candidates`` recording what was seen so an ambiguous instruction can be
    reported back rather than resolved by picking first — the discipline
    `server/looks/roles.py` applies to a group name claimed by two roles.
    """

    sort: str | None
    reason: str | None
    candidates: tuple[str, ...] = ()


def _named_sorts(text: str) -> set[str]:
    """Every sort this text names — by a standalone term or an endpoint pair."""
    named = {sort for term, sort in _STANDALONE_TERMS.items() if _found(term, text)}

    mentioned = {kind for term, kind in _ENDPOINT_TERMS.items() if _found(term, text)}
    origins = {kind for term, kind in _ENDPOINT_TERMS.items() if _origin_found(term, text)}

    for origin in origins:
        others = mentioned - {origin}
        if not others:
            destination = _IMPLIED_DESTINATION.get(origin)
        elif len(others) == 1:
            destination = next(iter(others))
        else:
            # Three or more ends of the axis named at once: which pair the
            # operator meant is not readable from the text, so this origin
            # contributes nothing rather than a guess.
            continue
        if destination is None:
            continue
        sort = _DIRECTED_SORTS.get((origin, destination))
        if sort is not None:
            named.add(sort)
    return named


# @MX:WARN: [AUTO] a query naming two sorts returns None — never the first hit,
#   never the "closest" one.
# @MX:REASON: REQ-SPATIAL-015 / AC-SPATIAL-015. The stage effect of a selection
#   order has no machine channel (spec.md §C.1), so a wrong-but-plausible pick
#   executes silently and looks correct in every log. The tempting edits are all
#   the same edit — rank the candidates, prefer the longest term, take
#   ``candidates[0]`` — and each turns an honest miss into a confident wrong
#   answer (`server/looks/matching.py` AP-2).
def match_spatial_qualifier(query: str) -> SpatialQualifierMatch:
    """Resolve one instruction's spatial qualifier onto the closed sort vocabulary.

    Pure: the query is the only input, so the same wording always resolves the
    same way.
    """
    text = _normalise(query)
    if not text.strip():
        return SpatialQualifierMatch(sort=None, reason=SPATIAL_QUALIFIER_EMPTY)

    named = _named_sorts(text)
    # Canonical order, so a reported ambiguity reads the same way every time.
    candidates = tuple(sort for sort in SPATIAL_SORTS if sort in named)
    if not candidates:
        return SpatialQualifierMatch(sort=None, reason=SPATIAL_QUALIFIER_NO_MATCH)
    if len(candidates) > 1:
        return SpatialQualifierMatch(
            sort=None, reason=SPATIAL_QUALIFIER_AMBIGUOUS, candidates=candidates
        )
    return SpatialQualifierMatch(sort=candidates[0], reason=None, candidates=candidates)


def resolve_spatial_sort(query: str) -> str | None:
    """The single sort this query names, or ``None`` (the `resolve_genre` shape)."""
    return match_spatial_qualifier(query).sort


# -- The utterance ------------------------------------------------------------
#
# Every literal below was executed against onPC 2.4.2 and observed on stage in
# M0 P8 (progress.md §E.2.7). None of it is inferred from documentation.

#: The one attribute the wave rides on. M0 observed a dimmer wave; Pan/Tilt
#: phasers are validated grammar (31_choreography_patterns.md:61-80) but were
#: not observed on a spatially sorted chain, so they are not offered here.
SPATIAL_WAVE_ATTRIBUTE = "Dimmer"

#: The two phaser steps. A phaser fans phase ACROSS steps, so one static value
#: has nothing to fan: M0 emitted `At 100` + `At Phase 0 Thru 360`, every line
#: answered ok, and the stage stood still (progress.md §E.2.7). Two steps is not
#: a stylistic choice — it is the difference between motion and none.
SPATIAL_WAVE_LOW = 0
SPATIAL_WAVE_HIGH = 100

#: One full wave spread across the selection, in selection order.
SPATIAL_WAVE_PHASE_SPAN = "0 Thru 360"

#: The rate M0 ran the observed wave at.
SPATIAL_WAVE_DEFAULT_SPEED = 30


def build_spatial_selection_chain(fids: Iterable[int]) -> str:
    """The additive selection line — `Fixture a + Fixture b + ...`.

    The chain IS the direction (progress.md §E.2.7). Reversing it reverses the
    wave, which is why the fid order must arrive already sorted and must not be
    re-sorted, de-duplicated or normalised on the way out.
    """
    chain = tuple(fids)
    if not chain:
        raise SpatialAnalysisError("a selection chain needs at least one fixture")
    return " + ".join(f"Fixture {fid}" for fid in chain)


def build_spatial_wave_commands(
    analysis: SpatialAnalysis,
    sort: str,
    *,
    speed: int = SPATIAL_WAVE_DEFAULT_SPEED,
) -> tuple[str, ...]:
    """Compile one spatial wave: sort the rig, select in that order, phase it.

    ``sort`` must be one of :data:`~server.spatial.SPATIAL_SORTS`;
    ``spatial_sorted_fids`` raises on anything else rather than falling back to
    a default order.

    Works on a low-confidence analysis — the one-row fallback is a real row and
    still yields a chain. Whether to USE the result is the caller's call, made
    against ``analysis.low_confidence`` (REQ-SPATIAL-012).

    Single quotes around the attribute name are the transport's only option:
    `server/bridge/protocol.py` rejects the double-quote character outright, so
    the MA3-documentation habit of `Attribute "Dimmer"` cannot be sent at all
    (progress.md §E.2.6a).
    """
    if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
        raise SpatialAnalysisError(f"phaser speed must be a positive integer, got {speed!r}")
    chain = build_spatial_selection_chain(spatial_sorted_fids(analysis, sort))
    attribute = SPATIAL_WAVE_ATTRIBUTE
    return (
        # Programming context. Fixture selection returns "Illegal object" while
        # the command line still points at the Patch editor
        # (31_choreography_patterns.md:9-23).
        "ChangeDestination Root",
        "ClearAll",
        chain,
        f"Attribute '{attribute}' At {SPATIAL_WAVE_LOW}",
        "Step 2",
        f"Attribute '{attribute}' At {SPATIAL_WAVE_HIGH}",
        f"Attribute '{attribute}' At Phase {SPATIAL_WAVE_PHASE_SPAN}",
        f"Attribute '{attribute}' At Speed {speed}",
        "ClearAll",
    )
