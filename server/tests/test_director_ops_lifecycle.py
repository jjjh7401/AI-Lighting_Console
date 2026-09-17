"""SPEC-LDRECV-001 M6 · REQ-LDPLUGIN-032 · AC-LDPLUGIN-032.

운영 중단·recovery — 이 SPEC의 마지막 마일스톤. 계약 §10이 단일 원본이다.

이 파일이 확인하는 것은 로컬로 닫히는 네 가지뿐이다(spec.md §5 — 승격부인
"recovery apply 가 실제로 콘솔에 적용됐는가"는 콘솔 게이트, 이 파일의 범위 밖):

1. 철회 직후 해당 principal 의 (MCP·human 모두) credential 로 어떤 route 를
   호출해도 UNAUTHENTICATED.
2. 철회 이후 신규 apply 요청이 credential 확인 단계에서 즉시 거부된다 —
   ApplyCoordinator 본문에 도달하지 않는다.
3. journal(bundle 기록·idempotency 응답)은 철회 전후 바이트 동일 — 삭제·수정된
   필드가 없다.
4. recovery 흐름에서 원본 execution 의 partial/unknown 기록이 새 execution
   생성 후에도 그대로 남아 있다(recovery_of 로만 연결되고 덮어쓰지 않는다).

## 신규 apply 차단은 별도 메커니즘이 아니다

이 SPEC 이 채택한 설계(ops.py 모듈 docstring)는 "인증 철회 자체가 모든 route 를
막는다"이다 — director_api.py 의 모든 handler 가 `auth.authenticate()` 를
가장 먼저 거치므로(auth.py `@MX:ANCHOR`), 별도의 "apply 차단 플래그"를 만들
필요가 없다. 그래서 항목 2 시험은 HTTP 라우트 층에서 ApplyCoordinator 가
**호출되지 않았음**을 스파이로 확인한다.
"""

from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.director.approvals import ApprovalBinding, ApprovalRegistry
from server.director.auth import (
    APP_HUMAN_SCOPES,
    AUDIENCE_APP_HUMAN,
    AUDIENCE_MCP,
    MCP_SCOPES,
    Credential,
    CredentialRegistry,
    PairingSecretStore,
    authenticate,
    encode_bearer_token,
    generate_secret,
)
from server.director.director_api import DirectorApiDeps, build_director_router
from server.director.execution import (
    STATE_PARTIAL,
    STATE_SENT,
    STATE_UNKNOWN,
    ApplyCoordinator,
    ExecutionJournal,
)
from server.director.knowledge import KnowledgeService
from server.director.models import ExchangeError
from server.director.ops import DecommissionResult, decommission_principal
from server.director.service import DirectorService
from server.director.store import DirectorStore

_PROJECT = "project-0001"
_PLAN = "plan-0001"
_PRINCIPAL = "principal-0001"
TRUSTED_ORIGIN = "http://127.0.0.1:37123"
DEFAULT_HOST = "127.0.0.1:37123"


# ---------------------------------------------------------------------------
# 공통 fixture — M5 시험(test_director_apply_rejection.py)과 같은 패턴.
# ---------------------------------------------------------------------------


class FakeLiveLock:
    def __init__(self, active: bool = False) -> None:
        self.is_active = active


class FakeScreenDecision:
    def __init__(self, cleared: bool, status: str = "cleared", notice: str = "") -> None:
        self.cleared = cleared
        self.status = status
        self.notice = notice


class FakeGate:
    def __init__(self, *, lock_active: bool = False, decision: FakeScreenDecision | None = None):
        self.lock = FakeLiveLock(lock_active)
        self.calls: list[list[str]] = []
        self._decision = decision or FakeScreenDecision(cleared=True)

    def execute_preapproved(self, commands):
        self.calls.append(list(commands))
        return self._decision


