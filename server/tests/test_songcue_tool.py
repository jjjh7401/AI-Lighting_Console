from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from server.llm.types import ToolCall
from server.looks.schema import AttributeValue, Look, LookLibrary
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.safety.gate import SafetyGate
from server.safety.lock import LiveLock
from server.tests.test_looks_tool import _RecordingGate, _RecordingPort

_TOOL = "prepare_songcue"
_TOOLS_MODULE = Path("server/orchestrator/tools.py")
_SPEC_MODULES = (
    Path("server/looks/songcue.py"),
    Path("server/looks/songcue_report.py"),
)
_GROUPS_PATH = "DataPool/Groups"
_SEQUENCES_PATH = "DataPool/Sequences"
_SEQUENCE_BODY_PATH = "DataPool/Sequences/3"
_DEFAULT_SECTIONS = (
    {"name": "Verse", "start": "0:10"},
    {"name": "Chorus", "start": "0:14"},
)
_FULL_GROUPS = (
    (11, "Back Wash"),
    (12, "FOH Wash"),
    (13, "Side L"),
    (14, "Top"),
    (15, "Cyc"),
    (16, "Special"),
)


class _SongCueStatePort:
    def __init__(self, tree: dict[str, dict]) -> None:
        self._tree = tree
        self.queried: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


def _registry(*, port=None, state=None, gate=None, library=None, rig_paths=None):
    return build_toolset(
        execution_port=port or _RecordingPort(),
        state_port=state if state is not None else _SongCueStatePort(_tree()),
        bundle_gate=gate,
        look_library=library if library is not None else _library(),
        rig_paths=rig_paths,
    )


def _call(registry, **arguments):
    payload = {
        "song_title": "테스트 곡",
        "genre": "록",
        "timecode_number": 7,
        "sections": list(_DEFAULT_SECTIONS),
    }
    payload.update(arguments)
    execution = registry.dispatch(ToolCall(id="songcue-1", name=_TOOL, arguments=payload))
    return execution, json.loads(execution.result.content)


