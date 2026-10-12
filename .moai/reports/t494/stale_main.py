"""t494: drift 기록마다 그 SPEC 의 spec.md 커밋이 낡은 로컬 main 과 origin/main 에 몇 개씩 있는지 센다."""
import json
import subprocess
import sys

path = sys.argv[1] if len(sys.argv) > 1 else ".moai/reports/t494/drift.json"
recs = json.load(open(path))["Records"]


def count(ref, sid):
    out = subprocess.run(
        ["git", "log", "--oneline", ref, "--", f".moai/specs/{sid}/spec.md"],
        capture_output=True, text=True, check=False,
    ).stdout
    return len(out.splitlines())


for r in recs:
    if r["GitImpliedStatus"] in ("era-exempt", "terminal-exempt"):
        continue
    sid = r["SPECID"]
    m, o = count("main", sid), count("origin/main", sid)
    flag = "STALE-GAP" if o > m else ""
    print(f"{sid:32} fm={r['FrontmatterStatus']:11} git={r['GitImpliedStatus']:11} drifted={r['Drifted']!s:5} main={m:3} origin={o:3} {flag}")
