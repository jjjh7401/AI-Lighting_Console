"""t538 v3 — 승인 목록 하나로 합친 묶음: T4s·T5s(느린 비교) + v2(A0′~A6·B) + A5b.

리드 지시(2026-10-10):
- T5 감독 판정 「차이를 모르겠다」 — 112 BPM 은 왕복이 짧아 끝 꺾임이 안 보인다.
  그래서 느리게 다시 비교한다. T4s·T5s = T4·T5 와 같고
  `Attribute 'Tilt' At Speed 112` → `At Speed 30` 한 줄만 바꾼다. 프로그래머만, Store 0.
- A5(곡선 없음)과 A5b(A5 + 곡선 4줄) 둘 다 넣는다. A5b 는 새 번호 323(B 번호 320~322 는 그대로).
- A6 포함.

v2 의 문면은 바꾸지 않는다(mover_probe_v2.py 를 그대로 가져와 A5 뒤에 A5b 만 끼운다).
쇼 저장 0. 실행은 리드 경유 감독 승인 뒤.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
sys.path.insert(0, ".moai/reports/t538")
import mover_probe as v1  # noqa: E402
import mover_probe_v2 as v2  # noqa: E402  (import 하면 v1.SEQ 가 312~322 로 바뀐다)
import t4_t5_two_steps as t45  # noqa: E402
from m1_common import main_cli, seq_path  # noqa: E402

v1.SEQ["A5b"] = 323
SEQ = v1.SEQ

SLOW_TAIL = ["Attribute 'Tilt' At Phase 0 Thru 360", "Attribute 'Tilt' At Speed 30"]


def plan_slow() -> list[tuple[str, list[str]]]:
    assert t45.TAIL[1] == "Attribute 'Tilt' At Speed 112"  # 바꾸는 줄이 정말 이 한 줄인지
    return [
        ("t4s_prog", [*t45.STEPS, *SLOW_TAIL]),
        ("t4s_clear", ["ClearAll"]),
        ("t5s_prog", [*t45.STEPS, *t45.CURVE, *SLOW_TAIL]),
        ("t5s_clear", ["ClearAll"]),
    ]


def _a5b_body() -> list[str]:
    """v2 A5 몸통에 곡선 4줄을 단계 뒤·위상 앞에 끼운다.

    앱 순서 단계→곡선→위상→속도(instantiate.py:646)를 따른다.
    """
    a5 = dict(v2.plan_a())["store_A5"][:-3]  # Store / ClearAll / Set Name 제외
    cut = a5.index("Attribute 'Pan' At Phase 0")
    return [*a5[:cut], *t45.CURVE, *a5[cut:]]


def plan_a_v3() -> list[tuple[str, list[str]]]:
    plan: list[tuple[str, list[str]]] = []
    for label, cmds in v2.plan_a():
        plan.append((label, cmds))
        if label == "off_A5":
            plan.append(("store_A5b", [*_a5b_body(), *v1._store("A5b", "pan tilt circle curve")]))
            plan += v1._play("A5b")
    return plan


def build_plan() -> list[tuple[str, list[str]]]:
    return [*plan_slow(), *plan_a_v3(), *v1.plan_b()]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T538v3",
            risk_reason="t538 v3 — 느린 비교 T4s·T5s(프로그래머) + 시퀀스 312~323(새)",
            build_plan=build_plan,
            free_slots=[seq_path(n) for n in SEQ.values()],
            extra_notes=[
                "T4s·T5s 는 Store 0(프로그래머만), 판정 뒤 각 clear.",
                "v2 문면 그대로 + A5b(323) 추가.",
            ],
        )
    )
