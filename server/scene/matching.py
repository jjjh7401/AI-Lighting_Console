"""Two-axis scene matching for REQ-SCENE-007/008/009.

The matcher splits one instruction into look and fx axes, applies the same
natural-language discipline as the upstream surfaces, and reports which axes
were resolved (both, look only, fx only, or neither) SEPARATELY from whether a
scene can actually be acted on. Those are two different facts: an instruction
can resolve both axes and still name no scene, because the library may carry no
entry composing exactly that pair. ``fallback`` therefore means "there is
nothing here to compile", never "no axis matched" — see ``SceneMatch.fallback``.
The rules are Korean suffix handling, four fallback facts, ties select None, and
deterministic ordering.

``match_scene`` receives a ``SceneLibrary``, not an ``FxLibrary``, so fx pattern
vocabulary is inferred from ``fx_id`` tokens plus the public
``server.fx.matching.PATTERN_ALIASES`` table. That inference is intentionally
guarded in ``test_scene_matching.py`` against today's shipped fx assets.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from server.fx.matching import PATTERN_ALIASES
from server.scene.schema import Scene, SceneLibrary

__all__ = [
    "AMBIGUOUS",
    "BOTH_MATCHED",
    "EMPTY_QUERY",
    "FALLBACK",
    "FX_ONLY",
    "LOOK_ONLY",
    "LOW_CONFIDENCE",
    "MAX_TOOL_MATCHES",
    "NO_MATCH",
    "NO_SCENE_COMPOSES_AXES",
    "AxisMatch",
    "AxisScore",
    "SceneMatch",
    "SceneScore",
    "match_scene",
]

EMPTY_QUERY = "empty_query"
NO_MATCH = "no_match"
LOW_CONFIDENCE = "low_confidence"
AMBIGUOUS = "ambiguous"
# The fifth fact, and the only one that is not about the axes: the axes DID
# resolve, but no scene in the library composes them. Kept apart from NO_MATCH
# because the repair differs — nothing is wrong with the instruction, the
# library simply has no entry, and the resolved axis ids are still worth
# reporting so the operator can reach for `find_looks`/`find_fx` instead.
NO_SCENE_COMPOSES_AXES = "no_scene_composes_axes"

BOTH_MATCHED = "both_matched"
LOOK_ONLY = "look_only"
FX_ONLY = "fx_only"
FALLBACK = "fallback"

MAX_TOOL_MATCHES = 8

_WORD = r"[0-9A-Za-zㄱ-ㆎ가-힣]"
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

_PATTERN_SLUGS = frozenset(PATTERN_ALIASES.values())


@dataclass(frozen=True)
class AxisScore:
    axis_id: str
    score: int
    matched: tuple[str, ...]
    scenes: tuple[Scene, ...]

    def to_dict(self) -> dict:
        return {
            "axis_id": self.axis_id,
            "score": self.score,
            "matched": list(self.matched),
            "scenes": [scene.scene_id for scene in self.scenes],
        }


@dataclass(frozen=True)
class AxisMatch:
    axis: str
    query: str
    matches: tuple[AxisScore, ...] = ()
    selected: str | None = None
    fallback_reason: str | None = None

    @property
    def fallback(self) -> bool:
        return self.fallback_reason is not None

    def to_dict(self, limit: int = MAX_TOOL_MATCHES) -> dict:
        shown = self.matches[:limit]
        return {
            "axis": self.axis,
            "query": self.query,
            "selected": self.selected,
            "fallback": self.fallback,
            "fallback_reason": self.fallback_reason,
            "total": len(self.matches),
            "truncated": len(shown) < len(self.matches),
            "matches": [scored.to_dict() for scored in shown],
        }


@dataclass(frozen=True)
class SceneScore:
    scene: Scene
    score: int
    matched_axes: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene.scene_id,
            "display_name": self.scene.display_name,
            "label": self.scene.label,
            "look_id": self.scene.look_id,
            "fx_id": self.scene.fx_id,
            "score": self.score,
            "matched_axes": list(self.matched_axes),
        }


@dataclass(frozen=True)
class SceneMatch:
    query: str
    kind: str
    look: AxisMatch
    fx: AxisMatch
    matches: tuple[SceneScore, ...] = ()
    selected: Scene | None = None
    fallback_reason: str | None = None

    @property
    def fallback(self) -> bool:
        # Deliberately the SAME definition `AxisMatch.fallback` already uses —
        # a reason is present. It used to read `self.kind == FALLBACK`, and that
        # divergence was the defect: when both axes resolved but the library
        # composed no scene for them, `kind` said `both_matched`, `fallback`
        # said False and `selected` was None. That is the success shape with
        # nothing in it — the model is told to pass a `scene_id` that is not in
        # the payload, and its only remaining move is to hand-write
        # `run_commands`, the exact failure this SPEC exists to prevent.
        # `kind` still reports WHICH AXES resolved; this reports whether there
        # is anything to act on. Found by independent pre-merge review.
        return self.fallback_reason is not None

    @property
    def partial(self) -> bool:
        return self.kind in {LOOK_ONLY, FX_ONLY}

    def to_dict(self, limit: int = MAX_TOOL_MATCHES) -> dict:
        shown = self.matches[:limit]
        return {
            "query": self.query,
            "kind": self.kind,
            "selected": self.selected.scene_id if self.selected is not None else None,
            "selected_look_id": self.look.selected
            if self.kind in {BOTH_MATCHED, LOOK_ONLY}
            else None,
            "selected_fx_id": self.fx.selected if self.kind in {BOTH_MATCHED, FX_ONLY} else None,
            "fallback": self.fallback,
            "fallback_reason": self.fallback_reason,
            "partial": self.partial,
            "look": self.look.to_dict(limit=limit),
            "fx": self.fx.to_dict(limit=limit),
            "total": len(self.matches),
            "truncated": len(shown) < len(self.matches),
            "matches": [scored.to_dict() for scored in shown],
        }


@lru_cache(maxsize=2048)
def _term_pattern(term: str) -> re.Pattern[str]:
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(f"(?<!{_WORD}){body}{_SUFFIX}(?!{_WORD})", re.IGNORECASE)


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _found(term: str, query: str) -> bool:
    return _term_pattern(term).search(query) is not None


def _unique_terms(raw_terms: tuple[str, ...]) -> tuple[str, ...]:
    seen: dict[str, str] = {}
    for raw in raw_terms:
        term = _normalise(raw).strip()
        if term:
            seen.setdefault(term.casefold(), term)
    return tuple(seen.values())


def _fx_pattern_terms(fx_id: str) -> tuple[str, ...]:
    tokens = frozenset(re.split(r"[-_\s]+", fx_id.casefold()))
    slugs = _PATTERN_SLUGS & tokens
    return tuple(alias for alias, slug in PATTERN_ALIASES.items() if slug in slugs)


def _terms_for(scene: Scene, axis: str, axis_id: str) -> tuple[str, ...]:
    common = (scene.display_name, *scene.aliases, *scene.mood_keywords, axis_id)
    if axis == "fx":
        return _unique_terms((*common, *_fx_pattern_terms(axis_id)))
    return _unique_terms(common)


def _classify_tie(top: tuple[AxisScore, ...]) -> str:
    common = set(top[0].matched)
    union = set(top[0].matched)
    for scored in top[1:]:
        terms = set(scored.matched)
        common &= terms
        union |= terms
    if union - common:
        return AMBIGUOUS
    return LOW_CONFIDENCE


def _rank_axis(scored: list[AxisScore]) -> tuple[AxisScore, ...]:
    return tuple(sorted(scored, key=lambda score: (-score.score, score.axis_id)))


def _match_axis(query: str, library: SceneLibrary, axis: str) -> AxisMatch:
    text = _normalise(query or "").strip()
    if not text:
        return AxisMatch(axis=axis, query="", fallback_reason=EMPTY_QUERY)

    matched_terms: dict[str, dict[str, str]] = defaultdict(dict)
    axis_scenes: dict[str, dict[str, Scene]] = defaultdict(dict)
    field_name = f"{axis}_id"

    for scene in sorted(library.scenes, key=lambda entry: entry.scene_id):
        axis_id = getattr(scene, field_name)
        if axis_id is None:
            continue
        axis_scenes[axis_id][scene.scene_id] = scene
        for term in _terms_for(scene, axis, axis_id):
            if _found(term, text):
                matched_terms[axis_id].setdefault(term.casefold(), term)

    matches = _rank_axis(
        [
            AxisScore(
                axis_id=axis_id,
                score=len(terms),
                matched=tuple(terms.values()),
                scenes=tuple(axis_scenes[axis_id][key] for key in sorted(axis_scenes[axis_id])),
            )
            for axis_id, terms in matched_terms.items()
        ]
    )
    if not matches:
        return AxisMatch(axis=axis, query=text, fallback_reason=NO_MATCH)

    top_score = matches[0].score
    top = tuple(scored for scored in matches if scored.score == top_score)
    if len(top) == 1:
        return AxisMatch(axis=axis, query=text, matches=matches, selected=top[0].axis_id)

    return AxisMatch(
        axis=axis,
        query=text,
        matches=matches,
        fallback_reason=_classify_tie(top),
    )


def _axis_score(axis_match: AxisMatch, axis_id: str | None) -> int:
    if axis_id is None:
        return 0
    for scored in axis_match.matches:
        if scored.axis_id == axis_id:
            return scored.score
    return 0


def _scene_scores(
    library: SceneLibrary, look: AxisMatch, fx: AxisMatch, kind: str
) -> tuple[SceneScore, ...]:
    scored: list[SceneScore] = []
    for scene in library.scenes:
        matched_axes: list[str] = []
        if kind == BOTH_MATCHED:
            if scene.look_id != look.selected or scene.fx_id != fx.selected:
                continue
            matched_axes = ["look", "fx"]
        elif kind == LOOK_ONLY:
            if scene.look_id != look.selected or scene.fx_id is not None:
                continue
            matched_axes = ["look"]
        elif kind == FX_ONLY:
            if scene.fx_id != fx.selected or scene.look_id is not None:
                continue
            matched_axes = ["fx"]
        else:
            continue
        scored.append(
            SceneScore(
                scene=scene,
                score=_axis_score(look, scene.look_id) + _axis_score(fx, scene.fx_id),
                matched_axes=tuple(matched_axes),
            )
        )
    return tuple(sorted(scored, key=lambda score: (-score.score, score.scene.scene_id)))


def _fallback_reason(look: AxisMatch, fx: AxisMatch) -> str:
    reasons = (look.fallback_reason, fx.fallback_reason)
    if EMPTY_QUERY in reasons:
        return EMPTY_QUERY
    if AMBIGUOUS in reasons:
        return AMBIGUOUS
    if LOW_CONFIDENCE in reasons:
        return LOW_CONFIDENCE
    return NO_MATCH


def match_scene(query: str, library: SceneLibrary) -> SceneMatch:
    text = _normalise(query or "").strip()
    look = _match_axis(text, library, "look")
    fx = _match_axis(text, library, "fx")

    if look.selected is not None and fx.selected is not None:
        kind = BOTH_MATCHED
    elif look.selected is not None:
        kind = LOOK_ONLY
    elif fx.selected is not None:
        kind = FX_ONLY
    else:
        kind = FALLBACK

    matches = _scene_scores(library, look, fx, kind)
    selected = matches[0].scene if matches else None
    if kind == FALLBACK:
        reason: str | None = _fallback_reason(look, fx)
    elif selected is None:
        # Axes resolved, library composed nothing. Reporting this as a
        # success shape is what let a caller be handed `selected: null` with
        # `fallback: false` and no reason at all.
        reason = NO_SCENE_COMPOSES_AXES
    else:
        reason = None

    return SceneMatch(
        query=text,
        kind=kind,
        look=look,
        fx=fx,
        matches=matches,
        selected=selected,
        fallback_reason=reason,
    )