def _binding(
    *,
    approval_id: str = "approval-0001",
    plan_revision: int = 1,
    context_digest: str = "ctx-digest-1",
    expires_at: str = "2099-01-01T00:00:00Z",
) -> ApprovalBinding:
    return ApprovalBinding(
        approval_id=approval_id,
        plan_id=_PLAN,
        plan_revision=plan_revision,
        plan_digest="plan-digest-1",
        context_digest=context_digest,
        compiled_digest="compiled-digest-1",
        principal_id=_PRINCIPAL,
        console_id="console-1",
        session_id="session-1",
        safety_policy_revision=1,
        approved_at="2026-01-01T00:00:00Z",
        expires_at=expires_at,
    )


def _body(
    *,
    approval_id: str = "approval-0001",
    idempotency_key: str = "key-0001",
    show_id: str = "show-1",
    sequence_id: str = "sequence-1",
    recovery_of: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "approval_id": approval_id,
        "idempotency_key": idempotency_key,
        "destination": {"show_id": show_id, "sequence_id": sequence_id},
        "bundles": [{"bundle_id": "bundle-a", "commands": ["Fixture 901 At 50"]}],
    }
    if recovery_of is not None:
        payload["recovery_of"] = recovery_of
    return payload


@pytest.fixture()
def store(tmp_path: Path) -> DirectorStore:
    s = DirectorStore(tmp_path / "director.sqlite3")
    s.submit(
        plan={
            "project_id": _PROJECT,
            "plan_id": _PLAN,
            "base_revision": 0,
            "body": "v1",
        },
        expected_revision=0,
        principal_id=_PRINCIPAL,
        operation="PUT /plans/plan-0001",
        idempotency_key="submit-key-1",
    )
    return s


@pytest.fixture()
def journal(tmp_path: Path) -> ExecutionJournal:
    return ExecutionJournal(tmp_path / "execution.sqlite3")


@pytest.fixture()
def approvals() -> ApprovalRegistry:
    return ApprovalRegistry()


def _register(approvals: ApprovalRegistry, binding: ApprovalBinding) -> None:
    approvals._approvals[binding.approval_id] = binding  # type: ignore[attr-defined]
    approvals._latest_by_plan[(_PROJECT, binding.plan_id)] = binding.approval_id  # type: ignore[attr-defined]


def _coordinator(*, journal, approvals, store, gate) -> ApplyCoordinator:
    return ApplyCoordinator(journal=journal, approvals=approvals, store=store, gate=gate)


def _bump_revision(store: DirectorStore, *, base_revision: int, idempotency_key: str) -> None:
    """recovery 흐름의 "새 revision" 단계 — plan.md M6 이 요구하는
    "새 revision→검증→승인→apply" 의 첫 단계를 실제로 store 에 반영한다. 이걸
    빼면 ``check_validity`` 가 ``head_changed`` 로 recovery apply 자체를
    거부한다 — recovery approval binding 의 plan_revision 은 store 의 실제
    head 와 맞아야 한다."""
    store.submit(
        plan={
            "project_id": _PROJECT,
            "plan_id": _PLAN,
            "base_revision": base_revision,
            "body": "v2-recovery",
        },
        expected_revision=base_revision,
        principal_id=_PRINCIPAL,
        operation="PUT /plans/plan-0001",
        idempotency_key=idempotency_key,
    )


# ---------------------------------------------------------------------------
# 항목 1 — 철회 직후 UNAUTHENTICATED (MCP·human 모두)
# ---------------------------------------------------------------------------


@pytest.fixture()
def credential_registry() -> CredentialRegistry:
    return CredentialRegistry()


@pytest.fixture()
def secret_store() -> PairingSecretStore:
    return PairingSecretStore()


def _issue(
    registry: CredentialRegistry,
    secret_store: PairingSecretStore,
    *,
    audience: str,
    scopes: frozenset[str],
    credential_id: str,
    principal_id: str = _PRINCIPAL,
) -> tuple[str, str]:
    credential = Credential(
        credential_id=credential_id,
        audience=audience,
        project_id=_PROJECT,
        principal_id=principal_id,
        session_id="session-1",
        scopes=frozenset(scopes),
        issued_at=0.0,
        expires_at=9_999_999_999.0,
    )
    secret = generate_secret()
    registry.register(credential)
    secret_store.set(credential.credential_id, secret)
    return credential.credential_id, secret


