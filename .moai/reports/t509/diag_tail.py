"""t509 — 앱 박 추적이 끝난 175초 이후 22초에 무엇이 있는가.

실행: .venv/bin/python .moai/reports/t509/diag_tail.py "<LOVE ATTACK.mp3>"

2초 창마다 음량(RMS, 곡 중앙값 대비)과 타악 온셋 수를 센다. 그리고 그 구간만 잘라
박 추적을 따로 돌려 박이 잡히는지 본다.
"""

import sys

import librosa
import numpy as np

sys.path.insert(0, ".moai/reports/t505")
from measure_music_map import HOP, N_FFT, app_beats, load_like_app  # noqa: E402

y, sr = load_like_app(sys.argv[1])
beats, bpm, _ = app_beats(y, sr)
rms = librosa.feature.rms(y=y, frame_length=N_FFT, hop_length=HOP)[0]
med = float(np.median(rms))
ft = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=HOP)
onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=HOP, units="time")
print(f"app beats last {beats[-1]:.2f}s of {len(y) / sr:.2f}s")
for t0 in range(165, int(len(y) / sr), 2):
    m = (ft >= t0) & (ft < t0 + 2)
    n = int(np.sum((onsets >= t0) & (onsets < t0 + 2)))
    print(f"{t0:3d}-{t0 + 2:3d}s rms/med {rms[m].mean() / med:4.2f} onsets {n}")
tail = y[int(175 * sr) :]
_, bt = librosa.beat.beat_track(y=tail, sr=sr, hop_length=HOP, units="time")
iv = np.diff(bt)
tb = 60 / np.median(iv) if iv.size else float("nan")
print(f"tail-only beat_track: {len(bt)} beats, bpm {tb:.2f}")
