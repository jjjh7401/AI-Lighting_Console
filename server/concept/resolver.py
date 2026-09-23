"""큐 상태 해석기 — SPEC-LDDESIGN-001 M2 (REQ-LDDESIGN-019~021, 053~057, 062).

``.moai/state/verify/f12e5c95-t429/final_integrated.py`` 의 ``apply()``
(17~41행)·시퀀스 해석(102~108행)·MIB 판정(110~117행)을 저장소 타입
(:mod:`server.concept.cue_model`)으로 재작성한다.

프로토타입과 다른 지점 둘, 둘 다 REQ 문언 위반을 막기 위한 결정:

- ``restore`` 는 참조 상태의 디머·색·모션만 복원하고 **포지션은 제외**한다
  (REQ-020) — 프로토타입의 ``op['pos']`` 별도 처리와 합쳐지면 포지션까지
  복원되는 것처럼 보이는 자리라 이 파일에서 명시적으로 건드리지 않는다.
- ``reduce`` 의 기준 상태는 **직전 트래킹 값이 아니라** (a) 명시된 ``ref``
  또는 (b) 그 큐가 속한 구간의 자기 1회차 값(REQ-021 "첫 회차 restore
  대상 또는 구간 자신의 1회차 값") 둘 중 하나다 — 상대 감소가 연쇄로
  겹쳐 곱해지는 결함(Too Cool 절 50→25→12 실측, REQ-021 근거)을 다시
  만들지 않는다. 어느 쪽도 없으면 예외를 던진다 — 현재 상태로 조용히
  대체하지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from server.concept.cue_model import CueState, Headroom, MibVerdict, RemainingLevels
from server.concept.vocab import VocabError, validate_operation

__all__ = [
    "MOVE_SECONDS",
    "SETTLE_SECONDS",
    "apply",
    "resolve_sequence",
    "mib_verdict",
    "compute_headroom",
    "section_base_name",
]

# plan.md §F 잠정값 — 이동 1.5초 + 정착 0.5초. M8 콘솔 프로브 실측치로
# 교체될 때까지의 자리표시자다(REQ-062, spec.md §4 비목표 B군).
MOVE_SECONDS: float = 1.5
SETTLE_SECONDS: float = 0.5


def section_base_name(section: str) -> str:
    """구간 이름의 자기 1회차 기준 상태 등록명 — 관례 ``"<section> 1"``.

    reduce 가 ``ref`` 없이 호출될 때(REQ-021 폴백 경로)의 조회 키를
    :func:`resolve_sequence` 와 :func:`apply` 양쪽이 같은 규칙으로
    만들도록 한곳에 둔다.
    """
    return f"{section} 1"


def apply(
    state: CueState,
    ops: Sequence[Mapping[str, object]],
    bases: Mapping[str, CueState],
    *,
    section_base: str | None = None,
) -> CueState:
    """큐 하나의 동작 목록(``ops``)을 현재 상태에 순서대로 적용한다(REQ-019).

    Args:
        state: 이 큐 직전까지 트래킹된 상태(``resolve_sequence`` 가 넘기는
            ``carry``, 또는 단일 큐를 단위 시험할 때의 임의 시작 상태).
        ops: ``{"op": <9종 중 하나>, ...}`` 형태의 동작 목록.
        bases: 이름 → 등록된 기준 상태(``restore``/``reduce`` 의 ``ref``
            대상). ``resolve_sequence`` 가 누적해 넘긴다.
        section_base: 현재 큐가 속한 구간의 자기 1회차 기준 이름(관례
            ``section_base_name(section)``) — ``reduce`` 가 ``ref`` 없이
            호출됐을 때의 폴백 조회 키다(REQ-021).

    Raises:
        VocabError: 동작 어휘 밖의 값, 또는 ``restore``/``reduce`` 가
            찾을 수 없는 ``ref`` 를 참조하거나(REQ-021 — ``ref`` 가 주어
            졌는데 ``bases`` 에 없으면 ``section_base`` 로 조용히 바꿔
            타지 않는다), ``reduce`` 가 ``ref`` 도 ``section_base`` 도
            갖지 못한 경우.
    """
    dim: dict[str, int] = dict(state.dim)
    color = state.color
    secondary = state.secondary
    pos = state.pos
    motion = state.motion

    for op in ops:
        kind = op["op"]
        validate_operation(kind)  # type: ignore[arg-type]

        if kind == "retain":
            pass
        elif kind in ("add", "expand"):
            for role in op["roles"]:  # type: ignore[union-attr]
                if kind == "add":
                    dim[role] = max(dim.get(role, 0), op["dimmer"])  # type: ignore[arg-type]
                else:
                    dim[role] = op["dimmer"]  # type: ignore[assignment]
        elif kind == "remove":
            for role in op["roles"]:  # type: ignore[union-attr]
                dim[role] = 0
        elif kind == "reduce":
            factor = op["factor"]
            ref = op.get("ref")
            if ref is not None:
                if ref not in bases:
                    raise VocabError(f"reduce: ref {ref!r} 가 bases 에 없음(REQ-021)")
                base = bases[ref]
            elif section_base is not None and section_base in bases:
                base = bases[section_base]
            else:
                raise VocabError(
                    "reduce: ref 도 구간 자기 1회차 기준(section_base)도 없어 "
                    "기준 상태를 결정할 수 없음 — 직전 트래킹 상태로 대체하지 "
                    "않는다(REQ-021, 연쇄 곱셈 방지)"
                )
            dim = {role: int(round(value * factor)) for role, value in base.dim.items()}  # type: ignore[operator]
        elif kind == "replace":
            color = op["color"]  # type: ignore[assignment]
            # 카드 t444 — 보조색은 같은 replace 동작에 실려 온다. 싣지 않은
            # 동작(한 색만 쓰는 기존 경로)은 보조색을 비운다: 주색만 바꾼
            # 큐가 앞 큐의 보조색을 그대로 끌고 가면 내보내지 않은 색이
            # 남는다.
            secondary = op.get("secondary")  # type: ignore[assignment]
        elif kind == "isolate":
            keep = op["role"]
            keep_dimmer = op["dimmer"]
            dim = {role: (keep_dimmer if role == keep else 0) for role in dim}  # type: ignore[misc]
            dim[keep] = keep_dimmer  # type: ignore[index]
        elif kind == "restore":
            ref = op["ref"]
            if ref not in bases:
                raise VocabError(f"restore: ref {ref!r} 가 bases 에 없음")
            base = bases[ref]  # type: ignore[index]
            dim = dict(base.dim)
            color = base.color
            secondary = base.secondary
            motion = base.motion
            # 포지션은 SHALL NOT 복원한다(REQ-020) — pos 는 건드리지 않는다.
        elif kind == "release":
            dim[op["role"]] = op["dimmer"]  # type: ignore[index]
        # validate_operation() 이 이미 9종 밖의 값을 걸러내므로 else 분기는
        # 불필요하다(9종 전부 위에서 처리됨).

        if "pos" in op:
            pos = op["pos"]  # type: ignore[assignment]
        if "motion" in op:
            motion = op["motion"]  # type: ignore[assignment]

    return CueState(dim=dim, color=color, pos=pos, motion=motion, secondary=secondary)


def resolve_sequence(rows: Sequence[Mapping[str, object]]) -> list[CueState]:
    """구간별 큐 순서 전체를 해석한다(REQ-053~057).

    ``Track`` 은 다음 큐로 누적되고, ``cue_only`` 는 그 큐에서만 적용되어
    다음 큐는 그 ``cue_only`` 큐 이전 상태에서 계산을 시작한다(REQ-057).

    각 행은 최소 ``section``(str)·``ops``(REQ-019 동작 목록)를 갖는다.
    선택 필드: ``occurrence``(기본 1)·``tracking``(REQ-053, 기본
    ``"track"``)·``base_name``(명시적 기준 상태 등록명). 구간의 1회차
    행(``occurrence == 1``)은 ``base_name`` 이 없으면
    :func:`section_base_name` 규칙으로 자동 등록되어, 같은 구간의 뒤
    회차가 ``ref`` 없는 ``reduce`` 를 쓸 수 있게 한다(REQ-021 폴백).
    """
    bases: dict[str, CueState] = {}
    states: list[CueState] = []
    carry = CueState(dim={}, color=None, pos="home", motion=0)

    for row in rows:
        section = str(row["section"])
        occurrence = row.get("occurrence", 1)
        section_base = section_base_name(section)

        next_state = apply(carry, row["ops"], bases, section_base=section_base)  # type: ignore[arg-type]
        states.append(next_state)

        base_name = row.get("base_name")
        if base_name:
            bases[str(base_name)] = next_state
        elif occurrence == 1 and section_base not in bases:
            bases[section_base] = next_state

        tracking = row.get("tracking", "track")
        if tracking != "cue_only":
            carry = next_state

    return states


def mib_verdict(
    prev_state: CueState,
    state: CueState,
    *,
    ts: float,
    dark_since: float,
    movers: Sequence[str],
) -> MibVerdict | None:
    """포지션 변화 하나의 MIB(사전 이동) 판정(REQ-062).

    포지션이 바뀌지 않았으면 ``None`` 이다 — design.md §1 의
    ``mib: MibVerdict | None`` 이 "포지션 변화가 있을 때만" 값을 갖는다고
    스케치한 그대로다.

    Args:
        prev_state: 이 큐 직전 상태.
        state: 이 큐의 상태(포지션 변화가 판정 대상).
        ts: 이 큐의 시각(초).
        dark_since: 무버 계열이 마지막으로 꺼진 시각(초) — 호출자가
            시퀀스를 순회하며 추적해 넘긴다(``final_integrated.py``
            ``off_since`` 와 같은 역할).
        movers: 무버 계열 그룹 이름 목록(예: ``("MOVER-U", "MOVER-D")``).
    """
    if state.pos == prev_state.pos:
        return None

    prev_on = any(prev_state.dim.get(role, 0) > 0 for role in movers)
    now_on = any(state.dim.get(role, 0) > 0 for role in movers)
    window = round(ts - dark_since, 1) if not prev_on else 0.0

    if not prev_on and not now_on:
        status = "dark"
    elif not prev_on and window >= MOVE_SECONDS + SETTLE_SECONDS:
        status = "mark"
    else:
        status = "live"

    mark_insert_at = round(ts - min(window - 0.5, 4.0), 1) if status == "mark" else None
    return MibVerdict(status=status, window_seconds=window, mark_insert_at=mark_insert_at)


def compute_headroom(
    state: CueState,
    *,
    all_groups: Sequence[str],
    reserved_colors_remaining: Sequence[str],
    reserved_effects: Sequence[str],
    max_motion: int = 3,
    max_dimmer: int = 100,
) -> Headroom:
    """REQ-025/050 — 4축 헤드룸(미사용 그룹 수·유보색·유보 효과·남은 상승 단계)."""
    on_groups = {role for role, value in state.dim.items() if value > 0}
    unused = [group for group in all_groups if group not in on_groups]
    top_dimmer = max(state.dim.values(), default=0)
    remaining = RemainingLevels(
        motion=max_motion - state.motion,
        dimmer=max_dimmer - top_dimmer,
    )
    return Headroom(
        unused_groups=len(unused),
        reserved_colors=tuple(reserved_colors_remaining),
        reserved_effects=tuple(reserved_effects),
        remaining=remaining,
    )
