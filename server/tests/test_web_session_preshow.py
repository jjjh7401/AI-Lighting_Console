"""Production-wiring regression tests (SPEC-COPILOT-PRESHOW-001 T-G2).

T-G added the LivenessPort seam (``server/preshow/osc_check.py``) and threaded
``preshow_liveness_port`` / ``preshow_receive_port`` through
``build_toolset``/``preshow_check`` — but ``ChatSession`` (the ONLY production
assembly point that calls ``build_toolset``, ``server/web/session.py``) never
passed either, so a live E2E against the running app still saw the OSC-family
checks report ``skip`` regardless of console state. Unit tests on
``build_toolset`` in isolation cannot catch this — the defect lives entirely
in the assembly wiring, the same class of gap the project's own field notes
call out (a router mounted correctly in isolation, never wired into the real
app). These tests exercise the ACTUAL ``ChatSession`` construction path.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall

from .test_runner_self_correction import ScriptedProvider
from .test_web_session import FakeConsole, _session


def _preshow_report(session) -> dict:
    execution = session._registry.dispatch(ToolCall(id="p1", name="preshow_check", arguments={}))
    return json.loads(execution.result.content)


class TestSessionWiresPreshowLiveness:
    """(a) ChatSession actually passes a liveness port through to build_toolset."""

    def test_osc_checks_run_instead_of_skip_when_the_gate_is_alive(self, tmp_path):
        console = FakeConsole()
        console.ping_ok = True
        session, _, _, _, _ = _session(
            tmp_path, ScriptedProvider([]), console=console, preshow_receive_port=9005
        )
        report = _preshow_report(session)
        by_name = {c["name"]: c for c in report["checks"]}
        assert by_name["osc_roundtrip"]["status"] == "pass"
        assert by_name["receive_port_binding"]["status"] == "pass"

    def test_no_wiring_without_a_receive_port_leaves_the_default_skip(self, tmp_path):
        # Sanity control: omitting preshow_receive_port (as every existing
        # caller does today) must stay byte-identical to pre-T-G2 behavior.
        console = FakeConsole()
        console.ping_ok = True
        session, _, _, _, _ = _session(tmp_path, ScriptedProvider([]), console=console)
        report = _preshow_report(session)
        by_name = {c["name"]: c for c in report["checks"]}
        assert by_name["osc_roundtrip"]["status"] == "skip"
        assert by_name["receive_port_binding"]["status"] == "skip"


class TestSessionLivenessPortReflectsGateState:
    """(b) the wired liveness port's ping() actually tracks the gate's liveness."""

    def test_a_dead_console_reports_skip_not_a_stale_pass(self, tmp_path):
        console = FakeConsole()
        console.ping_ok = False
        session, _, _, _, _ = _session(
            tmp_path, ScriptedProvider([]), console=console, preshow_receive_port=9005
        )
        report = _preshow_report(session)
        by_name = {c["name"]: c for c in report["checks"]}
        assert by_name["osc_roundtrip"]["status"] == "skip"
        assert by_name["receive_port_binding"]["status"] == "skip"

    def test_liveness_reflects_the_gates_most_recent_heartbeat_not_a_frozen_snapshot(
        self, tmp_path
    ):
        console = FakeConsole()
        console.ping_ok = True
        session, _, _, _, _ = _session(
            tmp_path, ScriptedProvider([]), console=console, preshow_receive_port=9005
        )
        assert _preshow_report(session)["checks"] and (
            {c["name"]: c for c in _preshow_report(session)["checks"]}["osc_roundtrip"]["status"]
            == "pass"
        )
        console.ping_ok = False
        by_name = {c["name"]: c for c in _preshow_report(session)["checks"]}
        assert by_name["osc_roundtrip"]["status"] == "skip"


class TestSessionWiresPreshowOscSlot:
    """T-G3 (c) — ChatSession forwards the site's real osc_slot setting.

    Live onPC E2E: this site's real osc_slot is 2, but runner.py's hardcoded
    DEFAULT_OSC_SLOT is 1 — an unwired ChatSession sent the operator to check
    the wrong console row, past the actual culprit row twice before.
    """

    def test_configured_osc_slot_reaches_the_guidance_text(self, tmp_path):
        session, _, _, _, _ = _session(tmp_path, ScriptedProvider([]), preshow_osc_slot=2)
        report = _preshow_report(session)
        by_name = {c["name"]: c for c in report["checks"]}
        assert "osc_slot=2" in by_name["osc_slot_send_row"]["detail"]
        assert "확인할 수 없어" not in by_name["osc_slot_send_row"]["detail"]

    def test_unwired_session_discloses_the_default_is_unconfirmed(self, tmp_path):
        session, _, _, _, _ = _session(tmp_path, ScriptedProvider([]))
        report = _preshow_report(session)
        by_name = {c["name"]: c for c in report["checks"]}
        assert "확인할 수 없어" in by_name["osc_slot_send_row"]["detail"]
