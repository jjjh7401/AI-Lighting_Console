---
id: SPEC-COPILOT-SHOWUI-001
title: "연출 컨트롤 패널 — 채팅 옆 Show-Control Panel"
version: "0.2.1"
status: draft
created: 2026-07-22
updated: 2026-07-22
author: manager-spec
priority: P1
phase: "Post-MVP 연출 UI (v1.1.0 target)"
module: "ui/src/, server/web/"
lifecycle: spec-anchored
tags: "show-control, panel, websocket, protocol, safety-gate, live-rail, pin, rig-context, ui"
tier: L
related_specs: [SPEC-COPILOT-MVP-001, SPEC-COPILOT-DEPLOY-001]
---

# SPEC-COPILOT-SHOWUI-001 — 연출 컨트롤 패널 (Show-Control Panel)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-22 | manager-spec | 최초 작성 (draft). Plan-review gate(DP1) 승인 및 clarification 3건 해소 반영: ① **페이더 v1 제외** — 후속 SPEC으로 이연(초안 REQ-SHOWUI-021 [Where] 조건부 요구 삭제, §D Out of Scope 등재), ② **All Off = bounded enumeration** — 패널이 추적 중인 running executor들에 대한 개별 `Off Executor N` 번들, 광역 `Thru`/`*` 커맨드 금지, 한계(§A) 명시, ③ **편집 모드 v1 = unpin 전용** — rename/reorder 이연, 핀 순서는 append-only. 아티팩트 5종(spec/plan/acceptance/design/progress) 동시 생성. |
| 0.2.0 | 2026-07-22 | manager-spec | **Plan-audit iteration 1 fold-in (FAIL 0.81 → 필수 교정 6건, 문서 전용).** (F1) **정지 클래스 서로소 분리** — 정지 = 타일별 Off(항상 single-press·zero-step), All Off = 파괴적 발화-클래스(arm→fire 2-step); design.md §5 정지 불릿에서 "전역 All Off" 제거, REQ-012 재작성, AC-011 이진 검증화. (F2) REQ-010 커버 기계 AC 신설(**AC-SHOWUI-015**) + AC-014에 REQ-010 추적 주석. (F3) **REQ-SHOWUI-022 신설** — `panel_execute`/`panel_stop` target의 `parse_client_message`-시점 정수 검증 + 카탈로그/핀 스토어 membership 검증(검증 실패 시 error 이벤트, 번들 미구성·게이트 미호출); AC-005에 거부 케이스 추가. (F4) 복합 REQ 분할 — REQ-004→004(pin)+**023**(unpin), REQ-019→019(모달 금지)+**024**(arm→fire)+**025**(All Off bounded 구성)+**026**(광역 타깃 금지). 잔여 복합 REQ(005/007/014/015)는 각 절이 개별 AC에 매핑되어 있음을 근거로 **singularity debt로 존치**하며 본 HISTORY 행이 그 기록이다. (F5) REQ-014 측별 재서술 — TS 클라이언트 silent-drop(`null`, protocol.ts:128-129) vs 서버 `ProtocolError` 명시 거부(messages.py:46-50, app.py:230-234). (F6) "대기 중인 실행 큐" 서술 삭제(큐는 존재하지 않음, REQ-011) — `panel_stop`은 1-in-flight busy 가드에서 **면제**되며 진행 중 execute와 동시 `gate.screen()` 호출 허용을 명시. ⚠️ **번호 규약**: REQ-SHOWUI-021은 소각(burned — 삭제된 페이더 초안, v0.1.0 HISTORY 참조)으로 **영구 결번**이며 신규 번호는 022부터 이어진다. |
| 0.2.1 | 2026-07-22 | manager-spec | **Plan-audit iteration 2 PASS(0.93) 후 fix-forward 정리 (비차단, 문서 전용, 재감사 불요).** (R1) 4개 아티팩트 헤더·frontmatter 버전 정렬 — plan.md 헤더가 v0.1.0에 잔류하던 드리프트 해소, spec/acceptance/design 포함 전부 **v0.2.1**로 통일. (R3, gate-인접 정정) REQ-012의 "clearance 소비는 번들 단위이므로 동시 stop 번들과 양립한다(gate.py:269-272)" 서술이 코드와 **정반대**임을 정정 — `screen()`은 동일 세션 키의 clearance Counter를 매 번들마다 **리셋**하므로 두 번째로 screen되는 번들이 첫 번들의 미소비 clearance를 무효화한다. 재작성: `panel_stop`은 busy 가드에서 면제되어 동시 screen 가능하되, clearance가 세션-키드이고 screen()마다 리셋되므로 **실패 방향이 안전(과다 차단이지 우회 아님)**이며 stop-preempts-execute가 의도된 순서임을 명시(거짓 "두 번들 clearance 공존" 전제를 manager-develop에 넘기지 않음). AC-009의 동시성 assert가 기계적 backstop으로 유지. (R2) plan.md의 미분화 "silent-drop" 표현을 REQ-014의 측별 계약(TS null-drop vs 서버 ProtocolError)에 정렬. (R4) AC-011에 REQ-025 양성 구성 assert 추가 — All Off 번들 == 추적 running executor당 정확히 `Off Executor N` 1개. |

