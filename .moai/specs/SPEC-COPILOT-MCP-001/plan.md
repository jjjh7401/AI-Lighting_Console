# SPEC-COPILOT-MCP-001 — 구현 계획 (plan)

> 마일스톤 **M1~M6**, 결정 등록부 **6건(D-1~D-6: 해소 4 · 조건부 2 — 조건부는 기계/라이브 판정으로 닫히며 사용자 재질의 불요)**, clarification 마커 **0건**. 정본 토큰 계약: REQ **23건** · AC **16건** · ASSUMPTION **6건(68~73)** · Out of Scope **10건** · 라이브 세션 **1회(M6)**. 마일스톤별 `- **AC**:` 줄은 `acceptance.md §C.0a`와 1:1이며, 합 **16 · 중복 0 · 누락 0**이다.
>
> **한 줄 요약**: 기존 툴 레지스트리의 읽기 전용 부분집합 11종을 stdio MCP 표면으로 노출한다. 무변이 보증은 3중이다 — ① 명시 allowlist + 전수 분할 테스트, ② `execution_port` 거부 스텁, ③ 기록형 fake 도달성 테스트. 콘솔 링크는 배타 소유하고, 포트 점유 시 fail-fast한다.

## §A. 접근 요약 (Context)

### §A.1 결정 검토 우선순위 (되돌리기 어려운 순 — 빌드 순서 아님)

사람 리뷰는 위에서부터 보라. 아래로 갈수록 기계적이다.

1. **무변이 보증의 형상** (§A.2 D-2 + REQ-MCP-007/010/011/012) — 사용자 대면 안전 계약. allowlist가 이름 상수인가 술어인가, 거부 스텁이 어디에 서는가는 나중에 바꾸기 가장 아픈 결정이다.
2. **콘솔 링크 조립 경로** (D-1) — 아키텍처 가드(REQ-MVP-029)와의 관계. 안 (a)/(b)는 가드 diff 유무가 갈린다.
3. **MCP 표면 형상** — 툴 스키마 변환 방식, 리소스 URI 설계. 클라이언트(Claude) UX에 직결된다.
4. **등록 아티팩트** (.mcp.json / README) — 사용자 손에 닿는 표면.
5. **기계적 배선** (엔트리포인트, 에러 매핑, 테스트 스캐폴딩) — 마지막에 보라. 교체 비용이 가장 낮다.

### §A.2 결정 등록부 — 해소 4건 / 조건부 2건 (재질의 금지 — 조건부는 판정 절차가 명시돼 있다)

| ID | 상태 | 결정 |
|---|---|---|
| **D-1** | **조건부 — M1 기계 판정** | **콘솔 링크 조립 경로.** 안 (a) `server.safety.bootstrap.build_console_stack` 재사용 **[권고]** — 아키텍처 가드 diff 0 (`server/safety/`는 `_ALLOWED_PREFIXES`에 이미 있다, spec F-4). 안 (b) `server/mcp/` 자체 조립 — **의도적 diff 2곳**(`test_architecture.py` 허용 목록 + `test_scene_boundary.py`의 "예외는 정확히 3건" 고정 테스트). 판정 기준 = ASSUMPTION-70: bootstrap 부수효과(백업 시도·`HealthMonitor`·감사 디렉토리·`_stop` 자원)가 stdio 프로세스 수명주기에 수용 가능한가. 수용 가능하면 (a) 확정, 아니면 (b) 전환. 판정 기록은 `progress.md §E.2`. |
| **D-2** | 해소 | **allowlist는 명시 이름 상수 + 전수 분할 테스트**(REQ-MCP-010/011). 술어(예: "이름이 find_/build_로 시작") 방식은 기각 — 상류 툴 추가가 **침묵 편입**되는 경로를 만든다. 이름 열거 + 분할 테스트는 형제 SPEC(SPATIAL·GROUPGEN 등) 머지 순간 깨져 편입/제외 결정을 **강제**한다. 이것은 버그가 아니라 설계된 감지기다. |
| **D-3** | **조건부 — M6 라이브 판정** | **룰북 리소스의 실효성.** ASSUMPTION-72가 NO-GO(클라이언트가 리소스를 사실상 안 읽음)면 Stage 2에서 읽기 툴 폴백(`get_rulebook_section` 류)을 검토한다. **본 SPEC에서는 기록만 한다** — 범위 확장 없음. |
| **D-4** | 해소 | **`ChatSession` 미사용.** 툴 조립은 `build_toolset`의 포트·라이브러리 인자만으로 한다(spec F-3·F-9). 세션 상태(`last_created` · 락)는 MCP 표면에 없다(spec §D). 세션 의존이 실측되는 툴은 정직한 축소로 제외(ASSUMPTION-73). |
| **D-5** | 해소 | **포트 점유 = fail-fast.** 대기/재시도 루프·포트 자동 변경은 만들지 않는다. `ReceivePortInUseError`(spec F-6)를 잡아 한국어 안내 + 비0 종료(REQ-MCP-008). 웹 앱과의 공존은 Stage 1 비목표(S2). |
| **D-6** | 해소 | **Lua 응답기 무변경.** v1.5.0 유지. v1.6.0은 INTROSPECT-001 예약 — 본 SPEC은 응답기 버전 축과 무접촉이므로 조율 절차 불요. |

