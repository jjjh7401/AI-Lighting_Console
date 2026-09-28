#!/bin/sh
# AC-051(빌드 산출물 웹폰트) · AC-019 REQ-096(Trans 값 잔존) 정적 확인.
# 사용: sh static_checks.sh <vite build 출력 폴더>  (워크트리 루트에서)
D="$1"
echo "## AC-051 build output ($D)"
find "$D" -type f | sed "s#$D/##"
echo "font files (.woff/.woff2/.ttf/.otf):"
find "$D" -type f \( -name '*.woff' -o -name '*.woff2' -o -name '*.ttf' -o -name '*.otf' \) | wc -l
echo "font CDN / @font-face refs:"
grep -rEo "fonts\.googleapis\.com|fonts\.gstatic\.com|@font-face" "$D" | wc -l
echo "tabular-nums occurrences in built css:"
cat "$D"/assets/*.css | grep -o "tabular-nums" | wc -l
echo
echo "## AC-019 REQ-096 Trans still valid on server"
uv run python -c "from server.design.cue_sheet_edit import TRANS_VALUES, EDITABLE_FIELD_LABELS; print('TRANS_VALUES=', TRANS_VALUES); print('label[trans]=', EDITABLE_FIELD_LABELS['trans'])"
