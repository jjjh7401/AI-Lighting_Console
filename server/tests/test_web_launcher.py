"""Launcher primitive tests (M6 — REQ-DEPLOY-001~003/006/006a/025/026).

The launcher wires the packaged-app process start: browser open at the served
local URL, port-in-use fail-loud (no silent random-port fallback), graceful
process-tree shutdown, keyring backend pin + fail-closed guard, and the
``--self-check`` frozen keyring roundtrip (research §B.3 / §B.4 / §E).

All primitives are dependency-injectable so this dev-venv suite proves the fail
paths WITHOUT touching the real Keychain (research §B.4: the real roundtrip runs
inside the PACKAGED binary at M6/Part 2, not in dev-venv pytest).
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from server.web import launcher

# --------------------------------------------------------------- keyring pin (B.3)


class TestKeyringBackendPin:
    def test_pin_sets_the_macos_backend_when_unset(self):
        environ: dict[str, str] = {}
        launcher.apply_keyring_backend_pin(environ)
        assert environ[launcher.KEYRING_BACKEND_ENV] == launcher.PINNED_KEYRING_BACKEND
        assert launcher.PINNED_KEYRING_BACKEND == "keyring.backends.macOS.Keyring"

    def test_pin_preserves_an_existing_value(self):
        environ = {launcher.KEYRING_BACKEND_ENV: "operator.override.Backend"}
        launcher.apply_keyring_backend_pin(environ)
        # setdefault semantics — an explicit operator override is not clobbered.
        assert environ[launcher.KEYRING_BACKEND_ENV] == "operator.override.Backend"


# -------------------------------------------------- keyring fail-closed guard (B.3)


def _fake_keyring(module_name: str):
    """A fake ``keyring`` module whose active backend reports ``module_name``."""

    # The class is deliberately named ``Keyring`` for the __name__ vs __module__
    # discrimination proof: the real macOS/fail/SecretService backends are all
    # named ``Keyring`` (research §B.3) — only __module__ distinguishes them.
    backend_cls = type("Keyring", (), {})
    backend_cls.__module__ = module_name
    instance = backend_cls()

    class _FakeKeyring:
        @staticmethod
        def get_keyring():
            return instance

    return _FakeKeyring


class TestAssertKeyringBackend:
    def test_passes_on_the_macos_backend(self):
        # No raise when the active backend module is keyring.backends.macOS.
        launcher.assert_keyring_backend(keyring_module=_fake_keyring("keyring.backends.macOS"))

    def test_fails_closed_on_the_fail_backend(self):
        with pytest.raises(RuntimeError) as excinfo:
            launcher.assert_keyring_backend(keyring_module=_fake_keyring("keyring.backends.fail"))
        message = str(excinfo.value)
        assert "refusing to start" in message
        assert "REQ-DEPLOY-006a" in message
        assert "no plaintext fallback" in message

    def test_fails_closed_on_a_leaked_keyrings_alt_file_backend(self):
        # A leaked plaintext/obfuscated keyrings.alt backend is exactly the
        # REQ-DEPLOY-006a leak vector — the __module__ gate rejects it.
        with pytest.raises(RuntimeError):
            launcher.assert_keyring_backend(
                keyring_module=_fake_keyring("keyrings.alt.file")
            )

    def test_discriminates_on_module_not_class_name(self):
        # The wrong backend's class is ALSO named "Keyring"; only __module__
        # differs. A __name__-based check would wrongly accept it (research §B.3).
        wrong = _fake_keyring("keyring.backends.fail")
        assert type(wrong.get_keyring()).__name__ == "Keyring"
        with pytest.raises(RuntimeError):
            launcher.assert_keyring_backend(keyring_module=wrong)


# ---------------------------------------------------------------- self-check (B.4)


class _FakeStore:
    """An in-memory keyring double with a configurable backend + roundtrip."""

    def __init__(
        self,
        module_name="keyring.backends.macOS",
        *,
        broken_set=False,
        broken_delete=False,
    ):
        backend_cls = type("Keyring", (), {})
        backend_cls.__module__ = module_name
        self._backend = backend_cls()
        self._store: dict[tuple[str, str], str] = {}
        self._broken_set = broken_set
        self._broken_delete = broken_delete

    def get_keyring(self):
        return self._backend

    def set_password(self, service, account, value):
        if self._broken_set:
            raise RuntimeError("simulated Keychain write failure")
        self._store[(service, account)] = value

    def get_password(self, service, account):
        return self._store.get((service, account))

    def delete_password(self, service, account):
        if self._broken_delete:
            return  # simulate a delete that silently leaves the value
        self._store.pop((service, account), None)


class TestRunSelfCheck:
    def test_ok_on_working_macos_backend_and_roundtrip(self):
        rc = launcher.run_self_check(keyring_module=_FakeStore(), out=_Sink())
        assert rc == 0

    def test_nonzero_on_wrong_backend(self):
        rc = launcher.run_self_check(
            keyring_module=_FakeStore("keyring.backends.fail"), out=_Sink()
        )
        assert rc != 0

    def test_nonzero_on_leaked_alt_backend(self):
        rc = launcher.run_self_check(
            keyring_module=_FakeStore("keyrings.alt.file"), out=_Sink()
        )
        assert rc != 0

    def test_nonzero_when_roundtrip_write_raises(self):
        rc = launcher.run_self_check(
            keyring_module=_FakeStore(broken_set=True), out=_Sink()
        )
        assert rc != 0

    def test_nonzero_when_delete_leaves_the_value(self):
        # delete then get must be None; a backend that leaves the value fails.
        rc = launcher.run_self_check(
            keyring_module=_FakeStore(broken_delete=True), out=_Sink()
        )
        assert rc != 0

    def test_uses_the_research_probe_service_and_sentinel(self):
        store = _FakeStore()
        launcher.run_self_check(keyring_module=store, out=_Sink())
        # After a clean roundtrip the probe key is deleted (no residue).
        assert store.get_password(launcher.SELF_CHECK_SERVICE, launcher.SELF_CHECK_ACCOUNT) is None
        assert launcher.SELF_CHECK_SERVICE == "grandma3-copilot-selfcheck"


class _Sink:
    def write(self, *_args, **_kwargs):
        return None


# --------------------------------------------------------- port-in-use (025/026)


def _occupy_port() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    return sock, sock.getsockname()[1]


class TestPortProbe:
    def test_free_port_is_available(self):
        sock, port = _occupy_port()
        sock.close()  # release it
        assert launcher.probe_port_available("127.0.0.1", port) is True

    def test_occupied_port_is_unavailable(self):
        sock, port = _occupy_port()
        try:
            assert launcher.probe_port_available("127.0.0.1", port) is False
        finally:
            sock.close()


class TestRequirePortsAvailable:
    def test_raises_with_reconfig_guidance_on_occupied_port(self):
        sock, port = _occupy_port()
        try:
            with pytest.raises(launcher.PortInUseError) as excinfo:
                launcher.require_ports_available([("127.0.0.1", port, "web UI")])
        finally:
            sock.close()
        err = excinfo.value
        text = f"{err} {err.guidance}"
        # No silent random-port fallback: explicit error names the port + the
        # label + reconfiguration guidance (AC-DEPLOY-015 ② / REQ-DEPLOY-026).
        assert str(port) in text
        assert "web UI" in text
        assert "reconfigure" in err.guidance.lower() or "설정" in err.guidance

    def test_passes_when_all_ports_free(self):
        sock, port = _occupy_port()
        sock.close()
        launcher.require_ports_available([("127.0.0.1", port, "web UI")])

    def test_ignores_port_zero(self):
        # --receive-port 0 means "OS assigns a free port" — not a fixed port to
        # pre-check, so it is skipped.
        launcher.require_ports_available([("127.0.0.1", 0, "OSC feedback listen")])


# ------------------------------------------------- UDP receive-port preflight (026)


@contextlib.contextmanager
def _occupy_osc_receive_port():
    """Hold a port exactly the way a real OSC receiver holds it.

    Not a bare ``SOCK_DGRAM`` bind: the production receiver is
    :class:`server.bridge.osc._ReuseAddrOSCUDPServer` and sets SO_REUSEADDR
    before binding (the M18 same-port rebind strategy depends on it). A probe
    that only survives a *plain* holder proves nothing about the real one.

    Binds the SPECIFIC loopback address — this is the "a second copy of OUR OWN
    app is already running" shape, which the preflight must keep catching.
    """
    from pythonosc.dispatcher import Dispatcher

    from server.bridge.osc import _ReuseAddrOSCUDPServer

    server = _ReuseAddrOSCUDPServer(("127.0.0.1", 0), Dispatcher())
    try:
        yield server.socket.getsockname()[1]
    finally:
        server.server_close()


@contextlib.contextmanager
def _occupy_wildcard_udp_port():
    """Hold a UDP port the way onPC holds one — bound to the WILDCARD address.

    Measured against the live console (``lsof -nP -iUDP``): grandMA3 onPC's OSC
    entries appear as ``UDP *:8000`` / ``UDP *:9000``, i.e. ``0.0.0.0``. A
    grandMA3 OSC entry has ONE port used for BOTH directions, so the port the
    console replies THROUGH is simultaneously an input the console holds — and
    the app must still be able to listen on it.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 0))
    try:
        yield sock.getsockname()[1]
    finally:
        sock.close()


