"""Director HTTP route skeleton (SPEC-LDRECV-001 M1, REQ-LDPLUGIN-018/019).

Wires contract Section 3 common routes (GET context/knowledge/plan, POST
validations, PUT plan, GET execution, POST feedback-proposals) thinly behind
auth.authenticate. No judgment or validation happens here -- it only calls into
LDSTORE (DirectorStore) and LDCOMPILE (an injected validator, via DirectorService).

GET execution / POST feedback-proposals have no backing store yet (each is a
later milestone -- M4 durable execution journal, M2 human-approval/feedback
store). GET context / GET knowledge also depend on a real "current server-owned
context" observation wiring (console readback) that was out of the original
SPEC scope -- so all four answer a contract Section 5 503
DEPENDENCY_UNAVAILABLE honestly when their deps provider is not injected,
rather than pretending a feature exists that does not.

SPEC-LDWIRE-001 M4 (design.md section "da" alternative A) changes the
POST .../validations and PUT .../plans/{plan_id} handlers to reconstruct a
context-aware PipelineValidator PER REQUEST instead of relying on a
construction-time-fixed deps.validator instance -- context.py.ContextProvider
snapshots change over a servers lifetime (REQ-LDWIRE-005), and a fixed
validator instance would keep validating against whatever context existed the
moment it was constructed. service.py and validate/pipeline.py stage content
stay untouched -- only this route layer reconstructs the validator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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
from server.director.digest import canonical_digest
from server.director.execution import (
    ApplyCoordinator,
    BundleSender,
    ExecutionJournal,
    InterferenceDetector,
    run_director_apply,
)
from server.director.knowledge import KnowledgeService
from server.director.models import Detail, ExchangeError
from server.director.service import DirectorService, NotInstalledValidator, PlanValidator
from server.director.store import DirectorStore, ValidationRecord, compute_validation_id
from server.director.validate.pipeline import PipelineValidator

_REQUEST_ID_HEADER = "x-request-id"

#: SPEC-LDWIRE-001 M2 -- how long a persisted ValidationReport stays resolvable by
#: validation_id. Matches the 30-minute window already established for
#: validation/context expiry elsewhere in this suite.
_VALIDATION_WINDOW_MINUTES = 30


class ContextProvider(Protocol):
    """GET context lookup seam. No console/observation wiring in the original SPEC --
    unset by default."""

    def current(self, project_id: str) -> dict[str, Any]: ...


class ExecutionProvider(Protocol):
    """GET execution lookup seam. M4 durable journal fills this."""

    def get(self, project_id: str, execution_id: str) -> dict[str, Any]: ...


class FeedbackProposalService(Protocol):
    """POST feedback-proposals storage seam. M2 fills this."""

    def propose(
        self, *, project_id: str, feedback: dict[str, Any], idempotency_key: str
    ) -> dict[str, Any]: ...


class ValidationProvider(Protocol):
    """The ValidationReport lookup seam POST .../approvals references.

    SPEC-LDCOMPILE-001 storage was not exposed over HTTP yet -- for the same reason
    as ContextProvider/ExecutionProvider, an unset provider honestly answers 503
    (module docstring)." SPEC-LDWIRE-001 M2 is the first real implementation
    (server.director.provision.StoreValidationProvider)."
    """

    def get(self, project_id: str, validation_id: str) -> ValidationRef: ...


@dataclass
class DirectorApiDeps:
    """Everything M1 wires -- real LDSTORE/LDCOMPILE services + auth material.

    context_provider/execution_provider/feedback_service are seams a later
    milestone (or an observation wiring out of this SPEC scope) fills -- M1 owns
    only the Protocol, default is None.
    """

    store: DirectorStore
    knowledge: KnowledgeService
    service: DirectorService
    registry: CredentialRegistry
    secrets: PairingSecretStore
    #: The validator POST .../validations no-store re-check path uses. None means
    #: NotInstalledValidator(). Also doubles, since SPEC-LDWIRE-001 M4, as the
    #: "PipelineValidator is installed" signal PUT plan reads -- the actual
    #: instance stored here is discarded per-request in favour of a freshly
    #: context-aware one (design.md section "da").
    validator: PlanValidator | None = None
    allowed_hosts: tuple[str, ...] = field(default_factory=lambda: DEFAULT_HOST_ALLOWLIST)
    trusted_origins: tuple[str, ...] = ()
    context_provider: ContextProvider | None = None
    execution_provider: ExecutionProvider | None = None
    feedback_service: FeedbackProposalService | None = None
    #: M2 (SPEC-LDRECV-001) human approve/reject overlay. Default is a fresh
    #: in-memory registry -- durable storage is M4s job (approvals.py module
    #: docstring).
    approvals: ApprovalRegistry = field(default_factory=ApprovalRegistry)
    #: ValidationReport lookup seam POST .../approvals references. 503 when unset.
    validation_provider: ValidationProvider | None = None
    #: M5 (SPEC-LDRECV-001) pre-apply re-check + durable journal commit +
    #: SafetyGate connection coordinator. 503 on POST .../apply when unset.
    apply_coordinator: ApplyCoordinator | None = None
    #: M4/M5 durable execution journal -- records bundle-send results after apply.
    execution_journal: ExecutionJournal | None = None
    #: The real console-send seam (execution.py module docstring -- this SPEC does
    #: not build an implementation). Unset means apply commits the journal + gate
    #: connection only and skips bundle send (partial wiring -- this layers
    #: console-gate boundary, spec.md section 5).
    bundle_sender: BundleSender | None = None
    #: Operator-intervention (programmer change) detection seam. Unset means no
    #: intervention detection while proceeding.
    interference_detector: InterferenceDetector | None = None


def _request_id(request: Request) -> str:
    return request.headers.get(_REQUEST_ID_HEADER, "unknown")


def _error_response(error: ExchangeError, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=error.http_status, content=error.to_envelope(_request_id(request))
    )


def _identity_mismatch(field_name: str, path_value: str, body_value: str) -> ExchangeError:
    """Contract Section 3 -- a path/body project or plan ID mismatch is 422 IDENTITY_MISMATCH."""
    return ExchangeError(
        "IDENTITY_MISMATCH",
        422,
        f"path {field_name}({path_value!r}) does not match body {field_name}({body_value!r}).",
        (Detail(f"/{field_name}", "path/body identity mismatch"),),
    )


def _dependency_unavailable(what: str) -> ExchangeError:
    return ExchangeError("DEPENDENCY_UNAVAILABLE", 503, f"{what} is not wired yet.")


def _build_request_validator(deps: DirectorApiDeps, project_id: str) -> PlanValidator:
    """SPEC-LDWIRE-001 M4 (design.md section "da" alternative A) -- reconstructs a
    context-aware PipelineValidator per request instead of using a fixed
    construction-time instance.

    deps.validator not being None is read ONLY as the "PipelineValidator is
    installed" signal -- whatever context (if any) that stored instance itself was
    built with is discarded here in favour of deps.context_provider CURRENT
    snapshot, so a stale construction-time context can never outlive a real
    context reissue (REQ-LDWIRE-005).
    """
    if deps.validator is None:
        return NotInstalledValidator()
    context_snapshot = deps.context_provider.current(project_id) if deps.context_provider else None
    return PipelineValidator(context=context_snapshot)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validation_expiry(created_at: str) -> str:
    moment = datetime.fromisoformat(created_at)
    return (moment + timedelta(minutes=_VALIDATION_WINDOW_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_director_router(deps: DirectorApiDeps) -> APIRouter:
    """Wires contract Section 3 common routes behind auth.

    The router carries the project path prefix
    (/api/director/v1/projects/{project_id}) under contract Section 3 six-route
    shape. Every handler goes through auth.authenticate first, and a failure
    becomes an ExchangeError -> _error_response with the contract Section 3
    ErrorEnvelope shape.
    """

    router = APIRouter(prefix="/api/director/v1/projects/{project_id}")

    # Every handler is async def -- deps.store (DirectorStore) pins its
    # sqlite3.connect() to its construction thread (server/director/store.py,
    # PRESERVE, do not modify). A def handler would let FastAPI send it to a
    # threadpool (run_in_threadpool), running on a different thread per request --
    # breaking that constraint. Measured: sqlite3.ProgrammingError: SQLite objects
    # created in a thread can only be used in that same thread. async def runs
    # directly on the event-loop thread, so as long as deps is constructed on that
    # same thread (app startup/lifespan) this constraint holds -- the caller
    # (serve.py composition) must not construct DirectorStore off the event-loop
    # thread (a separate thread/process pool).

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
        """Contract Section 4 -- only the human APP route issues an approval
        (REQ-LDPLUGIN-020 M2).

        An MCP credential is already rejected SCOPE_DENIED at the auth.authenticate
        step (plan:approve is human-only scope), never reaching this handler body.
        A general chat/WS approval boolean (e.g. approved true) is rejected
        SCHEMA_INVALID structurally by the required-field check below.
        """
        try:
            credential = _require_credential(request, scope="plan:approve")

            validation_id = body.get("validation_id")
            plan_digest = body.get("plan_digest")
            context_digest = body.get("context_digest")
            compiled_digest = body.get("compiled_digest")
            idempotency_key = body.get("idempotency_key")
            required_ok = all(
                isinstance(value, str) and value
                for value in (
                    validation_id,
                    plan_digest,
                    context_digest,
                    compiled_digest,
                    idempotency_key,
                )
            )
            if not required_ok:
                message = (
                    "validation_id/plan_digest/context_digest/compiled_digest/"
                    "idempotency_key are all required."
                )
                raise ExchangeError(
                    "SCHEMA_INVALID",
                    422,
                    message,
                    (Detail("", "missing approval fields -- not a director approval"),),
                )

            if deps.validation_provider is None or deps.context_provider is None:
                raise _dependency_unavailable("validation/context provider")

            validation = deps.validation_provider.get(project_id, str(validation_id))
            context_snapshot = deps.context_provider.current(project_id)
            context = ContextRef.from_snapshot(context_snapshot)

            approval_operation = (
                f"POST /api/director/v1/projects/{project_id}/plans/{plan_id}/"
                f"revisions/{revision}/approvals"
            )
            binding = deps.approvals.approve(
                store=deps.store,
                project_id=project_id,
                plan_id=plan_id,
                revision=revision,
                principal_id=credential.principal_id,
                validation=validation,
                context=context,
                body=body,
                operation=approval_operation,
            )
            record = deps.store.get(project_id=project_id, plan_id=plan_id, revision=revision)
            approval_record = dict(
                plan=record.plan,
                revision=record.revision,
                state="approved",
                plan_digest=record.plan_digest,
            )
            approval_content = dict(approval=binding.as_dict(), record=approval_record)
            return JSONResponse(status_code=201, content=approval_content)
        except ExchangeError as error:
            return _error_response(error, request)

    @router.post("/plans/{plan_id}/revisions/{revision}/rejections")
    async def post_rejection(
        project_id: str, plan_id: str, revision: int, body: dict[str, Any], request: Request
    ):
        """Contract Section 4 -- only the human APP route records a rejection
        (REQ-LDPLUGIN-020 M2)."""
        try:
            credential = _require_credential(request, scope="plan:reject")
            reason = body.get("reason")
            idempotency_key = body.get("idempotency_key")
            if not isinstance(reason, str) or not isinstance(idempotency_key, str):
                raise ExchangeError(
                    "SCHEMA_INVALID",
                    422,
                    "reason/idempotency_key are required.",
                    (Detail("", "missing reason/idempotency_key"),),
                )
            rejection_operation = (
                f"POST /api/director/v1/projects/{project_id}/plans/{plan_id}/"
                f"revisions/{revision}/rejections"
            )
            result = deps.approvals.reject(
                store=deps.store,
                project_id=project_id,
                plan_id=plan_id,
                revision=revision,
                reason=reason,
                idempotency_key=idempotency_key,
                principal_id=credential.principal_id,
                operation=rejection_operation,
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
                    "SCHEMA_INVALID", 422, "plan must be an object.", (Detail("/plan", ""),)
                )
            if str(plan.get("project_id")) != project_id:
                raise _identity_mismatch("project_id", project_id, str(plan.get("project_id")))
            # SPEC-LDWIRE-001 M4 -- a context-aware PipelineValidator reconstructed
            # per request (design.md section "da" alternative A). This is the
            # no-store re-check path (PUT plan / DirectorService.submit already
            # performs validation as part of storing -- see below).
            validator = _build_request_validator(deps, project_id)
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
                    "SCHEMA_INVALID", 422, "plan must be an object.", (Detail("/plan", ""),)
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
                    "expected_revision/idempotency_key are required.",
                    (Detail("", "missing expected_revision/idempotency_key"),),
                )
            # SPEC-LDWIRE-001 M4 -- deps.service is NOT used directly any more:
            # its validator is fixed at DirectorApiDeps construction time, which
            # would validate every request against whatever context existed at
            # boot (design.md section "da"). A fresh DirectorService sharing the
            # SAME deps.store is constructed per request instead, carrying a
            # freshly context-aware validator -- service.py itself is untouched.
            validator = _build_request_validator(deps, project_id)
            request_service = DirectorService(deps.store, validator=validator)
            put_operation = f"PUT /api/director/v1/projects/{project_id}/plans/{plan_id}"
            result = request_service.submit(
                plan=plan,
                expected_revision=expected_revision,
                principal_id=credential.principal_id,
                operation=put_operation,
                idempotency_key=idempotency_key,
            )

            result_validation = dict(result.validation)
            # SPEC-LDWIRE-001 M2 -- persists the ValidationReport so a later
            # POST .../approvals can resolve it by validation_id (REQ-LDWIRE-006).
            if deps.validation_provider is not None:
                context_snapshot = (
                    deps.context_provider.current(project_id) if deps.context_provider else None
                )
                context_digest = str(context_snapshot["context_digest"]) if context_snapshot else ""
                validation_id = compute_validation_id(
                    plan_digest=result.record.plan_digest,
                    revision=result.record.revision,
                    context_digest=context_digest,
                )
                compiled = dict(result.validation.get("compiled") or dict(available=False))
                created_at = _now_iso()
                validation_record = ValidationRecord(
                    validation_id=validation_id,
                    project_id=project_id,
                    plan_id=plan_id,
                    plan_digest=result.record.plan_digest,
                    context_digest=context_digest,
                    compiled_digest=canonical_digest(compiled),
                    outcome=str(result.validation.get("outcome", "")),
                    diagnostics=list(result.validation.get("diagnostics") or []),
                    compiled=compiled,
                    created_at=created_at,
                    expires_at=_validation_expiry(created_at),
                )
                deps.store.save_validation(validation_record)
                result_validation["validation_id"] = validation_id

            record_body = dict(
                plan=result.record.plan,
                revision=result.record.revision,
                state=result.state,
                plan_digest=result.record.plan_digest,
            )
            return dict(record=record_body, validation=result_validation)
        except ExchangeError as error:
            return _error_response(error, request)

    @router.post("/plans/{plan_id}/revisions/{revision}/apply")
    async def post_apply(
        project_id: str, plan_id: str, revision: int, body: dict[str, Any], request: Request
    ):
        """Contract Section 4 -- apply connects to SafetyGate only after passing the
        in-lock re-check (REQ-LDPLUGIN-021; REQ-LDPLUGIN-024 failure classification
        is server.director.execution.execute_bundles job).

        An MCP credential is already rejected SCOPE_DENIED at the auth.authenticate
        step (plan:apply is human-only scope), never reaching this handler body.

        SPEC-LDSEND-001 REQ-LDSEND-015 -- the apply decision flow (ApplyCoordinator.
        apply() -> execute_bundles() -> session bind/release) was extracted to
        server.director.execution.run_director_apply. This handler only calls that
        function and wraps its return tuple as a JSONResponse -- response status,
        body, and journal record are byte-identical to before the extraction.
        """
        try:
            credential = _require_credential(request, scope="plan:apply")

            if deps.apply_coordinator is None or deps.context_provider is None:
                raise _dependency_unavailable("apply coordinator/context provider")

            context_snapshot = deps.context_provider.current(project_id)
            apply_operation = (
                f"POST /api/director/v1/projects/{project_id}/plans/{plan_id}/"
                f"revisions/{revision}/apply"
            )
            response_body, response_status = run_director_apply(
                coordinator=deps.apply_coordinator,
                journal=deps.execution_journal,
                bundle_sender=deps.bundle_sender,
                interference=deps.interference_detector,
                project_id=project_id,
                plan_id=plan_id,
                revision=revision,
                principal_id=credential.principal_id,
                operation=apply_operation,
                current_context_digest=str(context_snapshot["context_digest"]),
                body=body,
            )
            return JSONResponse(status_code=response_status, content=response_body)
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
                    "feedback/idempotency_key are required.",
                    (Detail("", "missing feedback/idempotency_key"),),
                )
            return deps.feedback_service.propose(
                project_id=project_id, feedback=feedback, idempotency_key=idempotency_key
            )
        except ExchangeError as error:
            return _error_response(error, request)

    return router
