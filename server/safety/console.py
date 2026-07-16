"""Gate-owned console I/O (M4) — the ONLY production caller of the OSC bridge.

Wraps the M2 wire protocol: exec-wrapped command execution with result
confirmation (REQ-MVP-004/032), responder heartbeat pings, and object-tree
state queries (REQ-MVP-003), all correlated by request id over the bridge's
feedback consumer. Every wait is bounded by a configurable timeout
(REQ-MVP-030~032: all timeouts configurable).

Chokepoint note (REQ-MVP-029): this module lives inside ``server/safety`` on
purpose — the AC-MVP-019 import-boundary architecture test allows bridge
imports ONLY here (plus named operator diagnostics).
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from server.bridge.osc import FeedbackMessage
from server.bridge.protocol import (
    ProtocolError,
    build_deploy_request,
    build_exec_request,
    build_ping,
    build_state_query,
    decode_payload,
)
from server.safety.expand import BodyUnavailable
from server.safety.monitor import HealthMonitor


@dataclass(frozen=True)
class LinkTimeouts:
    """Configurable wait bounds for every console interaction (design.md §E)."""

    exec_confirm_seconds: float = 5.0
    ping_seconds: float = 2.0
    state_query_seconds: float = 5.0
    # Deployment compiles + creates a plugin object console-side (M7) —
    # a longer bound than a plain command execution.
    deploy_confirm_seconds: float = 10.0


@dataclass(frozen=True)
class ExecOutcome:
    """One command execution attempt: ok / failed / unconfirmed (REQ-MVP-032)."""

    status: str  # "ok" | "failed" | "unconfirmed"
    detail: str = ""


class StateQueryError(Exception):
    """A state query failed or timed out."""


class ConsolePort(Protocol):
    """The gate's view of the console (implemented by ConsoleLink and fakes)."""

    def execute(self, command: str) -> ExecOutcome: ...

    def ping(self) -> bool: ...

    def query_state(self, path: str) -> dict: ...

    def deploy_plugin(self, name: str, lua_source: str) -> ExecOutcome:
        """Deploy one reviewed Lua plugin (M7); ok / failed / unconfirmed."""
        ...


class _Waiter:
    __slots__ = ("event", "payload")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.payload: dict | None = None


