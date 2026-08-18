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
    "BASIC_POSITION_SEQUENCE",
    "FAN_MODES",
    "FX_POSITION_SEQUENCE",
    "POINTING_TILT_LIMIT_DEGREES",
    "POSITION_PRESET_POOL",
    "RADIAL_MODES",
    "PointingTarget",
    "SpatialPointingError",
    "aim_pan_tilt",
    "aimed_commands",
    "basic_position_presets",
    "fan_chain",
    "fan_pan_tilt",
    "fx_position_presets",
    "pointing_commands",
    "position_cue_store_commands",
    "position_preset_store_commands",
    "preset_recall_command",
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
    tilt_spread: float = 0.0,
) -> tuple[tuple[int, float, float], ...]:
    """Per-fixture (fid, pan, tilt) for a fan look over an ORDERED chain.

    ``fids`` must already be in stage order (e.g. left-to-right) — the fan is
    a function of that order, exactly like MA3's own ``Align``: fixture ``i``
    of ``N`` gets a pan offset of ``spread * (2i/(N-1) - 1)`` around
    ``base_pan`` (linear distribution, ``Align /``). ``spread`` is the END
    fixture's offset in degrees, so the full aperture is ``2 * spread``.
    ``mode`` picks the design: ``out`` fans away, ``in`` converges (mirrored
    offsets), ``cross`` alternates the offset sign per fixture so the beams
    cross mid-air.

    ``tilt_spread`` adds the SECOND axis of the classic spread-rig fan
    (``Align <>`` on Tilt): a centre-symmetric V where the middle fixture
    stays on ``base_tilt`` and the END fixtures swing ``tilt_spread`` degrees
    further (negative = ends lower). Combined with the pan spread this is the
    "부채살 pan/tilt 모두" look common on bars, semicircles, triangles and
    squares. Every resulting tilt must clear the physical ceiling — one
    over-range end fixture refuses the whole fan rather than bending it.

    The defaults (base pan 180 = downstage -Y, tilt 45) make a classic
    audience-facing fan on the measured axis conventions.
    """
    if not fids:
        raise SpatialPointingError("no fixtures to fan")
    if len(set(fids)) != len(fids):
        raise SpatialPointingError("a fid is named twice in the fan chain")
    if mode not in FAN_MODES:
        raise SpatialPointingError(f"{mode!r} is not a fan mode (allowed: {FAN_MODES})")
    if not 0.0 <= spread <= 180.0:
        raise SpatialPointingError(f"fan spread {spread!r} is outside 0..180 degrees")
    if abs(tilt_spread) > 90.0:
        raise SpatialPointingError(f"fan tilt spread {tilt_spread!r} is outside -90..90 degrees")
    if abs(base_tilt) > POINTING_TILT_LIMIT_DEGREES:
        raise SpatialPointingError(
            f"fan base tilt {base_tilt!r} exceeds the "
            f"{POINTING_TILT_LIMIT_DEGREES:.0f} degree ceiling"
        )
    if abs(base_tilt) + abs(tilt_spread) > POINTING_TILT_LIMIT_DEGREES:
        raise SpatialPointingError(
            f"end-fixture tilt {abs(base_tilt) + abs(tilt_spread):.1f}° exceeds the "
            f"{POINTING_TILT_LIMIT_DEGREES:.0f} degree ceiling"
        )
    count = len(fids)
    aims: list[tuple[int, float, float]] = []
    for index, fid in enumerate(fids):
        position = 0.0 if count == 1 else 2.0 * index / (count - 1) - 1.0
        offset = spread * position
        if mode == "in" or mode == "cross" and index % 2 == 1:
            offset = -offset
        pan = _normalize_degrees(base_pan + offset)
        tilt = base_tilt + tilt_spread * abs(position)
        aims.append((fid, round(pan, _VALUE_DECIMALS), round(tilt, _VALUE_DECIMALS)))
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


