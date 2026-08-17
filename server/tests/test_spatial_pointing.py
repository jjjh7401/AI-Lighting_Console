"""SPATIAL pointing math — the measured pan/tilt aiming conventions.

Every directional assertion here mirrors a live 2026-08-13 onPC 2.4.2
measurement (see ``server/spatial/pointing.py`` module docstring): home is
straight down, positive tilt swings upstage (+Y), positive pan rotates that
swing +Y -> -X, ``Rotz`` offsets pan one-for-one, and the 40-fixture
convergence shot validated the inverse formula end to end.
"""

import math

import pytest

from server.spatial.pointing import (
    BASIC_POSITION_SEQUENCE,
    FX_POSITION_SEQUENCE,
    POINTING_TILT_LIMIT_DEGREES,
    PointingTarget,
    SpatialPointingError,
    aim_pan_tilt,
    aimed_commands,
    basic_position_presets,
    fan_chain,
    fan_pan_tilt,
    fx_position_presets,
    pointing_commands,
    position_cue_store_commands,
    position_preset_store_commands,
    preset_recall_command,
    radial_pan_tilt,
)


def _direction(pan: float, tilt: float) -> tuple[float, float, float]:
    """The measured forward model — beam direction for (pan, tilt) degrees."""
    p, t = math.radians(pan), math.radians(tilt)
    return (-math.sin(p) * math.sin(t), math.cos(p) * math.sin(t), -math.cos(t))


class TestMeasuredConventions:
    def test_home_points_straight_down(self):
        # Pan 0 / Tilt 0 landed the spot directly under the fixture.
        pan, tilt = aim_pan_tilt((4.0, 0.0, 6.0), (4.0, 0.0, 0.0))
        assert (pan, tilt) == (0.0, 0.0)

    def test_positive_tilt_swings_upstage(self):
        # Tilt +45 at Pan 0 moved the spot toward +Y.
        pan, tilt = aim_pan_tilt((0.0, 0.0, 6.0), (0.0, 6.0, 0.0))
        assert pan == 0.0
        assert tilt == 45.0

    def test_positive_pan_rotates_toward_minus_x(self):
        # Pan +90 / Tilt 45 landed the spot 6 m toward -X from the fixture foot.
        pan, tilt = aim_pan_tilt((4.0, 0.0, 6.0), (-2.0, 0.0, 0.0))
        assert pan == 90.0
        assert tilt == 45.0

    def test_the_live_verified_fixture_twenty_case(self):
        # FID 20 at (4, 0, 6) aimed at the origin: Pan 90 / Tilt 33.7 converged.
        pan, tilt = aim_pan_tilt((4.0, 0.0, 6.0), (0.0, 0.0, 0.0))
        assert pan == 90.0
        assert tilt == pytest.approx(33.7, abs=0.05)

    def test_rotz_offsets_pan_one_for_one(self):
        # Rotz +90 turned the Pan-0 swing direction from +Y to -X, so the same
        # geometric aim needs 90 degrees LESS pan.
        base_pan, base_tilt = aim_pan_tilt((4.0, 0.0, 6.0), (0.0, 0.0, 0.0))
        pan, tilt = aim_pan_tilt((4.0, 0.0, 6.0), (0.0, 0.0, 0.0), rotz=90.0)
        assert tilt == base_tilt
        assert pan == base_pan - 90.0


class TestInverseAgainstForwardModel:
    @pytest.mark.parametrize(
        "position,target",
        [
            ((4.0, 0.0, 6.0), (0.0, 0.0, 0.0)),
            ((-3.5267, 4.8541, 6.0), (0.0, 0.0, 0.0)),
            ((-6.0, 0.0, 6.0), (2.0, -3.0, 1.0)),
            ((1.8541, -5.7063, 6.0), (-1.0, 4.0, 0.5)),
            ((0.0, 0.0, 6.0), (0.0, 0.0, 0.0)),
        ],
    )
    def test_computed_pan_tilt_reproduces_the_target_direction(self, position, target):
        pan, tilt = aim_pan_tilt(position, target)
        d = _direction(pan, tilt)
        v = tuple(t - p for t, p in zip(target, position, strict=True))
        norm = math.sqrt(sum(c * c for c in v))
        unit = tuple(c / norm for c in v)
        assert d == pytest.approx(unit, abs=0.01)

    def test_pan_stays_in_the_minimal_swing_band(self):
        for x, y in [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)]:
            pan, _tilt = aim_pan_tilt((x, y, 6.0), (0.0, 0.0, 0.0))
            assert -180.0 < pan <= 180.0


