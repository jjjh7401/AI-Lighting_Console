"""t469 실기 캡처(`<<<` 회신)를 그대로 테스트 픽스처로 옮긴다 — 값은 손대지 않는다.

uv run python .moai/reports/t477/extract_pools.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
out = {
    "_provenance": (
        "verbatim '<<<' replies from .moai/reports/t469/run2_preset_pools.txt and "
        "run3_phaser_pools.txt (real grandMA3 onPC, card t469). Keys are the console "
        "paths the probe read. Regenerate with .moai/reports/t477/extract_pools.py"
    ),
    "replies": {},
}
for name in ("run2_preset_pools.txt", "run3_phaser_pools.txt"):
    path = None
    for line in (ROOT / ".moai/reports/t469" / name).read_text(encoding="utf-8").splitlines():
        if line.startswith(">>> state "):
            path = line.split("'")[1]
        elif line.startswith("<<< ") and path:
            if "PresetPools" in path:
                out["replies"][path] = json.loads(line[4:])
            path = None
target = ROOT / "server/tests/fixtures/console/t469_preset_pools.json"
target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(sorted(out["replies"]))
