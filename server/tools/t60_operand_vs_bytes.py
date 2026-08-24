"""t60 판별자 — exec 상한은 **바이트인가 피연산자 개수인가**.

앞선 두 측정이 서로 어긋난다.

  이분 탐색: `Fixture 101` **142개** (전선 2026B) 통과 / **143개** (2040B) 실패
  미세 조정: 142개 뒤에 공백 **40바이트**를 더해 전선 2065B 로 만들어도 통과

바이트가 한계라면 2065B 가 통과할 수 없다. 그러므로 한계는 바이트가 아니거나,
뒤 공백이 전선 어딘가에서 잘려 실제로는 2025B 만 도달한 것이다. 둘은 다른
결론이고 처방도 다르다.

가르는 방법: **피연산자 개수를 고정하고 바이트만 크게 늘린다.**
`Fixture 101 Thru 101` 은 `Fixture 101` 과 같은 대상을 고르지만 9바이트 길다.
이것을 142개 이어 붙이면 피연산자는 142개 그대로, 바이트는 약 1.5배가 된다.

  통과하면  -> 한계는 **개수**다. 바이트 검사를 붙이는 것은 틀린 처방이다.
  실패하면  -> 한계는 **바이트**다. 앞선 공백 통과는 공백이 잘렸다는 뜻이다.

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
GATE_BLOCK_MARK = "not cleared by the safety gate"
FABRICATED_COMMAND = "Zzzblah Foo 1"

_WIRE_BYTES: list[int] = []


class _AlwaysApprove:
    def request_approval(self, request) -> bool:
        return True


def _install_wire_spy() -> None:
    original = console_module.build_exec_request

    def _spy(request_id, command, **kwargs):
        line = original(request_id, command, **kwargs)
        _WIRE_BYTES.append(len(line.encode("utf-8")))
        return line

    console_module.build_exec_request = _spy


def _fire(gate, label: str, line: str) -> dict:
    before = len(_WIRE_BYTES)
    decision = gate.screen([line, CLEAR])
    if not decision.cleared:
        return dict(label=label, observed=False, ok=None, detail="심사 미통과")
    try:
        result = gate._execute_cleared(line)
    except Exception as error:  # noqa: BLE001
        return dict(
            label=label,
            observed=True,
            ok=False,
            wire_bytes=(_WIRE_BYTES[before] if len(_WIRE_BYTES) > before else None),
            detail=type(error).__name__ + ": " + str(error),
        )
    detail = result.detail or ""
    if GATE_BLOCK_MARK in detail:
        return dict(label=label, observed=False, ok=None, detail=detail)
    sent = _WIRE_BYTES[before] if len(_WIRE_BYTES) > before else None
    with contextlib.suppress(Exception):
        gate._execute_cleared(CLEAR)
    return dict(
        label=label,
        observed=True,
        ok=bool(result.ok),
        operands=line.count(" + ") + 1,
        wire_bytes=sent,
        detail=detail,
    )


def main(argv: list[str] | None = None) -> int:
    if "--approve" not in (argv if argv is not None else sys.argv[1:]):
        print("--approve 없이는 아무것도 쏘지 않는다")
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    add_listen_port_argument(parser)
    parser.add_argument("--approve", action="store_true")
    known, _rest = parser.parse_known_args(argv if argv is not None else sys.argv[1:])
    listen = known.listen_port

    _install_wire_spy()
    stack = build_console_stack(
        send_host="127.0.0.1", send_port=8000, receive_port=listen, approval_port=_AlwaysApprove()
    )
    rows = []
    try:
        gate = stack.gate
        rows.append(_fire(gate, "C0 날조 대조군", FABRICATED_COMMAND))
        rows.append(_fire(gate, "C1 Thru 수단 대조군", "Fixture 101 Thru 101"))
        rows.append(_fire(gate, "A 짧은 피연산자 142개", " + ".join(["Fixture 101"] * 142)))
        rows.append(_fire(gate, "B 짧은 피연산자 143개", " + ".join(["Fixture 101"] * 143)))
        rows.append(_fire(gate, "C 긴 피연산자 142개", " + ".join(["Fixture 101 Thru 101"] * 142)))
    finally:
        stack.stop()

    by = dict((r["label"], r) for r in rows)
    control_ok = by["C0 날조 대조군"].get("ok") is False
    a = by["A 짧은 피연산자 142개"]
    b = by["B 짧은 피연산자 143개"]
    c = by["C 긴 피연산자 142개"]
    if not control_ok:
        verdict = "채널 불신 — 날조 대조군이 성공했다"
    elif not (a.get("ok") and b.get("ok") is False):
        verdict = "기준선 재현 실패 — 142 통과 / 143 실패가 이 실행에서 안 나왔다"
    elif c.get("ok"):
        verdict = "한계는 **개수**다 — 피연산자 142개는 바이트가 1.5배여도 통과한다"
    else:
        verdict = "한계는 **바이트**다 — 개수가 같아도 길면 실패한다"
    print(json.dumps(dict(rows=rows, verdict=verdict), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
