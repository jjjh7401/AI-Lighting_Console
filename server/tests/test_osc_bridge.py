"""Behavior tests for the OSC bridge (AC-MVP-011 — REQ-MVP-001, REQ-MVP-002).

Verified with a local loopback OSC server (no console required):
  1. A command handed to the bridge is sent as UDP OSC to ``/copilot/cmd``.
  2. A ``/copilot/feedback`` message sent to the bridge's receive port is
     delivered to the result-confirmation path (consumer callback / queue).

All waits are event/timeout-bounded (no sleeps); all ports are ephemeral (port 0).
"""

import queue
import socket
import threading

import pytest
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from server.bridge import osc as osc_module
from server.bridge.osc import (
    CMD_ADDRESS,
    FEEDBACK_ADDRESS,
    STATE_ADDRESS,
    BridgeConfig,
    FeedbackMessage,
    OscBridge,
    QueueFeedbackConsumer,
    ReceivePortInUseError,
)

RECEIVE_TIMEOUT = 5.0  # generous upper bound; loopback delivery is sub-millisecond
SILENCE_TIMEOUT = 0.3  # bounded wait used to assert the ABSENCE of a delivery


class LoopbackConsoleServer:
    """Test double for the grandMA3 OSC-in socket: captures every OSC message."""

    def __init__(self) -> None:
        self.messages: queue.Queue[tuple[str, tuple]] = queue.Queue()
        dispatcher = Dispatcher()
        dispatcher.set_default_handler(self._capture)
        self._server = ThreadingOSCUDPServer(("127.0.0.1", 0), dispatcher)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def _capture(self, address: str, *args) -> None:
        self.messages.put((address, args))

    @property
    def port(self) -> int:
        return self._server.socket.getsockname()[1]

    def __enter__(self) -> "LoopbackConsoleServer":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=RECEIVE_TIMEOUT)


class TestCommandSending:
    """REQ-MVP-001 — gate-approved command lines go out as UDP OSC to /copilot/cmd."""

    def test_command_is_sent_as_udp_osc_to_copilot_cmd_address(self) -> None:
        with LoopbackConsoleServer() as console:
            bridge = OscBridge(BridgeConfig(send_port=console.port))

            bridge.send_command('Store Sequence 1 Cue 1 "Intro"')

            address, args = console.messages.get(timeout=RECEIVE_TIMEOUT)
            assert address == CMD_ADDRESS
            assert args == ('Store Sequence 1 Cue 1 "Intro"',)

    def test_each_command_of_a_sequence_is_sent_as_its_own_osc_message(self) -> None:
        with LoopbackConsoleServer() as console:
            bridge = OscBridge(BridgeConfig(send_port=console.port))
            commands = ["ClearAll", "Group 1", 'Label Group 1 "Vocals"']

            for command in commands:
                bridge.send_command(command)

            received = [console.messages.get(timeout=RECEIVE_TIMEOUT) for _ in commands]
            assert received == [(CMD_ADDRESS, (command,)) for command in commands]

    def test_empty_command_is_rejected(self) -> None:
        bridge = OscBridge()
        with pytest.raises(ValueError):
            bridge.send_command("")

    def test_blank_command_is_rejected(self) -> None:
        bridge = OscBridge()
        with pytest.raises(ValueError):
            bridge.send_command("   ")


class TestFeedbackReceiving:
    """REQ-MVP-002 — /copilot/feedback messages reach the result-confirmation path."""

    def test_feedback_message_is_delivered_to_result_confirmation_path(self) -> None:
        consumer = QueueFeedbackConsumer()
        with OscBridge(BridgeConfig(receive_port=0), consumer=consumer) as bridge:
            client = SimpleUDPClient("127.0.0.1", bridge.receive_port)

            client.send_message(FEEDBACK_ADDRESS, ["ok", 1])

            message = consumer.get(timeout=RECEIVE_TIMEOUT)
            assert message == FeedbackMessage(address=FEEDBACK_ADDRESS, args=("ok", 1))

    def test_messages_to_other_osc_addresses_are_not_delivered(self) -> None:
        consumer = QueueFeedbackConsumer()
        with OscBridge(BridgeConfig(receive_port=0), consumer=consumer) as bridge:
            client = SimpleUDPClient("127.0.0.1", bridge.receive_port)

            client.send_message("/copilot/unknown", "ignored")
            client.send_message(FEEDBACK_ADDRESS, "expected")

            message = consumer.get(timeout=RECEIVE_TIMEOUT)
            assert message.args == ("expected",)
            with pytest.raises(queue.Empty):
                consumer.get(timeout=SILENCE_TIMEOUT)

    def test_custom_consumer_callback_receives_feedback(self) -> None:
        received: queue.Queue[FeedbackMessage] = queue.Queue()

        class RecordingConsumer:
            def deliver(self, message: FeedbackMessage) -> None:
                received.put(message)

        with OscBridge(BridgeConfig(receive_port=0), consumer=RecordingConsumer()) as bridge:
            SimpleUDPClient("127.0.0.1", bridge.receive_port).send_message(FEEDBACK_ADDRESS, 42)

            message = received.get(timeout=RECEIVE_TIMEOUT)
            assert message == FeedbackMessage(address=FEEDBACK_ADDRESS, args=(42,))

    def test_feedback_stops_being_delivered_after_stop(self) -> None:
        consumer = QueueFeedbackConsumer()
        bridge = OscBridge(BridgeConfig(receive_port=0), consumer=consumer)
        bridge.start()
        port = bridge.receive_port

        bridge.stop()

        SimpleUDPClient("127.0.0.1", port).send_message(FEEDBACK_ADDRESS, "late")
        with pytest.raises(queue.Empty):
            consumer.get(timeout=SILENCE_TIMEOUT)


