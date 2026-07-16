"""Live-lock and health-monitor tests (M4 — REQ-MVP-016/030/031/035 seed).

The lock is a plain state object (lock-FIRST semantics are enforced by the
gate, tested in test_safety_gate.py). The health monitor classifies console
liveness: console-offline (no traffic at all) vs responder-degraded (native
console traffic seen recently, but the responder heartbeat fails).
"""

from __future__ import annotations

from server.safety.lock import LiveLock, ProposalCard
from server.safety.monitor import HealthMonitor


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestLiveLock:
    def test_lock_starts_inactive(self):
        assert LiveLock().is_active is False

    def test_activate_and_deactivate(self):
        lock = LiveLock()
        lock.activate()
        assert lock.is_active is True
        lock.deactivate()
        assert lock.is_active is False

    def test_proposal_card_is_a_structured_object(self):
        card = ProposalCard(
            commands=("Store Cue 5",),
            reasons=("live lock active — read-only mode",),
        )
        assert card.commands == ("Store Cue 5",)
        assert card.reasons


class TestHealthMonitor:
    def test_initial_state_is_online(self):
        monitor = HealthMonitor(clock=FakeClock())
        assert monitor.state == HealthMonitor.ONLINE
        assert monitor.executions_blocked is False

    def test_ping_timeout_with_no_traffic_means_console_offline(self):
        # REQ-MVP-030: heartbeat/query timeout -> console offline.
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_ping_timeout()
        assert monitor.state == HealthMonitor.CONSOLE_OFFLINE
        assert monitor.executions_blocked is True

    def test_ping_timeout_with_recent_traffic_means_responder_degraded(self):
        # REQ-MVP-031: console alive (native OSC traffic) but responder silent.
        clock = FakeClock()
        monitor = HealthMonitor(clock=clock)
        monitor.note_activity()
        clock.advance(5.0)
        monitor.note_ping_timeout()
        assert monitor.state == HealthMonitor.RESPONDER_DEGRADED
        assert monitor.executions_blocked is True

    def test_stale_traffic_outside_window_means_console_offline(self):
        clock = FakeClock()
        monitor = HealthMonitor(clock=clock, activity_window_seconds=15.0)
        monitor.note_activity()
        clock.advance(30.0)
        monitor.note_ping_timeout()
        assert monitor.state == HealthMonitor.CONSOLE_OFFLINE

    def test_query_timeout_follows_the_same_semantics(self):
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_query_timeout()
        assert monitor.state == HealthMonitor.CONSOLE_OFFLINE

    def test_ping_success_recovers_to_online(self):
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_ping_timeout()
        monitor.note_ping_success()
        assert monitor.state == HealthMonitor.ONLINE
        assert monitor.executions_blocked is False

    def test_activity_alone_does_not_clear_a_degraded_state(self):
        clock = FakeClock()
        monitor = HealthMonitor(clock=clock)
        monitor.note_activity()
        monitor.note_ping_timeout()
        assert monitor.state == HealthMonitor.RESPONDER_DEGRADED
        monitor.note_activity()  # native traffic keeps flowing
        assert monitor.state == HealthMonitor.RESPONDER_DEGRADED

    def test_activity_window_is_configurable(self):
        clock = FakeClock()
        monitor = HealthMonitor(clock=clock, activity_window_seconds=60.0)
        monitor.note_activity()
        clock.advance(30.0)
        monitor.note_ping_timeout()
        assert monitor.state == HealthMonitor.RESPONDER_DEGRADED
