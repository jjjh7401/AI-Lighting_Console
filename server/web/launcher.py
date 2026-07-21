"""Packaged-app launcher primitives (M6 — REQ-DEPLOY-001~003/006/006a/025/026).

Process-start behaviours the double-click / frozen binary needs, factored into
small, dependency-injectable functions so the fail paths are unit-testable in the
dev venv WITHOUT touching the real Keychain or binding real service ports:

* **browser open** at the served loopback URL (stdlib :mod:`webbrowser`),
  suppressible for headless / test runs (REQ-DEPLOY-001~003);
* **port-in-use fail-loud** — an occupied web/OSC port raises
  :class:`PortInUseError` with reconfiguration guidance; NEVER a silent fallback
  to a random port (AC-DEPLOY-015 ② / REQ-DEPLOY-026);
* **graceful process-TREE shutdown** — tear down the console stack (OSC listeners
  / timers) AND any spawned child + grandchild processes on normal exit and on
  SIGINT / SIGTERM (AC-DEPLOY-015 ① / research §E, FEAS-5);
* **keyring backend pin + fail-closed guard** — pin ``PYTHON_KEYRING_BACKEND`` and
  refuse to boot on the wrong backend (research §B.3 / REQ-DEPLOY-006a);
* **``--self-check``** — the frozen keyring roundtrip (research §B.4). The REAL
  roundtrip runs inside the PACKAGED binary (``dist/<app>/<app> --self-check``),
  not this dev-venv suite — the dev venv has real metadata and would pass even
  when a bundle is broken (the FEAS-2 false-negative).
"""

from __future__ import annotations

import contextlib
import os
import secrets
import select
import signal
import socket
import sys
import threading
import webbrowser
from collections.abc import Callable, Iterable, MutableMapping
from typing import TextIO

# ------------------------------------------------- per-launch token (M7.1, 002a)

# The env var the token crosses a process boundary in — the Stage-2 Tauri host
# generates it and hands it to the sidecar it spawns; the sidecar reads it here.
# The name deliberately contains "TOKEN" so ``keystore.scrub_environ`` redacts it
# from any crash dump / diagnostic that serialises the environment (AC-DEPLOY-029,
# the same leak vector DECIDE-M6 closed for API keys).
LAUNCH_TOKEN_ENV = "COPILOT_LAUNCH_TOKEN"
# 32 bytes of entropy -> a 43-char urlsafe string. Unguessable within a launch.
_LAUNCH_TOKEN_BYTES = 32


def generate_launch_token() -> str:
    """Mint a fresh unguessable per-launch handshake token (REQ-DEPLOY-002a).

    Memory/env only — NEVER written to disk (AC-DEPLOY-029). A new value per
    launch means a token captured from one run is useless against the next.
    """
    return secrets.token_urlsafe(_LAUNCH_TOKEN_BYTES)

# ------------------------------------------------------------------ keyring (B.3)

KEYRING_BACKEND_ENV = "PYTHON_KEYRING_BACKEND"
# The exact macOS backend class path (research §B.3). Pinning it forces keyring to
# load THIS backend or fail at load, rather than silently degrade to a null /
# plaintext-file backend in a frozen bundle whose entry-point metadata was stripped.
PINNED_KEYRING_BACKEND = "keyring.backends.macOS.Keyring"
# The backend module (NOT class name) the app requires. Discriminate on
# ``__module__`` ONLY: the correct macOS backend class is literally named
# ``Keyring`` — so are ``fail.Keyring`` and ``SecretService.Keyring`` — so a
# ``__name__`` check both rejects the right backend and cannot tell them apart.
EXPECTED_KEYRING_MODULE = "keyring.backends.macOS"

# --self-check probe identifiers (research §B.4).
SELF_CHECK_SERVICE = "grandma3-copilot-selfcheck"
SELF_CHECK_ACCOUNT = "probe"
SELF_CHECK_SENTINEL = "sentinel-v1"


