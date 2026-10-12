"""t494: drift 출력 기록과 .moai/specs 디렉터리를 전수 대조한다."""
import collections
import json
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else ".moai/reports/t494/drift.json"
d = json.load(open(path))
recs = d["Records"]
ids = {r["SPECID"] for r in recs}
dirs = sorted(x for x in os.listdir(".moai/specs") if x.startswith("SPEC-"))
print("records", len(recs), "unique", len(ids), "dirs", len(dirs))
print("missing:", [x for x in dirs if x not in ids])
print("extra:", sorted(ids - set(dirs)))
print("keys:", list(d.keys()))
print(collections.Counter((r["FrontmatterStatus"], r["GitImpliedStatus"], r["Drifted"]) for r in recs))
