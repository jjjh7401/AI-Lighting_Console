# SPEC-COPILOT-SHOWUI-001 — 구현 계획 (plan)

status: completed (v0.2.1, 2026-07-23 — M1~M6 run-phase 완료 + sync 완료) · Tier L · 본 문서는 spec.md의 요구를 마일스톤으로 전개한다. 구현 코드 없음(작성 시점 기준 원문 보존).

## §A. 접근 요약 (Context)

- 기존 WS + OSC + `get_rig_context` 파이프라인 **전면 재사용**. 콘솔측 Lua 0건 변경.
- 실행은 전용 게이트 WS 메시지(`panel_execute`/`panel_stop`) → 커맨드 번들 → `gate.screen()` — research.md Recommendations 1의 option (b). 채팅 턴 락과 독립 직렬화(REQ-SHOWUI-013).
- 카탈로그는 `gate.state_port` 경유 읽기 전용 이벤트(research.md Recommendations 2). 영속화는 data dir JSON 원자적 쓰기(Recommendations 3). UI는 SettingsPanel/ApprovalCard 패턴 모델링(Recommendations 4), 2컬럼 레이아웃은 실제 CSS 변경(Recommendations 5).
- **마일스톤 순서는 결정-가역성 우선**: 변경 가능성이 높은 결정(데이터 모델·프로토콜 형상 M1, UX 플로우 M4)을 앞에 배치해 리뷰가 고변경 결정에 집중되도록 하고, 기계적 배선·테스트 마감은 뒤로 미룬다. 빌드 의존 체인: M1 → M2 → M3 → M4 → M5 → M6 (M4의 컴포넌트 작업은 M1 계약 동결 후 부분 병행 가능).

## §B. 마일스톤 (M1..M6)

### M1 — 프로토콜·데이터 모델 계약 (가장 가역성-민감; 최우선 리뷰 대상)

- 패널 항목 스키마 확정: `kind`(look/effect/sequence), 대상(`sequence no`/`executor no` — 실제 `no` 키잉), 동사 집합(`Go+`/`Off`), 어피어런스 컬러, 출처(pin/auto), append-only 순서.
- 신규 client 타입: `panel_execute`, `panel_stop`, `panel_pin`, `panel_unpin`, `panel_catalog_request`. 신규 server 이벤트: `panel_catalog`, `panel_item_state`, 패널 busy 응답. 양측 allowlist + reducer/handler 동시 등록(REQ-SHOWUI-014).
- `UiState.panel` 필드 신설 + `reduceServerEvent` case 추가. `PROTOCOL_VERSION = 1` 유지.
- 파일: `ui/src/protocol.ts`, `ui/src/protocol.test.ts`, `server/web/messages.py`, `server/tests/test_web_messages.py`, `server/web/PROTOCOL.md`.

### M2 — 서버 패널 스토어 + 카탈로그 + 핀 시드

- 신규 `server/web/panel.py`: 핀 스토어(data dir 전용 JSON, temp+`os.replace` 원자적 쓰기, 자격 증명 배제), 카탈로그 빌더(`_rig_section`/`_rig_object` 재사용, `gate.state_port` 경유, 실패 사유 2종 구분 유지), unpin 처리(v1 편집 범위 전부).
- `_last_created` 핀 시드 노출(session.py) — 시드 부재 시 명시적 오류 회신.
- `server/orchestrator/tools.py`의 섹션 헬퍼 재사용을 위한 순수 함수 분리(동작 무변경 — 기존 도구 테스트 그린 유지가 조건).
- 파일: `server/web/panel.py`(신규), `server/orchestrator/tools.py`(헬퍼 분리만), `server/web/session.py`, `server/tests/test_web_panel.py`(신규).

### M3 — 게이트 경유 실행 핸들러

