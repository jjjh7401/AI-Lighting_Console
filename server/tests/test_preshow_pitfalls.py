"""Known-pitfall diagnostic tests (SPEC-COPILOT-PRESHOW-001).

Covers the three field-observed failure modes: stale OSC socket, an
``osc_slot`` row that is not Send=Yes, and feedback/response port drift.
"""

from __future__ import annotations

from server.preshow.models import CheckResult
from server.preshow.pitfalls import (
    check_feedback_port_drift,
    check_osc_slot_send_row,
    check_stale_socket_advisory,
)


class TestCheckStaleSocketAdvisory:
    def test_pass_when_roundtrip_passed(self):
        roundtrip = CheckResult(name="osc_roundtrip", status="pass", detail="ok")
        result = check_stale_socket_advisory(roundtrip)
        assert result.status == "pass"

    def test_skip_with_advice_when_roundtrip_skipped(self):
        roundtrip = CheckResult(name="osc_roundtrip", status="skip", detail="timeout")
        result = check_stale_socket_advisory(roundtrip)
        assert result.status == "skip"
        assert "Enable Input/Output" in result.detail

    def test_skip_with_advice_when_roundtrip_failed(self):
        roundtrip = CheckResult(name="osc_roundtrip", status="fail", detail="bad decode")
        result = check_stale_socket_advisory(roundtrip)
        assert result.status == "skip"
        assert result.data == {"osc_roundtrip_status": "fail"}


class TestCheckOscSlotSendRow:
    def test_skip_when_no_live_rows_given(self):
        result = check_osc_slot_send_row(2, None)
        assert result.status == "skip"
        assert result.data == {"configured_slot": 2}

    def test_pass_when_row_is_send_yes(self):
        result = check_osc_slot_send_row(2, {2: {"send": True}})
        assert result.status == "pass"

    def test_fail_when_row_is_not_send_yes(self):
        result = check_osc_slot_send_row(2, {2: {"send": False}})
        assert result.status == "fail"
        assert "Send=Yes가 아니다" in result.detail

    def test_fail_when_row_missing_entirely(self):
        result = check_osc_slot_send_row(2, {1: {"send": True}})
        assert result.status == "fail"
        assert "찾지 못했다" in result.detail


class TestCheckOscSlotSendRowConfiguredDisclosure:
    """T-G3 — a wrong slot number in the guidance is worse than no guidance.

    ``slot_is_configured`` (default True, unchanged wording/behavior) marks
    whether ``configured_slot`` was actually resolved from the site's real
    settings, or is only a fallback default because the setting could not be
    read. The two must never read the same to an operator.
    """

    def test_default_is_configured_true_and_names_the_value_plainly(self):
        result = check_osc_slot_send_row(2, None)
        assert "osc_slot=2" in result.detail
        assert "확인할 수 없어" not in result.detail

    def test_unconfigured_fallback_discloses_it_is_a_default_not_a_confirmed_value(self):
        result = check_osc_slot_send_row(1, None, slot_is_configured=False)
        assert result.status == "skip"
        assert "확인할 수 없어" in result.detail
        assert "기본값" in result.detail
        assert "osc_slot=1" in result.detail

    def test_unconfigured_fallback_marks_data_too(self):
        result = check_osc_slot_send_row(1, None, slot_is_configured=False)
        assert result.data == {"configured_slot": 1, "slot_is_configured": False}


class TestCheckFeedbackPortDrift:
    def test_skip_when_nothing_observed(self):
        result = check_feedback_port_drift(9000, None)
        assert result.status == "skip"

    def test_pass_when_ports_match(self):
        result = check_feedback_port_drift(9000, 9000)
        assert result.status == "pass"

    def test_fail_when_ports_diverge(self):
        # The field incident this check targets: a console-side reply port
        # (e.g. 9005) drifting away from the configured value.
        result = check_feedback_port_drift(9000, 9005)
        assert result.status == "fail"
        assert result.data == {"configured_port": 9000, "observed_port": 9005}
