# SPEC-COPILOT-SHOWUI-001 — Plan-Phase Research: 연출 컨트롤 패널 (Show-Control Panel)

Deep research for adding a visual show-control panel (buttons/faders/color chips that execute/stop AI-generated looks, effects, and cue sequences) alongside the existing chat. All findings are grounded in file:line references. **No implementation code is proposed here — this is analysis only.**

---

## Architecture analysis

### UI shell and where a side panel plugs in

- **`ui/src/App.tsx`** is the single top-level layout. It is a flat flex column (`ui/src/styles.css:24` `.app { display:flex; flex-direction:column; height:100vh; max-width:860px; margin:0 auto }`) with four stacked regions: `<header class="header">` (App.tsx:42-54), `<StatusBanner>` + `<OnboardingBanner>` + optional `<SettingsPanel>` (App.tsx:55-60), `<main class="main">` holding `<ChatView>` plus the pending approval/review cards (App.tsx:61-74), and `<footer class="composer">` (App.tsx:75-88).
- All server state and every send action come from **one hook**: `const { state, connected, sendChat, sendDecision, sendReviewDecision, sendLock } = useCopilotSocket()` (App.tsx:15). A panel would consume the same hook (or an extension of it) rather than opening its own socket.
- `state` is a `UiState` (`ui/src/protocol.ts:195-200`): `{ entries, status, pendingApprovals, pendingReviews }`. A panel's item list / running-state would naturally become a **new field on `UiState`** folded by the reducer, mirroring how `pendingApprovals`/`pendingReviews` are handled.
- Layout note: `.app` is capped at `max-width:860px` and stacks vertically. A true *side* panel (chat + panel side-by-side) requires either widening `.app` and switching `.main` to a horizontal split, or adding a new flex row. The current CSS has no two-column primitive — this is a real layout change, not a drop-in.
- `SettingsPanel` is rendered as a modal overlay (`.settings-overlay` / `.settings-panel`, styles.css:409-421) toggled by `settingsOpen` state (App.tsx:18, 60). This is the closest existing precedent for a togglable panel region and a good pattern model for a collapsible show-panel.

### Message typing and dispatch (the protocol contract)

- **`ui/src/protocol.ts`** is the TS mirror of `server/web/PROTOCOL.md`, pure functions only (protocol.ts:1-3). It defines:
  - `ServerEvent` union (protocol.ts:62-103): `chat_response`, `approval_request`, `approval_resolved`, `review_request`, `review_resolved`, `status`, `proposal`, `error`, `busy`, `notice`. Gated by `SERVER_EVENT_TYPES` set (protocol.ts:105-116) and `parseServerEvent` (protocol.ts:119-131), which **drops any frame whose `v !== 1` or whose `type` is unknown** (returns `null`, silently ignored).
  - Client builders (protocol.ts:135-163): `buildChat`, `buildApprovalDecision`, `buildReviewDecision`, `buildLock`, `buildStatusRequest`.
  - `reduceServerEvent` (protocol.ts:210-294) — the switch that folds each event into `UiState`.
- **`ui/src/useCopilotSocket.ts`** owns the WebSocket. `reducer` (useCopilotSocket.ts:26-31) dispatches three action kinds: `server` (raw frame → parse → reduce), `user` (local echo), `disconnected` (clears pending cards). Send helpers wrap the builders (useCopilotSocket.ts:129-144). Reconnect with exponential backoff is built in (useCopilotSocket.ts:88-114), and **on close it dispatches `disconnected` which clears all pending approval/review cards** (useCopilotSocket.ts:102-108, protocol.ts:308-311) — because the server fail-safe-denies pending requests on disconnect.
- **Adding a panel means extending this protocol on both sides**: new server event type(s) for "panel items list" and "panel item state", and new client message type(s) for "execute panel item"/"stop panel item". Because `PROTOCOL_VERSION` stays `1` and both `parseServerEvent` (protocol.ts:128) and the server's `parse_client_message` (`server/web/messages.py:46-49`) hard-reject unknown types, **additive fields are safe but new `type` values must be registered in BOTH allowlists** (protocol.ts:105-116 and messages.py:23).

