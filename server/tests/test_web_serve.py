"""Production entry-point tests (M5 — REQ-MVP-043 runnable server).

``python -m server.web`` composes: provider config (TOML) -> provider adapter,
rulebook fixed prefix, gate-owned console stack (server.safety.bootstrap),
fallback detector + round-trip recorder, approval channel — then serves the
FastAPI app with uvicorn (injectable for tests; no real socket binding here).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import keyring
import pytest
from fastapi.testclient import TestClient
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

from server.deploy import keystore
from server.web.serve import (
    build_runtime,
    default_ui_dist,
    main,
    parse_args,
)


def _fake_keyring(module_name: str):
    """A fake ``keyring`` module whose active backend reports ``module_name``."""
    backend_cls = type("Keyring", (), {})
    backend_cls.__module__ = module_name

    class _FakeKeyring:
        _store: dict = {}

        @staticmethod
        def get_keyring():
            return backend_cls()

        @classmethod
        def set_password(cls, service, account, value):
            cls._store[(service, account)] = value

        @classmethod
        def get_password(cls, service, account):
            return cls._store.get((service, account))

        @classmethod
        def delete_password(cls, service, account):
            cls._store.pop((service, account), None)

    return _FakeKeyring


class TestParseArgs:
    def test_defaults(self):
        args = parse_args([])
        assert args.host == "127.0.0.1"
        assert args.port == 8765
        assert args.console_port == 8000
        assert args.receive_port == 9000
        assert args.no_session_backup is False

    def test_overrides(self):
        args = parse_args(
            [
                "--port",
                "9001",
                "--console-host",
                "10.0.0.5",
                "--receive-port",
                "0",
                "--no-session-backup",
            ]
        )
        assert args.port == 9001
        assert args.console_host == "10.0.0.5"
        assert args.receive_port == 0
        assert args.no_session_backup is True

    def test_m6_launcher_flags_default_off(self):
        args = parse_args([])
        assert args.no_browser is False
        assert args.self_check is False

    def test_m6_launcher_flags_settable(self):
        args = parse_args(["--no-browser", "--self-check"])
        assert args.no_browser is True
        assert args.self_check is True


class TestUiDistResolution:
    def test_dev_ui_dist_matches_the_repo_layout(self):
        # Characterisation: dev-mode resolution is unchanged (repo-root/ui/dist).
        assert default_ui_dist() == Path(__file__).resolve().parents[2] / "ui" / "dist"

    def test_frozen_ui_dist_resolves_under_meipass(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        assert default_ui_dist() == Path(str(tmp_path)) / "ui" / "dist"


class TestBuildRuntime:
    def test_builds_a_servable_app_from_the_repo_config(self):
        # The repo config pins the providers; adapters build their SDK clients
        # lazily, so NO key is needed until a completion is attempted.
        args = parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = build_runtime(args)
        try:
            with TestClient(app) as client:
                payload = client.get("/healthz").json()
                assert payload["ok"] is True
        finally:
            stack.stop()


class TestMain:
    def test_main_runs_uvicorn_and_stops_the_stack(self):
        calls: list[dict] = []

        def fake_run(app, **kwargs):
            calls.append({"app": app, **kwargs})

        code = main(
            ["--receive-port", "0", "--no-session-backup", "--port", "9017"],
            run=fake_run,
        )
        assert code == 0
        assert calls and calls[0]["port"] == 9017

    def test_module_entry_help_exits_zero(self, monkeypatch):
        import runpy

        monkeypatch.setattr(sys, "argv", ["server.web", "--help"])
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_module("server.web", run_name="__main__", alter_sys=False)
        assert excinfo.value.code == 0


class TestSelfCheckMode:
    """--self-check: the keyring backend + roundtrip mode the packaged binary runs."""

    def test_self_check_passes_on_a_macos_backend(self):
        code = main(["--self-check"], keyring_module=_fake_keyring("keyring.backends.macOS"))
        assert code == 0

    def test_self_check_fails_on_a_wrong_backend(self):
        code = main(["--self-check"], keyring_module=_fake_keyring("keyring.backends.fail"))
        assert code != 0

    def test_self_check_does_not_serve(self):
        # A self-check must not build the runtime / bind ports — passing a run
        # that would explode proves the self-check returns before serving.
        def explode(*_a, **_k):  # pragma: no cover — must never be called
            raise AssertionError("self-check must not reach the serve path")

        code = main(
            ["--self-check"],
            run=explode,
            keyring_module=_fake_keyring("keyring.backends.macOS"),
        )
        assert code == 0


class TestKeyringStartupGuard:
    """Fail-closed keyring backend guard at process start (REQ-DEPLOY-006a)."""

    def test_boot_refused_on_wrong_backend(self):
        with pytest.raises(RuntimeError) as excinfo:
            main(
                ["--receive-port", "0", "--no-session-backup"],
                run=lambda *a, **k: None,
                keyring_module=_fake_keyring("keyrings.alt.file"),
            )
        assert "REQ-DEPLOY-006a" in str(excinfo.value)

    def test_boot_proceeds_on_macos_backend(self):
        calls: list[dict] = []
        code = main(
            ["--receive-port", "0", "--no-session-backup", "--port", "9019"],
            run=lambda app, **kwargs: calls.append(kwargs),
            keyring_module=_fake_keyring("keyring.backends.macOS"),
        )
        assert code == 0
        assert calls and calls[0]["port"] == 9019


class TestFallbackTargetProviderWiring:
    """AC-MVP-027 part 3: build_runtime wires the config-switch when a
    fallback target is configured; unchanged (single adapter) when absent."""

    def test_shipped_config_builds_a_single_bare_adapter(self):
        # Today's shipped config/provider.toml has no target_provider — the
        # wiring must stay byte-identical: deps.provider is the bare adapter,
        # not the SwitchableProvider indirection.
        from server.orchestrator.runner import SwitchableProvider

        args = parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = build_runtime(args)
        try:
            assert not isinstance(app.state.deps.provider, SwitchableProvider)
        finally:
            stack.stop()

    def test_target_provider_configured_wires_a_switchable_provider(self, tmp_path):
        from server.orchestrator.runner import SwitchableProvider

        config_path = tmp_path / "provider.toml"
        config_path.write_text(
            '[provider]\nactive = "anthropic"\n\n'
            '[provider.anthropic]\nmodel = "claude-opus-4-8"\n\n'
            '[provider.gemini]\nmodel = "gemini-3.5-flash"\n\n'
            '[fallback]\ntarget_provider = "gemini"\n',
            encoding="utf-8",
        )
        args = parse_args(
            ["--receive-port", "0", "--no-session-backup", "--config", str(config_path)]
        )
        app, stack = build_runtime(args)
        try:
            provider = app.state.deps.provider
            assert isinstance(provider, SwitchableProvider)
            assert provider.name == "anthropic"
            provider.switch_to("gemini")
            assert provider.name == "gemini"
        finally:
            stack.stop()


class TestM7ReviewWiring:
    def test_wires_the_deploy_review_flow(self):
        args = parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = build_runtime(args)
        try:
            deps = app.state.deps
            assert deps.review_channel is not None
            assert deps.review_channel is not deps.approval_channel
            assert deps.deploy_pipeline is not None
            # The pipeline registers into the SAME registry the gate consults.
            assert deps.deploy_pipeline._registry is stack.registry
        finally:
            stack.stop()


class TestM10DeployShellWiring:
    """M10 Part D — the packaged deploy shell must actually MOUNT the M3/M4
    settings/key + provisioning REST routers.

    The routers (build_settings_router / build_provision_router) and their deps
    classes exist since M3/M4, but the M6 obligation to compose them into the
    production ``WebDeps`` (settings_api docstring: "serve.py composition at M6")
    was missed — so ``build_runtime`` shipped an app that 404s on the whole
    deploy-shell REST surface. This is a Case-5 missing-endpoint boundary defect
    the M10 integration verification exists to catch (AC-DEPLOY-005/006/007).
    """

    def test_build_runtime_composes_settings_and_provision_deps(self):
        args = parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = build_runtime(args)
        try:
            deps = app.state.deps
            assert deps.settings is not None, "settings deps not composed (M3 router unmounted)"
            assert deps.provision is not None, "provision deps not composed (M4 router unmounted)"
        finally:
            stack.stop()

    def test_settings_and_provision_endpoints_are_served(self):
        # The deploy-shell UX (in-app config + provisioning) is entirely these
        # endpoints; if they 404, the packaged app is terminal-config-broken.
        args = parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = build_runtime(args)
        try:
            with TestClient(app) as client:
                settings = client.get("/api/settings")
                assert settings.status_code == 200, "GET /api/settings must be mounted (M3)"
                doc = settings.json()
                # Keys are booleans only — a value would be a credential leak.
                assert all(isinstance(v, bool) for v in doc["keys"].values())
                assert "console_port" in doc["settings"]

                provision = client.get("/api/provision/responder")
                assert provision.status_code == 200, (
                    "GET /api/provision/responder must be mounted (M4)"
                )
                assert "installed" in provision.json()
        finally:
            stack.stop()

    def test_settings_write_targets_the_user_config_dir_not_the_bundle(self, tmp_path):
        # POST with an explicit settings_path proves the write-side seam is
        # wired; the packaged default (settings_path=None) resolves to the OS
        # user config dir (verified end-to-end by verify_packaged_e2e.py step 5).
        from fastapi import FastAPI

        from server.web.settings_api import SettingsDeps, build_settings_router

        settings_file = tmp_path / "settings.toml"
        app = FastAPI()
        app.include_router(build_settings_router(SettingsDeps(settings_path=settings_file)))
        with TestClient(app) as client:
            resp = client.post("/api/settings", json={"console_port": 8123})
            assert resp.status_code == 200
            assert settings_file.is_file()
            assert "console_port = 8123" in settings_file.read_text()


# --- REQ-DEPLOY-028 / AC-DEPLOY-019 startup key-injection harness -------------
# Obviously-fake key strings + a sentinel so any leak is grep-visible.
_FAKE_ANTHROPIC_KEY = "sk-ant-FAKE-SERVE-STARTUP-000111222333"
_PRESET_ENV_SENTINEL = "preset-operator-env-key-DO-NOT-OVERWRITE"


class _MemoryKeyring(KeyringBackend):
    """In-memory keyring backend — deterministic, never touches the OS store."""

    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        try:
            del self._store[(service, username)]
        except KeyError as error:
            raise PasswordDeleteError("not found") from error


class _BrokenKeyring(KeyringBackend):
    """Simulates the OS credential store being unavailable / locked / denied."""

    priority = 1  # type: ignore[assignment]

    def get_password(self, service: str, username: str) -> str | None:
        raise KeyringError("credential store locked")

    def set_password(self, service: str, username: str, password: str) -> None:
        raise KeyringError("credential store access denied")

    def delete_password(self, service: str, username: str) -> None:
        raise KeyringError("credential store unavailable")


@pytest.fixture(autouse=True)
def _isolate_real_keyring():
    """Autouse — pin an in-memory keyring for EVERY test in this module so none
    ever touches the real OS Keychain.

    build_runtime now reads the active provider's stored key at start-up
    (REQ-DEPLOY-028); without this guard a build_runtime call for the shipped
    config (active provider = gemini) would hit — and, on a machine with a stored
    item, block on a GUI prompt for — the real Keychain. Tests that need the store
    to be populated call ``keystore.set_api_key`` (writes into this backend);
    tests that need a store failure override with the ``broken_keyring`` fixture.
    """
    original = keyring.get_keyring()
    keyring.set_keyring(_MemoryKeyring())
    try:
        yield
    finally:
        keyring.set_keyring(original)
        keystore.clear_session_keys()


@pytest.fixture
def broken_keyring():
    original = keyring.get_keyring()
    keyring.set_keyring(_BrokenKeyring())
    try:
        yield
    finally:
        keyring.set_keyring(original)
        keystore.clear_session_keys()


@pytest.fixture
def preserve_environ():
    """Snapshot os.environ and restore it fully — build_runtime injects real env
    vars into the process environment, so every startup-injection test isolates
    that side effect."""
    snapshot = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(snapshot)


def _write_provider_config(tmp_path: Path, *, active: str) -> Path:
    config_path = tmp_path / "provider.toml"
    config_path.write_text(
        f'[provider]\nactive = "{active}"\n\n'
        '[provider.anthropic]\nmodel = "claude-opus-4-8"\n\n'
        '[provider.gemini]\nmodel = "gemini-3.5-flash"\n',
        encoding="utf-8",
    )
    return config_path


class TestStartupProviderKeyInjection:
    """REQ-DEPLOY-028 / AC-DEPLOY-019 — build_runtime injects the active-provider
    key from the OS credential store into the process env BEFORE the provider
    client is constructed, preserving an operator's pre-set env key and never
    aborting start-up when the store is unavailable.
    """

    def test_injects_active_provider_key_from_store_at_startup(
        self, monkeypatch, preserve_environ, tmp_path
    ):
        # No user settings file → the seed's active provider wins deterministically.
        monkeypatch.setattr(
            "server.deploy.settings.user_settings_path",
            lambda *a, **k: tmp_path / "absent.toml",
        )
        os.environ.pop("ANTHROPIC_API_KEY", None)
        config_path = _write_provider_config(tmp_path, active="anthropic")
        keystore.set_api_key("anthropic", _FAKE_ANTHROPIC_KEY)

        args = parse_args(
            ["--receive-port", "0", "--no-session-backup", "--config", str(config_path)]
        )
        app, stack = build_runtime(args)
        try:
            assert os.environ.get("ANTHROPIC_API_KEY") == _FAKE_ANTHROPIC_KEY
        finally:
            stack.stop()

    def test_preset_env_key_is_preserved_not_overwritten(
        self, monkeypatch, preserve_environ, tmp_path
    ):
        monkeypatch.setattr(
            "server.deploy.settings.user_settings_path",
            lambda *a, **k: tmp_path / "absent.toml",
        )
        os.environ["ANTHROPIC_API_KEY"] = _PRESET_ENV_SENTINEL
        config_path = _write_provider_config(tmp_path, active="anthropic")
        # A DIFFERENT key sits in the store; the pre-set env value must still win.
        keystore.set_api_key("anthropic", _FAKE_ANTHROPIC_KEY)

        args = parse_args(
            ["--receive-port", "0", "--no-session-backup", "--config", str(config_path)]
        )
        app, stack = build_runtime(args)
        try:
            assert os.environ["ANTHROPIC_API_KEY"] == _PRESET_ENV_SENTINEL
        finally:
            stack.stop()

    def test_unavailable_store_does_not_abort_startup(
        self, broken_keyring, monkeypatch, preserve_environ, tmp_path
    ):
        monkeypatch.setattr(
            "server.deploy.settings.user_settings_path",
            lambda *a, **k: tmp_path / "absent.toml",
        )
        os.environ.pop("ANTHROPIC_API_KEY", None)
        config_path = _write_provider_config(tmp_path, active="anthropic")

        args = parse_args(
            ["--receive-port", "0", "--no-session-backup", "--config", str(config_path)]
        )
        # A locked / denied store must NOT crash start-up (REQ-DEPLOY-006a).
        app, stack = build_runtime(args)
        try:
            # Env stays unset for the provider — no plaintext, operator uses the UI.
            assert "ANTHROPIC_API_KEY" not in os.environ
        finally:
            stack.stop()