class TestRefusals:
    def test_a_target_at_the_fixture_is_refused(self):
        with pytest.raises(SpatialPointingError, match="share a position"):
            aim_pan_tilt((1.0, 2.0, 3.0), (1.0, 2.0, 3.0))

    def test_a_target_above_the_tilt_ceiling_is_refused(self):
        # Aiming nearly straight UP needs tilt ~180 > the refusal ceiling.
        with pytest.raises(SpatialPointingError, match="refusal ceiling"):
            aim_pan_tilt((0.0, 0.0, 0.0), (0.0, 0.1, 10.0))
        assert POINTING_TILT_LIMIT_DEGREES == 135.0

    def test_an_empty_fixture_list_is_refused(self):
        with pytest.raises(SpatialPointingError, match="no fixtures"):
            pointing_commands([], PointingTarget(0.0, 0.0, 0.0))

    def test_a_duplicate_fid_is_refused(self):
        with pytest.raises(SpatialPointingError, match="named twice"):
            pointing_commands(
                [(1, (1.0, 0.0, 6.0)), (1, (2.0, 0.0, 6.0))],
                PointingTarget(0.0, 0.0, 0.0),
            )

    def test_an_out_of_band_dimmer_is_refused(self):
        with pytest.raises(SpatialPointingError, match="outside 0..100"):
            pointing_commands([(1, (1.0, 0.0, 6.0))], PointingTarget(0.0, 0.0, 0.0), dimmer=101.0)


class TestCommandBundle:
    def test_one_chained_line_per_fixture(self):
        commands = pointing_commands(
            [(20, (4.0, 0.0, 6.0))], PointingTarget(0.0, 0.0, 0.0), dimmer=100.0
        )
        assert commands == (
            "Fixture 20 ; Attribute 'Dimmer' At 100 ; "
            "Attribute 'Pan' At 90 ; Attribute 'Tilt' At 33.7",
        )

    def test_no_dimmer_clause_without_a_dimmer(self):
        commands = pointing_commands([(20, (4.0, 0.0, 6.0))], PointingTarget(0.0, 0.0, 0.0))
        assert commands == ("Fixture 20 ; Attribute 'Pan' At 90 ; Attribute 'Tilt' At 33.7",)

    def test_symmetric_fixtures_still_get_unique_lines(self):
        # The execution path dedupes REPEATED COMMAND TEXT within one
        # instruction (measured live: 84/160 split-line writes skipped), so
        # two fixtures sharing the same tilt MUST NOT share a line.
        commands = pointing_commands(
            [(1, (2.5, 0.0, 6.0)), (2, (-2.5, 0.0, 6.0))],
            PointingTarget(0.0, 0.0, 0.0),
        )
        assert len(commands) == len(set(commands)) == 2
        assert commands[0].startswith("Fixture 1 ; ")
        assert commands[1].startswith("Fixture 2 ; ")
        # The two mirrored fixtures need mirrored pans on the same tilt.
        assert "Attribute 'Pan' At 90" in commands[0]
        assert "Attribute 'Pan' At -90" in commands[1]
        tilts = {command.rsplit("At ", 1)[1] for command in commands}
        assert len(tilts) == 1


