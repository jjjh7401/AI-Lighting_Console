# SPEC-COPILOT-MCP-001 — 인수 기준 (acceptance)

## §A. 개요

AC **16건**. AC-MCP-015(라이브 종단)만 **사람 관측**이고 나머지 15건은 기계 검증이다. 검증 천장: 리소스의 "클라이언트 실효성"(ASSUMPTION-72)과 클라이언트 기동(ASSUMPTION-71)은 기계로 확인할 수 없다 — M6 사람 관측 + `progress.md §E.2` 접두 행 기록이 판정 채널이다(REQ-MCP-023).

## §B. Given-When-Then 시나리오

### 시나리오 1 — 행복 경로: Claude가 리그를 읽는다
- **Given** MCP 서버가 기동돼 있고 콘솔(또는 fake link)이 응답하는 상태에서
- **When** 클라이언트가 `tools/list` 후 `get_rig_context`를 호출하면
- **Then** allowlist 11종만 목록에 보이고, 리그 요약이 무손실 페이로드로 반환된다.

### 시나리오 2 — 변이 시도 거부
- **When** 클라이언트가 `run_commands`(레지스트리에 실존하는 변이 툴)를 호출하면
- **Then** 실행 없이 한국어 사유의 구조화 거부가 반환되고, fake `ConsolePort`의 `execute` 호출 기록은 **0건**이다.

### 시나리오 3 — 콘솔 오프라인
- **Given** 콘솔이 오프라인(응답기 타임아웃)인 상태에서
- **When** `query_state`를 호출하면
- **Then** 원인을 구분한 구조화 한국어 에러가 반환되고, 서버 프로세스는 살아서 후속 `tools/list`와 리소스 읽기에 정상 응답한다.

### 시나리오 4 — 포트 점유
- **Given** 수신 포트를 다른 프로세스(웹 앱 등)가 선점한 상태에서
- **When** `python -m server.mcp`로 기동하면
- **Then** stderr에 한국어 안내(원인 + 웹 앱 종료 후 재시도)가 출력되고 0이 아닌 종료 코드로 즉시 종료한다.

### 시나리오 5 — 룰북 리소스 열람
- **When** 클라이언트가 `resources/list` 후 룰북 리소스 1종을 읽으면
- **Then** 목록에 룰북 5종 + 라이브러리 자산이 보이고, 읽은 내용은 디스크 원본과 바이트 동일하다.

## §C. AC (검증 레시피는 각 AC 하위 상세)

### §C.0 REQ ↔ AC 역추적표

| REQ | AC |
|---|---|
| REQ-MCP-001 | AC-MCP-001 |
| REQ-MCP-002 | AC-MCP-012 |
| REQ-MCP-003 | AC-MCP-002 |
| REQ-MCP-004 | AC-MCP-010 |
| REQ-MCP-005 | AC-MCP-005 |
| REQ-MCP-006 | AC-MCP-013 |
| REQ-MCP-007 | AC-MCP-006 |
| REQ-MCP-008 | AC-MCP-007 |
| REQ-MCP-009 | AC-MCP-007, AC-MCP-011 |
| REQ-MCP-010 | AC-MCP-002, AC-MCP-003 |
| REQ-MCP-011 | AC-MCP-003 |
| REQ-MCP-012 | AC-MCP-004 |
| REQ-MCP-013 | AC-MCP-002, AC-MCP-005 |
| REQ-MCP-014 | AC-MCP-008 |
| REQ-MCP-015 | AC-MCP-008 |
| REQ-MCP-016 | AC-MCP-008 |
| REQ-MCP-017 | AC-MCP-014 |
| REQ-MCP-018 | AC-MCP-011 |
| REQ-MCP-019 | AC-MCP-014 |
| REQ-MCP-020 | AC-MCP-009 |
| REQ-MCP-021 | AC-MCP-009 |
| REQ-MCP-022 | AC-MCP-010 |
| REQ-MCP-023 | AC-MCP-015 |

23 REQ 전수 커버 · 고아 REQ 0건. AC-MCP-016(회귀)은 특정 REQ가 아닌 PRESERVE 경계 전체(plan.md §A.3)를 지킨다.

### §C.0a 마일스톤 배정표 (합 16 · 중복 0 · 누락 0)

