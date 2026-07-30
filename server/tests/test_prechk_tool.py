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
import re
from dataclasses import dataclass
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator import tools as tools_module
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.prechk.inventory import FIXTURE_ROOT, PROPERTY_WHITELIST
from server.prechk.macro import MacroResult

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

    def __init__(self, *, fixtures=None, groups=(11, 12), macros=(1,), macro_lines=None):
        self.fixtures = _FIXTURES if fixtures is None else fixtures
        self.groups = groups
        self.macros = macros
        # Stored macro-line command text, keyed by the object path a requery
        # names. Shared with :class:`MacroWritingExecutionPort` so a read-back
        # returns what a command actually wrote instead of a fabricated answer.
        self.macro_lines = {} if macro_lines is None else macro_lines
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
        if path.startswith("DataPool/Macros/"):
            if path in self.macro_lines:
                return {
                    "ok": True,
                    "path": path,
                    "property": property_name,
                    "value": self.macro_lines[path],
                }
            return {
                "ok": False,
                "path": path,
                "property": property_name,
                "error": "no reply within 3.0s",
            }
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


class MacroWritingExecutionPort(RecordingExecutionPort):
    """Execution port that actually STORES what a macro line writes.

    Without it, "the requery agrees with the authored command" would be checked
    against a double that invents the answer — a tautology. Here the value the
    read-back returns is the one the ``Set Macro`` command carried, so the
    assertion covers the round trip the M0 GO record measured live.
    """

    _SET_LINE = re.compile(r"^Set Macro (\d+)\.(\d+) Property 'Command' '(.*)'$")

    def __init__(self, store: dict[str, str]):
        super().__init__()
        self.store = store

    def execute(self, command: str):
        match = self._SET_LINE.match(command.strip())
        if match is not None:
            slot, line, payload = match.groups()
            self.store[f"DataPool/Macros/{slot}/{line}"] = payload
        return super().execute(command)


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


class LockedGate:
    """LiveLock is engaged: nothing is sent and the status says why.

    Distinct from :class:`HoldingGate` on purpose — ``AC-PRECHK-014`` ④ makes a
    hold an error (the model must react) and a lock an answer (the lock is doing
    its job). ``server/safety/gate.py`` reports the lock as ``status='locked'``.
    """

    def __init__(self):
        self.screened: list[list[str]] = []

    def screen(self, commands):
        self.screened.append(list(commands))
        return _Screen(
            cleared=False,
            status="locked",
            notice="라이브 락 — 송신하지 않았습니다",
            commands=tuple(
                _Decision(command=c, status="locked", reasons=("라이브 락",)) for c in commands
            ),
        )


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


