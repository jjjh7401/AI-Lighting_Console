"""Checklist-runner integration tests (SPEC-COPILOT-PRESHOW-001)."""

from __future__ import annotations

from server.looks.loader import LookSchemaError
from server.preshow.runner import run_preshow_checklist


class FakeStatePort:
    def __init__(self, responses: dict[str, dict]):
        self._responses = responses

    def query_state(self, path: str) -> dict:
        return self._responses[path]


class TestRunPreshowChecklistNoConsole:
    """The console-optional path: no osc_config, no state_port."""

    def test_yellow_when_console_inputs_are_absent(self):
        report = run_preshow_checklist()
        assert report.signal == "yellow"
        names = {check.name for check in report.checks}
        assert {
            "osc_roundtrip",
            "receive_port_binding",
            "sequences_exist",
            "preset_pools_exist",
            "preset_library_integrity",
            "stale_socket_advisory",
            "osc_slot_send_row",
            "feedback_port_drift",
        } <= names

    def test_console_dependent_checks_all_skip(self):
        report = run_preshow_checklist()
        by_name = {check.name: check for check in report.checks}
        assert by_name["osc_roundtrip"].status == "skip"
        assert by_name["sequences_exist"].status == "skip"
        assert by_name["preset_pools_exist"].status == "skip"
        assert by_name["feedback_port_drift"].status == "skip"

    def test_local_only_checks_still_run(self):
        # preset_library_integrity needs no console — it must actually run
        # (pass, against the real on-disk library) even with nothing wired.
        report = run_preshow_checklist()
        by_name = {check.name: check for check in report.checks}
        assert by_name["preset_library_integrity"].status == "pass"


class TestRunPreshowChecklistWithStatePort:
    def test_green_when_state_port_and_library_are_healthy(self):
        state_port = FakeStatePort(
            {
                "DataPool/Sequences": {"node": {"childCount": 2}},
                "DataPool/PresetPools": {"node": {"childCount": 1}},
            }
        )
        report = run_preshow_checklist(state_port=state_port)
        by_name = {check.name: check for check in report.checks}
        assert by_name["sequences_exist"].status == "pass"
        assert by_name["preset_pools_exist"].status == "pass"
        # osc_config was still not given, so the OSC-dependent checks skip —
        # the overall signal stays yellow, not green, until every check ran.
        assert report.signal == "yellow"

    def test_red_when_a_state_check_fails(self):
        state_port = FakeStatePort(
            {
                "DataPool/Sequences": {"node": {"childCount": 0}},
                "DataPool/PresetPools": {"node": {"childCount": 1}},
            }
        )
        report = run_preshow_checklist(state_port=state_port)
        assert report.signal == "red"


class TestRunPreshowChecklistPitfallWiring:
    def test_osc_slot_send_row_uses_configured_slot(self):
        report = run_preshow_checklist(
            configured_osc_slot=2, live_osc_rows={2: {"send": True}}
        )
        by_name = {check.name: check for check in report.checks}
        assert by_name["osc_slot_send_row"].status == "pass"
        assert by_name["osc_slot_send_row"].data["configured_slot"] == 2

    def test_feedback_port_drift_falls_back_to_a_configured_feedback_port(self):
        report = run_preshow_checklist(configured_feedback_port=9005)
        by_name = {check.name: check for check in report.checks}
        # No live observation exists (no osc_config -> no bound port), so this
        # still reports skip even though a configured port was supplied —
        # never a silent pass with nothing observed.
        assert by_name["feedback_port_drift"].status == "skip"

    def test_broken_local_library_turns_the_whole_run_red(self):
        def _broken_loader():
            raise LookSchemaError("duplicate look id")

        report = run_preshow_checklist(library_loader=_broken_loader)
        assert report.signal == "red"