def _handler_node() -> ast.FunctionDef:
    tree = ast.parse(_TOOLS_MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == _TOOL:
            return node
    raise AssertionError(f"{_TOOL} handler was not found in tools.py")


def _identifiers(node: ast.AST) -> set[str]:
    return (
        {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
        | {
            alias.asname or alias.name
            for n in ast.walk(node)
            if isinstance(n, ast.ImportFrom | ast.Import)
            for alias in n.names
        }
    )


class TestRegistrationConvention:
    def test_the_tool_is_in_all_three_registration_places_and_dispatches(self):
        registry = _registry()

        assert _TOOL in TOOL_NAMES
        assert _TOOL in {definition.name for definition in registry.definitions()}
        execution = registry.dispatch(ToolCall(id="probe", name=_TOOL, arguments={}))
        assert "unknown tool" not in execution.result.content

    def test_every_definition_name_matches_the_closed_tool_set_and_dispatches(self):
        registry = _registry()
        names = {definition.name for definition in registry.definitions()}

        assert names
        assert names == set(TOOL_NAMES)
        for name in TOOL_NAMES:
            execution = registry.dispatch(ToolCall(id="probe", name=name, arguments={}))
            assert "unknown tool" not in execution.result.content, name

    def test_the_schema_has_no_rig_or_sequence_number_fields(self):
        registry = _registry()
        definition = next(
            definition for definition in registry.definitions() if definition.name == _TOOL
        )
        field_names = _schema_property_names(definition.parameters)

        assert field_names
        forbidden = {
            "group",
            "groups",
            "pool",
            "pools",
            "preset_pool",
            "preset_pools",
            "slot",
            "slots",
            "fixture",
            "fixtures",
            "fid",
            "sequence",
            "sequence_no",
            "sequence_number",
        }
        assert forbidden & field_names == set()


class TestSingleExecutionPath:
    def test_the_handler_calls_run_commands_and_no_execution_surface(self):
        identifiers = _identifiers(_handler_node())

        assert identifiers
        assert "run_commands" in identifiers
        assert {"execution_port", "ConsoleLink", "APIRouter", "send_command"} & identifiers == set()

    def test_the_scan_is_not_vacuous_against_the_real_sender(self):
        tree = ast.parse(_TOOLS_MODULE.read_text(encoding="utf-8"))
        run_commands = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "run_commands"
        )
        identifiers = _identifiers(run_commands)

        assert "execution_port" in identifiers
        assert "execute" in identifiers

    def test_spec_modules_do_not_define_a_second_execution_surface(self):
        forbidden = {"execution_port", "ConsoleLink", "APIRouter", "FastAPI", "websocket"}
        for module in _SPEC_MODULES:
            identifiers = _identifiers(ast.parse(module.read_text(encoding="utf-8")))
            assert identifiers, module
            assert forbidden & identifiers == set()

    def test_the_bundle_goes_through_the_gate_and_run_commands_verbatim(self):
        gate = _RecordingGate()
        port = _RecordingPort()

        execution, payload = _call(_registry(port=port, gate=gate))

        assert execution.result.is_error is False
        assert payload["executed"] is True
        assert gate.screened
        assert port.executed
        assert gate.screened == [port.executed]
        assert [entry["command"] for entry in payload["commands"]] == port.executed


class TestIsErrorContract:
    def test_out_of_order_sections_are_a_correctable_error(self):
        execution, payload = _call(
            _registry(),
            sections=(
                {"name": "Chorus", "start": "0:30"},
                {"name": "Drop", "start": "0:10"},
            ),
        )

        assert execution.result.is_error is True
        assert payload["reason"] == "starts_before_previous"
        assert payload["index"] == 1

    def test_unknown_section_names_require_correction(self):
        execution, payload = _call(
            _registry(),
            sections=(
                {"name": "Chorus", "start": "0:10"},
                {"name": "Breakdown", "start": "0:14"},
            ),
        )

        assert execution.result.is_error is True
        assert payload["reason"] == "explicit_dynamics_required"
        assert payload["unknown_sections"] == [{"index": 1, "name": "Breakdown"}]

    def test_storing_nothing_is_an_answer_not_a_failure(self):
        port = _RecordingPort()
        library = _library(_look("chorus", dynamics=4, roles=("없는역할",)))

        execution, payload = _call(
            _registry(port=port, library=library),
            sections=({"name": "Chorus", "start": "0:10"},),
        )

        assert execution.result.is_error is False
        assert payload["executed"] is False
        assert port.executed == []
        assert payload["report"]["sections"][0]["reason"] == "role_unmapped"

    def test_unavailable_rig_section_returns_before_bundle_construction(self):
        class _Dead:
            def query_state(self, path: str) -> dict:
                raise LookupError("console unreachable")

        port = _RecordingPort()
        execution, payload = _call(_registry(port=port, state=_Dead()))

        assert execution.result.is_error is True
        assert "rig_unavailable" in payload
        assert port.executed == []


class TestLiveLockAndGateHold:
    @staticmethod
    def _locked_gate(tmp_path):
        from server.safety.audit import AuditLog

        class _Console:
            def send_command(self, command: str) -> ExecutionResult:
                raise AssertionError("LiveLock attempted a console send")

        lock = LiveLock()
        lock.activate()
        return SafetyGate(console=_Console(), audit=AuditLog(tmp_path / "audit"), lock=lock)

    def test_live_lock_sends_nothing_and_returns_a_proposal_answer(self, tmp_path):
        port = _RecordingPort()

        execution, payload = _call(_registry(port=port, gate=self._locked_gate(tmp_path)))

        assert execution.result.is_error is False
        assert payload["executed"] is False
        assert payload["gate_status"] == "locked"
        assert port.executed == []
        assert payload["commands"]
        assert {entry["status"] for entry in payload["commands"]} == {"proposal"}

    def test_gate_hold_is_an_error_distinct_from_live_lock_demotion(self):
        port = _RecordingPort()
        gate = _RecordingGate(cleared=False, status="held")

        execution, payload = _call(_registry(port=port, gate=gate))

        assert execution.result.is_error is True
        assert payload["gate_status"] == "held"
        assert payload["executed"] is False
        assert port.executed == []


class TestPayload:
    def test_report_and_timing_commands_are_attached_to_the_tool_result(self):
        _execution, payload = _call(_registry())
        command_lines = [entry["command"] for entry in payload["commands"]]

        assert payload["report"]["sections"]
        assert payload["report"]["property_unobserved"]
        assert payload["report"]["requery"]["matched"] is True
        assert "섹션" in payload["summary_ko"]
        assert any(command.startswith("Store Timecode 7") for command in command_lines)
        assert any("Property 'TrigType' 'Time'" in command for command in command_lines)


def _schema_property_names(schema: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    if isinstance(schema, dict):
        properties = schema.get("properties")
        if isinstance(properties, dict):
            names.update(str(name).casefold() for name in properties)
            for value in properties.values():
                names.update(_schema_property_names(value))
        items = schema.get("items")
        if isinstance(items, dict):
            names.update(_schema_property_names(items))
    return names


def _tree(
    *,
    groups: tuple[tuple[int | None, str], ...] = _FULL_GROUPS,
    sequences: tuple[int, ...] = (1, 2, 4),
    drop: tuple[str, ...] = (),
) -> dict[str, dict]:
    tree = {
        _GROUPS_PATH: _payload(_GROUPS_PATH, [_child(number, name) for number, name in groups]),
        _SEQUENCES_PATH: _payload(
            _SEQUENCES_PATH,
            [_child(number, f"Sequence {number}") for number in sequences],
        ),
        _SEQUENCE_BODY_PATH: _payload(
            _SEQUENCE_BODY_PATH,
            (
                {"class": "Cue", "cueNo": 1, "name": "Verse"},
                {"class": "Cue", "cueNo": 2, "name": "Chorus"},
            ),
        ),
    }
    for path in drop:
        tree.pop(path, None)
    return tree


def _payload(path: str, children, *, truncated: bool = False) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": list(children),
        "node": {"childCount": len(children)},
        "truncated": truncated,
    }


def _child(number: int | None, name: str) -> dict:
    if number is None:
        return {"name": name}
    return {"i": number, "name": name}


def _look(
    look_id: str,
    *,
    dynamics: int,
    value: float = 80,
    roles: tuple[str, ...] = ("백라이트",),
) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="rock",
        dynamics=dynamics,
        roles=roles,
        attributes=(AttributeValue("Dimmer", value),),
    )


def _library(*looks: Look) -> LookLibrary:
    return LookLibrary(
        schema_version=1,
        looks=looks
        or (
            _look("verse", dynamics=2, value=55),
            _look("chorus", dynamics=4, value=70),
        ),
    )
