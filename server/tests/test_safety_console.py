"""ConsoleLink tests (M4 — gate-owned console I/O with result confirmation).

The link wraps the M2 wire protocol (exec/state/ping requests over
``/copilot/cmd``, replies correlated by request id) and is the ONLY production
caller of the OSC send surface. Unit tests use a stub send function that
synthesizes replies synchronously through :meth:`ConsoleLink.deliver` — no
sockets, deterministic timeouts.
"""

from __future__ import annotations

import inspect
import json
import re

import pytest

from server.bridge.osc import FEEDBACK_ADDRESS, STATE_ADDRESS, FeedbackMessage
from server.bridge.protocol import encode_payload
from server.orchestrator.ports import BulkPropertyQueryPort, FieldEnumerationPort
from server.safety.audit import AuditLog
from server.safety.console import (
    ConsoleLink,
    ExecOutcome,
    LinkTimeouts,
    StateBodyFetcher,
    StateQueryError,
)
from server.safety.expand import BodyUnavailable
from server.safety.gate import SafetyGate
from server.safety.monitor import HealthMonitor

_REQUEST = re.compile(r'^Plugin "CopilotResponder" "(ping|state|exec) (\S+)(?: (.*))?"$')
_INTROSPECT_REQUEST = re.compile(r'^Plugin "CopilotResponder" "introspect (\S+) (.+)"$')
_PROPS_REQUEST = re.compile(r'^Plugin "CopilotResponder" "props (\S+) ([^ ]+) (.+)"$')

_FAST = LinkTimeouts(exec_confirm_seconds=0.05, ping_seconds=0.05, state_query_seconds=0.05)
_PROBE_PATH = "DataPool/Sequences/Sequence 101"
_PROBE_NAMES = ("CURRENTCUE", "FADER")


def _reply(link: ConsoleLink, payload: dict, address: str = FEEDBACK_ADDRESS) -> None:
    link.deliver(FeedbackMessage(address=address, args=(encode_payload(payload),)))


def _echo_send(link: ConsoleLink, *, ok: bool = True, silent: bool = False):
    """A stub console: answers every request synchronously (or stays silent)."""

    sent: list[str] = []

    def send(wire: str) -> None:
        sent.append(wire)
        if silent:
            return
        match = _REQUEST.match(wire)
        assert match, f"unexpected wire line: {wire!r}"
        kind, rid, rest = match.groups()
        if kind == "ping":
            _reply(link, {"v": 1, "kind": "pong", "id": rid, "ok": True})
        elif kind == "exec":
            payload = {"v": 1, "kind": "result", "id": rid, "ok": ok}
            payload["result" if ok else "error"] = "OK" if ok else "Illegal command"
            _reply(link, payload)
        else:
            _reply(
                link,
                {"v": 1, "kind": "state", "id": rid, "ok": True, "path": rest, "children": []},
                address=STATE_ADDRESS,
            )

    return send, sent


def _probe_send(link: ConsoleLink, *, ok: bool = True, silent: bool = False):
    sent: list[str] = []

    def send(wire: str) -> None:
        sent.append(wire)
        if silent:
            return
        introspect_match = _INTROSPECT_REQUEST.match(wire)
        props_match = _PROPS_REQUEST.match(wire)
        assert introspect_match or props_match, f"unexpected wire line: {wire!r}"
        if introspect_match:
            rid, path = introspect_match.groups()
            payload = {
                "v": 1,
                "kind": "introspect",
                "id": rid,
                "ok": ok,
                "path": path,
            }
            if ok:
                payload.update(
                    {
                        "class": "Sequence",
                        "source": "property_accessors",
                        "fields": [
                            {"n": "CURRENTCUE", "t": "string"},
                            {"n": "FADER", "t": "string"},
                        ],
                        "total": 2,
                        "truncated": False,
                    }
                )
            else:
                payload["error"] = "introspect unavailable"
        else:
            rid, names, path = props_match.groups()
            payload = {
                "v": 1,
                "kind": "props",
                "id": rid,
                "ok": ok,
                "path": path,
                "reads": [],
            }
            if ok:
                payload["reads"] = [
                    {"n": "CURRENTCUE", "ok": True, "t": "string", "v": "Sequence 80.3"},
                    {"n": "FADER", "ok": True, "t": "string", "v": "Master"},
                ]
                payload["truncated"] = False
            else:
                payload["error"] = f"props unavailable: {names}"
        link.deliver(FeedbackMessage(address=STATE_ADDRESS, args=(encode_payload(payload),)))

    return send, sent


