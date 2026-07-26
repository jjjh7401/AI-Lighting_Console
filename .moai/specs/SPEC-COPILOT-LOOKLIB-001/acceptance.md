# SPEC-COPILOT-LOOKLIB-001 — 인수 기준 (acceptance)

status: draft (v0.1.0, 2026-07-26) · Tier L · 본 문서는 spec.md의 요구를 관측 가능한 검증 기준으로 전개한다.

## §A. 개요

본 SPEC의 성공 기준은 세 층위다:

1. **데이터 계층** — 스키마·내장 라이브러리가 기계 검증 가능하게 완결되고 per-show 값이 없다.
2. **파이프라인 통합** — 역할 매핑·인스턴스화·매칭이 전부 기존 게이트/폴백/안전 불변식 위에서 동작하며, 실패 방향이 항상 축소/보류다.
3. **라이브 종단(1건)** — 실물 onPC에서 추상 한국어 지시 1회가 룩 매칭→인스턴스화까지 종단 완결된다(본 SPEC의 유일한 라이브 AC).

부분 성공은 부분 성공으로 보고한다: 역할 전멸 매핑·매칭 실패는 명시적 축소 출력이 정답이며(REQ-LOOKLIB-009/017), 이를 성공으로 위장하는 것이 실패다.

## §B. Given-When-Then 시나리오

### 시나리오 1 — 추상 무드 지시의 종단 적용 (행복 경로)

- **Given** 내장 라이브러리가 로드되어 있고, 리그에 역할 휴리스틱으로 매핑 가능한 이름의 그룹(예: 'FOH Wash'/'워시', 'Back'/'백라이트')이 존재한다.
- **When** 사용자가 채팅으로 "웅장한 금색 코러스로 가자"를 지시한다.
- **Then** 시스템은 워십/록 계열 클라이맥스 대역의 금색 룩을 매칭하고, 역할을 실존 그룹으로 바인딩해, `ChangeDestination Root`로 시작하고 Store 전후 `ClearAll`이 지켜지는 번들을 생성하며, 그 번들은 `gate.screen()`을 경유해 실행되고, 생성 오브젝트(프리셋 등)와 미매핑 역할이 요약 보고된다.

### 시나리오 2 — 역할 미매핑의 정직한 축소

- **Given** 리그의 그룹 이름이 역할 휴리스틱과 전혀 매칭되지 않는다(무명 그룹만 존재).
- **When** 룩 인스턴스화가 지시된다.
- **Then** 시스템은 해당 역할들을 명시적 미매핑으로 보고하고, 미매핑 역할에 대한 콘솔 커맨드를 생성하지 않으며, 임의 그룹 대입·하드 pan/tilt 합성·`Fixture` 범위 발명이 일어나지 않는다.

### 시나리오 3 — 매칭 실패 시 폴백 강등

- **Given** 채팅 지시가 라이브러리의 어떤 룩과도 신뢰할 만하게 매칭되지 않는다(예: "형광 보라 스트로브 지옥" — 라이브러리 외 무드).
- **When** 지시가 처리된다.
- **Then** 시스템은 기존 룰북 무드 폴백(31:173-206)으로 강등해 처리하며, 무관한 룩을 강제 매칭하지 않고, 폴백 경로의 기존 동작(rig 먼저 조회, 실존 그룹만)은 회귀 없이 유지된다.

### 시나리오 4 — 슬롯 충돌의 안전 방향

- **Given** 인스턴스화 대상 프리셋 슬롯이 이미 사용자 프리셋으로 점유되어 있다.
- **When** 룩 인스턴스화가 실행된다.
- **Then** 시스템은 기본 경로로 `Store /Overwrite`를 발화하지 않으며, 충돌 항목은 정책(plan.md §A.4 ④ 해소 결과)에 따라 스킵/재슬롯되고 그 사실이 요약 보고에 포함된다 — 사용자 프리셋은 명시적 승인 없이 파괴되지 않는다.

### 시나리오 5 — LiveLock 중 제안 강등

- **Given** LiveLock이 활성이다.
- **When** 룩 적용이 지시된다.
- **Then** 콘솔 송신은 0건이고 제안 카드만 생성된다(lock-FIRST 재확인 포함, 기존 게이트 동작 무변경).

