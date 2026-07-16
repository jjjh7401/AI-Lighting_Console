"""Gate-owned console-stack composition tests (M5 — REQ-MVP-029 preserved).

Production needs ONE place that constructs OscBridge + ConsoleLink + SafetyGate.
That place must live inside ``server/safety`` (the only production package the
AC-MVP-019 import-boundary test allows to touch the OSC send surface) — the web
layer receives the finished gate and never imports the bridge.
"""

from __future__ import annotations

import pytest

from server.safety.bootstrap import ConsoleStack, build_console_stack
from server.safety.console import LinkTimeouts

from .test_safety_e2e_audit import FakeConsoleServer

_FAST = LinkTimeouts(exec_confirm_seconds=1.0, ping_seconds=1.0, state_query_seconds=1.0)


@pytest.fixture()
def fake_console():
    server = FakeConsoleServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()


def _stack(tmp_path, fake_console, **kwargs) -> ConsoleStack:
    stack = build_console_stack(
        send_port=fake_console.port,
        receive_port=0,
        audit_dir=tmp_path / "audit",
        timeouts=_FAST,
        attempt_session_backup=kwargs.pop("attempt_session_backup", False),
        **kwargs,
    )
    fake_console.reply_port = stack.receive_port
    return stack


class TestConsoleStack:
    def test_gate_round_trip_over_udp_loopback(self, tmp_path, fake_console):
        stack = _stack(tmp_path, fake_console)
        try:
            decision = stack.gate.screen(["Store Cue 1"])
            assert decision.cleared
            result = stack.gate.execution_port.execute("Store Cue 1")
            assert result.ok
            assert fake_console.exec_commands == ["Store Cue 1"]
        finally:
            stack.stop()

    def test_heartbeat_reaches_the_fake_console(self, tmp_path, fake_console):
        stack = _stack(tmp_path, fake_console)
        try:
            assert stack.gate.heartbeat() == "online"
            assert fake_console.ping_count == 1
        finally:
            stack.stop()

    def test_default_approval_is_fail_safe_deny(self, tmp_path, fake_console):
        stack = _stack(tmp_path, fake_console)
        try:
            decision = stack.gate.screen(["Delete Sequence 5"])
            assert decision.cleared is False
            assert fake_console.exec_commands == []
        finally:
            stack.stop()

    def test_body_fetcher_rides_the_audited_gate_state_path(self, tmp_path, fake_console):
        # The fake console answers every state query with children [{name: Vocals}]
        # — a CLEAN macro body. With the fetcher wired, expand-or-hold EXPANDS
        # (an unwired default fetcher would hold as unverifiable) and the state
        # query lands in the audit log (kind=state_query, AC-MVP-019 ②).
        stack = _stack(tmp_path, fake_console)
        try:
            decision = stack.gate.screen(["Go Macro 1"])
            assert decision.cleared, decision
            queried = [
                e
                for e in stack.audit.iter_events()
                if e["event"] == "executed" and e["kind"] == "state_query"
            ]
            assert queried, "body fetch must be audited via the gate state port"
        finally:
            stack.stop()

    def test_session_backup_success_is_reported(self, tmp_path, fake_console):
        # The reply port is ephemeral in tests, so the backup attempt happens
        # AFTER wiring (production uses a fixed reply port and attempts at boot).
        stack = _stack(tmp_path, fake_console)
        try:
            assert stack.attempt_session_backup() is True
            assert stack.session_backup_ok is True
            assert "SaveShow" in fake_console.exec_commands
        finally:
            stack.stop()

    def test_session_backup_failure_does_not_crash_boot(self, tmp_path):
        # No console at all: the SaveShow confirmation times out -> BackupError.
        # Boot must survive (REQ-MVP-034 blocks EXECUTIONS, not the server).
        dead_console = FakeConsoleServer()  # never started -> no replies
        stack = build_console_stack(
            send_port=dead_console.port,
            receive_port=0,
            audit_dir=tmp_path / "audit",
            timeouts=LinkTimeouts(
                exec_confirm_seconds=0.1, ping_seconds=0.1, state_query_seconds=0.1
            ),
            attempt_session_backup=True,
        )
        try:
            assert stack.session_backup_ok is False
            assert stack.session_backup_detail
        finally:
            stack.stop()

    def test_backup_manager_is_exposed_for_the_runtime_scheduler(self, tmp_path, fake_console):
        stack = _stack(tmp_path, fake_console)
        try:
            assert stack.backup is not None
            assert stack.backup.tick() is True  # first tick performs a backup
            assert "SaveShow" in fake_console.exec_commands
        finally:
            stack.stop()

    def test_stop_shuts_the_bridge_down(self, tmp_path, fake_console):
        stack = _stack(tmp_path, fake_console)
        stack.stop()
        # After stop the receive port is closed; a second stop must be safe.
        stack.stop()