class TestPoolReadFailuresAreNotRigFindings:
    """run-audit P1-2 · P1-3 — a failed read is never a statement about the rig."""

    def test_a_group_pool_read_failure_is_an_error_not_a_no_groups_answer(self):
        class DeadGroups(RigPort):
            def query_state(self, path: str) -> dict:
                if path == "DataPool/Groups":
                    return {"ok": False, "path": path, "error": "timeout"}
                return super().query_state(path)

        execution = _dispatch(_registry(rig=DeadGroups(), gate=ClearingGate()), create_macro=True)
        # acceptance.md §D: 조회 실패 -> is_error=True (정정 가능).
        assert execution.result.is_error is True
        # And it must NOT claim the rig has no groups -- we never read the pool.
        assert "그룹이 없어" not in execution.result.content

    def test_a_group_pool_transport_failure_is_an_error_too(self):
        class RaisingGroups(RigPort):
            def query_state(self, path: str) -> dict:
                if path == "DataPool/Groups":
                    raise RuntimeError("no reply within 3.0s")
                return super().query_state(path)

        execution = _dispatch(
            _registry(rig=RaisingGroups(), gate=ClearingGate()), create_macro=True
        )
        assert execution.result.is_error is True
        assert "그룹이 없어" not in execution.result.content

    def test_a_truncated_macro_pool_refuses_to_name_a_free_slot(self):
        class TruncatedMacros(RigPort):
            def query_state(self, path: str) -> dict:
                if path == "DataPool/Macros":
                    # childCount 4 but only slot 1 returned: slots 2..4 are taken
                    # and invisible, so "lowest free" would answer 2 and the
                    # following `Store Macro 2` would overwrite the operator's.
                    return {
                        "ok": True,
                        "path": path,
                        "node": {"name": "Macros", "class": "Macros", "childCount": 4},
                        "children": [{"i": 1, "name": "Copilot Go", "class": "Macro"}],
                        "truncated": True,
                    }
                return super().query_state(path)

        port = RecordingExecutionPort()
        execution = _dispatch(
            _registry(rig=TruncatedMacros(), port=port, gate=ClearingGate()), create_macro=True
        )
        assert execution.result.is_error is True
        assert port.executed == [], "a slot was chosen from an incomplete enumeration"

    def test_a_complete_macro_pool_still_picks_the_lowest_free_slot(self):
        # Non-vacuity: the count check must not have disabled the happy path.
        port = RecordingExecutionPort()
        _dispatch(
            _registry(rig=RigPort(macros=(1, 2, 3)), port=port, gate=ClearingGate()),
            create_macro=True,
        )
        assert [c for c in port.executed if c.startswith("Store Macro 4")]

    def test_a_macro_pool_child_without_a_slot_index_refuses_too(self):
        class NamelessSlots(RigPort):
            def query_state(self, path: str) -> dict:
                if path == "DataPool/Macros":
                    return {
                        "ok": True,
                        "path": path,
                        "node": {"name": "Macros", "class": "Macros", "childCount": 1},
                        "children": [{"name": "Copilot Go", "class": "Macro"}],
                        "truncated": False,
                    }
                return super().query_state(path)

        execution = _dispatch(
            _registry(rig=NamelessSlots(), gate=ClearingGate()), create_macro=True
        )
        assert execution.result.is_error is True

    def test_a_zero_child_macro_pool_refuses_instead_of_taking_slot_one(self):
        # `M.safe_children` returns an empty table when BOTH `Children()` and
        # `Count()` pcall-fail, and `childCount` is derived from that same empty
        # read — so a wholesale enumeration failure and a genuinely empty pool
        # are ONE payload: ok=true, childCount 0, no children, truncated false.
        # Trusting it leaves the occupied set empty, "lowest free" answers 1, and
        # slot 1 holds the responder's own `Copilot Go` macro on the measured rig.
        class DeadPoolLooksEmpty(RigPort):
            def query_state(self, path: str) -> dict:
                if path == "DataPool/Macros":
                    return {
                        "ok": True,
                        "path": path,
                        "node": {"name": "Macros", "class": "Macros", "childCount": 0},
                        "children": [],
                        "truncated": False,
                    }
                return super().query_state(path)

        port = RecordingExecutionPort()
        execution = _dispatch(
            _registry(rig=DeadPoolLooksEmpty(), port=port, gate=ClearingGate()),
            create_macro=True,
        )
        assert execution.result.is_error is True
        assert port.executed == [], (
            f"a macro was stored over a pool that may never have been read: {port.executed}"
        )
        assert not [c for c in port.executed if c.startswith("Store Macro 1")]


class TestLiveLockDemotion:
    """run-audit P1-4 — AC-PRECHK-014 ④ separates a hold from a lock."""

    def test_a_locked_gate_is_not_an_error(self):
        port = RecordingExecutionPort()
        gate = LockedGate()
        execution = _dispatch(_registry(port=port, gate=gate), create_macro=True)
        assert gate.screened, "the gate never saw a bundle"
        assert port.executed == [], "a locked gate must send nothing"
        # The lock doing its job is an ANSWER, not a correctable mistake.
        assert execution.result.is_error is False

    def test_a_locked_gate_still_returns_the_report_and_the_lock_status(self):
        payload = json.loads(
            _dispatch(_registry(gate=LockedGate()), create_macro=True).result.content
        )
        assert payload["macro_execution"]["gate_status"] == "locked"
        assert payload["inventory"]["observed_count"] == 3

    def test_a_hold_is_still_an_error(self):
        # The two states must not be collapsed in either direction.
        execution = _dispatch(_registry(gate=HoldingGate()), create_macro=True)
        assert execution.result.is_error is True

    def test_a_locked_gate_says_the_macro_was_not_stored(self):
        # The lock is not an error, so `is_error` cannot carry this. Without an
        # explicit key the payload says `created` and instructs the user to go run
        # the macro and watch the lights — about a macro that was never sent.
        payload = json.loads(
            _dispatch(_registry(gate=LockedGate()), create_macro=True).result.content
        )
        assert payload["macro"]["created"] is True, "authoring itself must still be reported"
        assert payload["macro"]["executed"] is False, (
            "a locked gate sent nothing, yet the report does not say so"
        )

    def test_a_hold_says_the_macro_was_not_stored_either(self):
        payload = json.loads(
            _dispatch(_registry(gate=HoldingGate()), create_macro=True).result.content
        )
        assert payload["macro"]["executed"] is False

    def test_a_cleared_gate_says_the_macro_was_stored(self):
        # Non-vacuity: the key must not be constant-false.
        payload = json.loads(
            _dispatch(_registry(gate=ClearingGate()), create_macro=True).result.content
        )
        assert payload["macro"]["executed"] is True


