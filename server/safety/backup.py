"""Showfile backup policy (REQ-MVP-017) with fail-safe semantics (REQ-MVP-034).

Three backup rules: ① once at session start, ② periodic (default 10 minutes,
configurable), ③ once immediately before executing an approved risky command.
The NON-risky execution path never touches this module (round-trip budget
protection, design.md §F).

The backup mechanism is an injected action; production wires a showfile save
through the gate's audited console link (``SaveShow`` — see
:meth:`server.safety.gate.SafetyGate.make_showfile_backup_action`). Any action
failure raises :class:`BackupError` so the gate BLOCKS the planned execution
and notifies the user (fail-safe).

Snapshot retention (T-B scope A): every successful backup is retained as a
named, human-labeled :class:`Snapshot` (bounded by ``max_snapshots`` — an
eviction beyond the cap is announced via ``on_snapshot_evicted``, never
silently dropped). :meth:`BackupManager.find_snapshot` is a pure restore
*target-selection* lookup — it resolves and validates a snapshot id but never
sends anything. :meth:`BackupManager.snapshot_before` pairs a snapshot with
an :class:`~server.safety.audit.AuditLog` entry's ``ts`` on their shared
UTC ISO-8601 timeline, answering "what was the last snapshot right before
this audited command?" — the evidence a future restore decision would need.

T-B2 scope cut: an actual restore SEND path (loading a snapshot back onto the
console) is deliberately NOT part of this module — see the ``@MX:NOTE`` seat
in ``server/safety/gate.py`` next to :meth:`make_showfile_backup_action` for
where it would go, and why it needs its own SPEC + live calibration first.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

# REQ-MVP-017 rule ②: periodic backup every 10 minutes by default.
DEFAULT_INTERVAL_SECONDS = 600.0

# Human-readable label stems per backup trigger (REQ-MVP-017 rules ①②③).
_TRIGGER_LABELS = {
    "session_start": "session start",
    "periodic": "periodic backup",
    "pre_risky": "pre-risky backup",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


class BackupError(Exception):
    """A backup attempt failed — planned executions must be blocked."""


class RestoreError(Exception):
    """A restore *target* could not be resolved (e.g. an unknown snapshot
    id). Raised only by the pure selection API (:meth:`BackupManager.find_snapshot`)
    — there is no restore SEND path in this module (see module docstring)."""


@dataclass(frozen=True)
class Snapshot:
    """One retained backup point, addressable as a future restore target."""

    id: str
    trigger: str
    at: float
    label: str
    taken_at: str  # UTC ISO-8601, comparable against AuditLog event "ts"


class BackupManager:
    """Drives the 3-rule backup policy against an injected backup action, and
    retains each backup as a named, labeled :class:`Snapshot`."""

    def __init__(
        self,
        *,
        backup_action: Callable[[], None],
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = _utc_now,
        max_snapshots: int | None = None,
        on_snapshot_evicted: Callable[[Snapshot], None] | None = None,
    ) -> None:
        self._backup_action = backup_action
        self._interval_seconds = interval_seconds
        self._clock = clock
        self._wall_clock = wall_clock
        self._max_snapshots = max_snapshots
        self._on_snapshot_evicted = on_snapshot_evicted
        self._last_backup_at: float | None = None
        self._snapshot_seq = 0
        self.history: list[tuple[str, float]] = []
        self.snapshots: list[Snapshot] = []

    def _backup(self, trigger: str) -> None:
        try:
            self._backup_action()
        except Exception as error:
            raise BackupError(f"backup failed ({trigger}): {error}") from error
        at = self._clock()
        self._last_backup_at = at
        self.history.append((trigger, at))
        self._snapshot_seq += 1
        snapshot = Snapshot(
            id=f"{trigger}-{self._snapshot_seq}",
            trigger=trigger,
            at=at,
            label=f"{_TRIGGER_LABELS.get(trigger, trigger)} #{self._snapshot_seq}",
            taken_at=self._wall_clock().isoformat(),
        )
        self.snapshots.append(snapshot)
        if self._max_snapshots is not None and len(self.snapshots) > self._max_snapshots:
            evicted = self.snapshots.pop(0)
            if self._on_snapshot_evicted is not None:
                self._on_snapshot_evicted(evicted)

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

    def latest_snapshot(self) -> Snapshot | None:
        """The most recently retained snapshot, or None if none exist yet."""
        return self.snapshots[-1] if self.snapshots else None

    def find_snapshot(self, snapshot_id: str) -> Snapshot:
        """Pure restore target-selection lookup: resolve and validate a
        snapshot id, never send anything. Raises RestoreError if unknown
        (including one evicted past ``max_snapshots``)."""
        for snapshot in self.snapshots:
            if snapshot.id == snapshot_id:
                return snapshot
        raise RestoreError(f"unknown snapshot id: {snapshot_id!r}")

    def snapshot_before(self, moment: str) -> Snapshot | None:
        """The most recent retained snapshot at or before a UTC ISO-8601
        moment (e.g. an :class:`~server.safety.audit.AuditLog` event's
        ``ts``) — "what was the last snapshot right before this command?"

        Both this manager's ``taken_at`` and AuditLog's ``ts`` are UTC
        ISO-8601 strings from the same clock family, so they compare
        lexicographically without parsing. Snapshots are stored in
        chronological order, so the last match is the most recent one.
        """
        candidates = [s for s in self.snapshots if s.taken_at <= moment]
        return candidates[-1] if candidates else None

    def snapshot_before_event(self, event: dict) -> Snapshot | None:
        """Convenience: :meth:`snapshot_before` reading ``ts`` from an
        AuditLog event dict (as yielded by ``AuditLog.iter_events``)."""
        return self.snapshot_before(event["ts"])
