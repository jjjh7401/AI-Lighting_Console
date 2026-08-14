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

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from server.deploy.review import ReviewRequest
from server.llm.types import LLMProvider, ModelTurn, ToolCall, Usage, UserMessage
from server.looks.instantiate import LookInstantiation
from server.looks.songcue import normalise_start_ms
from server.orchestrator.last_created import LastCreated, parse_last_created
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.runner import InstructionResult, Orchestrator
from server.orchestrator.tools import CommandOutcome, DeployPipelinePort, build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate, ScreenDecision
from server.safety.monitor import HealthMonitor
from server.safety.session_context import bind_session_key, new_session_key, reset_session_key
from server.spatial.pointing import (
    BASIC_POSITION_SEQUENCE,
    PointingTarget,
    SpatialPointingError,
    aim_pan_tilt,
    aimed_commands,
    basic_position_presets,
    fan_chain,
    fan_pan_tilt,
    pointing_commands,
    position_cue_store_commands,
    position_preset_store_commands,
    preset_recall_command,
    radial_pan_tilt,
)
from server.spatial.position_cuesheet import PositionSheetSection, build_position_cue_sheet
from server.spatial.position_moods import match_position_mood
from server.spatial.vocabulary import (
    layout_terms_guidance,
    match_explicit_layout,
    parse_ring_layout,
)
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
    question_request_event,
    review_request_event,
    status_event,
)
from server.web.preview import build_execution_preview
from server.web.question import UNANSWERED, QuestionChannel, QuestionOption, QuestionRequest
from server.web.reply_discovery import ReplyPortMismatch

# The gate's unconfirmed-execution marker (REQ-MVP-032). String contract pinned
# by tests here AND by the gate's own tests — a wording change fails both.
UNCONFIRMED_MARKER = "execution unconfirmed"

# Rolling conversation memory: how many prior transcript messages (user +
# assistant, so an EVEN cap keeps exchanges paired) travel with each new turn.
# Bounded so token cost per turn stays finite while the model still sees enough
# recent context to keep an in-progress task in mind across follow-ups.
HISTORY_MAX_MESSAGES = 16

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

_ALL_FIXTURES_ELEVATION = re.compile(
    r"(?:3d|레이아웃|공간).*(?:모든|전체).*(?:장비|픽스처|fixture)"
    r".*(?:5\s*(?:m|미터)|5m).*(?:높이|올려|이동)"
    r"|(?:모든|전체).*(?:장비|픽스처|fixture)"
    r".*(?:5\s*(?:m|미터)|5m).*(?:높이|올려|이동)"
    r"|(?:모든|전체|전부).*(?:장비|픽스처|fixture|조명)"
    r".*(?:바닥(?:으로부터)?|무대(?:\s*바닥)?).*(?:위|기준).*(?:5\s*(?:m|미터)|5m)",
    re.IGNORECASE,
)

# Aim every moving head's beam at one stage point (measured pan/tilt model —
# server/spatial/pointing.py). Trigger: an aiming verb plus either a centre
# word or an explicit coordinate triple.
_POINT_AT_TARGET = re.compile(
    r"(?:바라보|바라볼|비추|비춰|비출|향하|향해|향할|조준|겨냥|point|aim)",
    re.IGNORECASE,
)
_POINT_TARGET_CENTRE = re.compile(r"중앙|센터|가운데|정?중앙|원점|center|centre", re.IGNORECASE)
_POINT_TARGET_TRIPLE = re.compile(
    r"\(?\s*(?P<x>-?\d+(?:\.\d+)?)\s*,\s*(?P<y>-?\d+(?:\.\d+)?)\s*,\s*(?P<z>-?\d+(?:\.\d+)?)\s*\)?"
)
_POINT_DIMMER_ON = re.compile(r"불(?:을|도)?\s*(?:다\s*)?켜|점등|풀\s*디머|dimmer", re.IGNORECASE)

_TYPED_TWO_ROW_REQUEST = re.compile(
    r"(?:mmx).*(?:350m|350\s*m).*(?:1[.,]?5\s*(?:m|미터))"
    r"|(?:350m|350\s*m).*(?:mmx).*(?:1[.,]?5\s*(?:m|미터))",
    re.IGNORECASE,
)

# LOOK-family (design-relation) pan/tilt handlers: fan over an ordered chain,
# or an inward/outward ring around the rig centroid. See
# docs/proposals/pan-tilt-position-preset-strategy.md.
_LOOK_FAN = re.compile(r"부채살|부채꼴|부채|팬\s*(?:아웃|인)|\bfan\b", re.IGNORECASE)
_LOOK_FAN_IN = re.compile(r"모아|모으|모이|converge|팬\s*인|안쪽으로\s*모", re.IGNORECASE)
_LOOK_FAN_CROSS = re.compile(r"교차|크로스|엇갈|cross", re.IGNORECASE)
_LOOK_RING = re.compile(
    r"(?P<dir>안쪽|바깥쪽|바깥|밖)(?:을|으로|를)?\s*(?:다\s*)?(?:바라보|바라볼|향하|향해|비추|비추도록|비출)",
    re.IGNORECASE,
)
_LOOK_SPREAD = re.compile(r"(?:팬\s*)?(?P<value>\d+(?:\.\d+)?)\s*도")
# The second fan axis (Align <> on Tilt): "틸트 15도" names the end-fixture
# tilt offset; "틸트도/팬틸트 모두/입체" without a number takes the default V.
_LOOK_TILT_SPREAD = re.compile(r"틸트\s*(?P<value>-?\d+(?:\.\d+)?)\s*도")
_LOOK_TILT_FAN = re.compile(
    r"틸트\s*(?:도|까지|랑|과|와)|팬\s*[/·]?\s*틸트|pan\s*/?\s*tilt|입체", re.IGNORECASE
)
_LOOK_PRESET_STORE = re.compile(
    r"프리셋\s*(?P<no>\d+)\s*(?:번)?\s*(?:으?로|에)?\s*저장|저장.*?프리셋\s*(?P<no2>\d+)"
)
# Position-cue store (T1, SPEC-COPILOT-CUETIME-001): "프리셋 N(포지션)을
# 시퀀스 S 큐 C로 저장, 페이드 F초". The cue is stored from a PRESET RECALL
# state so it holds a reference (32_spatial_design.md) — regenerating the
# preset re-focuses every cue built on it. The sequence number is the
# operator's call when absent (Store can land on an existing cue).
_CUE_STORE_INTENT = re.compile(r"(?=.*큐)(?=.*저장)", re.DOTALL)
_CUE_PRESET_REF = re.compile(r"프리셋\s*(?:2\s*\.\s*)?(?P<no>\d+)\s*(?:번)?")
_CUE_SEQUENCE_NO = re.compile(r"시퀀스\s*(?P<no>\d+)")
_CUE_NO = re.compile(r"큐\s*(?P<no>\d+(?:\.\d+)?)")
_CUE_FADE = re.compile(
    r"페이드\s*(?P<sec>\d+(?:\.\d+)?)\s*초?|(?P<sec2>\d+(?:\.\d+)?)\s*초\s*페이드"
)
# Song-structure position cue sheet (T3, SPEC-COPILOT-CUETIME-001):
# "포지션 큐 시트 … 시퀀스 S, 프리셋 P번부터[, 페이드 F초]: 이름 시각 무드, …".
# Sections ride "이름 m:ss 무드" (or "이름 N초 무드") comma-separated; the
# preset base is the operator-stated 'Home' slot of the stored basic ten.
_POSITION_SHEET_REQUEST = re.compile(r"포지션\s*큐\s*시트")
_SHEET_SECTION = re.compile(
    r"(?P<name>[가-힣A-Za-z0-9]+)\s+(?P<start>\d+:\d{2}(?:\.\d{1,3})?|\d+(?:\.\d+)?\s*초)"
    r"\s+(?P<mood>.+)$"
)
_SHEET_PRESET_START = re.compile(r"프리셋\s*(?P<no>\d+)\s*(?:번)?\s*부터")
# 무드→포지션 제안 게이트: 포지션 의도 단어가 있어야만 발화한다 — 무드 어휘만
# 있는 문장(색·룩 요청일 수 있음)은 모델 경로(find_looks 등)에 남긴다.
_POSITION_INTENT = re.compile(r"포지션|포커스|방향|바라보|비추|조준|잡아|연출")

# The ten-basic-positions request: build the canonical position sequence for
# THIS rig and store it as consecutive Position presets, asking for the first
# preset number when the instruction does not carry one.
_BASIC_POSITIONS_REQUEST = re.compile(
    r"(?:기본|베이직|basic).{0,16}?(?:포지션|프리셋|position).*?(?:저장|만들|잡아|생성)",
    re.IGNORECASE | re.DOTALL,
)
_BASIC_POSITIONS_START = re.compile(r"(?P<no>\d+)\s*(?:번)?\s*(?:부터|에서(?:부터)?|번대)")