def _requery_reads(rig):
    """The macro-line property reads the handler performed."""
    return [call for call in rig.property_calls if call[0].startswith("DataPool/Macros/")]


def _executed_bundle():
    """A cleared, fully executed macro bundle plus the doubles that recorded it.

    ``MacroWritingExecutionPort`` and ``RigPort`` share one store, so the value a
    read-back returns is the value a ``Set Macro`` command actually carried.
    """
    store: dict[str, str] = {}
    rig = RigPort(macro_lines=store)
    port = MacroWritingExecutionPort(store)
    execution = _dispatch(_registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True)
    return rig, port, json.loads(execution.result.content)


class TestStoredMacroIsRequeried:
    """PR #7 review A1-1 — a command receipt is not evidence of effect.

    This SPEC measured a console answering ``OK`` for a command it had rejected,
    and answering ``OK`` while writing to a different object than the one named.
    Nothing in this handler read a stored macro back, even though the M0 GO
    record establishes the macro grammar itself on a requery of
    ``DataPool/Macros/91/1 Command`` returning ``On Group 11``.
    """

    def test_the_stored_line_is_read_back_off_the_console(self):
        rig, port, payload = _executed_bundle()
        assert port.executed, "no command was executed — the check would be vacuous"
        # Default doubles: slot 1 is taken, so the free slot is 2; the first
        # authored line drives the first group.
        assert ("DataPool/Macros/2/1", "Command") in rig.property_calls
        assert payload["macro_requery"]["path"] == "DataPool/Macros/2/1"
        assert payload["macro_requery"]["read"] is True

    def test_the_read_back_value_is_the_value_the_command_carried(self):
        _rig, port, payload = _executed_bundle()
        authored = [c for c in port.executed if c.startswith("Set Macro 2.1 ")]
        assert len(authored) == 1, f"the first line was not authored once: {authored}"
        # The value is not asserted as a literal: it is the payload the executed
        # command actually carried, so the two cannot drift apart.
        carried = authored[0].split("'Command' '", 1)[1].rstrip("'")
        assert payload["macro_requery"]["value"] == carried
        assert payload["macro_requery"]["expected"] == carried
        assert payload["macro_requery"]["matches"] is True
        assert carried == "On Group 11", f"the authoring grammar changed shape: {carried}"

    def test_only_one_line_is_read_back_however_many_groups_there_are(self):
        # A full sweep would cost two extra audited property reads per group.
        store: dict[str, str] = {}
        rig = RigPort(groups=(11, 12, 13, 14), macro_lines=store)
        port = MacroWritingExecutionPort(store)
        _dispatch(_registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True)
        assert len([c for c in port.executed if c.startswith("Set Macro ")]) == 8
        assert len(_requery_reads(rig)) == 1, _requery_reads(rig)

    def test_a_requery_that_answers_not_ok_does_not_erase_the_authoring(self):
        # The default double has no stored line, so the read-back comes back
        # ok=false — the shape a timeout or a bad path produces.
        rig = RigPort()
        port = RecordingExecutionPort()
        payload = json.loads(
            _dispatch(
                _registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True
            ).result.content
        )
        assert _requery_reads(rig), "the requery never happened — the check would be vacuous"
        assert payload["macro_requery"]["read"] is False
        assert payload["macro_requery"]["error"]
        # A failed read is NEVER a statement about the macro: it must not claim
        # the console stored the wrong text either.
        assert payload["macro_requery"]["matches"] is None
        # And the authoring result stays exactly what it was — byte-identical to
        # the run whose requery succeeded.
        _rig, _port, confirmed = _executed_bundle()
        assert payload["macro"] == confirmed["macro"]
        assert payload["macro"]["created"] is True
        assert payload["macro"]["executed"] is True

    def test_a_failed_requery_says_requery_failed_not_macro_missing(self):
        summary = json.loads(
            _dispatch(_registry(gate=ClearingGate()), create_macro=True).result.content
        )["macro_requery"]["summary_ko"]
        # What the user reads must name the failed read as the failed thing.
        assert "재조회 실패" in summary
        # And must not be readable as "the macro is not there" — the substitution
        # this SPEC has now fixed on three separate read paths.
        assert "매크로가 없다는 뜻은 아니다" in summary

    def test_a_raising_requery_is_captured_not_propagated(self):
        class RaisingLineRead(RigPort):
            def query_property(self, path: str, property_name: str) -> dict:
                if path.startswith("DataPool/Macros/"):
                    self.property_calls.append((path, property_name))
                    raise RuntimeError("no reply within 3.0s")
                return super().query_property(path, property_name)

        rig = RaisingLineRead()
        execution = _dispatch(_registry(rig=rig, gate=ClearingGate()), create_macro=True)
        payload = json.loads(execution.result.content)
        assert _requery_reads(rig), "the requery never happened — the check would be vacuous"
        assert payload["macro_requery"]["read"] is False
        assert "no reply within 3.0s" in payload["macro_requery"]["error"]
        assert payload["macro"]["created"] is True
        # The fixture inventory — the tool's primary product — survives it.
        assert payload["inventory"]["observed_count"] == 3

    def test_a_value_that_disagrees_is_reported_as_a_disagreement(self):
        # Non-vacuity for `matches`: it must not be constant-true on a read that
        # answered. The console returns a line the handler never authored.
        store: dict[str, str] = {}
        rig = RigPort(macro_lines=store)

        class Overwriting(MacroWritingExecutionPort):
            def execute(self, command: str):
                result = super().execute(command)
                self.store["DataPool/Macros/2/1"] = "On Group 99"
                return result

        port = Overwriting(store)
        payload = json.loads(
            _dispatch(
                _registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True
            ).result.content
        )
        assert payload["macro_requery"]["read"] is True
        assert payload["macro_requery"]["matches"] is False
        assert payload["macro_requery"]["value"] == "On Group 99"
        summary = payload["macro_requery"]["summary_ko"]
        assert "재조회 불일치" in summary
        # Both sides of the disagreement are in front of the user.
        assert "On Group 11" in summary and "On Group 99" in summary

    def test_a_held_bundle_is_never_requeried(self):
        # Nothing was sent, so a read-back would manufacture a read failure about
        # a macro the console was never asked to store.
        rig = RigPort()
        port = RecordingExecutionPort()
        payload = json.loads(
            _dispatch(
                _registry(rig=rig, port=port, gate=HoldingGate()), create_macro=True
            ).result.content
        )
        assert port.executed == []
        assert _requery_reads(rig) == []
        assert "macro_requery" not in payload

    def test_a_locked_bundle_is_never_requeried(self):
        rig = RigPort()
        port = RecordingExecutionPort()
        payload = json.loads(
            _dispatch(
                _registry(rig=rig, port=port, gate=LockedGate()), create_macro=True
            ).result.content
        )
        assert port.executed == []
        assert _requery_reads(rig) == []
        assert "macro_requery" not in payload

    def test_a_failed_command_is_never_requeried(self):
        class FailingPort(RecordingExecutionPort):
            def execute(self, command: str):
                from server.orchestrator.ports import ExecutionResult

                self.executed.append(command)
                return ExecutionResult(ok=False, detail="Illegal object")

        rig = RigPort()
        execution = _dispatch(
            _registry(rig=rig, port=FailingPort(), gate=ClearingGate()), create_macro=True
        )
        assert execution.result.is_error is True
        assert _requery_reads(rig) == []

    def test_the_tool_description_tells_the_model_what_a_failed_read_back_means(self):
        # The description is the model's ONLY contract for reading this payload
        # (the convention `TestRigContextDescription` fixes for get_rig_context).
        # A new key the model reads as absence is the defect, not the key.
        (definition,) = [d for d in _registry().definitions() if d.name == TOOL]
        assert "macro_requery" in definition.description
        assert "UNCONFIRMED" in definition.description
        assert "does NOT mean the macro is absent" in definition.description


