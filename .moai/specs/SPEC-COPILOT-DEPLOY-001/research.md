# SPEC-COPILOT-DEPLOY-001 — research (D3 de-risk)

> Minimal `research.md (D3)` required by plan.md §A.0 **before** M6 implementation. Focused de-risk of the highest-uncertainty packaging area (FEAS-8), not an exhaustive study.
> Consumed by **M6** (plan.md §A.7 / §C M6 row): PyInstaller onedir bundle spec, frozen keyring backend collection, macOS hardened-runtime signing pipeline.
> Scope: Stage-1 packaging only (onedir → notarizable `.app`/`.dmg`). Findings verified against the live `.venv` (CPython 3.11.15, arm64) and repo source; cited URLs were fetched this session (see Sources).

---

## §A — PyInstaller onedir native-dependency packaging

Stage-1 mode is **onedir** (decided, both platforms — plan.md §A.7 F8). The five backend deps split into two packaging classes for a PyInstaller 6 build.

### A.1 Class 1 — plugin / dynamic-string-import (NOT found by static analysis)

- **keyring** → `--collect-all keyring`. Backends load via the `keyring.backends` entry point + distribution metadata, invisible to static analysis. PyInstaller's own hooks doc names `keyring` (and `pytest`) as the `collect_entry_point` case. Detail in §B. *(FEAS-2 mandate — correct.)*
- **uvicorn** → `--collect-submodules uvicorn`. `uvicorn/config.py` resolves loop/protocol/lifespan backends from `auto` strings at runtime via `import_from_string` — verified in the installed uvicorn 0.51.0: `HTTP_PROTOCOLS["auto"]=uvicorn.protocols.http.auto:AutoHTTPProtocol`, `WS_PROTOCOLS["auto"]=uvicorn.protocols.websockets.auto:AutoWebSocketsProtocol`, `LIFESPAN["auto"]=uvicorn.lifespan.on:LifespanOn`, `LOOP_FACTORIES["auto"]=uvicorn.loops.auto:auto_loop_factory`. PyInstaller cannot follow these string imports, so the submodules drop by default. `--collect-submodules uvicorn` grabs the tree; the collected `auto` modules then statically import the concrete backends (h11/httptools, websockets/wsproto) which PyInstaller follows. The app's WebSocket approval channel genuinely needs the ws protocol submodule.

### A.2 Class 2 — httpx/pydantic REST clients (statically analyzable, need namespace collection)

- **google-genai** → `--collect-all google.genai`. Installs as the `google.genai` **PEP-420 namespace** package (no `google/__init__.py`); a plain `--hidden-import google.genai` risks missing namespace siblings. REST/httpx transport only.
- **anthropic** → `--collect-all anthropic` (submodules + any bundled data).
- **No `--copy-metadata` for either SDK.** A prior draft justified `--copy-metadata google-genai` / `--copy-metadata anthropic` by claiming both SDKs read their version via `importlib.metadata` and raise `PackageNotFoundError` on a missing dist-info. **This is false as installed** — anthropic 0.116.0 has zero `importlib.metadata` usage (User-Agent built from a hardcoded `__version__` in `anthropic/_version.py`), and google-genai 2.12.0's primary `library_label` header also uses a hardcoded `__version__` in `google/genai/version.py` (its only `importlib.metadata` reads are on the MCP path and are wrapped in `try/except PackageNotFoundError`). Neither raises on a normal request. Moreover `--collect-all X` **already runs `copy_metadata(X)` internally**, so a separate `--copy-metadata` is redundant even if metadata were needed.
- **fastapi / starlette / pydantic / httpx / certifi** → no special flag. Statically analyzable; the pydantic native ext (`_pydantic_core.cpython-311-darwin.so`, leading underscore) and the certifi CA bundle are handled by PyInstaller's bundled contrib hooks. Add `--collect-submodules pydantic` only if a hidden pydantic plugin later surfaces.

### A.3 grpc is NOT needed (document the future-grpc caveat)

Confirmed two ways: (a) no `grpc`/`grpcio` in the `.venv` (a native-ext scan found only `_pydantic_core` and `jiter` `.so`); (b) the installed google-genai 2.12.0 is REST/httpx-only. `--exclude-module grpc` is optional — since grpcio is absent there is nothing to strip, so it only suppresses missing-import warnings for any conditional `import grpc` (no bundle-size benefit). **Caveat:** re-enabling a Vertex/gRPC transport later reintroduces grpcio compiled C-extensions + dynamic imports (needs `--collect-all grpc` + `grpc._cython` binaries), materially changing bundle size and the universal2 story — a `.spec` rework, not a runtime toggle.

