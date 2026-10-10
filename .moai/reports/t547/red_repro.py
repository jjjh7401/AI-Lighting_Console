"""t547 RED reproduction — OLD ``_check_bpm_half_double``(고정 격자 비교)가 정확한
(회귀) BPM 을 받으면 112→224 로 거짓 두 배를 낸다는 것을, 실제 함수 호출로 확인한다
(probe_songs.txt 가 이미 보인 결함을 CI-safe 합성 신호로 재현 — RED 단계 증거,
GREEN 이후에는 이 스크립트가 호출하는 3-인자 구형 시그니처가 존재하지 않는다).

실행: uv run python .moai/reports/t547/red_repro.py
"""

import sys

sys.path.insert(0, ".")
import librosa
import numpy as np

from server.audio.analyze import _HOP_LENGTH, _tempo_from_beat_regression, _tempo_from_beats
from server.audio.bar_map import _check_bpm_half_double

SR = 22050
rng = np.random.default_rng(112)


def click(sig, t, amp):
    i = int(t * SR)
    n = int(0.03 * SR)
    if i + n < len(sig):
        sig[i : i + n] += amp * np.exp(-np.arange(n) / (0.004 * SR)) * rng.standard_normal(n)


def render(bpm, dur, pattern):
    sig = np.zeros(int(dur * SR))
    beat = 60 / bpm
    k = 0
    t = 0.5
    while t < dur - 1:
        pat = pattern[k % len(pattern)]
        for j, a in enumerate(pat):
            if a > 0:
                click(sig, t + j * beat / len(pat), a)
        t += beat
        k += 1
    return (sig + 0.001 * rng.standard_normal(len(sig))).astype(np.float32)


y = render(112, 90.0, [[1.0, 0.3]])
beat_times = librosa.beat.beat_track(y=y, sr=SR, hop_length=_HOP_LENGTH, units="time")[1]
onset_times = librosa.onset.onset_detect(y=y, sr=SR, hop_length=_HOP_LENGTH, units="time")

median_bpm, _ = _tempo_from_beats(np, beat_times)
reg_bpm, _ = _tempo_from_beat_regression(np, beat_times)
print(f"median_bpm (what detect_beat_grid currently feeds)={median_bpm}")
print(f"regression_bpm (accurate - what analyze() uses since PR #593)={reg_bpm}")

print("\n--- OLD _check_bpm_half_double fed the MEDIAN bpm (via detect_beat_grid today) ---")
check_median = _check_bpm_half_double(np, float(median_bpm), np.asarray(onset_times, dtype=float))
print(f"adopted_bpm={check_median.adopted_bpm} trap_triggered={check_median.trap_triggered}")
print(check_median.rationale)

print("\n--- OLD _check_bpm_half_double fed the ACCURATE regression bpm (reproduces defect) ---")
check_reg = _check_bpm_half_double(np, float(reg_bpm), np.asarray(onset_times, dtype=float))
print(f"adopted_bpm={check_reg.adopted_bpm} trap_triggered={check_reg.trap_triggered}")
print(check_reg.rationale)

print(
    f"\nASSERTION (this is what the NEW design must satisfy): adopted_bpm should "
    f"stay near {reg_bpm:.3f}, NOT {reg_bpm * 2:.3f}"
)
is_doubled = abs(check_reg.adopted_bpm - reg_bpm * 2) < 0.01
defect = "DEFECT REPRODUCED (false double)" if is_doubled else "did not double"
print(f"OLD CODE RESULT: adopted_bpm={check_reg.adopted_bpm:.3f} -- {defect}")