class TestZeroTargetsDoesNotDeriveASlot:
    """PR #7 review A1-2 — the slot read was unconditional.

    A rig with no groups is an ANSWER (``AC-PRECHK-014`` ④, ``is_error=False``),
    yet a macro pool that read short turned it into an error and threw away the
    fixture inventory the tool exists to produce — plus one audited OSC send on a
    pool no command would ever name.
    """

    class _ShortMacroPool(RigPort):
        def query_state(self, path: str) -> dict:
            if path == "DataPool/Macros":
                # childCount 4 with one child returned: `_free_macro_slot` must
                # refuse this, which is what used to sink the whole call.
                return {
                    "ok": True,
                    "path": path,
                    "node": {"name": "Macros", "class": "Macros", "childCount": 4},
                    "children": [{"i": 1, "name": "Copilot Go", "class": "Macro"}],
                    "truncated": True,
                }
            return super().query_state(path)

    def test_a_short_macro_pool_does_not_sink_a_no_groups_answer(self):
        rig = self._ShortMacroPool(groups=())
        execution = _dispatch(_registry(rig=rig, gate=ClearingGate()), create_macro=True)
        payload = json.loads(execution.result.content)
        assert execution.result.is_error is False
        assert "macro_no_groups" in [row["kind"] for row in payload["skipped_checks"]]
        # The primary product survives: 3 fixtures with the planted duplicate.
        assert payload["inventory"]["observed_count"] == 3
        assert payload["collisions"]["address_duplicates"]

    def test_the_macro_pool_is_not_read_when_there_is_nothing_to_store(self):
        rig = RigPort(groups=())
        _dispatch(_registry(rig=rig, gate=ClearingGate()), create_macro=True)
        assert "DataPool/Groups" in rig.state_calls, "the group pool was not read at all"
        assert "DataPool/Macros" not in rig.state_calls, (
            f"the macro pool was read for a rig with no targets: {rig.state_calls}"
        )

    def test_the_placeholder_slot_never_reaches_the_console(self):
        # INVARIANT GUARD, not a regression test: it holds on the pre-fix code
        # too. What it pins is the absolute condition — the stand-in slot the
        # zero-target branch hands to `MacroPolicy.available` is a real slot on a
        # real console and must never be spoken.
        rig = RigPort(groups=())
        port = RecordingExecutionPort()
        execution = _dispatch(_registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True)
        assert port.executed == [], f"zero targets produced commands: {port.executed}"
        assert "9999" not in execution.result.content

    def test_commands_authored_for_zero_targets_are_refused(self, monkeypatch):
        """The refusal that keeps the stand-in slot off the wire.

        ``build_response_check_macro`` answers every zero-target case before it
        reads ``policy.macro_slot``, so the handler's refusal is unreachable as
        the two modules stand today. It exists for the day that stops holding, so
        it is exercised by making it stop holding: without it, a slot nobody
        derived becomes a ``Store Macro`` target.
        """

        def _authors_anyway(pool, policy):
            return MacroResult(
                created=True,
                target_kind="group",
                reason="stub — authored despite zero targets",
                reason_code="visual_confirmation_required",
                commands=(f"Store Macro {policy.macro_slot}",),
                macro_slot=policy.macro_slot,
            )

        monkeypatch.setattr(tools_module, "build_response_check_macro", _authors_anyway)
        rig = RigPort(groups=())
        port = RecordingExecutionPort()
        execution = _dispatch(_registry(rig=rig, port=port, gate=ClearingGate()), create_macro=True)
        assert execution.result.is_error is True
        assert port.executed == [], f"a slot nobody derived was stored into: {port.executed}"

    def test_the_macro_pool_is_still_read_when_there_are_groups(self):
        # NON-VACUITY (passes pre-fix by design): the guard must skip the read on
        # the branch that stores nothing, not disable it everywhere.
        rig = RigPort(groups=(11,))
        _dispatch(_registry(rig=rig, gate=ClearingGate()), create_macro=True)
        assert "DataPool/Macros" in rig.state_calls


