"""Director 인증·ACL·Host/Origin 검증 + evidence 신뢰 경계
(SPEC-LDRECV-001 M1 · REQ-LDPLUGIN-018/019).

이 모듈은 판단(계획 저작)도 검증(계약 준수 판정)도 하지 않는다 — 오직 "이 요청이
누구이고, 무엇을 할 자격이 있는가"만 판정한다. `../SPEC-LDPLUGIN-001/contract.md`
§5(LD-AUTH-001~004)가 단일 원본이며, 이 모듈은 그 규범을 코드로 옮길 뿐이다.

## 두 축의 자격 (LD-AUTH-001)

- **MCP credential** (``aud=director-mcp``): 계약 §3 의 공통 route 만 — 읽기/
  validate/submit/feedback propose. human-only scope 를 절대 갖지 않는다
  (:class:`Credential` 생성 시 구조적으로 막는다 — 나중에 검사하는 게 아니라
  애초에 그런 credential 을 만들 수 없다).
- **앱 human credential** (``aud=director-app-human``): 공통 scope 전부 +
  승인/거절/apply/feedback approve·revoke/reconcile. `server/web/approval_bridge.py`
  의 일반 chat/WS 승인 채널과는 다른, director 전용 자격이다 — 계약이 명시적으로
  금지한 재사용(LD-APPROVAL-001)을 이 모듈은 만들지 않는다.

secret 은 OS credential store(:class:`PairingSecretStore`, ``server/deploy/keystore.py``
와 같은 ``keyring``-직접 패턴이되 별도 service name 으로 격리)에만 머문다 — 어떤
예외 메시지·응답·model context 에도 평문으로 실리지 않는다.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hmac
import secrets as _secrets
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import keyring
from keyring.errors import KeyringError

from server.director.models import Detail, ExchangeError

# ---------------------------------------------------------------------------
# scope 상수 (계약 §5 LD-AUTH-001) — 우산 `contract.md` 원문 토큰 그대로.
# ---------------------------------------------------------------------------

AUDIENCE_MCP = "director-mcp"
AUDIENCE_APP_HUMAN = "director-app-human"

#: 계약 §5 — MCP credential 의 scope 전부(공통 scope 와 동일).
MCP_SCOPES: frozenset[str] = frozenset(
    {
        "context:read",
        "knowledge:read",
        "plan:read",
        "plan:validate",
        "plan:submit",
        "execution:read",
        "feedback:propose",
    }
)

#: 계약 §5 — 앱 human credential 에만 부여되는 scope. MCP credential 은 절대
#: 가질 수 없다(LD-AUTH-001). spec.md/acceptance.md/contract.md 세 문서 모두
#: 이 7개 토큰을 동일하게 나열한다(acceptance.md §3 AC-018 본문은 "6종"이라고
#: 세지만 나열된 토큰은 7개다 — 실측 불일치. 이 모듈은 세 문서가 공통으로
#: **나열**한 토큰 집합을 승계했고, 시험도 7개 전부를 돈다).
HUMAN_ONLY_SCOPES: frozenset[str] = frozenset(
    {
        "plan:approve",
        "plan:reject",
        "plan:apply",
        "feedback:read",
        "feedback:approve",
        "feedback:revoke",
        "execution:reconcile",
    }
)

#: 앱 human credential 이 가질 수 있는 scope 전체(공통 + human-only).
APP_HUMAN_SCOPES: frozenset[str] = MCP_SCOPES | HUMAN_ONLY_SCOPES

_SCOPES_BY_AUDIENCE: dict[str, frozenset[str]] = {
    AUDIENCE_MCP: MCP_SCOPES,
    AUDIENCE_APP_HUMAN: APP_HUMAN_SCOPES,
}

#: 계약 §5 LD-AUTH-002 — HTTP default 는 loopback. 콜론 없는 host 이름만 비교
#: 한다(포트는 :func:`_host_only` 가 벗겨낸다).
DEFAULT_HOST_ALLOWLIST: tuple[str, ...] = ("127.0.0.1", "[::1]", "localhost")


# ---------------------------------------------------------------------------
# credential 메타데이터 — secret 은 여기 없다
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Credential:
    """인증된 요청의 신원.

    secret 을 담지 않는다 — 검증(:func:`authenticate`)에서 별도로 대조되고
    버려진다. 이 객체가 로그에 찍혀도 secret 이 새지 않는 것이 설계다.
    """

    credential_id: str
    audience: str
    project_id: str
    principal_id: str
    session_id: str
    scopes: frozenset[str]
    issued_at: float
    expires_at: float
    revoked: bool = False

    def __post_init__(self) -> None:
        # LD-AUTH-001 을 "나중에 검사"가 아니라 "애초에 못 만든다"로 만든다 —
        # MCP credential 에 human-only scope 를 실어 만드는 코드 경로 자체가
        # 여기서 막힌다.
        allowed = _SCOPES_BY_AUDIENCE.get(self.audience)
        if allowed is None:
            raise ValueError(f"알 수 없는 audience 입니다: {self.audience!r}")
        offending = self.scopes - allowed
        if offending:
            raise ValueError(
                f"{self.audience} credential 은 {sorted(offending)} scope 를 가질 수 없습니다."
            )


class CredentialRegistry:
    """credential **메타데이터**(scope·만료·철회 — 비밀 아님)만 보관한다.

    secret 은 절대 여기 들어오지 않는다 — :class:`PairingSecretStore` 가 그
    책임을 진다. 이 분리 자체가 REQ-018 의 "secret 을 OS credential store 밖의
    ... model context 에 넣지 않는다"를 구조로 지킨다.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Credential] = {}

    def register(self, credential: Credential) -> None:
        self._by_id[credential.credential_id] = credential

    def get(self, credential_id: str) -> Credential | None:
        return self._by_id.get(credential_id)

    def revoke(self, credential_id: str) -> None:
        existing = self._by_id.get(credential_id)
        if existing is not None:
            self._by_id[credential_id] = dataclasses.replace(existing, revoked=True)


