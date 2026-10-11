"""카드 t601 — ``run_commands`` 중복 제거가 한 묶음 안의 정당한 같은 줄을 조용히 건너뛰던 결함.

REQ-MVP-033 의 중복 제거는 **앞선 호출에서 이미 실행된** 줄을 자가 수정 재전송 때 다시
보내지 않는 장치다(``context.executed_ok``). 카드 M6c-6(``82b83abc``)이 그 범위를 「같은
묶음 안의 앞줄」까지 넓혔고, 그 뒤로 한 묶음 안에서 같은 글자가 다시 나와야 하는 줄
(효과 묶음의 ``Step 2``, 같은 장비 그룹의 선택 체인, 사이클 경계의 ``ClearAll``)이 조용히
빠졌다 — ``Store`` 는 그대로 ok 라 빈 효과·빈 그룹이 저장된다(t593 판정서, ``db555da9``,
``4dd48e8f``). 이 시험은 그 범위를 원래 뜻(앞선 호출)으로 되돌린 것을 잠근다.
"""

from __future__ import annotations

import dataclasses

from server.fx.instantiate import build_fx_preset_bundle
from server.fx.loader import load_library_from_dir
from server.orchestrator.tools import ExecutionContext

from .test_tools import ScriptedPort, _call, _registry

_LIBRARY = load_library_from_dir()


def _fx(fx_id: str):
    return next(fx for fx in _LIBRARY.fx if fx.fx_id == fx_id)


def _two_effect_bundles() -> list[str]:
    """t593 이 반영 묶음에 실을 수 있는 꼴 — 효과 프리셋 둘(같은 그룹, 다른 slot)."""
    first = build_fx_preset_bundle(
        dataclasses.replace(_fx("sweep-soft-wide"), speed=60.0),
        group=7,
        preset_pool=22,
        preset=1,
        label="LA Wave",
    )
    second = build_fx_preset_bundle(
        dataclasses.replace(_fx("wave-soft-rise"), speed=30.0),
        group=7,
        preset_pool=22,
        preset=2,
        label="LA Rise",
    )
    return [*first.commands, *second.commands]


class TestRepeatsInsideOneBundleAllRun:
    def test_two_effect_bundles_send_every_line(self) -> None:
        # 재현: 고치기 전에는 두 번째 묶음의 ``Step 2`` 가 skipped_already_executed.
        commands = _two_effect_bundles()
        assert commands.count("Step 2") == 2, "전제: 두 묶음 모두 Step 2 를 낸다"
        port = ScriptedPort()
        execution = _registry(port=port).dispatch(_call("run_commands", {"commands": commands}))
        assert port.executed == commands
        assert {o.status for o in execution.command_outcomes} == {"executed_ok"}

    def test_a_plain_repeated_line_runs_each_time_it_appears(self) -> None:
        port = ScriptedPort()
        execution = _registry(port=port).dispatch(
            _call("run_commands", {"commands": ["cmd1", "cmd2", "cmd1"]})
        )
        assert port.executed == ["cmd1", "cmd2", "cmd1"]
        assert [o.status for o in execution.command_outcomes] == ["executed_ok"] * 3


class TestPriorCallDedupeIsUnchanged:
    """REQ-MVP-033 의 원래 뜻 — 자가 수정 재전송은 앞선 호출에서 실행된 줄을 다시 보내지 않는다."""

    def test_a_line_executed_by_a_prior_call_is_still_skipped(self) -> None:
        port = ScriptedPort()
        context = ExecutionContext(executed_ok=frozenset({"Store Cue 1"}))
        execution = _registry(port=port).dispatch(
            _call("run_commands", {"commands": ["Store Cue 1", "Store Cue 2"]}), context
        )
        assert port.executed == ["Store Cue 2"]
        statuses = [o.status for o in execution.command_outcomes]
        assert statuses == ["skipped_already_executed", "executed_ok"]

    def test_a_prior_line_repeated_in_the_retry_is_skipped_every_time(self) -> None:
        # 앞선 호출에서 실행된 줄은 재전송 묶음에 몇 번 나오든 다시 안 나간다.
        port = ScriptedPort()
        context = ExecutionContext(executed_ok=frozenset({"A"}))
        _registry(port=port).dispatch(_call("run_commands", {"commands": ["A", "B", "A"]}), context)
        assert port.executed == ["B"]

    def test_stop_on_first_failure_is_unchanged(self) -> None:
        port = ScriptedPort(failures=frozenset({"B"}))
        execution = _registry(port=port).dispatch(
            _call("run_commands", {"commands": ["A", "B", "A"]})
        )
        assert port.executed == ["A", "B"]
        assert [o.status for o in execution.command_outcomes] == [
            "executed_ok",
            "failed",
            "not_executed",
        ]
