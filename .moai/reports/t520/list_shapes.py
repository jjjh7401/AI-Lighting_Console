# ruff: noqa: E501 — 한국어 머리말·집계 출력 줄
"""t520 — 실기 감사 로그에서 `Fixture a + b + …` 줄의 목록 길이·점(서브픽스처) 유무별 성공/실패를 센다.

실패 원인이 「목록 안의 서브픽스처 번호」인지 「목록 길이」인지 가르려고 쓴다(읽기만, 콘솔 0).
실행: uv run python .moai/reports/t520/list_shapes.py <steps.jsonl 또는 audit 폴더>...
"""

import json
import sys
from collections import Counter
from pathlib import Path


def rows(path: Path):
    files = sorted(path.rglob("*.jsonl")) if path.is_dir() else [path]
    for f in files:
        for line in f.read_text("utf-8").splitlines():
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


tally: Counter = Counter()
examples: dict = {}
for arg in sys.argv[1:]:
    for r in rows(Path(arg)):
        cmd = r.get("command")
        ok = r.get("ok")
        if not isinstance(cmd, str) or not cmd.startswith("Fixture ") or ok is None:
            continue
        if r.get("event") not in (None, "executed") or r.get("kind") not in (
            None,
            "command",
            "exec",
        ):
            continue
        sel = cmd.split(";")[0][len("Fixture ") :]
        items = [x.strip() for x in sel.split("+")]
        key = (len(items), any("." in x for x in items), bool(ok))
        tally[key] += 1
        examples.setdefault(key, cmd[:90])
for (n, dot, ok), c in sorted(tally.items()):
    print(
        f"items={n:3d} subfixture_in_list={dot!s:5} ok={ok!s:5} count={c}  e.g. {examples[(n, dot, ok)]}"
    )
