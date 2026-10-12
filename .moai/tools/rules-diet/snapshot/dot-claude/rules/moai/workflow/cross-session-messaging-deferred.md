---
description: "Deferred detail moved verbatim out of cross-session-messaging.md (t613 rules diet); the SSOT file keeps pointers and the [HARD] one-liners"
paths: "**/cross-session-messaging.md"
---

# cross-session-messaging — deferred detail (t613)

> 원문 그대로 옮긴 상세. 출처: `.claude/rules/moai/workflow/cross-session-messaging.md`. 조항의 효력은 그대로다 (삭제 아님, 적재 위치만 바뀜).

## Availability constraints

"On with nothing to enable" holds only where the platform provides the channel. Four constraints bound where it exists at all — and because Kanban Mode delegates through the queue on disk, using this channel only to nudge companions, they bound where its nudges reach:

- **Operating system** — macOS and Linux (including Linux inside WSL 2) only. Claude Code does not provide cross-session messaging on native Windows.
- **Providers** — unavailable on Amazon Bedrock, Claude Platform on AWS, Agent Platform on Google Cloud, and Microsoft Foundry.
- **Versions** — v2.1.224+ for the channel itself; v2.1.225+ to open a cross-machine conversation first; v2.1.232+ for @mentions and the /config rows; v2.1.236+ for the `notify_when_idle` request.
- **Flag evaluation** — any one of `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_TELEMETRY`, `DO_NOT_TRACK`, `DISABLE_GROWTHBOOK` disables the feature-flag evaluation the channel depends on, turning messaging off silently. Diagnostic: `/list-agents` (alias `/peers`) recognized → present; unrecognized → absent.

Where a constraint bites, the failure is quiet — nothing errors, dispatch just has no channel. Surface the constraint to the operator instead of retrying or re-spawning.


## Where it sits among MoAI's existing mechanisms

Each mechanism answers a different question. Reaching for the wrong one is the most common error.

| Need | Mechanism | Not this |
|------|-----------|----------|
| Is another session working here right now? | session registry (`moai session list`) — detection | messaging |
| Tell a live peer session something it needs now | **cross-session messaging** | handoff |
| Continue this work after `/clear` or on another machine | paste-ready handoff (`session-handoff.md`) | messaging |
| Coordinate workers this session spawned | subagents / agent teams | peer messaging |
| Move a whole conversation elsewhere | resume the session | messaging |

Messaging complements the registry rather than replacing it: the registry says *that* a peer exists, messaging is *how to talk to it*. Neither carries context — a message that needs the recipient to hold prior state is the wrong tool, and a handoff is the right one.


## Addressing, sending, and replying

A session answers to the name set at launch or by rename; unset, the runtime derives one from the working directory, so parallel sessions in one project collide on a shared prefix and are told apart only by a short reference. Where a launcher starts a session bound to a known unit of work, passing an explicit name makes peers addressable by what they are doing rather than by where they run.

Three frictions are observed in practice and are worth expecting rather than rediscovering:

- **A bare name usually resolves; the short reference is the exception.** The runtime delivers on the name alone when exactly one live session answers to it, and reaches for a short reference only when several sessions share the name or it could not check everywhere your sessions run. So treat a refusal as that exception rather than as the norm: re-send with the reference the error supplies, rather than assuming the peer is unreachable. These appear only in the discovery tool's output, not the user-facing listing. A same-named in-process agent fails differently: with the team namespace on it takes the bare name silently, and a `routing` object on the result is the only sign it went there and was lost. Conditional — read the result rather than always reaching for the reference.
- **A reply address is not guaranteed to route.** A recipient may be unable to answer the sender it was addressed by and fall back to guessing a peer. Consequently a message must carry enough identification for a human or a peer to route the answer manually: name the sending context and what the answer is for. Never assume a reply will land automatically, and never make the sender's identity implicit.
- **The sender's permission class is disclosed.** An arriving message states whether its sender bypasses permission prompts, and that disclosure is what the receiver's inbound default keys on. A message from a bypassing sender is more likely to be held for approval, so a session that expects to be answered promptly should not assume delivery.

An arriving message carries **both** the sender's name and a reply address — not one to the exclusion of the other. Replying to the name as given is the normal path; the address is the fallback where that name does not resolve. What fails is re-deriving either from a listing instead of copying what the message supplied.


