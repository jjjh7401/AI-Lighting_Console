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
from dataclasses import dataclass, replace
from pathlib import Path
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
from server.deploy.pack import build_plugin_xml, import_slug
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


# @MX:ANCHOR: [AUTO] per-send deploy audit contract (M7.5) — every console
#   round-trip made inside deploy_plugin's file+Import path MUST append one
#   DeploySend record; the gate fans these out into individual audit entries
# @MX:REASON: AC-DEPLOY-027 Layer ② reconciles the wire 1:1 against the audit
#   log; a round-trip that skips its record becomes a false "unenumerated
#   sender" flag (fan_in >= 3: gate audit fan-out, wire-sink reconcile tests,
#   responder import-gate accounting tests)
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
@dataclass(frozen=True)
class DeploySend:
    """One console round-trip made INSIDE a deploy (per-send granularity).

    The console link never writes audit entries itself — the AuditLog stays
    gate-owned. It only RETURNS what it sent; ``SafetyGate.deploy_plugin_source``
    turns each record into its own ``executed`` audit event.
    """

    kind: str  # audit kind taxonomy: "state_query" | "command"
    command: str  # the state path or exec command line (the wire subject)
    ok: bool
    detail: str = ""
    outcome: str = ""  # "ok" | "failed" | "unconfirmed" | "error"


