"""M7 종단 라이브 검증 하네스 (AC-BUSKWIZ-017).

This is a DEV TOOL, not a production execution path — exempt from the
REQ-MVP-029 single-chokepoint rule the same way ``responder_roundtrip`` and
``osc_smoke`` are (M4 import-boundary test whitelists ``server.tools``).

**우회 배선을 만들지 않는다**: 콘솔 스택은 조립 루트 `build_console_stack`이
세우고, 툴은 `ChatSession`이 쓰는 것과 같은 `build_toolset`으로 만든다. 여기서
게이트·감사·브리지를 손으로 엮으면 M7이 검증하는 것이 제품 경로가 아니게 된다.

Usage (from the project root, with grandMA3 onPC running the responder)::

    uv run python -m server.tools.busking_e2e --genre 록 --listen-port 9005

승인은 `--approve`가 있을 때만 자동 승인된다. 없으면 `DenyAllApprovalPort`가
막고, 그때의 관측(콘솔 송신 0건)도 유효한 결과다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack


class _AutoApprove:
    """종단 실행용 승인 채널. 승인한 번들을 그대로 기록한다."""

    def __init__(self) -> None:
        self.approved: list[tuple[str, ...]] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        self.approved.append(request.commands)
        return True


def _pool_slots(state_port, pool: int) -> list[dict]:
    """한 프리셋 풀의 자식 목록을 재조회한다 (슬롯·라벨의 **존재** 수준)."""
    payload = state_port.query_state(f"DataPool/PresetPools/{pool}")
    node = payload.get("node") or {}
    children = payload.get("children") or node.get("children") or []
    return [c for c in children if isinstance(c, dict)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--genre", default="록")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--listen-port", type=int, default=9005)
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    approval = _AutoApprove()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=approval if args.approve else None,
    )
    try:
        registry = build_toolset(
            execution_port=stack.gate.execution_port,
            state_port=stack.gate.state_port,
            bundle_gate=stack.gate,
        )
        execution = registry.dispatch(
            ToolCall(id="m7", name="prepare_busking", arguments={"genre": args.genre})
        )
        payload = json.loads(execution.result.content)
        report = payload.get("report", {})
        pools = sorted({p["pool"] for p in report.get("created", [])})
        observed = {pool: _pool_slots(stack.gate.state_port, pool) for pool in pools}
        result = {
            "is_error": execution.result.is_error,
            "executed": payload.get("executed"),
            "genre": payload.get("genre"),
            "approved_bundles": [list(b) for b in approval.approved],
            "commands": payload.get("commands", []),
            "report": report,
            "summary_ko": payload.get("summary_ko", ""),
            "requery": {
                str(pool): [{"i": c.get("i"), "name": c.get("name")} for c in children]
                for pool, children in observed.items()
            },
        }
    finally:
        stack.stop()

    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if not result["is_error"] else 1


if __name__ == "__main__":
    sys.exit(main())
