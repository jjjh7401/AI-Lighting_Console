"""Music profile + unified mood dictionary — priority chain, no-guess
contract, BPM default/validation, and keyword-uniqueness invariants
(SPEC-COPILOT-SONGSTD-001 M1, REQ R1)."""

import dataclasses

import pytest

from server.design.profile import (
    CONCEPT_SEED_TABLE,
    DEFAULT_BPM,
    GENRE_DEFAULT_TABLE,
    GLOBAL_DEFAULT_COLOR_TENDENCY,
    GLOBAL_DEFAULT_D_LEVEL,
    SOURCE_CONCEPT,
    SOURCE_DIRECTOR_INTENT,
    SOURCE_GENRE,
    SOURCE_GLOBAL_DEFAULT,
    SOURCE_SECTION_MOOD,
    UNIFIED_MOOD_TABLE,
    DirectorOverride,
    MusicProfile,
    ProfileError,
    SectionMoodResolution,
    UnresolvedMood,
    resolve_section,
)
from server.spatial.pointing import BASIC_POSITION_SEQUENCE


class TestMusicProfile:
    def test_defaults_are_neutral(self):
        profile = MusicProfile()
        assert profile.bpm is None
        assert profile.meter == "4/4"
        assert profile.genre is None
        assert profile.concept is None
        assert profile.palette == ()

    def test_missing_bpm_falls_back_to_120_and_discloses_it(self):
        profile = MusicProfile()
        assert profile.effective_bpm == DEFAULT_BPM == 120.0
        assert profile.bpm_is_default is True

    def test_declared_bpm_is_used_verbatim_and_disclosed_as_not_default(self):
        profile = MusicProfile(bpm=128)
        assert profile.effective_bpm == 128
        assert profile.bpm_is_default is False

    @pytest.mark.parametrize("bad_bpm", [0, -1, -128.5])
    def test_non_positive_bpm_is_rejected(self, bad_bpm):
        with pytest.raises(ProfileError):
            MusicProfile(bpm=bad_bpm)

    def test_non_numeric_bpm_is_rejected(self):
        with pytest.raises(ProfileError):
            MusicProfile(bpm="fast")

    def test_bool_bpm_is_rejected(self):
        # bool is a numeric subtype in Python; the standard's "BPM" is a
        # tempo, not a flag — reject it explicitly rather than silently
        # accepting bpm=True as bpm=1.
        with pytest.raises(ProfileError):
            MusicProfile(bpm=True)

    def test_profile_is_immutable(self):
        profile = MusicProfile(bpm=140)
        with pytest.raises(dataclasses.FrozenInstanceError):
            profile.bpm = 100  # type: ignore[misc]


class TestUnifiedMoodTableContract:
    def test_every_entry_labels_a_canonical_position(self):
        names = set(BASIC_POSITION_SEQUENCE)
        for entry in UNIFIED_MOOD_TABLE:
            assert entry.label in names
            for candidate in entry.position_candidates:
                assert candidate in names

    def test_keywords_never_overlap_between_entries(self):
        seen: dict[str, str] = {}
        for entry in UNIFIED_MOOD_TABLE:
            for keyword in entry.keywords:
                assert keyword not in seen, (
                    f"{keyword!r} appears in both {seen.get(keyword)!r} and {entry.label!r}"
                )
                seen[keyword] = entry.label

    def test_every_entry_carries_a_d_level_in_range(self):
        for entry in UNIFIED_MOOD_TABLE:
            assert 1 <= entry.d_level <= 5

    def test_every_entry_carries_a_color_tendency_and_reason(self):
        for entry in UNIFIED_MOOD_TABLE:
            assert entry.color_tendency
            assert entry.reason

    def test_concept_seed_position_bias_is_canonical(self):
        names = set(BASIC_POSITION_SEQUENCE)
        for seed in CONCEPT_SEED_TABLE:
            for candidate in seed.position_bias:
                assert candidate in names

    def test_worked_example_grand_finale_is_d5_cool_bold_ring_in(self):
        # 표준 §2b M4 예시: "웅장한 피날레" → D5 + 쿨 볼드 + Ring In.
        entry = next(e for e in UNIFIED_MOOD_TABLE if e.label == "Ring In")
        assert entry.d_level == 5
        assert entry.color_tendency == "쿨 볼드"

    def test_worked_example_quiet_ballad_is_d2_blue_warm_white_vocal_dsc(self):
        # 표준 §2b M4 예시: "잔잔한 발라드" → D2 + 블루/웜화이트 + Vocal DSC.
        entry = next(e for e in UNIFIED_MOOD_TABLE if e.label == "Vocal DSC")
        assert entry.d_level == 2
        assert entry.color_tendency == "블루/웜화이트"


class TestResolveSectionTupleOutput:
    def test_grand_finale_resolves_the_full_triple_from_section_mood(self):
        result = resolve_section("웅장한 피날레 연출", MusicProfile())
        assert isinstance(result, SectionMoodResolution)
        assert result.as_tuple() == (5, "쿨 볼드", ("Ring In", "Center", "Wall"))
        assert result.d_source == SOURCE_SECTION_MOOD
        assert result.color_source == SOURCE_SECTION_MOOD
        assert result.position_source == SOURCE_SECTION_MOOD
        assert set(result.matched_keywords) == {"웅장", "피날레"}

    def test_quiet_ballad_resolves_vocal_dsc(self):
        result = resolve_section("잔잔한 발라드 느낌", MusicProfile())
        assert isinstance(result, SectionMoodResolution)
        d_level, color, positions = result.as_tuple()
        assert d_level == 2
        assert color == "블루/웜화이트"
        assert positions[0] == "Vocal DSC"


