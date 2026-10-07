# ruff: noqa: E501 — 한국어 머리말
"""t520 프로브 S — Spiider 를 맨 `At 100`(t459 에서 감독이 켜짐을 확인한 꼴)으로 켠다(시퀀스 셋, 트래킹 분리).

근거(이미 있던 실측 — 다시 재기 전에 찾았어야 했다):
- .moai/reports/t459/verdict.md:62-63 — `Attribute 'Dimmer' At 100` 으로 만든 큐는 3D 에서 아무것도 안 보였고, 프로그래머
  `Fixture 521 Thru 522 ; At 100` 은 둘 다 켜졌다(감독 확인). 「Spiider 에서 `Attribute 'Dimmer' At 100` 은 불을 켜지 못하고
  `At 100` 은 켠다(t442 와 같은 형태)」. .moai/reports/t442/verdict.md:95 — `Fixture 521 Thru 522 ; At 100 ; ` + 색 줄.

  266 큐1 'Group 12 At'      `Group 12 ; At 100`
  267 큐1 'Spiider Thru At'  `Fixture 521 Thru 528 ; At 100`
  268 큐1 'Spiider At RGB'   `Fixture 521 Thru 528 ; At 100 ; ColorRGB_R/G/B At 100`
이름 'FIXTURE PROBE - SPIIDER <꼴>'. 번호 266~268(path segment not found 확인). 쇼 저장 없음.
저장은 group_probe2.py(store 단계), 재생은 step_replay.py --target s(대화형).

실행: uv run python .moai/reports/t520/spiider_probe.py <출력폴더> --phase <all|store|p266|p267|p268> [--rehearse | --approve <전부-거절 폴더>]
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
    reason="t520 프로브 S — 빈 번호 266~268 생성·재생(Spiider 맨 At 100)", kind="t520_spiider_probe"
)
RGB = (
    "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 100"
)
g.PROBES = [
    (266, "Group 12 At", "Group 12 ; At 100", "FIXTURE PROBE - SPIIDER GROUP 12 AT"),
    (267, "Spiider Thru At", "Fixture 521 Thru 528 ; At 100", "FIXTURE PROBE - SPIIDER THRU AT"),
    (
        268,
        "Spiider At RGB",
        f"Fixture 521 Thru 528 ; At 100 ; {RGB}",
        "FIXTURE PROBE - SPIIDER AT RGB",
    ),
]

if __name__ == "__main__":
    sys.exit(g.main())
