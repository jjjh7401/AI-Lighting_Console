"""Korean error catalog (M5 — REQ-MVP-044, AC-MVP-030).

Maps the closed set of normalized provider error kinds
(:data:`server.llm.errors.ERROR_KINDS`) to Korean user-facing messages. The
chat surface shows ONLY these messages; the raw SDK detail is routed to the
diagnostic/audit log by the session layer and never appears here.
"""

from __future__ import annotations

from server.llm.errors import ProviderError
from server.safety.gate import WriteGateDeclarationError

# Non-provider (unexpected) failures get their own catalog entry.
UNEXPECTED_KIND = "unexpected"

#: 카드 t318 — 번들 위험 선언이 디스패치 배선을 못 지난 사고. `unexpected` 와
#: 갈라 두는 이유는 하나다: 이쪽은 **안전장치가 꺼진 상태**라 「다시 시도해
#: 주세요」가 틀린 안내다.
WRITE_GATE_DECLARATION_KIND = "write_gate_declaration"

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
    WRITE_GATE_DECLARATION_KIND: (
        "안전 승인 선언이 실행 경로를 지나지 못해 콘솔에 아무것도 보내지 않았습니다. "
        "이 상태로는 승인 카드 없이 쇼파일이 고쳐질 수 있으니 그대로 다시 시도하지 "
        "마시고 진단 로그를 확인해 주세요."
    ),
}


# Case-insensitive markers that identify a missing/invalid-credential
# ValueError (e.g. a provider client constructed without an API key).
_MISSING_KEY_MARKERS = ("api key", "api_key", "credential")


def korean_message_for(kind: str) -> str:
    """The Korean message for one error kind (unknown kinds fall back safely)."""
    return KOREAN_ERROR_MESSAGES.get(kind, KOREAN_ERROR_MESSAGES[UNEXPECTED_KIND])


def _looks_like_missing_key(exc: ValueError) -> bool:
    """True when a raw ValueError names a missing/invalid API key or credential."""
    text = str(exc).lower()
    return any(marker in text for marker in _MISSING_KEY_MARKERS)


def classify_exception(exc: Exception) -> tuple[str, str]:
    """Classify one exception into (kind, Korean user message).

    The returned message NEVER contains the exception's own text — raw detail
    is the session layer's diagnostic-log concern (REQ-MVP-044b).
    """
    # 카드 t318 — 선언이 배선을 못 지난 사고는 `unexpected` 로 접히면 안 된다.
    # ProviderError 검사보다 앞에 둔다: 이 예외는 프로바이더와 무관하다.
    if isinstance(exc, WriteGateDeclarationError):
        return WRITE_GATE_DECLARATION_KIND, korean_message_for(WRITE_GATE_DECLARATION_KIND)
    if isinstance(exc, ProviderError):
        return exc.kind, korean_message_for(exc.kind)
    # Defense-in-depth (REQ-DEPLOY-031): the primary normalization of a
    # missing-key "No API key" ValueError happens at the provider adapter
    # (ProviderError(kind="auth") via the ProviderError branch above). This
    # narrow branch catches a raw missing-credential ValueError that reaches the
    # classifier directly — it is an auth failure, NOT an 'unexpected' internal
    # error. Generic (non-key) ValueErrors still fall through to 'unexpected'.
    if isinstance(exc, ValueError) and _looks_like_missing_key(exc):
        return "auth", korean_message_for("auth")
    return UNEXPECTED_KIND, KOREAN_ERROR_MESSAGES[UNEXPECTED_KIND]