class TestDecommissionRevokesEveryCredential:
    """AC-032 항목1 — 해당 principal 의 MCP/human credential 을 즉시 철회한다."""

    def test_decommission_finds_both_audiences_for_the_principal(
        self, credential_registry: CredentialRegistry, secret_store: PairingSecretStore
    ) -> None:
        mcp_id, _ = _issue(
            credential_registry,
            secret_store,
            audience=AUDIENCE_MCP,
            scopes=MCP_SCOPES,
            credential_id="cred-mcp-1",
        )
        human_id, _ = _issue(
            credential_registry,
            secret_store,
            audience=AUDIENCE_APP_HUMAN,
            scopes=APP_HUMAN_SCOPES,
            credential_id="cred-human-1",
        )
        # 다른 principal 의 credential 은 대상이 아니다 — 원치 않는 광역 철회를
        # 막는 경계 시험.
        other_id, _ = _issue(
            credential_registry,
            secret_store,
            audience=AUDIENCE_APP_HUMAN,
            scopes=APP_HUMAN_SCOPES,
            credential_id="cred-other-principal",
            principal_id="principal-other",
        )

        result = decommission_principal(
            registry=credential_registry, project_id=_PROJECT, principal_id=_PRINCIPAL
        )

        assert isinstance(result, DecommissionResult)
        assert set(result.revoked_credential_ids) == {mcp_id, human_id}
        assert credential_registry.get(mcp_id).revoked is True
        assert credential_registry.get(human_id).revoked is True
        assert credential_registry.get(other_id).revoked is False

    def test_revoked_credentials_are_unauthenticated_for_every_route_scope(
        self, credential_registry: CredentialRegistry, secret_store: PairingSecretStore
    ) -> None:
        mcp_id, mcp_secret = _issue(
            credential_registry,
            secret_store,
            audience=AUDIENCE_MCP,
            scopes=MCP_SCOPES,
            credential_id="cred-mcp-2",
        )
        human_id, human_secret = _issue(
            credential_registry,
            secret_store,
            audience=AUDIENCE_APP_HUMAN,
            scopes=APP_HUMAN_SCOPES,
            credential_id="cred-human-2",
        )

        decommission_principal(
            registry=credential_registry, project_id=_PROJECT, principal_id=_PRINCIPAL
        )

        for credential_id, secret, scope in (
            (mcp_id, mcp_secret, "context:read"),
            (human_id, human_secret, "plan:apply"),
        ):
            with pytest.raises(ExchangeError) as excinfo:
                authenticate(
                    authorization_header=(f"Bearer {encode_bearer_token(credential_id, secret)}"),
                    host_header=DEFAULT_HOST,
                    origin_header=TRUSTED_ORIGIN,
                    required_scope=scope,
                    registry=credential_registry,
                    secrets_store=secret_store,
                    trusted_origins=(TRUSTED_ORIGIN,),
                )
            assert excinfo.value.code == "UNAUTHENTICATED"

    def test_already_revoked_credential_is_idempotent(
        self, credential_registry: CredentialRegistry, secret_store: PairingSecretStore
    ) -> None:
        """두 번 철회해도 예외 없이 안전하다 — 운영 재시도를 막지 않는다."""
        human_id, _ = _issue(
            credential_registry,
            secret_store,
            audience=AUDIENCE_APP_HUMAN,
            scopes=APP_HUMAN_SCOPES,
            credential_id="cred-human-3",
        )
        decommission_principal(
            registry=credential_registry, project_id=_PROJECT, principal_id=_PRINCIPAL
        )
        result_again = decommission_principal(
            registry=credential_registry, project_id=_PROJECT, principal_id=_PRINCIPAL
        )
        assert human_id in result_again.revoked_credential_ids
        assert credential_registry.get(human_id).revoked is True


# ---------------------------------------------------------------------------
# 항목 2 — 철회 이후 신규 apply 는 credential 확인 단계에서 즉시 거부
# ---------------------------------------------------------------------------


