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

from server.safety.approval import ApprovalRequest

PROTOCOL_VERSION = 1

# Closed set of client -> server message types.
CLIENT_MESSAGE_TYPES = ("chat", "approval_decision", "lock", "status_request")


class ProtocolError(ValueError):
    """A client message violated the protocol (rejected before any handling)."""


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

    if message_type == "approval_decision":
        request_id = message.get("request_id")
        approved = message.get("approved")
        if not isinstance(request_id, str) or not request_id:
            raise ProtocolError("approval_decision.request_id must be a non-empty string")
        if not isinstance(approved, bool):
            raise ProtocolError("approval_decision.approved must be a boolean")
        return {
            "v": PROTOCOL_VERSION,
            "type": "approval_decision",
            "request_id": request_id,
            "approved": approved,
        }

    if message_type == "lock":
        active = message.get("active")
        if not isinstance(active, bool):
            raise ProtocolError("lock.active must be a boolean")
        return {"v": PROTOCOL_VERSION, "type": "lock", "active": active}

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


def status_event(*, health: str, live_lock: bool, executions_blocked: bool) -> dict:
    """Gate-truth status surface (REQ-MVP-030/031 UI half + lock state)."""
    return _event(
        "status", health=health, live_lock=live_lock, executions_blocked=executions_blocked
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
