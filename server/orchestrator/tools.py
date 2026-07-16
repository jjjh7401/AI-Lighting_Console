"""The four Phase 1 tools (REQ-MVP-005) built on the execution/state ports.

Tools never touch the OSC bridge — they depend on :mod:`server.orchestrator.ports`
only (REQ-MVP-029 forward design). ``deploy_plugin`` is registered but safely
stubbed: its pcall compile harness + human review gate are Milestone M7 scope
(plan.md section C), so until then it returns a structured "not yet available"
error and never sends anything.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from server.llm.types import ToolCall, ToolDefinition, ToolResult
from server.orchestrator.ports import BundleGate, CommandExecutionPort, StateQueryPort

TOOL_NAMES = ("run_commands", "query_state", "deploy_plugin", "get_rig_context")

# Object-tree paths for the rig-context summary (REQ-MVP-037). Placeholder
# defaults pending live-console calibration at M6 (same discipline as the M2
# PROTOCOL.md assumptions); override via build_toolset(rig_paths=...).
DEFAULT_RIG_CONTEXT_PATHS = {
    "patch": "Patch/Fixtures",
    "groups": "DataPool/Groups",
    "presets": "DataPool/Presets",
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
            elif command in context.executed_ok:
                # Never re-execute a command that already succeeded in this
                # instruction — re-execution duplicates its console effect.
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

    # -- deploy_plugin (REQ-MVP-019 — SAFE STUB until M7) -----------------------

    def deploy_plugin(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        # M7 builds the pcall compile harness + human review gate on top of
        # this stub. Until then deployment is unavailable BY DESIGN and the
        # stub must never send anything toward the console.
        return _error_result(
            call,
            "deploy_plugin is not yet available (Milestone M7): plugin deployment "
            "requires the pcall compile check and the human review gate",
        )

    # -- get_rig_context (REQ-MVP-037 — showfile-based basic summary) -----------

    def get_rig_context(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        summary: dict[str, object] = {}
        for section, path in rig_paths.items():
            try:
                payload = state_port.query_state(path)
                children = payload.get("children", [])
                summary[section] = [
                    child.get("name", "") for child in children if isinstance(child, dict)
                ]
            except Exception as exc:
                summary[section] = {"error": f"unavailable ({path}): {exc}"}
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(summary, ensure_ascii=False),
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
                "Deploy a Lua plugin to the console. NOT YET AVAILABLE in this "
                "milestone — calls return a structured error until the compile "
                "check and human review gate land (M7)."
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
                "Summarize the loaded showfile's rig vocabulary: patched fixtures, "
                "groups, and presets. Call this FIRST when the instruction uses "
                "venue/field terms (e.g. Korean field vocabulary) that must be "
                "resolved to actual showfile object names."
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
