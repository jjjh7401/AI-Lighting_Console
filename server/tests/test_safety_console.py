"""ConsoleLink tests (M4 — gate-owned console I/O with result confirmation).

The link wraps the M2 wire protocol (exec/state/ping requests over
``/copilot/cmd``, replies correlated by request id) and is the ONLY production
caller of the OSC send surface. Unit tests use a stub send function that
synthesizes replies synchronously through :meth:`ConsoleLink.deliver` — no
sockets, deterministic timeouts.
"""

from __future__ import annotations

import re

import pytest

from server.bridge.osc import FEEDBACK_ADDRESS, STATE_ADDRESS, FeedbackMessage
from server.bridge.protocol import encode_payload
from server.safety.console import (
    ConsoleLink,
    LinkTimeouts,
    StateBodyFetcher,
    StateQueryError,
)
from server.safety.expand import BodyUnavailable
from server.safety.monitor import HealthMonitor

_REQUEST = re.compile(r'^Plugin "CopilotResponder" "(ping|state|exec) (\S+)(?: (.*))?"$')

_FAST = LinkTimeouts(exec_confirm_seconds=0.05, ping_seconds=0.05, state_query_seconds=0.05)


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
        fetcher = self._fetcher(
            {"Executor 201": {"ok": True, "node": {"class": "Executor"}}}
        )
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
