"""Instruction orchestrator — provider-neutral tool loop with self-correction.

One :meth:`Orchestrator.handle_instruction` call drives one user instruction to
completion: the model plans, calls tools, receives per-command error feedback,
and self-corrects (REQ-MVP-009) under a HARD cap of 3 retries per instruction
(REQ-MVP-010 — on exhaustion a structured failure report is returned, never a
4th correction round). Commands that already executed successfully within the
instruction are never re-executed (REQ-MVP-033 execution-time atomicity, M3
scope — bundle-level gate atomicity lands in M4).

Provider neutrality (REQ-MVP-038): this module binds ONLY to the neutral
LLMProvider interface and never inspects provider identity.

Measurement support (REQ-MVP-040, M3 scope): per-instruction metrics go to an
injectable metrics sink, and clean (zero-retry) turn durations feed the
fallback detector — retry turns are excluded, mirroring the acceptance
round-trip measurement rules.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from server.llm.types import (
    ConversationItem,
    LLMProvider,
    ModelTurn,
    ToolDefinition,
    ToolResult,
    ToolResultsMessage,
    UserMessage,
)
from server.orchestrator.fallback import FallbackDetector
from server.orchestrator.tools import CommandOutcome, ExecutionContext, ToolRegistry

# REQ-MVP-010: never more than 3 self-correction rounds per instruction.
MAX_RETRIES = 3

# Cost guard for runaway tool loops (constraint: bounded token spend per turn).
#
# [round24 후속] 12에서 24로. 12는 「명령 한 줄 -> 실행 한 번」 시절의 눈금이었다.
# 실물 패치 한 건을 끝까지 몰아 재 보니 **15회**가 들었다 — 타입 확인, 주소 자리
# 확인, 리그 판독, 프리체크, 상태 조회 여러 번, 플러그인 배포와 실행. 여기에
# 사람 왕복 3회가 더 얹혀 한도를 넘겼고, 대화는 마지막 한 걸음을 남기고 끊겼다.
# 가드를 없애는 것이 아니라 **실측에 맞춘다**: 24는 그 15회에 검증 읽기와 정정
# 여유를 더한 값이고, 폭주는 여전히 유한한 자리에서 끊긴다.
DEFAULT_MAX_MODEL_CALLS = 24

# The model sometimes ENDS a turn by claiming the app's tools are not connected
# ("No such tool available", "도구가 연결돼 있지 않다") and writing prose instead
# of emitting a tool_call — even though the tools ARE registered and offered on
# every turn. That is a hallucination, not a real failure: a genuine tool error
# arrives THROUGH a tool_call + ToolResult, never as a bare text claim on a turn
# with zero tool_calls. When it happens we nudge ONCE and let the model retry,
# so a whole request does not dead-end on a false "unavailable" report.
_TOOL_UNAVAILABLE_MARKERS = (
    "no such tool",
    "tool available",
    "도구가 연결",
    "연결돼 있지 않",
    "연결되어 있지 않",
    "붙어 있지 않",
    "올라와 있지 않",
    "사용할 수 없는 도구",
    "mcp가 없",
    "mcp 연결",
)
MAX_UNAVAILABLE_CORRECTIONS = 1

_TOOLS_ARE_AVAILABLE = (
    "그 도구들(get_spatial_context·arrange_fixtures·ask_user 등)은 이 앱에 실제로 "
    "연결되어 있다. '없다 / 연결 안 됨 / No such tool'이라고 말하지 말고, 지금 필요한 "
    "호출을 tool_calls로 내보내라. 배치·이동·높이 변경은 먼저 get_spatial_context로 "
    "실제 FID를 읽고, 확인이 필요한 값이 있으면 ask_user를 한 번에 하나씩 호출해 "
    "물어라 — 채팅 본문에 여러 질문을 늘어놓지 마라."
)


def _claims_tool_unavailable(text: str) -> bool:
    """True when a tool-less turn falsely reports the app tools as unavailable."""
    lowered = text.casefold()
    return any(marker in lowered for marker in _TOOL_UNAVAILABLE_MARKERS)


@dataclass(frozen=True)
class InstructionResult:
    """The outcome of one handled instruction (failure report included)."""

    status: str  # "ok" | "retries_exhausted" | "loop_limit"
    text: str
    command_outcomes: tuple[CommandOutcome, ...]
    retries_used: int
    model_calls: int
    duration_seconds: float


@dataclass(frozen=True)
class TurnMetrics:
    """Per-instruction measurement record (error-rate/round-trip inputs, M6)."""

    provider: str
    model: str
    status: str
    duration_seconds: float
    retries_used: int
    commands_generated: int
    commands_failed: int


class MetricsSink(Protocol):
    """Receives per-instruction metrics (provider selection inputs, REQ-MVP-040)."""

    def record_turn(self, metrics: TurnMetrics) -> None:
        """Persist/forward one instruction's metrics."""
        ...


