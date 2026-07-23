# SPEC-COPILOT-EXECBODY-001 — 인수 기준 (acceptance)

status: draft (v0.1.0, 2026-07-23) · Tier L · 본 문서는 spec.md의 요구를 관측 가능한 검증 기준으로 전개한다.

## §A. 개요

본 SPEC의 성공 기준은 두 층위로 나뉜다:

1. **필수(전 마일스톤 공통)** — 역주소 문제가 정직하게 해소되거나 DESCOPE되며, 어떤 경우에도 fail-closed가 훼손되지 않는다.
2. **조건부(M1 GO 결정 시에만)** — 익스큐터 타일 1회 누름의 실제 마찰(승인 카드·`SaveShow`)이 실측으로 제거된다.

EXECREF-001의 교훈(design.md AP-8)을 계승한다: **부분 성공을 성공으로 위장하지 않는다.** M1이 DESCOPE로 귀결되면 아래 §B 시나리오 1은 달성되지 않으며, 그 사실이 §C의 해당 AC와 §F DoD에 정직하게 반영되어야 한다.

## §B. Given-When-Then 시나리오 (최소 2개)

### 시나리오 1 — 해석 가능·양성 익스큐터의 single-press 통과 (조건부: M1 GO)

- **Given** 익스큐터 아이덴티티 노출 메커니즘(M1~M4)이 구현·배포되어 있고, 대상 익스큐터에 시퀀스가 할당되어 있으며 그 시퀀스의 모든 큐 이름이 블랙리스트에 매치하지 않는다(양성 본문).
- **When** 패널 또는 채팅이 `Go+ Executor <no>`를 스크리닝을 위해 게이트에 제출한다.
- **Then** 게이트는 승인 요청 0건·`SaveShow` 송신 0건으로 통과시키며, 콘솔 송신 기록은 정확히 `["Go+ Executor <no>"]`이다(REQ-EXECBODY-013).
- **주의**: 이 시나리오는 M1이 회피 경로(ASSUMPTION-10) 또는 검증된 관례(ASSUMPTION-11)를 확보한 경우에만 실물 콘솔에서 실측 가능하다. M1이 DESCOPE되면 이 시나리오는 "달성되지 않음"으로 정직하게 기록한다(AC-EXECBODY-013 참조).

### 시나리오 2 — 미할당/미해석 익스큐터는 여전히 보류 (fail-closed, 무조건)

- **Given** 대상 익스큐터에 시퀀스가 할당되어 있지 않거나, 아이덴티티 조회 자체가 실패한다(상태 질의 타임아웃 포함).
- **When** `Go+ Executor <no>`가 게이트에 제출된다.
- **Then** 게이트는 해당 참조를 보류한다(`_hold`) — 승인 카드가 뜨고 `SaveShow`가 발화한다. 이 동작은 M1의 결과와 무관하게 항상 성립해야 한다(REQ-EXECBODY-006).

### 시나리오 3 — 블랙리스트 큐를 포함하는 익스큐터는 계속 차단 (안전 경계 무변경)

- **Given** 익스큐터에 할당된 시퀀스의 큐 중 하나의 이름이 블랙리스트 커맨드에 매치한다.
- **When** `Go+ Executor <no>`가 게이트에 제출된다.
- **Then** 게이트는 위험으로 분류해 보류한다 — 아이덴티티 노출 메커니즘이 이 방어를 우회하지 않는다(REQ-EXECBODY-011).

### 시나리오 4 — 역주소 문제 미해소 시 정직한 DESCOPE (M1 게이트가 부정으로 답한 경우)

