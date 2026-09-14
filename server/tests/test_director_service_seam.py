"""검증기 seam (SPEC-LDSTORE-001 M1 · plan.md §2.0).

계약 §3 이 제출 응답에 `ValidationReport` 를 요구하지만 검증은 형제
`SPEC-LDCOMPILE-001` 의 소유다. 그 경계를 seam 으로 두었고, 이 파일은 seam 이
**통과를 사칭하지 않는지** 고정한다.

`plan.md` §2.0 의 [HARD]: stub validator 는 blocked 만 답한다. 검증 없이
`ready_for_review` 를 내면 검사하지 않은 계획이 사람 승인 대기열에 오른다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server.director.service import (
    NOT_IMPLEMENTED_REASON,
    STATE_NEEDS_REVISION,
    STATE_READY_FOR_REVIEW,
    DirectorService,
    NotInstalledValidator,
)
from server.director.store import DirectorStore

_EXAMPLES = (
    Path(__file__).resolve().parents[2] / ".moai" / "specs" / "SPEC-LDPLUGIN-001" / "examples"
)


def _plan() -> dict:
    plan = json.loads((_EXAMPLES / "plan.json").read_text(encoding="utf-8"))
    plan["base_revision"] = 0
    return plan


@pytest.fixture()
def service(tmp_path: Path) -> DirectorService:
    return DirectorService(DirectorStore(tmp_path / "director.sqlite3"))


def _submit(service: DirectorService, plan: dict, key: str = "key-0001"):
    return service.submit(
        plan=plan,
        expected_revision=plan["base_revision"],
        principal_id="principal-0001",
        operation="PUT /api/director/v1/projects/p/plans/q",
        idempotency_key=key,
    )


class TestDefaultSeamNeverFakesAPass:
    def test_stub_validator_returns_blocked(self):
        result = NotInstalledValidator().validate(_plan())
        assert result["outcome"] == "blocked"

    def test_stub_never_returns_ready_for_any_input(self):
        """어떤 입력에도 통과를 답하지 않는다 — 우연히 통과하는 경로가 없어야 한다."""
        validator = NotInstalledValidator()
        for payload in ({}, _plan(), {"cues": []}, {"anything": "at all"}):
            assert validator.validate(payload)["outcome"] == "blocked"

    def test_submitting_without_a_validator_lands_in_needs_revision(self, service: DirectorService):
        result = _submit(service, _plan())
        assert result.state == STATE_NEEDS_REVISION
        assert result.record.revision == 1

    def test_blocked_reason_distinguishes_missing_validator_from_a_bad_plan(
        self, service: DirectorService
    ):
        """ "검사기가 없다" 와 "계획이 잘못됐다" 는 사람에게 다른 뜻이다."""
        result = _submit(service, _plan())
        reasons = [item.get("reason") for item in result.validation["diagnostics"]]
        assert NOT_IMPLEMENTED_REASON in reasons

    def test_compiled_is_not_advertised_as_available(self, service: DirectorService):
        """계약 §6.3: critical blocking 이면 compiled.available=false."""
        result = _submit(service, _plan())
        assert result.validation["compiled"]["available"] is False


class TestPlanIsStoredEvenWhenBlocked:
    """계약 §10: *"shape-valid 지만 실행 불가능한 draft 도 저장하고 needs_revision 을
    반환한다."*

    저장하지 않으면 제출자가 무엇을 고쳐야 하는지 되짚을 원본이 남지 않는다.
    """

    def test_blocked_submission_still_creates_a_revision(self, service: DirectorService):
        plan = _plan()
        _submit(service, plan)
        stored = service._store.get(project_id=plan["project_id"], plan_id=plan["plan_id"])
        assert stored.revision == 1
        assert stored.plan == plan


class TestInjectedValidatorReachesReadyForReview:
    """실제 검증기가 끼워지면 ready_for_review 에 도달한다 — seam 이 살아 있다는 증거.

    이 시험이 없으면 "언제나 needs_revision" 인 구현도 위 시험들을 통과한다.
    """

    def test_a_passing_validator_yields_ready_for_review(self, tmp_path: Path):
        class PassingValidator:
            def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
                return {
                    "outcome": "ready_for_review",
                    "diagnostics": [],
                    "compiled": {"available": True},
                }

        service = DirectorService(
            DirectorStore(tmp_path / "director.sqlite3"), validator=PassingValidator()
        )
        result = _submit(service, _plan())
        assert result.state == STATE_READY_FOR_REVIEW

    def test_a_blocking_validator_yields_needs_revision(self, tmp_path: Path):
        class BlockingValidator:
            def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
                return {
                    "outcome": "blocked",
                    "diagnostics": [{"pointer": "/cues/0", "blocking": True, "reason": "nope"}],
                    "compiled": {"available": False},
                }

        service = DirectorService(
            DirectorStore(tmp_path / "director.sqlite3"), validator=BlockingValidator()
        )
        result = _submit(service, _plan())
        assert result.state == STATE_NEEDS_REVISION
