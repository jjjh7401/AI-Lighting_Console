"""t60 — exec 경로 명령줄의 **실제 상한**을 잰다. 없으면 없다고 적는다.

검증 도구다 — 제품 코드가 아니다. 저장하지 않는다: 선택 한 줄 + `ClearAll`.
**픽스처와 그룹은 건드리지 않는다** (콘솔의 패치 86 + 그룹 18 은 미저장 유일본).

왜 재는가. `server/bridge/protocol.py` 의 `_validate_plugin_call_budget` 은
introspect(:217)·props(:233) 에만 걸려 있고 exec(:237)에는 없다. 그런데 그
검사기의 기준 `MAX_PLUGIN_CALL_BYTES = 2048` 은 **프로토콜이 스스로 정한
프레이밍 상한이지 콘솔이 받아 주는 실측 상한이 아니다**(t66). 그리고 t66 의
요청 방향 이분 탐색은 1201B 까지 상한을 못 찾았다. 그러므로 「exec 에 2048
검사를 붙인다」가 옳은 처방인지조차 아직 모른다 — 먼저 **얼마까지 통과하는지**
를 재고, 그 값이 나온 뒤에 검사를 붙일지 정한다.

**상한이 안 나오는 것도 결과다.** 없는 상한을 지키는 검사는 공허하고, 프레이밍이
바뀌면 오히려 정상 명령을 막는다.

## 길이를 늘리는 수단

같은 픽스처를 반복 선택한다 — `Fixture 101 + Fixture 101 + …`. 의미는 픽스처
101 하나를 고르는 것이라 콘솔 상태에 남는 게 없고, 길이만 선형으로 자란다.
실재하지 않는 FID 나 인공 문자열로 늘리면 **길이 때문에 실패한 것과 대상이
없어서 실패한 것을 못 가른다.**

수단 자체가 유효한지도 잰다(C1) — 반복 피연산자를 콘솔이 거절한다면 이 탐색
전체가 무효다.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys

import server.safety.console as console_module
from server.safety.bootstrap import build_console_stack

# `server/tools/` 는 OSC 송신면(`server.bridge`)을 임포트하면 안 된다 —
# REQ-MVP-029 단일 초크포인트, `test_architecture.py` 가 전수로 막는다. 래핑
# 바이트가 필요하면 아래 스파이가 **실제 나간 값**을 준다. 계산해서 추정하지
# 마라. 그 추정이 틀렸다는 것이 이 카드의 발견 중 하나다(요청 id 길이가 변한다).

CLEAR = "ClearAll"
GATE_BLOCK_MARK = "not cleared by the safety gate"

#: 날조 대조군. 순수 쓰레기라 **실패가 정답**이다.
FABRICATED_COMMAND = "Zzzblah Foo 1"

#: 반복 수단의 최소형. 이것이 실패하면 탐색 수단 자체가 무효다.
VEHICLE_CONTROL = "Fixture 101 + Fixture 101"

#: 탐색 상한. 이 수를 지어내지 않고 근거를 적는다 — UDP 데이터그램의 이론
#: 최대(65507B)를 넘는 지점까지 훑는다. 여기까지 통과하면 「이 수단으로는
#: 상한을 못 찾았다」가 결과다.
MAX_REPEATS = 4600


class _AlwaysApprove:
    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return True


def _line(repeats: int) -> str:
    """`Fixture 101` 을 repeats 번 이어 붙인 선택 줄."""
    return " + ".join(["Fixture 101"] * repeats)


#: 실제로 전선에 나간 줄의 바이트. `build_exec_request` 를 **관측만** 하는
#: 스파이가 채운다(원본을 그대로 불러 그 결과를 돌려주므로 동작은 안 바뀐다).
#:
#: 왜 필요한가: 요청 id 는 `f"{prefix}-{counter}"` 라 **길이가 변한다**
#: (`server/safety/console.py:245`). 고정 id 로 계산한 값은 추정치이고, 카운터가
#: 도는 동안 실제 길이는 조금씩 자란다. 상한을 바이트로 말하려면 추정이 아니라
#: 나간 값을 세야 한다.
_WIRE_BYTES: list[int] = []


def _install_wire_spy() -> None:
    original = console_module.build_exec_request

    def _spy(request_id, command, **kwargs):
        line = original(request_id, command, **kwargs)
        _WIRE_BYTES.append(len(line.encode("utf-8")))
        return line

    console_module.build_exec_request = _spy


def _fire(gate, line: str) -> dict:
    """한 줄을 게이트 심사에 걸고, 통과하면 발화한다.

    심사 미통과는 **관측이 아니다** — 콘솔이 그 줄을 본 적이 없다. 그것을
    「실패」로 세면 판정이 공허해진다(t66 판별자 1차 발사의 교훈).
    """
    raw = len(line.encode("utf-8"))
    before = len(_WIRE_BYTES)
    decision = gate.screen([line, CLEAR])
    if not decision.cleared:
        return dict(
            raw_bytes=raw,
            observed=False,
            ok=None,
            detail="게이트 심사 미통과: " + decision.status,
        )
    try:
        result = gate._execute_cleared(line)
    except Exception as error:  # noqa: BLE001 — 거절 사유를 그대로 싣는다
        return dict(
            raw_bytes=raw,
            wire_bytes=(_WIRE_BYTES[before] if len(_WIRE_BYTES) > before else None),
            observed=True,
            ok=False,
            detail=type(error).__name__ + ": " + str(error),
        )
    detail = result.detail or ""
    if GATE_BLOCK_MARK in detail:
        return dict(raw_bytes=raw, observed=False, ok=None, detail=detail)
    sent = _WIRE_BYTES[before] if len(_WIRE_BYTES) > before else None
    with contextlib.suppress(Exception):
        gate._execute_cleared(CLEAR)
    return dict(
        raw_bytes=raw,
        wire_bytes=sent,
        observed=True,
        ok=bool(result.ok),
        detail=detail,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    parser.add_argument(
        "--listen-port",
        type=int,
        required=True,
        help="회신 수신 포트. 기본값 없음 — 틀린 포트의 침묵을 응답기 사망으로 오독한다",
    )
    parser.add_argument("--max-repeats", type=int, default=MAX_REPEATS)
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args(argv)

    top = _line(args.max_repeats)
    out = dict(
        max_repeats=args.max_repeats,
        max_raw_bytes=len(top.encode("utf-8")),
        fired=bool(args.approve),
    )
    if not args.approve:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    _install_wire_spy()
    approval = _AlwaysApprove()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=approval,
    )
    trace: list[dict] = []
    try:
        gate = stack.gate

        # 1) 날조 대조군 — 채널이 아무 말에나 ok 를 내면 그 뒤 관측은 전부 무효다.
        control = _fire(gate, FABRICATED_COMMAND)
        out["fabricated_control"] = control
        if not control["observed"]:
            out["verdict"] = "하네스 공허 — 대조군이 콘솔에 닿지 않았다"
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 2
        if control["ok"]:
            out["verdict"] = "채널 불신 — 날조 대조군이 성공했다. 아래 관측은 증거가 아니다"
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 2

        # 2) 수단 대조군 — 반복 피연산자를 콘솔이 받는가.
        vehicle = _fire(gate, VEHICLE_CONTROL)
        out["vehicle_control"] = vehicle
        if not (vehicle["observed"] and vehicle["ok"]):
            out["verdict"] = "수단 무효 — 반복 선택형을 콘솔이 거절했다. 다른 수단이 필요하다"
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 3

        results: dict[int, dict] = dict()

        def probe(n: int) -> dict:
            if n not in results:
                row = _fire(gate, _line(n))
                row["repeats"] = n
                results[n] = row
                trace.append(row)
            return results[n]

        low, high = 1, args.max_repeats
        bottom = probe(low)
        ceiling = probe(high)
        if not (bottom["observed"] and bottom["ok"]):
            out["verdict"] = "최소 단위조차 실패 — 길이 축이 아니다"
        elif ceiling["observed"] and ceiling["ok"]:
            out["verdict"] = (
                "상한 미발견 — 반복 "
                + str(high)
                + "회 ("
                + str(ceiling["raw_bytes"])
                + "B 원문 / "
                + str(ceiling["wire_bytes"])
                + "B 전선) 까지 통과했다"
            )
        else:
            while low + 1 < high:
                mid = (low + high) // 2
                row = probe(mid)
                if row["observed"] and row["ok"]:
                    low = mid
                else:
                    high = mid
            out["verdict"] = "상한 발견"
            out["boundary"] = dict(
                last_ok_repeats=low,
                last_ok_raw_bytes=results[low]["raw_bytes"],
                last_ok_wire_bytes=results[low].get("wire_bytes"),
                first_fail_repeats=high,
                first_fail_raw_bytes=results[high]["raw_bytes"],
                first_fail_wire_bytes=results[high].get("wire_bytes"),
                first_fail_observed=results[high]["observed"],
                first_fail_detail=results[high]["detail"],
            )
    finally:
        stack.stop()

    out["trace"] = sorted(trace, key=lambda row: row.get("repeats", 0))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
