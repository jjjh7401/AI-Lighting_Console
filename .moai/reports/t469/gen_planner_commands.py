"""카드 t469 — 반영 계획 함수가 실제로 짓는 명령 줄을 뽑는다(시퀀스 900 시험 큐용).

실행(프로젝트 루트)::

    uv run python .moai/reports/t469/gen_planner_commands.py > <출력 파일>
"""

from __future__ import annotations

import copy
import json
import sys

sys.path.insert(0, ".")

from server.design.cue_sheet_apply import plan_console_apply  # noqa: E402


def _section(index: int, cue: int, level: int) -> dict:
    return {
        "index": index,
        "label": f"T469 C{cue}",
        "cue_number": cue,
        "start_ms": index * 1000,
        "d_level": 4,
        "intensity": [{"group": "MOVER-D", "level": level}],
        "fixture_groups": ["MOVER-D"],
    }


base = {
    "song_title": "t469",
    "sequence_number": 900,
    "layer_mapping": [{"role": "key", "group_no": 12, "group_name": "MOVER-D"}],
    "sections": [_section(1, 11, 100), _section(2, 12, 60), _section(3, 13, 90)],
}
current = copy.deepcopy(base)
current["sections"][0].update(
    {"position": "POS05", "position_preset_no": "2.5", "tracking": "Release"}
)
current["sections"][1].update({"tracking": "Cue Only"})
current["sections"][2].update({"tracking": "Block"})
plan = plan_console_apply(base, current)
print(
    json.dumps(
        {
            "commands": plan.commands,
            "applied": plan.applied,
            "summaries": plan.summaries,
            "skipped": [skip.detail for skip in plan.skipped],
        },
        ensure_ascii=False,
        indent=1,
    )
)
