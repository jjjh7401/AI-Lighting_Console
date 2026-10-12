---
description: "Deferred detail moved verbatim out of session-handoff.md (t613 rules diet); the SSOT file keeps pointers and the [HARD] one-liners"
paths: "**/session-handoff.md"
---

# session-handoff — deferred detail (t613)

> 원문 그대로 옮긴 상세. 출처: `.claude/rules/moai/workflow/session-handoff.md`. 조항의 효력은 그대로다 (삭제 아님, 적재 위치만 바뀜).

### Cut-line Marker Specification

- Top marker: `✂──── 여기부터 복사 ────✂` (scissors U+2702 + 4× U+2500 + space + text + space + 4× U+2500 + scissors)
- Bottom marker: `✂──── 여기까지 복사 ────✂` (same structure, text differs)
- One blank line separates each marker from adjacent block content (top → blank → Block 1; Block 6 → blank → bottom)
- `✂` symbol (U+2702 BLACK SCISSORS) is **preserved verbatim across all locales** — never translate or substitute
- Box-drawing characters (`─` U+2500) preserved verbatim
- Marker text translates per `conversation_language` (see Localization table below)


### Field-by-Field Specification

Per-block detail — the `mode:` orchestration-seed enum and its directive couplings, the fan-out steering phrase, the two `ultracode` forms, the `source_session_id` environment fallback, and the Block 5 arm-only consequence — is in `session-handoff-fields.md` § Field-by-Field Specification (full) (reached via `session-handoff-examples.md` § Field-by-Field Specification (full)). The binding clauses are summarized here.

- **Block 1** — `ultrathink.` opener (sets `effort: xhigh`; Adaptive Thinking is a separate axis it does not toggle). `<phase>` ∈ `plan | run | sync | mx`. [HARD] Fixed line order: opener (plus any appended keyword or steering phrase) → `mode:` → `applied lessons:` → `source_session_id:`, each conditional line omitted when its condition does not hold. A purpose-conditional `mode:` line seeds the next session's orchestration mode from the 4-token enum `solo-sequential | parallel-subagents | agent-team | dynamic-workflow`; it is **omitted** for `solo-sequential` (the default), keeping the common case byte-identical. Its couplings: `parallel-subagents` appends the locale-verbatim phrase `fan out subagents (<read-only investigation scope>)` to the opener, `agent-team` appends `--team` to the Block 5 command, `dynamic-workflow` appends a bare `ultracode` to the opener. [HARD] Every one of these is a **SEED, not a permission grant** — Implementation Kickoff Approval remains mandatory, and a steered fan-out stays within the 3-5 concurrent `Agent()` ceiling and is read-only-scoped. `mode:` values and the fan-out phrase are protocol tokens preserved verbatim in every locale; only the parenthesized scope qualifier translates.
- **Block 2** — `applied lessons:` naming the relevant memory files, plus `source_session_id: <UUID from moai session current>`. When the CLI or registry is unavailable, emit the prescribed fallback line verbatim (see the sidecar); that fallback is graceful degradation, not an anti-pattern.
- **Block 3** — separator + `Preconditions:` header (locale rendering per § Localization Table).
- **Block 4** — numbered `<N>) <action> → <expected outcome>`, each independently verifiable by a command or a file check. Maximum 4.
- **Block 5** — separator + `Run:` carrying a **single primary action**, which is always the work-starting command. [HARD] `/moai goal` is arm-only and starts no work, so it never occupies this line alone — a goal armed with nothing running spins idle turns to the ceiling. Where the next SPEC declares a machine-verifiable end-state, the goal is armed *alongside* the primary action, after Implementation Kickoff Approval.
- **Block 6** — separator + a workflow-context header carrying exactly one next action: `After merge:` for a PR-based flow, `Follow-up:` for trunk-based no-PR. Omit the block entirely on a single-SPEC close with nothing queued.


## Paste-Time Activation Matrix

Handoff directives by activation mechanism: (a) paste-time keywords (`ultrathink`, bare `ultracode`) and (b) the fan-out phrase fire from a pasted body; (c) orchestrator-interpreted text (`mode:` seed, Block 5 `/moai …` including the `/moai goal` directive) routes via orchestrator reading; (d) user-only TUI commands (`/effort`, `/clear`) fire ONLY as a standalone user message. The goal-arming directive is class (c) — the orchestrator reads and routes it, so it needs no standalone user message.

