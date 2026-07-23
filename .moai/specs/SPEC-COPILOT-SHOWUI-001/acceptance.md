# SPEC-COPILOT-SHOWUI-001 — 수용 기준 (acceptance)

status: draft (v0.2.1, 2026-07-22 — plan-audit iteration 1 fold-in F1/F2/F3/F6 + iteration 2 fix-forward R4 반영). 기계 검증 가능(pytest/vitest) 항목과 LIVE(실제 onPC) 항목을 구분한다.

## §A. 완료 정의 (Definition of Done)

interview Round 2 확정 기준: **라이브 E2E + 테스트 그린.**

1. AC-SHOWUI-001..012 + AC-SHOWUI-015 전부 기계 검증 그린 (pytest 전체 + vitest 전체).
2. AC-SHOWUI-013/014 라이브 체크리스트를 실제 onPC 2.4.2에서 수행·기록 (증적은 progress.md §E.2).
3. `test_architecture.py` 그린 (신규 패널 모듈의 OSC 표면 미접촉).
4. `server/web/PROTOCOL.md` 신규 타입 반영 완료.
5. 신규 런타임 의존성 0 유지.

## §B. Given-When-Then 시나리오

### 시나리오 1 — 자동 나열 타일 실행/정지 (REQ-001/002/006)

- **Given** 콘솔 online, 카탈로그에 Sequence 41이 Executor 191로 나열된 타일이 있다.
- **When** 오퍼레이터가 타일의 `Go+`를 1회 누른다.
- **Then** `gate.screen()`을 통과한 `Go+ Executor 191`이 정확히 1회 송신되고 감사 로그 1건이 남으며, 타일이 RUN(live-amber) 상태가 된다.
- **When** 타일의 `Off`를 누른다. **Then** `Off Executor 191`이 송신되고 타일이 OFF로 복귀한다.

### 시나리오 2 — 채팅 → 핀 → 영속 (REQ-004/005/023)

- **Given** 채팅에서 연출 생성이 완료되어 `_last_created`가 Sequence 71/Executor 201을 가리킨다.
- **When** 사용자가 "패널에 추가"를 누른다.
- **Then** 핀 항목이 생성되어 패널에 append되고, data dir 전용 JSON에 원자적으로 기록된다.
- **When** 서버를 재시작한다. **Then** 핀 항목이 복원된다.
- **When** 사용자가 unpin한다. **Then** 항목이 제거되고 영속 상태에 반영된다.

### 시나리오 3 — LiveLock 강등 (REQ-009)

- **Given** LiveLock이 활성이다.
- **When** `panel_execute`가 도착한다.
- **Then** 콘솔 송신은 0건, 제안(Proposal) 전용 결과가 회신되며, 타일은 비활성/제안 상태로 렌더된다.

### 시나리오 4 — 연결 종료 fail-closed (REQ-015/016)

- **Given** 타일 하나가 RUN 상태다.
- **When** WebSocket이 끊긴다.
- **Then** UI는 패널 running 상태를 즉시 소거한다(휘발 파생 상태).
- **When** 재접속된다. **Then** 카탈로그 + status 재동기화 요청이 발행되어 패널이 재구축된다.

### 시나리오 5 — 버튼 연타 + 정지 우선 (REQ-011/012/013)

- **Given** 패널 실행 1건이 진행 중이다.
- **When** 추가 `panel_execute` N건이 연달아 도착한다.
- **Then** 1건만 실행되고 나머지는 busy 응답을 받는다.
- **When** 진행 중인 실행이 있는 상태에서 `panel_stop`이 도착한다. **Then** 1-in-flight busy 가드에서 면제되어 busy 응답 없이 즉시 처리되며, 진행 중 execute와 동시에 `gate.screen()`을 호출할 수 있다(게이트는 항상 경유 — REQ-012). 채팅 턴 락은 영향받지 않는다.

## §C. 검증 방법 (AC 표)

