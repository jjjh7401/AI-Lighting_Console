"""t520 — print-plan 결과(plan.json)의 줄 수·점 번호 목록 줄·최대 목록 길이·sha256 을 센다.

실행: uv run python .moai/reports/t520/plan_stats.py <plan.json> [대조할 승인 파일]
"""

import hashlib
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text("utf-8"))
lines = [c for _, cmds in plan for c in cmds]
text = "".join(f"{c}\n" for c in lines)
sels = [c.split(";")[0] for c in lines if c.startswith("Fixture ")]
dot_in_list = [s for s in sels if "+" in s and "." in s]
print("bundles", {label: len(cmds) for label, cmds in plan})
print("total", len(lines), "sha256", hashlib.sha256(text.encode()).hexdigest())
print("dot-in-list lines", len(dot_in_list), "max list", max(len(s.split("+")) for s in sels))
print("names", [c for c in lines if "'Name'" in c])
if len(sys.argv) > 2:
    print("equals", sys.argv[2], text == Path(sys.argv[2]).read_text("utf-8"))
