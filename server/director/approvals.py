"""사람 승인/거절 — `ApprovalBinding` 발급·무효화 (SPEC-LDRECV-001 M2 · REQ-LDPLUGIN-020).

이 모듈은 `POST .../approvals`·`POST .../rejections` route(`director_api.py`)가
호출하는 판정·저장을 담당한다. 계약 §4(APP human routes)·§8(LD-APPROVAL-001)·
§9.7(idempotency)이 단일 원본이다.

## human-only, director 전용

일반 chat/WS 승인 채널(`server/safety/approval.py`, `server/web/approval_bridge.py`)
과 MCP credential 은 이 모듈에 도달하지 않는다 — `director_api.py` 가 라우트
등록 시 `auth.authenticate(..., scope="plan:approve"/"plan:reject")`로 먼저 걸러
내므로(둘 다 `HUMAN_ONLY_SCOPES`), MCP credential 은 SCOPE_DENIED 로 이 모듈
진입 전에 거부된다. 일반 chat/WS 승인 boolean 은 이 모듈이 요구하는 body 형태
(validation_id·세 digest·idempotency_key)를 갖추지 못하므로 SCHEMA_INVALID 로
구조적으로 거부된다 — 계약 §4: *"body의 principal/role/approved boolean, 채팅
message, legacy WS 승인 boolean은 권한으로 인정하지 않는다."*

## plan_revisions 는 건드리지 않는다

`server/director/store.py` 의 `plan_revisions` 테이블은 INSERT-only 불변 저장소
(형제 SPEC 소유, PRESERVE)이며, `DirectorStore.submit()` 이 기록하는 `state` 는
항상 리터럴 `"submitted"` 다(검증 결과에 따른 needs_revision/ready_for_review 는
`DirectorService.submit()` 이 반환값에서만 계산하고 되쓰지 않는다 — `service.py`
실측). 그래서 승인 판정은 store 의 `state` 컬럼이 아니라, 요청이 참조하는
`ValidationReport.outcome` 을 근거로 삼는다(계약 §5: *"human approve/apply 시
blocking이면 422다"*). approved/rejected 상태 자체도 plan_revisions 행을 고치지
않고 이 모듈의 :class:`ApprovalRegistry` 오버레이에만 기록한다.

## console_id/session_id 출처 (이 SPEC 의 설계 판단)

`Credential`(auth.py)에는 `console_id` 가 없다 — credential 의 `session_id` 는
사람/plugin 세션이지 콘솔 세션이 아니다. 계약 §6.1 은 `target=
{console_id,session_id,identity_status,identity_evidence_refs,mode,destination}`
를 ContextSnapshot 의 identity 축으로 규정한다. 그래서 `ApprovalBinding` 의
`console_id`/`session_id` 는 credential 이 아니라 **current context 의
`target`** 에서 가져온다(:class:`ContextRef.from_snapshot`) — LDSTORE 의
`context.py`/`ContextObservations.target` 이 이미 이 축을 담는 자리이므로, 이
층은 그 위임 필드를 그대로 승계한다.

## durable 저장은 M4 가 한다

이 registry 는 in-memory 다 — 계획 §2 M4 행이 durable execution journal(SQLite,
`002_execution_journal.sql`)을 만들 때 승인 소비를 durable 하게 옮긴다. REQ-020
자체는 console 게이트가 아니므로(spec.md §5) M2 는 같은 process 수명 동안의
발급·무효화 판정만 책임진다.
"""

from __future__ import annotations

import secrets as _secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from server.director.digest import canonical_digest
from server.director.models import Detail, ExchangeError
from server.director.service import OUTCOME_READY
from server.director.store import DirectorStore, PlanRecord

