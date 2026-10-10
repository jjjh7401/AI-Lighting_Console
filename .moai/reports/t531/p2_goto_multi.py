"""P2 — 2번째 큐를 넘어선 Goto + 여러 시퀀스 동시. 미리보기만(Goto/Off), 새 번호 없음.

기존 시퀀스만 쓴다 — 쓰기 0, 신규 객체 0. free_slots 는 비어 있다(쓸 새 번호가 없다).

PASS/FAIL: 세 Goto 각각의 송신 결과 ok, 직후 ``CURRENTCUE`` 가 요청한 큐로
읽히는가(시퀀스 228 큐 3, 11 큐 1, 12 큐 1). 감독 관찰: 세 시퀀스가 동시에
무대에 걸리는지(혼선·우선순위) — 기계 판독은 "셋 다 CURRENTCUE 가 맞다"까지만
답한다.

문법 출처: ``Goto Cue <n> Sequence <s>`` — t516 control_probe.py TIMELINE 실측
그대로(``Goto Cue 1 Sequence 219`` 등). 2번째를 넘는 큐 번호(3)만 바꿨다.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli  # noqa: E402

TARGETS = ((228, 3), (11, 1), (12, 1))  # (시퀀스, 큐) — 228 은 큐 1~? 중 2번째를 넘긴 3


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        ("goto_all", [f"Goto Cue {cue} Sequence {seq}" for seq, cue in TARGETS]),
        ("off_all", [f"Off Sequence {seq}" for seq, _ in TARGETS]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P2",
            risk_reason="t531 M1 P2 — 미리보기 Goto/Off, 기존 시퀀스만, 신규 객체 0",
            build_plan=build_plan,
            free_slots=[],
            extra_notes=[
                "쓰기 0 — 기존 시퀀스 228·11·12 의 Goto/Off 뿐.",
                "228 큐 3 이 실제로 존재하는지는 r0b_pools.txt 에 큐 개수가 안 적혀 있어 미확인 — "
                "live 실행 전 `state Sequences/228` 로 큐 수를 먼저 재라.",
            ],
        )
    )