def _run_probe(link: ConsoleLink, operation: str) -> dict:
    if operation == "introspect":
        return link.enumerate_fields(_PROBE_PATH)
    return link.query_properties(_PROBE_PATH, _PROBE_NAMES)


class _ProbeConsole:
    def __init__(self) -> None:
        self.field_calls: list[str] = []
        self.props_calls: list[tuple[str, tuple[str, ...]]] = []
        self.field_errors: set[str] = set()
        self.props_errors: set[tuple[str, tuple[str, ...]]] = set()

    def execute(self, command: str) -> ExecOutcome:
        return ExecOutcome(status="ok", detail=command)

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict:
        return {"ok": True, "path": path, "children": []}

    def query_property(self, path: str, property_name: str) -> dict:
        return {"ok": True, "path": path, "property": property_name, "value": "unused"}

    def enumerate_fields(self, path: str) -> dict:
        self.field_calls.append(path)
        if path in self.field_errors:
            raise StateQueryError(f"introspect failed: {path}")
        return {
            "ok": True,
            "kind": "introspect",
            "path": path,
            "class": "Sequence",
            "fields": [{"n": "CURRENTCUE", "t": "string"}],
            "total": 1,
            "truncated": False,
        }

    def query_properties(self, path: str, property_names) -> dict:
        names = tuple(property_names)
        self.props_calls.append((path, names))
        if (path, names) in self.props_errors:
            raise StateQueryError(f"props failed: {path} {names}")
        return {
            "ok": True,
            "kind": "props",
            "path": path,
            "reads": [
                {"n": "CURRENTCUE", "ok": True, "t": "string", "v": "Sequence 80.3"},
                {"n": "FADER", "ok": True, "t": "string", "v": "Master"},
            ],
            "truncated": False,
        }

    def deploy_plugin(self, name: str, lua_source: str) -> ExecOutcome:
        return ExecOutcome(status="ok", detail=name)


def _make_probe_gate(tmp_path, console: _ProbeConsole | None = None):
    console = console or _ProbeConsole()
    audit = AuditLog(tmp_path / "audit")
    return SafetyGate(console=console, audit=audit), console, audit


def _executed(audit: AuditLog, kind: str) -> list[dict]:
    return [
        event
        for event in audit.iter_events()
        if event["event"] == "executed" and event["kind"] == kind
    ]


class TestExecute:
    def test_confirmed_success(self):
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _echo_send(link)
        link.bind_send(send)
        outcome = link.execute("Store Cue 5")
        assert outcome.status == "ok"
        assert outcome.detail == "OK"
        assert len(sent) == 1
        assert "exec" in sent[0] and "Store Cue 5" in sent[0]

    def test_confirmed_failure_carries_the_console_error(self):
        link = ConsoleLink(timeouts=_FAST)
        send, _ = _echo_send(link, ok=False)
        link.bind_send(send)
        outcome = link.execute("Bad Command")
        assert outcome.status == "failed"
        assert "Illegal command" in outcome.detail

    def test_no_reply_is_unconfirmed_not_failed(self):
        # REQ-MVP-032: send loss and feedback loss are indistinguishable.
        link = ConsoleLink(timeouts=_FAST)
        send, _ = _echo_send(link, silent=True)
        link.bind_send(send)
        outcome = link.execute("Store Cue 5")
        assert outcome.status == "unconfirmed"

    def test_unwrappable_command_fails_without_sending(self):
        # A double quote cannot ride the plugin-wrapped exec request.
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _echo_send(link)
        link.bind_send(send)
        outcome = link.execute('Store Cue 5 "name"')
        assert outcome.status == "failed"
        assert sent == []

    def test_unbound_send_raises(self):
        link = ConsoleLink(timeouts=_FAST)
        with pytest.raises(RuntimeError, match="send"):
            link.execute("List")


