---
id: SPEC-COPILOT-EXECREF-001
title: "안전 게이트의 Executor 참조 인식"
version: "0.2.0"
status: in-progress
created: 2026-07-22
updated: 2026-07-23
author: manager-spec
priority: P1
phase: "Post-MVP 연출 UI 하드닝 (v1.1.0 target)"
module: "server/safety/"
lifecycle: spec-anchored
tags: "safety-gate, expand-or-hold, executor, reference-resolution, fail-closed, false-negative, panel"
tier: L
related_specs: [SPEC-COPILOT-MVP-001, SPEC-COPILOT-SHOWUI-001]
---

# SPEC-COPILOT-EXECREF-001 — 안전 게이트의 Executor 참조 인식

> **(v0.2.0 범위: 인식만 — 단일-press 복원은 후속 SPEC 대기)**

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-22 | manager-spec | 최초 작성 (draft, Tier L). 출처: SPEC-COPILOT-SHOWUI-001 M3 실행 중 발견된 결함(progress.md §E.2 "M3에서 발견한 사항 — 사람 결정 필요(승인 게이트 빈도)", 199-219행)과 그에 대한 사람 결정 — 게이트측 Executor 인식 채택, 대안 (a)승인-매-누름 수용, (b)시퀀스 참조 치환은 기각(research.md §2). 아티팩트 6종(spec/plan/acceptance/design/research/progress) 동시 생성. 안전 경계를 **완화**하는 SPEC이므로 false-negative 검토(design.md §4)를 문서의 중심에 둔다. |
| 0.2.0 | 2026-07-23 | manager-spec | 라이브 프로브 실행(`.moai/state/verify/showui-m6-resume/5-probe-body.log`) — Q1 예(로컬-인덱스 단서)/Q2 결정적 아니오(자식 없음, childCount 0 4/4)/Q3 아니오(기존 갭 재확인). 사용자 결정(AskUserQuestion, 2026-07-23): S2 완전 이연, S1만 출하. REQ-EXECREF-004/005/006을 DEFERRED로 표기(철회 아님). 후속 SPEC `SPEC-COPILOT-EXECBODY-001` 권고(research.md §5.3, 미생성). design.md §5 해소, plan.md M2 DESCOPED, acceptance.md AC-EXECREF-013 갱신. |

## A. 개요

패널 익스큐터 타일을 한 번 누를 때마다 **승인 카드 1장 + 쇼파일 저장 1회**가 발생한다. 본 SPEC은 그 원인인 "게이트가 `Executor`를 해석 가능한 참조 타입으로 인정하지 않는다"는 점을 교정해, 해석 가능한 익스큐터 타일이 승인 없이 single-press로 발화하도록 만든다.

### 결함 연쇄 (전부 코드 실측, 재도출 불요)

1. `Go`/`Go+`/`Go-`는 `server/safety/blacklist.yaml:22-25`의 `invoking_verbs`에 있다(`Goto`/`On`/`Off`/`Toggle`/`Temp`/`Flash`/`Call`과 함께). invoking 커맨드는 expand-or-hold(REQ-MVP-026) 대상 — 타깃 본문을 조회해 분류한다.
2. `server/safety/classify.py:33` — `RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence")`. **`Executor`가 없다.** 따라서 `_extract_reference`(classify.py:117-125)는 `Go+ Executor 191`에 대해 `None`을 반환한다.
3. `server/safety/expand.py:82-83` — `reference is None` → `_hold("unverifiable reference: no recognizable target object")` → 번들이 사람 승인으로 보류된다.
4. 승인 이후 위험-경로 백업이 돈다 — `BACKUP_COMMAND = "SaveShow"`(gate.py:59)를 `_backup.before_risky_execution()`(gate.py:326-329)이 발화한다.

> **정밀 관찰 (design.md §4.7)**: gate.py:325-329의 백업 블록은 `if held:` 안에 있다. 주석은 "only the RISKY path backs up"이라 쓰여 있으나 실제 조건은 **보류(held)** 이지 `risky` 플래그가 아니다. 즉 `SaveShow`는 익스큐터 참조가 **위험하다고 분류되어서**가 아니라 **보류되었기 때문에** 발화한다. 결과적으로 보류를 제거하면 승인 카드와 `SaveShow`가 **한 번에** 사라진다.

