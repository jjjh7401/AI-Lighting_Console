---
id: SPEC-COPILOT-MCP-001
title: "읽기 전용 MCP 서버 — Claude 클라이언트가 콘솔을 읽는다 (Stage 1)"
version: "0.1.0"
status: draft
created: 2026-08-04
updated: 2026-08-04
author: manager-spec
priority: P1
phase: "접속 계층 Stage 1 — 읽기 전용 MCP 서버 (쓰기 서버는 Stage 2 이연)"
module: "server/mcp/ (신규), .mcp.json (신규), README.md, pyproject.toml (의존성 1건)"
lifecycle: spec-anchored
tags: "mcp, stdio, read-only, claude-client, tool-allowlist, zero-mutation, osc-bridge, console-link, rulebook-resources, port-exclusive, stage-1"
tier: M
related_specs: [SPEC-COPILOT-MVP-001, SPEC-COPILOT-DEPLOY-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-FXLIB-001, SPEC-COPILOT-SCENE-001, SPEC-COPILOT-PRECHK-001]
---

# SPEC-COPILOT-MCP-001 — 읽기 전용 MCP 서버 (Stage 1)

> **이 SPEC은 앱을 MCP(Model Context Protocol) 서버로 전환하는 1단계다.** Claude 클라이언트(Claude Code / Claude Desktop)가 기존 OSC 링크를 통해 grandMA3 콘솔을 **판독**한다 — 콘솔을 변이시키는 툴은 **하나도** 노출하지 않는다. 사용자 목표: "Claude와 대화하며 콘솔 상태를 읽고 이해한다." 쓰기 툴(`run_commands`, `instantiate_*`, `compile_scene`, `deploy_plugin` 등)은 명시적 비목표이며 Stage 2의 몫이다(§D).
>
> **아키텍처 전제**: 기존 툴 레지스트리(`server/orchestrator/tools.py` `build_toolset`)와 콘솔 통신 계층(`server/bridge/` + `server/safety/`)을 **재사용**한다. 툴 로직의 사본·포크는 금지된다. LLM 호출은 없다 — Claude 클라이언트가 브레인이고, 이 서버는 콘솔로 통하는 읽기 전용 감각 기관이다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-08-04 | manager-spec | 최초 작성 (draft, Tier M). 출처: 사용자 승인 임무(Stage 1 읽기 전용 MCP 서버) + 오케스트레이터 조사(툴 레지스트리·브리지 계층·아키텍처 가드·조립 루트). 저작 중 실측 정정 2건: ① 임무 브리프의 "20 툴 / 후보 12종"은 형제 branch 기준 — **본 branch(base 3176900)는 TOOL_NAMES 18종 · 읽기 전용 후보 11종**(`get_spatial_context`·`arrange_fixtures` 부재, §C.1). ② 전역 ASSUMPTION 카운터는 미머지 형제 SPEC들이 46~67을 소비 — **본 SPEC은 68부터**(§C.2). REQ **23건** · AC **16건** · ASSUMPTION **6건(68~73)** · Out of Scope **10건** · clarification 마커 **0건** · 라이브 세션 **1회(M6)**. 아티팩트 4종(spec·plan·acceptance·progress) 동시 생성. |

## A. 개요

지금 이 앱은 FastAPI 웹 앱이다: 사용자가 채팅 UI에 지시를 쓰면 서버측 LLM(Gemini)이 툴을 호출해 콘솔을 읽고 쓴다. 본 SPEC은 그 **읽기 절반**을 MCP 표면으로 여는 것이다 — Claude 클라이언트가 stdio로 이 서버에 붙어, 기존 툴 레지스트리의 읽기 전용 부분집합을 직접 호출한다. 서버측 LLM은 개입하지 않는다.

세 가지가 새로 생긴다:

1. **`server/mcp/` 패키지** — stdio MCP 서버 엔트리포인트(`python -m server.mcp`). 기존 `ToolRegistry`의 `definitions()`/`dispatch()`를 재사용해 읽기 전용 allowlist 툴만 MCP tool로 노출한다.
2. **MCP 리소스** — 룰북 자산 5종(`server/rulebook/assets/v2.4.2/*.md`)과 룩/FX/씬 내장 라이브러리. MCP는 시스템 프롬프트를 주입할 수 없으므로, 콘솔 어휘·문법 지식은 리소스로 노출해 클라이언트가 조회한다.
3. **등록 아티팩트** — 저장소 `.mcp.json`(Claude Code) + README의 Claude Desktop 등록 절차.

### 사전 확정 사실 (사용자 승인 범위 S1~S4 — 재질의 금지)

| # | 확정 내용 |
|---|---|
| **S1** | **읽기 전용.** 콘솔을 변이시키는 툴은 전면 제외. 쓰기 서버는 Stage 2 후속 SPEC의 몫이다. |
| **S2** | **링크 배타 소유.** MCP 서버가 구동 중이면 수신 포트(기본 9000)를 배타 점유한다 — 웹 앱과의 동시 구동은 지원하지 않는다. |
| **S3** | **LLM 키 불요.** 서버는 LLM을 호출하지 않는다. Claude 클라이언트가 브레인이다. |
| **S4** | **공식 Python MCP SDK + stdio 전송.** Claude Code는 `.mcp.json`, Claude Desktop은 `claude_desktop_config.json`으로 등록한다. |

### 툴 전수 분할 — 본 branch(base 3176900) TOOL_NAMES 18종 기준

읽기 전용 **후보 11종** (M2 도달성 판정으로 확정 — §B.3):

| 툴 | 콘솔 접촉 | 근거 |
|---|---|---|
| `query_state` | 읽기 | 응답기 state 판독 |
| `get_rig_context` | 읽기 | 오브젝트 트리 요약 판독 |
| `find_looks` / `find_fx` / `find_scene` | 무접촉 | 라이브러리 매칭 (순수) |
| `precheck_patch` | 읽기 | 패치 사전 점검 (state/property 판독) |
| `preshow_check` | 핑만 | 라이브니스 왕복 (무해 발화 — 변이 아님) |
| `build_patch_sheet` / `build_cue_sheet` / `build_preset_list` | 읽기 | 판독 기반 시트 생성 |
| `plan_executor_layout` | 무접촉 | 순수 배치 계획 |

변이 **제외 7종**: `run_commands`(임의 콘솔 발화) · `deploy_plugin`(플러그인 배포) · `instantiate_look` · `instantiate_fx` · `compile_scene`(콘솔 오브젝트 생성) · `prepare_busking` · `prepare_songcue`(생성 경로를 포함한 준비 위저드).

11 + 7 = 18 — 전수 분할이며, 이 분할 자체가 테스트로 고정된다(REQ-MCP-011). `get_spatial_context`·`arrange_fixtures`는 **이 branch에 존재하지 않는다**(미머지 형제 SPEC 소유 — §C.1, §D).

## B. 요구사항 (GEARS)

### B.1 서버 표면과 툴 브리지

- **REQ-MCP-001** (Ubiquitous): `server/mcp/` 패키지는 stdio 전송 MCP 서버 엔트리포인트를 제공해야 하며, `python -m server.mcp`로 기동되어야 한다.
- **REQ-MCP-002** (Ubiquitous): 서버는 기존 `build_toolset(...)`이 반환한 `ToolRegistry`의 `definitions()`(provider 중립 JSON-schema)와 `dispatch()`를 재사용해야 한다. 툴 로직의 사본·포크는 금지된다.
- **REQ-MCP-003** (Where): **Where** MCP 클라이언트가 `tools/list`를 요청하면, 서버는 읽기 전용 allowlist(§B.3)에 속한 툴 정의만 반환해야 한다.
- **REQ-MCP-004** (When): **When** 클라이언트의 tool call이 도착하면, 서버는 allowlist 검사를 통과한 이름만 `dispatch()`로 전달하고 그 결과 페이로드를 MCP 응답으로 무손실 반환해야 한다.
- **REQ-MCP-005** (When — 비정상 감지): **When** allowlist 밖 이름의 tool call이 감지되면(레지스트리에 실존하는 변이 툴 포함), 서버는 실행 없이 한국어 사유를 포함한 구조화 거부를 반환해야 한다.

