from __future__ import annotations

import ast
import copy
import re
from pathlib import Path

import pytest

from server.fx.loader import load_library_from_dir as load_fx_library_from_dir
from server.fx.matching import PATTERN_ALIASES
from server.scene import matching as scene_matching
from server.scene.loader import load_library_from_dir as load_scene_library_from_dir
from server.scene.matching import (
    AMBIGUOUS,
    BOTH_MATCHED,
    EMPTY_QUERY,
    FALLBACK,
    FX_ONLY,
    LOOK_ONLY,
    LOW_CONFIDENCE,
    NO_MATCH,
    NO_SCENE_COMPOSES_AXES,
    match_scene,
)
from server.scene.schema import SCENE_SCHEMA_VERSION, Scene, SceneLibrary

SCENE_DIR = Path(__file__).resolve().parents[1] / "scene"

# The four facts about the AXES. The fifth reason, NO_SCENE_COMPOSES_AXES, is
# deliberately NOT one of them: it says the axes resolved perfectly well and the
# LIBRARY carries no entry composing them. Different fact, different repair —
# reach for `find_looks`/`find_fx`, do not rewrite the instruction.
AXIS_FALLBACK_REASONS = frozenset({EMPTY_QUERY, NO_MATCH, LOW_CONFIDENCE, AMBIGUOUS})


def _scene(
    scene_id: str,
    *,
    display_name: str | None = None,
    label: str | None = None,
    look_id: str | None = None,
    fx_id: str | None = None,
    aliases: tuple[str, ...] = (),
    mood_keywords: tuple[str, ...] = (),
) -> Scene:
    return Scene(
        scene_id=scene_id,
        display_name=scene_id if display_name is None else display_name,
        label=scene_id.upper() if label is None else label,
        look_id=look_id,
        fx_id=fx_id,
        aliases=aliases,
        mood_keywords=mood_keywords,
    )


def _library(*entries: Scene) -> SceneLibrary:
    return SceneLibrary(schema_version=SCENE_SCHEMA_VERSION, scenes=tuple(entries))


@pytest.fixture
def library() -> SceneLibrary:
    return _library(
        _scene(
            "look-blue",
            display_name="파란 워시",
            label="BLUE",
            look_id="look-blue",
            aliases=("파란색", "블루"),
            mood_keywords=("부드러운",),
        ),
        _scene(
            "look-red",
            display_name="빨간 워시",
            label="RED",
            look_id="look-red",
            aliases=("빨간색", "레드"),
            mood_keywords=("부드러운",),
        ),
        _scene(
            "fx-wave",
            display_name="틸트 웨이브",
            label="WAVE",
            fx_id="fx-wave-tilt",
            aliases=("상하 웨이브",),
            mood_keywords=("물결치는",),
        ),
        _scene(
            "fx-circle",
            display_name="발리후 서클",
            label="CIRCLE",
            fx_id="fx-circle-ballyhoo",
            aliases=("서클",),
            mood_keywords=("화려한",),
        ),
        _scene(
            "fx-sweep-slow",
            display_name="느린 스윕",
            label="SWEEPSLOW",
            fx_id="fx-sweep-slow",
            aliases=("스윕", "느린 스윕"),
            mood_keywords=("차분한",),
        ),
        _scene(
            "fx-sweep-fast",
            display_name="빠른 스윕",
            label="SWEEPFAST",
            fx_id="fx-sweep-fast",
            aliases=("스윕", "빠른 스윕"),
            mood_keywords=("격렬한",),
        ),
        _scene(
            "scene-blue-wave",
            display_name="파란 웨이브",
            label="BLUEWAVE",
            look_id="look-blue",
            fx_id="fx-wave-tilt",
            aliases=("파란 웨이브",),
        ),
        _scene(
            "scene-red-circle",
            display_name="빨간 서클",
            label="REDCIRCLE",
            look_id="look-red",
            fx_id="fx-circle-ballyhoo",
            aliases=("빨간 서클",),
        ),
    )


