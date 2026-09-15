"""t374 배선 — `plan_override_look`, override look 플래너를 모델이 부를 수 있게 하는 도구.

t373 이 `server/design/override_look.py` 를 만들고 자기 시험을 통과시켰는데
12단계 커버리지는 7/12 그대로였다. `TOOL_NAMES` 에 이름이 없어 모델이 못 불렀기
때문이다 — 플래너 시험이 그것을 볼 수 없었던 이유는 그 시험들이
`plan_override_solo_spot` 을 **직접** 불렀다는 데 있다. 이 파일은 모델이 들어오는
자리(`registry.dispatch`)로 들어가므로, 등록되지 않은 도구는 여기서 전부 실패한다.

「돌아간다」 말고 이 파일이 붙들려고 있는 것 넷:

* **안전 답 셋에 기본값이 없다.** 문서20 §10.1 항목 13 이 자동화를 금지한
  결정이고, 답이 없으면 계획도 없다 — 조용한 기본값이 이 카드가 막는 실패다.
  스키마의 `required` 와 핸들러의 거절을 **둘 다** 잰다: 스키마는 조언이고
  거절이 방어다.
* **IFX/PFX 문형을 지어내지 않는다.** 답이 True 인데 원문 커맨드가 없으면
  거절한다. 지어낸 문형은 안전 심사를 통과해 콘솔에 그대로 간다.
* **잘린 풀 읽기는 빈 풀이 아니다.** 점유 목록이 잘리면 계획 자체를 거절한다 —
  진행하면 점유된 슬롯이 「빈 자리」로 답해지고 그 위에 Store 가 간다.
* **번들은 `run_commands` 로만 콘솔에 닿는다.** 게이트가 번들 전체를 한 번에
  보고, 통과시키지 않으면 발사가 0건이다.

콘솔 접촉 0. 아래 전부 인메모리다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import TOOL_NAMES, build_toolset

TOOL = "plan_override_look"
FIXTURES_PATH = "Patch/Stages/1/Fixtures"
POOLS_PATH = "DataPool/PresetPools"
POOL_NO = 22

#: 이 리그가 답하는 유일한 픽스처. FOH 한 대를 무대 중앙에 겨눈다.
FID = 111
POSITION = {"posx": "4.0", "posy": "-6.0", "posz": "6.0"}
ROTATION = {"rotx": "0.0", "roty": "0.0", "rotz": "0.0"}

ANSWERS_OFF = {"stop_ifx": False, "stop_pfx": False, "move_in_black": True}


# -- fakes --------------------------------------------------------------------


class _RecordingPort:
    """CommandExecutionPort 더블 — 도달한 명령을 전부 기록한다."""

    def __init__(self, failures: frozenset[str] = frozenset()) -> None:
        self.failures = set(failures)
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        if command in self.failures:
            return ExecutionResult(ok=False, detail=f"syntax error near '{command}'")
        return ExecutionResult(ok=True, detail="OK")


class _RigPort:
    """state + property 를 한 객체로 답하는 리그 더블.

    `build_toolset` 은 `property_port` 를 생략하면 `state_port` 에서 채택하므로
    (`query_property` 를 갖고 있으면) 생산 배선과 같은 모양이 된다.
    """

    def __init__(
        self,
        *,
        occupied: tuple[int, ...] = (),
        truncated: bool = False,
        fixtures: tuple[int, ...] = (FID,),
        readable: tuple[int, ...] | None = None,
        rotation: bool = True,
    ) -> None:
        self._occupied = occupied
        self._truncated = truncated
        self._fixtures = fixtures
        # 좌표를 답해 주는 픽스처. 기본은 전부.
        self._readable = fixtures if readable is None else readable
        self._rotation = rotation
        self.queried: list[str] = []

    # -- state ----------------------------------------------------------------

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path == FIXTURES_PATH:
            children = [
                {"i": index, "name": f"Fixture {fid}"}
                for index, fid in enumerate(self._fixtures, start=1)
            ]
            return {
                "v": 1,
                "kind": "state",
                "path": path,
                "children": children,
                "node": {"childCount": len(children)},
                "truncated": False,
            }
        if path == f"{POOLS_PATH}/{POOL_NO}":
            children = [{"i": slot, "name": f"Look {slot}"} for slot in self._occupied]
            # 절단을 흉내낼 때는 childCount 가 children 보다 커야 한다 — 그것이
            # `paged_children` 이 보는 산술이다.
            child_count = len(children) + 5 if self._truncated else len(children)
            return {
                "v": 1,
                "kind": "state",
                "path": path,
                "children": children,
                "node": {"childCount": child_count},
                "truncated": self._truncated,
            }
        raise LookupError(f"unknown object path: {path}")

    # -- property -------------------------------------------------------------

    def query_property(self, path: str, name: str) -> dict:
        prefix = f"{FIXTURES_PATH}/"
        if not path.startswith(prefix):
            return {"ok": False, "error": f"no such object: {path}"}
        slot = int(path[len(prefix) :])
        fid = self._fixtures[slot - 1]
        if fid not in self._readable:
            return {"ok": False, "error": f"property not readable: {name}"}
        if name == "fid":
            return {"ok": True, "value": str(fid)}
        if name in POSITION:
            return {"ok": True, "value": POSITION[name]}
        if name in ROTATION:
            if not self._rotation:
                return {"ok": False, "error": f"property not readable: {name}"}
            return {"ok": True, "value": ROTATION[name]}
        return {"ok": False, "error": f"unknown property: {name}"}


@dataclass(frozen=True)
class _CommandDecision:
    command: str
    status: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ScreenDecision:
    cleared: bool
    status: str
    commands: tuple[_CommandDecision, ...]
    notice: str = ""


@dataclass
class _RecordingGate:
    """BundleGate 더블 — 심사한 번들을 기록하고, 통과시키거나 막는다."""

    cleared: bool = True
    status: str = "ok"
    notice: str = ""
    screened: list[list[str]] = field(default_factory=list)
    risks: list[object] = field(default_factory=list)

    def screen(self, commands, *, risk=None):
        self.screened.append(list(commands))
        self.risks.append(risk)
        return _ScreenDecision(
            cleared=self.cleared,
            status=self.status,
            commands=tuple(
                _CommandDecision(
                    command=c,
                    status="ok" if self.cleared else "blocked",
                    reasons=() if self.cleared else ("live lock",),
                )
                for c in commands
            ),
            notice=self.notice,
        )


# -- dispatch -----------------------------------------------------------------


def _registry(*, port=None, rig=None, gate=None):
    return build_toolset(
        execution_port=port or _RecordingPort(),
        state_port=rig or _RigPort(),
        rig_paths={"fixtures": FIXTURES_PATH, "preset_pools": POOLS_PATH},
        bundle_gate=gate,
    )


def _arguments(**overrides) -> dict:
    arguments: dict = {
        "fixture_ids": [FID],
        "target": {"x": 0.0, "y": 0.0, "z": 1.2},
        "zoom_degrees": 8.0,
        "pool_no": POOL_NO,
        "safety": dict(ANSWERS_OFF),
    }
    arguments.update(overrides)
    return arguments


def _dispatch(registry, arguments: dict | None = None):
    call = ToolCall(id="c1", name=TOOL, arguments=_arguments() if arguments is None else arguments)
    execution = registry.dispatch(call)
    return execution, json.loads(execution.result.content)


def _definition(registry):
    return next(d for d in registry.definitions() if d.name == TOOL)


# =============================================================================
# registration — the whole point of this card
# =============================================================================


class TestToolRegistration:
    def test_the_tool_is_in_the_closed_tool_set(self):
        # 이 단언 하나가 t374 다. 플래너는 t373 부터 있었고, 없었던 것은 이 줄이다.
        assert TOOL in TOOL_NAMES
        assert TOOL in [d.name for d in _registry().definitions()]

    def test_the_planner_module_is_reachable_from_the_registry(self):
        # 등록만 되고 핸들러가 다른 것을 부르면 위 시험은 통과한다. 계획이
        # 실제로 플래너를 지났는지는 그 산출물(조준 각·슬롯)로만 확인된다.
        _execution, payload = _dispatch(_registry())
        assert payload["report"]["aims"][0][0] == FID
        assert payload["report"]["store"]["policy"] == "override"

    def test_the_five_required_arguments_are_required(self):
        required = _definition(_registry()).parameters["required"]
        assert set(required) == {
            "fixture_ids",
            "target",
            "zoom_degrees",
            "pool_no",
            "safety",
        }

    def test_the_schema_requires_all_three_safety_answers(self):
        safety = _definition(_registry()).parameters["properties"]["safety"]
        assert set(safety["required"]) == {"stop_ifx", "stop_pfx", "move_in_black"}
        for name in ("stop_ifx", "stop_pfx", "move_in_black"):
            assert safety["properties"][name]["type"] == "boolean"

    def test_the_description_sends_the_model_to_ask_user_for_the_answers(self):
        # 도구가 기본값을 안 갖는 것만으로는 부족하다 — 모델이 어디서 답을
        # 구해야 하는지 모르면 그 자리에서 멈추거나 지어낸다.
        description = _definition(_registry()).description
        assert "ask_user" in description

    def test_the_description_forbids_inventing_the_stop_command(self):
        description = _definition(_registry()).description.lower()
        assert "invent" in description

    def test_the_description_says_move_in_black_emits_no_command(self):
        description = _definition(_registry()).description.lower()
        assert "move in black" in description or "move_in_black" in description
        assert "no command" in description

    def test_the_schema_does_not_take_coordinates_or_occupancy(self):
        # AP-16 — 리그 숫자는 콘솔에서 읽는다. 스키마가 좌표나 점유를 받으면
        # 모델이 옮겨 적은 값이 명령줄에 오를 수 있다.
        properties = _definition(_registry()).parameters["properties"]
        for banned in ("positions", "coordinates", "occupied_slots", "rotz_by_fid"):
            assert banned not in properties


# =============================================================================
# the safety answers are the operator's — no defaults, ever
# =============================================================================


class TestSafetyAnswersAreNeverDefaulted:
    def test_a_missing_safety_object_is_refused(self):
        arguments = _arguments()
        del arguments["safety"]
        execution, payload = _dispatch(_registry(), arguments)
        assert execution.result.is_error is True
        assert "safety" in payload["error"]

    @pytest.mark.parametrize("name", ["stop_ifx", "stop_pfx", "move_in_black"])
    def test_one_missing_answer_refuses_the_whole_plan(self, name):
        safety = dict(ANSWERS_OFF)
        del safety[name]
        execution, payload = _dispatch(_registry(), _arguments(safety=safety))
        assert execution.result.is_error is True
        assert name in payload["error"]

    @pytest.mark.parametrize("bad", [None, 1, 0, "yes", "", 1.0])
    def test_a_non_bool_answer_is_not_coerced(self, bad):
        # 「빠진 답은 no 가 아니다」의 기계적 형태. 0/""/None 이 False 로
        # 강압되면 감독이 답하지 않은 결정이 「아니오」로 저장된다.
        safety = dict(ANSWERS_OFF, stop_ifx=bad)
        execution, payload = _dispatch(_registry(), _arguments(safety=safety))
        assert execution.result.is_error is True
        assert "stop_ifx" in payload["error"]

    def test_nothing_is_executed_when_the_answers_are_incomplete(self):
        # 거절이 보고에만 있고 명령이 이미 나갔다면 방어가 아니다.
        port = _RecordingPort()
        safety = dict(ANSWERS_OFF)
        del safety["stop_pfx"]
        _dispatch(_registry(port=port), _arguments(safety=safety))
        assert port.executed == []


class TestTheStopCommandIsNeverInvented:
    @pytest.mark.parametrize(
        ("answer", "argument"),
        [("stop_ifx", "stop_ifx_command"), ("stop_pfx", "stop_pfx_command")],
    )
    def test_answering_yes_without_the_command_is_refused(self, answer, argument):
        safety = dict(ANSWERS_OFF, **{answer: True})
        port = _RecordingPort()
        execution, payload = _dispatch(_registry(port=port), _arguments(safety=safety))
        assert execution.result.is_error is True
        assert argument in payload["error"]
        assert port.executed == []

    @pytest.mark.parametrize(
        ("answer", "argument"),
        [("stop_ifx", "stop_ifx_command"), ("stop_pfx", "stop_pfx_command")],
    )
    def test_the_operators_own_command_line_reaches_the_bundle_verbatim(self, answer, argument):
        # 원문이 그대로 실려야 한다. 여기서 재포장하면 이 저장소가 측정한 적
        # 없는 문형을 이 코드가 만들어 낸 것이 된다.
        command = "Preset 4.7 At Full"
        safety = dict(ANSWERS_OFF, **{answer: True})
        port = _RecordingPort()
        _dispatch(
            _registry(port=port),
            _arguments(safety=safety, **{argument: command}),
        )
        assert command in port.executed

    @pytest.mark.parametrize(
        ("answer", "argument"),
        [("stop_ifx", "stop_ifx_command"), ("stop_pfx", "stop_pfx_command")],
    )
    def test_a_command_without_the_matching_yes_is_refused_as_contradictory(self, answer, argument):
        execution, _payload = _dispatch(_registry(), _arguments(**{argument: "Preset 4.7 At Full"}))
        assert execution.result.is_error is True
        assert answer in _payload_error(execution)

    def test_no_stop_line_appears_when_both_answers_are_no(self):
        port = _RecordingPort()
        _dispatch(_registry(port=port))
        assert not any("ifx" in c.lower() or "pfx" in c.lower() for c in port.executed)


def _payload_error(execution) -> str:
    return json.loads(execution.result.content)["error"]


# =============================================================================
# occupancy: an unestablished slot is not a free slot
# =============================================================================


class TestSlotOccupancyIsReadNotAssumed:
    def test_an_empty_pool_takes_the_lowest_slot(self):
        _execution, payload = _dispatch(_registry(rig=_RigPort(occupied=())))
        assert payload["report"]["store"]["slot"] == 1

    def test_an_occupied_slot_is_stepped_over_never_overwritten(self):
        _execution, payload = _dispatch(_registry(rig=_RigPort(occupied=(1, 2, 3))))
        assert payload["report"]["store"]["slot"] == 4

    def test_a_truncated_pool_read_refuses_the_plan(self):
        # 이 갈래가 제일 비싼 것이다: 진행하면 점유된 슬롯이 빈 자리로 답해지고
        # 감독이 손으로 만든 프리셋 위에 Store 가 간다.
        port = _RecordingPort()
        rig = _RigPort(occupied=(1, 2), truncated=True)
        execution, payload = _dispatch(_registry(port=port, rig=rig))
        assert execution.result.is_error is True
        assert "truncated" in payload["error"]
        assert port.executed == []

    def test_a_requested_slot_that_is_occupied_is_refused(self):
        rig = _RigPort(occupied=(4,))
        execution, payload = _dispatch(_registry(rig=rig), _arguments(preferred_slot=4))
        assert execution.result.is_error is True
        assert "occupied" in payload["error"]

    def test_the_observed_occupancy_is_reported_back(self):
        # 무엇을 보고 그 슬롯을 골랐는지 감독이 볼 수 있어야 한다.
        _execution, payload = _dispatch(_registry(rig=_RigPort(occupied=(1, 3))))
        assert payload["report"]["occupancy"] == {
            "pool": POOL_NO,
            "occupied": [1, 3],
            "chosen_slot": 2,
        }


# =============================================================================
# the rig is read, and an unreadable fixture is refused rather than dropped
# =============================================================================


class TestTheRigIsRead:
    def test_the_pool_number_the_caller_named_is_the_one_that_is_read(self):
        rig = _RigPort()
        _dispatch(_registry(rig=rig))
        assert f"{POOLS_PATH}/{POOL_NO}" in rig.queried

    def test_the_configured_fixtures_path_is_used_not_a_hardcoded_one(self):
        rig = _RigPort()
        _dispatch(_registry(rig=rig))
        assert FIXTURES_PATH in rig.queried

    def test_a_fixture_with_no_readable_coordinates_is_refused_not_skipped(self):
        # 조용히 빼면 감독은 두 대를 요청했는데 한 대만 선 것을 모른다.
        port = _RecordingPort()
        rig = _RigPort(fixtures=(FID, 112), readable=(FID,))
        execution, payload = _dispatch(
            _registry(port=port, rig=rig), _arguments(fixture_ids=[FID, 112])
        )
        assert execution.result.is_error is True
        assert "112" in payload["error"]
        assert port.executed == []

    def test_an_unread_rotation_is_reported_rather_than_defaulted_silently(self):
        # 회전을 못 읽으면 조준에 보정이 안 들어간다. 0 을 쓰는 것 자체는
        # 플래너의 동작이고, 그것이 **측정값으로 읽히지 않는** 것이 이 시험이다.
        rig = _RigPort(rotation=False)
        _execution, payload = _dispatch(_registry(rig=rig))
        assert payload["report"]["rotation_unread"] == [FID]

    def test_a_read_rotation_leaves_no_unread_note(self):
        _execution, payload = _dispatch(_registry(rig=_RigPort(rotation=True)))
        assert "rotation_unread" not in payload["report"]


# =============================================================================
# move_in_black is a decision, not a command
# =============================================================================


class TestMoveInBlackEmitsNoCommand:
    def test_answering_yes_emits_no_command_for_it(self):
        port = _RecordingPort()
        _dispatch(_registry(port=port), _arguments(safety=dict(ANSWERS_OFF, move_in_black=True)))
        assert not any("black" in c.lower() or "mib" in c.lower() for c in port.executed)

    def test_the_report_says_it_must_still_be_set_by_hand(self):
        _execution, payload = _dispatch(
            _registry(), _arguments(safety=dict(ANSWERS_OFF, move_in_black=True))
        )
        assert "by hand" in payload["report"]["move_in_black_note"]

    def test_the_decision_is_carried_in_the_report_either_way(self):
        for answer in (True, False):
            _execution, payload = _dispatch(
                _registry(), _arguments(safety=dict(ANSWERS_OFF, move_in_black=answer))
            )
            assert payload["report"]["safety"]["move_in_black"] is answer


# =============================================================================
# the bundle reaches the console through run_commands and nothing else
# =============================================================================


class TestTheBundleGoesThroughRunCommands:
    def test_the_gate_sees_the_whole_bundle_as_one_screening(self):
        gate = _RecordingGate()
        _execution, payload = _dispatch(_registry(gate=gate))
        assert len(gate.screened) == 1
        assert gate.screened[0] == payload["report"]["commands"]

    def test_a_gate_that_does_not_clear_yields_zero_sends(self):
        port = _RecordingPort()
        gate = _RecordingGate(cleared=False, status="blocked")
        execution, _payload = _dispatch(_registry(port=port, gate=gate))
        assert port.executed == []
        assert execution.result.is_error is True

    def test_the_bundle_declares_its_showfile_write_risk_to_the_gate(self):
        # 이 번들은 프리셋 풀을 고친다(`Store Preset <풀>.<슬롯>`). 선언이
        # 게이트까지 가지 않으면 승인 카드가 안 뜬다.
        gate = _RecordingGate()
        _dispatch(_registry(gate=gate))
        assert gate.risks[0] is not None

    def test_the_handler_never_names_the_execution_port_itself(self):
        # 구조적 검사. 두 번째 실행 표면이 생기면 게이트·라이브 락·감사 로그가
        # 그 경로에서 통째로 빠진다.
        import ast
        import inspect
        from pathlib import Path

        import server.orchestrator.tools as tools_module

        source = Path(inspect.getfile(tools_module)).read_text(encoding="utf-8")
        handler = next(
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == TOOL
        )
        named = {node.attr for node in ast.walk(handler) if isinstance(node, ast.Attribute)}
        assert "execute" not in named
        assert "execution_port" not in named


# =============================================================================
# geometry refusals come back with their own reason
# =============================================================================


class TestGeometryRefusalsAreDistinguishable:
    def test_a_target_on_the_fixture_is_refused_as_a_pointing_problem(self):
        # 대상이 픽스처 자리에 있으면 빔 방향이 정의되지 않는다. 플래너의
        # 거절(점유·안전답)과 **다른 층의 사실**이라 사유가 달라야 한다.
        on_the_fixture = {
            "x": float(POSITION["posx"]),
            "y": float(POSITION["posy"]),
            "z": float(POSITION["posz"]),
        }
        port = _RecordingPort()
        execution, payload = _dispatch(_registry(port=port), _arguments(target=on_the_fixture))
        assert execution.result.is_error is True
        assert "aimed" in payload["error"]
        assert port.executed == []


# =============================================================================
# argument validation — a wrong argument fails visibly, never silently corrected
# =============================================================================


class TestArgumentValidation:
    @pytest.mark.parametrize("bad", [[], "111", {}, None])
    def test_fixture_ids_must_be_a_non_empty_list(self, bad):
        execution, payload = _dispatch(_registry(), _arguments(fixture_ids=bad))
        assert execution.result.is_error is True
        assert "fixture_ids" in payload["error"]

    def test_a_fixture_named_twice_is_refused(self):
        execution, payload = _dispatch(_registry(), _arguments(fixture_ids=[FID, FID]))
        assert execution.result.is_error is True
        assert "twice" in payload["error"]

    @pytest.mark.parametrize("axis", ["x", "y", "z"])
    def test_every_target_axis_must_be_a_finite_number(self, axis):
        target = {"x": 0.0, "y": 0.0, "z": 1.2}
        target[axis] = "middle"
        execution, payload = _dispatch(_registry(), _arguments(target=target))
        assert execution.result.is_error is True
        assert f"target.{axis}" in payload["error"]

    def test_a_dimmer_outside_the_percent_range_is_refused(self):
        execution, payload = _dispatch(_registry(), _arguments(dimmer_pct=140.0))
        assert execution.result.is_error is True
        assert "dimmer_pct" in payload["error"]

    def test_colour_needs_exactly_three_channels(self):
        execution, payload = _dispatch(_registry(), _arguments(color_percents=[100.0, 50.0]))
        assert execution.result.is_error is True
        assert "color_percents" in payload["error"]


# =============================================================================
# the capability is genuinely absent without a property port
# =============================================================================


class TestMissingCapabilityIsNotAnEmptyRig:
    def test_a_state_only_port_says_the_capability_is_missing(self):
        class _StateOnly:
            def query_state(self, path: str) -> dict:
                return {"v": 1, "kind": "state", "path": path, "children": []}

        registry = build_toolset(
            execution_port=_RecordingPort(),
            state_port=_StateOnly(),
            rig_paths={"fixtures": FIXTURES_PATH, "preset_pools": POOLS_PATH},
        )
        execution, payload = _dispatch(registry)
        assert execution.result.is_error is True
        assert "property" in payload["error"]
