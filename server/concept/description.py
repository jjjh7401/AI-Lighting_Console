"""큐 description 생성기 — SPEC-LDDESIGN-001 M2 (REQ-LDDESIGN-023, 070).

``.moai/state/verify/f12e5c95-t429/final_integrated.py`` 125~131행의
문장 조립 로직을 저장소 타입(:mod:`server.concept.cue_model`)으로
재작성한다 — 결정론적 한국어 한 문장 이상이며, 절대 빈 문자열을 내지
않는다(REQ-023 "description... 최소... 무엇을 복원/추가/제거했는지, 색이
바뀌었는지, 최대 밝기, 남겨둔 자원").
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from server.concept.cue_model import CueState, Headroom

__all__ = ["describe"]


def describe(
    prev_state: CueState,
    state: CueState,
    ops: Sequence[Mapping[str, object]],
    headroom: Headroom,
) -> str:
    """이전 상태와 현재 상태의 차이 + 헤드룸을 한 문장으로 서술한다.

    Args:
        prev_state: 이 큐 직전 상태.
        state: 이 큐가 해석된 뒤의 상태(:func:`server.concept.resolver.apply`
            의 반환값).
        ops: 이 큐가 수행한 동작 목록 — ``restore`` 대상 이름을 뽑는 데만
            쓴다(다른 동작은 상태 차이로 이미 드러난다).
        headroom: 이 큐의 헤드룸 계산 결과(REQ-025) — 남겨둔 자원 절을
            채운다.

    Returns:
        빈 문자열이 될 수 없는 한국어 문장. 각 부분은 " · " 로 잇는다
        (프로토타입과 같은 구분자).
    """
    parts: list[str] = []

    restore_ops = [op for op in ops if op.get("op") == "restore"]
    if restore_ops:
        parts.append(f"{restore_ops[0]['ref']} 복원")

    prev_on = {role for role, value in prev_state.dim.items() if value > 0}
    now_on = {role for role, value in state.dim.items() if value > 0}
    added = sorted(now_on - prev_on)
    removed = sorted(prev_on - now_on)
    if added:
        parts.append("+" + "·".join(added))
    if removed:
        parts.append("-" + "·".join(removed))

    if state.color != prev_state.color:
        parts.append(f"색 {state.color if state.color is not None else '—'}")

    top = max(state.dim.values(), default=0)
    parts.append(f"최대 {top}%")

    reserves = list(headroom.reserved_effects) + [
        color for color in headroom.reserved_colors if color != state.color
    ]
    if reserves:
        parts.append("남김: " + "·".join(reserves))

    # "최대 N%" 절을 항상 붙이므로 parts 는 여기서 절대 비지 않는다(REQ-023
    # "never empty" — 이 불변식을 시험이 직접 재확인한다).
    return " · ".join(parts)
