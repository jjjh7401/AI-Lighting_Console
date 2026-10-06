"""t516 v2 실기 결과 요약 — 저장된 큐 Part 크기(빈 Part 2521B 기준), 타임코드 표본, 송신 시각.

실행: uv run python .moai/reports/t516/v2_summary.py <실행 폴더>
"""

import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
EMPTY = 2521  # 빈 Part(OffCue/CueZero) MEMORYFOOTPRINT — diag4.txt
for line in (out / "steps.jsonl").read_text("utf-8").splitlines():
    row = json.loads(line)
    if row.get("step", "").startswith(("post_part_", "post_seq_")):
        reads = {r["n"]: r.get("v") for r in (row.get("payload") or {}).get("reads") or ()}
        size = reads.get("MEMORYFOOTPRINT")
        extra = f" (+{int(size) - EMPTY}B over empty)" if size else ""
        print(row["step"], row.get("path"), reads, extra)
result = json.loads((out / "result.json").read_text("utf-8"))
for sample in result.get("samples", []):
    print("SAMPLE", sample)
audit = next((out / "audit").glob("audit-*.jsonl"))
sends = [json.loads(x) for x in audit.read_text("utf-8").splitlines()]
sends = [x for x in sends if x.get("event") == "executed" and x.get("kind") == "command"]
print("first send", sends[0]["ts"], sends[0]["command"])
print("last send", sends[-1]["ts"], sends[-1]["command"])
