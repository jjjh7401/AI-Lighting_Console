"""Server-level Korean chat E2E (M5 — AC-MVP-016 ①②③).

Full production shape over a REAL WebSocket surface: FastAPI TestClient WS ↔
app ↔ ChatSession ↔ orchestrator (scripted provider — no network, no keys) ↔
REAL M4 SafetyGate ↔ REAL OscBridge over UDP loopback ↔ the M4 fake console
(``FakeConsoleServer`` answering the M2 wire protocol). Browser-level E2E is
M6 scope — this suite proves the WebSocket protocol surface end to end:

- ① Korean instruction round-trip (WS in → console wire → Korean report out)
- ② approval-pending → WS carries command + risk reason + approve/reject;
     the decision flows to the gate (approve executes; reject voids the bundle)
- ③ completion/failure reported in Korean
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from server.safety.bootstrap import build_console_stack
from server.safety.console import LinkTimeouts
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.measure import RoundTripRecorder
from server.web.messages import PROTOCOL_VERSION

from .test_runner_self_correction import (
    AlwaysFailingCommandProvider,
    ScriptedProvider,
    _final,
    _run_turn,
)
from .test_safety_e2e_audit import FakeConsoleServer

_FAST = LinkTimeouts(exec_confirm_seconds=2.0, ping_seconds=2.0, state_query_seconds=2.0)


@pytest.fixture()
def fake_console():
    server = FakeConsoleServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture()
def stack(tmp_path, fake_console):
    recorder = RoundTripRecorder()
    channel = ApprovalChannel(timeout_seconds=10.0, recorder=recorder)
    console_stack = build_console_stack(
        send_port=fake_console.port,
        receive_port=0,
        approval_port=channel,
        audit_dir=tmp_path / "audit",
        timeouts=_FAST,
        attempt_session_backup=False,
    )
    fake_console.reply_port = console_stack.receive_port
    try:
        yield console_stack, channel, recorder
    finally:
        console_stack.stop()


def _client(stack_bundle, provider):
    console_stack, channel, recorder = stack_bundle
    deps = WebDeps(
        gate=console_stack.gate,
        provider=provider,
        system_prefix="PREFIX",
        audit=console_stack.audit,
        approval_channel=channel,
        recorder=recorder,
    )
    return TestClient(create_app(deps))


def _send(ws, **fields):
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


def _receive_until(ws, event_type: str, *, limit: int = 30) -> dict:
    seen = []
    for _ in range(limit):
        event = ws.receive_json()
        seen.append(event["type"])
        if event["type"] == event_type:
            return event
    raise AssertionError(f"no {event_type!r} event within {limit} frames: {seen}")


class TestScenario1KoreanRoundTrip:
    """AC-MVP-016 ① — Korean instruction over WS reaches the console wire."""

    def test_korean_instruction_round_trip(self, stack, fake_console):
        provider = ScriptedProvider(
            [_run_turn(["Store Group 3"], "c1"), _final("보컬 그룹을 만들었습니다")]
        )
        recorder = stack[2]
        with _client(stack, provider) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="chat", text="보컬 그룹 만들어줘")
            event = _receive_until(ws, "chat_response")
        assert fake_console.exec_commands == ["Store Group 3"]
        assert event["status"] == "ok"
        assert event["text"] == "보컬 그룹을 만들었습니다"
        assert any("가" <= ch <= "힣" for ch in event["summary"])
        # Measurement hooks fired over the real wire (M6 prep).
        (record,) = recorder.records
        assert record.judged is True
        assert record.console_results == 1
        assert record.measured_seconds > 0


class TestScenario2ApprovalFlow:
    """AC-MVP-016 ② — approval card data + decision routed into the gate."""

    def test_approve_executes_the_risky_bundle(self, stack, fake_console):
        provider = ScriptedProvider(
            [_run_turn(["Delete Sequence 5"], "c1"), _final("시퀀스 5를 삭제했습니다")]
        )
        recorder = stack[2]
        with _client(stack, provider) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="chat", text="시퀀스 5 지워줘")
            request = _receive_until(ws, "approval_request")
            (item,) = request["items"]
            assert item["command"] == "Delete Sequence 5"
            assert item["risk_reasons"], "risk reason must be shown (REQ-MVP-021)"
            assert request["actions"] == ["approve", "reject"]
            _send(
                ws,
                type="approval_decision",
                request_id=request["request_id"],
                approved=True,
            )
            resolved = _receive_until(ws, "approval_resolved")
            assert resolved["approved"] is True
            event = _receive_until(ws, "chat_response")
        # Backup rule ③ (REQ-MVP-017) fires on the wire BEFORE the risky command.
        assert fake_console.exec_commands == ["SaveShow", "Delete Sequence 5"]
        assert event["status"] == "ok"
        # The human wait was measured and subtracted (§3).
        (record,) = recorder.records
        assert record.approval_wait_seconds > 0

    def test_reject_voids_the_bundle(self, stack, fake_console):
        provider = ScriptedProvider(
            [_run_turn(["Delete Sequence 6"], "c1"), _final("확인이 필요합니다")]
        )
        with _client(stack, provider) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="chat", text="시퀀스 6 지워줘")
            request = _receive_until(ws, "approval_request")
            _send(
                ws,
                type="approval_decision",
                request_id=request["request_id"],
                approved=False,
            )
            event = _receive_until(ws, "chat_response")
        assert fake_console.exec_commands == []  # nothing reached the wire
        assert any(c["status"] == "rejected" for c in event["commands"])
        assert "거부" in event["summary"]


class TestScenario3KoreanReporting:
    """AC-MVP-016 ③ — completion AND failure reported in Korean."""

    def test_completion_report_is_korean(self, stack, fake_console):
        provider = ScriptedProvider(
            [_run_turn(["Store Cue 1"], "c1"), _final("큐 1을 저장했습니다")]
        )
        with _client(stack, provider) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="chat", text="큐 1 저장해줘")
            event = _receive_until(ws, "chat_response")
        assert event["text"] == "큐 1을 저장했습니다"
        (command,) = event["commands"]
        assert command["label"] == "실행 완료"

    def test_failure_report_is_korean_after_retries_exhausted(self, stack, fake_console):
        # A grammar-invalid command is blocked every round -> retries exhaust.
        provider = AlwaysFailingCommandProvider("'broken quote")
        with _client(stack, provider) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="chat", text="이상한 명령 실행해줘")
            event = _receive_until(ws, "chat_response")
        assert fake_console.exec_commands == []  # grammar-blocked, never sent
        assert event["status"] == "retries_exhausted"
        assert "실패" in event["summary"]


class TestLiveLockOverWebSocket:
    """REQ-MVP-016/035 UI halves over the real WS surface."""

    def test_lock_yields_proposal_cards_and_zero_wire_sends(self, stack, fake_console):
        provider = ScriptedProvider(
            [_run_turn(["Store Cue 1"], "c1"), _final("잠금 중이라 제안만 생성했습니다")]
        )
        with _client(stack, provider) as client, client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "status"  # initial snapshot
            _send(ws, type="lock", active=True)
            status = _receive_until(ws, "status")
            assert status["live_lock"] is True
            _send(ws, type="chat", text="큐 1 저장해줘")
            proposal = _receive_until(ws, "proposal")
            assert proposal["commands"] == ["Store Cue 1"]
            event = _receive_until(ws, "chat_response")
            assert all(c["status"] == "proposal" for c in event["commands"])
        assert fake_console.exec_commands == []

    def test_lock_first_beats_a_pending_approval_over_ws(self, stack, fake_console):
        # REQ-MVP-035 through the full async path: lock arrives while the
        # approval is pending; the later approve must NOT execute.
        provider = ScriptedProvider(
            [_run_turn(["Delete Sequence 7"], "c1"), _final("잠금 상태입니다")]
        )
        with _client(stack, provider) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="chat", text="시퀀스 7 지워줘")
            request = _receive_until(ws, "approval_request")
            _send(ws, type="lock", active=True)
            _receive_until(ws, "status")
            _send(
                ws,
                type="approval_decision",
                request_id=request["request_id"],
                approved=True,
            )
            event = _receive_until(ws, "chat_response")
        assert fake_console.exec_commands == []  # lock-first held on the wire
        assert any(c["status"] == "proposal" for c in event["commands"])
