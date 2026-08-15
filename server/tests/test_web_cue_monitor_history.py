"""The cue-monitor history read is bounded — never a whole-log parse.

Measured 2026-08-15: the audit directory had grown to 709 MB (a background
poller writes ~10 probe events/second), and `recent_execution_history`'s
whole-log `iter_events` scan turned every UI refresh into hundreds of MB of
transient objects — GC pressure that starved the event loop. These tests pin
the replacement: newest-first bounded reading that stops at `limit` matches.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.safety.audit import AuditLog
from server.web.cue_monitor import recent_execution_history


def _log(tmp_path: Path) -> AuditLog:
    return AuditLog(directory=tmp_path)


def _write_day(tmp_path: Path, day: str, events: list[dict]) -> None:
    path = tmp_path / f"audit-{day}.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


def _command(ts: str, command: str) -> dict:
    return {"ts": ts, "event": "executed", "command": command, "kind": "command", "ok": True}


def _probe(ts: str) -> dict:
    return {
        "ts": ts,
        "event": "executed",
        "command": "Executor 1",
        "kind": "state_query",
        "ok": True,
    }


class TestReversedIterator:
    def test_yields_newest_first_across_files_and_chunk_seams(self, tmp_path):
        _write_day(tmp_path, "20260101", [_command("t1", "A"), _command("t2", "B")])
        _write_day(tmp_path, "20260102", [_command("t3", "C")])
        # A tiny chunk forces the partial-line carry path on every boundary.
        events = list(_log(tmp_path).iter_events_reversed(chunk_bytes=7))
        assert [e["command"] for e in events] == ["C", "B", "A"]

    def test_the_reversed_read_equals_the_forward_read_reversed(self, tmp_path):
        _write_day(tmp_path, "20260101", [_command(f"t{i}", f"cmd {i}") for i in range(50)])
        log = _log(tmp_path)
        assert list(log.iter_events_reversed(chunk_bytes=64)) == list(
            reversed(list(log.iter_events()))
        )


class TestBoundedHistory:
    def test_history_is_the_newest_limit_commands_oldest_first(self, tmp_path):
        events = []
        for i in range(30):
            events.append(_command(f"2026-01-01T00:00:{i:02d}", f"Go+ Executor {i}"))
            events.append(_probe(f"2026-01-01T00:00:{i:02d}"))
        _write_day(tmp_path, "20260101", events)
        entries = recent_execution_history(_log(tmp_path), limit=5)
        assert [e["command"] for e in entries] == [f"Go+ Executor {i}" for i in range(25, 30)]

    def test_probe_kinds_never_reach_the_history(self, tmp_path):
        _write_day(tmp_path, "20260101", [_probe("t")] * 100 + [_command("t", "Go+ Executor 1")])
        entries = recent_execution_history(_log(tmp_path), limit=20)
        assert [e["command"] for e in entries] == ["Go+ Executor 1"]

    def test_the_scan_stops_at_the_limit_instead_of_walking_the_whole_log(self, tmp_path):
        # A poisoned FIRST line proves early termination: reaching it raises.
        path = tmp_path / "audit-20260101.jsonl"
        lines = ["{not json"] + [json.dumps(_command(f"t{i}", f"cmd {i}")) for i in range(200)]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        entries = recent_execution_history(_log(tmp_path), limit=3)
        assert [e["command"] for e in entries] == ["cmd 197", "cmd 198", "cmd 199"]