SPEC-COPILOT-SHOWUI-001 M3에서 실제 UDP 트랜스포트로 실측: 익스큐터 타일 1회 누름 → `exec_commands == ["SaveShow", "Go+ Executor 201"]`. 반면 `Go+ Sequence 41`은 참조가 해석되어 승인 없이 통과한다 — **같은 패널 안에 마찰이 다른 두 타일 클래스가 공존한다.**

### 왜 문제인가

- `SPEC-COPILOT-SHOWUI-001/design.md` §5는 "일반 타일은 single-press"를 약속한다.
- 같은 SPEC의 `spec.md` §A는 광역 타깃 커맨드를 금지하는 근거로 "쇼 진행 중 블랙아웃 순간에 승인 카드가 뜨는 사고를 원천 배제"를 든다.

평범한 타일 누름마다 승인 카드와 쇼파일 저장이 발생하면 두 약속이 모두 무너진다.

### 이 SPEC이 완화하는 것과 완화하지 않는 것

완화되는 것은 정확히 하나다 — **해석 가능한 익스큐터는 해석된다.** 완화되지 않는 것: 해석 불가능한 익스큐터는 여전히 보류된다. 본문에 블랙리스트 커맨드가 있으면 여전히 보류된다. 깊이 상한·순환 탐지·본문 조회 실패·파싱 불가 라인은 전부 그대로 작동한다(design.md §4가 각각을 증명한다).

### ⚠️ v0.2.0 정직성 고지 — 마찰 제거 목표는 이번 버전에서 달성되지 않는다

2026-07-23 라이브 프로브(`.moai/state/verify/showui-m6-resume/5-probe-body.log`) 결과, 익스큐터 노드는 자식을 노출하지 않는다(Q2 결정적 아니오 — design.md §5.1/§5.2). 이는 익스큐터 본문 해석(S2)이 `server/safety/**` 범위 안에서 어떤 실질적 효과도 낼 수 없음을 뜻한다. **이번 버전이 출하하는 것은 인식측 완화(S1)뿐이다** — 분류기가 `Executor`를 인식 가능한 참조 타입으로 인정하게 되어, 보류 사유가 더 정확해지고(`"unverifiable reference: no recognizable target object"` → `"no body path mapping for 'Executor N'"`) 후속 작업의 토대가 마련된다. **평범한 익스큐터 타일의 single-press 마찰 제거라는 원래 목표는 이번 버전에서 달성되지 않는다** — `hold=True, risky=False`가 그대로 유지되어, 승인 카드 1장과 `SaveShow` 1회가 여전히 매 누름마다 발생한다. 이는 부분 성공을 성공으로 위장하지 않는다는 design.md AP-8 원칙에 따른 정직한 보고다. S2를 실제로 구현하려면 `console/lua/copilot_responder.lua` 확장(응답기가 익스큐터의 할당 시퀀스 아이덴티티를 노출)이 필요하며, 이는 본 SPEC의 범위(`server/safety/**` 한정) 밖이다 — 후속 SPEC `SPEC-COPILOT-EXECBODY-001`로 권고한다(research.md §5.3).

### ⚠️ 정직성 고지 — cue CMD 갭 (본 SPEC이 닫지 않는 기존 갭)

`server/safety/console.py:414-432`의 `StateBodyFetcher.fetch_body`는 `payload["children"][*]["name"]`으로 본문 라인을 구성한다. 응답기는 자식당 `{name, class, i}`만 반환한다(`console/lua/copilot_responder.lua:456`). 따라서 Sequence 참조의 "본문 라인"은 **큐의 이름이지 큐의 커맨드가 아니다.** `Blackout`이라는 이름의 큐는 스크리닝되지만, CMD 프로퍼티가 `Delete Sequence 5`인 큐는 게이트에 보이지 않는다 — 응답기가 그 필드를 전송한 적이 없기 때문이다.

