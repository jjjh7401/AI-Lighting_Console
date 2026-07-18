"""Measurement runner tests (M6a — AC-MVP-002/003 machinery, offline mock mode).

The runner drives the measurement corpus through the REAL orchestrator +
safety gate with a deterministic scripted provider and an in-memory console:

- grammar error rate per acceptance "문법 오류율 측정 방법": denominator =
  every model-generated command line, numerator = validator-rejected lines on
  the FIRST generation (self-correction success never removes the error),
  >=3 repetitions with the >=300-line repetition escalation rule, pooled +
  per-run rates.
- round trip per acceptance "왕복 시간 측정 방법": median judgment + p95
  report, retry turns segregated (never judged), warm-cache (the cold-start
  warm-up turn is excluded and reported as a reference value).

HARD offline constraint: no LLM API call, no network, no credentials — the
suite must pass with every provider API key removed from the environment.
"""

from __future__ import annotations

import json

import pytest

from server.measurement.corpus import Scenario, load_corpus
from server.measurement.runner import (
    RunnerConfig,
    build_offline_session,
    format_summary,
    run_measurement,
)


@pytest.fixture(autouse=True)
def no_provider_credentials(monkeypatch):
    # Mock mode MUST work without any provider credential in the environment.
    for key in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(scope="module")
def corpus() -> tuple[Scenario, ...]:
    return load_corpus()


def _quick_config(**overrides) -> RunnerConfig:
    defaults = dict(repetitions=1, min_command_lines=1, warmup=False)
    defaults.update(overrides)
    return RunnerConfig(**defaults)


def _total_mock_lines(corpus) -> int:
    return sum(len(s.mock.commands) for s in corpus)


class TestHappyPathCounting:
    def test_denominator_counts_every_generated_command_line(self, corpus, tmp_path):
        session = build_offline_session(corpus, audit_dir=tmp_path)
        report = run_measurement(corpus, session, _quick_config())
        rate = report["grammar_error_rate"]
        assert rate["denominator_lines"] == _total_mock_lines(corpus)
        assert rate["numerator_first_generation_rejections"] == 0
        assert rate["pooled_rate"] == 0.0
        assert rate["pooled_pass"] is True

    def test_happy_path_produces_no_gate_anomalies(self, corpus, tmp_path):
        # The baseline corpus must CLEAR the gate: no rejection, no hold, no
        # grammar block, no lock proposal — anomalies would poison the rates.
        session = build_offline_session(corpus, audit_dir=tmp_path)
        report = run_measurement(corpus, session, _quick_config())
        assert report["gate_anomalies"] == {}
        assert set(report["turn_statuses"]) == {"ok"}

    def test_per_run_rates_reported_per_repetition(self, corpus, tmp_path):
        session = build_offline_session(corpus, audit_dir=tmp_path)
        report = run_measurement(corpus, session, _quick_config(repetitions=2))
        per_run = report["grammar_error_rate"]["per_run"]
        assert len(per_run) == 2
        for entry in per_run:
            assert entry["denominator"] == _total_mock_lines(corpus)
            assert entry["numerator"] == 0
            assert entry["rate"] == 0.0


class TestFirstGenerationErrorAccounting:
    def test_first_generation_rejection_counts_even_after_correction(self, corpus, tmp_path):
        # Acceptance §4: the FIRST generation's grammar rejection stays in the
        # numerator even though self-correction later succeeds.
        target = next(s for s in corpus if s.mock.kind == "commands")
        bad_bundle = ("123 잘못된 명령",) + target.mock.commands
        session = build_offline_session(
            corpus,
            audit_dir=tmp_path,
            first_attempt_overrides={target.instruction: bad_bundle},
        )
        report = run_measurement(corpus, session, _quick_config())
        rate = report["grammar_error_rate"]
        # Denominator: happy lines + the extra first (bad) bundle re-screened.
        assert rate["denominator_lines"] == _total_mock_lines(corpus) + len(bad_bundle)
        assert rate["numerator_first_generation_rejections"] == 1
        assert rate["pooled_rate"] == pytest.approx(1 / rate["denominator_lines"])
        # The correction succeeded — the turn itself ends ok.
        assert report["turn_statuses"].get("ok") == len(corpus)

    def test_retry_turn_is_segregated_from_the_judged_corpus(self, corpus, tmp_path):
        target = next(s for s in corpus if s.mock.kind == "commands")
        bad_bundle = ("123 잘못된 명령",) + target.mock.commands
        session = build_offline_session(
            corpus,
            audit_dir=tmp_path,
            first_attempt_overrides={target.instruction: bad_bundle},
        )
        report = run_measurement(corpus, session, _quick_config())
        round_trip = report["round_trip"]
        result_scenarios = sum(1 for s in corpus if s.mock.kind in ("commands", "plugin"))
        # The corrected scenario used one retry -> excluded from judgment.
        assert round_trip["retry_turns"]["count"] == 1
        assert len(round_trip["retry_turns"]["durations_seconds"]) == 1
        assert round_trip["judged_turns"] == result_scenarios - 1


