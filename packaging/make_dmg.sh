#!/bin/bash
# packaging/make_dmg.sh — package the SEALED GrandMA3 Copilot .app into a
# drag-to-Applications .dmg for hand-over to a colleague (SPEC-COPILOT-DEPLOY-001,
# ad-hoc-only distribution — no Developer ID / notarization in scope).
#
#   ./packaging/make_dmg.sh                                   # uses the Tauri shell .app
#   ./packaging/make_dmg.sh "dist/GrandMA3 Copilot.app"        # or an explicit .app path
#
# MUST run AFTER `npm run shell:build` (or packaging/build.sh) has produced and
# ad-hoc-sealed the .app. `tauri build` alone (and `tauri build --bundles dmg`)
# emits the .app BEFORE the sidecar payload mirror + ad-hoc seal step, so a .dmg
# built directly by Tauri — or by this script pointed at an unsealed .app —
# would ship the unpatched, unsealed bundle. This script re-verifies the seal
# on its input before packaging, and exits non-zero rather than package a
# bundle that fails `codesign --verify --strict`.
#
# Why a .dmg over a plain zip: mounting/compressing into a UDZO image never
# touches the app's file bytes or resource fork, so the ad-hoc seal survives
# unchanged (same class of safe operation as `ditto -c -k --sequesterRsrc
# --keepParent`, `tar`, or `rsync -a` — see packaging/README.md "Delivery
# artifact"). Unlike a zip, mounting a .dmg gives a non-technical recipient the
# familiar "drag the app onto the Applications alias" affordance in one window,
# with no separate unzip-then-move step.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP="${1:-src-tauri/target/release/bundle/macos/GrandMA3 Copilot.app}"
APP_NAME="$(basename "$APP" .app)"
VERSION="$(node -p "require('./package.json').version" 2>/dev/null || echo 0.0.0)"
OUT_DIR="dist"
OUT_DMG="$OUT_DIR/${APP_NAME// /-}-${VERSION}.dmg"

if [ ! -d "$APP" ]; then
  echo "make_dmg.sh: app not found: $APP" >&2
  echo "make_dmg.sh: run 'npm run shell:build' (or packaging/build.sh) first" >&2
  exit 1
fi

echo "make_dmg.sh: verifying input seal ..."
if ! codesign --verify --strict "$APP"; then
  echo "make_dmg.sh: input app failed 'codesign --verify --strict' — refusing to" >&2
  echo "make_dmg.sh: package an unsealed bundle. Re-run the build/seal step first." >&2
  exit 1
fi
echo "make_dmg.sh: input seal OK ($APP)"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

echo "make_dmg.sh: staging ..."
ditto "$APP" "$STAGE/$APP_NAME.app"
ln -s /Applications "$STAGE/Applications"

mkdir -p "$OUT_DIR"
rm -f "$OUT_DMG"
echo "make_dmg.sh: creating $OUT_DMG ..."
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$OUT_DMG"

echo "make_dmg.sh: done -> $OUT_DMG"
