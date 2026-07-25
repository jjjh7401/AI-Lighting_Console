# Copilot Responder Wire Protocol — v1

Contract between the console-side Lua responder (`console/lua/copilot_responder.lua`)
and the server (`server/bridge/protocol.py` is the Python twin). SPEC-COPILOT-MVP-001
M2 deliverable; consumed by the M3 tool-runner and the M4 safety gate.

Versioning: every reply payload carries `"v": 1`. Any breaking change bumps the
version in BOTH implementations and revises this document.

> Revision note (responder 1.3.0): `send_reply` now tries **every** send
> variant (configured first, then `packed`, `args`, `cmd_keyword`) instead of
> the configured one followed immediately by `cmd_keyword`. Live 2026-07-22: on
> a console whose `SendOSCMessage` takes `(slot, address, payload)`, the
> `packed` default raised and `args` was never attempted, so the reply left via
> `Cmd('SendOSC ...')` — which that console rejected with `Illegal property`.
> `Cmd()` does not raise on a rejected command, so `pcall` reported success and
> the reply silently died. `cmd_keyword` therefore stays LAST, precisely
> because its failures are invisible to the responder. No wire change; protocol
> version stays 1.
>
> Revision note (responder 1.2.0): the snapshot child `i` is now the **real
> pool slot** and is **omitted** when that slot could not be established (§4.2,
> ASSUMPTION-7); a numeric path segment addresses the pool slot accordingly
> (§2). Wire protocol version stays 1: the change is parse-compatible in both
> directions (`i` becomes optional — the server already degrades an `i`-less
> child to a name-only rig-context entry, `server/orchestrator/tools.py`), and
> no consumer ever wanted the previous value. What changed is the *meaning*:
> `i` used to be the child's position in the (gap-compacted) listing, which on
> a non-contiguous pool is not an addressable object number at all.
>
> Revision note (M7, responder 1.1.0): ADDITIVE `deploy` verb (§2) + `deploy`
> reply kind (§4.5) + ASSUMPTION-6 (§6). Wire protocol version stays 1.
> Also fixed in 1.1.0: the reply JSON encoder's escape class is now
> byte-explicit (`[\0-\31"\\\127]`) — the former Lua `%c` class was
> locale-dependent and corrupted UTF-8 bytes 0x80–0x9F in non-ASCII replies.

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
| `deploy` | `deploy <id> <enc-name> <enc-source>` (M7) | `/copilot/feedback`, kind=`deploy` |

- `deploy` (M7, REQ-MVP-019): `<enc-name>` and `<enc-source>` are BOTH
  percent-encoded (same RFC 3986 style as replies, §3) so the request tokens
  are pure ASCII with no spaces/quotes regardless of the Lua source content.
  The responder percent-decodes, **re-compiles the source in the console
  runtime** (`load(source, name, "t")` — text-only, never executed at deploy
  time; defense in depth behind the server-side pcall harness), then finds or
  creates the plugin object in `DataPool/Plugins` and sets its Lua component
  source (ASSUMPTION-6). The server sends ONLY review-approved source through
  this verb (`server/deploy/pipeline.py`, REQ-MVP-019).

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
selects a child by its **pool slot** — the same number a snapshot reports as
`i` (§4.2) — so `DataPool/Groups/5` is Group 5, not the 5th listed group, and
an empty slot resolves to `path segment not found` rather than a neighbour.
Only when NO slot could be established for any child (ASSUMPTION-7 unmet) does
a numeric segment fall back to its legacy 1-based positional meaning.

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

- Each `children` entry is `{"i": <pool slot>, "name": ..., "class": ...}`,
  and **`i` is present only when the responder positively established that
  child's real pool slot**. A pool's `Children()` listing is gap-compacted, so
  the listing position is NOT an address. Two sources are tried, in this
  priority (ASSUMPTION-7): (1) the child's own index accessor, accepted only as
  a coherent whole-listing set; (2) the listing position, accepted per child
  only when `parent:Ptr(pos)` hands that same object back. When neither
  answers, the entry carries **no `i` at all**:
  ```json
  {"name":"Drums", "class":"Group"}
  ```
  Consumers MUST treat a missing `i` as "number unknown" and resolve it before
  addressing the object — never fill it in from the array position. That is
  exactly the failure this shape prevents: a 1/5/7 Groups pool previously
  reported `i` 1/2/3, so `Group 2 + 3` was issued against objects that do not
  exist. Server-side handling: `server/orchestrator/tools.py` emits a
  name-only rig-context entry (no `no`), and `server/safety/console.py`
  refuses to compute a free plugin slot rather than risk overwriting one.
