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
| `vectorworks_export_upload` | `file_name: string`, `content_base64: string` | Vectorworks Instrument Data export (`.csv`, `.txt`, `.xlsx`, or `.mvr`, non-empty and ≤8 MiB). Replaces this connection's source and immediately starts guided comparison. Raw bytes stay session-local; the model calls `vectorworks_autopatch` rather than receiving base64 or asking the operator to paste it. |
| `approval_decision` | `request_id: string`, `approved: bool` | The human decision for a pending `approval_request`. Unknown/expired ids get an `error` (kind `protocol`). |
| `review_decision` | `request_id: string`, `approved: bool` | (M7, additive) The human decision for a pending `review_request` (deploy review). Unknown/expired ids get an `error` (kind `protocol`). |
| `lock` | `active: bool` | Live-lock toggle (REQ-MVP-016). Effective immediately — including while an approval is pending (lock-first, REQ-MVP-035). |
| `status_request` | — | Ask for a `status` event. |
| `panel_execute` | `target_kind: "executor"\|"sequence"\|"macro"`, `target: int ≥ 1` | (SHOWUI M1, additive) Fire one panel tile → `Go+ Executor N` / `Go+ Sequence N`, via `gate.screen()`. One panel execution at a time; a second while busy gets `panel_busy`. `macro` (DASHUI M1, additive) fires the rulebook-verified bare form `Macro N` (00_grammar.md:60) — no playback verb word precedes it. |
| `panel_stop` | `target_kind`, `target` | (SHOWUI M1) Stop one panel tile → `Off Executor N` / `Off Sequence N`, via `gate.screen()`. EXEMPT from the one-at-a-time guard (REQ-SHOWUI-012) — stop is always single-press, zero-wait. Stops are serialized against each OTHER, which is what makes an All Off of N tiles stop N tiles (see below). A macro press is **one-shot** (DASHUI): no rulebook-verified stop form exists, so the panel's command builder refuses to construct a macro stop — the UI offers no Off affordance for a macro tile. |
| `panel_pin` | — | (SHOWUI M1) Pin the chat's last-created look to the panel. Payload-free: the seed is the server's own `_last_created` memory (REQ-SHOWUI-004). |
| `panel_unpin` | `target_kind`, `target` | (SHOWUI M1) Remove one pinned tile; the removal is persisted (REQ-SHOWUI-023). |
| `panel_catalog_request` | — | (SHOWUI M1) Ask for a `panel_catalog` event (sent on connect and on manual refresh). |
| `dash_catalog_request` | — | (DASHUI M1, additive) Ask for a `dash_catalog` event. Payload-free; sent on connect and on manual refresh only — never on a timer (REQ-DASHUI-021). |
| `cue_monitor_request` | — | (T-C, wave 2 — ad-hoc contract, no SPEC on file) Ask for a `cue_monitor` event. Payload-free; sent on connect, on manual refresh, AND on a client-side poll (`CUE_MONITOR_POLL_INTERVAL_MS`, unlike `dash_catalog_request` — see below). A tick arriving while the previous one is still building is **dropped**, and the executor resolution it needs is TTL-cached — see "Poll cost" below. |

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
| `execution_preview` | `preview_id: string`, `summary: string`, `risk_level: "info"\|"caution"\|"danger"`, `commands: [{command, action, target_kind, target, label}]`, `warnings: [{severity, label, detail, command}]` | Additive command-bundle preview sent before safety screening/approval. It is string-based and does not claim a real cue diff, tracking impact, or showfile mutation graph. |
| `approval_request` | `request_id: string`, `items: [{command, risk_reasons[], warnings[]}]`, `actions: ["approve","reject"]` | A held risky bundle (REQ-MVP-021). `warnings` carries e.g. the unspecified-target warning (REQ-MVP-036b). |
| `approval_resolved` | `request_id`, `approved: bool` | Decision echo — retire the approval card. |
| `review_request` | `request_id: string`, `plugin_name: string`, `source_preview: string` (bounded, ≤4000 chars), `source_length: int`, `source_truncated: bool`, `compile_ok: bool`, `scan: ScanReport`, `actions: ["approve","reject"]` | (M7, REQ-MVP-019/027) A pending plugin-deploy review. `scan.destructive: bool`; `scan.findings: [{line, command, kind: "blacklisted"\|"invoking"\|"unparseable", matched_entry, reasons[]}]`; `scan.dynamic_calls: [{line, snippet}]` (Cmd() calls the static scan cannot verify); `scan.caveat` carries the best-effort framing — the human reviewer is the authoritative control. |
| `review_resolved` | `request_id`, `approved: bool` | (M7) Review decision echo — retire the review card. On disconnect/timeout pending reviews are DENIED (same quadruple-deny as approvals). |
| `proposal` | `commands: string[]`, `reasons: string[]` | Read-only proposal card produced under the live lock (REQ-MVP-016). |
| `error` | `message: string` (Korean), `kind: string` | User-facing error. `kind` ∈ normalized provider kinds (`rate_limit`, `auth`, `invalid_request`, `connection`, `server`, `malformed_response`, `unknown`) + `unexpected` + `protocol`. |
| `busy` | `message: string` | An instruction is already in flight. |
| `notice` | `message: string` | Standalone Korean notice (e.g. showfile-backup failure, REQ-MVP-034). |
| `progress` | `phase: "model_call"\|"tool_start"\|"tool_done"`, `detail: string` (Korean), `seq: int ≥ 1` | (지연 개선, additive) 턴이 **도는 동안** 흘러나오는 한 줄 — see "Turn progress streaming" below. 소멸성: 대화록에 쌓이지 않고, 그 턴의 종결 프레임(`chat_response` / `error`)에서 사라진다. |
| `panel_catalog` | `items: PanelItem[]`, `sections: PanelSection[]` | (SHOWUI M1) The panel's executable tile list + per-section completeness. A refresh REPLACES the list; it does not merge. |
| `panel_item_state` | `id: string`, `target_kind`, `target: int`, `running: bool`, `cue: string\|null` | (SHOWUI M1) One tile's playback state. `cue` is the running sequence's current cue — a **string**, because MA3 cue numbers are not integers ("1.5"). |
| `panel_busy` | `id: string`, `target_kind`, `target: int`, `message: string` | (SHOWUI M1) A panel execution was refused because one is in flight (REQ-SHOWUI-011). Names the tile it refused so the UI can unlock that tile — distinct from `busy`, which is the CHAT turn lock the panel deliberately does not share (REQ-SHOWUI-013). |
| `dash_catalog` | `sections: DashSection[]` | (DASHUI M1) The console-info dashboard's read-only pool catalog. A refresh REPLACES the list; it does not merge (REQ-DASHUI-006). Info-only by shape — see DashSection / DashItem below. |
| `cue_monitor` | `executors: CueExecutorEntry[]`, `history: CueHistoryEntry[]` | (T-C, wave 2) The live cue-progress monitor's snapshot — see "Live cue-progress monitor" below. A refresh REPLACES both lists; it does not merge. |
| `song_timeline` | `timeline: SongTimelineView` | 감독이 검토하는 전곡 조명 타임라인. 구간별 D·팔레트·포지션·질감·FX·MIB·Cue·타이밍과 Q1~Q5 확정 상태, lint/disabled/unresolved notes, 승인·readback 상태를 담는다. 명령 문자열이나 실행 제어 필드는 없다. |

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
| `kind` | `look` \| `effect` \| `sequence` \| `macro` | The tile's type badge — LOOK / FX / SEQ (design.md §4) + MACRO (DASHUI M1, additive — widened together with `target_kind` so a macro tile is never stamped `sequence`). |
| `target_kind` | `executor` \| `sequence` \| `macro` | The console object class the command addresses. **`fixture` is absent on purpose**: a fixture's `no` is its patch slot, not its fixture id, so it is not an address the console fires (REQ-SHOWUI-003). `macro` (DASHUI M1, additive): a macro's `no` IS the address the console runs — bare form `Macro N`, one-shot, no stop form. |
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

