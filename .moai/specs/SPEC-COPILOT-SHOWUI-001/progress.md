# SPEC-COPILOT-SHOWUI-001 — progress

## Plan-phase log

- 2026-07-22 — Socratic interview 2 rounds (clarity 4/10 → 8/10) → `interview.md`.
- 2026-07-22 — plan-phase 심층 리서치(`research.md`, file:line 근거) + 디자인 방향(`design-direction.md`) 작성.
- 2026-07-22 — plan proposal 제출 → **DP1 human plan-review gate APPROVED**. clarification 3건 해소: ① 페이더 v1 제외(후속 SPEC 이연), ② All Off = bounded enumeration(광역 `Thru` 금지, 한계 명시), ③ 편집 모드 v1 = unpin 전용(append-only).
- 2026-07-22 — Tier L 아티팩트 세트 생성: `spec.md` + `plan.md` + `acceptance.md` + `design.md` (v0.1.0, status: draft) + 본 `progress.md` 스켈레톤. 다음 단계: plan-audit(Tier L PASS 기준) → design phase → Implementation Kickoff Approval → run.
- 2026-07-22 — plan-audit iteration 1: **FAIL 0.81** (Tier L 기준 0.85; must-pass 7/7 PASS, 전부 텍스트 레벨). 필수 교정 6건(F1 정지/All Off 클래스 서로소 분리, F2 REQ-010 AC 커버(AC-015 신설), F3 REQ-022 target 검증 신설, F4 REQ-004/019 분할 + 잔여 singularity debt HISTORY 기록, F5 REQ-014 측별 재서술, F6 stop busy-가드 면제 명시)을 **v0.2.0**으로 fold-in. REQ-021 소각 결번 유지, 신규 REQ-022~026.
- 2026-07-22 — plan-audit iteration 2: **PASS 0.93**. 비차단 fix-forward 4건을 **v0.2.1**로 정리(재감사 불요, 감사자 승인): R1 4개 아티팩트 버전 정렬(plan.md 헤더 드리프트 해소), R3 REQ-012 gate 정정(clearance 세션-키드 리셋 의미론 — 공존 가정 삭제, 실패 방향 안전=과다 차단, stop-preempts-execute 의도), R2 plan.md silent-drop 측별 정렬, R4 AC-011 All Off 양성 구성 assert 추가. 다음 단계: design phase → Implementation Kickoff Approval → run.

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-07-22T00:00:00Z
- plan_status: audit-ready
- plan_audit: iteration 2 PASS 0.93 (Tier L 기준 0.85), fix-forward v0.2.1 반영
- artifacts: spec.md/plan.md/acceptance.md/design.md/research.md (5-file Tier L) + interview.md + design-direction.md + plan-audit.md
- next: Implementation Kickoff Approval (plan→run HUMAN GATE) → design phase (UI-surfaced route, D1-D5) → run

## §E.2 Run-phase Evidence

### M1 — 프로토콜·데이터 모델 계약 (cycle_type=tdd, RED→GREEN→REFACTOR)

기준선(변경 전, HEAD 9836714): pytest **1380 passed**, vitest **82 passed**.
결과(변경 후): pytest **1478 passed** (+98), vitest **98 passed** (+16). 신규 실패 0건.

| AC | 대상 | 상태 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|---|
| AC-SHOWUI-001 (서버 절반) | REQ-014 — client allowlist 패리티 | **PASS** | `.venv/bin/python -m pytest server/tests/test_web_messages.py -q` | `121 passed in 0.06s` (신규 5종 전부 파싱, `panel_execute_all` 오타는 여전히 `ProtocolError`) |
| AC-SHOWUI-001 (클라이언트 절반) | REQ-014 — server event allowlist 패리티 + null-drop 보존 | **PASS** | `cd ui && npx vitest run` | `Tests 98 passed (98)` (신규 3종 파싱, `v:2`·미지 타입은 여전히 `null`) |
| AC-SHOWUI-005 (parse-time 절반) | REQ-022 — target 정수 검증 | **PASS** | `pytest server/tests/test_web_messages.py -q` | 8종 기형 target × 3 메시지 타입 = 24 케이스 전부 `ProtocolError`; 번들 미구성·`gate.screen()` 미도달 (호출자 자체가 아직 없음) |
| AC-SHOWUI-005 (membership 절반) | REQ-022 — 카탈로그/핀 스토어 존재 검증 | **DEFERRED-M2** | — | 패널 스토어(`server/web/panel.py`)가 M2에 신설되므로 M1에서 구현 불가. 스텁·가짜 구현 금지 원칙에 따라 미착수 |
| AC-SHOWUI-006 | REQ-007 — 단일 스크리닝 경로 | **PASS** | `pytest server/tests/test_architecture.py -q` + `grep -rn "bridge.osc\|from server.bridge" server/web/messages.py` | `4 passed`; grep 0건 (exit 1) |
| AC-SHOWUI-012 (부분) | 전체 회귀 | **PASS** | 위 pytest/vitest 전량 | 1478 + 98, 신규 실패 0 |

부가 검증: `PROTOCOL_VERSION` 양측 모두 `1` 유지(bump 없음) · `npx tsc --noEmit` exit 0 ·
`ruff check` clean · `server/web/messages.py` 커버리지 **100%** (전체 스위트 기준) ·
`grep -rn "window.confirm" ui/src/` 0건.

증적 로그: `.moai/state/verify/showui-m1/` (00 기준선 ~ 07).

### M1에서 동결한 계약 (M2~M6이 그 위에 쌓임)

- **PanelItem**: `id`(=`"<target_kind>:<no>"`, 배열 인덱스 금지) · `kind`(look/effect/sequence) ·
  `target_kind`(executor/sequence — **fixtures 불허**, REQ-003) · `target`(정수 ≥1) ·
  `name` · `appearance`(`#rrggbb`|null) · `source`(pin/auto). 순서 = 그리드 순서(append-only, 정렬 금지).
- **PanelSection**: `name` · `status`(ok/path_not_resolved/console_unreachable — 두 실패 사유 병합 금지) ·
  `truncated` · `drilldown_capped` · `contents_unavailable`.
- **client→server**: `panel_execute`/`panel_stop`/`panel_unpin`(`target_kind`+`target` 검증) ·
  `panel_pin`/`panel_catalog_request`(무페이로드).
- **server→client**: `panel_catalog` · `panel_item_state`(`cue`는 문자열, MA3 큐 번호는 정수가 아님) · `panel_busy`(거부한 타일 명시).
- **UiState.panel**: `items`/`sections`/`running`/`busy` + `clearOnDisconnect`(running·busy 소거, 타일 목록은 보존).

### M1 미결 항목 (다음 마일스톤 의무)

1. **M3 필수** — `server/web/app.py`의 `/ws` 디스패치는 `else: # status_request` 폴백으로 끝난다
   (app.py:279). 신규 panel 타입은 파싱은 되지만 라우팅이 없어 현재 **status 스냅샷으로 응답**된다.
   무해(실행·게이트 호출 0건)하나 M3에서 반드시 분기를 추가해야 한다.
2. **M5 필수** — `useCopilotSocket.ts`의 disconnect 핸들러를 `clearPendingRequests` →
   `clearOnDisconnect`로 교체해야 REQ-015 fail-closed가 실제로 발효된다. 순수 함수는 M1에서 완비·검증됨.

### M2 — 서버 패널 스토어 + 카탈로그 + 핀 시드 (cycle_type=tdd, RED→GREEN→REFACTOR)

기준선(변경 전, HEAD 88a0b34): pytest **1478 passed**, vitest **98 passed**, ruff `server/` **3 errors(E501, 기존)**.
결과(변경 후): pytest **1543 passed** (+65), vitest **98 passed** (변동 없음), ruff **3 errors(동일 3건, 신규 0)**. 신규 실패 0건.

| AC | 대상 | 상태 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|---|
| AC-SHOWUI-002 | REQ-001/002 — 카탈로그 정확성 | **PASS** | `.venv/bin/python -m pytest server/tests/test_web_panel.py -q` | `65 passed`. 비연속 픽스처(seq 2/7/41)로 실제 `no` 키잉 검증, `truncated`/`drilldown_capped`/`contents_unavailable` 3종 전파, `path_not_resolved`(형제 응답 있음) vs `console_unreachable`(무응답) 구분 유지 |
| AC-SHOWUI-003 | REQ-003 — 인덱스 키잉·fixture 타일 금지 | **PASS** | 동일 | `sequence:3` 부재·`sequence:41` 존재로 인덱스 키잉 회귀 차단. fixtures는 `PANEL_CATALOG_SECTIONS`에 **구조적으로 부재** — 픽스처 경로가 채워진 트리에서도 조회 0건·타일 0건 |
| AC-SHOWUI-004a | REQ-004 — 핀 시드 | **PASS** | 동일 | 시드에 executor 있으면 `executor:201`(주소) + 이름은 `Sequence 71`(정체성), executor 없으면 `sequence:71`. 시드 부재/`sequence=None` → `PinSeedUnavailable` 발생(조용한 무시 아님), 한국어 메시지 상수 제공 |
| AC-SHOWUI-004b | REQ-005/023 — 영속·unpin | **PASS** | 동일 | 동일 디렉터리 temp + `os.replace` 스파이로 원자적 스왑 확인·잔여 temp 0건; 재시작 시뮬레이션 복원; 손상/부재/기형 4종 전부 fail-open 빈 패널 후 다음 쓰기로 정상 재생성; credential-like 키 4종 쓰기 거부 + 파일 내 존재 시 미로드; unpin이 영속 상태에 반영(재시작 후에도) |
| AC-SHOWUI-005 (membership 절반) | REQ-022 — 카탈로그/핀 membership | **구현·테스트 완료, 배선 DEFERRED-M3** | 동일 | `PanelStore.contains()` 구현 + 테스트(카탈로그/핀 양쪽 조회, `sequence:41`≠`executor:41` 클래스 구분, 미지 target 거부, unpin 후 비회원화). **`app.py` 실행 경로 배선은 M3** — M2는 `app.py` 무접촉 |
| AC-SHOWUI-006 | REQ-007 — 단일 스크리닝 경로 | **PASS** | `pytest server/tests/test_architecture.py -q` + `grep -rn "bridge.osc\|from server.bridge" server/web/panel.py` | `4 passed`; grep 0건(exit 1). panel.py에 실행 표면 없음(`execute`/`screen` 속성 부재 assert) |
| AC-SHOWUI-012 (부분) | 전체 회귀 | **PASS** | `pytest server/tests/ -q` + `(cd ui && npx vitest run)` | `1543 passed` + `98 passed`, 신규 실패 0 |

엣지 케이스 (acceptance.md §D): 1(두 실패 사유 미병합) · 2(3종 플래그 전파) · 3(비연속 풀 번호) · 7(시드 부재 명시적 오류) · 9(핀 JSON 손상→빈 패널 기동, 다음 쓰기 재생성) 전부 커버.

