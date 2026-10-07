# ruff: noqa: E501 — 한국어 머리말
"""t520 프로브 W — 그룹 10(WASH-ALL, 바닥 워시 20대) 정적 Dimmer 100 하나(Seq 257 큐 1).

까닭: B 그룹판 시연에서 WASH 가 안 켜졌다(감독 「mover_u, Key 만 켜졌어」). 감독 확인: 「그룹 10은 바닥 워시 20대가 선택돼」.
판독(rush3_readonly.txt): Shutter1 기본 12 = open 구간, COLORMIXER 기본 0 = ColorMacro Normal, Zoom 기본 0x80 — 채널 기본값으로 막히는 건 없다.
남은 후보(추정): ROTX 180 으로 천정을 향해 빔이 닿는 면이 없어 3D 에서 안 보인다.

  Seq 257 큐1 'Wash All 100'  `Group 10 ; Attribute 'Dimmer' At 100` — 이름 'WASH PROBE - GROUP 10 DIMMER 100'
실행기는 group_probe2.py 를 그대로 쓰고 PROBES 만 바꾼다. 단계: store(257 빔 확인 → 저장) · p257(이름 확인 → Goto 15초 → Off) · all(리허설·전부-거절용).
감독이 볼 것: 바닥 워시 20대(무대 바닥, X −5~+5m, 앞·뒤 두 줄)의 렌즈가 켜지는지, 천정 쪽에 빛이 보이는지.

실행: uv run python .moai/reports/t520/g10_probe.py <출력폴더> --phase <all|store|p257> [--rehearse | --approve <전부-거절 폴더>]
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
    reason="t520 프로브 W — 빈 번호 257 생성·재생(그룹 10 정적)", kind="t520_wash_probe"
)
g.PROBES = [
    (
        257,
        "Wash All 100",
        "Group 10 ; Attribute 'Dimmer' At 100",
        "WASH PROBE - GROUP 10 DIMMER 100",
    )
]

if __name__ == "__main__":
    sys.exit(g.main())
