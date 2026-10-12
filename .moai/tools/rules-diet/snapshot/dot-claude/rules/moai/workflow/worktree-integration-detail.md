---
paths: "**/worktree-integration.md,**/worktree-integration-detail.md"
---

# Worktree Integration — Detail Companion

Detail companion for `worktree-integration.md`. The stub owns every `[HARD]` /
`[ZONE:Frozen]` clause and every externally cross-referenced section (§ Terminology
Glossary, § `EnterWorktree` / `ExitWorktree` Tools, § Worktree Selection Rules,
§ Parallel-Session Branch Conflict Auto-Isolation, § WorktreeCreate and WorktreeRemove
Hooks, § Prompt Path Rules for Worktree-Isolated Agents, § Teammate Session Launch,
§ The per-worktree Python environment, § The write boundary is the session's launch
directory, § SPEC-to-Worktree Mapping). This file holds the reference tables, the
invocation and settings detail, the per-role recipes, and the worked examples.

Content here is moved verbatim from the stub; nothing was rewritten or dropped. Read
this file when configuring a worktree, choosing between the mechanisms, or writing a
prompt for a worktree-isolated agent.

## Comparison Table

| Feature | Claude Native | MoAI |
|---------|--------------|------|
| **Path** | `.claude/worktrees/<name>/` | `~/.moai/worktrees/{Project}/{SPEC}/` |
| **Lifetime** | Ephemeral (session-scoped) | Persistent |
| **Purpose** | Session isolation for subagents | SPEC development, PR creation |
| **CLI** | `claude -w` (user) or `isolation: worktree` (agent) | `moai cc -w <name>` to enter; `moai worktree clean/done/remove` to dispose |
| **Cleanup** | Automatic on session end | Manual via `moai worktree remove` |
| **Branch Strategy** | Temporary branches | Feature branches linked to SPEC |
| **Team Use** | Single agent isolation | Multi-developer collaboration |
| **State Persistence** | None | SPEC state, progress tracking |
| **Hook Support** | WorktreeCreate/WorktreeRemove hooks | WorktreeCreate/WorktreeRemove hooks |


### `claude --worktree` (`-w`) Flag

For users starting isolated sessions:

```bash
# Start new isolated session in worktree
claude --worktree

# With custom name
claude --worktree my-feature

# With tmux for split-pane display (tmux or iTerm2 required)
claude --worktree --tmux
```

Behavior:
- Creates `.claude/worktrees/<name>/` automatically
- Branches from default remote branch
- On session end: prompts to keep (with commits) or auto-deletes (no changes)

tmux flag notes:
- Requires tmux or iTerm2
- NOT supported in VS Code integrated terminal, Windows Terminal, or Ghostty
- Useful for parallel team mode where viewing multiple teammates' output is beneficial


### `background: true` in Agent Frontmatter

Run agent without blocking the main conversation (v2.1.46+):

```yaml
---
name: team-coder
background: true   # Returns immediately; results delivered on next turn
---
```

Use with `isolation: worktree` for optimal parallel execution in team mode.

Background-execution policy for write-capable agents is owned by `.claude/rules/moai/core/agent-common-protocol.md` § Background Agent Execution. As of Claude Code v2.1.198 subagents run in the background by default, and a background write surfaces a permission prompt in the main session naming the asking subagent; MoAI aligns with that runtime default rather than forcing foreground. The retained safeguard is concurrency, not backgrounding: MoAI does not run two write-capable agents concurrently. Use `background: true` for:
- Read-only research and analysis agents
- Agents whose write paths are pre-approved in settings.json `permissions.allow`

Kill background agent: Press `Ctrl+X Ctrl+K` in Claude Code interface (v2.1.83+).

### Worktree Base Branch (`worktree.baseRef`)

Native worktrees (`--worktree` and subagent `isolation: worktree`) branch from the repository's default branch (`origin/HEAD`) by default, so they start from a clean tree matching the remote. If no remote is configured or the fetch fails, the worktree falls back to the current local `HEAD`. To always branch from local `HEAD` instead (carrying unpushed commits and feature-branch state), set `worktree.baseRef` to `"head"` in settings (accepts only `"fresh"` or `"head"`, not arbitrary refs):

```json
{
  "worktree": {
    "baseRef": "head"
  }
}
```

Use `"head"` when isolating subagents that must operate on in-progress work. To branch a native worktree from a specific pull request, pass the PR number prefixed with `#` (e.g. `claude --worktree "#1234"`); Claude Code fetches `pull/<number>/head` and creates the worktree at `.claude/worktrees/pr-<number>`.

