"""t60 후속 — exec 상한을 **바이트 단위**로 좁힌다.

`t60_exec_budget_bisect.py` 는 `Fixture 101` 반복으로 훑어 14바이트 간격의
괄호를 냈다(전선 2026 통과 / 2040 실패). 이 도구는 그 사이를 1바이트씩 좁힌다.

미세 조정 수단은 **뒤에 붙이는 공백**이다. 명령의 의미를 바꾸지 않으면서
길이만 1바이트씩 늘린다. 다만 「바꾸지 않을 것이다」는 가정이므로 **수단
대조군을 먼저 쏜다** — 짧은 줄에 공백을 붙여도 콘솔이 `OK` 를 내는지 본다.
거절하면 이 수단은 무효이고, 그때는 괄호를 그대로 남긴다(억지로 좁히지 않는다).

저장하지 않는다. 픽스처·그룹 미접촉.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys

import server.safety.console as console_module
from server.safety.bootstrap import build_console_stack

CLEAR = "ClearAll"
GATE_BLOCK_MARK = "not cleared by the safety gate"
FABRICATED_COMMAND = "Zzzblah Foo 1"
BASE_REPEATS = 142

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


def _line(repeats: int, pad: int) -> str:
    return " + ".join(["Fixture 101"] * repeats) + " " * pad


def _fire(gate, line: str) -> dict:
    before = len(_WIRE_BYTES)
    decision = gate.screen([line, CLEAR])
    if not decision.cleared:
        return dict(observed=False, ok=None, wire_bytes=None, detail="심사 미통과")
    try:
        result = gate._execute_cleared(line)
    except Exception as error:  # noqa: BLE001
        return dict(
            observed=True,
            ok=False,
            wire_bytes=(_WIRE_BYTES[before] if len(_WIRE_BYTES) > before else None),
            detail=type(error).__name__ + ": " + str(error),
        )
    detail = result.detail or ""
    if GATE_BLOCK_MARK in detail:
        return dict(observed=False, ok=None, wire_bytes=None, detail=detail)
    sent = _WIRE_BYTES[before] if len(_WIRE_BYTES) > before else None
    with contextlib.suppress(Exception):
        gate._execute_cleared(CLEAR)
    return dict(observed=True, ok=bool(result.ok), wire_bytes=sent, detail=detail)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--max-pad", type=int, default=40)
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args(argv)

    if not args.approve:
        print(json.dumps(dict(base_repeats=BASE_REPEATS, fired=False), ensure_ascii=False))
        return 0

    _install_wire_spy()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=_AlwaysApprove(),
    )
    out = dict(base_repeats=BASE_REPEATS, fired=True)
    trace: list[dict] = []
    try:
        gate = stack.gate
        control = _fire(gate, FABRICATED_COMMAND)
        out["fabricated_control"] = control
        if not control["observed"] or control["ok"]:
            out["verdict"] = "채널 불신 또는 하네스 공허 — 아래는 증거가 아니다"
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 2

        pad_control = _fire(gate, "Fixture 101   ")
        out["pad_vehicle_control"] = pad_control
        if not (pad_control["observed"] and pad_control["ok"]):
            out["verdict"] = "미세 조정 수단 무효 — 콘솔이 뒤 공백을 거절한다. 괄호를 그대로 둔다"
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 3

        results: dict[int, dict] = dict()

        def probe(pad: int) -> dict:
            if pad not in results:
                row = _fire(gate, _line(BASE_REPEATS, pad))
                row["pad"] = pad
                results[pad] = row
                trace.append(row)
            return results[pad]

        low, high = 0, args.max_pad
        bottom = probe(low)
        top = probe(high)
        if not (bottom["observed"] and bottom["ok"]):
            out["verdict"] = "기준선이 실패했다 — 재측정 필요"
        elif top["observed"] and top["ok"]:
            out["verdict"] = (
                "패딩 " + str(args.max_pad) + "바이트를 더해도 통과 — 이 범위에 경계가 없다"
            )
        else:
            while low + 1 < high:
                mid = (low + high) // 2
                row = probe(mid)
                if row["observed"] and row["ok"]:
                    low = mid
                else:
                    high = mid
            out["verdict"] = "상한 확정"
            out["ceiling"] = dict(
                last_ok_wire_bytes=results[low]["wire_bytes"],
                first_fail_wire_bytes=results[high]["wire_bytes"],
                first_fail_detail=results[high]["detail"],
            )
    finally:
        stack.stop()

    out["trace"] = sorted(trace, key=lambda row: row.get("pad", 0))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
