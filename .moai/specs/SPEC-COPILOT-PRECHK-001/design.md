# SPEC-COPILOT-PRECHK-001 — 설계 근거 (design)

status: draft (v0.1.0, 2026-07-29) · Tier L · 출처: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:102-105` · 본 문서는 spec.md 요구의 설계 근거와 위험 검토를 담는다. 설계 슬롯은 5건이고 전부 닫혔다.

> **참조 규약.** 본 SPEC의 정본 `research.md` · `spec.md` · `acceptance.md`는 줄번호로 인용하지 않고 `REQ-PRECHK-001` 같은 안정 토큰, `AC-PRECHK-001` 같은 안정 토큰, `ASSUMPTION-25` 같은 안정 토큰, 절 제목만 쓴다. `파일:줄`은 코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트에만 쓴다.
>
> **축약 금지.** 요구·인수 토큰은 슬러그 포함 완전형만 쓴다. 슬러그를 뺀 형태는 이 문서 전체에 0건이다. clarification 마커는 0건이다. 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]`으로 표기하며, `[실측]`은 라이브 콘솔 직접 관측을 기록한 `research.md` 절에만 붙인다.

---

## §1. 의도

본 SPEC은 쇼 시작 전에 **패치 메타데이터를 읽어 정합성 위험을 보고**하고, 픽스처 응답 확인은 **사람이 콘솔에서 눈으로 확인할 수 있는 매크로**로 보조한다. 읽기가 주 축인 첫 SPEC이므로 설계의 중심은 "더 많이 쏘기"가 아니라 "읽은 것과 읽지 못한 것을 섞지 않는 것"이다.

만드는 것은 셋이다.

| 산출 | 내용 | 연결 토큰 |
|---|---|---|
| 패치 인벤토리 | `Patch/Stages/1/Fixtures` 열거와 확정 프로퍼티 판독 | `REQ-PRECHK-001`, `REQ-PRECHK-002`, `REQ-PRECHK-003`, `REQ-PRECHK-004`, `REQ-PRECHK-005` |
| 정합성 판정 | 주소 정규화, 주소 중복, 조건부 구간 겹침, 판독 실패 분리 | `REQ-PRECHK-006`, `REQ-PRECHK-007`, `REQ-PRECHK-008`, `REQ-PRECHK-009`, `REQ-PRECHK-010` |
| 매크로와 리포트 | 그룹 기반 응답 확인 매크로, 2단 리포트, 한국어 표현, 툴 배선 | `REQ-PRECHK-011`, `REQ-PRECHK-012`, `REQ-PRECHK-013`, `REQ-PRECHK-014`, `REQ-PRECHK-015`, `REQ-PRECHK-016`, `REQ-PRECHK-017`, `REQ-PRECHK-018`, `REQ-PRECHK-019`, `REQ-PRECHK-020` |

만들지 않는 것은 넷이다.

| 제외 | 이유 | 고정 토큰 |
|---|---|---|
| 무응답 픽스처 자동 탐지 | 응답기가 하드웨어 피드백을 수집하지 않는다. `build_exec_result`는 `Cmd()` 결과 문자열만 분류한다 `[코드]` `console/lua/copilot_responder.lua:690-706`. | `REQ-PRECHK-014` |
| DMX 출력값 판독 | 응답기 디스패치 표면은 `ping` · `state` · `prop` · `exec` · `deploy`뿐이다 `[코드]` `console/lua/copilot_responder.lua:884-946`. | `REQ-PRECHK-014` |
| 쇼파일 파일 파싱 | 라이브 응답기 표면을 통해 읽는다. 쇼파일 파서 신규 작성은 본 SPEC 범위가 아니다. | `REQ-PRECHK-001` |
| 패치 수정과 주소 재배치 | 본 SPEC은 판정과 보고만 한다. 자동 재배치는 물리 배선 정책을 요구하는 별도 산출물이다. | `REQ-PRECHK-015`, `REQ-PRECHK-016` |

설계의 성공 조건은 충돌을 많이 찾는 것이 아니라, **충돌 0건이라는 말이 어떤 관측 범위에서만 참인지**를 정확히 말하는 것이다.

---

## §2. 변경 표면

### §2.1 예상 신규·수정 파일