@pytest.fixture(scope="module")
def shipped_library() -> SceneLibrary:
    """The library that actually ships, not the one written to suit the tests.

    The fixture above evades a whole class of defect BY CONSTRUCTION: every axis
    id in it owns a single-axis scene (``look-blue``, ``fx-wave`` …), so a
    LOOK_ONLY/FX_ONLY probe ALWAYS finds a scene. Today's ``core.yaml`` is the
    opposite — 6 of its 8 axis ids appear only inside a combined scene (pinned
    in ``test_scene_library.py``). Until this fixture landed, nothing in the
    repository ran ``match_scene`` against the shipped assets at all.
    """
    return load_scene_library_from_dir()


def _shipped_corpus(library: SceneLibrary) -> tuple[str, ...]:
    """Every surface word an operator could plausibly type at this library."""
    terms: set[str] = set()
    for scene in library.scenes:
        terms.add(scene.display_name)
        terms.update(scene.aliases)
        terms.update(scene.mood_keywords)
    terms.update(PATTERN_ALIASES)
    return tuple(sorted(terms))


def _reversed(library: SceneLibrary) -> SceneLibrary:
    return SceneLibrary(
        schema_version=library.schema_version, scenes=tuple(reversed(library.scenes))
    )


def _axis_ids(axis_match) -> list[str]:
    return [scored.axis_id for scored in axis_match.matches]


def _scene_ids(result) -> list[str]:
    return [scored.scene.scene_id for scored in result.matches]


class TestTwoAxisMatchingDiscipline:
    def test_korean_particles_select_the_look_and_fx_axes_separately(self, library):
        result = match_scene("파란색을 웨이브로 만들어줘", library)

        assert result.kind == BOTH_MATCHED
        assert result.look.selected == "look-blue"
        assert result.fx.selected == "fx-wave-tilt"
        assert result.selected is library.by_id("scene-blue-wave")
        assert result.fallback is False

    def test_tie_yields_no_axis_selection(self, library):
        result = match_scene("스윕", library)

        assert _axis_ids(result.fx) == ["fx-sweep-fast", "fx-sweep-slow"]
        assert result.fx.selected is None
        assert result.fx.fallback_reason == LOW_CONFIDENCE
        assert result.kind == FALLBACK
        assert result.selected is None

    def test_the_tie_is_not_broken_by_library_order(self, library):
        forward = match_scene("스윕", library)
        backward = match_scene("스윕", _reversed(library))

        assert forward.fx.selected is None
        assert backward.fx.selected is None
        assert _axis_ids(forward.fx) == _axis_ids(backward.fx)
        assert forward.to_dict() == backward.to_dict()

    def test_more_evidence_breaks_the_tie(self, library):
        result = match_scene("느린 스윕", library)

        assert result.kind == FX_ONLY
        assert result.fx.selected == "fx-sweep-slow"
        assert result.fx.fallback_reason is None

    def test_matching_does_not_mutate_the_library(self, library):
        before = copy.deepcopy(library)
        for query in ("파란색을 웨이브로", "스윕", "부드러운", "", "오늘 점심 뭐 먹지"):
            match_scene(query, library)
        assert library == before


