---
description: "Deferred detail moved verbatim out of askuser-protocol.md (t613 rules diet); the SSOT file keeps pointers and the [HARD] one-liners"
paths: "**/askuser-protocol.md"
---

# askuser-protocol — deferred detail (t613)

> 원문 그대로 옮긴 상세. 출처: `.claude/rules/moai/core/askuser-protocol.md`. 조항의 효력은 그대로다 (삭제 아님, 적재 위치만 바뀜).

### Interview-Round Structure Example

```
Turn 1: ToolSearch → AskUserQuestion (scope questions)
Turn 2: ToolSearch → AskUserQuestion (approach questions, built on Turn 1 answers)
...
Final:  ToolSearch → AskUserQuestion (confirmation: "Proceed with this plan?")
```

> **Note**: "Interview round" here denotes a turn of Socratic questioning (a generic English usage), NOT the retired SPEC taxonomy term `Round` (within-SPEC SSE-stall sub-division, now folded into `Milestone` per `.claude/rules/moai/development/sprint-round-naming.md`).

---


### Report Completeness Criteria (all mandatory)

1. **Per-source coverage**: the report names each investigation source (agent, lens, audit dimension) and states its key findings with quantification (N findings, severity/classification breakdown). A single-line completion claim ("investigation complete", or its equivalent in any locale) is NOT a report.
2. **Option-to-report traceability**: every codename, identifier, or finding referenced in the question's option labels / descriptions / previews (e.g., `P1 <CODENAME>`, a SPEC ID, a lens name) MUST have been introduced and explained in the preceding report body. An option referencing an entity the report never introduced is a violation — the user cannot evaluate what was never explained.
3. **Structured rendering**: render the report via the Discovery banner (`.claude/output-styles/moai/moai.md` §8 Discovery Report) or equivalent structured markdown with per-source subsections, scaled to the investigation's size.


### Preview-as-Report Substitution (named anti-pattern)

[HARD] Option `preview` / `description` fields MUST NOT be the sole carrier of investigation findings. The preview compresses a comparison; the report explains the evidence. Compressing all findings into an option preview table while the response body carries only a one-line completion claim is the named anti-pattern **preview-as-report substitution** — the user is forced to evaluate options inside a ≤12-line monospace box with no explanatory report behind it.


### Report-Promise Fulfillment

[HARD] When prior narration in the same task promised a consolidated report ("I will consolidate and report", or its equivalent in any locale), the report MUST be rendered before any subsequent decision AskUserQuestion. Claiming the report was delivered when none was rendered is an unobserved completion claim — see `.claude/rules/moai/core/verification-claim-integrity.md` §1.1 surface 1 (orchestrator self-report).


### The Unknowns 4-Quadrant Lens

Beyond the detection-signal triggers above, classify the ambiguity by **user blind spot** using the Known-Knowns / Known-Unknowns / Unknown-Knowns / Unknown-Unknowns 4-quadrant lens:

- **Known-Knowns** — facts the user has stated and the orchestrator has confirmed. No clarification needed.
- **Known-Unknowns** — gaps the user is aware of (open questions they can answer). Resolve via a Socratic interview round (§ Socratic Interview Structure).
- **Unknown-Knowns** — constraints implicit in the existing codebase that the user has not surfaced. Resolve via `Agent(Explore)` read-only reconnaissance, then confirm with the user.
- **Unknown-Unknowns** — risks neither the user nor the orchestrator has articulated. When Unknown-Unknowns are suspected (unfamiliar domain, new subsystem, unfamiliar design/library work), the lens directs the orchestrator to run a Blind Spot Pass (§ Blind Spot Pass) before plan-phase entry.


## Blind Spot Pass

The **Blind Spot Pass** is an OPTIONAL pre-plan Discovery technique for surfacing the user's **unknown-unknowns** — the risks neither the user nor the orchestrator has articulated. It adapts the "help me find my blind spots" activity to the orchestrator model: read-only reconnaissance by `Agent(Explore)`, with the findings surfaced to the user through the orchestrator's `AskUserQuestion` channel.


### When to run

**Where** the user is working in an **unfamiliar** domain — a new subsystem, or unfamiliar design/library territory — **and** the orchestrator suspects unknown-unknowns, the orchestrator SHOULD run a Blind Spot Pass **before plan-phase entry**, before authoring the SPEC. The trigger is a judgment call (suspected unknown-unknowns), NOT an automatic gate on every unfamiliar-domain plan entry.


### Optionality

The Blind Spot Pass is **optional** — it is triggered only when unknown-unknowns are suspected, and is **not a mandatory gate**. In a familiar domain with no suspected unknown-unknowns, the pass is skipped and no forced overhead is incurred.


### Mechanism

When the orchestrator runs a Blind Spot Pass:

1. Spawn `Agent(Explore)` in **read-only** mode to scan the relevant domain (the existing subsystem, library surface, integration points).
2. From that reconnaissance, surface the user's likely unknown-unknowns through a single `AskUserQuestion` round, so the user can react and prompt better before the plan is authored.


### Subagent boundary (preserved)

`Agent(Explore)` — and any subagent — **does not prompt the user** directly. The unknown-unknowns are surfaced only through the orchestrator's `AskUserQuestion` channel, preserving the asymmetric orchestrator–subagent boundary (§ Orchestrator–Subagent Boundary). A subagent that lacks input returns a blocker report; it never asks the user.

---


### Why this matters

`AskUserQuestion` automatically appends an **"Other"** option to every question set. This means:
- Users who prefer free-form answers can select "Other" and type their response
- The orchestrator does NOT need to produce free-form questions to support free-form answers
- Structured options via `AskUserQuestion` are faster and less error-prone than prose for most users


### Correct Pattern

```
# Correct — always through AskUserQuestion
ToolSearch(query: "select:AskUserQuestion")
AskUserQuestion({
  questions: [{
    question: "Select the next step.",
    header: "Direction",
    options: [
      { label: "Create PR immediately (Recommended)", description: "Creates a PR from the current changes. CI runs automatically." },
      { label: "Review then PR", description: "Reviews the changes first, then creates the PR." },
      { label: "Abort", description: "Aborts the current work and preserves state." }
    ]
  }]
})
```


### Failure Mode

A malformed escape — a stray space inside the sequence, a truncated code point, or a half-written `\u` — corrupts the JSON so the `questions` array is parsed as a bare string instead of a list of objects. The call is rejected with `Invalid tool parameters` / `InputValidationError`, and the orchestrator's clarification round silently fails on its first attempt.


### Root-Cause Mechanism

The corruption is not random; it follows a three-step chain documented across LLM tool-call runtimes:

1. **Serialization escaping.** A serialization layer emitting JSON with `ensure_ascii`-style escaping converts multi-byte characters into `\uXXXX` sequences (native CJK text becomes a run of `\uXXXX` code points) when a prior tool call or result is recorded into the conversation history.
2. **Prompt pollution.** That escaped form is fed back into the next inference turn, so the model sees literal `\uXXXX` sequences in its own context instead of native characters.
3. **Mimicry failure.** The model imitates the escape format for its next tool call but cannot reliably reproduce the exact code points, emitting plausible-looking but corrupted escapes (the stray-space / truncated forms above).

The corrective lever is step 1: keep multi-byte text as native UTF-8 in every tool call so the context is never seeded with `\uXXXX` runs.


### Self-Reinforcing Pollution Loop (why one failure recurs)

This failure is **not** an isolated one-off — it is self-reinforcing, and that is why it "keeps happening" rather than failing once and clearing. The Root-Cause Mechanism above is a loop, not a line: once a single `\uXXXX` run is seeded into the conversation context (step 2, prompt pollution), the model sees escaped text in its own context and mimics that format on the *next* tool call too (step 3), re-seeding fresh corruption. Left unbroken, one malformed call becomes a run of malformed calls.

Breaking the loop requires more than retrying the one rejected call:

- **Do not carry the corrupted form forward.** After a recovery, the very next tool call carrying non-ASCII text is the highest-risk moment — the polluted context is still in view. Re-author that payload as native UTF-8 from the intended source text (the user's actual words), NOT by transcribing the `\uXXXX` sequence you can see in context.
- **Recovery is per-payload, not per-call-type.** The clean-up applies to Bash, Write / Edit, and every subsequent multi-byte tool call in the turn — not only the `AskUserQuestion` that first failed.
- **Persistent recurrence → reset the context.** If native-UTF-8 re-authoring still yields repeated `InputValidationError` on non-ASCII payloads within the same session, the context is saturated with `\uXXXX` runs. Escalate to a `/clear` (per `context-window-management.md` § Context Window Targets) with a paste-ready resume message, so the next session starts from an un-polluted context. This is the last-resort loop-break, not the first response.


### Scope Note

This is a model-output discipline, not a project-code defect: a correct JSON serializer (for example Go's `encoding/json`) already preserves multi-byte UTF-8 and never emits `ensure_ascii`-style escapes, so it cannot be the pollution source. The discipline binds the orchestrator's own construction of every tool call — `AskUserQuestion`, Bash, Write / Edit, and any other tool whose JSON payload carries non-ASCII text — not just clarification rounds. The `AskUserQuestion` case above is the origin example; a corrupted `\uXXXX` escape in a Bash command or a Write payload fails the same way.

---

Version: 1.2.0
Classification: Canonical Reference — do not duplicate content; cross-reference this file instead.