### A.4 Runtime resource resolution — sys._MEIPASS (load-bearing)

A frozen build sets `sys.frozen=True` and `sys._MEIPASS`; per the PyInstaller runtime docs, in **onedir** `_MEIPASS` is the `_internal` folder inside the app tree, in **onefile** it is a temp extraction dir — **both** set `_MEIPASS`, so one resolver covers both (onefile stays forward-compatible even though Stage 1 is onedir):

```python
import sys
from pathlib import Path

def resource_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)          # onedir: <app>/_internal ; onefile: temp dir
    return Path(__file__).resolve().parents[2]   # dev project root
```

**Two call sites GENUINELY break in a bundle** (they climb to the dev project root, which is absent from the bundle) and MUST route through `resource_base()` before M6 — this is a code change, not a `.spec` change:

| File:line | Current | Bundle behavior |
|---|---|---|
| `server/web/serve.py:29` | `DEFAULT_UI_DIST = Path(__file__).resolve().parents[2] / "ui" / "dist"` | `parents[2]` = dev project root → not in bundle → **breaks** |
| `server/llm/config.py:22` | `DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "provider.toml"` | same `parents[2]` climb → **breaks** |

A **third** site — `server/rulebook/assembly.py:25` `_ASSETS_DIR = Path(__file__).parent / "assets"` — is **lower severity**: because `--add-data server/rulebook/assets:server/rulebook/assets` mirrors the tree, the frozen module's `__file__` (which PyInstaller 6 places under `_internal`) string-resolves to `<_internal>/server/rulebook/assets`, which **exists**. Routing it through `resource_base()` is recommended for robustness/consistency, but it is not categorically broken the way the two `parents[2]` sites are.

### A.5 `--add-data` bundle layout (colon `SRC:DEST` on macOS)

```
--add-data ui/dist:ui/dist
--add-data console/lua:console/lua
--add-data server/rulebook/assets:server/rulebook/assets
--add-data config/provider.toml:config
```

Assets then resolve to `resource_base()/"ui"/"dist"`, `.../"console"/"lua"`, `.../"server"/"rulebook"/"assets"`, `.../"config"/"provider.toml"`.

---

## §B — Frozen keyring backend discovery (FEAS-2)

### B.1 Root cause

keyring enumerates backends at runtime via `importlib.metadata.entry_points(group="keyring.backends")`, reading each distribution's `entry_points.txt` and then dynamically importing the named backend module — **neither** visible to PyInstaller's static analyzer. The PyInstaller hooks doc states verbatim: *"PyInstaller does not collect these metadata files by default."* With no metadata and no imported submodule, the query returns nothing and `get_keyring()` silently falls back to `keyring.backends.fail.Keyring` (priority 0, which raises only on first use) — or worse, to a `keyrings.alt` **plaintext/obfuscated file backend** if that package leaked into the venv. keyring issue #399 confirms this exact failure under PyInstaller (error: *"No recommended backend was available…"*) and the `PYTHON_KEYRING_BACKEND` env workaround.

Live-venv confirmation: keyring 25.7.0, active backend `keyring.backends.macOS.Keyring` (priority 5). The macOS module was renamed `keyring.backends.OS_X` → `keyring.backends.macOS` in keyring v22.0.0 — issue #399 shows the **old** `OS_X` name; pin `keyring.backends.macOS` and verify the installed version (do NOT hardcode `OS_X`, which errors on keyring ≥ 22).

### B.2 The fix (belt-and-suspenders — `--collect-all keyring` alone is not sufficient)

```
--collect-all keyring
--hidden-import keyring.backends.macOS
--hidden-import keyring.backends.fail
--hidden-import keyring.backends.null
--hidden-import keyring.backends.chainer
--exclude-module keyrings.alt
--exclude-module keyrings.cryptfile
```

`--collect-all keyring` restores the `entry_points.txt` metadata + backend submodules (and already runs `copy_metadata` internally — a separate `--copy-metadata keyring` is redundant). The explicit backend `--hidden-import`s are intentional redundancy because the bundled keyring hook is historically flaky. **`--exclude-module keyrings.alt` / `keyrings.cryptfile` is REQ-DEPLOY-006a-critical**: it guarantees no plaintext/encrypted-file fallback backend can ever be discovered even if one leaked into the build venv. (Also audit the build venv: `pip list | grep keyrings` should be empty, so the exclude is provably redundant, not load-bearing.)

