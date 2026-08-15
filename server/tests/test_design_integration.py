"""End-to-end pure-flow integration test for the M1 song design standard
foundations (SPEC-COPILOT-SONGSTD-001) — wires ``profile.py`` (R1),
``rig.py`` (R1b), ``energy.py`` (R2), and ``lint.py`` (R3) together the way a
real caller would chain them: an explicit :class:`MusicProfile`, one
:class:`RigProfile`, :func:`resolve_section`, :func:`axis_budget`, and
:func:`lint_sheet`.

Each module already has its own focused unit-test file; this file only
exercises the seams between them — director-override precedence surviving
into the resolved triple, a single-tier rig's RG1 degradation surfacing as
an audited (not flagged) L6/L7 disablement, and the Seq 114 flat-100%
regression still tripping L2 once the whole chain is wired end to end.
"""

from __future__ import annotations

from server.design.energy import EFFECT_AXIS_CAPABILITY, axis_budget
from server.design.lint import LintCue, LintSection, LintSheet, lint_sheet
from server.design.profile import (
    SOURCE_DIRECTOR_INTENT,
    SOURCE_SECTION_MOOD,
    DirectorOverride,
    MusicProfile,
    SectionMoodResolution,
    resolve_section,
)
from server.design.rig import RigProfile, build_rig_profile


def _single_tier_rig() -> RigProfile:
    """One rig: 8 fixtures declaring the effect capability, but no group
    names and no declared layers — the RG1 single-layer degradation path,
    so L6/L7 must disable (audited) rather than fire (flagged)."""
    patch = [
        {"fid": fid, "type_name": "Sharpy", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 9)
    ]
    return build_rig_profile(patch=patch, groups={}, coords=[])


class TestEndToEndPureFlow:
    def test_full_chain_from_profile_through_lint(self):
        profile = MusicProfile(bpm=128.0, genre="록", palette=("레드", "화이트"))
        rig = _single_tier_rig()
        assert rig.layer_rules_active() is False  # single-tier: RG1 degrades

        # Finale section: the standard's own "웅장한 피날레" worked example,
        # but the director overrides D level down from the matched D5 to
        # D4 — the override must win over the matched section-mood entry
        # for the axis it actually covers, while the un-overridden axes
        # (color, position) still come from the matched section mood.
        override = DirectorOverride(d_level=4)
        finale = resolve_section("웅장한 피날레 연출", profile, director_intent=override)
        assert isinstance(finale, SectionMoodResolution)
        assert finale.d_level == 4
        assert finale.d_source == SOURCE_DIRECTOR_INTENT
        assert finale.color_tendency == "쿨 볼드"
        assert finale.color_source == SOURCE_SECTION_MOOD

        # Verse section: no director involvement — resolves purely from the
        # section mood-word.
        verse = resolve_section("잔잔한 발라드 느낌", profile)
        assert isinstance(verse, SectionMoodResolution)
        assert verse.d_level == 2
        assert verse.d_source == SOURCE_SECTION_MOOD

        finale_budget = axis_budget(finale.d_level, profile, rig)
        verse_budget = axis_budget(verse.d_level, profile, rig)
        assert finale_budget.dimmer_pct[0] >= verse_budget.dimmer_pct[0]
        assert finale_budget.fx_axes > 0  # rig declares the effect capability

        sections = (LintSection(index=0, name="Verse"), LintSection(index=1, name="Finale"))
        cues = (
            LintCue(
                cue_no=0,
                section_index=0,
                d_level=verse.d_level,
                fade_seconds=verse_budget.fade_seconds[0],
                key_dimmer_pct=verse_budget.dimmer_pct[0],
                position_label=verse.position_candidates[0],
                position_width="narrow",
                palette_colors=("레드",),
            ),
            LintCue(
                cue_no=1,
                section_index=1,
                d_level=finale.d_level,
                fade_seconds=finale_budget.fade_seconds[0],
                key_dimmer_pct=finale_budget.dimmer_pct[0],
                position_label=finale.position_candidates[0],
                position_width="wide",
                palette_colors=("화이트",),
                effect_axis_count=finale_budget.fx_axes,
            ),
        )
        sheet = LintSheet(sections=sections, cues=cues)
        report = lint_sheet(sheet, profile, rig)

        finding_rules = {f.rule_id for f in report.findings}
        assert "L2" not in finding_rules  # both dimmers sit inside their own D-level budget
        assert "L6" not in finding_rules
        assert "L7" not in finding_rules
        disabled_ids = {note.rule_id for note in report.disabled_rules}
        assert disabled_ids == {"L6", "L7"}  # single-tier rig: audited, never flagged

    def test_seq114_all_100_percent_sequence_is_still_l2(self):
        """The Seq 114 regression must still surface through the full
        chain: a cue sheet pinned at 100% key dimmer across D2-D5 is a
        violation even though nothing in it ever literally decreases."""
        profile = MusicProfile(bpm=128.0)
        rig = _single_tier_rig()
        sections = (LintSection(index=0, name="Full Set"),)
        cues = tuple(
            LintCue(
                cue_no=float(i),
                section_index=0,
                d_level=d,
                fade_seconds=0.5,
                key_dimmer_pct=100.0,
            )
            for i, d in enumerate((2, 3, 4, 5))
        )
        sheet = LintSheet(sections=sections, cues=cues)
        report = lint_sheet(sheet, profile, rig)
        assert "L2" in {f.rule_id for f in report.findings}
