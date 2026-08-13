"""SPATIAL pointing — aim a moving head's beam at a 3D stage coordinate.

Converts a fixture's patched stage position (Posx/Posy/Posz, metres) plus a
target point into the ``Pan``/``Tilt`` attribute values (degrees) that make the
beam pass through the target.

Every convention here was MEASURED live on grandMA3 onPC 2.4.2 (2026-08-13,
NewShow_2026.08.08, RLB350M1/MMX rig, all patch rotations 0), by commanding
known values on one fixture and reading the beam landing off the 3D window:

* ``Attribute 'Pan'/'Tilt' At <n>`` takes PHYSICAL DEGREES (the console's
  Natural readout), not percent. ``At 45`` on Tilt produced a 45-degree beam
  cone; the full-rig convergence shot confirmed the arithmetic at 40 fixtures.
* ``Pan 0 / Tilt 0`` points the beam STRAIGHT DOWN (stage -Z).
* Positive Tilt swings the beam toward stage +Y (upstage) while Pan is 0.
* Positive Pan rotates that swing direction counter-clockwise seen from above
  (+Y -> -X at Pan +90).
* A fixture body rotation ``Rotz r`` rotates the Pan frame the SAME way, so
  the pan the console needs is the geometric pan minus ``r``. (``Rotx``/
  ``Roty`` were not measured; this module models zero for both — on the
  measured rig every patch rotation is zero.)

In vector form, with ``p``/``t`` in degrees and body ``Rotz`` zero, the beam
direction is::

    d = (-sin(p) * sin(t),  cos(p) * sin(t),  -cos(t))

which inverts, for the fixture-to-target vector ``v = target - fixture``, to::

    tilt = acos(-v_z / |v|)          # 0 = straight down
    pan  = atan2(-v_x, v_y) - rotz   # normalised into (-180, 180]

The write channel is the ordinary command line via ``run_commands`` (screened
and gated), exactly like ``arrange_fixtures`` — no new wire surface.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "POINTING_TILT_LIMIT_DEGREES",
    "PointingTarget",
    "SpatialPointingError",
    "aim_pan_tilt",
    "pointing_commands",
]


class SpatialPointingError(ValueError):
    """A pointing request this module refuses to turn into commands."""


#: Refusal ceiling for the computed tilt. The measured rig's heads (Robe
#: LEDBeam 350 / MMX) tilt at most ~±135 degrees physically; a computed tilt
#: beyond this means the fixture cannot reach the target through its front
#: hemisphere sweep and the honest answer is a refusal, not a clamped beam
#: that lands somewhere else.
POINTING_TILT_LIMIT_DEGREES = 135.0

#: Values are written to 0.1 degree. At the measured room scale (6 m trim) a
#: 0.1-degree quantisation moves the beam landing ~1 cm — far below the beam
#: diameter — while keeping the command text short and reproducible.
_VALUE_DECIMALS = 1


@dataclass(frozen=True)
class PointingTarget:
    """The stage point every named fixture's beam must pass through."""

    x: float
    y: float
    z: float

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


def _normalize_degrees(value: float) -> float:
    """Fold ``value`` into (-180, 180] — the minimal-swing pan choice."""
    folded = math.fmod(value + 180.0, 360.0)
    if folded <= 0.0:
        folded += 360.0
    return folded - 180.0


def aim_pan_tilt(
    position: tuple[float, float, float],
    target: tuple[float, float, float],
    *,
    rotz: float = 0.0,
) -> tuple[float, float]:
    """The (pan, tilt) degrees that aim a fixture at ``position`` toward ``target``.

    ``rotz`` is the fixture's patched body rotation about stage Z, degrees
    (measured: it offsets the pan frame one-for-one). Raises
    :class:`SpatialPointingError` when the target coincides with the fixture
    (no direction exists) or the required tilt exceeds
    :data:`POINTING_TILT_LIMIT_DEGREES`.
    """
    vx = target[0] - position[0]
    vy = target[1] - position[1]
    vz = target[2] - position[2]
    length = math.sqrt(vx * vx + vy * vy + vz * vz)
    if length < 1e-9:
        raise SpatialPointingError("fixture and target share a position — no beam direction exists")
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, -vz / length))))
    if tilt > POINTING_TILT_LIMIT_DEGREES:
        raise SpatialPointingError(
            f"required tilt {tilt:.1f}° exceeds the {POINTING_TILT_LIMIT_DEGREES:.0f}° "
            "refusal ceiling — the head cannot reach this target"
        )
    if vx == 0.0 and vy == 0.0:
        # Straight down (or up): pan is geometrically free; 0 minus the body
        # rotation keeps the head from spinning for no optical reason.
        pan = _normalize_degrees(-rotz)
    else:
        pan = _normalize_degrees(math.degrees(math.atan2(-vx, vy)) - rotz)
    return (round(pan, _VALUE_DECIMALS), round(tilt, _VALUE_DECIMALS))


def _format_value(value: float) -> str:
    """Degrees as command text: plain decimal, no trailing ``.0`` noise."""
    rounded = round(value, _VALUE_DECIMALS)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{_VALUE_DECIMALS}f}"


def pointing_commands(
    fixtures: Sequence[tuple[int, tuple[float, float, float]]],
    target: PointingTarget,
    *,
    dimmer: float | None = None,
    rotz_by_fid: dict[int, float] | None = None,
) -> tuple[str, ...]:
    """The command bundle that aims every ``(fid, position)`` at ``target``.

    ONE chained line per fixture — ``Fixture <fid> ; [Attribute 'Dimmer' At
    <n> ;] Attribute 'Pan' At <p> ; Attribute 'Tilt' At <t>`` — using the
    rulebook-validated ``;`` chaining (31_choreography_patterns.md). Chaining
    is not cosmetic: the execution path skips a command line whose TEXT it
    already ran in the same instruction, and on any symmetric rig two
    fixtures routinely need the same tilt, so per-attribute lines would be
    silently deduplicated away (measured live: 84 of 160 split lines came
    back ``skipped_already_executed``). The fid prefix makes every line
    unique. Values ride the programmer, so the approval gate and a later
    ``ClearAll`` behave exactly as for any manual look.
    """
    if not fixtures:
        raise SpatialPointingError("no fixtures to point")
    if dimmer is not None and not 0.0 <= dimmer <= 100.0:
        raise SpatialPointingError(f"dimmer {dimmer!r} is outside 0..100")
    seen: set[int] = set()
    commands: list[str] = []
    rotations = rotz_by_fid or {}
    for fid, position in fixtures:
        if fid in seen:
            raise SpatialPointingError(f"fid {fid} named twice")
        seen.add(fid)
        pan, tilt = aim_pan_tilt(position, target.as_tuple(), rotz=rotations.get(fid, 0.0))
        parts = [f"Fixture {fid}"]
        if dimmer is not None:
            parts.append(f"Attribute 'Dimmer' At {_format_value(dimmer)}")
        parts.append(f"Attribute 'Pan' At {_format_value(pan)}")
        parts.append(f"Attribute 'Tilt' At {_format_value(tilt)}")
        commands.append(" ; ".join(parts))
    return tuple(commands)
