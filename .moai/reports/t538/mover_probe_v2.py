"""t538 v2 — A 항목을 2단계로 다시 쓴 묶음 + A6·B(문면 그대로, 번호만 옮김).

원인(감독 판정 2026-10-10, 리드 경유): 1단계 상대값은 페이저가 아니다(T3 정지).
2단계 상대 Tilt + Phase 0 Thru 360 + Speed 112 는 물결로 움직였다(T4, Fixture 501~508 선택, MegaPointe).
그래서 새 양성 대조 A0′ 는 T4 몸통을 시퀀스로 저장한 것이고, A1~A5 는 A0′ 에서 한 가지씩만 바꾼다.

번호 312~322(311 은 1단계 A0 가 쓰고 있다). A6·B 의 문면은 mover_probe.py 와 같고 번호만 다르다.
쇼 저장 0. 실행은 리드 경유 감독 승인 뒤.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
sys.path.insert(0, ".moai/reports/t538")
import mover_probe as v1  # noqa: E402
from m1_common import main_cli, seq_path  # noqa: E402

FIX = v1.FIX
GROUP = v1.GROUP

# v1 의 함수들(_store·_play·plan_b)이 이 사전을 읽으므로 같은 객체를 고쳐 쓴다.
v1.SEQ.clear()
v1.SEQ.update(
    A0=312, A1=313, A2=314, A3=315, A4=316, A5=317,
    A6a=318, A6b=319, B1=320, B2=321, B3=322,
)
SEQ = v1.SEQ


def _two_step(
    *,
    sel: str = FIX,
    base: str | None = "Attribute 'Tilt' At 45",
    size: int = 30,
) -> list[str]:
    """T4 몸통(t516 v4:30-36 = approval_t45.txt t4_prog). 인자 하나만 바꿔 A1~A4 를 만든다."""
    lines = ["ChangeDestination Root", "ClearAll", f"{sel} ; Attribute 'Dimmer' At 70"]
    if base is not None:
        lines.append(f"{sel} ; {base}")
    lines += [
        f"{sel} ; Attribute 'Tilt' At Relative -{size}",
        "Step 2",
        f"Attribute 'Tilt' At Relative {size}",
        "Attribute 'Tilt' At Phase 0 Thru 360",
        "Attribute 'Tilt' At Speed 112",
    ]
    return lines


def plan_a() -> list[tuple[str, list[str]]]:
    plan: list[tuple[str, list[str]]] = []
    items = [
        ("A0", "two step T4", _two_step()),
        ("A1", "group 11", _two_step(sel=GROUP)),
        ("A2", "relative 12", _two_step(size=12)),
        ("A3", "base preset 2-1", _two_step(base="At Preset 2.1")),
        ("A4", "no base", _two_step(base=None)),
        (
            # Pan+Tilt 2단계, 축 사이 위상 90(앱 circle 패턴, instantiate.py _phase_lines).
            # 곡선 줄은 넣지 않는다 — A0′ 에서 바꾸는 것을 「축 추가」 하나로 둔다.
            "A5",
            "pan tilt circle",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"{FIX} ; Attribute 'Dimmer' At 70",
                f"{FIX} ; Attribute 'Tilt' At 45",
                f"{FIX} ; Attribute 'Pan' At Relative -30",
                f"{FIX} ; Attribute 'Tilt' At Relative -30",
                "Step 2",
                "Attribute 'Pan' At Relative 30",
                "Attribute 'Tilt' At Relative 30",
                "Attribute 'Pan' At Phase 0",
                "Attribute 'Tilt' At Phase 90",
                "Attribute 'Pan' At Speed 112",
                "Attribute 'Tilt' At Speed 112",
            ],
        ),
        (
            "A6a",
            "fx preset 21-2 PT-CIRCLE",
            ["ChangeDestination Root", "ClearAll", f"{GROUP} ; Attribute 'Dimmer' At 70", "At Preset 21.2"],
        ),
        (
            "A6b",
            "fx preset 21-5 TILT-SWEEP",
            ["ChangeDestination Root", "ClearAll", f"{GROUP} ; Attribute 'Dimmer' At 70", "At Preset 21.5"],
        ),
    ]
    for item, text, body in items:
        plan.append((f"store_{item}", [*body, *v1._store(item, text)]))
        plan += v1._play(item)
    return plan


def build_plan() -> list[tuple[str, list[str]]]:
    return [*plan_a(), *v1.plan_b()]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T538v2",
            risk_reason="t538 v2 — 시퀀스 312~322(새), 2단계 A0′~A5 + A6 + 위치 큐 B1~B3",
            build_plan=build_plan,
            free_slots=[seq_path(n) for n in SEQ.values()],
            extra_notes=[
                "A0′ = T4(감독 「물결처럼 움직임」) 몸통을 시퀀스로 저장. A0′ 가 안 움직이면 저장·재생 경로 쪽 — 나머지 중단.",
                "A6·B 문면은 mover_probe.py 와 같고 번호만 다름.",
            ],
        )
    )