부가 검증: `server/web/panel.py` 커버리지 **100%**(191 stmts, 0 miss — 전체 스위트 기준) ·
`ruff check server/` 신규 0건(기존 3건 E501: console.py:289/343, test_web_provision_api.py:102 — 본 마일스톤 무관) ·
`npx tsc --noEmit` exit 0 · `grep -rn "localStorage" ui/src/` 0건 · `PROTOCOL_VERSION` 양측 `1` 유지(M2는 와이어 형상 무변경).

**비공허성(non-vacuity) 검증**: 신규 스위트가 실제로 판별하는지 확인하기 위해 구현에 9종 변이(mutation)를 주입 — 인덱스 키잉 회귀, 두 실패 사유 병합, 비원자적 쓰기, credential 검사 생략, 시드 부재 조용한 반환, membership의 클래스 무시, fixtures 카탈로그 편입, 3종 플래그 드롭, 손상 파일 예외 전파 — **9/9 전부 KILLED**(생존 0). 첫 실행 전량 통과가 공허한 통과가 아님을 기계적으로 확인.

증적 로그: `.moai/state/verify/showui-m2/` (00 기준선 · 01 pytest · 02 vitest · 03 ruff · 03a ruff 기준선 · 04 커버리지 · 05 architecture · 06 boundary).

### M2에서 동결한 계약 (M3~M6이 그 위에 쌓임)

- **핀 파일**: `<user_data_dir>/panel_pins.json`, `{"version": 1, "pins": [{kind,target_kind,target,name,appearance}]}`.
  `id`/`source`는 파생값이라 미저장(저장된 `id`는 자신이 가리키는 쌍과 드리프트할 수 있음). 읽기 fail-open·부분 신뢰 금지(레코드 1건 불량 → 파일 전체 불신).
- **카탈로그 소스**: `PANEL_CATALOG_SECTIONS` — `sequences`(DataPool/Sequences, target_kind=sequence) + `pages`(DataPool/Pages, drill-down, target_kind=executor). fixtures 부재는 **구조적**이며 필터가 아니다.
- **그리드 순서**: 핀 먼저, 그다음 자동 나열. 자동 절반은 새로고침마다 통째로 교체되므로, 자동이 앞이면 쇼파일에 시퀀스 1건만 추가돼도 핀 타일 전체가 손가락 아래에서 밀린다.
- **타일 배지**: 카탈로그 타일은 전부 `kind="sequence"`(SEQ). rig 스냅샷에 정적 룩/페이저 구분 정보가 없어 LOOK/FX 추측은 하지 않는다.
- **`tools.py` 헬퍼 공개화**: `rig_object`/`rig_section`/`drill_into`/`REASON_UNRESOLVED`/`REASON_UNREACHABLE` — 순수 함수 이름 변경만(동작 무변경). 기존 도구 테스트 `test_tools.py`(72) + `test_lua_responder.py`(15) 전부 그린 유지.
- **세션 시드 seam**: `ChatSession.last_created` 읽기 전용 property. 패널은 "채팅이 방금 만든 것"에 대한 제2의 진실원을 갖지 않으며 이 값을 쓰지도 못한다.

### M2 미결 항목 (다음 마일스톤 의무)

1. **M3 필수** — `PanelStore.contains()`를 `panel_execute`/`panel_stop`/`panel_unpin` 경로에 배선(REQ-022 membership 절반). 현재 구현·테스트만 완료, 호출자 0건.
2. **M3 필수** — `PanelStore`/`PinStore` 인스턴스를 `WebDeps`/`app.py` 라이프사이클에 조립. M2는 `app.py` 무접촉이므로 현재 프로덕션 경로에서 패널 스토어는 생성되지 않는다.
3. **M3 필수** — `PIN_SEED_UNAVAILABLE_MESSAGE`를 error 이벤트로 회신하는 배선(현재는 예외만 발생).
4. **M1 이월(M3 필수)** — `/ws` 디스패치의 `else: # status_request` 폴백(app.py:279)에 panel 분기 추가.
5. **M1 이월(M5 필수)** — `useCopilotSocket.ts` disconnect 핸들러를 `clearOnDisconnect`로 교체.

### M2→M3 사이 라이브 확인 — ASSUMPTION-7 (페이지 자식 = 실행기 번호)

M2 보고의 최상위 잔여 리스크(페이지 드릴다운의 자식 `i`가 실행기 번호인지 페이지 내 위치인지 미검증)를
**실제 onPC 2.4.2에서 읽기 전용으로 확인**했다. 발사 0건 — 응답기의 `state` 조회 동사만 사용.

- 프로브: `.moai/state/verify/probe_executor_numbers.py` · 로그: `.moai/state/verify/probe-executor-numbers.log`
- 유효 설정(하드코딩 아님, settings.toml에서 read): `console_port=8000`, `receive_port=9005`
- 결과: `DataPool/Pages` → Page 1 (`i=1`) → 자식 8개, `i` = **1, 5, 11, 91, 92, 93, 95, 101**

**판정: 가정 성립.** 실행기가 8개인데 번호가 1..8이 아니라 비연속(2~4·6~10·12~90·94·96~100 결번)이므로
위치 번호 가설은 **반증**되었다. 값의 모양(91/92/93/95/101)도 MA3 실행기 번호 체계와 일치한다.

**남은 미검증**: 이 번호가 `Go+ Executor N`이 실제로 발사하는 대상과 동일하다는 최종 확인은
**AC-SHOWUI-013 ① (M6 라이브)** 의 몫이다 — 위 결과는 위험 가설을 제거했을 뿐 발사 대상 동치를
독립 증명하지 않는다. 이 구분을 M6까지 유지할 것.

### M3 — 게이트 경유 실행 핸들러 (cycle_type=tdd, RED→GREEN→REFACTOR)

기준선(변경 전, HEAD 5395a10, **실측**): pytest **1542 passed + 1 failed**, vitest **98 passed**,
ruff `server/` **3 errors(E501, 기존)**, `test_architecture.py` **4 passed**.
결과(변경 후): pytest **1591 passed + 1 failed**(+49), vitest **98 passed**(변동 없음),
ruff **3 errors(동일 3건, 신규 0)**, architecture **4 passed**.

> **기준선 정정**: 위임 프롬프트의 "1543 passed"와 달리 HEAD 5395a10에서 실측한 기준선은
> **1542 passed + 1 failed**이다. 실패 1건 `test_web_reply_discovery.py::TestDiscovery::
> test_every_candidate_socket_is_released`는 **환경 원인**으로, 코드 무변경 상태에서 단독
> 재현된다: 실행 중인 grandMA3 onPC(`app_gma3`, PID 86875)가 UDP **9005**를 점유하고 있고
> 그 포트가 이 테스트의 후보 집합에 들어 있다(`lsof -nP -iUDP | grep :90` 로 확인). M3와 무관하며
> M3가 만든 실패가 아니다. 신규 실패 0건.

| AC | 대상 | 상태 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|---|
| AC-SHOWUI-005 (게이트 경유) | REQ-006 — 송신 1회당 감사 1건, clearance 없으면 송신 0건, 번들 = `Go+ Executor N` | **PASS** | `.venv/bin/python -m pytest server/tests/test_web_panel_execute.py -q` | `56 passed`. 1 press → `screened == [["Go+ Executor 191"]]` · `sent == ["Go+ Executor 191"]` · `audit_sends(...) == 1`; 승인 거부 시 `sent == []` |
| AC-SHOWUI-005 (parse 거부) | REQ-022 — 기형 target | **PASS** | 동일 | 6종 기형(`0`/`-3`/`"191"`/`1.5`/`None`/`True`) 전부 `error(kind=protocol)`, `screened == []` |
| AC-SHOWUI-005 (membership) | REQ-022 — 미지 target, **`gate.screen()` 미호출 assert** | **PASS** (M1/M2의 DEFERRED 해소) | 동일 | 미지 `executor:9999` → `error(kind=panel)` + **`harness.screened == []`**; 클래스 구분(`sequence:41` 존재 ≠ `executor:41`)도 거부; 런타임 직접 호출도 `screened=False`·`command=""` |
| AC-SHOWUI-006 | REQ-007 — 단일 스크리닝 경로 | **PASS** | `pytest server/tests/test_architecture.py -q` + 경계 grep | `4 passed`; `grep "bridge.osc\|from server.bridge\|pythonosc" server/web/panel.py server/web/app.py` **0건(exit 1)**; 실행 코드의 `gate.screen(` 호출 **정확히 1곳**(panel.py:649), `execution_port` 호출 **정확히 1곳**(panel.py:657) |
| AC-SHOWUI-007 | REQ-008 — 승인 왕복 + all-or-nothing | **PASS** | 동일 + `pytest server/tests/test_web_e2e.py -q` | 실 UDP 왕복에서 `Go+ Executor 201` 승인 카드 → 승인 시 `["SaveShow","Go+ Executor 201"]` 송신, 거부 시 `[]`; 연결 종료 시 대기 승인 fail-safe deny(`pending_ids == ()`) |
| AC-SHOWUI-008 | REQ-009 — LiveLock | **PASS** (pytest 절반; vitest 절반은 M4) | 동일 | 잠금 중 execute/stop 모두 `proposal` 이벤트 + `sent == []` |
| AC-SHOWUI-009 | REQ-011/012/013 — 연타·정지 면제·턴 락 독립 | **PASS** | 동일 | 진행 중 execute + 3연타 → 1건 실행 + `panel_busy` 3건(거부 타일 id 명시), busy 거부는 번들 미구성; 진행 중 execute 상태의 `panel_stop` → busy 없이 즉시 처리 + 동시 `gate.screen()` 발생 확인; 채팅 턴 진행 중 패널 실행 OK(`busy` 없음), 패널 실행 중 채팅 OK; **채팅 번들 clearance 무효화 없음**(세션 키 분리) |
| AC-SHOWUI-015 (pytest 절반) | REQ-010 — 차단 상태 명시 회신 | **PASS** | 동일 | `console_offline`에서 `panel_execute` → `error(kind=panel)` + `panel_item_state(running=false)` + `sent == []`. 조용한 삼킴 0 |
| AC-SHOWUI-011 (REQ-025/026 서버 절반) | All Off bounded 구성·광역 금지 | **PASS**(서버) / **DEFERRED-M4**(UI arm→fire·라벨) | 동일 | 추적 running N=3 → 정확히 N개 `Off Executor N`(중복 0·누락 0); 정지 lane 직렬화로 동시 송신 최대 **1**; 광역 타깃은 **구성 불가**(빌더가 닫힌 동사쌍 + 양의 정수만 허용, `Thru`/`*`/`Everything` 문자열 리터럴 0건) |
| AC-SHOWUI-012 (부분) | 전체 회귀 | **PASS** | `pytest server/tests/ -q` + `(cd ui && npx vitest run)` | `1591 passed, 1 failed(환경 기존)` + `98 passed` |
| AC-SHOWUI-013/014 (LIVE) | 실기 onPC | **DEFERRED-M6** | — | 라이브 체크리스트는 M6 소관 |

엣지 케이스 (acceptance.md §D): 4(미확인 이력·자동 재전송 없음 — `unconfirmed` 결과가 성공으로
렌더되지 않음) · 6(추적 running 0건 → 송신 0·오류 아님) · 8(승인 대기 중 연결 종료 → fail-safe
deny + 패널 상태 소멸) · 10(기형·미지 target → error + 번들·screen 0건) 전부 커버.

