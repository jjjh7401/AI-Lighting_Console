# SPEC-COPILOT-DASHUI-001 — progress

## Plan-phase log

- 2026-07-24 — Tier L 판정: UI 레이아웃 재구성(App.tsx/styles.css) + 신규 좌측 컴포넌트 3종 + 서버 카탈로그 확장 + 프로토콜 additive 확장 — 15+ 파일·1000+ LOC 예상, UI-surfaced SPEC. 아티팩트 5종(spec/plan/acceptance/design/research) + 본 progress 스켈레톤 생성 (v0.1.0, status: draft).
- 2026-07-24 — 브랜치 실측: SHOWUI-001 M1~M3은 본 브랜치 조상(서버/프로토콜 기반 실재), M4/M5 UI는 타 브랜치(`feat/app-deploy-file-import`) — 본 SPEC UI는 신규 작성, reconciliation은 범위 제외(research.md §3).
- 2026-07-24 — plan-audit review-1(PASS-WITH-DEBT 0.89) findings D1-D6 folded, D7 no-op(`related_specs` 유지): D1 AC-DASHUI-017 신설(REQ-015 전담) · D2 핀 UI Out of Scope 명시 · D3 stylesheet-guard 교차-브랜치 정정 · D4 PANEL_ITEM_KINDS 배지 확장 명시 · D5 anchor 553-566 정정 · D6 Zone/풀 접힘 세션-휘발 확장. spec.md v0.1.1.
- 다음 단계: plan-audit(Tier L PASS 기준 0.85) → Implementation Kickoff Approval → design phase(UI-surfaced route, D1-D5) → run.

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-07-24T00:00:00Z
- plan_status: audit-ready
- artifacts: spec.md / plan.md / acceptance.md / design.md / research.md (5-file Tier L) + progress.md
- next: plan-audit → Implementation Kickoff Approval (plan→run HUMAN GATE) → design phase → run

## §E.2 Run-phase Evidence

### M1 — 프로토콜·데이터 모델 계약 (2026-07-24, TDD RED→GREEN)

**범위**: plan.md §B M1 3항목 전부 — ① `dash_catalog_request`/`dash_catalog` additive 타입(DashSection = `{name, status, truncated?, drilldown_capped?, contents_unavailable?, items}`, DashItem = `{no, name, appearance?|null, meta?}` — 발화 target 필드 부재, REQ-DASHUI-007 구조적 비발화), ② `PANEL_TARGET_KINDS` + 형제 `PANEL_ITEM_KINDS`/`PanelItemKind` 양측 additive `macro` + `playback_command` 룰북 검증 형태 `Macro <no>`(00_grammar.md:60, one-shot — `Off`+macro는 구성 불가), ③ `UiState.dash`(`{sections, lastSyncAt, stale}`) + `reduceServerEvent` case(replace + nowMs 주입 신선도 스탬프) + `clearOnDisconnect` 확장(동기화된 카탈로그 stale 표기 — 섹션은 잔존, 신선도 주장만 철회). `PROTOCOL_VERSION = 1` 유지, PROTOCOL.md 반영.

**RED 증적**: 서버 — `pytest server/tests/test_web_messages.py` collection ImportError(dash 미구현); UI — `vitest run src/protocol.test.ts` 13 failed / 52 passed. GREEN 후 전량 통과.

