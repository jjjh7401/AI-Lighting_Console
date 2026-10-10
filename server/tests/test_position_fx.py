"""Position-FX sequence builder — the preset-consuming command bundles.

Full-bundle snapshot assertions on purpose: every line is either validated
rulebook grammar (31_choreography_patterns.md) or `preset_recall_command`
reused verbatim, so the exact text IS the contract — including the preset
number offsets into the FX_POSITION_SEQUENCE bank.
"""

import pytest

from server.spatial.pointing import FX_POSITION_SEQUENCE, SpatialPointingError
from server.spatial.position_fx import (
    POSITION_FX_EFFECTS,
    position_fx_commands,
    relative_wave_lines,
)

FIDS = (11, 12, 13)
START = 41  # bank stored as Preset 2.41..2.50 in FX_POSITION_SEQUENCE order
SEQ = 201

#: t232 — the module no longer computes ``start + index`` itself; the caller
#: resolves each label to a real console slot first. This default mirrors a
#: NORMAL showfile (the ten labels sit contiguously at ``START``), so every
#: test below stays byte-identical to the pre-t232 ``fx_preset_start``-based
#: bundle unless it overrides ``preset_numbers`` directly.
_CONTIGUOUS_PRESET_NUMBERS = {
    name: START + offset for offset, name in enumerate(FX_POSITION_SEQUENCE)
}


def build(effect: str, **overrides) -> tuple[str, ...]:
    kwargs = dict(
        fids=FIDS, preset_numbers=_CONTIGUOUS_PRESET_NUMBERS, sequence_no=SEQ, label="My FX"
    )
    kwargs.update(overrides)
    return position_fx_commands(effect, **kwargs)


class TestVocabulary:
    def test_the_closed_effect_vocabulary(self):
        assert POSITION_FX_EFFECTS == ("sweep", "flyout", "circle", "ballyhoo", "wave")


class TestAbBundles:
    def test_sweep_full_bundle(self):
        # Sweep L = index 0 -> 2.41, Sweep R = index 1 -> 2.42.
        assert build("sweep") == (
            "ChangeDestination Root",
            "ClearAll",
            "Fixture 11 + 12 + 13 ; At Preset 2.41",
            "Store Sequence 201 Cue 1 'Sweep L' CueFade 2",
            "ClearAll",
            "Fixture 11 + 12 + 13 ; At Preset 2.42",
            "Store Sequence 201 Cue 2 'Sweep R' CueFade 2 /Merge",
            "ClearAll",
            "Label Sequence 201 'My FX'",
        )

    def test_flyout_full_bundle(self):
        # Sky Out = index 2 -> 2.43, Aisle Punch = index 9 -> 2.50.
        assert build("flyout") == (
            "ChangeDestination Root",
            "ClearAll",
            "Fixture 11 + 12 + 13 ; At Preset 2.43",
            "Store Sequence 201 Cue 1 'Sky Out' CueFade 2",
            "ClearAll",
            "Fixture 11 + 12 + 13 ; At Preset 2.50",
            "Store Sequence 201 Cue 2 'Aisle Punch' CueFade 2 /Merge",
            "ClearAll",
            "Label Sequence 201 'My FX'",
        )

    @pytest.mark.parametrize("effect", ["sweep", "flyout"])
    def test_merge_rides_cue_two_only(self, effect):
        commands = build(effect)
        merged = [line for line in commands if "/Merge" in line]
        assert len(merged) == 1
        assert "Cue 2" in merged[0]
        cue_one = next(line for line in commands if "Cue 1" in line)
        assert "/Merge" not in cue_one