class TestFanLook:
    def test_a_linear_out_fan_spreads_symmetrically_around_the_base(self):
        aims = fan_pan_tilt([1, 2, 3, 4, 5], base_pan=180.0, base_tilt=45.0, spread=30.0)
        assert [pan for _fid, pan, _tilt in aims] == [150.0, 165.0, 180.0, -165.0, -150.0]
        assert all(tilt == 45.0 for _fid, _pan, tilt in aims)

    def test_in_mode_mirrors_the_out_offsets(self):
        out = fan_pan_tilt([1, 2, 3], spread=20.0, mode="out")
        in_ = fan_pan_tilt([1, 2, 3], spread=20.0, mode="in")
        assert [pan for _f, pan, _t in in_] == [pan for _f, pan, _t in reversed(out)]

    def test_cross_mode_alternates_the_offset_sign(self):
        aims = fan_pan_tilt([1, 2, 3, 4], base_pan=0.0, spread=30.0, mode="cross")
        offsets = [pan for _fid, pan, _tilt in aims]
        # out offsets for 4 fixtures: -30, -10, +10, +30; odd indices flip.
        assert offsets == [-30.0, 10.0, 10.0, -30.0]

    def test_a_single_fixture_fan_stays_on_the_base(self):
        assert fan_pan_tilt([7], base_pan=90.0, base_tilt=30.0, spread=45.0) == ((7, 90.0, 30.0),)

    def test_fan_refusals(self):
        with pytest.raises(SpatialPointingError, match="no fixtures"):
            fan_pan_tilt([])
        with pytest.raises(SpatialPointingError, match="named twice"):
            fan_pan_tilt([1, 1])
        with pytest.raises(SpatialPointingError, match="not a fan mode"):
            fan_pan_tilt([1, 2], mode="sideways")
        with pytest.raises(SpatialPointingError, match="outside 0..180"):
            fan_pan_tilt([1, 2], spread=181.0)
        with pytest.raises(SpatialPointingError, match="ceiling"):
            fan_pan_tilt([1, 2], base_tilt=140.0)

    def test_tilt_spread_makes_a_centre_symmetric_v(self):
        # The two-axis fan (Align <> on Tilt): centre fixture stays on the
        # base tilt, the END fixtures swing tilt_spread degrees further.
        aims = fan_pan_tilt([1, 2, 3, 4, 5], base_tilt=45.0, spread=30.0, tilt_spread=15.0)
        assert [tilt for _fid, _pan, tilt in aims] == [60.0, 52.5, 45.0, 52.5, 60.0]

    def test_negative_tilt_spread_drops_the_ends(self):
        aims = fan_pan_tilt([1, 2, 3], base_tilt=45.0, tilt_spread=-20.0)
        assert [tilt for _fid, _pan, tilt in aims] == [25.0, 45.0, 25.0]

    def test_a_zero_tilt_spread_keeps_the_flat_fan(self):
        aims = fan_pan_tilt([1, 2, 3], base_tilt=45.0)
        assert {tilt for _fid, _pan, tilt in aims} == {45.0}

    def test_an_end_fixture_over_the_ceiling_refuses_the_whole_fan(self):
        with pytest.raises(SpatialPointingError, match="end-fixture tilt"):
            fan_pan_tilt([1, 2], base_tilt=125.0, tilt_spread=15.0)
        with pytest.raises(SpatialPointingError, match="outside -90..90"):
            fan_pan_tilt([1, 2], tilt_spread=91.0)


class TestRadialLook:
    def test_out_mode_aims_every_fixture_away_from_the_centre(self):
        aims = radial_pan_tilt(
            [(20, (4.0, 0.0, 6.0)), (26, (-4.0, 0.0, 6.0))], mode="out", reach=6.0
        )
        # Outward target for FID 20 is (10, 0, 0): pan -90 (toward +X), and
        # the mirrored fixture gets the mirrored pan on the same tilt.
        by_fid = {fid: (pan, tilt) for fid, pan, tilt in aims}
        assert by_fid[20][0] == -90.0
        assert by_fid[26][0] == 90.0
        assert by_fid[20][1] == by_fid[26][1] == 45.0

    def test_in_mode_converges_on_the_centre_axis_at_height(self):
        aims = radial_pan_tilt(
            [(20, (4.0, 0.0, 6.0)), (26, (-4.0, 0.0, 6.0))], mode="in", height=2.0
        )
        by_fid = {fid: (pan, tilt) for fid, pan, tilt in aims}
        assert by_fid[20][0] == 90.0
        assert by_fid[26][0] == -90.0
        assert by_fid[20][1] == pytest.approx(45.0, abs=0.05)

    def test_a_fixture_on_the_centre_is_refused_outward(self):
        with pytest.raises(SpatialPointingError, match="no outward radial"):
            radial_pan_tilt([(41, (0.0, 0.0, 6.0))], mode="out")

    def test_radial_refusals(self):
        with pytest.raises(SpatialPointingError, match="not a radial mode"):
            radial_pan_tilt([(1, (1.0, 0.0, 6.0))], mode="up")
        with pytest.raises(SpatialPointingError, match="must be positive"):
            radial_pan_tilt([(1, (1.0, 0.0, 6.0))], mode="out", reach=0.0)


