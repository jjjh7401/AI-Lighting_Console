"""리허설 approvals.json → 승인 목록 txt + sha256. 실행: uv run python .moai/reports/t538/write_approval.py <rehearse_dir> <out.txt>"""

import hashlib
import json
import sys

reqs = json.load(open(f"{sys.argv[1]}/approvals.json", encoding="utf-8"))
text = "".join(c + "\n" for r in reqs for c in r["commands"])
open(sys.argv[2], "w", encoding="utf-8").write(text)
print(len(text.splitlines()), hashlib.sha256(text.encode()).hexdigest())
