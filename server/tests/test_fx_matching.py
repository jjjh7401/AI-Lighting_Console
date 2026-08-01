"""Natural-language fx matching (M3 — AC-FXLIB-005 / 006 / 007).

Three contracts are pinned here, and they fail for different reasons on purpose:

* **the matching discipline** (AC-FXLIB-005) — Korean particles, a tie that
  selects nothing, and a deterministic order,
* **the single source of truth** (AC-FXLIB-006) — every returned entry is an
  object the caller's own library handed over; the matcher invents nothing,
* **the fallback signal** (AC-FXLIB-007) — a query that lands nothing
  confidently must SAY so, never surface the lowest-scoring candidate.

The library here is built in memory rather than loaded from ``server/fx/library``
(M2's asset, authored in parallel with this milestone). That is not a
convenience: matching reads ONLY the library it is handed, and an injected
fixture is what proves it — a test against the shipped assets could not tell
"matched from the library" apart from "matched from somewhere else".
"""

from __future__ import annotations

import ast
import copy
import unicodedata
from pathlib import Path

import pytest

from server.fx.matching import (
    EMPTY_QUERY,
    LOW_CONFIDENCE,
    MAX_TOOL_MATCHES,
    NO_MATCH,
    PATTERN_ALIASES,
    FxMatch,
    match_fx,
    resolve_pattern,
)
from server.fx.schema import FX_SCHEMA_VERSION, PATTERN_KINDS, Fx, FxLibrary, FxStep, StepValue

# The looks particle list is read (never written) so a particle added there
# cannot silently go missing here. M1 took the same shape with
# ``KNOWN_ATTRIBUTES``: the read-only looks import lives in the TEST layer, and
# ``server/fx/`` itself imports nothing but stdlib and its own schema.
from server.looks.matching import _PARTICLES as LOOKS_PARTICLES

FX_DIR = Path(__file__).resolve().parents[1] / "fx"

# The operator-facing pattern words of spec.md §A, one per closed pattern kind.
SPEC_PATTERN_TERMS = (
    ("스윕", "sweep"),
    ("웨이브", "wave"),
    ("서클", "circle"),
    ("대각선", "diagonal"),
    ("펄스", "pulse"),
    ("체이스", "chase"),
)


# --------------------------------------------------------------------------
# In-memory fixtures
# --------------------------------------------------------------------------


def _steps(attribute: str, *values: float) -> tuple[FxStep, ...]:
    """A step run of one attribute — the M0 anchor shape, one value per step."""
    return tuple(FxStep(values=(StepValue(attribute=attribute, value=value),)) for value in values)


def _fx(
    fx_id: str,
    pattern: str,
    *,
    display_name: str | None = None,
    aliases: tuple[str, ...] = (),
    mood_keywords: tuple[str, ...] = (),
    attribute: str = "Dimmer",
    values: tuple[float, ...] = (100.0, 0.0),
    **axes,
) -> Fx:
    return Fx(
        fx_id=fx_id,
        display_name=fx_id if display_name is None else display_name,
        pattern=pattern,
        steps=_steps(attribute, *values),
        aliases=aliases,
        mood_keywords=mood_keywords,
        **axes,
    )


def _library(*entries: Fx) -> FxLibrary:
    return FxLibrary(schema_version=FX_SCHEMA_VERSION, fx=tuple(entries))


