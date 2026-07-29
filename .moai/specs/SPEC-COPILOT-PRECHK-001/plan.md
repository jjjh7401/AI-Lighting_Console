# SPEC-COPILOT-PRECHK-001 — 구현 계획 (plan)

status: draft (v0.1.0, 2026-07-29) · Tier L

> **v0.1.0 — 최초 작성.** 마일스톤 **M0~M8**, 결정 등록부 **7건(A~G)**, 열린 결정 **0건**. 본 계획은 닫힌 정본 3종의 토큰 계약을 따른다: REQ 20건, AC 17건, ASSUMPTION 6건, 라이브 세션 2회. 마일스톤별 `- **AC**:` 줄은 `acceptance.md §C.0a`와 1:1이며, 합 **17 · 중복 0 · 누락 0**이다.
>
> **참조 규약.** 본 SPEC의 정본 3종은 줄번호로 인용하지 않고 `REQ-PRECHK-001`, `AC-PRECHK-001`, `ASSUMPTION-25` 같은 안정 토큰과 절 제목으로만 참조한다. 코드·룰북·응답기 프로토콜·타 SPEC 아티팩트는 `파일:줄` 좌표를 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓰며, clarification 마커는 0건이다.

---

## §A. 맥락과 우선순위

본 절은 **무엇을 먼저 검토해야 하는가**를 적는다. 구현 순서(§B)는 M0부터 M8까지 선형이지만, 위험 순서는 다르다. 가장 큰 위험은 라이브 전제가 아니라 **승인 대기**다.

### §A.1 우선순위 매핑 — 제안서 P2-6과 사용자 재범위 확정의 반영

