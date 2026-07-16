"""One-call live provider smoke (dev tool — AC-MVP-014 part 2 / AC-MVP-026 evidence path).

Runs a single completion against the ACTIVE configured provider using the real
rulebook fixed prefix, then prints provider/model/usage — including the
cache-read token count that AC-MVP-014 part 2 asserts live (>0 from the second
warm-cache call onward, on caching-capable configurations).

Requires a real API key in the environment for the active provider
(``ANTHROPIC_API_KEY`` or ``GEMINI_API_KEY``/``GOOGLE_API_KEY``). Run twice to
observe a warm-cache read:

    uv run python -m server.tools.provider_smoke [--config config/provider.toml]
"""

from __future__ import annotations

import argparse

from server.llm.config import DEFAULT_CONFIG_PATH, ConfigError, load_provider_config
from server.llm.errors import ProviderError
from server.llm.factory import build_provider
from server.llm.types import LLMProvider, UserMessage
from server.rulebook.assembly import assemble_prefix

_DEFAULT_PROMPT = "간단히 '준비 완료'라고만 답해줘. 도구는 호출하지 마."


def run_smoke(config_path: str, *, provider: LLMProvider | None = None) -> int:
    """Run one completion and print the evidence lines; returns an exit code."""
    try:
        config = load_provider_config(config_path)
        provider = provider or build_provider(config)
        turn = provider.complete(
            system_prefix=assemble_prefix(),
            conversation=[UserMessage(text=_DEFAULT_PROMPT)],
            tools=(),
        )
    except ConfigError as error:
        print(f"CONFIG ERROR: {error}")
        return 1
    except ProviderError as error:
        print(f"PROVIDER ERROR: kind={error.kind} retryable={error.retryable}")
        print(f"detail (diagnostics only): {error.raw_detail}")
        return 1
    usage = turn.usage
    print(f"provider={provider.name} model={provider.model_id}")
    print(f"caching={'on' if provider.supports_prompt_caching else 'off'}")
    print(f"stop_reason={turn.stop_reason}")
    print(
        f"usage: input={usage.input_tokens} output={usage.output_tokens} "
        f"cache_read={usage.cache_read_tokens} cache_write={usage.cache_write_tokens}"
    )
    print(f"text: {turn.text[:200]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="provider config file (default: repo config/provider.toml)",
    )
    args = parser.parse_args(argv)
    return run_smoke(args.config)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
