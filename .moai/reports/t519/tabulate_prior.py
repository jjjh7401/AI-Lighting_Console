"""t519 — t516 이 2026-10-06 에 실기에서 읽어 둔 패치 판독(diag7_patch.txt·v4f_floor.txt)에서
BACK 201~212 와 대조군 SIDE-L/R 301~316 의 줄만 뽑아 표로 찍는다(콘솔 송신 0, 파일 읽기만).

실행: uv run python .moai/reports/t519/tabulate_prior.py
"""

import json
from pathlib import Path

SRC = Path(".moai/reports/t516")
WANT = set(range(201, 213)) | set(range(301, 307)) | set(range(311, 317))

for name in ("diag7_patch.txt", "v4f_floor.txt"):
    print(f"== {name}")
    for line in (SRC / name).read_text("utf-8").splitlines():
        if not line.startswith("<<< "):
            continue
        data = json.loads(line[4:])
        if data.get("kind") != "props":
            continue
        reads = {r["n"]: r.get("v") for r in data["reads"]}
        try:
            fid = int(float(reads.get("FID") or 0))
        except ValueError:
            continue
        if fid in WANT:
            print(data["path"], json.dumps(reads, ensure_ascii=False))
