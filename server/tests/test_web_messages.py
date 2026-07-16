"""WebSocket protocol v1 message schema tests (M5 — REQ-MVP-020/021 surface).

The protocol is the contract between the FastAPI WebSocket server, the React
client, and the M6 measurement harness — versioned (``v: 1``) and documented in
``server/web/PROTOCOL.md``. Client messages are strictly validated (unknown or
malformed input never reaches the orchestrator); server events are plain dicts
built by one builder per event type.
"""

from __future__ import annotations

import json

import pytest

from server.safety.approval import ApprovalItem, ApprovalRequest
from server.web.messages import (
    PROTOCOL_VERSION,
    ProtocolError,
    approval_request_event,
    approval_resolved_event,
    busy_event,
    chat_response_event,
    error_event,
    notice_event,
    parse_client_message,
    proposal_event,
    status_event,
)


def _raw(**fields) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False)


class TestClientMessageParsing:
    def test_chat_message_parses(self):
        message = parse_client_message(_raw(type="chat", text="보컬 그룹 만들어줘"))
        assert message["type"] == "chat"
        assert message["text"] == "보컬 그룹 만들어줘"

    def test_approval_decision_parses(self):
        message = parse_client_message(
            _raw(type="approval_decision", request_id="req-1", approved=True)
        )
        assert message["type"] == "approval_decision"
        assert message["request_id"] == "req-1"
        assert message["approved"] is True

    def test_lock_toggle_parses(self):
        message = parse_client_message(_raw(type="lock", active=False))
        assert message["type"] == "lock"
        assert message["active"] is False

    def test_status_request_parses(self):
        assert parse_client_message(_raw(type="status_request"))["type"] == "status_request"

    @pytest.mark.parametrize(
        "raw",
        [
            "not json at all",
            json.dumps(["a", "list"]),
            json.dumps({"type": "chat", "text": "hi"}),  # missing v
            json.dumps({"v": 99, "type": "chat", "text": "hi"}),  # wrong version
            json.dumps({"v": 1, "type": "unknown_type"}),
            json.dumps({"v": 1, "type": "chat"}),  # missing text
            json.dumps({"v": 1, "type": "chat", "text": "   "}),  # blank text
            json.dumps({"v": 1, "type": "chat", "text": 42}),  # non-string text
            json.dumps({"v": 1, "type": "approval_decision", "approved": True}),  # no id
            json.dumps({"v": 1, "type": "approval_decision", "request_id": "r"}),  # no bool
            json.dumps({"v": 1, "type": "approval_decision", "request_id": "r", "approved": "yes"}),
            json.dumps({"v": 1, "type": "lock"}),  # missing active
            json.dumps({"v": 1, "type": "lock", "active": 1}),  # non-bool active
        ],
    )
    def test_malformed_client_messages_are_rejected(self, raw):
        with pytest.raises(ProtocolError):
            parse_client_message(raw)


def _request() -> ApprovalRequest:
    return ApprovalRequest(
        items=(
            ApprovalItem(
                command="Delete Sequence 5",
                risk_reasons=("blacklist: Delete",),
                warnings=("unspecified-target warning",),
            ),
        )
    )


class TestServerEventBuilders:
    def test_every_event_carries_version_and_type(self):
        events = [
            chat_response_event(status="ok", summary="완료", text="했어요", commands=[]),
            approval_request_event(request_id="r1", request=_request()),
            approval_resolved_event(request_id="r1", approved=True),
            status_event(health="online", live_lock=False, executions_blocked=False),
            proposal_event(commands=["Store Cue 1"], reasons=["live lock"]),
            error_event(message="오류", kind="rate_limit"),
            busy_event(message="처리 중"),
            notice_event(message="알림"),
        ]
        for event in events:
            assert event["v"] == PROTOCOL_VERSION
            assert isinstance(event["type"], str) and event["type"]
            json.dumps(event, ensure_ascii=False)  # must be JSON-serializable

    def test_approval_request_event_carries_commands_reasons_warnings_actions(self):
        event = approval_request_event(request_id="req-7", request=_request())
        assert event["type"] == "approval_request"
        assert event["request_id"] == "req-7"
        assert event["actions"] == ["approve", "reject"]
        (item,) = event["items"]
        assert item["command"] == "Delete Sequence 5"
        assert item["risk_reasons"] == ["blacklist: Delete"]
        assert item["warnings"] == ["unspecified-target warning"]

    def test_chat_response_event_shape(self):
        event = chat_response_event(
            status="ok",
            summary="실행 완료",
            text="그룹을 만들었습니다",
            commands=[{"command": "Store Group 3", "status": "executed_ok", "label": "실행 완료"}],
        )
        assert event["type"] == "chat_response"
        assert event["status"] == "ok"
        assert event["summary"] == "실행 완료"
        assert event["text"] == "그룹을 만들었습니다"
        assert event["commands"][0]["label"] == "실행 완료"

    def test_status_event_shape(self):
        event = status_event(health="console_offline", live_lock=True, executions_blocked=True)
        assert event["type"] == "status"
        assert event["health"] == "console_offline"
        assert event["live_lock"] is True
        assert event["executions_blocked"] is True

    def test_proposal_event_shape(self):
        event = proposal_event(commands=["Store Cue 1"], reasons=["live lock active"])
        assert event["type"] == "proposal"
        assert event["commands"] == ["Store Cue 1"]
        assert event["reasons"] == ["live lock active"]

    def test_error_event_shape(self):
        event = error_event(message="한도 초과", kind="rate_limit")
        assert event["type"] == "error"
        assert event["message"] == "한도 초과"
        assert event["kind"] == "rate_limit"
