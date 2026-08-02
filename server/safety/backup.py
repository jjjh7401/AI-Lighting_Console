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

Snapshot + restore (T-B extension): every successful backup is retained as a
named :class:`Snapshot` (bounded by ``max_snapshots``, oldest evicted first),
giving the operator a set of restore points instead of only "most recent
backup timestamp". Restore is materially more dangerous than backup — it can
discard the console's current live show state — so it is deliberately NOT
part of the 3-rule auto-trigger policy above; it only runs on an explicit
:meth:`BackupManager.restore` call, and the gate-level entry point
(:meth:`server.safety.gate.SafetyGate.restore_showfile`) requires human
approval every time regardless of ruleset (approval defaults to deny-all —
gate.py module docstring). Any restore-action failure, including an unknown
snapshot id, raises :class:`RestoreError` — the same fail-safe posture
REQ-MVP-034 applies to backup.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

# REQ-MVP-017 rule ②: periodic backup every 10 minutes by default.
DEFAULT_INTERVAL_SECONDS = 600.0


class BackupError(Exception):
    """A backup attempt failed — planned executions must be blocked."""


class RestoreError(Exception):
    """A restore attempt failed or targeted an unknown snapshot."""


@dataclass(frozen=True)
class Snapshot:
    """One retained backup point, addressable as a restore target."""

    id: str
    trigger: str
    at: float


class BackupManager:
    """Drives the 3-rule backup policy against an injected backup action, and
    retains each backup as a named :class:`Snapshot` for later restore."""

    def __init__(
        self,
        *,
        backup_action: Callable[[], None],
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        max_snapshots: int | None = None,
        restore_action: Callable[[Snapshot], None] | None = None,
    ) -> None:
        self._backup_action = backup_action
        self._interval_seconds = interval_seconds
        self._clock = clock
        self._max_snapshots = max_snapshots
        self._restore_action = restore_action
        self._last_backup_at: float | None = None
        self._snapshot_seq = 0
        self.history: list[tuple[str, float]] = []
        self.snapshots: list[Snapshot] = []
        self.restore_history: list[tuple[str, float]] = []

    def _backup(self, trigger: str) -> None:
        try:
            self._backup_action()
        except Exception as error:
            raise BackupError(f"backup failed ({trigger}): {error}") from error
        at = self._clock()
        self._last_backup_at = at
        self.history.append((trigger, at))
        self._snapshot_seq += 1
        snapshot_id = f"{trigger}-{self._snapshot_seq}"
        self.snapshots.append(Snapshot(id=snapshot_id, trigger=trigger, at=at))
        if self._max_snapshots is not None and len(self.snapshots) > self._max_snapshots:
            self.snapshots.pop(0)

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
        """Look up a retained snapshot by id; raises RestoreError if unknown
        (including one evicted past ``max_snapshots``)."""
        for snapshot in self.snapshots:
            if snapshot.id == snapshot_id:
                return snapshot
        raise RestoreError(f"unknown snapshot id: {snapshot_id!r}")

    def restore(self, snapshot_id: str) -> None:
        """Restore a named snapshot via the injected restore action.

        Never auto-triggered — restore only runs on an explicit call. Any
        failure (including an unknown snapshot id or no restore action
        configured) raises RestoreError; the periodic backup timer and
        history are untouched by a restore.
        """
        if self._restore_action is None:
            raise RestoreError("no restore action configured")
        snapshot = self.find_snapshot(snapshot_id)
        try:
            self._restore_action(snapshot)
        except RestoreError:
            raise
        except Exception as error:
            raise RestoreError(f"restore failed ({snapshot_id}): {error}") from error
        self.restore_history.append((snapshot_id, self._clock()))
