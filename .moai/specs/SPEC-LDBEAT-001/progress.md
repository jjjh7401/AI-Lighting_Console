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

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