### DashSection / DashItem (DASHUI M1)

The console-info dashboard's read-only catalog, carried by `dash_catalog`.
**INFO-ONLY by shape (REQ-DASHUI-007)**: a DashItem carries the console fact —
`no` + `name` — and nothing a command could be built from. The PanelItem
address triple (`id` / `target_kind` / `target`) does not exist on this shape,
so a dashboard entry is structurally un-fireable, not merely unfired; the
server's section builder additionally refuses any entry carrying one of those
fields.

DashSection (items ride INSIDE their section, unlike `panel_catalog`'s flat
tile list):

| field | values | meaning |
|---|---|---|
| `name` | string | The pool section (`groups`, `presets`, `macros`, …). |
| `status` | `ok` \| `path_not_resolved` \| `console_unreachable` | Same vocabulary + same distinct-causes rule as PanelSection (REQ-DASHUI-004). |
| `truncated` / `drilldown_capped` / `contents_unavailable` | bool | Same three completeness flags as PanelSection, carried through to the UI. |
| `items` | DashItem[] | Wire order — nothing sorts it (REQ-DASHUI-003). An empty list is a valid empty pool, not an error. |

DashItem:

```json
{"no": 3, "name": "Vocals", "appearance": "#00c8ff"}
```

| field | values | meaning |
|---|---|---|
| `no` | int ≥ 1 | The console's REAL object number (pools are non-contiguous — never a list position, REQ-DASHUI-005). |
| `name` | string | The console name, verbatim. |
| `appearance` | `"#rrggbb"` \| `null` | Appearance colour chip, or `null` when the object has none. |
| `meta` | object (optional) | Extra facts — e.g. the fixture-count summary (REQ-DASHUI-009). Omitted when absent. |