class TestAimedCommandsAndPresetStore:
    def test_aims_render_as_one_chained_line_each(self):
        commands = aimed_commands([(1, 150.0, 45.0), (2, -165.0, 45.0)], dimmer=100.0)
        assert commands == (
            "Fixture 1 ; Attribute 'Dimmer' At 100 ; "
            "Attribute 'Pan' At 150 ; Attribute 'Tilt' At 45",
            "Fixture 2 ; Attribute 'Dimmer' At 100 ; "
            "Attribute 'Pan' At -165 ; Attribute 'Tilt' At 45",
        )

    def test_the_preset_store_targets_the_position_pool(self):
        assert position_preset_store_commands(11, "FAN OUT") == (
            "Store Preset 2.11",
            "Label Preset 2.11 'FAN OUT'",
        )

    def test_a_bare_store_carries_no_label_line(self):
        assert position_preset_store_commands(3) == ("Store Preset 2.3",)

    def test_preset_store_refusals(self):
        with pytest.raises(SpatialPointingError, match="must be positive"):
            position_preset_store_commands(0)
        with pytest.raises(SpatialPointingError, match="quote"):
            position_preset_store_commands(1, "bad'name")


class TestPositionCueStore:
    """T1 (SPEC-COPILOT-CUETIME-001): preset-referenced cue with a fade."""

    def test_the_full_form_matches_the_verified_grammar(self):
        # 31_choreography_patterns.md:50 — sequence-explicit store + CueFade.
        assert position_cue_store_commands(101, 1, fade_seconds=5, name="Pos 2.28") == (
            "Store Sequence 101 Cue 1 'Pos 2.28' CueFade 5",
        )

    def test_fade_and_name_are_optional(self):
        assert position_cue_store_commands(101, 2) == ("Store Sequence 101 Cue 2",)

    def test_decimal_cue_numbers_render_without_noise(self):
        # Decimal cue numbers are the verified insert grammar (…:56) — the
        # MIB pre-move cue (T2) rides on them.
        assert position_cue_store_commands(101, 1.5, fade_seconds=0.5) == (
            "Store Sequence 101 Cue 1.5 CueFade 0.5",
        )

    def test_zero_fade_is_an_explicit_snap_not_an_omission(self):
        assert position_cue_store_commands(101, 1, fade_seconds=0) == (
            "Store Sequence 101 Cue 1 CueFade 0",
        )

    def test_refusals(self):
        with pytest.raises(SpatialPointingError, match="sequence number"):
            position_cue_store_commands(0, 1)
        with pytest.raises(SpatialPointingError, match="cue number"):
            position_cue_store_commands(101, 0)
        with pytest.raises(SpatialPointingError, match="fade"):
            position_cue_store_commands(101, 1, fade_seconds=-1)
        with pytest.raises(SpatialPointingError, match="fade"):
            position_cue_store_commands(101, 1, fade_seconds=float("inf"))
        with pytest.raises(SpatialPointingError, match="quote"):
            position_cue_store_commands(101, 1, name="bad'name")

    def test_preset_recall_is_one_selection_chained_line(self):
        # One line: the selection prefix keeps the text unique under the
        # instruction-scope dedupe (SKILL §3).
        assert preset_recall_command([20, 26], 28) == "Fixture 20 + 26 ; At Preset 2.28"

    def test_recall_refusals(self):
        with pytest.raises(SpatialPointingError, match="no fixtures"):
            preset_recall_command([], 28)
        with pytest.raises(SpatialPointingError, match="must be positive"):
            preset_recall_command([20], 0)


class TestBasicPositionSequence:
    # A two-fixture bar plus the origin marker — enough to exercise every
    # look family (uniform, focus, fan, radial) and the skip path.
    _FIXTURES = [
        (20, (4.0, 0.0, 6.0)),
        (26, (-4.0, 0.0, 6.0)),
        (41, (0.0, 0.0, 0.0)),
    ]

    def test_the_sequence_is_ten_looks_and_home_is_always_first(self):
        assert len(BASIC_POSITION_SEQUENCE) == 10
        assert BASIC_POSITION_SEQUENCE[0] == "Home"
        looks = basic_position_presets(self._FIXTURES)
        assert [label for label, _aims, _skipped in looks] == list(BASIC_POSITION_SEQUENCE)

    def test_home_points_every_fixture_straight_down(self):
        looks = dict(
            (label, aims) for label, aims, _skipped in basic_position_presets(self._FIXTURES)
        )
        assert looks["Home"] == ((20, 0.0, 0.0), (26, 0.0, 0.0), (41, 0.0, 0.0))

    def test_uniform_looks_share_one_angle_across_the_rig(self):
        looks = dict(
            (label, aims) for label, aims, _skipped in basic_position_presets(self._FIXTURES)
        )
        assert {(pan, tilt) for _fid, pan, tilt in looks["Wall"]} == {(180.0, 45.0)}
        assert {(pan, tilt) for _fid, pan, tilt in looks["Audience"]} == {(180.0, 100.0)}

    def test_focus_looks_are_derived_from_the_rig_centroid(self):
        # Centroid of the three fixtures is (0, 0): Center aims 20/26 at the
        # origin (the measured 90/33.7 case) and skips the marker ON it.
        by_label = {
            label: (aims, skipped)
            for label, aims, skipped in basic_position_presets(self._FIXTURES)
        }
        aims, skipped = by_label["Center"]
        assert (20, 90.0, 33.7) in aims
        assert (26, -90.0, 33.7) in aims
        assert skipped == (41,)

    def test_ring_out_skips_the_centroid_fixture_but_keeps_the_rest(self):
        by_label = {
            label: (aims, skipped)
            for label, aims, skipped in basic_position_presets(self._FIXTURES)
        }
        aims, skipped = by_label["Ring Out"]
        assert skipped == (41,)
        assert {fid for fid, _pan, _tilt in aims} == {20, 26}

    def test_an_empty_rig_is_refused(self):
        with pytest.raises(SpatialPointingError, match="no fixtures"):
            basic_position_presets([])