부가 검증: `server/web/panel.py` 커버리지 **100%**(292 stmts, 0 miss) ·
`server/web/app.py` **99%**(208 stmts, 1 miss — `_backup_loop` 조기 반환, M3 무관 기존 라인) ·
`ruff check server/` 신규 0건 · `PROTOCOL_VERSION` 양측 `1` 유지(M3는 **신규 와이어 타입 0** —
M1이 동결한 5종만 배선).

**비공허성(non-vacuity) 검증**: 12종 변이 주입 → **12/12 KILLED**(생존 0).
1차 11종 중 4종이 생존했고(정지 lane 직렬화 / 세션 키 분리 / 실패 송신의 running 오보 /
unpin membership), 이는 테스트 부족이지 구현 부족이 아니었으므로 **테스트 5종을 추가**해
2차에서 전부 KILL했다. 상세: `.moai/state/verify/showui-m3/05-mutation.log`.

증적 로그: `.moai/state/verify/showui-m3/` (00 기준선 · 01 pytest · 02 vitest · 03 ruff ·
04 커버리지 · 05 mutation · 06 boundary).

### M3에서 동결한 계약 (M4~M6이 그 위에 쌓임)

- **단일 진입**: 패널의 콘솔 도달 경로는 `PanelRuntime.fire()` **하나뿐**이다. 그 안에서
  membership → `playback_command()` → `gate.screen()` → `gate.execution_port` 순서가 한 함수에
  붙어 있고, `screen`과 `execute` 사이에는 **한 문장도 없다**(clearance 리셋 창을 0에 가깝게 유지).
  execute와 stop은 같은 메서드를 verb만 바꿔 호출한다 — 제2 경로가 없다.
- **세션 키 분리**: 패널은 연결마다 **자기 세션 키**를 갖는다(채팅 세션 키와 다름). 게이트의
  clearance가 세션-키드이므로 공유하면 채팅 번들 중간에 타일을 누른 순간 남은 명령이 좌초한다.
  분리는 REQ-013의 실체이며, `test_a_panel_screen_does_not_invalidate_a_chat_bundles_clearance`가
  이를 기계 검증한다(변이 M9로 비공허성 확인).
- **2개 lane**: execute lane은 1-in-flight이며 **거부**(`panel_busy`), stop lane은 절대 거부하지
  않되 **stop끼리는 직렬화**한다. 같은 세션 키 안에서 `screen()`이 매번 clearance를 리셋하므로,
  동시 stop 2건은 서로의 clearance를 무효화해 All Off가 N개 중 1개만 끄는 결과를 낳는다.
  직렬화는 그 구조적 방지책이다(변이 M5로 비공허성 확인).
- **터미널 타일 이벤트 1건**: 모든 `panel_execute`/`panel_stop`은 `panel_item_state` 또는
  `panel_busy` 중 정확히 하나를 낳는다(미지 target은 tile이 없으므로 `error`만). 비송신 시에는
  한국어 `error(kind="panel")`가 동반된다 — 차단의 조용한 삼킴 금지(REQ-010).
  `running`은 **패널이 관측한 것**만 담으며 콘솔 진실의 주장이 아니다.
- **All Off = 클라이언트 조립**: 서버에 All Off 전용 메시지 타입은 **없다**. UI가 추적 중 running
  타일마다 `panel_stop`을 1건씩 보내며, 서버는 그 N건을 stop lane에서 순차 처리한다. 광역 타깃은
  빌더가 닫힌 동사쌍 + 양의 정수만 받으므로 **구성 자체가 불가능**하다(REQ-026).
- **`WebDeps.panel`**: 프로세스 상태(핀 파일 + 마지막 rig 열거)이므로 앱당 1개를 모든 연결이 공유
  한다. `None`이면 첫 패널 메시지에서 기본값을 지연 생성 — 패키지 실행은 serve.py 수정 없이 패널을
  얻고, 타일을 누르지 않는 테스트는 사용자 핀 파일을 건드리지 않는다.

### M3 미결 항목 (다음 마일스톤 의무)

1. **M4 필수** — All Off의 bounded enumeration **조립**(추적 running 타일 → N개 `panel_stop`) +
   arm→fire 2-step + "ALL OFF (패널)" 한계 라벨. AC-SHOWUI-011의 vitest 절반.
2. **M4 필수** — `panel_busy` / `error(kind="panel")` / `proposal` 소비와 타일 잠금 해제 렌더.
3. **M5 이월** — `useCopilotSocket.ts` disconnect 핸들러를 `clearOnDisconnect`로 교체(M1 이월).
4. **M6** — `PROTOCOL.md` 최종화(M3가 §"Panel command outcomes"를 선반영했으므로 잔여는 M4~M5 결과 반영).

### M3에서 발견한 사항 — 사람 결정 필요 (승인 게이트 빈도)

`Go+ Executor N` / `Off Executor N`은 **현재 룰셋에서 매 누름마다 승인 카드를 띄운다.** 이는 M3가
만든 동작이 아니라 기존 게이트 의미론이며, M3는 그것을 그대로 소비했다. 근거 체인(전부 코드 실측):

1. `Go+`/`Off`는 `blacklist.yaml`의 `invoking_verbs`에 있다 → `classify.py:222` → `category="invoking"`.
2. 참조 추출은 `RECOGNIZED_REFERENCE_TYPES = ("Macro","Plugin","Sequence")`만 인식한다
   (`classify.py:33`, `_extract_reference` 117-125). **"Executor"는 없다** → `reference=None`.
3. `expand.py:82-83` — `reference is None` → `_hold("unverifiable reference: no recognizable
   target object")` → `gate.screen()`이 승인 보류.
4. 결과적으로 승인 후 `_backup.before_risky_execution()`도 돈다 → 매 누름마다 `SaveShow` 1회
   (e2e에서 `["SaveShow", "Go+ Executor 201"]`로 실측됨).

즉 **타일 1회 누름 = 승인 카드 1장 + 쇼파일 저장 1회**다. `target_kind="sequence"` 타일
(`Go+ Sequence 41`)은 참조가 해석되므로 본문 조회가 성공하고 깨끗하면 승인 없이 통과한다 —
같은 패널 안에서 두 클래스의 마찰이 다르다.

이는 design.md §5의 "일반 타일은 single-press"와 spec.md §A의 "쇼 진행 중 블랙아웃 순간에 승인
카드가 뜨는 사고를 원천 배제" 취지와 **정면으로 충돌한다.** M3는 이를 임의 해석하지 않고 계약대로
구현했고(`server/safety/**` 무변경 — B-7), 테스트는 승인/거부 양쪽 경로를 모두 덮으므로 어느 쪽으로
결정되든 구현은 유효하다. 선택지는 §E.2 M3 보고의 E7 항목 참조.

### M3→M4 사이 사람 결정 (2건 확정, 2026-07-22)

오케스트레이터가 인과 사슬을 소스에서 독립 확인한 뒤 사용자에게 제시하고 결정을 받았다.
확인 경로: `blacklist.yaml:22-25`(Go/Go+/Go- = invoking_verbs) → `classify.py:33`
(`RECOGNIZED_REFERENCE_TYPES = ("Macro","Plugin","Sequence")` — Executor 부재) →
`expand.py:83`(참조 미인식 → `_hold`) → `gate.py:59`(`BACKUP_COMMAND = "SaveShow"`).

**결정 ① — 승인 마찰: 게이트에 Executor 인식을 추가한다 (별도 SPEC).**
`classify.py`의 인식 참조 타입에 `Executor`를 추가하고 실행기 본문(배정된 시퀀스) 조회 경로를
만들어, 실행기 타일도 승인 없이 single-press로 발사되게 한다. `server/safety/**` 변경이므로
**본 SPEC 범위 밖 — 후속 SPEC으로 분리**한다. 방향이 확정되었으므로 M4는 design.md §5를
액면 그대로(일반 타일 = single-press) 구현해도 좋다. M4가 승인 상태를 렌더해야 하는 의무는
REQ-SHOWUI-008 때문에 어차피 유지된다(진짜 파괴적 번들은 여전히 승인을 거친다).
반려된 대안: (a) 승인-매-누름 수용 + design.md 수정 — 패널의 핵심 가치 상실,
(b) 시퀀스 참조로 대체 발사 — 동치성 미검증 + 실행기 재명명에 취약.

**결정 ② — All Off 구성: 클라이언트 N회 `panel_stop` 전송을 유지한다.**
M1이 동결한 와이어 계약을 변경하지 않으며, AC-SHOWUI-011의 번들 구성 assert가 vitest에
있는 배치와도 일치한다. 서버는 stop 레인 직렬화로 N회 순차 정지의 무간섭을 이미 보장한다(M3).
반려된 대안: `panel_all_off` 서버 타입 신설 — 왕복 1회로 줄지만 M1 계약 변경 + 양측 테스트 재작성.

### M4 — 연출 패널 UI (cycle_type=tdd, RED→GREEN→REFACTOR)

기준선(변경 전, HEAD 0576553, **실측**): vitest **98 passed**, `tsc --noEmit` **exit 0**,
pytest **1591 passed + 1 failed**(환경 기존 — M3 기록 참조).
결과(변경 후): vitest **168 passed**(+70), `tsc --noEmit` **exit 0**,
`npm run build` **exit 0**, pytest **1591 passed + 1 failed**(**변동 없음** — M4는 서버 무변경).

> **인계 상태 고지**: M4 착수 시 작업 트리에 선행 세션(중단됨)이 남긴 미커밋 산출물이
> 이미 존재했다(`ShowPanel.tsx`/`PanelTile.tsx`/테스트 3종 untracked + 4파일 수정).
> 그 산출물의 RED 단계는 **관측 불가**하므로 신뢰하지 않고, (a) design.md 전 조항 대조 검토,
> (b) 변이 주입 6종으로 비공허성 실측, (c) 신규 결함 2건은 RED→GREEN으로 직접 수정하는
> 경로를 취했다. 아래 증거는 전부 이번 세션에서 실행한 커맨드의 출력이다.

