"""Pre-check tool wiring tests (M6 — AC-PRECHK-014).

The new tool is a model-reachable entry point, not a second execution surface.
Three properties are fixed here:

  * it is registered in all three places, checked by DISPATCH -- a dict lookup
    would pass while ``TOOL_NAMES`` was missing the name, and ``TOOL_NAMES`` is
    what the provider advertises;
  * console speech rides ``run_commands`` and therefore the bundle gate. The
    handler never touches ``execution_port``, so a gate hold cannot be bypassed
    by routing around it (REQ-PRECHK-018);
  * the parameter schema carries no rig identifiers. The handler reads the rig
    itself, which is the only way the caller cannot point it at a fixture, a
    slot, or an address that the SPEC forbids selecting.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.prechk.inventory import FIXTURE_ROOT, PROPERTY_WHITELIST

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_SOURCE = PROJECT_ROOT / "server" / "orchestrator" / "tools.py"

TOOL = "precheck_patch"

_FIXTURES = {
    1: {"Patch": "1.001", "FixtureType": "FixtureType 1", "Mode": "1 Mode 1", "Name": "MMX 1"},
    2: {"Patch": "1.001", "FixtureType": "FixtureType 1", "Mode": "1 Mode 1", "Name": "MMX 2"},
    3: {"Patch": "2.001", "FixtureType": "FixtureType 1", "Mode": "1 Mode 1", "Name": "MMX 3"},
}


class RigPort:
    """State + property double covering the fixture root, groups and macros."""

    def __init__(self, *, fixtures=None, groups=(11, 12), macros=(1,)):
        self.fixtures = _FIXTURES if fixtures is None else fixtures
        self.groups = groups
        self.macros = macros
        self.state_calls: list[str] = []
        self.property_calls: list[tuple[str, str]] = []

    def _children(self, indices):
        return [{"i": i, "name": f"obj {i}", "class": "Object"} for i in indices]

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path == FIXTURE_ROOT:
            children = [
                {"i": slot, "name": self.fixtures[slot]["Name"], "class": "Fixture"}
                for slot in sorted(self.fixtures)
            ]
            return {
                "ok": True,
                "path": path,
                "node": {"name": "Fixtures", "class": "Fixtures", "childCount": len(children)},
                "children": children,
                "truncated": False,
            }
        if path == "DataPool/Groups":
            children = [{"i": no, "name": f"Group {no}", "class": "Group"} for no in self.groups]
            return {
                "ok": True,
                "path": path,
                "node": {"name": "Groups", "class": "Groups", "childCount": len(children)},
                "children": children,
                "truncated": False,
            }
        if path == "DataPool/Macros":
            children = self._children(self.macros)
            return {
                "ok": True,
                "path": path,
                "node": {"name": "Macros", "class": "Macros", "childCount": len(children)},
                "children": children,
                "truncated": False,
            }
        raise RuntimeError(f"unexpected state path: {path}")

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        slot = int(path.rsplit("/", 1)[1])
        value = self.fixtures[slot].get(property_name)
        if value is None:
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}
        return {"ok": True, "path": path, "property": property_name, "value": value}


class RecordingExecutionPort:
    def __init__(self):
        self.executed: list[str] = []

    def execute(self, command: str):
        from server.orchestrator.ports import ExecutionResult

        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


@dataclass(frozen=True)
class _Decision:
    """Per-command row shaped like the gate's own decision rows."""

    command: str
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class _Screen:
    cleared: bool
    status: str
    notice: str
    commands: tuple[_Decision, ...]


class HoldingGate:
    """Bundle gate that never clears — the hold path must survive the tool."""

    def __init__(self):
        self.screened: list[list[str]] = []

    def screen(self, commands):
        self.screened.append(list(commands))
        return _Screen(
            cleared=False,
            status="held",
            notice="사람 승인 대기",
            commands=tuple(
                _Decision(command=c, status="held", reasons=("승인 필요",)) for c in commands
            ),
        )


class ClearingGate:
    def __init__(self):
        self.screened: list[list[str]] = []

    def screen(self, commands):
        self.screened.append(list(commands))
        return _Screen(cleared=True, status="cleared", notice="", commands=())


def _registry(*, rig=None, port=None, gate=None):
    rig = rig or RigPort()
    return build_toolset(
        execution_port=port or RecordingExecutionPort(),
        state_port=rig,
        property_port=rig,
        bundle_gate=gate,
    )


