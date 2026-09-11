---
paths: "**/.claude/agents/**,**/.claude/worktrees/**,**/.claude/teams/**"
---

# Worktree Integration Guide

Integration guide for MoAI Worktree and Claude Code Native Worktree systems.

> **Detail companion**: `worktree-integration-detail.md` (paths-scoped to this file) — the feature comparison table, `claude --worktree` invocation forms, the `background:` / `worktree.baseRef` / `.worktreeinclude` settings detail, the sentinel-key glossary, the mechanism-selection lists, the hybrid integration pattern, the per-role frontmatter recipes, the prompt-path tables and examples, the minimum-version table, and the troubleshooting table. This stub keeps every `[HARD]` / `[ZONE:Frozen]` clause and every externally cross-referenced section; load the companion when configuring a worktree, choosing between the mechanisms, or writing a prompt for a worktree-isolated agent.

## Overview

MoAI-ADK supports two complementary worktree systems for isolated development:

**Claude Code Native Worktree** (`.claude/worktrees/`):
- Ephemeral, session-scoped isolation
- Automatic cleanup when session ends
- Used for subagent isolation via `isolation: worktree` in agent definitions (v2.1.49+)
- CLI access: `claude --worktree` or `claude -w` (user-level flag)

**MoAI Worktree** (`~/.moai/worktrees/{ProjectName}/`):
- Persistent, SPEC-scoped workspaces in global home directory
- Managed via `moai worktree` CLI commands
- Used for multi-session SPEC development and team collaboration

> **Feature comparison table** — path, lifetime, purpose, CLI, cleanup, branch strategy, team use, state persistence, and hook support per system: `worktree-integration-detail.md` § Comparison Table.

## Terminology Glossary

This glossary is the canonical definition surface for the L1 / L2 worktree-layer terms used across the MoAI rule set. (The former L3 "launch action" tier is retired with `/moai plan --worktree`; a worktree is now entered, not provisioned by a workflow step.) Other rules (`spec-workflow.md`, `worktree-state-guard.md`, `session-handoff.md`, and `CLAUDE.md` §14) cross-reference `§ Terminology Glossary` for these definitions.

| Layer | Name | What it is | Path / Trigger | Lifetime | Owner |
|-------|------|-----------|----------------|----------|-------|
| **L1** | Claude-native session worktree | Session-scoped isolation owned by a Claude Code session. Entered by short name — `moai cc -w <name>` (the launcher passes `-w` straight through to `claude`), `claude -w <name>`, or the in-session `EnterWorktree(<name>)` tool — or materialized autonomously for a subagent spawned with `Agent(isolation: "worktree")` (auto-named; the runtime decides whether to materialize it). | `.claude/worktrees/<name>/` on branch `worktree-<name>` (auto-named subagent trees use the runtime's generated name; kanban/team card worktrees rename to `WT-<slug>` per the WT- naming rule below); base per `worktree.baseRef` (`fresh` = remote default branch by default) | Session-scoped — the running session holds a `git worktree lock` on the tree by design (held while the session runs, released on its exit; a dead session's lock auto-releases on Claude Code 2.1.210+); disposed via the session-end keep/remove prompt, or `git worktree unlock` + `git worktree remove` once the session is done | Claude Code runtime. `moai worktree` does NOT manage these trees — they are never in its registry, so `done` / `clean` / `recover` have nothing to close on them |
| **L2** | MoAI persistent SPEC worktree | A persistent, SPEC-scoped working directory entered **by absolute path** — `moai cc -w ~/.moai/worktrees/<project>/<SPEC>`. Used for multi-session SPEC development (run + sync phases reuse the same L2 worktree). | `~/.moai/worktrees/<project>/<SPEC>/` | Persistent — lifecycle owned by the `moai worktree` verbs (`sync`, `remove`, `clean`, `recover`, `done`, plus the guard trio `snapshot` / `verify` / `restore`); disposed only via `moai worktree done SPEC-XXX` after both run + sync PRs merge | MoAI (user-managed via `moai worktree` CLI) |