즉 **`Go+ Sequence 41`이 오늘 통과하는 이유는 게이트가 큐를 검증해서가 아니라 큐 이름이 우연히 무해한 문자열이기 때문이다.** expand-or-hold는 **어떤 참조 타입에 대해서도** 큐 커맨드 프로퍼티를 스크리닝한 적이 없다. `DEFAULT_BODY_PATHS`의 독스트링(console.py:391-395)이 스스로를 `PLACEHOLDER assumption (onPC-unverified, M6 live calibration)`이라 표기한 것이 이 사실을 가린다.

본 SPEC은 이 갭을 **기록하되 닫지 않는다** (사용자 결정 — 범위를 `server/safety/**`로 유지; 갭 봉쇄는 응답기 Lua 변경 + 재배포 + 라이브 재검증이 필요). 본 SPEC이 지는 의무는 **동등성 증명이지 개선이 아니다**: Executor 추가가 cue-CMD 갭을 새로 만들지 않고 종류를 악화시키지 않음을 증명한다(design.md §4.2). 다만 **본문 조회에 도달하는 커맨드 집합은 넓어진다**(익스큐터 대상 invoking 커맨드는 이전에 무조건 보류되었다) — 이 확대는 명시되며 얼버무리지 않는다.

**게이트가 큐 커맨드를 스크리닝한다고 주장하지 않는다. 하지 않는다.**

## B. 요구사항 (GEARS)

### B.1 참조 인식 (classify 측)

- **REQ-EXECREF-001** [Ubiquitous] — The 분류기의 인식 참조 타입 집합(`RECOGNIZED_REFERENCE_TYPES`, classify.py:33) **shall** `Executor`를 포함한다. 이는 폐쇄 집합의 **의도적 개정**이며, blacklist.yaml의 폐쇄 집합 개정 규율(파일 개정 + 버전 범프)과 동일한 무게로 취급된다.
- **REQ-EXECREF-002** [Event-driven] — **When** invoking 동사(`invoking_verbs`, blacklist.yaml:22-33)를 가진 커맨드가 익스큐터를 타깃하면(`Go+ Executor 191` 형태), the 참조 추출기(`_extract_reference`, classify.py:117-125) **shall** `"Executor <no>"` 형태의 참조를 반환하며, `None`을 반환하지 않는다.
- **REQ-EXECREF-003** [Ubiquitous] — 분류 의미론 **shall** 단일하게 유지된다(`classify_command`, classify.py:158-161 `@MX:ANCHOR`). 제2 분류기·익스큐터 전용 매칭 경로 **shall not** 도입되지 않는다 — REQ-MVP-013/014의 FN=0은 하나의 매칭 의미론 위에 서 있다.

### B.2 본문 해석 (fetcher 측) — **[DEFERRED, v0.2.0]** S2 미출하로 REQ-EXECREF-004/005/006은 이연됨 (철회 아님 — 유효한 미래 요구사항, 근거: design.md §5, 후속 SPEC `SPEC-COPILOT-EXECBODY-001` 권고, research.md §5.3)

- **REQ-EXECREF-004** [Ubiquitous] **[DEFERRED]** — 익스큐터 본문 조회 **shall** 기존 게이트-감사 `state_port` seam을 경유한다(`_GateStatePort`, gate.py:114-121; `bootstrap.py:162`에서 `StateBodyFetcher(query=lambda path: gate.state_port.query_state(path))`로 배선). `get_rig_context`와 `build_catalog`가 쓰는 것과 **같은** seam이다.
- **REQ-EXECREF-005** [Unwanted] **[DEFERRED]** — 본문 해석 **shall not** 신규 콘솔 경로·신규 OSC 표면·`server/bridge/osc.py`의 직접 import를 도입한다. `server/safety/**`의 OSC import 경계 grep 결과는 무변경이어야 한다.
- **REQ-EXECREF-006** [Ubiquitous] **[DEFERRED]** — 본문 경로 해석 메커니즘 **shall** 익스큐터가 요구하는 경로 형상을 표현할 수 있어야 한다. 현재의 `{type_word: "path/{ref}"}` 템플릿(console.py:396-400, 414-418)은 페이지 성분을 요구하는 경로를 표현하지 못하므로, fetcher의 형상 자체가 변경될 수 있다 — 단 기존 `Macro`/`Plugin`/`Sequence` 3종의 해석 결과는 회귀 없이 보존된다.
- **REQ-EXECREF-007** [Unwanted] — 익스큐터 참조 해석 **shall not** 익스큐터의 표시 이름(`name`)에서 할당 시퀀스를 파싱하는 방식으로 구현되지 않는다. MA3 익스큐터의 표시 이름은 할당된 시퀀스의 이름이며, 시퀀스를 "Cyan Look"으로 rename하면 그 문자열은 더 이상 `Sequence 71`을 말하지 않는다 — 이름 파싱은 기각된 대안 (b)의 다른 얼굴이다(research.md §2).