- **Given** M1 조사 결과 회피 경로(ASSUMPTION-10)가 존재하지 않고, 다중-페이지 검증(ASSUMPTION-11)도 실패했거나 수행 불가능하다.
- **When** run-phase가 M1 완료 시점에 도달한다.
- **Then** M2 이후 마일스톤은 착수되지 않으며, spec.md의 관련 요구사항은 `[DEFERRED]`로 재표기되고(manager-spec 재위임 필요), progress.md에 조사 결과와 근거가 기록된다 — "본문 해석은 여전히 불가능하다"는 결론이 실패가 아니라 정직한 조사 결과로 보고된다(REQ-EXECBODY-010).

## §C. AC (GEARS 형식 — 검증 레시피는 각 AC 하위 상세로 보존)

각 AC는 GEARS 패턴 문장으로 시작하고, run-phase에서 실제 커맨드로 구체화할 검증 방법과 기대 결과를 하위 상세로 보존한다(EXECREF-001·SHOWUI-001의 구체적 검증-커맨드 관례는 하위 상세 형태로 유지).

### AC-EXECBODY-001 — 콘솔 네이티브 주소 해석 API 존재 여부 조사

**When** M1 조사가 grandMA3 Lua API 문서·룰북 및 실물 콘솔 접근을 통해 콘솔 네이티브 주소 해석 경로의 존재 여부를 확인하면, the M1 조사 **shall** 그 존재/부재를 근거와 함께 design.md §5에 명시적 결론으로 남긴다.

- 대상 요구사항: REQ-EXECBODY-009 / ASSUMPTION-10
- 검증 방법: M1 조사 로그 + grandMA3 Lua API 문서/룰북 인용
- 기대 결과: 존재/부재가 근거와 함께 design.md §5에 명시적으로 결론 남음(모호한 "아마도" 금지)

### AC-EXECBODY-002 — 오프셋(또는 등가 관례)의 다중-페이지 검증

**When** 오프셋(또는 등가 관례) 검증이 최소 2개의 서로 다른 페이지에서 읽기 전용 라이브 프로브로 실행되면, the 검증 **shall** 관례의 성립/불성립 여부를 페이지별로 명시적으로 기록한다.

- 대상 요구사항: REQ-EXECBODY-008 / ASSUMPTION-11
- 검증 방법: 읽기 전용 라이브 프로브를 최소 2개의 서로 다른 페이지에서 실행, 로그 저장
- 기대 결과: 관례가 성립/불성립 여부가 페이지별로 명시적으로 기록됨. ASSUMPTION-10이 확인되면 이 AC는 moot로 표기 가능(EXECREF-001 §5.3 선례)

### AC-EXECBODY-003 — 익스큐터→시퀀스 프로퍼티 접근성

**When** 익스큐터→시퀀스 프로퍼티 접근성 조사가 읽기 전용 라이브 프로브(state 동사)로 실행되면, the 조사 **shall** 익스큐터 핸들에서 할당 시퀀스 아이덴티티를 얻는 구체적 접근자(프로퍼티명 또는 API 호출)를 실측으로 확인한다.

- 대상 요구사항: REQ-EXECBODY-001 / ASSUMPTION-12 (정정: 이전 초안의 "REQ-EXECBODY-012" 인용은 오기 — ASSUMPTION-12는 REQ-EXECBODY-001이 요구하는 아이덴티티 노출의 전제이므로 REQ-EXECBODY-001과 연결된다. REQ-EXECBODY-012는 분류/스크리닝 단일성과 무관한 별개 요구사항이다)
- 검증 방법: 읽기 전용 라이브 프로브(state 동사)
- 기대 결과: 익스큐터 핸들에서 할당 시퀀스 아이덴티티를 얻는 구체적 접근자(프로퍼티명 또는 API 호출)가 실측 확인됨

### AC-EXECBODY-004 — 응답기 확장, 가산적 스키마

**When** Lua 응답기 확장이 코드 리뷰 및 라이브 프로브로 검증되면, the 확장 **shall** 기존 `{name, class, i}` 소비자를 무변경으로 계속 동작시키며(회귀 없음) 신규 아이덴티티 필드가 관측되도록 한다.

