"""t553 옆 화면 확인 — 프리셋 2.1 에서 MOVER-U 빔이 정말 수직인가(리드 지시 2026-10-11).

지금까지 「2.1 = 빔 수직」은 정면 화면만 본 추정이었다. 감독이 onPC 3D 를 FRONT + SIDE 로
나눠, 옆에서 틸트를 볼 수 있게 됐다. 이미 승인된 ``approval_t553_cell.txt`` 의 20~23줄
(켜기 + 기준 프리셋, 프로그래머만, Store 0)과 37줄(ClearAll)만 다시 보낸다 — 새 줄 없음.
줄은 승인 파일에서 그대로 읽는다(지어내지 않는다).

실행 (R=.moai/reports/t553):
  전부-거절: uv run python $R/probe_side_check.py $R/denyall_side
  실기:      uv run python $R/probe_side_check.py $R/live/side_lit \
               --approve $R/denyall_side --only side_lit
             uv run python $R/probe_side_check.py $R/live/side_clear \
               --approve $R/denyall_side --only side_clear
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli  # noqa: E402

_APPROVED = Path(".moai/reports/t553/approval_t553_cell.txt").read_text("utf-8").splitlines()


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        ("side_lit", _APPROVED[19:23]),  # 20~23줄
        ("side_clear", [_APPROVED[36]]),  # 37줄
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T553Side",
            risk_reason="t553 옆 화면 확인 — 승인된 20~23·37줄 재전송, 프로그래머만, 쇼 저장 0",
            build_plan=build_plan,
            free_slots=[],
            extra_notes=["approval_t553_cell.txt 20~23·37줄 그대로"],
        )
    )
