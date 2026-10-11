"""t554 — REQ-LDBEAT-016..025 요구사항 칸에서 shall 없는 문장을 센다 (읽기 전용).

실행(워크트리 루트): python3 .moai/reports/t554/shall_sweep.py .moai/specs/SPEC-LDBEAT-001/spec.md
"""

import re
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    text = handle.read()

offenders = 0
for line in text.splitlines():
    m = re.match(r"^\| (REQ-LDBEAT-0(1[6-9]|2[0-5])) \| (.*)$", line)
    if not m:
        continue
    rest = m.group(3)
    # 요구사항 칸은 근거 칸(" | **(a)**" 로 시작) 앞까지다.
    cut = re.search(r" \| \*\*\(a\)\*\*", rest)
    req = rest[: cut.start()] if cut else rest.split(" | ")[0]
    for clause in re.split(r"\s\([a-z]'?\)\s", " " + req):
        for sent in re.split(r"(?<=다\.)\s+", clause.strip()):
            s = sent.strip()
            if len(s) < 8 or s == "[HARD]":
                continue
            if "shall" not in s:
                offenders += 1
                print(m.group(1), "::", s[:140])
print("OFFENDERS", offenders)
