import sys

import librosa
import numpy as np

sys.path.insert(0, ".moai/reports/t505")
from measure_music_map import (  # noqa: E402
    HOP,
    N_FFT,
    band_energy,
    load_like_app,
    onset_env_from,
    pick_onsets,
)

y, sr = load_like_app(sys.argv[1])
D = librosa.stft(y, n_fft=N_FFT, hop_length=HOP)
H, P = librosa.decompose.hpss(D)
Sp = np.abs(P) ** 2
f = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
low = pick_onsets(onset_env_from(band_energy(Sp, f, (35, 120))), sr, 0.5)
hi = pick_onsets(onset_env_from(band_energy(Sp, f, (1500, 5000))), sr, 0.5)
allp = pick_onsets(onset_env_from(Sp.sum(0)), sr, 0.5)
for sb in (139.67, 93.96, 69.84):
    tempo, bt = librosa.beat.beat_track(
        y=y, sr=sr, hop_length=HOP, start_bpm=sb, tightness=400, units="time"
    )
    per = np.median(np.diff(bt))

    def onb(ts, bt=bt, per=per):
        return np.mean([abs((t - bt[np.argmin(abs(bt - t))]) / per) < 0.1 for t in ts])

    print(
        f"start {sb:6.2f} -> bpm {60 / per:6.2f} beats {len(bt)} | onbeat(±0.1 beat, chance 0.20)"
        f" low={onb(low):.2f} hi={onb(hi):.2f} perc={onb(allp):.2f}"
    )
