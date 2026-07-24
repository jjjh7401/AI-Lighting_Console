# SPEC-COPILOT-DASHUI-001 — 인수 기준 (acceptance)

status: draft (v0.1.0, 2026-07-24) · Tier L · 기계 검증 가능(pytest/vitest) 항목과 LIVE(실제 onPC) 항목을 구분한다. AC는 GEARS 패턴 문장으로 시작하고 검증 레시피를 하위 상세로 보존한다(EXECBODY-001 관례).

## §A. 완료 정의 (Definition of Done)

1. AC-DASHUI-001..013 + AC-DASHUI-016 전부 기계 검증 그린 (pytest 전체 + vitest 전체).
2. AC-DASHUI-014/015 라이브 체크리스트를 실제 onPC 2.4.2에서 수행·기록 (증적은 progress.md §E.2).
3. `test_architecture.py` 그린 (신규 대시 모듈의 OSC 표면 미접촉).
4. `server/web/PROTOCOL.md` 신규 타입/enum 반영 완료.
5. 신규 런타임 의존성 0 유지.
6. 매크로 press가 라이브 편차로 축소(read-only 강등)된 경우: 그 결정과 근거가 progress.md §E.2에 명시적 섹션으로 기록되고 AC-DASHUI-006/014 해당 항목은 "미달성"으로 정직하게 표기된다(EXECBODY AP-8 원칙 — 부분 성공을 성공으로 위장하지 않는다).

## §B. Given-When-Then 시나리오

### 시나리오 1 — 대시보드 로드 (REQ-004/005/006/018)

- **Given** 콘솔 online, showfile에 그룹/시퀀스/프리셋/매크로가 존재한다.
- **When** UI가 접속한다(또는 수동 새로고침을 누른다).
- **Then** 좌측 대시보드가 풀 섹션들을 실제 `no` 키잉으로 렌더하고, 마지막 동기화 시각이 표기되며, 실패한 섹션은 `path_not_resolved`/`console_unreachable`이 구분되어 표기된다. 갱신은 전체 교체다(이전 항목 잔존 없음).

### 시나리오 2 — 시퀀스/익스큐터 타일 발화·정지 (REQ-010/011)

- **Given** 카탈로그에 Sequence 41 타일과 해석된 콘솔 번호를 가진 익스큐터 타일이 있다.
- **When** 오퍼레이터가 타일의 `Go+`를 1회 누른다.
- **Then** `gate.screen()`을 통과한 커맨드가 정확히 1회 송신되고 감사 로그 1건이 남으며 타일이 RUN 상태가 된다. **When** `Off`를 누른다. **Then** 정지 커맨드가 송신되고 OFF로 복귀한다.

### 시나리오 3 — 매크로 press의 게이트 경유 (REQ-012/020)

- **Given** 본문이 양성인 Macro 3과 본문에 블랙리스트 커맨드를 포함한 Macro 9가 카탈로그에 있다.
- **When** Macro 3 타일을 누른다. **Then** `Macro 3` 번들이 `gate.screen()`을 경유해 송신된다(감사 1:1).
- **When** Macro 9 타일을 누른다. **Then** 게이트가 보류하고 ApprovalCard가 표면화된다 — 우회 없음, 조용한 무시 없음.

### 시나리오 4 — 정보 타일은 구조적으로 발화 불가 (REQ-007/023)

- **Given** 그룹/프리셋/플러그인 정보 타일이 렌더되어 있다.
- **When** 악의적/기형 클라이언트가 정보 전용 대상(예: group의 `no`)으로 `panel_execute`를 보낸다.
- **Then** membership 검증이 거부하고 error 이벤트가 회신되며, 번들 구성·`gate.screen()` 호출은 0건이다.

### 시나리오 5 — LiveLock 강등 (REQ-013)

- **Given** LiveLock이 활성이다.
- **When** 대시보드의 발화 가능 타일을 누른다.
- **Then** 콘솔 송신 0건, 제안(Proposal) 전용 결과가 회신되고, 발화 가능 타일은 비활성/제안 상태로 렌더된다.

### 시나리오 6 — 분할 레이아웃과 채팅 무손상 (REQ-001/002)

