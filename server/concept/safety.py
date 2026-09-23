"""안전 큐(첫 큐·마지막 큐) — SPEC-LDDESIGN-001 M5 (REQ-LDDESIGN-068~069).

두 함수 모두 큐 스펙(``tracking``·``ops``)만 낸다 — 실제 해석은 기존
:func:`server.concept.resolver.apply` 를 그대로 통과한다(새 해석 경로를
만들지 않는다). 마지막 안전 큐는 ``reduce factor=0`` 으로 전 그룹을
끈다(REQ-069) — 호출자가 전 그룹을 담은 기준 상태(``ref``)를
``bases`` 에 등록해 둬야 ``apply()`` 가 그 그룹 전부를 0으로 되돌린다
(``reduce`` 는 참조한 기준 상태에 있는 그룹만 다룬다).
"""

from __future__ import annotations

__all__ = ["first_safety_cue", "last_safety_cue"]


def first_safety_cue(
    *, default_color: str, min_dimmer: int = 10, min_group: str = "KEY"
) -> dict[str, object]:
    """REQ-LDDESIGN-068 — 곡의 첫 큐(안전, Q0.5): ``Block`` 트래킹,
    최소 조명(기본 KEY 10%), 기본 색, 포지션 홈을 명시한다."""
    return {
        "tracking": "block",
        "ops": [
            {"op": "replace", "color": default_color},
            {
                "op": "expand",
                "roles": [min_group],
                "dimmer": min_dimmer,
                "pos": "home",
                "motion": 0,
            },
        ],
    }


def last_safety_cue(*, ref: str) -> dict[str, object]:
    """REQ-LDDESIGN-069 — 곡의 마지막 큐(안전): 모든 그룹을 끄고
    (``reduce factor=0``, ``ref`` 를 통해) ``Release`` 트래킹으로 제어를
    반환한다.

    Args:
        ref: ``bases`` 에 등록된, 끄고자 하는 전 그룹을 포함한 기준 상태의
            이름. ``reduce`` 는 이 기준 상태에 있는 그룹만 0으로 되돌리므로
            (``apply()`` 의 ``reduce`` 동작), 호출자는 곡 전체 리그 그룹을
            담은 상태를 이 이름으로 미리 등록해 둬야 한다.
    """
    return {
        "tracking": "release",
        "ops": [{"op": "reduce", "factor": 0.0, "ref": ref}],
    }
