"""The four Phase 1 tools (REQ-MVP-005) built on the execution/state ports.

Tools never touch the OSC bridge — they depend on :mod:`server.orchestrator.ports`
only (REQ-MVP-029 forward design). ``deploy_plugin`` (M7) drives the deploy
pipeline — pcall compile harness + destructive scan + human review gate
(REQ-MVP-019); without a wired pipeline it stays a safe structured error and
never sends anything.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from server.llm.types import ToolCall, ToolDefinition, ToolResult
from server.looks.busking import build_genre_bundle, select_genre
from server.looks.instantiate import (
    CAPTURE_PER_FAMILY,
    CAPTURE_SHAPES,
    CAPTURE_SHARED,
    LookInstantiationError,
    build_instantiation,
    resolve_pools,
)
from server.looks.loader import LookSchemaError, load_library_from_dir
from server.looks.matching import match_looks
from server.looks.report import build_report, to_korean
from server.looks.resolver import resolve_roles
from server.looks.schema import LookLibrary
from server.looks.songcue import (
    EXPLICIT_DYNAMICS_REQUIRED,
    SectionTimeError,
    SequenceNumberError,
    SongCueBundleError,
    build_songcue_bundle,
    build_songcue_timing,
    map_sections_to_looks,
    parse_sections,
)
from server.looks.songcue_report import build_songcue_report
from server.orchestrator.ports import BundleGate, CommandExecutionPort, StateQueryPort

if TYPE_CHECKING:  # policy types only — no runtime import cycle
    from server.deploy.pipeline import DeployOutcome

# The dependency runs ONE way: this module reads the look layer, the look layer
# never reads this one. M3 kept the two rig-context failure reasons unenumerated
# in the resolver for exactly this reason — the reverse edge would close a cycle
# (tools -> matching -> resolver -> tools).
TOOL_NAMES = (
    "run_commands",
    "query_state",
    "deploy_plugin",
    "get_rig_context",
    "find_looks",
    "instantiate_look",
    "prepare_busking",
    "prepare_songcue",
)

# Object-tree paths for the rig-context summary (REQ-MVP-037). LIVE-CALIBRATED
# against grandMA3 onPC 2.4.2: the previous placeholders "Patch/Fixtures" and
# "DataPool/Presets" DO NOT EXIST on 2.4.2 (both reply "path segment not
# found"), so patch and preset vocabulary reached the model as an "unavailable"
# section on EVERY call and only groups ever got through. Override via
# build_toolset(rig_paths=...).
#
# What each path actually yields (read live, one tree level deep):
#   fixtures     - the stage's patched fixtures. An entry's "no" is its slot in
#                  that list; whether that slot equals the fixture id (FID) is
#                  NOT established by this snapshot, so it is never presented
#                  as an FID.
#   groups       - the group pool; here "no" IS the pool number you address
#                  (Group <no>).
#   preset_pools - the preset TYPES (Dimmer, Position, Gobo, Color, ...), i.e.
#                  ONE LEVEL ABOVE the individual stored presets. Those live
#                  INSIDE each pool ("DataPool/PresetPools/<no>") — opened by
#                  the drill-down below, because "a Color pool exists" and "a
#                  colour is stored in it" are different answers and only the
#                  second one tells you whether a recall will do anything.
#   sequences    - the cue lists a look is stored into.
#   pages        - executor pages; their CHILDREN are the executors, which are
#                  the only surface that actually fires a stored look.
#   macros /
#   plugins      - what already automates this show.
#   matricks /
#   worlds       - selection shaping and filtering vocabulary.
#
# Every path here was read back from a live onPC 2.4.2 on 2026-07-22 before
# being made a default. Guessed paths are how "Patch/Fixtures" and
# "DataPool/Presets" shipped dead for the whole of Stage 1.
#
# ASSUMPTION (stage slot, live-observed on ONE showfile): fixtures are read
# from stage slot 1. 2.4.2 creates "Stage 1" at slot 1 by default and the
# calibration showfile matches, but a show whose stage sits at another slot
# resolves nothing here. Stage auto-discovery is deliberately NOT implemented;
# the failure is made legible instead — get_rig_context reports such a section
# with reason "path_not_resolved" (a configuration defect) rather than the soft
# "unavailable" string that let the two dead paths above survive unnoticed.
# Point rig_paths= at the real stage to override.
DEFAULT_RIG_CONTEXT_PATHS = {
    "fixture_types": "Patch/FixtureTypes",
    "fixtures": "Patch/Stages/1/Fixtures",
    "groups": "DataPool/Groups",
    "sequences": "DataPool/Sequences",
    "preset_pools": "DataPool/PresetPools",
    "macros": "DataPool/Macros",
    "plugins": "DataPool/Plugins",
    "pages": "DataPool/Pages",
    "matricks": "DataPool/MAtricks",
    "worlds": "DataPool/Worlds",
}

# Sections whose children are CONTAINERS worth opening. A depth-1 snapshot of
# these answers "does it exist"; the show-readiness question is "is anything IN
# it", and that needs one query per child.
DEFAULT_RIG_DRILLDOWN = ("preset_pools", "pages")

# Ceiling on second-level queries per get_rig_context call. Each drill query is
# a UDP round trip through the gate + audit, so an unbounded walk would make rig
# context cost scale with the size of the showfile. When the ceiling stops the
# walk the section says so ("drilldown_capped") rather than presenting a partial
# walk as a complete one.
RIG_DRILLDOWN_QUERY_CAP = 16

# The two sections a look must be bound against: the groups its position roles
# resolve to, and the preset pools its values are stored into. Named rather
# than derived, so a rig_paths override that drops either one fails loudly
# instead of binding a look against half a rig.
# `SafetyGate._check_lock`가 LiveLock에서 발화하는 게이트 상태
# (`server/safety/gate.py:478`). per-command status "proposal"과 다른 층이다.
_LOCKED = "locked"

LOOK_RIG_SECTIONS = ("groups", "preset_pools")
SONGCUE_RIG_SECTIONS = ("groups", "sequences")

# The preset-pool drill is not optional on the look path. Occupancy is what
# makes "is this slot free" answerable at all; without it every store is
# skipped as unobserved — safe, and useless. get_rig_context's own drilldown
# configuration is left untouched.
_LOOK_DRILLDOWN = frozenset({"preset_pools"})


# Why a rig-context section is missing. The two causes are NOT interchangeable
# and used to be indistinguishable — both surfaced as one soft "unavailable"
# string, which is exactly how the two dead default paths above went unnoticed
# for the whole of Stage 1:
#   path_not_resolved   - a SIBLING section answered, so the console is
#                         demonstrably reachable and THIS path is wrong for
#                         this showfile: a configuration defect, fix the path.
#   console_unreachable - nothing answered, so no path can be blamed: an
#                         operational condition, retry when the console is up.
#
# Public because the show-control panel builds its catalog from the SAME two
# sections and must reach the same verdict (REQ-SHOWUI-002); two copies of this
# split would be two chances to merge them back into one soft "unavailable".
REASON_UNRESOLVED = "path_not_resolved"
REASON_UNREACHABLE = "console_unreachable"
_FAILURE_MESSAGES = {
    REASON_UNRESOLVED: (
        "this path does not exist in the loaded showfile — other sections "
        "answered, so the console IS reachable"
    ),
    REASON_UNREACHABLE: "no section answered — the console did not respond",
}


@dataclass(frozen=True)
class ExecutionContext:
    """Instruction-scoped dispatch context (self-correction dedupe state)."""

    executed_ok: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CommandOutcome:
    """Per-command execution status within one run_commands bundle.

    Execution statuses: "executed_ok" | "failed" | "not_executed" |
    "skipped_already_executed". Gate screening statuses (M4, when a bundle
    gate is wired): "blocked" | "rejected" | "proposal" | "held".
    """

    command: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class ToolExecution:
    """One dispatched tool call: the model-facing result + runner-facing outcomes."""

    result: ToolResult
    command_outcomes: tuple[CommandOutcome, ...] = ()


_Handler = Callable[[ToolCall, ExecutionContext], ToolExecution]

_EMPTY_CONTEXT = ExecutionContext()


# -- the dedupe exemption (M4 follow-up) ---------------------------------------
#
# Dedupe exists to prevent a duplicated DURABLE side effect. A command that
# establishes programmer state has no durable artifact to duplicate — it is
# idempotent in effect but POSITION-DEPENDENT in meaning. `ClearAll` appearing
# twice is not the same instruction twice; it is one instruction that must run
# at two different moments.
#
# The set is enumerated, not inferred, and deliberately small: the two
# programmer clears (00_grammar.md:57-58), and the BARE selection form of the
# two object types that select fixtures into the programmer. It is anchored on
# the command's LEADING token, because that is the discriminator between a bare
# selection and a command that creates or destroys something: `Store Group 7`,
# `Label Group 7 'Vocals'`, `Delete Group 3` and `Store Fixture 5` all carry a
# selection operand, and all leave an artifact behind (00_grammar.md "Frequently
# used functions"). A selection carrying a value is out too — `Group 3 Full` and
# `Fixture 1 Thru 10 At 80` set rather than merely select.
#
# `Clear` and `ClearAll` are SEPARATE patterns, matched independently under
# fullmatch, so neither can be caught by the other's pattern and no test for one
# can pass on the strength of the other.
#
# The operand grammar (`3`, `11 + 12`, `1 Thru 10`, `11 Thru`, `11 Thru 19 - 15`)
# is 00_grammar.md:17-22, where `Thru` / `+` / `-` are general object-reference
# operators — `Cue 3 Thru 7` is the rulebook's own non-Fixture example — so the
# two types share one operand pattern rather than being spelled out twice.
# Matching is case-insensitive because the console is (audit finding D14).
#
# NOT exempt, and not a style call: the `Select ...` prefix form. It is a
# command this project is forbidden to EMIT at all — `Select Fixture ...` and
# `SelFix ...` both returned "Illegal object" on live 2.4.2 and the rulebook
# directs the bare `Fixture ...` / `Group ...` forms instead
# (31_choreography_patterns.md:30-31; the measurement is on the Fixture forms,
# the bare-form directive covers Group). Exempting it from dedupe would
# pre-approve a command that can only ever fail. Secondary reason: admitting one
# benign leading verb costs the discriminator its "a leading verb means it
# creates or destroys something" simplicity.
#
# A wide selection is still the GATE's business, not this predicate's: an
# open-ended `Thru` is screened upstream (server/safety/classify.py) before any
# of this runs, so exempting one from dedupe never widens what may execute.
_SELECTION_OPERAND = r"\d+(?:\s*[-+]\s*\d+|\s+Thru(?:\s+\d+)?)*"
_PROGRAMMER_STATE_COMMANDS = (
    re.compile(r"Clear", re.IGNORECASE),  # step clear (selection -> values)
    re.compile(r"ClearAll", re.IGNORECASE),  # clear the whole programmer
    re.compile(rf"(?:Fixture|Group)\s+{_SELECTION_OPERAND}", re.IGNORECASE),  # bare selection
)


def _is_programmer_state(command: str) -> bool:
    """True for a command that establishes programmer state (exempt from dedupe)."""
    text = command.strip()
    return any(pattern.fullmatch(text) is not None for pattern in _PROGRAMMER_STATE_COMMANDS)


class DeployPipelinePort(Protocol):
    """The M7 deploy pipeline surface consumed by the deploy_plugin tool."""

    def deploy(self, name: str, lua_source: str) -> DeployOutcome: ...


# DeployOutcome.status -> per-command outcome status on the chat surface.
# "blocked" statuses count toward the self-correction retry cap; a human
# review rejection is NOT a technical failure (mirror of the M4 rule).
_DEPLOY_OUTCOME_STATUS = {
    "deployed": "executed_ok",
    "blocked_input": "blocked",
    "blocked_compile": "blocked",
    "blocked": "blocked",
    "review_rejected": "rejected",
    "deploy_failed": "failed",
}


# -- shared rig-shape helpers --------------------------------------------------
#
# ``rig_object`` / ``rig_section`` / ``drill_into`` are PURE (they touch only
# their arguments and the injected state port) and are public because a second
# reader of the same console shape now exists: the show-control panel's catalog
# builder (``server/web/panel.py``, SPEC-COPILOT-SHOWUI-001 REQ-SHOWUI-001).
# Sharing them rather than re-deriving the shape is what keeps ONE answer to the
# questions this snapshot is ambiguous about — the real-`no`-not-position rule,
# the truncation signal, and the unopened-vs-verified-empty distinction. Two
# copies would be two chances to answer one of them differently.


# @MX:NOTE: [AUTO] rig-context exposes the REAL pool number ('no'), not a bare
# positional index — stops the model mapping "the Nth item" onto "object N" and
# inventing a non-existent object on a non-contiguous rig (a hallucinated
# "Group 3" when groups live at pool 1, 2, 7). Live-demo finding #3,
# SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-029 / AC-DEPLOY-020.
def rig_object(child: dict) -> dict[str, object]:
    """One rig-context object: its REAL slot number (``no``) + ``name``.

    For a pool (groups, preset pools) that slot IS the pool number the console
    addresses (``Group <no>``); for a container that is not a pool (the stage's
    fixture list) it is the position the responder established within that
    container, which the tool description explicitly declines to present as a
    fixture id. Either way it is a number the responder READ, never one this
    code counted.

    The responder emits ``{"i": <pool-slot>, "name": ..., "class": ...}`` but
    ONLY when it positively established that slot; a child whose slot it could
    not establish arrives WITHOUT ``i`` (``console/lua/copilot_responder.lua``
    build_snapshot / safe_children, PROTOCOL.md §4.2 — the responder never
    substitutes the listing position, and ``server/safety/console.py`` relies
    on the same guarantee for its slot arithmetic).

    That absence is meaningful, not a glitch: it degrades to a name-only entry
    so the model has no number to address — it must resolve the real one (e.g.
    via ``query_state``) instead of counting list positions.
    """
    number = child.get("i")
    name = child.get("name", "")
    if number is None:
        return {"name": name}
    return {"no": number, "name": name}


def rig_section(objects: list[dict[str, object]], payload: dict) -> dict[str, object]:
    """Wrap a resolved section with what the responder said about its OWN
    completeness (PROTOCOL.md §4 ``truncated`` / ``node.childCount``).

    A short list with no completeness signal is worse than no list at all: the
    model would reason, confidently, over a rig it could not fully see. Absence
    of a real ``childCount`` reads as an unknown total, never as "the count
    equals what arrived".
    """
    node = payload.get("node")
    child_count = node.get("childCount") if isinstance(node, dict) else None
    return {
        "objects": objects,
        "truncated": bool(payload.get("truncated", False)),
        "total": child_count if isinstance(child_count, int) else None,
    }


def drill_into(
    state_port: StateQueryPort,
    objects: list[dict[str, object]],
    base_path: str,
    entry: dict[str, object],
    budget: int,
) -> int:
    """Open each object in ``objects`` as a container, IN PLACE, spending at
    most ``budget`` queries total (shared across every drilled section in one
    get_rig_context call).

    Distinguishes a verified-EMPTY container (``contents: []``) from one the
    drill could not reach (``contents_unavailable: True``) — collapsing the two
    would make a console that failed mid-walk look identical to a show with
    nothing configured, which is exactly the ambiguity a readiness check exists
    to remove.

    When the budget runs out before every object is opened, the section is
    marked ``drilldown_capped`` rather than silently presenting a partial walk
    as a complete one — each query is a UDP round trip through the gate +
    audit, so an unbounded walk would make rig-context cost scale with the
    size of the showfile.
    """
    capped = False
    for obj in objects:
        number = obj.get("no")
        if number is None:
            continue  # no real address to drill into (degraded name-only entry)
        if budget <= 0:
            capped = True
            break
        budget -= 1
        try:
            child_payload = state_port.query_state(f"{base_path}/{number}")
        except Exception:
            obj["contents_unavailable"] = True
            continue
        children = child_payload.get("children", [])
        obj["contents"] = [rig_object(c) for c in children if isinstance(c, dict)]
    if capped:
        entry["drilldown_capped"] = True
    return budget


def collect_rig_sections(
    state_port: StateQueryPort,
    paths: Mapping[str, str],
    drilldown: frozenset[str],
    budget: int,
) -> tuple[dict[str, object], int, int]:
    """Read each named section, drilling the ones in ``drilldown``.

    Returns ``(summary, resolved, failed)``. A failed section is replaced by the
    ``{"reason": ...}`` shape, classified by the SAME rule for every caller: a
    sibling section answering means this path is wrong for this showfile
    (``path_not_resolved``), nothing answering means no path can be blamed
    (``console_unreachable``).

    Shared rather than re-derived because a second caller of the same shape now
    exists (``instantiate_look``), and two copies of that classification would
    be two chances to collapse it back into one soft "unavailable" — the exact
    regression the two dead default paths hid behind for the whole of Stage 1.
    The sample size differs (ten sections vs two) and the rule does not: with
    one sibling answering, "the console is up and this path is wrong" is the
    same inference it is with nine.
    """
    summary: dict[str, object] = {}
    failures: dict[str, tuple[str, str]] = {}
    resolved = 0
    for section, path in paths.items():
        try:
            payload = state_port.query_state(path)
        except Exception as exc:
            # Placeholder keeps the section's position; classified below, once
            # every section's outcome is known.
            summary[section] = None
            failures[section] = (path, str(exc))
            continue
        # A resolved path proves the console ANSWERED — even with zero children
        # (a real shape: an empty preset pool).
        resolved += 1
        children = payload.get("children", [])
        objects = [rig_object(child) for child in children if isinstance(child, dict)]
        entry = rig_section(objects, payload)
        if section in drilldown:
            budget = drill_into(state_port, objects, path, entry, budget)
        summary[section] = entry
    reason = REASON_UNRESOLVED if resolved else REASON_UNREACHABLE
    for section, (path, detail) in failures.items():
        summary[section] = {
            "reason": reason,
            "path": path,
            "error": f"{_FAILURE_MESSAGES[reason]}: {detail}",
        }
    return summary, resolved, len(failures)


def _error_result(call: ToolCall, message: str) -> ToolExecution:
    return ToolExecution(
        result=ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"error": message}, ensure_ascii=False),
            is_error=True,
        )
    )


class ToolRegistry:
    """The closed set of Phase 1 tools with neutral definitions + dispatch."""

    def __init__(self, definitions: tuple[ToolDefinition, ...], handlers: dict[str, _Handler]):
        self._definitions = definitions
        self._handlers = handlers

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return self._definitions

    def dispatch(self, call: ToolCall, context: ExecutionContext | None = None) -> ToolExecution:
        context = context if context is not None else _EMPTY_CONTEXT
        handler = self._handlers.get(call.name)
        if handler is None:
            return _error_result(call, f"unknown tool: {call.name!r}")
        return handler(call, context)


def build_toolset(
    *,
    execution_port: CommandExecutionPort,
    state_port: StateQueryPort,
    rig_paths: dict[str, str] | None = None,
    rig_drilldown: tuple[str, ...] | None = None,
    bundle_gate: BundleGate | None = None,
    deploy_pipeline: DeployPipelinePort | None = None,
    look_library: LookLibrary | None = None,
) -> ToolRegistry:
    """Build the tool registry wired to the given ports (REQ-MVP-005).

    When ``bundle_gate`` is provided (M4 production wiring), every
    run_commands bundle is screened as a WHOLE before any per-command
    execution starts (REQ-MVP-011 pipeline + REQ-MVP-015 all-or-nothing);
    a non-cleared decision returns the block/hold reasons as an error tool
    result, feeding the self-correction loop (REQ-MVP-012).

    ``look_library`` is optional: production wiring passes nothing and the
    built-in library is read from disk on the first ``find_looks`` call, so a
    toolset that never looks up a look pays no file read.
    """
    rig_paths = dict(rig_paths or DEFAULT_RIG_CONTEXT_PATHS)
    drilldown = frozenset(rig_drilldown if rig_drilldown is not None else DEFAULT_RIG_DRILLDOWN)
    looks = look_library

    # -- run_commands (REQ-MVP-001 upstream, REQ-MVP-009/033 semantics) --------

    def run_commands(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        commands = call.arguments.get("commands")
        if (
            not isinstance(commands, list)
            or not commands
            or not all(isinstance(c, str) and c.strip() for c in commands)
        ):
            return _error_result(call, "'commands' must be a non-empty list of command lines")
        if bundle_gate is not None:
            decision = bundle_gate.screen(commands)
            if not decision.cleared:
                gate_outcomes = tuple(
                    CommandOutcome(command=d.command, status=d.status, detail="; ".join(d.reasons))
                    for d in decision.commands
                )
                content = json.dumps(
                    {
                        "all_ok": False,
                        "gate_status": decision.status,
                        "notice": decision.notice,
                        "commands": [
                            {
                                "command": d.command,
                                "status": d.status,
                                "reasons": list(d.reasons),
                            }
                            for d in decision.commands
                        ],
                    },
                    ensure_ascii=False,
                )
                return ToolExecution(
                    result=ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=content,
                        is_error=True,
                    ),
                    command_outcomes=gate_outcomes,
                )
        outcomes: list[CommandOutcome] = []
        failed = False
        # MEDIUM backlog item (M6c 종합, tools.py:145): ``context.executed_ok``
        # is a frozenset seeded from a PRIOR tool call — it is never updated
        # as commands succeed WITHIN this loop. A local, mutable copy (seeded
        # from the same starting set) tracks successes as they happen in THIS
        # call, so an in-bundle duplicate command (the same string appearing
        # twice in one ``commands`` list) is correctly recognized as
        # already-executed on its second occurrence instead of being
        # re-executed and duplicating its console side effect.
        already_executed = set(context.executed_ok)
        for command in commands:
            if failed:
                # Stop-on-first-failure: remaining commands are never executed.
                outcomes.append(
                    CommandOutcome(
                        command=command,
                        status="not_executed",
                        detail="not executed (stopped after an earlier failure)",
                    )
                )
            elif command in already_executed and not _is_programmer_state(command):
                # Never re-execute a command that already succeeded — either
                # in a prior tool call (context.executed_ok) or earlier in
                # THIS bundle — re-execution duplicates its console effect.
                # Programmer-state commands are exempt: they duplicate no
                # artifact, and their repeats are MOMENTS, not repetitions
                # (_is_programmer_state above).
                outcomes.append(
                    CommandOutcome(
                        command=command,
                        status="skipped_already_executed",
                        detail="already executed successfully in this instruction",
                    )
                )
            else:
                result = execution_port.execute(command)
                if result.ok:
                    already_executed.add(command)
                    outcomes.append(
                        CommandOutcome(command=command, status="executed_ok", detail=result.detail)
                    )
                else:
                    outcomes.append(
                        CommandOutcome(command=command, status="failed", detail=result.detail)
                    )
                    failed = True
        content = json.dumps(
            {
                "all_ok": not failed,
                "commands": [
                    {"command": o.command, "status": o.status, "detail": o.detail} for o in outcomes
                ],
            },
            ensure_ascii=False,
        )
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id, name=call.name, content=content, is_error=failed
            ),
            command_outcomes=tuple(outcomes),
        )

    # -- query_state (REQ-MVP-003 via the M2 protocol path) --------------------

    def query_state(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        path = call.arguments.get("path")
        if not isinstance(path, str) or not path.strip():
            return _error_result(call, "'path' must be a non-empty object-tree path")
        try:
            payload = state_port.query_state(path)
        except Exception as exc:
            return _error_result(call, f"state query failed for {path!r}: {exc}")
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
            )
        )

    # -- deploy_plugin (M7 — REQ-MVP-019 pipeline: compile + scan + review) ------

    def deploy_plugin(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        if deploy_pipeline is None:
            # Unwired session: deployment stays unavailable BY DESIGN and
            # never sends anything toward the console (deny-by-default).
            return _error_result(
                call,
                "deploy_plugin is not wired in this session: plugin deployment "
                "requires the pcall compile check and the human review gate",
            )
        name = call.arguments.get("name")
        lua_source = call.arguments.get("lua_source")
        if not isinstance(name, str) or not name.strip():
            return _error_result(call, "'name' must be a non-empty plugin name string")
        if not isinstance(lua_source, str) or not lua_source.strip():
            return _error_result(call, "'lua_source' must be non-empty Lua 5.4 source code")
        outcome = deploy_pipeline.deploy(name, lua_source)
        status = _DEPLOY_OUTCOME_STATUS.get(outcome.status, "failed")
        command_label = f'deploy_plugin "{name}"'
        deployed = outcome.status == "deployed"
        content: dict[str, object] = {
            "deployed": deployed,
            "plugin": name,
            "status": outcome.status,
            "destructive": outcome.destructive,
            "detail": outcome.detail,
        }
        if not deployed:
            content["error"] = outcome.detail
        if outcome.compile_error:
            content["compile_error"] = outcome.compile_error
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(content, ensure_ascii=False),
                is_error=not deployed,
            ),
            command_outcomes=(
                CommandOutcome(command=command_label, status=status, detail=outcome.detail),
            ),
        )

    # -- get_rig_context (REQ-MVP-037 — showfile-based basic summary) -----------

    def get_rig_context(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        summary, resolved, failed = collect_rig_sections(
            state_port, rig_paths, drilldown, RIG_DRILLDOWN_QUERY_CAP
        )
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(summary, ensure_ascii=False),
                # Partial vocabulary is still usable; returning NOTHING is a
                # failed call, not a quiet success.
                is_error=bool(failed) and resolved == 0,
            )
        )

    # -- find_looks (REQ-LOOKLIB-015/016/017 — lookup only, sends nothing) -----

    def find_looks(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        query = call.arguments.get("query")
        if not isinstance(query, str):
            return _error_result(call, "'query' must be a string — the operator's own words")
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                # A broken library is a structured failure, never a silent
                # empty result that would read as "no look matches".
                return _error_result(call, f"look library unavailable: {error}")
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(match_looks(query, looks).to_dict(), ensure_ascii=False),
                # A miss is an ANSWER (REQ-LOOKLIB-017), not a tool failure:
                # an is_error payload feeds the self-correction loop and would
                # invite a retry that can only miss again.
                is_error=False,
            )
        )

    # -- instantiate_look (REQ-LOOKLIB-010/013/019 — the look layer's ONE route) -
    #
    # @MX:ANCHOR: [AUTO] the only model-reachable entry to the instantiation
    #   chain (find_looks -> role resolution -> bundle -> gate.screen()).
    # @MX:REASON: REQ-LOOKLIB-010/019. This handler is a CALLER of run_commands,
    #   never a second execution surface: it re-enters the local run_commands
    #   closure above, so the bundle inherits that path's gate screening,
    #   execution preview, dedupe and audit log without any of them being
    #   duplicated for looks. Reaching execution_port directly from here would
    #   be the second path the SPEC forbids, and it would be invisible to the
    #   gate. The M4 layer was correct and had NO caller for exactly one
    #   milestone; that is what this tool repairs, so do not un-register it
    #   without giving the chain another model-reachable door.

    def instantiate_look(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        look_id = call.arguments.get("look_id")
        if not isinstance(look_id, str) or not look_id.strip():
            return _error_result(
                call, "'look_id' must be the look_id string returned by find_looks"
            )
        shape = call.arguments.get("capture_shape", CAPTURE_SHARED)
        if shape not in CAPTURE_SHAPES:
            # Never silently corrected to the default: a shape the model chose
            # deliberately and got wrong is worth one visible failure.
            return _error_result(
                call, f"'capture_shape' must be one of {list(CAPTURE_SHAPES)}, not {shape!r}"
            )
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                return _error_result(call, f"look library unavailable: {error}")
        try:
            look = looks.by_id(look_id.strip())
        except KeyError:
            # An id this library does not hold is a correctable mistake, so it
            # IS an error result — unlike a find_looks miss, a retry with the
            # right id succeeds.
            return _error_result(
                call,
                f"unknown look_id {look_id!r} — call find_looks and pass back the "
                f"look_id from one of its matches",
            )
        missing = [section for section in LOOK_RIG_SECTIONS if section not in rig_paths]
        if missing:
            return _error_result(
                call,
                f"rig context has no path configured for {missing} — a look cannot be "
                f"bound to this rig without them",
            )
        # The rig is READ here, never accepted as an argument: a model retyping
        # a rig section can paraphrase a name, drop the truncation signal or
        # supply a number the console never gave. Every number this bundle puts
        # on the command line has to come from the console itself (AP-16).
        sections, _resolved, _failed = collect_rig_sections(
            state_port,
            {section: rig_paths[section] for section in LOOK_RIG_SECTIONS},
            drilldown | _LOOK_DRILLDOWN,
            RIG_DRILLDOWN_QUERY_CAP,
        )
        unavailable = {
            name: entry
            for name, entry in sections.items()
            if isinstance(entry, dict) and "reason" in entry
        }
        if unavailable:
            # A section that never arrived is NOT a rig that answered "no such
            # group". Reporting the roles as unmapped here would state a fact
            # about a rig nobody observed.
            content = json.dumps(
                {
                    "error": (
                        "the rig sections a look is bound against did not arrive: "
                        + "; ".join(f"{n}: {e['reason']}" for n, e in unavailable.items())
                    ),
                    "rig_unavailable": unavailable,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            plan = build_instantiation(
                look,
                resolution=resolve_roles(sections["groups"]),  # type: ignore[arg-type]
                pools=resolve_pools(sections["preset_pools"]),  # type: ignore[arg-type]
                shape=shape,
            )
        except LookInstantiationError as error:
            return _error_result(call, f"look {look.look_id!r} cannot be instantiated: {error}")
        report = plan.to_dict()
        if not plan.commands:
            # The rig addressed none of this look's roles. An empty bundle is
            # the honest output, and it is an ANSWER rather than a failure: a
            # retry cannot bind a role this rig does not have.
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps({"executed": False, "report": report}, ensure_ascii=False),
                    is_error=False,
                )
            )
        execution = run_commands(
            ToolCall(id=call.id, name="run_commands", arguments={"commands": list(plan.commands)}),
            context,
        )
        payload = json.loads(execution.result.content)
        payload["executed"] = not execution.result.is_error
        payload["report"] = report
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=execution.result.is_error,
            ),
            command_outcomes=execution.command_outcomes,
        )

    # -- prepare_busking (REQ-BUSKWIZ-011/012/014/019/020 — 장르 팔레트 1왕복) ---
    #
    # @MX:ANCHOR: [AUTO] the busking wizard's ONE model-reachable entry.
    # @MX:REASON: REQ-BUSKWIZ-011/012. Like instantiate_look this handler is a
    #   CALLER of run_commands, never a second execution surface: the genre
    #   bundle inherits gate screening, LiveLock, dedupe and the audit log from
    #   that one path. Reaching execution_port from here would be invisible to
    #   the gate. The rig is READ here for the same reason instantiate_look
    #   reads it (:735-738) — a model retyping a section can paraphrase a name
    #   or supply a number the console never gave.

    def prepare_busking(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        genre = call.arguments.get("genre")
        if not isinstance(genre, str) or not genre.strip():
            return _error_result(
                call, "'genre' must be the operator's own word for the genre (e.g. '록', 'EDM')"
            )
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                return _error_result(call, f"look library unavailable: {error}")
        selection = select_genre(looks, genre)
        if selection.genre is None:
            # A genre this library does not hold is a CORRECTABLE mistake: the
            # candidate list makes the retry succeed. Promoting the query to the
            # nearest genre instead would leave a palette the operator never
            # asked for in their showfile.
            content = json.dumps(
                {
                    "error": f"unknown genre {genre!r}",
                    "reason": selection.reason,
                    "candidates": list(selection.candidates),
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        missing = [section for section in LOOK_RIG_SECTIONS if section not in rig_paths]
        if missing:
            return _error_result(
                call,
                f"rig context has no path configured for {missing} — a busking palette "
                f"cannot be built without them",
            )
        sections, _resolved, _failed = collect_rig_sections(
            state_port,
            {section: rig_paths[section] for section in LOOK_RIG_SECTIONS},
            drilldown | _LOOK_DRILLDOWN,
            RIG_DRILLDOWN_QUERY_CAP,
        )
        unavailable = {
            name: entry
            for name, entry in sections.items()
            if isinstance(entry, dict) and "reason" in entry
        }
        if unavailable:
            # A section that never arrived is NOT a rig that answered "no such
            # group" — the same split instantiate_look makes at :750.
            content = json.dumps(
                {
                    "error": (
                        "the rig sections a busking palette is built against did not "
                        "arrive: "
                        + "; ".join(f"{n}: {e['reason']}" for n, e in unavailable.items())
                    ),
                    "rig_unavailable": unavailable,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            bundle = build_genre_bundle(
                selection.genre,
                selection.looks,
                resolution=resolve_roles(sections["groups"]),  # type: ignore[arg-type]
                pools=resolve_pools(sections["preset_pools"]),  # type: ignore[arg-type]
            )
        except LookInstantiationError as error:
            return _error_result(call, f"genre {selection.genre!r} cannot be instantiated: {error}")
        if not bundle.commands:
            # The rig addressed none of this genre's roles. Storing nothing is
            # an ANSWER, not a failure: a retry cannot bind roles this rig does
            # not have. The report still says which look died and why.
            report = build_report(bundle)
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        {
                            "executed": False,
                            "genre": bundle.genre,
                            "report": report.to_dict(),
                            "summary_ko": to_korean(report),
                        },
                        ensure_ascii=False,
                    ),
                    is_error=False,
                )
            )
        execution = run_commands(
            ToolCall(
                id=call.id, name="run_commands", arguments={"commands": list(bundle.commands)}
            ),
            context,
        )
        payload = json.loads(execution.result.content)
        is_error = execution.result.is_error
        if payload.get("gate_status") == _LOCKED:
            # LiveLock demotion is an ANSWER (REQ-BUSKWIZ-014): the proposal IS
            # the deliverable. is_error=True would feed the self-correction loop
            # and send the model back into the same lock.
            is_error = False
        report = build_report(bundle, execution.command_outcomes)
        payload["executed"] = not execution.result.is_error
        payload["genre"] = bundle.genre
        payload["report"] = report.to_dict()
        payload["summary_ko"] = to_korean(report)
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=is_error,
            ),
            command_outcomes=execution.command_outcomes,
        )

    # -- prepare_songcue (REQ-SONGCUE-018/019 — song sections to one cue list) -
    #
    # @MX:ANCHOR: [AUTO] the song-cue generator's ONE model-reachable entry.
    # @MX:REASON: REQ-SONGCUE-018/019. Like prepare_busking this handler is a
    #   CALLER of run_commands, never a second execution surface: it reads the
    #   rig itself, builds the sequence/cue/timing bundle, and re-enters the
    #   local run_commands closure so gate.screen(), LiveLock demotion, dedupe
    #   and audit stay owned by the same path.

    def prepare_songcue(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        song_title = call.arguments.get("song_title")
        if not isinstance(song_title, str) or not song_title.strip():
            return _error_result(call, "'song_title' must be a non-empty song title string")
        genre = call.arguments.get("genre")
        if not isinstance(genre, str) or not genre.strip():
            return _error_result(call, "'genre' must be the operator's own word for the genre")
        timecode_number = call.arguments.get("timecode_number")
        if isinstance(timecode_number, bool) or not isinstance(timecode_number, int) or timecode_number < 1:
            return _error_result(call, "'timecode_number' must be a positive integer")
        raw_sections = call.arguments.get("sections")
        if not isinstance(raw_sections, list | tuple) or not raw_sections:
            return _error_result(call, "'sections' must be a non-empty array of song sections")
        raw_explicit = call.arguments.get("explicit_dynamics")
        explicit_dynamics: dict[int, int] | None = None
        if raw_explicit is not None:
            if not isinstance(raw_explicit, Mapping):
                return _error_result(
                    call,
                    "'explicit_dynamics' must map zero-based section indexes to dynamics 1..5",
                )
            explicit_dynamics = {}
            for key, value in raw_explicit.items():
                if isinstance(value, bool) or not isinstance(value, int):
                    return _error_result(call, "'explicit_dynamics' values must be integers")
                try:
                    explicit_dynamics[int(key)] = value
                except (TypeError, ValueError):
                    return _error_result(
                        call, "'explicit_dynamics' keys must be zero-based section indexes"
                    )
        try:
            sections = parse_sections(raw_sections)
        except SectionTimeError as error:
            content = json.dumps(
                {
                    "error": "song sections are not strictly increasing",
                    "reason": error.reason,
                    "index": error.index,
                    "previous_start_ms": error.previous_start_ms,
                    "start_ms": error.start_ms,
                    "sections": [
                        {"index": section.index, "name": section.name, "start_ms": section.start_ms}
                        for section in error.sections
                    ],
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        except ValueError as error:
            return _error_result(call, f"song sections cannot be parsed: {error}")
        for index, raw_section in enumerate(raw_sections):
            if not isinstance(raw_section, Mapping) or "dynamics" not in raw_section:
                continue
            value = raw_section["dynamics"]
            if isinstance(value, bool) or not isinstance(value, int):
                return _error_result(call, "'sections[].dynamics' values must be integers")
            if explicit_dynamics is None:
                explicit_dynamics = {}
            explicit_dynamics[index] = value
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                return _error_result(call, f"look library unavailable: {error}")
        genre_selection = select_genre(looks, genre)
        if genre_selection.genre is None:
            content = json.dumps(
                {
                    "error": f"unknown genre {genre!r}",
                    "reason": genre_selection.reason,
                    "candidates": list(genre_selection.candidates),
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            selections = map_sections_to_looks(
                sections,
                looks,
                genre_selection.genre,
                explicit_dynamics=explicit_dynamics,
            )
        except ValueError as error:
            return _error_result(call, f"song sections cannot be mapped: {error}")
        unknown_sections = [
            {"index": selection.section.index, "name": selection.section.name}
            for selection in selections
            if selection.reason == EXPLICIT_DYNAMICS_REQUIRED
        ]
        if unknown_sections:
            content = json.dumps(
                {
                    "error": "unknown section names need explicit dynamics",
                    "reason": EXPLICIT_DYNAMICS_REQUIRED,
                    "unknown_sections": unknown_sections,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        missing = [section for section in SONGCUE_RIG_SECTIONS if section not in rig_paths]
        if missing:
            return _error_result(
                call,
                f"rig context has no path configured for {missing} — a song cue list "
                f"cannot be built without them",
            )
        rig_sections, _resolved, _failed = collect_rig_sections(
            state_port,
            {section: rig_paths[section] for section in SONGCUE_RIG_SECTIONS},
            drilldown,
            RIG_DRILLDOWN_QUERY_CAP,
        )
        unavailable = {
            name: entry
            for name, entry in rig_sections.items()
            if isinstance(entry, dict) and "reason" in entry
        }
        if unavailable:
            content = json.dumps(
                {
                    "error": (
                        "the rig sections a song cue list is built against did not "
                        "arrive: "
                        + "; ".join(f"{n}: {e['reason']}" for n, e in unavailable.items())
                    ),
                    "rig_unavailable": unavailable,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            bundle = build_songcue_bundle(
                song_title,
                selections,
                sequences_section=rig_sections["sequences"],  # type: ignore[arg-type]
                groups_section=rig_sections["groups"],  # type: ignore[arg-type]
            )
            timing = build_songcue_timing(bundle, timecode_number=timecode_number)
        except (SequenceNumberError, SongCueBundleError, ValueError) as error:
            return _error_result(call, f"song cue list cannot be built: {error}")
        if not bundle.commands:
            report = build_songcue_report(bundle)
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        {
                            "executed": False,
                            "song_title": bundle.song_title,
                            "sequence": bundle.sequence_number,
                            "report": report.to_dict(),
                            "summary_ko": report.to_korean(),
                            "timing": {
                                "commands": [],
                                "timecode_commands": [],
                                "auto_advance_commands": [],
                                "skipped_axes": [],
                            },
                        },
                        ensure_ascii=False,
                    ),
                    is_error=False,
                )
            )
        command_bundle = bundle.commands + timing.commands
        execution = run_commands(
            ToolCall(id=call.id, name="run_commands", arguments={"commands": list(command_bundle)}),
            context,
        )
        payload = json.loads(execution.result.content)
        is_error = execution.result.is_error
        if payload.get("gate_status") == _LOCKED:
            is_error = False
        requery_payload = None
        if not execution.result.is_error:
            try:
                requery_payload = state_port.query_state(
                    f"{rig_paths['sequences']}/{bundle.sequence_number}"
                )
            except Exception as error:
                payload["requery_error"] = str(error)
        report = build_songcue_report(bundle, execution.command_outcomes, requery_payload=requery_payload)
        payload["executed"] = not execution.result.is_error
        payload["song_title"] = bundle.song_title
        payload["sequence"] = bundle.sequence_number
        payload["report"] = report.to_dict()
        payload["summary_ko"] = report.to_korean()
        payload["timing"] = {
            "commands": list(timing.commands),
            "timecode_commands": list(timing.timecode_commands),
            "auto_advance_commands": list(timing.auto_advance_commands),
            "skipped_axes": [
                {"axis": skipped.axis, "reason": skipped.reason}
                for skipped in timing.skipped_axes
            ],
        }
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=is_error,
            ),
            command_outcomes=execution.command_outcomes,
        )

    definitions = (
        ToolDefinition(
            name="run_commands",
            description=(
                "Execute MA3 command lines on the console, in order. Call this to "
                "carry out the user's instruction once you know the exact commands. "
                "Execution stops at the first failing command; the result reports "
                "each command's status (executed_ok / failed / not_executed / "
                "skipped_already_executed)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "MA3 command lines, one command per entry.",
                    }
                },
                "required": ["commands"],
            },
        ),
        ToolDefinition(
            name="query_state",
            description=(
                "Read a console object-tree snapshot (e.g. 'DataPool/Sequences'). "
                "Call this when you need current console state before deciding on "
                "commands."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Object-tree path, e.g. 'DataPool/Sequences'.",
                    }
                },
                "required": ["path"],
            },
        ),
        ToolDefinition(
            name="deploy_plugin",
            description=(
                "Deploy a Lua 5.4 plugin to the console. The source is compile-"
                "checked (a compile error comes back for correction), scanned "
                "for destructive Cmd() content, and shown to a human reviewer "
                "who must approve the deployment before anything reaches the "
                "console. A rejection is a final human decision — do not retry."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plugin name."},
                    "lua_source": {"type": "string", "description": "Lua 5.4 source code."},
                },
                "required": ["name", "lua_source"],
            },
        ),
        ToolDefinition(
            name="get_rig_context",
            description=(
                "Build a picture of THIS showfile — call this FIRST, before "
                "designing any look, and whenever the instruction uses venue/"
                "field terms (e.g. Korean field vocabulary) that must resolve "
                "to actual objects. One call covers everything a lighting "
                'instruction is made of: "fixture_types" (patched fixture '
                'types), "fixtures" (the stage\'s patched fixtures), "groups" '
                '(the group pool — what to select), "sequences" (stored cue '
                'lists — what a look is stored INTO), "preset_pools" (the '
                "preset TYPES — Dimmer, Position, Gobo, Color, ... — with each "
                'pool\'s STORED CONTENTS opened inline, see "contents" below), '
                '"macros" and "plugins" (what already automates this show), '
                '"pages" (executor pages — the ONLY surface that actually '
                'FIRES a stored look: each page\'s "objects" already lists its '
                'executors, e.g. Sequence 30 sitting on Executor 5), "matricks" '
                'and "worlds" (selection-shaping vocabulary).\n'
                "\n"
                'Each section is {"objects": [...], "truncated": bool, "total": '
                "<real count, or null if unknown>}. truncated=true means the "
                "responder cut the list short — total names the REAL count, so "
                "you know the objects you have are NOT everything; never treat "
                "a truncated list as complete.\n"
                "\n"
                'Each object is {"no": <number>, "name": <name>}; ALWAYS '
                'reference it by its REAL "no", NEVER by positional order — '
                "numbers may be non-contiguous (e.g. 1, 2, 7), so the Nth "
                "listed item is NOT necessarily object N. An entry with a "
                '"name" but NO "no" means its number is UNKNOWN: do not guess '
                "one — resolve it with query_state before addressing that "
                "object. For groups, sequences, macros, plugins and pages the "
                '"no" IS the address you use (e.g. Group 2, Sequence 5). For '
                'fixtures the "no" is the fixture\'s slot in the stage patch '
                "list and is NOT guaranteed to be its fixture id (FID) — "
                "confirm the FID with query_state before addressing a fixture "
                "by number.\n"
                "\n"
                'In "preset_pools" and "pages", each object additionally '
                'carries "contents": the pool\'s stored presets, or the '
                "page's executors, already fetched — an empty list means "
                "VERIFIED empty (nothing stored yet), not unknown. "
                '"contents_unavailable": true means that ONE object could not '
                "be opened (console busy or the object vanished) — its "
                "contents are genuinely unknown, distinct from a verified-"
                'empty pool. A section may also carry "drilldown_capped": '
                "true, meaning there were more objects than this call's "
                "per-request query budget allowed opening — the rest still "
                'have "no"/"name" but no "contents"; call query_state on '
                "those specific paths if you need them.\n"
                "\n"
                'A section may instead come back as {"reason": ...}: '
                '"path_not_resolved" means that vocabulary does not exist in '
                'THIS showfile (other sections answered), "console_unreachable" '
                "means nothing answered. In both cases you did NOT receive "
                "that vocabulary — say so and ask, never invent objects for it."
            ),
            parameters={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="find_looks",
            description=(
                "Ask the built-in look library BEFORE inventing any colour or "
                "intensity — call this the moment an instruction names a mood, "
                "a genre or a song section rather than explicit values (e.g. "
                "'a grand golden chorus', 'a calm ballad intro', 'the EDM "
                "drop'). A stored look is a DESIGNED answer; the values you "
                "would otherwise pick are a guess at the same question, so "
                "designing a mood from scratch without asking here first is "
                "the one thing this tool exists to prevent.\n"
                "\n"
                "This is the VALUES half of a mood instruction and "
                "get_rig_context is the OBJECTS half — they do not compete, "
                "and a mood instruction needs BOTH: ask here for the look, "
                "then bind it to the real rig. Pass the operator's own words; "
                "Korean is first-class, and the genre may be written either "
                "way (워십 / worship, 록 / rock, 발라드 / ballad, EDM).\n"
                "\n"
                "This tool READS ONLY — it never sends anything to the "
                'console. Each match is {"look_id", "display_name", "genre", '
                '"dynamics" (1 static .. 5 climax), "roles" (position roles, '
                'NOT rig objects), "attributes" (concrete values), "score" and '
                '"matched" (the library words your query hit)}. The list is '
                'ranked; "total" and "truncated" say whether it was cut '
                "short.\n"
                "\n"
                'When "fallback" is true NOTHING matched well enough — '
                '"no_match" (nothing answered), "low_confidence" (several '
                'looks tied and nothing narrows them) or "empty_query". In '
                "that case do NOT pick from the list: fall back to designing "
                "the mood yourself from the rulebook's mood table. The library "
                "never invents a look, and neither should you.\n"
                "\n"
                "A look carries NO group number, preset slot or fixture id. To "
                "put one on THIS rig, resolve its roles against "
                "get_rig_context and store it with run_commands."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The mood / genre / section wording to match, in "
                            "the operator's own language."
                        ),
                    }
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="instantiate_look",
            description=(
                "Put a look FROM find_looks onto THIS rig. Pass the look_id of "
                "the match you chose; do NOT hand-write the bundle with "
                "run_commands, because this tool is the only thing that binds "
                "a look's position roles to the rig's real groups.\n"
                "\n"
                "It reads the rig itself — the current groups and preset pools "
                "— so you do not pass any rig data in, and you must not retype "
                "anything from get_rig_context: every group and pool number it "
                "puts on the command line comes from the console on THIS call. "
                "It then stores ONE preset per in-scope pool (Dimmer, Color, "
                "and Beam / Focus when the look has those values), labels each "
                "one with the look's name, and runs the whole bundle through "
                "the SAME execution path as run_commands — so the live lock, "
                "the safety screening and the approval gate all apply "
                "unchanged.\n"
                "\n"
                "It creates PRESETS ONLY. It does not create a cue, a sequence "
                "or an executor assignment, so nothing is left running on "
                "stage. If the operator needs something they can fire, build "
                "that afterwards with run_commands, recalling the presets this "
                "tool reports.\n"
                "\n"
                'The result carries "executed", a per-command "commands" list '
                'exactly like run_commands, and a "report":\n'
                '- "created": every preset stored, with its pool, slot and '
                "label.\n"
                '- "unmapped": each position role the rig could NOT address, '
                'with a reason — "no_match" (no group named anything like it), '
                '"ambiguous" (a group name claimed by two roles) or '
                '"unaddressable" (a group matched but carries no number). An '
                "unmapped role emits NO command and gets NO substitute: report "
                "it to the operator, never aim it at another group.\n"
                '- "skipped": each preset store that did NOT happen, with its '
                'reason — "conflict" (that pool already holds a preset with '
                'this name), "no_free_slot" (occupancy was not observed, so no '
                'slot can be claimed free), "pool_unresolved" (this rig has no '
                'pool of that type) or "pool_unaddressable" (it has one with '
                "no number). Nothing is ever overwritten and nothing is "
                "re-slotted; the unit is one preset store, so a look can be "
                "partly created and partly skipped.\n"
                '- "complete": false whenever anything was unmapped or '
                "skipped. Say so — never report a partial run as a whole one.\n"
                "\n"
                "An empty bundle (nothing executed, no created presets) means "
                "the rig addressed none of this look's roles. That is an "
                "answer, not a transient failure: do not retry it, report the "
                "unmapped roles instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "look_id": {
                        "type": "string",
                        "description": "The look_id of a find_looks match, copied verbatim.",
                    },
                    "capture_shape": {
                        "type": "string",
                        "enum": list(CAPTURE_SHAPES),
                        "description": (
                            "Optional. Leave unset — the default stores every "
                            "family from one capture. Use "
                            f"'{CAPTURE_PER_FAMILY}' only if a previous run "
                            "visibly over-captured (e.g. a Dimmer preset that "
                            "also holds the colour); it isolates one capture "
                            "cycle per family at the cost of a longer bundle."
                        ),
                    },
                },
                "required": ["look_id"],
            },
        ),
        ToolDefinition(
            name="prepare_busking",
            description=(
                "Prepare a busking palette for one genre: store the genre's whole "
                "look set as colour/position/beam/dimmer presets on THIS rig, in a "
                "single bundle needing one approval. Call this when the operator "
                "asks to get ready for a rock / ballad / worship / EDM set rather "
                "than to realise one specific look. The rig is read here — never "
                "pass groups, pools or slot numbers. Returns a two-tier report: "
                "totals plus a per-look verdict, so a partially stored palette says "
                "which look is missing and why."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "genre": {
                        "type": "string",
                        "description": (
                            "The operator's own word for the genre, Korean or "
                            "English (e.g. '록', 'ballad', '워십', 'EDM'). An "
                            "unrecognised word is answered with the genres this "
                            "library actually holds."
                        ),
                    },
                },
                "required": ["genre"],
            },
        ),
        ToolDefinition(
            name="prepare_songcue",
            description=(
                "Prepare one song-structure cue list on THIS rig. Provide the song "
                "title, genre, section names and section start times; the tool reads "
                "the current groups and sequences itself, maps sections through the "
                "look library, stores one Sequence with one Cue per section, adds the "
                "measured Timecode and TrigType/TrigTime commands, and sends the "
                "whole bundle through the same run_commands path as any direct "
                "console execution. Do not pass rig numbers or copied rig sections."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "song_title": {
                        "type": "string",
                        "description": "Song title used for the generated cue-list report.",
                    },
                    "genre": {
                        "type": "string",
                        "description": (
                            "The operator's own word for the genre, Korean or English "
                            "(e.g. '록', 'ballad', '워십', 'EDM')."
                        ),
                    },
                    "timecode_number": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Positive Timecode object number to create for this draft.",
                    },
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Section name, such as Intro, Verse, Chorus or Drop.",
                                },
                                "start": {
                                    "description": "Start time as mm:ss, mm:ss.mmm, or seconds.",
                                },
                                "dynamics": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 5,
                                    "description": (
                                        "Optional explicit dynamics for section names the library "
                                        "does not recognise."
                                    ),
                                },
                            },
                            "required": ["name", "start"],
                        },
                        "description": (
                            "Song sections in input order. The tool rejects duplicate or "
                            "backward start times instead of sorting them."
                        ),
                    },
                    "explicit_dynamics": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                        },
                        "description": (
                            "Optional map from zero-based section index to explicit dynamics "
                            "for unknown section names."
                        ),
                    },
                },
                "required": ["song_title", "genre", "timecode_number", "sections"],
            },
        ),
    )
    handlers: dict[str, _Handler] = {
        "run_commands": run_commands,
        "query_state": query_state,
        "deploy_plugin": deploy_plugin,
        "get_rig_context": get_rig_context,
        "find_looks": find_looks,
        "instantiate_look": instantiate_look,
        "prepare_busking": prepare_busking,
        "prepare_songcue": prepare_songcue,
    }
    return ToolRegistry(definitions, handlers)