class TestFeedbackOriginAuthentication:
    """M6c backlog: ``_on_feedback`` had no sender-origin check — any host
    that could reach the receive UDP port could inject spoofed
    feedback/state messages (fake execution confirmations, fake state
    snapshots). Trusted origin = ``BridgeConfig.send_host`` (the same
    console we send commands TO is the console we expect feedback FROM).
    """

    def test_feedback_from_the_trusted_console_host_is_delivered(self) -> None:
        consumer = QueueFeedbackConsumer()
        bridge = OscBridge(BridgeConfig(send_host="127.0.0.1", receive_port=0), consumer=consumer)

        bridge._on_feedback(("127.0.0.1", 54321), FEEDBACK_ADDRESS, "ok")

        message = consumer.get(timeout=SILENCE_TIMEOUT)
        assert message == FeedbackMessage(address=FEEDBACK_ADDRESS, args=("ok",))
        assert bridge.rejected_origin_count == 0

    def test_feedback_from_an_untrusted_origin_is_dropped_and_counted(self) -> None:
        consumer = QueueFeedbackConsumer()
        bridge = OscBridge(BridgeConfig(send_host="127.0.0.1", receive_port=0), consumer=consumer)

        bridge._on_feedback(("10.0.0.99", 54321), FEEDBACK_ADDRESS, "spoofed")

        with pytest.raises(queue.Empty):
            consumer.get(timeout=SILENCE_TIMEOUT)
        assert bridge.rejected_origin_count == 1

    def test_state_message_from_an_untrusted_origin_is_also_dropped(self) -> None:
        consumer = QueueFeedbackConsumer()
        bridge = OscBridge(BridgeConfig(send_host="127.0.0.1", receive_port=0), consumer=consumer)

        bridge._on_feedback(("10.0.0.99", 1), STATE_ADDRESS, "spoofed-state")

        with pytest.raises(queue.Empty):
            consumer.get(timeout=SILENCE_TIMEOUT)
        assert bridge.rejected_origin_count == 1

    def test_multiple_untrusted_messages_each_increment_the_counter(self) -> None:
        consumer = QueueFeedbackConsumer()
        bridge = OscBridge(BridgeConfig(send_host="127.0.0.1", receive_port=0), consumer=consumer)

        bridge._on_feedback(("10.0.0.99", 1), FEEDBACK_ADDRESS, "a")
        bridge._on_feedback(("10.0.0.98", 1), FEEDBACK_ADDRESS, "b")

        assert bridge.rejected_origin_count == 2
        with pytest.raises(queue.Empty):
            consumer.get(timeout=SILENCE_TIMEOUT)

    def test_real_dispatcher_wiring_delivers_from_the_trusted_loopback_host(self) -> None:
        # End-to-end: confirms the dispatcher is actually wired with
        # needs_reply_address=True (not just that a direct call works) —
        # a real client on 127.0.0.1 matches the default send_host trust.
        consumer = QueueFeedbackConsumer()
        with OscBridge(BridgeConfig(receive_port=0), consumer=consumer) as bridge:
            client = SimpleUDPClient("127.0.0.1", bridge.receive_port)
            client.send_message(FEEDBACK_ADDRESS, "trusted")
            message = consumer.get(timeout=RECEIVE_TIMEOUT)
        assert message == FeedbackMessage(address=FEEDBACK_ADDRESS, args=("trusted",))
        assert bridge.rejected_origin_count == 0


