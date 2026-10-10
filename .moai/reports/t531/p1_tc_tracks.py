"""P1 — 타임코드 하나에 트랙 ≥3개(목표 6). t516/t520 은 트랙 2개만 쟀다.

새 번호: 타임코드 30(새). 트랙은 기존 시퀀스 228~233(RHYTHM PROBE v3 L0~L5)을
그대로 참조만 한다 — 그 시퀀스들은 손대지 않는다.

PASS/FAIL: ``state ShowData/.../Timecodes/30/1`` 의 자식 수가 7(MarkerTrack 1 +
Track 6)이고, Track 6개의 ``TARGET`` 속성이 시퀀스 228~233 순서로 맞는가.
감독 관찰: 불필요(기계 판독으로 충분).

문법 출처: ``Assign Sequence <S> At Timecode <N>.1.<track>`` — t516 rhythm_probe.py
PREP(``tc_a``) 실측 그대로, 트랙 수만 2→6.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, tc_path  # noqa: E402

TC_NO = 30
TRACK_SEQS = (228, 229, 230, 231, 232, 233)


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "tc_setup",
            [
                f"Store Timecode {TC_NO}",
                f"Set Timecode {TC_NO} Property 'Name' 'LDBEAT M1 - P1 six tracks'",
                f"Set Timecode {TC_NO} Property 'Duration' 10 'AutoStop' 0",
                f"Store Timecode {TC_NO}.1",
            ],
        ),
        (
            "assign_tracks",
            [
                f"Assign Sequence {s} At Timecode {TC_NO}.1.{i + 1}"
                for i, s in enumerate(TRACK_SEQS)
            ],
        ),
        ("play", [f"Go Timecode {TC_NO}"]),
        ("release", [f"Off Timecode {TC_NO}", *[f"Off Sequence {s}" for s in TRACK_SEQS]]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P1",
            risk_reason="t531 M1 P1 — 타임코드 30(새) 에 기존 시퀀스 6개를 트랙으로 배정",
            build_plan=build_plan,
            free_slots=[tc_path(TC_NO)],
            extra_notes=[
                "참조하는 시퀀스 228~233 은 기존 객체 — Store/수정하지 않는다.",
                "읽기 판정: Timecode 30/1 자식 7개(Marker+Track6), TARGET 순서 228..233.",
            ],
        )
    )
