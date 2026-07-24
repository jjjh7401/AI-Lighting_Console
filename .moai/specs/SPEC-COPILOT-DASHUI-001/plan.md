# SPEC-COPILOT-DASHUI-001 — 구현 계획 (plan)

status: draft (v0.1.0, 2026-07-24) · Tier L · 본 문서는 spec.md의 요구를 마일스톤으로 전개한다. 구현 코드 없음.

## §A. 접근 요약 (Context)

- **본 브랜치의 SHOWUI M1~M3 기반 위에 쌓는다**: 동결된 패널 프로토콜 계약 + `server/web/panel.py`(카탈로그/핀/membership/`PanelRuntime`) + app.py `/ws` 패널 라우팅. 신규 실행 경로 0 — 발화는 전부 기존 `panel_execute`/`panel_stop` → `gate.screen()`.
- **정보(읽기 전용) 카탈로그는 신규 additive 이벤트**로 분리한다: 발화 카탈로그(`panel_catalog`, `PANEL_CATALOG_SECTIONS` @MX:ANCHOR)는 "발화 가능한 것들의 닫힌 집합"이라는 의미를 유지하고, 정보 풀(그룹/프리셋/플러그인/픽스처 요약)은 새 `dash_catalog` 계열 이벤트로 나른다(spec.md REQ-DASHUI-007).
- **매크로 발화는 기존 닫힌 집합의 additive 확장**: `PANEL_TARGET_KINDS`(messages.py:61, protocol.ts:80)에 `macro` 추가 + `playback_command` 빌더에 룰북 검증 실행 형태(`Macro <no>`) 추가. 닫힌 집합·단일 양의 정수 속성은 유지(광역 타깃 구성 불가 속성 보존).
- **마일스톤 순서는 결정-가역성 우선**: 변경 가능성이 높은 결정(프로토콜·데이터 모델 M1, 레이아웃/UX 플로우 M3~M4)을 앞에 배치하고, 기계적 배선·테스트 마감을 뒤로 미룬다. 빌드 의존 체인: M1 → M2 → M3 → M4 → M5 → M6 (M3의 레이아웃 작업은 M1 계약 동결 후 M2와 부분 병행 가능).

## §B. 마일스톤 (M1..M6)

### M1 — 프로토콜·데이터 모델 계약 (가장 가역성-민감; 최우선 리뷰 대상)

- 신규 client 메시지: `dash_catalog_request`(무페이로드). 신규 server 이벤트: `dash_catalog` — `sections: DashSection[]`, DashSection = `{name, status(ok|path_not_resolved|console_unreachable), truncated?, drilldown_capped?, contents_unavailable?, items}`, DashItem = `{no, name, appearance?|null, meta?}` — **발화 target_kind를 나르지 않는 정보 전용 형상**(REQ-DASHUI-007).
- `PANEL_TARGET_KINDS`에 `macro` additive 추가(양측 allowlist 동시), `playback_command`에 매크로 실행 형태 추가 — 닫힌 집합 유지, 미검증 동사·광역 타깃은 여전히 구성 불가.
- `UiState`에 `dash` 필드 신설 + `reduceServerEvent` case + `clearOnDisconnect` 확장(휘발 상태 소거 범위 정의). `PROTOCOL_VERSION = 1` 유지, 양측 allowlist + reducer/handler 동시 등록(미등록 타입의 측별 계약 — TS null-drop vs 서버 ProtocolError — 회귀 없이 보존).
- 파일: `ui/src/protocol.ts`(+test), `server/web/messages.py`(+test), `server/web/panel.py`(빌더 닫힌 집합 확장만), `server/web/PROTOCOL.md`.

### M2 — 서버 대시 카탈로그 빌더 (풀 섹션 소싱)

- 신규 정보 섹션 목록(그룹 / preset_pools 드릴다운 / 매크로 / 플러그인 / 픽스처 카운트 요약)을 `gate.state_port` seam + 기존 rig 섹션/드릴다운 헬퍼 재사용으로 구성. 실패 사유 2종 구분·`truncated`/`drilldown_capped`/`contents_unavailable` 전파 유지.
- **섹션별 드릴다운 예산**: 단일 16-질의 예산을 프리셋 풀(~8-10개 풀 타입)과 공유하면 항상 캡아웃되므로, 섹션별 유계 예산으로 분리(정확한 수치는 M2 결정 — 유계성 자체가 요구이지 특정 수치가 아님, REQ-DASHUI-008).
- 매크로 발화 membership: 매크로 섹션이 발화 카탈로그 쪽(membership 대상)에 등재되도록 `PANEL_CATALOG_SECTIONS` 확장 또는 등가 경로 — @MX:ANCHOR 의미("모든 target_kind는 콘솔이 실제 발화하는 것") 보존.
- 익스큐터 타일: EXECBODY `resolve_path` 경로로 해석된 콘솔 번호가 있는 것만 발화 타일로 제공, 해석 불가는 정보 표기(REQ-DASHUI-011). 자식 인덱스/미검증 오프셋 하드코딩 금지(EXECBODY AC-016 원칙 계승).
- 파일: `server/web/panel.py`(또는 신규 `server/web/dash.py`), `server/tests/test_web_dash.py`(신규), `server/tests/test_web_panel.py`(회귀 그린).

