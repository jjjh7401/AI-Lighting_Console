# 카드 t630 — 런북 UI 「이유 없는 차이」 6건 (완료 보고)

- 작성일: 2026-10-14
- 워크트리: `.claude/worktrees/t630` (브랜치 `WT-runbook-ui-gaps`)
- 기준: origin/main `f69eb96e`. 착수 기준 `19a52738`과 UI·서버 코드가 같음(`git diff --stat 19a52738 f69eb96e -- ui server` 출력 없음)
- 현재 HEAD: `17ce8618`. 로컬 커밋 3개, **아직 push 안 함**
- **rebase 정정 (2026-10-14 09:48):** origin/main이 9커밋 더 앞서서 `origin/main`(`ce846ab6`) 위로 rebase했다. 추가된 9커밋은 docs·packaging 정리뿐이고 `ui/`·`server/`는 건드리지 않았다. 이 보고서 본문의 커밋 SHA는 rebase 전 값이며 대응은 다음과 같다. `507e04dd`→`b999c1a7`, `6db8d4ce`→`20e2727b`, `7d04a613`→`17ce8618`. 측정은 `7d04a613` 시점에 했고 내용은 같다.

## 1. 결과 요약

| 항목 | 판정 | 처리 |
|---|---|---|
| ① 마디 옆 구간 이름 | 없음 | 구현 (`507e04dd`, 폭 기준 `7d04a613`) |
| ② 반영 대기 배지 「—」 | 일부 있음 (숨김) | 구현 (`6db8d4ce`, 폭 기준 `7d04a613`) |
| ③ 줄 이름 둘째 줄 | 이미 있음 | 제외 |
| ④ 눈금 구간 이름·경계선 | 이미 있음 | 제외 |
| ⑤ 무대·한눈에 높이 389 | 시안 차이 | 감독 결정: **320px 유지**, 제외 |
| ⑥ 무대 이름표·빔 | 코드 있음, 데이터 게이트 | 제외, 데이터 카드 필요 |
| 서버 첫 연결 때 반영 기록 누락 | 범위 밖 | 후속 카드 **t635** (리드 생성) |

## 2. 커밋

| SHA | 제목 | 파일 |
|---|---|---|
| `507e04dd` | 상단 바 마디 표시에 현재 구간 이름 추가 | `BeatGrid.tsx`, `BeatGridTopBar.tsx`, `BeatGridTopBar.test.tsx`, `styles.css` |
| `6db8d4ce` | 반영 기록이 없을 때도 반영 대기 배지를 「—」로 표시 | `App.tsx`, `BeatGridTopBar.tsx`, `BeatGridTopBar.test.tsx`, `beatgrid/pendingApplyCount.ts`(+test) |
| `7d04a613` | 좁은 폭에서 줄바꿈이 생기지 않게 구간 이름 1490px·「—」 1520px 기준 추가 | `BeatGridTopBar.tsx`, `BeatGridTopBar.test.tsx`, `styles.css` |

## 3. 항목별 근거

### ① 마디 옆 구간 이름 — 구현
- 변경 전 상단 바는 `N마디`만 그렸다(`BeatGridTopBar.tsx`). 구간 정보는 이미 `BeatGrid.tsx`의 `viewBarSectionLabel`로 계산되고 있었다(「N마디 한눈에」 제목이 같은 값을 씀).
- 화면 근거: 변경 전 캡처, 마디 12 — 상단 바 「12마디」, 제목 「12마디 한눈에 — Verse 1」.
- 같은 값을 재사용했다. 새 데이터 경로는 없다.

### ② 반영 대기 배지 「—」 — 구현
- 변경 전에는 `pendingApplyCount`가 `undefined`일 때 배지를 숨겼다. 서버는 첫 반영 전 `unsent_cells`를 `null`로 준다(`server/web/session.py`의 `_beat_grid_current_unsent_cells`: 「이 곡으로 반영을 한 번도 안 했으면 None」).
- 「—」는 `null`을 뜻한다. 숫자는 기록이 있을 때만 센다(`pendingApplyCountOf`). 0으로 지어내지 않는다.
- **한계:** 첫 연결 경로(`server/web/app.py` 490–492행)는 `unsent_cells` 없이 저장된 시간표를 보낸다. 그래서 첫 화면에서는 배지가 보이지 않고, 편집 같은 갱신 뒤에만 「—」가 생긴다. 이건 서버 쪽 문제라 후속 카드 t635로 분리됐다.

