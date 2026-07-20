"""Tests for the secure key-storage adapter (M2 — REQ-DEPLOY-006/006a/007).

Covers AC-DEPLOY-004 (keys live ONLY in the OS credential store; zero key
strings in any file the app writes; env-scrub) and AC-DEPLOY-016 (credential
store unavailable/locked/denied -> explicit error + session-only in-memory
fallback, never a plaintext-disk fallback).

Testing discipline: the real macOS Keychain is NEVER touched. Every test that
exercises the keyring path installs a hand-rolled in-memory backend (or a
deliberately-broken backend to simulate unavailable/locked/denied), and the
default backend is restored in teardown. This keeps the suite deterministic and
lets the store-unavailable failure branch (the exact regression M2 exists to
prevent) be exercised explicitly.
"""

from __future__ import annotations

import json

import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

from server.deploy import keystore
from server.deploy.settings import UserSettings, save_user_settings
from server.llm.config import ConfigError, _reject_credentials

# Obviously-fake, unique key strings so the plaintext-scan greps are meaningful.
_FAKE_ANTHROPIC_KEY = "sk-ant-FAKE-KEYSTORE-TEST-000111222333"
_FAKE_GEMINI_KEY = "AIzaFAKEGEMINIKEYSTORETEST000111222333"


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
    backend = _MemoryKeyring()
    keyring.set_keyring(backend)
    try:
        yield backend
    finally:
        keyring.set_keyring(original)
        keystore.clear_session_keys()


@pytest.fixture
def broken_keyring():
    original = keyring.get_keyring()
    backend = _BrokenKeyring()
    keyring.set_keyring(backend)
    try:
        yield backend
    finally:
        keyring.set_keyring(original)
        keystore.clear_session_keys()


class TestServiceName:
    def test_service_name_is_stable_bundle_identifier(self):
        # The service name is the ACL / identity anchor (bundle id). It MUST NOT
        # churn — a change re-keys every stored credential.
        assert keystore.SERVICE_NAME == "com.grandma3copilot.app"


class TestPersistentRoundtrip:
    def test_set_then_get_roundtrip(self, memory_keyring):
        keystore.set_api_key("anthropic", _FAKE_ANTHROPIC_KEY)
        keystore.set_api_key("gemini", _FAKE_GEMINI_KEY)
        assert keystore.get_api_key("anthropic") == _FAKE_ANTHROPIC_KEY
        assert keystore.get_api_key("gemini") == _FAKE_GEMINI_KEY

    def test_get_unset_provider_returns_none(self, memory_keyring):
        assert keystore.get_api_key("anthropic") is None

    def test_delete_removes_key(self, memory_keyring):
        keystore.set_api_key("gemini", _FAKE_GEMINI_KEY)
        keystore.delete_api_key("gemini")
        assert keystore.get_api_key("gemini") is None

    def test_delete_unset_provider_is_idempotent(self, memory_keyring):
        # No error even though nothing is stored (idempotent delete).
        keystore.delete_api_key("anthropic")

    def test_stored_under_single_service_name(self, memory_keyring):
        keystore.set_api_key("anthropic", _FAKE_ANTHROPIC_KEY)
        # The key must be retrievable from the one stable service name.
        assert keyring.get_password(keystore.SERVICE_NAME, "anthropic") == _FAKE_ANTHROPIC_KEY

    @pytest.mark.parametrize("provider", ["", "openai", "azure", "GEMINI"])
    def test_unknown_provider_rejected(self, memory_keyring, provider):
        with pytest.raises(keystore.KeystoreError):
            keystore.set_api_key(provider, _FAKE_GEMINI_KEY)
        with pytest.raises(keystore.KeystoreError):
            keystore.get_api_key(provider)

    @pytest.mark.parametrize("key", ["", "   "])
    def test_empty_key_rejected(self, memory_keyring, key):
        with pytest.raises(keystore.KeystoreError):
            keystore.set_api_key("anthropic", key)


