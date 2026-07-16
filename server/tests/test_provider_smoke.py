"""Provider smoke tool tests (M3 dev tool — injected provider, no network)."""

from __future__ import annotations

from server.llm.config import DEFAULT_CONFIG_PATH
from server.llm.errors import ProviderError
from server.llm.types import ModelTurn, Usage
from server.tools.provider_smoke import run_smoke


class FakeProvider:
    name = "fake"
    model_id = "fake-model"
    supports_prompt_caching = True

    def __init__(self, outcome):
        self.outcome = outcome
        self.requests = []

    def complete(self, *, system_prefix, conversation, tools=()):
        self.requests.append({"system_prefix": system_prefix, "conversation": conversation})
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _turn() -> ModelTurn:
    return ModelTurn(
        text="준비 완료",
        tool_calls=(),
        stop_reason="end",
        usage=Usage(input_tokens=10, output_tokens=2, cache_read_tokens=9),
        provider="fake",
    )


class TestRunSmoke:
    def test_success_prints_usage_and_exits_zero(self, capsys):
        provider = FakeProvider(_turn())
        assert run_smoke(str(DEFAULT_CONFIG_PATH), provider=provider) == 0
        output = capsys.readouterr().out
        assert "provider=fake model=fake-model" in output
        assert "cache_read=9" in output

    def test_smoke_uses_the_real_rulebook_prefix(self):
        provider = FakeProvider(_turn())
        run_smoke(str(DEFAULT_CONFIG_PATH), provider=provider)
        assert "grandMA3" in provider.requests[0]["system_prefix"]

    def test_provider_error_exits_one_with_normalized_kind(self, capsys):
        error = ProviderError(kind="auth", provider="fake", retryable=False, raw_detail="401 boom")
        assert run_smoke(str(DEFAULT_CONFIG_PATH), provider=FakeProvider(error)) == 1
        assert "kind=auth" in capsys.readouterr().out

    def test_missing_config_exits_one(self, capsys):
        assert run_smoke("/nonexistent/provider.toml", provider=FakeProvider(_turn())) == 1
        assert "CONFIG ERROR" in capsys.readouterr().out