| 파일 | 신규/수정 | 근거 | PRESERVE 대조 |
|---|---|---|---|
| `server/prechk/__init__.py` | 신규 | 신규 모듈 경계. 오케스트레이터가 쓰는 공개 함수만 노출하고 콘솔 포트 구현을 모른다. | 신규 경로라 침범 0건 |
| `server/prechk/inventory.py` | 신규 | 열거, 슬롯별 보강 판독, 프로퍼티 형태 검증, 판독 실패 분류. | 신규 경로라 침범 0건 |
| `server/prechk/patch.py` | 신규 | 주소 정규화, 주소 중복, 조건부 구간 겹침 판정. | 신규 경로라 침범 0건 |
| `server/prechk/macro.py` | 신규 | `ASSUMPTION-26`이 GO일 때 M0가 실측한 리터럴만 써서 그룹 기반 매크로 커맨드 생성. | 신규 경로라 침범 0건 |
| `server/prechk/report.py` | 신규 | 집계와 픽스처별 2단 리포트, 한국어 사용자 대면 문자열, 닫힌 판정 어휘 매핑. | 신규 경로라 침범 0건 |
| `server/orchestrator/tools.py` | 수정 | 신규 모델 도달 툴 1종. 기존 `ToolRegistry`는 정의 튜플과 핸들러 맵으로 닫힌 디스패치를 수행한다 `[코드]` `server/orchestrator/tools.py:450-465`. | 잠긴 `_PROGRAMMER_STATE_COMMANDS`는 `server/orchestrator/tools.py:247-251`, 실행/dedupe 루프는 `server/orchestrator/tools.py:536-582`; 둘 다 무변경 |
| `server/safety/console.py` | 조건부 수정 | 승인 시 `query_state`와 동형인 `query_property` 추가. 현재 `query_state`는 `build_state_query`로 왕복하고 실패·타임아웃을 예외로 전파한다 `[코드]` `server/safety/console.py:372-386`. | `server/safety/**` PRESERVE의 승인 대기 예외 4지점 중 1 |
| `server/orchestrator/ports.py` | 조건부 수정 | `StateQueryPort`와 동형인 프로퍼티 조회 포트 추가. 현재 포트는 `query_state(path) -> dict`만 정의한다 `[코드]` `server/orchestrator/ports.py:68-73`. | `server/safety/**` 자체는 아니지만 초크포인트 예외 세트의 포트 계약 지점 |
| `server/safety/gate.py` | 조건부 수정 | `_GateStatePort`에 위임 메서드 추가. 현재 `_GateStatePort.query_state`는 게이트 내부 `_query_state`로 위임한다 `[코드]` `server/safety/gate.py:114-121`. | `server/safety/**` PRESERVE의 승인 대기 예외 4지점 중 2 |
| `server/measurement/mock_provider.py` | 조건부 수정 | 오프라인 대역에 프로퍼티 조회 동형 추가. 현재 대역은 `query_state`만 제공한다 `[코드]` `server/measurement/mock_provider.py:113-128`. | 테스트·측정 대역 순수 추가 |
| `server/tests/test_prechk_inventory.py` | 신규 | `AC-PRECHK-001`, `AC-PRECHK-002`, `AC-PRECHK-003`, `AC-PRECHK-004`, `AC-PRECHK-013`의 인메모리 검증. | 신규 테스트라 침범 0건 |
| `server/tests/test_prechk_patch.py` | 신규 | `AC-PRECHK-005`, `AC-PRECHK-006`, `AC-PRECHK-007`, `AC-PRECHK-008`, `AC-PRECHK-009` 검증. | 신규 테스트라 침범 0건 |
| `server/tests/test_prechk_macro.py` | 신규 | `AC-PRECHK-010`, `AC-PRECHK-011` 검증. | 신규 테스트라 침범 0건 |
| `server/tests/test_prechk_report.py` | 신규 | `AC-PRECHK-012` 검증. | 신규 테스트라 침범 0건 |
| `server/tests/test_prechk_tool.py` | 신규 | `AC-PRECHK-014` 검증. | 신규 테스트라 침범 0건 |

테스트 파일명은 `acceptance.md`의 검증 방법 필드가 지목한 이름 그대로다.

### §2.2 `server/prechk/` 모듈 구성

`server/prechk/`는 순수 판정 계층이다. 포트 인터페이스를 받아 읽고, 정규화하고, 보고 페이로드를 만든다. `server.bridge`를 직접 import하지 않는다. 그 경계는 아키텍처 테스트가 `server/bridge/` · `server/safety/` · `server/tests/`만 OSC 송신 표면 import 허용 대상으로 둔다 `[코드]` `server/tests/test_architecture.py:26-39`, 위반 시 단일 초크포인트 위반 메시지로 실패한다 `[코드]` `server/tests/test_architecture.py:48-61`.

| 모듈 | 공개 표면 | 내부 책임 |
|---|---|---|
| `inventory.py` | `read_inventory(port, policy)` | 루트 열거, 프로퍼티 판독, 형태 검증, 보강 판독 기록, completeness 산정 |
| `patch.py` | `evaluate_patch(inventory, footprint_policy)` | 주소 파싱, 중복 그룹화, 조건부 구간 겹침, 판독 실패 별도 부류 유지 |
| `macro.py` | `build_response_check_macro(groups, macro_policy)` | 그룹 대상만 선택, M0 리터럴 외 문법 발화 0건, 그룹 부재 시 답변인 실패 생성 |
| `report.py` | `build_report(result)` · `to_korean(report)` | 닫힌 판정 어휘를 한국어로 표현하고 집계와 픽스처별 산술을 맞춘다 |

`server/looks/report.py`의 한국어 라벨 접근자 패턴을 재사용한다. 해당 파일은 라벨 표를 코드 표현 계층에 두고 공개 접근자로 알 수 없는 코드를 그대로 통과시킨다 `[코드]` `server/looks/report.py:61-88`.

### §2.3 `server/orchestrator/tools.py` 신규 툴 등재 4지점

신규 툴 이름은 `run_precheck`로 둔다. 등재는 4지점 모두 필요하다.

| 지점 | 현재 형상 | PRECHK 변경 | 누락 시 죽는 AC |
|---|---|---|---|
| `TOOL_NAMES` | 닫힌 튜플에 모델 도달 툴 이름이 들어 있다 `[코드]` `server/orchestrator/tools.py:53-62`. | `"run_precheck"` 1항 추가 | `AC-PRECHK-014` |
| 핸들러 클로저 | 기존 복합 툴은 `build_toolset` 내부 핸들러가 리그를 읽고 `run_commands`를 재호출한다 `[코드]` `server/orchestrator/tools.py:974-1202`. | `run_precheck(call, context)` 추가 | `AC-PRECHK-014` |
| `definitions` | 모델에 전달되는 `ToolDefinition` 튜플이다 `[코드]` `server/orchestrator/tools.py:1204-1552`. | 매개변수 스키마를 최소화한 `ToolDefinition` 추가 | `AC-PRECHK-014` |
| `handlers` | 이름에서 핸들러로 이어지는 맵이다 `[코드]` `server/orchestrator/tools.py:1553-1562`. | `"run_precheck": run_precheck` 추가 | `AC-PRECHK-014` |

