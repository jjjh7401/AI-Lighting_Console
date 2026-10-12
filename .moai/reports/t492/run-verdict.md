# t492 — SPEC-LDDESIGN-001 AC-018 후속 3곳: 원천 판정 (구현 전 보고)

- 카드: t492 · 워크트리 `.claude/worktrees/t492` · 브랜치 `WT-ldd-empty-panels`
- 기준: `origin/main` = `f0b0071d`(착수 시 HEAD 와 같음, `git merge-base --is-ancestor f0b0071d HEAD` 통과)
- 이 판정서까지 코드 변경 0 · 콘솔 접촉 0. 리드 지시대로 **구현 전에 보고한다.**
- 대상: REQ-079(항목 클릭 → 4칸)·REQ-080(「그래서 보이는 것」)·REQ-098(탭 2·3), AC-018 잔여 3건(`progress.md:678`).

## 판정 요약

| 자리 | 원천 | 판정 |
|---|---|---|
| ① 탭 1 「그래서 보이는 것」 | 없음 | 비워 둔다 + 원천 설계안(§1) |
| ② 4칸 「무슨 뜻」 | 없음 | 원천 설계안(§2) |
| ② 4칸 「왜 이렇게 제안했나」 | **부분** — `rows[].evidence` 등급 토큰 | 등급만 싣는 배선은 가능, 사유 문장은 없음(§2) |
| ② 4칸 「바꾸려면」 | 없음(편집 기능은 있음, 안내 원천 없음) | 원천 설계안(§2) |
| ② 불릿(인과 불릿) 클릭 4칸 | 없음 — 4칸 모두 | 원천 설계안(§2) |
| ③ 탭 2 공간·움직임·질감·시작–끝 | **있음** — `sections[]` 의 `position`·`movement`·`texture`·`start_ms/end_ms` | 배선 가능하나 탭 1 표·CUE SHEET 와 **같은 값 반복**(§3) |
| ③ 탭 2 감정 | 없음 — `mood` 필드는 서버가 "못 채움"으로 선언 | 비워 둔다(§3) |
| ③ 탭 3 아껴 두는 것 | **있음** — `concept_report.reserve` | 배선 가능(§4) |
| ③ 탭 3 지키는 것·하지 않는 것 | **있음(가공 필요)** — `concept_report.gates` 13개 | 규칙 13개를 지킴/금지로 나누는 분류가 필요 = 설계 판단(§4) |

## 1. 「그래서 보이는 것」 — 원천 없음

- 인터뷰 질문은 모두 **곡 단위**다: `Q1_CONCEPT`·`Q2_PALETTE`·`Q2B_COLOR_USAGE`·`Q3_CLIMAX`·`Q4_SPATIAL_STORY`·`Q5_TEXTURE`(`server/design/interview.py:114-119,148-155`). 구간마다 "관객이 보는 결과"를 묻는 질문은 없다.
- 워크시트 `Worksheet`(`server/concept/worksheet.py:92-100`)에도 구간별 효과·의도 필드가 없다(`sections.rows[].memo` 는 자유 메모). 게다가 앱 경로에서 `load_worksheet` 를 부르는 곳이 0이다(t485 §2와 같음).
- `rows[].description` 은 t485 §4에서 "색 칸과 8/8 중복"으로 이미 제외했다.
- **설계안(선택 1개 필요)**
  - (가) 비워 둔 채 칸 사유를 「구간별 결과 원천 없음 — 감독 입력 필요」로 바꾼다. 코드는 사유 문자열 1곳만 바뀐다.
  - (나) 인터뷰에 구간별 질문을 하나 더한다(예: 정점·후렴 같은 핵심 구간마다 "관객이 무엇을 봐야 하나"). 서버 `interview.py`에 질문을 추가하고 → `audit_trail` → `session.py` 페이로드에 `section_outcome[screen_position]` 를 싣고 → 칸에 원문 그대로 표시한다. 감독이 답한 구간만 채우고, 나머지는 빈칸 + 사유. **인터뷰 흐름이 바뀌므로 감독 결정이 필요하다.**
  - (다) 계산 문장(예: 직전 구간 대비 밝기·색 변화를 "더 밝아진다"로 바꾸는 문장)으로 채운다. **권하지 않는다.** 앞 다섯 칸을 말로 다시 적는 것이라 REQ-097의 "같은 내용 반복"이 되고, t485 §4의 결론과도 충돌한다.