### M3 — UI 레이아웃 분할 + 좌측 스켈레톤

- `App.tsx` 분할 레이아웃: 좌 대시보드 / 우 채팅, 접기 토글, chat-first 보존(접힘 시 기존 단일 컬럼). `.app` 860px 캡 해제/확장(styles.css:24-28 — 실제 CSS 변경).
- 채팅 기능 무손상 확인 스캐폴딩(ApprovalCard/ReviewCard/Settings/Status 렌더 + 입력 플로우).
- 파일: `ui/src/App.tsx`, `ui/src/styles.css`, `ui/src/components/DashBoard.tsx`(신규 스켈레톤), 관련 vitest.

### M4 — 풀 그리드 + 타일 (onPC 풀 윈도우 시각)

- `PoolSection.tsx`/`PoolTile.tsx` 신규: 넘버드 슬롯 셀, 점유/빈 구분, 풀 타입 배지/색 구분, 픽스처 카운트 요약 카드, 섹션 헬스(실패 사유 구분) 렌더, 마지막 동기화 시각 + 수동 새로고침 버튼.
- 토큰 확장은 additive(교체 금지), live-amber 배타·15px 하한·콘솔 어휘 준수(REQ-DASHUI-016/017/018). 스타일 가드 테스트(SHOWUI M4의 stylesheet-guard 패턴)로 배타 규칙 기계화.
- 파일: `ui/src/components/PoolSection.tsx`(신규), `ui/src/components/PoolTile.tsx`(신규), `ui/src/components/DashBoard.tsx`, `ui/src/styles.css`, 관련 vitest.

### M5 — 발화 경로 통합 (게이트 + LiveLock)

- 시퀀스/익스큐터 타일 → 기존 `panel_execute`/`panel_stop` 배선(`buildPanelExecute`/`buildPanelStop` 재사용), 매크로 타일 → `panel_execute`(target_kind=macro, Off 어포던스 없음 — one-shot).
- LiveLock 제안 전용 강등, health/executions_blocked 차단 렌더, busy/승인 카드(ApprovalCard) 왕복, 연타 1회 수렴(`createDecisionGuard` 재사용), disconnect 시 휘발 상태 소거 + 재접속 시 양 카탈로그 + status 재동기화.
- 파일: `ui/src/useCopilotSocket.ts`, `ui/src/components/PoolTile.tsx`, `server/web/app.py`(매크로 라우팅이 M2에서 미완이면 여기서 마감), 관련 pytest/vitest.

### M6 — 전체 그린 + 라이브 E2E + 문서 마감

- pytest 전체 + vitest 전체 그린(AC-DASHUI-013). 실제 onPC 2.4.2 라이브 체크리스트(AC-DASHUI-014/015 — acceptance.md §C LIVE).
- `server/web/PROTOCOL.md` 최종화. 라이브 증적은 progress.md §E.2에 기록(run-phase, manager-develop 소관).

## §C. 기술 제약

1. **신규 런타임 의존성 0.** 기존 React+Vite+Vitest / FastAPI+python-osc+stdlib.
2. **@MX:ANCHOR 경계 (위반 불가)**:
   - `panel.py:118-132` `PANEL_CATALOG_SECTIONS` — 발화 소스는 이 튜플 등재로만; 모든 `target_kind`는 콘솔이 실제 발화하는 클래스.
   - `panel.py:553-566` `playback_command` — 패널 커맨드 문자열이 만들어지는 유일한 곳; 닫힌 동사 집합 + 단일 양의 정수(광역 타깃 구성 불가 속성 유지).
   - `gate.py` 스크리닝 경로 유일성(SHOWUI REQ-007 계승) + `server/bridge/osc.py` 무접촉.
   - `console/lua/copilot_responder.lua` 무변경 소비.
3. **프로토콜 규율**: `PROTOCOL_VERSION = 1` 고정, additive 확장만. 신규 타입·enum 값은 양측 allowlist + reducer/handler 동시 등록. 미등록 타입 처리 계약은 측별로 상이(TS null-drop / 서버 ProtocolError) — 각각 회귀 없이 보존.
4. **안전 의미론 무변경 계승**: lock-FIRST 재확인, deny-all 기본 승인 포트, 위험 번들 사전 백업 fail-closed, 미확인 이력 자동 재전송 금지, EXECBODY fail-closed 보류 기계(미할당/타임아웃/블랙리스트) 전체.
5. **effective 설정 규율**: `osc_slot`/`receive_port`/`reply_port` 하드코딩 금지.
6. **폴링 금지**: 타이머 구동 카탈로그 재질의 없음(REQ-DASHUI-021) — 접속 시 + 수동 새로고침만.