- `/ws` 루프에 패널 메시지 라우팅 추가(app.py). execute/stop → 번들 구성 → `gate.screen()` → 기존 실행 포트. clearance 1:1 감사 계약 유지.
- 1-in-flight 직렬화 + busy 응답(REQ-SHOWUI-011), stop 우선 처리(REQ-SHOWUI-012), 채팅 턴 락 비점유(REQ-SHOWUI-013).
- All Off = bounded enumeration 번들(추적 중 running executor 개별 `Off Executor N`; 광역 `Thru`/`*` 금지 — REQ-SHOWUI-025/026).
- 승인 보류 번들의 ApprovalCard 배선(approval_bridge 재사용 — 모델: serve.py:329-338), LiveLock/health/executions_blocked 결과 처리.
- 파일: `server/web/app.py`, `server/web/panel.py`, `server/web/approval_bridge.py`(배선만), `server/tests/test_web_panel_execute.py`(신규), `server/tests/test_web_e2e.py`(확장), `server/tests/test_architecture.py`(그린 유지 필수).

### M4 — UI 패널 (UX 플로우; 두 번째 고변경 결정 묶음)

- `ShowPanel.tsx` + `PanelTile.tsx` 신규: Live Rail 해부구조, arm→fire(파괴적 한정), `statusClass` + `createDecisionGuard` 재사용, RUN/OFF 배지, 차단/제안 상태 렌더.
- 2컬럼 접기형 레이아웃(App.tsx + styles.css — `.app` 860px 캡 해제/확장, chat-first 보존), 채팅 항목에 "패널에 추가" 버튼(ChatView.tsx), 소켓 훅 send 헬퍼(useCopilotSocket.ts).
- All Off 고정 코너 컨트롤(bounded 범위 라벨/한계 표기 — design.md §6).
- 파일: `ui/src/components/ShowPanel.tsx`(신규), `ui/src/components/PanelTile.tsx`(신규), `ui/src/App.tsx`, `ui/src/styles.css`, `ui/src/components/ChatView.tsx`, `ui/src/useCopilotSocket.ts`, 컴포넌트/순수 vitest 파일(신규).

### M5 — Fail-closed 하드닝

- WS 종료 시 패널 running 상태 소거(`disconnected` reducer 확장), 재접속 시 카탈로그+status 재동기화 요청(REQ-SHOWUI-015/016).
- health/executions_blocked 엣지 렌더, 모달-부재·그리드 안정성(append-only) 검증 마감.
- 파일: `ui/src/useCopilotSocket.ts`, `ui/src/protocol.ts`(disconnect reducer), 관련 테스트.

### M6 — 전체 그린 + 라이브 E2E + 문서 마감

- pytest 전체 + vitest 전체 그린(AC-SHOWUI-012). 실제 onPC 2.4.2 라이브 체크리스트 수행(AC-SHOWUI-013/014 — acceptance.md §C LIVE 항목).
- `server/web/PROTOCOL.md` 최종화. 라이브 증적은 progress.md §E.2에 기록(run-phase, manager-develop 소관).

## §C. 기술 제약

1. **신규 런타임 의존성 0.** UI는 기존 React+Vite+Vitest, 서버는 FastAPI+python-osc+stdlib(`json`, `os.replace`). 라이브러리 추가 제안은 스코프 이탈로 재리뷰 대상.
2. **@MX:ANCHOR 경계 (위반 불가)**:
   - `server/safety/gate.py:260-264` — 스크리닝 경로는 정확히 하나. 패널 실행은 `gate.screen()` 진입만 허용, 제2 진입 금지.
   - `server/web/settings_api.py:104-112` — REST 라우터는 OSC 송신 표면 import 금지. 따라서 실행은 게이트 WS 핸들러 전용, 카탈로그/영속은 콘솔 표면 무접촉 seam.
   - `server/bridge/osc.py:5-16` — 유일 OSC 송신 표면, 프로덕션 호출자는 게이트 executor뿐. 무변경.
   - `console/lua/copilot_responder.lua` 슬롯 해석 계약(responder.lua:189-311) — 무변경 소비.
3. **프로토콜 규율**: `PROTOCOL_VERSION = 1` 고정, 신규 타입은 양측 allowlist + reducer/handler 동시 등록. 미등록 타입 처리는 **측별로 상이**하다 — TS 클라이언트는 null-drop(`parseServerEvent` → `null`, protocol.ts:128-129), 서버는 `ProtocolError` 명시 거부 → error 이벤트(messages.py:46-50, app.py:230-234); 한쪽 allowlist 누락 시 그 측 계약대로 기능이 조용히(TS) 또는 오류로(서버) 증발(research.md Risk 11, REQ-014). AC-SHOWUI-001 패리티 테스트가 방어선.
4. **안전 의미론 무변경 계승**: lock-FIRST 재확인, 위험 번들 사전 백업 fail-closed, deny-all 기본 승인 포트, 미확인 이력 자동 재전송 금지.
5. **effective 설정 규율**: `osc_slot`/`receive_port`/`reply_port`는 `/api/settings`·status 이벤트에서만 읽기 — 하드코딩 금지(site 값 드리프트, research.md Risks 5-6).

