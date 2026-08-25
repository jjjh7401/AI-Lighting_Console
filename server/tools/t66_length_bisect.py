"""t66 — 서버→콘솔 명령줄의 **요청 방향** 바이트 상한을 잰다.

검증 도구다 — 제품 코드가 아니다. 저장하지 않는다: 선택 한 줄 + `ClearAll`.
**픽스처는 건드리지 않는다** (콘솔의 패치 86대는 미저장 유일본이다).

왜 새로 재는가. 이 저장소가 가진 `[1200, 1208)` 는 **회신 방향** payload 절단
경계다(`docs/runbooks/fake-real-parity-method.md` §3, 같은 문서 §4 가 스스로
"이 방법은 쓰기 경로를 못 닫는다"고 적었다). `MAX_PLUGIN_CALL_BYTES = 2048` 과
`DEFAULT_LINE_BYTE_BUDGET = 2000` 은 프레이밍 상한에서 역산한 값이지 실측이
아니다. 요청 방향 상한은 **한 번도 안 잰 값이다.**

방법. 실패한 그 형태 그대로 — 실재 FID 앞 n개로
`Fixture a + Fixture b + …` 를 만들어(86개 = 1201B) n 을 이분한다. 파딩이나
인공 문자열을 쓰지 않는 이유는, 상한이 바이트가 아니라 토큰 수·피연산자 수에
있을 수도 있기 때문이다 — 실패한 형태를 그대로 키워야 그 구분이 관측된다.

각 발사는 게이트 심사를 거치고, cleared 가 아니면 **관측으로 세지 않는다**
(게이트 차단과 콘솔 거절을 뭉개면 판정이 공허해진다 — 판별자 1차 발사의 교훈).
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import sys
from pathlib import Path

from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

CLEAR = "ClearAll"
GATE_BLOCK_MARK = "not cleared by the safety gate"

#: 날조 대조군. 순수 쓰레기라 **실패가 정답**이다.
FABRICATED_COMMAND = "Zzzblah Foo 1"


class _AlwaysApprove:
    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return True


def _load_fids(patch_csv: Path) -> list[int]:
    fids: list[int] = []
    with patch_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            raw = (row.get("FID") or "").strip()
            if raw.isdigit():
                fids.append(int(raw))
    return sorted(set(fids))


def _chain(fids: list[int]) -> str:
    """실패한 그 형태 — 반복 키워드형. 압축형이 아니다."""
    return " + ".join("Fixture " + str(fid) for fid in fids)


def _fire(gate, line: str) -> dict:
    size = len(line.encode("utf-8"))
    decision = gate.screen([line, CLEAR])
    if not decision.cleared:
        return dict(
            bytes=size,
            observed=False,
            ok=None,
            detail="게이트 심사 미통과: " + decision.status,
        )
    try:
        result = gate._execute_cleared(line)
    except Exception as error:  # noqa: BLE001
        return dict(bytes=size, observed=False, ok=None, detail=str(error))
    detail = result.detail or ""
    if GATE_BLOCK_MARK in detail:
        return dict(bytes=size, observed=False, ok=None, detail=detail)
    # 닫기 실패는 관측을 무효화하지 않는다 — 선택은 이미 답을 받았다.
    with contextlib.suppress(Exception):
        gate._execute_cleared(CLEAR)
    return dict(bytes=size, observed=True, ok=bool(result.ok), detail=detail)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch-csv", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    add_listen_port_argument(parser)
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args(argv)

    fids = _load_fids(args.patch_csv)
    full = _chain(fids)
    out = dict(
        fid_count=len(fids),
        full_line_bytes=len(full.encode("utf-8")),
        fired=bool(args.approve),
    )
    if not args.approve:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    approval = _AlwaysApprove()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=approval,
    )
    trace = []
    try:
        gate = stack.gate
        control = _fire(gate, FABRICATED_COMMAND)
        out["fabricated_control"] = control

        low, high = 1, len(fids)
        results = dict()

        def probe(n: int) -> dict:
            if n not in results:
                row = _fire(gate, _chain(fids[:n]))
                row["n"] = n
                results[n] = row
                trace.append(row)
            return results[n]

        top = probe(high)
        bottom = probe(low)
        if top["observed"] and top["ok"]:
            out["boundary"] = "상한 없음 — 전체 " + str(high) + "개가 통과했다"
        elif not (bottom["observed"] and bottom["ok"]):
            out["boundary"] = "최소 단위조차 실패 — 길이 축이 아니다"
        else:
            while low + 1 < high:
                mid = (low + high) // 2
                row = probe(mid)
                if row["observed"] and row["ok"]:
                    low = mid
                else:
                    high = mid
            out["boundary"] = dict(
                last_ok_n=low,
                last_ok_bytes=results[low]["bytes"],
                first_fail_n=high,
                first_fail_bytes=results[high]["bytes"],
                first_fail_detail=results[high]["detail"],
            )
    finally:
        stack.stop()

    out["trace"] = sorted(trace, key=lambda row: row.get("n", 0))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
