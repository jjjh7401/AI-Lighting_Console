# t603 run 판정 — 「＋ 새 프리셋 만들기」 창의 효과 종류: 효과 틀 + 한 바퀴(박/마디) + 영문 이름

브랜치 `WT-fx-preset-dialog` · 기준 origin/main `4ef55bb4`(`git merge-base --is-ancestor 4ef55bb4 HEAD` → OK; PR 직전 `git rev-list --count --left-right origin/main...HEAD` → `0 3`) · 콘솔 쓰기 0건(가짜 콘솔만, 전·후 캡처 서버의 쓰기 기록 0줄)

## 판정: PASS

## 무엇이 비어 있었나
t593 은 반영 때 효과 프리셋을 만드는 서버 길(`preset_fx_recipes{"p.s": {fx_id, period_unit, period_value}}`)만 있었다. 그 레시피를 채우는 화면이 없어서, 창으로 효과 번호를 만들면 반영 때 「효과 프리셋 레시피(템플릿·주기)가 없음」으로 보류됐다. 아래 「전」 캡처가 그 상태다.

## 고친 것
- 서버
  - `server/web/messages.py` — `beat_grid_new_preset` 의 `field: "effect"` 는 `fx{fx_id, period_unit: beat|bar, period_value: 양의 정수}` 가 **필수**다. 다른 필드에 오면 거절한다(t599 `aim` 과 같은 엄격함).
  - `server/web/session.py` `beat_grid_new_preset(…, fx=)` — 번호를 정하기 **전에** 두 가지를 본다. 틀이 라이브러리에 있는지, 그 칸 번호대 종류(`effect_kind`)에 맞는지다. 사유는 t593 반영과 같은 문자열이다(`effect_template_problem`). 그래서 반영 때 보류될 틀로 번호를 잡지 않는다. 배정 뒤에는 t593 의 단일 저장 자리 `record_effect_preset_recipe` 에 남긴다.
  - `server/design/beat_grid_effect_presets.py` — `effect_template_catalog`(출하 fx 라이브러리 목록 + 쓸 수 있는 번호대 종류 `kinds`, t593 `_template_fits` 와 같은 판정)와 `effect_template_problem` 을 더했다.
  - 격자 이벤트에 `fx_templates` 를 싣는다(`_beat_grid_refresh_unsent_cells`, `movement_vocabulary` 옆). 콘솔 판독은 0이다 — 출하 파일만 쓴다.
- 화면
  - 새 부품 `ui/src/components/beatgrid/newPresetFx.tsx`. `BeatGrid.tsx` 는 마운트만 한다(그 파일 머리 규칙 — 여러 레인이 동시에 고친다. lane-1 t594 가 같은 창에 색 RGB 를 넣을 예정이다).
  - 고를 수 있는 틀은 그 칸 `effect_kind` 에 맞는 것뿐이다(서버 `kinds`). 종류를 모르는 칸이면 「효과 종류를 먼저 정해야」 안내만 나온다.
  - 「한 바퀴 [N] [박|마디]」는 시안 「한 바퀴 N박」 문구 그대로다. 1 이상의 정수만 받는다.
  - 틀·주기가 다 차야 「만들기」가 켜지고, 요청에 `fx` 를 싣는다(`protocol.ts`·`useCopilotSocket.ts`·`App.tsx`).
  - 위치 칸 옆이 아니라 **창 안**에 칸을 두었다(카드 조건 「위치 칸 옆 별도 입력칸 금지」).
  - `ui/src/styles.css` — 첫 캡처에서 틀 상자가 세로로 120px 늘어났다. 편집 칸 규칙 `.beat-grid-cue-field.is-editing .beat-grid-cue-field-edit select { flex: 1 1 120px }` 이 세로로 쌓인 칸 안에서는 높이로 먹은 탓이다. 더 구체적인 선택자로 크기를 고정했다(아래 캡처 2장 비교는 고친 뒤).
- 번호대·디머 효과 보류 규칙은 t593 그대로다. 디머 효과(`dimmer_effect`)는 `fx` 를 받지 않는다(만들기 범위 밖, REQ-015(i-6)).

## 바뀐 기존 시험 (뜻이 바뀐 것)
- t589·t599 의 효과 창 호출·프로토콜 시험은 레시피가 필수가 되어 9건이 빨갰다. 레시피(`sweep-soft-wide`, 2박)를 넣었다.
- t595 `test_assigned_empty_number_is_marked_held` → `…_marked_create`: 창이 레시피를 남기므로 그 번호의 표식은 이제 「반영 때 만듦」이다.
- t589 승인 카드 시험: 창으로 만든 효과 번호가 보류 줄이 아니라 「새로 만드는 효과 프리셋 1개 … ← sweep-soft-wide · 2박 주기」로 나온다. 이름·설명이 카드에 보이는지(시험 본래 목적)는 그대로 잰다.

