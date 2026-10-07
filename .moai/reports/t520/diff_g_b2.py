"""t520 — B 그룹판(253·254·TC23)과 B2(269·270·TC24)가 번호·이름 말고 어디가 다른지(콘솔 0).

실행: uv run python .moai/reports/t520/diff_g_b2.py <g plan.json> <b2 plan.json>
"""

import difflib
import json
import re
import sys
from pathlib import Path


def lines(path: str) -> list[str]:
    return [c for _, cmds in json.loads(Path(path).read_text("utf-8")) for c in cmds]


def norm(line: str) -> str:
    line = re.sub(r"\bSequence 253\b", "Sequence 269", line)
    line = re.sub(r"\bSequence 254\b", "Sequence 270", line)
    line = re.sub(r"\bTimecode 23\b", "Timecode 24", line)
    return line.replace("RHYTHM M2a B ", "RHYTHM M2a B2 ")


g = [norm(x) for x in lines(sys.argv[1])]
b2 = lines(sys.argv[2])
print("lines", len(g), len(b2))
diff = [
    d
    for d in difflib.unified_diff(g, b2, lineterm="", n=0)
    if d[:1] in "+-" and d[:3] not in ("+++", "---")
]
print("changed lines", len(diff))
print("\n".join(diff))
