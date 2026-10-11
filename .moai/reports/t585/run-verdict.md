# t585 run verdict — 런북 박자 격자 화면 배치 결함 4건 (t583 🔴)

- 카드: t585 · SPEC-LDBEAT-001 REQ-016(b)·004(b) · 근거 `.moai/reports/t583/diff-list.md`
- 브랜치: `WT-layout-fix` · 기준 `origin/main` 41d8736c
- 바꾼 파일: `ui/src/styles.css`, `ui/src/components/beatGridPanels.css`(CSS 만), `ui/src/styles.test.ts`(회귀 시험 5개)
- 🟡 약 20건은 건드리지 않음(t586 몫) · 콘솔 연결 0 · 콘솔 쓰기 0(`console_executed*.log` 전부 0바이트) · 백그라운드 서버 2개 내림

## 원인 — 계산된 스타일로 잼 (`measure_before_1450x1000.json`)

| # | 증상 | 잰 원인 | 고친 것 |
|---|---|---|---|
| ① | 타임라인 171px(시안 440px) | `.beat-grid-mid { flex: 1 }` — 고정 높이 칸(무대·표 320, M1 프로브 136, 명령줄 등)이 먼저 가져가고 남은 것만 받음. `.beat-grid` 가 창 높이 898px 에 묶이고 `overflow: hidden` | `.beat-grid-mid { flex: 0 0 auto; height: 440px }`(시안 정본 수치 그대로) + `.beat-grid-fullscreen-frame .beat-grid { overflow-y: auto }` — 칸 합이 창보다 크면 잘라 버리지 않고 틀째 스크롤 |
| ② | 막대 선택 시 줄 이름이 덮이고 폴더 머리가 사라짐 | 줄 이름 칸은 이미 `sticky; left:0` 이었지만 **배경 높이가 글자 높이 15px 뿐**(줄은 26px) → 위아래로 막대가 비침. 폴더 머리(`.beat-grid-folder-head`)는 고정 대상이 아니어서 가로 스크롤 624px 에 화면 밖으로 밀림 | 줄 이름 `align-self: stretch` + 가운데 정렬. `.beat-grid-folder { width: max-content; min-width: 100% }` + 폴더 머리 `position: sticky; left: 0` |
| ③ | 편집 칸·전환 화면이 잘림 | 칸 자체는 `overflow: auto` 로 스크롤되지만 높이가 타임라인과 같은 171px — 전환 내용 553px 중 대부분이 칸 아래에 숨음 | ① 로 함께 해소 — 칸이 440px(시안 「칸 높이 = 타임라인 높이」), 넘치는 113px 는 칸 안 스크롤(시안 `.sidepane{overflow:auto}` 와 같음) |
| ④ | 무대 경고 다섯째 줄이 범례와 겹침 | **t583 판독 정정**: 실제로는 겹치지 않는다(목록 끝 770px, 범례 774px). 목록이 `max-height: 64px; overflow: auto` 인데 줄 높이가 약 15px 라 4.27줄 — 다섯째 줄이 칸 아래 끝에서 반만 잘려 범례에 붙어 보였다 | `.beat-grid-stage-notes { line-height: 16px }` — 64px 에 정확히 4줄, 나머지는 칸 안 스크롤 |

## 시안 정본과의 대조

`.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.md`(= `reports/` 사본, sha256 앞 16자리 `39032b4d5e313a56` 일치):

- 「타임라인 영역 높이 고정(440px) — 폴더를 펼쳐 줄이 늘면 그 안에서 위아래 스크롤. 마디 눈금·장면 전환 줄은 위에, 줄 이름은 왼쪽에 고정」 → ①②
- 「편집 칸(폭 310px, 높이 = 타임라인 높이)」, 「전환 화면이 같은 자리에서 바뀜」 → ③
- SPEC REQ-LDBEAT-016(b) 「타임라인 높이 440px … 그 값을 시안이 적은 값 그대로 보존」 → ①

**해석 하나(리드 판단 요청)**: REQ-004(b) 「전체화면 뷰는 한 화면 높이로 고정」을 시안 원문(`:155` 「화면을 한 화면 높이로 고정」 + 비교 표 「이전 시안 매우 김(스크롤 2~3화면) → 한 화면 고정」)대로 **칸들이 줄 수에 따라 늘지 않는 고정 높이**로 읽었다. 창 높이에 맞춰 줄이는 뜻으로 읽으면 REQ-016(b) 440px 와 부딪힌다. 시안 자체도 세로 약 1060px 이라 900·1000px 창에서는 틀이 스크롤된다 — 지금 구현도 같다(틀 높이 1167px, 창 안 틀 898px).

