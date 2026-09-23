"""Position cue sheet builder — SPEC-COPILOT-CUETIME-001 T3.

Contract: mood words resolve to the operator-based Position presets, every
lit cue stores a preset RECALL (never raw values), blackout sections are
dimmer-only, MIB pre-moves appear after blackouts, and an unmatched mood is
skipped (consuming its cue number) instead of guessed.
"""

from __future__ import annotations

import pytest

from server.design.position_sheet import build_standard_position_cue_sheet
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.spatial.pointing import BASIC_POSITION_SEQUENCE, SpatialPointingError
from server.spatial.position_cuesheet import (
    PositionSheetSection,
    build_position_cue_sheet,
    required_sheet_labels,
)

#: 카드 t449 — 정상 쇼파일(기본 10종이 21~30에 순서대로)을 라벨 조회한 결과.
#: 옛 ``preset_start=21`` 과 바이트 동일한 번호를 낸다.
_NORMAL_POOL_21 = {label: 21 + i for i, label in enumerate(BASIC_POSITION_SEQUENCE)}


def _single_layer_rig():
    """A rig with no declared layers and no group-name heuristic hit — the
    RG1 single-layer degrade (RigLayers.mapped is False)."""
    return build_rig_profile(patch=[], groups={}, coords=[])


def _sections() -> tuple[PositionSheetSection, ...]:
    return (
        PositionSheetSection("Intro", 0, "잔잔한 발라드"),
        PositionSheetSection("Break", 40_000, "암전"),
        PositionSheetSection("Chorus", 50_000, "클럽 드롭"),
    )


class TestBuildPositionCueSheet:
    def test_moods_resolve_to_operator_based_presets(self):
        sheet = build_position_cue_sheet(
            _sections(), sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20, 26]
        )
        by_cue = {res.cue_no: res for res in sheet.resolutions}
        # 잔잔/발라드 → Vocal DSC (sequence offset 4 → 2.25);
        # 클럽/드롭 → Cross (offset 7 → 2.28).
        assert by_cue[1].look_label == "Vocal DSC"
        assert by_cue[1].preset_no == 25
        assert by_cue[2].blackout is True
        assert by_cue[3].look_label == "Cross"
        assert by_cue[3].preset_no == 28

    def test_the_blackout_reveal_gains_a_mib_premove(self):
        sheet = build_position_cue_sheet(
            _sections(), sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20]
        )
        assert [plan.cue_no for plan in sheet.plans] == [1, 2, 2.5, 3]
        premove = sheet.plans[2]
        assert premove.preset_no == 28 and premove.dimmer is None
        # The reveal cue lost its position — the pre-move parked the heads.
        assert sheet.plans[3].preset_no is None and sheet.plans[3].dimmer == 100.0

    def test_every_lit_cue_stores_a_preset_recall(self):
        sheet = build_position_cue_sheet(
            _sections(), sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20]
        )
        stores = [line for bundle in sheet.bundles for line in bundle if "Store" in line]
        recalls = [line for bundle in sheet.bundles for line in bundle if "At Preset" in line]
        assert len(stores) == 4  # 3 sections + 1 pre-move
        assert recalls == [
            "Fixture 20 ; At Preset 2.25",
            "Fixture 20 ; At Preset 2.28",  # the dark pre-move carries the recall
        ]
        # No bundle ever stores raw Pan/Tilt values.
        assert not any(
            "'Pan'" in line or "'Tilt'" in line for bundle in sheet.bundles for line in bundle
        )

    def test_an_unmatched_mood_is_skipped_and_consumes_its_number(self):
        sections = (
            PositionSheetSection("Intro", 0, "잔잔한 발라드"),
            PositionSheetSection("Bridge", 30_000, "뭔가 애매한 느낌"),
            PositionSheetSection("Outro", 60_000, "웅장한 피날레"),
        )
        sheet = build_position_cue_sheet(
            sections, sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20]
        )
        assert sheet.resolutions[1].skipped_reason is not None
        assert [plan.cue_no for plan in sheet.plans] == [1, 3]

    def test_cue_names_are_console_safe(self):
        # Korean section names fall back to 'Section n'; dots never survive.
        sections = (PositionSheetSection("인트로 v2.1", 0, "잔잔하게"),)
        sheet = build_position_cue_sheet(
            sections, sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20]
        )
        store = next(line for line in sheet.bundles[0] if line.startswith("Store"))
        assert store == "Store Sequence 110 Cue 1 'v21' CueFade 3"

    def test_a_digits_only_name_remainder_falls_back(self):
        # "브레이크1" → ASCII remainder "1" — measured live: the cue list
        # filled with cues named '1', '2'. Digits-only = fall back.
        sections = (PositionSheetSection("브레이크1", 0, "잔잔하게"),)
        sheet = build_position_cue_sheet(
            sections, sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20]
        )
        store = next(line for line in sheet.bundles[0] if line.startswith("Store"))
        assert store == "Store Sequence 110 Cue 1 'Section 1' CueFade 3"

    def test_repeating_moods_rotate_over_alternatives(self):
        # A metal set repeats its chorus/verse moods; the sheet must not park
        # the rig on the identical preset every time. Deterministic rotation:
        # fewest uses -> least recently used -> table order.
        sections = (
            PositionSheetSection("Drop1", 0, "클럽 드롭"),
            PositionSheetSection("Verse", 10_000, "화려하게 펼침"),
            PositionSheetSection("Drop2", 20_000, "클럽 드롭"),
            PositionSheetSection("Solo", 30_000, "화려 펼침"),
        )
        sheet = build_position_cue_sheet(
            sections, sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20]
        )
        labels = [res.look_label for res in sheet.resolutions]
        # First occurrences keep the canonical looks; repeats drift to fresh
        # same-vibe alternatives (Cross -> Ring Out, Fan Out -> Audience).
        assert labels == ["Cross", "Fan Out", "Ring Out", "Audience"]
        assert len(set(labels)) == 4
        assert sheet.resolutions[2].varied_from == "Cross"
        assert sheet.resolutions[3].varied_from == "Fan Out"
        assert sheet.resolutions[0].varied_from is None

    def test_refusals(self):
        with pytest.raises(SpatialPointingError, match="no song sections"):
            build_position_cue_sheet((), sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20])
        with pytest.raises(SpatialPointingError, match="strictly increase"):
            build_position_cue_sheet(
                (
                    PositionSheetSection("A", 10_000, "잔잔"),
                    PositionSheetSection("B", 10_000, "웅장"),
                ),
                sequence_no=110,
                preset_numbers=_NORMAL_POOL_21,
                fids=[20],
            )
        with pytest.raises(SpatialPointingError, match="must be positive"):
            build_position_cue_sheet(
                _sections(),
                sequence_no=110,
                preset_numbers={**_NORMAL_POOL_21, "Vocal DSC": 0},
                fids=[20],
            )
        with pytest.raises(SpatialPointingError, match="nothing to store"):
            build_position_cue_sheet(
                (PositionSheetSection("A", 0, "애매한 무드"),),
                sequence_no=110,
                preset_numbers=_NORMAL_POOL_21,
                fids=[20],
            )


