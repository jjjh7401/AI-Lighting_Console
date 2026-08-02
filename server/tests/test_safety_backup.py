"""Backup policy tests (M4 — REQ-MVP-017/034, AC-MVP-008/022 seed).

Three rules: ① once at session start, ② periodic (default 10 min, configurable),
③ once immediately before executing an approved risky command. Backup failure
is fail-safe: BackupError propagates so the gate blocks the planned execution.
Deterministic via a fake monotonic clock; the backup action is injected.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from server.safety.audit import AuditLog
from server.safety.backup import BackupError, BackupManager, RestoreError, Snapshot


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SpyAction:
    def __init__(self, fail: bool = False):
        self.calls: list[float] = []
        self.fail = fail
        self.clock: FakeClock | None = None

    def __call__(self) -> None:
        if self.clock is not None:
            self.calls.append(self.clock())
        else:
            self.calls.append(0.0)
        if self.fail:
            raise RuntimeError("disk full")


def _manager(fail: bool = False, **kwargs):
    clock = FakeClock()
    action = SpyAction(fail=fail)
    action.clock = clock
    manager = BackupManager(backup_action=action, clock=clock, **kwargs)
    return manager, action, clock


class TestSessionStartRule:
    def test_session_start_performs_one_backup(self):
        manager, action, _ = _manager()
        manager.session_start()
        assert len(action.calls) == 1
        assert [t for t, _ in manager.history] == ["session_start"]

    def test_session_start_failure_raises_backup_error(self):
        manager, _, _ = _manager(fail=True)
        with pytest.raises(BackupError):
            manager.session_start()


class TestPeriodicRule:
    def test_tick_before_interval_does_not_backup(self):
        manager, action, clock = _manager()
        manager.session_start()
        clock.advance(599.0)
        assert manager.tick() is False
        assert len(action.calls) == 1

    def test_tick_after_default_ten_minute_interval_backs_up(self):
        manager, action, clock = _manager()
        manager.session_start()
        clock.advance(600.0)
        assert manager.tick() is True
        assert len(action.calls) == 2
        assert manager.history[-1][0] == "periodic"

    def test_interval_is_configurable(self):
        manager, action, clock = _manager(interval_seconds=60.0)
        manager.session_start()
        clock.advance(61.0)
        assert manager.tick() is True

    def test_any_backup_resets_the_periodic_timer(self):
        manager, action, clock = _manager()
        manager.session_start()
        clock.advance(500.0)
        manager.before_risky_execution()  # resets the timer at t=1500
        clock.advance(500.0)  # only 500s since last backup
        assert manager.tick() is False

    def test_periodic_failure_raises_backup_error(self):
        manager, action, clock = _manager()
        manager.session_start()
        action.fail = True
        clock.advance(600.0)
        with pytest.raises(BackupError):
            manager.tick()


class TestPreRiskyRule:
    def test_before_risky_execution_backs_up_with_timestamp(self):
        manager, action, clock = _manager()
        manager.session_start()
        clock.advance(10.0)
        manager.before_risky_execution()
        trigger, at = manager.history[-1]
        assert trigger == "pre_risky"
        assert at == clock()

    def test_pre_risky_failure_raises_backup_error(self):
        # REQ-MVP-034 fail-safe: the gate converts this into a blocked
        # execution + user notification.
        manager, action, _ = _manager()
        manager.session_start()
        action.fail = True
        with pytest.raises(BackupError, match="backup failed"):
            manager.before_risky_execution()


class TestSnapshotRetention:
    def test_every_successful_backup_is_retained_as_a_snapshot(self):
        manager, _, clock = _manager()
        manager.session_start()
        clock.advance(600.0)
        manager.tick()
        assert [s.trigger for s in manager.snapshots] == ["session_start", "periodic"]
        assert manager.latest_snapshot().trigger == "periodic"

    def test_snapshot_ids_are_unique_and_stable(self):
        manager, _, clock = _manager()
        manager.session_start()
        clock.advance(10.0)
        manager.before_risky_execution()
        ids = [s.id for s in manager.snapshots]
        assert len(ids) == len(set(ids))
        assert manager.find_snapshot(ids[0]).trigger == "session_start"

    def test_failed_backup_is_not_retained_as_a_snapshot(self):
        manager, action, _ = _manager(fail=True)
        with pytest.raises(BackupError):
            manager.session_start()
        assert manager.snapshots == []

    def test_max_snapshots_evicts_oldest_first(self):
        manager, _, clock = _manager(max_snapshots=2)
        manager.session_start()
        clock.advance(10.0)
        manager.before_risky_execution()
        clock.advance(10.0)
        manager.before_risky_execution()
        assert len(manager.snapshots) == 2
        assert [s.trigger for s in manager.snapshots] == ["pre_risky", "pre_risky"]

    def test_no_snapshots_yet_reports_none(self):
        manager, _, _ = _manager()
        assert manager.latest_snapshot() is None

    def test_find_unknown_snapshot_raises_restore_error(self):
        manager, _, _ = _manager()
        manager.session_start()
        with pytest.raises(RestoreError, match="unknown snapshot id"):
            manager.find_snapshot("does-not-exist")

    def test_evicted_snapshot_is_no_longer_findable(self):
        manager, _, clock = _manager(max_snapshots=1)
        manager.session_start()
        evicted_id = manager.latest_snapshot().id
        clock.advance(10.0)
        manager.before_risky_execution()
        with pytest.raises(RestoreError, match="unknown snapshot id"):
            manager.find_snapshot(evicted_id)


class TestSnapshotTargetSelection:
    """T-B2 scope cut: only a pure target-selection lookup remains — no
    restore SEND path exists in this module (see module docstring)."""

    def test_find_snapshot_returns_the_matching_snapshot_without_side_effects(self):
        manager, _, clock = _manager()
        manager.session_start()
        clock.advance(10.0)
        manager.before_risky_execution()
        target = manager.snapshots[0]
        found = manager.find_snapshot(target.id)
        assert found == target
        # Purely a lookup: no state changed, nothing sent anywhere.
        assert manager.snapshots == [target, manager.snapshots[1]]

    def test_latest_snapshot_is_the_natural_default_restore_target(self):
        manager, _, clock = _manager()
        manager.session_start()
        clock.advance(10.0)
        manager.before_risky_execution()
        assert manager.latest_snapshot() == manager.snapshots[-1]


class TestSnapshotLabel:
    """T-B2 scope A (a): every snapshot carries a human-readable label."""

    def test_session_start_snapshot_has_a_human_readable_label(self):
        manager, _, _ = _manager()
        manager.session_start()
        assert manager.latest_snapshot().label == "session start #1"

    def test_labels_are_distinguishable_per_trigger_and_sequence(self):
        manager, _, clock = _manager()
        manager.session_start()
        clock.advance(10.0)
        manager.before_risky_execution()
        clock.advance(600.0)
        manager.tick()
        labels = [s.label for s in manager.snapshots]
        assert labels == ["session start #1", "pre-risky backup #2", "periodic backup #3"]
        assert len(set(labels)) == len(labels)


class TestSnapshotAuditCorrelation:
    """T-B2 scope A (b): pair snapshots with AuditLog entries on their shared
    UTC ISO-8601 timeline so a caller can ask "what snapshot preceded this
    audited command?" — the evidence a future restore decision would need."""

    def test_snapshot_before_returns_the_most_recent_match(self):
        wall_times = iter(
            [
                datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
                datetime(2026, 1, 1, 12, 5, 0, tzinfo=UTC),
            ]
        )
        clock = FakeClock()
        action = SpyAction()
        action.clock = clock
        manager = BackupManager(
            backup_action=action, clock=clock, wall_clock=lambda: next(wall_times)
        )
        manager.session_start()  # taken_at = 12:00:00
        clock.advance(10.0)
        manager.before_risky_execution()  # taken_at = 12:05:00

        moment_between = datetime(2026, 1, 1, 12, 2, 0, tzinfo=UTC).isoformat()
        assert manager.snapshot_before(moment_between).trigger == "session_start"

        moment_after_both = datetime(2026, 1, 1, 12, 10, 0, tzinfo=UTC).isoformat()
        assert manager.snapshot_before(moment_after_both).trigger == "pre_risky"

    def test_snapshot_before_a_moment_earlier_than_every_snapshot_is_none(self):
        manager, _, _ = _manager()
        manager.session_start()
        moment_before_anything = datetime(2000, 1, 1, tzinfo=UTC).isoformat()
        assert manager.snapshot_before(moment_before_anything) is None

    def test_snapshot_before_event_reads_ts_from_a_real_audit_log_entry(self, tmp_path):
        manager, _, _ = _manager()
        manager.session_start()
        audit = AuditLog(tmp_path / "audit")
        audit.log_executed("SaveShow", kind="backup")
        (event,) = list(audit.iter_events())
        # Both AuditLog.ts and Snapshot.taken_at are real UTC-now ISO-8601
        # timestamps here, so the audit event necessarily lands after the
        # snapshot taken moments earlier in this same test.
        assert manager.snapshot_before_event(event) == manager.latest_snapshot()


class TestSnapshotEvictionNotified:
    """T-B2 scope A (c): an eviction beyond max_snapshots must be announced,
    never silently dropped."""

    def test_on_snapshot_evicted_is_called_with_the_evicted_snapshot(self):
        evicted: list[Snapshot] = []
        clock = FakeClock()
        action = SpyAction()
        action.clock = clock
        manager = BackupManager(
            backup_action=action,
            clock=clock,
            max_snapshots=1,
            on_snapshot_evicted=evicted.append,
        )
        manager.session_start()
        first = manager.latest_snapshot()
        clock.advance(10.0)
        manager.before_risky_execution()
        assert evicted == [first]
        assert manager.snapshots == [manager.snapshots[0]]

    def test_no_callback_configured_still_evicts_without_raising(self):
        manager, _, clock = _manager(max_snapshots=1)
        manager.session_start()
        clock.advance(10.0)
        manager.before_risky_execution()  # must not raise despite no callback
        assert len(manager.snapshots) == 1