## 2. 4칸 설명(구간 행 클릭 · 불릿 클릭)

현재 구간 행 4칸 중 「무대에서」만 차 있다(`conceptGlance.ts` `explanationCells`). 나머지 3칸은 원천이 있는지 보지 않고 고정 NO_DATA 를 넣는다. 불릿에는 4칸이 아예 붙어 있지 않다(t485 §6).

- **무슨 뜻**: `server/concept/vocab.py` 는 닫힌 어휘 목록(SECTIONS/TRIGGERS/ONE_SHOTS/OPERATIONS)과 검증기만 있고, 뜻풀이 텍스트가 없다 → **원천 없음.**
  - 설계안: `vocab.py` 옆에 어휘 토큰마다 한 줄 뜻풀이 표(`GLOSSARY`)를 두고, `concept_report.rows[]` 에 그 행이 쓴 토큰의 뜻을 싣는다. 리그·곡에 묶이지 않는 용어 정의라서 상수 표여도 "리그·곡 상수 금지"에 걸리지 않는다. 다만 **같은 토큰이 여러 행에 나오면 같은 문장이 반복된다** → 행마다 다른 토큰 조합이므로 반복은 행 단위로만 생긴다. 이것을 REQ-097 위반으로 볼지 리드 판단이 필요하다.
- **왜 이렇게 제안했나**: `rows[].evidence`(`session_bridge.py:240` → `evidence_for_row`)가 이미 페이로드에 있고, CUE SHEET 「근거 등급」 칸이 쓰고 있다(`runbookM7.ts:221`). 하지만 값은 `verified`/`designed_rule` 같은 **등급 토큰**이지 사유 문장이 아니다.
  - 설계안 A(작은 배선): 칸에 등급 + 등급 설명 상수를 싣는다(`VERIFIED_EXPLANATION` 등). CUE SHEET 근거 칸과 **같은 정보 반복**이다.
  - 설계안 B(원천 신설): 컨셉 파이프라인이 행을 만들 때 그 행을 고른 규칙 이름을 싣는다(예: 「후렴 앞 빌드업 규칙(G8)」·「피날레 새 축(G4)」). `build_song` → `SongBuild.table` 행에 `rule` 필드를 더하는 일이다. 규칙 이름은 게이트 이름과 같은 출처라 지어낸 문장이 아니다.
- **바꾸려면**: 편집 기능(`override_look.py`, `cue_sheet_edit.py`, 채팅 도구)은 있지만 안내 문장 원천이 없다.
  - 설계안: 행 종류(kind)마다 실제로 그 값을 바꿀 수 있는 화면 위치를 가리킨다(예: 색 → CUE SHEET 색 칸 편집 / 순서 → PLAN CUE 수정 요청). 가리키는 대상이 실제 UI 동작이어야 하므로, 동작이 있는 kind 만 채우고 나머지는 빈칸으로 둔다.
- **불릿 클릭 4칸**: 불릿은 감독의 Q1 원문이라 「무슨 뜻」·「왜」는 감독 본인의 말이다. 앱이 풀어 쓰면 REQ-032(요약·윤문 금지)와 부딪힌다. 「바꾸려면」만 사실로 채울 수 있다(출처가 `free_text`/`option`/`pre_specified` → "인터뷰 Q1 다시 답하기"). **제안: 불릿 4칸은 「바꾸려면」 하나만 채우고 나머지는 사유와 함께 비워 둔다.** 아니면 REQ-079의 "불릿 클릭" 조항 자체를 감독에게 다시 묻는다.

## 3. 탭 2 「이 곡의 재료」

- `sections[]` 의 `position`·`movement`·`texture`·`start_ms`/`end_ms` 는 실제 곡 경로에서 채워진다(`server/web/session.py:1685-1686`). `ConceptPanel` 도 이미 `sections` prop 으로 받는다.
- 하지만 **움직임**은 탭 1 표 「움직임」 칸(`runbookM7.ts` `grammarRows` → `movement ?? position`)이 쓰고 있다. **시작–끝**은 CUE SHEET 시각 칸·타임라인이 쓰고 있다. 구간마다 늘어놓으면 같은 값을 세 번째로 반복하게 된다.
- **감정(mood)**: `protocol.ts:346` 에 필드는 있지만 `session.py:1503` 이 "못 채우는 것: `mood`"라고 적어 두었다 → 원천 없음.
- **제안**: 탭 2를 구간 나열이 아니라 **곡 전체 재료 요약**으로 만든다. 예: 공간 = 곡에 쓰인 포지션 집합 + 처음 나오는 구간, 질감 = `texture` 분포(스냅 N구간 / 페이드 M구간) + Q5 답(곡 단위, `texture_source`), 시작–끝 = 첫 구간 → 마지막 구간의 색·밝기. 모두 `sections` 에서 계산하고 상수 문장은 쓰지 않는다. 감정은 빈칸 + 사유. 이 요약 방식이 탭 2의 의도("색 외 재료")와 맞는지 리드 확인이 필요하다.

