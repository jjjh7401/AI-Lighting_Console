"""Deploy-shell health surfacing + error-UX evidence (M5 — DEPLOY-001).

The distribution shell surfaces the SAME MVP HealthMonitor states and the SAME
REQ-MVP-044 error scrub — this module is the DEPLOY-scoped evidence that:

- AC-DEPLOY-008 (REQ-DEPLOY-012/013): the three health states (online /
  console_offline / responder_degraded) surface through the status-push snapshot
  and a full transition cycle — including recovery back to ``online`` — is
  reflected immediately.
- AC-DEPLOY-012 ③ (REQ-DEPLOY-020, REQ-MVP-044 extension): a missing/invalid API
  key raising an SDK auth error yields a human-friendly Korean message that
  routes the operator to settings, with the raw SDK original scrubbed from the
  chat surface (diagnostic/audit log only) — 0 stack traces, 0 raw SDK text.

This surface introduces NO OSC-send path — it reads the monitor state and the
error catalog only.
"""

from __future__ import annotations

import json

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.monitor import HealthMonitor
from server.web.approval_bridge import ApprovalChannel
from server.web.korean_errors import KOREAN_ERROR_MESSAGES
from server.web.session import ChatSession

from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

_PREFIX = "PREFIX"
# A secret-shaped raw SDK original that must NEVER reach the chat surface.
_SECRET_KEY = "sk-ant-SECRET-abcdef0123456789"
_RAW_SDK_DETAIL = (
    f"AuthenticationError(401): invalid x-api-key {_SECRET_KEY} — "
    "Traceback (most recent call last): raise AuthenticationError"
)


def _session(tmp_path, provider, *, monitor=None):
    """A minimal ChatSession over a real gate — the DEPLOY health/error surface."""
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate_kwargs = {} if monitor is None else {"monitor": monitor}
    gate = SafetyGate(console=console, audit=audit, approval_port=channel, **gate_kwargs)
    sent: list[dict] = []
    session = ChatSession(
        gate=gate,
        provider=provider,
        system_prefix=_PREFIX,
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
    )
    return session, audit, sent


class TestHealthSurfacingTransitions:
    """AC-DEPLOY-008 — three states surface + a full transition cycle reflects."""

    def test_full_transition_cycle_surfaces_each_state(self, tmp_path):
        # A monitor with a fixed clock so ``responder_degraded`` (recent activity
        # then a timeout) is deterministic within the activity window.
        now = [1000.0]
        monitor = HealthMonitor(clock=lambda: now[0], activity_window_seconds=15.0)
        session, _audit, _sent = _session(tmp_path, ScriptedProvider([]), monitor=monitor)

        # 1) Healthy — a fresh monitor is ``online`` (nothing blocked).
        assert session.status_snapshot()["health"] == HealthMonitor.ONLINE
        assert session.status_snapshot()["executions_blocked"] is False

        # 2) Console무응답 — a timeout with NO prior traffic at all → console_offline
        #    (blocks new executions).
        monitor.note_ping_timeout()
        offline = session.status_snapshot()
        assert offline["health"] == HealthMonitor.CONSOLE_OFFLINE
        assert offline["executions_blocked"] is True

        # 3) Responder무응답 — recent native traffic but the responder is silent
        #    within the activity window → responder_degraded.
        monitor.note_activity()
        now[0] += 1.0  # still inside the 15s window
        monitor.note_ping_timeout()
        degraded = session.status_snapshot()
        assert degraded["health"] == HealthMonitor.RESPONDER_DEGRADED
        assert degraded["executions_blocked"] is True

        # 4) 회복 — a successful heartbeat clears the degraded state to online.
        monitor.note_ping_success()
        recovered = session.status_snapshot()
        assert recovered["health"] == HealthMonitor.ONLINE
        assert recovered["executions_blocked"] is False

    def test_status_snapshot_is_the_status_push_payload(self, tmp_path):
        # REQ-DEPLOY-013: the snapshot the heartbeat loop pushes is a v1 status
        # event carrying the live health — so a transition reflects immediately.
        monitor = HealthMonitor()
        session, _audit, _sent = _session(tmp_path, ScriptedProvider([]), monitor=monitor)
        monitor.note_ping_timeout()  # no prior activity → console_offline
        snapshot = session.status_snapshot()
        assert snapshot["type"] == "status"
        assert snapshot["health"] == HealthMonitor.CONSOLE_OFFLINE


class TestKeyErrorScrubRoutesToSettings:
    """AC-DEPLOY-012 ③ — key auth error: friendly Korean + 0 raw SDK on surface."""

    def _auth_raising_provider(self):
        from server.llm.errors import ProviderError

        class _AuthRaisingProvider:
            name = "anthropic"
            model_id = "claude-opus-4-8"
            supports_prompt_caching = False

            def complete(self, **_kwargs):
                # An SDK auth failure at provider-client use (missing/invalid key)
                # normalized to the internal ProviderError, raw_detail carrying the
                # secret-bearing SDK original.
                raise ProviderError(
                    kind="auth",
                    provider="anthropic",
                    retryable=False,
                    raw_detail=_RAW_SDK_DETAIL,
                )

        return _AuthRaisingProvider()

    def test_auth_error_shows_settings_guidance_without_raw_sdk(self, tmp_path):
        session, audit, sent = _session(tmp_path, self._auth_raising_provider())
        event = session.run_instruction("보컬 그룹 만들어줘")

        # (1) A Korean auth message routing the operator to key settings.
        assert event["type"] == "error"
        assert event["kind"] == "auth"
        assert event["message"] == KOREAN_ERROR_MESSAGES["auth"]
        assert "API 키" in event["message"]  # routes to settings/key entry

        # (2) 0 stack traces / 0 raw SDK original anywhere on the chat surface.
        surface = json.dumps(sent, ensure_ascii=False)
        for marker in (_SECRET_KEY, "Traceback", "AuthenticationError", "x-api-key", "raise "):
            assert marker not in surface, f"raw SDK text {marker!r} leaked to the surface"

        # (3) the raw detail IS preserved in the diagnostic (audit) log only.
        errors = [e for e in audit.iter_events() if e["event"] == "provider_error"]
        assert len(errors) == 1
        assert _SECRET_KEY in errors[0]["raw_detail"]

    def test_catalog_auth_message_is_scrub_safe_korean(self, tmp_path):
        # The catalog entry itself carries no SDK vocabulary (REQ-MVP-044 lineage).
        message = KOREAN_ERROR_MESSAGES["auth"]
        assert any("가" <= ch <= "힣" for ch in message)
        for marker in ("Error", "Exception", "Traceback", "api-key", "401"):
            assert marker not in message
