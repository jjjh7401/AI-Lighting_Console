"""t496 — t458 시점 사본(t458_copy.json = git show b9c28959:…)의 구조 차이 중 beat_grid 밖의 것.
실행: ``uv run python .moai/reports/t496/c1_non_beatgrid.py``
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from server.tests.runbook_payload_fixture import build_payload  # noqa: E402
from server.tests.test_runbook_payload_fixture_t496 import structure_diff  # noqa: E402

old = json.loads(Path(__file__).with_name("t458_copy.json").read_text(encoding="utf-8"))
for line in structure_diff(build_payload(), old):
    if "beat_grid" not in line:
        print(line)
