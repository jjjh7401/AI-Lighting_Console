"""Sidecar stand-in for the M7.2 parent-liveness watchdog process tests.

NOT a test module (no ``test_`` prefix — pytest does not collect it). It is
spawned as a real subprocess so AC-DEPLOY-026 ③ can be proven at the process
level: a sidecar whose parent dies must reap its own process GROUP (itself +
extracted-Python grandchildren) and free the web / OSC ports.

Two modes:

* ``--mode sidecar`` — bind the web (TCP) + OSC (UDP) ports, spawn a long-lived
  grandchild in the SAME process group, arm the watchdog, then idle.
* ``--mode parent`` — the Tauri stand-in: spawn a sidecar in its OWN session
  (``start_new_session=True``, mirroring the planned Rust ``pre_exec``
  setsid/setpgid) and idle until force-killed, so the sidecar is orphaned.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# A grandchild that outlives the test unless the GROUP teardown reaches it.
_GRANDCHILD_CODE = "import time; time.sleep(300)"


def _write_status(path: str, payload: dict[str, int]) -> None:
    """Publish the pid map atomically (the test never reads a partial file)."""
    target = Path(path)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(target)


def _run_sidecar(args: argparse.Namespace) -> int:
    from server.web import launcher

    # Build the watchdog BEFORE anything is spawned: a construction failure must
    # not be able to strand a grandchild.
    watchdog = launcher.ParentLivenessWatchdog(
        pipe_fd=args.pipe_fd if args.pipe_fd >= 0 else None,
        expected_ppid=args.parent_pid if args.parent_pid > 0 else None,
    )

    web = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    web.bind(("127.0.0.1", args.web_port))
    web.listen(8)
    osc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    osc.bind(("127.0.0.1", args.osc_port))

    grandchild = subprocess.Popen([sys.executable, "-c", _GRANDCHILD_CODE])
    try:
        watchdog.start()
        _write_status(args.status, {"pid": os.getpid(), "grandchild": grandchild.pid})
        while True:  # the watchdog is the only exit path
            time.sleep(0.2)
    finally:  # any crash here reaps the grandchild instead of stranding it
        grandchild.kill()
        grandchild.wait(timeout=5)


def _run_parent(args: argparse.Namespace) -> int:
    child = subprocess.Popen(
        [
            sys.executable,
            __file__,
            "--mode",
            "sidecar",
            "--status",
            args.status,
            "--web-port",
            str(args.web_port),
            "--osc-port",
            str(args.osc_port),
            "--parent-pid",
            str(os.getpid()),
        ],
        start_new_session=True,  # the sidecar leads its own group (Rust setsid)
    )
    # Recorded immediately so the test can reap the sidecar even if the sidecar
    # itself never gets far enough to publish its own status.
    _write_status(args.status + ".parent", {"sidecar": child.pid})
    while True:  # idle until force-killed; the sidecar must notice on its own
        time.sleep(0.2)
    return child.returncode  # pragma: no cover — unreachable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("sidecar", "parent"), default="sidecar")
    parser.add_argument("--status", required=True)
    parser.add_argument("--web-port", type=int, required=True)
    parser.add_argument("--osc-port", type=int, required=True)
    parser.add_argument("--pipe-fd", type=int, default=-1)
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args(argv)
    if args.mode == "parent":
        return _run_parent(args)
    return _run_sidecar(args)


if __name__ == "__main__":
    raise SystemExit(main())
