"""Chat session — one Korean instruction turn through gate + orchestrator (M5).

Builds the M3 orchestrator on top of the REAL M4 gate ports and reports gate
TRUTH to the chat surface in Korean (REQ-MVP-020/022): blocked / held /
unconfirmed / partial states are never rendered as success. Provider failures
are translated through the Korean error catalog; the raw SDK detail goes to the
diagnostic (audit) log ONLY (REQ-MVP-044).

Measurement (acceptance "왕복 시간 측정 방법"): the session marks turn start at
instruction receipt, the measured execution port marks each console-result
receipt (§2 end event), the approval channel brackets human waits (§3), and the
recorder feeds judged turns to the fallback detector. The orchestrator is built
WITHOUT its own detector wiring so the recorder is the single feed point.

Threading: ``run_instruction`` is synchronous and runs on a worker thread
(``asyncio.to_thread`` in the app layer); ``send_event`` must therefore be
thread-safe (the app wraps the WebSocket send accordingly).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from server.deploy.review import ReviewRequest
from server.llm.types import LLMProvider
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.runner import InstructionResult, Orchestrator
from server.orchestrator.tools import CommandOutcome, DeployPipelinePort, build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate, ScreenDecision
from server.web.approval_bridge import ApprovalChannel
from server.web.korean_errors import classify_exception
from server.web.measure import RoundTripRecorder
from server.web.messages import (
    approval_request_event,
    chat_response_event,
    error_event,
    notice_event,
    proposal_event,
    review_request_event,
    status_event,
)

# The gate's unconfirmed-execution marker (REQ-MVP-032). String contract pinned
# by tests here AND by the gate's own tests — a wording change fails both.
UNCONFIRMED_MARKER = "execution unconfirmed"

# Korean labels for every per-command status the chat surface can show.
STATUS_LABELS: dict[str, str] = {
    "executed_ok": "실행 완료",
    "failed": "실행 실패",
    "not_executed": "미실행 (선행 명령 실패로 중단)",
    "skipped_already_executed": "건너뜀 (중복 실행 방지)",
    "blocked": "차단됨",
    "rejected": "거부됨",
    "proposal": "제안 (라이브 잠금 — 전송되지 않음)",
    "held": "승인 대기",
    "unconfirmed": "실행 미확인 (자동 재전송 안 함)",
}

# Korean summary lines derived from gate bundle decisions (gate truth).
_DECISION_SUMMARY: dict[str, str] = {
    "blocked_console_offline": "콘솔 오프라인 상태입니다 — 신규 명령 실행이 차단되었습니다.",
    "blocked_responder_degraded": (
        "콘솔 응답기가 저하 상태입니다 — 결과 확인이 불가능하여 "
        "부수효과 명령을 시작하지 않았습니다."
    ),
    "blocked_backup_failed": "쇼파일 백업 실패로 실행이 차단되었습니다 (안전 장치).",
    "locked": "라이브 잠금 활성 — 콘솔로 전송하지 않고 제안 카드만 생성했습니다.",
    "rejected": "승인 거부로 번들 전체가 실행되지 않았습니다.",
    "blocked_grammar": "문법 검증에 실패한 명령이 있었습니다.",
}

_TURN_STATUS_SUMMARY: dict[str, str] = {
    "retries_exhausted": "자가 수정 3회 한도에 도달하여 실행에 실패했습니다.",
    "loop_limit": "모델 호출 한도를 초과하여 중단했습니다.",
}


def outcome_view(outcome: CommandOutcome) -> dict:
    """One per-command chat-surface row with an honest Korean label."""
    status = outcome.status
    if status == "failed" and UNCONFIRMED_MARKER in outcome.detail:
        status = "unconfirmed"  # REQ-MVP-032: unconfirmed is NOT a failure claim
    return {
        "command": outcome.command,
        "status": status,
        "label": STATUS_LABELS.get(status, status),
        "detail": outcome.detail,
    }


def summarize_outcomes(status: str, views: Sequence[dict]) -> str:
    """Compose the outcome-derived Korean summary (gate-truth honesty)."""
    statuses = [view["status"] for view in views]
    parts: list[str] = []
    if status in _TURN_STATUS_SUMMARY:
        parts.append(_TURN_STATUS_SUMMARY[status])
    if "unconfirmed" in statuses:
        parts.append(
            "실행 미확인 명령이 있습니다 — 콘솔에서 실제 실행 여부를 확인해 주세요 "
            "(자동 재전송 안 함)."
        )
    executed = sum(1 for s in statuses if s == "executed_ok")
    incomplete = sum(1 for s in statuses if s in ("failed", "not_executed"))
    if executed and incomplete:
        parts.append("일부 명령만 실행되었습니다 (부분 실행).")
    if (
        status == "ok"
        and statuses
        and all(s in ("executed_ok", "skipped_already_executed") for s in statuses)
    ):
        parts.append("요청한 명령을 모두 실행했습니다.")
    return " ".join(parts)


class _MeasuredExecutionPort:
    """Wraps the gate executor; marks each RECEIVED console result (§2 end)."""

    def __init__(self, inner, recorder: RoundTripRecorder | None) -> None:
        self._inner = inner
        self._recorder = recorder

    def execute(self, command: str) -> ExecutionResult:
        result = self._inner.execute(command)
        if self._recorder is not None and self._is_console_result(result):
            self._recorder.note_console_result()
        return result

    @staticmethod
    def _is_console_result(result: ExecutionResult) -> bool:
        detail = result.detail or ""
        if detail.startswith("blocked:"):
            return False  # gate block — nothing was sent, nothing was received
        # Unconfirmed = timeout: no console result was received (§2 end event).
        return UNCONFIRMED_MARKER not in detail


class _ObservingBundleGate:
    """BundleGate wrapper surfacing every screening decision to the session."""

    def __init__(self, gate: SafetyGate, on_decision: Callable[[ScreenDecision], None]) -> None:
        self._gate = gate
        self._on_decision = on_decision

    def screen(self, commands: Sequence[str]) -> ScreenDecision:
        decision = self._gate.screen(commands)
        self._on_decision(decision)
        return decision


class ChatSession:
    """One WebSocket client's chat session over the shared gate + provider."""

    def __init__(
        self,
        *,
        gate: SafetyGate,
        provider: LLMProvider,
        system_prefix: str,
        audit: AuditLog,
        send_event: Callable[[dict], None],
        approval_channel: ApprovalChannel,
        recorder: RoundTripRecorder | None = None,
        rig_paths: dict[str, str] | None = None,
        review_channel: ApprovalChannel | None = None,
        deploy_pipeline: DeployPipelinePort | None = None,
    ) -> None:
        self._gate = gate
        self._audit = audit
        self._send = send_event
        self._channel = approval_channel
        self._review_channel = review_channel
        self._recorder = recorder
        self._turn_decisions: list[ScreenDecision] = []
        approval_channel.bind(self._notify_approval)
        if review_channel is not None:
            review_channel.bind(self._notify_review)
        registry = build_toolset(
            execution_port=_MeasuredExecutionPort(gate.execution_port, recorder),
            state_port=gate.state_port,
            bundle_gate=_ObservingBundleGate(gate, self._on_decision),
            rig_paths=rig_paths,
            deploy_pipeline=deploy_pipeline,
        )
        self._orchestrator = Orchestrator(
            provider=provider, registry=registry, system_prefix=system_prefix
        )

    def close(self) -> None:
        """Disconnect: unbind both channels (denies anything pending)."""
        self._channel.unbind()
        if self._review_channel is not None:
            self._review_channel.unbind()

    # -- event plumbing ----------------------------------------------------------

    def _notify_approval(self, request_id: str, request: ApprovalRequest) -> None:
        self._send(approval_request_event(request_id=request_id, request=request))

    def _notify_review(self, request_id: str, request: ReviewRequest) -> None:
        self._send(review_request_event(request_id=request_id, request=request))

    def _on_decision(self, decision: ScreenDecision) -> None:
        self._turn_decisions.append(decision)
        if decision.status == "locked" and decision.proposal is not None:
            self._send(
                proposal_event(
                    commands=list(decision.proposal.commands),
                    reasons=list(decision.proposal.reasons),
                )
            )
        elif decision.status == "blocked_backup_failed":
            self._send(
                notice_event(
                    "쇼파일 백업에 실패하여 실행이 차단되었습니다 (안전 장치). "
                    "저장 공간과 콘솔 상태를 확인해 주세요."
                )
            )
        elif decision.status in ("blocked_console_offline", "blocked_responder_degraded"):
            self._send(self.status_snapshot())

    # -- public surface ------------------------------------------------------------

    def status_snapshot(self) -> dict:
        """Gate-truth status event (REQ-MVP-030/031 UI half)."""
        gate_status = self._gate.status
        return status_event(
            health=gate_status["health"],
            live_lock=gate_status["live_lock"],
            executions_blocked=self._gate.monitor.executions_blocked,
        )

    def set_lock(self, active: bool) -> dict:
        """Toggle the live lock (REQ-MVP-016 UI half); emits a status event."""
        if active:
            self._gate.lock.activate()
        else:
            self._gate.lock.deactivate()
        event = self.status_snapshot()
        self._send(event)
        return event

    # @MX:NOTE: [AUTO] one instruction turn — measurement start/finish, gate-truth
    #   summary composition, and the REQ-MVP-044 raw-detail/audit split all funnel
    #   through this single method
    def run_instruction(self, text: str) -> dict:
        """Drive one Korean instruction; sends + returns the final event."""
        self._turn_decisions = []
        if self._recorder is not None:
            self._recorder.turn_started()
        try:
            result = self._orchestrator.handle_instruction(text)
        except Exception as exc:  # REQ-MVP-044: raw detail NEVER reaches the surface
            return self._report_error(exc)
        views = [outcome_view(outcome) for outcome in result.command_outcomes]
        summary = self._compose_summary(result, views)
        if self._recorder is not None:
            self._recorder.turn_finished(retries_used=result.retries_used)
        event = chat_response_event(
            status=result.status, summary=summary, text=result.text, commands=views
        )
        self._send(event)
        return event

    # -- internals ------------------------------------------------------------------

    def _report_error(self, exc: Exception) -> dict:
        kind, message = classify_exception(exc)
        raw_detail = getattr(exc, "raw_detail", None) or repr(exc)
        provider_name = getattr(exc, "provider", "")
        self._audit.record(
            {
                "event": "provider_error",
                "kind": kind,
                "provider": provider_name,
                "raw_detail": raw_detail,
            }
        )
        if self._recorder is not None:
            self._recorder.turn_finished(retries_used=0, error=True)
        event = error_event(message=message, kind=kind)
        self._send(event)
        return event

    def _compose_summary(self, result: InstructionResult, views: list[dict]) -> str:
        parts: list[str] = []
        seen: set[str] = set()
        for decision in self._turn_decisions:
            line = _DECISION_SUMMARY.get(decision.status)
            if line and decision.status not in seen:
                seen.add(decision.status)
                parts.append(line)
        outcome_summary = summarize_outcomes(result.status, views)
        if outcome_summary:
            parts.append(outcome_summary)
        return " ".join(parts)
