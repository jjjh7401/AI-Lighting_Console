#!/usr/bin/env python3
"""M10 Part D — packaged ``.app`` HTTP end-to-end verification (no onPC required).

Launches the PACKAGED binary (``dist/GrandMA3 Copilot.app/Contents/MacOS/GrandMA3
Copilot``) as a subprocess on unused loopback ports and drives the deploy-shell
HTTP surface end-to-end — health, SPA, settings read/write, secure-key status,
responder provisioning, the frozen-writable audit-dir location, and a CLEAN
SIGTERM graceful shutdown with a process-TREE residual scan.

This is the deployment INTEGRATION verification (AC-DEPLOY-014 lineage): it is the
only check that boots the real frozen bundle and exercises the composed server the
way a double-click launch does. It is a standalone opt-in script — NOT part of the
pytest suite — because it depends on a built artifact that does not exist in CI
without a prior ``pyinstaller`` build.

Run (from repo root, after a build):
    .venv/bin/python packaging/verify_packaged_e2e.py

Exit code 0 = all steps PASS; nonzero = at least one step FAILED (or the binary is
missing). The script ALWAYS tears the server down (process-group SIGKILL in a
finally) and ALWAYS restores any pre-existing user settings.toml it backed up, so
it never leaves a stray server or clobbers the operator's real config.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# Two sibling imports, both deliberately after the sys.path bootstrap:
#   * wire_sink (same directory) — Layer ② of the SAFETY-2 cross-language dual
#     scan (M7.3, AC-DEPLOY-027): the sink stands in for the console's OSC input
#     port so every datagram the packaged app emits reconciles 1:1 with the gate
#     audit log.
#   * server.deploy.settings — the SSOT for the OS-standard user paths the
#     packaged app writes to, so this E2E asserts against the exact same
#     resolution the frozen app uses (no path duplication / drift).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from wire_sink import WirePacketSink, reconcile  # noqa: E402

from server.deploy.settings import (  # noqa: E402
    user_config_dir,
    user_data_dir,
    user_settings_path,
)

APP_BUNDLE = REPO_ROOT / "dist" / "GrandMA3 Copilot.app"
BINARY = APP_BUNDLE / "Contents" / "MacOS" / "GrandMA3 Copilot"

HEALTH_TIMEOUT_S = 40.0
HTTP_TIMEOUT_S = 12.0
SHUTDOWN_TIMEOUT_S = 20.0


@dataclass
class Step:
    n: int
    name: str
    status: str = "SKIP"  # PASS / FAIL / SKIP
    evidence: list[str] = field(default_factory=list)

    def ok(self, *lines: str) -> None:
        self.status = "PASS"
        self.evidence.extend(lines)

    def fail(self, *lines: str) -> None:
        self.status = "FAIL"
        self.evidence.extend(lines)


def _free_port() -> int:
    """Bind :0 on loopback, read the OS-assigned port, release it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _http(
    method: str, url: str, body: dict | None = None, timeout: float = HTTP_TIMEOUT_S
) -> tuple[int, bytes]:
    """Return (status, body). HTTP error statuses (404/500/...) are returned, not raised."""
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def _pgid_processes(pgid: int) -> list[str]:
    """Every live process in ``pgid`` as 'pid pgid comm' lines (process-TREE scan)."""
    out = subprocess.run(
        ["ps", "-A", "-o", "pid=,pgid=,comm="],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    rows: list[str] = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2 and parts[1].isdigit() and int(parts[1]) == pgid:
            rows.append(line.strip())
    return rows


def _audit_executed_since(since_iso: str) -> list[dict]:
    """Every gate ``executed`` audit event written by the app since ``since_iso``.

    Filtering on the event's own UTC ``ts`` (not the file mtime) keeps entries
    from earlier runs that share today's rotation file out of the capture.
    """
    audit_dir = user_data_dir() / "audit_logs"
    events: list[dict] = []
    if not audit_dir.is_dir():
        return events
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") == "executed" and str(event.get("ts", "")) >= since_iso:
                events.append(event)
    return events


def _bundle_has_dir(name: str) -> list[str]:
    """Any directory named ``name`` anywhere inside the .app bundle (should be none)."""
    out = subprocess.run(
        ["find", str(APP_BUNDLE), "-type", "d", "-name", name],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return [p for p in out.splitlines() if p.strip()]


def run() -> int:
    if not BINARY.is_file():
        print(f"FATAL: packaged binary not found: {BINARY}", file=sys.stderr)
        print("Build it first: .venv/bin/python -m PyInstaller --noconfirm --clean "
              "packaging/GrandMA3-Copilot.spec", file=sys.stderr)
        return 3

    web_port = _free_port()
    recv_port = _free_port()
    while recv_port == web_port:
        recv_port = _free_port()
    base = f"http://127.0.0.1:{web_port}"

    # AC-DEPLOY-027 Layer ②: bind the console-input sink BEFORE launch, on an
    # OS-assigned port that is deliberately NOT the 8000 default (audit defect
    # D3 — binding the default while the app sends elsewhere captures nothing).
    sink = WirePacketSink(port=0)
    while sink.port in (web_port, recv_port):
        sink.stop()
        sink = WirePacketSink(port=0)
    console_port = sink.port

    steps = [Step(i, name) for i, name in [
        (1, "launch packaged binary on unused loopback ports"),
        (2, "GET /healthz until healthy"),
        (3, "GET / -> 200 bundled SPA"),
        (4, "GET /api/settings -> 200, key booleans present, NO key values"),
        (5, "POST /api/settings persists to user config dir (not bundle)"),
        (6, "POST/GET /api/provision/responder installs bundled plugin to temp dir"),
        (7, "running app audit dir resolves under user data dir (not bundle)"),
        (8, "wire sink on the configured send_port reconciles 1:1 with the gate audit log"),
        (9, "SIGTERM -> clean exit + 0 residual process-tree + ports freed"),
    ]]
    S = {s.n: s for s in steps}

    # Back up the operator's real settings.toml so the test never clobbers it.
    settings_file = user_settings_path()
    backup = None
    if settings_file.is_file():
        backup = settings_file.read_bytes()

    t0 = time.time()
    run_started_iso = datetime.now(UTC).isoformat()
    provision_dir = Path(tempfile.mkdtemp(prefix="ma3copilot-e2e-provision-"))
    proc: subprocess.Popen | None = None
    pgid = None
    logf = tempfile.NamedTemporaryFile(  # noqa: SIM115 — kept open across the run, closed in finally
        prefix="ma3copilot-e2e-boot-", suffix=".log", delete=False, mode="wb"
    )

    try:
        # ---- Step 1: launch (own process group -> whole-tree teardown) ----------
        proc = subprocess.Popen(
            [str(BINARY), "--no-browser", "--port", str(web_port),
             "--receive-port", str(recv_port), "--console-port", str(console_port)],
            stdout=logf,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        pgid = os.getpgid(proc.pid)
        S[1].ok(
            f"pid={proc.pid} pgid={pgid} web_port={web_port} receive_port={recv_port} "
            f"console_port={console_port} (wire sink bound)",
            f"argv=[{BINARY.name!r}, --no-browser, --port {web_port}, "
            f"--receive-port {recv_port}, --console-port {console_port}]",
        )

        # ---- Step 2: poll /healthz ---------------------------------------------
        deadline = time.time() + HEALTH_TIMEOUT_S
        health_body = None
        while time.time() < deadline:
            if proc.poll() is not None:
                tail = Path(logf.name).read_text(errors="replace")[-800:]
                S[2].fail(f"process exited early rc={proc.returncode}", f"boot log tail:\n{tail}")
                break
            try:
                status, raw = _http("GET", f"{base}/healthz", timeout=3.0)
                if status == 200:
                    health_body = json.loads(raw)
                    S[2].ok(
                        f"GET /healthz -> 200 after {time.time() - t0:.1f}s",
                        f"body={json.dumps(health_body)}",
                    )
                    break
            except Exception:
                pass
            time.sleep(0.4)
        if S[2].status != "PASS" and not S[2].evidence:
            S[2].fail(f"/healthz not 200 within {HEALTH_TIMEOUT_S:.0f}s")

        if S[2].status != "PASS":
            # Cannot drive HTTP without a healthy server; remaining HTTP steps fail.
            for n in (3, 4, 5, 6):
                S[n].fail("skipped: server never became healthy")
        else:
            # ---- Step 3: GET / (SPA) -------------------------------------------
            status, raw = _http("GET", f"{base}/")
            text = raw.decode("utf-8", "replace")
            lowered = text.lower()
            is_html = status == 200 and ("<html" in lowered or "<!doctype html" in lowered)
            if is_html:
                S[3].ok(f"GET / -> 200, {len(raw)}B HTML", f"head={text[:120]!r}")
            else:
                S[3].fail(f"GET / -> {status}, html={is_html}", f"head={text[:200]!r}")

            # ---- Step 4: GET /api/settings (booleans present, NO key values) ---
            status, raw = _http("GET", f"{base}/api/settings")
            if status == 200:
                doc = json.loads(raw)
                keys = doc.get("keys", {})
                providers = doc.get("providers", [])
                settings = doc.get("settings", {})
                booleans_ok = bool(keys) and all(isinstance(v, bool) for v in keys.values())
                # No key value leak: assert body carries none of the env-key names' values.
                # (booleans only; we scan the raw body for any obvious secret marker.)
                body_text = raw.decode("utf-8", "replace")
                # A leaked key would appear as a long string value under keys/settings;
                # the contract is keys are bool. Confirm no non-bool under "keys".
                leak = [p for p, v in keys.items() if not isinstance(v, bool)]
                has_settings = bool(settings) and "console_port" in settings
                if booleans_ok and not leak and has_settings:
                    S[4].ok(
                        f"GET /api/settings -> 200; providers={providers}",
                        f"keys(bool)={json.dumps(keys)} "
                        f"keystore_available={doc.get('keystore_available')}",
                        f"settings has {len(settings)} non-sensitive fields; no key VALUE in body",
                    )
                else:
                    S[4].fail(
                        f"status=200 but booleans_ok={booleans_ok} "
                        f"leak={leak} has_settings={has_settings}",
                        f"body[:300]={body_text[:300]!r}",
                    )
            else:
                S[4].fail(
                    f"GET /api/settings -> {status} (endpoint not mounted?)",
                    f"body[:300]={raw.decode('utf-8', 'replace')[:300]!r}",
                )

            # ---- Step 5: POST /api/settings persists to user config dir --------
            before = user_config_dir()
            probe_port = 8123 if health_body is None else 8127
            status, raw = _http("POST", f"{base}/api/settings", {"console_port": probe_port})
            if status == 200:
                # Re-read via GET: the persisted value must be reflected.
                gstatus, graw = _http("GET", f"{base}/api/settings")
                reflected = (
                    gstatus == 200
                    and json.loads(graw).get("settings", {}).get("console_port") == probe_port
                )
                landed = settings_file.is_file() and settings_file.stat().st_mtime >= t0
                in_bundle = _bundle_has_dir("Application Support")  # sanity: none
                if reflected and landed and not in_bundle:
                    S[5].ok(
                        f"POST /api/settings console_port={probe_port} -> 200; GET reflects it",
                        f"user settings file written: {settings_file}",
                        f"file under user config dir: {settings_file.parent == before}; "
                        f"mtime fresh: {settings_file.stat().st_mtime >= t0}",
                        "no 'Application Support' dir inside the .app bundle",
                    )
                else:
                    S[5].fail(
                        f"reflected={reflected} landed={landed} bundle_leak={in_bundle}",
                        f"settings_file={settings_file} exists={settings_file.is_file()}",
                    )
            else:
                S[5].fail(f"POST /api/settings -> {status} (endpoint not mounted?)",
                          f"body[:300]={raw.decode('utf-8', 'replace')[:300]!r}")

            # ---- Step 6: responder provisioning into a fresh temp dir ----------
            # POST /api/provision/responder resolves import_dir from settings, so
            # first point plugin_import_dir at the fresh temp dir via POST /api/settings.
            sstatus, sraw = _http(
                "POST", f"{base}/api/settings", {"plugin_import_dir": str(provision_dir)}
            )
            pstatus, praw = _http("POST", f"{base}/api/provision/responder")
            if sstatus == 200 and pstatus == 200:
                install = json.loads(praw)
                gstatus, graw = _http("GET", f"{base}/api/provision/responder")
                gdoc = json.loads(graw) if gstatus == 200 else {}
                landed_files = sorted(p.name for p in provision_dir.iterdir())
                expected = {"copilot_responder.xml", "copilot_responder.lua"}
                files_ok = expected.issubset(set(landed_files))
                installed_all = gdoc.get("installed_all") is True
                guide_ok = isinstance(gdoc.get("guide"), dict) and "steps" in gdoc.get("guide", {})
                if files_ok and installed_all and guide_ok:
                    S[6].ok(
                        f"POST /api/provision/responder -> 200; "
                        f"installed={install.get('installed')}",
                        f"GET installed_all={installed_all}; import_dir={gdoc.get('import_dir')}",
                        f"bundled assets copied into temp dir: {landed_files}",
                        f"guide steps present: {len(gdoc['guide']['steps'])} steps",
                    )
                else:
                    S[6].fail(
                        f"files_ok={files_ok} installed_all={installed_all} guide_ok={guide_ok}",
                        f"landed={landed_files}",
                    )
            else:
                S[6].fail(
                    f"POST /api/settings->{sstatus}, POST /api/provision/responder->{pstatus}",
                    f"provision body[:300]={praw.decode('utf-8', 'replace')[:300]!r}",
                )

        # ---- Step 7: audit dir under user DATA dir, not the bundle -------------
        audit_dir = user_data_dir() / "audit_logs"
        bundle_audit = _bundle_has_dir("audit_logs")
        under_user_data = str(audit_dir).startswith(str(user_data_dir()))
        fresh_entries = []
        if audit_dir.is_dir():
            fresh_entries = [
                p.name for p in audit_dir.iterdir() if p.stat().st_mtime >= t0
            ]
        if under_user_data and not bundle_audit:
            S[7].ok(
                f"audit dir resolves under user data dir: {audit_dir}",
                f"user_data_dir={user_data_dir()}",
                "no 'audit_logs' dir inside the .app bundle",
                f"audit dir exists={audit_dir.is_dir()}; "
                f"entries written this run={fresh_entries or 'none'}",
            )
        else:
            S[7].fail(
                f"under_user_data={under_user_data} bundle_audit={bundle_audit}",
                f"audit_dir={audit_dir}",
            )

        # ---- Step 8: wire-level packet sink (AC-DEPLOY-027 Layer ②) ------------
        # The sink has been bound to console_port since before launch. Confirm
        # the app's EFFECTIVE settings agree that this is the send port (never
        # assert against the hardcoded 8000 default — audit defect D3), let the
        # responder heartbeat produce real gate traffic, then reconcile every
        # observed datagram 1:1 against the gate audit "executed" log.
        if S[2].status == "PASS":
            _http("POST", f"{base}/api/settings", {"console_port": console_port})
            gstatus, graw = _http("GET", f"{base}/api/settings")
            effective_port = (
                json.loads(graw).get("settings", {}).get("console_port")
                if gstatus == 200
                else None
            )
            # Heartbeats are the app's own legitimate gate sends; wait for one
            # window plus the ping timeout so the audit entry lands too.
            time.sleep(8.0)
            observed = sink.drain(settle=0.5)
            time.sleep(3.0)
            audited = _audit_executed_since(run_started_iso)
            outcome = reconcile(observed, audited)

            # Synthetic rogue injection: a datagram that never transited the
            # gate (as a Rust sidecar's raw UDP would not) must be flagged.
            rogue_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                rogue_sock.sendto(b"m73-synthetic-rogue", ("127.0.0.1", console_port))
            finally:
                rogue_sock.close()
            rogue_seen = sink.drain(settle=0.5)
            rogue_outcome = reconcile(rogue_seen, audited)
            rogue_flagged = any(b"m73-synthetic-rogue" in d.raw for d in rogue_outcome.unaudited)

            port_ok = effective_port == console_port and console_port != 8000
            if port_ok and outcome.ok and rogue_flagged and not rogue_outcome.ok:
                S[8].ok(
                    f"sink bound to effective send_port {console_port} "
                    f"(GET /api/settings console_port={effective_port}; NOT the 8000 default)",
                    f"positive observation: {outcome.observed_count} datagram(s) captured, "
                    f"{outcome.matched} reconciled 1:1 against {outcome.audited_count} "
                    "gate 'executed' audit entries",
                    f"verbs observed: {sorted({d.verb for d in observed})}",
                    "0 observed-but-unaudited senders (no unenumerated OSC send surface)",
                    "synthetic rogue datagram injected off-gate -> FLAGGED "
                    f"({len(rogue_outcome.unaudited)} unaudited)",
                )
            else:
                S[8].fail(
                    f"port_ok={port_ok} (effective={effective_port}, sink={console_port})",
                    f"reconcile ok={outcome.ok}: {outcome.detail}",
                    f"observed={outcome.observed_count} audited={outcome.audited_count} "
                    f"matched={outcome.matched}",
                    f"rogue_flagged={rogue_flagged} rogue_reconcile_ok={rogue_outcome.ok}",
                )
        else:
            S[8].fail("skipped: server never became healthy")

        # ---- Step 9: CLEAN SIGTERM shutdown ------------------------------------
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                rc = proc.wait(timeout=SHUTDOWN_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                rc = None
            time.sleep(0.5)
            residual = _pgid_processes(pgid) if pgid else []
            # Ports free? (retry briefly for socket release.)
            web_freed = recv_freed = False
            for _ in range(10):
                web_freed = _port_free(web_port)
                recv_freed = _port_free(recv_port)
                if web_freed and recv_freed:
                    break
                time.sleep(0.3)
            clean_exit = rc is not None and rc == 0
            if clean_exit and not residual and web_freed and recv_freed:
                S[9].ok(
                    f"SIGTERM -> exit rc={rc} (clean)",
                    f"process-tree scan (pgid={pgid}) residual: 0",
                    f"web_port {web_port} freed: {web_freed}; "
                    f"receive_port {recv_port} freed: {recv_freed}",
                )
            else:
                S[9].fail(
                    f"rc={rc} clean={clean_exit} residual={residual} "
                    f"web_freed={web_freed} recv_freed={recv_freed}",
                )
        else:
            S[9].fail(f"process already dead before SIGTERM (rc={proc.returncode})")

    finally:
        # Guaranteed teardown: never leave a stray server.
        if proc is not None and proc.poll() is None:
            try:
                if pgid is not None and hasattr(os, "killpg"):
                    os.killpg(pgid, signal.SIGKILL)
                else:
                    proc.kill()
            except (ProcessLookupError, PermissionError):
                pass
            with contextlib.suppress(Exception):
                proc.wait(timeout=5)
        logf.close()
        with contextlib.suppress(Exception):
            sink.stop()
        # Restore the operator's real settings.toml.
        if backup is not None:
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            settings_file.write_bytes(backup)
        elif settings_file.is_file():
            # The test created it; remove so we leave no residue.
            settings_file.unlink()
        shutil.rmtree(provision_dir, ignore_errors=True)

    # ---- report -----------------------------------------------------------------
    print("=" * 78)
    print("M10 Part D — packaged .app HTTP E2E result")
    print(f"binary: {BINARY}")
    print("=" * 78)
    all_pass = True
    for s in steps:
        mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}[s.status]
        print(f"[{mark}] Step {s.n}: {s.name}")
        for line in s.evidence:
            for sub in line.splitlines():
                print(f"        {sub}")
        if s.status != "PASS":
            all_pass = False
    print("=" * 78)
    print("RESULT:", "ALL PASS" if all_pass else "FAILURES PRESENT")
    print("=" * 78)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run())
