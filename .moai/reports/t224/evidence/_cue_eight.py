import json
import re
from pathlib import Path

EIGHT = ["Q010", "Q020", "Q040", "Q050", "Q080", "Q090", "Q110", "Q130"]
path = ".moai/reports/t224/evidence/cues_preview_after_join_fix.json"
d = json.loads(Path(path).read_text(encoding="utf-8"))
p = d["tool"]["payload"] if "payload" in d["tool"] else d["tool"]
detail = p.get("refusal_detail") or ""

# 사유 문자열을 큐 단위로 가른다. `Q010 / BACK: ...; Q020 / KEY: ...` 형태.
blockers = dict()
for chunk in detail.split(";"):
    head = re.search(r"(Q\d+) / ([A-Z\-]+):", chunk)
    if not head:
        continue
    cue = head.group(1)
    ids = re.findall(r"프리셋 ((?:POS|COL|BM|FX|DIM)\.\d+)", chunk)
    blockers.setdefault(cue, set()).update(ids)

held_cues = set(h["cue_no"] for h in p["held"])
print("여덟 개 포지션 큐 — 조인 수리 후")
print()
for q in EIGHT:
    if q in held_cues:
        print(f"  {q}  보류 — 남은 미해결: {sorted(blockers.get(q, []))}")
    else:
        print(f"  {q}  전 행 해결")
print()
print("전 행 해결:", len([q for q in EIGHT if q not in held_cues]), "/ 8")
print(
    "실제 planned_cues:",
    p["planned_cues"],
    "  (§11.1 부분집합 금지 — 한 행이라도 보류면 배치 전체 거절)",
)