| AC | 대상 | 상태 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|---|
| AC-SHOWUI-011 ① 모달 금지 | REQ-019 | **PASS** | `grep -rn "window.confirm\|window.alert" ui/src/ \| wc -l` | `0` |
| AC-SHOWUI-011 ② 파괴적 발화 1회 press → 발행 0건 | REQ-024 | **PASS** | `npx vitest run src/components/ShowPanel.test.tsx` | `allOffPress(ARM_IDLE, …).frames == []` (running 3건 보유 상태에서도). 3연속 press 발행량 `[0, 3, 0]` |
| AC-SHOWUI-011 ③ 정지 클래스 1회 press 처리 | REQ-012 | **PASS** | `npx vitest run src/components/PanelTile.test.tsx` | `tilePressFrame(item,"off")` = 프레임 정확히 1개; `pending`/`busy` 상태에서도 `offDisabled == false` |
| AC-SHOWUI-011 ④ live-amber는 running 전용 | REQ-018 | **PASS** (결함 1건 수정 후) | `npx vitest run src/styles.test.ts` | 스타일시트 파싱 후 `--live` 사용 블록 = `{:root, .panel-tile.is-running, .panel-state-badge.is-run, .panel-tile-cue, .panel-rail-live, .panel-rail-sweep}` 뿐. 위반 목록 `[]` |
| AC-SHOWUI-011 ⑤ `Go+`/`Off` 동사 렌더 | REQ-020 | **PASS** | `npx vitest run src/components/PanelTile.test.tsx` | `VERB_GO == "Go+"`, `VERB_OFF == "Off"`, 미디어 글리프 `[▶⏸⏹■]` 매치 0 |
| AC-SHOWUI-011 ⑥ All Off 양성 구성 | REQ-025 | **PASS** | 동일 | running N=3 → 프레임 정확히 3개, 각 타일당 1개(`target` = `[1, 91, 41]`), 중복 0·누락 0. 핀+리그 중복 등재 타일은 1회만 |
| AC-SHOWUI-011 ⑦ 광역 타깃 부재 | REQ-026 | **PASS** | 동일 | 번들 문자열에 `Thru`/`thru`/`*`/`Everything`/`everything` 0건. 프레임 키집합은 `{target, target_kind, type, v}` 고정 |
| AC-SHOWUI-008 (vitest 절반) | REQ-009 — LiveLock | **PASS** (M3의 pytest 절반과 합쳐 완결) | `npx vitest run src/components/ShowPanel.test.tsx` | `panelGate({live_lock:true}, true).mode == "proposal"`; 타일은 `goDisabled==true`·`offDisabled==true`·`tileClass` 에 `is-proposal` |
| AC-SHOWUI-015 (vitest 절반) | REQ-010 — 차단 상태 | **PASS** (M3의 pytest 절반과 합쳐 완결) | 동일 | `health != "online"` → `mode=="blocked"`, `executions_blocked` → `mode=="blocked"`; 두 경우 모두 패널 배너 + 타일 양쪽 동사 비활성. `status==null`·소켓 단절도 fail-closed 차단 |
| 섹션 실패 구분 | REQ-002 | **PASS** | 동일 | `path_not_resolved` ≠ `console_unreachable` (문구 비동일 assert), `truncated`/`drilldown_capped`/`contents_unavailable` 3종 개별 표면화 |
| AC-SHOWUI-013/014 (LIVE) | 실기 onPC | **DEFERRED-M6** | — | 라이브 체크리스트는 M6 소관 |

**M4에서 발견·수정한 결함 2건** (선행 세션 산출물의 design.md 위반):

1. **live-amber 누출** — `.panel-rail-arming`(All Off arm 진행 레일)이 `var(--live)`로 칠해져
   있었고, `:root` 주석이 "running **또는 발화 컨트롤의 arm 진행**"으로 확장되어 위반을
   정당화하고 있었다. design.md §3은 live-amber를 "유일한 RUNNING 색, 장식 사용 절대 금지"로
   못박는다 — 모든 것을 정지시키려는 컨트롤에 "무언가 돌고 있다" 신호를 칠하는 셈이었다.
   arm 레일을 Stop red(`--bad`)로 교정하고 주석을 무조건부 배타 선언으로 되돌렸다.
2. **상태 배지 가독성** — `.panel-state-badge`(RUN/OFF)가 12px였다. REQ-SHOWUI-018은
   "상태는 색상 단독 전달 금지(RUN/OFF 배지 병행, **최소 15px**)"를 한 문장에 묶는다.
   색의 짝인 텍스트가 색보다 안 읽히면 이중화가 명목뿐이므로 15px로 올렸다.

두 결함 모두 **RED→GREEN**으로 처리했다: 먼저 `ui/src/styles.test.ts`(신규)를 작성해
실패를 관측하고(`[.panel-rail-arming]` 위반 목록 · `expected 12 to be >= 15`) 그 다음 수정했다.
이 가드는 클래스명이 아니라 **스타일시트 텍스트 자체**를 `node:fs`로 읽어 검사하므로
(신규 의존성 0), 앞으로 live-amber가 running 아닌 곳에 칠해지면 빌드가 깨진다.

**구조 개선(REFACTOR)**: `allOffPress(arm, now, items, running) → {next, frames}` 를 신설했다.
AC-SHOWUI-011이 요구하는 명제는 "1회 press = 발행 0건"이라는 **arm 게이트와 번들 구성의 합성**인데,
기존에는 `pressArm`과 `allOffFrames`로 분리되어 있어 정확히 그 이음매(오배선 시 블랙아웃이
한 번의 누름 앞에 놓이는 지점)만 무검증으로 남아 있었다. 합성 함수로 끌어올려 AC 명제를
문자 그대로 assert하고, `AllOffControl`의 핸들러는 그 결과를 내보내기만 하는 투영으로 축소했다.

**비공허성(non-vacuity) 검증**: 변이 주입 6종 → **6/6 KILLED**(생존 0).
arm 항상 발화(7 failed) · All Off 중복제거 제거(1) · running 플래그 무시(5) ·
정지 타일이 live-amber 착용(2) · Off를 pending에 종속(1) · live-amber를 차단 배너로 누출(2).
상세: `.moai/state/verify/showui-m4/7-mutation.log`.

**커버리지 — 열거 기반(측정 아님)**: `@vitest/coverage-v8` 미설치이며 설치는 신규 의존성
추가(제약 위반)이므로 **백분율을 보고하지 않는다.** 대신 export별로 그것을 실행하는 `it` 블록
수를 실측했다(M4 신규 테스트 70건 = PanelTile 18 + ShowPanel 33 + ChatView 8 + styles 11):
`tileView` **13** · `tilePressFrame` **2** · `allOffPress` **7** · `allOffFrames` **6** ·
`allOffTargets` **2** · `pressArm`/`isArmed` **5** · `panelGate` **8** · `sectionHints` **4** ·
`pinnableIndex` **8** · 스타일시트 계약 **11**.
상수(`VERB_GO`/`VERB_OFF`/`BADGE_RUN`/`BADGE_OFF`/`TYPE_BADGES`/`ALL_OFF_LABEL`/
`ALL_OFF_SUBLABEL`/`ARM_TIMEOUT_MS`)는 값 자체가 계약이므로 직접 assert된다.
분기 관점: `tileView`는 running × kind(look/그 외) × gate(ready/proposal/blocked) × pending ×
busy 조합을 덮고, `panelGate`는 5개 분기 전부 + 우선순위 역전(잠금 ∧ 오프라인)을 덮는다.
**미검증 잔여**: JSX 렌더 자체와 `useEffect` 타이머(press 래치 해제 `PRESS_LATCH_TIMEOUT_MS`,
시각적 disarm)는 DOM 하니스가 없어 실행되지 않는다 — 아래 잔여 위험 참조.

증적 로그: `.moai/state/verify/showui-m4/` (1 vitest 기준선 · 2 tsc · 3 RED styles ·
4 GREEN styles · 5 RED allOffPress · 6 GREEN 전체 · 7 mutation · 8 pytest · 9 build).

### M4에서 동결한 계약 (M5~M6이 그 위에 쌓임)

- **live-amber 배타성은 이제 기계 검증된다**: `ui/src/styles.test.ts`의 `RUNNING_SELECTORS`
  집합에 셀렉터를 추가하는 것은 포맷팅이 아니라 **디자인 결정**이다. 재생 중이 아닌 상태에
  live-amber가 필요해 보이면 그것은 다른 색을 써야 한다는 신호다.
- **발사 경로는 순수 함수가 결정한다**: 타일 press는 `tilePressFrame`, All Off는 `allOffPress`.
  컴포넌트 핸들러는 결과를 전달만 한다. 새 발화 경로를 만들 때도 이 형태를 유지해야
  AC 명제를 컴포넌트 렌더 없이 assert할 수 있다.
- **정지 클래스 면제**: `offDisabled`는 `blocked`에만 종속되며 `pending`/`busy`에 **절대**
  종속되지 않는다. 이 한 줄이 REQ-SHOWUI-012의 UI측 전부다.
- **그리드는 와이어 순서**: `panel.items`를 그대로 `map`한다. 정렬·필터·재배치 도입 금지.
- **레이아웃**: 860px 캡은 `.app`에서 `.chat-column`으로 이동했다. 패널을 접으면 M4 이전
  레이아웃이 정확히 복원된다.

### M4 미결 항목 (다음 마일스톤 의무)

- **M5 의무 — 단절 시 running 소거 배선**: `useCopilotSocket.ts`의 단절 핸들러는 아직
  `clearPendingRequests`를 호출한다. `clearOnDisconnect`(M1 제공, running·busy 소거 포함)로
  교체하는 것이 M5 범위이며, 그 전까지 REQ-SHOWUI-015의 UI 절반은 **미배선**이다.
  리듀서와 패널 렌더는 준비되어 있고, 남은 것은 호출 한 줄의 교체 + 회귀 테스트다.
- **M5 의무 — 재접속 시 재동기화**: 재연결 후 카탈로그+status 재요청(REQ-SHOWUI-015 후반).
  `sendPanelCatalogRequest`는 이미 노출되어 있으므로 호출 시점만 배선하면 된다.
- **M6 의무 — 실기 검증**: arm→fire 타임아웃 4초의 현장 적정성, 레일 스윕이 어두운 FOH에서
  실제로 읽히는지, 터치 타깃 44px가 장갑 낀 손에 충분한지는 실기에서만 확인된다.

### M5 — Fail-closed 하드닝 (cycle_type=tdd, RED→GREEN→REFACTOR)

기준선(변경 전, HEAD 857e9ed, **실측**): vitest **168 passed**, `tsc --noEmit` **exit 0**,
`npm run build` **exit 0**, pytest **1591 passed + 1 failed**(환경 기존 — 아래 참조).
결과(변경 후): vitest **176 passed**(+8), `tsc --noEmit` **exit 0**,
`npm run build` **exit 0**, pytest **1591 passed + 1 failed**(**변동 없음** — M5는 서버 무변경).

pytest의 1건 실패는 `test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`
로, 실행 중인 grandMA3 onPC가 UDP 9005(해당 테스트의 후보 포트 집합에 포함)를 점유해서 나는
**환경 기존 실패**다. M5는 `server/` 를 한 줄도 건드리지 않았고 기준선과 동일하다.

