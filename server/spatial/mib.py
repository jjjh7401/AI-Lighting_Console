"""MIB (Move In Black) — pre-position a dark rig before the reveal cue.

The industry rule this module encodes (SPEC-COPILOT-CUETIME-001 T2): when a
cue turns the dimmer up onto a NEW position while the previous cue left the
rig dark, the audience must never watch the heads swing into place. The fix
is a PRE-MOVE cue inserted between the two — position only, fired while the
dimmer is still 0 (tracking keeps it there), so the reveal cue fades
intensity onto beams that are already parked.

Cue numbers carry decimals in MA3 (verified insert grammar,
31_choreography_patterns.md:56), so the pre-move cue lives at the midpoint
between the dark cue and the reveal cue.

The rulebook carries no MIB precedent (measured: zero grep hits) — the live
behaviour of this pattern was measured in this SPEC's M2 and is recorded in
`.claude/skills/ma3-spatial-pointing/SKILL.md` §3c.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from server.spatial.pointing import (
    SpatialPointingError,
    position_cue_store_commands,
    preset_recall_command,
)

__all__ = [
    "PositionCuePlan",
    "apply_mib",
    "position_cue_bundle",
    "premove_follow_command",
]

#: The pre-move cue's own fade. The move happens in the dark, so it only has
#: to be comfortably inside the gap before the operator fires the reveal —
#: 1 s moves any head of the measured rig without an audible motor snap.
DEFAULT_MOVE_SECONDS = 1.0


@dataclass(frozen=True)
class PositionCuePlan:
    """One cue of a position cue sheet, BEFORE command rendering.

    ``preset_no`` is the Position preset (``Preset 2.<n>``) this cue recalls
    — cues reference presets, never raw values (32_spatial_design.md).
    ``dimmer=None`` means the cue does not touch intensity (MA3 tracking
    carries the previous value forward); ``0.0`` is an explicit blackout.
    """

    cue_no: float
    name: str
    preset_no: int | None = None
    dimmer: float | None = None
    fade_seconds: float | None = None
    premove: bool = False
    """A MIB dark pre-move — MUST fire automatically (``TrigType Follow``):
    left on Go, the operator's press at the reveal moment plays an invisible
    move instead of the reveal, one press late (measured live, Seq 113)."""


def _validate(cues: Sequence[PositionCuePlan]) -> None:
    if not cues:
        raise SpatialPointingError("no cues to apply MIB to")
    for prev, cur in zip(cues, cues[1:], strict=False):
        if not cur.cue_no > prev.cue_no:
            raise SpatialPointingError(
                f"cue numbers must strictly increase: {prev.cue_no!r} then {cur.cue_no!r}"
            )
    for cue in cues:
        if not math.isfinite(cue.cue_no) or cue.cue_no <= 0:
            raise SpatialPointingError(
                f"cue number {cue.cue_no!r} must be a positive finite number"
            )
        if cue.preset_no is None and cue.dimmer is None:
            raise SpatialPointingError(
                f"cue {cue.cue_no!r} carries neither a position nor a dimmer — "
                "storing it would capture an empty programmer"
            )


def apply_mib(
    cues: Sequence[PositionCuePlan],
    *,
    move_seconds: float = DEFAULT_MOVE_SECONDS,
) -> tuple[PositionCuePlan, ...]:
    """The cue sheet with MIB pre-move cues inserted where the rule fires.

    The rule, per consecutive-state walk: the rig is DARK (last explicit
    dimmer was 0) and the next cue both reveals (dimmer > 0) and moves
    (recalls a preset different from the one the rig is parked on). Then:

    * a pre-move cue appears at the numeric midpoint — position only, fade
      ``move_seconds``; tracking keeps the dimmer at 0 through it, and
    * the reveal cue loses its position (the pre-move already parked the
      heads) and keeps its dimmer fade untouched.

    An unknown starting state is treated as LIT: inserting a phantom
    pre-move on a rig that may be visible would cause exactly the on-stage
    swing MIB exists to remove.
    """
    _validate(cues)
    if not math.isfinite(move_seconds) or move_seconds < 0:
        raise SpatialPointingError(f"move_seconds {move_seconds!r} must be non-negative and finite")
    result: list[PositionCuePlan] = []
    dark = False  # unknown start = lit (see docstring)
    parked_preset: int | None = None
    prev_no: float | None = None
    for cue in cues:
        fires = (
            dark
            and prev_no is not None
            and cue.preset_no is not None
            and cue.preset_no != parked_preset
            and cue.dimmer is not None
            and cue.dimmer > 0
        )
        if fires:
            midpoint = (prev_no + cue.cue_no) / 2
            result.append(
                PositionCuePlan(
                    cue_no=midpoint,
                    name=f"{cue.name} Move",
                    preset_no=cue.preset_no,
                    fade_seconds=move_seconds,
                    premove=True,
                )
            )
            result.append(replace(cue, preset_no=None))
        else:
            result.append(cue)
        if cue.preset_no is not None:
            parked_preset = cue.preset_no
        if cue.dimmer is not None:
            dark = cue.dimmer == 0
        prev_no = cue.cue_no
    return tuple(result)


def position_cue_bundle(
    sequence_no: int,
    plan: PositionCuePlan,
    fids: Sequence[int],
    *,
    extra_value_lines: Sequence[str] = (),
) -> tuple[str, ...]:
    """The store bundle for ONE planned cue — recall/dimmer → store → clear.

    Every value line carries its ``Fixture`` selection prefix so the text
    stays unique under the instruction-scope command dedupe (SKILL §3), and
    the bundle ends with ``ClearAll`` so nothing leaks into the next store.
    Cue names must not carry dots — MA3 strips them (measured, SKILL §3b).
    ``extra_value_lines`` are appended after the plan's own value lines and
    before the store — e.g. a group-addressed back-layer dimmer override.
    """
    if not fids:
        raise SpatialPointingError("no fixtures to build the cue on")
    lines: list[str] = []
    if plan.preset_no is not None:
        lines.append(preset_recall_command(fids, plan.preset_no))
    if plan.dimmer is not None:
        if not 0.0 <= plan.dimmer <= 100.0:
            raise SpatialPointingError(f"dimmer {plan.dimmer!r} is outside 0..100")
        selection = " + ".join(str(fid) for fid in fids)
        lines.append(f"Fixture {selection} ; Attribute 'Dimmer' At {plan.dimmer:g}")
    lines.extend(extra_value_lines)
    if not lines:
        raise SpatialPointingError(f"cue {plan.cue_no!r} carries neither a position nor a dimmer")
    lines.extend(
        position_cue_store_commands(
            sequence_no,
            plan.cue_no,
            fade_seconds=plan.fade_seconds,
            name=plan.name,
        )
    )
    lines.append("ClearAll")
    return tuple(lines)


def premove_follow_command(sequence_no: int, plan: PositionCuePlan) -> str:
    """The trigger line that makes a MIB pre-move fire on its own.

    ``Set Cue <no> Sequence <n> Property 'TrigType' 'Follow'`` — verified
    grammar (31_choreography_patterns.md:111; the ``/trig=`` option form is
    rejected by 2.4.2). Follow fires when the previous cue completes, so the
    heads move in the dark right after the blackout lands and the operator's
    NEXT Go is the reveal — Go count stays one-per-song-section.
    """
    if not plan.premove:
        raise SpatialPointingError(f"cue {plan.cue_no!r} is not a MIB pre-move")
    if sequence_no <= 0:
        raise SpatialPointingError(f"sequence number {sequence_no!r} must be positive")
    return f"Set Cue {plan.cue_no:g} Sequence {sequence_no} Property 'TrigType' 'Follow'"
