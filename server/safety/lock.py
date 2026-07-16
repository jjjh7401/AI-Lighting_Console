"""Live lock (REQ-MVP-016) — read-only mode state + the proposal card object.

While the lock is active the system sends NOTHING to the console and produces
structured proposal cards only (the M5 UI renders them). Lock-FIRST semantics
(REQ-MVP-035 — activating the lock while approvals are pending converts held
commands to non-executable) are enforced by the gate pipeline and the gate
executor, which re-check this state at every decision and send point.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProposalCard:
    """A read-only command proposal produced instead of execution (REQ-MVP-016)."""

    commands: tuple[str, ...]
    reasons: tuple[str, ...] = ()


class LiveLock:
    """Mutable live-lock state; activation may arrive mid-approval (lock-first)."""

    def __init__(self) -> None:
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False