| 검증 항목 | 커맨드 | 결과 |
|---|---|---|
| 서버 프로토콜+패널 스위트 | `.venv/bin/python -m pytest -q server/tests/test_web_messages.py server/tests/test_web_panel.py server/tests/test_web_panel_execute.py` | `277 passed, 1 warning in 0.74s` |
| UI 프로토콜 스위트 | `(cd ui && npx vitest run src/protocol.test.ts)` | `Tests 65 passed (65)` (기준선 48 → +17) |
| TS 타입체크 (macro enum은 타입 레벨) | `(cd ui && npx tsc --noEmit)` | exit 0 |
| 전체 pytest | `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest -q` | `3 failed, 1793 passed, 2 skipped` — 실패 3건 전부 **기존 실패**(stash A/B로 M1 무관 귀속: test_lua_responder 1건, test_web_provision_api 1건, test_web_reply_discovery 1건. 셋 다 M1 변경 stash 제거 상태에서도 동일 실패) → **신규 실패 0건** |
| 전체 vitest | `(cd ui && npx vitest run)` | `Tests 115 passed (115)` |
| dash 형상 발화 필드 부재 | `grep -rn "target_kind" ui/src/protocol.ts \| grep -i dash` | 0건 |
| 프로토콜 버전 동결 | `grep -n "PROTOCOL_VERSION = 1" server/web/messages.py ui/src/protocol.ts` | 양측 1 유지 |
| OSC 경계 (AC-016 grep 절반) | `grep -rn "bridge.osc\|from server.bridge" server/web/panel.py` | 0건 (기준선과 동일) |
| ruff | `ruff check` 4개 터치 파일 | clean; `ruff format --check`는 기존 편차만 지적(baseline에서도 동일 실패 — M1 신규 라인 위반 0건) |

**M1 시점 AC 스냅샷** (전체 판정은 M6):

| AC | M1 상태 | 비고 |
|---|---|---|
| AC-DASHUI-001 | PASS | 신규 타입 양측 수락 + 미등록 타입 측별 계약(TS null-drop / 서버 ProtocolError) 회귀 없음 + v==1 양측 assert |
| AC-DASHUI-003 | 부분 PASS | 타입 레벨 절반 완료(DashItem 발화 필드 부재 + `dash_section`이 fire-shaped 항목 거부). membership 거부 절반은 M2 |
| AC-DASHUI-006 | 부분 PASS | 빌더 절반: `playback_command("Go+","macro",3) == "Macro 3"`, `Off`+macro 구성 불가. 게이트 경유·보류는 M2/M5 |
| AC-DASHUI-013 | PASS(M1 시점) | 킥오프 기준선 대비 신규 실패 0건(기존 실패 3건 stash 귀속 기록) |
| AC-DASHUI-016 | PASS(M1 시점) | bridge grep 0건 + `test_architecture.py` 전체 스위트 내 그린 |
| AC-DASHUI-017 | 부분 PASS | reducer 절반: `clearOnDisconnect`가 동기화된 dash를 stale 표기(섹션 보존·미동기화 시 무표기·재수신 시 해제) assert. 재접속 이중 카탈로그+status dispatch는 M5 |

**M2 인계 노트**: `dash_catalog_request`가 이제 파싱되므로 `server/web/app.py` ws 디스패치의 최종 `else:  # status_request` 분기(app.py:409)로 흘러들어가 status 이벤트로 응답된다 — M1 파일 범위(app.py 제외) 밖이라 미수정. M2에서 dash 카탈로그 빌더 배선 시 이 else **앞에** 전용 분기를 추가할 것. 또한 macro가 `panel_stop` parse를 통과하므로(닫힌 집합 공유), M2 membership/M5 UI가 macro stop 경로를 차단해야 함(빌더는 이미 ValueError로 방어).

### M2 — 서버 대시 카탈로그 빌더 (2026-07-24, TDD RED→GREEN)

**범위**: plan.md §B M2 5항목 전부.

