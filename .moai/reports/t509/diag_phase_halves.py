"""t509 — 다운비트 위상이 곡 중간에 바뀌는가(후렴 3 히트가 위상 0 에 떨어진 것의 확인).

실행: .venv/bin/python .moai/reports/t509/diag_phase_halves.py "<LOVE ATTACK.mp3>"

화성 변화(크로마 차이)를 박 위상(박 번호 % 4)별로 더하되, 곡을 세 구간
(0~70초 · 70~130초 · 130초~)으로 나눠 따로 센다. 구간마다 고른 위상이 다르면
그 사이 어딘가에서 마디 위상이 한 박 밀린 것이다.
"""

import sys

import librosa
import numpy as np

sys.path.insert(0, ".moai/reports/t505")
from measure_music_map import HOP, N_FFT, app_beats, load_like_app  # noqa: E402

y, sr = load_like_app(sys.argv[1])
beats, _, _ = app_beats(y, sr)
H, _ = librosa.decompose.hpss(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
chroma = librosa.feature.chroma_cqt(y=librosa.istft(H, hop_length=HOP), sr=sr, hop_length=HOP)
frames = librosa.time_to_frames(beats, sr=sr, hop_length=HOP)
sync = librosa.util.sync(chroma, frames, aggregate=np.median)
nov = np.r_[0.0, np.linalg.norm(np.diff(sync, axis=1), axis=0)]
for lo, hi in ((0, 70), (70, 130), (130, 200)):
    slot = np.zeros(4)
    for i, t in enumerate(beats):
        if lo <= t < hi and i < len(nov):
            slot[i % 4] += nov[i]
    best = int(np.argmax(slot))
    print(f"{lo:3d}-{hi:3d}s chroma novelty by phase {np.round(slot, 2).tolist()} -> {best}")
