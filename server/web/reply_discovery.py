"""Reply-port discovery — find where the console is ACTUALLY replying.

The root defect. A grandMA3 OSC entry has ONE port used for BOTH directions
(read off the console's In&Out -> OSC table: Lock / No / Name / Tags /
Destination IP / Mode / **Port** / Prefix / Data Pool / Page / Fader — one Port
column, no separate destination port). So the app sends commands to the
console's entry-1 port, and the responder's replies leave through whichever
entry points at this machine, arriving on THAT entry's port. The app's
``receive_port`` setting and the console's entry Port are therefore two numbers
kept in two different places, by hand, with no feedback when they drift. When
they drift the link simply goes quiet, and ``console_offline`` sends the
operator to inspect the two subsystems that are already healthy.

This module supplies the missing feedback. While the link is down it listens on
a small, explicit set of candidate ports, has the EXISTING gate send path emit
one ping, and reports which port the reply landed on.

Four boundaries, each load-bearing:

* **Report, never adopt (REQ-DEPLOY-026).** The requirement forbids the app
  quietly changing its effective port, because the operator aligns the console
  to a specific number. Silently adopting a discovered port is that same class
  of invisible divergence with the sign flipped: the settings screen would say
  9000 while the runtime listened on 9005 — exactly the UI-vs-runtime split
  M7.4b had to fix — and a genuinely misconfigured console would be masked
  instead of corrected. So the verdict is a DIAGNOSIS, carried beside the health
  state like :mod:`server.web.console_probe`'s verdict. It changes no setting,
  no bind and no health state; the operator applies the fix, in either place.
  :class:`ReplyProbeResult` deliberately has no method that could apply itself.
* **One send, and it is the gate's.** ``send_ping`` is injected — in production
  it is ``SafetyGate.heartbeat``, already audited and already the single
  sanctioned OSC send surface. This module opens no socket that transmits, so
  AC-MVP-019 (single gate) and AC-DEPLOY-027 (every send enumerated) are
  untouched: the wire sees one heartbeat that would have been sent anyway.
* **Never bind the console's INPUT port.** Measured on darwin: a SPECIFIC bind
  wins datagram delivery over a WILDCARD holder, and onPC holds ``*:8000``. A
  listener on the console's input port would therefore swallow the app's own
  outbound commands. The console port is excluded from the candidate set, which
  also means a console configured to use ONE entry for both directions is
  outside what discovery can safely probe.
* **Only while the link is down.** The caller gates on
  ``console_offline`` + a listening console input, and
  :class:`ReplyPortDiagnostic` adds a cooldown and runs off the caller's thread.
  A working configuration never pays for any of this.
"""

from __future__ import annotations

import select
import socket
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

# Nearest-first neighbourhood of the configured receive port. +/-5 is not a
# round number: the drift observed live was 9000 -> 9005, so a +/-1 window would
# have missed the case this exists for. Ten entries is a bounded, enumerable
# candidate list — deliberately not a scan.
DEFAULT_CANDIDATE_OFFSETS: tuple[int, ...] = (1, -1, 2, -2, 3, -3, 4, -4, 5, -5)

# The responder replies on /copilot/feedback and /copilot/state. An OSC packet
# begins with its address as a NUL-padded ASCII string, so the namespace prefix
# is readable without decoding the packet — which keeps this module off
# ``pythonosc`` and therefore outside the OSC surface entirely.
RESPONDER_ADDRESS_PREFIX = b"/copilot/"

_MIN_PORT = 1
_MAX_PORT = 65535
_READ_CHUNK = 4096
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 3.0
# How long a verdict stays fresh. Discovery costs one heartbeat and a handful of
# short-lived sockets; at this interval a wrong-port console is named within a
# few seconds of going quiet, and a genuinely dead console re-probes rarely.
DEFAULT_MIN_INTERVAL_SECONDS = 30.0


@dataclass(frozen=True)
class ReplyPortMismatch:
    """The two numbers the operator has to reconcile, and nothing else."""

    configured: int  # what the app listens on
    observed: int  # where a console reply actually landed