class TestBaseBundles:
    def test_circle_full_bundle(self):
        # Circle Base = index 4 -> 2.45; two ±steps (t540), sine curve per step,
        # quarter-cycle axis offset — the t538 A5b 「동그란 원」 shape.
        assert build("circle") == (
            "ChangeDestination Root",
            "ClearAll",
            "Fixture 11 + 12 + 13 ; At Preset 2.45",
            "Attribute 'Pan' At Relative -12",
            "Attribute 'Tilt' At Relative -8",
            "Step 2",
            "Attribute 'Pan' At Relative 12",
            "Attribute 'Tilt' At Relative 8",
            "Step 1 At Accel -100",
            "Step 1 At Decel -100",
            "Step 2 At Accel -100",
            "Step 2 At Decel -100",
            "Attribute 'Pan' At Phase 0",
            "Attribute 'Tilt' At Phase 90",
            "Attribute 'Pan' At Speed 60",
            "Attribute 'Tilt' At Speed 60",
            "Store Sequence 201 Cue 1 'Circle'",
            "ClearAll",
            "Label Sequence 201 'My FX'",
        )

    def test_ballyhoo_full_bundle(self):
        # Bally Base = index 5 -> 2.46; both axes fanned, fast by definition (60 * 2).
        assert build("ballyhoo") == (
            "ChangeDestination Root",
            "ClearAll",
            "Fixture 11 + 12 + 13 ; At Preset 2.46",
            "Attribute 'Pan' At Relative -20",
            "Attribute 'Tilt' At Relative -10",
            "Step 2",
            "Attribute 'Pan' At Relative 20",
            "Attribute 'Tilt' At Relative 10",
            "Step 1 At Accel -100",
            "Step 1 At Decel -100",
            "Step 2 At Accel -100",
            "Step 2 At Decel -100",
            "Attribute 'Pan' At Phase 0 Thru 360",
            "Attribute 'Tilt' At Phase 0 Thru 360",
            "Attribute 'Pan' At Speed 120",
            "Attribute 'Tilt' At Speed 120",
            "Store Sequence 201 Cue 1 'Ballyhoo'",
            "ClearAll",
            "Label Sequence 201 'My FX'",
        )

    def test_wave_full_bundle(self):
        # Floor Base = index 3 -> 2.44; tilt is the only moving axis.
        assert build("wave") == (
            "ChangeDestination Root",
            "ClearAll",
            "Fixture 11 + 12 + 13 ; At Preset 2.44",
            "Attribute 'Tilt' At Relative -12",
            "Step 2",
            "Attribute 'Tilt' At Relative 12",
            "Step 1 At Accel -100",
            "Step 1 At Decel -100",
            "Step 2 At Accel -100",
            "Step 2 At Decel -100",
            "Attribute 'Tilt' At Phase 0 Thru 360",
            "Attribute 'Tilt' At Speed 60",
            "Store Sequence 201 Cue 1 'Wave'",
            "ClearAll",
            "Label Sequence 201 'My FX'",
        )

    def test_speed_bpm_shapes_the_phaser_rate(self):
        commands = build("wave", speed_bpm=95.5)
        assert "Attribute 'Tilt' At Speed 95.5" in commands
        bally = build("ballyhoo", speed_bpm=45)
        assert "Attribute 'Pan' At Speed 90" in bally  # 45 * the ballyhoo factor 2


class TestInvariants:
    @pytest.mark.parametrize("effect", POSITION_FX_EFFECTS)
    def test_head_is_always_destination_then_clear(self, effect):
        commands = build(effect)
        assert commands[0] == "ChangeDestination Root"
        assert commands[1] == "ClearAll"

    @pytest.mark.parametrize("effect", POSITION_FX_EFFECTS)
    def test_no_overwrite_anywhere(self, effect):
        assert not any("/Overwrite" in line for line in build(effect))

    @pytest.mark.parametrize("effect", POSITION_FX_EFFECTS)
    def test_tail_is_the_label_line(self, effect):
        assert build(effect)[-1] == "Label Sequence 201 'My FX'"

    @pytest.mark.parametrize("effect", POSITION_FX_EFFECTS)
    def test_every_store_is_cleared_before_the_label(self, effect):
        # Leftover programmer values TRACK into the next capture — every
        # Store is followed by a ClearAll (31_choreography_patterns.md:40-41).
        commands = build(effect)
        for index, line in enumerate(commands):
            if line.startswith("Store "):
                assert commands[index + 1] == "ClearAll"