| AC | 검증 대상 | 방법 / 증거 (제안 커맨드) |
|---|---|---|
| **AC-SHOWUI-001** | REQ-014 — 양측 allowlist 패리티 | pytest: `parse_client_message`가 `panel_execute`/`panel_stop`/`panel_pin`/`panel_unpin`/`panel_catalog_request` 수락 + 미지 타입 거부. vitest: `parseServerEvent`가 신규 이벤트 수락, `v!==1`/미지 타입은 여전히 `null` |
| **AC-SHOWUI-002** | REQ-001/002 — 카탈로그 정확성 | pytest(가짜 state port): 실제 `no` 키잉(비연속 번호 픽스처), `truncated`/`contents` 플래그 전파, `path_not_resolved` vs `console_unreachable` 구분 유지 |
| **AC-SHOWUI-003** | REQ-003 — 인덱스 키잉·fixture 타일 금지 | pytest: fixtures 섹션 입력 시 실행 타일 0건, 배열 인덱스 키잉 회귀 테스트 |
| **AC-SHOWUI-004a** | REQ-004 — 핀 시드 | pytest: `_last_created` 존재 시 정확한 seq/exec로 핀 생성; 부재 시 명시적 오류 회신 |
| **AC-SHOWUI-004b** | REQ-005/023 — 영속·unpin | pytest: temp+`os.replace` 경유 JSON 기록, 재시작 시뮬레이션 후 복원, credential-like 키 거부, unpin 제거가 영속 상태에 반영 |
| **AC-SHOWUI-005** | REQ-006/022 — 게이트 경유 실행 + target 검증 | pytest: `panel_execute` → 송신 1회당 감사 레코드 1건; clearance 없으면 송신 0건(`blocked:` 결과); 번들 = `Go+ Executor N`. **거부 케이스(REQ-022)**: 비정수·음수·누락 target → `parse_client_message` 거부 + error 이벤트 + 번들 미구성; 카탈로그/핀 스토어에 없는 target → membership 거부 + error 이벤트 + `gate.screen()` 미호출 assert |
| **AC-SHOWUI-006** | REQ-007 — 단일 스크리닝 경로 | `test_architecture.py` 그린; `grep -rn "bridge.osc\|from server.bridge" server/web/panel*.py` 0건 |
| **AC-SHOWUI-007** | REQ-008 — 승인 플로우 | pytest(모델: `test_web_approval_bridge.py`): 파괴적 핀 번들 → approval_request 왕복; 거부 시 번들 전체 차단(all-or-nothing) |
| **AC-SHOWUI-008** | REQ-009 — LiveLock | pytest: LiveLock 활성 + `panel_execute` → 제안 생성·송신 0건. vitest: `live_lock` 상태에서 타일 비활성/제안 렌더 |
| **AC-SHOWUI-009** | REQ-011/012/013 — 연타·정지 면제 | pytest: 동시 `panel_execute` N건 → 1건 실행 + N-1 busy; 진행 중 execute 상태의 `panel_stop` → busy 가드 면제로 busy 응답 없이 즉시 처리(동시 `gate.screen()` 허용 assert); 채팅 busy_event 무영향 |
| **AC-SHOWUI-010** | REQ-015/016 — fail-closed 재접속 | vitest: `disconnected` 액션이 패널 running 상태 소거(protocol.ts:308-311 패턴 미러); 재접속 시 카탈로그+status 재요청 dispatch |
| **AC-SHOWUI-011** | REQ-017/018/019/020/024/025/026 — 디자인 준수 | vitest 컴포넌트/순수 테스트: `grep -rn "window.confirm" ui/src/` 0건; **파괴적 발화-클래스**(All Off·블랙아웃급 룩)는 arm→fire 정확히 2회 상호작용 전까지 커맨드 발행 0건(All Off 1회 press 후 발행 0건 assert); **정지 클래스**(타일별 Off)는 정확히 1회 press로 처리; running일 때만 live-amber 토큰 적용; 동사 `Go+`/`Off` 렌더; **All Off 양성 구성 assert(REQ-025)**: 추적 running executor N개일 때 번들 == 각 executor당 정확히 `Off Executor N` 1개(총 N개 커맨드, 중복·누락 0); **음성 assert(REQ-026)**: 번들에 `Thru`/`*`/`Everything` 부재 |
| **AC-SHOWUI-012** | 전체 회귀 | `pytest` 전체 + `npm test`(vitest) 전체 그린 |
| **AC-SHOWUI-013** (LIVE) | 실제 onPC end-to-end | 라이브 체크리스트: ① 자동 나열 시퀀스 타일 → 콘솔에서 실행 육안 확인(`Go+ Executor N`) — **시퀀스 타일 절반은 PASS; 드릴다운 실행기 타일 절반은 v1 의도적 범위 제외(DESCOPED-v1 → SPEC-COPILOT-EXECREF-001)**: v1은 드릴다운 실행기 타일을 카탈로그 소스에서 제거해 구조적으로 표시하지 않음. 사유 — 콘솔 실번호 = `100 + i`(8/8 라이브 실증), i=101 타일이 오류 없이 잘못된 오브젝트를 발화(silent wrong-object 충돌). 실행기 PIN 경로(정확한 번호)는 유지. 증적: `.moai/state/verify/showui-m6-resume/executor-offset.jsonl` + progress.md §M6, ② Off로 해제, ③ 채팅 연출 pin → 발화 → 정지, ④ LiveLock 토글 → 제안 전용·송신 0건, ⑤ 앱 재시작 → 핀 복원, ⑥ WS 강제 종료/재접속 → running 소거 후 재동기화, ⑦ All Off → 추적 중 executor만 개별 Off(콘솔측 비추적 재생은 유지됨을 확인 — 한계 검증) |
| **AC-SHOWUI-014** (LIVE) | REQ-010 — health/포트 드리프트 표면화(라이브 검증) | 라이브: responder degraded/offline 상태에서 패널이 차단 상태 표시(알려진 reply-port drift silent 서명 방어 — research.md Risk 6) |
| **AC-SHOWUI-015** | REQ-010 — 차단 상태 기계 검증 | vitest: `status.health ≠ online` 또는 `executions_blocked` 상태 → 패널 레벨 차단 배너 + 타일 비활성 렌더 assert; pytest: 차단 상태에서의 `panel_execute` → 차단 결과가 명시적으로 회신됨(조용히 삼켜지지 않음) assert |

