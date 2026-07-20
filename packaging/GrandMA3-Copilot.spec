# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for the GrandMA3 Copilot packaged app (M6 / SPEC-COPILOT-DEPLOY-001).

Implements the consolidated research §D directive block verbatim intent:

* **onedir + windowed** -> a macOS ``.app`` container (research §A.7 F8 / FEAS-6);
  a bare Mach-O is unsuitable for double-click + notarization/stapling.
* **keyring (FEAS-2 / research §B)** -> ``collect_all('keyring')`` restores the
  stripped ``entry_points.txt`` metadata + backend submodules, PLUS explicit
  ``macOS/fail/null/chainer`` hidden-imports (the bundled keyring hook is
  historically flaky), PLUS ``keyrings.alt`` / ``keyrings.cryptfile`` excludes
  (REQ-DEPLOY-006a-critical: no plaintext-file fallback backend can ever be
  discovered even if one leaked into the build venv).
* **uvicorn (research §A.1)** -> ``collect_submodules('uvicorn')`` grabs the
  ``auto`` loop/protocol/lifespan backends resolved from runtime strings that
  PyInstaller's static analysis cannot follow.
* **google.genai / anthropic (research §A.2)** -> ``collect_all`` (PEP-420
  namespace siblings + bundled data). No ``copy_metadata`` — ``collect_all``
  already runs it internally, and both SDKs read their version from a hardcoded
  ``__version__`` (research §A.2), so it is redundant anyway.
* **grpc (research §A.3)** -> excluded; grpcio is absent, so there is nothing to
  strip and the exclude only silences any conditional ``import grpc`` warning.
* **--add-data mirrors (research §A.5)** -> ``ui/dist``, ``console/lua``,
  ``server/rulebook/assets``, ``config/provider.toml`` mirrored so the frozen
  ``server.resources.resource_base()`` (``sys._MEIPASS``) resolves each asset.

Build:  .venv/bin/pyinstaller packaging/GrandMA3-Copilot.spec  (from repo root)
Output: dist/GrandMA3 Copilot.app  (+ dist/GrandMA3 Copilot/ onedir tree)

universal2 (research §C.6): the build interpreter here is arm64-only CPython, so
PyInstaller emits an arm64 single-arch app. On a universal2 build env (universal2
Python + universal2 wheels for _pydantic_core / jiter) set env ``PYI_TARGET_ARCH=
universal2`` to flip the target with NO spec edit.
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

APP_NAME = "GrandMA3 Copilot"
BUNDLE_ID = "com.grandma3copilot.app"
APP_VERSION = "0.2.0"

# SPECPATH is injected by PyInstaller at spec-exec time (packaging/ -> repo root).
PROJECT_ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 (SPECPATH is a PyInstaller global)

# arm64-only host -> host arch; ``PYI_TARGET_ARCH=universal2`` flips it with no edit.
TARGET_ARCH = os.environ.get("PYI_TARGET_ARCH") or None

datas: list = []
binaries: list = []
hiddenimports: list = []

# Class 2 (statically analyzable, need namespace/submodule collection) + keyring
# metadata restoration (Class 1). collect_all returns (datas, binaries, hiddenimports).
for pkg in ("keyring", "google.genai", "anthropic"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# uvicorn resolves loop/protocol/lifespan backends from ``auto`` runtime strings
# (research §A.1) that static analysis drops -> collect the whole submodule tree.
hiddenimports += collect_submodules("uvicorn")

# Explicit keyring backend hidden-imports: intentional redundancy on top of
# collect_all('keyring') because the bundled keyring hook is historically flaky
# (research §B.2). Pin the concrete backends the app may legitimately select.
hiddenimports += [
    "keyring.backends.macOS",
    "keyring.backends.fail",
    "keyring.backends.null",
    "keyring.backends.chainer",
]

# Bundled asset trees. PyInstaller ``datas`` tuples are ``(src, dest)`` — the
# ``.spec`` equivalent of the colon ``SRC:DEST`` command-line form (research §A.5).
# Dest dirs mirror the paths server.resources.resource_base() resolves against.
datas += [
    (str(PROJECT_ROOT / "ui" / "dist"), "ui/dist"),
    (str(PROJECT_ROOT / "console" / "lua"), "console/lua"),
    (str(PROJECT_ROOT / "server" / "rulebook" / "assets"), "server/rulebook/assets"),
    (str(PROJECT_ROOT / "config" / "provider.toml"), "config"),
    # Safety ruleset (blacklist + invoking verbs). LOAD-BEARING at boot:
    # server.safety.bootstrap.build_console_stack() -> load_ruleset() reads it via
    # server/safety/ruleset.py's Path(__file__).parent / "blacklist.yaml" (the
    # research §A.4 "third site" __file__-relative pattern), so mirroring the tree
    # here makes it resolve under the bundle — no Python change needed.
    (str(PROJECT_ROOT / "server" / "safety" / "blacklist.yaml"), "server/safety"),
]

excludes = [
    "keyrings.alt",       # REQ-DEPLOY-006a-critical: no plaintext/encrypted-file fallback backend
    "keyrings.cryptfile",
    "grpc",               # absent -> nothing to strip; silences conditional-import warnings (§A.3)
]

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "entry.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,             # windowed -> .app container, no Terminal window on double-click
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=TARGET_ARCH,   # None = host arch (arm64); 'universal2' via PYI_TARGET_ARCH
    codesign_identity=None,     # signing is done inside-out by packaging/sign.sh, NOT here
    entitlements_file=None,     # (a spec-side codesign_identity would --deep sign, which §C.3 forbids)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=None,
    bundle_identifier=BUNDLE_ID,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",   # min macOS 12 (plan.md §F DECIDE-M2)
        "LSUIElement": False,
    },
)
