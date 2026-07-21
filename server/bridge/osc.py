"""grandMA3 OSC bridge — UDP command send + feedback receive (``/copilot/*`` namespace).

Implements REQ-MVP-001 (send gate-approved command lines as OSC messages to
``/copilot/cmd`` over UDP) and REQ-MVP-002 (deliver received ``/copilot/feedback``
messages to the result-confirmation path).

Send-surface contract (REQ-MVP-029 — single chokepoint, forward-looking):
    This module is the ONLY OSC/UDP send surface in the server. Once the safety
    gate lands (``server.safety``, milestone M4), the gate must be the sole
    production caller of :meth:`OscBridge.send_command`; no other production
    module may import this module to send. An import-boundary architecture test
    (AC-MVP-019) enforces this at M4/M6. Dev/test surfaces (``server.tools``,
    ``server.tests``) are exempt and must be explicitly whitelisted by that test.

Feedback-path honesty (REQ-MVP-002, forward: REQ-MVP-032):
    UDP is lossy. This bridge only DELIVERS feedback that actually arrives; it
    performs no timeout tracking and no "execution unconfirmed" classification —
    that is safety-gate scope (M4). Consumers attach via :class:`FeedbackConsumer`.

Receive addresses (M2): the console-side Lua responder replies on TWO addresses
    of the ``/copilot/*`` namespace (plan.md §A-5) — ``/copilot/feedback``
    (execution results, REQ-MVP-004) and ``/copilot/state`` (object-tree
    snapshots, REQ-MVP-003). Both are delivered through the same
    :class:`FeedbackConsumer` attach point; consumers discriminate by
    :attr:`FeedbackMessage.address`.
"""

from __future__ import annotations

import errno
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

# Own OSC namespace (2026-07-15 decision) — deliberately boardop-incompatible.
CMD_ADDRESS = "/copilot/cmd"
FEEDBACK_ADDRESS = "/copilot/feedback"
STATE_ADDRESS = "/copilot/state"

_SERVER_SHUTDOWN_TIMEOUT = 5.0

# Receive-port rebind recovery (REQ-DEPLOY-032 / AC-DEPLOY-023): a bounded number
# of SAME-port bind attempts with a brief backoff. Small defaults keep an
# unrecoverable failure fast (attempts x delay) — the console sends to a fixed
# port, so recovery is always same-port; drifting to another port is forbidden.
_DEFAULT_BIND_ATTEMPTS = 3
_DEFAULT_BIND_RETRY_DELAY = 0.05


# @MX:NOTE: [AUTO] SO_REUSEADDR receive server — allow_reuse_address=True makes
#   socketserver set SO_REUSEADDR before bind, so a receive port left held by an
#   abnormally-exited prior instance can be reclaimed on restart (REQ-DEPLOY-032).
#   Deliberately NOT SO_REUSEPORT: two live listeners on the port are never wanted.
class _ReuseAddrOSCUDPServer(ThreadingOSCUDPServer):
    """Feedback receive server that reuses the address (SO_REUSEADDR) on bind."""

    allow_reuse_address = True


class ReceivePortInUseError(RuntimeError):
    """The OSC feedback receive port is still held after same-port rebind retries.

    Carries human-readable reconfiguration ``guidance`` (mirroring
    :class:`server.web.launcher.PortInUseError`) — the launcher surfaces this and
    exits rather than silently drifting to a different port (REQ-DEPLOY-032 /
    REQ-DEPLOY-026). Bridge-local (not the launcher's ``PortInUseError``) so the
    leaf OSC module keeps no upward dependency on ``server.web``.
    """

    def __init__(self, host: str, port: int, label: str = "OSC feedback receive") -> None:
        self.host = host
        self.port = port
        self.label = label
        self.guidance = (
            f"OSC 수신 포트 {port}({label}, {host})가 동일-포트 재바인드 재시도 후에도 "
            f"여전히 사용 중입니다. 비정상 종료한 이전 인스턴스가 포트를 점유 중일 수 있습니다 — "
            f"해당 프로세스를 종료하거나 설정(Settings)에서 수신 포트를 변경한 뒤 다시 시작하세요. "
            f"(OSC receive port {port} for '{label}' is still in use after same-port "
            f"rebind retries — free the process holding it or change the receive port "
            f"in Settings, then restart. No automatic port fallback.)"
        )
        # The GUIDANCE is the message. Handing super() a different, English-only
        # sentence made the bilingual operator text unreachable in every surface
        # that renders the exception (traceback, log line, str()) — the useful
        # half existed but nothing could ever show it.
        super().__init__(self.guidance)


