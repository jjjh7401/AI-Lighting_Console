"""SPEC-COPILOT-WRITEGATE-001 — 선언을 못 싣는 배선은 조용히 0건이 아니다 (카드 t318).

t317 을 만든 에이전트가 스스로 남긴 관찰: 「레지스트리 더블이 새 인자를 못 받자
실패가 예외가 아니라 **0 writes** 로 나타났다」. 재현해서 쟀다 — 그대로였다
(`.moai/state/verify/t318/repro_before.json`): 예외 0건, 승인 요청 0건,
콘솔 0건, 감사 로그에는 `provider_error` · `kind="unexpected"`.

삼킨 자리는 `session.py` 의 최상위 방어선이다::

    except Exception as exc:  # REQ-MVP-044: raw detail NEVER reaches the surface
        event = self._report_error(exc)

이 방어선 자체는 옳다 — 원시 detail 이 화면에 새면 안 된다. 문제는 **분류**다.
선언이 배선을 못 지난 사고가 프로바이더 오류 통에 들어가면, 「0건 나갔다」가
세 가지와 바이트 동일해진다: 감독이 거절했다 · 쓸 것이 없었다 ·
**안전장치가 꺼졌다**. 앞의 둘은 정상이고 셋째만 사고다.

이 파일이 못으로 박는 것 셋:

1. **크게 깨진다** — 선언을 못 받는 레지스트리에서는 콘솔에 한 줄도 안 나가고,
   감사 로그에 `write_gate_declaration_error` 가 남으며, 감독이 보는 문면이
   일반 내부 오류와 다르다.
2. **넓히지 않았다** — 핸들러 **안쪽**에서 나는 `TypeError` 는 이 자리가 삼키지
   않는다(여전히 `unexpected`). 잡는 것은 배선 하나뿐이다.
3. **진짜 「쓸 것이 없다」는 그대로다** — 정상 배선에서 명령 없는 회차는
   선언 사고로 읽히지 않는다.

한계. 서버 층만 잰다. DOM 은 안 잰다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.safety.audit import AuditLog
from server.safety.gate import BatchRisk, SafetyGate, WriteGateDeclarationError
from server.tests.test_writegate_song_finalize import (
    ANSWERS,
    REQUEST,
    _Approval,
    _audit_lines,
    _Console,
    _Provider,
    _Questions,
    _Spatial,
)
from server.web.approval_bridge import ApprovalChannel
from server.web.korean_errors import WRITE_GATE_DECLARATION_KIND
from server.web.session import ChatSession


class _LegacyRegistry:
    """선언을 못 받는 배선 — `dispatch(call)` 하나만 받는다.

    t317 이전의 모든 레지스트리 더블이 이 모양이었고, 프로덕션에서도 래퍼
    하나가 인자를 안 넘기면 같은 모양이 된다.
    """

    def __init__(self, inner) -> None:
        self._inner = inner

    def definitions(self):
        return self._inner.definitions()

    def dispatch(self, call):  # 두 번째 인자가 없다 — 그게 이 더블의 요점이다
        return self._inner.dispatch(call)


class _ExplodingRegistry:
    """배선은 멀쩡한데 **핸들러 안쪽**이 TypeError 를 낸다 — 대조군."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def definitions(self):
        return self._inner.definitions()

    def dispatch(self, call, context=None):
        if call.name == "run_commands":
            raise TypeError("핸들러 내부 버그 — 배선 문제가 아니다")
        return self._inner.dispatch(call, context)


def _drive(tmp_path: Path, wrap):
    console = _Console()
    audit = AuditLog(tmp_path / "audit")
    approval = _Approval(True)
    gate = SafetyGate(console=console, audit=audit, approval_port=approval)
    events: list[dict] = []
    session = ChatSession(
        gate=gate,
        provider=_Provider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=events.append,
        approval_channel=ApprovalChannel(timeout_seconds=1.0),
    )
    session._registry = wrap(_Spatial(session._registry, []))
    session._question_channel = _Questions(ANSWERS)
    session.run_instruction(REQUEST)
    return console, approval, events, audit


def _audit_events(audit: AuditLog) -> list[dict]:
    return [json.loads(line) for line in _audit_lines(audit)]


