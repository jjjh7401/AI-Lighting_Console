"""v3 대조. 실행: uv run python .moai/reports/t538/check_v3.py"""

import difflib
import json
from pathlib import Path


def load(d: str) -> dict:
    text = Path(f".moai/reports/t538/{d}/result.json").read_text("utf-8")
    return json.loads(text)["planned"]


v3, v2, t45 = load("v3_rehearse"), load("v2_rehearse"), load("t45_rehearse")

v2_same = all(v3.get(k) == cmds for k, cmds in v2.items())
print("v2 bundles carried unchanged:", v2_same, f"({len(v2)} bundles)")
extra = [k for k in v3 if k not in v2]
print("added bundles:", extra)


def delta(a, b):
    return [x for x in difflib.ndiff(a, b) if x[:1] in "+-"]


print("T4s vs T4:", delta(t45["t4_prog"], v3["t4s_prog"]))
print("T5s vs T5:", delta(t45["t5_prog"], v3["t5s_prog"]))
print("A5b vs A5:", delta(v3["store_A5"], v3["store_A5b"]))