class TestRepetitionEscalation:
    def test_repetitions_escalate_until_min_denominator(self, corpus, tmp_path):
        session = build_offline_session(corpus, audit_dir=tmp_path)
        config = RunnerConfig(repetitions=3, min_command_lines=300, warmup=False)
        report = run_measurement(corpus, session, config)
        reps = report["repetitions"]
        assert reps["configured"] == 3
        assert reps["executed"] > 3
        assert reps["escalated"] is True
        assert reps["denominator_satisfied"] is True
        assert report["grammar_error_rate"]["denominator_lines"] >= 300
        assert len(report["grammar_error_rate"]["per_run"]) == reps["executed"]


class TestEscalationSafety:
    def test_escalation_halts_when_rounds_generate_no_lines(self, corpus, tmp_path):
        # Quota guard (first live smoke finding): when every round adds ZERO
        # command lines (e.g. all turns fail), escalating repetitions can
        # never reach the denominator floor — the loop must stop instead of
        # burning max_repetitions rounds of live API calls.
        query_only = tuple(s for s in corpus if s.mock.kind == "query")
        session = build_offline_session(query_only, audit_dir=tmp_path)
        config = RunnerConfig(repetitions=1, min_command_lines=10, warmup=False)
        report = run_measurement(query_only, session, config)
        assert report["repetitions"]["executed"] == 1  # no futile escalation
        assert report["repetitions"]["denominator_satisfied"] is False


class TestRoundTripStats:
    def test_judged_median_p95_and_warm_cache_exclusion(self, corpus, tmp_path):
        session = build_offline_session(corpus, audit_dir=tmp_path)
        report = run_measurement(corpus, session, _quick_config(warmup=True))
        round_trip = report["round_trip"]
        result_scenarios = sum(1 for s in corpus if s.mock.kind in ("commands", "plugin"))
        # Judged = zero-retry turns with >=1 console result: command scenarios
        # AND deploy scenarios (the confirmed deploy IS the console feedback —
        # closes the M7 gap "deploy turn measurement marking unwired").
        assert round_trip["judged_turns"] == result_scenarios
        assert round_trip["median_seconds"] >= 0.0
        assert round_trip["p95_seconds"] >= round_trip["median_seconds"]
        assert round_trip["warm_cache"] is True
        # The warm-up (cold-start) turn is excluded and reported separately.
        assert round_trip["cold_start_reference_seconds"] is not None
        assert round_trip["retry_turns"]["count"] == 0
        assert round_trip["median_pass"] is True

    def test_query_turns_are_unjudged_but_plugin_turns_are_judged(self, corpus, tmp_path):
        # AC-MVP-001's 10 task types include "Lua 플러그인 배포": a deployed
        # plugin turn received its console confirmation, so it belongs to the
        # judged round-trip corpus; a pure state query receives no execution
        # result and stays unjudged.
        session = build_offline_session(corpus, audit_dir=tmp_path)
        report = run_measurement(corpus, session, _quick_config())
        query_only = sum(1 for s in corpus if s.mock.kind == "query")
        assert report["round_trip"]["unjudged_turns"] == query_only


class TestReportSurface:
    def test_report_is_json_serializable_with_fixed_settings_recorded(self, corpus, tmp_path):
        session = build_offline_session(corpus, audit_dir=tmp_path)
        report = run_measurement(corpus, session, _quick_config())
        payload = json.loads(json.dumps(report, ensure_ascii=False))
        assert payload["mode"] == "mock"
        assert payload["provider"]["name"] == "mock"
        # Acceptance §5: inference settings are pinned and RECORDED per run.
        assert "inference_settings" in payload
        assert payload["corpus"]["scenarios"] == len(corpus)
        assert payload["corpus"]["field_term_scenarios"] >= 3

    def test_human_summary_names_the_key_figures(self, corpus, tmp_path):
        session = build_offline_session(corpus, audit_dir=tmp_path)
        report = run_measurement(corpus, session, _quick_config())
        summary = format_summary(report)
        assert "pooled" in summary
        assert "median" in summary
        assert "p95" in summary
        assert "retry" in summary


def _write_gemini_config(tmp_path):
    """A measurement-scoped provider TOML: shipped config with active=gemini."""
    from pathlib import Path

    shipped = Path("config/provider.toml").read_text(encoding="utf-8")
    flipped = shipped.replace('active = "anthropic"', 'active = "gemini"')
    path = tmp_path / "provider-gemini.toml"
    path.write_text(flipped, encoding="utf-8")
    return path