① **신규 정보 섹션**: 신규 `server/web/dash.py`에 `build_dash_catalog()` 신설 — `gate.state_port` seam + `tools.py`의 `rig_object`/`rig_section`/`drill_into` 재사용(신규 구현 0). 6개 섹션(우선순위 순): `groups` / `preset_pools`(드릴다운) / `macros` / `plugins` / `fixtures`(카운트 요약) / `executors`(해석 투명성 리포트). **결정 기록(문서화된 판단)**: `dash_catalog`는 REQ-DASHUI-007이 명시한 읽기 전용 정보(그룹·프리셋·플러그인·픽스처 요약) + 매크로 참조 행 6종을 나른다 — 시퀀스/익스큐터의 발화 가능 절반은 `panel_catalog`(SHOWUI, 무변경)가 유일 출처로 남고, `dash_catalog`의 `executors` 섹션은 REQ-DASHUI-011 전용의 **해석 투명성 리포트**(어느 페이지-드릴다운 익스큐터 후보가 콘솔 자체 주소 형태로 확인되는지)만 나른다 — `panel_catalog`의 기존(SHOWUI M2/M3, 동결) 익스큐터 생성 로직은 무변경.
② **섹션별 드릴다운 예산 분리**: 단일 `PANEL_DRILLDOWN_QUERY_CAP=16` 공유 대신 3개 독립 예산 신설 — `DASH_PRESET_POOL_QUERY_CAP=12`(tools.py가 명시한 ~8-10 프리셋 타입에 여유분), `DASH_EXECUTOR_PAGE_QUERY_CAP=8`(페이지 워크), `DASH_EXECUTOR_VERIFY_QUERY_CAP=16`(후보별 `Executor <n>` 검증 질의, 페이지 워크와 별도 질의군이므로 별도 예산). 소진 시 `drilldown_capped` 정직 표기(테스트로 확인).
③ **매크로 발화 membership**: `panel.py` `PANEL_CATALOG_SECTIONS`에 `SectionSpec(name="macros", path="DataPool/Macros", target_kind="macro")` additive 추가(@MX:ANCHOR 확장, 재정의 아님 — "모든 target_kind는 콘솔이 실제 발화하는 것" 의미 유지·강화). `_tiles()`에 target_kind별 배지 매핑(`_ITEM_KIND_BY_TARGET_KIND`) 신설해 plan.md D4가 경고한 매크로 타일의 `kind="sequence"` 오배지를 봉쇄 — 매크로는 `kind="macro"`.
④ **익스큐터 타일**: `server/web/dash.py`의 `_resolve_executor_no()`가 페이지-드릴다운 후보(풀 슬롯 no + name)를 콘솔 자체 `"Executor <n>"` 주소 질의(EXECBODY-001 `resolve_path`/`ObjectList` 경로가 소비하는 것과 동일 형태, `console.py::StateBodyFetcher._fetch_executor_body`가 이미 쓰는 형태)로 **검증**해 `meta={"resolved": true/false}`로 정직 보고. 자식 인덱스·오프셋 추정 0건(후보 번호 자체를 검증할 뿐, 새 번호를 유추하지 않음). **알려진 잔여 위험**(§E.5 참고): `panel_catalog`(발화 카탈로그) 자체는 M2에서 필터링하지 않음 — 미해석 익스큐터도 여전히 기존 SHOWUI 경로로 발화 가능한 상태이며, dash 리포트를 실제 press 가능 여부에 배선하는 것은 M5 UI 과업으로 이연(회귀 안전성 우선 — test_web_panel.py/test_web_panel_execute.py의 기존 무조건 발화 가정 픽스처를 깨지 않기 위한 documented judgment call).
⑤ **app.py 디스패치 수정(M1 인계 갭 해소)**: `dash_catalog_request` 분기를 최종 `else: # status_request`(구 app.py:409) **앞에** 신설, `send_dash_catalog(deps.gate.state_port, send_event)`를 `panel_side_lane`(카탈로그/핀/언핀과 동일 락 — 다중 OSC 질의 스톰 방지)으로 직렬화.

**RED 증적**: `server/tests/test_web_dash.py`(신규 33종) 작성 전 `build_dash_catalog`/`dash_catalog_snapshot`가 미존재 → collection ImportError. GREEN 후 전량 통과. `test_web_panel.py`/`test_web_panel_execute.py`의 매크로 섹션 추가로 인한 회귀 4건(정확히 예측됨 — 섹션 리스트 exact-match assert 3건 + `console_unreachable` 리스트 길이 1건)을 fixture(`DataPool/Macros` 추가) + assert 갱신으로 해소, 신규 매크로 커버리지 6종 추가.