class TestConfigAndLifecycle:
    """Host/port are configurable with sane defaults; receiver lifecycle is safe."""

    def test_default_config_targets_local_onpc(self) -> None:
        config = BridgeConfig()
        assert config.send_host == "127.0.0.1"
        assert config.send_port == 8000
        assert config.receive_host == "127.0.0.1"
        assert config.receive_port == 9000

    def test_host_and_port_are_constructor_configurable(self) -> None:
        config = BridgeConfig(
            send_host="10.0.0.5", send_port=7001, receive_host="0.0.0.0", receive_port=7002
        )
        assert (config.send_host, config.send_port) == ("10.0.0.5", 7001)
        assert (config.receive_host, config.receive_port) == ("0.0.0.0", 7002)

    def test_default_consumer_is_a_queue_consumer(self) -> None:
        assert isinstance(OscBridge().consumer, QueueFeedbackConsumer)

    def test_receive_port_zero_binds_an_ephemeral_port_once_started(self) -> None:
        with OscBridge(BridgeConfig(receive_port=0)) as bridge:
            assert bridge.receive_port > 0

    def test_sending_does_not_require_the_receiver_to_be_started(self) -> None:
        with LoopbackConsoleServer() as console:
            bridge = OscBridge(BridgeConfig(send_port=console.port))
            bridge.send_command("Group 1")  # no start() call
            address, _ = console.messages.get(timeout=RECEIVE_TIMEOUT)
            assert address == CMD_ADDRESS

    def test_start_and_stop_are_idempotent(self) -> None:
        bridge = OscBridge(BridgeConfig(receive_port=0))
        bridge.start()
        first_port = bridge.receive_port
        bridge.start()  # second start is a no-op
        assert bridge.receive_port == first_port
        bridge.stop()
        bridge.stop()  # second stop is a no-op


class TestReceivePortRebindRecovery:
    """AC-DEPLOY-023 / REQ-DEPLOY-032 (#6) — an occupied receive port triggers a
    SAME-port rebind attempt (SO_REUSEADDR + bounded retry), NEVER a silent drift
    to an arbitrary port (REQ-DEPLOY-026), and on exhaustion raises a human-friendly
    typed error (naming the port + the Settings reconfiguration knob) — NOT a raw
    uncaught OSError crash.

    Port-preemption simulation: a LIVE ``SOCK_DGRAM`` socket holds the designated
    receive port. With ``SO_REUSEADDR`` (and deliberately NOT ``SO_REUSEPORT``) a
    second live UDP bind on the same port still fails on typical OSes, so this
    exercises the UNRECOVERABLE path. The successful-rebind-after-dead-prior-
    instance case is live/timing-gated (deferred N/A — see AC-DEPLOY-023).
    """

    @staticmethod
    def _occupy_udp_port() -> tuple[socket.socket, int]:
        squatter = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        squatter.bind(("127.0.0.1", 0))
        return squatter, squatter.getsockname()[1]

    def test_reuse_address_is_enabled_on_the_receive_server(self) -> None:
        # (a) reuse attempted: the receive server sets SO_REUSEADDR before bind, so a
        # port left held by an abnormally-exited prior instance can be reclaimed.
        assert osc_module._ReuseAddrOSCUDPServer.allow_reuse_address is True
        with OscBridge(BridgeConfig(receive_port=0)) as bridge:
            assert bridge._server.allow_reuse_address is True

    def test_occupied_receive_port_retries_same_port_then_raises_guidance(self) -> None:
        squatter, port = self._occupy_udp_port()
        sleeps: list[float] = []
        bridge = OscBridge(
            BridgeConfig(receive_host="127.0.0.1", receive_port=port),
            bind_attempts=3,
            bind_retry_delay=0.01,
            sleeper=sleeps.append,
        )
        try:
            with pytest.raises(ReceivePortInUseError) as excinfo:
                bridge.start()
        finally:
            squatter.close()

        err = excinfo.value
        # (b) bounded retry occurred: (attempts - 1) backoffs between the N bind tries.
        assert len(sleeps) == 2
        # (c) NO silent drift (REQ-DEPLOY-026): the bridge never bound a different
        # port — nothing is running and the reported receive port is still designated.
        assert bridge._server is None
        assert bridge.receive_port == port
        # (d) human-friendly typed error, NOT a raw OSError crash: names the port +
        # the Settings reconfiguration knob; the raw OSError is chained as the cause.
        assert isinstance(err, RuntimeError)
        assert not isinstance(err, OSError)  # distinct from the raw EADDRINUSE crash
        text = f"{err} {err.guidance}"
        assert str(port) in text
        assert "reconfigure" in err.guidance.lower() or "설정" in err.guidance
        assert "Settings" in err.guidance or "설정" in err.guidance
        assert isinstance(err.__cause__, OSError)

    def test_clean_start_on_a_free_port_is_unaffected_and_stop_releases(self) -> None:
        # Normal-lifecycle regression: the reuse + retry path must not disturb the
        # happy path — a free port binds on the first try (no backoff) and stop()
        # releases it so a fresh reuse-enabled bind on the same port succeeds.
        sleeps: list[float] = []
        bridge = OscBridge(BridgeConfig(receive_port=0), sleeper=sleeps.append)
        bridge.start()
        port = bridge.receive_port
        assert port > 0
        assert sleeps == []  # bound first try — no backoff on a free port
        bridge.stop()

        rebound = OscBridge(BridgeConfig(receive_host="127.0.0.1", receive_port=port))
        rebound.start()
        assert rebound.receive_port == port
        rebound.stop()