This setting governs **Claude-native** worktrees only, which is now every worktree the launcher creates — `moai cc -w <name>` passes `-w` straight through to `claude`.

**Creating a card worktree on a release branch.** Because the default is `origin/HEAD`, a worktree created while a release branch is the intended base starts behind it — measured on one such branch, 34 commits behind, with the reflog reading `branch: Created from origin/main`. Two ways out, and the difference between them is not convenience:

- **Set the base after creation**, while the new tree still has no commits of its own: `git -C <tree> reset --hard <ref>`, then `git -C <tree> merge-base --is-ancestor <ref> HEAD` and read the exit code. Only for a tree that is empty and clean; once it carries a commit, this discards it.
- **Set `baseRef` to `"head"`**, which makes creation inherit rather than default.

`"head"` carries a trap worth stating plainly, because the name invites the wrong reading: it is **the HEAD of the tree the launcher ran in**, not the branch you had in mind. Run `moai cc -w <name>` from the primary checkout while intending a release branch and the new worktree inherits whatever the primary happens to be sitting on — wrong in a quieter direction than the default was, because the reflog now names a plausible commit instead of an obviously-unrelated one. Using it correctly therefore adds a procedural requirement of its own: the launcher must be run from inside a tree already on the intended base.

That asymmetry is the reason to prefer the reset path for card work. `baseRef` is silent whether it lands right or wrong; the reset path ends in an exit code somebody read.


### `.worktreeinclude` (Copy Gitignored Files into Native Worktrees)

A native worktree is a fresh checkout, so untracked files (`.env`, `.env.local`, local config) are not present. Add a `.worktreeinclude` file at the project root to copy them automatically when Claude creates a worktree. It uses `.gitignore` syntax; only files that match a pattern AND are gitignored are copied (tracked files are never duplicated):

```text
.env
.env.local
.moai/config/sections/*.local.yaml
```

Applies to `claude --worktree`, subagent `isolation: worktree` worktrees, and desktop parallel sessions. NOT processed when a custom `WorktreeCreate` hook replaces the default git behavior — copy local files inside the hook script instead.


## Sentinel Key Glossary

Structured error codes emitted by `moai agent lint` and `moai workflow lint` for programmatic detection:

| Sentinel Key | Source | Meaning |
|---|---|---|
| `ORC_WORKTREE_MISSING` | LR-05 (agent lint) | Write-heavy agent lacks `isolation: worktree` in frontmatter |
| `ORC_WORKTREE_ON_READONLY` | LR-09 (agent lint) | Read-only agent (`permissionMode: plan`) has `isolation: worktree` — prohibited overhead |
| `ORC_WORKTREE_REQUIRED` | `moai workflow lint` | Legacy sentinel from the retired Agent Teams `role_profiles` isolation check — inert since the `team:` config block was removed from workflow.yaml |

### When to Use Which

### Use `claude --worktree` (`-w`) for:

- **User-initiated isolation**: Starting a fresh session for exploratory work
- **Parallel sessions**: Running multiple independent Claude sessions on same repo
- **Quick experiments**: Testing code changes without affecting main workspace

### Use `Agent(isolation: "worktree")` for:

- **Parallel team agents**: Multiple implementation teammates working simultaneously
- **File conflict prevention**: Agents that write to different file patterns
- **One-shot sub-agents**: Sub-agents making cross-file modifications
- **GitHub issue fixing**: Each issue gets isolated worktree for branch safety

### Use MoAI Worktree (`moai worktree`) for:

- **SPEC implementation**: Multi-session development of a feature
- **PR development**: Complete feature branches with commits
- **Persistent workspaces**: Work that spans multiple Claude sessions

## Integration Pattern (Hybrid Approach)

The recommended workflow combines both worktree systems:

```
PLAN PHASE
  Claude Native (-w): Quick exploration, ephemeral, no persistence
  Team researchers: No worktree (read-only, permissionMode: plan)

RUN PHASE
  MoAI Worktree: SPEC implementation, persistent state
  Team write agents: Agent(isolation: "worktree") for parallel execution
  Team read agents: No worktree (quality validation, analysis)

SYNC PHASE
  MoAI Worktree: PR creation from persistent workspace
```

## Agent Configuration by Role

### Implementation Agents (isolation: worktree + background: true)

