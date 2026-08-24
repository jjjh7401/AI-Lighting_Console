"""t60 — 경계 부근을 한 실행 안에서 훑는다. 이분이 아니라 전수다.

앞선 관측이 1바이트 폭에서 엇갈렸다(전선 2039 통과 / 2040 실패). 이분 탐색은
경계 좌우를 **다른 실행**에서 본 것이라, 요청 id 길이가 달라지며 전선 바이트가
1씩 흔들렸다. 그래서 여기서는 한 실행 안에서 연속 구간을 전수로 쏜다.

저장하지 않는다. 픽스처·그룹 미접촉.
"""

from __future__ import annotations

import contextlib
import json
import sys

import server.safety.console as console_module
from server.safety.bootstrap import build_console_stack

CLEAR = "ClearAll"
FABRICATED_COMMAND = "Zzzblah Foo 1"
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
    listen = 9005
    for index, token in enumerate(args):
        if token == "--listen-port":
            listen = int(args[index + 1])

    _spy_on()
    stack = build_console_stack(
        send_host="127.0.0.1", send_port=8000, receive_port=listen, approval_port=_Approve()
    )
    rows = []
    try:
        gate = stack.gate
        control = _fire(gate, FABRICATED_COMMAND)
        control["repeats"] = 0
        rows.append(control)
        for repeats in range(138, 152):
            row = _fire(gate, " + ".join(["Fixture 101"] * repeats))
            row["repeats"] = repeats
            rows.append(row)
    finally:
        stack.stop()

    print(json.dumps(dict(rows=rows), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