- **Given** 분할 레이아웃이 렌더되어 있다.
- **When** 사용자가 채팅으로 지시를 보내고 승인 카드를 처리한다. **Then** 채팅 파이프라인 전부가 기존과 동일하게 동작한다.
- **When** 좌측 대시보드를 접는다. **Then** chat-first 단일 컬럼 경험이 보존된다.

## §C. AC 표 (GEARS 형식 — 검증 레시피는 하위 상세)

### AC-DASHUI-001 — 프로토콜 양측 패리티 (additive)

**When** 신규 타입(`dash_catalog_request`/`dash_catalog`)과 `target_kind` enum 확장(`macro`)이 파싱되면, the 양측 프로토콜 계층 **shall** 이를 수락하고 미등록 타입의 측별 계약(TS null-drop / 서버 ProtocolError)을 회귀 없이 보존한다.

- 대상: REQ-DASHUI-006/010 (M1)
- 검증: pytest `test_web_messages.py`(신규 타입 수락 + 기형 거부), vitest `protocol.test.ts`(신규 이벤트 수락, `v!==1`/미지 타입 여전히 `null`), `PROTOCOL_VERSION == 1` 양측 assert

### AC-DASHUI-002 — 대시 카탈로그 정확성

**When** 대시 카탈로그가 가짜 state port 픽스처로 빌드되면, the 빌더 **shall** 실제 `no` 키잉(비연속 번호), 실패 사유 2종 구분, `truncated`/`drilldown_capped`/`contents_unavailable` 3종 플래그 전파, replace 의미론을 전부 보존한다.

- 대상: REQ-DASHUI-004/005/006/008
- 검증: pytest `test_web_dash.py`(신규) — 비연속 픽스처, 형제-응답 있는 실패(`path_not_resolved`) vs 무응답(`console_unreachable`), 드릴다운 예산 소진 시 `drilldown_capped` 표기

### AC-DASHUI-003 — 정보 타일 구조적 발화 불가

정보 전용 데이터 형상 **shall not** 발화 가능 `target_kind`를 나르지 않으며, membership 검증 **shall not** 정보 전용 대상을 발화 대상으로 승인하지 않는다.

- 대상: REQ-DASHUI-007/023
- 검증: pytest — 정보 전용 대상으로의 `panel_execute` → membership 거부 + error 이벤트 + `gate.screen()` 미호출 assert; 타입 레벨 — DashItem에 target_kind 필드 부재

### AC-DASHUI-004 — 픽스처 요약·FID 비제시

픽스처 섹션 **shall** 카운트 요약(+truncated)으로만 제공되며, the 대시보드 **shall not** 픽스처 발화 타일을 만들거나 슬롯 번호를 FID로 제시하지 않는다.

- 대상: REQ-DASHUI-009/022
- 검증: pytest — 픽스처 경로가 채워진 트리에서 발화 타일 0건 + 요약 카운트 정확; vitest — 요약 카드에 "FID" 표기 부재

### AC-DASHUI-005 — 시퀀스/익스큐터 발화 경로 무변경 + 해석된 번호

**When** 시퀀스/익스큐터 타일 발화가 실행되면, the 경로 **shall** 기존 `panel_execute`/`panel_stop` → `gate.screen()` 계약(송신 1회당 감사 1건, clearance 없으면 송신 0건)을 그대로 사용하고, 익스큐터 target은 해석된 콘솔 번호다.

- 대상: REQ-DASHUI-010/011
- 검증: pytest `test_web_panel_execute.py` 회귀 그린 + 신규 케이스(해석 매핑 픽스처); 코드 리뷰 — 자식 인덱스·무조건 `+100` 오프셋 발화 경로 부재(EXECBODY AC-016 교차 확인)

### AC-DASHUI-006 — 매크로 press 게이트 경유

**When** 매크로 타일이 눌리면, the 서버 **shall** 정확히 `["Macro <no>"]` 번들을 구성해 `gate.screen()`을 경유시키며, 본문 블랙리스트/해석 불가 매크로는 보류되어 ApprovalCard로 표면화된다.

