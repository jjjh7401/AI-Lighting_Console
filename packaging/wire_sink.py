"""Layer ② — wire-level OSC packet sink + audit reconciliation (M7.3, AC-DEPLOY-027).

A static scan proves what the SOURCE says; this proves what the WIRE does. The
sink stands in for the console's OSC input port: it binds the port the app is
actually configured to send to, records every datagram that arrives, and
reconciles the capture 1:1 against the safety gate's audit ``executed`` log.

Two vacuous-pass hazards this closes (both were audit findings):

* **D3 — wrong port.** Binding the hardcoded default (8000) while the app sends
  to a user-configured port (``send_port`` is user-settable per REQ-DEPLOY-005)
  captures nothing, and "no unenumerated sends observed" then passes for the
  wrong reason. The caller MUST bind the port resolved from EFFECTIVE settings.
* **Empty capture.** "0 unaudited senders" is meaningless when 0 datagrams were
  seen at all. :func:`reconcile` therefore requires a POSITIVE OBSERVATION —
  at least one datagram captured AND matched to an audit entry — before it
  reports ``ok``.

Reconciliation direction (deliberately asymmetric):

* **observed but NOT audited => VIOLATION.** That is exactly the Rust-sidecar /
  updater raw-UDP bypass the Python guards cannot see.
* **audited but NOT observed => fine.** UDP is lossy, and a gate path can audit
  an ``executed`` event whose send failed validation before reaching the wire.
  Neither is a bypass.

Known accounting caveat (recorded, not silently absorbed): the file+Import
plugin-deploy path (``ConsoleLink._deploy_via_file_import``) issues several
console round-trips under ONE gate-audited ``kind="deploy"`` event, so a capture
that spans a plugin deployment has more datagrams than audit entries. Callers
that exercise deploys must account for it explicitly; the reconciliation here
stays strict rather than papering over the gap.

Pure stdlib — runs inside the pytest suite and the packaged E2E host alike.
"""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass

_PLUGIN_CALL_PREFIX = 'Plugin "CopilotResponder" "'
_UNPARSEABLE = "?"

# Default settle window: how long to wait for in-flight loopback datagrams
# before reading the capture. Loopback delivery is immediate; this only guards
# against the send/return-to-caller race.
DEFAULT_SETTLE_SECONDS = 0.15


@dataclass(frozen=True)
class ObservedDatagram:
    """One datagram seen on the console input port."""

    raw: bytes
    source: tuple[str, int]
    address: str  # OSC address pattern, or "" when unparseable
    payload: str  # first OSC string argument, or the raw repr when unparseable
    verb: str  # responder verb (exec/ping/state/deploy) or "?" when unrecognised
    subject: str  # command line / object path / plugin name / "ping"

    @property
    def key(self) -> tuple[str, str]:
        return (self.verb, self.subject)


@dataclass(frozen=True)
class ReconcileResult:
    """Outcome of matching a wire capture against the gate audit log."""

    observed_count: int
    audited_count: int
    matched: int
    unaudited: tuple[ObservedDatagram, ...]
    positive_observation: bool
    detail: str

    @property
    def ok(self) -> bool:
        return not self.unaudited and self.positive_observation


# ------------------------------------------------------------------ OSC decoding


