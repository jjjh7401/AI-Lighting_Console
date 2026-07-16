"""Async/sync approval bridge (M5 — REQ-MVP-021, the M4 ApprovalPort wiring).

The M4 safety gate calls a SYNCHRONOUS :class:`server.safety.approval.ApprovalPort`
from the orchestrator worker thread. The WebSocket UI lives on the asyncio
event loop. This channel bridges the two without blocking the event loop:

- ``request_approval`` (gate side, worker thread) publishes the request through
  the bound ``notify`` callable and blocks on a ``threading.Event``.
- ``resolve`` (UI side, event loop) delivers the human decision and releases
  the waiting worker thread.

Fail-safe (REQ-MVP-014 — no exception via ANY route): with no UI bound, on a
notify failure, on timeout, and on disconnect (``unbind``/``deny_all_pending``)
the answer is ALWAYS deny. Lock-first (REQ-MVP-035) needs no help here — the
gate re-checks the lock after approval returns.

The optional recorder brackets the human wait (acceptance "왕복 시간 측정 방법"
§3 — approval wait is subtracted from the round-trip measurement).
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Callable
from typing import Protocol

from server.safety.approval import ApprovalRequest

# Default cap on how long one approval may stay pending (fail-safe deny after).
DEFAULT_APPROVAL_TIMEOUT_SECONDS = 600.0

NotifyFn = Callable[[str, ApprovalRequest], None]


class WaitRecorder(Protocol):
    """The approval-wait bracket the measurement recorder implements."""

    def approval_wait_started(self) -> None: ...

    def approval_wait_ended(self) -> None: ...


class _Pending:
    __slots__ = ("event", "approved")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.approved = False


class ApprovalChannel:
    """Blocking ApprovalPort implementation bridged to the WebSocket UI."""

    def __init__(
        self,
        *,
        timeout_seconds: float | None = DEFAULT_APPROVAL_TIMEOUT_SECONDS,
        recorder: WaitRecorder | None = None,
        id_prefix: str = "approval",
    ) -> None:
        self._timeout = timeout_seconds
        self._recorder = recorder
        self._id_prefix = id_prefix
        self._counter = itertools.count(1)
        self._notify: NotifyFn | None = None
        self._pending: dict[str, _Pending] = {}
        self._lock = threading.Lock()

    # -- UI-side surface (event loop) -------------------------------------------

    def bind(self, notify: NotifyFn) -> None:
        """Attach the UI publisher (called on WebSocket connect)."""
        self._notify = notify

    def unbind(self) -> None:
        """Detach the UI (disconnect) — every pending request is denied."""
        self._notify = None
        self.deny_all_pending()

    def resolve(self, request_id: str, *, approved: bool) -> bool:
        """Deliver one human decision; False when the id is unknown/expired."""
        with self._lock:
            pending = self._pending.get(request_id)
        if pending is None:
            return False
        pending.approved = approved
        pending.event.set()
        return True

    def deny_all_pending(self) -> None:
        """Fail-safe: release every waiting request with a denial."""
        with self._lock:
            pending = list(self._pending.values())
        for entry in pending:
            entry.approved = False
            entry.event.set()

    @property
    def pending_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._pending)

    # -- gate-side surface (ApprovalPort, worker thread) -------------------------

    def request_approval(self, request: ApprovalRequest) -> bool:
        """Block until the human decides; deny on no-UI/notify-failure/timeout."""
        notify = self._notify
        if notify is None:
            return False  # no approval UI connected — nothing risky may run
        request_id = f"{self._id_prefix}-{next(self._counter)}"
        pending = _Pending()
        with self._lock:
            self._pending[request_id] = pending
        try:
            notify(request_id, request)
        except Exception:
            with self._lock:
                self._pending.pop(request_id, None)
            return False  # the UI never saw the request — deny (fail-safe)
        if self._recorder is not None:
            self._recorder.approval_wait_started()
        try:
            signaled = pending.event.wait(self._timeout)
            return bool(signaled and pending.approved)
        finally:
            if self._recorder is not None:
                self._recorder.approval_wait_ended()
            with self._lock:
                self._pending.pop(request_id, None)