class TestPriorityChain:
    def test_section_mood_beats_genre_on_a_metal_ballad_bridge(self):
        # spec.md M2 worked example: "메탈 곡의 발라드 브릿지는 브릿지 무드가
        # 우선" — genre="메탈" must NOT win over the section's own mood-word.
        profile = MusicProfile(genre="메탈")
        result = resolve_section("브릿지, 발라드 느낌으로 잔잔하게", profile)
        assert isinstance(result, SectionMoodResolution)
        assert result.d_level == 2
        assert result.color_tendency == "블루/웜화이트"
        assert result.color_source == SOURCE_SECTION_MOOD

    def test_concept_beats_genre_when_no_section_mood_is_given(self):
        profile = MusicProfile(genre="메탈", concept="우주")
        result = resolve_section(None, profile)
        assert isinstance(result, SectionMoodResolution)
        assert result.color_tendency == "블루/퍼플"
        assert result.color_source == SOURCE_CONCEPT
        assert result.position_candidates == ("Ring In",)
        assert result.position_source == SOURCE_CONCEPT
        # No section mood and no director d_level -> D has no concept/genre
        # rung (module contract), falls straight to the global default.
        assert result.d_level == GLOBAL_DEFAULT_D_LEVEL
        assert result.d_source == SOURCE_GLOBAL_DEFAULT

    def test_genre_wins_when_concept_is_absent(self):
        profile = MusicProfile(genre="edm")
        result = resolve_section("", profile)
        assert isinstance(result, SectionMoodResolution)
        assert result.color_source == SOURCE_GENRE
        assert result.color_tendency == GENRE_DEFAULT_TABLE[2].color_tendency
        assert result.position_candidates == ()
        assert result.position_source == SOURCE_GLOBAL_DEFAULT

    def test_global_default_when_nothing_else_applies(self):
        result = resolve_section(None, MusicProfile())
        assert isinstance(result, SectionMoodResolution)
        assert result.as_tuple() == (GLOBAL_DEFAULT_D_LEVEL, GLOBAL_DEFAULT_COLOR_TENDENCY, ())
        assert result.d_source == SOURCE_GLOBAL_DEFAULT
        assert result.color_source == SOURCE_GLOBAL_DEFAULT
        assert result.position_source == SOURCE_GLOBAL_DEFAULT

    def test_director_intent_overrides_a_single_axis_only(self):
        override = DirectorOverride(d_level=5)
        result = resolve_section("잔잔한 발라드", MusicProfile(), director_intent=override)
        assert isinstance(result, SectionMoodResolution)
        assert result.d_level == 5
        assert result.d_source == SOURCE_DIRECTOR_INTENT
        # The un-overridden axes still come from the matched section mood.
        assert result.color_tendency == "블루/웜화이트"
        assert result.color_source == SOURCE_SECTION_MOOD

    def test_complete_director_override_bypasses_an_unmatched_mood_text(self):
        override = DirectorOverride(
            d_level=4, color_tendency="테스트 색", position_candidates=("Center",)
        )
        result = resolve_section(
            "알아들을 수 없는 이상한 문장", MusicProfile(), director_intent=override
        )
        assert isinstance(result, SectionMoodResolution)
        assert result.as_tuple() == (4, "테스트 색", ("Center",))
        assert result.d_source == SOURCE_DIRECTOR_INTENT
        assert result.color_source == SOURCE_DIRECTOR_INTENT
        assert result.position_source == SOURCE_DIRECTOR_INTENT


class TestUnresolvedMoodNoGuess:
    def test_unmatched_mood_text_is_reported_not_guessed(self):
        result = resolve_section("이해할 수 없는 외계어 문장", MusicProfile(genre="팝"))
        assert isinstance(result, UnresolvedMood)
        assert result.reason == "no_keyword_match"

    def test_ambiguous_mood_text_is_reported_not_guessed(self):
        # "발라드" (Vocal DSC) and "오프닝" (Center) each match exactly once —
        # a genuine cross-entry tie, not resolved by table order.
        result = resolve_section("발라드풍 오프닝 연출", MusicProfile())
        assert isinstance(result, UnresolvedMood)
        assert result.reason == "ambiguous_keyword_match"
        assert set(result.tied_labels) == {"Vocal DSC", "Center"}

    def test_partial_director_override_does_not_suppress_the_no_guess_report(self):
        override = DirectorOverride(d_level=5)  # incomplete — 2 axes still unresolved
        result = resolve_section(
            "이해할 수 없는 외계어 문장", MusicProfile(), director_intent=override
        )
        assert isinstance(result, UnresolvedMood)

    def test_blank_mood_text_is_not_a_mismatch(self):
        # No mood-word given at all is not the same as a mismatched one —
        # the chain simply proceeds to concept/genre/global-default.
        result = resolve_section("   ", MusicProfile())
        assert isinstance(result, SectionMoodResolution)
        assert result.d_source == SOURCE_GLOBAL_DEFAULT
