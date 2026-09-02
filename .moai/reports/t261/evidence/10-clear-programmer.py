"""t261 — 프로그래머를 비운다. `Clear` 두 줄 (단계 명령: 선택 → 값).

제품 이음매 그대로 나간다 — `build_console_stack` + `run_commands` + 안전 게이트.
우회 배선 0. 리드 지시 2026-09-02.
"""

from __future__ import annotations

import argparse
import json
import sys

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.bootstrap import build_console_stack


class _Approve:
    """`Clear` 는 게이트에서 safe 라 이 통로를 안 타지만, 배선은 실제와 같게 둔다."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(request.commands))
        return True


class _RefusingQuestions:
    def ask(self, request):
        raise AssertionError("이 프로브는 질문을 받지 않는다")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    approval = _Approve()
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=approval,
    )
    registry = build_toolset(
        execution_port=stack.gate.execution_port,
        state_port=stack.gate.state_port,
        bundle_gate=stack.gate,
        question_port=_RefusingQuestions(),
    )

    # 한 번들에 두 줄 — `Clear` 는 dedupe 면제라 둘 다 산다(t256 계열 실측).
    call = ToolCall(
        id="t261-clear",
        name="run_commands",
        arguments=dict(commands=["Clear", "Clear"]),
    )
    execution = registry.dispatch(call)
    out = dict(
        commands=["Clear", "Clear"],
        is_error=execution.result.is_error,
        outcomes=[
            dict(command=r.command, status=r.status, detail=r.detail)
            for r in execution.command_outcomes
        ],
        approval_requests=len(approval.asked),
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
