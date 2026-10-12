"""t494: drift 기록마다 spec.md 커밋 수를 낡은 로컬 main 과 origin/main 에서 센다."""

import json
import subprocess
import sys

path = sys.argv[1] if len(sys.argv) > 1 else ".moai/reports/t494/drift.json"
with open(path, encoding="utf-8") as fh:
    recs = json.load(fh)["Records"]


def count(ref, sid):
    out = subprocess.run(
        ["git", "log", "--oneline", ref, "--", f".moai/specs/{sid}/spec.md"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return len(out.splitlines())


for r in recs:
    if r["GitImpliedStatus"] in ("era-exempt", "terminal-exempt"):
        continue
    sid = r["SPECID"]
    m, o = count("main", sid), count("origin/main", sid)
    flag = "STALE-GAP" if o > m else ""
    status = f"fm={r['FrontmatterStatus']:11} git={r['GitImpliedStatus']:11}"
    print(f"{sid:32} {status} drifted={r['Drifted']!s:5} main={m:3} origin={o:3} {flag}")
