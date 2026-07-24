"""Round-trip tool tests (M2 — AC-MVP-012 automated sub-evidence).

Drives ``server/tools/responder_roundtrip.py`` against a **fake console**: a
loopback OSC server that receives ``/copilot/cmd`` plugin-call command lines
and executes them through the REAL ``console/lua/copilot_responder.lua``
(embedded Lua 5.4 via lupa), forwarding its replies over real UDP back to the
tool. The only simulated element is the MA3 API surface itself — the full
server->console->server protocol loop is exercised in-process.

The live onPC 2.4.2 counterpart of this loop is the SEMI-AUTOMATIC part of
AC-MVP-012 and is NOT covered here (reported as a gap in progress.md).
"""

from __future__ import annotations

import re
import socket
import threading

import pytest
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from server.bridge.osc import CMD_ADDRESS, BridgeConfig
from server.tools.responder_roundtrip import run_diagnose, run_roundtrip

from .lua_mock_env import ResponderHarness

_PLUGIN_CALL = re.compile(r'^Plugin "CopilotResponder" "(.*)"$')
_WAIT = 5.0


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class FakeConsole:
    """Simulated onPC: /copilot/cmd plugin calls run the real Lua responder."""

    def __init__(self, reply_host: str, reply_port: int):
        self.harness = ResponderHarness()
        self._client = SimpleUDPClient(reply_host, reply_port)
        self._forwarded = 0
        self._lock = threading.Lock()
        dispatcher = Dispatcher()
        dispatcher.map(CMD_ADDRESS, self._on_cmd)
        self._server = ThreadingOSCUDPServer(("127.0.0.1", 0), dispatcher)
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="fake-console", daemon=True
        )

    @property
    def cmd_port(self) -> int:
        return self._server.socket.getsockname()[1]

    def _on_cmd(self, address: str, *args) -> None:
        match = _PLUGIN_CALL.match(args[0]) if args else None
        if match is None:
            return  # raw command line: native execution, no reply (fire-and-forget)
        with self._lock:
            self.harness.main(None, match.group(1))
            sent = self.harness.sent()
            for message in sent[self._forwarded :]:
                self._client.send_message(message.address, message.payload)
            self._forwarded = len(sent)

    def __enter__(self) -> FakeConsole:
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5.0)


@pytest.fixture()
def loop() -> tuple[FakeConsole, BridgeConfig]:
    listen_port = _free_udp_port()
    with FakeConsole("127.0.0.1", listen_port) as console:
        config = BridgeConfig(
            send_host="127.0.0.1",
            send_port=console.cmd_port,
            receive_host="127.0.0.1",
            receive_port=listen_port,
        )
        yield console, config


class TestRoundtrip:
    def test_full_roundtrip_passes_all_steps(self, loop):
        console, config = loop
        report = run_roundtrip(config, wait=_WAIT)
        assert [step.name for step in report.steps] == ["ping", "state", "exec"]
        assert report.ok, [step.detail for step in report.steps]

    def test_state_step_returns_snapshot_of_mock_tree(self, loop):
        _, config = loop
        report = run_roundtrip(config, path="DataPool/Sequences", wait=_WAIT)
        state = next(step for step in report.steps if step.name == "state")
        names = [child["name"] for child in state.payload["children"]]
        assert names == ["Sequence 1", "Sequence 2", "Sequence 3"]

    def test_exec_step_runs_command_via_cmd(self, loop):
        console, config = loop
        report = run_roundtrip(config, exec_command="List", wait=_WAIT)
        assert report.ok
        assert console.harness.cmd_log() == ["List"]

    def test_unknown_path_fails_state_step_but_not_ping(self, loop):
        _, config = loop
        report = run_roundtrip(config, path="DataPool/Nonexistent", wait=_WAIT)
        results = {step.name: step.ok for step in report.steps}
        assert results["ping"] is True
        assert results["state"] is False
        assert report.ok is False

    def test_expect_version_match_passes(self, loop):
        # Deployment-reliability check (2026-07-24 finding): a fast,
        # definitive "did my deploy take effect" signal from ping alone.
        _, config = loop
        report = run_roundtrip(config, wait=_WAIT, skip_exec=True, expect_version="1.4.1")
        assert report.ok
        ping = next(step for step in report.steps if step.name == "ping")
        assert ping.payload["version"] == "1.4.1"

    def test_expect_version_mismatch_fails_ping_with_clear_detail(self, loop):
        _, config = loop
        report = run_roundtrip(config, wait=_WAIT, skip_exec=True, expect_version="9.9.9")
        ping = next(step for step in report.steps if step.name == "ping")
        assert ping.ok is False
        assert "9.9.9" in ping.detail
        assert "1.4.1" in ping.detail
        assert report.ok is False

    def test_skip_exec_runs_two_steps(self, loop):
        _, config = loop
        report = run_roundtrip(config, wait=_WAIT, skip_exec=True)
        assert [step.name for step in report.steps] == ["ping", "state"]
        assert report.ok

    def test_no_console_times_out_every_step(self):
        config = BridgeConfig(
            send_host="127.0.0.1",
            send_port=_free_udp_port(),  # nobody listening
            receive_host="127.0.0.1",
            receive_port=0,
        )
        report = run_roundtrip(config, wait=0.3)
        assert report.ok is False
        assert all(not step.ok for step in report.steps)
        assert all("timeout" in step.detail for step in report.steps)


class TestMainCli:
    def test_exit_zero_on_success(self, loop):
        console, config = loop
        argv = [
            "--host",
            "127.0.0.1",
            "--port",
            str(config.send_port),
            "--listen-port",
            str(config.receive_port),
            "--wait",
            str(_WAIT),
        ]
        from server.tools.responder_roundtrip import main

        assert main(argv) == 0

    def test_exit_one_on_failure(self):
        from server.tools.responder_roundtrip import main

        argv = [
            "--host",
            "127.0.0.1",
            "--port",
            str(_free_udp_port()),
            "--listen-port",
            "0",
            "--wait",
            "0.3",
        ]
        assert main(argv) == 1


class TestDiagnose:
    def test_diagnose_captures_arbitrary_addresses(self):
        captured: list[tuple[str, tuple]] = []
        port = _free_udp_port()

        def send_one():
            SimpleUDPClient("127.0.0.1", port).send_message("/copilot/copilot/state", "x")

        timer = threading.Timer(0.2, send_one)
        timer.start()
        try:
            run_diagnose(
                "127.0.0.1",
                port,
                duration=1.0,
                on_message=lambda a, args: captured.append((a, args)),
            )
        finally:
            timer.cancel()
        assert captured == [("/copilot/copilot/state", ("x",))]
