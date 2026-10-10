# SPEC-LDBEAT-001 — Progress

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-07
- 작성 카드: t522. 입력 출처는 `spec.md` HISTORY·`plan.md` §A/§G 참조.
- Tier: M (spec.md §0 근거) — REQ 14개·AC 13개 최초 작성(오케스트레이터 검토 D1~D3 교정 후에도 총량 불변), **카드 t526 개정(2026-10-10)으로 REQ 15개·AC 16개**로 변경 — Tier M 상한(각 16개) 이내, AC는 경계치.
- 플랜-오딧 전 자체 점검: SPEC ID 정규식 PASS(Bash 실행·출력 cite — 메인 작업 응답 참조), 프런트매터 12필드 schema 대조 완료, 기존 SPEC ID와 충돌 없음(`ls .moai/specs/` 확인), Out of Scope 섹션 6개 H3 하위헤딩 + `-` 불릿 포함(카드 t526 개정 뒤 7개로 증가, 아래 plan-amend 항목 참조).
- **오케스트레이터 검토 D1~D3 교정(2026-10-07, 같은 날 후속 커밋)**: D1(REQ-013/§5 — 콘솔 타임코드는 커맨드로 만들어진다는 실측, 장벽 A를 "해소"에서 "열린 결정"으로 되돌림), D2(REQ-007~009 — 기존 큐 레벨 파서가 격자를 커버한다는 주장 철회, 새 서버측 편집 연산 요구), D3(REQ-006 — `SongTimelineStore`/`TimelineDraftHistory`/`SongTimelineLibrary` 저장소 실체 인용 + M2 명시적 결정화). `.moai/reports/t522/verdict.md` §2(재측정 기록) 참조.
- **plan-amend(카드 t526, 2026-10-10)**: 입력 `reports/ldbeat-feasibility-roadmap-20261010.md`+`.html`·`reports/ldbeat-runbook-ui-proposal-20261008.html`·`reports/ldbeat-runbook-mockup-20261008.html`·`reports/ldbeat-plan-summary-20261008.md`·`.moai/reports/t525/verdict.md`. 코드 diff 0줄, 콘솔 접촉 0건. 바뀐 것: (1) 확정된 감독 결정 1~5 추가(spec.md § 확정된 감독 결정) — 열린 결정 0항(새 에미터) 해소. (2) REQ-LDBEAT-013 재교정 — `songcue.py:634,683`이 이미 타임코드 커맨드·영문화를 내고 있었다는 사실 반영, 진짜 틈은 `emit.py:51`의 재생 거부 + songcue의 1:1 시퀀스-타임코드 구조로 재정의. (3) 트랙 모양 교정 — "SCENE/BACK PULSE/…" → 콘솔 그룹 트랙 + 층 역할 이름표(REQ-LDBEAT-004). (4) 2D 무대를 콘솔 패치 기반으로 교정(t525 실측) + 응답기 그룹 소속 절단 실측 → M1에 응답기 긴 값 나눠 읽기 확장 추가(REQ-LDBEAT-002). (5) M1 미확인 항목 4개→9개(REQ-LDBEAT-001~003, AC-001/002/009). (6) REQ-LDBEAT-015(프리셋 아키텍처) + AC-LDBEAT-016 신설. (7) spec.md §4에 SPEC-LDBARMAP-001·SPEC-LDARRANGE-001(둘 다 미존재) 명시적 교차 참조 추가. **REQ 14→15개·AC 15→16개**(Tier M 상한 16개 이내, AC는 경계치). version 0.1.0→0.2.0, updated 2026-10-10. status는 draft 유지(완료 전 amend이므로 `amendment_of` 불필요 — completed→in-progress 전환 규칙과 무관).
- **plan-audit iteration 1 FAIL 대응(카드 t526, 같은 날 후속)**: `.moai/reports/t526/plan-audit.md` — Overall 0.85(통과선 0.80 이상이나 MP-2 필수통과 방화벽 FAIL로 집계 무효). D1~D3(GEARS-MIX, blocking) REQ-LDBEAT-004/005/011/012/013/015를 (a)(b)(c)… 라벨 하위 절로 재구조화, 모든 절에 굵은 GEARS 트리거 부여, 근거/권고 서술은 근거 칸으로 이동 — 새 REQ-ID 없음. D4~D6(TRACE-GAP, blocking) acceptance.md AC-LDBEAT-002/003을 하위 시나리오로 확장(새 AC-ID 없음, Tier M 상한 16/16 유지) — REQ-004(h) 겹침 금지·REQ-005(b) 재생±10초/음원동기·REQ-012(b) 미리보기 세션반복을 정식 Given/When/Then으로 승격. D7(UNVERIFIED-UI, blocking, 핵심) REQ-LDBEAT-004(b) "모드 전환 버튼(타임라인↔상세)"이 입력 보고서에 없는 지어낸 사실이었음을 확인 — `reports/ldbeat-runbook-ui-proposal-20261008.html:495,504,519`(큐 편집 칸 내부 "전환" 토글, 큐 편집 ↔ 들어오는-전환 편집)로 교정, `:155,376,196-200,238`도 재검증. D8(optional) REQ-LDBEAT-009 Where→When. D9(optional) 보류. REQ/AC 총량 불변(15/16) — 재구조화·교정뿐, ID 추가삭제 없음.
- **plan-audit iteration 2 FAIL(0.875, 원인 교체) 대응(카드 t526, 같은 날 후속)**: D1~D8 전부 FIXED 재확인, D9 보류 수용. 15개 REQ 전수 재검사로 신규 발견: D10(REQ-LDBEAT-002, D1과 동형 GEARS-MIX) — (a)(b)(c) 라벨 하위 절로 재구조화(새 REQ-ID 없음). D11(REQ-002(c) 응답기 확장의 TRACE-GAP) — AC-LDBEAT-009에 (b) 하위 시나리오 추가(새 AC-ID 없음, t525 §② 절단 실측을 Given으로 인용). REQ/AC 총량 불변(15/16).
- **plan-audit 최종 판정(카드 t526, 2026-10-10): PASS-with-fix — 리드 직접 확인.** 3회차 FAIL 은 필수 기준 7개 전부 PASS/N/A 이고 남은 결함 D12(AC-LDBEAT-009(b) 「각 8대」, 잰 적 없는 숫자) 한 문장뿐이었다. 레인이 `.moai/reports/t525/verdict.md:130`(전체 개수 미측정)으로 고쳤고, 리드가 고친 문장이 출처와 일치함을 직접 확인해 수용했다. 4회차 감사는 돌리지 않았다 — plan-auditor Retry Loop 상한 3회 도달, 남은 수정이 한 문장이라 리드 확인으로 대체(`.moai/reports/t526/plan-audit.md` 말미).