### ApprovalCard / ReviewCard patterns (reusable for panel confirmations)

- **`ui/src/components/ApprovalCard.tsx`**: renders `command + risk_reasons + warnings` with approve/reject buttons (ApprovalCard.tsx:51-92). Key reusable pattern: `createDecisionGuard` (ApprovalCard.tsx:16-26) + a `useRef` guard (ApprovalCard.tsx:41-49) ensures **exactly one decision reaches `onDecision`** even under double-click — pure and DOM-free so it is unit-testable. A panel "execute this risky look" confirmation should reuse this idempotency guard.
- **`ui/src/components/ReviewCard.tsx`**: richer card (compile verdict, scan findings, source preview, approve/reject) — the model for a detail-rich panel item card. It calls `onDecision(review.request_id, bool)` directly (ReviewCard.tsx:73-77).
- **`ui/src/components/ChatView.tsx`**: `statusClass` (ChatView.tsx:5-19) maps per-command status → CSS class (`cmd-ok`, `cmd-unconfirmed`, `cmd-held`, `cmd-skip`, `cmd-bad`). A panel showing per-item run status should reuse these status vocab + classes for visual consistency.

---

## Existing patterns & conventions

### Server WebSocket endpoint and message routing

- **`server/web/app.py`** — the single `/ws` endpoint (app.py:176-289). Flow:
  1. Handshake gate BEFORE `accept()` (app.py:182-197) — Origin+token check (`evaluate_handshake`).
  2. One `ChatSession` per connection (app.py:204-217), constructed from `WebDeps` (app.py:59-90).
  3. Receive loop (app.py:226-280) routes by `message["type"]`: `chat` (runs on a worker thread via `asyncio.to_thread`, **one instruction at a time** — a second while busy gets `busy_event`, app.py:236-242); `approval_decision` (app.py:243-259); `review_decision` (app.py:260-276); `lock` (app.py:277-278); `status_request` (app.py:279-280).
  4. `send_event` is thread-safe via `run_coroutine_threadsafe` (app.py:200-202) — **required** because instruction execution runs off the event loop.
- **There is NO HTTP/WS "execute a raw command" endpoint.** The only route from UI to console is `chat` → `ChatSession.run_instruction` → LLM orchestrator → `run_commands` tool → gate. REST surface is limited to `/api/settings`, `/api/keys` (settings_api.py), `/api/*` provision (provision_api.py), `/healthz` (app.py:171-174). **This is the single most important architectural constraint for the panel** (see Recommendations).

### `get_rig_context` — data shapes the panel would consume

- Implemented in **`server/orchestrator/tools.py:474-513`** (the `get_rig_context` handler inside `build_toolset`). It reads a fixed set of object-tree paths (`DEFAULT_RIG_CONTEXT_PATHS`, tools.py:65-76): `fixture_types`, `fixtures`, `groups`, `sequences`, `preset_pools`, `macros`, `plugins`, `pages`, `matricks`, `worlds`.
- Return shape per section (tools.py:197-212, `_rig_section`): `{ "objects": [...], "truncated": bool, "total": <int|null> }`. Each object (tools.py:169-194, `_rig_object`): `{ "no": <slot>, "name": <name> }` — or `{ "name": ... }` **with no `no`** when the responder could not positively establish the slot (this absence is meaningful — do not guess a number).
- Drill-down sections `preset_pools` and `pages` (tools.py:81, `DEFAULT_RIG_DRILLDOWN`) additionally carry inline `"contents"` (the pool's stored presets / the page's executors), fetched one level deeper with a query budget cap of `RIG_DRILLDOWN_QUERY_CAP = 16` (tools.py:88, 215-256). `contents: []` = verified-empty; `contents_unavailable: true` = one object could not be opened; `drilldown_capped: true` = budget ran out.
- Failure sections come back as `{ "reason": "path_not_resolved" | "console_unreachable", "path", "error" }` (tools.py:497-503, 100-108). **These two are deliberately distinct** and must not be collapsed.
- **Critical for the panel's "auto-list sequences/presets/executors" source**: `pages` objects already list their executors (e.g. "Sequence 30 on Executor 5") — tools.py:585-590 and the tool description. `sequences` = cue lists a look is stored into. So the raw material for panel chips (a sequence bound to an executor that actually fires it) is already in the `get_rig_context` output — **but this tool is currently only invoked by the LLM inside a chat turn**, not exposed as a standalone API (see Risks/Recommendations).
- Wiring: `rig_paths` flows `WebDeps.rig_paths` (app.py:71) → `ChatSession(rig_paths=...)` (session.py:172, 204) → `build_toolset(rig_paths=...)` (tools.py:292). Queries ride `gate.state_port` (session.py:202, gate.py:114-121, 598-607) — **audited, same chokepoint as everything else.**

