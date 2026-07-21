"""`/ws` transport handshake — Origin allowlist + per-launch token (M7.1).

REQ-DEPLOY-002a / AC-DEPLOY-025 (accept/reject matrix) + AC-DEPLOY-029 (token
secrecy). The gate closes FEAS-9: before M7.1 the ``/ws`` endpoint called
``accept()`` with zero origin/token/CORS checking, so any local process or
browser tab could drive the live console (cross-site WebSocket hijacking).

Two origin CLASSES, per plan.md §M7.1 — this is the whole design:

  * **Stage-2 (Tauri) origins** — the token is deliverable over Tauri IPC
    (an in-process channel no other local process can read), so the token is
    **REQUIRED**: a missing or wrong token is rejected.
  * **Stage-1 (localhost browser) origins** — a browser has no Tauri IPC, and
    every alternative delivery (disk file, unauthenticated loopback endpoint)
    is readable by the very local process the token is supposed to stop. So in
    Stage-1 the **Origin allowlist is the real CSWSH closer** and the token is
    **defense-in-depth only**: absent is allowed, but a WRONG token is still
    rejected (an attacker guessing gains nothing).

Both classes reject an origin outside the allowlist, and both compare the
token in constant time (``hmac.compare_digest``).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.deploy.keystore import REDACTED, scrub_environ
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.handshake import (
    BASE_SUBPROTOCOL,
    TOKEN_SUBPROTOCOL_PREFIX,
    HandshakePolicy,
    browser_origins_for,
    evaluate_handshake,
    token_from_subprotocols,
)
from server.web.launcher import LAUNCH_TOKEN_ENV, generate_launch_token
from server.web.messages import PROTOCOL_VERSION

from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

TOKEN = "test-launch-token-abcdef0123456789"
TAURI_ORIGIN = "tauri://localhost"
BROWSER_ORIGIN = "http://127.0.0.1:8765"
EVIL_ORIGIN = "https://evil.example"


def _policy(**overrides) -> HandshakePolicy:
    fields = {
        "token": TOKEN,
        "trusted_origins": (TAURI_ORIGIN,),
        "browser_origins": (BROWSER_ORIGIN,),
    }
    fields.update(overrides)
    return HandshakePolicy(**fields)


def _app(tmp_path, *, handshake):
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=FakeConsole(), audit=audit, approval_port=channel)
    deps = WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
        handshake=handshake,
    )
    return create_app(deps)


def _protocols(token: str) -> list[str]:
    return [BASE_SUBPROTOCOL, f"{TOKEN_SUBPROTOCOL_PREFIX}{token}"]


def _assert_rejected(client: TestClient, **connect_kwargs) -> None:
    """Assert the upgrade is refused BEFORE ``accept()``.

    A pre-accept close surfaces to the TestClient as ``WebSocketDisconnect``
    raised by ``websocket_connect`` itself — i.e. the session was never handed a
    connection, so the client reached no ChatSession, no gate and no console.
    """
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws", **connect_kwargs):
        pass  # pragma: no cover — the connect must raise


# ------------------------------------------------------------------ AC-DEPLOY-025
# Pure-decision matrix. The evaluator is a pure function so every row of the
# accept/reject matrix is asserted without a socket.


class TestHandshakeDecisionMatrix:
    def test_origin_outside_the_allowlist_is_rejected(self):
        decision = evaluate_handshake(
            _policy(), origin=EVIL_ORIGIN, subprotocols=_protocols(TOKEN)
        )
        assert decision.accepted is False
        assert decision.reason == "origin_not_allowed"

    def test_a_missing_origin_is_rejected(self):
        # Fail-closed: no Origin means the connection is not attributable to an
        # allowlisted surface. Browsers always send one for a WebSocket upgrade.
        decision = evaluate_handshake(_policy(), origin=None, subprotocols=_protocols(TOKEN))
        assert decision.accepted is False
        assert decision.reason == "origin_missing"

    def test_stage2_origin_without_a_token_is_rejected(self):
        # Tauri CAN deliver the token over IPC, so its absence is a real failure.
        decision = evaluate_handshake(_policy(), origin=TAURI_ORIGIN, subprotocols=[])
        assert decision.accepted is False
        assert decision.reason == "token_missing"

    def test_stage2_origin_with_a_wrong_token_is_rejected(self):
        decision = evaluate_handshake(
            _policy(), origin=TAURI_ORIGIN, subprotocols=_protocols("wrong-token")
        )
        assert decision.accepted is False
        assert decision.reason == "token_mismatch"

    def test_stage2_origin_with_the_correct_token_is_accepted(self):
        decision = evaluate_handshake(
            _policy(), origin=TAURI_ORIGIN, subprotocols=_protocols(TOKEN)
        )
        assert decision.accepted is True
        assert decision.reason == ""
        assert decision.subprotocol == BASE_SUBPROTOCOL

    def test_stage1_browser_origin_without_a_token_is_accepted(self):
        # plan §M7.1: a browser cannot receive the token leak-resistantly before
        # M7.4, so the Origin allowlist is Stage-1's real CSWSH closer and the
        # token is defense-in-depth only. Rejecting here would break Stage-1.
        decision = evaluate_handshake(_policy(), origin=BROWSER_ORIGIN, subprotocols=[])
        assert decision.accepted is True
        assert decision.subprotocol is None

    def test_stage1_browser_origin_with_a_wrong_token_is_still_rejected(self):
        # Defense-in-depth is not "anything goes": an offered token must match.
        decision = evaluate_handshake(
            _policy(), origin=BROWSER_ORIGIN, subprotocols=_protocols("wrong-token")
        )
        assert decision.accepted is False
        assert decision.reason == "token_mismatch"

    def test_stage1_browser_origin_with_the_correct_token_is_accepted(self):
        decision = evaluate_handshake(
            _policy(), origin=BROWSER_ORIGIN, subprotocols=_protocols(TOKEN)
        )
        assert decision.accepted is True
        assert decision.subprotocol == BASE_SUBPROTOCOL

    def test_the_token_comparison_is_constant_time(self):
        # AC-DEPLOY-025 ③: the compare must be hmac.compare_digest, not `==`.
        source = Path(__file__).resolve().parents[1] / "web" / "handshake.py"
        text = source.read_text(encoding="utf-8")
        assert "hmac.compare_digest" in text
        assert "compare_digest(" in text


class TestTokenSubprotocolParsing:
    def test_extracts_the_token_from_the_prefixed_subprotocol(self):
        assert token_from_subprotocols(_protocols(TOKEN)) == TOKEN

    def test_returns_none_when_no_token_subprotocol_is_offered(self):
        assert token_from_subprotocols([BASE_SUBPROTOCOL]) is None
        assert token_from_subprotocols([]) is None
        assert token_from_subprotocols(None) is None


class TestBrowserOriginsForHost:
    def test_covers_both_loopback_spellings_of_the_served_port(self):
        origins = browser_origins_for("127.0.0.1", 8765)
        assert "http://127.0.0.1:8765" in origins
        assert "http://localhost:8765" in origins

    def test_a_bind_all_host_still_yields_loopback_origins(self):
        origins = browser_origins_for("0.0.0.0", 9000)
        assert "http://127.0.0.1:9000" in origins
        assert "http://localhost:9000" in origins


# ------------------------------------------- AC-DEPLOY-025 over the real endpoint


class TestWebSocketEndpointGate:
    def test_disallowed_origin_never_reaches_accept(self, tmp_path):
        client = TestClient(_app(tmp_path, handshake=_policy()))
        _assert_rejected(
            client, headers={"origin": EVIL_ORIGIN}, subprotocols=_protocols(TOKEN)
        )

    def test_stage2_origin_missing_token_never_reaches_accept(self, tmp_path):
        client = TestClient(_app(tmp_path, handshake=_policy()))
        _assert_rejected(client, headers={"origin": TAURI_ORIGIN})

    def test_wrong_token_never_reaches_accept(self, tmp_path):
        client = TestClient(_app(tmp_path, handshake=_policy()))
        _assert_rejected(
            client, headers={"origin": TAURI_ORIGIN}, subprotocols=_protocols("wrong-token")
        )

    def test_correct_token_and_origin_connects_and_speaks_protocol_v1(self, tmp_path):
        client = TestClient(_app(tmp_path, handshake=_policy()))
        with client.websocket_connect(
            "/ws", headers={"origin": TAURI_ORIGIN}, subprotocols=_protocols(TOKEN)
        ) as ws:
            event = ws.receive_json()
        assert event["v"] == PROTOCOL_VERSION
        assert event["type"] == "status"

    def test_stage1_browser_origin_connects_without_a_token(self, tmp_path):
        # The Stage-1 regression guard: the packaged browser app must keep working.
        client = TestClient(_app(tmp_path, handshake=_policy()))
        with client.websocket_connect("/ws", headers={"origin": BROWSER_ORIGIN}) as ws:
            event = ws.receive_json()
        assert event["type"] == "status"

    def test_no_policy_configured_leaves_the_endpoint_open(self, tmp_path):
        # Backward compatibility: dev runs / tests that compose WebDeps without a
        # handshake policy behave exactly as before M7.1.
        client = TestClient(_app(tmp_path, handshake=None))
        with client.websocket_connect("/ws") as ws:
            event = ws.receive_json()
        assert event["type"] == "status"


# ------------------------------------------- AC-DEPLOY-025 ⑤ protocol-v1 regression


class TestProtocolV1Unchanged:
    def test_the_message_schema_module_knows_nothing_about_the_handshake(self):
        # The handshake is transport-layer ONLY (plan §M7.1): protocol v1,
        # messages.py and PROTOCOL.md stay unchanged.
        web = Path(__file__).resolve().parents[1] / "web"
        messages = (web / "messages.py").read_text(encoding="utf-8").lower()
        for leaked in ("origin", "subprotocol", "launch_token", "handshake"):
            assert leaked not in messages, f"protocol v1 schema leaked {leaked!r}"

    def test_the_protocol_document_still_declares_version_1(self):
        web = Path(__file__).resolve().parents[1] / "web"
        doc = (web / "PROTOCOL.md").read_text(encoding="utf-8")
        assert '"v": 1' in doc or "`v`" in doc
        assert PROTOCOL_VERSION == 1

    def test_a_gated_connection_emits_the_same_status_event_as_an_ungated_one(self, tmp_path):
        gated = TestClient(_app(tmp_path / "a", handshake=_policy()))
        open_app = TestClient(_app(tmp_path / "b", handshake=None))
        with gated.websocket_connect(
            "/ws", headers={"origin": TAURI_ORIGIN}, subprotocols=_protocols(TOKEN)
        ) as ws:
            gated_event = ws.receive_json()
        with open_app.websocket_connect("/ws") as ws:
            open_event = ws.receive_json()
        assert sorted(gated_event.keys()) == sorted(open_event.keys())
        assert gated_event == open_event


# ------------------------------------------------------------------ AC-DEPLOY-029


class TestLaunchTokenSecrecy:
    def test_each_launch_generates_a_fresh_unguessable_token(self):
        first = generate_launch_token()
        second = generate_launch_token()
        assert first != second
        assert len(first) >= 32
        assert first.isascii() and " " not in first

    def test_the_token_env_var_is_redacted_by_the_crash_dump_scrubber(self):
        scrubbed = scrub_environ({LAUNCH_TOKEN_ENV: TOKEN, "PATH": "/usr/bin"})
        assert scrubbed[LAUNCH_TOKEN_ENV] == REDACTED
        assert scrubbed["PATH"] == "/usr/bin"

    def test_the_token_appears_in_zero_files_the_app_writes(self, tmp_path):
        # AC-DEPLOY-029 ①, the same discipline as the AC-DEPLOY-004 key scan:
        # exercise a full connect + audit-writing lifecycle, then scan every file
        # the app wrote for the token string.
        client = TestClient(_app(tmp_path, handshake=_policy()))
        # A rejected connect is the interesting path: the token is in scope in
        # the audit record the reject writes, so a careless log line would leak.
        _assert_rejected(
            client, headers={"origin": TAURI_ORIGIN}, subprotocols=_protocols("wrong")
        )
        with client.websocket_connect(
            "/ws", headers={"origin": TAURI_ORIGIN}, subprotocols=_protocols(TOKEN)
        ) as ws:
            ws.receive_json()
        written = [p for p in tmp_path.rglob("*") if p.is_file()]
        assert written, "no files written — the scan would be vacuously satisfied"
        offenders = [
            p.as_posix()
            for p in written
            if TOKEN in p.read_text(encoding="utf-8", errors="replace")
        ]
        assert offenders == [], f"per-launch token leaked to disk: {offenders}"

    def test_the_ui_html_carries_no_token_meta_injection(self):
        # AC-DEPLOY-029 ② — the index.html meta-injection option was DROPPED in
        # the plan-audit remediation (D4a): it would write the token to disk.
        root = Path(__file__).resolve().parents[2]
        for html in (root / "ui" / "index.html", root / "ui" / "dist" / "index.html"):
            if not html.exists():
                continue
            text = html.read_text(encoding="utf-8").lower()
            assert "copilot-token" not in text
            assert "launch_token" not in text
            assert "launch-token" not in text

    def test_the_serve_wiring_never_writes_the_token_to_a_file(self):
        # Structural guard: the token crosses process boundaries via env/memory
        # only. A write_text/open(...,"w") of the token in the wiring modules is
        # the exact AC-DEPLOY-029 violation shape.
        web = Path(__file__).resolve().parents[1] / "web"
        for name in ("serve.py", "launcher.py", "handshake.py"):
            text = (web / name).read_text(encoding="utf-8")
            for line in text.splitlines():
                if "write_text" in line or "json.dump" in line:
                    assert "token" not in line.lower(), f"{name}: {line.strip()}"


class TestServeWiring:
    def test_build_runtime_composes_a_handshake_policy(self, monkeypatch):
        from server.web import serve

        monkeypatch.setenv(LAUNCH_TOKEN_ENV, TOKEN)
        args = serve.parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = serve.build_runtime(args)
        try:
            policy = app.state.deps.handshake
        finally:
            stack.stop()
        assert policy is not None
        assert policy.token == TOKEN
        assert f"http://127.0.0.1:{args.port}" in policy.browser_origins
        assert policy.trusted_origins  # Tauri/custom-scheme origins for Stage-2

    def test_build_runtime_generates_a_token_when_the_env_is_unset(self, monkeypatch):
        from server.web import serve

        monkeypatch.delenv(LAUNCH_TOKEN_ENV, raising=False)
        args = serve.parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = serve.build_runtime(args)
        try:
            policy = app.state.deps.handshake
        finally:
            stack.stop()
        assert policy is not None
        assert len(policy.token) >= 32
        assert os.environ.get(LAUNCH_TOKEN_ENV) is None  # never leaks into the parent env
