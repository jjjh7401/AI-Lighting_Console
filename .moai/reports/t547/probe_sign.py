"""t547 — 박 자리 vs 중간점 세기의 짝지은 부호 비교 (읽기 전용).

각 이웃 박 쌍 i 에서 on_i = 박 i 세기, mid_i = 박 i 와 i+1 중간점 세기.
  w_mid = mid_i > on_i 인 비율 (두 자리가 같은 종류면 0.5 근처)
  p_mid = 단측 부호 검정 p (H0: 같은 종류, H1: 박 자리가 더 세다)
짝/홀 박도 같은 식: 박 2k vs 2k+1.
실행: uv run python .moai/reports/t547/probe_sign.py
"""

import os
import sys

import librosa
import numpy as np
import soundfile as sf
from scipy.stats import binomtest

sys.path.insert(0, os.getcwd())
from server.audio.analyze import _HOP_LENGTH

SAMPLE_DIR = "/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music"
SONGS = ["/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3"] + [
    f"{SAMPLE_DIR}/{n}"
    for n in (
        "Club Diver.mp3",
        "Cut and Run.mp3",
        "Ice cream.mp3",
        "Let's Dance.mp3",
        "LoveMe.mp3",
        "Morning.mp3",
        "Rain.mp3",
        "Too Cool.mp3",
        "scott-buckley-neon.mp3",
    )
]


def strength_at(env, sr, times):
    f = np.clip(np.round(times * sr / _HOP_LENGTH).astype(int), 0, len(env) - 1)
    lo = np.clip(f - 1, 0, len(env) - 1)
    hi = np.clip(f + 1, 0, len(env) - 1)
    return np.maximum(np.maximum(env[lo], env[f]), env[hi])


print(f"{'song':22} {'n':>4} {'w_mid':>6} {'p_mid':>9} | {'w_odd':>6} {'p_two':>9}")
for path in sys.argv[1:] or SONGS:
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    mono = np.ascontiguousarray(y.mean(axis=1))
    beats = librosa.beat.beat_track(y=mono, sr=sr, hop_length=_HOP_LENGTH, units="time")[1]
    env = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=_HOP_LENGTH)
    on = strength_at(env, sr, beats)
    mid = strength_at(env, sr, (beats[:-1] + beats[1:]) / 2)
    d = mid - on[:-1]
    d = d[d != 0]
    w_mid = float(np.mean(d > 0))
    p_mid = binomtest(int(np.sum(d < 0)), len(d), 0.5, alternative="greater").pvalue
    m = len(on) // 2 * 2
    e2 = on[0:m:2] - on[1:m:2]
    e2 = e2[e2 != 0]
    w_odd = float(np.mean(e2 < 0))
    p_two = binomtest(int(np.sum(e2 > 0)), len(e2), 0.5).pvalue
    print(
        f"{os.path.basename(path)[:22]:22} {len(beats):4d} {w_mid:6.2f} {p_mid:9.2e} | "
        f"{w_odd:6.2f} {p_two:9.2e}",
        flush=True,
    )