class TestFanChain:
    def test_a_cross_stage_bar_chains_left_to_right(self):
        fixtures = [(2, (0.0, 0.0, 6.0)), (1, (-3.0, 0.0, 6.0)), (3, (3.0, 0.0, 6.0))]
        assert fan_chain(fixtures) == (1, 2, 3)

    def test_a_front_to_back_bar_chains_along_y(self):
        # No x structure to ride: the dominant axis is depth, so the chain
        # follows y ascending instead of collapsing into the fid tie-break.
        fixtures = [(2, (0.0, 0.0, 6.0)), (1, (0.0, 4.0, 6.0)), (3, (0.0, -4.0, 6.0))]
        assert fan_chain(fixtures) == (3, 2, 1)

    def test_a_tie_falls_back_to_the_measured_x_convention(self):
        # A square spans both axes equally: x wins, fid breaks the remainder.
        fixtures = [
            (4, (1.0, 1.0, 6.0)),
            (1, (-1.0, -1.0, 6.0)),
            (3, (1.0, -1.0, 6.0)),
            (2, (-1.0, 1.0, 6.0)),
        ]
        assert fan_chain(fixtures) == (1, 2, 3, 4)

    def test_an_empty_chain_is_refused(self):
        with pytest.raises(SpatialPointingError, match="no fixtures"):
            fan_chain([])


