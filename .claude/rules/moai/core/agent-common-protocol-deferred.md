---
description: "Deferred detail moved verbatim out of agent-common-protocol.md (t613 rules diet); the SSOT file keeps pointers and the [HARD] one-liners"
paths: "**/agent-common-protocol.md"
---

# agent-common-protocol — deferred detail (t613)

> 원문 그대로 옮긴 상세. 출처: `.claude/rules/moai/core/agent-common-protocol.md`. 조항의 효력은 그대로다 (삭제 아님, 적재 위치만 바뀜).

### Hook Invocation Surface

The orchestrator interacts with three hook scripts that mechanically enforce orchestrator-discipline obligations (exit-code semantics: stdout JSON is honored only on exit 0 — on exit 2 it is discarded and only stderr is surfaced):

| Hook script | Trigger | Exit-code semantics |
|-------------|---------|---------------------|
| `.claude/hooks/moai/status-transition-ownership.sh` | PostToolUse on Write/Edit of `.moai/specs/SPEC-*/{spec,plan,acceptance}.md` body | exit 0 always (advisory; audit-logged to `.moai/logs/status-transition-audit.log`; exit-2 blocking reserved for future enforcement) |
| `.claude/hooks/moai/sync-phase-quality-gate.sh` | Stop hook on sync-phase commit completion | exit 0 always; failing check emits advisory `systemMessage`; blocking mode (opt-in `MOAI_SYNC_GATE_BLOCKING=1`) emits stdout JSON `{"decision":"block"}` |
| `.claude/hooks/moai/team-ac-verify.sh` | TaskCompleted in team mode (dormant — harness `thorough` + team prerequisites) | exit 0 always; rejection via stdout JSON `{"continue":false,"stopReason":...,"ledger_note":...}` (`decision` NOT valid for TaskCompleted) |

Full per-row owning-policy detail and the hook subagent-boundary acceptance criterion (grep verifying no hook invokes AskUserQuestion): `agent-common-protocol-reference.md` § Hook Invocation Surface detail.

#### Orchestrator translation responsibility

Hooks return exit codes and structured JSON; they MUST NOT invoke `AskUserQuestion` directly. When a hook signals a block (stdout JSON `"decision":"block"` on exit 0, or a legacy exit-2), the orchestrator MUST:

1. Parse the hook's structured JSON output (`decision`, `reason`, plus optional `ledger_note` / `systemMessage` / `details`)
2. Preload `AskUserQuestion` via `ToolSearch(query: "select:AskUserQuestion")`
3. Compose an `AskUserQuestion` round presenting the user with at least: (a) accept the block and address the failed gate, (b) override with `--skip-hook` opt-out (logged to `.moai/logs/hook-skip.log`), (c) abort the workflow

#### Stop self-gate caveat

The Stop hook fires on every turn-end, not only on task completion, so it must self-gate (inspect state, decide whether the turn is a genuine completion point, otherwise exit 0). It does NOT fire on user interrupt — it is not a guaranteed end-of-work signal.

#### Recovery-Signal Carve-Out

[ZONE:Evolvable] **While** a turn's `stopReason` or surrounding context indicates the turn is itself a **recovery signal** (recovering from a sync failure, a compact, a `prompt_too_long` (PTL), a `max_output_tokens` exhaustion, or a `media_size` / `compact-failure`), Stop/PostToolUse hooks SHOULD exit 0 rather than exit 2, so recovery turns are NOT placed into the `error → stop-hook-blocks → retry → error` **death-spiral** loop. SHOULD (policy guidance), not a mechanical gate. SSOT: `runtime-recovery-doctrine.md` §4.


### Per-Spawn Model Injection

[ZONE:Evolvable] [HARD] When spawning a subagent, pass the model the active profile resolves for that agent as an explicit `model` argument on the spawn. (Why omitting is not neutral, and the full profile matrix: `agent-common-protocol-reference.md` § Per-Spawn Model Injection rationale; policy SSOT `.claude/rules/moai/development/model-policy.md`.)

- Resolve the value with `moai model profile --json` (reports the `{model, effort}` cell per retained agent under the active profile)
- Pass `model` per spawn. `effort` has no spawn-time parameter — it travels only through the agent file's frontmatter
- A spawn whose declared model differs from the resolved one is drift, not an override — change the profile instead
- Agents outside the retained catalog resolve to the inherit sentinel and take no injection

A PreToolUse hook observes every spawn and records the outcome to `.moai/logs/agent-model-audit.jsonl` (advisory; blocking is opt-in via `workflow.agent_model_guard.enabled`, refusing only a declared-vs-resolved conflict).


