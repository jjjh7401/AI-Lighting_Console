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

**(5) SCENE 메모 — 리드 추가 지시(2026-10-10), §REQ-006 밖의 새 데이터 요소(감사 필요)** — §4 SCENE 열 값(BACK/WASH/FOH가 섞인 역할·효과 혼성 칸, 카드 t526이 이미 "SCENE은 단일 콘솔 그룹이 아니라서 트랙에서 뺐다"고 결정한 바로 그 열)은 리드 규칙(두 조건 모두: (a) §4 칸이 그룹을 직접 부르고 (b) 그 그룹 번호가 이미 `beat_grid_data/love_attack.yaml`의 확인된 트랙에 있을 때만 그 트랙에 얹는다, 충돌이면 메모)을 전수 적용한 결과 **여섯 값 전부가 메모로 떨어졌다** — BACK(bar 0)은 그룹 번호가 확인돼 있지만 그 마디에 이미 펄스 큐(「앞박 1회」)가 있어 충돌, WASH·FOH는 이 데이터 파일에 트랙 자체가 없어(그룹 번호 미확인) 메모, 나머지 셋(11~13·18~21·22~25)은 칸 자체가 그룹 이름을 안 부름. `BeatGridView.scene_memos: list[{bar,text,source_ref}]`로 겹침 검증 로직과 완전히 분리된 새 리스트에 담았고(트랙 `cues`에 끼워 넣지 않음 — `TestOverlapIndependentOfCellStructuring`로 확인), UI는 곡 전체 지도의 해당 행에 「미정」 배지(`.has-scene-memo`, 주황 테두리)와 "이 마디 한눈에" 패널 위에 경고 배너(원문 그대로 + `source_ref`)로 보여준다. **이 데이터 요소(`scene_memos`)는 spec.md REQ-LDBEAT-006이 정의한 범위 밖이다** — REQ-006은 트랙 `BeatGridCue`의 구조화만 다루고 "트랙에 못 옮기는 §4 값을 메모로 보존한다"는 요구는 spec.md 어디에도 없다. spec.md는 고치지 않았다(리드 지시대로) — 이 추가가 REQ-006 확장으로 정식 편입돼야 하는지(또는 신설 REQ가 필요한지)는 **다음 plan-audit/감사 라운드의 판단 대상**으로 남긴다.

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

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