### B.3 Fail-closed 보존 (완화의 경계)

- **REQ-EXECREF-008** [Event-driven] — **When** 익스큐터 본문이 해석 불가능한 상태(시퀀스 미할당·빈 본문·본문 조회 실패·상태 질의 타임아웃)로 감지되면, the 게이트 **shall** 해당 참조를 보류한다(`_hold`). 완화의 범위는 "해석 가능한 익스큐터가 해석된다"이지, "해석 불가능한 익스큐터가 통과한다"가 **결코** 아니다.
- **REQ-EXECREF-009** [Ubiquitous] — 익스큐터 참조 **shall** 기존 expand-or-hold 기계의 모든 보류 사유를 참조-타입-무관하게 상속한다: 재귀 상한(`MAX_EXPANSION_DEPTH = 3`, expand.py:87-88), 순환 탐지(expand.py:85-86), 블랙리스트 본문 보류(expand.py:110-112), 본문 부재 보류(expand.py:101-104), 파싱 불가 라인 보류(expand.py:107-109). 신규 경로 **shall not** 이 중 어느 것도 우회한다.
- **REQ-EXECREF-010** [Ubiquitous] — 스크리닝 경로 **shall** 정확히 하나만 존재한다(`SafetyGate.screen`, gate.py:260-264 `@MX:ANCHOR`). 패널 전용 룰셋·"패널 커맨드는 expansion을 건너뛴다" 류의 지름길 **shall not** 도입되지 않는다 — 그것은 이름만 다른 제2 스크리닝이며 SPEC-COPILOT-SHOWUI-001 REQ-SHOWUI-007이 정확히 이를 막기 위해 존재한다.

### B.4 폐쇄 집합 규율

- **REQ-EXECREF-011** [Ubiquitous] — FN 코퍼스(`server/tests/test_safety_corpus.py`) **shall** 참조 타입 축을 폐쇄 집합에서 **동적으로 순회**하여 신규 참조 타입이 자동 확장되게 한다. 하드코딩된 `Executor` 케이스 추가 **shall not** 사용된다.

  > 정정 근거: 현재 `_invoking_commands()`(test_safety_corpus.py:86-92)는 **동사 축만** 동적으로 순회하고 참조 타입은 `f"{verb} Macro 9"`로 **하드코딩**한다. `_SCENARIOS`(test_safety_corpus.py:95-110)의 본문 키도 `"Macro 9"`/`"Plugin 9"` 고정이다. 따라서 `Executor` 추가는 자동 확장되지 **않으며**, 참조-타입 축의 동적 순회는 본 SPEC이 새로 만들어야 하는 것이다(design.md §6).

- **REQ-EXECREF-012** [Unwanted] — 본 SPEC **shall not** 게이트가 큐의 CMD(Command) 프로퍼티를 스크리닝한다고 주장하거나 암시한다. cue-CMD 갭(§A)은 `@MX:DEBT`로 코드에 기록되고(`@MX:CEILING`/`@MX:UPGRADE` 하위 라인 동반, plan.md §D) 후속 SPEC 권고로 research.md에 남는다.

### B.5 관측 가능한 결과

