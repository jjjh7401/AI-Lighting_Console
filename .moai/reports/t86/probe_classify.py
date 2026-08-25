"""t86 control probe - classify Store/Label family at the CHECK layer.

No console send. Feeds command strings through the real grammar+classify
pipeline and prints the verdict, so the classification table is read from
the classifier itself rather than from the yaml by eye.
"""

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

CASES = [
    ("Store Preset 1.1", "SUBJECT"),
    ("Store Preset 4.7", "SUBJECT"),
    ('Label Preset 4.7 "Warm Wash"', "SUBJECT"),
    ("Store Group 3", "STORE-FAMILY"),
    ("Store Cue 5", "STORE-FAMILY"),
    ("Store Sequence 1 Cue 2", "STORE-FAMILY"),
    ("Store Executor 1", "STORE-FAMILY"),
    ("Store Macro 7", "STORE-FAMILY"),
    ("Store World 2", "STORE-FAMILY"),
    ("Store View 1", "STORE-FAMILY"),
    ('Label Group 3 "Front Truss"', "LABEL-FAMILY"),
    ('Label Cue 5 "Blackout"', "LABEL-FAMILY"),
    ('Label Sequence 1 "Main"', "LABEL-FAMILY"),
    ("Store /overwrite", "CTRL-POS"),
    ("Store Preset 1.1 /overwrite", "CTRL-POS"),
    ("Store Preset 1.1 /o", "CTRL-POS"),
    ("Delete Preset 1.1", "CTRL-POS"),
    ("Set Fixture 11 Posx '5.0'", "CTRL-POS"),
    ("LoadShow", "CTRL-POS"),
    ("Go+ Executor 1", "CTRL-INVOKE"),
    ("Zzqqxx Preset 1.1", "CTRL-FABRICATED"),
]

ROW = "%-16s %-32s %-14s %-6s %s"


def main():
    ruleset = load_ruleset()
    print("ruleset version = %s" % ruleset.version)
    print("blacklist       = %s" % list(ruleset.blacklist))
    print("")
    print(ROW % ("group", "command", "category", "risky", "matched_entry"))
    print("-" * 92)
    for command, group in CASES:
        grammar = validate(command)
        if not grammar.ok:
            print(ROW % (group, command, "GRAMMAR-REJECT", "-", grammar.errors))
            continue
        finding = classify_command(grammar.parsed, ruleset)
        print(ROW % (group, command, finding.category, finding.risky, finding.matched_entry))


main()
