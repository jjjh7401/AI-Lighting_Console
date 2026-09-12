"""엔트리 "Set Layout" 투입 비용 실측 — `_would_be_held` over `load_corpus()`.

절차는 blacklist.yaml v2 가 세우고 v3~v8 이 이어 쓴 것과 동일하다.
"""

import dataclasses

from server.deploy.scan import scan_lua_source
from server.measurement.corpus import load_corpus
from server.safety.classify import classify_command
from server.safety.expand import BodyUnavailable, evaluate_reference
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

base = load_ruleset()
after = dataclasses.replace(base, version=9, blacklist=base.blacklist + ("Set Layout",))


class NoBody:
    def fetch_body(self, reference):
        raise BodyUnavailable("none")


def held(cmd, rs):
    g = validate(cmd)
    if not g.ok:
        return False
    v = classify_command(g.parsed, rs)
    if v.risky:
        return True
    if v.category == "invoking":
        return evaluate_reference(
            v.reference, ruleset=rs, fetcher=NoBody(), plugin_registry=None
        ).hold
    return False


def offenders(rs):
    sc = load_corpus()
    out = [(s.id, c) for s in sc for c in s.mock.commands if held(c, rs)]
    out += [
        (s.id, f.command)
        for s in sc
        if s.mock.kind == "plugin"
        for f in scan_lua_source(s.mock.plugin_source, rs).findings
    ]
    return out


sc = load_corpus()
lines = [c for s in sc for c in s.mock.commands]
print(f"corpus: {len(sc)} scenarios, {len(lines)} command lines")
b, a = offenders(base), offenders(after)
print(f"held BEFORE (v8): {len(b)}  scenarios={len(set(i for i, _ in b))}")
print(f"held AFTER  (v9): {len(a)}  scenarios={len(set(i for i, _ in a))}")
new = [x for x in a if x not in b]
print(f"NEWLY held lines: {len(new)}  -> {new}")
print(f"NEWLY held scenarios: {sorted(set(i for i, _ in new))}")
print()
print("corpus lines mentioning 'Layout':", [c for c in lines if "layout" in c.lower()])
