from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from server.llm.types import ToolCall
from server.looks.schema import AttributeValue, Look, LookLibrary
from server.looks.songcue import SongCueTimingAxes
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import TOOL_NAMES, build_toolset, timecode_slot_verdict
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
_TIMECODES_PATH = "DataPool/Timecodes"
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


class TestTimecodeSlotOccupancy:
    """`Store Timecode <n>` takes a MODEL-SUPPLIED number.

    Nothing checked it, so a showfile already using that slot lost its timecode
    track silently — the defect `_free_macro_slot` exists to prevent on the
    other pool-writing path. The three branches below are the three things the
    pool read can tell us, and each has a different correct answer.
    """

    def test_a_free_slot_still_emits_the_timecode_write(self):
        _execution, payload = _call(_registry())
        commands = [entry["command"] for entry in payload["commands"]]
        assert any(command.startswith("Store Timecode 7") for command in commands)
        assert payload["timing"]["skipped_axes"] == []

    def test_an_occupied_slot_is_refused_and_names_the_occupant(self):
        state = _SongCueStatePort(_tree(timecodes=(1, 3, 7)))
        execution, payload = _call(_registry(state=state))
        assert execution.result.is_error is True
        assert "Timecode 7" in payload["error"]
        # The occupant is named so the operator can decide, and the refusal says
        # WHY it matters — there is no restore path if the guess is wrong.
        assert "no restore path" in payload["error"]

    def test_it_does_not_silently_pick_a_different_slot(self):
        """Unlike `_free_macro_slot`, the number is part of this tool's schema.

        Substituting one would answer a question nobody asked, and the operator
        would find their timecode somewhere they did not put it."""
        state = _SongCueStatePort(_tree(timecodes=(1, 3, 7)))
        execution, payload = _call(_registry(state=state))
        assert execution.result.is_error is True
        assert "commands" not in payload

    def test_an_unreadable_pool_withholds_the_write_instead_of_sending_it(self):
        """The path is UNVERIFIED, so this branch is not a corner case.

        A dead pool must not read as "nothing is stored there" — the write is
        withheld and the reason travels on the EXISTING skipped_axes channel,
        which is the designed DESCOPE branch this bundle already ships.
        """
        state = _SongCueStatePort(_tree(drop=(_TIMECODES_PATH,)))
        execution, payload = _call(_registry(state=state))
        assert execution.result.is_error is False
        commands = [entry["command"] for entry in payload["commands"]]
        assert not any(command.startswith("Store Timecode") for command in commands)
        reasons = [axis["reason"] for axis in payload["timing"]["skipped_axes"]]
        assert any("occupancy could not be established" in reason for reason in reasons)

    def test_the_auto_advance_axis_survives_a_dead_timecode_pool(self):
        """Degrading one axis must not take the other with it — the cue timing
        is what actually drives the show."""
        state = _SongCueStatePort(_tree(drop=(_TIMECODES_PATH,)))
        _execution, payload = _call(_registry(state=state))
        commands = [entry["command"] for entry in payload["commands"]]
        assert any("Property 'TrigType' 'Time'" in command for command in commands)

    def test_an_empty_pool_is_treated_as_unreadable_not_as_free(self):
        """`M.safe_children` returns an empty table when the read FAILS, so an
        empty pool and a dead pool are one payload. Trusting it would make every
        slot look free — the exact trap `_free_macro_slot` refuses to walk into.
        """
        state = _SongCueStatePort(_tree(timecodes=()))
        _execution, payload = _call(_registry(state=state))
        commands = [entry["command"] for entry in payload["commands"]]
        assert not any(command.startswith("Store Timecode") for command in commands)

    def test_a_truncated_pool_is_treated_as_unreadable(self):
        """A short enumeration makes the occupied set a SUBSET, so "slot 7 was
        not in the list" stops being evidence that slot 7 is free."""
        tree = _tree()
        tree[_TIMECODES_PATH] = _payload(_TIMECODES_PATH, [_child(1, "Timecode 1")], truncated=True)
        _execution, payload = _call(_registry(state=_SongCueStatePort(tree)))
        commands = [entry["command"] for entry in payload["commands"]]
        assert not any(command.startswith("Store Timecode") for command in commands)

    def test_an_empty_pool_the_responder_vouches_for_is_free(self):
        """SPEC-COPILOT-POOLEMPTY-001 — `enumeration:"ok"` 를 실은 빈 풀은 비었음이다.

        위 `test_an_empty_pool_is_treated_as_unreadable_not_as_free` 는 마커가
        없는 페이로드(구버전 응답기)라 그대로 unknown 이어야 하고, 이 검사는 같은
        빈 풀에 마커만 더해 `Store Timecode 7` 이 나가는지를 본다 — 새 쇼의 첫
        타임코드가 만들어지는 경로다.
        """
        tree = _tree(timecodes=())
        tree[_TIMECODES_PATH]["node"]["enumeration"] = "ok"
        _execution, payload = _call(_registry(state=_SongCueStatePort(tree)))
        commands = [entry["command"] for entry in payload["commands"]]
        assert any(command.startswith("Store Timecode 7") for command in commands)
        assert payload["timing"]["skipped_axes"] == []


