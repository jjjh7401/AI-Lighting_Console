"""FastAPI WebSocket app tests (M5 — REQ-MVP-020 server surface).

App-level behaviors over the in-process TestClient: connect handshake,
protocol-error handling, one-instruction-at-a-time busy signaling, lock/status
routing, approval-decision routing, the health endpoint, static UI serving,
and the runtime heartbeat/backup loops (the M4 gap: BackupManager.tick() and
HealthMonitor probing needed a server lifecycle to run on).
"""

from __future__ import annotations

import json
import threading
import time

from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import PROTOCOL_VERSION

from .test_runner_self_correction import ScriptedProvider, _final, _run_turn
from .test_safety_gate import FakeConsole


def _deps(tmp_path, provider, *, console=None, channel=None, **overrides):
    console = console or FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = channel or ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    deps = WebDeps(
        gate=gate,
        provider=provider,
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
        **overrides,
    )
    return deps, console, gate


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


class TestWebSocketBasics:
    def test_connect_receives_an_initial_status_event(self, tmp_path):
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            event = ws.receive_json()
            assert event["type"] == "status"
            assert event["health"] == "online"
            assert event["live_lock"] is False

    def test_chat_round_trip(self, tmp_path):
        provider = ScriptedProvider([_run_turn(["Store Group 3"], "c1"), _final("만들었습니다")])
        deps, console, _gate = _deps(tmp_path, provider)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="chat", text="보컬 그룹 만들어줘")
            event = _receive_until(ws, "chat_response")
            assert event["status"] == "ok"
            assert event["text"] == "만들었습니다"
        assert console.executed == ["Store Group 3"]

    def test_malformed_message_yields_a_korean_protocol_error(self, tmp_path):
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()  # initial status
            ws.send_text("this is not json")
            event = ws.receive_json()
            assert event["type"] == "error"
            assert event["kind"] == "protocol"
            assert any("가" <= ch <= "힣" for ch in event["message"])

    def test_status_request_returns_a_status_event(self, tmp_path):
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()
            _send(ws, type="status_request")
            assert ws.receive_json()["type"] == "status"

    def test_lock_toggle_round_trip(self, tmp_path):
        deps, _console, gate = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()
            _send(ws, type="lock", active=True)
            event = _receive_until(ws, "status")
            assert event["live_lock"] is True
            assert gate.lock.is_active
            _send(ws, type="lock", active=False)
            event = _receive_until(ws, "status")
            assert event["live_lock"] is False

    def test_stale_approval_decision_is_reported(self, tmp_path):
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()
            _send(ws, type="approval_decision", request_id="gone-1", approved=True)
            event = ws.receive_json()
            assert event["type"] == "error"
            assert event["kind"] == "protocol"


class TestBusyGuard:
    def test_second_chat_while_busy_gets_a_busy_event(self, tmp_path):
        release = threading.Event()

        class BlockingProvider:
            name = "scripted"
            model_id = "m"
            supports_prompt_caching = False

            def __init__(self):
                self.calls = 0

            def complete(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    release.wait(5.0)
                return _final("끝")

        deps, _console, _gate = _deps(tmp_path, BlockingProvider())
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()
            _send(ws, type="chat", text="첫 번째 지시")
            _send(ws, type="chat", text="두 번째 지시")
            event = _receive_until(ws, "busy")
            assert any("가" <= ch <= "힣" for ch in event["message"])
            release.set()
            _receive_until(ws, "chat_response")


class TestHttpSurface:
    def test_healthz_reports_gate_truth(self, tmp_path):
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client:
            payload = client.get("/healthz").json()
            assert payload["ok"] is True
            assert payload["health"] == "online"
            assert payload["live_lock"] is False

    def test_built_ui_is_served_when_present(self, tmp_path):
        ui_dist = tmp_path / "dist"
        ui_dist.mkdir()
        (ui_dist / "index.html").write_text("<html>MA3 Copilot</html>", encoding="utf-8")
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]), ui_dist=ui_dist)
        with TestClient(create_app(deps)) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "MA3 Copilot" in response.text

    def test_missing_ui_dist_is_tolerated(self, tmp_path):
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]), ui_dist=tmp_path / "nope")
        with TestClient(create_app(deps)) as client:
            assert client.get("/healthz").status_code == 200


class TestRuntimeLoops:
    def test_heartbeat_loop_pushes_status_changes(self, tmp_path):
        console = FakeConsole()
        console.ping_ok = False  # first probe classifies console_offline
        deps, _console, _gate = _deps(
            tmp_path,
            ScriptedProvider([]),
            console=console,
            heartbeat_interval_seconds=0.02,
        )
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            # The loop starts at app startup: the offline transition may land
            # BEFORE the connect (then the initial snapshot already shows it)
            # or after (then a status push arrives) — accept either.
            event = ws.receive_json()
            assert event["type"] == "status"
            while event["type"] != "status" or event["health"] != "console_offline":
                event = _receive_until(ws, "status")
            assert event["health"] == "console_offline"
            assert event["executions_blocked"] is True

    def test_backup_loop_ticks_the_backup_manager(self, tmp_path):
        deps, _console, gate = _deps(tmp_path, ScriptedProvider([]), backup_poll_seconds=0.02)
        manager = gate.use_showfile_backup(interval_seconds=0.0)
        deps.backup_manager = manager
        with TestClient(create_app(deps)):
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and not manager.history:
                time.sleep(0.02)
        assert manager.history, "the runtime backup loop never ticked"

    def test_backup_loop_survives_backup_failures(self, tmp_path):
        deps, console, gate = _deps(tmp_path, ScriptedProvider([]), backup_poll_seconds=0.02)
        console.fail_on["SaveShow"] = "no showfile loaded"
        manager = gate.use_showfile_backup(interval_seconds=0.0)
        deps.backup_manager = manager
        with TestClient(create_app(deps)) as client:
            time.sleep(0.1)
            assert client.get("/healthz").status_code == 200  # app still alive
        failures = [e for e in deps.audit.iter_events() if e["event"] == "backup_tick_failed"]
        assert failures, "backup failures must be audited"
