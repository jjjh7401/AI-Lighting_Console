"""t66 판별자 — 「Illegal object」의 원인이 바이트인가 프로그래밍 목적지인가.

검증 도구다 — 제품 코드가 아니다. `server/tools/lxseq_groups_e2e.py` 의 형태를
승계한다: 실포트 조립(`build_console_stack`), 우회 배선 0, `--approve` 없으면
콘솔에 아무것도 닿지 않는다.

쇼파일에 아무것도 저장하지 않는다 — 선택만 하고 `ClearAll` 로 닫는다.
**픽스처는 건드리지 않는다** (콘솔의 패치 86대는 미저장 유일본이다).

발사 순서 (A 먼저, B 나중 — B 를 먼저 쏘면 바뀐 목적지가 A 에 남는다):

  C0 `Zzzblah Foo 1`                       날조 대조군 → 기대: 실패
  A  `Fixture 101 Thru 106` + `ClearAll`   20B         → 기대: Illegal object
  B  `ChangeDestination Root` + 선택 + `ClearAll`      → 기대: ok

**공허 방지가 이 도구의 핵심이다.** 1차 발사에서 이 하네스는 게이트 승인 없이
`execution_port.execute` 를 직접 불러 6줄 전부가 `blocked: command was not
cleared by the safety gate` 로 떨어졌는데, 「A 실패 · B 실패」를 그대로
「목적지 아님」으로 판정했다. 콘솔엔 아무것도 안 닿았으므로 그 판정은 증거가
아니라 공허였다. 그래서 지금은 **게이트 심사(`screen`)를 먼저 거치고, 심사에서
cleared 가 아닌 줄이 하나라도 있으면 판정 대신 「하네스 공허」를 낸다.**
"""

from __future__ import annotations

import argparse
import json
import sys

from server.safety.bootstrap import build_console_stack
from server.tools.probe_preflight import add_listen_port_argument

#: exec 채널 날조 대조군. 순수 쓰레기라 **실패가 정답**이다.
FABRICATED_COMMAND = "Zzzblah Foo 1"

#: 20바이트. 어떤 바이트 상한에도 닿을 수 없는 크기다 — 그래서 이 한 발이
#: 콘솔에서 거절되면 원인은 길이가 아니다.
SHORT_SELECTION = "Fixture 101 Thru 106"

DESTINATION = "ChangeDestination Root"
CLEAR = "ClearAll"

#: 게이트가 콘솔 앞에서 막았을 때 `detail` 에 실리는 문구. 이것이 보이면
#: 콘솔은 그 줄을 본 적이 없다 — 관측이 아니라 공허다.
GATE_BLOCK_MARK = "not cleared by the safety gate"


class _AlwaysApprove:
    """번들 승인 통로. 사람이 계획을 읽고 `--approve` 로 부른다."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return True


def _fire_bundle(gate, commands: list[str]) -> dict:
    """한 번들을 게이트에 심사시키고, 통과한 줄만 발화한다.

    심사 결과와 발화 결과를 **따로** 싣는다 — 둘을 합치면 게이트가 막은 것과
    콘솔이 거절한 것이 같은 「실패」로 뭉개진다. 그 뭉갬이 1차 발사의 공허를
    만들었다.
    """
    decision = gate.screen(commands)
    screened = [
        dict(command=row.command, status=row.status, reasons=list(row.reasons))
        for row in decision.commands
    ]
    fired = []
    if decision.cleared:
        for command in commands:
            size = len(command.encode("utf-8"))
            try:
                result = gate._execute_cleared(command)
            except Exception as error:  # noqa: BLE001 — 거절 사유를 그대로 싣는다
                fired.append(
                    dict(
                        command=command,
                        bytes=size,
                        raised=type(error).__name__,
                        ok=False,
                        detail=str(error),
                    )
                )
                continue
            fired.append(
                dict(
                    command=command,
                    bytes=size,
                    raised=None,
                    ok=bool(result.ok),
                    detail=result.detail,
                )
            )
    return dict(
        commands=list(commands),
        screen_cleared=bool(decision.cleared),
        screen_status=decision.status,
        screened=screened,
        fired=fired,
    )


def _reached_console(arm: dict, command: str) -> tuple[bool, dict | None]:
    """이 줄이 실제로 콘솔까지 갔는가. 게이트 차단은 「갔다」가 아니다."""
    if not arm["screen_cleared"]:
        return False, None
    for row in arm["fired"]:
        if row["command"] == command:
            if GATE_BLOCK_MARK in (row["detail"] or ""):
                return False, row
            return True, row
    return False, None


def _verdict(control: dict, arm_a: dict, arm_b: dict) -> str:
    a_reached, a_row = _reached_console(arm_a, SHORT_SELECTION)
    b_sel_reached, b_row = _reached_console(arm_b, SHORT_SELECTION)
    c_reached, c_row = _reached_console(control, FABRICATED_COMMAND)

    if not (a_reached and b_sel_reached):
        return (
            "하네스 공허 — 선택 줄이 콘솔에 닿지 않았다(게이트 차단). "
            "이 실행의 어떤 실패도 콘솔에 대한 관측이 아니다"
        )
    if c_reached and c_row["ok"]:
        return "채널 불신 — 날조 대조군이 성공했다. 아래 관측은 증거가 아니다"

    a_failed = not a_row["ok"]
    b_ok = bool(b_row["ok"])
    if a_failed and b_ok:
        return "목적지 가설 확정 (A 실패 · B 성공) — 바이트 아님"
    if a_failed and not b_ok:
        return "목적지 아님 — 둘 다 콘솔에서 실패. 바이트 축으로 넘어간다"
    if not a_failed and b_ok:
        return "목적지도 바이트도 아님 — A 가 성공했다. 길이 축에서 1201 재현 필요"
    return "설명 불가 조합 — A 성공 · B 실패. 재측정 필요"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--approve",
        action="store_true",
        help="없으면 아무것도 쏘지 않고 계획만 출력한다",
    )
    args = parser.parse_args(argv)

    control_bundle = [FABRICATED_COMMAND]
    bundle_a = [SHORT_SELECTION, CLEAR]
    bundle_b = [DESTINATION, SHORT_SELECTION, CLEAR]

    if not args.approve:
        print(
            json.dumps(
                dict(control=control_bundle, arm_a=bundle_a, arm_b=bundle_b, fired=False),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    approval = _AlwaysApprove()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=approval,
    )
    out = dict(fired=True)
    try:
        gate = stack.gate
        out["C0_fabricated_control"] = _fire_bundle(gate, control_bundle)
        out["A_no_destination"] = _fire_bundle(gate, bundle_a)
        out["B_destination"] = _fire_bundle(gate, bundle_b)
    finally:
        stack.stop()

    out["verdict"] = _verdict(
        out["C0_fabricated_control"], out["A_no_destination"], out["B_destination"]
    )
    out["approval_requests"] = [list(bundle) for bundle in approval.asked]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
