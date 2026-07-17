"""Fallback provider config-switch tests (AC-MVP-027 part 3, REQ-MVP-040 ii).

Closes the acceptance gap: previously ``FallbackDetector`` only DECIDED and
audit-logged a persistent-miss fallback event — nothing actually switched the
running orchestrator to a different provider. ``SwitchableProvider`` (runner.py)
is the runtime indirection an ``Orchestrator`` holds as its ``provider``; a
``FallbackDetector``'s ``on_fallback`` callback (fallback.py) is wired to its
``switch_to`` method so a persistent-miss decision actually changes which
adapter subsequent turns run against — not merely a config value a human must
apply by restarting the process.

``target_provider`` remains unset in the shipped ``config/provider.toml`` —
selecting a real production fallback target is a separate, still-pending
human decision (M6b-3, needs Anthropic-side error-rate measurement data).
"""

from __future__ import annotations

from server.llm.config import FallbackSettings
from server.llm.types import ModelTurn, Usage
from server.orchestrator.fallback import FallbackDetector
from server.orchestrator.runner import Orchestrator, SwitchableProvider
from server.orchestrator.tools import build_toolset

from .test_tools import FakeStatePort, ScriptedPort

_PREFIX = "PREFIX"


class NamedProvider:
    """Deterministic single-turn LLMProvider identified by name (swap-crux test)."""

    def __init__(self, name: str, model_id: str):
        self.name = name
        self.model_id = model_id
        self.supports_prompt_caching = False
        self.calls = 0

    def complete(self, *, system_prefix, conversation, tools=()):
        self.calls += 1
        return ModelTurn(
            text="done", tool_calls=(), stop_reason="end", usage=Usage(), provider=self.name
        )


class RecordingSink:
    def __init__(self):
        self.events: list[dict] = []

    def record(self, event: dict) -> None:
        self.events.append(event)


def _orchestrator(provider, *, fallback_detector=None, clock=None):
    registry = build_toolset(execution_port=ScriptedPort(), state_port=FakeStatePort({}))
    kwargs = {}
    if clock is not None:
        kwargs["clock"] = clock
    return Orchestrator(
        provider=provider,
        registry=registry,
        system_prefix=_PREFIX,
        fallback_detector=fallback_detector,
        **kwargs,
    )


class TestSwitchableProvider:
    def test_delegates_to_the_active_adapter(self):
        anthropic = NamedProvider("anthropic", "claude-opus-4-8")
        gemini = NamedProvider("gemini", "gemini-3.5-flash")
        switchable = SwitchableProvider(
            {"anthropic": anthropic, "gemini": gemini}, active_name="anthropic"
        )
        assert switchable.name == "anthropic"
        assert switchable.model_id == "claude-opus-4-8"
        switchable.switch_to("gemini")
        assert switchable.name == "gemini"
        assert switchable.model_id == "gemini-3.5-flash"

    def test_switch_to_an_unknown_name_is_a_no_op(self):
        anthropic = NamedProvider("anthropic", "claude-opus-4-8")
        switchable = SwitchableProvider({"anthropic": anthropic}, active_name="anthropic")
        switchable.switch_to("nonexistent")
        assert switchable.name == "anthropic"

    def test_rejects_an_active_name_absent_from_the_registry(self):
        import pytest

        with pytest.raises(KeyError):
            SwitchableProvider({"anthropic": NamedProvider("anthropic", "m")}, active_name="gemini")


class TestFallbackActuallySwitchesTheProvider:
    """AC-MVP-027 part 3 — the crux: two judged turns, fallback between them,
    the SECOND turn's provider identity differs from the first."""

    def test_target_provider_configured_switches_the_next_judged_turn(self):
        anthropic = NamedProvider("anthropic", "claude-opus-4-8")
        gemini = NamedProvider("gemini", "gemini-3.5-flash")
        switchable = SwitchableProvider(
            {"anthropic": anthropic, "gemini": gemini}, active_name="anthropic"
        )
        settings = FallbackSettings(
            window_turns=1,
            consecutive_windows=1,
            threshold_seconds=1.0,
            target_provider="gemini",
        )
        sink = RecordingSink()
        detector = FallbackDetector(
            settings, audit_sink=sink, active_provider="anthropic", on_fallback=switchable.switch_to
        )
        # turn 1: 0.0 -> 5.0 (5s > 1s threshold, window fills at 1 turn -> triggers)
        # turn 2: 5.0 -> 5.1
        clock_values = iter([0.0, 5.0, 5.0, 5.1])
        orchestrator = _orchestrator(
            switchable, fallback_detector=detector, clock=lambda: next(clock_values)
        )

        orchestrator.handle_instruction("첫 번째 지시")
        assert switchable.name == "gemini"  # fallback fired — switched already
        assert anthropic.calls == 1
        assert gemini.calls == 0

        orchestrator.handle_instruction("두 번째 지시")
        assert gemini.calls == 1  # the SECOND turn actually ran against gemini
        assert anthropic.calls == 1  # anthropic was not called again

        event = sink.events[0]
        assert event["switched"] is True
        assert event["target_provider"] == "gemini"

    def test_without_target_provider_the_active_provider_never_changes(self):
        # Today's default shape (shipped config/provider.toml): decision-only.
        anthropic = NamedProvider("anthropic", "claude-opus-4-8")
        settings = FallbackSettings(window_turns=1, consecutive_windows=1, threshold_seconds=1.0)
        sink = RecordingSink()
        detector = FallbackDetector(settings, audit_sink=sink, active_provider="anthropic")
        clock_values = iter([0.0, 5.0, 5.0, 5.1])
        orchestrator = _orchestrator(
            anthropic, fallback_detector=detector, clock=lambda: next(clock_values)
        )

        orchestrator.handle_instruction("첫 번째 지시")
        orchestrator.handle_instruction("두 번째 지시")
        assert anthropic.calls == 2  # same provider handled both turns

        event = sink.events[0]
        assert event["switched"] is False
        assert event["target_provider"] is None
