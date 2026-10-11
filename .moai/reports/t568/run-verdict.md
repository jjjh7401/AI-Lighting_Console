# t568 run 판정 — 박자 격자 표·타임라인 남은 공급자 3개

카드: t568 · 브랜치 `WT-grid-suppliers` · 기준 origin/main `68c0c930`
범위: SPEC-LDBEAT-001 REQ-LDBEAT-019(a)(c)·023(c) — t560 이 남긴 갭 셋

## 커밋

| SHA | 내용 |
|---|---|
| 0bf044dd | ① L·R 분리 판정을 `beat_grid_stage.groups[].member_fids` 로 |
| b36265b1 | ③ 프리셋 칩 `description` 을 명시적 `None` 으로 |
| d10b5a7f | ①③ 증거 파일 |
| (이 커밋) | ② `unsent_cells` → 「고침=초록」 UI 소비 + 이 판정문 |

## ① L·R 소속 — PASS

- 판정: 그 줄 그룹을 `groups.find(g => g.group_name === track.group_name)` 로 찾고, `complete === false` 이거나 없으면 버튼 숨김. 있으면 `member_fids` 를 무대 `x` 로 가른다. 이름 규칙 0.
- 방향(시험으로 고정): x 가 작을수록 관객 기준 왼쪽(L). 출처 둘이 일치 — ⓐ `.moai/specs/SPEC-COPILOT-SPATIAL-001/design.md:67-71`·`spec.md:164-165,170`(MA3 `+x = stage left` = 배우 기준, 관객 기준은 반대), ⓑ 앱 2D 무대 `projectFixture` 가 큰 x 를 화면 오른쪽에 그린다. `lrSplit.test.ts` 「L·R 방향(실측 확정)」.
- RED `red-lrsplit.txt`(21 실패/8 통과) → GREEN 29/29.

## ② 「고침=초록」 — PASS(UI 소비) / 공급 대기

- 리드 결정(2026-10-11): `BeatGridView.unsent_cells: [{group_name, bar}] | null`(반영 스냅숏 없으면 null). 스냅숏·필드는 t563(lane-1)이 넣고 t568 은 UI 소비만.
- `protocol.ts` 에 타입, `editedCueKeysFromUnsent` 순수 함수(null·undefined·빈 배열 → 초록 0, 여러 칸 → 칸마다 키), `BeatGrid` 는 부모 키가 없으면 이 값을 쓴다.
- RED: `npx vitest run src/components/beatgrid/cueDisplayState.test.ts` → `TypeError: editedCueKeysFromUnsent is not a function` 4건 실패 → GREEN.
- 갭: t563 머지 전까지 서버가 필드를 안 보내므로 화면에서는 아직 안 켜진다.

## ③ 칩 설명 — 출처 없음(정직한 None)

- `console_slots.paged_pool_children` 는 슬롯 `i`/`name` 만 돌려준다. `grep -rln "description" server/design/beat_grid_data/*.yaml` → 0건. 새 콘솔 판독 없이 설명을 얻을 곳이 없어서 `build_preset_drawer` 가 `"description": None` 을 명시로 보낸다(시험으로 고정). UI 는 사용 수만 보여 준다.
- RED `red-presets.txt`(2 실패) → GREEN 23/23.

## 최종 검증 (이 트리, `ui/`)

- `npx vitest run` → `Test Files 47 passed (47)` / `Tests 1060 passed (1060)`
- `npx tsc --noEmit -p .` → exit 0 · `npm run build` → exit 0
- Python(에이전트, ①③ 시점): `uv run pytest -q` → 15095 passed, 33 skipped. ② 는 서버 무변경.

## 갭 · 안 잰 것

- 브라우저로 직접 띄워 보지 않았다.
- ③ 설명 텍스트 자체는 비어 있다 — 채우려면 콘솔 프리셋의 설명 속성을 새로 읽는 판독이 필요(새 카드 감).
- ② 는 t563 머지 뒤에야 실제로 켜진다.
