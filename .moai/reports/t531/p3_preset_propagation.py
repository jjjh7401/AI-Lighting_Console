"""P3 — 프리셋을 고치면 그걸 참조하는 큐에 전파되는가.

새 번호: Color 풀(4) 프리셋 301(새) · 시퀀스 300(새, 큐 1 이 프리셋 301 을 참조).
기존 Color 프리셋(1~10,32)은 전혀 건들지 않는다.

순서: (a) 프리셋 301 저장(기존 프리셋 4.9 'Breathe Warm' 을 베이스로 recall 한 뒤 Store —
프리셋을 "복제해서 새 번호에 저장"하는 가장 가까운 측정 경로) (b) 그 프리셋을 참조하는
큐를 시퀀스 300 에 저장 (c) 프리셋 301 의 내용을 다시 고친다 (d) 큐를 다시 읽어
내용이 바뀌었는지 비교.

PASS/FAIL: (c) 전/후 ``Sequence 300/1``(큐 1) 의 ``MEMORYFOOTPRINT`` 또는
``PRESETDATA`` 읽기가 달라지는가. 감독 관찰 필수: 큐가 활성 상태일 때 프리셋을
고치면 무대 색이 즉시 바뀌는지(라이브 전파) — 기계 판독만으로는 "저장된 값이
바뀌었다"와 "재생 중에도 즉시 바뀐다"를 못 가른다.

🔴 미측정 문법: (c) 프리셋 수정 줄(``Set Preset 4.301 Property ...`` 또는
``Store Preset 4.301 /Merge``) 은 이 리포에 측정 전례가 없다 — grandMA3 일반
문법 추정이며 live 실행 전 더 작은 묶음으로 먼저 확인해야 한다.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, preset_path, seq_path  # noqa: E402

POOL_COLOR = 4
PRESET_NO = 301
SEQ_NO = 300
# t531 v2: 감독 눈에 보였던 그룹(Group 11 MOVER-U, t516 verdict.md:264)으로 교체
# Group 4 BACK 은 t516 에서 안 보였다(:134-138, :219-220)
GROUP_BACK = 11


def build_plan() -> list[tuple[str, list[str]]]:
    return [
        (
            "store_preset",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP_BACK}",
                f"Attribute 'Color' At Preset {POOL_COLOR}.9",  # 기존 'Breathe Warm' 를 베이스로
                f"Store Preset {POOL_COLOR}.{PRESET_NO}",
                f"Set Preset {POOL_COLOR}.{PRESET_NO} Property 'Name' 'LDBEAT M1 - P3 propagation'",
                "ClearAll",
            ],
        ),
        (
            "store_cue",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP_BACK}",
                f"Attribute 'Color' At Preset {POOL_COLOR}.{PRESET_NO}",
                f"Store Sequence {SEQ_NO} Cue 1 'LDBEAT M1 - P3 ref cue'",
                f"Set Sequence {SEQ_NO} Property 'Name' 'LDBEAT M1 - P3 preset propagation'",
                "ClearAll",
            ],
        ),
        (
            # 🔴 미측정 — 프리셋 내용을 바꾸는 가장 가까운 형태. live 전엔 더 작게 쪼개 확인.
            "edit_preset",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {GROUP_BACK}",
                f"Attribute 'Color' At Preset {POOL_COLOR}.5",  # 'Deep Purple' 로 내용 교체
                f"Store Preset {POOL_COLOR}.{PRESET_NO} /Merge",
                "ClearAll",
            ],
        ),
        ("off", ["ClearAll"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="P3",
            risk_reason="t531 M1 P3 — Color 프리셋 301(새), 시퀀스 300(새)이 참조, 전파 확인",
            build_plan=build_plan,
            free_slots=[preset_path(POOL_COLOR, PRESET_NO), seq_path(SEQ_NO)],
            extra_notes=[
                "edit_preset 묶음의 '/Merge' 문법은 미측정 — live 전 단독으로 먼저 확인.",
                "읽기 판정: edit_preset 전/후 Sequence 300/1 의 PRESETDATA·MEMORYFOOTPRINT 대조.",
                "감독 관찰: 큐 활성 중 프리셋 수정 시 무대가 즉시 바뀌는지.",
            ],
        )
    )
