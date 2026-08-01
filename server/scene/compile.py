"""Turn one scene (a look reference + an fx reference) into ONE console command
bundle (REQ-SCENE-005/010/011/012/013/015/016/017).

This module BUILDS text and never sends any. The returned bundle is handed to
the existing ``run_commands`` tool, which screens it through the one gate path;
there is no execution surface here and no import of one (REQ-SCENE-019).

The bundle shape is design.md §3's skeleton, anchored on the fx M0 measurement
that a phaser needs an existing step to modify (``server/fx/schema.py:66``
``MIN_STEPS``) and that ``Step 1`` is never emitted (``server/fx/instantiate.py``
``_step_lines``). The look values line fills exactly that current-step slot, so
it MUST sit before the first ``Step 2`` line — reversed, the look becomes the
phaser's last stop and the defect is invisible at runtime (design.md §3.2).

    ChangeDestination Root
    ClearAll
    Group <n>
    <look values line>                    # only when the scene carries a look
    <fx step 1 (current) value lines>      # only when the scene carries an fx
    Step 2
    <fx step 2 value lines>
    [Step 3] [...]
    <phase lines>
    <speed line>
    [Set Selection MAtricks '<axis>' <v>]
    Store Sequence <s> Cue <c> '<label>'   # never carries a flag (design.md §6.0)
    [Reset Selection MAtricks]
    ClearAll
    [Set Cue <c> Sequence <s> Property 'TrigType' '<Token>']
    [Set Cue <c> Sequence <s> Property 'TrigTime' <absolute seconds>]
    [Assign Sequence <s> At Executor <m>]

Two axes this module owns and that no downstream layer may recompute (design.md
§2.2, single source of truth):

* the collided-attribute enumeration (look ∩ fx, effect wins — §3.3), and
* the uniform-set ordering + unclaimed-attribute enumeration (§6.1/§6.3).

Both are static computations over already-loaded ``Look``/``Fx`` objects; the
console is never queried for either one.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# @MX:WARN: [AUTO] every value-line generator this module calls is a PRIVATE
#   function of an upstream package (`server.looks.instantiate._values_line`,
#   `server.fx.instantiate._step_lines`/`_phase_lines`/`_speed_line`/`_matricks`).
# @MX:REASON: design.md §2.2 makes each of these the single source of truth for
#   the exact string it produces; re-implementing any of them here would be a
#   second copy that can drift out of sync with what `run_commands`' own dedupe
#   compares, and the drift is silent — a stored cue's content is not
#   machine-readable at all (spec.md §C.1). The precedent for importing a
#   private name across a package boundary is `server/looks/busking.py:30` and
#   `server/looks/songcue.py:11`, both importing `_values_line` the same way.
from server.fx.instantiate import (
    FxInstantiationError,
    _matricks,
    _phase_lines,
    _speed_line,
    _step_lines,
    collided_lines,
    is_programmer_state,
    select_sequence_number,
)
from server.fx.schema import Fx
from server.looks.instantiate import _values_line
from server.looks.schema import KNOWN_ATTRIBUTES, AttributeValue, Look
from server.scene.schema import TRIGGER_TOKENS, Scene

__all__ = [
    "CUE_NUMBER_UNAVAILABLE",
    "CUE_OCCUPIED",
    "CUE_SECTION_UNAVAILABLE",
    "CUE_TRUNCATED",
    "INVALID_TRIGGER_TOKEN",
    "NO_COMPOSITION_SOURCE",
    "SCENE_UNIFORM_ATTRIBUTES",
    "TRIGGER_INCOMPLETE",
    "UNIFORM_ATTRIBUTES_INCOMPLETE",
    "VALUE_LINE_COLLISION",
    "SceneCompilation",
    "SceneCompilationError",
    "collided_lines",
    "compile_scene",
    "is_programmer_state",
    "select_sequence_number",
]

# Why a scene could not be compiled into a bundle safe to fire. Kept apart
# rather than summed: each names a different fact and a different repair —
# the same discipline `server/fx/instantiate.py` and `server/looks/busking.py`
# follow for their own reason vocabularies.
NO_COMPOSITION_SOURCE = "no_composition_source"  # neither look nor fx supplied
UNIFORM_ATTRIBUTES_INCOMPLETE = "uniform_attributes_incomplete"  # look misses a core-4 attr
INVALID_TRIGGER_TOKEN = "invalid_trigger_token"  # trig_type outside the closed set
TRIGGER_INCOMPLETE = "trigger_incomplete"  # only one of trig_type/trig_time given
CUE_SECTION_UNAVAILABLE = "cue_section_unavailable"  # the cue pool could not be read at all
CUE_TRUNCATED = "cue_truncated"  # the cue listing was cut, so "free" is unknowable
CUE_NUMBER_UNAVAILABLE = "cue_number_unavailable"  # a cue in the pool carries no number
CUE_OCCUPIED = "cue_occupied"  # the requested cue number is taken
VALUE_LINE_COLLISION = "value_line_collision"  # two identical non-exempt lines in ONE bundle

_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"
_RESET_MATRICKS = "Reset Selection MAtricks"

# @MX:ANCHOR: [AUTO] the uniform set is a fixed 4-tuple, in this order, and
#   MUST equal `server.looks.schema.CONFIRMED_ATTRIBUTES` (asserted in
#   `test_scene_boundary.py`, M7 — the price of owning a second name for the
#   same measured band, decision E/K).
# @MX:REASON: design.md §6.1 — this is the ONLY mechanical enforcement point of
#   the tracking policy. Every scene that carries a look must emit these four
#   attributes in this order, so an earlier scene's leftover programmer value
#   is always overwritten regardless of whether MA3 tracks it forward.
SCENE_UNIFORM_ATTRIBUTES: tuple[str, ...] = ("Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B")

_UNIFORM_SET = frozenset(SCENE_UNIFORM_ATTRIBUTES)


class SceneCompilationError(ValueError):
    """A scene cannot be turned into a bundle that is safe to fire.

    Carries a ``reason`` code (see the module constants above) so a caller can
    branch on the fact rather than on the message text — the same shape as
    ``server.fx.instantiate.FxInstantiationError``.
    """

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


@dataclass(frozen=True)
class SceneCompilation:
    """One compiled scene: the bundle plus what it claims to create.

    ``collided_attributes`` and ``unclaimed_attributes`` are the two static
    enumerations design.md §3.3/§6.1 require the compiler itself to compute —
    neither is ever measured against the console.
    """

    scene_id: str
    display_name: str
    label: str
    group: int
    sequence: int
    cue: int
    look_id: str | None = None
    fx_id: str | None = None
    executor: int | None = None
    trig_type: str | None = None
    trig_time: float | None = None
    commands: tuple[str, ...] = ()
    collided_attributes: tuple[str, ...] = ()
    unclaimed_attributes: tuple[str, ...] = ()

    @property
    def non_exempt_commands(self) -> tuple[str, ...]:
        """The lines the instruction-scoped dedupe will compare."""
        return tuple(c for c in self.commands if not is_programmer_state(c))

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "display_name": self.display_name,
            "label": self.label,
            "group": self.group,
            "sequence": self.sequence,
            "cue": self.cue,
            "look_id": self.look_id,
            "fx_id": self.fx_id,
            "executor": self.executor,
            "trig_type": self.trig_type,
            "trig_time": self.trig_time,
            "collided_attributes": list(self.collided_attributes),
            "unclaimed_attributes": list(self.unclaimed_attributes),
            "commands": list(self.commands),
        }


def _format_value(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


# @MX:ANCHOR: [AUTO] the uniform-set reordering is an ARGUMENT ORDER CHOICE, not
#   a reassembly of the value-line string (design.md §2.2 is not violated: the
#   string itself still comes from `_values_line` alone).
# @MX:REASON: design.md §6.1 — sorting core-4 first then the rest in
#   declaration order means an earlier scene's leftover value on any of the
#   four is always explicitly overwritten by the next scene's look, whether or
#   not MA3 tracks the programmer forward. Today's 32/32 assets already sort
#   this way (byte-identical output), so removing this step changes nothing
#   observable until a future asset is authored out of order — which is
#   exactly why the ordering must be enforced here rather than trusted to
#   authoring convention.
def _ordered_look_values(look: Look) -> tuple[AttributeValue, ...]:
    by_name = {value.name: value for value in look.attributes}
    missing = [name for name in SCENE_UNIFORM_ATTRIBUTES if name not in by_name]
    if missing:
        raise SceneCompilationError(
            UNIFORM_ATTRIBUTES_INCOMPLETE,
            f"look {look.look_id!r} is missing uniform attribute(s) {missing}; "
            "every scene carrying a look must assert the core-4 set explicitly "
            "so a leftover programmer value is always overwritten",
        )
    uniform = tuple(by_name[name] for name in SCENE_UNIFORM_ATTRIBUTES)
    rest = tuple(value for value in look.attributes if value.name not in _UNIFORM_SET)
    return uniform + rest


# -- cue number -----------------------------------------------------------


def _cue_numbers(cues_section: Mapping[str, object]) -> set[int]:
    listed = cues_section.get("objects")
    if not isinstance(listed, list):
        raise SceneCompilationError(
            CUE_SECTION_UNAVAILABLE,
            "the cue pool could not be read, so no free cue number can be measured; "
            "inventing one is forbidden (REQ-SCENE-013)",
        )
    occupied: set[int] = set()
    for entry in listed:
        number = entry.get("no") if isinstance(entry, Mapping) else None
        if not isinstance(number, int):
            # A cue in this pool carries no number — some cue in it is taken
            # and we cannot say which, so no number in the pool can be claimed
            # free (the same split fx's `_sequence_numbers` makes for sequences).
            raise SceneCompilationError(
                CUE_NUMBER_UNAVAILABLE,
                "a cue in the pool carries no number, so no number in the pool can be claimed free",
            )
        occupied.add(number)
    return occupied


def _select_cue_number(cues_section: Mapping[str, object], *, requested: int | None = None) -> int:
    """Measure a free cue number from a re-queried pool — scene's own logic.

    A cue number is never a saved asset field (REQ-SCENE-004) and fx's own
    ``Store`` is fixed at ``Cue 1`` (design.md §5), so this is not a third copy
    of anything upstream — there is no upstream cue-number logic to reuse.
    """
    unavailable = cues_section.get("reason")
    if isinstance(unavailable, str) or cues_section.get("ok") is False:
        raise SceneCompilationError(
            CUE_SECTION_UNAVAILABLE,
            "the cue pool could not be read "
            f"({unavailable or 'the section reported not-ok'}), so no free cue "
            "number can be measured",
        )
    if cues_section.get("truncated"):
        raise SceneCompilationError(
            CUE_TRUNCATED,
            "the cue pool listing was truncated, so an unlisted cue may hold any "
            "candidate number; automatic assignment is refused",
        )
    occupied = _cue_numbers(cues_section)
    if requested is not None:
        if requested in occupied:
            raise SceneCompilationError(
                CUE_OCCUPIED,
                f"cue {requested} is already occupied; scenes never store onto an "
                "existing cue (no /Overwrite, no un-flagged Store)",
            )
        return requested
    candidate = 1
    while candidate in occupied:
        candidate += 1
    return candidate


# -- guard ------------------------------------------------------------------


# @MX:WARN: [AUTO] refuses (raises) rather than skips.
# @MX:REASON: a scene bundle is ONE store — there is no surviving remainder to
#   report, exactly like fx's own `_guard_collision` (design.md §4.1). The
#   scene's collision surface is WIDER than fx's own guard: a scene bundle
#   carries both the look's value line and the fx's step value lines, so this
#   check runs over the fully assembled command list, not just the fx portion.
#   Exemption is a call to `is_programmer_state` — this module owns no second
#   copy of that regex (decision E).
def _guard_collision(commands: Sequence[str], *, scene_id: str) -> None:
    seen: set[str] = set()
    for command in commands:
        if is_programmer_state(command):
            continue
        if command in seen:
            raise SceneCompilationError(
                VALUE_LINE_COLLISION,
                f"scene {scene_id!r} would emit the line {command!r} twice; the "
                "second one is dropped by the run_commands dedupe and the Store "
                "then runs against a programmer that is missing a value — "
                "silently, because a stored cue's content is not machine-readable",
            )
        seen.add(command)


# -- compilation --------------------------------------------------------------


def _effective_trigger(
    scene: Scene, trig_type: str | None, trig_time: float | None
) -> tuple[str | None, float | None]:
    """The caller may override the scene's authored trigger intent (schema.py)."""
    effective_type = scene.trig_type if trig_type is None else trig_type
    effective_time = scene.trig_time if trig_time is None else trig_time
    if (effective_type is None) != (effective_time is None):
        raise SceneCompilationError(
            TRIGGER_INCOMPLETE,
            "a trigger needs both trig_type and trig_time; only one was given "
            f"(trig_type={effective_type!r}, trig_time={effective_time!r})",
        )
    if effective_type is not None and effective_type not in TRIGGER_TOKENS:
        raise SceneCompilationError(
            INVALID_TRIGGER_TOKEN,
            f"trig_type must be one of {list(TRIGGER_TOKENS)}, got {effective_type!r}",
        )
    return effective_type, effective_time


