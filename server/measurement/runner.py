"""Measurement runner (M6) — grammar error rate + round trip over the corpus.

Operationalizes the two acceptance measurement procedures over the REAL
orchestrator + safety gate pipeline:

- "문법 오류율 측정 방법": denominator = every model-generated command line
  screened by the gate; numerator = lines the grammar validator rejected on
  their FIRST generation (self-correction success never removes the initial
  error from the numerator); >=3 repetitions with the >=300-line repetition
  escalation rule; per-run rates + pooled rate; judgment on the POOLED rate.
- "왕복 시간 측정 방법": median judgment + p95 report over judged (zero-retry)
  turns, human-approval waits subtracted (recorder semantics), retry turns
  segregated (count + durations, never judged), warm-cache condition (the
  warm-up cold-start turn is excluded and reported as a reference value).

Modes:

- ``mock`` (M6a, default): deterministic scripted provider + in-memory console.
  No LLM API call, no network, no credentials.
- ``live`` (M6b): the SAME corpus and rules against the configured real
  provider (config/provider.toml + API key env) and a live console stack.
  Composed here but NOT executed in M6a — running it requires a provider
  credential and a reachable grandMA3 onPC.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import tempfile
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from server.llm.errors import ProviderError
from server.llm.types import ConversationItem, LLMProvider, ModelTurn, ToolDefinition
from server.measurement.corpus import DEFAULT_CORPUS_PATH, Scenario, load_corpus
from server.measurement.mock_provider import (
    MockScenarioProvider,
    OfflineConsole,
    OfflineDeployPipeline,
)
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.runner import InstructionResult, Orchestrator
from server.orchestrator.tools import build_toolset
from server.rulebook.assembly import assemble_prefix
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate, ScreenDecision
from server.safety.ruleset import load_ruleset
from server.web.measure import RoundTripRecorder
from server.web.session import UNCONFIRMED_MARKER

DEFAULT_ERROR_RATE_THRESHOLD = 0.05  # AC-MVP-002: pooled rate < 5%
DEFAULT_ROUND_TRIP_THRESHOLD_SECONDS = 10.0  # AC-MVP-003: judged median < 10 s


@dataclass(frozen=True)
class RunnerConfig:
    """Measurement run parameters (acceptance-procedure defaults)."""

    repetitions: int = 3
    min_command_lines: int = 300
    max_repetitions: int = 30
    error_rate_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD
    round_trip_threshold_seconds: float = DEFAULT_ROUND_TRIP_THRESHOLD_SECONDS
    warmup: bool = True
    # @MX:NOTE: repetitions=0 previously reached the escalation while-loop
    # with an empty per_run list and crashed on per_run[-1] (IndexError) — see
    # run_measurement's fail-fast check, which rejects this at the door.


class TelemetryBackoffProvider:
    """LLMProvider wrapper: bounded backoff on retryable errors + telemetry.

    Live measurement runs hit free-tier rate limits (429): a retryable
    :class:`ProviderError` triggers exponential backoff (base * 2^attempt,
    capped) up to ``max_attempts`` total attempts, counted per error kind.
    Non-retryable errors (auth, invalid_request, ...) propagate immediately.
    Every successful turn accumulates token usage — the cache-read totals are
    the AC-MVP-014 ② live evidence surface, and the overall totals feed the
    AC-MVP-027 cost input.
    """

    def __init__(
        self,
        inner: LLMProvider,
        *,
        max_attempts: int = 5,
        base_delay_seconds: float = 10.0,
        max_delay_seconds: float = 120.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._inner = inner
        self._max_attempts = max_attempts
        self._base_delay = base_delay_seconds
        self._max_delay = max_delay_seconds
        self._sleep = sleep
        self.model_calls = 0
        self.backoff_retries: Counter[str] = Counter()
        self.usage_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def supports_prompt_caching(self) -> bool:
        return self._inner.supports_prompt_caching

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        attempt = 0
        while True:
            try:
                turn = self._inner.complete(
                    system_prefix=system_prefix, conversation=conversation, tools=tools
                )
            except ProviderError as error:
                if not error.retryable or attempt + 1 >= self._max_attempts:
                    raise
                self.backoff_retries[error.kind] += 1
                self._sleep(min(self._base_delay * (2**attempt), self._max_delay))
                attempt += 1
                continue
            self.model_calls += 1
            usage = turn.usage
            self.usage_totals["input_tokens"] += usage.input_tokens
            self.usage_totals["output_tokens"] += usage.output_tokens
            self.usage_totals["cache_read_tokens"] += usage.cache_read_tokens
            self.usage_totals["cache_write_tokens"] += usage.cache_write_tokens
            return turn


class _CountingBundleGate:
    """BundleGate wrapper accumulating the error-rate numerator/denominator."""

    def __init__(self, gate: SafetyGate) -> None:
        self._gate = gate
        self.denominator = 0
        self.numerator = 0
        self.decision_statuses: Counter[str] = Counter()

    def screen(self, commands: Sequence[str]) -> ScreenDecision:
        decision = self._gate.screen(commands)
        # Every generated command line counts (regenerated lines included).
        self.denominator += len(commands)
        if decision.status == "blocked_grammar":
            # Only the lines the validator itself rejected count — collateral
            # "bundle blocked" companions are not grammar errors.
            self.numerator += sum(
                1
                for d in decision.commands
                if any(reason.startswith("grammar: ") for reason in d.reasons)
            )
        self.decision_statuses[decision.status] += 1
        return decision


class _MeasuredExecutionPort:
    """Marks each RECEIVED console result on the recorder (§2 end event)."""

    def __init__(self, inner, recorder: RoundTripRecorder) -> None:
        self._inner = inner
        self._recorder = recorder

    def execute(self, command: str) -> ExecutionResult:
        result = self._inner.execute(command)
        detail = result.detail or ""
        if not detail.startswith("blocked:") and UNCONFIRMED_MARKER not in detail:
            self._recorder.note_console_result()
        return result


class _MeasuredDeployPipeline:
    """Marks a CONFIRMED deploy as a received console result (§2 end event).

    Closes the M7 gap "deploy turn measurement marking unwired": the deploy
    confirmation is the console feedback that ends a plugin-deploy turn, so
    the turn joins the judged round-trip corpus. Only ``deployed`` marks —
    blocked/rejected outcomes never reached the console, and a failed deploy
    may be an unconfirmed send (conservative, mirrors the execution port).
    """

    def __init__(self, inner, recorder: RoundTripRecorder) -> None:
        self._inner = inner
        self._recorder = recorder

    def deploy(self, name: str, lua_source: str):
        outcome = self._inner.deploy(name, lua_source)
        if outcome.status == "deployed":
            self._recorder.note_console_result()
        return outcome


@dataclass
class MeasurementSession:
    """One wired measurement pipeline (provider + gate + tools + counters)."""

    mode: str
    provider_name: str
    provider_model: str
    supports_prompt_caching: bool
    inference_settings: dict
    orchestrator: Orchestrator
    counter: _CountingBundleGate
    recorder: RoundTripRecorder
    cleanup: Callable[[], None] = field(default=lambda: None)
    telemetry: TelemetryBackoffProvider | None = None

    def run_instruction(self, instruction: str) -> InstructionResult:
        """Drive one corpus instruction with round-trip bracketing."""
        self.recorder.turn_started()
        try:
            result = self.orchestrator.handle_instruction(instruction)
        except Exception:
            self.recorder.turn_finished(retries_used=0, error=True)
            raise
        self.recorder.turn_finished(retries_used=result.retries_used)
        return result


def build_offline_session(
    scenarios: Sequence[Scenario],
    *,
    audit_dir: Path | str | None = None,
    first_attempt_overrides: dict[str, tuple[str, ...]] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> MeasurementSession:
    """Compose the M6a mock pipeline: scripted provider + in-memory console."""
    if audit_dir is None:
        audit_dir = tempfile.mkdtemp(prefix="ma3-measure-audit-")
    gate = SafetyGate(console=OfflineConsole(), audit=AuditLog(audit_dir), ruleset=load_ruleset())
    counter = _CountingBundleGate(gate)
    recorder = RoundTripRecorder(clock=clock)
    registry = build_toolset(
        execution_port=_MeasuredExecutionPort(gate.execution_port, recorder),
        state_port=gate.state_port,
        bundle_gate=counter,
        deploy_pipeline=_MeasuredDeployPipeline(OfflineDeployPipeline(), recorder),
    )
    provider = MockScenarioProvider(scenarios, first_attempt_overrides=first_attempt_overrides)
    orchestrator = Orchestrator(
        provider=provider, registry=registry, system_prefix=assemble_prefix()
    )
    return MeasurementSession(
        mode="mock",
        provider_name=provider.name,
        provider_model=provider.model_id,
        supports_prompt_caching=provider.supports_prompt_caching,
        inference_settings={
            "note": "deterministic scripted mock provider — no model inference settings apply",
        },
        orchestrator=orchestrator,
        counter=counter,
        recorder=recorder,
    )


def build_live_llm_session(
    *,
    config_path: Path | str | None = None,
    audit_dir: Path | str | None = None,
    provider_override: LLMProvider | None = None,
    backoff_max_attempts: int = 5,
    backoff_base_delay_seconds: float = 10.0,
    sleep: Callable[[float], None] = time.sleep,
) -> MeasurementSession:
    """Compose the M6b-1 pipeline: LIVE provider + OFFLINE (mock) console.

    Grammar-error-rate live measurement without a console: the model is real
    (config + API key env), the console side is the in-memory mock, so
    round-trip figures from this mode are REFERENCE ONLY — never AC-MVP-003
    evidence. ``provider_override`` injects a scripted provider for offline
    tests of this composition.
    """
    from server.llm.config import DEFAULT_CONFIG_PATH, load_provider_config
    from server.llm.factory import build_provider

    provider_config = load_provider_config(config_path or DEFAULT_CONFIG_PATH)
    inner = provider_override if provider_override is not None else build_provider(provider_config)
    provider = TelemetryBackoffProvider(
        inner,
        max_attempts=backoff_max_attempts,
        base_delay_seconds=backoff_base_delay_seconds,
        sleep=sleep,
    )
    if audit_dir is None:
        audit_dir = tempfile.mkdtemp(prefix="ma3-measure-audit-")
    gate = SafetyGate(console=OfflineConsole(), audit=AuditLog(audit_dir), ruleset=load_ruleset())
    counter = _CountingBundleGate(gate)
    recorder = RoundTripRecorder()
    registry = build_toolset(
        execution_port=_MeasuredExecutionPort(gate.execution_port, recorder),
        state_port=gate.state_port,
        bundle_gate=counter,
        deploy_pipeline=_MeasuredDeployPipeline(OfflineDeployPipeline(), recorder),
    )
    orchestrator = Orchestrator(
        provider=provider, registry=registry, system_prefix=assemble_prefix()
    )
    active = provider_config.active
    settings = provider_config.anthropic if active == "anthropic" else provider_config.gemini
    return MeasurementSession(
        mode="live-llm-mock-console",
        provider_name=provider.name,
        provider_model=provider.model_id,
        supports_prompt_caching=provider.supports_prompt_caching,
        # Acceptance §5: the pinned production inference settings are recorded.
        inference_settings={k: getattr(settings, k) for k in settings.__dataclass_fields__},
        orchestrator=orchestrator,
        counter=counter,
        recorder=recorder,
        telemetry=provider,
    )


def build_live_session(
    *,
    config_path: Path | str | None = None,
    send_host: str = "127.0.0.1",
    send_port: int = 8000,
    receive_port: int = 9000,
    audit_dir: Path | str | None = None,
) -> MeasurementSession:
    """Compose the M6b live pipeline (real provider + live console stack).

    NOT executed in M6a: constructing the adapter requires a provider API key
    in the environment, and measurements require a reachable grandMA3 onPC.
    Deploy scenarios additionally need a review channel (server session) and
    are expected to be run through the web server in M6b — this headless
    composition leaves the deploy pipeline unwired (deny-by-default).
    """
    from server.llm.config import DEFAULT_CONFIG_PATH, load_provider_config
    from server.llm.factory import build_provider
    from server.safety.bootstrap import build_console_stack

    provider_config = load_provider_config(config_path or DEFAULT_CONFIG_PATH)
    provider = build_provider(provider_config)
    stack = build_console_stack(
        send_host=send_host,
        send_port=send_port,
        receive_port=receive_port,
        **({"audit_dir": audit_dir} if audit_dir is not None else {}),
    )
    counter = _CountingBundleGate(stack.gate)
    recorder = RoundTripRecorder()
    registry = build_toolset(
        execution_port=_MeasuredExecutionPort(stack.gate.execution_port, recorder),
        state_port=stack.gate.state_port,
        bundle_gate=counter,
        deploy_pipeline=None,
    )
    orchestrator = Orchestrator(
        provider=provider, registry=registry, system_prefix=assemble_prefix()
    )
    active = provider_config.active
    settings = provider_config.anthropic if active == "anthropic" else provider_config.gemini
    return MeasurementSession(
        mode="live",
        provider_name=provider.name,
        provider_model=provider.model_id,
        supports_prompt_caching=provider.supports_prompt_caching,
        # Acceptance §5: the pinned production inference settings are recorded.
        inference_settings={k: getattr(settings, k) for k in settings.__dataclass_fields__},
        orchestrator=orchestrator,
        counter=counter,
        recorder=recorder,
        cleanup=stack.stop,
    )


def _percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def run_measurement(
    scenarios: Sequence[Scenario],
    session: MeasurementSession,
    config: RunnerConfig,
) -> dict:
    """Run the measurement procedure and build the machine-readable report."""
    if config.repetitions < 1:
        raise ValueError("run_measurement requires config.repetitions >= 1 (got 0)")
    run_started = time.monotonic()
    statuses: Counter[str] = Counter()

    def run_one(instruction: str) -> None:
        # Live-run containment: one instruction's provider failure (backoff
        # exhausted or non-retryable) is recorded by kind and the run goes on.
        # Any OTHER exception (a bug, an unwrapped SDK error) is contained the
        # same way — the containment guarantee is general, not ProviderError-
        # specific — so a single bad turn never crashes the whole measurement
        # run and discards every scenario already processed.
        try:
            result = session.run_instruction(instruction)
        except ProviderError as error:
            statuses[f"provider_error:{error.kind}"] += 1
            return
        except Exception as error:  # live-run containment — see module docstring
            statuses[f"unexpected_error:{type(error).__name__}"] += 1
            return
        statuses[result.status] += 1

    cold_start_reference: float | None = None
    if config.warmup:
        # Warm-up turn (§3 warm-cache condition): excluded from every corpus
        # statistic; its duration is reported as the cold-start reference.
        run_one(scenarios[0].instruction)
        statuses.clear()  # the warm-up turn is not a corpus turn
        warmup_record = session.recorder.records[-1]
        cold_start_reference = warmup_record.measured_seconds
    base_denominator = session.counter.denominator
    base_numerator = session.counter.numerator
    records_offset = len(session.recorder.records)

    per_run: list[dict] = []

    def run_round() -> None:
        before_den = session.counter.denominator
        before_num = session.counter.numerator
        for scenario in scenarios:
            run_one(scenario.instruction)
        denominator = session.counter.denominator - before_den
        numerator = session.counter.numerator - before_num
        per_run.append(
            {
                "run": len(per_run) + 1,
                "denominator": denominator,
                "numerator": numerator,
                "rate": (numerator / denominator) if denominator else 0.0,
            }
        )

    for _ in range(config.repetitions):
        run_round()
    escalated = False
    # Acceptance §3: when the denominator falls short of the >=300-line floor,
    # repetitions are increased until it is satisfied (bounded by the config).
    # Quota guard: a round that added ZERO lines means escalation can never
    # converge (e.g. every turn fails) — stop instead of burning API calls.
    while (
        session.counter.denominator - base_denominator < config.min_command_lines
        and len(per_run) < config.max_repetitions
        and per_run[-1]["denominator"] > 0
    ):
        escalated = True
        run_round()

    denominator = session.counter.denominator - base_denominator
    numerator = session.counter.numerator - base_numerator
    pooled_rate = (numerator / denominator) if denominator else 0.0

    records = session.recorder.records[records_offset:]
    judged = [r.measured_seconds for r in records if r.judged]
    retry_records = [r for r in records if r.retries_used > 0]
    unjudged = sum(1 for r in records if r.retries_used == 0 and not r.judged)
    median = statistics.median(judged) if judged else None
    p95 = _percentile_95(judged) if judged else None

    anomalies = {
        status: count
        for status, count in session.counter.decision_statuses.items()
        if status not in ("cleared", "blocked_grammar")
    }

    report: dict = {
        "generated_at": datetime.now(UTC).isoformat(),
        "wall_clock_seconds": round(time.monotonic() - run_started, 3),
        "mode": session.mode,
        "provider": {
            "name": session.provider_name,
            "model": session.provider_model,
            "supports_prompt_caching": session.supports_prompt_caching,
        },
        "inference_settings": session.inference_settings,
        "corpus": {
            "scenarios": len(scenarios),
            "task_types": dict(Counter(s.task_type for s in scenarios)),
            "field_term_scenarios": sum(1 for s in scenarios if s.field_terms),
        },
        "repetitions": {
            "configured": config.repetitions,
            "executed": len(per_run),
            "escalated": escalated,
            "min_command_lines": config.min_command_lines,
            "denominator_satisfied": denominator >= config.min_command_lines,
        },
        "grammar_error_rate": {
            "denominator_lines": denominator,
            "numerator_first_generation_rejections": numerator,
            "pooled_rate": pooled_rate,
            "per_run": per_run,
            "threshold": config.error_rate_threshold,
            "pooled_pass": pooled_rate < config.error_rate_threshold,
        },
        "round_trip": {
            "judged_turns": len(judged),
            "median_seconds": median,
            "p95_seconds": p95,
            "retry_turns": {
                "count": len(retry_records),
                "durations_seconds": [r.measured_seconds for r in retry_records],
            },
            "unjudged_turns": unjudged,
            "cold_start_reference_seconds": cold_start_reference,
            "warm_cache": config.warmup,
            "threshold_seconds": config.round_trip_threshold_seconds,
            "median_pass": (
                median < config.round_trip_threshold_seconds if median is not None else None
            ),
        },
        "turn_statuses": dict(statuses),
        "gate_anomalies": anomalies,
    }
    if session.telemetry is not None:
        report["provider_telemetry"] = {
            "model_calls": session.telemetry.model_calls,
            "usage_totals": dict(session.telemetry.usage_totals),
            "backoff_retries": dict(session.telemetry.backoff_retries),
        }
    return report


def format_summary(report: dict) -> str:
    """Human-readable one-screen summary of a measurement report."""
    rate = report["grammar_error_rate"]
    round_trip = report["round_trip"]
    reps = report["repetitions"]
    lines = [
        f"measurement report — mode={report['mode']}, provider={report['provider']['name']}"
        f" ({report['provider']['model']})",
        f"repetitions: {reps['executed']} executed"
        f" (configured {reps['configured']}, escalated={reps['escalated']})",
        f"grammar error rate: pooled {rate['pooled_rate']:.4f}"
        f" = {rate['numerator_first_generation_rejections']}/{rate['denominator_lines']} lines"
        f" (threshold {rate['threshold']:.2%}, pass={rate['pooled_pass']})",
        "per-run rates: " + ", ".join(f"run{e['run']}={e['rate']:.4f}" for e in rate["per_run"]),
        f"round trip: median {round_trip['median_seconds']}s"
        f" / p95 {round_trip['p95_seconds']}s over {round_trip['judged_turns']} judged turns"
        f" (median pass={round_trip['median_pass']})",
        f"retry turns (segregated): {round_trip['retry_turns']['count']}"
        f" | unjudged turns: {round_trip['unjudged_turns']}"
        f" | cold-start reference: {round_trip['cold_start_reference_seconds']}s",
    ]
    if report["gate_anomalies"]:
        lines.append(f"gate anomalies: {report['gate_anomalies']}")
    telemetry = report.get("provider_telemetry")
    if telemetry is not None:
        lines.append(
            f"provider telemetry: {telemetry['model_calls']} model calls"
            f" | usage {telemetry['usage_totals']}"
            f" | backoff retries {telemetry['backoff_retries']}"
            f" | wall clock {report.get('wall_clock_seconds')}s"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MA3 copilot measurement runner (M6)")
    parser.add_argument("--mode", choices=("mock", "live-llm", "live"), default="mock")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--output", type=Path, default=None, help="write the JSON report here")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--min-command-lines", type=int, default=300)
    parser.add_argument("--max-repetitions", type=int, default=30)
    parser.add_argument("--scenario-limit", type=int, default=None, help="first N scenarios only")
    parser.add_argument("--no-warmup", action="store_true")
    parser.add_argument("--audit-dir", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None, help="provider TOML (live modes)")
    parser.add_argument("--backoff-max-attempts", type=int, default=5)
    parser.add_argument("--backoff-base-delay", type=float, default=10.0)
    parser.add_argument("--console-host", default="127.0.0.1")
    parser.add_argument("--console-port", type=int, default=8000)
    parser.add_argument("--receive-port", type=int, default=9000)
    args = parser.parse_args(argv)

    scenarios = load_corpus(args.corpus)
    if args.scenario_limit is not None:
        scenarios = scenarios[: args.scenario_limit]
    config = RunnerConfig(
        repetitions=args.repetitions,
        min_command_lines=args.min_command_lines,
        max_repetitions=args.max_repetitions,
        warmup=not args.no_warmup,
    )
    if args.mode == "mock":
        session = build_offline_session(scenarios, audit_dir=args.audit_dir)
    elif args.mode == "live-llm":
        session = build_live_llm_session(
            config_path=args.config,
            audit_dir=args.audit_dir,
            backoff_max_attempts=args.backoff_max_attempts,
            backoff_base_delay_seconds=args.backoff_base_delay,
        )
    else:
        session = build_live_session(
            config_path=args.config,
            send_host=args.console_host,
            send_port=args.console_port,
            receive_port=args.receive_port,
            audit_dir=args.audit_dir,
        )
    try:
        report = run_measurement(scenarios, session, config)
    finally:
        session.cleanup()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(format_summary(report))
    return 0


if __name__ == "__main__":  # pragma: no cover — CLI entry
    raise SystemExit(main())
