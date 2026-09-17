"""SPEC-LDRECV-001 M1 · REQ-LDPLUGIN-018 · AC-LDPLUGIN-018.

인증·ACL·Host/Origin 검증. 계약 §5(LD-AUTH-001/002)를 `server.director.auth`
가 코드로 옮긴 것을 여기서 시험한다.

이 파일은 `pytest-asyncio` 나 실제 OS keyring 을 필요로 하지 않는다 —
`server/tests/conftest.py` 의 autouse `_neutralize_os_keyring` 이 모든 테스트에
in-memory keyring backend 를 심어 두므로, `PairingSecretStore` 가 그대로 쓰는
`keyring.set_password`/`get_password` 호출이 격리된 채로 통과한다.
"""

from __future__ import annotations

import time

import pytest

from server.director.auth import (
    APP_HUMAN_SCOPES,
    AUDIENCE_APP_HUMAN,
    AUDIENCE_MCP,
    HUMAN_ONLY_SCOPES,
    MCP_SCOPES,
    Credential,
    CredentialRegistry,
    PairingSecretStore,
    authenticate,
    encode_bearer_token,
    generate_secret,
)
from server.director.models import ExchangeError

PROJECT = "proj-1"
TRUSTED_ORIGIN = "http://127.0.0.1:37123"
DEFAULT_HOST = "127.0.0.1:37123"


def _issue(
    registry: CredentialRegistry,
    secret_store: PairingSecretStore,
    *,
    audience: str,
    scopes: frozenset[str],
    expires_in: float = 600.0,
    now: float | None = None,
) -> tuple[Credential, str]:
    moment = time.time() if now is None else now
    credential_id = f"cred-{audience}-{moment!r}-{len(scopes)}"
    secret = generate_secret()
    credential = Credential(
        credential_id=credential_id,
        audience=audience,
        project_id=PROJECT,
        principal_id="principal-1",
        session_id="session-1",
        scopes=frozenset(scopes),
        issued_at=moment,
        expires_at=moment + expires_in,
    )
    registry.register(credential)
    secret_store.set(credential_id, secret)
    return credential, secret


def _auth_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "authorization_header": None,
        "host_header": DEFAULT_HOST,
        "origin_header": TRUSTED_ORIGIN,
        "required_scope": "plan:read",
        "trusted_origins": (TRUSTED_ORIGIN,),
    }
    base.update(overrides)
    return base


@pytest.fixture
def registry() -> CredentialRegistry:
    return CredentialRegistry()


@pytest.fixture
def secret_store() -> PairingSecretStore:
    return PairingSecretStore()


# ---------------------------------------------------------------------------
# SCOPE_DENIED — MCP credential 로 human-only route 호출
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scope", sorted(HUMAN_ONLY_SCOPES))
def test_mcp_credential_denied_for_human_only_scope(
    registry: CredentialRegistry, secret_store: PairingSecretStore, scope: str
) -> None:
    """AC-018: MCP credential 로 human-only scope 각각 호출 시도 → SCOPE_DENIED.

    HUMAN_ONLY_SCOPES 는 7개다 — acceptance.md 본문은 "6종"이라 세지만 나열된
    토큰은 7개(spec.md/contract.md 도 동일). 이 시험은 더 넓은 실측 토큰
    집합(7개) 전부를 돈다 — 세는 쪽이 아니라 나열한 쪽을 승계했다.
    """
    credential, secret = _issue(registry, secret_store, audience=AUDIENCE_MCP, scopes=MCP_SCOPES)
    with pytest.raises(ExchangeError) as excinfo:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
                ),
                required_scope=scope,
                registry=registry,
                secrets_store=secret_store,
            )
        )
    assert excinfo.value.code == "SCOPE_DENIED"
    assert excinfo.value.http_status == 403


