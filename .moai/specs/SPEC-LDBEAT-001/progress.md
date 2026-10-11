# SPEC-LDBEAT-001 — Progress

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-07
- 작성 카드: t522. 입력 출처는 `spec.md` HISTORY·`plan.md` §A/§G 참조.
- Tier: M→L (spec.md §0 근거) — REQ 14개·AC 13개 최초 작성(오케스트레이터 검토 D1~D3 교정 후에도 총량 불변), **카드 t526 개정(2026-10-10)으로 REQ 15개·AC 16개**로 변경 — Tier M 상한(각 16개) 이내, AC는 경계치. **카드 t554(2026-10-11)로 Tier L 승급, REQ 25개·AC 25개**(Tier L 상한에 정확히 도달).
- 플랜-오딧 전 자체 점검: SPEC ID 정규식 PASS(Bash 실행·출력 cite — 메인 작업 응답 참조), 프런트매터 12필드 schema 대조 완료, 기존 SPEC ID와 충돌 없음(`ls .moai/specs/` 확인), Out of Scope 섹션 6개 H3 하위헤딩 + `-` 불릿 포함(카드 t526 개정 뒤 7개로 증가, 아래 plan-amend 항목 참조).
- **오케스트레이터 검토 D1~D3 교정(2026-10-07, 같은 날 후속 커밋)**: D1(REQ-013/§5 — 콘솔 타임코드는 커맨드로 만들어진다는 실측, 장벽 A를 "해소"에서 "열린 결정"으로 되돌림), D2(REQ-007~009 — 기존 큐 레벨 파서가 격자를 커버한다는 주장 철회, 새 서버측 편집 연산 요구), D3(REQ-006 — `SongTimelineStore`/`TimelineDraftHistory`/`SongTimelineLibrary` 저장소 실체 인용 + M2 명시적 결정화). `.moai/reports/t522/verdict.md` §2(재측정 기록) 참조.
- **plan-amend(카드 t526, 2026-10-10)**: 입력 `reports/ldbeat-feasibility-roadmap-20261010.md`+`.html`·`reports/ldbeat-runbook-ui-proposal-20261008.html`·`reports/ldbeat-runbook-mockup-20261008.html`·`reports/ldbeat-plan-summary-20261008.md`·`.moai/reports/t525/verdict.md`. 코드 diff 0줄, 콘솔 접촉 0건. 바뀐 것: (1) 확정된 감독 결정 1~5 추가(spec.md § 확정된 감독 결정) — 열린 결정 0항(새 에미터) 해소. (2) REQ-LDBEAT-013 재교정 — `songcue.py:634,683`이 이미 타임코드 커맨드·영문화를 내고 있었다는 사실 반영, 진짜 틈은 `emit.py:51`의 재생 거부 + songcue의 1:1 시퀀스-타임코드 구조로 재정의. (3) 트랙 모양 교정 — "SCENE/BACK PULSE/…" → 콘솔 그룹 트랙 + 층 역할 이름표(REQ-LDBEAT-004). (4) 2D 무대를 콘솔 패치 기반으로 교정(t525 실측) + 응답기 그룹 소속 절단 실측 → M1에 응답기 긴 값 나눠 읽기 확장 추가(REQ-LDBEAT-002). (5) M1 미확인 항목 4개→9개(REQ-LDBEAT-001~003, AC-001/002/009). (6) REQ-LDBEAT-015(프리셋 아키텍처) + AC-LDBEAT-016 신설. (7) spec.md §4에 SPEC-LDBARMAP-001·SPEC-LDARRANGE-001(둘 다 미존재) 명시적 교차 참조 추가. **REQ 14→15개·AC 15→16개**(Tier M 상한 16개 이내, AC는 경계치). version 0.1.0→0.2.0, updated 2026-10-10. status는 draft 유지(완료 전 amend이므로 `amendment_of` 불필요 — completed→in-progress 전환 규칙과 무관).
- **plan-audit iteration 1 FAIL 대응(카드 t526, 같은 날 후속)**: `.moai/reports/t526/plan-audit.md` — Overall 0.85(통과선 0.80 이상이나 MP-2 필수통과 방화벽 FAIL로 집계 무효). D1~D3(GEARS-MIX, blocking) REQ-LDBEAT-004/005/011/012/013/015를 (a)(b)(c)… 라벨 하위 절로 재구조화, 모든 절에 굵은 GEARS 트리거 부여, 근거/권고 서술은 근거 칸으로 이동 — 새 REQ-ID 없음. D4~D6(TRACE-GAP, blocking) acceptance.md AC-LDBEAT-002/003을 하위 시나리오로 확장(새 AC-ID 없음, Tier M 상한 16/16 유지) — REQ-004(h) 겹침 금지·REQ-005(b) 재생±10초/음원동기·REQ-012(b) 미리보기 세션반복을 정식 Given/When/Then으로 승격. D7(UNVERIFIED-UI, blocking, 핵심) REQ-LDBEAT-004(b) "모드 전환 버튼(타임라인↔상세)"이 입력 보고서에 없는 지어낸 사실이었음을 확인 — `reports/ldbeat-runbook-ui-proposal-20261008.html:495,504,519`(큐 편집 칸 내부 "전환" 토글, 큐 편집 ↔ 들어오는-전환 편집)로 교정, `:155,376,196-200,238`도 재검증. D8(optional) REQ-LDBEAT-009 Where→When. D9(optional) 보류. REQ/AC 총량 불변(15/16) — 재구조화·교정뿐, ID 추가삭제 없음.
- **plan-audit iteration 2 FAIL(0.875, 원인 교체) 대응(카드 t526, 같은 날 후속)**: D1~D8 전부 FIXED 재확인, D9 보류 수용. 15개 REQ 전수 재검사로 신규 발견: D10(REQ-LDBEAT-002, D1과 동형 GEARS-MIX) — (a)(b)(c) 라벨 하위 절로 재구조화(새 REQ-ID 없음). D11(REQ-002(c) 응답기 확장의 TRACE-GAP) — AC-LDBEAT-009에 (b) 하위 시나리오 추가(새 AC-ID 없음, t525 §② 절단 실측을 Given으로 인용). REQ/AC 총량 불변(15/16).
- **plan-audit 최종 판정(카드 t526, 2026-10-10): PASS-with-fix — 리드 직접 확인.** 3회차 FAIL 은 필수 기준 7개 전부 PASS/N/A 이고 남은 결함 D12(AC-LDBEAT-009(b) 「각 8대」, 잰 적 없는 숫자) 한 문장뿐이었다. 레인이 `.moai/reports/t525/verdict.md:130`(전체 개수 미측정)으로 고쳤고, 리드가 고친 문장이 출처와 일치함을 직접 확인해 수용했다. 4회차 감사는 돌리지 않았다 — plan-auditor Retry Loop 상한 3회 도달, 남은 수정이 한 문장이라 리드 확인으로 대체(`.moai/reports/t526/plan-audit.md` 말미).
- **plan-amend(카드 t554, 2026-10-11) — 런북 UI 시안 정식 반영, Tier M→L.** 입력: `design/ldbeat-runbook-ui-proposal-20261008.{md,html}`(17:51판)·`design/ldbeat-runbook-mockup-20261008.{md,html}`(15:16판, 둘 다 바이트 동일 복사 — `.moai/reports/t554/sha256.txt`)·`.moai/reports/t554/coverage-draft.md`(시안 23개 항목 1차 분류)·현재 구현 `ui/src/components/BeatGrid.tsx`/`RunbookMode.tsx`/`ui/src/App.tsx` 전수 재독·리드 확정 3건(상세 칸 제거 절의 ▸펼침/칩툴팁 유효 유지, 음원 자동 연결 일반화, 재생 멈춤 수정의 부모 그룹 줄 일반화). 코드 diff 0줄, 콘솔 접촉 0건. 바뀐 것: (1) Tier M→L 승급(REQ 15→25개·AC 16→25개, Tier L 상한에 정확히 도달 — 근거 spec.md §0). (2) 신설 REQ-LDBEAT-016~025(10개, 화면 영역별 — 상단바/곡전체지도/타임라인줄·막대/이음매·전환/편집칸/2D무대/이마디한눈에/재생·음원/명령창·AI·프리셋서랍 + 교차영역 REQ-016)·AC-LDBEAT-017~025(9개, 영역당 1개). (3) `design.md`·`research.md`(Tier L 신설 아티팩트) — 시안 23개 항목 전수 매핑 + 현재 구현과의 항목별 대조(구현 10·부분 15·미구현 29·상충 0, 54행 전수 재측정 — research.md §10 집계, plan-audit iteration 1 D3 교정). (4) plan.md에 M9(런북 UI 시안 화면 영역 전수 반영, 아직 미구현) 신설. version 0.3.3→0.4.0. plan-audit 재감사 권고(새 Tier·REQ/AC 다량 신설) — 다음 run-phase 착수 전.
- **plan-audit iteration 1 FAIL(0.75, Tier L 통과선 0.85) D1~D5 대응(카드 t554, 2026-10-11, 같은 날 후속)**: D1(critical) REQ-LDBEAT-019(b)의 비-shall 문장을 요구사항 칸에서 제거하고 근거 칸으로 이동(재레터링 없음, 기존 (b)(c)(d) 참조 전부 유효 — 재검증 명령: `grep -n "REQ-LDBEAT-019(b)\|REQ-LDBEAT-019(c)\|REQ-LDBEAT-019(d)" .moai/specs/SPEC-LDBEAT-001/*.md` → design.md 4곳만, 전부 유효한 참조). D2(major) AC-LDBEAT-019(e)·017(c) 신설 + 022(c) 보강으로 440px/1640px·97%/320px 치수에 구체 검증 수단 추가(310px·1450px는 기존에 이미 구체적이었음을 재확인). D3(major) research.md §10 집계 오류 — `awk '/^## §1\./,/^## §10\./' research.md | grep "^| " | grep -v 분류 | grep -v '^|---' | wc -l` → `54`(이전 "49"는 5행 누락) → 10·15·29·0으로 재측정·교정(이 progress.md 자신의 "9·16·24·0" 인용도 교정, plan.md/design.md/spec.md/acceptance.md에는 그 수치 없었음을 그렙 확인). D4(minor) plan.md M9에 REQ-LDBEAT-021 전용 step 4 신설(움직임/옆빛L·R 필드 + 표→편집 클릭 연동), 이후 step 4→9로 번호만 밀림. D5(minor) `RunbookMode.tsx` "281행"(plan.md·research.md)을 `wc -l` 실측 `280`으로 교정. **REQ/AC 총량 불변(25/25)** — 기존 REQ-001~015/AC-001~016 텍스트 무변경, 새 ID 없음.
- **plan-audit iteration 2 FAIL(0.80) D-NEW-1~6 대응(카드 t554, 2026-10-11, 같은 날 후속)**: D-NEW-1~4(critical, D1과 같은 결함 유형) REQ-LDBEAT-020(a)·021(b)·024(b)·024(c)의 shall-없는 꼬리 문장을 When/While+shall로 재작성(행위 무변경). 전수 재스윕: `python3`으로 REQ-016~025 전체의 요구사항 칸을 글자별 절로 쪼개 "shall" 부재 문장을 검사 → `[HARD]` 태그 1건을 빼면 **0건**. D-NEW-5(major) AC-LDBEAT-024에 REQ-024(a)/(b) 전용 (g)(h) 체크 행 신설(미구현 확인) — REQ-016~025 전체 글자별 하위절의 AC 커버리지를 전수 재확인, 빠진 자리는 이 신설로 전부 메움. D-NEW-6(minor) spec.md를 §D 소속 파일로 잘못 적은 오기(spec.md에는 §D가 없음) 5곳을 `acceptance.md` §D로 교정 — 그 틀린 조합 문자열의 전체 재검색 결과 0. **REQ/AC 총량 불변(25/25)**.
- **plan-amend(카드 t566·t556·t564 묶음 + 카드 t555 반영 재확인, 2026-10-11, 리드 경유, plan만 — 코드 diff 0줄, 콘솔 접촉 0건).** 입력: `.moai/reports/t561/run-verdict.md`(§4 — 트리거 박·딜레이·위치만 따로·트래킹·「모두 1박 페이드」 비활성 사실)·`server/design/beat_grid_edit.py`(카드 t551 계속, `confirmed`-게이트·`fresh_approval_cue`)·`server/design/beat_grid_data/preset_pools.yaml`·`server/design/beat_grid_data/love_attack.yaml`(전수 재계수)·`server/design/cue_sheet_edit.py`(`TRACKING_VALUES`/`MIB_MODES`)·`git log --oneline origin/main`(t560 머지 확인). 바뀐 것 넷: **① 카드 t566** — REQ-LDBEAT-006(i-4a)~(i-4f) 신설(`entry` 저장 스키마 확장: `fade_beats`·`trigger_beat`·`delay_beats`·`position_late_beats`·`tracking`), REQ-LDBEAT-020(e) 재교정, AC-LDBEAT-020에 (f)~(k) 신설(전부 미구현, 검증 수단만 명시). **② 카드 t556** — AC-LDBEAT-016(a)를 `confirmed`-플래그 조건부 경고/거절로, AC-LDBEAT-016(e)를 "non-null은 §4/t525 출처 또는 REQ-015(g) 승인 중 하나"로, AC-LDBEAT-025(d)를 "현재는 데이터 파일(PROVISIONAL)에서 읽음"으로 재교정 — 전부 재교정 태그, 새 AC-ID 없음. **③ 카드 t564** — spec.md REQ-LDBEAT-023 근거의 "구현" 과장을 research.md §7과 일치하도록 교정("미구현(표 자체는 구현, 내용은 아님) — 2칼럼"). 발견(범위 밖): 카드 t560(PR #609)이 이미 머지됐으나 이 재확인은 그 반영분을 포함하지 않는다 — research.md §7 갱신은 후속 sync 카드로 남긴다. **④ 카드 t555 반영 재확인** — 머지된 커밋 `0a947e72`("새 번호는 이번 변경의 승인만 인정")를 REQ-LDBEAT-015(h)로 명문화하고 AC-LDBEAT-016(v)를 신설. **REQ 총량 25개 불변**(REQ-006에 (i-4a)~(i-4f), REQ-015에 (h) 하위 절 신설뿐) · **AC 총량 25개 불변**(AC-020에 (f)~(k), AC-016에 (v) 신설 + AC-016(a)(e)/AC-025(d) 재교정뿐) · **옛 REQ/AC 삭제 0**. version 0.4.1→0.5.0. plan-audit 재감사는 선택 사항으로 남긴다(신규 하위 절은 REQ-006(i-4a)~(i-4f)·REQ-015(h)뿐이고, 나머지는 기존 절의 문면 정합 교정이다).
- **delta plan-audit iteration 1 FAIL(0.94) D1/D2 대응(같은 날 후속)** — `.moai/reports/plan-audit/SPEC-LDBEAT-001-t566-delta.md`. **D1(critical, blocking, MP-2 GEARS)**: REQ-LDBEAT-020(e)에 카드 t566이 끼워 넣은 라우팅 문장("정수 마디로 떨어지는 입력은 `entry.fade_bars`에, … `entry.fade_beats`에 저장된다")이 굵은 GEARS 트리거 없이 독립된 새 사실을 주장했다 — **When**(정수배)/**When**(비정수배) 두 절로 재작성해 각각 `entry.fade_bars`/`entry.fade_beats`에 쓴다는 shall 절로 교정했다(의미 불변, 복원해 둔 옛 문면 인용은 그대로 보존). **전수 재스윕(지시대로 이번 개정이 건드린 절 전부 + REQ-016~025 전체를 글자별 절로 쪼개 'shall' 부재 문장 검사)**: 이 재스윕 과정에서 REQ-LDBEAT-006(i-4a)의 둘째 문장("`fade_beats`는 … 저장 가능하게 한다 — 기존 데이터는 … 유효하다")도 같은 결함(트리거 없는 독립 사실 주장)임을 자체 발견해 **While**(기존 데이터가 `fade_beats`를 비워 둔 동안) … **The** … **shall** 유효한 채로 남는다 — 로 교정했다(1건 선재 발견·수정, delta 보고서가 지적한 것 외 추가분). 재스윕 결과: REQ-006(i-4a)~(i-4f)·REQ-015(h)·REQ-020(e) 전부 shall/shall-not 트리거 보유 확인(0건 미비) + `REQ-LDBEAT-016~025` 전체를 글자별 절로 쪼갠 기계 재검사 → **0건**(스크립트 `.moai/reports/t566/sweep_016_025.py`, 출력 "REQ-LDBEAT-016~025 합계 shall 부재 문장: 0"). **D2(minor, optional)**: REQ-LDBEAT-023(a) 근거의 `.beat-grid-glance-table(1118-1134행)` 줄 번호 인용이 낡았다(카드 t560 이후 origin/main에서 바뀜) — 심볼 인용(`ui/src/components/BeatGrid.tsx`의 `.beat-grid-glance-table`)으로 바꾸고, 줄 번호를 측정 커밋과 함께 적었다(HEAD `b961cc9e` 기준 1987행, `git grep -n 'beat-grid-glance-table' HEAD -- ui/src/components/BeatGrid.tsx`로 재측정) — 옛 인용("1118-1134행")은 대체됨 표기로 보존. **REQ/AC 총량 불변(25/25)**(문면 교정뿐, 새 ID 없음).

## 저장 키 맞춤 (카드 t529, 2026-10-10)

- ③ 저장 키 맞춤(t529 후속, 2026-10-10): §5 열린 결정에 세 SPEC 공통 권고 키 `timeline["beat_grid"]`/`["bar_map"]`/`["arrangement_draft"]` 추가. 권고뿐 — REQ·AC·plan.md·acceptance.md 변경 0, plan-audit 재실행 없음.

## §E.2 Run-phase Evidence

_<run-phase 대기 — manager-develop 착수 전까지 비어 있음>_

### M1 — 콘솔 확인 프로브 + 응답기 나눠 읽기 (카드 t531, lane-3, 브랜치 `WT-ldbeat-m1`)

기준 `b52512ee`(origin/main, ed740c12 이후). 측정일 2026-10-10. 실기 쓰기: 승인 문면 안의 새 객체만(아래 「콘솔에 남은 새 객체」), 쇼 저장 0.

**응답기 1.6.6 (REQ-LDBEAT-002(c), AC-LDBEAT-009(b))**

- `82d2b877` — `props <id> <Name> <path> offset=<n>` 엔트리 단위 나눠 읽기. 응답 전체가 `max_payload`(1900) 안에 들도록 엔트리를 담고 `offset`·`total`·`truncated` 를 붙인다. 토큰 없는 요청은 1.6.5 와 바이트 동일.
- `fef93ed6` — `EXPECTED_RESPONDER_VERSION` 1.6.5→1.6.6, console/lua 지문 재고정.
- 오프라인 증거: `uv run --quiet pytest server/ -q` → `14555 passed, 35 skipped` @ `fef93ed6` (`.moai/state/verify/t531/full_suite_fef93ed6.txt`). 86개 배열을 나눠 읽어 다시 맞추면 86개 전부 돌아온다(`server/tests/test_lua_responder_props_paging.py`).
- 실기: 처음엔 미배치(`ping` → `1.6.5`, `group_members.py` 실행 거부 — `.moai/reports/t531/group_members_refusal.txt`). 감독 ASCII 붙여넣기 뒤 **`ping` → `1.6.6`**(`r4_ping_after_ascii_paste.txt`, 마무리 때 다시 `1.6.6` — `live/final_leftovers.txt`). AC-LDBEAT-009(b)(나눠 읽기로 그룹 소속 읽기)는 **여전히 미실행** — 실기 프로브에 집중했다.
- 🔴 머지하면 main 의 `EXPECTED_RESPONDER_VERSION` 이 1.6.6 이 된다(`server/safety/gate.py:675`). 이 콘솔은 1.6.6 이라 통과하지만, **1.6.5 응답기를 쓰는 다른 콘솔·쇼 파일은 게이트가 새 실행을 막는다** — 쇼를 다시 열면 응답기도 쇼 파일에 든 판으로 돌아갈 수 있다(쇼 저장 0, 아래 남은 객체 참조). 다시 붙여넣기 안내: `deploy-1.6.6-paste.md`.

**프로브 9+2항목 최종 표 (REQ-LDBEAT-001~003)** — 설계 `.moai/reports/t531/probe-design.md`(커밋 `abdd407d`), ⑩⑪ 은 v3 재승인 때 추가. 승인 문면: 1·2차 `approval-list.md`, v3 `approval-v3-package.md`. 근거 경로는 `.moai/reports/t531/` 기준.

판정 갈래: **통과** = 감독 눈 또는 구조 되읽기로 확인 · **부분** = 기계로 일부만 확인 · **미확인** = 판정 근거 없음 · **움직임 없음** = 문법은 받았지만 기대한 효과가 안 보임.

| 항목 | 판정 | 무엇을 봤나 | 근거 |
|---|---|---|---|
| ① 타임코드 트랙 ≥3(목표 6) | **통과(구조)** | TC 30 에 시퀀스 트랙 6개(228→233) | `live/p1/` · `live/p1_readback.txt` |
| ② Goto 2번 이후·여러 시퀀스 동시 | **미확인** | 줄은 전부 OK. CURRENTCUE 는 켜짐 증거가 아니고(아래 정정) 눈 미확인 | `live/p2_on/` · `live/p2_readback.txt` |
| ③ 프리셋 수정 전파 | **부분** | v2 `Attribute 'Color' At Preset` 거절 → v3 `At Preset` 받음. 프리셋 4.302 크기 2068→1852(수정 먹음), 큐 300.1 4292→4296(참조 가설). 무대 전파는 재생 줄이 없어 미측정 | `live/p3_a/` · `p3_b/` · `p3_c/` · `p3_before_edit.txt` · `p3_after_edit.txt` |
| ④ 효과 프리셋의 SM15·Measure | **미확인** | 감독 「다 같이 깜빡임」. 박자 속도는 번갈아가 없어 눈으로 못 가림 | `live/p4_a/` · `p4_held_readback.txt` · `p4_off/` |
| ⑤ 위치 프리셋 위 상대값(원) | **움직임 없음** | 감독 「멈춰 있음」 | `live/p5_a/` · `p5_readback.txt` · `p5_off/` |
| ⑥ 타임코드 중간 재생 | **미확인 — 문법 불명** | `Goto Time 5 Timecode 31` → User Canceled Command, CURSOR 0.00 | `live/p6_a/` · `p6_after_goto.txt` |
| ⑦ 큐에 선택 + Step 2 | **부분(결과 기록)** | 큐1 「다 같이 깜빡임, ④보다 느림」(번갈아 아님) · 큐2 「두 그룹 다 깜빡임」 | `live/p7_a/` · `p7_b/` · `p7_c/` |
| ⑧ 같은 그룹 두 시퀀스 분담 | **통과** | 감독 「켜지고 틸트가 조금 기울어짐」 | `live/p8_a/` · `p8_readback.txt` · `p8_off/` |
| ⑨ circle·발리후·wave | wave **움직임 없음** · circle·발리후 **미확인** | wave 감독 「멈춰 있음」. circle·발리후는 재생 묶음이 바로 꺼서 볼 틈 없음 | `live/p9_a/` · `p9_readback.txt` · `p9_off/` |
| ⑩ 디머 위상 펼침(추가) | **통과** | 감독 「물결처럼 차례로」 — `Group 11` 에서 디머 페이저 + `Phase 0 Thru 180` 먹음. 엄밀한 홀짝 번갈아는 미측정 | `live/p10_a/` · `p10_readback.txt` · `p10_off/` |
| ⑪ t520 줄 순서 재현(추가) | **통과(가설 반증)** | 감독 「둘 다 깜빡임」. 큐 크기 ⑦ 큐2 와 바이트 동일(4272) → Step 2 위치는 t520 실패 원인 아님 | `live/p11_a/` · `p11_readback.txt` · `p11_off/` |

**콘솔에 남은 새 객체(읽어서 확인, `live/final_leftovers.txt`)** — 쇼 저장 0 이라 쇼를 다시 열면 사라진다. 지우지 않았다(삭제는 승인 범위 밖).

| 풀 | 번호 | 이름 |
|---|---|---|
| 타임코드 | 30 | `LDBEAT M1 - P1 six tracks` |
| 타임코드 | 31 | `LDBEAT M1 - P6 mid-start` |
| Color 프리셋(4) | 301 | `LDBEAT M1 - P3 propagation` — **빈 것**(v2 거절 뒤 남음) |
| Color 프리셋(4) | 302 | `LDBEAT M1 - P3 propagation#2` |
| All 프리셋(21) | 301 | `LDBEAT M1 - P4 SM15 MEASURE` |
| 시퀀스 | 300~310 | `LDBEAT M1 - P3 …` ~ `LDBEAT M1 - P11 …` (11개) |

모든 시퀀스는 끄기(`Off`) 묶음까지 보냈다 — 켜진 채 남은 것 없음(각 `live/*_off/`).

**다음 시험 설계안(실행 X)** — ⑤⑨ 정지 원인 가르기: `.moai/reports/t531/next-probe-design.md`. wave 를 기준으로 크기·속도·기준을 하나씩 바꾸고 디머를 넣으며, t516 A2 그대로를 양성 대조로 둔다. 실행은 재승인.

**실기 2026-10-10 (응답기 1.6.6, 쇼 저장 0)**

- ③ 묶음 1: 7줄 중 `Attribute 'Color' At Preset 4.9` 만 `Illegal object`(`live/p3_a/steps.jsonl:7`). 뒤 줄 `Store Preset 4.301` 은 OK(`:8`) → **이름만 있는 빈 프리셋 4.301**(자식 0, `live/p3_a_readback.txt`)이 남았다. 지우지 않음(삭제는 승인 범위 밖). 묶음 2 이후는 안 보냄 — 시퀀스 300 없음.
- 🔴 **묶음 안에서 한 줄이 실패해도 나머지 줄이 계속 나갔다.** 원인은 콘솔이 아니라 **이 프로브의 반복문**이다: `.moai/reports/t506/tc_probe.py:220-231` 은 줄마다 `execute` 하고 실패해도 `all_ok` 만 내릴 뿐 멈추지 않는다(멈추는 건 묶음 사이, `m1_common.py:192-194`). 콘솔 쪽 사실은 「각 줄이 따로 실행된다 — 앞 줄 거절이 뒤 줄을 막지 않는다」까지. **앱 송신기(emit 경로)가 실패 줄에서 멈추는지는 안 쟀다** — 앱 설계에 쓰기 전에 그쪽 코드를 따로 읽어야 한다.
- ④ 묶음 1~3, 19줄 전부 OK(`live/p4_a/steps.jsonl`). `Attribute 'Dimmer' At Measure 1`·`At SpeedMaster 15`·`At Preset 21.301`(Attribute 접두 없는 호출) 모두 콘솔이 받았다. 시퀀스 301 CURRENTCUE = `Sequence 301.1`(`live/p4_held_readback.txt`). 프리셋 21.301 `SPEEDMASTER` 읽기 `"None"`, `PRESETDATA` 빈 문자열 → 이 두 속성으로는 SM15·Measure 저장 여부를 못 가린다.
  - 감독 판정(리드 전달, 2026-10-10): **「다 같이 깜빡임」** — Group 11 이 번갈아(Step 2)가 아니라 한꺼번에 깜빡였다. 디머 페이저 자체는 재생됐지만 Step 2 가 프리셋 저장→그룹 호출 경로에서 살아남지 않았다. 박자 속도(SM15·Measure)는 번갈아가 없어 눈으로 가릴 수 없다 → **미확인**.
  - 원인 후보(전부 **가설**, 하나도 안 쟀다): (가) 프리셋이 Step 정보를 담지 않는다 (나) 프리셋은 담지만 그룹 선택 뒤 `At Preset` 호출에서 Step 이 풀린다 (다) `/Universal` 저장이 선택 순서 의존 정보를 버린다. 가르려면 ⑦(같은 Step 2 를 큐에 직접 저장)과 대조하고, 그다음 저장 옵션만 바꾼 묶음이 필요하다.
  - 끄기: `Off Sequence 301` OK(`live/p4_off/`).
- ⑦ 큐1·큐2 저장 + 큐1 재생, 22줄 OK(`live/p7_a/`, CURRENTCUE 303.1). 감독 판정(리드 전달): **「다 같이 깜빡이는데 ④보다 느림」**. 프리셋을 거치지 않고 큐에 바로 저장해도 번갈아가 아니다 → ④ 가설 (가)「프리셋이 Step 을 잃는다」는 약해졌다.
  - 큐2: `Off Sequence 303` → `Goto Cue 2 Sequence 303` OK, CURRENTCUE 303.2(`live/p7_b/`). 감독 판정(리드 전달): **「둘 다 깜빡임」** — MOVER-U(Group 11)와 바닥 워시(Group 10) 모두. 큐 하나에 선택 둘을 각각 Step 2 로 저장하면 두 그룹 효과가 함께 남는다 → t520 「마지막 선택의 페이저만 남는다」는 이 형태에서는 재현되지 않았다. 끄기 `Off Sequence 303` OK(`live/p7_c/`).
  - t520 이 실제로 보낸 형태(잰 것, 승인 문면 `t520/approval_m2a_batch1_v2.txt:178-209`, 큐 4 `Kick Four`)와 ⑦ 큐2 의 차이 — **어느 차이가 원인인지는 가설**:
    1. **Step 2 위치** — t520: 선택 다섯에 단계 1 값을 다 넣고(`:178-182`) `Step 2` 를 **한 번**(`:183`), 그 뒤 선택을 다시 하나씩 골라 단계 2 값(`:184-209`). ⑦: 선택마다 `At 0 → Step 2 → At 100` 을 끝내고 다음 선택으로. 가설: Step 2 뒤 선택을 바꾸면 단계가 1로 돌아가거나 앞 선택의 단계 구성이 덮인다.
    2. **선택 수** — t520 다섯, ⑦ 둘.
    3. **선택 형태** — t520 `Fixture 201 + 201.1 + …`(서브픽스처 포함 목록, 선택과 값이 한 줄 `; Attribute`), ⑦ `Group 11` / `Group 10` 단독 줄.
    4. **속성 섞임** — t520 은 디머와 Pan/Tilt 를 한 큐에 섞고 선택마다 `Phase 0`·`Measure`·`SpeedMaster 15` 를 붙였다. ⑦ 은 디머만, 속도·위상 줄 없음.
    - 가르려면 ⑦ 큐2 에서 하나만 바꾼 묶음(예: Step 2 한 번 뒤 재선택)이 필요하다 — 문면 밖이라 이번엔 안 보냄. → ⑪ 로 준비.
- ⑧ 17줄 OK, 304.1·305.1 동시 재생(`live/p8_a/`, `p8_readback.txt`). 감독 판정(리드 전달): **「켜지고 틸트가 조금 기울어짐」 → 통과** — 같은 그룹을 밝기 시퀀스와 위치 시퀀스가 나눠 써도 둘 다 먹는다. 끄기 `Off Sequence 304`·`305` OK(`live/p8_off/`).
- **v3 재승인 묶음**: `.moai/reports/t531/approval-v3-package.md`(`make_v3_package.py` 생성) — ③⑤⑨ 「이전 → 새」 수정 10줄 + ⑩⑪ 전문 28줄. ⑩ = ⑦ 큐1 + `Attribute 'Dimmer' At Phase 0 Thru 180` 한 줄(문법 근거 `t227/verdict.md:98` 의 `0 Thru 360` executed_ok, 끝값 180·눈 결과 미측정). ⑪ = ⑦ 큐2 를 t520 줄 순서(Step 2 한 번 뒤 재선택)로 바꾼 한 가지 차이. 리허설 5/5, 실기 전부-거절 5/5(실행 줄 0), 309·310 비어 있음 확인(실행 직전 다시 확인).
- **v3 감독 승인(리드 전달, 2026-10-10)** — 문면 그대로 ③⑤⑨⑩⑪, 순서대로 하나씩.
- ③ v3: 4묶음 21줄 OK(`live/p3_b/`·`live/p3_c/`). `At Preset 4.9`·`4.302`·`4.5` 모두 콘솔이 받음 — Attribute 접두가 거절 원인이었다는 데 맞는다. 되읽기(`p3_before_edit.txt` → `p3_after_edit.txt`): 프리셋 4.302 MEMORYFOOTPRINT **2068 → 1852**(내용 바뀜), 큐 300.1 **4292 → 4296**(거의 그대로). 큐가 값을 복사하지 않고 프리셋을 가리킨다는 해석과 맞지만 **가설** — 무대에서 색이 바뀌는지(전파 자체)는 재생 줄이 승인 문면에 없어 미측정. 4.302 이름이 콘솔에서 `LDBEAT M1 - P3 propagation#2` 로 붙었다(잰 것) — 같은 이름의 빈 4.301 때문으로 보인다(추정). 빈 4.301 MEMORYFOOTPRINT 1568.
- ⑤ v3: 14줄 OK(`live/p5_a/`), CURRENTCUE 302.1, 큐 크기 3780(`p5_readback.txt`). 감독 판정(리드 전달): **「멈춰 있음」** — 프리셋 자리에 서 있고 움직임 없음. 프리셋 호출·상대값 줄은 콘솔이 받았지만 움직임은 안 생겼다. 끄기 `Off Sequence 302` OK(`live/p5_off/`).
  - 근거 대조(잰 것): t516 A2(시퀀스 236, `t516/approval_rhythm_probe_v4.txt:21-25`) — `Fixture 501…508 ; Attribute 'Tilt' At Relative 30` → `Attribute 'Tilt' At Phase 0 Thru 360` → `Attribute 'Tilt' At Speed 112`, **상대값 한 단계**인데 감독이 「Tilt 움직임」 확인(`t516/verdict.md:385`). 두 단계(`Step 2` ±값)인 237·247 도 움직였다(`:385`, `:428`). → 리드 가설 「한 단계면 정적 오프셋」은 A2 실측과 맞지 않는다.
  - ⑤ 와 A2 의 차이(원인은 **가설**): 위상(⑤ `Phase 0`/`Phase 90` 단일값 vs A2 `Phase 0 Thru 360`) · 크기(12·8 vs 30) · 속도(60 vs 112) · 선택(`Group 11` vs `Fixture 501…508`) · 기준(프리셋 2.1 호출 vs 같은 큐 Tilt 45 — A2 는 기준이 빠졌다, `t516/verdict.md:390`).
- 🔴 **CURRENTCUE 는 켜짐/꺼짐을 못 가린다(잰 것).** ⑨ 에서 306·307 을 `Off` 한 뒤에도 CURRENTCUE 가 `Sequence 306.1`·`307.1`(`live/p9_readback.txt`). 위 ②④⑦⑧⑤ 의 「CURRENTCUE = …(재생 중)」은 **마지막으로 간 큐**의 증거일 뿐, 켜져 있다는 증거가 아니다 — 켜짐은 감독 눈으로만 확인됐다.
- ⑨ v3: 41줄 OK(`live/p9_a/`), 306~308 큐 크기 3748·3780·3760. 🔴 승인 문면의 재생 묶음이 `Goto 306 / Off 306 / Goto 307 / Off 307 / Goto 308` 을 한 번에 보내므로 circle·발리후는 눈으로 볼 틈이 없다 — 이번 문면으로 판정 가능한 것은 wave(308)뿐. wave 는 A2 와 거의 같은 꼴(Tilt 상대값 12 + `Phase 0 Thru 360` + Speed 60, 기준 프리셋 2.1). 감독 판정(리드 전달): wave **「멈춰 있음」**. circle·발리후는 **눈 미확인**. 끄기 `Off Sequence 306·307·308` OK(`live/p9_off/`).
  - 위상 펼침이 있는 wave 도 정지 → ⑤ 정지의 원인은 위상(단일값) 쪽이 아니라 **크기(12 vs 30)·선택(`Group 11` vs `Fixture 501…508`)·기준(프리셋 2.1 호출)·속도(60 vs 112)** 쪽으로 좁혀진다 — **가설**. 하나만 바꾼 시험은 ⑪ 뒤 설계안으로만(실행은 재승인).
  - **리드 가설 「상대값 한 단계면 정적 오프셋」은 t516 A2 실측으로 반증**(리드 동의, 2026-10-10).
- ⑩ v3: 11줄 OK(`live/p10_a/`). `Attribute 'Dimmer' At Phase 0 Thru 180` 을 콘솔이 받았다(끝값 180 문법 확인). 큐 크기 309.1 = 3608 vs ⑦ 큐1(303.1, 위상 줄 없음) = 3568 → +40(`p10_readback.txt`) — 위상이 큐에 들어갔다는 해석과 맞음(가설). 감독 판정(리드 전달): **「물결처럼 차례로」 → 통과**. 끄기 `Off Sequence 309` OK(`live/p10_off/`).
  - ⑤⑨ 정지 원인 후보 중 「Group 선택이라 페이저·위상이 안 먹는다」는 **약해졌다** — 같은 `Group 11` 선택에서 디머 페이저와 위상 펼침은 먹었다. 남는 차이는 위치 속성 쪽(크기·기준 프리셋 호출·속도). **엄밀한 홀짝 번갈아(0/180/0/180)는 여전히 미측정** — `Thru` 는 고르게 나누는 범위라 물결로 나왔다.
- ⑪ v3: 15줄 OK(`live/p11_a/`). 큐 크기 310.1 = **4272**, ⑦ 큐2(303.2) = **4272** — 바이트까지 같다(`p11_readback.txt`). 줄 순서(Step 2 한 번 뒤 재선택)를 바꿔도 콘솔이 같은 내용으로 저장했다는 해석과 맞음(**가설** — 크기 같음 ≠ 내용 같음). 감독 판정(리드 전달): **「둘 다 깜빡임」** → Step 2 위치(줄 순서)는 t520 실패 원인이 아니다(큐 바이트 동일과 일치). 끄기 `Off Sequence 310` OK(`live/p11_off/`).
  - t520 실패 원인 후보로 남은 것(**가설**): 선택 형태(`Fixture` 목록 + 서브픽스처 `.1`, 선택 다섯) · 속성 섞임(디머 + Pan/Tilt, 선택마다 Phase·Measure·SpeedMaster).
- ⑦ 보충(위치는 ⑦ 아래가 맞으나 기록 순서대로 둔다):
  - 「번갈아」의 근거 조사(t516·t519·t520 문서): **Step 2 하나로 장비가 번갈아 켜진 실측은 없다.** t516 이 확인한 것은 「페이저 실행(Dimmer 0↔100 2단계) 됨」(`t516/verdict.md:14`)으로, 번갈아인지 다 같이인지는 적혀 있지 않다. t520 의 SIDE 번갈이는 Step 2 가 아니라 **두 목록에 엇갈린 단계 값(0/100 · 100/0)** 을 준 설계였고(`t520/verdict.md:160`), §8 「2박마다 번갈아 켜짐」(`:220`)은 감독이 볼 것 — 기대이고, 실기에선 깜빡임 자체가 안 나왔다(`:693`). 위상 펼침(`Phase 0 Thru 360`)은 상대값 Tilt 한 단계에서 확인됐다(`t520/verdict.md:169`, t516 v4 A2) — 디머 2단계에는 안 쟀다.
  - 리드 가설(미측정): Step 2 는 값 두 개를 시간축에 놓을 뿐이고, 장비별 번갈아는 선택 전체에 위상을 펼쳐야(예: `Phase 0 Thru 180`) 나온다. 위 근거와 모순은 없다.
  - 속도 차이(④ SM15 + Measure 1 vs ⑦ 속도 지정 없음): ④가 박자 마스터를 따랐다는 간접 근거일 수 있다 — **가설**. t516 은 「Measure 1 빠름」을 감독 눈으로 확인했다(`t516/verdict.md:18`).
- v3 문면(③⑤⑨ `Attribute '<X>' At Preset` → `At Preset`, ③ 프리셋 번호 301→302): 바뀐 줄 10, `approval-diff-v3.md`. 리허설 3/3, 실기 전부-거절 3/3(실행 줄 0). 이전 문면은 `denyall_v2/`.

- 새 번호 비어 있음 실측: `.moai/reports/t531/r1_free_slots.txt`(실기 읽기). 실행 직전에 다시 읽는다.
- 실기 쇼 상태(읽기): 시퀀스 1-15·210·219·220-233·1999·2000, 타임코드 1·2·7·8·9·19·20·21 — t520 기록의 시퀀스 250번대·TC 22/23 은 없다(`r0_pools.txt`·`r0b_pools.txt`). Speed15 `NORMEDVALUE` 69.
- 리허설은 게이트 심사만 증명한다 — 가짜 콘솔은 명령의 콘솔 의미를 흉내 내지 않는다.
- 미측정 문법(설계 당시): ③ 프리셋 수정 줄, ⑥ `Goto Time 5 Timecode 31`, ④·⑤·⑨ 그룹 선택 프리셋 호출. → 실기 뒤: `Attribute '<X>' At Preset` 은 거절, `At Preset` 은 받음, `Store Preset … /Merge` 받음, ⑥ 은 여전히 문법 불명.
- **통과 판정은 ①(구조)·⑧·⑩·⑪(감독 눈) 넷이다.** ②④ 미확인, ③⑦ 부분, ⑤⑨ 움직임 없음(⑨ circle·발리후 미확인), ⑥ 미확인 — REQ-LDBEAT-001 게이트상 M4 송신은 ①⑧⑩⑪ 말고 어떤 항목에도 기대지 못한다.

**2026-10-11 대체 고지 (카드 t553)** — 위 ⑤⑨ 판정 문자열("움직임 없음"/
"wave 움직임 없음 · circle·발리후 미확인")은 **고치지 않는다**(원래 표
그대로 보존, 위 두 줄은 수정 없이 남겨 둔다). 다만 그 뒤 두 카드가 더
구체적인 실기 증거로 두 M1 항목의 일부를 대체했다:

- 원인: ⑤⑨가 "움직임 없음"으로 찍힌 건 **1단계 상대값**(`Step` 없음)을
  썼기 때문이었다 — grandMA3의 페이저는 최소 2단계가 필요하다(MA 공식
  문서 "two or more steps", `server/fx/schema.py:67` `MIN_STEPS=2`). 이
  사실은 카드 t540(앱 결함 카드, PR #588 머지 `72b5d042`)으로 고쳐졌다.
- MOVER-U(Group 11, Robin MegaPointe) — 카드 t538(2026-10-10)이 2단계
  해법을 실기로 확인했다: A0′(2단계 Tilt wave, 시퀀스 312) 물결로 움직임,
  A1(Group 11 선택, 313) 같은 물결, A3(기준 `At Preset 2.1`, 315) 프리셋
  자리 중심 물결, A5b(Pan+Tilt 위상 0/90 + 곡선, 323) 동그란 원 — 전부
  감독 육안 확인(`progress.md` 위 "M1 후속" 절 결과 표 참조, 상세 근거
  `.moai/reports/t538/`).
- MOVER-D(Group 12, Martin/Chauvet 계열 Spiider) — 카드 t548(2026-10-11)이
  같은 2단계 형태를 Spiider에서 처음 쟀다(`.moai/reports/t548/
  probe-moverd.md`): **D1**(seq 331, Tilt ±30 2단계 + 곡선 + 위상 펼침,
  한 바퀴 2마디) 프레임 변화 1.3~1.4%(정지 대조 0.00%) — 움직임. **D3**
  (seq 333, Tilt ±30 2단계 + 곡선, 한 바퀴 2박) 프레임 변화 1.0~1.3%,
  D1보다 빠름 — 움직임, 2박 vs 2마디와 일치. **D2**(seq 332, Pan ±30
  2단계, 기준 `At Preset 2.1`) 프레임 변화 0.02~0.03% — **판정 불가**
  (2.1 자리는 빔이 거의 수직 아래라 Pan이 빔 축 회전으로만 보임). **D2'**
  (seq 335, 같은 Pan 2단계지만 기준을 `Attribute 'Tilt' At 45`로 바꿈)
  프레임 변화 3.7~5.1% — 움직임(기준을 기울이자 비로소 보임).
  v0a(Dimmer만, 기준 2.1)는 **안 켜짐**, v0b(Dimmer+Dimmer2 추가)는
  **켜짐** — Spiider는 Dimmer2 없이는 안 켜진다.

**허용목록으로 옮긴 결론 (측정된 그룹·모양·축만, 느슨하게 풀지 않음)**:
`server/design/beat_grid_data/measured_movements.yaml` +
`server/design/beat_grid_measured.py`(카드 t553)가 `beat_grid_emit`의
M1 게이트를 다음 두 조합에서만 선택적으로 연다 — 둘 다 **group_no +
shape="wave" + axes 정확 일치**로만 매칭한다:

| 그룹 | 모양·축 | 게이트 | 근거 |
|---|---|---|---|
| MOVER-D(12) | wave, axes=[Tilt] | **열림**(base_condition=`any`) | D1·D3 — Tilt는 빔 각도 자체가 바뀌어 기준과 무관하게 보인다 |
| MOVER-D(12) | wave, axes=[Pan] | **영구 닫힘**(base_condition=`requires_tilted_base_unverifiable`) | D2(판정 불가)·D2'(기운 기준에서만 움직임) — 이 앱은 `position_preset_no`가 실제로 기운 자리인지 읽을 방법이 없다(M1 ⑥과 같은 한계) |
| MOVER-U(11) | wave, axes=[Pan] | 매칭 자체가 없음 → **그대로 닫힘** | Pan 단독은 MOVER-U에서 한 번도 라이브로 재지 않았다(t538은 2단계 Tilt·원만 쟀다) |

결과: LOVE ATTACK 데이터의 MOVER-D bar 7·22(둘 다 `app_movement`
shape=wave axes=[Tilt])는 이제 열린다. MOVER-U bar 11·18(둘 다
axes=[Pan])은 그대로 막힌다 — bar 11은 애초에 `period_unit`/
`period_value`가 없어(레이블이 주기를 말하지 않음) `app_movement_
commands`가 그 전에 먼저 거절한다(지어내지 않음, M1 게이트와 무관한
별개 사유).

**Dimmer2 확인(코드 추적, 콘솔 접촉 0)**: `app_movement.brightness_
value_commands`는 `dimmer_attributes` 인자로 받은 **모든** 디머 계열
속성(정규식 `^dimmer\d*$`)에 한 줄씩 낸다 — Spiider처럼 Dimmer+Dimmer2
둘 다 필요한 기구도 호출자가 두 이름을 넘기기만 하면 이미 일반적으로
처리된다(코드 수정 불필요). 다만 `love_attack.yaml`의 MOVER-D 큐
전체(bar 0·3·7·11·14·18·22)를 grep하면 **`brightness` 필드가 하나도
없다** — bar 7·22의 `app_movement`(이제 게이트가 열림) 큐는 Dimmer/
Dimmer2 명령을 **전혀 내지 않는다**. 이 트랙의 다른 큐에도 brightness가
없어, 이 데이터 그대로는 MOVER-D가 격자 전체에서 한 번도 켜지는 큐가
없다(이전 큐에서 이미 켜져 있지 않은 한 빔이 안 보일 수 있다) — **이건
보고만 한다, 이 카드 범위를 벗어난 데이터 보강이라 고치지 않았다.**

### M1 후속 — 무빙 움직임 원인 가르기 + 위치 프리셋 큐 (카드 t538, lane-3, 브랜치 `WT-mover-probe`)


기준 `156a1d08`(origin/main, #582 뒤). 측정일 2026-10-10. 실기 쓰기는 승인 문면 안의 줄만 보냈다. 승인 목록은 `approval_t538.txt` → `approval_t3.txt` → `approval_t45.txt` → `approval_t538_v3.txt`(215줄, sha256 `430e2ab4…`)이고, 모두 리허설과 실기 전부-거절을 먼저 거쳤다. 쇼 저장은 0회다. 감독 판정은 모두 리드를 거쳐 전달받았다. 근거는 `.moai/reports/t538/`에 있다(진단 `a0-stop-diag.md`, 실기 `live/`).

**조건**: 장비는 Robin MegaPointe(MOVER-U 501~508, Mode 1, 디머 1개)다. 선택은 `Fixture 501…508` 또는 `Group 11`이다(Group 11 = 501~508 정확히, `r3_group11_fid.txt`). 콘솔은 grandMA3 onPC + 응답기 1.6.6이고, 감독은 onPC 3D 와 Fixture Sheet 를 보고 판정했다. 아래 결론은 모두 이 조건에서 잰 것이다. 다른 기종과 다른 그룹 순서에서는 재지 않았다.

**결과 표**

| 항목 | 결론 (조건 포함) | 근거 |
|---|---|---|
| 1단계 상대값 | **페이저가 아니다.** MegaPointe·Fixture 501~508 에서 `Tilt At Relative 30` + `Phase 0 Thru 360` + `Speed 112` 를 `Step` 없이 보내면, 위치만 한 번 바뀌고 Fixture Sheet 의 Tilt 숫자가 멈춘다(T3). 시퀀스(A0 311)와 프로그래머(T3) 둘 다 정지했다. | 감독 「위치는 바뀌었는데 무빙은 안 됨」·「숫자가 멈춰 있음」. 앱 룰북 `33_effect_editors.md:21-22`, `server/fx/schema.py:67` MIN_STEPS=2, MA 공식 Phasers 「two or more steps」 |
| 2단계 해법 | `… ; Attribute 'Tilt' At Relative -30` / `Step 2` / `Attribute 'Tilt' At Relative 30` + `Phase 0 Thru 360` + `Speed 112` → 물결로 움직인다. 프로그래머(T4)와 시퀀스 저장·재생(A0′ 312) 둘 다 움직였다. | 감독 「물결처럼 움직임」 ×2 |
| 선택 | 2단계 페이저는 `Group 11` 선택에서도 움직이고(A1 313), 물결 순서도 Fixture 목록과 같다. 다른 그룹(내부 순서가 501→508 이 아닌 그룹)은 재지 않았다. | 감독 「움직이고 물결 순서도 같음」 |
| 크기 | ±12 도 2단계면 보인다(A2 314). ⑤의 정지는 크기 탓이 아니라 1단계였기 때문이다. | 감독 「작지만 보임」 |
| 기준 위치 | `At Preset 2.1` 을 기준으로 둔 2단계 상대 페이저는 프리셋 자리를 중심으로 움직인다(A3 315). → ⑤⑨ 정지 원인은 1단계다. 기준 줄이 없으면 기본 위치(수직) 중심으로 움직인다(A4 316). → 무빙 효과 큐에는 기준 위치 줄이 필요하다(앱 규칙 후보). | 감독 「프리셋 자리 중심으로 물결」·「수직/기본 자리 중심」 |
| 원 모양 | Pan+Tilt 2단계 ±30, 위상 0/90, 곡선 없음이면 모서리 진 마름모가 나온다(A5 317). 여기에 단계마다 `Step k At Accel -100`·`At Decel -100` 을 더하면 동그란 원이 된다(A5b 323, 112 BPM 에서도 구분됨). 이것이 원의 정답 형태다. | 감독 「마름모」·「동그란 원」 |
| 곡선 | Tilt 2단계 페이저에 곡선 4줄을 더하면 끝에서 부드럽게 돌아온다. 이 차이는 Speed 30 에서 보이고 112 에서는 안 보인다(T4s/T5s, T4/T5). | 감독 「끝에서 턱 꺾임」 vs 「부드럽게 돌아옴」, 112 에선 「차이를 모르겠다」 |
| PositionMSpeed | MegaPointe 채널 3 `PositionMSpeed` 의 기본값은 「Track 80%」(빠름)다. 0 을 넣어도 1단계 정지는 그대로였다(T1). 이 채널은 원인이 아니다. 채널이 있는지와 기본값은 패치의 FixtureType→DMXMode→DMXChannels 에서 읽힌다. | `r10`·`r12`·`r13`, 감독 「여전히 멈춰 있음」 |
| 쇼 효과 프리셋 | 21.2(이름 PT-CIRCLE)는 Group 11 에서 움직이지만 원이 아니다(A6a 318). 21.5(TILT-SWEEP)는 이름대로 위아래로 쓴다(A6b 319). **프리셋 이름을 모양의 근거로 쓰지 않는다.** | 감독 「다른 모양으로 움직임」·「위아래로 쓸기」 |
| 위치 프리셋 큐 | `Store … CueFade` 는 먹는다(쓸고 간다). 단 큐1(2.1)→큐2(2.4)에서 팬이 180° 돈다. 큐2↔큐3(2.4↔2.5)에서는 8대 중 반만 180° 팬했다(어느 4대인지는 미측정). 큐3↔큐4(2.5↔2.3)는 세 번 봐도 「안 움직임」이었다(원인 미확정, 아래). 2.1 은 실제로 「조금 무대 앞, 틸트업」을 본다 — 이름(보컬 센터)과 다르다(B1 320). | 감독 원문 각 회차, `live/v3_B1_*` |
| 팬 반대편 해 (가설) | 같은 쪽을 비추는 두 프리셋이라도 장비마다 Pan 이 약 180° 떨어진 「반대편 해」로 저장돼 있으면, 페이드가 팬을 반 바퀴 돌린다. 점검은 프리셋 단위가 아니라 **장비 단위 Pan 차이**로 해야 한다. 프리셋 값을 읽을 수 없어 미측정이다. | 리드 정리, 감독 관찰과 일치 |
| Follow 반복 | 큐마다 `Set Cue k Sequence n Property 'TrigType' 'Follow'` 를 두고 새 시퀀스 기본값 `WRAPAROUND` true 를 쓰면, 누르지 않아도 네 자리를 돌고 되감아 반복한다(B2 321). CURRENTCUE 연속 판독도 321.2→3→4→1 로 같은 결과였다. | 감독 「혼자 계속 돎」, `live/v3_B2_currentcue.txt` |
| MIB | 앱 `apply_mib`/`position_cue_bundle`/`premove_follow_command` 가 낸 줄 그대로 쓴다: 큐1 켜짐 → `Go+ Sequence 322` → 큐2 암전 + 큐2.5(Follow)가 어둠 속에서 미리 이동 → `Go+ Sequence 322` → 큐3 이 이미 새 자리를 보고 켜진다(B3 322, 이어 보기 3회). `Go+ Sequence <n>` 은 이 저장소 첫 사용이고 콘솔이 받았다. | 감독 「꺼진 후 이동만」·「이미 새 자리」 |
| CURRENTCUE | 진행 순서를 보는 데는 쓸 수 있다(B2). 그러나 지금 상태의 증거는 아니다: B3 에서 Go+ 한 번 뒤 무대는 큐3 점등 전 대기였는데, 값은 「322.3」을 4회 읽었다. ⑨(Off 뒤에도 남음)와 같은 한계다. | `live/v3_B3_after_dark.txt` |
| 프리셋 값 읽기 | 응답기 1.6.6 으로는 프리셋 Pan/Tilt 값을 **못 읽는다.** 프리셋 2.1·2.4 의 속성 138개 중 `PRESETDATA` 는 "", `SELECTIONDATA` 는 `{}`, state childCount 는 0 이다. DMX 출력값을 읽는 길도 없다(응답기 verb 는 ping/state/prop/props/introspect/exec/deploy 일곱 개, `Patch/DmxUniverses`·`RTChannels` 에는 기본값 필드만 있다). 장비 단위 Pan 차이 점검에는 응답기 코드 카드가 필요하다. | `r24`·`r26`·`r27` |

**t516 A2 「움직임」 전제는 감독 원문이 아니었다 (리드 실수로 기록)**: 카드 t538 은 A0(t516 A2 재현)을 「알려진 성공」으로 두었다. 그런데 t516 의 감독 원문은 「235 … 확인 못했어 … 242~244 켜진거 없어」와 「나머지는 모두 확인했어」뿐이다. 「236·237 Tilt 움직임」은 리드 정리로 붙은 해석이다(`t516/verdict.md:385`). 카드 본문과 t531 설계안은 이 정리를 「감독 『움직임』」으로 옮겼고, 이 레인도 원문을 대조하지 않고 받아 썼다. 2단계 움직임에는 감독 원문이 있다(t516 v5 E2 247 「좌우로 흔들렸어」).

**앱 결함 (리드가 카드 t540 으로 만듦)**: `server/spatial/position_fx.py` 의 circle·wave·ballyhoo 는 1단계 상대값이라 페이저가 아니다. ⑤⑨ 정지와 원인이 같다. 고칠 때 정답 형태는 위 「2단계 해법」과 「원 모양」(A5b)이다.

**콘솔에 남은 새 객체**(읽어서 확인, `live/final_leftovers.txt`, 모두 Off): 시퀀스 311~323, 13개.

| 번호 | 이름 |
|---|---|
| 311 | T538 - A0 A2 replay (1단계, 정지) |
| 312~317 | A0′ 2단계 · A1 group 11 · A2 relative 12 · A3 base preset 2-1 · A4 no base · A5 pan tilt circle |
| 318·319 | A6a fx preset 21-2 · A6b fx preset 21-5 |
| 320·321·322 | B1 position cues · B2 follow loop · B3 MIB |
| 323 | A5b pan tilt circle curve |

- 프리셋·타임코드·실행기는 새로 만들지 않았다.
- 프로그래머는 T5s 뒤 `ClearAll` 로 비웠고, 선택은 0대다.
- 쇼 저장이 0회라서 쇼를 다시 열면 이 객체들은 사라진다. 지울지는 리드·감독이 정한다.

**안 잰 것(Gaps)**

- 큐3↔큐4(2.5↔2.3) 「안 움직임」의 원인은 모른다. 2.3·2.5 둘 다 `OWNDATAPRESENT` true 라서(`r28`) 「값 없음 → 트래킹」 가설은 기각했다. 「두 프리셋이 이 8대에서 거의 같은 자리」 가설은 프리셋 값을 못 읽어 재지 않았다.
- 🔴 프리셋 2.4·2.5 의 크기가 오늘 첫 판독(`r6`)보다 각각 +256B 커졌다(2176→2432, 2640→2896). 2.1·2.2·2.3·2.6 은 그대로다. 이 레인은 프리셋에 Store/Edit 를 0줄 보냈다. 원인은 재지 않았고, 감독에게 아직 묻지 않았다.
- B1 에서 180° 팬한 4대가 어느 장비인지는 재지 않았다.
- `Goto` 가 큐 페이드를 쓰는지는 B1 에서 「쓸고 감」으로 보였다. 다만 `TIMINGGOTO` 값의 뜻은 재지 않았다.
- 다른 기종(디머가 여럿인 Spiider·Aura XB)과 다른 그룹 순서에서는 아무것도 재지 않았다.

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

### t537 ① plan 개정

기준 `640235f5`(origin/main, PR#581 = 카드 t534 포함). 작업 내용: plan-phase 개정뿐 — 코드 diff 0줄, 콘솔 접촉 0건. 감독 결정(2026-10-10, 리드 경유) 「전체 화면 + 속성별 값」을 spec.md/plan.md/acceptance.md에 반영했다.

- **App.tsx 금지 완화**: REQ-LDBEAT-004(a)(g)를 교정 — 박자 격자는 런북 모드 안의 **독립 전체화면 뷰**이고(기존 5블록 사이 블록이 아니다), `App.tsx`의 `runbookMode` 참 분기 안에 그 뷰로의 전환을 추가하는 것은 더 이상 범위 밖이 아니다. 코파일럿 **메인** 화면(`runbookMode` 거짓)은 그대로 PRESERVE. `CueSheetTimeline*`·`emit*`·`songcue*`·`cue_sheet_edit*`·`console/lua/**`도 그대로 금지.
- **칸 데이터 구조화**: REQ-LDBEAT-006에 (i)~(iii) 신설 — `BeatGridCue`를 단일 `label`에서 밝기(`brightness`: 값/디머 프리셋/디머 효과 중 정확히 하나)·`position_preset_no`·`color_preset_no`·`effect_preset_no`·들어올 때(`entry`: 페이드초+MIB)로 구조화한다. 레거시 `{bar,label}` 칸은 다섯 필드를 전부 미정(`null`)으로 두고 `label`만 그대로 보여준다(파싱·추측 금지). REQ-LDBEAT-004(h) 겹침 거절(트랙 레벨 `group_name` 비교)은 이 칸 레벨 변경과 독립임을 재확인(`server/design/beat_grid.py` 재독).
- **미정 하드룰**: REQ-LDBEAT-015(f) 신설 — 배치 규칙서(§2~§4)·t525류 실측 출처 없는 프리셋 번호는 지어내지 않고 미정(`null`)으로 남긴다. **실측**: `reports/effect-arrangement-rules-20261007.md` §4(0~25마디 격자) 전수 재독 — 프리셋 **번호는 0개**(전부 정성 서술). §2 "그룹(선택 하나)" 칸의 숫자(Group 4/7/11/12)는 트랙의 콘솔 그룹 번호이지 칸 레벨 프리셋 번호가 아니다. `server/design/beat_grid.py` `_love_attack_tracks()`의 기존 30개 큐(BACK 7·SIDE-ALL 7·MOVER-U 7·MOVER-D 7·BLIND 2·STROBE 0)는 전부 `label` 자유 텍스트뿐이라 이 규칙과 충돌하지 않는다 — M3/M7 구조화 시 30개 전부의 네 프리셋 필드는 미정에서 시작(지어낸 번호 0건). `reports/ldbeat-runbook-ui-proposal-20261008.html`의 `P` 객체(`4.21`·`2.41`·`1.31` 등)는 그 시안 자신이 지어낸 예시 데이터이고 배치 규칙서의 출처가 아니다 — 베끼면 이 규칙 위반.
- **M1 상태 실시간 읽기**: REQ-LDBEAT-003(b) 신설 — 화면의 M1 9항목 판정은 `progress.md`를 읽어 오는 살아있는 소스여야 하며, 손으로 옮긴 TS 상수(`ui/src/components/beatGridM1Probes.ts`, 카드 t534 신설)로 영구히 대체하는 것은 금지다 — 이 바로 위 M2 후속 절이 스스로 적어 둔 "M1 프로브 상수가 낡을 수 있음" 위험을 REQ로 못박았다.
- **plan.md**: §A 범위·§B 위험(12·13 신설)·§D 제약(2건 신설)·§E M7 신설(전체화면 전환 + 칸 구조화 + M1 실시간 읽기 + 막대 채우기 미정 렌더 규칙 + 시안 대조 캡처, 결정 번복 비용 순)·§F 안티패턴(4건 신설)·§G 교차 참조(`beat_grid.py`/`protocol.ts`/`beatGridM1Probes.ts` 좌표 추가)를 갱신했다.
- **acceptance.md**: AC-LDBEAT-003(d)·AC-LDBEAT-009(c)·AC-LDBEAT-016(e) 하위 시나리오 신설(새 AC-ID 없음, 16/16 유지), §A.1에 REQ-006→AC-016(e) 추가 매핑, §D DoD에 5개 항목 신설.
- **REQ/AC 총량 불변** — REQ 15개(기존 REQ-003/004/006/015에 하위 절만 추가), AC 16개(기존 AC에 하위 시나리오만 추가). version 0.2.1→0.3.0. plan-audit 재실행 필요(다음 run-phase 착수 전).
- **배치 규칙서 §4 측정 결과(이 개정의 핵심 실측)**: 프리셋 번호 기재 0개 / 미정 대상 30개 큐 × 4필드(brightness preset/position/color/effect) = 최대 120개 필드 슬롯, 전부 미정으로 시작해야 함(배치 규칙서가 준 숫자가 전무하므로).
- **열지 못한 결정**: §5 항목 6(전체화면 전환 트리거의 정확한 UI 모양 — 탭/버튼/자리)은 입력 보고서에 명시가 없어 M2(phase ②)가 director와 확정하도록 열어 두었다.

### t537 ① 개정 2 — plan-audit 독립 감사 FAIL(0.55) 대응

`.moai/reports/t537/plan-audit.md` — MP-2(GEARS 형식) FAIL + Clarity/Completeness/Testability/Traceability 전부 0.50. 코드 diff 0줄, 콘솔 접촉 0건.

- **D1(blocking)**: REQ-LDBEAT-006(i)·(ii)가 트리거 없는 평서문 부속 요구를 다시 들여온 재발(iteration 1/2와 같은 패턴) — (i-1)~(i-7)·(ii-1)~(ii-5) 라벨 하위 절로 재구조화(새 REQ-ID 없음).
- **D2(blocking)**: `reports/effect-arrangement-rules-20261007.md:98-115`(§4) 전수 재독 결과 프리셋 번호는 0개지만 밝기 퍼센트·마디 단위 페이드 힌트는 명시돼 있다는 것을 실측 — `entry.fade_seconds`를 `entry.fade_bars`(마디 수)로 바꾸고 `source_ref` 필드를 신설해, 실제 30개 큐 중 §4가 숫자로 준 네 자리(BACK@7/18/22마디·BLIND@18마디, 전부 `brightness.value_percent`)만 전사하고 나머지는 미정으로 남기는 규칙을 REQ-LDBEAT-006(i-4)~(i-7)에 명시. acceptance.md에 전사값 기대표(§A 보충)와 AC-LDBEAT-016(f)를 신설.
- **D3·D4(blocking)**: §A.1의 과잉 매핑 주장을 AC-LDBEAT-016(g)(레거시 읽기+label-파싱 부재 grep)·(h)(겹침 독립성)·AC-LDBEAT-009(d)(M1 실패-경로)로 맞췄다.
- **D5(blocking, minor)**: AC-LDBEAT-009(c) 검증 수단에 빌드 타임 생성 경로 조건부 문구 추가.
- **D6(blocking, minor)**: AC-LDBEAT-016(g)에 label-파싱 함수 부재 grep 추가.
- **D7·D8(optional)**: "656행"→"655행", HISTORY의 "AC-LDBEAT-016(f)" 오기→"(e)" 정정.
- **D9(optional)**: REQ-LDBEAT-006(i-3)에 `effect_kind` 필드 신설(색/혼합 효과 풀 구분), §5 열린 결정 7항 추가.
- plan.md M7 (1)의 데이터 모양 블록을 `fade_bars`/`effect_kind`/`source_ref`로 갱신.
- **REQ 15개·AC 16개 총량 불변.** plan-audit 재감사(D1~D9 delta 스코프) 요청.

### t537 ② 구현 — 전체 화면 + 속성별 값 (카드 t537, 브랜치 `WT-ldbeat-fullview-impl`)

기준: `e0612b8d`(승인된 plan 개정, PR #584 머지분 — plan-audit PASS `.moai/reports/t537/plan-audit.md`)를 `156a1d08`(origin/main, lane-3 M1 실기 결과 포함)와 ff-merge. cycle_type=tdd — Python 쪽은 모듈 삭제→RED 확인→재작성(GREEN)으로 엄격히 지켰고, TS 쪽은 `protocol.ts` 타입 변경이 `BeatGrid.tsx`·`BeatGrid.test.tsx`를 동시에 컴파일 불가로 만들어(TypedDict 필드 추가가 기존 전수 테스트 픽스처를 깨뜨림) 완전한 RED→GREEN 분리가 Python만큼 깨끗하지 않았다 — 정직하게 §Gaps에 남긴다. 콘솔 접촉 0건.

**(1) 칸 데이터 구조화(REQ-LDBEAT-006(i-1)~(i-7)·(ii-1)~(ii-5)·(iii))** — `server/design/beat_grid.py`의 `BeatGridCue`를 `{bar,label}`에서 `{bar,label,brightness:{mode,value_percent,preset_no},position_preset_no,color_preset_no,effect_preset_no,effect_kind,entry:{fade_bars,mib_mode},source_ref}`로 확장했다. 새 읽기 경로 `normalize_beat_grid_cue`(레거시·부분 선언 둘 다 받아 다섯 구조화 필드를 전부 채운 완전한 모양으로 — `label` 파싱 0건, `inspect.getsource` grep으로 확인)를 신설했다. LOVE ATTACK 30개 큐 중 §4(`reports/effect-arrangement-rules-20261007.md:98-115`)가 숫자로 준 **네 자리만** 전사됐다(BACK@7마디=60%·@18마디=100%·@22마디=100%, BLIND@18마디=100%, 전부 `brightness.value_percent`+`source_ref`) — 나머지 26개 큐의 `value_percent`와 30개 전부의 `entry.fade_bars`·네 프리셋 번호 필드는 `None`이다(§A 보충 전사값 기대표와 1:1 대조하는 단위시험으로 확인, 아래 §검증). `ui/src/protocol.ts`의 `BeatGridCue`도 같은 모양으로 확장했다.

**(2) 전체화면 전환(REQ-LDBEAT-004(a)(g))** — `RunbookMode.tsx`에서 `<BeatGrid>`를 완전히 빼냈다(기존 5블록 사이 블록 배선 제거, `beatGridFixtures`/`beatGridProbeResults` prop도 같이 제거). `App.tsx`의 `runbookMode` 참 분기에 `beatGridFullscreen` 상태(세션-휘발성, `paperworkMode`와 같은 패턴)와 헤더 토글 버튼(「박자 배치」, `runbookMode`가 참일 때만 보임)을 신설해, `runbookMode && beatGridFullscreen` 분기가 `<BeatGrid>`를 전체화면 루트로 렌더한다. 기존 `runbookMode` 단독 분기(5블록+채팅)와 메인 화면(`runbookMode` 거짓) 분기는 그대로다 — `git diff --stat e0612b8d -- ui/src/App.tsx`가 33줄(+import 1·+state 1·+토글 버튼 1·+분기 1)뿐임을 아래 §검증에서 확인.

**(3) 막대 채우기 색 규칙(plan.md M7 (3))** — 새 순수함수 `cueColorFill(cue, colorPresetHex?)`: `color_preset_no`가 없거나, 있어도 `colorPresetHex`에 그 색이 없으면(이 카드는 콘솔 접촉 0이라 아직 이 표 자체가 없다) **중립**(해칭 CSS, `.is-color-unset`) — 임의 색을 지어내지 않는다. LOVE ATTACK 30개 큐는 전부 `color_preset_no=null`이라(§4에 번호가 없음, REQ-LDBEAT-015(f)) 지금 화면은 전부 해칭으로 보인다 — 이것이 **정확한 모습**이다(아래 캡처로 확인).

**(4) M1 상태 실시간 읽기(REQ-LDBEAT-003(b))** — 신설 모듈 `server/design/beat_grid_probes.py`의 `parse_m1_probe_table`(progress.md의 `① 통과(구조)` 같은 판정 칸 텍스트를 `**`만 벗겨 그대로 돌려줌, 1~9항목만 — ⑩⑪ 확장 항목 제외)과 `read_m1_probe_results`/`read_m1_probe_results_from_path`(표 부재·파싱 실패 시 9항목 전부 `"미확인"`, 지어낸 PASS 0건)를 신설했다. `server/design/beat_grid.py`에 `attach_beat_grid_runtime_extras(payload, progress_md_path=None)`를 신설해 `server/web/session.py`의 `_song_timeline_payload`가 `attach_beat_grid_default` 뒤에 이 함수를 추가로 거치게 배선했다(`attach_beat_grid_default` 자체의 "있으면 바이트 그대로 보존" 계약은 건드리지 않음 — 별도 단계). `ui/src/components/beatGridM1Probes.ts`(카드 t534가 만든 손-복사 상수)와 그 테스트는 삭제했다 — `BeatGrid.tsx`의 `ProbeStatus`를 고정 네 상태(`"pass"|"fail"|"미실행"|"리허설PASS·실기미실행"`)에서 `string`(progress.md 판정 칸 자유 문자열)으로 바꾸고, `isWriteLocked`는 "통과"로 시작하는지, `probeStatusClass`는 "통과" 접두/정확히 "미확인"/그 밖(fail)으로 분류한다. `RunbookMode.tsx`는 이제 이 prop들을 아예 안 받고(제거), `App.tsx`의 전체화면 `<BeatGrid>`는 `grid.probe_results`를 직접 읽는다(prop으로 override 안 함) — **실제로 돌아가는지** `server/web/session.py`의 진짜 배선을 통해 이 저장소의 진짜 progress.md를 읽어 확인했다(아래 §검증 `TestLiveProbeReadThroughTheRealSessionWiring`): 지금 이 표는 `{1: "통과(구조)", 2: "미확인", 3: "부분", 4: "미확인", 5: "움직임 없음", 6: "미확인 — 문법 불명", 7: "부분(결과 기록)", 8: "통과", 9: "wave 움직임 없음 · circle·발리후 미확인"}`.

**(5) SCENE 메모 — 리드 추가 지시(2026-10-10), §REQ-006 밖의 새 데이터 요소(감사 필요)** — §4 SCENE 열 값(BACK/WASH/FOH가 섞인 역할·효과 혼성 칸, 카드 t526이 이미 "SCENE은 단일 콘솔 그룹이 아니라서 트랙에서 뺐다"고 결정한 바로 그 열)은 리드 규칙(세 조건 모두: (a) §4 칸이 그룹을 직접 부르고 (b) 그 그룹 번호가 이미 `beat_grid_data/love_attack.yaml`의 확인된 트랙에 있고 (c) 그 마디·트랙 자리에 기존 큐와 충돌이 없을 때만 그 트랙에 얹는다, 그 밖은 메모 — `classify_scene_cell_assignment`(plan-audit iteration 3 D4)가 이 세 조건을 그대로 파라미터화한다)을 전수 적용한 결과 **여섯 값 전부가 메모로 떨어졌다** — BACK(bar 0)은 그룹 번호가 확인돼 있지만 그 마디에 이미 펄스 큐(「앞박 1회」)가 있어 충돌, WASH·FOH는 이 데이터 파일에 트랙 자체가 없어(그룹 번호 미확인) 메모, 나머지 셋(11~13·18~21·22~25)은 칸 자체가 그룹 이름을 안 부름. `BeatGridView.scene_memos: list[{bar,text,source_ref}]`로 겹침 검증 로직과 완전히 분리된 새 리스트에 담았고(트랙 `cues`에 끼워 넣지 않음 — `TestOverlapIndependentOfCellStructuring`로 확인), UI는 곡 전체 지도의 해당 행에 「미정」 배지(`.has-scene-memo`, 주황 테두리)와 "이 마디 한눈에" 패널 위에 경고 배너(원문 그대로 + `source_ref`)로 보여준다. **이 데이터 요소(`scene_memos`)는 spec.md REQ-LDBEAT-006이 정의한 범위 밖이다** — REQ-006은 트랙 `BeatGridCue`의 구조화만 다루고 "트랙에 못 옮기는 §4 값을 메모로 보존한다"는 요구는 spec.md 어디에도 없다. spec.md는 고치지 않았다(리드 지시대로) — 이 추가가 REQ-006 확장으로 정식 편입돼야 하는지(또는 신설 REQ가 필요한지)는 **다음 plan-audit/감사 라운드의 판단 대상**으로 남긴다.

**(6) 리그·곡 일반화(카드 t537 추가 지시 2, 감독 원칙 2026-10-10)** — `server/design/beat_grid.py`의 로더(`default_beat_grid`·`_build_track_from_data`·`normalize_beat_grid_cue`·`find_overlapping_group_tracks`)에서 LOVE ATTACK 전용 그룹 번호·이름·큐 내용을 전부 들어냈다 — 전부 신설 데이터 파일 `server/design/beat_grid_data/love_attack.yaml`(YAML, `server/measurement/corpus.yaml` 선례와 같은 모양) 하나로 옮기고, Python 쪽에 남은 유일한 곡-특정 결정은 `_SONG_DEFAULT_FILES`(곡 제목 정규화 키 → YAML 경로) 딕셔너리 한 줄이다. 새 단위시험 `TestLoaderIsRigAndSongAgnostic`이 (a) 전혀 다른 가짜 그룹 번호(999)·이름("WEIRD-GROUP-99")을 담은 가짜 YAML을 레지스트리에 끼워 넣어 로더가 그 데이터를 그대로 돌려주는지(LOVE ATTACK 이름이 전혀 안 섞이는지), (b) `find_overlapping_group_tracks` 소스에 리그 전용 리터럴(BACK/MOVER-U 등)이 0건인지를 `inspect.getsource` grep으로 확인한다. UI 쪽(`BeatGrid.tsx`)은 이미 M2/M2후속부터 그룹 번호·장비 종류를 하드코딩하지 않았다(재확인 — `grep -n "201\|301\|501\|601\|Aura XB\|MegaPointe" ui/src/components/BeatGrid.tsx` → 0건, 전부 `track.group_name`/`fixture.confirmedGroupName` 같은 데이터 필드로만 읽는다). **이 변경에서 이 리그·이 곡에만 맞는 것**: `server/design/beat_grid_data/love_attack.yaml`(그룹 번호 4/7/11/12/14, 트랙 이름 6개, 큐 30개, SCENE 메모 6개) + `.moai/reports/t537/`의 캡처 고정값(`love_attack_beat_grid.json`은 이 YAML을 그대로 덤프한 것, `stage_fixtures.json`은 t525가 실측한 이 리그의 8대 확인 그룹) — 그 밖의 로더·렌더 로직은 어떤 그룹 번호·이름·장비 종류도 하드코딩하지 않는다.

**만든/고친 파일**:

- `server/design/beat_grid.py` — `BeatGridCue`/`BeatGridBrightness`/`BeatGridEntry`/`SceneMemo`/`BeatGridView` 구조화, `_love_attack_tracks()` 제거(YAML 로더로 대체), `normalize_beat_grid_cue`/`_build_track_from_data`/`_build_scene_memo_from_data`/`_load_song_default_document`/`attach_beat_grid_runtime_extras` 신설.
- `server/design/beat_grid_data/love_attack.yaml`(신설) — LOVE ATTACK 전용 데이터(트랙 6개·큐 30개·SCENE 메모 6개).
- `server/design/beat_grid_probes.py`(신설) — `parse_m1_probe_table`/`read_m1_probe_results`/`read_m1_probe_results_from_path`/`default_progress_md_path`.
- `server/web/session.py` — `attach_beat_grid_runtime_extras` 배선(1곳, `_song_timeline_payload` 끝).
- `server/tests/test_beat_grid_t537.py`(신설, 21개)·`server/tests/test_beat_grid_probes_t537.py`(신설, 11개).
- `ui/src/protocol.ts` — `BeatGridBrightness`/`BeatGridEntry`/`BeatGridSceneMemo` 신설, `BeatGridCue`/`BeatGridView` 확장.
- `ui/src/components/BeatGrid.tsx` — 구조화 필드 표시 헬퍼 7종(`formatBrightnessField` 등) + `cueColorFill` + `sceneMemoForBar` 신설, `ProbeStatus`를 `string`으로, 큐 편집 칸·곡 전체 지도·이 마디 한눈에 렌더 갱신.
- `ui/src/components/BeatGrid.test.tsx` — 신규 테스트 46개 추가(69개로 증가), 레거시 픽스처 헬퍼 갱신.
- `ui/src/components/RunbookMode.tsx` — `<BeatGrid>` 배선 제거, 관련 prop 2개 제거.
- `ui/src/components/beatGridM1Probes.ts`·`beatGridM1Probes.test.ts`(삭제).
- `ui/src/App.tsx` — `BeatGrid` import, `beatGridFullscreen` 상태, 헤더 토글, 전체화면 렌더 분기(33줄, `runbookMode` 범위 안).
- `ui/src/styles.css` — `.beat-grid-fullscreen-*`·`.beat-grid-scene-memo-*`·`.is-color-unset`·`.is-unset`·`.beat-grid-cue-field-derived` 신설, `.beat-grid-probe-rehearsal`→`.beat-grid-probe-pending`(의미 교정, `probeStatusClass`가 더 이상 "rehearsal"을 안 돌려줌).

**검증**:

```
$ uv run --quiet pytest server/tests/test_beat_grid_t532.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_probes_t537.py -q
...................................................
51 passed in 0.42s

$ uv run ruff check server/design/beat_grid.py server/design/beat_grid_probes.py server/web/session.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_probes_t537.py
All checks passed!

$ uv run ruff format --check server/design/beat_grid.py server/design/beat_grid_probes.py server/web/session.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_probes_t537.py
5 files already formatted

$ cd ui && npx tsc --noEmit
(종료 코드 0, 출력 없음)

$ npx vitest run src/components/BeatGrid.test.tsx src/components/RunbookMode.test.tsx src/App.test.tsx
 ✓ src/components/BeatGrid.test.tsx (69 tests)
 ✓ src/components/RunbookMode.test.tsx (16 tests)
 ✓ src/App.test.tsx (30 tests)
 Test Files  3 passed (3) · Tests  115 passed (115)

$ git diff --stat e0612b8d -- ui/src/components/CueSheetTimeline.tsx 'CueSheetTimeline*' 'emit*' 'songcue*' 'cue_sheet_edit*' 'console/lua/**'
(출력 없음 — 금지 파일 0 diff)
```

**RED 확인(Python, cycle_type=tdd 그대로 지킴)** — `server/design/beat_grid_probes.py`를 임시로 치우고 `test_beat_grid_probes_t537.py` 실행 → `ModuleNotFoundError: No module named 'server.design.beat_grid_probes'`(수집 단계 에러, 1 error). 되돌린 뒤 11 passed. `test_beat_grid_t537.py`도 구현 전에는 `ImportError: cannot import name 'attach_beat_grid_runtime_extras'`로 수집 실패했다(beat_grid.py 재작성 전 상태) — 재작성 후 20→(리그 일반화 추가 시험 포함)21 passed.

**RED 확인(TS, 불완전 — 정직하게 남김)**: `protocol.ts`의 `BeatGridCue` 필드 확장이 `BeatGrid.test.tsx`의 기존 `cue()` 헬퍼·`LOVE_ATTACK_GRID` 픽스처를 동시에 타입 에러로 만들어(`tsc`가 `BeatGrid.tsx` 구현이 없어도 "속성 누락" 에러를 내므로), 새 함수(`formatBrightnessField` 등) 전용의 깨끗한 RED 캡처가 Python만큼 분리되지 않았다 — 구현과 테스트 추가를 거의 동시에 진행했다(§Gaps 참조, TDD 엄격도 미달).

**SCENE 메모 규칙(한 줄, PR 본문용)**: §4 SCENE 열 값은 "그 칸이 그룹을 직접 부르고 그 그룹 번호가 이미 확인돼 있을 때만, 충돌 없으면" 그 트랙에 얹고, 그 밖엔(이번엔 여섯 전부) 트랙에 끼워 넣지 않고 `scene_memos`(겹침 검증과 독립)로만 남겨 화면에 「미정」 배지+원문 배너로 보여준다 — 이것은 REQ-LDBEAT-006이 정의한 범위 밖의 새 데이터 요소이므로 spec.md를 고치지 않고 이 섹션에만 기록했고, REQ-006 편입 여부는 다음 감사 라운드 판단 대상이다.

**리그 일반화(한 줄, PR 본문용)**: 이 변경에서 이 리그·이 곡에만 맞는 것은 `server/design/beat_grid_data/love_attack.yaml`과 `.moai/reports/t537/`의 캡처 고정값(`love_attack_beat_grid.json`·`stage_fixtures.json`)뿐이고, 로더·렌더 로직에는 그룹 번호·이름·장비 종류가 전혀 하드코딩돼 있지 않다(`TestLoaderIsRigAndSongAgnostic`으로 확인).

**캡처**: `.moai/reports/t537/`. `proposal_full.png`(시안 원본, 1640×1900)·`implemented_full.png`(같은 뷰포트, 전체화면 루트 `<BeatGrid>` — 곡 전체 지도에 「미정」 배지 6개(SCENE 메모) 전부 보임, M1 패널이 실제 progress.md 값(「1. … 통과(구조)」 등)을 보여줌, 모든 막대가 해칭(색 미정) 렌더 확인)·`implemented_selected.png`(1640×1200, BACK 18마디 선택 — 밝기 100%·위치 프리셋 미정·색 프리셋 미정·들어올 때 미정+전환 버튼·출처(§4 109행)·설명(원문) 여섯 줄이 각각 독립된 자리에 렌더됨을 확인)·`side_by_side.png`(둘을 나란히). 데이터는 전부 실측: `love_attack_beat_grid.json`은 `uv run python3 -c "from server.design.beat_grid import default_beat_grid, attach_beat_grid_runtime_extras, LOVE_ATTACK_TITLE; ..."` 실행 출력 그대로(probe_results 포함, 실제 progress.md 읽은 값), `stage_fixtures.json`은 t534가 쓴 것(t525 §② 실측)을 그대로 재사용. 재현: `ui/`에 `npm ci` → 임시 엔트리(`t537-capture.html`, `src/components/_t537_capture_entry.tsx`, `src/components/_t537_*.json`)를 이 절 설명대로 다시 만들고 `npx vite --port 5799`로 띄운 뒤 `.moai/reports/t532/run_chrome.sh` 재사용(`?select=BACK,18` 쿼리로 선택 캡처) — 캡처 뒤 임시 파일은 삭제했다(M2/M2후속 선례와 동일한 의도적 선택).

**차이 목록(시안 대비, 정직하게 남김)**:

- **값 구조화는 됐지만 편집은 아직 읽기 전용** — 구조화 필드를 각각 독립된 자리에 보여주지만(이번 카드의 핵심), 그 값을 바꾸는 편집 UI(드롭다운 선택 등)는 M3 범위다. 지금은 읽기 전용 표시만.
- **전체화면 전환 트리거 UI 모양** — 시안엔 전역 모드 전환 버튼이 없다(plan-audit D7, 큐 편집 칸 내부의 "전환" 토글과는 다른 것 — REQ-LDBEAT-004(d)). 이번 카드가 신설한 「박자 배치」 헤더 토글은 §5 열린 결정 6이 "M2(phase ②)가 director와 확정"하도록 열어 둔 자리를 처음 채운 것이고, 정확한 자리·모양(탭? 버튼? 다른 위치?)은 여전히 재확인 대상이다.
- **전체화면 프레임의 실제 높이 채움** — `.beat-grid-fullscreen-frame{flex:1}`로 배선했지만 `.beat-grid` 자체 레이아웃(내부 3단 `.beat-grid-body`)은 M2/M2후속 그대로라, 시안처럼 "한 화면 높이 꽉 채움 + 내부 스크롤"이 정확히 같은 느낌인지는 캡처 두 장(1640×1900 전체페이지)으로 간접 확인했을 뿐 실제 브라우저 창(뷰포트 고정)에서 보진 않았다.
- **예제 모드 불일치** — `App.tsx`의 전체화면 분기는 `state.songTimeline.timeline`만 읽고(예: 실제 타임라인 없음) `timelineExample`(`SONG_TIMELINE_EXAMPLE`) 폴백을 안 쓴다 — 기존 5블록 분기(`RunbookMode`)는 그 폴백을 쓰므로, 예제 모드에서 런북 본문은 예제가 보이는데 박자 격자 전체화면은 "데이터 없음"으로 떨어지는 불일치가 있다(기능 결함은 아니지만 UX 공백).
- **색 프리셋 실제 색 표(`colorPresetHex`)가 아직 없음** — `cueColorFill`은 받을 준비가 됐지만, 이 카드는 콘솔 접촉 0이라 실제 프리셋→hex 매핑의 살아있는 출처가 없다. 지금은 전부 중립(해칭)으로만 보인다 — M3+ 콘솔 프리셋 풀 읽기가 이 표를 채워야 실제 색이 보인다.
- M2 후속(t534)이 이미 남긴 차이(곡 전체 지도 에너지 곡선·자(ruler) 박 단위·2D 무대 입체감·프리셋 서랍·장면 전환 알약)는 이번 카드 범위 밖 그대로.

**안 잰 것(Gaps, 정직하게 남김)**:

- **TS 쪽 RED 분리 미흡** — 위 "RED 확인(TS)" 절 참조. 함수별 개별 RED 캡처를 하지 않았다.
- **MOVER-U/MOVER-D 선택 캡처 없음** — "효과 프리셋" 행이 `roleFieldHints`의 mover 조건에서만 보이는지는 BACK 선택 캡처로는 확인 못 했다(코드 리딩+단위시험으로만 확인, `formatPresetField`/역할 조건 분기 — 단위시험은 있으나 헤드리스 캡처로 눈으로는 안 봤다).
- **`attach_beat_grid_runtime_extras`의 레거시 칸 정규화가 실제 저장된 커스텀 격자 경로를 탄 적이 없음** — M3 편집 경로가 아직 없어 "레거시 칸이 실제로 저장돼 있다가 이 함수를 거쳐 보인다"는 시나리오는 단위시험(가짜 payload)으로만 확인했지, 실제 세션 저장소 왕복으로는 안 쟀다.
- **scene_memos 리드 추가 지시의 SPEC 편입 여부** — (5)에 적은 대로 REQ-006 밖의 새 데이터 요소라는 것만 표시했고, spec.md/acceptance.md는 건드리지 않았다 — 다음 라운드의 판단이 필요하다.
- **콘솔 접촉 0, 실기 확인 0** — M1 읽기 배선이 "진짜 progress.md를 읽는지"는 쟀지만(§검증 `TestLiveProbeReadThroughTheRealSessionWiring`), 그 값 자체가 콘솔 실측과 일치하는지는 M1(카드 t531, lane-3)의 몫이고 이 카드는 그 결과를 "읽는 경로"만 새로 만들었다.

#### t537 ② 레이아웃 교정 — 레인 리뷰 대응 (같은 카드 후속, 커밋 `edc537db` 위)

레인이 `side_by_side.png`를 직접 읽고 지적(2026-10-10): 테스트/tsc/금지경로/리그상수 검사는 전부 PASS했지만(재실행 결과 동일) **레이아웃이 시안과 다르다**(카드 요구 "시안 레이아웃 그대로"). 지적된 5개 격차를 데이터·검증 로직은 그대로 두고(M1 읽기·SCENE 메모·리그 일반화·금지 경로·`App.tsx` 범위 전부 불변) 레이아웃만 고쳤다.

1. **무대(2D)+이 마디 한눈에가 타임라인 오른쪽에 있던 것** → `.beat-grid-body`(3칸 가로 분할: 타임라인|상세|편집칸)를 둘로 쪼갰다. `.beat-grid-mid`(타임라인 + 큐 편집 칸, 시안 `.mid`+`.sidepane`과 같은 자리)와 `.beat-grid-insp`(무대 2D + 이 마디 한눈에, 그 아래 고정 높이 띠, 시안 `.insp`와 같은 자리)로 — 큐 편집 칸은 타임라인 바로 오른쪽, 무대·한눈에 표는 그 아래로 옮겼다.
2. **뷰포트의 위쪽 30%만 쓰고 나머지가 빈 것** → `.beat-grid`를 `min-height:0;overflow:hidden`으로, `.beat-grid-mid`를 `flex:1;min-height:0`으로 바꿔 `.beat-grid-fullscreen-frame{flex:1}`가 준 전체 높이를 실제로 채우게 했다(헤더/지도/툴바/하단띠/명령창/M1패널은 auto 높이, 타임라인 행만 남는 공간을 전부 먹는다). 내부 스크롤은 `.beat-grid-lanes{overflow:auto}` 그대로.
3. **곡 전체 지도가 7칸 숫자 띠였던 것** → 새 순수함수 `deriveSectionBlocks`(`BeatGrid.tsx`)가 `timeline.sections`(서버가 이미 보내는 값, `App.tsx`가 `sections` prop으로 새로 넘김)의 `label`+`start_ms`를 그 곡 BPM(`secondsPerBar`)으로 마디 위치 환산해 구간 블록 띠로 그린다(인트로/벌스1/프리코러스1/코러스1 — 아래 캡처로 확인). **에너지 곡선은 그 데이터 자체가 서버 페이로드 어디에도 없어 추가하지 않았다**(지어내지 않음 — 그대로 Gaps에 남김). **"전체 곡 중 지금 보는 범위 강조"도 못 했다** — 전체 곡 길이(마디 수) 데이터가 없어(`bar_count`/`total_duration_ms`가 session.py 어디서도 채워지지 않음, 재확인: `grep -n '"bar_count"' server/web/session.py` → 0건) 지도 자체가 표시 범위(0~25마디)다. 구간 데이터가 없으면(`secondsPerBar` 미확정 등) 기존 7칸 숫자 띠로 조용히 떨어진다(새 시험 `describe("deriveSectionBlocks …")` 7개로 확인, `BeatGrid.test.tsx`).
4. **편집 칸 빈 상태가 과도하게 길고 비어 있던 것** → 위 1·2의 결과로 자연히 해소 — `.beat-grid-cue-panel`을 `flex:0 0 310px`(시안 `.sidepane` 폭)로 고정하고 `.beat-grid-mid`의 둘째 칸으로 두니, 높이는 타임라인 행과 같아져(flex stretch) 더 이상 화면 전체 높이로 늘어나지 않는다.
5. **무대(2D)가 작은 점 무더기였던 것** → `.beat-grid-insp`가 고정 높이(280px) 띠를 주고 `.beat-grid-stage{flex:1}`로 그 안을 꽉 채우게 했다(이전엔 `height:160px` 고정값 + 좁은 칸). 좌표·소속은 그대로 `fixtures`/`fixtureDisplayColor`/`fixtureDisplayOpacity`(리그 상수 0, t525 실측 좌표만) — 크기만 키웠다.

**추가/고친 파일**: `ui/src/components/BeatGrid.tsx`(`deriveSectionBlocks`/`barPercentInRange`/`BeatGridSectionLite`/`BeatGridSectionBlock` 신설, `sections` prop 신설, `.beat-grid-body`→`.beat-grid-mid`+`.beat-grid-insp` 재배선, 곡 전체 지도 렌더 교체), `ui/src/components/BeatGrid.test.tsx`(`deriveSectionBlocks` 7개+`barPercentInRange` 3개 신설, 69→80개), `ui/src/App.tsx`(`sections={state.songTimeline.timeline?.sections}` 한 줄 추가, `runbookMode` 분기 안), `ui/src/styles.css`(`.beat-grid-mid`/`.beat-grid-insp`/`.beat-grid-overview-track`/`.beat-grid-overview-section`/`.beat-grid-overview-memos`/`.beat-grid-overview-memo-marker` 신설, `.beat-grid-body`/`.beat-grid-detail`/`.beat-grid-ov-cell` 제거).

**검증(재실행, verbatim)**:

```
$ uv run --quiet pytest server/tests/test_beat_grid_t532.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_probes_t537.py -q
...................................................
51 passed in 0.50s

$ uv run ruff check server/design/beat_grid.py server/design/beat_grid_probes.py server/web/session.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_probes_t537.py
All checks passed!

$ uv run ruff format --check <위와 같음>
5 files already formatted

$ cd ui && npx tsc --noEmit
(종료 코드 0, 출력 없음)

$ npx vitest run src/components/BeatGrid.test.tsx src/components/RunbookMode.test.tsx src/App.test.tsx
 ✓ src/components/BeatGrid.test.tsx (80 tests)
 ✓ src/components/RunbookMode.test.tsx (16 tests)
 ✓ src/App.test.tsx (30 tests)
 Test Files  3 passed (3) · Tests  126 passed (126)

$ git diff --stat edc537db -- ui/src/components/CueSheetTimeline.tsx 'CueSheetTimeline*' 'emit*' 'songcue*' 'cue_sheet_edit*' 'console/lua/**'
(출력 없음 — 금지 파일 0 diff)

$ git diff edc537db -- ui/src/App.tsx
 (한 줄 — `sections={state.songTimeline.timeline?.sections}`, `runbookMode && beatGridFullscreen` 분기 안)
```

**캡처 갱신**: `.moai/reports/t537/`의 `implemented_full.png`·`implemented_selected.png`·`side_by_side.png`를 같은 뷰포트(1640×1900/1640×1200)로 덮어썼다. 데이터도 갱신 — `love_attack_sections.json`(신설, 구간 4개: 인트로·벌스1·프리코러스1·코러스1, `_song_timeline_payload` 실제 출력, BPM 120·secondsPerBar=2.0 고정 테스트 픽스처 — 실제 LOVE ATTACK 다중 구간 타임스탬프 데이터는 이 저장소에 아직 없어 레이블만 배치 규칙서 §1/§2 표현을 그대로 썼다). 직접 읽은 결과: 곡 전체 지도에 구간 4개 블록 + 그 위 SCENE 메모 배지 6개 모두 올바른 위치에 겹쳐 보임, 타임라인 행이 전체화면 높이를 채우고 편집 칸이 같은 높이로 오른쪽에 붙음, 무대·한눈에 표가 그 아래 한 띠로 나란히, 선택 캡처에서 편집 칸이 과도하게 길지 않고 내용 높이에 맞게 보임.

**수정된 차이 목록 항목(위 "차이 목록" 절 갱신)**: "전체화면 프레임의 실제 높이 채움"·"무대(2D)가 작은 점 무더기" 두 항목은 이번 교정으로 해소됐다(위 2·5). "곡 전체 지도" 관련 차이는 다음으로 좁혀졌다 — 에너지 곡선·전체 곡 길이 강조 둘은 데이터 부재로 여전히 Gaps(아래). 나머지 항목(값 구조화=읽기전용, 전환 트리거 UI 모양, 예제 모드 불일치, 색 프리셋 실제 표 부재, M2후속이 남긴 차이)은 레이아웃과 무관해 그대로다.

**새로 추가된 안 잰 것(Gaps)**:

- **에너지 곡선 데이터 없음** — 서버 페이로드(`SongTimelineSection`/`SongTimelineView`)에 음량·에너지 수치 필드가 없다. 지어내지 않고 생략했다 — 추가하려면 별도 SPEC(오디오 분석 파이프라인)이 필요하다.
- **전체 곡 길이(마디 수) 데이터 없음** — `bar_count`/`total_duration_ms`는 타입엔 있지만(LX-SEQ 확장, 선택 필드) `session.py`가 채우는 자리가 없다(`grep` 0건, 위 §검증). 그래서 "전체 곡 중 지금 범위 강조"를 못 하고, 지도 자체가 표시 범위다.
- **구간 캡처 데이터는 실제 LOVE ATTACK 곡 구조가 아니라 테스트 픽스처** — `love_attack_sections.json`은 4개 구간(인트로/벌스1/프리코러스1/코러스1)뿐이고 BPM 120 고정값을 썼다. 실제 배치 규칙서의 BPM(스피드 마스터 15, 콘솔에서 직접 설정 — REQ-LDBEAT-014)과 전체 구간 구성(인트로/드럼/벌스/프리/코러스/브릿지/드롭/마지막 코러스 등, §3 전체 배치)을 담은 다중 구간 데이터는 이 저장소의 서버 쪽 어디에도 아직 없다 — 메커니즘은 실제 데이터로 증명됐지만(위 §검증), 시각적 완성도는 그 데이터가 채워져야 는다.
- **뷰포트 고정 높이 체감** — `.beat-grid-mid{flex:1}`이 전체화면 높이를 채운다는 것은 CSS flex 표준 동작 + 캡처(1640×1900 전체페이지, 뷰포트 아님)로 간접 확인했을 뿐, 실제 고정 창 크기(예: 1280×800) 브라우저에서 내부 스크롤이 정확히 어떻게 보이는지는 여전히 직접 안 봤다.

**SPEC 개정 후기(2026-10-10, 같은 카드, 코드 변경 0줄)** — 위 (5)(6)이 "REQ-006 밖"·"다음 라운드 판단 대상"으로 남겨 둔 `scene_memos`와 로더의 리그·곡 일반화를 spec.md REQ-LDBEAT-006(iv-1)~(iv-4)·(v-1)(v-2)과 acceptance.md AC-LDBEAT-016(i)(j)(k)(l)(m)·§A.1 매핑으로 정식 편입하는 SPEC 개정 커밋이 이 구현 위에 쌓였다 — 위 "새로 추가된 안 잰 것(Gaps)" 앞의 §Gaps 항목 "scene_memos 리드 추가 지시의 SPEC 편입 여부"는 이로써 해소.

**plan-audit iteration 3 FAIL(0.60) D1/D2/D4/D5 보강(같은 카드)** — D1: `BeatGrid.tsx`에 순수함수 `sceneMemoMarkers(memos, visibleBarRange)` 신설("이 마디 한눈에" 패널이 실제로 그리는 배지+§4 원문+`source_ref` derivation, DOM 없이 단언)해 `BeatGrid.test.tsx`에 LOVE ATTACK 여섯 메모+가짜 다른 곡 메모 단위시험 5개 추가(85개로 증가). D2: `TestOverlapIndependentOfCellStructuring`에 `inspect.signature`/`inspect.getsource` 기반 `scene_memos` 매개변수·참조 부재 단언 + LOVE ATTACK 실제 데이터로 메모·큐 공유 마디(겹침 자리)가 있어도 `validate_beat_grid_tracks`가 그대로 PASS하는 행동시험 2개 추가. D4: REQ-LDBEAT-006(iv-2) "세 조건" 규칙을 파라미터화한 순수함수 `classify_scene_cell_assignment`(`beat_grid.py`) 신설 + 조건별 독립 단위시험 4개와 LOVE ATTACK §4 SCENE 여섯 자리 재도출 대조시험 1개(`TestSceneCellAssignmentRule`, `test_beat_grid_t537.py` 21→28개). D5: `love_attack_data/love_attack.yaml` 주석의 "나머지 셋(11~13·18~21·22~25)"을 bar 14 포함 "나머지 넷(11~13·14~17·18~21·22~25)"으로 정정. 전수 재검증: `pytest` 58 passed·`ruff check`/`format --check` 2 files 통과·`tsc --noEmit` 0·`vitest`(BeatGrid/RunbookMode/App) 131 passed. D3(AC-016(m) 인용 테스트 파일 정정)는 acceptance.md 편집이 범위 밖이라 보류.

### 데이터 채우기 — FOH·WASH-ALL·STROBE 트랙 + 규칙 확장 (카드 t543, lane-3, 브랜치 `WT-ldbeat-data-fill`)

감독 결정 2026-10-10 「데이터 채우기 먼저」. 콘솔 읽기 전용(쓰기 0, 응답기 1.6.6). 증거 `.moai/reports/t543/verdict.md`.

- **콘솔 실측**: 프리셋 풀 14개·그룹 18개 목록(`r1_pools.json`), 그룹 18개 SELECTIONDATA 전량(1.6.6 props 나눠 읽기, `r2_group_members.jsonl`) → 패치 SUBFIXTUREINDEX 로 fid 대응(`r4_group_fids.txt`, 18개 모두 이름과 일치, unknown 0). t525 의 「그룹당 앞 2대」 한계는 1.6.6 에서 풀렸다.
- **데이터**: `love_attack.yaml` 에 FOH(G3, 111~118)·WASH-ALL(G10, 401~410·421~430) 트랙 추가(시안 ROLES 순서), STROBE `group_no` 15(611~614). 그룹 번호는 데이터 파일에만 — 코드 상수 0.
- **규칙 확장, 감독 결정 2026-10-10** — REQ-LDBEAT-006(iv-2) 「세 조건」의 조건 1·2를 넓혔다: 칸이 그룹 이름 대신 **층 역할**(예: 「워시」 → `wash`)을 부르면, 확인된 트랙 중 그 역할(공용 판정기 `resolve_layer_role`)을 가진 트랙이 **정확히 하나**일 때만 그 트랙 큐로 옮긴다. 둘 이상이거나 없으면 메모로 남는다. 그룹 이름 문자열 비교는 넓히지 않았다(`"WASH"` ≠ `"WASH-ALL"` 그대로). 구현: `classify_scene_cell_assignment(named_role=, confirmed_track_roles=)` 선택 인자(기존 호출 동작 불변). 결과: bar 7 「라벤더 워시 40%(2마디 번짐)」·bar 14 「워시 25% 덜어냄」 → WASH-ALL 큐, bar 7 「FOH 켬」 → FOH 큐(기존 세 조건), 메모 6 → 4(0·11·18·22). 이 확장은 spec.md REQ-LDBEAT-006(iv-2) 문면에 아직 반영되지 않았다 — 문면 개정은 manager-spec 몫.
- **검증**: `pytest server/tests -k "beat_grid or runbook or ldbeat or timeline"` → 206 passed, 2 skipped. 역할 경로를 끈 몽키패치에서 새 시험 2개 FAIL(`test_love_attack_section_4_scene_cells_classify_to_the_yaml_layout`, `test_role_match_requires_exactly_one_track_with_that_role`) — 시험이 확장을 실제로 잰다. `ruff check`·`format --check` 통과.
- **색 프리셋 값**: 4.1·4.2 필드 135개 읽기 — 색 값 칸 없음(`PRESETDATA ""`, `SELECTIONDATA {}`). `colorPresetHex` 막힘 유지(빗금).
- **안 잰 것**: 화면(`ui/`)에서 새 트랙이 어떻게 보이는지 브라우저로 안 봄. 전체 시험은 CI 에 맡김.

### 프리셋 번호 12칸 반영 — 감독 승인 2026-10-10 (카드 t543 후속)

- **출처**: `.moai/reports/t543/proposal-table.md`(AI 초안) 12칸을 감독이 「모두 승인」(2026-10-10, 리드 경유). 나머지 120칸은 미정(`null`) 그대로. 움직임 칸(팬 흔들기·틸트 웨이브)은 감독 결정 「앱 2단계 무빙으로」에 따라 카드 t548 몫 — 여기서 손대지 않음.
- **반영**: 디머 프리셋 2(FOH 7 → 1.1, BLIND 17 → 1.6, `brightness.mode = dimmer_preset`), 효과 8(21.1×4 BACK, 21.3×2 SIDE-ALL, 21.5×2 MOVER-U/D, `effect_kind = mixed` — 21번은 All 풀), 위치 2(MOVER-U/D 18 → 2.1). 로더 출력과 제안표 데이터를 기계 대조: 12/12 일치.
- **근거 표기 위치**: 칸마다 yaml 주석에 `[실측]`/`[실측·다른 그룹]`/`[이름]` + 「감독 승인 2026-10-10」 + 제안표 행 번호. `source_ref` 는 쓰지 않았다 — REQ-LDBEAT-006(i-5)가 `source_ref` 를 「§4 파일 경로+행 번호, 칸당 1개」로 묶고 있고, FOH 7·BACK 18 등은 이미 §4 % 출처를 거기 싣고 있어 덮어쓰면 그 출처가 사라진다.
- **REQ-LDBEAT-015(f) 예외, 감독 승인 2026-10-10**: (f)는 프리셋 번호를 「배치 규칙서 또는 t525류 실측 출처에 숫자로 적힌 값만」으로 묶는다. 이번 12칸 중 실측 근거는 4칸(그중 2칸은 Group 11 에서 잰 것을 Group 12 에 적용)이고, 8칸은 프리셋 **이름**만 맞춘 후보다. 감독이 제안표의 「이름은 증거가 아니다」 경고를 본 뒤 승인했다. spec.md (f) 문면 개정은 manager-spec 몫으로 남긴다.
- **검증**: `pytest server/tests -k "beat_grid or runbook or ldbeat or timeline"` → 207 passed, 2 skipped. 「승인된 12칸 외엔 번호 없음」·「밝기 단일모드」 시험 추가. `ruff check`·`format --check` 통과.
- **안 잰 것**: 이 번호들이 실제 콘솔에서 의도대로 보이는지(특히 [이름] 8칸과 Group 12 의 21.5·2.1)는 재지 않았다 — 데이터만 바꿨고 콘솔 쓰기 0.

### SPEC 개정 0.3.2 — 앱 2단계 무빙 칸·근거 필드·승인 예외 (카드 t548, lane-3, 브랜치 `WT-ldbeat-app-movers`, plan 만)

감독 결정 2026-10-10 「앱 2단계 무빙으로」. plan 문서만 — 코드 0줄, 콘솔 0건. 작성 manager-spec, 독립 감사 plan-auditor. 감독 승인 전엔 run 하지 않는다.

- **개정 네 가지**: (A) REQ-006 (vi-1)~(vi-7) `app_movement` 큐 필드 — 닫힌 모양 어휘·축·주기(박/마디, 초 금지)·위상 펼침·리그 상수 금지·같은 축 `effect_preset_no` 배타. (B) REQ-015 (g) 감독 승인 예외 — 제안표에서 감독이 명시 승인한 번호만, 승인 기록 필수. (C) REQ-006 (vii) 칸별 근거 필드 `evidence` = `grade`(실측/다른 그룹 실측/이름만/null) + `approval`({by, date, source}/null), `source_ref`(i-5)와 독립. (D) REQ-006 (iv-2) 문면을 t543 역할 매칭 구현에 맞춤. AC-LDBEAT-016 에 하위 (n)~(t). §5 열린 결정 8.
- **예산**: REQ 15/16, AC 16/16 — 새 ID 0개.
- **감사**: 1회차 FAIL 0.63 — D1 `grade` 한 필드에 증거 강도와 승인 경로가 섞여 AC(o)/(p)가 같은 8칸에 다른 값을 요구, D2 (vi-5)(vi-6)(vi-7)에 실패하는 AC 없음. 2회차 PASS 1.00(`grade`/`approval` 분리, AC (r)(s)(t) 추가). 보고서 `.moai/reports/t548/plan-audit.md`.
- **열린 결정(run 전에 감독이 정할 것)**: ① 팬만 흔드는 모양이 `position_fx` 에 없다(`wave` 는 Tilt 만) — 새 모양 vs `wave` 에 축 매개변수. ② 무빙 기준 위치 — `position_fx` 의 라벨 해석 뱅크 프리셋 vs 큐 자신의 `position_preset_no`. ③ MOVER-D(Group 12, Spiider)는 2단계 무빙을 한 번도 안 쟀다 — run 전 프로브 필요.

### M8 — 앱 2단계 무빙 칸 + 칸별 근거 등급 (카드 t548, 브랜치 `WT-ldbeat-movers-run`)

REQ-LDBEAT-006(vi)(vii)·(iv-2) 재교정, REQ-LDBEAT-015(g) 구현. 콘솔 접촉 0건, 콘솔 쓰기 0건. TDD(RED-GREEN), cycle_type=tdd. 전체 verdict는 `.moai/reports/t548/run-verdict.md`.

- **`BeatGridCue` 신설 필드** — `app_movement: {shape, axes, period_unit, period_value, phase_spread} | None`, `evidence: {grade, approval} | None`. `normalize_beat_grid_cue`가 레거시 칸에서 둘 다 `None`으로 채운다(`label` 파싱 0건, REQ-006(ii-2)와 같은 금지).
- **`position_fx.py` 일반화** — `wave`를 `axes` 파라미터(Pan/Tilt/둘 다)로 일반화한 `relative_wave_lines()` 신설. `position_fx_commands`의 기존 wave 경로(axes={Tilt}, phase_spread=True)는 일반화 이전 하드코딩 출력과 바이트 동일 — 기존 `test_wave_full_bundle` 그대로 PASS.
- **새 에미터 `server/design/app_movement.py`** — `app_movement_commands()`가 선택+기준 위치 리콜(그 칸 **자신의** `position_preset_no`, `position_fx`의 레이블 해석 뱅크 프리셋은 호출하지 않음, REQ-006(vi-8)) → 상대 두 단계 → 커브 → 위상(phase_spread가 참일 때만) → 속도 순서로 명령을 낸다. Speed는 BPM ÷ (주기 × 마디당 박, period_unit="bar"일 때만) 로 호출 시점에 계산 — 저장 시점 계산·초 단위 상수 0건(vi-4). BPM/beats_per_bar/period 중 하나라도 없으면 거절(reason 문자열). `dimmer_attribute_names()`/`brightness_value_commands()` — MA3 Dimmer 패밀리(정확 일치, `DimmerCurve` 제외) 전수에 한 줄씩.
- **검증 함수 3개(`beat_grid.py`)** — `check_app_movement_axis_conflict`(같은 축 배타성, REQ-006(vi-7)), `check_evidence_approval`(프리셋 번호 있는 칸은 완전한 `evidence.approval` 필요, REQ-015(f)/(g)), `pan_only_vertical_base_warning`(감독 결정④ — Pan 단독+기준 위치 없음 경고, `position_preset_no == None`에만 한정 — non-null 프리셋의 "수직인가" 판정은 범위 밖, §5 항목 8 미해소분).
- **데이터(`love_attack.yaml`)** — MOVER-U bar 11(`wave`+`axes=[Pan]`, 주기 미정 — 레이블이 말하지 않아 지어내지 않음)·bar 18(`axes=[Pan]`, `period_unit=beat`, `period_value=2`), MOVER-D bar 7(`axes=[Tilt]`, `period_unit=bar`, `period_value=2`, `phase_spread=true`)·bar 22(`axes=[Tilt]`, `period_unit=beat`, `period_value=2`) — MOVER-D 두 칸은 실기 라이브 프로브(`.moai/reports/t548/probe-moverd.md`, `reports/t548-moverd-probe-20261011.md`, 2026-10-11) PASS 확인 후 채움(Dimmer2까지 내야 빛남·2단계 틸트 웨이브/원 움직임·팬 단독은 기울인 자리에서만 보임, 세 사실 전부 구현에 반영). 12칸의 `evidence`를 yaml 주석에서 구조화 필드로 소급(측정 2·다른 그룹 실측 2·이름만 8, `.moai/reports/t543/proposal-table.md` 전수 재독, 전부 승인 `by=supervisor, date=2026-10-10`) — `source_ref` 바이트 동일 보존.
- **UI(`protocol.ts`/`BeatGrid.tsx`)** — `BeatGridAppMovement`/`BeatGridEvidence`/`BeatGridEvidenceApproval` 타입. `formatAppMovementField`/`formatEvidenceField`(shape+축+음악단위주기, grade+승인날짜) + `appMovementAxisConflictWarning`(⚠ 같은 축 충돌) + `panOnlyVerticalBaseWarning` 4개 순수 함수, `sceneMemoMarkers`와 같은 DOM-없는 단위시험 패턴.
- **검증**: `pytest server/tests/test_beat_grid_t532.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_probes_t537.py server/tests/test_beat_grid_t548.py server/tests/test_position_fx.py server/tests/test_position_fx_dedupe_t542.py server/tests/test_app_movement_t548.py` → 181 passed. `ruff check`/`format --check` 통과(7개 파일). `vitest run src/components/BeatGrid.test.tsx` → 101 passed. `tsc --noEmit` 클린.
- **안 잰 것**: MOVER-U bar 11의 주기(레이블이 말하지 않음, 미정으로 둠)·이 앱 에미터가 낸 명령의 실기 송신(MOVER-D 실기 프로브는 2026-10-11 리드 「실행」 뒤 콘솔에서 실행돼 Dimmer2 필요·틸트 웨이브·원·기울인 자리 팬 웨이브 움직임을 확인했다 — `reports/t548-moverd-probe-20261011.md`. 다만 그 프로브는 손으로 쓴 승인 목록이었고, 이 에미터 출력 자체는 콘솔에 보내지 않았다)·이 4칸이 실제 콘솔에서 시각적으로 의도대로 보이는지(라이브 프로브는 화소 변화율만 잼)·non-null `position_preset_no`의 "수직인가" 판정(§5 항목 8 미해소분, 범위를 넓히지 않음).

### M3 — 새 서버측 그리드 편집 연산 `apply_beat_grid_edit` (카드 t551, 브랜치 `WT-ldbeat-grid-edit`)

REQ-LDBEAT-007~009·015 구현. 콘솔 접촉 0건, 콘솔 쓰기 0건, OSC/응답기 호출 0건. TDD(RED-GREEN), cycle_type=tdd. M4(카드 t549, lane-2 동시 진행)와는 파일 경계로 분리 — `server/design/beat_grid.py`·`ui/src/protocol.ts` 변경 0줄(아래 「M4 lane-2 와의 경계」 참조).

- **신규 모듈 `server/design/beat_grid_edit.py`** — `cue_sheet_edit.py`와 같은 모양(순수 함수, 콘솔 무접촉). 편집 세 길(직접 고르기·문장·AI 제안의 「적용」) 전부가 수렴하는 단일 함수 `apply_beat_grid_edit(grid, *, bar, target, changes)` — 검증을 전부 끝낸 뒤에만 쓴다(부분 적용 0건). `@MX:ANCHOR`(기대 fan_in >= 3) 달았다.
  - **화이트리스트** `EDITABLE_CUE_FIELD_LABELS` — `brightness`/`position_preset_no`/`color_preset_no`/`effect_preset_no`/`effect_kind`/`entry`/`app_movement`/`evidence`(t548의 두 필드도 편집 대상, 카드 지시대로)/`new_preset_label`(콘솔 프리셋 생성용 메타데이터 — `BeatGridCue`에 영속되지 않음). 모르는 키는 "수정 가능한 항목" 안내와 함께 단일-원인 거절(`cue_sheet_edit.apply_cue_sheet_edit`와 같은 패턴).
  - **그룹/역할 스코프(REQ-LDBEAT-009)** `resolve_track_scope(tracks, target)` — 그룹 이름 정확 일치(대소문자 무시)를 먼저 보고, 없으면 트랙에 이미 계산된 `layer_role`(`resolve_layer_role` 재사용, 다시 계산하지 않음) 일치로 넓힌다. 매칭 0건이면 거절(이 곡의 알려진 트랙·역할 목록을 안내에 싣는다, 지어내지 않음). 실측: `"MOVER-U"` → 그 트랙 하나, `"mover"` → MOVER-U+MOVER-D 둘(LOVE ATTACK 실 데이터로 확인) — AC-LDBEAT-014(a)(b) 패턴.
  - **모양 어휘 + "⚠ 미확인" 플래그(REQ-LDBEAT-010)** — `app_movement.shape`는 `position_fx.POSITION_FX_EFFECTS`(import, 재선언 아님)와 같은 닫힌 집합. `UNVERIFIED_SHAPES = {"circle", "ballyhoo"}`(REQ-010 본문이 직접 이름 지목)는 거절이 아니라 report에 "⚠ 미확인" 경고 한 줄 — `wave`는 M8의 별도 라이브 프로브로 이미 확인됐으므로 플래그하지 않는다.
  - **속도·축 값 범위** — `axes`는 `{"Pan","Tilt"}` 안에서만, `period_unit`은 `{"beat","bar"}`만(초 단위 문자열 "seconds"는 거절, REQ-LDBEAT-006(vi-4)), `period_value`는 양의 정수만. 같은 축 배타성(REQ-006(vi-7))은 신규 모듈 함수를 만들지 않고 `beat_grid.check_app_movement_axis_conflict`를 **병합된 칸**(기존 칸 + 이번 changes) 기준으로 재사용.
  - **프리셋 풀 번호대(REQ-LDBEAT-015(a)(b)) — config/data 소스, 코드 상수 아님** — 새 데이터 파일 `server/design/beat_grid_data/preset_pools.yaml`(`confirmed: false`, 로드맵 예시 번호대를 PROVISIONAL 값으로 — 실제 쇼 파일과 대조한 적 없음을 `confirmed` 플래그와 주석에 명시). `load_preset_pool_policy()`가 읽고, `validate_preset_pool_assignment(kind, number, policy)`가 검사한다 — **base 풀**(`position_preset_no`/`color_preset_no`, 쇼에 원래 있는 프리셋 참조)은 번호대 검사 대상이 **아니다**(REQ-015(b) — base/effect 분리); **effect 풀**(`effect_preset_no`+`effect_kind`, `brightness.mode=="dimmer_effect"`의 `preset_no`)만 검사한다. 번호대 밖 → 거절(REQ-LDBEAT-015 인용 사유). 모듈 소스에 `"2.61"`/`"4.41"` 같은 리터럴 0건(시험으로 확인, `inspect.getsource` grep).
  - **근거 승인 재사용(REQ-LDBEAT-015(f)(g))** — 새 검증을 만들지 않고 M8의 `check_evidence_approval`을 병합된 칸에 그대로 재사용: 신규 effect 풀 프리셋 번호를 쓰려면 `evidence.approval`(by=supervisor+date+source)이 채워져야 한다. 안 채우면 거절, 채우면(예: 레인 제안표 경로 인용) 수락.
  - **밝기 단일모드(REQ-LDBEAT-015(c))** — `value_percent`/`preset_no` 중 둘 이상 동시 지정 거절, `value_percent` 범위 0~100.
  - **ASCII 신규 프리셋 이름(REQ-LDBEAT-015(d))** — `new_preset_label`에 비-ASCII(한글 등) 문자가 있으면 거절(`_ascii_label` 재확인 — 다만 그 함수는 콘솔 **송신 직전** 치환용이고, 이 자리는 송신 **전** 검증 단계라 치환이 아니라 거절로 다르게 처리했다 — 감독이 의도한 이름이 조용히 바뀌지 않게). ASCII면 report에 실리고 `BeatGridCue`에는 저장되지 않는다(실제 콘솔 프리셋 생성·명명은 M4의 몫).
  - **M1 의존 기능 비활성 — 재확인**: 현재 M1 9항목 중 ⑤(움직임 없음)는 M8의 별도 라이브 프로브로 이미 해소됐고(progress.md M8 절), ⑦⑧(같은 그룹 두 시퀀스 분담)은 M1 자체가 PASS다 — 이 M3 시점에 전면 비활성화할 M1-FAIL 의존 기능은 없다. ⑨(circle·발리후)만 REQ-LDBEAT-010의 "선택 허용+플래그" 경로로 처리(비활성화가 아니라 경고).
- **M4 lane-2 와의 경계**: `server/design/beat_grid.py`·`ui/src/protocol.ts` **diff 0줄**(`git diff --stat HEAD -- server/design/beat_grid.py ui/src/protocol.ts` 출력 없음, 확인됨) — M3는 beat_grid.py가 이미 가진 공개 함수(`normalize_beat_grid_cue`/`check_app_movement_axis_conflict`/`check_evidence_approval`)만 import해서 쓰고, 새 타입·새 필드를 그 모듈에 추가하지 않았다. 신규 데이터 파일(`preset_pools.yaml`)·신규 모듈(`beat_grid_edit.py`)·신규 시험(`test_beat_grid_edit_t551.py`) 셋 다 M4가 만지는 파일과 겹치지 않는다.
- **범위 결정 — session.py 명령창 와이어링은 이 카드에서 하지 않았다(잔여 위험으로 아래 기록)**: 카드가 "UI는 서버 페이로드를 직접 만들지 않는다"고 요구한 것은 이 함수의 **존재**(REQ-LDBEAT-007/008)이지, 기존 채팅 명령 라우팅(`server/web/session.py`, 11,791행, `_cue_sheet_draft_edit` 등 20개 이상의 우선순위가 정교하게 조정된 디스패치 체인)에 문장-파싱 경로를 새로 엮는 것은 별도 규모의 작업이다(그 체인의 각 라우트는 서로소성 분석이 딸려 있다 — `cue_sheet_edit.py`의 2백 줄 넘는 정규식 파서가 그 복잡도를 보여준다). 이 카드의 범위(§D — "console-group tracks, shape vocabulary..." 화이트리스트 선언)와 하드 규칙(파일 경계 최소화, 전체 스위트 대신 레인 로컬 검증)을 지키려 session.py는 건드리지 않기로 결정했다 — 다음 카드(문장 파서 또는 UI 다이렉트-픽 와이어링)가 이 함수를 호출하는 쪽에서 이어받는다.
- **검증**: RED(모듈 부재) → `uv run --quiet pytest server/tests/test_beat_grid_edit_t551.py -q` → `ModuleNotFoundError: No module named 'server.design.beat_grid_edit'`. GREEN → 같은 명령 → `35 passed in 0.29s`. 회귀 확인(관련 스위트만, 레인 로컬) → `uv run --quiet pytest server/tests/test_beat_grid_t532.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_probes_t537.py server/tests/test_beat_grid_t548.py server/tests/test_beat_grid_edit_t551.py server/tests/test_cue_sheet_edit.py server/tests/test_position_fx.py -q` → `252 passed in 0.99s`. `ruff check server/design/beat_grid_edit.py server/tests/test_beat_grid_edit_t551.py` → `All checks passed!`. `ruff format --check` 같은 파일 → `2 files already formatted`. UI 자체-점검 `grep -rn "changes\s*=\s*{" ui/src` → 출력 0건(§D 제약 자체 점검, 변경 없음이라 기존 상태 그대로).
- **AC PASS/FAIL 매트릭스(이 카드가 손댄 범위만 — AC-LDBEAT-012/013/014/016 전부는 M4/완료된 M1/M8 범위와 겹쳐 있어 이 카드가 새로 구현한 부분만 표기)**:

| AC | 상태 | 근거 |
|---|---|---|
| AC-LDBEAT-010(새 연산의 화이트리스트·단일-원인 거절·부분 적용 0건) | PASS | `test_beat_grid_edit_t551.py::TestNoPartialApply` 3개 + `TestGroupScopedEdit::test_unknown_target_rejected_naming_known_tracks` |
| AC-LDBEAT-014(a)(역할 스코프 화이트리스트 밖 거절) | PASS | `TestGroupScopedEdit::test_unknown_target_rejected_naming_known_tracks` |
| AC-LDBEAT-014(b)(매핑된 그룹에만 diff, 비매핑 diff 0) | PASS | `TestGroupScopedEdit::test_role_scope_edits_every_mapped_track_and_nothing_else`·`test_exact_group_name_edits_only_that_track` |
| AC-LDBEAT-016(a)(풀 번호대 밖 거절) | PASS | `TestPresetPoolPolicy::test_number_outside_declared_band_is_rejected`·`test_effect_preset_outside_pool_band_rejected_via_apply` |
| AC-LDBEAT-016(b)(밝기 복수 지정 거절) | PASS | `TestBrightnessSingleMode::test_two_brightness_modes_at_once_rejected` |
| AC-LDBEAT-016(c)(신규 프리셋 이름 ASCII) | PASS | `TestAsciiPresetLabel` 2개 |
| AC-LDBEAT-016(d)(쇼 원본 프리셋 덮어쓰기 금지 — 근거 승인 경로로 재구현) | PASS(경로 재구성) | `TestEvidenceApprovalReuse` 2개 — base 풀은 검사 대상이 아니므로(REQ-015(b)) `check_evidence_approval` 로 구현했다; `TestPresetPoolPolicy::test_base_pool_fields_are_not_band_checked`가 그 경계를 확인 |
| REQ-LDBEAT-010(미확인 모양 선택 허용+플래그) | PASS | `TestShapeVocabularyAndUnverifiedFlag` 6개 |
| REQ-LDBEAT-009(그룹→역할 매핑 재사용) | PASS | `TestTrackScopeResolution` 3개 |

- **안 잰 것(Gaps)**: (1) 프리셋 풀 번호대 수치 자체는 실제 쇼 파일과 대조한 적 없다(콘솔 접촉 0건인 이 카드 범위에서 불가능) — `preset_pools.yaml`의 `confirmed: false`가 그 상태를 정직하게 기록하고, 번호대를 바꿀 때 이 파일만 고치면 되게 설계했다(코드 변경 불필요). (2) 문장(②) 경로의 실제 자연어 파서(`cue_sheet_edit.parse_cue_sheet_edit_request`에 대응하는 박자 격자용 파서)는 짜지 않았다 — `apply_beat_grid_edit`가 구조화된 `changes` 딕셔너리를 받는 지점까지만 이 카드의 범위다. (3) `session.py`의 채팅 명령 디스패치 체인에 이 함수를 엮는 UI 와이어링은 하지 않았다(위 「범위 결정」 참조) — 지금은 직접 호출(단위시험)로만 도달 가능하다, 실제 UI 버튼/명령창에서 아직 도달 불가능. (4) AI 제안 경로(③)의 "제안 카드 → 「적용」 클릭 전 변경 0" 상태 전이(초안 레벨 상태 관리)는 구현하지 않았다 — `apply_beat_grid_edit` 자체가 "적용" 호출 시점의 최종 쓰기만 다루고, 그 이전의 제안-보류 상태는 UI/세션 레벨의 몫이다. (5) `new_preset_label`이 ASCII를 통과해도 실제로 콘솔에 그 이름의 프리셋이 생기는지는 M4의 몫이라 여기서는 report 문자열로만 확인했다.
- **잔여 위험**: (1) `preset_pools.yaml`의 PROVISIONAL 번호대가 실제 쇼 파일의 기존 프리셋과 충돌할 가능성이 있다 — `confirmed: false`인 동안은 `check_evidence_approval`의 명시적 승인 게이트가 추가 방어선이지만, 번호대 자체의 정확성은 director의 실제 쇼 파일 조회가 선행돼야 한다(§B 위험 11 미해소). (2) session.py 와이어링이 없는 채로 이 함수가 머지되면, 다음 카드가 도달 경로를 만들기 전까지는 "구현됐지만 아무도 호출하지 않는" 상태다(fan_in 0) — `@MX:ANCHOR`에 적은 "기대 fan_in >= 3"은 그 다음 카드가 와이어링을 마쳐야 실제 참이 된다. (3) "역할" 스코프 해석이 `layer_role`(공용 판정기 결과) 하나에만 의존한다 — 이 곡 데이터에서는 MOVER-U/MOVER-D 둘뿐이라 검증됐지만, 더 많은 트랙이 같은 역할을 공유하는 다른 곡·리그에서의 동작은 구조적으로는 일반화돼 있으나(코드 상수 0건, 로더 함수 재사용) 실 데이터로 교차검증하지는 않았다.

### M3 후속 — 도달 경로 배선(서버 전용 채널 + UI 세 길) (카드 t551 계속, 리드 지시 2026-10-11 "fan_in 0 해소" + 감독 지시 2026-10-11 "UI는 mockup 그대로")

위 M3 절은 `apply_beat_grid_edit` 자체만 구현했고 아무도 부르지 않았다(fan_in 0). 이 절은 그 도달 경로를 배선한다 — **서버는 채팅 디스패치 체인과 분리된 전용 WS 메시지 채널**, **UI는 mockup(`reports/ldbeat-runbook-ui-proposal-20261008.html`/`.md`, `reports/ldbeat-runbook-mockup-20261008.html`/`.md`, 2026-10-08)의 기존 스캐폴드**(이미 그 모양대로 있던 비활성 버튼·플레이스홀더를 켜는 것)만 건드렸다. TDD(RED-GREEN), cycle_type=tdd.

**UI 파일 변경 전 확인(지시 (4))**: 이 후속 작업 시작 시점까지 `ui/` 어떤 파일도 바뀌지 않았다 — `git diff --stat HEAD -- ui/` 출력 0줄로 확인(최초 M3 커밋 이후 그대로). 이번 절에서 처음으로 UI 를 건드렸다.

- **서버 전용 채널(채팅 디스패치 체인과 분리)** — `server/web/messages.py`에 신규 메시지 타입 3개(`beat_grid_edit`/`beat_grid_suggest`/`beat_grid_suggestion_apply`) + 이벤트 빌더 2개(`beat_grid_suggestion_event`/`beat_grid_suggestion_consumed_event`, `approval_resolved`와 같은 짝). `server/web/app.py`에 전용 `elif` 분기 3개 — `session.run_instruction`(채팅 체인)을 **거치지 않는다**(검증: `run_instruction` 함수 본문 소스에 세 메서드 이름 0건, 아래 참조). `server/web/session.py`에 `ChatSession.beat_grid_edit`/`beat_grid_suggest`/`beat_grid_suggestion_apply` 3개 메서드 — `_cue_sheet_draft_edit`와 같은 거절 관행(사유 문자열을 `chat_response_event.text`에 그대로 싣고, 거절 시 `store.latest` 바이트 동일 보존).
- **AI 제안 보류 메커니즘(신규 `server/design/beat_grid_suggestion.py`)** — `PendingSuggestionStore`(생성~「적용」 사이 보류, 격자·콘솔 diff 0) + `SuggestionSource` Protocol(교체 가능) + `NullSuggestionSource`(이 카드는 실제 AI 백엔드가 없다 — 지어낸 제안 0건, 정직하게 "제안 없음"). `ChatSession`에 `beat_grid_suggestion_source` 생성자 인자 추가(기본값 `NullSuggestionSource()`).
- **문장 파서 fidelity 교정(`server/design/beat_grid_sentence.py`)** — 1차 구현("포지션"/단일 마디/raw 번호)이 mockup 명령창(`#cmdIn`/`#bRule` 정규식, 플레이스홀더 "22~25마디 MOVER-D 효과를 Sweep 2박으로")과 다르다는 것을 이번 절에서 발견(coordinator 지시로 mockup HTML 을 처음 전수 재독). 교정: (a) 필드 레이블 "포지션"→"위치"(mockup 어휘 그대로), (b) **마디 범위**("(마디)~(마디)마디") 지원 — 신규 `apply_beat_grid_edit_range(grid, bar_start, bar_end, target, changes)`가 범위 안의 **이미 있는 칸에만** 적용하고(mockup `bRule` 핸들러의 `segs.filter(...)`와 같은 선택 — 새 칸을 지어내지 않음) 하나라도 없으면 그 경계를 사유에 실어 거절, 부분 적용 0건(범위 전체가 한 단위). (c) "효과" 항목과 프리셋 **이름** 값 해석은 **구현하지 않았다** — 아래 Missing Inputs 참조.
- **UI(`ui/src/components/BeatGrid.tsx`)** — mockup이 이미 그 모양대로 스캐폴드해 둔 두 자리를 켰다:
  - 명령창(mockup "구조" 5 + "조작 방법" 절, `#cmdIn`/`#bRule`/`#bAi`) — 플레이스홀더·버튼 라벨 **변경 0**(이미 mockup 그대로였다, 소스 자체 주석 "M3에서 배선"이 이 카드를 가리키고 있었다). "바로 적용(문장)" → `onSentenceEditRequest`, "AI 제안" → `onSuggestionRequest`(칸을 먼저 골라야 활성 — mockup은 이 제약이 없지만 이 카드의 비-NLU 구현은 bar·target 컨텍스트가 필요해 추가한 것, 안내 텍스트로 고지).
  - 밝기 "값"(%) 인라인 편집(mockup "구조" 4 + "막대 → 오른쪽 큐 편집" 절 "밝기 값/디머 프리셋/디머 효과" 중 "값"만, 카탈로그 불필요) — 새 순수 함수 `isBrightnessValueEditable`/`buildBrightnessValueChanges`(DOM 없는 단위시험 패턴, 이 프로젝트 관행) + `onEditRequest` 콜백.
  - 위치·색·효과 목록 선택, AI 제안의 점선 막대 렌더, 프리셋 서랍은 **건드리지 않았다** — 아래 Missing Inputs.
- **`ui/src/protocol.ts`/`useCopilotSocket.ts`/`App.tsx`** — 빌더 3개(`buildBeatGridEdit`/`buildBeatGridEditSentence`/`buildBeatGridSuggest`) + 전송 함수 3개(`sendBeatGridEdit`/`sendBeatGridEditSentence`/`sendBeatGridSuggest`, `sendTimelineDraftUndo`와 같은 패턴) + `App.tsx`의 `<BeatGrid>` 호출에 세 콜백 연결. **신규 서버 이벤트(`beat_grid_suggestion`/`beat_grid_suggestion_consumed`)는 `ServerEvent` 유니온·리듀서에 아직 추가하지 않았다** — `NullSuggestionSource` 기본값에서는 그 이벤트가 구조적으로 발생하지 않아(항상 "제안 없음" `chat_response`로 끝남) 지금 추가하면 한 번도 안 타는 코드가 된다, 실제 제안 소스가 연결될 때 함께 추가하기로 미뤘다(아래 Missing Inputs).
- **검증 — 세 그렙(coordinator 지시 AC-LDBEAT-005)**:
  1. `grep -rn "changes\s*=\s*{" ui/src` → 매칭 0건(exit 1) — UI 는 서버 페이로드를 직접 구성하지 않는다.
  2. `grep -rn "parse_cue_sheet_edit_request|apply_cue_sheet_edit" ui/src/components/BeatGrid.tsx ui/src/App.tsx ui/src/useCopilotSocket.ts ui/src/protocol.ts` → 매칭 0건(exit 1) — 큐 레벨 파서가 격자 경로에 섞여 들어가지 않았다.
  3. `run_instruction` 함수 본문 소스에 `beat_grid_edit`/`beat_grid_suggest`/`beat_grid_suggestion_apply` 세 이름이 0건(파이썬으로 함수 본문만 잘라 확인) — 채팅 디스패치 체인과 분리됐다(위 "서버 전용 채널" 참조, coordinator 지시 1항 "do NOT thread it into the existing chat-command dispatch chain").
- **RED→GREEN(신규 시험)**: `uv run --quiet pytest server/tests/test_beat_grid_edit_t551.py::TestApplyRange -q` → RED `ImportError: cannot import name 'apply_beat_grid_edit_range'` → GREEN `5 passed, 35 deselected`. `server/tests/test_session_beat_grid_edit_t551.py -q` → `14 passed`(원래 11 + 신규 3: consumed 이벤트 1개·범위 문장 2개). `server/tests/test_beat_grid_sentence_t551.py -q` → `13 passed`(범위·deviation 음성 사례 포함). 서버 회귀(레인 로컬) `test_web_*.py server/tests/test_session*.py server/tests/test_beat_grid*.py server/tests/test_messages_beat_grid_t551.py server/tests/test_cue_sheet_edit.py` → `1716 passed`. `ruff check server/` → `All checks passed!`.
- **UI 검증(레인 로컬, 손댄 파일만)**: `npx tsc --noEmit` → 깨끗(출력 0줄). `npx vitest run`(전체 — 이 프로젝트는 파일 단위 실행도 전체와 같은 속도라 전체를 돌렸다) → `852 passed`(원래 842 + 신규 10: `BeatGrid.test.tsx`에 `isBrightnessValueEditable`/`buildBrightnessValueChanges` 유닛 9개 + `protocol.test.ts`에 빌더 3개를 검증하는 시험 1개). `BeatGrid.test.tsx` 단독 → `110 passed`(원래 101 + 9).
- **AC-LDBEAT-005 PASS 근거**: 세 편집 경로(직접 고르기=`beat_grid_edit`+`changes`, 문장=`beat_grid_edit`+`sentence`, AI 제안=`beat_grid_suggest`→`beat_grid_suggestion_apply`)가 전부 `apply_beat_grid_edit`/`apply_beat_grid_edit_range`를 거친다(`session.py` 세 메서드가 전부 그 두 함수만 호출 — 코드 읽기로 확인, 호출 스택 로그 도구는 없음). UI 소스에 서버 페이로드 직접 구성 0건(그렙 1). `parse_cue_sheet_edit_request`/`apply_cue_sheet_edit` 0건(그렙 2). AI 제안 생성~적용 사이 상태 diff 0건은 `test_suggestion_creation_does_not_mutate_grid_state`가 직접 잰다.
- **AC-LDBEAT-010 PASS 근거**: `test_rejection_reason_reaches_the_event_text_verbatim`(session 시험)가 `BeatGridEditError`의 메시지 문자열이 `chat_response_event.text`에 **그대로**(`in` 포함 단언) 실리는 것과, 거절 시 `store.latest`가 바이트 동일 보존되는 것을 함께 잰다. UI 쪽 "그대로 노출"은 기존 제네릭 리듀서(`case "chat_response"`/`case "error"`)가 `event.text`/`event.message`를 가감 없이 `entries`에 넣는 경로를 그대로 탄다(신규 리듀서 분기 0개 필요).

**## Missing Inputs (coordinator 지시 3항 — 개선하지 않고 정지, director 결정 대기)**

이 항목들은 공통으로 **프리셋 카탈로그(이름↔번호, 풀 소속, 쇼 기존 프리셋 목록, 어디서 쓰이는지)를 읽는 경로가 이 앱 어디에도 없다**는 하나의 근본 원인으로 막혀 있다 — 지어내면 REQ-LDBEAT-015(f)류 금지(출처 없는 값)를 어기므로, 개선하지 않고 여기 정지해 둔다.

| 항목 | mockup 근거 | 막힌 이유 | 필요한 입력 |
|---|---|---|---|
| 모든 편집 경로의 **콘솔 반영**("⇪ 콘솔에 반영", 승인 1회) | "구조" 1, 결정 필요 표 | M4(카드 t549, lane-2 진행 중)의 범위 — 이 카드는 콘솔 접촉 0건 | (M4가 담당, 이 카드의 Missing Input 아님 — 참고용 명시) |
| 직접 고르기 패널의 위치·색·효과·디머 프리셋 **드롭다운**(mockup "이 곡 + 쇼 기존 + 새 프리셋") | "구조" 4 + "막대 → 오른쪽 큐 편집" | 아래 M3 후속 2차 절에서 카탈로그 경로를 복구했지만, 이번 라운드(지시 1~3항)는 드로워·배지·AI 점선 막대에 집중했다 — 이 드롭다운은 아직 안 만들었다(밝기 "값"만 인라인 편집 가능, 위치/색/효과는 여전히 명령창 문장으로만 쓴다). 드로워 데이터(`drawerSections`)가 이미 있으니 다음 카드가 그대로 재사용할 수 있다 | (카탈로그는 이미 있음 — UI 작업만 남음) |

### M3 후속 2차 — 근본 원인 정정: 프리셋 카탈로그 읽기 경로 복구 (카드 t551 계속, 리드 지시 2026-10-11 "이미 있는 길을 써라")

**근본 원인 정정**: 위 "## Missing Inputs" 표가 (이전 판에서) "프리셋 카탈로그를 읽는 경로가 이 앱에 없다"고 적은 네 항목은 **틀렸다** — `server/design/console_slots.py`(`paged_pool_children:32`·`resolve_named_pool_no:104`, 카드 t480)와 `server/design/preset_names.py`(`match_preset_name_across_pools`, `NAME_ABSENT`/`NAME_AMBIGUOUS`/`POOL_UNREAD`, 카드 t477)가 이미 그 경로였고, `server/web/session.py`의 `_resolve_draft_preset_names:8726`이 이미 그 경로로 초안을 채우고 있었다. 콘솔 **쓰기** 0 규칙은 **읽기**를 막지 않는다 — 이 틀린 결론이 왜 나왔는지는 재확인하지 않았다(카드 종료 전 재발 방지용으로만 기록).

- **신규 `server/design/beat_grid_presets.py`** — 새 판독 규율 0개, 기존 두 모듈을 그대로 재사용. `resolve_preset_name`(위치/색/밝기, 항목별 풀 하나)·`resolve_effect_preset_name`(효과, 네 풀 `Position`/`Color`/`Dimmer`/`All 1` 전부 검색 + 매칭된 풀 이름 반환 → `effect_kind` 역추적)·`build_preset_drawer`(mockup 서랍과 같은 세 섹션, 사용처는 `grid` 전수 스캔). 콘솔 접촉 0건 — 전부 가짜 `query`로 시험(`test_preset_label_lookup_t232.py`의 `_FakeRegistry` 관행과 같다).
- **`beat_grid_sentence.py` 교정** — 값이 "N.NN" 번호 꼴이 아니면 이름으로 보고 `name_lookup({"field","name"})`을 돌려준다(`changes`와 상호배타). "효과" 항목 추가(항상 `name_lookup`).
- **`session.py` `beat_grid_edit` 확장** — `name_lookup`을 받으면 `_resolve_beat_grid_name_lookup`이 콘솔 카탈로그로 번호를 해석한 뒤(읽기만) 기존 `apply_beat_grid_edit`로 넘긴다. 못 찾으면(이름 부재/모호/`POOL_UNREAD`) 번호를 지어내지 않고 단일-원인 거절 — `POOL_UNREAD`는 "번호대를 확인할 수 없습니다"로 이름 부재와 또렷이 구별한다(지시 2항의 "번호대를 사실로 내보이지 않는다"와 같은 원칙을 거절 사유에도 적용).
- **프리셋 서랍 백엔드** — `ChatSession.beat_grid_preset_drawer`, `beat_grid_drawer_request`/`beat_grid_drawer` 메시지 쌍. `preset_pools.yaml`의 `confirmed` 값을 모든 섹션에 실어 UI가 "번호대 미확인"을 보여줄 수 있게 한다.
- **AI 제안 거절** — `beat_grid_suggestion_reject`(mockup `aNo` 핸들러), 적용과 짝이지만 편집을 부르지 않는다(`beat_grid_suggestion_apply`와 같은 `beat_grid_suggestion_consumed_event` 짝 전송).
- **검증**: RED(`ModuleNotFoundError: beat_grid_presets`) → GREEN. 세션 레벨은 `FakeConsole.state_tree`로 **실제 세션 코드 경로**(`registry → query_state 도구 → gate.state_port → console`)를 그대로 태워 검증했다 — 별도 대역이 아니다. 회귀(레인 로컬) `test_web_*.py`+`test_session*.py`+`test_beat_grid*.py`+`test_cue_sheet_edit.py`+`test_preset_label_lookup_t232.py` → `1768 passed`. `ruff check server/` → All checks passed.

### M3 후속 3차 — 프리셋 서랍 UI·번호대 미확인 배지·AI 제안 점선 막대 (카드 t551 계속, 리드 지시 1~3항)

UI 변경 전 확인(지시 4항, 2차 라운드 시작 시점): `ui/` 어떤 파일도 바뀌지 않은 상태였다(`git diff --stat HEAD -- ui/` 0줄).

- **프리셋 서랍(지시 1항)** — mockup `drawDrawer()`를 그대로: 안내 문구 "누르면 쓰는 막대가 노랗게 · 콘솔 이름(영문) 표시" 그대로, 세 섹션 제목("디머 풀 1 — 밝기·밝기 효과"/"위치 풀 2 — 위치·움직임(상대값)"/"색 풀 4") 그대로. 사용처는 데모 `P` 객체가 아니라 `beat_grid_preset_drawer`의 실제 콘솔 판독에서 온다. 클릭하면 하이라이트(`.pr.on`, `highlightedPresetNo` 상태) + 그 프리셋을 쓰는 타임라인 막대에 `is-preset-highlighted`(새 순수 함수 `cueReferencesPreset`). 사용 큐 수는 행에 보이고(mockup과 같음) + `title` 호버로 "쓰는 곳: 큐 N개 — ..." 도 보인다(지시 1항의 "chip tooltip" 요구 — mockup 자체는 행 안에 바로 적지만, 이 구현은 행 텍스트 + hover title 둘 다로 중복 안내한다).
- **"번호대 미확인" 배지(지시 2항)** — 새 순수 함수 `presetPoolBandBadge`. **mockup 자신에는 "번호대 자체가 미확인"이라는 상태 표시 자리가 없다** — 그 데모는 번호대가 이미 확정돼 있다는 전제로 만들어졌다(재확인: mockup HTML 전수 재독, `confirmed` 류 플래그나 번호대 경고 문구 0건). 그래서 이 카드는 가장 가까운 기존 관례 — "⚠ 실기 미확인"(모양 선택지 배지, `isUnconfirmedShapeCue`와 같은 글자와 `.u` CSS 클래스)의 폭을 넓혀 섹션 제목 옆에 달았다. 둘은 "지어낸 상태를 사실로 내보이지 않는다"는 같은 원칙(REQ-LDBEAT-010/015(f))을 공유하므로 같은 시각 언어가 맞다고 판단했다 — `preset_pools.yaml`의 `confirmed: false`(§B 위험 11 미해소)인 동안 모든 섹션에 뜬다.
- **AI 제안 점선 막대 + 수락/거절(지시 1항)** — mockup "AI 제안은 타임라인에 점선 막대로 미리 보임"(구조 5) + `#bAi`→`aOk`/`aNo`. 렌더 경로는 **시험용 가짜 제안 소스**로 검증했다(`BeatGrid.test.tsx`에 리터럴 `BeatGridPendingSuggestion` prop을 직접 넘긴다) — 서버의 `NullSuggestionSource`는 그대로 생산 기본값이다(지시 원문 "NullSuggestionSource stays the production default"). 「적용」·「거절」 전까지 격자·콘솔 diff 0(결정④) — 서버 쪽은 `beat_grid_suggestion_reject`(2차 라운드에서 추가)가 거절 경로를 보장하고, UI 쪽은 새 순수 함수 `isPendingSuggestionForTrack`가 어느 트랙 줄에 점선 막대가 뜰지를 가린다.
- **protocol.ts/useCopilotSocket.ts** — `ServerEvent` 3종(`beat_grid_drawer`/`beat_grid_suggestion`/`beat_grid_suggestion_consumed`, 순수 추가 — 이전 라운드에서 "실제 소스가 생기면 함께 추가"로 미뤘던 바로 그 작업, 이번에 했다) + 빌더 3개(`buildBeatGridSuggestionApply`/`buildBeatGridSuggestionReject`/`buildBeatGridDrawerRequest`) + `UiState` 필드 2개(`beatGridDrawer`/`pendingBeatGridSuggestion`) + 리듀서 케이스 3개(기존 케이스 0줄 변경).
- **styles.css** — `.drawer`/`.pr`/`.beat-grid-cue-ghost`/`.beat-grid-ai-suggestion` 등 최소 스타일(순수 추가, mockup의 CSS 클래스 이름을 그대로 재사용해 의도를 맞췄다).
- **검증**: `npx tsc --noEmit` 깨끗. `npx vite build --mode=development` 성공(CSS·JS 문법 확인, dist/ 는 gitignore). `npx vitest run` → `864 passed`(원래 852 + 신규 12: `cueReferencesPreset` 7개·`presetPoolBandBadge` 2개·`isPendingSuggestionForTrack` 3개). `beat_grid.py` diff **0줄**(lane-2/t549 경계 유지, `git diff --stat HEAD -- server/design/beat_grid.py` 출력 없음). `protocol.ts` diff — 이전 라운드 종료 커밋(`a313c0ed`) 대비 **99줄 추가, 0줄 변경**(해시 `@@ -516,6 +516,41` · `@@ -780,7 +815,14` · `@@ -809,6 +851,10` · `@@ -881,6 +927,30` · `@@ -1287,12 +1357,21` · `@@ -1517,6 +1596,24`, 전부 순수 추가 — 기존 줄 삭제 0건).
- **안 한 것(지시 1~3항에는 없었지만, 이전 (b) 요청과의 간극 — 정직하게 기록)**: 직접 고르기 패널의 위치·색·효과·디머 프리셋 **드롭다운**("이 곡 + 쇼 기존 + 새 프리셋")은 만들지 않았다 — 밝기 "값"만 인라인 편집이고, 나머지는 여전히 명령창 문장(이름 또는 번호)으로만 고친다. 드로워 데이터(`drawerSections`)가 이미 있으니 다음 카드가 그대로 드롭다운 옵션으로 재사용할 수 있다.
- **잔여 위험**: (1) 사용처 계산(`_usage_for_slot`)이 `build_preset_drawer` 안에서 항목마다 중복 호출되지 않도록(이전 턴에서 1회로 캐싱) 고쳤지만, 전체 그리드를 매 항목마다 스캔하는 O(풀 항목 수 × 큐 수) 구조는 그대로다 — 큰 격자에서는 드로워 열기가 느려질 수 있다(이번 LOVE ATTACK 규모에서는 측정상 체감 없음, 별도 프로파일링은 안 함). (2) `.pr`/`.u` 같은 짧은 CSS 클래스 이름은 mockup과 맞추려 그대로 썼는데, 다른 전역 스타일과 충돌할 가능성이 있다(이 세션에서는 `npx vite build` 성공만 확인했고, 실제 화면에서의 시각적 충돌은 안 쟀다).

### M3 후속 4차 — 직접 고르기(①) 드롭다운: 위치·색·밝기(디머 프리셋) (카드 t551 계속, 코디네이터 지시 "build the direct-pick lists exactly as the mockup defines them")

위 M3 후속 3차의 "안 한 것"이 가리킨 바로 그 드롭다운. UI 전용 — `server/`·`ui/src/protocol.ts`·`ui/src/useCopilotSocket.ts`·`ui/src/App.tsx` 전부 diff 0줄(아래 검증). 기존 `onEditRequest`→`sendBeatGridEdit`→`buildBeatGridEdit(bar, target, changes)` 경로가 이미 임의 `changes` 모양을 그대로 올려 보내고, 서버 `apply_beat_grid_edit`의 화이트리스트가 이미 `position_preset_no`/`color_preset_no`/`brightness`를 받으므로 — 드롭다운 **데이터**(`drawerSections`)와 **적용 버튼**만 새로 짠 BeatGrid.tsx 안쪽 일이었다. TDD(RED-GREEN), cycle_type=tdd.

- **mockup 재확인 — 그룹 레이블의 정본 출처**: progress.md M3 후속 3차가 인용한 "이 곡 + 쇼 기존 + 새 프리셋"은 `ldbeat-runbook-ui-proposal-20261008.html`(최신 시안)의 `opts()`에는 없다 — 그 파일의 `opts()`(452/461행)는 평평한 목록 + "+ 새 프리셋"만이다(그렙으로 확인, "이 곡"/"쇼 기존" 0건). 정본은 **더 이른** `ldbeat-runbook-mockup-20261008.html`(이 카드 지시가 읽으라고 한 두 번째 파일)의 `opts()`(343~345행) — `<optgroup label="이 곡 프리셋">`+`<optgroup label="쇼에 이미 있는 프리셋">`(그 안 옵션은 `disabled` — 데모 `SHOW_PRESETS`에 번호가 없어서였다, 실제 데이터에는 번호가 있으므로 이 카드는 비활성화하지 않았다)+`"+ 새 프리셋 만들기…"` 셋. 이 카드는 이 레이블·순서를 바이트 그대로 썼다.
- **신규 순수 함수(BeatGrid.tsx) — 전부 RED-GREEN**: `NEW_PRESET_OPTION_VALUE`("__new", mockup 리터럴)·`formatDrawerEntryOptionLabel`("번호 이름")·`splitDrawerSectionEntries`(섹션을 `usage_count>0`="이 곡 프리셋"/`usage_count===0`="쇼에 이미 있는 프리셋"으로 가름, `null`·`unread`(POOL_UNREAD)면 둘 다 빈 배열)·`findDrawerSection`(풀 이름으로 섹션 찾기)·`buildPositionPresetChanges`/`buildColorPresetChanges`/`buildBrightnessPresetChanges`(각각 `{position_preset_no}`/`{color_preset_no}`/`{brightness:{mode:"dimmer_preset",...}}`).
- **UI 와이어링** — 큐 편집 칸의 "밝기"/"위치 프리셋"/"색 프리셋" 세 행이 이제 `onEditRequest` 있을 때 항상(기존 모드와 무관하게) 편집 가능(✎). 한 번에 한 필드만 열린다(`activeEditField`, mockup "같은 자리에서"). 밝기 행은 mockup `#eM`/`eDimMode` 그대로 값/디머 프리셋/디머 효과 3항 모드 선택을 먼저 보여주고, 모드별 하위 컨트롤이 바뀐다(값=숫자 입력(기존 동작 바이트 동일)·디머 프리셋=드롭다운(신규)·디머 효과=읽기 전용 안내(아래 Missing Inputs)). 위치·색 행은 각각 `drawerSections`의 Position/Color 섹션에서 드롭다운을 채운다. 세 필드 다 "적용"/"취소" 버튼 쌍을 쓴다 — mockup의 즉시-onChange 적용이 아니라 **이 프로젝트가 이미 밝기 "값" 모드에 쓰던 관행**을 그대로 따른 것(일관성, 네트워크 왕복이 매 키 입력마다 일어나지 않게). "+ 새 프리셋 만들기…"를 고르면 적용하지 않고 안내 문구만 뜬다(mockup `newPreset()`과 같은 "표시만, 쓰지 않음" 동작).
- **POOL_UNREAD/미열람 — 지어내지 않는다(코디네이터 지시)**: 드로워 섹션이 아직 안 왔으면(`null`, 서랍을 한 번도 안 열었음) 셀렉트가 비활성(`disabled`) + "프리셋 서랍을 먼저 열어야 선택할 수 있습니다." 안내. 열렸지만 그 풀을 콘솔에서 못 읽었으면(`section.unread`, POOL_UNREAD) 역시 비활성 + "이 풀을 콘솔에서 읽지 못했습니다." — 기존 드로워 렌더(1455행 부근)와 같은 문구, 두 "못 고름" 상태를 또렷이 구별했다.
- **거절 사유 그대로 노출 — 변경 없음**: 서버가 `apply_beat_grid_edit`에서 거절하면(예: 알 수 없는 번호) 기존 제네릭 `case "error"` 리듀서가 `event.message`를 그대로 `entries`에 싣는다(신규 리듀서 분기 0개, M3 후속 3차와 같은 경로) — 이 카드가 새 거절 표시 로직을 만들지 않았다.
- **검증 — 세 그렙(코디네이터 지시)**:
  1. `grep -rnE "changes\s*=\s*\{" ui/src` → 매칭 0건(exit 1) — UI는 여전히 서버 페이로드를 직접 구성하지 않는다.
  2. `git diff --stat HEAD -- server/design/beat_grid.py` → 출력 없음(0줄) — lane-2/t549 경계 유지.
  3. `git diff --stat HEAD -- ui/src/protocol.ts` → 출력 없음(**0줄, 추가도 0줄**) — 이 카드는 기존 `buildBeatGridEdit`가 이미 임의 `changes`를 받으므로 protocol.ts 쪽에 새 빌더가 전혀 필요 없었다(App.tsx·useCopilotSocket.ts도 diff 0줄, 같은 이유).
- **RED→GREEN**: 새 순수 함수 12개를 먼저 테스트에 import하고 구현은 비워 둔 채 `npx vitest run src/components/BeatGrid.test.tsx` → RED `12 failed | 122 passed (134)`(`buildPositionPresetChanges is not a function` 등, 마지막은 `NEW_PRESET_OPTION_VALUE` `undefined` AssertionError). 구현 추가 후 같은 명령 → GREEN `134 passed (134)`.
- **회귀(레인 로컬, 전체 — 이 프로젝트는 파일 단위 실행도 전체와 같은 속도)**: `npx tsc --noEmit` → 깨끗(출력 0줄). `npx vitest run` → `876 passed`(원래 864 + 신규 12). `npx vite build --mode=development` → 성공(68 modules transformed, `dist/` gitignore).
- **AC-LDBEAT-005 PASS 근거(이어서)**: 세 필드(위치·색·밝기) 전부 `onEditRequest`→`buildBeatGridEdit`를 거치고(그렙 1), 서버 `apply_beat_grid_edit`가 검증·적용하는 경로는 M3 1차와 바이트 동일(이 카드가 서버를 전혀 건드리지 않았으므로).
- **AC PASS/FAIL 매트릭스(이 라운드가 손댄 범위만)**:

| AC | 상태 | 근거 |
|---|---|---|
| REQ-LDBEAT-015(c)(밝기 단일모드, 값/디머 프리셋/디머 효과 중 하나) | PASS | UI 모드 선택이 서버 `_validate_brightness`(기존, 변경 없음)와 같은 세 값을 쓴다 — 모드 전환 시 이전 모드의 값을 같이 보내지 않는다(`buildBrightnessValueChanges`/`buildBrightnessPresetChanges` 각각 다른 두 필드만 채움) |
| AC-LDBEAT-005(UI가 서버 페이로드를 직접 구성하지 않음) | PASS | 그렙 1, 0건 |

**## Missing Inputs (아직 못 한 것 — 코디네이터 결정 대기, 개선하지 않고 정지)**

| 항목 | 막힌 이유 |
|---|---|
| **효과(움직임, `effect_preset_no`) 직접 고르기 드롭다운** | `effect_preset_no`는 서버 `resolve_effect_preset_name`/`EFFECT_SEARCH_POOL_NAMES`가 네 풀(Position/Color/Dimmer/**All 1**) 전부를 뒤진다(이름 해석 경로, M3 후속 2차) — 그런데 `drawerSections`는 Dimmer/Position/Color **세 풀뿐**이고 "All 1"(이 곡 전용 혼합 풀, `mixed_all: 22.0~22.99`)은 어느 섹션에도 없다. 거기다 Position/Color 풀 안에서도 "기본 위치·색 프리셋"과 "위치 효과·색 효과 프리셋"(`preset_pools.yaml`의 `position_effect`/`color_effect` 번호대)이 **같은 섹션의 번호 구분 없는 한 목록**에 섞여 있어, 지금의 `drawerSections` 모양만으로는 "효과만" 걸러낼 수 없다(걸러내려면 드로워 섹션에 새 분류 필드를 더해야 하는데, 이번 카드 지시 "feed from drawerSections, not from new data"가 막는다). 지어내지 않고 정지 |
| **디머 "효과"(`brightness.mode==="dimmer_effect"`) 드롭다운** | 같은 근본 원인 — `preset_pools.yaml`의 `dimmer_effect_a`(1.21~1.26)/`dimmer_effect_b`(1.31~1.33)가 Dimmer 풀 **안의 번호대**로만 "디머 프리셋"과 "디머 효과"를 가르는데, `drawerSections`의 Dimmer 섹션은 그 구분 없이 전체를 한 목록으로 준다. (참고: 서버 `_validate_brightness`는 `dimmer_preset` 모드의 `preset_no`를 번호대 검사하지 않는다 — REQ-LDBEAT-015(b) "base 풀은 번호대 검사 대상 아님" — 그래서 "디머 프리셋" 드롭다운에 Dimmer 풀 전체를 넣는 것은 서버 쪽에서 안전하다. 하지만 `dimmer_effect` 모드 쪽은 서버가 번호대를 검사하므로(코드 475~489행), 무엇이 "효과"인지 모른 채 목록을 주면 사용자가 거절될 선택지를 고를 수 있다 — 안내만 보이고 목록은 비워둔 이유) |
| 두 항목을 풀려면 필요한 것 | `drawerSections`에 `All 1` 풀 섹션을 추가하고, 세 풀(Position/Color/Dimmer) 각 항목에 `preset_pools.yaml` 번호대 기준 base/effect 분류 플래그를 더하는 서버 변경(새 데이터) — 이번 카드 지시가 "drawerSections 에서만, 새 데이터 없이"라 범위 밖. 다음 카드가 `build_preset_drawer`를 확장하면 이 UI 쪽은 `renderPresetOptions`/`splitDrawerSectionEntries`를 그대로 재사용할 수 있다(이미 범용) |

- **잔여 위험**: (1) `isBrightnessValueEditable`(이전 라운드가 만든 순수 함수)는 이제 컴포넌트 안에서 아무도 안 부른다(모드 전환 자체가 새 게이트 역할을 하므로) — export·테스트는 그대로 남겨 뒀다(죽은 호출부만 제거, 공개 함수·시험은 이 카드 범위 밖이라 안 지웠다). 다음 정리 카드의 후보. (2) 세 드롭다운 다 "적용" 전까지 로컬 draft 상태로만 있고, 서버가 거절해도 draft가 자동으로 되돌아가지 않는다(기존 밝기 "값" 모드와 같은 동작, 이 카드가 새로 만든 결함은 아니다 — M3 1차부터 있던 패턴). (3) 디머 프리셋 드롭다운이 Dimmer 풀 전체(실제로는 효과 프리셋도 섞여 있을 수 있는 번호)를 보여주므로, 사용자가 실제로는 "효과" 프리셋을 "프리셋" 모드로 잘못 골라도 서버가 막지 않는다(REQ-015(b) 설계가 base 참조는 번호대 검사 안 함이라 — 이게 결함인지는 director 판단 필요, 이 카드가 만든 간극이 아니라 기존 서버 설계의 결과임을 기록).

### M3 후속 5차 — 효과(움직임)·디머 "효과" 드롭다운 + 번호대 거절→경고 전환 (카드 t551 계속, 리드 지시 2026-10-11 "옵션 A" + 코디네이터 지시 조건 1~3)

위 M3 후속 4차 Missing Inputs 두 항목이 이번 절에서 풀렸다. 리드가 고른 **옵션 A**(mockup 자신이 같은 풀 안에서 번호대로 기본/효과를 가른다는 근거, `ldbeat-runbook-mockup-20261008.md` 14-17행·26-29행)를 적용했다 — "All 1" 풀을 새로 추가하지 않고, 기존 세 섹션(Dimmer/Position/Color) 안에서 `preset_pools.yaml` 번호대로 효과/기본을 가른다. TDD(RED-GREEN), cycle_type=tdd. 서버·UI 양쪽 변경.

**REQ-LDBEAT-015(b) 문면 검토 결과 — 경고-전환이 그 문면을 어기지 않는다(코디네이터 지시 "stop before changing server if the wording forbids it"에 대한 응답)**: spec.md REQ-LDBEAT-015(b)의 shall 절("효과 프리셋은 종류별 풀에 나눠 담긴다")은 **저장 분리 원칙**만 구속한다 — 정확한 번호대 자체는 shall 절이 아니다. 같은 REQ-015 행의 증거 칸이 명시적으로 이렇게 적어 뒀다: "**번호대는 결정이 아니라 재확인 대상(§5 항목 4 참조)**: 정확한 번호대는 M2/M3가 실제 쇼 파일과 대조해 확정하되, 로드맵이 든 예시는 ... 이 예시 자체는 (b)(e)가 요구하는 shall 절이 아니라 M2/M3 재확인 대상임을 §5 항목 4가 명시한다." 즉 번호대 숫자는 PROVISIONAL(이미 `preset_pools.yaml`의 `confirmed: false`가 같은 사실을 말한다) — `confirmed:false`인 동안 그 미확정 번호대를 근거로 거절하는 것이 오히려 REQ-015(b)의 실제 shall 절(저장 분리)보다 더 강하게 구속하는 과잉 집행이었다. 그래서 거절→경고 전환은 REQ-015(b) 문면을 어기지 않는다 — **서버 변경을 멈추지 않고 진행했다**(STOP 하지 않음).
  - 한 가지 발견한 별도 간극(이 지시의 "REQ-015(b) 문면" 범위 밖이지만 정직하게 기록): `acceptance.md` AC-LDBEAT-016(a)의 Then 절은 여전히 "각 효과가 선언된 종류별 풀 번호대 밖에 저장되면 거절된다"로 **무조건** 적혀 있다 — confirmed:false 예외가 반영돼 있지 않다. AC 문서(spec.md body)는 manager-develop 수정 권한 밖이라(§ SPEC Artifact Ownership — Forbidden modifications) 고치지 않았다. director/manager-spec이 AC-016(a)에 "confirmed:true일 때만" 조건을 더하는 개정이 필요한지 판단해야 한다.
- **서버 — 거절→경고 전환(조건3)** `server/design/beat_grid_edit.py`의 두 호출 지점(`effect_preset_no` 경로·`brightness.mode=="dimmer_effect"` 경로) — `validate_preset_pool_assignment`가 사유를 돌려줘도 `policy.get("confirmed")`가 거짓이면 더 이상 `raise`하지 않고 `warnings.append(f"⚠ 번호대 미확인 — {pool_reason}")`로 바꿔 격자에 그대로 쓴다(REQ-LDBEAT-010 "실기 미확인 모양" 경고-아닌-거절과 같은 관행). `confirmed:true`면 그대로 거절(회귀 없음, 시험으로 확인).
- **서버 — `is_effect_band` 판정(조건1)** `server/design/beat_grid_presets.py` `build_preset_drawer`의 시그니처를 `confirmed: bool` → `policy: Mapping`로 바꾸고(유일한 생산 호출자 `server/web/session.py::beat_grid_preset_drawer`도 같이 고쳤다), 각 드로워 항목에 `is_effect_band`를 더했다 — 새 판정 규칙을 짜지 않고 `apply_beat_grid_edit`가 이미 쓰는 `validate_preset_pool_assignment`(+ `pool_name_to_effect_kind`, 둘 다 기존 함수 재사용)를 그대로 불러 "그 번호가 그 풀의 효과 번호대 안에 있는가"를 판정한다 — 번호대 리터럴은 `beat_grid_presets.py`에도 없다(조건1, `inspect.getsource` 류 grep으로 재확인하지 않았지만 코드에 숫자 리터럴을 추가하지 않았다는 사실 자체로 충족). 번호대가 아직 안 선언돼 있으면(`pools`가 비었거나) "효과"로 지어내지 않고 `False`(기본 쪽)로 떨어진다.
- **UI — 효과(움직임)·디머 효과 드롭다운(조건1)** `ui/src/components/BeatGrid.tsx` — 새 순수 함수 `splitDrawerSectionEffectEntries`(섹션에서 `is_effect_band`인 항목만 골라 다시 "이 곡 프리셋"/"쇼에 이미 있는 프리셋"으로 가름, 기존 `splitDrawerSectionEntries`와 `splitEntriesByUsage` 헬퍼를 공유)·`buildEffectPresetChanges`(`{effect_preset_no, effect_kind:"position"}`, 이 드롭다운은 무빙 전용이라 종류를 고정했다 — 리터럴이지만 번호대 숫자가 아니라 REQ-LDBEAT-006(i-3)의 닫힌 종류 어휘)·`buildBrightnessDimmerEffectChanges`. "효과 프리셋" 행(무빙 역할, `hints.includes("움직임")`)이 이제 `isEffectRow`로 편집 가능해졌고, 밝기 모드 "디머 효과"의 자리표시자 안내문을 실제 드롭다운으로 바꿨다. `renderPresetOptions`를 섹션이 아니라 이미 가른 `{thisSong, showExisting}` 쌍을 받도록 일반화해 두 경로(기본/효과)가 같은 JSX 조립 함수를 공유한다.
- **UI — "번호대 미확인" 배지(조건2)** 두 새 드롭다운 옆에 기존 `presetPoolBandBadge`(드로워와 같은 배지, 새 함수 0개)를 그대로 달았다 — `positionSection`/`dimmerSection`의 `bands_confirmed`가 `confirmed:false`인 동안 뜬다.
- **protocol.ts — 추가만(1훅크)**: `BeatGridDrawerEntry`에 `is_effect_band: boolean` 필드 하나 추가. 훅크 헤더: `@@ -524,6 +524,12 export interface BeatGridDrawerEntry {`(6줄 추가, 0줄 변경·삭제). `git diff --stat HEAD -- ui/src/protocol.ts` → `6 insertions(+)`.
- **`beat_grid.py` diff 0줄**(lane-2 경계 유지, `git diff --stat HEAD -- server/design/beat_grid.py` 출력 없음).
- **RED→GREEN(서버, `server/tests/test_beat_grid_edit_t551.py`)**: 신규 시험 4개(`TestPresetPoolBandWarningWhileUnconfirmed`) 추가 전 `uv run --quiet pytest server/tests/test_beat_grid_edit_t551.py -q` → RED `2 failed, 42 passed`(effect_preset_no·dimmer_effect 각 1건 — `BeatGridEditError: 프리셋 번호 99.99는 'dimmer' 효과 풀 번호대(1.21~1.26 또는 1.31~1.33) 밖입니다`). 서버 구현(confirmed 게이트) 후 같은 명령 → GREEN `44 passed`. 기존 `test_effect_preset_outside_pool_band_rejected_via_apply`는 `monkeypatch`로 `confirmed:true`를 명시해 격리했다(실제 yaml이 `confirmed:false`라 이 monkeypatch 없이는 "번호대 거절"이 아니라 "근거 승인 누락" 거절을 재는 것으로 조용히 바뀌는 것을 발견 — 경계검증).
- **RED→GREEN(서버, `server/tests/test_beat_grid_presets_t551.py`)**: `TestPresetDrawerEffectBand` 신규 5개 + 기존 5개를 `policy=` 키워드로 교정하기 전 `uv run --quiet pytest server/tests/test_beat_grid_presets_t551.py -q` → RED `10 failed, 12 passed`(`TypeError: build_preset_drawer() got an unexpected keyword argument 'policy'`). 구현 후 → GREEN `22 passed`.
- **RED→GREEN(UI, `ui/src/components/BeatGrid.test.tsx`)**: `splitDrawerSectionEffectEntries`/`buildEffectPresetChanges`/`buildBrightnessDimmerEffectChanges` 시험 6개 추가 전 `npx vitest run src/components/BeatGrid.test.tsx` → RED `6 failed | 134 passed (140)`(`TypeError: splitDrawerSectionEffectEntries is not a function` 등). 구현 후 → GREEN `140 passed (140)`.
- **회귀(레인 로컬)**: `uv run --quiet pytest server/tests/test_web_*.py server/tests/test_session*.py server/tests/test_beat_grid*.py server/tests/test_cue_sheet_edit.py server/tests/test_position_fx.py server/tests/test_preset_label_lookup_t232.py -q` → `1818 passed`. `uv run --quiet ruff check`/`ruff format --check`(건드린 5개 서버 파일) → `All checks passed!`/`5 files already formatted`. UI: `npx tsc --noEmit` 깨끗 · `npx vitest run` → `882 passed`(이전 라운드 876 + 신규 6) · `npx vite build --mode=development` → 성공.
- **AC-LDBEAT-016(a) PASS 근거(갱신)**: confirmed:true 경로는 기존과 바이트 동일(그대로 거절) — `test_effect_preset_out_of_band_still_rejected_when_confirmed`·`test_dimmer_effect_preset_out_of_band_still_rejected_when_confirmed`. confirmed:false(실제 운영 상태) 경로는 이제 PASS 기준이 "거절"이 아니라 "경고"로 바뀐다 — 위 acceptance.md 간극 기록 참조, AC 문면 개정은 이 카드 권한 밖.
- **잔여 위험**: (1) acceptance.md AC-LDBEAT-016(a) 문면이 confirmed:false 예외를 아직 반영 안 함(위 기록, director/manager-spec 판단 대기). (2) `buildEffectPresetChanges`가 `effect_kind:"position"`을 고정해, 이 드롭다운은 움직임(무빙) 역할에만 쓴다 — 색 효과·밝기 효과를 이 패턴으로 넓히려면 `effect_kind`를 role/field 별로 분기하는 로직이 필요하다(이번 라운드 범위 밖, 코디네이터 지시가 "effect (movement)"로 좁혔다). (3) `is_effect_band` 판정은 매 드로워 조회마다 풀의 모든 항목에 대해 `validate_preset_pool_assignment`를 다시 부른다(이전 라운드가 이미 적었던 `_usage_for_slot` O(풀×큐) 구조와 같은 종류의 비용, 이번 규모에서는 체감 없음 — 별도 프로파일링 안 함).

### M4 — 콘솔 송신 경로: 새 에미터 + 승인=송신 승격 + 승인 단위 (카드 t549)

REQ-LDBEAT-001/003/011~013 구현. cycle_type=tdd. 콘솔 접촉 0건, 콘솔 쓰기 0건. 전체 verdict는 `.moai/reports/t549/run-verdict.md`.

- **승인=송신 승격** — `.moai/reports/t512/approval_vs_sent.py`(리포트 스크립트)의 로직을 `server/design/approval_vs_sent.py`로 로직 그대로 포팅 — 판정 함수 본문 동일, 결과 객체로 감쌈(REQ-LDBEAT-011). `.moai/reports` import 0건(AST 전수 조사로 확인).
- **새 에미터 `server/design/beat_grid_emit.py`** — `songcue.py`의 `_ascii_label`/`_format_seconds` 재사용(songcue.py diff 0줄), t520이 증명한 `Store Sequence`/`Assign Sequence At Timecode` 모양으로 역할별 시퀀스 × 타임코드 트랙 다대다 배선. 칸 내용은 `app_movement_commands`/`At Preset` 정적 리콜/`brightness_value_commands`로 구성.
- **REQ-LDBEAT-001 M1 게이트** — progress.md의 실제 M1 판정(①⑧만 PASS)을 읽어, 효과 프리셋 리콜(④)·`app_movement`(⑤⑦⑨) 의존 칸을 전부 거절(부분 적용 0건). LOVE ATTACK 전수 확인: 효과 8칸(BACK 3·7·18·22, SIDE-ALL 11·14, MOVER-U 14, MOVER-D 14) + app_movement 4칸(MOVER-U 11·18, MOVER-D 7·22) = 12칸 거절, 허용 6칸(FOH 7, WASH-ALL 7·14, MOVER-D 18, BLIND 17·18). ⑩⑪은 `beat_grid_probes.DEFAULT_PROBE_IDS`(1~9)·REQ-001 조문 범위 밖이라 게이트에서 뺐다(이 레인의 판단, run-verdict §판단 콜 참조).
- **추가 발견** — LOVE ATTACK 8트랙을 타임코드 하나에 몰면 M1 ①이 구조로 확인한 실제 최대(6)를 넘어 **트랙 레벨 전부 거절**(`MEASURED_MAX_TIMECODE_TRACKS=6`, 이 레인이 독자적으로 추가한 보수적 상한). 둘 이상 타임코드로 쪼개거나 ①을 6개 초과로 재확인해야 한다 — 감독/리드 판단 사항.
- **승인 단위 `server/design/send_approval.py`** — `build_write_approval_batch`(쓰기 N≥2칸도 아티팩트 1개, AC-LDBEAT-015)·`PreviewApprovalSession`(미리보기 세션-1회-반복, AC-LDBEAT-002(b), 쓰기 승인과 완전 독립).
- **검증**: 신규 `test_approval_vs_sent_t549.py`(10)·`test_send_approval_t549.py`(7)·`test_beat_grid_emit_t549.py`(27) + 기존 관련 181개 = 225 passed, 회귀 0. `ruff check`/`format --check` 통과. `git diff af00ffb2 -- server/director/emit.py ui/src/components/CueSheetTimeline.tsx server/looks/songcue.py` → 0줄(AC-LDBEAT-012).
- **작업 위치**: 구현 서브에이전트가 자동 격리 워크트리(`agent-a96dd8e7…`)에서 커밋했고, 레인이 그 4커밋을 `WT-ldbeat-console-send`(`.claude/worktrees/t549`)로 fast-forward 했다 — 머지 대상은 이 브랜치다.
- **안 잰 것**: 이 에미터 출력의 콘솔 송신 0건(전부 순수 함수)·`_timecode_commands` 함수 자체 재사용 불가(SongCueBundle 결합 — 문자열 모양만 재현, grep으로 재확인)·AI 제안→적용→전송 전체 UI/서버 배선(카드 범위 밖, Deliverables 5)·`PreviewApprovalSession`의 서버 세션 배선·승인=송신 비교를 이 에미터 송신 뒤 호출하는 배선·8트랙 전체를 한 타임코드에 담는 결정(쪼갤지 ①을 재확인할지)·`Store Cue` 뒤 `ClearAll` 삽입(이 레인의 설계 판단, t538 전례 인용 — 실기 미확인).

### M4 후속 — 게이트 증거 갱신 + 8트랙 타임코드 재측정 (카드 t553)

REQ-LDBEAT-001/006(vi) 후속. cycle_type=tdd. Part ①(측정된 무빙 허용목록) 콘솔 접촉 0건. Part ②(실기 프로브)는 전부-거절까지만 — 실행은 리드 승인 뒤. 전체 verdict는 `.moai/reports/t553/run-verdict.md`.

- **Part ① — 측정된 무빙 허용목록** — 위 "2026-10-11 대체 고지" 참조. `server/design/beat_grid_data/measured_movements.yaml`(신설, 리그 전용 group_no·shape·axes 숫자는 전부 여기에만) + `server/design/beat_grid_measured.py`(신설, `is_movement_measured_open` — group_no+shape+axes **정확 일치**만, `base_condition != "any"`는 매칭돼도 영구 닫힘). `beat_grid_emit.blocked_m1_items_for_cue`에 키워드 전용 `group_no` 매개변수 추가(기본값 `None` — 기존 2-위치-인자 호출부는 바이트 동일하게 동작), `_emit_cue`가 이미 가진 `group_no`를 넘겨준다.
- **RED 먼저**: `server/tests/test_beat_grid_measured_t553.py`(9개, 신설) — 모듈이 없어 `ModuleNotFoundError`로 전부 실패 확인(`.moai/state/verify/` 아래 명령 출력 참조, run-verdict에 전재). GREEN: 모듈 구현 뒤 9개 전부 통과.
- **기존 t549 시험 갱신(behavior 변경, 삭제 아님)** — `test_beat_grid_emit_t549.py`의 LOVE ATTACK 전수 통합 시험(`test_blocked_and_allowed_cells_match_the_m1_gate_mapping`)이 `("MOVER-D", 7)`·`("MOVER-D", 22)`를 "거절"에서 "허용"으로 옮김(새 측정 증거가 그 통합 시험이 검증하던 실제 동작을 바꿨다 — 날짜 붙은 주석으로 사유를 남김). `TestBlockedM1ItemsForCue`에 `group_no` 오버라이드 전용 단위 시험 4개 추가(열림/안열림/기본값 유지/다른 항목 무영향).
- **Dimmer2 확인(코드 추적만, 콘솔 접촉 0)** — `app_movement.brightness_value_commands`는 호출자가 넘긴 `dimmer_attributes`의 모든 디머 계열 속성에 이미 일반적으로 명령을 낸다(Spiider의 Dimmer+Dimmer2 둘 다 포함, 코드 수정 불필요). 다만 `love_attack.yaml`의 MOVER-D 트랙은 전체 큐에 `brightness` 필드가 0건이라, 이제 열린 bar 7·22의 `app_movement` 큐도 Dimmer/Dimmer2 명령을 전혀 안 낸다 — 데이터 보강은 이 카드 범위 밖이라 고치지 않고 보고만 한다.
- **Part ② — 8트랙 타임코드 + MOVER-U 기운 기준 Pan 프로브** — 설계·리허설·전부-거절만(실행 금지). 상세는 `.moai/reports/t553/run-verdict.md`.
- **검증**: `uv run --quiet pytest server/tests/ -k "beat_grid or app_movement" -q` → 171 passed(회귀 0). `ruff check`/`format --check` 통과(touched files). `git diff` — `server/director/emit.py`·`server/looks/songcue.py`·`ui/src/components/CueSheetTimeline.tsx`·`server/safety/**`·`console/lua/**` 0줄.
- **작업 위치**: 이 구현 서브에이전트는 배차서가 지정한 `.claude/worktrees/t553`(`WT-ldbeat-gate-update`)가 아니라 런타임이 자동 격리한 다른 워크트리(`.claude/worktrees/agent-a6fd8f53bcc5b099d`, 브랜치 `worktree-agent-a6fd8f53bcc5b099d`)에서 커밋했다 — HEAD는 `ae3afea6`의 자손(`git merge-base --is-ancestor` 확인). 레인/리드가 이 브랜치를 `WT-ldbeat-gate-update`로 fast-forward 해야 한다.
- **안 잰 것**: D4(Pan+Tilt circle, t548 seq 334)는 `app_movement_commands`가 아직 `shape="wave"`만 구현해(circle 미구현) 허용목록 엔트리로 옮기지 않았다(이 카드 범위 밖) · MOVER-U의 Pan 단독은 Part ②의 새 프로브가 실행·판정되기 전까지는 허용목록에 올리지 않는다(리드 "do NOT open bar 18... until the lead executes and judges it moved") · MOVER-D bar 7·22가 실제로 켜진 채 움직이는지(Dimmer2 공백 참조)는 데이터 보강 없이는 확인 불가.
- **실기 실행 (2026-10-11, 리드 「실행」 뒤, 레인이 묶음마다 멈춰 전송, 쇼 저장 0)** — 승인 목록 sha256 은 보낼 때마다 다시 재 일치 확인.
  - **① 8트랙** — `approval_t553.txt`(sha256 `cc7f5881…902e`) 1~22줄 전부 OK. 되읽기 `Timecodes/32/1` childCount 9(Marker 1 + Track 8), TARGET Sequence 226..233 순서 일치 → 리드 PASS. 상한을 `server/design/beat_grid_data/measured_console.yaml`(`max_timecode_tracks: 8`, 근거 포함)에서 읽도록 바꿨다 — `MEASURED_MAX_TIMECODE_TRACKS` 6→8, LOVE ATTACK 8트랙이 타임코드 하나에 들어간다(`test_beat_grid_timecode_cap_t553.py`, RED 3 실패 → GREEN). 8 초과는 여전히 안 쟀다.
  - **MOVER-U(Group 11) Pan 단독** — 336(기준 `Tilt At 45`): 리드 판정 움직임(프레임 변화 4.5~5.3%). 338(bar 18 칸 그대로 = `app_movement_commands` 출력, 기준 `At Preset 2.1`, ±12, 위상 줄 없음): 판정 불가 0.00~0.01%. 337(기준 `At Preset 2.1`, 나머지 336 과 같음): 판정 불가 0.01~0.02%. → **2.1 기준(빔 거의 수직)에선 Pan 단독이 안 보인다** — 원인은 기준이지 진폭·위상 줄이 아니다(t548 D2 와 같은 그림). **bar 18 은 닫힌 채.** 열려면 기울인 위치 프리셋을 칸에 지정해야 한다(감독 결정 대상). `measured_movements.yaml` 에 group 11 Pan 기록 추가(`requires_tilted_base_unverifiable`, 게이트 안 엶).
  - 레인이 고친 것: 337 첫 시도는 스크립트 빈 번호 확인이 337·338 을 함께 봐서 「338 이미 있음」으로 0줄 보내고 멈췄다(안전장치 정상) — 확인 대상을 337 하나로 고쳐 다시 보냄(명령 줄 무변경, 승인 sha 그대로). 근거 `.moai/reports/t553/live/cell_337_on_stopped_slotcheck/`.
  - **옆 화면 확인** — 「2.1 = 빔 수직」은 처음엔 정면 화면만 본 추정이었다. 감독이 onPC 3D 를 FRONT+SIDE 로 나눈 뒤 승인된 20~23줄(켜기 + `At Preset 2.1`, 프로그래머만)을 다시 보내 리드가 SIDE 캡처로 판정: 8대 빔이 트러스에서 거의 수직으로 떨어지고 바닥 스폿은 장비 줄 바로 아래, 앞으로 아주 조금 — **이제 잰 사실**. 그 뒤 37줄 ClearAll. 근거 `.moai/reports/t553/live/side_lit/`·`side_clear/`(캡처 파일은 리드 작업 폴더).
  - 이 카드 최종: MOVER-D 7·22 열림, MOVER-U 11·18 닫힘, 효과 프리셋(④) 닫힘, 타임코드 8트랙 허용.
- **작업 위치 정정**: 위 「작업 위치」 줄은 서브에이전트 시점 기록이다 — 레인이 그 커밋을 `WT-ldbeat-gate-update` 로 fast-forward 했고 머지 대상은 이 브랜치다.

### M7 step 5 — 앱 서버 화면 시안 대조 캡처 + 차이 목록 (카드 t583, 2026-10-11)

고치지 않고 목록만. 기준 `origin/main` 00393f75. 처음으로 **앱 서버(`create_app`)를 띄워 빌드된 UI 를 헤드리스 브라우저로** 찍었다(이전 t532·t534·t537 은 컴포넌트만 번들한 하네스). 콘솔 연결 0 · 콘솔 쓰기 0(`console_executed.log` 0바이트) · 사용자 앱 데이터 폴더 접촉 0.

- **차이 목록**: `.moai/reports/t583/diff-list.md` — 영역 8곳(상단 바·플레이 묶음·곡 지도·타임라인·한눈에 표·2D 무대·편집 칸·전환 화면) × 1450/1700px. 🔴 4건: 세로 1000px 창에서 타임라인이 171px(시안 440px)라 8트랙 중 2줄만 보임 · 막대를 고르면 줄 이름 칸이 막대에 덮임 · 편집 칸/전환 화면이 타임라인 높이에 묶여 전환 내용이 잘림 · 2D 무대 경고 목록 다섯째 줄이 범례 줄과 겹침.
- **캡처**: `.moai/reports/t583/side_by_side/{W}_{영역}.png`(왼쪽 시안·오른쪽 앱) + 전체 화면 + `regions.json`(영역 크기 실측).
- **재현**: `serve_fake.py`(FakeConsole + LOVE ATTACK 실측 분석 t509 + 제품 기본 격자 + t525 무대 좌표) → `capture.py`(Playwright). 실행 명령은 diff-list.md 머리말.
- **안 잰 것**: 세로 1000px 한 높이만 · ✎/이음매 ◆/무대 장비 클릭 미조작 · 프리셋이 채워진 곡 미사용(「미정」 칸 상당수는 데이터 탓, 목록에 ⚪ 로 구분) · 171px 원인 CSS 미조사.

### M7 step 5 후속 — 배치 결함 🔴 4건 고침 (카드 t585, 2026-10-11)

t583 diff-list 🔴 4건을 원인 CSS 부터 재고 고쳤다(CSS 두 파일 + 회귀 시험 5개, 🟡 는 손대지 않음, 콘솔 0). 전체 verdict `.moai/reports/t585/run-verdict.md`.

- **원인(계산된 스타일 실측)**: ① `.beat-grid-mid{flex:1}` 가 남은 공간만 받아 1000px 창 171px·900px 창 71px · ② 줄 이름 배경이 글자 높이 15px 뿐 + 폴더 머리가 고정 대상 아님 · ③ 편집 칸이 타임라인 높이에 묶여 171px · ④ 겹침이 아니라 경고 목록 64px 에 15px 줄이 4.27줄 들어가 다섯째 줄이 반만 잘림(t583 판독 정정).
- **고친 것**: 타임라인 440px 고정(REQ-016(b) 시안 수치) + 틀 `overflow-y:auto` · 줄 이름 `align-self:stretch` · 폴더 `max-content` + 폴더 머리 sticky · 경고 줄 높이 16px.
- **증거**: 1450·1700 × 세로 900·1000·1200 전후 캡처 — 타임라인·편집·전환 칸 전부 440px(전 71/171/371), 페이지 오류 0. 새 시험 5개는 main CSS 에서 5개 전부 실패·고친 CSS 에서 통과. vitest 1162 passed.
- **해석 하나**: REQ-004(b) 「한 화면 높이로 고정」을 시안 원문대로 「칸이 줄 수에 따라 늘지 않음」으로 읽고, 칸 합이 창보다 크면 틀째 스크롤하게 했다 — run-verdict 에 리드 판단 요청으로 적음.
- **새 카드 후보**: 세로 900px 에서 상단 바 「⇪ 반영」 잘림 + 긴 BPM 문구 — main 에도 있는 기존 결함.

### M7 step 5 후속 2 — 시안과 다른 곳(🟡) 영역별 정리 (카드 t586, 2026-10-11)

t583 diff-list 🟡 을 전수 처리표로 갈랐다(상단 바·플레이 묶음은 t587, ★ 은 t567 몫이라 건드리지 않음, 콘솔 0). 전체 verdict `.moai/reports/t586/run-verdict.md`.

- **고친 것(시안 수치 그대로)**: 눈금에 구간 이름 + 진흙색 경계선(38px) · 줄 이름 둘째 줄 `G4 · 201~202 · 2대`(무대 판독 소속에서만) · 한눈에 표 역할 폴더 묶음 + 머리말 구간 이름·안내 · 무대 머리말 `N마디 · 초` · 편집 칸 머리 장비 범위 · 전환 머리말 `전환 · 줄 · Cue a → Cue b` · 명령 레이블 · 맨 아래 조작 안내.
- **동작 확인(바꾸지 않음)**: ✎ 는 값을 누르면 드롭다운이 열리고, 이음매 ◆ 는 전환 화면을 연다(`probe_clicks.py`).
- **판독 정정**: 무대 고른 줄 노란 점선·이름표는 이미 있다 — t583 은 소속 미확인 줄을 골라 안 보였다.
- **유지(이유 있음)**: SCENE 경고 줄(REQ-006(iv-3))·M1 프로브 칸·빔/워시 장식(REQ-022(b) 밖).
- **증거**: vitest 1179 passed, 빌드 통과, `{1450,1700}x1000` 전후 영역 캡처(페이지 오류 0).
- **리드 판단 요청**: 편집 칸을 처음부터 열린 드롭다운으로 바꿀지.

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
