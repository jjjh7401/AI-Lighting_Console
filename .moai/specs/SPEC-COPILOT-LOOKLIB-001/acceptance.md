# SPEC-COPILOT-LOOKLIB-001 — 인수 기준 (acceptance)

status: draft (v0.2.0, 2026-07-26) · Tier L · 본 문서는 spec.md의 요구를 관측 가능한 검증 기준으로 전개한다.

> **v0.2.0 — 독립 감사(FAIL 0.65) 반영.** (a) **AC 미커버 REQ 5건에 AC 신설**(감사 D4/D12): REQ-006·013·014·016·021 → AC-015~019. (b) **M0 라이브 프로브 AC 신설**(감사 D9): AC-020. (c) **REQ↔AC 역추적표 도입** — 미커버 REQ가 조용히 생기지 않도록 구조적으로 봉쇄. (d) AC-007 `/Overwrite` assert **대소문자 무관화**(D14), AC-008 "run_commands 경유만" 주장의 검증 보강(D10), AC-014의 비토큰 축약 REQ 표기 정정(D12).
>
> **번호 정책**: 기존 AC-001~014는 **번호를 유지**한다(plan.md·design.md·§F의 교차 참조 안정성). 신설분은 §C.2에 015~020으로 추가한다 — 문서상 LIVE AC(014) 뒤에 오지만 실행 순서와는 무관하다(각 AC의 담당 마일스톤은 역추적표에 명시).

## §A. 개요

본 SPEC의 성공 기준은 세 층위다:

1. **데이터 계층** — 스키마·내장 라이브러리가 기계 검증 가능하게 완결되고 per-show 값이 없다.
2. **파이프라인 통합** — 역할 매핑·인스턴스화·매칭이 전부 기존 게이트/프리뷰/폴백/안전 불변식 위에서 동작하며, 실패 방향이 항상 축소/보류다.
3. **라이브 실측(2건)** — **M0 프로브**(저작 전 전제 실측)와 **M7 종단**(통합 후 종단 완결). v0.1.0은 "라이브 AC 정확히 1건"을 설계 성질로 삼았으나, 전제 검증이 그 전제에 의존하는 저작보다 뒤에 오는 순서 결함이 있어 M0를 신설했다(감사 D9, 근거는 plan.md §B 라이브 세션 회계 / design.md §6.5).

부분 성공은 부분 성공으로 보고한다: 역할 전멸 매핑·매칭 실패는 명시적 축소 출력이 정답이며(REQ-LOOKLIB-009/017), 이를 성공으로 위장하는 것이 실패다. **M0의 부정 실측(빔 DESCOPE, 명명 관례 미매칭)도 유효한 인수 결과다.**

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
- **Then** 시스템은 **어떤 경로로도** `Store /Overwrite`를 발화하지 않고 **재슬롯도 하지 않으며**, 충돌 항목을 **건너뛰고** "N개 건너뜀"을 요약 보고에 포함한다(사용자 확정 ⑦) — 사용자 프리셋은 파괴되지 않는다.

### 시나리오 5 — LiveLock 중 제안 강등

- **Given** LiveLock이 활성이다.
- **When** 룩 적용이 지시된다.
- **Then** 콘솔 송신은 0건이고 제안 카드만 생성된다(lock-FIRST 재확인 포함, 기존 게이트 동작 무변경).

## §C. AC (GEARS 형식 — 검증 레시피는 각 AC 하위 상세로 보존)

### §C.0 REQ ↔ AC 역추적표 (감사 D4 재발 방지)

v0.1.0은 **REQ-006 / 013 / 014 / 016 / 021이 어떤 AC에도 연결되지 않은 채** 출하될 뻔했다. REQ-013은 AC-014(LIVE) 본문에 비토큰 축약("REQ-LOOKLIB-010/011/013/015")으로만 등장해 기계 추출이 불가능했고(감사 D12), 그마저도 라이브 AC 뒤에 숨어 있어 유닛 레벨 검증 경로가 없었다. 아래 표가 그 구조적 공백을 봉쇄한다 — **모든 REQ가 최소 1개 AC를 갖는다.**

