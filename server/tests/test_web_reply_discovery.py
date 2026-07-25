"""Reply-port discovery tests (REQ-DEPLOY-018/026/032 follow-up).

The root defect these pin: a grandMA3 OSC entry has ONE port used for BOTH
directions, so the port the console replies THROUGH lives in the console's OSC
table while the port the app listens ON lives in the app's settings. Two numbers,
two places, no feedback when they drift — and the drift surfaces as a generic
``console_offline`` that sends the operator to check things that are already
fine.

Discovery answers "where is the console actually replying?" by listening on a
small, explicit candidate set while the EXISTING gate send path emits one ping.

The boundaries pinned here are the ones a plausible-looking implementation gets
wrong:

* it never adopts a port by itself (REQ-DEPLOY-026 — the app must not change its
  effective port behind the operator's back);
* it opens no new OSC send surface (AC-MVP-019 / AC-DEPLOY-027) — the ping is the
  gate's own heartbeat, injected;
* it never binds the console's INPUT port, which would hijack the app's own
  command stream (a specific bind beats a wildcard holder for delivery);
* it does not run at all while the configured port works.
"""

from __future__ import annotations

import re
import socket
from pathlib import Path

import pytest

from server.web.reply_discovery import (
    ReplyPortDiagnostic,
    ReplyPortMismatch,
    ReplyProbeResult,
    candidate_ports,
    discover_reply_port,
)

CONFIGURED = 9000
CONSOLE = 8000


