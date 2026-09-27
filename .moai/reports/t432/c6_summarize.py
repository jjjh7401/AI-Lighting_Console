"""c6_all_types.txt 요약 — 기종별 컨테이너 자식 수·이미터 필드 값(원문 회신에서만 뽑는다).

uv run python .moai/reports/t432/c6_summarize.py
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows: dict[str, dict] = {}
for line in (HERE / "c6_all_types.txt").read_text(encoding="utf-8").splitlines():
    if not line.startswith("<<< "):
        continue
    body = json.loads(line[4:])
    path = body.get("path", "")
    m = re.match(r"Patch/FixtureTypes/(\d+)(.*)", path)
    if not m:
        continue
    no, rest = m.group(1), m.group(2)
    row = rows.setdefault(no, {"emitters": []})
    if body.get("kind") == "state":
        if rest == "":
            row["name"] = body["node"]["name"]
        elif not body.get("ok", True):
            row[rest.rsplit("/", 1)[-1]] = f"ERR {body.get('error')}"
        else:
            kids = [c.get("name") for c in body.get("children", [])]
            row[rest.rsplit("/", 1)[-1]] = f"{body['node']['childCount']} {kids}"
    elif body.get("kind") == "props":
        if not body.get("ok", True):
            continue
        reads = {r["n"]: (r.get("v") if r.get("ok") else f"✗{r.get('e')}") for r in body["reads"]}
        if all(str(v).startswith("✗") for v in reads.values()):
            continue  # 없는 이미터 번호
        row["emitters"].append(reads)
    else:
        row.setdefault("other", []).append(line[:160])

for no, row in rows.items():
    print(f"## type {no} {row.get('name')}")
    for key in ("Emitters", "CRIs", "FTFilters", "ColorSpaceCollect", "GamutCollect", "Wheels"):
        print(f"   {key}: {row.get(key)}")
    for e in row["emitters"]:
        print(
            f"   emitter {e.get('NAME')}: COLOR={e.get('COLOR')} INTENSITY={e.get('INTENSITY')} "
            f"DWL={e.get('DOMINANTWAVELENGTH')} DIODEPART={e.get('DIODEPART')!r}"
        )
    for o in row.get("other", []):
        print("   other:", o)