_REPEATING_TYPE_COLUMNS_REQUEST = re.compile(
    r"(?:\d+\s*열\s*:\s*)?.*mmx.*(?:\d+\s*열\s*:\s*)?.*350\s*m?.*반복",
    re.IGNORECASE,
)
_COLUMN_GAP = re.compile(
    r"(?:열\s*간|열간)\s*간격(?:은|은)?\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?:m|미터)",
    re.IGNORECASE,
)
_FIXTURE_GAP = re.compile(
    r"(?:장비\s*간|장비간)\s*(?:의\s*)?(?:좌우\s*)?간격(?:은|은)?\s*"
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?:m|미터)",
    re.IGNORECASE,
)
_METRE_VALUE = re.compile(r"(\d+(?:[.,]\d+)?)")


def _first_metres(text: str | None) -> float | None:
    """The first number in a free-form spacing answer (e.g. '1.5m' -> 1.5)."""
    if not text:
        return None
    match = _METRE_VALUE.search(text)
    return float(match.group(1).replace(",", ".")) if match else None


@dataclass
class _UploadedVectorworksExport:
    """Ephemeral source/report pair for one WebSocket conversation."""

    content_base64: str | None = None
    file_name: str | None = None
    report: dict[str, object] | None = None

    def replace(self, file_name: str, content_base64: str) -> None:
        self.content_base64 = content_base64
        self.file_name = file_name
        self.report = None

    def clear(self) -> None:
        self.content_base64 = None
        self.file_name = None
        self.report = None


@dataclass
class _PendingRepeatingColumns:
    """The still-incomplete MMX/MMX/350 layout for this chat connection."""

    instruction: str
    row_spacing: float | None = None
    column_spacing: float | None = None


_VECTORWORKS_UPLOAD_INSTRUCTION = (
    "Vectorworks Instrument Data export를 업로드했습니다. "
    "vectorworks_autopatch로 먼저 도면과 현재 콘솔을 대조하고, 자동 패치 가능한 항목을 "
    "정리해 주세요. 반드시 대조 결과에 없는 값은 추측하지 말고 필요한 값만 질문 카드로 "
    "물어보세요."
)


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