class TestOscReceivePortIsProbedAsUdp:
    """The OSC receive port is UDP; a TCP probe sails straight past it."""

    def test_the_tcp_probe_is_blind_to_a_held_udp_receive_port(self):
        # Pins WHY the protocol parameter has to exist. TCP and UDP are separate
        # port spaces, so the default probe binds the TCP port of the same
        # number, succeeds, and reports the occupied receive port as free.
        with _occupy_osc_receive_port() as port:
            assert launcher.probe_port_available("127.0.0.1", port) is True

    def test_a_udp_probe_sees_a_duplicate_instance_holding_the_receive_port(self):
        # The case the preflight exists for: a second copy of OUR OWN app already
        # holds the SPECIFIC loopback receive address. Measured on darwin, that
        # collision survives SO_REUSEADDR on both sides (two sockets cannot share
        # one exact addr:port without SO_REUSEPORT), so modelling the receiver's
        # real bind options does NOT weaken this detection.
        with _occupy_osc_receive_port() as port:
            assert (
                launcher.probe_port_available(
                    "127.0.0.1", port, sock_type=socket.SOCK_DGRAM
                )
                is False
            )

    def test_a_free_udp_port_is_still_reported_available(self):
        with _occupy_osc_receive_port() as port:
            pass  # released on exit — the same number must now read free
        assert (
            launcher.probe_port_available("127.0.0.1", port, sock_type=socket.SOCK_DGRAM)
            is True
        )

    def test_require_ports_available_rejects_an_occupied_receive_port(self):
        with (
            _occupy_osc_receive_port() as port,
            pytest.raises(launcher.PortInUseError) as excinfo,
        ):
            launcher.require_ports_available(
                [("127.0.0.1", port, "OSC feedback listen", socket.SOCK_DGRAM)]
            )
        err = excinfo.value
        assert str(port) in f"{err} {err.guidance}"
        assert "OSC feedback listen" in err.guidance

    def test_a_three_tuple_spec_still_means_tcp(self):
        # Backward compatibility: every pre-existing caller passes 3-tuples and
        # must keep its TCP semantics unchanged.
        sock, port = _occupy_port()
        try:
            with pytest.raises(launcher.PortInUseError):
                launcher.require_ports_available([("127.0.0.1", port, "web UI")])
        finally:
            sock.close()

    def test_port_zero_is_still_skipped_for_udp(self):
        launcher.require_ports_available(
            [("127.0.0.1", 0, "OSC feedback listen", socket.SOCK_DGRAM)]
        )