## 4. 탭 3 「지키는 것·하지 않는 것·아껴 두는 것」

- **아껴 두는 것** ← `concept_report.reserve`(`session_bridge.py:261-287`): 그룹(BLIND·STROBE) + 유보색과 각각의 해제 큐(`released_q`). 이미 `SongTimeline.tsx:371`·`cueRequestWarnings.ts` 가 쓰고 있다. 탭 3에는 "무엇을 · 언제 처음 푸나(Q###)"로 싣는다. 곡 데이터에서 나온 값이다. **주의**: 그룹 이름 `("BLIND", "STROBE")` 는 서버 상수(`_RESERVE_GROUPS`, t461)이고, 리그에 그 그룹이 없으면 `released_q` 가 None 이 된다. 이 카드가 새로 만드는 상수는 아니지만 표시할 때는 "이 리그에 없음"과 "아직 안 풂"을 가를 수 없다(둘 다 None).
- **지키는 것·하지 않는 것** ← `concept_report.gates`(13개, `gates.py:701-715`): 이름이 곧 규칙이다(예: 「G7 후렴 주색 동일」=지킴, 「G12 MIB: 켜진 채 이동 0」=금지). 통과/실패/n/a 와 detail 은 곡 데이터에서 나온다. 다만 (1) 13개를 지킴/금지로 나누는 분류표가 새로 필요하고(설계 판단), (2) `RunbookGateBar.tsx` 가 같은 13개를 이미 보여 준다(반복).
  - 설계안: 분류표는 UI 상수로 둔다(게이트 이름 → 지킴|금지). 탭 3에는 판정 결과가 아니라 **규칙과 이 곡의 근거(detail)**를 싣고, n/a 게이트는 「이 곡엔 해당 없음」으로 묶는다. 게이트 바는 "통과했나", 탭 3은 "무엇을 지키나"로 관점을 나눈다.

## 5. 안 잰 것

- 각 원천 값이 실제 세션 페이로드에서 비어 있지 않은지는 아직 돌려 보지 않았다(t485 `make_payload.py` 같은 실측 전). 위 판정은 코드 경로 읽기와 grep 근거다 — 구현 단계에서 실제 세션 페이로드로 다시 잰다.
- 조사 일부(인터뷰 질문 목록·`mood` 미충전·`session.py:1685`)는 읽기 전용 조사 에이전트 보고를 근거로 했다. 직접 다시 확인한 것은 `reserve`/`gates` 생산자(`session_bridge.py:255-300,385-410`), 게이트 이름(`gates.py:701-715`), `evidence` 생산·소비(`session_bridge.py:240`, `runbookM7.ts:221`), `mood` 미충전 선언(`session.py:1503`), UI 타입(`protocol.ts:890-925`), `ConceptPanel.tsx` 전체다.

## 6. 리드 결정 요청

1. ① 「그래서 보이는 것」: (가) 사유만 바꾸고 비워 둠 / (나) 인터뷰 구간 질문 신설(감독 결정).
2. ② 4칸: 무슨 뜻 = GLOSSARY 신설 OK? · 왜 = A(등급 배선) 또는 B(행 규칙 이름 신설) · 바꾸려면 = kind별 실제 편집 위치 · 불릿 4칸 = 「바꾸려면」만 채움.
3. ③ 탭 2 = 곡 전체 재료 요약(감정 빈칸) OK?
4. ④ 탭 3 = reserve 배선 + 게이트 지킴/금지 분류표(UI 상수) OK?

승인한 항목부터 구현하고, 각 항목은 실제 세션 페이로드 + 브라우저로 잰다.

---

## 7. 구현 (리드 결정 2026-10-12 반영)