## 저장 키 맞춤 (카드 t529, 2026-10-10)

- ③ 저장 키 맞춤(t529 후속, 2026-10-10): §5 열린 결정에 세 SPEC 공통 권고 키 `timeline["beat_grid"]`/`["bar_map"]`/`["arrangement_draft"]` 추가. 권고뿐 — REQ·AC·plan.md·acceptance.md 변경 0, plan-audit 재실행 없음.

## §E.2 Run-phase Evidence

_<run-phase 대기 — manager-develop 착수 전까지 비어 있음>_

### M1 — 콘솔 확인 프로브 + 응답기 나눠 읽기 (카드 t531, lane-3, 브랜치 `WT-ldbeat-m1`)

기준 `b52512ee`(origin/main, ed740c12 이후). 측정일 2026-10-10. 실기 쓰기 0건.

**응답기 1.6.6 (REQ-LDBEAT-002(c), AC-LDBEAT-009(b))**

- `82d2b877` — `props <id> <Name> <path> offset=<n>` 엔트리 단위 나눠 읽기. 응답 전체가 `max_payload`(1900) 안에 들도록 엔트리를 담고 `offset`·`total`·`truncated` 를 붙인다. 토큰 없는 요청은 1.6.5 와 바이트 동일.
- `fef93ed6` — `EXPECTED_RESPONDER_VERSION` 1.6.5→1.6.6, console/lua 지문 재고정.
- 오프라인 증거: `uv run --quiet pytest server/ -q` → `14555 passed, 35 skipped` @ `fef93ed6` (`.moai/state/verify/t531/full_suite_fef93ed6.txt`). 86개 배열을 나눠 읽어 다시 맞추면 86개 전부 돌아온다(`server/tests/test_lua_responder_props_paging.py`).
- 실기: **미배치.** `ping` → `1.6.5` (2026-10-10). 배치는 감독 붙여넣기(t104 실측: 재임포트는 OK 를 받고도 안 바뀜). `group_members.py` 는 1.6.5 에서 실행 거부(`.moai/reports/t531/group_members_refusal.txt`). AC-LDBEAT-009(b) 는 **미실행**.
- 🔴 이 브랜치를 콘솔 1.6.6 배치 전에 main 에 머지하면 게이트가 모든 새 실행을 막는다(`server/safety/gate.py:675`, 버전 불일치).

