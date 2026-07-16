"""Orchestrator self-correction loop tests (M3 — AC-MVP-005, REQ-MVP-009/010/033 seed).

The loop feeds console errors back to the model and retries with corrected
commands, capped at 3 retries per instruction (hard cap — REQ-MVP-010). It
NEVER re-executes a command that already executed successfully within the same
instruction (REQ-MVP-033 execution-time atomicity, M3 scope).

The provider is scripted (deterministic — no model, no network) and the
execution port is an in-memory fake, per AC-MVP-005's deterministic test shape.
"""

from __future__ import annotations

import json

from server.llm.types import ModelTurn, ToolCall, ToolResultsMessage, Usage
from server.orchestrator.runner import Orchestrator
from server.orchestrator.tools import build_toolset

from .test_tools import FakeStatePort, ScriptedPort

_PREFIX = "PREFIX"


def _run_turn(commands: list[str], call_id: str) -> ModelTurn:
    return ModelTurn(
        text="",
        tool_calls=(ToolCall(id=call_id, name="run_commands", arguments={"commands": commands}),),
        stop_reason="tool_use",
        usage=Usage(),
        provider="scripted",
    )


def _final(text: str = "완료했습니다") -> ModelTurn:
    return ModelTurn(
        text=text, tool_calls=(), stop_reason="end", usage=Usage(), provider="scripted"
    )


class ScriptedProvider:
    """Deterministic LLMProvider — returns pre-scripted turns in order."""

    name = "scripted"
    model_id = "scripted-model"
    supports_prompt_caching = False

    def __init__(self, turns):
        self.turns = list(turns)
        self.calls: list[list] = []  # conversation snapshot per complete() call

    def complete(self, *, system_prefix, conversation, tools=()):
        self.calls.append(list(conversation))
        return self.turns.pop(0)


class AlwaysFailingCommandProvider(ScriptedProvider):
    """Always answers with the same failing command bundle (AC-MVP-005 shape)."""

    def __init__(self, command: str = "Bad Command"):
        super().__init__([])
        self.command = command

    def complete(self, *, system_prefix, conversation, tools=()):
        self.calls.append(list(conversation))
        return _run_turn([self.command], call_id=f"call-{len(self.calls)}")


class RecordingDetector:
    def __init__(self):
        self.observed: list[float] = []

    def observe_turn(self, duration_seconds: float) -> bool:
        self.observed.append(duration_seconds)
        return False


class RecordingMetricsSink:
    def __init__(self):
        self.turns = []

    def record_turn(self, metrics) -> None:
        self.turns.append(metrics)


def _orchestrator(provider, port=None, **kwargs):
    registry = build_toolset(execution_port=port or ScriptedPort(), state_port=FakeStatePort({}))
    return Orchestrator(provider=provider, registry=registry, system_prefix=_PREFIX, **kwargs)


class TestCleanPath:
    def test_instruction_without_failures_uses_zero_retries(self):
        provider = ScriptedProvider([_run_turn(["Store Cue 5"], "c1"), _final()])
        port = ScriptedPort()
        result = _orchestrator(provider, port).handle_instruction("큐 5 저장해줘")
        assert result.status == "ok"
        assert result.retries_used == 0
        assert result.model_calls == 2
        assert result.text == "완료했습니다"
        assert port.executed == ["Store Cue 5"]

    def test_tool_results_are_bundled_into_one_message(self):
        two_calls = ModelTurn(
            text="",
            tool_calls=(
                ToolCall(id="c1", name="query_state", arguments={"path": "X"}),
                ToolCall(id="c2", name="run_commands", arguments={"commands": ["List"]}),
            ),
            stop_reason="tool_use",
            usage=Usage(),
            provider="scripted",
        )
        provider = ScriptedProvider([two_calls, _final()])
        _orchestrator(provider).handle_instruction("hi")
        follow_up = provider.calls[1]
        results_message = follow_up[-1]
        assert isinstance(results_message, ToolResultsMessage)
        assert len(results_message.results) == 2


class TestRetryCap:
    """AC-MVP-005 — always-failing command -> exactly 3 retries -> failure report."""

    def test_exactly_three_retries_then_failure_report(self):
        provider = AlwaysFailingCommandProvider()
        port = ScriptedPort(failures=frozenset({"Bad Command"}))
        result = _orchestrator(provider, port).handle_instruction("항상 실패하는 지시")
        assert result.status == "retries_exhausted"
        assert result.retries_used == 3
        assert result.model_calls == 4  # initial attempt + 3 correction rounds
        assert port.executed == ["Bad Command"] * 4
        # The failure report carries the per-command evidence for the user.
        assert any(o.status == "failed" for o in result.command_outcomes)

    def test_successful_retry_stops_the_retry_count(self):
        provider = ScriptedProvider(
            [
                _run_turn(["Bad"], "c1"),
                _run_turn(["Good"], "c2"),
                _final(),
            ]
        )
        port = ScriptedPort(failures=frozenset({"Bad"}))
        result = _orchestrator(provider, port).handle_instruction("do it")
        assert result.status == "ok"
        assert result.retries_used == 1


