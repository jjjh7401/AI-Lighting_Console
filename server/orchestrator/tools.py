"""The four Phase 1 tools (REQ-MVP-005) built on the execution/state ports.

Tools never touch the OSC bridge — they depend on :mod:`server.orchestrator.ports`
only (REQ-MVP-029 forward design). ``deploy_plugin`` (M7) drives the deploy
pipeline — pcall compile harness + destructive scan + human review gate
(REQ-MVP-019); without a wired pipeline it stays a safe structured error and
never sends anything.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from server.llm.types import ToolCall, ToolDefinition, ToolResult
from server.orchestrator.ports import BundleGate, CommandExecutionPort, StateQueryPort

if TYPE_CHECKING:  # policy types only — no runtime import cycle
    from server.deploy.pipeline import DeployOutcome

TOOL_NAMES = ("run_commands", "query_state", "deploy_plugin", "get_rig_context")

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
#                  INSIDE each pool ("DataPool/PresetPools/<no>") and a depth-1
#                  snapshot cannot reach them.
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
    "fixtures": "Patch/Stages/1/Fixtures",
    "groups": "DataPool/Groups",
    "preset_pools": "DataPool/PresetPools",
}


# Why a rig-context section is missing. The two causes are NOT interchangeable
# and used to be indistinguishable — both surfaced as one soft "unavailable"
# string, which is exactly how the two dead default paths above went unnoticed
# for the whole of Stage 1:
#   path_not_resolved   - a SIBLING section answered, so the console is
#                         demonstrably reachable and THIS path is wrong for
#                         this showfile: a configuration defect, fix the path.
#   console_unreachable - nothing answered, so no path can be blamed: an
#                         operational condition, retry when the console is up.
_REASON_UNRESOLVED = "path_not_resolved"
_REASON_UNREACHABLE = "console_unreachable"
_FAILURE_MESSAGES = {
    _REASON_UNRESOLVED: (
        "this path does not exist in the loaded showfile — other sections "
        "answered, so the console IS reachable"
    ),
    _REASON_UNREACHABLE: "no section answered — the console did not respond",
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


# @MX:NOTE: [AUTO] rig-context exposes the REAL pool number ('no'), not a bare
# positional index — stops the model mapping "the Nth item" onto "object N" and
# inventing a non-existent object on a non-contiguous rig (a hallucinated
# "Group 3" when groups live at pool 1, 2, 7). Live-demo finding #3,
# SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-029 / AC-DEPLOY-020.
def _rig_object(child: dict) -> dict[str, object]:
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
    bundle_gate: BundleGate | None = None,
    deploy_pipeline: DeployPipelinePort | None = None,
) -> ToolRegistry:
    """Build the 4-tool registry wired to the given ports (REQ-MVP-005).

    When ``bundle_gate`` is provided (M4 production wiring), every
    run_commands bundle is screened as a WHOLE before any per-command
    execution starts (REQ-MVP-011 pipeline + REQ-MVP-015 all-or-nothing);
    a non-cleared decision returns the block/hold reasons as an error tool
    result, feeding the self-correction loop (REQ-MVP-012).
    """
    rig_paths = dict(rig_paths or DEFAULT_RIG_CONTEXT_PATHS)

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
            elif command in already_executed:
                # Never re-execute a command that already succeeded — either
                # in a prior tool call (context.executed_ok) or earlier in
                # THIS bundle — re-execution duplicates its console effect.
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
        summary: dict[str, object] = {}
        failures: dict[str, tuple[str, str]] = {}
        resolved = 0
        for section, path in rig_paths.items():
            try:
                payload = state_port.query_state(path)
            except Exception as exc:
                # Placeholder keeps the section's position; classified below,
                # once every section's outcome is known.
                summary[section] = None
                failures[section] = (path, str(exc))
                continue
            # A resolved path proves the console ANSWERED — even with zero
            # children (a real shape: an empty preset pool).
            resolved += 1
            children = payload.get("children", [])
            summary[section] = [_rig_object(child) for child in children if isinstance(child, dict)]
        reason = _REASON_UNRESOLVED if resolved else _REASON_UNREACHABLE
        for section, (path, detail) in failures.items():
            summary[section] = {
                "reason": reason,
                "path": path,
                "error": f"{_FAILURE_MESSAGES[reason]}: {detail}",
            }
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(summary, ensure_ascii=False),
                # Partial vocabulary is still usable; returning NOTHING is a
                # failed call, not a quiet success.
                is_error=bool(failures) and resolved == 0,
            )
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
                "Summarize the loaded showfile's rig vocabulary. Call this FIRST "
                "when the instruction uses venue/field terms (e.g. Korean field "
                "vocabulary) that must be resolved to actual showfile object "
                'names. Returns three sections: "fixtures" (the stage\'s patched '
                'fixtures), "groups" (the group pool), and "preset_pools" (the '
                "preset TYPES — Dimmer, Position, Gobo, Color, ... — NOT the "
                "individual stored presets, which live INSIDE each pool: to list "
                "those, call query_state on one pool, e.g. "
                "'DataPool/PresetPools/4'). Each object is returned as "
                '{"no": <number>, "name": <name>}; ALWAYS reference an object by '
                'its REAL "no", NEVER by positional order — numbers may be '
                "non-contiguous (e.g. 1, 2, 7), so the Nth listed item is NOT "
                'necessarily object N. An entry with a "name" but NO "no" means '
                "its number is UNKNOWN: do not guess one — resolve it with "
                "query_state before addressing that object. For groups and preset "
                'pools the "no" IS the pool number you address (e.g. Group 2). For '
                'fixtures the "no" is the fixture\'s slot in the stage patch list '
                "and is NOT guaranteed to be its fixture id (FID) — confirm the FID "
                "with query_state before addressing a fixture by number. A section "
                'may instead come back as {"reason": ...}: "path_not_resolved" '
                "means that vocabulary does not exist in THIS showfile (other "
                'sections answered), "console_unreachable" means nothing answered. '
                "In both cases you did NOT receive that vocabulary — say so and "
                "ask, never invent objects for it."
            ),
            parameters={"type": "object", "properties": {}},
        ),
    )
    handlers: dict[str, _Handler] = {
        "run_commands": run_commands,
        "query_state": query_state,
        "deploy_plugin": deploy_plugin,
        "get_rig_context": get_rig_context,
    }
    return ToolRegistry(definitions, handlers)
