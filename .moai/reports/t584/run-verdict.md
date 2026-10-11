# t584 run 판정 — 편집 칸 「움직임」 고르기 목록

카드: t584 · 브랜치 `WT-shape-picker` · 기준 origin/main `a2cc872d`
범위: SPEC-LDBEAT-001 REQ-LDBEAT-006(vi)(app_movement) · REQ-010(미확인 모양) · REQ-021(b)(편집 칸) — t579 갭

## 시안 확인 (먼저 함)

- 정본 `design/ldbeat-runbook-ui-proposal-20261008.html` 편집 칸의 「움직임」은 `<select id="eF">` 하나다. 목록은 **위치 풀 움직임 효과 프리셋**(`P[x].pool==="m"`), 무빙 줄에서만, 미확인 항목엔 `" ⚠"`(`opts()`의 `${P[i].u?" ⚠":""}`), 고르면 그 자리에서 적용.
- 그 드롭다운은 앱에 **이미 있다** — 무빙 줄의 「효과 프리셋」 행(`isEffectRow`, t551). 손대지 않았다.
- 우리 「움직임」 행은 그것과 다른 것이다 — 앱 2단계 무빙 `app_movement`(감독 결정 2026-10-10 「앱 2단계 무빙으로」, t548 이 REQ-006(vi)로 신설). 시안 날짜(10-08)보다 뒤에 생겨 **시안에 이 편집기가 그려져 있지 않다**.
- 그래서 시안이 그린 것은 하나도 바꾸지 않고, 「움직임」 행에 **다른 행과 같은 편집 관례**(값 ✎ 누르기 → 그 자리 드롭다운 → 적용/취소, 미확인 항목 `" ⚠"`)를 그대로 썼다. REQ-016(시안 이탈 = 감독 승인)에 걸리는 변경은 없다고 판단 — 리드가 다르게 보면 되돌리기 쉬운 크기다(부품 하나).

## 바뀐 것

| 항목 | 내용 |
|---|---|
| 서버 어휘 | `beat_grid_edit.movement_vocabulary(probe_results)` — 모양 `POSITION_FX_EFFECTS`, 축 `AXES_VALUES`, 주기 단위 `PERIOD_UNITS`(박·마디만, 초 없음). 각 모양의 `unverified` 와 `phase_spread_unverified` 는 t579 `unverified_movement_terms`(M1 표 ⑨) 그대로 |
| 실어 보내기 | `beat_grid.movement_vocabulary` — 첫 로드(`attach_beat_grid_runtime_extras`)·편집 뒤 재전송(`_beat_grid_refresh_unsent_cells`) 두 길 모두 |
| 화면 | `BeatGridMovementPicker`(`BeatGridCuePanelParts.tsx`): 모양(— 없음 — + 서버 목록, 미확인 `⚠`) → 축(Pan·Tilt·Pan+Tilt) → 주기(미정/박/마디 + 정수 ≥1) → 위상 펼침(미확인이면 `⚠`) → 적용/취소. UI 상수에 모양 이름 0 |
| 명시적 선택만 | 초안은 지금 칸 값이나 「없음」에서 출발 — 미확인 모양을 먼저 골라 두지 않는다. 미확인을 고르면 「⚠ 실기 미확인 — …: 직접 고른 칸에만 들어가요. 곡 기본값으로 쓰지 않고, 콘솔 송신은 M1 확인 뒤에만」 |
| 저장 | `onEditRequest({bar, target, changes: {app_movement}})` → 서버 `apply_beat_grid_edit` 한 길. 「없음」 = `app_movement: null`(지우기) |
| 배지 | 고른 뒤 칸 배지는 t579 `unverified_cells`(같은 함수, 그룹·축까지 봄) |

## 검증 (이 트리 = a2cc872d + 이 변경)

- `python -m pytest -q server/tests -k 'beat_grid or architecture or web_session or protocol or ldbeat or movement_vocab'` → `1006 passed, 14336 deselected`
  - 새 `test_beat_grid_movement_vocab_t584.py` 5개: 닫힌 어휘 일치·초 없음 / ⑨ 미확인↔통과에 따른 ⚠ / 첫 로드 경로 / 세션 편집 → 저장·`unverified_cells`·어휘 재전송 / 「없음」으로 지우기
- `ruff check server` → `All checks passed!` · `ruff format --check server` → `805 files already formatted`
- `ui: vitest run` → `Test Files 53 passed (53)` / `Tests 1166 passed (1166)`(새 9개: 초안 변환·적용 막힘·렌더·⚠·미확인 미선택·저장 경로)
- `ui: tsc --noEmit -p .` → 오류 0 · `npm run build` → `✓ built in 438ms`
- `git rev-list --left-right origin/main...HEAD` → `0 0`(PR 직전, lane-3 겹침 없음)

## 갭

- 실제 브라우저에서 고르기 칸을 눌러 보지 않았다(DOM 시험대 없음 — `renderToStaticMarkup` 과 소스 구조 시험만). 클릭 → 열림 → 적용 흐름의 상호작용은 시험되지 않았다.
- 고르기 전 목록의 ⚠ 는 M1 표만 본 값이다. 실측 기록이 연 그룹(예: MOVER-D Tilt wave + 위상 펼침)은 목록에 ⚠ 가 보여도 적용 뒤 칸 배지는 없을 수 있다 — 의도한 차이(고르기 전엔 축·그룹 조합이 정해지지 않음). 화면 안내문은 이 예외를 말하지 않는다(코드 주석·`protocol.ts` 타입 주석에만 있음).
- 로컬 전체 pytest 는 안 돌림(레인 규칙 — CI 몫).
- 콘솔 접촉 0건.