class TestPingAndState:
    def test_ping_success_updates_monitor(self):
        monitor = HealthMonitor()
        link = ConsoleLink(timeouts=_FAST, monitor=monitor)
        send, _ = _echo_send(link)
        link.bind_send(send)
        assert link.ping() is True
        assert monitor.state == HealthMonitor.ONLINE

    def test_ping_timeout_updates_monitor(self):
        monitor = HealthMonitor()
        link = ConsoleLink(timeouts=_FAST, monitor=monitor)
        send, _ = _echo_send(link, silent=True)
        link.bind_send(send)
        assert link.ping() is False
        assert monitor.state == HealthMonitor.CONSOLE_OFFLINE

    def test_query_state_returns_the_decoded_payload(self):
        link = ConsoleLink(timeouts=_FAST)
        send, _ = _echo_send(link)
        link.bind_send(send)
        payload = link.query_state("DataPool/Sequences")
        assert payload["ok"] is True
        assert payload["path"] == "DataPool/Sequences"

    def test_query_state_timeout_raises_and_notes_monitor(self):
        monitor = HealthMonitor()
        link = ConsoleLink(timeouts=_FAST, monitor=monitor)
        send, _ = _echo_send(link, silent=True)
        link.bind_send(send)
        with pytest.raises(StateQueryError):
            link.query_state("DataPool/Sequences")
        assert monitor.state == HealthMonitor.CONSOLE_OFFLINE

    def test_delivery_notes_activity_on_the_monitor(self):
        monitor = HealthMonitor()
        link = ConsoleLink(timeouts=_FAST, monitor=monitor)
        _reply(link, {"v": 1, "kind": "result", "id": "unknown", "ok": True})
        monitor.note_ping_timeout()
        # traffic was seen -> degraded, not offline
        assert monitor.state == HealthMonitor.RESPONDER_DEGRADED

    def test_foreign_feedback_is_ignored(self):
        link = ConsoleLink(timeouts=_FAST)
        link.deliver(FeedbackMessage(address=FEEDBACK_ADDRESS, args=("not-a-payload",)))
        link.deliver(FeedbackMessage(address=FEEDBACK_ADDRESS, args=(42,)))
        link.deliver(FeedbackMessage(address=FEEDBACK_ADDRESS, args=()))


class TestIntrospectAndPropsLink:
    def test_round_trips_arrive_on_the_existing_state_address(self):
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _probe_send(link)
        link.bind_send(send)
        fields = link.enumerate_fields(_PROBE_PATH)
        props = link.query_properties(_PROBE_PATH, _PROBE_NAMES)
        assert fields["fields"] == [
            {"n": "CURRENTCUE", "t": "string"},
            {"n": "FADER", "t": "string"},
        ]
        assert props["reads"][0]["v"] == "Sequence 80.3"
        assert _INTROSPECT_REQUEST.match(sent[0]).groups()[1] == _PROBE_PATH
        assert _PROPS_REQUEST.match(sent[1]).groups()[1:] == ("CURRENTCUE,FADER", _PROBE_PATH)

    @pytest.mark.parametrize("operation", ("introspect", "props"))
    def test_timeout_raises_state_query_error_and_notes_monitor(self, operation):
        monitor = HealthMonitor()
        link = ConsoleLink(timeouts=_FAST, monitor=monitor)
        send, _ = _probe_send(link, silent=True)
        link.bind_send(send)
        with pytest.raises(StateQueryError):
            _run_probe(link, operation)
        assert monitor.state == HealthMonitor.CONSOLE_OFFLINE

    @pytest.mark.parametrize("operation", ("introspect", "props"))
    def test_ok_false_reply_raises_state_query_error(self, operation):
        link = ConsoleLink(timeouts=_FAST)
        send, _ = _probe_send(link, ok=False)
        link.bind_send(send)
        with pytest.raises(StateQueryError, match="unavailable"):
            _run_probe(link, operation)


