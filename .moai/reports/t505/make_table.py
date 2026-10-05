"""clubdiver_map_phase0.json → 마디별 표(MD) + 순간 목록. 순간 규칙은 판정서 §2 에 적은 그대로."""

import json
import sys
from pathlib import Path

r = json.loads(Path(sys.argv[1]).read_text())
bars = r["bars"]
ref = sorted(b["rms"] for b in bars[2:82])
med = ref[len(ref) // 2]
rows, moments = [], []
for k, b in enumerate(bars):
    m = []
    if k == 2:
        m.append("비트 진입")
    if k >= 2:
        prev = (bars[k - 1]["rms"] + bars[k - 2]["rms"]) / 2
        if b["rms"] < 0.85 * prev and k != len(bars) - 1:
            depth = "깊음" if b["rms"] < 0.7 * prev else "얕음"
            m.append(f"브레이크({depth}, {b['rms'] / prev:.0%})")
    if k >= 1 and k + 1 < len(bars) and any("브레이크" in x for x in rows[-1][-1:]):
        pass
    if k >= 1 and rows and "브레이크" in rows[-1][8]:
        m.append("재진입")
    if k == len(bars) - 1:
        m.append("끝(소리 빠짐)")
    if b["section_first_bar"]:
        m.append(f"앱 구간 시작: {b['section']}")
    rel = b["rms"] / med
    row = [
        str(b["bar"]),
        f"{b['start_s']:.2f}",
        b["section"],
        f"{b['start_s']:.3f}",
        " ".join(b["kick_grid"]) or "-",
        " ".join(b["snare_grid"]) or "-",
        f"{rel:.2f}",
        f"{b['vocal_ratio']:.3f}",
        " · ".join(m),
    ]
    rows.append(row)
    if any(x for x in m if not x.startswith("앱 구간")):
        moments.append((b["bar"], b["start_s"], [x for x in m if not x.startswith("앱 구간")]))
hdr = (
    "| 마디 | 시각(초) | 구간(앱) | 다운비트(초) | 킥 후보 칸 [추정] | 스네어·클랩 후보 칸 [추정]"
    " | 음량(중앙값=1) | 보컬 대역 비율(참고) | 순간 |"
)
sep = "|" + "---|" * 9
print(hdr)
print(sep)
for row in rows:
    print("| " + " | ".join(row) + " |")
print()
print("MOMENTS")
for bar, t, m in moments:
    print(bar, t, m)
print("MEDIAN_RMS", med)
