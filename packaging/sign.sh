#!/bin/bash
# packaging/sign.sh — macOS hardened-runtime signing pipeline for the frozen
# GrandMA3 Copilot .app (SPEC-COPILOT-DEPLOY-001 M6 / research §C.3).
#
# Env-driven so it runs HERE with no certificate (ad-hoc) and flips to a real
# Developer ID + notarization with NO code change when a cert appears:
#
#   SIGN_IDENTITY   codesign identity. Default '-' (ad-hoc). Set to
#                   'Developer ID Application: NAME (TEAMID)' for a real sign.
#   DEVELOPER_ID    when non-empty, gates xcrun notarytool submit + stapler
#                   staple + spctl assess (research §C.5). Empty here -> N/A.
#   NOTARY_PROFILE  notarytool --keychain-profile name (used only when gated on).
#   ENTITLEMENTS    entitlements plist. Default: packaging/entitlements.plist.
#
# Signing rules (research §C.3, Apple DTS thread 701514):
#   * NEVER --deep on the sign side. Sign inside-out: nested Mach-O first,
#     .app bundle root LAST, and only the root carries --entitlements.
#   * every codesign call: --options runtime (+ secure --timestamp for a real
#     identity; --timestamp=none for the ad-hoc dry run so it runs offline).
#   * pre-submit: confirm get-task-allow (the classic real rejection cause,
#     research §C.4) is absent on every nested binary.
set -euo pipefail

APP="${1:-dist/GrandMA3 Copilot.app}"
SIGN_IDENTITY="${SIGN_IDENTITY:--}"
DEVELOPER_ID="${DEVELOPER_ID:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENTITLEMENTS="${ENTITLEMENTS:-$SCRIPT_DIR/entitlements.plist}"

if [ ! -d "$APP" ]; then
  echo "sign.sh: app bundle not found: $APP" >&2
  echo "  (build it first: .venv/bin/pyinstaller packaging/GrandMA3-Copilot.spec)" >&2
  exit 1
fi
if [ ! -f "$ENTITLEMENTS" ]; then
  echo "sign.sh: entitlements plist not found: $ENTITLEMENTS" >&2
  exit 1
fi

# A real (non-ad-hoc) identity gets a secure timestamp (required for
# notarization); the ad-hoc dry run skips it so it never needs the network.
if [ "$SIGN_IDENTITY" = "-" ]; then
  TIMESTAMP_FLAG="--timestamp=none"
  echo "sign.sh: SIGN_IDENTITY='-' (ad-hoc dry run) — real Developer-ID signing is env-gated N/A"
else
  TIMESTAMP_FLAG="--timestamp"
  echo "sign.sh: SIGN_IDENTITY='$SIGN_IDENTITY' (real identity)"
fi

codesign_one() {
  # $1 = target. --options runtime always (hardened runtime); NO --entitlements
  # on nested items (only the .app root gets them). --force lets us re-sign the
  # PyInstaller-emitted ad-hoc signatures.
  codesign --force --options runtime $TIMESTAMP_FLAG -s "$SIGN_IDENTITY" "$1"
}

echo "sign.sh: enumerating nested Mach-O (inside-out, deepest first) ..."
# Iterate files, test each with `file`, keep Mach-O, sort deepest-first so A is
# signed after its dependency B (research §C.3: sign B before A).
NESTED=()
while IFS= read -r -d '' f; do
  if file --brief "$f" 2>/dev/null | grep -q 'Mach-O'; then
    NESTED+=("$f")
  fi
done < <(find "$APP" -type f -print0)

# Sort deepest-first (most '/' path separators first).
IFS=$'\n' NESTED_SORTED=($(printf '%s\n' "${NESTED[@]}" | awk -F'/' '{print NF"\t"$0}' | sort -rn | cut -f2-))
unset IFS

echo "sign.sh: signing ${#NESTED_SORTED[@]} nested Mach-O binaries ..."
for f in "${NESTED_SORTED[@]}"; do
  codesign_one "$f"
done

# Sign the .app bundle root LAST, WITH entitlements (research §C.3 step 4).
echo "sign.sh: signing bundle root WITH entitlements: $APP"
codesign --force --options runtime $TIMESTAMP_FLAG \
  --entitlements "$ENTITLEMENTS" -s "$SIGN_IDENTITY" "$APP"

# --- pre-submit: get-task-allow MUST be absent on every nested binary (§C.4) ---
echo "sign.sh: auditing get-task-allow (the classic real notarization rejection) ..."
GTA_HITS=0
for f in "${NESTED_SORTED[@]}" "$APP"; do
  if codesign -d --entitlements - "$f" 2>/dev/null | grep -q 'get-task-allow'; then
    echo "sign.sh: FAIL get-task-allow present on: $f" >&2
    GTA_HITS=$((GTA_HITS + 1))
  fi
done
if [ "$GTA_HITS" -ne 0 ]; then
  echo "sign.sh: $GTA_HITS binary(ies) carry get-task-allow — would be rejected by notarization" >&2
  exit 1
fi
echo "sign.sh: get-task-allow absent on all binaries (OK)"

# --- verify (research §C.3: --deep is acceptable on the VERIFY side only) ------
echo "sign.sh: codesign --verify --deep --strict ..."
codesign --verify --deep --strict --verbose=2 "$APP"
echo "sign.sh: embedded entitlements on bundle root:"
codesign -d --entitlements - "$APP" 2>&1 | sed 's/^/  /'

# --- env-gated notarization + stapling (research §C.5) ------------------------
if [ -n "$DEVELOPER_ID" ]; then
  echo "sign.sh: DEVELOPER_ID set — running notarization + stapling"
  DMG="${APP%.app}.dmg"
  hdiutil create -volname "GrandMA3 Copilot" -srcfolder "$APP" -ov -format UDZO "$DMG"
  codesign --force --options runtime $TIMESTAMP_FLAG -s "$SIGN_IDENTITY" "$DMG"
  if [ -n "$NOTARY_PROFILE" ]; then
    xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
  else
    echo "sign.sh: NOTARY_PROFILE unset — configure it for notarytool submit" >&2
    exit 1
  fi
  xcrun stapler staple "$DMG"
  xcrun stapler staple "$APP"
  spctl --assess --type execute --verbose=4 "$APP"
  echo "sign.sh: notarized + stapled: $DMG"
else
  echo "sign.sh: DEVELOPER_ID unset — notarization + stapling are env-gated N/A (research §C.5)."
  echo "sign.sh: ad-hoc structure verified; set DEVELOPER_ID + NOTARY_PROFILE to notarize."
fi

echo "sign.sh: done."
