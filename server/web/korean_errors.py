"""Korean error catalog (M5 — REQ-MVP-044, AC-MVP-030).

Maps the closed set of normalized provider error kinds
(:data:`server.llm.errors.ERROR_KINDS`) to Korean user-facing messages. The
chat surface shows ONLY these messages; the raw SDK detail is routed to the
diagnostic/audit log by the session layer and never appears here.
"""

from __future__ import annotations

from server.llm.errors import ProviderError

# Non-provider (unexpected) failures get their own catalog entry.
UNEXPECTED_KIND = "unexpected"

# One Korean message per normalized kind — product language, no SDK vocabulary.
KOREAN_ERROR_MESSAGES: dict[str, str] = {
    "rate_limit": "AI 서비스 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.",
    "auth": "AI 서비스 인증에 실패했습니다. API 키 설정을 확인해 주세요.",
    "invalid_request": "AI 서비스가 요청을 거부했습니다. 지시를 바꾸어 다시 시도해 주세요.",
    "connection": "AI 서비스에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요.",
    "server": "AI 서비스에 일시적인 장애가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "malformed_response": "AI 응답을 해석하지 못했습니다. 다시 시도해 주세요.",
    "unknown": "AI 서비스 처리 중 알 수 없는 문제가 발생했습니다. 다시 시도해 주세요.",
    UNEXPECTED_KIND: (
        "서버 내부 문제가 발생했습니다. 다시 시도해도 반복되면 진단 로그를 확인해 주세요."
    ),
}


def korean_message_for(kind: str) -> str:
    """The Korean message for one error kind (unknown kinds fall back safely)."""
    return KOREAN_ERROR_MESSAGES.get(kind, KOREAN_ERROR_MESSAGES[UNEXPECTED_KIND])


def classify_exception(exc: Exception) -> tuple[str, str]:
    """Classify one exception into (kind, Korean user message).

    The returned message NEVER contains the exception's own text — raw detail
    is the session layer's diagnostic-log concern (REQ-MVP-044b).
    """
    if isinstance(exc, ProviderError):
        return exc.kind, korean_message_for(exc.kind)
    return UNEXPECTED_KIND, KOREAN_ERROR_MESSAGES[UNEXPECTED_KIND]
