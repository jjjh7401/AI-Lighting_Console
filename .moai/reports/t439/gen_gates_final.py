"""t439 — 8곡 13게이트 최종 실측 표 생성(server.concept.gates 경로)."""

import json
from collections import Counter

from server.concept.gates import GATE_NAMES, evaluate_song

songs = [
    s
    for s in json.load(open("server/tests/fixtures/pilot_baseline.json", encoding="utf-8"))
    if "error" not in s
]
res = {s["song"]: evaluate_song(s) for s in songs}
c: Counter[str] = Counter()
lines = [
    "# t439 — 13게이트 × 8곡 최종 실측",
    "",
    "명령: `uv run python .moai/reports/t439/gen_gates_final.py`",
    "",
    "| 게이트 | " + " | ".join(n[:12] for n in res) + " |",
    "|---|" + "---|" * len(res),
]
for g in GATE_NAMES:
    row = []
    for n in res:
        p = res[n][g].passed
        v = "PASS" if p else ("n/a" if p is None else "FAIL")
        c[v] += 1
        row.append(v)
    lines.append(f"| {g} | " + " | ".join(row) + " |")
lines += [
    "",
    f"집계: PASS {c['PASS']} · n/a {c['n/a']} · FAIL {c['FAIL']} (104칸)",
    "",
    "구 기준선 98 은 프로토타입 G6 식 반전(final_integrated.py:169 — REQ-029 면제 조건을"
    " 위반으로 셈)으로 과대, 정정값 90.",
    "",
    "## G6 세부(실제 위반)",
    "",
]
g6 = next(g for g in GATE_NAMES if g.startswith("G6"))
for n in res:
    lines.append(f"- {n}: {res[n][g6].detail}")
with open(".moai/reports/t439/gates_final.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(dict(c))
