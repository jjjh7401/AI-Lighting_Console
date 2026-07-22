"""Console OSC-input reachability probe (follow-up defect — REQ-DEPLOY-018).

Live-observed defect: the responder plugin stopped while onPC itself stayed up
and healthy, and the app told the operator to check the two things that were
already fine ("is onPC running? is OSC input on?") while never naming the one
thing that was actually wrong. ``HealthMonitor._classify_silence`` cannot tell
the two apart: it distinguishes ``console_offline`` from ``responder_degraded``
by OBSERVED INBOUND TRAFFIC, and when the responder is the only thing that ever
sends, a stopped responder produces zero traffic and falls through to
``console_offline``. The state machine is right; its inputs are insufficient.

The discriminator is a BIND attempt on the console's OSC input port
(EADDRINUSE => something is listening => onPC's OSC input is live), reusing the
established :func:`server.web.launcher.probe_port_available` UDP semantics.

Load-bearing boundaries pinned here:

* the DIAGNOSIS changes, the VERDICT does not — health state and gate decision
  are byte-identical whatever the probe reports;
* the probe BINDS ONLY, never sends (an unenumerated OSC send would violate the
  AC-DEPLOY-027 wire-level enumeration invariant and the AC-MVP-019 single gate);
* a non-loopback console host is ``undetermined`` — you cannot bind someone
  else's port — and ``undetermined`` stays distinguishable from "not listening"
  so the UI falls back to the current (correct-in-that-case) message.
"""

from __future__ import annotations

import socket
from pathlib import Path

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.monitor import HealthMonitor
from server.web.approval_bridge import ApprovalChannel
from server.web.console_probe import (
    make_console_input_probe,
    probe_console_input,
    probe_target,
)
from server.web.messages import (
    CONSOLE_INPUT_LISTENING,
    CONSOLE_INPUT_SILENT,
    CONSOLE_INPUT_UNDETERMINED,
    status_event,
)
from server.web.session import ChatSession

from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole


def _hold_udp_port() -> tuple[socket.socket, int]:
    """Hold a real loopback UDP port (the "onPC OSC input is live" shape)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    return sock, sock.getsockname()[1]


def _hold_wildcard_udp_port() -> tuple[socket.socket, int]:
    """Hold a UDP port the way onPC really holds its OSC input.

    Measured live (``lsof -nP -iUDP``): the console's entries are ``UDP *:8000``
    / ``UDP *:9000`` — bound to the WILDCARD address, not to loopback. Any test
    that only ever holds ``127.0.0.1`` proves nothing about the shape this probe
    actually meets.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 0))
    return sock, sock.getsockname()[1]


def _free_udp_port() -> int:
    sock, port = _hold_udp_port()
    sock.close()
    return port


def _session(tmp_path, *, console_input_probe=None):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    sent: list[dict] = []
    session = ChatSession(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        console_input_probe=console_input_probe,
    )
    return session, gate


def _go_offline(gate: SafetyGate) -> None:
    """Drive the monitor into console_offline (silence, no prior activity)."""
    gate.monitor.note_ping_timeout()
    assert gate.monitor.state == HealthMonitor.CONSOLE_OFFLINE


