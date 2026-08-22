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

The closed sets (blacklist, invoking verbs and their bare object forms) live
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

## Irreversible-write guard — Position presets (PRESETGUARD)

A **separate** layer from the safety gate above: the gate classifies command
risk, but `Store Preset 2.n` is a perfectly ordinary command that silently
overwrites whatever occupies the slot. There is no undo, no restore path, and
`Delete` is blacklisted — **an overwritten preset is gone.** So the guard lives
in the session layer ([`server/web/session.py`](server/web/session.py)), not in
`server/safety/`, and it closes three holes:

1. **Occupancy is checked regardless of how the start number arrived.** The
   check used to run only when the operator left the number to the system;
   naming a number explicitly (`"21번부터"`) skipped it entirely — the most
   confident operator was the least protected. The guard now sits outside that
   branch, so the explicit-number path and the free-text answer path are
   checked alike, and a collision asks **which numbered slots would be lost**.
2. **The pool is read back after storing.** The store loop used to fire
   `run_commands` and report "저장 요청했습니다". It now re-reads the pool once
   and reports arithmetic (landed / missing slot numbers) instead of an
   adjective. A withheld-by-approval slot is classified `proposal`, not a
   defect — otherwise the report cries wolf on every gated run.
3. **Regeneration updates presets in place.** *"지금 배치로 다시 잡아줘"* now
   rewrites an existing range, so every cue referencing those presets is
   re-aimed. Previously no handler existed and such a phrase fell through to
   the store path — the operator believed the presets were refreshed while a
   new range was written instead.

Two rules hold the design together. **One confirmation card, two callers** —
first-time store and regeneration share the same decision logic, so one path
cannot drift out of fail-closed. And **unknown ≠ empty** — when the pool cannot
be read, that is never reported as "checked, and it was empty"; a store
proceeds with an explicit notice while a regeneration refuses outright, since
regeneration presupposes the range exists.

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


## Vectorworks auto-patch (VWX + AUTOPATCH)

Upload a Vectorworks Instrument Data export (`.csv`, `.txt`, `.xlsx`) or an MVR
file (`.mvr`) through the chat UI and the copilot will:

1. **Read the design** — parse columns, resolve addresses (3-way cross-check),
   build a designed-rig model.
2. **Diff against the live console** — report missing fixtures, address
   collisions, and quantity mismatches.
3. **Plan the patch** — assign fixture IDs (within a range you confirm),
   resolve fixture types against the console's library, generate an
   `AddFixtures` Lua script, and plan DMX addresses from the drawing.
4. **Hand off for execution** — the generated Lua is shown for review; **you
   run it from the console** (Patch editor must be open). The server never
   executes the patch itself.
5. **Verify** — after you execute, the server re-reads the console and
   confirms what was actually created. Already-patched fixtures are
   automatically excluded (idempotent).

The upload, diff report, and patch plan all stay within your WebSocket session
— the model never asks you to paste base64 or a report back into chat.

When information is missing (ambiguous fixture types, unnamed fixtures, empty
FID range), the copilot asks through a question card instead of guessing.

**Why not fully automatic?** MA3's `AddFixtures` requires the Patch editor to
be open and a human to trigger execution — server-only automation was tested
across 10 execution paths and produced zero fixtures in every case (measured
live, AUTOPATCH-001 M0). The semi-automatic model matches the original request:
*"if auto-patch fails, ask the user for manual steps."*

Implementation: `server/vwx/` (7 modules) + `server/orchestrator/tools.py`
(`vectorworks_autopatch` tool). Specifications:
[SPEC-COPILOT-VWX-001](.moai/specs/SPEC-COPILOT-VWX-001/spec.md),
[SPEC-COPILOT-AUTOPATCH-001](.moai/specs/SPEC-COPILOT-AUTOPATCH-001/spec.md).

## LX-SEQ patch import (LXSEQ — stage 1 of 4)

A lighting designer's LX-SEQ RIG pack ships a **patch CSV** with nine columns
(`FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position`). The
`import_lxseq_patch` tool reads one such file and patches the console with it.
Stage 1 covers **patch only**; groups, presets/FX, and sequences/cues are
follow-up specifications.

1. **Parse** — columns are found by name, not by position (scrambled headers
   and a BOM are absorbed). Rejected rows are reported by kind:
   `non_integer_field`, `universe_overflow`, `address_out_of_range`,
   `addr_range_mismatch`, `duplicate_fid`, `address_overlap_in_file`. A duplicate
   or an overlap rejects **every** row involved, not just the later one.
   A row with `Ch` = 0 is **not** a rejection — a fixture that occupies no DMX
   (a manually operated one, say) is counted separately as an *excluded* row
   (`zero_channels`).
   **A FID is not an address** — it never takes part in address arithmetic.
