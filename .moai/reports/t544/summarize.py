"""t544 읽기 결과 요약 — 응답 줄(<<<)만 읽어 크기표와 속성 이름 diff 를 낸다. 콘솔 송신 없음.

실행: uv run python .moai/reports/t544/summarize.py <읽기결과파일> [<읽기결과파일> ...]
"""

import json
import sys
from pathlib import Path

names = {}
for path in sys.argv[1:]:
    for line in Path(path).read_text("utf-8").splitlines():
        if not line.startswith("<<< "):
            continue
        j = json.loads(line[4:])
        tail = "/".join(j.get("path", "").split("/")[-2:])
        kind = j["kind"]
        if kind == "pong":
            print("pong", {k: v for k, v in j.items() if k not in ("id", "kind")})
        elif kind in ("props", "prop"):
            reads = j.get("reads") or [j]
            print(tail, {r.get("n"): r.get("v") for r in reads if r.get("n") != "NAME"})
        elif kind == "introspect":
            raw = j.get("fields") or []
            ks = [x if isinstance(x, str) else (x.get("n") or x.get("name")) for x in raw]
            names[tail] = names.get(tail, []) + ks
            print(
                "introspect",
                tail,
                "n",
                len(ks),
                "truncated",
                j.get("truncated"),
                "offset",
                j.get("offset"),
                "total",
                j.get("total"),
                "first",
                ks[:1],
            )
        elif kind == "state":
            print("state", tail, j.get("node"), "children", len(j.get("children", [])))

if names:
    ref = next(iter(names))
    base = names[ref]
    for t, ks in names.items():
        print(
            t,
            "vs",
            ref,
            "order-equal",
            ks == base,
            "+",
            sorted(set(ks) - set(base)),
            "-",
            sorted(set(base) - set(ks)),
        )
