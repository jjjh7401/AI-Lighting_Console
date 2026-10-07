# ruff: noqa: E501 — 근거(경로·판독값)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t519 248 다시 보기 — 쓰기 없음. BACK 201 높이 시험(d1) 뒤에 감독이 3D 화면에서 본다.

248(`RHYTHM PROBE v5 - F1 AURA DIMMER 100`)은 201·201.1·301·301.1 에 Dimmer 100 만 준다
(`.moai/reports/t516/approval_rhythm_probe_v5.txt:30-33`). 301 은 대조군(이미 켜지는 것으로 관찰됨).
3초 여유 → `Goto Cue 1 Sequence 248` → 20초 → `Off Sequence 248`.
재생기는 t516 `replay_v5.py` 를 그대로 쓰고, 이름 사전 판독이 v5 이름과 다르면 재생하지 않는다.

실행: uv run python .moai/reports/t519/replay_248.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
"""

import sys

sys.path.insert(0, ".moai/reports/t516")
import replay_v5  # noqa: E402

replay_v5.LEAD_IN = 3.0
replay_v5.TIMELINE = [
    (
        "on_248",
        ["Goto Cue 1 Sequence 248"],
        20.0,
        "BACK 201(높이 1.2) 이 보이는가 · 301 대조(20초)",
    ),
    ("off_248", ["Off Sequence 248"], 0.0, ""),
]
replay_v5.EXPECTED = {248: replay_v5.EXPECTED[248]}

if __name__ == "__main__":
    sys.exit(replay_v5.main())