def test_human_only_scopes_cover_exactly_the_contract_tokens() -> None:
    """계약 §5 원문 7개 토큰과 정확히 일치하는지 — 오타로 하나 빠지면 위 파라미터화
    시험이 조용히 그 scope 를 건너뛰므로, 집합 자체를 별도로 고정한다.
    """
    expected = frozenset(
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
    assert expected == HUMAN_ONLY_SCOPES


def test_mcp_credential_cannot_be_constructed_with_human_only_scope() -> None:
    """LD-AUTH-001 을 "검사"가 아니라 "구조적으로 불가능"으로 만든다."""
    with pytest.raises(ValueError):
        Credential(
            credential_id="bad",
            audience=AUDIENCE_MCP,
            project_id=PROJECT,
            principal_id="p",
            session_id="s",
            scopes=frozenset({"plan:approve"}),
            issued_at=0.0,
            expires_at=1.0,
        )


# ---------------------------------------------------------------------------
# UNAUTHENTICATED — 만료·철회·부재·위조 credential
# ---------------------------------------------------------------------------


def test_expired_credential_is_unauthenticated(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    now = time.time()
    credential, secret = _issue(
        registry,
        secret_store,
        audience=AUDIENCE_APP_HUMAN,
        scopes=APP_HUMAN_SCOPES,
        expires_in=-10.0,
        now=now,
    )
    with pytest.raises(ExchangeError) as excinfo:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
                ),
                registry=registry,
                secrets_store=secret_store,
                now=now,
            )
        )
    assert excinfo.value.code == "UNAUTHENTICATED"
    assert excinfo.value.http_status == 401


def test_revoked_credential_is_unauthenticated(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    credential, secret = _issue(
        registry, secret_store, audience=AUDIENCE_APP_HUMAN, scopes=APP_HUMAN_SCOPES
    )
    registry.revoke(credential.credential_id)
    with pytest.raises(ExchangeError) as excinfo:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
                ),
                registry=registry,
                secrets_store=secret_store,
            )
        )
    assert excinfo.value.code == "UNAUTHENTICATED"


def test_missing_authorization_header_is_unauthenticated(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    with pytest.raises(ExchangeError) as excinfo:
        authenticate(**_auth_kwargs(registry=registry, secrets_store=secret_store))
    assert excinfo.value.code == "UNAUTHENTICATED"


def test_unknown_credential_id_is_unauthenticated(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    with pytest.raises(ExchangeError) as excinfo:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token('no-such-credential', 'whatever')}"
                ),
                registry=registry,
                secrets_store=secret_store,
            )
        )
    assert excinfo.value.code == "UNAUTHENTICATED"


def test_wrong_secret_is_unauthenticated(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    credential, _secret = _issue(registry, secret_store, audience=AUDIENCE_MCP, scopes=MCP_SCOPES)
    with pytest.raises(ExchangeError) as excinfo:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token(credential.credential_id, 'forged-secret')}"
                ),
                registry=registry,
                secrets_store=secret_store,
            )
        )
    assert excinfo.value.code == "UNAUTHENTICATED"


# ---------------------------------------------------------------------------
# ORIGIN_DENIED — Origin 불일치 · Host allowlist 밖 (AC-018: 둘 다 이 코드)
# ---------------------------------------------------------------------------


def test_origin_mismatch_is_origin_denied(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    credential, secret = _issue(
        registry, secret_store, audience=AUDIENCE_APP_HUMAN, scopes=APP_HUMAN_SCOPES
    )
    with pytest.raises(ExchangeError) as excinfo:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
                ),
                registry=registry,
                secrets_store=secret_store,
                origin_header="http://evil.example",
            )
        )
    assert excinfo.value.code == "ORIGIN_DENIED"
    assert excinfo.value.http_status == 403