### ③ 줄 이름 둘째 줄 — 제외 (이미 있음)
- 변경 전 캡처의 시간표 줄 이름에 둘째 줄이 있다. 예: `G4 · 201~202 · 2대`(BACK), `G14 · 601~602 · 2대`(BLIND).
- 그룹 소속이 확정된 줄만 개수와 범위를 보인다. 시험 데이터에서 FOH, WASH-ALL 등은 「G3」처럼 번호만 나온다. 데이터 게이트이며 UI 빈틈은 없다.

### ④ 눈금 구간 이름·경계선 — 제외 (이미 있음)
- 변경 전 캡처의 눈금에 `Intro`(1마디), `Verse 1`(6마디), `Verse 2`(13마디)와 경계선이 있다.

### ⑤ 무대·한눈에 높이 389 — 제외 (감독 결정 320px 유지)
- 앱은 무대 칸 높이가 320px로 고정돼 있다(`beatGridPanels.css`). 시안 측정은 389px이다(변경 전 캡처: 한눈에 표 320 vs 시안 389, 무대 320 vs 시안 389).
- SPEC `REQ-LDBEAT-016(b)`과 `AC-LDBEAT-022(c)`가 320px을 고정 요구한다. 시안 요약 md는 320px이다.
- 시안 HTML 정본은 `.insp` 390px(내부 389px), 무대 SVG 330px이다. md와 HTML이 서로 다르다.
- 2026-10-14, 이 창에서 감독님이 「320px 유지 (권장)」로 답하셨다. 그래서 이번 카드에서는 손대지 않는다.
- 389로 바꾸려면 감독 확인을 SPEC 기록과 함께 따로 받아야 한다. 이 카드 범위가 아니다.

### ⑥ 무대 이름표·빔 — 제외 (데이터 게이트)
- 이름표는 그룹 소속이 확정된 장비에만 그려진다(변경 전 캡처: BACK, BLIND만 표시).
- 빔은 움직이는 장비가 확정되고 점등돼야 그려진다. 빔 길이와 색에 필요한 틸트·프리셋 색 데이터는 페이로드에 없다.
- UI만으로는 채울 수 없다. 데이터 카드가 먼저 필요하다.

## 4. 폭 기준 (감독 결정, 2026-10-14)

- **구간 이름**: 1490px부터 보인다. 그 아래는 마디 번호만 보이고, 전체 이름은 마디 칸의 `title` 툴팁으로 본다.
- **「—」 배지**: 1520px부터 보인다. 그 아래에서는 CSS로 숨기고, 마크업에는 남긴다.
- **근거 측정 (변경 전 CSS, 마디 12, 가짜 콘솔 하네스):**
  - 구간 이름만: 1475px에서 두 줄, 1490px에서 한 줄
  - 「—」 배지만(이름 없이): 1450px에서 두 줄
  - 이름과 배지를 같이: 1500px에서 두 줄, 1520px에서 한 줄
- **승인 출처**
  1. 이 창의 답 2026-10-14: 「1490px부터 (권장)」, 「1520px부터 (권장)」
  2. 리드 세션 중계 2026-10-14: 리드의 감독 확인 「승인」, 「REQ-LDBEAT-016(a) 시안 차이 승인 기록으로 SPEC에 남길 것」
- **SPEC 기록은 이 카드에서 쓰지 않았다.** SPEC 본문과 `progress.md`는 manager-spec 소관이다. 리드에게 기록을 요청했다.

## 5. 화면 측정 (`7d04a613`, 마디 12)

| 폭(px) | 마디 텍스트 | 구간 이름 display | 「—」 display | 상단 바 높이 | 두 번째 줄 버튼 |
|---|---|---|---|---|---|
| 1450 | 12마디 | none | none | 58 | 없음 |
| 1475 | 12마디 | none | none | 58 | 없음 |
| 1489 | 12마디 | none | none | 58 | 없음 |
| 1490 | 12마디 · Verse 1 | inline | none | 58 | 없음 |
| 1505 | 12마디 · Verse 1 | inline | none | 58 | 없음 |
| 1519 | 12마디 · Verse 1 | inline | none | 58 | 없음 |
| 1520 | 12마디 · Verse 1 | inline | inline | 58 | 없음 |
| 1540 | 12마디 · Verse 1 | inline | inline | 58 | 없음 |
| 1700 | 12마디 · Verse 1 | inline | inline | 58 | 없음 |

