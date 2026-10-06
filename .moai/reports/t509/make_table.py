"""love_attack_map_phase1.json → 마디별 표(MD) + 순간 목록.

t509 — t505 make_table.py 를 K-pop 용으로 넓힌 것.
실행: python3 .moai/reports/t509/make_table.py <evidence/love_attack_map_phase1.json>

순간 규칙(판정서 §2 와 같다 — 모두 잰 값에 씌운 [추정] 규칙):
- 큰 히트: 마디 평균 저역 타악 에너지 ≥ 곡 중앙값의 2.5배
- 브레이크: 음량 < 직전 두 마디 평균의 85%, 또는 저역 에너지 < 곡 중앙값의 35%(킥이 빠짐)
- 상승 진입: 음량 ≥ 직전 두 마디 평균의 115%
- 빌드업: 큰 히트 직전까지 음량이 3마디 이상 연달아 오르는 구간
"""

import json
import sys
from pathlib import Path

r = json.loads(Path(sys.argv[1]).read_text())
bars = r["bars"]
rms_med = sorted(b["rms"] for b in bars)[len(bars) // 2]
ke_med = sorted(b["kick_energy"] for b in bars)[len(bars) // 2]

tags: list[list[str]] = [[] for _ in bars]
for k, b in enumerate(bars):
    if b["kick_energy"] >= 2.5 * ke_med:
        tags[k].append(f"큰 히트(저역 {b['kick_energy'] / ke_med:.1f}배)")
    if k >= 2:
        prev = (bars[k - 1]["rms"] + bars[k - 2]["rms"]) / 2
        if b["rms"] < 0.85 * prev:
            tags[k].append(f"브레이크(음량 {b['rms'] / prev:.0%})")
        elif b["rms"] >= 1.15 * prev:
            tags[k].append(f"상승 진입(음량 {b['rms'] / prev:.0%})")
    if b["kick_energy"] < 0.35 * ke_med:
        tags[k].append(f"킥 빠짐(저역 {b['kick_energy'] / ke_med:.2f}배)")
# 빌드업: 큰 히트 마디 h 앞에서 음량이 연달아 오르는 마디들
for h in range(len(bars)):
    if not any(t.startswith("큰 히트") for t in tags[h]):
        continue
    j = h - 1
    while j > 0 and bars[j]["rms"] > bars[j - 1]["rms"]:
        j -= 1
    run = list(range(j, h))
    if len(run) >= 3:
        for q in run:
            tags[q].append("빌드업")

seen = set()
rows, moments = [], []
for k, b in enumerate(bars):
    first = b["section_i"] not in seen
    seen.add(b["section_i"])
    m = list(tags[k])
    if first:
        m.append(f"앱 구간 시작: {b['section']}")
    rows.append(
        [
            str(b["bar"]),
            f"{b['start_s']:.2f}",
            b["section"],
            " ".join(b["kick_grid"]) or "-",
            " ".join(b["snare_grid"]) or "-",
            f"{b['rms'] / rms_med:.2f}",
            f"{b['kick_energy'] / ke_med:.2f}",
            f"{b['vocal_ratio']:.3f}",
            " · ".join(m),
        ]
    )
    if tags[k]:
        moments.append((b["bar"], b["start_s"], b["section"], tags[k]))

print(
    "| 마디 | 다운비트(초) | 구간(앱) | 킥 후보 칸 [추정] | 스네어·클랩 후보 칸 [추정]"
    " | 음량(중앙값=1) | 저역(중앙값=1) | 보컬 대역 비율(참고) | 순간 |"
)
print("|" + "---|" * 9)
for row in rows:
    print("| " + " | ".join(row) + " |")
print()
print("MOMENTS")
for bar, t, sec, m in moments:
    print(bar, t, sec, m)
print("MEDIANS rms", round(rms_med, 4), "kick", round(ke_med, 1))
