#!/bin/bash
# t588 — main(0a89a121)의 두 파일로 ui/dist-before 를 빌드하고, 고친 파일을 되돌린다.
set -e
F1=ui/src/components/BeatGrid.tsx
F2=ui/src/components/BeatGridStage.tsx
SAVE=.moai/reports/t588/_save
mkdir -p "$SAVE"
cp "$F1" "$SAVE/BeatGrid.tsx"
cp "$F2" "$SAVE/BeatGridStage.tsx"
restore() { cp "$SAVE/BeatGrid.tsx" "$F1"; cp "$SAVE/BeatGridStage.tsx" "$F2"; rm -r "$SAVE"; }
trap restore EXIT
git show origin/main:"$F1" > "$F1"
git show origin/main:"$F2" > "$F2"
(cd ui && npx vite build --outDir dist-before --emptyOutDir > /dev/null 2>&1)
echo "before build ok"
