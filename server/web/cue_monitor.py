"""Live cue-progress monitor — read-only snapshot (T-C, wave 2).

Ad-hoc contract, no SPEC on file (coordinator directive, 2026-08-02). Two
independent read paths:

1. Per-executor cue progress — for each ALREADY console-verified executor
   number (``server/web/dash.py::resolved_executor_nos`` stays the one owner
   of that resolution; this module builds no executor list of its own), reads
   the SAME "Executor <n>" identity probe
   ``server/safety/console.py::StateBodyFetcher._fetch_executor_body`` uses
   (``node.sequenceNo``), then reads the assigned sequence's cue children off
   ``DataPool/Sequences/<no>`` the same way ``server/orchestrator/tools.py``'s
   ``drill_into`` opens any other pool.

2. Recent execution history — a pure read of ``server.safety.audit.AuditLog``,
   independent of the console connection entirely. This is the monitor's
   guaranteed floor: it renders even when the console is unreachable.

Current-cue read (UNVERIFIED — documented per this project's established
doctrine that a static probe cannot answer what only live firing can): no
PROTOCOL.md / rulebook entry names a confirmed MA3 property that exposes an
executor's live cue position. ``CURRENT_CUE_PROPERTY_CANDIDATES`` below is
tried, in order, as candidate guesses; every candidate failing is the
EXPECTED and NORMAL degrade path, never an error — the entry reports
``status: "unavailable"`` and the caller (the UI) is responsible for telling
the operator why the field is empty, never for estimating a percentage or a
countdown that no channel here confirms (out of scope by contract).

Chokepoint discipline (unchanged from dash.py/panel.py): this module holds NO
execution surface of its own — it never imports the OSC send surface.
"""

from __future__ import annotations

from server.orchestrator.ports import PropertyQueryPort, StateQueryPort
from server.orchestrator.tools import rig_object
from server.prechk.query import read_properties
from server.safety.audit import AuditLog
from server.web.messages import cue_executor_entry, cue_history_entry, cue_monitor_event

SEQUENCE_PATH_TEMPLATE = "DataPool/Sequences/{sequence_no}"

# @MX:NOTE: [AUTO] UNVERIFIED candidate(s) for an executor's live cue-position
# property. console/lua/PROTOCOL.md documents the `state`/`prop`/`ping` reply
# kinds only; no property name that exposes a PLAYBACK POSITION has ever been
# exercised against a live console on this project (see module docstring
# ASSUMPTION). Tried in order; every failure degrades to "unavailable".
# @MX:CEILING: single unverified guess — do not add more without a live-probe
# session that actually confirms (or refutes) a candidate name.
# @MX:UPGRADE: replace/extend once a live "prop" round trip against a running
# executor confirms which property (if any) exposes the current cue.
CURRENT_CUE_PROPERTY_CANDIDATES: tuple[str, ...] = ("Cue",)

DEFAULT_HISTORY_LIMIT = 20


def _executor_reference(console_no: int) -> str:
    return f"Executor {console_no}"


def _cue_items(children: list) -> list[dict]:
    """One entry per cue child: its pool slot + name, plus the responder's
    additive real cue number (``cueNo``, responder 1.5.0+) when it could read
    one (console/lua/PROTOCOL.md §4.2) — never substituted from the slot."""
    items: list[dict] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        obj = rig_object(child)
        no = obj.get("no")
        if no is None:
            continue
        entry: dict = {"no": no, "name": str(obj.get("name", ""))}
        cue_no = child.get("cueNo")
        if isinstance(cue_no, int):
            entry["cue_no"] = cue_no
        items.append(entry)
    return items


def _read_current_cue(property_port: PropertyQueryPort, executor_ref: str) -> dict:
    """Best-effort current-cue read. Every candidate failing is the NORMAL
    path (see module docstring) — this never raises."""
    tried = list(CURRENT_CUE_PROPERTY_CANDIDATES)
    reads = read_properties(property_port, executor_ref, tried)
    for name in tried:
        read = reads.get(name)
        if read is not None and read.ok and read.value:
            return {"status": "ok", "value": read.value, "property": name, "tried": tried}
    return {"status": "unavailable", "tried": tried}


def build_executor_cue_progress(
    state_port: StateQueryPort,
    property_port: PropertyQueryPort,
    console_no: int,
) -> dict:
    """One resolved executor's cue-progress entry (contract item 1)."""
    executor_ref = _executor_reference(console_no)
    try:
        identity = state_port.query_state(executor_ref)
    except Exception:
        return cue_executor_entry(executor_no=console_no, status="unavailable")

    node = identity.get("node") if isinstance(identity, dict) else None
    sequence_no = node.get("sequenceNo") if isinstance(node, dict) else None
    if not isinstance(sequence_no, int):
        return cue_executor_entry(executor_no=console_no, status="unassigned")

    sequence_path = SEQUENCE_PATH_TEMPLATE.format(sequence_no=sequence_no)
    try:
        sequence_payload = state_port.query_state(sequence_path)
    except Exception:
        return cue_executor_entry(
            executor_no=console_no, status="unavailable", sequence_no=sequence_no
        )

    sequence_node = sequence_payload.get("node") if isinstance(sequence_payload, dict) else None
    sequence_name = str(sequence_node.get("name", "")) if isinstance(sequence_node, dict) else ""
    cues = _cue_items(sequence_payload.get("children", []))
    current_cue = _read_current_cue(property_port, executor_ref)

    return cue_executor_entry(
        executor_no=console_no,
        status="ok",
        sequence_no=sequence_no,
        sequence_name=sequence_name,
        cues=cues,
        current_cue=current_cue,
    )


def build_cue_progress(
    state_port: StateQueryPort,
    property_port: PropertyQueryPort,
    console_nos: list[int],
) -> list[dict]:
    """One entry per already-resolved executor console number (contract item 1)."""
    return [build_executor_cue_progress(state_port, property_port, no) for no in console_nos]


def recent_execution_history(audit: AuditLog, *, limit: int = DEFAULT_HISTORY_LIMIT) -> list[dict]:
    """The most recent console COMMAND executions, oldest-first (contract item 2).

    Reads ``AuditLog.iter_events`` directly — no console round trip, so this
    renders even when the console is completely unreachable (the monitor's
    guaranteed floor per the coordinator's contract).

    Filtered to ``kind == "command"`` (``server/safety/gate.py``'s
    ``_execute_cleared`` — the only writer of that kind): every OTHER
    ``executed`` kind (``state_query`` / ``property_query`` / ``heartbeat`` /
    ``deploy``) is the gate's own internal probing, INCLUDING the very
    ``query_state``/``query_property`` calls this module's own executor-cue
    read performs — without this filter, building one cue-monitor snapshot
    would pollute its own "recent history" with its own read traffic.
    """
    executed = [
        event
        for event in audit.iter_events()
        if event.get("event") == "executed" and event.get("kind") == "command"
    ]
    tail = executed[-limit:] if limit > 0 else executed
    return [
        cue_history_entry(
            ts=str(event.get("ts", "")),
            command=str(event.get("command", "")),
            ok=bool(event.get("ok", True)),
        )
        for event in tail
    ]


def cue_monitor_snapshot(
    state_port: StateQueryPort,
    property_port: PropertyQueryPort,
    audit: AuditLog,
    console_nos: list[int],
    *,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> dict:
    """The full ``cue_monitor`` server event for one refresh (contract items 1+2)."""
    return cue_monitor_event(
        executors=build_cue_progress(state_port, property_port, console_nos),
        history=recent_execution_history(audit, limit=history_limit),
    )