### B.3 Force explicit error, no silent fallback (REQ-DEPLOY-006 / 006a)

Two fail-closed layers, both wired at process start **before** the first keyring import triggers backend selection:

```python
# 1. Env pin — load the exact backend or fail at load rather than degrade silently
os.environ.setdefault("PYTHON_KEYRING_BACKEND", "keyring.backends.macOS.Keyring")

# 2. Startup integrity guard — refuse to boot on the wrong backend
import keyring
kr = keyring.get_keyring()
if type(kr).__module__ != "keyring.backends.macOS":
    raise RuntimeError(
        "OS credential store unavailable — refusing to start "
        "(REQ-DEPLOY-006a: no plaintext fallback)"
    )
```

Discriminate on **`__module__` only**. Do **not** gate on the class name (`type(kr).__name__`): the correct macOS backend class is literally named `Keyring` — so are `fail.Keyring` and `SecretService.Keyring` — so a `__name__` check both rejects the right backend and cannot distinguish backends at all. keyring docs confirm the three override mechanisms (`PYTHON_KEYRING_BACKEND` env, `keyringrc.cfg` `default-keyring`, and `set_keyring()`); the env pin is the most deterministic and is the primary path (also sidesteps a `ChainerBackend` ambiguity).

### B.4 In-frozen roundtrip verification (AC-DEPLOY-004 / 016 gate)

Run **inside the packaged binary** (`subprocess dist/<app>/<app> --self-check`), NOT a dev-venv pytest — the dev venv has real metadata and passes even when the bundle is broken (the exact FEAS-2 false-negative). Assert the backend **type before** the roundtrip — the type gate is the real defense, because a leaked `keyrings.alt` file backend would pass a naive roundtrip while writing plaintext:

1. `import keyring; kr = keyring.get_keyring()`
2. `assert type(kr).__module__ == "keyring.backends.macOS"`  ← rejects `fail`, any `keyrings.alt.*`, bare chainer
3. `keyring.set_password("grandma3-copilot-selfcheck", "probe", "sentinel-v1")`
4. `assert keyring.get_password("grandma3-copilot-selfcheck", "probe") == "sentinel-v1"`
5. `keyring.delete_password("grandma3-copilot-selfcheck", "probe")`
6. `assert keyring.get_password("grandma3-copilot-selfcheck", "probe") is None`

Run this from inside the actual signed `.app` container (not only the raw onedir tree) — Keychain ACL behavior differs under a hardened-runtime signature (see §E).

---

## §C — macOS hardened-runtime notarization (FEAS-3)

### C.1 Sequence

`codesign` (hardened runtime + entitlements, **inside-out**) → `xcrun notarytool submit --wait` → `xcrun stapler staple` → verify (`spctl --assess --type execute` + `codesign --verify --deep --strict`). Deliver the onedir tree inside a container: onedir → `.app` (with `Info.plist`) → `.dmg` (or `ditto -c -k --keepParent` zip for submission). A **bare Mach-O cannot be stapled** — the ticket needs a `.app`/`.dmg`/`.pkg`. Sign the `.dmg` too; submit and staple the `.dmg`.

### C.2 Entitlements plist — exactly three keys

```xml
<key>com.apple.security.cs.allow-jit</key><true/>
<key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
<key>com.apple.security.cs.disable-library-validation</key><true/>
```

Ship all three (verified in-the-wild for bundled-CPython apps). Per-key rationale, corrected for this arm64-only box:

- `allow-jit` — on **arm64** the OS enforces W^X and requires `MAP_JIT` + this entitlement for executable pages; this is the **architecturally-relevant** JIT entitlement here.
- `allow-unsigned-executable-memory` — CPython / C-extensions create unsigned executable memory; the documented PyInstaller failure without it is a **`MemoryError` on importing certain C-extension modules** (not a guaranteed startup illegal-instruction crash). Primarily the x86_64 lever, but ship it on both.
- `disable-library-validation` — allows loading libs/plugins not signed under the app's Team ID. Keep it as defense for `dlopen` paths / ad-hoc-and-resign edge cases / any unsigned third-party lib. Note it is NOT strictly justified by "bundled `.so` aren't signed under the Team ID," because the inside-out loop (C.3) re-signs every bundled Mach-O under the Developer ID identity, which would itself satisfy library validation.

### C.3 Inside-out signing — never `--deep` on the sign side

