"""왜 실제 곡의 D등급이 전부 4~5 인가 — 구간 RMS 비율을 직접 재서 확증한다."""

from pathlib import Path

import numpy as np

from server.audio.analyze import _D_LEVEL_BANDS, _HOP_LENGTH, _MIN_SEGMENT_SECONDS, analyze

path = Path("src/걸그룹DinoDino_C_max최고품질.wav")
out = analyze(path.read_bytes())
cands = out.d_candidates

import librosa  # noqa: E402

y, sr = librosa.load(str(path), sr=22050, mono=True)
rms = librosa.feature.rms(y=y, hop_length=_HOP_LENGTH)[0]
times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=_HOP_LENGTH)

print(f"등급 띠: {_D_LEVEL_BANDS} · 최소 구간 길이 {_MIN_SEGMENT_SECONDS}s")
print(f"곡 길이 {len(y) / sr:.1f}s · RMS 프레임 {len(rms)}\n")

vals = []
for c in cands:
    m = (times >= c.start_ms / 1000) & (times < c.end_ms / 1000)
    vals.append(float(rms[m].mean()) if m.any() else 0.0)
top = max(vals)
print(f"{'구간':>3} {'길이':>6} {'평균RMS':>9} {'최대대비':>7}  D  최소길이")
short = 0
for c, v in zip(cands, vals, strict=True):
    dur = (c.end_ms - c.start_ms) / 1000
    flag = "🔴짧다" if dur < _MIN_SEGMENT_SECONDS else ""
    if dur < _MIN_SEGMENT_SECONDS:
        short += 1
    print(f"{c.start_ms // 1000:>3}s {dur:>5.1f}s {v:>9.4f} {v / top:>7.3f}  D{c.d_level}  {flag}")
print(f"\n최소 길이({_MIN_SEGMENT_SECONDS}s) 미달 구간: {short}개")
ratios = [v / top for v in vals]
print(f"최대대비 비율 범위: {min(ratios):.3f} ~ {max(ratios):.3f}")
print(f"0.80 이상(→D5): {sum(1 for r in ratios if r > 0.80)}개 / {len(ratios)}")
