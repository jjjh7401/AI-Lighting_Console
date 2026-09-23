"""SPEC-COPILOT-COLORMODE-001 M2 — Q2B_COLOR_USAGE reflected in the actual
section-palette computation (spec.md §2 D5, plan.md §C M2).

(i) modulate (default) is byte-identical to the pre-SPEC `_arc_palette`
    behaviour — the existing t402/t403/t405/t406 regression fixtures already
    prove this for the production call path (`_build_unified_song_plan`
    with no Q2B answer); this file additionally proves it at the
    `_section_palette_choice` unit level with an EXPLICIT "modulate" value,
    so the two paths (implicit default vs explicit confirmed answer) are
    both pinned.
(ii) single returns the palette_mode-resolved base, unmodified, for every
     role/occurrence — including the palette_mode="concept" case (AC-012).
(iii) per_chorus assigns chorus/finale occurrences the SAME accent across
      every occurrence (카드 t439, REQ-LDDESIGN-004/030 supersedes the
      original REQ-014 "differs between consecutive occurrences" behavior),
      while base[0] (primary) stays first; a role with exactly one
      occurrence in the song matches modulate (AC-013).
"""

from __future__ import annotations

from server.design.profile import MusicProfile
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import (
    _arc_palette,
    _section_palette_choice,
    _section_palette_sizes,
    _split_sections_for_density,
)


def _section(mood: str = "") -> PositionSheetSection:
    return PositionSheetSection(name="S", start_ms=0, mood=mood)


def _choice(
    *,
    role: str,
    color_usage: str,
    occurrence: int = 1,
    profile: MusicProfile | None = None,
    palette_mode: str = "palette",
    concept_colors: tuple[str, ...] = (),
    color_tendency: object = "블루",
):
    return _section_palette_choice(
        _section(),
        role=role,
        profile=profile or MusicProfile(palette=("블루",)),
        color_tendency=color_tendency,
        palette_mode=palette_mode,
        concept_colors=concept_colors,
        occurrence=occurrence,
        color_usage=color_usage,
    )


class TestModulateIsByteIdenticalToPreSpec:
    """AC-COLORMODE-011 (REQ-012)."""

    def test_modulate_matches_arc_palette_directly_for_every_occurrence(self):
        profile = MusicProfile(palette=("블루",))
        for occurrence in range(1, 6):
            colors, source, weight = _choice(
                role="chorus", color_usage="modulate", occurrence=occurrence, profile=profile
            )
            expected = _arc_palette(("블루",), "chorus", occurrence)
            assert colors == expected
            assert source == "section_arc"

    def test_modulate_is_the_default_when_color_usage_is_omitted(self):
        profile = MusicProfile(palette=("블루",))
        explicit = _section_palette_choice(
            _section(),
            role="chorus",
            profile=profile,
            color_tendency="블루",
            palette_mode="palette",
            concept_colors=(),
            occurrence=3,
            color_usage="modulate",
        )
        implicit = _section_palette_choice(
            _section(),
            role="chorus",
            profile=profile,
            color_tendency="블루",
            palette_mode="palette",
            concept_colors=(),
            occurrence=3,
        )
        assert explicit == implicit


class TestSingleReturnsBaseEverywhere:
    """AC-COLORMODE-012 (REQ-013)."""

    def test_single_returns_the_q2_base_unmodified_across_occurrences(self):
        profile = MusicProfile(palette=("블루", "화이트"))
        for occurrence in range(1, 5):
            colors, source, weight = _choice(
                role="chorus", color_usage="single", occurrence=occurrence, profile=profile
            )
            assert colors == ("블루", "화이트")
            assert source == "section_single"
            assert weight is None

    def test_single_returns_concept_base_when_palette_mode_is_concept(self):
        colors, source, _weight = _choice(
            role="chorus",
            color_usage="single",
            palette_mode="concept",
            concept_colors=("엘로우", "그린"),
        )
        assert colors == ("엘로우", "그린")
        assert source == "section_single"

    def test_single_direct_section_color_still_wins_over_everything(self):
        colors, source, _weight = _section_palette_choice(
            _section(mood="레드로 강조"),
            role="chorus",
            profile=MusicProfile(palette=("블루",)),
            color_tendency="블루",
            palette_mode="palette",
            concept_colors=(),
            color_usage="single",
        )
        assert source == "section_text"
        assert "레드" in colors


class TestPerChorusIdentityAcrossOccurrences:
    """AC-COLORMODE-013 (REQ-014) — 카드 t439(REQ-LDDESIGN-004/030)로 뒤집힘.

    이전 이름 `TestPerChorusConsecutiveAccentsDiffer`/
    `test_per_chorus_consecutive_accents_differ` 는 REQ-014 시절 "연속
    회차는 액센트가 달라야 한다"를 검증했다. REQ-LDDESIGN-004/030 이
    "후렴(chorus) 구간 전체는 동일한 주색을 유지한다"를 요구하면서 그
    성질 자체가 결함으로 재분류됐다 — `per_chorus` 는 이제 `modulate`
    와 바이트 동일하게 항등이다(자세한 근거:
    `test_chorus_color_identity_t439.py`)."""

    def test_per_chorus_occurrences_are_identical(self):
        profile = MusicProfile(palette=("블루",))
        results = [
            _choice(role="chorus", color_usage="per_chorus", occurrence=n, profile=profile)
            for n in range(1, 6)
        ]
        colors_by_occurrence = [colors for colors, _source, _weight in results]
        first = colors_by_occurrence[0]
        for later in colors_by_occurrence[1:]:
            assert later == first, "REQ-004/030: per_chorus 회차 간 색이 항등이어야 한다"
        for colors, _source, _weight in results:
            assert colors[0] == "블루"  # primary always first

    def test_per_chorus_source_label_is_distinct(self):
        _colors, source, _weight = _choice(role="chorus", color_usage="per_chorus", occurrence=2)
        assert source == "section_per_chorus"

    def test_per_chorus_single_occurrence_matches_modulate(self):
        """A role occurring exactly once has no adjacent occurrence to
        differ from — its output (the palette tuple) must equal modulate's
        for that occurrence. The source label may still distinguish
        per_chorus from modulate for traceability (research.md §6)."""
        profile = MusicProfile(palette=("블루",))
        per_chorus_colors, _pc_source, per_chorus_weight = _choice(
            role="finale", color_usage="per_chorus", occurrence=1, profile=profile
        )
        modulate_colors, _mod_source, modulate_weight = _choice(
            role="finale", color_usage="modulate", occurrence=1, profile=profile
        )
        assert per_chorus_colors == modulate_colors
        assert per_chorus_weight == modulate_weight

    def test_non_chorus_finale_roles_stay_on_modulate_behaviour_under_per_chorus(self):
        profile = MusicProfile(palette=("블루",))
        per_chorus = _choice(role="verse", color_usage="per_chorus", occurrence=3, profile=profile)
        modulate = _choice(role="verse", color_usage="modulate", occurrence=3, profile=profile)
        assert per_chorus == modulate