class TestPartialMatchingSignals:
    def test_the_four_axis_outcomes_are_distinguishable(self, library):
        both = match_scene("파란색을 웨이브로", library)
        look_only = match_scene("파란색을", library)
        fx_only = match_scene("웨이브로", library)
        neither = match_scene("오늘 점심 뭐 먹지", library)

        assert {both.kind, look_only.kind, fx_only.kind, neither.kind} == {
            BOTH_MATCHED,
            LOOK_ONLY,
            FX_ONLY,
            FALLBACK,
        }
        assert both.selected is library.by_id("scene-blue-wave")

        assert look_only.look.selected == "look-blue"
        assert look_only.fx.selected is None
        assert look_only.selected is library.by_id("look-blue")
        assert look_only.selected.fx_id is None

        assert fx_only.look.selected is None
        assert fx_only.fx.selected == "fx-wave-tilt"
        assert fx_only.selected is library.by_id("fx-wave")
        assert fx_only.selected.look_id is None

        assert neither.look.selected is None
        assert neither.fx.selected is None
        assert neither.selected is None

    def test_partial_payload_does_not_fill_the_missing_axis_with_a_default(self, library):
        payload = match_scene("웨이브로", library).to_dict()

        assert payload["kind"] == FX_ONLY
        assert payload["look"]["selected"] is None
        assert payload["selected_look_id"] is None
        assert payload["selected_fx_id"] == "fx-wave-tilt"


class TestFallbackSignals:
    def test_the_fallback_reasons_are_distinct(self):
        assert len({NO_MATCH, LOW_CONFIDENCE, AMBIGUOUS}) == 3
        assert EMPTY_QUERY not in {NO_MATCH, LOW_CONFIDENCE, AMBIGUOUS}

    @pytest.mark.parametrize("query", ["", "   ", "\n\t"])
    def test_an_empty_query_is_a_fallback_signal_not_an_exception(self, query, library):
        result = match_scene(query, library)

        assert result.kind == FALLBACK
        assert result.fallback_reason == EMPTY_QUERY
        assert result.matches == ()
        assert result.selected is None

    def test_an_unrelated_instruction_matches_nothing_and_says_so(self, library):
        result = match_scene("오늘 점심 뭐 먹지", library)

        assert result.kind == FALLBACK
        assert result.fallback_reason == NO_MATCH
        assert result.look.matches == ()
        assert result.fx.matches == ()
        assert result.matches == ()
        assert result.selected is None

    def test_no_nearest_neighbour_is_offered_on_a_miss(self, library):
        result = match_scene("오늘 점심 뭐 먹지", library)

        assert len(library.scenes) >= 6
        assert _scene_ids(result) == []
        assert result.to_dict()["matches"] == []
        assert result.to_dict()["selected"] is None

    def test_low_confidence_reports_the_tie_without_selecting(self, library):
        result = match_scene("부드러운", library)

        assert result.kind == FALLBACK
        assert result.fallback_reason == LOW_CONFIDENCE
        assert result.look.matches
        assert result.look.selected is None
        assert result.selected is None

    def test_ambiguous_names_are_distinct_from_low_confidence(self, library):
        result = match_scene("파란색이랑 빨간색으로", library)

        assert result.kind == FALLBACK
        assert result.fallback_reason == AMBIGUOUS
        assert result.look.selected is None
        assert _axis_ids(result.look) == ["look-blue", "look-red"]


class TestFxPatternIdInference:
    def test_shipped_fx_ids_carry_the_pattern_slug_scene_matching_infers(self):
        library = load_fx_library_from_dir()

        assert len(library.fx) == 12
        for entry in library.fx:
            tokens = frozenset(re.split(r"[-_\s]+", entry.fx_id.casefold()))
            assert entry.pattern in tokens, entry.fx_id


_AXIS_REASON_CASES = (
    ("shipped", "", EMPTY_QUERY),
    ("shipped", "오늘 점심 뭐 먹지", NO_MATCH),
    ("shipped", "체이스", NO_MATCH),
    ("fixture", "부드러운", LOW_CONFIDENCE),
    ("fixture", "파란색이랑 빨간색으로", AMBIGUOUS),
)


