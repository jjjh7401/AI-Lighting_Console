# t561 run 판정서 — SPEC-LDBEAT-001 M9 step 3·4(가)(다)·5

- 카드: t561 (편집 칸·무대 — 전환 화면 교체·움직임/옆빛 행·2D 무대)
- 범위: REQ-LDBEAT-020·021(a)·022 / AC-LDBEAT-020·021(b)·022 / plan.md M9 step 3·4(가)(다)·5
- 브랜치: `WT-edit-panel-stage` (작업 트리 `.claude/worktrees/t561`), 기준 `d3f47f5a` (= origin/main, 착수 시 확인)
- 정본: `.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.html` (`drawClipEd`·`trViewHTML`·`drawTr`·`clipsHTML`·`drawStage`)
- 콘솔 접촉: 0건 (읽기·쓰기 모두 없음). 새 WS 메시지 타입: 0건.

## 1. 바뀐 것

| 파일 | 내용 |
|---|---|
| `ui/src/components/beatGridTransition.ts` (신규) | 순수 계산: 페이드 "초 먼저(마디 괄호)" 표시, 박→정수 마디 변환, MIB 판정(시안 `mibOf`), [제안] 경고(시안 `warnOf`), 이음매 표시 M·!·◢, 장면 전환 마디(3줄 이상), 콘솔 명령 미리보기(서버 `beat_grid_emit.py` 와 같은 줄 꼴), 2D 무대 그룹 영역 |
| `ui/src/components/BeatGridTransitionView.tsx` (신규) | 전환 화면 — 페이드(들어올 때)·트리거·딜레이·위치만 따로·MIB·트래킹·경고 |
| `ui/src/components/BeatGridCuePanelParts.tsx` (신규) | 머리 둘째 줄(Cue·마디·초), 「움직임」 행, 「옆빛 L·R」 행, 「콘솔 명령」 버튼, 초점 감싸개 `BeatGridCueFocus` |
| `ui/src/components/BeatGridTimelineParts.tsx` (신규) | 이음매(표시 + 페이드 번짐), 「장면 전환」 알약 줄, 장면 전환 표(모두 끊기 / 모두 1박 페이드) |
| `ui/src/components/BeatGridStage.tsx` (신규) | 2D 무대 — 칸 비율에 맞춰 가로 채움(ResizeObserver), 고른 줄 노란 점선, 그룹 이름표, 장비 영역 클릭 → 그 줄 편집 |
| `ui/src/components/beatGridPanels.css` (신규) | 위 부품 스타일. `styles.css` 는 건드리지 않음(t559·t560 동시 수정) |
| `ui/src/components/BeatGrid.tsx` | 마운트만: 장면 전환 줄·이음매·장면 전환 패널·전환 화면·움직임/옆빛 행·콘솔 명령·무대 부품. 「들어올 때」 행과 예전 자리표시자 제거, `timeSignature` prop 추가, 초점 상태 `focusField` 추가 |
| `ui/src/App.tsx` | `timeSignature={timeline.time_signature}` 한 줄 |

### t560 연동 — 초점 prop

`BeatGrid` 안에 `focusField` 상태(`"밝기" | "위치" | "색" | "움직임" | "옆빛" | null`)를 두고 `BeatGridCueFocus focusField={…}` 로 넘긴다. t560 의 「이 마디 한눈에」 표 클릭 핸들러는 `selectCue(trackIndex, bar, false)` 뒤에 `setFocusField("색")` 처럼 부르면 된다 — 그 행에 노란 테두리(`.is-focused`)를 두고 스크롤·포커스한다. 막대를 누르면 `selectCue` 가 초점을 지운다. 행 짝은 `focusFieldRowNames()` (편집 칸 행의 `data-field`).

## 2. AC 대조

