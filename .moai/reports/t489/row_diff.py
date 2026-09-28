"""t489 — t455 테스트 곡(8구간, Chorus 3 → Outro)의 컨셉 행을 출력한다.

고치기 전/후 트리에서 각각 돌려 행 차이를 본다.
실행: `uv run python .moai/reports/t489/row_diff.py`
"""

import sys

sys.path.insert(0, ".")
from server.tests.test_runbook_payload_t455_t456 import _sections
from server.tests.test_song_timeline_concept_report_wiring import _payload

report = _payload(bpm=120.0, sections=_sections())["concept_report"]
for r in report["rows"]:
    print(r["q"], r["ts"], r["kind"], r["section"], r["occurrence"], r["trigger"])
print("rows:", len(report["rows"]))