### OSC exec/command path and reply matching

- **`server/bridge/osc.py`** is the **only** OSC/UDP send surface (osc.py:5-16 contract, REQ-MVP-029). Namespace: `/copilot/cmd` (send), `/copilot/feedback` (exec results), `/copilot/state` (object-tree snapshots) — osc.py:42-45. Deliberately boardop-incompatible namespace (osc.py:41).
- The **only production caller** of the send surface is `SafetyGate` via `_GateExecutor` / `_GateStatePort` (gate.py:104-121). Execution consumes exactly one clearance token per send (gate.py:549-585); no clearance = no send (`"blocked: command was not cleared by the safety gate"`, gate.py:560-564). Every send is audited 1:1 (gate.py:566-573).
- The **console-side reply** is produced by `console/lua/copilot_responder.lua` (the embedded plugin). Slot resolution contract (responder.lua:189-311): a child's slot is reported ONLY when positively established; the listing position is never substituted — `server/safety/console.py` slot arithmetic and `_rig_object` (tools.py:169-194) both depend on this.
- **Firing a look** is a normal command bundle: `Go+ Executor 191`, `Off Executor 191` (rulebook `31_choreography_patterns.md`, "Playback" section). **Stopping** is `Off Executor <n>`. These go through `run_commands` → gate → OSC exactly like any other command. The panel's "execute/stop" therefore maps onto ordinary MA3 command lines, not a new transport.

### Safety invariants panel-triggered execution MUST respect

Every one of these lives on the `screen()` pipeline in **`server/safety/gate.py:265-358`** (the `@MX:ANCHOR` "exactly ONE screening path may exist; a second entry would be a gate bypass by construction", gate.py:260-264):

1. **Health gate** (gate.py:366-388): `console_offline` → `blocked_console_offline`; `responder_degraded` → `blocked_responder_degraded`. New executions blocked when console not online.
2. **Grammar validation** (gate.py:390-423).
3. **Risk classification** (gate.py:425-462, `server/safety/classify.py`): blacklisted commands and unspecified-target destructive commands (`/Overwrite`, `Delete`, `Store … /Overwrite`, broad `*`/`All`/`Everything`/open-ended `Thru`) → **held for human approval** (classify.py:83-106, 162-230).
4. **Live-lock check** (gate.py:464-486, `server/safety/lock.py`): while `LiveLock.is_active`, **nothing is sent** — a `ProposalCard` (read-only) is produced instead. Re-checked **after** approval (lock-FIRST, REQ-MVP-035, gate.py:318-324) and again at every send point (gate.py:504-506, 550-552).
5. **Human approval** for held commands (gate.py:288-316), defaults to **deny-all** (`DenyAllApprovalPort`, gate.py:141). All-or-nothing: a rejection blocks the whole bundle (gate.py:299-315).
6. **Pre-risky showfile backup** (gate.py:326-344) — backup failure is **fail-closed** (`blocked_backup_failed`).
7. **Unconfirmed-history**: a previously-unconfirmed command re-requires approval and is **never auto-resent** (gate.py:448-453, REQ-MVP-032).

**Implication for the panel:** a panel button that fires a look must funnel through `screen()`. It cannot get a shortcut path. If a panel command is destructive (e.g. `/Overwrite`) it will raise an approval card; if the live lock is on, the panel must show a proposal, not execute. Panel UI must reflect `state.status.live_lock` and `executions_blocked` (already on the `status` event, protocol.ts:85-99, messages.py:154-187).