툴 핸들러는 `execution_port`를 직접 호출하지 않는다. 기존 `run_commands`가 `bundle_gate.screen()`을 먼저 거친 뒤 `execution_port.execute`를 호출한다 `[코드]` `server/orchestrator/tools.py:496-535`, `server/orchestrator/tools.py:571-582`. PRECHK 매크로 생성도 이 클로저를 재호출하는 호출자여야 한다.

### §2.4 승인 대기인 초크포인트 4지점

`server/safety/**` 조건부 예외는 승인 전 미착수다. 승인되면 다음 4지점만 순수 추가한다.

| 지점 | 추가 | 근거 |
|---|---|---|
| `server/safety/console.py` | `query_property(path, property_name) -> dict` | 현재 콘솔 포트가 게이트 소유 I/O이고 `server.bridge.protocol` import를 이미 갖는다 `[코드]` `server/safety/console.py:1-12`, `server/safety/console.py:23-31`. `build_prop_query`는 공백 프로퍼티명을 거부한다 `[코드]` `server/bridge/protocol.py:136-142`. |
| `server/orchestrator/ports.py` | `PropertyQueryPort` 또는 `StateQueryPort`의 비파괴 확장 | 현재 오케스트레이터 포트는 브리지 직접 호출 금지를 독스트링으로 고정한다 `[코드]` `server/orchestrator/ports.py:1-13`. |
| `server/safety/gate.py` | 게이트 소유 포트 위임 | 현재 `state_port`는 게이트 내부 위임 객체로 노출된다 `[코드]` `server/safety/gate.py:168-181`. |
| `server/measurement/mock_provider.py` | 오프라인 콘솔 대역의 `query_property` | 현재 대역이 콘솔 전송 없이 `execute`, `ping`, `query_state`, `deploy_plugin`을 제공한다 `[코드]` `server/measurement/mock_provider.py:113-128`. |

### §2.5 PRESERVE 침범 0건 표

| PRESERVE 항목 | 설계 방침 | 침범 |
|---|---|---|
| `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` | 읽지 않거나 공개 API만 소비한다. | 0건 |
| `server/looks/library/` | 룩 자산을 변경하지 않는다. | 0건 |
| `server/web/preview.py` | 웹 미리보기는 본 SPEC 산출물이 아니다. | 0건 |
| `console/lua/**` | 현재 `state`와 `prop` 표면을 소비한다. 응답기 확장 없음. | 0건 |
| `server/rulebook/assets/v2.4.2/**` | M0가 실측한 매크로 리터럴만 소비한다. 룰북 편집 없음. | 0건 |
| `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS` | `server/orchestrator/tools.py:247-251` 무변경. | 0건 |
| `server/orchestrator/tools.py`의 실행/dedupe 루프 | `server/orchestrator/tools.py:536-582` 무변경. | 0건 |
| `server/safety/**` | 승인된 조건부 예외 4지점 외 hunk 0건. 승인 전 hunk 0건. | 0건 |

---

## §3. 흐름

```
열거 -> 프로퍼티 판독 -> 형태검증 -> 정규화 -> 판정 -> 리포트
```