@dataclass(frozen=True)
class BridgeConfig:
    """Bridge endpoints. Defaults target a local grandMA3 onPC instance.

    ``send_port`` must match the OSC *input* port configured in onPC;
    ``receive_port`` is where this server listens for console feedback
    (``0`` binds an ephemeral port — useful for tests).
    """

    send_host: str = "127.0.0.1"
    send_port: int = 8000
    receive_host: str = "127.0.0.1"
    receive_port: int = 9000


@dataclass(frozen=True)
class FeedbackMessage:
    """One OSC feedback message as received from the console."""

    address: str
    args: tuple


# @MX:NOTE: [AUTO] result-confirmation attach point — the M3 tool-runner and M4 safety
#   gate consume console feedback exclusively through this protocol (REQ-MVP-002)
class FeedbackConsumer(Protocol):
    """Result-confirmation path attach point (used by M3 tool-runner / M4 gate)."""

    def deliver(self, message: FeedbackMessage) -> None:
        """Accept one received feedback message."""


class QueueFeedbackConsumer:
    """Default consumer: thread-safe FIFO queue of received feedback messages."""

    def __init__(self) -> None:
        self._messages: queue.Queue[FeedbackMessage] = queue.Queue()

    def deliver(self, message: FeedbackMessage) -> None:
        self._messages.put(message)

    def get(self, timeout: float | None = None) -> FeedbackMessage:
        """Return the next feedback message; raises ``queue.Empty`` on timeout."""
        return self._messages.get(timeout=timeout)