class TestMissingRigSectionIsAWiringGap:
    """PR #7 review A1-3 — a dropped rig_paths section blamed the group pool.

    Indexing ``rig_paths`` inside the try block rendered a ``KeyError`` as
    ``group pool unreadable: 'groups'``: a wiring mistake reported as a failed
    read of a pool that was never queried.
    """

    def _dispatch_with(self, rig_paths):
        rig = RigPort()
        registry = build_toolset(
            execution_port=RecordingExecutionPort(),
            state_port=rig,
            property_port=rig,
            rig_paths=rig_paths,
            bundle_gate=ClearingGate(),
        )
        return rig, _dispatch(registry, create_macro=True)

    def test_an_override_missing_both_sections_names_them(self):
        rig, execution = self._dispatch_with({"fixtures": FIXTURE_ROOT})
        assert execution.result.is_error is True
        content = execution.result.content
        assert "groups" in content and "macros" in content
        assert "no path configured" in content
        # Not a failed read: nothing was queried, so nothing may be called
        # unreadable.
        assert "unreadable" not in content
        assert "DataPool/Groups" not in rig.state_calls
        assert "DataPool/Macros" not in rig.state_calls

    def test_an_override_missing_only_the_macro_pool_names_only_it(self):
        _rig, execution = self._dispatch_with(
            {"fixtures": FIXTURE_ROOT, "groups": "DataPool/Groups"}
        )
        assert execution.result.is_error is True
        content = execution.result.content
        assert "macros" in content
        assert "unreadable" not in content
        assert "'groups'" not in content, f"a configured section was blamed: {content}"

    def test_a_complete_override_still_builds_the_macro(self):
        # Non-vacuity: the guard must not reject every override.
        _rig, execution = self._dispatch_with(
            {
                "fixtures": FIXTURE_ROOT,
                "groups": "DataPool/Groups",
                "macros": "DataPool/Macros",
            }
        )
        assert execution.result.is_error is False
        assert json.loads(execution.result.content)["macro"]["created"] is True