class TestRefusals:
    def test_unknown_effect_is_refused(self):
        with pytest.raises(SpatialPointingError, match="unknown position fx effect"):
            build("strobe")

    def test_empty_fids_are_refused(self):
        with pytest.raises(SpatialPointingError, match="no fixtures"):
            build("sweep", fids=())

    def test_nonpositive_resolved_preset_number_is_refused(self):
        # t232 — the module no longer validates a bare "start"; each
        # RESOLVED preset number is validated instead (``preset_recall_
        # command``'s own guard), the same rule as every other consumer.
        broken = dict(_CONTIGUOUS_PRESET_NUMBERS)
        broken["Sweep L"] = 0
        with pytest.raises(SpatialPointingError, match="must be positive"):
            build("sweep", preset_numbers=broken)

    def test_a_label_missing_from_preset_numbers_is_refused(self):
        with pytest.raises(SpatialPointingError, match="no resolved preset number"):
            build("sweep", preset_numbers={})

    def test_nonpositive_sequence_number_is_refused(self):
        with pytest.raises(SpatialPointingError, match="must be positive"):
            build("circle", sequence_no=-1)

    def test_nonpositive_speed_is_refused(self):
        with pytest.raises(SpatialPointingError, match="positive finite BPM"):
            build("wave", speed_bpm=0)

    @pytest.mark.parametrize("label", ["it's", 'say "hi"', "", "   "])
    def test_quoted_or_empty_label_is_refused(self, label):
        with pytest.raises(SpatialPointingError, match="empty or carries a quote"):
            build("sweep", label=label)


class TestRelativeWaveLinesGeneralization:
    """Card t548 — REQ-LDBEAT-006(vi-2)(vi-3): ``wave`` generalizes to any
    non-empty subset of {Pan, Tilt} via an explicit ``axes`` parameter,
    without inventing a new shape name (감독 결정 2026-10-11 ①)."""

    def test_tilt_only_default_matches_the_pre_generalization_hardcoded_wave(self):
        # byte-identical to the old hardcoded wave branch (REQ carve-out —
        # position_fx_commands' own call path is untouched by this change).
        assert relative_wave_lines(frozenset({"Tilt"}), 60.0) == (
            "Attribute 'Tilt' At Relative -12",
            "Step 2",
            "Attribute 'Tilt' At Relative 12",
            "Step 1 At Accel -100",
            "Step 1 At Decel -100",
            "Step 2 At Accel -100",
            "Step 2 At Decel -100",
            "Attribute 'Tilt' At Phase 0 Thru 360",
            "Attribute 'Tilt' At Speed 60",
        )

    def test_pan_only_wave_swings_pan_not_tilt(self):
        lines = relative_wave_lines(frozenset({"Pan"}), 60.0)
        assert lines == (
            "Attribute 'Pan' At Relative -12",
            "Step 2",
            "Attribute 'Pan' At Relative 12",
            "Step 1 At Accel -100",
            "Step 1 At Decel -100",
            "Step 2 At Accel -100",
            "Step 2 At Decel -100",
            "Attribute 'Pan' At Phase 0 Thru 360",
            "Attribute 'Pan' At Speed 60",
        )
        assert not any("Tilt" in line for line in lines)

    def test_pan_and_tilt_wave_swings_both_in_pan_then_tilt_order(self):
        lines = relative_wave_lines(frozenset({"Pan", "Tilt"}), 56.0)
        assert lines == (
            "Attribute 'Pan' At Relative -12",
            "Attribute 'Tilt' At Relative -12",
            "Step 2",
            "Attribute 'Pan' At Relative 12",
            "Attribute 'Tilt' At Relative 12",
            "Step 1 At Accel -100",
            "Step 1 At Decel -100",
            "Step 2 At Accel -100",
            "Step 2 At Decel -100",
            "Attribute 'Pan' At Phase 0 Thru 360",
            "Attribute 'Tilt' At Phase 0 Thru 360",
            "Attribute 'Pan' At Speed 56",
            "Attribute 'Tilt' At Speed 56",
        )

    def test_phase_spread_false_omits_the_phase_lines_only(self):
        with_phase = relative_wave_lines(frozenset({"Pan"}), 60.0, phase_spread=True)
        without_phase = relative_wave_lines(frozenset({"Pan"}), 60.0, phase_spread=False)
        assert not any("At Phase" in line for line in without_phase)
        assert len(with_phase) == len(without_phase) + 1

    def test_empty_axes_is_refused(self):
        with pytest.raises(SpatialPointingError, match="non-empty subset"):
            relative_wave_lines(frozenset(), 60.0)

    def test_axes_outside_pan_tilt_is_refused(self):
        with pytest.raises(SpatialPointingError, match="non-empty subset"):
            relative_wave_lines(frozenset({"Zoom"}), 60.0)

    def test_position_fx_commands_wave_path_is_unaffected(self):
        # The existing byte-identical snapshot in TestBaseBundles::test_wave_full_bundle
        # already covers this end-to-end; this test pins the generalization
        # entry point specifically so a future edit to _relative_phaser_lines
        # cannot silently drop the delegation to relative_wave_lines.
        commands = build("wave")
        assert "Attribute 'Tilt' At Phase 0 Thru 360" in commands
        assert not any("Pan" in line for line in commands)


