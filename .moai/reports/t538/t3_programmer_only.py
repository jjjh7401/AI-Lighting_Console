"""t538 T3 — 시퀀스를 거치지 않고 프로그래머에서만 A0 위치 페이저를 낸다(Store 없음).

리드 설계(2026-10-10): 311 을 끈 뒤 A0 몸통 줄을 프로그래머에만 넣고 감독 눈 → ClearAll.
- 움직임 → 원인은 「시퀀스 저장·재생 경로」.
- 정지 → 원인은 「장비·출력·시각화 쪽」.
A0 몸통(t516 v4:20-24)과 같은 줄이다. Dimmer 70 은 A0 그대로 둔다(빛이 있어야 보인다).
새 객체 0 · 쇼 저장 0.

실행: uv run python .moai/reports/t538/t3_programmer_only.py <out>
      [--rehearse | --approve <dir> --only <묶음>]
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli  # noqa: E402

FIX = "Fixture 501 + 502 + 503 + 504 + 505 + 506 + 507 + 508"


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        ("t3_off311", ["Off Sequence 311"]),
        (
            "t3_prog",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"{FIX} ; Attribute 'Dimmer' At 70",
                f"{FIX} ; Attribute 'Tilt' At 45",
                f"{FIX} ; Attribute 'Tilt' At Relative 30",
                "Attribute 'Tilt' At Phase 0 Thru 360",
                "Attribute 'Tilt' At Speed 112",
            ],
        ),
        ("t3_clear", ["ClearAll"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T538-T3",
            risk_reason="t538 T3 — 311 끄고 프로그래머 전용 Tilt 페이저(501~508), Store 없음",
            build_plan=build_plan,
            free_slots=[],
            extra_notes=["Store 0줄. 감독 판정 뒤 t3_clear."],
        )
    )
