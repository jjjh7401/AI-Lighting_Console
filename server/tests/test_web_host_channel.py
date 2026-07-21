"""Sidecar -> host stdout channel (M7.4a — AC-DEPLOY-024 ②③).

The Stage-2 Tauri shell must learn two things from the backend it spawned:

* **where to point the webview** — the served loopback URL. It cannot hold that
  as a Rust literal: ``packaging/rust_scan.py`` denies ``127.0.0.1`` and
  console-port literals in the shell's Rust source (AC-DEPLOY-027 Layer ①), and
  a literal would desync the moment the operator reconfigures the port.
* **the gate-truth health state** — ``online`` / ``console_offline`` /
  ``responder_degraded`` (the M5 states) so the tray badge is real, not decorative.

Both cross the process boundary on the sidecar's **stdout**, which the host
already pipes: one line, one prefix, no parsing ambiguity. Not a socket — the
shell owns zero network surface by construction.
"""

from __future__ import annotations

import io

import pytest

from server.web import host_channel


class TestReadyLine:
    def test_ready_line_carries_the_url_on_one_prefixed_line(self):
        out = io.StringIO()
        host_channel.emit_ready("http://127.0.0.1:8765", out=out)
        assert out.getvalue() == f"{host_channel.READY_PREFIX}http://127.0.0.1:8765\n"

    def test_ready_line_is_flushed(self):
        # A pipe to the host is block-buffered; an unflushed ready line would
        # leave the shell waiting forever on a window it never opens.
        flushed: list[bool] = []

        class _Stream(io.StringIO):
            def flush(self) -> None:
                flushed.append(True)

        host_channel.emit_ready("http://x", out=_Stream())
        assert flushed, "the ready line was not flushed"


class TestStatusLine:
    @pytest.mark.parametrize("health", ["online", "console_offline", "responder_degraded"])
    def test_each_m5_health_state_round_trips(self, health):
        out = io.StringIO()
        host_channel.emit_status(health, out=out)
        assert out.getvalue() == f"{host_channel.STATUS_PREFIX}{health}\n"

    def test_prefixes_are_distinct_and_unambiguous(self):
        assert host_channel.READY_PREFIX != host_channel.STATUS_PREFIX
        assert not host_channel.READY_PREFIX.startswith(host_channel.STATUS_PREFIX)
        assert not host_channel.STATUS_PREFIX.startswith(host_channel.READY_PREFIX)

    def test_a_newline_in_the_payload_cannot_forge_a_second_line(self):
        # The channel is line-oriented; an embedded newline would let one value
        # inject a second protocol line into the host's parser.
        out = io.StringIO()
        host_channel.emit_status("online\n@copilot:ready http://evil", out=out)
        assert out.getvalue().count("\n") == 1, out.getvalue()


class TestNoStreamIsSurvivable:
    def test_emitting_without_a_stream_is_a_no_op(self):
        # A windowed PyInstaller bundle can hand the process a None stdout;
        # the emitters must degrade to silence, never crash the server.
        host_channel.emit_ready("http://x", out=None)
        host_channel.emit_status("online", out=None)

    def test_a_broken_pipe_does_not_propagate(self):
        class _Broken(io.StringIO):
            def write(self, _text):  # noqa: ANN001 - stream signature
                raise BrokenPipeError("host went away")

        # The host exiting first must not take the backend down through an
        # unhandled write error; the watchdog owns that teardown.
        host_channel.emit_status("online", out=_Broken())


class TestStatusEmitter:
    def test_emitter_reads_the_health_at_call_time(self):
        out = io.StringIO()
        health = {"value": "online"}
        notify = host_channel.make_status_emitter(lambda: health["value"], out=out)
        notify()
        health["value"] = "console_offline"
        notify()
        assert out.getvalue().splitlines() == [
            f"{host_channel.STATUS_PREFIX}online",
            f"{host_channel.STATUS_PREFIX}console_offline",
        ]

    def test_emitter_swallows_a_health_read_failure(self):
        def _angry() -> str:
            raise RuntimeError("gate unavailable")

        notify = host_channel.make_status_emitter(_angry, out=io.StringIO())
        notify()  # a status-push failure must never break the heartbeat loop
