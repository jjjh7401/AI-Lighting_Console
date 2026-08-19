# CopilotResponder — grandMA3 onPC install & verification (M2)

Console-side Lua 5.4 responder plugin for SPEC-COPILOT-MVP-001. Provides
object-tree state snapshots (REQ-MVP-003) and command execution result capture
(REQ-MVP-004) over the `/copilot/*` OSC namespace. Wire format:
[PROTOCOL.md](PROTOCOL.md).

Target: **grandMA3 onPC 2.4.2** (macOS build; any onPC platform works — the
responder follows onPC's supported platform range per REQ-MVP-043).

## 1. Configure OSC in onPC

**Every brand-new show starts with NO usable OSC config** — onPC does not
carry OSC settings forward from a previous show. Skipping this section is the
#1 cause of "the plugin is installed and running but the console never
replies" on a fresh show.

### 1.-1 Zero-touch path (BEST — no computer-use, no per-show clicks)

Interface selection has NO command-line or file-import equivalent — verified
2026-08-12 live: `Set 'ShowData'.'OSCBase' 'Interface' "lo0"` and the numeric
form `Set 'ShowData'.'OSCBase' 'Interface' 1` both fail with `Illegal value`.
It is GUI-dialog-only in onPC 2.4.2, which means the app (or any agent acting
for it) can never fully self-bootstrap OSC on a truly blank show.

But OSC config — Interface, Enable Output/Input, both OSCData rows, AND the
imported plugin — all live **inside the .show file itself**. A show created
via `File > New` starts blank; a show created via **Save As from an
already-configured show** inherits all of it. This turns the entire manual
bootstrap into a one-time cost:

1. Once, by hand: configure OSC per §1.1 below on any show, then
   `Menu > Backup > Save As` it under a dedicated name (this project's copy:
   `CopilotOscTemplate.show`).
2. Every future session: start new work with **`Backup > Save As` from
   `CopilotOscTemplate.show`**, never `New Show`. The saved copy already has
   Interface=lo0, both OSCData rows, Enable Output/Input, and the imported
   plugin — the console replies before the operator does anything else.

This is the only path with truly zero manual steps per show. Sections 1.0/1.1
below exist for the one-time template setup and for recovering a show that
was started from `New Show` anyway.

### 1.0 Automated path (recommended)

`POST /api/provision/responder` stages two import-ready OSCData files —
`copilot_osc_row1_receive.xml` / `copilot_osc_row2_send.xml` — into the site's
configured OSC import directory (default
`~/MALightingTechnology/gma3_library/inout/osc/`), with the console/receive
ports rendered from the app's settings. This turns steps 3-4 below into an
`Import` + file pick instead of re-typing every field. See
`server/deploy/provisioning.py` `OSC_TEMPLATE_ASSETS` /
`install_osc_templates` / `osc_bootstrap_guide` for the implementation — it is
filesystem-only, same safety boundary as the plugin install (AC-DEPLOY-014 ③).

### 1.1 Verified recipe (2026-08-12, live onPC 2.4.2.2)

Captured by reading a known-working show's `Menu → Settings → In & Out → OSC`
screen and exporting both rows via onPC's native `Export`. Reproduce this
exactly — a plausible-looking row is not the same as this one:

1. **Interface**: set to **`lo0 (127.0.0.1)`**, not the machine's Wi-Fi/
   Ethernet adapter (`en0` or similar). This is the single most-missed step:
   a console left on `en0` silently never delivers 127.0.0.1 traffic even
   after every port and destination field is otherwise correct — no error is
   ever shown, the console just never replies (see Troubleshooting).
2. **Enable Output** and **Enable Input**: both ON (shown in yellow when
   enabled).
3. **Row 1 — receive** (`copilot_osc_row1_receive.xml`): `Prefix=copilot`,
   `Port=8000` (must equal the app's `console_port` setting), `Receive=Yes`,
   `ReceiveCommand=Yes` (native "execute an incoming OSC string as a command
   line" — this is how `server.bridge.osc.OscBridge.send_command` reaches the
   console; no plugin round trip needed for the send direction), `Send=No`.
   Destination IP is irrelevant for a receive-only row.
4. **Row 2 — send** (`copilot_osc_row2_send.xml`): `DestinationIP=127.0.0.1`,
   `Port=9005` (must equal the app's `receive_port` setting), `Send=Yes`,
   `SendCommand=Yes`, `Receive=No`. This is the row `CONFIG.osc_slot` in the
   Lua must index — the responder's `SendOSCMessage(CONFIG.osc_slot, ...)`
   reply channel.
5. Confirm with a round trip: run `Plugin "CopilotResponder" "ping <id>"` on
   the console command line and check the app's `/healthz` — `health` flips
   from `console_offline` to `online`.

Both templates omit the `Guid` attribute so onPC assigns a fresh one on
Import; re-importing the same file into two different shows never collides.

## 2. Install the plugin

Two options — Option B always works and needs no import-format compatibility.

### Option A — import the XML wrapper

1. Copy `copilot_responder.xml` and `copilot_responder.lua` into the onPC
   plugins library folder. macOS default:
   `~/MALightingTechnology/gma3_library/datapools/plugins/`
2. In onPC: open a `Plugins` pool window, then import via
   `Import/Export → Import` (or command line: `Import Plugin "copilot_responder"`),
   selecting the copied file.
3. Verify the plugin appears in the pool with name `CopilotResponder`.

### Option B — paste into a new plugin (guaranteed path)

1. In onPC: open a `Plugins` pool window, edit an empty pool slot
   (`Edit` + tap), which opens the plugin editor.
2. Set the plugin name to `CopilotResponder`, add/open its Lua component,
   and open the text editor.
3. Paste the full contents of `copilot_responder.lua`. Save.

### 2.1 Deployment reliability — updating an ALREADY-imported plugin

Re-importing (Option A) over an EXISTING same-named plugin has been observed
to NOT refresh its stored Lua source on 2.4.2 (2026-07-24 finding): the
plugin pool slot silently kept running the OLD code even though the external
`.lua` file on disk was correctly updated and the import reported success.
This is a PLUGIN POOL caching issue, distinct from the stale-OSC-socket issue
in the Troubleshooting table below.

**Always verify a deploy actually took effect — do not assume Import
succeeded.** Immediately after ANY re-import, run:

```bash
uv run python -m server.tools.responder_roundtrip \
    --host 127.0.0.1 --port 8000 --listen-port 9005 \
    --skip-exec --expect-version "<the version you just deployed>"
```

`[FAIL] ping: live responder version '...' != expected '...'` means the
re-import did NOT take. Recovery, in order:

1. **Delete the existing plugin slot, then re-import fresh** (Option A,
   applied to an empty slot instead of an existing one).
2. **Option B (paste-in) — guaranteed.** Open the existing plugin's Lua
   component editor, select all, delete, and paste the full updated
   `copilot_responder.lua` source. This directly overwrites the stored
   source and has not been observed to fail.

For any FUNCTIONAL Lua change (not just a `CONFIG` value tweak), consider
skipping straight to Option B — it is the only path confirmed reliable for
both kinds of change.

### 2.2 Deployment reliability — the app's automated re-deploy (alias swap)

When the app deploys through the gate (`deploy_plugin`, file+Import path), a
re-deploy of a plugin that ALREADY exists under the same Name cannot simply
delete the old object first. Every command the app sends is wrapped as
`Plugin "CopilotResponder" "exec <id> <cmd>"`, so `Delete Plugin <responder's
own slot>` would run INSIDE the object it deletes. MA3 2.4.2 answers a
self-delete with a confirmation dialog, and the OSC/exec path has no channel to
answer it, so the console reports `User Canceled Command`. Importing the same
Name into an empty slot is refused for the same reason (a duplicate Name asks
the same question). Measured live: `docs/research/ma3-effects/12-introspect-v161-redeploy-probe.md`
§1.

The app therefore swaps the responder through a temporary alias — four commands,
none of them self-referencing:

```
Import Plugin <free slot> '<stem>' /nc          # duplicate Name needs /nc; MA3 names the copy
(from the alias) Delete Plugin <old slot>       # foreign object -> no dialog
(from the alias) Import Plugin <old slot> '<stem>'   # real Name is free again; NO /nc
(from the new primary) Delete Plugin <alias slot>    # drop the temporary copy
```

The alias Name is READ BACK from `DataPool/Plugins` (MA3 chose it — `#2` was
observed, but it is not guessed), and the deploy reports success only after a
final pool read shows exactly one plugin under the real Name and no leftover
alias. `Rename Plugin` is not usable — 2.4.2 answers it with `Not implemented`.

**If a re-deploy fails midway, the alias is deliberately LEFT in the pool** — it
is a working copy of the new source. The failure detail names the alias and its
slot; recover by hand from there (delete the stale slot in the GUI, or import
the staged `<stem>.xml` into the intended slot). Any other plugin (a generated
patch plugin) is a foreign object to the responder, so its re-deploy keeps the
direct `Delete` + `Import` path and only falls back to the alias swap if the
console refuses that delete.

### Configuration (both options)

The `CONFIG` table at the top of the Lua file may need on-site adjustment:

| Key | Default | Meaning |
|---|---|---|
| `osc_slot` | `2` | OSC settings row used for replies — must be a row with `Send=Yes` (a receive-only row silently swallows every reply). Set via app Settings, rendered in at install (do not hand-edit) |
| `state_address` | `/copilot/state` | snapshot reply address |
| `feedback_address` | `/copilot/feedback` | result/pong reply address |
| `max_children` | `24` | snapshot child cap — no paging past it (PROTOCOL.md §4.2) |
| `max_payload` | `1900` | encoded payload byte budget (MA3 command line drops past ~2048) |
| `send_variant` | `packed` | OSC send mechanism (PROTOCOL.md §5) |

## 3. Smoke check inside the console (no server needed)

In the onPC command line:

```
Plugin "CopilotResponder"
```

Expected: a usage line in the console feedback/system monitor
(`copilot_responder v1.5.0 - no request. ...`). This verifies the plugin loads
and runs; replies are not exercised yet.

## 4. Round-trip verification from the server (AC-MVP-012 semi-automatic)

From the project root, with onPC running and OSC configured as above:

```bash
uv run python -m server.tools.responder_roundtrip \
    --host 127.0.0.1 --port 8000 --listen-port 9000 \
    --path "DataPool/Sequences" --exec-command "List" --wait 5
```

Expected output: `[PASS] ping`, `[PASS] state` (with a node/children summary),
`[PASS] exec`, `result: PASS` (exit code 0).

- The `exec` step sends the benign command `List` through the responder's
  result-capture path (`exec` wrap). Pick another harmless command with
  `--exec-command` if desired; commands containing `"` are rejected.
- `--skip-exec` runs only ping + state.
- `--expect-version "X.Y.Z"` fails the `ping` step (with a clear detail
  message) if the LIVE responder's reported version doesn't match — the
  fast, definitive "did my deploy actually take effect" check (§2.1). Run
  this FIRST after every plugin re-import, before any other live test.

## 5. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Re-imported plugin still behaves like the old version | Import over an existing same-named plugin doesn't reliably refresh its stored source (§2.1, 2026-07-24 finding). Verify with `--expect-version` after every deploy; recover via delete+reimport or Option B paste-in. |
| Requests stop arriving after an OSC config change (row destination, port, prefix) even though the settings screen looks correct | grandMA3's OSC subsystem does not auto-rebind on config change — a "stale socket". Toggle the row's `Enable Input` / `Enable Output` off then on again (a real rebind cycle, not just re-saving the same values), then retry. Recurring finding across multiple sessions (2026-07-18, 2026-07-23). |
| `[FAIL] ping: timeout` and nothing in onPC | OSC input not enabled, wrong `--port`, or prefix ≠ `copilot`. Verify with the M1 tool: `uv run python -m server.tools.osc_smoke --port 8000 --listen-port 9000 "List"` and check the onPC command-line history. |
| Command arrives in onPC history but no reply | Replies not reaching the server: wrong OSC row destination IP/send-port, wrong `CONFIG.osc_slot`, or the send API assumption (PROTOCOL.md §6 ASSUMPTION-2) — try `CONFIG.send_variant = "args"` then `"cmd_keyword"`. |
| Replies arrive at `/copilot/copilot/...` | Console prepends the OSC prefix to outgoing addresses (ASSUMPTION-5). Detect with `uv run python -m server.tools.responder_roundtrip --listen-port 9000 --wait 10 --diagnose`, then strip the leading `/copilot` from `CONFIG.state_address` / `CONFIG.feedback_address`. |
| Plugin runs but reports `no request` | Plugin arguments not delivered (ASSUMPTION-1). Use the user-variable fallback: `SetUserVariable "COPILOT_REQ" "ping 1"` then `Plugin "CopilotResponder"`. |
| `exec` reports failure for a command that clearly worked | `Cmd()` success-token mismatch (ASSUMPTION-3): note the raw `result` string in the reply and extend `SUCCESS_RESULTS` in the Lua file. |
| A second responder-looking plugin sits in the pool and you fear double replies | It cannot reply. Requests name the plugin (`Plugin "CopilotResponder" "..."`), so a copy under any other name — `CopilotResponder#2`, the name an in-console duplicate gets — is never invoked (§6, 2026-07-25 finding). Confirm rather than assume: one `ping` returns exactly one `pong`. |
| A `state` listing is short and `truncated:true`, and re-querying returns the same children | Expected — there is no paging. Enumerate slot by slot against `node.childCount` (PROTOCOL.md §4.2). |
| App reports `console_offline` forever on a NEW show even though every OSC row's IP/port/prefix is verified correct by eye | Check **Interface** at the top of `In & Out > OSC` — if it is bound to the machine's Wi-Fi/Ethernet adapter (`en0` or similar) instead of `lo0 (127.0.0.1)`, 127.0.0.1 traffic is silently dropped with no error surfaced anywhere. Verified 2026-08-12: a show with an otherwise-identical OSC table connected the instant Interface was set to `lo0`. |

Record the outcome of this live round-trip (pass or deviations found) in the
SPEC progress log — it is the semi-automatic half of AC-MVP-012.

## 6. Plugin/macro pool hygiene

Development leaves debris in the showfile: probe macros from a debugging
session, diagnostic plugins, and duplicate copies of the responder itself. The
showfile is not under version control, so nothing here is recoverable — read
this section before deleting anything.

**Verified deletion syntax** (2026-07-25, live 2.4.2):

```
Delete Macro <slot>
Delete Plugin <slot>
```

Both act immediately with no confirmation dialog. `Delete Plugin` is the same
call the deploy path already issues (`server/safety/console.py`).

**Delete from the highest slot number downwards.** Whether MA3 renumbers a pool
after a deletion is unverified; descending order is correct either way, while
ascending order would shift a not-yet-deleted target into the slot just freed.

**Never delete the responder's own slot.** It is the only channel the server
has; removing it leaves recovery only through raw `bridge.send_command` OSC.
Ping between plugin deletions and stop at the first missed `pong`.

Two shapes of debris are easy to misread:

- **A duplicate responder is inert, not dangerous.** An in-console copy is
  named `CopilotResponder#2` and is therefore never invoked (§5). Treat it as
  clutter, not as a live double-reply risk.
- **Import can leave default-named plugins.** Slots named `UserPlugin <n>`
  carrying an empty `ComponentLua 1` accumulate from interrupted imports. There
  is no verb that reads a plugin's stored source back, and the `.show` file
  does not expose it as plain text, so such a slot cannot be identified after
  the fact — delete only if you can account for it.

MA3 autosaves the showfile, but confirm a save before closing the console: an
unsaved deletion is restored on the next load.
