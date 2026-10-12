---
description: "Deferred detail moved verbatim out of moai-constitution.md (t613 rules diet); the SSOT file keeps pointers and the [HARD] one-liners"
paths: "**/moai-constitution.md"
---

# moai-constitution — deferred detail (t613)

> 원문 그대로 옮긴 상세. 출처: `.claude/rules/moai/core/moai-constitution.md`. 조항의 효력은 그대로다 (삭제 아님, 적재 위치만 바뀜).

## Opus 5 / 4.8 Prompt Philosophy

Reasoning-intensive agents targeting `claude-opus-5` (the default Opus as of Claude Code 2.1.219) and `claude-opus-4-8` (and 4.7+) must follow Anthropic's official prompt guidelines (platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-8).

Rules:
- One-turn fully-loaded: deliver intent + constraints + completion criteria + file locations in a single agent prompt. Avoid multi-turn ping-pong which wastes tokens.
- Adaptive Thinking: do NOT set fixed thinking budgets via `budget_tokens` — Opus 4.7+ and 4.8 reject fixed budgets with HTTP 400. Enable thinking via `thinking: {type: "adaptive"}` and let the model self-allocate reasoning depth.
- State scope explicitly: Opus 4.8 follows instructions literally and does not silently generalize from one item to another. When an instruction should apply broadly, say so (e.g. "apply to every section, not just the first").
- Remove Opus 4.6-era defensive scaffolding: "double-check X before returning", "verify N times", "explicitly confirm before proceeding" patterns are counterproductive given literal instruction following.
- [ZONE:Evolvable] [HARD] Principle 4 — Fewer subagents spawned by default: Opus 4.7+ / 4.8 does not auto-spawn subagents. This behavior is steerable: when fan-out helps, instruct explicitly "Spawn multiple subagents in the same turn when fanning out across items or files; do not spawn a subagent for work you can complete directly in one response."
- [ZONE:Evolvable] [HARD] Principle 5 — Fewer tool calls by default, more reasoning: Opus 4.7+ / 4.8 prefers reasoning over tool invocation. When tool use is expected, specify when and why to use each tool (Grep for content search, Glob for file discovery, Read for full-file context). Raise effort to high/xhigh to increase tool usage when needed.
- Effort defaults: Opus 5 and Opus 4.8 default to `effort: high` on all surfaces (Claude API and Claude Code); `xhigh`/`max` are available on Opus 5, Sonnet 5, Opus 4.8, and Opus 4.7. Opus 5 carries a previously-set effort level across sessions (no hold). Set `effort: xhigh` for coding/agentic work, keep a minimum of `high` for intelligence-sensitive work, and step down to `medium`/`low` only for speed-critical or simple tasks (route effort by role rather than by named agent).
- Per-agent effort calibration: see `.claude/rules/moai/development/agent-authoring.md` § Effort-Level Calibration Matrix for the retained-agent default-effort table and the archived-agent legacy reference.


## Lessons Protocol

Capture and reuse learnings from user corrections and agent failures across sessions.

Rules:
- When user corrects agent behavior, capture the pattern in auto-memory
- Store lessons as topic files in auto-memory — one fact per `feedback_*.md` file under `~/.claude/projects/{project-hash}/memory/`, indexed by `MEMORY.md`. This topic-file convention (`feedback_*.md` topic files + the `MEMORY.md` index) is the single designated lesson store; the legacy `lessons.md` is superseded (kept on disk marked `[SUPERSEDED]`, content not migrated)
- Each lesson entry: category, incorrect pattern, correct approach, date added
- Review relevant lessons before starting tasks in the same domain
- Lesson categories: architecture, testing, naming, workflow, security, performance, hardcoding
- Maximum 50 active topic files per project; archive older or superseded topic files into `memory/_archive/` (never delete — archive preserves the audit trail)
- Lessons are additive: never overwrite a lesson, append corrections as updates
- To supersede a lesson, add `[SUPERSEDED by #{new_lesson_number}]` prefix to the old entry
- Session start: scan lessons for patterns matching current task domain
- Repo-local lessons inbox (`.moai/lessons-inbox.jsonl`): tool failures and test failures append structured stubs (timestamp, event_key, summary, source) here as they occur. **Drain actor: the MoAI orchestrator. Drain trigger: when the inbox backlog grows large enough to obscure recurring patterns (a cluster of same-`event_key` stubs), the orchestrator drains these stubs into topic-file lesson entries as part of the Lessons Protocol — converting each recurring `event_key` cluster into one candidate `feedback_*.md` topic file before human review, and discarding one-off noise (single-occurrence stubs with no recurring pattern). Drained stubs are marked (the drain-marking mechanism is an implementation detail).**

Harness Edit Discipline (decision observability):
- Harness surface tag: each lesson entry SHOULD carry a `surface:` tag naming the harness component it binds to (rule / agent / skill / hook / config / template / workflow) — enables clustering recurring failures by component
- Prediction pairing: when a lesson motivates a harness edit (a change to a rule, agent, skill, hook, config, or template), the lesson entry SHOULD record `prediction:` — the falsifiable expected effect (which failure class stops recurring) — and later `verified: true|false` with the observed evidence
- Held-in / held-out acceptance: before accepting a harness edit, verify BOTH (a) held-in — the edit demonstrably addresses the motivating failure (reproduce or cite the failing case), and (b) held-out — existing guards still pass (lint, mirror-parity, neutrality checks, test suite). An edit failing either check is rejected, not merged
- Preserve rejected candidates: a rejected or reverted harness edit is recorded as a lesson entry with `verified: false` and the rejection reason — never silently discarded. This prevents re-attempting known-bad edits
- A falsified prediction (`verified: false`) is itself a signal: re-diagnose the root cause before authoring a second edit to the same surface

Auto-Capture Triggers:
- When a fix/refactor commit completes, check if the change matches a known anti-pattern category
- If match found, propose a lesson entry to the user via AskUserQuestion
- Auto-generated lesson entries include: category, incorrect pattern, correct approach, date, tags
- Duplicate detection: check existing lessons before proposing new entry

Domain Matching Algorithm:
- Extract domain keywords from current SPEC (title, scope, modified file paths)
- Match lesson categories against extracted keywords
- Match lesson tags against modified package names
- Relevance score: categories match (weight 2) + tags match (weight 1)
- Select top 5 lessons by relevance score, then by recency

Integration Points:
- run.md Phase 1: Load filtered lessons into agent context before implementation (see Lessons Loading section)
- /moai fix completion: Propose lesson capture after successful fix
- /moai loop completion: Propose lesson capture after successful iteration cycle

<!-- moai:evolvable-start id="agent-core-behaviors" -->

