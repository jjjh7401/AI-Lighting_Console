"""M7.4a — Tauri v2 shell scaffold guards (AC-DEPLOY-024, AC-DEPLOY-027 Layer ③).

The Stage-2 shell is Rust; every guard the Stage-1 suite owns is Python-blind to
it. Three obligations of the scaffold are **silent-failure traps** — wrong, the
app still builds, still launches and still looks healthy — so each gets a
mechanical guard here rather than a review checklist:

1. **Parent declaration (the trap).** ``server/web/launcher.py``'s
   ``install_parent_watchdog`` arms ONLY when the spawning host declares itself
   through ``COPILOT_PARENT_PIPE_FD`` / ``COPILOT_PARENT_PID``. A sidecar spawn
   that forgets the declaration leaves the watchdog **silently disarmed**: no
   error, no log, no failing test — until a force-quit orphans the extracted
   Python and the next launch dies on ``require_ports_available``. Same defect
   class as the Stage-1 unmounted-router P0. :class:`TestSidecarParentDeclaration`
   fails when the declaration is missing, and its own detection logic is proven
   against synthetic positive/negative controls (a guard that cannot fail is not
   a guard).

2. **No backend URL literal.** The deny-all Rust scan (``packaging/rust_scan.py``)
   forbids ``127.0.0.1`` and console-port literals in Rust. The shell therefore
   may not KNOW the backend address at compile time: it reads the URL the backend
   prints on its stdout (``server/web/host_channel.py``). A hardcoded literal
   would both trip the scan and silently desync from a reconfigured port.

3. **Windows origin stays deferred.** ``http://tauri.localhost`` (the Windows
   webview origin) is deliberately NOT in the handshake allowlist — no Windows
   runner exists in M7. The deferral carries the greppable ``PENDING-WINDOWS``
   marker so it cannot be silently forgotten, mirroring ``PENDING-M7.4``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from server.web import handshake
from server.web.launcher import PARENT_PID_ENV, PARENT_PIPE_FD_ENV

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_TAURI = PROJECT_ROOT / "src-tauri"
RUST_SRC = SRC_TAURI / "src"
CAPABILITIES = SRC_TAURI / "capabilities"
TAURI_CONF = SRC_TAURI / "tauri.conf.json"

# The greppable marker for the deferred Windows webview origin (constraint: the
# deferral must be discoverable by grep, exactly like PENDING-M7.4).
PENDING_WINDOWS_MARKER = "PENDING-WINDOWS"

_CONST_STR = re.compile(r'const\s+(\w+)\s*:\s*&(?:\'\w+\s+)?str\s*=\s*"([^"]*)"')


# --------------------------------------------------------------- guard mechanics


def rust_string_consts(source: str) -> dict[str, str]:
    """Map every ``const NAME: &str = "value";`` declaration to its value."""
    return {name: value for name, value in _CONST_STR.findall(source)}


def function_body(source: str, signature: str) -> str | None:
    """Return the brace-matched body of the function whose header matches.

    ``signature`` is matched as a substring of the header line (e.g.
    ``"fn spawn_backend"``). Returns ``None`` when the function is absent — the
    fail-closed direction: an absent spawn function cannot declare a parent.
    """
    start = source.find(signature)
    if start < 0:
        return None
    brace = source.find("{", start)
    if brace < 0:
        return None
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace : index + 1]
    return None


def parent_declaration_gaps(source: str) -> list[str]:
    """Return every reason ``source`` fails to declare the parent on spawn.

    Empty list == the sidecar spawn declares the parent to the backend watchdog.
    The check is deliberately structural rather than textual: the declaration
    must live INSIDE the function that spawns, and the env-var NAME must equal
    the constant ``server/web/launcher.py`` actually reads (so renaming it there
    breaks this test loudly instead of disarming the watchdog quietly).
    """
    gaps: list[str] = []
    consts = rust_string_consts(source)
    declared = {value: name for name, value in consts.items()}

    pipe_const = declared.get(PARENT_PIPE_FD_ENV)
    pid_const = declared.get(PARENT_PID_ENV)
    if pipe_const is None and pid_const is None:
        gaps.append(
            f"no const declares {PARENT_PIPE_FD_ENV!r} or {PARENT_PID_ENV!r} — "
            "the backend watchdog would never arm"
        )

    body = function_body(source, "fn spawn_backend")
    if body is None:
        gaps.append("no `fn spawn_backend` found — nothing spawns the sidecar")
        return gaps

    if "spawn(" not in body:
        gaps.append("`fn spawn_backend` never calls spawn()")

    referenced = [name for name in (pipe_const, pid_const) if name and name in body]
    if not referenced:
        gaps.append(
            "the spawn body references no parent-declaration constant — "
            "the sidecar would inherit no COPILOT_PARENT_* env var"
        )
    if not any(marker in body for marker in ("envs(", ".env(")):
        gaps.append("the spawn body sets no environment on the command")
    # PRIMARY trigger: pipe EOF is race-free; the pid poll is only the fallback.
    if pipe_const is None or pipe_const not in body:
        gaps.append(
            f"the spawn body does not declare {PARENT_PIPE_FD_ENV!r} (the "
            "race-free PRIMARY trigger); a pid-poll-only declaration is the "
            "fallback, not the contract"
        )
    return gaps


_GOOD_SPAWN = """
const PARENT_PIPE_FD_ENV: &str = "COPILOT_PARENT_PIPE_FD";
const PARENT_PID_ENV: &str = "COPILOT_PARENT_PID";