- 대상 요구사항: REQ-EXECBODY-001 / REQ-EXECBODY-003
- 검증 방법: Lua 응답기 코드 리뷰 + 라이브 프로브로 신규 필드 존재 확인
- 기대 결과: 기존 `{name, class, i}` 소비자가 무변경으로 계속 동작(회귀 없음) + 신규 필드가 관측됨

### AC-EXECBODY-005 — 이름-파싱 금지

익스큐터-시퀀스 아이덴티티 도출 로직 **shall not** 익스큐터의 표시 이름(`name`) 프로퍼티를 파싱하는 방식을 사용한다.

- 대상 요구사항: REQ-EXECBODY-002
- 검증 방법: 코드 리뷰(정적) — 아이덴티티 도출 로직이 `name` 프로퍼티를 참조하지 않음을 확인
- 기대 결과: grep/리뷰 결과 `name` 기반 파싱 부재 확인

### AC-EXECBODY-006 — 게이트 진입점 배선, OSC 경계 무변경

**When** 게이트 진입점 배선과 OSC 경계 테스트가 실행되면, the 배선 **shall** 그린 상태를 유지하며 `server/safety/**`의 OSC import 경계는 기준선 대비 무변경이다.

- 대상 요구사항: REQ-EXECBODY-004 / REQ-EXECBODY-005
- 검증 방법: `pytest server/tests/test_safety_console.py -q` + `grep -rn "bridge.osc\|from server.bridge" server/safety/`(기준선 대비 무변경)
- 기대 결과: 그린 + grep diff 없음

### AC-EXECBODY-007 — 아이덴티티 조회 실패 시 보류

**When** 할당-시퀀스 아이덴티티 조회가 실패하면(미할당/타임아웃/프로퍼티 부재), the 게이트 **shall** 해당 참조를 보류하며, 3종 실패 경로가 개별적으로 검증된다.

- 대상 요구사항: REQ-EXECBODY-006
- 검증 방법: `test_safety_console.py`의 실패-경로 케이스(미할당/타임아웃/프로퍼티 부재 3종 개별)
- 기대 결과: 3종 전부 개별 PASS — 병합 테스트 금지(EXECREF-001 design.md §6.2 원칙)

### AC-EXECBODY-008 — fail-closed 기계 전체 상속

**While** 익스큐터-경유 본문 해석 메커니즘이 활성 상태여도, the 게이트 **shall** 기존 fail-closed 보류 기계 전체(재귀 상한·순환 탐지·블랙리스트 본문·본문 부재·파싱 불가)를 무변경으로 상속한다.

- 대상 요구사항: REQ-EXECBODY-011
- 검증 방법: `pytest server/tests/test_safety_expand.py server/tests/test_safety_corpus.py -q`(익스큐터 시나리오 포함)
- 기대 결과: 전량 PASS

### AC-EXECBODY-009 — 단일 분류 의미론 + 단일 스크리닝 경로

게이트 **shall** 단일 분류 의미론과 단일 스크리닝 경로를 유지한다.

- 대상 요구사항: REQ-EXECBODY-012
- 검증 방법: `pytest server/tests/test_architecture.py -q` + `grep -c "^def classify_command" server/safety/classify.py`
- 기대 결과: 그린 + `classify_command` 정의 1개

### AC-EXECBODY-010 — 실제 single-press 마찰 제거 (LIVE, 조건부)

**When** 해석 가능하고 본문이 양성인 익스큐터를 대상으로 `Go+ Executor <no>`가 실물 콘솔에서 스크리닝되면, the 게이트 **shall** 승인 요청 0건·`SaveShow` 송신 0건으로 통과시키고 콘솔 송신 기록은 정확히 `["Go+ Executor <no>"]`가 된다(조건부: M1 GO).

