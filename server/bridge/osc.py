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
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Protocol

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

# Own OSC namespace (2026-07-15 decision) — deliberately boardop-incompatible.
CMD_ADDRESS = "/copilot/cmd"
FEEDBACK_ADDRESS = "/copilot/feedback"

_SERVER_SHUTDOWN_TIMEOUT = 5.0


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
    ) -> None:
        self._config = config or BridgeConfig()
        self._consumer: FeedbackConsumer = consumer or QueueFeedbackConsumer()
        self._client = SimpleUDPClient(self._config.send_host, self._config.send_port)
        self._server: ThreadingOSCUDPServer | None = None
        self._server_thread: threading.Thread | None = None

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
        """Start the background feedback receiver. No-op if already running."""
        if self._server is not None:
            return
        dispatcher = Dispatcher()
        dispatcher.map(FEEDBACK_ADDRESS, self._on_feedback)
        self._server = ThreadingOSCUDPServer(
            (self._config.receive_host, self._config.receive_port), dispatcher
        )
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name="osc-bridge-feedback-receiver",
            daemon=True,
        )
        self._server_thread.start()

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

    def _on_feedback(self, address: str, *args) -> None:
        self._consumer.deliver(FeedbackMessage(address=address, args=args))

    def __enter__(self) -> OscBridge:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
