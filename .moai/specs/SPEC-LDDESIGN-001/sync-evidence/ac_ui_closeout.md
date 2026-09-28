# SPEC-LDDESIGN-001 — 화면 쪽 AC 마무리 (ac-ui)

- 워크트리: `.claude/worktrees/ac-ui`, 브랜치 `WT-lddesign-ac-ui`, 기준 HEAD `30f02eb5`(= `origin/main`, PR #529 머지)
- 콘솔 접속 0회. 서버는 띄우지 않았고, 서버 함수 `_song_timeline_payload` 를 직접 호출해 만든 페이로드로 화면을 그렸다.
- 증거 폴더: `sync-evidence/ac_ui/` (아래 표의 경로는 모두 이 폴더 기준)
- 대상: 분류표(`ac_evidence_map.md`)의 "PASS-test(미실행)" 14건 + AC-051 + UNVERIFIED 3건(AC-020·039·041) + 부분 미검증 AC-040

## 1. 결론 먼저

| 판정 | 개수 | AC |
|---|---|---|
| PASS (브라우저 또는 실행으로 확인) | 14 | 019, 020, 034, 036, 039, 041, 042, 043, 050, 051, 052, 053, 035†, 038† |
| PASS — SPEC 문면과 구현이 다름, 소유자 확인 필요 | 1 | 044 |
| **FAIL** | 4 | **018**(일부), **037**, **040**(일부), **049** |

† 035·038 은 조건 하나가 이 페이로드로는 발생하지 않아 단위 시험으로만 확인했다(§3 참조).

AC 표 밖의 결함 하나: **PLAN CUE 카드 안 생성기 버튼 6/26 개가 옆 카드에 덮여 마우스로 눌리지 않는다**(§4).

## 2. 무엇을 돌렸나

| # | 명령 | 결과 | 원본 |
|---|---|---|---|
| 1 | `npm ci` 후 `npx vitest run --reporter=verbose` (ui/) | 31 파일 · **710 passed**, 실패 0 | `vitest_full.txt` |
| 2 | `uv run pytest -v server/tests/test_plan_cue_generator_vocabulary_t460.py test_cue_sheet_edit_vocab_t466.py test_cue_sheet_edit_group_scope_t461.py` | **62 passed** | `pytest_ac039.txt` |
| 3 | `uv run python make_payload.py` — 36구간·구간마다 다른 색(blue/red/amber/green/magenta/cyan), 120 BPM | concept_report `available: True`, `row_pairing.available: True`, 행 49개 | `payload_36.json` |
| 4 | vite dev + 헤드리스 Chrome(playwright 1.63, 1600×1000) — 하니스가 `RunbookMode` 를 App 과 같은 prop 으로 띄우고, 서버로 나가는 호출을 `window.__calls` 에 기록 | 페이지 오류 0 | `ac_ui_browser.js`, `ac_ui_browser_result.json`, 캡처 `01~05_*.png`, 하니스 사본 `acuiHarness.tsx.txt` |
| 5 | `npx vite build --outDir <임시>` + `static_checks.sh` | build exit 0 | `ac051_ac019_static.txt` |
| 6 | `npx tsc --noEmit` | 오류 1건 — 임시 하니스 파일의 미사용 import 뿐(제품 코드 0건). 하니스는 측정 뒤 `ui/` 에서 지웠다 | — |

하니스는 `ui/` 안에 임시로만 두었고 커밋하지 않았다(사본만 증거 폴더에 `.txt` 로). 프리셋 풀 API(`/api/presets/N`)만 가짜 응답으로 가로챘다.

## 3. AC별 판정

| AC | 판정 | 근거(잰 값) |
|---|---|---|
| 018 | **FAIL(일부)** | PASS: 블록 순서 `runbook-header → concept-panel → cue-sheet-timeline(타임라인 → CUE SHEET) → song-timeline(PLAN CUE) → runbook-gate`, 패널 기본 `open=false`, 6칸 표 헤더 일치·앞 5칸 실제 값(`Intro · blue · KEY 70 / BACK 56 · Center · —`). **FAIL: ① 인과 불릿이 「데이터 없음 — 워크시트 concept 원문이 서버에서 오지 않는다」 ② 6번째 칸 「그래서 보이는 것」 이 전 행 「데이터 없음」 ③ 항목 클릭 4칸 설명이 없다 — 펼친 패널에서 탭 외 클릭 가능한 요소 0개, 4칸 제목 문자열 0개.** 원인: 서버 `concept_report` 키가 `available·gates·mib·lint_*·energy_report_count·rows·row_pairing·reserve` 뿐이다(`server/concept/session_bridge.py:265-278`). `ConceptPanel.tsx:6-9` 주석이 같은 사실을 적고 있다. 이 원천을 맡은 열린 카드는 없다(t455·t456 은 행·색만 채우고 닫힘). REQ-086(메인 화면 불변)은 이번에 재지 않았다 |
| 019 | PASS | 36큐 전부 타임라인 칩 = CUE SHEET 첫 칸 = PLAN CUE 배지(`chips_eq_rows: true`, `chips_eq_badges: true`). 헤더 정확히 14열 `Q# · 구간 · 회차 · Trigger · 시각 · 색 · 밝기 · 기구 그룹 · 움직임 · 효과 · Fade · MIB · Track 예외 · 근거 등급`, 제거된 5열 없음. 행 왼쪽 레일 `border-left: 7px` 색이 구간 HEX 와 같다(예 Q102 `rgb(255,0,0)` = `#FF0000`). `TRANS_VALUES=('SNAP','XFADE','FADE')`, `EDITABLE_FIELD_LABELS['trans']='전환'` |
| 020 | PASS | CUE SHEET 에 휠 12번 → `scrollTop 0→830`, 화면 중앙 행 2→32, 타임라인 레일 `scrollLeft 0→3219`, 중앙 행(32)의 칩이 레일 화면 안에 있음(`true`). 블록 색 36/36 이 `palette_primary_hex` 와 일치. 상태줄 `GATE ✓ 통과 9 ✕ 실패 4 – 해당없음 0 ! 경고 · 데이터 없음`. (AC 예시곡 Too Cool 이 아니라 36큐 합성곡) |
| 034 | PASS | `onGeneratorSend` 가 있으면 생성기 36개, 없으면(`runbook-preview.html`) 0개 |
| 035 | PASS† | KEY 70 / BACK 56 두 그룹 선택 → 「현재 혼합」. 색 「혼합 2색」은 이 페이로드에 보조색이 없어(`palette_secondary` null) 발생하지 않음 → vitest `cueRequestSentence.test.ts` 혼합 색 시험으로만 확인 |
| 036 | PASS | 딤머 풀 팝업에 `1.18 Dim 90` / `Dim 90 Warm` → 첫째 선택 뒤 딤머 행 「1.18 Dim 90」. "컬러·딤머는 선택 그룹에만, 포지션·이펙트·페이저는 큐 전체" 적용 범위는 재지 않았다 |
| 037 | **FAIL** | 서버 reserve: `BLIND released_q=45, screen_position=33`. 45 는 컨셉 **행 번호**(행 49개 중 45번째, 화면 구간 33 = 큐 134)인데 생성기는 이를 **구간 큐 번호**와 비교한다(`PlanCueRequestGenerator.tsx:101-108` `cueNumber < item.released_q`, `cueNumber = section.cue_number`). 이 곡의 큐는 101~136 이라 `101 < 45` 가 거짓 → **어느 카드에서도 잠기지 않는다**. 브라우저(`?blind` — 각 구간에 BLIND 칩만 덧붙이고 reserve 는 서버 값 그대로): 카드 0·3·31~35 전부 `locked: false`, 해제 전인 카드 3(Q104)에서 BLIND 클릭 → `aria-pressed=true`. 기대는 카드 0~32 잠금. 반대로 실제 앱처럼 큐 번호가 1부터면 행 수(49)가 구간 수(36)보다 많아 해제 뒤에도 잠긴 채로 남는다 — 어느 쪽이든 두 번호 체계가 섞였다. 추가: 서버 페이로드 그대로는 BLIND 가 칩으로 나타나지도 않는다(구간 `intensity` 가 KEY·BACK 뿐) |
| 038 | PASS† | 밝기+색 두 줄 → 「바꾼 것 2 — 코파일럿 확인 대기」, 줄마다 `~ KEY 밝기 70% → 95%` / `~ KEY 컬러 green → Red`, 줄 밖 경고 0. 전송 직후 라벨 그대로 「확인 대기」, 줄 상태 `requested/selected` → 첫 수락 뒤 `applied/requested`(3상태 구분). 경고가 색 줄에만 붙는 경우는 이 페이로드에서 경고 조건이 안 생겨 관찰 못 함 → vitest 경고 병기 시험으로만 |
| 039 | PASS | pytest 62 passed — 생성기 TS 빌더와 같은 fixture(`cueRequestSentences.json`, 9조작)를 실제 `parse_cue_sheet_edit_request` 에 통과시켜 `changes` 일치. 정적: 서버에서 `apply_cue_sheet_edit` 호출은 `server/web/session.py:9626` 한 곳이고 인자는 파서 결과 `request["changes"]`. UI 생성기 3파일에 `apply_cue_sheet_edit`·`changes:` 0건 |
| 040 | **FAIL(일부)** | 6종 중 4종만 구현(`cueRequestWarnings.ts:1-5` — 팬 폭·페이저=BPM 은 2026-09-27 감독 결정 D3·카드 t467 n/a 로 꺼둠). 재사용 3종은 서버 필드를 그대로 읽는다(`unused_groups`·`mib`·`reserve`, 재계산 코드 없음 — 코드 검사). 단 리저브 경고는 AC-037 과 같은 비교(`cueRequestWarnings.ts:47`)라 같은 결함을 갖는다 |
| 041 | PASS | 전송 문장: 「큐 104 KEY 밝기 95%로 바꿔줘」, 「큐 104 KEY 컬러 Red로 바꿔줘 그리고 이 구간 전체를 반 박자 당겨줘」. 경로: `App.tsx:626-631` `sendGeneratorRequest → sendChat`, `useCopilotSocket.ts:343-348` 이 손입력과 같은 `dispatch({kind:"user"})` + `buildChat`. 채팅 뷰 자체의 렌더는 하니스에 없어 캡처하지 않았다(코드 경로로만) |
| 042 | PASS | 4줄 쌓은 뒤 「선택 취소」 → 나간 호출 0건, `timeline_draft_undo` 0건 |
| 043 | PASS | 스택이 찬 상태에서 「되돌리기」를 포함한 버튼은 `↶ 되돌리기` 하나 |
| 044 | PASS — 문면 확인 필요 | 2줄 전송·수락 뒤 스택 비움, 배지 「되돌리기 2단계」(전: 없음=0). 생성기가 줄마다 한 문장씩 보내므로 N줄이면 +N 이다. AC 문면은 "N개 항목 수락 → +1". N=1 이면 일치, N≥2 면 문면과 다르다 |
| 049 | **FAIL** | 「한눈에」 5단계 카드가 그려지지 않는다 — 「데이터 없음 — 단계 배정 원천이 서버에 없다」(`ConceptPanel.tsx:39-42`). 하드코딩이 없는 건 맞지만 카드 자체가 없다. 원천 담당 카드 없음(AC-018 과 같은 뿌리) |
| 050 | PASS | 탭 라벨 정확히 `이 곡의 연출` / `이 곡의 재료` / `지키는 것·하지 않는 것·아껴 두는 것`, 영어는 `<small>` 11px (라벨 13px) |
| 051 | PASS | 빌드 산출물 폰트 파일 0, 폰트 CDN·`@font-face` 0, CSS 의 `tabular-nums` 14곳. vitest REQ-099 5건(`.cst-sheet`·`.song-timeline-section`·`.cst-tick span` tabular-nums, 웹폰트 0) 통과 |
| 052 | PASS | 4줄 중 2번째 ✕ → 나머지 3줄 유지, 이후 「선택 취소」 → 0줄 |
| 053 | PASS | 자유 입력이 마지막 문장 끝에 그대로 붙음(위 AC-041 둘째 문장). 서버에서는 같은 채팅 문장이 `session.py:9609` 파서로 간다 |

## 4. AC 밖에서 나온 결함 — 생성기 버튼이 눌리지 않는다

1600×1000 에서 PLAN CUE 카드(`article`) 폭은 130px 인데 생성기 내용 폭은 248px(`scrollWidth`)이다. 넘친 부분이 오른쪽 카드 밑으로 들어가, 카드 3(Q104)의 버튼 26개 중 **6개(`적용`, `FADE`, `Cue Only`, `Release`, `mark`, `live`)가 옆 카드 「00:20 Verse 2」에 덮여 있다**(버튼 중앙 좌표의 `elementFromPoint` 가 옆 카드). playwright 의 실제 마우스 클릭이 30초 동안 막혀 실패했고, 이후 조작은 클릭 이벤트를 요소에 직접 보내 진행했다. 캡처 `05_card3_overlap.png`. AC-034~053 의 기능은 동작하지만 감독이 마우스로 쓸 수 없는 버튼이 있다. t460·t470 판정서 모두 "브라우저에서 눌러 보지 않았다"를 미검증으로 남겼던 자리다.

## 5. 안 잰 것

- 앱 본체(App + 웹소켓 + 서버)가 아니라 하니스로 띄웠다. 수락은 서버 대신 하니스가 `draft.depth+1` 을 넣어 흉내 냈다. 채팅 뷰 렌더는 보지 않았다.
- 페이로드는 시험 도우미(`_section`/`_plan`)로 만든 합성곡 하나다. 실제 감독 곡·Too Cool 은 아니다.
- 생성기 조작은 카드 3 하나에서만 했다. 뷰포트는 1600×1000 하나뿐이다(더 넓은 화면에서 겹침이 풀리는지 안 쟀다).
- 프리셋 풀은 가짜 응답이다. AC-036 의 적용 범위(그룹/큐 전체)는 안 쟀다.
- AC-018 REQ-086(메인 화면 컴포넌트 불변·값 일치)은 이번에 재지 않았다.
- AC-037 의 번호 체계 불일치를 실제 앱 번호(1부터)로는 띄워 보지 않았다 — 위 서술의 "해제 뒤에도 잠긴다"는 코드와 숫자로 추론한 것이다.
- AC-035 색 혼합, AC-038 색 줄 경고는 브라우저에서 발생시키지 못했다(단위 시험만).

## 6. 후속 제안(카드 후보 — 리드 판단)

1. **AC-037/040 번호 체계** — `released_q`(컨셉 행 번호)를 구간 큐 번호와 비교하지 않도록. 서버가 이미 주는 `screen_position` 을 구간 위치와 비교하거나, 서버가 구간 큐 번호로 환산해 보내는 방향. 시험 픽스처가 두 번호를 같게 두면 이 결함을 못 잡는다.
2. **AC-018/049 원천** — 인과 불릿·「그래서 보이는 것」·「한눈에」 단계·4칸 설명을 서버가 내보내는 카드(열린 카드 없음).
3. **생성기 넘침** — PLAN CUE 카드 폭 130px 안에 생성기가 들어가지 않는다.
4. **AC-044 문면** — 줄마다 전송(+N)과 문면(+1) 중 어느 쪽이 맞는지 SPEC 소유자 확인.