class TestProbeClassification:
    def test_a_held_loopback_input_port_reports_listening(self):
        holder, port = _hold_udp_port()
        try:
            assert probe_console_input("127.0.0.1", port) == CONSOLE_INPUT_LISTENING
        finally:
            holder.close()

    def test_a_free_loopback_input_port_reports_silent(self):
        assert probe_console_input("127.0.0.1", _free_udp_port()) == CONSOLE_INPUT_SILENT

    def test_localhost_is_probed_like_a_loopback_literal(self):
        holder, port = _hold_udp_port()
        try:
            assert probe_console_input("localhost", port) == CONSOLE_INPUT_LISTENING
        finally:
            holder.close()

    def test_a_non_loopback_console_host_is_undetermined_and_never_probed(self):
        calls: list[tuple] = []

        def _probe(host, port, *, sock_type):  # pragma: no cover - must not run
            calls.append((host, port, sock_type))
            return True

        assert probe_console_input("10.0.0.5", 8000, probe=_probe) == CONSOLE_INPUT_UNDETERMINED
        assert calls == [], "a remote console's port must never be bound"

    def test_probe_target_resolution(self):
        # Only an IPv4 loopback address is bindable by the AF_INET probe.
        assert probe_target("127.0.0.1") == "127.0.0.1"
        assert probe_target("127.0.0.9") == "127.0.0.9"
        assert probe_target("localhost") == "127.0.0.1"
        for unprobeable in ("::1", "10.0.0.5", "192.168.1.20", "ma3.local", "", "0.0.0.0"):
            assert probe_target(unprobeable) is None, unprobeable

    def test_an_ipv6_loopback_host_is_undetermined_not_listening(self):
        # The underlying probe is AF_INET-only and reports an address-family
        # bind failure as "occupied". Trusting it for an IPv6 host would report
        # a FREE port as "listening" — a confidently-wrong cause, which is the
        # entire failure class this module exists to remove.
        free = _free_udp_port()
        assert probe_console_input("::1", free) == CONSOLE_INPUT_UNDETERMINED

    def test_an_unresolvable_or_remote_hostname_never_reaches_the_socket(self):
        calls: list[tuple] = []

        def _probe(host, port, *, sock_type):  # pragma: no cover - must not run
            calls.append((host, port, sock_type))
            return True

        for host in ("ma3.local", "console.example.invalid", "", "0.0.0.0"):
            assert probe_console_input(host, 8000, probe=_probe) == CONSOLE_INPUT_UNDETERMINED, host
        assert calls == []

    def test_undetermined_is_distinguishable_from_not_listening(self):
        # Collapsing the two would reintroduce a confidently-wrong message for a
        # remote console — the exact failure this probe exists to remove.
        assert CONSOLE_INPUT_UNDETERMINED != CONSOLE_INPUT_SILENT
        assert CONSOLE_INPUT_UNDETERMINED != CONSOLE_INPUT_LISTENING

    def test_an_out_of_range_port_is_undetermined(self):
        assert probe_console_input("127.0.0.1", 0) == CONSOLE_INPUT_UNDETERMINED
        assert probe_console_input("127.0.0.1", 70000) == CONSOLE_INPUT_UNDETERMINED

    def test_a_probe_failure_degrades_to_undetermined(self):
        def _boom(host, port, **kwargs):
            raise OSError("no socket for you")

        assert probe_console_input("127.0.0.1", 8000, probe=_boom) == CONSOLE_INPUT_UNDETERMINED

    def test_a_wildcard_bound_console_input_reports_listening(self):
        # THE live shape. onPC binds *:8000, not 127.0.0.1:8000. Detection here
        # must use the STRICT bind (no SO_REUSEADDR): with the option set, a
        # specific-address bind succeeds right past a wildcard holder (measured
        # on darwin), and a live console input would be reported as silent —
        # a confidently-wrong cause, which is what this module exists to remove.
        # The preflight in launcher.py deliberately makes the OPPOSITE choice
        # (it models our own binder); the two must not be unified.
        holder, port = _hold_wildcard_udp_port()
        try:
            assert probe_console_input("127.0.0.1", port) == CONSOLE_INPUT_LISTENING
        finally:
            holder.close()

    def test_the_probe_asks_for_the_strict_bind_explicitly(self):
        # Boundary assertion, not a re-statement: the shared probe's DEFAULT is
        # the permissive preflight bind, so this module must opt out by name.
        seen: list[dict] = []

        def _probe(host, port, **kwargs):
            seen.append(kwargs)
            return True

        probe_console_input("127.0.0.1", 8000, probe=_probe)
        assert seen == [{"sock_type": socket.SOCK_DGRAM, "reuse_addr": False}]

    def test_the_factory_binds_the_configured_host_and_port(self):
        holder, port = _hold_udp_port()
        try:
            assert make_console_input_probe("127.0.0.1", port)() == CONSOLE_INPUT_LISTENING
        finally:
            holder.close()