class TestTheFifthState:
    """The axes resolved and the library composes no scene for them.

    ``kind`` reports WHICH AXES resolved. ``fallback`` reports whether there is
    anything to act on. Those two used to be one fact — ``SceneMatch.fallback``
    read ``self.kind == FALLBACK`` — and the collision produced the success
    shape with nothing in it: ``kind=fx_only``, ``fallback=False``,
    ``fallback_reason=None``, ``selected=None``. A model handed that payload is
    told to pass a ``scene_id`` the payload does not carry, and its only
    remaining move is to hand-write ``run_commands`` — the exact failure this
    SPEC exists to prevent. The console answers ``ok`` either way and no path
    reads a cue back, so the defect emits NO runtime signal: these tests are the
    only net under it.
    """

    def test_one_axis_resolved_with_no_composing_scene_declares_the_fallback(self, shipped_library):
        result = match_scene("웨이브", shipped_library)

        assert result.fx.selected == "wave-soft-rise"
        assert result.selected is None
        assert result.fallback is True
        assert result.fallback_reason == NO_SCENE_COMPOSES_AXES
        # The axis fact survives the actionability fact instead of being erased
        # by it: the operator still learns which fx the words resolved to.
        assert result.kind == FX_ONLY

    def test_both_axes_resolved_with_no_composing_scene_declares_the_same_fallback(
        self, shipped_library
    ):
        result = match_scene("말씀 회전", shipped_library)

        assert result.look.selected == "worship-scripture-key"
        assert result.fx.selected == "circle-club-wings"
        assert result.selected is None
        assert result.fallback is True
        assert result.fallback_reason == NO_SCENE_COMPOSES_AXES
        assert result.kind == BOTH_MATCHED

    @pytest.mark.parametrize("query", ["웨이브", "말씀 회전"])
    def test_the_payload_separates_the_axis_fact_from_the_actionable_fact(
        self, query, shipped_library
    ):
        payload = match_scene(query, shipped_library).to_dict()

        assert payload["selected"] is None
        assert payload["fallback"] is True
        assert payload["fallback_reason"] == NO_SCENE_COMPOSES_AXES
        # Not FALLBACK: the two facts are reported separately, so a caller can
        # still see which axes landed while being told there is nothing to run.
        assert payload["kind"] != FALLBACK
        assert payload["kind"] in {FX_ONLY, LOOK_ONLY, BOTH_MATCHED}

    def test_an_axis_tie_elsewhere_does_not_rename_the_composition_reason(self, shipped_library):
        # "차분한" ties the look axis (ballad-moonlight / worship-scripture-key)
        # while the fx axis resolves cleanly. The top-level reason is about the
        # LIBRARY; the tie is still reported, on its own axis, undisturbed.
        result = match_scene("차분한", shipped_library)

        assert result.look.selected is None
        assert result.look.fallback_reason == LOW_CONFIDENCE
        assert result.fx.selected == "wave-soft-rise"
        assert result.kind == FX_ONLY
        assert result.fallback_reason == NO_SCENE_COMPOSES_AXES

    def test_the_composition_reason_is_none_of_the_axis_reasons(self):
        assert NO_SCENE_COMPOSES_AXES not in AXIS_FALLBACK_REASONS
        assert len(AXIS_FALLBACK_REASONS | {NO_SCENE_COMPOSES_AXES}) == 5


class TestTheFifthStateControls:
    """Without these, a mutant that fails EVERYTHING into fallback passes."""

    @pytest.mark.parametrize(
        ("query", "expected_kind", "expected_scene"),
        [
            ("달빛 웨이브", BOTH_MATCHED, "ballad-moonlight-rise"),
            ("서클 모션", FX_ONLY, "club-circle-motion"),
            ("말씀 스틸", LOOK_ONLY, "worship-scripture-still"),
        ],
    )
    def test_a_query_the_library_does_compose_is_not_a_fallback(
        self, query, expected_kind, expected_scene, shipped_library
    ):
        result = match_scene(query, shipped_library)

        assert result.kind == expected_kind
        assert result.selected is not None
        assert result.selected.scene_id == expected_scene
        assert result.fallback is False
        assert result.fallback_reason is None

    @pytest.mark.parametrize(("source", "query", "expected_reason"), _AXIS_REASON_CASES)
    def test_a_query_that_resolves_no_axis_keeps_an_axis_reason(
        self, source, query, expected_reason, library, shipped_library
    ):
        result = match_scene(query, shipped_library if source == "shipped" else library)

        assert result.kind == FALLBACK
        assert result.fallback is True
        assert result.fallback_reason == expected_reason
        assert result.fallback_reason in AXIS_FALLBACK_REASONS
        assert result.fallback_reason != NO_SCENE_COMPOSES_AXES

    def test_the_controls_exercise_every_axis_reason(self):
        assert {reason for _, _, reason in _AXIS_REASON_CASES} == AXIS_FALLBACK_REASONS