class PairingSecretStore:
    """LD-AUTH-001 pairing secret 의 OS credential store 어댑터.

    ``server/deploy/keystore.py`` 와 같은 ``keyring``-직접 패턴이되 **다른
    service name** 으로 격리한다 — director pairing secret 과 LLM provider API
    key 는 서로 다른 credential 도메인이고, 하나의 keychain ACL 을 공유하면 한
    도메인의 유출이 다른 도메인까지 번진다(``keystore.py`` 자신의 경고: "SERVICE_NAME
    ... 변경하면 저장된 모든 credential 이 다시 키가 매겨진다").

    테스트는 이 클래스를 그대로 쓴다 — ``server/tests/conftest.py`` 의 autouse
    ``_neutralize_os_keyring`` 이 모든 테스트에 in-memory keyring backend 를
    심어 두므로, 실제 OS store 를 건드리지 않고도 이 경로 전체가 검증된다.
    """

    SERVICE_NAME = "com.grandma3copilot.director"

    def set(self, credential_id: str, secret: str) -> None:
        try:
            keyring.set_password(self.SERVICE_NAME, credential_id, secret)
        except KeyringError as error:
            raise ExchangeError(
                "DEPENDENCY_UNAVAILABLE",
                503,
                "OS credential store 를 쓸 수 없어 pairing secret 을 저장하지 못했습니다.",
            ) from error

    def get(self, credential_id: str) -> str | None:
        try:
            return keyring.get_password(self.SERVICE_NAME, credential_id)
        except KeyringError as error:
            raise ExchangeError(
                "DEPENDENCY_UNAVAILABLE",
                503,
                "OS credential store 를 쓸 수 없어 pairing secret 을 읽지 못했습니다.",
            ) from error

    def delete(self, credential_id: str) -> None:
        # 멱등 — 이미 없는 것도 성공으로 본다 (keystore.py 와 같은 규율).
        with contextlib.suppress(KeyringError):
            keyring.delete_password(self.SERVICE_NAME, credential_id)


def generate_secret() -> str:
    """새 pairing secret. 서버 발급 opaque 값 — 사람이 타이핑하지 않는다."""
    return _secrets.token_urlsafe(32)


def encode_bearer_token(credential_id: str, secret: str) -> str:
    """``Authorization: Bearer <token>`` 헤더에 실을 형태."""
    return f"{credential_id}:{secret}"


def _parse_bearer(authorization_header: str | None) -> tuple[str, str] | None:
    if authorization_header is None:
        return None
    prefix = "Bearer "
    if not authorization_header.startswith(prefix):
        return None
    token = authorization_header[len(prefix) :]
    credential_id, sep, secret = token.partition(":")
    if not sep or not credential_id or not secret:
        return None
    return credential_id, secret


def _host_only(host_header: str) -> str:
    """``Host`` 헤더에서 포트를 벗긴다. IPv6 literal(``[::1]:port``)은 대괄호를 보존한다."""
    if host_header.startswith("["):
        end = host_header.find("]")
        if end != -1:
            return host_header[: end + 1]
        return host_header
    return host_header.rsplit(":", 1)[0] if ":" in host_header else host_header