class TestEnvInjection:
    def test_env_vars_for_provider(self):
        assert keystore.env_vars_for_provider("anthropic") == ("ANTHROPIC_API_KEY",)
        assert keystore.env_vars_for_provider("gemini") == ("GEMINI_API_KEY", "GOOGLE_API_KEY")

    def test_inject_anthropic(self, memory_keyring):
        keystore.set_api_key("anthropic", _FAKE_ANTHROPIC_KEY)
        env: dict[str, str] = {}
        names = keystore.inject_key_for_provider("anthropic", environ=env)
        assert names == ["ANTHROPIC_API_KEY"]
        assert env == {"ANTHROPIC_API_KEY": _FAKE_ANTHROPIC_KEY}

    def test_inject_gemini_sets_both_aliases(self, memory_keyring):
        keystore.set_api_key("gemini", _FAKE_GEMINI_KEY)
        env: dict[str, str] = {}
        names = keystore.inject_key_for_provider("gemini", environ=env)
        assert names == ["GEMINI_API_KEY", "GOOGLE_API_KEY"]
        assert env["GEMINI_API_KEY"] == _FAKE_GEMINI_KEY
        assert env["GOOGLE_API_KEY"] == _FAKE_GEMINI_KEY

    def test_inject_missing_key_is_noop(self, memory_keyring):
        env: dict[str, str] = {}
        names = keystore.inject_key_for_provider("anthropic", environ=env)
        assert names == []
        assert env == {}

    def test_inject_active_provider_key_integrates_with_settings(self, memory_keyring, tmp_path):
        # M1 seam: the active provider comes from resolve_effective_settings.
        user_path = tmp_path / "settings.toml"
        save_user_settings(
            UserSettings(
                active_provider="anthropic",
                console_host="127.0.0.1",
                console_port=8000,
                receive_port=9000,
                web_host="127.0.0.1",
                web_port=8765,
                plugin_import_dir=str(tmp_path / "plugins"),
            ),
            user_path,
        )
        keystore.set_api_key("anthropic", _FAKE_ANTHROPIC_KEY)
        env: dict[str, str] = {}
        names = keystore.inject_active_provider_key(
            environ=env, user_path=user_path, seed_path=tmp_path / "no-seed.toml"
        )
        assert names == ["ANTHROPIC_API_KEY"]
        assert env["ANTHROPIC_API_KEY"] == _FAKE_ANTHROPIC_KEY


class TestStoreUnavailable:
    """AC-DEPLOY-016 — store unavailable/locked/denied handling."""

    def test_set_raises_explicit_error_no_plaintext_fallback(self, broken_keyring):
        with pytest.raises(keystore.KeystoreUnavailableError):
            keystore.set_api_key("anthropic", _FAKE_ANTHROPIC_KEY)

    def test_unavailable_error_is_keystore_error_subclass(self):
        assert issubclass(keystore.KeystoreUnavailableError, keystore.KeystoreError)

    def test_get_raises_when_store_broken_and_no_session(self, broken_keyring):
        with pytest.raises(keystore.KeystoreUnavailableError):
            keystore.get_api_key("anthropic")

    def test_session_only_path_works_when_store_broken(self, broken_keyring):
        keystore.set_session_api_key("anthropic", _FAKE_ANTHROPIC_KEY)
        # Session key is returned without raising, even though the store is broken.
        assert keystore.get_api_key("anthropic") == _FAKE_ANTHROPIC_KEY
        env: dict[str, str] = {}
        names = keystore.inject_key_for_provider("anthropic", environ=env)
        assert names == ["ANTHROPIC_API_KEY"]
        assert env["ANTHROPIC_API_KEY"] == _FAKE_ANTHROPIC_KEY

    def test_session_key_takes_precedence_over_store(self, memory_keyring):
        keystore.set_api_key("anthropic", "stored-value")
        keystore.set_session_api_key("anthropic", _FAKE_ANTHROPIC_KEY)
        assert keystore.get_api_key("anthropic") == _FAKE_ANTHROPIC_KEY

    def test_delete_raises_when_store_broken(self, broken_keyring):
        with pytest.raises(keystore.KeystoreUnavailableError):
            keystore.delete_api_key("anthropic")

    def test_clear_session_keys_removes_session_key(self, broken_keyring):
        keystore.set_session_api_key("anthropic", _FAKE_ANTHROPIC_KEY)
        keystore.clear_session_keys()
        with pytest.raises(keystore.KeystoreUnavailableError):
            keystore.get_api_key("anthropic")

    def test_isolated_session_store_instance(self, broken_keyring):
        session = keystore.SessionKeyStore()
        keystore.set_session_api_key("gemini", _FAKE_GEMINI_KEY, session=session)
        assert keystore.get_api_key("gemini", session=session) == _FAKE_GEMINI_KEY
        # The module-default session is untouched by the isolated instance.
        with pytest.raises(keystore.KeystoreUnavailableError):
            keystore.get_api_key("gemini")