- 대상: REQ-DASHUI-012/020
- 검증: pytest — 양성 매크로: 번들 == `["Macro N"]`·감사 1:1; 블랙리스트 본문 매크로: 보류(`_hold`)·approval_request 왕복; 해석 불가: 보류(fail-closed). (라이브 확인은 AC-014 ⑤)

### AC-DASHUI-007 — LiveLock 강등

**While** LiveLock이 활성인 동안, 대시보드발 발화 **shall** 제안 전용(송신 0건)이며 발화 가능 타일은 비활성/제안 상태로 렌더된다.

- 대상: REQ-DASHUI-013
- 검증: pytest — LiveLock + `panel_execute`(macro 포함) → 제안 생성·송신 0건; vitest — `live_lock` 상태 타일 렌더 assert

### AC-DASHUI-008 — 차단 상태 표면화

**While** `status.health ≠ online` 또는 `executions_blocked`인 동안, the 대시보드 **shall** 차단 상태를 표시하고 발화 시도를 사전에 막거나 차단 결과를 명시적으로 회신한다.

- 대상: REQ-DASHUI-014
- 검증: vitest — 차단 배너 + 발화 타일 비활성 렌더; pytest — 차단 상태 `panel_execute` → 명시적 차단 결과 회신(조용히 삼켜지지 않음)

### AC-DASHUI-009 — 분할 레이아웃 + 채팅 무손상 + 접기

The UI **shall** 분할 레이아웃에서 채팅 기능 전부를 무손상 제공하고, 좌측 접기 시 chat-first 단일 컬럼을 보존한다.

- 대상: REQ-DASHUI-001/002
- 검증: vitest — 분할 상태에서 composer 입력/전송, ApprovalCard/ReviewCard/SettingsPanel 렌더·동작; 접기 토글 후 대시보드 미렌더 + 채팅 정상; 접힘 상태 비영속(리마운트 시 기본값) assert

### AC-DASHUI-010 — onPC 풀 시각 언어 준수

풀 섹션 렌더 **shall** 넘버드 슬롯 셀(슬롯 번호 1급 요소)·점유/빈 구분·풀 타입 구분을 제공하고, live-amber 배타·15px 하한·콘솔 어휘 규칙을 유지한다.

- 대상: REQ-DASHUI-003/016/017
- 검증: vitest 컴포넌트 테스트 + 스타일 가드(SHOWUI M4 stylesheet-guard 패턴): live-amber가 running 외 사용 0건, 라벨 최소 15px, `grep -rn "window.confirm" ui/src/` 0건, 정렬/reflow 부재(입력 순서 == 렌더 순서, `no` 순 고정)

### AC-DASHUI-011 — 폴링 부재 (refresh-on-demand)

The 대시보드 **shall not** 타이머 구동 자동 카탈로그 재질의를 수행하지 않는다 — 갱신 트리거는 접속 시 + 수동 새로고침뿐이다.

- 대상: REQ-DASHUI-021
- 검증: 코드 리뷰 + `grep -rn "setInterval\|setTimeout" ui/src/components/DashBoard.tsx ui/src/components/Pool*.tsx`(카탈로그 재질의 목적 사용 0건); vitest — 수동 새로고침 버튼이 요청 1회 dispatch, 시간 경과만으로 요청 0회

### AC-DASHUI-012 — 신선도/섹션 헬스 렌더

The 대시보드 **shall** 마지막 동기화 시각과 섹션별 실패/부분 상태(사유 구분)를 렌더한다.

- 대상: REQ-DASHUI-018
- 검증: vitest — 동기화 시각 표기, `path_not_resolved` vs `console_unreachable` 구분 렌더, `drilldown_capped`/`truncated` 힌트 렌더

### AC-DASHUI-013 — 전체 회귀 (협상 불가)

전체 회귀 스위트 **shall** run-phase 킥오프 기준선 대비 신규 실패 0건을 유지한다.

- 대상: (의도적 REQ 무연결 — 전역 품질 게이트)
- 검증: `.venv/bin/python -m pytest -q` + `(cd ui && npx vitest run)` — 신규 실패 0건

### AC-DASHUI-014 (LIVE) — 실제 onPC end-to-end

