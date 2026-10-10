"""t544 — s3 값 읽기를 프리셋별 표로 모아, 2.4·2.5 가 2.2·2.3·2.6 과 갈리는 필드를 찾는다. 콘솔 송신 없음.

실행: uv run python .moai/reports/t544/diff_values.py
"""

import json
from pathlib import Path

HERE = Path(".moai/reports/t544")
vals = {}
for line in (HERE / "s3_values.txt").read_text("utf-8").splitlines():
    if not line.startswith("<<< "):
        continue
    j = json.loads(line[4:])
    p = "2." + j["path"].split("/")[-1]
    for r in j.get("reads", []):
        vals.setdefault(r["n"], {})[p] = r.get("v") if r.get("ok") else f"!{r.get('err') or r.get('e') or 'fail'}"

order = [f"2.{i}" for i in range(1, 7)]
grown, control = ("2.4", "2.5"), ("2.2", "2.3", "2.6")
print("== fields where values differ among 2.1..2.6 ==")
for n, d in vals.items():
    row = [str(d.get(p)) for p in order]
    if len(set(row)) > 1:
        print(n, "|", " | ".join(f"{p}={v[:60]}" for p, v in zip(order, row)))
print("\n== fields that split grown(2.4,2.5) from control(2.2,2.3,2.6) ==")
for n, d in vals.items():
    g = {str(d.get(p)) for p in grown}
    c = {str(d.get(p)) for p in control}
    if not (g & c):
        print(n, "grown", g, "control", c)
fails = sorted({n for n, d in vals.items() if any(str(v).startswith("!") for v in d.values())})
print("\nread-failed fields:", len(fails), fails)
