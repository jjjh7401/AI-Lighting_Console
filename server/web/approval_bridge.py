"""Async/sync approval bridge (M5 — REQ-MVP-021, the M4 ApprovalPort wiring).

The M4 safety gate calls a SYNCHRONOUS :class:`server.safety.approval.ApprovalPort`
from the orchestrator worker thread. The WebSocket UI lives on the asyncio
event loop. This channel bridges the two without blocking the event loop:

- ``request_approval`` (gate side, worker thread) publishes the request through
  the bound ``notify`` callable and blocks on a ``threading.Event``.
- ``resolve`` (UI side, event loop) delivers the human decision and releases
  the waiting worker thread.

Fail-safe (REQ-MVP-014 — no exception via ANY route): with no UI bound, on a
notify failure, on timeout, and on disconnect (``unbind``/``deny_pending_for``)
the answer is ALWAYS deny. Lock-first (REQ-MVP-035) needs no help here — the
gate re-checks the lock after approval returns.

The optional recorder brackets the human wait (acceptance "왕복 시간 측정 방법"
§3 — approval wait is subtracted from the round-trip measurement).

M7: the channel is payload-agnostic (it never inspects the request), so the
deploy REVIEW flow reuses it as a second instance carrying
:class:`server.deploy.review.ReviewRequest` payloads (``id_prefix="review"``);
``request_review`` aliases ``request_approval`` so the channel satisfies the
ReviewPort protocol directly — same quadruple-deny fail-safe.

M6c-1 (cross-session isolation, Finding 1): ONE channel instance is shared by
every concurrent ``ChatSession`` (``WebDeps.approval_channel`` is composed
once, before any WebSocket connects). ``bind``/``unbind`` therefore take an
explicit ``session_key`` so one session's disconnect denies ONLY that
session's own pending requests — never another session's still-legitimate
one. ``request_approval`` runs on the calling session's own worker thread and
reads the ambient session key ``ChatSession.run_instruction`` binds around
each turn (see :mod:`server.safety.session_context`) to route the notify call
and tag its pending entry. Callers outside any bound session (direct
gate/channel unit tests) all share ``DEFAULT_SESSION_KEY`` — single-session
semantics are unchanged.
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Callable
from typing import Generic, Protocol, TypeVar

from server.safety.approval import ApprovalRequest
from server.safety.session_context import DEFAULT_SESSION_KEY, SessionKey, current_session_key

# Default cap on how long one approval may stay pending (fail-safe deny after).
DEFAULT_APPROVAL_TIMEOUT_SECONDS = 600.0

# The payload type one channel instance carries (ApprovalRequest for the M4
# approval flow; server.deploy.review.ReviewRequest for the M7 review flow).
RequestT = TypeVar("RequestT")

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


class ApprovalChannel(Generic[RequestT]):
    """Blocking ApprovalPort/ReviewPort implementation bridged to the UI."""

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
        self._notify: dict[SessionKey, Callable[[str, RequestT], None]] = {}
        self._pending: dict[str, tuple[SessionKey, _Pending]] = {}
        self._lock = threading.Lock()

    # -- UI-side surface (event loop) -------------------------------------------

    def bind(
        self,
        notify: Callable[[str, RequestT], None],
        *,
        session_key: SessionKey = DEFAULT_SESSION_KEY,
    ) -> None:
        """Attach one session's UI publisher (called on WebSocket connect)."""
        with self._lock:
            self._notify[session_key] = notify

    def unbind(self, *, session_key: SessionKey = DEFAULT_SESSION_KEY) -> None:
        """Detach one session's UI (disconnect) — ONLY its own pending requests deny."""
        with self._lock:
            self._notify.pop(session_key, None)
        self.deny_pending_for(session_key)

    def resolve(self, request_id: str, *, approved: bool) -> bool:
        """Deliver one human decision; False when the id is unknown/expired."""
        with self._lock:
            entry = self._pending.get(request_id)
        if entry is None:
            return False
        _session_key, pending = entry
        pending.approved = approved
        pending.event.set()
        return True

    def deny_pending_for(self, session_key: SessionKey) -> None:
        """Fail-safe: release only ``session_key``'s waiting requests, denied.

        Called by ``unbind`` on a session's own disconnect — never touches
        another session's still-legitimate pending requests.
        """
        with self._lock:
            matching = [p for key, p in self._pending.values() if key == session_key]
        for entry in matching:
            entry.approved = False
            entry.event.set()

    def deny_all_pending(self) -> None:
        """Fail-safe: release EVERY waiting request across ALL sessions, denied."""
        with self._lock:
            pending = list(self._pending.values())
        for _session_key, entry in pending:
            entry.approved = False
            entry.event.set()

    @property
    def pending_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._pending)

    # -- gate-side surface (ApprovalPort / ReviewPort, worker thread) -------------

    def request_review(self, request: RequestT) -> bool:
        """ReviewPort alias (M7): reviews ride the same channel semantics."""
        return self.request_approval(request)

    def request_approval(self, request: RequestT) -> bool:
        """Block until the human decides; deny on no-UI/notify-failure/timeout."""
        session_key = current_session_key()
        with self._lock:
            notify = self._notify.get(session_key)
        if notify is None:
            return False  # no approval UI connected for THIS session — deny
        request_id = f"{self._id_prefix}-{next(self._counter)}"
        pending = _Pending()
        with self._lock:
            self._pending[request_id] = (session_key, pending)
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
