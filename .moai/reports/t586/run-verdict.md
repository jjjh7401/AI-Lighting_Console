# t586 run verdict — 런북 화면 시안과 다른 곳(t583 🟡) 영역별 정리

- 카드: t586 · SPEC-LDBEAT-001 REQ-016~025 · 근거 `.moai/reports/t583/diff-list.md`
- 브랜치: `WT-mockup-gaps` · 기준 `origin/main` 0a08eef3
- 콘솔 연결 0 · 콘솔 쓰기 0(`console_executed_882{1,2}.log` 0바이트) · 백그라운드 서버 2개 내림(포트 8821·8822 리스너 0)
- 다른 레인 몫이라 건드리지 않음: 상단 바·플레이 묶음(t587), ★ 표식(t567)

## t583 🟡 항목 처리표 (전수)

| 영역 | t583 🟡 항목 | 처리 | 근거 |
|---|---|---|---|
| 상단 바 | 마디 표시에 구간 이름 없음 · 반영 배지 · 버튼 크기 · `v1 초안` | ⏭ t587 몫 | 리드 지시 |
| 플레이 묶음 | 크기·글자 크기 들쭉날쭉 | ⏭ t587 몫(상단 바 안) | 리드 지시 |
| 곡 지도 | 구간 색 | ⚪ 데이터(구간 `palette_primary_hex` 없음) | t583 표 |
| 곡 지도 | ★ 대신 ⚠ | ⏭ t567 몫 | 리드 지시 |
| 타임라인 | **눈금에 구간 이름·경계선 없음** | ✅ 고침 — 구간 시작 마디에 이름 + 진흙색 왼쪽선(시안 `.rb.sec`/`.sl`), 눈금 38px | `1450x1000/1450_4_timeline.png` |
| 타임라인 | **줄 이름에 그룹 정보 없음** | ✅ 고침 — 둘째 줄 `G4 · 201~202 · 2대`(시안 `.lhead small`). 확인된 소속 장비가 없으면 `G3` 만(지어내지 않음) | 같은 그림 · `trackFixtureSummary` 시험 4개 |
| 타임라인 | 「26마디~ 아직 배치 안 함」 | ➖ 범위 밖 — t583 에서도 미측정, 기본 격자가 0~25 라 이 곡에선 재현 불가 | — |
| 한눈에 표 | **역할 폴더 묶음 없음** | ✅ 고침 — `▾ 앞빛 · key` 머리 줄(시안 `#bt tr.gh`), 타임라인 폴더 접기 상태 공유(시안 `OPEN`) | `1450_5_glance_table.png` |
| 한눈에 표 | **머리말에 구간 이름·오른쪽 안내 없음** | ✅ 고침 — `14마디 한눈에 — Verse 2` + `훑어보기 · 누르면 오른쪽에서 고치기` | 같은 그림 |
| 한눈에 표 | 노란 점선 SCENE 경고 줄 | ➖ 유지 — 시안엔 없지만 REQ-006(iv-3) 이 만든 「미정 이유」 표시. 빼려면 SPEC 변경이 필요 | `BeatGrid.test.tsx:413` |
| 2D 무대 | **고른 줄 노란 점선·그룹 이름표** | ⚪ **이미 있음 — t583 판독 정정**. BACK 을 고르면 점선·이름표가 그려진다(`probe_before_seam.png`). t583 에서는 소속이 확인 안 된 WASH-ALL 을 골라 안 보였다(하네스 데이터) | `BeatGridStage.tsx:98-117` |
| 2D 무대 | 빔 삼각형·워시 면·역할 색 | ➖ 안 함 — REQ-022(b) 요구 목록(점선·이름표·클릭·L·R 색)에 없는 시안 장식. 시안 문구도 「2D 개념도」 | spec REQ-022 |
| 2D 무대 | **머리말 오른쪽 위치·초 없음** | ✅ 고침 — `14마디 · 29.9초`(시안 `#stT`), BPM 없으면 마디만 | `1450_6_stage_2d.png` |
| 편집 칸 | 드롭다운 대신 읽기 + ✎ | ✅ **동작 확인, 바꾸지 않음** — 값을 누르면 드롭다운·입력 2개가 열린다(`probe_clicks.py`: 컨트롤 0 → 2). 「처음부터 열린 입력」으로 바꾸는 것은 편집 상태 구조를 갈아엎는 일이라 이 카드 범위를 넘는다 → 리드 판단 | `probe_before_pencil.png` |
| 편집 칸 | **머리 구성(장비 범위 등)** | ✅ 일부 고침 — `장비 201~202 · 2대(소속 확인)`(REQ-021(b) 머리의 「장비」). 시퀀스 번호·기종은 이 화면이 받는 데이터에 없어 안 넣음 | `1450_7_edit_panel.png` |
| 편집 칸 | 출처 경로 두 줄 꺾임 | ➖ 그대로 — 시안에 「출처」 줄 자체가 없다. 줄바꿈은 넘침이 아니라 정상 감싸기 | — |
| 편집 칸 | 빈 상태 안내 | — 비교 대상 없음(t583 과 같음) | — |
| 전환 화면 | 이음매 ◆ 로 열리는가 | ✅ **동작 확인** — `button.beat-grid-joint` 를 누르면 전환 화면이 열린다(`transition_view_open: 1`) | `probe_before_seam.png` |
| 전환 화면 | **머리말이 길고 노란 글자** | ✅ 고침 — `전환 · WASH-ALL · Cue 1 → Cue 2`(흰 13px, 시안 `.sidepane h5`) + 둘째 줄에 막대 이름·저장 위치 | `1450_8_transition.png` |
| 전체 | M1 콘솔 확인 프로브 9줄 | ➖ 유지 — REQ-003(b) 가 만든 칸. 이제 틀 스크롤 맨 아래 | — |
| 전체 | **명령 줄에 「명령」 레이블 없음** | ✅ 고침(시안 `.cmd`). 예시는 값이 아니라 placeholder 로 둠 — 미리 채운 문장이 실수로 보내지지 않게 | `after/.../app_*_full*.png`, `wip_*_bottom.png` |
| 전체 | 프리셋 버튼 위치(시안은 상단 바 `▤`) | ⏭ 상단 바라 t587 몫 | — |
| 전체 | **맨 아래 조작 안내 줄 없음** | ✅ 고침 — 시안 `.log` 문구·색. 적힌 조작이 앱에 실제로 있는지 대조함(←→ `barNavKeyDelta`, ◢·M·! `beatGridTransition.ts:200`) | `wip_1450x1000_bottom.png` |

