"""Director HTTP route 골격 (SPEC-LDRECV-001 M1 · REQ-LDPLUGIN-018/019).

계약 §3 의 공통 route(GET context/knowledge/plan, POST validations, PUT plan,
GET execution, POST feedback-proposals)를 `auth.authenticate` 뒤에 얇게
배선한다. 판단·검증은 하지 않는다 — LDSTORE(`DirectorStore`)와 LDCOMPILE(주입된
validator, `DirectorService` 경유)을 그대로 호출할 뿐이다.

GET execution · POST feedback-proposals 는 아직 근거 저장소가 없다(각각 M4
durable execution journal, M2 사람 승인/feedback 저장소 — 이 SPEC 의 뒤
마일스톤). GET context · GET knowledge 도 "현재 server-owned context" 를 만들
관측 배선(콘솔 판독)이 이 SPEC 의 범위 밖이다 — 그래서 이 넷은 `deps` 에 해당
provider 가 주입되지 않으면 계약 §5 의 ``503 DEPENDENCY_UNAVAILABLE`` 을
정직하게 답한다. 아직 없는 기능을 있는 것처럼 꾸미지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from server.director.approvals import ApprovalRegistry, ContextRef, ValidationRef
from server.director.auth import (
    DEFAULT_HOST_ALLOWLIST,
    CredentialRegistry,
    PairingSecretStore,
    authenticate,
)
from server.director.execution import (
    ApplyCoordinator,
    BundleSender,
    ExecutionJournal,
    InterferenceDetector,
    execute_bundles,
)
from server.director.knowledge import KnowledgeService
from server.director.models import Detail, ExchangeError
from server.director.service import DirectorService, NotInstalledValidator, PlanValidator
from server.director.store import DirectorStore

_REQUEST_ID_HEADER = "x-request-id"


class ContextProvider(Protocol):
    """GET context 의 조회 seam. 이 SPEC 에는 콘솔/관측 배선이 없다 — 미주입 기본."""

    def current(self, project_id: str) -> dict[str, Any]: ...


class ExecutionProvider(Protocol):
    """GET execution 의 조회 seam. M4 durable journal 이 채운다."""

    def get(self, project_id: str, execution_id: str) -> dict[str, Any]: ...


class FeedbackProposalService(Protocol):
    """POST feedback-proposals 의 저장 seam. M2 가 채운다."""

    def propose(
        self, *, project_id: str, feedback: dict[str, Any], idempotency_key: str
    ) -> dict[str, Any]: ...


class ValidationProvider(Protocol):
    """`POST .../approvals` 가 참조하는 `ValidationReport` 조회 seam.

    `SPEC-LDCOMPILE-001` 이 만들 저장소가 아직 HTTP 로 노출되지 않았다 —
    `ContextProvider`/`ExecutionProvider` 와 같은 이유로 미주입 시 503 을
    정직하게 답한다(모듈 상단 docstring).
    """

    def get(self, project_id: str, validation_id: str) -> ValidationRef: ...


@dataclass
class DirectorApiDeps:
    """M1 이 배선하는 것 전부 — 실제 LDSTORE/LDCOMPILE 서비스 + 인증 자료.

    ``context_provider``/``execution_provider``/``feedback_service`` 는 이
    SPEC 의 뒤 마일스톤(또는 범위 밖의 관측 배선)이 채우는 seam 이다 — M1 은
    Protocol 만 소유하고 기본값은 ``None`` 이다.
    """

    store: DirectorStore
    knowledge: KnowledgeService
    service: DirectorService
    registry: CredentialRegistry
    secrets: PairingSecretStore
    #: `POST .../validations` 의 무저장 재검증 경로가 쓰는 validator. ``None``
    #: 이면 `NotInstalledValidator()` — `deps.service` 가 이미 물고 있는
    #: private `_validator` 를 밖에서 다시 꺼내지 않기 위해 별도 필드로 둔다
    #: (호출자는 같은 validator 인스턴스를 두 곳에 넘기면 된다).
    validator: PlanValidator | None = None
    allowed_hosts: tuple[str, ...] = field(default_factory=lambda: DEFAULT_HOST_ALLOWLIST)
    trusted_origins: tuple[str, ...] = ()
    context_provider: ContextProvider | None = None
    execution_provider: ExecutionProvider | None = None
    feedback_service: FeedbackProposalService | None = None
    #: M2 (SPEC-LDRECV-001) 사람 승인/거절 오버레이. 기본값은 새 in-memory
    #: registry — durable 저장은 M4 가 한다(approvals.py 모듈 docstring).
    approvals: ApprovalRegistry = field(default_factory=ApprovalRegistry)
    #: `POST .../approvals` 가 참조하는 ValidationReport 조회 seam. 미주입 시 503.
    validation_provider: ValidationProvider | None = None
    #: M5 (SPEC-LDRECV-001) apply 직전 재검사 + durable journal 커밋 + SafetyGate
    #: 연결 조율자. 미주입 시 `POST .../apply` 는 503 을 답한다.
    apply_coordinator: ApplyCoordinator | None = None
    #: M4/M5 durable execution journal — apply 이후 bundle 전송 결과를 기록한다.
    execution_journal: ExecutionJournal | None = None
    #: 실제 콘솔 송신 seam (execution.py 모듈 docstring — 이 SPEC 은 구현체를
    #: 만들지 않는다). 미주입 시 apply 는 journal 커밋·gate 연결까지만 하고
    #: bundle 전송은 건너뛴다(부분 배선 — 이 층의 콘솔 게이트 경계, spec.md §5).
    bundle_sender: BundleSender | None = None
    #: operator 개입(programmer 변경) 감지 seam. 미주입 시 개입 감지 없이 진행한다.
    interference_detector: InterferenceDetector | None = None


def _request_id(request: Request) -> str:
    return request.headers.get(_REQUEST_ID_HEADER, "unknown")


def _error_response(error: ExchangeError, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=error.http_status, content=error.to_envelope(_request_id(request))
    )


def _identity_mismatch(field_name: str, path_value: str, body_value: str) -> ExchangeError:
    """계약 §3 — path/query 와 body 의 project/plan ID 불일치는 422 IDENTITY_MISMATCH."""
    return ExchangeError(
        "IDENTITY_MISMATCH",
        422,
        f"path 의 {field_name}({path_value!r})와 body 의 {field_name}({body_value!r})가 다릅니다.",
        (Detail(f"/{field_name}", "path/body identity mismatch"),),
    )


def _dependency_unavailable(what: str) -> ExchangeError:
    return ExchangeError("DEPENDENCY_UNAVAILABLE", 503, f"{what} 이(가) 아직 배선되지 않았습니다.")


def build_director_router(deps: DirectorApiDeps) -> APIRouter:
    """계약 §3 공통 route 를 인증 뒤에 배선한다.

    router 는 project 경로 prefix (``/api/director/v1/projects/{project_id}``)
    아래 계약 §3 의 여섯 route 형태를 갖는다. 모든 handler 는 `auth.authenticate`
    를 먼저 거치고, 실패는 `ExchangeError` → :func:`_error_response` 로 계약
    §3 의 `ErrorEnvelope` shape 을 그대로 돌려준다.
    """

    router = APIRouter(prefix="/api/director/v1/projects/{project_id}")

    # 모든 handler 를 ``async def`` 로 둔다 — ``deps.store`` (`DirectorStore`)
    # 는 `sqlite3.connect()` 를 생성 스레드에 고정한다(`server/director/store.py`,
    # PRESERVE, 수정 불가). ``def`` handler 는 FastAPI 가 threadpool 로 보내
    # 매 요청마다 다른 스레드에서 실행될 수 있어(`run_in_threadpool`) 이
    # 제약을 깬다 — 실측: `sqlite3.ProgrammingError: SQLite objects created
    # in a thread can only be used in that same thread.` ``async def`` 는
    # event loop 스레드에서 직접 실행되므로, `deps` 를 그 스레드에서 구성하는
    # 한(앱 startup/lifespan) 이 제약이 지켜진다 — 호출자(`serve.py` 조립부)
    # 는 `DirectorStore` 를 event loop 스레드 밖(별도 스레드/프로세스 풀)에서
    # 구성하지 않아야 한다.

    def _require_credential(request: Request, *, scope: str):
        return authenticate(
            authorization_header=request.headers.get("authorization"),
            host_header=request.headers.get("host"),
            origin_header=request.headers.get("origin"),
            required_scope=scope,
            registry=deps.registry,
            secrets_store=deps.secrets,
            allowed_hosts=deps.allowed_hosts,
            trusted_origins=deps.trusted_origins,
        )

    @router.get("/context")
    async def get_context(project_id: str, request: Request):
        try:
            _require_credential(request, scope="context:read")
            if deps.context_provider is None:
                raise _dependency_unavailable("context provider")
            return deps.context_provider.current(project_id)
        except ExchangeError as error:
            return _error_response(error, request)

    @router.get("/knowledge")
    async def get_knowledge(
        project_id: str,
        query: str,
        limit: int,
        request: Request,
        cursor: str | None = None,
    ):
        try:
            credential = _require_credential(request, scope="knowledge:read")
            # 계약 §3 — 검색 범위는 "서버의 현재 project context" 에 고정된다.
            # 현재 context 가 없으면(§ 상단 docstring 이유) 검색 자체가 성립하지
            # 않는다 — GET context 와 동일한 의존이다.
            if deps.context_provider is None:
                raise _dependency_unavailable("context provider")
            context = deps.context_provider.current(project_id)
            page = deps.knowledge.search(
                project_id=project_id,
                principal_id=credential.principal_id,
                query=query,
                limit=limit,
                context_id=context["context_id"],
                context_digest=context["context_digest"],
                cursor=cursor,
            )
            return page.as_dict()
        except ExchangeError as error:
            return _error_response(error, request)

    @router.get("/plans/{plan_id}")
    async def get_plan(
        project_id: str, plan_id: str, request: Request, revision: int | None = None
    ):
        try:
            _require_credential(request, scope="plan:read")
            record = deps.store.get(project_id=project_id, plan_id=plan_id, revision=revision)
            return {
                "plan": record.plan,
                "revision": record.revision,
                "state": record.state,
                "plan_digest": record.plan_digest,
            }
        except ExchangeError as error:
            return _error_response(error, request)

    @router.post("/plans/{plan_id}/revisions/{revision}/approvals")
    async def post_approval(
        project_id: str, plan_id: str, revision: int, body: dict[str, Any], request: Request
    ):
        """계약 §4 — human APP route 만 승인을 발급한다 (REQ-LDPLUGIN-020 M2).

        MCP credential 은 ``plan:approve`` 가 human-only scope 이므로
        `auth.authenticate` 단계에서 SCOPE_DENIED 로 이미 거부되어 이 handler
        본문에 도달하지 않는다. 일반 chat/WS 승인 boolean(예: ``{"approved":
        true}``)은 아래 필수 필드 검사에서 SCHEMA_INVALID 로 구조적으로 거부된다.
        """
        try:
            credential = _require_credential(request, scope="plan:approve")

            # 일반 chat/WS 승인 boolean(예: {"approved": true})은 director 승인
            # route 의 필수 필드를 갖추지 못하므로 여기서 SCHEMA_INVALID 로 구조적
            # 거부된다 — dependency 미배선(503)보다 형태 검사가 먼저다: 형태부터
            # 틀린 요청은 애초에 director 승인 시도가 아니었다는 판정을 우선한다.
            validation_id = body.get("validation_id")
            plan_digest = body.get("plan_digest")
            context_digest = body.get("context_digest")
            compiled_digest = body.get("compiled_digest")
            idempotency_key = body.get("idempotency_key")
            if not all(
                isinstance(value, str) and value
                for value in (
                    validation_id,
                    plan_digest,
                    context_digest,
                    compiled_digest,
                    idempotency_key,
                )
            ):
                raise ExchangeError(
                    "SCHEMA_INVALID",
                    422,
                    "validation_id·plan_digest·context_digest·compiled_digest·"
                    "idempotency_key 가 모두 필요합니다.",
                    (Detail("", "missing approval fields — not a director approval"),),
                )

            if deps.validation_provider is None or deps.context_provider is None:
                raise _dependency_unavailable("validation/context provider")

            validation = deps.validation_provider.get(project_id, str(validation_id))
            context_snapshot = deps.context_provider.current(project_id)
            context = ContextRef.from_snapshot(context_snapshot)

            binding = deps.approvals.approve(
                store=deps.store,
                project_id=project_id,
                plan_id=plan_id,
                revision=revision,
                principal_id=credential.principal_id,
                validation=validation,
                context=context,
                body=body,
                operation=(
                    f"POST /api/director/v1/projects/{project_id}/plans/{plan_id}/"
                    f"revisions/{revision}/approvals"
                ),
            )
            record = deps.store.get(project_id=project_id, plan_id=plan_id, revision=revision)
            return JSONResponse(
                status_code=201,
                content={
                    "approval": binding.as_dict(),
                    "record": {
                        "plan": record.plan,
                        "revision": record.revision,
                        "state": "approved",
                        "plan_digest": record.plan_digest,
                    },
                },
            )
        except ExchangeError as error:
            return _error_response(error, request)

    @router.post("/plans/{plan_id}/revisions/{revision}/rejections")
    async def post_rejection(
        project_id: str, plan_id: str, revision: int, body: dict[str, Any], request: Request
    ):
        """계약 §4 — human APP route 만 거절을 기록한다 (REQ-LDPLUGIN-020 M2)."""
        try:
            credential = _require_credential(request, scope="plan:reject")
            reason = body.get("reason")
            idempotency_key = body.get("idempotency_key")
            if not isinstance(reason, str) or not isinstance(idempotency_key, str):
                raise ExchangeError(
                    "SCHEMA_INVALID",
                    422,
                    "reason·idempotency_key 가 필요합니다.",
                    (Detail("", "missing reason/idempotency_key"),),
                )
            result = deps.approvals.reject(
                store=deps.store,
                project_id=project_id,
                plan_id=plan_id,
                revision=revision,
                reason=reason,
                idempotency_key=idempotency_key,
                principal_id=credential.principal_id,
                operation=(
                    f"POST /api/director/v1/projects/{project_id}/plans/{plan_id}/"
                    f"revisions/{revision}/rejections"
                ),
            )
            return result
        except ExchangeError as error:
            return _error_response(error, request)

    @router.post("/validations")
    async def post_validations(project_id: str, body: dict[str, Any], request: Request):
        try:
            _require_credential(request, scope="plan:validate")
            plan = body.get("plan")
            if not isinstance(plan, dict):
                raise ExchangeError(
                    "SCHEMA_INVALID", 422, "plan 은 object 여야 합니다.", (Detail("/plan", ""),)
                )
            if str(plan.get("project_id")) != project_id:
                raise _identity_mismatch("project_id", project_id, str(plan.get("project_id")))
            # M1 은 저장 없이 validator 를 직접 호출한다 — 실제 저장 경로는
            # PUT plan(`DirectorService.submit`)이 이미 검증을 함께 수행한다
            # (`service.py`). 이 route 는 `ld_validate_plan`(계약 §3) 의 "짧은
            # report 저장은 허용, console 불변" 을 따르는 무저장 재검증 경로다.
            validator = deps.validator or NotInstalledValidator()
            return validator.validate(plan)
        except ExchangeError as error:
            return _error_response(error, request)

    @router.put("/plans/{plan_id}")
    async def put_plan(project_id: str, plan_id: str, body: dict[str, Any], request: Request):
        try:
            credential = _require_credential(request, scope="plan:submit")
            plan = body.get("plan")
            if not isinstance(plan, dict):
                raise ExchangeError(
                    "SCHEMA_INVALID", 422, "plan 은 object 여야 합니다.", (Detail("/plan", ""),)
                )
            if str(plan.get("project_id")) != project_id:
                raise _identity_mismatch("project_id", project_id, str(plan.get("project_id")))
            if str(plan.get("plan_id")) != plan_id:
                raise _identity_mismatch("plan_id", plan_id, str(plan.get("plan_id")))
            expected_revision = body.get("expected_revision")
            idempotency_key = body.get("idempotency_key")
            if not isinstance(expected_revision, int) or not isinstance(idempotency_key, str):
                raise ExchangeError(
                    "SCHEMA_INVALID",
                    422,
                    "expected_revision·idempotency_key 가 필요합니다.",
                    (Detail("", "missing expected_revision/idempotency_key"),),
                )
            result = deps.service.submit(
                plan=plan,
                expected_revision=expected_revision,
                principal_id=credential.principal_id,
                operation=f"PUT /api/director/v1/projects/{project_id}/plans/{plan_id}",
                idempotency_key=idempotency_key,
            )
            return {
                "record": {
                    "plan": result.record.plan,
                    "revision": result.record.revision,
                    "state": result.state,
                    "plan_digest": result.record.plan_digest,
                },
                "validation": result.validation,
            }
        except ExchangeError as error:
            return _error_response(error, request)

    @router.post("/plans/{plan_id}/revisions/{revision}/apply")
    async def post_apply(
        project_id: str, plan_id: str, revision: int, body: dict[str, Any], request: Request
    ):
        """계약 §4 — apply 는 lock 안 재검사(REQ-LDPLUGIN-021)를 통과한 뒤에만
        SafetyGate 로 연결한다(REQ-LDPLUGIN-024 의 실패 분류는
        :func:`server.director.execution.execute_bundles` 가 맡는다).

        MCP credential 은 ``plan:apply`` 가 human-only scope 이므로
        `auth.authenticate` 단계에서 SCOPE_DENIED 로 이미 거부되어 이 handler
        본문에 도달하지 않는다.
        """
        try:
            credential = _require_credential(request, scope="plan:apply")

            if deps.apply_coordinator is None or deps.context_provider is None:
                raise _dependency_unavailable("apply coordinator/context provider")

            context_snapshot = deps.context_provider.current(project_id)
            result = deps.apply_coordinator.apply(
                project_id=project_id,
                plan_id=plan_id,
                revision=revision,
                principal_id=credential.principal_id,
                operation=(
                    f"POST /api/director/v1/projects/{project_id}/plans/{plan_id}/"
                    f"revisions/{revision}/apply"
                ),
                current_context_digest=str(context_snapshot["context_digest"]),
                body=body,
            )

            # 실제 bundle 전송은 이 SPEC 의 콘솔 게이트 경계다(spec.md §5) — sender
            # 가 배선되지 않았거나 이미 replay 된 응답이면 journal 커밋·gate 연결
            # 결과만 그대로 돌려준다.
            journal_ready = deps.execution_journal is not None
            if deps.bundle_sender is not None and not result.replayed and journal_ready:
                bundles = body.get("bundles") or []
                outcome = execute_bundles(
                    deps.execution_journal,
                    execution_id=result.execution_id,
                    bundles=bundles,
                    sender=deps.bundle_sender,
                    interference=deps.interference_detector,
                )
                return JSONResponse(
                    status_code=result.response_status,
                    content={**result.response_body, **outcome},
                )

            return JSONResponse(status_code=result.response_status, content=result.response_body)
        except ExchangeError as error:
            return _error_response(error, request)

    @router.get("/executions/{execution_id}")
    async def get_execution(project_id: str, execution_id: str, request: Request):
        try:
            _require_credential(request, scope="execution:read")
            if deps.execution_provider is None:
                raise _dependency_unavailable("execution provider")
            return deps.execution_provider.get(project_id, execution_id)
        except ExchangeError as error:
            return _error_response(error, request)

    @router.post("/feedback-proposals")
    async def post_feedback_proposals(project_id: str, body: dict[str, Any], request: Request):
        try:
            _require_credential(request, scope="feedback:propose")
            if deps.feedback_service is None:
                raise _dependency_unavailable("feedback proposal service")
            feedback = body.get("feedback")
            idempotency_key = body.get("idempotency_key")
            if not isinstance(feedback, dict) or not isinstance(idempotency_key, str):
                raise ExchangeError(
                    "SCHEMA_INVALID",
                    422,
                    "feedback·idempotency_key 가 필요합니다.",
                    (Detail("", "missing feedback/idempotency_key"),),
                )
            return deps.feedback_service.propose(
                project_id=project_id, feedback=feedback, idempotency_key=idempotency_key
            )
        except ExchangeError as error:
            return _error_response(error, request)

    return router