1. **열거.** `read_inventory`는 `Patch/Stages/1/Fixtures`를 `state` 경로로 읽는다. 응답기 스냅샷은 `node.childCount`에 참 전체 수를 넣고 `children`에는 잘릴 수 있는 목록을 넣는다 `[코드]` `console/lua/copilot_responder.lua:579-611`. `children` 길이가 `node.childCount`보다 작으면 이 시점에 completeness를 `incomplete`로 둔다.
2. **절단 개입.** 절단은 두 지점에서 생긴다. 첫째, `max_children`는 24다 `[코드]` `console/lua/copilot_responder.lua:31-39`, `console/lua/copilot_responder.lua:579-611`. 둘째, 페이로드가 예산을 넘으면 뒤 항목을 제거하고 `truncated`를 참으로 바꾼다 `[코드]` `console/lua/copilot_responder.lua:634-639`. 설계는 `truncated`만 믿지 않고 `node.childCount`와 읽은 개수를 비교한다.
3. **보강 판독.** 루트 열거가 절단되면 `Patch/Stages/1/Fixtures/<slot>` 단일 노드 조회를 보강으로 수행한다. 경계는 `1..node.childCount`다. 이 경계는 확인된 하한 보강일 뿐이며, 인덱스 정의역을 모르는 문제 때문에 루트가 절단된 실행을 `complete`로 승격하지 않는다. 리포트에는 `recovery_boundary`, `recovered_slots`, `still_unobserved_count`, `index_domain_unknown`을 싣는다.
4. **프로퍼티 판독.** 각 관측 슬롯에 대해 `Patch`, `FixtureType`, `Mode`, `Name`만 요청한다. 프로퍼티명 열거 API가 없고 `safe_property`는 호출자가 준 이름만 조회한다 `[코드]` `console/lua/copilot_responder.lua:204-217`. 공백 포함 이름은 클라이언트 프로토콜에서 거부된다 `[코드]` `server/bridge/protocol.py:136-142`.
5. **판독 실패 전파.** `prop`의 `ok=true`는 값 유효성을 보장하지 않는다. 응답기 `safe_property`는 `handle:Get(name)` 실패 뒤 `handle[name]` 값을 문자열화한다 `[코드]` `console/lua/copilot_responder.lua:208-215`. 기대 형태를 만족하지 않는 값, `None` 문자열, 함수 참조 문자열은 `ReadFailure`가 되고 이후 정규화와 판정에는 들어가지 않는다. 리포트는 실패 사유와 원문 값을 보존한다.
6. **정규화.** `Patch` 원문은 유니버스 정수와 주소 정수로 바꾼다. 파싱 실패는 기본값으로 채우지 않고 `ReadFailure`로 전파한다. `FixtureType`과 `Mode`는 표시 문자열이므로 경로 인덱스로 파싱하지 않는다. `ASSUMPTION-27`이 GO로 판정될 때만 별도 연결 경로를 통해 점유폭을 얻는다.
7. **판정.** 주소 중복은 항상 수행한다. 구간 겹침은 `ASSUMPTION-27` GO에서만 수행하고, 부정이면 `skipped_checks`에 축소 사유를 남긴다. 판독 실패 픽스처는 정합으로도 부적합으로도 세지 않는다.
8. **매크로.** `ASSUMPTION-26` GO에서만 M0가 실측한 리터럴로 매크로 커맨드를 만든다. 대상은 그룹뿐이다. 그룹이 없으면 매크로를 만들지 않고 `is_error=False` 답변으로 사유를 돌려준다.
9. **리포트.** 리포트는 집계와 픽스처별 목록을 함께 싣는다. 완전성 3수치, 충돌 부류, 판독 실패, 미수행 판정, FID 미확정 표시가 모두 구조화된다. 사용자 대면 문자열은 한국어이며 코드 표현 계층에서 만든다.

---

## §4. 위험 검토

| 위험 | 흡수 설계 | 고정 AC |
|---|---|---|
| `research.md` §4.3 T-1: `ok=true`인데 Lua 함수 참조가 값으로 온다. | 프로퍼티별 형태 검증기를 통과한 값만 채택한다. 함수 참조와 `None` 문자열은 판독 실패다. | `AC-PRECHK-002`, `AC-PRECHK-008`, `AC-PRECHK-012` |
| `research.md` §4.3 T-2: 공백 포함 프로퍼티명은 조회 불가다. | 화이트리스트는 `Patch`, `FixtureType`, `Mode`, `Name` 네 이름으로 닫고 공백형 후보를 코드에 두지 않는다. | `AC-PRECHK-001` |
| `research.md` §4.3 T-3: 프로퍼티명을 열거할 수 없다. | 목록 밖 이름을 추측 발화하지 않는다. 새로운 프로퍼티 필요가 생기면 M0 측정이나 별도 SPEC으로 넘긴다. | `AC-PRECHK-001`, `AC-PRECHK-002` |
| `research.md` §4.4와 §4.7: 절단이 기본 경로이고 payload 예산도 절단을 만든다. | completeness는 `node.childCount`와 읽은 개수 비교로 산정한다. 보강 조회를 해도 루트 절단 실행은 완전으로 승격하지 않는다. | `AC-PRECHK-003`, `AC-PRECHK-009`, `AC-PRECHK-017` |
| `research.md` §4.6: 현재 쇼파일은 슬롯과 FID가 같아 FID 의미를 증명할 수 없다. | 판정 키는 슬롯과 이름이다. FID는 정합성 근거가 아니며 `Fixture <n>` 커맨드는 생성하지 않는다. | `AC-PRECHK-004`, `AC-PRECHK-011` |
| `research.md` §7.4: 프로퍼티 조회는 프로덕션 경로로 도달할 수 없고 경로는 PRESERVE다. | 승인된 초크포인트 4지점만 순수 추가한다. 승인 전 M1 미착수이며 `server.bridge` 우회와 `server/tools/` 예외 증설은 금지한다. | `AC-PRECHK-013`, `AC-PRECHK-015` |
| `ASSUMPTION-26` 부정: 매크로 저작 문법이 없다. | 매크로 대상 커맨드 0건, `DESCOPE:` 접두 기록, 패치 정합성 판정은 계속 수행한다. | `AC-PRECHK-010`, `AC-PRECHK-016` |
| `ASSUMPTION-27` 부정: 점유폭 연결이 없다. | 구간 겹침만 미수행으로 보고하고 주소 중복은 수행한다. | `AC-PRECHK-007`, `AC-PRECHK-012`, `AC-PRECHK-016` |

위험의 공통 처리 원칙은 하나다. 읽기 실패, 절단, 미수행, 부정 전제는 모두 **정상 페이로드의 구조화된 부류**이며 예외 산문으로만 흘리지 않는다.

---

## §5. 설계 슬롯

열린 슬롯은 0건이다. 아래 결정은 run-phase 재량이 아니라 이 문서의 설계 계약이다.

