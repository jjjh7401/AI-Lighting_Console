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
    "FAN_MODES",
    "POINTING_TILT_LIMIT_DEGREES",
    "POSITION_PRESET_POOL",
    "RADIAL_MODES",
    "PointingTarget",
    "SpatialPointingError",
    "aim_pan_tilt",
    "aimed_commands",
    "fan_pan_tilt",
    "pointing_commands",
    "position_preset_store_commands",
    "radial_pan_tilt",
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
    seen: set[int] = set()
    aims: list[tuple[int, float, float]] = []
    rotations = rotz_by_fid or {}
    for fid, position in fixtures:
        if fid in seen:
            raise SpatialPointingError(f"fid {fid} named twice")
        seen.add(fid)
        pan, tilt = aim_pan_tilt(position, target.as_tuple(), rotz=rotations.get(fid, 0.0))
        aims.append((fid, pan, tilt))
    return aimed_commands(aims, dimmer=dimmer)


#: The design-look (LOOK family) vocabularies — closed, like the spatial sorts.
#: ``out`` fans the ends away from the base direction, ``in`` mirrors that
#: toward it (converge), ``cross`` alternates the out-offsets' sign so
#: neighbouring beams cross (the FancyFAN "Crossed Fan" shape).
FAN_MODES = ("out", "in", "cross")

#: ``out`` aims every fixture away from the rig centre (beam lands on the
#: floor outside the ring), ``in`` converges every beam on one point of the
#: centre axis.
RADIAL_MODES = ("out", "in")

#: grandMA3's default Position preset pool number (`Preset 2.x`).
POSITION_PRESET_POOL = 2


def fan_pan_tilt(
    fids: Sequence[int],
    *,
    base_pan: float = 180.0,
    base_tilt: float = 45.0,
    spread: float = 30.0,
    mode: str = "out",
) -> tuple[tuple[int, float, float], ...]:
    """Per-fixture (fid, pan, tilt) for a fan look over an ORDERED chain.

    ``fids`` must already be in stage order (e.g. left-to-right) — the fan is
    a function of that order, exactly like MA3's own ``Align``: fixture ``i``
    of ``N`` gets a pan offset of ``spread * (2i/(N-1) - 1)`` around
    ``base_pan`` (linear distribution, the Align default). ``spread`` is the
    END fixture's offset in degrees, so the full aperture is ``2 * spread``.
    ``mode`` picks the design: ``out`` fans away, ``in`` converges (mirrored
    offsets), ``cross`` alternates the offset sign per fixture so the beams
    cross mid-air. The defaults (base pan 180 = downstage -Y, tilt 45) make a
    classic audience-facing fan on the measured axis conventions.
    """
    if not fids:
        raise SpatialPointingError("no fixtures to fan")
    if len(set(fids)) != len(fids):
        raise SpatialPointingError("a fid is named twice in the fan chain")
    if mode not in FAN_MODES:
        raise SpatialPointingError(f"{mode!r} is not a fan mode (allowed: {FAN_MODES})")
    if not 0.0 <= spread <= 180.0:
        raise SpatialPointingError(f"fan spread {spread!r} is outside 0..180 degrees")
    if abs(base_tilt) > POINTING_TILT_LIMIT_DEGREES:
        raise SpatialPointingError(
            f"fan base tilt {base_tilt!r} exceeds the "
            f"{POINTING_TILT_LIMIT_DEGREES:.0f} degree ceiling"
        )
    count = len(fids)
    aims: list[tuple[int, float, float]] = []
    for index, fid in enumerate(fids):
        offset = 0.0 if count == 1 else spread * (2.0 * index / (count - 1) - 1.0)
        if mode == "in" or mode == "cross" and index % 2 == 1:
            offset = -offset
        pan = _normalize_degrees(base_pan + offset)
        aims.append((fid, round(pan, _VALUE_DECIMALS), round(base_tilt, _VALUE_DECIMALS)))
    return tuple(aims)


