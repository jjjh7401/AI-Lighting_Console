"""t546 — 잔차 컷의 근거를 실제 곡이 아닌 합성 박 목록에서 잰다.

두 갈래를 만든다.
  깨끗함: 등간격 박 + hop 512 양자화(44.1kHz, 11.6ms 격자) + 사람 연주 흔들림(σ 0~15ms)
  구조 오류: 박 하나를 빼거나(누락) 반 박 자리에 하나 넣어(삽입) 번호가 밀린 경우,
            위치를 곡의 5%~95%로 바꿔 가며
각 경우에 회귀 BPM 오차와 「잔차 표준편차 / 박 길이」를 낸다.
실행(워크트리 루트): uv run python .moai/reports/t546/cut_basis.py
"""

import numpy as np

HOP_S = 512 / 44100


def regression(beats):
    iv = np.diff(beats)
    med = np.median(iv)
    idx = np.concatenate([[0], np.cumsum(np.maximum(1, np.round(iv / med)))])
    slope, icpt = np.polyfit(idx, beats, 1)
    resid = beats - (slope * idx + icpt)
    return 60.0 / slope, float(np.std(resid) / slope), 60.0 / med


def grid(bpm, n, jitter_s, rng):
    t = np.arange(n) * 60.0 / bpm + 0.5 + rng.normal(0, jitter_s, n)
    return np.round(t / HOP_S) * HOP_S


rng = np.random.default_rng(0)
print("clean: bpm jitter_ms -> regr_err median_err resid/beat")
worst_clean = 0.0
for bpm in (60.0, 76.0, 100.0, 112.0, 128.5, 139.7, 160.0, 200.0):
    for jit in (0.0, 5.0, 10.0, 15.0):
        b = grid(bpm, 300, jit / 1000, rng)
        r, ratio, m = regression(b)
        worst_clean = max(worst_clean, ratio)
        print(f"  {bpm:6.1f} {jit:4.0f} -> {r - bpm:+7.3f} {m - bpm:+7.3f} {ratio:6.3f}")
print(f"worst clean resid/beat = {worst_clean:.3f}")

print("structural: kind bpm pos -> regr_err resid/beat")
best_struct = 1.0
for bpm in (76.0, 112.0, 160.0):
    for kind in ("drop", "insert"):
        for pos in (0.05, 0.25, 0.5, 0.75, 0.95):
            b = list(grid(bpm, 300, 0.005, rng))
            k = int(pos * len(b))
            if kind == "drop":
                del b[k]
            else:
                b.insert(k, (b[k - 1] + b[k]) / 2)
            r, ratio, _ = regression(np.asarray(b))
            # a dropped beat is re-numbered correctly by the rounding (interval ~2x);
            # an inserted half beat is the numbering slip that biases the slope.
            if abs(r - bpm) > 0.05:
                best_struct = min(best_struct, ratio)
            print(f"  {kind:6} {bpm:6.1f} {pos:4.2f} -> {r - bpm:+7.3f} {ratio:6.3f}")
print(f"smallest resid/beat among structural cases with |err|>0.05 = {best_struct:.3f}")
