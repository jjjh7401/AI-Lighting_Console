"""t566 — 바뀐 REQ/AC 행마다 옛 문장 중 새 파일 어디에도 없는 것을 센다.

「옛 REQ/AC 삭제 0」은 조항 표지만이 아니라 옛 문면이 남았는지(대체됨 표기와 함께)
까지 본다. 새 파일 **전체**(HISTORY 행 포함)에서 찾으므로, 옛 문장을 HISTORY 에
인용해 보존한 경우도 남은 것으로 센다.

실행: python3 .moai/reports/t566/dropped_text_check.py <옛 파일 폴더>
"""

import re
import sys

OLD_DIR = sys.argv[1]
SPEC = ".moai/specs/SPEC-LDBEAT-001"
ROW = re.compile(r"^\| ((?:REQ|AC)-LDBEAT-\d+) ")
SPLIT = re.compile(r"(?<=[.。])\s+|\s+—\s+|\s*\|\s*")

for name in ("spec.md", "acceptance.md"):
    old = open(f"{OLD_DIR}/old-{name}", encoding="utf-8").read().splitlines()
    new_text = open(f"{SPEC}/{name}", encoding="utf-8").read()
    new = new_text.splitlines()
    o = {m.group(1): line for line in old if (m := ROW.match(line))}
    n = {m.group(1): line for line in new if (m := ROW.match(line))}
    total = 0
    for key, line in o.items():
        if line == n.get(key):
            continue
        pieces = [p.strip() for p in SPLIT.split(line) if len(p.strip()) >= 25]
        dropped = [p for p in pieces if p not in new_text]
        total += len(dropped)
        print(f"{name} {key}: {len(pieces)} 문장 중 사라짐 {len(dropped)}")
        for p in dropped:
            print("    -", p[:200])
    print(f"{name} 합계 사라진 문장: {total}")
