"""t547 — 반/두배 검사 재보정 착수 실측 (읽기 전용, 판정식 설계 입력).

각 곡에서 같은 박 시각·온셋으로
  med  = 박 간격 중앙값 BPM (bar_map 이 지금 쓰는 ``_tempo_from_beats``)
  reg  = 박 시각 회귀 BPM (analyze() 가 t546 부터 쓰는 값)
  현행 검사(``_check_bpm_half_double``)가 med·reg 각각에서 무엇을 채택하는지와 정합도 r/h/d.
그리고 고정 격자 대신 **추적된 박 시각 자체**를 격자로 쓰는 세기 지표 두 개:
  mid/on  = 이웃 박 중간점의 온셋 세기 중앙값 / 박 자리 온셋 세기 중앙값
            (1 에 가까우면 중간점도 박만큼 세다 → 추적기가 실제 박의 절반 빠르기를 짚었을 수 있다)
  odd/even = 홀수 번째 박 세기 중앙값 / 짝수 번째 박 세기 중앙값 (작은 쪽/큰 쪽, ≤1)
            (1 보다 한참 작으면 박 하나 건너 하나가 약하다 → 추적기가 두 배 빠르기를 짚었을 수 있다)

실행(워크트리 루트): uv run python .moai/reports/t547/probe_songs.py
"""

import os
import sys

import librosa
import numpy as np
import soundfile as sf

sys.path.insert(0, os.getcwd())
from server.audio.analyze import _HOP_LENGTH, _tempo_from_beat_regression, _tempo_from_beats  # noqa: E402
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


def strength_at(env, sr, times):
    frames = np.clip(np.round(times * sr / _HOP_LENGTH).astype(int), 0, len(env) - 1)
    # 박 자리 ±1 프레임 중 최댓값 — 박 추적기 위치의 프레임 반올림 오차 흡수
    lo = np.clip(frames - 1, 0, len(env) - 1)
    hi = np.clip(frames + 1, 0, len(env) - 1)
    return np.maximum(np.maximum(env[lo], env[frames]), env[hi])


print(
    f"{'song':22} {'med':>8} {'reg':>8} | {'adopt@med':>9} {'r/h/d @med':>16} | "
    f"{'adopt@reg':>9} {'r/h/d @reg':>16} | {'mid/on':>6} {'odd/even':>8}"
)
for path in sys.argv[1:] or SONGS:
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    mono = np.ascontiguousarray(y.mean(axis=1))
    beats = librosa.beat.beat_track(y=mono, sr=sr, hop_length=_HOP_LENGTH, units="time")[1]
    onsets = np.asarray(
        librosa.onset.onset_detect(y=mono, sr=sr, hop_length=_HOP_LENGTH, units="time"),
        dtype=float,
    )
    env = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=_HOP_LENGTH)
    med, _ = _tempo_from_beats(np, beats)
    reg, _ = _tempo_from_beat_regression(np, beats)
    cm = _check_bpm_half_double(np, med, onsets)
    cr = _check_bpm_half_double(np, reg, onsets)
    on = strength_at(env, sr, beats)
    mids = (beats[:-1] + beats[1:]) / 2.0
    mid = strength_at(env, sr, mids)
    mid_on = float(np.median(mid) / np.median(on))
    even, odd = np.median(on[0::2]), np.median(on[1::2])
    odd_even = float(min(even, odd) / max(even, odd))
    name = os.path.basename(path)[:22]
    print(
        f"{name:22} {med:8.3f} {reg:8.3f} | {cm.adopted_bpm:9.3f} "
        f"{cm.grid_lock_raw:5.2f}/{cm.grid_lock_half:5.2f}/{cm.grid_lock_double:5.2f} | "
        f"{cr.adopted_bpm:9.3f} {cr.grid_lock_raw:5.2f}/{cr.grid_lock_half:5.2f}/{cr.grid_lock_double:5.2f} | "
        f"{mid_on:6.2f} {odd_even:8.2f}",
        flush=True,
    )