Apple DTS guidance (thread 701514, verified): *"do not pass the `--deep` option … Sign code from the inside out. That is, if A depends on B, sign B before you sign A."* `--deep` applies identical entitlements to every nested item and only finds code in nested code sites. Recipe:

1. every codesign call carries `--options runtime --timestamp`;
2. sign every nested Mach-O innermost-first: `find <App>.app -type f \( -name '*.so' -o -name '*.dylib' \)` plus nested executables → `codesign --force --options runtime --timestamp -s "$SIGN_IDENTITY" <each>`;
3. sign the main executable (`Contents/MacOS/<name>`);
4. sign the `.app` bundle root **last, WITH** `--entitlements entitlements.plist`.

`--deep` is acceptable only on the **verify** side (`codesign --verify --deep --strict`), and even there Apple treats it as a debugging aid, not a blessed verification path.

### C.4 get-task-allow — the classic real rejection cause

The single most common **real** PyInstaller notarization rejection is a bundled binary carrying `com.apple.security.get-task-allow` (the debug entitlement), or a nested Mach-O left ad-hoc/unsigned. Before submission, confirm `get-task-allow` is absent on every nested binary: `codesign -d --entitlements - <each binary>`.

### C.5 Cert-absent N/A boundary (this build host)

No Developer ID Application certificate on the probed host (`codesign` + `notarytool` present; no cert). Real `codesign -s "Developer ID Application: …"`, `notarytool submit`, and `stapler staple` **cannot run** → AC-DEPLOY-009/010 are **environment-gated N/A** per plan.md §A.6 F7. Authorable/dry-verifiable NOW via ad-hoc identity:

- `SIGN_IDENTITY='-'` (ad-hoc) → run the C.3 inside-out loop to prove it touches every Mach-O;
- confirm entitlements embed: `codesign -d --entitlements - <App>.app` and `codesign -d -vv <App>.app`;
- confirm structure: `codesign --verify --deep --strict <App>.app`;
- gate `notarytool`/`stapler` behind `if [ -n "$DEVELOPER_ID" ]`, and read the identity from an env var so the pipeline flips from `-` to the real Developer ID with **no code change**.

### C.6 universal2 is a SEPARATE gate

Signing/notarization is architecture-agnostic. The blocker is the interpreter: the probed CPython 3.11.15 is **arm64-only**, so PyInstaller can emit only an arm64 single-arch app. The pre-confirmed `universal2` target (spec.md 0.2.0 HISTORY) is **unreachable** on this host without a universal2 Python **and** universal2 wheels for `_pydantic_core` and `jiter`. Keep the two concerns decoupled: pipeline authorable now; universal2 output deferred to a universal2 build env.

---

## §D — Consolidated M6 build directives (copy-ready)

**PyInstaller (macOS onedir):**

```
pyinstaller --onedir --windowed \
  --name "GrandMA3 Copilot" \
  --collect-all keyring \
  --hidden-import keyring.backends.macOS \
  --hidden-import keyring.backends.fail \
  --hidden-import keyring.backends.null \
  --hidden-import keyring.backends.chainer \
  --exclude-module keyrings.alt \
  --exclude-module keyrings.cryptfile \
  --collect-submodules uvicorn \
  --collect-all google.genai \
  --collect-all anthropic \
  --exclude-module grpc \
  --add-data ui/dist:ui/dist \
  --add-data console/lua:console/lua \
  --add-data server/rulebook/assets:server/rulebook/assets \
  --add-data config/provider.toml:config \
  <entrypoint pointing at server/web/serve.py : create_app>
```

- No `--copy-metadata` (redundant with `--collect-all`; SDK versions are hardcoded, not metadata-read).
- No special flag for fastapi/starlette/pydantic/httpx/certifi (bundled contrib hooks handle `_pydantic_core.*.so` + certifi CA bundle).
- `--exclude-module grpc` is optional (grpcio absent → nothing to strip; only silences conditional-import warnings).

**Code change before M6 (§A.4):** add `resource_base()` and route `serve.py:29` + `config.py:22` through it (both climb `parents[2]`); route `assembly.py:25` too for robustness. Backend logic otherwise unchanged (plan.md §B: no functional change).

**Launch-time keyring guards (§B.3):** env-pin `PYTHON_KEYRING_BACKEND=keyring.backends.macOS.Keyring` + fail-closed `__module__` startup guard.

**Entitlements plist (§C.2):** `allow-jit`, `allow-unsigned-executable-memory`, `disable-library-validation`.