- 대상 요구사항: REQ-EXECBODY-013 (LIVE, 조건부)
- 검증 방법: 실물 콘솔에서 익스큐터 타일 1회 누름, 송신 기록 관측
- 기대 결과: M1 GO인 경우: 승인 0·`SaveShow` 0·송신 `["Go+ Executor <no>"]`. M1 DESCOPE인 경우: **본 AC는 미달성으로 정직하게 기록**(§B 시나리오 4)

### AC-EXECBODY-011 — 기존 안전 불변식 전체 상속

**While** 본 SPEC의 익스큐터 아이덴티티 노출 메커니즘이 활성 상태여도, the 게이트 **shall** 기존 안전 불변식 전부(health gate, 문법 검증, 위험 분류, LiveLock, deny-all 기본 승인 포트, 위험 커맨드 사전 백업 fail-closed, 미확인 이력 재승인·자동 재전송 금지)를 무변경 유지한다.

- 대상 요구사항: REQ-EXECBODY-014
- 검증 방법: `pytest server/tests/test_safety_gate.py server/tests/test_web_panel_execute.py -q`
- 기대 결과: 전량 PASS

### AC-EXECBODY-012 — cue-CMD 갭 미확장 + CUECMD-001 미번들

본 SPEC **shall not** 게이트가 큐의 CMD 프로퍼티를 스크리닝한다고 주장·암시하거나 `SPEC-COPILOT-CUECMD-001`의 작업을 본 SPEC의 커밋 범위에 번들한다.

- 대상 요구사항: REQ-EXECBODY-015 / REQ-EXECBODY-016
- 검증 방법: 코드 리뷰 — `console.py` 본문 라인 구성이 여전히 `name` 기반임을 확인, PR/커밋 범위에 CUECMD 관련 파일 부재 확인
- 기대 결과: 확인 완료 — cue-CMD 갭 미확장 + CUECMD-001 미번들

### AC-EXECBODY-013 — `Go+ Page N.M` 구문 계속 보류 (regression)

**When** `Go+ Page <page>.<executor>` 구문이 게이트에 제출되면, the 게이트 **shall** 계속 해당 참조를 보류한다(regression, 무변경 상속).

- 대상 요구사항: REQ-EXECBODY-017
- 검증 방법: `test_safety_classify.py::TestInvokingDetection` 기존 케이스(무변경 상속)
- 기대 결과: `reference=None` → 보류 유지

### AC-EXECBODY-014 — 전체 회귀 (협상 불가)

전체 회귀 스위트 **shall** run-phase 킥오프 기준선 대비 신규 실패 0건을 유지한다.

- 대상 요구사항: 전체 회귀 (협상 불가)
- 검증 방법: `.venv/bin/python -m pytest -q`(run-phase 킥오프 기준선 대비)
- 기대 결과: 신규 실패 0건

### AC-EXECBODY-015 — 역주소 문제 정직한 처리

**When** M1이 DESCOPE로 귀결되면, the SPEC **shall** 그 결정 게이트와 근거를 progress.md §E.2에 각주가 아니라 명시적 섹션으로 기록한다.

- 대상 요구사항: REQ-EXECBODY-010 (§B 시나리오 4)
- 검증 방법: progress.md §E.2 기록 검토 — M1 결정 게이트와 그 근거가 명시적으로 남아 있는지 확인
- 기대 결과: GO/DESCOPE 여부와 근거가 각주가 아니라 명시적 섹션으로 존재

### AC-EXECBODY-016 — 오프셋 관례 무조건 하드코딩 금지 (NEW — REQ-EXECBODY-007 전담 AC)

익스큐터 아이덴티티 해석 코드 **shall not** 관측된 페이지 1의 +100 오프셋 관례를, 최소 2개 이상의 서로 다른 페이지에서 라이브로 검증되기 전에 일반 해석 규칙으로 하드코딩한다.

