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

        # 갱신 근거 (t299 Phase 3): 아래 「안전한 번들」과 잠금 단계의 운반용
        # 리터럴이 `Store Cue <n>` 이었고, v7(SPEC-COPILOT-CLASSIFYGAP-001)이
        # `Store Cue` 를 폐집합에 넣어 안전하지 않게 됐다. 이 검사가 재는 축은
        # 감사 로그의 **완전성**(보낸 것 ↔ 기록된 것 1:1)이고, 안전/위험 경로를
        # 각각 한 번씩 지나가는 것이 그 축의 전제다.
        #
        # 이 자리는 특히 조용히 망가진다: 안전 번들이 위험해지면 `ScriptedApproval`
        # 의 첫 `True` 를 그 번들이 먹어버리고, 3단계의 「승인된 위험 번들」이
        # `False` 를 받는다. 실제로 이 회차에서 빨개진 줄은 3단계였다 — 원인은
        # 2단계다. 그래서 Phase 1·2 의 규율대로 프로그래머 값으로 옮긴다.
        safe_a, safe_b, safe_c = "Fixture 1 At 50", "Fixture 2 At 60", "Fixture 3 At 70"

        # 1. session start -> one backup send (rule 1)
        gate.start_session()
        # 2. safe bundle -> two command sends
        assert gate.screen([safe_a, safe_b]).cleared
        assert gate.execution_port.execute(safe_a).ok
        assert gate.execution_port.execute(safe_b).ok
        # 3. risky bundle approved -> pre-risky backup send + one command send
        assert gate.screen(["Delete Sequence 5"]).cleared
        assert gate.execution_port.execute("Delete Sequence 5").ok
        # 4. risky bundle rejected -> zero sends
        assert gate.screen(["Delete Sequence 6"]).cleared is False
        # 5. grammar block -> zero sends
        assert gate.screen(["'broken"]).status == "blocked_grammar"
        # 6. live lock -> proposal only, zero sends
        gate.lock.activate()
        # 여기도 **안전한** 줄이어야 축이 산다: 잠금이 분류보다 먼저 이긴다는 것을
        # 재는 자리인데, 위험한 줄을 쓰면 `locked` 가 어느 경로에서 왔는지 구분되지
        # 않는다(위험 경로도 `locked` 를 답한다). v7 이후 `Store Cue 3` 이 위험해졌으니
        # 안전한 줄로 되돌려 그 구분을 지킨다.
        assert gate.screen([safe_c]).status == "locked"
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
                safe_a: 1,
                safe_b: 1,
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