### B.2 콘솔 링크 조립과 소유권

- **REQ-MCP-006** (Ubiquitous): MCP 프로세스는 자체 `OscBridge` + `ConsoleLink`를 단일 관문 불변식(REQ-MVP-029) 위반 없이 조립해야 한다 — 조립은 `server.safety.bootstrap` 경유이거나, 아키텍처 가드(`server/tests/test_architecture.py`의 `_ALLOWED_PREFIXES` + 명명 예외)에 **의도적 diff**로 편입된 승인 경로여야 한다(plan.md §A.2 D-1).
- **REQ-MCP-007** (Ubiquitous): 툴 레지스트리 조립 시 `execution_port`(필수 인자)에는 어떤 콘솔 발화도 수행하지 않는 **거부 스텁**(RefusingExecutionPort)을 주입해야 한다 — allowlist 필터와 독립인 2중 방벽이다.
- **REQ-MCP-008** (When — 비정상 감지): **When** 수신 포트가 이미 점유되어 있으면(웹 앱 구동 중 등), 서버는 stderr에 한국어 안내(원인 + 웹 앱 종료 후 재시도)를 내고 0이 아닌 종료 코드로 기동을 중단해야 한다.
- **REQ-MCP-009** (Ubiquitous — shall not): 서버는 웹 앱과 콘솔 링크를 공유하거나 동시 구동하는 어떤 메커니즘도 제공하지 않아야 한다(Stage 1 배타 소유 — S2).

### B.3 무변이 보증

- **REQ-MCP-010** (Ubiquitous): 읽기 전용 allowlist는 `server/mcp/` 소유의 명시적 이름 상수로 존재해야 하며, §A의 후보 11종을 **상한**으로 한다. M2 도달성 판정(REQ-MCP-012)에서 execute/deploy 도달이 실측된 툴은 제외한다 — 축소는 SPEC 개정 없이 허용되고(정직한 축소 원칙), 확장은 SPEC 개정을 요구한다.
- **REQ-MCP-011** (Ubiquitous): allowlist ∪ 제외목록 = `TOOL_NAMES`(전수) · allowlist ∩ 제외목록 = ∅ — 이 분할이 테스트로 고정되어야 한다. 상류에 툴이 추가되면(형제 SPEC 머지 등) 분할 테스트가 깨져 편입/제외 결정을 강제한다 — 침묵 편입은 없다.
- **REQ-MCP-012** (Ubiquitous): 기계적 도달성 테스트가 존재해야 한다 — allowlist의 각 툴을 호출 기록형 fake `ConsolePort`로 대표 인자 호출했을 때 `execute`/`deploy_plugin` 호출이 **0건**임을 검증한다(ASSUMPTION-69의 판정기).
- **REQ-MCP-013** (Ubiquitous — shall not): 서버는 콘솔 상태를 변이시키는 어떤 MCP 툴·리소스·프롬프트도 노출하지 않아야 한다.

### B.4 지식 리소스

- **REQ-MCP-014** (Ubiquitous): 룰북 자산 5종(`server/rulebook/assets/v2.4.2/`: `00_grammar.md` · `10_object_model.md` · `20_korean_terms.md` · `30_plugin_patterns.md` · `31_choreography_patterns.md`)을 읽기 전용 MCP 리소스로 노출해야 한다.
- **REQ-MCP-015** (Ubiquitous): 룩/FX/씬 내장 라이브러리 자산(`server/looks/library` · `server/fx/library` · `server/scene/library`)을 읽기 전용 MCP 리소스로 노출해야 한다.
- **REQ-MCP-016** (Ubiquitous): 리소스 응답 내용은 디스크 자산의 무변경 사본이어야 하며, 자산 파일 자체는 PRESERVE다(plan.md §A.3).

