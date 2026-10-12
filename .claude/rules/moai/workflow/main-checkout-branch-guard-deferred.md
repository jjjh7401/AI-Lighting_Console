---
description: "Deferred detail moved verbatim out of main-checkout-branch-guard.md (t613 rules diet); the SSOT file keeps pointers and the [HARD] one-liners"
paths: "**/main-checkout-branch-guard.md"
---

# main-checkout-branch-guard — deferred detail (t613)

> 원문 그대로 옮긴 상세. 출처: `.claude/rules/moai/workflow/main-checkout-branch-guard.md`. 조항의 효력은 그대로다 (삭제 아님, 적재 위치만 바뀜).

## Mechanical Enforcement (v1.2.0)

The doctrine above is mechanically enforced by a PreToolUse hook. The
enforcer is NOT a static `settings.json` deny entry — a static deny cannot
scope to the primary checkout only and would lock out legitimate worktree
flows. The hook applies the doctrine conditionally.

- **Handler**: `internal/hook/pre_tool.go` `preToolHandler.Handle` calls
  `checkBranchState` (in `internal/hook/branch_guard.go`) after the existing
  dangerous-pattern check and before the default-allow fall-through.
- **Opt-in gate (v1.2.0)**: the call to `checkBranchState` is gated at the
  call site by the `Workflow.BranchGuard.Enabled` config flag (read via the
  handler's ConfigProvider). The default is **false** — the guard ships INERT
  to all users, because the shared-checkout hazard it addresses does not apply
  to single-developer repos. Maintainers of shared multi-session checkouts opt
  in via local config. When disabled, NO `git rev-parse` subprocess runs (the
  primary-checkout discriminant cost is avoided entirely) and the guard
  returns the allow fall-through without evaluating patterns, checkout state,
  or exemption logic. The exemption logic (`MOAI_BRANCH_GUARD_EXEMPT` +
  `manager-git` identity) is unchanged and is consulted only on the enabled
  path.
- **Pattern refinement (v1.2.0)**: the regex set no longer matches the
  read-only forms `git stash list`, `git stash show`, and `git merge-base`.
  `git merge` anchors on trailing whitespace so `merge-base` is excluded;
  `git stash` requires either bare end-of-input or one of the mutating
  subcommands (push/pop/apply/drop). The genuinely dangerous forms
  (switch/checkout/branch/reset --hard/rebase/bare+mutating stash/actual
  merge) remain matched.
- **Deny reason sentinel**: every deny emitted by this path carries the
  prefix `BRANCH_GUARD_VIOLATION:` so the orchestrator can pattern-match the
  source without parsing the full reason string.
- **Discriminant (primary vs worktree)**: the hook compares the absolute
  `git rev-parse --git-dir` against the absolute `git rev-parse
  --git-common-dir` **at the command's actual cwd**; equal paths classify as
  the primary checkout, differing paths as a worktree. The cwd is resolved
  from `input.CWD` (via `resolveProjectRootFromInputOrEnv`: `input.CWD`, then
  `$CLAUDE_PROJECT_DIR`, then `os.Getwd()`), NOT from `$CLAUDE_PROJECT_DIR`
  alone — querying the primary checkout about itself always answered
  "primary", which misclassified a worktree-resident agent's branch-state
  command as a primary-checkout violation (discriminant directory correction,
  v1.2.0). The audit-log project directory stays pinned to
  `$CLAUDE_PROJECT_DIR` → `os.Getwd()` for central logging, independent of
  which directory the git-context discriminant queries. Primary path uses
  `--path-format=absolute` (git 2.31+, March 2021); older git or Apple Git
  that rejects the flag falls back to `git rev-parse --absolute-git-dir` +
  cwd-normalized `--git-common-dir`.
- **Exemption mechanism**: the deny is suppressed when EITHER the invoking
  agent identity is the trusted git agent (`HookInput.AgentType ==
  "manager-git"`) OR the sentinel environment variable
  `MOAI_BRANCH_GUARD_EXEMPT=1` is present. Both axes are implemented and each
  fires on its own — but each is read from a different place, and **neither is
  reachable from inside a tool-spawned subagent**:
  - `AgentType` arrives in the hook payload, and Claude Code populates
    `agent_type` for a main-thread `claude --agent manager-git` launch. A
    subagent spawned through the Agent tool sends no `agent_type` on
    PreToolUse, so the identity axis cannot fire for it.
  - The sentinel is read from the hook process's own environment. The hook
    runs as a separate process spawned **before** the guarded command executes,
    so an `export MOAI_BRANCH_GUARD_EXEMPT=1` inside that command never reaches
    it. The variable must be present in the environment Claude Code itself was
    launched with.

  Exporting the sentinel inside the command being guarded is therefore a no-op.
  A `manager-git` subagent that needs to mutate branch state has two working
  routes: do the work in a worktree (`git -C <worktree>`, which the discriminant
  correctly classifies as non-primary), or have the operator launch the session
  with the sentinel already in its environment. Reading a `BRANCH_GUARD_VIOLATION`
  as "the exemption is broken" is a misdiagnosis — the axes work; the values were
  never delivered.

  The deny reason's remediation text aligns with this reachability caveat
  (v1.3.1): it directs the caller to a worktree and states that the manager-git
  identity and sentinel exemptions fire only for main-thread launches — it must
  not suggest delegating to a `manager-git` subagent, which receives the same
  deny again.

- **Scan scope**: the pattern set is matched against the command with quoted
  spans collapsed to a placeholder word, so a match reflects the command being
  invoked rather than text carried as data. `moai todo add "… git switch …"` is
  allowed because the command being run is `moai todo add`; `git switch main`
  and `git checkout -b "feat/x"` both still deny, the latter because the
  placeholder preserves the operand after `-b`. A git invocation hidden inside a
  shell wrapper (`bash -c "git switch main"`) is not matched — under-matching an
  obfuscated form is the correct direction to err for a fail-open guard.
- **Fail-open norm**: the deny fires ONLY on positive evidence (primary
  checkout confirmed AND a branch-state pattern matched AND the agent is not
  exempt). Any uncertainty — not a git repo, missing git binary, `git
  rev-parse` exiting non-zero, or indeterminate agent identity — falls
  through to allow, writes an advisory to stderr, and appends a structured
  entry to `.moai/logs/branch-guard-audit.log`. Aligns with the Bash
  Risk-Amplifier Doctrine (WARN-ONLY, FAIL-OPEN). This norm is unchanged by
  the opt-in gate: when disabled the guard returns allow BEFORE reaching any
  uncertainty path, so fail-open is trivially preserved.

Origin: the run-phase SPEC that landed the v1.1.0 mechanical enforcer. The
v1.2.0 opt-in gate and pattern refinement landed in a follow-up behavior-tuning
SPEC; the v1.2.0 discriminant directory correction (query the command cwd, not
$CLAUDE_PROJECT_DIR) landed in a second follow-up SPEC.


