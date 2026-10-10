"""P5 — 포지션 프리셋 위에 relative 무빙 이펙트를 얹기.

새 번호: 시퀀스 302(새). 기존 Position 프리셋 2.1('POS01 보컬 센터 페이스')을 베이스로
recall 한 뒤 그 위에 relative 페이저(Pan/Tilt At Relative + At Phase + At Speed)를
얹는다 — 베이스가 어디를 보든 그 자리를 중심으로 궤도를 돈다(center-follow).

🔴 미측정 매핑: ``server/spatial/position_fx.py`` 가 측정/검증한 recall 문법은
픽스처 ID 선택(``Fixture <id>+<id> ; At Preset 2.<n>``, ``pointing.py
preset_recall_command``)이다. 이 세션은 실측 픽스처 ID 목록을 갖고 있지 않으므로
그룹 선택(``Group 13`` MOVER-ALL)으로 대체했다 — Relative-on-preset 자체의 동작은
묻지만, "그룹 선택으로도 똑같이 되는가"는 이 프로브가 추가로 떠안는 변수다.
relative 페이저의 크기(Pan±12/Tilt±8, Phase 0/90)는 position_fx.py
``_relative_phaser_lines``(circle) 실측 상수를 그대로 가져왔다.

PASS/FAIL: 큐 재생 중 ``Group 13`` 의 ``PAN``/``TILT`` 가 베이스 프리셋 중심으로
흔들리는가(수치 판독으론 중심값이 베이스와 같은지만 확인). 감독 관찰 필수:
실제로 "프리셋이 가리키는 자리를 중심으로" 도는지(중심이 아니라 절대 0/0 기준으로
도는 회귀는 숫자로는 못 가른다).
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

SEQ_NO = 302
GROUP_MOVER_ALL = 13
POS_POOL = 2
BASE_PRESET = 1  # POS01 보컬 센터 페이스


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "store_cue",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP_MOVER_ALL}",
                f"Attribute 'Position' At Preset {POS_POOL}.{BASE_PRESET}",
                "Attribute 'Pan' At Relative 12",
                "Attribute 'Tilt' At Relative 8",
                "Attribute 'Pan' At Phase 0",
                "Attribute 'Tilt' At Phase 90",
                "Attribute 'Pan' At Speed 60",
                "Attribute 'Tilt' At Speed 60",
                f"Store Sequence {SEQ_NO} Cue 1 'LDBEAT M1 - P5 relative-on-preset'",
                f"Set Sequence {SEQ_NO} Property 'Name' 'LDBEAT M1 - P5 relative-on-preset'",
                "ClearAll",
            ],
        ),
        ("play", [f"Goto Cue 1 Sequence {SEQ_NO}"]),
        ("release", [f"Off Sequence {SEQ_NO}"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P5",
            risk_reason="t531 M1 P5 — 시퀀스 302(새), 포지션 프리셋 2.1 위 relative 페이저",
            build_plan=build_plan,
            free_slots=[seq_path(SEQ_NO)],
            extra_notes=[
                "Group 선택으로 대체(픽스처 ID 미확보) — position_fx.py 는 Fixture 선택 전제.",
                "감독 관찰 필수: 궤도 중심이 베이스 프리셋 방향인지.",
            ],
        )
    )