class SwitchableProvider:
    """Runtime-swappable :class:`LLMProvider` indirection (AC-MVP-027 part 3,
    REQ-MVP-039/040 ii config-switch).

    Wraps a small registry of already-built adapters keyed by provider name.
    An :class:`Orchestrator` holds ``self._provider`` exactly as before — this
    class simply satisfies the ``LLMProvider`` protocol via delegation, so
    ``handle_instruction()`` requires no change to switch providers mid-run.
    A :class:`~server.orchestrator.fallback.FallbackDetector`'s ``on_fallback``
    callback is wired to :meth:`switch_to` so a persistent-miss decision
    actually changes which adapter the NEXT judged turn calls, instead of
    requiring a human to edit config and restart the process.
    """

    def __init__(self, registry: dict[str, LLMProvider], *, active_name: str) -> None:
        if active_name not in registry:
            raise KeyError(f"active provider {active_name!r} not present in registry")
        self._registry = registry
        self._active_name = active_name

    @property
    def name(self) -> str:
        return self._registry[self._active_name].name

    @property
    def model_id(self) -> str:
        return self._registry[self._active_name].model_id

    @property
    def supports_prompt_caching(self) -> bool:
        return self._registry[self._active_name].supports_prompt_caching

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        return self._registry[self._active_name].complete(
            system_prefix=system_prefix, conversation=conversation, tools=tools
        )

    def switch_to(self, name: str) -> None:
        """Swap the active adapter (invoked as a FallbackDetector on_fallback
        callback); an unknown name is a no-op — the registry is the only
        source of truth for what a valid switch target is."""
        if name in self._registry:
            self._active_name = name


