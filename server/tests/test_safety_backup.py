"""Backup policy tests (M4 — REQ-MVP-017/034, AC-MVP-008/022 seed).

Three rules: ① once at session start, ② periodic (default 10 min, configurable),
③ once immediately before executing an approved risky command. Backup failure
is fail-safe: BackupError propagates so the gate blocks the planned execution.
Deterministic via a fake monotonic clock; the backup action is injected.
"""

from __future__ import annotations

import pytest

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


class TestRestore:
    def test_restore_invokes_the_restore_action_with_the_snapshot(self):
        clock = FakeClock()
        backup_action = SpyAction()
        backup_action.clock = clock
        restored: list[Snapshot] = []
        manager = BackupManager(
            backup_action=backup_action,
            clock=clock,
            restore_action=lambda snapshot: restored.append(snapshot),
        )
        manager.session_start()
        snapshot_id = manager.latest_snapshot().id
        clock.advance(5.0)
        manager.restore(snapshot_id)
        assert restored == [manager.snapshots[0]]
        assert manager.restore_history == [(snapshot_id, clock())]

    def test_restore_never_touches_the_periodic_timer_or_history(self):
        clock = FakeClock()
        backup_action = SpyAction()
        backup_action.clock = clock
        manager = BackupManager(
            backup_action=backup_action, clock=clock, restore_action=lambda snapshot: None
        )
        manager.session_start()
        history_before = list(manager.history)
        manager.restore(manager.latest_snapshot().id)
        assert manager.history == history_before

    def test_restore_without_configured_action_raises_restore_error(self):
        manager, _, _ = _manager()
        manager.session_start()
        with pytest.raises(RestoreError, match="no restore action configured"):
            manager.restore(manager.latest_snapshot().id)

    def test_restore_unknown_snapshot_raises_before_invoking_the_action(self):
        calls: list[str] = []
        manager, _, _ = _manager()
        manager.session_start()
        manager._restore_action = lambda snapshot: calls.append(snapshot.id)
        with pytest.raises(RestoreError, match="unknown snapshot id"):
            manager.restore("nope")
        assert calls == []

    def test_restore_action_failure_raises_restore_error(self):
        def failing_restore(snapshot):
            raise RuntimeError("console rejected the load")

        manager, _, _ = _manager()
        manager.session_start()
        manager._restore_action = failing_restore
        with pytest.raises(RestoreError, match="restore failed"):
            manager.restore(manager.latest_snapshot().id)
        assert manager.restore_history == []
