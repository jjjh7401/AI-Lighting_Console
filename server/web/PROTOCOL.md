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

Malformed frames (bad JSON, wrong `v`, unknown `type`, missing fields) yield an
`error` event with `kind: "protocol"` and are otherwise ignored.

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

## Round-trip measurement hooks (M6)

Per acceptance.md "왕복 시간 측정 방법": start = `chat` frame receipt at the
server (§1); end = last console result receipt (§2); the human-approval wait
(`approval_request` sent → `approval_decision` received) is subtracted (§3);
retry turns are recorded but excluded from the judged corpus (§4). Implemented
in `server/web/measure.py`; judged values feed the M3 fallback detector.