제안서 P2-6은 "픽스처 응답 확인 매크로 생성 + 결과 리포트(주소 불일치·무응답 픽스처 탐지)"를 요구했다(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:102-105`). 착수 전 조사는 그중 **무응답 픽스처 자동 탐지**의 관측 경로가 없음을 닫았고, 사용자는 범위를 다음처럼 재확정했다.

| 우선순위 | 항목 | 계획 반영 |
|---|---|---|
| 1 | **패치 메타데이터 점검** | 픽스처 인벤토리 읽기, 주소 정규화, 주소 중복, 조건부 구간 겹침, 판독 실패 분리. `REQ-PRECHK-001`, `REQ-PRECHK-002`, `REQ-PRECHK-003`, `REQ-PRECHK-004`, `REQ-PRECHK-005`, `REQ-PRECHK-006`, `REQ-PRECHK-007`, `REQ-PRECHK-008`, `REQ-PRECHK-009`, `REQ-PRECHK-010` |
| 2 | **사람이 눈으로 확인할 응답 확인 매크로** | 매크로는 판정기가 아니라 관측 보조다. 하드웨어 응답 여부를 주장하지 않는다. `REQ-PRECHK-011`, `REQ-PRECHK-012`, `REQ-PRECHK-013`, `REQ-PRECHK-014` |
| 3 | **결과 리포트와 툴 표면** | 집계 + 픽스처별 2단, 한국어 표현, 단일 실행 경로. `REQ-PRECHK-015`, `REQ-PRECHK-016`, `REQ-PRECHK-017`, `REQ-PRECHK-018`, `REQ-PRECHK-019`, `REQ-PRECHK-020` |
| 4 | **BUSKWIZ 후속 측정** | `ASSUMPTION-28`, `ASSUMPTION-29`, `ASSUMPTION-30`은 같은 M0 세션에서 측정하되 본 SPEC 산출물을 막지 않는다. 결과는 후속 SPEC 입력이다 |
| 제외 | **무응답 픽스처 자동 탐지** | 응답기 `build_exec_result`는 `Cmd()` 결과 문자열만 분류하고 하드웨어 피드백을 수집하지 않는다(`console/lua/copilot_responder.lua:690-706`). 응답기 디스패치 표면은 `ping`, `state`, `prop`, `exec`, `deploy`로 닫혀 있다(`console/lua/copilot_responder.lua:884-946`) |

### §A.2 빌드 순서 vs 리뷰 순서, 그리고 무엇이 무엇을 막는가

빌드 순서는 **M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8**이다. 리뷰 순서는 아래 차단 표를 먼저 본다. 특히 승인 대기는 `ASSUMPTION`이 아니지만 본 SPEC의 최대 위험이다.

| 항목 | 막는 대상 | 성격 | 부정·미승인 시 처리 |
|---|---|---|---|
| **server/safety/** 조건부 예외 승인 대기 | **M1**. M1이 프로퍼티 조회를 제공하므로 **M2 이후도 정지** | **최대 위험.** 코드 착수 게이트 | 승인 전 M1 미착수. `server.bridge` 직접 import, `server/tools/` 예외 증설, 응답기 확장, `exec` 문자열 파싱 우회 전부 금지 |
| `ASSUMPTION-26` | **M4의 매크로 저작 분기** | **M4를 막는 유일한 블로킹 ASSUMPTION** | 부정이면 매크로 대상 커맨드 0건과 `DESCOPE:` 접두 기록. 이것은 정의된 결과이며, 패치 점검·리포트는 계속 진행한다 |
| `ASSUMPTION-27` | M3의 **구간 겹침** 축만 | **동작 축소** | 부정이면 구간 겹침 판정만 빠진다. 주소 중복, 판독 실패 분리, 리포트는 그대로 수행한다 |
| `ASSUMPTION-28` | 본 SPEC 마일스톤 없음 | BUSKWIZ 후속 측정 | 페이지·익스큐터 저작 측정 결과만 기록한다 |
| `ASSUMPTION-29` | 본 SPEC 마일스톤 없음 | `ASSUMPTION-28` 조건부 후속 측정 | `ASSUMPTION-28`이 테스트 익스큐터를 확보할 때만 측정한다 |
| `ASSUMPTION-30` | 본 SPEC 마일스톤 없음 | `ASSUMPTION-28` 조건부 후속 측정 | `ASSUMPTION-28`이 테스트 페이지·익스큐터를 확보할 때만 측정한다 |
| `ASSUMPTION-25` | 계획상 별도 구현 분기 없음 | M0 재확인 항목 | 부정은 조사와 정본 계약의 충돌이다. 우회 구현을 만들지 않고 M0 실패로 기록해 오케스트레이터에게 범위 재개정 필요를 올린다 |

#### 승인 미확정 또는 거부 시 처리 지침

**하는 것**

- `progress.md`에 승인 미확정 또는 거부 사실을 기록하고 M1 상태를 미착수로 둔다.
- M0 접근이 가능하면 M0 측정은 별도 자원으로 진행할 수 있다. 단 그 결과가 M1 우회를 허용하지 않는다.
- 오케스트레이터에게 본 SPEC의 최대 위험이 승인 대기임을 다시 보고한다.

**하지 않는 것**

- `server/prechk/`에서 `server.bridge`를 import하지 않는다. 아키텍처 테스트는 허용 디렉터리를 `server/bridge/`, `server/safety/`, `server/tests/`로 닫고(`server/tests/test_architecture.py:26-39`) 위반 시 실패한다(`server/tests/test_architecture.py:48-61`).
- `server/tools/` 운영 유틸 예외를 늘리지 않는다. 예외 목록은 파일 단위 2건으로 닫혀 있다(`server/tests/test_architecture.py:33-39`).
- `state`나 `exec` 응답 문자열에서 주소를 추출하는 대체 경로를 만들지 않는다. 주소는 확정 프로퍼티 조회의 산출물이며, `exec`는 커맨드 접수 결과만 돌려준다(`console/lua/copilot_responder.lua:690-706`).
- `console/lua/**`를 확장하지 않는다. 현재 디스패치 표면은 이미 `prop`을 제공한다(`console/lua/copilot_responder.lua:884-946`).

### §A.3 ASSUMPTION 부정 시 처리 지침

| 축 | M0 판정 대상 | 부정 시 정의된 결과 | 후속 |
|---|---|---|---|
| `ASSUMPTION-25` | 주소 읽기 재확인 | 계획된 DESCOPE 축이 아니다. M0 실패로 기록하고 범위 재개정 필요를 올린다 | 코드 우회 0건 |
| `ASSUMPTION-26` | 매크로 저작 문법과 효과 재조회 | 매크로 대상 커맨드 0건. `DESCOPE: ASSUMPTION-26 <사유>` 접두 행 기록 | M4는 DESCOPE 경로로 완료, M5 이후 계속 |
| `ASSUMPTION-27` | 픽스처와 점유폭 연결 | 구간 겹침 판정 미수행. `DESCOPE: ASSUMPTION-27 <사유>` 접두 행 기록 | M3 주소 중복과 리포트는 계속 |
| `ASSUMPTION-28` | 페이지·익스큐터 저작 문법 | 후속 측정 실패로 기록 | 본 SPEC 산출물 차단 없음 |
| `ASSUMPTION-29` | 빈 익스큐터 식별 | `ASSUMPTION-28` 부정이면 미측정 기록. 자체 부정이면 후속 측정 실패로 기록 | 본 SPEC 산출물 차단 없음 |
| `ASSUMPTION-30` | `Assign Preset ... At Executor` 효과와 page ≥ 2 일반화 | `ASSUMPTION-28` 부정이면 미측정 기록. 자체 부정이면 후속 측정 실패로 기록 | 본 SPEC 산출물 차단 없음 |

### §A.4 결정 현황 — 해소 7건 / 열린 결정 0건

아래 결정 등록부는 run-phase 재량이 아니다. 문자 식별자는 §F의 결정 기록과 동일하다.

| 결정 | 이름 | 확정 내용 | 반영 마일스톤 |
|---|---|---|---|
| **A** | 신규 모듈 위치 | 신규 기능은 `server/prechk/`에 둔다. 신규 모듈은 콘솔 포트 구현을 모르고 `server.bridge`를 import하지 않는다 | M2~M6 |
| **B** | 초크포인트 확장 범위 | 승인 시 순수 추가 4지점만 허용한다: `server/safety/console.py`, `server/orchestrator/ports.py`, `server/safety/gate.py`, `server/measurement/mock_provider.py` | M1 |
| **C** | 절단 복구 전략 | 루트 열거가 절단되면 `1..node.childCount` 슬롯별 단일 조회를 보강하되, 인덱스 정의역을 모르므로 완전으로 승격하지 않는다 | M2, M3, M8 |
| **D** | 판정 부류 집합 | completeness, fixture verdict, collision kind, read failure kind, skipped check kind는 닫힌 코드 집합으로 둔다 | M3, M5 |
| **E** | 매크로 대상 | 매크로 대상은 리그가 이미 정의한 그룹뿐이다. `Fixture <n>` 대상, 새 그룹 저작, 임의 전체 선택은 0건 | M4 |
| **F** | 리포트 스키마 | 최상위 키는 `inventory`, `fixtures`, `collisions`, `read_failures`, `skipped_checks`, `macro`, `summary_ko`다 | M5, M6, M8 |
| **G** | 라이브 세션 회계 | 라이브는 2회(M0, M8)이며 병합하지 않는다 | M0, M8 |

**열린 결정은 0건이다.** `ASSUMPTION` 부정이나 승인 거부가 새 질문을 만들 수는 있지만, 그것은 이 등록부의 빈칸이 아니라 측정 또는 승인 결과가 새로 만든 외부 접점이다.

### §A.5 PRESERVE 재확인

본 계획은 아래 PRESERVE를 다시 잠근다.

| 항목 | 계획 방침 |
|---|---|
| `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `server/looks/library/` | PRECHK는 룩 계층 소비자가 아니다. 변경 0건 |
| `server/web/preview.py` | 웹 미리보기 산출물 없음 |
| `console/lua/**` | 현재 `state`와 `prop` 표면을 소비한다. 응답기 변경 0건. 프로퍼티 조회 구현은 이미 디스패치에 있다(`console/lua/copilot_responder.lua:900-915`) |
| `server/rulebook/assets/v2.4.2/**` | M0가 실측한 리터럴만 사용하고 룰북을 편집하지 않는다 |
| `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS` | 현재 면제 집합은 `Clear`, `ClearAll`, bare `Fixture|Group` 선택으로 닫혀 있다(`server/orchestrator/tools.py:247-250`). 변경 0건 |
| `server/orchestrator/tools.py`의 실행/dedupe 루프 | `run_commands`의 게이트, stop-on-first-failure, dedupe, 실행 결과 축은 유지한다(`server/orchestrator/tools.py:496-597`) |
| `server/safety/**` | 승인된 조건부 예외 4지점 외 hunk 0건. 승인 전 hunk 0건 |

---

## §B. 마일스톤 M0~M8

각 마일스톤은 착수 직전 baseline을 직접 잰다. 계약 baseline의 2490 passed · 5 skipped · 0 failed 값은 BASE 기록일 뿐, run-phase 마일스톤 baseline으로 이월하지 않는다.

### M0 — 라이브 프로브 (cycle_type=none — 측정 세션, 코드 변경 0)

- **요구·설계 지시**: 실물 grandMA3 onPC 세션에서 `ASSUMPTION-25`, `ASSUMPTION-26`, `ASSUMPTION-27`, `ASSUMPTION-28`, `ASSUMPTION-29`, `ASSUMPTION-30`을 판정한다. `ASSUMPTION-25`는 재확인만 한다. `ASSUMPTION-26`은 생성 프로브와 재조회로 효과를 확인한다. `ASSUMPTION-27`은 표시 문자열 파싱 없이 점유폭 연결이 되는지 본다. `ASSUMPTION-29`와 `ASSUMPTION-30`은 `ASSUMPTION-28` 조건부다.
- **baseline**: 코드 baseline 없음. M0 시작 직전 콘솔 접근성, 응답기 버전, OSC 포트, 대상 쇼파일의 주요 개체 수를 직접 기록한다. 조사 문서의 라이브 값을 이월하지 않는다.
- **뮤테이션**: ① 매크로 저작 GO를 재조회 없이 기록하면 `AC-PRECHK-016`이 죽어야 한다. ② 부정 판정에서 `DESCOPE:` 접두 행을 빼면 `AC-PRECHK-016`이 죽어야 한다. ③ 부정 프로브만으로 `ASSUMPTION-26`을 판정하면 `AC-PRECHK-016`이 죽어야 한다.
- **파일**: 코드 변경 0. 기록은 `progress.md` M0 절. 라이브 콘솔은 M0 소유이므로 plan-phase나 다른 마일스톤이 접속하지 않는다.
- **AC**: AC-PRECHK-016.

### M1 — 초크포인트 프로퍼티 조회 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-PRECHK-019`와 `REQ-PRECHK-020`의 경계를 먼저 구현한다. 승인 기록이 없으면 착수하지 않는다. 승인되면 `query_state`와 동형인 프로퍼티 조회를 추가한다. 현재 `ConsoleLink.query_state`는 request id 생성, `build_state_query` 왕복, timeout/failure 예외, payload 반환으로 닫혀 있다(`server/safety/console.py:372-386`). 현재 포트 계약은 `query_state(path) -> dict`만 둔다(`server/orchestrator/ports.py:68-73`), 게이트 위임은 `_GateStatePort.query_state` 한 메서드다(`server/safety/gate.py:114-121`), 오프라인 대역도 `query_state`만 갖는다(`server/measurement/mock_provider.py:113-128`).
- **baseline**: 착수 직전 `uv run pytest server/tests/ -q`를 직접 실행하고 결과를 기록한다. 승인 기록 존재를 baseline 조건으로 함께 확인한다.
- **뮤테이션**: ① `server/prechk/`에서 `server.bridge`를 import하면 `AC-PRECHK-013`이 죽어야 한다. ② `_NAMED_TOOL_EXEMPTIONS`에 PRECHK 파일을 추가하면 `AC-PRECHK-013`이 죽어야 한다. ③ 기존 `query_state` 시그니처를 바꾸면 `AC-PRECHK-013`이 죽어야 한다.
- **파일**: 조건부 수정 `server/safety/console.py`, `server/orchestrator/ports.py`, `server/safety/gate.py`, `server/measurement/mock_provider.py`; 테스트 `server/tests/test_prechk_inventory.py`; 기존 `server/tests/test_architecture.py`는 소비만 한다.
- **AC**: AC-PRECHK-013.

### M2 — 픽스처 인벤토리 읽기 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-PRECHK-001`, `REQ-PRECHK-002`, `REQ-PRECHK-003`, `REQ-PRECHK-004`, `REQ-PRECHK-005`를 구현한다. 열거 경로는 `Patch/Stages/1/Fixtures`이고, 프로퍼티명은 `Patch`, `FixtureType`, `Mode`, `Name`의 부분집합이다. 공백 포함 프로퍼티명은 프로토콜에서 거부된다(`server/bridge/protocol.py:136-142`). 응답기 `safe_property`는 `handle:Get(name)` 실패 뒤 `handle[name]`을 문자열화하므로 값 형태 검증이 필요하다(`console/lua/copilot_responder.lua:204-217`). 스냅샷은 `node.childCount`에 참 전체 수를 넣고 `children`는 절단될 수 있다(`console/lua/copilot_responder.lua:579-611`, `console/lua/copilot_responder.lua:634-639`).
- **baseline**: 착수 직전 전체 server 테스트를 직접 실측한다. M1이 제공한 프로퍼티 조회 경로가 테스트 대역에서 동작함을 별도 확인한다.
- **뮤테이션**: ① 열거 경로를 `Patch/Fixtures`로 바꾸면 `AC-PRECHK-001`이 죽어야 한다. ② 프로퍼티 후보에 `Address`나 공백 포함 이름을 추가하면 `AC-PRECHK-001`이 죽어야 한다. ③ `function: 0x...` 또는 `None` 문자열을 정상 값으로 채택하면 `AC-PRECHK-002`가 죽어야 한다. ④ completeness를 `truncated` 플래그만으로 판단하면 `AC-PRECHK-003`이 죽어야 한다. ⑤ `Fixture <slot>` 커맨드를 만들면 `AC-PRECHK-004`가 죽어야 한다.
- **파일**: 신규 `server/prechk/__init__.py`, `server/prechk/inventory.py`, 테스트 `server/tests/test_prechk_inventory.py`.
- **AC**: AC-PRECHK-001, AC-PRECHK-002, AC-PRECHK-003, AC-PRECHK-004.

### M3 — 패치 정합성 판정 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-PRECHK-006`, `REQ-PRECHK-007`, `REQ-PRECHK-008`, `REQ-PRECHK-009`, `REQ-PRECHK-010`을 구현한다. `Patch` 원문은 유니버스 정수와 주소 정수로 정규화한다. 주소 중복은 항상 수행한다. 구간 겹침은 `ASSUMPTION-27` GO에서만 수행하고, 부정이면 미수행 판정으로 남긴다. 현재 점유폭 계수의 근거는 `DMXChannels` 자식 수이지만, 픽스처의 표시 문자열을 경로 인덱스로 파싱하지 않는다. FID는 현재 쇼파일에서 슬롯과 구별할 수 없으므로 판정 근거가 아니다(`console/lua/PROTOCOL.md:305-324`).
- **baseline**: 착수 직전 전체 server 테스트를 직접 실측한다. M2의 정합 리그·절단·판독 실패 픽스처가 모두 통과한 상태에서 시작한다.
- **뮤테이션**: ① 주소를 문자열로 비교하면 `AC-PRECHK-005`가 죽어야 한다. ② 파싱 실패 주소를 0이나 1로 채우면 `AC-PRECHK-005`와 `AC-PRECHK-008`이 죽어야 한다. ③ 3개 중복을 쌍 3건으로 세면 `AC-PRECHK-006`이 죽어야 한다. ④ 유니버스를 무시하면 `AC-PRECHK-006`이 죽어야 한다. ⑤ `ASSUMPTION-27` 부정 상태에서 구간 겹침을 수행하면 `AC-PRECHK-007`이 죽어야 한다. ⑥ 판독 실패 픽스처를 정합으로 세면 `AC-PRECHK-008`이 죽어야 한다. ⑦ 불완전 입력에서 한정 없는 정합 판정을 내면 `AC-PRECHK-009`가 죽어야 한다.
- **파일**: 신규 `server/prechk/patch.py`, 테스트 `server/tests/test_prechk_patch.py`.
- **AC**: AC-PRECHK-005, AC-PRECHK-006, AC-PRECHK-007, AC-PRECHK-008, AC-PRECHK-009.

### M4 — 응답 확인 매크로 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-PRECHK-011`, `REQ-PRECHK-012`, `REQ-PRECHK-013`, `REQ-PRECHK-014`를 구현한다. `ASSUMPTION-26` GO면 M0가 실측한 리터럴만 사용한다. 부정이면 매크로 대상 커맨드 0건과 DESCOPE 기록이 결과다. 대상은 그룹뿐이고, `Fixture <n>`은 금지다. 매크로 실행 `ok`는 픽스처 응답 증거가 아니다. 응답기의 `exec` 결과는 `Cmd()`의 접수 결과를 분류한 payload다(`console/lua/copilot_responder.lua:690-706`).
- **baseline**: 착수 직전 전체 server 테스트를 직접 실측한다. M0의 `ASSUMPTION-26` 판정과 `DESCOPE:` 접두 기록 존재 여부를 확인한다.
- **뮤테이션**: ① 매크로 대상에 `Fixture <n>`을 쓰면 `AC-PRECHK-011`이 죽어야 한다. ② 그룹이 없을 때 임의 대체 대상을 만들면 `AC-PRECHK-011`이 죽어야 한다. ③ 결과 payload에 `responded`, `fixture_ok`, `no_response` 계열 필드를 넣으면 `AC-PRECHK-011`이 죽어야 한다. ④ `ASSUMPTION-26` 부정 상태에서 매크로 커맨드를 생성하면 `AC-PRECHK-010`이 죽어야 한다.
- **파일**: 신규 `server/prechk/macro.py`, 테스트 `server/tests/test_prechk_macro.py`.
- **AC**: AC-PRECHK-010, AC-PRECHK-011.

### M5 — 리포트 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-PRECHK-015`, `REQ-PRECHK-016`, `REQ-PRECHK-017`을 구현한다. 집계와 픽스처별 목록을 함께 싣고, 관측된 모든 픽스처가 정확히 한 번 나타나야 한다. 판정 어휘는 닫힌 집합이다. 한국어 라벨은 표현 계층 코드에 두고, 기존 라벨 재사용은 공개 접근자를 통한다. 기존 `server/looks/report.py`는 라벨 표와 공개 접근자를 제공한다(`server/looks/report.py:61-88`).
- **baseline**: 착수 직전 전체 server 테스트를 직접 실측한다. M2~M4의 산출 fixture를 조합한 합성 리포트 입력을 baseline fixture로 고정한다.
- **뮤테이션**: ① 집계만 반환하고 픽스처별 목록을 빼면 `AC-PRECHK-012`가 죽어야 한다. ② 집계 수치와 픽스처별 합을 어긋나게 만들면 `AC-PRECHK-012`가 죽어야 한다. ③ 판정 집합 밖 값을 넣으면 `AC-PRECHK-012`가 죽어야 한다. ④ 밑줄 식별자 직접 import로 한국어 라벨을 가져오면 `AC-PRECHK-012`가 죽어야 한다.
- **파일**: 신규 `server/prechk/report.py`, 테스트 `server/tests/test_prechk_report.py`.
- **AC**: AC-PRECHK-012.

### M6 — 툴 배선 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-PRECHK-018`을 구현한다. 신규 툴 이름은 결정 A~F의 산출물을 실행하는 모델 도달 표면이며, 기존 `run_commands`의 호출자여야 한다. `TOOL_NAMES`는 닫힌 튜플이다(`server/orchestrator/tools.py:53-62`), `query_state` 핸들러는 포트를 통해 읽는다(`server/orchestrator/tools.py:601-610`), 핸들러 맵은 이름에서 클로저로 이어진다(`server/orchestrator/tools.py:1553-1562`). 매크로 실행이 필요할 때도 `run_commands` 게이트를 우회하지 않는다(`server/orchestrator/tools.py:496-597`).
- **baseline**: 착수 직전 전체 server 테스트를 직접 실측한다. 툴 등록 3곳과 핸들러 클로저 위치를 현재 파일에서 심볼로 재확인한다.
- **뮤테이션**: ① `TOOL_NAMES`에서 신규 이름을 빼면 `AC-PRECHK-014`가 죽어야 한다. ② 핸들러에서 `execution_port`를 직접 호출하면 `AC-PRECHK-014`가 죽어야 한다. ③ 신규 REST 라우트나 웹소켓 메시지를 만들면 `AC-PRECHK-014`가 죽어야 한다. ④ 툴 스키마에 그룹·풀·슬롯·픽스처·주소 인자를 받게 하면 `AC-PRECHK-014`가 죽어야 한다. ⑤ 게이트 보류의 `is_error`를 거짓으로 바꾸면 `AC-PRECHK-014`가 죽어야 한다.
- **파일**: 수정 `server/orchestrator/tools.py`, 테스트 `server/tests/test_prechk_tool.py`.
- **AC**: AC-PRECHK-014.

### M7 — 회귀 · PRESERVE (cycle_type=tdd)

- **요구·설계 지시**: 신규 파일 0. 전체 스위트, 신규·변경 파일 lint/format check, PRESERVE diff, 조건부 예외 hunk 제한을 검증한다. diff 범위는 `<BASE>..HEAD`이며 인자 없는 `git diff`로 대체하지 않는다.
- **baseline**: 착수 직전 전체 server 테스트를 직접 실측한다. `<BASE>`는 run-phase kickoff가 기록한 SHA를 쓴다.
- **뮤테이션**: ① PRESERVE 목록의 파일에 공백 1줄을 넣은 임시 변경 또는 임시 커밋을 만들면 diff 게이트가 적발해야 하고, 즉시 되돌린 뒤 다시 빈 출력이어야 한다. 이것이 게이트 비공허성 증명이다. ② `<BASE>..HEAD`를 인자 없는 diff로 바꾸면 절차가 실패해야 한다. ③ `console/lua/**`를 수정하면 `AC-PRECHK-015`가 죽어야 한다. ④ 승인 없는 `server/safety/**` hunk가 있으면 `AC-PRECHK-015`가 죽어야 한다.
- **파일**: 신규 파일 0. 기존 테스트와 diff gate만 사용한다. 기록은 `progress.md` M7 절.
- **AC**: AC-PRECHK-015.

### M8 — 종단 라이브 (cycle_type=none — 측정 세션, 코드 변경 0)

- **요구·설계 지시**: 완성된 툴을 통해 실물 콘솔에서 점검을 종단 1회 실행한다. 빌더를 직접 호출하지 않는다. 감사 로그와 재조회 결과로 툴 반환을 대조한다. M0의 `ASSUMPTION`을 재측정하지 않는다. 무응답 여부는 판정하지 않고 패치 메타데이터 수준의 한계를 결과에 명시한다.
- **baseline**: 코드 baseline은 M7의 검증 결과가 최종이다. M8 시작 직전 콘솔 접근성, 응답기 버전, OSC 포트, 대상 쇼파일 개체 수를 직접 재기록한다.
- **뮤테이션**: ① 툴을 거치지 않고 빌더를 직접 실행하면 `AC-PRECHK-017`이 죽어야 한다. ② 감사 로그 대조 없이 툴 반환만으로 검증하면 `AC-PRECHK-017`이 죽어야 한다. ③ M0에서 닫은 `ASSUMPTION`을 M8에서 다시 측정해 결과를 덮어쓰면 `AC-PRECHK-017`이 죽어야 한다.
- **파일**: 코드 변경 0. 기록은 `progress.md` M8 절, 감사 로그 원문, 재조회 응답 원문.
- **AC**: AC-PRECHK-017.

---

## §C. 라이브 세션 회계

라이브 세션은 **2회**다: M0와 M8. 둘은 병합할 수 없다.

| 세션 | AC | 대상 | 왜 병합 불가인가 |
|---|---|---|---|
| **M0** | `AC-PRECHK-016` | 코드 없는 시점의 전제 측정. `ASSUMPTION-25`, `ASSUMPTION-26`, `ASSUMPTION-27`, `ASSUMPTION-28`, `ASSUMPTION-29`, `ASSUMPTION-30` 판정 | M1~M6의 구현 전에 답이 필요한 전제다. 완성된 파이프라인이 없으므로 M8 대상도 없다 |
| **M8** | `AC-PRECHK-017` | 완성된 툴의 종단 통합. 읽기, 판정, 보고, 감사 로그 대조 | M6와 M7 이후에만 존재한다. M0에서 미리 실행할 물건이 없다 |

M0는 코드 없는 시점의 전제 측정이고, M8은 완성된 파이프라인 대상이다. 라이브 접근성은 Kickoff와 M7 완료 직후에 각각 확인한다.

---

## §D. 제약

1. **순수 함수 우선.** `server/prechk/`는 포트가 돌려준 payload를 정규화하고 판정하는 계층이다. 콘솔 접촉은 M0와 M8의 라이브 세션뿐이며, M1~M7의 테스트는 인메모리 대역과 기존 포트를 쓴다.
2. **테스트 파일명은 고정.** `acceptance.md`가 이미 `server/tests/test_prechk_inventory.py`, `server/tests/test_prechk_patch.py`, `server/tests/test_prechk_macro.py`, `server/tests/test_prechk_report.py`, `server/tests/test_prechk_tool.py`를 지목했다. run-phase가 임의로 바꾸지 않는다.
3. **실패 모드는 개별 테스트로 분리.** `프로퍼티 판독 실패`, `형태 불만족`, `주소 파싱 불가`를 한 카운터에 넣지 않는다. 사용자 조치가 다르기 때문이다.
4. **0건 스캔은 비공허성을 동반.** 생성된 조회 목록, 생성 커맨드 목록, AST 식별자 목록이 실제로 비어 있지 않음을 함께 assert한다.
5. **AST 스캔 우선.** import 경계와 직접 접근 검증은 raw grep이 아니라 AST 식별자 스캔을 쓴다. 주석·독스트링의 설명을 호출로 오인하지 않기 위해서다.
6. **값 형태 검증은 시스템 경계다.** 응답기 `safe_property`가 메서드 참조도 문자열화할 수 있으므로(`console/lua/copilot_responder.lua:204-217`) `ok=true`는 값 채택 조건이 아니다.
7. **절단은 정상 경로다.** 응답기는 `max_children = 24`와 `max_payload = 1900`을 둘 다 갖고(`console/lua/copilot_responder.lua:31-39`), payload 예산 초과 시 trailing children을 제거한다(`console/lua/copilot_responder.lua:634-639`). 완전성은 `node.childCount`와 읽은 개수 비교로 판단한다.

---

## §E. 테스트 골격

| 파일 | 소유 AC | 핵심 fixture |
|---|---|---|
| `server/tests/test_prechk_inventory.py` | `AC-PRECHK-001`, `AC-PRECHK-002`, `AC-PRECHK-003`, `AC-PRECHK-004`, `AC-PRECHK-013` | 정합 리그, 절단 parent, `function: 0x...`, `None`, 슬롯≠FID, 승인 미확정 |
| `server/tests/test_prechk_patch.py` | `AC-PRECHK-005`, `AC-PRECHK-006`, `AC-PRECHK-007`, `AC-PRECHK-008`, `AC-PRECHK-009` | 주소 파싱 실패, 2개 중복, 3개 중복, 다른 유니버스, 구간 겹침 GO, `ASSUMPTION-27` 부정 |
| `server/tests/test_prechk_macro.py` | `AC-PRECHK-010`, `AC-PRECHK-011` | 그룹 있음, 그룹 없음, `ASSUMPTION-26` 부정, 슬롯≠FID |
| `server/tests/test_prechk_report.py` | `AC-PRECHK-012` | 모든 결함 fixture를 합성한 2단 리포트 |
| `server/tests/test_prechk_tool.py` | `AC-PRECHK-014` | 툴 디스패치, 스키마 최소화, 실행 경로, `is_error` 규약 |
| 기존 전체 스위트와 diff gate | `AC-PRECHK-015` | PRESERVE diff, gate 비공허성, 전체 회귀 |

마일스톤별 뮤테이션은 §B의 각 절에 적은 항목을 소진한다. 뮤테이션 결과는 `progress.md`에 killed/survived로 기록하고, survived는 해당 마일스톤 미완료로 본다.

---

## §F. 결정 기록 (재질의 금지)

### §F.1 채택된 결정 7건

| 결정 | 확정 내용 | 반영 위치 |
|---|---|---|
| **A — 신규 모듈 위치** | `server/prechk/` 신규 모듈. 콘솔 포트 구현과 `server.bridge`를 모른다 | §A.4, §B M2~M6 |
| **B — 초크포인트 확장 범위** | 승인 시 순수 추가 4지점만 허용. 승인 전 M1 미착수 | §A.2, §B M1, §G 사용자 접점 |
| **C — 절단 복구 전략** | 슬롯별 보강은 상세를 늘리지만 완전성 승격은 하지 않는다 | §A.4, §B M2, §B M8 |
| **D — 판정 부류 집합** | completeness, fixture verdict, collision kind, read failure kind, skipped check kind는 닫힌 집합 | §A.4, §B M3, §B M5 |
| **E — 매크로 대상** | 그룹만 대상으로 한다. `Fixture <n>`, 새 그룹 저작, 임의 전체 선택은 0건 | §A.4, §B M4 |
| **F — 리포트 스키마** | `inventory`, `fixtures`, `collisions`, `read_failures`, `skipped_checks`, `macro`, `summary_ko` | §A.4, §B M5 |
| **G — 라이브 세션 회계** | M0와 M8 2회. M0는 전제 측정, M8은 완성 파이프라인 검증 | §B M0, §B M8, §C |

### §F.2 열린 결정 0건

열린 결정은 0건이다. 다음 항목은 열린 결정이 아니다.

| 항목 | 왜 열린 결정이 아닌가 |
|---|---|
| `server/safety/**` 조건부 예외 | 승인 게이트다. 승인되면 결정 B대로 4지점만 추가하고, 승인되지 않으면 M1 미착수다 |
| `ASSUMPTION-26` 부정 | 결정 E가 이미 DESCOPE 결과를 정의했다 |
| `ASSUMPTION-27` 부정 | 결정 D와 F가 미수행 부류와 리포트 표현을 이미 정의했다 |
| `ASSUMPTION-28`, `ASSUMPTION-29`, `ASSUMPTION-30` 결과 | BUSKWIZ 후속 측정 기록이며 PRECHK 산출물 정의를 바꾸지 않는다 |

---

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

> **구속력 있는 기록은 progress.md §F이며 오케스트레이터 소유다**(첫 run-phase Agent() 스폰 전 작성). **본 절은 권고이며 오케스트레이터가 확정·기각한다.** 어긋나면 progress.md가 이긴다.

### 입력 파라미터

- **tier**: L.
- **scope (file count)**: 예상 13~16 파일. 신규 구현 5(`server/prechk/__init__.py`, `inventory.py`, `patch.py`, `macro.py`, `report.py`), 조건부 초크포인트 4, 툴 수정 1, 신규 테스트 5, 기록 1.
- **domain count**: 1. 파이썬 백엔드와 markdown 기록. 콘솔 Lua, 프런트엔드, 룰북 자산은 PRESERVE.
- **file language mix**: Python + markdown. 신규 런타임 의존성 0.
- **parallel benefit**: LOW. M1 승인이 M2 이후를 정지시키고, M2 인벤토리가 M3 판정의 입력이며, M3/M4 결과가 M5 리포트와 M6 툴 반환 형상을 정한다.
- **Agent Teams prereqs**: 해당 없음.

### 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 라이브 2회, 조건부 승인, 신규 모듈, 툴 배선이 있다 |
| 2 | background | 미선택 | 코드 쓰기와 승인 게이트가 포함된다 |
| 3 | agent-team | 미선택 | retired/tombstone 모드 |
| 4 | parallel | 미선택 | 도메인 1, 단일 언어, M1 승인 사슬과 M2→M3→M5→M6 데이터 사슬 때문에 병렬 이득이 낮다 |
| 5 | **sub-agent** | **선택** | Tier L이지만 순차 의존이 강하고, 각 마일스톤을 단일 worker가 계약대로 밀고 가는 편이 충돌이 적다 |
| 6 | workflow | 미선택 | 균일 기계 변환이 아니라 판정·DESCOPE·보고 형상을 계속 확인해야 한다 |

### Decision: sub-agent

### 정당화

M1의 승인 대기가 본 SPEC의 최대 위험이고, 그 뒤 M2 인벤토리 → M3 판정 → M5 리포트 → M6 툴 표면이 순차 데이터 사슬을 이룬다. `ASSUMPTION-26`은 M4의 매크로 저작 분기만 막고, `ASSUMPTION-27`은 M3 구간 겹침만 줄이며, `ASSUMPTION-28`, `ASSUMPTION-29`, `ASSUMPTION-30`은 후속 측정이라 병렬 팀으로 나눌 독립 산출물이 아니다. 따라서 권고 모드는 **sub-agent**다.

### 사용자 접점

| 시점 | 접점 | 이유 |
|---|---|---|
| **Kickoff** | **server/safety/** 조건부 예외 승인 | M1 전제다. 미승인 시 M1 미착수이고 M2 이후도 정지한다. 본 SPEC 최대 위험 |
| **Kickoff** | M0 라이브 세션 접근 가능성 | M0는 코드 없는 전제 측정이며 라이브 세션 2회 중 1번째다 |
| **M7 완료 직후** | M8 라이브 세션 접근 가능성 재확인 | M8은 완성된 파이프라인 대상이며 M0와 병합할 수 없다 |

### 조건부 접점

| 조건 | 접점 |
|---|---|
| `ASSUMPTION-26` 부정 | 매크로 DESCOPE가 기록됐음을 사용자에게 고지한다. 대체 문법을 묻지 않고 매크로 대상 커맨드 0건으로 진행한다 |
| `ASSUMPTION-25` 부정 | 정본 계약과 조사 결론의 충돌이므로 오케스트레이터가 범위 재개정을 요청한다. 우회 구현 0건 |
| `ASSUMPTION-28` GO 이후 테스트 페이지·익스큐터가 남는 경우 | M0 정리 기록을 사용자에게 확인받는다. 남길지 지울지 묻는 것이 아니라, 원상 복구 재조회 증거를 공유한다 |
| M8에서 M0 판정과 종단 관측이 어긋나는 경우 | 불일치 자체를 기록하고 오케스트레이터에게 후속 판단을 요청한다. M8이 M0 판정을 덮어쓰지 않는다 |

**Implementation Kickoff Approval은 위 접점의 승인을 받는 절차이지, §F 결정 등록부를 다시 여는 절차가 아니다.**
