"""이펙트 인스턴스화 — 한국어 2단 보고 계층 (REQ-FXLIB-014).

`server/looks/report.py`의 미러다: 번들 조립과 **다른 관심사**라 별도 모듈에
두고, 한국어 표현 매핑은 커맨드 생성과 무관하게 여기서만 산다.

# @MX:ANCHOR: [AUTO] 성공 경로를 포함한 **모든** 보고가 `EFFECT_EVIDENCE_NOTICE`를
#   싣는다. 조건부가 아니다.
# @MX:REASON: M0가 이펙트 효과의 기계 증거 채널이 **부정**임을 측정으로 확정했다
#   (progress.md §E.2) — 저장된 큐는 `Cue → Part(childCount 0)`에서 트리가 바닥나
#   내용 있는 큐와 빈 큐가 구별되지 않고, `Phase`/`Speed`는 "property not
#   readable"이며, 픽스처 실시간 값도 읽히지 않는다. 이 문면을 지우면 사용자는
#   커맨드 접수 `ok`를 효과 확인으로 오독하고, 그 오독을 뒤에서 받아 줄 자동
#   검사는 이 SPEC에 존재하지 않는다.

이 모듈은 **읽고 세기만 한다** — 실행 포트도, 재시도 경로도 갖지 않는다.
특히 재발화는 금지에 가깝다: 같은 지시 턴에서 다시 쏘면 `Step 2`부터 dedupe에
접히고(면제 집합 밖이다) 불완전한 프로그래머로 `Store`가 실행된다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.fx.instantiate import (
    CROSS_CALL_COLLISION,
    SKIPPED_ALREADY_EXECUTED,
    FxInstantiation,
    collided_lines,
    is_programmer_state,
)

__all__ = [
    "COMPLETE",
    "CROSS_CALL_COLLISION",
    "EFFECT_EVIDENCE_NOTICE",
    "PARTIAL",
    "PLANNED",
    "REQUERY_LIMIT_NOTICE",
    "FxReport",
    "build_report",
    "to_korean",
]

# 판정 4종. 닫힌 집합이며 "부분"을 "성공"으로 접지 않는다.
PLANNED = "planned"  # 실행 결과를 관측하지 않음
COMPLETE = "complete"  # 전 커맨드 실행됨 + 충돌 0
PARTIAL = "partial"  # 실패 또는 미실행이 있음
# CROSS_CALL_COLLISION 은 `instantiate`가 소유한다 — 사유 코드와 판정이 같은 사실을
# 가리키므로 두 벌로 두지 않는다.

EFFECT_EVIDENCE_NOTICE = (
    "※ 이펙트 효과는 기계로 확인되지 않습니다 — 무대/GUI에서 사람이 직접 확인해야 합니다."
)
REQUERY_LIMIT_NOTICE = (
    "※ 재조회로 확인할 수 있는 것은 시퀀스·큐의 존재뿐입니다 — 그것은 효과의 증거가 아닙니다."
)

_VERDICT_LABELS = {
    PLANNED: "계획",
    COMPLETE: "전량 실행",
    PARTIAL: "부분",
    CROSS_CALL_COLLISION: "교차 호출 충돌",
}


def verdict_label(code: str) -> str:
    """판정 코드의 한국어 라벨. 모르는 코드는 그대로 돌려준다."""
    return _VERDICT_LABELS.get(code, code)


def _field(outcome: object, name: str) -> str:
    value = outcome.get(name, "") if isinstance(outcome, Mapping) else getattr(outcome, name, "")
    return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class FxReport:
    """인스턴스화 1회의 판정 + 전파 대상 3종."""

    instantiation: FxInstantiation
    verdict: str
    executed: bool = False
    executed_ok: int = 0
    failed: tuple[str, ...] = ()
    not_executed: tuple[str, ...] = ()
    collided: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        """성공은 `COMPLETE` 하나뿐이다 — 부분 성공을 전체 성공으로 위장하지 않는다."""
        return self.verdict == COMPLETE

    def to_dict(self) -> dict:
        plan = self.instantiation
        return {
            "fx_id": plan.fx_id,
            "display_name": plan.display_name,
            "pattern": plan.pattern,
            "group": plan.group,
            "sequence": plan.sequence,
            "cue": plan.cue,
            "label": plan.label,
            "executor": plan.executor,
            "attributes": list(plan.attributes),
            "step_count": plan.step_count,
            "speed_bpm": plan.speed_bpm,
            "verdict": self.verdict,
            "verdict_ko": verdict_label(self.verdict),
            "executed": self.executed,
            "succeeded": self.succeeded,
            "command_count": len(plan.commands),
            "executed_ok": self.executed_ok,
            "failed": list(self.failed),
            "not_executed": list(self.not_executed),
            "collided": list(self.collided),
            # 무조건 문면. 구조화 보고에서도 빠지지 않는다 — 모델이 읽는 것도
            # 이쪽이기 때문이다.
            "effect_evidence": EFFECT_EVIDENCE_NOTICE,
            "requery_limit": REQUERY_LIMIT_NOTICE,
        }


def build_report(
    instantiation: FxInstantiation, outcomes: Sequence[object] | None = None
) -> FxReport:
    """번들과 (있다면) 실행 결과에서 2단 보고를 만든다.

    ``outcomes``는 ``run_commands``의 per-command status다. 없으면 계획 수준
    보고이며 ``executed=False``가 그 사실을 말한다 — 실행하지 않은 것을 실행한
    것처럼 보고하지 않는다.
    """
    listed = list(outcomes or ())
    if not listed:
        return FxReport(instantiation=instantiation, verdict=PLANNED)

    failed = tuple(_field(o, "command") for o in listed if _field(o, "status") == "failed")
    not_executed = tuple(
        _field(o, "command") for o in listed if _field(o, "status") == "not_executed"
    )
    executed_ok = sum(1 for o in listed if _field(o, "status") == "executed_ok")
    collided = collided_lines(listed)

    if collided:
        # 면제 라인의 접힘은 정상이다(`ClearAll`은 반복돼도 아무 산출물을
        # 만들지 않는다). 비면제 라인이 한 줄이라도 접혔으면 성공 보고를
        # 금지한다 — 시퀀스 번호가 달라 `Store`는 유일 문자열이므로 실행됐고,
        # 불완전한 큐가 이미 존재할 수 있다.
        verdict = CROSS_CALL_COLLISION
    elif failed or not_executed:
        verdict = PARTIAL
    else:
        verdict = COMPLETE

    return FxReport(
        instantiation=instantiation,
        verdict=verdict,
        executed=True,
        executed_ok=executed_ok,
        failed=failed,
        not_executed=not_executed,
        collided=collided,
    )


def to_korean(report: FxReport) -> str:
    """사용자 대면 요약. 요약 한 단, 상세 한 단 — 둘 다 낸다."""
    plan = report.instantiation
    lines = [
        f"[{plan.pattern}] 시퀀스 {plan.sequence} 큐 {plan.cue} '{plan.label}' · "
        f"그룹 {plan.group} · 커맨드 {len(plan.commands)}개 · "
        f"판정 {verdict_label(report.verdict)}",
    ]
    if not report.executed:
        lines.append("  ※ 실행 결과를 관측하지 않은 계획 단계 보고입니다.")
    else:
        lines.append(
            f"  실행 {report.executed_ok}개 · 실패 {len(report.failed)}개 · "
            f"미실행 {len(report.not_executed)}개 · 접힘 {len(report.collided)}개"
        )

    lines.append("상세:")
    lines.append(
        f"  패턴 {plan.pattern} · 대상 {', '.join(plan.attributes)} · 스텝 {plan.step_count}단"
    )
    if plan.speed_bpm is not None:
        # ASSUMPTION-38 GO — 단위는 BPM이다(M0 GUI 판독).
        lines.append(f"  속도 {_number(plan.speed_bpm)} BPM")
    if plan.matricks:
        axes = ", ".join(f"{axis} {_number(value)}" for axis, value in plan.matricks)
        lines.append(f"  MAtricks {axes}")
    if plan.executor is not None:
        lines.append(f"  익스큐터 {plan.executor}에 배치 (사용자 명시 지정)")

    for command in report.failed:
        lines.append(f"  ! 실패 — {command}")
    for command in report.not_executed:
        lines.append(f"  - 미실행 — {command}")
    for command in report.collided:
        lines.append(f"  × 접힘 — {command}")

    if report.collided:
        lines.append(
            "  ! 교차 호출 충돌: 위 라인은 같은 지시 턴의 앞선 호출이 이미 발화해 "
            "dedupe에 접혔습니다. 이 인스턴스화는 성공이 아닙니다 — "
            "불완전한 시퀀스·큐가 이미 생성됐을 수 있습니다."
        )
        lines.append(
            "  ! v1의 운용 경계는 지시 턴당 인스턴스화 1회입니다. 다시 걸려면 "
            "새 지시로 나눠 주세요."
        )
    lines.append(f"  {EFFECT_EVIDENCE_NOTICE}")
    lines.append(f"  {REQUERY_LIMIT_NOTICE}")
    return "\n".join(lines)


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


# `is_programmer_state`/`SKIPPED_ALREADY_EXECUTED`는 판정 어휘의 출처를 한 곳으로
# 묶어 두기 위한 재수출이다 — 보고 계층이 자기 판단으로 면제를 다시 정의하면
# 가드와 보고가 갈라진다.
_REEXPORTED = (is_programmer_state, SKIPPED_ALREADY_EXECUTED)
