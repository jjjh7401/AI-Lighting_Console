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
    """FakeConsole + the M7 deploy surface (+ M7.5 per-send records)."""

    def __init__(self, state_tree: dict | None = None):
        super().__init__(state_tree)
        self.deployed: list[tuple[str, str]] = []
        self.deploy_status = "ok"
        self.deploy_detail = "deployed"
        self.deploy_sends: tuple = ()

    def deploy_plugin(self, name: str, lua_source: str):
        from server.safety.console import ExecOutcome

        self.deployed.append((name, lua_source))
        return ExecOutcome(
            status=self.deploy_status, detail=self.deploy_detail, sends=self.deploy_sends
        )


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


# ---------------------------------------------------------------- M7.5 per-send granularity


class TestFileImportPerSendRecords:
    """M7.5 (AC-DEPLOY-027 Layer ②) — every console round-trip inside a
    file+Import deploy is returned as its own ``DeploySend`` record, so the
    gate can audit each wire send 1:1 instead of one blanket ``deploy`` event."""

    def _import_link(self, tmp_path):
        from .test_responder_import_gate import RecordingConsole

        link = ConsoleLink(
            timeouts=LinkTimeouts(exec_confirm_seconds=2.0, state_query_seconds=2.0),
            import_dir=tmp_path / "plugins",
        )
        console = RecordingConsole(link)
        link.bind_send(console.send)
        return link, console

    def test_fresh_deploy_returns_one_record_per_round_trip(self, tmp_path):
        link, _console = self._import_link(tmp_path)
        outcome = link.deploy_plugin("CopilotResponder", "return 1")
        assert outcome.status == "ok"
        assert [(s.kind, s.command, s.ok) for s in outcome.sends] == [
            ("state_query", "DataPool/Plugins", True),
            ("command", "Import Plugin 1 'CopilotResponder'", True),
            ("state_query", "DataPool/Plugins", True),
        ]

    def test_redeploy_records_the_delete_round_trip_too(self, tmp_path):
        link, _console = self._import_link(tmp_path)
        assert link.deploy_plugin("CopilotResponder", "return 1").status == "ok"
        outcome = link.deploy_plugin("CopilotResponder", "return 2")
        assert outcome.status == "ok"
        assert ("command", "Delete Plugin 1") in [(s.kind, s.command) for s in outcome.sends]
        assert len(outcome.sends) == 4  # pool read + Delete + Import + confirm read

    def test_timeout_path_still_records_the_sends_that_hit_the_wire(self, tmp_path):
        # No replies at all: the pool read times out and the Import exec times
        # out — but both SENT a datagram, so both MUST be recorded (a lost
        # reply is not a lost send; AC-DEPLOY-027 reconciles the wire).
        link = ConsoleLink(timeouts=_FAST, import_dir=tmp_path / "plugins")
        sent: list[str] = []
        link.bind_send(sent.append)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "unconfirmed"
        assert len(sent) == 2  # state query + Import Plugin exec
        assert [(s.kind, s.ok) for s in outcome.sends] == [
            ("state_query", False),
            ("command", False),
        ]

    def test_osc_verb_fallback_has_no_sub_sends(self):
        # The remote deploy verb is ONE wire send, already represented 1:1 by
        # the gate's parent kind="deploy" audit entry — no sub-records.
        link = ConsoleLink(timeouts=_FAST)  # no import_dir -> OSC deploy verb
        send, _ = _deploy_echo_send(link)
        link.bind_send(send)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "ok"
        assert outcome.sends == ()


