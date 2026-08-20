"""Provider factory — builds the SINGLE active provider from config (REQ-MVP-006/039).

Every provider boots through this one code path; switching is a config-file
value change with zero code diff (AC-MVP-026 part 1).
"""

from __future__ import annotations

from typing import Any

from server.llm.anthropic_adapter import AnthropicAdapter
from server.llm.claude_code_adapter import ClaudeCodeAdapter
from server.llm.config import ConfigError, ProviderConfig
from server.llm.gemini_adapter import GeminiAdapter
from server.llm.ollama_adapter import OllamaAdapter
from server.llm.types import LLMProvider


def build_provider(config: ProviderConfig, *, client: Any | None = None) -> LLMProvider:
    """Instantiate exactly one adapter for the configured active provider.

    ``client`` injects a pre-built SDK client (tests / smoke tooling); when
    omitted, the adapter constructs the real SDK client lazily on first use,
    resolving credentials from environment variables only.
    """
    if config.active == "anthropic":
        return AnthropicAdapter(config.anthropic, client=client)
    if config.active == "claude_code":
        return ClaudeCodeAdapter(config.claude_code.model)
    if config.active == "gemini":
        return GeminiAdapter(config.gemini, client=client)
    if config.active == "ollama":
        # No `client=`: the local daemon is reached over plain HTTP, so there is
        # no SDK object to inject — the adapter's own `transport` seam is what
        # tests substitute.
        return OllamaAdapter(
            config.ollama.model,
            host=config.ollama.host,
            keep_alive=config.ollama.keep_alive,
        )
    raise ConfigError(f"unsupported active provider: {config.active!r}")  # pragma: no cover
