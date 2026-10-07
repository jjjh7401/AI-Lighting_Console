"""t516 245 한 번 더 — 쓰기 없음.

리드 지시(2026-10-07, 감독 「245 다시」):
3초 여유 → `Goto Cue 1 Sequence 245` → 15초 → `Off Sequence 245`.
재생기는 `replay_v5.py` 를 그대로 쓰고 재생 목록·이름 대조 대상·여유 시간만 바꾼다.
이름 사전 판독이 v5 이름과 다르면 재생하지 않는다.

실행: uv run python .moai/reports/t516/replay_245.py <출력폴더>
      [--rehearse | --approve <전부-거절 폴더>]
"""

import sys

sys.path.insert(0, ".moai/reports/t516")
import replay_v5  # noqa: E402

replay_v5.LEAD_IN = 3.0
replay_v5.TIMELINE = [
    ("on_245", ["Goto Cue 1 Sequence 245"], 15.0, "E0 — 무빙 501~508 이 기울어졌는가(15초)"),
    ("off_245", ["Off Sequence 245"], 0.0, ""),
]
replay_v5.EXPECTED = {245: replay_v5.EXPECTED[245]}

if __name__ == "__main__":
    sys.exit(replay_v5.main())