class TestTwoStepPhaser:
    """Card t540 — a base effect must be a real phaser: two steps, not one.

    grandMA3 only builds a phaser from two or more steps (MA Phasers manual;
    rulebook 33_effect_editors.md:21-22; server/fx/schema.py MIN_STEPS=2). The
    one-step ``At Relative`` bundle moved the beams once and then froze
    (t538 T3/A0 live, director: 「숫자가 멈춰 있음」). The two-step ±value
    shape moved (t538 T4/A0'/A1/A3), and a circle only reads round with the
    per-step curve lines (t538 A5b, director: 「동그란 원」).
    """

    BASE_EFFECTS = ("circle", "ballyhoo", "wave")

    @pytest.mark.parametrize("effect", BASE_EFFECTS)
    def test_bundle_opens_exactly_one_second_step(self, effect):
        assert build(effect).count("Step 2") == 1

    @pytest.mark.parametrize("effect", BASE_EFFECTS)
    def test_each_moving_axis_swings_minus_then_plus_around_step_two(self, effect):
        commands = list(build(effect))
        step_two = commands.index("Step 2")
        before = [line for line in commands[:step_two] if "At Relative" in line]
        after = [line for line in commands[step_two:] if "At Relative" in line]
        assert before and len(before) == len(after)
        for minus, plus in zip(before, after, strict=True):
            assert minus.replace("At Relative -", "At Relative ") == plus

    @pytest.mark.parametrize("effect", BASE_EFFECTS)
    def test_base_position_is_recalled_before_the_phaser(self, effect):
        # t538 A4: without a base position the phaser orbits the default
        # (vertical) aim, so the recall line must lead the step run.
        commands = list(build(effect))
        recall = next(i for i, line in enumerate(commands) if "At Preset 2." in line)
        first_relative = next(i for i, line in enumerate(commands) if "At Relative" in line)
        assert recall < first_relative

    @pytest.mark.parametrize("effect", BASE_EFFECTS)
    def test_every_step_carries_the_sine_curve(self, effect):
        commands = build(effect)
        for step in (1, 2):
            assert f"Step {step} At Accel -100" in commands
            assert f"Step {step} At Decel -100" in commands
