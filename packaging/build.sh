#!/bin/bash
# packaging/build.sh — reproducible macOS build of the frozen GrandMA3 Copilot
# .app (SPEC-COPILOT-DEPLOY-001 M6). Run from the repo root.
#
#   ./packaging/build.sh          # build (arm64 host) + ad-hoc sign
#   PYI_TARGET_ARCH=universal2 ./packaging/build.sh   # universal2 build env
#   SIGN_IDENTITY='Developer ID Application: ...' DEVELOPER_ID=TEAMID \
#     NOTARY_PROFILE=my-profile ./packaging/build.sh   # real sign + notarize
#
# Prerequisites (research §D):
#   * ui/dist must exist (bundled UI). Built here if missing via `npm --prefix ui run build`.
#   * .venv with pyinstaller installed (uv pip install --python .venv/bin/python pyinstaller).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PY:-$ROOT/.venv/bin/python}"
APP_NAME="GrandMA3 Copilot"
SPEC="packaging/GrandMA3-Copilot.spec"

echo "build.sh: repo root      = $ROOT"
echo "build.sh: python         = $PY"
echo "build.sh: PYI_TARGET_ARCH= ${PYI_TARGET_ARCH:-<host arch>}"

# 1. UI build prerequisite — the bundle mirrors ui/dist (research §A.5).
if [ ! -f "ui/dist/index.html" ]; then
  echo "build.sh: ui/dist missing — building the UI (npm --prefix ui run build) ..."
  npm --prefix ui run build
else
  echo "build.sh: ui/dist present (skipping npm build)"
fi

# 2. PyInstaller onedir build from the committed .spec (reproducible).
echo "build.sh: running PyInstaller ..."
"$PY" -m PyInstaller --noconfirm --clean "$SPEC"

APP="dist/$APP_NAME.app"
if [ ! -d "$APP" ]; then
  echo "build.sh: expected app not produced: $APP" >&2
  exit 1
fi
echo "build.sh: built $APP"

# 3. Sign (ad-hoc by default; real identity + notarization when env-gated on).
echo "build.sh: signing ..."
bash packaging/sign.sh "$APP"

echo "build.sh: done -> $APP"
echo "build.sh: frozen self-check:  '$APP/Contents/MacOS/$APP_NAME' --self-check"