| REQ | 커버하는 AC | 담당 M | 비고 |
|---|---|---|---|
| REQ-LOOKLIB-001 | AC-001 | M1 | 빔 게이트 부분은 AC-020(M0)이 선행 |
| REQ-LOOKLIB-002 | AC-002 | M2 | 스팬 판정은 마커 2 확정 척도에 의존 |
| REQ-LOOKLIB-003 | AC-003 | M2 | 3구간 어휘(확정/용도한정/프로브대기) 각각 검증 |
| REQ-LOOKLIB-004 | AC-004 | M2 | |
| REQ-LOOKLIB-005 | AC-001 | M1 | |
| **REQ-LOOKLIB-006** | **AC-015 (신설)** | M1 | v0.1.0 미커버 — 감사 D4 |
| REQ-LOOKLIB-007 | AC-005 | M3 | |
| REQ-LOOKLIB-008 | AC-006 | M3 | |
| REQ-LOOKLIB-009 | AC-005 | M3 | |
| REQ-LOOKLIB-010 | AC-008, AC-014 | M4, M7 | |
| REQ-LOOKLIB-011 | AC-007, AC-014 | M4, M7 | |
| REQ-LOOKLIB-012 | AC-007 | M4 | 대소문자 무관 assert(D14) |
| **REQ-LOOKLIB-013** | **AC-018 (신설, 유닛)** + AC-014 | M4, M7 | v0.1.0은 LIVE AC 뒤에만 존재 — 감사 D12 |
| **REQ-LOOKLIB-014** | **AC-016 (신설)** | M4 | v0.1.0 미커버 — 감사 D4/D11 |
| REQ-LOOKLIB-015 | AC-012, AC-014 | M5, M7 | |
| **REQ-LOOKLIB-016** | **AC-017 (신설)** | M5 | v0.1.0 미커버 — 감사 D4 |
| REQ-LOOKLIB-017 | AC-011 | M5 | |
| REQ-LOOKLIB-018 | AC-012 | M5 | |
| REQ-LOOKLIB-019 | AC-008 | M4 | |
| REQ-LOOKLIB-020 | AC-009 | M6 | |
| **REQ-LOOKLIB-021** | **AC-019 (신설)** | M6 | v0.1.0 미커버 — 감사 D4 |
| REQ-LOOKLIB-022 | AC-010 | M6 | |
| (REQ 무연결 — 전역 게이트) | AC-013 | M6 | 전체 회귀, 협상 불가 |
| (ASSUMPTION-13/14/15 실측) | **AC-020 (신설, LIVE)** | M0 | 감사 D9 |

### §C.1 기존 AC (001~014 — 번호 유지)

### AC-LOOKLIB-001 — 스키마 로딩 + 검증

**When** 내장 라이브러리가 로드되면, the 로더 **shall** 스키마 검증을 통과시키고, 주입된 위반 케이스(미지 역할/attribute, 다이내믹스 이탈, 중복 id)를 명시적 에러로 거부한다.

- 대상 요구사항: REQ-LOOKLIB-001 / REQ-LOOKLIB-005
- 검증 방법: `pytest server/tests/test_looks_schema.py -q` — 정상 로드 + 위반 케이스별 개별 거부 테스트
- 기대 결과: 전량 PASS, 위반 케이스는 병합 없이 개별 테스트

### AC-LOOKLIB-002 — 내장 라이브러리 커버리지

내장 라이브러리 **shall** 워십/록/발라드/EDM 4장르를 포함하고, 각 장르는 6~10개 룩을 가지며, 각 장르가 다이내믹스 척도의 **최저 구간과 최고 구간을 각각 1개 이상** 포함한다.