@dataclass(frozen=True)
class ReplyProbeResult:
    """One discovery run, including what it could NOT look at.

    ``listened`` and ``unbindable`` are reported rather than folded away: a
    candidate this run never managed to listen on is a hole in the answer, and
    "found nothing" must stay distinguishable from "looked everywhere".
    """

    configured_port: int
    candidates: tuple[int, ...]
    listened: tuple[int, ...]
    unbindable: tuple[int, ...]
    observed_port: int | None
    send_error: str | None = None

    @property
    def mismatch(self) -> ReplyPortMismatch | None:
        """The mismatch to report, or None when nothing was observed."""
        if self.observed_port is None or self.observed_port == self.configured_port:
            return None
        return ReplyPortMismatch(configured=self.configured_port, observed=self.observed_port)


def candidate_ports(
    *,
    receive_port: int,
    console_port: int,
    offsets: Iterable[int] = DEFAULT_CANDIDATE_OFFSETS,
) -> tuple[int, ...]:
    """The explicit, bounded set of ports to listen on, nearest-first.

    Excluded, each for its own reason:

    * ``receive_port`` — the entry condition, not a hypothesis. Discovery only
      runs because that port produced no reply, and our own receiver still holds
      it (a second bind on the same specific address fails regardless).
    * ``console_port`` — binding it would HIJACK the app's own command stream,
      because a specific bind outranks the console's wildcard hold for delivery.
    * anything outside ``[1, 65535]`` — dropped, never clamped: a clamped
      neighbour is a port nobody asked about.
    """
    seen: set[int] = {receive_port, console_port}
    candidates: list[int] = []
    for offset in offsets:
        port = receive_port + offset
        if port < _MIN_PORT or port > _MAX_PORT or port in seen:
            continue
        seen.add(port)
        candidates.append(port)
    return tuple(candidates)


def _looks_like_responder_reply(datagram: bytes) -> bool:
    """True when the datagram is in the copilot OSC namespace.

    Unrelated local traffic on a neighbour port must not be read as "the console
    replies here" — that would tell the operator to change a setting that is
    right. This is a namespace check, not a correlation: see the module note on
    what discovery cannot prove.
    """
    return datagram.startswith(RESPONDER_ADDRESS_PREFIX)


