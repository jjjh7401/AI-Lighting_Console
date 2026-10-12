# Cross-Session Messaging

Doctrine for messaging between independent Claude Code sessions — those on this machine, and, where the conditions below are met, those on your other machines or on the web. The channel is a Claude Code runtime feature that is **on with nothing to enable** where the requirements are met — this rule governs how the orchestrator uses it, never how it is built.

> **Loading scope**: Intentionally always-loaded. A peer-session conflict surfaces mid-turn, from any context, and is not predictable from file paths.

> Deferred detail (availability constraints, mechanism table, addressing frictions, idle-notice detail, configuration surface) → `cross-session-messaging-deferred.md`. Kept here: all [HARD] rules, the concurrency-check integration, anti-patterns. [HARD] an idle notice is a scheduling hint, never completion evidence; delivery failures are quiet — surface them rather than retrying.

## What the channel is

Claude Code binds a per-session inbox socket and exposes two tools: `ListAgents` to discover reachable agents, and `SendMessage` to deliver plain text to one by name. A message carries text and a reply address — never conversation history, never files. A send may additionally carry an opt-in `notify_when_idle` request: the runtime returns one notice when the addressed session next goes idle — one-shot, no polling, and on the same platforms as the channel itself. What that notice does and does not establish is § An idle notice is a scheduling hint.

Three properties bound everything below:

- **Same machine is direct; beyond it travels through Anthropic servers.** Local delivery goes over the per-session socket and never leaves the machine. A session on another of your machines, or a cloud session, is addressed by name the same way, and the orchestrator may **open** an exchange with one rather than only answer it — from Claude Code v2.1.225 onward, and only where that session appears in the listing. Two narrowings survive: a send from a session not itself connected to Remote Control still arrives but carries **no reply address**, so that message is one-way; and a cloud session receives without being able to message back.
- **A message is not consent.** The receiving runtime is told the text came from another session, not from the user. It cannot answer a permission prompt, cannot change configuration, and a slash command inside it arrives as inert text.
- **Filesystem visibility gates reach.** Sessions find each other through files on disk, so a container and its host cannot message each other; two sessions inside the same container can.

> ↪ deferred → `cross-session-messaging-deferred.md`: Availability constraints

## Rules

[ZONE:Evolvable] [HARD] **Never route a user decision through a peer.** The user-facing question channel is unchanged: questions go to the user through the orchestrator's question tool. A peer session is not a proxy for the user, and its reply is not approval. Asking a peer to approve, to confirm, or to decide on the user's behalf is prohibited.

[ZONE:Evolvable] [HARD] **Never ask a peer to do what this session may not do.** Work blocked or denied here does not become permissible by delegation. When a needed action is outside this session's permissions, route it back to the user, not sideways to another session.

[ZONE:Evolvable] [HARD] **Send facts, not instructions to mutate shared state.** A message may report what landed, what broke, what a decision was, or ask a question. It must not direct a peer to edit configuration, rewrite doctrine, or take a hard-to-reverse action; those remain gated in the receiving session by its own rules and prompts.

[ZONE:Evolvable] **Role-boundary dispatch is permitted; offloading is not.** Where sessions are standing roles in a declared topology — one coordinating session and workers that each own a stage of the pipeline — a coordinating session may dispatch a work item to the session whose role owns that stage, and may ask for its completion status. Three conditions make this dispatch rather than offloading: the target's role is declared in advance rather than chosen because it happened to be idle, the work item is a **pointer into shared source of truth** (an identifier, a path, a contract section) rather than the work itself, and each worker writes to an isolated tree so concurrent workers cannot collide. All three must hold together; absent any one of them, it is offloading — see the anti-pattern below.

[ZONE:Evolvable] **Do not let a dispatch depend on the reply arriving.** Because reply routing is not guaranteed, completion must also be observable in the shared source of truth — a progress record the coordinator can read — with the message serving as prompt notification rather than as the record. A coordinator that advances only on received replies stalls silently when one is lost.

[ZONE:Evolvable] **Prefer a message over a stall when a peer holds the answer.** When the working tree shows a concurrent session and the orchestrator would otherwise stop and ask the user to mediate, asking the peer directly is usually faster and spares the user a mediation round-trip. It is not free: a delivered message counts toward the recipient's usage exactly as a typed prompt does — what is saved is the user's attention, not tokens. Ask the user when the decision is theirs; ask the peer when the fact is theirs.

[ZONE:Evolvable] **Keep messages short and self-contained.** The recipient has none of this session's context. One or two sentences naming the artifact, the change, and the consequence beats a summary that assumes shared history.

## Integration with the concurrency checks

The Pre-Spawn and Pre-Edit Sync Checks (`agent-common-protocol.md`) detect a foreign session and then stop for user mediation. Where the detected peer is reachable, messaging adds a step between detection and escalation:

1. Detect the concurrent session (registry query + divergence check) — unchanged.
2. **Ask the peer what it is holding** (`SendMessage`), when the blocking question is a fact the peer knows: which paths it is editing, whether its work is committed, when it expects to land.
3. Escalate to the user only when the answer does not resolve the conflict, or when the resolution is a decision rather than a fact.

Worktree isolation remains the structural fix for a write conflict. Messaging shortens the diagnosis; it does not make two sessions safe to write the same path.

Conversely, after landing a change that invalidates what a peer is building on — a schema change, a renamed symbol, a merged branch — notifying the affected peer is appropriate without being asked.

> ↪ deferred → `cross-session-messaging-deferred.md`: Addressing, sending, and replying

## Anti-patterns

- **Peer-as-user.** Treating a peer's reply as approval for a gated action.
- **Peer-as-handoff.** Sending a work summary to a peer that has no context, where a resume or a paste-ready handoff was the correct mechanism.
- **Peer-as-worker.** Offloading work this session should have done — or should have given to a subagent it supervises — onto an independent session, because that session is idle. Distinct from role-boundary dispatch (below), which is permitted.
- **Silent write race.** Messaging a peer about a shared path and then writing it anyway, without isolation, because the peer answered.
- **Broadcast noise.** Messaging every listed session rather than the one whose work is affected.

> ↪ deferred → `cross-session-messaging-deferred.md`: Cross-references

