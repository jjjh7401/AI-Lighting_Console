"""t520 — 재생 표본(result.json samples)에서 큐가 바뀐 첫 표본을 뽑아 이벤트 시각과 견준다(읽기만).

실행: uv run python .moai/reports/t520/sample_view.py <result.json>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t520")
import m2a_batch1 as gen  # noqa: E402

result = json.loads(Path(sys.argv[1]).read_text("utf-8"))
print("audio", result.get("audio"))
want = {
    "scene": [gen.LEAD + s[3] for s in gen.SCENE],
    "rhythm": [gen.LEAD + r[2] for r in gen.RHYTHM],
}
keys = [k for k in result["samples"][0] if k not in ("t", "cursor")]
prev: dict = {}
for row in result["samples"]:
    for k in keys:
        if row[k] != prev.get(k):
            print(f"t={row['t']:6.2f} cursor={row['cursor']} seq {k} -> {row[k]}")
            prev[k] = row[k]
print("planned TC (scene)", [round(x, 2) for x in want["scene"]])
print("planned TC (rhythm)", [round(x, 2) for x in want["rhythm"]])
print("samples", len(result["samples"]))
