"""drift 기록 수를 SPEC 디렉터리 목록과 대조하고, 대상 두 SPEC 의 기록과 audit 판정을 출력한다."""

import glob
import json
import os
import sys
from pathlib import Path

drift = json.loads(Path(sys.argv[1]).read_text())
recs = drift if isinstance(drift, list) else next(v for v in drift.values() if isinstance(v, list))
ids = {r["SPECID"] for r in recs}
dirs = {os.path.basename(p) for p in glob.glob(".moai/specs/SPEC-*") if os.path.isdir(p)}
print("records", len(ids), "dirs", len(dirs))
print("missing", sorted(dirs - ids))
targets = ("SPEC-LDBEAT-001", "SPEC-LDDESIGN-001")
for r in recs:
    if r["SPECID"] in targets:
        print("drift", r)

if len(sys.argv) > 2:
    audit = json.loads(Path(sys.argv[2]).read_text())

    def walk(o):
        if isinstance(o, dict):
            if any(isinstance(v, str) and v in targets for v in o.values()):
                print("audit", {k: v for k, v in o.items() if not isinstance(v, (list, dict))})
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(audit)
