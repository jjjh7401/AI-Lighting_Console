"""제출 facade — 저장과 검증을 잇는 자리 (SPEC-LDSTORE-001 M1).

계약 §3 은 `SubmitResult = {record:PlanRecord, validation:ValidationReport}` 로 정의한다.
즉 **제출이 검증을 호출한다.** 그런데 검증은 `SPEC-LDCOMPILE-001` 의 소유다. 그래서 이
모듈은 검증기를 **주입받는 seam** 으로만 두고 직접 구현하지 않는다.

계약 §10 이 그 중간 상태를 이미 정의해 두었다:

> 저장 성공 후 validation 이 blocked 면 needs_revision, 통과하면 ready_for_review.
> submitted 는 저장 후 검증이 끝나기 전 durable 내부 상태이며 처리 장애 시 재개한다.

따라서 검증기가 아직 없는 동안 도달하는 상태는 `needs_revision` 이고, `ready_for_review`
는 실제 검증기가 끼워질 때 처음 나온다.

[HARD] 기본 stub 은 **blocked 만** 답한다. 검증 없이 `ready_for_review` 를 내는 것은
계약이 막으려는 바로 그 상태다 — 검사하지 않은 계획이 사람 승인 대기열에 올라간다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from server.director.store import DirectorStore, PlanRecord

#: 계약 §10 의 PlanState 중 이 층이 다루는 둘.
STATE_NEEDS_REVISION = "needs_revision"
STATE_READY_FOR_REVIEW = "ready_for_review"

#: 계약 §6.3 의 outcome enum.
OUTCOME_BLOCKED = "blocked"
OUTCOME_READY = "ready_for_review"

#: stub 이 남기는 진단의 사유. 사람이 "왜 blocked 인가" 를 물었을 때 "검사기가 아직
#: 없다" 와 "계획이 잘못됐다" 가 구분되어야 한다.
NOT_IMPLEMENTED_REASON = "validator-not-installed"


class PlanValidator(Protocol):
    """검증기 seam. `SPEC-LDCOMPILE-001` 이 이 형태로 들어온다."""

    def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
        """`ValidationReport` 를 돌려준다. `outcome` 은 blocked 또는 ready_for_review."""
        ...


class NotInstalledValidator:
    """검증기가 아직 없음을 정직하게 표현하는 기본 구현.

    통과를 답하지 않는다. 이 클래스가 `ready_for_review` 를 내면 검증되지 않은 계획이
    승인 대기열에 오르므로, 그 경로를 아예 만들지 않는다.
    """

    def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
        return {
            "outcome": OUTCOME_BLOCKED,
            "diagnostics": [
                {
                    "pointer": "",
                    "status": "unresolved",
                    "blocking": True,
                    "reason": NOT_IMPLEMENTED_REASON,
                }
            ],
            "compiled": {"available": False},
        }


@dataclass(frozen=True, slots=True)
class SubmitResult:
    """계약 §3 의 `SubmitResult` 중 M1 이 채우는 부분."""

    record: PlanRecord
    validation: dict[str, Any]
    state: str


class DirectorService:
    """제출 경로. 저장은 `DirectorStore`, 판정은 주입된 검증기가 한다."""

    def __init__(self, store: DirectorStore, validator: PlanValidator | None = None) -> None:
        self._store = store
        self._validator: PlanValidator = validator or NotInstalledValidator()

    def submit(
        self,
        *,
        plan: dict[str, Any],
        expected_revision: int,
        principal_id: str,
        operation: str,
        idempotency_key: str,
    ) -> SubmitResult:
        """계획을 저장하고 검증 결과에 따른 상태를 함께 돌려준다.

        저장이 검증보다 먼저다 — 계약 §10 은 shape-valid 지만 실행 불가능한 draft 도
        저장하고 `needs_revision` 을 답하라고 규정한다. 저장하지 않으면 제출자가 무엇을
        고쳐야 하는지 되짚을 원본이 남지 않는다.
        """
        record = self._store.submit(
            plan=plan,
            expected_revision=expected_revision,
            principal_id=principal_id,
            operation=operation,
            idempotency_key=idempotency_key,
        )
        validation = self._validator.validate(record.plan)
        state = (
            STATE_READY_FOR_REVIEW
            if validation.get("outcome") == OUTCOME_READY
            else STATE_NEEDS_REVISION
        )
        return SubmitResult(record=record, validation=validation, state=state)
