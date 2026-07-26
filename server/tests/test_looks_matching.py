"""Natural-language look matching (M5 — AC-LOOKLIB-010 / 011 / 012 / 017).

Four things are pinned here, and they fail for different reasons on purpose:

* the matching axes themselves (genre / dynamics / mood keyword / alias),
* the Korean-first contract (REQ-LOOKLIB-018) — including the genre axis, whose
  library values are ENGLISH slugs while every operator-facing name in spec.md
  §A is Korean,
* the fallback signal (REQ-LOOKLIB-017) — a query that matches nothing
  confidently must SAY so, never surface a nearest-neighbour look,
* the two static properties AC-LOOKLIB-012 and AC-LOOKLIB-017 assert: the fixed
  rulebook prefix carries no look data, and the matching surface names no LLM
  provider.
"""

from __future__ import annotations

import ast
import unicodedata
from pathlib import Path

import pytest

from server.looks.loader import load_library_from_dir
from server.looks.matching import (
    DYNAMICS_TERMS,
    EMPTY_QUERY,
    GENRE_ALIASES,
    LOW_CONFIDENCE,
    MAX_TOOL_MATCHES,
    NO_MATCH,
    match_looks,
    resolve_dynamics,
    resolve_genre,
)
from server.looks.schema import Look
from server.rulebook.assembly import assemble_prefix, rulebook_dir

LOOKS_DIR = Path(__file__).resolve().parents[1] / "looks"

# The four genre names exactly as spec.md §A writes them for the operator.
# Three are Korean; EDM is already latin there, and inventing a Hangul-only
# rule would force a transliteration the SPEC never asked for.
SPEC_GENRE_TERMS = ("워십", "록", "발라드", "EDM")


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir()


def _ids(result) -> list[str]:
    return [scored.look.look_id for scored in result.matches]


def _genres(result) -> set[str]:
    return {scored.look.genre for scored in result.matches}


# --------------------------------------------------------------------------
# The genre axis — the one place the library speaks English and the user does not
# --------------------------------------------------------------------------


class TestGenreAxisIsBilingual:
    """The library's ``genre`` field holds English slugs (``worship`` / ``rock``
    / ``ballad`` / ``edm``) while spec.md §A names the genres 워십 / 록 / 발라드
    / EDM. Nothing in the assets bridges the two, so this surface owns the
    bridge — and a user typing 워십 must never fall through to no-match because
    of it (REQ-LOOKLIB-018)."""

    @pytest.mark.parametrize("term", SPEC_GENRE_TERMS)
    def test_every_spec_genre_name_resolves(self, term, library):
        genre = resolve_genre(term)
        assert genre is not None, f"{term!r} (spec.md §A) resolves to no genre"
        assert genre in {look.genre for look in library.looks}

    def test_the_korean_genre_word_reaches_the_english_slug(self, library):
        # The specific failure M2 handed forward: 워십 -> worship.
        assert resolve_genre("워십") == "worship"
        assert resolve_genre("록") == "rock"
        assert resolve_genre("발라드") == "ballad"

    @pytest.mark.parametrize("term", ["worship", "WORSHIP", "Rock", "ballad", "edm", "EDM"])
    def test_the_english_slug_still_resolves_and_is_case_insensitive(self, term):
        # Parametrised, not looped: a loop only ever proves its FIRST failing
        # item, so a mutation could be "killed" without the later casings ever
        # being reached.
        assert resolve_genre(term) is not None

    def test_every_library_genre_is_reachable_from_some_alias(self, library):
        # The pin that survives a 5th genre: adding one without a surface term
        # makes it unreachable, and this fails rather than silently matching
        # nothing.
        reachable = set(GENRE_ALIASES.values())
        for genre in {look.genre for look in library.looks}:
            assert genre in reachable, f"genre {genre!r} has no surface term"

    def test_no_alias_points_at_a_genre_the_library_does_not_have(self, library):
        present = {look.genre for look in library.looks}
        assert set(GENRE_ALIASES.values()) <= present

    def test_a_korean_genre_query_returns_only_that_genre(self, library):
        result = match_looks("워십 느낌으로", library)
        assert _genres(result) == {"worship"}
        assert result.genre == "worship"
        assert result.fallback_reason is None

    @pytest.mark.parametrize("query", ["블록 만들어줘", "기록 남겨줘", "목록 보여줘"])
    def test_a_genre_word_inside_a_longer_word_is_not_a_genre(self, query, library):
        # 록 lives inside 블록 / 기록 / 목록. A substring matcher would read a
        # genre out of every one of them.
        assert resolve_genre(query) is None
        assert match_looks(query, library).genre is None

    def test_two_genres_named_at_once_constrain_nothing(self, library):
        # Documented behaviour needs a test or it is an accident (M3's lesson).
        # A query naming two genres is ambiguous on this axis, and the axis
        # reports nothing rather than picking whichever was seen first — the
        # same rule roles.py applies to a group name two roles claim.
        assert resolve_genre("워십이나 발라드") is None
        result = match_looks("워십이나 발라드", library)
        assert result.genre is None

    def test_the_two_genre_control_really_does_name_two_genres(self, library):
        # Non-vacuity for the test above: each half resolves on its own, so the
        # None is ambiguity, not two failed lookups.
        assert resolve_genre("워십이나") == "worship"
        assert resolve_genre("발라드") == "ballad"


