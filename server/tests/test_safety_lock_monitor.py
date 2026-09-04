"""Live-lock and health-monitor tests (M4 — REQ-MVP-016/030/031/035 seed).

The lock is a plain state object (lock-FIRST semantics are enforced by the
gate, tested in test_safety_gate.py). The health monitor classifies console
liveness: console-offline (no traffic at all) vs responder-degraded (native
console traffic seen recently, but the responder heartbeat fails).
"""

from __future__ import annotations

import pytest

from server.safety.lock import LiveLock, ProposalCard
from server.safety.monitor import HealthMonitor
from server.safety.responder_version import (
    EXPECTED_RESPONDER_VERSION,
    VERSION_LOW,
    VERSION_OK,
    VERSION_UNRECOGNIZED,
    VERSION_UNREPORTED,
    classify_version,
)


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


class TestVersionClassification:
    """AC-READBACK2-004 계기 — 술어의 **경계 바깥까지** 쏜다.

    「낮은 버전이면 차단」만 재면 술어가 낮음 이외의 갈래를 어떻게 답하는지
    알 수 없다. 이 저장소에는 `ord(ch) < 32` 가 DEL·C1·U+2028 을 놓친 전례가
    있으므로 낮음·같음·높음·파싱 불가·빈 문자열·부재 여섯 갈래를 모두 단언한다.
    """

    @pytest.mark.parametrize(
        ("reported", "expected"),
        [
            ("1.6.3", VERSION_OK),
            ("1.6.2", VERSION_LOW),
            ("1.6.1", VERSION_LOW),
            ("1.5.9", VERSION_LOW),
            ("1.6", VERSION_LOW),  # 짧은 형태는 0 으로 채워 (1,6,0) < (1,6,3)
            ("1.6.4", VERSION_UNRECOGNIZED),  # 더 높다 — 재임포트가 아니라 조사다
            ("2.0.0", VERSION_UNRECOGNIZED),
            ("1.6.3.1", VERSION_UNRECOGNIZED),
            ("dev", VERSION_UNRECOGNIZED),
            ("v1.6.3", VERSION_UNRECOGNIZED),
            ("1.6.3-rc1", VERSION_UNRECOGNIZED),
            ("", VERSION_UNRECOGNIZED),
            ("   ", VERSION_UNRECOGNIZED),
            (None, VERSION_UNREPORTED),
        ],
    )
    def test_every_branch_of_the_family_is_answered(self, reported, expected):
        assert classify_version(reported, expected="1.6.3") == expected

    def test_the_expected_constant_classifies_itself_as_ok(self):
        # 상수가 자기 자신에 대해 OK 가 아니면 게이트가 항상 차단한다.
        assert classify_version(EXPECTED_RESPONDER_VERSION) == VERSION_OK

    def test_surrounding_whitespace_is_tolerated(self):
        assert classify_version(" 1.6.3 ", expected="1.6.3") == VERSION_OK


class TestHealthMonitorVersionStates:
    """AC-READBACK2-003·004·005·006 의 monitor 절반."""

    def test_a_low_version_is_its_own_state_not_degraded(self):
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_ping_success(version="1.6.1")
        assert monitor.state == HealthMonitor.RESPONDER_VERSION_MISMATCH
        assert monitor.state != HealthMonitor.RESPONDER_DEGRADED
        assert monitor.executions_blocked is True
        assert monitor.responder_version == "1.6.1"

    def test_an_unrecognized_version_is_a_different_state_from_a_low_one(self):
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_ping_success(version="9.9.9")
        assert monitor.state == HealthMonitor.RESPONDER_VERSION_UNRECOGNIZED
        assert monitor.state != HealthMonitor.RESPONDER_VERSION_MISMATCH
        assert monitor.executions_blocked is True

    def test_an_unparseable_version_is_unrecognized_too(self):
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_ping_success(version="dev-build")
        assert monitor.state == HealthMonitor.RESPONDER_VERSION_UNRECOGNIZED

    def test_the_expected_version_keeps_the_state_online(self):
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_ping_timeout()
        monitor.note_ping_success(version=EXPECTED_RESPONDER_VERSION)
        assert monitor.state == HealthMonitor.ONLINE
        assert monitor.executions_blocked is False

    def test_an_unreported_version_keeps_the_state_online(self):
        # 열어 둔 구멍(REQ-READBACK2-011 계열): `version` 없는 pong 은 이
        # 저장소의 오프라인 하네스가 실제로 보내는 형태이므로 차단하지 않는다.
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_ping_success()
        assert monitor.state == HealthMonitor.ONLINE
        assert monitor.responder_version is None

    def test_a_timeout_after_a_version_mismatch_falls_back_to_silence_rules(self):
        """AC-READBACK2-005 의 monitor 절반: 침묵 분류가 버전 사유를 덮어쓴다.

        성공한 ping 자체가 콘솔 트래픽이므로, 활동 창 **안**의 타임아웃은
        `responder_degraded` 이고 창을 **넘긴** 타임아웃은 `console_offline` 이다.
        어느 쪽이든 버전 상태는 남지 않는다 — 그것이 이 AC 가 재는 것이다.
        """
        clock = FakeClock()
        monitor = HealthMonitor(clock=clock, activity_window_seconds=15.0)
        monitor.note_ping_success(version="1.6.1")
        assert monitor.state == HealthMonitor.RESPONDER_VERSION_MISMATCH

        monitor.note_ping_timeout()  # 창 안 — 조금 전 응답기가 답했다
        assert monitor.state == HealthMonitor.RESPONDER_DEGRADED

        monitor.note_ping_success(version="1.6.1")
        clock.advance(30.0)  # 창을 넘긴 침묵
        monitor.note_ping_timeout()
        assert monitor.state == HealthMonitor.CONSOLE_OFFLINE

    def test_a_recovered_matching_ping_clears_a_version_mismatch(self):
        monitor = HealthMonitor(clock=FakeClock())
        monitor.note_ping_success(version="1.6.1")
        monitor.note_ping_success(version=EXPECTED_RESPONDER_VERSION)
        assert monitor.state == HealthMonitor.ONLINE