| 슬롯 | 결정 | 기각한 대안 | 연결 토큰 |
|---|---|---|---|
| A. 절단 복구 전략 | 루트 열거가 절단되면 `1..node.childCount` 슬롯별 단일 조회를 보강으로 수행한다. 보강은 상세를 늘리는 장치이고, 인덱스 정의역을 모르므로 completeness를 `complete`로 승격하지 않는다. | `truncated=false`를 믿는 대안, 절단 목록만으로 정상 판정을 내리는 대안, 무한 슬롯 탐색으로 완전성을 주장하는 대안. | `REQ-PRECHK-004`, `REQ-PRECHK-010`, `AC-PRECHK-003`, `AC-PRECHK-009` |
| B. 값 형태 검증기 | `server/prechk/inventory.py`에 프로퍼티별 기대 형태 테이블을 둔다. `Patch`는 주소 파서, `Name`·`FixtureType`·`Mode`는 비어 있지 않고 함수 참조나 `None` 문자열이 아닌 표시 문자열 검증을 갖는다. | `ok=true`만 믿는 대안, 보고 계층에서 문자열을 다시 해석하는 대안, 테스트 픽스처에만 검증 규칙을 두는 대안. | `REQ-PRECHK-003`, `REQ-PRECHK-006`, `AC-PRECHK-002`, `AC-PRECHK-005` |
| C. 판정 부류의 닫힌 집합 | 코드 상수로 `completeness = {complete, incomplete}`, `fixture_verdict = {observed_clear, collision, read_failed, not_assessed}`, `collision_kind = {address_duplicate, range_overlap}`, `read_failure_kind = {property_unreadable, shape_invalid, address_parse_failed, type_mode_unresolved}`, `skipped_check_kind = {range_overlap_descope, macro_descope, macro_no_groups, gate_unapproved}`를 둔다. | 자유 문자열 사유만 반환하는 대안, 충돌과 판독 실패를 한 카운터에 합치는 대안, 리포트에서만 한국어 라벨로 판정을 저장하는 대안. | `REQ-PRECHK-009`, `REQ-PRECHK-015`, `REQ-PRECHK-016`, `AC-PRECHK-008`, `AC-PRECHK-012` |
| D. 매크로 대상 선택 | 매크로는 리그가 이미 정의한 그룹만 대상으로 한다. 그룹의 `no`가 없거나 그룹 풀이 없으면 매크로를 생성하지 않고 사유로 답한다. `Fixture <n>`은 0건이다. | 슬롯을 FID로 보고 픽스처를 직접 선택하는 대안, 새 그룹을 만들어 우회하는 대안, 그룹이 없을 때 임의 전체 선택을 발화하는 대안. | `REQ-PRECHK-011`, `REQ-PRECHK-012`, `REQ-PRECHK-013`, `REQ-PRECHK-014`, `AC-PRECHK-010`, `AC-PRECHK-011` |
| E. 리포트 페이로드 스키마 | `inventory`, `fixtures`, `collisions`, `read_failures`, `skipped_checks`, `macro`, `summary_ko`를 최상위 키로 둔다. 집계와 픽스처별 목록의 산술은 코드에서 한 번 계산하고 테스트가 합계를 대조한다. | 집계만 반환하는 대안, 사용자 문자열만 반환하는 대안, 툴 결과에 응답 여부 단언 필드를 넣는 대안. | `REQ-PRECHK-015`, `REQ-PRECHK-016`, `REQ-PRECHK-017`, `AC-PRECHK-012`, `AC-PRECHK-014` |

### §5.1 리포트 페이로드 스키마

스키마의 의미는 다음과 같다. 구현은 dataclass와 `to_dict()`를 써도 되지만, 키와 닫힌 어휘는 이 표를 따른다.

| 키 | 값 | 필수성 |
|---|---|---|
| `inventory` | `{path, child_count, observed_count, recovered_count, missing_count, completeness, recovery_boundary, index_domain_unknown}` | 항상 |
| `fixtures` | 각 항목 `{slot, name, patch_raw, universe, address, fixture_type, mode, fid_note, verdict, reasons}` | 관측 픽스처 전량 |
| `collisions` | `{address_duplicates, range_overlaps}`이며 각 충돌은 관여 픽스처 전량을 슬롯과 이름으로 싣는다. | 항상, 비어 있어도 포함 |
| `read_failures` | `{slot, name, property, raw_value, kind, detail}` 목록 | 항상, 비어 있어도 포함 |
| `skipped_checks` | `{kind, reason, assumption}` 목록 | 미수행 축이 있으면 포함 |
| `macro` | `{created, target_kind, targets, commands, requires_human_visual_confirmation, reason}` | 매크로 요청 시 |
| `summary_ko` | 한국어 요약 문자열 | 항상 |

`fid_note`는 값이 있을 때도 `미확정`을 표시한다. 이 필드는 판정 입력이 아니다.

---

## §6. 테스트 설계

### §6.1 인메모리 픽스처

정합 리그만으로는 탐지 로직이 참임을 보일 수 없다. `research.md` §4.5가 실측 리그에 결함이 없음을 기록하므로 결함을 심은 인메모리 픽스처가 필수다.

