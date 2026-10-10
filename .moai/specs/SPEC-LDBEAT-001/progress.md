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
| ① 타임코드 트랙 ≥3(목표 6) | `p1_tc_tracks.py` (TC 30) | exit 0, 막힌 줄 0 | 9/9 거절 | `live/p1/` | **통과(구조)** — `4fdce816` 기록 |
| ② Goto 2번 이후·여러 시퀀스 동시 | `p2_goto_multi.py` (쓰기 0) | exit 0 | 거절 | `live/p2_on/` | **기계 PASS · 눈 미확인** — `4fdce816` 기록 |
| ③ 프리셋 수정 전파 | `p3_preset_propagation.py` (v2: 4.301 / v3: 4.302, 시퀀스 300) | v3 exit 0 | v3 4/4 거절 | `live/p3_a/` 묶음 1만 | **미확인 — `Attribute 'Color' At Preset 4.9` 거절(Illegal object)**. v3 재승인 대기 |
| ④ 효과 프리셋의 SM15·Measure | `p4_effect_speedmaster_measure.py` (21.301, 시퀀스 301) | exit 0 | 거절 | `live/p4_a/` 19줄 OK · `live/p4_off/` 끄기 OK | **미확인** — 감독 눈: 「다 같이 깜빡임」(번갈아 아님). 디머 페이저는 재생, Step 2 는 안 살아남음, SM15·Measure 는 눈으로 판정 불가 |
| ⑤ 위치 프리셋 위 상대값 | `p5_relative_on_position_preset.py` (시퀀스 302) | v3 exit 0 | v3 거절 | 보류(리드) | **미실행** — ③과 같은 줄 형태라 v3 재승인 대기 |
| ⑥ 타임코드 중간 재생 | `p6_mid_start.py` (TC 31) | exit 0 | 거절 | `live/p6_a/` | **미확인 — 문법 불명**(`Goto Time 5 Timecode 31` → User Canceled Command) — `4fdce816` 기록 |
| ⑦ 큐 하나 그룹 하나 + Step 2 | `p7_single_selection_step2.py` (시퀀스 303, 대조 큐 포함) | exit 0 | 미실행 | 미실행 | **미실행** |
| ⑧ 같은 그룹 두 시퀀스 분담 | `p8_shared_group_two_sequences.py` (시퀀스 304·305) | exit 0 | 미실행 | 미실행 | **미실행** |
| ⑨ circle·발리후 | `p9_shapes.py` (시퀀스 306~308) | v3 exit 0 | v3 거절 | 보류(리드) | **미실행** — ③과 같은 줄 형태라 v3 재승인 대기 |

**실기 2026-10-10 (응답기 1.6.6, 쇼 저장 0)**

- ③ 묶음 1: 7줄 중 `Attribute 'Color' At Preset 4.9` 만 `Illegal object`(`live/p3_a/steps.jsonl:7`). 뒤 줄 `Store Preset 4.301` 은 OK(`:8`) → **이름만 있는 빈 프리셋 4.301**(자식 0, `live/p3_a_readback.txt`)이 남았다. 지우지 않음(삭제는 승인 범위 밖). 묶음 2 이후는 안 보냄 — 시퀀스 300 없음.
- 🔴 **묶음 안에서 한 줄이 실패해도 나머지 줄이 계속 나갔다.** 원인은 콘솔이 아니라 **이 프로브의 반복문**이다: `.moai/reports/t506/tc_probe.py:220-231` 은 줄마다 `execute` 하고 실패해도 `all_ok` 만 내릴 뿐 멈추지 않는다(멈추는 건 묶음 사이, `m1_common.py:192-194`). 콘솔 쪽 사실은 「각 줄이 따로 실행된다 — 앞 줄 거절이 뒤 줄을 막지 않는다」까지. **앱 송신기(emit 경로)가 실패 줄에서 멈추는지는 안 쟀다** — 앱 설계에 쓰기 전에 그쪽 코드를 따로 읽어야 한다.
- ④ 묶음 1~3, 19줄 전부 OK(`live/p4_a/steps.jsonl`). `Attribute 'Dimmer' At Measure 1`·`At SpeedMaster 15`·`At Preset 21.301`(Attribute 접두 없는 호출) 모두 콘솔이 받았다. 시퀀스 301 CURRENTCUE = `Sequence 301.1`(`live/p4_held_readback.txt`). 프리셋 21.301 `SPEEDMASTER` 읽기 `"None"`, `PRESETDATA` 빈 문자열 → 이 두 속성으로는 SM15·Measure 저장 여부를 못 가린다.
  - 감독 판정(리드 전달, 2026-10-10): **「다 같이 깜빡임」** — Group 11 이 번갈아(Step 2)가 아니라 한꺼번에 깜빡였다. 디머 페이저 자체는 재생됐지만 Step 2 가 프리셋 저장→그룹 호출 경로에서 살아남지 않았다. 박자 속도(SM15·Measure)는 번갈아가 없어 눈으로 가릴 수 없다 → **미확인**.
  - 원인 후보(전부 **가설**, 하나도 안 쟀다): (가) 프리셋이 Step 정보를 담지 않는다 (나) 프리셋은 담지만 그룹 선택 뒤 `At Preset` 호출에서 Step 이 풀린다 (다) `/Universal` 저장이 선택 순서 의존 정보를 버린다. 가르려면 ⑦(같은 Step 2 를 큐에 직접 저장)과 대조하고, 그다음 저장 옵션만 바꾼 묶음이 필요하다.
  - 끄기: `Off Sequence 301` OK(`live/p4_off/`).
- v3 문면(③⑤⑨ `Attribute '<X>' At Preset` → `At Preset`, ③ 프리셋 번호 301→302): 바뀐 줄 10, `approval-diff-v3.md`. 리허설 3/3, 실기 전부-거절 3/3(실행 줄 0). 이전 문면은 `denyall_v2/`.

- 새 번호 비어 있음 실측: `.moai/reports/t531/r1_free_slots.txt`(실기 읽기). 실행 직전에 다시 읽는다.
- 실기 쇼 상태(읽기): 시퀀스 1-15·210·219·220-233·1999·2000, 타임코드 1·2·7·8·9·19·20·21 — t520 기록의 시퀀스 250번대·TC 22/23 은 없다(`r0_pools.txt`·`r0b_pools.txt`). Speed15 `NORMEDVALUE` 69.
- 리허설은 게이트 심사만 증명한다 — 가짜 콘솔은 명령의 콘솔 의미를 흉내 내지 않는다.
- 미측정 문법: ③ 프리셋 수정 줄, ⑥ `Goto Time 5 Timecode 31`(전례 0 — 거절은 「미확인 — 문법 불명」), ④·⑤·⑨ 그룹 선택 프리셋 호출.
- **통과 판정은 ①(구조)뿐이다. ②④는 눈 판정 전, ③⑥은 미확인, ⑤⑦⑧⑨는 미실행 — REQ-LDBEAT-001 게이트상 M4 송신은 ① 말고 어떤 항목에도 기대지 못한다.**

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
