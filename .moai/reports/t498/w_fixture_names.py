"""t498 — W 채널 줄의 28기구에 이름·기종을 붙인다(읽기 전용 판독 run4 결과를 해석만 한다).

실행: uv run python .moai/reports/t498/w_fixture_names.py
"""

import json
import re
from collections import Counter
from pathlib import Path

REPORT = Path(".moai/reports/t498")
text = (REPORT / "run4_fixture_names.txt").read_text("utf-8")
rows = {}
for m in re.finditer(r"<<< (\{.*\})", text):
    d = json.loads(m.group(1))
    vals = {r["n"]: r.get("v") for r in d.get("reads", []) if r.get("ok")}
    if "FID" in vals:
        rows[int(vals["FID"])] = (vals.get("Name"), vals.get("FixtureType"), vals.get("Mode"))
print("fixtures read:", len(rows))

diff_text = (REPORT / "run3_classify_diff.txt").read_text("utf-8")
ids = json.loads(re.search(r"W fixture set used 12x: count=28 ids=(\[.*\])", diff_text).group(1))
missing = [i for i in ids if i not in rows]
print("W ids:", len(ids), "missing from read:", missing)
kinds = Counter(rows[i][1] for i in ids if i in rows)
print("W fixture types:", dict(kinds))
for i in ids:
    print(i, rows.get(i))
others = Counter(v[1] for k, v in rows.items() if k not in ids)
print("non-W fixture types:", dict(others))