## 하네스 전후 캡처 (`capture.py`·`serve_fake.py`, 1450×1000, 가짜 콘솔)
- 전 = main `4ef55bb4` 파일을 `git archive` 로 스크래치에 꺼내 그 서버·빌드로 찍었다. 후 = 이 브랜치.
- 같은 칸(MOVER-U 14마디, 시안 「가속 스윕」 칸, 혼합 효과)에 이름 `LA Sweep 2`, 설명을 넣었다. 둘 다 번호 `22.0` 이 승인 대기로 배정된다.
  - `before/2_filled.png`: 창에 이름·설명 칸뿐이다. 배정 뒤 표식은 `⚠ 22.0 — 빈 프리셋 — 아직 콘솔에 만들 길 없음(효과 프리셋 레시피(템플릿·주기)가 없음) · 「⇪ 콘솔에 반영」에서 이 칸은 송신 보류됩니다`.
  - `after/2_filled.png`: 창 안에 「효과 틀(부드러운 좌우 스윕 (Pan))」 · 「한 바퀴 2 · 박」. 배정 뒤 표식은 `⚠ 22.0 — 빈 효과 프리셋 — 반영 때 템플릿·주기로 만듦(반영당 하나, BPM 없으면 보류) · 「⇪ 콘솔에 반영」 승인 때 콘솔에 만들어 함께 보냅니다`.
- 가짜 콘솔 쓰기 기록: 전 `console_executed_8875_before.log` 0줄, 후 `console_executed_8874_after.log` 0줄. 두 파일은 저장소 `.gitignore` 대상이라 커밋하지 않았다(잰 값만 여기 적는다).
- 하네스 실수 1건(내 것): 처음 가짜 풀 이름을 `All` 로 넣어 「콘솔 빈칸 미확인」 경고가 떴다. 앱이 찾는 이름은 `All 1` 이다(`beat_grid_presets._POOL_NAME_TO_EFFECT_KIND`). 고친 뒤 전·후를 다시 찍었다.

## 검증 (이 트리, 이 세션)
- RED: 새 시험 파일을 먼저 쓰고 `uv run pytest server/tests/test_new_fx_preset_dialog_t603.py` → 수집 오류(`effect_template_catalog` 없음).
- GREEN: 같은 파일 `22 passed`. 관련 묶음(t589·t599·t595·t593·t603·web_messages) → `379 passed`.
- 서버 전체 `uv run pytest server -q` → `15540 passed, 33 skipped`(`full-server.txt`).
- UI `npx tsc --noEmit` exit 0 · `npx vitest run` → `57 files, 1238 passed`(새 `BeatGridNewFxPreset.test.tsx` 10개) · `npm run build` OK.
- `ruff check`/`ruff format --check` — 바꾼 파이썬·하네스 깨끗.
- 뮤테이션(각각 되돌림, 끝에 `git status --short` → `?? ui/.moai/`(훅 상태 파일)뿐):
  - 서버 A 틀 확인 건너뜀 → `2 failed, 20 passed` · B 레시피 저장 안 함 → `3 failed, 19 passed` · C 프로토콜 fx 검사 끔 → `2 failed, 20 passed`
  - UI A 「만들기」가 레시피를 안 봄 → `3 failed, 7 passed` · B 효과 칸 숨김 → `2 failed, 8 passed`

## 이 레인의 실수 1건 (되돌림)
UI 뮤테이션 A 를 되돌리려고 `git checkout -- ui/src/components/BeatGrid.tsx` 를 썼다. 그런데 그 파일의 화면 수정이 **아직 커밋 전**이라 수정까지 같이 지워졌다. 직후 `git diff --stat` 이 비어서 알아챘다. 같은 수정을 다시 넣었고, tsc 0·vitest `1238 passed`(지우기 전과 같은 수)를 확인한 뒤 바로 커밋했다(`4868074d`). 그 뒤 뮤테이션은 커밋된 상태에서만 했다.

## 안 잰 것 / 남은 위험
- **실기 콘솔 0회.** 만든 효과가 실제 콘솔에서 어떻게 보이는지는 t593 범위로, 여기서 다시 재지 않았다.
- **번호 `22.0`**: 혼합 효과 번호대가 `preset_pools.yaml` 에 `22.0`~`22.99` 로 적혀 있어 첫 빈 번호가 슬롯 0 이 된다. MA3 에서 프리셋 슬롯 0 이 유효한지 재지 않았다. 이 카드가 만든 규칙은 아니다(t589 번호 배정 + 번호대 파일) — 리드 확인이 필요하다.
- 화면 클릭 흐름은 jsdom 이 없어 순수 부품 시험과 캡처 한 번으로만 봤다.
- 틀 목록은 이름·속성만 보인다. 틀마다 어떤 움직임인지 미리보기는 없다.
- 반영당 효과 1개 제한(t601 송신 중복)은 t593 그대로다. 창에서 여러 개를 만들어도 반영은 하나씩 만든다 — 창은 이를 알리지 않는다.
- SPEC: REQ-015 (i-4) 가 레시피 출처를 정하고, 창이 레시피를 받는 것을 막는 문구는 없어 고치지 않았다. sync 때 plan.md M13 의 「입력 화면은 범위 밖」 성격 서술이 있으면 이 카드로 닫혔다고 적어야 한다(찾지 못함 — `grep "입력 화면\|채우는 화면\|레시피 입력"` spec·plan 0건).
