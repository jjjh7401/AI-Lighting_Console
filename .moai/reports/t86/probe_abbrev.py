"""t86 abbreviation probe - does the VERB abbreviate the way the OPTION does?

`/o` reaches `/overwrite`, so the fair question is whether `Sto` reaches
`Store`. Runs each form twice: against the shipped ruleset, and against a
hypothetical ruleset carrying entry "Store" (branch B), because B's
completeness depends on whether abbreviated verbs are caught too.
No console send.
"""

import dataclasses

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

BASE = load_ruleset()
WITH_STORE = dataclasses.replace(BASE, blacklist=BASE.blacklist + ("Store", "Label"))

FORMS = [
    "Store Preset 1.1",
    "Stor Preset 1.1",
    "Sto Preset 1.1",
    "St Preset 1.1",
    "S Preset 1.1",
    "STORE Preset 1.1",
    "sto preset 1.1",
    "Store Preset 1.1 /o",
    "Sto Preset 1.1 /o",
    "St Preset 1.1 /o",
    'Label Preset 4.7 "x"',
    'Lab Preset 4.7 "x"',
    'La Preset 4.7 "x"',
]


def verdict_of(command, ruleset):
    grammar = validate(command)
    if not grammar.ok:
        return "GRAMMAR-REJECT", None
    finding = classify_command(grammar.parsed, ruleset)
    return finding.category, finding.matched_entry


print("%-26s %-24s %s" % ("form", "shipped ruleset (v3)", "hypothetical +Store,+Label"))
print("-" * 92)
for form in FORMS:
    a_cat, a_entry = verdict_of(form, BASE)
    b_cat, b_entry = verdict_of(form, WITH_STORE)
    a = a_cat if a_entry is None else "%s <%s>" % (a_cat, a_entry)
    b = b_cat if b_entry is None else "%s <%s>" % (b_cat, b_entry)
    print("%-26s %-24s %s" % (form, a, b))
