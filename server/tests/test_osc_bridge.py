"""Behavior tests for the OSC bridge (AC-MVP-011 — REQ-MVP-001, REQ-MVP-002).

Verified with a local loopback OSC server (no console required):
  1. A command handed to the bridge is sent as UDP OSC to ``/copilot/cmd``.
  2. A ``/copilot/feedback`` message sent to the bridge's receive port is
     delivered to the result-confirmation path (consumer callback / queue).

All waits are event/timeout-bounded (no sleeps); all ports are ephemeral (port 0).
"""

import queue
import threading

import pytest
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from server.bridge.osc import (
    CMD_ADDRESS,
    FEEDBACK_ADDRESS,
    BridgeConfig,
    FeedbackMessage,
    OscBridge,
    QueueFeedbackConsumer,
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