| AC | 판정 | 확인 방법 (시험 이름) |
|---|---|---|
| AC-020(a) 이음매 길이/트리거/페이드/MIB/트래킹/경고, 장면전환 알약 | 부분 PASS | `jointMarker` 시험 4건(M·!·◢·빈 이음매), `sceneChangeBars` 시험, `BeatGridSceneRow`·`BeatGridScenePanel` 렌더 시험. 딜레이 [미확인]·경고 [제안] 표기 유지 시험. 트리거 박·트래킹은 저장 칸이 없어 비활성(§4) |
| AC-020(b) 토글 노란색·곡 첫 큐 비활성 | PASS | CSS `#ffd84d` 시험, `disabled={firstCue \|\| !selectedPrevCue}` 소스 시험 |
| AC-020(c) 콘솔 명령 버튼이 지금 화면에 맞는 명령 | PASS | 렌더 시험(맨 아래·처음 닫힘·켜면 노란색) + 화면별 줄 선택 소스 시험 |
| AC-020(d) 같은 자리 교체·별도 상자 0건·「들어올 때」는 전환 화면 | PASS | 한 삼항의 두 갈래 소스 시험, 자리표시자 잔존 0, 전환 화면 렌더에 「들어올 때」 |
| AC-020(e) "N.NN초 (M마디)", `fade_bars` 불변 | PASS | `formatFadeSecondsFirst` 시험 + 렌더 정규식. 보기만 해서는 저장 요청 0 — 코드 판독: `onEditRequest` 호출은 「적용」·「모두 끊기」 핸들러 두 곳뿐(실행으로 잰 것 아님) |
| AC-021(b) 필드 순서 머리→밝기→위치→색→움직임→옆빛L·R→콘솔명령, 「들어올 때」 없음, 안내문 | PASS | 순서 소스 시험, `beat-grid-cue-field-entry` 잔존 0 시험, 빈 안내문 = 시안 `drawEd` 문구 |
| AC-022(a) 상태판·3D 캡처·평면도 UI 0건 | PASS | 소스 grep 시험 |
| AC-022(b) 노란 점선·그룹 이름표·클릭 편집 | PASS(데이터 있을 때) | `BeatGridStage` 렌더 시험(점선 1개·이름표·`data-track` 클릭 영역). 옆빛 L·R 좌우 색 구분은 갈라짐 데이터가 없어 미구현(§4) |
| AC-022(c) 높이 320px, 폭 1.2배, 창 크기 따라 다시 그림 | PASS(CSS·계산) | CSS 규칙 시험 + `stageViewWidth` 시험. 실제 브라우저 계산값은 안 잼(§3) |

## 3. 증거 (이 실행, 이 트리)

| 명령 | 결과 | 파일 |
|---|---|---|
| `cd ui && npx vitest run` (착수 전) | `Test Files 35 passed (35)` · `Tests 882 passed (882)` | `baseline-vitest.txt` |
| `cd ui && npx tsc --noEmit -p .` (착수 전) | exit 0 | `baseline-tsc.txt` |
| `npx vitest run src/components/beatGridTransition.test.ts` (구현 전) | `Test Files 1 failed (1)` · `Tests no tests` (모듈 없음 — RED) | `red-1.txt` |
| `cd ui && npx vitest run` (완료 후) | `Test Files 37 passed (37)` · `Tests 942 passed (942)` | `vitest.txt` |
| `cd ui && npx tsc --noEmit -p .` (완료 후) | exit 0 | `tsc.txt` |
| `cd ui && npx vite build --outDir <scratch>` | exit 0, `✓ built in 405ms` | `vite-build.txt` |

**렌더 시험 뮤테이션 확인** — 렌더 시험은 구현 뒤에 썼으므로 공허하지 않은지 셋을 일부러 깨 봤다(높이 320→280, 토글 비활성 조건에서 `!selectedPrevCue` 제거, 옆빛 행 마운트 제거):

