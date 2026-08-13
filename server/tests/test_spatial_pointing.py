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
    POINTING_TILT_LIMIT_DEGREES,
    PointingTarget,
    SpatialPointingError,
    aim_pan_tilt,
    pointing_commands,
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
