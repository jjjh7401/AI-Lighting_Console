"""Async/sync approval bridge tests (M5 — REQ-MVP-021, AC-MVP-016 ②).

The M4 gate calls a SYNCHRONOUS ``ApprovalPort`` from the orchestrator worker
thread; the WebSocket UI lives on the asyncio event loop. The
:class:`ApprovalChannel` bridges the two: ``request_approval`` blocks the
worker thread on a ``threading.Event`` while the decision travels over the
WebSocket; ``resolve`` is called from the event loop.

Fail-safe invariants (REQ-MVP-014 discipline): no bound UI, a notify failure,
a timeout, and a disconnect ALL deny — nothing risky runs without an explicit
human approval.
"""

from __future__ import annotations

import threading
import time

from server.safety.approval import ApprovalItem, ApprovalRequest
from server.safety.session_context import bind_session_key, new_session_key, reset_session_key
from server.web.approval_bridge import ApprovalChannel


def _request(command: str = "Delete Sequence 5") -> ApprovalRequest:
    return ApprovalRequest(
        items=(ApprovalItem(command=command, risk_reasons=("blacklist: Delete",)),)
    )


class NotifyRecorder:
    """Captures notify calls and signals the test thread."""

    def __init__(self, fail: bool = False):
        self.calls: list[tuple[str, ApprovalRequest]] = []
        self.notified = threading.Event()
        self.fail = fail

    def __call__(self, request_id: str, request: ApprovalRequest) -> None:
        if self.fail:
            raise RuntimeError("websocket closed")
        self.calls.append((request_id, request))
        self.notified.set()


class WaitRecorder:
    """Stub recorder capturing approval-wait bracket calls."""

    def __init__(self):
        self.events: list[str] = []

    def approval_wait_started(self) -> None:
        self.events.append("started")

    def approval_wait_ended(self) -> None:
        self.events.append("ended")


def _request_in_thread(channel, request=None):
    result: dict = {}

    def run():
        result["approved"] = channel.request_approval(request or _request())

    thread = threading.Thread(target=run)
    thread.start()
    return thread, result


def _request_in_thread_for_session(channel, session_key, request=None):
    """Like ``_request_in_thread`` but the request runs under ``session_key`` —
    the ambient context ``ChatSession.run_instruction`` binds around one turn.
    """
    result: dict = {}

    def run():
        token = bind_session_key(session_key)
        try:
            result["approved"] = channel.request_approval(request or _request())
        finally:
            reset_session_key(token)

    thread = threading.Thread(target=run)
    thread.start()
    return thread, result


class TestFailSafeDenials:
    def test_unbound_channel_denies_immediately(self):
        channel = ApprovalChannel()
        assert channel.request_approval(_request()) is False

    def test_notify_failure_denies(self):
        channel = ApprovalChannel()
        channel.bind(NotifyRecorder(fail=True))
        assert channel.request_approval(_request()) is False

    def test_timeout_denies(self):
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=0.05)
        channel.bind(notify)
        started = time.monotonic()
        assert channel.request_approval(_request()) is False
        assert time.monotonic() - started < 5.0

    def test_deny_all_pending_unblocks_with_false(self):
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        channel.bind(notify)
        thread, result = _request_in_thread(channel)
        assert notify.notified.wait(2.0)
        channel.deny_all_pending()
        thread.join(timeout=2.0)
        assert result["approved"] is False

    def test_unbind_denies_pending_requests(self):
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        channel.bind(notify)
        thread, result = _request_in_thread(channel)
        assert notify.notified.wait(2.0)
        channel.unbind()
        thread.join(timeout=2.0)
        assert result["approved"] is False
        # After unbind the channel is fail-safe again.
        assert channel.request_approval(_request()) is False


