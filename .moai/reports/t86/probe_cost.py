"""t86 cost probe - what each candidate blacklist entry would cost.

Re-runs the `_would_be_held` over `load_corpus()` procedure that
blacklist.yaml's header establishes, in THIS tree at THIS head.
No console send. Round 2 adds Assign/Copy and the combined B shape.
"""

import dataclasses

from server.deploy.scan import scan_lua_source
from server.measurement.corpus import load_corpus
from server.safety.classify import classify_command
from server.safety.expand import evaluate_reference
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

BASE = load_ruleset()
SCENARIOS = load_corpus()

CANDIDATES = [
    ("(base, none)", []),
    ("Store", ["Store"]),
    ("Store Preset", ["Store Preset"]),
    ("Store Group", ["Store Group"]),
    ("Store Cue", ["Store Cue"]),
    ("Label", ["Label"]),
    ("Label Preset", ["Label Preset"]),
    ("Assign", ["Assign"]),
    ("Copy", ["Copy"]),
    ("Assign Sequence", ["Assign Sequence"]),
    ("Copy Page", ["Copy Page"]),
    ("A: SPreset+LPreset", ["Store Preset", "Label Preset"]),
    ("B: Store+Label", ["Store", "Label"]),
    ("B+: Store,Label,Assign,Copy", ["Store", "Label", "Assign", "Copy"]),
]


class NoBody:
    def fetch_body(self, reference):
        raise Exception("no body fetcher configured")


def would_be_held(command, ruleset):
    grammar = validate(command)
    if not grammar.ok:
        return False
    verdict = classify_command(grammar.parsed, ruleset)
    if verdict.risky:
        return True
    if verdict.category == "invoking":
        return evaluate_reference(
            verdict.reference, ruleset=ruleset, fetcher=NoBody(), plugin_registry=None
        ).hold
    return False


def offenders(ruleset):
    out = []
    for scenario in SCENARIOS:
        for command in scenario.mock.commands:
            if would_be_held(command, ruleset):
                out.append((scenario.id, command))
        if scenario.mock.kind == "plugin":
            for finding in scan_lua_source(scenario.mock.plugin_source, ruleset).findings:
                out.append((scenario.id, finding.command))
    return out


total_scenarios = len(SCENARIOS)
total_lines = sum(len(s.mock.commands) for s in SCENARIOS)
print("corpus: %d scenarios, %d command lines" % (total_scenarios, total_lines))
print("")
print("%-30s %-8s %-12s %s" % ("candidate", "lines", "scenarios", "newly-held scenario ids"))
print("-" * 110)

baseline = set()
for label, entries in CANDIDATES:
    ruleset = dataclasses.replace(BASE, blacklist=BASE.blacklist + tuple(entries))
    found = offenders(ruleset)
    ids = sorted(set(i for i, _ in found))
    if not entries:
        baseline = set(found)
        new_ids = []
    else:
        new_ids = sorted(set(i for i, c in found if (i, c) not in baseline))
    print(
        "%-30s %-8s %-12s %s"
        % (label, len(found), "%d/%d" % (len(ids), total_scenarios), ",".join(new_ids) or "-")
    )
