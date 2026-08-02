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

Current-cue read (T-H3, coordinator live probe, 2026-08-02 — LIVE-VERIFIED,
supersedes the earlier "unavailable" doctrine below the module docstring):
the property lives on the SEQUENCE handle, not the executor — ``prop
DataPool/Sequences/80 CurrentCue`` returned ``'Sequence 80.1'`` at rest and
``'Sequence 80.2'`` after two ``Go+ Executor 191`` presses, i.e. it tracks
playback. The earlier executor-handle probe (``CURRENT_CUE_PROPERTY_CANDIDATES``
tried against ``Executor <n>``) was reading the WRONG object — that failure
was real, but the "no channel exposes this" conclusion it supported was not.
The console's own ``CueNo`` property is UNRELIABLE (observed ``'1'`` at rest,
``''`` once playing) and is deliberately never read here. The value's shape
is ``<sequence name>.<cue index>`` — the index is taken from after the LAST
``.``; anything that does not end in a bare integer suffix (an unexpected
shape, or an empty string) degrades to ``"unavailable"`` rather than being
guessed at.

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

# @MX:ANCHOR: [AUTO] the live-verified current-cue property — read off the
# SEQUENCE handle (``DataPool/Sequences/<no>``), never the executor. A prior
# `prop` round trip against a running executor confirmed this (module
# docstring, T-H3): "CurrentCue" tracks playback (`.1` -> `.2` across two
# Go+ presses); the console's own "CueNo" property is unreliable and is
# deliberately NOT read (see module docstring).
# @MX:REASON: this replaced an UNVERIFIED executor-handle guess
# (`CURRENT_CUE_PROPERTY_CANDIDATES = ("Cue",)`, tried against `Executor <n>`)
# that always failed — not because no such property exists, but because it
# was aimed at the wrong object. Do not revert to probing the executor
# handle without a fresh live probe that actually contradicts this one.
CURRENT_CUE_PROPERTY_CANDIDATES: tuple[str, ...] = ("CurrentCue",)

# T-H3 — `<sequence name>.<cue index>` is the confirmed shape; the index is
# whatever follows the LAST '.', and must be a bare non-negative integer or
# the read degrades to "unavailable" rather than guessing at a malformed or
# empty value (the coordinator's probe: '' once playing rules out treating a
# missing suffix as "still at cue 0").
_CURRENT_CUE_INDEX_RE = re.compile(r"\.(\d+)$")


def _parse_current_cue_index(value: str) -> int | None:
    """The integer after the LAST ``.`` in ``value``, or ``None`` when the
    shape does not match (empty string, no ``.``, non-integer suffix)."""
    match = _CURRENT_CUE_INDEX_RE.search(value)
    return int(match.group(1)) if match else None


def _cue_name_for_index(cues: list[dict], index: int) -> str | None:
    """The cue name matching ``index``, or ``None`` when no cue in the list
    carries it — never silently dropped by the caller (the index itself is
    still exposed; see ``_read_current_cue``).

    Prefers the responder's real cue number (``cue_no``) when present, since
    that is what ``CurrentCue``'s index almost certainly names; falls back to
    the pool slot (``no``) for cues the responder could not number.
    """
    for cue in cues:
        if cue.get("cue_no") == index:
            return cue.get("name")
    for cue in cues:
        if cue.get("no") == index:
            return cue.get("name")
    return None


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


def _read_current_cue(
    property_port: PropertyQueryPort, sequence_path: str, cues: list[dict]
) -> dict:
    """Best-effort current-cue read off the SEQUENCE handle (T-H3 — see
    module docstring for why this is the sequence, not the executor).

    A read failure, an empty value, or a value that does not end in an
    integer suffix all degrade to ``"unavailable"`` — never guessed at. On
    success, ``value`` carries the parsed cue index, plus its name (from
    ``cues``) when the index maps to a known cue — "index only" is a valid,
    surfaced outcome (REQ: never silently dropped), not a failure.
    """
    tried = list(CURRENT_CUE_PROPERTY_CANDIDATES)
    reads = read_properties(property_port, sequence_path, tried)
    for name in tried:
        read = reads.get(name)
        if read is None or not read.ok or not read.value:
            continue
        index = _parse_current_cue_index(read.value)
        if index is None:
            continue
        cue_name = _cue_name_for_index(cues, index)
        value = str(index) if cue_name is None else f"{index} — {cue_name}"
        return {"status": "ok", "value": value, "property": name, "tried": tried}
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
    current_cue = _read_current_cue(property_port, sequence_path, cues)

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
