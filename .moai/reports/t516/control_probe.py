"""t516 대조 재생 P1~P3 — 쓰기 없음. 다시 보기에서 조명이 안 켜진 원인을 가른다.

P1 대조군: 앱 연출 시퀀스 219 큐 Intro(내용이 큰 큐, MEMORYFOOTPRINT 17192B) 8초
P2: 시퀀스 220 큐 1(BACK 30%) 8초
P3: 시퀀스 221 큐 1(BACK 1박 펄스) 8초
각각 끄고 2초 쉰다. 219 만 켜지면 원인은 우리 큐 내용, 219 도 안 켜지면 출력·화면 쪽.

replay_probe.py 의 실행 틀(사전 판독·리허설·전부-거절·승인)을 그대로 쓰고 재생 목록만 바꾼다.
🔴 리드의 「실행」 메시지 뒤에만 --approve 로 돌린다.

실행: uv run python .moai/reports/t516/control_probe.py <출력폴더>
      [--rehearse | --approve <전부-거절 폴더>]
"""

import sys

sys.path.insert(0, ".moai/reports/t516")
import replay_probe  # noqa: E402
import tc_probe  # noqa: E402

from server.safety.gate import BatchRisk  # noqa: E402

tc_probe.RISK = BatchRisk(reason="t516 대조 재생 P1~P3 — 쓰기 없음", kind="t516_control")
HOLD, GAP = replay_probe.HOLD, replay_probe.GAP
replay_probe.TIMELINE = [
    (
        "p1_on",
        ["Goto Cue 1 Sequence 219"],  # 큐 번호 1 = Intro(상태 목록에선 OffCue·CueZero 뒤 3번째)
        HOLD,
        "P1 대조군 — 시퀀스 219 Intro(앱 연출)가 켜지는지",
    ),
    ("p1_off", ["Off Sequence 219"], GAP, ""),
    ("p2_on", ["Goto Cue 1 Sequence 220"], HOLD, "P2 — 시퀀스 220 BACK 30% 가 켜지는지"),
    ("p2_off", ["Off Sequence 220"], GAP, ""),
    ("p3_on", ["Goto Cue 1 Sequence 221"], HOLD, "P3 — 시퀀스 221 BACK 이 1박마다 깜빡이는지"),
    ("p3_off", ["Off Sequence 221"], 0.0, ""),
]

if __name__ == "__main__":
    sys.exit(replay_probe.main())
