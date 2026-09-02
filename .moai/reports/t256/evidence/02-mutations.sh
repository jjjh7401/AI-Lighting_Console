#!/bin/bash
# t256 — 뮤테이션: 새 검사가 판별력을 갖는지. 각 치환 뒤 원복한다.
set -u
cd /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t256
SRC=server/lxseq/cue_mapper.py
PY=/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.venv/bin/python
BAK=$(mktemp)
cp "$SRC" "$BAK"

run() {
  PYTHONPATH=. "$PY" -m pytest server/tests/test_lxseq_cue_mapper.py -q \
    -k "dim or reference or numeric_columns" 2>&1 | tail -1
}

mutate() {
  local label="$1"; shift
  cp "$BAK" "$SRC"
  "$@"
  printf '%-46s -> %s\n' "$label" "$(run)"
  cp "$BAK" "$SRC"
}

mutate "M1 Dim 갈래 제거 (항상 BAD_NUMBER)" \
  perl -0pi -e 's/if column == "Dim" and DIM_REFERENCE_SHAPE\.match\(raw\.strip\(\)\):/if False:/' "$SRC"

mutate "M2 판별자를 「점이 있으면」 으로 넓힘" \
  perl -0pi -e 's/\^\[A-Za-z\]\+\\\.\[0-9A-Za-z\]\+\$/^.+\\..+\$/' "$SRC"

mutate "M3 열 한정(column == Dim) 제거" \
  perl -0pi -e 's/if column == "Dim" and DIM_REFERENCE_SHAPE/if DIM_REFERENCE_SHAPE/' "$SRC"

mutate "M4 사유 문면에서 「참조」 제거" \
  perl -0pi -e 's/"Dim 은 프리셋 참조가 아니라 숫자다: "/"Dim 값이 이상하다: "/' "$SRC"

mutate "M5 3분류를 (A) 로 오분류" \
  perl -0pi -e 's/    DIM_NOT_A_REFERENCE: \(\n        BLOCK_DOC_INTENT,/    DIM_NOT_A_REFERENCE: (\n        BLOCK_OUR_DEFECT,/' "$SRC"

cp "$BAK" "$SRC"
rm -f "$BAK"
echo "--- 원복 확인 ---"
run
