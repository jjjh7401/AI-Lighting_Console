"""Position cue sheet builder — SPEC-COPILOT-CUETIME-001 T3.

Contract: mood words resolve to the operator-based Position presets, every
lit cue stores a preset RECALL (never raw values), blackout sections are
dimmer-only, MIB pre-moves appear after blackouts, and an unmatched mood is
skipped (consuming its cue number) instead of guessed.
"""

from __future__ import annotations

import pytest

from server.spatial.pointing import SpatialPointingError
from server.spatial.position_cuesheet import (
    PositionSheetSection,
    build_position_cue_sheet,
)


def _sections() -> tuple[PositionSheetSection, ...]:
    return (
        PositionSheetSection("Intro", 0, "잔잔한 발라드"),
        PositionSheetSection("Break", 40_000, "암전"),
        PositionSheetSection("Chorus", 50_000, "클럽 드롭"),
    )


class TestBuildPositionCueSheet:
    def test_moods_resolve_to_operator_based_presets(self):
        sheet = build_position_cue_sheet(
            _sections(), sequence_no=110, preset_start=21, fids=[20, 26]
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
        sheet = build_position_cue_sheet(_sections(), sequence_no=110, preset_start=21, fids=[20])
        assert [plan.cue_no for plan in sheet.plans] == [1, 2, 2.5, 3]
        premove = sheet.plans[2]
        assert premove.preset_no == 28 and premove.dimmer is None
        # The reveal cue lost its position — the pre-move parked the heads.
        assert sheet.plans[3].preset_no is None and sheet.plans[3].dimmer == 100.0

    def test_every_lit_cue_stores_a_preset_recall(self):
        sheet = build_position_cue_sheet(_sections(), sequence_no=110, preset_start=21, fids=[20])
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
        sheet = build_position_cue_sheet(sections, sequence_no=110, preset_start=21, fids=[20])
        assert sheet.resolutions[1].skipped_reason is not None
        assert [plan.cue_no for plan in sheet.plans] == [1, 3]

    def test_cue_names_are_console_safe(self):
        # Korean section names fall back to 'Section n'; dots never survive.
        sections = (PositionSheetSection("인트로 v2.1", 0, "잔잔하게"),)
        sheet = build_position_cue_sheet(sections, sequence_no=110, preset_start=21, fids=[20])
        store = next(line for line in sheet.bundles[0] if line.startswith("Store"))
        assert store == "Store Sequence 110 Cue 1 'v21' CueFade 3"

    def test_a_digits_only_name_remainder_falls_back(self):
        # "브레이크1" → ASCII remainder "1" — measured live: the cue list
        # filled with cues named '1', '2'. Digits-only = fall back.
        sections = (PositionSheetSection("브레이크1", 0, "잔잔하게"),)
        sheet = build_position_cue_sheet(sections, sequence_no=110, preset_start=21, fids=[20])
        store = next(line for line in sheet.bundles[0] if line.startswith("Store"))
        assert store == "Store Sequence 110 Cue 1 'Section 1' CueFade 3"

    def test_refusals(self):
        with pytest.raises(SpatialPointingError, match="no song sections"):
            build_position_cue_sheet((), sequence_no=110, preset_start=21, fids=[20])
        with pytest.raises(SpatialPointingError, match="strictly increase"):
            build_position_cue_sheet(
                (
                    PositionSheetSection("A", 10_000, "잔잔"),
                    PositionSheetSection("B", 10_000, "웅장"),
                ),
                sequence_no=110,
                preset_start=21,
                fids=[20],
            )
        with pytest.raises(SpatialPointingError, match="preset start"):
            build_position_cue_sheet(_sections(), sequence_no=110, preset_start=0, fids=[20])
        with pytest.raises(SpatialPointingError, match="nothing to store"):
            build_position_cue_sheet(
                (PositionSheetSection("A", 0, "애매한 무드"),),
                sequence_no=110,
                preset_start=21,
                fids=[20],
            )