---

## Reference implementations (closest existing analogues to copy)

1. **A new server→client card flow** — model on `review_request`/`review_resolved`:
   - Server event builder: `review_request_event` (messages.py:115-146), registered in the union and reducer (protocol.ts:79-84, 241-256).
   - A second `ApprovalChannel` instance carrying a different payload type (`server/web/approval_bridge.py:19-27` — "payload-agnostic … the deploy REVIEW flow reuses it as a second instance"). Wired in `serve.py:329-338`. This is the exact template if panel-triggered risky execution needs its own confirmation channel.
2. **A new client→server message type** — model on `review_decision`: added to `CLIENT_MESSAGE_TYPES` (messages.py:23), validated in `parse_client_message` (messages.py:58-70), routed in the `/ws` loop (app.py:260-276), built client-side by `buildReviewDecision` (protocol.ts:148-155), sent via `sendReviewDecision` (useCopilotSocket.ts:140-143).
3. **A new REST router** (if panel items are fetched over HTTP rather than WS) — model on `build_settings_router` (settings_api.py:113-195) / `build_provision_router`, composed into `WebDeps.settings`/`provision` and `include_router`'d in `create_app` **before** the static SPA mount (app.py:294-301). Note the `@MX:ANCHOR` boundary rule (settings_api.py:104-112): settings/provision routers **must never import the OSC-send surface** — a panel *execute* endpoint would violate this boundary and belongs on the gated WS/chat path instead.
4. **Status fan-out to all sessions** — `deps.status_listeners` set + `push_status` (app.py:219-222, 108-111). If panel state must be broadcast on console changes, this is the existing pub/sub seam.
5. **Cross-turn "last created look" memory** — `session.py:189-192, 354-389` (`_last_created`, `_session_context_note`). This is how the app already tracks "the look you just made on Sequence N / Executor M" — directly relevant to the **"패널에 추가 (pin from chat)"** source: the just-created sequence/executor is already captured server-side and could seed a panel item.

### Persistence options for pinned panel items

- **Server-side settings**: `server/deploy/settings.py` — TOML at the OS-standard user config dir (`user_config_dir`, settings.py:141-149; `user_settings_path`, settings.py:195-197), atomic write via temp-file + `os.replace` (settings.py:383-404). Schema is a **closed set of recognised keys** (`_RECOGNISED_KEYS`, settings.py:74-80) and **rejects credential-like keys** (settings.py:248-280). Adding a panel-items collection here means extending `UserSettings` (settings.py:97-114) and the hand-rolled TOML dumper (settings.py:362-380) — feasible but the current writer only serialises flat scalars, so a list-of-items payload needs a real serializer or a separate JSON file.
- **Server-side data dir** (`user_data_dir`, settings.py:184-192) is the correct home for non-config runtime state (audit logs live there) — a better fit than settings.toml for a growable pinned-items list.
- **UI-side**: settings client is pure functions (`ui/src/settings.ts:1-8`), fetch/state owned by `SettingsPanel`. No localStorage usage exists today; the app treats the server as source of truth. Pinned items should persist **server-side** so both the packaged Tauri window and browser mode see the same panel, consistent with the current "UI only calls server APIs" design.

---

## Risks, constraints, implicit contracts

1. **No direct execution API exists — and by design.** The only console path is `chat → LLM orchestrator → run_commands → gate` (app.py:236-242, session.py:321-348). The settings/provision routers are **forbidden** from touching the OSC surface (settings_api.py:104-112). A panel "fire this look" button therefore must either (a) send a `chat` instruction (natural-language or a structured directive the model turns into `run_commands`), or (b) introduce a **new gated WS message type** whose handler builds a command bundle and calls `gate.screen()` + the execution port directly. Option (b) reuses the chokepoint but must not create a second screening path (gate.py:260-264 ANCHOR).