class FootprintRigPort(RigPort):
    """``RigPort`` that also answers the three-tier fixture-type walk.

    The base double raises for ``Patch/FixtureTypes``, which is deliberate — it
    proves the walk classifies rather than raises. This subclass is the other
    half: a rig where the bound axis actually produces a grade, so "no command was
    fired" is asserted on a run that DID do the work.
    """

    #: Injected, never derived. Two modes so the widest is unambiguous.
    MODE_WIDTHS = (11, 17)

    def query_state(self, path: str) -> dict:
        if path == "Patch/FixtureTypes":
            self.state_calls.append(path)
            return _walk_snapshot(path, 1, self._children([1]))
        if path == "Patch/FixtureTypes/1/DMXModes":
            self.state_calls.append(path)
            return _walk_snapshot(
                path, len(self.MODE_WIDTHS), self._children(range(1, len(self.MODE_WIDTHS) + 1))
            )
        parts = path.split("/")
        if len(parts) == 6 and parts[-1] == "DMXChannels":
            self.state_calls.append(path)
            # Truncated listing with an exact count -- the measured shape.
            return _walk_snapshot(path, self.MODE_WIDTHS[int(parts[4]) - 1], [], truncated=True)
        return super().query_state(path)


def _walk_snapshot(path: str, child_count: int, children, *, truncated: bool = False) -> dict:
    return {
        "ok": True,
        "path": path,
        "node": {"name": path.rsplit("/", 1)[-1], "class": "Pool", "childCount": child_count},
        "children": list(children),
        "truncated": truncated,
    }