@pytest.fixture
def library() -> FxLibrary:
    """One entry per pattern kind, plus a second `sweep` so ties are reachable.

    ``부드러운`` deliberately sits on a sweep AND a wave entry: an unconstrained
    mood word spanning two patterns is the low-confidence case, and it has to be
    reachable to be tested.
    """
    return _library(
        _fx(
            "sweep-slow-pan",
            "sweep",
            display_name="느린 팬 스윕",
            aliases=("느린 스윕",),
            mood_keywords=("부드러운", "부드럽게", "잔잔한"),
            attribute="Pan",
            values=(-20.0, 20.0),
            phase_from=0.0,
            phase_to=360.0,
            speed=20.0,
        ),
        _fx(
            "sweep-fast-pan",
            "sweep",
            display_name="빠른 팬 스윕",
            aliases=("질주",),
            mood_keywords=("빠른", "격렬한"),
            attribute="Pan",
            values=(-30.0, 30.0),
            speed=140.0,
        ),
        _fx(
            "wave-tilt",
            "wave",
            display_name="틸트 웨이브",
            aliases=("상하 웨이브",),
            mood_keywords=("부드러운", "물결치는"),
            attribute="Tilt",
            values=(-10.0, 10.0),
            speed=30.0,
        ),
        _fx(
            "circle-ballyhoo",
            "circle",
            display_name="발리후 서클",
            mood_keywords=("화려한",),
            attribute="Pan",
            values=(-20.0, 20.0),
            speed=45.0,
        ),
        _fx(
            "diagonal-cross",
            "diagonal",
            display_name="대각 크로스",
            mood_keywords=("교차하는",),
            attribute="Tilt",
            values=(-15.0, 15.0),
        ),
        _fx(
            "pulse-dimmer",
            "pulse",
            display_name="디머 펄스",
            mood_keywords=("맥동하는",),
            attribute="Dimmer",
            values=(100.0, 0.0),
            speed=60.0,
        ),
        _fx(
            "chase-color",
            "chase",
            display_name="컬러 체이스",
            mood_keywords=("현란한",),
            attribute="ColorRGB_R",
            values=(100.0, 0.0),
        ),
    )


def _ids(result: FxMatch) -> list[str]:
    return [scored.fx.fx_id for scored in result.matches]


def _patterns(result: FxMatch) -> set[str]:
    return {scored.fx.pattern for scored in result.matches}


def _reversed(library: FxLibrary) -> FxLibrary:
    return FxLibrary(schema_version=library.schema_version, fx=tuple(reversed(library.fx)))


# --------------------------------------------------------------------------
# The pattern axis — the one place the library speaks English and the user does not
# --------------------------------------------------------------------------


class TestPatternAxisIsBilingual:
    """The library's ``pattern`` field holds English slugs (the closed set of
    ``PATTERN_KINDS``) while every operator-facing name in spec.md §A is Korean.
    Nothing in the assets bridges the two, so this surface owns the bridge — and
    the bridge must never name a pattern the schema does not have."""

    def test_no_alias_names_a_pattern_the_schema_does_not_have(self):
        # The "never invent" rule at the vocabulary level: the bridge can only
        # ever point INTO the closed set.
        assert set(PATTERN_ALIASES.values()) <= set(PATTERN_KINDS)

    def test_every_pattern_kind_is_reachable_from_some_term(self):
        # The pin that survives a 7th pattern: adding one to the schema without
        # a surface term makes it unreachable, and this fails rather than
        # silently matching nothing.
        reachable = set(PATTERN_ALIASES.values())
        for kind in PATTERN_KINDS:
            assert kind in reachable, f"pattern {kind!r} has no surface term"

    @pytest.mark.parametrize(("term", "slug"), SPEC_PATTERN_TERMS)
    def test_the_korean_pattern_word_reaches_the_english_slug(self, term, slug):
        assert resolve_pattern(term) == slug

    @pytest.mark.parametrize(
        "term", ["sweep", "SWEEP", "Wave", "circle", "DIAGONAL", "pulse", "Chase"]
    )
    def test_the_english_slug_still_resolves_and_is_case_insensitive(self, term):
        # Parametrised, not looped: a loop only ever proves its FIRST failing
        # item, so a mutation could be "killed" without the later casings ever
        # being reached.
        assert resolve_pattern(term) is not None

    def test_two_patterns_named_at_once_constrain_nothing(self, library):
        # Two patterns named is NOT half a constraint: the query is ambiguous on
        # this axis, so the axis reports nothing rather than picking whichever
        # was seen first.
        assert resolve_pattern("웨이브랑 서클") is None
        assert match_fx("웨이브랑 서클", library).pattern is None

    def test_the_two_pattern_control_really_does_name_two_patterns(self):
        # Non-vacuity for the test above: each half resolves on its own, so the
        # None is ambiguity, not two failed lookups.
        assert resolve_pattern("웨이브랑") == "wave"
        assert resolve_pattern("서클") == "circle"

    def test_a_pattern_query_returns_only_that_pattern(self, library):
        result = match_fx("웨이브로 돌려줘", library)
        assert _patterns(result) == {"wave"}
        assert result.pattern == "wave"