class TestFileImportSlotHonesty:
    """The free-slot arithmetic depends on ``i`` being a REAL pool slot.

    The responder omits ``i`` when it could not establish a child's slot
    (PROTOCOL.md §4.2). Guessing anyway would mean ``Import Plugin <slot>``
    into an occupied slot — the pool read exists precisely to prevent that.
    """

    def _link_with_pool(self, tmp_path, children: list[dict]):
        link = ConsoleLink(timeouts=_FAST, import_dir=tmp_path / "plugins")
        sent: list[str] = []

        def send(wire: str) -> None:
            sent.append(wire)
            match = re.match(r'^Plugin "CopilotResponder" "(state|exec) (\S+)(?: (.*))?"$', wire)
            assert match, wire
            kind, rid, rest = match.groups()
            if kind == "state":
                payload = {
                    "v": 1,
                    "kind": "state",
                    "id": rid,
                    "ok": True,
                    "path": rest,
                    "children": children,
                }
                address = "/copilot/state"
            else:
                payload = {"v": 1, "kind": "result", "id": rid, "ok": True, "result": "OK"}
                address = FEEDBACK_ADDRESS
            link.deliver(FeedbackMessage(address=address, args=(encode_payload(payload),)))

        link.bind_send(send)
        return link, sent

    def test_unnumbered_pool_entry_stops_the_import(self, tmp_path):
        link, sent = self._link_with_pool(
            tmp_path, [{"i": 1, "name": "Other"}, {"name": "SlotUnknown"}]
        )
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "failed"
        assert "free plugin slot" in outcome.detail
        assert "1 plugin(s)" in outcome.detail
        # Nothing was imported or deleted: only the pool read hit the wire.
        assert len(sent) == 1
        assert [s.kind for s in outcome.sends] == ["state_query"]

    def test_fully_numbered_gapped_pool_picks_a_genuinely_free_slot(self, tmp_path):
        # Gapped pool (1, 5, 7): slot 2 is free and must be chosen. Under the
        # old positional `i` the same pool reported 1, 2, 3 — so slot 4 looked
        # free while the real slot 2 sat unused and slot 5 stayed hidden.
        link, _sent = self._link_with_pool(
            tmp_path,
            [{"i": 1, "name": "A"}, {"i": 5, "name": "B"}, {"i": 7, "name": "C"}],
        )
        outcome = link.deploy_plugin("Cleaner", "return 1")
        imports = [s.command for s in outcome.sends if s.kind == "command"]
        assert imports == ["Import Plugin 2 'Cleaner'"]


class TestGatePerSendDeployAudit:
    """M7.5 — the gate fans deploy sub-sends out into individual ``executed``
    audit entries correlated to the parent deploy (``deploy_of``)."""

    def test_sub_sends_get_their_own_audit_entries_with_correlation(self, tmp_path):
        from server.safety.console import DeploySend

        console = DeployableFakeConsole()
        console.deploy_sends = (
            DeploySend(kind="state_query", command="DataPool/Plugins", ok=True, outcome="ok"),
            DeploySend(
                kind="command", command="Import Plugin 1 'Cleaner'", ok=True, outcome="ok"
            ),
        )
        gate, _, audit = _gate(tmp_path, console=console)
        assert gate.deploy_plugin_source("Cleaner", "return 1").ok is True

        executed = _events(audit, "executed")
        subs = [e for e in executed if e.get("deploy_of") == "Cleaner"]
        assert [(e["kind"], e["command"], e["ok"]) for e in subs] == [
            ("state_query", "DataPool/Plugins", True),
            ("command", "Import Plugin 1 'Cleaner'", True),
        ]
        # The parent deploy entry survives (approval/summary record) and counts
        # its sub-sends; sub-entries precede it in the durable log.
        (parent,) = [e for e in executed if e["kind"] == "deploy"]
        assert parent["command"] == "Cleaner"
        assert parent["deploy_sends"] == 2
        assert executed.index(parent) > max(executed.index(e) for e in subs)

    def test_deploy_without_sub_sends_stays_single_entry(self, tmp_path):
        # OSC-verb fallback / fakes: no sends -> exactly the old single entry.
        gate, _, audit = _gate(tmp_path)
        assert gate.deploy_plugin_source("Cleaner", "return 1").ok is True
        executed = _events(audit, "executed")
        assert len(executed) == 1
        assert executed[0]["kind"] == "deploy"
        assert executed[0]["deploy_sends"] == 0