# ---------------------------------------------------------------------------
# SPEC-COPILOT-POOLEMPTY-001 — 들어올린 술어 `timecode_slot_verdict` (REQ-016)

_VERDICT_PATH = "DataPool/Timecodes"
_ZERO_CHILDREN_REASON = (
    f"timecode pool occupancy could not be established ({_VERDICT_PATH} reported "
    "zero children — a failed enumeration and an empty pool are indistinguishable here) "
    "— the timecode write is withheld rather than sent unchecked"
)


def _wrapped(reason: str) -> str:
    return (
        f"timecode pool occupancy could not be established ({reason}) — "
        "the timecode write is withheld rather than sent unchecked"
    )


class _RaisingPort:
    def query_state(self, path: str) -> dict:
        raise LookupError("no answer")


class _ScriptedPort:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def query_state(self, path: str) -> object:
        return self._payload


def _verdict_payload(children, *, count=None, truncated=False, enumeration=None) -> dict:
    node: dict[str, object] = {"name": "Timecodes", "class": "Pool"}
    if count is not None:
        node["childCount"] = count
    if enumeration is not None:
        node["enumeration"] = enumeration
    return {"node": node, "children": list(children), "truncated": truncated}


class TestTimecodeSlotVerdictMarker:
    """앱은 마커가 「성공」이라고 말할 때에만 `childCount 0` 을 비었음으로 읽는다."""

    def test_an_empty_pool_with_the_ok_marker_is_free(self):
        """AC-POOLEMPTY-006."""
        port = _ScriptedPort(_verdict_payload([], count=0, enumeration="ok"))
        occupant, axes = timecode_slot_verdict(port, _VERDICT_PATH, 7)
        assert occupant is None
        assert axes == SongCueTimingAxes()
        assert axes.timecode_go is True

    def test_an_empty_pool_without_the_marker_is_unknown_with_todays_exact_reason(self):
        """AC-POOLEMPTY-007 — 구버전 응답기 형태 그대로. 사유 문자열까지 바이트 동일."""
        port = _ScriptedPort(_verdict_payload([], count=0))
        occupant, axes = timecode_slot_verdict(port, _VERDICT_PATH, 7)
        assert occupant is None
        assert axes.timecode_go is False
        assert "reported zero children — a failed enumeration and an empty pool" in (
            axes.timecode_skip_reason
        )
        assert axes.timecode_skip_reason == _ZERO_CHILDREN_REASON

    def test_an_empty_pool_with_the_failed_marker_is_unknown(self):
        """AC-POOLEMPTY-008."""
        port = _ScriptedPort(_verdict_payload([], count=0, enumeration="failed"))
        occupant, axes = timecode_slot_verdict(port, _VERDICT_PATH, 7)
        assert occupant is None
        assert axes.timecode_go is False
        assert axes.timecode_skip_reason == _ZERO_CHILDREN_REASON

    def test_a_marker_that_is_neither_value_is_not_trusted(self):
        """값은 두 개뿐이다 — `"partial"` 같은 미래 값이나 오타는 「성공」이 아니다."""
        port = _ScriptedPort(_verdict_payload([], count=0, enumeration="OK"))
        _occupant, axes = timecode_slot_verdict(port, _VERDICT_PATH, 7)
        assert axes.timecode_go is False

    def test_the_other_five_unknown_branches_are_not_relaxed_by_the_marker(self):
        """AC-POOLEMPTY-009 — 마커가 다른 갈래를 뚫지 못한다. 사유는 오늘의 것과 동일.

        (ㄱ) 판독 예외와 (ㄴ) 비-매핑 페이로드는 `node` 자체가 없어 마커를 실을
        자리가 없다 — 그 둘은 형태 그대로 쏘고, 나머지 셋은 `"ok"` 를 싣는다.
        """
        cases = [
            (_RaisingPort(), _wrapped(f"{_VERDICT_PATH} did not answer: no answer")),
            (
                _ScriptedPort("not-a-mapping"),
                _wrapped(f"{_VERDICT_PATH} returned a non-mapping payload"),
            ),
            (
                _ScriptedPort(
                    _verdict_payload([_child(1, "T1")], count=1, truncated=True, enumeration="ok")
                ),
                _wrapped(f"{_VERDICT_PATH} enumeration was truncated"),
            ),
            (
                _ScriptedPort(_verdict_payload([_child(1, "T1")], enumeration="ok")),
                _wrapped(f"{_VERDICT_PATH} reported no childCount"),
            ),
            (
                _ScriptedPort(
                    _verdict_payload(
                        [_child(1, "T1"), _child(2, "T2"), _child(3, "T3")],
                        count=5,
                        enumeration="ok",
                    )
                ),
                _wrapped(
                    f"{_VERDICT_PATH} enumeration is short: childCount 5 but 3 children returned"
                ),
            ),
        ]
        for port, expected_reason in cases:
            occupant, axes = timecode_slot_verdict(port, _VERDICT_PATH, 7)
            assert occupant is None, expected_reason
            assert axes.timecode_go is False, expected_reason
            assert axes.timecode_skip_reason == expected_reason

    def test_occupied_and_free_are_unchanged_by_the_lift(self):
        children = [_child(1, "Timecode 1"), _child(7, "SHOWTC")]
        port = _ScriptedPort(_verdict_payload(children, count=2, enumeration="ok"))
        assert timecode_slot_verdict(port, _VERDICT_PATH, 7) == ("SHOWTC", SongCueTimingAxes())
        assert timecode_slot_verdict(port, _VERDICT_PATH, 8) == (None, SongCueTimingAxes())

    def test_the_nested_definition_is_gone_and_the_handler_calls_the_lifted_one(self):
        """AC-POOLEMPTY-015 — 중첩 정의 0행, 유일 호출자는 이름만 바꿨다."""
        source = _TOOLS_MODULE.read_text(encoding="utf-8")
        assert "def _timecode_slot_verdict" not in source
        assert source.count("def timecode_slot_verdict(") == 1
        assert "timecode_slot_verdict" in _identifiers(_handler_node())
        assert "_timecode_slot_verdict" not in _identifiers(_handler_node())


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
    timecodes: tuple[int, ...] = (1, 3),
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
        # Slot 7 (the number every case here passes) is deliberately FREE, and
        # slots 1/3 are deliberately taken: an empty pool would read as "the
        # enumeration failed" to `timecode_slot_verdict` and suppress the
        # timecode axis, so a pool with occupants is what proves the check
        # passes on merit rather than on an unreadable pool.
        _TIMECODES_PATH: _payload(
            _TIMECODES_PATH,
            [_child(number, f"Timecode {number}") for number in timecodes],
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
