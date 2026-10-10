"""v3 재승인 묶음 하나로 — ③⑤⑨ 「이전 → 새」 + ⑩⑪ 전문 (카드 t531).

입력은 전부 실기 전부-거절 승인 문면(`denyall/p<n>/approvals.json`)이다.
실행: uv run python .moai/reports/t531/make_v3_package.py
"""

import json
from pathlib import Path

BASE = Path(".moai/reports/t531")
DIFF_ITEMS = {3: "③ 프리셋 수정 전파", 5: "⑤ 위치 프리셋 위 상대값", 9: "⑨ circle·발리후·wave"}
NEW_ITEMS = {
    10: (
        "⑩ 디머 번갈아 — 위상 펼침 (새 시퀀스 309)",
        "감독 눈: MOVER-U 가 다 같이 / 물결 / 한 대씩 번갈아 중 무엇인가",
        "⑦ 큐1 과 다른 줄은 `Attribute 'Dimmer' At Phase 0 Thru 180` 하나. 문법 근거: "
        "`0 Thru 360` 은 t227 에서 콘솔이 받음(`t227/verdict.md:98`). "
        "🔴 끝값 180 과 눈 결과는 미측정.",
    ),
    11: (
        "⑪ t520 실패 재현 — Step 2 한 번 뒤 선택 바꾸기 (새 시퀀스 310)",
        "감독 눈: MOVER-U 와 바닥 워시가 둘 다 깜빡이나",
        "⑦ 큐2 와 다른 것은 `Step 2` 위치 하나(t520 승인 문면 "
        "`approval_m2a_batch1_v2.txt:178-209` 꼴). 그룹·속성·값은 같다.",
    ),
}


def load(folder: str, n: int) -> list[list[str]]:
    rows = json.loads((BASE / f"{folder}/p{n}/approvals.json").read_text("utf-8"))
    return [r["commands"] for r in rows]


out = [
    "# t531 M1 v3 재승인 묶음",
    "",
    "전부 실기 전부-거절(쓰기 0)에서 나온 승인 문면 그대로다. 이 문면과 **글자까지 같은**"
    " 묶음만 실행된다.",
    "",
]
total_changed = total_new = 0
out += ["## 1. 수정 — 이전 → 새", ""]
for n, title in DIFF_ITEMS.items():
    old, new = load("denyall_v2", n), load("denyall", n)
    lines = sum(len(b) for b in new)
    out.append(f"### {title} — 묶음 {len(new)} · 줄 {lines}")
    if len(old) != len(new):
        out.append("🔴 묶음 수가 다르다")
    for b, (c1, c2) in enumerate(zip(old, new, strict=False), 1):
        if len(c1) != len(c2):
            out.append(f"- 묶음 {b}: 🔴 줄 수 {len(c1)} → {len(c2)}")
        for i, (a, z) in enumerate(zip(c1, c2, strict=False), 1):
            if a != z:
                total_changed += 1
                out.append(f"- 묶음 {b} 줄 {i}: `{a}` → `{z}`")
    out.append("")
out += ["## 2. 추가 — 전문", ""]
for n, (title, eye, note) in NEW_ITEMS.items():
    new = load("denyall", n)
    lines = sum(len(b) for b in new)
    total_new += lines
    out += [f"### {title} — 묶음 {len(new)} · 줄 {lines}", "", f"- {eye}", f"- {note}", ""]
    for b, cmds in enumerate(new, 1):
        out.append(f"{b}. " + " / ".join(f"`{c}`" for c in cmds))
    out.append("")
out.insert(4, f"합계: 수정 줄 {total_changed} · 추가 줄 {total_new}\n")
(BASE / "approval-v3-package.md").write_text("\n".join(out), "utf-8")
print("수정", total_changed, "추가", total_new)