```
× AC-LDBEAT-020(b) — 전환 토글 > 곡 첫 큐(들어오는 전환 없음)에서는 비활성
× AC-LDBEAT-021(b) — 편집 칸 필드 순서 > 밝기 → 위치 → 색 → 움직임 → 옆빛 L·R → 콘솔 명령
× AC-LDBEAT-022 — 2D 무대 > (c) 높이 320px, 폭 비율 1.2
      Tests  3 failed | 23 passed (26)
```

되돌린 뒤 `Tests 26 passed (26)`.

### 안 잰 것

- **브라우저 화면 확인 0회.** 이 저장소에 jsdom·브라우저 시험대가 없고, 박자 격자 미리보기 진입점도 없다. 320px·1.2배·노란색은 CSS 문면과 계산 함수로만 확인했다 — 실제 `getComputedStyle` 값은 안 쟀다.
- **앱에서 2D 무대는 지금 안내문만 보인다.** `App.tsx` 가 `BeatGrid` 에 `fixtures` 를 넘기지 않는다(기존 상태, 이 카드 이전부터). 노란 점선·이름표·클릭은 장비 좌표가 들어오는 날 보인다.
- 「모두 끊기」·페이드 「적용」의 서버 왕복은 안 쟀다 — 서버 `apply_beat_grid_edit` 가 `entry` 를 받는 것(`beat_grid_edit.py:435`)과 `entry` 를 통째로 바꾼다는 것(병합 `{**base, **changes}`)만 코드로 읽었다. 그래서 `mib_mode` 를 함께 보낸다.
- Python 시험은 로컬에서 안 돌렸다(서버 파일 변경 0). CI 가 돈다.

## 4. 리드 판단이 필요한 것 (시안과 다르게 보이는 곳 — 전부 데이터 제약)

1. **「모두 1박 페이드」 비활성.** 저장 단위가 정수 마디(`entry.fade_bars`, REQ-LDBEAT-006(i-4))라 1박(=¼마디)을 저장할 수 없다. 버튼은 시안 자리에 두고 이유를 툴팁으로 단다. 살리려면 저장 단위를 박으로 바꾸는 SPEC 결정이 필요하다(REQ-020(e)가 지금은 저장 단위 불변을 요구).
2. **트리거 박·딜레이·위치만 따로·트래킹은 비활성 컨트롤.** 시안에는 입력이 있지만 저장 칸이 없다. 값을 지어내지 않고 같은 자리에 비활성으로 두었다(트리거는 1박 = 마디 시작으로 표시 — 에미터가 1박 기준). 저장 칸 신설은 별도 카드 감.
3. **박 입력은 정수 마디로 떨어질 때만 받는다** — 곡 박자표가 4/4 면 4·8·12박만. 박자표를 모르면 박 입력 자체가 비활성(4를 지어내지 않음).
4. **「옆빛 L·R」 행은 상태 표시 + 비활성 버튼.** L·R 자식 줄(REQ-019(c))은 M9 step 2(타임라인) 소관이라 여기서 배선하지 않았다. 무대의 좌우 색 구분도 그 데이터가 생겨야 한다.
5. **경고의 강조(★) 마디 예외 미적용.** 시안 `warnOf` 는 ★ 마디의 끊김을 경고에서 뺀다 — 곡 데이터에 강조 마디가 아직 없다(M9 step 1 소관). 그 전까지 ★ 마디의 켜진 채 위치 끊김도 [제안] 경고로 보인다.
6. **곡 시각은 곡 0초 기준.** 시안은 타임코드 리드(앞박) 3초를 더해 보여 준다 — 그 값의 데이터 출처가 UI 에 없어 더하지 않았다(지어내지 않음). 표시 문구는 "곡 N.NN초".

## 5. 남긴 것

- `ui/src/styles.css` 의 `.beat-grid-cue-field-entry-btn` 규칙이 이제 쓰이지 않는다. 다른 레인이 같은 파일을 고치는 중이라 지우지 않았다.
- `formatFadeBarsField`·`deriveFadeSeconds` 내보내기는 기존 시험이 쓰므로 그대로 두었다(화면에서는 더 안 쓴다).
