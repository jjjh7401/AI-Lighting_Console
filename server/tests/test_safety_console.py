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
            fetcher.fetch_body("Executor 201")

    def test_query_failure_is_unavailable(self):
        fetcher = self._fetcher({})
        with pytest.raises(BodyUnavailable):
            fetcher.fetch_body("Macro 9")

    def test_empty_body_is_unavailable(self):
        fetcher = self._fetcher({"DataPool/Macros/9": {"ok": True, "children": []}})
        with pytest.raises(BodyUnavailable, match="empty"):
            fetcher.fetch_body("Macro 9")
