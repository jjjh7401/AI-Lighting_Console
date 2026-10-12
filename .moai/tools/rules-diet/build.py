"""rules-diet build: 상시 적재 규칙 파일에서 상세 절을 지연 로드 companion 으로 옮긴 판본을 만든다.

원본은 BASE_REF 커밋의 파일이다 (재실행해도 결과가 같다). 결과는 snapshot/ 에 쓴다.
저장소 루트에서: python3 .moai/tools/rules-diet/build.py
[HARD] 조항은 삭제하지 않는다 — 절을 통째로 companion 에 그대로 옮기고, 원 파일에는 포인터와 핵심 한 줄만 남긴다.
"""
import os
import re
import subprocess
import sys

BASE_REF = "1973c4811de3ec4b06964bedd1b99584654179ac"  # 축소 전 원본이 있는 커밋
HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot")
R = ".claude/rules/moai/"

# 이동 지정: 'H2:접두어' (H2 절 전체, 하위 H3 포함) | 'H3:접두어' (H3 절 하나)
# dest 는 COMPANIONS 의 키.
COMPANIONS = {
    "constitution": R + "core/moai-constitution-deferred.md",
    "guard": R + "workflow/main-checkout-branch-guard-deferred.md",
    "vci": R + "core/verification-claim-integrity-deferred.md",
    "ctx": R + "workflow/context-window-management-deferred.md",
    "kanban-lead": ".moai/docs/kanban-lead-protocol.md",
    "kanban-lane": ".moai/docs/lane-protocol.md",  # 끝에 부록으로 덧붙인다
    "handoff": R + "workflow/session-handoff-deferred.md",
    "xsession": R + "workflow/cross-session-messaging-deferred.md",
    "askuser": R + "core/askuser-protocol-deferred.md",
    "agent-common": R + "core/agent-common-protocol-deferred.md",
}