- 대상 요구사항: REQ-LOOKLIB-002
- 검증 방법: `pytest server/tests/test_looks_library.py -q` — 장르 수/장르당 룩 수/다이내믹스 스팬을 기계 assert
- **"스팬"의 기계적 정의 (감사 D8c)**: 제안 기본값(정수 1~5, plan.md §A.4b 마커 2)을 채택할 경우 → 각 장르가 `level in {1,2}`인 룩 ≥1개 **그리고** `level in {4,5}`인 룩 ≥1개. v0.1.0의 "최소 저역…최고역"은 척도가 정의되지 않아 **평가 불가능한 문장**이었다 — Kickoff에서 마커 2가 확정되면 그 척도로 이 식을 확정한다.
- 기대 결과: 4장르 × 6~10룩 × 스팬 조건 전부 기계 검증 PASS

### AC-LOOKLIB-003 — 검증된 attribute 어휘 한정

라이브러리의 모든 속성 페이로드 **shall** REQ-LOOKLIB-003의 3구간 어휘 규칙을 만족한다.

- 대상 요구사항: REQ-LOOKLIB-003
- 검증 방법: 라이브러리 전수 순회 테스트 — 세 구간을 **각각 개별 테스트**로 분리(design.md §6.2 실패 모드 병합 금지)
  1. **실측 확정 어휘**: `Dimmer` / `ColorRGB_R` / `ColorRGB_G` / `ColorRGB_B` 및 검증된 페이저·MAtricks 문법만 등장 — 허용 집합 밖 이름 발견 시 실패.
  2. **용도 한정 어휘 (감사 D2)**: `Pan` / `Tilt`가 등장하는 위치가 **전부 무브먼트(페이저) 지정 내부**임을 assert. **정적 포지션 값으로 등장하면 실패** — 이것이 v0.1.0에서 REQ-003의 평면 허용 목록이 §A 사용자 확정 ①·REQ-009의 금지와 충돌했던 지점이다.
  3. **프로브 대기 어휘**: 빔 계열 문자열은 **M0 판정 결과에 등재된 문자열만** 등장. M0가 DESCOPE면 빔 값 0건(스키마 필드는 존재하되 라이브러리 미사용)을 assert. 스트로브/셔터 문자열은 어느 분기에서든 **0건**(spec.md §D Out of Scope).
- 기대 결과: 3구간 개별 테스트 전량 PASS, 위반 0건

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

생성된 인스턴스화 번들 **shall** 선두 `ChangeDestination Root` 1회, 각 룩 캡처 전과 각 `Store` 후 `ClearAll`, 생성 오브젝트별 `Label`을 포함하고, **어떤 경로에서도** `/Overwrite`를 포함하지 않는다.

- 대상 요구사항: REQ-LOOKLIB-011 / REQ-LOOKLIB-012
- 검증 방법: `pytest server/tests/test_looks_instantiate.py -q` — 번들 문자열 수준 불변식 assert(design.md §6.3)
- **`/Overwrite` assert는 대소문자 무관이어야 한다 (감사 D14)**: `assert not re.search(r"/overwrite", bundle, re.IGNORECASE)` 형태. **근거** — 런타임 매칭은 이미 대소문자 무관이다(`server/safety/ruleset.py:47` `lowered = [e.lower() ...]`, `server/safety/classify.py:64` `t, k = text.lower(), keyword.lower()`, `server/web/preview.py:100` `lower = command.lower()`). 따라서 대소문자를 고정한 assert(`"/Overwrite" not in bundle`)는 빌더가 `/overwrite`를 내보내도 **조용히 통과**한다. 위험은 런타임 방어의 구멍이 아니라 **테스트의 위양성**이며, 그래서 이 항목은 테스트 작성 규칙으로 명시된다.
- 추가 assert: 충돌 슬롯이 **재슬롯되지 않고 건너뛰어짐**(사용자 확정 ⑦) — 점유 슬롯이 주입된 fake rig에서 해당 슬롯 대상 `Store`가 번들에 0건.
- 기대 결과: 5개 불변식 전부 기계 PASS (대소문자 무관 케이스 포함)

### AC-LOOKLIB-008 — 단일 실행 경로 + 경계 무변경

룩 모듈 **shall** 기존 `run_commands → gate.screen()` 경로로만 실행을 흘리며, OSC/bridge 표면을 import하지 않는다.