# --------------------------------------------------------------------------
# The dynamics axis
# --------------------------------------------------------------------------


class TestDynamicsAxis:
    def test_section_words_resolve_to_a_band(self):
        assert resolve_dynamics("인트로") == (1, 2)
        assert resolve_dynamics("코러스") == (4, 5)
        assert resolve_dynamics("드랍") == (4, 5)

    def test_every_declared_band_is_inside_the_schema_range(self):
        for term, band in DYNAMICS_TERMS.items():
            assert band, f"{term!r} declares an empty band"
            assert all(1 <= level <= 5 for level in band), term

    def test_a_dynamics_constrained_query_returns_only_that_band(self, library):
        result = match_looks("EDM 드랍", library)
        assert result.genre == "edm"
        assert result.dynamics == (4, 5)
        assert _genres(result) == {"edm"}
        assert {scored.look.dynamics for scored in result.matches} <= {4, 5}
        assert result.matches, "a named genre + band must return its band"
        assert result.fallback_reason is None

    def test_a_band_query_excludes_the_looks_outside_it(self, library):
        result = match_looks("EDM 드랍", library)
        ids = _ids(result)
        assert "edm-ambient-hold" not in ids  # dynamics 1
        assert "edm-intro-bed" not in ids  # dynamics 2

    def test_a_genre_and_section_pair_lands_in_the_expected_band(self, library):
        # AC-LOOKLIB-010's second example phrase.
        result = match_looks("잔잔한 발라드 인트로", library)
        assert result.genre == "ballad"
        assert result.dynamics == (1, 2)
        assert _genres(result) == {"ballad"}
        assert {scored.look.dynamics for scored in result.matches} <= {1, 2}

    def test_the_band_excludes_a_look_the_keyword_axis_would_have_scored(self, library):
        # The band filter needs a case where it CHANGES the answer. In "EDM
        # 드랍" the keyword and the band happen to select the same three looks,
        # so that test passes with the filter removed entirely — it proves the
        # keyword axis, not the filter.
        #
        # 차오르는 is a mood keyword of two dynamics-3 looks. Naming an intro
        # (band 1-2) must drop both.
        unbanded = _ids(match_looks("차오르는", library))
        assert "worship-rising-warmth" in unbanded
        assert "ballad-second-verse-rise" in unbanded

        banded = match_looks("차오르는 인트로", library)
        assert banded.dynamics == (1, 2)
        assert "worship-rising-warmth" not in _ids(banded)
        assert "ballad-second-verse-rise" not in _ids(banded)
        assert {scored.look.dynamics for scored in banded.matches} <= {1, 2}


# --------------------------------------------------------------------------
# Mood keyword / alias hits
# --------------------------------------------------------------------------


