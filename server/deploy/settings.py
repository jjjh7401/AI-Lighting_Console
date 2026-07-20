"""User-settings storage layer (M1 — REQ-DEPLOY-008, AC-DEPLOY-005).

The packaged app runs from an OS-installed bundle, not a dev checkout, so its
NON-SENSITIVE settings (OSC ports, plugin import directory, active provider)
must live in a user-writable, OS-standard config path — NOT the repo-shipped
``config/provider.toml`` (read-only inside a signed bundle) and NOT CLI args
(no terminal at run time).

This module owns the config-storage LAYER only. Full UI wiring is M3 and
launcher wiring is M6; the integration seam here is
:func:`resolve_effective_settings`, a pure function ``serve.py`` can call to
resolve effective settings. The existing CLI args stay the highest-precedence
override — this layer does not replace them.

Precedence (lowest -> highest):
    built-in defaults < bundled ``provider.toml`` seed < user config file
    < explicit override (CLI/arg).

Format: TOML, read via the stdlib ``tomllib`` (zero extra dependency, reusing
the same choice as :mod:`server.llm.config`). TOML has no stdlib writer, so a
minimal hand-rolled writer serialises the small, fully-known non-sensitive
schema (:func:`_dump_settings_toml`).

Secured (REQ-DEPLOY-008): credentials are NEVER stored here. The user config
loader reuses :mod:`server.llm.config`'s credential-key rejection — so a user
config file that carries an ``api_key`` / ``token`` / ... is rejected outright,
guaranteeing the settings loader and the provider loader share one identical,
drift-free credential-key policy. API keys go to the OS credential store (M2).
"""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Reuse the MVP provider-loader security invariant + provider enum verbatim so
# the settings loader and the provider loader can never drift on which keys
# count as a credential or which providers are supported.
from server.llm.config import (
    SUPPORTED_PROVIDERS,
    ConfigError,
    _reject_credentials,
)

# Bundle anchor — config path, Keychain service name, Tauri identifier, and the
# code-signing identity all derive from this AppName (DECIDE-M1).
APP_NAME = "GrandMA3 Copilot"
_SETTINGS_FILE_NAME = "settings.toml"

# Built-in defaults REUSE the MVP serve.py values verbatim (DECIDE-M9 — OSC
# port drift prevention: the operator aligns onPC OSC output to these ports).
DEFAULT_CONSOLE_HOST = "127.0.0.1"
DEFAULT_CONSOLE_PORT = 8000
DEFAULT_RECEIVE_PORT = 9000
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8765
DEFAULT_ACTIVE_PROVIDER = "gemini"  # matches the shipped config/provider.toml seed
DEFAULT_PLUGIN_IMPORT_DIR = str(
    Path.home() / "MALightingTechnology" / "gma3_library" / "datapools" / "plugins"
)

_PORT_KEYS = ("console_port", "receive_port", "web_port")
_HOST_KEYS = ("console_host", "web_host")
# Recognised non-sensitive keys — the UI<->backend config schema contract (F2).
_RECOGNISED_KEYS = (
    "active_provider",
    *_HOST_KEYS,
    *_PORT_KEYS,
    "plugin_import_dir",
)

_MIN_PORT = 1
_MAX_PORT = 65535


class SettingsError(ValueError):
    """Raised when the user settings file is malformed, out of range, or unsafe."""


@dataclass(frozen=True)
class UserSettings:
    """Validated non-sensitive settings (REQ-DEPLOY-008).

    This is the typed UI<->backend config schema contract. It NEVER carries a
    credential field by construction — API keys live in the OS credential store
    (M2), never in this dataclass or its serialised form.
    """

    active_provider: str
    console_host: str
    console_port: int
    receive_port: int
    web_host: str
    web_port: int
    plugin_import_dir: str


def _resolve_config_dir(
    app_name: str,
    *,
    platform: str,
    os_name: str,
    environ: Mapping[str, str],
    home: Path,
) -> Path:
    """Resolve the OS-standard per-user config directory (pure, testable).

    macOS   -> ~/Library/Application Support/<AppName>
    Windows -> %APPDATA%\\<AppName>   (fallback ~/AppData/Roaming/<AppName>)
    POSIX   -> $XDG_CONFIG_HOME/<AppName>  (fallback ~/.config/<AppName>)
    """
    if platform == "darwin":
        return home / "Library" / "Application Support" / app_name
    if os_name == "nt":
        appdata = environ.get("APPDATA")
        root = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return root / app_name
    xdg = environ.get("XDG_CONFIG_HOME")
    root = Path(xdg) if xdg else home / ".config"
    return root / app_name


def user_config_dir(app_name: str = APP_NAME) -> Path:
    """The OS-standard per-user config directory for this app."""
    return _resolve_config_dir(
        app_name,
        platform=sys.platform,
        os_name=os.name,
        environ=os.environ,
        home=Path.home(),
    )


def user_settings_path(app_name: str = APP_NAME) -> Path:
    """The user settings TOML path (``<config-dir>/settings.toml``)."""
    return user_config_dir(app_name) / _SETTINGS_FILE_NAME


def _require_port(key: str, value: object) -> int:
    # bool is an int subclass — reject it before the range check.
    if not isinstance(value, int) or isinstance(value, bool):
        raise SettingsError(f"{key} must be an integer port, got {value!r}")
    if not (_MIN_PORT <= value <= _MAX_PORT):
        raise SettingsError(f"{key} must be in [{_MIN_PORT}, {_MAX_PORT}], got {value}")
    return value