# ------------------------------------------- preflight models the REAL bind (026)


class TestThePreflightModelsTheReceiversActualBind:
    """The probe must answer "can OUR receiver bind here?", not "is the address
    pristine?".

    A grandMA3 OSC entry has ONE port for BOTH directions, so the port the
    console replies through is a port the console also holds — as a WILDCARD
    bind (measured live: ``UDP *:9000``). The real receiver
    (:class:`server.bridge.osc._ReuseAddrOSCUDPServer`, ``allow_reuse_address =
    True``) coexists with that wildcard holder by binding the SPECIFIC loopback
    address. A preflight that binds more strictly than the receiver it guards
    rejects a configuration that demonstrably works, and the app never starts.
    """

    def test_a_wildcard_holder_does_not_block_the_receive_port_preflight(self):
        # The exact live shape: onPC holds *:<port>, the app is configured to
        # receive on the same number. The real receiver binds fine, so the
        # preflight must report the port available.
        with _occupy_wildcard_udp_port() as port:
            assert (
                launcher.probe_port_available(
                    "127.0.0.1", port, sock_type=socket.SOCK_DGRAM
                )
                is True
            )

    def test_require_ports_available_admits_a_wildcard_held_receive_port(self):
        with _occupy_wildcard_udp_port() as port:
            launcher.require_ports_available(
                [("127.0.0.1", port, "OSC feedback listen", socket.SOCK_DGRAM)]
            )

    def test_the_real_receiver_can_bind_everything_the_preflight_admits(self):
        # The load-bearing equivalence, asserted against the PRODUCTION receiver
        # rather than a re-statement of the option flags: whatever the preflight
        # calls free, _ReuseAddrOSCUDPServer must actually be able to bind.
        from pythonosc.dispatcher import Dispatcher

        from server.bridge.osc import _ReuseAddrOSCUDPServer

        with _occupy_wildcard_udp_port() as port:
            assert (
                launcher.probe_port_available(
                    "127.0.0.1", port, sock_type=socket.SOCK_DGRAM
                )
                is True
            )
            server = _ReuseAddrOSCUDPServer(("127.0.0.1", port), Dispatcher())
            server.server_close()

    def test_a_strict_probe_is_still_available_for_foreign_holder_detection(self):
        # The opt-out exists because "can I bind here?" and "is anyone bound
        # here?" are different questions. console_probe.py asks the second one
        # and MUST keep the strict bind, or a wildcard-bound console input reads
        # as free.
        with _occupy_wildcard_udp_port() as port:
            assert (
                launcher.probe_port_available(
                    "127.0.0.1", port, sock_type=socket.SOCK_DGRAM, reuse_addr=False
                )
                is False
            )

    def test_the_udp_preflight_must_set_so_reuseaddr(self):
        # SUPERSEDES an earlier test that asserted the OPPOSITE. That test read
        # the same darwin measurement (SO_REUSEADDR lets a specific-address UDP
        # bind succeed past a WILDCARD holder) as evidence of a probe hole, and
        # concluded the UDP probe must bind strictly. The conclusion was wrong:
        # the thing the probe GUARDS — _ReuseAddrOSCUDPServer — sets the very
        # option the probe was denied, so the strict probe was stricter than
        # reality and rejected a configuration that works. It is what stopped the
        # app from starting against a console holding *:9000.
        #
        # What is NOT lost: a duplicate instance of this app binds the SPECIFIC
        # loopback address, and that collision is EADDRINUSE with SO_REUSEADDR on
        # both sides (measured) — asserted by
        # test_a_udp_probe_sees_a_duplicate_instance_holding_the_receive_port.
        from pythonosc.dispatcher import Dispatcher

        from server.bridge.osc import _ReuseAddrOSCUDPServer

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as scratch:
            scratch.bind(("127.0.0.1", 0))
            port = scratch.getsockname()[1]
        server = _ReuseAddrOSCUDPServer(("0.0.0.0", port), Dispatcher())
        try:
            assert (
                launcher.probe_port_available(
                    "127.0.0.1", port, sock_type=socket.SOCK_DGRAM
                )
                is True
            ), "the UDP preflight dropped SO_REUSEADDR — it now blocks a working start"
        finally:
            server.server_close()

    def test_the_startup_preflight_asks_the_probe_for_our_binders_options(self):
        # Caller-boundary assertion: require_ports_available must not quietly
        # opt into the strict bind for the UDP row, which would restore the
        # startup false positive with every probe-level test still green.
        seen: list[dict] = []

        def _spy(host, port, **kwargs):
            seen.append(kwargs)
            return True

        original = launcher.probe_port_available
        launcher.probe_port_available = _spy
        try:
            launcher.require_ports_available(
                [
                    ("127.0.0.1", 8765, "web UI", socket.SOCK_STREAM),
                    ("127.0.0.1", 9000, "OSC feedback listen", socket.SOCK_DGRAM),
                ]
            )
        finally:
            launcher.probe_port_available = original
        assert seen == [
            {"sock_type": socket.SOCK_STREAM},
            {"sock_type": socket.SOCK_DGRAM},
        ], "the preflight passed a reuse_addr override — it must take the default"


