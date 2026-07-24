---
id: SPEC-COPILOT-DASHUI-001
title: "콘솔 상태 대시보드 + 코파일럿 분할 UI"
version: "0.1.1"
status: in-progress
created: 2026-07-24
updated: 2026-07-24
author: manager-spec
priority: P1
phase: "Post-MVP 대시보드 UI (v1.2.0 target)"
module: "ui/src/, server/web/"
lifecycle: spec-anchored
tags: "dashboard, split-pane, pool-window, rig-context, panel, websocket, safety-gate, ui"
tier: L
related_specs: [SPEC-COPILOT-SHOWUI-001, SPEC-COPILOT-EXECBODY-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-DASHUI-001 — 콘솔 상태 대시보드 + 코파일럿 분할 UI

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-24 | manager-spec | 최초 작성 (draft, Tier L 5종 아티팩트). 사용자 요구 5건(채팅 우측 이동 / 좌측 콘솔 정보 버튼 영역 / onPC 풀 윈도우 미학 / 좌측 IA 디자이너 위임 / plan-first) 반영. 좌측 IA는 위임에 따라 design.md §2에서 확정. |
| 0.1.1 | 2026-07-24 | manager-spec | Plan-audit review-1 fold-in (PASS-WITH-DEBT 0.89 — D1~D6 반영, D7 no-op). D1: REQ-DASHUI-015 전담 기계 AC 신설(acceptance.md AC-DASHUI-017 — `clearOnDisconnect` 소거 + 재접속 이중 카탈로그·status 재동기화; DoD 1 갱신). D2: 핀 UI 경계 확정 — §D "Out of Scope — 핀 UI" 신설(v1 좌측은 카탈로그 섹션만 렌더, `source:"pin"` 렌더·핀 CRUD UI는 후속 이연, 서버 `panel_pin`/`panel_unpin`·PinStore 무접촉). D3: stylesheet-guard 인용을 교차-브랜치 참조로 정정(857e9ed 비-조상 — 본 브랜치 신규 작성; plan.md M4/§D + acceptance.md AC-010). D4: plan.md M1에 형제 닫힌 집합 `PANEL_ITEM_KINDS`/`PanelItemKind` 배지 확장 명시(매크로 타일 `sequence` 오배지 방지). D5: §A anchor 553-556 → 553-566 정정. D6: design.md §6 — Zone/풀 단위 접힘도 D5 세션-휘발 규칙 동일 적용 명시. |

## A. 개요

본 SPEC은 현재 채팅 단일 컬럼인 앱(`ui/src/App.tsx`)을 **분할(split-pane) 대시보드 UI**로 재구성한다: **우측 = 코파일럿 채팅**(기능 무손상), **좌측 = 콘솔 상태 정보 영역** — 패치 장비·그룹·시퀀스·프리셋·매크로·플러그인 등 조명 연출에 필요한 풀(pool)들을 grandMA3 onPC 풀 윈도우 미학의 **버튼/타일 그리드**로 표면화한다.

구현 기반은 **본 브랜치에 이미 존재하는 SHOWUI-001 M1~M3 기반**(동결된 패널 프로토콜 계약 + 서버 카탈로그/핀 스토어 + `PanelRuntime` 게이트 실행 경로)이다. 좌측 대시보드는 이 기반을 **확장**하며, 신규 실행 경로를 만들지 않는다 — 모든 발화(press)는 기존과 동일하게 `gate.screen()` 유일 관문을 경유한다(panel.py:631-636 단일 진입, playback_command @MX:ANCHOR panel.py:553-566). EXECBODY-001의 완료로 **양성 본문 익스큐터의 single-press 게이트 통과**가 확보되어(REQ-EXECBODY-013 라이브 PASS), SHOWUI-001 v1에서 축소되었던 익스큐터 타일이 본 SPEC에서 해제된다.

### 사전 확정 사실 (사용자 요구 — 재질의 금지)

1. **채팅은 우측으로**: 좌측이 콘솔 상태 정보 영역이 된다.
2. **좌측 = 조명 운용 정보의 버튼/타일**: 패치장비, 그룹, 시퀀스, 프리셋, 매크로, 플러그인 등 연출에 필요한 풀.
3. **시각은 onPC 풀 윈도우 미학**: 콘솔 오퍼레이터에게 친숙한 넘버드 슬롯 그리드.
4. **좌측 IA는 디자이너 위임**: 프로 조명 오퍼레이터 관점에서 설계 — **design.md §2가 확정 IA**이며 본 SPEC의 §B는 그 계약을 요구사항으로 고정한다.
5. **plan-first**: SPEC 문서 승인 후 구현.

### 안전 전제 (무변경 계승)

LiveLock(잠금 중 제안 전용), deny-all 기본 승인 포트, fail-closed 게이트, health gate — 전부 `gate.screen()` 파이프라인에 있으며 본 SPEC은 **소비만 하고 수정하지 않는다**. 발화하는 타일(시퀀스/익스큐터/매크로)은 채팅과 동일한 스크리닝을 받고, 읽기 전용 정보 타일(픽스처 요약·그룹·프리셋·플러그인)은 콘솔 발화 표면 자체를 갖지 않는다.

## B. 요구사항 (GEARS)

### B.1 레이아웃 재구성 (REQ group 1)

- **REQ-DASHUI-001** [Ubiquitous] — The UI **shall** 분할 레이아웃을 제공한다: 좌측 = 콘솔 상태 대시보드, 우측 = 채팅. 채팅의 기존 기능 전부(지시 전송, ApprovalCard/ReviewCard 플로우, LockToggle, StatusBanner/OnboardingBanner, SettingsPanel)는 분할 후에도 무손상으로 동작한다.
- **REQ-DASHUI-002** [Ubiquitous] — 좌측 대시보드 **shall** 접기(collapse)가 가능하며, 접힌 상태에서는 기존 chat-first 단일 컬럼 경험이 보존된다. 접힘 상태는 세션-휘발(클라이언트 영속화 없음 — 서버 단일 진실원 관례의 보수적 계승, design.md §6 D5).
- **REQ-DASHUI-003** [Ubiquitous] — 대시보드 타일 그리드 위치 **shall** 쇼 중 안정적으로 유지된다 — 자동 정렬·재배치(reflow) 금지, 갱신 시에도 풀 번호 순서 고정(SHOWUI REQ-017 계승).

### B.2 좌측 풀 섹션 + 데이터 소싱 (REQ group 2)

- **REQ-DASHUI-004** [Ubiquitous] — 대시보드 데이터 **shall** 기존 감사되는 조회 chokepoint(`gate.state_port` seam, app.py:175)와 rig 섹션/드릴다운 헬퍼(tools.py:169-256 형상)를 재사용해 구성되며, **라이브 검증된 경로만** 사용한다(`DEFAULT_RIG_CONTEXT_PATHS`, tools.py:65-76). 섹션별 실패 사유는 `path_not_resolved`와 `console_unreachable`을 **구분된 상태로** UI까지 전달한다(tools.py:104-105 — 병합 금지).
- **REQ-DASHUI-005** [Ubiquitous] — v1 풀 섹션 집합과 우선순위 **shall** design.md §2의 IA를 따른다: ① 시퀀스, ② 익스큐터(pages 드릴다운), ③ 그룹, ④ 프리셋(PresetPools 드릴다운), ⑤ 매크로, ⑥ 플러그인, ⑦ 픽스처/패치(카운트 요약). 모든 항목은 실제 `no`로 키잉된다(비연속 풀 번호, 배열 인덱스 금지).
- **REQ-DASHUI-006** [Event-driven] — **When** UI가 대시보드 카탈로그를 요청하면(접속 직후 + 수동 새로고침), the 서버 **shall** 신규 서버 이벤트로 회신하며, 갱신은 병합이 아니라 **전체 교체(replace)**다(SHOWUI PanelCatalog replace 의미론 계승, panel.py:135-143).
- **REQ-DASHUI-007** [Ubiquitous] — 읽기 전용 정보 타일(그룹·프리셋·플러그인·픽스처 요약) **shall** 구조적으로 발화 불가능한 데이터 형상을 갖는다 — 발화 가능 `target_kind`를 나르지 않으며, 패널 membership 검증은 정보 전용 대상을 절대 발화 대상으로 승인하지 않는다.
- **REQ-DASHUI-008** [Ubiquitous] — 드릴다운(프리셋 풀 내용물, 페이지 자식 익스큐터) **shall** 유계 질의 예산을 준수하며(`RIG_DRILLDOWN_QUERY_CAP`/`PANEL_DRILLDOWN_QUERY_CAP` 선례), 예산 소진으로 잘린 섹션은 `drilldown_capped`로 정직하게 표기된다 — 부분 결과를 완전한 결과로 위장하지 않는다.
- **REQ-DASHUI-009** [Ubiquitous] — 픽스처/패치 섹션 **shall** 카운트 요약으로 제공된다(패치 대수 + truncated 여부). 픽스처의 `no`는 패치 슬롯이며 FID가 아니므로(tools.py:33-36), the 대시보드 **shall not** 슬롯 번호를 FID로 제시하지 않는다.

### B.3 발화 가능 타일 — 안전 불변식 무변경 계승 (REQ group 3)

- **REQ-DASHUI-010** [Ubiquitous] — v1 발화 가능 종류 **shall** 정확히 셋이다: 시퀀스(`Go+`/`Off`), 익스큐터(`Go+`/`Off`), 매크로(run). 모든 발화는 기존 `panel_execute`/`panel_stop` → `PanelRuntime.fire` → `gate.screen()` 경로만을 사용한다(panel.py:631-636 — 제2 진입 금지).
- **REQ-DASHUI-011** [Ubiquitous] — 익스큐터 타일 **shall** **해석된(resolved) 콘솔 발화 번호**로만 키잉·발화된다(EXECBODY-001 M6 `resolve_path`/ObjectList 경로 소비). 자식 인덱스 `i` 또는 미검증 `+100` 오프셋을 발화 번호로 사용하는 것 **shall not** 허용된다 — 해석 불가 익스큐터는 발화 타일로 제공되지 않고 그 사실이 표기된다.
- **REQ-DASHUI-012** [Event-driven] — **When** 매크로 타일이 눌리면, the 서버 **shall** 룰북 검증 실행 형태(`Macro <no>` — 00_grammar.md:60 "Run a macro by id/name")로 번들을 구성해 `gate.screen()`을 경유시킨다. 본문 해석 불가·블랙리스트 매치 매크로는 게이트의 기존 fail-closed 기계에 따라 보류되어 ApprovalCard로 표면화된다 — 우회도, 조용한 무시도 없다.
- **REQ-DASHUI-013** [State-driven] — **While** LiveLock이 활성인 동안, 대시보드발 모든 발화 **shall** 제안(Proposal) 전용으로 강등되고 콘솔 송신은 0건이며, 발화 가능 타일은 비활성/제안 상태로 렌더된다(SHOWUI REQ-009 계승).
- **REQ-DASHUI-014** [State-driven] — **While** `status.health ≠ online` 또는 `executions_blocked`인 동안, the 대시보드 **shall** 차단 상태를 표시하고 신규 발화를 사전에 막거나 차단 결과를 명시적으로 표면화한다(SHOWUI REQ-010 계승 — 값은 항상 effective 설정/status 이벤트에서 읽는다).
- **REQ-DASHUI-015** [Event-driven] — **When** WebSocket이 닫히면, the UI **shall** 대시보드의 휘발 파생 상태(running 등)를 즉시 소거하고, **when** 재접속되면 카탈로그(양쪽) + status 재동기화를 요청해 재구축한다(SHOWUI REQ-015/016 fail-closed 계승).

### B.4 onPC 풀 윈도우 시각 디자인 (REQ group 4)

- **REQ-DASHUI-016** [Ubiquitous] — 풀 섹션 **shall** onPC 풀 윈도우 시각 언어를 따른다: 슬롯 번호가 1급 시각 요소인 넘버드 셀 그리드, 점유/빈 슬롯의 시각적 구분, 풀 타입별 식별(헤더/배지 색 구분). 토큰은 `ui/src/styles.css` `:root`를 재사용하고 최소한으로만 확장한다(교체 금지). 다크 전용(`color-scheme: dark`).
- **REQ-DASHUI-017** [Ubiquitous] — live-amber(`#ffb02e` 계열) **shall** 실행 중 상태 전용으로만 사용되고(SHOWUI REQ-018 배타 규칙), 상태는 색상 단독으로 전달되지 않으며(`RUN`/`OFF` 배지 병행, 라벨 최소 15px), 타일 동사는 콘솔 어휘(`Go+`/`Off`/`Macro`)를 사용한다(미디어 플레이어 은유 금지 — SHOWUI REQ-020 계승).
- **REQ-DASHUI-018** [Ubiquitous] — 대시보드 **shall** 데이터 신선도를 표면화한다: 마지막 동기화 시각 표기 + 수동 새로고침 어포던스 + 섹션별 실패/부분(플래그) 상태의 구분 렌더.

### B.5 Unwanted (금지 요구)

- **REQ-DASHUI-019** [Unwanted] — 본 SPEC **shall not** 신규 콘솔 쓰기 경로를 만들지 않는다: 신규 대시보드 모듈은 OSC 송신 표면(`server/bridge/osc.py`)을 import하지 않고, 실행용 REST 엔드포인트를 신설하지 않으며, 제2 스크리닝 경로를 만들지 않는다(`test_architecture.py` 그린이 증거).
- **REQ-DASHUI-020** [Unwanted] — 본 SPEC **shall not** 게이트를 우회하거나 약화시키지 않는다 — 어떤 발화도 `gate.screen()` 없이 콘솔에 도달하지 않으며, 승인 사전 부여·승인 카드 억제가 없다.
- **REQ-DASHUI-021** [Unwanted] — the 대시보드 **shall not** 콘솔을 공격적으로 폴링하지 않는다 — 타이머 구동 자동 카탈로그 재질의 금지. 갱신 트리거는 접속 시 + 수동 새로고침뿐이다(OSC 왕복은 게이트+감사를 경유하는 비용 — SHOWUI가 확립한 refresh-on-demand 패턴 계승).
- **REQ-DASHUI-022** [Unwanted] — the 대시보드 **shall not** 2.4.2에서 죽은 것으로 실측된 경로(`Patch/Fixtures`, `DataPool/Presets`)를 사용하지 않는다 — 프리셋 열거는 `DataPool/PresetPools/<no>` 드릴다운 경유만 허용된다(tools.py:25-55 실측 기록).
- **REQ-DASHUI-023** [Unwanted] — v1의 프리셋 타일 **shall not** 콘솔에 적용(recall)되지 않고, 플러그인 타일 **shall not** 실행되지 않는다 — 둘 다 읽기 전용이다. (프리셋 recall은 programmer 상태를 변경하는 더 큰 안전 질문으로 §D에 이연 근거 기록.)

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC 2.4.2, 앱-콘솔 동일 머신 로컬 공존, OSC `127.0.0.1` UDP. site config(`osc_slot`/`receive_port`/`reply_port`)는 effective 값에서만 읽는다 — 하드코딩 금지.
- **기반 전제 (본 브랜치 실재 확인)**: SHOWUI-001 M1~M3이 본 브랜치의 조상이다 — 동결된 패널 프로토콜 계약(protocol.ts / messages.py 양측 allowlist), `server/web/panel.py`(카탈로그/핀/membership/`PanelRuntime.fire`), app.py `/ws` 패널 라우팅 + 패널 전용 세션 키. **주의**: SHOWUI M4/M5의 UI 커밋(857e9ed, 09e2c4f)은 본 브랜치의 조상이 **아니다**(research.md §3) — 본 브랜치의 UI는 채팅 단일 컬럼이며, 본 SPEC의 UI는 신규 작성이다.
- **EXECBODY-001 완료 전제**: 양성 본문 익스큐터의 `Go+ Executor <no>` single-press 게이트 통과(승인 0·`SaveShow` 0) 라이브 검증 완료. 미할당/미해석/블랙리스트 익스큐터의 fail-closed 보류는 무변경.
- **기술 스택**: 기존 그대로 — UI: React+Vite+Vitest, 서버: FastAPI+python-osc+pytest. **신규 런타임 의존성 0**.
- **콘솔측**: `console/lua/copilot_responder.lua` 무변경 소비(EXECBODY가 추가한 `resolve_path` 포함).

## D. 제외 범위 (Out of Scope)

### Out of Scope — 프리셋 적용(recall) / 플러그인 실행

- 프리셋 타일 press로 콘솔 programmer에 상태를 적용하는 동작 — programmer 오염·라이브 룩 훼손의 별도 안전 설계가 필요한 질문으로 후속 SPEC 이연. v1은 읽기 전용(REQ-DASHUI-023).
- 플러그인 타일 press 실행 — 플러그인 본문은 Lua이며 게이트의 커맨드 스크리닝 대상 모델 밖. v1 읽기 전용.

### Out of Scope — 페이더 / 연속 파라미터

- 페이더·rate·grand master 등 연속 파라미터 컨트롤 전반 — SHOWUI-001 DP1-① 이연 유지.

### Out of Scope — MAtricks / Worlds 섹션

- 선택-정형 어휘 풀은 한눈 대시보드의 v1 정보 가치가 낮아 제외(design.md §2 판단 근거). 경로 자체는 라이브 검증되어 있어 후속 추가 비용이 낮다.

### Out of Scope — 콘솔측 Lua 변경

- `copilot_responder.lua` 및 신규 콘솔측 Lua 일체 — 0건.

### Out of Scope — 비게이트 실행 경로

- 실행용 REST/HTTP 엔드포인트, 제2 스크리닝 경로, 대시보드 모듈의 OSC 표면 직접 import.

### Out of Scope — 자동 폴링 / 백그라운드 동기화

- 타이머 구동 카탈로그 폴링, 백그라운드 diff 동기화 — refresh-on-demand만(REQ-DASHUI-021).

### Out of Scope — 패널 편집 / 큐 에디터

- 핀 rename·reorder(SHOWUI DP1-③ 이연 유지), 큐리스트 타임라인 편집 UI.

### Out of Scope — 핀 UI (서버측 핀 기능의 v1 비노출)

- 본 브랜치 서버에 존재하는 핀 기능(`panel_pin`/`panel_unpin`, PinStore — messages.py:28-33, panel.py:61-71)의 UI 노출 전반 — v1 좌측 대시보드는 카탈로그 섹션만 렌더하며, `source: "pin"` 항목 렌더와 핀 생성/삭제 UI는 후속 SPEC으로 이연한다(기존 서버 엔드포인트는 무접촉·무변경 유지). 근거: v1 IA(design.md §2)의 목적은 풀 카탈로그 표면화이고, 핀 큐레이션 UX는 별도 설계 질문이다 — 침묵 탈락이 아닌 기록된 이연.

### Out of Scope — 타 브랜치 SHOWUI M4/M5 UI와의 병합 조정

- `feat/app-deploy-file-import` 브랜치에 존재하는 ShowPanel M4/M5 커밋과의 reconciliation은 본 SPEC 범위 밖의 브랜치 전략 결정이다(research.md §3에 위험으로 기록). 본 SPEC은 충돌 최소화를 위해 구별되는 컴포넌트 이름을 사용한다(plan.md §F D7).

## E. 참조 구현 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 복제/소비 원본 (file:line) |
|---|---|
| 라이브 검증 rig 경로 + 죽은 경로 기록 | `DEFAULT_RIG_CONTEXT_PATHS`(tools.py:65-76), 헤더 실측 주석(tools.py:25-64) |
| 드릴다운 + 질의 상한 | `DEFAULT_RIG_DRILLDOWN`(tools.py:81), `RIG_DRILLDOWN_QUERY_CAP`(tools.py:88), `PANEL_DRILLDOWN_QUERY_CAP`(panel.py:77) |
| 실패 사유 2종 구분 | `REASON_UNRESOLVED`/`REASON_UNREACHABLE`(tools.py:104-105) |
| 발화 카탈로그 소스의 닫힌 집합 | `PANEL_CATALOG_SECTIONS` @MX:ANCHOR(panel.py:118-132) |
| 게이트 경유 발화 단일 진입 | `PanelRuntime.fire`(panel.py:631-636), `playback_command` @MX:ANCHOR(panel.py:553-566) |
| 커맨드 동사의 닫힌 집합 | `PANEL_VERBS`(panel.py:510-512), `_TARGET_WORD`(panel.py:515) |
| 신규 메시지/이벤트 end-to-end 배선 | `review_decision` 선례 + 패널 5종 선례(messages.py:23-49, protocol.ts:158-176) |
| replace-not-merge 카탈로그 갱신 | `PanelCatalog` docstring(panel.py:135-143), reducer(protocol.ts:448-455) |
| fail-closed 재접속 소거 | `clearOnDisconnect`(protocol.ts:509-514) |
| 게이트 조회 seam | `deps.gate.state_port` 경유 lazy `panel_store()`(app.py:167-176) |
| 매크로 실행 형태 | 룰북 `00_grammar.md:60`(`Macro 3` — run by id/name), `10_object_model.md:26` |
| 익스큐터 콘솔 주소 해석 | EXECBODY-001 M6 `resolve_path`/ObjectList (커밋 6c08fd4) |
| 디자인 토큰 베이스 | `ui/src/styles.css` `:root`(styles.css:1-11), `.app` 860px 캡(styles.css:24-28 — 해제 필요) |