def _require_host(key: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SettingsError(f"{key} must be a non-empty host string, got {value!r}")
    return value


def _require_provider(value: object) -> str:
    if not isinstance(value, str) or value not in SUPPORTED_PROVIDERS:
        raise SettingsError(f"active_provider must be one of {SUPPORTED_PROVIDERS}, got {value!r}")
    return value


def _require_str(key: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise SettingsError(f"{key} must be a non-empty string, got {value!r}")
    return value


# @MX:ANCHOR: [AUTO] user-config credential-rejection boundary — the sole point
#   where an on-disk user config is admitted into the app; reuses the MVP
#   provider loader's credential-key policy so no credential can enter here.
# @MX:REASON: REQ-DEPLOY-008/AC-DEPLOY-005 security invariant — a user config
#   file must NEVER carry an API key; drift between two credential-key lists
#   would be a plaintext-leak hole, so the one MVP list is reused, not copied.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
def load_user_settings(path: Path | str) -> dict[str, object]:
    """Load + validate the user settings file into a partial value dict.

    Returns only the recognised keys that are present (an absent file yields an
    empty dict). Rejects credential-like keys anywhere in the document and
    validates the type/range of every recognised key. Unknown non-credential
    keys are ignored (forward compatibility).
    """
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise SettingsError(f"user settings file is not valid TOML: {error}") from error

    # Reuse the MVP credential-key rejection verbatim (raises ConfigError);
    # re-raise as SettingsError so callers see one uniform error type.
    try:
        _reject_credentials(data, context=str(path))
    except ConfigError as error:
        raise SettingsError(str(error)) from error

    table = data.get("settings", {})
    if not isinstance(table, dict):
        raise SettingsError("[settings] must be a table")

    values: dict[str, object] = {}
    for key in _RECOGNISED_KEYS:
        if key not in table:
            continue
        values[key] = _validate_field(key, table[key])
    return values


def _validate_field(key: str, value: object) -> object:
    if key in _PORT_KEYS:
        return _require_port(key, value)
    if key in _HOST_KEYS:
        return _require_host(key, value)
    if key == "active_provider":
        return _require_provider(value)
    return _require_str(key, value)  # plugin_import_dir


def _seed_active_provider(seed_path: Path | str) -> str | None:
    """Best-effort read of ``[provider] active`` from the bundled seed."""
    seed_path = Path(seed_path)
    if not seed_path.is_file():
        return None
    try:
        data = tomllib.loads(seed_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    provider = data.get("provider")
    active = provider.get("active") if isinstance(provider, dict) else None
    return active if active in SUPPORTED_PROVIDERS else None


def resolve_effective_settings(
    *,
    user_path: Path | str | None = None,
    seed_path: Path | str | None = None,
    overrides: Mapping[str, object] | None = None,
) -> UserSettings:
    """Resolve effective settings across the precedence chain (the serve.py seam).

    defaults < seed (active provider) < user config file < explicit overrides.
    ``None`` override values are ignored, so a CLI layer may pass ``None`` for
    unset flags without clobbering a lower-precedence layer.
    """
    from server.llm.config import DEFAULT_CONFIG_PATH  # seed default (avoid import cycle cost)

    if user_path is None:
        user_path = user_settings_path()
    if seed_path is None:
        seed_path = DEFAULT_CONFIG_PATH

    # @MX:NOTE: [AUTO] precedence order is load-bearing — an explicit CLI/arg
    #   override MUST win so the operator can force a port (REQ-DEPLOY-026 OSC
    #   port drift prevention); the user file wins over the shipped seed.
    values: dict[str, object] = {
        "active_provider": DEFAULT_ACTIVE_PROVIDER,
        "console_host": DEFAULT_CONSOLE_HOST,
        "console_port": DEFAULT_CONSOLE_PORT,
        "receive_port": DEFAULT_RECEIVE_PORT,
        "web_host": DEFAULT_WEB_HOST,
        "web_port": DEFAULT_WEB_PORT,
        "plugin_import_dir": DEFAULT_PLUGIN_IMPORT_DIR,
    }

    seed_active = _seed_active_provider(seed_path)
    if seed_active is not None:
        values["active_provider"] = seed_active

    values.update(load_user_settings(user_path))

    if overrides:
        for key, value in overrides.items():
            if value is None or key not in _RECOGNISED_KEYS:
                continue
            values[key] = _validate_field(key, value)

    return UserSettings(**values)  # type: ignore[arg-type]


def _toml_escape(value: str) -> str:
    """Escape a string for a TOML basic string (backslash + double-quote)."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _dump_settings_toml(settings: UserSettings) -> str:
    """Serialise the fully-known non-sensitive schema to TOML (no writer dep)."""
    return "\n".join(
        (
            "# GrandMA3 Copilot — user settings (non-sensitive only).",
            "# API keys are NEVER stored here — they live in the OS credential store.",
            "",
            "[settings]",
            f'active_provider = "{_toml_escape(settings.active_provider)}"',
            f'console_host = "{_toml_escape(settings.console_host)}"',
            f"console_port = {settings.console_port}",
            f"receive_port = {settings.receive_port}",
            f'web_host = "{_toml_escape(settings.web_host)}"',
            f"web_port = {settings.web_port}",
            f'plugin_import_dir = "{_toml_escape(settings.plugin_import_dir)}"',
            "",
        )
    )


def save_user_settings(settings: UserSettings, path: Path | str | None = None) -> Path:
    """Atomically persist non-sensitive settings to the user config path.

    Creates the config directory if absent and writes via a same-directory temp
    file + ``os.replace`` so a crash mid-write cannot corrupt the config.
    Returns the written path.
    """
    path = Path(path) if path is not None else user_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _dump_settings_toml(settings)

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp_name, path)
    except BaseException:
        # Best-effort cleanup of the temp file on any failure before the swap.
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    return path
