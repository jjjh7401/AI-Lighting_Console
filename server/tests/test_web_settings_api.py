"""In-app settings + secure-key REST API tests (M3 — REQ-DEPLOY-005/007, AC-DEPLOY-003/014 ③).

The settings API is the terminal-free replacement for CLI args / env injection:
it reads and writes the M1 non-sensitive settings layer and drives the M2 secure
keystore. Two invariants dominate the test surface:

* **Key never leaves the store to the client (AC-DEPLOY-004).** ``GET /api/settings``
  exposes only a per-provider "key set: true/false" status — never a key value.
  Keys are write-only from the UI (``POST /api/keys`` -> keystore).
* **No OSC-send surface (AC-DEPLOY-014 ③ / SAFETY-1).** The settings/key path only
  calls the M1/M2 config + keystore seams; it never reaches the console-send
  surface. A source scan asserts the module imports no OSC / raw-socket path.

Testing discipline mirrors ``test_deploy_keystore.py``: the real macOS Keychain is
NEVER touched — a hand-rolled in-memory backend (or a deliberately broken one to
simulate store-unavailable) is installed and restored in teardown.
"""

from __future__ import annotations

import keyring
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

from server.deploy import keystore
from server.deploy.keystore import SessionKeyStore
from server.deploy.settings import UserSettings, resolve_effective_settings, save_user_settings
from server.web.settings_api import SettingsDeps, build_settings_router

# Obviously-fake, unique key strings so the "no key value leaked" scans are meaningful.
_FAKE_GEMINI_KEY = "AIzaFAKE-SETTINGS-API-GEMINI-000111222333"
_FAKE_ANTHROPIC_KEY = "sk-ant-FAKE-SETTINGS-API-000111222333"


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


@pytest.fixture
def memory_keyring():
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


def _make_deps(tmp_path, *, session=None, environ=None) -> SettingsDeps:
    return SettingsDeps(
        settings_path=tmp_path / "settings.toml",
        seed_path=tmp_path / "no-seed.toml",  # absent -> defaults only
        session=session if session is not None else SessionKeyStore(),
        environ=environ if environ is not None else {},
    )


def _client(deps: SettingsDeps) -> TestClient:
    app = FastAPI()
    app.include_router(build_settings_router(deps))
    return TestClient(app)


# --------------------------------------------------------------------------- GET