| 검증 항목 | 커맨드 | 결과 |
|---|---|---|
| 신규 대시 카탈로그 스위트 | `.venv/bin/python -m pytest -q server/tests/test_web_dash.py` | `33 passed` |
| 회귀 스위트(패널+메시지+앱+아키텍처) | `.venv/bin/python -m pytest -q server/tests/test_web_panel.py server/tests/test_web_panel_execute.py server/tests/test_web_messages.py server/tests/test_web_app.py server/tests/test_architecture.py` | `335 passed` |
| 전체 pytest | `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest -q` | `3 failed, 1831 passed, 2 skipped` — 실패 3건 전부 M1과 동일한 **기존 실패**(test_lua_responder/test_web_provision_api/test_web_reply_discovery — 소켓/lua-harness flakiness, M2 무관) → **신규 실패 0건**. M1 기준선(1793 passed) 대비 +38건(신규 커버리지) |
| 전체 vitest | `(cd ui && npx vitest run)` | `Tests 115 passed (115)` — M1과 동일(서버 전용 마일스톤, 영향 없음 확인) |
| ruff (터치 파일) | `ruff check` 6개 터치 파일 | clean |
| ruff format | `ruff format --check` → 신규 편차 2건(내 Edit 툴 줄바꿈) `ruff format` 적용 후 clean; `panel.py`/`app.py`/`test_web_panel_execute.py`는 **기존 편차만**(baseline과 동일 — stash 비교로 확인, M2 신규 라인 위반 0건) |
| OSC 경계 | `grep -rn "bridge.osc\|from server.bridge" server/web/panel.py server/web/dash*.py server/web/app.py` | 0건 |
| target_kind 비부착 | `grep -n "target_kind" server/web/dash*.py` | 모듈 독스트링의 설명 문구 1건뿐(panel_catalog를 설명하는 산문) — 실제 구성 필드 0건, 구조 테스트(`test_no_dash_item_ever_carries_a_fire_address`)로 교차 확인 |

**M2 시점 AC 스냅샷** (전체 판정은 M6):

| AC | M2 상태 | 비고 |
|---|---|---|
| AC-DASHUI-002 | PASS | `test_web_dash.py` — 비연속 `no` 키잉, 실패 사유 2종 구분, 3종 플래그 전파, 드릴다운 예산 소진 표기 전부 확인 |
| AC-DASHUI-003 | PASS | 구조 테스트로 dash_item의 target_kind/target/id 부재 확인(M1의 construction-time 거부 + M2의 통합 레벨 재확인) |
| AC-DASHUI-004 | PASS | fixtures 섹션은 `meta.count`만 나르고 실제 슬롯 번호 0건 노출 |
| AC-DASHUI-005 | PASS-WITH-DEBT | `panel_execute`/`panel_stop` → `gate.screen()` 경로 무변경 확인(회귀 그린) + 익스큐터 해석 리포트 신설. **DEBT**: `panel_catalog` 자체의 발화 가능 목록은 해석 여부로 필터링되지 않음(위 ④ 잔여 위험) — M5에서 UI가 dash의 해석 리포트를 press 가능 여부에 실제로 배선해야 REQ-DASHUI-011이 완전 충족됨 |
| AC-DASHUI-006 | PASS | `TestMacroGateRouting` — 양성 매크로 press가 `["Macro 3"]` 1:1 screened+sent+audit 확인, 미상 대상 사전 거부, 매크로 stop 프레임 미구성 확인(콘솔 미도달) |
| AC-DASHUI-016 | PASS(M2 시점) | `test_architecture.py` 4/4 그린 + dash.py 자체 OSC 경계 테스트 신설 |

### M3 — UI 레이아웃 분할 + 좌측 스켈레톤 (2026-07-24, TDD RED→GREEN)

**범위**: plan.md §B M3 전부 — UI 레이아웃 전용(실 카탈로그 fetch/dispatch는 M5, 실 풀 렌더는 M4, 둘 다 범위 외). ① `App.tsx` 분할 레이아웃: hook-free `AppShell` 래퍼(신규 export) 신설 — `dashCollapsed`(session-volatile, D5 — 클라이언트 영속화 없음, 기본값 `true`)가 `DashBoard` 마운트 여부를 결정, 접힘 시 `AppShell`의 children이 곧 전체 출력(오늘의 단일 컬럼 트리와 동일, AC-DASHUI-009). `header-actions`에 `dash-toggle` 버튼 신설(항상 노출 — DashBoard 자체 접기 버튼과 별개로, 접힘 상태에서도 펼치기 트리거 보장). ② `.app` 860px 캡을 `.app-shell.dash-collapsed .app`로 스코프 이동(styles.css:41-44) — 무조건 캡 규칙은 제거, 분할 상태는 `.app-shell.dash-split .app`에서 720px 캡(가독폭 유지, design.md §6). ③ 신규 `ui/src/components/DashBoard.tsx` — 훅 없는 순수 프레젠테이션 컴포넌트(header + 접기 버튼 + placeholder body). M1 동결 `UiState.dash` 슬라이스를 read-only prop으로 미래-대비 배선(빈/기본 상태에서 크래시 없음 — `dash.sections.length === 0` → "로딩 중" placeholder).