- 대상 요구사항: REQ-LOOKLIB-010 / REQ-LOOKLIB-019
- **검증 범위의 정직한 분해 (감사 D10)**: v0.1.0의 검증 방법 3종은 "**bridge를 import하지 않는다**"만 증명하고 "**`run_commands` 경유로만 실행이 흐른다**"는 주장은 증명하지 않았다 — 둘은 다른 명제다(모듈이 bridge를 직접 import하지 않으면서도 게이트 밖의 다른 실행 헬퍼를 호출할 수 있다). 아래 ①~④로 분해한다.
  - ① **bridge 경계** (기존, 유효): `pytest server/tests/test_architecture.py -q`. 이 테스트는 `SERVER_DIR.rglob("*.py")`로 서버 트리 전수를 훑고 허용 프리픽스(`server/bridge/`, `server/safety/`, `server/tests/`)만 면제하므로(`server/tests/test_architecture.py:51-54`), **신규 `server/looks/`는 자동으로 검사 대상에 포함**된다 — 테스트 수정 없이 경계가 확장된다.
  - ② **import 경로 직접 grep** (기존, 유효): `grep -rn "bridge.osc\|from server.bridge" server/looks/` → 0건.
  - ③ **실행 호출 경로 assert** (**신설** — ①②가 덮지 못한 부분): `server/looks/`의 어느 모듈도 `SafetyGate.screen` / `ExecutionPort` / 콘솔 링크를 직접 호출하지 않음을 정적으로 assert한다 — `grep -rnE "gate\.screen|execution_port|ConsoleLink" server/looks/` → 0건. 룩 계층은 **번들 문자열을 반환할 뿐 스스로 실행하지 않는다**는 것이 REQ-010의 실질 내용이다.
  - ④ **safety 무변경**: `git diff --stat server/safety/` → 빈 출력.
- 기대 결과: ① 그린 + ②③ grep 각 0건 + ④ 빈 출력

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

### AC-LOOKLIB-014 — 종단 라이브 인수 (LIVE — 2건 중 2번째, M7)

**When** 실물 onPC 2.4.2에서 사용자가 채팅으로 추상 무드 지시(예: "웅장한 금색 코러스로 가자")를 1회 입력하면, the 시스템 **shall** 룩 매칭 → 역할 매핑 → 인스턴스화 번들 → 실행 프리뷰 → 게이트 경유 실행까지 종단 완결하고, 생성 프리셋이 콘솔 GUI에서 확인되며, 감사 로그에 해당 번들의 송신 기록이 1:1로 남는다.

- 대상 요구사항 (**감사 D12 — 축약 표기를 완전 토큰으로 정정**): `REQ-LOOKLIB-010`, `REQ-LOOKLIB-011`, `REQ-LOOKLIB-013`, `REQ-LOOKLIB-015` 종단. v0.1.0의 `REQ-LOOKLIB-010/011/013/015` 축약은 **기계 추출이 불가능**해 REQ-013이 커버리지 스캔에서 사라졌다. REQ-013의 유닛 레벨 커버는 AC-LOOKLIB-018이 별도로 갖는다 — 라이브 AC 뒤에만 있는 요구는 라이브 세션 없이는 검증 불가이기 때문이다.
- **ASSUMPTION 재측정 없음 (감사 D9)**: ASSUMPTION-13/14/15는 **M0(AC-LOOKLIB-020)에서 이미 실측**되었다. M7은 종단 통합의 실측이지 전제 검증이 아니다. M0 판정과 M7 관측이 어긋나면 그 불일치를 progress.md에 기록한다.
- 검증 방법: 실물 콘솔 라이브 세션 — 감사 로그 jsonl verbatim 판독(EXECBODY-001 AC-010 인수 형식) + 프리셋 풀 GUI 스크린샷 + 실행 프리뷰 이벤트 캡처 + 요약 보고 캡처
- 기대 결과: 종단 성공 + 감사 1:1 + GUI 실물 확인. 역할이 전멸 미매핑이면 미매핑 보고가 정직하게 출력되는 것까지를 관측하고 progress.md에 기록한다(plan.md §A.3 — 축소도 유효한 인수 결과이나 "종단 성공" 판정에는 매핑 ≥1 역할이 필요)

