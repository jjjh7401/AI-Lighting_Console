"""t516 다시 보기 승인 파일 만들기 — 전부-거절 요청 문면을 주석 없는 맨 줄로 잇고, 리허설과 대조한다.

실행: uv run python .moai/reports/t516/write_replay_approval.py
"""

import json
from pathlib import Path

BASE = Path(".moai/reports/t516")
live = [q["commands"] for q in json.loads((BASE / "replay_denyall/approvals.json").read_text())]
fake = [q["commands"] for q in json.loads((BASE / "replay_rehearse/approvals.json").read_text())]
print("live == rehearsal", live == fake, len(live), len(fake))
lines = [c for cmds in live for c in cmds]
(BASE / "approval_replay.txt").write_text("".join(f"{c}\n" for c in lines), "utf-8")
print("approval lines", len(lines))