| 마일스톤 | AC |
|---|---|
| M1 | AC-MCP-001, AC-MCP-013 |
| M2 | AC-MCP-003, AC-MCP-004, AC-MCP-006 |
| M3 | AC-MCP-002, AC-MCP-005, AC-MCP-009 |
| M4 | AC-MCP-008, AC-MCP-011 |
| M5 | AC-MCP-007, AC-MCP-010, AC-MCP-012, AC-MCP-014, AC-MCP-016 |
| M6 | AC-MCP-015 |

### §C.1 AC 상세

### AC-MCP-001 — 엔트리포인트 기동 (REQ-MCP-001)
- `python -m server.mcp`가 stdio 서버로 기동한다(fake link 구성으로 대체 가능).
- **레시피**: 서브프로세스 기동 → initialize 핸드셰이크 성공 → 정상 종료. stdout에 프로토콜 외 출력 0바이트(plan.md §C stdout 오염 금지).

### AC-MCP-002 — tools/list = allowlist 전수·초과 0 (REQ-MCP-003, REQ-MCP-010, REQ-MCP-013)
- `tools/list` 응답의 이름 집합 == 확정 allowlist(상한 11종). 변이 툴 이름 0건.
- **레시피**: 집합 동등 단언. `run_commands`·`deploy_plugin`·`instantiate_look`·`instantiate_fx`·`compile_scene`·`prepare_busking`·`prepare_songcue` 각각 not-in 단언.

### AC-MCP-003 — 전수 분할 테스트 (REQ-MCP-010, REQ-MCP-011)
- allowlist ∪ 제외목록 == `TOOL_NAMES` 그리고 allowlist ∩ 제외목록 == ∅.
- **레시피**: `server/orchestrator/tools.py`의 `TOOL_NAMES`를 import해 집합 연산 단언. 상류 툴 추가 시 이 테스트가 깨지는 것 자체가 설계다(plan.md D-2).

### AC-MCP-004 — 기계적 도달성: 무변이 실측 (REQ-MCP-012)
- allowlist 각 툴을 호출 기록형 fake `ConsolePort`로 대표 인자 호출 → `execute` + `deploy_plugin` 호출 합계 **0건**.
- **레시피**: 11종 전수 파라미터라이즈. `preshow_check`는 ping/왕복 호출만 허용됨을 별도 단언(ping은 변이 아님 — spec §A 분할표). 도달이 실측되면 해당 툴 제외 + `progress.md §E.2`에 `NO-GO: ASSUMPTION-69(<툴명>)` 접두 행.

### AC-MCP-005 — 변이 툴 호출 거부 (REQ-MCP-005, REQ-MCP-013)
- allowlist 밖 이름(실존 변이 툴 포함) tool call → 실행 없이 구조화 거부(한국어 사유).
- **레시피**: `run_commands` 호출 → 거부 페이로드 단언 + fake `execute` 기록 0건.

### AC-MCP-006 — 거부 스텁 2중 방벽 (REQ-MCP-007)
- allowlist 필터를 우회해 레지스트리 `dispatch("run_commands", ...)`를 직접 호출해도 `RefusingExecutionPort`가 콘솔 발화 없이 구조화 거부를 낸다.
- **레시피**: 필터 계층을 생략한 단위 테스트로 스텁 단독 검증 — 방벽 ①(allowlist)이 제거돼도 방벽 ②가 산다는 것의 실증.

### AC-MCP-007 — 포트 점유 fail-fast (REQ-MCP-008, REQ-MCP-009)
- 수신 포트 선점 상태에서 기동 → 한국어 stderr 안내 + 비0 종료 코드. 재시도 루프·포트 변경 없음.
- **레시피**: 테스트가 포트를 먼저 bind → 서브프로세스 기동 → 종료 코드·stderr 내용 단언(D-5).

### AC-MCP-008 — 리소스 목록·읽기 바이트 동일 (REQ-MCP-014, REQ-MCP-015, REQ-MCP-016)
- `resources/list`에 룰북 5종 + 룩/FX/씬 라이브러리 자산이 보이고, 각 읽기 결과가 디스크 원본과 바이트 동일하다.
- **레시피**: 5종 이름 전수 단언 + 샘플 리소스 `read` == `Path.read_bytes()` 비교. 원본 파일 mtime/내용 무변경(PRESERVE) 단언.

