"""t511 — LOVE ATTACK 구간별로 킥·스네어 후보가 마디의 어느 칸에 자주 오는가.

실행: python3 .moai/reports/t511/kick_slots.py

입력은 t509 음악 지도(위상 1, 감독 귀 확인 2026-10-06)의 마디별 후보 칸이다.
값 = 그 구간 마디 중 해당 칸에 후보가 있었던 마디의 비율(0~1).
대본의 "킥 박" 펄스 위치를 이 표로 정한다(약점 ② — 매 박 전체 펄스 금지).
"""

import collections
import json
from pathlib import Path

r = json.loads(Path(".moai/reports/t509/evidence/love_attack_map_phase1.json").read_text())
SECTIONS = [
    ("인트로 B 3~6", range(3, 7)),
    ("벌스 1 7~13", range(7, 14)),
    ("코러스 1 18~32", range(18, 33)),
    ("벌스 2 34~41", range(34, 42)),
    ("코러스 2 46~60", range(46, 61)),
    ("드롭 63~66", range(63, 67)),
    ("마지막 코러스 68~81", range(68, 82)),
]
SLOTS = ["1.1", "1.3", "2.1", "2.3", "3.1", "3.3", "4.1", "4.3"]
print("구간 | 마디 수 | 킥 후보 칸 비율 (" + " ".join(SLOTS) + ")")
for name, rng in SECTIONS:
    c = collections.Counter()
    for b in r["bars"]:
        if b["bar"] in rng:
            c.update(b["kick_grid"])
    n = len(rng)
    print(f"{name} | {n} | " + " ".join(f"{c[s] / n:.2f}" for s in SLOTS))
