"""Backup policy tests (M4 — REQ-MVP-017/034, AC-MVP-008/022 seed).

Three rules: ① once at session start, ② periodic (default 10 min, configurable),
③ once immediately before executing an approved risky command. Backup failure
is fail-safe: BackupError propagates so the gate blocks the planned execution.
Deterministic via a fake monotonic clock; the backup action is injected.
"""

from __future__ import annotations

import pytest

from server.safety.backup import BackupError, BackupManager


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
