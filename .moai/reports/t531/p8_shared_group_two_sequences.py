"""P8 — 같은 그룹을 두 시퀀스가 나눠 쥘 때(하나는 디머, 하나는 팬/틸트) 섞이는가.

새 번호: 시퀀스 304(디머 전담, 새) · 305(팬/틸트 전담, 새). 둘 다 그룹 MOVER-ALL(13)을
선택한다 — BACK(4)은 무빙헤드가 아니라 팬/틸트가 없을 수 있어 둘 다 가진 MOVER-ALL
로 바꿨다(그룹 목록 실측, r0b_pools.txt).

PASS/FAIL: 둘 다 Goto 한 뒤 ``Group 13`` 의 ``DIMMER``·``PAN``·``TILT`` 를 한 번에
읽어 셋 다 "의도한 값"으로 읽히는가(디머는 시퀀스 304 값, 팬/틸트는 305 값). 감독
관찰 필수: HTP/LTP 트래킹 규칙에 따라 두 시퀀스가 같은 그룹의 다른 속성을 동시에
쥘 수 있는지는 grandMA3 의 속성별 트래킹(채널별, 좌표별이 아니라 "다른 속성이면
충돌 안 함")에 달려 있다 — 이 리포에 전례 없음.

문법 출처: 디머 100%/Pan·Tilt Relative 10 — t516 rhythm_probe.py 의 Attribute
문법 그대로, 새 조합.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

SEQ_DIMMER = 304
SEQ_PANTILT = 305
# t531 v2: Group 13 은 t516 에서 8/16대만 보였다(:219-220)
# → 보였던 Group 11 MOVER-U(t516 verdict.md:264)로 교체
GROUP_MOVER_ALL = 11


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "store_dimmer_seq",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP_MOVER_ALL}",
                "Attribute 'Dimmer' At 100",
                f"Store Sequence {SEQ_DIMMER} Cue 1 'LDBEAT M1 - P8 dimmer-only'",
                f"Set Sequence {SEQ_DIMMER} Property 'Name' 'LDBEAT M1 - P8 dimmer'",
                "ClearAll",
            ],
        ),
        (
            "store_pantilt_seq",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP_MOVER_ALL}",
                "Attribute 'Pan' At Relative 10",
                "Attribute 'Tilt' At Relative 10",
                f"Store Sequence {SEQ_PANTILT} Cue 1 'LDBEAT M1 - P8 pantilt-only'",
                f"Set Sequence {SEQ_PANTILT} Property 'Name' 'LDBEAT M1 - P8 pantilt'",
                "ClearAll",
            ],
        ),
        (
            "play_both",
            [f"Goto Cue 1 Sequence {SEQ_DIMMER}", f"Goto Cue 1 Sequence {SEQ_PANTILT}"],
        ),
        ("release", [f"Off Sequence {SEQ_DIMMER}", f"Off Sequence {SEQ_PANTILT}"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P8",
            risk_reason="t531 M1 P8 — 시퀀스 304/305(새), MOVER-ALL 을 디머/팬틸트로 분담",
            build_plan=build_plan,
            free_slots=[seq_path(SEQ_DIMMER), seq_path(SEQ_PANTILT)],
            extra_notes=[
                "BACK 대신 MOVER-ALL 사용(무빙헤드만 팬/틸트 보유).",
                "감독 관찰 필수: 두 시퀀스가 섞이는지, 한쪽이 다른 쪽을 덮는지.",
            ],
        )
    )
