"""Tests for the ``/copilot/state`` receive path (M2 — plan.md §A-5 namespace).

State snapshot replies from the console-side Lua responder arrive on
``/copilot/state`` and must reach the same result-confirmation attach point
(:class:`FeedbackConsumer`) as ``/copilot/feedback`` messages; consumers
discriminate by ``FeedbackMessage.address``.
"""

from __future__ import annotations

import time

from pythonosc.udp_client import SimpleUDPClient

from server.bridge.osc import (
    FEEDBACK_ADDRESS,
    STATE_ADDRESS,
    BridgeConfig,
    OscBridge,
    QueueFeedbackConsumer,
)

_RECEIVE_TIMEOUT = 5.0


def _loopback_bridge() -> tuple[OscBridge, QueueFeedbackConsumer]:
    consumer = QueueFeedbackConsumer()
    bridge = OscBridge(BridgeConfig(receive_host="127.0.0.1", receive_port=0), consumer=consumer)
    return bridge, consumer


class TestStateReceiving:
    def test_state_address_constant(self):
        assert STATE_ADDRESS == "/copilot/state"

    def test_state_message_is_delivered_to_result_confirmation_path(self):
        bridge, consumer = _loopback_bridge()
        with bridge:
            client = SimpleUDPClient("127.0.0.1", bridge.receive_port)
            client.send_message(STATE_ADDRESS, "%7B%22v%22%3A1%7D")
            message = consumer.get(timeout=_RECEIVE_TIMEOUT)
        assert message.address == STATE_ADDRESS
        assert message.args == ("%7B%22v%22%3A1%7D",)

    def test_state_and_feedback_are_discriminable_by_address(self):
        bridge, consumer = _loopback_bridge()
        with bridge:
            client = SimpleUDPClient("127.0.0.1", bridge.receive_port)
            client.send_message(STATE_ADDRESS, "state-payload")
            first = consumer.get(timeout=_RECEIVE_TIMEOUT)
            client.send_message(FEEDBACK_ADDRESS, "feedback-payload")
            second = consumer.get(timeout=_RECEIVE_TIMEOUT)
        addresses = {first.address, second.address}
        assert addresses == {STATE_ADDRESS, FEEDBACK_ADDRESS}

    def test_unrelated_addresses_are_not_delivered(self):
        bridge, consumer = _loopback_bridge()
        with bridge:
            client = SimpleUDPClient("127.0.0.1", bridge.receive_port)
            client.send_message("/copilot/unknown", "x")
            client.send_message(STATE_ADDRESS, "y")
            message = consumer.get(timeout=_RECEIVE_TIMEOUT)
            # Give the unrelated message time to (wrongly) arrive if mapped.
            time.sleep(0.1)
        assert message.address == STATE_ADDRESS
        assert consumer._messages.empty()
