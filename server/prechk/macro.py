"""Response-check macro authoring — group targets only (design.md slot D).

The pre-check can answer *"is the patch consistent?"* from metadata alone, but it
can NEVER answer *"did that fixture actually light up?"* — the responder collects
no hardware feedback and its verb table is closed at five
(``console/lua/copilot_responder.lua:884-946``). So this module builds the tool a
human uses instead: a macro that walks the rig's groups on and off, one pair at a
time, for someone standing in the room to watch.

**Groups are a FORCED reduction, not a design preference.** Selecting individual
fixtures needs a FID, and this show file cannot prove what its ``FID`` values
mean — it is patched slot == FID, so a correct FID probe and a slot probe are
indistinguishable (``console/lua/PROTOCOL.md:305-324``). ``REQ-PRECHK-005``
therefore bars FID from every judgement, and substituting the slot is what
``REQ-LOOKLIB-008`` forbids because it silently selects the wrong lights on any
rig where they diverge. Per-fixture response checking is consequently NOT a
product of this SPEC (``REQ-PRECHK-011``); it opens when a show file patched
slot != FID exists. Groups are what remains, and they are what the rig's operator
already grouped by hand.

Authoring grammar — **three steps, not the rulebook's two**
------------------------------------------------------------
``server/rulebook/assets/v2.4.2/00_grammar.md:80-84`` gives a two-step recipe:
create the macro, then set each line's ``Command``. M0 measured that recipe
FAILING: without a line object the third step has no target and the console
answers ``Illegal object``. The measured sequence is::

    Store Macro <n>                                       # the macro object
    Store Macro <n>.<line>                                # the LINE object
    Set Macro <n>.<line> Property 'Command' '<text>'      # the line's content

recorded as the ``GO: ASSUMPTION-26 literal=…`` prefix line in this SPEC's
``progress.md`` (that line is the canon; ``server/tests/test_prechk_macro.py``
parses it and compares shapes rather than trusting a transcription here). Each
line's ``Store`` immediately precedes its ``Set``, which is the measured order.

Stored line text — why the off line is not ``Off Group <n>``
------------------------------------------------------------
On the production path the quoted value of ``Property 'Command' '<text>'`` is
reclassified RECURSIVELY by the gate (``server/safety/classify.py:201-222``), so
the stored text is screened as if it had been sent bare. ``Off`` is an invoking
verb (``server/safety/blacklist.yaml`` key ``invoking_verbs.verbs`` -- the key
path and not a line number, because that file grows and this anchor drifted
twice during SPEC-COPILOT-WRITEGATE-001 alone) and its target ``Group`` is not a
recognized reference type (``server/safety/classify.py:44``), so ``Off Group
<n>`` resolves to no verifiable reference and the whole authoring command is HELD
(``server/safety/expand.py:83``). ``server/tests/test_prechk_macro.py`` pins that
classification difference directly, so the reasoning is checked rather than
asserted in prose. The value form ``Group <n> At 0`` classifies safe and is what
this module stores; it was MEASURED on the live console in the M4 supplementary
session and appears in the ``GO: ASSUMPTION-26`` prefix line of
``.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md`` §E.2, which is the canon
``server/tests/test_prechk_macro.py`` compares every stored payload against.
The rulebook shows ``At`` as a value verb but never this exact target form
(``server/rulebook/assets/v2.4.2/00_grammar.md:54`` gives ``Fixture 1 Thru 10 At
80``), so the rulebook is NOT the authority here — the measurement is.

The on line is ``On Group <n>``, the form M0 measured with its effect confirmed
by re-query. Note that ``On`` sits in the SAME invoking-verb list as ``Off``
(``server/safety/blacklist.yaml`` key ``invoking_verbs.verbs``), so that
authoring line is likewise held for human approval on the production path — a
defined outcome (``AC-PRECHK-014`` ④), and the gate screens bundles whole, so a
hold means zero sends rather than a half-written macro. M0's probe channel
bypasses the gate (the driver reaches ``server.bridge`` directly, which is why
the measurement did not surface the hold; the gate path is exercised by
``server/tests/test_prechk_tool.py`` instead).

No execution surface lives here
------------------------------
This module produces a command LIST and stops. Executing it itself would BE the
second execution surface ``REQ-PRECHK-018`` forbids: commands must ride
``run_commands`` → ``bundle_gate.screen()``, and a ``CommandExecutionPort`` used
from here would send unscreened. The M6 tool handler is the caller of that
existing path. This is not a pass-through: the module reads a group pool
snapshot, drops unaddressable groups, allocates macro slots and line numbers,
expands each group into the measured three-step sequence, checks every command
against the transport's rejected characters, accounts the pairs, and assigns the
closed-vocabulary skip verdict when it produces nothing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from server.prechk.verdicts import validate

__all__ = [
    "ASSUMPTION_MACRO_AUTHORING",
    "AUTHORING_DESCOPED",
    "GROUPS_UNADDRESSABLE",
    "GROUP_POOL_EMPTY",
    "GROUP_POOL_PATH",
    "OFF",
    "ON",
    "PARTIAL_GROUP_COVERAGE",
    "TARGET_KIND_GROUP",
    "VISUAL_CONFIRMATION_REQUIRED",
    "GroupPool",
    "GroupTarget",
    "MacroLine",
    "MacroPolicy",
    "MacroResult",
    "build_response_check_macro",
    "groups_from_snapshot",
    "reason_label",
]

# The group pool path. `DataPool/Groups` is live-calibrated
# (`server/orchestrator/tools.py:93-95`) and returned four groups on the
# measured rig.
GROUP_POOL_PATH = "DataPool/Groups"

# The only target kind this SPEC produces (see the module docstring).
TARGET_KIND_GROUP = "group"

ASSUMPTION_MACRO_AUTHORING = "ASSUMPTION-26"

# Line phases. A pair is exactly one of each.
ON = "on"
OFF = "off"

# Reason codes. Codes live with the producer and Korean labels with the
# presentation layer, the split `server/looks/instantiate.py` and
# `server/looks/report.py:61-88` already use.
VISUAL_CONFIRMATION_REQUIRED = "visual_confirmation_required"
AUTHORING_DESCOPED = "authoring_descoped"
GROUP_POOL_EMPTY = "group_pool_empty"
GROUPS_UNADDRESSABLE = "groups_unaddressable"
PARTIAL_GROUP_COVERAGE = "partial_group_coverage"

# Skipped-check kinds, drawn from the closed vocabulary (design.md slot C).
_SKIP_DESCOPE = "macro_descope"
_SKIP_NO_GROUPS = "macro_no_groups"

_REASON_LABELS = {
    VISUAL_CONFIRMATION_REQUIRED: (
        "매크로를 콘솔에서 실행하고 그룹이 점등·소등하는지 사람이 눈으로 확인하십시오 — "
        "실행 결과의 ok는 커맨드 접수만 뜻하며 픽스처가 응답했다는 증거가 아닙니다"
    ),
    AUTHORING_DESCOPED: "매크로 저작 문법이 실측되지 않아 매크로를 생성하지 않았습니다",
    GROUP_POOL_EMPTY: (
        "리그에 그룹이 없어 매크로를 생성하지 않았습니다 — 대체 대상을 발명하지 않습니다"
    ),
    GROUPS_UNADDRESSABLE: (
        "그룹은 있으나 번호가 없어 대상으로 쓸 수 없습니다 — 이름으로 선택하지 않습니다"
    ),
    PARTIAL_GROUP_COVERAGE: "그룹 열거가 절단되어 관측된 그룹만 대상입니다",
}

# `server/bridge/protocol.py:103-111` rejects these before the wire, so a command
# carrying one never reaches the console and never reaches the audit log either.
_TRANSPORT_REJECTED = ('"', "\n", "\r")


def reason_label(code: str) -> str:
    """The Korean label for a reason code; an unknown code passes through.

    Unknown codes are returned verbatim rather than translated, so a string that
    came up from the console or the M0 record stays searchable by its original
    text — the same contract as ``server/looks/report.py``'s accessor.
    """
    return _REASON_LABELS.get(code, code)


def _positive_slot(value: object, *, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{what} must be a positive integer, got {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class GroupTarget:
    """One addressable group: the number the macro speaks, plus its name.

    Only ``no`` reaches a command. The name is for the report — a group NAME can
    never enter a stored line because MA3 quoting has no escape for a quote
    nested inside the property value
    (``server/rulebook/assets/v2.4.2/00_grammar.md:97-101``).
    """

    no: int
    name: str = ""

    def __post_init__(self) -> None:
        _positive_slot(self.no, what="group number")

    def to_dict(self) -> dict[str, object]:
        return {"no": self.no, "name": self.name}


@dataclass(frozen=True, slots=True)
class GroupPool:
    """The observed group pool: what is addressable, what is not, and coverage.

    ``unaddressable`` is kept rather than discarded because "the rig has no
    groups" and "the rig's groups have no numbers" are different facts with
    different user actions. ``truncated`` is kept for the same reason the
    inventory keeps it: a macro built from a truncated enumeration covers only
    the groups that were observed, and saying so is cheaper than being wrong.
    """

    targets: tuple[GroupTarget, ...] = ()
    unaddressable: tuple[str, ...] = ()
    truncated: bool = False

    def __post_init__(self) -> None:
        numbers = [target.no for target in self.targets]
        duplicates = sorted({no for no in numbers if numbers.count(no) > 1})
        if duplicates:
            raise ValueError(f"duplicate group numbers in the pool: {duplicates}")


def groups_from_snapshot(payload: Mapping[str, object]) -> GroupPool:
    """Read a ``state DataPool/Groups`` payload into a :class:`GroupPool`.

    Truncation is decided by comparing ``node.childCount`` with the number of
    children returned, not by trusting ``truncated`` alone: the count is the true
    total and the comparison is what survives a missing or stale flag
    (``spec.md`` §A constraint 2, the same discipline as ``REQ-PRECHK-004``).
    """
    if not payload.get("ok"):
        detail = payload.get("error") or payload.get("path") or GROUP_POOL_PATH
        raise ValueError(f"group pool snapshot is not ok: {detail}")

    raw_children = payload.get("children") or ()
    if not isinstance(raw_children, Sequence) or isinstance(raw_children, str | bytes):
        raise ValueError(
            f"group pool children must be a sequence, got {type(raw_children).__name__}"
        )

    targets: list[GroupTarget] = []
    unaddressable: list[str] = []
    for child in raw_children:
        name = ""
        number: int | None = None
        if isinstance(child, Mapping):
            name = str(child.get("name") or "")
            raw_index = child.get("i")
            if isinstance(raw_index, int) and not isinstance(raw_index, bool) and raw_index >= 1:
                number = raw_index
        if number is None:
            unaddressable.append(name or "<unnamed>")
            continue
        targets.append(GroupTarget(no=number, name=name))

    truncated = bool(payload.get("truncated"))
    node = payload.get("node")
    child_count = node.get("childCount") if isinstance(node, Mapping) else None
    countable = isinstance(child_count, int) and not isinstance(child_count, bool)
    if countable and child_count > len(raw_children):
        truncated = True

    return GroupPool(
        targets=tuple(targets), unaddressable=tuple(unaddressable), truncated=truncated
    )


@dataclass(frozen=True, slots=True)
class MacroPolicy:
    """Whether the authoring grammar is available, and where to write.

    ``macro_slot`` is the CALLER's choice and has no default on purpose: slot 1
    holds the responder's own ``Copilot Go`` macro on the measured rig, and only
    a live pool read can tell which slot is free. Picking one here would make
    overwriting it the quiet default.

    A negative policy must carry the reason M0 recorded. A descope with no reason
    is indistinguishable from a bug, and ``REQ-PRECHK-012`` pairs the zero-command
    outcome with a recorded ``DESCOPE:`` line.
    """

    authoring_available: bool
    macro_slot: int = 0
    descope_reason: str = ""

    def __post_init__(self) -> None:
        if self.authoring_available:
            _positive_slot(self.macro_slot, what="macro slot")
            if self.descope_reason.strip():
                raise ValueError("an available policy must not carry a descope reason")
        elif not self.descope_reason.strip():
            raise ValueError("a descoped policy must carry the reason M0 recorded")

    @classmethod
    def available(cls, macro_slot: int) -> MacroPolicy:
        """ASSUMPTION-26 is GO: author into ``macro_slot``."""
        return cls(authoring_available=True, macro_slot=macro_slot)

    @classmethod
    def descoped(cls, reason: str) -> MacroPolicy:
        """ASSUMPTION-26 is negative: speak zero macro commands, answer why."""
        return cls(authoring_available=False, descope_reason=reason)


@dataclass(frozen=True, slots=True)
class MacroLine:
    """One macro line: its number, the group it drives, and the stored text."""

    number: int
    group_no: int
    phase: str
    payload: str


def _on_payload(group_no: int) -> str:
    return f"On Group {group_no}"


def _off_payload(group_no: int) -> str:
    # NOT `Off Group <n>` -- see the module docstring.
    return f"Group {group_no} At 0"


def _check_transportable(command: str) -> str:
    for character in _TRANSPORT_REJECTED:
        if character in command:
            raise ValueError(f"command carries a rejected character {character!r}: {command!r}")
    return command


@dataclass(frozen=True, slots=True)
class MacroResult:
    """What the macro axis produced, or why it produced nothing.

    ``requires_human_visual_confirmation`` is a class constant, not a field: it
    does not vary with ``created``. Fixture response is not machine-decidable
    anywhere in this SPEC (``REQ-PRECHK-014``, ``spec.md`` §D), so a flag that
    flipped to ``False`` when nothing was authored would read as "no human check
    needed" — the one claim this module must never make.
    """

    created: bool
    target_kind: str
    reason: str
    reason_code: str
    targets: tuple[GroupTarget, ...] = ()
    lines: tuple[MacroLine, ...] = ()
    commands: tuple[str, ...] = ()
    macro_slot: int = 0
    skipped_kind: str = ""
    assumption: str = ""

    requires_human_visual_confirmation: ClassVar[bool] = True

    @property
    def pairs(self) -> tuple[tuple[MacroLine, MacroLine], ...]:
        """The on/off pairs, grouped by target rather than by position.

        Grouping by ``group_no`` (instead of slicing the line list two at a time)
        is what makes the pair count a real observation: a build that emitted two
        on lines for one group would raise here rather than report a tidy pair.
        """
        by_group: dict[int, dict[str, MacroLine]] = {}
        for line in self.lines:
            phases = by_group.setdefault(line.group_no, {})
            if line.phase in phases:
                raise ValueError(f"group {line.group_no} has two {line.phase} lines")
            phases[line.phase] = line
        pairs = []
        for group_no, phases in by_group.items():
            missing = {ON, OFF} - set(phases)
            if missing:
                raise ValueError(f"group {group_no} is missing its {sorted(missing)} line")
            pairs.append((phases[ON], phases[OFF]))
        return tuple(pairs)

    @property
    def pair_count(self) -> int:
        return len(self.pairs)

    def to_dict(self) -> dict[str, object]:
        """The ``macro`` key of the report payload (design.md §5.1).

        Exactly the six designed keys. No field asserts that a fixture answered
        (``REQ-PRECHK-014``); the acceptance flag is the only statement made about
        response, and it says a human still has to look.
        """
        return {
            "created": self.created,
            "target_kind": self.target_kind,
            "targets": [target.to_dict() for target in self.targets],
            "commands": list(self.commands),
            "requires_human_visual_confirmation": self.requires_human_visual_confirmation,
            "reason": self.reason,
        }

    def skipped_checks(self) -> tuple[dict[str, str], ...]:
        """The ``skipped_checks`` rows this axis contributes.

        ``assumption`` is empty when no assumption is at fault: a rig with no
        groups is a rig fact, and naming ``ASSUMPTION-26`` there would blame a
        measurement that came back GO.
        """
        if self.created:
            return ()
        return (
            {
                "kind": validate("skipped_check_kind", self.skipped_kind),
                "reason": self.reason,
                "assumption": self.assumption,
            },
        )


def _compose_reason(code: str, detail: str = "") -> str:
    label = reason_label(code)
    detail = detail.strip()
    return f"{label} — {detail}" if detail else label


def _not_created(
    code: str, *, skipped_kind: str, detail: str = "", assumption: str = ""
) -> MacroResult:
    return MacroResult(
        created=False,
        target_kind=TARGET_KIND_GROUP,
        reason=_compose_reason(code, detail),
        reason_code=code,
        skipped_kind=validate("skipped_check_kind", skipped_kind),
        assumption=assumption,
    )


def build_response_check_macro(groups: GroupPool, policy: MacroPolicy) -> MacroResult:
    """Build the response-check macro's commands for ``groups``.

    Returns a :class:`MacroResult` in every case — a rig with no groups and a
    negative ``ASSUMPTION-26`` are ANSWERS, not errors, and the M6 tool maps them
    to ``is_error=False`` (``AC-PRECHK-014`` ④). Nothing here invents a target:
    no new group is authored, and no blanket selection substitutes for a missing
    pool (``design.md`` slot D).
    """
    if not policy.authoring_available:
        return _not_created(
            AUTHORING_DESCOPED,
            skipped_kind=_SKIP_DESCOPE,
            detail=policy.descope_reason,
            assumption=ASSUMPTION_MACRO_AUTHORING,
        )

    if not groups.targets:
        if groups.unaddressable:
            return _not_created(
                GROUPS_UNADDRESSABLE,
                skipped_kind=_SKIP_NO_GROUPS,
                detail=", ".join(groups.unaddressable),
            )
        if groups.truncated:
            # "이 리그에 그룹이 없다" would be a claim about a pool we did not
            # finish reading. `acceptance.md` §D defines the fully-truncated
            # enumeration as an INCOMPLETE REPORT, never a negative finding.
            return _not_created(
                PARTIAL_GROUP_COVERAGE,
                skipped_kind=_SKIP_NO_GROUPS,
                detail="열거가 전부 절단되어 대상 그룹을 하나도 관측하지 못했다",
            )
        return _not_created(GROUP_POOL_EMPTY, skipped_kind=_SKIP_NO_GROUPS)

    slot = policy.macro_slot
    lines: list[MacroLine] = []
    commands: list[str] = [_check_transportable(f"Store Macro {slot}")]
    for target in groups.targets:
        for phase, payload in ((ON, _on_payload(target.no)), (OFF, _off_payload(target.no))):
            number = len(lines) + 1
            lines.append(MacroLine(number=number, group_no=target.no, phase=phase, payload=payload))
            # The measured order per line: create the line object, then set it.
            commands.append(_check_transportable(f"Store Macro {slot}.{number}"))
            commands.append(
                _check_transportable(f"Set Macro {slot}.{number} Property 'Command' '{payload}'")
            )

    reason = _compose_reason(VISUAL_CONFIRMATION_REQUIRED)
    if groups.truncated:
        reason = f"{reason} ({reason_label(PARTIAL_GROUP_COVERAGE)})"

    return MacroResult(
        created=True,
        target_kind=TARGET_KIND_GROUP,
        reason=reason,
        reason_code=VISUAL_CONFIRMATION_REQUIRED,
        targets=groups.targets,
        lines=tuple(lines),
        commands=tuple(commands),
        macro_slot=slot,
    )