def _import_keyring():
    # Lazy import so the backend-selection ordering is deterministic: the env pin
    # (apply_keyring_backend_pin) can be applied BEFORE keyring is first imported.
    import keyring

    return keyring


def apply_keyring_backend_pin(environ: MutableMapping[str, str] | None = None) -> None:
    """Pin ``PYTHON_KEYRING_BACKEND`` to the macOS backend (setdefault semantics).

    ``setdefault`` — an explicit operator override in the environment is preserved.
    Must run at process start, BEFORE the first ``keyring.get_keyring()`` backend
    selection (research §B.3).
    """
    target = os.environ if environ is None else environ
    target.setdefault(KEYRING_BACKEND_ENV, PINNED_KEYRING_BACKEND)


def assert_keyring_backend(*, keyring_module=None) -> None:
    """Fail-closed guard: raise unless the active keyring backend is the OS store.

    Discriminates on ``type(backend).__module__`` only (research §B.3). Raises
    :class:`RuntimeError` (REQ-DEPLOY-006a message — no plaintext fallback) when
    the backend module is anything other than :data:`EXPECTED_KEYRING_MODULE`
    (fail backend, leaked ``keyrings.alt`` file backend, bare chainer, ...).
    """
    kr = keyring_module if keyring_module is not None else _import_keyring()
    backend = kr.get_keyring()
    if type(backend).__module__ != EXPECTED_KEYRING_MODULE:
        raise RuntimeError(
            "OS credential store unavailable — refusing to start "
            "(REQ-DEPLOY-006a: no plaintext fallback)"
        )


def run_self_check(*, keyring_module=None, out: TextIO | None = None) -> int:
    """Run the frozen keyring roundtrip self-check; return 0 on pass, nonzero fail.

    Verifies (research §B.4) the backend TYPE first (a leaked file backend would
    pass a naive roundtrip while writing plaintext), then a set -> get -> delete ->
    get(None) roundtrip. Any failure returns nonzero. Intended to run inside the
    PACKAGED binary (``--self-check``).
    """
    stream = out if out is not None else sys.stderr
    kr = keyring_module if keyring_module is not None else _import_keyring()
    try:
        backend_module = type(kr.get_keyring()).__module__
        if backend_module != EXPECTED_KEYRING_MODULE:
            print(
                f"self-check FAIL: keyring backend {backend_module!r} is not "
                f"{EXPECTED_KEYRING_MODULE!r} (no OS credential store)",
                file=stream,
            )
            return 1
        kr.set_password(SELF_CHECK_SERVICE, SELF_CHECK_ACCOUNT, SELF_CHECK_SENTINEL)
        got = kr.get_password(SELF_CHECK_SERVICE, SELF_CHECK_ACCOUNT)
        if got != SELF_CHECK_SENTINEL:
            print(f"self-check FAIL: keyring roundtrip mismatch ({got!r})", file=stream)
            return 1
        kr.delete_password(SELF_CHECK_SERVICE, SELF_CHECK_ACCOUNT)
        after = kr.get_password(SELF_CHECK_SERVICE, SELF_CHECK_ACCOUNT)
        if after is not None:
            print(f"self-check FAIL: probe key not deleted ({after!r})", file=stream)
            return 1
    except Exception as error:  # any keyring failure = self-check fail (not a crash)
        print(f"self-check FAIL: {error}", file=stream)
        return 1
    print("self-check OK: macOS keyring backend + roundtrip verified", file=stream)
    return 0


# ----------------------------------------------------------- port-in-use (025/026)


