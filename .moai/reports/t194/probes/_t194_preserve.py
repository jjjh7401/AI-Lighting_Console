import re
import subprocess

BASE = "38a6e7e2157a4862721fcd868056e0dbbb09c4c0"
MAIN = "822e9bd73a05606a47e5683960e74d534af6543c"
PATH = "server/orchestrator/tools.py"
PROTECTED = ((234, 238), (524, 569))
HUNK = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+\d+(?:,\d+)? @@")


def hunks(rev):
    out = subprocess.run(
        ["git", "diff", "--unified=0", BASE + ".." + rev, "--", PATH],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    got = []
    for line in out.splitlines():
        m = HUNK.match(line)
        if m:
            got.append((int(m.group("old_start")), int(m.group("old_count") or "1")))
    return got


def overlaps(s, c, ps, pe):
    return s <= pe and ps <= s + max(c, 1) - 1


for label, rev in (("main (대조군)", MAIN), ("HEAD (t194)", "HEAD")):
    h = hunks(rev)
    bad = [(s, c) for s, c in h for ps, pe in PROTECTED if overlaps(s, c, ps, pe)]
    print(f"{label:16s} 훅 {len(h):3d}개   보호구역 침범: {bad}")
