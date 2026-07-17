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