## A. 개요

본 SPEC은 채팅과 나란히 붙는 **시각적 연출 컨트롤 패널**을 정의한다. AI가 채팅에서 만든 룩/이펙트/시퀀스와 콘솔의 기존 시퀀스/익스큐터를 **버튼·컬러칩 타일**로 표면화해, 조명 오퍼레이터가 **한 번의 시선과 한 번의 누름**으로 실행/정지할 수 있게 한다 (interview Round 1: "연출 컨트롤 패널" 선택).

아키텍처 전제 (interview Round 1 결정): **기존 파이프라인 전면 재사용** — 현재의 WebSocket + OSC 응답기 + `get_rig_context` 경로를 그대로 사용하고, UI는 서버 API만 호출한다. 새 콘솔측 Lua 추가는 0건이다(`copilot_responder.lua` 무변경). 실행은 기존 안전 게이트의 **유일한 스크리닝 경로**(`gate.screen()`, gate.py:260-264 `@MX:ANCHOR`)를 경유하는 신규 게이트 WS 메시지 타입(`panel_execute` / `panel_stop`)으로 흐른다 — 제2의 실행 경로는 구성상 금지된다.

패널 항목의 출처는 하이브리드다 (interview Round 2 결정):

1. **AI-pin**: 채팅에서 AI가 연출을 만들면 "패널에 추가" 버튼으로 고정 — 서버측 `_last_created` 크로스턴 메모리(session.py:354-389)를 시드로 사용.
2. **rig 자동 나열**: 콘솔의 기존 시퀀스/익스큐터를 `get_rig_context` 데이터 형상(sequences + pages executor drill-down)으로 읽어 자동 나열.

### 사전 확정 사실 (합의된 접근 — 재질의 금지)

- **패널 형태**: 채팅 옆 2컬럼(접기 가능) 연출 컨트롤 패널. 타임라인/큐 에디터 아님 (interview R1).
- **데이터 흐름**: 기존 WS + OSC + `get_rig_context` 재사용, UI는 서버 API만 호출, 콘솔측 Lua 무변경 (interview R1).
- **항목 출처**: AI-pin + rig 자동 나열 하이브리드 (interview R2).
- **완료 기준**: 실제 onPC에서 패널 버튼 → 연출 실행/정지 라이브 검증 + pytest/vitest 전체 그린 (interview R2).
- **DP1 해소 ① 페이더**: v1 **제외**, 후속 SPEC으로 이연 (§D).
- **DP1 해소 ② All Off**: **bounded enumeration** — 패널이 추적하는 running executor 개별 `Off Executor N`, 광역 `Thru` 금지 (§A 한계, REQ-SHOWUI-025/026).
- **DP1 해소 ③ 편집 모드**: v1은 **unpin 전용**. rename/reorder 없음, 핀 순서는 append-only (§D).
- **실행 라우팅**: 채팅 지시 경유가 아닌 **전용 게이트 WS 핸들러**(research.md Recommendations 1 — option (b)). 채팅의 단일 지시 턴 락과 독립 직렬화.

