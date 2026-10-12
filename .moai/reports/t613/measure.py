"""t613 측정 스크립트: 상시 적재 instruction 파일 16개의 글자 수와 이동 시나리오 추정.

실행 (저장소 루트에서): python3 .moai/reports/t613/measure.py
읽기 전용이다. 표준 출력만 쓰며 규칙·설정 파일을 바꾸지 않는다.
글자 수는 파일에서 직접 잰 값이고, 스텁(남기는 요약문) 크기만 가정치(stub)다.
"""
import os
import re
import sys

FILES = [
    "CLAUDE.md",
    ".moai/config/sections/user.yaml",          # CLAUDE.md 의 @import
    ".moai/config/sections/language.yaml",      # CLAUDE.md 의 @import
    ".claude/rules/moai/core/agent-common-protocol.md",
    ".claude/rules/moai/core/askuser-protocol.md",
    ".claude/rules/moai/core/moai-constitution.md",
    ".claude/rules/moai/core/native-idiom-and-register.md",
    ".claude/rules/moai/core/verification-claim-integrity.md",
    ".claude/rules/moai/workflow/cache-aware-execution.md",
    ".claude/rules/moai/workflow/context-window-management.md",
    ".claude/rules/moai/workflow/cross-session-messaging.md",
    ".claude/rules/moai/workflow/goal-directive.md",
    ".claude/rules/moai/workflow/kanban-dispatch.md",
    ".claude/rules/moai/workflow/main-checkout-branch-guard.md",
    ".claude/rules/moai/workflow/session-handoff.md",
    ".claude/rules/moai/workflow/skill-routing.md",
]

FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)   # 파일 맨 앞 frontmatter
COMMENT = re.compile(r"<!--.*?-->", re.S)        # HTML 주석

LEAD = [  # 리드 세션에서만 쓰는 kanban 조항
    "H2:The board", "H2:Entry into the board", "H2:Report milestones", "H2:Card classes",
    "H2:The dispatch cycle", "H2:Completion is read", "H2:Review lens selection",
    "H2:The `/clear` handoff",
]
LANE = [  # 레인 세션이 실제로 쓰는 kanban 조항
    "H2:Isolation is entered", "H2:Verification load",
    "H2:Integration into the release branch", "H2:Factory Mode",
]

A_GROUP = [  # 이동만 하면 되는 항목 (역할·설정 로더 변경 불필요)
    dict(name="moai-constitution", path=".claude/rules/moai/core/moai-constitution.md",
         move=["H2:Opus 5 / 4.8", "H2:Lessons Protocol"],
         keep={"H2:Lessons Protocol": 900}, stub=600),
    dict(name="main-checkout-branch-guard", path=".claude/rules/moai/workflow/main-checkout-branch-guard.md",
         move=["H2:Mechanical Enforcement"], keep={}, stub=650),
    dict(name="verification-claim-integrity", path=".claude/rules/moai/core/verification-claim-integrity.md",
         move=["H2:4. Cross-References", "H2:5. Worked Example", "H2:6. Worked Example"],
         keep={}, stub=500),
    dict(name="context-window-management", path=".claude/rules/moai/workflow/context-window-management.md",
         move=["H2:Claude Code's Graduated", "H2:Reduction Ladder", "H2:Detection Heuristics",
               "H2:Cross-references", "H3:GLM-5.3"],
         keep={}, stub=600),
]

B_GROUP = [  # 로딩 경로 변경(역할 주입·명시 Read·스킬)이 필요한 항목
    dict(name="kanban-dispatch", path=".claude/rules/moai/workflow/kanban-dispatch.md",
         move=LEAD + LANE + ["H2:Cross-references"], keep={}, stub=1500),
    dict(name="session-handoff", path=".claude/rules/moai/workflow/session-handoff.md",
         move=["H2:Canonical Format", "H2:Paste-Time Activation Matrix",
               "H2:Auto-Injected Resume Flow", "H2:Auto-Memory Integration",
               "H2:Worktree-Anchored Resume Pattern", "H2:Diet Constraints", "H2:Cross-references"],
         keep={}, stub=1800),
    dict(name="cross-session-messaging", path=".claude/rules/moai/workflow/cross-session-messaging.md",
         move=["H2:What the channel is", "H2:Availability constraints", "H2:Where it sits",
               "H2:An idle notice", "H2:Addressing, sending", "H2:Configuration surface",
               "H2:Cross-references"],
         keep={"H2:What the channel is": 700, "H2:An idle notice": 400}, stub=700),
    dict(name="askuser-protocol", path=".claude/rules/moai/core/askuser-protocol.md",
         move=["H2intro:Non-ASCII Tool-Call Encoding", "H3:Failure Mode", "H3:Root-Cause Mechanism",
               "H3:Self-Reinforcing Pollution Loop", "H3:Scope Note",
               "H3:Report Completeness Criteria", "H3:Preview-as-Report Substitution",
               "H3:Report-Promise Fulfillment", "H2:Blind Spot Pass", "H3:Why this matters",
               "H3:Correct Pattern", "H3:The Unknowns 4-Quadrant Lens",
               "H3:Interview-Round Structure Example"],
         keep={}, stub=1000),
    dict(name="agent-common-protocol", path=".claude/rules/moai/core/agent-common-protocol.md",
         move=["H3:Verbatim batch", "H3:Attributable diff-check", "H3:Hook Invocation Surface",
               "H3:Pre-Spawn Sync Check", "H3:Super-Advisor Escalation", "H3:Per-Spawn Model Injection"],
         keep={"H3:Hook Invocation Surface": 459, "H3:Pre-Spawn Sync Check": 1600,
               "H3:Super-Advisor Escalation": 700, "H3:Per-Spawn Model Injection": 340},
         stub=400),
]


