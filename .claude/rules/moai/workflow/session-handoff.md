# Session Handoff Protocol

Long-running session continuity: clean transitions across context boundaries via paste-ready resume messages.

> **Loading scope**: Intentionally always-loaded (no `paths:` restriction) because Trigger #3 (user explicit session-end) can fire from any session context, including those without SPEC files. The always-loaded cost is justified by cross-cutting applicability.

> Deferred detail (cut-line spec, field-by-field spec, activation matrix, auto-injected flow, memory steps, worktree block 0, diet constraints) → `session-handoff-deferred.md`; Read it when emitting a handoff. Kept here: triggers, save obligation, the 6-block skeleton, ko labels, output surface. Emission also requires: save the block verbatim to memory `project_<epic>_<spec>_<status>.md` under `## 다음 세션 시작점`, update `MEMORY.md`, and render the cut-line block in the response body.

## Why This Matters

Long workflows (multi-SPEC Epics, multi-milestone implementation) accumulate context that exceeds the window or benefits from fresh start. Without a standardized handoff, session boundaries lose work-in-progress. This rule defines when to emit a paste-ready resume, the 6-block structure, and auto-memory integration that persists across `/clear`.

## When To Generate (5 Triggers)

[ZONE:Evolvable] [HARD] The orchestrator MUST emit a paste-ready resume message when ANY of these conditions activate:

| # | Trigger | Detection |
|---|---------|-----------|
| 1 | Context usage crosses model-specific threshold (cumulative input+output) | Model-specific percentage threshold (1M-context models vs 200K-context models) — see `.claude/rules/moai/workflow/context-window-management.md` § Context Window Targets for the per-model-class threshold table (the authoritative SSOT for the numeric thresholds; this file carries no inline model-class numbers to avoid label drift). |
| 2 | SPEC phase completion (plan/run/sync) within a multi-SPEC workflow | Phase boundary in `.claude/rules/moai/workflow/spec-workflow.md` §Phase Transitions (after plan/run/sync phase finishes within a multi-SPEC SPEC ID series) |
| 3 | User explicitly requests session end ("세션 종료", "이번 세션 마무리", "next session") | Intent detection in user message |
| 4 | PR creation success when more SPECs remain in the current Epic | After `gh pr create` success + memory indicates >0 pending SPECs |
| 5 | Long-running multi-milestone task reaches a stable checkpoint | After milestone Mn complete + Mn+1 not yet started |

When NONE apply (single-turn, trivial task, read-only query), emit a brief completion confirmation. The threshold in Trigger #1 reflects asymmetric stall risk: 1M models tolerate higher absolute load; 200K models hit the ceiling earlier. The `/clear` policy in `context-window-management.md` is co-anchored to the same threshold per model class.

### Emission-Time Save Obligation (auto-resume wiring)

[ZONE:Evolvable] [HARD] When the orchestrator emits a paste-ready resume message (any of the 5 triggers above), it MUST also persist the cut-line-bounded main block verbatim as the pending handoff record: pipe the block to `moai handoff save --stdin --spec <ID> --phase <phase> [--goal "<condition>"] [--ultrathink] [--ultracode] [--lang <conversation_language>] [--session <uuid>]` (body fed via stdin). `--goal` is recorded ONLY when the next SPEC is run-phase AND declares a machine-verifiable end-state — the same condition under which Block 5 carries a `/moai goal` directive (§ Canonical Format, Field-by-Field Block 5); `--lang` snapshots the current `conversation_language`; `--session` carries the same session id as Block 2's `source_session_id` when available.

[ZONE:Evolvable] [HARD] **Fail-open invariant**: when the `moai` CLI is absent from PATH or `moai handoff save` exits non-zero, the orchestrator emits the paste-ready surface UNCHANGED — a save failure never blocks, delays, or alters handoff emission, and no retry loop is entered. The manual paste path is fully functional without the save; the save is an additive persistence step, never a gate.

The saved record (`.moai/state/handoff/pending.json`) is consumed by the auto-injected flow when the project config sets `handoff.mode: auto` — see § Auto-Injected Resume Flow. Under the distributed default `handoff.mode: manual` the record is inert (the session-start injector never touches it, even when stale), and this save obligation still applies — flipping the mode later requires no doctrine change.

## Canonical Format (Verbatim Spec)

[ZONE:Evolvable] [HARD] Resume message MUST follow this exact 6-block structure, **bounded by cut-line markers** (see § Cut-line Marker Specification below for the literal marker format, Unicode-preservation rules, and locale translation contract). Cut-line markers sit **inside** the fenced text block alongside the content so they are copied verbatim with the message; this provides the user an unambiguous copy boundary in long terminal scrollback:

```
✂──── 여기부터 복사 ────✂

ultrathink. <SPEC-ID> <phase> <entering verb>.
mode: <value>   ← emit ONLY when the seeded orchestration mode ≠ solo-sequential; value ∈ {parallel-subagents | agent-team | dynamic-workflow} → Phase 4 Mode 4 / 3 / 6. OMIT for solo-sequential (default) → v1 byte-identical. When mode = dynamic-workflow, ALSO append bare `ultracode` to the opener line above (paste-time trigger keyword; the session-persistent `/effort ultracode` slash form is a separate variant — per Field-by-Field Spec, Block 1). When mode = agent-team, append `--team` to the Block 5 run command. When mode = parallel-subagents, append the fan-out steering phrase `fan out subagents (<read-only investigation scope>)` to the opener line above (paste-time steering phrase — per Field-by-Field Spec, Block 1).
applied lessons: <memory-file-1>, <memory-file-2>, ...

Preconditions:
1) <verifiable precondition 1>
2) <verifiable precondition 2>
N) <verifiable precondition N>

Run: <command-or-action>

After merge: <next-action-or-spec>

✂──── 여기까지 복사 ────✂
```

> ↪ deferred → `session-handoff-deferred.md`: Cut-line Marker Specification

### Localization Table

The cut-line marker text AND the 6-block skeleton verbs/headers translate per `conversation_language`. This table carries the en / ko columns inline (the inline locales); the full 4-locale table (en / ko / ja / zh) lives in `session-handoff-examples.md` § Localization Table (Full 4-Locale). Cross-verified for consistency with `.claude/output-styles/moai/moai.md §8` (the canonical render surface).

| Element | English | Korean |
|---------|---------|--------|
| Cut-line top text | `Copy from here` | `여기부터 복사` |
| Cut-line bottom text | `Copy to here` | `여기까지 복사` |
| Block 1 entering verb | `entering` | `진입` |
| Block 3 Preconditions header | `Preconditions:` | `전제 검증:` |
| Block 5 Run header | `Run:` | `실행:` |
| Block 6 After-merge header (PR workflow) | `After merge:` | `머지 후:` |
| Block 6 Follow-up header (trunk no-PR) | `Follow-up:` | `후속:` |
| Memory heading | `## Next Session Entry Point` | `## 다음 세션 시작점` |

Read `conversation_language` from `.moai/config/sections/language.yaml` at render time; substitute the localized text between the `✂────` decorators (cut-line markers) while keeping `✂` and `─` characters verbatim, and substitute the locale rendering for each Block 1/3/5/6 placeholder and the memory heading (per § Auto-Memory Integration) when emitting the paste-ready message.

**Fallback rule for locales not in the table.** The inline table above lists concrete renderings for en / ko only. When `conversation_language` is ja, zh, or any other ISO-639 code whose language column is NOT in the inline table (e.g. `fr`, `de`, `es`, `pt`, `vi`), consult the full 4-locale table in `session-handoff-examples.md` for ja / zh renderings; for all other locales, English is the canonical fallback skeleton and each label translates to that locale using the naturalization principle (idiomatic phrasing a native reader expects, never literal word-by-word transliteration). In other words: locales not in the inline table fall back to the English column for the structural skeleton, with the label text rendered in the configured ISO-639 language — ISO-639 not in the table ⇒ English-skeleton fallback, not English-output.

> ↪ deferred → `session-handoff-deferred.md`: Field-by-Field Specification

## Output Surface (User-Facing)

[ZONE:Evolvable] [HARD] Emitting a resume message means **rendering it in the response body of the turn that generates it** — not storing it. At session end the orchestrator displays all three of: (1) the main message in a fenced ```text``` block **bounded by cut-line markers** (per § Cut-line Marker Specification — marker text translated per `conversation_language`, `✂`/`─` symbols preserved verbatim) for verbatim paste, (2) the memory file path, (3) a one-sentence summary of what next session continues.

**reference-instead-of-render (named anti-pattern).** Writing the resume into the memory topic file (§ Auto-Memory Integration) and then merely *citing* that file path in the completion report is NOT emission. The memory write and the `moai handoff save` record are both persistence steps; neither reaches the user, so a report stating the resume "is saved in memory" while rendering no block leaves the user with nothing to paste. The hazard is structural rather than a lapse of attention: § Auto-Memory Integration is discharged by concrete tool calls whose results are visible, so the turn feels complete once they succeed — while the render, being ordinary response text, is the one step with no tool call to confirm it happened. Persistence without rendering is an unobserved completion claim under `.claude/rules/moai/core/verification-claim-integrity.md` §1.1 surface 1.

**Render-surface dependency.** The per-persona banner template for this render lives in the active output style, and not every persona defines one. Where the active style carries no handoff banner, this obligation still binds unchanged — render the cut-line-bounded block from the § Canonical Format skeleton directly, styled to match that persona's other banners. A missing banner template is never a reason to skip the render.

### Pre-emit self-check (emission surface) — 3 items

- [ ] Is the cut-line-bounded block rendered in THIS response body — not only written to memory or persisted via the CLI?
- [ ] Are all three surface items present: the block, the memory file path, and the one-sentence continuation summary?
- [ ] Does the completion report avoid claiming the handoff was delivered when only the persistence steps ran?

## Anti-Patterns

> General resume-hygiene anti-pattern bullet list moved to `session-handoff-examples.md` § Anti-Patterns. See also § Diet Constraints (AP-D-001..005) and § V0 Abort Gate Doctrine (AP-V-001..004).

> ↪ deferred → `session-handoff-deferred.md`: Worktree-Anchored Resume Pattern

