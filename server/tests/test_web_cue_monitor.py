"""Live cue-progress monitor builder tests (T-C, wave 2 — ad-hoc contract).

Every test drives the builder through in-memory StateQueryPort/PropertyQueryPort
fakes — the same shape ``gate.state_port`` presents — so nothing here can reach
the console or the OSC send surface (chokepoint discipline unchanged from
test_web_dash.py).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.cue_monitor import (
    CURRENT_CUE_PROPERTY_CANDIDATES,
    _cue_name_for_index,
    _parse_current_cue_index,
    build_cue_progress,
    build_executor_cue_progress,
    cue_monitor_snapshot,
    recent_execution_history,
)
from server.web.messages import PROTOCOL_VERSION

from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole


class FakeStatePort:
    """Fake StateQueryPort backed by path -> decoded snapshot payload."""

    def __init__(self, tree: dict):
        self.tree = tree
        self.queries: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queries.append(path)
        if path not in self.tree:
            raise LookupError(f"unknown object path: {path}")
        return self.tree[path]


class FakePropertyPort:
    """Fake PropertyQueryPort backed by (path, property) -> payload."""

    def __init__(self, values: dict[tuple[str, str], dict]):
        self.values = values
        self.queries: list[tuple[str, str]] = []

    def query_property(self, path: str, property_name: str) -> dict:
        self.queries.append((path, property_name))
        if (path, property_name) not in self.values:
            raise LookupError(f"unknown property: {path} {property_name}")
        return self.values[(path, property_name)]


def _identity(sequence_no: int | None) -> dict:
    node: dict[str, object] = {"name": "Executor 101", "class": "Executor"}
    if sequence_no is not None:
        node["sequenceNo"] = sequence_no
    return {"v": 1, "kind": "state", "ok": True, "node": node}


def _sequence_payload(name: str, cues: list[tuple[int, str, int | None]]) -> dict:
    children = []
    for slot, cue_name, cue_no in cues:
        child: dict[str, object] = {"i": slot, "name": cue_name, "class": "Cue"}
        if cue_no is not None:
            child["cueNo"] = cue_no
        children.append(child)
    return {
        "v": 1,
        "kind": "state",
        "ok": True,
        "node": {"name": name, "class": "Sequence", "childCount": len(children)},
        "children": children,
    }


class TestParseCurrentCueIndex:
    """T-H3 — the coordinator's live-verified `<sequence name>.<index>`
    shape, parsed from after the LAST '.'. Three branches per the task
    contract: normal, empty string, unexpected shape."""

    def test_parses_the_index_after_the_last_dot(self):
        assert _parse_current_cue_index("Sequence 80.2") == 2

    def test_parses_a_sequence_name_that_itself_contains_a_dot(self):
        # The rule is explicitly "the LAST '.'" — a dotted sequence name
        # must not confuse which suffix is the index.
        assert _parse_current_cue_index("Song v1.2.5") == 5

    def test_an_empty_string_fails_to_parse(self):
        # The coordinator's own finding: CueNo goes '' once playing. A blank
        # CurrentCue value must degrade the same way, never be treated as 0.
        assert _parse_current_cue_index("") is None

    def test_an_unexpected_shape_with_no_integer_suffix_fails_to_parse(self):
        assert _parse_current_cue_index("Sequence 80") is None
        assert _parse_current_cue_index("Sequence 80.") is None
        assert _parse_current_cue_index("Sequence 80.abc") is None


class TestCueNameForIndex:
    def test_matches_by_the_responders_real_cue_number_first(self):
        cues = [
            {"no": 1, "name": "Intro", "cue_no": 1},
            {"no": 2, "name": "Hook Drop", "cue_no": 2},
        ]
        assert _cue_name_for_index(cues, 2) == "Hook Drop"

    def test_falls_back_to_the_pool_slot_when_no_cue_no_matches(self):
        cues = [{"no": 3, "name": "Slot 3"}]
        assert _cue_name_for_index(cues, 3) == "Slot 3"

    def test_returns_none_when_no_cue_carries_the_index_at_all(self):
        # Never dropped silently by the CALLER — see _read_current_cue,
        # which still surfaces the bare index in this case.
        cues = [{"no": 1, "name": "Intro", "cue_no": 1}]
        assert _cue_name_for_index(cues, 9) is None


class TestBuildExecutorCueProgress:
    def test_unavailable_when_the_executor_identity_query_fails(self):
        # Degrade path 1/2 (coordinator contract): no console connection.
        state_port = FakeStatePort({})
        property_port = FakePropertyPort({})

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry == {
            "executor_no": 101,
            "status": "unavailable",
            "sequence_no": None,
            "sequence_name": None,
            "cues": [],
            "current_cue": None,
            "last_app_action": None,
        }

    def test_unassigned_when_the_executor_carries_no_sequence(self):
        state_port = FakeStatePort({"Executor 101": _identity(None)})
        property_port = FakePropertyPort({})

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry["status"] == "unassigned"
        assert entry["cues"] == []

    def test_unavailable_when_the_assigned_sequence_cannot_be_read(self):
        state_port = FakeStatePort({"Executor 101": _identity(5)})
        property_port = FakePropertyPort({})

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry["status"] == "unavailable"
        assert entry["sequence_no"] == 5

    def test_ok_reads_sequence_name_and_cue_list(self):
        state_port = FakeStatePort(
            {
                "Executor 101": _identity(5),
                "DataPool/Sequences/5": _sequence_payload(
                    "Song A", [(1, "PROBEA1", 1), (2, "PROBEA2", None)]
                ),
            }
        )
        property_port = FakePropertyPort({})  # every candidate fails -> unavailable

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry["status"] == "ok"
        assert entry["sequence_no"] == 5
        assert entry["sequence_name"] == "Song A"
        assert entry["cues"] == [
            {"no": 1, "name": "PROBEA1", "cue_no": 1},
            {"no": 2, "name": "PROBEA2"},
        ]

    def test_current_cue_degrades_when_the_property_read_fails(self):
        # Degrade path 2/2 (coordinator contract): connected, but the
        # current-cue property read fails — the EXPECTED and NORMAL path,
        # never an error. T-H3: the read now targets the SEQUENCE handle
        # (``DataPool/Sequences/<no>``), not the executor.
        state_port = FakeStatePort(
            {
                "Executor 101": _identity(5),
                "DataPool/Sequences/5": _sequence_payload("Song A", []),
            }
        )
        property_port = FakePropertyPort({})  # every query_property raises

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry["current_cue"] == {
            "status": "unavailable",
            "tried": list(CURRENT_CUE_PROPERTY_CANDIDATES),
        }

    def test_current_cue_degrades_on_an_empty_value(self):
        # T-H3 live finding: `CueNo` goes '' once playing — a blank read is
        # a real shape the console produces, not a hypothetical, so
        # `CurrentCue` must degrade on it too rather than guess.
        state_port = FakeStatePort(
            {
                "Executor 101": _identity(5),
                "DataPool/Sequences/5": _sequence_payload("Song A", []),
            }
        )
        property_port = FakePropertyPort(
            {("DataPool/Sequences/5", "CurrentCue"): {"ok": True, "value": ""}}
        )

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry["current_cue"]["status"] == "unavailable"

    def test_current_cue_degrades_on_an_unexpected_shape(self):
        # No trailing ".<int>" suffix — never guessed at.
        state_port = FakeStatePort(
            {
                "Executor 101": _identity(5),
                "DataPool/Sequences/5": _sequence_payload("Song A", []),
            }
        )
        property_port = FakePropertyPort(
            {("DataPool/Sequences/5", "CurrentCue"): {"ok": True, "value": "Song A"}}
        )

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry["current_cue"]["status"] == "unavailable"

    def test_current_cue_reads_ok_and_names_the_cue_when_the_index_is_known(self):
        # T-H3 live shape: "<sequence name>.<cue index>" off the SEQUENCE
        # handle — mirrors the coordinator's own probe ('Sequence 80.2').
        state_port = FakeStatePort(
            {
                "Executor 101": _identity(5),
                "DataPool/Sequences/5": _sequence_payload(
                    "Song A", [(1, "Intro", 1), (2, "Hook Drop", 2)]
                ),
            }
        )
        property_port = FakePropertyPort(
            {("DataPool/Sequences/5", "CurrentCue"): {"ok": True, "value": "Song A.2"}}
        )

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry["current_cue"] == {
            "status": "ok",
            "value": "2 — Hook Drop",
            "property": "CurrentCue",
            "tried": list(CURRENT_CUE_PROPERTY_CANDIDATES),
        }

    def test_current_cue_reads_ok_with_index_only_when_no_cue_matches(self):
        # An index the cue list does not contain is surfaced (never dropped
        # silently), just without a name.
        state_port = FakeStatePort(
            {
                "Executor 101": _identity(5),
                "DataPool/Sequences/5": _sequence_payload("Song A", [(1, "Intro", 1)]),
            }
        )
        property_port = FakePropertyPort(
            {("DataPool/Sequences/5", "CurrentCue"): {"ok": True, "value": "Song A.9"}}
        )

        entry = build_executor_cue_progress(state_port, property_port, 101)

        assert entry["current_cue"]["status"] == "ok"
        assert entry["current_cue"]["value"] == "9"


class TestBuildCueProgress:
    def test_one_entry_per_resolved_executor_number(self):
        state_port = FakeStatePort(
            {
                "Executor 101": _identity(None),
                "Executor 201": _identity(None),
            }
        )
        property_port = FakePropertyPort({})

        entries = build_cue_progress(state_port, property_port, [101, 201])

        assert [entry["executor_no"] for entry in entries] == [101, 201]

    def test_an_empty_console_nos_list_yields_no_entries(self):
        entries = build_cue_progress(FakeStatePort({}), FakePropertyPort({}), [])
        assert entries == []


class TestRecentExecutionHistory:
    def _audit(self, tmp_path: Path) -> AuditLog:
        fixed = datetime(2026, 8, 2, tzinfo=UTC)
        return AuditLog(directory=tmp_path / "audit", clock=lambda: fixed)

    def test_only_executed_events_are_surfaced_oldest_first(self, tmp_path: Path):
        audit = self._audit(tmp_path)
        audit.log_approved(["Go+ Executor 101"])
        audit.log_executed("Go+ Executor 101", ok=True)
        audit.log_blocked("Delete Group 1", reason="destructive")
        audit.log_executed("Off Executor 101", ok=False, detail="already off")

        history = recent_execution_history(audit)

        assert [entry["command"] for entry in history] == [
            "Go+ Executor 101",
            "Off Executor 101",
        ]
        assert history[0]["ok"] is True
        assert history[1]["ok"] is False
        assert all(entry["ts"] for entry in history)

    def test_the_console_does_not_need_to_answer_at_all(self, tmp_path: Path):
        # Contract item 2's guaranteed floor: a pure audit-log read, no
        # console round trip.
        audit = self._audit(tmp_path)
        audit.log_executed("Store Cue 1", ok=True)

        history = recent_execution_history(audit)

        assert len(history) == 1

    def test_limit_keeps_only_the_most_recent_entries(self, tmp_path: Path):
        audit = self._audit(tmp_path)
        for i in range(5):
            audit.log_executed(f"cmd {i}", ok=True)

        history = recent_execution_history(audit, limit=2)

        assert [entry["command"] for entry in history] == ["cmd 3", "cmd 4"]

    def test_an_empty_audit_log_yields_an_empty_history(self, tmp_path: Path):
        audit = self._audit(tmp_path)
        assert recent_execution_history(audit) == []

    def test_executor_commands_are_attributed_to_their_target(self, tmp_path: Path):
        audit = self._audit(tmp_path)
        audit.log_executed("Go+ Executor 191", ok=True)
        audit.log_executed("Off Executor 191", ok=False)
        audit.log_executed("Go+ Sequence 80", ok=True)
        audit.log_executed("Macro 5", ok=True)

        history = recent_execution_history(audit)

        assert [(entry["target_kind"], entry["target_no"]) for entry in history] == [
            ("executor", 191),
            ("executor", 191),
            ("sequence", 80),
            ("macro", 5),
        ]

    def test_an_unparseable_command_is_kept_with_unknown_attribution(self, tmp_path: Path):
        # T-H requirement: a parse failure is NEVER a reason to drop the row —
        # the full history must stay visible even for commands this module
        # cannot address to a target.
        audit = self._audit(tmp_path)
        audit.log_executed("Store Cue 1", ok=True)
        audit.log_executed("Delete Group 20", ok=True)

        history = recent_execution_history(audit)

        assert len(history) == 2
        assert all(entry["target_kind"] is None for entry in history)
        assert all(entry["target_no"] is None for entry in history)


class TestLastAppActionAttribution:
    """T-H — the app's last confirmed/failed action per executor, threaded
    from `recent_execution_history` into `build_cue_progress`."""

    def _audit(self, tmp_path: Path) -> AuditLog:
        fixed = datetime(2026, 8, 2, tzinfo=UTC)
        return AuditLog(directory=tmp_path / "audit", clock=lambda: fixed)

    def test_an_executor_with_no_app_history_carries_no_last_app_action(self, tmp_path: Path):
        audit = self._audit(tmp_path)
        state_port = FakeStatePort({"Executor 101": _identity(None)})
        property_port = FakePropertyPort({})

        event = cue_monitor_snapshot(state_port, property_port, audit, [101])

        assert event["executors"][0]["last_app_action"] is None

    def test_the_most_recent_matching_command_wins(self, tmp_path: Path):
        audit = self._audit(tmp_path)
        audit.log_executed("Go+ Executor 101", ok=True)
        audit.log_executed("Off Executor 101", ok=False)
        state_port = FakeStatePort({"Executor 101": _identity(None)})
        property_port = FakePropertyPort({})

        event = cue_monitor_snapshot(state_port, property_port, audit, [101])

        action = event["executors"][0]["last_app_action"]
        assert action["command"] == "Off Executor 101"
        assert action["ok"] is False

    def test_a_different_executors_history_is_not_cross_attributed(self, tmp_path: Path):
        audit = self._audit(tmp_path)
        audit.log_executed("Go+ Executor 201", ok=True)
        state_port = FakeStatePort({"Executor 101": _identity(None)})
        property_port = FakePropertyPort({})

        event = cue_monitor_snapshot(state_port, property_port, audit, [101])

        assert event["executors"][0]["last_app_action"] is None

    def test_last_app_action_is_reported_even_when_the_console_is_unreachable(self, tmp_path: Path):
        # The app's own claim ("we sent this and it was ok'd") is independent
        # of whether the LIVE identity read succeeds right now.
        audit = self._audit(tmp_path)
        audit.log_executed("Go+ Executor 101", ok=True)
        state_port = FakeStatePort({})  # every query_state raises -> "unavailable"
        property_port = FakePropertyPort({})

        event = cue_monitor_snapshot(state_port, property_port, audit, [101])

        assert event["executors"][0]["status"] == "unavailable"
        assert event["executors"][0]["last_app_action"]["command"] == "Go+ Executor 101"


class TestCueMonitorSnapshot:
    def test_combines_executor_progress_and_history(self, tmp_path: Path):
        state_port = FakeStatePort({"Executor 101": _identity(None)})
        property_port = FakePropertyPort({})
        audit = AuditLog(directory=tmp_path / "audit")
        audit.log_executed("Go+ Executor 101", ok=True)

        event = cue_monitor_snapshot(state_port, property_port, audit, [101])

        assert event["type"] == "cue_monitor"
        assert [entry["executor_no"] for entry in event["executors"]] == [101]
        assert len(event["history"]) == 1


# -- /ws dispatch (cue_monitor_request wired in app.py alongside dash_catalog_request) --


def _deps(tmp_path, provider):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    return WebDeps(
        gate=gate,
        provider=provider,
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
    )


def _send(ws, **fields) -> None:
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


class TestCueMonitorRequestDispatch:
    def test_cue_monitor_request_answers_with_a_cue_monitor_event(self, tmp_path):
        deps = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()  # initial status
            _send(ws, type="cue_monitor_request")
            event = ws.receive_json()
        assert event["type"] == "cue_monitor"
        assert isinstance(event["executors"], list)
        assert isinstance(event["history"], list)

    def test_cue_monitor_request_does_not_fall_through_to_status(self, tmp_path):
        deps = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()  # initial status
            _send(ws, type="cue_monitor_request")
            event = ws.receive_json()
        assert event["type"] != "status"

    def test_cue_monitor_request_surfaces_audit_log_history_without_a_console(self, tmp_path):
        # Contract item 2's guaranteed floor, exercised end-to-end: the fake
        # console answers nothing (empty rig), so every executor entry is
        # trivially empty, but a previously-recorded audit event still shows.
        deps = _deps(tmp_path, ScriptedProvider([]))
        deps.audit.log_executed("Go+ Executor 101", ok=True)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            ws.receive_json()  # initial status
            _send(ws, type="cue_monitor_request")
            event = ws.receive_json()
        assert event["history"] == [
            {
                "ts": event["history"][0]["ts"],
                "command": "Go+ Executor 101",
                "ok": True,
                "target_kind": "executor",
                "target_no": 101,
            }
        ]