def counted(text):
    """주입 전 frontmatter 와 HTML 주석을 뺀 글자 수 (보고값 227.7k 를 재현하는 계산)."""
    return COMMENT.sub("", FRONT.sub("", text, count=1))


def sections(text):
    """(H2 제목, H3 제목, 본문) 목록. 코드펜스 안의 '#' 줄은 제목으로 보지 않는다."""
    out = []
    h2, h3, buf, fence = "(preamble)", "(intro)", [], False

    def flush():
        out.append((h2, h3, "\n".join(buf) + "\n"))

    for ln in text.split("\n"):
        if ln.startswith("```"):
            fence = not fence
        if not fence and ln.startswith("## "):
            flush()
            h2, h3, buf = ln[3:].strip(), "(intro)", [ln]
        elif not fence and ln.startswith("### "):
            flush()
            h3, buf = ln[4:].strip(), [ln]
        else:
            buf.append(ln)
    flush()
    return out


def hit(sec, spec):
    """spec 형식: 'H2:접두어' | 'H2intro:접두어' (H2 직속 본문만) | 'H3:접두어'."""
    h2, h3, _ = sec
    kind, _, pref = spec.partition(":")
    if kind == "H2":
        return h2.startswith(pref)
    if kind == "H2intro":
        return h2.startswith(pref) and h3 == "(intro)"
    if kind == "H3":
        return h3.startswith(pref)
    raise ValueError(spec)


def project(item):
    text = counted(open(item["path"], encoding="utf-8").read())
    secs = sections(text)
    moved, detail = 0, []
    for spec in item["move"]:
        sz = sum(len(s[2]) for s in secs if hit(s, spec))
        if sz == 0:
            print(f"  WARN no match: {item['name']} {spec}")
        k = item["keep"].get(spec, 0)
        m = max(sz - k, 0)
        moved += m
        detail.append((spec, sz, k, m))
    coverage = sum(len(s[2]) for s in secs) / max(len(text), 1)
    return dict(name=item["name"], counted=len(text), moved=moved,
                stub=item["stub"], net=moved - item["stub"], detail=detail, coverage=coverage)


def main():
    if not os.path.exists(FILES[0]):
        sys.exit("저장소 루트에서 실행하세요 (CLAUDE.md 가 보이지 않음)")
    raw = sum(len(open(f, encoding="utf-8").read()) for f in FILES)
    base = sum(len(counted(open(f, encoding="utf-8").read())) for f in FILES)
    print(f"[1] 파일 {len(FILES)}개 글자 수")
    print(f"    raw (frontmatter·주석 포함)        : {raw:>8}")
    print(f"    counted (frontmatter·주석 제외)     : {base:>8}  = {base/1000:.1f}k  (보고값 227.7k)")
    print(f"    한도 150.0k 대비 초과분              : {base-150000:>8}  ({(base-150000)/base:.1%} of total)")

    print("\n[2] 이동 항목별 추정 (헤딩 단위; stub 은 가정치)")
    rows = {}
    for group, label in [(A_GROUP, "A군 (역할·로더 변경 불필요)"), (B_GROUP, "B군 (로딩 경로 변경 필요)")]:
        print(f"  -- {label}")
        print(f"     {'item':30} {'counted':>8} {'moved':>8} {'stub':>6} {'net':>8}  parser-coverage")
        for item in group:
            r = project(item)
            rows[r["name"]] = r
            print(f"     {r['name']:30} {r['counted']:>8} {r['moved']:>8} {r['stub']:>6} {r['net']:>8}  {r['coverage']:.3f}")
            for spec, sz, k, m in r["detail"]:
                print(f"         {spec:52} section={sz:>6} keep={k:>5} moved={m:>6}")

    lead = sum(d[3] for d in rows["kanban-dispatch"]["detail"] if d[0] in LEAD)
    lane = sum(d[3] for d in rows["kanban-dispatch"]["detail"] if d[0] in LANE)
    other = rows["kanban-dispatch"]["moved"] - lead - lane
    print(f"\n[3] kanban-dispatch 역할 분할 (이동 글자 수): lead={lead}  lane={lane}  공통/참고={other}")

    print("\n[4] 누적 시나리오 (base 에서 순감소를 차례로 뺀 추정치)")
    order = ["moai-constitution", "main-checkout-branch-guard", "verification-claim-integrity",
             "context-window-management"]
    a_total = sum(rows[n]["net"] for n in order)
    steps = [
        ("A군만", a_total),
        ("A + kanban", a_total + rows["kanban-dispatch"]["net"]),
        ("A + kanban + session-handoff", a_total + rows["kanban-dispatch"]["net"] + rows["session-handoff"]["net"]),
        ("… + cross-session-messaging", a_total + rows["kanban-dispatch"]["net"] + rows["session-handoff"]["net"] + rows["cross-session-messaging"]["net"]),
        ("… + askuser-protocol (최소 세트)", a_total + rows["kanban-dispatch"]["net"] + rows["session-handoff"]["net"] + rows["cross-session-messaging"]["net"] + rows["askuser-protocol"]["net"]),
        ("… + agent-common-protocol (권장 세트)", a_total + rows["kanban-dispatch"]["net"] + rows["session-handoff"]["net"] + rows["cross-session-messaging"]["net"] + rows["askuser-protocol"]["net"] + rows["agent-common-protocol"]["net"]),
    ]
    for label, net in steps:
        after = base - net
        verdict = f"초과 {after-150000}" if after > 150000 else f"이하 (여유 {150000-after})"
        print(f"    {label:40} 순감소 {net:>7}  →  {after:>7}  ({after/1000:.1f}k)  {verdict}")


if __name__ == "__main__":
    main()