**프로브 9항목 (REQ-LDBEAT-001~003)** — 설계 `.moai/reports/t531/probe-design.md`, 커밋 `abdd407d`

| 항목 | 프로브 | 가짜 콘솔 리허설 | 실기 전부-거절 | 실기 실행 | 판정 |
|---|---|---|---|---|---|
| ① 타임코드 트랙 ≥3(목표 6) | `p1_tc_tracks.py` (TC 30) | exit 0, 막힌 줄 0 | 미실행 | 미실행 | **미실행** |
| ② Goto 2번 이후·여러 시퀀스 동시 | `p2_goto_multi.py` (쓰기 0) | exit 0 | 미실행 | 미실행 | **미실행** |
| ③ 프리셋 수정 전파 | `p3_preset_propagation.py` (4.301, 시퀀스 300) | exit 0 | 미실행 | 미실행 | **미실행** |
| ④ 효과 프리셋의 SM15·Measure | `p4_effect_speedmaster_measure.py` (21.301, 시퀀스 301) | exit 0 | 미실행 | 미실행 | **미실행** |
| ⑤ 위치 프리셋 위 상대값 | `p5_relative_on_position_preset.py` (시퀀스 302) | exit 0 | 미실행 | 미실행 | **미실행** |
| ⑥ 타임코드 중간 재생 | `p6_mid_start.py` (TC 31) | exit 0 | 미실행 | 미실행 | **미실행** |
| ⑦ 큐 하나 그룹 하나 + Step 2 | `p7_single_selection_step2.py` (시퀀스 303, 대조 큐 포함) | exit 0 | 미실행 | 미실행 | **미실행** |
| ⑧ 같은 그룹 두 시퀀스 분담 | `p8_shared_group_two_sequences.py` (시퀀스 304·305) | exit 0 | 미실행 | 미실행 | **미실행** |
| ⑨ circle·발리후 | `p9_shapes.py` (시퀀스 306~308) | exit 0 | 미실행 | 미실행 | **미실행** |

- 새 번호 비어 있음 실측: `.moai/reports/t531/r1_free_slots.txt`(실기 읽기). 실행 직전에 다시 읽는다.
- 실기 쇼 상태(읽기): 시퀀스 1-15·210·219·220-233·1999·2000, 타임코드 1·2·7·8·9·19·20·21 — t520 기록의 시퀀스 250번대·TC 22/23 은 없다(`r0_pools.txt`·`r0b_pools.txt`). Speed15 `NORMEDVALUE` 69.
- 리허설은 게이트 심사만 증명한다 — 가짜 콘솔은 명령의 콘솔 의미를 흉내 내지 않는다.
- 미측정 문법: ③ 프리셋 수정 줄, ⑥ `Goto Time 5 Timecode 31`(전례 0 — 거절은 「미확인 — 문법 불명」), ④·⑤·⑨ 그룹 선택 프리셋 호출.
- **9항목 모두 미실행이므로 REQ-LDBEAT-001 게이트상 M4 송신은 어떤 항목에도 기대지 못한다.**

