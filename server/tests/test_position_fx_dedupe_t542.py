"""카드 t542 — 무빙 효과의 ``Step 2`` 줄이 중복 제거로 빠지는지 잰다.

PR #588(카드 t540)부터 ``position_fx_commands`` 의 base 효과(circle·wave·ballyhoo)는
``Step 2`` 와 커브 줄(``Step k At Accel/Decel -100``)을 낸다. 이 줄들은
``run_commands`` 중복 제거 면제(``tools.py`` ``_PROGRAMMER_STATE_COMMANDS``)에 없다.
그래서 같은 효과를 두 번 만들 때 두 번째 묶음의 ``Step 2`` 가 ``skipped_already_executed``
로 조용히 빠져 1단계(정지)로 돌아갈 수 있다는 가설이 섰다.

이 파일은 그 가설을 **실제 중복 제거 코드**(``build_toolset`` 의 ``run_commands``)로 잰다.
대화 경로는 세션 핸들러가 디스패치마다 만드는 ``ExecutionContext`` 를 그대로 실제 도구에
넘긴다 — 가짜 리그는 판독만 대신하고, ``run_commands`` 는 진짜로 돈다.
"""

from __future__ import annotations

import pytest

from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import ToolCall, _is_programmer_state, build_toolset
from server.spatial.pointing import FX_POSITION_SEQUENCE
from server.spatial.position_fx import position_fx_commands
from server.tests.test_web_session import (
    _DEFAULT_FX_POSITION_POOL_NAMES,
    ScriptedProvider,
    _AnsweringChannel,
    _PresetPoolRegistry,
    _session,
)

BASE_EFFECTS = ("circle", "wave", "ballyhoo")

_CIRCLE = "원을 그리는 포지션 이펙트 시퀀스 {seq} 걸어줘, 41번부터"
_WAVE = "물결 시퀀스 {seq} 저장해줘, FX 프리셋 41번부터"


class _RecordingPort:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class _StatePort:
    def query_state(self, path: str) -> dict:
        return {}


class _RealRunCommandsRegistry(_PresetPoolRegistry):
    """판독은 가짜 리그 그대로, ``run_commands`` 만 실제 도구(중복 제거 포함)로 돌린다."""

    def __init__(self, calls, **rig):
        super().__init__(calls, **rig)
        self.port = _RecordingPort()
        self._toolset = build_toolset(execution_port=self.port, state_port=_StatePort())
        self.statuses: list[list[tuple[str, str]]] = []

    def dispatch(self, call: ToolCall, context=None):
        if call.name != "run_commands":
            return super().dispatch(call, context)
        self.calls.append(call)
        self.wrote = True
        execution = self._toolset.dispatch(call, context)
        self.statuses.append([(o.command, o.status) for o in execution.command_outcomes])
        return execution


def _bundle(effect: str) -> tuple[str, ...]:
    return position_fx_commands(
        effect,
        fids=(11, 12),
        preset_numbers={name: 41 + i for i, name in enumerate(FX_POSITION_SEQUENCE)},
        sequence_no=201,
        label="FX",
    )


def _step_lines(bundle):
    return [(command, status) for command, status in bundle if command.startswith("Step ")]


class TestOneBundleCarriesNoDuplicate:
    """한 묶음 안에서 같은 비면제 줄이 두 번 나오면 묶음 안 중복 제거가 두 번째를 지운다."""

    @pytest.mark.parametrize("effect", BASE_EFFECTS)
    def test_no_non_exempt_line_repeats_inside_one_bundle(self, effect):
        lines = [c for c in _bundle(effect) if not _is_programmer_state(c)]
        assert len(lines) == len(set(lines))


class TestTheInstrumentSeesADrop:
    """대조군 — 앞 묶음의 실행 기록을 넘겨받으면 같은 도구가 ``Step`` 줄을 실제로 지운다.

    이것이 통과해야 아래 대화 경로 시험의 「안 빠짐」이 계기가 눈먼 탓이 아니다.
    대화 경로가 안전한 이유는 세션 핸들러가 디스패치마다 새
    ``ExecutionContext``(``executed_ok`` 빈 집합)를 만들기 때문이다
    (``session.py`` ``_dispatch_declared``). 그 맥락을 이어 붙이는 호출자가 생기면
    아래 줄들이 빠진다.
    """

    def test_carried_executed_set_drops_the_second_step_lines(self):
        from server.orchestrator.tools import ExecutionContext

        port = _RecordingPort()
        toolset = build_toolset(execution_port=port, state_port=_StatePort())
        first = list(_bundle("circle"))
        toolset.dispatch(ToolCall(id="a", name="run_commands", arguments={"commands": first}))
        second = toolset.dispatch(
            ToolCall(id="b", name="run_commands", arguments={"commands": first}),
            ExecutionContext(executed_ok=frozenset(port.executed)),
        )
        dropped = {
            o.command for o in second.command_outcomes if o.status == "skipped_already_executed"
        }
        assert {"Step 2", "Step 1 At Accel -100", "Step 2 At Decel -100"} <= dropped


class TestTwoBuildsThroughTheChatPath:
    """같은 세션에서 무빙 효과를 두 번 만들면 두 묶음 모두 ``Step`` 줄이 콘솔에 닿는가."""

    def _two_builds(self, tmp_path, first, second):
        session, *_ = _session(tmp_path, ScriptedProvider([]))
        registry = _RealRunCommandsRegistry([], position_pool_names=_DEFAULT_FX_POSITION_POOL_NAMES)
        session._registry = registry
        session._question_channel = _AnsweringChannel(())
        session.run_instruction(first)
        session.run_instruction(second)
        return registry

    def test_second_circle_keeps_its_step_lines(self, tmp_path):
        registry = self._two_builds(tmp_path, _CIRCLE.format(seq=201), _CIRCLE.format(seq=202))
        assert len(registry.statuses) == 2
        for bundle in registry.statuses:
            steps = _step_lines(bundle)
            assert [command for command, _ in steps] == [
                "Step 2",
                "Step 1 At Accel -100",
                "Step 1 At Decel -100",
                "Step 2 At Accel -100",
                "Step 2 At Decel -100",
            ]
            assert {status for _, status in steps} == {"executed_ok"}
        assert registry.port.executed.count("Step 2") == 2

    def test_circle_then_wave_skip_nothing(self, tmp_path):
        registry = self._two_builds(tmp_path, _CIRCLE.format(seq=201), _WAVE.format(seq=202))
        assert len(registry.statuses) == 2
        skipped = [c for bundle in registry.statuses for c, s in bundle if s != "executed_ok"]
        assert skipped == []