class TestFootprintWalkIsWiredThroughRigPaths:
    """AC-OVERLAP-018 · D-2 · D-3 — the axis rides the existing seams."""

    def test_the_walk_module_hardcodes_no_rig_path(self):
        source = (PROJECT_ROOT / "server" / "prechk" / "footprint.py").read_text(encoding="utf-8")
        constants = [
            node.value
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        assert constants, "문자열 상수를 모으지 못하면 이 단정이 공허하다"
        assert "Patch/FixtureTypes" not in constants
        # Non-vacuity: the path DOES exist -- as the rig-context default the
        # handler passes in, which is the seam a literal would bypass.
        assert tools_module.DEFAULT_RIG_CONTEXT_PATHS["fixture_types"] == "Patch/FixtureTypes"

    def test_the_handler_walks_the_configured_path(self):
        rig = FootprintRigPort()
        registry = build_toolset(
            execution_port=RecordingExecutionPort(),
            state_port=rig,
            property_port=rig,
            rig_paths={**tools_module.DEFAULT_RIG_CONTEXT_PATHS},
        )
        _dispatch(registry)
        assert "Patch/FixtureTypes" in rig.state_calls
        assert "Patch/FixtureTypes/1/DMXModes" in rig.state_calls

    def test_an_override_redirects_the_walk(self):
        # The point of the seam: a different rig_paths entry moves the walk.
        class Elsewhere(FootprintRigPort):
            def __init__(self):
                super().__init__()
                self.requested: list[str] = []

            def query_state(self, path: str) -> dict:
                self.requested.append(path)
                if path.startswith("Patch/OtherTypes"):
                    return super().query_state(
                        path.replace("Patch/OtherTypes", "Patch/FixtureTypes")
                    )
                return super().query_state(path)

        rig = Elsewhere()
        registry = build_toolset(
            execution_port=RecordingExecutionPort(),
            state_port=rig,
            property_port=rig,
            rig_paths={
                **tools_module.DEFAULT_RIG_CONTEXT_PATHS,
                "fixture_types": "Patch/OtherTypes",
            },
        )
        payload = json.loads(_dispatch(registry).result.content)
        # The walk asked for the overridden root, never the default one.
        assert [path for path in rig.requested if path.startswith("Patch/OtherTypes")]
        assert [path for path in rig.requested if path.startswith("Patch/FixtureTypes")] == []
        # Non-vacuity: the redirected walk still produced a bound, so the override
        # moved the walk rather than breaking it.
        assert payload["overlap_basis"]["bound"] == max(FootprintRigPort.MODE_WIDTHS)
        assert payload["overlap_basis"]["bound_source"].startswith("Patch/OtherTypes")

    def test_the_macro_section_tuple_is_unchanged(self):
        # D-3: adding "fixture_types" here would make one override omission behave
        # differently depending on create_macro, and would break the two tests
        # that pin the macro guard's message.
        assert tools_module.PRECHK_RIG_SECTIONS == ("groups", "macros")
        assert tools_module.PRECHK_FOOTPRINT_SECTIONS == ("fixture_types",)
        assert (
            set(tools_module.PRECHK_FOOTPRINT_SECTIONS) & set(tools_module.PRECHK_RIG_SECTIONS)
            == set()
        )

    def test_the_footprint_section_is_checked_regardless_of_create_macro(self):
        """D-3: the guard sits OUTSIDE the create_macro branch.

        A guard inside that branch is the trap: the same override omission would
        be named when a macro was requested and pass silently when it was not.
        """
        paths = {
            key: value
            for key, value in tools_module.DEFAULT_RIG_CONTEXT_PATHS.items()
            if key != "fixture_types"
        }
        for create_macro in (False, True):
            rig = FootprintRigPort()
            registry = build_toolset(
                execution_port=RecordingExecutionPort(),
                state_port=rig,
                property_port=rig,
                rig_paths=paths,
                bundle_gate=ClearingGate(),
            )
            execution = _dispatch(registry, create_macro=create_macro)
            payload = json.loads(execution.result.content)
            note = payload["overlap_basis"]["observation_note"]
            assert payload["overlap_basis"]["basis"] == "not_performed", create_macro
            assert "fixture_types" in note, create_macro
            # Names the section; does NOT claim a pool read failed.
            assert "판독 실패가 아니다" in note
            assert "Patch/FixtureTypes" not in rig.state_calls

    def test_a_missing_section_does_not_discard_the_report(self):
        # Refusing the call would throw away the fixture inventory the tool exists
        # to produce -- the shape the zero-target macro branch already fixed once.
        paths = {
            key: value
            for key, value in tools_module.DEFAULT_RIG_CONTEXT_PATHS.items()
            if key != "fixture_types"
        }
        rig = FootprintRigPort()
        registry = build_toolset(
            execution_port=RecordingExecutionPort(),
            state_port=rig,
            property_port=rig,
            rig_paths=paths,
        )
        execution = _dispatch(registry)
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["inventory"]["observed_count"] == len(_FIXTURES)
        assert payload["collisions"]["address_duplicates"]

    def test_a_walk_that_cannot_read_its_root_blames_the_path_not_the_console(self):
        # The base RigPort raises for Patch/FixtureTypes. The fixture inventory
        # answered first, so the console is demonstrably reachable.
        rig = RigPort()
        execution = _dispatch(_registry(rig=rig))
        payload = json.loads(execution.result.content)
        assert payload["overlap_basis"]["basis"] == "not_performed"
        assert "다른 경로가 답했으므로" in payload["overlap_basis"]["observation_note"]

    def test_the_query_count_stays_inside_the_budget(self):
        rig = FootprintRigPort()
        registry = build_toolset(
            execution_port=RecordingExecutionPort(),
            state_port=rig,
            property_port=rig,
            rig_paths={**tools_module.DEFAULT_RIG_CONTEXT_PATHS},
        )
        _dispatch(registry)
        walk_calls = [call for call in rig.state_calls if call.startswith("Patch/FixtureTypes")]
        assert walk_calls, "순회 조회가 0건이면 상한 단정이 공허하다"
        assert len(walk_calls) == 1 + 1 + len(FootprintRigPort.MODE_WIDTHS)
        assert len(walk_calls) <= tools_module.PRECHK_FOOTPRINT_QUERY_CAP


class TestTheOverlapAxisFiresNoCommand:
    """AC-OVERLAP-018 ⑤ — read-only, fixed by observing the execution port."""

    def test_the_bound_axis_speaks_nothing_to_the_console(self):
        rig = FootprintRigPort()
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=rig,
            property_port=rig,
            rig_paths={**tools_module.DEFAULT_RIG_CONTEXT_PATHS},
        )
        payload = json.loads(_dispatch(registry).result.content)
        # Non-vacuity: the axis really ran on this call.
        assert payload["overlap_basis"]["bound"] == max(FootprintRigPort.MODE_WIDTHS)
        assert port.executed == []

    def test_the_same_port_is_not_simply_inert(self):
        # Without this the assertion above would pass against a port that records
        # nothing at all.
        rig = FootprintRigPort()
        port = RecordingExecutionPort()
        registry = build_toolset(
            execution_port=port,
            state_port=rig,
            property_port=rig,
            rig_paths={**tools_module.DEFAULT_RIG_CONTEXT_PATHS},
            bundle_gate=ClearingGate(),
        )
        _dispatch(registry, create_macro=True)
        assert port.executed


