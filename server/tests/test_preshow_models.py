"""Result/report model tests for the pre-show checklist (SPEC-COPILOT-PRESHOW-001)."""

from __future__ import annotations

import pytest

from server.preshow.models import CheckResult, PreshowReport


class TestCheckResult:
    def test_accepts_every_closed_status(self):
        for status in ("pass", "fail", "skip"):
            CheckResult(name="x", status=status, detail="d")

    def test_rejects_unknown_status(self):
        with pytest.raises(ValueError):
            CheckResult(name="x", status="warn", detail="d")

    def test_to_dict_shape(self):
        result = CheckResult(name="x", status="pass", detail="d", data={"a": 1})
        assert result.to_dict() == {"name": "x", "status": "pass", "detail": "d", "data": {"a": 1}}


def _result(name: str, status: str) -> CheckResult:
    return CheckResult(name=name, status=status, detail=f"{name} {status}")


class TestPreshowReport:
    def test_all_pass_is_green(self):
        report = PreshowReport(checks=(_result("a", "pass"), _result("b", "pass")))
        assert report.signal == "green"

    def test_any_skip_without_fail_is_yellow(self):
        report = PreshowReport(checks=(_result("a", "pass"), _result("b", "skip")))
        assert report.signal == "yellow"

    def test_any_fail_is_red_even_with_skips(self):
        report = PreshowReport(
            checks=(_result("a", "fail"), _result("b", "skip"), _result("c", "pass"))
        )
        assert report.signal == "red"

    def test_signal_is_derived_not_stored_independently(self):
        # Two reports built from the same statuses in different orders agree —
        # the signal cannot be poked into disagreement with its own rows.
        first = PreshowReport(checks=(_result("a", "skip"), _result("b", "pass")))
        second = PreshowReport(checks=(_result("b", "pass"), _result("a", "skip")))
        assert first.signal == second.signal == "yellow"

    def test_counts_match_the_rows(self):
        report = PreshowReport(
            checks=(_result("a", "pass"), _result("b", "pass"), _result("c", "fail"))
        )
        counts = report.counts()
        assert counts["pass"] == 2
        assert counts["fail"] == 1
        assert counts["skip"] == 0

    def test_to_dict_carries_signal_summary_and_every_check(self):
        report = PreshowReport(checks=(_result("a", "pass"),))
        payload = report.to_dict()
        assert payload["signal"] == "green"
        assert "summary" in payload
        assert payload["checks"] == [
            {"name": "a", "status": "pass", "detail": "a pass", "data": None}
        ]
