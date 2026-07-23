# SPEC-COPILOT-EXECREF-001 — 수용 기준 (acceptance)

status: draft (v0.2.0, 2026-07-23). 기계 검증 가능(pytest) 항목과 LIVE(실제 onPC) 항목을 구분한다. 본 SPEC은 **안전 경계를 완화**하므로, AC의 다수는 "완화되지 **않은** 것"을 증명하는 데 쓰인다. 2026-07-23 라이브 프로브 결과 S2는 DESCOPED되었다(plan.md M2) — AC-EXECREF-001/004/005/013이 이를 반영해 갱신되었다.

## §A. 완료 정의 (Definition of Done)

1. AC-EXECREF-001..012 + 014 + 015 전부 기계 검증 그린.
2. AC-EXECREF-013(LIVE)을 실제 onPC 2.4.2에서 수행·기록 (증적은 progress.md §E.2).
3. `test_architecture.py` 그린 + `server/safety/**` OSC import 경계 grep 기준선 대비 무변경.
4. design.md §5의 열린 슬롯이 2026-07-23 라이브 프로브 결과로 채워졌다 (plan.md §A.3) — 결과는 부정적이었다(Q2 결정적 아니오): M2는 착수 없이 DESCOPED되었다(plan.md M2). 슬롯은 닫혔으나 S2는 출하되지 않는다.
5. ASSUMPTION-8(확인됨 TRUE, 로컬-인덱스 단서 있음) / ASSUMPTION-9(반증됨 FALSE, 자식 없음)의 검증 결과가 progress.md §E.2 및 design.md §5.5에 기록됨.
6. 신규 런타임 의존성 0 유지.

## §B. Given-When-Then 시나리오

### 시나리오 1 — 해석 가능·양성 익스큐터 (REQ-EXECREF-001/002/004/013)

- **Given** 콘솔 online, 익스큐터 201에 무해한 시퀀스가 할당되어 있다.
- **When** `Go+ Executor 201`이 `gate.screen()`에 들어온다.
- **Then** 참조가 `"Executor 201"`로 추출되고, 본문이 게이트-감사 `state_port` 경유로 조회되며, 본문 라인이 전부 무해로 분류되어 **승인 요청 0건**으로 통과한다.
- **And** 기록된 콘솔 송신은 정확히 `["Go+ Executor 201"]`이다 — `"SaveShow"`가 **없다**.
- **주의(2026-07-23)**: REQ-EXECREF-013은 S2 DESCOPE로 `[DEFERRED]` 상태다(plan.md M2, spec.md §B.5) — 본 시나리오는 인메모리 fetcher로 본문 조회가 성공한다고 가정한 기계 증명이며, 프로덕션에서 실제로 도달 가능한 friction-elimination 경로임을 증명하지 않는다(AC-EXECREF-001 주의와 동일한 성격).

### 시나리오 2 — 본문에 블랙리스트 커맨드 (REQ-EXECREF-009)

- **Given** 익스큐터 201의 본문 라인 중 하나가 블랙리스트 커맨드로 파싱된다.
- **When** `Go+ Executor 201`이 스크리닝된다.
- **Then** 번들이 보류되고 `risky=True`이며, 승인 전 콘솔 송신은 0건이다(deny-all 승인 포트 하에서 `console.executed == []`).

### 시나리오 3 — 해석 불가 익스큐터 (REQ-EXECREF-008)

- **Given** 익스큐터 201에 시퀀스가 할당되지 않아 본문이 비어 있다.
- **When** `Go+ Executor 201`이 스크리닝된다.
- **Then** 보류된다 — 즉 **오늘의 동작이 유지된다.** 빈 본문이 "위험 없음"으로 해석되지 않는다.
- **And** 조회 실패·타임아웃·파싱 불가 라인 각각도 동일하게 보류된다(각기 다른 코드 경로).

### 시나리오 4 — 익스큐터 재귀 (REQ-EXECREF-009)

- **Given** 익스큐터 201의 본문이 `Go+ Executor 202`를, 202의 본문이 `Go+ Executor 201`을 담는다.
- **When** `Go+ Executor 201`이 스크리닝된다.
- **Then** 순환 탐지로 보류된다.
- **And** 깊이 4 이상의 익스큐터 체인은 `MAX_EXPANSION_DEPTH = 3` 상한으로 보류된다.

### 시나리오 5 — M1 단독 무행동 변화 (design.md §2.1)

- **Given** M1만 적용된 상태(참조 인식 O, 본문 경로 X).
- **When** `Go+ Executor 201`이 스크리닝된다.
- **Then** 여전히 보류되며 `hold=True, risky=False`가 유지된다 — 보류 사유 문자열만 `"no recognizable target object"`에서 본문 부재 사유로 바뀐다.

