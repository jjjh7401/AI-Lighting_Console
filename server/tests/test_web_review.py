"""Deploy review WebSocket flow tests (M7 — AC-MVP-010 ②③ / AC-MVP-018 ① UI half).

The review rides the M5 channel pattern as a DISTINCT request type: a second
ApprovalChannel instance carries ReviewRequest payloads, the server publishes
``review_request`` events (plugin name + bounded source preview + compile
verdict + scan report with the best-effort caveat), and the client answers
with ``review_decision``. Quadruple-deny fail-safe applies: no UI / notify
failure / timeout / disconnect all deny (REQ-MVP-019 deny-by-default).
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from server.deploy.compile import LuaCompileChecker
from server.deploy.pipeline import DeployPipeline
from server.deploy.review import build_review_request
from server.deploy.scan import scan_lua_source
from server.llm.types import ModelTurn, ToolCall, Usage
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import load_ruleset
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import (
    PROTOCOL_VERSION,
    ProtocolError,
    parse_client_message,
    review_request_event,
    review_resolved_event,
)
from server.web.session import ChatSession

from .test_deploy_pipeline import DESTRUCTIVE_SOURCE, SAFE_SOURCE
from .test_deploy_transport import DeployableFakeConsole
from .test_runner_self_correction import ScriptedProvider, _final
from .test_safety_gate import FakeConsole  # noqa: F401  (re-exported fixture base)

BROKEN_SOURCE = "function broken( end"


def _deploy_turn(name: str, source: str, call_id: str = "d1") -> ModelTurn:
    return ModelTurn(
        text="",
        tool_calls=(
            ToolCall(
                id=call_id,
                name="deploy_plugin",
                arguments={"name": name, "lua_source": source},
            ),
        ),
        stop_reason="tool_use",
        usage=Usage(),
        provider="scripted",
    )


# -- protocol layer -------------------------------------------------------------


class TestClientMessageParsing:
    def test_valid_review_decision(self):
        message = parse_client_message(
            json.dumps(
                {
                    "v": PROTOCOL_VERSION,
                    "type": "review_decision",
                    "request_id": "review-1",
                    "approved": True,
                }
            )
        )
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "review_decision",
            "request_id": "review-1",
            "approved": True,
        }

    @pytest.mark.parametrize(
        "payload",
        [
            {"type": "review_decision", "approved": True},  # missing id
            {"type": "review_decision", "request_id": "", "approved": True},
            {"type": "review_decision", "request_id": "r-1", "approved": "yes"},
            {"type": "review_decision", "request_id": "r-1"},  # missing approved
        ],
    )
    def test_invalid_review_decision_is_rejected(self, payload):
        with pytest.raises(ProtocolError):
            parse_client_message(json.dumps({"v": PROTOCOL_VERSION, **payload}))


class TestReviewEvents:
    def _request(self, source=DESTRUCTIVE_SOURCE):
        scan = scan_lua_source(source, load_ruleset())
        return build_review_request("Cleaner", source, compile_ok=True, scan=scan)

    def test_review_request_event_carries_everything_the_reviewer_needs(self):
        event = review_request_event(request_id="review-1", request=self._request())
        assert event["v"] == PROTOCOL_VERSION
        assert event["type"] == "review_request"
        assert event["request_id"] == "review-1"
        assert event["plugin_name"] == "Cleaner"
        assert "Delete Sequence 5" in event["source_preview"]
        assert event["source_length"] == len(DESTRUCTIVE_SOURCE)
        assert event["source_truncated"] is False
        assert event["compile_ok"] is True
        assert event["actions"] == ["approve", "reject"]
        scan = event["scan"]
        assert scan["destructive"] is True
        (finding,) = scan["findings"]
        assert finding["line"] == 2
        assert finding["kind"] == "blacklisted"
        assert finding["command"] == "Delete Sequence 5"
        assert finding["matched_entry"] == "Delete"
        assert finding["reasons"]
        assert scan["dynamic_calls"] == []
        # REQ-MVP-027 residual-risk framing rides the wire to the reviewer.
        assert "best-effort" in scan["caveat"]

    def test_review_resolved_event(self):
        event = review_resolved_event(request_id="review-1", approved=False)
        assert event["type"] == "review_resolved"
        assert event["approved"] is False


# -- session layer ----------------------------------------------------------------


def _review_session(tmp_path, provider, *, decide=True, console=None):
    """ChatSession with the deploy pipeline wired; reviews auto-answered."""
    console = console or DeployableFakeConsole()
    audit = AuditLog(tmp_path / "audit")
    approval_channel = ApprovalChannel(timeout_seconds=1.0)
    review_channel = ApprovalChannel(timeout_seconds=1.0, id_prefix="review")
    gate = SafetyGate(console=console, audit=audit, approval_port=approval_channel)
    pipeline = DeployPipeline(
        compile_checker=LuaCompileChecker(),
        ruleset=load_ruleset(),
        deploy_port=gate,
        registry=PluginFlagRegistry(),
        audit=audit,
        review_port=review_channel,  # the channel IS the ReviewPort (M7 alias)
    )
    sent: list[dict] = []

    def send_event(event: dict) -> None:
        sent.append(event)
        # Deterministic reviewer: answer the review as soon as it is shown
        # (notify fires before the channel blocks, so this resolves the wait).
        if event.get("type") == "review_request":
            review_channel.resolve(event["request_id"], approved=decide)

    session = ChatSession(
        gate=gate,
        provider=provider,
        system_prefix="PREFIX",
        audit=audit,
        send_event=send_event,
        approval_channel=approval_channel,
        review_channel=review_channel,
        deploy_pipeline=pipeline,
    )
    return session, console, audit, sent


class TestSessionDeployFlow:
    def test_approved_deploy_reports_success_in_korean(self, tmp_path):
        provider = ScriptedProvider(
            [_deploy_turn("Helper", SAFE_SOURCE), _final("플러그인을 배포했습니다")]
        )
        session, console, _, sent = _review_session(tmp_path, provider, decide=True)
        event = session.run_instruction("헬퍼 플러그인 배포해줘")
        assert event["status"] == "ok"
        (row,) = event["commands"]
        assert row["status"] == "executed_ok"
        assert "실행 완료" in row["label"]
        assert console.deployed == [("Helper", SAFE_SOURCE)]
        review_events = [e for e in sent if e["type"] == "review_request"]
        assert len(review_events) == 1
        assert review_events[0]["plugin_name"] == "Helper"

    def test_destructive_scan_is_shown_to_the_reviewer(self, tmp_path):
        # AC-MVP-018 ①: the scan result reaches the reviewer surface.
        provider = ScriptedProvider([_deploy_turn("Cleaner", DESTRUCTIVE_SOURCE), _final("완료")])
        session, _, _, sent = _review_session(tmp_path, provider, decide=True)
        session.run_instruction("정리 플러그인 배포해줘")
        (review,) = [e for e in sent if e["type"] == "review_request"]
        assert review["scan"]["destructive"] is True
        assert review["scan"]["findings"][0]["matched_entry"] == "Delete"

    def test_rejected_review_reports_rejection_not_success(self, tmp_path):
        provider = ScriptedProvider([_deploy_turn("Helper", SAFE_SOURCE), _final("끝")])
        session, console, _, sent = _review_session(tmp_path, provider, decide=False)
        event = session.run_instruction("배포해줘")
        (row,) = event["commands"]
        assert row["status"] == "rejected"
        assert "거부됨" in row["label"]
        assert console.deployed == []
        assert "완료" not in event["summary"]

    def test_compile_failure_never_reaches_the_reviewer(self, tmp_path):
        provider = ScriptedProvider([_deploy_turn("Broken", BROKEN_SOURCE), _final("실패 보고")])
        session, console, _, sent = _review_session(tmp_path, provider, decide=True)
        event = session.run_instruction("배포해줘")
        (row,) = event["commands"]
        assert row["status"] == "blocked"
        assert console.deployed == []
        assert [e for e in sent if e["type"] == "review_request"] == []

    def test_close_denies_a_pending_review(self, tmp_path):
        # Quadruple-deny: disconnect while a review is pending -> denied.
        provider = ScriptedProvider([_deploy_turn("Helper", SAFE_SOURCE), _final("끝")])
        console = DeployableFakeConsole()
        session, _, _, sent = _review_session(tmp_path, provider, console=console)
        # Sabotage: never resolve; instead close the session inside notify.
        sent.clear()

        # Rebind: closing on first notify simulates a disconnect mid-review.
        def closing_send(event):
            sent.append(event)
            if event.get("type") == "review_request":
                session.close()

        session._send = closing_send  # test seam: swap the sink
        event = session.run_instruction("배포해줘")
        (row,) = event["commands"]
        assert row["status"] == "rejected"
        assert console.deployed == []


# -- app layer ---------------------------------------------------------------------


def _app_deps(tmp_path, provider):
    console = DeployableFakeConsole()
    audit = AuditLog(tmp_path / "audit")
    approval_channel = ApprovalChannel(timeout_seconds=2.0)
    review_channel = ApprovalChannel(timeout_seconds=2.0, id_prefix="review")
    gate = SafetyGate(console=console, audit=audit, approval_port=approval_channel)
    pipeline = DeployPipeline(
        compile_checker=LuaCompileChecker(),
        ruleset=load_ruleset(),
        deploy_port=gate,
        registry=PluginFlagRegistry(),
        audit=audit,
        review_port=review_channel,
    )
    deps = WebDeps(
        gate=gate,
        provider=provider,
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=approval_channel,
        review_channel=review_channel,
        deploy_pipeline=pipeline,
    )
    return deps, console


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


class TestAppReviewFlow:
    def test_full_review_round_trip_over_websocket(self, tmp_path):
        provider = ScriptedProvider(
            [_deploy_turn("Cleaner", DESTRUCTIVE_SOURCE), _final("배포했습니다")]
        )
        deps, console = _app_deps(tmp_path, provider)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="chat", text="정리 플러그인 배포해줘")
            review = _receive_until(ws, "review_request")
            assert review["plugin_name"] == "Cleaner"
            assert review["scan"]["destructive"] is True
            _send(
                ws,
                type="review_decision",
                request_id=review["request_id"],
                approved=True,
            )
            resolved = _receive_until(ws, "review_resolved")
            assert resolved["approved"] is True
            response = _receive_until(ws, "chat_response")
            assert response["commands"][0]["status"] == "executed_ok"
        assert console.deployed == [("Cleaner", DESTRUCTIVE_SOURCE)]

    def test_stale_review_decision_yields_a_korean_error(self, tmp_path):
        deps, _ = _app_deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()  # initial status
            _send(ws, type="review_decision", request_id="review-999", approved=True)
            event = ws.receive_json()
            assert event["type"] == "error"
            assert event["kind"] == "protocol"
            assert any("가" <= ch <= "힣" for ch in event["message"])
