"""Provider configuration — the config-file SSOT for provider selection (REQ-MVP-039).

The TOML config file carries the provider choice, per-provider model pins, and
the fallback-detection operational parameters (REQ-MVP-040 part ii, default
N=20 / M=2). It NEVER carries credentials: API keys are injected exclusively
via environment variables (``ANTHROPIC_API_KEY``, ``GEMINI_API_KEY`` /
``GOOGLE_API_KEY``) and the loader rejects credential-looking keys outright.

Format: TOML via the stdlib ``tomllib`` (zero extra dependency). Switching the
active provider is a one-value config edit — no code change (AC-MVP-026 part 1).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_PROVIDERS = ("anthropic", "gemini")

# Repo-shipped runtime config (project root /config/provider.toml).
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "provider.toml"

_CREDENTIAL_KEYS = frozenset(
    {"api_key", "apikey", "api-key", "token", "secret", "credential", "credentials", "password"}
)


class ConfigError(ValueError):
    """Raised when the provider config file is missing, malformed, or unsafe."""


@dataclass(frozen=True)
class AnthropicSettings:
    """Anthropic adapter settings (REQ-MVP-006 pins the model to claude-opus-4-8)."""

    model: str
    prompt_caching: bool = True
    max_tokens: int = 16000
    thinking: str = "adaptive"  # "adaptive" | "none"
    effort: str = "high"  # "" omits output_config

    # Fixed, recorded inference settings — the error-rate measurement (M6)
    # requires the production inference configuration to be pinned in config.


@dataclass(frozen=True)
class GeminiSettings:
    """Gemini adapter settings — model pin is config-changeable (REQ-MVP-039)."""

    model: str
    context_caching: bool = True
    cache_ttl_seconds: int = 3600


@dataclass(frozen=True)
class FallbackSettings:
    """REQ-MVP-040 part ii persistent-miss detection parameters (AD2-m1)."""

    window_turns: int = 20  # N — rolling window of judged turns
    consecutive_windows: int = 2  # M — consecutive violating windows
    threshold_seconds: float = 10.0  # round-trip median threshold


@dataclass(frozen=True)
class ProviderConfig:
    """Validated provider configuration — exactly ONE active provider."""

    active: str
    anthropic: AnthropicSettings
    gemini: GeminiSettings
    fallback: FallbackSettings


def _reject_credentials(table: dict, *, context: str) -> None:
    for key, value in table.items():
        if key.lower() in _CREDENTIAL_KEYS:
            raise ConfigError(
                f"credential-like key {key!r} found in {context} — API keys must be "
                "provided via environment variables only, never the config file"
            )
        if isinstance(value, dict):
            _reject_credentials(value, context=f"{context}.{key}")


def _require_positive_int(table: dict, key: str, default: int) -> int:
    value = table.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigError(f"fallback.{key} must be a positive integer, got {value!r}")
    return value


def _provider_table(data: dict, name: str) -> dict:
    provider = data.get("provider")
    if not isinstance(provider, dict):
        raise ConfigError("config must contain a [provider] table")
    table = provider.get(name)
    if not isinstance(table, dict):
        raise ConfigError(f"config must contain a [provider.{name}] table")
    model = table.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ConfigError(f"provider.{name}.model must be a non-empty pinned model id")
    return table


def load_provider_config(path: Path | str = DEFAULT_CONFIG_PATH) -> ProviderConfig:
    """Load and validate the provider config file."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"provider config file not found: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"provider config is not valid TOML: {error}") from error

    _reject_credentials(data, context=str(path))

    provider = data.get("provider")
    if not isinstance(provider, dict):
        raise ConfigError("config must contain a [provider] table")
    active = provider.get("active")
    if active is None:
        raise ConfigError("provider.active is required")
    if not isinstance(active, str):
        raise ConfigError(f"provider.active must be a single provider name, got {active!r}")
    if active not in SUPPORTED_PROVIDERS:
        raise ConfigError(f"provider.active must be one of {SUPPORTED_PROVIDERS}, got {active!r}")

    anthropic_table = _provider_table(data, "anthropic")
    gemini_table = _provider_table(data, "gemini")
    fallback_table = data.get("fallback", {})
    if not isinstance(fallback_table, dict):
        raise ConfigError("[fallback] must be a table")

    threshold = fallback_table.get("threshold_seconds", 10.0)
    if not isinstance(threshold, int | float) or isinstance(threshold, bool) or threshold <= 0:
        raise ConfigError(f"fallback.threshold_seconds must be positive, got {threshold!r}")

    return ProviderConfig(
        active=active,
        anthropic=AnthropicSettings(
            model=anthropic_table["model"],
            prompt_caching=bool(anthropic_table.get("prompt_caching", True)),
            max_tokens=int(anthropic_table.get("max_tokens", 16000)),
            thinking=str(anthropic_table.get("thinking", "adaptive")),
            effort=str(anthropic_table.get("effort", "high")),
        ),
        gemini=GeminiSettings(
            model=gemini_table["model"],
            context_caching=bool(gemini_table.get("context_caching", True)),
            cache_ttl_seconds=int(gemini_table.get("cache_ttl_seconds", 3600)),
        ),
        fallback=FallbackSettings(
            window_turns=_require_positive_int(fallback_table, "window_turns", 20),
            consecutive_windows=_require_positive_int(fallback_table, "consecutive_windows", 2),
            threshold_seconds=float(threshold),
        ),
    )
