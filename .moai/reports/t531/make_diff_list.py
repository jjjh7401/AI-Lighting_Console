"""그룹 교체 v2 승인 문면을 v1 과 줄 단위로 대조한다 (카드 t531).

v1 = .moai/reports/t531/denyall_v1/p<n>/approvals.json (감독 1차 승인 문면)
v2 = .moai/reports/t531/denyall/p<n>/approvals.json (그룹 교체 뒤 전부-거절)

실행: uv run python .moai/reports/t531/make_diff_list.py
"""

import json
from pathlib import Path

BASE = Path(".moai/reports/t531")
PROBES = [3, 4, 5, 7, 8, 9]

out = [
    "# t531 M1 v2 — 그룹 교체 승인 대조 (이전 줄 → 새 줄)",
    "",
    "v1 = 감독 1차 승인 문면(`denyall_v1/`), v2 = 그룹 교체 뒤 실기 전부-거절 문면(`denyall/`).",
    "바뀐 줄만 적는다. 묶음 수나 묶음 안 줄 수가 다르면 🔴 로 적는다 — 이번 대조에서 0건.",
    "",
]
total_changed = 0
for n in PROBES:
    v1 = json.loads((BASE / f"denyall_v1/p{n}/approvals.json").read_text("utf-8"))
    v2 = json.loads((BASE / f"denyall/p{n}/approvals.json").read_text("utf-8"))
    lines2 = sum(len(r["commands"]) for r in v2)
    out.append(f"## P{n} — 묶음 {len(v1)} → {len(v2)} · 줄 {lines2}")
    if len(v1) != len(v2):
        out.append("🔴 묶음 수가 다르다")
    changed = 0
    for b, (r1, r2) in enumerate(zip(v1, v2, strict=False), 1):
        c1, c2 = r1["commands"], r2["commands"]
        if len(c1) != len(c2):
            out.append(f"- 묶음 {b}: 🔴 줄 수 {len(c1)} → {len(c2)}")
        for i, (a, z) in enumerate(zip(c1, c2, strict=False), 1):
            if a != z:
                changed += 1
                out.append(f"- 묶음 {b} 줄 {i}: `{a}` → `{z}`")
    if changed == 0:
        out.append("- 바뀐 줄 없음")
    total_changed += changed
    out.append("")
    print(f"P{n} 바뀐 줄 {changed}")
out.insert(4, f"바뀐 줄 합계: {total_changed}\n")
(BASE / "approval-diff-v2.md").write_text("\n".join(out), "utf-8")
print("합계", total_changed)
