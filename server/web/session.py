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
from server.llm.types import LLMProvider, ToolCall
from server.looks.instantiate import CAPTURE_SHARED, LookInstantiation
from server.orchestrator.last_created import LastCreated, parse_last_created
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.runner import InstructionResult, Orchestrator
from server.orchestrator.tools import CommandOutcome, DeployPipelinePort, build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate, ScreenDecision
from server.safety.monitor import HealthMonitor
from server.safety.session_context import bind_session_key, new_session_key, reset_session_key
from server.web.approval_bridge import ApprovalChannel
from server.web.korean_errors import classify_exception
from server.web.measure import RoundTripRecorder
from server.web.messages import (
    CONSOLE_INPUT_LISTENING,
    CONSOLE_INPUT_UNDETERMINED,
    approval_request_event,
    chat_response_event,
    error_event,
    execution_preview_event,
    notice_event,
    proposal_event,
    review_request_event,
    status_event,
)
from server.web.preview import build_execution_preview
from server.web.reply_discovery import ReplyPortMismatch

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

    def __init__(
        self,
        gate: SafetyGate,
        on_preview: Callable[[Sequence[str]], None],
        on_decision: Callable[[ScreenDecision], None],
    ) -> None:
        self._gate = gate
        self._on_preview = on_preview
        self._on_decision = on_decision

    def screen(self, commands: Sequence[str]) -> ScreenDecision:
        self._on_preview(commands)
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
        console_input_probe: Callable[[], str] | None = None,
        reply_port_probe: Callable[[], ReplyPortMismatch | None] | None = None,
    ) -> None:
        self._gate = gate
        # Injected so the status surface owns the I/O and the health state
        # machine stays a pure, clock-driven object on the gate's hot path.
        self._console_input_probe = console_input_probe
        self._reply_port_probe = reply_port_probe
        self._audit = audit
        self._send = send_event
        self._channel = approval_channel
        self._review_channel = review_channel
        self._recorder = recorder
        self._turn_decisions: list[ScreenDecision] = []
        self._preview_counter = 0
        # REQ-DEPLOY-030 (#4): the single most-recent created look, persisted
        # ACROSS turns (unlike _turn_decisions, this is NOT reset per turn) so a
        # bare follow-up modification can anchor to the real target.
        self._last_created: LastCreated | None = None
        # M6c-1 Finding 1/2: a unique identity for THIS connection, scoping the
        # shared approval_channel/review_channel/gate's per-session state so a
        # sibling ChatSession's disconnect or screening never leaks in.
        self._session_key = new_session_key()
        approval_channel.bind(self._notify_approval, session_key=self._session_key)
        if review_channel is not None:
            review_channel.bind(self._notify_review, session_key=self._session_key)
        registry = build_toolset(
            execution_port=_MeasuredExecutionPort(gate.execution_port, recorder),
            state_port=gate.state_port,
            bundle_gate=_ObservingBundleGate(gate, self._on_preview, self._on_decision),
            rig_paths=rig_paths,
            deploy_pipeline=deploy_pipeline,
        )
        # Held so a look bundle re-enters the SAME run_commands tool the model
        # uses, rather than growing a second way to reach the console.
        self._registry = registry
        self._orchestrator = Orchestrator(
            provider=provider, registry=registry, system_prefix=system_prefix
        )

    def close(self) -> None:
        """Disconnect: unbind both channels for THIS session ONLY — denies
        this session's own pending requests, never another session's."""
        self._channel.unbind(session_key=self._session_key)
        if self._review_channel is not None:
            self._review_channel.unbind(session_key=self._session_key)

    # -- event plumbing ----------------------------------------------------------

    def _notify_approval(self, request_id: str, request: ApprovalRequest) -> None:
        self._send(approval_request_event(request_id=request_id, request=request))

    def _notify_review(self, request_id: str, request: ReviewRequest) -> None:
        self._send(review_request_event(request_id=request_id, request=request))

    def _on_preview(self, commands: Sequence[str]) -> None:
        if not commands:
            return
        self._preview_counter += 1
        preview = build_execution_preview(
            preview_id=f"preview-{self._preview_counter}",
            commands=commands,
        )
        self._send(execution_preview_event(preview=preview))

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

    # @MX:NOTE: [AUTO] the panel's pin seed (REQ-SHOWUI-004). Read-only exposure
    #   of the EXISTING cross-turn memory — the panel gets no second source of
    #   truth for "what did the chat just create", and cannot write to this one.
    @property
    def last_created(self) -> LastCreated | None:
        """The look this session most recently created, or ``None``.

        ``None`` is the seed-absent case the panel turns into an explicit error
        rather than a silent no-op (``server.web.panel.PinSeedUnavailable``,
        acceptance.md §D edge case 7).
        """
        return self._last_created

    # @MX:NOTE: [AUTO] the look layer's only route to a console (REQ-LOOKLIB-010
    #   / 019). This is a CALLER of the single execution path, not a second one:
    #   the bundle re-enters the same run_commands tool a model-issued call
    #   uses, so it inherits the execution preview, gate.screen() and the audit
    #   log without any of them being duplicated for looks.
    def run_look_bundle(self, plan: LookInstantiation) -> dict:
        """Screen and run one look instantiation bundle; return it with its report.

        An empty bundle sends nothing — that is the shape a look takes when the
        rig addressed none of its roles, and the report says why.

        The per-family capture shape is REFUSED here rather than run. It is
        built from repeated ``ClearAll`` / ``Group`` lines, and run_commands
        deduplicates identical strings within one bundle (tools.py:376-391) —
        right for a ``Store``, wrong for a ``ClearAll`` whose whole purpose is
        to run at a second MOMENT. Cycles 2..N would lose both their clear and
        their re-selection and store the previous cycle's programmer, which is
        the silent over-capture that shape exists to prevent. Refusing loudly
        beats writing wrong presets; lifting the refusal needs the dedupe rule
        changed, which is outside the look layer.
        """
        report = plan.to_dict()
        if plan.capture_shape != CAPTURE_SHARED:
            return {
                "executed": False,
                "report": report,
                "commands": [],
                "refused": (
                    f"capture shape {plan.capture_shape!r} cannot be executed: "
                    "run_commands drops the repeated ClearAll/Group lines its "
                    "isolated cycles are built from"
                ),
            }
        if not plan.commands:
            return {"executed": False, "report": report, "commands": []}
        execution = self._registry.dispatch(
            ToolCall(
                id=f"look-{plan.look_id}",
                name="run_commands",
                arguments={"commands": list(plan.commands)},
            )
        )
        return {
            "executed": not execution.result.is_error,
            "report": report,
            "commands": [outcome_view(o) for o in execution.command_outcomes],
        }

    def status_snapshot(self) -> dict:
        """Gate-truth status event (REQ-MVP-030/031 UI half)."""
        gate_status = self._gate.status
        health = gate_status["health"]
        console_input = self._console_input(health)
        mismatch = self._reply_port(console_input)
        return status_event(
            health=health,
            live_lock=gate_status["live_lock"],
            executions_blocked=self._gate.monitor.executions_blocked,
            console_input=console_input,
            reply_port=mismatch.observed if mismatch is not None else None,
            receive_port=mismatch.configured if mismatch is not None else None,
        )

    def _console_input(self, health: str) -> str:
        """Diagnose WHY the console is silent — never WHETHER it is (REQ-DEPLOY-018).

        Only ``console_offline`` is ambiguous: the monitor reaches it both when
        onPC is genuinely down and when onPC is up but the responder plugin —
        the only thing that ever sends — has stopped. A bind probe on the
        console's OSC input port separates the two, so the UI can name the real
        cause instead of sending the operator to inspect two healthy subsystems.

        Every other state is left unprobed: ``online`` and ``responder_degraded``
        already imply console traffic was seen, so there is nothing to
        disambiguate and no reason to pay for a socket on every heartbeat tick.
        A probe failure degrades to ``undetermined`` — a diagnosis aid must never
        be able to break the status surface it decorates.
        """
        if health != HealthMonitor.CONSOLE_OFFLINE or self._console_input_probe is None:
            return CONSOLE_INPUT_UNDETERMINED
        try:
            return self._console_input_probe()
        except Exception:
            return CONSOLE_INPUT_UNDETERMINED

    def _reply_port(self, console_input: str) -> ReplyPortMismatch | None:
        """The third ``console_offline`` cause: the console replies elsewhere.

        Gated on ``console_input == listening`` and nothing weaker. That verdict
        already means "the console's OSC input is live but nothing is reaching
        us", which is precisely the shape a reply-port drift makes — and it is
        also the only shape where a reply could exist to be found. A silent
        input means onPC itself is down, so there is nothing to discover; a
        healthy link means the configured port already works and discovery must
        not run at all.

        The probe is non-blocking by contract (see
        :class:`server.web.reply_discovery.ReplyPortDiagnostic`) because this
        method runs on the asyncio event loop. A failure degrades to "no
        mismatch": the operator then sees the responder message, which is still
        the better of the two pre-existing answers.
        """
        if console_input != CONSOLE_INPUT_LISTENING or self._reply_port_probe is None:
            return None
        try:
            return self._reply_port_probe()
        except Exception:
            return None

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
        # M6c-1 Finding 1/2: bind THIS session's identity for the whole turn so
        # the shared gate/approval_channel can scope clearances and pending
        # approvals to this connection (no thread hop happens below — the
        # nested gate.screen()/request_approval() calls run synchronously on
        # this same worker thread, see server.safety.session_context).
        token = bind_session_key(self._session_key)
        try:
            try:
                result = self._orchestrator.handle_instruction(
                    text, session_context=self._session_context_note()
                )
            except Exception as exc:  # REQ-MVP-044: raw detail NEVER reaches the surface
                return self._report_error(exc)
            self._capture_last_created(result)
            views = [outcome_view(outcome) for outcome in result.command_outcomes]
            summary = self._compose_summary(result, views)
            if self._recorder is not None:
                self._recorder.turn_finished(retries_used=result.retries_used)
            event = chat_response_event(
                status=result.status, summary=summary, text=result.text, commands=views
            )
            self._send(event)
            return event
        finally:
            reset_session_key(token)

    # -- internals ------------------------------------------------------------------

    def _capture_last_created(self, result: InstructionResult) -> None:
        """Snapshot the just-created look from this turn's SUCCESSFUL commands.

        Snapshot-only: a new creation replaces the prior value; a turn that
        creates nothing leaves the prior snapshot intact (so a later bare
        modification still anchors to the last real look)."""
        executed = [
            outcome.command
            for outcome in result.command_outcomes
            if outcome.status == "executed_ok"
        ]
        captured = parse_last_created(executed)
        if captured is not None:
            self._last_created = captured

    def _session_context_note(self) -> str | None:
        """The cross-turn note injected before the next instruction (REQ-DEPLOY-030).

        Carries the last-created look's identity AND a regenerate-don't-blind-
        edit steer. Written as an instruction to the model (English, matching
        the rulebook system-prefix convention) with the Korean operator phrase
        as a grounded example. Returns ``None`` when no look has been created."""
        last = self._last_created
        if last is None or last.sequence is None:
            return None
        target = f"Sequence {last.sequence}"
        if last.executor is not None:
            target += f" / Executor {last.executor}"
        return (
            f"Session context — the last look you created is on {target}. "
            f'When the user asks to modify that look (e.g. "더 느리게" / make it '
            f"slower), apply the change to {target} — do NOT target an arbitrary "
            f"Sequence or Executor (such as Sequence 1 / Executor 1). Prefer "
            f"regenerating the look on {target} over blind-editing a different "
            f"target."
        )

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