def _send_to(port: int, payload: bytes = b"/copilot/feedback\x00\x00\x00,s\x00\x00") -> None:
    """Emit one datagram the way the console's responder replies."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(payload, ("127.0.0.1", port))
    finally:
        sock.close()


def _bindable_candidate(preferred: int) -> int:
    """A candidate port nothing else on this host currently holds.

    The probe can only observe a port it can bind, so a hardcoded candidate
    fails — or passes vacuously, which is worse — whenever something else holds
    it. Not hypothetical: a running copilot-server binds its receive port, and
    the candidate window covers 8995-9005. Measured 2026-07-25, two stray dev
    servers held 9001 and 9005 and this file reported a defect that was not
    there. Falls back through the rest of the candidate set, then skips.
    """
    for port in (preferred, *candidate_ports(receive_port=CONFIGURED, console_port=CONSOLE)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            continue
        finally:
            sock.close()
        return port
    pytest.skip("every reply-discovery candidate port is held by another process")


class TestCandidateSet:
    def test_the_candidate_set_is_small_bounded_and_nearest_first(self):
        candidates = candidate_ports(receive_port=CONFIGURED, console_port=CONSOLE)
        assert candidates == (9001, 8999, 9002, 8998, 9003, 8997, 9004, 8996, 9005, 8995)
        assert len(candidates) <= 10, "a candidate set this size is a scan, not a probe"

    def test_the_configured_receive_port_is_never_a_candidate(self):
        # It is the entry condition, not a hypothesis: discovery only runs
        # because that port produced no pong, and our own receiver still holds it.
        assert CONFIGURED not in candidate_ports(receive_port=CONFIGURED, console_port=CONSOLE)

    def test_the_console_input_port_is_never_a_candidate(self):
        # Binding it would be actively harmful, not merely useless: a SPECIFIC
        # bind wins delivery over the console's WILDCARD hold (measured on
        # darwin), so a listener on the console's input port would swallow the
        # app's OWN outbound commands.
        assert CONSOLE not in candidate_ports(receive_port=8001, console_port=CONSOLE)
        assert candidate_ports(receive_port=8001, console_port=CONSOLE) == (
            8002,
            # 8000 (the console's OSC input) is dropped, not substituted
            8003,
            7999,
            8004,
            7998,
            8005,
            7997,
            8006,
            7996,
        )

    def test_out_of_range_neighbours_are_dropped_not_clamped(self):
        assert candidate_ports(receive_port=3, console_port=CONSOLE) == (4, 2, 5, 1, 6, 7, 8)
        assert all(1 <= p <= 65535 for p in candidate_ports(receive_port=65534, console_port=1))

    def test_the_observed_live_drift_is_inside_the_set(self):
        # 9000 -> 9005 is the drift this unit exists for; it is why the
        # neighbourhood is +/-5 and not +/-1.
        assert 9005 in candidate_ports(receive_port=9000, console_port=CONSOLE)


class TestDiscovery:
    def test_a_pong_on_a_neighbour_port_is_found_and_reported(self):
        neighbour = _bindable_candidate(9003)

        def _ping() -> None:
            _send_to(neighbour)

        result = discover_reply_port(
            send_ping=_ping,
            receive_host="127.0.0.1",
            receive_port=CONFIGURED,
            console_port=CONSOLE,
            timeout=1.0,
        )
        assert result.observed_port == neighbour
        assert result.mismatch == ReplyPortMismatch(configured=CONFIGURED, observed=neighbour)

    def test_silence_reports_nothing_rather_than_guessing(self):
        result = discover_reply_port(
            send_ping=lambda: None,
            receive_host="127.0.0.1",
            receive_port=CONFIGURED,
            console_port=CONSOLE,
            timeout=0.2,
        )
        assert result.observed_port is None
        assert result.mismatch is None

    def test_foreign_traffic_is_not_mistaken_for_a_responder_reply(self):
        # Something else on the machine sending to a neighbour port must not be
        # reported as "the console replies here" — that would be a confidently
        # wrong instruction to change a working setting.
        neighbour = _bindable_candidate(9002)

        def _ping() -> None:
            _send_to(neighbour, payload=b"\x00\x01\x02\x03not-osc")

        result = discover_reply_port(
            send_ping=_ping,
            receive_host="127.0.0.1",
            receive_port=CONFIGURED,
            console_port=CONSOLE,
            timeout=0.3,
        )
        assert result.observed_port is None

    def test_the_state_address_counts_as_a_responder_reply(self):
        neighbour = _bindable_candidate(9001)

        def _ping() -> None:
            _send_to(neighbour, payload=b"/copilot/state\x00\x00,s\x00\x00")

        result = discover_reply_port(
            send_ping=_ping,
            receive_host="127.0.0.1",
            receive_port=CONFIGURED,
            console_port=CONSOLE,
            timeout=1.0,
        )
        assert result.observed_port == neighbour

    def test_every_candidate_socket_is_released(self):
        def _ping() -> None:
            _send_to(9001)

        result = discover_reply_port(
            send_ping=_ping,
            receive_host="127.0.0.1",
            receive_port=CONFIGURED,
            console_port=CONSOLE,
            timeout=1.0,
        )
        # A leaked listener would squat a port the operator may later configure,
        # turning a diagnosis into the very failure it diagnoses.
        for port in result.listened:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                probe.bind(("127.0.0.1", port))
            finally:
                probe.close()

    def test_a_candidate_that_cannot_be_bound_is_reported_not_silently_dropped(self):
        holder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        holder.bind(("127.0.0.1", 0))
        port = holder.getsockname()[1]
        try:
            result = discover_reply_port(
                send_ping=lambda: None,
                receive_host="127.0.0.1",
                receive_port=CONFIGURED,
                console_port=CONSOLE,
                timeout=0.05,
                candidates=(port,),
            )
            assert result.unbindable == (port,)
            assert result.listened == ()
            assert result.observed_port is None
        finally:
            holder.close()

    def test_a_failing_ping_never_raises_out_of_the_diagnosis(self):
        def _boom() -> None:
            raise RuntimeError("console link is down")

        result = discover_reply_port(
            send_ping=_boom,
            receive_host="127.0.0.1",
            receive_port=CONFIGURED,
            console_port=CONSOLE,
            timeout=0.05,
        )
        assert result.observed_port is None
        assert result.send_error is not None

    def test_the_ping_is_sent_exactly_once(self):
        calls: list[int] = []
        discover_reply_port(
            send_ping=lambda: calls.append(1),
            receive_host="127.0.0.1",
            receive_port=CONFIGURED,
            console_port=CONSOLE,
            timeout=0.05,
        )
        assert calls == [1], "discovery must not spray pings across the candidate set"

    def test_listeners_are_bound_before_the_ping_is_sent(self):
        # Otherwise the reply races the bind and discovery reports a false
        # negative on a correctly-drifted console.
        order: list[str] = []

        def _ping() -> None:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                probe.bind(("127.0.0.1", 9001))
            except OSError:
                order.append("already-bound")
            else:
                order.append("still-free")
            finally:
                probe.close()

        discover_reply_port(
            send_ping=_ping,
            receive_host="127.0.0.1",
            receive_port=CONFIGURED,
            console_port=CONSOLE,
            timeout=0.05,
        )
        assert order == ["already-bound"]


class TestNoSilentAdoption:
    """REQ-DEPLOY-026 — the app never changes its effective port by itself."""

    def test_the_result_carries_no_way_to_apply_itself(self):
        result = ReplyProbeResult(
            configured_port=CONFIGURED,
            candidates=(9005,),
            listened=(9005,),
            unbindable=(),
            observed_port=9005,
        )
        for mutator in ("apply", "adopt", "save", "write", "commit"):
            assert not hasattr(result, mutator), (
                f"ReplyProbeResult.{mutator} — a diagnosis that can apply itself "
                "is a silent port drift (REQ-DEPLOY-026)"
            )

    def test_the_module_never_writes_settings_or_rebinds(self):
        source = (Path(__file__).resolve().parents[1] / "web" / "reply_discovery.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("save_user_settings", "resolve_effective_settings", "BridgeConfig"):
            assert forbidden not in source, f"reply_discovery.py reaches {forbidden!r}"

    def test_the_module_stays_off_the_osc_send_surface(self):
        # Same boundary as test_architecture.py, asserted at the file most
        # tempted to cross it: a discovery that "just" borrowed the bridge's
        # socket would be a second send surface. Checked on IMPORT lines, so the
        # module may still NAME the receiver it models in prose.
        source = (Path(__file__).resolve().parents[1] / "web" / "reply_discovery.py").read_text(
            encoding="utf-8"
        )
        imported = re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.MULTILINE)
        for module in imported:
            assert not module.startswith(("server.bridge", "pythonosc")), (
                f"reply_discovery.py imports {module}"
            )
        assert "server.bridge.osc._ReuseAddrOSCUDPServer" in source, (
            "the module no longer documents which receiver its bind models"
        )

    def test_the_module_opens_no_new_osc_send_surface(self):
        source = (Path(__file__).resolve().parents[1] / "web" / "reply_discovery.py").read_text(
            encoding="utf-8"
        )
        for transmit in ("sendto", "sendall", ".send("):
            assert transmit not in source, (
                f"reply_discovery.py calls {transmit!r} — the ping must come from "
                "the gate's own send path (AC-MVP-019 / AC-DEPLOY-027)"
            )
        # Positive control: the boundary is not vacuous — the module really does
        # depend on an injected send.
        assert "send_ping" in source


class TestDiagnosticGate:
    """When discovery may run at all, and what it costs on the status path."""

    def _diag(self, **kwargs):
        runs: list[int] = []

        def _discover() -> ReplyProbeResult:
            runs.append(1)
            return ReplyProbeResult(
                configured_port=CONFIGURED,
                candidates=(9005,),
                listened=(9005,),
                unbindable=(),
                observed_port=9005,
            )

        clock = kwargs.pop("clock", None)
        diagnostic = ReplyPortDiagnostic(
            discover=_discover,
            spawn=lambda fn: fn(),  # synchronous in tests
            clock=clock or (lambda: 0.0),
            **kwargs,
        )
        return diagnostic, runs

    def test_the_first_call_returns_nothing_and_schedules_the_run(self):
        diagnostic, runs = self._diag()
        # Synchronous spawn: the run has completed by the time verdict() returns,
        # but the CONTRACT is that verdict() never waits for it.
        assert diagnostic.verdict() is None
        assert runs == [1]
        assert diagnostic.verdict() == ReplyPortMismatch(configured=CONFIGURED, observed=9005)

    def test_the_result_is_cached_within_the_cooldown(self):
        diagnostic, runs = self._diag(min_interval_seconds=30.0)
        for _ in range(5):
            diagnostic.verdict()
        assert runs == [1], "discovery re-ran inside its cooldown"

    def test_the_cooldown_expires(self):
        now = [0.0]
        diagnostic, runs = self._diag(min_interval_seconds=10.0, clock=lambda: now[0])
        diagnostic.verdict()
        now[0] = 11.0
        diagnostic.verdict()
        assert runs == [1, 1]

    def test_verdict_never_blocks_on_the_run(self):
        # The status snapshot is built on the asyncio event loop; a discovery
        # that took its ping timeout inline would stall the whole server.
        started: list[str] = []
        diagnostic = ReplyPortDiagnostic(
            discover=lambda: pytest.fail("discovery ran on the caller's thread"),
            spawn=lambda fn: started.append("spawned"),
            clock=lambda: 0.0,
        )
        assert diagnostic.verdict() is None
        assert started == ["spawned"]

    def test_a_raising_discovery_never_breaks_the_status_surface(self):
        def _boom() -> ReplyProbeResult:
            raise OSError("no sockets today")

        diagnostic = ReplyPortDiagnostic(discover=_boom, spawn=lambda fn: fn(), clock=lambda: 0.0)
        assert diagnostic.verdict() is None
        assert diagnostic.verdict() is None

    def test_a_completed_run_notifies_so_the_verdict_actually_reaches_the_ui(self):
        # Health does not change when discovery finishes, and the heartbeat loop
        # only pushes status on a CHANGE — without this callback the diagnosis
        # would be computed and never shown.
        notified: list[int] = []
        diagnostic, _runs = self._diag(on_complete=lambda: notified.append(1))
        diagnostic.verdict()
        assert notified == [1]

    def test_an_unchanged_verdict_does_not_re_notify(self):
        notified: list[int] = []
        now = [0.0]
        diagnostic, _runs = self._diag(
            min_interval_seconds=1.0,
            clock=lambda: now[0],
            on_complete=lambda: notified.append(1),
        )
        diagnostic.verdict()
        now[0] = 5.0
        diagnostic.verdict()
        assert notified == [1], "a stable verdict pushed a redundant status frame"


# ------------------------------------------------ mismatch diagnosis on the wire


def _mismatch_session(tmp_path, *, console_input, reply_port_probe):
    from server.safety.approval import ApprovalRequest  # noqa: F401 (import cost only)
    from server.safety.audit import AuditLog
    from server.safety.gate import SafetyGate
    from server.web.approval_bridge import ApprovalChannel
    from server.web.session import ChatSession

    from .test_runner_self_correction import ScriptedProvider
    from .test_safety_gate import FakeConsole

    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=FakeConsole(), audit=audit, approval_port=channel)
    session = ChatSession(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        send_event=lambda event: None,
        approval_channel=channel,
        console_input_probe=lambda: console_input,
        reply_port_probe=reply_port_probe,
    )
    return session, gate


class TestMismatchReachesTheStatusSurface:
    """The third cause. ``console_offline`` has now been split three ways:
    onPC down, responder stopped, and the console replying to another port.
    """

    def test_a_listening_input_with_a_pong_elsewhere_reports_both_numbers(self, tmp_path):
        session, gate = _mismatch_session(
            tmp_path,
            console_input="listening",
            reply_port_probe=lambda: ReplyPortMismatch(configured=9000, observed=9005),
        )
        gate.monitor.note_ping_timeout()
        event = session.status_snapshot()
        assert event["health"] == "console_offline"
        assert event["console_input"] == "listening"
        assert event["reply_port"] == 9005
        assert event["receive_port"] == 9000

    def test_no_mismatch_leaves_the_status_frame_exactly_as_before(self, tmp_path):
        session, gate = _mismatch_session(
            tmp_path, console_input="listening", reply_port_probe=lambda: None
        )
        gate.monitor.note_ping_timeout()
        event = session.status_snapshot()
        assert event["reply_port"] is None
        assert event["receive_port"] is None

    def test_discovery_is_not_consulted_while_the_console_input_is_silent(self, tmp_path):
        # onPC itself is down — there is nothing to reply from, so a ping and ten
        # sockets would buy nothing.
        calls: list[int] = []
        session, gate = _mismatch_session(
            tmp_path,
            console_input="silent",
            reply_port_probe=lambda: calls.append(1) or None,
        )
        gate.monitor.note_ping_timeout()
        session.status_snapshot()
        assert calls == []

    def test_discovery_is_not_consulted_while_the_link_is_healthy(self, tmp_path):
        calls: list[int] = []
        session, _gate = _mismatch_session(
            tmp_path,
            console_input="listening",
            reply_port_probe=lambda: calls.append(1) or None,
        )
        event = session.status_snapshot()
        assert event["health"] == "online"
        assert calls == [], "a working configuration must never pay for discovery"

    def test_a_raising_discovery_never_breaks_the_status_surface(self, tmp_path):
        def _boom():
            raise RuntimeError("discovery exploded")

        session, gate = _mismatch_session(
            tmp_path, console_input="listening", reply_port_probe=_boom
        )
        gate.monitor.note_ping_timeout()
        event = session.status_snapshot()
        assert event["health"] == "console_offline"
        assert event["reply_port"] is None

    def test_the_websocket_status_frame_carries_the_mismatch(self, tmp_path):
        from fastapi.testclient import TestClient

        from server.safety.audit import AuditLog
        from server.safety.gate import SafetyGate
        from server.web.app import WebDeps, create_app
        from server.web.approval_bridge import ApprovalChannel

        from .test_runner_self_correction import ScriptedProvider
        from .test_safety_gate import FakeConsole

        audit = AuditLog(tmp_path / "audit")
        channel = ApprovalChannel(timeout_seconds=1.0)
        gate = SafetyGate(console=FakeConsole(), audit=audit, approval_port=channel)
        gate.monitor.note_ping_timeout()
        deps = WebDeps(
            gate=gate,
            provider=ScriptedProvider([]),
            system_prefix="PREFIX",
            audit=audit,
            approval_channel=channel,
            console_input_probe=lambda: "listening",
            reply_port_probe=lambda: ReplyPortMismatch(configured=9000, observed=9005),
        )
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            event = ws.receive_json()
        assert event["reply_port"] == 9005
        assert event["receive_port"] == 9000

    def test_build_runtime_composes_a_reply_port_diagnostic(self):
        # The assembly seam. Every part below passes in isolation while the
        # verdict reaches nobody unless serve.py actually wires it.
        from server.web import serve
        from server.web.reply_discovery import ReplyPortDiagnostic

        args = serve.parse_args(
            [
                "--receive-port",
                "0",
                "--no-session-backup",
                "--console-host",
                "127.0.0.1",
                "--console-port",
                "8000",
            ]
        )
        app, stack = serve.build_runtime(args)
        try:
            probe = app.state.deps.reply_port_probe
            assert probe is not None, "the composed app carries no reply-port diagnostic"
            assert isinstance(probe.__self__, ReplyPortDiagnostic)
            # And the completed run must be able to push a status frame, or the
            # diagnosis is computed and never shown (the heartbeat loop only
            # notifies on a health CHANGE).
            assert probe.__self__._on_complete is not None
        finally:
            stack.stop()

    def test_the_mismatch_changes_neither_the_health_state_nor_the_gate_decision(self, tmp_path):
        session, gate = _mismatch_session(
            tmp_path,
            console_input="listening",
            reply_port_probe=lambda: ReplyPortMismatch(configured=9000, observed=9005),
        )
        gate.monitor.note_ping_timeout()
        session.status_snapshot()
        assert gate.monitor.state == "console_offline"
        assert gate.monitor.executions_blocked is True
        assert gate.screen(["Store Group 3"]).status == "blocked_console_offline"
