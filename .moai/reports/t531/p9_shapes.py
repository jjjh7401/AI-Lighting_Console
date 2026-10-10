"""P9 — circle/ballyhoo/phase-spread(wave) 모양이 실제로 저장·재생되는가.

새 번호: 시퀀스 306(circle)·307(ballyhoo)·308(wave), 전부 새 번호. 그룹 MOVER-ALL(13).

🔴 미측정 매핑: ``server/spatial/position_fx.py`` 의 ``position_fx_commands()``
는 FX_POSITION_SEQUENCE 스켈레톤 프리셋(라벨 'Circle Base'/'Bally Base'/
'Floor Base')과 Fixture-ID 선택을 전제한다. 이 쇼엔 그 스켈레톤 프리셋이 없고
(r0c_presets.txt — Position 풀엔 POS01~06·Home/Wall/Audience/Center 뿐), 이
세션은 실측 Fixture ID 목록도 갖고 있지 않다. 그래서 이 프로브는
``position_fx_commands()`` 를 직접 호출하지 않고, 그 모듈이 쓰는 **측정된
상수**(circle: Pan±12/Tilt±8, Phase 0/90 · ballyhoo: Pan±20/Tilt±10,
BALLYHOO_SPEED_FACTOR=2 · wave: Tilt±12, Phase 0 Thru 360)를 그대로 가져와
기존 Position 프리셋 2.1 위에 Group 선택으로 얹는다 — "position_fx.py 가 설계한
세 모양이 콘솔에 저장·재생되는가"는 답하지만 "그 모듈 함수 자체가 라이브로
도는가"는 답하지 않는다. probe-design.md 「안 잰 것」에 기록.

PASS/FAIL: 세 큐 각각 저장 뒤 introspect 로 Pan/Tilt 속성이 페이저로(정적이 아니라)
저장됐는지. 감독 관찰 필수: 세 모양이 서로 다르게 보이는지(원형/엇갈린 궤도/스윕).
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

GROUP_MOVER_ALL = 13
POS_POOL = 2
BASE_PRESET = 1
SEQ = dict(circle=306, ballyhoo=307, wave=308)


def _base(seq_no: int, name: str) -> list[str]:
    return [
        "ChangeDestination Root",
        "ClearAll",
        f"Group {GROUP_MOVER_ALL}",
        f"Attribute 'Position' At Preset {POS_POOL}.{BASE_PRESET}",
    ]


def build_plan() -> list[tuple[str, list[str]]]:
    circle = [
        *_base(SEQ["circle"], "circle"),
        "Attribute 'Pan' At Relative 12",
        "Attribute 'Tilt' At Relative 8",
        "Attribute 'Pan' At Phase 0",
        "Attribute 'Tilt' At Phase 90",
        "Attribute 'Pan' At Speed 60",
        "Attribute 'Tilt' At Speed 60",
        f"Store Sequence {SEQ['circle']} Cue 1 'LDBEAT M1 - P9 circle'",
        f"Set Sequence {SEQ['circle']} Property 'Name' 'LDBEAT M1 - P9 circle'",
        "ClearAll",
    ]
    ballyhoo = [
        *_base(SEQ["ballyhoo"], "ballyhoo"),
        "Attribute 'Pan' At Relative 20",
        "Attribute 'Tilt' At Relative 10",
        "Attribute 'Pan' At Phase 0",
        "Attribute 'Tilt' At Phase 90",
        "Attribute 'Pan' At Speed 120",  # BALLYHOO_SPEED_FACTOR=2 x 기본 60
        "Attribute 'Tilt' At Speed 120",
        f"Store Sequence {SEQ['ballyhoo']} Cue 1 'LDBEAT M1 - P9 ballyhoo'",
        f"Set Sequence {SEQ['ballyhoo']} Property 'Name' 'LDBEAT M1 - P9 ballyhoo'",
        "ClearAll",
    ]
    wave = [
        *_base(SEQ["wave"], "wave"),
        "Attribute 'Tilt' At Relative 12",
        "Attribute 'Tilt' At Phase 0 Thru 360",
        "Attribute 'Tilt' At Speed 60",
        f"Store Sequence {SEQ['wave']} Cue 1 'LDBEAT M1 - P9 wave'",
        f"Set Sequence {SEQ['wave']} Property 'Name' 'LDBEAT M1 - P9 wave'",
        "ClearAll",
    ]
    return [
        ("store_circle", circle),
        ("store_ballyhoo", ballyhoo),
        ("store_wave", wave),
        (
            "play_each",
            [
                f"Goto Cue 1 Sequence {SEQ['circle']}",
                f"Off Sequence {SEQ['circle']}",
                f"Goto Cue 1 Sequence {SEQ['ballyhoo']}",
                f"Off Sequence {SEQ['ballyhoo']}",
                f"Goto Cue 1 Sequence {SEQ['wave']}",
            ],
        ),
        ("release", [f"Off Sequence {s}" for s in SEQ.values()]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P9",
            risk_reason="t531 M1 P9 — 시퀀스 306/307/308(새), circle/ballyhoo/wave 모양",
            build_plan=build_plan,
            free_slots=[seq_path(n) for n in SEQ.values()],
            extra_notes=[
                "position_fx_commands() 는 호출하지 않음(스켈레톤 프리셋·픽스처ID 미확보).",
                "그 모듈의 측정 상수만 재사용 — 「안 잰 것」: 모듈 함수 자체의 라이브 동작.",
                "감독 관찰 필수: 세 모양이 서로 다르게 보이는지.",
            ],
        )
    )