## §D. 엣지 케이스

1. 카탈로그 실패 섹션 — `path_not_resolved`와 `console_unreachable`이 병합되지 않고 각각 렌더 (AC-002).
2. `truncated`/`contents_unavailable`/`drilldown_capped` — 플래그가 소실되지 않고 UI 힌트로 전달 (AC-002).
3. 비연속 풀 번호 — "N번째 항목 ≠ 오브젝트 N" 픽스처로 회귀 방지 (AC-002/003).
4. 미확인(unconfirmed) 이력 커맨드 — 재승인 요구, 자동 재전송 없음 (게이트 기존 계약, AC-005 경유 확인).
5. 승인 대기 중 LiveLock 활성화 — lock-FIRST 재확인으로 보류 번들 무력화 (기존 REQ-MVP-035 계승).
6. All Off 시 running 항목 0건 — no-op (송신 0건, 오류 아님).
7. `_last_created` 부재 상태에서 pin 요청 — 명시적 오류 표면화, 조용한 무시 금지 (AC-004a).
8. 승인 카드 대기 중 연결 종료 — 기존 fail-safe deny 유지, 패널 상태도 함께 소거 (AC-010).
9. 핀 JSON 손상/부재 — 빈 패널로 기동(fail-open 읽기), 다음 쓰기에서 정상 파일 재생성.
10. 기형·미지 target 페이로드(`panel_execute`/`panel_stop`) — parse/membership 거부 + 명시적 error 이벤트, 번들 구성·`gate.screen()` 호출 0건 (REQ-022, AC-005).

## §E. 품질 게이트

- **Tested**: 신규 서버/UI 모듈 커버리지 프로젝트 기준(85%+) 충족; 순수 함수 우선 설계로 DOM 없는 테스트 유지.
- **Readable/Unified**: 기존 코드 스타일·네이밍 관례 준수(ruff/prettier 등 기존 툴체인 통과).
- **Secured**: 핀 JSON에 자격 증명 배제(credential-like 키 거부 관례 계승), 클라이언트 제어 target의 parse-시점 정수 검증 + 카탈로그/핀 membership 검증(REQ-022 — 검증 실패 시 번들 미구성), 실행 전량 `gate.screen()` 경유, 비게이트 경로 0.
- **Trackable**: Conventional Commits + SPEC ID 참조(`feat(SPEC-COPILOT-SHOWUI-001): …`).