| 픽스처 이름 | 심은 사실 | 죽이는 결함 | 관련 AC |
|---|---|---|---|
| `clean_rig_18` | 실측 리그와 같은 정합 주소, FID 중복 없음, 절단 없음 | 오탐 | `AC-PRECHK-006`, `AC-PRECHK-009`, `AC-PRECHK-012` |
| `slot_not_fid` | 슬롯 1, FID 101 | 슬롯을 FID로 쓰는 구현 | `AC-PRECHK-004`, `AC-PRECHK-011` |
| `duplicate_address_pair` | 서로 다른 슬롯 2개가 `1.001` | 주소 중복 미탐 | `AC-PRECHK-006` |
| `duplicate_address_triple` | 서로 다른 슬롯 3개가 `1.001` | 쌍 단위 과다 카운트 | `AC-PRECHK-006` |
| `same_address_other_universe` | `1.001`과 `2.001` | 유니버스 무시 | `AC-PRECHK-006` |
| `truncated_parent` | `node.childCount = 40`, `children = 18`, `truncated = true` | 절단 미보고 | `AC-PRECHK-003`, `AC-PRECHK-009` |
| `truncated_flag_false` | `node.childCount > len(children)`, `truncated = false` | 플래그만 신뢰 | `AC-PRECHK-003` |
| `function_ref_property` | `ok=true`, 값 `function: 0x105b0f048` | 형태 검증 부재 | `AC-PRECHK-002` |
| `none_string_property` | `ok=true`, 값 `None` | 문자열 부재값 채택 | `AC-PRECHK-002` |
| `bad_patch_value` | `Patch` 값이 빈 문자열, `abc`, `1`, `1.2.3` | 기본값 대입 | `AC-PRECHK-005`, `AC-PRECHK-008` |
| `range_overlap_go` | 주소 1, 점유폭 29와 주소 15 | 구간 겹침 미탐 | `AC-PRECHK-007` |
| `range_descope` | `ASSUMPTION-27` 부정 상태 | 미수행 축 누락 | `AC-PRECHK-007`, `AC-PRECHK-012` |
| `groups_present` | 번호 있는 그룹 2개 이상 | 매크로 그룹 대상 생성 | `AC-PRECHK-010`, `AC-PRECHK-011` |
| `groups_empty` | 그룹 0개 | 대체 대상 발명 금지 | `AC-PRECHK-011` |
| `gate_unapproved` | 초크포인트 승인 기록 없음 | M1 미착수 | `AC-PRECHK-013` |

### §6.2 AC별 검증 파일

| AC | 검증 파일 | 핵심 픽스처 |
|---|---|---|
| `AC-PRECHK-001` | `server/tests/test_prechk_inventory.py` | `clean_rig_18`, 금지 경로 주입 |
| `AC-PRECHK-002` | `server/tests/test_prechk_inventory.py` | `function_ref_property`, `none_string_property` |
| `AC-PRECHK-003` | `server/tests/test_prechk_inventory.py` | `truncated_parent`, `truncated_flag_false` |
| `AC-PRECHK-004` | `server/tests/test_prechk_inventory.py` | `slot_not_fid`, `bad_patch_value` |
| `AC-PRECHK-005` | `server/tests/test_prechk_patch.py` | `clean_rig_18`, `bad_patch_value` |
| `AC-PRECHK-006` | `server/tests/test_prechk_patch.py` | `duplicate_address_pair`, `duplicate_address_triple`, `same_address_other_universe` |
| `AC-PRECHK-007` | `server/tests/test_prechk_patch.py` | `range_overlap_go`, `range_descope` |
| `AC-PRECHK-008` | `server/tests/test_prechk_patch.py` | `bad_patch_value`, `function_ref_property` |
| `AC-PRECHK-009` | `server/tests/test_prechk_patch.py` | `truncated_parent`, `clean_rig_18` |
| `AC-PRECHK-010` | `server/tests/test_prechk_macro.py` | `groups_present`, `ASSUMPTION-26` 부정 상태 |
| `AC-PRECHK-011` | `server/tests/test_prechk_macro.py` | `slot_not_fid`, `groups_empty` |
| `AC-PRECHK-012` | `server/tests/test_prechk_report.py` | 모든 결함 픽스처의 합성 리포트 |
| `AC-PRECHK-013` | `server/tests/test_architecture.py`, `server/tests/test_prechk_inventory.py` | `gate_unapproved` |
| `AC-PRECHK-014` | `server/tests/test_prechk_tool.py` | 툴 디스패치 픽스처 |
| `AC-PRECHK-015` | 기존 전체 스위트와 diff 게이트 | PRESERVE diff 비공허성 주입 |
| `AC-PRECHK-016` | 라이브 세션 | M0 프로브 기록 |
| `AC-PRECHK-017` | 라이브 세션 | 툴 종단 실행과 감사 로그 대조 |

### §6.3 마일스톤별 뮤테이션 제안

