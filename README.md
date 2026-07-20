# AI-Lighting_Console — grandMA3 AI Copilot

Phase 1 MVP (SPEC-COPILOT-MVP-001): Korean natural-language lighting instructions are
translated into grandMA3 command lines and executed over OSC, behind a 3-stage safety gate.

Target console: grandMA3 onPC 2.4.2 (MA3 v2.x). Server: Python 3.11+.

## Server install (cross-platform, reproducible)

Requires [uv](https://docs.astral.sh/uv/). Python 3.11 is provisioned automatically
(pinned via `.python-version`); dependencies are version-pinned in `uv.lock`.

```bash
uv sync                                   # install pinned dependencies
uv run pytest                             # run the test suite
uv run pytest --cov=server.bridge         # with coverage
```

## Manual OSC smoke test against onPC

Enable OSC input in grandMA3 onPC and set its UDP input port to match `--port`.
Then send a harmless command line and listen for `/copilot/feedback`:

```bash
uv run python -m server.tools.osc_smoke --host 127.0.0.1 --port 8000 --listen-port 9000 "List"
```

Note: with a bare onPC (no console-side Lua responder installed) no OSC feedback
will arrive — verify command arrival in the onPC command line history instead.

## Console-side Lua responder (M2)

The grandMA3-resident responder plugin lives in [`console/lua/`](console/lua/):
state snapshots on `/copilot/state`, execution results on `/copilot/feedback`
(wire format: [`console/lua/PROTOCOL.md`](console/lua/PROTOCOL.md)). Install and
onPC 2.4.2 OSC setup: [`console/lua/README.md`](console/lua/README.md). Verify the
full loop with:

```bash
uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9000
```

## LLM provider configuration (M3)

The tool-runner server speaks to exactly ONE active LLM provider behind a
provider-neutral abstraction (Anthropic Claude or Google Gemini). Selection and
model pins live in [`config/provider.toml`](config/provider.toml):

```toml
[provider]
active = "anthropic"        # or "gemini" — switching is this one value, no code change
```

- Anthropic is pinned to `claude-opus-4-8`; the Gemini pin (`gemini-3.5-flash`)
  is config-changeable.
- **API keys are environment variables only** — never put credentials in the
  config file (the loader rejects them): `ANTHROPIC_API_KEY` for Anthropic,
  `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) for Gemini.
- The MA3 grammar rulebook (fixed system-prompt prefix, incl. the Korean
  field-lighting term dictionary) lives in `server/rulebook/assets/v2.4.2/`.

With a key present, verify the active provider with one live call (run twice to
observe a warm cache read):

```bash
uv run python -m server.tools.provider_smoke
```

## Safety gate (M4)

Every command bound for the console passes the 3-stage safety gate in
[`server/safety/`](server/safety/) — the SINGLE chokepoint (an architecture
test enforces that no other production module can reach the OSC send surface):

1. **Grammar validator** — structural parse; rejected lines feed the
   self-correction loop.
2. **Risk classification** — the closed blacklist + indirect-invocation
   expand-or-hold (recursion cap 3, cycle detection) + destructive-plugin
   flags + unspecified-target detection.
3. **Human approval** — risky commands are HELD until an explicit approval;
   one rejection voids the whole bundle (all-or-nothing). Without an approval
   channel the default is deny-all.

The closed sets (blacklist 6 entries, invoking verbs 10 + 2 bare forms) live
in ONE version-controlled file: [`server/safety/blacklist.yaml`](server/safety/blacklist.yaml).
Changing a set requires a file revision with a version bump — tests iterate
the file's content, so revisions auto-extend the FN corpora.

Also part of the gate: **live lock** (read-only proposal cards, lock wins over
pending approvals), **showfile backups** (session start + periodic 10 min +
immediately before approved risky commands; backup failure blocks execution),
**failure modes** (console-offline / responder-degraded / per-command
"execution unconfirmed" with no auto-resend), and the **audit log**
(append-only JSONL under `server/audit_logs/`, daily rotation, 90-day
retention — every console send reconciles 1:1 with an audit record).

## Korean chat UI (M5)

The chat surface is a FastAPI WebSocket server ([`server/web/`](server/web/))
plus a React client ([`ui/`](ui/)). Wire contract:
[`server/web/PROTOCOL.md`](server/web/PROTOCOL.md) (protocol v1). Everything
console-bound still goes through the M4 gate — the web layer never touches the
OSC surface (architecture-tested).

### Run the server

```bash
uv sync
export ANTHROPIC_API_KEY=...      # or GEMINI_API_KEY per config/provider.toml
uv run python -m server.web       # ws://127.0.0.1:8765/ws (+ /healthz)
```

Useful flags: `--port`, `--console-host/--console-port` (onPC OSC input,
default 127.0.0.1:8000), `--receive-port` (feedback listen, default 9000),
`--no-session-backup` (skip the boot-time showfile backup attempt when no
console is connected). `python -m server.web --help` lists everything.
Without a running console the UI shows **콘솔 오프라인** and the gate blocks
new executions (fail-safe) — the server itself boots fine.

### Build / run the chat UI

Requires Node.js 22+ and npm (versions pinned in `ui/package.json` +
`ui/package-lock.json`):

```bash
cd ui
npm install
npm run build        # tsc + vite -> ui/dist (served by the server at /)
npm test             # vitest — protocol/reducer unit tests
npm run dev          # dev server on :5173, proxies /ws to :8765
```

After `npm run build`, open `http://127.0.0.1:8765/` — the server serves
`ui/dist` automatically. The UI provides the Korean chat, approval/reject
cards (command + risk reasons + warnings), the live-lock toggle, console
status banners, and proposal cards; raw LLM SDK errors never reach the chat
surface (Korean messages only — details go to the audit/diagnostic log,
REQ-MVP-044).

## Lua plugin deployment gate (M7)

`deploy_plugin` is live: a model-generated Lua plugin deploys ONLY when **both**
the pcall compile check **and** the human review gate pass (REQ-MVP-019 —
deny-by-default; without a connected review UI nothing ever deploys).

Pipeline ([`server/deploy/`](server/deploy/)):

1. **Compile harness** — the source is compiled (never executed) in an embedded
   Lua 5.4 runtime (`lupa`, now a runtime dependency). A compile failure goes
   back to the model as a structured error and counts toward the same ≤3
   self-correction retry cap as command failures.
2. **Destructive scan** — every `Cmd()` string literal is classified against
   the same closed-set SSOT the gate uses (`server/safety/blacklist.yaml`,
   abbreviation-aware). The scan is **best-effort reviewer assistance**:
   dynamically assembled strings (`Cmd("Delete " .. x)`, `string.format`, …)
   are surfaced as unverifiable-call warnings, and the **human review stays
   the authoritative control** (REQ-MVP-027).
3. **Human review** — the UI shows a review card: plugin name, compile
   verdict, scan findings (blacklisted lines highlighted), dynamic-assembly
   notes, bounded source preview, approve/reject. Disconnect/timeout = deny.
4. **Gate-owned deploy send** — the deployment rides the safety gate
   (audited 1:1, blocked under live lock / console-offline) to the responder's
   new `deploy` verb (`console/lua/PROTOCOL.md` §2, responder 1.1.0 — the
   console re-compiles the source before touching the plugin pool;
   plugin-object creation is ASSUMPTION-6, onPC-unverified).
5. **Flag registration** — on approval the plugin is registered in the M4
   flag registry; a destructive-scanned plugin then requires human approval
   on **every** invocation (REQ-MVP-028 — the M4 invocation gate enforces it
   with no extra wiring).

## Packaged app — build & run (SPEC-COPILOT-DEPLOY-001 Stage 1, M6)

A self-contained PyInstaller **onedir** build lets an operator run the app
without a terminal or a venv. Stage 1 targets **macOS arm64** on this build
host; see the caveats below for the other targets. Full details:
[`packaging/README.md`](packaging/README.md).

### Build

```bash
# Prereqs (once): PyInstaller in the project venv.
uv pip install --python .venv/bin/python pyinstaller

# One-shot build + ad-hoc sign (builds ui/dist first if missing):
./packaging/build.sh
# -> dist/GrandMA3 Copilot.app   (+ dist/GrandMA3 Copilot/ onedir tree)
```

### Run

```bash
open "dist/GrandMA3 Copilot.app"                      # double-click equivalent
# or, from the bundle's executable directly:
"dist/GrandMA3 Copilot.app/Contents/MacOS/GrandMA3 Copilot" --no-browser
"dist/GrandMA3 Copilot.app/Contents/MacOS/GrandMA3 Copilot" --self-check
```

`--no-browser` skips opening the default browser to the local UI URL;
`--self-check` verifies the frozen bundle's OS-keyring backend + roundtrip
without booting the server. Without a running onPC, the UI shows **콘솔
오프라인** and the safety gate blocks new executions (fail-safe) — the app
itself still boots and serves the settings UI.

### Environment-gated boundaries (this host)

- **universal2** (arm64+x86_64): this build host's CPython is arm64-only, so
  the output is single-arch arm64. A universal2 build environment (universal2
  CPython + universal2 `_pydantic_core`/`jiter` wheels) activates it via
  `PYI_TARGET_ARCH=universal2` — no code/spec change.
- **Windows x86_64**: built + signed on a Windows host; N/A here.
- **Developer-ID signing / notarization**: no certificate on this host — the
  signing pipeline runs ad-hoc (`sign.sh`); a real `SIGN_IDENTITY` +
  `DEVELOPER_ID` env activates real signing/notarization with no code change.

Stage 2 (Tauri v2 native shell + Python-backend sidecar + auto-update) is
deferred to a separate kickoff — SPEC-COPILOT-DEPLOY-001 remains
`status: in-progress` until Stage 2 lands.