### §A.3 PRESERVE 목록 (무변경 대상 — 읽기 import만)

- `server/orchestrator/tools.py` — 읽기 import만. allowlist 상수는 `server/mcp/` 소유다(tools.py에 추가하지 않는다).
- `server/bridge/**` · `server/safety/**` — 읽기 import만(안 (a)에서 `build_console_stack` 호출 포함).
- `server/looks/**` · `server/fx/**` · `server/scene/**` · `server/rulebook/assets/**` — 리소스 원본. 바이트 무변경.
- `console/lua/**` — 응답기 무변경(D-6).
- `server/web/**` — 무변경. MCP는 이 계층을 import하지 않는다(웹 프레임워크 의존 차단).

**변경 허용 파일**: `server/mcp/**`(신규) · `server/tests/test_mcp_*.py`(신규) · `pyproject.toml`(의존성 1건: `mcp`) · `.mcp.json`(신규) · `README.md`(절 추가). 그 외 전부 PRESERVE — 단, D-1이 (b)로 판정되면 `server/tests/test_architecture.py` + `server/tests/test_scene_boundary.py` 2곳의 의도적 diff가 추가로 허용된다(판정 기록 필수).

## §B. 마일스톤 (M1~M6)

### M1 — SDK 스파이크 + 조립 경로 판정 (cycle_type=tdd)

- **목표**: `mcp` 의존성 추가(버전 핀), 최소 stdio 서버(에코 툴 1종) 기동, `build_console_stack` 부수효과 실측.
- **판정**: ASSUMPTION-68(SDK 공존) · ASSUMPTION-70(bootstrap 부수효과) → D-1 확정. 판정 접두 행을 `progress.md §E.2`에 기록.
- **AC**: AC-MCP-001, AC-MCP-013
- **게이트**: 판정 2건이 기록되기 전에 M2 착수 금지.

### M2 — 무변이 코어: allowlist + 분할·도달성 테스트 + 거부 스텁 (cycle_type=tdd)

- **목표**: allowlist 이름 상수, 전수 분할 테스트(∪=TOOL_NAMES · ∩=∅), 호출 기록형 fake `ConsolePort`로 11종 전수 도달성 테스트, `RefusingExecutionPort` 구현·주입.
- **판정**: ASSUMPTION-69(후보 11종 무변이) · ASSUMPTION-73(세션 무의존). 도달이 실측된 툴은 정직한 축소로 제외하고 접두 행 기록.
- **AC**: AC-MCP-003, AC-MCP-004, AC-MCP-006

### M3 — MCP 툴 브리지 (cycle_type=tdd)

- **목표**: `ToolDefinition` → MCP tool 변환(무손실), tool call → `dispatch()` 배선, allowlist 밖 호출 구조화 거부, 콘솔 오프라인/타임아웃의 구조화 한국어 에러 매핑(원인 구분), 미연결 상태에서 list 표면 정상 동작.
- **AC**: AC-MCP-002, AC-MCP-005, AC-MCP-009

### M4 — 지식 리소스 + 등록 아티팩트 (cycle_type=tdd)

- **목표**: 룰북 5종 + 룩/FX/씬 라이브러리 MCP 리소스 노출(바이트 동일 사본), `.mcp.json` 작성, README 절(Claude Desktop 등록 + 배타 구동 제약).
- **AC**: AC-MCP-008, AC-MCP-011

### M5 — 프로토콜 스모크 + 경계 + 회귀 전체 그린

- **목표**: stdio 클라이언트 관통 스모크(initialize → tools/list → 읽기 툴 1종, fake link), 포트 점유 fail-fast 시나리오, 무포크 경계 검증, 무키 기동, 기존 전체 스위트 무손상.
- **AC**: AC-MCP-007, AC-MCP-010, AC-MCP-012, AC-MCP-014, AC-MCP-016

### M6 — 종단 라이브 검증 (실물 onPC + 실제 Claude 클라이언트 — 사람 관측)

