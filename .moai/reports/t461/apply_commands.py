"""t461 ⚠1 — 콘솔 반영 명령 전후 대조. 같은 시나리오를 수정 전·후 코드로 돌려
큐 하나의 value_line·summary·skips 를 찍는다(콘솔 접촉 0 — 계획만 만든다).

실행: .venv/bin/python .moai/reports/t461/apply_commands.py > <출력>
"""

import json
import sys

sys.path.insert(0, ".")

from server.design.cue_sheet_apply import plan_cue_console_apply  # noqa: E402

MAPPING = [
    {"group_name": "Key Wash", "group_no": 11, "role": "key"},
    {"group_name": "Back Light", "group_no": 12, "role": "back"},
]
LEGEND = {"블루": "#0D33FF", "앰버": "#FF8C0D"}


def section(key: int, back: int, **extra: object) -> dict:
    return {
        "cue_number": 3,
        "label": "Chorus",
        "intensity": [{"group": "KEY", "level": key}, {"group": "BACK", "level": back}],
        "palette_primary": "블루",
        "fade_seconds": 1.5,
        **extra,
    }


SCENARIOS = {
    "equal_levels": (section(90, 90), MAPPING),
    "equal_levels_with_secondary": (section(80, 80, palette_secondary="앰버"), MAPPING),
    "back_lower": (section(90, 70), MAPPING),
    "key_lower_with_secondary": (section(50, 90, palette_secondary="앰버"), MAPPING),
    "back_lower_unmapped_back": (section(90, 70), MAPPING[:1]),
}

for name, (sec, mapping) in SCENARIOS.items():
    plan = plan_cue_console_apply(sec, None, mapping, LEGEND)
    print(f"## {name}")
    print("value_line:", plan.value_line)
    print("summary:", plan.summary)
    print("skips:", json.dumps([s.detail for s in plan.skips], ensure_ascii=False))