## §D. 테스트 스캐폴딩 계획 (기존 관례 준수)

- **UI (vitest)**: DOM 없는 순수 함수 테스트(`protocol.test.ts` 패턴)로 신규 빌더/파서/reducer 커버. 가드-테스트 컴포넌트 패턴(`ApprovalCard.test.tsx`)으로 arm→fire·one-shot 가드 커버. `npm test`(vitest run).
- **서버 (pytest)**: autouse 인메모리 keyring(`server/tests/conftest.py`), 메시지 스키마 테스트(`test_web_messages.py` 확장), 게이트 불변식 테스트(`test_safety_gate.py`·`test_safety_lock_monitor.py`는 무변경 그린), import 경계 테스트(`test_architecture.py` — 신규 panel 모듈의 OSC 표면 미접촉을 기계 검증), E2E 왕복 템플릿(`test_web_e2e.py`, `test_web_approval_bridge.py`).
- **신규 테스트 파일**: `server/tests/test_web_panel.py`, `server/tests/test_web_panel_execute.py`, `ui/src/components/ShowPanel`/`PanelTile` 테스트, protocol 패널 case 테스트.
- **run-phase 자기 검증 커맨드(예상)**: `pytest`(전체), `npm test`, `grep -rn "bridge.osc\|from server.bridge" server/web/panel*.py`(0건 기대), `grep -rn "window.confirm" ui/src/`(0건 기대).

## §E. 리스크

| # | 리스크 | 완화 |
|---|---|---|
| R1 | 게이트 인접 작업 — 실수 하나가 제2 스크리닝 경로를 만듦 | 패널 모듈의 OSC import 금지 + 실행은 `gate.screen()` 단일 진입 + `test_architecture.py` 기계 검증(AC-006) |
| R2 | 프로토콜 측별 미등록 처리(TS null-drop / 서버 ProtocolError) — allowlist 한쪽 누락 시 그 측 계약대로 기능 소실 | 양측 패리티 테스트(AC-001), PROTOCOL.md 동시 갱신 |
| R3 | tools.py 헬퍼 분리가 LLM 도구 동작을 흔들 위험 | 순수 함수 분리만(동작 무변경), 기존 도구 테스트 그린 유지 조건 |
| R4 | busy/stop 스케줄링 복잡도 | 1-in-flight + stop 우선의 최소 설계, pytest 동시성 테스트(AC-009) |
| R5 | 레이아웃 회귀(860px 캡 해제) | 접기형 기본 + chat-first 보존, vitest + 수동 시각 점검 |
| R6 | reply-port drift 시 패널 피드백이 걸린 듯 보임(알려진 라이브 서명) | health/executions_blocked 상시 표면화(AC-014 LIVE) |
| R7 | All Off bounded 한계 오해(전체 정지로 오인) | UI 한계 표기(design.md §6) + spec.md §A 명시 |

## §F. 결정 기록 (DP1 해소 — 재질의 금지)

| 결정 | 내용 | 반영 위치 |
|---|---|---|
| DP1-① 페이더 | v1 제외, 후속 SPEC 이연. 초안 REQ-SHOWUI-021 삭제 | spec.md §D "페이더 컨트롤" |
| DP1-② All Off | bounded enumeration — 추적 running executor 개별 `Off Executor N`, 광역 `Thru`/`*` 금지, 한계 명시 | spec.md §A·REQ-SHOWUI-025/026, design.md §6 |
| DP1-③ 편집 모드 | v1 unpin 전용, rename/reorder 이연, append-only 순서 | REQ-SHOWUI-004/023/005, spec.md §D |
| 실행 라우팅 | 전용 게이트 WS 핸들러(option b), 채팅 경유 아님 | REQ-SHOWUI-006/013 |
| frontmatter 참조 | `related_specs`(비차단) — MVP-001 `in-progress`로 인한 pre-flight 차단 회피 | spec.md frontmatter·§C |
