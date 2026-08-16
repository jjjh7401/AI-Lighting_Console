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


class TestUnserializableValuesNeverDropTheEvent:
    def test_record_with_unserializable_value_still_writes_one_line(self, tmp_path):
        class Unserializable:
            def __repr__(self) -> str:
                return "Unserializable()"

        log, _ = _log(tmp_path)
        # Must not raise TypeError, and must not lose the event.
        log.record({"event": "blocked", "command": Unserializable(), "reason": "bad type"})
        files = _lines(tmp_path / "audit")
        (line,) = files["audit-20260716.jsonl"]
        event = json.loads(line)  # re-parses cleanly — no truncated/half-written JSON
        assert event["event"] == "blocked"
        assert event["reason"] == "bad type"
        assert event["command"] == "Unserializable()"


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


class TestProbeFamilySplit:
    """Growth fix (handoff 2026-08-15 item 2): read-probe traffic routes to a
    capped, short-retention ``probe-`` family; command/gate events stay 90-day."""

    def _probe_lines(self, directory):
        return {
            path.name: path.read_text(encoding="utf-8").splitlines()
            for path in sorted(directory.glob("probe-*.jsonl"))
        }

    def test_probe_kinds_route_to_the_probe_family(self, tmp_path):
        log, _clock = _log(tmp_path)
        log.log_executed("Patch/Stages", kind="state_query")
        log.log_executed("Sequence 1", kind="property_query")
        log.log_executed("ping", kind="heartbeat")
        log.log_executed("Store Cue 5", kind="command")
        audit = _lines(tmp_path / "audit")["audit-20260716.jsonl"]
        probe = self._probe_lines(tmp_path / "audit")["probe-20260716.jsonl"]
        assert [json.loads(line)["command"] for line in audit] == ["Store Cue 5"]
        assert [json.loads(line)["kind"] for line in probe] == [
            "state_query",
            "property_query",
            "heartbeat",
        ]

    def test_a_deploy_sub_send_never_routes_to_the_probe_family(self, tmp_path):
        log, _clock = _log(tmp_path)
        log.log_executed("Import Plugin", kind="state_query", deploy_of="Responder")
        assert self._probe_lines(tmp_path / "audit") == {}
        (line,) = _lines(tmp_path / "audit")["audit-20260716.jsonl"]
        assert json.loads(line)["deploy_of"] == "Responder"

    def test_iter_events_still_sees_both_families(self, tmp_path):
        log, _clock = _log(tmp_path)
        log.log_executed("Store Cue 5", kind="command")
        log.log_executed("Patch/Stages", kind="state_query")
        kinds = {e["kind"] for e in log.iter_events()}
        assert kinds == {"command", "state_query"}

    def test_reversed_read_can_skip_the_probe_family(self, tmp_path):
        log, _clock = _log(tmp_path)
        log.log_executed("Patch/Stages", kind="state_query")
        log.log_executed("Store Cue 5", kind="command")
        events = list(log.iter_events_reversed(include_probes=False))
        assert [e["kind"] for e in events] == ["command"]

    def test_probe_files_purge_on_their_own_short_retention(self, tmp_path):
        log, clock = _log(tmp_path, probe_retention_days=2)
        log.log_executed("Patch/Stages", kind="state_query")
        log.log_executed("Store Cue 5", kind="command")
        clock.advance(days=3)
        log.log_executed("Store Cue 6", kind="command")
        assert self._probe_lines(tmp_path / "audit") == {}
        assert len(_lines(tmp_path / "audit")) == 2  # audit family untouched

    def test_the_daily_byte_cap_drops_probes_after_one_marker(self, tmp_path):
        log, _clock = _log(tmp_path, probe_daily_max_bytes=1)
        log.log_executed("Patch/A", kind="state_query")  # first write: file empty
        log.log_executed("Patch/B", kind="state_query")  # over cap -> marker
        log.log_executed("Patch/C", kind="state_query")  # over cap -> dropped
        lines = self._probe_lines(tmp_path / "audit")["probe-20260716.jsonl"]
        events = [json.loads(line) for line in lines]
        assert [e.get("command", e["event"]) for e in events] == [
            "Patch/A",
            "probe_log_capped",
        ]

    def test_startup_compaction_splits_a_legacy_mixed_file(self, tmp_path):
        # Dated YESTERDAY relative to the fake clock (2026-07-16): today's
        # file is deliberately never rewritten (concurrent-append safety).
        directory = tmp_path / "audit"
        directory.mkdir()
        legacy = directory / "audit-20260715.jsonl"
        rows = [
            {
                "ts": "2026-07-15T10:00:00+00:00",
                "event": "executed",
                "kind": "command",
                "command": "Store Cue 5",
            },
            {
                "ts": "2026-07-15T10:00:01+00:00",
                "event": "executed",
                "kind": "state_query",
                "command": "Patch/Stages",
            },
        ]
        legacy.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        log, _clock = _log(tmp_path)  # __init__ runs the compaction
        audit = _lines(directory)["audit-20260715.jsonl"]
        probe = self._probe_lines(directory)["probe-20260715.jsonl"]
        assert [json.loads(line)["command"] for line in audit] == ["Store Cue 5"]
        assert [json.loads(line)["command"] for line in probe] == ["Patch/Stages"]
        assert list(log.iter_events_reversed(include_probes=False))[0]["command"] == "Store Cue 5"

    def test_compaction_never_rewrites_todays_file(self, tmp_path):
        # Independent review 2026-08-16: a concurrent AuditLog only ever
        # appends to TODAY's file; rewriting it via os.replace could unlink a
        # racing durable append. Today's mixed file stays untouched.
        directory = tmp_path / "audit"
        directory.mkdir()
        legacy = directory / "audit-20260716.jsonl"  # == the fake clock's today
        rows = [
            {
                "ts": "2026-07-16T10:00:00+00:00",
                "event": "executed",
                "kind": "command",
                "command": "Store Cue 5",
            },
            {
                "ts": "2026-07-16T10:00:01+00:00",
                "event": "executed",
                "kind": "state_query",
                "command": "Patch/Stages",
            },
        ]
        body = "".join(json.dumps(r) + "\n" for r in rows)
        legacy.write_text(body, encoding="utf-8")
        _log(tmp_path)
        assert legacy.read_text(encoding="utf-8") == body  # byte-identical
        assert self._probe_lines(directory) == {}

    def test_compaction_drops_probes_older_than_probe_retention(self, tmp_path):
        directory = tmp_path / "audit"
        directory.mkdir()
        legacy = directory / "audit-20260701.jsonl"  # 15 days before the clock
        rows = [
            {
                "ts": "2026-07-01T10:00:00+00:00",
                "event": "executed",
                "kind": "state_query",
                "command": "Patch/Old",
            },
            {"ts": "2026-07-01T10:00:01+00:00", "event": "approved", "commands": ["Store Cue 5"]},
        ]
        legacy.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        _log(tmp_path)
        assert self._probe_lines(directory) == {}
        (line,) = _lines(directory)["audit-20260701.jsonl"]
        assert json.loads(line)["event"] == "approved"
