"""Provider config + factory tests (M3 — AC-MVP-013, AC-MVP-026 part 1).

REQ-MVP-006: single active provider, single pinned model (Anthropic ->
``claude-opus-4-8``; Gemini -> the model pinned in the config file).
REQ-MVP-039: provider selection is config-file only — switching providers is a
config value change, zero code diff.
Secured constraint: the config file carries provider choice + model pins +
fallback parameters ONLY — never credentials (keys come from env vars).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.llm.config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    load_provider_config,
)
from server.llm.factory import build_provider


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "provider.toml"
    path.write_text(text, encoding="utf-8")
    return path


_BASE_CONFIG = """\
[provider]
active = "anthropic"

[provider.anthropic]
model = "claude-opus-4-8"

[provider.gemini]
model = "gemini-2.5-pro"
"""


class TestShippedConfig:
    """The repo-shipped config/provider.toml is the runtime SSOT (AC-MVP-013)."""

    def test_shipped_config_exists(self):
        assert DEFAULT_CONFIG_PATH.is_file(), DEFAULT_CONFIG_PATH

    def test_anthropic_model_is_pinned_to_opus_4_8(self):
        config = load_provider_config(DEFAULT_CONFIG_PATH)
        assert config.anthropic.model == "claude-opus-4-8"

    def test_gemini_model_is_pinned_in_config(self):
        # Pin decided at the M3 check-in (2026-07-16): latest stable GA model,
        # web-verified against ai.google.dev/gemini-api/docs/models.
        config = load_provider_config(DEFAULT_CONFIG_PATH)
        assert config.gemini.model == "gemini-3.5-flash"

    def test_exactly_one_active_provider(self):
        config = load_provider_config(DEFAULT_CONFIG_PATH)
        assert isinstance(config.active, str)
        assert config.active in ("anthropic", "gemini")

    def test_fallback_defaults_are_n20_m2_10s(self):
        # REQ-MVP-040 part ii (AD2-m1): config-defined operational parameters.
        config = load_provider_config(DEFAULT_CONFIG_PATH)
        assert config.fallback.window_turns == 20
        assert config.fallback.consecutive_windows == 2
        assert config.fallback.threshold_seconds == 10.0


class TestConfigValidation:
    def test_unknown_provider_rejected(self, tmp_path):
        path = _write(tmp_path, _BASE_CONFIG.replace('active = "anthropic"', 'active = "openai"'))
        with pytest.raises(ConfigError, match="openai"):
            load_provider_config(path)

    def test_multiple_active_providers_rejected(self, tmp_path):
        path = _write(
            tmp_path,
            _BASE_CONFIG.replace('active = "anthropic"', 'active = ["anthropic", "gemini"]'),
        )
        with pytest.raises(ConfigError, match="single"):
            load_provider_config(path)

    def test_missing_active_rejected(self, tmp_path):
        path = _write(tmp_path, _BASE_CONFIG.replace('active = "anthropic"\n', ""))
        with pytest.raises(ConfigError, match="active"):
            load_provider_config(path)

    def test_missing_model_pin_rejected(self, tmp_path):
        path = _write(tmp_path, _BASE_CONFIG.replace('model = "claude-opus-4-8"\n', ""))
        with pytest.raises(ConfigError, match="model"):
            load_provider_config(path)

    def test_credentials_in_config_rejected(self, tmp_path):
        # Secured: credentials NEVER live in the config file (env vars only).
        path = _write(tmp_path, _BASE_CONFIG + '\n[provider.extra]\napi_key = "sk-nope"\n')
        with pytest.raises(ConfigError, match="credential"):
            load_provider_config(path)

    def test_fallback_override_is_respected(self, tmp_path):
        # AC-MVP-031 part 3: N/M are config-overridable.
        path = _write(
            tmp_path,
            _BASE_CONFIG + "\n[fallback]\nwindow_turns = 5\nconsecutive_windows = 3\n",
        )
        config = load_provider_config(path)
        assert config.fallback.window_turns == 5
        assert config.fallback.consecutive_windows == 3
        assert config.fallback.threshold_seconds == 10.0  # default retained

    def test_invalid_fallback_values_rejected(self, tmp_path):
        path = _write(tmp_path, _BASE_CONFIG + "\n[fallback]\nwindow_turns = 0\n")
        with pytest.raises(ConfigError, match="window_turns"):
            load_provider_config(path)


class _NullClient:
    """Injected stand-in client — construction must not touch env keys/network."""


class TestConfigOnlyProviderSwitch:
    """AC-MVP-026 part 1 — flipping ONLY the provider value boots either adapter."""

    def test_configs_differ_only_in_the_active_line(self, tmp_path):
        config_a = _BASE_CONFIG
        config_b = _BASE_CONFIG.replace('active = "anthropic"', 'active = "gemini"')
        diff = [
            (a, b)
            for a, b in zip(config_a.splitlines(), config_b.splitlines(), strict=True)
            if a != b
        ]
        assert len(diff) == 1
        assert "active" in diff[0][0]

    def test_same_factory_boots_anthropic(self, tmp_path):
        path = _write(tmp_path, _BASE_CONFIG)
        provider = build_provider(load_provider_config(path), client=_NullClient())
        assert provider.name == "anthropic"
        assert provider.model_id == "claude-opus-4-8"

    def test_same_factory_boots_gemini(self, tmp_path):
        config_b = _BASE_CONFIG.replace('active = "anthropic"', 'active = "gemini"')
        path = _write(tmp_path, config_b)
        provider = build_provider(load_provider_config(path), client=_NullClient())
        assert provider.name == "gemini"
        assert provider.model_id == "gemini-2.5-pro"

    def test_factory_returns_a_single_provider(self, tmp_path):
        path = _write(tmp_path, _BASE_CONFIG)
        provider = build_provider(load_provider_config(path), client=_NullClient())
        assert not isinstance(provider, (list, tuple))