def _dispatch(registry, **arguments):
    return registry.dispatch(ToolCall(id="p1", name=TOOL, arguments=arguments))


class TestRegistration:
    """AC-PRECHK-014 ① — all three registries, proven by dispatch."""

    def test_the_name_is_in_the_closed_tool_name_tuple(self):
        assert TOOL in TOOL_NAMES

    def test_the_definition_is_advertised(self):
        names = {definition.name for definition in _registry().definitions()}
        assert TOOL in names

    def test_dispatch_reaches_a_handler(self):
        execution = _dispatch(_registry())
        # Dispatch, not a dict lookup: a missing TOOL_NAMES entry still resolves
        # in the handler map, so only dispatch proves the whole chain.
        assert execution.result.name == TOOL
        assert execution.result.is_error is False

    def test_every_advertised_name_is_dispatchable(self):
        registry = _registry()
        advertised = {definition.name for definition in registry.definitions()}
        assert advertised == set(TOOL_NAMES)


class TestParameterSchemaCarriesNoRigIdentifiers:
    """AC-PRECHK-014 ③ — the handler reads the rig; the caller cannot aim it."""

    def _schema(self):
        for definition in _registry().definitions():
            if definition.name == TOOL:
                return definition.parameters
        raise AssertionError(f"{TOOL} is not advertised")

    def test_no_group_pool_slot_fixture_or_address_parameter(self):
        schema = self._schema()
        properties = schema.get("properties", {})
        assert properties, "schema has no properties — the check would be vacuous"
        banned = ("group", "pool", "slot", "fixture", "address", "universe", "fid")
        for name in properties:
            lowered = name.lower()
            assert not any(word in lowered for word in banned), (
                f"{TOOL} takes a rig identifier: {name}"
            )

    def test_the_schema_is_a_closed_object(self):
        schema = self._schema()
        assert schema.get("type") == "object"
        assert schema.get("additionalProperties") is False


class TestSingleExecutionPath:
    """AC-PRECHK-014 ② — no second execution surface, no gate bypass."""

    def test_the_handler_never_touches_the_execution_port_directly(self):
        rig = RigPort()
        port = RecordingExecutionPort()
        gate = ClearingGate()
        _dispatch(_registry(rig=rig, port=port, gate=gate), create_macro=True)
        # Every command reached the port THROUGH run_commands, so the gate saw
        # the whole bundle first.
        assert gate.screened, "the gate never saw a bundle"
        assert port.executed, "no command was executed — the check would be vacuous"
        assert gate.screened[0] == port.executed

    def test_a_gate_hold_stops_every_command_and_is_an_error(self):
        rig = RigPort()
        port = RecordingExecutionPort()
        gate = HoldingGate()
        execution = _dispatch(_registry(rig=rig, port=port, gate=gate), create_macro=True)
        assert gate.screened, "the gate never saw a bundle"
        assert port.executed == []
        # AC-PRECHK-014 ④: a gate hold IS an error — the model must react.
        assert execution.result.is_error is True

    def test_the_report_survives_a_gate_hold(self):
        execution = _dispatch(
            _registry(gate=HoldingGate()),
            create_macro=True,
        )
        payload = json.loads(execution.result.content)
        # The precheck answer is not lost because the macro was held.
        assert payload["inventory"]["observed_count"] == 3
        assert payload["collisions"]["address_duplicates"]

    def test_no_new_rest_route_or_websocket_type_was_added(self):
        source = TOOLS_SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        identifiers = [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)] + [
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        ]
        assert len(identifiers) > 100, "identifier scan collected too little to be meaningful"
        for banned in ("APIRouter", "add_api_route", "websocket", "WebSocket"):
            assert banned not in identifiers, f"tools.py grew a transport surface: {banned}"

    def test_the_execution_port_is_only_named_inside_run_commands(self):
        tree = ast.parse(TOOLS_SOURCE.read_text(encoding="utf-8"))
        offenders: list[str] = []
        found = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Attribute)
                    and inner.attr == "execute"
                    and isinstance(inner.value, ast.Name)
                    and inner.value.id == "execution_port"
                ):
                    found += 1
                    if node.name not in ("run_commands", "build_toolset"):
                        offenders.append(node.name)
        assert found >= 1, "scan found no execution_port.execute call at all"
        assert offenders == [], f"execution_port reached outside run_commands: {offenders}"


