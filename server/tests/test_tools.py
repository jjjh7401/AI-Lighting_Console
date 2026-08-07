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
    RIG_DRILLDOWN_QUERY_CAP,
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


def _rig_summary(registry) -> dict:
    """Dispatch get_rig_context and return the decoded summary."""
    return json.loads(registry.dispatch(_call("get_rig_context")).result.content)


# Standard test showfile snapshot fixture (AC-MVP-025). Named sections carry
# realistic vocabulary; every OTHER default path resolves to an empty pool, so a
# newly added default cannot silently arrive as "unavailable" in these tests.
_RIG_NAMED_SECTIONS = {
    "fixtures": ["Spot 1", "Wash 1", "Wash 2"],
    "groups": ["Vocals", "Wash All"],
    "preset_pools": ["Dimmer", "Color"],
}
_RIG_TREE = {
    path: _snapshot(path, _RIG_NAMED_SECTIONS.get(section, []))
    for section, path in DEFAULT_RIG_CONTEXT_PATHS.items()
}
# Preset pools are drilled into by default (DEFAULT_RIG_DRILLDOWN); a real
# console answers each one, most of them empty. Without this, every fixture
# using the default tree would see "contents_unavailable" rather than a
# genuinely empty pool — a fixture bug, not the behaviour under test.
for _n in range(1, len(_RIG_NAMED_SECTIONS["preset_pools"]) + 1):
    _RIG_TREE[f"{DEFAULT_RIG_CONTEXT_PATHS['preset_pools']}/{_n}"] = _snapshot(
        f"{DEFAULT_RIG_CONTEXT_PATHS['preset_pools']}/{_n}", []
    )

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
    def test_the_registered_tools_are_exactly_the_declared_set(self):
        # AC-MVP-013 (run_commands / query_state / deploy_plugin /
        # get_rig_context) + AC-LOOKLIB-010's find_looks and instantiate_look
        # + AC-BUSKWIZ-011's prepare_busking + AC-SONGCUE-015's prepare_songcue
        # + AC-PRECHK-014's precheck_patch
        # + AC-FXLIB-013/014's find_fx and instantiate_fx
        # + AC-SCENE-018's find_scene and compile_scene
        # + SPEC-COPILOT-PRESHOW-001's preshow_check.
        # + T-J's build_patch_sheet / build_cue_sheet / build_preset_list
        #   (SPEC-COPILOT-PAPERWORK-001, previously unregistered) and
        #   plan_executor_layout (server/looks/layout.py, previously
        #   unregistered).
        # + SPEC-COPILOT-SPATIAL-001's get_spatial_context (READ) and
        #   arrange_fixtures (WRITE) — kept as TWO tools by decision D-4, so a
        #   showfile-mutating call never hides behind the tool a model uses to
        #   look at the rig.
        # + SPEC-COPILOT-GROUPGEN-001's classify_arrangement_topology (READ)
        #   and create_arrangement_groups (WRITE) — same D-4 split: a group
        #   write carries its own tool-layer approval gate (design.md §7) and
        #   must never hide behind the read tool.
        # + build_handover_pack (server/paperwork/bundle.py, P0 W2 — the
        #   handover-pack index tying the three T-J sheets together).
        # The count is asserted against the declared tuple's length so the set
        # stays CLOSED: adding a handler without declaring it, or declaring one
        # without a handler, still fails here.
        registry = _registry()
        names = [definition.name for definition in registry.definitions()]
        assert sorted(names) == sorted(TOOL_NAMES)
        assert len(names) == len(TOOL_NAMES) == 23

    def test_the_four_original_tools_are_still_registered(self):
        # The M5 addition must not have displaced any of them.
        names = {definition.name for definition in _registry().definitions()}
        assert {"run_commands", "query_state", "deploy_plugin", "get_rig_context"} <= names

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