class TestKoreanSurfaceForms:
    """Korean is agglutinative: the operator writes 웨이브*로*, not 웨이브."""

    @pytest.mark.parametrize(
        "query", ["웨이브로", "웨이브는", "웨이브가", "웨이브까지", "웨이브의", "웨이브만"]
    )
    def test_a_pattern_word_followed_by_a_particle_still_hits(self, query):
        # One case per particle, not a loop: a loop stops at the first failure,
        # so it can only ever prove the particle that happens to be first.
        assert resolve_pattern(query) == "wave"

    @pytest.mark.parametrize("query", ["웨이브로", "서클을"])
    def test_the_acceptance_particle_forms_resolve(self, query):
        # The two forms AC-FXLIB-005 names by hand.
        assert resolve_pattern(query) is not None

    @pytest.mark.parametrize("query", ["쓸어줘", "쓸어주세요", "쓸어줄래", "쓸어봐"])
    def test_a_verb_stem_followed_by_a_closed_ending_still_hits(self, query):
        # 쓸어 is a verb stem, and the ordinary field form conjugates it. The
        # ending list is CLOSED for the same reason the particle list is:
        # accepting any trailing syllable is substring matching wearing a hat.
        assert resolve_pattern(query) == "sweep"

    def test_the_acceptance_scenario_phrase_resolves_to_sweep(self, library):
        # 시나리오 1's live phrase, particle, adverb and conjugation included.
        phrase = "무버들 좌우로 부드럽게 쓸어줘"
        assert resolve_pattern(phrase) == "sweep"
        result = match_fx(phrase, library)
        assert result.selected is not None
        assert result.selected.fx_id == "sweep-slow-pan"
        assert result.fallback_reason is None

    @pytest.mark.parametrize("query", ["웨이브펌", "서클렌즈", "펄스타", "체이스보드"])
    def test_a_pattern_word_followed_by_a_non_particle_syllable_does_not_hit(self, query):
        # 웨이브 + 펌 is a different word, not 웨이브 + a particle.
        assert resolve_pattern(query) is None

    def test_the_non_particle_control_really_does_contain_the_word(self):
        # Non-vacuity: each stem above resolves once the trailing syllable goes.
        assert resolve_pattern("웨이브") == "wave"
        assert resolve_pattern("서클") == "circle"
        assert resolve_pattern("펄스") == "pulse"
        assert resolve_pattern("체이스") == "chase"


class TestMatchingIsByTokenNotBySubstring:
    """The repository's recurring hazard in the query axis: a term found inside
    a longer word. Here the live cases are English ``wave`` inside ``microwave``
    and ``chase`` inside ``purchase``, plus Korean 쓸어 inside 쓸어담아."""

    def test_microwave_does_not_contain_the_wave_pattern(self, library):
        assert resolve_pattern("microwave 켜줘") is None
        result = match_fx("microwave 켜줘", library)
        assert "wave-tilt" not in _ids(result)

    def test_purchase_does_not_contain_the_chase_pattern(self, library):
        assert resolve_pattern("purchase 목록 보여줘") is None
        assert "chase-color" not in _ids(match_fx("purchase 목록 보여줘", library))

    def test_the_substring_control_really_does_resolve_on_its_own(self):
        # Non-vacuity: the bare words are live terms, so the None above is the
        # boundary rule firing, not two absent aliases.
        assert resolve_pattern("wave") == "wave"
        assert resolve_pattern("chase") == "chase"

    @pytest.mark.parametrize("query", ["쓸어담아줘", "물결무늬 벽지"])
    def test_a_korean_term_inside_a_longer_word_does_not_hit(self, query):
        assert resolve_pattern(query) is None

    def test_a_decomposed_hangul_query_matches_the_same_fx(self, library):
        # macOS hands over NFD Hangul often enough to matter, and NFD 웨이브 is
        # a different string from NFC 웨이브 to every regex here.
        phrase = "물결치는 웨이브"
        composed = match_fx(unicodedata.normalize("NFC", phrase), library)
        decomposed = match_fx(unicodedata.normalize("NFD", phrase), library)
        assert composed.selected is not None
        assert decomposed.selected is not None
        assert decomposed.selected.fx_id == composed.selected.fx_id


