---
description: "Deferred detail moved verbatim out of verification-claim-integrity.md (t613 rules diet); the SSOT file keeps pointers and the [HARD] one-liners"
paths: "**/verification-claim-integrity.md"
---

# verification-claim-integrity — deferred detail (t613)

> 원문 그대로 옮긴 상세. 출처: `.claude/rules/moai/core/verification-claim-integrity.md`. 조항의 효력은 그대로다 (삭제 아님, 적재 위치만 바뀜).

## 4. Cross-References (SSOT — cross-reference only, do not duplicate)

This doctrine cross-references the following canonical surfaces. It does NOT copy their content — each remains the single source of truth for its own subject:

- `.claude/rules/moai/core/agent-common-protocol.md` § Skeptical Evaluation Stance — the fresh-judgment auditor stance (treat claims as suspect until evidence is shown).
- `.claude/rules/moai/core/moai-constitution.md` § Agent Core Behaviors "Verify, Don't Assume" — the cross-cutting HARD behavior requiring evidence of completion.
- `.claude/rules/moai/development/manager-develop-prompt-template.md` § E (Self-Verification Deliverables) — the manager-agent self-verification matrix that the 5-section format generalizes and relates to.
- `.claude/rules/moai/workflow/verification-batch-pattern.md` — the orchestrator-side read-only verification batching pattern (the mechanism by which observed evidence is gathered efficiently).
- `.claude/output-styles/moai/moai.md` — the Verification Matrix and Completion Report banners (the orchestrator self-report surface bound by §1.1).


## 5. Worked Example — Defect-Claim Hazard

A status report counted N items matching a text pattern (for example, a metadata field absent from N files) and inferred "these N items are debt requiring action" — then proposed batch-modifying all N.

This was an unobserved defect claim: the domain had a dedicated verification tool, and it had not been run. The text pattern was compatible with two contradictory interpretations (items legitimately in a protected or legacy state versus items with a genuinely missing step); only the dedicated tool could disambiguate. When the tool was finally run, the inferred debt did not exist — the items were in their correct state — and had the batch modification proceeded, N items would have been touched for no reason.

Lesson codified: **a defect claim is a hypothesis until the domain's tool confirms it.** Whenever a domain verification tool exists (an audit command, a type checker, a linter, a coverage tool), its output MUST precede any defect / debt / drift claim — §1.1 surface 3 + §2 attribution. Text-pattern matching alone produces a candidate defect, never a verified one.


## 6. Worked Example — Retention-Claim Hazard

A user instructed that a directory of retired artifacts be removed. The actor deleted the artifacts but held one item back — a scan in a shipped workflow file that globbed for files under that directory — on the stated premise that removing it "would withdraw a live feature from every distributed user", and recommended a separate retirement task instead.

That premise was never checked. The actor had verified the scan was *reachable* (the workflow's routing table points at it) and had read that the task which originally delivered the feature still carried an in-service status, then treated both facts as evidence the feature was live. Neither establishes that. When the producers were finally enumerated, every one was already gone: the command that invoked the feature, its workflow file, its dedicated agent, its CLI entry point, the flag that consumed its output, the template scaffold that created the directory, and its documentation pages in every locale. A completed retirement task had removed the feature from the template source permanently, for all distributed users, and a later cleanup commit had swept the orphans that retirement left behind. The scan simply survived both passes. With no producer and no scaffold, the glob could only ever return zero on a user's machine.

Lesson codified: **reachability is not justification, and an originating task still reading as in-service is not proof the feature it delivered is still live** — a later task may have retired it. Before recommending retention against an instruction, enumerate the producers of the thing being retained and check for a completed retirement; an objection whose premise was never verified is an unobserved claim — §1.1 surface 4 + §2 attribution.

---

Version: 1.2.0
Classification: Canonical Reference (policy-layer codification) — do not duplicate cross-referenced content; cross-reference this file instead.


