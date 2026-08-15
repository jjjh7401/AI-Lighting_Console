"""FX schema — the shared data shape of the effect layer (REQ-FXLIB-001/003/004).

An fx is one movement pattern: a closed pattern kind, an ordered STEP AXIS of
absolute attribute values, and the modifier axes (phase spread, speed, relative
amplitude, reverse, MAtricks division) that ride on top of the phaser those
steps create. Rig binding happens at instantiation time, never here.

The attribute vocabulary is fx-owned and split into two bands (REQ-FXLIB-003):

1. Measured / literal-backed — ``Dimmer`` (the M0 [실측] anchor) and the three
   ``ColorRGB_*`` channels (31_choreography_patterns.md:75, multi-step colours).
2. Movement — ``Pan`` / ``Tilt``, legal only inside a phaser. As a static value
   they are exactly the hard pan/tilt the SPEC forbids.

The former probe-pending band (``At Accel`` / ``At Decel``) opened on the
2026-08-15 live session (SPEC-COPILOT-FXGEN-001 spec.md §A): the
curve axes below are now measured vocabulary, valued per entry.

# @MX:NOTE: [AUTO] the closed field set is the mechanism enforcing
#   REQ-FXLIB-004: there is no group, sequence, cue, FID or executor field to
#   put a per-show value in, and the loader rejects unknown keys so one cannot
#   be added by accident. `server/looks/schema.py` is the mirror original; this
#   package deliberately owns its own definitions rather than extending that
#   one, which is PRESERVE (design.md §3).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

FX_SCHEMA_VERSION = 1

# spec.md §A — 4 unconditional patterns plus the 2 that entered on the
# ASSUMPTION-37 GO recorded by the M0 live probe (progress.md §E.2).
PATTERN_KINDS: tuple[str, ...] = (
    "sweep",
    "wave",
    "circle",
    "diagonal",
    "pulse",
    "chase",
)

# Band 1 — Dimmer is the only attribute M0 measured end to end; the ColorRGB
# channels back `chase` off the rulebook's multi-step colour literal.
MEASURED_ATTRIBUTES: tuple[str, ...] = (
    "Dimmer",
    "ColorRGB_R",
    "ColorRGB_G",
    "ColorRGB_B",
)

# Band 2 — movement-only (31_choreography_patterns.md:69).
MOVEMENT_ATTRIBUTES: tuple[str, ...] = ("Pan", "Tilt")

KNOWN_ATTRIBUTES = frozenset(MEASURED_ATTRIBUTES + MOVEMENT_ATTRIBUTES)

# @MX:ANCHOR: [AUTO] a phaser requires two or more steps. Every consumer of this
#   schema (loader, library assets, bundle builder) depends on that invariant.
# @MX:REASON: M0 measured that `Relative`/`Phase`/`Speed` MODIFY an existing
#   phaser rather than create one, so a one-step entry emits `ok:true` on every
#   line and leaves the stage still. The effect is not machine-readable — a
#   stored cue holding a phaser is indistinguishable from an empty cue — so
#   nothing downstream can detect the violation at runtime. This bound and the
#   loader check enforcing it are the only net.
MIN_STEPS = 2

# Phase is a walk around the circle; the reverse literal is `Thru -360`
# (31_choreography_patterns.md:80).
PHASE_MIN = -360.0
PHASE_MAX = 360.0

# Percent axes. The M0 anchor itself is `At 100` / `At 0`, so the bound must
# include both endpoints.
PERCENT_MIN = 0.0
PERCENT_MAX = 100.0

# Pan/Tilt authoring envelope. The repository carries no measured unit or
# fixture limit for a bare `Attribute 'Pan' At <n>`, so this is deliberately
# wide enough to hold either a percent or a degree reading while still catching
# a mis-keyed 2000. Inventing a tighter "console maximum" would be a fabricated
# constant (spec.md's own citation discipline).
SWING_MIN = -360.0
SWING_MAX = 360.0

ATTRIBUTE_VALUE_RANGE: Mapping[str, tuple[float, float]] = {
    "Dimmer": (PERCENT_MIN, PERCENT_MAX),
    "ColorRGB_R": (PERCENT_MIN, PERCENT_MAX),
    "ColorRGB_G": (PERCENT_MIN, PERCENT_MAX),
    "ColorRGB_B": (PERCENT_MIN, PERCENT_MAX),
    "Pan": (SWING_MIN, SWING_MAX),
    "Tilt": (SWING_MIN, SWING_MAX),
}

# The axes that MODIFY an already-created phaser. Declaring any of them without
# a step axis is the exact shape M0 fired three times for zero motion.
# `speed_master`/`width`/`measure` entered on the 2026-08-15 live session
# (SPEC-COPILOT-FXGEN-001 spec.md §A, V3/V4): each was fired from
# the command line and its effect confirmed on stage by GUI observation.
PHASER_MODIFIER_AXES: tuple[str, ...] = (
    "phase_from",
    "phase_to",
    "speed",
    "speed_master",
    "width",
    "measure",
    "relative",
    "reverse",
)

# `Set Selection MAtricks '<axis>' <value>` (31_choreography_patterns.md:85-89).
MATRICKS_AXES: tuple[str, ...] = (
    "phase_from_x",
    "phase_to_x",
    "x",
    "x_wings",
    "x_shuffle",
)

# Curve axes — MEASURED on the 2026-08-15 live session (V1): two dimmer steps
# plus `Step <k> At Accel -100` / `At Decel -100` per step rendered a smooth
# sinusoidal fade on stage (M0 had recorded ok:true with no observed effect;
# the missing piece was firing the curve lines AFTER both steps existed).
CURVE_AXES: tuple[str, ...] = ("accel", "decel")

# The measured curve literal is -100 (the sine shape); the console GUI spans
# the same axis symmetrically, so the authoring bound is the full percent span.
CURVE_MIN = -100.0
CURVE_MAX = 100.0

# 16 speed masters exist, each 0-225 BPM (help.malighting.com, Speed Masters).
# The axis here is the MASTER NUMBER a phaser binds to, not the BPM.
SPEED_MASTER_MIN = 1
SPEED_MASTER_MAX = 16

# Width is a percent of one beat (measured literal: 25). Zero would erase the
# step; the M0 anchor's own `At 100` shape makes 100 the inclusive top.
WIDTH_MIN = 0.0
WIDTH_MAX = 100.0

# Measure scales the whole loop to N beats (measured literal: 4). Only the
# lower bound is principled — zero or negative beats is not a duration; no
# measured upper limit exists, so none is invented.
MEASURE_MIN = 0.0


@dataclass(frozen=True)
class StepValue:
    """One attribute value inside one step, e.g. ``At 100``.

    Emitted as ``At <n>`` by default, or ``At Relative <n>`` when the owning
    fx sets ``relative`` — measured 2026-08-15 (V2): relative step values
    sweep around the fixture's CURRENT position instead of an absolute aim.
    """

    attribute: str
    value: float


@dataclass(frozen=True)
class FxStep:
    """One step of a phaser.

    Index ``i`` maps to console step ``i + 1``: the first element is the current
    step (no ``Step 1`` line is emitted), and every element after it is preceded
    by a standalone ``Step <i+1>`` line. ``Attribute '<attr>' At Step <k>`` is a
    FORBIDDEN form — accepted with `ok:true`, no effect (REQ-FXLIB-022).
    """

    values: tuple[StepValue, ...]

    @property
    def attributes(self) -> tuple[str, ...]:
        """The attributes this step sets, in authored order."""
        return tuple(v.attribute for v in self.values)

    def value_of(self, attribute: str) -> float:
        for entry in self.values:
            if entry.attribute == attribute:
                return entry.value
        raise KeyError(attribute)


@dataclass(frozen=True)
class Fx:
    """One effect pattern. Carries no rig binding — see the module @MX:NOTE."""

    fx_id: str
    display_name: str
    pattern: str
    steps: tuple[FxStep, ...]
    aliases: tuple[str, ...] = ()
    mood_keywords: tuple[str, ...] = ()
    # Phaser modifier axes — emitted AFTER the step run, never instead of it.
    phase_from: float | None = None
    phase_to: float | None = None
    speed: float | None = None
    # Speed source is EITHER a fixed BPM (`speed`) or a live master binding
    # (`speed_master`, V3) — never both; the combination is unmeasured.
    speed_master: int | None = None
    width: float | None = None
    measure: float | None = None
    # True => every step value line is emitted `At Relative <n>` (V2).
    relative: bool = False
    reverse: bool = False
    # MAtricks division axes.
    phase_from_x: float | None = None
    phase_to_x: float | None = None
    x: int | None = None
    x_wings: int | None = None
    x_shuffle: int | None = None
    # Curve axes — measured 2026-08-15 (V1): -100/-100 renders a sine fade.
    accel: float | None = None
    decel: float | None = None

    @property
    def attributes(self) -> tuple[str, ...]:
        """The target attributes, in the order step 1 authored them.

        Derived rather than stored: the loader guarantees every step carries the
        same attribute set, so a second copy of that set could only ever drift
        out of sync with the steps it claims to describe.
        """
        return self.steps[0].attributes if self.steps else ()


@dataclass(frozen=True)
class FxLibrary:
    """The loaded, validated set of fx patterns."""

    schema_version: int
    fx: tuple[Fx, ...] = field(default_factory=tuple)

    def by_id(self, fx_id: str) -> Fx:
        for entry in self.fx:
            if entry.fx_id == fx_id:
                return entry
        raise KeyError(fx_id)


def step_to_dict(step: FxStep) -> dict:
    """Serialise one step back to its wire form (an attribute -> value mapping)."""
    return {v.attribute: v.value for v in step.values}


def fx_to_dict(fx: Fx) -> dict:
    """Serialise an fx back to its wire form; ``load`` of this is the same fx."""
    data: dict = {
        "fx_id": fx.fx_id,
        "display_name": fx.display_name,
        "pattern": fx.pattern,
        "aliases": list(fx.aliases),
        "mood_keywords": list(fx.mood_keywords),
        "steps": [step_to_dict(step) for step in fx.steps],
    }
    for axis in PHASER_MODIFIER_AXES + MATRICKS_AXES + CURVE_AXES:
        value = getattr(fx, axis)
        if value is None or value is False:
            continue
        data[axis] = value
    return data
