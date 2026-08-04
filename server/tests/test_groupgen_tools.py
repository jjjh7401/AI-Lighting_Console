"""``classify_arrangement_topology`` / ``create_arrangement_groups`` tool tests
(SPEC-COPILOT-GROUPGEN-001 M3 — REQ-GROUPGEN-028, design.md §7/§8/§10).

Two invariants this file pins with mutation-required coverage:

* **Tool-layer approval is structural, not advisory** (design.md §7.2). There
  is no code path from ``create_arrangement_groups`` to a console send that
  does not pass through ``group_approval_port.request_approval(...)`` and
  observe ``True`` first. Deleting that check must turn a "denied" test RED
  (the execution port would then record sends it must never see).
* **Policy (c)** (design.md §10 게이트 A): ``unverified`` always names
  ``"membership"`` — a structural field, never prose — because grandMA3
  exposes no channel to read group membership back. What IS verified after a
  write is the slot's existence and its label, never who is in it.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    TOOL_NAMES,
    ExecutionContext,
    build_toolset,
)
from server.safety.approval import ApprovalRequest

FIXTURES_PATH = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]
GROUPS_PATH = DEFAULT_RIG_CONTEXT_PATHS["groups"]

CLASSIFY = "classify_arrangement_topology"
CREATE = "create_arrangement_groups"


class RecordingExecutionPort:
    """Records every command it is asked to fire — nothing else."""

    def __init__(self):
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class FakeConsole:
    """A single state + property double covering the fixture patch, the group
    pool and a group slot — configured per test via plain dicts, mirroring
    ``test_spatial_context.py::SpatialRig`` / ``test_tools.py::_FakeInventoryPort``.
    """

    def __init__(self, states: dict[str, dict], properties: dict[tuple[str, str], dict]):
        self._states = states
        self._properties = properties
        self.state_calls: list[str] = []
        self.property_calls: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path not in self._states:
            raise LookupError(f"unknown object path: {path}")
        return self._states[path]

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        key = (path, property_name)
        if key not in self._properties:
            return {"ok": False, "error": f"property not readable: {property_name}"}
        return self._properties[key]


def _fixture_props(fid: int, x: str, y: str = "0.0", z: str = "0.0") -> dict[str, dict]:
    return {
        "fid": {"ok": True, "value": str(fid)},
        "posx": {"ok": True, "value": x},
        "posy": {"ok": True, "value": y},
        "posz": {"ok": True, "value": z},
    }


#: Four fixtures, two clear x-axis clusters, with enough y-jitter that
#: `depth_rows` is NOT confident (otherwise a flat y=0 rig makes `depth_rows`
#: win by default) and NOT mirror-symmetric (so `bilateral_pairs` never
#: contends either) — live-checked to select `lateral_split` unambiguously.
_LATERAL_FIXTURES = (
    (1, "-5.0", "0.0"),
    (2, "-4.0", "1.0"),
    (3, "4.0", "0.5"),
    (4, "5.0", "1.5"),
)


def _lateral_pair_console(*, groups: dict[str, dict] | None = None) -> FakeConsole:
    """Four fixtures split on x — a confident ``lateral_split`` topology."""
    fixtures_state = {
        FIXTURES_PATH: {
            "ok": True,
            "truncated": False,
            "node": {"childCount": len(_LATERAL_FIXTURES)},
            "children": [
                {"i": slot, "name": f"Spot {slot}"} for slot in range(1, len(_LATERAL_FIXTURES) + 1)
            ],
        }
    }
    properties: dict[tuple[str, str], dict] = {}
    for slot, (fid, x, y) in enumerate(_LATERAL_FIXTURES, start=1):
        for prop, read in _fixture_props(fid, x, y).items():
            properties[(f"{FIXTURES_PATH}/{slot}", prop)] = read
    states = dict(fixtures_state)
    if groups is not None:
        states.update(groups)
    return FakeConsole(states, properties)


def _empty_group_pool(occupied: tuple[int, ...] = ()) -> dict[str, dict]:
    return {
        GROUPS_PATH: {
            "ok": True,
            "truncated": False,
            "node": {"childCount": len(occupied)},
            "children": [{"i": n, "name": f"Existing {n}"} for n in occupied],
        }
    }


def _call(name: str, arguments: dict | None = None, call_id: str = "call-1") -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments or {})


class ScriptedApprovalPort:
    """In-memory ``ApprovalPort`` double — records every request it saw."""

    def __init__(self, *, approve: bool):
        self.approve = approve
        self.requests: list[ApprovalRequest] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        self.requests.append(request)
        return self.approve


# -- registration -------------------------------------------------------------


class TestRegistration:
    def test_both_tools_are_registered_and_dispatchable(self):
        assert CLASSIFY in TOOL_NAMES
        assert CREATE in TOOL_NAMES
        registry = build_toolset(
            execution_port=RecordingExecutionPort(), state_port=_lateral_pair_console()
        )
        names = {definition.name for definition in registry.definitions()}
        assert CLASSIFY in names
        assert CREATE in names


# -- classify_arrangement_topology (read-only) --------------------------------


class TestClassifyArrangementTopology:
    def test_is_read_only_and_names_the_selected_topology(self):
        console = _lateral_pair_console()
        port = RecordingExecutionPort()
        registry = build_toolset(execution_port=port, state_port=console)
        execution = registry.dispatch(_call(CLASSIFY))
        assert execution.result.is_error is False
        assert port.executed == []  # READ tool sends nothing, ever

        payload = json.loads(execution.result.content)
        assert payload["topology"]["selected"]["kind"] == "lateral_split"
        assert payload["fixture_types"] is None
        suggested = {group["name"]: tuple(group["fids"]) for group in payload["suggested_groups"]}
        assert suggested == {"GEO Stage Right": (1, 2), "GEO Stage Left": (3, 4)}

    def test_fixture_type_records_add_a_species_axis_without_reading_the_console(self):
        console = _lateral_pair_console()
        port = RecordingExecutionPort()
        registry = build_toolset(execution_port=port, state_port=console)
        execution = registry.dispatch(
            _call(
                CLASSIFY,
                arguments={
                    "fixture_type_records": [
                        {"fid": 1, "manufacturer": "Robe", "type_name": "Robin MMX Spot"},
                        {"fid": 2, "manufacturer": "Chauvet", "type_name": "Rogue R2"},
                    ]
                },
            )
        )
        assert execution.result.is_error is False
        assert port.executed == []
        payload = json.loads(execution.result.content)
        assert payload["fixture_types"]["reason"] is None
        names = {group["name"] for group in payload["suggested_groups"]}
        # No "GEO " prefix on the type axis — that prefix is reserved for the
        # geometric axes (design.md §4.1 "종류" row / §D-Q3).
        assert "Robin MMX Spot" in names
        assert "Robe" in names
        assert not any(name.startswith("GEO Robe") for name in names)

    def test_full_coverage_rig_reports_complete_and_not_partial(self):
        console = _lateral_pair_console()
        registry = build_toolset(execution_port=RecordingExecutionPort(), state_port=console)
        execution = registry.dispatch(_call(CLASSIFY))
        payload = json.loads(execution.result.content)
        assert payload["coverage"] == {"judged": 4, "of": 4, "complete": True}
        assert payload["topology_partial"] is False
        assert payload["topology"]["partial"] is False
        for group in payload["suggested_groups"]:
            assert group["axis"] == "geometry"
            assert group["topology_partial"] is False

    def test_truncated_rig_read_reports_partial_coverage_and_lowconfidence_flag(self):
        """REQ-GROUPGEN-024 amendment (2026-08-04) — the DISCRIMINATE-path
        guard. Mutation-required: removing 'coverage'/'topology_partial'
        population must turn this test RED (a KeyError or a wrong boolean).
        """
        fixtures_state = {
            FIXTURES_PATH: {
                "ok": True,
                "truncated": True,
                "node": {"childCount": 39},
                "children": [{"i": slot, "name": f"Spot {slot}"} for slot in range(1, 19)],
            }
        }
        properties: dict[tuple[str, str], dict] = {}
        for slot in range(1, 19):
            for prop, read in _fixture_props(slot, str(float(slot))).items():
                properties[(f"{FIXTURES_PATH}/{slot}", prop)] = read
        console = FakeConsole(fixtures_state, properties)
        registry = build_toolset(execution_port=RecordingExecutionPort(), state_port=console)
        execution = registry.dispatch(_call(CLASSIFY))
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["coverage"] == {"judged": 18, "of": 39, "complete": False}
        assert payload["topology_partial"] is True
        assert payload["topology_partial_reason"]
        assert payload["topology"]["partial"] is True
        assert payload["topology"]["partial_reason"]
        for group in payload["suggested_groups"]:
            assert group["axis"] == "geometry"
            assert group["topology_partial"] is True

    def test_species_axis_groups_are_independent_of_rig_read_coverage(self):
        """The type axis (fixture_type_records) is caller-supplied and MUST
        NOT inherit a topology_partial flag it has no relationship to."""
        fixtures_state = {
            FIXTURES_PATH: {
                "ok": True,
                "truncated": True,
                "node": {"childCount": 39},
                "children": [{"i": slot, "name": f"Spot {slot}"} for slot in range(1, 19)],
            }
        }
        properties: dict[tuple[str, str], dict] = {}
        for slot in range(1, 19):
            for prop, read in _fixture_props(slot, str(float(slot))).items():
                properties[(f"{FIXTURES_PATH}/{slot}", prop)] = read
        console = FakeConsole(fixtures_state, properties)
        registry = build_toolset(execution_port=RecordingExecutionPort(), state_port=console)
        execution = registry.dispatch(
            _call(
                CLASSIFY,
                arguments={
                    "fixture_type_records": [
                        {"fid": 1, "manufacturer": "Robe", "type_name": "Robin MMX Spot"},
                        {"fid": 2, "manufacturer": "Chauvet", "type_name": "Rogue R2"},
                    ]
                },
            )
        )
        payload = json.loads(execution.result.content)
        assert payload["topology_partial"] is True  # the geometric axis IS partial
        species_groups = [g for g in payload["suggested_groups"] if g["axis"] == "species"]
        assert species_groups
        for group in species_groups:
            assert "topology_partial" not in group

    def test_missing_property_port_is_a_structured_error(self):
        class StateOnly:
            def query_state(self, path: str) -> dict:
                raise AssertionError("must not be reached without a property port")

        registry = build_toolset(execution_port=RecordingExecutionPort(), state_port=StateOnly())
        execution = registry.dispatch(_call(CLASSIFY))
        assert execution.result.is_error is True
        assert "property_port" in json.loads(execution.result.content)["error"]

    def test_malformed_fixture_type_records_is_a_structured_error_and_sends_nothing(self):
        console = _lateral_pair_console()
        port = RecordingExecutionPort()
        registry = build_toolset(execution_port=port, state_port=console)
        execution = registry.dispatch(
            _call(CLASSIFY, arguments={"fixture_type_records": "not-a-list"})
        )
        assert execution.result.is_error is True
        assert port.executed == []


# -- create_arrangement_groups: structural approval enforcement --------------


class TestCreateArrangementGroupsApproval:
    """design.md §7.2 [HARD]: no path to a send exists without an observed
    ``True`` from ``group_approval_port.request_approval``."""

    def _args(self) -> dict:
        return {"groups": [{"name": "GEO Stage Right", "fids": [1]}]}

    def test_no_approval_port_wired_denies_by_default_and_sends_nothing(self):
        # DenyAllApprovalPort is the fail-closed default (design.md §7.2 ②) —
        # omitting group_approval_port must NOT read as "pre-approved".
        console = _lateral_pair_console(groups=_empty_group_pool())
        port = RecordingExecutionPort()
        registry = build_toolset(execution_port=port, state_port=console)
        execution = registry.dispatch(_call(CREATE, arguments=self._args()))
        assert execution.result.is_error is False  # a demotion, not a failure
        assert port.executed == []
        payload = json.loads(execution.result.content)
        assert payload["status"] == "proposal"
        assert payload["executed"] is False
        assert len(payload["plan"]) == 1

    def test_approval_withheld_sends_nothing_even_though_the_port_was_asked(self):
        console = _lateral_pair_console(groups=_empty_group_pool())
        port = RecordingExecutionPort()
        approval = ScriptedApprovalPort(approve=False)
        registry = build_toolset(
            execution_port=port, state_port=console, group_approval_port=approval
        )
        execution = registry.dispatch(_call(CREATE, arguments=self._args()))
        assert execution.result.is_error is False
        assert port.executed == []
        assert len(approval.requests) == 1  # the port WAS called — not bypassed
        payload = json.loads(execution.result.content)
        assert payload["status"] == "proposal"

    def test_approval_granted_fires_exactly_the_planned_commands(self):
        groups = _empty_group_pool()
        states = dict(groups)
        # Pre-seed the slot the write will land on (slot 1, the sole empty
        # slot in an empty pool) so the post-write re-query succeeds.
        states[f"{GROUPS_PATH}/1"] = {"ok": True}
        console = _lateral_pair_console(groups=states)
        console._properties[(f"{GROUPS_PATH}/1", "Name")] = {
            "ok": True,
            "value": "GEO Stage Right",
        }
        port = RecordingExecutionPort()
        approval = ScriptedApprovalPort(approve=True)
        registry = build_toolset(
            execution_port=port, state_port=console, group_approval_port=approval
        )
        execution = registry.dispatch(_call(CREATE, arguments=self._args()))
        assert len(approval.requests) == 1
        assert port.executed == [
            "ClearAll",
            "Fixture 1",
            "Store Group 1",
            "Label Group 1 'GEO Stage Right'",
            "ClearAll",
        ]
        payload = json.loads(execution.result.content)
        assert payload["status"] == "created"
        assert payload["succeeded"] is True
        assert execution.result.is_error is False

    def test_removing_the_approval_check_would_go_red(self):
        # A behavioral pin, not a real deletion: asserts the exact property a
        # removed approval-check mutation breaks — that a denied approval
        # still sends nothing. If the structural check is ever bypassed
        # (e.g. replaced by `approved = True`), `port.executed` below stops
        # being empty and this test fails.
        console = _lateral_pair_console(groups=_empty_group_pool())
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=False),
        )
        registry.dispatch(_call(CREATE, arguments=self._args()))
        assert port.executed == []


# -- create_arrangement_groups: policy (c) — membership stays unverified -----


class TestCreateArrangementGroupsPolicyC:
    def test_unverified_always_names_membership_on_a_proposal(self):
        console = _lateral_pair_console(groups=_empty_group_pool())
        registry = build_toolset(execution_port=RecordingExecutionPort(), state_port=console)
        execution = registry.dispatch(
            _call(CREATE, arguments={"groups": [{"name": "GEO Stage Right", "fids": [1]}]})
        )
        payload = json.loads(execution.result.content)
        assert payload["unverified"] == ["membership"]
        assert payload["unverified_reason"]
        assert payload["human_check_commands"] == ["Group 1"]

    def test_unverified_always_names_membership_on_a_successful_write(self):
        states = _empty_group_pool()
        states[f"{GROUPS_PATH}/1"] = {"ok": True}
        console = _lateral_pair_console(groups=states)
        console._properties[(f"{GROUPS_PATH}/1", "Name")] = {
            "ok": True,
            "value": "GEO Stage Right",
        }
        registry = build_toolset(
            execution_port=RecordingExecutionPort(),
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(
            _call(CREATE, arguments={"groups": [{"name": "GEO Stage Right", "fids": [1]}]})
        )
        payload = json.loads(execution.result.content)
        assert payload["unverified"] == ["membership"]
        # Only the slot's existence and its label are verified — never who is
        # inside it.
        assert payload["verified_steps"][0]["slot_exists"] is True
        assert payload["verified_steps"][0]["name_verified"] is True
        assert "fids_verified" not in payload["verified_steps"][0]

    def test_ok_true_is_never_the_only_evidence_a_mismatched_label_fails_verification(self):
        states = _empty_group_pool()
        states[f"{GROUPS_PATH}/1"] = {"ok": True}
        console = _lateral_pair_console(groups=states)
        # Console answers OK but the label read back is wrong — the write.py
        # write chain always sends the correct label, so this simulates the
        # exact console failure mode research.md documents elsewhere: an OK
        # reply that is not evidence of what actually landed.
        console._properties[(f"{GROUPS_PATH}/1", "Name")] = {"ok": True, "value": "Wrong Name"}
        registry = build_toolset(
            execution_port=RecordingExecutionPort(),
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(
            _call(CREATE, arguments={"groups": [{"name": "GEO Stage Right", "fids": [1]}]})
        )
        payload = json.loads(execution.result.content)
        assert payload["status"] == "verification_failed"
        assert execution.result.is_error is True
        assert payload["verified_steps"][0]["name_verified"] is False


# -- create_arrangement_groups: fail-closed structural refusals --------------


class TestCreateArrangementGroupsRefusals:
    def test_missing_groups_argument_is_a_structured_error_and_sends_nothing(self):
        console = _lateral_pair_console(groups=_empty_group_pool())
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(_call(CREATE, arguments={}))
        assert execution.result.is_error is True
        assert port.executed == []

    def test_truncated_group_pool_refuses_the_whole_call(self):
        truncated_pool = {
            GROUPS_PATH: {"ok": True, "truncated": True, "children": []},
        }
        console = _lateral_pair_console(groups=truncated_pool)
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(
            _call(CREATE, arguments={"groups": [{"name": "GEO Stage Right", "fids": [1]}]})
        )
        assert execution.result.is_error is True
        assert "GROUP_POOL_TRUNCATED" in execution.result.content
        assert port.executed == []

    def test_truncated_fixture_container_never_blocks_an_explicit_fids_write(self):
        """REQ-GROUPGEN-024 amendment (2026-08-04) — LIVE-shape regression.

        The scenario: a 39-fixture rig where one UDP round trip only returns
        18 fixtures (``truncated: true``, real ``childCount`` 39). The write
        path consumes caller-supplied ``fids`` — not this listing — so the
        write must PROCEED, carrying the truncation as a structural notice
        rather than a refusal."""
        groups = _empty_group_pool()
        states = dict(groups)
        states[FIXTURES_PATH] = {
            "ok": True,
            "truncated": True,
            "node": {"childCount": 39},
            "children": [{"i": slot, "name": f"Spot {slot}"} for slot in range(1, 19)],
        }
        states[f"{GROUPS_PATH}/1"] = {"ok": True}
        console = FakeConsole(states, {(f"{GROUPS_PATH}/1", "Name"): {"ok": True, "value": "X"}})
        port = RecordingExecutionPort()
        approval = ScriptedApprovalPort(approve=True)
        registry = build_toolset(
            execution_port=port, state_port=console, group_approval_port=approval
        )
        execution = registry.dispatch(
            _call(CREATE, arguments={"groups": [{"name": "X", "fids": [3, 5, 7]}]})
        )
        assert execution.result.is_error is False
        assert port.executed  # the write actually fired — never refused
        payload = json.loads(execution.result.content)
        assert payload["status"] == "created"
        assert payload["fixture_list_truncated"] is True
        assert payload["fixture_list_truncated_reason"]

    def test_never_targets_an_occupied_slot(self):
        console = _lateral_pair_console(groups=_empty_group_pool(occupied=(1,)))
        console._states[f"{GROUPS_PATH}/2"] = {"ok": True}
        console._properties[(f"{GROUPS_PATH}/2", "Name")] = {
            "ok": True,
            "value": "GEO Stage Right",
        }
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        registry.dispatch(
            _call(CREATE, arguments={"groups": [{"name": "GEO Stage Right", "fids": [1]}]})
        )
        assert any("Store Group 2" in command for command in port.executed)
        assert not any("Store Group 1" in command for command in port.executed)


# -- create_arrangement_groups: ONE run_commands bundle PER GROUP ------------
#
# The defect this section pins: `run_commands` folds a line that already
# succeeded in the same bundle (or earlier in the same instruction turn) into
# `skipped_already_executed`, and a MULTI-fixture selection chain is NOT
# dedupe-exempt. Firing the whole plan as one bundle therefore dropped the
# second group's selection line and let `Store Group N` run against an empty
# programmer — the console answers ok, group membership is unreadable
# (progress.md §E.2.8), so the human approved one plan and the console
# received another, undetectably.


class FailingExecutionPort:
    """Records every command it is asked to fire, and fails exactly one."""

    def __init__(self, *, fail_on: str):
        self.fail_on = fail_on
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        if command == self.fail_on:
            return ExecutionResult(ok=False, detail="console refused the store")
        return ExecutionResult(ok=True, detail="OK")


def _writable_console(slots: dict[int, str]) -> FakeConsole:
    """A lateral rig with an EMPTY group pool whose target slots answer the
    post-write re-query with exactly the label the write chain will set."""
    states = _empty_group_pool()
    for slot in slots:
        states[f"{GROUPS_PATH}/{slot}"] = {"ok": True}
    console = _lateral_pair_console(groups=states)
    for slot, name in slots.items():
        console._properties[(f"{GROUPS_PATH}/{slot}", "Name")] = {"ok": True, "value": name}
    return console


#: The selection line for fids (1, 2, 3) — the multi-fixture form, which is
#: NOT dedupe-exempt (only a single bare `Fixture <operand>` is).
SELECTION_123 = "Fixture 1 + Fixture 2 + Fixture 3"


class TestCreateArrangementGroupsFiresOneBundlePerGroup:
    def test_the_multi_fixture_selection_line_is_not_dedupe_exempt(self):
        # The premise every test below rests on, asserted rather than assumed:
        # a ONE-fixture group was never affected (its `Fixture 1` IS exempt),
        # so a fixture-count-blind reading of these tests would misread them.
        from server.orchestrator.tools import _is_programmer_state

        assert _is_programmer_state("Fixture 1") is True
        assert _is_programmer_state(SELECTION_123) is False

    def test_two_groups_over_identical_fids_both_reach_the_console(self):
        """`classify_arrangement_topology` emits byte-identical fid tuples for
        two axes on any rig whose manufacturer:model mapping is 1:1, so this is
        an ORDINARY plan, not a contrived one."""
        console = _writable_console({1: "GEO Stage Right", 2: "GEO Stage Left"})
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(
            _call(
                CREATE,
                arguments={
                    "groups": [
                        {"name": "GEO Stage Right", "fids": [1, 2, 3]},
                        {"name": "GEO Stage Left", "fids": [1, 2, 3]},
                    ]
                },
            )
        )
        # The SECOND group's selection line reached the console — the whole
        # point. Asserted as full equality so a dropped, reordered or
        # duplicated line all fail here.
        assert port.executed == [
            "ClearAll",
            SELECTION_123,
            "Store Group 1",
            "Label Group 1 'GEO Stage Right'",
            "ClearAll",
            "ClearAll",
            SELECTION_123,
            "Store Group 2",
            "Label Group 2 'GEO Stage Left'",
            "ClearAll",
        ]
        payload = json.loads(execution.result.content)
        assert [entry["status"] for entry in payload["commands"]] == ["executed_ok"] * 10
        assert payload["status"] == "created"
        assert execution.result.is_error is False

    def test_what_the_human_approved_is_exactly_what_the_console_received(self):
        """The property the split exists to protect, stated directly: the
        approval card and the wire carry the same lines, in the same order."""
        console = _writable_console({1: "GEO Stage Right", 2: "GEO Stage Left"})
        port = RecordingExecutionPort()
        approval = ScriptedApprovalPort(approve=True)
        registry = build_toolset(
            execution_port=port, state_port=console, group_approval_port=approval
        )
        registry.dispatch(
            _call(
                CREATE,
                arguments={
                    "groups": [
                        {"name": "GEO Stage Right", "fids": [1, 2, 3]},
                        {"name": "GEO Stage Left", "fids": [1, 2, 3]},
                    ]
                },
            )
        )
        # ONE approval card for the whole plan — the execution split must not
        # fragment the human decision into one request per group.
        assert len(approval.requests) == 1
        assert [item.command for item in approval.requests[0].items] == port.executed

    def test_a_prior_tool_calls_identical_selection_never_folds_this_write(self):
        """`ExecutionContext.executed_ok` accumulates across every tool call in
        one instruction turn (runner.py:216, 222-223), so a self-correction
        retry alone (REQ-MVP-012) is enough to arm this — even for a plan that
        holds a SINGLE group."""
        console = _writable_console({1: "GEO Stage Right"})
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(
            _call(CREATE, arguments={"groups": [{"name": "GEO Stage Right", "fids": [1, 2, 3]}]}),
            ExecutionContext(executed_ok=frozenset({SELECTION_123})),
        )
        assert port.executed == [
            "ClearAll",
            SELECTION_123,
            "Store Group 1",
            "Label Group 1 'GEO Stage Right'",
            "ClearAll",
        ]
        payload = json.loads(execution.result.content)
        assert "skipped_already_executed" not in [entry["status"] for entry in payload["commands"]]
        assert payload["status"] == "created"

    def test_distinct_fid_groups_still_fire_every_command_in_plan_order(self):
        """Non-vacuity for the split: the ordinary N-group path is unchanged —
        same commands, same count, same order, same verified_steps."""
        console = _writable_console({1: "GEO A", 2: "GEO B", 3: "GEO C"})
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(
            _call(
                CREATE,
                arguments={
                    "groups": [
                        {"name": "GEO A", "fids": [1]},
                        {"name": "GEO B", "fids": [2]},
                        {"name": "GEO C", "fids": [3, 4]},
                    ]
                },
            )
        )
        assert port.executed == [
            "ClearAll",
            "Fixture 1",
            "Store Group 1",
            "Label Group 1 'GEO A'",
            "ClearAll",
            "ClearAll",
            "Fixture 2",
            "Store Group 2",
            "Label Group 2 'GEO B'",
            "ClearAll",
            "ClearAll",
            "Fixture 3 + Fixture 4",
            "Store Group 3",
            "Label Group 3 'GEO C'",
            "ClearAll",
        ]
        payload = json.loads(execution.result.content)
        assert payload["status"] == "created"
        assert payload["succeeded"] is True
        assert [entry["slot"] for entry in payload["verified_steps"]] == [1, 2, 3]
        # No partial-write bookkeeping leaks onto a clean success.
        assert "slot_outcomes" not in payload
        assert "partial_write" not in payload

    def test_a_failing_middle_bundle_stops_there_and_separates_written_slots(self):
        console = _writable_console({1: "GEO A", 2: "GEO B", 3: "GEO C"})
        port = FailingExecutionPort(fail_on="Store Group 2")
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(
            _call(
                CREATE,
                arguments={
                    "groups": [
                        {"name": "GEO A", "fids": [1]},
                        {"name": "GEO B", "fids": [2]},
                        {"name": "GEO C", "fids": [3, 4]},
                    ]
                },
            )
        )
        # Stopped AT the failure: group 3's chain never reached the console.
        assert port.executed[-1] == "Store Group 2"
        assert "Store Group 3" not in port.executed
        assert execution.result.is_error is True
        payload = json.loads(execution.result.content)
        assert payload["status"] == "failed"
        # Partial success never reads as success...
        assert payload["executed"] is False
        assert "succeeded" not in payload
        assert "verified_steps" not in payload
        # ...but which slots were written is still recoverable.
        assert payload["partial_write"] is True
        assert payload["slot_outcomes"] == [
            {"slot": 1, "name": "GEO A", "status": "executed"},
            {"slot": 2, "name": "GEO B", "status": "failed"},
            {"slot": 3, "name": "GEO C", "status": "not_attempted"},
        ]
        assert [entry["status"] for entry in payload["commands"]] == [
            *["executed_ok"] * 5,
            "executed_ok",
            "executed_ok",
            "failed",
            "not_executed",
            "not_executed",
            *["not_executed"] * 5,
        ]
        assert "1 of 3" in payload["error"]

    def test_a_first_bundle_failure_reports_no_written_slot_at_all(self):
        """The other side of ``partial_write``: nothing landed, so the flag
        must be False rather than a constant True."""
        console = _writable_console({1: "GEO A", 2: "GEO B"})
        port = FailingExecutionPort(fail_on="Store Group 1")
        registry = build_toolset(
            execution_port=port,
            state_port=console,
            group_approval_port=ScriptedApprovalPort(approve=True),
        )
        execution = registry.dispatch(
            _call(
                CREATE,
                arguments={
                    "groups": [
                        {"name": "GEO A", "fids": [1]},
                        {"name": "GEO B", "fids": [2]},
                    ]
                },
            )
        )
        payload = json.loads(execution.result.content)
        assert payload["partial_write"] is False
        assert [entry["status"] for entry in payload["slot_outcomes"]] == [
            "failed",
            "not_attempted",
        ]
        assert "0 of 2" in payload["error"]
