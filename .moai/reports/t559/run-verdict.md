# 카드 t559 — run 판정 (SPEC-LDBEAT-001 M9 step 1·8)

- 범위: 곡 전체 지도(REQ-LDBEAT-018 / AC-LDBEAT-018, plan.md M9 step 1) + 상단 바(REQ-LDBEAT-017 / AC-LDBEAT-017, step 8)
- 트리: `.claude/worktrees/t559`, 브랜치 `WT-song-map-topbar`, 기준 `origin/main` `d3f47f5a`
- 정본: `.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.{html,md}` (`.top`, `.ov`/`drawOv()`, `:7-8`, `:122`)
- 콘솔 쓰기: 0 (새 WebSocket 메시지 타입 0, 서버 코드 변경 0)

## 1. 데이터 모양 (step 1을 먼저 고정)

`ui/src/components/songOverviewModel.ts` — 지도가 그리는 값은 전부 곡 데이터에서 읽는다.

| 지도 요소 | 출처 필드 | 없을 때 |
|---|---|---|
| 총 마디 수 | `timeline.bar_count` | 격자 표시 범위(`bar_range.end + 1`) |
| 구간 띠 위치 | `sections[].bar_start`, 없으면 `start_ms ÷ seconds_per_bar` | 그 구간을 뺀다(위치를 지어내지 않음) |
| 구간 색 | `sections[].palette_primary_hex` | 중립색 |
| 에너지선 | `sections[].d_level`(1~5) ÷ 5 | 그 구간에서 선을 끊는다 |
| 강조 ★ | `sections[].accents`가 비어 있지 않은 구간의 **시작 마디** | ★ 없음 |
| BPM | `timeline.bpm` | `BPM —` |
| 버전 | `timeline.lifecycle` 라벨(`SongTimeline.tsx`의 `LIFECYCLE_LABEL`, 이번에 export만 추가) | 표시 안 함 |

**해석 하나(리드 확인 필요)**: 곡 데이터에 "강조 마디 번호" 필드는 없다. 있는 것은 구간 단위 `accents` 문자열(`song_cue_render.py:272-280`, 예: `"climax accent"`)뿐이라 ★를 "accents가 있는 구간의 시작 마디"로 읽었다. 시안의 ★ 네 자리(18·46·63·67)를 같은 방식으로 재현하는지는 LOVE ATTACK 실데이터로 재보지 않았다(§4 미검증).

## 2. 무엇이 생겼나

- **상단 바**(`BeatGridTopBar.tsx`): 런북 모드 · 곡 · 버전 · BPM · ◀ N마디 ▶(←→ 키, 입력칸 안에서는 무시) · 「▶ 이 마디 콘솔에서 보기」 · 「■ 끄기」 · 「⇪ 콘솔에 반영(대기 수)」 · 「▤ 프리셋 서랍」. 1450px 이상이면 세 버튼이 「▶ 콘솔」「⇪ 반영」「▤」로 줄고 풀네임은 title에 있다.
  - 콘솔 쓰는 세 버튼(보기·끄기·반영)은 송신 경로가 없어 **비활성**이고, title에 "아직 배선 안 됨"이라고 적힌다. 대기 수는 출처가 없어 숫자를 띄우지 않는다(prop을 주면 뜬다).
  - ▤는 기존 서랍과 같은 동작(`onDrawerRequest`)으로 실제로 열린다.
- **곡 전체 지도**(`SongOverview.tsx`): 곡 전체 길이 한 줄 SVG — 구간 띠 · 에너지선 · ★ · 채운 범위(점선) · 지금 보는 범위(흰 테두리, 타임라인 스크롤을 따라감) · 재생 위치 · SCENE 메모 ⚠(기존 표식 유지) · 클릭하면 그 마디로 점프 · 확대 3단계(곡 전체/16마디/8마디, 기본 16마디 — 시안 기본값).
- **확대는 타임라인 가로 폭을 실제로 바꾼다**: 16마디/8마디 = 보이는 폭에 16·8마디가 들어가는 폭, 곡 전체 = 곡 전체가 들어가는 폭(최소 6px).
- **전체 폭**: `.beat-grid` `max-width: 1640px`, `width: min(97vw, 1640px)`(REQ-LDBEAT-016(b), AC-LDBEAT-017(c)).

## 3. 증거

