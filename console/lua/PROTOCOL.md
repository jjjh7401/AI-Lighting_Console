# Copilot Responder Wire Protocol — v1

Contract between the console-side Lua responder (`console/lua/copilot_responder.lua`)
and the server (`server/bridge/protocol.py` is the Python twin). SPEC-COPILOT-MVP-001
M2 deliverable; consumed by the M3 tool-runner and the M4 safety gate.

Versioning: every reply payload carries `"v": 1`. Any breaking change bumps the
version in BOTH implementations and revises this document.

## 1. Addresses (plan.md §A-5 — `/copilot/*` namespace)

| Address | Direction | Carries |
|---|---|---|
| `/copilot/cmd` | server → console | MA3 command lines (native execution) — including responder-invoking plugin calls |
| `/copilot/state` | console → server | State snapshot replies (REQ-MVP-003) |
| `/copilot/feedback` | console → server | Execution results, pong, error replies (REQ-MVP-004) |

grandMA3's native OSC input executes only command lines arriving at
`<prefix>/cmd`; there is no console-side hook for arbitrary custom addresses.
Therefore **state queries ride `/copilot/cmd`** as plugin-invoking command
lines, and `/copilot/state` is the dedicated **reply** channel for snapshots.

## 2. Requests (server → console)

One MA3 command line per request, sent as the single OSC string argument to
`/copilot/cmd`:

```
Plugin "CopilotResponder" "<verb> <request-id> [rest]"
```

| Verb | Form | Reply address / kind |
|---|---|---|
| `ping` | `ping <id>` | `/copilot/feedback`, kind=`pong` |
| `state` | `state <id> <object-path>` | `/copilot/state`, kind=`state` |
| `exec` | `exec <id> <ma3-command>` | `/copilot/feedback`, kind=`result` |

- `<request-id>`: token matching `[A-Za-z0-9._-]+`; echoed back verbatim so the
  server can correlate replies (UDP gives no ordering/delivery guarantee).
- `<object-path>` and `<ma3-command>` are parsed **rest-of-line** (embedded
  spaces are legal) and MUST NOT contain a double quote (`"`), which would
  terminate the MA3 plugin argument. MA3 accepts single-quoted strings, so
  `Store Cue 5 'name'` is the workaround for quoted names.
- Fallback transport (if plugin arguments do not reach `main` on the target
  build): set user variable `COPILOT_REQ` to the request string, then call
  `Plugin "CopilotResponder"` without arguments (two command lines; see
  README troubleshooting).

Object paths resolve against root aliases (case-insensitive first segment):
`DataPool` → `DataPool()` (current pool), `Root` → `Root()`, plus `ShowData` /
`Patch` when those globals exist. Unknown first segments navigate from
`Root()`. Segments match child names case-insensitively; an all-digit segment
selects a child by 1-based index.

## 3. Reply encoding

Every reply is ONE OSC string argument: **percent-encoded JSON**.

- JSON: object at top level; keys sorted (deterministic); integers only.
- Percent-encoding (RFC 3986 style): every byte outside `A-Za-z0-9-._~` is
  encoded as `%XX` — including `,`, `"`, spaces, and all UTF-8 bytes ≥ 0x80.
- Why: MA3's packed OSC-send string form (`"/addr,s,<payload>"`) splits on
  commas, and MA3 command-line quoting breaks on `"`. The encoded payload is
  pure ASCII and contains neither, so it survives every send variant (§5).
- Server decode: `urllib.parse.unquote` → `json.loads`
  (`server.bridge.protocol.decode_payload`; raw unencoded JSON is also
  accepted leniently).

## 4. Reply payloads

### 4.1 `pong` (liveness — on `/copilot/feedback`)

```json
{"v":1, "kind":"pong", "id":"<id>", "plugin":"CopilotResponder",
 "version":"1.0.0", "proto":1}
```

### 4.2 `state` (snapshot — on `/copilot/state`, REQ-MVP-003)