def preset_recall_command(fids: Sequence[int], preset_no: int) -> str:
    """One selection line that recalls ``Preset 2.<n>`` into the programmer.

    ``Fixture a + b + … ; At Preset 2.<n>`` — the cue stored from this state
    holds a REFERENCE to the preset (32_spatial_design.md), so regenerating
    the preset at a new venue re-focuses every cue built on it. One single
    line: the selection prefix keeps the text unique under the instruction-
    scope command dedupe.
    """
    if not fids:
        raise SpatialPointingError("no fixtures to recall the preset on")
    if preset_no <= 0:
        raise SpatialPointingError(f"preset number {preset_no!r} must be positive")
    selection = " + ".join(str(fid) for fid in fids)
    return f"Fixture {selection} ; At Preset {POSITION_PRESET_POOL}.{preset_no}"


def _format_cue_no(cue_no: float) -> str:
    """Cue numbers carry decimals (insert with 1.5) — render without noise."""
    if float(cue_no).is_integer():
        return str(int(cue_no))
    return f"{cue_no:g}"


def position_cue_store_commands(
    sequence_no: int,
    cue_no: float,
    *,
    fade_seconds: float | None = None,
    name: str | None = None,
) -> tuple[str, ...]:
    """Store the programmer as a cue with an optional position fade.

    Verified grammar: ``Store Sequence 11 Cue 1 'Warm Wash' CueFade 2``
    (31_choreography_patterns.md:50) — the sequence-explicit form, so the cue
    never lands in whatever sequence happens to be selected. No ``/Merge`` or
    ``/Overwrite`` flag ever: merging flattens phasers living in the cue
    (measured — SKILL §3) and overwrite is blacklisted; the caller targets an
    empty cue slot. ``fade_seconds`` is the CueFade — omit it to keep the
    console default.
    """
    if sequence_no <= 0:
        raise SpatialPointingError(f"sequence number {sequence_no!r} must be positive")
    if not math.isfinite(cue_no) or cue_no <= 0:
        raise SpatialPointingError(f"cue number {cue_no!r} must be a positive finite number")
    command = f"Store Sequence {sequence_no} Cue {_format_cue_no(cue_no)}"
    if name is not None:
        text = name.strip()
        if not text or "'" in text or '"' in text:
            raise SpatialPointingError(f"cue name {name!r} is empty or carries a quote")
        command += f" '{text}'"
    if fade_seconds is not None:
        if not math.isfinite(fade_seconds) or fade_seconds < 0:
            raise SpatialPointingError(
                f"fade {fade_seconds!r} must be a non-negative finite number of seconds"
            )
        command += f" CueFade {fade_seconds:g}"
    return (command,)


#: The ten canonical design positions, most basic first, variation growing —
#: derived from the researched vocabulary (straight-down "Godspot", parallel
#: beam curtains, audience/house beams, focus points, fans, crossed beams,
#: radial rings — see docs/proposals/pan-tilt-position-preset-strategy.md).
#: Slot 1 is ALWAYS "Home". The sequence is a contract: preset numbers are
#: allocated in exactly this order.
BASIC_POSITION_SEQUENCE: tuple[str, ...] = (
    "Home",
    "Wall",
    "Audience",
    "Center",
    "Vocal DSC",
    "Fan Out",
    "Fan In",
    "Cross",
    "Ring Out",
    "Ring In",
)

#: The fixed angles behind the uniform looks. Wall = the parallel downstage
#: beam curtain (base fan direction with zero spread); Audience = the same
#: pan swung past horizontal into the house air, still inside the tilt
#: ceiling.
_WALL_PAN, _WALL_TILT = 180.0, 45.0
_AUDIENCE_PAN, _AUDIENCE_TILT = 180.0, 100.0
#: Focus-point geometry derived from the rig itself, so the same ten names
#: work on a bar, a ring, a rectangle or a triangle: the centre is the rig
#: centroid, the vocal point sits 2 m downstage (-Y) of the rig's front edge
#: at standing-person height, and the converge cone meets 3 m above the
#: centroid.
_VOCAL_DOWNSTAGE_OFFSET = 2.0
_VOCAL_HEIGHT = 1.6
_RING_IN_HEIGHT = 3.0