class TestBoundaryProhibitions:
    """AC-OVERLAP-018 ①②③④ — four boundaries, each with a non-vacuity guard."""

    def _prechk_sources(self) -> list[Path]:
        return sorted((PROJECT_ROOT / "server" / "prechk").rglob("*.py"))

    def test_the_axis_adds_no_web_surface(self):
        visited = 0
        hits: list[str] = []
        for source in sorted((PROJECT_ROOT / "server" / "web").rglob("*.py")):
            visited += 1
            text = source.read_text(encoding="utf-8")
            for needle in ("footprint", "walk_mode_widths", "overlap_basis"):
                if needle in text:
                    hits.append(f"{source.name}: {needle}")
        assert visited >= 1, "web 계층 파일을 방문하지 않으면 0건 판정이 공허하다"
        assert hits == []
        # Non-vacuity: the axis IS reachable -- through the existing tool name.
        assert TOOL in TOOL_NAMES
        assert "walk_mode_widths" in TOOLS_SOURCE.read_text(encoding="utf-8")

    def test_the_walk_never_touches_the_execution_port(self):
        nodes = 0
        hits: list[str] = []
        for source in self._prechk_sources():
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                nodes += 1
                if isinstance(node, ast.Name) and node.id == "execution_port":
                    hits.append(source.name)
                if isinstance(node, ast.Attribute) and node.attr == "execution_port":
                    hits.append(source.name)
        assert nodes >= 1, "AST 노드를 방문하지 않으면 0건 판정이 공허하다"
        assert hits == []

    def test_the_prechk_package_never_imports_the_send_surface(self):
        modules: list[str] = []
        for source in self._prechk_sources():
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    modules.append(node.module or "")
        assert len(modules) >= 1, "import를 하나도 모으지 못하면 0건 판정이 공허하다"
        assert [m for m in modules if m.startswith(("server.bridge", "pythonosc"))] == []

    def test_the_operator_tool_exemption_list_is_unchanged(self):
        from .test_architecture import _NAMED_TOOL_EXEMPTIONS

        assert (
            frozenset({"server/tools/osc_smoke.py", "server/tools/responder_roundtrip.py"})
            == _NAMED_TOOL_EXEMPTIONS
        )
