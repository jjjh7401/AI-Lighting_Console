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
| REQ-LDBEAT-004(f) | 2D 무대는 콘솔 패치 좌표에서(손그림 아님), **콘솔 SELECTIONDATA로 확인된 소속만** 색(트랙 `group_name`과 정확히 일치할 때만 — 이름 접두 추론 fallback 없음, 레인 리뷰 05ad9ec4 대응) | `BeatGrid.test.tsx`의 `2D stage projection` describe(8개 PASS) + 헤드리스 캡처(아래) — t525 §②가 확인한 네 그룹(MOVER-ALL·BACK·SIDE-L·BLIND, 그룹당 앞 2대)만 `confirmedGroupName`을 받는다. 그중 **BACK·BLIND만 색**이 나온다(LOVE ATTACK 기본 격자의 트랙 이름과 정확히 일치) — MOVER-ALL·SIDE-L은 확인됐어도 화면 트랙이 MOVER-U/MOVER-D/SIDE-ALL이라 이름이 다르므로 회색으로 남는다(거짓 확인 0건). STROBE·KEY는 애초에 `confirmedGroupName` 자체가 없어 회색 |
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
- **그룹 소속 색칠 — 레인 리뷰(05ad9ec4) 대응으로 이름 추론을 걷어냈다**: `fixtureDisplayColor`는 이제 장비 이름을 전혀 보지 않는다 — 오직 `BeatGridFixturePoint.confirmedGroupName`(콘솔 `SELECTIONDATA`로 **확인된** 값)이 화면 트랙의 `group_name`과 **정확히** 일치할 때만 색이 나온다. 이름이 비슷해 보인다는 추론은 fallback으로도 쓰지 않는다. 지금까지 확인된 소속은 t525 §②(`.moai/reports/t525/verdict.md` 93~103행, 표 본문 100~103행) 네 그룹 — MOVER-ALL(501·502)·BACK(201·202)·SIDE-L(301·302)·BLIND(601·602) — 뿐이고, 그룹당 앞 2대만이다(응답기 절단, 그 읽기 자체는 M1 응답기 확장이 아직 실기 미배치). LOVE ATTACK 기본 격자의 트랙 이름은 MOVER-U/MOVER-D/SIDE-ALL/BACK/BLIND/STROBE이므로, 확인된 네 그룹 중 **BACK·BLIND만** 화면 트랙 이름과 정확히 일치해 색이 나온다 — MOVER-ALL·SIDE-L은 확인됐어도 일치하는 트랙이 없어 회색으로 남는다(이것이 정확한 동작이다: "MOVER-ALL 소속 확인"은 "MOVER-U 소속"의 증거가 아니다). `server/tests/test_beat_grid_t532.py`는 아직 이 UI 전용 동작을 직접 재지 않는다(Python 쪽엔 `confirmedGroupName` 개념이 없다 — 2D 무대는 UI 전용 레이어) — `ui/src/components/BeatGrid.test.tsx`가 전담한다.
- **헤드리스 캡처 하네스**: 재사용 가능한 스크립트(`run_chrome.sh`, `capture.html`)는 `.moai/reports/t532/`에 남겼지만, 실제 React 엔트리(`_t532_capture_entry.tsx`)는 `ui/src/`에 임시로 뒀다가 캡처 뒤 삭제했다 — 다음에 같은 캡처가 필요하면 이 progress.md의 구성을 참고해 다시 만들어야 한다(상시 유지 비용을 피하려는 의도적 선택).
- **명령창 실제 배선, 「전환」 뷰 안의 실제 필드 편집, 겹침 거절의 UI 상호작용(AC-LDBEAT-003(b))**: 전부 M3 범위(새 서버측 편집 연산이 있어야 의미가 생긴다). M2는 서버 쪽 겹침 **검증 함수**(`validate_beat_grid_tracks`)만 만들고 테스트했다 — UI가 그 함수를 실제로 호출해 트랙 추가를 막는 상호작용은 아직 없다.

### M2 후속 — 화면을 시안에 맞춤 (카드 t534, 브랜치 `WT-ldbeat-ui-match`)