class _SpyApplyCoordinator:
    """``.apply()`` 가 호출되면 실패시키는 스파이 — 인증 단계에서 막혀야
    이 스파이 본문에 도달하지 않는다."""

    def __init__(self) -> None:
        self.called = False

    def apply(self, **kwargs: Any) -> Any:  # pragma: no cover - 호출되면 시험이 실패한다
        self.called = True
        raise AssertionError("ApplyCoordinator.apply() 가 호출됐다 — 인증 단계가 막지 못했다.")


@pytest.fixture()
def client(
    store: DirectorStore, credential_registry: CredentialRegistry, secret_store: PairingSecretStore
):
    """`test_director_approvals.py` 의 route 층 fixture 와 같은 패턴 — handler 가
    ``async def`` 이므로 store 는 portal 스레드 안에서 새로 연다."""
    db_path = store.path
    spy = _SpyApplyCoordinator()
    deps_holder: dict[str, Any] = {"spy": spy}

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
            apply_coordinator=spy,  # type: ignore[arg-type]
            context_provider=_FakeContextProvider(),
        )
        deps_holder["deps"] = deps
        app.include_router(build_director_router(deps))
        yield
        route_store.close()

    app = FastAPI(lifespan=_lifespan)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        test_client.deps = deps_holder["deps"]  # type: ignore[attr-defined]
        yield test_client, spy


class _FakeContextProvider:
    def current(self, project_id: str) -> dict[str, Any]:
        return {
            "context_id": "ctx-1",
            "context_digest": "ctx-digest-1",
            "expires_at": "2099-01-01T00:00:00Z",
            "safety_policy_revision": 1,
            "target": {"console_id": "console-1", "session_id": "session-1"},
        }


def _apply_headers(credential_id: str, secret: str) -> dict[str, str]:
    return {
        "authorization": f"Bearer {encode_bearer_token(credential_id, secret)}",
        "host": DEFAULT_HOST,
        "origin": TRUSTED_ORIGIN,
    }


