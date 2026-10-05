import sys

import librosa
import numpy as np

sys.path.insert(0, ".moai/reports/t505")
from measure_music_map import HOP, N_FFT, app_beats, band_energy, load_like_app, onset_env_from

y, sr = load_like_app(sys.argv[1])
beats, bpm, _ = app_beats(y, sr)
D = librosa.stft(y, n_fft=N_FFT, hop_length=HOP)
H, P = librosa.decompose.hpss(D)
Sp = np.abs(P) ** 2
f = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
ft = librosa.frames_to_time(np.arange(Sp.shape[1]), sr=sr, hop_length=HOP)
per = np.median(np.diff(beats))
for name, band in [
    ("kick35-120", (35, 120)),
    ("snare1.5-5k", (1500, 5000)),
    ("hat6-14k", (6000, 14000)),
]:
    env = onset_env_from(band_energy(Sp, f, band))
    prof = np.zeros(16)
    cnt = np.zeros(16)
    for k in range(len(beats) - 1):
        m = (ft >= beats[k]) & (ft < beats[k + 1])
        ph = ((ft[m] - beats[k]) / (beats[k + 1] - beats[k]) * 16).astype(int).clip(0, 15)
        np.add.at(prof, ph, env[m])
        np.add.at(cnt, ph, 1)
    p = prof / np.maximum(cnt, 1)
    p = p / p.max()
    print(name, " ".join(f"{v:.2f}" for v in p))
