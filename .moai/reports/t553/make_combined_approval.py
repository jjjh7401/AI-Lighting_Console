"""두 전부-거절 승인 문면(8트랙 재측정 + MOVER-U 기운 기준 Pan)을 승인 목록
하나로 합친다 (카드 t553 Part ②). 리드 지시 — "same approval list".

실행: uv run python .moai/reports/t553/make_combined_approval.py
"""

import hashlib
import json
from pathlib import Path

BASE = Path(".moai/reports/t553")
BATCHES = [
    ("P1b — 8트랙 타임코드 재측정 (TC 32, 시퀀스 226~233 참조)", BASE / "denyall_8track"),
    ("추가 — MOVER-U(Group 11) 기운 기준 Pan 물결 재시험 (시퀀스 336, 새)", BASE / "denyall_u_pan"),
]

lines: list[str] = []
body: list[str] = []
total_bundles = total_lines = 0
for title, directory in BATCHES:
    requests = json.loads((directory / "approvals.json").read_text("utf-8"))
    batch_lines = sum(len(r["commands"]) for r in requests)
    total_bundles += len(requests)
    total_lines += batch_lines
    body.append(f"## {title} — 묶음 {len(requests)} · 줄 {batch_lines}")
    for i, request in enumerate(requests, 1):
        body.append(f"{i}. " + " / ".join(f"`{c}`" for c in request["commands"]))
        lines.extend(request["commands"])
    body.append("")

approval_text = "".join(c + "\n" for c in lines)
(BASE / "approval_t553.txt").write_text(approval_text, "utf-8")
digest = hashlib.sha256(approval_text.encode()).hexdigest()

head = [
    "# t553 Part ② — 실기 승인 목록 (8트랙 재측정 + MOVER-U 기운 기준 Pan)",
    "",
    "두 전부-거절(2026-10-11)에서 나온 승인 문면 그대로다. "
    "`--approve .moai/reports/t553/denyall_8track`(P1b)와 "
    "`--approve .moai/reports/t553/denyall_u_pan`(추가 묶음)은 "
    "각각의 문면과 **글자까지 같은** 묶음만 승인한다(t506 RecordingApproval).",
    "",
    f"합계: 묶음 {total_bundles} · 줄 {total_lines}",
    f"approval_t553.txt sha256: {digest}",
    f"approval_t553.txt 줄 수: {len(lines)}",
    "",
]
(BASE / "approval-list.md").write_text("\n".join(head + body), "utf-8")
print(json.dumps(dict(bundles=total_bundles, lines=total_lines, sha256=digest), indent=2))
