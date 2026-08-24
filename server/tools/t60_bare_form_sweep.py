"""t60 확정 프로브 — 한계가 개수인지 바이트인지 **못 박는다**.

앞 판별자에서 한계가 바이트가 아님이 나왔다(전선 2167B 통과 / 2040B 실패).
남은 가설은 **피연산자 개수**다. 그것을 확정하려면 같은 개수를 **훨씬 짧은
바이트**로 쏘아야 한다.

수단: 규칙서 `31_choreography_patterns.md:28` 이 실기 검증한 목록 문법
`Fixture 101 + 101 + 101 …`. 키워드가 한 번뿐이라 피연산자 하나가 6바이트다
(반복 키워드형은 14바이트). 143개면 약 870B — 어떤 바이트 상한에도 못 닿는다.

  143개가 실패하면  -> 한계는 **개수**다. 바이트 검사는 틀린 처방이다.
  143개가 통과하면  -> 개수도 아니다. 두 형태가 다른 무언가로 갈린다.

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


def _bare(operands: int) -> str:
    """`Fixture 101 + 101 + …` — 규칙서 검증 목록 문법."""
    return "Fixture " + " + ".join(["101"] * operands)


def _repeated(unit: str, operands: int) -> str:
    """`<unit> + <unit> + …` — 키워드를 매번 반복하는 형태."""
    return " + ".join([unit] * operands)


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
        control["operands"] = 0
        rows.append(control)
        low, high = 138, 152
        for index, token in enumerate(args):
            if token == "--range":
                low, high = (int(part) for part in args[index + 1].split(","))
        for operands in range(low, high):
            unit = None
            for index, token in enumerate(args):
                if token == "--unit":
                    unit = args[index + 1]
            line = _bare(operands) if unit is None else _repeated(unit, operands)
            row = _fire(gate, line)
            row["operands"] = operands
            rows.append(row)
    finally:
        stack.stop()

    print(json.dumps(dict(rows=rows), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
