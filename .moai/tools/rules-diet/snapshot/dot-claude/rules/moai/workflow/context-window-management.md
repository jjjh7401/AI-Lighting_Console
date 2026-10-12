# Context Window Management

Long-horizon session continuity guidance for both users and the MoAI orchestrator.

> Deferred detail (graduated compaction, Reduction Ladder, detection heuristics, GLM note) → `context-window-management-deferred.md`. Kept here: per-model thresholds, user/orchestrator duties; prefer `.moai/state/context-usage.json` (`stage`, `raw_pct`) over byte heuristics; cheaper moves (`/compact`, `/rewind`) come before `/clear`.

## Why This Matters

Anthropic SSE streams stall (`stream_idle_partial`) near the context window ceiling — intermittent but predictable above the model-specific threshold. Reference: large-SPEC SSE-stall mitigation.

> **CC 2.1.196 watchdog note**: The streaming idle watchdog is now default-on for all providers — it aborts and retries a response stream that produces no events for 5 minutes (`CLAUDE_ENABLE_STREAM_WATCHDOG=0` disables). This softens the mid-stream-hang *consequence* (auto-abort+retry) but not the stall *hazard* itself — a stall near the ceiling still wastes a turn. The `/clear` thresholds below are unchanged.

> ↪ deferred → `context-window-management-deferred.md`: Claude Code's Graduated-Compaction Layers (consumed, not implemented)

## Context Window Targets

[ZONE:Evolvable] [HARD] Operational threshold is **model-specific**. Larger windows tolerate higher percentage utilization before stall risk dominates; smaller windows hit the operational ceiling later in percentage terms but with less absolute headroom:

| Model class | Window | Handoff threshold | Absolute ceiling |
|-------------|--------|-------------------|------------------|
| Opus 5 (1M) | 1,000,000 tokens | **50%** | ~500,000 tokens |
| Opus 4.8 (1M) | 1,000,000 tokens | **50%** | ~500,000 tokens |
| GLM-5.3 via `moai glm`/`moai cg` (1M) | 1,000,000 tokens | **50%** | ~500,000 tokens |
| Fable (256K) | 256,000 tokens | **90%** | ~230,000 tokens |
| Sonnet/Opus standard (200K) | 200,000 tokens | **90%** | ~180,000 tokens |
| Haiku (200K) | 200,000 tokens | **90%** | ~180,000 tokens |

The model-specific threshold is the operational ceiling — beyond it, plan for a `/clear` before the next non-trivial action. Both this rule and `session-handoff.md` Trigger #1 read from this same table.

> ↪ deferred → `context-window-management-deferred.md`: GLM-5.3 context window (Issue #653)

## User Responsibilities

User monitors via Claude Code statusline / `/cost` and intervenes at threshold (50% on 1M / GLM-5.3, 90% on 200K/256K).

[ZONE:Evolvable] [HARD] When usage crosses the model-specific threshold:
1. Save in-flight state to `.moai/specs/<SPEC-ID>/progress.md` if not already saved (orchestrator does this automatically)
2. Run `/clear` to flush the conversation context
3. Paste the **resume message** (provided by the orchestrator before the clear) to continue

[ZONE:Evolvable] [HARD] When usage crosses 95% on any model:
- The next action MUST be `/clear` — no further large work in the current session
- Stall risk is severe; agent invocations may fail mid-stream
- This is the absolute hard stop regardless of model class

## Orchestrator Responsibilities

The orchestrator MUST proactively recognize the model-specific boundary and prepare the user for a clean handoff.

[ZONE:Evolvable] [HARD] Pre-clear announcement: When the orchestrator detects accumulated context (input + output) approaching the model-specific threshold (50% on 1M / GLM-5.3, 90% on 200K/256K), it MUST:
1. Stop initiating new large tool calls or `Agent()` delegations
2. Persist all in-flight progress to `.moai/specs/<SPEC-ID>/progress.md`
3. Emit a structured "resume message" the user can paste verbatim after `/clear`
4. Recommend `/clear` via natural-language guidance (status announcement, not a question — `AskUserQuestion` not required)

[ZONE:Evolvable] [HARD] Resume message format: include all of the following so the next session is self-sufficient (locale renderings per `session-handoff.md` § Localization Table — do not redefine a parallel format here):
```
ultrathink. Resume Epic <N>. SPEC-<ID> — <approach summary>.
applied lessons: <memory file names>.
progress.md path: .moai/specs/SPEC-<ID>/progress.md
Run: <one-line command>.
After merge: <next SPEC or /moai sync>.
```

Paste-ready, no editing required.

> ↪ deferred → `context-window-management-deferred.md`: Detection Heuristics

## Applies To

All MoAI workflows: `/moai plan|run|sync`, multi-SPEC Epics, iterative loops (`/moai loop`, GAN loop).

> ↪ deferred → `context-window-management-deferred.md`: Cross-references

