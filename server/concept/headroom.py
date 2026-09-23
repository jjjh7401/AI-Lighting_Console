"""헤드룸 4축 + G5 경고 4조건 — SPEC-LDDESIGN-001 M4 (REQ-LDDESIGN-050~052,
047).

순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다.

4축 계산 자체는 M2 :func:`server.concept.resolver.compute_headroom` 이
이미 한다(REQ-025/050) — 이 모듈은 그 결과를 그대로 재사용하고(얇은
래퍼), G5 경고 4조건(REQ-051)과 그 조건 하나(브릿지)가 참조하는 "구간
단위 비교"(REQ-047)를 새로 정의한다. 경고는 언제나 경고일 뿐이다
(REQ-052 — 조립을 막지 않는다) — 이 모듈의 모든 판정 함수는 예외를
던지지 않는다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from server.concept.cue_model import CueState, Headroom
from server.concept.density import GROUP_ROSTER
from server.concept.resolver import compute_headroom

__all__ = [
    "SectionCueSnapshot",
    "compute_cue_headroom",
    "bridge_reduced",
    "g5_warnings",
]


def compute_cue_headroom(
    state: CueState,
    *,
    all_groups: Sequence[str] = GROUP_ROSTER,
    reserved_colors_remaining: Sequence[str] = (),
    reserved_effects: Sequence[str] = (),
    max_motion: int = 3,
    max_dimmer: int = 100,
) -> Headroom:
    """REQ-050 — 매 구간 큐마다 4축 헤드룸을 계산한다(``resolver.
    compute_headroom`` 의 얇은 래퍼 — 그룹 로스터 기본값만
    ``density.GROUP_ROSTER`` 로 채운다)."""
    return compute_headroom(
        state,
        all_groups=all_groups,
        reserved_colors_remaining=reserved_colors_remaining,
        reserved_effects=reserved_effects,
        max_motion=max_motion,
        max_dimmer=max_dimmer,
    )


@dataclass(frozen=True)
class SectionCueSnapshot:
    """구간 큐 하나를 G5 경고 판정용으로 요약한 것.

    Attributes:
        section: 9종 어휘 이름.
        occurrence: 그 섹션 이름 자신의 회차.
        is_bridge: ``section == "Bridge"`` 여부.
        groups_on: 켜진 그룹 수.
        top_dimmer: 최대 디머 값.
        effects_on: 켜진 효과 그룹 집합(``BLIND``/``STROBE`` 부분집합).
        color: 이 큐가 해석된 뒤의 색.
    """

    section: str
    occurrence: int
    is_bridge: bool
    groups_on: int
    top_dimmer: int
    effects_on: frozenset[str]
    color: str | None


def bridge_reduced(snapshots: Sequence[SectionCueSnapshot]) -> bool:
    """REQ-047 — 모든 Bridge 구간 큐가 그 **직전 "브릿지가 아닌" 구간**
    보다 밝기·그룹 수 둘 다 줄었는지 확인한다(구간 단위 비교 — 브릿지가
    끄기 큐와 켜기 큐 두 개로 나뉘었을 때, 두 번째 큐를 첫 번째 큐와
    비교해 "감소 아님"으로 오탐하지 않는다).

    비교할 "브릿지가 아닌" 직전 구간이 없으면(곡 맨 앞이 Bridge인 경우)
    그 Bridge 큐는 판정에서 건너뛴다 — 비교 기준이 없다.
    """
    ok = True
    for i, snap in enumerate(snapshots):
        if not snap.is_bridge:
            continue
        j = i - 1
        while j >= 0 and snapshots[j].is_bridge:
            j -= 1
        if j < 0:
            continue
        prev = snapshots[j]
        if not (snap.top_dimmer < prev.top_dimmer and snap.groups_on < prev.groups_on):
            ok = False
    return ok


def g5_warnings(
    *,
    intro_groups_on: int | None,
    total_groups: int,
    chorus1_effects_on: frozenset[str],
    chorus1_color: str | None,
    bridge_snapshots: Sequence[SectionCueSnapshot],
    final_chorus_has_new_axis: bool | None,
    white_color: str = "흰색",
) -> tuple[str, ...]:
    """REQ-051 — 4조건 중 하나라도 성립하면 경고를 기록한다. 절대
    조립을 막지 않는다(REQ-052 — 예외를 던지지 않고 문자열 튜플만
    돌려준다).

    조건 (2)는 **OR** 다 — 블라인더/스트로브가 켜졌거나(``|``) 색이
    흰색이면 경고다. AND 로 구현하면(둘 다 참일 때만 경고) 절반의
    경우를 놓친다 — 시험이 이 차이를 대조군으로 확인한다.
    """
    warnings: list[str] = []
    if intro_groups_on is not None and total_groups > 0 and intro_groups_on >= total_groups:
        warnings.append("G5: Intro 에서 전체 기구 그룹이 이미 켜짐")
    if (chorus1_effects_on & {"BLIND", "STROBE"}) or chorus1_color == white_color:
        warnings.append("G5: Chorus 1 에서 블라인더/스트로브가 켜졌거나 색이 흰색")
    if bridge_snapshots and not bridge_reduced(bridge_snapshots):
        warnings.append("G5: Bridge 에서 밝기·그룹 수가 줄지 않음(구간 단위 비교)")
    if final_chorus_has_new_axis is False:
        warnings.append("G5: Final Chorus 에 추가 가능한 새 축이 없음")
    return tuple(warnings)
