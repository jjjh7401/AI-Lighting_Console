"""t60 마지막 판별자 — 뒤 공백이 잘리는가, 아니면 한계가 바이트가 아닌가.

전수 훑기는 한 실행 안에서 깨끗한 경계를 냈다(전선 2026B 통과 / 2040B 실패).
그런데 142개 뒤에 공백 40바이트를 붙여 2065B 로 만든 줄은 **통과했다.** 둘이
동시에 참이려면, 뒤 공백이 길이를 재는 단계 앞에서 **잘려야** 한다.

가르는 방법: 같은 분량의 공백을 **줄 가운데** 넣는다. 피연산자 사이를
`" +  "`(공백 둘)로 이으면 의미는 그대로이고 길이만 자란다. 가운데 공백은
뒤 공백처럼 잘릴 수 없다.

  실패하면  -> 뒤 공백이 잘렸던 것이고, 한계는 **바이트**다.
  통과하면  -> 한계는 바이트가 아니다. 뒤/가운데 공백 둘 다 안 세는 무언가다.

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


def _fire(gate, label: str, line: str) -> dict:
    before = len(_WIRE)
    decision = gate.screen([line, CLEAR])
    if not decision.cleared:
        return dict(label=label, observed=False, ok=None, wire=None, detail="심사 미통과")
    try:
        result = gate._execute_cleared(line)
    except Exception as error:  # noqa: BLE001
        return dict(
            label=label,
            observed=True,
            ok=False,
            wire=(_WIRE[before] if len(_WIRE) > before else None),
            detail=type(error).__name__,
        )
    sent = _WIRE[before] if len(_WIRE) > before else None
    with contextlib.suppress(Exception):
        gate._execute_cleared(CLEAR)
    return dict(
        label=label, observed=True, ok=bool(result.ok), wire=sent, detail=result.detail or ""
    )


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
        rows.append(_fire(gate, "C0 날조 대조군", FABRICATED))
        rows.append(_fire(gate, "C1 가운데 공백 수단", "Fixture 101 +  Fixture 101"))
        rows.append(_fire(gate, "A 142개 기준선", " + ".join(["Fixture 101"] * 142)))
        rows.append(
            _fire(gate, "B 142개 + 뒤 공백 40", " + ".join(["Fixture 101"] * 142) + " " * 40)
        )
        rows.append(_fire(gate, "C 142개 + 가운데 공백", " +  ".join(["Fixture 101"] * 142)))
    finally:
        stack.stop()

    by = dict((r["label"], r) for r in rows)
    a = by["A 142개 기준선"]
    b = by["B 142개 + 뒤 공백 40"]
    c = by["C 142개 + 가운데 공백"]
    if by["C0 날조 대조군"].get("ok") is not False:
        verdict = "채널 불신 — 날조 대조군이 성공했다"
    elif by["C1 가운데 공백 수단"].get("ok") is not True:
        verdict = "수단 무효 — 콘솔이 가운데 공백을 거절한다"
    elif not a.get("ok"):
        verdict = "기준선 실패 — 재측정 필요"
    elif b.get("ok") and not c.get("ok"):
        verdict = "뒤 공백은 잘린다 — 한계는 **바이트**다"
    elif b.get("ok") and c.get("ok"):
        verdict = "한계는 바이트가 아니다 — 공백은 위치와 무관하게 안 세어진다"
    else:
        verdict = "뒤 공백도 실패 — 앞선 통과 관측과 어긋난다. 재측정 필요"
    print(json.dumps(dict(rows=rows, verdict=verdict), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