def compile_scene(
    scene: Scene,
    *,
    look: Look | None,
    fx: Fx | None,
    group: int,
    sequences_section: Mapping[str, object],
    cues_section: Mapping[str, object],
    sequence_number: int | None = None,
    cue_number: int | None = None,
    trig_type: str | None = None,
    trig_time: float | None = None,
    executor: int | None = None,
) -> SceneCompilation:
    """Compile one scene against one already-resolved group and re-queried rig.

    ``group`` is a number the CALLER measured from the rig — this function
    never derives, guesses or renumbers it. ``sequences_section``/
    ``cues_section`` are re-queried listings; sequence numbers are measured by
    fx's own `select_sequence_number` (decision H — no second implementation),
    cue numbers by this module's own logic (decision I — fx's Store is fixed
    at Cue 1 and cannot be reused).
    """
    if look is None and fx is None:
        raise SceneCompilationError(
            NO_COMPOSITION_SOURCE,
            f"scene {scene.scene_id!r} carries neither a look nor an fx; there is "
            "nothing to compose (REQ-SCENE-003)",
        )

    look_attributes = frozenset(value.name for value in look.attributes) if look else frozenset()
    fx_attributes = frozenset(fx.attributes) if fx else frozenset()

    # @MX:ANCHOR: [AUTO] this intersection/difference is a pure function of the
    #   already-loaded look/fx attribute sets — the console is never queried.
    # @MX:REASON: design.md §3.3 (collided attributes: effect wins, enumerated
    #   for the report) and §6.1(다) (unclaimed attributes: the universe this
    #   scene did NOT assert, so a future reader is not left guessing whether an
    #   axis was silently inherited). Both are computed exactly once, here.
    collided_attributes = tuple(sorted(look_attributes & fx_attributes))
    unclaimed_attributes = tuple(sorted(KNOWN_ATTRIBUTES - (look_attributes | fx_attributes)))

    try:
        sequence = select_sequence_number(sequences_section, requested=sequence_number)
    except FxInstantiationError as error:
        # fx owns the sequence-number LOGIC (decision H) and its reason
        # vocabulary; this package owns its exception TYPE. Letting
        # `FxInstantiationError` cross the boundary would make every caller of a
        # scene catch an fx class to stay correct — and the tool layer that did
        # not know to do so crashed instead of refusing (found by
        # `test_scene_tool.py::...refused_before_any_cue_question`). The reason
        # code travels unchanged so the two layers keep ONE vocabulary.
        raise SceneCompilationError(error.reason, str(error)) from error
    cue = _select_cue_number(cues_section, requested=cue_number)
    effective_trig_type, effective_trig_time = _effective_trigger(scene, trig_type, trig_time)

    commands: list[str] = [_DESTINATION, _CLEAR, f"Group {group}"]

    if look is not None:
        commands.append(_values_line(_ordered_look_values(look)))

    matricks: tuple[tuple[str, float], ...] = ()
    if fx is not None:
        commands.extend(_step_lines(fx))
        commands.extend(_phase_lines(fx))
        commands.extend(_speed_line(fx))
        matricks = _matricks(fx)
        commands.extend(
            f"Set Selection MAtricks '{axis}' {_format_value(value)}" for axis, value in matricks
        )

    # @MX:WARN: [AUTO] the Store line never carries a flag — not `/CueOnly`, not
    #   `/Overwrite`, not `/Merge`.
    # @MX:REASON: M0 measured that the console silently ACCEPTS an unknown store
    #   flag with `ok:true` and the cue still saves under its intended name/cueNo
    #   (a fabricated control probe, `/CueOnlyy`, was accepted — design.md §6.0).
    #   A typo'd flag therefore leaves no runtime signal on either the `ok`
    #   channel or a re-query; the only net is never opening the flag axis at
    #   all, which this line's fixed format guarantees.
    commands.append(f"Store Sequence {sequence} Cue {cue} '{scene.label}'")
    if matricks:
        # After the Store: the sub-selection is part of the shape being stored,
        # so releasing it earlier would store the undivided effect (design.md §3.4).
        commands.append(_RESET_MATRICKS)
    commands.append(_CLEAR)
    if effective_trig_type is not None:
        # PROPERTY form only — never `/trig=` (onPC 2.4.2 refuses that form as
        # "Illegal object"). Trigger lines sit AFTER the capture-cycle ClearAll
        # because they touch a saved cue's property, not programmer state.
        commands.append(
            f"Set Cue {cue} Sequence {sequence} Property 'TrigType' '{effective_trig_type}'"
        )
        commands.append(
            f"Set Cue {cue} Sequence {sequence} Property 'TrigTime' "
            f"{_format_value(effective_trig_time or 0.0)}"
        )
    if executor is not None:
        # Explicit only — never auto-assigned, and always the last line: it is
        # outside the capture cycle (design.md §3.4, `_ASSIGN_IS_LAST` precedent).
        commands.append(f"Assign Sequence {sequence} At Executor {executor}")

    _guard_collision(commands, scene_id=scene.scene_id)

    return SceneCompilation(
        scene_id=scene.scene_id,
        display_name=scene.display_name,
        label=scene.label,
        group=group,
        sequence=sequence,
        cue=cue,
        look_id=scene.look_id,
        fx_id=scene.fx_id,
        executor=executor,
        trig_type=effective_trig_type,
        trig_time=effective_trig_time,
        commands=tuple(commands),
        collided_attributes=collided_attributes,
        unclaimed_attributes=unclaimed_attributes,
    )