pub fn spawn_backend(app: &AppHandle) -> Result<(), String> {
    let mut env = HashMap::new();
    env.insert(PARENT_PIPE_FD_ENV.to_string(), "0".to_string());
    env.insert(PARENT_PID_ENV.to_string(), id().to_string());
    let command = app.shell().sidecar(NAME).unwrap().envs(env);
    let (rx, child) = command.spawn().unwrap();
    Ok(())
}
"""

_SPAWN_WITHOUT_DECLARATION = """
pub fn spawn_backend(app: &AppHandle) -> Result<(), String> {
    let command = app.shell().sidecar(NAME).unwrap();
    let (rx, child) = command.spawn().unwrap();
    Ok(())
}
"""

_DECLARATION_OUTSIDE_THE_SPAWN = """
const PARENT_PIPE_FD_ENV: &str = "COPILOT_PARENT_PIPE_FD";

pub fn unrelated() { let _ = PARENT_PIPE_FD_ENV; }

pub fn spawn_backend(app: &AppHandle) -> Result<(), String> {
    let command = app.shell().sidecar(NAME).unwrap();
    let (rx, child) = command.spawn().unwrap();
    Ok(())
}
"""


class TestParentDeclarationGuardDetectsItsOwnFailure:
    """Positive/negative controls — the guard must be able to FAIL.

    A guard proven only against the real (passing) tree is indistinguishable
    from ``assert True``; these controls pin the detection itself.
    """

    def test_a_correct_spawn_reports_no_gaps(self):
        assert parent_declaration_gaps(_GOOD_SPAWN) == []

    def test_a_spawn_without_the_declaration_is_flagged(self):
        gaps = parent_declaration_gaps(_SPAWN_WITHOUT_DECLARATION)
        assert gaps, "the guard passed a spawn that declares no parent"
        assert any("watchdog would never arm" in gap for gap in gaps), gaps

    def test_a_declaration_outside_the_spawn_body_is_flagged(self):
        # The exact silent failure: the constant EXISTS (so a naive grep passes)
        # but never reaches the spawned command's environment.
        gaps = parent_declaration_gaps(_DECLARATION_OUTSIDE_THE_SPAWN)
        assert any("spawn body" in gap for gap in gaps), gaps

    def test_an_absent_spawn_function_is_flagged(self):
        gaps = parent_declaration_gaps("fn main() {}")
        assert any("nothing spawns the sidecar" in gap for gap in gaps), gaps


def _rust_sources() -> list[Path]:
    return sorted(RUST_SRC.rglob("*.rs"))


def _spawn_source() -> tuple[Path, str]:
    for path in _rust_sources():
        text = path.read_text(encoding="utf-8")
        if "fn spawn_backend" in text:
            return path, text
    pytest.fail(f"no Rust source under {RUST_SRC} defines `fn spawn_backend`")


class TestSidecarParentDeclaration:
    """🔴 The trap. The sidecar spawn MUST declare the parent to the backend."""

    def test_the_shell_source_tree_exists(self):
        assert RUST_SRC.is_dir(), f"M7.4a scaffold missing: {RUST_SRC}"
        assert _rust_sources(), f"no Rust sources under {RUST_SRC}"

    def test_the_spawn_declares_the_parent_to_the_watchdog(self):
        path, source = _spawn_source()
        gaps = parent_declaration_gaps(source)
        assert gaps == [], f"{path}: {gaps}"

    def test_the_declared_env_names_match_the_python_watchdog(self):
        # Linkage, not duplication: the expected values are IMPORTED from
        # launcher.py, so a rename there fails this test instead of silently
        # disarming the watchdog.
        _, source = _spawn_source()
        values = set(rust_string_consts(source).values())
        assert PARENT_PIPE_FD_ENV in values
        assert PARENT_PID_ENV in values

    def test_the_primary_trigger_is_the_inherited_stdin_pipe(self):
        # fd 0 — the sidecar's own stdin, which the host holds the write end of
        # for its whole lifetime. Any host death closes it => EOF => immediate,
        # race-free self-reap (plan §C M7.2 PRIMARY trigger).
        _, source = _spawn_source()
        consts = rust_string_consts(source)
        fd_value = consts.get("PARENT_PIPE_FD_VALUE")
        assert fd_value == "0", (
            "the declared parent pipe fd must be 0 (the inherited stdin pipe); "
            f"got {fd_value!r}"
        )


class TestAFailedSpawnIsReportedNotPanicked:
    """Error-UX (REQ-DEPLOY-018~020): "the backend did not start" is a
    foreseeable, recoverable startup condition — a stale bundle, a quarantined
    binary, a missing runtime payload. Propagating it out of Tauri's setup hook
    with ``?`` aborts the process with a NON-UNWINDING panic (the panic crosses
    the macOS app delegate), so the operator gets a Rust backtrace instead of a
    cause. Observed once, guarded here so it cannot come back."""

    def test_the_setup_hook_does_not_propagate_the_spawn_error(self):
        source = (RUST_SRC / "main.rs").read_text(encoding="utf-8")
        assert "spawn_backend" in source
        assert "spawn_backend(handle)?" not in source, (
            "the setup hook propagates the spawn error with `?` — Tauri turns "
            "that into a non-unwinding panic and aborts the app"
        )
        assert "if let Err" in source, "main.rs does not handle the spawn error at all"

    def test_a_human_readable_report_path_exists(self):
        report = (RUST_SRC / "startup_error.rs").read_text(encoding="utf-8")
        # A cause AND a next step — the M5 error-UX shape, not a raw error string.
        assert "What to try" in report, report[:400]
        assert "MessageDialogKind::Error" in report
        # Prose that NAMES the panic is fine (the file explains why it avoids
        # one); code that panics is not — so judge the non-comment lines only.
        code = [line for line in report.splitlines() if not line.lstrip().startswith("//")]
        assert not any("panic!" in line or ".unwrap()" in line for line in code), code

    def test_the_report_is_reachable_from_both_failure_shapes(self):
        # Two ways the backend can fail to come up: the spawn itself errors
        # (missing executable), or it spawns and dies before reporting a URL
        # (missing runtime payload — the packaged-bundle failure mode). Both must
        # reach the same human-readable report.
        main_source = (RUST_SRC / "main.rs").read_text(encoding="utf-8")
        spawn_source = (RUST_SRC / "sidecar.rs").read_text(encoding="utf-8")
        assert "startup_error::report" in main_source
        assert "startup_error::report" in spawn_source, (
            "a sidecar that dies during start-up is silent — the packaged "
            "missing-payload failure would surface as nothing at all"
        )


class TestShellHasNoBackendAddressLiteral:
    """The webview URL comes from the sidecar at runtime, never from a literal."""

    def test_no_rust_source_hardcodes_a_loopback_or_port_literal(self):
        offenders = []
        for path in _rust_sources():
            text = path.read_text(encoding="utf-8")
            for needle in ("127.0.0.1", "localhost", "8765", "8000", "9000"):
                if needle in text:
                    offenders.append(f"{path.name}: {needle!r}")
        assert offenders == [], offenders

    def test_the_shell_parses_the_url_the_backend_prints(self):
        _, source = _spawn_source()
        from server.web.host_channel import READY_PREFIX

        values = set(rust_string_consts(source).values())
        assert READY_PREFIX in values, (
            "the shell must recognise the backend's stdout ready line "
            f"({READY_PREFIX!r}) — that is the only literal-free way it can "
            "learn the URL to load"
        )


class TestTauriConfigBundlesTheSidecar:
    def test_config_declares_the_backend_as_an_external_binary(self):
        conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
        external = conf["bundle"]["externalBin"]
        assert external, "no externalBin — the backend would not be bundled"
        assert any("copilot-backend" in entry for entry in external), external

    def test_the_capability_scope_names_the_same_binary_as_the_config(self):
        # The Rust side resolves the BARE file name (the plugin joins the given
        # path onto the executable's own directory) while the config and the
        # JS-side capability scope use the `binaries/...` path. Both spellings
        # are pinned so the deliberate asymmetry cannot silently become a typo.
        conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
        capability = json.loads((CAPABILITIES / "default.json").read_text(encoding="utf-8"))
        consts = rust_string_consts(_spawn_source()[1])

        configured = conf["bundle"]["externalBin"][0]
        assert consts["SIDECAR_SCOPE_NAME"] == configured
        assert consts["SIDECAR_NAME"] == configured.rsplit("/", 1)[-1]
        scoped = [
            item["name"]
            for entry in capability["permissions"]
            if not isinstance(entry, str)
            for item in entry.get("allow", [])
        ]
        assert scoped == [configured], scoped

    def test_config_serves_the_built_spa_from_ui_dist(self):
        conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
        assert conf["build"]["frontendDist"].endswith("ui/dist"), conf["build"]

    def test_the_sidecar_payload_directory_is_not_committed(self):
        ignore = (SRC_TAURI / ".gitignore").read_text(encoding="utf-8")
        assert "target" in ignore, "src-tauri/target/ must never be committed"
        assert "binaries" in ignore, "the staged sidecar payload must not be committed"


class TestCapabilityDeniesNetworkPlugins:
    """AC-DEPLOY-027 Layer ③ — capabilities deny network, shell = sidecar only."""

    def test_default_capability_exists_and_is_scanned_by_the_deny_all_scan(self):
        assert (CAPABILITIES / "default.json").is_file(), CAPABILITIES

    def test_no_network_plugin_permission_is_granted(self):
        for path in sorted(CAPABILITIES.glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            for entry in document.get("permissions", []):
                name = entry if isinstance(entry, str) else entry.get("identifier", "")
                assert not name.startswith(("http:", "websocket:", "upload:", "geolocation:")), (
                    f"{path.name} grants a network permission: {name!r}"
                )

    def test_shell_permission_is_scoped_to_sidecar_spawn_only(self):
        document = json.loads((CAPABILITIES / "default.json").read_text(encoding="utf-8"))
        shell_entries = [
            entry
            for entry in document["permissions"]
            if (entry if isinstance(entry, str) else entry.get("identifier", "")).startswith(
                "shell:"
            )
        ]
        assert shell_entries, "the shell needs SOME shell permission to spawn the sidecar"
        for entry in shell_entries:
            name = entry if isinstance(entry, str) else entry["identifier"]
            # allow-open would let the shell hand arbitrary URLs/paths to the OS;
            # allow-execute (unscoped) would let it run arbitrary binaries.
            assert name != "shell:allow-open", "shell:allow-open is not needed to spawn a sidecar"
            if name == "shell:allow-execute":
                assert not isinstance(entry, str), (
                    "shell:allow-execute must carry a scope; a bare grant allows "
                    "executing anything"
                )
                scope = entry.get("allow", [])
                assert scope, "shell:allow-execute granted with an empty allow scope"
                assert all(item.get("sidecar") is True for item in scope), scope


class TestBundledSidecarCarriesItsRuntime:
    """The dev-works / packaged-fails gap, closed and guarded.

    ``bundle.externalBin`` carries the sidecar EXECUTABLE into the ``.app`` and
    nothing else — but a PyInstaller **onedir** executable cannot boot without
    its runtime tree. Dev runs pass (Cargo's copy sits next to a mirrored
    ``_internal/``) while the shipped bundle dies on first spawn: exactly the
    class of defect that produced the Stage-1 unmounted-router P0. The payload
    step and its verifier are unit-proven here against a synthetic bundle, so the
    check does not depend on a release build being available.
    """

    @staticmethod
    def _stage_sidecar():
        sys.path.insert(0, str(PROJECT_ROOT / "packaging"))
        import stage_sidecar

        return stage_sidecar

    def _fake_bundle(self, tmp_path, *, with_executable=True):
        stage_sidecar = self._stage_sidecar()
        app = tmp_path / "Fake.app"
        (app / "Contents" / "MacOS").mkdir(parents=True)
        if with_executable:
            (app / "Contents" / "MacOS" / stage_sidecar.SIDECAR_BASE).write_text("#!/bin/sh\n")
        return app

    def test_verify_fails_on_a_bundle_missing_the_runtime_payload(self, tmp_path):
        stage_sidecar = self._stage_sidecar()
        app = self._fake_bundle(tmp_path)
        # The exact shipped-and-broken shape: executable present, runtime absent.
        assert stage_sidecar.verify_bundle(app) == 1

    def test_verify_fails_on_a_bundle_missing_the_executable(self, tmp_path):
        stage_sidecar = self._stage_sidecar()
        app = self._fake_bundle(tmp_path, with_executable=False)
        assert stage_sidecar.verify_bundle(app) == 1

    def test_payload_lands_flat_in_contents_frameworks(self, tmp_path, monkeypatch):
        # PyInstaller resolves an executable in Contents/MacOS against
        # ../Frameworks, and expects the tree FLAT there (not nested under
        # _internal/). Verified against the real dist/*.app layout.
        stage_sidecar = self._stage_sidecar()
        staged = tmp_path / "binaries"
        (staged / "_internal").mkdir(parents=True)
        (staged / "_internal" / "base_library.zip").write_text("x")
        monkeypatch.setattr(stage_sidecar, "SIDECAR_DIR", staged)

        app = self._fake_bundle(tmp_path)
        stage_sidecar.bundle_payload(app)
        assert (app / "Contents" / "Frameworks" / "base_library.zip").is_file()
        assert not (app / "Contents" / "Frameworks" / "_internal").exists()
        assert stage_sidecar.verify_bundle(app) == 0

    def test_the_real_pyinstaller_app_uses_the_layout_this_relies_on(self):
        # Not an assumption: the M6 bundle itself puts the executable in
        # Contents/MacOS and the runtime flat in Contents/Frameworks. If
        # PyInstaller ever changes that, this fails instead of shipping a
        # silently-broken sidecar.
        reference = PROJECT_ROOT / "dist" / "GrandMA3 Copilot.app" / "Contents"
        if not reference.is_dir():
            pytest.skip("dist/GrandMA3 Copilot.app not built in this checkout")
        assert (reference / "MacOS" / "GrandMA3 Copilot").is_file()
        assert (reference / "Frameworks" / "base_library.zip").is_file()

    def test_a_built_bundle_in_this_checkout_carries_a_bootable_sidecar(self):
        # Auto-flipping REAL-artifact gate, same discipline as PENDING-M7.4: while
        # no bundle exists there is nothing to check, but the moment one is built
        # it MUST verify. That is what stops the payload step from being silently
        # dropped by a future packaging change — the graceful startup dialog makes
        # the runtime failure soft, so only a hard gate keeps it visible.
        stage_sidecar = self._stage_sidecar()
        bundle = (
            PROJECT_ROOT
            / "src-tauri"
            / "target"
            / "release"
            / "bundle"
            / "macos"
            / "GrandMA3 Copilot.app"
        )
        if not bundle.is_dir():
            pytest.skip(f"PENDING-BUNDLE: no built bundle at {bundle} in this checkout")
        assert stage_sidecar.verify_bundle(bundle) == 0, (
            "the built .app ships a sidecar executable without its PyInstaller "
            "runtime — it would fail on first launch (run `npm run shell:build`)"
        )

    def test_the_payload_destination_matches_the_bootloader_expectation(self):
        # The destination is Contents/Frameworks, NOT a nested _internal/: the
        # PyInstaller bootloader switches to the .app layout when its executable
        # sits in Contents/MacOS. Observed verbatim from the bootloader itself
        # ("Failed to load Python shared library '<app>/Contents/Frameworks/
        # libpython3.11.dylib'"), so `find <app> -name _internal` finding nothing
        # is the CORRECT shape here, not a missing payload.
        stage_sidecar = self._stage_sidecar()
        source = Path(stage_sidecar.__file__).read_text(encoding="utf-8")
        assert '"Frameworks"' in source
        assert "Contents/MacOS" in source or '"MacOS"' in source

    def test_the_build_script_runs_the_payload_step(self):
        package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
        build = package["scripts"]["shell:build"]
        assert "--bundle" in build, (
            "npm run shell:build must copy the runtime payload into the .app, or "
            "the shipped sidecar cannot boot"
        )


class TestWindowsOriginStaysDeferred:
    """The Windows webview origin is deferred (no Windows runner in M7) and the
    deferral is greppable so it cannot be silently forgotten."""

    def test_tauri_localhost_is_not_in_the_handshake_allowlist(self):
        assert not any("tauri.localhost" in origin for origin in handshake.TAURI_ORIGINS), (
            handshake.TAURI_ORIGINS
        )

    def test_the_deferral_carries_the_greppable_marker(self):
        source = Path(handshake.__file__).read_text(encoding="utf-8")
        assert PENDING_WINDOWS_MARKER in source, (
            "the Windows-origin deferral must carry the greppable "
            f"{PENDING_WINDOWS_MARKER} marker (mirrors PENDING-M7.4)"
        )

    def test_the_loopback_host_guard_was_not_widened(self):
        from server.tests import test_deploy_local_only

        expected = frozenset({"127.0.0.1", "localhost", "::1"})
        assert expected == test_deploy_local_only._LOOPBACK_HOSTS, (
            "the AC-DEPLOY-002 loopback guard must not be widened for a Windows origin"
        )
