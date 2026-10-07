# ruff: noqa: E501 — 한국어 머리말·안내 문구라 줄 길이 규칙을 끈다
"""t520 프로브 G — 기존 그룹 선택이 서브픽스처 디머까지 여는가(Seq 255 큐 1개).

까닭: 프로브 A 큐1 `Fixture 301 + 302 ; Dimmer 100` 무점등(감독 「안켜졌어」) — Aura XB 는 본체 선택만으로
서브픽스처 디머가 안 열린다. 감독(원문): 「여러대의 장비를 작동하려면 그룹을 만들어서 사용하면 되잖아」.
앱 Seq 219 도 `Group N ; Attribute …` 꼴을 쓴다(t516 line_shapes: 219 에 110줄).

  큐 1 'Group Five'  `Group 5 ; Attribute 'Dimmer' At 100` — 그룹 5(SIDE-L, Aura XB 301~306)
재생: 5초 여유 → `Goto Cue 1 Sequence 255` → 15초 → `Off Sequence 255`. 감독이 무대 왼쪽 뒤 기둥(301·302)을 본다.
그룹 5 의 구성원(서브픽스처 포함 여부)은 응답기로 읽을 수 없다(t516 §4-3: 그룹 COUNT 늘 0). 그래서 눈으로 가른다.
이름 'GROUP PROBE - GROUP 5 SIDE-L'. 쓰는 번호 255 만. 쇼 저장 없음.

실행: uv run python .moai/reports/t520/group_probe.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t520")
import line_probe  # noqa: E402
import tc_probe  # noqa: E402

from server.safety.gate import BatchRisk  # noqa: E402

tc_probe.RISK = BatchRisk(
    reason="t520 프로브 G — 빈 번호 255 생성·재생(그룹 5 선택)", kind="t520_group_probe"
)
line_probe.SEQ_NO = 255
line_probe.SEQ_PATH = f"{line_probe.POOL}/Sequences/255"
line_probe.B_SLOTS = []
line_probe.HOLD, line_probe.GAP = 15.0, 0.0
LEAD_IN = 5.0
line_probe.CUES = [
    (
        1,
        "Group Five",
        "Group 5 ; Attribute 'Dimmer' At 100",
        "큐 1 — 그룹 5(SIDE-L) Dimmer 100. 무대 왼쪽 뒤 기둥 301·302 가 켜지는가(15초)",
    ),
]


def bundles() -> list[tuple[str, list[str], float, str]]:
    return [
        (
            "store_1",
            [
                "ChangeDestination Root",
                "ClearAll",
                "Group 5 ; Attribute 'Dimmer' At 100",
                "Store Sequence 255 Cue 1 'Group Five'",
                "ClearAll",
                "Set Sequence 255 Property 'Name' 'GROUP PROBE - GROUP 5 SIDE-L'",
            ],
            LEAD_IN,
            "",
        ),
        ("on_1", ["Goto Cue 1 Sequence 255"], 15.0, line_probe.CUES[0][3]),
        ("off_1", ["Off Sequence 255"], 0.0, ""),
    ]


line_probe.bundles = bundles

if __name__ == "__main__":
    sys.exit(line_probe.main())