| 주장 | 명령 | 관측 |
|---|---|---|
| 새 시험이 먼저 실패했다(RED) | `npx vitest run src/components/songOverview.test.ts`(모듈 생성 전) / `…BeatGridTopBar.test.tsx` | `Test Files 1 failed` · `Failed to load url ./BeatGridTopBar` |
| 새 시험 통과 | `npx vitest run src/components/BeatGridTopBar.test.tsx src/components/songOverviewModel.test.ts` | `Test Files 2 passed (2)` · `Tests 22 passed (22)` |
| UI 시험 전량 | `npx vitest run` (ui/) | `Test Files 37 passed (37)` · `Tests 904 passed (904)` |
| 타입·빌드 | `npx tsc --noEmit -p .` → exit 0, `npx vite build` | `✓ built in 368ms` |
| 곡 리터럴 0건(AC-018(a)) | `grep -nE '\b(18\|46\|63\|67)\b' SongOverview.tsx songOverviewModel.ts BeatGridTopBar.tsx` | 매치 0(grep exit 1) |
| 두 곡 → 서로 다른 ★ | `songOverviewModel.test.ts`·`BeatGridTopBar.test.tsx` "두 곡이 서로 다른…" | `[12]` vs `[0, 6]`, 마크업 `data-bar="5"` vs `data-bar="0"` |
| AC-017(a)(b)(c), AC-018(b), 점프·←→ | 헤드리스 크로뮴 폭 1000/1449/1450/1700 | `browser-measure.txt` — 1449: 풀네임 3개 보임 · 1450: 줄임 3개만 보임 · 모든 폭 title에 풀네임 · maxWidth `1640px` · 폭 970 / 1405.5 / 1406.5 / 1640 = `min(폭×0.97, 1640)` · 확대 3단계 눈금 폭 서로 다름(1000px: 13.4 / 33.5 / 67) · 지도 클릭 → `12마디` · → 키 → `13마디` |

증거 원문: `.moai/state/verify/t559/vitest.txt`, `build.txt`(gitignore 대상이라 이 보고서에 숫자를 옮겨 적음), `.moai/reports/t559/browser-measure.txt`.

## 4. 안 잰 것 (Gaps)

- **CI**: 이 문서를 쓰는 시점엔 아직 안 돌았다 — PR head의 CI 결과는 리드 회신에 적는다.
- **LOVE ATTACK 실데이터로 지도를 그려 보지 않았다**: 시험·측정은 전부 지어낸 곡 fixture다. 실제 `timeline.bar_count`·`bar_start`·`accents`가 채워져 오는지, ★가 시안 네 자리와 맞는지 모른다.
- **실기 콘솔·실제 앱 서버로 띄워 보지 않았다**(임시 미리보기 페이지만).
- 창 높이 560px에서는 타임라인 줄이 보이지 않았다(높이 1000px에서는 정상). 높이 배분(440px, REQ-LDBEAT-019(d))은 이 카드 범위 밖이라 원인을 파지 않았다.
- pytest는 돌리지 않았다(서버 변경 0).

## 5. 남은 위험 · 리드에게 넘길 것

1. **`BeatGrid.tsx`는 "마운트만"보다 넓게 건드렸다**(+137/−70, 12덩어리). 대부분 파일 위쪽(가져오기·속성·상태)과 옛 머리줄·지도 자리 교체지만, 타임라인 본문도 두 줄 바뀌었다 — 줄 영역 `<div className="beat-grid-lanes">`에 `ref`/`onScroll`, 자 눈금 `width: PX_PER_BAR → pxPerBar`. 확대가 타임라인 가로 스케일을 바꾸려면 피할 수 없었다. 타임라인 막대 그리기 코드는 컴포넌트 안 `barToX`를 확대 폭으로 감싸서 **한 줄도 안 고쳤다**. t560·t561과 겹칠 수 있는 자리는 이 두 줄과 `viewBar` 한 줄이다.
2. 옛 `.beat-grid-head`·`.beat-grid-overview-*` CSS는 지웠다(쓰는 곳 0). 순수 함수 `deriveSectionBlocks`·`barPercentInRange`·`BEAT_GRID_BAR_ROWS`는 기존 시험이 쓰므로 남겼다.
3. 아래 명령창 줄의 「📁 프리셋」 버튼은 그대로 뒀다(명령창은 REQ-LDBEAT-025, 다른 카드). 지금은 상단 ▤와 같은 서랍을 연다 — 시안엔 상단 ▤만 있다.
4. 기존 `.beat-grid-toolbar`(모두 접기·±10초·시계·음원·쓰기 잠김)는 plan.md step 8대로 그대로 유지했다 — 시안처럼 상단 바 안으로 옮기는 일은 재생·음원(REQ-LDBEAT-024) 카드와 같이 정할 일이다.
5. ◀▶·지도 점프는 격자 칸 데이터가 있는 범위(`bar_range`) 안에서만 움직인다. 그 밖의 마디는 지도에는 보이지만 갈 수 없다.