2. **fixture number = slot ≠ FID gotcha** (tools.py:36-44, 596-609; responder.lua:189-212). For `fixtures`, `no` is the patch-list slot, **not guaranteed to equal the fixture id**. Panel chips built from fixtures must confirm FID via `query_state` before addressing — the tool description says so explicitly (tools.py:605-609). For `groups`/`sequences`/`macros`/`plugins`/`pages`, `no` **is** the address. Panel item construction must respect this per-section distinction.

3. **Non-contiguous pool numbers** (tools.py:164-168, 598-604): "the Nth listed item is NOT necessarily object N." Panel must key items by real `no`, never by array index — the same defect the `_rig_object` design exists to prevent.

4. **`ChangeDestination Root` for programming, but NEVER for patch** (`31_choreography_patterns.md` "CRITICAL — set the programming destination first"; responder.lua:200, 321-327). Any panel-generated bundle that *programs* (stores/edits a look) must prepend `ChangeDestination Root`; a *patch* bundle must not. Panel-triggered *playback* (`Go+/Off Executor`) does not need it, but AI-generated "looks" that store cues do. This is a live-validated invariant.

5. **`osc_slot` site config** (settings.py:69, 209-220; responder.lua:27): the reply row index (1–32, **not a port** — validated separately from ports precisely so a mis-pasted `9000` is rejected). The panel does not touch this, but any panel that surfaces connection health should read it from `/api/settings` (settings.ts:39, `osc_slot`).

6. **receive_port / reply-port drift** (protocol.ts:342-364, messages.py:154-187, serve.py:371-391): a grandMA3 OSC entry uses ONE port for both directions; the console's reply port and the app's `receive_port` are hand-synced. The status event already carries `console_input`, `reply_port`, `receive_port` for diagnosis. (The memory note "receive_port 9005" is the operator's site value; the code default is `DEFAULT_RECEIVE_PORT = 9000`, settings.py:60 — the panel should read the effective value, never hardcode.) A silent link with everything "healthy" is the drift signature — panel execution feedback could appear to hang for this reason, so the panel must surface `status.health`/`executions_blocked`.

7. **live_lock semantics** (lock.py:1-38, gate.py:464-486): while active, **zero console sends**; panel must render items as disabled/proposal-only and reflect `state.status.live_lock`. Lock can activate mid-approval and retroactively neutralize a held bundle (REQ-MVP-035, gate.py:318-324).

8. **Approval-required command classes** the panel will hit (classify.py:33, 162-230; ruleset): blacklisted keywords (`Delete`, etc.), destructive store flags (`/Overwrite` — flagged in the rulebook as "DESTRUCTIVE → human approval"), unspecified-target destructive commands, quoted `Property 'Command'/'Cmd'` values that smuggle executable text (classify.py:133-211), and any previously-unconfirmed command. A panel that lets users pin arbitrary AI choreography can produce any of these — so the **approval card flow is not optional** for the panel; it must be wired (reuse `ApprovalCard`, App.tsx:63-69).

9. **Fail-closed on disconnect** (useCopilotSocket.ts:102-108, protocol.ts:308-311, approval_bridge.py:11-16): pending requests are denied and cleared on close. Panel "running" state must be treated as ephemeral/derived, re-synced on reconnect via a status/list request — never assumed to survive a reconnect.

10. **One-instruction-at-a-time** (app.py:236-242): the session serializes chat turns. If the panel routes execution through `chat`, a burst of button presses will get `busy_event` responses. A panel firing multiple looks needs either queueing UX or a dedicated non-`chat` gated handler that does not share the single-turn lock (design decision for the SPEC).

11. **Additive-protocol discipline**: `PROTOCOL_VERSION` must stay `1`; unknown `type` values are dropped on both ends (protocol.ts:128-129, messages.py:46-49). Every new event/message type must be added to both allowlists **and** the reducer/handler, or it silently vanishes.

---

## Recommendations for implementation approach

1. **Reuse the WS+gate chokepoint; do not add an ungated execute endpoint.** Add panel execution as a **new gated client message type** (e.g. `panel_execute` / `panel_stop`) registered in `messages.py:23` + `parse_client_message`, routed in `app.py`'s `/ws` loop, and handled by building a command bundle (`Go+ Executor N` / `Off Executor N`, or the stored look's commands) that passes through `gate.screen()` exactly as `run_commands` does. This preserves every safety invariant (§Risks 1, 7, 8) without forking the screening path. Mirror the `review_decision` wiring end-to-end (§Reference 2).

