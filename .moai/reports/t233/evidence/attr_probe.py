"""t233 어트리뷰트 프로브 — 제품 이음매 그대로(run_commands -> 안전 게이트 -> 링크).

우회 배선을 만들지 않는다: 콘솔 스택은 조립 루트 build_console_stack 이 만든다
(server/tools/lxseq_e2e.py 와 같은 형태).

규율(리드 승인 2026-09-01, t135 대체안):
  - 건마다 선택 -> 발사 -> 즉시 Off Fixture <fid>. 묶지 않는다
  - ClearAll 금지 — 전역이라 감독 작업물을 파괴한다
  - 복구를 ok 로 판정하지 않는다. 이 채널엔 프로그래머 되읽기가 없다(t235)
  - 대상은 단계마다 한 대
"""

from __future__ import annotations

import argparse
import json
import sys

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.bootstrap import build_console_stack


class _RefusingQuestions:
    def ask(self, request):
        raise AssertionError("이 프로브는 질문을 받지 않는다")


def _run(registry, command):
    call = ToolCall(id="t233", name="run_commands", arguments=dict(commands=[command]))
    execution = registry.dispatch(call)
    rows = []
    for r in execution.command_outcomes:
        rows.append(dict(command=r.command, status=r.status, detail=r.detail))
    return dict(command=command, is_error=execution.result.is_error, outcomes=rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fid", required=True)
    ap.add_argument("--attribute", required=True)
    ap.add_argument("--value", required=True)
    ap.add_argument("--listen-port", type=int, required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)

    stack = build_console_stack(
        send_host=args.host, send_port=args.port, receive_port=args.listen_port
    )
    registry = build_toolset(
        execution_port=stack.gate.execution_port,
        state_port=stack.gate.state_port,
        bundle_gate=stack.gate,
        question_port=_RefusingQuestions(),
    )
    steps = []
    steps.append(_run(registry, "Fixture " + args.fid))
    quoted = chr(39) + args.attribute + chr(39)
    steps.append(_run(registry, "Attribute " + quoted + " At " + args.value))
    steps.append(_run(registry, "Off Fixture " + args.fid))
    out = dict(
        fid=args.fid,
        attribute=args.attribute,
        value=args.value,
        steps=steps,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
