"""Round-trip measurement tests (M5 — M6 prep + AD4-m1 rider).

Implements the acceptance.md "왕복 시간 측정 방법" hooks:

- §1 start event  = instruction received over WebSocket (``turn_started``)
- §2 end event    = LAST console result received (``note_console_result``)
- §3 exclusion    = human-approval wait subtracted
  (``approval_wait_started`` / ``approval_wait_ended``)
- §4 retry split  = retry turns are NOT judged (not fed to the detector)

The judged per-turn value (approval-subtracted) feeds the M3 fallback detector
(``FallbackDetector.observe_turn`` shape). Turns with zero console results have
no "실행 결과 수신" end event and are recorded but never judged.
"""

from __future__ import annotations

from server.web.measure import RoundTripRecorder, TurnRecord


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now


class RecordingDetector:
    def __init__(self):
        self.observed: list[float] = []

    def observe_turn(self, duration_seconds: float) -> bool:
        self.observed.append(duration_seconds)
        return False


def _recorder(detector=None):
    clock = FakeClock()
    return RoundTripRecorder(detector=detector, clock=clock), clock


class TestEndEventSemantics:
    def test_end_is_the_last_console_result_not_turn_finish(self):
        recorder, clock = _recorder()
        recorder.turn_started()
        clock.now = 3.0
        recorder.note_console_result()
        clock.now = 7.0  # trailing model text generation is NOT round-trip time
        record = recorder.turn_finished(retries_used=0)
        assert record.measured_seconds == 3.0
        assert record.console_results == 1

    def test_multiple_console_results_use_the_last_one(self):
        recorder, clock = _recorder()
        recorder.turn_started()
        clock.now = 1.0
        recorder.note_console_result()
        clock.now = 4.0
        recorder.note_console_result()
        clock.now = 5.0
        record = recorder.turn_finished(retries_used=0)
        assert record.measured_seconds == 4.0
        assert record.console_results == 2

    def test_zero_console_results_turn_is_recorded_but_not_judged(self):
        detector = RecordingDetector()
        recorder, clock = _recorder(detector)
        recorder.turn_started()
        clock.now = 2.0
        record = recorder.turn_finished(retries_used=0)
        assert record.judged is False
        assert detector.observed == []


class TestApprovalWaitSubtraction:
    def test_approval_wait_is_subtracted(self):
        recorder, clock = _recorder()
        recorder.turn_started()
        clock.now = 1.0
        recorder.approval_wait_started()
        clock.now = 4.0
        recorder.approval_wait_ended()  # 3s human wait
        clock.now = 5.0
        recorder.note_console_result()
        record = recorder.turn_finished(retries_used=0)
        assert record.approval_wait_seconds == 3.0
        assert record.measured_seconds == 2.0  # (5 - 0) - 3

    def test_multiple_approval_waits_accumulate(self):
        recorder, clock = _recorder()
        recorder.turn_started()
        clock.now = 1.0
        recorder.approval_wait_started()
        clock.now = 2.0
        recorder.approval_wait_ended()
        clock.now = 3.0
        recorder.approval_wait_started()
        clock.now = 5.0
        recorder.approval_wait_ended()
        clock.now = 6.0
        recorder.note_console_result()
        record = recorder.turn_finished(retries_used=0)
        assert record.approval_wait_seconds == 3.0
        assert record.measured_seconds == 3.0

    def test_approval_wait_outside_a_turn_is_a_safe_no_op(self):
        recorder, clock = _recorder()
        recorder.approval_wait_started()
        recorder.approval_wait_ended()
        assert recorder.records == ()


class TestJudgedFeed:
    def test_clean_turn_feeds_the_detector_with_the_subtracted_value(self):
        detector = RecordingDetector()
        recorder, clock = _recorder(detector)
        recorder.turn_started()
        clock.now = 2.0
        recorder.approval_wait_started()
        clock.now = 3.0
        recorder.approval_wait_ended()
        clock.now = 4.0
        recorder.note_console_result()
        record = recorder.turn_finished(retries_used=0)
        assert record.judged is True
        assert detector.observed == [3.0]

    def test_retry_turn_is_recorded_but_never_fed(self):
        detector = RecordingDetector()
        recorder, clock = _recorder(detector)
        recorder.turn_started()
        clock.now = 2.0
        recorder.note_console_result()
        record = recorder.turn_finished(retries_used=1)
        assert record.judged is False
        assert detector.observed == []
        assert len(recorder.records) == 1

    def test_error_turn_is_never_judged(self):
        detector = RecordingDetector()
        recorder, clock = _recorder(detector)
        recorder.turn_started()
        clock.now = 2.0
        recorder.note_console_result()
        record = recorder.turn_finished(retries_used=0, error=True)
        assert record.judged is False
        assert detector.observed == []

    def test_works_without_a_detector(self):
        recorder, clock = _recorder(detector=None)
        recorder.turn_started()
        clock.now = 1.0
        recorder.note_console_result()
        assert recorder.turn_finished(retries_used=0).judged is True

    def test_attach_detector_late_binds_the_feed(self):
        detector = RecordingDetector()
        recorder, clock = _recorder(detector=None)
        recorder.attach_detector(detector)
        recorder.turn_started()
        clock.now = 2.0
        recorder.note_console_result()
        recorder.turn_finished(retries_used=0)
        assert detector.observed == [2.0]


class TestLifecycle:
    def test_finish_without_start_returns_none(self):
        recorder, _ = _recorder()
        assert recorder.turn_finished(retries_used=0) is None
        assert recorder.records == ()

    def test_records_accumulate_in_order(self):
        recorder, clock = _recorder()
        for finish_at in (1.0, 2.0):
            recorder.turn_started()
            clock.now = finish_at
            recorder.note_console_result()
            recorder.turn_finished(retries_used=0)
            clock.now = 0.0 if finish_at == 1.0 else clock.now
        assert len(recorder.records) == 2
        assert all(isinstance(r, TurnRecord) for r in recorder.records)

    def test_console_result_outside_a_turn_is_a_safe_no_op(self):
        recorder, _ = _recorder()
        recorder.note_console_result()
        assert recorder.records == ()
