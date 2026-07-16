"""Deploy transport tests (M7 — wire builder + ConsoleLink + gate deploy surface).

The deployment send is console-bound traffic: it MUST ride the gate
(REQ-MVP-029) and be audited 1:1 like every other send. The wire form is a
new responder verb (``deploy <id> <enc-name> <enc-source>`` — PROTOCOL.md §2,
percent-encoded so the payload survives MA3 plugin-argument quoting), an
onPC-unverified protocol extension recorded as ASSUMPTION-6.
"""

from __future__ import annotations

import re
import urllib.parse

import pytest

from server.bridge.osc import FEEDBACK_ADDRESS, FeedbackMessage
from server.bridge.protocol import ProtocolError, build_deploy_request, encode_payload
from server.safety.audit import AuditLog
from server.safety.console import ConsoleLink, LinkTimeouts
from server.safety.gate import SafetyGate
from server.safety.monitor import HealthMonitor

from .test_safety_gate import FakeConsole

_FAST = LinkTimeouts(
    exec_confirm_seconds=0.05,
    ping_seconds=0.05,
    state_query_seconds=0.05,
    deploy_confirm_seconds=0.05,
)

_DEPLOY_WIRE = re.compile(r'^Plugin "CopilotResponder" "deploy (\S+) (\S+) (\S+)"$')


class TestBuildDeployRequest:
    def test_wire_shape_and_percent_encoding(self):
        wire = build_deploy_request("d-1", "My Cleaner", 'Cmd("Delete 1")\n')
        match = _DEPLOY_WIRE.match(wire)
        assert match, wire
        rid, enc_name, enc_source = match.groups()
        assert rid == "d-1"
        assert urllib.parse.unquote(enc_name) == "My Cleaner"
        assert urllib.parse.unquote(enc_source) == 'Cmd("Delete 1")\n'

    def test_encoded_payload_is_quote_and_space_free(self):
        wire = build_deploy_request("d-2", 'na"me', 'x = "샤막"\n')
        inner = wire[len('Plugin "CopilotResponder" "') : -1]
        # The MA3 plugin argument tolerates no embedded double quote; the
        # encoded tokens must therefore be pure [A-Za-z0-9-._~%] + separators.
        assert '"' not in inner
        assert re.fullmatch(r"deploy [A-Za-z0-9._-]+ \S+ \S+", inner), inner

    def test_invalid_request_id_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_deploy_request("bad id", "Cleaner", "return 1")

    def test_empty_name_or_source_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_deploy_request("d-3", "", "return 1")
        with pytest.raises(ProtocolError):
            build_deploy_request("d-3", "Cleaner", "")


def _deploy_echo_send(link: ConsoleLink, *, ok: bool = True, silent: bool = False):
    sent: list[str] = []

    def send(wire: str) -> None:
        sent.append(wire)
        if silent:
            return
        match = _DEPLOY_WIRE.match(wire)
        assert match, f"unexpected wire line: {wire!r}"
        rid, enc_name, _ = match.groups()
        payload = {
            "v": 1,
            "kind": "deploy",
            "id": rid,
            "ok": ok,
            "name": urllib.parse.unquote(enc_name),
        }
        if not ok:
            payload["error"] = "plugin pool unavailable"
        link.deliver(FeedbackMessage(address=FEEDBACK_ADDRESS, args=(encode_payload(payload),)))

    return send, sent


class TestConsoleLinkDeploy:
    def test_confirmed_deploy(self):
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _deploy_echo_send(link)
        link.bind_send(send)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "ok"
        assert len(sent) == 1

    def test_console_error_is_reported(self):
        link = ConsoleLink(timeouts=_FAST)
        send, _ = _deploy_echo_send(link, ok=False)
        link.bind_send(send)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "failed"
        assert "plugin pool unavailable" in outcome.detail

    def test_timeout_is_unconfirmed_never_resent(self):
        # REQ-MVP-032 discipline: send loss and reply loss are
        # indistinguishable; the link reports unconfirmed and sends ONCE.
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _deploy_echo_send(link, silent=True)
        link.bind_send(send)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "unconfirmed"
        assert len(sent) == 1


class DeployableFakeConsole(FakeConsole):
    """FakeConsole + the M7 deploy surface."""

    def __init__(self, state_tree: dict | None = None):
        super().__init__(state_tree)
        self.deployed: list[tuple[str, str]] = []
        self.deploy_status = "ok"
        self.deploy_detail = "deployed"

    def deploy_plugin(self, name: str, lua_source: str):
        from server.safety.console import ExecOutcome

        self.deployed.append((name, lua_source))
        return ExecOutcome(status=self.deploy_status, detail=self.deploy_detail)


def _gate(tmp_path, **kwargs):
    console = kwargs.pop("console", None) or DeployableFakeConsole()
    audit = AuditLog(tmp_path / "audit")
    gate = SafetyGate(console=console, audit=audit, **kwargs)
    return gate, console, audit


def _events(audit, event_type):
    return [e for e in audit.iter_events() if e["event"] == event_type]


class TestGateDeploySurface:
    def test_deploy_send_is_audited_one_to_one(self, tmp_path):
        gate, console, audit = _gate(tmp_path)
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is True
        assert console.deployed == [("Cleaner", "return 1")]
        (event,) = [e for e in _events(audit, "executed") if e["kind"] == "deploy"]
        assert event["command"] == "Cleaner"
        assert event["ok"] is True

    def test_live_lock_blocks_the_deploy(self, tmp_path):
        # REQ-MVP-016: under the live lock NOTHING reaches the console.
        gate, console, audit = _gate(tmp_path)
        gate.lock.activate()
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is False
        assert result.detail.startswith("blocked:")
        assert console.deployed == []
        assert _events(audit, "blocked") != []

    def test_console_offline_blocks_the_deploy(self, tmp_path):
        gate, console, _ = _gate(tmp_path, monitor=HealthMonitor())
        gate.monitor.note_ping_timeout()  # no prior activity -> console_offline
        assert gate.monitor.executions_blocked
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is False
        assert result.detail.startswith("blocked:")
        assert console.deployed == []

    def test_unconfirmed_deploy_carries_the_marker(self, tmp_path):
        # Same honest-marker contract the chat surface pins (REQ-MVP-032).
        console = DeployableFakeConsole()
        console.deploy_status = "unconfirmed"
        console.deploy_detail = "no confirmation"
        gate, _, audit = _gate(tmp_path, console=console)
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is False
        assert "execution unconfirmed" in result.detail
        (event,) = [e for e in _events(audit, "executed") if e["kind"] == "deploy"]
        assert event["ok"] is False

    def test_console_failure_detail_is_returned(self, tmp_path):
        console = DeployableFakeConsole()
        console.deploy_status = "failed"
        console.deploy_detail = "no plugin pool"
        gate, _, _ = _gate(tmp_path, console=console)
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is False
        assert "no plugin pool" in result.detail