| AC | 대상 | 상태 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|---|
| AC-SHOWUI-010 ① 단절 시 running 소거 | REQ-015 전반 | **PASS** (RED 관측 후) | `npx vitest run src/useCopilotSocket.test.ts` | **RED**(교체 전): `expected { 'executor:41': { …(2) } } to deeply equal {}` · `expected [ { running: true, cue: '3' } ] to deeply equal []` — 4건 실패. **GREEN**(교체 후): 15 passed |
| AC-SHOWUI-010 ② 재접속 재동기화 | REQ-015 후반/016 | **PASS** (RED 관측 후) | 동일 | **RED**: `TypeError: resyncFrames is not a function` — 3건 실패. **GREEN**: `resyncFrames()` == `[panel_catalog_request, status_request]`, 둘 다 `v==1` |
| AC-SHOWUI-010 ③ 자동 재전송 금지 | REQ-016 (REQ-MVP-032 계승) | **PASS** | 동일 | 재동기화 프레임 문자열에 `panel_execute`/`panel_stop`/`"type":"chat"` **0건**. 변이 3(재동기화에 `panel_stop` 밀어넣기) → **KILLED** |
| §D 엣지 8 — 승인 대기 중 연결 종료 | AC-010 | **PASS** | 동일 | 승인 1건 + 리뷰 1건 + running 타일 1건 동시 보유 상태 → 단절 후 `pendingApprovals==[]` · `pendingReviews==[]` · `panel.running=={}` · `panel.busy==null` (4개 동시 assert) |
| 그리드 안정성(단절 후 리플로 금지) | REQ-017 | **PASS** (M5 신규 가드) | 동일 | 단절 후에도 `panel.items == [TILE]` 보존. 변이 2(단절 시 items도 비우기) → **KILLED** |
| 전체 회귀 | AC-SHOWUI-012 부분 | **PASS** | `npx vitest run` · `npx tsc --noEmit` · `npm run build` · `pytest server/tests/ -q` | `176 passed (9 files)` · `exit 0` · `exit 0` · `1591 passed, 1 failed`(기준선 동일) |
| M4 가드 무손상 | REQ-018 | **PASS** | `git diff --stat -- ui/src/styles.test.ts ui/src/styles.css` | 출력 없음(무수정). `✓ src/styles.test.ts (11 tests)` |
| AC-SHOWUI-013/014 (LIVE) | 실기 onPC | **DEFERRED-M6** | — | 라이브 체크리스트는 M6 소관 |

**RED 관측 기록**(교체 자체가 무엇을 바꿨는지의 증거): 교체 전 `useCopilotSocket.ts:30`은
`clearPendingRequests(state)`를 호출했고, running 타일을 보유한 상태로 `disconnected` 를
디스패치하면 **타일이 여전히 RUN 으로 보고**됐다(`[ { running: true, cue: '3' } ]`).
이것이 M4가 "REQ-SHOWUI-015의 UI 절반은 미배선"이라고 기록한 바로 그 상태다.
`clearOnDisconnect` 로 한 줄 교체한 뒤 동일 테스트가 통과한다 —
즉 이번 마일스톤에서 **fail-closed 약속이 처음으로 런타임에 발효**됐다.
증적: `.moai/state/verify/showui-m5/4-RED.log`(exit 1, 7 failed) → `5-GREEN.log`(exit 0, 15 passed).

**변이 주입(non-vacuity)**: 3종 → **3/3 KILLED**(생존 0).
① 재동기화에서 `status_request` 누락(2 failed) · ② 단절 시 타일 목록까지 비우기(1 failed) ·
③ 재동기화에 `panel_stop` 재전송 밀어넣기(3 failed). 상세: `6-mutation.log`.
단절 관련 4개 assert는 RED 자체가 변이 등가(교체 전 코드 = 변이체)이므로 별도 주입을 생략했다.

**계약 점검(E4)**: `grep -rn "localStorage" ui/src/` **0** · `window.confirm|window.alert` **0** ·
`PROTOCOL_VERSION` 양측 **1** 동일 · `git diff HEAD -- ui/package.json` **빈 출력**(신규 의존성 0).

**커버리지 — 열거 기반(측정 아님)**: `@vitest/coverage-v8` 미설치이며 설치는 신규 의존성
추가(제약 위반)이므로 **백분율을 보고하지 않는다.** M5 신규 export는 `resyncFrames` 하나이며
이를 실행하는 `it` 블록 **3건**(구성·재전송 금지·버전/타입)이다. 재배선된 `reducer`의
`disconnected` 분기는 `it` 블록 **8건**(기존 3 + 신규 5)이 실행한다.
`clearOnDisconnect` 자체의 순수 함수 테스트는 M1에서 `protocol.test.ts` 에 이미 존재하며,
M5는 그것을 **호출부에서** 실행하는 경로를 덮었다.
**미검증 잔여**: `socket.onopen` 핸들러 본체(실제 `socket.send` 호출)는 DOM/WebSocket 하니스가
없어 실행되지 않는다 — `resyncFrames()` 의 결과만 검증되고, 그것을 소켓에 흘리는 3줄은
M6 라이브 체크리스트 ⑥(WS 강제 종료/재접속)에서만 확인된다.

**M4가 이미 끝내둔 것 — M5가 다시 주장하지 않는 항목**(감사 시 중복 계상 방지):

- `health ≠ online` / `executions_blocked` 엣지 렌더는 **M4에서 완료**됐다
  (`panelGate` 5분기 + 패널 배너 + 타일 양쪽 동사 비활성; AC-SHOWUI-015 vitest 절반 PASS,
  `ShowPanel.test.tsx` 의 `panel-level gate` 8건). M5는 이 코드를 건드리지 않았다.
- 모달-부재 보장도 **M4에서 검증**됐다(`grep` 0건). M5에서 재실행해 0건을 재확인했을 뿐,
  새 작업이 아니다. **기계적 가드 테스트는 여전히 없다** — AC-SHOWUI-011 ①이 정한 검증 방법이
  grep이기 때문이며, 새 가드 파일 신설은 M5 범위를 넘는다(아래 잔여 위험 참조).
