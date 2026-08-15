"""MIB (Move In Black) rule + bundle rendering — SPEC-COPILOT-CUETIME-001 T2.

The contract under test: a dark rig (explicit dimmer 0) followed by a
reveal-onto-a-new-position cue gains a position-only pre-move cue at the
numeric midpoint, and the reveal cue loses its position. Everything else
passes through untouched — MIB must never invent movement on a lit stage.
"""

from __future__ import annotations

import pytest

from server.spatial.mib import (
    PositionCuePlan,
    apply_mib,
    position_cue_bundle,
    premove_follow_command,
)
from server.spatial.pointing import SpatialPointingError


def _sheet() -> tuple[PositionCuePlan, ...]:
    return (
        PositionCuePlan(1, "Wide", preset_no=26, dimmer=100, fade_seconds=2),
        PositionCuePlan(2, "Black", dimmer=0, fade_seconds=1),
        PositionCuePlan(3, "Cross", preset_no=28, dimmer=100, fade_seconds=3),
    )


class TestApplyMib:
    def test_dark_then_reveal_on_a_new_position_inserts_the_premove(self):
        result = apply_mib(_sheet())
        assert [cue.cue_no for cue in result] == [1, 2, 2.5, 3]
        premove = result[2]
        assert premove.name == "Cross Move"
        assert premove.preset_no == 28
        assert premove.dimmer is None  # tracking keeps the rig at 0
        assert premove.fade_seconds == 1.0
        # The reveal cue keeps its intensity fade but loses the position —
        # the pre-move already parked the heads.
        reveal = result[3]
        assert premove.premove is True
        assert reveal.premove is False
        assert reveal.preset_no is None
        assert reveal.dimmer == 100
        assert reveal.fade_seconds == 3

    def test_the_premove_follow_command_matches_the_verified_grammar(self):
        # 31_choreography_patterns.md:111 — Property form; /trig= is rejected
        # by 2.4.2. Left on Go, the operator's reveal press plays an invisible
        # dark move instead (measured live, Seq 113).
        premove = apply_mib(_sheet())[2]
        assert premove_follow_command(101, premove) == (
            "Set Cue 2.5 Sequence 101 Property 'TrigType' 'Follow'"
        )
        with pytest.raises(SpatialPointingError, match="not a MIB pre-move"):
            premove_follow_command(101, _sheet()[0])

    def test_a_lit_transition_is_untouched(self):
        cues = (
            PositionCuePlan(1, "Wide", preset_no=26, dimmer=100),
            PositionCuePlan(2, "Cross", preset_no=28, dimmer=100),
        )
        assert apply_mib(cues) == cues

    def test_a_reveal_onto_the_parked_position_needs_no_premove(self):
        cues = (
            PositionCuePlan(1, "Cross", preset_no=28, dimmer=100),
            PositionCuePlan(2, "Black", dimmer=0),
            PositionCuePlan(3, "Cross Again", preset_no=28, dimmer=100),
        )
        assert apply_mib(cues) == cues

    def test_an_unknown_start_is_treated_as_lit(self):
        # No explicit dimmer before the reveal: inserting a phantom pre-move
        # on a possibly-visible rig would CAUSE the swing MIB removes.
        cues = (
            PositionCuePlan(1, "Park", preset_no=26),
            PositionCuePlan(2, "Cross", preset_no=28, dimmer=100),
        )
        assert apply_mib(cues) == cues

    def test_a_tracked_dark_state_survives_position_only_cues(self):
        cues = (
            PositionCuePlan(1, "Black", dimmer=0),
            PositionCuePlan(2, "Park", preset_no=26),  # still dark (tracked)
            PositionCuePlan(3, "Cross", preset_no=28, dimmer=100),
        )
        result = apply_mib(cues)
        assert [cue.cue_no for cue in result] == [1, 2, 2.5, 3]

    def test_a_dark_reveal_without_position_is_untouched(self):
        cues = (
            PositionCuePlan(1, "Black", dimmer=0),
            PositionCuePlan(2, "Bump", dimmer=100),
        )
        assert apply_mib(cues) == cues

    def test_move_seconds_names_the_premove_fade(self):
        result = apply_mib(_sheet(), move_seconds=0.5)
        assert result[2].fade_seconds == 0.5

    def test_refusals(self):
        with pytest.raises(SpatialPointingError, match="no cues"):
            apply_mib(())
        with pytest.raises(SpatialPointingError, match="strictly increase"):
            apply_mib(
                (
                    PositionCuePlan(2, "A", dimmer=100),
                    PositionCuePlan(2, "B", dimmer=0),
                )
            )
        with pytest.raises(SpatialPointingError, match="empty programmer"):
            apply_mib((PositionCuePlan(1, "Empty"),))
        with pytest.raises(SpatialPointingError, match="move_seconds"):
            apply_mib(_sheet(), move_seconds=-1)


class TestPositionCueBundle:
    def test_a_full_cue_renders_recall_dimmer_store_clear(self):
        plan = PositionCuePlan(1, "Wide", preset_no=26, dimmer=100, fade_seconds=2)
        assert position_cue_bundle(102, plan, [20, 26]) == (
            "Fixture 20 + 26 ; At Preset 2.26",
            "Fixture 20 + 26 ; Attribute 'Dimmer' At 100",
            "Store Sequence 102 Cue 1 'Wide' CueFade 2",
            "ClearAll",
        )

    def test_a_premove_cue_is_position_only(self):
        plan = PositionCuePlan(2.5, "Cross Move", preset_no=28, fade_seconds=1)
        assert position_cue_bundle(102, plan, [20]) == (
            "Fixture 20 ; At Preset 2.28",
            "Store Sequence 102 Cue 2.5 'Cross Move' CueFade 1",
            "ClearAll",
        )

    def test_a_blackout_cue_is_dimmer_only(self):
        plan = PositionCuePlan(2, "Black", dimmer=0, fade_seconds=1)
        assert position_cue_bundle(102, plan, [20]) == (
            "Fixture 20 ; Attribute 'Dimmer' At 0",
            "Store Sequence 102 Cue 2 'Black' CueFade 1",
            "ClearAll",
        )

    def test_extra_value_lines_land_between_the_dimmer_and_the_store(self):
        plan = PositionCuePlan(1, "Wide", preset_no=26, dimmer=100, fade_seconds=2)
        bundle = position_cue_bundle(
            102,
            plan,
            [20, 26],
            extra_value_lines=("Group 12 ; Attribute 'Dimmer' At 80",),
        )
        assert bundle == (
            "Fixture 20 + 26 ; At Preset 2.26",
            "Fixture 20 + 26 ; Attribute 'Dimmer' At 100",
            "Group 12 ; Attribute 'Dimmer' At 80",
            "Store Sequence 102 Cue 1 'Wide' CueFade 2",
            "ClearAll",
        )

    def test_refusals(self):
        with pytest.raises(SpatialPointingError, match="no fixtures"):
            position_cue_bundle(102, PositionCuePlan(1, "A", dimmer=100), [])
        with pytest.raises(SpatialPointingError, match="neither a position nor a dimmer"):
            position_cue_bundle(102, PositionCuePlan(1, "A"), [20])
        with pytest.raises(SpatialPointingError, match="outside 0..100"):
            position_cue_bundle(102, PositionCuePlan(1, "A", dimmer=150), [20])