Relationships:
- A **short name** passed to `-w` (`moai cc -w <name>`) resolves against `.claude/worktrees/<name>/` and creates an **L1** tree, not an L2 one; an **L2** persistent worktree is entered by absolute path (`moai cc -w <abs-path>`). `moai worktree` deliberately carries no creation verb — entering is the launcher's job (the former `/moai plan --worktree` launch action and `moai worktree new` command are both retired).
- An **L1** ephemeral worktree is materialized autonomously by the Claude Code runtime for an isolated subagent; it is independent of L2 and may occur inside either the main checkout or an L2 worktree.
- When work happens inside an L2 worktree, the paste-ready resume MUST anchor the next session there (Block 0) per `session-handoff.md` § Worktree-Anchored Resume Pattern.

[HARD] **`moai worktree` verbs are L2-only.** An L1 tree under `.claude/worktrees/` is never registered with `moai worktree`, so `done`, `clean`, and `recover` cannot act on it — `moai worktree done` on an L1 tree is a category error, not a disposal. L1 disposal is the session-end keep/remove prompt, or `git worktree unlock` + `git worktree remove` after the session releases its lock. The lock itself is designed behavior, not a defect: it is held while the session runs and released on exit, and a dead session's lock auto-releases on Claude Code 2.1.210+ — a locked tree at disposal time means a live session still owns it, and the remediation is the unlock guidance, not a cause investigation.

[HARD] **An unpushed worktree branch is the work's only instance.** A card or lane worktree is created from inside the session with the Claude tool (`EnterWorktree(<name>)`) or launched by the operator (`moai cc -w <name>`) — never with a bare `git worktree add`. Until its branch has been integrated and the remote merge has landed, dispose of no worktree, L1 or L2: disposal before that destroys the only copy of the work.

[HARD] **Kanban/team card worktree branches carry the `WT-` prefix followed by a descriptive slug.** `EnterWorktree(<name>)` auto-names its branch `worktree-<name>`; for card worktrees, rename immediately after creation with `git branch -m WT-<slug>` (renaming the checked-out branch inside a worktree is safe — the tree, its lock, and the session anchoring are unaffected — and `moai cc -w <name>` re-entry resolves by tree name, not branch name). `WT-` is the session-worktree branch convention (`SessionWorktreeBranchPrefix`, `internal/cli/session_worktree.go`).

[HARD] **The slug describes the change; the card id stays out of the branch name.** At most 3 hyphen-separated tokens, at most 24 characters, lowercase `a-z0-9-` — `WT-branch-naming`, not `WT-t0`. The **worktree directory** still carries the card id (`.claude/worktrees/<card-id>`), which is what the disposal tooling and the evidence path key on, so the id is never lost — it simply stops living in the branch name. Traceability moves onto the dispatch `card:` field, the commit messages, and the evidence path; the full contract is `kanban-dispatch.md` § Isolation is entered, never provisioned.

Nothing reads a card id back out of a branch name: `internal/cli/session_worktree_prmerge.go` matches the `WT-` prefix only (`strings.HasPrefix`), never the remainder. The prefix is load-bearing; the suffix is for humans.

The rename is also a disposal-path switch, and that is deliberate:

- Left as `worktree-<name>`, the tree is **invisible to the PR-merge auto-cleanup sweep** — that sweep enumerates `git worktree list` and considers only `WT-` branches — so disposal stays manual: the session-end keep/remove prompt, or `git worktree unlock` + `git worktree remove`.
- Renamed to `WT-<slug>`, the tree becomes a **sweep candidate**: where `Workflow.Worktree.AutoCleanup` is enabled (distributed default: off), the sweep removes a `WT-` worktree once its branch reads merged (gh `MERGED` state, or the `git branch --merged origin/main` fallback — squash-merge blind) and the tree is clean, re-checking dirtiness immediately before removal, and never while a live session is anchored in the tree.

Either way the unpushed-branch rule above still governs timing — the sweep's merged-branch condition is the same "after the remote merge" boundary. The lane-side procedure that consumes `WT-` branches lives in `kanban-dispatch.md` § Integration into the release branch is self-served.

## Claude Code 2.1.50+ Worktree Features

> **Launcher flag usage** — `claude --worktree` invocation forms, the auto-created path, the session-end keep/delete prompt, and the `--tmux` terminal constraints: `worktree-integration-detail.md` § `claude --worktree` (`-w`) Flag.

### `isolation: worktree` in Agent Frontmatter

