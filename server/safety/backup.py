"""Showfile backup policy (REQ-MVP-017) with fail-safe semantics (REQ-MVP-034).

Three rules: ① once at session start, ② periodic (default 10 minutes,
configurable), ③ once immediately before executing an approved risky command.
The NON-risky execution path never touches this module (round-trip budget
protection, design.md §F).

The backup mechanism is an injected action; production wires a showfile save
through the gate's audited console link (``SaveShow`` — see
:meth:`server.safety.gate.SafetyGate.make_showfile_backup_action`). Any action
failure raises :class:`BackupError` so the gate BLOCKS the planned execution
and notifies the user (fail-safe).
"""

from __future__ import annotations

import time
from collections.abc import Callable

# REQ-MVP-017 rule ②: periodic backup every 10 minutes by default.
DEFAULT_INTERVAL_SECONDS = 600.0


class BackupError(Exception):
    """A backup attempt failed — planned executions must be blocked."""


class BackupManager:
    """Drives the 3-rule backup policy against an injected backup action."""

    def __init__(
        self,
        *,
        backup_action: Callable[[], None],
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backup_action = backup_action
        self._interval_seconds = interval_seconds
        self._clock = clock
        self._last_backup_at: float | None = None
        self.history: list[tuple[str, float]] = []

    def _backup(self, trigger: str) -> None:
        try:
            self._backup_action()
        except Exception as error:
            raise BackupError(f"backup failed ({trigger}): {error}") from error
        at = self._clock()
        self._last_backup_at = at
        self.history.append((trigger, at))

    def session_start(self) -> None:
        """Rule ①: one backup at session start."""
        self._backup("session_start")

    def tick(self) -> bool:
        """Rule ②: back up when the interval has elapsed since the last backup.

        Returns True when a backup was performed. Any backup (of any trigger)
        resets the periodic timer — a backup is a backup.
        """
        if self._last_backup_at is None:
            self._backup("periodic")
            return True
        if self._clock() - self._last_backup_at >= self._interval_seconds:
            self._backup("periodic")
            return True
        return False

    def before_risky_execution(self) -> None:
        """Rule ③: one extra backup immediately before an approved risky command."""
        self._backup("pre_risky")