def _chorus_sections(count: int, *, gap_ms: int = 40_000) -> list[PositionSheetSection]:
    return [
        PositionSheetSection(name=f"Chorus {i + 1}", start_ms=i * gap_ms, mood="", role="chorus")
        for i in range(count)
    ]


class TestColorUsageAffectsQueueDensity:
    """sync-audit.md F5 — measured, not guessed. `_section_palette_sizes`
    reports `len(colors)` per section, and `plan_cue_density` caps a
    section's split count to its palette size (never splitting a
    single-color section, per `cue_density.py`'s own "2 미만인 구간은
    쪼개지 않는다" contract). `single` returns exactly ``len(profile.palette)``
    colors (no accent), which is fewer than modulate's 2-color
    (primary+accent) output — so `single` measurably reduces both the
    reported palette size AND the actual queue split count.
    `per_chorus` reuses the same 2-color (primary+accent) shape as
    modulate for every occurrence, so — measured below — it produces the
    IDENTICAL palette sizes and split count as modulate for this fixture;
    it changes WHICH accent color is used, not HOW MANY.
    """

    def test_single_reduces_palette_sizes_versus_modulate(self):
        sections = _chorus_sections(4)
        profile = MusicProfile(palette=("블루",))
        modulate_sizes = _section_palette_sizes(
            sections,
            profile=profile,
            palette_mode="palette",
            concept_colors=(),
            color_usage="modulate",
        )
        single_sizes = _section_palette_sizes(
            sections,
            profile=profile,
            palette_mode="palette",
            concept_colors=(),
            color_usage="single",
        )
        assert modulate_sizes == [2, 2, 2, 2]
        assert single_sizes == [1, 1, 1, 1]
        assert single_sizes != modulate_sizes

    def test_per_chorus_reports_the_same_palette_sizes_as_modulate(self):
        """Measured equality, not an assumption: per_chorus varies the
        accent COLOR per occurrence but not the accent COUNT, so its sizes
        match modulate's exactly for this fixture."""
        sections = _chorus_sections(4)
        profile = MusicProfile(palette=("블루",))
        modulate_sizes = _section_palette_sizes(
            sections,
            profile=profile,
            palette_mode="palette",
            concept_colors=(),
            color_usage="modulate",
        )
        per_chorus_sizes = _section_palette_sizes(
            sections,
            profile=profile,
            palette_mode="palette",
            concept_colors=(),
            color_usage="per_chorus",
        )
        assert per_chorus_sizes == modulate_sizes == [2, 2, 2, 2]

    def test_single_reduces_the_actual_cue_split_count_versus_modulate(self):
        """`single`'s single-color sections (size 1, below the "2 미만인
        구간은 쪼개지 않는다" split floor) stay unsplit, while modulate's
        2-color sections split into 2 units each (BPM 120, 4/4, 40s gap ==
        2.5 bar-units of 8 bars each) — a real, observable queue-count
        difference, not a pass-through."""
        sections = _chorus_sections(3, gap_ms=40_000)
        profile = MusicProfile(bpm=120.0, meter="4/4", palette=("블루",))
        modulate_expanded, _origins, _notes = _split_sections_for_density(
            sections,
            profile=profile,
            palette_mode="palette",
            concept_colors=(),
            color_usage="modulate",
        )
        single_expanded, _origins, _notes = _split_sections_for_density(
            sections,
            profile=profile,
            palette_mode="palette",
            concept_colors=(),
            color_usage="single",
        )
        assert (
            len(modulate_expanded) == 5
        )  # Chorus 1/2 split into 2 units each, Chorus 3 (last, no end) stays 1
        assert (
            len(single_expanded) == 3
        )  # every section capped to 1 unit — single color, no distinct variant
        assert len(single_expanded) < len(modulate_expanded)

    def test_per_chorus_produces_the_same_cue_split_count_as_modulate(self):
        sections = _chorus_sections(3, gap_ms=40_000)
        profile = MusicProfile(bpm=120.0, meter="4/4", palette=("블루",))
        modulate_expanded, _origins, _notes = _split_sections_for_density(
            sections,
            profile=profile,
            palette_mode="palette",
            concept_colors=(),
            color_usage="modulate",
        )
        per_chorus_expanded, _origins, _notes = _split_sections_for_density(
            sections,
            profile=profile,
            palette_mode="palette",
            concept_colors=(),
            color_usage="per_chorus",
        )
        assert len(per_chorus_expanded) == len(modulate_expanded) == 5