SPECS = {
    R + "core/moai-constitution.md": dict(
        stub="> Deferred detail (Opus 5/4.8 prompt philosophy; Lessons Protocol procedures) → `{c}`. "
             "Kept here: [HARD] lessons are one fact per `feedback_*.md` topic file under auto-memory, indexed by "
             "`MEMORY.md`; additive, never overwritten; archive, never delete.",
        moves=[("H2:Opus 5 / 4.8", "constitution"), ("H2:Lessons Protocol", "constitution")]),
    R + "workflow/main-checkout-branch-guard.md": dict(
        stub="> Deferred detail (hook implementation: opt-in gate, discriminant, exemptions, fail-open) → `{c}`. "
             "A `BRANCH_GUARD_VIOLATION:` deny means a switch/checkout/reset --hard/stash/rebase/merge was attempted "
             "in the primary checkout: use a worktree (`git -C <path>`); the exemptions never reach tool-spawned subagents.",
        moves=[("H2:Mechanical Enforcement", "guard")]),
    R + "core/verification-claim-integrity.md": dict(
        stub="> Deferred detail (§4 cross-references, §5-§6 worked examples) → `{c}`.",
        moves=[("H2:4. Cross-References", "vci"), ("H2:5. Worked Example", "vci"), ("H2:6. Worked Example", "vci")]),
    R + "workflow/context-window-management.md": dict(
        stub="> Deferred detail (graduated compaction, Reduction Ladder, detection heuristics, GLM note) → `{c}`. "
             "Kept here: per-model thresholds, user/orchestrator duties; prefer `.moai/state/context-usage.json` "
             "(`stage`, `raw_pct`) over byte heuristics; cheaper moves (`/compact`, `/rewind`) come before `/clear`.",
        moves=[("H2:Claude Code's Graduated", "ctx"), ("H3:GLM-5.3", "ctx"), ("H2:Reduction Ladder", "ctx"),
               ("H2:Detection Heuristics", "ctx"), ("H2:Cross-references", "ctx")]),
    R + "workflow/kanban-dispatch.md": dict(
        stub="> Role clauses moved out (not always-loaded); the detail-companion note above predates this move, "
             "so some [HARD] clauses now live in the files named here. **Lead session**: Read `{lead}` before moving a card. "
             "**Lane session**: Read `.moai/docs/lane-protocol.md` § 부록 (kanban-dispatch lane clauses). "
             "[HARD] one-liners kept: the lead is the queue's sole producer and promotion is always the operator's act; "
             "completion is read from evidence on disk, never trusted, and the verdict is the lead's; one card per worktree, "
             "entered via the launcher, branch `WT-<slug>` with the card id in the dispatch `card:` field and every commit; "
             "a dispatch is a fixed-field block of at most 10 lines in the operator's `conversation_language`; "
             "a lane integrates into the release branch itself via `EnterWorktree`; never spawn background load.",
        moves=[("H2:The board", "kanban-lead"), ("H2:Entry into the board", "kanban-lead"),
               ("H2:Report milestones", "kanban-lead"), ("H2:Card classes", "kanban-lead"),
               ("H2:The dispatch cycle", "kanban-lead"), ("H2:Completion is read", "kanban-lead"),
               ("H2:Review lens selection", "kanban-lead"), ("H2:The `/clear` handoff", "kanban-lead"),
               ("H2:Isolation is entered", "kanban-lane"), ("H2:Verification load", "kanban-lane"),
               ("H2:Integration into the release branch", "kanban-lane"), ("H2:Factory Mode", "kanban-lane"),
               ("H2:Cross-references", "kanban-lead")]),
    R + "workflow/session-handoff.md": dict(
        stub="> Deferred detail (cut-line spec, field-by-field spec, activation matrix, auto-injected flow, memory steps, "
             "worktree block 0, diet constraints) → `{c}`; Read it when emitting a handoff. "
             "Kept here: triggers, save obligation, the 6-block skeleton, ko labels, output surface. Emission also requires: "
             "save the block verbatim to memory `project_<epic>_<spec>_<status>.md` under `## 다음 세션 시작점`, "
             "update `MEMORY.md`, and render the cut-line block in the response body.",
        moves=[("H3:Cut-line Marker Specification", "handoff"), ("H3:Field-by-Field Specification", "handoff"),
               ("H2:Paste-Time Activation Matrix", "handoff"), ("H2:Auto-Injected Resume Flow", "handoff"),
               ("H2:Auto-Memory Integration", "handoff"), ("H2:Worktree-Anchored Resume Pattern", "handoff"),
               ("H2:Diet Constraints", "handoff"), ("H2:V0 Abort Gate Doctrine", "handoff"),
               ("H2:Cross-references", "handoff")]),
    R + "workflow/cross-session-messaging.md": dict(
        stub="> Deferred detail (availability constraints, mechanism table, addressing frictions, idle-notice detail, "
             "configuration surface) → `{c}`. Kept here: all [HARD] rules, the concurrency-check integration, anti-patterns. "
             "[HARD] an idle notice is a scheduling hint, never completion evidence; delivery failures are quiet — "
             "surface them rather than retrying.",
        moves=[("H2:Availability constraints", "xsession"), ("H2:Where it sits", "xsession"),
               ("H2:Addressing, sending", "xsession"), ("H2:An idle notice", "xsession"),
               ("H2:Configuration surface", "xsession"), ("H2:Cross-references", "xsession")]),
    R + "core/askuser-protocol.md": dict(
        stub="> Deferred detail (encoding failure mechanism, report-gate criteria, Blind Spot Pass, free-form examples, "
             "Unknowns lens) → `{c}`. Kept here: Channel Monopoly, ToolSearch preload, option standards, boundary, "
             "triggers, the [HARD] native-UTF-8 directive.",
        moves=[("H3:Failure Mode", "askuser"), ("H3:Root-Cause Mechanism", "askuser"),
               ("H3:Self-Reinforcing Pollution Loop", "askuser"), ("H3:Scope Note", "askuser"),
               ("H3:Report Completeness Criteria", "askuser"), ("H3:Preview-as-Report Substitution", "askuser"),
               ("H3:Report-Promise Fulfillment", "askuser"), ("H2:Blind Spot Pass", "askuser"),
               ("H3:Why this matters", "askuser"), ("H3:Correct Pattern", "askuser"),
               ("H3:The Unknowns 4-Quadrant Lens", "askuser"), ("H3:Interview-Round Structure Example", "askuser")]),
    R + "core/agent-common-protocol.md": dict(
        stub="> Deferred detail (verbatim batch, attributable diff-check, hook table, per-spawn model injection, "
             "super-advisor triggers) → `{c}`. Kept here: subagent prohibitions, blocker/re-delegation, ledger closure, "
             "pre-spawn and pre-edit sync checks, sweep prohibition.",
        moves=[("H3:Verbatim batch", "agent-common"), ("H3:Attributable diff-check", "agent-common"),
               ("H3:Hook Invocation Surface", "agent-common"), ("H3:Per-Spawn Model Injection", "agent-common"),
               ("H3:Super-Advisor Escalation", "agent-common")]),
}