# ------------------------------------------------------------------- browser open


class TestOpenAppBrowser:
    def test_opens_when_enabled(self):
        opened: list[str] = []
        ok = launcher.open_app_browser(
            "http://127.0.0.1:8765", enabled=True, opener=opened.append
        )
        assert ok is True
        assert opened == ["http://127.0.0.1:8765"]

    def test_suppressed_when_disabled(self):
        opened: list[str] = []
        ok = launcher.open_app_browser(
            "http://127.0.0.1:8765", enabled=False, opener=opened.append
        )
        assert ok is False
        assert opened == []

    def test_opener_failure_is_swallowed(self):
        def boom(_url):
            raise RuntimeError("no display")

        # A headless/no-browser environment must not crash the launcher.
        assert launcher.open_app_browser("http://x", enabled=True, opener=boom) is False

    def test_serve_local_url_builds_the_loopback_url(self):
        assert launcher.serve_local_url("127.0.0.1", 8765) == "http://127.0.0.1:8765"
        assert launcher.serve_local_url("0.0.0.0", 9000) == "http://127.0.0.1:9000"


# ---------------------------------------------- graceful shutdown / process tree


class _FakeStack:
    def __init__(self):
        self.stopped = 0

    def stop(self):
        self.stopped += 1


class TestShutdownHandler:
    def test_handler_stops_stack_and_exits(self):
        stack = _FakeStack()
        exits: list[int] = []
        handler = launcher.make_shutdown_handler(
            stack, exit_fn=exits.append, child_pids=(), tree_terminator=lambda pid: None
        )
        handler(2, None)  # SIGINT
        assert stack.stopped == 1
        assert exits == [0]

    def test_handler_terminates_child_process_tree(self):
        stack = _FakeStack()
        reaped: list[int] = []
        handler = launcher.make_shutdown_handler(
            stack,
            exit_fn=lambda code: None,
            child_pids=(4242,),
            tree_terminator=reaped.append,
        )
        handler(15, None)  # SIGTERM
        assert stack.stopped == 1
        assert reaped == [4242]

    def test_stack_stops_before_the_tree_is_reaped(self):
        # M7.2 preservation guard: the console stack (OSC listeners / timers)
        # must be stopped BEFORE the group teardown, and the exit last. The
        # watchdog's self-reap relies on this ordering surviving unchanged.
        order: list[str] = []

        class _OrderedStack:
            def stop(self):
                order.append("stack.stop")

        handler = launcher.make_shutdown_handler(
            _OrderedStack(),
            exit_fn=lambda code: order.append("exit"),
            child_pids=(7,),
            tree_terminator=lambda pid: order.append("reap"),
        )
        handler(15, None)
        assert order == ["stack.stop", "reap", "exit"]

    def test_stack_stop_failure_still_reaps_children_and_exits(self):
        class _AngryStack:
            def stop(self):
                raise RuntimeError("stop failed")

        reaped: list[int] = []
        exits: list[int] = []
        handler = launcher.make_shutdown_handler(
            _AngryStack(),
            exit_fn=exits.append,
            child_pids=(99,),
            tree_terminator=reaped.append,
        )
        handler(15, None)
        assert reaped == [99]
        assert exits == [0]


class TestInstallSignalHandlers:
    def test_registers_sigint_and_sigterm(self):
        registered: dict[int, object] = {}

        def fake_register(sig, handler):
            registered[sig] = handler

        import signal

        launcher.install_signal_handlers(lambda *a: None, register=fake_register)
        assert signal.SIGINT in registered
        assert signal.SIGTERM in registered


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="POSIX process-group teardown only")
class TestTerminateProcessTree:
    def test_reaps_a_child_and_its_grandchild(self):
        # AC-DEPLOY-015 ①: teardown is a process-TREE, not a single PID. Spawn a
        # child that itself spawns a long-lived grandchild; terminating the tree
        # must leave neither alive (no grandchild Python zombie / port squatter).
        code = (
            "import subprocess, sys, time;"
            "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']);"
            "print(g.pid, flush=True);"
            "time.sleep(60)"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", code],
            stdout=subprocess.PIPE,
            text=True,
            start_new_session=True,  # child leads its own process group
        )
        grandchild_pid = int(child.stdout.readline().strip())
        # Both are alive now.
        assert _pid_alive(child.pid)
        assert _pid_alive(grandchild_pid)

        launcher.terminate_process_tree(child.pid, timeout=5.0)
        child.wait(timeout=5)

        # Give the OS a beat to reap the group.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and _pid_alive(grandchild_pid):
            time.sleep(0.05)
        assert not _pid_alive(child.pid)
        assert not _pid_alive(grandchild_pid), "grandchild survived the tree teardown"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# ----------------------------------------- parent-liveness watchdog (M7.2 / 025)