> **Full classification table**: `session-handoff-examples.md` § Paste-Time Activation Matrix.


## Auto-Injected Resume Flow (mode=auto)

[ZONE:Evolvable] Where the project config `.moai/config/sections/handoff.yaml` sets `handoff.mode: auto`, the saved pending record (§ Emission-Time Save Obligation) is consumed automatically at the next `/clear` session start, collapsing the resume to **ONE** user message. This section is the SSOT for the flow; the render surface (`.claude/output-styles/moai/moai.md` §8) carries a compact emission clause + pointer only.

> **One-message flow, /clear-only injection boundary, and resumed-turn precondition verification**: moved to `session-handoff-examples.md` § Auto-Injected Resume Flow (mode=auto). In brief: the previous session saves via `moai handoff save`; at the next `/clear` (ONLY `clear` source) the handler claim-renames the pending record then injects the saved body verbatim; the user sends ONE message; injected preconditions are verified first.


### Invariants (both modes)

- **Implementation Kickoff Approval unchanged**: neither auto-injection nor a set goal pre-authorizes run-phase entry. The Implementation Kickoff Approval human gate remains required before run-phase entry in both modes.
- **Manual reversion is baseline-identical**: restoring `handoff.mode: manual` reverts runtime behavior to the pre-auto baseline — the injector's manual branch is a pure no-op that never touches the pending record, even a stale one — and the manual path documented in this file (the 6-block paste) is complete and self-sufficient without this section.
- **Fail-open everywhere**: save failures never block emission (§ Emission-Time Save Obligation); injection failures never block session start; a missing, stale, or already-claimed record degrades silently to the manual paste path.


## Auto-Memory Integration (Mandatory)

[ZONE:Evolvable] [HARD] When generating a resume message, the orchestrator MUST also:

1. Save the message to a memory project entry. Filename pattern: `project_<epic>_<spec>_<status>.md` (e.g., `project_epic8_wf002_complete.md`). The `<epic>` token reflects the multi-SPEC grouping per sprint-round-naming.md (the legacy `<sprint>/<wave>` tokens are retired).
2. Include the resume message verbatim in that file under a `## Next Session Entry Point (paste-ready resume message)` heading (locale variant per the Localization Table memory-heading row; e.g. ko `## 다음 세션 시작점`).
3. Update `MEMORY.md` index with a one-line entry pointing to the new memory file.
4. Mark superseded entries (if any) with `[SUPERSEDED by <new-file>]` prefix per Lessons Protocol in `.claude/rules/moai/core/moai-constitution.md` §Lessons Protocol.
5. Annotate the MEMORY.md index entry with a `(session: <UUID-8-char-prefix>)` parenthetical when the SPEC was worked across multiple sessions (cross-references the `source_session_id` in Block 2 — enables readers to correlate the resume back to its originating session).
6. **Close-time pruning (auto-resume era)**: on SPEC close, the consumed verbatim resume block inside the memory topic file (the next-session-start-point section) SHOULD be pruned to a one-line summary — once the record has been consumed, verbatim preservation is owned by the `.moai/state/handoff/consumed/` audit trail, not the memory file. The generation-time verbatim-persistence obligation above (items 1-2) is UNCHANGED: the resume message is still saved verbatim to memory when emitted; the pruning binds only later, at SPEC close (temporal separation). Forward-looking only — no retroactive rewrite of existing memory files is mandated. This stops double-storage growth and keeps the always-loaded memory index within the loader's line/byte cap.

This ensures the message survives `/clear` and is discoverable at the start of the next session's context.


## Worktree-Anchored Resume Pattern

> [ZONE:Evolvable] [HARD] When the work happened inside a worktree, the resume message MUST prepend **Block 0 (cwd anchoring)** before the standard 6-block structure, and Block 4 gains precondition `0) git rev-parse --show-toplevel → <worktree-path>`. Block 0 uses the **canonical EnterWorktree-first forms** — `moai cc -w <name>` for a worktree under `.claude/worktrees/`, `moai cc -w <abs-path>` for one under `~/.moai/worktrees/`, or `EnterWorktree(<path>)` for current-session re-entry — NOT a bare `cd <worktree>` shell instruction. Work in the main checkout (the default) needs only the standard 6-block. Full: `session-handoff-examples.md` § Worktree-Anchored Resume Pattern.