class TestKoreanParticleParityWithLooks:
    def test_every_looks_particle_is_handled_here_too(self, library):
        # Drift guard. The looks list grew by a particle (이나) only when a test
        # went looking for it; this package must not have to relearn that.
        for particle in LOOKS_PARTICLES:
            assert resolve_pattern(f"웨이브{particle}") == "wave", particle

    def test_the_particle_parity_control_is_not_empty(self):
        assert len(LOOKS_PARTICLES) > 5


# --------------------------------------------------------------------------
# AC-FXLIB-005 — tie yields no selection, and the order is deterministic
# --------------------------------------------------------------------------


class TestTieYieldsNoSelection:
    """A tie is not a weak answer, it is the absence of one. Picking the first
    candidate anyway is the nearest-neighbour guess this SPEC keeps refusing."""

    def test_two_entries_of_the_named_pattern_tie_and_nothing_is_selected(self, library):
        result = match_fx("스윕", library)
        assert set(_ids(result)) == {"sweep-slow-pan", "sweep-fast-pan"}
        assert result.selected is None
        assert result.fallback_reason == LOW_CONFIDENCE

    def test_the_tie_is_not_broken_by_library_order(self, library):
        # A matcher that returns "the first candidate" would still return one
        # here — and would return a DIFFERENT one under each ordering. Both
        # halves have to hold.
        forward = match_fx("스윕", library)
        backward = match_fx("스윕", _reversed(library))
        assert forward.selected is None
        assert backward.selected is None
        assert _ids(forward) == _ids(backward)

    @pytest.mark.parametrize(
        ("query", "expected"),
        [("느린 스윕", "sweep-slow-pan"), ("질주", "sweep-fast-pan")],
    )
    def test_each_tied_entry_selects_on_its_own(self, query, expected, library):
        # Non-vacuity for the tie above: both entries are individually
        # selectable, so the None is a tie and not two failed lookups.
        result = match_fx(query, library)
        assert result.selected is not None
        assert result.selected.fx_id == expected
        assert result.fallback_reason is None

    def test_a_cross_pattern_tie_also_yields_no_selection(self, library):
        # 부드러운 sits on a sweep AND a wave entry. With no pattern named there
        # is nothing to choose between them.
        result = match_fx("부드러운", library)
        assert _patterns(result) == {"sweep", "wave"}
        assert result.selected is None
        assert result.fallback_reason == LOW_CONFIDENCE

    def test_the_same_mood_word_with_a_pattern_is_confident_again(self, library):
        # The constraint the user supplied is what makes the band meaningful.
        result = match_fx("부드러운 웨이브", library)
        assert result.selected is not None
        assert result.selected.fx_id == "wave-tilt"
        assert result.fallback_reason is None

    def test_a_sole_entry_of_the_named_pattern_is_selected(self, library):
        # The pattern axis has to be able to answer on its own, or naming a
        # pattern buys nothing.
        result = match_fx("서클", library)
        assert result.selected is not None
        assert result.selected.fx_id == "circle-ballyhoo"
        assert result.fallback_reason is None

    def test_more_evidence_beats_less_and_breaks_the_tie(self, library):
        # Non-vacuity for the tie rule: scores DO separate candidates when they
        # differ, so a tie is a real property of the query and not a matcher
        # that never selects. 부드러운 alone tied these two above; 물결치는 is
        # the second piece of evidence that only one of them carries.
        result = match_fx("부드러운 물결치는", library)
        assert result.pattern is None, "this case must not be decided by the pattern filter"
        assert _ids(result) == ["wave-tilt", "sweep-slow-pan"]
        assert result.matches[0].score > result.matches[1].score
        assert result.selected is not None
        assert result.selected.fx_id == "wave-tilt"


