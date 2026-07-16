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
| `lock` | `active: bool` | Live-lock toggle (REQ-MVP-016). Effective immediately — including while an approval is pending (lock-first, REQ-MVP-035). |
| `status_request` | — | Ask for a `status` event. |

Malformed frames (bad JSON, wrong `v`, unknown `type`, missing fields) yield an
`error` event with `kind: "protocol"` and are otherwise ignored.

## Server → Client

| type | fields | meaning |
|---|---|---|
| `status` | `health: "online"\|"console_offline"\|"responder_degraded"`, `live_lock: bool`, `executions_blocked: bool` | Gate-truth status (sent on connect, on change via the heartbeat loop, after lock toggles, and on `status_request`). |
| `chat_response` | `status: "ok"\|"retries_exhausted"\|"loop_limit"`, `summary: string` (Korean, server-composed), `text: string` (model's final Korean text), `commands: CommandView[]` | One instruction's final report (REQ-MVP-022). |
| `approval_request` | `request_id: string`, `items: [{command, risk_reasons[], warnings[]}]`, `actions: ["approve","reject"]` | A held risky bundle (REQ-MVP-021). `warnings` carries e.g. the unspecified-target warning (REQ-MVP-036b). |
| `approval_resolved` | `request_id`, `approved: bool` | Decision echo — retire the approval card. |
| `proposal` | `commands: string[]`, `reasons: string[]` | Read-only proposal card produced under the live lock (REQ-MVP-016). |
| `error` | `message: string` (Korean), `kind: string` | User-facing error. `kind` ∈ normalized provider kinds (`rate_limit`, `auth`, `invalid_request`, `connection`, `server`, `malformed_response`, `unknown`) + `unexpected` + `protocol`. |
| `busy` | `message: string` | An instruction is already in flight. |
| `notice` | `message: string` | Standalone Korean notice (e.g. showfile-backup failure, REQ-MVP-034). |

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
