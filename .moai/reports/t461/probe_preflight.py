"""t461 ⚠1 조건② — test_rig_preflight 의 「일부만 나가는 큐 1건」이 왜 사라졌나.
같은 시나리오(시험 헬퍼 그대로)로 사전 점검 요약 줄과 큐별 사유를 찍는다."""

import sys

sys.path.insert(0, ".")

from server.design.rig_preflight import plan_rig_preflight, render_rig_preflight  # noqa: E402
from server.tests.test_rig_preflight import _payload_for, _unbound_palette_timeline  # noqa: E402

timeline = _unbound_palette_timeline()
report = plan_rig_preflight(timeline, console_payload=_payload_for(timeline))
for line in render_rig_preflight(report).splitlines():
    if "반영 가능" in line or line.startswith("  · 큐"):
        print(line)
print("partial:", [cue.cue_number for cue in report.partial_cues])
for cue in report.partial_cues:
    for skip in cue.skips:
        print(f"  skip q{cue.cue_number} [{skip.reason}] {skip.detail}")
cue30 = next(s for s in timeline["sections"] if s["cue_number"] == 30)
print("q30 intensity:", cue30.get("intensity"), "fixture_groups:", cue30.get("fixture_groups"))
print("skipped:", [cue.cue_number for cue in report.skipped_cues])