표 행 기준: ✅ 11행(그중 2행은 「동작 확인, 바꾸지 않음」) · ⏭ 다른 레인 4행 · ➖ 이유 있는 유지 5행 · ⚪ 데이터/판독 정정 2행 · — 비교 대상 없음 1행

## 바뀐 파일

- `ui/src/components/BeatGrid.tsx` — 눈금 구간 이름, 줄 이름 둘째 줄, 한눈에 표 폴더 묶음·머리말, 무대 머리말, 편집 칸 장비 범위 전달, 명령 레이블, 조작 안내
- `ui/src/components/beatGridStageModel.ts` — `confirmedFixtureRange`·`trackFixtureSummary`(무대 판독 소속에서만, 상수 0)
- `ui/src/components/BeatGridCuePanelParts.tsx` — 머리에 장비 범위
- `ui/src/components/BeatGridTransitionView.tsx` — 전환 머리말
- `ui/src/styles.css`, `ui/src/components/beatGridPanels.css` — 시안 수치(눈금 38px·진흙색 `#d97757`·`#f0b49c`·로그 줄 색), 장면 전환 줄 sticky `top` 21→39px(눈금 높이를 따라)
- `ui/src/components/beatGridStageModel.test.ts` — 시험 4개 추가

## 증거

```
$ npm --prefix ui test
Test Files  53 passed (53) · Tests  1179 passed (1179)

$ npm --prefix ui run build      # tsc + vite
exit=0
```

- 전후 캡처: `side_by_side_before/` · `side_by_side_after/` — `{1450,1700}x1000/` 의 영역 짝 그림(4 타임라인·5 한눈에·6 무대·7 편집·8 전환) + 앱 전체 화면. 앱 페이지 오류 전부 0.
- 작업 중 확인: `wip_1450x1000_{default,selected,transition,bottom}.png`
- 미측정 두 동작 측정: `probe_clicks.py` → `probe_before_pencil.png`, `probe_before_seam.png`

## 안 잰 것

- 실기 콘솔·프리셋이 채워진 곡 0회 — 줄 이름 둘째 줄의 범위·대수는 소속이 확인된 BACK·BLIND 에서만 보였다(하네스 데이터가 그만큼만 있음).
- 세로 1000 한 높이만 캡처(t585 가 900·1200 배치는 확인).
- 구간이 많은 곡에서 눈금의 구간 이름이 좁은 칸(8마디 확대 아닌 곡 전체 확대)에서 잘리는 모양 — `overflow:hidden` 으로 잘리게 해 두었지만 곡 전체 확대에서는 찍지 않았다.

## 리드 판단 요청

1. 편집 칸을 시안처럼 「처음부터 열린 드롭다운」으로 바꿀지 — 지금은 값 한 번 누르면 열린다(동작 동일, 한 단계 차이).
2. 한눈에 표의 SCENE 경고 줄·M1 프로브 칸 — 시안엔 없지만 다른 REQ 가 만든 기능이라 유지했다.
