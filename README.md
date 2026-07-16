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

- Anthropic is pinned to `claude-opus-4-8`; the Gemini pin (`gemini-2.5-pro`)
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
