"""User-settings storage layer tests (M1 — REQ-DEPLOY-008, AC-DEPLOY-005).

The packaged app stores NON-SENSITIVE settings (OSC ports, plugin import
directory, active provider) in an OS-standard, user-writable config path. It
NEVER stores credentials — the user config loader rejects credential-like keys,
mirroring ``server.llm.config`` (SPEC-COPILOT-MVP-001 Secured constraint).

Precedence (lowest -> highest): built-in defaults < bundled ``provider.toml``
seed < user config file < explicit override (CLI/arg).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.deploy.settings import (
    APP_NAME,
    DEFAULT_ACTIVE_PROVIDER,
    DEFAULT_CONSOLE_HOST,
    DEFAULT_CONSOLE_PORT,
    DEFAULT_PLUGIN_IMPORT_DIR,
    DEFAULT_RECEIVE_PORT,
    DEFAULT_WEB_HOST,
    DEFAULT_WEB_PORT,
    SettingsError,
    UserSettings,
    _resolve_config_dir,
    load_user_settings,
    resolve_effective_settings,
    save_user_settings,
    user_config_dir,
    user_settings_path,
)


def _seed(tmp_path: Path, active: str = "gemini") -> Path:
    """A minimal bundled provider.toml seed (active provider only matters here)."""
    path = tmp_path / "seed_provider.toml"
    path.write_text(
        f'[provider]\nactive = "{active}"\n\n'
        '[provider.anthropic]\nmodel = "claude-opus-4-8"\n\n'
        '[provider.gemini]\nmodel = "gemini-3.5-flash"\n',
        encoding="utf-8",
    )
    return path


class TestUserConfigPath:
    """REQ-DEPLOY-008: OS-standard user config path resolution (stdlib only)."""

    def test_app_name_is_the_bundle_anchor(self):
        assert APP_NAME == "GrandMA3 Copilot"

    def test_macos_uses_application_support(self):
        home = Path("/Users/op")
        got = _resolve_config_dir(
            APP_NAME, platform="darwin", os_name="posix", environ={}, home=home
        )
        assert got == home / "Library" / "Application Support" / "GrandMA3 Copilot"

    def test_windows_uses_appdata_env(self):
        got = _resolve_config_dir(
            APP_NAME,
            platform="win32",
            os_name="nt",
            environ={"APPDATA": r"C:\Users\op\AppData\Roaming"},
            home=Path(r"C:\Users\op"),
        )
        assert got == Path(r"C:\Users\op\AppData\Roaming") / "GrandMA3 Copilot"

    def test_windows_without_appdata_falls_back_to_home_roaming(self):
        home = Path(r"C:\Users\op")
        got = _resolve_config_dir(APP_NAME, platform="win32", os_name="nt", environ={}, home=home)
        assert got == home / "AppData" / "Roaming" / "GrandMA3 Copilot"

    def test_linux_honours_xdg_config_home(self):
        got = _resolve_config_dir(
            APP_NAME,
            platform="linux",
            os_name="posix",
            environ={"XDG_CONFIG_HOME": "/home/op/.config-alt"},
            home=Path("/home/op"),
        )
        assert got == Path("/home/op/.config-alt") / "GrandMA3 Copilot"

    def test_linux_defaults_to_dot_config(self):
        home = Path("/home/op")
        got = _resolve_config_dir(
            APP_NAME, platform="linux", os_name="posix", environ={}, home=home
        )
        assert got == home / ".config" / "GrandMA3 Copilot"

    def test_public_helpers_return_real_paths(self):
        directory = user_config_dir()
        assert directory.name == "GrandMA3 Copilot"
        assert user_settings_path() == directory / "settings.toml"


class TestBuiltinDefaults:
    """Defaults REUSE the MVP serve.py values (DECIDE-M9 drift prevention)."""

    def test_defaults_match_serve_py(self):
        assert DEFAULT_CONSOLE_HOST == "127.0.0.1"
        assert DEFAULT_CONSOLE_PORT == 8000
        assert DEFAULT_RECEIVE_PORT == 9000
        assert DEFAULT_WEB_HOST == "127.0.0.1"
        assert DEFAULT_WEB_PORT == 8765
        assert DEFAULT_PLUGIN_IMPORT_DIR.endswith(
            "MALightingTechnology/gma3_library/datapools/plugins"
        )

    def test_resolve_with_nothing_yields_builtin_defaults(self, tmp_path):
        settings = resolve_effective_settings(
            user_path=tmp_path / "absent.toml", seed_path=tmp_path / "absent_seed.toml"
        )
        assert settings.console_host == DEFAULT_CONSOLE_HOST
        assert settings.console_port == DEFAULT_CONSOLE_PORT
        assert settings.receive_port == DEFAULT_RECEIVE_PORT
        assert settings.web_host == DEFAULT_WEB_HOST
        assert settings.web_port == DEFAULT_WEB_PORT
        assert settings.plugin_import_dir == DEFAULT_PLUGIN_IMPORT_DIR
        assert settings.active_provider == "gemini"


class TestSaveLoadRoundtrip:
    """AC-DEPLOY-005: save to user config path, reload, values persist."""

    def test_save_creates_directory_and_file(self, tmp_path):
        target = tmp_path / "nested" / "dir" / "settings.toml"
        settings = UserSettings(
            active_provider="gemini",
            console_host="127.0.0.1",
            console_port=8000,
            receive_port=9000,
            web_host="127.0.0.1",
            web_port=8765,
            plugin_import_dir="/tmp/plugins",
        )
        save_user_settings(settings, target)
        assert target.is_file()

    def test_roundtrip_preserves_non_sensitive_values(self, tmp_path):
        target = tmp_path / "settings.toml"
        settings = UserSettings(
            active_provider="anthropic",
            console_host="127.0.0.1",
            console_port=8010,
            receive_port=9010,
            web_host="127.0.0.1",
            web_port=8770,
            plugin_import_dir="/tmp/plugins/dir",
        )
        save_user_settings(settings, target)
        loaded = load_user_settings(target)
        assert loaded["active_provider"] == "anthropic"
        assert loaded["console_port"] == 8010
        assert loaded["receive_port"] == 9010
        assert loaded["web_port"] == 8770
        assert loaded["plugin_import_dir"] == "/tmp/plugins/dir"

    def test_windows_style_path_roundtrips(self, tmp_path):
        # The hand-rolled TOML writer must escape backslashes so a Windows path
        # survives the write -> tomllib.read round trip.
        target = tmp_path / "settings.toml"
        win_dir = r"C:\Users\op\MALightingTechnology\plugins"
        settings = UserSettings(
            active_provider="gemini",
            console_host="127.0.0.1",
            console_port=8000,
            receive_port=9000,
            web_host="127.0.0.1",
            web_port=8765,
            plugin_import_dir=win_dir,
        )
        save_user_settings(settings, target)
        assert load_user_settings(target)["plugin_import_dir"] == win_dir

    def test_load_absent_file_returns_empty(self, tmp_path):
        assert load_user_settings(tmp_path / "nope.toml") == {}


class TestPrecedence:
    """Explicit override > user config file > seed > built-in default."""

    def test_seed_active_provider_overrides_builtin(self, tmp_path):
        settings = resolve_effective_settings(
            user_path=tmp_path / "absent.toml", seed_path=_seed(tmp_path, active="anthropic")
        )
        assert settings.active_provider == "anthropic"

    def test_user_file_overrides_seed(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text('[settings]\nactive_provider = "gemini"\n', encoding="utf-8")
        settings = resolve_effective_settings(
            user_path=user, seed_path=_seed(tmp_path, active="anthropic")
        )
        assert settings.active_provider == "gemini"

    def test_override_beats_user_file(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text("[settings]\nweb_port = 8770\n", encoding="utf-8")
        settings = resolve_effective_settings(
            user_path=user,
            seed_path=tmp_path / "absent_seed.toml",
            overrides={"web_port": 9999},
        )
        assert settings.web_port == 9999

    def test_override_none_values_are_ignored(self, tmp_path):
        # CLI layers pass None for unset flags — None must NOT clobber a lower layer.
        user = tmp_path / "settings.toml"
        user.write_text("[settings]\nconsole_port = 8055\n", encoding="utf-8")
        settings = resolve_effective_settings(
            user_path=user,
            seed_path=tmp_path / "absent_seed.toml",
            overrides={"console_port": None},
        )
        assert settings.console_port == 8055

    def test_partial_user_file_only_overlays_present_keys(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text("[settings]\nconsole_port = 8001\n", encoding="utf-8")
        settings = resolve_effective_settings(
            user_path=user, seed_path=tmp_path / "absent_seed.toml"
        )
        assert settings.console_port == 8001
        assert settings.web_port == DEFAULT_WEB_PORT  # untouched key keeps default

    def test_malformed_seed_falls_back_to_builtin_provider(self, tmp_path):
        seed = tmp_path / "seed_provider.toml"
        seed.write_text("[provider\nactive = \n", encoding="utf-8")  # invalid TOML
        settings = resolve_effective_settings(user_path=tmp_path / "absent.toml", seed_path=seed)
        assert settings.active_provider == DEFAULT_ACTIVE_PROVIDER

    def test_seed_with_unsupported_active_is_ignored(self, tmp_path):
        seed = tmp_path / "seed_provider.toml"
        seed.write_text('[provider]\nactive = "openai"\n', encoding="utf-8")
        settings = resolve_effective_settings(user_path=tmp_path / "absent.toml", seed_path=seed)
        assert settings.active_provider == DEFAULT_ACTIVE_PROVIDER

    def test_seed_without_provider_table_is_ignored(self, tmp_path):
        seed = tmp_path / "seed_provider.toml"
        seed.write_text("[other]\nx = 1\n", encoding="utf-8")
        settings = resolve_effective_settings(user_path=tmp_path / "absent.toml", seed_path=seed)
        assert settings.active_provider == DEFAULT_ACTIVE_PROVIDER

    def test_unknown_override_key_is_ignored(self, tmp_path):
        settings = resolve_effective_settings(
            user_path=tmp_path / "absent.toml",
            seed_path=tmp_path / "absent_seed.toml",
            overrides={"bogus_key": "ignored"},
        )
        assert settings.web_port == DEFAULT_WEB_PORT

    def test_default_paths_resolve_against_the_real_shipped_seed(self):
        # No explicit paths -> uses user_settings_path() + the shipped
        # config/provider.toml seed (read-only). Assert shape, not exact values,
        # so a real user settings file on the host cannot make this flaky.
        settings = resolve_effective_settings()
        assert settings.active_provider in ("gemini", "anthropic")
        assert 1 <= settings.web_port <= 65535
        assert 1 <= settings.console_port <= 65535


class TestValidation:
    """Type + range validation (ports 1-65535, host strings, provider enum)."""

    @pytest.mark.parametrize("bad_port", [0, -1, 65536, 70000])
    def test_out_of_range_port_rejected(self, tmp_path, bad_port):
        user = tmp_path / "settings.toml"
        user.write_text(f"[settings]\nweb_port = {bad_port}\n", encoding="utf-8")
        with pytest.raises(SettingsError, match="web_port"):
            resolve_effective_settings(user_path=user, seed_path=tmp_path / "absent_seed.toml")

    def test_non_integer_port_rejected(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text('[settings]\nconsole_port = "8000"\n', encoding="utf-8")
        with pytest.raises(SettingsError, match="console_port"):
            resolve_effective_settings(user_path=user, seed_path=tmp_path / "absent_seed.toml")

    def test_boolean_is_not_a_valid_port(self, tmp_path):
        # bool is an int subclass — must be rejected explicitly.
        user = tmp_path / "settings.toml"
        user.write_text("[settings]\nweb_port = true\n", encoding="utf-8")
        with pytest.raises(SettingsError, match="web_port"):
            resolve_effective_settings(user_path=user, seed_path=tmp_path / "absent_seed.toml")

    def test_empty_host_rejected(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text('[settings]\nconsole_host = ""\n', encoding="utf-8")
        with pytest.raises(SettingsError, match="console_host"):
            resolve_effective_settings(user_path=user, seed_path=tmp_path / "absent_seed.toml")

    def test_unsupported_active_provider_rejected(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text('[settings]\nactive_provider = "openai"\n', encoding="utf-8")
        with pytest.raises(SettingsError, match="active_provider"):
            resolve_effective_settings(user_path=user, seed_path=tmp_path / "absent_seed.toml")

    def test_non_string_plugin_dir_rejected(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text("[settings]\nplugin_import_dir = 42\n", encoding="utf-8")
        with pytest.raises(SettingsError, match="plugin_import_dir"):
            resolve_effective_settings(user_path=user, seed_path=tmp_path / "absent_seed.toml")

    def test_settings_table_must_be_a_table(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text('settings = "oops"\n', encoding="utf-8")
        with pytest.raises(SettingsError, match="settings"):
            load_user_settings(user)

    def test_malformed_toml_rejected(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text("[settings\nweb_port = 8765\n", encoding="utf-8")
        with pytest.raises(SettingsError, match="TOML"):
            load_user_settings(user)


class TestCredentialRejection:
    """AC-DEPLOY-005 / REQ-DEPLOY-008: a user config can NEVER carry a credential."""

    @pytest.mark.parametrize(
        "cred_key", ["api_key", "apikey", "token", "secret", "password", "credential"]
    )
    def test_credential_like_key_rejected(self, tmp_path, cred_key):
        user = tmp_path / "settings.toml"
        user.write_text(
            f'[settings]\nweb_port = 8765\n{cred_key} = "leaked-value"\n', encoding="utf-8"
        )
        with pytest.raises((SettingsError, ValueError), match="credential"):
            load_user_settings(user)

    def test_nested_credential_key_rejected(self, tmp_path):
        # The scan must recurse into nested tables, not only the top level.
        user = tmp_path / "settings.toml"
        user.write_text(
            '[settings]\nweb_port = 8765\n\n[settings.extra]\napi_key = "sk-nope"\n',
            encoding="utf-8",
        )
        with pytest.raises((SettingsError, ValueError), match="credential"):
            load_user_settings(user)

    def test_resolve_rejects_credential_in_user_file(self, tmp_path):
        user = tmp_path / "settings.toml"
        user.write_text('[settings]\ntoken = "sk-live"\n', encoding="utf-8")
        with pytest.raises((SettingsError, ValueError), match="credential"):
            resolve_effective_settings(user_path=user, seed_path=tmp_path / "absent_seed.toml")

    def test_saved_file_contains_no_credential_field(self, tmp_path):
        target = tmp_path / "settings.toml"
        settings = UserSettings(
            active_provider="gemini",
            console_host="127.0.0.1",
            console_port=8000,
            receive_port=9000,
            web_host="127.0.0.1",
            web_port=8765,
            plugin_import_dir="/tmp/plugins",
        )
        save_user_settings(settings, target)
        # No credential-like key may appear as a TOML assignment. (A benign
        # comment mentioning "credential store" is fine — assert on keys, not
        # on the raw substring.)
        banned = ("api_key", "apikey", "token", "secret", "password", "credential")
        for line in target.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip().lower()
            assert key not in banned
        # And the written file reloads cleanly (no credential rejection tripped).
        assert load_user_settings(target)["active_provider"] == "gemini"