def test_revoked_human_credential_is_rejected_before_apply_coordinator_runs(
    client, credential_registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    test_client, spy = client
    human_id, human_secret = _issue(
        credential_registry,
        secret_store,
        audience=AUDIENCE_APP_HUMAN,
        scopes=APP_HUMAN_SCOPES,
        credential_id="cred-human-apply",
    )

    decommission_principal(
        registry=credential_registry, project_id=_PROJECT, principal_id=_PRINCIPAL
    )

    response = test_client.post(
        f"/api/director/v1/projects/{_PROJECT}/plans/{_PLAN}/revisions/1/apply",
        json=_body(),
        headers=_apply_headers(human_id, human_secret),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert spy.called is False


def test_non_revoked_human_credential_still_reaches_apply_coordinator(
    client, credential_registry: CredentialRegistry, secret_store: PairingSecretStore
) -> None:
    """대조군 — 철회하지 않으면 스파이까지 도달한다(그래서 스파이가 실제로
    "본문 도달"의 증거로 성립함을 보증한다)."""
    test_client, spy = client
    human_id, human_secret = _issue(
        credential_registry,
        secret_store,
        audience=AUDIENCE_APP_HUMAN,
        scopes=APP_HUMAN_SCOPES,
        credential_id="cred-human-apply-2",
    )

    response = test_client.post(
        f"/api/director/v1/projects/{_PROJECT}/plans/{_PLAN}/revisions/1/apply",
        json=_body(),
        headers=_apply_headers(human_id, human_secret),
    )

    # 스파이는 호출되면 AssertionError 를 던진다 — ExchangeError 가 아니므로
    # director_api.py 의 ``except ExchangeError`` 에 잡히지 않고 500 으로
    # 올라온다. 그 자체가 "본문에 도달했다"는 증거다.
    assert response.status_code == 500
    assert spy.called is True


# ---------------------------------------------------------------------------
# 항목 3 — journal 은 삭제·수정 API 가 없다 + 철회 전후 바이트 동일
# ---------------------------------------------------------------------------


def _dump_journal_tables(path: Path) -> dict[str, list[tuple[Any, ...]]]:
    with sqlite3.connect(path) as connection:
        tables = ("executions", "execution_bundles", "idempotency_records")
        return {
            table: sorted(connection.execute(f"SELECT * FROM {table}").fetchall())
            for table in tables
        }


class TestJournalPreservedAcrossDecommission:
    def test_execution_journal_exposes_no_delete_or_overwrite_api(self) -> None:
        """journal 보존은 "아무것도 안 한다"가 증거다 — 삭제/내용수정 API 자체가
        없다는 것을 구조로 고정한다(state 전이 메서드는 예외 — 그것은 이 SPEC이
        규정한 정상 진행이지 "삭제"가 아니다)."""
        forbidden_substrings = ("delete", "purge", "erase", "overwrite", "truncate")
        for name in dir(ExecutionJournal):
            if name.startswith("_"):
                continue
            lowered = name.lower()
            assert not any(bad in lowered for bad in forbidden_substrings), name

    def test_decommission_does_not_touch_the_journal_at_all(
        self, journal: ExecutionJournal, approvals: ApprovalRegistry, store: DirectorStore
    ) -> None:
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        _register(approvals, _binding())
        coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST /apply",
            current_context_digest="ctx-digest-1",
            body=_body(),
        )

        before = _dump_journal_tables(journal.path)

        registry = CredentialRegistry()
        secret_store = PairingSecretStore()
        _issue(
            registry,
            secret_store,
            audience=AUDIENCE_APP_HUMAN,
            scopes=APP_HUMAN_SCOPES,
            credential_id="cred-unrelated",
        )
        decommission_principal(registry=registry, project_id=_PROJECT, principal_id=_PRINCIPAL)

        after = _dump_journal_tables(journal.path)
        assert before == after


# ---------------------------------------------------------------------------
# 항목 4 — recovery 흐름: 원본 불변 + recovery_of 로만 연결
# ---------------------------------------------------------------------------


class TestRecoveryFlow:
    def test_recovery_apply_creates_a_separate_execution_linked_by_recovery_of(
        self, journal: ExecutionJournal, approvals: ApprovalRegistry, store: DirectorStore
    ) -> None:
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)

        # 원본 execution — partial/unknown 으로 확정한다(합성 crash 재현, M4
        # 시험과 같은 패턴: mark_sending 이후 finalize 를 STATE_UNKNOWN 으로).
        _register(approvals, _binding(approval_id="approval-original"))
        original = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST /apply",
            current_context_digest="ctx-digest-1",
            body=_body(approval_id="approval-original", idempotency_key="key-original"),
        )
        journal.finalize_execution(original.execution_id, STATE_UNKNOWN)
        original_snapshot_before = _dump_journal_tables(journal.path)

        # 새 revision → 검증 → 승인(새 approval binding) → apply(recovery_of=원본).
        _bump_revision(store, base_revision=1, idempotency_key="submit-key-recovery")
        _register(
            approvals,
            _binding(
                approval_id="approval-recovery",
                plan_revision=2,
                context_digest="ctx-digest-2",
            ),
        )
        recovered = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=2,
            principal_id=_PRINCIPAL,
            operation="POST /apply",
            current_context_digest="ctx-digest-2",
            body=_body(
                approval_id="approval-recovery",
                idempotency_key="key-recovery",
                sequence_id="sequence-2",  # 원본 destination 은 create-only 로 이미 점유돼 있다
                recovery_of=original.execution_id,
            ),
        )

        assert recovered.execution_id != original.execution_id
        assert journal.recovery_of(recovered.execution_id) == original.execution_id
        assert journal.status(original.execution_id) == STATE_UNKNOWN

        # 원본 행은 물리적으로 한 바이트도 바뀌지 않았다 — 새 recovery execution
        # 이 생성된 뒤에도 원본 테이블 스냅샷이 동일하다(새 행이 추가된 것과
        # 원본 행이 수정된 것은 다르다 — 여기서는 원본 관련 행만 비교한다).
        with sqlite3.connect(journal.path) as connection:
            connection.row_factory = sqlite3.Row
            original_row = dict(
                connection.execute(
                    "SELECT * FROM executions WHERE execution_id = ?",
                    (original.execution_id,),
                ).fetchone()
            )
        assert original_row["state"] == STATE_UNKNOWN
        assert original_row["execution_id"] == original.execution_id
        # 원본 스냅샷(위에서 찍은)에 이미 이 행이 그대로 들어 있었다 — recovery
        # apply 이후에도 원본 테이블 행 자체는 다시 세어도 똑같다.
        after_recovery_original_only = {
            "executions": [
                row
                for row in _dump_journal_tables(journal.path)["executions"]
                if row[0] == original.execution_id
            ]
        }
        before_original_only = {
            "executions": [
                row
                for row in original_snapshot_before["executions"]
                if row[0] == original.execution_id
            ]
        }
        assert after_recovery_original_only == before_original_only

    def test_recovery_of_rejects_a_source_that_is_not_partial_or_unknown(
        self, journal: ExecutionJournal, approvals: ApprovalRegistry, store: DirectorStore
    ) -> None:
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)

        _register(approvals, _binding(approval_id="approval-confirmed"))
        confirmed = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST /apply",
            current_context_digest="ctx-digest-1",
            body=_body(approval_id="approval-confirmed", idempotency_key="key-confirmed"),
        )
        journal.finalize_execution(confirmed.execution_id, STATE_SENT)

        _register(
            approvals,
            _binding(
                approval_id="approval-recovery-2",
                plan_revision=2,
                context_digest="ctx-digest-2",
            ),
        )
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=2,
                principal_id=_PRINCIPAL,
                operation="POST /apply",
                current_context_digest="ctx-digest-2",
                body=_body(
                    approval_id="approval-recovery-2",
                    idempotency_key="key-recovery-2",
                    recovery_of=confirmed.execution_id,
                ),
            )
        assert excinfo.value.code == "RECOVERY_SOURCE_INVALID"
        assert excinfo.value.http_status == 409

    def test_recovery_of_accepts_partial_source(
        self, journal: ExecutionJournal, approvals: ApprovalRegistry, store: DirectorStore
    ) -> None:
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)

        _register(approvals, _binding(approval_id="approval-partial"))
        partial = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=1,
            principal_id=_PRINCIPAL,
            operation="POST /apply",
            current_context_digest="ctx-digest-1",
            body=_body(approval_id="approval-partial", idempotency_key="key-partial"),
        )
        journal.finalize_execution(partial.execution_id, STATE_PARTIAL)

        _bump_revision(store, base_revision=1, idempotency_key="submit-key-recovery-3")
        _register(
            approvals,
            _binding(
                approval_id="approval-recovery-3",
                plan_revision=2,
                context_digest="ctx-digest-2",
            ),
        )
        recovered = coordinator.apply(
            project_id=_PROJECT,
            plan_id=_PLAN,
            revision=2,
            principal_id=_PRINCIPAL,
            operation="POST /apply",
            current_context_digest="ctx-digest-2",
            body=_body(
                approval_id="approval-recovery-3",
                idempotency_key="key-recovery-3",
                sequence_id="sequence-2",  # 원본 destination 은 create-only 로 이미 점유돼 있다
                recovery_of=partial.execution_id,
            ),
        )
        assert journal.recovery_of(recovered.execution_id) == partial.execution_id

    def test_recovery_of_missing_execution_is_not_found(
        self, journal: ExecutionJournal, approvals: ApprovalRegistry, store: DirectorStore
    ) -> None:
        gate = FakeGate()
        coordinator = _coordinator(journal=journal, approvals=approvals, store=store, gate=gate)
        _register(approvals, _binding())
        with pytest.raises(ExchangeError) as excinfo:
            coordinator.apply(
                project_id=_PROJECT,
                plan_id=_PLAN,
                revision=1,
                principal_id=_PRINCIPAL,
                operation="POST /apply",
                current_context_digest="ctx-digest-1",
                body=_body(recovery_of="execution-does-not-exist"),
            )
        assert excinfo.value.code == "NOT_FOUND"
