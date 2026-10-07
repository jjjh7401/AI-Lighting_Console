"""t516 — 바닥 기구 판독용 단계 목록을 만든다(무빙 501~508·521~528, BACK 201~212).

`diag7_patch.txt` 에서 FID → 패치 경로를 찾아 위치·회전·반전 속성 읽기 단계를 한 줄로 찍는다.
실행: uv run python .moai/reports/t516/floor_reads.py > <단계 파일>
"""

import json
import subprocess
import sys
from pathlib import Path

FIELDS = (
    "NAME,FID,FIXTURETYPE,POSX,POSY,POSZ,ROTX,ROTY,ROTZ,"
    "DMXINVERTTILT,INVERT3DTILT,OFFSETTILT,OFFSETPAN"
)
idx = {}
for line in Path(".moai/reports/t516/diag7_patch.txt").read_text("utf-8").splitlines():
    if not line.startswith("<<< "):
        continue
    data = json.loads(line[4:])
    if data.get("kind") != "props":
        continue
    reads = {r["n"]: r.get("v") for r in data["reads"]}
    idx[int(reads["FID"])] = data["path"]
want = [*range(501, 509), *range(521, 529), *range(201, 213)]
steps = [f"props:{idx[f]}|{FIELDS}" for f in want]
# 읽기 전용 프로브(ping/state/props 만 보낸다)를 그대로 부른다
subprocess.run(
    [sys.executable, ".moai/reports/t506/probe_readonly.py", *steps],  # noqa: S603
    check=False,
)
