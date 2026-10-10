"""t538 T4·T5 — 프로그래머 전용(Store 없음), 2단계 상대 Tilt 페이저.

T3 감독 판정(리드 경유 2026-10-10): 1단계 상대값은 「위치는 바뀌었는데 무빙 안 됨」,
Fixture Sheet 의
501 Tilt 숫자도 멈춤. 앱 룰북은 「Steps CREATE the phaser (two or more)」
(server/rulebook/assets/v2.4.2/33_effect_editors.md:21)이고, 앱 코드도 1단계를 거부한다
(server/fx/schema.py:67 MIN_STEPS=2, instantiate.py:405-416 REQ-FXLIB-009).

- T4 양성 대조: t516 v4 A3(시퀀스 237) 몸통 그대로(approval_rhythm_probe_v4.txt:28-36), Store 없음.
- T5: T4 + 단계마다 `Step <k> At Accel -100` / `At Decel -100` — 앱이 사인 곡선으로 실측한 줄
  (instantiate.py:470-485, 「Measured 2026-08-15 (V1)」).
  공식 문서의 Form(Sine/Circle)은 페이저 편집기
  버튼으로만 문서화돼 있고 명령줄 키워드는 찾지 못했다 — 그래서 「1단계 + Form」은 만들지 않는다.
  줄 순서는 앱과 같다: 단계 → 곡선 → 위상 → 속도(instantiate.py:646).

새 객체 0 · 쇼 저장 0. 각 시험은 켜 둔 채 감독 판정 → ClearAll.
실행: uv run python .moai/reports/t538/t4_t5_two_steps.py <out>
      [--rehearse | --approve <dir> --only <묶음>]
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli  # noqa: E402

FIX = "Fixture 501 + 502 + 503 + 504 + 505 + 506 + 507 + 508"

STEPS = [
    "ChangeDestination Root",
    "ClearAll",
    f"{FIX} ; Attribute 'Dimmer' At 70",
    f"{FIX} ; Attribute 'Tilt' At 45",
    f"{FIX} ; Attribute 'Tilt' At Relative -30",
    "Step 2",
    "Attribute 'Tilt' At Relative 30",
]
CURVE = [
    "Step 1 At Accel -100",
    "Step 1 At Decel -100",
    "Step 2 At Accel -100",
    "Step 2 At Decel -100",
]
TAIL = ["Attribute 'Tilt' At Phase 0 Thru 360", "Attribute 'Tilt' At Speed 112"]


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        ("t4_prog", [*STEPS, *TAIL]),
        ("t4_clear", ["ClearAll"]),
        ("t5_prog", [*STEPS, *CURVE, *TAIL]),
        ("t5_clear", ["ClearAll"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T538-T4T5",
            risk_reason="t538 T4·T5 — 프로그래머 전용 2단계 상대 Tilt 페이저(501~508), Store 없음",
            build_plan=build_plan,
            free_slots=[],
            extra_notes=["Store 0줄. 각 시험 감독 판정 뒤 clear."],
        )
    )
