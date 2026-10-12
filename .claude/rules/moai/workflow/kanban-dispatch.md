# Kanban Dispatch Protocol

How the **lead** session of Kanban Mode moves a card across the board: what admits work, who is told to do it, how completion is judged, and when the operator is asked to `/clear`.

> **Loading scope**: Intentionally always-loaded. A session learns it is the kanban lead from the SessionStart context, not from a file path, so a `paths:`-restricted rule would never reach it.

> **Detail companion**: `kanban-dispatch-detail.md` owns the long tables, dispatch-cycle walkthrough, incident narratives, and rationale — now also per-card fan-out, Factory in-lane 3-stage, and the `manager-lead` working mode. The stub keeps every [HARD] rule and pointer; load the companion when moving or classifying a card, or choosing review lenses.

> Role clauses moved out (not always-loaded); the detail-companion note above predates this move, so some [HARD] clauses now live in the files named here. **Lead session**: Read `.moai/docs/kanban-lead-protocol.md` before moving a card. **Lane session**: Read `.moai/docs/lane-protocol.md` § 부록 (kanban-dispatch lane clauses). [HARD] one-liners kept: the lead is the queue's sole producer and promotion is always the operator's act; completion is read from evidence on disk, never trusted, and the verdict is the lead's; one card per worktree, entered via the launcher, branch `WT-<slug>` with the card id in the dispatch `card:` field and every commit; a dispatch is a fixed-field block of at most 10 lines in the operator's `conversation_language`; a lane integrates into the release branch itself via `EnterWorktree`; never spawn background load.

## Scope — when this rule is live

This rule binds a session whose SessionStart context declares **Kanban Mode** with the `lead` role. In every other session it is inert: a companion session (`plan` / `run` / `sync`) receives instructions, it does not dispatch them, and a session outside Kanban Mode has no board to move.

Kanban Mode is entered with `moai cc -k` (or `moai glm -k`), which elects one lead and prints one launch command per companion role. Companion sessions are launched **by hand, one per terminal** — a session cannot launch another, and no peer-spawning mechanism exists or is wanted.

The lead session works through the `manager-lead` agent: it holds the operator dialogue (the session's `AskUserQuestion` stays the user channel) while dispatching parallel work in the background — neither blocks the other. Lead and lane sessions orchestrate only; real work runs in sub-agents (design intent + spawn rules: `kanban-dispatch-detail.md` § Design intent, § The lead works through manager-lead).

One boundary: nudge delivery rides on cross-session messaging, absent on native Windows and off under some providers, versions, and flags (`cross-session-messaging.md` § Availability constraints) — an absent channel fails quietly; the lead surfaces it, and the queue keeps working without it.

> ↪ deferred → `.moai/docs/kanban-lead-protocol.md`: The board

> ↪ deferred → `.moai/docs/lane-protocol.md`: Isolation is entered, never provisioned

## Boundaries — what this protocol does not do

- **No board state store.** The queue is a plain file; column position is held by the lead within a card's run and re-derived from SPEC status after a clear. Persistent board state, per-card worktree lifecycle, WIP limits, and card/frontmatter reconciliation are separate work, not assumed here.
- **No session spawning.** The lead addresses sessions the operator launched — it never creates one (sub-agents are not sessions).
- **No gate bypass.** Kickoff approval before run-phase entry, and every other approval gate, is unchanged by being inside a dispatch cycle.
- **No question delegation.** Companion sessions return blocker reports; the operator is asked by the lead, through `AskUserQuestion`.
- **A role with no live session is a fault, not a wait.** The lead reports the empty role and the waiting card; silently holding it presents as a hang, the most expensive failure shape to diagnose. Empty means a complete listing showed none; an incomplete one is a gap, not an empty role (detail companion).

> ↪ deferred → `.moai/docs/kanban-lead-protocol.md`: Cross-references