def _rate_limit_error():
    from server.llm.errors import ProviderError

    return ProviderError(
        kind="rate_limit", provider="gemini", retryable=True, raw_detail="429 quota"
    )


class _FlakyProvider:
    """Scripted inner provider: raises the given errors first, then succeeds."""

    name = "gemini"
    model_id = "gemini-3.5-flash"
    supports_prompt_caching = True

    def __init__(self, errors, turn):
        self._errors = list(errors)
        self._turn = turn
        self.calls = 0

    def complete(self, *, system_prefix, conversation, tools=()):
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return self._turn


def _final_turn(usage=None):
    from server.llm.types import ModelTurn, Usage

    return ModelTurn(
        text="완료했습니다.",
        tool_calls=(),
        stop_reason="end",
        usage=usage or Usage(),
        provider="gemini",
    )


class TestBackoffProvider:
    def test_rate_limit_retries_with_bounded_exponential_backoff(self):
        from server.measurement.runner import TelemetryBackoffProvider

        inner = _FlakyProvider([_rate_limit_error(), _rate_limit_error()], _final_turn())
        delays: list[float] = []
        provider = TelemetryBackoffProvider(
            inner, max_attempts=5, base_delay_seconds=10.0, sleep=delays.append
        )
        turn = provider.complete(system_prefix="P", conversation=[], tools=())
        assert turn.text == "완료했습니다."
        assert delays == [10.0, 20.0]  # exponential, bounded
        assert provider.backoff_retries == {"rate_limit": 2}

    def test_exhaustion_reraises_after_max_attempts(self):
        from server.llm.errors import ProviderError
        from server.measurement.runner import TelemetryBackoffProvider

        inner = _FlakyProvider([_rate_limit_error()] * 10, _final_turn())
        delays: list[float] = []
        provider = TelemetryBackoffProvider(
            inner, max_attempts=3, base_delay_seconds=1.0, sleep=delays.append
        )
        with pytest.raises(ProviderError):
            provider.complete(system_prefix="P", conversation=[], tools=())
        assert inner.calls == 3  # bounded — never a 4th attempt
        assert len(delays) == 2

    def test_non_retryable_error_propagates_immediately(self):
        from server.llm.errors import ProviderError
        from server.measurement.runner import TelemetryBackoffProvider

        auth = ProviderError(kind="auth", provider="gemini", retryable=False, raw_detail="401")
        inner = _FlakyProvider([auth], _final_turn())
        delays: list[float] = []
        provider = TelemetryBackoffProvider(
            inner, max_attempts=5, base_delay_seconds=1.0, sleep=delays.append
        )
        with pytest.raises(ProviderError):
            provider.complete(system_prefix="P", conversation=[], tools=())
        assert delays == []
        assert inner.calls == 1

    def test_usage_totals_accumulate_across_turns(self):
        from server.llm.types import Usage
        from server.measurement.runner import TelemetryBackoffProvider

        inner = _FlakyProvider(
            [], _final_turn(Usage(input_tokens=100, output_tokens=7, cache_read_tokens=90))
        )
        provider = TelemetryBackoffProvider(inner, sleep=lambda _: None)
        provider.complete(system_prefix="P", conversation=[], tools=())
        provider.complete(system_prefix="P", conversation=[], tools=())
        assert provider.model_calls == 2
        assert provider.usage_totals["input_tokens"] == 200
        assert provider.usage_totals["cache_read_tokens"] == 180


class TestLiveLlmSession:
    def test_live_llm_session_uses_mock_console_and_records_settings(self, corpus, tmp_path):
        # live-llm mode: REAL provider + OFFLINE console. Wired here with the
        # deterministic mock provider injected, so the composition is testable
        # without credentials; the actual Gemini run swaps only the provider.
        from server.measurement.mock_provider import MockScenarioProvider
        from server.measurement.runner import build_live_llm_session

        session = build_live_llm_session(
            config_path=_write_gemini_config(tmp_path),
            audit_dir=tmp_path / "audit",
            provider_override=MockScenarioProvider(corpus),
        )
        assert session.mode == "live-llm-mock-console"
        # Acceptance §5: the pinned inference settings snapshot comes from the
        # measurement config (active=gemini) — model pin included.
        assert session.inference_settings["model"] == "gemini-3.5-flash"
        report = run_measurement(corpus, session, _quick_config())
        assert report["mode"] == "live-llm-mock-console"
        assert report["grammar_error_rate"]["pooled_pass"] is True
        # Telemetry rides the report: model calls + usage + backoff retries.
        telemetry = report["provider_telemetry"]
        assert telemetry["model_calls"] > 0
        assert telemetry["backoff_retries"] == {}
        assert "wall_clock_seconds" in report


