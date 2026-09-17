"""SPEC-LDRECV-001 M2 · REQ-LDPLUGIN-020 · AC-LDPLUGIN-020.

사람 승인/거절 — `ApprovalBinding` 발급과 무효화. 계약 §4(APP human routes)·
§8(LD-APPROVAL-001)이 단일 원본이다. `server.director.approvals` 가 그 판정을
코드로 옮긴 것을 여기서 시험한다.

시험은 두 층이다:

- **service 층** (``ApprovalRegistry``/``compute_expiry``/``check_validity``) —
  digest 묶음·만료 계산·무효화 판정을 라우트 없이 직접 시험한다.
- **route 층** (``build_director_router``) — MCP credential 로 human-only route
  를 부르면 SCOPE_DENIED 로 이 모듈에 도달조차 못 하는지, 일반 WS 승인 boolean
  형태 body 는 구조적으로 거부되는지 HTTP 표면에서 확인한다.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.director.approvals import (
    APPROVAL_BINDING_FIELDS,
    ApprovalBinding,
    ApprovalRegistry,
    ContextRef,
    ValidationRef,
    check_validity,
    compute_expiry,
)
from server.director.auth import (
    AUDIENCE_APP_HUMAN,
    AUDIENCE_MCP,
    Credential,
    CredentialRegistry,
    PairingSecretStore,
    encode_bearer_token,
    generate_secret,
)
from server.director.director_api import DirectorApiDeps, build_director_router
from server.director.knowledge import KnowledgeService
from server.director.models import ExchangeError
from server.director.service import OUTCOME_READY, DirectorService
from server.director.store import DirectorStore

PROJECT = "proj-1"
PLAN_ID = "plan-1"
TRUSTED_ORIGIN = "http://127.0.0.1:37123"
DEFAULT_HOST = "127.0.0.1:37123"


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now() -> datetime:
    return datetime(2026, 9, 17, 12, 0, 0, tzinfo=UTC)


def _plan(
    *, project_id: str = PROJECT, plan_id: str = PLAN_ID, base_revision: int = 0
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "plan_id": plan_id,
        "base_revision": base_revision,
        "title": "synthetic plan",
        "bindings": {"context_id": "ctx-1"},
    }


# ---------------------------------------------------------------------------
# ApprovalBinding 필드
# ---------------------------------------------------------------------------


def test_approval_binding_has_all_twelve_contract_fields():
    """계약 §4 원문이 나열한 필드 12개 — plan.md/acceptance.md 는 "9필드"라 세지만
    나열된 토큰은 12개다(auth.py 의 HUMAN_ONLY_SCOPES "6종" vs 실제 7개 나열과
    같은 문서 표기 불일치 — 이 시험은 나열된 쪽을 승계한다)."""
    assert APPROVAL_BINDING_FIELDS == (
        "approval_id",
        "plan_id",
        "plan_revision",
        "plan_digest",
        "context_digest",
        "compiled_digest",
        "principal_id",
        "console_id",
        "session_id",
        "safety_policy_revision",
        "approved_at",
        "expires_at",
    )
    binding = ApprovalBinding(
        approval_id="appr-1",
        plan_id=PLAN_ID,
        plan_revision=1,
        plan_digest="sha256:" + "a" * 64,
        context_digest="sha256:" + "b" * 64,
        compiled_digest="sha256:" + "c" * 64,
        principal_id="principal-1",
        console_id="console-1",
        session_id="session-1",
        safety_policy_revision=1,
        approved_at=_fmt(_now()),
        expires_at=_fmt(_now() + timedelta(minutes=10)),
    )
    payload = binding.as_dict()
    assert set(payload) == set(APPROVAL_BINDING_FIELDS)
    for field_name in APPROVAL_BINDING_FIELDS:
        assert payload[field_name] not in (None, ""), field_name


# ---------------------------------------------------------------------------
# 만료 계산 — approved_at+10분과 validation/context 만료 중 가장 빠른 값
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "validation_delta_min,context_delta_min,expected_delta_min",
    [
        (30, 30, 10),  # 둘 다 넉넉 → approved_at+10분이 가장 빠르다
        (5, 30, 5),  # validation 이 더 이르다
        (30, 3, 3),  # context 가 더 이르다
    ],
)
def test_expiry_picks_earliest_of_three_candidates(
    validation_delta_min, context_delta_min, expected_delta_min
):
    approved_at = _now()
    validation_expires = approved_at + timedelta(minutes=validation_delta_min)
    context_expires = approved_at + timedelta(minutes=context_delta_min)
    expiry = compute_expiry(
        approved_at=_fmt(approved_at),
        validation_expires_at=_fmt(validation_expires),
        context_expires_at=_fmt(context_expires),
    )
    assert expiry == _fmt(approved_at + timedelta(minutes=expected_delta_min))


# ---------------------------------------------------------------------------
# ApprovalRegistry.approve — 정상 발급 + 거부 경로
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> DirectorStore:
    s = DirectorStore(tmp_path / "director.sqlite3")
    yield s
    s.close()


@pytest.fixture
def ready_record(store: DirectorStore):
    """head revision 1, 검증 통과(가정) 상태의 plan 하나를 저장해 둔다."""
    return store.submit(
        plan=_plan(),
        expected_revision=0,
        principal_id="principal-1",
        operation="PUT /api/director/v1/projects/proj-1/plans/plan-1",
        idempotency_key="submit-1",
    )


def _validation_ref(
    record, *, expires_delta_min: int = 30, outcome: str = OUTCOME_READY
) -> ValidationRef:
    return ValidationRef(
        validation_id="val-1",
        plan_digest=record.plan_digest,
        context_digest="sha256:" + "c" * 64,
        compiled_digest="sha256:" + "d" * 64,
        expires_at=_fmt(_now() + timedelta(minutes=expires_delta_min)),
        outcome=outcome,
    )


def _context_ref(
    *, expires_delta_min: int = 30, context_digest: str = "sha256:" + "c" * 64
) -> ContextRef:
    return ContextRef(
        context_digest=context_digest,
        expires_at=_fmt(_now() + timedelta(minutes=expires_delta_min)),
        console_id="console-1",
        session_id="console-session-1",
        safety_policy_revision=7,
    )


def _body(record, validation: ValidationRef, context: ContextRef, *, idempotency_key="appr-key-1"):
    return {
        "validation_id": validation.validation_id,
        "plan_digest": record.plan_digest,
        "context_digest": context.context_digest,
        "compiled_digest": validation.compiled_digest,
        "idempotency_key": idempotency_key,
    }


def test_approve_issues_binding_sourcing_console_session_from_context_target(store, ready_record):
    """console_id/session_id 는 credential 이 아니라 context.target 에서 온다
    (design.md 가 지시한 LDSTORE ContextObservations.target 출처 확인 — 이 SPEC 의
    설계 판단: contract.md target={console_id,session_id,...} 를 그대로 따른다)."""
    registry = ApprovalRegistry()
    validation = _validation_ref(ready_record)
    context = _context_ref()
    binding = registry.approve(
        store=store,
        project_id=PROJECT,
        plan_id=PLAN_ID,
        revision=ready_record.revision,
        principal_id="human-principal-1",
        validation=validation,
        context=context,
        body=_body(ready_record, validation, context),
        operation="POST /api/director/v1/projects/proj-1/plans/plan-1/revisions/1/approvals",
        approved_at=_fmt(_now()),
    )
    assert binding.console_id == "console-1"
    assert binding.session_id == "console-session-1"
    assert binding.principal_id == "human-principal-1"
    assert binding.plan_revision == ready_record.revision
    assert binding.plan_digest == ready_record.plan_digest
    assert binding.context_digest == context.context_digest
    assert binding.compiled_digest == validation.compiled_digest
    assert binding.safety_policy_revision == context.safety_policy_revision
    assert binding.expires_at == _fmt(_now() + timedelta(minutes=10))


def test_approve_rejects_when_validation_outcome_is_blocked(store, ready_record):
    """계약 §5: human approve 시 참조된 validation 이 blocking 이면 422 VALIDATION_BLOCKED."""
    registry = ApprovalRegistry()
    validation = _validation_ref(ready_record, outcome="blocked")
    context = _context_ref()
    with pytest.raises(ExchangeError) as excinfo:
        registry.approve(
            store=store,
            project_id=PROJECT,
            plan_id=PLAN_ID,
            revision=ready_record.revision,
            principal_id="human-principal-1",
            validation=validation,
            context=context,
            body=_body(ready_record, validation, context),
            operation="POST .../approvals",
            approved_at=_fmt(_now()),
        )
    assert excinfo.value.code == "VALIDATION_BLOCKED"
    assert excinfo.value.http_status == 422


def test_approve_rejects_stale_digest_mismatch(store, ready_record):
    """body 의 digest 가 현재 record/context/validation 과 어긋나면 CONTEXT_STALE."""
    registry = ApprovalRegistry()
    validation = _validation_ref(ready_record)
    context = _context_ref()
    body = _body(ready_record, validation, context)
    body["plan_digest"] = "sha256:" + "0" * 64  # 어긋난 값
    with pytest.raises(ExchangeError) as excinfo:
        registry.approve(
            store=store,
            project_id=PROJECT,
            plan_id=PLAN_ID,
            revision=ready_record.revision,
            principal_id="human-principal-1",
            validation=validation,
            context=context,
            body=body,
            operation="POST .../approvals",
            approved_at=_fmt(_now()),
        )
    assert excinfo.value.code == "CONTEXT_STALE"
    assert excinfo.value.http_status == 409


def test_approve_rejects_when_revision_is_no_longer_head(store, ready_record):
    """제출된 새 revision 이 head 를 앞서가면(superseded) 옛 revision 승인은 REVISION_CONFLICT."""
    store.submit(
        plan=_plan(base_revision=1),
        expected_revision=1,
        principal_id="principal-1",
        operation="PUT .../plans/plan-1 rev2",
        idempotency_key="submit-2",
    )
    registry = ApprovalRegistry()
    validation = _validation_ref(ready_record)
    context = _context_ref()
    with pytest.raises(ExchangeError) as excinfo:
        registry.approve(
            store=store,
            project_id=PROJECT,
            plan_id=PLAN_ID,
            revision=ready_record.revision,  # 이제 head 가 아니다(2)
            principal_id="human-principal-1",
            validation=validation,
            context=context,
            body=_body(ready_record, validation, context),
            operation="POST .../approvals",
            approved_at=_fmt(_now()),
        )
    assert excinfo.value.code == "REVISION_CONFLICT"


def test_approve_is_idempotent_and_conflicts_on_different_request(store, ready_record):
    registry = ApprovalRegistry()
    validation = _validation_ref(ready_record)
    context = _context_ref()
    body = _body(ready_record, validation, context)
    kwargs = dict(
        store=store,
        project_id=PROJECT,
        plan_id=PLAN_ID,
        revision=ready_record.revision,
        principal_id="human-principal-1",
        validation=validation,
        context=context,
        operation="POST .../approvals",
        approved_at=_fmt(_now()),
    )
    first = registry.approve(body=body, **kwargs)
    replayed = registry.approve(body=body, **kwargs)
    assert replayed.approval_id == first.approval_id
    assert replayed.approved_at == first.approved_at

    different_body = dict(body)
    different_body["validation_id"] = "val-2"
    with pytest.raises(ExchangeError) as excinfo:
        registry.approve(body=different_body, **kwargs)
    assert excinfo.value.code == "IDEMPOTENCY_CONFLICT"


def test_approval_registry_never_mutates_the_immutable_plan_revisions_row(store, ready_record):
    """plan_revisions 는 형제 SPEC 소유(PRESERVE) — approve() 뒤에도 store 가 읽는 상태는
    바뀌지 않는다. 이 층은 자신의 오버레이(registry)에만 approved/rejected 를 기록한다."""
    registry = ApprovalRegistry()
    validation = _validation_ref(ready_record)
    context = _context_ref()
    before = store.get(project_id=PROJECT, plan_id=PLAN_ID, revision=ready_record.revision)
    registry.approve(
        store=store,
        project_id=PROJECT,
        plan_id=PLAN_ID,
        revision=ready_record.revision,
        principal_id="human-principal-1",
        validation=validation,
        context=context,
        body=_body(ready_record, validation, context),
        operation="POST .../approvals",
        approved_at=_fmt(_now()),
    )
    after = store.get(project_id=PROJECT, plan_id=PLAN_ID, revision=ready_record.revision)
    assert before == after


# ---------------------------------------------------------------------------
# ApprovalRegistry.reject
# ---------------------------------------------------------------------------


def test_reject_records_reason_without_touching_store(store, ready_record):
    registry = ApprovalRegistry()
    result = registry.reject(
        store=store,
        project_id=PROJECT,
        plan_id=PLAN_ID,
        revision=ready_record.revision,
        reason="예술적 의도와 맞지 않음",
        idempotency_key="rej-1",
        operation="POST .../rejections",
    )
    assert result["state"] == "rejected"
    assert result["plan_digest"] == ready_record.plan_digest
    # plan_revisions 자체는 불변 — state 는 여전히 store.STATE_SUBMITTED 다.
    stored = store.get(project_id=PROJECT, plan_id=PLAN_ID, revision=ready_record.revision)
    assert stored.state == "submitted"


def test_reject_requires_nonempty_reason(store, ready_record):
    registry = ApprovalRegistry()
    with pytest.raises(ExchangeError) as excinfo:
        registry.reject(
            store=store,
            project_id=PROJECT,
            plan_id=PLAN_ID,
            revision=ready_record.revision,
            reason="",
            idempotency_key="rej-2",
            operation="POST .../rejections",
        )
    assert excinfo.value.code == "SCHEMA_INVALID"


# ---------------------------------------------------------------------------
# 무효화 판정 — check_validity
# ---------------------------------------------------------------------------


def _binding(**overrides: Any) -> ApprovalBinding:
    base = dict(
        approval_id="appr-1",
        plan_id=PLAN_ID,
        plan_revision=1,
        plan_digest="sha256:" + "a" * 64,
        context_digest="sha256:" + "b" * 64,
        compiled_digest="sha256:" + "c" * 64,
        principal_id="human-principal-1",
        console_id="console-1",
        session_id="console-session-1",
        safety_policy_revision=7,
        approved_at=_fmt(_now()),
        expires_at=_fmt(_now() + timedelta(minutes=10)),
    )
    base.update(overrides)
    return ApprovalBinding(**base)


def test_check_validity_passes_when_nothing_changed():
    binding = _binding()
    reasons = check_validity(
        binding,
        current_head=1,
        current_context_digest=binding.context_digest,
        now=_fmt(_now() + timedelta(minutes=1)),
    )
    assert reasons == ()


def test_check_validity_flags_head_change():
    binding = _binding()
    reasons = check_validity(
        binding,
        current_head=2,  # 새 revision 이 제출됐다
        current_context_digest=binding.context_digest,
        now=_fmt(_now() + timedelta(minutes=1)),
    )
    assert "head_changed" in reasons


def test_check_validity_flags_context_change():
    """context_digest 하나가 compiler/target/policy 아홉 축을 전부 덮으므로
    (context.py NINE_AXES) mutation/compiler/target/policy 변경은 이 한 비교로
    잡힌다 — REQ-020 이 "context stale·compiler/target/policy 변경"을 나열한 것과
    부합한다(design.md 의 결정과 같은 원리, context.py stale_bindings 참고)."""
    binding = _binding()
    reasons = check_validity(
        binding,
        current_head=1,
        current_context_digest="sha256:" + "9" * 64,  # 리그/compiler/target 변경
        now=_fmt(_now() + timedelta(minutes=1)),
    )
    assert "context_changed" in reasons


def test_check_validity_flags_expiry():
    binding = _binding()
    reasons = check_validity(
        binding,
        current_head=1,
        current_context_digest=binding.context_digest,
        now=_fmt(_now() + timedelta(minutes=11)),  # expires_at 을 지났다
    )
    assert "expired" in reasons


def test_check_validity_reports_all_reasons_together():
    binding = _binding()
    reasons = check_validity(
        binding,
        current_head=2,
        current_context_digest="sha256:" + "9" * 64,
        now=_fmt(_now() + timedelta(minutes=11)),
    )
    assert set(reasons) == {"head_changed", "context_changed", "expired"}


# ---------------------------------------------------------------------------
# route 층 — human-only, director 전용. MCP·일반 WS boolean 은 이 모듈에 못 온다.
# ---------------------------------------------------------------------------


@pytest.fixture
def credential_registry() -> CredentialRegistry:
    return CredentialRegistry()


@pytest.fixture
def secret_store() -> PairingSecretStore:
    return PairingSecretStore()


def _issue(
    registry: CredentialRegistry,
    secret_store: PairingSecretStore,
    *,
    audience: str,
    scopes: frozenset[str],
) -> tuple[str, str]:
    credential = Credential(
        credential_id=f"cred-{audience}",
        audience=audience,
        project_id=PROJECT,
        principal_id="human-principal-1",
        session_id="session-1",
        scopes=frozenset(scopes),
        issued_at=0.0,
        expires_at=9_999_999_999.0,
    )
    secret = generate_secret()
    registry.register(credential)
    secret_store.set(credential.credential_id, secret)
    return credential.credential_id, secret


@pytest.fixture
def client(store: DirectorStore, credential_registry, secret_store):
    """`director_api.py` 의 handler 는 ``async def`` 다 — `DirectorStore` 의 sqlite3
    connection 은 **생성한 스레드에서만** 쓸 수 있다(`director_api.py` 코드 주석,
    `store.py` PRESERVE). `TestClient` 는 ASGI 앱을 별도 portal 스레드에서 돌리므로,
    pytest 스레드에서 만든 `store`(위 fixture, service 층 시험이 공유)를 그대로
    주입하면 다른 스레드에서 같은 connection 을 쓰게 되어 깨진다.

    그래서 route 층 시험만을 위한 **두 번째 connection**을 같은 sqlite 파일에
    `app` 의 startup 훅(=portal 스레드) 안에서 새로 연다 — 파일은 같으므로
    `store` fixture 가 이미 커밋한 행(``ready_record``)이 그대로 보인다.
    """
    from server.director.auth import APP_HUMAN_SCOPES, MCP_SCOPES  # noqa: F401

    db_path = store.path
    deps_holder: dict[str, DirectorApiDeps] = {}

    @contextlib.asynccontextmanager
    async def _lifespan(app: FastAPI):
        route_store = DirectorStore(db_path)
        deps = DirectorApiDeps(
            store=route_store,
            knowledge=KnowledgeService(),
            service=DirectorService(route_store),
            registry=credential_registry,
            secrets=secret_store,
            allowed_hosts=(DEFAULT_HOST.split(":")[0],),
            trusted_origins=(TRUSTED_ORIGIN,),
            approvals=ApprovalRegistry(),
        )
        deps_holder["deps"] = deps
        app.include_router(build_director_router(deps))
        yield
        route_store.close()

    app = FastAPI(lifespan=_lifespan)

    with TestClient(app) as test_client:
        test_client.deps = deps_holder["deps"]  # type: ignore[attr-defined]
        yield test_client


def _headers(credential_id: str, secret: str) -> dict[str, str]:
    return {
        "authorization": f"Bearer {encode_bearer_token(credential_id, secret)}",
        "host": DEFAULT_HOST,
        "origin": TRUSTED_ORIGIN,
    }


def test_mcp_credential_cannot_reach_approvals_route(
    client, credential_registry, secret_store, ready_record
):
    """AC-020: MCP 호출로 승인을 시도해도 director 승인으로 인정하지 않는다 —
    plan:approve 는 human-only scope 이므로 MCP credential 은 SCOPE_DENIED 로
    이 라우트 진입조차 못 한다(auth.authenticate 가 approvals.py 도달 전에 막는다)."""
    from server.director.auth import MCP_SCOPES

    credential_id, secret = _issue(
        credential_registry, secret_store, audience=AUDIENCE_MCP, scopes=MCP_SCOPES
    )
    response = client.post(
        f"/api/director/v1/projects/{PROJECT}/plans/{PLAN_ID}/revisions/{ready_record.revision}/approvals",
        json={
            "validation_id": "val-1",
            "plan_digest": ready_record.plan_digest,
            "context_digest": "sha256:" + "c" * 64,
            "compiled_digest": "sha256:" + "d" * 64,
            "idempotency_key": "k-1",
        },
        headers=_headers(credential_id, secret),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SCOPE_DENIED"


def test_general_ws_style_boolean_body_is_structurally_rejected(
    client, credential_registry, secret_store, ready_record
):
    """AC-020: 일반 chat/WS boolean 승인 형태(예: {"approved": true})는 director 승인
    route 의 필수 필드(validation_id·세 digest·idempotency_key)를 갖추지 못하므로
    구조적으로 거부된다 — director 승인으로 인정되지 않는다."""
    from server.director.auth import APP_HUMAN_SCOPES

    credential_id, secret = _issue(
        credential_registry, secret_store, audience=AUDIENCE_APP_HUMAN, scopes=APP_HUMAN_SCOPES
    )
    response = client.post(
        f"/api/director/v1/projects/{PROJECT}/plans/{PLAN_ID}/revisions/{ready_record.revision}/approvals",
        json={"approved": True},
        headers=_headers(credential_id, secret),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SCHEMA_INVALID"


def test_human_credential_approves_via_app_route(
    client, credential_registry, secret_store, ready_record
):
    from server.director.auth import APP_HUMAN_SCOPES

    credential_id, secret = _issue(
        credential_registry, secret_store, audience=AUDIENCE_APP_HUMAN, scopes=APP_HUMAN_SCOPES
    )
    validation = _validation_ref(ready_record)
    context = _context_ref()
    client.deps.validation_provider = _StubValidationProvider(validation)  # type: ignore[attr-defined]
    client.deps.context_provider = _StubContextProvider(context)  # type: ignore[attr-defined]

    response = client.post(
        f"/api/director/v1/projects/{PROJECT}/plans/{PLAN_ID}/revisions/{ready_record.revision}/approvals",
        json={
            "validation_id": validation.validation_id,
            "plan_digest": ready_record.plan_digest,
            "context_digest": context.context_digest,
            "compiled_digest": validation.compiled_digest,
            "idempotency_key": "k-1",
        },
        headers=_headers(credential_id, secret),
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body["approval"]) == set(APPROVAL_BINDING_FIELDS)
    assert body["approval"]["console_id"] == context.console_id
    assert body["record"]["state"] == "approved"


def test_human_credential_rejects_via_app_route(
    client, credential_registry, secret_store, ready_record
):
    from server.director.auth import APP_HUMAN_SCOPES

    credential_id, secret = _issue(
        credential_registry, secret_store, audience=AUDIENCE_APP_HUMAN, scopes=APP_HUMAN_SCOPES
    )
    response = client.post(
        f"/api/director/v1/projects/{PROJECT}/plans/{PLAN_ID}/revisions/{ready_record.revision}/rejections",
        json={"reason": "예술적 의도와 맞지 않음", "idempotency_key": "k-2"},
        headers=_headers(credential_id, secret),
    )
    assert response.status_code == 200
    assert response.json()["state"] == "rejected"


class _StubValidationProvider:
    def __init__(self, validation: ValidationRef) -> None:
        self._validation = validation

    def get(self, project_id: str, validation_id: str) -> ValidationRef:
        return self._validation


class _StubContextProvider:
    def __init__(self, context: ContextRef) -> None:
        self._context = context

    def current(self, project_id: str) -> dict[str, Any]:
        return {
            "context_digest": self._context.context_digest,
            "expires_at": self._context.expires_at,
            "target": {
                "console_id": self._context.console_id,
                "session_id": self._context.session_id,
            },
            "safety_policy_revision": self._context.safety_policy_revision,
        }
