"""Shared programmer mutation arbiter (M3 — REQ-LDPLUGIN-022).

Serializes EVERY shared-programmer mutation path — director apply, general
chat, import — behind ONE non-blocking lock, so that two concurrent mutation
requests targeting the same console programmer never race. The lock lives
here, in `server.director`, but is threaded through
:class:`server.safety.gate.SafetyGate`'s shared private pipeline stage (the
one stage :meth:`~server.safety.gate.SafetyGate.screen` and
:meth:`~server.safety.gate.SafetyGate.execute_preapproved` both call) —
design.md §2.3 chose that seam specifically so that
``server/orchestrator/tools.py``, ``server/web/session.py``, and
``server/measurement/runner.py`` never need to change: every one of them
already reaches the gate through ``.screen(...)``, and the lock now lives
inside that call.

Acquisition is IMMEDIATE-REJECT, never polling or waiting
(REQ-LDPLUGIN-022 — "오래 대기시켜 낡은 승인을 실행하지 않는다"): a caller
that finds the lock held raises :class:`TargetBusyError` right away. There
is no queue, so a request can never sit long enough for its approval to go
stale before it finally runs — every retry after a release re-enters the
gate's pipeline from scratch (grammar -> classify -> lock -> arbiter ->
backup), which is what re-checks freshness (the M5 apply layer will add the
actual freshness/occupancy judgment; this module only owns mutual
exclusion).
"""

from __future__ import annotations

import threading


class TargetBusyError(RuntimeError):
    """Raised when the shared programmer mutation lock is already held.

    The wire-level token this maps to is the literal REQ-LDPLUGIN-022
    vocabulary, ``TARGET_BUSY`` — carried in :attr:`str(error)` so callers
    that log or surface this exception keep that vocabulary without a
    separate translation table.
    """

    def __init__(self, held_by: str | None = None) -> None:
        self.held_by = held_by
        message = "TARGET_BUSY — shared programmer mutation lock already held"
        if held_by:
            message = f"{message} by {held_by!r}"
        super().__init__(message)


class ProgrammerArbiter:
    """Non-blocking mutual-exclusion lock for shared programmer mutation.

    ``try_acquire``/``release`` are the ONLY operations. There is
    deliberately no wait/queue/retry inside this class — see the module
    docstring for why REQ-LDPLUGIN-022 requires immediate rejection rather
    than fair queuing.

    One instance is owned by each :class:`~server.safety.gate.SafetyGate`
    (constructed once per gate, injectable for tests) — NOT a module-level
    singleton — because exactly one live ``SafetyGate`` instance is already
    shared by every concurrent ``ChatSession`` in the running app
    (``deps.gate`` in ``server/web/app.py``; see the M6c-1 note atop
    ``server/safety/gate.py``), so an instance-scoped lock already covers
    every live director/chat/import mutation path without needing
    process-global state.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._held_by: str | None = None

    @property
    def is_active(self) -> bool:
        """Best-effort — a diagnostic read, not a synchronization primitive."""
        return self._held_by is not None

    def try_acquire(self, requester: str) -> None:
        """Acquire the lock immediately, or raise :class:`TargetBusyError`.

        Never blocks. ``requester`` is carried only for diagnostics (the
        busy error message + audit trail) — it plays no role in the
        mutual-exclusion decision itself (a requester re-entering while it
        already holds the lock is busy too; this lock is not reentrant).
        """
        if not self._lock.acquire(blocking=False):
            raise TargetBusyError(held_by=self._held_by)
        self._held_by = requester

    def release(self) -> None:
        """Release the lock. Calling this without holding it is a bug in the
        caller — mirrors :meth:`threading.Lock.release`'s own contract."""
        self._held_by = None
        self._lock.release()