LOCAL_ONLY = [R + "workflow/session-handoff-fields.md", R + "workflow/worktree-integration-detail.md"]


def git_show(path):
    return subprocess.run(["git", "show", f"{BASE_REF}:{path}"], check=True, capture_output=True, text=True).stdout


def split_blocks(text):
    """[(h2, h3, 본문)] — 코드펜스 안의 '#' 줄은 제목이 아니다. 본문은 제목 줄을 포함한다."""
    out, h2, h3, buf, fence = [], "(preamble)", "(intro)", [], False

    def flush():
        if buf:
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


def dest_of(block, moves):
    h2, h3, _ = block
    for spec, dest in moves:
        kind, _, pref = spec.partition(":")
        if (kind == "H2" and h2.startswith(pref)) or (kind == "H3" and h3.startswith(pref)):
            return dest
    return None


def title_of(block):
    h2, h3, _ = block
    return h2 if h3 == "(intro)" else h3


def write(rel, text):
    # 스냅샷 안에 .claude/ 디렉터리가 생기면 규칙으로 읽힐 수 있어 선행 점을 dot- 로 바꿔 저장한다
    p = os.path.join(SNAP, "dot-" + rel[1:] if rel.startswith(".") else rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    if not os.path.exists("CLAUDE.md"):
        sys.exit("저장소 루트에서 실행하세요")
    moved = {k: [] for k in COMPANIONS}   # dest -> [(원 파일, 블록)]
    for path, spec in SPECS.items():
        text = git_show(path)
        fm = re.match(r"\A---\n.*?\n---\n", text, re.S)
        blocks = split_blocks(text)
        kept, run, prev_dest = [], [], None
        names = {k: os.path.basename(v) for k, v in COMPANIONS.items()}
        fmt = dict(c=names.get(spec["moves"][0][1], ""), lead=COMPANIONS["kanban-lead"])
        stub_done = False
        for b in blocks:
            d = dest_of(b, spec["moves"])
            if d is None:
                kept.append(b[2])
                if b[0] == "(preamble)" and not stub_done:
                    kept.append("\n" + spec["stub"].format(**fmt) + "\n\n")
                    stub_done = True
                prev_dest = None
                continue
            moved[d].append((path, b))
            if prev_dest != d:  # 같은 목적지로 이어지는 연속 이동은 포인터 한 줄만
                where = COMPANIONS[d]
                tgt = where if where.startswith(".moai/") else os.path.basename(where)
                kept.append(f"> ↪ deferred → `{tgt}`: {title_of(b)}\n\n")
            prev_dest = d
        body = "".join(kept)
        body = re.sub(r"\n{3,}", "\n\n", body)
        write(path, body)

    for dest, items in moved.items():
        if not items:
            continue
        rel = COMPANIONS[dest]
        srcs = sorted({p for p, _ in items})
        body = "".join(b[2] + "\n" for _, b in items)
        if dest == "kanban-lane":
            base = git_show(rel)  # 원본 커밋 기준 (재실행해도 부록이 중복되지 않는다)
            text = (base.rstrip("\n") + "\n\n## 부록 — kanban-dispatch.md 레인 조항 (t613 에서 이동, 원문 그대로)\n\n"
                    "> 출처: `.claude/rules/moai/workflow/kanban-dispatch.md`. 레인 세션이 읽는다. "
                    "리드 조항은 `.moai/docs/kanban-lead-protocol.md`.\n\n" + body)
            write(rel, text)
            continue
        stem = os.path.basename(srcs[0])[:-3]
        if rel.startswith(R):
            head = (f'---\ndescription: "Deferred detail moved verbatim out of {stem}.md (t613 rules diet); '
                    f'the SSOT file keeps pointers and the [HARD] one-liners"\npaths: "**/{stem}.md"\n---\n\n')
        else:
            head = ""
        title = f"# {stem} — deferred detail (t613)\n\n> 원문 그대로 옮긴 상세. 출처: `{srcs[0]}`. " \
                f"조항의 효력은 그대로다 (삭제 아님, 적재 위치만 바뀜).\n\n"
        write(rel, head + title + body)

    for p in LOCAL_ONLY:
        write(p, git_show(p))
    print("built ->", SNAP)


if __name__ == "__main__":
    main()