2. **Expose `get_rig_context` output as a panel-list source over an existing gated seam.** The data shapes are ready (§get_rig_context), but the tool runs only inside LLM turns today. Add a read-only WS event (e.g. `panel_catalog`) or a small router that calls `gate.state_port.query_state` through the same `build_toolset` logic — reusing `_rig_object`/`_rig_section` so the fixture-slot-vs-FID and non-contiguous-number contracts (§Risks 2,3) are honored automatically. Prefer the WS/status path over a REST router, since a REST router is boundary-forbidden from the console surface (settings_api.py:104-112).

3. **Persist pinned items server-side in the data dir, not settings.toml.** Use `user_data_dir` (settings.py:184-192) with a dedicated JSON file and atomic-write pattern (settings.py:383-404). Keep credentials out by construction (the settings module's credential-rejection is the precedent, settings.py:248-280). Seed pins from the existing `_last_created` cross-turn memory (session.py:354-389) for the "패널에 추가" flow.

4. **Model the panel UI on `SettingsPanel` (togglable region) + `ApprovalCard`/`ReviewCard` (item cards).** Extend `UiState` with a `panel` field folded by `reduceServerEvent`; add send helpers to `useCopilotSocket` next to `sendDecision`/`sendLock`. Reuse `createDecisionGuard` (ApprovalCard.tsx:16-26) for one-shot fire idempotency, and `statusClass` (ChatView.tsx:5-19) for per-item run status colors. Gate every panel control on `state.connected`, `state.status.live_lock`, and `state.status.executions_blocked`.

5. **Layout**: introduce a two-column split inside `.main` (or widen `.app` beyond 860px) — this is a genuine CSS change since no horizontal layout primitive exists today (styles.css:24-31, 79). Consider a collapsible panel to preserve the chat-first experience.

6. **Test scaffolding to follow** (all existing conventions):
   - **UI**: pure-function tests with Vitest, no DOM (`ui/src/protocol.test.ts`, `useCopilotSocket.test.ts`; `package.json` `"test": "vitest run"`). New panel reducer logic and message builders/parsers should be pure and covered exactly like `parseServerEvent`/`reduceServerEvent` (protocol.test.ts:23-49). `ApprovalCard.test.tsx` shows the guard-tested component pattern.
   - **Server**: pytest with the autouse in-memory keyring (`server/tests/conftest.py:1-27`), message-schema tests (`test_web_messages.py`), gate-invariant tests (`test_safety_gate.py`, `test_safety_lock_monitor.py`), and the architecture import-boundary test (`test_architecture.py`) which will **enforce that any new panel module does not import the OSC send surface** — write new server code to pass it. E2E flows: `test_web_e2e.py`, `test_web_approval_bridge.py` are the templates for a panel-execute round-trip test.

7. **Honor programming vs. patch destination** (§Risk 4): if the panel stores/edits AI looks (not just fires them), the generated bundles must prepend `ChangeDestination Root`; keep this in the rulebook-driven command generation, not hardcoded in the panel.

**Key load-bearing files to cite in the SPEC**: `ui/src/App.tsx`, `ui/src/protocol.ts`, `ui/src/useCopilotSocket.ts`, `ui/src/components/{ApprovalCard,ReviewCard,ChatView,SettingsPanel}.tsx`, `ui/src/settings.ts`, `ui/src/styles.css`; `server/web/{app,messages,session,settings_api,serve,approval_bridge}.py`, `server/orchestrator/tools.py`, `server/safety/{gate,classify,lock}.py`, `server/bridge/osc.py`, `server/deploy/settings.py`, `console/lua/copilot_responder.lua`, `server/rulebook/assets/v2.4.2/31_choreography_patterns.md`.
