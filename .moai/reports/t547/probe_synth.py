"""t547 — 합성 클릭으로 새 판정식 후보의 행동 확인 (정답을 아는 대조군).

경우마다 박 추적기(librosa beat_track hop 512)가 짚은 BPM, 그리고
  w_mid/p_mid (박 vs 중간점, 단측 부호 검정)
  w_odd/p_two (짝 vs 홀 박, 양측 부호 검정)
를 낸다. 실행: uv run python .moai/reports/t547/probe_synth.py
"""
import os, sys
import librosa, numpy as np
from scipy.stats import binomtest
sys.path.insert(0, os.getcwd())
from server.audio.analyze import _HOP_LENGTH, _tempo_from_beat_regression
SR = 22050
rng = np.random.default_rng(547)
def click(sig, t, amp):
    i = int(t * SR); n = int(0.03 * SR)
    if i + n < len(sig):
        sig[i:i + n] += amp * np.exp(-np.arange(n) / (0.004 * SR)) * rng.standard_normal(n)
def render(bpm, dur, pattern):
    """pattern: 한 박을 n 등분한 자리별 세기 목록 (마디 4박 반복, 박마다 같은 목록 또는 4개 목록)."""
    sig = np.zeros(int(dur * SR)); beat = 60 / bpm; k = 0; t = 0.5
    while t < dur - 1:
        pat = pattern[k % len(pattern)]
        for j, a in enumerate(pat):
            if a > 0: click(sig, t + j * beat / len(pat), a)
        t += beat; k += 1
    return sig + 0.001 * rng.standard_normal(len(sig))
def strength_at(env, times):
    f = np.clip(np.round(times * SR / _HOP_LENGTH).astype(int), 0, len(env) - 1)
    return np.maximum(np.maximum(env[np.clip(f - 1, 0, None)], env[f]), env[np.clip(f + 1, None, len(env) - 1)])
CASES = [
    ("112 박만(같은 세기)",          112, [[1.0]]),
    ("112 박+8분 하이햇 0.3",       112, [[1.0, 0.3]]),
    ("112 박+8분 하이햇 0.7",       112, [[1.0, 0.7]]),
    ("112 킥/스네어 1.0/0.6 +8분0.3", 112, [[1.0, 0.3], [0.6, 0.3], [1.0, 0.3], [0.6, 0.3]]),
    ("224 같은 세기(참 224)",        224, [[1.0]]),
    ("240 같은 세기(참 240)",        240, [[1.0]]),
    ("60 같은 세기(참 60)",          60, [[1.0]]),
    ("56 박+8분 0.3(참 56)",         56, [[1.0, 0.3]]),
]
print(f"{'case':30} {'tracked':>8} {'w_mid':>6} {'p_mid':>9} | {'w_odd':>6} {'p_two':>9}")
for name, bpm, pat in CASES:
    y = render(bpm, 90.0, pat).astype(np.float32)
    beats = librosa.beat.beat_track(y=y, sr=SR, hop_length=_HOP_LENGTH, units="time")[1]
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=_HOP_LENGTH)
    reg, _ = _tempo_from_beat_regression(np, beats)
    on = strength_at(env, beats); mid = strength_at(env, (beats[:-1] + beats[1:]) / 2)
    d = mid - on[:-1]; d = d[d != 0]
    w_mid = float(np.mean(d > 0)); p_mid = binomtest(int(np.sum(d < 0)), len(d), 0.5, alternative="greater").pvalue
    m = len(on) // 2 * 2; e2 = on[0:m:2] - on[1:m:2]; e2 = e2[e2 != 0]
    w_odd = float(np.mean(e2 < 0)) if len(e2) else float("nan")
    p_two = binomtest(int(np.sum(e2 > 0)), len(e2), 0.5).pvalue if len(e2) else float("nan")
    print(f"{name:30} {reg:8.2f} {w_mid:6.2f} {p_mid:9.2e} | {w_odd:6.2f} {p_two:9.2e}", flush=True)