Success (depth-1 snapshot of the resolved node):

```json
{"v":1, "kind":"state", "id":"<id>", "path":"DataPool/Sequences", "ok":true,
 "node": {"name":"Sequences", "class":"Pool", "childCount":12},
 "children": [{"i":1, "name":"Sequence 1", "class":"Sequence"}],
 "truncated": false}
```

- `children` is capped at `CONFIG.max_children` (default 24) and further
  reduced until the encoded payload fits `CONFIG.max_payload` (default 4000
  bytes — UDP budget). `truncated:true` signals a partial listing;
  `node.childCount` always carries the real total. Deeper inspection =
  follow-up query on a child path.
- Failure: `{"v":1,"kind":"state","id":"<id>","path":"...","ok":false,"error":"<message>"}`

### 4.3 `result` (execution result — on `/copilot/feedback`, REQ-MVP-004)

```json
{"v":1, "kind":"result", "id":"<id>", "ok":true,  "result":"OK"}
{"v":1, "kind":"result", "id":"<id>", "ok":false, "result":"Illegal command", "error":"Illegal command"}
{"v":1, "kind":"result", "id":"<id>", "ok":false, "error":"lua error: <message>"}
```

Result capture requires execution to go THROUGH the responder (`exec` wrap):
raw command lines sent to `/copilot/cmd` execute natively, fire-and-forget,
with no result reply — the M3 tool-runner opts into wrapping when it needs
confirmation. The responder never retries and never times out (REQ-MVP-032
handling is server-side M4 scope).

### 4.4 `error` (malformed/unknown request — on `/copilot/feedback`)

```json
{"v":1, "kind":"error", "id":"<id-or-->", "ok":false, "error":"<message>"}
```

## 5. Console-side reply transport (`CONFIG.send_variant`)

| Variant | Mechanism |
|---|---|
| `packed` (default) | `SendOSCMessage(slot, "<address>,s,<payload>")` |
| `args` | `SendOSCMessage(slot, "<address>", "<payload>")` |
| `cmd_keyword` | `Cmd('SendOSC <slot> "<address>,s,<payload>"')` |

All variants are pcall-guarded; on failure of the configured variant the
responder falls back to `cmd_keyword` once. `slot` is the row index of the
console's OSC configuration used for replies (README §OSC setup).

## 6. Live-console assumptions (verify on onPC 2.4.2 — AC-MVP-012 semi-automatic)

Recorded per Section E honesty rules; the round-trip tool
(`server/tools/responder_roundtrip.py`) is the designated verification path.

- **ASSUMPTION-1 (plugin argument)**: `Plugin "Name" "arg"` delivers `arg` as
  the second parameter of the plugin's `main(display_handle, argument)`.
  Fallback: `COPILOT_REQ` user variable (§2).
- **ASSUMPTION-2 (OSC send API)**: `SendOSCMessage` exists with one of the §5
  signatures, or the `SendOSC` command keyword works via `Cmd()`. Select with
  `CONFIG.send_variant`.
- **ASSUMPTION-3 (Cmd result classification)**: `Cmd()` returns a result
  string; `nil`/empty/`"OK"` (case-insensitive) = success, anything else =
  failure with the raw string as the error message. Refine the
  `SUCCESS_RESULTS` table in the plugin if 2.4.2 uses different tokens.
- **ASSUMPTION-4 (handle accessors)**: object handles expose `name` (property
  or `Get("name")`), `GetClass()`, and `Children()` (or `Count()`/`Ptr(i)`).
  The accessors probe all forms defensively.
- **ASSUMPTION-5 (outbound prefix)**: the console does NOT prepend the OSC
  config prefix to custom-sent reply addresses. If replies arrive at
  `/copilot/copilot/*` (detect with the round-trip tool's `--diagnose` mode),
  strip the leading `/copilot` from `CONFIG.state_address` /
  `CONFIG.feedback_address`.