#
# AC-DEPLOY-026 ③: on a Tauri force-quit the Rust ``RunEvent::Exit`` never fires,
# so the sidecar must notice the dead parent itself and reap its own process
# group. PRIMARY trigger = pipe EOF (no race window), FALLBACK = getppid()
# polling, both inside a bounded max reap latency so the residual-0 scan is
# deterministic. The Rust authoritative half (setsid/Job Object, RunEvent::Exit)
# is M7.4 — AC-026 ① / ② are NOT provable here.


class TestWatchdogBounds:
    def test_poll_interval_is_bounded_by_the_max_reap_latency(self):
        # No unbounded race window: the fallback poll never exceeds the latency
        # ceiling the residual-0 scan is asserted against.
        assert 0 < launcher.PARENT_POLL_INTERVAL_SECONDS <= launcher.MAX_REAP_LATENCY_SECONDS
        assert launcher.MAX_REAP_LATENCY_SECONDS <= 1.0

    def test_rejects_an_unbounded_poll_interval(self):
        with pytest.raises(ValueError):
            launcher.ParentLivenessWatchdog(expected_ppid=4242, poll_interval=5.0)

    def test_rejects_a_nonpositive_poll_interval(self):
        with pytest.raises(ValueError):
            launcher.ParentLivenessWatchdog(expected_ppid=4242, poll_interval=0)

    def test_requires_a_parent_signal(self):
        # Neither a pipe nor an expected ppid = nothing to watch; refusing to
        # construct keeps a standalone launch from ever self-reaping.
        with pytest.raises(ValueError):
            launcher.ParentLivenessWatchdog()


class TestWatchdogPipeEOF:
    def test_eof_triggers_self_reap_within_the_latency_bound(self):
        read_fd, write_fd = os.pipe()
        reaped: list[int] = []
        watchdog = launcher.ParentLivenessWatchdog(
            pipe_fd=read_fd, reaper=reaped.append, pid=4242
        )
        watchdog.start()
        try:
            time.sleep(0.05)
            assert reaped == []  # parent still holds the write end
            started = time.monotonic()
            os.close(write_fd)  # the parent dies -> every write end closed
            fired = watchdog.triggered.wait(launcher.MAX_REAP_LATENCY_SECONDS)
            elapsed = time.monotonic() - started
        finally:
            watchdog.stop()
            os.close(read_fd)
        assert fired, "pipe EOF did not trigger the self-reap"
        assert reaped == [4242]  # reaps its OWN pid -> its own group
        assert elapsed <= launcher.MAX_REAP_LATENCY_SECONDS

    def test_heartbeat_byte_does_not_trigger(self):
        read_fd, write_fd = os.pipe()
        reaped: list[int] = []
        watchdog = launcher.ParentLivenessWatchdog(
            pipe_fd=read_fd, reaper=reaped.append, pid=4242
        )
        watchdog.start()
        try:
            os.write(write_fd, b"\x01")  # a live parent's heartbeat
            time.sleep(3 * launcher.PARENT_POLL_INTERVAL_SECONDS)
            assert not watchdog.triggered.is_set()
            assert reaped == []
        finally:
            watchdog.stop()
            os.close(write_fd)
            os.close(read_fd)


class TestWatchdogGetppidFallback:
    def test_orphan_triggers_self_reap_when_no_pipe_is_available(self):
        reaped: list[int] = []
        watchdog = launcher.ParentLivenessWatchdog(
            expected_ppid=4242,
            reaper=reaped.append,
            getppid=lambda: 1,  # POSIX re-parents an orphan to init
            pid=99,
        )
        started = time.monotonic()
        watchdog.start()
        try:
            fired = watchdog.triggered.wait(launcher.MAX_REAP_LATENCY_SECONDS)
            elapsed = time.monotonic() - started
        finally:
            watchdog.stop()
        assert fired, "getppid()==1 did not trigger the fallback self-reap"
        assert reaped == [99]
        assert elapsed <= launcher.MAX_REAP_LATENCY_SECONDS

    def test_live_parent_does_not_trigger(self):
        reaped: list[int] = []
        watchdog = launcher.ParentLivenessWatchdog(
            expected_ppid=4242, reaper=reaped.append, getppid=lambda: 4242
        )
        watchdog.start()
        try:
            time.sleep(3 * launcher.PARENT_POLL_INTERVAL_SECONDS)
            assert not watchdog.triggered.is_set()
            assert reaped == []
        finally:
            watchdog.stop()

    def test_pipe_failure_degrades_to_the_polling_fallback(self):
        read_fd, write_fd = os.pipe()
        os.close(read_fd)  # the inherited fd went bad
        os.close(write_fd)
        reaped: list[int] = []
        watchdog = launcher.ParentLivenessWatchdog(
            pipe_fd=read_fd, expected_ppid=4242, reaper=reaped.append, getppid=lambda: 1, pid=7
        )
        watchdog.start()
        try:
            assert watchdog.triggered.wait(launcher.MAX_REAP_LATENCY_SECONDS)
        finally:
            watchdog.stop()
        assert reaped == [7]