## §C. AC (GEARS 형식 — 검증 레시피는 각 AC 하위 상세로 보존)

### AC-LOOKLIB-001 — 스키마 로딩 + 검증

**When** 내장 라이브러리가 로드되면, the 로더 **shall** 스키마 검증을 통과시키고, 주입된 위반 케이스(미지 역할/attribute, 다이내믹스 이탈, 중복 id)를 명시적 에러로 거부한다.

- 대상 요구사항: REQ-LOOKLIB-001 / REQ-LOOKLIB-005
- 검증 방법: `pytest server/tests/test_looks_schema.py -q` — 정상 로드 + 위반 케이스별 개별 거부 테스트
- 기대 결과: 전량 PASS, 위반 케이스는 병합 없이 개별 테스트

### AC-LOOKLIB-002 — 내장 라이브러리 커버리지

내장 라이브러리 **shall** 워십/록/발라드/EDM 4장르를 포함하고, 각 장르는 6~10개 룩을 가지며, 각 장르의 다이내믹스 레벨이 최소 저역(잔잔함 대역)과 최고역(클라이맥스 대역)을 모두 포함한다.

- 대상 요구사항: REQ-LOOKLIB-002
- 검증 방법: `pytest server/tests/test_looks_library.py -q` — 장르 수/장르당 룩 수/다이내믹스 스팬을 기계 assert
- 기대 결과: 4장르 × 6~10룩 × 스팬 조건 전부 기계 검증 PASS

### AC-LOOKLIB-003 — 검증된 attribute 어휘 한정

라이브러리의 모든 속성 페이로드 **shall** 허용 attribute 집합(룰북 31 검증 어휘) 내의 이름·값 범위만 사용한다.

- 대상 요구사항: REQ-LOOKLIB-003
- 검증 방법: 라이브러리 전수 순회 테스트 — 허용 집합 밖 attribute/범위 발견 시 실패
- 기대 결과: 위반 0건

### AC-LOOKLIB-004 — per-show 값 부재

룩 데이터 **shall not** 구체 그룹 번호/프리셋 슬롯/FID/익스큐터 번호를 포함한다.

- 대상 요구사항: REQ-LOOKLIB-004
- 검증 방법: 스키마 수준(리그 바인딩 필드 부재) + 자산 전수 테스트(수치 바인딩 필드 grep/파서 검증)
- 기대 결과: 스키마에 바인딩 필드 자체가 없고, 자산 검사 위반 0건

### AC-LOOKLIB-005 — 역할 매핑 리졸버

**When** 리졸버가 rig groups 데이터(fake)를 받으면, the 리졸버 **shall** 이름 휴리스틱으로 역할별 실존 그룹을 바인딩하고, 매핑 불가 역할을 명시적 미매핑으로 반환하며, `truncated`/`path_not_resolved`/`console_unreachable` 신호를 결과에 전파한다.

- 대상 요구사항: REQ-LOOKLIB-007 / REQ-LOOKLIB-009
- 검증 방법: `pytest server/tests/test_looks_resolver.py -q` — 한/영 관례 매핑, 미매핑, 신호 전파 3계열 개별 테스트
- 기대 결과: 전량 PASS — 미매핑 케이스에서 커맨드 대상이 생성되지 않음

### AC-LOOKLIB-006 — 슬롯≠FID + 그룹 발명 금지

the 리졸버·번들 빌더 **shall not** fixtures 번호 기반 `Fixture ... Thru ...` 범위를 합성하거나 rig 미등재 그룹 번호를 산출물에 포함한다.

- 대상 요구사항: REQ-LOOKLIB-008
- 검증 방법: 코드 리뷰(정적 — fixtures 섹션 소비 부재) + 번들 산출물 테스트(입력 rig에 없는 `Group <n>` 부재 assert)
- 기대 결과: fixtures 기반 범위 합성 경로 부재 + 미등재 그룹 0건

### AC-LOOKLIB-007 — 번들 프로그래밍 규율

생성된 인스턴스화 번들 **shall** 선두 `ChangeDestination Root` 1회, 각 룩 캡처 전과 각 `Store` 후 `ClearAll`, 생성 오브젝트별 `Label`을 포함하고, 기본 경로에서 `/Overwrite`를 포함하지 않는다.

