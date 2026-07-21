"""Sidecar -> host stdout channel (M7.4a — REQ-DEPLOY-001/002, AC-DEPLOY-024).

When the Stage-2 Tauri shell spawns this backend as a sidecar it needs three facts
back, and it may not obtain any of them over a socket: the deny-all Rust scan
(``packaging/rust_scan.py`` / AC-DEPLOY-027 Layer ①) forbids the shell any raw
socket, any networking crate and any loopback/console-port literal. The shell's
ONLY legitimate inbound channel is the sidecar's piped **stdout**:

* :data:`READY_PREFIX` + the served loopback URL — the address the native window
  navigates to. Runtime-supplied, so a reconfigured port (REQ-DEPLOY-005/026)
  moves the window with it instead of desyncing from a compile-time literal.
* :data:`STATUS_PREFIX` + the gate-truth health (``online`` / ``console_offline``
  / ``responder_degraded`` — the M5 states) — the tray badge's source.
* :data:`ERROR_PREFIX` + the reason a start-up that never served is giving up —
  the start-up dialog's text. Without it the shell must GUESS why a backend that
  never reported ready died, and a guess is hardcoded: it blamed an incomplete
  runtime payload even when the real cause was an occupied port.

Design constraints this module encodes:

* **One line per fact, flushed.** A pipe to the host is block-buffered; an
  unflushed ready line strands the shell on a window it never opens.
* **Newlines are stripped from payloads.** The channel is line-oriented, so an
  embedded newline in a value would forge a second protocol line.
* **Never fatal.** A windowed PyInstaller bundle may hand the process a ``None``
  stdout, and a host that exits first turns every write into ``BrokenPipeError``.
  Neither may take the server down — the parent-liveness watchdog
  (``server.web.launcher``) owns that teardown, not a stray write error.

No secrets cross this channel: the per-launch handshake token is NOT emitted here
(AC-DEPLOY-029 — stdout is inherited by the host and readable in a crash dump).
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TextIO

# Prefixes are deliberately distinct and neither is a prefix of the other, so the
# host's line parser needs no lookahead. The ``@copilot:`` namespace keeps them
# from colliding with uvicorn / library log lines on the same stream.
READY_PREFIX = "@copilot:ready "
STATUS_PREFIX = "@copilot:status "
ERROR_PREFIX = "@copilot:error "

# Sentinel for "resolve ``sys.stdout`` at CALL time". Binding the module-level
# ``sys.stdout`` as a default would freeze whichever stream existed at import,
# which is both wrong under a redirect and untestable under captured output.
# An explicit ``out=None`` still means "no stream" (the windowed-bundle case).
_USE_STDOUT: TextIO = object()  # type: ignore[assignment]


def _resolve(out: TextIO | None) -> TextIO | None:
    return sys.stdout if out is _USE_STDOUT else out


def _emit(prefix: str, payload: str, out: TextIO | None) -> None:
    """Write one prefixed, flushed protocol line; never raise."""
    out = _resolve(out)
    if out is None:
        return
    # Line-oriented channel: a payload newline would forge a second line.
    flat = payload.replace("\r", " ").replace("\n", " ")
    try:
        out.write(f"{prefix}{flat}\n")
        out.flush()
    except Exception:  # host gone / stream closed — the watchdog owns teardown
        return


def emit_ready(url: str, *, out: TextIO | None = _USE_STDOUT) -> None:
    """Tell the spawning host which URL the native window should load."""
    _emit(READY_PREFIX, url, out)


def emit_status(health: str, *, out: TextIO | None = _USE_STDOUT) -> None:
    """Tell the spawning host the current gate-truth health state."""
    _emit(STATUS_PREFIX, health, out)


def emit_startup_error(cause: str, *, out: TextIO | None = _USE_STDOUT) -> None:
    """Tell the spawning host WHY a start-up that never served is giving up.

    Emitted BEFORE the process exits, because the host's ``Terminated`` event
    carries only an exit payload. Without this the shell can only guess at the
    cause of a start-up failure — and its guess was hardcoded to an incomplete
    runtime payload, which misdiagnoses the commonest real cause (a port still
    held by an abnormally-exited prior instance) as a broken installation.

    Carries operator guidance, never a secret: same stream, same
    AC-DEPLOY-029 constraint as the other two lines.
    """
    _emit(ERROR_PREFIX, cause, out)


def make_status_emitter(
    read_health: Callable[[], str], *, out: TextIO | None = _USE_STDOUT
) -> Callable[[], None]:
    """Build a no-arg listener for ``WebDeps.status_listeners``.

    Health is read at CALL time (the listener is notified on change, not handed
    a value), and a read failure is swallowed: a status push must never break the
    heartbeat loop that drives it.
    """

    def _notify() -> None:
        try:
            health = read_health()
        except Exception:
            return
        emit_status(health, out=out)

    return _notify