class TestIntrospectAndPropsGate:
    def test_state_port_exposes_the_declared_introspection_ports(self, tmp_path):
        gate, _, _ = _make_probe_gate(tmp_path)
        assert hasattr(gate.state_port, "enumerate_fields")
        assert hasattr(gate.state_port, "query_properties")
        assert list(inspect.signature(gate.state_port.enumerate_fields).parameters) == ["path"]
        assert list(inspect.signature(gate.state_port.query_properties).parameters) == [
            "path",
            "property_names",
        ]
        assert list(inspect.signature(FieldEnumerationPort.enumerate_fields).parameters) == [
            "self",
            "path",
        ]
        assert list(inspect.signature(BulkPropertyQueryPort.query_properties).parameters) == [
            "self",
            "path",
            "property_names",
        ]

    def test_successful_field_enumeration_is_audited_once(self, tmp_path):
        gate, _, audit = _make_probe_gate(tmp_path)
        payload = gate.state_port.enumerate_fields(_PROBE_PATH)
        assert payload["fields"] == [{"n": "CURRENTCUE", "t": "string"}]
        events = _executed(audit, "introspect_query")
        assert len(events) == 1
        assert events[0]["ok"] is True
        assert events[0]["command"] == _PROBE_PATH

    def test_failed_field_enumeration_is_audited_once_and_reraised(self, tmp_path):
        console = _ProbeConsole()
        console.field_errors.add(_PROBE_PATH)
        gate, _, audit = _make_probe_gate(tmp_path, console)
        with pytest.raises(StateQueryError, match="introspect failed"):
            gate.state_port.enumerate_fields(_PROBE_PATH)
        events = _executed(audit, "introspect_query")
        assert len(events) == 1
        assert events[0]["ok"] is False
        assert events[0]["command"] == _PROBE_PATH

    def test_successful_bulk_property_query_audits_names_without_values(self, tmp_path):
        gate, _, audit = _make_probe_gate(tmp_path)
        payload = gate.state_port.query_properties(_PROBE_PATH, _PROBE_NAMES)
        assert payload["reads"][0]["v"] == "Sequence 80.3"
        events = _executed(audit, "props_query")
        assert len(events) == 1
        assert events[0]["ok"] is True
        assert events[0]["command"] == f"{_PROBE_PATH} CURRENTCUE,FADER"
        serialized = "\n".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True) for event in audit.iter_events()
        )
        assert "Sequence 80.3" not in serialized

    def test_failed_bulk_property_query_is_audited_once_and_reraised(self, tmp_path):
        console = _ProbeConsole()
        console.props_errors.add((_PROBE_PATH, _PROBE_NAMES))
        gate, _, audit = _make_probe_gate(tmp_path, console)
        with pytest.raises(StateQueryError, match="props failed"):
            gate.state_port.query_properties(_PROBE_PATH, _PROBE_NAMES)
        events = _executed(audit, "props_query")
        assert len(events) == 1
        assert events[0]["ok"] is False
        assert events[0]["command"] == f"{_PROBE_PATH} CURRENTCUE,FADER"


class TestStateBodyFetcher:
    def _fetcher(self, tree: dict, calls: list | None = None):
        def query(path: str) -> dict:
            if calls is not None:
                calls.append(path)
            if path not in tree:
                raise StateQueryError(f"no reply for {path}")
            return tree[path]

        return StateBodyFetcher(query)

    def test_macro_body_lines_come_from_child_names(self):
        fetcher = self._fetcher(
            {"DataPool/Macros/9": {"ok": True, "children": [{"name": "Store Cue 1"}]}}
        )
        assert fetcher.fetch_body("Macro 9") == ("Store Cue 1",)

    def test_unmapped_reference_type_is_unavailable(self):
        fetcher = self._fetcher({})
        with pytest.raises(BodyUnavailable, match="mapping"):
            fetcher.fetch_body("Group 1")

    def test_query_failure_is_unavailable(self):
        fetcher = self._fetcher({})
        with pytest.raises(BodyUnavailable):
            fetcher.fetch_body("Macro 9")

    def test_empty_body_is_unavailable(self):
        fetcher = self._fetcher({"DataPool/Macros/9": {"ok": True, "children": []}})
        with pytest.raises(BodyUnavailable, match="empty"):
            fetcher.fetch_body("Macro 9")


