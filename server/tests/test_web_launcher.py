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

import os
import socket
import subprocess
import sys
import time

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
