"""Audit-completeness E2E (M4 — AC-MVP-019 ② + AC-MVP-006).

Fake-console E2E pattern: a REAL OscBridge sends over UDP loopback to a fake
console server that records every wire receipt and answers the M2 protocol.
Two reconciliations, zero misses each:

- AC-MVP-019 ②: every console send has a 1:1 gate-passage audit record
  (exec-wrapped commands ↔ ``executed`` kind command/backup; heartbeat pings ↔
  kind heartbeat; state queries ↔ kind state_query).
- AC-MVP-006: all four gate event types (executed / approved / rejected /
  blocked) reconcile against the scenario's expected events with zero misses.
"""

from __future__ import annotations

import re
import threading
from collections import Counter

import pytest
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from server.bridge.osc import CMD_ADDRESS, FEEDBACK_ADDRESS, STATE_ADDRESS, BridgeConfig, OscBridge
from server.bridge.protocol import encode_payload
from server.safety.audit import AuditLog
from server.safety.console import ConsoleLink, LinkTimeouts
from server.safety.gate import BACKUP_COMMAND, SafetyGate

from .test_safety_gate import ScriptedApproval

_REQUEST = re.compile(r'^Plugin "CopilotResponder" "(ping|state|exec) (\S+)(?: (.*))?"$')


class FakeConsoleServer:
    """Answers the M2 wire protocol and records every /copilot/cmd receipt."""

    def __init__(self):
        dispatcher = Dispatcher()
        dispatcher.map(CMD_ADDRESS, self._on_cmd)
        self._server = ThreadingOSCUDPServer(("127.0.0.1", 0), dispatcher)
        self._thread: threading.Thread | None = None
        self.reply_port: int | None = None
        self.exec_commands: list[str] = []
        self.state_paths: list[str] = []
        self.ping_count = 0
        self.raw_unwrapped: list[str] = []

    @property
    def port(self) -> int:
        return self._server.socket.getsockname()[1]

    def start(self):
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=5.0)

    def _on_cmd(self, address, *args):
        line = args[0]
        match = _REQUEST.match(line)
        if not match:
            self.raw_unwrapped.append(line)
            return
        kind, rid, rest = match.groups()
        client = SimpleUDPClient("127.0.0.1", self.reply_port)
        if kind == "ping":
            self.ping_count += 1
            client.send_message(
                FEEDBACK_ADDRESS, encode_payload({"v": 1, "kind": "pong", "id": rid, "ok": True})
            )
        elif kind == "exec":
            self.exec_commands.append(rest)
            client.send_message(
                FEEDBACK_ADDRESS,
                encode_payload({"v": 1, "kind": "result", "id": rid, "ok": True, "result": "OK"}),
            )
        else:
            self.state_paths.append(rest)
            client.send_message(
                STATE_ADDRESS,
                encode_payload(
                    {
                        "v": 1,
                        "kind": "state",
                        "id": rid,
                        "ok": True,
                        "path": rest,
                        "children": [{"name": "Vocals"}],
                    }
                ),
            )


@pytest.fixture()
def loopback(tmp_path):
    console_server = FakeConsoleServer()
    console_server.start()
    link = ConsoleLink(
        timeouts=LinkTimeouts(exec_confirm_seconds=2.0, ping_seconds=2.0, state_query_seconds=2.0)
    )
    bridge = OscBridge(BridgeConfig(send_port=console_server.port, receive_port=0), consumer=link)
    bridge.start()
    console_server.reply_port = bridge.receive_port
    link.bind_send(bridge.send_command)
    try:
        yield console_server, link
    finally:
        bridge.stop()
        console_server.stop()


class TestAuditCompletenessE2E:
    def test_every_send_reconciles_with_a_gate_passage_record(self, tmp_path, loopback):
        console_server, link = loopback
        audit = AuditLog(tmp_path / "audit")
        approval = ScriptedApproval(decisions=[True, False])
        gate = SafetyGate(console=link, audit=audit, approval_port=approval)
        gate.use_showfile_backup()

        # 1. session start -> one backup send (rule 1)
        gate.start_session()
        # 2. safe bundle -> two command sends
        assert gate.screen(["Store Cue 1", "Store Cue 2"]).cleared
        assert gate.execution_port.execute("Store Cue 1").ok
        assert gate.execution_port.execute("Store Cue 2").ok
        # 3. risky bundle approved -> pre-risky backup send + one command send
        assert gate.screen(["Delete Sequence 5"]).cleared
        assert gate.execution_port.execute("Delete Sequence 5").ok
        # 4. risky bundle rejected -> zero sends
        assert gate.screen(["Delete Sequence 6"]).cleared is False
        # 5. grammar block -> zero sends
        assert gate.screen(["'broken"]).status == "blocked_grammar"
        # 6. live lock -> proposal only, zero sends
        gate.lock.activate()
        assert gate.screen(["Store Cue 3"]).status == "locked"
        gate.lock.deactivate()
        # 7. heartbeat + 8. state query
        assert gate.heartbeat() == "online"
        payload = gate.state_port.query_state("DataPool/Groups")
        assert payload["ok"] is True

        events = list(audit.iter_events())

        # -- AC-MVP-019 ②: sends ↔ executed records, 1:1, zero misses --------
        executed = [e for e in events if e["event"] == "executed"]
        sent_commands = Counter(console_server.exec_commands)
        audited_commands = Counter(
            e["command"] for e in executed if e["kind"] in ("command", "backup")
        )
        assert sent_commands == audited_commands
        assert sent_commands == Counter(
            {
                BACKUP_COMMAND: 2,  # session start + pre-risky
                "Store Cue 1": 1,
                "Store Cue 2": 1,
                "Delete Sequence 5": 1,
            }
        )
        assert console_server.ping_count == sum(1 for e in executed if e["kind"] == "heartbeat")
        assert Counter(console_server.state_paths) == Counter(
            e["command"] for e in executed if e["kind"] == "state_query"
        )
        assert console_server.raw_unwrapped == []  # nothing bypassed the exec wrap

        # -- AC-MVP-006: four event types, expected counts, zero misses ------
        by_type = Counter(e["event"] for e in events)
        assert by_type["approved"] == 1  # Delete Sequence 5 bundle
        assert by_type["rejected"] == 1  # Delete Sequence 6 bundle
        blocked = [e for e in events if e["event"] == "blocked"]
        assert len(blocked) == 2  # one grammar block + one live-lock block
        reasons = " | ".join(e["reason"] for e in blocked)
        assert "quote" in reasons or "grammar" in reasons
        assert "lock" in reasons

    def test_unapproved_risky_command_never_reaches_the_wire(self, tmp_path, loopback):
        console_server, link = loopback
        audit = AuditLog(tmp_path / "audit")
        gate = SafetyGate(console=link, audit=audit)  # deny-all approval default
        decision = gate.screen(["Delete Sequence 5"])
        assert decision.cleared is False
        gate.execution_port.execute("Delete Sequence 5")
        assert console_server.exec_commands == []
        assert console_server.raw_unwrapped == []
