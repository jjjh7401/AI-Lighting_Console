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
(iii) per_chorus assigns chorus/finale occurrences accents that differ
      between consecutive occurrences, while base[0] (primary) stays first;
      a role with exactly one occurrence in the song matches modulate
      (AC-013).
"""

from __future__ import annotations

from server.design.profile import MusicProfile
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import _arc_palette, _section_palette_choice


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


class TestPerChorusConsecutiveAccentsDiffer:
    """AC-COLORMODE-013 (REQ-014)."""

    def test_per_chorus_consecutive_accents_differ(self):
        profile = MusicProfile(palette=("블루",))
        results = [
            _choice(role="chorus", color_usage="per_chorus", occurrence=n, profile=profile)
            for n in range(1, 6)
        ]
        colors_by_occurrence = [colors for colors, _source, _weight in results]
        for earlier, later in zip(colors_by_occurrence, colors_by_occurrence[1:], strict=False):
            assert earlier != later
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