### ⚠️ All Off의 명시적 한계 (bounded enumeration)

패널의 All Off는 **패널이 추적 중인 running executor들만** 개별 `Off Executor N` 커맨드로 정지한다. **패널이 모르는 콘솔측 재생**(콘솔에서 직접 올린 executor, 채팅/패널 밖에서 시작된 재생)은 이 All Off로 **정지되지 않는다.** 이는 의도된 트레이드오프다 — 광역 타깃 커맨드(`Off Executor Thru`, `*`, `Everything`)는 위험 분류기(classify.py:162-230)가 개방형 타깃으로 승인 보류시키므로, 쇼 진행 중 블랙아웃 순간에 승인 카드가 뜨는 사고를 원천 배제하기 위해 광역 커맨드를 금지한다. 전체 무대 정지가 필요한 경우 콘솔 자체의 Off 조작을 사용한다. 이 한계는 UI에도 명시된다 (design.md §6).

## B. 요구사항 (GEARS)

### B.1 패널 카탈로그 (rig 자동 나열)

- **REQ-SHOWUI-001** [Ubiquitous] — The 패널 카탈로그 **shall** 기존 `get_rig_context` 데이터 형상(`_rig_section`/`_rig_object`, tools.py:169-212)을 재사용하여 `sequences` + `pages`(executor drill-down 포함, tools.py:215-256)로부터 실행 가능 타일 목록을 구성하며, `truncated` / `contents_unavailable` / `drilldown_capped` 플래그를 UI까지 전달한다.
- **REQ-SHOWUI-002** [Event-driven] — **When** UI가 패널 카탈로그를 요청하면(접속 직후 + 수동 새로고침), the 서버 **shall** `gate.state_port` 조회 경로(감사되는 동일 chokepoint, session.py:202, gate.py:598-607)를 통해 카탈로그를 생성해 신규 서버 이벤트로 회신하고, 실패 섹션은 `path_not_resolved`와 `console_unreachable`을 **구분된 상태로** 표면화한다(tools.py:100-108 — 두 사유의 병합 금지).
- **REQ-SHOWUI-003** [Unwanted] — The 패널 **shall not** 항목을 배열 인덱스로 키잉하지 않는다 — 항상 실제 `no`로 키잉한다(비연속 풀 번호, tools.py:164-168). 아울러 the 패널 **shall not** `fixtures` 섹션으로 실행 타일을 구성하지 않는다(fixture `no`=패치 슬롯≠FID gotcha, tools.py:36-44 — 실행 대상은 `no`가 곧 주소인 sequences/pages 한정).

### B.2 채팅 → 핀 (패널에 추가)

- **REQ-SHOWUI-004** [Event-driven] — **When** 사용자가 채팅에서 생성된 연출에 "패널에 추가"를 누르면, the 서버 **shall** 기존 `_last_created` 크로스턴 메모리(session.py:354-389)를 시드로 핀 항목(이름·시퀀스/익스큐터 대상·타입·어피어런스 컬러)을 생성해 패널에 추가한다.
- **REQ-SHOWUI-023** [Event-driven] *(v0.2.0 — REQ-004에서 분할, F4)* — **When** 사용자가 핀 항목의 제거(unpin)를 요청하면, the 서버 **shall** 해당 항목을 제거하고 영속 상태에 반영한다. (참고: v1 편집 범위는 unpin 전용 — rename/reorder 제외는 §D, append-only 순서 의무는 REQ-SHOWUI-005 소관.)
- **REQ-SHOWUI-005** [Ubiquitous] — The 핀 항목 **shall** 서버측 사용자 데이터 디렉터리(`user_data_dir`, settings.py:184-192)의 전용 JSON 파일에 원자적 쓰기(temp + `os.replace`, settings.py:383-404 패턴)로 영속화되고, 자격 증명을 절대 포함하지 않으며, 서버 재시작 후에도 유지된다. The UI **shall not** localStorage 등 클라이언트측 영속 저장을 사용하지 않는다(서버 단일 진실원 유지).