class TestProgrammerStateIsExemptFromDedupe:
    """The dedupe above guards DURABLE artifacts, and only those (M4 follow-up).

    A command that establishes programmer state leaves no artifact behind to
    duplicate, so suppressing its second occurrence removes an instruction
    rather than a repeat. The look bundles this fix exists for are built from
    ``ClearAll``-delimited capture cycles: without the exemption a bundle loses
    its trailing clear, and a per-family bundle loses every cycle boundary
    after the first and stores the previous cycle's programmer.
    """

    def test_clearall_runs_at_every_moment_it_appears(self):
        port = ScriptedPort()
        registry = _registry(port=port)
        commands = ["ClearAll", "Store Preset 4.1", "ClearAll"]
        execution = registry.dispatch(_call("run_commands", {"commands": commands}))
        assert port.executed == commands
        assert [o.status for o in execution.command_outcomes] == ["executed_ok"] * 3

    def test_bare_clear_runs_at_every_moment_it_appears(self):
        # `Clear` is the step clear one rung below `ClearAll` (00_grammar.md:57)
        # and has the identical property: nothing durable to duplicate.
        port = ScriptedPort()
        registry = _registry(port=port)
        commands = ["Clear", "Store Preset 4.1", "Clear"]
        execution = registry.dispatch(_call("run_commands", {"commands": commands}))
        assert port.executed == commands
        assert [o.status for o in execution.command_outcomes] == ["executed_ok"] * 3

    def test_a_prior_calls_clear_does_not_suppress_this_ones(self):
        port = ScriptedPort()
        registry = _registry(port=port)
        context = ExecutionContext(executed_ok=frozenset({"Clear"}))
        registry.dispatch(
            _call("run_commands", {"commands": ["Clear", "Store Preset 4.1"]}), context
        )
        assert port.executed == ["Clear", "Store Preset 4.1"]

    def test_clear_and_clearall_are_matched_independently(self):
        # A test that passes because a SIBLING pattern caught the string is a
        # false green. Assert each clear is matched by exactly ONE pattern, and
        # that it is its own — so neither `Clear`'s nor `ClearAll`'s cases can
        # be carried by the other's pattern.
        from server.orchestrator.tools import _PROGRAMMER_STATE_COMMANDS

        matched = {
            text: [p.pattern for p in _PROGRAMMER_STATE_COMMANDS if p.fullmatch(text)]
            for text in ("Clear", "ClearAll")
        }
        assert matched == {"Clear": ["Clear"], "ClearAll": ["ClearAll"]}

    def test_a_bare_group_selection_is_re_selected_for_each_cycle(self):
        port = ScriptedPort()
        registry = _registry(port=port)
        commands = ["Group 11", "Store Preset 4.1", "ClearAll", "Group 11", "Store Preset 5.1"]
        registry.dispatch(_call("run_commands", {"commands": commands}))
        assert port.executed == commands

    def test_a_bare_fixture_selection_is_re_selected_for_each_cycle(self):
        # `Fixture` selects into the programmer exactly as `Group` does, so it
        # carries the same position-dependent meaning and the same exemption.
        port = ScriptedPort()
        registry = _registry(port=port)
        commands = ["Fixture 101", "Store Preset 4.1", "ClearAll", "Fixture 101"]
        registry.dispatch(_call("run_commands", {"commands": commands}))
        assert port.executed == commands

    def test_the_whole_bare_selection_operand_grammar_is_exempt(self):
        # 00_grammar.md:17-22 — `Thru` (incl. the open range), `+` and `-` are
        # general object-reference operators, so both types get all of them.
        port = ScriptedPort()
        registry = _registry(port=port)
        for command in (
            "Group 11 + 12",  # what the look layer emits for a two-group role
            "Fixture 11 + 12 + 13",
            "Fixture 101 Thru 110",
            "Fixture 11 Thru",  # open range
            "Fixture 11 Thru 19 - 15",
            "Group 1 Thru 5",
        ):
            port.executed.clear()
            registry.dispatch(_call("run_commands", {"commands": [command, command]}))
            assert port.executed == [command, command], command

    def test_a_prior_calls_clearall_does_not_suppress_this_ones(self):
        # The exemption covers the cross-call set as well as the in-bundle one:
        # a bundle that opens with a clear must clear, whatever the last one did.
        port = ScriptedPort()
        registry = _registry(port=port)
        context = ExecutionContext(executed_ok=frozenset({"ClearAll", "Group 11"}))
        registry.dispatch(
            _call("run_commands", {"commands": ["ClearAll", "Group 11", "Store Preset 4.1"]}),
            context,
        )
        assert port.executed == ["ClearAll", "Group 11", "Store Preset 4.1"]

    def test_a_repeated_store_is_still_deduped(self):
        # The rule the exemption must NOT widen into: a second `Store Preset`
        # writes a second console object (REQ-MVP-033).
        port = ScriptedPort()
        registry = _registry(port=port)
        execution = registry.dispatch(
            _call("run_commands", {"commands": ["Store Preset 4.1", "Store Preset 4.1"]})
        )
        assert port.executed == ["Store Preset 4.1"]
        assert [o.status for o in execution.command_outcomes] == [
            "executed_ok",
            "skipped_already_executed",
        ]

    def test_the_leading_verb_is_the_discriminator_not_the_object_type(self):
        # `Store` / `Label` / `Delete` all take a selection operand and all
        # leave a durable artifact; only the BARE form is programmer state.
        port = ScriptedPort()
        registry = _registry(port=port)
        for command in (
            "Store Group 7",
            "Label Group 7 'Vocals'",
            "Delete Group 3",
            "Store Fixture 5",
            "Label Fixture 5 'Spot'",
            "Delete Fixture 101 Thru 110",
        ):
            port.executed.clear()
            registry.dispatch(_call("run_commands", {"commands": [command, command]}))
            assert port.executed == [command], command

    def test_a_selection_carrying_a_value_is_still_deduped(self):
        # These select AND set — outside the enumerated exemption, which is
        # deliberately the bare selection form only.
        port = ScriptedPort()
        registry = _registry(port=port)
        for command in ("Group 3 Full", "Fixture 1 Thru 10 At 80"):
            port.executed.clear()
            registry.dispatch(_call("run_commands", {"commands": [command, command]}))
            assert port.executed == [command], command

    def test_the_match_is_case_insensitive_like_the_console(self):
        # D14: this project has already shipped one case-sensitive assert that
        # the console's own case-insensitivity walked straight past.
        port = ScriptedPort()
        registry = _registry(port=port)
        for command in (
            "clearall",
            "CLEARALL",
            "ClearAll",
            "clear",
            "CLEAR",
            "Clear",
            "group 11",
            "GROUP 11",
            "fixture 101",
            "FIXTURE 101 THRU 110",
        ):
            port.executed.clear()
            registry.dispatch(_call("run_commands", {"commands": [command, command]}))
            assert port.executed == [command, command], command


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
        # console, 2026-07-22): "Patch/Fixtures" and "DataPool/Presets" DO NOT
        # EXIST — both reply "path segment not found" — while every path below
        # resolves. Pinning the exact mapping so a dead path cannot be
        # reintroduced: a wrong path only degrades to a soft per-section error
        # that nobody reads, which is how the original two survived unnoticed.
        # Extended from the original 3-path fixtures/groups/preset_pools set to
        # cover the objects a lighting instruction is actually made of —
        # sequences, executors (pages), macros, plugins, matricks, worlds.
        assert DEFAULT_RIG_CONTEXT_PATHS == {
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

    def test_the_two_dead_paths_are_never_defaults_again(self):
        dead = {"Patch/Fixtures", "DataPool/Presets", "Patch/Layers"}
        assert dead.isdisjoint(set(DEFAULT_RIG_CONTEXT_PATHS.values()))


class TestRigContextIsSelfSufficient:
    """The app has to build its own picture of the show.

    Before this, rig context read three hard-coded paths and the model was blind
    to sequences, executors, macros, plugins and what was actually STORED in a
    preset pool — the objects a lighting instruction is made of. A human had to
    hand it the object-tree paths, which means the app could not answer
    "무빙들 파랗게 해줘" on its own. Every path below was verified live against
    onPC 2.4.2 on 2026-07-22 before being made a default.
    """

    def test_it_covers_the_objects_a_lighting_instruction_is_made_of(self):
        covered = set(DEFAULT_RIG_CONTEXT_PATHS)
        # Targets, the look itself, the trigger surface, and stored vocabulary.
        assert {"fixtures", "groups"} <= covered  # what to select
        assert {"sequences", "preset_pools"} <= covered  # what to store / recall
        assert "pages" in covered  # executors — the only way to FIRE a look
        assert {"macros", "plugins"} <= covered  # what already automates the show

    def test_every_default_path_was_verified_live(self):
        # Guessed paths are how "Patch/Fixtures" and "DataPool/Presets" shipped
        # dead for all of Stage 1, silently reducing rig context to groups only.
        assert DEFAULT_RIG_CONTEXT_PATHS["fixtures"] == "Patch/Stages/1/Fixtures"
        assert DEFAULT_RIG_CONTEXT_PATHS["preset_pools"] == "DataPool/PresetPools"
        assert DEFAULT_RIG_CONTEXT_PATHS["sequences"] == "DataPool/Sequences"
        assert DEFAULT_RIG_CONTEXT_PATHS["pages"] == "DataPool/Pages"
        for path in DEFAULT_RIG_CONTEXT_PATHS.values():
            assert not path.startswith("Patch/Fixtures"), path
            assert path != "DataPool/Presets", path


class TestRigContextReportsItsOwnCompleteness:
    """A capped list that looks complete is worse than no list.

    The responder caps a snapshot at CONFIG.max_children and sets ``truncated``;
    rig context used to read ``children`` and throw the rest away, so a rig with
    more groups than the cap reached the model as a SHORT list with no signal —
    and the model would then reason, confidently, over a show it could not see.
    """

    def test_a_capped_section_says_so_and_names_the_real_total(self):
        tree = dict(_RIG_TREE)
        capped = _snapshot(DEFAULT_RIG_CONTEXT_PATHS["groups"], [f"G{n}" for n in range(1, 25)])
        capped["truncated"] = True
        capped["node"] = {"name": "Groups", "class": "Groups", "childCount": 37}
        tree[DEFAULT_RIG_CONTEXT_PATHS["groups"]] = capped

        summary = _rig_summary(_registry(state_port=FakeStatePort(tree)))
        groups = summary["groups"]
        assert groups["truncated"] is True
        assert groups["total"] == 37
        assert len(groups["objects"]) == 24

    def test_a_complete_section_is_not_marked_truncated(self):
        summary = _rig_summary(_registry())
        assert summary["groups"]["truncated"] is False

    def test_a_responder_that_reports_no_total_does_not_get_one_invented(self):
        # Absence must read as unknown, never as "the count equals what I got".
        summary = _rig_summary(_registry())
        assert summary["groups"].get("total") is None


class TestRigContextOpensContainers:
    """Knowing a "Color" pool EXISTS says nothing about whether a colour is
    stored in it — and an empty pool is exactly the state where a recall
    silently produces nothing. Same for a page: its executors are the only
    surface that actually fires a look."""

    def test_preset_pool_contents_are_fetched(self):
        tree = dict(_RIG_TREE)
        tree["DataPool/PresetPools/1"] = _snapshot("DataPool/PresetPools/1", ["Full", "Half"])
        tree["DataPool/PresetPools/2"] = _snapshot("DataPool/PresetPools/2", [])

        summary = _rig_summary(_registry(state_port=FakeStatePort(tree)))
        pools = {p["no"]: p for p in summary["preset_pools"]["objects"]}
        assert pools[1]["contents"] == [{"no": 1, "name": "Full"}, {"no": 2, "name": "Half"}]

    def test_an_empty_container_is_distinguishable_from_an_unread_one(self):
        # The whole point: "verified empty" and "could not ask" must not look
        # the same, or the model cannot tell a show that needs setting up from
        # a console it failed to reach.
        tree = dict(_RIG_TREE)
        tree["DataPool/PresetPools/1"] = _snapshot("DataPool/PresetPools/1", [])
        del tree["DataPool/PresetPools/2"]  # deliberately absent -> the drill query raises

        summary = _rig_summary(_registry(state_port=FakeStatePort(tree)))
        pools = {p["no"]: p for p in summary["preset_pools"]["objects"]}
        assert pools[1]["contents"] == []
        assert pools[1].get("contents_unavailable") is not True
        assert pools[2].get("contents_unavailable") is True
        assert "contents" not in pools[2]

    def test_drilldown_is_bounded_and_says_when_it_stopped(self):
        # Each drill query is a UDP round trip through the gate + audit, so an
        # unbounded walk would make rig context cost scale with the showfile.
        many = [f"P{n}" for n in range(1, 40)]
        tree = dict(_RIG_TREE)
        tree[DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]] = _snapshot(
            DEFAULT_RIG_CONTEXT_PATHS["preset_pools"], many
        )
        for n in range(1, 40):
            tree[f"DataPool/PresetPools/{n}"] = _snapshot(f"DataPool/PresetPools/{n}", [])

        port = FakeStatePort(tree)
        summary = _rig_summary(_registry(state_port=port))
        drilled = sum(1 for q in port.queries if q.startswith("DataPool/PresetPools/"))
        assert drilled <= RIG_DRILLDOWN_QUERY_CAP
        assert summary["preset_pools"]["drilldown_capped"] is True

    def test_an_uncapped_walk_is_not_flagged_as_capped(self):
        tree = dict(_RIG_TREE)
        for n in (1, 2):
            tree[f"DataPool/PresetPools/{n}"] = _snapshot(f"DataPool/PresetPools/{n}", [])
        summary = _rig_summary(_registry(state_port=FakeStatePort(tree)))
        assert summary["preset_pools"].get("drilldown_capped") is not True