A `dash_catalog` refresh REPLACES the whole section list (the `panel_catalog`
replace semantics, inherited). On disconnect the client keeps the sections but
marks the catalog STALE — the freshness claim, not the data, is the volatile
half (REQ-DASHUI-015) — and rebuilds via `dash_catalog_request` +
`panel_catalog_request` + `status_request` on reconnect.

### Live cue-progress monitor (T-C, wave 2 — ad-hoc contract, no SPEC on file)

Two independent read paths, combined into one `cue_monitor` event
(`server/web/cue_monitor.py`):

1. Per-executor cue progress, for every executor `dash_catalog`'s own
   resolution step has console-VERIFIED (`resolved_executor_nos` — this
   module builds no executor list of its own).
2. Recent execution history — a pure read of the audit log
   (`server/safety/audit.py`), independent of the console connection. This is
   the monitor's guaranteed floor: it renders even when the console is
   completely unreachable.

CueExecutorEntry:

```json
{
  "executor_no": 101,
  "status": "ok",
  "sequence_no": 5,
  "sequence_name": "Song A",
  "cues": [{"no": 1, "name": "PROBEA1", "cue_no": 1}],
  "current_cue": {"status": "unavailable", "tried": ["Cue"]}
}
```

| field | values | meaning |
|---|---|---|
| `executor_no` | int ≥ 1 | The console-VERIFIED executor number (`dash_catalog`'s `meta.console_no`), never a pool slot. |
| `status` | `ok` \| `unassigned` \| `unavailable` | `ok`: the assigned sequence's cue list was read. `unassigned`: the executor answered but carries no sequence. `unavailable`: the executor or its sequence could not be read at all. |
| `sequence_no` / `sequence_name` | int / string \| null | The executor's assigned sequence (`node.sequenceNo`, the same identity probe `StateBodyFetcher._fetch_executor_body` uses), only present when `status: "ok"`. |
| `cues` | CueItem[] | The sequence's cue children (`no` = pool slot, `cue_no` = the responder's additive real cue number when it could read one, PROTOCOL.md §4.2). Empty list when `status` is not `"ok"`. |
| `current_cue` | object \| null | **Independently Optional** — see below. `null` only when `status` is not `"ok"` (there is no sequence to read a current cue against). |

