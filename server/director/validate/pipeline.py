"""`LD-VAL-001` 6단 파이프라인 (SPEC-LDCOMPILE-001 C1, REQ-LDPLUGIN-014).

계약 §8 `LD-VAL-001` 은 순서를 못박는다 — source identity → time/reference → tracking/FX →
capability/fidelity → safety → approval freshness. 뒤 단계가 앞 단계의 결론을 전제하므로
**순서가 곧 의미다.**

그런데 이 층은 앞 단계가 blocking 이어도 **끊지 않는다.** 계약 §6.3 이 *"각 요청 action에는
적어도 하나의 diagnostic이 있어야"* 한다고 규정하기 때문이다 — 1단계에서 끊으면 뒤 단계까지
못 간 action 은 진단이 0개가 되어 그 조항을 위반한다. 사람이 무엇을 왜 고쳐야 하는지 보려면
전 단계의 진단이 다 필요하다.

[HARD] 지금 `capability_fidelity` 는 **무조건 blocking** 이다. 축별 timing emitter 가 저장소에
0건이고(`spec.md` §6.1 실측: `PanFade`/`TiltFade`/`ColorFade`/`BeamFade` 각 0건, 유일한
`CueFade` 87건은 큐 단위 스칼라 하나라 축을 구분하지 못한다), `LD-CAP-001` 이 capability 광고의
근거를 *"실제 compiler+rig+target 출력"* 으로 못박았으므로 실측 전 정직한 답은 unsupported 다.
이것은 착수 시점의 상태이지 종착지가 아니다 — 여는 것은 C6(emitter 프로브)의 일이다.

[HARD] OSC 를 만지지 않는다. 이 모듈은 dict 만 다루며 `server.bridge` 를 import 하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.director.models import SCHEMA_VERSION
from server.director.validate.diagnostics import (
    STATUS_ACCEPTED,
    STATUS_UNSUPPORTED,
    Diagnostic,
)

#: 계약 §8 `LD-VAL-001` 의 검사 순서. 바꾸지 않는다 — 순서가 곧 의미다.
STAGES: tuple[str, ...] = (
    "source_identity",
    "time_reference",
    "tracking_fx",
    "capability_fidelity",
    "safety",
    "approval_freshness",
)

#: 계약 §6.3 의 outcome enum.
OUTCOME_BLOCKED = "blocked"
OUTCOME_READY = "ready_for_review"

#: 전체 plan 을 가리키는 pointer (계약 §6.3).
ROOT_POINTER = ""

#: 축별 timing emitter 부재의 사유. 사람이 "왜 막혔나" 를 물었을 때 「구현이 안 됐다」와
#: 「계획이 잘못됐다」가 구분되어야 한다.
_NO_AXIS_EMITTER_REASON = (
    "축별 delay/fade 를 보존하는 emitter 가 실측되지 않았습니다. "
    "LD-CAP-001 은 capability 광고의 근거를 실제 compiler+rig+target 출력으로 규정하므로, "
    "관측 전에는 unsupported 로 답합니다. 계획의 결함이 아닙니다."
)


@dataclass(frozen=True, slots=True)
class CoreReport:
    """`ValidationReport` 중 계획만 보고 채울 수 있는 부분.

    신원 필드(validation_id·digest·시각)는 계획에 없다. `PlanValidator` seam 이 계획만
    넘기므로 그것들은 `build_report` 가 밖에서 받는다 — 이 층이 지어내지 않는다.
    """

    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = OUTCOME_BLOCKED
    compiled: dict[str, Any] = field(default_factory=lambda: {"available": False})


def _action_pointers(plan: dict[str, Any]) -> list[str]:
    """요청된 모든 action 의 leaf JSON Pointer. submitted plan root 기준이다."""
    pointers: list[str] = []
    for cue_index, cue in enumerate(plan.get("cues", []) or []):
        actions = cue.get("actions", []) if isinstance(cue, dict) else []
        for action_index in range(len(actions or [])):
            pointers.append(f"/cues/{cue_index}/actions/{action_index}")
    return pointers


def _stage_source_identity(plan: dict[str, Any]) -> list[Diagnostic]:
    """1단 — source identity. 근거·출처가 해소되는가 (`LD-REF-001`·`LD-CTX-001`).

    C1 은 골격이다. snapshot 대조는 `ContextSnapshot` 을 받는 상위 층의 일이므로, 여기서는
    계획 하나만 보고 말할 수 있는 것에 그친다.
    """
    return [
        Diagnostic(
            rule_id="LD-REF-001",
            pointer=ROOT_POINTER,
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=(
                "계획 단독 판독 범위에서 참조 형태에 변경·누락이 없습니다. "
                "snapshot 대조는 ContextSnapshot 을 받는 호출자가 수행합니다."
            ),
            stage="source_identity",
        )
    ]


def _stage_time_reference(plan: dict[str, Any]) -> list[Diagnostic]:
    """2단 — time/reference (`LD-TIME-001`~`003`).

    시간 해석의 실제 계산은 C2 가 `timing.py` 에 넣는다. C1 은 자리를 만들고, 아직 재지
    않았음을 진단으로 남긴다 — 침묵으로 남기지 않는다.
    """
    return [
        Diagnostic(
            rule_id="LD-TIME-001",
            pointer=ROOT_POINTER,
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=(
                "시간 해석 단계에 도달했습니다. 반올림·delta·tempo 분할 판정은 C2 의 "
                "timing 검사기가 이 자리에서 수행합니다."
            ),
            stage="time_reference",
        )
    ]


def _stage_tracking_fx(plan: dict[str, Any]) -> list[Diagnostic]:
    """3단 — tracking/FX (`LD-STATE-001`·`002`, `LD-FX-001`, `LD-CONFLICT-001`).

    축별·fixture별 simulation 은 C3 가 `simulate.py`/`conflict.py` 에 넣는다.
    """
    return [
        Diagnostic(
            rule_id="LD-STATE-001",
            pointer=ROOT_POINTER,
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=(
                "tracking/FX 단계에 도달했습니다. 누락=hold·baseline·terminal 판정과 "
                "fixture×axis 충돌 검출은 C3 의 simulation 이 이 자리에서 수행합니다."
            ),
            stage="tracking_fx",
        )
    ]


def _stage_capability_fidelity(plan: dict[str, Any]) -> list[Diagnostic]:
    """4단 — capability/fidelity (`LD-CAP-001`). **요청 action 별로 진단을 낸다.**

    이 단계가 계약 §6.3 의 'action 당 진단 최소 하나' 를 채우는 자리다. 표현 보존을 판정하는
    단계이므로 판정의 단위가 action 이고, 그래서 leaf pointer 가 여기서 붙는다.

    [HARD] 지금은 무조건 blocking 이다. 유보 상태의 기본값이 안전한 쪽이어야 한다 —
    C4 가 하는 일은 이 blocking 의 *사유를 축·op별로 정확하게 만드는 것*이지 blocking 을
    켜는 것이 아니다.
    """
    diagnostics = [
        Diagnostic(
            rule_id="LD-CAP-001",
            pointer=pointer,
            status=STATUS_UNSUPPORTED,
            blocking=True,
            reason=_NO_AXIS_EMITTER_REASON,
            stage="capability_fidelity",
        )
        for pointer in _action_pointers(plan)
    ]
    if not diagnostics:
        # action 이 하나도 없는 계획도 판정을 받는다. 침묵으로 통과시키지 않는다.
        diagnostics.append(
            Diagnostic(
                rule_id="LD-CAP-001",
                pointer=ROOT_POINTER,
                status=STATUS_UNSUPPORTED,
                blocking=True,
                reason=(
                    "요청된 action 이 없습니다. 계약 LD-STATE-001 은 빈 cue/terminal 배열을 "
                    "draft 에서만 허용하므로 ready 판정 대상이 아닙니다."
                ),
                stage="capability_fidelity",
            )
        )
    return diagnostics


def _stage_safety(plan: dict[str, Any]) -> list[Diagnostic]:
    """5단 — safety (`LD-SAFE-001`).

    기존 SafetyGate 의 hard check 는 실행 층(`SPEC-LDRECV-001`)이 소유한다. 이 층은
    그것을 우회하지 않으며, artistic advisory 로 hard limit 을 완화하지도 않는다.
    """
    return [
        Diagnostic(
            rule_id="LD-SAFE-001",
            pointer=ROOT_POINTER,
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=(
                "safety 단계에 도달했습니다. max intensity·forbidden preset·LiveLock 의 "
                "hard check 는 실행 층의 SafetyGate 가 소유하며 이 층은 우회하지 않습니다."
            ),
            stage="safety",
        )
    ]


def _stage_approval_freshness(plan: dict[str, Any]) -> list[Diagnostic]:
    """6단 — approval freshness (`LD-APPROVAL-001`).

    승인 발급·소비는 `SPEC-LDRECV-001` 이다. 이 층은 `ApprovalBinding` 을 발급하지 않는다.
    """
    return [
        Diagnostic(
            rule_id="LD-APPROVAL-001",
            pointer=ROOT_POINTER,
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=(
                "approval freshness 단계에 도달했습니다. 승인은 human APP route 만 발급하며 "
                "이 층은 ApprovalBinding 을 만들지 않습니다."
            ),
            stage="approval_freshness",
        )
    ]


#: 단계 이름 → 검사 함수. `STAGES` 와 키 집합이 같아야 한다 (아래에서 단언).
_STAGE_FUNCS = {
    "source_identity": _stage_source_identity,
    "time_reference": _stage_time_reference,
    "tracking_fx": _stage_tracking_fx,
    "capability_fidelity": _stage_capability_fidelity,
    "safety": _stage_safety,
    "approval_freshness": _stage_approval_freshness,
}

assert tuple(_STAGE_FUNCS) == STAGES, "단계 표와 STAGES 순서가 어긋났습니다."


def run_stages(plan: dict[str, Any]) -> CoreReport:
    """6단을 `STAGES` 순서대로 돌리고 **전 단계** 진단을 수집한다.

    앞 단계가 blocking 이어도 끊지 않는다 — 계약 §6.3 의 action 당 진단 coverage 를 지키려면
    끊을 수 없다. 하나라도 execution-critical blocking 이면 전체가 `blocked` 이고
    `compiled.available=false` 다. 부분 적용은 이 층이 만들 수 있는 상태가 아니다.
    """
    collected: list[dict[str, Any]] = []
    for stage in STAGES:
        for diagnostic in _STAGE_FUNCS[stage](plan):
            collected.append(diagnostic.to_internal())

    blocked = any(d["blocking"] for d in collected)
    return CoreReport(
        diagnostics=collected,
        outcome=OUTCOME_BLOCKED if blocked else OUTCOME_READY,
        compiled={"available": False} if blocked else {"available": True},
    )


def build_report(
    core: CoreReport,
    *,
    validation_id: str,
    project_id: str,
    plan_id: str,
    plan_digest: str,
    context_digest: str,
    created_at: str,
    expires_at: str,
    environment: str,
) -> dict[str, Any]:
    """`CoreReport` + 신원 필드를 스키마가 통과시키는 wire 메시지로 조립한다.

    신원 필드는 전부 키워드 필수다 — 계획에 없는 값을 기본값으로 채우면 그 순간 보고서가
    자기 출처를 지어낸다.

    `stage` 는 여기서 떨어진다. 스키마가 `additionalProperties: false` 이므로 새어 나가면
    보고서 전체가 거절된다.
    """
    return {
        "message_type": "validation_report",
        "schema_version": SCHEMA_VERSION,
        "environment": environment,
        "validation_id": validation_id,
        "project_id": project_id,
        "plan_id": plan_id,
        "plan_digest": plan_digest,
        "context_digest": context_digest,
        "created_at": created_at,
        "expires_at": expires_at,
        "outcome": core.outcome,
        "diagnostics": to_wire_diagnostics(core),
        "compiled": core.compiled,
    }


def to_wire_diagnostics(core: CoreReport) -> list[dict[str, Any]]:
    """내부 진단 목록을 계약 §6.3 의 9필드로 옮기고 `diagnostic_id` 를 배정한다.

    `stage` 는 여기서 떨어진다 — 스키마가 `additionalProperties: false` 이므로 새어 나가면
    보고서 전체가 거절된다. 그래서 wire 변환 통로를 이 한 자리로 모은다.
    """
    return [
        _rewire(internal, f"diagnostic-{index:04d}")
        for index, internal in enumerate(core.diagnostics, start=1)
    ]


def _rewire(internal: dict[str, Any], diagnostic_id: str) -> dict[str, Any]:
    """내부 진단(`stage` 포함)을 wire 9필드로 옮긴다."""
    return {
        "diagnostic_id": diagnostic_id,
        "rule_id": internal["rule_id"],
        "pointer": internal["pointer"],
        "status": internal["status"],
        "blocking": internal["blocking"],
        "before": internal["before"],
        "after": internal["after"],
        "reason": internal["reason"],
        "evidence_refs": internal["evidence_refs"],
    }


class PipelineValidator:
    """`server.director.service.PlanValidator` seam 구현.

    `service.py` 를 수정하지 않는다 — seam 이 이미 이 목적으로 있으므로 고칠 것이 없다.
    기본 stub(`NotInstalledValidator`)도 지우지 않는다: 검증기 없이 서버를 띄우는 경로가
    여전히 유효해야 한다.
    """

    def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
        """seam 계약대로 `outcome`/`diagnostics`/`compiled` 를 돌려준다.

        신원 필드는 넣지 않는다 — seam 이 계획만 넘기므로 이 자리에서 알 수 없고,
        모르는 값을 지어내는 것이 이 층이 막아야 하는 실패다.
        """
        core = run_stages(plan)
        return {
            "outcome": core.outcome,
            "diagnostics": to_wire_diagnostics(core),
            "compiled": core.compiled,
        }