### 시나리오 6 — 범위 밖 구문의 fail-closed (REQ-EXECREF-015)

- **Given** LLM이 채팅에서 `Go+ Page 1.101`을 작성한다.
- **When** 스크리닝된다.
- **Then** 참조가 해석되지 않아 보류된다 — 과다 차단이며 우회가 아니다.

## §C. 검증 방법 (AC 표)

| AC | 검증 대상 | 방법 / 증거 (제안 커맨드) |
|---|---|---|
| **AC-EXECREF-001** | REQ-001/002/004/013 — 해석 가능·양성 익스큐터의 single-press 통과 | pytest(인메모리 fetcher + `FakeConsole` + deny-all 승인 포트): `Go+ Executor N`(무해 본문) → `decision.cleared is True`, `approval.requests == []`, **`console.executed == ["Go+ Executor N"]`** (`"SaveShow"` 부재를 명시 assert — SHOWUI M3 실측 `["SaveShow", "Go+ Executor 201"]`의 직접 교정). **주의(2026-07-23)**: 인메모리 fetcher로 본문 조회가 성공한다고 가정한 시나리오다. S2(실제 콘솔 fetcher 경로)는 DESCOPED되었으므로(plan.md M2, design.md §5) 이 AC는 게이트의 범용 스크리닝 기계가 `Executor` 참조 타입을 올바르게 처리함을 증명할 뿐 — 프로덕션에서 실제로 도달 가능한 경로임을 증명하지 않는다 |
| **AC-EXECREF-002** | REQ-009 — 블랙리스트 본문 보류 | pytest: 익스큐터 본문에 블랙리스트 커맨드 → `decision.cleared is False`, 보류 사유가 `risky=True`, 승인 전 `console.executed == []` |
| **AC-EXECREF-003a** | REQ-008 — 빈 본문(시퀀스 미할당) | pytest: `children == []` 또는 부재 → `BodyUnavailable`(console.py:423-425) → 보류. **003b/003c와 병합 금지** |
| **AC-EXECREF-003b** | REQ-008 — 조회 실패/타임아웃 | pytest: `query`가 예외/`StateQueryError` → `BodyUnavailable`(console.py:419-422) → 보류 |
| **AC-EXECREF-003c** | REQ-008 — 읽을 수 없는 본문 라인 | pytest: 자식에 `name` 부재 또는 공백 → `BodyUnavailable`(console.py:428-430) → 보류. 별개로, 파싱 불가 라인은 `grammar.ok is False` → `_hold`(expand.py:107-109) |
| **AC-EXECREF-004** | REQ-009 — 익스큐터→익스큐터 순환 | pytest: `Executor 201 → Executor 202 → Executor 201` 본문 사전 → 보류, 사유에 cycle 표기(expand.py:85-86). **주의(2026-07-23)**: 인메모리 본문 사전을 가정한 시나리오 — S2 DESCOPED로 프로덕션 도달 불가(위 AC-EXECREF-001 주의와 동일한 성격, plan.md M2) |
| **AC-EXECREF-005** | REQ-009 — 깊이 상한 | pytest: 익스큐터 4단 체인 → 보류, 사유에 depth 표기(expand.py:87-88). **주의(2026-07-23)**: 인메모리 본문 사전을 가정한 시나리오 — S2 DESCOPED로 프로덕션 도달 불가(위 AC-EXECREF-001 주의와 동일한 성격, plan.md M2) |
| **AC-EXECREF-006** | REQ-011 — 코퍼스의 참조 타입 축 동적 순회 | pytest: 코퍼스가 `classify.RECOGNIZED_REFERENCE_TYPES`를 import해 parametrize하며 `Executor` 케이스가 **자동** 생성됨. 기계 검증: 하드코딩된 `"Executor"` 리터럴이 코퍼스 파일에 없음 (`grep -c '"Executor"' server/tests/test_safety_corpus.py` → 0) **AND** 코퍼스 수집 케이스에 Executor 케이스가 존재 (`pytest --collect-only server/tests/test_safety_corpus.py -q \| grep -c Executor` → >0). 두 조건 동시 충족이 "하드코딩 추가가 아닌 집합 순회"의 이진 증거 |
| **AC-EXECREF-007** | REQ-003/005/010 — 단일 분류 의미론 + 단일 스크리닝 경로 + OSC 경계 | `.venv/bin/python -m pytest server/tests/test_architecture.py -q` 그린 **AND** `grep -rn "bridge.osc\|from server.bridge" server/safety/` 결과가 기준선과 동일(신규 매치 0) **AND** `grep -c "^def classify_command" server/safety/classify.py` → 1(REQ-003: 단일 진입점 유지, 제2 분류기·익스큐터 전용 매칭 경로가 `classify_command` 밖에 신설되지 않았음의 이진 증거) |
| **AC-EXECREF-008** | design.md §2.1 — M1 단독 무행동 변화 | pytest: 익스큐터 본문 경로 미주입 상태에서 `Go+ Executor N` → `hold=True`, `risky is False`. 게이트 관측 결과가 변경 전과 동일함을 assert(사유 문자열만 상이) |
| **AC-EXECREF-009** | REQ-014 — 회귀 (협상 불가) | `.venv/bin/python -m pytest server/tests/test_safety_gate.py server/tests/test_web_panel_execute.py -q` → 전량 그린 |
| **AC-EXECREF-010** | REQ-014 — 회귀 (협상 불가) | `.venv/bin/python -m pytest server/tests/test_safety_classify.py server/tests/test_safety_expand.py server/tests/test_safety_corpus.py server/tests/test_safety_ruleset.py server/tests/test_safety_console.py -q` → 전량 그린 |
| **AC-EXECREF-011** | REQ-015 — 범위 밖 구문 fail-closed | pytest: `Go+ Page 1.101` → 참조 미해석 → 보류. 이것이 **의도된 동작**임을 테스트 이름/독스트링에 명시 |
| **AC-EXECREF-012** | REQ-012 — cue-CMD 갭의 정직한 기록 | `grep -rn "@MX:DEBT" -A 2 server/safety/console.py` → DEBT 마커 존재 + `@MX:CEILING` + `@MX:UPGRADE` 하위 라인 동반. **음성 assert**: 코드/문서에 "게이트가 큐 커맨드를 스크리닝한다"는 취지의 서술 부재 |
| **AC-EXECREF-013** (LIVE) | ASSUMPTION-8/9 + S1 no-op 검증 | 라이브 체크리스트(실제 onPC 2.4.2): **① DONE (2026-07-23)** — 프로브 재실행으로 익스큐터 노드 경로와 자식 형상 확인 완료. 증거: `.moai/state/verify/showui-m6-resume/5-probe-body.log`; 비준 기록: progress.md §E.2. 결과: ASSUMPTION-8 확인됨(로컬-인덱스 단서 있음), ASSUMPTION-9 반증됨(자식 없음, `childCount: 0` 4/4 샘플). **② moot** (S2 DESCOPED — "해석한 익스큐터 번호 == 발화 오브젝트" 검증은 S2가 본문을 실제로 해석할 때만 의미가 있으나 S2는 이연됨). **③ DONE (2026-07-23, run-phase 사후 라이브 재검증)** — 실제 onPC(2.4.2, settings.toml 기준 console_port=8000/receive_port=9005) 대상, 패널이 아닌 조립 스크립트(`server.safety.bootstrap.build_console_stack()` — `server/web`과 동일 합성 루트) 경유로 `stack.gate.screen(["Go+ Executor 111"])` 1회 직접 호출(UI/패널 미경유 — 패널에 Executor 종 타일이 아직 없음, 복원은 본 SPEC 범위 밖 후속 항목). 결과: `cleared=False`(여전히 보류·차단, M1 이전과 동일 관측), `approval_request present=True`(승인 카드 생성, M1 이전과 동일 — 로그의 `status=rejected`는 스크립트 컨텍스트의 `approval_port=None`이 승인 대기 대신 자동 거절한 산물일 뿐이며, 실배포 환경에서 인간 승인자가 있으면 `pending` 상태가 되어 net effect는 동일: 승인 없이는 아무것도 발사되지 않음). 보류 사유 문자열은 구인식 `"unverifiable reference: no recognizable target object"`에서 신인식 `"unverifiable reference 'Executor 111': no body path mapping for 'Executor 111'"`로 확인 변경됨 — 참조가 이제 인식·추출됨(M1 동작)을 증명하면서도 본문-조회 경로 부재로 여전히 정확히 보류됨(S2 정확히 이연됨)을 동시에 증명(S1의 no-op 검증 — friction-elimination이 아님). 콘솔로 전송된 것 없음, 조명 리그 무변경. 증거: `.moai/state/verify/showui-m6-resume/6-live-executor-noop.log`. **④ 별도 라이브 테스트 미수행 — 동일 메커니즘으로 암묵 커버됨**: 가드는 `"no body path mapping"` 디스패치 단계에서 발동하며 MA3가 개별 익스큐터의 할당 상태를 확인하기도 전에 선행하므로, 미할당 익스큐터 타일도 별도 실측 없이 여전히 보류(fail-closed, 무변경)로 커버됨 |
| **AC-EXECREF-014** | REQ-014 — 전체 회귀 | `.venv/bin/python -m pytest -q` → 기준선(HEAD `0576553`: 1591 passed + 1 환경적 failed) 대비 **신규 실패 0건**. `test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`는 기존 환경적 실패이며 본 SPEC 무관(plan.md §C.6) |
| **AC-EXECREF-015** | REQ-007 — 이름 파싱 금지(rename 내성) | pytest: 익스큐터 202에 할당된 시퀀스의 `name`이 `'Sequence 71'`에서 `'Cyan Look'`으로 rename된 인메모리 fixture로 `Go+ Executor 202` 스크리닝 → 참조는 여전히 `"Executor 202"`로 추출되고 스크리닝 결과(hold/risky)가 rename 전후 동일함을 assert. `_extract_reference`가 `name` 필드를 읽지 않고 익스큐터 번호만으로 참조를 삼는다는 사실을 rename 전/후 동일 결과로 이진 증명(§D 엣지 케이스 2의 정식화) |

