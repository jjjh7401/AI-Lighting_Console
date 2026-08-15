"""Tests for server/design/lint.py (SPEC-COPILOT-SONGSTD-001, M1, R3).

One pass/fail pair per implemented L1-L14 rule, the Seq 114 regression (a
cue sheet held flat at 100% key dimmer across D2-D5 must yield L2 even
though it never literally *decreases*), intentional-violation tag
suppression (a tag suppresses only its own rule), and the two disabled-rule
paths this milestone wires: L6/L7 on a single-layer rig (RG1) and L11
without a declared BPM (spec.md R3's R clause).
"""

from __future__ import annotations

import pytest

from server.design.lint import (
    LINT_RULE_IDS,
    LintCue,
    LintFinding,
    LintSection,
    LintSheet,
    LintSheetError,
    lint_sheet,
)
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile

_SINGLE_LAYER_RIG = build_rig_profile(patch=[], groups={}, coords=[])
_DUAL_LAYER_RIG = build_rig_profile(
    patch=[],
    groups={},
    coords=[],
    declared_layers={"key": [1, 2], "back": [3, 4]},
)
_NO_BPM = MusicProfile()
_WITH_BPM = MusicProfile(bpm=120.0)


def _sheet(cues: list[LintCue], *, section_count: int = 1) -> LintSheet:
    sections = tuple(LintSection(index=i, name=f"S{i}") for i in range(section_count))
    return LintSheet(sections=sections, cues=tuple(cues))


def _rule_ids(findings: tuple[LintFinding, ...]) -> set[str]:
    return {finding.rule_id for finding in findings}


def _disabled_ids(sheet: LintSheet, profile: MusicProfile, rig) -> set[str]:
    return {note.rule_id for note in lint_sheet(sheet, profile, rig).disabled_rules}


# ---------------------------------------------------------------------------
# Structural input validation
# ---------------------------------------------------------------------------


class TestLintCueValidation:
    def test_rejects_out_of_range_d_level(self):
        with pytest.raises(LintSheetError):
            LintCue(cue_no=1, section_index=0, d_level=6, fade_seconds=1.0)

    def test_rejects_unknown_tag(self):
        with pytest.raises(LintSheetError):
            LintCue(
                cue_no=1,
                section_index=0,
                d_level=1,
                fade_seconds=1.0,
                tags=frozenset({"L99"}),
            )

    def test_rejects_out_of_range_key_dimmer(self):
        with pytest.raises(LintSheetError):
            LintCue(cue_no=1, section_index=0, d_level=1, fade_seconds=1.0, key_dimmer_pct=101.0)

    def test_rejects_negative_fade(self):
        with pytest.raises(LintSheetError):
            LintCue(cue_no=1, section_index=0, d_level=1, fade_seconds=-0.5)

    def test_rejects_unknown_position_width(self):
        with pytest.raises(LintSheetError):
            LintCue(
                cue_no=1,
                section_index=0,
                d_level=1,
                fade_seconds=1.0,
                position_width="huge",
            )


class TestLintSheetValidation:
    def test_rejects_cue_referencing_missing_section(self):
        with pytest.raises(LintSheetError):
            LintSheet(
                sections=(LintSection(index=0, name="S0"),),
                cues=(LintCue(cue_no=1, section_index=5, d_level=1, fade_seconds=1.0),),
            )

    def test_rejects_out_of_order_cues(self):
        with pytest.raises(LintSheetError):
            LintSheet(
                sections=(LintSection(index=0, name="S0"),),
                cues=(
                    LintCue(cue_no=2, section_index=0, d_level=1, fade_seconds=1.0),
                    LintCue(cue_no=1, section_index=0, d_level=1, fade_seconds=1.0),
                ),
            )

    def test_all_fourteen_rule_ids_are_registered(self):
        assert tuple(f"L{n}" for n in range(1, 15)) == LINT_RULE_IDS