기준 `bdf6a968`(origin/main, M2 머지 PR#579 포함). 콘솔 접촉 0건 — TDD 사이클, 새 응답기 verb·OSC·프로브 스크립트 실행 0건. cycle_type=tdd(RED 먼저 확인 — 아래 §검증).

**입력**: 리드의 캡처 판독(2026-10-10) — 트랙 줄이 마디 시간축 위 막대가 아니라 칩 목록, 2D 무대에 색·밝기 없음, 막대 클릭이 편집 칸을 안 띄움, M1 프로브가 전부 "미실행"으로만 보임. 시안 정본은 `reports/ldbeat-runbook-ui-proposal-20261008.html`(전체 656행 다 읽음).

**고친 것(REQ-LDBEAT-004 확장, 지어낸 값 없음 — 아래 각 항목에 근거)**:

1. **칸을 마디 시간축 위 막대로** — `BeatGrid.tsx`에 순수 함수 `trackCueSegments`(칸 길이 = 다음 칸이 시작하는 마디까지)·`barToX`/`PX_PER_BAR`를 추가하고, 트랙 줄을 `position:absolute` 막대로 다시 그렸다. 칸과 칸 사이에 이음매(`◆`, `.beat-grid-joint`)를 두어 누르면 다음 칸의 "전환" 보기가 바로 열린다(시안 §"큐 운영"의 "막대와 막대가 만나는 자리"를 그대로 옮김). 첫 칸 앞의 빈 구간은 점선 칸(`.beat-grid-cue-gap`)으로 — "아직 선언 안 됨"을 지어내지 않는다. 마디 자(눈금, `.beat-grid-ruler`)를 새로 추가했고 `position:sticky`로 세로 스크롤 중에도 위에 고정된다. 줄 이름 칸(`.beat-grid-track-label`)도 `position:sticky;left:0`으로 가로 스크롤 중에도 고정했다(시안 `.lhead`와 같은 동작).
2. **2D 무대 밝기** — 콘솔 디머 수치는 M2/M3 전까지 존재하지 않는다(칸 내용이 문장 하나뿐, 플랜-phase 결정). 수치를 지어내는 대신, 이미 있는 실측 표기(「—」= 꺼짐/변화없음, 배치 규칙서 관례)만 켜짐/흐림 두 단계 불투명도로 옮겼다 — 새 순수 함수 `cueIsActive`·`fixtureDisplayOpacity`(둘 다 `BeatGrid.test.tsx`에서 단위 시험). 소속 미확인·그 마디에 칸 미선언·꺼진 칸은 모두 흐리게, 확인된 소속 + 켜진 칸만 최대 밝기 — `fixtureDisplayColor`의 "확인된 소속만 색"과 같은 축이다.
3. **큐 편집 칸을 오른쪽에 늘 보이게** — 이전엔 선택했을 때만 화면 맨 아래에 나타났다. `.beat-grid-body`를 3단(타임라인 | 무대·한눈에 | 큐 편집 칸)으로 넓혀, 선택 전엔 빈 안내("막대(큐)를 누르면 밝기·위치·색·들어올 때를 여기서 확인합니다")를 보여 주고 선택하면 그 자리에서 채워진다(시안 "오른쪽 칸에 늘 있음"). "들어올 때" 필드를 새로 추가했다 — 값을 따로 지어내지 않고 이미 있는 "전환" 토글 뷰(페이드·트리거 박·딜레이·트래킹)를 여는 버튼으로 연결했다.
4. **M1 프로브 9항목 실제 결과** — progress.md 위 "### M1" 표(커밋 `46283183`)를 그대로 옮긴 새 모듈 `ui/src/components/beatGridM1Probes.ts`(`M1_PROBE_RESULTS_T531`). 그 표는 9항목 전부 "가짜 콘솔 리허설"은 통과(exit 0)했지만 "실기 실행"·"판정"은 전부 "미실행"이다 — `ProbeStatus`에 `"리허설PASS·실기미실행"`을 추가해 이 중간 상태를 그대로 담았다(`"미실행"` 하나로만 보여주면 리허설 통과 사실이 사라지고, `"pass"`로 보여주면 실기 미실행인데 통과라고 지어내는 셈이라 둘 다 틀렸다). `RunbookMode.tsx`가 `beatGridProbeResults` 기본값으로 이 상수를 쓴다 — `App.tsx`는 여전히 이 prop을 안 넘기지만(건드리지 않음, 이 SPEC의 범위 경계), 기본값이 바뀌었으므로 실제로 뜨는 화면이 바뀐다. **카드 t534 지시대로 리드의 입력 메시지가 든 예시("①통과 ②기계PASS·눈미확인 ⑥미확인 …")는 실제 표와 다르다** — M1 표의 「판정」 칸은 9항목 모두 "미실행"으로 균일하고, 항목별로 다른 값은 없다. 지어내지 않고 표를 있는 그대로 옮겼다(리드 예시를 베끼지 않음 — 베끼면 안 잰 차이를 지어내는 것이 된다).

**만든/고친 파일**:

- `ui/src/components/BeatGrid.tsx` — `PX_PER_BAR`/`barToX`/`trackCueSegments`/`cueIsActive`/`fixtureDisplayOpacity`/`probeStatusClass` 추가. 렌더: 자(ruler) 추가, 트랙 줄 절대위치 막대+이음매로 교체, 큐 편집 칸을 `.beat-grid-body`의 3번째 칸으로 이동(늘 보임), "들어올 때" 필드 추가, 무대 서클에 `opacity` 적용.
- `ui/src/components/RunbookMode.tsx` — `beatGridProbeResults` 기본값을 `M1_PROBE_RESULTS_T531`로.
- `ui/src/components/beatGridM1Probes.ts`(신설) — M1 표 실측 상수.
- `ui/src/styles.css` — `.beat-grid-ruler*`/`.beat-grid-joint`/`.beat-grid-playhead`/`.beat-grid-cue-gap`/`.beat-grid-cue-slot`/`.beat-grid-cue-panel-empty`/`.beat-grid-cue-field-entry-btn`/`.beat-grid-probe-rehearsal` 추가, `.beat-grid-body`/`.beat-grid-track-label`/`.beat-grid-track-cues`/`.beat-grid-cue`/`.beat-grid-cue-panel` 재배치. 새 `@media` 0개(`styles.test.ts` "정확히 1개" 단언 유지).
- `ui/src/components/BeatGrid.test.tsx` — `barToX`/`PX_PER_BAR`·`trackCueSegments`·`cueIsActive`·`fixtureDisplayOpacity`·`probeStatusClass` 단위 시험 23개 추가(RED 먼저 확인 — 아래 §검증).
- `ui/src/components/beatGridM1Probes.test.ts`(신설) — M1 상수 모양·`buildProbeStatusTable`/`isWriteLocked` 연동 시험 4개.

**검증**:

```
$ npx vitest run src/components/BeatGrid.test.tsx   (함수 추가 전, RED 확인)
 FAIL  … TypeError: cueIsActive is not a function  (외 12건 — trackCueSegments/barToX/fixtureDisplayOpacity 미구현)
 Test Files  1 failed (1)
      Tests  13 failed | 37 passed (50)

$ npx vitest run   (구현 후, GREEN)
 Test Files  36 passed (36)
      Tests  797 passed (797)

$ npx tsc --noEmit
(종료 코드 0, 출력 없음)

$ uv run --quiet pytest server/tests/test_beat_grid_t532.py -q
19 passed in 0.36s

$ git diff --stat origin/main -- ui/src/components/CueSheetTimeline.tsx 'CueSheetTimeline*' 'emit*' 'songcue*' 'cue_sheet_edit*' 'console/lua' ui/src/App.tsx server/director/emit.py server/looks/songcue.py server/design/cue_sheet_edit.py
(출력 없음 — 금지 파일 0 diff)
```

린트: 이 프로젝트 `ui/`에는 eslint 설정이 없다(`.eslintrc*`/`eslint.config.*` 전무, `package.json` lint 스크립트 없음 — t532 자체 검증 블록도 ruff/vitest/tsc만 쓴다) — python 쪽은 이번에 건드린 `.py` 파일이 0개라 ruff 대상 없음.

**캡처**: `.moai/reports/t534/`. `implemented_default.png`(1280×1000, 선택 없음)·`implemented_full.png`(1280×1900, 전체 페이지 — M1 프로브 9항목 "리허설PASS·실기미실행" 렌더 확인)·`implemented_selected.png`(BACK 18마디 선택 — 큐 편집 칸에 밝기·위치·색·들어올 때 네 필드 + "전환"/"들어올 때 → 전환 보기 열기" 버튼 렌더 확인)·`proposal_full.png`(시안 원본, 같은 1280×1900)·`side_by_side.png`(둘을 나란히 붙임, 구조 대조용)·`stage_zoom.png`/`stage_zoom_bar18.png`(2D 무대 크롭 확대 — BACK은 0마디부터 밝고, BLIND는 0마디엔 흐리다가 18마디에서 밝아짐을 직접 눈으로 확인). 데이터는 전부 실측: LOVE ATTACK 격자는 `uv run python3 -c "from server.design.beat_grid import default_beat_grid; ..."` 실행 출력을 그대로 덤프(`love_attack_beat_grid.json`), 무대 좌표는 t525가 실제 응답기로 읽은 60개 픽스처(`.moai/reports/t525/r2_spatial_pername.json`)에 t525 §②가 확인한 8대(BACK 201·202, SIDE-L 301·302, MOVER-ALL 501·502, BLIND 601·602)만 `confirmedGroupName`을 얹었다(`stage_fixtures.json`) — 지어낸 좌표 없음. 재현 방법은 t532 선례와 같다: `ui/` 에 `npm ci` → 임시 React 엔트리(`_t534_capture_entry.tsx`, `t534-capture.html`, `ui/src/components/_t534_*.json`)를 이 progress.md 설명대로 다시 만들고 `npx vite --port 5799` 로 띄운 뒤 `.moai/reports/t532/run_chrome.sh` 재사용 — 캡처 뒤 임시 엔트리는 삭제했다(상시 유지 비용을 피하려는 의도적 선택, M2 선례와 동일).

**차이 목록(시안 대비, 정직하게 남김)**:

- **값 구조화** — 시안은 밝기/위치/색을 각각 드롭다운(디머 프리셋·좌표 프리셋·색 프리셋 선택지)으로 보여 준다. M2 데이터 모델(`BeatGridCue.label`)은 아직 문장 하나뿐이라(M3가 구조화) 이번 구현도 네 필드 모두 같은 문장을 보여준다 — M2 §"안 잰 것"에 이미 적힌 제약을 M3까지 그대로 가져간다, 지어내지 않음.
- **곡 전체 지도** — 시안은 에너지 곡선 + 구간 색 블록 + 강조(★). 구현은 여전히 7칸 숫자 띠(기존 M2 그대로, 이번 카드 범위 밖) — 구간·에너지 데이터 자체가 M2/M3 데이터 모델에 없다.
- **자(ruler)** — 시안은 박 단위 세부 눈금(마디 중간 박)까지 보인다. 구현은 마디 단위까지만(박 단위 트리거 시각은 M3 "이음매 상세" 범위).
- **2D 무대 그림** — 시안은 입체감 있는 빔 원뿔 + 그룹 라벨(BACK/SIDE-L/SIDE-R/WASH/FOH)이 테두리에 배치된 그림. 구현은 여전히 단순 점(기존 M2 투영 방식 유지) — 칠하는 범위를 색+밝기 두 축으로 늘렸을 뿐, 그림 자체의 입체화는 이번 카드 범위 밖(REQ-LDBEAT-004(f) 재측정 대상 아님).
- **프리셋 서랍·칩 강조(마우스 오버 시 같은 프리셋 쓰는 곳 보여주기)** — 시안에 있으나 M2/M3 데이터 모델에 프리셋 참조 자체가 아직 없어 못 옮김.
- **장면 전환(여러 줄 동시 변화) 알약** — 시안의 "장면 전환" 요약 줄은 이번에 옮기지 않았다(새 교차-트랙 계산이 필요해 범위를 넘음).
- **화면 배치(레인 판독, 2026-10-10 `side_by_side.png`)** — 시안은 박자 격자가 한 화면 높이를 다 쓰는 런북 모드 본체이고, 맨 위 막대에 재생·±10초·음원·「콘솔 같이 끔」·마디 이동이 모여 있다. 구현은 기존 「오늘의 곡·큐 순서」 페이지 아래, 비어 있는 TIMELINE·CUE SHEET 블록 다음에 붙은 패널이다 — 첫 화면(1280×1000)에서 격자는 아래쪽 약 40%만 보인다. 페이지 배치를 바꾸려면 `App.tsx`(금지 경로)나 RunbookMode 구조를 건드려야 해서 이번 카드에선 그대로 뒀다.
- **2D 무대 색** — 확인된 소속 8대만 색이 들어가서, 첫 화면에서는 60개 점 대부분이 회색이다(시안은 그룹마다 색 덩어리). 소속 확인 범위(t525 §②)가 늘어야 나아진다.
- **M1 프로브 상수가 낡을 수 있음** — `beatGridM1Probes.ts` 는 main(`bdf6a968`)의 M1 표를 옮긴 고정값이다. lane-3 가 지금 M1 실기를 돌리고 있어 그 결과가 머지되면 이 상수는 바로 낡는다. progress.md 를 읽어 오는 배선이 아니라 손으로 옮긴 값이라, M1 결과가 머지될 때 같이 고쳐야 한다(후속 카드 필요).

**안 잰 것(Gaps, 정직하게 남김)**:

- **음원 동기 실측** — 재생 위치(`playbackSeconds`)를 마디로 환산해 플레이헤드 선(`.beat-grid-playhead`)과 자의 `is-playhead` 표시로 그렸지만, **실제 음원 파일로 재생→동기 확인을 안 했다**(헤드리스 캡처는 음원 파일 입력이 없다). `RunbookMode`/`SongTimelineView`에 기존 공유 재생헤드 소스가 없어(App.tsx를 건드리지 않는 범위 안에서는 찾지 못함) `BeatGrid` 자체 로컬 상태(`playbackSeconds`)에만 묶여 있다 — 다른 화면(큐시트 타임라인 등)과 재생 위치가 같이 안 움직인다.
- **실기 콘솔 0건** — 이번 카드도 콘솔 접촉 0(읽기·쓰기 모두 없음). 2D 무대 밝기의 "켜짐/꺼짐"은 배치 규칙서가 적어 둔 칸 문장(「—」 유무)에서 유도한 것이지, 콘솔에서 실제 디머 값을 읽은 것이 아니다.
- **이음매 클릭의 "전환" 뷰 실제 값** — 이음매를 누르면 다음 칸의 전환 뷰가 열리지만, 그 안의 "페이드·트리거 박·딜레이·트래킹" 문구는 M2부터 있던 읽기 전용 자리표시자 그대로다(M3가 구조화된 전환 데이터를 채운다).
- **클릭 상호작용 자체의 DOM 시험** — `BeatGrid`는 훅을 쓰므로(RunbookMode/DashBoard와 다른 관례) 이 프로젝트의 무-jsdom 시험대로는 렌더/클릭을 단위 시험할 수 없다(기존 M2도 같은 경계) — 선택·클릭 동작은 헤드리스 캡처(`implemented_selected.png`, `?select=` 쿼리로 버튼 클릭을 흉내)로만 확인했고, 자동화된 회귀 시험은 아니다.
- **1280px보다 좁은 화면에서의 좌우 스크롤 체감** — 헤드리스 캡처는 고정 뷰포트 한 장이라, 실제 좌우 스크롤로 26마디 전체를 넘겨 보는 느낌(줄 이름 칸이 계속 고정되는지)은 스크린샷 여러 장을 비교하지 않는 한 직접 보지 못했다 — CSS `position:sticky`가 맞게 동작한다는 것은 브라우저 표준 동작에 근거한 것이지, 스크롤하며 눈으로 확인한 것은 아니다.

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
