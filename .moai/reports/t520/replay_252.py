# ruff: noqa: E501 — 한국어 머리말
"""t520 프로브 A 큐1 다시 보기 — 쓰기 없음.

리드 지시(2026-10-07, 감독이 큐1 을 못 봄):
5초 여유 → `Goto Cue 1 Sequence 252` → 15초 → `Off Sequence 252` 2줄만.
재생기는 t516 `replay_v5.py` 를 그대로 쓰고 재생 목록·이름 대조 대상·여유 시간·위험 표지만 바꾼다(t516 replay_245.py 와 같은 방식).
이름 사전 판독이 'LINE SHAPE PROBE - MAIN SUB LONG' 이 아니면 재생하지 않는다.

실행: uv run python .moai/reports/t520/replay_252.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
"""

import sys

sys.path.insert(0, ".moai/reports/t516")
import replay_v5  # noqa: E402
import tc_probe  # noqa: E402

from server.safety.gate import BatchRisk  # noqa: E402

tc_probe.RISK = BatchRisk(
    reason="t520 프로브 A 큐1 다시 보기 — 재생만(쓰기 없음)", kind="t520_replay_252"
)
replay_v5.LEAD_IN = 5.0
replay_v5.TIMELINE = [
    ("on_252_cue1", ["Goto Cue 1 Sequence 252"], 15.0, "큐1 — 본체 301·302 만 Dimmer 100(15초)"),
    ("off_252", ["Off Sequence 252"], 0.0, ""),
]
replay_v5.EXPECTED = {252: "LINE SHAPE PROBE - MAIN SUB LONG"}

if __name__ == "__main__":
    sys.exit(replay_v5.main())