class TestLabelResolvedPresetNumbers:
    """카드 t449 — 번호는 ``preset_start + index`` 산술이 아니라 호출자가 콘솔에서
    라벨로 찾은 슬롯에서 온다. 결함 상태: 1~10 이 시트 프리셋이고 진짜 기본
    10종은 다른 자리에 있을 때 옛 산술은 조용히 엉뚱한 프리셋을 불렀다."""

    def test_required_labels_match_what_the_sheet_recalls(self):
        # 반복 무드의 대안 회전까지 포함해 빌더가 실제로 부르는 라벨과 같다.
        sections = (
            PositionSheetSection("Drop1", 0, "클럽 드롭"),
            PositionSheetSection("Break", 5_000, "암전"),
            PositionSheetSection("Verse", 10_000, "화려하게 펼침"),
            PositionSheetSection("Drop2", 20_000, "클럽 드롭"),
            PositionSheetSection("Odd", 25_000, "뭔가 애매한 느낌"),
        )
        labels = required_sheet_labels(sections)
        assert labels == ("Cross", "Fan Out", "Ring Out")
        sheet = build_position_cue_sheet(
            sections, sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20]
        )
        recalled = tuple(dict.fromkeys(r.look_label for r in sheet.resolutions if r.look_label))
        assert recalled == labels

    def test_a_blackout_only_sheet_needs_no_label(self):
        assert required_sheet_labels((PositionSheetSection("B", 0, "암전"),)) == ()

    def test_the_recall_uses_the_resolved_slot_not_arithmetic(self):
        # 진짜 Vocal DSC=45, Cross=48 (시트 프리셋이 1~10 을 차지한 쇼파일).
        sheet = build_position_cue_sheet(
            _sections(),
            sequence_no=110,
            preset_numbers={"Vocal DSC": 45, "Cross": 48},
            fids=[20],
        )
        recalls = [line for bundle in sheet.bundles for line in bundle if "At Preset" in line]
        assert recalls == ["Fixture 20 ; At Preset 2.45", "Fixture 20 ; At Preset 2.48"]
        assert [r.preset_no for r in sheet.resolutions] == [45, None, 48]

    def test_a_label_without_a_resolved_number_is_refused(self):
        with pytest.raises(SpatialPointingError, match="no resolved preset number"):
            build_position_cue_sheet(
                _sections(), sequence_no=110, preset_numbers={"Vocal DSC": 45}, fids=[20]
            )