`current_cue.status` is `"ok"` (`value`/`property`/`tried` carried) or
`"unavailable"` (`tried` carried, no `value`). **UNVERIFIED**: no property
name that exposes an executor's live cue position has been confirmed on this
console/responder combination (`CURRENT_CUE_PROPERTY_CANDIDATES` in
`cue_monitor.py` — currently `("Cue",)`, an unverified guess). Every
candidate failing is the EXPECTED and NORMAL path, never an error — the UI
explains the gap to the operator rather than rendering a blank or guessing a
value. **No progress percentage and no timer field exist anywhere in this
shape** — out of scope by contract, since no channel here confirms a fade's
remaining time.

CueHistoryEntry:

```json
{"ts": "2026-08-02T00:00:00+00:00", "command": "Go+ Executor 101", "ok": true}
```

Filtered to the audit log's `kind: "command"` events only (real console
sends) — excluding the gate's own internal `state_query`/`property_query`/
`heartbeat`/`deploy` probing, so a cue-monitor refresh never pollutes its own
history with the read traffic it just performed.

A `cue_monitor` refresh REPLACES both lists (same replace semantics as
`dash_catalog`). Unlike `dash_catalog_request` (REQ-DASHUI-021 forbids timer
polling), `cue_monitor_request` is explicitly contracted to poll
(`CUE_MONITOR_POLL_INTERVAL_MS`, `ui/src/useCopilotSocket.ts`) — "which cue is
live right now" goes stale between chat turns with nothing else to trigger a
refresh.

#### Poll cost (latency-1-3, 2026-08-19)

A `cue_monitor` tick used to rebuild the ENTIRE dash catalog just to learn its
executor console numbers — 26 console round trips per 5s tick, of which 19
(groups / preset pools and their drilldown / macros / plugins / fixtures) were
discarded unread. Measured over a day (`server/audit_logs/probe-*.jsonl`):
457,666 round trips, 81 distinct queries, **100.0% duplicate rate**, 1,221
round trips per minute while completely idle, 67.3ms p90.

That also **bypassed REQ-DASHUI-021** in substance: the requirement forbids
timer-driven re-query of the dash catalog, and the cue-monitor poll was
re-querying every dash section on a timer under a different message name. Two
changes close it:

- The tick resolves executors through `dash.build_executor_catalog` — the
  executors section ALONE (~7 round trips). The other five sections are never
  read on this path, so no timer re-queries them any more; `dash_catalog`
  itself remains refresh-on-demand only, exactly as REQ-DASHUI-021 requires.
- Those executor numbers are TTL-cached process-wide
  (`app.EXECUTOR_NOS_TTL_SECONDS`, 60s) because they change only when the
  operator re-patches. Inside the TTL a tick issues **zero** executor round
  trips. A manual `dash_catalog_request` refreshes the cache immediately, so
  the operator never has to wait out the TTL after a re-patch.

Independently, a tick that arrives while the previous build is still in flight
is dropped rather than queued (one lost UDP reply stalls a build for 5s, which
is exactly the poll interval — an unguarded spawn builds a backlog that never
drains). The drop is recorded in the audit log as `cue_monitor_tick_coalesced`.
The in-flight build produces a newer snapshot than the dropped request would
have, so nothing is lost.

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

### Turn progress streaming — `progress` (additive, protocol stays v1)

