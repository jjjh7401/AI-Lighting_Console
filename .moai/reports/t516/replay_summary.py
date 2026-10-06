"""t516 다시 보기 실행 결과 요약 + 금지 동사 검사(쓰기 0줄 확인).

실행: uv run python .moai/reports/t516/replay_summary.py <실행 폴더>
"""

import json
import re
import sys
from pathlib import Path

FORBIDDEN = re.compile(r"^(Store|Set|Assign|Delete|ClearAll|Save|Copy|Move|Label|Edit)\b")

out = Path(sys.argv[1])
r = json.loads((out / "result.json").read_text("utf-8"))
reqs = r["approval_requests"]
lines = [c for q in reqs for c in q["commands"]]
print("verdict", r["verdict"])
print("bundles", len(r["bundles"]), "all ok", all(r["bundles"].values()))
print("requests", len(reqs), "approved", sum(q["approved"] for q in reqs), "lines", len(lines))
print("forbidden verbs", [c for c in lines if FORBIDDEN.match(c)])
print("verbs", sorted({" ".join(c.split()[:2]) for c in lines}))
print("saveshow", len(r["skipped_saveshow"]))
if "fake_sent" in r:
    print("fake sent", len(r["fake_sent"]))