class TestProviderErrorContainment:
    def test_provider_error_is_recorded_and_the_run_continues(self, corpus, tmp_path):
        # A live run must survive one instruction's provider failure: the turn
        # is recorded by error kind and the remaining corpus still runs.
        from server.llm.errors import ProviderError
        from server.measurement.mock_provider import MockScenarioProvider
        from server.measurement.runner import build_live_llm_session

        target = corpus[0].instruction

        class OneAuthFailureProvider(MockScenarioProvider):
            def complete(self, *, system_prefix, conversation, tools=()):
                from server.llm.types import UserMessage

                instruction = next(
                    item.text for item in conversation if isinstance(item, UserMessage)
                )
                if instruction == target:
                    raise ProviderError(
                        kind="auth", provider="gemini", retryable=False, raw_detail="401"
                    )
                return super().complete(
                    system_prefix=system_prefix, conversation=conversation, tools=tools
                )

        session = build_live_llm_session(
            config_path=_write_gemini_config(tmp_path),
            audit_dir=tmp_path / "audit",
            provider_override=OneAuthFailureProvider(corpus),
        )
        report = run_measurement(corpus, session, _quick_config())
        assert report["turn_statuses"]["provider_error:auth"] == 1
        assert report["turn_statuses"]["ok"] == len(corpus) - 1


class TestNonProviderErrorContainment:
    def test_unexpected_exception_from_one_instruction_does_not_crash_the_run(
        self, corpus, tmp_path, monkeypatch
    ):
        # Live-run containment (module docstring) promises the run continues
        # past one instruction's failure — but the original code only caught
        # ProviderError. Any OTHER exception (a bug, an unwrapped SDK error)
        # must also be contained, not crash the whole run_measurement call.
        session = build_offline_session(corpus, audit_dir=tmp_path)
        target = corpus[0].instruction
        original = session.orchestrator.handle_instruction

        def flaky(instruction: str):
            if instruction == target:
                raise RuntimeError("boom - not a ProviderError")
            return original(instruction)

        monkeypatch.setattr(session.orchestrator, "handle_instruction", flaky)
        report = run_measurement(corpus, session, _quick_config())
        assert report["turn_statuses"]["unexpected_error:RuntimeError"] == 1
        assert report["turn_statuses"]["ok"] == len(corpus) - 1


class TestRepetitionsValidation:
    def test_repetitions_zero_raises_a_clear_value_error(self, corpus, tmp_path):
        # RunnerConfig.repetitions=0 previously crashed with IndexError deep
        # in the escalation while-loop (per_run[-1] on an empty list). It must
        # instead fail fast with a clear, actionable error before any round runs.
        session = build_offline_session(corpus, audit_dir=tmp_path)
        config = RunnerConfig(repetitions=0, warmup=False)
        with pytest.raises(ValueError, match="repetitions"):
            run_measurement(corpus, session, config)

    def test_default_repetitions_is_unaffected_by_the_new_check(self, corpus, tmp_path):
        # Regression guard: the repetitions=3 default must stay byte-identical.
        session = build_offline_session(corpus, audit_dir=tmp_path)
        report = run_measurement(corpus, session, _quick_config(repetitions=3))
        assert report["repetitions"]["configured"] == 3
        assert report["repetitions"]["executed"] >= 3


class TestCli:
    def test_cli_mock_mode_writes_report_file(self, tmp_path, monkeypatch):
        from server.measurement.runner import main

        out = tmp_path / "report.json"
        exit_code = main(
            [
                "--mode",
                "mock",
                "--output",
                str(out),
                "--repetitions",
                "1",
                "--min-command-lines",
                "1",
                "--no-warmup",
                "--audit-dir",
                str(tmp_path / "audit"),
            ]
        )
        assert exit_code == 0
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["mode"] == "mock"
        assert payload["grammar_error_rate"]["pooled_pass"] is True

    def test_cli_scenario_limit_bounds_the_smoke_run(self, tmp_path):
        # The live smoke uses --scenario-limit for a minimal quota footprint.
        from server.measurement.runner import main

        out = tmp_path / "report.json"
        exit_code = main(
            [
                "--mode",
                "mock",
                "--scenario-limit",
                "2",
                "--output",
                str(out),
                "--repetitions",
                "1",
                "--min-command-lines",
                "1",
                "--no-warmup",
                "--audit-dir",
                str(tmp_path / "audit"),
            ]
        )
        assert exit_code == 0
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["corpus"]["scenarios"] == 2
