# Copilot Chat WebSocket Protocol — v1

The contract between the FastAPI WebSocket server (`server/web/`), the React
client (`ui/`), and the M6 measurement harness. Executable half:
`server/web/messages.py` (server) and `ui/src/protocol.ts` (client).

- Endpoint: `ws://<host>:<port>/ws` (default port 8765)
- Framing: one JSON object per text frame, UTF-8
- Versioning: every message carries `"v": 1`. A frame with any other `v` is
  rejected (server) / ignored (client). Breaking changes bump `v`.
- Language rule (REQ-MVP-020/044): every user-facing string the server sends
  (`summary`, `label`, `message`) is Korean. Raw LLM SDK error text NEVER
  appears in any frame — it goes to the diagnostic/audit log only.

## Client → Server

| type | fields | meaning |
|---|---|---|
| `chat` | `text: string` (non-empty) | One Korean instruction. The server processes ONE instruction at a time; a second `chat` while busy gets a `busy` event. |
| `approval_decision` | `request_id: string`, `approved: bool` | The human decision for a pending `approval_request`. Unknown/expired ids get an `error` (kind `protocol`). |
| `review_decision` | `request_id: string`, `approved: bool` | (M7, additive) The human decision for a pending `review_request` (deploy review). Unknown/expired ids get an `error` (kind `protocol`). |
| `lock` | `active: bool` | Live-lock toggle (REQ-MVP-016). Effective immediately — including while an approval is pending (lock-first, REQ-MVP-035). |
| `status_request` | — | Ask for a `status` event. |
| `panel_execute` | `target_kind: "executor"\|"sequence"`, `target: int ≥ 1` | (SHOWUI M1, additive) Fire one panel tile → `Go+ Executor N` / `Go+ Sequence N`, via `gate.screen()`. One panel execution at a time; a second while busy gets `panel_busy`. |
| `panel_stop` | `target_kind`, `target` | (SHOWUI M1) Stop one panel tile → `Off Executor N` / `Off Sequence N`, via `gate.screen()`. EXEMPT from the one-at-a-time guard (REQ-SHOWUI-012) — stop is always single-press, zero-wait. Stops are serialized against each OTHER, which is what makes an All Off of N tiles stop N tiles (see below). |
| `panel_pin` | — | (SHOWUI M1) Pin the chat's last-created look to the panel. Payload-free: the seed is the server's own `_last_created` memory (REQ-SHOWUI-004). |
| `panel_unpin` | `target_kind`, `target` | (SHOWUI M1) Remove one pinned tile; the removal is persisted (REQ-SHOWUI-023). |
| `panel_catalog_request` | — | (SHOWUI M1) Ask for a `panel_catalog` event (sent on connect and on manual refresh). |

Malformed frames (bad JSON, wrong `v`, unknown `type`, missing fields) yield an
`error` event with `kind: "protocol"` and are otherwise ignored.

### Unknown types: the two sides behave DIFFERENTLY, on purpose

This asymmetry is a contract, not an oversight, and neither half may be
"harmonised" into the other (REQ-SHOWUI-014):

| side | on an unregistered type | why |
|---|---|---|
| server (`parse_client_message`) | raises `ProtocolError` → `error` event, `kind: "protocol"` | Client input is untrusted. Anything the server cannot name, it refuses loudly — silence here would mean a frame reaching a handler that was never written for it. |
| client (`parseServerEvent`) | returns `null`; the frame is dropped | A UI must survive a NEWER server. Dropping an event it does not understand keeps an old build usable instead of crashing the panel mid-show. |

The cost of the client's silence is that a type registered on only one side
disappears without a trace — which is why every addition must land on both
allowlists (`CLIENT_MESSAGE_TYPES` / `PANEL_CLIENT_MESSAGE_TYPES` in
`server/web/messages.py`, `SERVER_EVENT_TYPES` in `ui/src/protocol.ts`) in the
same change. `AC-SHOWUI-001` is the parity test that holds this.

## Server → Client