| 마일스톤 | 주입할 결함 | 죽어야 하는 AC |
|---|---|---|
| M0 | 매크로 저작 GO를 재조회 없이 기록한다. | `AC-PRECHK-016` |
| M0 | 부정 판정에서 `DESCOPE:` 접두 행을 빼고 산문만 남긴다. | `AC-PRECHK-016`, `AC-PRECHK-010`, `AC-PRECHK-007` |
| M1 | `server/prechk/`에서 `server.bridge`를 import한다. | `AC-PRECHK-013` |
| M1 | `_NAMED_TOOL_EXEMPTIONS`에 PRECHK 파일을 추가한다. | `AC-PRECHK-013`, `AC-PRECHK-015` |
| M1 | 기존 `query_state` 시그니처를 바꾼다. | `AC-PRECHK-013` |
| M2 | 열거 경로를 `Patch/Fixtures`로 바꾼다. | `AC-PRECHK-001` |
| M2 | 프로퍼티 후보에 `Address` 또는 공백 포함 이름을 추가한다. | `AC-PRECHK-001` |
| M2 | 함수 참조 문자열을 정상 값으로 채택한다. | `AC-PRECHK-002` |
| M2 | `None` 문자열을 정상 값으로 채택한다. | `AC-PRECHK-002` |
| M2 | completeness를 `truncated` 플래그로만 판단한다. | `AC-PRECHK-003` |
| M2 | `Fixture <slot>` 커맨드를 생성한다. | `AC-PRECHK-004`, `AC-PRECHK-011` |
| M2 | 생성 조회 목록을 빈 배열로 만들어 0건 스캔을 공허하게 통과시킨다. | `AC-PRECHK-001`, `AC-PRECHK-004` |
| M3 | 주소를 문자열로 비교한다. | `AC-PRECHK-005` |
| M3 | 파싱 실패 주소를 0이나 1로 채운다. | `AC-PRECHK-005`, `AC-PRECHK-008` |
| M3 | 3개 중복을 쌍 3건으로 센다. | `AC-PRECHK-006` |
| M3 | 유니버스를 무시하고 주소 숫자만 비교한다. | `AC-PRECHK-006` |
| M3 | `ASSUMPTION-27` 부정 상태에서도 구간 겹침 판정을 수행한다. | `AC-PRECHK-007` |
| M3 | 판독 실패 픽스처를 정합으로 센다. | `AC-PRECHK-008`, `AC-PRECHK-012` |
| M3 | 불완전 입력에서 한정 없는 정합 판정을 출력한다. | `AC-PRECHK-009` |
| M4 | 매크로 대상에 `Fixture <n>`을 쓴다. | `AC-PRECHK-011` |
| M4 | 그룹이 없을 때 임의 대체 대상을 발명한다. | `AC-PRECHK-011` |
| M4 | 매크로 실행 결과에 `responded` 계열 필드를 넣는다. | `AC-PRECHK-011` |
| M4 | `ASSUMPTION-26` 부정 상태에서 매크로 커맨드를 생성한다. | `AC-PRECHK-010` |
| M5 | 집계만 반환하고 픽스처별 목록을 생략한다. | `AC-PRECHK-012` |
| M5 | 집계 수치와 픽스처별 합을 어긋나게 둔다. | `AC-PRECHK-012` |
| M5 | 한국어 라벨을 밑줄 식별자 직접 import로 가져온다. | `AC-PRECHK-012` |
| M6 | `TOOL_NAMES`에 툴을 넣지 않는다. | `AC-PRECHK-014` |
| M6 | 핸들러에서 `execution_port`를 직접 호출한다. | `AC-PRECHK-014` |
| M6 | 신규 REST 라우트나 웹소켓 메시지를 만든다. | `AC-PRECHK-014` |
| M6 | 툴 스키마에 그룹·풀·슬롯·픽스처·주소 인자를 받게 한다. | `AC-PRECHK-014` |
| M7 | PRESERVE diff를 `<BASE>..HEAD` 없이 검사한다. | `AC-PRECHK-015` |
| M7 | `console/lua/**`를 수정한다. | `AC-PRECHK-015` |
| M7 | 게이트 비공허성 주입을 생략한다. | `AC-PRECHK-015` |
| M8 | 툴을 거치지 않고 빌더를 직접 실행해 종단 검증한다. | `AC-PRECHK-017` |
| M8 | 감사 로그 대조 없이 툴 반환만으로 검증한다. | `AC-PRECHK-017` |

제안 뮤테이션은 총 35개다.

---

## §7. 안티패턴

| 안티패턴 | 왜 금지인가 | 걸리는 토큰 |
|---|---|---|
| `Patch/Fixtures`나 `DataPool/Presets`를 재시도한다. | 죽은 경로를 다시 탐색하는 것이다. | `REQ-PRECHK-002`, `AC-PRECHK-001` |
| `state` 결과의 `children` 위치를 슬롯이나 FID로 본다. | 슬롯과 FID를 혼동하고 절단 시 더 틀어진다. | `REQ-PRECHK-005`, `AC-PRECHK-004` |
| `ok=true`면 값을 곧바로 채택한다. | 함수 참조와 `None` 문자열이 정상 값으로 섞인다. | `REQ-PRECHK-003`, `AC-PRECHK-002` |
| `FixtureType 1` 같은 표시 문자열에서 인덱스를 뽑는다. | 표시 이름에서 정체성을 끌어내는 형태다. | `REQ-PRECHK-008`, `AC-PRECHK-007` |
| 절단된 목록에서 충돌 0건을 전체 정합으로 말한다. | 불완전 집합에 대한 단정이다. | `REQ-PRECHK-004`, `REQ-PRECHK-010`, `AC-PRECHK-009` |
| `server/prechk/`가 `server.bridge`를 직접 import한다. | 단일 초크포인트 경계를 우회한다. | `REQ-PRECHK-019`, `AC-PRECHK-013` |
| `server/tools/` 예외를 늘려 프로퍼티 조회를 넣는다. | 운영 유틸 예외를 기능 경로로 위장한다. | `REQ-PRECHK-020`, `AC-PRECHK-013` |
| 매크로에서 `Fixture <n>`을 쓴다. | 슬롯을 FID로 오인하는 경로다. | `REQ-PRECHK-013`, `AC-PRECHK-011` |
| 매크로 실행 성공을 픽스처 응답 증거로 보고한다. | `exec` 성공은 커맨드 접수 결과일 뿐 하드웨어 피드백이 아니다. | `REQ-PRECHK-014`, `AC-PRECHK-011` |
| 매크로 그룹이 없을 때 새 그룹을 만든다. | 패치 수정과 그룹 저작은 본 SPEC 산출물이 아니다. | `REQ-PRECHK-011`, `REQ-PRECHK-013`, `AC-PRECHK-011` |
| 툴 테스트가 빌더를 직접 호출한다. | `TOOL_NAMES`, `definitions`, `handlers` 중 누락을 못 본다. | `AC-PRECHK-014` |
| 리포트를 자유 산문으로만 반환한다. | 산술 정합과 닫힌 판정 어휘를 검증할 수 없다. | `REQ-PRECHK-015`, `REQ-PRECHK-016`, `AC-PRECHK-012` |