class Orchestrator:
    """Runs the model↔tool loop for one instruction at a time."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        registry: ToolRegistry,
        system_prefix: str,
        max_retries: int = MAX_RETRIES,
        max_model_calls: int = DEFAULT_MAX_MODEL_CALLS,
        fallback_detector: FallbackDetector | None = None,
        metrics_sink: MetricsSink | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._system_prefix = system_prefix
        self._max_retries = max_retries
        self._max_model_calls = max_model_calls
        self._fallback_detector = fallback_detector
        self._metrics_sink = metrics_sink
        self._clock = clock

    # @MX:NOTE: [AUTO] self-correction loop — retry accounting (<=3 per instruction,
    #   REQ-MVP-010) and the executed-command dedupe set both live ONLY here
    #: 한도에 걸렸을 때 마지막으로 한 번만 더 부른다 — **도구 없이.** 도구를 주면
    #: 그 자리에서 또 루프가 시작되므로 가드가 무의미해진다.
    _WRAP_UP = (
        "여기까지의 진행을 한국어로 짧게 정리하라. 새 도구를 부르지 말라. "
        "**이미 사용자가 답한 것은 결정된 것이다** — 같은 것을 다시 묻지 말고 "
        "그 결정을 확정 사항으로 적어라. 아직 못 한 일과 사용자가 다음에 해야 할 "
        "일만 남은 것으로 적고, 하지 않은 일을 했다고 말하지 마라."
    )

    def _closing_words(self, conversation: list[ConversationItem]) -> str:
        """한도에 걸려도 사용자에게 **말은 남긴다.**

        정확히 한 번만 더 부른다 — 비용은 1회로 묶이고, 도구를 주지 않으므로
        여기서 루프가 되살아날 수 없다. 이 호출이 실패하면 조용히 빈 글을 내되,
        예외가 턴을 죽이지는 않게 한다.
        """
        try:
            closing = self._provider.complete(
                system_prefix=self._system_prefix,
                conversation=[*conversation, UserMessage(text=self._WRAP_UP)],
                tools=(),
            )
        except Exception:
            return ""
        return closing.text or ""

    def handle_instruction(
        self,
        instruction: str,
        history: Sequence[ConversationItem] = (),
        session_context: str | None = None,
    ) -> InstructionResult:
        """Drive one user instruction through the model↔tool loop.

        ``history`` is the prior conversation transcript (earlier user
        instructions and the assistant's replies) this session has accumulated.
        Prepending it is what lets the model keep CONTEXT across turns: without
        it every turn is stateless and the model answers each message in
        isolation, forgetting an in-progress task the moment the turn ends.
        Intermediate tool calls/results are deliberately NOT replayed — only the
        user-visible exchange — so history stays compact and no console side
        effect is re-fed to the loop.

        ``session_context`` (REQ-DEPLOY-030, #4): when supplied, a synthetic
        UserMessage carrying cross-turn state (the last-created look's target
        identity + a regenerate-don't-blind-edit steer) is appended AFTER the
        history and BEFORE the instruction, so a bare follow-up modification
        anchors to the real target. Default ``None`` keeps the conversation
        byte-identical for every existing caller that passes neither argument.
        """
        started = self._clock()
        conversation: list[ConversationItem] = list(history)
        if session_context:
            conversation.append(UserMessage(text=session_context))
        conversation.append(UserMessage(text=instruction))
        executed_ok: set[str] = set()
        all_outcomes: list[CommandOutcome] = []
        retries_used = 0
        last_run_failed = False
        model_calls = 0
        #: 사람이 답을 준 횟수 — 폭주 가드에서 제외한다(아래 dispatch 루프 참조).
        human_turns = 0
        final_text = ""
        status = "ok"
        tool_definitions = self._registry.definitions()
        unavailable_corrections = 0

        while True:
            if model_calls - human_turns >= self._max_model_calls:
                status = "loop_limit"
                # 가드는 **도구 루프**를 끊는 것이지 답을 삼키는 것이 아니다.
                # 실측: 사용자가 질문 카드 셋에 답하며 끝까지 따라왔는데
                # `text=0자`로 끝나 화면에 아무것도 안 남았다.
                final_text = final_text or self._closing_words(conversation)
                break
            turn = self._provider.complete(
                system_prefix=self._system_prefix,
                conversation=conversation,
                tools=tool_definitions,
            )
            model_calls += 1
            if turn.text:
                final_text = turn.text
            if not turn.tool_calls:
                if (
                    tool_definitions
                    and unavailable_corrections < MAX_UNAVAILABLE_CORRECTIONS
                    and _claims_tool_unavailable(turn.text)
                ):
                    # False "tools unavailable" report on a turn with zero
                    # tool_calls: keep it for context, tell the model the tools
                    # ARE connected, and let it retry with real tool_calls.
                    # Bounded so a model that insists cannot loop — after the
                    # cap we accept its text as the final answer.
                    unavailable_corrections += 1
                    conversation.append(turn)
                    conversation.append(UserMessage(text=_TOOLS_ARE_AVAILABLE))
                    continue
                break  # final answer — instruction complete
            conversation.append(turn)
            # A correction round is charged AT MOST ONCE per model turn, at
            # the turn boundary: `last_run_failed` here reflects the PRIOR
            # turn's outcome (error already fed back to the model), never a
            # failure that happens later in the loop below. Deciding this
            # BEFORE the dispatch loop (rather than per tool call) prevents a
            # within-turn multi-tool-call bundle from being over-counted —
            # e.g. call 1 failing must not charge call 2 in the SAME turn,
            # since no error feedback occurred between them (M6c-3 Finding 3,
            # REQ-MVP-009/010 accounting correctness).
            has_retryable_call = any(
                call.name in ("run_commands", "deploy_plugin") for call in turn.tool_calls
            )
            if last_run_failed and has_retryable_call:
                # M7: a corrected deploy_plugin attempt counts the same —
                # compile failures share the <=3 cap (REQ-MVP-010).
                retries_used += 1
            last_run_failed = False
            results: list[ToolResult] = []
            for call in turn.tool_calls:
                execution = self._registry.dispatch(
                    call, ExecutionContext(executed_ok=frozenset(executed_ok))
                )
                results.append(execution.result)
                if execution.awaited_human:
                    # 사람이 카드에 답한 회차는 폭주가 아니다 — 가드에서 뺀다.
                    # 실측: 질문 3회를 거치면 12회 한도가 말라 `loop_limit` ·
                    # 본문 0자로 끝났고, 사용자는 답을 한 글자도 못 받았다.
                    # 사람 왕복은 사람이 스스로 멈추므로 폭주할 수 없다.
                    human_turns += 1
                if execution.command_outcomes:
                    all_outcomes.extend(execution.command_outcomes)
                    for outcome in execution.command_outcomes:
                        if outcome.status == "executed_ok":
                            executed_ok.add(outcome.command)
                    # "failed" = console error; "blocked" = gate block (M4 —
                    # e.g. grammar, REQ-MVP-012): both feed the correction
                    # loop and count toward the retry cap. Human rejections
                    # and lock proposals are NOT technical failures.
                    if any(o.status in ("failed", "blocked") for o in execution.command_outcomes):
                        last_run_failed = True
            conversation.append(ToolResultsMessage(results=tuple(results)))
            if last_run_failed and retries_used >= self._max_retries:
                # Hard cap reached: report failure to the user, no 4th round.
                status = "retries_exhausted"
                break

        duration = self._clock() - started
        result = InstructionResult(
            status=status,
            text=final_text,
            command_outcomes=tuple(all_outcomes),
            retries_used=retries_used,
            model_calls=model_calls,
            duration_seconds=duration,
        )
        if self._metrics_sink is not None:
            self._metrics_sink.record_turn(
                TurnMetrics(
                    provider=self._provider.name,
                    model=self._provider.model_id,
                    status=status,
                    duration_seconds=duration,
                    retries_used=retries_used,
                    commands_generated=len(all_outcomes),
                    commands_failed=sum(1 for o in all_outcomes if o.status == "failed"),
                )
            )
        if self._fallback_detector is not None and retries_used == 0:
            # Judged turns only — retry turns are excluded from the fallback
            # feed (acceptance round-trip measurement rule 4).
            self._fallback_detector.observe_turn(duration)
        return result