## §D. 엣지 케이스

1. **비연속 익스큐터 번호** — 프로브 실측상 `i` = 1, 5, 11, 91, 92, 93, 95, 101. 배열 인덱스 키잉 시 조용히 다른 오브젝트를 조회한다. `tools.py:164-168` "N번째 항목 ≠ 오브젝트 N" 계약 계승 — 회귀 픽스처로 방지.
2. **익스큐터 이름이 rename된 경우** — `name`이 `'Sequence 71'`에서 `'Cyan Look'`으로 바뀌어도 해석이 깨지지 않아야 한다(REQ-EXECREF-007). rename된 이름 픽스처로 검증.
3. **인용된 토큰** — `Go+ "Executor 201"`처럼 인용된 형태는 `_extract_reference`(classify.py:119-121)가 인용 토큰을 건너뛰므로 참조가 추출되지 않는다 → 보류. 기존 의미론 그대로이며 변경 대상 아님.
4. **익스큐터 본문이 중첩 매크로 호출을 담는 경우** — 재귀 `_evaluate`가 매크로 본문까지 내려간다. 단 큐 CMD가 와이어에 실리지 않으므로 이 경로는 큐 **이름**이 매크로 호출로 파싱될 때만 도달한다(design.md §4.3).
5. **동시 스크리닝** — clearance Counter는 세션-키드이고 `screen()`이 매 번들마다 리셋한다(gate.py:269-272). 본 SPEC은 이 의미론을 변경하지 않는다.
6. **LiveLock 활성 중** — 익스큐터 참조가 해석되어도 lock 검사가 선행하므로 콘솔 송신 0건·제안 전용. 기존 계약 무변경.
7. **health ≠ online** — health gate가 스크리닝 최전단에 있으므로 본 SPEC의 변경 이전에 차단된다. 무변경.
8. **`Macro`/`Plugin`/`Sequence` 해석 결과 회귀** — fetcher 형상이 바뀔 수 있으므로(REQ-EXECREF-006) 3종의 기존 해석 경로가 동일 결과를 내는지 회귀 테스트 필수.
9. **프로브가 ASSUMPTION-8/9를 반증하는 경우** — 익스큐터 본문이 구조적으로 해석 불가능하면 design.md §5.4 폴백(오늘의 동작 유지)으로 귀결된다. **이는 목표 미달이며 성공으로 보고하지 않는다**(design.md AP-8). SPEC을 부분 완료로 기록하고 대안(응답기 확장 병합)을 재검토한다.

## §E. 품질 게이트

- **Tested**: 신규/변경 코드 커버리지 프로젝트 기준(85%+) 충족. 스크리닝 경로 테스트는 전부 인메모리 fetcher 기반 결정론 — 테스트 안에 OSC 0.
- **Readable/Unified**: 기존 코드 스타일·네이밍 준수(ruff 통과). 안전 모듈의 기존 독스트링 톤 유지.
- **Secured**: 완화 방향이 fail-closed 경계를 넘지 않음을 AC-003a/003b/003c/004/005가 개별 증명. 단일 스크리닝 경로·단일 분류 의미론 유지(AC-007). cue-CMD 갭은 은폐하지 않고 `@MX:DEBT`로 기록(AC-012).
- **Trackable**: Conventional Commits + SPEC ID 참조(`feat(SPEC-COPILOT-EXECREF-001): …`). 폐쇄 집합 개정 사실을 커밋 본문에 명시.
