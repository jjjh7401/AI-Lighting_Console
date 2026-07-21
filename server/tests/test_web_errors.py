"""Korean error catalog tests (M5 — REQ-MVP-044, AC-MVP-030 catalog half).

Every normalized provider error kind (``server/llm/errors.ERROR_KINDS``) maps to
a Korean user-facing message that NEVER contains the raw SDK detail. The full
adapter-path injection tests (real Anthropic/Gemini adapters + fake SDK clients
raising real SDK exceptions -> chat surface / diagnostic log split) live in
``test_web_session.py`` (AC-MVP-030 (1)(2)(3)).
"""

from __future__ import annotations

import re

import pytest

from server.llm.errors import ERROR_KINDS, ProviderError
from server.web.korean_errors import (
    KOREAN_ERROR_MESSAGES,
    UNEXPECTED_KIND,
    classify_exception,
    korean_message_for,
)

_HANGUL = re.compile(r"[가-힣]")

_RAW_DETAIL = 'RateLimitError(\'Error code: 429 — {"type":"rate_limit_error"}\')'


class TestCatalogCompleteness:
    @pytest.mark.parametrize("kind", ERROR_KINDS)
    def test_every_normalized_kind_has_a_korean_message(self, kind):
        message = KOREAN_ERROR_MESSAGES[kind]
        assert _HANGUL.search(message), f"{kind} message is not Korean: {message!r}"

    def test_unexpected_kind_has_a_korean_message(self):
        assert _HANGUL.search(KOREAN_ERROR_MESSAGES[UNEXPECTED_KIND])

    def test_unknown_kind_falls_back_to_the_unexpected_message(self):
        assert korean_message_for("never-heard-of-it") == KOREAN_ERROR_MESSAGES[UNEXPECTED_KIND]

    @pytest.mark.parametrize("kind", ERROR_KINDS)
    def test_messages_never_contain_english_sdk_vocabulary(self, kind):
        # The chat surface must read as a Korean product message, not an SDK
        # trace: no exception-class-looking tokens.
        message = KOREAN_ERROR_MESSAGES[kind]
        assert "Error" not in message
        assert "Exception" not in message


class TestClassifyException:
    def test_provider_error_maps_to_its_kind(self):
        error = ProviderError(
            kind="rate_limit", provider="anthropic", retryable=True, raw_detail=_RAW_DETAIL
        )
        kind, message = classify_exception(error)
        assert kind == "rate_limit"
        assert message == KOREAN_ERROR_MESSAGES["rate_limit"]

    @pytest.mark.parametrize("kind", ERROR_KINDS)
    def test_no_kind_message_ever_contains_the_raw_detail(self, kind):
        error = ProviderError(kind=kind, provider="gemini", retryable=False, raw_detail=_RAW_DETAIL)
        _, message = classify_exception(error)
        assert _RAW_DETAIL not in message
        assert "429" not in message
        assert _HANGUL.search(message)

    def test_non_provider_exception_maps_to_unexpected(self):
        # A GENERIC (non-key) ValueError still buckets to 'unexpected' — the
        # missing-key branch below must NOT over-broaden this path.
        kind, message = classify_exception(ValueError("boom secret detail"))
        assert kind == UNEXPECTED_KIND
        assert "boom secret detail" not in message
        assert _HANGUL.search(message)

    def test_missing_key_valueerror_classifies_as_auth(self):
        # REQ-DEPLOY-031 / AC-DEPLOY-022 ②: a raw missing-credential ValueError
        # that reaches the classifier directly (defense-in-depth beside the
        # adapter normalization) classifies as 'auth', not 'unexpected'.
        exc = ValueError(
            "No API key was provided. Please pass a valid API key. "
            "Learn how to create an API key at https://ai.google.dev/..."
        )
        kind, message = classify_exception(exc)
        assert kind == "auth"
        assert message == KOREAN_ERROR_MESSAGES["auth"]
        # Raw detail (the URL, the English sentence) never rides the message.
        assert "ai.google.dev" not in message
        assert _HANGUL.search(message)
