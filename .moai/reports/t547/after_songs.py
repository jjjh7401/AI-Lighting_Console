"""t547 — 재설계(REQ-LDBARMAP-006) GREEN 이후, 10곡 통제군 재확인 (읽기 전용).

``probe_songs.py``(옛 설계, 고정 격자 비교) 와 같은 10곡 목록을 그대로 쓰되,
``_check_bpm_half_double`` 의 새 시그니처(beat_times·onset_strength 환경·
표본율)로 다시 잰다. med(중앙값 BPM)·reg(회귀 BPM) 둘 다로 호출해, 새 설계가
median_bpm 경로 뿐 아니라 "정확한" 회귀 BPM 경로에서도 거짓 두 배를 내지
않는지 확인한다 — probe_songs.txt 가 보인 결함(LOVE ATTACK·Let's Dance·
LoveMe 거짓 두 배)이 사라지는지가 이 스크립트의 목적이다.

실행(워크트리 루트): uv run python .moai/reports/t547/after_songs.py
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

print(
    f"{'song':22} {'med':>8} {'reg':>8} | "
    f"{'outcome@med':>12} {'adopt@med':>9} {'amb@med':>7} | "
    f"{'outcome@reg':>12} {'adopt@reg':>9} {'amb@reg':>7}"
)
for path in sys.argv[1:] or SONGS:
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    mono = np.ascontiguousarray(y.mean(axis=1))
    beats = librosa.beat.beat_track(y=mono, sr=sr, hop_length=_HOP_LENGTH, units="time")[1]
    env = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=_HOP_LENGTH)
    med, _ = _tempo_from_beats(np, beats)
    reg, _ = _tempo_from_beat_regression(np, beats)
    cm = _check_bpm_half_double(np, med, beats, env, sr)
    cr = _check_bpm_half_double(np, reg, beats, env, sr)
    name = os.path.basename(path)[:22]
    print(
        f"{name:22} {med:8.3f} {reg:8.3f} | "
        f"{cm.outcome:>12} {cm.adopted_bpm:9.3f} {str(cm.ambiguous):>7} | "
        f"{cr.outcome:>12} {cr.adopted_bpm:9.3f} {str(cr.ambiguous):>7}",
        flush=True,
    )