def test_host_outside_loopback_allowlist_is_origin_denied(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    credential, secret = _issue(
        registry, secret_store, audience=AUDIENCE_APP_HUMAN, scopes=APP_HUMAN_SCOPES
    )
    with pytest.raises(ExchangeError) as excinfo:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
                ),
                registry=registry,
                secrets_store=secret_store,
                host_header="attacker.example:8420",
            )
        )
    assert excinfo.value.code == "ORIGIN_DENIED"
    assert excinfo.value.http_status == 403


# ---------------------------------------------------------------------------
# 양성 대조 — 올바른 scope·audience·Origin 은 실제로 통과한다 (날조 대조군 방지)
# ---------------------------------------------------------------------------


def test_mcp_credential_with_common_scope_succeeds(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    credential, secret = _issue(registry, secret_store, audience=AUDIENCE_MCP, scopes=MCP_SCOPES)
    result = authenticate(
        **_auth_kwargs(
            authorization_header=(
                f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
            ),
            registry=registry,
            secrets_store=secret_store,
        )
    )
    assert result.credential_id == credential.credential_id
    assert result.audience == AUDIENCE_MCP


def test_human_credential_with_human_only_scope_succeeds(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    credential, secret = _issue(
        registry, secret_store, audience=AUDIENCE_APP_HUMAN, scopes=APP_HUMAN_SCOPES
    )
    result = authenticate(
        **_auth_kwargs(
            authorization_header=(
                f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
            ),
            required_scope="plan:approve",
            registry=registry,
            secrets_store=secret_store,
        )
    )
    assert result.audience == AUDIENCE_APP_HUMAN
    assert result.credential_id == credential.credential_id


def test_missing_origin_is_allowed_for_stdio_proxy(
    registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    """계약 §5: "stdio proxy HTTP에는 Origin이 없을 수 있지만 bearer 인증은 필수다."""
    credential, secret = _issue(registry, secret_store, audience=AUDIENCE_MCP, scopes=MCP_SCOPES)
    result = authenticate(
        **_auth_kwargs(
            authorization_header=(
                f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
            ),
            registry=registry,
            secrets_store=secret_store,
            origin_header=None,
        )
    )
    assert result.credential_id == credential.credential_id


# ---------------------------------------------------------------------------
# secret 비노출 — 로그·응답·예외 메시지 어디에도 등장하지 않는다
# ---------------------------------------------------------------------------


def test_secret_never_exposed_in_errors_body_or_logs(
    registry: CredentialRegistry, secret_store: PairingSecretStore, caplog: pytest.LogCaptureFixture
) -> None:
    credential, secret = _issue(registry, secret_store, audience=AUDIENCE_MCP, scopes=MCP_SCOPES)
    canary = secret  # 실제 secret 문자열 — 이 값이 어디에도 나타나면 안 된다.
    captured: list[str] = []

    # (1) 위조 secret 시도 — UNAUTHENTICATED
    try:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token(credential.credential_id, 'forged')}"
                ),
                registry=registry,
                secrets_store=secret_store,
            )
        )
    except ExchangeError as error:
        captured.append(str(error))
        captured.append(repr(error))
        captured.append(str(error.to_envelope("req-1")))

    # (2) 올바른 secret 이지만 scope 거부 — SCOPE_DENIED
    try:
        authenticate(
            **_auth_kwargs(
                authorization_header=(
                    f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
                ),
                required_scope="plan:approve",
                registry=registry,
                secrets_store=secret_store,
            )
        )
    except ExchangeError as error:
        captured.append(str(error))
        captured.append(str(error.to_envelope("req-2")))

    # (3) 성공 경로 — Credential 자체의 str/repr 에도 secret 이 없어야 한다.
    result = authenticate(
        **_auth_kwargs(
            authorization_header=(
                f"Bearer {encode_bearer_token(credential.credential_id, secret)}"
            ),
            registry=registry,
            secrets_store=secret_store,
        )
    )
    captured.append(str(result))
    captured.append(repr(result))

    captured.append(caplog.text)

    for message in captured:
        assert canary not in message, f"pairing secret 이 노출됐습니다: {message!r}"
