"""Reproduction tests for the T-G live-E2E defect (SPEC-COPILOT-PRESHOW-001).

Live onPC 2.4.2 E2E (2026-08-02) found that the OSC-family checks
(``osc_roundtrip`` / ``receive_port_binding`` / ``stale_socket_advisory`` /
``feedback_port_drift``) never actually execute through the ``preshow_check``
model tool — ``build_toolset``'s handler never passes anything an OSC check
could use, so all four always report ``skip`` regardless of console state.

This file captures the DESIRED post-fix behavior: an already-open console
link (a liveness port) can be injected into ``build_toolset`` so the tool
actually exercises those checks without opening a second socket on the
receive port the app itself already holds.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset

from .test_tools import FakeStatePort, ScriptedPort


class _FakeLiveness:
    """Structural stand-in for an already-open console link's liveness probe."""

    def __init__(self, *, ok: bool):
        self._ok = ok
        self.calls = 0

    def ping(self) -> bool:
        self.calls += 1
        return self._ok


def _call_preshow_check(registry):
    execution = registry.dispatch(ToolCall(id="p1", name="preshow_check", arguments={}))
    return json.loads(execution.result.content)


class TestPreshowCheckOscWiring:
    def test_osc_checks_are_skip_only_without_injection(self):
        # Documents today's default (no liveness injected): unchanged by the
        # fix, this remains the correct "nothing to check against" outcome.
        registry = build_toolset(execution_port=ScriptedPort(), state_port=FakeStatePort({}))
        report = _call_preshow_check(registry)
        by_name = {c["name"]: c for c in report["checks"]}
        assert by_name["osc_roundtrip"]["status"] == "skip"
        assert by_name["receive_port_binding"]["status"] == "skip"

    def test_osc_checks_actually_run_when_a_liveness_port_is_injected(self):
        # RED before the fix: build_toolset accepts no such wiring today, so
        # the OSC checks stay skip even though a responding liveness port was
        # supplied — this assertion fails until preshow_liveness_port is wired
        # through to run_preshow_checklist.
        liveness = _FakeLiveness(ok=True)
        registry = build_toolset(
            execution_port=ScriptedPort(),
            state_port=FakeStatePort({}),
            preshow_liveness_port=liveness,
            preshow_receive_port=9005,
        )
        report = _call_preshow_check(registry)
        by_name = {c["name"]: c for c in report["checks"]}
        assert by_name["osc_roundtrip"]["status"] == "pass"
        assert by_name["receive_port_binding"]["status"] == "pass"
        assert liveness.calls >= 1

    def test_no_response_liveness_yields_skip_not_a_bind_failure(self):
        # RED before the fix: a non-responding liveness port must degrade to
        # skip (stale-socket territory), never attempt a real bind — that
        # would always "fail" for a port the app itself already holds.
        liveness = _FakeLiveness(ok=False)
        registry = build_toolset(
            execution_port=ScriptedPort(),
            state_port=FakeStatePort({}),
            preshow_liveness_port=liveness,
            preshow_receive_port=9005,
        )
        report = _call_preshow_check(registry)
        by_name = {c["name"]: c for c in report["checks"]}
        assert by_name["osc_roundtrip"]["status"] == "skip"
        assert by_name["receive_port_binding"]["status"] == "skip"


class TestPreshowCheckOscSlotWiring:
    """T-G3 — the configured osc_slot must reach preshow_check, not the
    hardcoded runner.py default (which sent operators to the wrong row)."""

    def test_configured_osc_slot_is_named_in_the_guidance(self):
        # RED before the fix: build_toolset accepts no preshow_osc_slot today,
        # so the guidance always names DEFAULT_OSC_SLOT (1) regardless of the
        # site's real setting.
        registry = build_toolset(
            execution_port=ScriptedPort(), state_port=FakeStatePort({}), preshow_osc_slot=2
        )
        report = _call_preshow_check(registry)
        by_name = {c["name"]: c for c in report["checks"]}
        assert "osc_slot=2" in by_name["osc_slot_send_row"]["detail"]
        assert "확인할 수 없어" not in by_name["osc_slot_send_row"]["detail"]

    def test_unwired_default_discloses_it_is_unconfirmed(self):
        registry = build_toolset(execution_port=ScriptedPort(), state_port=FakeStatePort({}))
        report = _call_preshow_check(registry)
        by_name = {c["name"]: c for c in report["checks"]}
        assert "확인할 수 없어" in by_name["osc_slot_send_row"]["detail"]