2. **Map** — fixture type names are **never guessed**; they are resolved
   through `resolve_fixture_type` (once per distinct type). The mode is
   settled by the **width measured on the console**, falling back to a label
   token when widths tie. A type whose mode cannot be settled is not patched:
   its rows are skipped as `mode_unresolved` and handed back so you can
   re-run with `mode_overrides`.
3. **Check occupancy** — occupied addresses (`address_occupied`), rows already
   patched with the same type at the same start (`already_patched`), and taken
   fixture IDs (`fid_occupied`) are all skipped. **Nothing is ever
   overwritten**, so re-running the same file plans zero runs.
4. **Plan runs** — rows are grouped into runs by type, mode, universe, `Group`,
   and address continuity. The reference 86-fixture rig plans **12 runs** in the
   default `group` naming mode and 9 runs in `type` mode.
5. **Execute** — `action='preview'` (the default) writes **nothing** to the
   console. `action='apply'` hands each run to `patch_fixtures`, which owns the
   Lua generation, the deployment gate, and the read-back. Success is only ever
   read from that tool's re-query. If a run does not come back `created`, the
   import **stops there** and reports the rest as `not_attempted` — there is no
   automatic retry, because a retry on a partial write creates duplicates.

**Bytes come from a file, never from chat.** `file_content_base64` must be the
base64 of the file's bytes. Pasted CSV text silently loses newlines and
whitespace, which patches the wrong slots — and this app has no undo. The
payload carries the received bytes' sha256 and length so you can compare
against the original. Today a local harness fills the argument
(`uv run python -m server.tools.lxseq_e2e --csv <path> --action preview`); a UI
file picker will fill it later.

Live status: verified on grandMA3 onPC 2.4.2 with the reference rig — 12 runs,
86 fixtures created, confirmed by a re-query independent of the tool.

The handle/name gap is now closed **offline**. On a real console
`occupant.fixture_type` returns a handle string (`FixtureType <slot>`) rather
than a name, so a re-run used to report `fid_occupied` where `already_patched`
was meant; the read boundary now translates slot-to-name before the comparison.
**This has not been re-verified on a console** — the fix is covered by offline
tests only, and the handle format itself is an assumption drawn from live reads
of one rig. Writes stayed at zero either way, before and after; only the label
was wrong.

Two consumers of the same value are still **untranslated**, because they read
the inventory without supplying the slot-to-name table: the Vectorworks diff
counts fixtures by type string, so a handle matches no designed type and every
type reports a console count of zero even when the rig is patched; and the
printed patch sheet prints the handle verbatim in the fixture-type column.

Implementation: `server/lxseq/` (parser + mapper) + `server/orchestrator/tools.py`
(`import_lxseq_patch` tool). Specification:
[SPEC-COPILOT-LXSEQ-001](.moai/specs/SPEC-COPILOT-LXSEQ-001/spec.md).

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

## Native desktop shell — build & run (SPEC-COPILOT-DEPLOY-001 Stage 2, M7)

A Tauri v2 native shell (`src-tauri/`) wraps the Stage-1 PyInstaller onedir
backend as a **sidecar** — same `ui/dist` UI, a system tray + connection-status
badge, and no separate terminal/venv required. M7 (shell scaffold + sidecar
lifecycle + `/ws` handshake + cross-language safety scan) is done;
auto-update (M8) and code signing/notarization (M9) remain Stage-2-deferred.

### Build

```bash
# Prereqs (once): Tauri CLI (devDependency) + a Rust toolchain (cargo/rustc).
npm install

# One-shot: stage the PyInstaller sidecar, build the Tauri bundle, then
# re-stage the sidecar binary into the built .app (macOS arm64, this host):
npm run shell:build
# -> src-tauri/target/release/bundle/macos/GrandMA3 Copilot.app
```

`npm run shell:stage` (staging only) and `npm run shell:dev` (dev-mode
`tauri dev` against the staged sidecar) are also available; see
`packaging/stage_sidecar.py` for the staging logic shared by both paths.

### Run

```bash
open "src-tauri/target/release/bundle/macos/GrandMA3 Copilot.app"
```

The native window loads the same `ui/dist` as the Stage-1 browser mode; a
per-launch token is injected via Tauri IPC (never written to disk) and the
`/ws` handshake rejects any disallowed Origin or missing/incorrect token.
Sidecar teardown is Rust-authoritative process-group kill on normal quit, with
a backend parent-liveness watchdog as the self-reap fallback on force-quit.

### Environment-gated boundaries (this host)

- **Windows Job Object** (`KILL_ON_JOB_CLOSE`) teardown path: needs a Windows
  build host; N/A here (Unix setsid/setpgid path is what's exercised).
- **universal2 shell build** / **real notarization**: same caveats as the
  Stage-1 packaged app above — no code change required once the build
  environment / certificate is available.