- 대상 요구사항: REQ-LOOKLIB-011 / REQ-LOOKLIB-012
- 검증 방법: `pytest server/tests/test_looks_instantiate.py -q` — 번들 문자열 수준 불변식 assert(design.md §6.3)
- 기대 결과: 4개 불변식 전부 기계 PASS

### AC-LOOKLIB-008 — 단일 실행 경로 + 경계 무변경

룩 모듈 **shall** 기존 `run_commands → gate.screen()` 경로로만 실행을 흘리며, OSC/bridge 표면을 import하지 않는다.

- 대상 요구사항: REQ-LOOKLIB-010 / REQ-LOOKLIB-019
- 검증 방법: `pytest server/tests/test_architecture.py -q` + `grep -rn "bridge.osc\|from server.bridge" server/looks/`(0건) + `git diff --stat server/safety/`(빈 출력)
- 기대 결과: 그린 + grep 0건 + safety 무변경

### AC-LOOKLIB-009 — LiveLock 제안 강등

**While** LiveLock이 활성인 동안, 룩 적용 **shall** 콘솔 송신 0건 + 제안 전용으로 강등된다.

- 대상 요구사항: REQ-LOOKLIB-020
- 검증 방법: 기존 LiveLock 테스트 패턴 재사용 — 룩발 번들 시나리오 추가(`test_safety_gate.py` 계열)
- 기대 결과: 송신 0건 관측 + 제안 카드 생성

### AC-LOOKLIB-010 — 자연어 매칭

**When** 매칭 축이 한국어 무드 구문 집합(예: "웅장한 금색 코러스", "잔잔한 발라드 인트로", "EDM 드랍")을 받으면, the 매칭 **shall** 기대 장르·다이내믹스 대역의 룩을 반환하고, 라이브러리 외 무드에는 명시적 no-match(폴백 신호)를 반환한다.

- 대상 요구사항: REQ-LOOKLIB-015 / REQ-LOOKLIB-018
- 검증 방법: `pytest server/tests/test_looks_matching.py -q` — 한국어 구문→기대 룩 표 기반 테스트 + no-match 케이스
- 기대 결과: 매칭 표 전량 PASS + no-match가 강제 매칭으로 오염되지 않음

### AC-LOOKLIB-011 — 폴백 경로 보존

**When** 매칭이 no-match를 반환하면, the 시스템 **shall** 기존 룰북 무드 폴백 경로로 강등하며, 그 경로의 기존 테스트는 회귀 없이 그린이다.

- 대상 요구사항: REQ-LOOKLIB-017
- 검증 방법: 폴백 분기 테스트 + 기존 채팅/무드 관련 스위트 회귀 확인
- 기대 결과: 폴백 분기 관측 + 기존 스위트 신규 실패 0건

### AC-LOOKLIB-012 — 고정 프리픽스 규율

**When** 본 SPEC의 전체 변경이 적용되면, the 룰북 프리픽스 **shall** 구조화 룩 데이터 본문·per-show 값을 포함하지 않으며, 프리픽스 변경이 있다면 정적 텍스트의 1회 변경으로 수렴한다.

- 대상 요구사항: REQ-LOOKLIB-022
- 검증 방법: `assemble_prefix()` 출력 검사 테스트(룩 데이터 시그니처 부재) + 기존 AC-MVP-014 계열 byte-stability 테스트 그린
- 기대 결과: 프리픽스 내 룩 구조화 데이터 0건 + byte-stability 스위트 그린

### AC-LOOKLIB-013 — 전체 회귀 (협상 불가)

전체 회귀 스위트 **shall** run-phase 킥오프 기준선 대비 신규 실패 0건을 유지한다.

- 대상 요구사항: (의도적 REQ 무연결 — 전역 회귀 게이트, EXECBODY-001 AC-014 선례) 협상 불가.
- 검증 방법: `.venv/bin/python -m pytest -q` + `npm run test`(ui — 무변경 확인 목적), 킥오프 기준선 대조
- 기대 결과: 신규 실패 0건

### AC-LOOKLIB-014 — 종단 라이브 인수 (LIVE — 본 SPEC 유일의 라이브 AC)