def radial_pan_tilt(
    fixtures: Sequence[tuple[int, tuple[float, float, float]]],
    *,
    center: tuple[float, float] = (0.0, 0.0),
    mode: str = "out",
    reach: float = 4.0,
    height: float = 0.0,
) -> tuple[tuple[int, float, float], ...]:
    """Per-fixture (fid, pan, tilt) for a ring look around ``center``.

    ``out``: each beam lands on the floor ``reach`` metres OUTSIDE the
    fixture, along its own radial from the rig centre — the classic
    outward-facing ring. ``in``: every beam converges on the point
    ``(center, height)`` on the centre axis (``height`` in metres above the
    floor; 0 = the floor itself). A fixture standing ON the centre has no
    radial in ``out`` mode and is refused, never guessed.
    """
    if not fixtures:
        raise SpatialPointingError("no fixtures to aim radially")
    if mode not in RADIAL_MODES:
        raise SpatialPointingError(f"{mode!r} is not a radial mode (allowed: {RADIAL_MODES})")
    if mode == "out" and reach <= 0.0:
        raise SpatialPointingError(f"radial reach {reach!r} must be positive")
    cx, cy = center
    aims: list[tuple[int, float, float]] = []
    seen: set[int] = set()
    for fid, position in fixtures:
        if fid in seen:
            raise SpatialPointingError(f"fid {fid} named twice")
        seen.add(fid)
        fx, fy, fz = position
        if mode == "in":
            target = (cx, cy, height)
        else:
            dx, dy = fx - cx, fy - cy
            radial = math.hypot(dx, dy)
            if radial < 1e-9:
                raise SpatialPointingError(
                    f"fid {fid} stands on the ring centre — it has no outward radial"
                )
            target = (fx + dx / radial * reach, fy + dy / radial * reach, 0.0)
        pan, tilt = aim_pan_tilt((fx, fy, fz), target)
        aims.append((fid, pan, tilt))
    return tuple(aims)


def aimed_commands(
    aims: Sequence[tuple[int, float, float]],
    *,
    dimmer: float | None = None,
) -> tuple[str, ...]:
    """One chained command line per ``(fid, pan, tilt)`` aim.

    Same shape and same reason as :func:`pointing_commands`: the execution
    path dedupes repeated command TEXT within one instruction, so every line
    carries its ``Fixture <fid>`` prefix to stay unique.
    """
    if not aims:
        raise SpatialPointingError("no aims to render")
    if dimmer is not None and not 0.0 <= dimmer <= 100.0:
        raise SpatialPointingError(f"dimmer {dimmer!r} is outside 0..100")
    commands: list[str] = []
    for fid, pan, tilt in aims:
        parts = [f"Fixture {fid}"]
        if dimmer is not None:
            parts.append(f"Attribute 'Dimmer' At {_format_value(dimmer)}")
        parts.append(f"Attribute 'Pan' At {_format_value(pan)}")
        parts.append(f"Attribute 'Tilt' At {_format_value(tilt)}")
        commands.append(" ; ".join(parts))
    return tuple(commands)


def position_preset_store_commands(preset_no: int, label: str | None = None) -> tuple[str, ...]:
    """Store the programmer's current position values as ``Preset 2.<n>``.

    Run AFTER the aim bundle, while the values still sit in the programmer —
    cues built from the preset then hold a REFERENCE, so regenerating the
    preset re-focuses every cue that uses it. The label rides a separate
    ``Label`` line in single quotes (double quotes cannot be sent at all —
    ``server/bridge/protocol.py`` rejects them).
    """
    if preset_no <= 0:
        raise SpatialPointingError(f"preset number {preset_no!r} must be positive")
    commands = [f"Store Preset {POSITION_PRESET_POOL}.{preset_no}"]
    if label is not None:
        text = label.strip()
        if not text or "'" in text or '"' in text:
            raise SpatialPointingError(f"preset label {label!r} is empty or carries a quote")
        commands.append(f"Label Preset {POSITION_PRESET_POOL}.{preset_no} '{text}'")
    return tuple(commands)