class PortInUseError(RuntimeError):
    """A required web / OSC port is already in use.

    Carries human-readable reconfiguration ``guidance`` — the launcher surfaces
    this and exits rather than silently falling back to a random port
    (REQ-DEPLOY-026 / AC-DEPLOY-015 ②).
    """

    def __init__(self, host: str, port: int, label: str) -> None:
        self.host = host
        self.port = port
        self.label = label
        self.guidance = (
            f"포트 {port}({label}, {host})가 이미 사용 중입니다. "
            f"다른 프로세스를 종료하거나 설정(Settings)에서 포트를 변경한 뒤 다시 시작하세요. "
            f"(Port {port} for '{label}' is in use — free it or reconfigure the "
            f"port in Settings, then restart. No automatic port fallback.)"
        )
        super().__init__(
            f"port {port} for {label!r} on {host} is already in use"
        )


def probe_port_available(host: str, port: int) -> bool:
    """Return True when ``host:port`` can be bound (i.e. is free) for TCP."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def require_ports_available(specs: Iterable[tuple[str, int, str]]) -> None:
    """Raise :class:`PortInUseError` for the first occupied fixed port.

    ``specs`` are ``(host, port, label)`` triples. Port ``0`` means "let the OS
    assign a free port" and is skipped (nothing fixed to pre-check).
    """
    for host, port, label in specs:
        if port == 0:
            continue
        if not probe_port_available(host, port):
            raise PortInUseError(host, port, label)


# ---------------------------------------------------------------- browser open


def serve_local_url(host: str, port: int) -> str:
    """Build the loopback URL to open — a bind-all host maps to 127.0.0.1."""
    display_host = "127.0.0.1" if host in ("", "0.0.0.0", "::") else host
    return f"http://{display_host}:{port}"


def open_app_browser(
    url: str,
    *,
    enabled: bool,
    opener: Callable[[str], object] = webbrowser.open,
) -> bool:
    """Open ``url`` in the default browser when ``enabled``; never raise.

    Returns True when the open was attempted and did not raise. A headless / no
    -browser environment (or a suppressed run) returns False without crashing the
    launcher.
    """
    if not enabled:
        return False
    try:
        opener(url)
    except Exception:  # headless / no display — the server still runs
        return False
    return True


# -------------------------------------------------- graceful process-tree teardown


def terminate_process_tree(pid: int, *, timeout: float = 5.0) -> None:
    """Terminate ``pid`` and every descendant (process TREE, not just ``pid``).

    POSIX: ``pid`` is expected to be a process-group leader (spawn children with
    ``start_new_session=True``); the whole group is signalled SIGTERM, then
    SIGKILL after ``timeout`` — reaping extracted grandchild processes so no
    Python zombie / port squatter survives (AC-DEPLOY-015 ① / research §E). On a
    platform without ``os.killpg`` the single ``pid`` is terminated best-effort.
    """
    if not hasattr(os, "killpg"):  # pragma: no cover — non-POSIX best-effort
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGTERM)
        return

    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return

    def _group_alive() -> bool:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:  # pragma: no cover — group exists, not ours
            return True
        return True

    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return

    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and _group_alive():
        time.sleep(0.05)

    if _group_alive():  # escalate — a wedged tree does not get to squat the port
        # Best-effort: a reparented/zombie group member can raise EPERM; teardown
        # must never propagate an OS signal error.
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(pgid, signal.SIGKILL)


def make_shutdown_handler(
    stack,
    *,
    exit_fn: Callable[[int], object] = sys.exit,
    child_pids: Iterable[int] = (),
    tree_terminator: Callable[[int], object] = terminate_process_tree,
) -> Callable[..., None]:
    """Build a SIGINT/SIGTERM handler that tears down the stack + child trees.

    Guarantees the child process trees are reaped and the process exits even if
    ``stack.stop()`` raises (a failed OSC-listener teardown must not leave
    grandchildren squatting the console port).
    """
    pids = tuple(child_pids)

    def _handler(signum=None, frame=None) -> None:  # noqa: ARG001 — signal signature
        try:
            stack.stop()
        except Exception:  # teardown best-effort — still reap children + exit
            pass
        finally:
            for pid in pids:
                tree_terminator(pid)
            exit_fn(0)

    return _handler


def install_signal_handlers(
    handler: Callable[..., None],
    *,
    register: Callable[[int, Callable[..., None]], object] = signal.signal,
) -> None:
    """Register ``handler`` for SIGINT and SIGTERM (graceful shutdown on signal)."""
    register(signal.SIGINT, handler)
    register(signal.SIGTERM, handler)


# --------------------------------------- parent-liveness watchdog (M7.2, 025/026)

# The inherited read-end fd of the host's liveness pipe (PRIMARY trigger). The
# Stage-2 Tauri host opens the pipe, keeps the write end for its own lifetime and
# passes the read end down to the sidecar.
PARENT_PIPE_FD_ENV = "COPILOT_PARENT_PIPE_FD"
# The spawning host's own pid (FALLBACK trigger). Set by a host that cannot hand
# down a pipe; it is ALSO what marks this process as a sidecar at all.
PARENT_PID_ENV = "COPILOT_PARENT_PID"

# Upper bound on how long a dead parent may go unnoticed (plan §C M7.2): the
# residual-0 scan after a force-quit must be bounded-deterministic, not a race.
MAX_REAP_LATENCY_SECONDS = 1.0
# Fallback poll period. Constrained to <= MAX_REAP_LATENCY_SECONDS at construction.
PARENT_POLL_INTERVAL_SECONDS = 0.25

# POSIX re-parents an orphan to init; a ppid of 1 means the spawner is gone.
_INIT_PID = 1
_PIPE_READ_CHUNK = 4096


class ParentLivenessWatchdog:
    # @MX:ANCHOR: [AUTO] sidecar self-reap boundary — the only path that tears
    #   this process GROUP down without a signal from the parent.
    # @MX:REASON: A Unix force-quit of the Tauri host never fires
    #   ``RunEvent::Exit``, so the Rust authoritative group-kill cannot run; if
    #   this trigger is wrong the extracted-Python grandchildren survive and
    #   squat the web / OSC ports, and the next launch fails
    #   ``require_ports_available``. Inverse hazard: arming it on a standalone
    #   launch (whose parent may legitimately be launchd, pid 1) would reap a
    #   healthy server — hence the host-declaration gate in
    #   :func:`install_parent_watchdog`.
    # @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-025 / AC-DEPLOY-026 ③
    """Reap this process group once the spawning host dies (FEAS-5 Option C).

    Two triggers, both bounded by :data:`MAX_REAP_LATENCY_SECONDS`:

    * **PRIMARY — pipe EOF.** The host holds the write end of ``pipe_fd`` for its
      own lifetime, so ANY death (normal exit, crash, force-quit) closes the last
      write end and makes the read end readable-at-EOF *immediately* — no race
      window and no polling. A non-empty read is a heartbeat: the host lives.
    * **FALLBACK — ``getppid()`` polling.** Where no pipe was inherited, or the
      inherited fd goes bad, a poll no wider than
      :data:`PARENT_POLL_INTERVAL_SECONDS` detects the re-parent away from
      ``expected_ppid`` (to init, pid 1).

    On either trigger it calls ``reaper(pid)`` — by default
    :func:`terminate_process_tree` against its OWN pid, i.e. SIGTERM-then-SIGKILL
    over this process GROUP. The SIGTERM arrives at this process too, so the
    installed :func:`make_shutdown_handler` still stops the console stack BEFORE
    the group teardown completes: the graceful ordering is unchanged, only its
    trigger is new.
    """

    def __init__(
        self,
        *,
        pipe_fd: int | None = None,
        expected_ppid: int | None = None,
        poll_interval: float = PARENT_POLL_INTERVAL_SECONDS,
        reaper: Callable[[int], object] = terminate_process_tree,
        getppid: Callable[[], int] = os.getppid,
        pid: int | None = None,
    ) -> None:
        if not 0 < poll_interval <= MAX_REAP_LATENCY_SECONDS:
            raise ValueError(
                f"poll_interval must be within (0, {MAX_REAP_LATENCY_SECONDS}] seconds "
                "so the post-force-quit residual scan stays bounded"
            )
        if pipe_fd is None and expected_ppid is None:
            raise ValueError(
                "watchdog needs a parent pipe fd or an expected parent pid — "
                "a launch with no declared host must never self-reap"
            )
        self._pipe_fd = pipe_fd
        self._expected_ppid = expected_ppid
        self._poll_interval = poll_interval
        self._reaper = reaper
        self._getppid = getppid
        self._pid = os.getpid() if pid is None else pid
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.triggered = threading.Event()

    def parent_gone(self) -> bool:
        """One non-blocking liveness probe; True once the host is gone."""
        if self._pipe_fd is not None:
            try:
                ready, _, _ = select.select([self._pipe_fd], [], [], 0)
            except (OSError, ValueError):  # inherited fd went bad -> fall back
                self._pipe_fd = None
            else:
                if ready:
                    try:
                        chunk = os.read(self._pipe_fd, _PIPE_READ_CHUNK)
                    except OSError:
                        return True
                    if not chunk:  # EOF — every write end closed
                        return True
        if self._expected_ppid is None:
            return False
        ppid = self._getppid()
        return ppid == _INIT_PID or ppid != self._expected_ppid

    def run(self) -> None:
        """Watch until the host dies (then reap) or :meth:`stop` is called."""
        while not self._stop.is_set():
            if self.parent_gone():
                self.triggered.set()
                self._reaper(self._pid)
                return
            self._wait_tick()

    def _wait_tick(self) -> None:
        # Block on the pipe when there is one so EOF wakes us at once; otherwise
        # sleep exactly one bounded poll period.
        if self._pipe_fd is not None:
            try:
                select.select([self._pipe_fd], [], [], self._poll_interval)
                return
            except (OSError, ValueError):
                self._pipe_fd = None
        self._stop.wait(self._poll_interval)

    def start(self) -> None:
        """Run the watch loop on a daemon thread (never blocks shutdown)."""
        thread = threading.Thread(
            target=self.run, name="parent-liveness-watchdog", daemon=True
        )
        self._thread = thread
        thread.start()

    def stop(self, *, timeout: float | None = None) -> None:
        """Stop watching; joins within roughly one poll period."""
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(self._poll_interval * 4 if timeout is None else timeout)


def _parse_int(raw: str | None, *, minimum: int) -> int | None:
    """Parse a host-declared integer; None when absent, malformed or too small."""
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= minimum else None


def install_parent_watchdog(
    *,
    environ: MutableMapping[str, str] | None = None,
    **kwargs,
) -> ParentLivenessWatchdog | None:
    """Arm + start the watchdog when a host declared itself; else return None.

    The declaration (``COPILOT_PARENT_PIPE_FD`` / ``COPILOT_PARENT_PID``) is what
    distinguishes a Stage-2 sidecar from a Stage-1 standalone launch. A
    double-clicked Stage-1 app is parented by launchd (pid 1) and a terminal
    launch can be orphaned by a closing shell — arming there would reap a healthy
    server, so an undeclared launch is left completely untouched.
    """
    source = os.environ if environ is None else environ
    pipe_fd = _parse_int(source.get(PARENT_PIPE_FD_ENV), minimum=0)
    # A pid of 0 is not a real parent — an expectation built from it would fire
    # on the first poll.
    expected_ppid = _parse_int(source.get(PARENT_PID_ENV), minimum=1)
    if pipe_fd is None and expected_ppid is None:
        return None
    if expected_ppid is None:
        # Keep a fallback for a pipe that goes bad mid-run — but only when this
        # process actually has a real parent to miss.
        current_ppid = os.getppid()
        expected_ppid = current_ppid if current_ppid != _INIT_PID else None
    watchdog = ParentLivenessWatchdog(pipe_fd=pipe_fd, expected_ppid=expected_ppid, **kwargs)
    watchdog.start()
    return watchdog
