"""WebSocket protocol v1 (M5 — REQ-MVP-020/021/022 wire contract).

Versioned message schema between the FastAPI WebSocket server and its clients
(the React UI and the M6 measurement harness). The full contract is documented
in ``server/web/PROTOCOL.md``; this module is the executable half: strict
client-message validation plus one builder per server event type.

Client messages that fail validation raise :class:`ProtocolError` and never
reach the orchestrator or the safety gate.
"""

from __future__ import annotations

import json

from server.deploy.review import ReviewRequest
from server.safety.approval import ApprovalRequest

PROTOCOL_VERSION = 1

# The show-control panel's client messages (SPEC-COPILOT-SHOWUI-001 M1). Like
# the M7 "review_decision" extension before it this is ADDITIVE: the protocol
# version stays 1 and every type below is registered on BOTH allowlists — here
# and in ``ui/src/protocol.ts`` — because a type present on only one side goes
# silently missing on the client and loudly wrong on the server
# (REQ-SHOWUI-014).
PANEL_CLIENT_MESSAGE_TYPES = (
    "panel_execute",
    "panel_stop",
    "panel_pin",
    "panel_unpin",
    "panel_catalog_request",
)

# Closed set of client -> server message types. "review_decision" is the M7
# additive extension (deploy review) — protocol version stays 1.
CLIENT_MESSAGE_TYPES = (
    "chat",
    "approval_decision",
    "review_decision",
    "lock",
    "status_request",
    *PANEL_CLIENT_MESSAGE_TYPES,
)

# The panel messages that address ONE console object, and therefore carry the
# (target_kind, target) pair the parser validates before anything downstream
# can build a command bundle out of it.
PANEL_TARGETED_MESSAGE_TYPES = ("panel_execute", "panel_stop", "panel_unpin")

# The tile's type badge — design.md §4 (LOOK / FX / SEQ).
PANEL_ITEM_KINDS = ("look", "effect", "sequence")

# @MX:ANCHOR: [AUTO] the closed set of console object classes a panel tile may
# address. Consumed by the client-message parser, the item constructor, and
# (from M2) the catalog builder and the pin store.
# @MX:REASON: REQ-SHOWUI-003 — a fixture's `no` is its patch SLOT, which is not
# its fixture id; only sequences and executors are objects whose `no` is the
# address the console fires. Admitting "fixtures" here would let the panel send
# `Go+ Fixture <slot>` and hit the wrong thing on stage.
PANEL_TARGET_KINDS = ("executor", "sequence")

# Where a tile came from: a chat-created look the user pinned (REQ-SHOWUI-004)
# or an object enumerated from the rig (REQ-SHOWUI-001).
PANEL_ITEM_SOURCES = ("pin", "auto")

# Why a catalog section is incomplete. These mirror the rig-context reasons
# (``server/orchestrator/tools.py``) and stay DISTINCT on the wire: "this path
# does not exist in the loaded showfile" and "the console did not answer" ask
# the operator for different actions, and merging them is exactly how two dead
# rig paths survived a whole stage unnoticed (REQ-SHOWUI-002).
PANEL_SECTION_STATUSES = ("ok", "path_not_resolved", "console_unreachable")

# ``status.console_input`` — the console-OSC-input reachability verdict carried
# alongside ``health`` so the UI can name the RIGHT cause for a console_offline
# state. Three values, deliberately NOT two: collapsing "we could not tell" into
# "nothing is listening" is how a confidently-wrong message gets shown again.
CONSOLE_INPUT_LISTENING = "listening"  # the port is held — the console's OSC input is live
CONSOLE_INPUT_SILENT = "silent"  # the port is free — nothing is listening there
CONSOLE_INPUT_UNDETERMINED = "undetermined"  # not determined (remote console / not probed)


class ProtocolError(ValueError):
    """A client message violated the protocol (rejected before any handling)."""