class TestExecutedCommandProtection:
    """REQ-MVP-033 (M3 scope) — retries touch only unexecuted/corrected commands."""

    def test_retry_bundle_never_reexecutes_prior_successes(self):
        provider = ScriptedProvider(
            [
                _run_turn(["A", "B", "C"], "c1"),
                _run_turn(["A", "B2", "C"], "c2"),  # model repeats A — must be skipped
                _final(),
            ]
        )
        port = ScriptedPort(failures=frozenset({"B"}))
        result = _orchestrator(provider, port).handle_instruction("3개 실행해줘")
        assert result.status == "ok"
        assert result.retries_used == 1
        assert port.executed == ["A", "B", "B2", "C"]  # A executed exactly once

    def test_error_feedback_reports_per_command_status_to_the_model(self):
        provider = ScriptedProvider(
            [_run_turn(["A", "B", "C"], "c1"), _run_turn(["B2", "C"], "c2"), _final()]
        )
        port = ScriptedPort(failures=frozenset({"B"}))
        _orchestrator(provider, port).handle_instruction("hi")
        feedback = provider.calls[1][-1]
        assert isinstance(feedback, ToolResultsMessage)
        payload = json.loads(feedback.results[0].content)
        statuses = [entry["status"] for entry in payload["commands"]]
        assert statuses == ["executed_ok", "failed", "not_executed"]
        assert feedback.results[0].is_error is True


class TestMeasurementSupport:
    """REQ-MVP-040 measurement support (M3) — metrics + judged-turn feed only."""

    def test_clean_turn_is_fed_to_the_fallback_detector_with_duration(self):
        provider = ScriptedProvider([_run_turn(["Ok"], "c1"), _final()])
        detector = RecordingDetector()
        ticks = iter([100.0, 107.5])
        orchestrator = _orchestrator(
            provider, fallback_detector=detector, clock=lambda: next(ticks)
        )
        result = orchestrator.handle_instruction("hi")
        assert detector.observed == [7.5]
        assert result.duration_seconds == 7.5

    def test_retry_turns_are_excluded_from_the_fallback_feed(self):
        # acceptance.md round-trip measurement rule 4: retry turns are excluded.
        provider = ScriptedProvider([_run_turn(["Bad"], "c1"), _run_turn(["Good"], "c2"), _final()])
        detector = RecordingDetector()
        orchestrator = _orchestrator(
            provider,
            port=ScriptedPort(failures=frozenset({"Bad"})),
            fallback_detector=detector,
        )
        orchestrator.handle_instruction("hi")
        assert detector.observed == []

    def test_metrics_sink_records_provider_model_and_counts(self):
        provider = ScriptedProvider([_run_turn(["A", "B"], "c1"), _final()])
        sink = RecordingMetricsSink()
        orchestrator = _orchestrator(
            provider, port=ScriptedPort(failures=frozenset({"B"})), metrics_sink=sink
        )
        # B fails; the scripted follow-up turn is a plain text answer (model
        # reports instead of retrying), so the instruction still completes.
        orchestrator.handle_instruction("hi")
        assert len(sink.turns) == 1
        metrics = sink.turns[0]
        assert metrics.provider == "scripted"
        assert metrics.model == "scripted-model"
        assert metrics.commands_generated == 2
        assert metrics.commands_failed == 1


class TestLoopGuard:
    def test_runaway_tool_loops_are_bounded(self):
        class EndlessToolProvider(ScriptedProvider):
            def complete(self, *, system_prefix, conversation, tools=()):
                self.calls.append(list(conversation))
                return ModelTurn(
                    text="",
                    tool_calls=(
                        ToolCall(
                            id=f"q-{len(self.calls)}",
                            name="query_state",
                            arguments={"path": "X"},
                        ),
                    ),
                    stop_reason="tool_use",
                    usage=Usage(),
                    provider="scripted",
                )

        provider = EndlessToolProvider([])
        result = _orchestrator(provider, max_model_calls=5).handle_instruction("hi")
        assert result.status == "loop_limit"
        assert result.model_calls == 5