class ConsoleLink:
    """Request/reply correlation over the bridge (implements FeedbackConsumer)."""

    def __init__(
        self,
        *,
        send: Callable[[str], None] | None = None,
        timeouts: LinkTimeouts | None = None,
        monitor: HealthMonitor | None = None,
        id_prefix: str = "gate",
    ) -> None:
        self._send = send
        self._timeouts = timeouts or LinkTimeouts()
        self._monitor = monitor
        self._id_prefix = id_prefix
        self._counter = itertools.count(1)
        self._pending: dict[str, _Waiter] = {}
        self._pending_lock = threading.Lock()

    def bind_send(self, send: Callable[[str], None]) -> None:
        """Attach the bridge's send function (breaks the construction cycle)."""
        self._send = send

    # -- FeedbackConsumer ------------------------------------------------------

    def deliver(self, message: FeedbackMessage) -> None:
        """Accept one received feedback/state message; correlate by id."""
        if self._monitor is not None:
            self._monitor.note_activity()
        if not message.args or not isinstance(message.args[0], str):
            return
        try:
            payload = decode_payload(message.args[0])
        except ProtocolError:
            return  # foreign feedback — not a responder reply
        request_id = payload.get("id")
        with self._pending_lock:
            waiter = self._pending.get(request_id)
        if waiter is not None:
            waiter.payload = payload
            waiter.event.set()

    # -- request/reply helpers -------------------------------------------------

    def _new_id(self) -> str:
        return f"{self._id_prefix}-{next(self._counter)}"

    def _round_trip(self, wire: str, request_id: str, timeout: float) -> dict | None:
        if self._send is None:
            raise RuntimeError("ConsoleLink send is not bound (call bind_send first)")
        waiter = _Waiter()
        with self._pending_lock:
            self._pending[request_id] = waiter
        try:
            self._send(wire)
            if not waiter.event.wait(timeout):
                return None
            return waiter.payload
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    # -- console operations ------------------------------------------------------

    def execute(self, command: str) -> ExecOutcome:
        """Execute one command exec-wrapped; blocks until confirmed or timeout."""
        request_id = self._new_id()
        try:
            wire = build_exec_request(request_id, command)
        except ProtocolError as error:
            return ExecOutcome(
                status="failed", detail=f"cannot wrap command for result capture: {error}"
            )
        payload = self._round_trip(wire, request_id, self._timeouts.exec_confirm_seconds)
        if payload is None:
            return ExecOutcome(
                status="unconfirmed",
                detail=(
                    "no result confirmation within "
                    f"{self._timeouts.exec_confirm_seconds}s (send loss and feedback "
                    "loss are indistinguishable)"
                ),
            )
        ok = bool(payload.get("ok"))
        detail = str(payload.get("result") or payload.get("error") or "")
        return ExecOutcome(status="ok" if ok else "failed", detail=detail)

    def ping(self) -> bool:
        """Responder heartbeat; updates the health monitor when attached."""
        request_id = self._new_id()
        payload = self._round_trip(build_ping(request_id), request_id, self._timeouts.ping_seconds)
        if payload is None:
            if self._monitor is not None:
                self._monitor.note_ping_timeout()
            return False
        if self._monitor is not None:
            self._monitor.note_ping_success()
        return True

    def deploy_plugin(self, name: str, lua_source: str) -> ExecOutcome:
        """Deploy one plugin via the responder deploy verb (M7, REQ-MVP-019).

        Sends ONCE and never retries: like exec, a deploy timeout is
        UNCONFIRMED (send loss and reply loss are indistinguishable —
        REQ-MVP-032 discipline applies to deployments too).
        """
        request_id = self._new_id()
        try:
            wire = build_deploy_request(request_id, name, lua_source)
        except ProtocolError as error:
            return ExecOutcome(status="failed", detail=f"cannot build deploy request: {error}")
        payload = self._round_trip(wire, request_id, self._timeouts.deploy_confirm_seconds)
        if payload is None:
            return ExecOutcome(
                status="unconfirmed",
                detail=(
                    "no deploy confirmation within "
                    f"{self._timeouts.deploy_confirm_seconds}s (send loss and feedback "
                    "loss are indistinguishable)"
                ),
            )
        ok = bool(payload.get("ok"))
        detail = str(payload.get("error") or payload.get("result") or "deployed")
        return ExecOutcome(status="ok" if ok else "failed", detail=detail)

    def query_state(self, path: str) -> dict:
        """Object-tree snapshot query (REQ-MVP-003); raises on failure/timeout."""
        request_id = self._new_id()
        payload = self._round_trip(
            build_state_query(request_id, path), request_id, self._timeouts.state_query_seconds
        )
        if payload is None:
            if self._monitor is not None:
                self._monitor.note_query_timeout()
            raise StateQueryError(
                f"no state reply for {path!r} within {self._timeouts.state_query_seconds}s"
            )
        if not payload.get("ok"):
            raise StateQueryError(str(payload.get("error") or f"state query failed: {path}"))
        return payload


# -- reference body fetching (expand-or-hold production path) -----------------

# Object-tree path templates per recognized reference type. PLACEHOLDER
# assumption (onPC-unverified, M6 live calibration — same discipline as the M2
# PROTOCOL.md assumptions): a Macro/Plugin/Sequence body is readable as the
# child names of its object-tree node. Unmapped types are UNVERIFIABLE -> the
# expand-or-hold rule holds them for human approval (fail-safe).
DEFAULT_BODY_PATHS = {
    "Macro": "DataPool/Macros/{ref}",
    "Plugin": "DataPool/Plugins/{ref}",
    "Sequence": "DataPool/Sequences/{ref}",
}


class StateBodyFetcher:
    """Fetches reference bodies through the gate's state-query path (M2 wire)."""

    def __init__(
        self,
        query: Callable[[str], dict],
        path_templates: dict[str, str] | None = None,
    ) -> None:
        self._query = query
        self._templates = dict(path_templates or DEFAULT_BODY_PATHS)

    def fetch_body(self, reference: str) -> Sequence[str]:
        type_word, _, ref = reference.partition(" ")
        template = self._templates.get(type_word)
        if template is None or not ref:
            raise BodyUnavailable(f"no body path mapping for {reference!r}")
        try:
            payload = self._query(template.format(ref=ref))
        except Exception as error:
            raise BodyUnavailable(f"state query failed for {reference!r}: {error}") from error
        children = payload.get("children")
        if not isinstance(children, list) or not children:
            raise BodyUnavailable(f"empty or missing body for {reference!r}")
        lines: list[str] = []
        for child in children:
            name = child.get("name") if isinstance(child, dict) else None
            if not isinstance(name, str) or not name.strip():
                raise BodyUnavailable(f"unreadable body line in {reference!r}")
            lines.append(name)
        return tuple(lines)
