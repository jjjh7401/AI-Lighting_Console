"""t509 — 저역 타악 에너지가 가장 큰 순간(큰 히트)이 박 격자의 어느 위상에 놓이는가.

실행: .venv/bin/python .moai/reports/t509/diag_big_hits.py "<LOVE ATTACK.mp3>"

다운비트 근거 하나를 더 잰다: 후렴 진입 같은 큰 히트는 마디 1박에 오는 경우가 많다.
타악 성분 35~120 Hz 에너지의 로그 증가량에서 가장 큰 봉우리 8개를 골라, 가장 가까운
앱 박 번호의 위상(박 번호 % 4)과 박 길이 대비 어긋남을 적는다.
"""

import sys

import librosa
import numpy as np

sys.path.insert(0, ".moai/reports/t505")
from measure_music_map import (  # noqa: E402
    HOP,
    N_FFT,
    app_beats,
    band_energy,
    load_like_app,
    onset_env_from,
)

y, sr = load_like_app(sys.argv[1])
beats, bpm, _ = app_beats(y, sr)
per = 60.0 / bpm
_, P = librosa.decompose.hpss(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
Sp = np.abs(P) ** 2
f = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
env = onset_env_from(band_energy(Sp, f, (35.0, 120.0)))
peaks = librosa.util.peak_pick(
    env, pre_max=20, post_max=20, pre_avg=20, post_avg=20, delta=0.0, wait=40
)
top = peaks[np.argsort(env[peaks])[::-1][:8]]
print(f"bpm {bpm:.2f} beats {len(beats)} median_env {np.median(env[peaks]):.3f}")
for p in sorted(top):
    t = librosa.frames_to_time(p, sr=sr, hop_length=HOP)
    k = int(np.argmin(np.abs(beats - t)))
    off = (t - beats[k]) / per
    print(f"t {t:7.3f}  strength {env[p]:.3f}  beat#{k} phase {k % 4}  off {off:+.2f}")

# (2) 원 에너지(증가량이 아니라 크기) — 마디 평균 저역 에너지가 평소의 3~4배였던 세 자리
# (t509 마디표 18·46·68마디, 위상 1 기준 37.90·97.93·145.08초) 근처 ±2박에서 저역 에너지가
# 처음 치솟는 프레임(최대값의 50% 를 처음 넘는 프레임)이 어느 박에 놓이는가.
energy = band_energy(Sp, f, (35.0, 120.0))
frame_t = librosa.frames_to_time(np.arange(len(energy)), sr=sr, hop_length=HOP)
med_e = float(np.median(energy))
print(f"raw kick-band energy median {med_e:.1f}")
for t0 in (37.90, 97.93, 145.08):
    idx = np.where((frame_t > t0 - 2 * per) & (frame_t < t0 + 2 * per))[0]
    peak = idx[np.argmax(energy[idx])]
    rise = idx[np.argmax(energy[idx] >= 0.5 * energy[peak])]
    for label, fr in (("rise", rise), ("peak", peak)):
        t = frame_t[fr]
        k = int(np.argmin(np.abs(beats - t)))
        print(
            f"near {t0:6.2f} {label} t {t:7.3f} energy/median {energy[fr] / med_e:5.1f}x"
            f"  beat#{k} phase {k % 4}  off {(t - beats[k]) / per:+.2f}"
        )