def _unauthenticated(message: str) -> ExchangeError:
    return ExchangeError("UNAUTHENTICATED", 401, message)


def _scope_denied(message: str) -> ExchangeError:
    return ExchangeError("SCOPE_DENIED", 403, message)


def _origin_denied(message: str) -> ExchangeError:
    return ExchangeError("ORIGIN_DENIED", 403, message)


# @MX:ANCHOR: [AUTO] director 인증 경계 — 모든 director HTTP route 가 이 함수
#   하나를 거친다(director_api.py 의 모든 handler 가 호출). fan_in >= 3(공통
#   GET/PUT/POST route 전부).
# @MX:REASON: REQ-LDPLUGIN-018 · 계약 §5 LD-AUTH-001/002/003 — 이 함수가 우회되면
#   audience/scope/Host/Origin/만료/철회 검사가 전부 무력화된다. 새 route 를
#   추가할 때 이 함수를 부르지 않으면(또는 순서를 바꾸면) 인증 없는 진입점이
#   생긴다.
# @MX:SPEC: SPEC-LDRECV-001
def authenticate(
    *,
    authorization_header: str | None,
    host_header: str | None,
    origin_header: str | None,
    required_scope: str,
    registry: CredentialRegistry,
    secrets_store: PairingSecretStore,
    now: float | None = None,
    allowed_hosts: Sequence[str] = DEFAULT_HOST_ALLOWLIST,
    trusted_origins: Sequence[str] = (),
) -> Credential:
    """계약 §5 의 인증·ACL·Host/Origin 검증. 실패는 :class:`ExchangeError`.

    검사 순서 — Host → Origin → credential 존재/서명 → 만료/철회 → scope.
    AC-LDPLUGIN-018 이 세 결과를 명시적으로 매핑한다: MCP credential 로
    human-only route 호출 **또는** 만료·철회 credential **또는** Host/Origin
    불일치 각각 SCOPE_DENIED/UNAUTHENTICATED/ORIGIN_DENIED — Host 불일치와
    Origin 불일치가 **같은 코드**(ORIGIN_DENIED)로 매핑되는 것이 원문이다.

    Origin 은 없을 수 있다(계약 §5: "stdio proxy HTTP에는 Origin이 없을 수
    있지만 bearer 인증은 필수다") — 있을 때만 exact-match 를 요구한다.

    CSRF: 계약 §5 는 "cookie 사용 APP route도 CSRF token도 요구한다"고
    규정한다. 이 서버의 기존 인증 표면(``server/web/handshake.py`` 의 `/ws`
    bearer-subprotocol 토큰, 이 함수의 Authorization bearer)은 쿠키를 쓰지
    않는다 — 이 코드베이스 전체에 쿠키 기반 세션 패턴이 없음을 확인했다
    (``grep -rn "set_cookie\\|request.cookies" server/`` 무매치). 계약의
    CSRF 요구는 **쿠키 사용을 전제로 조건부**이므로, 쿠키를 쓰지 않는 이
    경로에는 아직 적용되지 않는다 — 향후 쿠키 기반 세션이 추가되면 이 함수에
    CSRF token 검사를 추가해야 한다(추측이 아니라 현재 없음을 실측한 결정).
    """
    moment = time.time() if now is None else now

    # LD-AUTH-002 — Host allowlist. AC-018: Host/Origin 불일치는 모두 ORIGIN_DENIED.
    if host_header is not None and _host_only(host_header) not in allowed_hosts:
        raise _origin_denied("요청 Host 가 loopback allowlist 밖입니다.")

    # LD-AUTH-002 — Origin: 없으면 통과(stdio proxy). 있으면 exact-match 만.
    if origin_header is not None and origin_header not in trusted_origins:
        raise _origin_denied("요청 Origin 이 신뢰 목록과 exact-match 하지 않습니다.")

    parsed = _parse_bearer(authorization_header)
    if parsed is None:
        raise _unauthenticated("Authorization bearer credential 이 없습니다.")
    credential_id, offered_secret = parsed

    credential = registry.get(credential_id)
    if credential is None:
        raise _unauthenticated("알 수 없는 credential 입니다.")

    stored_secret = secrets_store.get(credential_id)
    # 상수 시간 비교 — secret 을 한 글자씩 추측 가능하게 만들지 않는다
    # (`server/web/handshake.py` `_token_matches` 와 같은 규율).
    if stored_secret is None or not hmac.compare_digest(offered_secret, stored_secret):
        raise _unauthenticated("credential secret 이 일치하지 않습니다.")

    if credential.revoked:
        raise _unauthenticated("철회된 credential 입니다.")
    if moment > credential.expires_at:
        raise _unauthenticated("만료된 credential 입니다.")

    if required_scope not in credential.scopes:
        raise _scope_denied(
            f"{credential.audience} credential 은 {required_scope!r} scope 가 없습니다."
        )

    return credential