- 대상 요구사항: REQ-EXECBODY-007
- 검증 방법: 코드 리뷰(정적) — 오프셋 기반 해석 경로가 다중-페이지 검증 게이트(ASSUMPTION-11 확인 결과) 없이 무조건 적용되는 코드 경로가 존재하지 않음을 확인. AC-EXECBODY-002의 다중-페이지 검증 로그와 교차 확인.
- 기대 결과: grep/리뷰 결과 무조건 오프셋 하드코딩 경로 부재 확인 — 검증-게이트된 브랜치 내에서만 오프셋 사용 가능

## §D. Edge Cases

- **다중 시퀀스 재할당 도중(런타임 변경)**: 익스큐터의 시퀀스 할당이 스크리닝 도중 변경되는 레이스 컨디션 — 게이트는 조회 시점의 스냅샷을 사용하며, 이는 기존 `state_port` 조회 seam이 이미 갖는 일반적 계약(TOCTOU 완화는 본 SPEC 범위 밖, MVP-001 게이트 설계가 이미 다룬 영역).
- **페이지 미지정 익스큐터 번호 충돌**: 서로 다른 페이지에 동일한 콘솔-발화 번호를 가진 익스큐터가 존재할 가능성(오프셋 관례가 페이지마다 다르면 발생 가능) — M1이 이 가능성을 조사 대상에 포함해야 한다. 충돌이 해소 불가능하면 fail-closed(보류)가 안전한 기본값이다.
- **빈 시퀀스(큐 0개)**: 할당된 시퀀스에 큐가 하나도 없는 경우 — "본문이 있지만 비어 있음"과 "본문 자체가 없음"을 구분해야 하며, 전자는 양성 통과(빈 본문에 위험 커맨드가 있을 수 없음), 후자는 REQ-EXECBODY-006에 따라 보류. design.md에서 명시적으로 구분한다.
- **배포 왕복 실패**: M3에서 Import 후 신규 필드가 예상과 다른 형태로 관측되는 경우 — M2로 회귀하며 SPEC 실패로 집계하지 않는다(plan.md §B M3 참조).

## §E. Quality Gate 기준

- pytest 전체 스위트: run-phase 킥오프 시점 기준선 대비 신규 실패 0건.
- `ruff check`: 터치 파일 전용 clean(기존 baseline 위반은 본 SPEC 무관으로 별도 표기).
- `grep -rn 'AskUserQuestion\|mcp__askuser' server/safety/`: 0건(subagent boundary).
- `@MX:ANCHOR` 2종(`gate.py:260-264`, `classify.py:158-161`) 무변경 확인(신규 ANCHOR 추가 없음).
- 라이브 프로브 로그 전부 읽기 전용(발화 0·쓰기 0)임을 각 로그 자체에서 확인 가능해야 함(EXECREF-001 관례 계승).

## §F. Definition of Done

1. M1의 결정 게이트(회피/검증/DESCOPE)가 design.md §5와 progress.md §E.2에 명시적으로 기록되어 있다 — 결과가 부정적이어도 DoD를 충족한다(정직한 DESCOPE는 유효한 완료 상태).
2. M1이 GO로 귀결된 경우: M2~M6이 전부 완료되고, AC-EXECBODY-001~016 전부 PASS 또는 명시적으로 사유가 기록된 N/A다.
3. M1이 DESCOPE로 귀결된 경우: spec.md의 관련 REQ가 `[DEFERRED]`로 재표기되고(manager-spec 재위임 경유), AC-EXECBODY-010은 미달성으로 정직하게 기록되며, 나머지 AC(001~003, 013~016 등 M1 범위에 해당하는 것들)는 PASS다.
4. fail-closed 및 역주소-안전 관련 AC(007, 008, 009, 011, 013, 016)는 M1의 결과와 무관하게 항상 전량 PASS — 이는 협상 대상이 아니다.
5. `SPEC-COPILOT-CUECMD-001`이 본 SPEC의 커밋 범위에 등장하지 않는다(AC-EXECBODY-012).