class TestDecisionFlow:
    def test_approve_resolves_true(self):
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        channel.bind(notify)
        thread, result = _request_in_thread(channel)
        assert notify.notified.wait(2.0)
        request_id, request = notify.calls[0]
        assert request.commands == ("Delete Sequence 5",)
        assert channel.resolve(request_id, approved=True) is True
        thread.join(timeout=2.0)
        assert result["approved"] is True

    def test_reject_resolves_false(self):
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        channel.bind(notify)
        thread, result = _request_in_thread(channel)
        assert notify.notified.wait(2.0)
        request_id, _ = notify.calls[0]
        assert channel.resolve(request_id, approved=False) is True
        thread.join(timeout=2.0)
        assert result["approved"] is False

    def test_resolving_an_unknown_id_is_ignored(self):
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        channel.bind(notify)
        thread, result = _request_in_thread(channel)
        assert notify.notified.wait(2.0)
        assert channel.resolve("no-such-id", approved=True) is False
        request_id, _ = notify.calls[0]
        channel.resolve(request_id, approved=False)
        thread.join(timeout=2.0)
        assert result["approved"] is False

    def test_request_ids_are_unique(self):
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        channel.bind(notify)
        seen: list[str] = []
        for _ in range(2):
            notify.notified.clear()
            thread, _result = _request_in_thread(channel)
            assert notify.notified.wait(2.0)
            request_id, _ = notify.calls[-1]
            seen.append(request_id)
            channel.resolve(request_id, approved=False)
            thread.join(timeout=2.0)
        assert len(set(seen)) == 2


class TestWaitMeasurement:
    def test_wait_bracket_surrounds_the_human_decision(self):
        recorder = WaitRecorder()
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None, recorder=recorder)
        channel.bind(notify)
        thread, _result = _request_in_thread(channel)
        assert notify.notified.wait(2.0)
        request_id, _ = notify.calls[0]
        channel.resolve(request_id, approved=True)
        thread.join(timeout=2.0)
        assert recorder.events == ["started", "ended"]

    def test_denied_by_unbound_channel_records_no_wait(self):
        recorder = WaitRecorder()
        channel = ApprovalChannel(recorder=recorder)
        channel.request_approval(_request())
        assert recorder.events == []


class TestSessionScopedFailSafe:
    """M6c-1 Finding 1 — the shared channel must isolate concurrent sessions.

    Production wires exactly ONE ``ApprovalChannel`` across every WebSocket
    ``ChatSession`` (``WebDeps.approval_channel``). Before this fix, ``bind``/
    ``unbind`` mutated a single scalar ``_notify`` slot and ``unbind`` denied
    the ENTIRE shared ``_pending`` dict — one session's disconnect silently
    force-denied every OTHER session's still-legitimate pending approval.
    """

    def test_unbinding_one_session_does_not_deny_anothers_pending_request(self):
        notify_a = NotifyRecorder()
        notify_b = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        key_a = new_session_key()
        key_b = new_session_key()
        channel.bind(notify_a, session_key=key_a)
        channel.bind(notify_b, session_key=key_b)

        thread_a, result_a = _request_in_thread_for_session(channel, key_a)
        assert notify_a.notified.wait(2.0)

        # Session B disconnects WHILE session A's approval is still pending.
        channel.unbind(session_key=key_b)

        # A's own pending request must be untouched by B's disconnect.
        request_id, _request_obj = notify_a.calls[0]
        assert channel.resolve(request_id, approved=True) is True
        thread_a.join(timeout=2.0)
        assert result_a["approved"] is True

    def test_own_unbind_still_denies_own_pending_request(self):
        # Fail-safe preserved (REQ-MVP-014): a session's OWN disconnect must
        # still deny its OWN pending requests.
        notify_a = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        key_a = new_session_key()
        channel.bind(notify_a, session_key=key_a)

        thread_a, result_a = _request_in_thread_for_session(channel, key_a)
        assert notify_a.notified.wait(2.0)

        channel.unbind(session_key=key_a)

        thread_a.join(timeout=2.0)
        assert result_a["approved"] is False

    def test_unscoped_callers_share_the_default_session_key(self):
        # Backward compatibility: callers that never bind/request under an
        # explicit session_key (direct gate/channel unit tests) behave exactly
        # as the pre-M6c-1 single-shared-slot channel did.
        notify = NotifyRecorder()
        channel = ApprovalChannel(timeout_seconds=None)
        channel.bind(notify)
        thread, result = _request_in_thread(channel)
        assert notify.notified.wait(2.0)
        channel.unbind()
        thread.join(timeout=2.0)
        assert result["approved"] is False
