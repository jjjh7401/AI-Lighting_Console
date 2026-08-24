"""t60 확정 프로브 — 한계는 **공백 정규화된 바이트**인가.

지금까지의 관측이 하나의 가설로 모인다.

  Fixture 101 x142            2026B  통과
  Fixture 101 x143            2040B  실패
  Group 1     x151            1548B  통과   (경계 아래라 무모순)
  Fixture 101 + 101 … x225    1396B  통과   (경계 아래라 무모순)
  x142 + 뒤 공백 40           2065B  통과   <- 바이트 상한과 모순
  x142, 사이를 공백 둘로      2167B  통과   <- 바이트 상한과 모순

모순되는 둘은 **공백만** 더한 것이다. 명령줄이 길이를 재기 전에 공백을
정규화(축약)한다면 두 줄의 실효 길이는 2025B 이고, 모든 관측이 한 번에 설명된다.

가르는 방법: **공백이 아닌 바이트**로 늘린다. 피연산자 하나를
`Fixture 101` -> `Fixture 101 Thru 106` 으로 바꾸면 9바이트가 늘고, 개수는 142로
고정된다. `Fixture 101 Thru 106` 은 t66 에서 검증된 유효 문법이다.

  9바이트씩 늘려 실패하면 -> 한계는 **공백 정규화된 바이트**다.
  계속 통과하면 -> 바이트가 아니다. 다른 축을 찾아야 한다.

저장하지 않는다. 픽스처·그룹 미접촉.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys

import server.safety.console as console_module
from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument

CLEAR = "ClearAll"
FABRICATED = "Zzzblah Foo 1"
SHORT = "Fixture 101"
LONG = "Fixture 101 Thru 106"
TOTAL_OPERANDS = 142
_WIRE: list[int] = []


class _Approve:
    def request_approval(self, request) -> bool:
        return True


def _spy_on() -> None:
    original = console_module.build_exec_request

    def _spy(request_id, command, **kwargs):
        line = original(request_id, command, **kwargs)
        _WIRE.append(len(line.encode("utf-8")))
        return line

    console_module.build_exec_request = _spy


def _mixed(long_count: int) -> str:
    units = [LONG] * long_count + [SHORT] * (TOTAL_OPERANDS - long_count)
    return " + ".join(units)


def _fire(gate, line: str) -> dict:
    before = len(_WIRE)
    decision = gate.screen([line, CLEAR])
    if not decision.cleared:
        return dict(observed=False, ok=None, wire=None, detail="심사 미통과")
    try:
        result = gate._execute_cleared(line)
    except Exception as error:  # noqa: BLE001
        return dict(
            observed=True,
            ok=False,
            wire=(_WIRE[before] if len(_WIRE) > before else None),
            detail=type(error).__name__,
        )
    sent = _WIRE[before] if len(_WIRE) > before else None
    with contextlib.suppress(Exception):
        gate._execute_cleared(CLEAR)
    return dict(observed=True, ok=bool(result.ok), wire=sent, detail=result.detail or "")


def main() -> int:
    args = sys.argv[1:]
    if "--approve" not in args:
        print("--approve 없이는 아무것도 쏘지 않는다")
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    add_listen_port_argument(parser)
    parser.add_argument("--approve", action="store_true")
    known, _rest = parser.parse_known_args(args)
    listen = known.listen_port

    _spy_on()
    stack = build_console_stack(
        send_host="127.0.0.1", send_port=8000, receive_port=listen, approval_port=_Approve()
    )
    rows = []
    try:
        gate = stack.gate
        control = _fire(gate, FABRICATED)
        control["long_count"] = -1
        rows.append(control)
        vehicle = _fire(gate, LONG)
        vehicle["long_count"] = -2
        rows.append(vehicle)
        for long_count in range(0, 7):
            row = _fire(gate, _mixed(long_count))
            row["long_count"] = long_count
            rows.append(row)
    finally:
        stack.stop()

    print(json.dumps(dict(rows=rows), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