| type | fields | meaning |
|---|---|---|
| `status` | `health: "online"\|"console_offline"\|"responder_degraded"`, `live_lock: bool`, `executions_blocked: bool`, `console_input: "listening"\|"silent"\|"undetermined"`, `reply_port: int\|null`, `receive_port: int\|null` | Gate-truth status (sent on connect, on change via the heartbeat loop, after lock toggles, and on `status_request`). `console_input` and the `reply_port`/`receive_port` pair are additive diagnosis fields — see below. |
| `chat_response` | `status: "ok"\|"retries_exhausted"\|"loop_limit"`, `summary: string` (Korean, server-composed), `text: string` (model's final Korean text), `commands: CommandView[]` | One instruction's final report (REQ-MVP-022). |
| `approval_request` | `request_id: string`, `items: [{command, risk_reasons[], warnings[]}]`, `actions: ["approve","reject"]` | A held risky bundle (REQ-MVP-021). `warnings` carries e.g. the unspecified-target warning (REQ-MVP-036b). |
| `approval_resolved` | `request_id`, `approved: bool` | Decision echo — retire the approval card. |
| `review_request` | `request_id: string`, `plugin_name: string`, `source_preview: string` (bounded, ≤4000 chars), `source_length: int`, `source_truncated: bool`, `compile_ok: bool`, `scan: ScanReport`, `actions: ["approve","reject"]` | (M7, REQ-MVP-019/027) A pending plugin-deploy review. `scan.destructive: bool`; `scan.findings: [{line, command, kind: "blacklisted"\|"invoking"\|"unparseable", matched_entry, reasons[]}]`; `scan.dynamic_calls: [{line, snippet}]` (Cmd() calls the static scan cannot verify); `scan.caveat` carries the best-effort framing — the human reviewer is the authoritative control. |
| `review_resolved` | `request_id`, `approved: bool` | (M7) Review decision echo — retire the review card. On disconnect/timeout pending reviews are DENIED (same quadruple-deny as approvals). |
| `proposal` | `commands: string[]`, `reasons: string[]` | Read-only proposal card produced under the live lock (REQ-MVP-016). |
| `error` | `message: string` (Korean), `kind: string` | User-facing error. `kind` ∈ normalized provider kinds (`rate_limit`, `auth`, `invalid_request`, `connection`, `server`, `malformed_response`, `unknown`) + `unexpected` + `protocol`. |
| `busy` | `message: string` | An instruction is already in flight. |
| `notice` | `message: string` | Standalone Korean notice (e.g. showfile-backup failure, REQ-MVP-034). |
| `panel_catalog` | `items: PanelItem[]`, `sections: PanelSection[]` | (SHOWUI M1) The panel's executable tile list + per-section completeness. A refresh REPLACES the list; it does not merge. |
| `panel_item_state` | `id: string`, `target_kind`, `target: int`, `running: bool`, `cue: string\|null` | (SHOWUI M1) One tile's playback state. `cue` is the running sequence's current cue — a **string**, because MA3 cue numbers are not integers ("1.5"). |
| `panel_busy` | `id: string`, `target_kind`, `target: int`, `message: string` | (SHOWUI M1) A panel execution was refused because one is in flight (REQ-SHOWUI-011). Names the tile it refused so the UI can unlock that tile — distinct from `busy`, which is the CHAT turn lock the panel deliberately does not share (REQ-SHOWUI-013). |

### Panel command outcomes (SHOWUI M3)

Every `panel_execute` / `panel_stop` frame produces exactly ONE terminal tile
event, so a UI that latches a tile on press always has something that unlatches
it (REQ-SHOWUI-011). It is one of:

| terminal event | when |
|---|---|
| `panel_item_state` | the command was screened — whether or not it reached the console. `running` carries the tile's TRACKED state, never a guess. |
| `panel_busy` | refused because a panel execution is already in flight. No bundle was built and the gate was never asked. |
| `error` (`kind: "panel"`) alone | the target is not a panel tile (membership, REQ-SHOWUI-022). No bundle, no `gate.screen()` call — and no tile state, because there is no tile. |

When the command did not reach the console, the terminal event is accompanied
by a Korean `error` with `kind: "panel"` naming the reason (blocked by health,
rejected at approval, backup failed, unconfirmed, …). A refusal is **never**
silent: REQ-SHOWUI-010 exists because a panel that swallows a block is a panel
the operator keeps pressing.

Under the live lock the panel additionally emits the existing `proposal` event
before that `error` — the same read-only card the chat path produces
(REQ-SHOWUI-009), with zero console sends.

**Tracked-running is an observation, not console truth.** The server tracks only
what the panel itself started, so a playback started at the desk is invisible to
it — which is exactly the bounded limitation `spec.md §A` names for All Off. All
Off is composed by the UI as one `panel_stop` per tracked-running tile
(REQ-SHOWUI-025); there is no wide-target command anywhere in the panel path,
because the panel's command builder accepts one verb and one positive integer and
nothing else (REQ-SHOWUI-026).

**Approval-held panel bundles** ride the EXISTING `approval_request` /
`approval_decision` flow (REQ-SHOWUI-008). Note that under the current ruleset a
`Go+ / Off Executor N` is an invoking command whose reference the gate cannot
expand, so it is held for approval on every press — see progress.md §E.2 M3.

### PanelItem (SHOWUI M1)

```json
{
  "id": "executor:191",
  "kind": "sequence",
  "target_kind": "executor",
  "target": 191,
  "name": "Summer Rock",
  "appearance": "#ff3fa4",
  "source": "auto"
}
```

| field | values | meaning |
|---|---|---|
| `id` | `"<target_kind>:<target>"` | Derived tile key. Always the console's REAL object number — **never a list position** (REQ-SHOWUI-003): pool numbers are non-contiguous, so "the 3rd tile" and "object 3" are different objects. The `kind:no` shape also keeps Executor 41 and Sequence 41 apart, which a bare number cannot. |
| `kind` | `look` \| `effect` \| `sequence` | The tile's type badge — LOOK / FX / SEQ (design.md §4). |
| `target_kind` | `executor` \| `sequence` | The console object class the command addresses. **`fixture` is absent on purpose**: a fixture's `no` is its patch slot, not its fixture id, so it is not an address the console fires (REQ-SHOWUI-003). |
| `target` | int ≥ 1 | The real object number. Console pools are 1-based, so `0` and negatives are refused at parse time. |
| `name` | string | The console name, verbatim. |
| `appearance` | `"#rrggbb"` \| `null` | Appearance colour chip — the tile's identity, read before the text (design.md §4). |
| `source` | `pin` \| `auto` | Chat-pinned (REQ-SHOWUI-004) or rig-enumerated (REQ-SHOWUI-001). |

**Order is meaning.** `items` arrives in grid order and neither side sorts it:
new tiles append, existing tiles never move (REQ-SHOWUI-005/017). A tile that
shifts under the operator's finger mid-show is a misfire waiting to happen.

### PanelSection (SHOWUI M1)

Each catalog section reports its own completeness, so the UI never presents a
partial rig as a whole one:

| field | values | meaning |
|---|---|---|
| `name` | string | The rig-context section (`sequences`, `pages`, …). |
| `status` | `ok` \| `path_not_resolved` \| `console_unreachable` | See below. |
| `truncated` | bool | The responder said its own listing was cut short (PROTOCOL §4 `truncated`). |
| `drilldown_capped` | bool | The per-call query budget ran out before every container was opened, so tiles are missing. |
| `contents_unavailable` | bool | At least one container could **not be opened** — distinct from a verified-empty one. Collapsing the two makes a console that failed mid-walk look like a show with nothing configured. |

The two failure statuses stay **distinct and are never merged** (REQ-SHOWUI-002),
mirroring `server/orchestrator/tools.py`:

| status | meaning | operator action |
|---|---|---|
| `path_not_resolved` | a sibling section answered, so the console IS reachable and THIS path is wrong for this showfile | a configuration defect — fix the path |
| `console_unreachable` | nothing answered, so no path can be blamed | an operational condition — retry when the console is up |

Merging them into one soft "unavailable" is exactly how two dead default rig
paths survived a whole stage unnoticed.

### status.console_input (additive, protocol stays v1)

`console_offline` is reached by two different situations that the health monitor
cannot separate: onPC is genuinely down, and onPC is up with its OSC input live
but the responder plugin — the only thing that ever sends — has stopped. Both
produce zero inbound traffic. `console_input` carries the missing discriminator:
a **bind attempt** (never a send) on the console's configured OSC input port.

| value | meaning |
|---|---|
| `listening` | the port is held — something IS listening on the console's OSC input |
| `silent` | the port is free — nothing is listening there |
| `undetermined` | not determined: a non-loopback `console_host` (you cannot bind a remote machine's port), a state other than `console_offline` (nothing to disambiguate), no probe wired, or a probe failure |

Rules:

- **Diagnosis only.** `console_input` never changes `health`, never changes
  `executions_blocked`, and never changes what the safety gate blocks. It exists
  so the UI can name the right cause for a state the gate already decided.
- **Three values, not two.** `undetermined` must stay distinguishable from
  `silent`; collapsing them would show a confidently wrong cause for a remote
  console. On `undetermined` the client falls back to the base guidance.
- **Additive, `v` stays 1** (same call as the M7 `review_decision` extension):
  the field is informational, defaults to `undetermined`, and a client that
  ignores it behaves exactly as before. Only breaking changes bump `v`.
- **A held port proves "something is listening", not "onPC is listening."** The
  client's wording is hedged accordingly.

### status.reply_port / status.receive_port (additive, protocol stays v1)

A grandMA3 OSC entry has **one port used for both directions** (the console's
In&Out → OSC table has a single `Port` column — there is no separate destination
port). So the port the console replies THROUGH lives in the console's OSC table
while the port the app listens ON lives in the app's settings: two numbers, two
places, synchronised by hand, with nothing to signal a drift. A drift makes the
link go quiet while every subsystem is healthy — a third, previously unnamed
cause of `console_offline`.

When the app has observed a console reply arriving on a port other than the one
it listens on, it reports **both numbers**:

| field | meaning |
|---|---|
| `reply_port` | the port a `/copilot/*` reply was actually observed on |
| `receive_port` | the port the app is configured to listen on |

Rules:

- **Present together or not at all.** Both are `null` unless a mismatch was
  actually observed. `reply_port == receive_port` is not a mismatch and is never
  reported.
- **Reported, never applied (REQ-DEPLOY-026).** The app does not switch to the
  observed port. Silently adopting it would put the settings screen and the
  runtime out of agreement with nothing on screen to say so, and would mask a
  genuinely misconfigured console instead of correcting it. The client names both
  numbers and both fixes; the operator chooses which side moves.
- **Diagnosis only**, on the same terms as `console_input`: no effect on
  `health`, on `executions_blocked`, or on what the gate blocks.
- **Discovery is bounded and gated.** It runs only while `health` is
  `console_offline` AND `console_input` is `listening`, at most once per cooldown
  window, over a small explicit set of ports near `receive_port`. The console's
  own input port is excluded — binding it would swallow the app's outbound
  commands. The one ping it needs is the gate's existing heartbeat, so no new OSC
  send surface is opened (AC-MVP-019 / AC-DEPLOY-027).
- **Absence is not proof of correctness.** Discovery only learns where a reply
  lands. If the responder is not running, or the console replies outside the
  candidate set, nothing is observed and nothing is reported — the client then
  falls back to the `console_input` guidance.

### CommandView

```json
{"command": "Store Group 3", "status": "executed_ok", "label": "실행 완료", "detail": "OK"}
```

`status` values (honest gate truth — never render non-success as success):

| status | Korean label | source |
|---|---|---|
| `executed_ok` | 실행 완료 | console-confirmed success |
| `failed` | 실행 실패 | console-confirmed error |
| `unconfirmed` | 실행 미확인 (자동 재전송 안 함) | result-confirmation timeout (REQ-MVP-032) |
| `not_executed` | 미실행 (선행 명령 실패로 중단) | stop-on-first-failure (REQ-MVP-033) |
| `skipped_already_executed` | 건너뜀 (중복 실행 방지) | execution-time atomicity (REQ-MVP-033) |
| `blocked` | 차단됨 | gate block (grammar/health/backup/clearance) |
| `rejected` | 거부됨 | human rejection — all-or-nothing (REQ-MVP-015) |
| `proposal` | 제안 (라이브 잠금 — 전송되지 않음) | live lock (REQ-MVP-016) |
| `held` | 승인 대기 | pending approval |

## Ordering & concurrency

- The server processes one `chat` per connection at a time; `approval_decision`
  and `lock` frames are handled WHILE an instruction is in flight (this is how
  approvals unblock the gate, and how lock-first can win over a pending
  approval).
- Session events (`approval_request`, `proposal`, `notice`, some `status`) may
  interleave ahead of the final `chat_response`. Clients must dispatch by
  `type`, not by position.
- On disconnect all pending approvals are DENIED (fail-safe, REQ-MVP-014).
  Approvals also deny after the server-side timeout (default 600 s).
- On disconnect the client ERASES all panel running state (SHOWUI, REQ-SHOWUI-015/016).
  The console keeps playing, but the app can no longer observe it, and
  "probably still running" is the render that gets an operator to press Off on a
  tile that already stopped. The tile LIST survives (it is server state, not an
  observation); running state is rebuilt from a `panel_catalog_request` +
  `status_request` resync on reconnect. Unconfirmed commands are never
  auto-resent (REQ-MVP-032).

## Round-trip measurement hooks (M6)

Per acceptance.md "왕복 시간 측정 방법": start = `chat` frame receipt at the
server (§1); end = last console result receipt (§2); the human-approval wait
(`approval_request` sent → `approval_decision` received) is subtracted (§3);
retry turns are recorded but excluded from the judged corpus (§4). Implemented
in `server/web/measure.py`; judged values feed the M3 fallback detector.