class TestStandardEngineIntegration:
    """R4: the standard sheet consuming M1's profile+rig engine
    (SPEC-COPILOT-SONGSTD-001, spec.md §R4) — via
    ``server.design.position_sheet.build_standard_position_cue_sheet``, the
    design-layer home the SONGSTD M2 path moved to so ``server/spatial``
    stays stdlib + intra-spatial (AC-SPATIAL-013)."""

    def _profile_sections(self):
        return (
            PositionSheetSection("Verse", 0, "잔잔한 발라드"),  # Vocal DSC, D2
            PositionSheetSection("Outro", 20_000, "웅장한 피날레"),  # Ring In, D5
        )

    def test_no_profile_output_is_unchanged(self):
        # Byte-identical to the pre-R4 contract: flat _LIT_DIMMER — and the
        # pure spatial draft carries no lint at all since the SONGSTD M2
        # boundary move (the audit lives on StandardPositionCueSheet).
        sheet = build_position_cue_sheet(
            self._profile_sections(), sequence_no=110, preset_numbers=_NORMAL_POOL_21, fids=[20]
        )
        assert [plan.dimmer for plan in sheet.plans] == [100.0, 100.0]
        assert not hasattr(sheet, "lint_report")

    def test_explicit_profile_changes_d2_vs_d5_dimmer_and_fade(self):
        profile = MusicProfile(bpm=120.0)
        rig = _single_layer_rig()
        sheet = build_standard_position_cue_sheet(
            self._profile_sections(),
            sequence_no=110,
            preset_numbers=_NORMAL_POOL_21,
            fids=[20],
            profile=profile,
            rig=rig,
        )
        by_cue = {plan.cue_no: plan for plan in sheet.plans}
        # D2 row: dimmer (40, 60) -> midpoint 50; fade_beats (4, 4) at 120bpm -> 2.0s.
        assert by_cue[1].dimmer == 50.0
        assert by_cue[1].fade_seconds == 2.0
        # D5 row: dimmer (100, 100) -> 100; fade_beats (0, 1) at 120bpm -> 0.25s.
        assert by_cue[2].dimmer == 100.0
        assert by_cue[2].fade_seconds == 0.25
        # E1/G2: D rose -> dimmer rose and fade shortened.
        assert by_cue[1].dimmer < by_cue[2].dimmer
        assert by_cue[1].fade_seconds > by_cue[2].fade_seconds

    def test_no_all_100_percent_sheet(self):
        # The Seq 114 defect this REQ fixes: every cue flat at 100%.
        profile = MusicProfile(bpm=120.0)
        rig = _single_layer_rig()
        sheet = build_standard_position_cue_sheet(
            self._profile_sections(),
            sequence_no=110,
            preset_numbers=_NORMAL_POOL_21,
            fids=[20],
            profile=profile,
            rig=rig,
        )
        dimmers = [plan.dimmer for plan in sheet.plans]
        assert not all(value == 100.0 for value in dimmers)

    def test_mib_alternative_rotation_and_follow_survive_with_profile(self):
        profile = MusicProfile(bpm=120.0)
        rig = _single_layer_rig()
        sheet = build_standard_position_cue_sheet(
            _sections(),
            sequence_no=110,
            preset_numbers=_NORMAL_POOL_21,
            fids=[20],
            profile=profile,
            rig=rig,
        )
        assert [plan.cue_no for plan in sheet.plans] == [1, 2, 2.5, 3]
        premove = sheet.plans[2]
        assert premove.preset_no == 28 and premove.dimmer is None
        reveal = sheet.plans[3]
        assert reveal.preset_no is None
        # D4 ("클럽 드롭" -> Cross): dimmer (80, 100) -> midpoint 90, not the
        # flat pre-R4 100.0 — proof the reveal's dimmer is now D-budget-driven.
        assert reveal.dimmer == 90.0
        follow_lines = [line for bundle in sheet.bundles for line in bundle if "Follow" in line]
        assert follow_lines == ["Set Cue 2.5 Sequence 110 Property 'TrigType' 'Follow'"]

    def test_single_layer_rig_reports_l6_l7_disabled(self):
        profile = MusicProfile(bpm=120.0)
        rig = _single_layer_rig()
        sheet = build_standard_position_cue_sheet(
            (PositionSheetSection("Verse", 0, "잔잔한 발라드"),),
            sequence_no=110,
            preset_numbers=_NORMAL_POOL_21,
            fids=[20],
            profile=profile,
            rig=rig,
        )
        disabled_ids = {note.rule_id for note in sheet.lint_report.disabled_rules}
        assert {"L6", "L7"} <= disabled_ids

    def test_profile_and_rig_are_structurally_required(self):
        # The old runtime "supplied together" check became structural with
        # the SONGSTD M2 boundary move: the design entry point REQUIRES both
        # keywords, and the pure spatial builder accepts neither.
        with pytest.raises(TypeError):
            build_standard_position_cue_sheet(
                self._profile_sections(),
                sequence_no=110,
                preset_numbers=_NORMAL_POOL_21,
                fids=[20],
                profile=MusicProfile(bpm=120.0),
            )
        with pytest.raises(TypeError):
            build_position_cue_sheet(
                self._profile_sections(),
                sequence_no=110,
                preset_numbers=_NORMAL_POOL_21,
                fids=[20],
                profile=MusicProfile(bpm=120.0),
                rig=_single_layer_rig(),
            )