class TestProbeNeverSends:
    """AC-DEPLOY-027 / AC-MVP-019: every OSC send is enumerated and gated."""

    def test_the_holder_receives_no_packet_from_the_probe(self):
        holder, port = _hold_udp_port()
        try:
            assert probe_console_input("127.0.0.1", port) == CONSOLE_INPUT_LISTENING
            holder.setblocking(False)
            try:
                payload = holder.recvfrom(4096)
            except BlockingIOError:
                payload = None
            assert payload is None, f"the probe transmitted {payload!r} — bind only"
        finally:
            holder.close()

    def test_the_probe_module_contains_no_transmit_call(self):
        source = (Path(__file__).resolve().parents[1] / "web" / "console_probe.py").read_text(
            encoding="utf-8"
        )
        for transmit in ("sendto", "send(", "sendall", "connect("):
            assert transmit not in source, f"console_probe.py calls {transmit!r}"
        # Positive control: the boundary above is not vacuous — the module really
        # does delegate to the launcher's measured bind-only UDP probe.
        assert "probe_port_available" in source

    def test_the_probe_module_stays_off_the_osc_send_surface(self):
        # server/web may never import server.bridge (test_architecture.py); this
        # is the same boundary asserted at the file that is most tempted to cross
        # it — a reachability probe that "just" reused the bridge socket would.
        source = (Path(__file__).resolve().parents[1] / "web" / "console_probe.py").read_text(
            encoding="utf-8"
        )
        assert "server.bridge" not in source
        assert "pythonosc" not in source


class TestStatusEventCarriesTheDiscriminator:
    def test_status_event_defaults_to_undetermined(self):
        event = status_event(health="console_offline", live_lock=False, executions_blocked=True)
        assert event["console_input"] == CONSOLE_INPUT_UNDETERMINED

    def test_console_offline_with_a_live_input_port_reports_listening(self, tmp_path):
        session, gate = _session(tmp_path, console_input_probe=lambda: CONSOLE_INPUT_LISTENING)
        _go_offline(gate)
        event = session.status_snapshot()
        assert event["health"] == "console_offline"
        assert event["console_input"] == CONSOLE_INPUT_LISTENING

    def test_console_offline_with_a_silent_input_port_reports_silent(self, tmp_path):
        session, gate = _session(tmp_path, console_input_probe=lambda: CONSOLE_INPUT_SILENT)
        _go_offline(gate)
        assert session.status_snapshot()["console_input"] == CONSOLE_INPUT_SILENT

    def test_console_offline_without_a_wired_probe_is_undetermined(self, tmp_path):
        session, gate = _session(tmp_path)
        _go_offline(gate)
        assert session.status_snapshot()["console_input"] == CONSOLE_INPUT_UNDETERMINED

    def test_a_raising_probe_never_breaks_the_status_surface(self, tmp_path):
        def _boom() -> str:
            raise RuntimeError("probe exploded")

        session, gate = _session(tmp_path, console_input_probe=_boom)
        _go_offline(gate)
        event = session.status_snapshot()
        assert event["health"] == "console_offline"
        assert event["console_input"] == CONSOLE_INPUT_UNDETERMINED

    def test_the_healthy_state_never_pays_for_a_socket_bind(self, tmp_path):
        calls: list[int] = []
        session, _gate = _session(tmp_path, console_input_probe=lambda: calls.append(1) or "x")
        event = session.status_snapshot()
        assert event["health"] == "online"
        assert event["console_input"] == CONSOLE_INPUT_UNDETERMINED
        assert calls == [], "the probe is a console_offline diagnosis, not a heartbeat"