### AC-MCP-009 — 콘솔 오프라인 우아한 성능저하 (REQ-MCP-020, REQ-MCP-021)
- 타임아웃 fake로 `query_state` 호출 → 원인 구분된 구조화 한국어 에러. 서버 생존 — 직후 `tools/list`·리소스 읽기 정상.
- **레시피**: 타임아웃 주입 fake → 에러 페이로드 필드 단언 → 동일 세션에서 후속 호출 성공 단언.

### AC-MCP-010 — 프로토콜 스모크: stdio 관통 (REQ-MCP-004, REQ-MCP-022)
- stdio 클라이언트로 initialize → `tools/list` → `query_state`(fake link) 호출이 관통하고, dispatch 결과가 무손실로 돌아온다.
- **레시피**: MCP SDK 클라이언트(인프로세스 또는 서브프로세스)로 왕복 → 페이로드 동등 단언.

### AC-MCP-011 — 등록 아티팩트 (REQ-MCP-009, REQ-MCP-018)
- 저장소 루트 `.mcp.json`이 존재하고 엔트리포인트를 가리킨다. README에 Claude Desktop 등록 절차 + 배타 구동 제약(S2) 절이 있다.
- **레시피**: `.mcp.json` 파싱 단언(명령이 `server.mcp`를 가리킴) + README 절 존재 grep.

### AC-MCP-012 — 툴 로직 무포크 (REQ-MCP-002)
- `server/mcp/`는 orchestrator 툴 구현을 import 재사용만 한다 — 툴 본문 사본 함수가 없다.
- **레시피**: `server/mcp/` 소스에서 툴 구현 심볼의 재정의 부재를 구조 검증(import만 허용). `build_toolset`/`ToolRegistry` 사용 지점 존재 단언.

### AC-MCP-013 — 아키텍처 가드 정합 (REQ-MCP-006)
- D-1 판정 결과와 가드가 정합한다: 안 (a)면 `test_architecture.py`·`test_scene_boundary.py` **무변경** 그린, 안 (b)면 두 테스트의 의도적 diff + 판정 기록이 존재한다.
- **레시피**: 전체 스위트에서 두 가드 테스트 통과 + (안 (b)일 때만) diff 사유가 `progress.md §E.2`에 기록됐는지 확인.

### AC-MCP-014 — 무키 · 기존 설정 기동 (REQ-MCP-017, REQ-MCP-019)
- LLM API 키 환경변수가 전무한 환경에서 기동·스모크 전 구간이 통과한다. MCP 전용 신규 설정 파일이 없다.
- **레시피**: 키 관련 env를 비운 서브프로세스에서 AC-MCP-010 레시피 재실행 + 신규 설정 파일 부재 단언.

### AC-MCP-015 — 라이브 종단 (REQ-MCP-023 — 사람 관측, M6) 【이 SPEC의 중심 AC】
- 실물 onPC 연결 + 실제 Claude 클라이언트 등록 상태에서: ① 기동·등록 성공(ASSUMPTION-71), ② 리그 판독 대화가 유의미한 응답으로 성립, ③ 룰북 리소스 조회 실효 관측(ASSUMPTION-72), ④ 세션 동안 콘솔 변이 0건(콘솔측 관측).
- **레시피**: 사람 관측 체크리스트 ①~④ + `progress.md §E.2`에 판정 접두 행(`GO:`/`NO-GO:`/`CONDITION_NOT_MET:`/`INCONCLUSIVE:` — 한 판정당 1행) 기록. 코드 변경 0(결함은 기록만).

### AC-MCP-016 — 회귀 전체 그린 (PRESERVE 경계)
- 기존 전체 스위트(pytest + vitest)가 본 SPEC 변경 후에도 그린이다. PRESERVE 목록(plan.md §A.3) diff 0(허용 파일 제외).
- **레시피**: 전체 스위트 실행 + `git diff --stat`으로 변경 파일이 허용 목록에 속함을 대조.

## §D. Definition of Done

1. AC-MCP-001~014, 016 기계 검증 전부 그린 (M1~M5).
2. AC-MCP-015 사람 관측 완료 + 판정 접두 행 기록 (M6).
3. ASSUMPTION-68~73 전건 판정 기록(`progress.md §E.2` — GO/NO-GO/moot 무관, **미기록이 실패다**).
4. 조건부 결정 D-1·D-3 판정 종결.
5. PRESERVE diff 0 (허용 파일 제외).