- **REQ-EXECREF-013** [Event-driven] **[DEFERRED]** — **When** 해석 가능하고 본문이 양성인 익스큐터를 대상으로 `Go+ Executor <no>`가 스크리닝되면, the 게이트 **shall** 승인 요청 0건·`SaveShow` 송신 0건으로 통과시키고, 콘솔 송신 기록은 정확히 `["Go+ Executor <no>"]`가 된다(SHOWUI M3 실측 형상 `["SaveShow", "Go+ Executor 201"]`의 교정). **S2 DESCOPE로 v0.2.0에서는 달성되지 않음** — 철회 아님, 유효한 미래 요구사항. 근거: design.md §5. 후속 SPEC `SPEC-COPILOT-EXECBODY-001` 권고(research.md §5.3).
- **REQ-EXECREF-014** [State-driven] — **While** 익스큐터 참조 인식이 도입된 상태에서도, the 게이트 **shall** 기존 안전 불변식 전부를 무변경 유지한다: health gate, 문법 검증, 위험 분류, LiveLock(lock-FIRST 재확인 포함), deny-all 기본 승인 포트, 위험 커맨드 사전 쇼파일 백업 fail-closed, 미확인 이력 재승인·자동 재전송 금지.

### B.6 범위 경계의 명시적 선언

- **REQ-EXECREF-015** [Unwanted] — `Go+ Page <page>.<executor>` 형태(익스큐터를 발화하는 제2 구문, 룰북 `10_object_model.md:23-25`) **shall not** 본 SPEC에서 해석 대상이 되지 않는다. 결과적으로 이 형태는 계속 `reference=None` → 보류로 귀결되며, 이는 **fail-closed 방향이므로 안전하다** — 과다 차단이지 우회가 아니다. 패널은 이 형태를 만들지 않지만(SHOWUI M3가 번들 형상을 `Go+ Executor N`으로 동결) LLM이 채팅에서 작성할 수 있으므로, 침묵으로 생략하지 않고 명시적으로 선언한다.

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 동일 머신 로컬 공존. OSC는 `127.0.0.1` UDP. site config(`osc_slot`, `receive_port`, `reply_port`)는 항상 effective 값에서 읽는다 — 하드코딩 금지.
- **기능 전제**: SPEC-COPILOT-MVP-001의 안전 게이트 파이프라인(3-stage screen, expand-or-hold, LiveLock, 백업, 감사)과 SPEC-COPILOT-SHOWUI-001의 패널 M1~M3(프로토콜·스토어·게이트 경유 실행)는 구현·검증 완료 상태다. 두 SPEC 모두 frontmatter `status`가 `completed`가 아니므로 `depends_on`이 아닌 `related_specs`로 참조한다 — 엄격 충족 전제의 pre-flight 차단을 피하기 위함(SHOWUI-001 §C의 동일 관례 계승).
- **기술 스택**: 기존 스택 그대로. **신규 런타임 의존성 0.**
- **콘솔측**: `console/lua/copilot_responder.lua` 무변경. 와이어 프로토콜 무변경(`PROTOCOL_VERSION` 불변).
- **미검증 전제 (ASSUMPTION 규율)**: 익스큐터 본문 해석 경로의 오브젝트-트리 형상은 아직 라이브 실측되지 않았다. `ASSUMPTION-8`(익스큐터 노드 경로), `ASSUMPTION-9`(익스큐터 자식 = 할당 시퀀스의 큐)로 번호를 부여하고 design.md §5에서 각각의 검증 질문과 결과별 함의를 기술한다. `console/lua/PROTOCOL.md` §6의 ASSUMPTION-1~7 다음 번호이며, 라이브 확정 시 비준 기록은 progress.md §E.2에 남긴다(PROTOCOL.md §6 등재는 본 SPEC 범위 밖 — plan.md §F 참조).
- **측정된 기준선**: HEAD `0576553`에서 스위트는 **1591 passed + 1 failed**. 유일한 실패는 `server/tests/test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`이며 **환경적**이다 — 구동 중인 onPC가 UDP 9005를 점유하고 있고 그 포트가 해당 테스트의 후보 집합에 있다. **기존 실패이며 본 SPEC과 무관하다.** run-phase 에이전트가 자신이 유발한 회귀로 오인하지 않도록 여기에 기록한다.