class TestGetRigContext:
    def test_exposes_real_pool_number_and_name(self):
        # AC-MVP-025 + AC-DEPLOY-020 ①: each object exposes its REAL pool
        # number ("no") AND name — not a bare positional array of names.
        # Every resolved section wraps its objects with the completeness
        # signal (truncated/total) — see TestRigContextReportsItsOwnCompleteness
        # for the shape's own contract; here only "objects" is asserted.
        registry = _registry()
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["fixtures"]["objects"] == [
            {"no": 1, "name": "Spot 1"},
            {"no": 2, "name": "Wash 1"},
            {"no": 3, "name": "Wash 2"},
        ]
        assert summary["groups"]["objects"] == [
            {"no": 1, "name": "Vocals"},
            {"no": 2, "name": "Wash All"},
        ]
        assert summary["preset_pools"]["objects"] == [
            {"no": 1, "name": "Dimmer", "contents": []},
            {"no": 2, "name": "Color", "contents": []},
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
        assert summary["groups"]["objects"] == [
            {"no": 1, "name": "Vocals"},
            {"no": 2, "name": "Wash All"},
            {"no": 7, "name": "Big Spot"},
        ]
        group_numbers = {entry["no"] for entry in summary["groups"]["objects"]}
        assert group_numbers == {1, 2, 7}
        assert 3 not in group_numbers  # the hallucinated "Group 3" is absent
        assert execution.result.is_error is False

    def test_child_missing_pool_number_degrades_to_name_only(self):
        # A child lacking ``i`` degrades to a name-only entry rather than
        # crashing or emitting a null pool number.
        tree = dict(_RIG_TREE)
        tree[DEFAULT_RIG_CONTEXT_PATHS["fixtures"]] = {
            "v": 1,
            "kind": "state",
            "path": DEFAULT_RIG_CONTEXT_PATHS["fixtures"],
            "children": [{"name": "Nameless"}, {"i": 4, "name": "Spot 4"}],
        }
        registry = _registry(state_port=FakeStatePort(tree))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["fixtures"]["objects"] == [{"name": "Nameless"}, {"no": 4, "name": "Spot 4"}]
        assert execution.result.is_error is False

    def test_missing_section_is_reported_not_fatal(self):
        tree = dict(_RIG_TREE)
        del tree[DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]]
        registry = _registry(state_port=FakeStatePort(tree))
        execution = registry.dispatch(_call("get_rig_context"))
        summary = json.loads(execution.result.content)
        assert summary["fixtures"]["objects"]  # healthy sections still present
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
        assert summary["preset_pools"]["objects"] == []
        assert summary["groups"]["reason"] == "path_not_resolved"
        assert execution.result.is_error is False