### B.5 설정 · 등록 · 키

- **REQ-MCP-017** (Ubiquitous): OSC host/포트 설정은 기존 설정 계층(`BridgeConfig` 기본값 + 기존 설정 소스)을 재사용해야 하며, MCP 전용 신규 설정 파일을 도입하지 않는다.
- **REQ-MCP-018** (Ubiquitous): 저장소 루트 `.mcp.json`에 Claude Code 등록 항목을 제공하고, README에 Claude Desktop(`claude_desktop_config.json`) 등록 절차와 배타 구동 제약(S2)을 문서화해야 한다.
- **REQ-MCP-019** (Ubiquitous — shall not): 서버는 LLM API 키를 요구하거나 LLM 호출을 수행하지 않아야 한다.

### B.6 우아한 성능저하

- **REQ-MCP-020** (When — 비정상 감지): **When** 콘솔이 오프라인이거나 응답기 왕복이 타임아웃되면, 해당 tool call은 원인을 구분한(타임아웃/미연결) 구조화 한국어 에러 페이로드를 반환해야 하고, 서버 프로세스는 계속 살아 있어야 한다.
- **REQ-MCP-021** (While): **While** 콘솔 미연결 상태, `tools/list` · `resources/list` · 리소스 읽기는 정상 동작해야 한다 — 콘솔 왕복은 tool call 시점에만 발생한다.

### B.7 검증 규율

- **REQ-MCP-022** (Ubiquitous): MCP 프로토콜 스모크 테스트가 존재해야 한다 — stdio 클라이언트로 initialize → `tools/list` → 읽기 툴 1종 호출(fake link 경유)을 관통한다.
- **REQ-MCP-023** (Ubiquitous): 라이브 판정 기록 의무 — 실물 onPC + 실제 Claude 클라이언트 검증(M6)의 판정은 `progress.md §E.2`에 행두 접두 행(`GO:` / `NO-GO:` / `CONDITION_NOT_MET:` / `INCONCLUSIVE:`) 형식으로 기록되어야 한다(SCENE-001 REQ-SCENE-021 계승 — 한 판정당 1행, 대상은 `ASSUMPTION-nn` 또는 `AC-MCP-nnn`).

## C. 환경 및 전제 (Environment / Assumptions)

### C.1 검증 천장 — 기계로 확인된 사실 (2026-08-04, 본 branch 실측)

아래는 이 세션에서 명령 실행으로 확인된 사실이다. 줄 번호는 실측 시점 좌표이며 썩을 수 있다 — 앵커는 심볼/절 이름이 정본이다.