# ---------------------------------------------------------------------------
# evidence 신뢰 경계 (REQ-LDPLUGIN-019 · 계약 §5 LD-AUTH-003/004)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    """클라이언트가 실어 보낸 주장 — 권한이 아니다 (계약 §5 LD-AUTH-003).

    계약 원문: *"provenance의 actor_ref, origin, evidence의 confirmation은
    클라이언트 주장일 뿐 권한이 아니다."* 이 dataclass 는 그 주장을 담을 뿐,
    :func:`resolve_trust` 의 반환값에 이 필드들의 **값 자체**는 들어가지 않는다
    — 오직 역참조된 서버 record 의 ``kind`` 만 신뢰된다.
    """

    actor_ref: str | None
    origin: str
    confirmation: str | None


@dataclass(frozen=True, slots=True)
class ServerRecord:
    """서버 자신의 immutable record — 유일한 신뢰 근거 (계약 §5 LD-AUTH-003)."""

    record_id: str
    project_id: str
    principal_id: str
    scope: str
    kind: str  # "human_confirmed" | "approved_feedback"


class EvidenceRegistry(Protocol):
    """claim 을 역참조할 immutable server record 의 조회 seam.

    실 구현(durable journal · feedback record 저장소)은 각각 M4 · M2 가
    채운다. M1 은 이 Protocol 과 판정 함수만 소유한다 — 저장을 만들지 않는다.
    """

    def lookup(self, *, project_id: str, principal_id: str, scope: str) -> ServerRecord | None: ...


#: :func:`resolve_trust` 가 역참조에 실패했을 때 돌려주는 정직한 상태.
UNCONFIRMED = "unconfirmed"


def resolve_trust(
    claim: EvidenceClaim,
    *,
    project_id: str,
    principal_id: str,
    scope: str,
    registry: EvidenceRegistry,
) -> str:
    """claim 만으로 승격하지 않는다 (REQ-019).

    같은 project/principal/scope 의 immutable 서버 record 로 역참조됐을 때만
    ``human_confirmed``/``approved_feedback`` 로 인정한다. ``claim`` 은 이
    함수의 시그니처에 남아 있지만(호출자가 무엇을 주장했는지 감사 기록을
    남기기 위해) 반환값 계산에는 쓰이지 않는다 — 실제 판정은 전적으로
    ``registry`` 에서 역참조된 record 에 근거한다.
    """
    del claim  # 감사 기록용 인자 — 판정에는 쓰지 않는다(계약이 금지한 자리).
    record = registry.lookup(project_id=project_id, principal_id=principal_id, scope=scope)
    if record is None:
        return UNCONFIRMED
    return record.kind


@dataclass(frozen=True, slots=True)
class AudioTransferRecord:
    """앱 명시 동의로 승인된 외부 전송 — 목적/수신자/범위를 기록한다 (LD-AUTH-004)."""

    purpose: str
    recipient: str
    scope: str


def authorize_audio_transfer(
    *, explicit_consent: bool, purpose: str, recipient: str, scope: str
) -> AudioTransferRecord:
    """audio 외부 provider 전송을 명시 동의 없이는 차단한다 (REQ-019 · LD-AUTH-004).

    동의가 있어도 목적/수신자/범위 중 하나라도 비어 있으면 여전히 차단한다 —
    계약 원문: *"다른 provider 전송은 앱에서 명시적 동의를 얻고 목적/수신자/
    범위를 기록해야 한다."* 기록 없는 동의는 계약이 요구하는 감사 가능성을
    충족하지 못한다.
    """
    if not explicit_consent:
        raise ExchangeError(
            "FORBIDDEN", 403, "앱 명시 동의 없이 audio 를 외부로 전송할 수 없습니다."
        )
    if not purpose or not recipient or not scope:
        raise ExchangeError(
            "FORBIDDEN",
            403,
            "목적/수신자/범위 기록 없이는 audio 를 외부로 전송할 수 없습니다.",
            (Detail("", "missing purpose/recipient/scope record"),),
        )
    return AudioTransferRecord(purpose=purpose, recipient=recipient, scope=scope)