# ---------------------------------------------------------------------------
# L1 — 구간당 큐 >= 1 (T1)
# ---------------------------------------------------------------------------


class TestL1SectionHasACue:
    def test_pass_every_section_has_a_cue(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=2, fade_seconds=1.0, key_dimmer_pct=50.0)]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L1" not in _rule_ids(report.findings)

    def test_fail_section_without_a_cue(self):
        sheet = _sheet([], section_count=1)
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L1" in _rule_ids(report.findings)


# ---------------------------------------------------------------------------
# L2 — D 단조성 (E1) + Seq 114 range regression (E4)
# ---------------------------------------------------------------------------


class TestL2DimmerMonotonicity:
    def test_pass_dimmer_rises_within_each_d_levels_budget(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=2, fade_seconds=2.0, key_dimmer_pct=50.0
                ),
                LintCue(
                    cue_no=1, section_index=0, d_level=3, fade_seconds=1.5, key_dimmer_pct=70.0
                ),
                LintCue(
                    cue_no=2, section_index=0, d_level=4, fade_seconds=1.0, key_dimmer_pct=90.0
                ),
                LintCue(
                    cue_no=3, section_index=0, d_level=5, fade_seconds=0.0, key_dimmer_pct=100.0
                ),
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L2" not in _rule_ids(report.findings)

    def test_fail_seq114_style_all_cues_pinned_at_100_percent(self):
        """The exact measured Seq 114 defect: every lit cue at dimmer 100%
        regardless of D level — flat, never decreasing, still a violation
        because D2/D3 sit far outside their own 40-60% / 60-80% budgets."""
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=2, fade_seconds=0.5, key_dimmer_pct=100.0
                ),
                LintCue(
                    cue_no=1, section_index=0, d_level=3, fade_seconds=0.5, key_dimmer_pct=100.0
                ),
                LintCue(
                    cue_no=2, section_index=0, d_level=4, fade_seconds=0.5, key_dimmer_pct=100.0
                ),
                LintCue(
                    cue_no=3, section_index=0, d_level=5, fade_seconds=0.5, key_dimmer_pct=100.0
                ),
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        l2_findings = [f for f in report.findings if f.rule_id == "L2"]
        assert len(l2_findings) >= 2  # the D2 cue and the D3 cue are both out of range
        assert {f.cue_number for f in l2_findings} == {0.0, 1.0}

    def test_tag_suppresses_only_l2(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=2,
                    fade_seconds=0.5,
                    key_dimmer_pct=100.0,
                    tags=frozenset({"L2"}),
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L2" not in _rule_ids(report.findings)


# ---------------------------------------------------------------------------
# L3 — 헤드룸 (E2)
# ---------------------------------------------------------------------------


class TestL3Headroom:
    def test_pass_pre_d5_keeps_one_axis_short_of_max(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=4,
                    fade_seconds=1.0,
                    key_dimmer_pct=100.0,
                    position_width="wide",  # not "max"
                    effect_axis_count=2,
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L3" not in _rule_ids(report.findings)

    def test_fail_pre_d5_maxes_dimmer_width_and_effects_together(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=4,
                    fade_seconds=1.0,
                    key_dimmer_pct=100.0,
                    position_width="max",
                    effect_axis_count=2,
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L3" in _rule_ids(report.findings)


# ---------------------------------------------------------------------------
# L4 — 포지션 폭 축소 (E3)
# ---------------------------------------------------------------------------


class TestL4PositionWidthProgression:
    def test_pass_width_holds_or_widens_as_d_rises(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=2, fade_seconds=1.0, position_width="narrow"
                ),
                LintCue(
                    cue_no=1, section_index=0, d_level=3, fade_seconds=1.0, position_width="medium"
                ),
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L4" not in _rule_ids(report.findings)

    def test_fail_width_narrows_as_d_rises_without_a_tag(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=2, fade_seconds=1.0, position_width="medium"
                ),
                LintCue(
                    cue_no=1, section_index=0, d_level=3, fade_seconds=1.0, position_width="narrow"
                ),
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L4" in _rule_ids(report.findings)

    def test_tag_suppresses_only_l4(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=2, fade_seconds=1.0, position_width="medium"
                ),
                LintCue(
                    cue_no=1,
                    section_index=0,
                    d_level=3,
                    fade_seconds=1.0,
                    position_width="narrow",
                    tags=frozenset({"L4"}),
                ),
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L4" not in _rule_ids(report.findings)


# ---------------------------------------------------------------------------
# L5 — 팔레트 크기/이탈 (C1)
# ---------------------------------------------------------------------------


class TestL5Palette:
    def test_pass_colors_stay_inside_a_5_or_fewer_palette(self):
        profile = MusicProfile(palette=("red", "blue"))
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, palette_colors=("red",)
                )
            ]
        )
        report = lint_sheet(sheet, profile, _DUAL_LAYER_RIG)
        assert "L5" not in _rule_ids(report.findings)

    def test_fail_palette_declares_more_than_5_colors(self):
        profile = MusicProfile(palette=("a", "b", "c", "d", "e", "f"))
        sheet = _sheet([LintCue(cue_no=0, section_index=0, d_level=3, fade_seconds=1.0)])
        report = lint_sheet(sheet, profile, _DUAL_LAYER_RIG)
        assert "L5" in _rule_ids(report.findings)

    def test_fail_cue_uses_an_off_palette_color(self):
        profile = MusicProfile(palette=("red", "blue"))
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=3,
                    fade_seconds=1.0,
                    palette_colors=("green",),
                )
            ]
        )
        report = lint_sheet(sheet, profile, _DUAL_LAYER_RIG)
        assert "L5" in _rule_ids(report.findings)

    def test_no_declared_palette_means_nothing_to_violate(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=3,
                    fade_seconds=1.0,
                    palette_colors=("green",),
                )
            ]
        )
        report = lint_sheet(sheet, MusicProfile(), _DUAL_LAYER_RIG)
        assert "L5" not in _rule_ids(report.findings)


