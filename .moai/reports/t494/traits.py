"""t494: sync_commit_sha 를 가진 SPEC 들의 특성을 drift 포함 여부와 나란히 본다."""

import json
import os
import re


def read(path):
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def field(frontmatter, key):
    found = re.search(rf"^{key}:\s*(.*)$", frontmatter, re.M)
    return found.group(1).strip()[:30] if found else "-"


recs = {r["SPECID"]: r for r in json.loads(read(".moai/reports/t494/drift.json"))["Records"]}
root = ".moai/specs"
for name in sorted(os.listdir(root)):
    d = os.path.join(root, name)
    text = read(os.path.join(d, "progress.md"))
    m = re.search(r"^sync_commit_sha:\s*(\S+)", text, re.M)
    if not m:
        continue
    spec = read(os.path.join(d, "spec.md"))
    fm = spec.split("---", 2)[1] if spec.startswith("---") else ""
    subdirs = [x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
    heads = "".join(re.findall(r"^## §E\.(\d)", text, re.M))
    r = recs.get(name)
    implied = r["GitImpliedStatus"] if r else "-"
    print(
        f"{'IN ' if r else 'OUT'} {name:32} status={field(fm, 'status'):11} "
        f"tier={field(fm, 'tier'):3} era_lines={heads:6} sha={m.group(1)[:20]:20} "
        f"subdirs={subdirs} implied={implied}"
    )