#: 계약 §4 — `ApprovalBinding` 필드 전부(실제 나열 12개). plan.md/acceptance.md
#: 본문은 "9필드"라 세지만 계약 원문이 나열한 토큰은 12개다 — auth.py 의
#: `HUMAN_ONLY_SCOPES` 가 "6종"이라 세면서 실제로는 7개를 나열한 것과 같은
#: 문서 표기 불일치다. 이 모듈은 나열된 쪽(12개)을 승계한다.
APPROVAL_BINDING_FIELDS: tuple[str, ...] = (
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

#: 계약 §4 — 승인 만료는 생성 시각+10분과 validation/context 만료 중 가장 빠른 값.
_EXPIRY_WINDOW = timedelta(minutes=10)


def _parse_utc(value: str) -> datetime:
    """계약 §2 의 시각(끝이 ``Z``)을 datetime 으로. 문자열 비교로 대신하지 않는다
    (`context.py` `_parse_utc` 와 같은 이유 — 같은 순간의 다른 표기에서 사전순이
    시간순과 어긋난다)."""
    return datetime.fromisoformat(value)


def _format_utc(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_utc() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# ApprovalBinding
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApprovalBinding:
    """계약 §4 의 `ApprovalBinding` — 모든 필드 required."""

    approval_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    context_digest: str
    compiled_digest: str
    principal_id: str
    console_id: str
    session_id: str
    safety_policy_revision: int
    approved_at: str
    expires_at: str

    def as_dict(self) -> dict[str, Any]:
        return {field_name: getattr(self, field_name) for field_name in APPROVAL_BINDING_FIELDS}


@dataclass(frozen=True, slots=True)
class ValidationRef:
    """`POST .../approvals` body 가 참조하는 `ValidationReport` 중 이 모듈이 쓰는 값만.

    저장소 자체(`SPEC-LDCOMPILE-001` 소유)는 아직 이 코드베이스에 HTTP 로 노출되지
    않았다 — `director_api.py` 의 `ValidationProvider` seam 이 주입될 때까지는
    미배선(503)이다(M1 의 `ContextProvider`/`ExecutionProvider` 와 같은 패턴).
    """

    validation_id: str
    plan_digest: str
    context_digest: str
    compiled_digest: str
    expires_at: str
    outcome: str


@dataclass(frozen=True, slots=True)
class ContextRef:
    """current context 중 이 모듈이 쓰는 값만 — `target` 에서 console/session 을 꺼낸다."""

    context_digest: str
    expires_at: str
    console_id: str
    session_id: str
    safety_policy_revision: int

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> ContextRef:
        target = snapshot.get("target") or {}
        return cls(
            context_digest=str(snapshot["context_digest"]),
            expires_at=str(snapshot["expires_at"]),
            console_id=str(target.get("console_id", "")),
            session_id=str(target.get("session_id", "")),
            safety_policy_revision=int(snapshot["safety_policy_revision"]),
        )


def compute_expiry(*, approved_at: str, validation_expires_at: str, context_expires_at: str) -> str:
    """계약 §4 의 만료 규칙 — approved_at+10분과 두 만료 중 가장 빠른 값."""
    candidates = (
        _parse_utc(approved_at) + _EXPIRY_WINDOW,
        _parse_utc(validation_expires_at),
        _parse_utc(context_expires_at),
    )
    return _format_utc(min(candidates))


def check_validity(
    binding: ApprovalBinding,
    *,
    current_head: int,
    current_context_digest: str,
    current_compiled_digest: str,
    now: str,
) -> tuple[str, ...]:
    """무효 사유 목록. 빈 tuple 이면 유효 — `context.stale_bindings` 와 같은 관례.

    `context_digest` 하나가 compiler·target·policy 를 포함한 아홉 축 전부를
    덮으므로(`context.py` `NINE_AXES`), REQ-020 이 나열한 "context stale·
    compiler/target/policy 변경"은 이 한 비교로 함께 잡힌다.

    `current_compiled_digest` 는 apply 호출자(``ApplyCoordinator``)가 이번
    apply 요청이 적용하려는 compiled artifact 라고 주장하는 digest 값이다 —
    `current_context_digest` 와 같은 관례로, 이 함수는 recompute 하지 않고
    호출자가 이미 관측한 값을 그대로 받아 `binding.compiled_digest` 와
    동등성만 비교한다(계약 §209 — `compiled_digest` 는 `ValidationReport.
    compiled.manifest` 객체 전체의 digest 이고, 그 manifest 는 compiler_id·
    compiler_version·compiler_build_digest·target·playback 을 포함해 이 모듈이
    접근할 수 없는 필드까지 묶는다 — 그래서 여기서 bundles 등 원재료로부터
    재계산하지 않는다; `SPEC-LDRECV-001 M5 다각도 검토` 결함1+2 수정 근거).
    불일치하면 `compiled_digest_changed` 를 보탠다 — apply 가 승인된 것과 다른
    compiled artifact 로 향하고 있다는 신호다(LD-APPROVAL-001: "apply 직전
    durable human approval을 exact compiled artifact digest에 묶은 SafetyGate
    bridge에서 소비한다").
    """
    reasons: list[str] = []
    if binding.plan_revision != current_head:
        reasons.append("head_changed")
    if binding.context_digest != current_context_digest:
        reasons.append("context_changed")
    if binding.compiled_digest != current_compiled_digest:
        reasons.append("compiled_digest_changed")
    if _parse_utc(now) > _parse_utc(binding.expires_at):
        reasons.append("expired")
    return tuple(reasons)


# ---------------------------------------------------------------------------
# 오류 헬퍼
# ---------------------------------------------------------------------------


def _validation_blocked(message: str) -> ExchangeError:
    return ExchangeError("VALIDATION_BLOCKED", 422, message)


def _context_stale(message: str, pointer: str = "") -> ExchangeError:
    return ExchangeError("CONTEXT_STALE", 409, message, (Detail(pointer, "stale digest"),))


def _revision_conflict(message: str) -> ExchangeError:
    return ExchangeError("REVISION_CONFLICT", 409, message, (Detail("/revision", "superseded"),))


def _idempotency_conflict() -> ExchangeError:
    return ExchangeError(
        "IDEMPOTENCY_CONFLICT",
        409,
        "같은 idempotency_key 에 다른 요청이 들어왔습니다.",
        (Detail("", "idempotency key reused with a different request"),),
    )


def _schema_invalid(message: str, pointer: str = "") -> ExchangeError:
    return ExchangeError("SCHEMA_INVALID", 422, message, (Detail(pointer, ""),))


# ---------------------------------------------------------------------------
# ApprovalRegistry
# ---------------------------------------------------------------------------


class ApprovalRegistry:
    """이 층이 소유하는 승인/거절 오버레이. process 수명 동안만 유지된다(모듈
    docstring "durable 저장은 M4 가 한다" 참고)."""

    def __init__(self) -> None:
        self._approvals: dict[str, ApprovalBinding] = {}
        self._latest_by_plan: dict[tuple[str, str], str] = {}
        self._idempotency: dict[tuple[str, str, str], tuple[str, Any]] = {}

    # ------------------------------------------------------------ 조회

    def get(self, approval_id: str) -> ApprovalBinding | None:
        return self._approvals.get(approval_id)

    def latest_for(self, *, project_id: str, plan_id: str) -> ApprovalBinding | None:
        approval_id = self._latest_by_plan.get((project_id, plan_id))
        return None if approval_id is None else self._approvals.get(approval_id)

    # ------------------------------------------------------------ idempotency (계약 §9.7)

    @staticmethod
    def _fingerprint(
        *, operation: str, project_id: str, principal_id: str, request: Mapping[str, Any]
    ) -> str:
        return canonical_digest(
            {
                "operation": operation,
                "project_id": project_id,
                "principal_id": principal_id,
                "request": dict(request),
            }
        )

    def _replay_or_none(
        self,
        *,
        project_id: str,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        fingerprint: str,
    ) -> Any | None:
        key = (project_id, principal_id, f"{operation}:{idempotency_key}")
        existing = self._idempotency.get(key)
        if existing is None:
            return None
        stored_fingerprint, result = existing
        if stored_fingerprint != fingerprint:
            raise _idempotency_conflict()
        return result

    def _remember(
        self,
        *,
        project_id: str,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        fingerprint: str,
        result: Any,
    ) -> None:
        key = (project_id, principal_id, f"{operation}:{idempotency_key}")
        self._idempotency[key] = (fingerprint, result)

    # ------------------------------------------------------------ 승인

    def approve(
        self,
        *,
        store: DirectorStore,
        project_id: str,
        plan_id: str,
        revision: int,
        principal_id: str,
        validation: ValidationRef,
        context: ContextRef,
        body: Mapping[str, Any],
        operation: str,
        approved_at: str | None = None,
        approval_id: str | None = None,
    ) -> ApprovalBinding:
        """`POST .../approvals` 판정. 성공하면 새 :class:`ApprovalBinding` 을 돌려준다.

        Raises:
            ExchangeError: ``VALIDATION_BLOCKED`` (참조된 validation 이 blocking),
                ``CONTEXT_STALE`` (body 의 digest 가 현재 record/context/validation
                과 어긋남 또는 만료), ``REVISION_CONFLICT`` (요청한 revision 이 더
                이상 head 가 아님), ``IDEMPOTENCY_CONFLICT``.
        """
        idempotency_key = body.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise _schema_invalid("idempotency_key 가 필요합니다.", "/idempotency_key")

        fingerprint = self._fingerprint(
            operation=operation,
            project_id=project_id,
            principal_id=principal_id,
            request={k: v for k, v in body.items() if k != "idempotency_key"},
        )
        replayed = self._replay_or_none(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed

        record: PlanRecord = store.get(project_id=project_id, plan_id=plan_id, revision=revision)

        head = store.head_revision(project_id=project_id, plan_id=plan_id)
        if revision != head:
            raise _revision_conflict(
                f"revision {revision} 은 더 이상 head({head}) 가 아닙니다 — superseded."
            )

        if validation.outcome != OUTCOME_READY:
            raise _validation_blocked(
                f"참조된 validation({validation.validation_id}) 이 ready_for_review 가 "
                "아닙니다 — human approve 는 blocking validation 을 승인할 수 없습니다."
            )

        moment = _format_utc(_now_utc()) if approved_at is None else approved_at

        expected = {
            "validation_id": validation.validation_id,
            "plan_digest": record.plan_digest,
            "context_digest": context.context_digest,
            "compiled_digest": validation.compiled_digest,
        }
        offending = [
            field_name for field_name, value in expected.items() if body.get(field_name) != value
        ]
        # validation 자신도 record/context 와 어긋나면 이미 stale 하다 — body 만 보면
        # 놓친다.
        if validation.plan_digest != record.plan_digest:
            offending.append("validation.plan_digest")
        if validation.context_digest != context.context_digest:
            offending.append("validation.context_digest")
        if offending:
            raise _context_stale(
                f"승인 요청의 digest 가 현재 상태와 어긋납니다: {sorted(set(offending))}"
            )

        if _parse_utc(moment) > _parse_utc(validation.expires_at):
            raise _context_stale("참조된 validation 이 이미 만료되었습니다.")
        if _parse_utc(moment) > _parse_utc(context.expires_at):
            raise _context_stale("참조된 context 가 이미 만료되었습니다.")

        expires_at = compute_expiry(
            approved_at=moment,
            validation_expires_at=validation.expires_at,
            context_expires_at=context.expires_at,
        )

        binding = ApprovalBinding(
            approval_id=approval_id or _secrets.token_urlsafe(16),
            plan_id=plan_id,
            plan_revision=record.revision,
            plan_digest=record.plan_digest,
            context_digest=context.context_digest,
            compiled_digest=validation.compiled_digest,
            principal_id=principal_id,
            console_id=context.console_id,
            session_id=context.session_id,
            safety_policy_revision=context.safety_policy_revision,
            approved_at=moment,
            expires_at=expires_at,
        )

        self._approvals[binding.approval_id] = binding
        self._latest_by_plan[(project_id, plan_id)] = binding.approval_id
        self._remember(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            result=binding,
        )
        return binding

    # ------------------------------------------------------------ 거절

    def reject(
        self,
        *,
        store: DirectorStore,
        project_id: str,
        plan_id: str,
        revision: int,
        reason: str,
        idempotency_key: str,
        operation: str,
        principal_id: str = "",
        rejected_at: str | None = None,
    ) -> dict[str, Any]:
        """`POST .../rejections` 판정. 계약 §4: 응답은 `PlanRecord`.

        `plan_revisions` 행은 고치지 않는다 — 파생 dict 의 ``state`` 만 ``"rejected"``
        로 오버레이한다.
        """
        if not reason or not reason.strip():
            raise _schema_invalid("reason 이 비어 있습니다.", "/reason")

        fingerprint = self._fingerprint(
            operation=operation,
            project_id=project_id,
            principal_id=principal_id,
            request={"reason": reason},
        )
        replayed = self._replay_or_none(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        if replayed is not None:
            return replayed

        record = store.get(project_id=project_id, plan_id=plan_id, revision=revision)
        head = store.head_revision(project_id=project_id, plan_id=plan_id)
        if revision != head:
            raise _revision_conflict(
                f"revision {revision} 은 더 이상 head({head}) 가 아닙니다 — superseded."
            )

        # 이후 apply 가 낡은 승인을 소비하지 못하게 같은 plan 의 승인을 폐기한다.
        self._latest_by_plan.pop((project_id, plan_id), None)

        result = {
            "plan": record.plan,
            "revision": record.revision,
            "state": "rejected",
            "plan_digest": record.plan_digest,
            "reason": reason,
        }
        self._remember(
            project_id=project_id,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            result=result,
        )
        return result