class TestKeywordAndAliasHits:
    def test_a_distinctive_mood_keyword_selects_one_look(self, library):
        result = match_looks("경건한 분위기", library)
        assert result.selected is not None
        assert result.selected.look_id == "worship-prayer-wash"
        assert result.fallback_reason is None

    def test_an_alias_hit_selects_its_look(self, library):
        result = match_looks("금빛 코러스", library)
        assert result.selected is not None
        assert result.selected.look_id == "worship-golden-chorus"

    def test_the_acceptance_phrase_selects_the_golden_chorus(self, library):
        # AC-LOOKLIB-014's live phrase, particle and all: 코러스*로*.
        result = match_looks("웅장한 금색 코러스로 가자", library)
        assert result.selected is not None
        assert result.selected.look_id == "worship-golden-chorus"
        assert result.fallback_reason is None

    def test_matched_terms_are_reported_not_just_a_score(self, library):
        result = match_looks("웅장한 금색 코러스로 가자", library)
        top = result.matches[0]
        assert top.score == len(top.matched)
        assert "웅장한" in top.matched
        assert "금색" in top.matched

    def test_a_display_name_query_finds_its_look(self, library):
        result = match_looks("영광의 클라이맥스", library)
        assert result.selected is not None
        assert result.selected.look_id == "worship-glory-climax"

    def test_words_that_match_nothing_are_ignored_not_penalised(self, library):
        plain = match_looks("경건한", library)
        padded = match_looks("오늘은 경건한 느낌이면 좋겠어", library)
        assert padded.selected is not None
        assert plain.selected is not None
        assert padded.selected.look_id == plain.selected.look_id


class TestMatchingIsByTokenNotBySubstring:
    """The M1 lesson in the query axis: `백` must not be found inside `백색`.
    Here the live hazards are English `drop` inside `backdrop`, Korean `밤`
    inside `밤하늘`, and `빔` inside `빔프로젝터`."""

    def test_backdrop_does_not_contain_the_edm_drop(self, library):
        result = match_looks("backdrop wash", library)
        assert result.dynamics == ()
        assert not any(scored.look.genre == "edm" for scored in result.matches)
        assert result.fallback_reason == NO_MATCH

    def test_a_korean_keyword_inside_a_longer_word_does_not_hit(self, library):
        # 밤 is ballad-moonlight's mood keyword.
        result = match_looks("밤하늘이 예쁘다", library)
        assert "ballad-moonlight" not in _ids(result)

    def test_beam_does_not_match_a_projector(self, library):
        # 빔 is edm-drop-beams' mood keyword.
        result = match_looks("빔프로젝터 켜줘", library)
        assert "edm-drop-beams" not in _ids(result)

    @pytest.mark.parametrize(
        "query", ["드랍으로", "드랍에서", "드랍은", "드랍까지", "드랍의", "드랍만"]
    )
    def test_a_keyword_followed_by_a_korean_particle_still_hits(self, query):
        # One case per particle, not a loop: a loop stops at the first failure,
        # so it can only ever prove the particle that happens to be first.
        assert resolve_dynamics(query) == (4, 5)

    @pytest.mark.parametrize("query", ["드랍곡", "드랍파티", "코러스단", "밤하늘"])
    def test_a_keyword_followed_by_a_non_particle_syllable_does_not_hit(self, query):
        # 드랍 + 곡 is a different word, not 드랍 + a particle.
        assert resolve_dynamics(query) is None

    def test_a_decomposed_hangul_query_matches_the_same_look(self, library):
        phrase = "웅장한 금색 코러스"
        composed = match_looks(unicodedata.normalize("NFC", phrase), library)
        decomposed = match_looks(unicodedata.normalize("NFD", phrase), library)
        assert composed.selected is not None
        assert decomposed.selected is not None
        assert decomposed.selected.look_id == composed.selected.look_id


# --------------------------------------------------------------------------
# The fallback signal — REQ-LOOKLIB-017 / AC-LOOKLIB-011
# --------------------------------------------------------------------------