@pytest.fixture
def broken_wiring(tmp_path):
    return _drive(tmp_path, _LegacyRegistry)


class TestABrokenDeclarationChannelFailsLoudly:
    def test_nothing_reaches_the_console(self, broken_wiring):
        console, _approval, _events, _audit = broken_wiring
        assert console.executed == [], "선언을 못 실으면 한 줄도 보내지 않는다"

    def test_the_audit_names_the_declaration_channel_not_the_provider(self, broken_wiring):
        _console, _approval, _events, audit = broken_wiring
        entries = _audit_events(audit)
        names = {entry.get("event") for entry in entries}
        assert "write_gate_declaration_error" in names, entries
        # 변경 전의 문면. 프로바이더는 이 사고와 아무 관계가 없다.
        assert "provider_error" not in names, entries

    def test_the_operator_sees_a_message_that_is_not_the_generic_internal_error(
        self, broken_wiring
    ):
        _console, _approval, events, _audit = broken_wiring
        errors = [event for event in events if event.get("type") == "error"]
        assert errors, "감독은 아무 말도 못 듣는 상태로 남지 않는다"
        assert errors[-1]["kind"] == WRITE_GATE_DECLARATION_KIND
        message = errors[-1]["message"]
        assert "승인" in message and "보내지 않았습니다" in message, message

    def test_no_approval_card_is_raised_because_nothing_was_attempted(self, broken_wiring):
        _console, approval, _events, _audit = broken_wiring
        assert approval.requests == []


class TestTheCatchWasNotBroadened:
    """핸들러 **안쪽**의 TypeError 는 여전히 일반 내부 오류다."""

    def test_a_handler_side_type_error_is_still_unexpected(self, tmp_path):
        _console, _approval, events, audit = _drive(tmp_path, _ExplodingRegistry)
        errors = [event for event in events if event.get("type") == "error"]
        assert errors and errors[-1]["kind"] == "unexpected", errors
        names = {entry.get("event") for entry in _audit_events(audit)}
        assert "write_gate_declaration_error" not in names, (
            "배선 문제로 오진하면 진짜 버그가 안전 사고로 위장된다"
        )


class TestNothingToWriteStillReadsAsNothingToWrite:
    """정상 배선에서 명령이 비면 그것은 사고가 아니라 거절 사유다."""

    def test_an_empty_bundle_is_a_tool_error_not_a_declaration_failure(self, tmp_path):
        console = _Console()
        audit = AuditLog(tmp_path / "audit")
        gate = SafetyGate(console=console, audit=audit, approval_port=_Approval(True))
        session = ChatSession(
            gate=gate,
            provider=_Provider(),
            system_prefix="PREFIX",
            audit=audit,
            send_event=lambda event: None,
            approval_channel=ApprovalChannel(timeout_seconds=1.0),
        )
        execution = session._dispatch_declared(
            ToolCall(id="empty", name="run_commands", arguments={"commands": []}),
            risk=BatchRisk(reason="쇼파일 쓰기 — 이 회차는 보낼 것이 없다", kind="probe"),
        )
        assert execution.result.is_error
        assert "non-empty list" in str(execution.result.content)
        assert console.executed == []


class TestTheGuardOnlyRejectsAnUnusableSignature:
    def test_a_registry_that_cannot_take_the_context_raises_by_name(self, tmp_path):
        audit = AuditLog(tmp_path / "audit")
        gate = SafetyGate(console=_Console(), audit=audit, approval_port=_Approval(True))
        session = ChatSession(
            gate=gate,
            provider=_Provider(),
            system_prefix="PREFIX",
            audit=audit,
            send_event=lambda event: None,
            approval_channel=ApprovalChannel(timeout_seconds=1.0),
        )
        session._registry = _LegacyRegistry(session._registry)
        with pytest.raises(WriteGateDeclarationError) as raised:
            session._dispatch_declared(
                ToolCall(id="x", name="run_commands", arguments={"commands": ["Store Preset 4.1"]}),
                risk=BatchRisk(reason="쇼파일 쓰기", kind="probe"),
            )
        assert "_LegacyRegistry" in str(raised.value)
        assert "probe" in str(raised.value)