리드 결정: ① (가) 사유만 · ② 「바꾸려면」만(경로가 코드에 실재하는 것만) · ③ 곡 단위 집계, 감정은 빈칸 · ④ reserve 배선, 게이트 분류표는 안 함. 원칙: 다른 칸 값 반복 금지(REQ-097), 원천 없는 내용 짓기 금지.

### 판정

- **AC-018 잔여 3건: 원천이 있는 자리는 채움(PASS), 원천이 없는 자리는 사유를 보이며 비움.** 남은 빈 칸(「그래서 보이는 것」·무슨 뜻·왜·감정·지킴/금지)은 화면에 사유가 보인다. 원천 신설(인터뷰 구간 질문)은 감독 결정이며 리드가 따로 묻는다.

### 바뀐 코드

- `ui/src/components/conceptTabs.ts`(신규) — 순수 함수.
  - `OUTCOME_NO_SOURCE` = 「구간별 원천 없음 — 인터뷰가 곡 단위」. 칸에는 「데이터 없음」만 쓰고, 사유는 **표 아래 한 번만** 쓴다(행마다 같은 문장을 반복하지 않는다).
  - `changeGuideText(section, status)` — PLAN CUE(콘솔 저장 전)면 「타임라인 Q### PLAN CUE 카드 → 수정요청 생성기(…)」. 생성기는 `SongTimeline.tsx` 에서 `!onConsole && onGeneratorSend` 일 때만 열리고(`onConsole = stored|verified`), 앱이 `onGeneratorSend` 를 넘긴다(`App.tsx:1250` → `RunbookMode.tsx:252`). 저장·검증된 큐는 데이터 없음 + 사유.
  - `materialSummary(sections)` — 탭 2. 감정(데이터 없음 — `session.py:1503` "못 채우는 것: mood") · 공간(값별 구간 수) · 움직임 · 질감(값별 구간 수) · 시작–끝(이웃 구간 사이에서 공간·질감이 바뀐 횟수). 구간 라벨을 늘어놓지 않는다.
  - **찾은 것 — 움직임 = 포지션.** 서버 `movement` 는 `cue.position.stored or cue.position.requested`(`session.py:1539`)라서 「공간」과 같은 축이다. 실측 페이로드에서 10/10 구간이 같았다(`panel_probe.json` `movement_equals_position: true`). 그래서 모든 구간에서 같으면 「움직임」은 데이터 없음 + 「포지션 프리셋과 같다(공간에서 셌다)」로 두고, 다른 구간이 하나라도 있을 때만 따로 센다.
  - `grammarView(report, sections)` — 탭 3 「아껴 두는 것」. `concept_report.reserve` 를 그대로 쓴다. 해제 위치는 `screen_position` → 그 구간의 `Q###` + 라벨이다(`released_q` 는 컨셉 행 번호라 쓰지 않는다 — `cueRequestWarnings.reserveLock` 과 같은 규칙). `released_q` 가 null 이면 「미해제 — 해제 큐를 찾지 못했다」. 서버가 "한 번도 안 켜짐"과 "입력 색 없음"을 둘 다 null 로 내므로 이유를 짓지 않는다. 「지키는 것·하지 않는 것」은 데이터 없음 + 「규칙별 지킴/금지 분류 원천이 없다 — 규칙 판정은 게이트 바」.
- `ui/src/components/conceptGlance.ts` — `explanationCells(report, position, changeGuide?)` 에 세 번째 인자를 추가했다(추가만, 기존 호출은 그대로).
- `ui/src/components/ConceptPanel.tsx` — 위 셋을 그린다. 4칸은 `sectionPlanStatus(section, timeline.lifecycle)` 로 상태를 읽는다(타임라인이 없으면 「바꾸려면」도 데이터 없음).
- `ui/src/styles.css` — `.concept-materials`·`.concept-reserve`·`.concept-grammar-note` 몇 줄.
- **불릿 클릭 4칸은 붙이지 않았다.** 「Q1 다시」 재시작은 인터뷰 루프 안(`session.py:8069-8074` `_song_run_interview`)에서만 확인됐고, 타임라인이 나온 뒤의 경로는 확인하지 못했다 — "경로가 코드에 실재하는 것만" 조건을 채우지 못한다.

### 증거