**When** 실물 onPC 2.4.2에서 사용자가 채팅으로 추상 무드 지시(예: "웅장한 금색 코러스로 가자")를 1회 입력하면, the 시스템 **shall** 룩 매칭 → 역할 매핑 → 인스턴스화 번들 → 게이트 경유 실행까지 종단 완결하고, 생성 오브젝트가 콘솔 GUI에서 확인되며, 감사 로그에 해당 번들의 송신 기록이 1:1로 남는다.

- 대상 요구사항: REQ-LOOKLIB-010/011/013/015 종단 + ASSUMPTION-13/14 실측
- 검증 방법: 실물 콘솔 라이브 세션 — 감사 로그 jsonl verbatim 판독(EXECBODY-001 AC-010 인수 형식) + 프리셋 풀/시퀀스 GUI 스크린샷 + 요약 보고 캡처
- 기대 결과: 종단 성공 + 감사 1:1 + GUI 실물 확인. ASSUMPTION-13이 부정 실측되면(역할 전멸 미매핑) 미매핑 보고가 정직하게 출력되는 것까지를 관측하고, 그 사실을 progress.md에 기록한다(plan.md §A.3 — 축소도 유효한 인수 결과이나 "종단 성공" 판정에는 매핑 ≥1 역할이 필요)

## §D. Edge Cases

- **콘솔 불능 중 인스턴스화 지시**: `console_unreachable` 전파 — 번들 생성 전 중단 + 명시 보고(기존 health gate 동작과 정합).
- **truncated 리그**: groups 섹션 truncated 시 매핑 결과에 불완전성 표시 — 완전한 리그처럼 제시 금지(tools.py rig_section 계약).
- **역할 전멸 미매핑**: 시나리오 2 — 정직한 축소, 커맨드 0건도 유효 출력.
- **드릴다운 캡 도달**: 슬롯 탐색(정책이 런타임 탐색을 채택한 경우)이 캡에 걸리면 `drilldown_capped` 정합 처리 — 부분 탐색을 전체로 위장 금지.
- **동일 지시 반복(더블 인스턴스화)**: 같은 룩 재인스턴스화 시 충돌 정책이 자연히 방어(점유 슬롯 스킵/보고) — 무한 중복 생성 금지.
- **LiveLock이 승인 대기 중 활성화**: 기존 lock-FIRST 재확인(gate.py:318-321)이 그대로 방어 — 룩 경로 특례 없음.
- **다이내믹스 경계 표현**("살짝만 웅장하게"): 매칭은 근접 대역 반환 또는 no-match 폴백 — 억지 최상급 매칭 금지.

## §E. Quality Gate 기준

- pytest 전체: run-phase 킥오프 기준선 대비 신규 실패 0건.
- `ruff check`: 터치 파일 clean(기존 baseline 위반은 별도 표기).
- `grep -rn 'AskUserQuestion\|mcp__askuser' server/looks/`: 0건(subagent boundary).
- `@MX:ANCHOR` 3종(gate.py:260-265, classify.py:169, assembly.py:69-72) 무변경 확인(신규 ANCHOR 추가 없음 — plan.md §D).
- `server/safety/**` diff 없음, `server/looks/**`의 bridge import 0건.
- 라이브 세션 산출물(M6): 감사 로그 verbatim + GUI 스크린샷이 progress.md §E.2에 기록.

## §F. Definition of Done

1. plan.md §A.4의 미해결 결정 6건이 Implementation Kickoff Approval 전 전부 해소되어 design.md §5에 fold-in되어 있다.
2. AC-LOOKLIB-001~013 전부 PASS(기계 검증) — 협상 불가 게이트는 AC-008/009/012/013.
3. AC-LOOKLIB-014(LIVE)가 실측 완료: 종단 성공이 감사 로그+GUI로 확인되었거나, ASSUMPTION-13 부정 실측 시 정직한 축소 동작이 실측·기록되고 후속 항목(휴리스틱 확장)이 등재되어 있다.
4. 내장 라이브러리가 4장르 × 6~10룩 완결 상태로 repo에 존재하고, 스키마 문서(P1-1/P1-2 소비 계약)가 `server/looks/` 내에 존재한다.
5. 미매핑·충돌·폴백의 실패 방향이 전부 축소/보류임이 테스트로 고정되어 있다(추측 보완 경로 0).
6. P1-1/P1-2 기능이 본 SPEC의 커밋 범위에 등장하지 않는다(§D 범위 경계).