class OscBridge:
    """Sends command lines to the console and receives feedback from it.

    Sending needs no lifecycle (:meth:`send_command` works immediately).
    Receiving requires :meth:`start` / :meth:`stop`, or use the bridge as a
    context manager.
    """

    def __init__(
        self,
        config: BridgeConfig | None = None,
        consumer: FeedbackConsumer | None = None,
        *,
        bind_attempts: int = _DEFAULT_BIND_ATTEMPTS,
        bind_retry_delay: float = _DEFAULT_BIND_RETRY_DELAY,
        sleeper: Callable[[float], object] = time.sleep,
    ) -> None:
        self._config = config or BridgeConfig()
        self._consumer: FeedbackConsumer = consumer or QueueFeedbackConsumer()
        self._client = SimpleUDPClient(self._config.send_host, self._config.send_port)
        self._server: ThreadingOSCUDPServer | None = None
        self._server_thread: threading.Thread | None = None
        # Same-port rebind recovery knobs (injectable so tests stay fast).
        self._bind_attempts = max(1, bind_attempts)
        self._bind_retry_delay = bind_retry_delay
        self._sleep = sleeper
        # M6c backlog (sender-origin authentication): messages dropped
        # because their UDP source address did not match the trusted
        # console origin. Observable counter, not a full logging subsystem —
        # this module has no audit-log wiring (see _on_feedback).
        self.rejected_origin_count: int = 0

    @property
    def config(self) -> BridgeConfig:
        return self._config

    @property
    def consumer(self) -> FeedbackConsumer:
        return self._consumer

    @property
    def receive_port(self) -> int:
        """Actual bound receive port while running; configured port otherwise."""
        if self._server is not None:
            return self._server.socket.getsockname()[1]
        return self._config.receive_port

    # -- send path (REQ-MVP-001) --------------------------------------------

    # @MX:ANCHOR: [AUTO] single OSC send surface — the M4 safety gate must be the only
    #   production caller (REQ-MVP-029 single-chokepoint invariant)
    # @MX:REASON: the AC-MVP-019 import-boundary architecture test (M4/M6) pins this
    #   contract; widening the send surface silently re-opens the gate-bypass path
    def send_command(self, command: str) -> None:
        """Send one MA3 command line as a UDP OSC message to ``/copilot/cmd``."""
        if not command or not command.strip():
            raise ValueError("command line must be a non-empty string")
        self._client.send_message(CMD_ADDRESS, command)

    # -- receive path (REQ-MVP-002) ------------------------------------------

    def start(self) -> None:
        """Start the background feedback receiver. No-op if already running.

        Binds the receive socket with SO_REUSEADDR and a bounded SAME-port retry
        (REQ-DEPLOY-032): a port left held by an abnormally-exited prior instance
        is reclaimed on restart. On exhausted retries a :class:`ReceivePortInUseError`
        (human-friendly reconfiguration guidance) is raised instead of a raw
        ``OSError`` crash — and the port is NEVER silently drifted (REQ-DEPLOY-026).
        """
        if self._server is not None:
            return
        dispatcher = Dispatcher()
        dispatcher.map(FEEDBACK_ADDRESS, self._on_feedback, needs_reply_address=True)
        dispatcher.map(STATE_ADDRESS, self._on_feedback, needs_reply_address=True)
        self._server = self._bind_receiver(dispatcher)
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name="osc-bridge-feedback-receiver",
            daemon=True,
        )
        self._server_thread.start()

    # @MX:NOTE: [AUTO] same-port rebind carve-out (REQ-DEPLOY-032 / REQ-DEPLOY-026):
    #   only EADDRINUSE is retried, and ALWAYS against the SAME configured
    #   receive_port — the console sends to a fixed port, so drifting to any other
    #   port is forbidden. A non-EADDRINUSE OSError surfaces unchanged.
    def _bind_receiver(self, dispatcher: Dispatcher) -> _ReuseAddrOSCUDPServer:
        host = self._config.receive_host
        port = self._config.receive_port
        last_error: OSError | None = None
        for attempt in range(self._bind_attempts):
            try:
                return _ReuseAddrOSCUDPServer((host, port), dispatcher)
            except OSError as error:
                if error.errno != errno.EADDRINUSE:
                    raise  # not a port-occupancy failure — surface as-is
                last_error = error
                if attempt + 1 < self._bind_attempts:
                    self._sleep(self._bind_retry_delay)
        raise ReceivePortInUseError(host, port) from last_error

    def stop(self) -> None:
        """Stop the feedback receiver and release the socket. No-op if stopped."""
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._server_thread is not None:
            self._server_thread.join(timeout=_SERVER_SHUTDOWN_TIMEOUT)
        self._server = None
        self._server_thread = None

    def _on_feedback(self, client_address: tuple[str, int], address: str, *args) -> None:
        # M6c backlog (sender-origin authentication): previously registered
        # with no sender-address check — any host that could reach this UDP
        # port could inject spoofed feedback/state messages (fake execution
        # confirmations, fake state snapshots) that the safety gate's
        # result-confirmation and state-query paths would treat as genuine
        # console replies. Trust origin reuses BridgeConfig.send_host — the
        # console we send commands TO is the same console we expect
        # feedback FROM.
        #
        # ASSUMPTION (onPC-unverified, pending M6b-2 live calibration): a
        # real onPC deployment could legitimately send feedback from a
        # different local interface than send_host (e.g. multi-homed
        # console host); if that surfaces in live testing, this check needs
        # a configurable trusted-origin allowlist instead of the single
        # send_host value.
        if client_address[0] != self._config.send_host:
            self.rejected_origin_count += 1
            return
        self._consumer.deliver(FeedbackMessage(address=address, args=args))

    def __enter__(self) -> OscBridge:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