class TestFallbackSignal:
    def test_an_unrelated_instruction_matches_nothing_and_says_so(self, library):
        result = match_looks("오늘 점심 뭐 먹지", library)
        assert result.matches == ()
        assert result.selected is None
        assert result.fallback_reason == NO_MATCH
        assert result.fallback is True

    def test_no_nearest_neighbour_is_offered_on_a_miss(self, library):
        # The failure this SPEC forbids: quietly returning "the closest look".
        result = match_looks("오늘 점심 뭐 먹지", library)
        assert _ids(result) == []

    @pytest.mark.parametrize("query", ["", "   ", "\n\t"])
    def test_an_empty_query_is_its_own_reason(self, query, library):
        result = match_looks(query, library)
        assert result.fallback_reason == EMPTY_QUERY
        assert result.matches == ()
        assert result.selected is None

    def test_a_mood_word_spread_across_genres_is_low_confidence(self, library):
        # 따뜻한 sits on worship, ballad AND rock looks. With no genre and no
        # section named there is nothing to choose between them, and choosing
        # anyway is the guess this SPEC keeps refusing.
        result = match_looks("따뜻한", library)
        assert len(_genres(result)) >= 2
        assert result.selected is None
        assert result.fallback_reason == LOW_CONFIDENCE
        assert result.fallback is True

    def test_the_same_mood_word_with_a_genre_is_confident_again(self, library):
        # The constraint the user supplied is what makes the band meaningful.
        result = match_looks("따뜻한 발라드", library)
        assert _genres(result) == {"ballad"}
        assert result.fallback_reason is None
        assert result.fallback is False

    def test_a_low_confidence_result_still_reports_what_it_saw(self, library):
        # Honest reporting, not a selection: the tie is visible, `selected`
        # stays empty (the resolver's `ambiguous` discipline, one layer up).
        result = match_looks("따뜻한", library)
        assert result.matches, "the tie must be reported, not swallowed"
        assert result.selected is None

    def test_the_rulebook_mood_fallback_section_is_unchanged(self):
        # AC-LOOKLIB-011: the path a fallback degrades TO must be preserved.
        #
        # M7 renamed this heading — "resolve the rig FIRST" was the exact
        # phrase that out-competed the library note, so the word FIRST now
        # points at the library. What this test guards is unchanged: the
        # section a fallback degrades TO still exists, and the four table
        # rows below (the destination itself) are asserted byte-for-byte.
        source = (rulebook_dir() / "31_choreography_patterns.md").read_text(encoding="utf-8")
        assert "### Concept / mood instructions — ask the look library FIRST" in source
        for row in (
            "| warm / ballad / intimate | 40–70% | amber (R high, G low, B ~0) "
            "| none, or slow Tilt sway, Speed 10–20 |",
            "| cool / calm / night | 30–60% | blue / cyan | slow, gentle |",
            "| energetic / club / party | 80–100% | saturated, cycling "
            "(2-color chase or rainbow) | fast Pan/Tilt sweep or circle, Speed 90–180 |",
            "| dramatic / build | rising across successive cues | deep color → white "
            "| accelerating |",
        ):
            assert row in source, row


# --------------------------------------------------------------------------
# AC-LOOKLIB-017 — single source of truth + provider neutrality
# --------------------------------------------------------------------------


class TestSingleSourceOfTruth:
    def test_every_returned_look_comes_from_the_loaded_library(self, library):
        known = {look.look_id for look in library.looks}
        for query in ("웅장한 금색 코러스", "EDM 드랍", "따뜻한", "발라드", "rock chorus"):
            result = match_looks(query, library)
            assert set(_ids(result)) <= known, query
            if result.selected is not None:
                assert result.selected.look_id in known

    def test_a_look_absent_from_the_injected_library_is_never_returned(self, library):
        # Matching reads ONLY what it was handed: shrink the library and the
        # look disappears, so no second source can be feeding it.
        assert match_looks("경건한", library).selected is not None
        without = type(library)(
            schema_version=library.schema_version,
            looks=tuple(look for look in library.looks if look.look_id != "worship-prayer-wash"),
        )
        result = match_looks("경건한", without)
        assert "worship-prayer-wash" not in _ids(result)

    def test_matching_is_a_pure_function_of_query_and_library(self, library):
        first = match_looks("웅장한 금색 코러스", library)
        second = match_looks("웅장한 금색 코러스", library)
        assert _ids(first) == _ids(second)
        assert first.to_dict() == second.to_dict()

    def test_the_returned_look_is_the_library_object_itself(self, library):
        result = match_looks("경건한", library)
        assert isinstance(result.selected, Look)
        assert result.selected is library.by_id("worship-prayer-wash")