- 그리드 append-only·정렬 금지는 **M1/M4에서 완료**됐다
  (`protocol.test.ts` "stores the catalog in wire order without sorting it" / "replaces the
  catalog on refresh rather than appending a duplicate"). M5가 **새로 추가한 것은 단 하나** —
  단절이 타일 목록을 지우지 않는다는 가드다(위 표). 동작 자체는 교체 전에도 옳았고,
  이제 그 사실이 명시적으로 고정됐다.

**REFACTOR 판단**: 별도 리팩터링을 수행하지 않았다. 변경은 호출 한 줄 교체 + 순수 함수 1개
신설 + onopen 3줄이며, 추출하거나 중복을 제거할 구조가 생기지 않았다. `resyncFrames` 를
`protocol.ts` 가 아니라 `useCopilotSocket.ts` 에 둔 것은 이 파일이 이미
`connectProtocols`/`launchToken`/`reducer` 같은 "훅이 쓰는 순수 함수"를 테스트용으로 export 하는
자리이기 때문이고, M5 범위가 이 파일로 한정되어 있기 때문이다.

증적 로그: `.moai/state/verify/showui-m5/` (1 vitest 기준선 · 2 tsc 기준선 · 3 pytest 기준선 ·
4 RED · 5 GREEN · 6 mutation · 7 vitest 전체 · 8 tsc · 9 build · 10 pytest).

### M5에서 동결한 계약 (M6이 그 위에 쌓임)

- **단절 = running 소거는 이제 런타임 동작이다**: `useCopilotSocket.ts` 의 `disconnected`
  분기는 `clearOnDisconnect` 하나만 호출한다. `clearPendingRequests` 를 이 분기에서 다시
  직접 호출하는 것은 **회귀**다(패널 절반만 소거됨). 소거 대상을 늘리거나 줄일 일이 생기면
  `clearOnDisconnect` 안에서 처리한다 — 호출부를 갈라놓지 않는다.
- **재동기화는 읽기 전용이다**: `resyncFrames()` 는 요청 프레임만 반환한다. 여기에 실행·정지
  프레임을 추가하는 것은 REQ-SHOWUI-016(미확인 명령 자동 재전송 금지) 위반이며,
  테스트가 그것을 막는다("no execute or stop rides along").
- **onopen 은 매 연결마다 재동기화한다**: 최초 접속과 재접속을 구분하지 않는다. 구분을 도입하면
  재접속 경로가 세션당 0회 실행되는 코드가 되어 아무도 검증하지 못한다.
- **타일 목록은 서버 상태다**: 단절이 지우는 것은 관측(running·busy)뿐이고 목록은 남는다.
  목록을 지우면 재접속 시 그리드가 조작자 손 밑에서 재배치된다(REQ-SHOWUI-017 위반).

### M5 미결 항목 (M6 의무)

- **AC-SHOWUI-013 (LIVE)** — 라이브 체크리스트 7항목(①타일 실행 육안 확인 ②Off 해제
  ③채팅 연출 pin→발화→정지 ④LiveLock 제안 전용·송신 0건 ⑤앱 재시작 후 핀 복원
  ⑥**WS 강제 종료/재접속 → running 소거 후 재동기화** ⑦All Off 개별 Off + 비추적 재생 유지).
  ⑥은 M5가 배선한 경로의 유일한 실기 검증 지점이다.
- **AC-SHOWUI-014 (LIVE)** — responder degraded/offline 상태에서 패널 차단 표시
  (reply-port drift silent 서명 방어).
- **AC-SHOWUI-012 (전체 회귀)** — M6에서 최종 재확인. 단, pytest 1건은 onPC를 닫고 돌려야
  1592 green 이 된다(포트 점유 해제).
- **`server/web/PROTOCOL.md` 마감** — M5는 와이어 형태를 바꾸지 않았으므로
  `PROTOCOL_VERSION` 은 1 그대로다. 남은 문서 작업은 패널 메시지 5종(`panel_execute`/
  `panel_stop`/`panel_pin`/`panel_unpin`/`panel_catalog_request`)과 서버 이벤트 4종
  (`panel_catalog`/`panel_item_state`/`panel_busy`/`error(kind:"panel")`)의 기재,
  그리고 **재접속 시 클라이언트가 `panel_catalog_request` + `status_request` 를 보낸다**는
  이번 계약의 명문화다.
- **열린 라이브 질문 2건(이월)** — (a) 페이지 드릴다운이 반환한 실행기 번호가
  `Go+ Executor N` 이 실제로 발화하는 그 번호와 동일한지(AC-013 ①에서 확인),
  (b) arm 타임아웃 4000ms와 패널 가독성(RUN/OFF 15px, 레일)이 어두운 실기 FOH 모니터에서
  버티는지. 둘 다 실기에서만 답이 나온다.

### M6 — 전체 그린 + 라이브 E2E + 문서 마감 (부분 완료, 라이브 세션 1회)

기준선: HEAD `09e2c4f`. 실기 = grandMA3 onPC 2.4.2, 응답기 `copilot_responder.lua` **1.2.0**
(HEAD는 1.3.0 — 기준선 유지를 위해 의도적으로 업그레이드하지 않음), `osc_slot=2`,
`console_port=8000`, `receive_port=9005` — 전부 `settings.toml`에서 읽음(하드코딩 0).

**패키지 번들은 사용하지 않았다.** `dist/GrandMA3 Copilot.app`과 Tauri 번들은 모두 13:56 빌드로
M1~M5 다섯 커밋(15:44~19:15)보다 앞선다 — 번들 안에 `server/web/panel.py`가 부재하고
번들 UI의 `ShowPanel` grep이 0건이다. 라이브는 전 구간 개발 모드(`python -m server.web`,
`ui/dist` 19:16 빌드)로 수행했다.

| AC | 상태 | 검증 커맨드 / 증거 | 실제 출력 |
|---|---|---|---|
| AC-SHOWUI-012 | **PASS** | `.venv/bin/python -m pytest server/tests/ -q` · `(cd ui && npx vitest run)` | `1592 passed in 84.15s` · `Tests 176 passed (176)` |
| AC-SHOWUI-013 ① (시퀀스 타일) | **PASS** | 패널 `panel_execute sequence:41` → 감사 로그 | `Go+ Sequence 41 ok=True detail=OK`, `panel_item_state running=true`; **조작자 육안으로 조명 변화 확인** |
| AC-SHOWUI-013 ① (실행기 타일) | **DESCOPED-v1 → EXECREF-001** | 아래 §M6 결함(정정판) + §M6 결정(범위 축소) 참조 | v1은 드릴다운 실행기 타일을 **구조적으로 표시하지 않음**(카탈로그 소스에서 제거). 실행기 주소 결함(`console# = 100+i`) + 게이트 Executor 인식은 EXECREF-001로 이연. 시퀀스 타일 절반은 PASS(위 AC-013 ① 시퀀스 행) |
| AC-SHOWUI-013 ② | **PASS** | `panel_stop sequence:41` | `Off Sequence 41 ok=True`, `running` true→false |
| AC-SHOWUI-013 ③ | **PASS** | `chat` → `panel_pin` → execute → stop | `Store Sequence 90 Cue 1 'Blue Look' ok=True` → 핀 `sequence:90` 생성(그리드 0번) → `Go+/Off Sequence 90 ok=True` |
| AC-SHOWUI-013 ④ | **PASS** | `lock active` → `panel_execute` → 감사 로그 창 census | 프레임 `proposal`(`["Go+ Sequence 41"]`) → `error(kind:panel, 라이브 잠금…)` → `panel_item_state running=false`, **승인 카드 없음**; 창 내 `kind==command` **0건**, `blocked` 1건(`reason='live lock active'`), 하트비트 4건 |
| AC-SHOWUI-013 ⑤ | **PASS** | 백엔드 완전 종료(포트 0건 확인) → 재기동 → `panel_catalog_request` | 핀 `sequence:90` 복원, 그리드 index **0** 유지; `panel_pins.json` 실재(`id`/`source` 미저장 = 파생 확인) |
| AC-SHOWUI-013 ⑥ | **PASS** | 타일 running 상태에서 드라이버 프로세스 `kill -9`(비정상 종료) → 신규 소켓 | 수신 프레임 전량 = `status`,`status`,`panel_catalog`; **`panel_item_state` 0건**. 동시에 콘솔은 `Go+ Sequence 41 ok=True` 이후 Off 없이 **실제 재생 중** — 즉 "콘솔은 돌고 앱은 모른다"가 실기로 성립 |
| AC-SHOWUI-013 ⑦ | **PASS** | 3타일 발화 → 추적 running마다 개별 `panel_stop` | 콘솔 커맨드 6건 = `Go+`3 + `Off`3, 광역 타깃(`Thru`/`*`/`Everything`) **0건**; **데스크에서 직접 띄운 재생은 All Off 후에도 생존**(조작자 확인) = 한계가 사양대로 동작 |
| AC-SHOWUI-002/003 | **PASS(라이브)** | `panel_catalog_request` 실기 응답 | 섹션 2종 모두 `status:"ok"`; 시퀀스 비연속(1,2,11~16,30,41,50,62,71,80 — 3~10·17~29 부재)으로 인덱스 키잉 회귀 차단 실증; fixtures 섹션 구조적 부재 |
| AC-SHOWUI-014 | **PASS (라이브·완결, resume 세션)** | 아래 §M6 AC-014 라이브 완결 참조 | reply-port 드리프트 9005→9006(앱측, 콘솔 무변경) 유발 → `console_offline`; 핀 `sequence:90` membership 통과 후 HEALTH에서 차단(감사 `blocked` "Go+ Sequence 90", 창 내 `kind=command` **0건**); UI 상단 오프라인 배너 + amber "⛔ 실행 차단됨" 패널 배너 + 드리프트 안내(양 포트 명시) + 타일 `is-blocked`·Go+/Off/ALL OFF 전부 `disabled`(JS assert); 양성대조: 9005 복귀 시 online |

증적(원 세션): `.moai/state/verify/showui-m6/` (`driver.py` 하니스, 세션별 `frames.jsonl`/`driver.log`,
`probe_executor_address.py`) + `server/audit_logs/audit-20260722.jsonl`.
원 라이브 세션 콘솔 커맨드 총 **19건 — 성공 17 / 실패 2**, 실패 2건 모두 실행기 주소 문제.
증적(resume 세션 — 실행기 주소 실측 + AC-014 완결): `.moai/state/verify/showui-m6-resume/`
(`executor-offset.jsonl` 16행, `probe_executor_offset.py`, `live-ac014b/` frames.jsonl,
`live-ac014/` backend 로그) + 동일 감사 로그.

### M6 결함 (정정판) — 실행기 타일 주소: 콘솔 실번호 = `100 + i`

**정정 배경 — 이전 표는 미검증 주장이었다.** 원래 라이브 세션(HEAD `09e2c4f`, 13:55)이
실제로 발화한 실행기 커맨드는 `Go+ Executor 11` **단 1건**뿐이다(`audit-20260722.jsonl:298`,
`ok=false 'Illegal object'`; 원 세션 census 19 kind=command, 성공 17 / 실패 2). 이전 표의
"1·5·91·92·93·95 → Illegal, 101 → ok" 중 나머지 7행은 발화 없이 추정된 값이었고, 특히
**"101 → ok" 행은 오독**이다 — `Off Executor 101`이 실제 ok인 것은 맞으나 그것이 i=101 타일의
정상 발화를 뜻하지 않는다(아래 충돌 참조). 이전 표는 이로써 **폐기·대체(superseded)**한다.
텍스트 추론만으로 결함을 단정한 그 표는 `verification-claim-integrity.md §1.1 surface 3`
(도구 확인 없는 결함 주장 금지) 위반이었다.

**정정 — resume 세션에서 16개 커맨드를 1:1 실측했다.** page 1의 자식 실행기 8개 각각에 대해
`Off Executor i`(raw)와 `Off Executor i+100`(plus100) 두 형식을 모두 발화하고 감사에 기록했다.

| 응답기 i | 배정 시퀀스 | `Off Executor i` (raw) | `Off Executor i+100` |
|---|---|---|---|
| 1 | Sequence 50 | `Illegal object` | `ok` |
| 5 | Sequence 30 | `Illegal object` | `ok` |
| 11 | Sequence 41 | `Illegal object` | `ok` |
| 91 | Sequence 80 | `Illegal object` | `ok` |
| 92 | Sequence 14 | `Illegal object` | `ok` |
| 93 | Sequence 16 | `Illegal object` | `ok` |
| 95 | Sequence 62 | `Illegal object` | `ok` |
| 101 | Sequence 71 | **`ok`(충돌!)** | `ok` |

**결론 — 콘솔 실번호 = `100 + i`, 균일.** 8개 실행기 전부에서 `Off Executor i+100`이 발화했고,
`Off Executor i`(raw)는 i=101을 제외하고 전부 `Illegal object`였다. 즉 드릴다운 인덱스 i는
커맨드라인 주소가 아니며, 실번호는 8개 전부에서 균일하게 `100 + i`다.

**i=101 행은 무오류 오발(silent wrong-object) 위험 — 7건의 거절보다 나쁘다.**
`Off Executor 101`도 `Off Executor 201`도 둘 다 `ok`를 반환한다. 101은 i=101(Sequence 71)의
raw 주소인 동시에 i=1(Sequence 50)의 `+100` 주소이기 때문이다. 따라서 패널이 "Sequence 71"로
라벨한 타일이 번호 101로 발화하면 **오류 없이 Sequence 50의 실행기를 켠다** — 잘못된 조명이,
아무 경고 없이. 나머지 7개의 `Illegal object`는 최소한 소리를 내지만, i=101은 조용히 틀린다.

증적: `.moai/state/verify/showui-m6-resume/executor-offset.jsonl` (16행, i/name/addressed/form/
status 1:1) + `server/audit_logs/audit-20260722.jsonl`의 마지막 16개 `Off Executor` 행(23:11·23:14
창). 이로써 결함은 **도구 확인됨** — 텍스트 추론이 아니라 실발화 관측이며,
`verification-claim-integrity.md §1.1 surface 3`(결함은 도구가 확인해야 성립)을 충족한다.

**게이트는 이미 예측적으로 경고했다.** `Go+ Executor 11`의 승인 카드 사유는
`["reference-invoking command", "unverifiable reference: no recognizable target object"]`였고,
시퀀스 타일은 승인 카드 자체가 뜨지 않았다. 안전 계층의 "확인 불가능한 참조" 판정이 콘솔 거절을
예측적으로 맞혔다. 결함 계열은 `copilot-fid-vs-slot-decision`(픽스처 `no` = 패치 슬롯 ≠ FID)과
동일한 "인덱스 ≠ 주소"다. ASSUMPTION-7(드릴다운 i = 커맨드 번호)은 이 쇼파일에서 최종 반증됐다.

### M6 — AC-SHOWUI-014 라이브 완결 (PASS)

원 세션에서 미완이던 AC-014를 resume 세션에서 **핀 경로 실행-차단 + UI 렌더까지 완결**했다.
membership이 health보다 먼저 검사되므로(§M6 미결 원 항목 1의 함정), 오프라인에서 실행-차단 경로에
도달하려면 살아있는 카탈로그 또는 핀이 선행되어야 한다 — AC-013 ③에서 만든 핀 `sequence:90`이
재기동 후 복원되어 그 선행을 만족했다.

- **유발**: reply-port 드리프트 9005→9006. **앱측 `receive_port`만 변경**, 콘솔 OSC 테이블은
  무변경. 결과 `status health=console_offline, executions_blocked=true, console_input=listening,
  reply_port=9005, receive_port=9006`(`live-ac014b/frames.jsonl` 1행, `live-ac014/backend*.log`).
- **실행-차단 경로**: `panel_execute sequence:90` → membership 통과 → HEALTH에서 차단.
  감사 로그에 `{"event":"blocked","command":"Go+ Sequence 90","reason":"console offline — new
  executions are blocked (REQ-MVP-030)"}`, 차단 창 내 `kind=command` **0건**. 프레임:
  `error(kind:panel, "콘솔 오프라인 상태입니다 — 패널 실행이 차단되었습니다.")` +
  `panel_item_state running=false`(`live-ac014b/frames.jsonl` 3~4행).
- **UI 렌더**: 상단 오프라인 배너 + amber "⛔ 실행 차단됨" 패널 배너 + 드리프트 안내
  (reply 9005 / receive 9006 **양 포트 명시**) + 핀 타일 class `is-blocked` + Go+/Off/ALL OFF
  버튼 전부 `disabled=true`(JS assert) + 타일 노트 "실행 차단됨".
- **양성 대조**: `receive_port`를 9005로 되돌리자 health가 online으로 복귀 — 차단이 드리프트에
  귀속됨을 증명(단순 무응답 아님).

증적: `.moai/state/verify/showui-m6-resume/live-ac014b/`(frames.jsonl) +
`.moai/state/verify/showui-m6-resume/live-ac014/`(backend 로그) + `audit-20260722.jsonl`.

### M6 결정 — 실행기 타일 v1 범위 축소 (→ SPEC-COPILOT-EXECREF-001)

**결정(사용자 승인).** v1에서 **드릴다운 실행기 타일을 숨긴다.** 주소 결함(`console# = 100+i`)의
수정과 게이트 Executor 인식은 **후속 SPEC-COPILOT-EXECREF-001**로 이연한다.

**구현 방식 — 구조적 부재(REQ-SHOWUI-003 선례).** 런타임 필터가 아니라 카탈로그 소스에서 제거:
`server/web/panel.py`의 `PANEL_CATALOG_SECTIONS`에서 `pages`(drilldown=True, target_kind=executor)
`SectionSpec`을 삭제하여 `sequences` 단일 소스만 남긴다 — fixtures가 애초에 소스가 아닌 것과 동일한
"인덱스 ≠ 주소" 사유. 드릴다운 순회 기계(`build_catalog`의 drilldown 분기 + `drill_into`)는
EXECREF-001이 재사용하도록 **보존**하고, `SectionSpec` 한 줄만 부재시킨다.

**핀 실행기는 안전 — 손대지 않는다.** 핀의 실행기 번호는 채팅의 `Assign Sequence X At Executor Y`
커맨드에서 온 **실 콘솔 번호 Y**(예: 201)이지 드릴다운 인덱스가 아니므로 올바르게 주소한다.
따라서 `PANEL_TARGET_KINDS`의 `"executor"`, `pin_from_seed`, `_TARGET_WORD`, 실행기-핀 지원은
전부 유지한다. 라이브에서 핀 실행기 201은 정상 발화했다(원 세션 `Off Executor 201 ok`).

**채팅 rig-context 경로는 별개.** `server/orchestrator/tools.py`는 `PANEL_CATALOG_SECTIONS`를
임포트하지 않는 별도 소비자이며, 그 실행기 처리는 EXECREF-001 범위 — 본 범위 축소와 무관.

**@MX.** `panel.py` `PANEL_CATALOG_SECTIONS` 위 `@MX:ANCHOR`/`@MX:REASON`에 `console# = 100+i`
근거와 i=101 충돌을 기록하고 `@MX:DEBT`/`@MX:CEILING`/`@MX:UPGRADE`(EXECREF-001이 `console#
= page*100 + i`로 섹션 재추가)를 추가함.

### M6 문서 정정 — `PROTOCOL.md` 재접속 조항

정정 전(`PROTOCOL.md:258`): *"running state is rebuilt from a `panel_catalog_request` +
`status_request` resync on reconnect."* — **사실이 아니다.**

- **구조적 근거**: `panel_item` 의 와이어 키 7개(`id`/`kind`/`target_kind`/`target`/`name`/
  `appearance`/`source`)에 `running` 이 없다(`messages.py:317-358`). `running` 은
  `panel_item_state_event` 에만 존재하고(`messages.py:410-423`), 그것을 발화하는 `_emit_state` 는
  execute/stop 경로에서만 호출된다(`panel.py:739,754,764,769`). `self._running` 은 연결마다
  새로 비는 집합이다(`panel.py:624`).
- **행동적 근거**: 재접속 소켓 수신 프레임 전량이 `status`,`status`,`panel_catalog` — 0건 재생.
- **위험 방향**: 옛 문장을 믿은 클라이언트는 "콘솔은 재생 중인데 앱은 아무것도 안 돈다고 말하는"
  상태를 재구축 실패가 아니라 정상으로 오해한다.

정정 후 문장은 재구축 대상이 **타일 목록 + health** 이며 running 은 의도적으로 재구축되지
않음을 명시한다. `PROTOCOL_VERSION` 은 1 유지(와이어 형태 무변경).

`PROTOCOL.md` 의 패널 메시지 8종 기재는 M1/M3 시점에 이미 완료되어 있었고, 코드와 1:1로
일치함을 재확인했다(client 5종 + server 3종, 양측 allowlist 대조).

### M6 잔여/해소 항목

1. **[해소] AC-SHOWUI-014 (LIVE)** — resume 세션에서 핀 `sequence:90` 경유 실행-차단 경로 +
   UI 배너/버튼 렌더 + reply-port 드리프트 유발 + 양성대조까지 완결(위 §M6 AC-014 라이브 완결).
   원 함정(카탈로그 빈 오프라인 → `fire()`가 membership을 health보다 먼저 검사(`panel.py:643`)해
   `unknown_target` 반환)은 AC-013 ③에서 만든 핀이 재기동 후 복원되어 해소됨.
2. **[해소] 실행기 주소 결함 처리 방침** — v1 범위 축소로 결정(위 §M6 결정). 주소 수정
   (`console# = 100+i`) + 게이트 Executor 인식은 EXECREF-001로 이연.
3. **[잔여] 열린 라이브 질문 (b) 미답** — arm 타임아웃 4000ms 체감, 레일 스윕의 모션 가독성,
   두 amber 배너(상단 오프라인 + 패널 차단) 분리 인지가 어두운 FOH 물리 모니터에서 적절한지의
   **주관적 육안 판단**. 조작자가 콘솔 앞에서 관측해야만 답할 수 있어 여전히 미측정(§E.3 Gaps).
4. **[정보] `--no-session-backup` 사전검증 구간** — 오프라인 사전검증은 백업 없이 기동했다.
   이후 라이브 본 세션은 백업 켠 정상 모드로 재기동했고 `SaveShow ok=True`를 확인했다.

## §E.3 Run-phase Audit-Ready Signal

M6 closure(실행기 타일 v1 범위 축소 + AC-014 라이브 완결) 기준 run-phase audit-ready 선언.
5-section evidence format (`verification-claim-integrity.md §3`).

### Claim (주장)

1. v1 카탈로그는 `sequences` 단일 소스만 자동 열거한다 — 드릴다운 실행기 타일은 **구조적 부재**.
2. 실행기 타일 결함은 **도구 확인됨**: 콘솔 실번호 = `100 + i`(page-1, 8/8 균일), i=101은
   무오류 오발(silent wrong-object) 충돌.
3. AC-SHOWUI-014(핀 경유 실행-차단 + UI 렌더 + 드리프트 유발 + 양성대조)는 라이브 완결 **PASS**.
4. 전체 회귀 그린(환경 실패 1건 제외), UI 그린, 신규 lint 0.
5. 핀 실행기 경로는 무변경·정상(범위 축소는 auto 드릴다운 소스에만 적용).

### Evidence (증거)

- pytest: `.venv/bin/python -m pytest server/tests/ -q` → `1 failed, 1591 passed in 83.58s`.
  유일 실패 = `test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`,
  `OSError: [Errno 48] Address already in use` — onPC가 UDP 9005를 점유 중인 **환경 실패**(코드 회귀 아님).
- vitest: `(cd ui && npx vitest run)` → `Test Files 9 passed (9)` / `Tests 176 passed (176)`. UI 무변경.
- 카탈로그 소스: `grep -n "SectionSpec(name=" server/web/panel.py` → 1행(`sequences`)만.
  `grep -n "pages\|drilldown" server/web/panel.py` → `pages` 매치 **0**, `drilldown`은 EXECREF-001용
  휴면 순회 기계 3행(field 115 / branch 408 / capped 420)만 잔존.
- 실행기 실측: `.moai/state/verify/showui-m6-resume/executor-offset.jsonl`(16행) +
  `audit-20260722.jsonl` 마지막 16 `Off Executor` 행 → `Off Executor i+100` 8/8 ok,
  `Off Executor i`(raw) i=101 제외 7/7 `Illegal object`, `Off Executor 101`·`Off Executor 201` 동시 ok(충돌).
- AC-014: `live-ac014b/frames.jsonl`(status console_offline reply_port=9005 receive_port=9006 →
  panel_execute sequence:90 → error(kind:panel) + panel_item_state running=false) +
  `audit-20260722.jsonl` `{"event":"blocked","command":"Go+ Sequence 90","reason":"console offline — new executions are blocked (REQ-MVP-030)"}`.
- lint: `ruff check` — 수정 3개 .py(panel.py / 2 test) 전부 clean; 잔존 3건 E501은 **미변경 파일**
  (`server/safety/console.py:289,343`, `server/tests/test_web_provision_api.py:102`) 기존 baseline.

### Baseline-attribution (baseline 귀속)

- pytest baseline: 본 트리(HEAD `37adbff` + 본 변경) 이번 run 실측. 원 M6 표(위 AC-012 행) `1592 passed`와
  총계 동일(1592=1591+1) — 본 변경은 test_web_panel.py 65→65, test_web_panel_execute.py 56→56로 순증감 0.
  차이는 onPC의 9005 점유로 인한 환경 실패 1건뿐(코드 회귀 아님).
- lint baseline: 3건 E501은 본 변경 이전부터 존재(내 diff 파일 목록에 없음 — `git status --porcelain`로 확인).
- 실행기 결함 baseline: 원 세션은 `Go+ Executor 11` 1건만 발화(`audit …:298`); 이번 resume 세션이
  16 커맨드를 새로 실측 — 캐리오버 없는 fresh 측정.

### Gaps (미검증)

- **열린 질문 (b) 주관적 육안 판단 미측정**: arm 타임아웃 4000ms 체감, 레일 스윕의 모션 인지,
  두 amber 배너(상단 오프라인 + 패널 차단) 분리 인지가 어두운 FOH **물리 모니터**에서 적절한지 —
  콘솔 앞 사람 없이는 측정 불가. 관측이 없으므로 declare하지 않는다.
- **UI 커버리지는 열거 기반, 백분율 미측정**: `@vitest/coverage-v8` 미도입(의도적 zero-new-dependency).
  176 vitest는 열거된 케이스 통과이지 라인 커버리지 수치가 아니다.
- **`+100` 공식의 page-N 일반화 미검증**: 쇼파일에 page가 **1개뿐**이라 `console# = page*100 + i`의
  page≥2 항은 관측되지 않음 — page-1(=100+i)만 실측. 일반화는 EXECREF-001의 몫.
- **panel.py 드릴다운 분기는 기본 카탈로그로 미실행**: 휴면 코드로 보존(EXECREF-001용). 분류 로직만
  monkeypatch 테스트(`TestRetainedDrilldownMachineryForExecref`)로 별도 커버.

### Residual-risk (잔여 위험)

- onPC의 9005 점유 해제 후 `test_every_candidate_socket_is_released` 재실행 시 pass 예상이나 본
  세션에서 미확인(환경 의존, TOCTTOU 창).
- 휴면 드릴다운 분기는 EXECREF-001 활성화 전까지 기본 경로 미실행 — 회귀 감지는 monkeypatch 테스트 +
  구조 회귀 테스트(`test_no_catalog_section_drills_into_executors`)에 의존.
- 패키지 번들(.app/Tauri)은 M1~M6 커밋보다 앞선 빌드라 본 변경 미반영 — 라이브는 전 구간 개발 모드.

### Audit-ready signal

```yaml
run_complete_at: 2026-07-23T00:00:00Z
run_commit_sha: 13a2f6b   # backfilled (spec-frontmatter-schema D3 exemption — a commit cannot name its own hash)
run_status: audit-ready
m6_disposition: executor-tile DESCOPED-v1 → SPEC-COPILOT-EXECREF-001
ac_summary:
  AC-SHOWUI-013_sequence_half: PASS
  AC-SHOWUI-013_executor_half: DESCOPED-v1
  AC-SHOWUI-014: PASS
  AC-SHOWUI-002_003_live: PASS
ac_fail_count: 0
regression_new_failures: 0
environmental_failures: 1   # test_every_candidate_socket_is_released — onPC holds UDP 9005
pytest: "1591 passed, 1 environmental-fail"
vitest: "176 passed"
new_warnings_or_lints_introduced: 0   # 3 pre-existing E501 live in untouched files
cross_platform_build: N/A   # Python/TS project, no build-tag matrix
l44_pre_commit_fetch: N/A   # no remote (local-only, main-direct)
l44_post_push_fetch: N/A    # no remote
total_run_phase_files_this_change: 5   # panel.py + test_web_panel.py + test_web_panel_execute.py + PROTOCOL.md + progress.md
m1_to_mN_commit_strategy: per-milestone commits, main-direct (no PR), local-only
preserve_list_post_run_count: intact   # tools.py / test_tools.py / pin_from_seed / _TARGET_WORD / PANEL_TARGET_KINDS untouched
```

## §E.4 Sync-phase Audit-Ready Signal

5-section evidence format (`verification-claim-integrity.md §3`).

### Claim (주장)

1. sync-auditor 독립 평가 **PASS 0.93**(harmonic mean, must-pass 4/4 PASS) — SHOWUI-001의
   `in-progress → completed` 전환 근거가 성립한다.
2. sync-auditor가 제기한 2건의 SHOULD 항목(D1/D2) 중 D2(acceptance.md descope 각주)는 본 sync 이전에
   이미 해소(커밋 `14e2b14`); D1(SPEC-COPILOT-EXECREF-001 미materialize)은 후속 SPEC 자체의 존재
   여부이므로 SHOWUI-001 범위에서 해소 불가 — 다음 SPEC(EXECREF-001) plan 단계로 이연.
3. CHANGELOG.md `[Unreleased] → ### Added`에 SHOWUI-001 항목 신설, spec.md/plan.md/acceptance.md/
   progress.md 4개 아티팩트 전부 `completed`(또는 그에 상응하는 prose status) 전환 완료.
4. README.md는 milestone별 섹션 관례(M2~M7, Stage-1/2)를 따르며, 패널이 사용자 대면 신규 표면이므로
   해당 관례에 맞춰 1개 섹션 추가.

### Evidence (증거)

- sync-audit 리포트: `.moai/state/verify/showui-m6-resume/sync-audit.md` — Overall Verdict **PASS**,
  harmonic mean `4/(1/0.92+1/0.95+1/0.90+1/0.95)=0.930`, 4-dim 표(Functionality 92/Security 95/
  Craft 90/Consistency 95), Merged AC Status Table 전 AC PASS/DESCOPED-v1(사용자 승인) 일치, Must-Pass
  Gate Check 4/4 PASS.
- D2 해소 커밋: `git show 14e2b14 --stat` → `.moai/specs/SPEC-COPILOT-SHOWUI-001/acceptance.md` 1개
  파일, AC-SHOWUI-013 행에 descope 각주 삽입 확인(본 파일 §C 표 상단 재확인 가능).
- pytest 재실측(본 sync 세션, 커밋 전): `.venv/bin/python -m pytest server/tests/ -q` →
  `1 failed, 1591 passed in 85.05s`; 유일 실패 = `test_web_reply_discovery.py::TestDiscovery::
  test_every_candidate_socket_is_released`(`OSError: [Errno 48] Address already in use`, onPC가
  UDP 9005 점유 — §E.3에서 이미 선언된 동일 환경 실패, 신규 회귀 아님).
- CHANGELOG: `grep -c "SHOWUI" CHANGELOG.md` → 신설 전 0(중복 방지 확인) → 신설 후 1개 항목 블록.
- 아티팩트 상태 전환: `grep -n "^status:" spec.md` → `completed`; `grep -n "^status:" plan.md acceptance.md`
  → prose descriptor `completed (v0.2.1, 2026-07-23 …)`.

### Baseline-attribution (baseline 귀속)

- sync-audit 판정은 본 sync 세션이 아니라 M6 close 직후 별도 sync-auditor 실행분(HEAD `df6bc16`,
  M6 close `13a2f6b` + §E.3 SHA backfill `df6bc16`)의 결과를 인용 — 본 sync 세션은 그 판정을
  재실행하지 않고 인용하되(§Evidence에 리포트 경로 명시), pytest만 본 세션에서 재실측하여
  판정 시점 이후 코드 드리프트가 없음을 별도로 확인했다(1591 passed 동일, 환경 실패 동일 1건).
- CHANGELOG 중복 검사(`grep -c`)는 본 sync 세션에서 편집 직전 실측한 baseline(0건)이다.

### Gaps (미검증)

- SPEC-COPILOT-EXECREF-001의 실제 SPEC 디렉터리 materialize는 본 sync의 범위 밖 — 자동 메모리에
  "plan 완료·미커밋"으로 기록되어 있으나, 그 커밋 여부는 본 세션에서 직접 확인하지 않았다(다른 세션 소관).
- README.md 신설 섹션은 sync-auditor가 직접 재평가하지 않은 항목(sync-audit 리포트는 M6 close
  시점 코드만 평가) — 본 sync 작성자 자체 판단으로 milestone 섹션 관례를 따라 추가.
- 열린 라이브 질문 (b)(주관적 FOH 가독성)는 §E.3에서 이미 미측정으로 선언되어 있으며 본 sync에서도
  추가 관측 없음 — 후속 SPEC 또는 실사용 피드백으로 이연.

### Residual-risk (잔여 위험)

- onPC UDP 9005 점유 환경 실패는 CI/무인 환경에서 onPC를 열지 않는 한 계속 재현될 수 있음 — 코드
  회귀가 아니므로 sync를 막지 않으나, 향후 pytest 실행자는 이 실패를 신규 회귀와 혼동하지 않아야 한다.
- 원격 저장소 부재(local-only)로 이 sync 커밋은 push되지 않는다 — 다음 세션에서 원격이 추가되면
  이 커밋 이력을 포함한 전체 브랜치를 검토 후 push할 것.

### Audit-ready signal

```yaml
sync_complete_at: 2026-07-23T00:00:00Z
sync_status: completed
sync_auditor_verdict: PASS 0.93 (harmonic mean; must-pass 4/4 PASS)
sync_auditor_report: .moai/state/verify/showui-m6-resume/sync-audit.md
should_items:
  D2_acceptance_descope_note: RESOLVED (commit 14e2b14, pre-sync)
  D1_execref001_materialization: DEFERRED (next-SPEC scope, not resolvable within SHOWUI-001)
changelog_entry_position: "[Unreleased] > ### Added, first entry"
frontmatter_status_transitions:
  spec.md: "in-progress -> completed"
  plan.md: "draft (prose descriptor) -> completed (prose descriptor)"
  acceptance.md: "draft (prose descriptor) -> completed (prose descriptor)"
  progress.md: "run_status audit-ready -> sync_status completed (this block)"
pytest_resync: "1591 passed, 1 environmental-fail (unchanged from §E.3)"
vitest_resync: "not re-run this session (unchanged since §E.3, UI untouched by sync)"
readme_updated: true
b12_self_test_a_pre_emission_grep: "grep -c SHOWUI CHANGELOG.md -> 0 before emission (no duplicate)"
b12_self_test_b_ac_count_match: "acceptance.md SSOT AC identifiers == 16 (AC-SHOWUI-001..003, 004a, 004b, 005..015 — grep -oE '\\*\\*AC-SHOWUI-[0-9]+[ab]?\\*\\*' | sort -u | wc -l); CHANGELOG entry references full milestone scope M1-M6, consistent"
b12_self_test_c_file_path_verification: "all file paths cited in CHANGELOG entry verified via ls (server/web/panel.py, server/web/messages.py, ui/src/, .moai/state/verify/showui-m6-resume/sync-audit.md)"
```

## §F Phase 4 Mode Selection

### 입력 파라미터

- tier: L (5-artifact 세트 존재)
- scope: 약 12~15 파일 (M1~M6 누계; M1 단독은 5 파일)
- domain count: 2 (UI/TypeScript, 서버/Python) — 3 미만
- file language mix: TypeScript + Python + Markdown, 코딩 중심(신규 로직 작성)
- concurrency benefit: LOW — 프로토콜 계약이 M2~M6 전체를 규정하는 순차 의존 체인

### 모드 평가

| Mode | 선택 | 근거 |
|---|---|---|
| 1 trivial | 미선택 | 신규 모듈·신규 프로토콜 타입 5종 — trivial 아님 |
| 2 background | 미선택 | Write/Edit 수반 (read-only 아님) |
| 3 agent-team | 미선택 | RETIRED (tombstone) |
| 4 parallel | 미선택 | 코딩 중심 + 도메인 2개(<3). Anthropic coding-task parallelism caveat 적용 |
| 5 sub-agent | **선택** | 기본 폴백. 마일스톤당 순차 `Agent(manager-develop)` 1회, cycle_type=tdd |
| 6 workflow | 미선택 | 기계적 균일 변환 아님(신규 설계 코드), ~30파일 미만, 파일 간 의존 존재 |

**Decision: sub-agent**

### 정당화

M1은 프로토콜·데이터 모델 계약으로 M2~M6 전체를 규정하는 단일 응집 단위다. 5개 파일(protocol.ts / protocol.test.ts / messages.py / test_web_messages.py / PROTOCOL.md)이 하나의 계약을 양측에서 미러링하므로 분할 시 측별 드리프트 위험이 오히려 커진다. Anthropic의 coding-task parallelism caveat("most coding tasks involve fewer truly parallelizable tasks than research")에 따라 Mode 5 순차 sub-agent가 정확한 선택이며, Mode 6은 균일 기계 변환 조건을 충족하지 않는다.

### 게이트 기록

- **Plan Audit Gate**: 재실행 skip (4조건 전부 충족) — 최근 verdict PASS 0.93 (≥0.90), plan 아티팩트 무변경(전부 커밋 9836714), 24시간 이내(2026-07-22).
- **Implementation Kickoff Approval (plan→run HUMAN GATE)**: **APPROVED** 2026-07-22, 사용자 3결정 확정 —
  ① 브랜치: `feat/app-deploy-file-import` 유지 (원격 없음 → PR 불가, Route B의 PR 단계는 로컬 커밋으로 대체)
  ② 디자인 페이즈 D1~D5: **생략** — design.md v0.2.1이 이미 구현 가능한 디자인 계약(§1~§9, REQ 트레이서빌리티 포함)이며 `.moai/design/system.md` 부재는 design.md §3 + `styles.css :root`를 canonical로 삼는 것으로 갈음
  ③ 착수 범위: **M1 선행 후 사용자 확인 → M2~M6** (계획서가 M1을 최고 가역성-민감 항목으로 지정)