def _is_object_number(value: object) -> bool:
    """True when ``value`` is a console object number the panel may address.

    ``bool`` is checked FIRST because it is an ``int`` subclass in Python:
    without that guard ``True`` would sail through as object number 1 and the
    panel would fire at whatever sits in slot 1.

    Console pools are 1-based, so 0 addresses nothing — it is rejected in the
    same breath as a negative number rather than being handed downstream as a
    plausible-looking target.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def parse_client_message(raw: str) -> dict:
    """Parse + validate one client text frame; returns the normalized message."""
    try:
        message = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"not valid JSON: {error}") from error
    if not isinstance(message, dict):
        raise ProtocolError("message must be a JSON object")
    if message.get("v") != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version: {message.get('v')!r}")
    message_type = message.get("type")
    if message_type not in CLIENT_MESSAGE_TYPES:
        raise ProtocolError(f"unknown message type: {message_type!r}")

    if message_type == "chat":
        text = message.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ProtocolError("chat.text must be a non-empty string")
        return {"v": PROTOCOL_VERSION, "type": "chat", "text": text}

    if message_type in ("approval_decision", "review_decision"):
        request_id = message.get("request_id")
        approved = message.get("approved")
        if not isinstance(request_id, str) or not request_id:
            raise ProtocolError(f"{message_type}.request_id must be a non-empty string")
        if not isinstance(approved, bool):
            raise ProtocolError(f"{message_type}.approved must be a boolean")
        return {
            "v": PROTOCOL_VERSION,
            "type": message_type,
            "request_id": request_id,
            "approved": approved,
        }

    if message_type == "lock":
        active = message.get("active")
        if not isinstance(active, bool):
            raise ProtocolError("lock.active must be a boolean")
        return {"v": PROTOCOL_VERSION, "type": "lock", "active": active}

    if message_type in PANEL_TARGETED_MESSAGE_TYPES:
        # REQ-SHOWUI-022: the target is client-controlled, so it is validated
        # HERE — at parse time, before any caller can exist. A malformed target
        # therefore cannot reach a command bundle and cannot reach
        # ``gate.screen()``; it is refused with the same ProtocolError as any
        # other malformed frame and answered with an error event.
        #
        # This is the parse-time half only. Whether the (kind, no) pair names an
        # object that actually EXISTS in the catalog or the pin store is a
        # membership question, and membership is checked against the panel
        # store — which M2 introduces.
        target = message.get("target")
        if not _is_object_number(target):
            raise ProtocolError(f"{message_type}.target must be a positive integer object number")
        target_kind = message.get("target_kind")
        if target_kind not in PANEL_TARGET_KINDS:
            raise ProtocolError(f"{message_type}.target_kind must be one of {PANEL_TARGET_KINDS}")
        return {
            "v": PROTOCOL_VERSION,
            "type": message_type,
            "target_kind": target_kind,
            "target": target,
        }

    if message_type in ("panel_pin", "panel_catalog_request"):
        # Payload-free by design. The pin seed is the server's own
        # ``_last_created`` cross-turn memory (REQ-SHOWUI-004), so there is no
        # client-supplied target here to get wrong or to have to trust.
        return {"v": PROTOCOL_VERSION, "type": message_type}

    return {"v": PROTOCOL_VERSION, "type": "status_request"}


# -- server -> client event builders -------------------------------------------


def _event(event_type: str, **fields) -> dict:
    return {"v": PROTOCOL_VERSION, "type": event_type, **fields}


def chat_response_event(*, status: str, summary: str, text: str, commands: list[dict]) -> dict:
    """One instruction's final report (REQ-MVP-022 — Korean result reporting)."""
    return _event("chat_response", status=status, summary=summary, text=text, commands=commands)


def approval_request_event(*, request_id: str, request: ApprovalRequest) -> dict:
    """One pending approval bundle: commands + risk reasons + warnings (REQ-MVP-021)."""
    return _event(
        "approval_request",
        request_id=request_id,
        items=[
            {
                "command": item.command,
                "risk_reasons": list(item.risk_reasons),
                "warnings": list(item.warnings),
            }
            for item in request.items
        ],
        actions=["approve", "reject"],
    )


def approval_resolved_event(*, request_id: str, approved: bool) -> dict:
    """The decision echo so the UI can retire the approval card."""
    return _event("approval_resolved", request_id=request_id, approved=approved)


