"""Live OSC round-trip + receive-port checks (SPEC-COPILOT-PRESHOW-001).

Uses a lightweight loopback fake console (no Lua/lupa dependency, unlike
``test_responder_roundtrip.py``'s ``ResponderHarness``) that replies to the
two verbs this module sends (``ping``, ``state``) with synthetic responder
payloads. Sufficient here because ``server/preshow/osc_check.py`` only
exercises the wire protocol, not the console-side Lua logic.
"""

from __future__ import annotations

import re
import socket
import threading

import pytest
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from server.bridge.osc import CMD_ADDRESS, FEEDBACK_ADDRESS, STATE_ADDRESS, BridgeConfig
from server.bridge.protocol import encode_payload
from server.preshow.osc_check import check_osc_roundtrip, check_receive_port_binding

_WAIT = 5.0
_PLUGIN_CALL = re.compile(r'^Plugin "CopilotResponder" "(\w+) (\S+)(?: (.*))?"$')


class FakeConsole:
    """Replies to ``ping``/``state`` verbs with synthetic responder payloads."""

    def __init__(self, reply_host: str, reply_port: int, *, child_count: int = 4):
        self._client = SimpleUDPClient(reply_host, reply_port)
        self._child_count = child_count
        dispatcher = Dispatcher()
        dispatcher.map(CMD_ADDRESS, self._on_cmd)
        self._server = ThreadingOSCUDPServer(("127.0.0.1", 0), dispatcher)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def cmd_port(self) -> int:
        return self._server.socket.getsockname()[1]

    def _on_cmd(self, address: str, *args) -> None:
        match = _PLUGIN_CALL.match(args[0]) if args else None
        if match is None:
            return
        verb, request_id, rest = match.group(1), match.group(2), match.group(3)
        if verb == "ping":
            payload = encode_payload({"kind": "pong", "id": request_id, "v": 1, "version": "test-1.0"})
            self._client.send_message(FEEDBACK_ADDRESS, payload)
        elif verb == "state":
            payload = encode_payload(
                {
                    "kind": "state",
                    "id": request_id,
                    "node": {"name": rest, "childCount": self._child_count},
                    "children": [],
                }
            )
            self._client.send_message(STATE_ADDRESS, payload)

    def __enter__(self) -> "FakeConsole":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=_WAIT)


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestCheckOscRoundtrip:
    def test_pass_against_a_live_fake_console(self):
        reply_port = _free_udp_port()
        with FakeConsole("127.0.0.1", reply_port) as console:
            config = BridgeConfig(send_port=console.cmd_port, receive_port=reply_port)
            result = check_osc_roundtrip(config, wait=_WAIT)
        assert result.status == "pass"
        assert result.data["ping"]["version"] == "test-1.0"
        assert result.data["state"]["node"]["childCount"] == 4

    def test_skip_when_no_console_listening(self):
        # Nothing is bound to this send port — no reply will ever arrive.
        config = BridgeConfig(send_host="127.0.0.1", send_port=1, receive_port=0)
        result = check_osc_roundtrip(config, wait=0.3)
        assert result.status == "skip"
        assert "응답 없음" in result.detail


class TestCheckReceivePortBinding:
    def test_pass_when_ephemeral_port_requested(self):
        # receive_port=0 is exempt from the mismatch check by design (an
        # ephemeral bind has no fixed value to drift from).
        config = BridgeConfig(send_port=1, receive_port=0)
        result = check_receive_port_binding(config)
        assert result.status == "pass"

    def test_pass_when_fixed_port_binds_successfully(self):
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            free_port = sock.getsockname()[1]
        config = BridgeConfig(send_port=1, receive_port=free_port)
        result = check_receive_port_binding(config)
        assert result.status == "pass"
        assert result.data == {"configured": free_port, "actual": free_port}

    def test_fail_when_port_already_held(self):
        import socket

        holder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        holder.bind(("127.0.0.1", 0))
        held_port = holder.getsockname()[1]
        try:
            config = BridgeConfig(send_port=1, receive_port=held_port)
            result = check_receive_port_binding(config)
            assert result.status == "fail"
        finally:
            holder.close()
