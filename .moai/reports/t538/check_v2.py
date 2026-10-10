"""v2 대조: A0′ 몸통 = T4(t4_prog), A6·B = v1 과 번호만 다름.

실행: uv run python .moai/reports/t538/check_v2.py
"""

import json
import re
from pathlib import Path


def _planned(d: str) -> dict:
    text = Path(f".moai/reports/t538/{d}/result.json").read_text("utf-8")
    return json.loads(text)["planned"]


v2 = _planned("v2_rehearse")
v1 = _planned("rehearse")
t45 = _planned("t45_rehearse")

body = v2["store_A0"][:-3]  # Store / ClearAll / Set Name 3줄 제외
print("A0' body == T4:", body == t45["t4_prog"], len(body))

old_to_new = {
    311: 312,
    312: 313,
    313: 314,
    314: 315,
    315: 316,
    316: 317,
    317: 318,
    318: 319,
    319: 320,
    320: 321,
    321: 322,
}


def renum(line: str) -> str:
    return re.sub(
        r"\b(3[12]\d)\b", lambda m: str(old_to_new.get(int(m.group(1)), m.group(1))), line
    )


for key in [k for k in v1 if k.endswith(("A6a", "A6b")) or "B" in k]:
    same = [renum(x) for x in v1[key]] == v2.get(key)
    print(key, "same-but-number:", same)
