"""P6 — 타임코드 재생을 중간부터 시작.

새 번호: 타임코드 31(새), 트랙 하나가 기존 시퀀스 228 을 참조. 이벤트 1개를
5초 지점에 둔다(전체 길이 10초). t506/t516 은 전부 0초부터 Go 했다 — "중간부터"는
문법조차 전례가 없다(아래 참조).

🔴 미확인 — 문법 불명: 중간 지점에서 시작하는 명령(``Goto Time <n> Timecode 31``)의
전례를 찾으려고 아래 세 곳을 그렙했다 — **문법 전례가 없다**, 명령어 레퍼런스가
아니라 세 곳 모두 결과가 비어 있거나 다른 형태였다:

- `tc_probe.py` 독스트링이 이름 댄 `shared/resource/lib_plugins/systemtests/db/
  system_test_timecode_record.lua` — 로컬 설치본 `~/MALightingTechnology/
  gma3_2.4.2/.../system_test_timecode_record.lua` 에 실제로 존재한다(확인됨).
  그러나 이 파일은 Lua 내부 객체 API(`TEST.CmdSubTrack:Ptr(n)`, `TimecodeTokens.
  Goto` 등)를 테스트할 뿐 **콘솔 명령줄 문자열을 전혀 담고 있지 않다** —
  ``grep -n "Cmd(|GotoTime|'Goto "`` 결과 0건.
- 같은 폴더의 `system_test_timecode_generic.lua`·`system_test_timecode_store.lua`
  도 같은 그렙으로 0건.
- `docs/research/ma3-*` 전체에서 "중간 시작"/"scrub"/"mid-start"/"Goto Time" 류
  문서화된 전례 0건(14-musicsync-m3a-timecode-probe-run2.md 는 `Go`/`Go+`/
  `Pause`/`Toggle`/`Off` 만 실측 — 전부 0초 시작 전제).

그래서 ``Goto Time 5 Timecode 31`` 은 **문서화·실측 전례가 전혀 없는, 순수
추정 문법**이다. 콘솔이 거절하면 그 결과는 **「미확인 — 문법 불명」** 으로
적는다 — "중간 시작 기능 자체가 없다"는 더 강한 주장이라 쓰지 않는다(거절
하나로는 "그런 명령이 없다"와 "문법을 잘못 썼다"를 가를 수 없다).

PASS/FAIL: 재생 직후 ``CURSOR`` 읽기가 5.0 근방(왕복 지연 포함)에서 시작하는가 —
0.0 에서 시작하면 "중간 시작"이 아니라 "처음부터 재생, 커서만 빠르게 진행"일 수
있으므로 재생 시작 0.1초 내 CURSOR 값을 반드시 같이 적는다.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, tc_path  # noqa: E402

TC_NO = 31
REF_SEQ = 228
EVENT_AT = 5


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "tc_setup",
            [
                f"Store Timecode {TC_NO}",
                f"Set Timecode {TC_NO} Property 'Name' 'LDBEAT M1 - P6 mid-start'",
                f"Set Timecode {TC_NO} Property 'Duration' 10 'AutoStop' 0",
                f"Store Timecode {TC_NO}.1",
                f"Assign Sequence {REF_SEQ} At Timecode {TC_NO}.1.1",
                f"Store Type 'CmdSubTrack' Timecode {TC_NO}.1.1.1",
                f"cd Timecode {TC_NO}.1.1.1.1",
                f"Store Property 'Time' {EVENT_AT} 'AbsTime' {EVENT_AT} 'Token' 'Go+'",
                "cd root",
            ],
        ),
        # 🔴 미확인 — 문법 불명(전례 0건, 독스트링의 그렙 근거 참조). 거절되면
        # 「미확인 — 문법 불명」으로 적는다. 「중간 시작 기능 없음」으로 쓰지 않는다.
        ("goto_mid", [f"Goto Time {EVENT_AT} Timecode {TC_NO}"]),
        ("play", [f"Go Timecode {TC_NO}"]),
        ("release", [f"Off Timecode {TC_NO}", f"Off Sequence {REF_SEQ}"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P6",
            risk_reason="t531 M1 P6 — 타임코드 31(새), 중간(5초) 시작 미측정 문법 시험",
            build_plan=build_plan,
            free_slots=[tc_path(TC_NO)],
            extra_notes=[
                "`Goto Time <n> Timecode <n>` 은 문서화·실측 전례 0건(그렙 근거: 독스트링).",
                "거절 시 기록 문구는 반드시 '미확인 — 문법 불명' — '중간 시작 기능 없음' 금지.",
                "읽기 판정: play 직후 0.1초 내 CURSOR 값.",
            ],
        )
    )