**Signing (§C.3, env-driven `$SIGN_IDENTITY`, `-` for ad-hoc dry runs):** inside-out loop → main exe → `.app` root with `--entitlements` → `.dmg` → (cert-gated) `notarytool submit --wait` → `stapler staple` → `spctl`/`codesign` verify. Pre-submit: `codesign -d --entitlements -` confirms `get-task-allow` absent (§C.4).

**Verification gate (§B.4):** frozen-binary self-check (`dist/<app>/<app> --self-check`) asserting backend `__module__` + keyring roundtrip — runs the PACKAGED binary, not a dev-venv pytest.

---

## §E — Open risks / residual uncertainty

1. **LOAD-BEARING code refactor before M6** — `serve.py:29` and `config.py:22` (`parents[2]`) MUST route through `resource_base()` or the frozen app cannot find `ui/dist` / `provider.toml`. `assembly.py:25` refactor recommended (lower severity — resolves under `_internal` via the mirrored `--add-data`). Code change, not `.spec` change.
2. **universal2 blocked** — build interpreter is arm64-only CPython 3.11.15 → arm64 single-arch only. The pre-confirmed universal2 decision (spec.md 0.2.0) is unreachable without a universal2 Python + universal2 wheels (`_pydantic_core`, `jiter`). Intel-Mac support out of scope until then — **surface to the user** (this contradicts the recorded universal2 decision).
3. **Signing/notarization blocked** — no Developer ID cert on the build host → only ad-hoc dry verification; AC-DEPLOY-009/010 environment-gated N/A per plan §A.6.
4. **Keychain access under code signing** — keyring items written by the unsigned dev interpreter may be inaccessible to a differently-signed (ad-hoc or Developer-ID) frozen binary (Keychain ACL/partition list keyed on the code-signing identity). Validate the keyring roundtrip inside the actual signed `.app`, not just the raw onedir tree (matches plan §A.6: verify keychain UX with a signed dev build).
5. **get-task-allow / nested ad-hoc binaries** — the classic real notarization rejection; confirm `get-task-allow` absent on every nested Mach-O before submission (`codesign -d --entitlements -`).
6. **uvicorn auto-backend depends on the build-time venv** — the concrete loop/protocol backends (`httptools`/`websockets`/`uvloop`) are selected from what is installed at build time. Pin the packaging venv and verify which backends are present before the M6 build; a packaging venv diverging from the dev venv changes the frozen `auto` resolution.
7. **Future-grpc caveat** — re-enabling a gRPC/Vertex transport reintroduces grpcio C-extensions + dynamic imports (`--collect-all grpc` + `grpc._cython` binaries), changing bundle size and the universal2 story. A `.spec` rework, not a runtime toggle.

---

## Sources

All URLs fetched this session and confirmed to support the cited claim.

- https://pyinstaller.org/en/stable/runtime-information.html — `sys.frozen` + `sys._MEIPASS`; onedir `_MEIPASS` = the `_internal` folder, onefile = temp extraction dir; both set `_MEIPASS`.
- https://pyinstaller.org/en/stable/hooks.html — `collect_all` / `collect_submodules` / `collect_data_files` / `collect_entry_point` / `copy_metadata`; names `keyring` (and `pytest`) as the `collect_entry_point` case; verbatim *"PyInstaller does not collect these metadata files by default."*
- https://pyinstaller.org/en/stable/spec-files.html — `--add-data` colon `SRC:DEST` command-line form (and the `datas` tuple form in `.spec` files).
- https://github.com/jaraco/keyring/issues/399 — keyring backend not auto-detected under PyInstaller (entry-point metadata stripped); *"No recommended backend was available…"* failure; `PYTHON_KEYRING_BACKEND` env workaround (shown with the pre-rename `OS_X` module name).
- https://keyring.readthedocs.io/en/stable/index.html — automatic priority-based backend selection; three override mechanisms (`PYTHON_KEYRING_BACKEND` env, `keyringrc.cfg` `default-keyring`, `set_keyring()`); `keyring.backends.macOS.Keyring` class path.
- https://developer.apple.com/forums/thread/701514 — Apple DTS: do NOT `--deep` for signing complex bundles; *"Sign code from the inside out. That is, if A depends on B, sign B before you sign A."*
- https://www.dolthub.com/blog/2024-10-22-how-to-publish-a-mac-desktop-app-outside-the-app-store/ — real outside-App-Store pipeline: entitlements plist with all three `com.apple.security.cs.*` keys, `xcrun notarytool submit … --wait`, `xcrun stapler staple`, verify.
