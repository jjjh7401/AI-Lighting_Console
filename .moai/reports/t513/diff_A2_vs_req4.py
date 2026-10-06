"""t513 — A2 요청(페이저 있음) 대 run3 요청 4(페이저 없음) 차이 전량 분류.

실행: uv run python .moai/reports/t513/diff_A2_vs_req4.py
"""

import difflib
import re
from pathlib import Path

D = Path(".moai/reports/t513")
old = (D / "run3_real_denyall/approval_request_4.txt").read_text("utf-8").splitlines()
new = (D / "run7_A2_denyall/approval_request_1.txt").read_text("utf-8").splitlines()
print(f"req4={len(old)} A2={len(new)}")
added, removed = [], []
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
    if tag in ("replace", "delete"):
        removed.extend(old[i1:i2])
    if tag in ("replace", "insert"):
        added.extend((j, new[j]) for j in range(j1, j2))
#: 페이저 호출 줄 = 새로 만든 세 프리셋(4.9·4.10·21.7)을 부르는 줄.
recall = re.compile(r"At Preset (4\.9|4\.10|21\.7)\b")
print("removed:", len(removed))
for x in removed:
    print("   -", x[:200])
kinds = {"phaser recall": 0, "OTHER": 0}
for j, x in added:
    k = "phaser recall" if recall.search(x) else "OTHER"
    kinds[k] += 1
    print(f"   + [{k}] line {j + 1}: {x[-120:]}")
print("added by kind:", kinds)