- `children` is capped at `CONFIG.max_children` (default 24) and further
  reduced until the encoded payload fits `CONFIG.max_payload` (default 1900
  bytes — MA3 command-line budget, §5). `truncated:true` signals a partial
  listing; `node.childCount` always carries the real total. Deeper inspection =
  follow-up query on a child path.
- **There is no paging.** The request carries no offset and the reply carries
  no cursor, so a `truncated:true` listing cannot be continued — re-querying
  the same path returns the same first N children forever. To enumerate a pool
  larger than the cap, query each slot as its own path
  (`<pool>/<n>`, e.g. `DataPool/Macros/150`) and stop once `node.childCount`
  from the pool query has been accounted for. A slot query answers whether or
  not the slot is occupied, so the scan needs no prior knowledge of which
  numbers exist. Measured live 2026-07-25 on a 27-macro pool that reported
  only 17 children: batches of 10 slot queries with a ~2.5 s collection window
  recovered 27/27 without dropping a request on the MA3 command queue.
- **`node.sequenceNo`** (additive, `Executor` nodes only, SPEC-COPILOT-EXECBODY-001
  M2/REQ-EXECBODY-003): the pool number of the sequence assigned to this
  executor, e.g. `{"name":"Exec 201", "class":"Executor", "childCount":0,
  "sequenceNo":71}`. `Executor.Children()` never populates (the executor's
  assigned sequence is not a child), so this is the sole body-identity path
  for executors. Present only when `handle.Object` (or `:Get("Object")` /
  `:Get("object")`) resolves to a handle whose `GetClass()` is `"Sequence"`
  AND that handle's own pool number was established via the SAME
  self-index-accessor set used for child slots (ASSUMPTION-7/§6) — never by
  parsing the executor's `name` (AC-EXECBODY-005: `name` is user-editable and
  not guaranteed to encode the assignment, per ASSUMPTION-12/§6). Absent
  entirely (no `sequenceNo` key) when unassigned, wrongly-classed, or the
  number could not be established — consumers MUST treat absence as "unknown"
  and never substitute a guess. Wire protocol version stays 1 (additive field
  on an existing reply kind — same precedent as ASSUMPTION-6/§4.5).
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

### 4.5 `deploy` (deployment result — on `/copilot/feedback`, M7 REQ-MVP-019)

```json
{"v":1, "kind":"deploy", "id":"<id>", "ok":true,  "name":"Cleaner", "created":true}
{"v":1, "kind":"deploy", "id":"<id>", "ok":false, "name":"Cleaner", "error":"lua compile failed: ..."}
```

- `created` is `true` for a newly created plugin object, `false` when an
  existing plugin of the same name was updated in place.
- Failure modes: console-side compile failure, missing plugin pool, or an
  accessor probe failure (ASSUMPTION-6) — all reported in `error`, never
  retried by the responder.

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
- **ASSUMPTION-7 (child pool slot)**: at least ONE of these holds on 2.4.2 —
  (a) a child reports its own 1-based pool slot through `child:Index()` /
  `child.index` / `child.no` / `child:GetIndex()` / `child:Get("no")` (probed
  in that order, pcall-guarded), or (b) `parent:Ptr(n)` is **slot-addressed**
  (the object AT slot n, `nil` for a gap) rather than positional.
  (a) takes priority and is accepted only as a coherent whole-listing set —
  one value per child, each ≥ 1, strictly increasing — so a silent or 0-based
  accessor is discarded entirely instead of contributing plausible wrong
  numbers. (b) is used to confirm the listing position per child; it is
  deliberately NOT allowed to veto (a), because a positional `Ptr()` would
  otherwise overturn a correct self-reported slot.
  Failure modes, in order of severity: if (a) is absent and (b) is positional,
  the responder cannot tell a gapped pool from a dense one and re-emits
  listing positions — **the original defect, undetectable from the console
  side**; if (a) is absent and (b) is slot-addressed, children after the first
  gap degrade to name-only (rig context loses their numbers, file+Import
  deployment refuses to pick a slot). Verify on-site by snapshotting a
  deliberately gapped pool (e.g. groups at 1, 5, 7) and reading the `i`
  values: `1,5,7` = (a) works; `1` plus two number-less entries = (b) only;
  `1,2,3` = **neither** — do not trust any reported pool number.
