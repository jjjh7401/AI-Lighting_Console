"""SPEC-LDSEND-001 M2 · REQ-LDSEND-001/002/003/004 · AC-LDSEND-001~004.

``GateBundleSender`` — ``BundleSender`` 프로토콜(``server/director/execution.py``)의
실물 구현체. 명령을 공유 ``SafetyGate.execution_port`` 로만 보내고
(``server.bridge`` 를 직접 import 하지 않는다), 번들 하나마다
``STATE_ACKNOWLEDGED``/``STATE_FAILED``/``STATE_UNKNOWN`` 중 정확히 하나만
반환한다 — ``STATE_SENT`` 는 이 구현이 반환하지 않는다(``ConsoleLink.execute()``
가 확인 또는 timeout 까지 블록하므로 "보냈지만 미확인"이라는 중간 상태가
``send()`` 반환 시점에는 존재하지 않는다, plan.md §4 M2).

이 파일은 콘솔/OSC 로 실제로 나가지 않는다 — ``CommandExecutionPort`` 를
흉내내는 fake 만 주입한다(``server.bridge`` import 없음).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from server.director.execution import STATE_ACKNOWLEDGED, STATE_FAILED, STATE_UNKNOWN
from server.orchestrator.bundle_sender import GateBundleSender
from server.orchestrator.ports import ExecutionResult


class _ScriptedExecutionPort:
    """``CommandExecutionPort`` fake — 미리 정해둔 ``ExecutionResult`` 를
    순서대로 반환하고, 실제 호출된 명령을 순서대로 기록한다."""

    def __init__(self, results: list[ExecutionResult]) -> None:
        self._results = list(results)
        self.calls: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.calls.append(command)
        return self._results.pop(0)


class _RaisingExecutionPort:
    """``ok_count`` 번은 ok 로 답하고, 그 뒤 호출부터는 예외를 던지는 fake —
    REQ-LDSEND-004(콘솔 링크 예외 흡수)."""

    def __init__(self, *, ok_count: int = 0) -> None:
        self.calls: list[str] = []
        self._ok_count = ok_count

    def execute(self, command: str) -> ExecutionResult:
        self.calls.append(command)
        if len(self.calls) <= self._ok_count:
            return ExecutionResult(ok=True, detail="", outcome="ok")
        raise RuntimeError("console link broken — synthetic test failure")


def _bundle(*commands: str) -> dict:
    return {"bundle_id": "bundle-1", "commands": list(commands)}


def _ok() -> ExecutionResult:
    return ExecutionResult(ok=True, detail="", outcome="ok")


def _failed() -> ExecutionResult:
    return ExecutionResult(ok=False, detail="blocked: not cleared", outcome="failed")


def _unconfirmed() -> ExecutionResult:
    return ExecutionResult(ok=False, detail="execution unconfirmed", outcome="unconfirmed")


class TestAllCommandsOk:
    def test_all_ok_returns_acknowledged(self) -> None:
        port = _ScriptedExecutionPort([_ok(), _ok(), _ok()])
        sender = GateBundleSender(execution_port=port)

        state = sender.send(_bundle("cmd-1", "cmd-2", "cmd-3"))

        assert state == STATE_ACKNOWLEDGED
        assert port.calls == ["cmd-1", "cmd-2", "cmd-3"]

    def test_commands_are_sent_only_through_the_injected_execution_port(self) -> None:
        """AC-LDSEND-001 — 오직 주입된 execution_port.execute() 경로로만 관측된다."""
        port = _ScriptedExecutionPort([_ok()])
        sender = GateBundleSender(execution_port=port)

        sender.send(_bundle("cmd-1"))

        assert port.calls == ["cmd-1"]


class TestFirstCommandExplicitFailure:
    def test_first_command_failed_with_none_confirmed_before_returns_failed(self) -> None:
        port = _ScriptedExecutionPort([_failed(), _ok(), _ok()])
        sender = GateBundleSender(execution_port=port)

        state = sender.send(_bundle("cmd-1", "cmd-2", "cmd-3"))

        assert state == STATE_FAILED
        # REQ-LDSEND-002 — 확인 안 된 첫 결과 뒤 남은 명령은 보내지 않는다.
        assert port.calls == ["cmd-1"]


class TestAnyUnconfirmedStopsAndReturnsUnknown:
    def test_middle_command_unconfirmed_returns_unknown_and_stops(self) -> None:
        port = _ScriptedExecutionPort([_ok(), _unconfirmed(), _ok()])
        sender = GateBundleSender(execution_port=port)

        state = sender.send(_bundle("cmd-1", "cmd-2", "cmd-3"))

        assert state == STATE_UNKNOWN
        assert port.calls == ["cmd-1", "cmd-2"]


class TestConfirmedThenFailedIsPartialAndUnknown:
    def test_failure_after_a_confirmed_command_returns_unknown_not_failed(self) -> None:
        """앞선 명령이 이미 확인됐는데 뒤 명령이 명시적으로 실패(부분 완료) —
        계약 "atomic OSC rollback 을 주장하지 않는다" 를 이 갈래가 구체화한다."""
        port = _ScriptedExecutionPort([_ok(), _ok(), _failed()])
        sender = GateBundleSender(execution_port=port)

        state = sender.send(_bundle("cmd-1", "cmd-2", "cmd-3"))

        assert state == STATE_UNKNOWN
        assert port.calls == ["cmd-1", "cmd-2", "cmd-3"]


class TestConsoleLinkExceptionIsAbsorbed:
    def test_exception_from_execute_is_treated_as_unconfirmed(self) -> None:
        port = _RaisingExecutionPort(ok_count=1)
        sender = GateBundleSender(execution_port=port)

        # 예외가 send() 밖으로 전파되지 않아야 한다 — 그 자체가 이 시험의 단언이다.
        state = sender.send(_bundle("cmd-1", "cmd-2", "cmd-3"))

        assert state == STATE_UNKNOWN
        assert port.calls == ["cmd-1", "cmd-2"]

    def test_exception_on_first_command_returns_unknown_not_failed(self) -> None:
        port = _RaisingExecutionPort(ok_count=0)
        sender = GateBundleSender(execution_port=port)

        state = sender.send(_bundle("cmd-1"))

        assert state == STATE_UNKNOWN
        assert port.calls == ["cmd-1"]


class TestNeverReturnsStateSent:
    def test_all_ok_bundle_does_not_return_state_sent(self) -> None:
        """``STATE_SENT`` 는 이 구현이 반환하지 않는다(plan.md §4 M2, `console.py`
        `ConsoleLink.execute()` 독스트링 — 확인 또는 timeout 까지 블록한다)."""
        port = _ScriptedExecutionPort([_ok()])
        sender = GateBundleSender(execution_port=port)

        state = sender.send(_bundle("cmd-1"))

        assert state in (STATE_ACKNOWLEDGED, STATE_FAILED, STATE_UNKNOWN)


class TestSendDoesNotRevokeClearances:
    def test_send_never_calls_revoke_clearances(self) -> None:
        """클리어런스 회수는 ``send()`` 의 책임이 아니다 — ``run_director_apply()``
        가 ``execute_bundles()`` 반환 뒤 처리한다(§2.0-나/마 plan.md). fake gate 의
        ``revoke_clearances`` mock 호출 카운트가 0 인지 명시적으로 잰다."""
        port = _ScriptedExecutionPort([_ok(), _ok()])
        gate = SimpleNamespace(execution_port=port, revoke_clearances=MagicMock())
        sender = GateBundleSender(execution_port=gate.execution_port)

        state = sender.send(_bundle("cmd-1", "cmd-2"))

        assert state == STATE_ACKNOWLEDGED
        gate.revoke_clearances.assert_not_called()

    def test_send_never_calls_revoke_clearances_even_on_failure(self) -> None:
        port = _ScriptedExecutionPort([_failed()])
        gate = SimpleNamespace(execution_port=port, revoke_clearances=MagicMock())
        sender = GateBundleSender(execution_port=gate.execution_port)

        sender.send(_bundle("cmd-1"))

        gate.revoke_clearances.assert_not_called()