def review_request_event(*, request_id: str, request: ReviewRequest) -> dict:
    """One pending deploy review (M7, REQ-MVP-019/027): everything the
    reviewer must see — name, bounded source preview, compile verdict, and
    the destructive-scan report with its best-effort caveat."""
    scan = request.scan
    return _event(
        "review_request",
        request_id=request_id,
        plugin_name=request.plugin_name,
        source_preview=request.source_preview,
        source_length=request.source_length,
        source_truncated=request.source_truncated,
        compile_ok=request.compile_ok,
        scan={
            "destructive": scan.destructive,
            "findings": [
                {
                    "line": finding.line,
                    "command": finding.command,
                    "kind": finding.kind,
                    "matched_entry": finding.matched_entry,
                    "reasons": list(finding.reasons),
                }
                for finding in scan.findings
            ],
            "dynamic_calls": [
                {"line": call.line, "snippet": call.snippet} for call in scan.dynamic_calls
            ],
            "caveat": scan.caveat,
        },
        actions=["approve", "reject"],
    )


def review_resolved_event(*, request_id: str, approved: bool) -> dict:
    """The review decision echo so the UI can retire the review card."""
    return _event("review_resolved", request_id=request_id, approved=approved)


def status_event(
    *,
    health: str,
    live_lock: bool,
    executions_blocked: bool,
    console_input: str = CONSOLE_INPUT_UNDETERMINED,
    reply_port: int | None = None,
    receive_port: int | None = None,
) -> dict:
    """Gate-truth status surface (REQ-MVP-030/031 UI half + lock state).

    ``console_input``, ``reply_port`` and ``receive_port`` are ADDITIVE fields
    (protocol version stays 1, same call as the M7 ``review_decision``
    extension): purely informational diagnosis carriers with safe defaults, so a
    client that ignores them behaves exactly as before and a server that never
    diagnoses emits the pre-existing meaning. They NEVER alter ``health`` or
    ``executions_blocked`` — the gate's verdict is untouched; only the cause the
    UI names for it becomes accurate.

    ``reply_port``/``receive_port`` are the reply-port MISMATCH pair, and they
    appear together or not at all: a console reply was observed on
    ``reply_port`` while the app listens on ``receive_port``. Reporting both
    numbers, rather than silently switching to the observed one, is what keeps
    REQ-DEPLOY-026 intact — the operator decides which of the two moves.
    """
    return _event(
        "status",
        health=health,
        live_lock=live_lock,
        executions_blocked=executions_blocked,
        console_input=console_input,
        reply_port=reply_port,
        receive_port=receive_port,
    )


def proposal_event(*, commands: list[str], reasons: list[str]) -> dict:
    """A read-only proposal card produced under the live lock (REQ-MVP-016)."""
    return _event("proposal", commands=list(commands), reasons=list(reasons))


def error_event(*, message: str, kind: str = "") -> dict:
    """A Korean user-facing error — NEVER carries raw SDK text (REQ-MVP-044)."""
    return _event("error", message=message, kind=kind)


def busy_event(message: str) -> dict:
    """The session is already processing an instruction (one at a time)."""
    return _event("busy", message=message)


def notice_event(message: str) -> dict:
    """A standalone Korean notice (e.g. backup failure, REQ-MVP-034 UI half)."""
    return _event("notice", message=message)


# -- show-control panel (SPEC-COPILOT-SHOWUI-001 M1) ---------------------------


# @MX:ANCHOR: [AUTO] the panel tile's identity on the wire and in the pin store.
# @MX:REASON: REQ-SHOWUI-003 — pool numbers are non-contiguous, so "the Nth
# tile" and "object N" are different objects. Keying on the console's REAL `no`
# (never a list position) is what stops a rig with sequences at 2, 7, 41 from
# resolving tile #3 to a non-existent "Sequence 3". The `kind:no` shape also
# keeps Executor 41 and Sequence 41 apart, which a bare number cannot.
def panel_item_id(target_kind: str, target: int) -> str:
    """The stable tile key: ``"<target_kind>:<no>"`` (e.g. ``"executor:191"``)."""
    return f"{target_kind}:{target}"