### §C.2 신설 AC (015~020 — 감사 반영)

### AC-LOOKLIB-015 — 역할 어휘 폐쇄 집합 (REQ-006, 신설: 감사 D4)

역할 어휘 **shall** 폐쇄 집합으로 정의되고, 각 역할이 한국어·영어 별칭과 매핑 힌트 문자열을 가지며, 스키마가 집합 밖 역할 이름을 **거부**한다.

- 대상 요구사항: `REQ-LOOKLIB-006`
- 검증 방법: `pytest server/tests/test_looks_schema.py -q` — ① 집합 밖 역할 이름을 담은 룩 주입 시 로더가 명시적 에러로 거부, ② 집합의 모든 역할이 한/영 별칭 ≥1개씩 보유, ③ 라이브러리 전수의 포지션 필드가 집합 내부 값만 사용.
- **PRESERVE assert (감사 D13)**: `git diff --stat server/rulebook/assets/v2.4.2/20_korean_terms.md` → **빈 출력**. REQ-006은 그 파일과의 *행 단위 정합*이 아니라 **명명 관례 스타일 준수**만 요구하므로, 이 AC를 만족시키기 위해 어떤 PRESERVE 파일도 수정되어서는 안 된다. v0.1.0의 REQ-006 문언("20_korean_terms.md의 showfile 어휘 클래스 관례와 정합")은 존재하지 않는 행과의 정합을 요구해, 문자 그대로 만족시키려면 PRESERVE 파일 수정이 필요했다.
- 기대 결과: ①②③ 전량 PASS + PRESERVE diff 빈 출력

### AC-LOOKLIB-016 — 생성형 Lua 경로의 배포 파이프라인 우회 부재 (REQ-014, 신설: 감사 D4/D11)

the 룩 계층 **shall** 생성형 Lua 배포를 위한 제2 표면을 갖지 않으며, 해당 경로가 사용되는 경우 전부 기존 `deploy_plugin` 파이프라인(pcall compile → destructive scan → 사람 리뷰 게이트)을 경유한다.

- 대상 요구사항: `REQ-LOOKLIB-014`
- 검증 방법 (**정적 부재 검증** — REQ-014를 역량 게이트로 재진술한 결과, 감사 D11):
  - `grep -rnE "build_plugin_xml|deploy/pack|lupa|pcall" server/looks/` → **0건** (룩 계층이 패키징·컴파일 표면을 직접 만지지 않음)
  - `grep -rn "deploy_pipeline\|deploy_plugin" server/looks/` → 0건 또는, 사용 시 **툴 레지스트리 경유 호출만**임을 코드 리뷰로 확인
  - `git diff --stat server/deploy/` → **빈 출력** (파이프라인 무변경)
- **공허한 참(vacuous truth)이 아닌 이유**: v1 산출물이 프리셋만이므로(사용자 확정 ⑥) 생성형 Lua 경로는 사용되지 않을 전망이다. 그래도 이 AC는 의미를 갖는다 — "사용하지 않는다"가 아니라 "**우회 표면이 존재하지 않는다**"를 확인하기 때문이다. v0.1.0의 REQ-014("사용하면 파이프라인을 경유한다")는 사용하지 않으면 자동으로 참이 되는 동어반복이었다.
- 기대 결과: grep 전량 0건 + deploy diff 빈 출력

### AC-LOOKLIB-017 — 매칭의 단일 진실원 + 제공자 중립 (REQ-016, 신설: 감사 D4)

매칭의 단일 진실원 **shall** 구조화 룩 라이브러리 데이터이며, the 매칭 표면 **shall** 특정 LLM 제공자 어댑터에 종속되지 않는다.