class TestInstallParentWatchdog:
    def test_standalone_launch_is_never_armed(self):
        # Stage-1 double-click / terminal launch: no host declared itself, and a
        # GUI launch's parent may legitimately BE launchd (pid 1). Arming there
        # would self-reap a healthy standalone server.
        assert launcher.install_parent_watchdog(environ={}) is None

    def test_arms_from_the_parent_pid_env(self):
        watchdog = launcher.install_parent_watchdog(
            environ={launcher.PARENT_PID_ENV: "4242"}, reaper=lambda pid: None
        )
        assert watchdog is not None
        watchdog.stop()

    def test_arms_from_the_parent_pipe_fd_env(self):
        read_fd, write_fd = os.pipe()
        try:
            watchdog = launcher.install_parent_watchdog(
                environ={launcher.PARENT_PIPE_FD_ENV: str(read_fd)}, reaper=lambda pid: None
            )
            assert watchdog is not None
            watchdog.stop()
        finally:
            os.close(write_fd)
            os.close(read_fd)

    def test_ignores_a_malformed_fd(self):
        assert launcher.install_parent_watchdog(environ={launcher.PARENT_PIPE_FD_ENV: "x"}) is None

    def test_ignores_a_zero_parent_pid(self):
        # pid 0 is not a real parent; an expectation built from it would fire on
        # the very first poll and reap a healthy process.
        assert launcher.install_parent_watchdog(environ={launcher.PARENT_PID_ENV: "0"}) is None


