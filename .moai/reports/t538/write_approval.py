"""리허설 approvals.json → 승인 목록 txt + sha256.

실행: uv run python .moai/reports/t538/write_approval.py <rehearse_dir> <out.txt>
"""

import hashlib
import json
import sys
from pathlib import Path

reqs = json.loads(Path(f"{sys.argv[1]}/approvals.json").read_text("utf-8"))
text = "".join(c + "\n" for r in reqs for c in r["commands"])
Path(sys.argv[2]).write_text(text, "utf-8")
print(len(text.splitlines()), hashlib.sha256(text.encode()).hexdigest())