- 대상 요구사항: `REQ-LOOKLIB-016`
- 검증 방법:
  - **제공자 중립 (정적)**: `grep -rnE "anthropic|gemini|AnthropicAdapter|GeminiAdapter" server/looks/` → **0건**. 근거 — `server/llm/factory.py:17-28` `build_provider`가 `config.active` 값으로 `AnthropicAdapter` 또는 `GeminiAdapter` 중 정확히 하나를 부팅하므로, 룩 계층이 어느 한쪽을 이름으로 참조하면 그 순간 중립이 깨진다.
  - **제공자 중립 (동적)**: 매칭 테스트를 두 제공자 config 모두에 대해 파라미터화하거나, 매칭 축이 제공자 무관한 순수 함수임을 assert(주입된 라이브러리 데이터만 입력).
  - **단일 진실원**: 매칭 결과의 모든 look id가 로더가 반환한 라이브러리 집합 안에 있음을 assert — 프롬프트·룰북 안내 축이 라이브러리에 없는 룩을 만들어낼 수 없음.
- 기대 결과: grep 0건 + 제공자 무관 통과 + look id 집합 포함 관계 PASS

### AC-LOOKLIB-018 — 요약 보고 형상 (REQ-013 유닛 레벨, 신설: 감사 D12)

**When** 인스턴스화가 완료되면, the 요약 보고 **shall** (a) 생성 프리셋의 풀·슬롯·이름, (b) 미매핑 역할 목록, (c) **건너뛴 항목 수와 슬롯**, (d) `drilldown_capped` 표시를 구조화된 형태로 담는다.

- 대상 요구사항: `REQ-LOOKLIB-013`
- **왜 유닛 레벨이 필요한가**: v0.1.0에서 REQ-013은 AC-014(LIVE)의 축약 표기 안에만 존재했다. 즉 **실물 콘솔 세션 없이는 이 요구를 검증할 방법이 없었다** — 라이브 접근이 확보되지 않으면 보고 형상이 미검증인 채로 남는다. 이 AC가 그 의존을 끊는다.
- 검증 방법: `pytest server/tests/test_looks_instantiate.py -q` — fake rig + 인위적 충돌 슬롯 + 미매핑 역할 + `drilldown_capped` 신호를 주입한 4개 시나리오에서 보고 dict의 (a)~(d) 필드를 개별 assert(design.md §6.2 병합 금지).
  - 특히 (c)는 **"N개 건너뜀"의 N이 실제 충돌 수와 일치**함을 assert — 부분 성공을 전체 성공으로 위장하지 않는다는 요구의 기계적 형태.
- 기대 결과: 4시나리오 × (a)~(d) 필드 전량 PASS

### AC-LOOKLIB-019 — 기존 안전 불변식 전체 상속 (REQ-021, 신설: 감사 D4)

**While** 본 SPEC의 룩 인스턴스화 메커니즘이 활성 상태여도, the 게이트 **shall** 기존 안전 불변식 전부(health gate, 문법 검증, 위험 분류, LiveLock, deny-all 기본 승인 포트, 위험 커맨드 사전 백업 fail-closed, 미확인 이력 재승인·자동 재전송 금지, 스크리닝 전 실행 프리뷰 발화)를 무변경 유지한다.

- 대상 요구사항: `REQ-LOOKLIB-021`
- 검증 방법 (**형식은 `SPEC-COPILOT-EXECBODY-001/acceptance.md:125-131` AC-EXECBODY-011을 그대로 계승** — 형제 SPEC이 이 형태로 검증 가능함을 이미 입증했다):
  ```
  pytest server/tests/test_safety_gate.py server/tests/test_web_panel_execute.py -q
  ```
  + 프리뷰 계층 회귀: `pytest server/tests/test_web_preview.py -q`
  + `git diff --stat server/safety/ server/web/preview.py` → **빈 출력**
- 기대 결과: 전량 PASS + diff 빈 출력

### AC-LOOKLIB-020 — M0 라이브 프로브 (LIVE — 2건 중 1번째, M1의 전제, 신설: 감사 D9)

**When** M1 착수 전 실물 onPC 2.4.2에서 프로브 세션이 수행되면, the 세션 **shall** ASSUMPTION-13 / 14 / 15와 슬롯 탐색 실현성 각각에 대해 **GO 또는 DESCOPE 판정과 그 실측 근거**를 산출하고, 그 판정이 progress.md §E.2에 **각주가 아니라 명시적 섹션**으로 기록된다.