class TestDeterminism:
    def test_the_same_query_yields_the_same_result(self, library):
        first = match_fx("부드러운", library)
        second = match_fx("부드러운", library)
        assert _ids(first) == _ids(second)
        assert first.to_dict() == second.to_dict()

    def test_the_ranking_does_not_depend_on_library_order(self, library):
        # The sort key carries the fx id, so equal scores still land in one
        # fixed order. Without that, a tie would rank by insertion order and the
        # "same input, same output" contract would hold only by accident.
        forward = match_fx("부드러운", library)
        backward = match_fx("부드러운", _reversed(library))
        assert _ids(forward) == _ids(backward)
        assert forward.to_dict() == backward.to_dict()

    def test_the_order_control_really_is_a_different_library_order(self, library):
        ordered = [entry.fx_id for entry in library.fx]
        assert [entry.fx_id for entry in _reversed(library).fx] == list(reversed(ordered))

    def test_matching_does_not_mutate_the_library(self, library):
        before = copy.deepcopy(library)
        for query in ("부드러운", "스윕", "", "오늘 점심 뭐 먹지"):
            match_fx(query, library)
        assert library == before


# --------------------------------------------------------------------------
# AC-FXLIB-007 — the fallback signal
# --------------------------------------------------------------------------


class TestFallbackSignals:
    def test_the_three_reasons_are_distinct(self):
        assert len({EMPTY_QUERY, NO_MATCH, LOW_CONFIDENCE}) == 3

    @pytest.mark.parametrize("query", ["", "   ", "\n\t"])
    def test_an_empty_query_is_its_own_reason(self, query, library):
        result = match_fx(query, library)
        assert result.fallback_reason == EMPTY_QUERY
        assert result.matches == ()
        assert result.selected is None

    def test_an_unrelated_instruction_matches_nothing_and_says_so(self, library):
        result = match_fx("오늘 점심 뭐 먹지", library)
        assert result.matches == ()
        assert result.selected is None
        assert result.fallback_reason == NO_MATCH
        assert result.fallback is True

    def test_no_nearest_neighbour_is_offered_on_a_miss(self, library):
        # The failure this SPEC forbids: quietly returning "the closest fx".
        # The library is full and every entry is one term away, so a matcher
        # that force-returned its lowest-scoring candidate would show it here.
        result = match_fx("오늘 점심 뭐 먹지", library)
        assert _ids(result) == []
        assert result.to_dict()["matches"] == []
        assert result.to_dict()["total"] == 0
        assert result.to_dict()["selected"] is None

    def test_the_miss_control_really_does_run_against_a_full_library(self, library):
        # Non-vacuity: the empty result above is the query missing, not an
        # empty library.
        assert len(library.fx) >= 6
        assert match_fx("부드러운", library).matches != ()

    def test_a_low_confidence_result_still_reports_what_it_saw(self, library):
        # Honest reporting, not a selection: the tie is visible and `selected`
        # stays empty. Reading matches[0] as "the answer" is exactly the guess
        # `fallback_reason` exists to prevent.
        result = match_fx("부드러운", library)
        assert result.matches, "the tie must be reported, not swallowed"
        assert result.selected is None
        assert result.fallback is True

    @pytest.mark.parametrize(
        "query",
        ["", "   ", "오늘 점심 뭐 먹지", "부드러운", "스윕", "서클", "부드러운 웨이브"],
    )
    def test_a_fallback_is_reported_exactly_when_nothing_was_selected(self, query, library):
        # The invariant that keeps a mushy "no fallback, nothing selected"
        # state from existing: a caller can trust either field alone.
        result = match_fx(query, library)
        assert result.fallback is (result.selected is None)
        assert (result.fallback_reason is not None) is (result.selected is None)

    def test_the_selected_control_covers_both_sides(self, library):
        # Non-vacuity for the invariant above: the parametrised table really
        # does contain both a selecting and a non-selecting query.
        assert match_fx("서클", library).selected is not None
        assert match_fx("부드러운", library).selected is None


