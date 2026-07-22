# CopilotResponder — grandMA3 onPC install & verification (M2)

Console-side Lua 5.4 responder plugin for SPEC-COPILOT-MVP-001. Provides
object-tree state snapshots (REQ-MVP-003) and command execution result capture
(REQ-MVP-004) over the `/copilot/*` OSC namespace. Wire format:
[PROTOCOL.md](PROTOCOL.md).

Target: **grandMA3 onPC 2.4.2** (macOS build; any onPC platform works — the
responder follows onPC's supported platform range per REQ-MVP-043).

## 1. Configure OSC in onPC

In grandMA3: `Menu → Settings → ... → OSC` (the OSC settings table):

1. Add (or reuse) an OSC configuration row. Note its **row index** — the
   responder's `CONFIG.osc_slot` (default `1`) must match it. Set it in the
   app's Settings ("OSC 응답 행") rather than by hand: the app renders that
   value into the Lua as it installs, so a re-install keeps it. A hand-edit of
   the installed file is reverted the next time you install.
   The row's destination must actually reach the app — a row pointing at a
   broadcast address (e.g. `192.168.0.255`) never arrives at `127.0.0.1`, and
   the only symptom is a console that appears offline while its own command
   history shows the requests arriving.
2. **Destination IP**: the machine running the copilot server (`127.0.0.1`
   when server and onPC share the host).
3. **Port (send)**: the server's listen port (default `9000` — the
   `--listen-port` of the server tools).
4. **Port (receive)**: the console's OSC input port (default `8000` — the
   `--port` of the server tools).
5. **Prefix**: `copilot` — so incoming `/copilot/cmd` command lines execute.
6. Enable the row and its command input/output flags (`CMD` / enabled toggles
   as exposed by the 2.4.2 settings UI).

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

### Configuration (both options)

The `CONFIG` table at the top of the Lua file may need on-site adjustment:

| Key | Default | Meaning |
|---|---|---|
| `osc_slot` | `1` | OSC settings row used for replies — set via app Settings, rendered in at install (do not hand-edit) |
| `state_address` | `/copilot/state` | snapshot reply address |
| `feedback_address` | `/copilot/feedback` | result/pong reply address |
| `max_children` | `24` | snapshot child cap |
| `max_payload` | `4000` | encoded payload byte budget |
| `send_variant` | `packed` | OSC send mechanism (PROTOCOL.md §5) |

## 3. Smoke check inside the console (no server needed)

In the onPC command line:

```
Plugin "CopilotResponder"
```

Expected: a usage line in the console feedback/system monitor
(`copilot_responder v1.0.0 - no request. ...`). This verifies the plugin loads
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

## 5. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `[FAIL] ping: timeout` and nothing in onPC | OSC input not enabled, wrong `--port`, or prefix ≠ `copilot`. Verify with the M1 tool: `uv run python -m server.tools.osc_smoke --port 8000 --listen-port 9000 "List"` and check the onPC command-line history. |
| Command arrives in onPC history but no reply | Replies not reaching the server: wrong OSC row destination IP/send-port, wrong `CONFIG.osc_slot`, or the send API assumption (PROTOCOL.md §6 ASSUMPTION-2) — try `CONFIG.send_variant = "args"` then `"cmd_keyword"`. |
| Replies arrive at `/copilot/copilot/...` | Console prepends the OSC prefix to outgoing addresses (ASSUMPTION-5). Detect with `uv run python -m server.tools.responder_roundtrip --listen-port 9000 --wait 10 --diagnose`, then strip the leading `/copilot` from `CONFIG.state_address` / `CONFIG.feedback_address`. |
| Plugin runs but reports `no request` | Plugin arguments not delivered (ASSUMPTION-1). Use the user-variable fallback: `SetUserVariable "COPILOT_REQ" "ping 1"` then `Plugin "CopilotResponder"`. |
| `exec` reports failure for a command that clearly worked | `Cmd()` success-token mismatch (ASSUMPTION-3): note the raw `result` string in the reply and extend `SUCCESS_RESULTS` in the Lua file. |

Record the outcome of this live round-trip (pass or deviations found) in the
SPEC progress log — it is the semi-automatic half of AC-MVP-012.
