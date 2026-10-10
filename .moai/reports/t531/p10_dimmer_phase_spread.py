"""P10 — 디머 2단계 페이저 + 선택 전체 위상 펼침. 한 대씩 번갈아 보이는가.

④(프리셋 경유)·⑦ 큐1(큐 직접 저장) 모두 「다 같이 깜빡임」이었다. ``Step 2`` 는
값 두 개를 시간축에 놓을 뿐이고, 장비별로 엇갈리려면 선택 전체에 위상을 펼쳐야
한다는 리드 가설(미측정)을 가르는 묶음이다. ⑦ 큐1 과 다른 점은 위상 펼침 한 줄뿐.

새 번호: 시퀀스 309.

문법 근거:
- ``Attribute 'Dimmer' At Phase 0 Thru 360`` 은 t227 에서 Group 13 에 보내 콘솔이
  받았다(``.moai/reports/t227/verdict.md:98``, executed_ok). 룰북
  ``server/rulebook/assets/v2.4.2/32_spatial_design.md:70`` 의 디머 체이스 레시피도 같은 줄.
- 🔴 미측정: 끝값 ``180`` (t227 은 ``360``), 그리고 눈으로 번갈아 보이는지.
  ``Thru`` 는 선택 순서대로 위상을 고르게 나누는 범위라, 엄밀한 홀·짝 번갈아(0/180/0/180)
  가 아니라 물결처럼 보일 수 있다 — 결과는 본 그대로 적는다.

감독 관찰: Group 11(MOVER-U)이 한 대씩 번갈아 깜빡이는가(다 같이 / 물결 / 번갈아).
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

SEQ_NO = 309
# ⑦ 큐1 과 같은 그룹 — 감독 눈에 보였던 MOVER-U(t516 verdict.md:264)
GROUP = 11


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "store_cue",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP}",
                "Attribute 'Dimmer' At 0",
                "Step 2",
                "Attribute 'Dimmer' At 100",
                # 🔴 미측정 끝값 180 — 0 Thru 360 은 t227 에서 콘솔이 받았다
                "Attribute 'Dimmer' At Phase 0 Thru 180",
                f"Store Sequence {SEQ_NO} Cue 1 'LDBEAT M1 - P10 dimmer phase spread'",
                f"Set Sequence {SEQ_NO} Property 'Name' 'LDBEAT M1 - P10 dimmer phase spread'",
                "ClearAll",
            ],
        ),
        ("play", [f"Goto Cue 1 Sequence {SEQ_NO}"]),
        ("release", [f"Off Sequence {SEQ_NO}"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P10",
            risk_reason="t531 M1 P10 — 시퀀스 309(새), 디머 2단계 + 위상 펼침 0 Thru 180",
            build_plan=build_plan,
            free_slots=[seq_path(SEQ_NO)],
            extra_notes=[
                "⑦ 큐1 과의 차이는 'Attribute 'Dimmer' At Phase 0 Thru 180' 한 줄.",
                "문법 근거: t227 verdict.md:98 (0 Thru 360, executed_ok). 끝값 180 은 미측정.",
                "감독 관찰: MOVER-U 가 다 같이 / 물결 / 한 대씩 번갈아 중 무엇인가.",
            ],
        )
    )