---

## §8. 교차 참조

### §8.1 REQ 대응

| 토큰 | 설계 위치 | 주요 AC |
|---|---|---|
| `REQ-PRECHK-001` | §3 열거와 프로퍼티 판독 | `AC-PRECHK-001` |
| `REQ-PRECHK-002` | §1 제외, §7 안티패턴 | `AC-PRECHK-001` |
| `REQ-PRECHK-003` | §3 판독 실패 전파, §5 슬롯 B | `AC-PRECHK-002` |
| `REQ-PRECHK-004` | §3 절단 개입, §5 슬롯 A | `AC-PRECHK-003` |
| `REQ-PRECHK-005` | §4 FID 위험, §5 슬롯 D | `AC-PRECHK-004` |
| `REQ-PRECHK-006` | §3 정규화, §5 슬롯 B | `AC-PRECHK-005` |
| `REQ-PRECHK-007` | §3 판정 | `AC-PRECHK-006` |
| `REQ-PRECHK-008` | §3 판정, §4 `ASSUMPTION-27` 위험 | `AC-PRECHK-007` |
| `REQ-PRECHK-009` | §3 판정, §5 슬롯 C | `AC-PRECHK-008` |
| `REQ-PRECHK-010` | §3 리포트, §5 슬롯 A | `AC-PRECHK-009` |
| `REQ-PRECHK-011` | §3 매크로, §5 슬롯 D | `AC-PRECHK-010` |
| `REQ-PRECHK-012` | §4 `ASSUMPTION-26` 위험 | `AC-PRECHK-010` |
| `REQ-PRECHK-013` | §5 슬롯 D, §7 안티패턴 | `AC-PRECHK-011` |
| `REQ-PRECHK-014` | §1 제외, §3 매크로 | `AC-PRECHK-011` |
| `REQ-PRECHK-015` | §5 슬롯 E | `AC-PRECHK-012` |
| `REQ-PRECHK-016` | §5 슬롯 C, §5 슬롯 E | `AC-PRECHK-012` |
| `REQ-PRECHK-017` | §2.2, §5 슬롯 E | `AC-PRECHK-012` |
| `REQ-PRECHK-018` | §2.3 툴 등재 | `AC-PRECHK-014` |
| `REQ-PRECHK-019` | §2.4 초크포인트 | `AC-PRECHK-013` |
| `REQ-PRECHK-020` | §2.4 초크포인트, §7 안티패턴 | `AC-PRECHK-013` |

### §8.2 AC와 마일스톤 대응

| 마일스톤 | AC | 설계 검증 초점 |
|---|---|---|
| M0 | `AC-PRECHK-016` | `ASSUMPTION-25`, `ASSUMPTION-26`, `ASSUMPTION-27`, `ASSUMPTION-28`, `ASSUMPTION-29`, `ASSUMPTION-30` 판정 확정 |
| M1 | `AC-PRECHK-013` | 초크포인트 승인, `server.bridge` import 0건, 유틸 예외 증설 0건 |
| M2 | `AC-PRECHK-001`, `AC-PRECHK-002`, `AC-PRECHK-003`, `AC-PRECHK-004` | 인벤토리 읽기, 형태 검증, 완전성, FID 금지 |
| M3 | `AC-PRECHK-005`, `AC-PRECHK-006`, `AC-PRECHK-007`, `AC-PRECHK-008`, `AC-PRECHK-009` | 주소 정규화, 중복, 조건부 겹침, 판독 실패 분리, 불완전 단정 금지 |
| M4 | `AC-PRECHK-010`, `AC-PRECHK-011` | 매크로 GO/DESCOPE, 그룹 대상, 응답 증거 단언 금지 |
| M5 | `AC-PRECHK-012` | 2단 리포트, 산술 정합, 한국어 표현 |
| M6 | `AC-PRECHK-014` | 툴 등록 4지점과 단일 실행 경로 |
| M7 | `AC-PRECHK-015` | PRESERVE diff, 회귀, 비공허성 게이트 |
| M8 | `AC-PRECHK-017` | 툴을 통한 종단 라이브, 감사 로그 대조 |

### §8.3 ASSUMPTION 대응

| 토큰 | 설계 결정 |
|---|---|
| `ASSUMPTION-25` | M0는 주소 읽기를 재확인한다. 설계는 `Patch` 프로퍼티가 GO로 유지될 때의 경로를 쓴다. |
| `ASSUMPTION-26` | 매크로 저작의 유일한 블로킹 전제다. 부정이면 매크로 대상 커맨드 0건이다. |
| `ASSUMPTION-27` | 구간 겹침의 동작 축소 전제다. 부정이어도 주소 중복과 리포트는 남는다. |
| `ASSUMPTION-28` | 본 SPEC 산출물이 아니라 같은 라이브 세션에서 닫는 BUSKWIZ 후속 측정이다. |
| `ASSUMPTION-29` | `ASSUMPTION-28` 조건부 후속 측정이다. |
| `ASSUMPTION-30` | `ASSUMPTION-28` 조건부 후속 측정이다. |

열린 설계 슬롯은 0건이다.
