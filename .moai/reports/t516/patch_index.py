# ruff: noqa: E501 — 한국어 머리말·판독 경로가 길어 줄 길이 규칙을 끈다
"""t516 — 패치 목록 판독 파일에서 (상태 경로 순번 i, 고정구 이름)을 뽑는다(속성 읽기 경로를 만들 때 쓴다).

실행: uv run python .moai/reports/t516/patch_index.py <판독 파일> [<판독 파일> …]
"""

import json
import re
import sys
from pathlib import Path

seen: dict[int, str] = {}
for name in sys.argv[1:]:
    for body in re.findall(r"<<< (.*)", Path(name).read_text("utf-8")):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        if data.get("path") == "Patch/Stages/1/Fixtures":
            for child in data.get("children") or ():
                seen[child["i"]] = child["name"]
for i in sorted(seen):
    print(i, seen[i])
