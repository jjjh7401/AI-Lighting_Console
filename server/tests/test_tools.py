"""Tool registry tests (M3 — AC-MVP-013 tool registration, AC-MVP-025 rig context).

The four Phase 1 tools (REQ-MVP-005) are built on top of narrow execution/state
PORTS — never on the OSC bridge directly. The M4 safety gate will be the sole
production implementation of the execution port (REQ-MVP-029 single-chokepoint
forward design); M3 tests use in-memory fakes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    TOOL_NAMES,
    ExecutionContext,
    build_toolset,
)


class ScriptedPort:
    """Fake CommandExecutionPort — scripted failures, records every execute call."""

    def __init__(self, failures: frozenset[str] = frozenset()):
        self.failures = set(failures)
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        if command in self.failures:
            return ExecutionResult(ok=False, detail=f"syntax error near '{command}'")
        return ExecutionResult(ok=True, detail="OK")


class FakeStatePort:
    """Fake StateQueryPort backed by a dict of path -> decoded snapshot payload."""

    def __init__(self, tree: dict):
        self.tree = tree
        self.queries: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queries.append(path)
        if path not in self.tree:
            raise LookupError(f"unknown object path: {path}")
        return self.tree[path]


def _snapshot(path: str, names: list[str]) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": [{"name": name} for name in names],
    }


# Standard test showfile snapshot fixture (AC-MVP-025) — patch/group/preset vocab.
_RIG_TREE = {
    DEFAULT_RIG_CONTEXT_PATHS["patch"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["patch"], ["Spot 1", "Wash 1", "Wash 2"]
    ),
    DEFAULT_RIG_CONTEXT_PATHS["groups"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["groups"], ["Vocals", "Wash All"]
    ),
    DEFAULT_RIG_CONTEXT_PATHS["presets"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["presets"], ["Warm Wash", "Cool Cyc"]
    ),
}


def _registry(port=None, state_port=None):
    return build_toolset(
        execution_port=port or ScriptedPort(),
        state_port=state_port or FakeStatePort(dict(_RIG_TREE)),
    )


def _call(name: str, arguments: dict | None = None, call_id: str = "call-1") -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments or {})


class TestRegistry:
    def test_exactly_four_tools_registered(self):
        # AC-MVP-013: run_commands / query_state / deploy_plugin / get_rig_context.
        registry = _registry()
        names = [definition.name for definition in registry.definitions()]
        assert sorted(names) == sorted(TOOL_NAMES)
        assert len(names) == 4

    def test_definitions_carry_descriptions_and_object_schemas(self):
        for definition in _registry().definitions():
            assert definition.description.strip()
            assert definition.parameters["type"] == "object"

    def test_unknown_tool_name_returns_error_result(self):
        execution = _registry().dispatch(_call("bogus_tool"))
        assert execution.result.is_error is True
        assert "unknown tool" in execution.result.content


class TestRunCommands:
    def test_commands_execute_in_order_via_the_port(self):
        port = ScriptedPort()
        registry = _registry(port=port)
        execution = registry.dispatch(
            _call("run_commands", {"commands": ["Store Group 7", "Label Group 7 'Vocals'"]})
        )
        assert port.executed == ["Store Group 7", "Label Group 7 'Vocals'"]
        assert execution.result.is_error is False
        assert [o.status for o in execution.command_outcomes] == ["executed_ok"] * 2

    def test_stop_on_first_failure(self):
        # REQ-MVP-033 execution atomicity seed: remaining commands never run.
        port = ScriptedPort(failures=frozenset({"B"}))
        registry = _registry(port=port)
        execution = registry.dispatch(_call("run_commands", {"commands": ["A", "B", "C"]}))
        assert port.executed == ["A", "B"]
        statuses = [o.status for o in execution.command_outcomes]
        assert statuses == ["executed_ok", "failed", "not_executed"]
        assert execution.result.is_error is True

    def test_already_executed_commands_are_skipped(self):
        # Self-correction honesty: never resend an already-executed command.
        port = ScriptedPort()
        registry = _registry(port=port)
        context = ExecutionContext(executed_ok=frozenset({"A"}))
        execution = registry.dispatch(_call("run_commands", {"commands": ["A", "B"]}), context)
        assert port.executed == ["B"]
        statuses = {o.command: o.status for o in execution.command_outcomes}
        assert statuses["A"] == "skipped_already_executed"
        assert statuses["B"] == "executed_ok"

    def test_feedback_content_carries_per_command_status(self):
        port = ScriptedPort(failures=frozenset({"B"}))
        registry = _registry(port=port)
        execution = registry.dispatch(_call("run_commands", {"commands": ["A", "B", "C"]}))
        payload = json.loads(execution.result.content)
        assert payload["all_ok"] is False
        assert [entry["status"] for entry in payload["commands"]] == [
            "executed_ok",
            "failed",
            "not_executed",
        ]
        assert "syntax error" in payload["commands"][1]["detail"]

    def test_invalid_arguments_are_an_error_without_port_calls(self):
        port = ScriptedPort()
        registry = _registry(port=port)
        for arguments in ({}, {"commands": []}, {"commands": "Store Cue 5"}, {"commands": [1]}):
            execution = registry.dispatch(_call("run_commands", arguments))
            assert execution.result.is_error is True
        assert port.executed == []


class TestQueryState:
    def test_returns_decoded_snapshot_payload(self):
        state_port = FakeStatePort(dict(_RIG_TREE))
        registry = _registry(state_port=state_port)
        path = DEFAULT_RIG_CONTEXT_PATHS["groups"]
        execution = registry.dispatch(_call("query_state", {"path": path}))
        assert json.loads(execution.result.content) == _RIG_TREE[path]
        assert state_port.queries == [path]

    def test_unknown_path_is_an_error_result(self):
        registry = _registry(state_port=FakeStatePort({}))
        execution = registry.dispatch(_call("query_state", {"path": "DataPool/Nope"}))
        assert execution.result.is_error is True

    def test_missing_path_argument_is_an_error(self):
        execution = _registry().dispatch(_call("query_state", {}))
        assert execution.result.is_error is True


class TestDeployPluginStub:
    def test_registered_but_safely_stubbed_until_m7(self):
        # plan.md M7: pcall harness + review gate land later, on this stub.
        port = ScriptedPort()
        state_port = FakeStatePort(dict(_RIG_TREE))
        registry = _registry(port=port, state_port=state_port)
        execution = registry.dispatch(
            _call("deploy_plugin", {"name": "cleaner", "lua_source": "return 1"})
        )
        assert execution.result.is_error is True
        assert "M7" in execution.result.content
        assert port.executed == []  # never sends anything anywhere
        assert state_port.queries == []


class TestGetRigContext:
    def test_summarizes_patch_group_preset_vocabulary(self):
        # AC-MVP-025: summary contains patch, group, and preset vocabulary.
        registry = _registry()
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["patch"] == ["Spot 1", "Wash 1", "Wash 2"]
        assert summary["groups"] == ["Vocals", "Wash All"]
        assert summary["presets"] == ["Warm Wash", "Cool Cyc"]
        assert execution.result.is_error is False

    def test_missing_section_is_reported_not_fatal(self):
        tree = dict(_RIG_TREE)
        del tree[DEFAULT_RIG_CONTEXT_PATHS["presets"]]
        registry = _registry(state_port=FakeStatePort(tree))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["patch"]  # healthy sections still present
        assert "error" in summary["presets"]


_ORCHESTRATOR_DIR = Path(__file__).resolve().parents[1] / "orchestrator"
_IMPORT_LINE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.MULTILINE)


class TestArchitectureBoundaries:
    def test_orchestrator_never_touches_the_osc_send_surface(self):
        # REQ-MVP-029 forward design: only the M4 gate may reach the bridge.
        for source in _ORCHESTRATOR_DIR.glob("*.py"):
            imports = _IMPORT_LINE.findall(source.read_text(encoding="utf-8"))
            for module in imports:
                assert not module.startswith("server.bridge"), (
                    f"{source.name} must not import the bridge (found {module})"
                )
                assert not module.startswith("pythonosc"), (
                    f"{source.name} must not import OSC transport (found {module})"
                )

    def test_orchestrator_is_provider_neutral(self):
        # REQ-MVP-038: the orchestrator never branches on provider identity.
        for source in _ORCHESTRATOR_DIR.glob("*.py"):
            text = source.read_text(encoding="utf-8").lower()
            for provider_name in ("anthropic", "gemini"):
                assert provider_name not in text, (
                    f"{source.name} must stay provider-neutral (found {provider_name!r})"
                )