class TestStateBodyFetcherExecutor:
    """M4 (REQ-EXECBODY-004): Executor bodies aren't Children() — the fetcher
    delegates via the M2-exposed assigned-sequence identity (``node.sequenceNo``,
    PROTOCOL.md §4.2) to the already-trusted Sequence body path.
    """

    def _fetcher(self, tree: dict, calls: list | None = None):
        def query(path: str) -> dict:
            if calls is not None:
                calls.append(path)
            if path not in tree:
                raise StateQueryError(f"no reply for {path}")
            return tree[path]

        return StateBodyFetcher(query)

    def test_executor_body_delegates_to_assigned_sequence(self):
        calls: list[str] = []
        fetcher = self._fetcher(
            {
                "Executor 201": {
                    "ok": True,
                    "node": {"class": "Executor", "sequenceNo": 71},
                },
                "DataPool/Sequences/71": {"ok": True, "children": [{"name": "Store Cue 1"}]},
            },
            calls,
        )
        assert fetcher.fetch_body("Executor 201") == ("Store Cue 1",)
        assert calls == ["Executor 201", "DataPool/Sequences/71"]

    def test_executor_unassigned_is_unavailable(self):
        # Node resolves, but nothing is assigned to it (no sequenceNo key —
        # PROTOCOL.md §4.2: "absent entirely ... when unassigned").
        fetcher = self._fetcher({"Executor 201": {"ok": True, "node": {"class": "Executor"}}})
        with pytest.raises(BodyUnavailable, match="Executor 201"):
            fetcher.fetch_body("Executor 201")

    def test_executor_identity_query_timeout_is_unavailable(self):
        # The identity query itself never replies (tree has no matching key ->
        # the stub query raises StateQueryError, same shape as a live timeout).
        fetcher = self._fetcher({})
        with pytest.raises(BodyUnavailable, match="identity"):
            fetcher.fetch_body("Executor 201")

    def test_executor_identity_property_absent_is_unavailable(self):
        # The reply arrived but carries no `node` at all (malformed/degenerate
        # payload) — the sequenceNo property itself is unreadable.
        fetcher = self._fetcher({"Executor 201": {"ok": True}})
        with pytest.raises(BodyUnavailable):
            fetcher.fetch_body("Executor 201")

    def test_executor_sequence_body_itself_unavailable_propagates(self):
        # Identity resolves fine, but the assigned sequence's own body query
        # fails — the existing Sequence fetch path's error propagates unchanged
        # (AC-EXECBODY-004: no regression to the Macro/Plugin/Sequence paths).
        fetcher = self._fetcher(
            {"Executor 201": {"ok": True, "node": {"class": "Executor", "sequenceNo": 99}}}
        )
        with pytest.raises(BodyUnavailable, match="Sequence 99"):
            fetcher.fetch_body("Executor 201")

    def test_executor_identity_derivation_never_reads_name(self):
        # AC-EXECBODY-005: identity derivation must not parse the executor's
        # display name — a name-bearing-but-sequenceNo-less reply still holds.
        fetcher = self._fetcher(
            {"Executor 201": {"ok": True, "node": {"class": "Executor", "name": "Exec 71"}}}
        )
        with pytest.raises(BodyUnavailable):
            fetcher.fetch_body("Executor 201")

    def test_executor_assigned_to_empty_sequence_is_a_positive_pass(self):
        # M5 / acceptance.md §D "빈 시퀀스": a verified-empty body (query
        # succeeded, 0 cues) is NOT the same failure as a body that could not
        # be verified at all — no risky command can hide in zero lines, so
        # this returns an empty body rather than holding.
        fetcher = self._fetcher(
            {
                "Executor 201": {
                    "ok": True,
                    "node": {"class": "Executor", "sequenceNo": 71},
                },
                "DataPool/Sequences/71": {"ok": True, "children": []},
            }
        )
        assert fetcher.fetch_body("Executor 201") == ()

    def test_executor_assigned_sequence_query_failure_still_unavailable(self):
        # Distinct from the empty-pass case above: the sequence's own state
        # query never resolves at all (not in the tree) -> genuinely
        # unverifiable, must still hold.
        fetcher = self._fetcher(
            {"Executor 201": {"ok": True, "node": {"class": "Executor", "sequenceNo": 71}}}
        )
        with pytest.raises(BodyUnavailable, match="Sequence 71"):
            fetcher.fetch_body("Executor 201")