class TestReportAndMacroReachTheModel:
    def test_the_report_is_returned_without_a_macro_by_default(self):
        execution = _dispatch(_registry())
        payload = json.loads(execution.result.content)
        assert "macro" not in payload
        assert payload["summary_ko"].strip()
        assert payload["collisions"]["address_duplicates"], "planted duplicate not detected"

    def test_the_whitelisted_properties_are_the_only_ones_read(self):
        rig = RigPort()
        _dispatch(_registry(rig=rig))
        assert rig.property_calls, "no property was read — the check would be vacuous"
        assert {name for _, name in rig.property_calls} <= set(PROPERTY_WHITELIST)

    def test_no_generated_command_selects_a_fixture(self):
        rig = RigPort()
        port = RecordingExecutionPort()
        _dispatch(_registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True)
        assert port.executed, "no command was executed — the check would be vacuous"
        assert not [c for c in port.executed if "Fixture" in c]

    def test_the_macro_slot_is_chosen_free_not_taken(self):
        rig = RigPort(macros=(1, 2, 3))
        port = RecordingExecutionPort()
        _dispatch(_registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True)
        stores = [c for c in port.executed if c.startswith("Store Macro ")]
        assert stores, "no macro was stored"
        chosen = {int(c.split()[2].split(".")[0]) for c in stores}
        assert chosen == {4}, f"a taken macro slot was chosen: {chosen}"

    def test_an_empty_group_pool_answers_with_a_reason_and_is_not_an_error(self):
        rig = RigPort(groups=())
        execution = _dispatch(_registry(rig=rig, gate=ClearingGate()), create_macro=True)
        payload = json.loads(execution.result.content)
        assert payload["macro"]["created"] is False
        assert payload["macro"]["commands"] == []
        assert payload["macro"]["reason"].strip()
        # AC-PRECHK-014 ④: an answer-shaped failure is NOT an error.
        assert execution.result.is_error is False
        assert "macro_no_groups" in [row["kind"] for row in payload["skipped_checks"]]

    def test_the_pair_count_follows_the_group_count(self):
        for groups in ((11,), (11, 12), (11, 12, 13, 14)):
            rig = RigPort(groups=groups)
            port = RecordingExecutionPort()
            _dispatch(_registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True)
            payloads = [c for c in port.executed if c.startswith("Set Macro ")]
            assert len(payloads) == 2 * len(groups), (
                f"{len(groups)} groups produced {len(payloads)} lines"
            )


class TestErrorConvention:
    """AC-PRECHK-014 ④ — correctable mistakes error, answers do not."""

    def test_a_bad_argument_type_is_an_error(self):
        execution = _dispatch(_registry(), create_macro="yes")
        assert execution.result.is_error is True
        assert "create_macro" in execution.result.content

    def test_a_narrow_state_port_yields_an_error_not_a_silent_empty_report(self):
        class StateOnly:
            """A pre-M1 double: it can enumerate but cannot read a property."""

            def query_state(self, path: str) -> dict:
                return RigPort().query_state(path)

        registry = build_toolset(execution_port=RecordingExecutionPort(), state_port=StateOnly())
        execution = _dispatch(registry)
        # A toolset without the property capability must SAY so rather than
        # report zero fixtures, which would read as a clean rig.
        assert execution.result.is_error is True
        assert "property" in execution.result.content

    def test_an_unreadable_fixture_root_is_an_error(self):
        class DeadRoot(RigPort):
            def query_state(self, path: str) -> dict:
                if path == FIXTURE_ROOT:
                    return {"ok": False, "path": path, "error": "path segment not found"}
                return super().query_state(path)

        execution = _dispatch(_registry(rig=DeadRoot()))
        assert execution.result.is_error is True

    def test_a_read_failure_inside_a_fixture_is_reported_not_raised(self):
        fixtures = {
            1: {"Patch": "1.001", "FixtureType": "FixtureType 1", "Mode": "1 Mode 1", "Name": "A"},
            2: {"Patch": None, "FixtureType": "FixtureType 1", "Mode": "1 Mode 1", "Name": "B"},
        }
        execution = _dispatch(_registry(rig=RigPort(fixtures=fixtures)))
        payload = json.loads(execution.result.content)
        assert payload["read_failures"], "the unreadable property vanished"
        # One bad property must not lose the readable fixture.
        assert payload["inventory"]["observed_count"] == 2
        assert execution.result.is_error is False
