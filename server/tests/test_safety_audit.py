"""Audit log tests (M4 — REQ-MVP-018, plan.md §A-4: JSONL / daily rotation /
90-day retention / append-only). Deterministic via an injected datetime clock.

Also verifies the M3 fallback detector's injectable audit sink wired to the
REAL durable audit log (Section B: fallback events land in JSONL).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from server.llm.config import FallbackSettings
from server.orchestrator.fallback import FallbackDetector
from server.safety.audit import AuditLog


class FakeClock:
    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now = self.now + timedelta(**kwargs)


def _log(tmp_path, start=datetime(2026, 7, 16, 10, 0, tzinfo=UTC), **kwargs):
    clock = FakeClock(start)
    return AuditLog(tmp_path / "audit", clock=clock, **kwargs), clock


def _lines(directory):
    return {
        path.name: path.read_text(encoding="utf-8").splitlines()
        for path in sorted(directory.glob("audit-*.jsonl"))
    }


class TestJsonlAppendOnly:
    def test_record_appends_jsonl_lines_with_timestamp(self, tmp_path):
        log, _ = _log(tmp_path)
        log.record({"event": "executed", "command": "Store Cue 5"})
        log.record({"event": "blocked", "command": "Delete", "reason": "grammar"})
        files = _lines(tmp_path / "audit")
        assert list(files) == ["audit-20260716.jsonl"]
        events = [json.loads(line) for line in files["audit-20260716.jsonl"]]
        assert [e["event"] for e in events] == ["executed", "blocked"]
        assert all(e["ts"].startswith("2026-07-16") for e in events)

    def test_korean_payloads_survive_round_trip(self, tmp_path):
        log, _ = _log(tmp_path)
        log.record({"event": "rejected", "detail": "사용자가 거부함"})
        (event,) = [json.loads(line) for line in _lines(tmp_path / "audit").popitem()[1]]
        assert event["detail"] == "사용자가 거부함"

    def test_iter_events_returns_all_events_in_order(self, tmp_path):
        log, clock = _log(tmp_path)
        log.record({"event": "executed", "n": 1})
        clock.advance(days=1)
        log.record({"event": "approved", "n": 2})
        events = list(log.iter_events())
        assert [e["n"] for e in events] == [1, 2]


class TestRotationAndRetention:
    def test_daily_rotation_creates_one_file_per_day(self, tmp_path):
        log, clock = _log(tmp_path)
        log.record({"event": "executed"})
        clock.advance(days=1)
        log.record({"event": "executed"})
        assert list(_lines(tmp_path / "audit")) == [
            "audit-20260716.jsonl",
            "audit-20260717.jsonl",
        ]

    def test_files_older_than_retention_are_purged(self, tmp_path):
        log, clock = _log(tmp_path)
        log.record({"event": "executed"})
        clock.advance(days=91)
        log.record({"event": "executed"})
        assert list(_lines(tmp_path / "audit")) == ["audit-20261015.jsonl"]

    def test_files_within_retention_are_kept(self, tmp_path):
        log, clock = _log(tmp_path)
        log.record({"event": "executed"})
        clock.advance(days=89)
        log.record({"event": "executed"})
        assert len(_lines(tmp_path / "audit")) == 2

    def test_retention_days_is_configurable(self, tmp_path):
        log, clock = _log(tmp_path, retention_days=7)
        log.record({"event": "executed"})
        clock.advance(days=8)
        log.record({"event": "executed"})
        assert len(_lines(tmp_path / "audit")) == 1


class TestEventHelpers:
    def test_log_executed_records_command_kind_and_outcome(self, tmp_path):
        log, _ = _log(tmp_path)
        log.log_executed("Store Cue 5", ok=True, detail="OK")
        (event,) = list(log.iter_events())
        assert event["event"] == "executed"
        assert event["command"] == "Store Cue 5"
        assert event["kind"] == "command"
        assert event["ok"] is True

    def test_log_approved_and_rejected_record_the_bundle(self, tmp_path):
        log, _ = _log(tmp_path)
        log.log_approved(["Delete Sequence 5"], reasons=["blacklisted"])
        log.log_rejected(["Delete Sequence 5"])
        events = list(log.iter_events())
        assert [e["event"] for e in events] == ["approved", "rejected"]
        assert events[0]["commands"] == ["Delete Sequence 5"]

    def test_log_blocked_requires_a_reason(self, tmp_path):
        log, _ = _log(tmp_path)
        log.log_blocked("Delete", reason="live lock active")
        (event,) = list(log.iter_events())
        assert event["event"] == "blocked"
        assert event["reason"] == "live lock active"


class TestFallbackDetectorWiring:
    def test_fallback_decision_lands_in_the_durable_audit_log(self, tmp_path):
        # Section B: wire the M3 fallback detector's audit sink to the real
        # M4 audit log — the AuditLog satisfies the AuditSink protocol.
        log, _ = _log(tmp_path)
        settings = FallbackSettings(window_turns=3, consecutive_windows=1, threshold_seconds=1.0)
        detector = FallbackDetector(settings, audit_sink=log, active_provider="anthropic")
        for _ in range(3):
            detector.observe_turn(5.0)
        events = [e for e in log.iter_events() if e["event"] == "provider_fallback_triggered"]
        assert len(events) == 1
        assert events[0]["provider"] == "anthropic"
