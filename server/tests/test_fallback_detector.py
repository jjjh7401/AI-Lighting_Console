"""Fallback detector tests (M3 — AC-MVP-031, REQ-MVP-040 part ii, AD2-m1).

Persistent-miss detection over synthetic round-trip time series: a rolling
window of the last N judged turns (retry turns excluded upstream); when the
window median exceeds the threshold for M CONSECUTIVE windows, the detector
emits a fallback decision through the injectable audit sink (the real audit
log lands in M4).
"""

from __future__ import annotations

from server.llm.config import FallbackSettings
from server.orchestrator.fallback import FallbackDetector


class RecordingSink:
    def __init__(self):
        self.events: list[dict] = []

    def record(self, event: dict) -> None:
        self.events.append(event)


def _detector(n: int = 20, m: int = 2, threshold: float = 10.0):
    sink = RecordingSink()
    detector = FallbackDetector(
        FallbackSettings(window_turns=n, consecutive_windows=m, threshold_seconds=threshold),
        audit_sink=sink,
        active_provider="scripted",
    )
    return detector, sink


class TestTrigger:
    def test_triggers_on_m_consecutive_violating_windows(self):
        # AC-MVP-031 part 1: N=20 window median >10s, M=2 consecutive -> trigger.
        detector, sink = _detector()
        for _ in range(20):
            assert detector.observe_turn(11.0) is False
        assert detector.triggered is False  # first violating window: 1 of 2
        assert detector.observe_turn(11.0) is True  # second consecutive window
        assert detector.triggered is True
        assert len(sink.events) == 1

    def test_audit_event_carries_the_fallback_decision(self):
        detector, sink = _detector()
        for _ in range(21):
            detector.observe_turn(11.0)
        event = sink.events[0]
        assert event["event"] == "provider_fallback_triggered"
        assert event["provider"] == "scripted"
        assert event["window_turns"] == 20
        assert event["consecutive_windows"] == 2
        assert event["threshold_seconds"] == 10.0
        assert event["window_median_seconds"] > 10.0

    def test_latched_after_trigger_with_a_single_audit_event(self):
        detector, sink = _detector()
        for _ in range(30):
            detector.observe_turn(11.0)
        assert detector.triggered is True
        assert len(sink.events) == 1  # decision emitted exactly once
        assert detector.observe_turn(11.0) is True


class TestNonTrigger:
    def test_fast_turns_never_trigger(self):
        detector, sink = _detector()
        for _ in range(60):
            assert detector.observe_turn(5.0) is False
        assert sink.events == []

    def test_recovery_after_one_violating_window_resets_the_count(self):
        # AC-MVP-031 part 2: a series that recovers after one violation
        # must NOT trigger.
        detector, sink = _detector()
        for duration in [12.0] * 11 + [1.0] * 9:
            detector.observe_turn(duration)
        assert detector.triggered is False  # window median 12.0 -> violation 1 of 2
        # Next turn pushes the oldest 12.0 out: median drops to 6.5 -> reset.
        for _ in range(30):
            assert detector.observe_turn(1.0) is False
        assert detector.triggered is False
        assert sink.events == []

    def test_no_evaluation_until_the_window_is_full(self):
        detector, sink = _detector(m=1)
        for _ in range(19):
            assert detector.observe_turn(11.0) is False
        assert detector.observe_turn(11.0) is True  # 20th turn fills the window
        assert len(sink.events) == 1


class TestConfigOverride:
    def test_n_and_m_overrides_are_respected(self):
        # AC-MVP-031 part 3: config-redefined N/M drive the detection.
        detector, sink = _detector(n=4, m=3)
        for index in range(5):
            assert detector.observe_turn(11.0) is False, f"turn {index + 1}"
        assert detector.observe_turn(11.0) is True  # windows 4,5,6 all violate
        assert sink.events[0]["window_turns"] == 4
        assert sink.events[0]["consecutive_windows"] == 3

    def test_threshold_override_is_respected(self):
        detector, _ = _detector(n=2, m=1, threshold=3.0)
        assert detector.observe_turn(4.0) is False  # window not yet full
        assert detector.observe_turn(4.0) is True