**결정 기록(문서화된 판단)**: 이 프로젝트는 DOM/jsdom 테스트 하네스가 없다(`protocol.ts`/`useCopilotSocket.test.ts`/`ApprovalCard.test.tsx` 헤더에 기존 명문화된 관례 — "Pure functions only... unit-testable without a DOM"). `App()` 자체는 훅(`useCopilotSocket`의 `useReducer`/`useState`/`useEffect`)을 호출하므로 렌더러 없이 직접 호출 불가. 이를 우회하기 위해 레이아웃 분기 로직을 훅-프리 `AppShell`로 추출(App.tsx에서 export) — 테스트가 이를 평범한 함수로 직접 호출해, `react-jsx` 런타임이 만든 React 엘리먼트 트리(`.type`/`.props` 객체)를 리액트 렌더러 없이 구조적으로 검사한다. `DashBoard`도 동일한 이유로 훅을 갖지 않도록 설계.

**RED 증적**: `App.test.tsx`(신규)가 `./App`에서 `AppShell`을 import → 아직 미export라 모듈 로드 실패; `DashBoard.test.tsx`(신규)가 `./DashBoard` import → 파일 미존재로 로드 실패. GREEN 후 전량 통과.

| 검증 항목 | 커맨드 | 결과 |
|---|---|---|
| AppShell 레이아웃 스위트(신규) | `(cd ui && npx vitest run src/App.test.tsx)` | `4 passed` |
| DashBoard 스위트(신규) | `(cd ui && npx vitest run src/components/DashBoard.test.tsx)` | `6 passed` |
| 전체 vitest | `(cd ui && npx vitest run)` | `Tests 125 passed (125)` (M2 기준선 115 → +10) |
| TS 타입체크 | `(cd ui && npx tsc --noEmit)` | exit 0 |
| 전체 pytest | `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest -q` | `3 failed, 1831 passed, 2 skipped` — 실패 3건은 M1/M2와 **동일한 기존 실패**(test_lua_responder/test_web_provision_api/test_web_reply_discovery, M3는 서버 미접촉) → **신규 실패 0건**, M2 기준선(1831 passed)과 pass count 동일(UI 전용 마일스톤 확인) |
| `.app` 860px 캡 스코프 이동 확인 | `grep -n "max-width" ui/src/styles.css` | `.app-shell.dash-collapsed .app { max-width: 860px }` (스코프됨) / `.app-shell.dash-split .app { max-width: 720px }` — 무조건 캡 0건 |
| 대시보드 폴링 부재(REQ-DASHUI-021) | `grep -rn "setInterval\|setTimeout" ui/src/components/DashBoard.tsx` | 0건 |
| 확인 모달 부재 | `grep -rn "window.confirm" ui/src/` | 0건 |

**M3 시점 AC 스냅샷** (전체 판정은 M6):

| AC | M3 상태 | 비고 |
|---|---|---|
| AC-DASHUI-009 | PASS-WITH-DEBT | 구조 레벨 확인 완료: 접힘 시 DashBoard 노드 0개 + children(채팅 UI 서브트리) 무손상 통과(`AppShell` 테스트), App.tsx의 헤더/배너/main/composer 마크업 자체는 M2 기준 무변경(className·컴포넌트 참조 동일). **DEBT**: DOM 렌더링·실제 클릭/입력 시뮬레이션(ApprovalCard/ReviewCard/SettingsPanel 렌더 확인, composer 입력→전송 왕복)은 이 프로젝트의 DOM-free 테스트 하네스 제약으로 vitest 레벨에서 미실행 — acceptance.md AC-DASHUI-009 검증 레시피가 요구하는 완전한 동작 검증은 M6 라이브/수동 브라우저 점검으로 이연(§E.5 잔여 위험에 기록) |