- 「—」 배지는 주입(DOM에 같은 클래스 요소를 넣음)으로 확인했다. 배지가 보일 때 「반영」 버튼 폭은 69.89px에서 94.83px로 늘어난다.
- 1450px 마디 12 캡처는 변경 전 캡처와 바이트 단위로 같다.
- 마디 0(1450, 1700): `0마디`, 58px, 구간 요소와 title이 없다.
- 페이지 오류는 모든 실행에서 없다(`app_page_errors` = `[]`).
- 콘솔 쓰기 0건(가짜 콘솔 로그 0바이트).

## 6. 시험

- `npm --prefix ui run test`: 60 files, **1272 tests passed** (`7d04a613`에서 직접 재실행).
- `npm --prefix ui exec -- tsc --noEmit -p ui/tsconfig.json`: 종료 코드 0.
- `npm --prefix ui run build`: 종료 코드 0 (97 modules).
- 단계별 시험 수: 기준 1262 → 507e04dd 후 1269 → 7d04a613 후 1272.

## 7. 안 잰 것 · 남은 위험

- **첫 화면 배지**: 캡처에서는 보이지 않는다(서버 첫 연결 경로). 「—」가 편집 뒤에 실제로 뜨는지는 실제 편집 경로로 재지 않았다. 주입으로만 확인했다.
- **숫자 배지**(반영 뒤 편집 수): 기존 요소이며 같은 클래스를 쓴다. 1450px에서 줄이 바뀌는지는 재지 않았다.
- **0마디 표기**: 구간 밖에서는 번호만 보인다. 정본 시안은 「앞박」으로 쓴다. 이번 카드 범위 밖이라 두었다.
- **실기 콘솔**: 확인하지 않았다. 가짜 콘솔 하네스(`t583`)와 단위 시험만 썼다.
- **CI**: 아직 돌리지 않았다. push 전이다.
- **SPEC 승인 기록**: 리드가 manager-spec을 통해 남겨야 한다(REQ-LDBEAT-016(a)).
- **베이스**: origin/main이 착수 뒤 6커밋 앞서 있었다(PR #671, #672와 SPEC 문서·CHANGELOG). UI·서버 코드는 같아서 전 캡처 기준선은 유효하다. 로컬 fast-forward로 맞췄다.

## 8. 원격 반영 상태

- push: **하지 않음**. PR: **하지 않음**. 머지: **하지 않음**.
- 이 창의 감독 확인을 받은 뒤에 진행한다. 리드가 중계한 승인만으로는 push 허용을 대신하지 못한다.

## 9. 컨텍스트 (완료 보고 기재 사항)

- 2026-10-14 09:40:28 기준 **65%** (1M 기준, `tokens_used` 650,000, 단계 `soft`). 상태 파일의 세션 번호(`88051e3a-…`)가 이 창과 일치한다.
- 인계 기준 50%를 넘었다. 감독님께 `/clear`를 권했다.
- 닫은 카드 수: 0(t630은 아직 닫지 않음). 이 창이 맡은 카드 수: 1.

## 10. 증거 파일 (`.moai/reports/t630/`, 워크트리 안, git 추적 외)

- `premise.md`: 전제 재확인 6건
- `before-app-1450-full.png`, `before-app-1700-full.png`, `before-design-*-full.png`, `before-regions.json`, `before-commands.txt`
- `before-bar12-*.png`, `before-bar12.json`, `before-bar12-harness.mjs`
- `after-*.png`, `after-regions.json`, `after-bar12.json`, `after-commands.txt`
- `after2-bar12-topbar-{1450,1490,1520,1700}.png`, `after2-bar12-full-{1450,1700}.png`, `after2-measure.json`
- `after-measure-threshold.json`, `after-measure-wrappoints.json`
- `before-side_by_side/`, `after-side_by_side/`: 영역별 캡처 묶음(큰 폴더, 커밋 대상 아님)
- `runbook-preview-misdirected/`: 처음에 잘못된 대상(`ui/runbook-preview.html`)을 찍은 결과. 보관만 하고 근거로 쓰지 않는다.
