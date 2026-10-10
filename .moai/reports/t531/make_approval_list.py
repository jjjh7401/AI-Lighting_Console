"""전부-거절 승인 문면을 감독·리드용 목록으로 모은다 (카드 t531).

실행: uv run python .moai/reports/t531/make_approval_list.py
"""

import json
import re
from collections import Counter
from pathlib import Path

BASE = Path(".moai/reports/t531")
ITEMS = {
    1: "① 타임코드 트랙 6개",
    2: "② Goto 2번 이후·여러 시퀀스",
    3: "③ 프리셋 수정 전파",
    4: "④ 효과 프리셋 SM15·Measure",
    5: "⑤ 위치 프리셋 위 상대값",
    6: "⑥ 타임코드 중간 재생",
    7: "⑦ 선택 하나 + Step 2 (대조 큐 포함)",
    8: "⑧ 같은 그룹 두 시퀀스",
    9: "⑨ circle·발리후·wave",
}

body: list[str] = []
verbs: Counter[str] = Counter()
total_bundles = total_lines = 0
for n, title in ITEMS.items():
    requests = json.loads((BASE / f"denyall/p{n}/approvals.json").read_text("utf-8"))
    lines = sum(len(r["commands"]) for r in requests)
    total_bundles += len(requests)
    total_lines += lines
    body.append(f"## P{n} {title} — 묶음 {len(requests)} · 줄 {lines}")
    for i, request in enumerate(requests, 1):
        body.append(f"{i}. " + " / ".join(f"`{c}`" for c in request["commands"]))
        for command in request["commands"]:
            verbs[re.split(r"\s", command.strip(), maxsplit=1)[0]] += 1
    body.append("")
    print(f"P{n} 묶음 {len(requests)} 줄 {lines}")

head = [
    "# t531 M1 — 실기 승인 목록",
    "",
    "전부-거절(2026-10-10 15:26)에서 나온 승인 문면 그대로다. "
    "`--approve .moai/reports/t531/denyall/p<n>` 은",
    "이 문면과 **글자까지 같은** 묶음만 승인한다(t506 RecordingApproval).",
    "",
    f"합계: 묶음 {total_bundles} · 줄 {total_lines}",
    "",
    "첫 낱말별 줄 수: " + ", ".join(f"{v} {k}" for k, v in verbs.most_common()),
    "",
]
(BASE / "approval-list.md").write_text("\n".join(head + body), "utf-8")
print("합계", total_bundles, total_lines)
print("첫 낱말", verbs.most_common())