**M4/M5 인계 노트**: `DashBoard`는 `dash: DashState` prop을 받아 `sections.length === 0`일 때 "로딩 중" placeholder, 그 외엔 `dashboard-sections` 빈 컨테이너를 렌더한다 — M4는 이 컨테이너 내부에 `PoolSection`/`PoolTile`을 채우면 되고, 새 조건 분기나 prop 시그니처 변경이 필요 없다. `AppShell`은 `dashCollapsed`/`dash`/`onToggleDash`/`children` 4개 prop만 받으므로 M5가 `useCopilotSocket.ts`에 접속 시 `dash_catalog_request` dispatch를 배선해도 `AppShell`/`DashBoard` 자체는 무변경으로 남는다(단순히 `state.dash`가 실 데이터로 채워질 뿐).

### M4 — 풀 그리드 + 타일 (onPC 풀 윈도우 시각) (2026-07-24, TDD RED→GREEN)

**범위**: plan.md §B M4 전부. ① 신규 `ui/src/components/PoolTile.tsx`(넘버드 슬롯 셀, 점유 항목 1개 렌더 — 번호/이름/어피어런스 칩) + `ui/src/components/PoolSection.tsx`(섹션 헤더 + 헬스/플래그 배지 + 타일 그리드, wire order 고정). ② 픽스처 카운트 요약: design.md §2 헤더 스트립 ASCII 목업("리그 요약: 픽스처 N대 · 동기화 HH:MM:SS · [새로고침]")을 그대로 따라 별도 풀-섹션 카드가 아닌 헤더 스트립 한 줄로 접힘 — `dashboardSummaryText()`가 조립. ③ 섹션 헬스: `path_not_resolved` vs `console_unreachable` 텍스트 분리 + `truncated`/`drilldown_capped`/`contents_unavailable` 3종 플래그를 " · "로 결합해 정직 표기(`sectionHealthLabel()`, PoolSection.tsx). ④ 마지막 동기화 시각(`formatSyncTime()`) + 수동 새로고침 버튼 — `onRefresh?: () => void` optional prop으로 배선(미제공 시 `console.debug` 플레이스홀더, design.md §7 규칙7 — 죽은 버튼 금지). ⑤ 익스큐터 타일: `dashItemIsPressable("executors", item)`이 `meta.resolved === true`인 항목만 press-able로 라우팅 — 미해석 항목은 `pool-tile-info` + "정보만" 배지, 클릭 어포던스·버튼 0건(REQ-DASHUI-011/EXECBODY AC-016 계승). ⑥ 토큰: `--live-amber`(#ffb02e) additive 신설(REQ-DASHUI-016) — `.pool-tile-running`/`.pool-tile-running .pool-tile-verb` 외 참조 0건으로 배타 확보(REQ-DASHUI-017), 15px 하한은 1급 라벨 클래스(`.pool-tile-no`/`.pool-tile-name`/`.pool-tile-verb`/`.pool-section-label`/`.dashboard-summary`)에 적용. ⑦ 신규 `ui/src/styles.test.ts` — SHOWUI M4의 stylesheet-guard 패턴(857e9ed, 비-조상 브랜치 — 기법만 참고, cherry-pick 아님)을 본 브랜치에 순수 문자열/정규식 파서로 재작성(jsdom 미사용, 프로젝트 no-DOM-harness 관례 계승).

**결정 기록(문서화된 판단 — plan.md §F 패턴 계승)**:

- **D-M4-1 빈 슬롯 갭 렌더 범위 축소**: design.md §3 "빈 슬롯: 어두운 셀 + 번호만" 요구는 점유 최대 `no`까지의 갭 데이터가 필요하나, `build_dash_catalog`(server/web/dash.py)는 점유 오브젝트만 반환하고 갭/최대치 메타를 나르지 않는다. 클라이언트 측에서 갭을 추정하는 것은 REQ-DASHUI-011이 금지하는 "미검증 오프셋 추정"과 같은 계열의 위험(존재하지 않는 슬롯 번호를 UI가 만들어내는 것)이므로 채택하지 않음 — PoolTile은 점유 슬롯만 렌더한다. §E.5 잔여 위험에 기록.
- **D-M4-2 픽스처 카드 → 헤더 스트립 한 줄로 배치**: Section A 프롬프트는 "compact card"라 표현했으나, design.md §2 확정 IA(사용자 위임 설계)의 ASCII 목업은 픽스처 카운트를 헤더 스트립 한 줄(동기화 시각·새로고침과 동렬)에 배치한다. 확정 설계 문서를 우선해 헤더 스트립 통합을 채택 — 별도 `pool-section-fixtures` 카드는 만들지 않음(REQ-DASHUI-009 요구인 "카운트만, 슬롯 나열 금지"는 두 배치 모두 충족하므로 배치만의 판단).
- **D-M4-3 새로고침 콜백 optional-prop**: `onRefresh?: () => void` — 미제공 시 클릭이 `console.debug` 플레이스홀더를 호출(죽은 버튼 금지, design.md §7 규칙7). M5가 `useCopilotSocket.ts`에서 실 콜백을 주입하면 `DashBoard`/`App.tsx` 시그니처 변경 없이 즉시 배선됨(M3 인계 노트와 동일한 무변경-확장 패턴).
- **D-M4-4 live-amber/RUN 배지 미배선**: `panel.running`(키: `panelItemId(target_kind, target)`)은 `DashBoard`가 받는 `dash: DashState` prop 밖에 있다 — dash 익스큐터 항목은 `{no, name, meta}`뿐, target_kind가 구조적으로 없다(REQ-DASHUI-007). 토큰·CSS 선택자(`--live-amber`, `.pool-tile-running`)는 배타 규칙과 함께 신설했으나 실제 RUN 표시는 M5가 `panel.running`을 익스큐터 dash 항목과 교차 참조하도록 배선해야 함. §E.5 잔여 위험에 기록.

**RED 증적**: `PoolTile.test.tsx`/`PoolSection.test.tsx`(신규)가 각각 `./PoolTile`/`./PoolSection` import → 파일 미존재로 모듈 로드 실패; `DashBoard.test.tsx` 기존 6종 중 "switches to the sections placeholder region..." 케이스가 M4 확장 후 `dashboard-sections` 빈 placeholder 구조를 더 이상 반환하지 않아 실패(3-child aside 구조로 확장됨) → M4 범위에서 재작성; `styles.test.ts`(신규)가 `--live-amber` 미존재로 실패. GREEN 후 전량 통과.

| 검증 항목 | 커맨드 | 결과 |
|---|---|---|
| PoolTile 스위트(신규) | `(cd ui && npx vitest run src/components/PoolTile.test.tsx)` | `8 passed` |
| PoolSection 스위트(신규) | `(cd ui && npx vitest run src/components/PoolSection.test.tsx)` | `9 passed` |
| DashBoard 스위트(M4 확장) | `(cd ui && npx vitest run src/components/DashBoard.test.tsx)` | `25 passed` (M3 6종 → M4 25종 — 레이아웃 확장으로 구조 케이스 일부 재작성 + 신규 헤더-스트립/섹션-라우팅 유틸리티 테스트 다수 추가) |
| 스타일 가드 스위트(신규) | `(cd ui && npx vitest run src/styles.test.ts)` | `18 passed` |
| 전체 vitest | `(cd ui && npx vitest run)` | `Tests 179 passed (179)` (M3 기준선 125 → +54: PoolTile 8 + PoolSection 9 + styles.test.ts 18 + DashBoard 순증 19) |
| TS 타입체크 | `(cd ui && npx tsc --noEmit)` | exit 0 |
| 전체 pytest | `.venv/bin/python -m pytest -q` | `3 failed, 1831 passed, 2 skipped` — 실패 3건은 M1~M3와 **동일한 기존 실패**(test_lua_responder/test_web_provision_api/test_web_reply_discovery, M4는 UI 전용·서버 미접촉) → **신규 실패 0건**, pass count M3 기준선(1831)과 동일(서버 미변경 확인) |
| live-amber 배타 (styles.test.ts 기계 검증) | `grep -n "live-amber" ui/src/styles.css` | `:root` 정의 1건 + `.pool-tile-running`/`.pool-tile-running .pool-tile-verb` 2건 — 그 외 0건 |
| 확인 모달 부재 | `grep -rn "window.confirm" ui/src/` | 0건(exit=1) |
| 대시보드/풀 컴포넌트 폴링 부재(REQ-DASHUI-021) | `grep -rn "setInterval\|setTimeout" ui/src/components/DashBoard.tsx ui/src/components/PoolSection.tsx ui/src/components/PoolTile.tsx` | 0건(exit=1) |
| OSC 경계(서버 미접촉 재확인) | `grep -rn "bridge.osc\|from server.bridge" server/web/panel.py server/web/dash*.py` | 0건(exit=1) — M2와 동일, M4는 서버 무변경 |

**M4 시점 AC 스냅샷** (전체 판정은 M6):

| AC | M4 상태 | 비고 |
|---|---|---|
| AC-DASHUI-004 | PASS(UI 절반 추가) | 헤더 스트립이 `meta.count`만 노출(`fixtureSummaryLabel`), 슬롯 번호·FID 표기 0건(PoolTile 미마운트) — 서버 절반은 M2 PASS 기완료 |
| AC-DASHUI-010 | PASS | 넘버드 슬롯(1급 `no`) + 어피어런스 칩 + press-able/read-only 구조적 분리(`pressable` prop, read-only엔 버튼 0건) + wire-order 고정(`PoolSection.test.tsx` "no sort/reflow") + live-amber 배타(styles.test.ts) + 15px 하한(1급 라벨) 전부 기계 검증 |
| AC-DASHUI-011 | PASS-WITH-DEBT | 폴링 부재는 PASS(grep 0건, 시간경과만으론 dispatch 없음 — DashBoard는 onRefresh를 클릭에서만 호출). **DEBT**: 실제 `dash_catalog_request` 전송은 onRefresh 콜백 내부(M5 소관)라 "요청 1회 dispatch"의 소켓 왕복 절반은 여전히 미검증 — M4는 콜백 호출 1회만 확인 |
| AC-DASHUI-012 | PASS | 동기화 시각(`formatSyncTime`) + stale 접미사(`(오래됨)`) + `path_not_resolved`/`console_unreachable` 텍스트 구분 + 3종 플래그 결합 표기 전부 `DashBoard.test.tsx`/`PoolSection.test.tsx`로 확인 |
| AC-DASHUI-013 | PASS(M4 시점) | 킥오프 기준선 대비 pytest 신규 실패 0건 + vitest 179/179 전부 그린 |
| AC-DASHUI-017 | 부분 PASS(렌더 절반 추가) | `dash.stale`일 때 헤더 스트립에 "(오래됨)" 표기됨을 확인(렌더 절반). `clearOnDisconnect` 로직 자체와 재접속 이중 dispatch는 M1에서 이미 부분 PASS로 기록된 그대로 — M5에서 완결 |

**M5 인계 노트**: (1) `DashBoard`에 `onRefresh?: () => void`를 실제 `dash_catalog_request` 디스패처로 주입하면 새로고침이 완결된다(시그니처 변경 없음). (2) 실행 상태(RUN/OFF, live-amber)는 `panel.running`을 익스큐터 dash 항목과 `panelItemId("executor", no)`로 교차 참조해야 하며, `PoolTile`에 `running?: boolean` prop을 추가하고 `.pool-tile-running` 클래스를 조건부로 붙이는 확장이 필요(현재 CSS 선택자·토큰은 이미 준비됨, TSX 배선만 M5 몫). (3) 시퀀스/익스큐터 실제 press 배선(`buildPanelExecute`/`buildPanelStop`)은 여전히 전량 M5 범위 — M4는 시각적 어포던스만 완성했다.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase — M5-M6 잔여>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