```yaml
# Implementation teammates (write-capable implementation roles: implementer / tester / designer)
# Spawned via: Agent(subagent_type: "general-purpose", mode: "acceptEdits", isolation: "worktree")
isolation: worktree   # Isolated worktree per agent
background: true      # Non-blocking parallel execution
permissionMode: acceptEdits
```

### Research/Analysis Agents (no isolation needed)

```yaml
# Read-only teammates (read-only research/review roles: researcher / analyst / reviewer)
# Spawned via: Agent(subagent_type: "general-purpose") with a read-only tools list
# No isolation: worktree (read-only via tool restriction — the spawn-time mode
# parameter is deprecated/ignored since v2.1.213; a parent bypassPermissions/
# acceptEdits mode takes precedence over child permission settings)
permissionMode: plan  # advisory frontmatter; the tool restriction is the guarantee
```


### Path Categories

| Category | Example | Absolute Path OK? | Reason |
|----------|---------|-------------------|--------|
| Write-target files | Source code, tests | NO — use relative | Agent CWD is worktree root; relative paths resolve correctly |
| Read-only references | Skills, configs via `${CLAUDE_SKILL_DIR}` | YES | Content is identical in main repo; read-only access is safe |
| SPEC documents | `.moai/specs/SPEC-XXX/spec.md` | Relative preferred | SPEC files are copied to worktree during checkout |
| Bash commands | `go test ./...` | NO `cd` prefix | Agent CWD is already set to worktree root |

### How It Works

When `isolation: "worktree"` is set, Claude Code:
1. Creates a temporary worktree from the current branch
2. Sets the agent's CWD to the worktree root
3. The agent constructs absolute paths from its own CWD

```
Main repo:  $HOME/project/src/auth/handler.go
Worktree:   $HOME/project/.claude/worktrees/abc123/src/auth/handler.go
```

Both share the same project structure. `src/auth/handler.go` resolves correctly in either context.

### Anti-Pattern Examples

```
# WRONG: Absolute path in prompt bypasses worktree
"Read $HOME/project/src/auth/handler.go and fix the bug"

# WRONG: cd to main project in Bash command
"Run: cd $HOME/project && go test ./..."

# CORRECT: Relative path — agent resolves from its own CWD
"The bug is in src/auth/handler.go. Read the file and fix it."

# CORRECT: No cd prefix — agent CWD is already worktree root
"Run: go test ./..."
```


## Minimum Version Requirements

| Feature | Minimum Version | Notes |
|---------|----------------|-------|
| `isolation: worktree` in Agent frontmatter | 2.1.49 | Basic worktree isolation |
| `background: true` in Agent frontmatter | 2.1.46 | Non-blocking agent execution |
| `claude --worktree` user flag | 2.1.50 | User-initiated worktree sessions |
| `Ctrl+X Ctrl+K` to kill background agent | 2.1.83 | Kill stuck background agents |
| Worktree CWD isolation fix | **2.1.97** | Prior versions leaked agent CWD back to parent session |
| Stop/SubagentStop hook stability | **2.1.97** | Prior versions failed on long-running sessions |
| `moai doctor` MCP scope duplicate detection | **2.1.110** | Warns on MCP server duplication across `.mcp.json` + settings.json |
| Bash tool timeout ceiling enforcement | **2.1.110** | Maximum 600,000ms (10 min) enforced by runtime |
| `effortLevel` setting for Opus 4.7 | **2.1.110** | Supports `low`/`medium`/`high`/`xhigh`/`max` effort levels |
| `CLAUDE_ENV_FILE` on Windows | **2.1.111** | Prior versions: no-op on Windows; fixed to inject env as on macOS/Linux |
| `disableBypassPermissionsMode` policy | **2.1.111** | Prevents agents from requesting `bypassPermissions` when `true` |

**Recommended**: Claude Code **2.1.186 or later** for current background-agent permission-prompt semantics, Opus 4.7+ / 4.8 / Opus 5 support, MCP doctor warnings, and Windows CLAUDE_ENV_FILE parity. Minimum baseline: **2.1.97** for worktree isolation.


## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Worktree not found | Removed manually | Run `git worktree list` to verify |
| Agent worktree conflicts | Multiple agents same file | Check file ownership in team config |
| Stale worktree branches | Incomplete cleanup | Run `git worktree prune` |
| Hooks not firing | Missing wrapper script | Check `.claude/hooks/moai/` directory |
| `--tmux` not working | Unsupported terminal | Use tmux or iTerm2 (not VS Code, Ghostty) |
