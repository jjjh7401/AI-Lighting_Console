"""기대 응답기 버전의 단일 출처 + 보고된 버전의 분류 (REQ-READBACK2-002/004).

`console/lua/copilot_responder.lua` 의 `VERSION` 에 고정된 상수 하나가 이 모듈에
있고, 서버 어디에도 두 번째 출처가 없다. 테스트는 리터럴을 다시 적는 대신 그
Lua 파일에서 값을 읽어 이 상수와 대조한다(AC-READBACK2-002).

분류가 **두 갈래로 갈리는 이유**는 운영자가 취할 행동이 다르기 때문이다
(REQ-READBACK2-004): 기대보다 낮은 버전은 **재임포트**로 끝나지만, 파싱할 수
없는 값이나 기대보다 **높은** 값은 무엇이 도는지 모른다는 뜻이므로 **조사**가
먼저다. 같은 배너에 담으면 사유를 거짓말한다.

「보고되지 않음」(`None`)은 세 번째 갈래이고 의도적으로 **차단하지 않는다**:
`pong` 에 `version` 이 없는 회신은 이 저장소의 오프라인 하네스가 실제로 보내는
형태이고(`server/tests/test_safety_console.py` 의 `_echo_send`,
`test_responder_import_gate.py`, `test_deploy_transport.py`,
`test_safety_e2e_audit.py` — 2026-09-04 실측), 버전을 재지 않는 호출자와 버전
없는 응답기를 이 채널로는 구별할 수 없다. 구별할 수 없는 것을 차단 사유로 쓰면
재지 않은 것을 잰 것처럼 보고하게 된다. 이 구멍은 열린 채로 남고 완료 보고의
미검증 절에 적힌다.
"""

from __future__ import annotations

import re

# @MX:NOTE: [AUTO] cross-file version pin. This literal is the ONLY server-side
# source for the expected responder version; its counterpart lives in
# `console/lua/copilot_responder.lua` (`VERSION`), which this SPEC may only read.
# @MX:REASON: REQ-READBACK2-002 — a second source would let the two drift
# silently. The test reads the Lua file instead of restating the literal.
# @MX:SPEC: SPEC-COPILOT-READBACK-002
#: 기대 응답기 버전. `console/lua/copilot_responder.lua` 의 `VERSION` 에 고정된
#: 유일한 서버측 출처다 — 여기 말고 어디에도 이 리터럴을 적지 않는다.
#: 001 이 응답기를 1.6.4 로 올리면 바뀌는 것은 이 한 줄뿐이다.
EXPECTED_RESPONDER_VERSION = "1.6.4"

#: 분류 결과. status 문자열이 아니라 **판정**이며, health state 로의 사상은
#: `server/safety/monitor.py` 가 소유한다.
VERSION_OK = "ok"
VERSION_LOW = "low"
VERSION_UNRECOGNIZED = "unrecognized"
VERSION_UNREPORTED = "unreported"

_NUMERIC_VERSION = re.compile(r"^\d+(?:\.\d+)*$")


def parse_version(reported: str | None) -> tuple[int, ...] | None:
    """`"1.6.3"` → `(1, 6, 3)`. 숫자-점 형태가 아니면 None(파싱 불가)."""
    if reported is None:
        return None
    text = str(reported).strip()
    if not _NUMERIC_VERSION.match(text):
        return None
    return tuple(int(part) for part in text.split("."))


def _pad(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)), right + (0,) * (width - len(right))


def classify_version(reported: str | None, *, expected: str = EXPECTED_RESPONDER_VERSION) -> str:
    """보고된 버전을 네 갈래로 판정한다 — 술어의 경계 바깥까지 전부 덮는다.

    낮음 / 같음 / 높음 / 파싱 불가 / 빈 문자열 / 부재를 각각 답한다. 빈 문자열과
    파싱 불가는 같은 갈래(`unrecognized`)지만 **부재**(`None`)는 다른
    갈래(`unreported`)이며, 모듈 docstring 의 이유로 차단하지 않는다.
    """
    if reported is None:
        return VERSION_UNREPORTED
    parsed = parse_version(reported)
    if parsed is None:
        return VERSION_UNRECOGNIZED
    expected_parsed = parse_version(expected)
    if expected_parsed is None:  # 상수 자체가 깨진 경우 — 조사 대상이다
        return VERSION_UNRECOGNIZED
    left, right = _pad(parsed, expected_parsed)
    if left == right:
        return VERSION_OK
    if left < right:
        return VERSION_LOW
    return VERSION_UNRECOGNIZED