class TestFxPositionSequence:
    # A symmetric two-fixture bar carries the mirror/sweep symmetry checks;
    # a three-fixture bar exercises the chain-ordered looks (tail, floor fan).
    _BAR = [(20, (4.0, 0.0, 6.0)), (26, (-4.0, 0.0, 6.0))]
    _TRIO = [(1, (-4.0, 0.0, 6.0)), (2, (0.0, 0.0, 6.0)), (3, (4.0, 0.0, 6.0))]

    @staticmethod
    def _by_label(fixtures):
        return {label: (aims, skipped) for label, aims, skipped in fx_position_presets(fixtures)}

    def test_the_sequence_is_exactly_the_ten_fx_labels(self):
        assert FX_POSITION_SEQUENCE == (
            "Sweep L",
            "Sweep R",
            "Sky Out",
            "Floor Base",
            "Circle Base",
            "Bally Base",
            "Tail",
            "Mirror Split",
            "Fan Floor",
            "Aisle Punch",
        )

    def test_the_return_shape_mirrors_the_basic_presets(self):
        looks = fx_position_presets(self._TRIO)
        assert [label for label, _aims, _skipped in looks] == list(FX_POSITION_SEQUENCE)
        all_fids = {fid for fid, _position in self._TRIO}
        for _label, aims, skipped in looks:
            assert isinstance(aims, tuple) and isinstance(skipped, tuple)
            assert {fid for fid, _pan, _tilt in aims} | set(skipped) == all_fids

    def test_the_sweep_endpoints_are_pan_mirrors_on_a_symmetric_rig(self):
        by_label = self._by_label(self._BAR)
        left = {fid: (pan, tilt) for fid, pan, tilt in by_label["Sweep L"][0]}
        right = {fid: (pan, tilt) for fid, pan, tilt in by_label["Sweep R"][0]}
        # Mirroring x mirrors the fixture too: 20 (x=+4) against the left
        # endpoint is the mirror image of 26 (x=-4) against the right one.
        for fid, mirror_fid in ((20, 26), (26, 20)):
            assert left[fid][0] == -right[mirror_fid][0]
            assert left[fid][1] == right[mirror_fid][1]

    def test_sky_out_and_circle_base_are_uniform_headroom_angles(self):
        by_label = self._by_label(self._BAR)
        assert POINTING_TILT_LIMIT_DEGREES - 15.0 == 120.0
        assert {(pan, tilt) for _fid, pan, tilt in by_label["Sky Out"][0]} == {(180.0, 120.0)}
        assert {(pan, tilt) for _fid, pan, tilt in by_label["Circle Base"][0]} == {(180.0, 40.0)}

    def test_floor_base_puts_each_beam_at_its_own_feet(self):
        by_label = self._by_label(self._BAR)
        aims = {fid: (pan, tilt) for fid, pan, tilt in by_label["Floor Base"][0]}
        assert aims[20] == aim_pan_tilt((4.0, 0.0, 6.0), (4.0, -1.5, 0.0))
        assert aims[26] == aim_pan_tilt((-4.0, 0.0, 6.0), (-4.0, -1.5, 0.0))

    def test_bally_base_keeps_the_out_fan_pans_at_the_wobble_tilt(self):
        by_label = self._by_label(self._TRIO)
        fan = fan_pan_tilt(list(fan_chain(self._TRIO)), mode="out")
        assert [(fid, pan) for fid, pan, _tilt in by_label["Bally Base"][0]] == [
            (fid, pan) for fid, pan, _tilt in fan
        ]
        assert {tilt for _fid, _pan, tilt in by_label["Bally Base"][0]} == {60.0}

    def test_the_tail_chain_closes_its_loop(self):
        by_label = self._by_label(self._TRIO)
        aims = {fid: (pan, tilt) for fid, pan, tilt in by_label["Tail"][0]}
        # Chain order is 1→2→3; each fixture chases its predecessor's floor
        # point and the FIRST chases the LAST one's, closing the loop.
        assert aims[1] == aim_pan_tilt((-4.0, 0.0, 6.0), (4.0, 0.0, 0.0))
        assert aims[2] == aim_pan_tilt((0.0, 0.0, 6.0), (-4.0, 0.0, 0.0))
        assert aims[3] == aim_pan_tilt((4.0, 0.0, 6.0), (0.0, 0.0, 0.0))

    def test_mirror_split_crosses_the_two_halves(self):
        by_label = self._by_label(self._BAR)
        pans = {fid: pan for fid, pan, _tilt in by_label["Mirror Split"][0]}
        # The right fixture leans left (+pan on the measured convention) and
        # the left one leans right: opposite signs = the beams cross.
        assert pans[20] > 0.0 > pans[26]
        assert pans[20] == -pans[26]

    def test_fan_floor_lands_on_equally_spaced_points(self):
        by_label = self._by_label(self._TRIO)
        aims = list(by_label["Fan Floor"][0])
        # Landing xs are -5, 0, +5 — the rig span plus the 1 m margins split
        # equally. Verify each aim by re-deriving it from its landing point.
        assert aims == [
            (1, *aim_pan_tilt((-4.0, 0.0, 6.0), (-5.0, -2.0, 0.0))),
            (2, *aim_pan_tilt((0.0, 0.0, 6.0), (0.0, -2.0, 0.0))),
            (3, *aim_pan_tilt((4.0, 0.0, 6.0), (5.0, -2.0, 0.0))),
        ]
        # The pans swing monotonically across downstage; fold the ±180 wrap
        # into 0..360 to see the monotone run.
        unwrapped = [pan % 360.0 for _fid, pan, _tilt in aims]
        assert unwrapped == sorted(unwrapped)
        assert len(set(unwrapped)) == 3

    def test_aisle_punch_skips_a_fixture_past_the_tilt_ceiling(self):
        # A sub-stage marker 7 m below deck would have to tilt >135° up to
        # reach the knee-height punch point — refused, skipped by name, and
        # absent from the aims.
        fixtures = [*self._BAR, (43, (0.0, 0.0, -7.0))]
        aims, skipped = self._by_label(fixtures)["Aisle Punch"]
        assert skipped == (43,)
        assert {fid for fid, _pan, _tilt in aims} == {20, 26}

    def test_an_empty_rig_is_refused(self):
        with pytest.raises(SpatialPointingError, match="no fixtures"):
            fx_position_presets([])
