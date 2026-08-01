"""Turn one fx into a console command bundle (REQ-FXLIB-009..013, REQ-FXLIB-022).

This module BUILDS text and never sends any. The returned bundle is handed to
the existing ``run_commands`` tool, which screens it through the one gate path;
there is no execution surface here and no import of one (REQ-FXLIB-017).

# @MX:WARN: [AUTO] every line this module emits is unverifiable after the fact.
# @MX:REASON: M0 measured that the effect is NOT machine-readable — a stored cue
#   holding a phaser bottoms out at `Cue -> Part(childCount 0)`, exactly like an
#   empty one; `Phase`/`Speed` read back as "property not readable"; fixture
#   values are unreadable; MA3 keeps no separate effect pool (progress.md §E.2).
#   A malformed bundle therefore returns `ok:true` on every line and leaves the
#   stage still. The two guards below and the tests are the whole net.

The bundle shape (design.md §4, anchored on the M0 [실측] measurement):

    ChangeDestination Root
    ClearAll
    Group <n>                             # bare number form only
    <step 1 value lines>                  # no `Step 1` line — step 1 is current
    Step 2
    <step 2 value lines>                  # the phaser exists from here on
    <phase lines>                         # modifiers ride on an EXISTING phaser
    <speed line>
    [Set Selection MAtricks '<axis>' <v>]
    Store Sequence <n> Cue 1 '<label>'
    [Reset Selection MAtricks]            # after the Store: it shapes what is stored
    ClearAll
    [Assign Sequence <n> At Executor <m>] # only when explicitly asked for

Two design choices this module makes that the SPEC left open are documented at
``_phase_lines`` (how a multi-attribute pattern spends its phase axis) and at
``_ASSIGN_IS_LAST`` (where an explicit executor binding sits).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.fx.schema import GATED_CURVE_AXES, MIN_STEPS, Fx

__all__ = [
    "CIRCLE_PHASE_CONFLICT",
    "CROSS_CALL_COLLISION",
    "GATED_AXIS_NOT_EMITTED",
    "RELATIVE_NOT_EMITTED",
    "SEQUENCE_NUMBER_UNAVAILABLE",
    "SEQUENCE_OCCUPIED",
    "SEQUENCE_TRUNCATED",
    "SEQUENCE_UNAVAILABLE",
    "SKIPPED_ALREADY_EXECUTED",
    "STEP_AXIS_TOO_SHORT",
    "VALUE_LINE_COLLISION",
    "FxInstantiation",
    "FxInstantiationError",
    "build_fx_bundle",
    "collided_lines",
    "instantiate_fx",
    "is_programmer_state",
    "select_sequence_number",
]

# Why a bundle could not be built, or why an execution cannot be called a
# success. Kept apart rather than summed: each names a different fact and a
# different repair.
VALUE_LINE_COLLISION = "value_line_collision"  # two identical non-exempt lines in ONE bundle
CROSS_CALL_COLLISION = "cross_call_collision"  # a line already fired earlier in this turn
SEQUENCE_UNAVAILABLE = "sequence_unavailable"  # the pool could not be read at all
SEQUENCE_TRUNCATED = "sequence_truncated"  # the listing was cut, so "free" is unknowable
SEQUENCE_NUMBER_UNAVAILABLE = "sequence_number_unavailable"  # a child carries no number
SEQUENCE_OCCUPIED = "sequence_occupied"  # the requested number is taken
RELATIVE_NOT_EMITTED = "relative_not_emitted"  # `At Relative` is unmeasured as a step value
GATED_AXIS_NOT_EMITTED = "gated_axis_not_emitted"  # `At Accel`/`At Decel` are probe-pending
LABEL_UNQUOTABLE = "label_unquotable"
STEP_AXIS_TOO_SHORT = "step_axis_too_short"  # fewer than two steps: no phaser is created
CIRCLE_PHASE_CONFLICT = "circle_phase_conflict"  # `circle` owns its offset; phase_to would fight it

# `circle` is DEFINED as its two axes a quarter cycle apart — spec.md §A's
# pattern table and 31_choreography_patterns.md:78-79 both spell the output out
# as `Attribute 'Pan' At Phase 0` + `Attribute 'Tilt' At Phase 90`, and name the
# 0/180 relationship as the diagonal instead. The offset therefore belongs to
# the pattern kind, not to a field: the schema carries ONE phase pair for the
# whole entry, so there is nowhere else to put a per-axis relationship.
_QUARTER_CYCLE = 90.0
_FULL_CYCLE = 360.0

# The per-command status `run_commands` reports when the instruction-scoped
# dedupe drops a line (`server/orchestrator/tools.py` run_commands loop).
SKIPPED_ALREADY_EXECUTED = "skipped_already_executed"

_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"
_RESET_MATRICKS = "Reset Selection MAtricks"
_CUE_NUMBER = 1

# The console-side literal for each MAtricks axis (31_choreography_patterns.md:85-89).
_MATRICKS_LITERALS: tuple[tuple[str, str], ...] = (
    ("phase_from_x", "PhaseFromX"),
    ("phase_to_x", "PhaseToX"),
    ("x", "X"),
    ("x_wings", "XWings"),
    ("x_shuffle", "XShuffle"),
)

# An explicit executor binding is the LAST line of the bundle. It is not part of
# the capture cycle — by the time it runs the programmer has already been
# cleared — so putting it inside the cycle would break the M0-anchored shape for
# no gain. REQ-FXLIB-013 says "번들 말미"; this is that, literally.
_ASSIGN_IS_LAST = True

# @MX:ANCHOR: [AUTO] this exemption set MUST stay equal to
#   `server/orchestrator/tools.py` `_PROGRAMMER_STATE_COMMANDS`.
# @MX:REASON: the guard below decides which of ITS OWN lines the dedupe will
#   compare. If this set is wider than the tool's, the guard waves through a
#   line the dedupe then drops — and the drop is silent, because `Store` still
#   runs and the console still answers ok. The equality is asserted by
#   `server/tests/test_fx_boundary.py` (M6), which may import both sides; this
#   module may NOT import the tool layer, because `tools.py` imports fx at
#   registration time and a top-level fx->tools import would be circular. The
#   mirror precedent is `server/looks/busking.py` `_guard_collision`: the
#   builder classifies the lines it generated itself.
_SELECTION_OPERAND = r"\d+(?:\s*[-+]\s*\d+|\s+Thru(?:\s+\d+)?)*"
_PROGRAMMER_STATE_COMMANDS = (
    re.compile(r"Clear", re.IGNORECASE),
    re.compile(r"ClearAll", re.IGNORECASE),
    re.compile(rf"(?:Fixture|Group)\s+{_SELECTION_OPERAND}", re.IGNORECASE),
)


class FxInstantiationError(ValueError):
    """An fx cannot be turned into a bundle that is safe to fire.

    Carries a ``reason`` code so a caller can branch on the fact rather than on
    the message text.
    """

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


def is_programmer_state(command: str) -> bool:
    """True for a line the run_commands dedupe exempts (see the @MX:ANCHOR above)."""
    text = command.strip()
    return any(pattern.fullmatch(text) is not None for pattern in _PROGRAMMER_STATE_COMMANDS)


@dataclass(frozen=True)
class FxInstantiation:
    """One fx bound to one rig: the bundle plus what it claims to create."""

    fx_id: str
    display_name: str
    pattern: str
    group: int
    sequence: int
    label: str
    commands: tuple[str, ...] = ()
    cue: int = _CUE_NUMBER
    executor: int | None = None
    attributes: tuple[str, ...] = ()
    step_count: int = 0
    speed_bpm: float | None = None
    matricks: tuple[tuple[str, float], ...] = ()

    @property
    def non_exempt_commands(self) -> tuple[str, ...]:
        """The lines the instruction-scoped dedupe will compare."""
        return tuple(c for c in self.commands if not is_programmer_state(c))

    def to_dict(self) -> dict:
        return {
            "fx_id": self.fx_id,
            "display_name": self.display_name,
            "pattern": self.pattern,
            "group": self.group,
            "sequence": self.sequence,
            "cue": self.cue,
            "label": self.label,
            "executor": self.executor,
            "attributes": list(self.attributes),
            "step_count": self.step_count,
            "speed_bpm": self.speed_bpm,
            "matricks": [{"axis": axis, "value": value} for axis, value in self.matricks],
            "commands": list(self.commands),
        }


# -- sequence number -----------------------------------------------------------


def _sequence_numbers(sequences_section: Mapping[str, object]) -> set[int]:
    listed = sequences_section.get("objects")
    if not isinstance(listed, list):
        raise FxInstantiationError(
            SEQUENCE_UNAVAILABLE,
            "the sequence pool could not be read, so no free number can be measured; "
            "inventing one is forbidden (REQ-FXLIB-012)",
        )
    occupied: set[int] = set()
    for entry in listed:
        number = entry.get("no") if isinstance(entry, Mapping) else None
        if not isinstance(number, int):
            # The responder lists a sequence it could not number. Some number in
            # this pool is taken and we cannot say which, so no number in it can
            # be claimed free (the same split `resolve_pools` makes for slots).
            raise FxInstantiationError(
                SEQUENCE_NUMBER_UNAVAILABLE,
                "a sequence in the pool carries no number, so no number in the pool "
                "can be claimed free",
            )
        occupied.add(number)
    return occupied


def select_sequence_number(
    sequences_section: Mapping[str, object], *, requested: int | None = None
) -> int:
    """Measure a free sequence number from a re-queried pool (REQ-FXLIB-012 (c)).

    Never invents one. A truncated listing refuses outright: "free" is not a
    property of the numbers that happened to arrive, and the console's own
    refusal of an un-flagged Store onto an occupied sequence is the LAST line of
    defence, not the first.
    """
    unavailable = sequences_section.get("reason")
    if isinstance(unavailable, str) or sequences_section.get("ok") is False:
        raise FxInstantiationError(
            SEQUENCE_UNAVAILABLE,
            "the sequence pool could not be read "
            f"({unavailable or 'the section reported not-ok'}), so no free number "
            "can be measured",
        )
    if sequences_section.get("truncated"):
        raise FxInstantiationError(
            SEQUENCE_TRUNCATED,
            "the sequence pool listing was truncated, so an unlisted sequence may "
            "hold any candidate number; automatic assignment is refused",
        )
    occupied = _sequence_numbers(sequences_section)
    if requested is not None:
        if requested in occupied:
            raise FxInstantiationError(
                SEQUENCE_OCCUPIED,
                f"sequence {requested} is already occupied; v1 never stores onto an "
                "existing sequence (no /Overwrite, no un-flagged Store)",
            )
        return requested
    candidate = 1
    while candidate in occupied:
        candidate += 1
    return candidate


# -- bundle construction -------------------------------------------------------


def _format_value(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _label_of(fx: Fx, label: str | None) -> str:
    text = fx.display_name if label is None else label
    if not text.strip():
        raise FxInstantiationError(
            LABEL_UNQUOTABLE, f"fx {fx.fx_id!r} has an empty label to store under"
        )
    if "'" in text or "\n" in text:
        raise FxInstantiationError(
            LABEL_UNQUOTABLE,
            f"fx {fx.fx_id!r} has a label that cannot be quoted on the MA3 command line: {text!r}",
        )
    return text


def _refuse_unemitted_axes(fx: Fx) -> None:
    """Refuse an entry whose declared axis this version does not emit.

    Dropping it silently is the failure this whole SPEC exists to prevent: the
    entry would look configured, the bundle would fire clean, and the difference
    would only ever show on stage.
    """
    if len(fx.steps) < MIN_STEPS:
        # The loader already refuses this, but the loader is not the only door:
        # an `Fx` constructed directly reaches here having never met it. Without
        # this check a one-step entry builds the exact bundle M0 fired three
        # times — every line ok:true, no `Step` line, no phaser, a stored cue
        # that reads identically to an empty one (REQ-FXLIB-009).
        raise FxInstantiationError(
            STEP_AXIS_TOO_SHORT,
            f"fx {fx.fx_id!r} carries {len(fx.steps)} step(s); a phaser needs at "
            f"least {MIN_STEPS}, because `Phase`/`Speed`/`Relative` modify an "
            "existing phaser and cannot create one",
        )
    if fx.pattern == "circle" and fx.phase_to is not None:
        # Two mechanisms for one output. Picking either one silently would make
        # the entry read as configured while emitting the other one's shape.
        raise FxInstantiationError(
            CIRCLE_PHASE_CONFLICT,
            f"fx {fx.fx_id!r} is a circle and also declares phase_to="
            f"{_format_value(fx.phase_to)}; a circle's axes are a quarter cycle "
            "apart by definition, measured from phase_from, so phase_to has "
            "nothing left to describe",
        )
    if fx.relative is not None:
        raise FxInstantiationError(
            RELATIVE_NOT_EMITTED,
            f"fx {fx.fx_id!r} declares relative={_format_value(fx.relative)}, but v1 "
            "never emits `At Relative`: whether it holds as a step value is "
            "unmeasured (ASSUMPTION-40), and amplitude is carried by the difference "
            "between step values instead",
        )
    for axis in GATED_CURVE_AXES:
        value = getattr(fx, axis)
        if value is not None:
            raise FxInstantiationError(
                GATED_AXIS_NOT_EMITTED,
                f"fx {fx.fx_id!r} declares {axis}={_format_value(value)}, but the "
                f"{axis} curve is probe-pending: M0 recorded ok:true with no observed "
                "effect (SKIP), so v1 defines the field and never emits it",
            )


def _step_lines(fx: Fx) -> list[str]:
    """The step run: index ``i`` is console step ``i + 1``.

    ``Step 1`` is never emitted — the first step is the current one — and each
    later step is opened by a STANDALONE ``Step <k>`` line placed before its own
    value lines. ``Attribute '<attr>' At Step <k>`` is a forbidden form: the
    console accepts it with ok:true and nothing happens (REQ-FXLIB-022).
    """
    lines: list[str] = []
    for index, step in enumerate(fx.steps):
        if index:
            lines.append(f"Step {index + 1}")
        lines.extend(
            f"Attribute '{value.attribute}' At {_format_value(value.value)}"
            for value in step.values
        )
    return lines


def _phase_lines(fx: Fx) -> list[str]:
    """The phase modifier lines, one per target attribute.

    How the single ``phase_from``/``phase_to`` pair is spent depends on the
    pattern, because the rulebook's validated shapes differ on exactly that:

    * ``circle`` -> the two axes a QUARTER CYCLE apart, measured from
      ``phase_from``: ``Attribute 'Pan' At Phase 0`` + ``Attribute 'Tilt' At
      Phase 90`` (:78-79). This one is dictated by spec.md §A's pattern table,
      and the offset lives in the pattern kind because the schema has one phase
      pair for the whole entry and nowhere to put a per-axis relationship.
      Without it ``circle`` and ``diagonal`` emit identical lines and the closed
      vocabulary quietly loses a pattern.
    * ONE attribute + ``phase_to`` -> a spread across the SELECTION:
      ``Attribute 'Pan' At Phase 0 Thru 360`` (:69) — the fan that turns a
      blinking phaser into a travelling wave, and the M0 anchor's own shape.
    * MORE THAN ONE attribute + ``phase_to`` -> a fixed phase PER ATTRIBUTE,
      walked from ``phase_from`` to ``phase_to`` with both endpoints included.
    * no ``phase_to`` -> every attribute sits at ``phase_from``. This is the
      ``diagonal`` shape: both axes travel together and the in-phase/anti-phase
      distinction is carried by the STEP VALUES, not by this axis.

    Only the multi-attribute-with-``phase_to`` rule is a choice the SPEC left
    open; the other three are its stated outputs. Its cost: a multi-attribute
    pattern cannot ALSO fan across the selection from this axis — the MAtricks
    ``PhaseFromX``/``PhaseToX`` axes are where that lives.
    """
    if fx.phase_from is None and fx.phase_to is None:
        return []
    attributes = fx.attributes
    start = 0.0 if fx.phase_from is None else float(fx.phase_from)
    end = None if fx.phase_to is None else float(fx.phase_to)
    if fx.pattern == "circle":
        step = -_QUARTER_CYCLE if fx.reverse else _QUARTER_CYCLE
        return [
            f"Attribute '{name}' At Phase {_format_value(start + step * index)}"
            for index, name in enumerate(attributes)
        ]
    if end is not None and fx.reverse:
        # Reverse the walk direction: `At Phase 0 Thru -360` (:80). Only the
        # far end changes; every other line of the bundle is untouched.
        end = -end
    if end is None:
        return [f"Attribute '{name}' At Phase {_format_value(start)}" for name in attributes]
    if len(attributes) == 1:
        return [
            f"Attribute '{attributes[0]}' At Phase {_format_value(start)} Thru {_format_value(end)}"
        ]
    # Endpoint inclusion depends on whether the arc closes on itself. Phase is
    # cyclic, so a span of a whole cycle puts the far endpoint on the SAME phase
    # as the near one: walking 0->360 across three attributes inclusively yields
    # 0 / 180 / 360, and 360 == 0, so the first and last attribute run in phase
    # and a three-colour chase renders as a two-phase flip. Dividing by the
    # attribute COUNT instead spaces them 0 / 120 / 240 — evenly around the
    # cycle, which is what spending the axis across N attributes means.
    # A partial arc (0->180) does not close, so its far endpoint is meaningful
    # and stays included: 0 / 90 / 180.
    span = end - start
    closes_on_itself = span != 0 and span % _FULL_CYCLE == 0
    divisor = len(attributes) if closes_on_itself else len(attributes) - 1
    return [
        f"Attribute '{name}' At Phase {_format_value(start + span * index / divisor)}"
        for index, name in enumerate(attributes)
    ]


def _speed_line(fx: Fx) -> list[str]:
    if fx.speed is None:
        return []
    # `;` chaining is a validated literal (:39) and design.md §4.3 keeps it on
    # the Speed line only — its combination with the step context is unmeasured,
    # so step value lines stay one per line.
    return [
        " ; ".join(
            f"Attribute '{name}' At Speed {_format_value(fx.speed)}" for name in fx.attributes
        )
    ]


def _matricks(fx: Fx) -> tuple[tuple[str, float], ...]:
    return tuple(
        (literal, getattr(fx, axis))
        for axis, literal in _MATRICKS_LITERALS
        if getattr(fx, axis) is not None
    )


def _guard_collision(fx: Fx, commands: Sequence[str]) -> None:
    """Refuse a bundle carrying the same non-exempt line twice (REQ-FXLIB-011 (a)).

    The mirror precedent is `server/looks/busking.py` ``_guard_collision`` and
    its ``VALUE_LINE_COLLISION`` reason — the same class of fact: this store
    cannot happen safely. It refuses rather than skips because an fx bundle is
    ONE store; there is no surviving remainder to report.

    This guard sees only THIS bundle. A line fired by an earlier call in the
    same instruction turn is invisible here by construction — that boundary is
    `collided_lines` below.
    """
    seen: set[str] = set()
    for command in commands:
        if is_programmer_state(command):
            continue
        if command in seen:
            raise FxInstantiationError(
                VALUE_LINE_COLLISION,
                f"fx {fx.fx_id!r} would emit the line {command!r} twice; the second "
                "one is dropped by the run_commands dedupe and the Store then runs "
                "against a programmer that is missing a step — silently, because a "
                "stored phaser cue is indistinguishable from an empty one",
            )
        seen.add(command)


def build_fx_bundle(
    fx: Fx,
    *,
    group: int,
    sequence: int,
    executor: int | None = None,
    label: str | None = None,
) -> FxInstantiation:
    """Build the command bundle for one fx against one already-chosen binding.

    ``group`` and ``sequence`` are numbers the CALLER measured from the rig —
    this function never derives, guesses or renumbers them.
    """
    _refuse_unemitted_axes(fx)
    text = _label_of(fx, label)
    matricks = _matricks(fx)

    commands: list[str] = [_DESTINATION, _CLEAR, f"Group {group}"]
    commands.extend(_step_lines(fx))
    commands.extend(_phase_lines(fx))
    commands.extend(_speed_line(fx))
    commands.extend(f"Set Selection MAtricks '{axis}' {_format_value(v)}" for axis, v in matricks)
    commands.append(f"Store Sequence {sequence} Cue {_CUE_NUMBER} '{text}'")
    if matricks:
        # After the Store: the sub-selection is part of the shape being stored,
        # so releasing it earlier would store the undivided effect (:90).
        commands.append(_RESET_MATRICKS)
    commands.append(_CLEAR)
    if executor is not None:
        commands.append(f"Assign Sequence {sequence} At Executor {executor}")

    _guard_collision(fx, commands)
    return FxInstantiation(
        fx_id=fx.fx_id,
        display_name=fx.display_name,
        pattern=fx.pattern,
        group=group,
        sequence=sequence,
        label=text,
        commands=tuple(commands),
        executor=executor,
        attributes=fx.attributes,
        step_count=len(fx.steps),
        speed_bpm=fx.speed,
        matricks=matricks,
    )


def instantiate_fx(
    fx: Fx,
    *,
    group: int,
    sequences_section: Mapping[str, object],
    sequence: int | None = None,
    executor: int | None = None,
    label: str | None = None,
) -> FxInstantiation:
    """Measure the sequence number from a re-queried pool, then build."""
    return build_fx_bundle(
        fx,
        group=group,
        sequence=select_sequence_number(sequences_section, requested=sequence),
        executor=executor,
        label=label,
    )


# -- the instruction-turn boundary ---------------------------------------------


def _outcome_field(outcome: object, name: str) -> str:
    # Duck-typed on purpose: `run_commands` hands back `CommandOutcome` objects,
    # while its JSON content carries the same two fields as a mapping. Reading
    # both shapes costs one line and removes a reason to import the tool layer.
    value = outcome.get(name, "") if isinstance(outcome, Mapping) else getattr(outcome, name, "")
    return value if isinstance(value, str) else ""


def collided_lines(outcomes: Sequence[object] | None) -> tuple[str, ...]:
    """The non-exempt lines this run did NOT fire because they already had.

    The dedupe's real boundary is the whole instruction turn, not the bundle:
    ``executed_ok`` accumulates across tool calls, so a second instantiation in
    one turn folds from ``Step 2`` onward — that line is common to every pattern
    and is not in the exempt set, so even two UNRELATED patterns collide.

    Nothing here can be seen at construction time, which is why the detection
    lives on the execution result: that is the only surface this package can be
    sure of. A non-empty return forbids reporting the instantiation as a
    success (REQ-FXLIB-011 (b)) — the Store carries a unique string of its own,
    so it runs, and an incomplete sequence may already exist.
    """
    return tuple(
        command
        for outcome in (outcomes or ())
        if _outcome_field(outcome, "status") == SKIPPED_ALREADY_EXECUTED
        and (command := _outcome_field(outcome, "command"))
        and not is_programmer_state(command)
    )
