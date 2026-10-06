"""t509 — 평론(izm) 서술을 잰 값으로 찾기 위한 마디별 질감 + 조(key) 추정.

실행: .venv/bin/python .moai/reports/t509/diag_texture.py "<LOVE ATTACK.mp3>" <phase1.json>

마디마다 잰다(위상 1 마디 경계 그대로):
- perc: 타악 성분 에너지(곡 중앙값=1) — 드럼이 얼마나 센가
- harm: 화성 성분 에너지(곡 중앙값=1)
- pshare: 타악 / (타악+화성) — 드럼 비중
- hi_harm: 화성 성분 중 2~8 kHz 비율 — 디스토션 기타처럼 고역 배음이 많은 소리의 대리값
- kick: 35~120 Hz 타악 에너지(곡 중앙값=1)
조 추정: 크로마 평균을 Krumhansl-Kessler 장·단조 프로필 24개와 상관해 가장 높은 것.
"""

import json
import sys
from pathlib import Path

import librosa
import numpy as np

sys.path.insert(0, ".moai/reports/t505")
from measure_music_map import HOP, N_FFT, band_energy, load_like_app  # noqa: E402

y, sr = load_like_app(sys.argv[1])
bars = json.loads(Path(sys.argv[2]).read_text())["bars"]
D = librosa.stft(y, n_fft=N_FFT, hop_length=HOP)
H, P = librosa.decompose.hpss(D)
Sh, Sp = np.abs(H) ** 2, np.abs(P) ** 2
f = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
pe, he = Sp.sum(0), Sh.sum(0) + 1e-12
hi = band_energy(Sh, f, (2000.0, 8000.0)) / he
kick = band_energy(Sp, f, (35.0, 120.0))
ft = librosa.frames_to_time(np.arange(Sp.shape[1]), sr=sr, hop_length=HOP)

rows = []
for b in bars:
    m = (ft >= b["start_s"]) & (ft < b["end_s"])
    rows.append((b["bar"], b["start_s"], pe[m].mean(), he[m].mean(), hi[m].mean(), kick[m].mean()))
med_p = float(np.median([r[2] for r in rows]))
med_h = float(np.median([r[3] for r in rows]))
med_k = float(np.median([r[5] for r in rows]))
print("bar start  perc  harm pshare hi_harm kick")
for n, t, p, h, hh, k in rows:
    share = p / (p + h)
    print(
        f"{n:3d} {t:6.2f} {p / med_p:5.2f} {h / med_h:5.2f} {share:6.3f} {hh:7.4f} {k / med_k:5.2f}"
    )
# 0~1.5초(첫 마디 앞) 도 따로 — 인트로 첫 소리
m = ft < bars[0]["start_s"]
print(
    f"pre  0.00 {pe[m].mean() / med_p:5.2f} {he[m].mean() / med_h:5.2f}"
    f" {pe[m].mean() / (pe[m].mean() + he[m].mean()):6.3f} {hi[m].mean():7.4f}"
    f" {kick[m].mean() / med_k:5.2f}"
)

# 조 추정 (Krumhansl-Kessler)
chroma = librosa.feature.chroma_cqt(y=librosa.istft(H, hop_length=HOP), sr=sr, hop_length=HOP)
c = chroma[:, ft[: chroma.shape[1]] < 179.0].mean(axis=1)
major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
scores = []
for i in range(12):
    scores.append((np.corrcoef(c, np.roll(major, i))[0, 1], f"{names[i]} major"))
    scores.append((np.corrcoef(c, np.roll(minor, i))[0, 1], f"{names[i]} minor"))
scores.sort(reverse=True)
print("key top3:", [(k, round(float(s), 3)) for s, k in scores[:3]])
