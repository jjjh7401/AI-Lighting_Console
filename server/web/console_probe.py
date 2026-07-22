"""Console OSC-input reachability probe — the console_offline discriminator.

:class:`server.safety.monitor.HealthMonitor` separates ``console_offline`` from
``responder_degraded`` by OBSERVED INBOUND TRAFFIC. When the responder plugin is
the only thing that ever sends, a stopped responder produces zero inbound
traffic, so the monitor cannot tell "onPC is down" from "onPC is up but nothing
is sending" and correctly falls through to ``console_offline``. The state
machine is sound; its inputs are insufficient — and the operator is then sent to
inspect two healthy subsystems while the real cause goes unnamed.

This module supplies the missing input WITHOUT touching the state machine: a
BIND attempt on the console's OSC input port. On loopback,

    bind 127.0.0.1:<console_port> -> EADDRINUSE  => something IS listening
    bind 127.0.0.1:<console_port> -> success     => nothing is listening

reusing :func:`server.web.launcher.probe_port_available` with ``reuse_addr=False``
— the STRICT bind. That opt-out is load-bearing: the shared probe defaults to
modelling our own binder (SO_REUSEADDR), and with that option set a specific-
address bind succeeds right past a wildcard holder. onPC binds the wildcard
(measured live: ``UDP *:8000``), so the permissive bind would call a live console
input silent. Detection wants the strictest bind; the launcher preflight, which
asks a different question, deliberately makes the opposite choice.

Three deliberate boundaries:

* **Diagnosis only.** The verdict is carried on the ``status`` event beside the
  health state; it changes NO health state and NO gate decision.
* **Bind only, never send.** A datagram here would be an OSC send outside the
  single gate (AC-MVP-019) and outside the enumerated wire set (AC-DEPLOY-027).
  A bind transmits nothing.
* **Loopback only.** You cannot bind a remote console's port, so any host that
  is not an IPv4 loopback address yields ``undetermined`` and the UI keeps the
  existing message — the honest one when nothing can be determined.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable

from server.web.launcher import probe_port_available
from server.web.messages import (
    CONSOLE_INPUT_LISTENING,
    CONSOLE_INPUT_SILENT,
    CONSOLE_INPUT_UNDETERMINED,
)

_MIN_PORT = 1
_MAX_PORT = 65535

# The one non-numeric host resolved here. Everything else that is not an IP
# literal is left unresolved ON PURPOSE: a name lookup would put a potentially
# slow, network-dependent DNS call on the status path, and any name that is not
# this machine is a remote console we could not probe anyway. "localhost" is
# answered from the hosts file, and it is what an operator most often types.
_LOOPBACK_ALIASES = frozenset({"localhost"})


def _is_probeable_address(address: str) -> bool:
    """True for an IPv4 loopback literal — the only thing this probe can bind.

    IPv4 because :func:`~server.web.launcher.probe_port_available` binds
    ``AF_INET``; loopback because a bind probe is only meaningful against the
    local stack. A wildcard (``0.0.0.0`` / ``""``) is excluded: as a SEND target
    it names no console, so probing it would answer a different question.
    """
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return parsed.version == 4 and parsed.is_loopback


def probe_target(host: str) -> str | None:
    """The IPv4 loopback literal to bind for ``host``, or None if unprobeable.

    Returning None — rather than letting an unprobeable host reach the socket —
    is load-bearing. The underlying probe reports ANY bind failure as "port
    occupied", including an address-family mismatch, so handing it an IPv6 host
    would classify a genuinely FREE port as ``listening``: a confidently wrong
    cause, which is the exact failure class this module exists to remove.
    """
    if host in _LOOPBACK_ALIASES:
        try:
            infos = socket.getaddrinfo(host, None, family=socket.AF_INET, type=socket.SOCK_DGRAM)
        except OSError:
            return None
        for info in infos:
            address = str(info[4][0])
            if _is_probeable_address(address):
                return address
        return None
    return host if _is_probeable_address(host) else None


# @MX:ANCHOR: [AUTO] the console_offline cause discriminator — consumed by the
#   status surface (session.status_snapshot) and rendered by the UI guidance.
# @MX:REASON: a WRONG verdict here puts a confidently-wrong cause in front of the
#   operator, which is the exact defect this module exists to remove. The
#   three-value return is therefore load-bearing: "undetermined" MUST stay
#   distinguishable from "silent", or a remote console silently regains the
#   old wrong-cause message with new false confidence. Never widen this to a
#   bool, and never let it transmit — a datagram here is an ungated OSC send.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-018
def probe_console_input(
    host: str,
    port: int,
    *,
    probe: Callable[..., bool] = probe_port_available,
) -> str:
    """Classify the console's OSC input port as listening / silent / undetermined.

    Binds (never sends) ``host:port`` in the UDP port space — the OSC input is
    UDP, and TCP is a separate space that could never answer for it.
    """
    target = probe_target(host)
    if target is None:
        return CONSOLE_INPUT_UNDETERMINED
    if not _MIN_PORT <= port <= _MAX_PORT:
        return CONSOLE_INPUT_UNDETERMINED
    try:
        # ``reuse_addr=False`` is the whole detection. The shared probe defaults
        # to modelling OUR binder (SO_REUSEADDR — see launcher.probe_port_available),
        # and with that option a specific-address bind succeeds straight past a
        # WILDCARD holder. onPC binds the wildcard (measured: ``UDP *:8000``), so
        # the permissive bind would report a live console input as silent. The
        # strictest bind is the most sensitive detector, and detection — not our
        # own bindability — is the question here.
        free = probe(target, port, sock_type=socket.SOCK_DGRAM, reuse_addr=False)
    except OSError:
        # No socket / permission / resolution failure — an inability to look is
        # not evidence of either answer.
        return CONSOLE_INPUT_UNDETERMINED
    return CONSOLE_INPUT_SILENT if free else CONSOLE_INPUT_LISTENING


def make_console_input_probe(host: str, port: int) -> Callable[[], str]:
    """Bind the configured console endpoint into a zero-argument probe.

    The injected-callable seam: the status surface calls this and never learns
    what a socket is, so the probe stays trivially replaceable in tests and the
    health state machine keeps zero I/O.
    """

    def _probe() -> str:
        return probe_console_input(host, port)

    return _probe
