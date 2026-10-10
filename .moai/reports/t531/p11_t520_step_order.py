"""P11 — t520 실패 재현: ⑦ 큐2 를 t520 줄 순서로 바꾼 한 가지 차이만.

⑦ 큐2(선택마다 ``At 0 → Step 2 → At 100`` 을 끝내고 다음 선택)는 감독 눈에
「두 그룹 다 깜빡임」이었다. t520 이 실제로 보낸 꼴(승인 문면
``.moai/reports/t520/approval_m2a_batch1_v2.txt:178-209``)은 달랐다 — 선택 전부에
단계 1 값을 넣고 ``Step 2`` 를 **한 번만**(``:183``), 그 뒤 선택을 다시 골라 단계 2 값.

이 묶음은 그 차이 하나만 바꾼다. 그룹(11·10)·속성(디머만)·값(0/100)은 ⑦ 큐2 와 같다.
t520 의 나머지 차이(선택 다섯·Fixture 목록·Pan/Tilt 섞임·Phase/Measure/SpeedMaster)는
그대로 두지 않는다 — 한 번에 하나만 가른다.

새 번호: 시퀀스 310.

판정(감독 눈): 두 그룹 다 깜빡이나. 하나만 깜빡이면 「Step 2 뒤 선택을 바꾸면
앞 선택의 단계 구성이 덮인다」 가설을 지지한다. 둘 다 깜빡이면 t520 실패의 원인은
나머지 차이 쪽이다. 어느 쪽이든 본 그대로 적는다.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

SEQ_NO = 310
# ⑦ 큐2 와 같은 두 그룹 — MOVER-U(t516 verdict.md:264) · WASH-ALL(t520 verdict.md:508)
GROUP_FIRST = 11
GROUP_SECOND = 10


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "store_cue",
            [
                "ChangeDestination Root",
                "ClearAll",
                # 단계 1 값을 두 선택에 먼저 (t520 :178-182 꼴)
                f"Group {GROUP_FIRST}",
                "Attribute 'Dimmer' At 0",
                f"Group {GROUP_SECOND}",
                "Attribute 'Dimmer' At 0",
                # Step 2 는 한 번만 (t520 :183)
                "Step 2",
                # 선택을 다시 골라 단계 2 값 (t520 :184-209 꼴)
                f"Group {GROUP_FIRST}",
                "Attribute 'Dimmer' At 100",
                f"Group {GROUP_SECOND}",
                "Attribute 'Dimmer' At 100",
                f"Store Sequence {SEQ_NO} Cue 1 'LDBEAT M1 - P11 t520 step order'",
                f"Set Sequence {SEQ_NO} Property 'Name' 'LDBEAT M1 - P11 t520 step order'",
                "ClearAll",
            ],
        ),
        ("play", [f"Goto Cue 1 Sequence {SEQ_NO}"]),
        ("release", [f"Off Sequence {SEQ_NO}"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P11",
            risk_reason="t531 M1 P11 — 시퀀스 310(새), ⑦ 큐2 를 t520 줄 순서(Step 2 한 번)로",
            build_plan=build_plan,
            free_slots=[seq_path(SEQ_NO)],
            extra_notes=[
                "⑦ 큐2 와의 차이는 Step 2 위치 하나(t520 approval_m2a_batch1_v2.txt:178-209 꼴).",
                "감독 관찰: MOVER-U 와 바닥 워시가 둘 다 깜빡이나.",
            ],
        )
    )
