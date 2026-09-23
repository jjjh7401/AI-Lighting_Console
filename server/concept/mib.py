"""MIB(사전 이동) 시퀀스 판정 — SPEC-LDDESIGN-001 M5 (REQ-LDDESIGN-062~067).

:func:`server.concept.resolver.mib_verdict` 를 그대로 재사용한다(REQ-062,
REQ-067 — 두 번째 판정 함수를 만들지 않는다). 이 파일은
``.moai/state/verify/f12e5c95-t429/final_integrated.py`` 110~117행의
``off_since`` 순회를 저장소 코드로 재구현한 시퀀스 호출자와, mark 판정에
대한 Mark 큐 삽입(REQ-063), 절·브릿지 무버 소등 규칙(REQ-064), 어두운
창이 없을 때 포지션 유지(REQ-065), live 판정 설명 주석(REQ-066)을 담는다.

REQ-067 — ``server.director.validate.mib`` 를 import 하지 않는다(계약
경계가 다르다 — 그 모듈의 독스트링 "콘솔 무접촉 · OSC 무접촉"과 같은
이유로 이 계층 전체가 순수 계산이어야 한다). 대신
:func:`server.concept.resolver.mib_verdict` 가 이미 재구현한 같은 원칙
(정착값 0 + 진행 중인 쓰기 없음, "부재는 증명이 아니다")을 재사용한다.

MOVE_SECONDS/SETTLE_SECONDS 잠정값(plan.md §F)은 ``resolver.py`` 한
지점에만 있다 — 이 파일은 그 상수를 다시 적지 않고 그대로 가져와 쓴다.
"""

from __future__ import annotations

from collections.abc import Sequence

from server.concept.cue_model import CueState, MibVerdict
from server.concept.resolver import mib_verdict

__all__ = [
    "MOVER_HOLD_SECTIONS",
    "LIVE_MOVE_ANNOTATION",
    "compute_mib_sequence",
    "mark_cue_spec",
    "movers_off_ops",
    "resolve_position",
    "live_move_note",
]

# REQ-064 — 절(Verse) 또는 Bridge 구간에서 무버 계열 그룹을 소등한다.
MOVER_HOLD_SECTIONS: frozenset[str] = frozenset({"Verse", "Bridge"})

# REQ-066 — live 판정 설명에 붙는 표시.
LIVE_MOVE_ANNOTATION = "live_move"

_INITIAL_STATE = CueState(dim={}, color=None, pos="home", motion=0)


def compute_mib_sequence(
    states: Sequence[CueState],
    timestamps: Sequence[float],
    *,
    movers: Sequence[str],
) -> list[MibVerdict | None]:
    """REQ-062/067 — 시퀀스 전체를 돌며 ``dark_since`` 를 추적해 각 큐의
    MIB 판정을 낸다(``off_since`` 와 같은 역할).

    Args:
        states: 해석된 큐 상태 목록(:func:`server.concept.resolver.
            resolve_sequence` 의 반환값과 같은 모양).
        timestamps: ``states`` 와 같은 길이의 큐 시각(초) 목록.
        movers: 무버 계열 그룹 이름 목록.

    Returns:
        ``states`` 와 같은 길이의 판정 목록 — 포지션 변화가 없는 큐는
        ``None``.
    """
    verdicts: list[MibVerdict | None] = []
    dark_since = 0.0
    prev = _INITIAL_STATE
    for ts, state in zip(timestamps, states, strict=True):
        prev_on = any(prev.dim.get(role, 0) > 0 for role in movers)
        now_on = any(state.dim.get(role, 0) > 0 for role in movers)
        verdict = mib_verdict(prev, state, ts=ts, dark_since=dark_since, movers=movers)
        verdicts.append(verdict)
        if prev_on and not now_on:
            dark_since = ts
        prev = state
    return verdicts


def mark_cue_spec(verdict: MibVerdict, *, pos: str) -> dict[str, object]:
    """REQ-063 — ``mark`` 판정 하나에 대한 Mark 큐(포지션만 변경, 밝기는
    0 유지)를 정확히 1건 만든다.

    Raises:
        ValueError: ``verdict.status`` 가 ``"mark"`` 가 아니면.
    """
    if verdict.status != "mark":
        raise ValueError(f"mark_cue_spec: mark 판정에만 쓴다 (받음: {verdict.status!r})")
    return {
        "ts": verdict.mark_insert_at,
        "kind": "mark",
        "ops": [{"op": "retain", "pos": pos}],
    }


def movers_off_ops(section: str, mover_roles: Sequence[str]) -> list[dict[str, object]] | None:
    """REQ-064 — 절·브릿지 구간이면 무버 계열 그룹을 소등하는 동작
    목록을 낸다(어두운 창에서 포지션을 옮길 수 있도록) — 그 밖의
    구간이면 ``None``."""
    if section not in MOVER_HOLD_SECTIONS:
        return None
    return [{"op": "remove", "roles": list(mover_roles)}]


def resolve_position(
    intended_pos: str,
    prev_state: CueState,
    *,
    ts: float,
    dark_since: float,
    movers: Sequence[str],
) -> tuple[str, MibVerdict | None]:
    """REQ-065 — 어두운 창(dark/mark)이 없으면 포지션을 유지해 변화 자체가
    없도록 한다 — 두 번째 판정 함수를 만들지 않고
    :func:`server.concept.resolver.mib_verdict` 로 미리 판정해 본다.

    Returns:
        ``(실제로 쓸 포지션, 그 전환의 MibVerdict 또는 None)``. 의도한
        전환이 ``live`` 로 판정되면 ``prev_state.pos`` 를 그대로 돌려주고
        (변화가 없었던 것이 되므로) 판정은 ``None`` 이다.

    Note:
        이 함수는 포지션만 바꿔 보는 프로브다 — ``prev_state.dim`` 은
        그대로 들고 간다. 그래서 무버가 꺼진 채라면 창이 아무리 길어도
        판정은 ``dark`` 로 나온다(``mark`` 문턱을 넘겨도 매한가지) —
        ``mark`` 는 "무버가 이 큐에서 함께 켜지며 이동"하는 경우인데,
        이 프로브는 dim 을 바꾸지 않으므로 그 경우를 표현하지 못한다.
        Mark 판정이 필요한 자리는 :func:`compute_mib_sequence` (dim 변화도
        함께 도는 시퀀스 판정)를 쓴다.
    """
    probe = CueState(
        dim=dict(prev_state.dim),
        color=prev_state.color,
        pos=intended_pos,
        motion=prev_state.motion,
        secondary=prev_state.secondary,
    )
    verdict = mib_verdict(prev_state, probe, ts=ts, dark_since=dark_since, movers=movers)
    if verdict is not None and verdict.status == "live":
        return prev_state.pos, None
    return intended_pos, verdict


def live_move_note(
    *, alternative: str = "느린 포지션 페이드 또는 어두운 창 확보를 위한 구조 재배치"
) -> str:
    """REQ-066 — ``live`` 판정 설명에 붙는 ``live_move`` 표시 + 대안 제안
    문장. 조용히 넘어가지 않는다."""
    return f"{LIVE_MOVE_ANNOTATION} — {alternative}"