측정된 문제: 한 턴은 모델 호출을 최대 24회(`DEFAULT_MAX_MODEL_CALLS`) 돌고,
도구 하나도 짧지 않다 — `server/audit_logs/probe-*.jsonl` 실측에서 콘솔 왕복
p90이 67.3ms이고 `get_spatial_context` 1회가 240~420왕복 = 16~28초였다. CLI
모델 호출 1회도 ~12초다(`server/llm/claude_code_adapter.py` `_DEFAULT_PROFILE`
주석: 다단 도구 턴이 "~70초+ 무응답"으로 쌓여 사용자가 서버가 죽은 줄 안다).
그런데 종전에는 그 사이 프레임이 **0개**였고 화면에는 턴이 전부 끝난 뒤
`chat_response` 하나만 도착했다.

`progress`는 루프의 이음매마다 한 줄을 흘린다:

| `phase` | 언제 | `detail` 예 |
|---|---|---|
| `model_call` | 모델을 부르기 **직전** (마무리 정리 호출 포함) | `요청을 파악하는 중…`, `다음 단계를 판단하는 중… (3번째)`, `마무리 정리 중…` |
| `tool_start` | 도구 하나를 디스패치하기 **직전** | `무대 좌표 읽기…` |
| `tool_done` | 같은 도구가 **끝난 직후** | `무대 좌표 읽기 완료` |

규칙:

- **`seq`는 턴 안에서만 1부터 단조증가한다.** 순서가 곧 의미이고, 늦게 도착한
  프레임이 앞선 상태를 되돌리는 것을 클라이언트가 막을 수 있어야 한다. 턴이
  바뀌면 다시 1로 돌아간다 — 그때는 종결 프레임이 이미 표시를 지운 뒤다.
- **소멸성 상태, 대화록 아님.** 클라이언트는 마지막 한 줄만 들고 있다가 그
  턴의 종결 프레임(`chat_response` 또는 `error`)에서 `null`로 되돌린다. 한 턴에
  수십 줄이 나오므로 전부 기록에 쌓으면 정작 읽어야 할 답이 묻힌다. 소켓이
  끊길 때도 지운다(`clearOnDisconnect`) — 끊긴 뒤의 "…중"은 정보가 아니다.
- **`detail`은 항상 한국어 사용자 문구** (REQ-MVP-020). 영어 도구 이름은 조명
  감독의 어휘가 아니다 — `server/orchestrator/runner.py`의 `_TOOL_TASKS`가
  도구 이름을 작업 이름으로 옮기고, 표에 없는 도구도 문구 없이 지나가지 않는다.
- **Additive, `v`는 1.** 이 이벤트를 보내지 않는 서버에서는 클라이언트가 종전
  그대로 동작하고, 이 이벤트를 모르는 클라이언트는 프레임을 조용히 버린다
  (unknown-type 비대칭, 위 참조).
- **러너는 웹소켓을 모른다.** `Orchestrator`는 선택적 `ProgressSink` 하나만
  받고, 그것을 전송으로 이어 붙이는 일은 `ChatSession._emit_progress` →
  `send_event`가 한다. 싱크가 `None`이면 배출 자체가 없다. 싱크가 던진 예외는
  삼켜진다 — 진행 표시 때문에 실제 턴이 죽는 것은 개선이 아니라 새 고장이다.
- **게이트 감사에는 아무 영향이 없다.** `progress`는 콘솔 왕복을 하나도 만들지
  않는다: 이미 일어나는 일을 이름 붙여 내보내는 것뿐이다.

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
| `not_created` | 생성 안 됨 (Patch 편집기를 연 뒤 재시도 필요) | patch verification read — zero fixtures observed **after the server executed the command**; the usual cause is the console's command destination not being the fixture layer (semi-automatic patch model: the server fires, the operator only keeps the Patch editor open) |
| `partially_created` | 부분 생성 (자동 재시도 안 함) | patch verification read — some but not all fixtures observed |

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