class TestShippedLibrarySweep:
    """Run the shipped assets through the matcher — nothing else in the repo does.

    The invariant is the structural bar under the fifth state: whatever a query
    does, the payload must either NAME a scene or SAY it has none. A payload
    that does neither is the shape a model cannot act on honestly.
    """

    def test_the_sweep_has_something_to_sweep(self, shipped_library):
        assert len(shipped_library.scenes) >= 5
        assert len(_shipped_corpus(shipped_library)) >= 40

    def test_every_shipped_query_either_selects_a_scene_or_declares_a_fallback(
        self, shipped_library
    ):
        corpus = _shipped_corpus(shipped_library)
        offenders: list[tuple[str, str]] = []
        selected: list[str] = []
        composed_nothing: list[str] = []
        axis_reason: list[str] = []
        for query in corpus:
            result = match_scene(query, shipped_library)
            if result.selected is not None:
                selected.append(query)
            elif not result.fallback:
                offenders.append((query, result.kind))
            elif result.fallback_reason == NO_SCENE_COMPOSES_AXES:
                composed_nothing.append(query)
            else:
                axis_reason.append(query)

        assert offenders == []
        # Non-vacuity, and more: the sweep must reach all three legitimate
        # outcomes, so no single branch can carry the assertion alone.
        assert len(corpus) >= 40
        assert len(selected) >= 10
        assert len(composed_nothing) >= 5
        assert len(axis_reason) >= 1


class TestUpstreamAliasTableIsRead:
    """A 27/27 identical copy of ``PATTERN_ALIASES`` actually shipped here once.

    Identical on the day it landed, so the symptom count was zero; the day
    upstream adds one alias, scene matching alone goes deaf. Equality cannot see
    that — identity can.
    """

    def test_scene_matching_reads_the_upstream_table_instead_of_copying_it(self):
        assert scene_matching.PATTERN_ALIASES is PATTERN_ALIASES

    def test_every_upstream_alias_for_a_shipped_pattern_reaches_its_fx_axis(self, shipped_library):
        checked = 0
        for scene in shipped_library.scenes:
            if scene.fx_id is None:
                continue
            tokens = frozenset(re.split(r"[-_\s]+", scene.fx_id.casefold()))
            for alias, slug in PATTERN_ALIASES.items():
                if slug not in tokens:
                    continue
                reached = _axis_ids(match_scene(alias, shipped_library).fx)
                assert scene.fx_id in reached, (alias, scene.fx_id)
                checked += 1

        assert checked >= 15


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    return names


class TestPurity:
    _FORBIDDEN = ("anthropic", "gemini", "anthropicadapter", "geminiadapter")

    def test_matching_imports_no_transport_provider_or_tool_registry(self):
        imported = _imported_modules(SCENE_DIR / "matching.py")
        assert imported, "non-vacuity: the module must import something"
        for forbidden in (
            "server.bridge",
            "pythonosc",
            "server.llm",
            "server.orchestrator",
            "server.safety",
        ):
            assert not any(name.startswith(forbidden) for name in imported), forbidden

    def test_no_provider_name_appears_in_the_matching_surface(self):
        text = (SCENE_DIR / "matching.py").read_text(encoding="utf-8").casefold()
        assert [token for token in self._FORBIDDEN if token in text] == []
