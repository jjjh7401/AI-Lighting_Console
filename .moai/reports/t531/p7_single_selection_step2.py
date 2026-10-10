"""P7 (리드 리뷰 수정판) — 단일 선택 vs 복수 선택 + ``Step 2`` 를 **같은 시퀀스
안의 두 큐**로 직접 대조한다.

리드 리뷰(2026-10-10) 세 항목 중 2번 수정: 원판은 대조군이 없어 "단일 선택이면
페이저가 남는다"만 보고 "복수 선택이면 마지막 것만 남는다"(t520 가설,
`verdict.md:46`)를 가르지 못했다. 이번판은 같은 시퀀스 303 에 큐를 둘 저장한다:

- **Cue 1**(단일 선택, 기준선) — Group 4(BACK) 하나만 선택해 디머 페이저.
- **Cue 2**(t520 모양의 축소판) — Group 4(BACK) 선택+디머 페이저 값을 넣은 뒤
  **선택을 Group 11(MOVER-U)로 바꿔** Pan 페이저 값을 넣고 저장 — t520
  `verdict.md:167`이 적은 "`Step 2` 뒤 선택을 바꿔도 단계 2에 머무는지는 안 잰
  것"을 가장 작게 줄인 형태(선택 다섯 개 → 둘, 그룹 하나씩).

판정: Cue 1 은 디머 페이저가 남고 Cue 2 는 BACK 디머 페이저를 잃고 MOVER-U Pan
페이저만 남으면 → t520 가설(마지막 선택만 남는다) 확인. 둘 다 남거나 둘 다
없으면 그 결과를 그대로 적는다(가설 확인만을 기대하지 않는다).
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

SEQ_NO = 303
GROUP_BACK = 4
GROUP_MOVER_U = 11


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "store_cue1_single",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP_BACK}",
                "Attribute 'Dimmer' At 0",
                "Step 2",
                "Attribute 'Dimmer' At 100",
                f"Store Sequence {SEQ_NO} Cue 1 'LDBEAT M1 - P7 cue1 single-selection step2'",
                "ClearAll",
            ],
        ),
        (
            "store_cue2_two_selections",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP_BACK}",
                "Attribute 'Dimmer' At 0",
                "Step 2",
                "Attribute 'Dimmer' At 100",
                f"Group {GROUP_MOVER_U}",
                "Attribute 'Pan' At Relative 10",
                "Step 2",
                "Attribute 'Pan' At Relative -10",
                f"Store Sequence {SEQ_NO} Cue 2 'LDBEAT M1 - P7 cue2 two-selections step2'",
                f"Set Sequence {SEQ_NO} Property 'Name' 'LDBEAT M1 - P7 single-vs-double'",
                "ClearAll",
            ],
        ),
        ("play_cue1", [f"Goto Cue 1 Sequence {SEQ_NO}"]),
        ("off_cue1", [f"Off Sequence {SEQ_NO}"]),
        ("play_cue2", [f"Goto Cue 2 Sequence {SEQ_NO}"]),
        ("release", [f"Off Sequence {SEQ_NO}"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P7",
            risk_reason="t531 M1 P7(수정판) — 시퀀스 303(새), 큐1 단일선택 vs 큐2 복수선택 대조",
            build_plan=build_plan,
            free_slots=[seq_path(SEQ_NO)],
            extra_notes=[
                "t520 가설(verdict.md:46) 직접 대조 — 같은 시퀀스의 큐1/큐2로 변수를 분리.",
                "읽기 판정: 큐1 디머 페이저 존재 AND 큐2 디머 페이저 소실+Pan 페이저 존재 → "
                "가설 확인. 그 외 결과는 그대로 기록(확인을 전제하지 않는다).",
                "감독 관찰: 큐1 재생 시 BACK 깜빡임, 큐2 재생 시 BACK 이 여전히 깜빡이는지.",
            ],
        )
    )