### B.3 게이트 경유 실행/정지

- **REQ-SHOWUI-006** [Event-driven] — **When** `panel_execute` / `panel_stop` 메시지가 수신되면, the 서버 **shall** 해당 항목의 재생 커맨드 번들(`Go+ Executor N` / `Off Executor N` — 룰북 31_choreography_patterns.md "Playback")을 구성해 **`gate.screen()`을 경유**시키고, 기존 계약 그대로 clearance 토큰 1개당 송신 1회·감사 로그 1:1(gate.py:549-573)을 유지한다.
- **REQ-SHOWUI-022** [Event-driven] *(v0.2.0 신설 — F3; 021은 소각 결번)* — **When** `panel_execute` / `panel_stop` 메시지가 파싱되면, the 서버 **shall** target 필드를 `parse_client_message` 시점에 정수 `no`로 검증하고(`review_decision` 필드 검증 선례, messages.py:58-70), 번들 구성 전에 해당 target이 현재 카탈로그 또는 핀 스토어에 존재하는 항목인지 membership 검증한다 — 기형(비정수·음수·누락)·미지 target은 명시적 error 이벤트로 거부되며, 그 어떤 경우에도 커맨드 번들이 구성되거나 `gate.screen()`이 호출되지 않는다.
- **REQ-SHOWUI-007** [Ubiquitous] — 스크리닝 경로 **shall** 정확히 하나만 존재한다(gate.py:260-264 `@MX:ANCHOR`). 패널 관련 모듈 **shall not** OSC 송신 표면(`server/bridge/osc.py`)을 import하지 않으며, 실행용 REST 엔드포인트를 신설하지 않는다(settings_api.py:104-112 라우터 경계 관례 계승; `test_architecture.py` 통과가 증거).
- **REQ-SHOWUI-008** [Event-driven] — **When** 패널발 번들이 스크리닝에서 승인 보류로 분류되면(파괴적·미확인 이력 등, classify.py:83-230), the UI **shall** 기존 ApprovalCard 플로우(App.tsx:63-69)로 승인/거부를 표면화하고 all-or-nothing 계약(gate.py:299-315)을 유지한다.
- **REQ-SHOWUI-009** [State-driven] — **While** LiveLock이 활성인 동안, 패널발 실행 **shall** 제안(Proposal) 전용으로 강등되고 콘솔 송신은 0건이며(lock.py, gate.py:464-486), the 패널 타일 **shall** 비활성/제안 상태로 렌더된다. 승인 후 lock-FIRST 재확인(REQ-MVP-035, gate.py:318-324)은 그대로 계승된다.
- **REQ-SHOWUI-010** [State-driven] — **While** `status.health ≠ online` 또는 `executions_blocked`인 동안, the 패널 **shall** 차단 상태를 타일·패널 레벨에서 표시하고 신규 발화 시도를 사전에 막거나 차단 결과를 명시적으로 표면화한다(protocol.ts:85-99의 기존 status 이벤트 소비; 값은 항상 effective 설정에서 읽고 하드코딩하지 않는다).

### B.4 상호작용 직렬화 (버튼 연타 처리)