### M2 — 박자 격자 화면 + 저장 (카드 t532, 브랜치 `WT-ldbeat-m2`)

기준 `46283183`(origin/main, M1 머지 뒤). 콘솔 접촉 0건 — 읽기·쓰기 모두 없음(새 응답기 verb·OSC·프로브 스크립트 실행 0건).

**저장소 결정(REQ-LDBEAT-006, 열린 결정 0', 이 마일스톤에서 확정)**: 권고안(기존 `timeline` 사전에 `beat_grid` 키로 임베드)을 **그대로 채택**했다 — 독립 저장소는 신설하지 않았다. 근거: `SongTimelineStore.latest`(`session.py:3521` setter)와 `TimelineDraftHistory.record`(`timeline_draft.py:52`)가 둘 다 **타임라인 전체 사전**을 다루는 generic 메커니즘이라, `beat_grid`를 그 사전의 새 키 하나로 심는 순간 — 코드 추가 없이 — atomic JSON 영속화(`SongTimelineStore`)와 되돌리기/다시하기(`TimelineDraftHistory`)를 모두 상속한다. 이것을 `server/tests/test_beat_grid_t532.py::TestStorageRoundTrip`로 직접 재서 확인했다(가정하지 않음) — 아래 §E 증거 참조.

**만든 것**:

- `server/design/beat_grid.py`(신설) — 콘솔 접촉 0인 순수 파이썬 모듈. `BeatGridTrack`/`BeatGridCue`/`BeatGridView` 타입, `default_beat_grid(song_title)`(LOVE ATTACK 첫 기본값 + 다른 곡 빈 상태), `attach_beat_grid_default(timeline)`(있으면 보존·없으면 기본값), `find_overlapping_group_tracks`/`validate_beat_grid_tracks`(REQ-LDBEAT-004(h) 겹침 검증 — M3 `apply_beat_grid_edit`가 재사용할 토대).
- `server/web/session.py` — `_song_timeline_payload`의 반환을 `attach_beat_grid_default(...)`로 감쌌다(한 줄 래핑, 1곳). 그 함수가 만드는 다른 칸은 전혀 건드리지 않았다(ADDITIVE).
- `ui/src/protocol.ts` — `BeatGridCue`/`BeatGridTrack`/`BeatGridView` 타입 + `SongTimelineView.beat_grid?` 선택 필드.
- `ui/src/components/BeatGrid.tsx`(신설) — 3단 상시-동시-표시 레이아웃(① 곡 전체 지도 ② 콘솔 그룹 트랙 × 마디 타임라인, 층 역할 폴더 접기/펴기 + 전역 토글 ③ 상세 창 — 2D 무대 + "이 마디 한눈에" 표). 막대 클릭 → 우측 큐 편집 칸(역할별 조건부 필드 힌트) + 헤더의 "전환" 토글(곡 첫 칸에서 비활성, title "곡 첫 큐 — 들어오는 전환 없음"). 하단 명령 입력 + 두 버튼(M3 배선 전까지 `disabled`). ±10초 스킵 + 음원 파일 입력(바·초 환산은 `barToSeconds`/`secondsToBar`, "음원 0초 = 앞박" 규칙 그대로). circle·발리후·위상 펼침 칸에 "⚠ 실기 미확인" 배지(REQ-LDBEAT-010). M1 프로브 9항목 상태표(기본 전부 "미실행") + 쓰기-잠김 배지(REQ-LDBEAT-001/003).
- `ui/src/components/RunbookMode.tsx` — `<BeatGrid>`를 `CueSheetTimeline`과 `SongTimeline` 사이에 삽입(기존 5블록 순서는 그대로, REQ-LDBEAT-004(g)). `beatGridFixtures`/`beatGridProbeResults` 선택 prop 추가(둘 다 안 넘기면 안전한 기본값으로 떨어짐).
- `ui/src/styles.css` — `.beat-grid-*` 규칙 블록 추가(기존 `--bg`/`--panel`/`--muted`/`--accent`/`--ok`/`--warn`/`--bad` 변수 재사용, 새 `@media` 0개 — `styles.test.ts`의 "정확히 1개" 단언 안 건드림).

**REQ/AC 진전(증거 포함)**:

| REQ/AC | 진전 | 증거 |
|---|---|---|
| REQ-LDBEAT-006 | 저장소 결정 확정 + 구현 | `uv run --quiet pytest server/tests/test_beat_grid_t532.py::TestStorageRoundTrip -q` → `2 passed`(`SongTimelineStore` 재시작 후 복원 + `TimelineDraftHistory.undo`가 깊은 사본으로 격자를 되돌리는지 직접 측정) |
| AC-LDBEAT-007 | LOVE ATTACK 외 곡은 강제 적용 없이 빈 상태 | `TestDefaultBeatGrid::test_a_different_song_gets_no_forced_default` PASS — `_song_timeline_payload`의 실제 배선까지(`TestSongTimelinePayloadWiring::test_another_song_payload_carries_the_empty_no_default_marker`) 통과 |
| AC-LDBEAT-008 | 곡 간 비오염 | `TestAttachBeatGridDefault::test_cross_song_edits_do_not_leak_ac_008` PASS(한 곡의 격자를 고쳐도 다른 곡 사전은 독립 객체라 안 바뀜을 직접 돌연변이로 확인) |
| REQ-LDBEAT-004(a)(g) | 콘솔 그룹 트랙 × 마디 격자 블록, 기존 5블록 순서 보존 | `git diff --stat` 참조(§ 검증) — `RunbookMode.tsx`에 `<BeatGrid>` 1곳만 삽입, 기존 5블록 호출부 문자열 그대로 |
| REQ-LDBEAT-004(h) | 겹치는 그룹 트랙 거절(단일-원인 사유) | `TestOverlapValidation`(5개 PASS) — `MOVER-ALL`+`MOVER-U` 거절, LOVE ATTACK 기본값 자체는 겹침 없이 통과 |
| REQ-LDBEAT-004(f) | 2D 무대는 콘솔 패치 좌표에서(손그림 아님), 확인된 그룹만 색 | `BeatGrid.test.tsx`의 `2D stage projection` describe(8개 PASS) + 헤드리스 캡처(아래) — STROBE(미확인)·KEY(비매칭)는 회색, BACK/SIDE-ALL/MOVER-U/MOVER-D/BLIND(확인)는 색 |
| REQ-LDBEAT-010/AC-LDBEAT-004 | 미확인 모양 배지 | `isUnconfirmedShapeCue` 4개 PASS + 캡처에서 MOVER-D "위상 펼침" 칸에 배지 실제 렌더 확인(육안) |
| REQ-LDBEAT-003 | M1 프로브 상태표(기본 미실행) | `buildProbeStatusTable`/`isWriteLocked` 4개 PASS — 캡처에서 9항목 전부 "미실행" + "⚠ 쓰기 잠김" 렌더 확인 |
| REQ-LDBEAT-005(a) | 0~25마디 7행 초기 범위 | `barRowIndex` 4개 PASS(배치 규칙서 §4 행 경계 그대로) |
| REQ-LDBEAT-005(b) | ±10초 + 음원 동기 환산 | `barToSeconds`/`secondsToBar`/`clampSkipSeconds` 9개 PASS |

**검증(§E 자체)**:

```
$ uv run --quiet pytest server/tests/test_beat_grid_t532.py -q
19 passed in 0.29s
$ uv run --quiet ruff check server/design/beat_grid.py server/web/session.py server/tests/test_beat_grid_t532.py
All checks passed!
$ cd ui && npx vitest run
Test Files  35 passed (35)
     Tests  776 passed (776)
$ cd ui && npx tsc --noEmit
(종료 코드 0, 출력 없음)
$ git diff --stat origin/main...HEAD -- ui/src/components/CueSheetTimeline.tsx server/director/emit.py server/looks/songcue.py server/design/cue_sheet_edit.py console/lua
(출력 없음 — 금지 파일 0 diff, AC-LDBEAT-012)
```

캡처: `.moai/reports/t532/beat_grid_love_attack_and_empty.png`(헤드리스 Chrome, esbuild로 `BeatGrid`만 번들한 일회성 하네스 — `ui/src/` 밖, 커밋 대상 아님. 재현: `.moai/reports/t532/capture.html` + `.moai/reports/t532/run_chrome.sh`, 번들은 `esbuild ui/src/components/BeatGrid.tsx`류 임시 엔트리로 재생성). LOVE ATTACK 기본값(6트랙·4폴더) + Sugar 빈 상태(0트랙) 둘 다 한 이미지에 라벨과 함께 담겼다.

**안 잰 것(정직하게 남김)**:

- **프리셋 번호대(REQ-LDBEAT-015)**: 실제 쇼 파일과 대조한 적 없다 — M2/M3 착수 시 쇼 파일 조회로 확정(§B 위험 11). 로드맵 예시 번호는 코드에 **하드코딩하지 않았다**.
- **STROBE 그룹 번호**: 이 plan-phase·t525 증거 어디에도 없다 — `group_no=None`, `group_no_confirmed=False`로 솔직하게 비워 뒀다. M1(미실행)이나 M3가 실제 쇼 파일로 채운다.
- **SCENE 트랙**: 배치 규칙서 §2가 "여럿(정적 값만)"이라 적어, "줄 하나 = 그룹 하나" 모양에 안 맞는다 — M2 기본값에서 **뺐다**(지어내지 않음). 어느 그룹으로 쪼갤지는 director 확인이 필요한 빈틈으로 남는다.
- **2D 무대 좌표의 실제 소스**: `read_spatial_fixtures`/`_spatial_read_budget`(`server/orchestrator/tools.py:1403,1527`)은 **콘솔 접촉 함수**라 M2(콘솔 0)에서 부를 수 없다. `BeatGrid`는 `fixtures` prop으로만 좌표를 받고, `App.tsx`에는 아직 그 prop을 채우는 살아있는 배선이 없다(App.tsx 자체를 건드리지 않았다 — 이 SPEC의 "코파일럿 메인 화면 변경 범위 밖" 경계와도 맞물린다). 캡처는 t525가 실측한 좌표의 일부를 손으로 옮겨 쓴 고정 샘플을 썼다 — 실기 좌표 그 자체이지만, 살아있는 읽기 경로를 거치지 않았다는 점은 분명히 한다.
- **그룹 소속 색칠의 이름-접두 대조**: `fixtureDisplayColor`는 장비 이름이 `"<그룹명> "`으로 시작하는지만 본다(예: `BACK 201`은 `BACK` 트랙과 일치) — 이것은 **표시용 보조 수단**이지 콘솔 `SELECTIONDATA` 소속 확인이 아니다(그 읽기는 M1 응답기 확장이 아직 실기 미배치). `SIDE-L 301`/`SIDE-R 311`은 `SIDE-ALL` 트랙과 접두가 다르므로 — 정확하게 — 회색으로 남는다(거짓 확인 0건).
- **헤드리스 캡처 하네스**: 재사용 가능한 스크립트(`run_chrome.sh`, `capture.html`)는 `.moai/reports/t532/`에 남겼지만, 실제 React 엔트리(`_t532_capture_entry.tsx`)는 `ui/src/`에 임시로 뒀다가 캡처 뒤 삭제했다 — 다음에 같은 캡처가 필요하면 이 progress.md의 구성을 참고해 다시 만들어야 한다(상시 유지 비용을 피하려는 의도적 선택).
- **명령창 실제 배선, 「전환」 뷰 안의 실제 필드 편집, 겹침 거절의 UI 상호작용(AC-LDBEAT-003(b))**: 전부 M3 범위(새 서버측 편집 연산이 있어야 의미가 생긴다). M2는 서버 쪽 겹침 **검증 함수**(`validate_beat_grid_tracks`)만 만들고 테스트했다 — UI가 그 함수를 실제로 호출해 트랙 추가를 막는 상호작용은 아직 없다.

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