# ---------------------------------------------------------------------------
# L6 — 키층 소등 + 보컬 구간 (I3), RG1-gated
# ---------------------------------------------------------------------------


class TestL6VocalKeyLayer:
    def test_pass_key_layer_stays_lit_in_a_vocal_section(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=2, fade_seconds=1.0, key_dimmer_pct=45.0)]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L6" not in _rule_ids(report.findings)

    def test_fail_key_layer_off_in_a_vocal_section(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=2, fade_seconds=1.0, key_dimmer_pct=0.0)]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L6" in _rule_ids(report.findings)

    def test_disabled_and_noted_on_a_single_layer_rig(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=2, fade_seconds=1.0, key_dimmer_pct=0.0)]
        )
        report = lint_sheet(sheet, _WITH_BPM, _SINGLE_LAYER_RIG)
        assert "L6" not in _rule_ids(report.findings)
        assert "L6" in {note.rule_id for note in report.disabled_rules}


# ---------------------------------------------------------------------------
# L7 — 백층 > 키층 (I2), RG1-gated
# ---------------------------------------------------------------------------


class TestL7BackLayerBudget:
    def test_pass_back_layer_stays_under_key_layer(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=3,
                    fade_seconds=1.0,
                    key_dimmer_pct=80.0,
                    back_dimmer_pct=40.0,
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L7" not in _rule_ids(report.findings)

    def test_fail_back_layer_exceeds_key_layer_without_a_tag(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=3,
                    fade_seconds=1.0,
                    key_dimmer_pct=40.0,
                    back_dimmer_pct=80.0,
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L7" in _rule_ids(report.findings)

    def test_disabled_and_noted_on_a_single_layer_rig(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=3,
                    fade_seconds=1.0,
                    key_dimmer_pct=40.0,
                    back_dimmer_pct=80.0,
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _SINGLE_LAYER_RIG)
        assert "L7" not in _rule_ids(report.findings)
        assert "L7" in {note.rule_id for note in report.disabled_rules}


# ---------------------------------------------------------------------------
# L8 — 블랙아웃 예산 (I4)
# ---------------------------------------------------------------------------


class TestL8BlackoutBudget:
    def _blackout_cue(self, cue_no: float) -> LintCue:
        return LintCue(
            cue_no=cue_no, section_index=0, d_level=1, fade_seconds=0.0, is_blackout=True
        )

    def test_pass_three_blackouts_stays_within_budget(self):
        sheet = _sheet([self._blackout_cue(n) for n in range(3)])
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L8" not in _rule_ids(report.findings)

    def test_fail_a_fourth_blackout_exceeds_budget(self):
        sheet = _sheet([self._blackout_cue(n) for n in range(4)])
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        findings = [f for f in report.findings if f.rule_id == "L8"]
        assert len(findings) == 1
        assert findings[0].cue_number == 3.0


# ---------------------------------------------------------------------------
# L9 — 스냅은 악센트 전용 (G1)
# ---------------------------------------------------------------------------


class TestL9SnapAtAccentOnly:
    def test_pass_snap_at_an_accent_cue(self):
        sheet = _sheet(
            [LintCue(cue_no=0.5, section_index=0, d_level=4, fade_seconds=0.0, is_accent=True)]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L9" not in _rule_ids(report.findings)

    def test_fail_snap_at_a_non_accent_cue(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=4, fade_seconds=0.0, is_accent=False)]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L9" in _rule_ids(report.findings)

    def test_tag_suppresses_only_l9(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=4,
                    fade_seconds=0.0,
                    is_accent=False,
                    tags=frozenset({"L9"}),
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L9" not in _rule_ids(report.findings)


# ---------------------------------------------------------------------------
# L10 — 동시 이펙트 축 수 예산 (F3)
# ---------------------------------------------------------------------------


class TestL10EffectAxisBudget:
    def test_pass_effect_axis_count_within_d3_budget(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, effect_axis_count=1)]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L10" not in _rule_ids(report.findings)

    def test_fail_effect_axis_count_exceeds_d3_budget(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, effect_axis_count=2)]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L10" in _rule_ids(report.findings)


# ---------------------------------------------------------------------------
# L11 — 이펙트 Speed BPM 배수 격자 (F2), BPM-declared-gated
# ---------------------------------------------------------------------------


class TestL11EffectSpeedGrid:
    def test_pass_speed_on_grid(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, effect_speed_beats=1.0
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L11" not in _rule_ids(report.findings)

    def test_fail_speed_far_off_grid(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, effect_speed_beats=1.35
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L11" in _rule_ids(report.findings)

    def test_disabled_and_noted_when_bpm_is_not_declared(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, effect_speed_beats=1.35
                )
            ]
        )
        report = lint_sheet(sheet, _NO_BPM, _DUAL_LAYER_RIG)
        assert "L11" not in _rule_ids(report.findings)
        assert "L11" in {note.rule_id for note in report.disabled_rules}


# ---------------------------------------------------------------------------
# L12 — 인접 큐 변화 축 > 2, 리셋 예외 (V1)
# ---------------------------------------------------------------------------


class TestL12AdjacentChangeBudget:
    def test_pass_reset_allows_every_axis_to_change(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=2,
                    fade_seconds=1.0,
                    position_label="Vocal DSC",
                    palette_colors=("blue",),
                    effect_axis_count=0,
                    effect_speed_beats=None,
                ),
                LintCue(
                    cue_no=1,
                    section_index=0,
                    d_level=5,  # jump of 3 -> reset
                    fade_seconds=0.0,
                    position_label="Ring In",
                    palette_colors=("red",),
                    effect_axis_count=2,
                    effect_speed_beats=1.0,
                ),
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L12" not in _rule_ids(report.findings)

    def test_fail_more_than_two_axes_change_outside_a_reset(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=3,
                    fade_seconds=1.0,
                    position_label="Wall",
                    palette_colors=("blue",),
                    effect_axis_count=1,
                    effect_speed_beats=1.0,
                ),
                LintCue(
                    cue_no=1,
                    section_index=0,
                    d_level=3,  # same D -> not a reset
                    fade_seconds=1.0,
                    position_label="Cross",
                    palette_colors=("red",),
                    effect_axis_count=0,
                    effect_speed_beats=None,
                ),
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L12" in _rule_ids(report.findings)


# ---------------------------------------------------------------------------
# L13 — 동일 3중 조합 연속 (V2)
# ---------------------------------------------------------------------------


class TestL13RepeatComboStreak:
    def _cue(self, cue_no: float) -> LintCue:
        return LintCue(
            cue_no=cue_no,
            section_index=0,
            d_level=4,
            fade_seconds=1.0,
            position_label="Cross",
            palette_colors=("red",),
            effect_axis_count=1,
            effect_speed_beats=1.0,
        )

    def test_pass_two_repeats_stay_under_the_streak_limit(self):
        sheet = _sheet([self._cue(0), self._cue(1)])
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L13" not in _rule_ids(report.findings)

    def test_fail_three_consecutive_identical_combos(self):
        sheet = _sheet([self._cue(0), self._cue(1), self._cue(2)])
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        findings = [f for f in report.findings if f.rule_id == "L13"]
        assert len(findings) == 1
        assert findings[0].cue_number == 2


# ---------------------------------------------------------------------------
# L14 — Audience/블라인더 예산 + D5 전용 (P4, X1)
# ---------------------------------------------------------------------------


class TestL14AudienceOrBlinderBudget:
    def test_pass_single_use_at_d5(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=5,
                    fade_seconds=0.0,
                    is_audience_or_blinder=True,
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L14" not in _rule_ids(report.findings)

    def test_fail_used_outside_d5(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=0,
                    section_index=0,
                    d_level=3,
                    fade_seconds=0.0,
                    is_audience_or_blinder=True,
                )
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        assert "L14" in _rule_ids(report.findings)

    def test_fail_a_third_use_exceeds_budget(self):
        sheet = _sheet(
            [
                LintCue(
                    cue_no=n,
                    section_index=0,
                    d_level=5,
                    fade_seconds=0.0,
                    is_audience_or_blinder=True,
                )
                for n in range(3)
            ]
        )
        report = lint_sheet(sheet, _WITH_BPM, _DUAL_LAYER_RIG)
        findings = [f for f in report.findings if f.rule_id == "L14"]
        assert len(findings) == 1
        assert findings[0].cue_number == 2


# ---------------------------------------------------------------------------
# Disabled-rules audit note — combined view
# ---------------------------------------------------------------------------


class TestDisabledRulesAudit:
    def test_single_layer_rig_with_declared_bpm_disables_only_l6_and_l7(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, key_dimmer_pct=70.0)]
        )
        assert _disabled_ids(sheet, _WITH_BPM, _SINGLE_LAYER_RIG) == {"L6", "L7"}

    def test_dual_layer_rig_without_bpm_disables_only_l11(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, key_dimmer_pct=70.0)]
        )
        assert _disabled_ids(sheet, _NO_BPM, _DUAL_LAYER_RIG) == {"L11"}

    def test_single_layer_rig_without_bpm_disables_all_three(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, key_dimmer_pct=70.0)]
        )
        assert _disabled_ids(sheet, _NO_BPM, _SINGLE_LAYER_RIG) == {"L6", "L7", "L11"}

    def test_fully_declared_rig_and_profile_disables_nothing(self):
        sheet = _sheet(
            [LintCue(cue_no=0, section_index=0, d_level=3, fade_seconds=1.0, key_dimmer_pct=70.0)]
        )
        assert _disabled_ids(sheet, _WITH_BPM, _DUAL_LAYER_RIG) == set()
