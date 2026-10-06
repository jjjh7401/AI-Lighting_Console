"""t516 승인 파일 만들기(일반판) — 전부-거절 요청 문면을 맨 줄로 잇고 리허설 문면과 대조한다.

실행: uv run python .moai/reports/t516/write_approval.py <전부-거절 폴더> <리허설 폴더> <승인 파일>
"""

import json
import sys
from pathlib import Path

live_dir, fake_dir, out = (Path(a) for a in sys.argv[1:4])
live = [q["commands"] for q in json.loads((live_dir / "approvals.json").read_text())]
fake = [q["commands"] for q in json.loads((fake_dir / "approvals.json").read_text())]
print("live == rehearsal", live == fake, len(live), len(fake))
lines = [c for cmds in live for c in cmds]
out.write_text("".join(f"{c}\n" for c in lines), "utf-8")
print("approval lines", len(lines))
