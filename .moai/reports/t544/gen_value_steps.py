"""t544 — 스키마 페이지(s2)에서 필드 이름을 모아 2.1~2.6 값 읽기 단계 파일을 만든다. 콘솔 송신 없음.

실행: uv run python .moai/reports/t544/gen_value_steps.py
출력: .moai/reports/t544/s3_steps.txt, 필드 목록 s3_fields.txt
"""

import json
from pathlib import Path

HERE = Path(".moai/reports/t544")
fields, types = [], {}
for line in (HERE / "s2_schema.txt").read_text("utf-8").splitlines():
    if line.startswith("<<< "):
        for f in json.loads(line[4:]).get("fields", []):
            if f["n"] not in types:
                fields.append(f["n"])
                types[f["n"]] = f["t"]
(HERE / "s3_fields.txt").write_text("\n".join(f"{n}\t{types[n]}" for n in fields) + "\n", "utf-8")
steps = []
for i in range(1, 7):
    for k in range(0, len(fields), 16):
        steps.append(
            f"props:ShowData/DataPools/Default/PresetPools/2/{i}|" + ",".join(fields[k : k + 16])
        )
(HERE / "s3_steps.txt").write_text("\n".join(steps) + "\n", "utf-8")
print("unique fields", len(fields), "steps", len(steps))
