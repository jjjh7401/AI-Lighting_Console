"""t538 T1 — A0(311) 을 켜 둔 채 프로그래머에 PositionMSpeed 0 한 줄, 감독 판정 뒤 ClearAll.

감독 승인(리드 경유, 2026-10-10): 이 두 줄만. 새 객체 0 · 쇼 저장 0.
가르는 것: 어딘가 MSpeed 를 느리게 쥐고 있어 위치 페이저가 멈춰 보이는가(a0-stop-diag.md 후보 ①).
문법 근거: t464 run21 (Spiider 에서 `Attribute 'PositionMSpeed' At 0` OK).

실행: uv run python .moai/reports/t538/t1_mspeed.py <out> [--rehearse | --approve <dir> --only <묶음>]
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli  # noqa: E402

FIX = "Fixture 501 + 502 + 503 + 504 + 505 + 506 + 507 + 508"


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        ("t1_mspeed", [f"{FIX} ; Attribute 'PositionMSpeed' At 0"]),
        ("t1_clear", ["ClearAll"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T538-T1",
            risk_reason="t538 T1 — 프로그래머 PositionMSpeed 0 (501~508), 새 객체 0",
            build_plan=build_plan,
            free_slots=[],
            extra_notes=["311 켜 둔 상태 전제. 감독 판정 뒤 t1_clear."],
        )
    )