class TestVerdictIsUnchanged:
    """Constraint: only the DIAGNOSIS improves — no health state, no gate rule."""

    def test_the_probe_result_changes_neither_the_state_nor_the_gate_decision(self, tmp_path):
        seen = []
        for verdict in (CONSOLE_INPUT_LISTENING, CONSOLE_INPUT_SILENT, CONSOLE_INPUT_UNDETERMINED):
            session, gate = _session(tmp_path / verdict, console_input_probe=lambda v=verdict: v)
            _go_offline(gate)
            event = session.status_snapshot()
            decision = gate.screen(["Store Group 3"])
            seen.append(
                (
                    gate.monitor.state,
                    gate.monitor.executions_blocked,
                    event["health"],
                    event["executions_blocked"],
                    decision.status,
                    decision.cleared,
                )
            )
        assert (
            seen
            == [
                (
                    HealthMonitor.CONSOLE_OFFLINE,
                    True,
                    "console_offline",
                    True,
                    "blocked_console_offline",
                    False,
                )
            ]
            * 3
        )

    def test_the_gate_keeps_its_two_distinct_blocking_semantics(self, tmp_path):
        # A "listening" verdict must NOT promote console_offline to
        # responder_degraded: the two map to DIFFERENT gate block statuses with
        # different safety meanings, and quietly changing which one applies
        # would change what the gate blocks. Only the wording moves.
        session, gate = _session(tmp_path, console_input_probe=lambda: CONSOLE_INPUT_LISTENING)
        _go_offline(gate)
        assert session.status_snapshot()["console_input"] == CONSOLE_INPUT_LISTENING
        assert gate.screen(["Store Group 3"]).status == "blocked_console_offline"

        gate.monitor.note_activity()
        gate.monitor.note_ping_timeout()
        assert gate.monitor.state == HealthMonitor.RESPONDER_DEGRADED
        assert gate.screen(["Store Group 3"]).status == "blocked_responder_degraded"

    def test_the_monitor_state_machine_gains_no_socket_dependency(self):
        source = (Path(__file__).resolve().parents[1] / "safety" / "monitor.py").read_text(
            encoding="utf-8"
        )
        for io_marker in ("socket", "bind", "console_probe"):
            assert io_marker not in source, (
                f"monitor.py acquired {io_marker!r} — it is a clock-driven state "
                "machine on the gate's hot path and must stay pure"
            )


class TestCompositionWiring:
    """The assembly points — a correct part wired nowhere is still the defect.

    Both seams below are the shape a full unit suite misses: every piece passes
    in isolation while the verdict never reaches the operator.
    """

    def test_the_websocket_status_frame_carries_the_verdict(self, tmp_path):
        from fastapi.testclient import TestClient

        from server.web.app import WebDeps, create_app

        console = FakeConsole()
        console.ping_ok = False
        audit = AuditLog(tmp_path / "audit")
        channel = ApprovalChannel(timeout_seconds=1.0)
        gate = SafetyGate(console=console, audit=audit, approval_port=channel)
        gate.monitor.note_ping_timeout()
        deps = WebDeps(
            gate=gate,
            provider=ScriptedProvider([]),
            system_prefix="PREFIX",
            audit=audit,
            approval_channel=channel,
            console_input_probe=lambda: CONSOLE_INPUT_LISTENING,
        )
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            event = ws.receive_json()
        assert event["type"] == "status"
        assert event["health"] == "console_offline"
        assert event["console_input"] == CONSOLE_INPUT_LISTENING

    def test_build_runtime_probes_the_CONFIGURED_console_endpoint_live(self):
        from server.web import serve

        holder, port = _hold_udp_port()
        try:
            args = serve.parse_args(
                [
                    "--receive-port",
                    "0",
                    "--no-session-backup",
                    "--console-host",
                    "127.0.0.1",
                    "--console-port",
                    str(port),
                ]
            )
            app, stack = serve.build_runtime(args)
            try:
                probe = app.state.deps.console_input_probe
                assert probe is not None, "the composed app carries no console probe"
                assert probe() == CONSOLE_INPUT_LISTENING
                holder.close()
                # Re-probed per call, never cached: a responder restarted mid-
                # session must flip the verdict without a server restart.
                assert probe() == CONSOLE_INPUT_SILENT
            finally:
                stack.stop()
        finally:
            holder.close()
