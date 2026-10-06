"""t516 — probe_readonly 출력 파일을 사람이 읽기 좋게 요약한다(state 자식·props 값·introspect 필드).

실행: uv run python .moai/reports/t516/show_reads.py <출력 파일>
"""

import json
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text("utf-8")
for block in text.split(">>> ")[1:]:
    head = block.split("\n")[0]
    m = re.search(r"<<< (.*)", block)
    try:
        d = json.loads(m.group(1)) if m else {}
    except json.JSONDecodeError:
        print(head, "| (unparsed)", (m.group(1) if m else block)[:160])
        continue
    if not d.get("ok", True) and "error" in d:
        print(head, "| ERROR", d["error"][:140])
    elif "children" in d:
        kids = [(c.get("i"), c.get("class"), c.get("name")) for c in d["children"]]
        print(head, "| node", d.get("node"), "| kids", kids)
    elif "reads" in d:
        print(head, "|", [(r["n"], r.get("v"), r.get("e")) for r in d["reads"]])
    elif "fields" in d:
        print(head, "| fields", [f["n"] for f in d["fields"]], "trunc", d.get("truncated"))
    else:
        print(head, "|", str(d)[:160])