- **REQ-SHOWUI-011** [Event-driven] — **When** 패널 실행이 진행 중인 상태에서 추가 `panel_execute`가 도착하면, the 서버 **shall** 해당 요청에 busy 응답을 회신하고 동시 실행하지 않는다(패널 자체 1-in-flight 직렬화). The UI **shall** 발화 직후 타일을 잠가 연타를 1회 결정으로 수렴시킨다(`createDecisionGuard` 재사용, ApprovalCard.tsx:16-26).
- **REQ-SHOWUI-012** [Ubiquitous] *(v0.2.1 재작성 — F1/F6 + R3 gate 정정)* — `panel_stop`(타일별 Off — **정지 클래스**) **shall** 1-in-flight busy 가드(REQ-SHOWUI-011)의 적용 대상에서 **면제**된다: 진행 중인 `panel_execute`가 있어도 busy 응답 없이 즉시 처리되며(정지는 항상 single-press·zero-wait — design.md §5), 진행 중 execute와 **동시에** `gate.screen()`을 호출할 수 있다. **clearance 공존 가정 금지**: clearance Counter는 **세션-키드**이고 `screen()`은 매 번들마다 이를 **리셋**하므로(gate.py:269-272), 두 번들이 같은 세션 키로 순차 screen되면 나중 번들이 앞 번들의 미소비 clearance를 무효화한다 — 즉 두 번들의 clearance는 **공존하지 않는다.** 이 세션-키드 리셋 의미론의 실패 방향은 **안전**하다: 최악의 경우 앞 execute가 clearance를 잃어 **과다 차단(over-block)**될 뿐 게이트 우회는 구조적으로 불가능하며, `panel_stop`이 진행 중 execute를 선점(stop-preempts-execute)하는 것이 **의도된 순서**다. 정지 커맨드 역시 `gate.screen()`을 경유한다 — 면제는 스케줄링 속성이지 게이트 우회가 아니다. **전역 All Off는 이 정지 클래스에 속하지 않는다**(파괴적 발화-클래스 — REQ-SHOWUI-024/025/026).
- **REQ-SHOWUI-013** [Unwanted] — 패널 실행 **shall not** 채팅의 단일 지시 턴 락(app.py:236-242)을 점유하지 않는다 — 채팅 LLM 턴 진행 중에도 패널 정지/실행이 가능해야 하며, 두 경로는 독립적으로 직렬화된다.

### B.5 프로토콜 추가 규율

- **REQ-SHOWUI-014** [Ubiquitous] *(v0.2.0 재작성 — F5)* — `PROTOCOL_VERSION` **shall** 1을 유지한다. 신규 메시지/이벤트 타입 **shall** 양측 allowlist(`CLIENT_MESSAGE_TYPES` messages.py:23 + `SERVER_EVENT_TYPES` protocol.ts:105-116)와 reducer/handler에 **모두** 등록된다. 미등록 타입 처리 계약은 **측별로 상이하며 각각** 회귀 없이 보존된다 — TS 클라이언트는 미지 타입을 silent-drop한다(`parseServerEvent` → `null`, protocol.ts:128-129); 서버는 `ProtocolError`로 명시 거부하고 error 이벤트를 회신한다(messages.py:46-50, app.py:230-234).

### B.6 Fail-closed 재접속 의미론

- **REQ-SHOWUI-015** [Event-driven] — **When** WebSocket이 닫히면, the UI **shall** 패널의 running 상태를 즉시 소거한다(파생·휘발 상태 — 기존 `disconnected` 액션 관례, useCopilotSocket.ts:102-108, protocol.ts:308-311). **When** 재접속되면, the UI **shall** 카탈로그 + status 재동기화를 요청해 패널 상태를 재구축한다.
- **REQ-SHOWUI-016** [Unwanted] — The 패널 **shall not** running 상태가 재접속을 넘어 생존한다고 가정하지 않으며, 미확인(unconfirmed) 명령의 자동 재전송 금지(REQ-MVP-032, gate.py:448-453)를 그대로 계승한다.

### B.7 레이아웃 + 디자인 방향 준수

