"""t221 — get_spatial_context 원문을 그대로 저장한다. 읽기 전용."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack


class _Deny:
    def request_approval(self, request: ApprovalRequest) -> bool:
        return False


class _Q:
    def ask(self, request) -> str:
        return ""


stack = build_console_stack(
    send_host="127.0.0.1", send_port=8000, receive_port=9005, approval_port=_Deny()
)
try:
    registry = build_toolset(
        execution_port=stack.gate.execution_port,
        state_port=stack.gate.state_port,
        property_port=stack.gate.state_port,
        bundle_gate=stack.gate,
        question_port=_Q(),
        group_approval_port=_Deny(),
    )
    execution = registry.dispatch(
        ToolCall(id="t221-raw", name="get_spatial_context", arguments=dict())
    )
    Path(".moai/reports/t221/evidence/spatial_raw.json").write_text(
        execution.result.content, encoding="utf-8"
    )
    print("is_error", execution.result.is_error, "bytes", len(execution.result.content))
finally:
    stack.stop()
