# ruff: noqa: E501 — 한국어 머리말
"""t520 프로브 F — Spiider(G12)·Rush Par(G10)가 안 켜지는 까닭을 가른다(시퀀스 여섯, 각 큐 1개·10초).

근거(읽기, spiider_readonly.txt · spiider2_readonly.txt · rush3_readonly.txt):
- Spiider(Robin Spiider, 모드 「1 Mode 1」, 서브 3): 디머 채널 셋 — RGBW Cluster_Dimmer(기본 FF) · Main Module_Dimmer(기본 FF) ·
  Main Module_Dimmer2(기본 00) — 셋 다 속성 이름이 `Dimmer` 다. 셔터 둘(Shutter1·Shutter2, 속성 이름 둘 다 `Shutter1`)
  기본 0x30 = open 구간(32~63). 그래서 ③ 「다른 디머 속성 이름」은 쓸 이름이 없다 → ③ 은 ② + 색 R/G/B 100 으로 둔다.
- Rush Par(모드 「2 9 channel」): Dimmer 기본 00 · Shutter1 기본 12 = open · COLORMIXER 속성 `ColorMacro` 기본 0 = Normal ·
  Zoom 기본 0x80(물리 60°→10°, 100 = 10° 가장 좁음) · RGB 기본 FF · W 00.

  257 ① 'G12 Dimmer'          `Group 12 ; Attribute 'Dimmer' At 100`
  258 ② 'Spiider Dot'         `Fixture 521 Thru 528. ; Attribute 'Dimmer' At 100`
  259 ③ 'Spiider Dot RGB'     ② + `ColorRGB_R/G/B At 100`
  263 ④ 'G10 Dimmer'          `Group 10 ; Attribute 'Dimmer' At 100`
  264 ⑤ 'G10 RGB Macro'       ④ + `ColorRGB_R/G/B At 100` + `ColorMacro At 0`
  265 ⑥ 'Wash 401 Zoom'       `Fixture 401 ; Attribute 'Dimmer' At 100 ; Attribute 'Zoom' At 100`
이름 'FIXTURE PROBE - <꼴>'. 쓰는 번호는 여섯뿐(260~262 는 t519 사용 중). 쇼 저장 없음. 실행기는 group_probe2.py(PROBES 만 바꿈),
단계 store → p257 → p258 → p259 → p263 → p264 → p265, 재생 직전마다 리드에게 「지금 ①」 식으로 알린다.

실행: uv run python .moai/reports/t520/fixture_probe.py <출력폴더> --phase <all|store|p257|…> [--rehearse | --approve <전부-거절 폴더>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만.
"""

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t520")
import group_probe2 as g  # noqa: E402
import tc_probe  # noqa: E402

from server.safety.gate import BatchRisk  # noqa: E402

tc_probe.RISK = BatchRisk(
    reason="t520 프로브 F — 빈 번호 257·258·259·263·264·265 생성·재생(Spiider·Rush Par 점등 가르기)",
    kind="t520_fixture_probe",
)
RGB = (
    "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 100"
)
g.HOLD = 10.0
g.PROBES = [
    (257, "G12 Dimmer", "Group 12 ; Attribute 'Dimmer' At 100", "FIXTURE PROBE - GROUP 12 DIMMER"),
    (
        258,
        "Spiider Dot",
        "Fixture 521 Thru 528. ; Attribute 'Dimmer' At 100",
        "FIXTURE PROBE - SPIIDER TRAILING DOT",
    ),
    (
        259,
        "Spiider Dot RGB",
        f"Fixture 521 Thru 528. ; Attribute 'Dimmer' At 100 ; {RGB}",
        "FIXTURE PROBE - SPIIDER DOT RGB",
    ),
    (263, "G10 Dimmer", "Group 10 ; Attribute 'Dimmer' At 100", "FIXTURE PROBE - GROUP 10 DIMMER"),
    (
        264,
        "G10 RGB Macro",
        f"Group 10 ; Attribute 'Dimmer' At 100 ; {RGB} ; Attribute 'ColorMacro' At 0",
        "FIXTURE PROBE - GROUP 10 RGB MACRO",
    ),
    (
        265,
        "Wash 401 Zoom",
        "Fixture 401 ; Attribute 'Dimmer' At 100 ; Attribute 'Zoom' At 100",
        "FIXTURE PROBE - WASH 401 ZOOM",
    ),
]

if __name__ == "__main__":
    sys.exit(g.main())
