"""t498 — 읽기 전용 판독 파일에서 풀별 (번호, 이름) 목록을 뽑아 비교한다(C1·C3).

실행: uv run python .moai/reports/t498/pool_snapshot.py <판독.txt> [<비교할 판독.txt>]
페이징(@offset) 응답은 같은 경로로 합친다.
"""

import json
import re
import sys
from pathlib import Path


def load(path: Path) -> dict[str, list[tuple[int, str]]]:
    pools: dict[str, list[tuple[int, str]]] = {}
    counts: dict[str, int | None] = {}
    for block in path.read_text("utf-8").split(">>> ")[1:]:
        m = re.search(r"<<< (\{.*\})", block)
        if not m:
            continue
        d = json.loads(m.group(1))
        if d.get("kind") != "state" or not d.get("ok"):
            continue
        key = d["path"]
        pools.setdefault(key, []).extend((c["i"], c["name"]) for c in d.get("children", []))
        counts[key] = d.get("node", {}).get("childCount")
    # 잘린 응답을 「삭제」로 읽는 함정(실측: 시퀀스 19개 중 2000 이 1쪽에서 빠져 removed 로 보였다).
    for key, n in counts.items():
        if n is not None and len(set(pools[key])) < n:
            raise SystemExit(f"TRUNCATED {path.name} {key}: read {len(set(pools[key]))} of {n}")
    return pools


a = load(Path(sys.argv[1]))
for key, items in a.items():
    print(f"{key}: {len(items)} -> {[i for i, _ in items]}")
if len(sys.argv) > 2:
    b = load(Path(sys.argv[2]))
    for key in sorted(set(a) | set(b)):
        sa, sb = set(a.get(key, [])), set(b.get(key, []))
        print(f"DIFF {key}: removed={sorted(sa - sb)} added={sorted(sb - sa)}")
