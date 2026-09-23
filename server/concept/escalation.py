"""후렴 회차 확장(escalation) 판정 — SPEC-LDDESIGN-001 M4 (REQ-LDDESIGN-042~049).

순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다.

여섯 축(REQ-043) — 기구군 수·무대 면적·밝기·모션 단계·포지션 방향·
큐 밀도(그 후렴 안의 프레이즈 큐 수) — 로만 "새로 확장됐는지"를 판정한다.
**색은 이 여섯 축에 없다** — 정체성 판정(REQ-042, G2)은 색을 보지만
그것은 별도 판정이지 회차 확장 축이 아니다.

모든 판정 함수는 결과 객체를 반환하며 예외를 던지지 않는다(REQ-052 와
같은 방향 — 경고/판정은 조립을 막지 않는다).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.concept.cue_model import CueState

__all__ = [
    "AXES",
    "ChorusSnapshot",
    "ChorusPair",
    "GateResult",
    "build_chorus_snapshots",
    "new_axes",
    "check_pairs",
    "g2_identity",
    "g3_new_axis_within_five",
    "g4_final_new_axis_and_headroom",
    "g49_stagnation_is_normal",
    "remaining_motion_before_final",
]

# REQ-043 여섯 축 — 이 이름 다섯 + "density"(프레이즈 밀도)가 전부다.
AXES: tuple[str, ...] = ("groups", "area", "brightness", "motion", "direction", "density")


@dataclass(frozen=True)
class ChorusSnapshot:
    """후렴(Chorus/Final Chorus) 구간 큐 하나를 회차 판정용으로 요약한 것.

    Attributes:
        section: ``"Chorus"`` 또는 ``"Final Chorus"``.
        occurrence: 그 섹션 이름 자신의 회차(호출자가 붙인 번호 — Chorus
            와 Final Chorus 는 독립적으로 센다).
        round_number: 후렴 계열 전체에서 몇 번째인지(1-base, Chorus 와
            Final Chorus 를 합쳐 시간순으로 센다) — REQ-043/045/049 의
            "N회차"는 전부 이 번호를 가리킨다.
        color: 이 큐가 해석된 뒤의 색(REQ-042 정체성 판정용 — 회차 확장
            축은 아니다).
        groups_on: 켜진 그룹 수.
        area: 켜진 그룹 비율(0~1).
        brightness: 최대 디머 값.
        motion: 모션 단계.
        position: 포지션 이름.
        phrase_density: 그 후렴 안(같은 section+occurrence)의 프레이즈
            큐 개수.
    """

    section: str
    occurrence: int
    round_number: int
    color: str | None
    groups_on: int
    area: float
    brightness: int
    motion: int
    position: str
    phrase_density: int


def build_chorus_snapshots(
    rows: Sequence[Mapping[str, object]],
    states: Sequence[CueState],
    *,
    total_groups: int,
) -> list[ChorusSnapshot]:
    """:func:`server.concept.density.compile_density` 의 ``sequence`` 를
    :func:`server.concept.resolver.resolve_sequence` 로 해석한 뒤, 후렴
    구간 큐만 골라 스냅샷으로 요약한다.

    ``rows`` 와 ``states`` 는 같은 순서(``ts`` 오름차순)의 나란한
    시퀀스여야 한다 — ``resolve_sequence(rows)`` 의 반환값을 그대로
    ``states`` 로 넘기면 된다.
    """
    snapshots: list[ChorusSnapshot] = []
    for row, state in zip(rows, states, strict=True):
        if row.get("kind") != "section":
            continue
        section = row["section"]
        if section not in ("Chorus", "Final Chorus"):
            continue
        occurrence = row.get("occurrence", 1)
        groups_on = sum(1 for value in state.dim.values() if value > 0)
        top = max(state.dim.values(), default=0)
        phrase_density = sum(
            1
            for r in rows
            if r.get("kind") == "phrase"
            and r.get("section") == section
            and r.get("occurrence", 1) == occurrence
        )
        snapshots.append(
            ChorusSnapshot(
                section=str(section),
                occurrence=int(occurrence),
                round_number=len(snapshots) + 1,
                color=state.color,
                groups_on=groups_on,
                area=round(groups_on / total_groups, 4) if total_groups else 0.0,
                brightness=top,
                motion=state.motion,
                position=state.pos,
                phrase_density=phrase_density,
            )
        )
    return snapshots


def new_axes(prev: ChorusSnapshot, curr: ChorusSnapshot) -> frozenset[str]:
    """REQ-043 — 인접한 두 후렴 스냅샷 사이에 새로 확장된 축 집합.

    "새로 확장"은 엄밀히 더 커진 것(``>``)만 센다 — 같거나 줄어든 것은
    새 축이 아니다(포지션 방향만 예외로, 값이 달라지면 축으로 센다).
    """
    axes: set[str] = set()
    if curr.groups_on > prev.groups_on:
        axes.add("groups")
    if curr.area > prev.area:
        axes.add("area")
    if curr.brightness > prev.brightness:
        axes.add("brightness")
    if curr.motion > prev.motion:
        axes.add("motion")
    if curr.position != prev.position:
        axes.add("direction")
    if curr.phrase_density > prev.phrase_density:
        axes.add("density")
    return frozenset(axes)


@dataclass(frozen=True)
class ChorusPair:
    """인접한 후렴 쌍 하나의 판정 결과."""

    label: str
    prev: ChorusSnapshot
    curr: ChorusSnapshot
    axes: frozenset[str]
    identity_maintained: bool


def check_pairs(snapshots: Sequence[ChorusSnapshot]) -> list[ChorusPair]:
    """REQ-042/043 — 인접 후렴 쌍마다 새 축(REQ-043)과 정체성 유지
    (REQ-042 — 주색 동일 **또는** Final Chorus)를 판정한다.
    """
    pairs: list[ChorusPair] = []
    for prev, curr in zip(snapshots, snapshots[1:], strict=False):
        axes = new_axes(prev, curr)
        identity = (curr.color == prev.color) or (curr.section == "Final Chorus")
        pairs.append(
            ChorusPair(
                label=f"{prev.section} {prev.round_number}→{curr.section} {curr.round_number}",
                prev=prev,
                curr=curr,
                axes=axes,
                identity_maintained=identity,
            )
        )
    return pairs


@dataclass(frozen=True)
class GateResult:
    """게이트 판정 결과 — ``passed`` 가 ``None`` 이면 해당 없음(n/a)."""

    passed: bool | None
    detail: str


def g2_identity(pairs: Sequence[ChorusPair]) -> GateResult:
    """G2 — 후렴 쌍 전부(8곡 기준 n/a 아닌 곡 전부) 정체성 유지 비율이
    1.0 인지(REQ-042, AC-LDDESIGN-002)."""
    if not pairs:
        return GateResult(None, "후렴 쌍 없음(구조상 n/a)")
    kept = sum(1 for pair in pairs if pair.identity_maintained)
    return GateResult(kept == len(pairs), f"{kept}/{len(pairs)} 쌍 정체성 유지")


def g3_new_axis_within_five(pairs: Sequence[ChorusPair]) -> GateResult:
    """G3 — 5회차까지의 후렴 쌍 중 새 축이 0인 쌍이 없는지(REQ-043,
    AC-LDDESIGN-003). 6회차 이후는 이 게이트가 보지 않는다(REQ-049는
    그 몫을 :func:`g49_stagnation_is_normal` 이 명시적으로 진다)."""
    if not pairs:
        return GateResult(None, "후렴 쌍 없음(구조상 n/a)")
    early_flat = [pair for pair in pairs if pair.curr.round_number <= 5 and not pair.axes]
    return GateResult(len(early_flat) == 0, f"새 축 0인 쌍(5회차 이내) {len(early_flat)}개")


def remaining_motion_before_final(
    states: Sequence[CueState],
    final_chorus_index: int | None,
    *,
    max_motion: int = 3,
) -> int | None:
    """REQ-044/048 재정의(카드 t439, 리드 결정) — G4 가 읽을 "피날레
    직전까지 남은 모션 단계"를 낸다.

    "직전 한 줄"의 모션이 아니라 **Final Chorus 이전에 등장한 모든 큐
    중 최대 모션 단계**를 기준으로 삼는다 — 피날레 바로 앞 한 줄이
    절·프리코러스처럼 모션을 0 으로 낮춰도, 그 전에 이미 모션을
    최대치까지 썼다는 사실이 그 한 줄 뒤에 가려지지 않게 하기 위함이다.
    옛 정의(``states[index - 1].motion`` 한 줄만 읽음)는 이 창을 놓쳐,
    마지막 절·브릿지가 모션 0 으로 복귀한 곡(Morning·Rain 실측)에서
    실제로는 이미 소진된 여유를 3 으로 오판했다.

    Args:
        states: :func:`server.concept.resolver.resolve_sequence` 가 낸
            전체 큐 상태 목록(구간+프레이즈 전부, ``ts`` 오름차순).
        final_chorus_index: ``states`` 안에서 Final Chorus 구간 큐의
            인덱스. 그 앞(``states[:final_chorus_index]``)만 판정
            대상이다 — 그 인덱스 자신(피날레 자신의 모션)은 포함하지
            않는다.
        max_motion: 모션 단계 상한(기본 3).

    Returns:
        ``final_chorus_index`` 가 ``None`` 이거나 0 이하이면(Final
        Chorus 가 곡 첫 큐거나 찾지 못했으면) ``None`` — 판정 불가.
    """
    if final_chorus_index is None or final_chorus_index <= 0:
        return None
    used = max((state.motion for state in states[:final_chorus_index]), default=0)
    return max_motion - used


def g4_final_new_axis_and_headroom(
    pairs: Sequence[ChorusPair],
    *,
    before_final_remaining_motion: int | None,
) -> GateResult:
    """G4 — Final Chorus 가 최소 1개의 새 축을 갖고, 그 직전 구간의 남은
    모션 단계가 1 이상인지(REQ-044/048, AC-LDDESIGN-004)."""
    final_pair = next((pair for pair in pairs if pair.curr.section == "Final Chorus"), None)
    if final_pair is None:
        return GateResult(None, "Final Chorus 없음(구조상 n/a)")
    has_new_axis = bool(final_pair.axes)
    motion_ok = before_final_remaining_motion is not None and before_final_remaining_motion >= 1
    detail = (
        f"피날레 새 축 {sorted(final_pair.axes)} · "
        f"직전 남은 모션 단계 {before_final_remaining_motion}"
    )
    return GateResult(has_new_axis and motion_ok, detail)


def g49_stagnation_is_normal(pairs: Sequence[ChorusPair]) -> GateResult:
    """REQ-049 — 후렴 6회 이상 반복 시(상승 축 소진 이후) 상태 유지를
    결함이 아닌 정상으로 간주한다 — 이 게이트는 항상 통과이고, 발견된
    "소진 뒤 유지" 쌍 수를 정보성으로만 남긴다(경고나 실패를 내지
    않는다 — REQ-049 문면 그대로)."""
    late_flat = [pair for pair in pairs if pair.curr.round_number >= 6 and not pair.axes]
    return GateResult(True, f"6회차 이상에서 상태 유지 {len(late_flat)}건(결함 아님)")