#: The ten FX skeleton positions — each one is the BASE a phaser effect
#: swings around (sweeps, jumps, circles, ballyhoos, waves, tails, mirrors),
#: not a finished look by itself. Like BASIC_POSITION_SEQUENCE the sequence
#: is a contract: preset numbers are allocated in exactly this order.
FX_POSITION_SEQUENCE: tuple[str, ...] = (
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

#: FX skeleton geometry. Every number is either a phaser's wobble headroom
#: or a landing margin, derived from the rig the same way as the design-look
#: constants above.
#: Sweep endpoints land 2 m OUTSIDE the rig's x span so a pan phaser running
#: A→B carries every beam past the end fixtures instead of stopping on them.
_SWEEP_SIDE_MARGIN = 2.0
#: The fly-out arrival beam keeps 15 degrees under the tilt refusal ceiling
#: so a tilt phaser wobbling around it never trips the refusal.
_SKY_OUT_TILT_MARGIN = 15.0
#: Tilt sweeps and waves start from each fixture's own floor spot 1.5 m
#: downstage of its feet — steep enough to read as "down", still aimable.
_FLOOR_BASE_DOWNSTAGE_OFFSET = 1.5
#: Circle / figure-8 phasers wobble BOTH axes around this base: pan 180
#: faces the house, tilt 40 leaves headroom toward 0 AND the 135 ceiling.
_CIRCLE_BASE_PAN, _CIRCLE_BASE_TILT = 180.0, 40.0
#: Ballyhoo random phasers wobble around a mid tilt — 60 sits between the
#: floor fan (45) and the horizon so excursions stay visible both ways.
_BALLY_BASE_TILT = 60.0
#: The straight landing row of the floor fan overshoots the rig ends by 1 m
#: so the end beams visibly splay outward instead of pointing straight down.
_FAN_FLOOR_SIDE_MARGIN = 1.0
#: The landing row sits 2 m downstage of the rig's front edge — on the
#: apron, where an equal-spacing row of hits reads as one straight line.
_FAN_FLOOR_DOWNSTAGE_OFFSET = 2.0
#: The aisle punch point is 6 m into the house — past the vocal point, deep
#: enough that a steeply-hung fixture may legitimately refuse (and be
#: skipped) rather than bend the look.
_AISLE_PUNCH_DOWNSTAGE_OFFSET = 6.0
#: Punch height 0.5 m: knee height still reads as a floor hit while keeping
#: the beams off a grazing flat-floor angle.
_AISLE_PUNCH_HEIGHT = 0.5


def fan_chain(
    fixtures: Sequence[tuple[int, tuple[float, float, float]]],
) -> tuple[int, ...]:
    """The fan's fixture order — along the rig's DOMINANT horizontal axis.

    A fan is a function of the chain order, and the chain must follow the
    axis the rig actually extends along: a bar hung ACROSS the stage fans
    left-to-right (x ascending), but a bar hung front-to-back has no x
    structure to ride — there the chain follows y. The wider horizontal span
    wins; a tie (a ring, a square) falls back to x, which is the measured
    left-to-right convention. fid is the documented tie-break within the
    axis, same as the spatial sorts.
    """
    if not fixtures:
        raise SpatialPointingError("no fixtures to chain")
    xs = [position[0] for _fid, position in fixtures]
    ys = [position[1] for _fid, position in fixtures]
    axis = 1 if (max(ys) - min(ys)) > (max(xs) - min(xs)) else 0
    ordered = sorted(fixtures, key=lambda item: (item[1][axis], item[0]))
    return tuple(fid for fid, _position in ordered)


def basic_position_presets(
    fixtures: Sequence[tuple[int, tuple[float, float, float]]],
) -> tuple[tuple[str, tuple[tuple[int, float, float], ...], tuple[int, ...]], ...]:
    """The ten basic looks for THIS rig — ``(label, aims, skipped_fids)`` each.

    Everything is derived from the fixtures' own patch coordinates, so the
    same sequence adapts to any placement design (bar, ring, rectangle,
    triangle, semicircle): the centroid anchors Center/Ring, the bounding
    box's front edge anchors the vocal point, and the fans ride the x-ordered
    chain. A fixture a look cannot aim (standing on its target or past the
    tilt ceiling) is skipped AND named — never clamped, and one impossible
    fixture never voids the other nine looks.
    """
    if not fixtures:
        raise SpatialPointingError("no fixtures to build basic positions for")
    xs = [position[0] for _fid, position in fixtures]
    ys = [position[1] for _fid, position in fixtures]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    front_y = min(ys)
    ordered_fids = list(fan_chain(fixtures))

    def _focus(target: tuple[float, float, float]) -> tuple[tuple, tuple]:
        aims: list[tuple[int, float, float]] = []
        skipped: list[int] = []
        for fid, position in fixtures:
            try:
                pan, tilt = aim_pan_tilt(position, target)
            except SpatialPointingError:
                skipped.append(fid)
            else:
                aims.append((fid, pan, tilt))
        return tuple(aims), tuple(skipped)

    def _radial(mode: str, **kwargs: float) -> tuple[tuple, tuple]:
        aims: list[tuple[int, float, float]] = []
        skipped: list[int] = []
        for fid, position in fixtures:
            try:
                aims.extend(
                    radial_pan_tilt([(fid, position)], center=(cx, cy), mode=mode, **kwargs)
                )
            except SpatialPointingError:
                skipped.append(fid)
        return tuple(aims), tuple(skipped)

    def _uniform(pan: float, tilt: float) -> tuple[tuple, tuple]:
        return tuple((fid, pan, tilt) for fid, _position in fixtures), ()

    center_aims = _focus((cx, cy, 0.0))
    vocal_aims = _focus((cx, front_y - _VOCAL_DOWNSTAGE_OFFSET, _VOCAL_HEIGHT))
    looks: dict[str, tuple[tuple, tuple]] = {
        "Home": _uniform(0.0, 0.0),
        "Wall": _uniform(_WALL_PAN, _WALL_TILT),
        "Audience": _uniform(_AUDIENCE_PAN, _AUDIENCE_TILT),
        "Center": center_aims,
        "Vocal DSC": vocal_aims,
        "Fan Out": (fan_pan_tilt(ordered_fids, mode="out"), ()),
        "Fan In": (fan_pan_tilt(ordered_fids, mode="in"), ()),
        "Cross": (fan_pan_tilt(ordered_fids, mode="cross"), ()),
        "Ring Out": _radial("out"),
        "Ring In": _radial("in", height=_RING_IN_HEIGHT),
    }
    return tuple((label, *looks[label]) for label in BASIC_POSITION_SEQUENCE)


def fx_position_presets(
    fixtures: Sequence[tuple[int, tuple[float, float, float]]],
) -> tuple[tuple[str, tuple[tuple[int, float, float], ...], tuple[int, ...]], ...]:
    """The ten FX skeleton positions for THIS rig — ``(label, aims, skipped_fids)``.

    Same shape and rules as :func:`basic_position_presets`, but every entry
    is the BASE a phaser swings around: the sweep endpoints, the fly-out
    arrival, the tilt-wave floor, the circle/bally wobble centres, the tail
    chain, the mirror cross, the equal-spacing floor fan and the aisle
    punch. All point aims go through :func:`aim_pan_tilt`; a fixture a look
    cannot aim is skipped AND named — never clamped, and one impossible
    fixture never voids the other looks.
    """
    if not fixtures:
        raise SpatialPointingError("no fixtures to build FX positions for")
    xs = [position[0] for _fid, position in fixtures]
    ys = [position[1] for _fid, position in fixtures]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    min_x, max_x = min(xs), max(xs)
    front_y = min(ys)
    by_fid = dict(fixtures)
    ordered = [(fid, by_fid[fid]) for fid in fan_chain(fixtures)]

    def _aim_each(
        pairs: Sequence[tuple[int, tuple[float, float, float], tuple[float, float, float]]],
    ) -> tuple[tuple, tuple]:
        aims: list[tuple[int, float, float]] = []
        skipped: list[int] = []
        for fid, position, target in pairs:
            try:
                pan, tilt = aim_pan_tilt(position, target)
            except SpatialPointingError:
                skipped.append(fid)
            else:
                aims.append((fid, pan, tilt))
        return tuple(aims), tuple(skipped)

    def _focus(target: tuple[float, float, float]) -> tuple[tuple, tuple]:
        return _aim_each([(fid, position, target) for fid, position in fixtures])

    def _uniform(pan: float, tilt: float) -> tuple[tuple, tuple]:
        return tuple((fid, pan, tilt) for fid, _position in fixtures), ()

    # Tail: fixture i chases the floor point under its chain predecessor;
    # index -1 closes the loop (the first fixture chases the last one).
    tail_pairs = [
        (fid, position, (ordered[index - 1][1][0], ordered[index - 1][1][1], 0.0))
        for index, (fid, position) in enumerate(ordered)
    ]
    # Mirror Split: each half aims at the FAR side's floor edge so the two
    # halves cross mid-stage.
    mirror_pairs = [
        (fid, position, ((max_x, cy, 0.0) if position[0] <= cx else (min_x, cy, 0.0)))
        for fid, position in fixtures
    ]
    # Fan Floor: equal-spacing LANDING points (not equal pan splits) on one
    # straight downstage row, one per chain slot.
    fan_left = min_x - _FAN_FLOOR_SIDE_MARGIN
    fan_right = max_x + _FAN_FLOOR_SIDE_MARGIN
    fan_floor_y = front_y - _FAN_FLOOR_DOWNSTAGE_OFFSET
    count = len(ordered)
    fan_floor_pairs = [
        (
            fid,
            position,
            (
                cx if count == 1 else fan_left + index * (fan_right - fan_left) / (count - 1),
                fan_floor_y,
                0.0,
            ),
        )
        for index, (fid, position) in enumerate(ordered)
    ]
    # Bally Base: the out-fan's pan fan with every tilt moved to the bally
    # wobble centre.
    bally_aims = tuple(
        (fid, pan, _BALLY_BASE_TILT)
        for fid, pan, _tilt in fan_pan_tilt([fid for fid, _position in ordered], mode="out")
    )

    looks: dict[str, tuple[tuple, tuple]] = {
        "Sweep L": _focus((min_x - _SWEEP_SIDE_MARGIN, cy, 0.0)),
        "Sweep R": _focus((max_x + _SWEEP_SIDE_MARGIN, cy, 0.0)),
        "Sky Out": _uniform(180.0, POINTING_TILT_LIMIT_DEGREES - _SKY_OUT_TILT_MARGIN),
        "Floor Base": _aim_each(
            [
                (fid, position, (position[0], position[1] - _FLOOR_BASE_DOWNSTAGE_OFFSET, 0.0))
                for fid, position in fixtures
            ]
        ),
        "Circle Base": _uniform(_CIRCLE_BASE_PAN, _CIRCLE_BASE_TILT),
        "Bally Base": (bally_aims, ()),
        "Tail": _aim_each(tail_pairs),
        "Mirror Split": _aim_each(mirror_pairs),
        "Fan Floor": _aim_each(fan_floor_pairs),
        "Aisle Punch": _focus((cx, front_y - _AISLE_PUNCH_DOWNSTAGE_OFFSET, _AISLE_PUNCH_HEIGHT)),
    }
    return tuple((label, *looks[label]) for label in FX_POSITION_SEQUENCE)