## D. 제외 범위 (Out of Scope)

### Out of Scope — 콘솔측 Lua 및 와이어 프로토콜

- `console/lua/copilot_responder.lua` 변경 일체, 응답기 재배포, 와이어 프로토콜 변경. **사용자 결정**: 본 SPEC은 `server/safety/**`에 머문다.
- 따라서 cue-CMD 갭(§A) 봉쇄도 제외 — 기록만 하고 닫지 않는다.

### Out of Scope — 제2 스크리닝 진입점

- 패널 전용 룰셋, "패널 커맨드는 expansion을 건너뛴다" 류의 좁은 carve-out, 제2 분류기, 실행용 REST 엔드포인트. gate.py:260-264 + classify.py:158-161 두 `@MX:ANCHOR`가 금지한다.

### Out of Scope — `Go+ Page <page>.<executor>` 구문

- 익스큐터 발화의 제2 구문은 해석 대상이 아니다(REQ-EXECREF-015). 계속 보류되며 이는 fail-closed로 안전하다. 필요해지면 후속 SPEC.

### Out of Scope — UI 및 페이더/엔코더 표면

- `server/web/**`, `ui/src/**` 변경 없음. 페이더·엔코더 등 연속 파라미터 표면은 SPEC-COPILOT-SHOWUI-001 §D에서 이미 이연된 상태 그대로 유지.

### Out of Scope — 다른 미인식 참조 타입의 일괄 추가

- `Group`, `Preset`, `World`, `MAtricks` 등 여타 오브젝트 타입의 참조 인식. 각각 고유한 본문 의미론을 가지며 개별 false-negative 검토를 요구한다. 본 SPEC은 `Executor` 하나만 다룬다.

### Out of Scope — 큐 커맨드 프로퍼티 스크리닝

- 큐의 CMD/Command 프로퍼티를 게이트가 읽고 분류하는 기능. 응답기 변경이 선행 조건이므로 구조적으로 본 SPEC 범위 밖이며, research.md §5에 후속 SPEC 권고로 명명된다.

## E. 참조 구현 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 복제 원본 (file:line) |
|---|---|
| 인식 참조 타입 폐쇄 집합 | `RECOGNIZED_REFERENCE_TYPES`(classify.py:33) + 주입 지점 `classify_command(..., reference_types=...)`(classify.py:162-167) |
| 참조 추출 의미론 | `_extract_reference`(classify.py:117-125) — 인용되지 않은 토큰만, 타입 워드 다음 토큰이 참조 번호 |
| 본문 경로 템플릿 + fetcher 계약 | `DEFAULT_BODY_PATHS`(console.py:396-400), `StateBodyFetcher.fetch_body`(console.py:414-432) |
| 게이트-감사 상태 조회 seam | `_GateStatePort`(gate.py:114-121), 배선(bootstrap.py:162) |
| 참조-타입-무관 보류 기계 | `_evaluate`(expand.py:72-125) — 깊이 87-88, 순환 85-86, 본문 부재 101-104, 파싱 불가 107-109, 블랙리스트 본문 110-112 |
| 폐쇄 집합 동적 순회 코퍼스 | `TestBlacklistFnCorpus`(test_safety_corpus.py:54-84), `_invoking_commands`(86-92), `_SCENARIOS`(95-110) — 동사 축은 동적, 참조 타입 축은 하드코딩(REQ-EXECREF-011이 교정 대상) |
| import 경계 기계 검증 | `server/tests/test_architecture.py` |
| 페이지→익스큐터 드릴다운 경로 조합 | `server/orchestrator/tools.py:264` — `f"{base_path}/{number}"` 조합, 실제 `no` 키잉 |
| 익스큐터 주소 규약 | 룰북 `server/rulebook/assets/v2.4.2/10_object_model.md:23-25` — `Page <page>.<executor>` |
| 재생 동사 | 룰북 `31_choreography_patterns.md` "Playback"(`Go+ Executor N` / `Off Executor N`) |
