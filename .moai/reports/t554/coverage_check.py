"""t554 — design.md 가 mockup.md/proposal.md 의 `## ` 절 전수를 다루는지 기계 검사 (읽기 전용).

실행(워크트리 루트):
  python3 .moai/reports/t554/coverage_check.py

방식: 각 디자인 정본 파일의 `## ` 절을, 그 절의 시작 줄부터 다음 절 시작 줄 바로 앞까지의
구간으로 잡고, design.md §2(mockup.md 몫)·§3~§6(proposal.md 몫)에 그 구간과 겹치는 줄 번호
인용이( `:N`·`:N-M` 또는 `(N)`·`(N-M)` 꼴 ) 하나라도 있는지 확인한다. 하나도 없으면 MISS.

[구조적 완전성만 — 정확성은 아님] 이 검사는 design.md가 각 `## ` 절을 "어떤 행에서든"
인용했는지만 본다(줄 번호 겹침 1건 이상). 그 인용이 **맞게** 분류됐는지(예: 저장 절을
디스플레이 절로 잘못 인용했는지, "대체됨"이 진짜 대체인지)는 이 스크립트가 검사하지
않는다 — 그건 사람이 원문(특히 .html 렌더 코드)을 다시 읽어야 잡히는 오류다(delta
plan-audit 2026-10-11이 바로 그 방식으로 D1~D4를 잡았다, MISSING=0인 상태에서도).
MISSING=0은 "빠진 행이 없다"는 뜻일 뿐 "모든 매핑이 옳다"는 뜻이 아니다.
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
    for m in re.finditer(r":(\d+)(?:-(\d+))?", blob):
        s = int(m.group(1))
        e = int(m.group(2)) if m.group(2) else s
        covered.update(range(s, e + 1))
    for m in re.finditer(r"\((\d+)(?:-(\d+))?\)", blob):
        s = int(m.group(1))
        e = int(m.group(2)) if m.group(2) else s
        covered.update(range(s, e + 1))
    return covered


def headings_with_span(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    hs = [(i + 1, line.strip()[3:]) for i, line in enumerate(lines) if line.startswith("## ")]
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
        if not any(n in covered for n in range(start, end + 1)):
            missing.append((start, name))
    return spans, missing


spans_m, miss_m = check(MOCKUP_MD, covered_lines(sec_mockup))
spans_p, miss_p = check(PROPOSAL_MD, covered_lines(sec_proposal))

total_headings = len(spans_m) + len(spans_p)
print(f"TOTAL_HEADINGS={total_headings} (mockup={len(spans_m)}, proposal={len(spans_p)})")
print(f"MISSING={len(miss_m) + len(miss_p)}")
for i, name in miss_m:
    print(f"  MISS mockup.md:{i} {name}")
for i, name in miss_p:
    print(f"  MISS proposal.md:{i} {name}")