class TestGetSettings:
    def test_defaults_when_no_user_file(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        response = _client(deps).get("/api/settings")
        assert response.status_code == 200
        body = response.json()
        assert body["settings"]["console_port"] == 8000
        assert body["settings"]["receive_port"] == 9000
        assert body["settings"]["active_provider"] == "gemini"
        assert set(body["providers"]) == {"anthropic", "gemini"}
        # No key configured yet -> both false.
        assert body["keys"] == {"anthropic": False, "gemini": False}
        assert body["keystore_available"] is True

    def test_reflects_persisted_user_settings(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        save_user_settings(
            UserSettings(
                active_provider="anthropic",
                console_host="127.0.0.1",
                console_port=8123,
                receive_port=9456,
                web_host="127.0.0.1",
                web_port=8765,
                plugin_import_dir="/tmp/plugins",
            ),
            deps.settings_path,
        )
        body = _client(deps).get("/api/settings").json()
        assert body["settings"]["active_provider"] == "anthropic"
        assert body["settings"]["console_port"] == 8123
        assert body["settings"]["receive_port"] == 9456
        assert body["settings"]["plugin_import_dir"] == "/tmp/plugins"

    def test_key_set_status_true_but_value_never_returned(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        keystore.set_api_key("gemini", _FAKE_GEMINI_KEY)
        response = _client(deps).get("/api/settings")
        body = response.json()
        assert body["keys"]["gemini"] is True
        assert body["keys"]["anthropic"] is False
        # AC-DEPLOY-004: the key value MUST NOT appear anywhere in the response.
        assert _FAKE_GEMINI_KEY not in response.text

    def test_session_only_key_counts_as_set(self, tmp_path, memory_keyring):
        session = SessionKeyStore()
        session.set("anthropic", _FAKE_ANTHROPIC_KEY)
        deps = _make_deps(tmp_path, session=session)
        response = _client(deps).get("/api/settings")
        body = response.json()
        assert body["keys"]["anthropic"] is True
        assert _FAKE_ANTHROPIC_KEY not in response.text

    def test_keystore_unavailable_is_surfaced_not_crashed(self, tmp_path, broken_keyring):
        deps = _make_deps(tmp_path)
        response = _client(deps).get("/api/settings")
        assert response.status_code == 200
        body = response.json()
        assert body["keystore_available"] is False
        # No key readable -> both false, no crash.
        assert body["keys"] == {"anthropic": False, "gemini": False}


# ----------------------------------------------------------------- POST /settings


class TestPostSettings:
    def test_persists_and_survives_reload(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        client = _client(deps)
        payload = {
            "active_provider": "anthropic",
            "console_host": "127.0.0.1",
            "console_port": 8200,
            "receive_port": 9200,
            "web_host": "127.0.0.1",
            "web_port": 8765,
            "plugin_import_dir": "/tmp/imports",
        }
        response = client.post("/api/settings", json=payload)
        assert response.status_code == 200
        assert response.json()["ok"] is True
        # AC-DEPLOY-003: a fresh resolve (== restart) sees the persisted values.
        resolved = resolve_effective_settings(
            user_path=deps.settings_path, seed_path=deps.seed_path
        )
        assert resolved.active_provider == "anthropic"
        assert resolved.console_port == 8200
        assert resolved.receive_port == 9200
        assert resolved.plugin_import_dir == "/tmp/imports"

    def test_invalid_port_rejected_and_file_unchanged(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        client = _client(deps)
        response = client.post("/api/settings", json={"console_port": 70000})
        assert response.status_code == 422
        assert not deps.settings_path.is_file()  # nothing written on rejection

    def test_credential_key_in_body_is_not_persisted(self, tmp_path, memory_keyring):
        # Credential-rejection preserved: a smuggled api_key must never reach disk.
        deps = _make_deps(tmp_path)
        client = _client(deps)
        response = client.post(
            "/api/settings",
            json={"console_port": 8300, "api_key": _FAKE_GEMINI_KEY},
        )
        assert response.status_code == 200
        contents = deps.settings_path.read_text(encoding="utf-8")
        assert _FAKE_GEMINI_KEY not in contents
        assert "api_key" not in contents


# --------------------------------------------------------------------- POST /keys


class TestPostKeys:
    def test_store_in_keystore_and_inject_env(self, tmp_path, memory_keyring):
        environ: dict[str, str] = {}
        deps = _make_deps(tmp_path, environ=environ)
        response = _client(deps).post(
            "/api/keys", json={"provider": "gemini", "key": _FAKE_GEMINI_KEY}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["mode"] == "keystore"
        # REQ-DEPLOY-007: the key reaches the provider client via process env.
        assert environ["GEMINI_API_KEY"] == _FAKE_GEMINI_KEY
        assert environ["GOOGLE_API_KEY"] == _FAKE_GEMINI_KEY
        # Write-only: the response never echoes the key value.
        assert _FAKE_GEMINI_KEY not in response.text
        # It really landed in the keystore.
        assert keystore.get_api_key("gemini") == _FAKE_GEMINI_KEY

    def test_session_only_path_injects_without_touching_disk(self, tmp_path, memory_keyring):
        environ: dict[str, str] = {}
        session = SessionKeyStore()
        deps = _make_deps(tmp_path, session=session, environ=environ)
        response = _client(deps).post(
            "/api/keys",
            json={"provider": "anthropic", "key": _FAKE_ANTHROPIC_KEY, "session_only": True},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "session"
        assert environ["ANTHROPIC_API_KEY"] == _FAKE_ANTHROPIC_KEY
        assert session.get("anthropic") == _FAKE_ANTHROPIC_KEY
        # The persistent keystore was NOT written.
        assert keystore.get_api_key("anthropic", session=SessionKeyStore()) is None

    def test_keystore_unavailable_returns_explicit_error_with_session_fallback(
        self, tmp_path, broken_keyring
    ):
        deps = _make_deps(tmp_path)
        response = _client(deps).post(
            "/api/keys", json={"provider": "gemini", "key": _FAKE_GEMINI_KEY}
        )
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "keystore_unavailable"
        assert detail["provider"] == "gemini"
        assert detail["session_fallback"] is True
        # REQ-DEPLOY-006a: nothing was written to disk on the failure branch.
        assert not deps.settings_path.is_file()

    def test_session_fallback_works_when_keystore_broken(self, tmp_path, broken_keyring):
        # After a keystore failure the UI retries with session_only -> must succeed.
        environ: dict[str, str] = {}
        session = SessionKeyStore()
        deps = _make_deps(tmp_path, session=session, environ=environ)
        response = _client(deps).post(
            "/api/keys",
            json={"provider": "gemini", "key": _FAKE_GEMINI_KEY, "session_only": True},
        )
        assert response.status_code == 200
        assert environ["GEMINI_API_KEY"] == _FAKE_GEMINI_KEY

    def test_unknown_provider_rejected(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        response = _client(deps).post("/api/keys", json={"provider": "openai", "key": "x"})
        assert response.status_code == 400

    def test_empty_key_rejected(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        response = _client(deps).post("/api/keys", json={"provider": "gemini", "key": "  "})
        assert response.status_code == 400


# ------------------------------------------------------------------- DELETE /keys


class TestDeleteKeys:
    def test_delete_removes_key(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        keystore.set_api_key("gemini", _FAKE_GEMINI_KEY)
        client = _client(deps)
        assert client.get("/api/settings").json()["keys"]["gemini"] is True

        response = client.delete("/api/keys/gemini")
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert client.get("/api/settings").json()["keys"]["gemini"] is False

    def test_delete_unknown_provider_rejected(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        response = _client(deps).delete("/api/keys/openai")
        assert response.status_code == 400

    def test_delete_is_idempotent(self, tmp_path, memory_keyring):
        deps = _make_deps(tmp_path)
        response = _client(deps).delete("/api/keys/anthropic")  # nothing stored
        assert response.status_code == 200

    def test_delete_keystore_unavailable_surfaces_503(self, tmp_path, broken_keyring):
        deps = _make_deps(tmp_path)
        response = _client(deps).delete("/api/keys/gemini")
        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "keystore_unavailable"


# ------------------------------------------------------------------ create_app wiring


class TestCreateAppWiring:
    def test_settings_router_mounted_alongside_static_and_ws(self, tmp_path, memory_keyring):
        # Both sides of the boundary: the settings router must resolve even though
        # create_app also mounts StaticFiles at "/" (a catch-all).
        from server.safety.audit import AuditLog
        from server.safety.gate import SafetyGate
        from server.web.app import WebDeps, create_app
        from server.web.approval_bridge import ApprovalChannel

        from .test_runner_self_correction import ScriptedProvider
        from .test_safety_gate import FakeConsole

        audit = AuditLog(tmp_path / "audit")
        channel = ApprovalChannel(timeout_seconds=2.0)
        gate = SafetyGate(console=FakeConsole(), audit=audit, approval_port=channel)
        ui_dist = tmp_path / "dist"
        ui_dist.mkdir()
        (ui_dist / "index.html").write_text("<html>ui</html>", encoding="utf-8")

        deps = WebDeps(
            gate=gate,
            provider=ScriptedProvider([]),
            system_prefix="PREFIX",
            audit=audit,
            approval_channel=channel,
            ui_dist=ui_dist,
            settings=_make_deps(tmp_path),
        )
        with TestClient(create_app(deps)) as client:
            api = client.get("/api/settings")
            assert api.status_code == 200
            assert "settings" in api.json()
            # Static mount still serves the SPA index at "/".
            assert client.get("/").status_code == 200
            # And /healthz still works.
            assert client.get("/healthz").json()["ok"] is True


# ------------------------------------------------------------------ SAFETY: no OSC surface
#
# The interim M3 per-module OSC-send-surface guard for the settings API is
# CONSOLIDATED into the M10 AC-DEPLOY-014 ③ fail-closed allowlist scan
# (``server/tests/test_deploy_safety_invariants.py`` ::
# ``TestAcDeploy014OscSendSurfaceAllowlist``), which scans every server module —
# including server/web/settings_api.py — against one named send-surface allowlist.