def _read_padded_string(buf: bytes, offset: int) -> tuple[str, int]:
    end = buf.index(b"\x00", offset)
    text = buf[offset:end].decode("utf-8", "replace")
    return text, offset + (((end - offset) // 4) + 1) * 4


def parse_datagram(raw: bytes, source: tuple[str, int]) -> ObservedDatagram:
    """Decode one OSC datagram into an :class:`ObservedDatagram`.

    Anything that is not a well-formed OSC message with a single string
    argument decodes to ``verb="?"`` — which reconciles against nothing and
    therefore FAILS CLOSED, exactly as a rogue raw-UDP packet should.
    """
    address = ""
    payload = ""
    try:
        address, offset = _read_padded_string(raw, 0)
        typetags, offset = _read_padded_string(raw, offset)
        if typetags.startswith(",") and "s" in typetags:
            payload, _ = _read_padded_string(raw, offset)
    except (ValueError, IndexError):
        address = ""
        payload = ""

    if not payload:
        payload = repr(raw)

    verb, subject = _UNPARSEABLE, payload
    if address == "/copilot/cmd" and payload.startswith(_PLUGIN_CALL_PREFIX):
        request = payload[len(_PLUGIN_CALL_PREFIX) :].rstrip('"')
        head, _, rest = request.partition(" ")
        if head in {"exec", "ping", "state", "deploy"}:
            verb = head
            _request_id, _, remainder = rest.partition(" ")
            subject = remainder if head != "ping" else "ping"
    return ObservedDatagram(
        raw=raw,
        source=source,
        address=address,
        payload=payload,
        verb=verb,
        subject=subject,
    )


def audit_key(event: dict) -> tuple[str, str]:
    """The wire key a gate ``executed`` audit event predicts.

    Every ``executed`` entry maps to exactly one ``send_command`` call:
    ``kind="heartbeat"`` -> a ``ping`` request, ``kind="state_query"`` -> a
    ``state`` request for that object path, ``kind="deploy"`` -> a ``deploy``
    request for that plugin name, everything else (``command`` / ``backup``)
    -> an ``exec`` request carrying that command line.
    """
    kind = event.get("kind", "command")
    command = str(event.get("command", ""))
    if kind == "heartbeat":
        return ("ping", "ping")
    if kind == "state_query":
        return ("state", command)
    if kind == "deploy":
        return ("deploy", command)
    return ("exec", command)


# @MX:ANCHOR: [AUTO] fail-closed wire<->audit reconciliation — an observed
#   datagram with no matching gate audit entry is an unenumerated sender, and an
#   EMPTY capture never satisfies the criterion (positive-observation required)
# @MX:REASON: AC-DEPLOY-027 Layer ② ③/④; without the positive-observation gate a
#   sink bound to the wrong port (audit defect D3) or a silent app would report
#   "0 unenumerated sends" while observing nothing at all
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
def reconcile(
    observed,
    audit_events,
    *,
    require_positive_observation: bool = True,
) -> ReconcileResult:
    """Match a wire capture 1:1 against gate ``executed`` audit events."""
    observed = tuple(observed)
    executed = [e for e in audit_events if e.get("event") == "executed"]

    remaining: dict[tuple[str, str], int] = {}
    for event in executed:
        key = audit_key(event)
        remaining[key] = remaining.get(key, 0) + 1

    unaudited: list[ObservedDatagram] = []
    matched = 0
    for datagram in observed:
        key = datagram.key
        if remaining.get(key, 0) > 0:
            remaining[key] -= 1
            matched += 1
        else:
            unaudited.append(datagram)

    positive = matched >= 1 if require_positive_observation else True
    if unaudited:
        detail = (
            f"{len(unaudited)} datagram(s) reached the console port without a gate "
            f"audit entry — unenumerated sender(s): "
            f"{[d.payload[:80] for d in unaudited]}"
        )
    elif not positive:
        detail = (
            "no legitimate gate send was observed on the wire — an empty capture "
            "does NOT satisfy 'no unenumerated sends' (AC-DEPLOY-027 Layer ② ③)"
        )
    else:
        detail = f"{matched} datagram(s) reconciled 1:1 with the gate audit log"
    return ReconcileResult(
        observed_count=len(observed),
        audited_count=len(executed),
        matched=matched,
        unaudited=tuple(unaudited),
        positive_observation=positive,
        detail=detail,
    )


# ------------------------------------------------------------------ the sink


class WirePacketSink:
    """UDP sink standing in for the console's OSC input port.

    Bind BEFORE the app starts sending, and bind the port resolved from
    EFFECTIVE settings — not the 8000 default (audit defect D3).
    """

    def __init__(self, *, host: str = "127.0.0.1", port: int = 0) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((host, port))
        self._socket.settimeout(0.2)
        self.host, self.port = self._socket.getsockname()
        self._datagrams: list[ObservedDatagram] = []
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(
            target=self._serve, name="m73-wire-packet-sink", daemon=True
        )
        self._thread.start()

    def _serve(self) -> None:
        while self._running:
            try:
                raw, source = self._socket.recvfrom(65535)
            except (TimeoutError, OSError):
                continue
            with self._lock:
                self._datagrams.append(parse_datagram(raw, source))

    @property
    def datagrams(self) -> tuple[ObservedDatagram, ...]:
        with self._lock:
            return tuple(self._datagrams)

    def drain(self, settle: float = DEFAULT_SETTLE_SECONDS) -> tuple[ObservedDatagram, ...]:
        """Wait ``settle`` seconds for in-flight datagrams, then snapshot."""
        if settle:
            time.sleep(settle)
        return self.datagrams

    def clear(self) -> None:
        with self._lock:
            self._datagrams.clear()

    def stop(self) -> None:
        self._running = False
        self._thread.join(timeout=2.0)
        self._socket.close()

    def __enter__(self) -> WirePacketSink:
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
