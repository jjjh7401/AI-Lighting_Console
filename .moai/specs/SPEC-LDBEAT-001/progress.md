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

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
