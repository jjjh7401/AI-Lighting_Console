"""Structured internal provider errors (REQ-MVP-044 forward design).

Adapters normalize every SDK exception into :class:`ProviderError` so that M5
can translate ``kind`` into a Korean user-facing message WITHOUT touching the
adapters, while the raw SDK detail is preserved for diagnostics/audit logs only
(never for the chat surface).
"""

from __future__ import annotations

# Closed set of error kinds the M5 UI will translate to Korean messages.
ERROR_KINDS = (
    "rate_limit",
    "auth",
    "invalid_request",
    "connection",
    "server",
    "malformed_response",
    "unknown",
)


class ProviderError(Exception):
    """One normalized LLM provider failure (kind + provider + retryable + raw detail)."""

    def __init__(self, *, kind: str, provider: str, retryable: bool, raw_detail: str) -> None:
        if kind not in ERROR_KINDS:
            raise ValueError(f"unknown provider error kind: {kind!r}")
        super().__init__(f"{provider} {kind}: {raw_detail}")
        self.kind = kind
        self.provider = provider
        self.retryable = retryable
        self.raw_detail = raw_detail


def normalize_anthropic_error(exc: Exception) -> ProviderError:
    """Map an Anthropic SDK exception onto the structured internal error."""
    import anthropic

    detail = repr(exc)

    def _error(kind: str, retryable: bool) -> ProviderError:
        return ProviderError(
            kind=kind, provider="anthropic", retryable=retryable, raw_detail=detail
        )

    if isinstance(exc, anthropic.RateLimitError):
        return _error("rate_limit", True)
    if isinstance(exc, anthropic.AuthenticationError | anthropic.PermissionDeniedError):
        return _error("auth", False)
    if isinstance(exc, anthropic.APIConnectionError):
        return _error("connection", True)
    if isinstance(exc, anthropic.InternalServerError):
        return _error("server", True)
    if isinstance(exc, anthropic.APIStatusError):
        status = getattr(exc, "status_code", 0) or 0
        return _error("server", True) if status >= 500 else _error("invalid_request", False)
    return _error("unknown", False)


def normalize_gemini_error(exc: Exception) -> ProviderError:
    """Map a google-genai SDK exception onto the structured internal error."""
    import httpx
    from google.genai import errors as genai_errors

    detail = repr(exc)

    def _error(kind: str, retryable: bool) -> ProviderError:
        return ProviderError(kind=kind, provider="gemini", retryable=retryable, raw_detail=detail)

    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None) or 0
        if code == 429:
            return _error("rate_limit", True)
        if code in (401, 403):
            return _error("auth", False)
        if code >= 500:
            return _error("server", True)
        return _error("invalid_request", False)
    # google-genai is httpx-based: real network failures raise
    # httpx.ConnectError / httpx.TimeoutException, which are NOT subclasses of
    # the Python builtin ConnectionError/TimeoutError (checked alongside, not
    # instead of, the builtins so pre-existing builtin-exception tests/mocks
    # keep classifying correctly too).
    connectivity_errors = (
        ConnectionError,
        TimeoutError,
        httpx.ConnectError,
        httpx.TimeoutException,
    )
    if isinstance(exc, connectivity_errors):
        return _error("connection", True)
    return _error("unknown", False)