## 증거

### 영역 높이 — 전후 × 6 뷰포트 (`side_by_side_{before,after}/regions.json`, 앱 페이지 오류 전부 0)

| 뷰포트 | 타임라인 전→후 | 편집 칸 전→후 | 전환 화면 전→후 | 무대 |
|---|---|---|---|---|
| 1450×900 | 71 → **440** | 71 → **440** | 71 → **440** | 320 |
| 1450×1000 | 171 → **440** | 171 → **440** | 171 → **440** | 320 |
| 1450×1200 | 371 → **440** | 371 → **440** | 371 → **440** | 320 |
| 1700×900 | 71 → **440** | 71 → **440** | 71 → **440** | 320 |
| 1700×1000 | 171 → **440** | 171 → **440** | 171 → **440** | 320 |
| 1700×1200 | 371 → **440** | 371 → **440** | 371 → **440** | 320 |

### 계산된 스타일 — 후 (`measure_after_1450x1000.json`)

- 막대 선택 뒤 첫 줄 이름 칸 상자 `[36, 355, 90, 26]` (전: 높이 15)
- 전환 화면 칸 `[1104, 287, 310, 440]`, 스크롤 높이 553 (전: 칸 171)
- 무대 경고 목록 64px, 줄 높이 16px

### 눈으로 본 것

- `side_by_side_after/1450x1000/app_1450_full_selected.png` — 8줄·폴더 머리 6개 전부 보이고, 14마디로 가로 스크롤된 상태에서도 줄 이름이 막대 위에 불투명하게 남음
- `side_by_side_after/1450x1000/1450_8_transition.png` — 페이드·트리거·딜레이·위치만 따로·MIB 까지 한 칸에 보임
- `side_by_side_after/1450x1000/1450_6_stage_2d.png` — 경고 4줄 정확히, 반 줄 잘림 없음
- 비교: 같은 이름의 `side_by_side_before/...` 파일

### 시험

```
$ npm --prefix ui exec -- vitest run src/styles.test.ts     # 고친 CSS
Tests  33 passed (33)

$ (main 의 CSS 두 파일로 바꿔 같은 명령 — 돌린 뒤 되돌림, git diff --stat 동일 확인)
Tests  5 failed | 28 passed (33)          # 새 시험 5개 전부 실패 = 결함을 잡는다

$ npm --prefix ui test
Test Files  53 passed (53) · Tests  1162 passed (1162)

$ npm --prefix ui run build                # tsc + vite
exit=0
```

## 오진 정정 · 제 탓 아님으로 판정한 것

- **④ 은 「겹침」이 아니라 「반 줄 잘림」** — t583 diff-list 를 내가 잘못 읽었다(위 표). 고칠 결함인 것은 같다.
- **막대 선택 뒤 틀이 아래로 밀린 캡처**는 캡처 스크립트 탓이다 — Playwright 의 요소 캡처가 아래 영역을 화면 안으로 스크롤한다. 실제 클릭만 재면 틀 `scrollTop` 0 → 0, `scrollIntoView`·`focus` 호출 0건(`measure_select_scroll.py`).
- **세로 900px 에서 상단 바 「⇪ 반영」이 오른쪽에서 잘림 + BPM 알약이 긴 문구** — 고치기 전 main 화면(`side_by_side_before/1450x900/app_1450_full.png`)에도 똑같다. 이 카드 변경 탓이 아니어서 손대지 않음 → **새 카드 후보**(🟡/🔴 판정은 리드 몫).

## 안 잰 것

- 실기 콘솔·프리셋이 채워진 곡 0회(t583 하네스 데이터).
- 1450·1700 두 폭만 — 그보다 좁은 창(1280 등)은 안 잼.
- 폴더를 다 펼친 큰 리그(트랙 수십 개)에서 440px 안 세로 스크롤은 이 곡(8트랙, 내용이 440 안에 들어감)으로는 재지 못했다.
- 시안에 없는 「M1 콘솔 확인 프로브」 칸은 그대로 둠(🟡, t586 몫) — 이제 틀 스크롤 아래쪽에 있다.

## 재현

```
npm --prefix ui ci && npm --prefix ui run build
uv run python .moai/reports/t585/serve_fake.py 8811              # 고친 UI
uv run python .moai/reports/t585/serve_fake.py 8812 dist-before  # main CSS 로 빌드한 UI(만드는 법은 위 「시험」)
uv run --with playwright --with pillow python .moai/reports/t585/capture.py 8811 after
uv run --with playwright python .moai/reports/t585/measure_layout.py 8811 1450 1000 after
```