For agents that need isolated execution (v2.1.49+):

```yaml
---
name: my-implementer
isolation: worktree   # Agent runs in its own isolated worktree
background: true      # Agent runs without blocking main conversation
---
```

When to use `isolation: worktree`:
- Implementation teammates that write files (write-capable implementation roles: implementer / tester / designer)
- Prevents file conflicts between parallel teammates
- Each agent gets its own clean worktree at `.claude/worktrees/<auto-name>/`

When NOT to use `isolation: worktree`:
- Read-only teammates (read-only research/review roles: researcher / analyst / reviewer)
- `permissionMode: plan` already prevents writes; adding isolation adds overhead without benefit

#### L1 ephemeral vs L2 persistent — `isolation: worktree` is NOT a re-entry mechanism

`Agent(isolation: "worktree")` creates a NEW **L1 ephemeral** worktree scoped to a single subagent invocation under `.claude/worktrees/<auto-name>/`. It is categorically distinct from an **L2 persistent** SPEC worktree entered with `moai cc -w <name>`. Conflating the two produces the worktree-masked flaky failure mode documented in `worktree-state-guard.md` — an L1 ephemeral worktree diverges from the L2 base and silently breaks parallel-session coordination.

`Agent(isolation: "worktree")` is NOT a re-entry mechanism for existing L2 persistent worktrees. To re-enter an existing worktree:
- **Current-session re-entry** (no `/clear`, same session continuing): use the Claude Code runtime tool `EnterWorktree(<path>)` — see `EnterWorktree` / `ExitWorktree` Tools below.
- **New-session launch** (post-`/clear` or new terminal): use the launcher flag `moai cc -w <name-or-abs-path>` (see the `-w` L2 absolute-path extension in `EnterWorktree` / `ExitWorktree` Tools below; flag invocation forms live in `worktree-integration-detail.md` § `claude --worktree` (`-w`) Flag).

> **Frontmatter and settings detail** — `background: true` semantics with its background-execution policy pointer, the `worktree.baseRef` setting (`fresh` / `head`, PR-based worktrees, the release-branch base trap, and the reset-vs-`baseRef` choice), and `.worktreeinclude` gitignored-file copying: `worktree-integration-detail.md` § `background: true` in Agent Frontmatter, § Worktree Base Branch (`worktree.baseRef`), § `.worktreeinclude`.

### `EnterWorktree` / `ExitWorktree` Tools

`EnterWorktree(<path>)` is the canonical mechanism for entering an existing worktree in the current session. The orchestrator's emitted guidance (paste-ready resume messages, Block 0 of the Worktree-Anchored Resume Pattern, in-session instructions) SHALL use `EnterWorktree(<path>)` for current-session worktree re-entry, replacing the shell-`cd`, `git -C <path>`, and subshell-`cd` patterns. A bare `cd` instruction SHALL NOT appear in orchestrator-emitted current-session-entry guidance; it remains valid only for human-typed, manual-shell contexts.

Claude can move the session into a worktree mid-session via the `EnterWorktree` tool (e.g. when the user says "work in a worktree"), creating one under `.claude/worktrees/`. Once inside, Claude can switch directly to another worktree by calling `EnterWorktree` with a target path; the previous worktree stays on disk untouched. `ExitWorktree` returns to the originating checkout. These are Claude Code runtime tools — MoAI does not mandate their use; they are the interactive counterpart to the launcher `-w` flag and `isolation: worktree` frontmatter.

`EnterWorktree` is complementary to, not replaced by, the launcher flag `moai cc -w <name-or-abs-path>`:

- **`EnterWorktree(<path>)`** — current-session re-entry (no `/clear`, same session continuing). Use this when the orchestrator is mid-turn and needs to move the active session into an existing worktree.
- **`moai cc -w <name>` (or `moai glm -w` / `moai cg -w`)** — new-session launch (post-`/clear` or new terminal). Use this as the Block 0 new-terminal launcher of the paste-ready resume. The `-w` flag accepts BOTH short names (resolved against `.claude/worktrees/<name>/`) AND absolute paths under `~/.moai/worktrees/<project>/...` (L2 persistent worktrees — this bullet is itself the L2 absolute-path extension; the flag's invocation forms live in `worktree-integration-detail.md` § `claude --worktree` (`-w`) Flag).

The shell-`cd` form (`cd <path> && <launcher>`), the `git -C <path>` form, and the subshell-`cd` form (`(cd <path> && ...)`) are DEPRECATED for orchestrator-emitted current-session worktree entry guidance. They break `Agent(isolation: "worktree")` CWD isolation (the agent's CWD is the worktree root; a `cd /absolute/path` bypasses it) and were the root cause of prior incidents where a sub-agent used `git -C` instead of `EnterWorktree` and was corrected mid-run.

## Worktree Selection Rules [ZONE:Evolvable] [HARD]

### Decision Tree

```
Is this a parallel write workers within a hierarchical team (e.g., manager-lead fan-out)?
  YES → Use Agent(isolation: "worktree") for write agents
        Do NOT use isolation for read-only agents
  NO ↓

Is this a multi-session SPEC development?
  YES → Enter a worktree: moai cc -w <name>
  NO ↓

Is this a user-initiated parallel session?
  YES → Use claude --worktree (-w)
  NO ↓

Is this a one-shot sub-agent task?
  YES → Use Agent(isolation: "worktree") if agent writes files
        Use Agent() without isolation if agent is read-only
  NO → No worktree needed
```

### HARD Rules

- [ZONE:Evolvable] [HARD] Implementation leaf workers spawned in parallel by `manager-lead` (or any parallel-write fan-out shape) MUST use `isolation: "worktree"` when spawned via Agent()
- [ZONE:Evolvable] [HARD] Read-only teammates (read-only research/review roles: researcher / analyst / reviewer) MUST NOT use `isolation: "worktree"` — read-only enforcement rests on tool restriction (`Explore`, or a `tools:` list omitting Write/Edit); the spawn-time `mode` parameter is deprecated and ignored since Claude Code v2.1.213, so a teammate is read-only only when its tools cannot write
- [ZONE:Evolvable] [HARD] One-shot sub-agents that write files across 3 or more paths per invocation MUST use `isolation: "worktree"`. This includes write-heavy retained agents (manager-develop), per-spawn `Agent(general-purpose)` specialists with a write-heavy domain whitelist (e.g. backend / frontend / devops / refactoring), and team-mode role profiles (implementer, tester, designer).
<!-- @MX:ANCHOR: WorktreeMUSTRule — invariant contract; all write-heavy agents MUST declare isolation:worktree; enforced by LR-05 lint rule -->
<!-- @MX:REASON: MUST level required to eliminate silent file-write conflict failure mode in parallel Agent() execution. -->
- [ZONE:Evolvable] [HARD] GitHub workflow agents (fixer agents in /moai github issues) MUST use `isolation: "worktree"` for branch isolation

### Parallel-Session Branch Conflict Auto-Isolation

[ZONE:Evolvable] [HARD] **When** the orchestrator detects (via the Pre-Spawn Sync Check active-sessions registry OR the Pre-Edit Sync Check, `.moai/state/active-sessions.json`) that ≥1 foreign active session is on the same checkout during **any write work** — whether worktree entry was chosen OR the orchestrator is editing the shared tree directly (direct main-session Edit/Write/Bash, which bypasses the spawn gate; see `.claude/rules/moai/core/agent-common-protocol.md` § Pre-Edit Sync Check) — the orchestrator SHALL auto-create one worktree per foreign registry entry (or isolate the direct-edit work into a worktree) to prevent cross-session branch-state interference. This auto-isolation procedure resolves the parallel-session branch conflict mechanically rather than surfacing it as a manual race. The "worktree entry is chosen" conjunct is no longer required: a foreign active session during direct-edit work triggers isolation too, because direct edits share the same branch-state mutable surface as spawned-agent writes.

**Conservative predicate** — ANY foreign active-session registry entry triggers auto-isolation. False positives are cheap (an extra worktree is inexpensive and user-deletable); false negatives corrupt the working tree (a genuine conflict goes unresolved and produces cross-session branch-state interference). Stale-registry false positives MAY produce a worktree that the user later deletes.

**Naming scheme** — each auto-created worktree is named `auto-<session-short>-<spec-id>` where `<session-short>` is the first 8 characters of THAT foreign session entry's UUID and `<spec-id>` is the active SPEC identifier. The naming is deterministic so the auto-created worktree is greppable and traceable to the originating foreign session. No "or equivalent" clause — the scheme is fixed.

**Landing paths** — each auto-created worktree SHALL land under `.claude/worktrees/auto-<session-short>-<spec-id>/` (L1 Claude-native) OR `~/.moai/worktrees/<project>/auto-<session-short>-<spec-id>/` (L2 persistent), so the two sessions do NOT share a branch-state mutable surface. The primary-checkout branch guard exempts worktree paths from its deny, so the auto-isolation procedure does NOT trip the branch guard.

**Surface** — the orchestrator surfaces the auto-isolation as an info log (NOT an `AskUserQuestion` round — the procedure auto-resolves the race, it does not ask the user to resolve it). The info log notes the registry entry's age so a stale-registry false positive is visible.

**Multiple foreign sessions (≥2)** — the procedure auto-creates N worktrees, one per foreign registry entry (Edge-3: each session gets its own isolated branch-state surface).

## Reference tables and role recipes

> Moved to the detail companion — the `ORC_WORKTREE_*` sentinel keys emitted by `moai agent lint` / `moai workflow lint`, the per-mechanism selection lists, the hybrid plan/run/sync integration pattern, and the per-role frontmatter recipes: `worktree-integration-detail.md` § Sentinel Key Glossary, § When to Use Which, § Integration Pattern (Hybrid Approach), § Agent Configuration by Role.

## WorktreeCreate and WorktreeRemove Hooks (Not Registered by Default)

Claude Code v2.1.49+ defines `WorktreeCreate` / `WorktreeRemove` hooks that **replace** Claude Code's default git worktree behavior — not extend it. Per the official contract (https://code.claude.com/docs/en/hooks):

| Hook | Role | stdout contract | Failure mode |
|---|---|---|---|
| WorktreeCreate | Active creator — MUST actually create the worktree directory and echo its absolute path to stdout (plain text only, no JSON; HTTP hooks use `{"hookSpecificOutput": {"worktreePath": "..."}}`). | Single line: `/absolute/path/to/worktree` | Empty stdout OR any non-zero exit aborts creation |
| WorktreeRemove | Observer — runs during/after removal for cleanup. | No output required | Failures logged in debug mode only |

The stdin JSON for both events includes `worktree_path` (Claude Code's proposed path), `name`, `cwd`, `session_id`, `transcript_path`, `hook_event_name`.

**MoAI-ADK does NOT register these hooks by default.** Claude Code's default git worktree handling is sufficient for our agent isolation use case — write-heavy work is declared `isolation: worktree` by the retained `manager-develop` agent, by per-spawn `Agent(general-purpose)` specialists with a write-heavy domain whitelist, and by team-mode role profiles (implementer, tester, designer) per the Worktree Selection Rules above. Registering observer-only hooks here would replace the default behavior with non-functional stubs and produce `"WorktreeCreate hook returned a path that is not a directory: {}"` because an empty JSON object cannot be parsed as a path.

If a future use case requires custom worktree creation (e.g., non-git VCS, shared-file symlinks, per-worktree database setup), implement an active creator hook that:

1. Reads stdin JSON (fields: `worktree_path`, `name`, `cwd`, `session_id`).
2. Performs `git worktree add` (or equivalent for the VCS), redirecting its stdout to `/dev/null` so it does not pollute the hook stdout.
3. Prints **only** the absolute worktree path to stdout. All progress/diagnostic output goes to stderr.
4. Exits 0 on success; any non-zero exit aborts creation.

Handler files at `internal/hook/worktree_{create,remove}.go` and `internal/cli/hook.go` `worktree-create` / `worktree-remove` subcommands are preserved as opt-in infrastructure for future active-creator implementations. They are not registered in `.claude/settings.json` until such an implementation lands. Likewise, `.claude/hooks/moai/handle-worktree-{create,remove}.sh` wrapper scripts exist but are not invoked by any settings.json entry.

## Prompt Path Rules for Worktree-Isolated Agents

When the orchestrator generates prompts for agents spawned with `isolation: "worktree"`, paths in the prompt determine where the agent operates. Incorrect paths bypass worktree isolation entirely.

### HARD Rules

- [ZONE:Frozen] [HARD] Do NOT include absolute paths to the main project directory in agent prompts for write-target files
- [ZONE:Frozen] [HARD] Do NOT include `cd /absolute/project/path &&` in Bash commands within agent prompts
- [ZONE:Frozen] [HARD] Reference write-target files by project-root-relative paths (e.g., `src/domains/auth/handler.go`) and let the agent resolve from its own CWD
- [ZONE:Frozen] [HARD] `$CLAUDE_PROJECT_DIR` in hook commands is acceptable — Claude Code resolves this to the correct directory for the agent's context

> **Path-rule detail** — the per-category absolute-path table, how worktree CWD resolution works, and the correct / incorrect prompt-path examples: `worktree-integration-detail.md` § Path Categories, § How It Works, § Anti-Pattern Examples.

## Teammate Session Launch (`--spawn`)

`moai cc -w <name> --spawn` (likewise `moai glm` / `moai cg`) opens a session in the named worktree in a NEW tmux window and returns, so the caller keeps its own session. Without `--spawn` the same command enters the worktree in place by replacing the current process. See `.claude/skills/moai-workflow-worktree/SKILL.md` § `--spawn` for requirements, error messages, and example invocations.

> **Two distinct `teammateMode` fields — do not conflate.** MoAI's own `.claude/settings.local.json` launcher-selection field (values `"tmux"` / `"glm"` / `"claude"`) is set by `moai cg` / `moai glm` / `moai cc` and selects which launcher a session runs. This is SEPARATE from the Claude Code runtime `teammateMode` setting, whose default changed from `auto` to `in-process` as of Claude Code v2.1.179 — with the in-process default, split panes no longer auto-open. Additionally, as of Claude Code v2.1.181, an idle teammate's agent-panel row hides after 30 seconds and reappears on the next turn. These two CC-runtime behaviors govern how teammates are displayed. Both fields happen to share the name `teammateMode`.

### HARD Rules

[ZONE:Frozen] [HARD] CLI launch decisions MUST NOT invoke `AskUserQuestion`. Every launch outcome is decided from observable state (tmux session presence, `teammateMode`, GLM env vars) and reported through exit codes and stderr. This satisfies the Branch Origin Decision Protocol (see `.claude/rules/moai/development/branch-origin-protocol.md` § HARD Rules).

Static guard: `internal/cli/worktree/new_test.go` `TestNew_NoAskUserQuestion` scans the worktree-creation source for `AskUserQuestion` / `mcp__askuser` references.

[ZONE:Evolvable] [HARD] `--spawn` refuses rather than degrades. Outside tmux, or without the `tmux` / `moai` binaries, it returns a non-zero exit instead of falling back to an in-place launch — a silent fallback would replace the caller's session, the outcome the flag exists to avoid. Refusal happens before any settings mutation.

### Retired: `moai worktree new --team` and the swarm registry

The `--team` flag and its four launch patterns are retired. Entering a worktree is `-w`; spawning a teammate window is `--spawn`. The write-only `.moai/state/swarm/<SPEC-ID>.json` registry was retired with it — no code ever read it, and the `moai swarm status / done / kill-all` commands it was a baseline for were never built.

### Cross-references

- `.claude/skills/moai-workflow-worktree/SKILL.md` § `--spawn` (requirements + examples)
- `internal/cli/spawn.go`, `internal/cli/spawn_test.go`
- Branch Origin Decision Protocol (BODP)

> **Minimum version table** — per-feature Claude Code version floors and the recommended baseline: `worktree-integration-detail.md` § Minimum Version Requirements.

## The per-worktree Python environment

A worktree is a full checkout, so an editable install inside one worktree's virtual
environment pins that worktree's sources: the `.pth` written by the install names the
tree it was created in, and it keeps naming it no matter where the interpreter is later
invoked from. Borrowing a sibling worktree's interpreter therefore does not merely use
another tree's dependencies — it can import another tree's code, with no warning.

Whether it actually does depends on what sits at the front of `sys.path`, which is set
by the invocation shape rather than by the interpreter:

| Invocation | What wins | Borrowing is |
|---|---|---|
| `python -c …` / `python -m …` from the tree root | the current directory shadows the `.pth` | harmless |
| `python <dir>/<script>.py` where that dir holds no package | the `.pth` | **silent cross-tree import** |
| `python -c …` from a subdirectory of the tree | the `.pth` | **silent cross-tree import** |
| `pytest` on tests that live inside the package | the test's base directory | harmless |
| `uv run …` | the project environment resolved from the current directory | harmless — a mismatched `VIRTUAL_ENV` is reported and ignored |

[HARD] **The interpreter is part of the evidence.** Where a result is produced by running
a script by path — a measurement tool, a one-off probe, anything outside the test runner —
the record names the interpreter that produced it, and that interpreter is the tree's own.
A result whose interpreter is unnamed cannot be attributed to a tree, and an unattributable
measurement is not evidence (`verification-claim-integrity.md` §2).

The check is one command, and it is cheap enough to run rather than reason about:

```bash
<interpreter> -c "import <package>; print(<package>.__file__)"
```

Run it from a subdirectory, not the tree root — at the root the current directory shadows
the `.pth` and the check passes even when the interpreter belongs to another tree.

**Measured example — an observation, not a claim about your checkout.**
`jjjh7401/AI-Lighting_Console`, 2026-08-25, worktrees `t47` and `t56`: from `t47/server`,
the tree's own interpreter resolved `server` to `t47`, and `t56`'s interpreter resolved it
to `t56` — same directory, same command, only the interpreter differed, and neither printed
a warning. The same pair run through `pytest` both resolved to `t47`. At that moment the
board held 35 worktrees and 28 virtual environments. Re-measure rather than carrying these
numbers forward.

## The write boundary is the session's launch directory

A session launched from one checkout and then moved into a worktree of another checkout
can find its file-writing tools refusing paths that plainly exist and are plainly inside
the worktree. The refusal is about which project the tools resolve, not about the path.

Three things separate this from a broken path, and all three are measurable in one turn:
a read of the same file succeeds, a shell write to the same path succeeds, and only the
dedicated write tool refuses. Where that pattern holds, the work proceeds through shell
writes; entering the worktree again does not change it, because the launch directory is
fixed for the life of the session.

[HARD] A dispatch that assigns work in a worktree does not assume the receiving session can
write there. Where the assigned session was launched from a different checkout, say so in
the dispatch, or launch the session from the checkout that owns the worktree.

**Measured example.** Same repository and date as above: in worktree `t47`, `Read` on a
file in the tree succeeded, a heredoc write to the tree succeeded, and `Write` to a new
file in the same tree was refused as a path traversal. The session had been launched from
a sibling checkout.

> **Troubleshooting table** — symptom / cause / solution rows: `worktree-integration-detail.md` § Troubleshooting.

## SPEC-to-Worktree Mapping

[ZONE:Frozen] [HARD] Per-step worktree applicability is governed by `.claude/rules/moai/workflow/spec-workflow.md` § SPEC Phase Discipline (canonical source). This table summarizes the mapping for quick reference; on conflict, spec-workflow.md wins.

| Step | Phase   | Worktree?                | Location                              | Lifecycle event              |
|------|---------|--------------------------|---------------------------------------|------------------------------|
| 1    | Plan    | **NO** (main checkout)   | n/a — `plan/SPEC-XXX` branch on main  | plan PR merged               |
| 2    | Run     | **opt-in (`moai cc -w <name>`)** | the entered worktree                  | run PR merged                |
| 3    | Sync    | **opt-in** — same as Step 2            | same path as Step 2 (do NOT recreate) | sync PR merged               |
| 4    | Cleanup | n/a                      | host checkout                         | `moai worktree done SPEC-XXX` |

Worktree usage is user opt-in; the default flow runs all phases on a `feat/SPEC-XXX` branch in the main checkout. To use one, enter it with `moai cc -w <name>` before invoking the phase.

[ZONE:Frozen] [HARD] Disposal contract: `moai worktree done SPEC-XXX` MUST run only after BOTH run PR AND sync PR are merged. Premature disposal between Step 2 merge and Step 3 merge breaks Sync.

---

Version: 4.4.0 (descriptive card-branch slugs — card id leaves the branch name, stays on the tree path; WT- naming + disposal-path reconciliation; release self-integration pointer)