class TestWaitUntilServing:
    """M7.4a: the host must be told the URL only once the URL actually ANSWERS.

    The Stage-2 shell cannot probe the port itself — the deny-all scan gives its
    Rust no socket at all (AC-DEPLOY-027 Layer ①) — so "the server is up" is a
    fact only the backend can report. Announcing it before uvicorn binds hands
    the native window a connection-refused page (observed, not theorised)."""

    def test_returns_true_once_the_port_is_bound(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
            held.bind(("127.0.0.1", 0))
            held.listen(1)
            port = held.getsockname()[1]
            assert launcher.wait_until_serving("127.0.0.1", port, timeout=2.0) is True

    def test_returns_false_when_nothing_ever_binds(self):
        port = _free_port()
        started = time.monotonic()
        assert launcher.wait_until_serving("127.0.0.1", port, timeout=0.3) is False
        assert time.monotonic() - started < 2.0, "the wait ignored its timeout"

    def test_port_zero_is_refused_rather_than_polled_forever(self):
        # ``--port 0`` means "let the OS choose", so the configured number is not
        # the served one: probing it would never report bound, and announcing
        # ``http://127.0.0.1:0`` would send the shell to an address that cannot
        # exist. Observed while probing the frozen bundle, not theorised.
        assert launcher.wait_until_serving("127.0.0.1", 0, timeout=5.0) is False

    def test_polls_until_the_probe_reports_the_port_taken(self):
        answers = [True, True, False]  # available, available, then bound
        assert (
            launcher.wait_until_serving(
                "127.0.0.1", 1, timeout=2.0, interval=0.0, probe=lambda h, p: answers.pop(0)
            )
            is True
        )
        assert answers == []


class TestSessionLeaderDetach:
    """M7.4a: a sidecar must be its OWN session/process-group leader so the host
    can reap the whole tree with one ``killpg`` (AC-DEPLOY-026 ①②).

    ``tauri-plugin-shell`` exposes no ``pre_exec`` hook, so the detach is done by
    the sidecar itself at start-up — gated on the same host declaration as the
    watchdog, because detaching a Stage-1 terminal launch would sever it from its
    controlling terminal and break Ctrl-C."""

    def test_a_standalone_launch_never_detaches(self):
        calls: list[int] = []
        assert (
            launcher.become_session_leader(environ={}, setsid=lambda: calls.append(1)) is False
        )
        assert calls == [], "a standalone launch detached from its terminal"

    def test_a_declared_sidecar_detaches(self):
        calls: list[int] = []
        assert (
            launcher.become_session_leader(
                environ={launcher.PARENT_PIPE_FD_ENV: "0"}, setsid=lambda: calls.append(1)
            )
            is True
        )
        assert calls == [1]

    def test_a_pid_declaration_also_detaches(self):
        calls: list[int] = []
        launcher.become_session_leader(
            environ={launcher.PARENT_PID_ENV: "4242"}, setsid=lambda: calls.append(1)
        )
        assert calls == [1]

    def test_already_a_group_leader_is_not_an_error(self):
        def _angry() -> None:
            raise PermissionError("already a process group leader")

        # setsid() fails with EPERM when the caller is already a group leader —
        # which means the goal is ALREADY met. Never fatal.
        assert (
            launcher.become_session_leader(
                environ={launcher.PARENT_PID_ENV: "4242"}, setsid=_angry
            )
            is False
        )

    def test_detach_actually_creates_a_new_session_in_a_child(self):
        # Process-level proof, not a mock: a forked child that detaches reports a
        # process-group id equal to its own pid (i.e. it leads its own group).
        repo_root = str(Path(__file__).resolve().parents[2])
        code = (
            "import os,sys;"
            f"sys.path.insert(0, {repo_root!r});"
            "from server.web.launcher import become_session_leader, PARENT_PID_ENV;"
            "become_session_leader(environ={PARENT_PID_ENV: '1234'});"
            "print(os.getpid() == os.getpgid(0))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )
        assert result.stdout.strip() == "True", result


class TestDeclaredParentPidIsCrossCheckedAgainstTheRealParent:
    """M7.4a: the host declares its OWN pid, but it may not be this process's
    DIRECT parent (a bootloader or wrapper can sit between). Trusting the
    declared value blindly would make ``ppid != expected`` true on the very
    first poll and reap a healthy backend at start-up. The declaration arms the
    watchdog; the REAL parent is what it then expects."""

    def test_a_declared_pid_that_is_not_the_real_parent_does_not_fire_at_once(self):
        reaped: list[int] = []
        watchdog = launcher.install_parent_watchdog(
            # 4242 is nobody's parent here — an intermediary stand-in.
            environ={launcher.PARENT_PID_ENV: "4242"},
            reaper=reaped.append,
        )
        assert watchdog is not None, "a declared host must still arm the watchdog"
        try:
            assert watchdog.parent_gone() is False, (
                "a mismatched declared pid reaped a healthy process on the first probe"
            )
            time.sleep(launcher.PARENT_POLL_INTERVAL_SECONDS * 2)
            assert reaped == [], reaped
        finally:
            watchdog.stop()

    def test_a_declared_pid_that_matches_the_real_parent_is_kept(self):
        watchdog = launcher.install_parent_watchdog(
            environ={launcher.PARENT_PID_ENV: str(os.getppid())}, reaper=lambda pid: None
        )
        assert watchdog is not None
        try:
            assert watchdog.parent_gone() is False
        finally:
            watchdog.stop()


class TestDeclaredPipeFdMustActuallyBeAPipe:
    """M7.4a: the host declares ``COPILOT_PARENT_PIPE_FD=0`` — its own end of the
    sidecar's stdin pipe. If that fd is NOT a pipe (a bundle handed /dev/null, a
    redirect from a regular file), it reads EOF immediately and the watchdog
    would reap a perfectly healthy backend at start-up. Validate the fd TYPE."""

    def test_a_regular_file_fd_is_not_accepted_as_the_liveness_pipe(self, tmp_path):
        path = tmp_path / "not-a-pipe"
        path.write_text("", encoding="utf-8")
        fd = os.open(path, os.O_RDONLY)
        reaped: list[int] = []
        try:
            assert launcher.is_liveness_pipe(fd) is False
            # A host DID declare itself, so the watchdog still arms — but on the
            # bounded ppid poll, never on the bogus fd.
            watchdog = launcher.install_parent_watchdog(
                environ={launcher.PARENT_PIPE_FD_ENV: str(fd)}, reaper=reaped.append
            )
            assert watchdog is not None
            assert watchdog.parent_gone() is False, "the non-pipe fd read as a dead parent"
            watchdog.stop()
            assert reaped == []
        finally:
            os.close(fd)

    def test_a_devnull_fd_is_not_accepted_as_the_liveness_pipe(self):
        fd = os.open(os.devnull, os.O_RDONLY)
        try:
            assert launcher.is_liveness_pipe(fd) is False
        finally:
            os.close(fd)

    def test_a_real_pipe_is_accepted(self):
        read_fd, write_fd = os.pipe()
        try:
            assert launcher.is_liveness_pipe(read_fd) is True
        finally:
            os.close(write_fd)
            os.close(read_fd)

    def test_a_closed_fd_is_rejected_rather_than_raising(self):
        read_fd, write_fd = os.pipe()
        os.close(write_fd)
        os.close(read_fd)
        assert launcher.is_liveness_pipe(read_fd) is False

    def test_a_non_pipe_fd_degrades_to_the_pid_poll_instead_of_reaping(self, tmp_path):
        path = tmp_path / "not-a-pipe"
        path.write_text("", encoding="utf-8")
        fd = os.open(path, os.O_RDONLY)
        reaped: list[int] = []
        try:
            watchdog = launcher.install_parent_watchdog(
                environ={
                    launcher.PARENT_PIPE_FD_ENV: str(fd),
                    launcher.PARENT_PID_ENV: str(os.getppid()),
                },
                reaper=reaped.append,
            )
            assert watchdog is not None
            # The whole point: a readable-at-EOF regular file must NOT read as
            # "parent gone" while the real parent is alive.
            assert watchdog.parent_gone() is False
            time.sleep(launcher.PARENT_POLL_INTERVAL_SECONDS * 2)
            watchdog.stop()
            assert reaped == [], "a non-pipe fd triggered a spurious self-reap"
        finally:
            os.close(fd)


# ------------------------------- sidecar self-reap, process level (AC-026 ③ / ④)

_CHILD_SCRIPT = str(Path(__file__).resolve().parent / "watchdog_child.py")

# Detection is bounded by MAX_REAP_LATENCY_SECONDS; the remainder is OS process
# teardown. Held explicit so the residual-0 scan is a bounded assertion rather
# than an open-ended race (plan §C M7.2).
_REAP_DEADLINE_SECONDS = launcher.MAX_REAP_LATENCY_SECONDS + 4.0


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _udp_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _await_status(path: Path, timeout: float = 15.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:  # pragma: no cover — atomic rename race
                pass
        time.sleep(0.05)
    raise AssertionError(f"sidecar never published {path}")


def _await_gone(pid: int, timeout: float = 10.0) -> float:
    started = time.monotonic()
    deadline = started + timeout
    while time.monotonic() < deadline and _pid_alive(pid):
        time.sleep(0.02)
    return time.monotonic() - started


def _force_cleanup(*pids: int, pgids: tuple[int, ...] = ()) -> None:
    """Last-resort teardown so a failed assertion never leaks a process.

    ``pgids`` are captured at spawn time so a group can still be reaped after its
    leader died. NEVER signals pytest's own process group — a helper that spawned
    into this group is killed by pid only.
    """
    own_pgid = os.getpgid(0)
    for pgid in pgids:
        if pgid > 0 and pgid != own_pgid:
            with contextlib.suppress(OSError):
                os.killpg(pgid, signal.SIGKILL)
    for pid in pids:
        if pid <= 0:
            continue
        with contextlib.suppress(OSError):
            pgid = os.getpgid(pid)
            if pgid != own_pgid:
                os.killpg(pgid, signal.SIGKILL)
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGKILL)


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="POSIX process-group teardown only")
class TestSidecarSelfReap:
    def test_pipe_eof_reaps_the_group_and_frees_the_ports(self, tmp_path):
        # AC-DEPLOY-026 ③ (PRIMARY trigger): the host holds the write end of the
        # liveness pipe; its death is observable as EOF with no race window.
        web_port, osc_port = _free_port(), _free_port()
        status = tmp_path / "status.json"
        read_fd, write_fd = os.pipe()
        proc = subprocess.Popen(
            [
                sys.executable,
                _CHILD_SCRIPT,
                "--mode", "sidecar",
                "--status", str(status),
                "--web-port", str(web_port),
                "--osc-port", str(osc_port),
                "--pipe-fd", str(read_fd),
            ],
            pass_fds=(read_fd,),
            start_new_session=True,  # the sidecar leads its own group
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Captured now so the group is still reapable after its leader dies.
        sidecar_pgid = os.getpgid(proc.pid)
        info = {}
        try:
            info = _await_status(status)
            assert _pid_alive(info["grandchild"])
            # AC-DEPLOY-026 ④: while the sidecar holds them, a restart is
            # fail-closed — explicit error, never a silent port drift.
            with pytest.raises(launcher.PortInUseError):
                launcher.require_ports_available([("127.0.0.1", web_port, "web UI")])

            os.close(write_fd)  # <- the "Tauri force-quit"
            write_fd = -1
            proc.wait(timeout=10)
            elapsed = _await_gone(info["grandchild"])

            assert elapsed <= _REAP_DEADLINE_SECONDS
            assert not _pid_alive(info["grandchild"]), "grandchild survived the self-reap"
            assert launcher.probe_port_available("127.0.0.1", web_port)
            assert _udp_port_free(osc_port)
            launcher.require_ports_available(
                [
                    ("127.0.0.1", web_port, "web UI"),
                    ("127.0.0.1", osc_port, "OSC feedback listen"),
                ]
            )
        finally:
            if write_fd >= 0:
                os.close(write_fd)
            os.close(read_fd)
            _force_cleanup(
                proc.pid, info.get("grandchild", 0), pgids=(sidecar_pgid,)
            )

    def test_orphaned_sidecar_reaps_the_group_without_a_pipe(self, tmp_path):
        # AC-DEPLOY-026 ③ (FALLBACK trigger): no pipe channel — the sidecar is
        # orphaned to init when its parent is force-killed and must still reap.
        web_port, osc_port = _free_port(), _free_port()
        status = tmp_path / "status.json"
        parent = subprocess.Popen(
            [
                sys.executable,
                _CHILD_SCRIPT,
                "--mode", "parent",
                "--status", str(status),
                "--web-port", str(web_port),
                "--osc-port", str(osc_port),
            ],
            start_new_session=True,  # keep the helper out of pytest's own group
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        info = {}
        try:
            info = _await_status(status)
            assert _pid_alive(info["pid"])
            assert _pid_alive(info["grandchild"])

            parent.kill()  # SIGKILL — no chance to clean up (force-quit)
            parent.wait(timeout=10)

            elapsed = _await_gone(info["pid"])
            elapsed += _await_gone(info["grandchild"])
            assert elapsed <= _REAP_DEADLINE_SECONDS
            assert not _pid_alive(info["pid"]), "orphaned sidecar did not self-reap"
            assert not _pid_alive(info["grandchild"]), "grandchild survived the self-reap"
            assert launcher.probe_port_available("127.0.0.1", web_port)
            assert _udp_port_free(osc_port)
        finally:
            # The parent records the sidecar pid at spawn, so cleanup works even
            # when the sidecar never published its own status.
            recorded = Path(str(status) + ".parent")
            spawned = 0
            if recorded.exists():
                with contextlib.suppress(json.JSONDecodeError, OSError):
                    spawned = json.loads(recorded.read_text(encoding="utf-8"))["sidecar"]
            _force_cleanup(
                parent.pid, info.get("pid", 0), info.get("grandchild", 0), spawned
            )