- 대상 요구사항: (REQ 무연결 — 전제 실측 게이트). ASSUMPTION-13/14/15 실측이 대상이며, 결과가 REQ-LOOKLIB-001의 빔 게이트와 plan.md §A.4b 마커 1의 힌트 문자열을 확정한다.
- 검증 방법 (**형식은 `SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123` AC-EXECBODY-010의 GO/DESCOPE 조건부 인수 패턴 계승**):
  - **ASSUMPTION-15 (빔)**: 후보 `Attribute 'Zoom'` / `'Focus'` / `'Iris'` / `'Frost'` / `'Prism1'` / `'Shutter'`를 게이트 경유로 발화하고 콘솔 응답·감사 로그 verbatim 판독. **GO** = ≥1개 수용 → 수용된 문자열 목록과 값 범위 기록. **DESCOPE** = 0개 수용 → REQ-001 빔 게이트 발동.
  - **ASSUMPTION-14 (`Store Preset` 캡처)**: 컬러 값만 활성인 프로그래머에서 `Store Preset <pool>.<slot>` → `Label` 후 GUI/`query_state`로 저장 내용 확인. GO = 기대 속성만 캡처 / 형상 수정 필요 = 그 사실과 관측 내용 기록.
  - **ASSUMPTION-13 (명명 관례)**: `get_rig_context` groups 판독 → plan.md §A.4b 마커 1의 제안 6종 역할에 대해 **매칭된 역할 수**를 기록(0건도 유효 결과 — 힌트 문자열 조정 입력이 된다).
  - **슬롯 탐색 실현성**: preset_pools 드릴다운으로 점유 슬롯 판독, `drilldown_capped` 발생 여부 기록.
- 기대 결과: 판정 4건 + 실측 원문(콘솔 응답 / 감사 로그 jsonl verbatim / GUI 스크린샷)이 progress.md §E.2의 명시적 섹션에 존재. **부정 실측도 PASS다** — 이 AC가 요구하는 것은 "긍정 결과"가 아니라 "**실측되고 기록되었다**"이다(plan.md §A.3 정직한 축소, EXECBODY-001 M1 GO/DESCOPE 선례).

## §D. Edge Cases

- **콘솔 불능 중 인스턴스화 지시**: `console_unreachable` 전파 — 번들 생성 전 중단 + 명시 보고(기존 health gate 동작과 정합).
- **truncated 리그**: groups 섹션 truncated 시 매핑 결과에 불완전성 표시 — 완전한 리그처럼 제시 금지(tools.py rig_section 계약).
- **역할 전멸 미매핑**: 시나리오 2 — 정직한 축소, 커맨드 0건도 유효 출력.
- **드릴다운 캡 도달**: 런타임 빈 슬롯 탐색(사용자 확정 ⑤)이 `RIG_DRILLDOWN_QUERY_CAP = 16`(`server/orchestrator/tools.py:88`)에 걸리면 `drilldown_capped`를 보고에 전파 — 부분 탐색을 전체로 위장 금지(AC-018 (d)).
- **동일 지시 반복(더블 인스턴스화)**: 같은 룩 재인스턴스화 시 충돌 정책(건너뛰기)이 자연히 방어 — 두 번째 실행은 "N개 건너뜀"만 보고하고 중복 생성이 없다.
- **빔 DESCOPE 후 빔 언급 지시**("줌 좁혀줘" 류): M0가 DESCOPE로 판정된 빌드에서는 라이브러리에 빔 값이 없으므로 매칭이 no-match → 룰북 무드 폴백으로 강등된다(REQ-017). 빔 문자열을 추측해 합성하지 않는다(design.md AP-11).
- **스트로브를 요청하는 지시**("스트로브 쳐줘"): v1 라이브러리에 스트로브 룩이 없으므로 no-match → 폴백. 폴백 경로에서 사용자가 직접 스트로브 커맨드를 지시하면 기존 프리뷰가 `danger`로 분류하고 게이트가 정상 처리한다 — 본 SPEC은 그 경로를 바꾸지 않는다.
- **LiveLock이 승인 대기 중 활성화**: 기존 lock-FIRST 재확인(gate.py:318-321)이 그대로 방어 — 룩 경로 특례 없음.
- **다이내믹스 경계 표현**("살짝만 웅장하게"): 매칭은 근접 대역 반환 또는 no-match 폴백 — 억지 최상급 매칭 금지.

