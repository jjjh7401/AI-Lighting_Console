"""씬 컴파일 — 한국어 2단 보고 계층 (REQ-SCENE-014).

`server/fx/report.py`의 미러다: 번들 조립과 **다른 관심사**라 별도 모듈에 두고,
한국어 표현은 커맨드 생성과 무관하게 여기서만 산다.

이 계층이 다른 리포트와 갈리는 지점은 하나다 — **네 주장을 분리한다.**

| 주장 | 증거 채널 | 이 모듈의 상수 |
|---|---|---|
| (a) 큐가 생성됐다 | 재조회(이름·`cueNo`) | `ARTIFACT_CONFIRMED_NOTE` / `..._UNVERIFIED_...` |
| (a′) 값 라인이 균일 집합을 담았다 | 산출 문자열 정적 검사 | `UNIFORM_CONFIRMED_NOTE` |
| (b) 이펙트가 움직인다 / 룩이 발색한다 | 사람 GUI | `EFFECT_EVIDENCE_NOTICE` |
| (c) 트래킹이 무해해졌다 | **없음** | `TRACKING_UNOBSERVABLE_NOTICE` |
| (d) 이 씬이 주장하지 않는 속성 | 정적 차집합 | `UNCLAIMED_ENUMERATION_NOTE` |

# @MX:ANCHOR: [AUTO] (a′)와 (c)는 **다른 주장**이며 같은 문단에 오지 않는다.
#   성공 경로를 포함한 **모든** 보고가 `EFFECT_EVIDENCE_NOTICE`와
#   `TRACKING_UNOBSERVABLE_NOTICE`를 싣는다 — 조건부가 아니다.
# @MX:REASON: design.md §6.2 — "균일 집합을 발화했다"는 정적으로 확인되지만
#   "그래서 트래킹이 무해해졌다"는 **관측 채널이 아예 없다**(큐의 내용을 돌려주는
#   경로가 존재하지 않는다, spec.md §C.1). 둘을 붙여 쓰면 독자는 전자를 후자의
#   증거로 읽으며, 그것이 `/CueOnly` 때의 실패 모드였다. 정책은 D1 개정으로
#   바뀌었고 **인지 함정은 그대로다** — 그래서 (c)의 문면은 침묵하지 않고
#   그 추론을 명시적으로 거절한다.

이 모듈은 **읽고 세기만 한다** — 실행 포트도, 재시도 경로도 갖지 않는다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.fx.instantiate import (
    CROSS_CALL_COLLISION,
    SKIPPED_ALREADY_EXECUTED,
    collided_lines,
    is_programmer_state,
)
from server.scene.compile import SCENE_UNIFORM_ATTRIBUTES, SceneCompilation

__all__ = [
    "ARTIFACT_CONFIRMED_NOTE",
    "ARTIFACT_UNVERIFIED_NOTE",
    "COLLIDED_ENUMERATION_NOTE",
    "COMPLETE",
    "CROSS_CALL_COLLISION",
    "CROSS_CALL_COLLISION_NOTE",
    "EFFECT_EVIDENCE_NOTICE",
    "PARTIAL",
    "PLANNED",
    "TRACKING_UNOBSERVABLE_NOTICE",
    "UNCLAIMED_ENUMERATION_NOTE",
    "UNIFORM_BROKEN_NOTE",
    "UNIFORM_CONFIRMED_NOTE",
    "UNIFORM_NOT_APPLICABLE_NOTE",
    "SceneReport",
    "build_report",
    "to_korean",
    "verdict_label",
]

# 판정 4종. 닫힌 집합이며 "부분"을 "성공"으로 접지 않는다. `CROSS_CALL_COLLISION`은
# `server.fx.instantiate`가 소유한다 — 사유 코드와 판정이 같은 사실을 가리키므로
# 씬이 두 번째 이름을 만들지 않는다(결정 G).
PLANNED = "planned"  # 실행 결과를 관측하지 않음
COMPLETE = "complete"  # 전 커맨드 실행됨 + 접힘 0
PARTIAL = "partial"  # 실패 또는 미실행이 있음

# (a) — 재조회가 돌려주는 것의 경계를 문면에 박아 둔다.
ARTIFACT_CONFIRMED_NOTE = (
    "※ 기계 확인됨 — 재조회가 확인해 준 것은 시퀀스·큐의 존재와 이름, 실제 cueNo뿐입니다."
)
ARTIFACT_UNVERIFIED_NOTE = (
    "※ 재조회를 수행하지 않았습니다 — 커맨드 접수(ok)는 큐가 생성됐다는 증거가 아닙니다."
)

# (a′) — 산출 문자열을 다시 읽어 세운 사실이다. 콘솔에 묻지 않는다.
UNIFORM_CONFIRMED_NOTE = (
    "※ 기계 확인됨 — 룩 값 라인이 균일 속성 집합"
    f"({', '.join(SCENE_UNIFORM_ATTRIBUTES)})을 이 순서로 담았습니다. 산출 문자열 정적 검사입니다."
)
UNIFORM_NOT_APPLICABLE_NOTE = (
    "※ 이 씬은 룩 값 라인이 없어(이펙트 단독) 균일 속성 집합의 적용 대상이 아닙니다."
)
UNIFORM_BROKEN_NOTE = (
    "! 룩 값 라인이 균일 속성 집합을 이 순서로 담지 않았습니다 — 산출 문자열 정적 검사 결과입니다."
)

# (b) — 무조건. 성공 경로에서도 빠지지 않는다.
EFFECT_EVIDENCE_NOTICE = (
    "※ 기계 확인 불가 — 이펙트의 모션과 룩의 발색은 무대/GUI에서 사람이 직접 확인해야 합니다."
)

# (c) — 침묵하지 않고 추론을 거절한다. 위 @MX:REASON 참조.
TRACKING_UNOBSERVABLE_NOTICE = (
    "※ 기계 확인 불가 — 트래킹이 무해해졌는지는 관측 채널이 존재하지 않습니다"
    "(큐의 내용을 돌려주는 경로가 없습니다). 위 균일성 확인은 무엇을 발화했는지에 대한 "
    "사실이며 트래킹 무해화의 증거가 아닙니다."
)

# 두 열거는 서로 다른 것이다 — 문면이 그것을 구분한다(AC-SCENE-016).
COLLIDED_ENUMERATION_NOTE = (
    "덮인 attribute — 룩과 이펙트가 같은 축을 지정해 이펙트가 이긴 속성입니다."
)
UNCLAIMED_ENUMERATION_NOTE = (
    "이 씬이 주장하지 않는 속성 — 앞 씬의 값이 이월될 수 있습니다"
    "(이월됐다는 뜻이 아닙니다 — 실제 이월은 관측할 수 없습니다)."
)

CROSS_CALL_COLLISION_NOTE = (
    "! 교차 호출 충돌: 아래 라인은 같은 지시 턴의 앞선 호출이 이미 발화해 dedupe에 "
    "접혔습니다. 이 컴파일은 성공이 아닙니다 — Store는 자기 고유 문자열이라 실행되므로 "
    "불완전한 시퀀스·큐가 이미 생성됐을 수 있습니다."
)

_VERDICT_LABELS = {
    PLANNED: "계획",
    COMPLETE: "전량 실행",
    PARTIAL: "부분",
    CROSS_CALL_COLLISION: "교차 호출 충돌",
}

# 절대값 세그먼트(`Attribute 'X' At <수>`)만으로 이루어진 `;` 체인이 룩 값 라인이다.
# `;` 체인이라는 것만으로는 부족하다 — `_speed_line`도 체인이며 `At Speed`를 낸다.
_ABSOLUTE_VALUE = re.compile(r"^Attribute '(?P<name>[^']+)' At -?\d+(?:\.\d+)?$")


def verdict_label(code: str) -> str:
    """판정 코드의 한국어 라벨. 모르는 코드는 그대로 돌려준다."""
    return _VERDICT_LABELS.get(code, code)


def _field(outcome: object, name: str) -> str:
    value = outcome.get(name, "") if isinstance(outcome, Mapping) else getattr(outcome, name, "")
    return value if isinstance(value, str) else ""


def _look_value_line(commands: Sequence[str]) -> str | None:
    for line in commands:
        parts = [part.strip() for part in line.split(";")]
        if len(parts) > 1 and all(_ABSOLUTE_VALUE.match(part) for part in parts):
            return line
    return None


def _uniform_attributes(commands: Sequence[str]) -> tuple[str, ...]:
    """(a′)를 산출 문자열에서 **다시 읽어** 세운다.

    빌더가 무엇을 의도했는지가 아니라 번들이 실제로 무엇을 담았는지가 주장의
    내용이므로, 컴파일러의 정렬 결과를 신뢰하지 않고 여기서 독립적으로 판독한다.
    """
    line = _look_value_line(commands)
    if line is None:
        return ()
    names = [
        match.group("name")
        for match in (_ABSOLUTE_VALUE.match(part.strip()) for part in line.split(";"))
        if match
    ]
    return tuple(name for name in names if name in set(SCENE_UNIFORM_ATTRIBUTES))


@dataclass(frozen=True)
class SceneReport:
    """컴파일 1회의 판정 + 전파 대상 + 주장 4종."""

    compilation: SceneCompilation
    verdict: str
    executed: bool = False
    executed_ok: int = 0
    failed: tuple[str, ...] = ()
    not_executed: tuple[str, ...] = ()
    collided: tuple[str, ...] = ()
    uniform_attributes: tuple[str, ...] = ()
    has_look_value_line: bool = False
    requery: Mapping[str, object] | None = None

    @property
    def succeeded(self) -> bool:
        """성공은 `COMPLETE` 하나뿐이다 — 부분 성공을 전체 성공으로 위장하지 않는다."""
        return self.verdict == COMPLETE

    @property
    def collided_attributes(self) -> tuple[str, ...]:
        """룩 ∩ 이펙트. 결정론 정렬 — 집합 순회 순서에 맡기지 않는다."""
        return tuple(sorted(self.compilation.collided_attributes))

    @property
    def unclaimed_attributes(self) -> tuple[str, ...]:
        """`KNOWN_ATTRIBUTES` − (룩 ∪ fx). 결정론 정렬."""
        return tuple(sorted(self.compilation.unclaimed_attributes))

    @property
    def artifact_claim(self) -> str:
        return ARTIFACT_CONFIRMED_NOTE if self.requery else ARTIFACT_UNVERIFIED_NOTE

    @property
    def uniform_claim(self) -> str:
        if not self.has_look_value_line:
            return UNIFORM_NOT_APPLICABLE_NOTE
        if self.uniform_attributes == SCENE_UNIFORM_ATTRIBUTES:
            return UNIFORM_CONFIRMED_NOTE
        return UNIFORM_BROKEN_NOTE

    def to_dict(self) -> dict:
        plan = self.compilation
        return {
            "scene_id": plan.scene_id,
            "display_name": plan.display_name,
            "label": plan.label,
            "group": plan.group,
            "sequence": plan.sequence,
            "cue": plan.cue,
            "look_id": plan.look_id,
            "fx_id": plan.fx_id,
            "executor": plan.executor,
            "trig_type": plan.trig_type,
            "trig_time": plan.trig_time,
            "verdict": self.verdict,
            "verdict_ko": verdict_label(self.verdict),
            "executed": self.executed,
            "succeeded": self.succeeded,
            "command_count": len(plan.commands),
            "executed_ok": self.executed_ok,
            "failed": list(self.failed),
            "not_executed": list(self.not_executed),
            "collided": list(self.collided),
            "collided_attributes": list(self.collided_attributes),
            "unclaimed_attributes": list(self.unclaimed_attributes),
            "uniform_attributes": list(self.uniform_attributes),
            "requery": dict(self.requery) if self.requery else None,
            # 네 주장은 구조화 보고에서도 분리된 키다 — 모델이 읽는 것도
            # 이쪽이기 때문이다. 뭉치면 산문에서 분리한 의미가 사라진다.
            "claims": {
                "artifact": self.artifact_claim,
                "uniform": self.uniform_claim,
                "effect": EFFECT_EVIDENCE_NOTICE,
                "tracking": TRACKING_UNOBSERVABLE_NOTICE,
                "unclaimed": UNCLAIMED_ENUMERATION_NOTE,
            },
        }


def build_report(
    compilation: SceneCompilation,
    outcomes: Sequence[object] | None = None,
    *,
    requery: Mapping[str, object] | None = None,
) -> SceneReport:
    """번들과 (있다면) 실행 결과에서 2단 보고를 만든다.

    ``outcomes``는 ``run_commands``의 per-command status다. 없으면 계획 수준
    보고이며 ``executed=False``가 그 사실을 말한다 — 실행하지 않은 것을 실행한
    것처럼 보고하지 않는다. ``requery``도 같은 규율이다: 주지 않으면 (a)는
    "확인됨"이 아니라 "미확인"으로 나간다.
    """
    uniform = _uniform_attributes(compilation.commands)
    has_look_line = _look_value_line(compilation.commands) is not None
    listed = list(outcomes or ())
    if not listed:
        return SceneReport(
            compilation=compilation,
            verdict=PLANNED,
            uniform_attributes=uniform,
            has_look_value_line=has_look_line,
            requery=requery,
        )

    failed = tuple(_field(o, "command") for o in listed if _field(o, "status") == "failed")
    not_executed = tuple(
        _field(o, "command") for o in listed if _field(o, "status") == "not_executed"
    )
    executed_ok = sum(1 for o in listed if _field(o, "status") == "executed_ok")
    # 면제 라인의 접힘은 정상이다(`ClearAll`은 반복돼도 산출물을 만들지 않는다).
    # 비면제 판정은 fx의 공개 함수가 소유한다 — 씬은 사본을 두지 않는다(결정 E·G).
    collided = collided_lines(listed)

    if collided:
        verdict = CROSS_CALL_COLLISION
    elif failed or not_executed:
        verdict = PARTIAL
    else:
        verdict = COMPLETE

    return SceneReport(
        compilation=compilation,
        verdict=verdict,
        executed=True,
        executed_ok=executed_ok,
        failed=failed,
        not_executed=not_executed,
        collided=collided,
        uniform_attributes=uniform,
        has_look_value_line=has_look_line,
        requery=requery,
    )


def to_korean(report: SceneReport) -> str:
    """사용자 대면 보고. 요약 한 단, 상세 한 단 — 그리고 주장은 분리한다."""
    plan = report.compilation
    lines = [
        f"[씬] 시퀀스 {plan.sequence} 큐 {plan.cue} '{plan.label}' · 그룹 {plan.group} · "
        f"커맨드 {len(plan.commands)}개 · 판정 {verdict_label(report.verdict)}",
    ]
    if not report.executed:
        lines.append("  ※ 실행 결과를 관측하지 않은 계획 단계 보고입니다.")
    else:
        lines.append(
            f"  실행 {report.executed_ok}개 · 실패 {len(report.failed)}개 · "
            f"미실행 {len(report.not_executed)}개 · 접힘 {len(report.collided)}개"
        )

    lines.append("상세:")
    lines.append(f"  씬 {plan.scene_id} '{plan.display_name}'")
    lines.append(f"  룩 {plan.look_id or '없음'} · 이펙트 {plan.fx_id or '없음'}")
    if plan.trig_type is not None:
        lines.append(f"  트리거 {plan.trig_type} · TrigTime {plan.trig_time}")
    if plan.executor is not None:
        lines.append(f"  익스큐터 {plan.executor}에 배치 (사용자 명시 지정)")
    if report.requery:
        lines.append(
            f"  재조회 — 시퀀스 '{report.requery.get('sequence_name')}' · "
            f"큐 '{report.requery.get('cue_name')}' (cueNo {report.requery.get('cue_no')})"
        )

    lines.append(f"  {COLLIDED_ENUMERATION_NOTE}")
    lines.append(f"    {', '.join(report.collided_attributes) or '없음'}")
    lines.append(f"  {UNCLAIMED_ENUMERATION_NOTE}")
    lines.append(f"    {', '.join(report.unclaimed_attributes) or '없음'}")

    for command in report.failed:
        lines.append(f"  ! 실패 — {command}")
    for command in report.not_executed:
        lines.append(f"  - 미실행 — {command}")
    for command in report.collided:
        lines.append(f"  × 접힘 — {command}")
    if report.collided:
        lines.append(f"  {CROSS_CALL_COLLISION_NOTE}")
        lines.append("  ! v1의 운용 경계는 지시 턴당 컴파일 1회입니다. 새 지시로 나눠 주세요.")

    # 주장 분리. 확인된 것과 확인되지 않은 것은 다른 표제 아래 산다 — 그리고
    # (a′)와 (c) 사이에는 반드시 표제가 하나 들어간다(design.md §6.2).
    #
    # (a)는 표제가 고정이 아니다. 재조회를 하지 않았으면 그 문면은 "확인하지
    # 않았습니다"라고 말하는데, 그것을 `기계 확인됨:` 아래 놓으면 표제와 바로
    # 아래 줄이 서로를 반박한다 — 그리고 툴은 `requery=`를 넘기지 않으므로
    # 그것이 모든 생산 리포트의 모양이었다. 표제만 훑는 독자에게 산출물이
    # 기계 확인된 것으로 제시되는 것이 교리(발화 ≠ 효과)가 가장 막고 싶어 하는
    # 오독이다. 상수 문면은 그대로 두고 배치만 사실을 따라간다.
    # 독립 사전 머지 리뷰가 찾았다 — 스위트는 두 표제의 존재만 보고 있었다.
    artifact_confirmed = report.artifact_claim == ARTIFACT_CONFIRMED_NOTE
    lines.append("기계 확인됨:")
    if artifact_confirmed:
        lines.append(f"  {report.artifact_claim}")
    lines.append(f"  {report.uniform_claim}")
    lines.append("기계 확인 불가:")
    if not artifact_confirmed:
        lines.append(f"  {report.artifact_claim}")
    lines.append(f"  {EFFECT_EVIDENCE_NOTICE}")
    lines.append(f"  {TRACKING_UNOBSERVABLE_NOTICE}")
    return "\n".join(lines)


# `is_programmer_state`/`SKIPPED_ALREADY_EXECUTED`는 판정 어휘의 출처를 한 곳으로
# 묶어 두기 위한 재수출이다 — 보고 계층이 자기 판단으로 면제를 다시 정의하면
# 가드와 보고가 갈라진다(fx report.py:221-224와 같은 규율).
_REEXPORTED = (is_programmer_state, SKIPPED_ALREADY_EXECUTED)