- **목표**: 실물 onPC 연결 상태에서 Claude Code(또는 Desktop)로 등록·기동·대화 — 리그 판독 질문에 대한 유의미한 응답을 사람이 관측한다. 리소스 조회 실효성 관측 포함.
- **판정**: ASSUMPTION-71(클라이언트 기동) · ASSUMPTION-72(리소스 실효) · AC-MCP-015. 전 판정 접두 행 기록. 코드 변경 0 — 결함은 기록만 하고 별도 커밋(SCENE-001 M8 규율 계승).
- **AC**: AC-MCP-015

### 라이브 세션 회계

- **1회(M6)**. M1~M5는 콘솔 없이 완결된다(fake link). 콘솔 오프라인 우아한 성능저하(REQ-MCP-020/021) 덕에 M6 이전 실기 접속은 불요.

## §C. 기술 제약

- **stdio stdout 오염 금지** — stdio 전송에서 stdout은 프로토콜 채널이다. `print`/로그가 stdout에 나가면 클라이언트 파서가 깨진다. 로깅은 전부 stderr. 이 제약은 M1 에코 서버부터 테스트로 고정하라.
- **Python 3.11** + 공식 `mcp` SDK(FastMCP). 버전 핀은 M1에서 확정.
- **콘솔 왕복 타임아웃은 기존 `LinkTimeouts`**(exec 5s / ping 2s / state 5s)를 재사용 — MCP 계층에서 새 타임아웃 축을 발명하지 않는다.
- **단일 관문 불변식(REQ-MVP-029)** — `OscBridge` 생성은 승인 경로만(D-1). 가드 테스트가 정합 판정기다.
- **의존 방향** — `server/mcp/`는 `server/web/**`을 import하지 않는다(FastAPI 무의존 기동). 역방향(web → mcp)도 만들지 않는다.

## §D. @MX 태그 대상 (예상 — 실제 배치는 run-phase 확정)

- `server/mcp/` allowlist 상수 — `@MX:ANCHOR` (불변 계약: 전수 분할 + 상한 11종 + 확장은 SPEC 개정).
- `RefusingExecutionPort` — `@MX:NOTE` (2중 방벽의 두 번째 층이라는 의도; allowlist가 있어도 제거 금지 — 제거 시 REQ-MCP-007 위반).
- 포트 점유 fail-fast 분기 — `@MX:NOTE` (재시도 루프를 넣고 싶어질 자리 — D-5가 금지).

## §E. 테스트 스캐폴딩 계획

- `server/tests/test_mcp_allowlist.py` — 분할 테스트(REQ-MCP-011) + 도달성 테스트(REQ-MCP-012, 기록형 fake ConsolePort) + 거부 스텁(REQ-MCP-007).
- `server/tests/test_mcp_bridge.py` — 정의 변환 무손실(REQ-MCP-003/004) + allowlist 밖 거부(REQ-MCP-005) + 오프라인 구조화 에러(REQ-MCP-020/021).
- `server/tests/test_mcp_resources.py` — 리소스 목록/읽기 바이트 동일(REQ-MCP-014~016).
- `server/tests/test_mcp_smoke.py` — stdio 관통(REQ-MCP-022) + 포트 점유 fail-fast(REQ-MCP-008) + 무키 기동(REQ-MCP-019).
- 기존 fake 재사용: `server/tests/`의 기존 fake `ConsolePort` 계열을 우선 조사·재사용한다(M1). 재사용 불가 판정 시에만 신규 fake — 사유를 테스트 독스트링에 기록.

## §F. 병렬 가능성 분석 + 결정 기록

- **의존 사슬**: M1 → M2 → M3 → M5 → M6. M4는 M1 이후 M2/M3와 병렬 가능(파일 교집합: `server/mcp/` 내 리소스 모듈 vs 툴 브리지 모듈 — 서로소로 설계 가능).
- **권고**: **순차**(병렬 비채택). Tier M 규모에서 병렬 슬라이스 조율 비용(공유 계약 문면·브리프 작성)이 이득을 초과한다. M4를 병렬로 떼어낼 실익이 생기면 run-phase에서 오케스트레이터가 재평가하라.

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

- **권고: Mode 5 (solo-sequential sub-agent)**. 근거: 단일 도메인(backend/Python) · 신규 파일 위주(충돌 면적 최소) · 마일스톤 간 판정 의존(M1 판정이 M2 이후 형상을 결정). 팀/워크플로 fan-out 불요.

## §H. 교차 참조

- `spec.md` §B(REQ 정본) · §C(검증 천장 + ASSUMPTION) · §D(제외 범위).
- `acceptance.md` §C.0(역추적표) · §C.0a(마일스톤 배정표).
- `progress.md` §E.2 — 판정 접두 행 정본(REQ-MCP-023).
- `server/tests/test_architecture.py` — 단일 관문 가드(D-1 판정기).
- SPEC-COPILOT-SCENE-001 `plan.md` §A.3 — 정직한 축소 원칙(계승 출처).