- **REQ-SHOWUI-017** [Ubiquitous] — The UI **shall** 채팅과 패널의 2컬럼 레이아웃(패널 접기 가능, chat-first 보존)을 제공하고, 타일 그리드 위치 **shall** 쇼 중 안정적으로 유지된다 — 자동 정렬·재배치 금지, 신규 항목은 append (design.md §2 Executor / §7).
- **REQ-SHOWUI-018** [Ubiquitous] — 모든 패널 타일 **shall** Live Rail 해부구조(어피어런스 컬러칩 + 이름/타입 배지 + 하단 상태 레일 — design.md §4)를 공유하고, live-amber(`#ffb02e` 계열) **shall** 실행 중 상태 전용으로만 사용되며, 상태는 색상 단독으로 전달되지 않는다(`RUN`/`OFF` 배지 병행, 최소 15px 라벨).
- **REQ-SHOWUI-019** [Unwanted] *(v0.2.0 분할 — F4; 모달 금지만 잔류)* — The 패널 **shall not** 발화 확인 모달(`window.confirm` 류)을 사용하지 않는다 — 안전은 모달이 아니라 레일 기반 arm→fire(REQ-SHOWUI-024)와 지속 상태 표시가 담당한다(design.md §5).
- **REQ-SHOWUI-024** [Ubiquitous] *(v0.2.0 — REQ-019에서 분할, F4)* — 파괴적 발화-클래스 패널 액션(All Off, 블랙아웃급 룩) **shall** 레일 기반 arm→fire 2-step으로 보호된다. 정지 클래스(타일별 Off)는 이 클래스에 속하지 않는다(두 클래스는 서로소 — single-press 의무는 REQ-SHOWUI-012 소관).
- **REQ-SHOWUI-025** [Ubiquitous] *(v0.2.0 — REQ-019에서 분할, F4; DP1-②)* — All Off 번들 **shall** 패널이 추적 중인 running executor들에 대한 **개별 `Off Executor N` 커맨드의 bounded enumeration**으로 구성된다. 패널이 모르는 콘솔측 재생이 정지되지 않는 한계는 §A에 명시된 의도된 트레이드오프이며 UI에도 표기된다(design.md §6).
- **REQ-SHOWUI-026** [Unwanted] *(v0.2.0 — REQ-019에서 분할, F4; DP1-②)* — All Off 번들 **shall not** 광역 타깃 커맨드(`Thru`, `*`, `Everything`)를 사용하지 않는다 — 위험 분류기의 개방형 타깃 승인 보류(classify.py:162-230)를 쇼 중에 유발하지 않기 위함이다.
- **REQ-SHOWUI-020** [Ubiquitous] — 타일 동사 **shall** 콘솔 어휘(`Go+`, `Off`)를 사용하며(미디어 플레이어 은유 금지 — design.md §7), the 패널 **shall** 다크 전용(`color-scheme: dark`)이다.

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 **동일 머신** 로컬 공존(SPEC-COPILOT-DEPLOY-001 HARD 제약 계승). OSC는 `127.0.0.1` UDP. site config(`osc_slot`, `receive_port`, `reply_port`)는 항상 effective 값(`/api/settings` / status 이벤트)에서 읽는다 — 하드코딩 금지 (research.md Risks 5-6; 알려진 reply-port drift 서명 대응).
- **기능 전제**: SPEC-COPILOT-MVP-001의 파이프라인(WS 프로토콜 v1, `gate.screen()` 단일 관문, `get_rig_context`, ApprovalCard/ReviewCard 플로우, `_last_created` 메모리)은 기능 구현·라이브 검증 완료 상태다. MVP-001의 frontmatter `status`가 `in-progress`이므로 `depends_on`이 아닌 `related_specs`로 참조한다 — 엄격 충족(completed) 전제의 pre-flight 차단을 피하기 위함(DEPLOY-001 D6 `--ignore-deps` 정합 관례의 교훈).
- **안전 불변식 계승 (무변경)**: health gate, 문법 검증, 위험 분류(승인 보류), LiveLock(lock-FIRST 재확인 포함), deny-all 기본 승인 포트, 위험 명령 사전 쇼파일 백업 fail-closed, 미확인 이력 재승인·자동 재전송 금지 — 전부 `gate.screen()` 파이프라인(gate.py:265-358)에 있으며 본 SPEC은 이를 소비만 하고 수정하지 않는다.
- **기술 스택**: 기존 스택 그대로 — UI: React + Vite + Vitest, 서버: FastAPI + python-osc + pytest. **신규 런타임 의존성 0** (영속화는 stdlib `json` + `os.replace`).
- **콘솔측**: `console/lua/copilot_responder.lua` 무변경. 슬롯 해석 계약(responder.lua:189-311) 그대로 소비.

## D. 제외 범위 (Out of Scope)

### Out of Scope — 타임라인/큐 에디터

- 큐리스트 타임라인 편집 UI. 사용자가 interview Round 1에서 패널 형태를 선택하며 명시적으로 이연.