def _bind_candidate(host: str, port: int) -> socket.socket | None:
    """Listen on one candidate the way the real receiver listens, or give up.

    SO_REUSEADDR mirrors :class:`server.bridge.osc._ReuseAddrOSCUDPServer`: it is
    what lets this bind coexist with the console's wildcard hold on the same
    port number, and (measured on darwin) the resulting SPECIFIC binding is the
    one the datagram is delivered to.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
    except OSError:
        sock.close()
        return None
    sock.setblocking(False)
    return sock


# @MX:ANCHOR: [AUTO] reply-port discovery — the only place the app listens
#   outside its configured receive port. Diagnosis only: it returns numbers, it
#   never binds the runtime receiver anywhere and never writes a setting.
# @MX:REASON: two failure shapes are one mistake away and both are silent. (1) A
#   candidate set that includes the console's INPUT port hijacks the app's own
#   outbound commands, because a specific bind beats the console's wildcard hold
#   for delivery — the app would then break the very link it is diagnosing. (2)
#   Adopting the discovered port instead of reporting it is the REQ-DEPLOY-026
#   silent drift with the sign flipped: settings and runtime disagree with
#   nothing on screen to say so.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-026
def discover_reply_port(
    *,
    send_ping: Callable[[], object],
    receive_host: str,
    receive_port: int,
    console_port: int,
    timeout: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    candidates: Sequence[int] | None = None,
    offsets: Iterable[int] = DEFAULT_CANDIDATE_OFFSETS,
) -> ReplyProbeResult:
    """Listen on the candidate set, ping once through the gate, report what landed.

    Binds BEFORE pinging — a reply that beats the bind is a false negative on a
    console that is in fact reachable. ``send_ping`` failures are captured, not
    raised: a diagnosis must never be able to break the surface it decorates.
    Every socket is released before returning; a leaked listener would squat a
    port the operator may then try to configure.
    """
    ports = (
        tuple(candidates)
        if candidates is not None
        else candidate_ports(receive_port=receive_port, console_port=console_port, offsets=offsets)
    )
    listeners: dict[int, socket.socket] = {}
    unbindable: list[int] = []
    for port in ports:
        sock = _bind_candidate(receive_host, port)
        if sock is None:
            unbindable.append(port)
        else:
            listeners[port] = sock

    send_error: str | None = None
    observed: int | None = None
    try:
        try:
            send_ping()
        except Exception as error:  # the link being down is the normal case here
            send_error = f"{type(error).__name__}: {error}"
        if listeners:
            observed = _await_reply(listeners, timeout)
    finally:
        for sock in listeners.values():
            sock.close()

    return ReplyProbeResult(
        configured_port=receive_port,
        candidates=ports,
        listened=tuple(listeners),
        unbindable=tuple(unbindable),
        observed_port=observed,
        send_error=send_error,
    )


def _await_reply(listeners: dict[int, socket.socket], timeout: float) -> int | None:
    """Return the port a copilot-namespace datagram arrived on, within ``timeout``.

    Foreign datagrams are drained and ignored rather than ending the wait: one
    unrelated packet must not blind the probe to the real reply behind it.
    """
    by_socket = {sock: port for port, sock in listeners.items()}
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        try:
            ready, _, _ = select.select(list(by_socket), [], [], remaining)
        except OSError:
            return None
        for sock in ready:
            try:
                datagram, _origin = sock.recvfrom(_READ_CHUNK)
            except OSError:
                continue
            if _looks_like_responder_reply(datagram):
                return by_socket[sock]


def _spawn_daemon(target: Callable[[], object]) -> None:
    threading.Thread(target=target, name="reply-port-discovery", daemon=True).start()


# @MX:ANCHOR: [AUTO] the status-path gate for discovery — every caller reaches
#   discovery through this, and it is what keeps a socket-and-ping diagnosis off
#   the asyncio event loop.
# @MX:REASON: ``status_snapshot`` is built ON the event loop (app.py builds the
#   frame inline, and the heartbeat loop's notify() is not threaded), so a
#   verdict() that waited for a run would stall the whole server for the ping
#   timeout. The cooldown is the other half: without it a diagnosis costing one
#   heartbeat plus ten sockets would run on every status frame.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-018
class ReplyPortDiagnostic:
    """A cached, off-thread reply-port verdict for the status surface.

    :meth:`verdict` never blocks and never raises: it answers from cache and, if
    that cache is stale, schedules a run whose result the NEXT status frame
    carries. Because the heartbeat loop only pushes status on a health CHANGE,
    a completed run fires ``on_complete`` — otherwise the diagnosis would be
    computed correctly and never reach the operator.
    """

    def __init__(
        self,
        *,
        discover: Callable[[], ReplyProbeResult],
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        spawn: Callable[[Callable[[], object]], object] = _spawn_daemon,
        on_complete: Callable[[], object] | None = None,
    ) -> None:
        self._discover = discover
        self._min_interval = min_interval_seconds
        self._clock = clock
        self._spawn = spawn
        self._on_complete = on_complete
        self._lock = threading.Lock()
        self._running = False
        self._checked_at: float | None = None
        self._mismatch: ReplyPortMismatch | None = None

    def set_on_complete(self, callback: Callable[[], object] | None) -> None:
        """Attach the status fan-out (wired after the app deps exist)."""
        self._on_complete = callback

    def verdict(self) -> ReplyPortMismatch | None:
        """The cached mismatch, scheduling a refresh when stale. Never blocks."""
        with self._lock:
            if self._running:
                return self._mismatch
            now = self._clock()
            fresh = self._checked_at is not None and now - self._checked_at < self._min_interval
            if fresh:
                return self._mismatch
            self._running = True
            cached = self._mismatch
        self._spawn(self._run)
        return cached

    def _run(self) -> None:
        mismatch: ReplyPortMismatch | None = None
        try:
            mismatch = self._discover().mismatch
        except Exception:
            # An unusable diagnosis is "no verdict", never an error the status
            # surface has to carry.
            mismatch = None
        with self._lock:
            changed = mismatch != self._mismatch
            self._mismatch = mismatch
            self._checked_at = self._clock()
            self._running = False
            callback = self._on_complete
        if changed and callback is not None:
            callback()


def make_reply_port_diagnostic(
    *,
    send_ping: Callable[[], object],
    receive_host: str,
    receive_port: int,
    console_port: int,
    timeout: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
) -> ReplyPortDiagnostic:
    """Bind the configured endpoints into a ready-to-inject diagnostic."""

    def _discover() -> ReplyProbeResult:
        return discover_reply_port(
            send_ping=send_ping,
            receive_host=receive_host,
            receive_port=receive_port,
            console_port=console_port,
            timeout=timeout,
        )

    return ReplyPortDiagnostic(discover=_discover, min_interval_seconds=min_interval_seconds)
