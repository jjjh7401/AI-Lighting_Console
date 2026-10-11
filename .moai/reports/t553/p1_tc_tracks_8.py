"""P1 재측정(8트랙) — 카드 t553, Part ②.

카드 t549의 발견: `MEASURED_MAX_TIMECODE_TRACKS=6`(①이 구조로 확인한 실제
최대, t531)은 LOVE ATTACK 실제 콘솔 그룹 트랙 수 8개보다 작다 — 8트랙을
한 타임코드에 몰면 트랙 레벨 전부 거절된다(`test_all_eight_love_attack_
tracks_on_one_timecode_exceeds_measured_max`). 이 프로브는 t531 P1(6트랙,
TC 30)과 같은 형태로 **트랙 수만 6→8**, 새 타임코드 번호로 재측정한다.

새 번호: 타임코드 32(새, 전부-거절 전 실기 읽기로 비어 있음 확인). 트랙은
기존 시퀀스 226~233(RHYTHM PROBE v2/v3, 8개, 실기 읽기로 존재 확인) 을
그대로 참조만 한다 — 그 시퀀스들은 손대지도 수정하지도 않는다.

PASS/FAIL: ``state ShowData/.../Timecodes/32/1`` 의 자식 수가 9
(MarkerTrack 1 + Track 8)이고, Track 8개의 ``TARGET`` 속성이 시퀀스
226..233 순서로 맞는가. 감독 관찰 불필요(기계 판독으로 충분).

문법 출처: t531 p1_tc_tracks.py(``Assign Sequence <S> At Timecode
<N>.1.<track>``) 그대로, 번호와 트랙 수만 바뀜.

실행 (R=.moai/reports/t553):
  리허설:    uv run python $R/p1_tc_tracks_8.py $R/rehearse_8track --rehearse
  전부-거절: uv run python $R/p1_tc_tracks_8.py $R/denyall_8track
실기 전송은 리드 「실행」 뒤에만(--approve $R/denyall_8track). 쇼 저장 0.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, tc_path  # noqa: E402

TC_NO = 32
TRACK_SEQS = (226, 227, 228, 229, 230, 231, 232, 233)


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "tc_setup",
            [
                f"Store Timecode {TC_NO}",
                f"Set Timecode {TC_NO} Property 'Name' 'LDBEAT T553 - P1b eight tracks'",
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
            item="T553P1b",
            risk_reason=(
                "t553 Part② — 타임코드 32(새)에 기존 시퀀스 8개를 트랙으로 배정(8트랙 재측정)"
            ),
            build_plan=build_plan,
            free_slots=[tc_path(TC_NO)],
            extra_notes=[
                "참조하는 시퀀스 226~233 은 기존 객체(RHYTHM PROBE v2/v3) — Store/수정하지 않는다.",
                "읽기 판정: Timecode 32/1 자식 9개(Marker+Track8), TARGET 순서 226..233.",
                "목적: MEASURED_MAX_TIMECODE_TRACKS=6(t549 보수적 상한,"
                " 실제 최대는 ①이 6개만 쟀다) 재확인 —"
                " LOVE ATTACK 실제 트랙 8개가 구조로 도는지.",
            ],
        )
    )
