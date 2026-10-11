"""t566 — 옛 REQ/AC 행의 조항 표지가 새 행에 전부 남았는지, 표 밖에서 지워진 줄이 무엇인지.

실행: python3 .moai/reports/t566/clause_check.py <옛 spec.md·acceptance.md 가 든 폴더>
(옛 파일은 `git show HEAD:.moai/specs/SPEC-LDBEAT-001/<name>` 로 뽑아 old-<name> 으로 둔다)
"""

import difflib
import re
import sys
from pathlib import Path

OLD_DIR = sys.argv[1]
SPEC = ".moai/specs/SPEC-LDBEAT-001"
LAB = re.compile(r"\(([a-z](?:-\d+[a-z]?)?)\)")
ROW = re.compile(r"^\| ((?:REQ|AC)-LDBEAT-\d+) ")

for name in ("spec.md", "acceptance.md"):
    old = Path(f"{OLD_DIR}/old-{name}").read_text(encoding="utf-8").splitlines()
    new = Path(f"{SPEC}/{name}").read_text(encoding="utf-8").splitlines()
    o = {m.group(1): line for line in old if (m := ROW.match(line))}
    n = {m.group(1): line for line in new if (m := ROW.match(line))}
    for key, line in o.items():
        if line != n.get(key):
            lo, ln = set(LAB.findall(line)), set(LAB.findall(n.get(key, "")))
            print(
                name,
                key,
                "chars",
                len(line),
                "->",
                len(n.get(key, "")),
                "missing:",
                sorted(lo - ln) or "none",
                "added:",
                sorted(ln - lo),
            )
    removed = [
        x for x in difflib.ndiff(old, new) if x.startswith("- ") and not x.startswith("- | ")
    ]
    print(name, "non-table removed lines:", len(removed))
    for r in removed:
        print("   ", r[:160])