| # | 사실 | 실측 |
|---|---|---|
| F-1 | `TOOL_NAMES`는 **18종** — 임무 브리프의 "20종"은 형제 branch 기준 | `tools.py` 튜플 파싱 결과 `18` (§A 분할표와 일치) |
| F-2 | `get_spatial_context`는 본 branch에 **부재** | `grep -c` = `0` (`server/orchestrator/tools.py`) |
| F-3 | `build_toolset`은 `execution_port`가 **키워드 필수 인자** — 거부 스텁 주입 지점이 시그니처에 이미 존재 | `tools.py` `def build_toolset(*, execution_port: CommandExecutionPort, ...)` 실측 |
| F-4 | 단일 관문 가드: `_ALLOWED_PREFIXES = ("server/bridge/", "server/safety/", "server/tests/")` + 명명 예외 3건, 예외 목록은 형제 테스트가 **정확히 3건**으로 고정 | `server/tests/test_architecture.py` + `server/tests/test_scene_boundary.py` 실측 |
| F-5 | `bootstrap.py`의 web 의존은 `launcher.PortInUseError` 1건이고 `launcher.py`는 FastAPI-free | `grep -c "fastapi\|FastAPI" server/web/launcher.py` = `0` |
| F-6 | 포트 점유 감지 채널 존재 — `ReceivePortInUseError`가 `server/bridge/osc.py`에 실존 | `bootstrap.py` import 문 실측 |
| F-7 | 룰북 자산은 정확히 5종 | `ls server/rulebook/assets/v2.4.2/` 실측 |
| F-8 | `mcp` 패키지 미설치 | `grep -n "mcp" pyproject.toml` 매치 0 (exit 2) |
| F-9 | 웹 앱의 레지스트리 조립 지점은 `server/web/session.py`의 `ChatSession`(`build_toolset(` 호출) — MCP는 이 경로를 쓰지 않는다 | `grep` 실측 |
| F-10 | Lua 응답기는 v1.5.0이며 본 SPEC은 **무변경** — v1.6.0은 SPEC-COPILOT-INTROSPECT-001(미머지)이 예약 | 에이전트 메모리 + `console/lua/copilot_responder.lua` |

### C.2 미검증 전제 (ASSUMPTION — 전역 카운터: 미머지 형제 SPEC들이 46~67 소비(INTROSPECT 46~52 · SPATIAL 53~60 · GROUPGEN 61~67), 본 SPEC은 **68부터**)

각 전제는 판정 마일스톤과 NO-GO 시 경로를 갖는다. 판정 기록은 `progress.md §E.2` 접두 행이 정본이다(REQ-MCP-023).

- **ASSUMPTION-68** — 공식 Python MCP SDK(`mcp` 패키지, FastMCP, stdio)가 Python 3.11 + 기존 의존성과 충돌 없이 설치·구동된다. **[기계 판정 — M1]** NO-GO 시: 버전 핀 조정 → 그래도 불가면 SPEC 중단 후 사용자 보고(대안 전송/SDK는 재승인 사안).
- **ASSUMPTION-69** — 읽기 전용 후보 11종 각각의 dispatch 경로가 `ConsolePort.execute`/`deploy_plugin`에 도달하지 않는다. 특히 `preshow_check`(핑/왕복만이라는 전제) · `precheck_patch` · `build_*` 시트류가 실측 대상이다. **[기계 판정 — M2 도달성 테스트(REQ-MCP-012)]** NO-GO 시: 해당 툴을 allowlist에서 제외(정직한 축소 — REQ-MCP-010, SPEC 개정 불요).
- **ASSUMPTION-70** — `build_console_stack` 재사용(plan.md D-1 안 (a))이 MCP stdio 프로세스에서 수용 가능한 부수효과만 갖는다(포트 바인드는 의도된 필수; 백업 시도·모니터·감사 로그 디렉토리 생성이 stdio 수명주기와 충돌하지 않음). **[기계 판정 — M1]** NO-GO 시: D-1 안 (b)로 전환(신규 조립 경로 + 아키텍처 가드 의도적 diff 2곳).
- **ASSUMPTION-71** — Claude 클라이언트(Claude Code `.mcp.json` / Claude Desktop)가 이 저장소의 venv Python으로 stdio 엔트리포인트를 기동할 수 있다(PATH·venv 경로 전제). **[라이브 판정 — M6]** NO-GO 시: 절대 경로 명시/래퍼 스크립트로 등록 아티팩트 보정(코드 무변경).
- **ASSUMPTION-72** — MCP 리소스로 노출한 룰북/라이브러리를 Claude 클라이언트가 실제로 조회·활용한다(리소스 소비는 클라이언트 재량 — 자동 주입이 아니다). **[라이브 판정 — M6]** NO-GO 시: 기록만 하고 Stage 2에서 읽기 툴 폴백 검토(plan.md D-3 — 본 SPEC 범위 밖).
- **ASSUMPTION-73** — 읽기 전용 툴들은 `ChatSession` 상태(`last_created` · 락) 없이 유의미하게 동작한다 — `build_toolset` 시그니처가 요구하는 것은 포트·라이브러리뿐이다(F-3·F-9). **[기계 판정 — M2]** NO-GO 시: 세션 의존이 실측된 툴을 allowlist에서 제외(정직한 축소).