class _GateLivenessPort:
    """Adapts ``SafetyGate.heartbeat()`` to the preshow ``LivenessPort`` shape.

    SPEC-COPILOT-PRESHOW-001 T-G2: the pre-show OSC checks need a
    ``ping() -> bool``, but the gate exposes ``heartbeat() -> str`` (the
    ``HealthMonitor`` state after probing the console once). The adapter
    lives HERE, in the consuming web layer, rather than in
    ``server/preshow/osc_check.py`` — the preshow package must not import
    ``server.safety`` (that import would blur the package boundary the
    architecture test enforces).

    ``heartbeat()``'s only two branches (``server/safety/gate.py``) are: on a
    successful ping, ``HealthMonitor.note_ping_success`` sets the state to
    ``HealthMonitor.ONLINE`` UNCONDITIONALLY; on a failed/timed-out ping,
    ``note_ping_timeout`` sets it to ``CONSOLE_OFFLINE`` or
    ``RESPONDER_DEGRADED`` — never ``ONLINE``. So comparing the returned
    state against ``HealthMonitor.ONLINE`` exactly recovers THIS ping's own
    success/failure, not some stale prior state.
    """

    def __init__(self, gate: SafetyGate) -> None:
        self._gate = gate

    def ping(self) -> bool:
        return self._gate.heartbeat() == HealthMonitor.ONLINE


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
        question_channel: QuestionChannel | None = None,
        deploy_pipeline: DeployPipelinePort | None = None,
        console_input_probe: Callable[[], str] | None = None,
        reply_port_probe: Callable[[], ReplyPortMismatch | None] | None = None,
        preshow_receive_port: int | None = None,
        preshow_osc_slot: int | None = None,
    ) -> None:
        self._gate = gate
        # Injected so the status surface owns the I/O and the health state
        # machine stays a pure, clock-driven object on the gate's hot path.
        self._console_input_probe = console_input_probe
        self._reply_port_probe = reply_port_probe
        self._audit = audit
        self._send = send_event
        # Fixture IDs are immutable patch identities. Once a complete spatial
        # read has established them, a later elevation can reuse the set:
        # arrange_fixtures still resolves every ID to its current slot and
        # backs up/read-backs the write, so this removes only a redundant
        # 4-property-per-fixture discovery pass.
        self._spatial_fids: tuple[int, ...] | None = None
        self._pending_repeating_columns: _PendingRepeatingColumns | None = None
        # Layout parameters the operator has already established this session
        # (column gap, fixture gap in metres). Persisted ACROSS turns and NOT
        # cleared after a placement, so a follow-up ("나머지도 배치해줘") reuses
        # them instead of the copilot re-asking for spacing it was already told.
        self._last_layout_spacing: tuple[float, float] | None = None
        # Rolling transcript of prior turns (user instruction + assistant reply),
        # replayed to the model so context survives across turns for EVERY
        # conversation, not just the layout special-cases. Bounded to the last
        # HISTORY_MAX_MESSAGES entries; reset only when this connection ends.
        self._history: list[UserMessage | ModelTurn] = []
        self._channel = approval_channel
        self._review_channel = review_channel
        self._question_channel = question_channel
        self._recorder = recorder
        self._turn_decisions: list[ScreenDecision] = []
        self._preview_counter = 0
        # REQ-DEPLOY-030 (#4): the single most-recent created look, persisted
        # ACROSS turns (unlike _turn_decisions, this is NOT reset per turn) so a
        # bare follow-up modification can anchor to the real target.
        self._last_created: LastCreated | None = None
        self._vectorworks_upload = _UploadedVectorworksExport()
        # M6c-1 Finding 1/2: a unique identity for THIS connection, scoping the
        # shared approval_channel/review_channel/gate's per-session state so a
        # sibling ChatSession's disconnect or screening never leaks in.
        self._session_key = new_session_key()
        approval_channel.bind(self._notify_approval, session_key=self._session_key)
        if review_channel is not None:
            review_channel.bind(self._notify_review, session_key=self._session_key)
        if question_channel is not None:
            question_channel.bind(self._notify_question, session_key=self._session_key)
        registry = build_toolset(
            execution_port=_MeasuredExecutionPort(gate.execution_port, recorder),
            state_port=gate.state_port,
            bundle_gate=_ObservingBundleGate(gate, self._on_preview, self._on_decision),
            rig_paths=rig_paths,
            deploy_pipeline=deploy_pipeline,
            question_port=question_channel,
            vectorworks_upload=self._vectorworks_upload,
            # SPEC-COPILOT-PRESHOW-001 T-G2: reuse the gate's own audited
            # heartbeat as the pre-show OSC checks' liveness probe — no
            # second console link, no new socket. Gated on preshow_receive_port
            # being supplied (wired from server/web/app.py WebDeps ->
            # server/web/serve.py ConsoleStack.receive_port): without a real
            # bound port to report/compare, receive_port_binding has nothing
            # meaningful to check, and the whole OSC family stays the
            # pre-T-G2 skip default — never partially wired.
            preshow_liveness_port=(
                _GateLivenessPort(gate) if preshow_receive_port is not None else None
            ),
            preshow_receive_port=preshow_receive_port,
            # SPEC-COPILOT-PRESHOW-001 T-G3: the site's real osc_slot setting
            # (wired from server/web/app.py WebDeps -> server/web/serve.py
            # apply_effective_settings). None (unwired) is passed through
            # unchanged — run_preshow_checklist itself discloses the
            # unconfirmed-default fallback rather than this layer guessing.
            preshow_osc_slot=preshow_osc_slot,
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
        if self._question_channel is not None:
            self._question_channel.unbind(session_key=self._session_key)
        self._vectorworks_upload.clear()

    # -- event plumbing ----------------------------------------------------------

    def _notify_approval(self, request_id: str, request: ApprovalRequest) -> None:
        self._send(approval_request_event(request_id=request_id, request=request))

    def _notify_review(self, request_id: str, request: ReviewRequest) -> None:
        self._send(review_request_event(request_id=request_id, request=request))

    def _notify_question(self, request_id: str, request: QuestionRequest) -> None:
        self._send(question_request_event(request_id=request_id, request=request))

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

        BOTH capture shapes run. The per-family shape used to be refused here:
        it is built from repeated ``ClearAll`` / ``Group`` lines, and
        run_commands deduplicated every repeat, so cycles 2..N would have lost
        their clear and their re-selection and stored the previous cycle's
        programmer. That defect is fixed at its source — programmer-state
        commands are now exempt from the dedupe
        (``server.orchestrator.tools._is_programmer_state``) — so the isolated
        cycles reach the console intact and the refusal has nothing left to
        protect.
        """
        report = plan.to_dict()
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

    def _all_fixtures_elevation(self, text: str) -> InstructionResult | None:
        """Raise every fixture with a console-confirmed 3D position to 5 m.

        A partial general-layout read can still name a safe elevation target:
        fixtures omitted because they have no usable 3D coordinates are not
        placed in the layout. Console truncation and our own query ceiling are
        different: neither can establish that an omitted fixture is unplaced,
        so both remain a hard stop.
        """
        if _ALL_FIXTURES_ELEVATION.search(text) is None:
            return None
        if self._spatial_fids is not None:
            fids = list(self._spatial_fids)
            target_label = "전체 배치 장비"
        else:
            spatial = self._registry.dispatch(
                ToolCall(id="spatial-read", name="get_spatial_context", arguments={})
            )
            if spatial.result.is_error:
                return InstructionResult(
                    status="ok",
                    text=(
                        "3D 좌표를 읽지 못해 높이 변경을 시작하지 않았습니다. "
                        "콘솔 연결을 확인해 주세요."
                    ),
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
            try:
                payload = json.loads(spatial.result.content)
                coverage = payload["coverage"]
                complete = coverage["complete"]
                fixtures = payload.get("fixtures")
                if complete is True and isinstance(fixtures, list):
                    target_label = "전체 배치 장비"
                else:
                    fixtures = payload["partial_fixtures"]
                    if payload.get("truncated") or payload.get("roundtrip_capped"):
                        raise ValueError("coordinate read is incomplete")
                    target_label = "좌표가 확인된 배치 장비"
                fids = [
                    fixture["fid"]
                    for fixture in fixtures
                    if isinstance(fixture, dict)
                    and isinstance(fixture.get("fid"), int)
                    and not isinstance(fixture.get("fid"), bool)
                ]
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                return InstructionResult(
                    status="ok",
                    text=(
                        "3D 좌표 응답이 전송 중 잘렸거나 조회 한도에 도달해 높이 변경을 "
                        "시작하지 않았습니다."
                    ),
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
        if not fids or len(set(fids)) != len(fids):
            return InstructionResult(
                status="ok",
                text=(
                    "확인된 3D 좌표에서 유효한 FID 목록을 만들지 못해 "
                    "높이 변경을 시작하지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        if self._spatial_fids is None and complete is True:
            self._spatial_fids = tuple(fids)
        arranged = self._registry.dispatch(
            ToolCall(
                id="spatial-elevation",
                name="arrange_fixtures",
                arguments={"preset": "elevation", "fids": fids, "height": 5.0},
            )
        )
        return InstructionResult(
            status="ok",
            text=(
                f"{target_label} {len(fids)}대의 x/y는 유지하고, 바닥 기준 z=5m로 "
                "변경을 요청했습니다. 승인 또는 라이브 잠금 상태에 따른 결과를 아래 "
                "명령 상태에서 확인해 주세요."
            ),
            command_outcomes=arranged.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    @staticmethod
    def _pointing_refusal(text: str) -> InstructionResult:
        """A no-op turn result carrying WHY no aim command was sent."""
        return InstructionResult(
            status="ok",
            text=text,
            command_outcomes=(),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _read_pointing_coordinates(
        self, call_id: str
    ) -> list[tuple[int, tuple[float, float, float]]] | InstructionResult:
        """Every coordinate-confirmed ``(fid, (x, y, z))`` — or the refusal.

        Shared by the FOCUS (point-at) and LOOK (fan/ring) handlers: both
        compute per-fixture pan/tilt from the console's own patch read, and
        both must refuse on a partial read rather than aim half a rig.
        """
        spatial = self._registry.dispatch(
            ToolCall(id=call_id, name="get_spatial_context", arguments={})
        )
        if spatial.result.is_error:
            return self._pointing_refusal(
                "3D 좌표를 읽지 못해 조명 방향 변경을 시작하지 않았습니다. "
                "콘솔 연결을 확인해 주세요."
            )
        try:
            payload = json.loads(spatial.result.content)
            records = payload["fixtures"] if "fixtures" in payload else payload["partial_fixtures"]
            if "fixtures" not in payload and (
                payload.get("truncated") or payload.get("roundtrip_capped")
            ):
                raise ValueError("coordinate read is incomplete")
            return [
                (record["fid"], (float(record["x"]), float(record["y"]), float(record["z"])))
                for record in records
                if isinstance(record, dict)
                and isinstance(record.get("fid"), int)
                and not isinstance(record.get("fid"), bool)
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self._pointing_refusal(
                "3D 좌표 응답이 전송 중 잘렸거나 조회 한도에 도달해 조명 방향 "
                "변경을 시작하지 않았습니다."
            )

    def _point_fixtures_at_target(self, text: str) -> InstructionResult | None:
        """Aim every coordinate-confirmed fixture's beam at one stage point.

        Runs on the MEASURED pan/tilt model (``server/spatial/pointing.py``):
        positions come off the console's own patch read, the pan/tilt degrees
        are computed per fixture, and the writes ride ``run_commands`` through
        the ordinary approval gate. A fixture standing ON the target or beyond
        the tilt ceiling is skipped and reported, never clamped.
        """
        if _POINT_AT_TARGET.search(text) is None:
            return None
        triple = _POINT_TARGET_TRIPLE.search(text)
        if triple is not None:
            target = PointingTarget(
                float(triple.group("x")), float(triple.group("y")), float(triple.group("z"))
            )
        elif _POINT_TARGET_CENTRE.search(text) is not None:
            target = PointingTarget(0.0, 0.0, 0.0)
        else:
            return None  # aiming verb without a target — let the model ask
        fixtures = self._read_pointing_coordinates("pointing-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        pointable: list[tuple[int, tuple[float, float, float]]] = []
        skipped: list[int] = []
        for fid, position in fixtures:
            try:
                aim_pan_tilt(position, target.as_tuple())
            except SpatialPointingError:
                skipped.append(fid)
            else:
                pointable.append((fid, position))
        if not pointable:
            return InstructionResult(
                status="ok",
                text="목표 지점을 향할 수 있는 장비가 없어 조명 방향 변경을 시작하지 않았습니다.",
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        dimmer = 100.0 if _POINT_DIMMER_ON.search(text) is not None else None
        commands = pointing_commands(pointable, target, dimmer=dimmer)
        executed = self._registry.dispatch(
            ToolCall(
                id="pointing-write",
                name="run_commands",
                arguments={"commands": list(commands)},
            )
        )
        skipped_note = (
            f" 목표 지점과 겹치거나 틸트 한계를 넘는 {len(skipped)}대(FID "
            f"{', '.join(str(fid) for fid in skipped)})는 제외했습니다."
            if skipped
            else ""
        )
        dimmer_note = "디머를 켜고 " if dimmer is not None else ""
        return InstructionResult(
            status="ok",
            text=(
                f"{dimmer_note}좌표가 확인된 장비 {len(pointable)}대의 헤드가 "
                f"({target.x:g}, {target.y:g}, {target.z:g}) 지점을 향하도록 "
                f"Pan/Tilt를 요청했습니다.{skipped_note} 승인 또는 라이브 잠금 "
                "상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _look_pan_tilt(self, text: str) -> InstructionResult | None:
        """Aim the rig into a DESIGN look — fan (out/in/cross) or ring (in/out).

        The LOOK family of docs/proposals/pan-tilt-position-preset-strategy.md:
        values are a function of the fixtures' RELATION (chain order, or the
        radial around the rig centroid), not of one target point. Optionally
        stores the programmer as a Position preset when the instruction names
        an explicit preset number (never a guessed slot).
        """
        ring = _LOOK_RING.search(text)
        fan = _LOOK_FAN.search(text)
        if ring is None and fan is None:
            return None
        fixtures = self._read_pointing_coordinates("look-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 룩 포지션을 시작하지 않았습니다."
            )
        skipped: list[int] = []
        if ring is not None:
            mode = "in" if ring.group("dir") == "안쪽" else "out"
            cx = sum(position[0] for _fid, position in fixtures) / len(fixtures)
            cy = sum(position[1] for _fid, position in fixtures) / len(fixtures)
            aims: list[tuple[int, float, float]] = []
            for fid, position in fixtures:
                try:
                    aims.extend(radial_pan_tilt([(fid, position)], center=(cx, cy), mode=mode))
                except SpatialPointingError:
                    skipped.append(fid)
            look_label = f"RING {mode.upper()}"
            look_korean = "링 " + ("안쪽" if mode == "in" else "바깥쪽") + " 조준"
        else:
            if _LOOK_FAN_CROSS.search(text) is not None:
                mode = "cross"
            elif _LOOK_FAN_IN.search(text) is not None:
                mode = "in"
            else:
                mode = "out"
            spread_match = _LOOK_SPREAD.search(_LOOK_TILT_SPREAD.sub("", text))
            spread = float(spread_match.group("value")) if spread_match else 30.0
            tilt_match = _LOOK_TILT_SPREAD.search(text)
            if tilt_match is not None:
                tilt_spread = float(tilt_match.group("value"))
            elif _LOOK_TILT_FAN.search(text) is not None:
                tilt_spread = 15.0
            else:
                tilt_spread = 0.0
            try:
                aims = list(
                    fan_pan_tilt(
                        list(fan_chain(fixtures)),
                        spread=spread,
                        mode=mode,
                        tilt_spread=tilt_spread,
                    )
                )
            except SpatialPointingError as error:
                return self._pointing_refusal(f"부채살 포지션을 만들 수 없습니다: {error}")
            look_label = f"FAN {mode.upper()}"
            tilt_note = f", 틸트 ±{tilt_spread:g}도" if tilt_spread else ""
            look_korean = {
                "out": f"부채살(끝 장비 팬 ±{spread:g}도{tilt_note})",
                "in": f"모으는 부채살(끝 장비 팬 ±{spread:g}도{tilt_note})",
                "cross": f"교차 부채살(끝 장비 팬 ±{spread:g}도{tilt_note})",
            }[mode]
        if not aims:
            return self._pointing_refusal(
                "룩 포지션을 계산할 수 있는 장비가 없어 시작하지 않았습니다."
            )
        dimmer = 100.0 if _POINT_DIMMER_ON.search(text) is not None else None
        commands = list(aimed_commands(aims, dimmer=dimmer))
        preset_match = _LOOK_PRESET_STORE.search(text)
        preset_note = ""
        if preset_match is not None:
            preset_no = int(preset_match.group("no") or preset_match.group("no2"))
            try:
                commands.extend(position_preset_store_commands(preset_no, look_label))
            except SpatialPointingError as error:
                return self._pointing_refusal(f"프리셋 저장 명령을 만들 수 없습니다: {error}")
            preset_note = (
                f" 이어서 Position 프리셋 2.{preset_no}에 '{look_label}'로 저장을 요청했습니다."
            )
        executed = self._registry.dispatch(
            ToolCall(id="look-write", name="run_commands", arguments={"commands": commands})
        )
        skipped_note = (
            f" 중심과 겹치거나 틸트 한계를 넘는 {len(skipped)}대(FID "
            f"{', '.join(str(fid) for fid in skipped)})는 제외했습니다."
            if skipped
            else ""
        )
        dimmer_note = "디머를 켜고 " if dimmer is not None else ""
        return InstructionResult(
            status="ok",
            text=(
                f"{dimmer_note}좌표가 확인된 장비 {len(aims)}대를 {look_korean} "
                f"포지션으로 요청했습니다.{skipped_note}{preset_note} 승인 또는 "
                "라이브 잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _position_mood_suggestion(self, text: str) -> InstructionResult | None:
        """연출 의도(무드) → 포지션 추천 카드 → 선택된 룩만 적용.

        docs/proposals의 무드→포지션 매핑(`server/spatial/position_moods.py`)
        기반. 실행이 아니라 제안이 기본이다: 키워드가 맞아도 카드로 확인을
        받고, 무응답·거절이면 아무것도 보내지 않는다 — 키워드 하나로 단정해
        실행하던 반사적 처리의 재도입을 막는 경계.
        """
        if _POSITION_INTENT.search(text) is None:
            return None
        suggestion = match_position_mood(text)
        if suggestion is None:
            return None
        fixtures = self._read_pointing_coordinates("mood-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 포지션 제안을 시작하지 않았습니다."
            )
        entry = suggestion.entry
        options = [QuestionOption(label=entry.label, description=entry.reason)]
        by_label = {
            label: (aims, skipped) for label, aims, skipped in basic_position_presets(fixtures)
        }
        for alt in entry.alternatives:
            options.append(QuestionOption(label=alt))
        options.append(QuestionOption(label="적용 안 함"))
        matched = ", ".join(suggestion.matched)
        answer = self._ask_one(
            f"'{matched}' 느낌에는 {entry.korean}({entry.label}) 포지션을 추천합니다. 적용할까요?",
            options=tuple(options),
            why=entry.reason,
        )
        if answer is None or "안 함" in answer or "안함" in answer:
            return self._pointing_refusal(
                f"포지션을 적용하지 않았습니다. (추천이었던 룩: {entry.label})"
            )
        chosen = next(
            (label for label in by_label if label.casefold() == answer.strip().casefold()),
            None,
        )
        if chosen is None:
            return self._pointing_refusal(
                f"'{answer}'는 기본 포지션 이름이 아니어서 적용하지 않았습니다. "
                f"(가능: {', '.join(by_label)})"
            )
        aims, skipped = by_label[chosen]
        if not aims:
            return self._pointing_refusal(
                f"{chosen} 포지션을 계산할 수 있는 장비가 없어 적용하지 않았습니다."
            )
        dimmer = 100.0 if _POINT_DIMMER_ON.search(text) is not None else None
        executed = self._registry.dispatch(
            ToolCall(
                id="mood-write",
                name="run_commands",
                arguments={"commands": list(aimed_commands(aims, dimmer=dimmer))},
            )
        )
        skipped_note = (
            f" 조준 불가 {len(skipped)}대(FID {', '.join(str(fid) for fid in skipped)})는 "
            "제외했습니다."
            if skipped
            else ""
        )
        dimmer_note = "디머를 켜고 " if dimmer is not None else ""
        return InstructionResult(
            status="ok",
            text=(
                f"{dimmer_note}'{matched}' 의도에 맞춰 {chosen} 포지션을 장비 "
                f"{len(aims)}대에 요청했습니다.{skipped_note} 승인 또는 라이브 잠금 "
                "상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _basic_position_presets(self, text: str) -> InstructionResult | None:
        """Build the ten canonical positions for THIS rig and store them.

        Preset 1 of the run is ALWAYS 'Home'; the rest follow
        ``BASIC_POSITION_SEQUENCE`` from most basic to most varied. The first
        preset number comes from the instruction ("N번부터") or from ONE
        question card — never from a guessed free slot: ``Store Preset``
        silently overwrites, so the number is the operator's call.
        Each look is applied, stored, labelled and cleared as its own bundle,
        so one refused look never voids the other nine.
        """
        if _BASIC_POSITIONS_REQUEST.search(text) is None:
            return None
        fixtures = self._read_pointing_coordinates("basic-presets-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 기본 포지션 프리셋을 시작하지 않았습니다."
            )
        start_match = _BASIC_POSITIONS_START.search(text)
        if start_match is not None:
            start_no = int(start_match.group("no"))
        else:
            count = len(BASIC_POSITION_SEQUENCE)
            answer = self._ask_one(
                f"기본 포지션 {count}개를 Position 프리셋 몇 번부터 저장할까요? "
                f"(예: 1 → Preset 2.1~2.{count}) 이미 있는 번호는 덮어씁니다.",
                options=(
                    QuestionOption(label="1"),
                    QuestionOption(label="11"),
                    QuestionOption(label="21"),
                ),
                why=(
                    "Store Preset은 기존 슬롯을 경고 없이 덮어쓰므로 "
                    "시작 번호는 운영자가 정해야 합니다."
                ),
            )
            try:
                start_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "시작 프리셋 번호를 받지 못해 저장을 시작하지 않았습니다. "
                    "예: '기본 포지션 10개를 프리셋 21번부터 저장해줘'"
                )
        if start_no <= 0:
            return self._pointing_refusal("시작 프리셋 번호는 1 이상이어야 합니다.")
        try:
            looks = basic_position_presets(fixtures)
        except SpatialPointingError as error:
            return self._pointing_refusal(f"기본 포지션을 계산할 수 없습니다: {error}")
        outcomes: list[CommandOutcome] = []
        stored: list[str] = []
        skipped_notes: list[str] = []
        for offset, (label, aims, skipped) in enumerate(looks):
            preset_no = start_no + offset
            if not aims:
                skipped_notes.append(f"{label}(2.{preset_no}): 조준 가능한 장비 없음 — 건너뜀")
                continue
            commands = [
                *aimed_commands(aims),
                *position_preset_store_commands(preset_no, label),
                "ClearAll",
            ]
            executed = self._registry.dispatch(
                ToolCall(
                    id=f"basic-preset-{preset_no}",
                    name="run_commands",
                    arguments={"commands": commands},
                )
            )
            outcomes.extend(executed.command_outcomes)
            stored.append(f"2.{preset_no} '{label}'")
            if skipped:
                skipped_notes.append(f"{label}: FID {', '.join(str(fid) for fid in skipped)} 제외")
        if not stored:
            return self._pointing_refusal(
                "어느 포지션도 계산되지 않아 프리셋을 저장하지 않았습니다."
            )
        notes = f" 참고: {'; '.join(skipped_notes)}." if skipped_notes else ""
        return InstructionResult(
            status="ok",
            text=(
                f"리그 배치에서 유도한 기본 포지션 {len(stored)}개를 "
                f"Position 프리셋에 저장 요청했습니다: {', '.join(stored)}.{notes} "
                "각 프리셋은 적용→저장→ClearAll 순서로 처리했으며, 승인 또는 라이브 "
                "잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=tuple(outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _position_cue_store(self, text: str) -> InstructionResult | None:
        """Store a Position preset as a cue with an optional position fade (T1).

        The bundle is ``recall → Store Sequence S Cue C 'Pos 2.N' CueFade F →
        ClearAll``: the cue keeps a preset REFERENCE, and the fade is what
        makes the beams glide instead of snap. The sequence number comes from
        the instruction or ONE question card — ``Store`` on an occupied cue
        changes a show object, so the number is the operator's call. No
        ``/Merge``/``/Overwrite`` ever (phaser-flattening + blacklist).
        """
        if _CUE_STORE_INTENT.search(text) is None:
            return None
        preset_ref = _CUE_PRESET_REF.search(text)
        if preset_ref is None:
            return None
        preset_no = int(preset_ref.group("no"))
        fixtures = self._read_pointing_coordinates("cue-store-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 포지션 큐 저장을 시작하지 않았습니다."
            )
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        if sequence_match is not None:
            sequence_no = int(sequence_match.group("no"))
        else:
            answer = self._ask_one(
                f"Position 프리셋 2.{preset_no}을(를) 어느 시퀀스에 큐로 저장할까요? "
                "(예: 101) 이미 큐가 있는 시퀀스면 해당 큐가 바뀔 수 있습니다.",
                options=(
                    QuestionOption(label="101"),
                    QuestionOption(label="110"),
                    QuestionOption(label="200"),
                ),
                why=(
                    "Store Sequence는 지정한 큐 슬롯에 그대로 저장되므로 "
                    "시퀀스 번호는 운영자가 정해야 합니다."
                ),
            )
            try:
                sequence_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "시퀀스 번호를 받지 못해 큐 저장을 시작하지 않았습니다. "
                    "예: '프리셋 2.28을 시퀀스 101 큐 1로 저장, 페이드 5초'"
                )
        cue_match = _CUE_NO.search(text)
        cue_no = float(cue_match.group("no")) if cue_match is not None else 1.0
        fade_match = _CUE_FADE.search(text)
        fade_seconds = (
            float(fade_match.group("sec") or fade_match.group("sec2"))
            if fade_match is not None
            else None
        )
        fids = [fid for fid, _position in fixtures]
        try:
            commands = [
                preset_recall_command(fids, preset_no),
                *position_cue_store_commands(
                    sequence_no,
                    cue_no,
                    fade_seconds=fade_seconds,
                    name=f"Pos 2.{preset_no}",
                ),
                "ClearAll",
            ]
        except SpatialPointingError as error:
            return self._pointing_refusal(f"큐 저장 명령을 만들 수 없습니다: {error}")
        executed = self._registry.dispatch(
            ToolCall(
                id="cue-store-write",
                name="run_commands",
                arguments={"commands": commands},
            )
        )
        fade_note = f" 페이드 {fade_seconds:g}초로" if fade_seconds is not None else ""
        return InstructionResult(
            status="ok",
            text=(
                f"Position 프리셋 2.{preset_no} 리콜 상태를 시퀀스 {sequence_no} "
                f"큐 {cue_match.group('no') if cue_match else '1'}에{fade_note} 저장 "
                "요청했습니다 (프리셋 참조 유지, 저장 후 ClearAll). 승인 또는 라이브 "
                "잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=executed.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _position_cue_sheet(self, text: str) -> InstructionResult | None:
        """Song-structure position cue sheet draft (T3) — mood → preset cues.

        Sections ("이름 시각 무드", comma-separated) resolve through the mood
        table to the stored basic Position presets; blackout sections store
        dimmer 0 and the MIB rule inserts dark pre-move cues (measured, M2).
        The sequence number AND the preset base come from the instruction or
        one question card each — recalling a guessed preset slot would aim
        the show at whatever lives there. Each cue is its own bundle, so one
        refused cue never voids the rest of the sheet.
        """
        if _POSITION_SHEET_REQUEST.search(text) is None:
            return None
        sections: list[PositionSheetSection] = []
        for part in text.split(","):
            matched = _SHEET_SECTION.search(part.strip())
            if matched is None:
                continue
            start_token = matched.group("start").replace("초", "").strip()
            try:
                start_ms = normalise_start_ms(start_token)
            except Exception:
                continue
            sections.append(
                PositionSheetSection(
                    name=matched.group("name"),
                    start_ms=start_ms,
                    mood=matched.group("mood").strip(),
                )
            )
        if not sections:
            return self._pointing_refusal(
                "곡 구간을 읽지 못해 포지션 큐 시트를 만들지 않았습니다. 형식: "
                "'포지션 큐 시트, 시퀀스 110, 프리셋 21번부터: 인트로 0:00 잔잔하게, "
                "후렴 0:40 클럽 드롭'"
            )
        fixtures = self._read_pointing_coordinates("sheet-read")
        if isinstance(fixtures, InstructionResult):
            return fixtures
        if not fixtures:
            return self._pointing_refusal(
                "좌표가 확인된 장비가 없어 포지션 큐 시트를 시작하지 않았습니다."
            )
        sequence_match = _CUE_SEQUENCE_NO.search(text)
        if sequence_match is not None:
            sequence_no = int(sequence_match.group("no"))
        else:
            answer = self._ask_one(
                "포지션 큐 시트를 어느 시퀀스에 저장할까요? (예: 110) "
                "이미 큐가 있는 시퀀스면 해당 큐가 바뀔 수 있습니다.",
                options=(
                    QuestionOption(label="110"),
                    QuestionOption(label="120"),
                    QuestionOption(label="200"),
                ),
                why="Store Sequence는 지정한 큐 슬롯에 그대로 저장되므로 운영자 결정입니다.",
            )
            try:
                sequence_no = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "시퀀스 번호를 받지 못해 큐 시트를 만들지 않았습니다."
                )
        preset_match = _SHEET_PRESET_START.search(text)
        if preset_match is not None:
            preset_start = int(preset_match.group("no"))
        else:
            answer = self._ask_one(
                "기본 포지션 10종(Home~Ring In)이 Position 프리셋 몇 번부터 "
                "저장돼 있나요? (예: 21 → 2.21~2.30)",
                options=(
                    QuestionOption(label="1"),
                    QuestionOption(label="11"),
                    QuestionOption(label="21"),
                ),
                why=(
                    "큐는 프리셋 참조로 빌드됩니다 — 잘못된 슬롯을 리콜하면 "
                    "그 자리에 있는 다른 포지션이 무대에 나갑니다."
                ),
            )
            try:
                preset_start = int(re.search(r"\d+", answer or "").group(0))
            except AttributeError:
                return self._pointing_refusal(
                    "프리셋 시작 번호를 받지 못해 큐 시트를 만들지 않았습니다."
                )
        fade_match = _CUE_FADE.search(text)
        fade_seconds = (
            float(fade_match.group("sec") or fade_match.group("sec2"))
            if fade_match is not None
            else 3.0
        )
        fids = [fid for fid, _position in fixtures]
        try:
            sheet = build_position_cue_sheet(
                sections,
                sequence_no=sequence_no,
                preset_start=preset_start,
                fids=fids,
                fade_seconds=fade_seconds,
            )
        except SpatialPointingError as error:
            return self._pointing_refusal(f"포지션 큐 시트를 만들 수 없습니다: {error}")
        outcomes: list[CommandOutcome] = []
        for plan, bundle in zip(sheet.plans, sheet.bundles, strict=True):
            executed = self._registry.dispatch(
                ToolCall(
                    id=f"song-sheet-cue-{plan.cue_no:g}",
                    name="run_commands",
                    arguments={"commands": list(bundle)},
                )
            )
            outcomes.extend(executed.command_outcomes)
        lines: list[str] = []
        for res in sheet.resolutions:
            minute, second = divmod(res.section.start_ms // 1000, 60)
            stamp = f"{minute}:{second:02d}"
            if res.blackout:
                lines.append(f"큐 {res.cue_no} {res.section.name}({stamp}): 암전")
            elif res.skipped_reason is not None:
                lines.append(
                    f"큐 {res.cue_no} {res.section.name}({stamp}): 건너뜀 — {res.skipped_reason}"
                )
            else:
                varied = f", {res.varied_from} 대안" if res.varied_from else ""
                lines.append(
                    f"큐 {res.cue_no} {res.section.name}({stamp}): {res.look_label} "
                    f"(Preset 2.{res.preset_no}{varied})"
                )
        mib_notes = [
            f"큐 {plan.cue_no:g} '{plan.name}' (다크 선이동)"
            for plan in sheet.plans
            if plan.name.endswith(" Move")
        ]
        mib_note = f" MIB 삽입: {', '.join(mib_notes)}." if mib_notes else ""
        return InstructionResult(
            status="ok",
            text=(
                f"시퀀스 {sequence_no}에 포지션 큐 시트 {len(sheet.plans)}큐를 저장 "
                f"요청했습니다 (페이드 {fade_seconds:g}초, 전 큐 프리셋 참조). "
                f"{' / '.join(lines)}.{mib_note} 승인 또는 라이브 잠금 상태에 따른 "
                "결과를 아래 명령 상태에서 확인해 주세요."
            ),
            command_outcomes=tuple(outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _repeating_type_columns_layout(self, text: str) -> InstructionResult | None:
        """Arrange repeating MMX/MMX/350 columns with independent grid pitches."""
        pattern_present = _REPEATING_TYPE_COLUMNS_REQUEST.search(text) is not None
        if pattern_present:
            self._pending_repeating_columns = _PendingRepeatingColumns(instruction=text)
        pending = self._pending_repeating_columns
        if pending is None:
            return None

        column_gap = _COLUMN_GAP.search(text)
        fixture_gap = _FIXTURE_GAP.search(text)
        if (
            not pattern_present
            and column_gap is None
            and fixture_gap is None
            and re.search(r"(?:뭘|무엇|뭐).*(?:알려|필요)|(?:필요|알려).*?(?:뭘|무엇|뭐)", text)
        ):
            missing_labels = [
                label
                for value, label in (
                    (pending.row_spacing, "열간 간격"),
                    (pending.column_spacing, "장비간 좌우 간격"),
                )
                if value is None
            ]
            detail = (
                f"현재 필요한 정보는 {', '.join(missing_labels)}입니다."
                if missing_labels
                else (
                    "열간·장비간 간격은 모두 확인했습니다. 전체 3D 패치에서 "
                    "MMX·350 수량만 확인하면 됩니다."
                )
            )
            return InstructionResult(
                status="ok",
                text=f"MMX 10대 → MMX 10대 → 350 10대 반복 배치를 계속 준비 중입니다. {detail}",
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        try:
            if column_gap is not None:
                pending.row_spacing = float(column_gap.group("value").replace(",", "."))
            if fixture_gap is not None:
                pending.column_spacing = float(fixture_gap.group("value").replace(",", "."))
            if (
                pending.row_spacing is not None
                and pending.row_spacing <= 0.0
                or pending.column_spacing is not None
                and pending.column_spacing <= 0.0
            ):
                raise ValueError("non-positive spacing")
        except ValueError:
            return InstructionResult(
                status="ok",
                text="열간·장비간 간격은 0보다 큰 미터 값이어야 합니다.",
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        missing = [
            label
            for value, label in (
                (pending.row_spacing, "열간 간격"),
                (pending.column_spacing, "장비간 좌우 간격"),
            )
            if value is None
        ]
        if missing:
            # Collect each missing gap through its OWN card, one at a time —
            # clickable presets plus a free-text box — instead of a prose wall
            # the operator has to parse and answer in one breath.
            gap_options = (
                QuestionOption(label="1m"),
                QuestionOption(label="1.5m"),
                QuestionOption(label="2m"),
            )
            for attr, prompt in (
                ("row_spacing", "열 사이(열간) 간격은 몇 미터인가요?"),
                ("column_spacing", "같은 열 안 장비 사이(좌우) 간격은 몇 미터인가요?"),
            ):
                if getattr(pending, attr) is not None:
                    continue
                answer = self._ask_one(
                    prompt,
                    why="열 배치를 계산하려면 열간·장비간 간격이 각각 필요합니다.",
                    options=gap_options,
                )
                value = _first_metres(answer)
                if value is not None and value > 0.0:
                    setattr(pending, attr, value)
            still_missing = [
                label
                for value, label in (
                    (pending.row_spacing, "열간 간격"),
                    (pending.column_spacing, "장비간 좌우 간격"),
                )
                if value is None
            ]
            if still_missing:
                return InstructionResult(
                    status="ok",
                    text=(
                        "MMX 10대 → MMX 10대 → 350 10대 반복 배치를 기억했습니다. "
                        f"계속하려면 {', '.join(still_missing)}을 미터 단위로 알려주세요."
                    ),
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
        row_spacing = pending.row_spacing
        column_spacing = pending.column_spacing
        assert row_spacing is not None and column_spacing is not None
        spatial = self._registry.dispatch(
            ToolCall(id="repeating-columns-read", name="get_spatial_context", arguments={})
        )
        try:
            payload = json.loads(spatial.result.content)
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = None
        if spatial.result.is_error or not isinstance(payload, dict):
            return InstructionResult(
                status="ok",
                text=(
                    "3D 좌표를 읽지 못해 배치를 시작하지 않았습니다. 콘솔 연결(응답기·OSC "
                    "포트)을 확인한 뒤 다시 요청해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        coverage = payload.get("coverage") or {}
        fixtures = payload.get("fixtures")
        if coverage.get("complete") is not True or not isinstance(fixtures, list):
            return InstructionResult(
                status="ok",
                text=(
                    "전체 3D 패치를 완전히 읽지 못했습니다(부분/절단 응답). 일부만 읽은 상태로 "
                    "배치하면 누락된 장비를 덮어쓸 수 있어 시작하지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )

        def _named(predicate: Callable[[str], bool]) -> list[int]:
            return [
                item["fid"]
                for item in fixtures
                if isinstance(item, dict)
                and isinstance(item.get("fid"), int)
                and not isinstance(item.get("fid"), bool)
                and predicate(str(item.get("name", "")))
            ]

        mmx = _named(lambda name: "mmx" in name.casefold())
        mmx_set = set(mmx)
        beam = [
            fid
            for fid in _named(lambda name: re.search(r"350\s*m?", name, re.IGNORECASE) is not None)
            if fid not in mmx_set  # MMX classification wins, so a type is never double-counted
        ]
        found_line = f"현재 패치에서 MMX {len(mmx)}대, 350 계열 {len(beam)}대를 확인했습니다."

        self._last_layout_spacing = (row_spacing, column_spacing)
        column_size = 10
        cycle = ("mmx", "mmx", "beam")
        pools = {"mmx": mmx, "beam": beam}
        cursor = {"mmx": 0, "beam": 0}
        # Budget = how many COMPLETE columns each type can still fill. Follow the
        # requested cyclic order, but SKIP a type that has no full column left
        # rather than stopping the whole walk at the first short type — the old
        # early-stop abandoned every later type in the cycle (e.g. 19 MMX + 20
        # 350 placed one MMX column and dropped all 20 beams). Stop only when no
        # type can fill another column.
        budget = {kind: len(pool) // column_size for kind, pool in pools.items()}
        columns: list[list[int]] = []
        step = 0
        while any(budget.values()):
            kind = cycle[step % len(cycle)]
            step += 1
            if budget[kind] <= 0:
                continue
            start = cursor[kind]
            columns.append(pools[kind][start : start + column_size])
            cursor[kind] = start + column_size
            budget[kind] -= 1

        if not columns:
            return InstructionResult(
                status="ok",
                text=(
                    f"{found_line} MMX/MMX/350 반복 배치는 한 열이 {column_size}대이므로, "
                    f"먼저 MMX가 최소 {column_size}대 있어야 첫 열을 만들 수 있습니다. "
                    "장비 타입이 이름으로 구분되는지(MMX·350 포함) 확인해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )

        fids = [fid for column in columns for fid in column]
        arranged = self._registry.dispatch(
            ToolCall(
                id="repeating-columns-write",
                name="arrange_fixtures",
                arguments={
                    "preset": "grid",
                    "fids": fids,
                    "rows": len(columns),
                    "columns": column_size,
                    "row_spacing": row_spacing,
                    "column_spacing": column_spacing,
                    "orientation": "xy",
                },
            )
        )
        placed_mmx = cursor["mmx"]
        placed_beam = cursor["beam"]
        summary = (
            f"{found_line} MMX {placed_mmx}대·350 계열 {placed_beam}대를 10대씩 "
            f"{len(columns)}열로, 열간 {row_spacing:g}m·장비간 {column_spacing:g}m 그리드로 "
            "배치하도록 요청했습니다. 승인 또는 라이브 잠금 상태에 따른 결과를 아래 명령 "
            "상태에서 확인해 주세요."
        )
        leftovers = []
        if len(mmx) - placed_mmx > 0:
            leftovers.append(f"MMX {len(mmx) - placed_mmx}대")
        if len(beam) - placed_beam > 0:
            leftovers.append(f"350 계열 {len(beam) - placed_beam}대")
        if leftovers:
            summary += (
                f" 남은 {', '.join(leftovers)}는 {column_size}대에 못 미쳐 완전한 열을 "
                "만들지 못했습니다. 요청하신 MMX·MMX·350 반복은 MMX가 350의 2배일 때 "
                "딱 맞는데 현재 수량은 그렇지 않습니다. 남은 장비를 (1) 부분 열로 그대로 "
                "붙일지, (2) 열당 대수를 바꿔 다시 배치할지 알려주시면 이어서 처리합니다."
            )
        self._pending_repeating_columns = None
        return InstructionResult(
            status="ok",
            text=summary,
            command_outcomes=arranged.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _multi_ring_circle_layout(self, text: str) -> InstructionResult | None:
        """Place a multi-ring circle: ask the missing decisions one card at a
        time (radii, then the remainder ring's order), then arrange each ring.

        This is an EXECUTING handler, not a canned clarifier: it reasons about
        the whole request (ring types/counts + a remainder ring), collects only
        what is genuinely missing through interactive cards, reads the real rig,
        and writes each ring with its own circle arrange (backup + verify per
        call). Count mismatches are reported, never guessed away.
        """
        rings = parse_ring_layout(text)
        if rings is None:
            return None

        radii = self._ask_ring_radii(len(rings))
        order = "fid"
        if any(r.kind == "remainder" and r.alternate for r in rings):
            order = self._ask_remainder_order()

        spatial = self._registry.dispatch(
            ToolCall(id="ring-read", name="get_spatial_context", arguments={})
        )
        try:
            payload = json.loads(spatial.result.content)
            fixtures = payload["fixtures"]
            if spatial.result.is_error or payload["coverage"]["complete"] is not True:
                raise ValueError("incomplete spatial read")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return InstructionResult(
                status="ok",
                text=(
                    "여러 겹 원형 배치를 계획했지만 전체 3D 좌표를 읽지 못해 시작하지 "
                    "않았습니다. 콘솔 연결을 확인한 뒤 다시 요청해 주세요."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )

        def _valid(item: object) -> bool:
            return (
                isinstance(item, dict)
                and isinstance(item.get("fid"), int)
                and not isinstance(item.get("fid"), bool)
            )

        coord = {
            item["fid"]: (float(item.get("x", 0.0)), float(item.get("y", 0.0)))
            for item in fixtures
            if _valid(item)
        }
        key = {"fid": lambda f: f, "left": lambda f: coord[f][0], "front": lambda f: coord[f][1]}[
            order
        ]

        def _named(pred) -> list[int]:
            picked = [
                item["fid"] for item in fixtures if _valid(item) and pred(str(item.get("name", "")))
            ]
            return sorted(picked, key=key)

        mmx = _named(lambda n: "mmx" in n.casefold())
        mmx_set = set(mmx)
        beam = [
            fid
            for fid in _named(lambda n: re.search(r"350\s*m?", n, re.IGNORECASE) is not None)
            if fid not in mmx_set
        ]
        beam_set = set(beam)
        classified = mmx_set | beam_set
        others = sorted(
            (item["fid"] for item in fixtures if _valid(item) and item["fid"] not in classified),
            key=key,
        )

        pos = {"mmx": 0, "beam": 0}
        notes: list[str] = []
        ring_fids: list[list[int]] = []
        for index, ring in enumerate(rings, start=1):
            if ring.kind == "remainder":
                rest_mmx = mmx[pos["mmx"] :]
                rest_beam = beam[pos["beam"] :]
                pos["mmx"], pos["beam"] = len(mmx), len(beam)
                merged: list[int] = []
                for a, b in zip(rest_mmx, rest_beam, strict=False):
                    merged.extend((a, b))
                shorter = min(len(rest_mmx), len(rest_beam))
                tail = rest_mmx[shorter:] + rest_beam[shorter:]
                merged.extend(tail)
                merged.extend(others)
                ring_fids.append(merged)
            else:
                pool = mmx if ring.kind == "mmx" else beam
                want = ring.count or 0
                take = pool[pos[ring.kind] : pos[ring.kind] + want]
                pos[ring.kind] += len(take)
                if len(take) < want:
                    label = "MMX" if ring.kind == "mmx" else "350 계열"
                    notes.append(f"{index}번째 원 {label} {want}대 요청 중 {len(take)}대만 가능")
                ring_fids.append(take)

        outcomes: list[CommandOutcome] = []
        placed_lines: list[str] = []
        for index, (fids, radius) in enumerate(zip(ring_fids, radii, strict=False), start=1):
            if not fids:
                notes.append(f"{index}번째 원에 배치할 장비가 없습니다")
                continue
            arranged = self._registry.dispatch(
                ToolCall(
                    id=f"ring-write-{index}",
                    name="arrange_fixtures",
                    arguments={
                        "preset": "circle",
                        "fids": fids,
                        "radius": radius,
                        "start_angle": 0.0,
                        "orientation": "xy",
                    },
                )
            )
            outcomes.extend(arranged.command_outcomes)
            placed_lines.append(f"{index}번째 원(반지름 {radius:g}m): {len(fids)}대")

        summary = "여러 겹 원형 배치를 요청했습니다 — " + ", ".join(placed_lines) + "."
        if notes:
            summary += " 다만 " + "; ".join(notes) + "."
        summary += " 승인 또는 라이브 잠금 상태에 따른 결과를 아래 명령 상태에서 확인해 주세요."
        return InstructionResult(
            status="ok",
            text=summary,
            command_outcomes=tuple(outcomes),
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _ask_ring_radii(self, count: int) -> list[float]:
        """One card for the ring diameters (innermost→outer); default 4/6/8… m."""
        default = [2.0 + i for i in range(count)]  # radius 2,3,4… (diameter 4,6,8…)
        answer = self._ask_one(
            "각 원의 지름을 안쪽→바깥 순서로 알려주세요 (미터).",
            options=(
                QuestionOption(label="4·6·8m"),
                QuestionOption(label="6·8·10m"),
            ),
            why="원마다 반지름이 달라야 여러 겹으로 겹치지 않고 배치됩니다.",
        )
        if not answer:
            return default
        diameters = [float(v.replace(",", ".")) for v in re.findall(r"\d+(?:[.,]\d+)?", answer)]
        radii = [d / 2.0 for d in diameters if d > 0.0]
        if len(radii) < count:
            radii += default[len(radii) :]
        return radii[:count]

    def _ask_remainder_order(self) -> str:
        """One card for how the remainder ring's 번갈아 order is decided."""
        answer = self._ask_one(
            "마지막 원(남은 장비)을 어떤 순서로 번갈아 배치할까요?",
            options=(
                QuestionOption(label="FID 오름차순", description="패치 번호 순 — 가장 예측 가능"),
                QuestionOption(label="좌→우", description="현재 무대 x좌표 순"),
                QuestionOption(label="앞→뒤", description="현재 무대 y좌표 순"),
            ),
            why="circle 프리셋은 넘긴 FID 순서대로 채우므로 번갈아 기준이 필요합니다.",
        )
        if answer and ("좌" in answer or "left" in answer.casefold()):
            return "left"
        if answer and ("앞" in answer or "front" in answer.casefold()):
            return "front"
        return "fid"

    def _typed_two_row_layout(self, text: str) -> InstructionResult | None:
        """Place named MMX/350M rows without trusting the CLI model's tool view."""
        if _TYPED_TWO_ROW_REQUEST.search(text) is None:
            return None
        spatial = self._registry.dispatch(
            ToolCall(id="typed-layout-read", name="get_spatial_context", arguments={})
        )
        try:
            payload = json.loads(spatial.result.content)
            fixtures = payload["fixtures"]
            if spatial.result.is_error or payload["coverage"]["complete"] is not True:
                raise ValueError("incomplete spatial read")
            mmx = [
                item["fid"]
                for item in fixtures
                if isinstance(item, dict)
                and isinstance(item.get("fid"), int)
                and "mmx" in str(item.get("name", "")).lower()
            ][:10]
            beam = [
                item["fid"]
                for item in fixtures
                if isinstance(item, dict)
                and isinstance(item.get("fid"), int)
                and re.search(r"350\s*m", str(item.get("name", "")), re.IGNORECASE)
            ][:10]
            if len(mmx) != 10 or len(beam) != 10:
                raise ValueError("fixture types not uniquely identified")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return InstructionResult(
                status="ok",
                text=(
                    "MMX와 350M을 각각 10대로 확정할 수 있는 전체 패치 이름·3D 좌표를 "
                    "읽지 못해 배치를 시작하지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        arranged = self._registry.dispatch(
            ToolCall(
                id="typed-layout-write",
                name="arrange_fixtures",
                arguments={
                    "preset": "grid",
                    "fids": [*beam, *mmx],
                    "rows": 2,
                    "columns": 10,
                    "spacing": 1.5,
                    "orientation": "xy",
                },
            )
        )
        self._last_layout_spacing = (1.5, 1.5)
        return InstructionResult(
            status="ok",
            text="350M 10대 앞줄, MMX 10대 뒷줄의 1.5m 간격 2×10 그리드를 요청했습니다.",
            command_outcomes=arranged.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

    def _vocabulary_layout(self, text: str) -> InstructionResult | None:
        """Apply an explicitly worded whole-rig geometry without model latency."""
        match = match_explicit_layout(text)
        if match is None:
            return None
        if self._spatial_fids is None:
            spatial = self._registry.dispatch(
                ToolCall(id="vocabulary-layout-read", name="get_spatial_context", arguments={})
            )
            try:
                payload = json.loads(spatial.result.content)
                fixtures = payload["fixtures"]
                if spatial.result.is_error or payload["coverage"]["complete"] is not True:
                    raise ValueError("incomplete spatial read")
                fids = tuple(
                    fixture["fid"]
                    for fixture in fixtures
                    if isinstance(fixture, dict)
                    and isinstance(fixture.get("fid"), int)
                    and not isinstance(fixture.get("fid"), bool)
                )
                if not fids or len(fids) != len(fixtures) or len(set(fids)) != len(fids):
                    raise ValueError("invalid fixture identities")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                return InstructionResult(
                    status="ok",
                    text="전체 3D 좌표와 FID를 확인하지 못해 배치를 시작하지 않았습니다.",
                    command_outcomes=(),
                    retries_used=0,
                    model_calls=0,
                    duration_seconds=0.0,
                )
            self._spatial_fids = fids

        arguments: dict[str, object] = {
            "preset": match.preset,
            "fids": list(self._spatial_fids),
        }
        if match.rows is not None:
            arguments["rows"] = match.rows
        if match.columns is not None:
            arguments["columns"] = match.columns
        if match.spacing is not None:
            arguments["spacing"] = match.spacing
        if match.radius is not None:
            arguments["radius"] = match.radius
        if match.preset == "grid" and match.rows * match.columns != len(self._spatial_fids):
            return InstructionResult(
                status="ok",
                text=(
                    f"전체 장비는 {len(self._spatial_fids)}대입니다. 요청한 "
                    f"{match.rows}행×{match.columns}열은 장비 수와 일치하지 않아 "
                    "배치를 시작하지 않았습니다."
                ),
                command_outcomes=(),
                retries_used=0,
                model_calls=0,
                duration_seconds=0.0,
            )
        arranged = self._registry.dispatch(
            ToolCall(
                id="vocabulary-layout-write",
                name="arrange_fixtures",
                arguments=arguments,
            )
        )
        if match.spacing is not None:
            self._last_layout_spacing = (match.spacing, match.spacing)
        labels = {"grid": "그리드", "row": "일렬", "circle": "원형"}
        return InstructionResult(
            status="ok",
            text=(
                f"전체 배치 장비 {len(self._spatial_fids)}대를 {labels[match.preset]} "
                "형태로 배치하도록 요청했습니다."
            ),
            command_outcomes=arranged.command_outcomes,
            retries_used=0,
            model_calls=0,
            duration_seconds=0.0,
        )

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
                result = self._all_fixtures_elevation(text)
                if result is None:
                    result = self._basic_position_presets(text)
                if result is None:
                    result = self._position_cue_sheet(text)
                if result is None:
                    result = self._position_cue_store(text)
                if result is None:
                    result = self._look_pan_tilt(text)
                if result is None:
                    result = self._point_fixtures_at_target(text)
                if result is None:
                    result = self._position_mood_suggestion(text)
                if result is None:
                    result = self._repeating_type_columns_layout(text)
                if result is None:
                    result = self._typed_two_row_layout(text)
                if result is None:
                    result = self._multi_ring_circle_layout(text)
                if result is None:
                    result = self._vocabulary_layout(text)
                if result is None:
                    # No canned clarifiers: an under-specified layout request
                    # (rings, alternation, shapes) goes to the model so it
                    # reasons about the WHOLE request and, if something is truly
                    # missing, asks one question at a time via ask_user — never a
                    # reflexive keyword-triggered line.
                    result = self._orchestrator.handle_instruction(
                        text,
                        history=tuple(self._history),
                        session_context=self._session_context_note(text),
                    )
            except Exception as exc:  # REQ-MVP-044: raw detail NEVER reaches the surface
                event = self._report_error(exc)
                self._record_history(text, event.get("message", ""))
                return event
            self._capture_last_created(result)
            views = [outcome_view(outcome) for outcome in result.command_outcomes]
            summary = self._compose_summary(result, views)
            if self._recorder is not None:
                self._recorder.turn_finished(retries_used=result.retries_used)
            event = chat_response_event(
                status=result.status, summary=summary, text=result.text, commands=views
            )
            self._send(event)
            self._record_history(text, result.text)
            return event
        finally:
            reset_session_key(token)

    def upload_vectorworks_export(self, file_name: str, content_base64: str) -> dict:
        """Replace this session's export and immediately start its guided analysis."""
        self._vectorworks_upload.replace(file_name, content_base64)
        return self.run_instruction(_VECTORWORKS_UPLOAD_INSTRUCTION)

    # -- internals ------------------------------------------------------------------

    def restore_history(self, messages: Sequence[Mapping[str, str]]) -> None:
        """Seed the rolling transcript from the client's persisted UI transcript.

        Refresh survival: the browser keeps the visible conversation in
        localStorage and reinjects it on (re)connect, so the model's cross-turn
        memory continues across a page refresh. Seeds a FRESH session only — a
        session that already holds live turns never lets a late or duplicate
        restore frame overwrite what actually happened here. Wire-level
        validation (roles, non-empty text, length caps) happened in
        ``parse_client_message``; the window cap is re-applied for defence.
        """
        if self._history:
            return
        for item in list(messages)[-HISTORY_MAX_MESSAGES:]:
            if item["role"] == "user":
                self._history.append(UserMessage(text=item["text"]))
            else:
                self._history.append(
                    ModelTurn(
                        text=item["text"],
                        tool_calls=(),
                        stop_reason="end",
                        usage=Usage(),
                        provider="history",
                    )
                )

    def _record_history(self, user_text: str, reply_text: str) -> None:
        """Append this turn's user instruction and assistant reply to memory.

        Only the user-visible exchange is kept — never the intermediate tool
        calls/results — so replaying it is cheap and re-feeds no console side
        effect. The window is trimmed from the front in whole pairs so the
        model never sees a user message stripped of its answer.
        """
        self._history.append(UserMessage(text=user_text))
        self._history.append(
            ModelTurn(
                text=reply_text or "",
                tool_calls=(),
                stop_reason="end",
                usage=Usage(),
                provider="history",
            )
        )
        excess = len(self._history) - HISTORY_MAX_MESSAGES
        if excess > 0:
            del self._history[:excess]

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

    def _ask_one(
        self,
        prompt: str,
        *,
        options: tuple[QuestionOption, ...] = (),
        why: str = "",
        steps: tuple[str, ...] = (),
    ) -> str | None:
        """Ask the operator ONE question through the interactive card channel.

        This is how a direct handler collects a missing decision WITHOUT the
        wall-of-prose failure: the UI renders ``options`` as clickable buttons
        and always offers a free-text box, and the worker thread blocks here
        until exactly one answer returns — so a handler that needs several
        decisions calls this once per decision and the cards appear one at a
        time, never as a single unanswerable message.

        Returns the answer, or ``None`` when no UI is attached or the question
        went unanswered (timeout / disconnect) — the caller then falls back to
        a plain-text prompt instead of hanging.
        """
        if self._question_channel is None:
            return None
        answer = self._question_channel.ask(
            QuestionRequest(prompt=prompt, why=why, steps=steps, options=options)
        )
        if not isinstance(answer, str) or answer in ("", UNANSWERED):
            return None
        return answer

    def _session_context_note(self, text: str = "") -> str | None:
        """Cross-turn grounding plus reasoning aids for THIS instruction.

        ``text`` is the current instruction: recognized layout vocabulary is
        surfaced as guidance so the model REASONS about the whole request and
        asks any genuinely-missing parameter one at a time — replacing the old
        reflexive canned clarifier that fired on a keyword alone.
        """
        notes: list[str] = []
        last = self._last_created
        if last is not None and last.sequence is not None:
            target = f"Sequence {last.sequence}"
            if last.executor is not None:
                target += f" / Executor {last.executor}"
            notes.append(
                f"Session context — the last look you created is on {target}. "
                f'When the user asks to modify that look (e.g. "더 느리게" / make it '
                f"slower), apply the change to {target} — do NOT target an arbitrary "
                f"Sequence or Executor (such as Sequence 1 / Executor 1). Prefer "
                f"regenerating the look on {target} over blind-editing a different "
                f"target."
            )
        if self._last_layout_spacing is not None:
            row_gap, column_gap = self._last_layout_spacing
            notes.append(
                "Session context — the operator already set the layout spacing "
                f"this session: column gap {row_gap:g} m, fixture gap {column_gap:g} m. "
                "Reuse these for any follow-up placement (e.g. 나머지 장비도 배치해줘) "
                "instead of asking for spacing again; only ask for what is genuinely "
                "still missing."
            )
        if self._vectorworks_upload.content_base64 is not None:
            notes.append(
                "Session context — one Vectorworks export is uploaded for this "
                "conversation. Its bytes and any completed report are available only "
                "through vectorworks_autopatch; never request them in chat or infer "
                "details that tool did not report."
            )
        guidance = layout_terms_guidance(text)
        if guidance:
            notes.append(guidance)
        return "\n\n".join(notes) or None

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