class TestRigContextDescription:
    """The description is the model's ONLY contract for reading the summary."""

    def _description(self) -> str:
        (definition,) = [d for d in _registry().definitions() if d.name == "get_rig_context"]
        return definition.description

    def test_preset_pools_are_described_as_types_with_contents_opened(self):
        # "DataPool/PresetPools" lists the preset TYPES (Dimmer, Position,
        # Color, ...); a depth-1 snapshot alone cannot reach what is STORED
        # inside each pool. Since the drilldown was added, get_rig_context
        # opens each pool itself — the description must say the contents ARE
        # included (as "contents"), not send the model to a manual query_state
        # round trip it no longer needs for the common case.
        text = self._description()
        assert "preset_pools" in text
        lowered = text.lower()
        assert "type" in lowered
        assert "contents" in lowered

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

    def test_every_default_section_is_named(self):
        # The model must know the whole surface it can see in one call, not
        # just the three original sections — sequences and pages (executors)
        # are how a look is actually stored and fired.
        text = self._description()
        for section in DEFAULT_RIG_CONTEXT_PATHS:
            assert section in text, f"{section!r} missing from get_rig_context description"

    def test_pages_are_described_as_the_executor_surface(self):
        lowered = self._description().lower()
        assert "executor" in lowered

    def test_truncation_signal_is_documented(self):
        # A short list with no completeness signal is worse than no list.
        lowered = self._description().lower()
        assert "truncated" in lowered
        assert "total" in lowered

    def test_drilldown_contents_are_documented(self):
        lowered = self._description().lower()
        assert "contents" in lowered
        assert "contents_unavailable" in lowered


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


