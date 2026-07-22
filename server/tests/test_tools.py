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


def _snapshot(path: str, names: list[str], numbers: list[int] | None = None) -> dict:
    # Each child carries its real pool number ``i`` (the responder's pool slot
    # per copilot_responder.lua build_snapshot / server/safety/console.py, which
    # treats ``i`` as the slot). ``numbers`` supplies NON-CONTIGUOUS pool numbers
    # (AC-DEPLOY-020); it defaults to a contiguous 1..N.
    nums = numbers if numbers is not None else list(range(1, len(names) + 1))
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": [{"i": n, "name": name} for n, name in zip(nums, names, strict=True)],
    }


# Standard test showfile snapshot fixture (AC-MVP-025) — fixture/group/preset-pool vocab.
_RIG_TREE = {
    DEFAULT_RIG_CONTEXT_PATHS["fixtures"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["fixtures"], ["Spot 1", "Wash 1", "Wash 2"]
    ),
    DEFAULT_RIG_CONTEXT_PATHS["groups"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["groups"], ["Vocals", "Wash All"]
    ),
    DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["preset_pools"], ["Dimmer", "Color"]
    ),
}

# Non-contiguous pool-number showfile (AC-DEPLOY-020) — groups live at pool
# 1, 2, 7 (NOT 1, 2, 3). This is the exact shape that made the model map "the
# 3rd item" onto a non-existent "Group 3" → "Illegal object" (live-demo #3).
_GAPPED_RIG_TREE = {
    DEFAULT_RIG_CONTEXT_PATHS["fixtures"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["fixtures"], ["Spot 1", "Wash 1", "Wash 2"], numbers=[1, 4, 5]
    ),
    DEFAULT_RIG_CONTEXT_PATHS["groups"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["groups"], ["Vocals", "Wash All", "Big Spot"], numbers=[1, 2, 7]
    ),
    DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]: _snapshot(
        DEFAULT_RIG_CONTEXT_PATHS["preset_pools"], ["Dimmer", "Color"], numbers=[1, 4]
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

    def test_in_bundle_duplicate_command_is_not_re_executed(self):
        # MEDIUM backlog item (M6c 종합, server/orchestrator/tools.py:145) —
        # ``context.executed_ok`` is the frozenset from a PRIOR tool call; it
        # is never updated as commands succeed WITHIN this loop iteration.
        # A command string repeated TWICE in the SAME ``commands`` list must
        # still be recognized as already-executed on its second occurrence
        # (REQ-MVP-033 dedup semantics — never duplicate a console side
        # effect), not silently re-executed.
        port = ScriptedPort()
        registry = _registry(port=port)
        execution = registry.dispatch(_call("run_commands", {"commands": ["cmd1", "cmd1"]}))
        assert port.executed == ["cmd1"]  # execute() called exactly once
        statuses = [o.status for o in execution.command_outcomes]
        assert statuses == ["executed_ok", "skipped_already_executed"]

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


class FakeDeployPipeline:
    """Scripted M7 pipeline — records every deploy request."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.deploys: list[tuple[str, str]] = []

    def deploy(self, name: str, lua_source: str):
        self.deploys.append((name, lua_source))
        return self.outcome


def _deploy_registry(outcome, port=None, state_port=None):
    pipeline = FakeDeployPipeline(outcome)
    registry = build_toolset(
        execution_port=port or ScriptedPort(),
        state_port=state_port or FakeStatePort(dict(_RIG_TREE)),
        deploy_pipeline=pipeline,
    )
    return registry, pipeline


class TestDeployPluginTool:
    def test_unwired_session_is_a_safe_structured_error(self):
        # Without a wired pipeline (M7 dependency absent) the tool behaves
        # like the former M3 stub: structured error, zero sends anywhere.
        port = ScriptedPort()
        state_port = FakeStatePort(dict(_RIG_TREE))
        registry = _registry(port=port, state_port=state_port)
        execution = registry.dispatch(
            _call("deploy_plugin", {"name": "cleaner", "lua_source": "return 1"})
        )
        assert execution.result.is_error is True
        assert "not wired" in execution.result.content
        assert port.executed == []
        assert state_port.queries == []

    def test_invalid_arguments_never_reach_the_pipeline(self):
        from server.deploy.pipeline import DeployOutcome

        registry, pipeline = _deploy_registry(DeployOutcome(status="deployed"))
        for arguments in (
            {},
            {"name": "x"},
            {"lua_source": "return 1"},
            {"name": 1, "lua_source": 2},
        ):
            execution = registry.dispatch(_call("deploy_plugin", arguments))
            assert execution.result.is_error is True
        assert pipeline.deploys == []

    def test_deployed_outcome_maps_to_executed_ok(self):
        from server.deploy.pipeline import DeployOutcome

        registry, pipeline = _deploy_registry(
            DeployOutcome(status="deployed", detail="deployed", destructive=True)
        )
        execution = registry.dispatch(
            _call("deploy_plugin", {"name": "Cleaner", "lua_source": "return 1"})
        )
        assert execution.result.is_error is False
        content = json.loads(execution.result.content)
        assert content["deployed"] is True
        assert content["destructive"] is True
        (outcome,) = execution.command_outcomes
        assert outcome.status == "executed_ok"
        assert pipeline.deploys == [("Cleaner", "return 1")]

    def test_compile_block_maps_to_blocked_and_feeds_correction(self):
        from server.deploy.pipeline import DeployOutcome

        registry, _ = _deploy_registry(
            DeployOutcome(
                status="blocked_compile",
                detail="lua compile failed: unexpected symbol",
                compile_error="unexpected symbol",
            )
        )
        execution = registry.dispatch(
            _call("deploy_plugin", {"name": "Cleaner", "lua_source": "broken("})
        )
        assert execution.result.is_error is True
        assert "compile" in execution.result.content
        (outcome,) = execution.command_outcomes
        assert outcome.status == "blocked"  # counts toward the retry cap

    def test_review_rejection_maps_to_rejected_not_blocked(self):
        from server.deploy.pipeline import DeployOutcome

        registry, _ = _deploy_registry(
            DeployOutcome(status="review_rejected", detail="not approved")
        )
        execution = registry.dispatch(
            _call("deploy_plugin", {"name": "Cleaner", "lua_source": "return 1"})
        )
        assert execution.result.is_error is True
        (outcome,) = execution.command_outcomes
        assert outcome.status == "rejected"  # human decision — not a retry


class TestRigContextPaths:
    """The default paths MUST address objects that actually exist on 2.4.2."""

    def test_defaults_match_the_live_console_object_tree(self):
        # Live-verified against grandMA3 onPC 2.4.2 (state queries on the real
        # console): "Patch/Fixtures" and "DataPool/Presets" DO NOT EXIST — both
        # reply "path segment not found" — while "DataPool/Groups" resolves.
        # The patched fixtures live under the STAGE ("Patch/Stages/1/Fixtures",
        # 19 children) and the preset TYPES under "DataPool/PresetPools" (14
        # children). Pinning the exact mapping so the two dead paths cannot be
        # reintroduced: a wrong path only degrades to a soft per-section error
        # that nobody reads, which is how it survived unnoticed.
        assert DEFAULT_RIG_CONTEXT_PATHS == {
            "fixtures": "Patch/Stages/1/Fixtures",
            "groups": "DataPool/Groups",
            "preset_pools": "DataPool/PresetPools",
        }

    def test_the_two_dead_paths_are_never_defaults_again(self):
        dead = {"Patch/Fixtures", "DataPool/Presets", "Patch/Layers"}
        assert dead.isdisjoint(set(DEFAULT_RIG_CONTEXT_PATHS.values()))


class TestGetRigContext:
    def test_exposes_real_pool_number_and_name(self):
        # AC-MVP-025 + AC-DEPLOY-020 ①: each object exposes its REAL pool
        # number ("no") AND name — not a bare positional array of names.
        registry = _registry()
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["fixtures"] == [
            {"no": 1, "name": "Spot 1"},
            {"no": 2, "name": "Wash 1"},
            {"no": 3, "name": "Wash 2"},
        ]
        assert summary["groups"] == [
            {"no": 1, "name": "Vocals"},
            {"no": 2, "name": "Wash All"},
        ]
        assert summary["preset_pools"] == [
            {"no": 1, "name": "Dimmer"},
            {"no": 2, "name": "Color"},
        ]
        assert execution.result.is_error is False

    def test_non_contiguous_pool_numbers_are_exposed_not_positional(self):
        # AC-DEPLOY-020 ①②: on a rig whose groups live at pool 1, 2, 7 the
        # third group MUST surface as pool 7 (its REAL number, not positional
        # index 3), and a non-existent number (3, absent from {1,2,7}) MUST
        # NOT appear as an available object — so the model can no longer map
        # "the 3rd item" onto a hallucinated "Group 3" ("Illegal object", #3).
        registry = _registry(state_port=FakeStatePort(dict(_GAPPED_RIG_TREE)))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["groups"] == [
            {"no": 1, "name": "Vocals"},
            {"no": 2, "name": "Wash All"},
            {"no": 7, "name": "Big Spot"},
        ]
        group_numbers = {entry["no"] for entry in summary["groups"]}
        assert group_numbers == {1, 2, 7}
        assert 3 not in group_numbers  # the hallucinated "Group 3" is absent
        assert execution.result.is_error is False

    def test_child_missing_pool_number_degrades_to_name_only(self):
        # A child lacking ``i`` degrades to a name-only entry rather than
        # crashing or emitting a null pool number.
        tree = {
            DEFAULT_RIG_CONTEXT_PATHS["fixtures"]: {
                "v": 1,
                "kind": "state",
                "path": DEFAULT_RIG_CONTEXT_PATHS["fixtures"],
                "children": [{"name": "Nameless"}, {"i": 4, "name": "Spot 4"}],
            },
            DEFAULT_RIG_CONTEXT_PATHS["groups"]: _snapshot(
                DEFAULT_RIG_CONTEXT_PATHS["groups"], ["Vocals"]
            ),
            DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]: _snapshot(
                DEFAULT_RIG_CONTEXT_PATHS["preset_pools"], ["Dimmer"]
            ),
        }
        registry = _registry(state_port=FakeStatePort(tree))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["fixtures"] == [{"name": "Nameless"}, {"no": 4, "name": "Spot 4"}]
        assert execution.result.is_error is False

    def test_missing_section_is_reported_not_fatal(self):
        tree = dict(_RIG_TREE)
        del tree[DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]]
        registry = _registry(state_port=FakeStatePort(tree))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["fixtures"]  # healthy sections still present
        assert "error" in summary["preset_pools"]

    def test_unresolved_path_is_distinguished_from_an_unreachable_console(self):
        # THE defect class that hid the wrong default paths: a path that does
        # not exist in this showfile (a CONFIGURATION bug) and a console that
        # never answered (an OPERATIONAL condition) looked identical — one
        # soft "unavailable" string. When a sibling section DID answer, the
        # console is demonstrably reachable, so the failing path is wrong.
        tree = dict(_RIG_TREE)
        del tree[DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]]
        registry = _registry(state_port=FakeStatePort(tree))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        failure = summary["preset_pools"]
        assert failure["reason"] == "path_not_resolved"
        assert failure["path"] == DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]
        assert "error" in failure
        # Partial vocabulary is still usable — not a failed tool call.
        assert execution.result.is_error is False

    def test_no_section_resolving_reports_an_unreachable_console_and_errors(self):
        # Nothing answered: the paths CANNOT be blamed (the console may simply
        # be down), and the call returned zero rig vocabulary — that is a
        # failed tool call, not a quietly successful one.
        registry = _registry(state_port=FakeStatePort({}))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert {section["reason"] for section in summary.values()} == {"console_unreachable"}
        assert execution.result.is_error is True

    def test_an_empty_section_still_proves_the_console_answered(self):
        # "DataPool/PresetPools/N with 0 children" is a real, live shape: the
        # pool exists but holds nothing. An empty child list is a RESOLVED
        # path, so a sibling failure must still classify as path_not_resolved.
        tree = dict(_RIG_TREE)
        del tree[DEFAULT_RIG_CONTEXT_PATHS["groups"]]
        tree[DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]] = _snapshot(
            DEFAULT_RIG_CONTEXT_PATHS["preset_pools"], []
        )
        tree[DEFAULT_RIG_CONTEXT_PATHS["fixtures"]] = _snapshot(
            DEFAULT_RIG_CONTEXT_PATHS["fixtures"], []
        )
        registry = _registry(state_port=FakeStatePort(tree))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["preset_pools"] == []
        assert summary["groups"]["reason"] == "path_not_resolved"
        assert execution.result.is_error is False


class TestRigContextDescription:
    """The description is the model's ONLY contract for reading the summary."""

    def _description(self) -> str:
        (definition,) = [d for d in _registry().definitions() if d.name == "get_rig_context"]
        return definition.description

    def test_preset_pools_are_described_as_types_not_stored_presets(self):
        # "DataPool/PresetPools" lists the preset TYPES (Dimmer, Position,
        # Color, ...). The individual stored presets live INSIDE each pool and
        # a depth-1 snapshot cannot reach them — the description must not let
        # the model believe it is seeing presets it never received.
        text = self._description()
        assert "preset_pools" in text
        assert "query_state" in text
        lowered = text.lower()
        assert "type" in lowered
        assert "not the individual" in lowered or "not individual" in lowered

    def test_fixture_numbers_are_not_promised_to_be_fixture_ids(self):
        # A fixture entry's "no" is its slot in the stage patch list; whether
        # that equals the fixture id (FID) is NOT established by this snapshot.
        lowered = self._description().lower()
        assert "fid" in lowered
        assert "not guaranteed" in lowered

    def test_failure_reasons_are_documented(self):
        text = self._description()
        assert "path_not_resolved" in text
        assert "console_unreachable" in text


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
