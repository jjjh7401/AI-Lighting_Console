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