**When** 라이브 체크리스트가 실제 onPC 2.4.2에서 수행되면, the 대시보드 **shall** 실제 리그를 정확히 표면화하고 발화 경로가 콘솔에서 육안 확인된다.

- 대상: REQ 전반 (LIVE)
- 체크리스트: ① 접속 → 좌측 대시보드에 실제 showfile의 풀들이 실제 `no`로 렌더, ② 시퀀스 타일 `Go+`/`Off` 콘솔 육안 확인, ③ 익스큐터 타일(해석된 번호) `Go+`/`Off` — 의도한 익스큐터가 실행됨을 확인(오발 없음), ④ 수동 새로고침 왕복(콘솔측 변경 반영), ⑤ 양성 매크로 press 1회 → 콘솔에서 매크로 실행 확인 + 블랙리스트 매크로 press → 승인 카드, ⑥ LiveLock 토글 → 제안 전용·송신 0건, ⑦ WS 강제 종료/재접속 → 휘발 상태 소거 후 재동기화, ⑧ 접기/펼치기 중 채팅 지시 정상 동작

### AC-DASHUI-015 (LIVE) — 드릴다운 예산 정직성

**When** 프리셋 풀 드릴다운이 예산을 소진하면, the 대시보드 **shall** 해당 섹션을 `drilldown_capped`로 표기한다(작은 showfile에서 캡 미도달 시 "미발생 — N/A"로 정직 기록).

- 대상: REQ-DASHUI-008 (LIVE)
- 검증: 라이브 관찰 + progress.md §E.2 기록

### AC-DASHUI-016 — 아키텍처 경계

신규 대시 모듈 **shall not** OSC 송신 표면을 import하지 않으며 실행용 REST 엔드포인트를 신설하지 않는다.

- 대상: REQ-DASHUI-019
- 검증: `pytest server/tests/test_architecture.py -q` 그린 + `grep -rn "bridge.osc\|from server.bridge" server/web/panel.py server/web/dash*.py` 0건

## §D. 엣지 케이스

1. 빈 풀(항목 0건) — 섹션은 렌더되되 빈 상태 표기(오류 아님), 발화 타일 0건.
2. 전 섹션 unreachable(콘솔 다운) — 대시보드가 콘솔 미응답 상태를 패널 레벨로 표기, 채팅의 health 배너와 모순되지 않음.
3. 프리셋 풀 존재하나 내용물 미확인 — "풀이 있다"와 "풀 안에 뭔가 저장돼 있다"의 구분 유지(`contents_unavailable` ≠ 빈 풀).
4. 매크로 본문 빈 경우(라인 0개) — 게이트 기존 의미론에 따름(빈 본문 양성 통과 vs 본문 부재 보류의 구분 — EXECBODY design.md 선례).
5. 새로고침 도중 WS 끊김 — 요청 유실은 재접속 재동기화로 회복, 이전 카탈로그의 stale 표기.
6. 접기 상태에서 running 타일 존재 — 접기는 뷰 상태일 뿐 실행 상태에 영향 없음; 펼치면 서버 상태 기준으로 재렌더.
7. 해석 불가 익스큐터(resolve 실패) — 발화 타일 미제공 + 정보 표기(추정 발화 금지, REQ-DASHUI-011).
8. 기형/미지 target의 `panel_execute`(macro 포함) — parse/membership 거부 + error 이벤트, 번들·게이트 호출 0건.

## §E. 품질 게이트

- **Tested**: 신규 서버/UI 모듈 커버리지 프로젝트 기준(85%+) 충족, 순수 함수 우선 설계.
- **Readable/Unified**: 기존 스타일·네이밍 관례(ruff/prettier 툴체인 통과), 터치 파일 신규 위반 0.
- **Secured**: 발화 전량 `gate.screen()` 경유·비게이트 경로 0, 클라이언트 제어 target의 parse-시점 검증 + membership 검증, 정보 타일 구조적 발화 불가, 자격 증명 배제 관례 계승.
- **Trackable**: Conventional Commits + SPEC ID 참조(`feat(SPEC-COPILOT-DASHUI-001): …`).