## §D. 테스트 스캐폴딩 계획 (기존 관례 준수)

- **UI (vitest)**: DOM 없는 순수 함수 테스트(`protocol.test.ts` 패턴)로 신규 빌더/파서/reducer 커버. 컴포넌트 테스트로 접기/차단/새로고침/풀 렌더 커버. 스타일 가드 테스트(live-amber 배타·15px)는 SHOWUI M4의 stylesheet-guard 패턴 재사용.
- **서버 (pytest)**: 가짜 state port 픽스처로 대시 카탈로그 정확성(비연속 `no`, 실패 사유 2종, 플래그 3종, 드릴다운 예산), membership 거부(정보 전용 대상), 매크로 번들 구성·게이트 경유·보류 경로. `test_architecture.py` 그린 유지(신규 모듈의 OSC 표면 미접촉 기계 검증).
- **run-phase 자기 검증 커맨드(예상)**: `.venv/bin/python -m pytest -q`, `(cd ui && npx vitest run)`, `grep -rn "bridge.osc\|from server.bridge" server/web/panel.py server/web/dash*.py`(0건), `grep -rn "window.confirm" ui/src/`(0건), `grep -rn "setInterval" ui/src/components/`(대시 폴링 부재 확인).

## §E. 리스크

| # | 리스크 | 완화 |
|---|---|---|
| R1 | **브랜치 분기** — SHOWUI M4/M5 UI(ShowPanel/PanelTile)가 `feat/app-deploy-file-import`에 존재, 본 브랜치 조상 아님. 훗날 병합 시 UI 충돌 | 구별되는 컴포넌트 이름(DashBoard/PoolSection/PoolTile) 사용(§F D7), reconciliation은 명시적 Out of Scope + research.md §3 기록 |
| R2 | 매크로 실행 형태/동작의 라이브 편차(룰북 `Macro <no>` vs 실측) | M6 라이브 체크리스트에 매크로 press 검증 포함; 편차 시 EXECBODY 선례(정직한 DESCOPE — 매크로 press만 read-only로 강등, 나머지 범위 유지) |
| R3 | 드릴다운 예산 vs 프리셋 풀 8-10종 — 단일 16캡 공유 시 상시 캡아웃 | M2 섹션별 유계 예산 분리 + `drilldown_capped` 정직 표기(REQ-DASHUI-008) |
| R4 | 익스큐터 해석 불가(showfile에 따라 resolve 실패) | 해석된 번호 있는 것만 발화 타일 제공, 불가 항목은 정보 표기(REQ-DASHUI-011) — 오프셋 추정 금지 |
| R5 | 레이아웃 회귀(860px 캡 해제로 채팅 UX 훼손) | 접기 기본 제공 + chat-first 보존 assert(AC-DASHUI-009), 수동 시각 점검 |
| R6 | 큰 showfile에서 카탈로그 빌드 비용(질의 수 증가) | 유계 예산 + 폴링 금지 + 수동 새로고침만 — 비용이 사용자 의도에만 비례 |
| R7 | 정보 타일이 발화 타일로 오인/승격되는 회귀 | 정보 형상에 target_kind 부재(구조적) + membership 음성 테스트(AC-DASHUI-003) |

## §F. 결정 기록 (재질의 금지)

| 결정 | 내용 | 반영 위치 |
|---|---|---|
| D1 매크로 press | v1 포함, 실행 형태는 룰북 검증 `Macro <no>`(00_grammar.md:60). 라이브 편차 시 매크로만 read-only 강등하는 정직한 축소 경로 | REQ-DASHUI-012, §E R2 |
| D2 정보 카탈로그 분리 | 발화 카탈로그(`panel_catalog`) 무변경, 정보 풀은 신규 `dash_catalog` additive 이벤트 | REQ-DASHUI-006/007, M1 |
| D3 프리셋/플러그인 read-only | recall/실행은 후속 SPEC — programmer 오염·Lua 본문 스크리닝 문제 | REQ-DASHUI-023, spec.md §D |
| D4 픽스처 = 카운트 요약 | 전체 그리드는 참조 가치 대비 비용 과다 + 슬롯≠FID 함정 | REQ-DASHUI-009 |
| D5 접힘 상태 세션-휘발 | 클라이언트 영속화 없음(서버 단일 진실원 관례의 보수적 계승) | REQ-DASHUI-002 |
| D6 익스큐터 = 해석된 번호만 | EXECBODY resolve 소비, 자식 인덱스/미검증 오프셋 금지 | REQ-DASHUI-011 |
| D7 컴포넌트 명명 | DashBoard/PoolSection/PoolTile — 타 브랜치 ShowPanel/PanelTile과 이름 충돌 회피 | §E R1 |