## An idle notice is a scheduling hint

A send may ask the addressed session to report back once, when it next goes idle (`notify_when_idle`). It is opt-in per send and one-shot — the request is spent on the first notice, so a second notice needs a second request — and it replaces a polling loop on the asking side.

[ZONE:Evolvable] [HARD] **An idle notice is not completion evidence.** A session goes idle when it finishes, when it stops at a permission prompt, and when it dies, and the notice cannot tell those three apart. What it establishes is *when to go look*; what it says about the work is nothing. Treating it as a completion signal converts the [HARD] read-don't-trust rule (`kanban-dispatch.md` § Completion is read, never trusted) into an unobserved completion claim (`verification-claim-integrity.md` §1.1 surface 1) — the notice arrives, the card advances, and no one read the evidence.

Used for what it is, it removes waste: instead of re-reading a progress file on a guessed interval, ask for the notice and read the evidence once, when there is something to read.


## Configuration surface

| Key | Effect |
|-----|--------|
| `crossSessionInbound` | `accept` delivers, `hold` parks for approval, `refuse` drops. Unset, the runtime decides per message from the two sessions' permission-mode classes |
| `isolatePeerMachines` | `true` requires explicit approval before any message leaves the machine. A `true` from any scope applies |
| `dialogExpiry` | Deadline after which a **default**-held message is dropped — the dialog closes, or in a non-interactive session the held message expires. Five minutes unless set; `never` holds until the session ends. It does not govern a message held by an explicit `hold` |
| `permissions.deny: ["SendMessage", "ListAgents"]` | Turns off sending and listing. Also removes messaging to subagents and teammates, which share the tool |

A fifth path stops a message and is not a setting at all. Each inbox accepts only so many messages in quick succession; once a rapid burst would exceed what the addressed session takes, further sends to it are **refused up front** rather than reported sent and then dropped. Fan-out is the shape that reaches it — a lead nudging N lanes within one turn (Factory Mode, `moai cc -f <N>`) is precisely a rapid burst. A refusal there is the channel working, not a channel fault, and it costs nothing: delegation rides the queue on disk, never the message (`kanban-dispatch.md` § The delegation channel is the queue). Read the send result rather than assuming it, and where every lane genuinely needs nudging, spread the sends across turns instead of firing them together.

The two ways a message is held do not expire alike. A message the inbound **default** holds waits on `dialogExpiry` and is then dropped, and the sender is told it expired; a message held by an explicit `crossSessionInbound: hold` does not expire at all, and is delivered only when an `accept` later applies. A non-interactive worker cannot show an approval dialog, but a default-held message there still runs the same deadline rather than waiting indefinitely — so a worker meant to take messages unattended needs `accept` in its own settings. One asymmetry is worth knowing: while a background session has no terminal attached, the default-held dialog stays open past its deadline, and the countdown only runs properly once you attach.

Two further facts bear on unattended workers. A `claude -p` session binds an inbox socket like an interactive one, but a session started in **bare mode** binds none — it neither receives messages nor appears in listings. And the `/config` row that selects `crossSessionInbound` (v2.1.232+) does not appear while `--settings` or managed settings set the key — a companion session launched with an injected inbound value cannot change it from its own `/config`, only from the settings source that injected it.

**Availability trap**: a session where the peer-listing command is unrecognized does not have the feature — see § Availability constraints for the OS, provider, version, and flag reasons; a session where listing works but a send never arrives is being blocked by something narrower — a deny rule, the receiver's inbound control, or, for a target beyond this machine, the version and listing conditions above.


## Cross-references

- `.claude/rules/moai/core/agent-common-protocol.md` — Pre-Spawn / Pre-Edit Sync Check, the detection layer this composes with
- `.claude/rules/moai/core/askuser-protocol.md` — the user-question channel monopoly, unchanged by this rule
- `.claude/rules/moai/workflow/session-handoff.md` — crossing a context boundary, the mechanism messaging does not replace
- `.claude/rules/moai/workflow/worktree-integration.md` — isolation, the structural fix for a write conflict
- `.claude/rules/moai/workflow/main-checkout-branch-guard.md` — why concurrency is assumed rather than proven absent

---

Version: 1.2.0
Classification: Evolvable operational rule — peer-session communication; changes no gate semantics.