### Super-Advisor Escalation (E1-E4)

When recovery via the 3-retry ceiling is insufficient OR a higher-reasoning consultation is warranted, the orchestrator escalates to the **super-advisor** agent. super-advisor returns **non-binding prescriptions**; the orchestrator remains the decision owner. DISTINCT from auditor verdicts — `plan-auditor` / `sync-auditor` own binding PASS/FAIL judgment; "should this PASS?" → an auditor, "what should I do here?" → super-advisor.

Entry conditions (exhaustive):

| Trigger | Condition | Example |
|---------|-----------|---------|
| **E1 — bug-deadlock** | 3+ consecutive same-diagnostic failures | same failing test retried 3 times with the same root-cause hypothesis |
| **E2 — architecture/design decision point** | A spec-body or plan-body decision with ≥2 viable options, neither obviously correct | "write-through or write-behind?" at L-plan boundary |
| **E3 — second-opinion request** | Orchestrator uncertainty: < 80% confidence in the next delegation step | ambiguous blocker-report; re-spawn vs user-escalation |
| **E4 — loop-deadlock** | `/moai loop` or `/moai fix` ceiling-exit per the loop-verdict contract | auto-fix iterations exhausted without green CI |

On trigger: spawn `Agent(general-purpose)` with the super-advisor role profile (Opus + xhigh at max/medium tier; Sonnet + xhigh at low tier — GLM-backed sessions fall back to the session model), receive the prescription, then re-seed the executor or escalate to the user via `AskUserQuestion`. Agent file: `.claude/agents/moai/super-advisor.md`.


### Verbatim batch, output contracts, and CLI idioms

The canonical 7-command batch, the file-redirect contract, the evidence-persistence obligation, the serial-verification anti-pattern, and the CLI idiom catalogue (`gh pr checks --json … | jq`, `--watch --fail-fast` in background mode, `git log --format=…`, the per-turn `ToolSearch` preload) all live in `agent-common-protocol-reference.md`. Read it when composing a batch.

Three obligations from that file bind here and are restated so they hold without it:

- **Batch in one turn.** Independent read-only verifications are issued as separate Bash tool calls within a single assistant turn — never serialized across turns. Serialize only for genuine dependencies: one command's output feeding another, writes to the same path, or shared-state mutation.
- **File-redirect contract.** When a command's verbatim output exceeds the bounded-tail ceiling (default: 50 lines or 2KB, whichever is smaller), redirect it to a file and surface only the exit code plus a bounded tail. Below the ceiling, inline quotation is fine. The contract removes the double-burn of quoting output twice, never the evidence itself.
- **Evidence persistence.** The cited path must still resolve at audit time, so evidence is persisted under `.moai/state/verify/<session>/` rather than left in `/tmp`, which the OS clears. A claim whose cited evidence path no longer resolves is an unattributed claim (`verification-claim-integrity.md` §2).


### Attributable diff-check doctrinal switch

Default-inversion switch in how the orchestrator COMPOSES the canonical batch: consult the shared diagnostic snapshot via `moai verify check --key-current` (keyed by HEAD SHA) BEFORE re-executing; on all-three attribution match, consume the attributable §E evidence for that dimension INSTEAD of re-executing the corresponding command. This is a composition-time doctrinal switch binding the orchestrator's batch-composition discipline, not a runtime hook. (Full mechanism + fallback contract: `agent-common-protocol-reference.md` § Attributable diff-check detail; pattern file `.claude/rules/moai/workflow/verification-batch-pattern.md`.)

**All-three attribution match → CONSUMES the attributable §E evidence (no re-execution) [DEFAULT].** When ALL THREE hold for a verification dimension:
1. **Snapshot key match** — the §E-cited HEAD SHA equals the current `moai verify check --key-current` key
2. **Command match** — the §E-cited command matches the snapshot's recorded command
3. **Output match** — the §E-cited observed output matches the snapshot's recorded output

the batch records the snapshot key + cited §E evidence path as its baseline-attribution per VCI §2 and DOES NOT re-execute that dimension (marked PASS-attributed, not PASS-reexecuted).

**Any mismatch → fallback to re-execution.** On ANY of `snapshot_key_drift` (HEAD SHA changed) / `command_drift` / `missing_section_e` (§E evidence missing or citing no observable output) / `output_drift`, the batch SHALL re-execute the affected dimension — any-mismatch → re-execute, never silent skip. The fallback is logged with the mismatch reason; the VCI §1.1 invariant holds on every path.


