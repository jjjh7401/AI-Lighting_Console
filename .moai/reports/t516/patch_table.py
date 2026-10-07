# ruff: noqa: E501 — 한국어 머리말·판독 경로가 길어 줄 길이 규칙을 끈다
"""t516 — 86대 패치 속성 판독을 표로 묶고, 역할별로 유형·모드·DMX 주소·3D 보임·위치를 요약한다.

실행: uv run python .moai/reports/t516/patch_table.py .moai/reports/t516/diag7_patch.txt
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

rows = []
for body in re.findall(r"<<< (.*)", Path(sys.argv[1]).read_text("utf-8")):
    data = json.loads(body)
    if data.get("kind") != "props":
        continue
    rows.append(
        {r["n"]: (r.get("v") if r.get("ok") else f"!{r.get('e', '')[:20]}") for r in data["reads"]}
    )

by_role: dict[str, list[dict]] = defaultdict(list)
for row in rows:
    by_role[str(row.get("NAME", "?")).split()[0]].append(row)
print(f"fixtures read: {len(rows)}")
for role, items in by_role.items():
    print(f"\n== {role} ({len(items)})")
    for key in ("FIXTURETYPE", "MODE", "VISIBLE3D", "HIDDEN", "CONFLITEDPATCH", "BEAMANGLE"):
        print(f"  {key:15s} {dict(Counter(str(i.get(key)) for i in items))}")
    for i in items:
        pos = ",".join(str(i.get(k)) for k in ("POSX", "POSY", "POSZ"))
        print(f"    {i.get('NAME'):12s} FID {i.get('FID'):>4} PATCH {i.get('PATCH')} pos({pos})")

patches = Counter(r.get("PATCH") for r in rows if r.get("PATCH") not in (None, "", "-"))
print("\nduplicate PATCH addresses:", {k: v for k, v in patches.items() if v > 1})
