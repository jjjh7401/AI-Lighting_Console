"""t237 — 순진한 수리(참조 타입 확장)가 무력함을 오프라인으로 확인. 콘솔 접촉 0."""

from server.safety.classify import RECOGNIZED_REFERENCE_TYPES, classify_command
from server.safety.console import DEFAULT_BODY_PATHS, StateBodyFetcher
from server.safety.expand import evaluate_reference
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

rs = load_ruleset()
print("RECOGNIZED_REFERENCE_TYPES =", RECOGNIZED_REFERENCE_TYPES)
print("DEFAULT_BODY_PATHS keys    =", sorted(DEFAULT_BODY_PATHS))
print()


def q(path):
    raise AssertionError("이 프로브는 콘솔에 질의하지 않는다 — 여기 닿으면 설계가 틀린 것")


fetcher = StateBodyFetcher(query=q)

for types in (RECOGNIZED_REFERENCE_TYPES, RECOGNIZED_REFERENCE_TYPES + ("Fixture", "Group")):
    print(f"--- reference_types = {types} ---")
    for c in ["Off Fixture 501", "Off Group 1"]:
        g = validate(c)
        f = classify_command(g.parsed, rs, reference_types=types)
        r = evaluate_reference(f.reference, ruleset=rs, fetcher=fetcher)
        print(f"  {c!r:20} ref={f.reference!r:14} hold={r.hold} reasons={r.reasons}")
    print()
