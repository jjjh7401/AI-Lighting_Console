"""고친 뒤 분류 실측 — `01_probe_before.txt` 와 같은 형태로 재서 대조한다."""

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

rs = load_ruleset()
print(f"ruleset version = {rs.version}, entries = {len(rs.blacklist)}")
FORMS = [
    "Set Layout 1.1 'PositionX' 5.0",
    "Set Layout 1.1 'PositionY' 5.0",
    "Set Layout 1.1 PositionX 5.0",
    "Set Lay 1.1 'PositionX' 5.0",
    "Set Layout 1.1 Name 'Cue list'",
    "Set Fixture 11 Posx '5.0'",
    "Set Fixture 11 Rotx '90.0'",
    "Set Layouts 1.1 'PositionX' 5.0",
    "Edit Layout 1.1 'PositionX' 5.0",
    "Store Layout 3",
    "Layout 1",
    "Set Selection MAtricks 'PhaseFromX' 0",
    "Store Page 3",
    "Group 4",
]
for c in FORMS:
    g = validate(c)
    if not g.ok:
        print(f"{c:42s} PARSE-FAIL {g.reason}")
        continue
    f = classify_command(g.parsed, rs)
    print(f"{c:42s} category={f.category:12s} risky={str(f.risky):5s} entry={f.matched_entry!r}")
