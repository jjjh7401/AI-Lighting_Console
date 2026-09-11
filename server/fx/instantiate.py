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

from server.fx.schema import MIN_STEPS, Fx

__all__ = [
    "CIRCLE_PHASE_CONFLICT",
    "CROSS_CALL_COLLISION",
    "PRESET_NUMBER_UNAVAILABLE",
    "PRESET_OCCUPIED",
    "PRESET_POOL_TRUNCATED",
    "PRESET_POOL_UNAVAILABLE",
    "SPEED_SOURCE_CONFLICT",
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
    "phaser_lines",
    "build_fx_preset_bundle",
    "select_preset_number",
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
SPEED_SOURCE_CONFLICT = "speed_source_conflict"  # both a fixed BPM and a master binding
PRESET_POOL_UNAVAILABLE = "preset_pool_unavailable"  # the preset pool could not be read
PRESET_POOL_TRUNCATED = "preset_pool_truncated"  # the pool listing was cut short
PRESET_NUMBER_UNAVAILABLE = "preset_number_unavailable"  # a pool child carries no number
PRESET_OCCUPIED = "preset_occupied"  # the requested preset slot is taken
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
    label: str
    # Destination: EITHER a sequence + cue (the original shape) OR a preset
    # slot in a pool (`Store Preset <pool>.<n> /Universal`, live-verified —
    # the "All" pools accept multistep/phaser data regardless of feature group).
    sequence: int | None = None
    preset_pool: int | None = None
    preset: int | None = None
    commands: tuple[str, ...] = ()
    cue: int | None = _CUE_NUMBER
    executor: int | None = None
    attributes: tuple[str, ...] = ()
    step_count: int = 0
    speed_bpm: float | None = None
    speed_master: int | None = None
    width: float | None = None
    measure: float | None = None
    accel: float | None = None
    decel: float | None = None
    relative: bool = False
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
            "preset_pool": self.preset_pool,
            "preset": self.preset,
            "label": self.label,
            "executor": self.executor,
            "attributes": list(self.attributes),
            "step_count": self.step_count,
            "speed_bpm": self.speed_bpm,
            "speed_master": self.speed_master,
            "width": self.width,
            "measure": self.measure,
            "accel": self.accel,
            "decel": self.decel,
            "relative": self.relative,
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


# -- preset slot -----------------------------------------------------------------


def select_preset_number(
    presets_section: Mapping[str, object], *, requested: int | None = None
) -> int:
    """Measure a free preset slot from a re-queried pool listing.

    The mirror of ``select_sequence_number`` with the same refusal discipline:
    an unreadable or truncated listing licenses NO number, and a child without
    a number poisons the whole pool ("free" cannot be measured).
    """
    unavailable = presets_section.get("reason")
    if isinstance(unavailable, str) or presets_section.get("ok") is False:
        raise FxInstantiationError(
            PRESET_POOL_UNAVAILABLE,
            "the preset pool could not be read "
            f"({unavailable or 'the section reported not-ok'}), so no free slot "
            "can be measured",
        )
    if presets_section.get("truncated"):
        raise FxInstantiationError(
            PRESET_POOL_TRUNCATED,
            "the preset pool listing was truncated, so an unlisted preset may hold "
            "any candidate slot; automatic assignment is refused",
        )
    listed = presets_section.get("objects")
    if not isinstance(listed, list):
        raise FxInstantiationError(
            PRESET_POOL_UNAVAILABLE,
            "the preset pool carries no object listing, so no free slot can be "
            "measured; inventing one is forbidden",
        )
    occupied: set[int] = set()
    for entry in listed:
        number = entry.get("no") if isinstance(entry, Mapping) else None
        if not isinstance(number, int):
            raise FxInstantiationError(
                PRESET_NUMBER_UNAVAILABLE,
                "a preset in the pool carries no number, so no slot in the pool "
                "can be claimed free",
            )
        occupied.add(number)
    if requested is not None:
        if requested in occupied:
            raise FxInstantiationError(
                PRESET_OCCUPIED,
                f"preset slot {requested} is already occupied; this path never "
                "stores onto an existing preset (no /Merge, no un-flagged Store)",
            )
        return requested
    candidate = 1
    while candidate in occupied:
        candidate += 1
    return candidate


# -- bundle construction -------------------------------------------------------


def _format_value(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _english_fallback_label(fx: Fx) -> str:
    """A console-displayable English name derived from the fx_id.

    ``sweep-soft-wide`` -> ``Soft Wide Sweep`` (the leading pattern token
    reads better trailing, matching how the Korean display names are built).
    """
    parts = [part for part in fx.fx_id.replace("_", "-").split("-") if part]
    if len(parts) > 1 and parts[0].casefold() == fx.pattern.casefold():
        parts = parts[1:] + parts[:1]
    derived = " ".join(part.capitalize() for part in parts)
    return derived or fx.pattern.capitalize()


def _label_of(fx: Fx, label: str | None) -> str:
    text = fx.display_name if label is None else label
    if not text.strip():
        raise FxInstantiationError(
            LABEL_UNQUOTABLE, f"fx {fx.fx_id!r} has an empty label to store under"
        )
    if not text.isascii():
        # 실기 2026-08-16 (사용자 발견): onPC 2.4.2 풀 타일이 한글 라벨을
        # 표시하지 못한다 — 저장은 접수되지만 이름이 보이지 않는다. 보이지
        # 않는 이름 대신 fx_id에서 파생한 영어 라벨을 자동으로 붙인다.
        text = _english_fallback_label(fx)
        if not text.strip() or not text.isascii():
            # 독립 리뷰 2026-08-16: fx_id에 ASCII 슬러그 제약이 없으므로
            # 파생 폴백 자체가 비ASCII/공백일 수 있다 — 그대로 내보내면
            # 이 수정이 막으려던 '보이지 않는 라벨'이 재발한다. 구조적 거부.
            raise FxInstantiationError(
                LABEL_UNQUOTABLE,
                f"fx {fx.fx_id!r} yields no console-displayable ASCII label — "
                f"give the fx an ASCII fx_id or pass an explicit English label",
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
    if fx.speed is not None and fx.speed_master is not None:
        # Measured V3 bound the phaser to a master INSTEAD of a fixed BPM; the
        # combination of both lines on one attribute is unmeasured. The loader
        # already refuses this, but a directly-constructed Fx never met it.
        raise FxInstantiationError(
            SPEED_SOURCE_CONFLICT,
            f"fx {fx.fx_id!r} declares both speed={_format_value(fx.speed)} and "
            f"speed_master={fx.speed_master}; the combination is unmeasured — "
            "pick a fixed BPM or a master binding, not both",
        )


def _step_lines(fx: Fx) -> list[str]:
    """The step run: index ``i`` is console step ``i + 1``.

    ``Step 1`` is never emitted — the first step is the current one — and each
    later step is opened by a STANDALONE ``Step <k>`` line placed before its own
    value lines. ``Attribute '<attr>' At Step <k>`` is a forbidden form: the
    console accepts it with ok:true and nothing happens (REQ-FXLIB-022).
    """
    lines: list[str] = []
    verb = "At Relative" if fx.relative else "At"
    for index, step in enumerate(fx.steps):
        if index:
            lines.append(f"Step {index + 1}")
        lines.extend(
            f"Attribute '{value.attribute}' {verb} {_format_value(value.value)}"
            for value in step.values
        )
    return lines


def _curve_lines(fx: Fx) -> list[str]:
    """The per-step curve lines — AFTER the whole step run exists.

    Measured 2026-08-15 (V1): `Step <k> At Accel -100` / `At Decel -100` fired
    after both steps were built renders a sinusoidal fade. M0's SKIP came from
    firing the same literals into a programmer that held no second step yet, so
    the ordering here is the measurement, not a style choice.
    """
    lines: list[str] = []
    for index in range(len(fx.steps)):
        if fx.accel is not None:
            lines.append(f"Step {index + 1} At Accel {_format_value(fx.accel)}")
        if fx.decel is not None:
            lines.append(f"Step {index + 1} At Decel {_format_value(fx.decel)}")
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


def _timing_lines(fx: Fx) -> list[str]:
    """Width, Measure, then the speed source (fixed BPM or master binding).

    Each follows the `_speed_line` precedent: one `;`-chained line per axis
    covering every target attribute (the `;` chain is a validated literal and
    stays OFF the step value lines — design.md §4.3). Width narrows each step
    (V4), Measure scales the whole loop in beats (V4), and `At SpeedMaster <n>`
    binds the phaser to a live master instead of a fixed BPM (V3).
    """
    lines: list[str] = []
    if fx.width is not None:
        lines.append(
            " ; ".join(
                f"Attribute '{name}' At Width {_format_value(fx.width)}" for name in fx.attributes
            )
        )
    if fx.measure is not None:
        lines.append(
            " ; ".join(
                f"Attribute '{name}' At Measure {_format_value(fx.measure)}"
                for name in fx.attributes
            )
        )
    if fx.speed is not None:
        lines.append(
            " ; ".join(
                f"Attribute '{name}' At Speed {_format_value(fx.speed)}" for name in fx.attributes
            )
        )
    if fx.speed_master is not None:
        lines.append(
            " ; ".join(
                f"Attribute '{name}' At SpeedMaster {fx.speed_master}" for name in fx.attributes
            )
        )
    return lines


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


# @MX:ANCHOR: [AUTO] 페이저 문법의 **유일한** 생산 지점. 캡처 사이클(선택·Store·
#   ClearAll)은 호출자가 갖고, 그 안쪽 줄은 전부 여기서 나온다.
# @MX:REASON: 이 줄들은 발사 후 되읽을 수 없다 — 저장된 페이저 큐는 빈 큐와 구별되지
#   않는다(모듈 머리의 @MX:WARN). 문법이 두 곳에 있으면 한쪽만 고쳐지고, 그 갈라짐은
#   콘솔이 ok 를 답하는 동안 무대에서만 보인다. `server/looks/movement.py` 가 룩의
#   `MovementSpec` 을 여기로 들고 오는 이유가 그것이다: 룩 계층은 축과 세기만 정하고
#   명령 문면은 만들지 않는다.
def phaser_lines(fx: Fx) -> tuple[str, ...]:
    """캡처 사이클 **안쪽**의 페이저 줄들 — 스텝 런 · 커브 · 위상 · 타이밍.

    선택 줄도, ``Store`` 도, ``ClearAll`` 도 넣지 않는다: 그 셋은 사이클의 소유자
    (:func:`build_fx_bundle` · :func:`build_fx_preset_bundle` · 곡 큐 번들)의 몫이다.
    MAtricks 도 뺀다 — 그 축은 ``Store`` **뒤**의 ``Reset Selection MAtricks`` 와
    한 쌍이므로, 반쪽만 여기서 내면 선택 분할이 풀리지 않은 채 남는다.

    ``_refuse_unemitted_axes`` 를 먼저 부른다. 스텝이 둘 미만인 엔트리는 여기서
    거절되며, 그 거절이 이 계층의 존재 이유다: 스텝 없는 수정자 줄만 내면 모든 줄이
    ``ok:true`` 를 받고 무대는 가만히 있는다.
    """
    _refuse_unemitted_axes(fx)
    return tuple([*_step_lines(fx), *_curve_lines(fx), *_phase_lines(fx), *_timing_lines(fx)])


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
    commands.extend(phaser_lines(fx))
    commands.extend(f"Set Selection MAtricks '{axis}' {_format_value(v)}" for axis, v in matricks)
    commands.append(f"Store Sequence {sequence} Cue {_CUE_NUMBER} '{text}'")
    # The quoted store name labels the CUE only; the SEQUENCE object stays
    # unnamed and shows as a bare number in every pool/executor view (user
    # report, 2026-08-15 live test). Label it too — the same validated form
    # songcue.py/layout.py already emit (`Label Sequence <n> '<name>'`).
    commands.append(f"Label Sequence {sequence} '{text}'")
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
        speed_master=fx.speed_master,
        width=fx.width,
        measure=fx.measure,
        accel=fx.accel,
        decel=fx.decel,
        relative=fx.relative,
        matricks=matricks,
    )


def build_fx_preset_bundle(
    fx: Fx,
    *,
    group: int,
    preset_pool: int,
    preset: int,
    label: str | None = None,
) -> FxInstantiation:
    """Build the bundle that stores one fx as a PRESET instead of a cue.

    Live-verified shape: the same capture cycle as ``build_fx_bundle`` with the
    Store line swapped for ``Store Preset <pool>.<n> '<label>' /Universal`` —
    an "All" pool accepts phaser data regardless of feature group, and
    ``/Universal`` makes the preset applicable to any compatible fixture. The
    pool NUMBER is a per-show fact the CALLER measured from the rig (the pool
    named "All 1" is not guaranteed a fixed slot), and so is the free preset
    slot. Executor binding is a sequence concept and has no meaning here.
    """
    _refuse_unemitted_axes(fx)
    text = _label_of(fx, label)
    matricks = _matricks(fx)

    commands: list[str] = [_DESTINATION, _CLEAR, f"Group {group}"]
    commands.extend(phaser_lines(fx))
    commands.extend(f"Set Selection MAtricks '{axis}' {_format_value(v)}" for axis, v in matricks)
    commands.append(f"Store Preset {preset_pool}.{preset} '{text}' /Universal")
    # 실기 2026-08-16 (사용자 발견): the inline '<label>' on Store Preset is
    # ACCEPTED (ok) but NOT applied as the pool label — the presets landed
    # nameless. Same console behavior the position-preset path already works
    # around (`server/spatial/pointing.py::position_preset_store_commands`):
    # the name must ride its own Label line.
    commands.append(f"Label Preset {preset_pool}.{preset} '{text}'")
    if matricks:
        commands.append(_RESET_MATRICKS)
    commands.append(_CLEAR)

    _guard_collision(fx, commands)
    return FxInstantiation(
        fx_id=fx.fx_id,
        display_name=fx.display_name,
        pattern=fx.pattern,
        group=group,
        sequence=None,
        cue=None,
        preset_pool=preset_pool,
        preset=preset,
        label=text,
        commands=tuple(commands),
        attributes=fx.attributes,
        step_count=len(fx.steps),
        speed_bpm=fx.speed,
        speed_master=fx.speed_master,
        width=fx.width,
        measure=fx.measure,
        accel=fx.accel,
        decel=fx.decel,
        relative=fx.relative,
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