## Diet Constraints

[ZONE:Evolvable] [HARD] A paste-ready resume message is "next session minimum executable context" — NOT an audit trail, history record, or ceremonial commitment record. Two concrete anti-patterns illustrate the hazard (full AP-D-001..005 catalogue + 9-item pre-emit checklist + V0 Abort Gate Doctrine in `session-handoff-examples.md`):

- **AP-D-002**: precondition body prose (history/lesson narrative/cumulative pattern) → keep only a one-line verifiable command + STRICT criterion (≤ 200 chars).
- **AP-D-003**: Block 5 sub-step nesting (Phase 0 + Phase 1 + Phase 1B style multi-phase 11-substep) → compress into a single primary action; sub-detail belongs in SPEC artifacts.

Full Diet Constraints catalogue (AP-D-001..005 + 9-item pre-emit checklist) and V0 Abort Gate Doctrine in `session-handoff-examples.md` § Diet Constraints (Full Catalogue) + § V0 Abort Gate Doctrine.


## V0 Abort Gate Doctrine

> [ZONE:Evolvable] [HARD] The paste-ready Block 4 V0 precondition uses **lsof + cwd cross-validation** (NOT a raw `ps aux` count). When V0-b ≥ 1 OR V0-c ≥ 3, spawning implementation agents is prohibited and the session ends (no force-through). Canonical: `session-handoff-examples.md` § V0 Abort Gate Doctrine.


## Cross-references

<!-- self-check sentinel — references the render surface's structural invariant by content, not line number, so it survives line drift. This is mitigation + visibility (it surfaces drift to a reading editor), NOT mechanical prevention. A future editor who changes one surface without reading the other surface's sentinel produces silent drift; the only mechanical catch is a deferred Go lint rule (see the session-handoff SSOT-align doctrine §F.6 follow-up). -->
**Drift-mitigation self-check sentinel (SSOT → render surface).** This file is the SSOT; `.claude/output-styles/moai/moai.md §8` is the render surface. Before committing any edit to the Localization Table, the 6-block skeleton, the cut-line marker spec, the Pre-emit self-check labels, § Emission-Time Save Obligation, or § Auto-Injected Resume Flow in THIS file, verify the parity check against the render surface: the moai.md §8 Localization Contract carries the full 4-locale table (en / ko / ja / zh); this file carries the en / ko subset inline with the ja / zh columns relocated to `session-handoff-examples.md`, the moai.md §8 Pre-emit self-check labels must use the same concern-name qualifiers (`paste-ready budget` / `localization render` / `session-handoff template completeness`) as this file, and the moai.md §8 emission clause (the `moai handoff save` save duty + auto-flow pointer) must remain a compact pointer consistent with § Emission-Time Save Obligation and § Auto-Injected Resume Flow here (pointer, NOT full duplication). If the two surfaces have diverged, this is the canonical surface — update the render surface to match.

- `.claude/rules/moai/workflow/context-window-management.md` § Context Window Targets — the per-model-class threshold SSOT for `/clear` and Trigger #1 (this file carries no inline model-class numbers to avoid label drift).
- `.claude/output-styles/moai/moai.md` §6 (Persistence & Context Awareness)
- `.claude/output-styles/moai/moai.md` §8 (Response Templates → Session Handoff) — the canonical render surface for the 6-block template + pre-emit self-check; this file is the SSOT, moai.md §8 is the render surface (bidirectional link).
- `.claude/rules/moai/core/moai-constitution.md` §Lessons Protocol — auto-memory + `[SUPERSEDED by ...]` convention
- `.moai/config/sections/handoff.yaml` — `handoff.mode` (`manual`/`auto`) + `handoff.guide` config keys consumed by § Auto-Injected Resume Flow
- `.claude/rules/moai/workflow/goal-directive.md` § Goal-Presentation Timing — the arm-only property and the Kickoff-gate timing that Block 5 implements; § MoAI Integration Notes — the auto-injected resume path
- CLAUDE.md §11 (Error Handling) — token-limit recovery
- large-SPEC wave-split rationale
- Block 0 cwd anchoring + the single/multi-session decision rationale
- worktree isolation + --team base mismatch

---

Status: HARD operational rule, applies to all multi-phase MoAI workflows


