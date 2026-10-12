"""t494: sync_commit_sha 를 가진 SPEC 들의 특성을 drift 포함 여부와 나란히 본다."""
import json
import os
import re

recs = {r["SPECID"]: r for r in json.load(open(".moai/reports/t494/drift.json"))["Records"]}
root = ".moai/specs"
for name in sorted(os.listdir(root)):
    d = os.path.join(root, name)
    prog = os.path.join(d, "progress.md")
    if not os.path.isfile(prog):
        continue
    text = open(prog, encoding="utf-8").read()
    m = re.search(r"^sync_commit_sha:\s*(\S+)", text, re.M)
    if not m:
        continue
    spec = open(os.path.join(d, "spec.md"), encoding="utf-8").read() if os.path.isfile(os.path.join(d, "spec.md")) else ""
    fm = spec.split("---", 2)[1] if spec.startswith("---") else ""
    get = lambda k: (re.search(rf"^{k}:\s*(.*)$", fm, re.M) or [None, "-"])[1].strip()[:30]
    subdirs = [x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
    heads = re.findall(r"^## §E\.(\d)", text, re.M)
    r = recs.get(name)
    print(
        f"{'IN ' if r else 'OUT'} {name:32} status={get('status'):11} tier={get('tier'):3} "
        f"era_lines={''.join(heads):6} sha={m.group(1)[:20]:20} subdirs={subdirs} "
        f"implied={r['GitImpliedStatus'] if r else '-'}"
    )
