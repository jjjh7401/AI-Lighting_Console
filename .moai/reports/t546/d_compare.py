"""t546 — 10곡 전후 대조: 옛 BPM(중앙값) vs 새 BPM(회귀+폴백) vs 대조군 D(온셋 접기).

각 곡에서 같은 박 시각으로
  old  = 60 / 박 간격 중앙값          (고치기 전 ``_tempo_from_beats``)
  new  = analyze() 가 쓰는 ``_tempo_from_beat_regression``
  (bar_map 은 계속 old 를 쓴다 — 오른쪽 adopt_new 열은 A 적용 뒤 bar_map 이 실제로 채택하는 값)
  D    = 온셋 접기(t536 ``probe_comb.py`` 와 같은 식, 박 추적기 안 씀)
그리고 절반/두 배 검사(``bar_map._check_bpm_half_double``)가 old·new 각각에서
무엇을 채택하는지와 격자 정합도 세 값을 낸다.

실행(워크트리 루트): uv run python .moai/reports/t546/d_compare.py
"""

import os
import sys

import librosa
import numpy as np
import soundfile as sf

sys.path.insert(0, os.getcwd())
from server.audio.analyze import (  # noqa: E402
    _HOP_LENGTH,
    _tempo_from_beat_regression,
    _tempo_from_beats,
)
from server.audio.bar_map import _check_bpm_half_double  # noqa: E402

SAMPLE_DIR = "/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music"
SONGS = [
    "/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3",
    *(
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
    ),
]


def comb_bpm(mono, sr, center):
    env = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=64)
    times = np.arange(len(env)) * 64 / sr
    env = env - env.mean()
    best_bpm, best = None, -np.inf
    for bpm in np.arange(center - 2.5, center + 2.5, 0.002):
        period = 60.0 / bpm
        phase = ((times % period) / period * 240).astype(int) % 240
        score = np.bincount(phase, weights=env, minlength=240).max()
        if score > best:
            best_bpm, best = float(bpm), score
    return best_bpm


def check(bpm, onsets):
    c = _check_bpm_half_double(np, bpm, onsets)
    return c.adopted_bpm, c.grid_lock_raw, c.grid_lock_half, c.grid_lock_double


print(
    f"{'song':22} {'old':>8} {'new':>8} {'D':>8} {'|old-D|':>7} {'|new-D|':>7} | "
    f"{'adopt_old':>9} {'lock r/h/d old':>16} | {'adopt_new':>9} {'lock r/h/d new':>16}"
)
for path in sys.argv[1:] or SONGS:
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    mono = np.ascontiguousarray(y.mean(axis=1))
    beats = librosa.beat.beat_track(y=mono, sr=sr, hop_length=_HOP_LENGTH, units="time")[1]
    onsets = np.asarray(
        librosa.onset.onset_detect(y=mono, sr=sr, hop_length=_HOP_LENGTH, units="time"),
        dtype=float,
    )
    iv = np.diff(beats)
    old = 60.0 / float(np.median(iv[iv > 0]))
    new, _ = _tempo_from_beat_regression(np, beats)
    bar_map_bpm, _ = _tempo_from_beats(np, beats)
    d = comb_bpm(mono, sr, old)
    ao, ro, ho, do = check(old, onsets)
    an, rn, hn, dn = check(bar_map_bpm, onsets)
    name = os.path.basename(path)[:22]
    print(
        f"{name:22} {old:8.3f} {new:8.3f} {d:8.3f} {abs(old - d):7.3f} {abs(new - d):7.3f} | "
        f"{ao:9.3f} {ro:5.2f}/{ho:5.2f}/{do:5.2f} | {an:9.3f} {rn:5.2f}/{hn:5.2f}/{dn:5.2f}",
        flush=True,
    )
