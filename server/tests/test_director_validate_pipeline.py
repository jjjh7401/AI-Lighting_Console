"""C1 검증 골격 — `LD-VAL-001` 6단 순서와 진단 형태 (SPEC-LDCOMPILE-001, REQ-LDPLUGIN-014).

이 시험이 고정하는 것은 **판정의 형태**다. 무엇이 좋은 조명인가가 아니라, 요청한 것이
보존되는지 답할 때 그 답이 어떤 모양으로 나오는가다.

계약 §6.3 이 한 조항으로 이 층의 성격을 정한다 — *"각 요청 action에는 적어도 하나의
diagnostic이 있어야 하고"*. 이 조항 때문에 1단계 blocking 에서 파이프라인을 끊을 수 없다:
끊으면 뒤 단계까지 못 간 action 은 진단이 0개가 되어 조항을 위반한다. 그래서 전 단계를
수집한다.

콘솔 무접촉 · OSC 무접촉 — 순수 함수와 dict 만 다룬다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server.director.models import ExchangeError, parse_exchange
from server.director.service import OUTCOME_READY, STATE_NEEDS_REVISION
from server.director.validate.diagnostics import (
    STATUS_ACCEPTED,
    STATUS_UNSUPPORTED,
    absent,
    present,
)
from server.director.validate.pipeline import (
    STAGES,
    PipelineValidator,
    build_report,
    run_stages,
)

#: 우산 계약 §11 의 합성 예제. 양성 대조군의 출처다.
_EXAMPLES = (
    Path(__file__).resolve().parents[2] / ".moai" / "specs" / "SPEC-LDPLUGIN-001" / "examples"
)


def _load(name: str) -> dict[str, Any]:
    return json.loads((_EXAMPLES / name).read_text(encoding="utf-8"))


def _identity() -> dict[str, str]:
    """`build_report` 가 계획에서 알 수 없는 신원 필드. seam 이 계획만 넘기므로 밖에서 온다."""
    return {
        "validation_id": "validation-test-001",
        "project_id": "project-synthetic",
        "plan_id": "plan-synthetic-song",
        "plan_digest": "sha256:" + "0" * 64,
        "context_digest": "sha256:" + "1" * 64,
        "created_at": "2026-09-15T00:00:00Z",
        "expires_at": "2026-09-15T00:10:00Z",
    }


def _minimal_plan(action_count: int = 3) -> dict[str, Any]:
    """cue 하나에 action 여럿. pointer 계산과 개수 대조에만 쓴다."""
    return {
        "plan_id": "plan-min",
        "cues": [
            {
                "cue_id": "cue-min",
                "at_ms": 0,
                "actions": [
                    {
                        "action_id": f"action-{i:03d}",
                        "op": "intensity_set",
                        "group_id": "group-front",
                        "value_pct": 50,
                    }
                    for i in range(action_count)
                ],
            }
        ],
    }


# ── 계기 검정: 양성 대조군을 먼저 쏜다 ────────────────────────────────────────
# 내 시험 장치가 스키마를 실제로 판정할 수 있는지부터 확인한다. 이것이 실패하면
# 뒤의 실패는 내 코드의 결함이 아니라 장치의 결함이다.


def test_shipped_example_passes_schema() -> None:
    """계약 §11 의 `validation.json` 이 `parse_exchange` 를 통과한다 (양성 대조)."""
    raw = (_EXAMPLES / "validation.json").read_bytes()
    payload = parse_exchange(raw, environment="synthetic")
    assert payload["outcome"] == "ready_for_review"


def test_schema_rejects_a_report_missing_required_field() -> None:
    """필수 필드를 뺀 보고서는 거절된다 (음성 대조 — 장치가 아무거나 통과시키지 않는다).

    거절 **사유**를 단언한다. `Exception` 만 보면 스키마가 아닌 다른 이유(오타·JSON 파싱
    실패)로 거절돼도 이 시험이 통과해버리고, 그러면 참 사유가 안 보인다.
    """
    payload = _load("validation.json")
    del payload["compiled"]
    with pytest.raises(ExchangeError) as caught:
        parse_exchange(json.dumps(payload).encode("utf-8"), environment="synthetic")
    assert caught.value.code == "SCHEMA_INVALID"


# ── LD-VAL-001 6단 순서 ──────────────────────────────────────────────────────


def test_stage_order_is_the_contract_order() -> None:
    """계약 §8 `LD-VAL-001` 이 정한 순서 그대로다. 순서가 곧 의미다."""
    assert STAGES == (
        "source_identity",
        "time_reference",
        "tracking_fx",
        "capability_fidelity",
        "safety",
        "approval_freshness",
    )


def test_all_stages_run_even_when_an_early_stage_blocks() -> None:
    """앞 단계가 blocking 이어도 뒤 단계가 돈다.

    계약 §6.3 의 'action당 진단 최소 하나' 를 지키려면 끊을 수 없다.
    """
    core = run_stages(_minimal_plan())
    stages_seen = {d["stage"] for d in core.diagnostics}
    assert stages_seen == set(STAGES)


# ── 진단 coverage (계약 §6.3) ────────────────────────────────────────────────


@pytest.mark.parametrize("action_count", [1, 3, 8])
def test_every_requested_action_gets_at_least_one_diagnostic(action_count: int) -> None:
    core = run_stages(_minimal_plan(action_count))
    for i in range(action_count):
        pointer = f"/cues/0/actions/{i}"
        assert any(d["pointer"] == pointer for d in core.diagnostics), (
            f"action {i} 에 진단이 없다 — 계약 §6.3 위반"
        )


def test_root_diagnostic_pointer_is_empty_string() -> None:
    """`\"\"` 는 전체 plan 을 가리킨다 (계약 §6.3)."""
    core = run_stages(_minimal_plan())
    assert any(d["pointer"] == "" for d in core.diagnostics)


def test_full_example_plan_covers_all_sixty_actions() -> None:
    """계약 §11 의 실제 계획(cue 16 · action 60)에서도 coverage 가 성립한다."""
    plan = _load("plan.json")
    expected = sum(len(c.get("actions", [])) for c in plan["cues"])
    core = run_stages(plan)
    covered = {d["pointer"] for d in core.diagnostics}
    missing = [
        f"/cues/{i}/actions/{j}"
        for i, cue in enumerate(plan["cues"])
        for j in range(len(cue.get("actions", [])))
        if f"/cues/{i}/actions/{j}" not in covered
    ]
    assert not missing, f"{len(missing)}/{expected} action 에 진단이 없다"


# ── blocking 전파 ────────────────────────────────────────────────────────────


def test_capability_stage_blocks_unconditionally_for_now() -> None:
    """축별 emitter 가 0건인 상태에서 capability 는 무조건 blocking 이다.

    plan.md §2.1 — C4 를 유보하는 동안의 기본값은 안전한 쪽이어야 한다. C4 는 이
    blocking 의 *사유를 정확하게* 만드는 일이지 blocking 을 켜는 일이 아니다.
    """
    core = run_stages(_minimal_plan())
    capability = [d for d in core.diagnostics if d["stage"] == "capability_fidelity"]
    assert capability, "capability 단계 진단이 없다"
    assert all(d["blocking"] for d in capability)
    assert all(d["status"] == STATUS_UNSUPPORTED for d in capability)


def test_one_critical_blocking_makes_the_whole_plan_blocked() -> None:
    """부분 적용은 이 층이 만들 수 있는 상태가 아니다 (AC-LDPLUGIN-014)."""
    core = run_stages(_minimal_plan())
    assert core.outcome == "blocked"
    assert core.compiled == {"available": False}


def test_normal_actions_still_get_diagnostics_when_another_action_blocks() -> None:
    """정상 action 도 진단을 받는다 — blocking 이 남의 진단을 삼키지 않는다."""
    core = run_stages(_minimal_plan(4))
    for i in range(4):
        pointer = f"/cues/0/actions/{i}"
        assert any(d["pointer"] == pointer for d in core.diagnostics)


# ── 조용한 수용의 표현 ───────────────────────────────────────────────────────


def test_silent_acceptance_is_before_after_both_absent_with_a_reason() -> None:
    """조용한 수용은 진단 부재가 아니라 `present=false` 둘 + 사유다 (계약 §6.3)."""
    accepted = [
        d for d in run_stages(_minimal_plan()).diagnostics if d["status"] == STATUS_ACCEPTED
    ]
    assert accepted, "수용 진단이 하나도 없다"
    for d in accepted:
        assert d["before"] == {"present": False}
        assert d["after"] == {"present": False}
        assert d["reason"].strip(), "사유 없는 수용은 조용한 수용이다"


def test_present_helper_requires_a_value_and_absent_forbids_one() -> None:
    """`present=true` 면 value 가 반드시 있고 `false` 면 없어야 한다 (계약 §6.3)."""
    assert absent() == {"present": False}
    assert present(50) == {"present": True, "value": 50}


# ── 거절 장치를 쏴본다 — 안 쏘면 공허한지 알 수 없다 ─────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [
        (True, {"present": True, "value": True}),
        (0, {"present": True, "value": 0}),
        (-1e9, {"present": True, "value": -1e9}),
        (1e9, {"present": True, "value": 1e9}),
        ("preset-warm", {"present": True, "value": "preset-warm"}),
        (["id-a", "id-b"], {"present": True, "value": ["id-a", "id-b"]}),
        ((), {"present": True, "value": []}),
    ],
)
def test_present_accepts_the_contract_value_types(value: Any, expected: dict[str, Any]) -> None:
    """계약 §6.3 의 `value?: string|number|boolean|Id[]` 경계 안쪽."""
    assert present(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        1e9 + 1,  # 상한 바로 밖
        -1e9 - 1,  # 하한 바로 밖
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_present_rejects_numbers_outside_the_finite_range(value: float) -> None:
    """*"숫자는 finite -1e9..1e9"* — 경계 바깥을 실제로 막는다."""
    with pytest.raises(ValueError):
        present(value)


@pytest.mark.parametrize(
    "value",
    [
        {"op": "intensity_set"},  # object 전체
        [{"id": "a"}],  # Id[] 가 아닌 배열
        None,
        object(),
    ],
)
def test_present_rejects_objects_and_non_id_arrays(value: Any) -> None:
    """*"object 전체는 value로 넣지 않고 해당 leaf에 진단한다"* (계약 §6.3)."""
    with pytest.raises(ValueError):
        present(value)


def test_diagnostic_rejects_a_status_outside_the_contract_enum() -> None:
    from server.director.validate.diagnostics import Diagnostic

    with pytest.raises(ValueError):
        Diagnostic(
            rule_id="LD-CAP-001",
            pointer="",
            status="probably_fine",
            blocking=False,
            reason="사유",
            stage="safety",
        )


@pytest.mark.parametrize("reason", ["", "   ", "\n\t"])
def test_diagnostic_rejects_an_empty_reason(reason: str) -> None:
    """사유 없는 진단은 조용한 수용이다 — 만들지 못하게 막는다."""
    from server.director.validate.diagnostics import Diagnostic

    with pytest.raises(ValueError):
        Diagnostic(
            rule_id="LD-CAP-001",
            pointer="",
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=reason,
            stage="safety",
        )


def test_a_plan_with_no_actions_is_still_judged() -> None:
    """action 이 0개인 계획도 진단을 받는다. 침묵으로 통과시키지 않는다."""
    core = run_stages({"plan_id": "plan-empty", "cues": []})
    assert core.outcome == "blocked"
    assert any(d["stage"] == "capability_fidelity" and d["blocking"] for d in core.diagnostics)


# ── 왕복: 우리 출력이 스키마를 통과하는가 ────────────────────────────────────


def test_built_report_round_trips_through_parse_exchange() -> None:
    core = run_stages(_minimal_plan())
    report = build_report(core, environment="synthetic", **_identity())
    payload = parse_exchange(json.dumps(report).encode("utf-8"), environment="synthetic")
    assert payload["outcome"] == "blocked"
    assert payload["compiled"] == {"available": False}


def test_built_report_carries_the_nine_diagnostic_fields() -> None:
    """스키마의 diagnostic required 9개를 전부 채운다."""
    report = build_report(run_stages(_minimal_plan()), environment="synthetic", **_identity())
    required = {
        "diagnostic_id",
        "rule_id",
        "pointer",
        "status",
        "blocking",
        "before",
        "after",
        "reason",
        "evidence_refs",
    }
    for d in report["diagnostics"]:
        assert set(d) == required, f"필드 집합이 다르다: {set(d) ^ required}"


def test_built_report_drops_the_internal_stage_field() -> None:
    """`stage` 는 내부 추적용이다. 스키마가 `additionalProperties:false` 라 나가면 거절된다."""
    report = build_report(run_stages(_minimal_plan()), environment="synthetic", **_identity())
    assert all("stage" not in d for d in report["diagnostics"])


def test_diagnostic_ids_are_unique_within_a_report() -> None:
    report = build_report(run_stages(_minimal_plan(5)), environment="synthetic", **_identity())
    ids = [d["diagnostic_id"] for d in report["diagnostics"]]
    assert len(ids) == len(set(ids))


# ── seam: 검증기를 꽂아도 통과가 나오지 않는다 ───────────────────────────────


def test_service_seam_never_reaches_ready_while_capability_blocks() -> None:
    """`PlanValidator` seam 에 꽂았을 때 `ready_for_review` 가 나오지 않는다.

    `service.py` 는 수정하지 않는다 — seam 이 이미 그 목적으로 있다.
    """
    result = PipelineValidator().validate(_minimal_plan())
    assert result["outcome"] != OUTCOME_READY
    assert result["compiled"] == {"available": False}
    assert STATE_NEEDS_REVISION == "needs_revision"
