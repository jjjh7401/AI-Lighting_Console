"""카드 t546 — BPM 이 hop 격자 값으로 양자화되던 결함.

``_tempo_from_beats`` 는 박 간격의 **중앙값**으로 BPM 을 냈다. 박 시각은 hop 512
(44.1kHz 에서 11.6ms) 격자 위에 있으므로 간격도 그 격자의 정수배이고, 중앙값 BPM 은
그 정수배 중 하나로만 나온다 — 참 112 BPM 클릭에서 46프레임(534.06ms) = 112.347.
(t530 lane-1 실측, t536 판정 ``.moai/reports/t536/verdict.md``.)

처방: 박 시각에 박 번호를 매겨 직선을 맞춘 기울기로 BPM 을 낸다. 박 번호가 밀린
경우(반 박 자리에 박이 하나 끼면 그 뒤 번호가 모두 한 칸 밀린다)에는 기울기가
틀리므로, 잔차가 박 길이의 일정 비율을 넘으면 지금의 중앙값으로 돌아간다.

시험은 오디오 없이 합성 박 목록으로 한다 — 양자화는 hop 격자 반올림으로 그대로
재현된다(``.moai/reports/t546/cut_basis.py`` 와 같은 생성식).
"""

from __future__ import annotations

import numpy as np
import pytest

from server.audio.analyze import _tempo_from_beat_regression, _tempo_from_beats, analyze

_HOP_S = 512 / 44100


def _quantized_beats(bpm: float, count: int = 300, jitter_s: float = 0.0, seed: int = 0):
    rng = np.random.default_rng(seed)
    times = np.arange(count) * 60.0 / bpm + 0.5 + rng.normal(0.0, jitter_s, count)
    return np.round(times / _HOP_S) * _HOP_S


class TestHopGridQuantization:
    @pytest.mark.parametrize("true_bpm", [76.0, 112.0, 120.0, 128.5, 139.7, 160.0])
    def test_bpm_is_not_stuck_on_the_hop_grid(self, true_bpm):
        # 고치기 전: 112 → 112.347, 128.5 → 129.199 (hop 격자 한 칸).
        bpm, _confidence = _tempo_from_beat_regression(np, _quantized_beats(true_bpm))
        assert bpm == pytest.approx(true_bpm, abs=0.05)

    def test_human_timing_jitter_still_lands_near_the_true_tempo(self):
        # 사람 연주 흔들림 σ 10ms — 깨끗한 쪽 잔차 상한(박의 5%) 근처를 재현한다.
        bpm, _confidence = _tempo_from_beat_regression(np, _quantized_beats(112.0, jitter_s=0.010))
        assert bpm == pytest.approx(112.0, abs=0.1)


class TestNumberingSlipFallsBack:
    """박 번호가 밀린 목록에서는 회귀를 버리고 중앙값으로 돌아간다."""

    def test_an_inserted_half_beat_uses_the_median(self):
        beats = list(_quantized_beats(112.0, jitter_s=0.005))
        middle = len(beats) // 2
        beats.insert(middle, (beats[middle - 1] + beats[middle]) / 2)
        beats = np.asarray(beats)
        bpm, _confidence = _tempo_from_beat_regression(np, beats)
        intervals = np.diff(beats)
        assert bpm == pytest.approx(60.0 / float(np.median(intervals[intervals > 0])))

    def test_a_dropped_beat_is_renumbered_and_keeps_the_regression(self):
        # 빠진 박은 간격이 두 배라 번호 매김이 바로잡는다 — 폴백이 필요 없다.
        beats = list(_quantized_beats(112.0))
        del beats[len(beats) // 2]
        bpm, _confidence = _tempo_from_beat_regression(np, np.asarray(beats))
        assert bpm == pytest.approx(112.0, abs=0.05)


class TestUnchangedContract:
    def test_too_few_beats_still_report_nothing(self):
        assert _tempo_from_beat_regression(np, [0.0, 0.5, 1.0]) == (None, 0.0)

    def test_confidence_keeps_its_interval_spread_meaning(self):
        beats = _quantized_beats(112.0)
        intervals = np.diff(beats)
        expected = max(0.0, min(1.0, 1.0 - float(np.std(intervals)) / float(np.median(intervals))))
        _bpm, confidence = _tempo_from_beat_regression(np, beats)
        assert confidence == pytest.approx(expected)


class TestTwoPathsSplit:
    """``analyze()`` 만 회귀를 쓰고, ``bar_map`` 이 부르는 중앙값 함수는 그대로다.

    ``bar_map.detect_beat_grid`` 뒤의 절반/두 배 검사(REQ-LDBARMAP-006)는 중앙값 BPM 에
    맞춰져 있어, 정확한 BPM 을 주면 LOVE ATTACK 을 224 로 뒤집는다(카드 t547).
    """

    def test_the_median_function_keeps_its_hop_grid_value(self):
        bpm, _confidence = _tempo_from_beats(np, _quantized_beats(112.0))
        assert bpm == pytest.approx(112.347, abs=0.001)

    def test_analyze_reports_the_regressed_tempo_of_a_click_track(self):
        import io

        import soundfile as sf

        sample_rate = 44100
        audio = np.zeros(sample_rate * 30, dtype=np.float32)
        burst = np.sin(2 * np.pi * 1000 * np.arange(441) / sample_rate).astype(np.float32)
        burst *= np.hanning(882)[441:].astype(np.float32)
        period = 60.0 / 112.0
        for beat in range(int(30 / period)):
            start = int(round(beat * period * sample_rate))
            end = min(start + burst.size, audio.size)
            audio[start:end] += burst[: end - start]
        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format="WAV")

        result = analyze(buffer.getvalue())
        assert result.bpm == pytest.approx(112.0, abs=0.05)
