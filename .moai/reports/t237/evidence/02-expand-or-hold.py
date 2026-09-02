"""t237 — expand-or-hold 결과 + import 출처. 콘솔 접촉 0.

실행: PYTHONPATH=. python .moai/reports/t237/evidence/02-expand-or-hold.py
"""

import os

import server.safety.classify as classify_module
import server.safety.ruleset as ruleset_module
from server.safety.classify import classify_command
from server.safety.expand import evaluate_reference
from server.safety.gate import _UnavailableBodyFetcher
from server.safety.grammar import validate


def main() -> None:
    print("cwd =", os.getcwd())
    print("classify module file =", classify_module.__file__)
    print("ruleset default path =", ruleset_module.DEFAULT_RULESET_PATH)

    rs = ruleset_module.load_ruleset()
    fetcher = _UnavailableBodyFetcher()
    for command in ["Off Fixture 501", "Off Group 1", "Off Sequence 1", "Clear"]:
        grammar = validate(command)
        finding = classify_command(grammar.parsed, rs)
        line = f"{command!r:20} category={finding.category:10} ref={finding.reference!r:14}"
        if finding.category == "invoking":
            result = evaluate_reference(finding.reference, ruleset=rs, fetcher=fetcher)
            line += f" hold={result.hold} reasons={result.reasons}"
        print(line)


if __name__ == "__main__":
    main()
