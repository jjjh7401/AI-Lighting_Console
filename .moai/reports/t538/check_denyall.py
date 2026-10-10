"""t538 전부-거절 검사 — 실행 0 · 요청 문면 = 리허설 · 금지어 0.

실행: uv run python .moai/reports/t538/check_denyall.py
"""

import hashlib
import json
from pathlib import Path

base = Path(".moai/reports/t538")
deny = json.loads((base / "denyall/result.json").read_text("utf-8"))
reh = json.loads((base / "rehearse/approvals.json").read_text("utf-8"))

print("verdict:", deny.get("verdict"), "| preflight:", deny.get("preflight"))
print("occupied_before:", deny.get("occupied_before"))
bundles = deny.get("bundles", {})
print("bundles:", len(bundles), "executed:", sum(1 for v in bundles.values() if v))
reqs = deny["approval_requests"]
print("requests:", len(reqs), "approved:", sum(1 for r in reqs if r.get("approved")))

same = [r["commands"] for r in reqs] == [r["commands"] for r in reh]
print("request text == rehearsal:", same)

audit_rows = []
for f in sorted((base / "denyall/audit").glob("*")):
    if f.is_file():
        audit_rows += [json.loads(x) for x in f.read_text("utf-8").splitlines() if x.strip()]
print("audit rows:", len(audit_rows), "| executed rows:",
      sum(1 for r in audit_rows if str(r.get("outcome", r.get("status", ""))).startswith("exec")))

lines = [c for r in reh for c in r["commands"]]
banned = [c for c in lines if c.split()[0] in ("SaveShow", "Delete", "Remove", "Master")]
print("lines:", len(lines), "| banned verbs:", banned)
text = "\n".join(lines) + "\n"
(base / "approval_t538.txt").write_text(text, "utf-8")
print("approval_t538.txt sha256:", hashlib.sha256(text.encode()).hexdigest())