| 항목 | 명령 | 결과 | 원본 |
|---|---|---|---|
| UI 범위 | `npx vitest run src/components/conceptTabs.test.ts src/components/conceptGlance.test.ts` | 26 passed | `vitest_scope.txt` |
| UI 전체 | `npx vitest run`(하니스 지운 뒤) | **59 파일 · 1262 passed** | `vitest_full.txt` |
| 타입 | `npx tsc --noEmit -p ui` | 오류 0(exit 0) | `tsc.txt` |
| 가드 변이 | `uv run python .moai/reports/t492/mutate.py` | **6/6 CAUGHT**(첫 실행은 5/6 — U2 가 살아남아 픽스처를 구간 10개로 늘림) | `mutation.txt` |
| 실제 세션 페이로드 ① | `uv run python .moai/reports/t492/make_payload.py`(인터뷰부터, 가짜 콘솔) | 컨셉 리포트 `available: false`(「BPM이 선언되지 않았다」) | `payload_causal.json` |
| 서버 실경로 페이로드 ② | `uv run python .moai/reports/t492/make_roles_payload.py`(`_song_timeline_payload`, 10구간) | 리포트 있음, reserve BLIND(screen_position 8)·STROBE(null) | `payload_roles.json` |
| 브라우저 | `panel_probe.js`(헤드리스 Chrome 1600×1000, vite :5492, 하니스 `acuiHarness.tsx.txt`) | 「그래서 보이는 것」 칸 10/10 「데이터 없음」 + 표 아래 사유 1줄 · Intro 4칸 「바꾸려면」=「타임라인 Q101 PLAN CUE 카드 → …」, 같은 화면에 생성기 카드 10개 · 탭 2 = 감정 사유 / 「Center 10구간」 / 움직임 사유 / 「long fade 10구간」 / 「구간 경계 9곳 중 공간 바뀜 0번 · 질감 바뀜 0번」 · 탭 3 = 「BLIND 그룹 — Q109 Chorus 3 에서 처음 푼다」(서버 screen_position 8 → Q109 Chorus 3 과 일치) · 「STROBE 그룹 — 미해제 — 해제 큐를 찾지 못했다」 · 페이로드 ① 의 탭 3 은 서버 사유 그대로 · 페이지 오류 0/0 | `panel_probe.json`, `panel_tab1.png`·`panel_tab2.png`·`panel_tab3.png` |

변이별로 잡은 시험:

| 변이 | 잡은 시험 |
|---|---|
| U1 저장된 큐에도 생성기를 가리킴 | `콘솔에 저장·검증된 큐는 생성기가 열리지 않으므로…` |
| U2 해제 위치를 released_q(행 번호)로 읽음 | `해제 위치는 screen_position 의 구간 큐 번호다…` |
| U3 움직임=포지션이어도 따로 셈 | `움직임이 모든 구간에서 포지션과 같으면…` |
| U4 4칸이 「바꾸려면」 문장을 무시 | `explanationCells 에 넘기면 「바꾸려면」 칸만 바뀌고…` |
| U5 해제 못 찾음에 이유를 지어냄 | `released_q 가 null 이면 이유를 지어내지 않고 미해제` |
| U6 시작–끝이 빈 값 경계도 셈 | `시작–끝은 이웃 구간 사이에서 재료가 바뀐 횟수다…` |

### 안 잰 것

- `ConceptPanel.tsx` 배선(4칸에 `changeGuideText` 를 넘기는 줄, 탭 2·3 렌더)을 끊는 변이는 단위 시험이 못 잡는다. 이 프로젝트에는 DOM 시험 하니스가 없다. 배선은 브라우저 실측(`panel_probe.json`)으로만 확인했다.
- 실측한 곡 둘 다 테스트 자료다(인터뷰 하니스 곡 · t482 의 10구간 곡). 10구간 곡은 포지션·질감이 전 구간 같아서 탭 2 집계가 단조롭다. 값이 섞인 곡의 화면은 단위 시험(`Center 2구간 · Fan 1구간 · 값 없음 1구간`)으로만 쟀다.
- 저장·검증된(stored/verified) 큐의 「바꾸려면」 화면은 브라우저로 보지 않았다(두 페이로드 모두 draft). 단위 시험만 있다.
- 앱 본체(App + 웹소켓)가 아니라 하니스로 띄웠다. 좁은 화면은 재지 않았다.
- 서버 코드는 바꾸지 않았으므로 pytest 는 돌리지 않았다(CI 가 전체를 돈다).