# -- T-J: paperwork tools (build_patch_sheet / build_cue_sheet / build_preset_list) -


class _FakeInventoryPort:
    """State + property double for the fixture inventory (mirrors
    test_paperwork_patch_sheet.FakeInventoryPort — kept local so this file does
    not import a sibling test module)."""

    def __init__(self, states: dict[str, dict], properties: dict[tuple[str, str], dict]):
        self._states = states
        self._properties = properties

    def query_state(self, path: str) -> dict:
        if path not in self._states:
            raise LookupError(f"unknown state path: {path}")
        return self._states[path]

    def query_property(self, path: str, property_name: str) -> dict:
        key = (path, property_name)
        if key not in self._properties:
            raise LookupError(f"unknown property: {key}")
        return self._properties[key]


def _prop(value: str) -> dict:
    return {"ok": True, "value": value}


def _one_fixture_inventory_port() -> _FakeInventoryPort:
    from server.prechk.inventory import FIXTURE_ROOT

    states = {
        FIXTURE_ROOT: {
            "ok": True,
            "node": {"name": "Fixtures", "class": "Container", "childCount": 1},
            "children": [{"i": 1, "name": "Spot 1"}],
        }
    }
    properties = {
        (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
        (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Robe MegaPointe"),
        (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
        (f"{FIXTURE_ROOT}/1", "Name"): _prop("Spot 1"),
    }
    return _FakeInventoryPort(states, properties)


class TestBuildPatchSheetTool:
    def test_missing_property_port_is_a_structured_error(self):
        # A state_port with no query_property means build_toolset never adopts
        # a property_port — the tool must refuse, not silently answer "0 fixtures".
        registry = build_toolset(execution_port=ScriptedPort(), state_port=FakeStatePort({}))
        execution = registry.dispatch(_call("build_patch_sheet"))
        assert execution.result.is_error is True
        payload = json.loads(execution.result.content)
        assert "property_port" in payload["error"]

    def test_success_returns_a_path_and_a_summary_never_the_html(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.paperwork.output.resolve_paperwork_dir", lambda: tmp_path)
        registry = build_toolset(
            execution_port=ScriptedPort(), state_port=_one_fixture_inventory_port()
        )
        execution = registry.dispatch(_call("build_patch_sheet"))
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["fixture_count"] == 1
        assert payload["completeness"] == "complete"
        assert "<html" not in json.dumps(payload)
        written = Path(payload["path"])
        assert written.is_file()
        assert "<html" in written.read_text(encoding="utf-8")

    def test_an_unreadable_root_is_a_structured_error(self):
        from server.prechk.inventory import FIXTURE_ROOT

        registry = build_toolset(
            execution_port=ScriptedPort(),
            state_port=_FakeInventoryPort(
                {FIXTURE_ROOT: {"ok": False, "error": "no reply within 3.0s"}}, {}
            ),
        )
        execution = registry.dispatch(_call("build_patch_sheet"))
        assert execution.result.is_error is True


class TestBuildCueSheetTool:
    def _tree(self) -> dict[str, dict]:
        path = DEFAULT_RIG_CONTEXT_PATHS["sequences"]
        return {
            path: {"children": [{"i": 1, "name": "Main Show"}]},
            f"{path}/1": {"children": [{"i": 1, "name": "Cyan Wash"}]},
        }

    def test_success_returns_a_path_and_a_summary_never_the_html(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.paperwork.output.resolve_paperwork_dir", lambda: tmp_path)
        registry = build_toolset(
            execution_port=ScriptedPort(), state_port=FakeStatePort(self._tree())
        )
        execution = registry.dispatch(_call("build_cue_sheet"))
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["sequence_count"] == 1
        assert payload["cue_count"] == 1
        written = Path(payload["path"])
        assert written.is_file()
        assert "<html" in written.read_text(encoding="utf-8")

    def test_an_unreachable_console_is_a_structured_error(self):
        registry = build_toolset(execution_port=ScriptedPort(), state_port=FakeStatePort({}))
        execution = registry.dispatch(_call("build_cue_sheet"))
        assert execution.result.is_error is True


class TestBuildPresetListTool:
    def _tree(self) -> dict[str, dict]:
        path = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]
        return {
            path: {"children": [{"i": 1, "name": "Dimmer"}]},
            f"{path}/1": {"children": []},
        }

    def test_success_returns_a_path_and_a_summary_never_the_html(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.paperwork.output.resolve_paperwork_dir", lambda: tmp_path)
        registry = build_toolset(
            execution_port=ScriptedPort(), state_port=FakeStatePort(self._tree())
        )
        execution = registry.dispatch(_call("build_preset_list"))
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["pool_count"] == 1
        assert payload["preset_count"] == 0
        written = Path(payload["path"])
        assert written.is_file()

    def test_an_unreachable_console_is_a_structured_error(self):
        registry = build_toolset(execution_port=ScriptedPort(), state_port=FakeStatePort({}))
        execution = registry.dispatch(_call("build_preset_list"))
        assert execution.result.is_error is True


# -- T-J: plan_executor_layout (server/looks/layout.py wiring) ----------------

from server.looks.schema import AttributeValue, Look, LookLibrary  # noqa: E402


def _layout_look(look_id: str, display_name: str, *, dynamics: int) -> Look:
    return Look(
        look_id=look_id,
        display_name=display_name,
        genre="rock",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=(AttributeValue(name="Dimmer", value=80),),
    )


def _layout_library() -> LookLibrary:
    return LookLibrary(
        schema_version=1,
        looks=(
            _layout_look("intro", "Intro Wash", dynamics=1),
            _layout_look("verse", "Verse", dynamics=2),
        ),
    )


class TestPlanExecutorLayoutTool:
    def _registry(self, *, port=None, state=None):
        return build_toolset(
            execution_port=port or ScriptedPort(),
            state_port=state if state is not None else FakeStatePort({}),
            look_library=_layout_library(),
        )

    def test_unknown_genre_is_an_error_with_candidates(self):
        registry = self._registry()
        execution = registry.dispatch(
            _call("plan_executor_layout", {"genre": "재즈", "sequence_numbers": {"intro": 1}})
        )
        assert execution.result.is_error is True
        payload = json.loads(execution.result.content)
        assert "rock" in payload["candidates"]

    def test_missing_sequence_numbers_is_an_error(self):
        registry = self._registry()
        execution = registry.dispatch(_call("plan_executor_layout", {"genre": "rock"}))
        assert execution.result.is_error is True

    def test_places_looks_on_the_measured_page_one_addresses(self):
        state = FakeStatePort({"Executor 101": {"node": {}}, "Executor 102": {"node": {}}})
        registry = self._registry(state=state)
        execution = registry.dispatch(
            _call(
                "plan_executor_layout",
                {"genre": "rock", "sequence_numbers": {"intro": 11, "verse": 12}},
            )
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["executed"] is False
        assert [item["executor_no"] for item in payload["items"]] == [101, 102]
        assert [item["conflict"] for item in payload["items"]] == [False, False]
        assert "Assign Sequence 11 At Executor 101" in payload["commands"]
        assert "Label Sequence 11 'Intro Wash'" in payload["commands"]
        assert len(payload["commands"]) == 4

    def test_a_look_missing_a_sequence_number_is_skipped_not_guessed(self):
        state = FakeStatePort({"Executor 101": {"node": {}}})
        registry = self._registry(state=state)
        execution = registry.dispatch(
            _call(
                "plan_executor_layout",
                {"genre": "rock", "sequence_numbers": {"intro": 11}},
            )
        )
        payload = json.loads(execution.result.content)
        assert len(payload["items"]) == 1
        assert payload["skipped"] == [
            {
                "look_id": "verse",
                "reason": "sequence_not_provided",
                "detail": (
                    "no existing sequence number was supplied for look "
                    "'verse' — this planner does not create sequences"
                ),
            }
        ]

    def test_an_occupied_executor_is_flagged_and_excluded_from_commands(self):
        state = FakeStatePort(
            {"Executor 101": {"node": {"sequenceNo": 99}}, "Executor 102": {"node": {}}}
        )
        registry = self._registry(state=state)
        execution = registry.dispatch(
            _call(
                "plan_executor_layout",
                {"genre": "rock", "sequence_numbers": {"intro": 11, "verse": 12}},
            )
        )
        payload = json.loads(execution.result.content)
        assert payload["items"][0]["conflict"] is True
        assert payload["items"][0]["conflict_reason"] == "occupied"
        assert payload["items"][1]["conflict"] is False
        # only the non-conflicted item's two lines survive
        assert len(payload["commands"]) == 2
        assert all("Executor 101" not in c for c in payload["commands"])

    def test_an_unconfirmed_executor_is_treated_as_a_conflict_not_free(self):
        # Executor 101's state query is never answered by this port at all.
        state = FakeStatePort({})
        registry = self._registry(state=state)
        execution = registry.dispatch(
            _call("plan_executor_layout", {"genre": "rock", "sequence_numbers": {"intro": 11}})
        )
        payload = json.loads(execution.result.content)
        assert payload["items"][0]["conflict"] is True
        assert payload["items"][0]["conflict_reason"] == "unconfirmed"
        assert payload["commands"] == []

    def test_never_sends_anything_to_the_console(self):
        port = ScriptedPort()
        state = FakeStatePort({"Executor 101": {"node": {}}, "Executor 102": {"node": {}}})
        registry = self._registry(port=port, state=state)
        registry.dispatch(
            _call(
                "plan_executor_layout",
                {"genre": "rock", "sequence_numbers": {"intro": 11, "verse": 12}},
            )
        )
        assert port.executed == []