# --------------------------------------------------------------------------
# AC-FXLIB-006 — the library is the single source of truth
# --------------------------------------------------------------------------


class TestSingleSourceOfTruth:
    def test_every_returned_fx_comes_from_the_loaded_library(self, library):
        known = {entry.fx_id for entry in library.fx}
        for query in ("부드러운", "스윕", "서클", "wave", "빠른 스윕"):
            result = match_fx(query, library)
            assert set(_ids(result)) <= known, query
            if result.selected is not None:
                assert result.selected.fx_id in known

    def test_the_returned_fx_is_the_library_object_itself(self, library):
        result = match_fx("서클", library)
        assert isinstance(result.selected, Fx)
        assert result.selected is library.by_id("circle-ballyhoo")

    def test_an_fx_absent_from_the_injected_library_is_never_returned(self, library):
        # Matching reads ONLY what it was handed: shrink the library and the
        # entry disappears, so no second source can be feeding it.
        assert match_fx("서클", library).selected is not None
        without = FxLibrary(
            schema_version=library.schema_version,
            fx=tuple(entry for entry in library.fx if entry.fx_id != "circle-ballyhoo"),
        )
        result = match_fx("서클", without)
        assert "circle-ballyhoo" not in _ids(result)
        assert result.selected is None

    def test_a_pattern_the_library_does_not_carry_returns_no_entry(self):
        # The bridge resolves 웨이브 -> wave even when no wave entry exists.
        # That must surface as an honest miss, NOT as a manufactured entry and
        # NOT as the nearest sweep.
        sweep_only = _library(_fx("sweep-only", "sweep", mood_keywords=("부드러운",)))
        assert resolve_pattern("웨이브") == "wave"
        result = match_fx("웨이브", sweep_only)
        assert result.pattern == "wave"
        assert result.matches == ()
        assert result.selected is None
        assert result.fallback_reason == NO_MATCH

    def test_an_empty_library_answers_nothing_for_every_query(self):
        empty = _library()
        for query in ("서클", "부드러운", "웨이브로 돌려줘"):
            result = match_fx(query, empty)
            assert result.matches == ()
            assert result.selected is None
            assert result.fallback_reason == NO_MATCH, query

    def test_matching_is_a_pure_function_of_query_and_library(self, library):
        first = match_fx("부드러운 웨이브", library)
        second = match_fx("부드러운 웨이브", library)
        assert first.to_dict() == second.to_dict()


class TestScoringReadsTheEntrysOwnTerms:
    def test_a_mood_keyword_hit_scores_and_is_reported(self, library):
        result = match_fx("화려한", library)
        top = result.matches[0]
        assert top.fx.fx_id == "circle-ballyhoo"
        assert top.score == len(top.matched)
        assert "화려한" in top.matched

    def test_an_alias_hit_selects_its_fx(self, library):
        result = match_fx("상하 웨이브", library)
        assert result.selected is not None
        assert result.selected.fx_id == "wave-tilt"

    def test_a_display_name_query_finds_its_fx(self, library):
        result = match_fx("디머 펄스", library)
        assert result.selected is not None
        assert result.selected.fx_id == "pulse-dimmer"

    def test_the_pattern_slug_is_itself_a_match_term(self, library):
        # A model that read `"pattern": "wave"` out of a previous tool result
        # will type it back verbatim; that has to score, not just filter.
        result = match_fx("wave", library)
        assert result.selected is not None
        assert result.selected.fx_id == "wave-tilt"
        assert "wave" in result.matches[0].matched

    def test_a_term_repeated_across_two_axes_is_counted_once(self):
        # A display name is usually also an alias; counting it twice would
        # inflate that entry's score for no extra evidence.
        doubled = _library(
            _fx(
                "wave-doubled",
                "wave",
                display_name="틸트 웨이브",
                aliases=("틸트 웨이브",),
                mood_keywords=("틸트 웨이브",),
            ),
            _fx("wave-plain", "wave", display_name="플레인", mood_keywords=("틸트 웨이브",)),
        )
        result = match_fx("틸트 웨이브", doubled)
        assert result.selected is None, "double counting would break the tie"
        assert {scored.score for scored in result.matches} == {1}

    def test_words_that_match_nothing_are_ignored_not_penalised(self, library):
        plain = match_fx("화려한", library)
        padded = match_fx("오늘은 화려한 느낌이면 좋겠어", library)
        assert plain.selected is not None
        assert padded.selected is not None
        assert padded.selected.fx_id == plain.selected.fx_id


