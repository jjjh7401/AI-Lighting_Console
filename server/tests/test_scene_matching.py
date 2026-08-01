from __future__ import annotations

import ast
import copy
import re
from pathlib import Path

import pytest

from server.fx.loader import load_library_from_dir
from server.scene.matching import (
    AMBIGUOUS,
    BOTH_MATCHED,
    EMPTY_QUERY,
    FALLBACK,
    FX_ONLY,
    LOOK_ONLY,
    LOW_CONFIDENCE,
    NO_MATCH,
    match_scene,
)
from server.scene.schema import SCENE_SCHEMA_VERSION, Scene, SceneLibrary

SCENE_DIR = Path(__file__).resolve().parents[1] / "scene"


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
        library = load_library_from_dir()

        assert len(library.fx) == 12
        for entry in library.fx:
            tokens = frozenset(re.split(r"[-_\s]+", entry.fx_id.casefold()))
            assert entry.pattern in tokens, entry.fx_id


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