## D. 제외 범위 (Out of Scope)

### Out of Scope — 콘솔 변이 툴 전부 (Stage 2)
- `run_commands` · `deploy_plugin` · `instantiate_look` · `instantiate_fx` · `compile_scene` · `prepare_busking` · `prepare_songcue`는 노출하지 않는다. 쓰기 MCP 서버(안전 게이트 경유 변이)는 Stage 2 후속 SPEC의 몫이다.

### Out of Scope — 웹 앱과의 동시 구동 · 링크 공유
- 수신 포트 멀티플렉싱, 링크 프록시, 웹 앱과의 공존 데몬은 만들지 않는다. 포트 점유 시 명확한 기동 실패가 전부다(REQ-MCP-008, S2).

### Out of Scope — Lua 응답기 변경
- `console/lua/copilot_responder.lua`는 v1.5.0 그대로다. v1.6.0은 SPEC-COPILOT-INTROSPECT-001이 예약했다 — 본 SPEC은 응답기 동사를 추가·변경하지 않는다.

### Out of Scope — 신규 콘솔 판독 능력
- 기존 툴이 읽지 못하는 것을 새로 읽게 만들지 않는다. 본 SPEC은 **노출**이지 **확장**이 아니다.

### Out of Scope — stdio 외 전송
- HTTP/SSE/WebSocket 전송, 원격 접속, 다중 클라이언트 동시 세션은 다루지 않는다.

### Out of Scope — LLM 호출 · 서버측 프롬프트 엔지니어링
- 서버는 LLM을 호출하지 않고 API 키를 다루지 않는다(S3). 시스템 프롬프트 주입 대체 장치도 만들지 않는다 — 지식 전달은 리소스 노출(REQ-MCP-014/015)까지다.

### Out of Scope — 본 branch에 없는 형제 SPEC 툴
- `get_spatial_context`(SPATIAL-001) · `arrange_fixtures` 등 미머지 형제 branch의 툴은 다루지 않는다. 머지 후 편입 여부는 분할 테스트(REQ-MCP-011)가 강제하는 별도 결정이다.

### Out of Scope — 세션 영속 상태
- `ChatSession`의 `last_created` · 락 · 대화 이력은 MCP 표면에 노출하지 않는다. MCP 세션 간 서버측 상태 유지도 없다.

### Out of Scope — SafetyGate 확장 · 쓰기 안전 장치 신규 설계
- 읽기 전용이므로 게이트 정책·룰셋은 건드리지 않는다. Stage 2가 다룰 영역이다.

### Out of Scope — UI 표면 변경
- 웹 앱 UI(`server/web/**` 프런트 포함)는 무변경이다. README 절 추가만 허용된다.

## E. 참조

- 임무 브리프(사용자 승인 범위 + 오케스트레이터 조사) — 본 SPEC §A·§C.1로 흡수, 실측 정정 2건 반영(F-1·F-2, ASSUMPTION 카운터).
- `plan.md` — 결정 등록부(D-1~D-6) · 마일스톤(M1~M6) · PRESERVE 목록.
- `acceptance.md` — GWT 시나리오 5건 · AC 16건 · 역추적표.
- `progress.md` — §0 인수인계 · §E 판정 기록(정본).
- 선행 규율 계승: SPEC-COPILOT-SCENE-001(판정 어휘 접두 행 · 정직한 축소 원칙), SPEC-COPILOT-MVP-001(REQ-MVP-029 단일 관문).