## §E. Quality Gate 기준

- pytest 전체: run-phase 킥오프 기준선 대비 신규 실패 0건.
- `ruff check`: 터치 파일 clean(기존 baseline 위반은 별도 표기).
- `grep -rn 'AskUserQuestion\|mcp__askuser' server/looks/`: 0건(subagent boundary).
- `@MX:ANCHOR` 3종(`server/safety/gate.py:260-265`, `server/safety/classify.py:169`, `server/rulebook/assembly.py:69-72`) 무변경 확인(신규 ANCHOR 추가 없음 — plan.md §D).
- **PRESERVE diff 빈 출력**: `git diff --stat server/safety/ server/web/preview.py server/rulebook/assets/v2.4.2/20_korean_terms.md`.
- `server/looks/**`의 bridge import 0건 + 실행 호출 0건(AC-008 ②③).
- `grep -rniE "/overwrite" server/looks/` → 0건(**대소문자 무관**, 감사 D14).
- 라이브 세션 산출물 **2회분**: **M0**(AC-020 — 판정 4건 + 실측 원문)와 **M7**(AC-014 — 종단 감사 로그 verbatim + GUI 스크린샷)이 각각 progress.md §E.2에 **명시적 섹션**으로 기록.

## §F. Definition of Done

1. plan.md §A.4b의 미해결 결정 **3건**(역할 어휘 / 다이내믹스 척도 / 매핑 UX)이 Implementation Kickoff Approval 전 전부 해소되어 design.md §5.1로 이동해 있다. §A.4a의 해소 7건은 재질의 없이 그대로 적용된다.
2. **AC-LOOKLIB-020(LIVE, M0)이 M1 착수 전에 실측 완료**되어 있고, ASSUMPTION-13/14/15 판정 4건이 progress.md §E.2에 명시적 섹션으로 존재한다. **부정 실측도 충족**이다 — 요구는 긍정 결과가 아니라 실측·기록이다.
3. AC-LOOKLIB-001~013 및 신설 AC-LOOKLIB-015~019 전부 PASS(기계 검증) — 협상 불가 게이트는 **AC-008 / 009 / 012 / 013 / 019**(019 추가: 기존 안전 불변식 상속은 협상 대상이 아니다).
4. AC-LOOKLIB-014(LIVE, M7)가 실측 완료: 종단 성공이 감사 로그+GUI로 확인되었거나, 역할 전멸 미매핑 시 정직한 축소 동작이 실측·기록되고 후속 항목(휴리스틱 확장)이 등재되어 있다.
5. **§C.0 역추적표의 모든 REQ가 최소 1개 AC로 커버되어 있고**, 그 표가 최종 REQ 목록과 일치한다(감사 D4 재발 방지 — REQ를 추가·삭제하면 표를 함께 갱신한다).
6. 내장 라이브러리가 4장르 × 6~10룩 완결 상태로 repo에 YAML 자산으로 존재하고, 스키마 문서(P1-1/P1-2 소비 계약)가 `server/looks/` 내에 존재한다. **빔 필드는 M0 판정에 따라 값이 채워졌거나, DESCOPE 사유와 함께 미사용 상태로 명시되어 있다.**
7. 미매핑·충돌·폴백의 실패 방향이 전부 축소/보류임이 테스트로 고정되어 있다(추측 보완 경로 0).
8. **PRESERVE 무변경 확인**: `server/safety/**`, `server/web/preview.py`, `server/rulebook/assets/v2.4.2/20_korean_terms.md`의 diff가 빈 출력이다.
9. P1-1/P1-2 기능이 본 SPEC의 커밋 범위에 등장하지 않으며, **장르 묶음 런타임 실행·데모 시퀀스·익스큐터 바인딩·스트로브 값**도 등장하지 않는다(§D 범위 경계).