# --------------------------------------------------------------------------
# The tool-facing surface
# --------------------------------------------------------------------------


class TestToDictSurface:
    def test_the_result_carries_the_keys_the_tool_layer_reads(self, library):
        payload = match_fx("서클", library).to_dict()
        assert set(payload) == {
            "query",
            "pattern",
            "selected",
            "fallback",
            "fallback_reason",
            "total",
            "truncated",
            "matches",
        }
        assert payload["selected"] == "circle-ballyhoo"
        assert payload["fallback"] is False
        assert payload["fallback_reason"] is None

    def test_each_match_carries_the_evidence_that_put_it_there(self, library):
        payload = match_fx("화려한", library).to_dict()
        entry = payload["matches"][0]
        assert set(entry) == {
            "fx_id",
            "display_name",
            "pattern",
            "attributes",
            "speed",
            "reverse",
            "score",
            "matched",
        }
        assert entry["fx_id"] == "circle-ballyhoo"
        assert entry["matched"] == ["화려한"]

    def test_a_cut_list_is_never_presented_as_a_complete_one(self):
        crowded = _library(
            *(
                _fx(f"sweep-{index:02d}", "sweep", mood_keywords=("공통",))
                for index in range(MAX_TOOL_MATCHES + 3)
            )
        )
        result = match_fx("공통", crowded)
        payload = result.to_dict()
        assert payload["total"] == MAX_TOOL_MATCHES + 3
        assert len(payload["matches"]) == MAX_TOOL_MATCHES
        assert payload["truncated"] is True

    def test_an_uncut_list_says_it_is_complete(self, library):
        payload = match_fx("스윕", library).to_dict()
        assert payload["total"] == 2
        assert payload["truncated"] is False

    def test_the_limit_is_explicit_and_honoured(self, library):
        payload = match_fx("스윕", library).to_dict(limit=1)
        assert len(payload["matches"]) == 1
        assert payload["total"] == 2
        assert payload["truncated"] is True


# --------------------------------------------------------------------------
# Purity — no transport, no provider, no orchestrator
# --------------------------------------------------------------------------


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

    def test_matching_imports_only_stdlib_and_its_own_schema(self):
        imported = _imported_modules(FX_DIR / "matching.py")
        assert imported, "non-vacuity: the module must import something"
        project = [name for name in imported if name.split(".")[0] == "server"]
        assert project, "non-vacuity: the schema import must be visible to this scan"
        assert all(name.startswith("server.fx.") for name in project), project

    def test_matching_reaches_no_transport_provider_or_tool_registry(self):
        imported = _imported_modules(FX_DIR / "matching.py")
        for forbidden in ("server.bridge", "pythonosc", "server.llm", "server.orchestrator"):
            assert not any(name.startswith(forbidden) for name in imported), forbidden

    def test_no_provider_name_appears_in_the_matching_surface(self):
        text = (FX_DIR / "matching.py").read_text(encoding="utf-8").casefold()
        assert [token for token in self._FORBIDDEN if token in text] == []

    def test_the_provider_scan_is_not_vacuous(self):
        # The same scan over a module that DOES name a provider must fire.
        factory = Path(__file__).resolve().parents[1] / "llm" / "factory.py"
        text = factory.read_text(encoding="utf-8").casefold()
        assert any(token in text for token in self._FORBIDDEN)