- **ASSUMPTION-12 (executor → assigned-sequence accessor, VERIFIED on 2.4.2,
  SPEC-COPILOT-EXECBODY-001 M1/M2)**: an executor handle exposes its assigned
  sequence via `.Object` (also reachable as `:Get("Object")` / `:Get("object")`,
  all three confirmed equivalent live) — a real object handle (`userdata`),
  NOT the executor's display name. On that handle, `GetClass()` returns the
  string `"Sequence"` and the same self-index-accessor set as ASSUMPTION-7
  (`:Index()` / `:Get("No")` / `:Get("no")`, all three confirmed) returns its
  real pool number. `.Assign` / `:Get("Assign")` do NOT exist (both probed:
  `nil`, no error). Live evidence: `.moai/state/verify/execbody_probe_v5.lua`
  (round 1 — accessor existence) and `execbody_probe_v6.lua` (round 2 —
  class + number confirmation), full record in design.md §5.9. Consumed by
  `M.safe_object` + the `Executor` branch of `build_snapshot` (§4.2
  `node.sequenceNo`).
- **DEFERRED (fixture id in the snapshot)** — NOT assumed, NOT implemented.
  A child of `Patch/Stages/1/Fixtures` carries only its container slot (`i`),
  never its fixture id (FID), so `Fixture <i>` selects the wrong rig whenever
  slot ≠ FID — silently, because MA3 accepts the range and stores the look.
  The prompt surface forbids that shortcut instead
  (`server/rulebook/assets/v2.4.2/31_choreography_patterns.md`,
  `20_korean_terms.md`, and the `get_rig_context` tool description). That is
  containment, not a fix: the model still cannot build a NEW group from a
  natural-language description without a `query_state` round-trip.
  Emitting a real `fid` per fixture child is the fix. It is blocked on
  verification, not on effort:
  (i) no FID *read* accessor is established anywhere in this repo — `child.fid`
  and `child:Get("fid")` are guesses, and the only `fid` evidence is the WRITE
  side (`AddFixtures{ fid = ... }`, live-proven);
  (ii) ASSUMPTION-7 probe (a) already reads `child.no` / `child:Get("no")`, so
  if either returns an FID on a real 2.4.2 fixture the strictly-increasing gate
  ACCEPTS it and emits it as `i` — the responder cannot tell the two apart;
  (iii) the site calibration showfile has slot == FID by coincidence and so
  CANNOT distinguish a correct FID probe from a slot probe. Verify only against
  a showfile patched so slot ≠ FID (e.g. FIDs 101..109 in stage slots 1..9).
  Budget is not the constraint: +432 B worst case at `max_children` = 24 against
  a 4000 B `max_payload`. An optional `fid` key is additive and wire-compatible
  (both readers use keyed `get`), but four exact-shape contract pins would need
  a deliberate update rather than a silent repair — `test_tools.py`
  TestGetRigContext (3) and `test_lua_responder.py`
  `test_unknown_slot_reaches_the_llm_as_a_name_only_entry`.
- **ASSUMPTION-5 (outbound prefix)**: the console does NOT prepend the OSC
  config prefix to custom-sent reply addresses. If replies arrive at
  `/copilot/copilot/*` (detect with the round-trip tool's `--diagnose` mode),
  strip the leading `/copilot` from `CONFIG.state_address` /
  `CONFIG.feedback_address`.
- **ASSUMPTION-6 (plugin-object API, M7)**: the plugin pool is reachable as
  `DataPool/Plugins`; `pool:Acquire()` (fallback `Append()`) creates a plugin
  object; the plugin's name is settable via `.name` (fallback
  `:Set("name", ...)`); a Lua component is the plugin's first child or
  created via `plugin:Acquire()`/`Append()`; the component's source is
  settable via `.content` / `.Content` / `:Set("content", ...)` /
  `:SetContent(...)` (probed in that order, pcall-guarded). Also assumes the
  MA3 OSC input accepts command lines long enough to carry a percent-encoded
  plugin source (server-side cap: 16 KB source before encoding — calibrate at
  M6). Mitigation: every probe failure is reported verbatim in the `deploy`
  reply's `error`; verify on-site with a harmless one-line plugin first.
