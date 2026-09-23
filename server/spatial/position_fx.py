"""SPATIAL position FX — sequences that CONSUME the stored FX position presets.

``fx_position_presets`` (server/spatial/pointing.py) stores ten skeleton
positions (``FX_POSITION_SEQUENCE``) as ``Preset 2.<start>..2.<start+9>``.
This module turns a named effect plus that stored bank into ONE sequence-
building command bundle, in two validated shapes:

* **A/B effects** (``sweep``, ``flyout``) — a two-cue sequence: Cue 1 recalls
  preset A, Cue 2 recalls preset B. Crossfading the cues carries every beam
  A -> B and back. Grammar: the sequence auto-creates on the first ``Store``;
  the second cue rides ``/Merge`` (31_choreography_patterns.md:50-55, live
  validated on onPC 2.4.2). Because each cue stores a preset RECALL, the cue
  holds a REFERENCE (31_choreography_patterns.md V7) — regenerating the
  presets at a new venue re-aims the sequence for free.

* **Base effects** (``circle``, ``ballyhoo``, ``wave``) — one cue: recall the
  base preset, then build a RELATIVE phaser on top of it. ``At Relative``
  rides on the fixtures' current aim and KEEPS that center-follow semantics
  under preset recall (31_choreography_patterns.md V2 + operator
  confirmations), so the same cue orbits/waves around wherever the base
  preset points today.

Every command line below is either the rulebook's validated grammar
(31_choreography_patterns.md — the only first-hand source) or an existing
emitter reused verbatim (``preset_recall_command``). No forum-sourced
syntax; no ``/Overwrite`` ever.

Pure module: imports ``server.spatial.pointing`` only — zero transport,
zero gate. Callers hand the bundle to the existing gated ``run_commands``
path unchanged.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from server.spatial.pointing import (
    FX_POSITION_SEQUENCE,
    SpatialPointingError,
    preset_recall_command,
)

__all__ = [
    "POSITION_FX_EFFECTS",
    "position_fx_commands",
    "required_position_labels",
]

#: The closed effect vocabulary — like FAN_MODES/RADIAL_MODES in pointing.
POSITION_FX_EFFECTS: tuple[str, ...] = ("sweep", "flyout", "circle", "ballyhoo", "wave")

#: Verified programming preamble (31_choreography_patterns.md:9-23,40-41):
#: `Root` is the programming context, and a fresh look starts from a clean
#: programmer or leftovers TRACK into the capture.
_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"

#: A/B effects: (offset of preset A, offset of preset B) as INDICES into
#: FX_POSITION_SEQUENCE. sweep pans the whole rig Sweep L <-> Sweep R;
#: flyout dives Sky Out (house air) <-> Aisle Punch (deep floor hit).
_AB_PRESET_OFFSETS: dict[str, tuple[int, int]] = {
    "sweep": (0, 1),  # 'Sweep L', 'Sweep R'
    "flyout": (2, 9),  # 'Sky Out', 'Aisle Punch'
}

#: Base effects: the single skeleton preset the relative phaser rides on,
#: again an INDEX into FX_POSITION_SEQUENCE.
_BASE_PRESET_OFFSETS: dict[str, int] = {
    "circle": 4,  # 'Circle Base'
    "ballyhoo": 5,  # 'Bally Base'
    "wave": 3,  # 'Floor Base'
}

#: A/B cues crossfade over the CueFade — 2 s is the rulebook's own worked
#: value (31_choreography_patterns.md:50,55), slow enough that the position
#: change reads as a sweep instead of a snap.
_AB_CUE_FADE_SECONDS = 2

#: Relative phaser magnitudes. The repository carries no measured unit for a
#: bare position value (movement.yaml header), so these reuse the SAME
#: magnitudes the fx library already ships — deliberately small, riding on a
#: base preset that may sit near a limit:
#:   circle  — circle-relative-orbit: Pan ±12 / Tilt ±8 (movement.yaml:194-206)
#:   wave    — wave-soft-rise: Tilt ±12 (movement.yaml:76-86)
#:   ballyhoo— circle-soft-ballyhoo: Pan ±20 / Tilt ±10 (movement.yaml:112-123)
_CIRCLE_RELATIVE_PAN = 12
_CIRCLE_RELATIVE_TILT = 8
_WAVE_RELATIVE_TILT = 12
_BALLY_RELATIVE_PAN = 20
_BALLY_RELATIVE_TILT = 10

#: A ballyhoo is FAST by definition — the rulebook mood table puts energetic
#: movement at Speed 90-180 BPM (31_choreography_patterns.md:236-241) while
#: the module's 60 BPM default sits below that band. Doubling lands the
#: default at 120, mid-band, matching the library's own club entries
#: (sweep-club-xwave 120, circle-club-wings 112 — movement.yaml).
_BALLYHOO_SPEED_FACTOR = 2

#: Circle geometry is the two axes a QUARTER CYCLE apart; 0/180 would be a
#: diagonal line instead (31_choreography_patterns.md:78-79).
_CIRCLE_PAN_PHASE = 0
_CIRCLE_TILT_PHASE = 90

#: One full wave fanned across the selection (rulebook phaser example,
#: 31_choreography_patterns.md:66-73).
_PHASE_SPREAD = "Phase 0 Thru 360"


def _format_speed(speed_bpm: float) -> str:
    """BPM as command text without trailing ``.0`` noise."""
    if float(speed_bpm).is_integer():
        return str(int(speed_bpm))
    return f"{speed_bpm:g}"


def _validated_label(label: str) -> str:
    """The sequence label, or a refusal — same rule as pointing's labels.

    Single quotes delimit MA3 names and double quotes cannot be sent at all
    (``server/bridge/protocol.py`` rejects them), so a label carrying either
    is refused, never mangled — the exact rule ``position_preset_store_commands``
    applies to preset labels.
    """
    text = label.strip()
    if not text or "'" in text or '"' in text:
        raise SpatialPointingError(f"sequence label {label!r} is empty or carries a quote")
    return text


def _cue_store(sequence_no: int, cue_no: int, name: str, *, merge: bool) -> str:
    """Validated store grammar: ``Store Sequence <S> Cue <n> '<name>' CueFade 2``.

    The sequence auto-creates on the first store; every LATER cue must ride
    ``/Merge`` or the store prompts (31_choreography_patterns.md:54-55).
    ``/Overwrite`` never appears — it is the destructive flag the safety gate
    routes to human approval.
    """
    command = f"Store Sequence {sequence_no} Cue {cue_no} '{name}' CueFade {_AB_CUE_FADE_SECONDS}"
    if merge:
        command += " /Merge"
    return command


def _relative_phaser_lines(effect: str, speed_bpm: float) -> tuple[str, ...]:
    """The relative-phaser body for one base effect, rulebook shape exactly.

    Each axis that moves gets three validated lines — ``At Relative`` (the
    swing, one step riding the base aim), ``At Phase ...`` (the shape), and
    ``At Speed <bpm>`` (the rate) — mirroring the live-validated build at
    31_choreography_patterns.md:66-73. Only the moving axes are touched.
    """
    speed = _format_speed(speed_bpm)
    if effect == "circle":
        return (
            f"Attribute 'Pan' At Relative {_CIRCLE_RELATIVE_PAN}",
            f"Attribute 'Tilt' At Relative {_CIRCLE_RELATIVE_TILT}",
            f"Attribute 'Pan' At Phase {_CIRCLE_PAN_PHASE}",
            f"Attribute 'Tilt' At Phase {_CIRCLE_TILT_PHASE}",
            f"Attribute 'Pan' At Speed {speed}",
            f"Attribute 'Tilt' At Speed {speed}",
        )
    if effect == "wave":
        return (
            f"Attribute 'Tilt' At Relative {_WAVE_RELATIVE_TILT}",
            f"Attribute 'Tilt' At {_PHASE_SPREAD}",
            f"Attribute 'Tilt' At Speed {speed}",
        )
    # ballyhoo — both axes swing, phase fanned per axis, fast by definition.
    bally_speed = _format_speed(speed_bpm * _BALLYHOO_SPEED_FACTOR)
    return (
        f"Attribute 'Pan' At Relative {_BALLY_RELATIVE_PAN}",
        f"Attribute 'Tilt' At Relative {_BALLY_RELATIVE_TILT}",
        f"Attribute 'Pan' At {_PHASE_SPREAD}",
        f"Attribute 'Tilt' At {_PHASE_SPREAD}",
        f"Attribute 'Pan' At Speed {bally_speed}",
        f"Attribute 'Tilt' At Speed {bally_speed}",
    )


def required_position_labels(effect: str) -> tuple[str, ...]:
    """The ``FX_POSITION_SEQUENCE`` labels ``effect`` recalls — STORE order.

    One label for a base effect (``circle``/``ballyhoo``/``wave``), two for
    an A/B effect (``sweep``/``flyout``). Callers resolve each label to an
    ACTUAL console preset slot (t232 — by label, never ``start + index``)
    before calling :func:`position_fx_commands`.
    """
    if effect not in POSITION_FX_EFFECTS:
        raise SpatialPointingError(
            f"unknown position fx effect {effect!r}; expected one of {POSITION_FX_EFFECTS}"
        )
    if effect in _AB_PRESET_OFFSETS:
        offset_a, offset_b = _AB_PRESET_OFFSETS[effect]
        return (FX_POSITION_SEQUENCE[offset_a], FX_POSITION_SEQUENCE[offset_b])
    offset = _BASE_PRESET_OFFSETS[effect]
    return (FX_POSITION_SEQUENCE[offset],)


def position_fx_commands(
    effect: str,
    *,
    fids: Sequence[int],
    preset_numbers: Mapping[str, int],
    sequence_no: int,
    label: str,
    speed_bpm: float = 60.0,
) -> tuple[str, ...]:
    """The command bundle that builds one position-FX sequence.

    ``preset_numbers`` maps each label :func:`required_position_labels`
    returns for ``effect`` to its RESOLVED Position preset slot number — the
    caller looks these up on the console BY LABEL (t232; see
    ``ChatSession._resolve_position_preset_labels``), never by
    ``fx_preset_start + index``, so a pool whose FX bank is not a contiguous
    ``FX_POSITION_SEQUENCE``-ordered run still recalls the right preset.
    ``speed_bpm`` shapes the base effects' phaser rate only; the A/B effects
    move on the cue crossfade instead.
    """
    needed = required_position_labels(effect)
    if not fids:
        raise SpatialPointingError("no fixtures to build the position fx on")
    if sequence_no <= 0:
        raise SpatialPointingError(f"sequence number {sequence_no!r} must be positive")
    if not math.isfinite(speed_bpm) or speed_bpm <= 0:
        raise SpatialPointingError(f"speed {speed_bpm!r} must be a positive finite BPM")
    missing = [name for name in needed if name not in preset_numbers]
    if missing:
        raise SpatialPointingError(
            f"no resolved preset number for {missing!r} — expected one of {needed!r}"
        )
    text = _validated_label(label)

    commands: list[str] = [_DESTINATION, _CLEAR]
    if effect in _AB_PRESET_OFFSETS:
        name_a, name_b = needed
        commands += [
            preset_recall_command(fids, preset_numbers[name_a]),
            _cue_store(sequence_no, 1, name_a, merge=False),
            _CLEAR,
            preset_recall_command(fids, preset_numbers[name_b]),
            _cue_store(sequence_no, 2, name_b, merge=True),
            _CLEAR,
        ]
    else:
        (name,) = needed
        commands += [
            preset_recall_command(fids, preset_numbers[name]),
            *_relative_phaser_lines(effect, speed_bpm),
            f"Store Sequence {sequence_no} Cue 1 '{effect.capitalize()}'",
            _CLEAR,
        ]
    commands.append(f"Label Sequence {sequence_no} '{text}'")
    return tuple(commands)