class TestProviderNeutrality:
    _FORBIDDEN = ("anthropic", "gemini", "anthropicadapter", "geminiadapter")

    def test_no_look_module_names_an_llm_provider(self):
        offenders = [
            f"{path.name}: {token}"
            for path in sorted(LOOKS_DIR.rglob("*.py"))
            for token in self._FORBIDDEN
            if token in path.read_text(encoding="utf-8").casefold()
        ]
        assert offenders == []

    def test_the_provider_scan_is_not_vacuous(self):
        # The same scan over a module that DOES name a provider must fire.
        factory = Path(__file__).resolve().parents[1] / "llm" / "factory.py"
        text = factory.read_text(encoding="utf-8").casefold()
        assert any(token in text for token in self._FORBIDDEN)

    def test_matching_imports_nothing_from_the_llm_layer(self):
        tree = ast.parse((LOOKS_DIR / "matching.py").read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert imported, "non-vacuity: the module must import something"
        assert not any(name.startswith("server.llm") for name in imported)
        # No cycle back into the tool registry either (M3's reason for keeping
        # the two unavailable reasons unenumerated).
        assert not any(name.startswith("server.orchestrator") for name in imported)


# --------------------------------------------------------------------------
# AC-LOOKLIB-012 — the fixed prefix carries guidance, never look data
# --------------------------------------------------------------------------


class TestFixedPrefixDiscipline:
    def test_the_prefix_carries_no_look_id(self, library):
        prefix = assemble_prefix()
        assert prefix, "non-vacuity: the prefix must be non-empty"
        for look in library.looks:
            assert look.look_id not in prefix, look.look_id

    def test_the_prefix_carries_no_look_display_name(self, library):
        prefix = assemble_prefix()
        for look in library.looks:
            assert look.display_name not in prefix, look.display_name

    def test_the_prefix_carries_no_schema_field_of_the_look_data(self):
        prefix = assemble_prefix()
        for marker in ("look_id", "mood_keywords", "schema_version", "dynamics:"):
            assert marker not in prefix, marker

    def test_the_prefix_names_the_look_tool_so_the_axis_is_reachable(self):
        # The guidance axis is the whole reason a byte changed; if it is not
        # here the change bought nothing.
        assert "find_looks" in assemble_prefix()

    def test_the_guidance_axis_defers_to_the_mood_table_rather_than_replacing_it(self):
        source = (rulebook_dir() / "31_choreography_patterns.md").read_text(encoding="utf-8")
        axis = source.index("find_looks")
        table = source.index("Rough mood → design starting points")
        assert axis < table, "the axis must precede the table it defers to"

    def test_the_prefix_stays_byte_identical_across_assemblies(self):
        # REQ-LOOKLIB-022: a static text change is a ONE-TIME cache
        # invalidation, so the assembled string must still be a pure function
        # of the assets.
        builds = [assemble_prefix() for _ in range(5)]
        assert all(build == builds[0] for build in builds)

    def test_the_prefix_carries_no_per_turn_value(self):
        # The guidance axis must not have smuggled one in.
        import re

        prefix = assemble_prefix()
        assert not re.search(r"\d{4}-\d{2}-\d{2}", prefix)
        assert "session" not in prefix.lower()


# --------------------------------------------------------------------------
# M7 steering fix — the mood procedure ROUTES through the library
#
# What M7 measured live: the turn produced a designed look and an executor
# assignment, and created no preset and bound no role. What the rulebook
# looked like at that moment: TWO sections triggered on the same input — a
# look-library note that ADVISED calling find_looks, and, immediately below
# it, a self-contained "resolve the rig FIRST" recipe that INSTRUCTED and
# terminated in exactly the observed behaviour. A model entering the second
# had no reason to leave it: the recipe never mentions the library.
#
# These tests pin the STRUCTURE that removes the competition. None of them
# can observe whether a model actually calls the tool — that is only
# measurable live, and is stated as an explicit gap rather than dressed up
# as coverage here.
# --------------------------------------------------------------------------


class TestMoodProcedureRoutesThroughTheLibrary:
    @staticmethod
    def _source() -> str:
        return (rulebook_dir() / "31_choreography_patterns.md").read_text(encoding="utf-8")

    def test_the_mood_procedure_reaches_the_library_before_the_rig(self):
        # The defect was ORDER, not absence: both tools were named, but the
        # rig step owned the word FIRST and the whole recipe. If a future
        # edit puts get_rig_context back in front, the library becomes an
        # optional aside again and this fails.
        source = self._source()
        assert "find_looks" in source, "non-vacuity: the tool must be named"
        assert "get_rig_context" in source, "non-vacuity: the rig step must survive"
        assert source.index("find_looks") < source.index("get_rig_context")

    def test_no_section_boundary_separates_the_library_step_from_the_mood_table(self):
        # The anti-competition pin. A `###` heading between the library step
        # and the table it falls back to is exactly the shape M7 measured:
        # two sections triggering on one input, the later one self-contained.
        # One procedure cannot compete with itself.
        source = self._source()
        start = source.index("find_looks")
        table = source.index("Rough mood → design starting points")
        assert start < table, "non-vacuity: the library step must precede the table"
        assert "\n### " not in source[start:table]

    def test_the_fallback_still_routes_to_the_mood_table(self):
        # Constraint: reaching the library must not become "the library
        # always answers". The fallback signal keeps its own exit.
        source = self._source()
        assert "fallback" in source.lower()
        assert "Rough mood → design starting points" in source
        fallback = source.lower().index("fallback")
        assert fallback < source.index("Rough mood → design starting points")

    def test_the_library_still_refuses_to_invent_a_look(self):
        # Matched on the LIBRARY's own refusal, not on any "never invent"
        # anywhere in the file: the first draft of this test asserted the
        # bare phrase and SURVIVED a mutation that deleted the library
        # sentence outright — it was passing on the strength of the
        # unrelated `NEVER invent a Group 3` rule two paragraphs down.
        # The two refusals are independent and must fail independently.
        assert "returns library looks only, and never invents one" in self._source()

    def test_the_two_refusals_are_independent(self):
        # Non-vacuity for the pair above: each must be present on its own
        # terms, so neither test can be satisfied by the other's string.
        source = self._source()
        library_refusal = "returns library looks only, and never invents one"
        group_refusal = "NEVER invent a `Group 3`"
        assert library_refusal in source
        assert group_refusal in source
        assert library_refusal not in group_refusal
        assert group_refusal not in library_refusal

    @pytest.mark.parametrize(
        "rule",
        [
            "ChangeDestination Root",  # the programming-destination reminder
            "NOT its fixture id",  # the slot != FID warning (live-earned)
            "NEVER invent a `Group 3`",  # the missing-group rule (live-earned)
        ],
    )
    def test_the_live_earned_rules_survive_the_restructure(self, rule):
        # These three were paid for on a live console. A restructure that
        # loses one trades a measured defence for a tidier document.
        assert rule in self._source()


# --------------------------------------------------------------------------
# Report shape (what the tool serialises)
# --------------------------------------------------------------------------


class TestReportShape:
    def test_a_confident_result_names_its_selection(self, library):
        report = match_looks("웅장한 금색 코러스", library).to_dict()
        assert report["selected"] == "worship-golden-chorus"
        assert report["fallback"] is False
        assert report["fallback_reason"] is None
        assert report["genre"] is None or report["genre"] == "worship"

    def test_a_fallback_result_says_so_in_the_payload(self, library):
        report = match_looks("오늘 점심 뭐 먹지", library).to_dict()
        assert report["fallback"] is True
        assert report["fallback_reason"] == NO_MATCH
        assert report["matches"] == []
        assert report["selected"] is None

    def test_each_match_carries_the_values_a_look_is_made_of(self, library):
        report = match_looks("웅장한 금색 코러스", library).to_dict()
        entry = report["matches"][0]
        assert entry["look_id"] == "worship-golden-chorus"
        assert entry["genre"] == "worship"
        assert entry["dynamics"] == 4
        assert entry["roles"]
        assert entry["attributes"]["Dimmer"] == 88
        assert entry["score"] >= 1
        assert entry["matched"]

    def test_a_long_result_is_truncated_and_says_it_was(self, library):
        # Never present a partial list as a complete one (the rig-context rule).
        report = match_looks("EDM", library).to_dict()
        assert report["total"] == 9
        assert len(report["matches"]) == min(9, MAX_TOOL_MATCHES)
        assert report["truncated"] is (MAX_TOOL_MATCHES < 9)

    def test_a_short_result_is_not_flagged_as_truncated(self, library):
        report = match_looks("경건한", library).to_dict()
        assert report["truncated"] is False
        assert report["total"] == len(report["matches"])

    def test_the_report_carries_no_rig_binding(self, library):
        # A look has no group number, preset slot or FID — and the report must
        # not have invented one on the way out (REQ-LOOKLIB-004).
        report = match_looks("웅장한 금색 코러스", library).to_dict()
        for entry in report["matches"]:
            assert set(entry) == {
                "look_id",
                "display_name",
                "genre",
                "dynamics",
                "roles",
                "attributes",
                "score",
                "matched",
            }


# --------------------------------------------------------------------------
# Tool registration (AC-LOOKLIB-010's chat-pipeline half)
# --------------------------------------------------------------------------


class _RecordingPort:
    """Execution port that must never be reached by a lookup tool."""

    def __init__(self):
        self.executed: list[str] = []

    def execute(self, command: str):
        from server.orchestrator.ports import ExecutionResult

        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class _EmptyStatePort:
    def query_state(self, path: str) -> dict:
        raise LookupError(path)


def _registry(library=None):
    from server.orchestrator.tools import build_toolset

    return build_toolset(
        execution_port=_RecordingPort(),
        state_port=_EmptyStatePort(),
        look_library=library,
    )


def _dispatch(registry, arguments: dict):
    import json

    from server.llm.types import ToolCall

    execution = registry.dispatch(ToolCall(id="c1", name="find_looks", arguments=arguments))
    return execution.result, json.loads(execution.result.content)


class TestFindLooksTool:
    def test_the_tool_is_registered_with_a_neutral_definition(self):
        from server.orchestrator.tools import TOOL_NAMES

        assert "find_looks" in TOOL_NAMES
        definition = next(d for d in _registry().definitions() if d.name == "find_looks")
        assert definition.description.strip()
        assert definition.parameters["type"] == "object"
        assert "query" in definition.parameters["properties"]
        assert definition.parameters["required"] == ["query"]

    def test_a_korean_query_round_trips_through_the_registry(self, library):
        result, payload = _dispatch(_registry(library), {"query": "웅장한 금색 코러스로 가자"})
        assert result.is_error is False
        assert payload["selected"] == "worship-golden-chorus"

    def test_the_lookup_tool_executes_nothing_on_the_console(self, library):
        from server.orchestrator.tools import build_toolset

        port = _RecordingPort()
        registry = build_toolset(
            execution_port=port,
            state_port=_EmptyStatePort(),
            look_library=library,
        )
        _dispatch(registry, {"query": "웅장한 금색 코러스"})
        assert port.executed == []

    def test_a_fallback_is_returned_as_a_result_not_an_error(self, library):
        # A miss is a legitimate answer (REQ-LOOKLIB-017), not a tool failure —
        # an is_error payload would feed the self-correction loop and invite a
        # retry that can only miss again.
        result, payload = _dispatch(_registry(library), {"query": "오늘 점심 뭐 먹지"})
        assert result.is_error is False
        assert payload["fallback"] is True
        assert payload["fallback_reason"] == NO_MATCH

    def test_a_missing_query_argument_is_an_error(self, library):
        result, payload = _dispatch(_registry(library), {})
        assert result.is_error is True
        assert "query" in payload["error"]

    @pytest.mark.parametrize("bad", [5, None, ["웅장한"], {"q": "x"}, True])
    def test_a_non_string_query_is_an_error(self, bad, library):
        result, _payload = _dispatch(_registry(library), {"query": bad})
        assert result.is_error is True

    def test_a_blank_query_is_a_fallback_result_not_an_argument_error(self, library):
        # Blank is a miss, not a malformed call — and this is the only path on
        # which EMPTY_QUERY reaches the wire.
        result, payload = _dispatch(_registry(library), {"query": "   "})
        assert result.is_error is False
        assert payload["fallback_reason"] == EMPTY_QUERY

    def test_the_default_library_is_loaded_when_none_is_injected(self):
        # Production wiring passes no library; the tool must still answer.
        result, payload = _dispatch(_registry(), {"query": "웅장한 금색 코러스"})
        assert result.is_error is False
        assert payload["selected"] == "worship-golden-chorus"

    def test_the_tool_description_tells_the_model_about_the_fallback(self):
        definition = next(d for d in _registry().definitions() if d.name == "find_looks")
        assert "fallback" in definition.description.lower()
