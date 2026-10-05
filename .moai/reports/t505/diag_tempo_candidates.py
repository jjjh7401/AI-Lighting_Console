import sys

import librosa
import numpy as np

sys.path.insert(0, ".moai/reports/t505")
from measure_music_map import (  # noqa: E402
    HOP,
    load_like_app,
)

y, sr = load_like_app(sys.argv[1])
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
ac = librosa.autocorrelate(oenv, max_size=600)
ac /= ac[0]
bpms = 60 * sr / HOP / np.arange(1, 600)
peaks = librosa.util.peak_pick(
    ac[1:], pre_max=3, post_max=3, pre_avg=3, post_avg=3, delta=0.01, wait=3
)
cand = [(bpms[p], ac[1:][p]) for p in peaks if 50 < bpms[p] < 300]
for b, v in sorted(cand, key=lambda x: -x[1])[:8]:
    print(f"{b:7.2f} {v:.3f}")