### Out of Scope — 페이더 컨트롤 (후속 SPEC)

- 페이더(grand master / speed master / rate 조절) 전반 — **DP1 clarification ①에서 v1 제외 확정, 후속 SPEC으로 이연.** 초안의 [Where] 조건부 요구(구 REQ-SHOWUI-021)는 삭제되었다.
- 연속 파라미터 스트리밍(fader value stream)도 함께 제외 — 재개 시에도 이산 게이트 커맨드 발행이 전제다.

### Out of Scope — 콘솔측 Lua 변경

- `copilot_responder.lua` 및 신규 콘솔측 Lua 일체. interview R1: "새 콘솔측 Lua 추가 최소화" — 본 SPEC의 목표치는 0건.

### Out of Scope — 비게이트 실행 경로

- 실행용 REST/HTTP 엔드포인트, 제2의 스크리닝 경로, 패널 모듈의 OSC 표면 직접 import (gate.py:260-264 ANCHOR + settings_api.py:104-112 경계).

### Out of Scope — 채팅 경로 변경

- `chat → LLM → run_commands` 경로는 무변경. 패널은 채팅 지시를 경유해 실행하지 않는다.

### Out of Scope — 패널에서의 연출 편집 (programming)

- 패널에서 룩 내용 수정/저장(programming: Store, ChangeDestination 계열). 생성/수정은 채팅 담당, 패널은 재생 전용(playback-only) — `ChangeDestination Root` programming-vs-patch 함정을 패널에서 구조적으로 제거.

### Out of Scope — 패널 편집 모드 (rename/reorder)

- 핀 항목의 rename·수동 reorder — **DP1 clarification ③에서 v1 unpin 전용 확정.** 핀 순서는 append-only. rename/reorder는 이연 항목으로 기록.

### Out of Scope — 자동 정렬/재배치

- recently-used 정렬, 알파벳 정렬, 쇼 중 타일 reflow (design.md §7 — 오퍼레이터 타깃 위치 안정성 우선).

### Out of Scope — 라이브 잠금 중 자율 실행

- LiveLock 활성 중 어떤 형태의 콘솔 송신도 없음 — 제안 카드 전용. 제품 비목표(product.md §6) 그대로 계승.

## E. 참조 구현 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 복제 원본 (file:line) |
|---|---|
| 신규 client→server 메시지 end-to-end | `review_decision` 배선: messages.py:23,58-70 → app.py:260-276 → protocol.ts:148-155 → useCopilotSocket.ts:140-143 |
| 신규 server→client 이벤트/카드 플로우 | `review_request_event`(messages.py:115-146) + union/reducer 등록(protocol.ts:79-84, 241-256) |
| 제2 확인 채널(패널 보류 번들용, 필요 시) | payload-agnostic `ApprovalChannel` 2번째 인스턴스(approval_bridge.py:19-27, serve.py:329-338) |
| 카탈로그 데이터 형상 + 섹션별 의미론 | `_rig_object`/`_rig_section`/drill-down(tools.py:169-256), `DEFAULT_RIG_CONTEXT_PATHS`(tools.py:65-76) |
| 게이트 경유 조회 seam | `gate.state_port`(session.py:202, gate.py:114-121, 598-607) |
| 원자적 영속화 + 자격 증명 거부 관례 | settings.py:383-404(temp+`os.replace`), settings.py:248-280 |
| 핀 시드 출처 | `_last_created`/`_session_context_note`(session.py:189-192, 354-389) |
| 1회성 누름 멱등 가드 | `createDecisionGuard`(ApprovalCard.tsx:16-26, 41-49) |
| 항목별 실행 상태 어휘 | `statusClass`(ChatView.tsx:5-19) |
| 접기형 패널 영역 선례 | `SettingsPanel` 오버레이(App.tsx:18,60; styles.css:409-421) |
| 상태 fan-out(패널 상태 브로드캐스트) | `deps.status_listeners`+`push_status`(app.py:108-111, 219-222) |
| 재생 동사 | 룰북 `31_choreography_patterns.md` "Playback"(`Go+ Executor N`/`Off Executor N`) |