class TestNoPlaintextLeak:
    """AC-DEPLOY-004 (2) + AC-DEPLOY-016 (1) — zero key strings on disk."""

    def test_no_key_string_in_any_written_file(self, memory_keyring, tmp_path):
        keystore.set_api_key("anthropic", _FAKE_ANTHROPIC_KEY)
        env: dict[str, str] = {"PATH": "/usr/bin"}
        keystore.inject_key_for_provider("anthropic", environ=env)

        # Files the app writes: settings, a log line, a crash/diagnostic dump.
        settings_path = tmp_path / "settings.toml"
        save_user_settings(
            UserSettings(
                active_provider="anthropic",
                console_host="127.0.0.1",
                console_port=8000,
                receive_port=9000,
                web_host="127.0.0.1",
                web_port=8765,
                plugin_import_dir=str(tmp_path / "plugins"),
            ),
            settings_path,
        )
        log_path = tmp_path / "app.log"
        log_path.write_text("provider client started for anthropic\n", encoding="utf-8")
        crash_path = tmp_path / "crash.json"
        # DECIDE-M6: a crash/diagnostic dump MUST route env through scrub_environ.
        crash_path.write_text(json.dumps(keystore.scrub_environ(env)), encoding="utf-8")

        for path in (settings_path, log_path, crash_path):
            assert _FAKE_ANTHROPIC_KEY not in path.read_text(encoding="utf-8"), path

    def test_broken_store_session_fallback_leaves_no_disk_plaintext(self, broken_keyring, tmp_path):
        keystore.set_session_api_key("gemini", _FAKE_GEMINI_KEY)
        env: dict[str, str] = {}
        keystore.inject_key_for_provider("gemini", environ=env)
        settings_path = tmp_path / "settings.toml"
        save_user_settings(
            UserSettings(
                active_provider="gemini",
                console_host="127.0.0.1",
                console_port=8000,
                receive_port=9000,
                web_host="127.0.0.1",
                web_port=8765,
                plugin_import_dir=str(tmp_path / "plugins"),
            ),
            settings_path,
        )
        crash_path = tmp_path / "crash.json"
        crash_path.write_text(json.dumps(keystore.scrub_environ(env)), encoding="utf-8")

        for path in (settings_path, crash_path):
            assert _FAKE_GEMINI_KEY not in path.read_text(encoding="utf-8"), path

        # Session end: clearing leaves no residue anywhere (nothing on disk).
        keystore.clear_session_keys()
        for path in tmp_path.rglob("*"):
            if path.is_file():
                assert _FAKE_GEMINI_KEY not in path.read_text(encoding="utf-8"), path


class TestEnvScrub:
    """AC-DEPLOY-004 (2) — env-scrub (DECIDE-M6)."""

    def test_scrubs_provider_key_values(self):
        env = {
            "ANTHROPIC_API_KEY": _FAKE_ANTHROPIC_KEY,
            "GEMINI_API_KEY": _FAKE_GEMINI_KEY,
            "GOOGLE_API_KEY": _FAKE_GEMINI_KEY,
            "PATH": "/usr/bin",
            "HOME": "/home/operator",
        }
        scrubbed = keystore.scrub_environ(env)
        blob = json.dumps(scrubbed)
        assert _FAKE_ANTHROPIC_KEY not in blob
        assert _FAKE_GEMINI_KEY not in blob
        assert scrubbed["ANTHROPIC_API_KEY"] == keystore.REDACTED
        assert scrubbed["GEMINI_API_KEY"] == keystore.REDACTED
        assert scrubbed["GOOGLE_API_KEY"] == keystore.REDACTED

    def test_preserves_non_sensitive_values(self):
        scrubbed = keystore.scrub_environ({"PATH": "/usr/bin", "HOME": "/home/operator"})
        assert scrubbed["PATH"] == "/usr/bin"
        assert scrubbed["HOME"] == "/home/operator"

    @pytest.mark.parametrize(
        "name",
        ["DB_PASSWORD", "MY_TOKEN", "CLIENT_SECRET", "SERVICE_CREDENTIAL", "SOME_APIKEY"],
    )
    def test_scrubs_credential_substring_names(self, name):
        scrubbed = keystore.scrub_environ({name: "super-secret-value"})
        assert scrubbed[name] == keystore.REDACTED

    def test_does_not_mutate_input(self):
        env = {"ANTHROPIC_API_KEY": _FAKE_ANTHROPIC_KEY}
        keystore.scrub_environ(env)
        assert env["ANTHROPIC_API_KEY"] == _FAKE_ANTHROPIC_KEY

    def test_default_environ_is_scrubbed(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", _FAKE_ANTHROPIC_KEY)
        scrubbed = keystore.scrub_environ()
        assert scrubbed["ANTHROPIC_API_KEY"] == keystore.REDACTED
        assert _FAKE_ANTHROPIC_KEY not in json.dumps(scrubbed)


class TestCredentialRejectionPreserved:
    """AC-DEPLOY-004 (3) — the M1/MVP credential-key rejection contract holds."""

    def test_config_loader_still_rejects_credential_keys(self):
        with pytest.raises(ConfigError):
            _reject_credentials({"api_key": "leak"}, context="test")

    def test_user_settings_has_no_credential_field(self, tmp_path):
        # The settings schema carries no credential field by construction — the
        # key path is keystore-only, never the settings file.
        settings_path = tmp_path / "settings.toml"
        save_user_settings(
            UserSettings(
                active_provider="gemini",
                console_host="127.0.0.1",
                console_port=8000,
                receive_port=9000,
                web_host="127.0.0.1",
                web_port=8765,
                plugin_import_dir=str(tmp_path / "plugins"),
            ),
            settings_path,
        )
        # Scan only the data (non-comment) lines — the header comment legitimately
        # mentions "OS credential store", which is not a credential field.
        data_lines = [
            line
            for line in settings_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        content = "\n".join(data_lines).lower()
        for token in ("api_key", "apikey", "token", "secret", "password", "credential"):
            assert token not in content