def panel_item(
    *,
    kind: str,
    target_kind: str,
    target: int,
    name: str,
    source: str,
    appearance: str | None = None,
) -> dict:
    """One panel tile — the frozen item schema every later milestone builds on.

    | field         | meaning                                                  |
    |---------------|----------------------------------------------------------|
    | ``id``        | ``"<target_kind>:<no>"`` — derived, never a list position |
    | ``kind``      | the LOOK / FX / SEQ type badge (design.md §4)             |
    | ``target_kind``| the console object class the command addresses           |
    | ``target``    | the console's REAL object number                          |
    | ``name``      | the console name, verbatim                                |
    | ``appearance``| the appearance colour chip, or ``None``                   |
    | ``source``    | ``"pin"`` (chat-pinned) or ``"auto"`` (rig-enumerated)    |

    Every enum is closed and every violation raises — a tile that cannot be
    addressed correctly must not be constructed at all, because by the time it
    reaches a command bundle the wrong object is already on stage.
    """
    if kind not in PANEL_ITEM_KINDS:
        raise ValueError(f"panel item kind must be one of {PANEL_ITEM_KINDS}, got {kind!r}")
    if target_kind not in PANEL_TARGET_KINDS:
        raise ValueError(
            f"panel item target_kind must be one of {PANEL_TARGET_KINDS}, got {target_kind!r}"
        )
    if not _is_object_number(target):
        raise ValueError(f"panel item target must be a positive integer, got {target!r}")
    if source not in PANEL_ITEM_SOURCES:
        raise ValueError(f"panel item source must be one of {PANEL_ITEM_SOURCES}, got {source!r}")
    return {
        "id": panel_item_id(target_kind, target),
        "kind": kind,
        "target_kind": target_kind,
        "target": target,
        "name": name,
        "appearance": appearance,
        "source": source,
    }


def panel_section(
    *,
    name: str,
    status: str,
    truncated: bool = False,
    drilldown_capped: bool = False,
    contents_unavailable: bool = False,
) -> dict:
    """One catalog section's own account of how complete it is.

    A short tile list with no completeness signal is worse than no list at all:
    the operator would trust a rig they cannot fully see. The three flags mirror
    the rig-context ones (``server/orchestrator/tools.py``) and are carried all
    the way to the UI (REQ-SHOWUI-001):

    - ``truncated`` — the responder itself said the listing was cut short.
    - ``drilldown_capped`` — the per-call query budget ran out before every
      container in this section was opened, so tiles are missing.
    - ``contents_unavailable`` — at least one container could NOT be opened.
      Distinct from a verified-empty container: collapsing the two makes a
      console that failed mid-walk look like a show with nothing configured.

    ``status`` keeps the two failure causes apart (REQ-SHOWUI-002).
    """
    if status not in PANEL_SECTION_STATUSES:
        raise ValueError(
            f"panel section status must be one of {PANEL_SECTION_STATUSES}, got {status!r}"
        )
    return {
        "name": name,
        "status": status,
        "truncated": bool(truncated),
        "drilldown_capped": bool(drilldown_capped),
        "contents_unavailable": bool(contents_unavailable),
    }


def panel_catalog_event(*, items: list[dict], sections: list[dict]) -> dict:
    """The panel's executable tile list plus per-section completeness.

    ``items`` order IS grid order (REQ-SHOWUI-005/017): append-only, never
    sorted by either side. A tile that moves under the operator's finger
    mid-show is a misfire waiting to happen.
    """
    return _event("panel_catalog", items=list(items), sections=list(sections))


def panel_item_state_event(
    *, target_kind: str, target: int, running: bool, cue: str | None = None
) -> dict:
    """One tile's playback state. ``cue`` is the running sequence's current cue
    number when the console reported one (design.md §2), else ``None`` —
    a string because MA3 cue numbers are not integers (e.g. "1.5")."""
    return _event(
        "panel_item_state",
        id=panel_item_id(target_kind, target),
        target_kind=target_kind,
        target=target,
        running=bool(running),
        cue=cue,
    )


def panel_busy_event(*, target_kind: str, target: int, message: str) -> dict:
    """A panel execution was refused because one is already in flight.

    Names the tile it refused: the UI locks a tile the moment it is pressed
    (REQ-SHOWUI-011), so a bare busy message would leave that tile latched with
    nothing to unlock it. Distinct from ``busy`` — that one is the chat turn
    lock, which the panel deliberately does not share (REQ-SHOWUI-013).
    """
    return _event(
        "panel_busy",
        id=panel_item_id(target_kind, target),
        target_kind=target_kind,
        target=target,
        message=message,
    )
