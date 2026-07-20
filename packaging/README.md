# Packaging — GrandMA3 Copilot (SPEC-COPILOT-DEPLOY-001 M6, Stage 1)

Reproducible macOS build of the frozen local-launcher app (PyInstaller onedir →
`.app`). Stage 2 (Tauri) reuses this frozen backend as a sidecar (M7+).

## Files

| File | Purpose |
|------|---------|
| `entry.py` | PyInstaller frozen entrypoint — boots `server.web.serve.main()`. |
| `GrandMA3-Copilot.spec` | PyInstaller onedir spec (deps collection + `--add-data` asset mirroring). |
| `entitlements.plist` | Hardened-runtime entitlements applied to the `.app` root. |
| `sign.sh` | Inside-out codesign pipeline (ad-hoc-capable; env-gated notarization). |
| `build.sh` | Orchestration: UI build check → PyInstaller → sign. |

## Build (arm64 host)

```bash
# Prereqs (once): a .venv with the app deps + PyInstaller.
uv pip install --python .venv/bin/python pyinstaller

# One-shot build + ad-hoc sign:
./packaging/build.sh
# -> dist/GrandMA3 Copilot.app   (+ dist/GrandMA3 Copilot/ onedir tree)

# Or the two steps manually:
.venv/bin/python -m PyInstaller --noconfirm --clean packaging/GrandMA3-Copilot.spec
bash packaging/sign.sh "dist/GrandMA3 Copilot.app"
```

`ui/dist` must exist (bundled UI); `build.sh` runs `npm --prefix ui run build` if missing.

## Frozen verification

```bash
APP="dist/GrandMA3 Copilot.app"
BIN="$APP/Contents/MacOS/GrandMA3 Copilot"

# Keyring backend + roundtrip, INSIDE the frozen bundle (FEAS-2 / research §B.4):
"$BIN" --self-check          # -> exit 0, "self-check OK: macOS keyring backend + roundtrip verified"

# Launch smoke (headless) + graceful shutdown:
"$BIN" --no-browser --port 8799 --receive-port 9099    # Ctrl-C / SIGTERM -> clean exit, ports freed

# Codesign structure (ad-hoc):
codesign --verify --deep --strict "$APP"
codesign -d --entitlements - "$APP"   # shows the 3 cs.* entitlements
```

## Entitlements rationale (research §C.2 — exactly three keys)

A bundled-CPython PyInstaller app needs exactly these to pass notarization:

- `com.apple.security.cs.allow-jit` — arm64 W^X: executable pages need `MAP_JIT` + this entitlement.
- `com.apple.security.cs.allow-unsigned-executable-memory` — CPython / C-extensions create unsigned executable memory (otherwise `MemoryError` importing certain C-extensions).
- `com.apple.security.cs.disable-library-validation` — load libs/plugins not signed under the app's Team ID.

The plist is intentionally comment-free: AMFI's entitlements parser rejects XML comments.

## Signing — ad-hoc now, Developer ID later (NO code change)

`sign.sh` signs **inside-out** (nested Mach-O first, `.app` root LAST with
`--entitlements`; never `--deep` on the sign side — Apple DTS thread 701514) and
is env-driven so it flips to a real identity + notarization with no edit:

```bash
# ad-hoc dry run (default — runs here with no certificate):
bash packaging/sign.sh "dist/GrandMA3 Copilot.app"

# real Developer ID + notarization (when a cert exists):
SIGN_IDENTITY='Developer ID Application: NAME (TEAMID)' \
  DEVELOPER_ID=TEAMID NOTARY_PROFILE=my-notary-profile \
  bash packaging/sign.sh "dist/GrandMA3 Copilot.app"
```

`xcrun notarytool submit --wait` + `xcrun stapler staple` + `spctl --assess` are
gated behind a non-empty `DEVELOPER_ID`, so AC-DEPLOY-009/010 are **environment-
gated N/A** on a cert-less host (research §C.5) and activate with no code change.

## Environment-gated boundaries (this host)

- **universal2** (research §C.6): the build interpreter is arm64-only CPython, so
  the output is a single-arch arm64 `.app`. On a universal2 build env (universal2
  Python + universal2 wheels for `_pydantic_core` / `jiter`) set
  `PYI_TARGET_ARCH=universal2` — no spec edit.
- **Developer-ID signing / notarization**: no certificate on this host → ad-hoc
  dry verification only; real signing is env-gated as above.
- **Windows Authenticode** (AC-DEPLOY-010): built + signed on Windows; N/A here.

## Bundled assets (`--add-data`, research §A.5)

`ui/dist`, `console/lua`, `server/rulebook/assets`, `config/provider.toml`, and
`server/safety/blacklist.yaml` are mirrored into the bundle so
`server.resources.resource_base()` (`sys._MEIPASS`) and the `__file__`-relative
safety-ruleset loader resolve them in the frozen app.
