"""t554 — design.md 가 mockup.md/proposal.md 의 `## ` 절 전수를 다루는지 기계 검사 (읽기 전용).

실행(워크트리 루트):
  python3 .moai/reports/t554/coverage_check.py

방식: 각 디자인 정본 파일의 `## ` 절을, 그 절의 시작 줄부터 다음 절 시작 줄 바로 앞까지의
구간으로 잡고, design.md §2(mockup.md 몫)·§3~§6(proposal.md 몫)에 그 구간과 겹치는 줄 번호
인용이( `:N`·`:N-M` 또는 `(N)`·`(N-M)` 꼴 ) 하나라도 있는지 확인한다. 하나도 없으면 MISS.
"""

import re

DESIGN_MD = ".moai/specs/SPEC-LDBEAT-001/design.md"
MOCKUP_MD = ".moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-mockup-20261008.md"
PROPOSAL_MD = ".moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.md"

with open(DESIGN_MD, encoding="utf-8") as fh:
    design = fh.read()


def section(start_marker, end_marker=None):
    start = design.index(start_marker)
    end = design.index(end_marker) if end_marker else len(design)
    return design[start:end]


sec_mockup = section("## §2.", "## §3.")
sec_proposal = section("## §3.", "## §7.")


def covered_lines(blob):
    covered = set()
    for m in re.finditer(r':(\d+)(?:-(\d+))?', blob):
        s = int(m.group(1))
        e = int(m.group(2)) if m.group(2) else s
        covered.update(range(s, e + 1))
    for m in re.finditer(r'\((\d+)(?:-(\d+))?\)', blob):
        s = int(m.group(1))
        e = int(m.group(2)) if m.group(2) else s
        covered.update(range(s, e + 1))
    return covered


def headings_with_span(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    hs = [(i + 1, l.strip()[3:]) for i, l in enumerate(lines) if l.startswith("## ")]
    total = len(lines)
    spans = []
    for idx, (ln, name) in enumerate(hs):
        nxt = hs[idx + 1][0] - 1 if idx + 1 < len(hs) else total
        spans.append((ln, nxt, name))
    return spans


def check(path, covered):
    spans = headings_with_span(path)
    missing = []
    for start, end, name in spans:
        if not any(l in covered for l in range(start, end + 1)):
            missing.append((start, name))
    return spans, missing


spans_m, miss_m = check(MOCKUP_MD, covered_lines(sec_mockup))
spans_p, miss_p = check(PROPOSAL_MD, covered_lines(sec_proposal))

print(f"TOTAL_HEADINGS={len(spans_m) + len(spans_p)} (mockup={len(spans_m)}, proposal={len(spans_p)})")
print(f"MISSING={len(miss_m) + len(miss_p)}")
for i, name in miss_m:
    print(f"  MISS mockup.md:{i} {name}")
for i, name in miss_p:
    print(f"  MISS proposal.md:{i} {name}")
