"""t513 — 실기 전부-거절 회신에서 페이저·거절 관련 문장을 뽑는다.

실행: uv run python .moai/reports/t513/reply_notices.py <run 폴더>
"""

import json
import re
import sys
from pathlib import Path

replies = json.loads((Path(sys.argv[1]) / "replies.json").read_text("utf-8"))
text = " ".join(r or "" for r in replies).replace("\n", " ")
for key in ("페이저", "효과:", "사전 생성", "거부", "거절", "219", "타임코드"):
    for m in list(re.finditer(re.escape(key), text))[:2]:
        print(f"[{key}] …{text[max(0, m.start() - 100) : m.start() + 200]}…")
