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

import re

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

# T-H — "app's last action" attribution (coordinator directive, 2026-08-02).
# ``server/web/panel.py::playback_command`` is this project's ONLY command
# author for these forms — "Go+ Executor <n>" / "Off Executor <n>" /
# "Go+ Sequence <n>" / "Off Sequence <n>" / "Macro <n>" (macro is one-shot,
# no verb word) — so parsing against exactly those literal shapes is not a
# guess, it is the inverse of a function this module can read directly.
# Anything else (a chat-composed command, an unrecognized verb) fails to
# parse and is carried as "attribution unknown" rather than dropped — see
# ``recent_execution_history``.
_PLAYBACK_TARGET_RE = re.compile(r"^(?:Go\+|Off)\s+(Executor|Sequence)\s+(\d+)$")
_MACRO_TARGET_RE = re.compile(r"^Macro\s+(\d+)$")

_WORD_TO_TARGET_KIND = {"Executor": "executor", "Sequence": "sequence"}


def _parse_command_target(command: str) -> tuple[str, int] | None:
    """The ``(target_kind, target_no)`` a command addresses, or ``None``.

    Best-effort inverse of ``panel.py::playback_command`` — a failure here is
    the NORMAL degrade path for any command this module was never meant to
    attribute (e.g. a chat-composed command), never an error.
    """
    match = _PLAYBACK_TARGET_RE.match(command)
    if match:
        return _WORD_TO_TARGET_KIND[match.group(1)], int(match.group(2))
    match = _MACRO_TARGET_RE.match(command)
    if match:
        return "macro", int(match.group(1))
    return None


def _last_app_action_for_executor(history: list[dict], executor_no: int) -> dict | None:
    """The most recent history row this app sent to ``executor_no``, or
    ``None`` when the app has never sent this executor anything (T-H: a
    console operated by hand, invisible to the app, is NOT a claim this
    function can make either way)."""
    for entry in reversed(history):
        if entry.get("target_kind") == "executor" and entry.get("target_no") == executor_no:
            return {"command": entry["command"], "ts": entry["ts"], "ok": entry["ok"]}
    return None


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
    *,
    last_app_action: dict | None = None,
) -> dict:
    """One resolved executor's cue-progress entry (contract item 1).

    ``last_app_action`` (T-H) is attributed by the CALLER (see
    ``build_cue_progress``) and threaded through every return branch — it is
    an independent claim ("what did the app last send this executor, and did
    the console ok it") from the live identity/sequence read above, and is
    just as meaningful when that read fails as when it succeeds.
    """
    executor_ref = _executor_reference(console_no)
    try:
        identity = state_port.query_state(executor_ref)
    except Exception:
        return cue_executor_entry(
            executor_no=console_no, status="unavailable", last_app_action=last_app_action
        )

    node = identity.get("node") if isinstance(identity, dict) else None
    sequence_no = node.get("sequenceNo") if isinstance(node, dict) else None
    if not isinstance(sequence_no, int):
        return cue_executor_entry(
            executor_no=console_no, status="unassigned", last_app_action=last_app_action
        )

    sequence_path = SEQUENCE_PATH_TEMPLATE.format(sequence_no=sequence_no)
    try:
        sequence_payload = state_port.query_state(sequence_path)
    except Exception:
        return cue_executor_entry(
            executor_no=console_no,
            status="unavailable",
            sequence_no=sequence_no,
            last_app_action=last_app_action,
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
        last_app_action=last_app_action,
    )


def build_cue_progress(
    state_port: StateQueryPort,
    property_port: PropertyQueryPort,
    console_nos: list[int],
    *,
    history: list[dict] | None = None,
) -> list[dict]:
    """One entry per already-resolved executor console number (contract item 1).

    ``history`` (T-H, optional — omission preserves the pre-T-H call shape
    every existing caller/test uses) is the SAME oldest-first list
    ``recent_execution_history`` builds; each executor's ``last_app_action``
    is attributed from it via ``_last_app_action_for_executor``.
    """
    history = history or []
    return [
        build_executor_cue_progress(
            state_port,
            property_port,
            no,
            last_app_action=_last_app_action_for_executor(history, no),
        )
        for no in console_nos
    ]


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

    T-H: each row also carries its best-effort ``(target_kind, target_no)``
    attribution (``None``/``None`` when the command string does not parse as
    one of ``panel.py``'s known forms) — an unattributable row is KEPT, never
    dropped, so the operator's full history stays trustworthy even for
    commands this module cannot address to an executor.
    """
    executed = [
        event
        for event in audit.iter_events()
        if event.get("event") == "executed" and event.get("kind") == "command"
    ]
    tail = executed[-limit:] if limit > 0 else executed
    entries = []
    for event in tail:
        command = str(event.get("command", ""))
        parsed = _parse_command_target(command)
        entries.append(
            cue_history_entry(
                ts=str(event.get("ts", "")),
                command=command,
                ok=bool(event.get("ok", True)),
                target_kind=parsed[0] if parsed else None,
                target_no=parsed[1] if parsed else None,
            )
        )
    return entries


def cue_monitor_snapshot(
    state_port: StateQueryPort,
    property_port: PropertyQueryPort,
    audit: AuditLog,
    console_nos: list[int],
    *,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> dict:
    """The full ``cue_monitor`` server event for one refresh (contract items 1+2).

    History is built ONCE and threaded into ``build_cue_progress`` (T-H) so
    each executor's ``last_app_action`` and the flat history list are
    attributed from the exact same read — never two independent audit-log
    passes that could observe different tails under concurrent writes.
    """
    history = recent_execution_history(audit, limit=history_limit)
    return cue_monitor_event(
        executors=build_cue_progress(state_port, property_port, console_nos, history=history),
        history=history,
    )
