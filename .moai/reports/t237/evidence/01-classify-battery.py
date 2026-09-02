from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

rs = load_ruleset()
cmds = [
    "Clear",
    "Clear Clear",
    "Clear Clear Clear",
    "ClearAll",
    "Off Fixture 501",
    "Off Fixture 1 Thru 86",
    "Off Group 1",
    "Fixture 501",
    "Attribute 'Zoom' At 45",
    "Off",
    "Off Sequence 1",
    "Off Macro 1",
]
for c in cmds:
    g = validate(c)
    if not g.ok:
        print(f"{c!r:34} grammar=REJECT reason={g.reason}")
        continue
    f = classify_command(g.parsed, rs)
    print(f"{c!r:34} category={f.category:12} reference={f.reference!r:16} reasons={f.reasons}")
