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
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS, TOOL_NAMES, build_toolset
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
