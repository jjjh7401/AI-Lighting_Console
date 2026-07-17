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
DEFAULT_MAX_MODEL_CALLS = 12


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
    def handle_instruction(self, instruction: str) -> InstructionResult:
        """Drive one user instruction through the model↔tool loop."""
        started = self._clock()
        conversation: list[ConversationItem] = [UserMessage(text=instruction)]
        executed_ok: set[str] = set()
        all_outcomes: list[CommandOutcome] = []
        retries_used = 0
        last_run_failed = False
        model_calls = 0
        final_text = ""
        status = "ok"

        while True:
            if model_calls >= self._max_model_calls:
                status = "loop_limit"
                break
            turn = self._provider.complete(
                system_prefix=self._system_prefix,
                conversation=conversation,
                tools=self._registry.definitions(),
            )
            model_calls += 1
            if turn.text:
                final_text = turn.text
            if not turn.tool_calls:
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