@dataclass(frozen=True)
class ExecOutcome:
    """One command execution attempt: ok / failed / unconfirmed (REQ-MVP-032)."""

    status: str  # "ok" | "failed" | "unconfirmed"
    detail: str = ""
    # Sub-sends performed inside a deploy (file+Import path). Empty for plain
    # executions and for the single-send OSC deploy verb, whose one wire send
    # is already represented 1:1 by the gate's parent kind="deploy" entry.
    sends: tuple[DeploySend, ...] = ()


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
        import_dir: str | Path | None = None,
    ) -> None:
        self._send = send
        self._timeouts = timeouts or LinkTimeouts()
        self._monitor = monitor
        self._id_prefix = id_prefix
        # When set (co-located server + console), deploy_plugin uses the working
        # file+Import path (write a native Base64-embedded plugin XML to the
        # onPC plugins library folder, then `Import Plugin`). When None, it falls
        # back to the OSC `deploy` verb (kept for a remote console with no shared
        # filesystem; that verb is size-capped and content-setter-fragile on 2.4.2).
        self._import_dir = Path(import_dir).expanduser() if import_dir else None
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
        """Deploy one reviewed plugin so it is RUNNABLE on the console (M7).

        Uses file+Import when an ``import_dir`` is configured (co-located server
        + console — the working path on onPC 2.4.2), otherwise the OSC ``deploy``
        verb (remote fallback). Sends ONCE and never retries: like exec, a deploy
        timeout is UNCONFIRMED (send loss and reply loss are indistinguishable —
        REQ-MVP-032 discipline applies to deployments too).
        """
        if self._import_dir is not None:
            return self._deploy_via_file_import(name, lua_source)
        return self._deploy_via_osc_verb(name, lua_source)

    def _deploy_via_file_import(self, name: str, lua_source: str) -> ExecOutcome:
        """Write a native Base64-embedded plugin XML and ``Import Plugin`` it.

        The OSC ``deploy`` verb's embedded-content write does not run on 2.4.2
        (ASSUMPTION-6) and truncates past ~2 KB; the native inline-Base64 import
        format has neither limit (verified live: 9-fixture patch plugin ran).
        Idempotent: an existing plugin of the same Name is deleted first so a
        re-deploy updates in place instead of creating a duplicate.

        Per-send granularity (M7.5, AC-DEPLOY-027 Layer ②): every console
        round-trip made here is recorded as a :class:`DeploySend` on the
        returned outcome, so the gate can audit each wire send individually.
        """
        sends: list[DeploySend] = []
        outcome = self._run_file_import(name, lua_source, sends)
        return replace(outcome, sends=tuple(sends))

    def _deploy_query_state(self, path: str, sends: list[DeploySend]) -> dict:
        """One pool read inside a deploy — recorded even on failure/timeout
        (a lost reply is not a lost send; the query still hit the wire)."""
        try:
            payload = self.query_state(path)
        except StateQueryError as error:
            sends.append(
                DeploySend(
                    kind="state_query", command=path, ok=False, detail=str(error), outcome="error"
                )
            )
            raise
        sends.append(DeploySend(kind="state_query", command=path, ok=True, outcome="ok"))
        return payload

    def _deploy_execute(self, command: str, sends: list[DeploySend]) -> ExecOutcome:
        """One exec round-trip inside a deploy — recorded with its outcome."""
        outcome = self.execute(command)
        sends.append(
            DeploySend(
                kind="command",
                command=command,
                ok=outcome.status == "ok",
                detail=outcome.detail,
                outcome=outcome.status,
            )
        )
        return outcome

    def _run_file_import(
        self, name: str, lua_source: str, sends: list[DeploySend]
    ) -> ExecOutcome:
        try:
            xml = build_plugin_xml(name, lua_source)
        except ValueError as error:
            return ExecOutcome(status="failed", detail=str(error))
        slug = import_slug(name)
        target = self._import_dir / f"{slug}.xml"
        try:
            self._import_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(xml, encoding="utf-8")
        except OSError as error:
            return ExecOutcome(status="failed", detail=f"cannot write plugin file {target}: {error}")

        # One pool read: find an existing same-Name slot (idempotent redeploy)
        # AND the occupied slots (to pick a free one). A no-slot `Import Plugin`
        # is unreliable on 2.4.2 — an explicit free slot is required.
        existing_slot: int | None = None
        occupied: set[int] = set()
        unnumbered = 0
        try:
            pool = self._deploy_query_state("DataPool/Plugins", sends)
            for child in pool.get("children", []):
                if not isinstance(child, dict):
                    continue
                index = child.get("i")
                if isinstance(index, int):
                    occupied.add(index)
                else:
                    unnumbered += 1
                if child.get("name") == name:
                    existing_slot = index if isinstance(index, int) else None
        except StateQueryError:
            pass  # non-fatal — proceed with the slot-1 fallback below
        # A listed plugin whose real slot the responder could NOT establish
        # (it omits "i" rather than substituting a listing position —
        # PROTOCOL.md §4.2) makes the arithmetic below a guess: that plugin may
        # sit in exactly the slot picked as "free", and `Import Plugin <slot>`
        # would overwrite it. Refuse rather than gamble with the user's pool.
        if unnumbered:
            return ExecOutcome(
                status="failed",
                detail=(
                    f"cannot choose a free plugin slot: {unnumbered} plugin(s) in "
                    "DataPool/Plugins reported no pool slot (the console exposes no "
                    "usable child-index accessor), so importing could overwrite one"
                ),
            )
        if isinstance(existing_slot, int):
            self._deploy_execute(f"Delete Plugin {existing_slot}", sends)
            occupied.discard(existing_slot)
        slot = 1
        while slot in occupied:
            slot += 1

        # Import into the chosen free slot; single-quoted stem (exec rejects ").
        outcome = self._deploy_execute(f"Import Plugin {slot} '{slug}'", sends)
        if outcome.status != "ok":
            return ExecOutcome(
                status=outcome.status,
                detail=f"Import Plugin {slot} '{slug}' failed: {outcome.detail}",
            )
        # Confirm the plugin object now exists in the pool under its Name.
        try:
            pool = self._deploy_query_state("DataPool/Plugins", sends)
        except StateQueryError as error:
            return ExecOutcome(status="unconfirmed", detail=f"imported but pool unreadable: {error}")
        names = [c.get("name") for c in pool.get("children", []) if isinstance(c, dict)]
        if name in names:
            return ExecOutcome(status="ok", detail=f"imported plugin {name!r} via file+Import")
        return ExecOutcome(
            status="failed", detail=f"import did not create plugin {name!r} (pool: {names})"
        )

    def _deploy_via_osc_verb(self, name: str, lua_source: str) -> ExecOutcome:
        """Legacy OSC ``deploy`` verb (remote fallback; size-capped on 2.4.2)."""
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
