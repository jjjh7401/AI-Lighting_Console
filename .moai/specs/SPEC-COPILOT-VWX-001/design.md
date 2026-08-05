# SPEC-COPILOT-VWX-001 — 설계 근거 (design)

status: draft (v0.1.0, 2026-08-05) · Tier L · 출처: `.moai/reports/ma3-copilot-overview.html` §7 P0 항목. 본 문서는 spec.md 요구의 설계 근거와 위험 검토를 담는다. 설계 슬롯은 5건이고 전부 닫혔다.

> **참조 규약.** 본 SPEC의 정본 `research.md` · `spec.md` · `acceptance.md`는 줄번호로 인용하지 않고 `REQ-VWX-001` 같은 안정 토큰, `AC-VWX-001` 같은 안정 토큰, `ASSUMPTION-68` 같은 안정 토큰, 절 제목만 쓴다. `파일:줄`은 코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다. clarification 마커는 0건이다. 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]`으로 표기하며, `[실측]`은 라이브 콘솔 직접 관측을 기록한 절에만 붙인다. Vectorworks 공식 문서 인용은 `[Vectorworks 문서]`로 표기한다.

---

## §1. 의도

본 SPEC은 Vectorworks Instrument Data를 읽어 **설계상 리그(designed rig)** 모델을 만들고, 이미 라이브 검증된 `precheck_patch`(콘솔 실측)와 대조해 **차이만 보고**한다. 콘솔에 아무것도 쓰지 않는 첫 Vectorworks 연계 SPEC이므로 설계의 중심은 "더 많이 파싱하기"가 아니라 **"포맷을 추측하지 않고, 대조 조인 키를 정직하게 좁히는 것"**이다.

만드는 것은 셋이다.

| 산출 | 내용 | 연결 토큰 |
|---|---|---|
| 가져오기 + 정규화 | 경로 A/B 판독, 별칭 테이블, 인코딩, 주소 4형식 정규화 | `REQ-VWX-001`~`REQ-VWX-011` |
| 설계상 리그 모델 | 멀티셀 폴딩, 액세서리 필터링, 퍼지 매칭, 조인키 충돌 거부, VW 자체 충돌 통과 | `REQ-VWX-012`~`REQ-VWX-017` |
| 대조 리포트 | (유니버스,주소)+타입 조인, FID/CID 구조화된 미수행, 3부류 리포트, 옵션 구간겹침 | `REQ-VWX-018`~`REQ-VWX-025` |

만들지 않는 것은 넷이다.

| 제외 | 이유 | 고정 토큰 |
|---|---|---|
| Lua `AddFixtures` 자동 패치 | 사람 승인이 필요한 2단계이며 본 SPEC은 콘솔에 쓰지 않는다 | §D |
| MVR/GDTF 가져오기 | 3단계이며 공간 인식 계층 결합이 별도로 필요하다 | §D |
| FID/CID 아이덴티티 대조 | 슬롯==FID 쇼파일로는 원리적으로 불가(`console/lua/PROTOCOL.md:305-324`) | `REQ-VWX-018`, `REQ-VWX-019` |
| 패치 자동 재배치 | 본 SPEC은 판정·보고만 한다 | §D |

설계의 성공 조건은 파일을 많이 파싱하는 것이 아니라, **"이 필드는 도면에서 왔고 저 필드는 추측이다"를 절대 섞지 않는 것**이다.

---

## §2. 변경 표면

### §2.1 예상 신규·수정 파일

| 파일 | 신규/수정 | 근거 | PRESERVE 대조 |
|---|---|---|---|
| `server/vwx/__init__.py` | 신규 | 신규 모듈 경계. 공개 함수만 노출한다 | 신규 경로라 침범 0건 |
| `server/vwx/reader.py` | 신규 | 경로 A/B 판별, 인코딩 폴백, `Instrument Summary` 거부, 데이터 블록 구조적 식별 | 신규 경로라 침범 0건 |
| `server/vwx/columns.py` | 신규 | 별칭 테이블 매칭, `extra` 보존, 최소 유효 레코드 판정 | 신규 경로라 침범 0건 |
| `server/vwx/address.py` | 신규 | 4형식 주소 파싱, 미패치 sentinel, 멀티시스템 차단, `normalize_address` 표현 일치 | 신규 경로라 침범 0건 |
| `server/vwx/rig.py` | 신규 | 설계상 리그 도메인 모델, 멀티셀 폴딩, 액세서리 필터링, 퍼지 매칭, 조인키 충돌 거부, VW 자체 충돌 통과 | 신규 경로라 침범 0건 |
| `server/vwx/diff.py` | 신규 | 조인 키 (유니버스,주소)+타입, FID/CID `SkippedCheck`, 3부류 리포트, 옵션 구간겹침 | 신규 경로라 침범 0건 |
| `server/vwx/report.py` | 신규 | 구조화 페이로드, 한국어 표현, 닫힌 판정 어휘 매핑 | 신규 경로라 침범 0건 |
| `server/orchestrator/tools.py` | 수정 | 신규 모델 도달 툴 1종(`precheck_vectorworks_diff`). 기존 `precheck_patch`가 `TOOL_NAMES`(`server/orchestrator/tools.py:127`, 항목 `:136`) · 핸들러(`:1986`) · `ToolDefinition`(`:4317`) · `handlers`(`:5134`, 항목 `:5143`) 4지점에 등재된 동형 패턴을 따른다 | 잠긴 `_PROGRAMMER_STATE_COMMANDS`와 실행/dedupe 루프는 무변경 |
| `server/prechk/verdicts.py` | 조건부 수정(순수 추가) | 신규 판정 부류(`missing_in_console` 등)를 `CLOSED_VOCABULARIES`(`server/prechk/verdicts.py:52`)에 추가 | 기존 부류 의미 무변경 — 순수 추가만 |
| `pyproject.toml` | 조건부 수정 | `openpyxl` 승인 시 런타임 의존성 1건 추가 | 승인 없으면 무변경 |
| `server/tests/test_vwx_reader.py` | 신규 | `AC-VWX-002`~`005` | 신규 테스트라 침범 0건 |
| `server/tests/test_vwx_columns.py` | 신규 | `AC-VWX-006`~`008` | 신규 테스트라 침범 0건 |
| `server/tests/test_vwx_address.py` | 신규 | `AC-VWX-009`~`012` | 신규 테스트라 침범 0건 |
| `server/tests/test_vwx_rig.py` | 신규 | `AC-VWX-013`~`017` | 신규 테스트라 침범 0건 |
| `server/tests/test_vwx_diff.py` | 신규 | `AC-VWX-018`~`021` | 신규 테스트라 침범 0건 |
| `server/tests/test_vwx_report.py` | 신규 | `AC-VWX-022`, `AC-VWX-023` | 신규 테스트라 침범 0건 |
| `server/tests/test_vwx_tool.py` | 신규 | `AC-VWX-024` | 신규 테스트라 침범 0건 |

테스트 파일명은 `plan.md` §D가 지목한 이름 그대로다.

### §2.2 `server/vwx/` 모듈 구성

`server/vwx/`는 파일 바이트를 받아 판정 결과를 산출하는 순수 판정 계층이다. `server.bridge`를 직접 import하지 않는다 — 그 경계는 아키텍처 테스트가 `server.bridge`·`pythonosc`를 `_FORBIDDEN_MODULE_PREFIXES`(`server/tests/test_architecture.py:48`)로 닫아 강제한다.

| 모듈 | 공개 표면(개념) | 내부 책임 |
|---|---|---|
| `reader.py` | 원시 바이트 → 원시 레코드(dict) 목록 | 경로 A/B 판별, 인코딩 폴백, `Instrument Summary` 거부, 데이터 블록 구조적 식별 |
| `columns.py` | 원시 레코드 → 별칭 해석된 레코드 | 별칭 테이블 매칭, `extra` 보존, 최소 유효성 판정 |
| `address.py` | 컬럼 해석 레코드 → 정규화 주소 + 분류 | 4형식 주소 파싱, 미패치 sentinel, 멀티시스템 차단, `AddressParse` 동형 표현 |
| `rig.py` | 정규화 레코드 목록 → 설계상 리그 모델 | 멀티셀 폴딩, 액세서리 필터링, 퍼지 매칭, 조인키 충돌 거부, VW 자체 충돌 통과 |
| `diff.py` | 설계상 리그 + 콘솔 실측(`Inventory`/`PatchSheet`) → 대조 결과 | 조인, 3부류 분류, FID/CID `SkippedCheck`, 옵션 구간겹침 |
| `report.py` | 대조 결과 → 사용자 대면 페이로드 | 닫힌 판정 어휘를 한국어로 표현하고 구조화 페이로드를 조립한다 |

`server/prechk/report.py`의 한국어 라벨 접근자 패턴을 재사용한다 — 라벨 표를 코드 표현 계층에 두고 공개 접근자(`label()`, `server/prechk/report.py:143`)로 알 수 없는 코드를 그대로 통과시키지 않는다.

### §2.3 `server/orchestrator/tools.py` 신규 툴 등재 4지점

신규 툴 이름은 `precheck_vectorworks_diff`로 둔다. `precheck_patch`의 실측 등록 좌표를 동형으로 따른다.

| 지점 | `precheck_patch`의 현재 좌표 | VWX 변경 | 누락 시 죽는 AC |
|---|---|---|---|
| `TOOL_NAMES` | 닫힌 튜플에 `"precheck_patch"`가 있다(`server/orchestrator/tools.py:127`, 항목 `:136`) | `"precheck_vectorworks_diff"` 1항 추가 | `AC-VWX-024` |
| 핸들러 클로저 | `precheck_patch` 핸들러가 `build_toolset` 내부에서 정의된다(`server/orchestrator/tools.py:1986`) | `precheck_vectorworks_diff(call, context)` 추가 | `AC-VWX-024` |
| `definitions` | `precheck_patch`의 `ToolDefinition`이 등재된다(`server/orchestrator/tools.py:4317`) | 신규 `ToolDefinition` 추가 — 파일 경로/바이트 인자만, **리그 식별자 0개**(콘솔에서 직접 읽으므로 스키마에 슬롯·픽스처·주소 인자가 필요 없다) | `AC-VWX-024` |
| `handlers` | `"precheck_patch": precheck_patch`가 맵에 있다(`server/orchestrator/tools.py:5134`, 항목 `:5143`) | `"precheck_vectorworks_diff": precheck_vectorworks_diff` 추가 | `AC-VWX-024` |

툴 핸들러는 `execution_port`를 직접 호출하지 않는다. 본 SPEC은 콘솔 발화가 없으므로(§1) `run_commands` 재호출도 없다 — 핸들러는 (1) 업로드된 Vectorworks 파일을 판독하고 (2) `read_inventory`/`build_patch_sheet`로 콘솔 실측을 읽어 (3) 대조 결과를 반환하는 **독립 판독-대조 경로**다.

### §2.4 신규 의존성 승인 지점

| 지점 | 추가 | 근거 |
|---|---|---|
| `pyproject.toml` `dependencies` | `openpyxl` (승인 시) | 경로 B의 `.xlsx` 바이너리 포맷을 표준 라이브러리로 파싱할 수 없다. 현재 런타임 의존성 9건 중 CSV/Excel 파싱 라이브러리는 0건(`pyproject.toml` 직접 확인) |

미승인이면 `server/vwx/reader.py`는 `.xlsx` 확장자를 판독 실패("미승인 의존성")로 분류하는 분기만 갖는다(§D Out of Scope 참조).

### §2.5 PRESERVE 침범 0건 표

| PRESERVE 항목 | 설계 방침 | 침범 |
|---|---|---|
| `console/lua/**` | 콘솔 발화 0건 — 본 SPEC은 읽고 대조만 한다 | 0건 |
| `server/safety/**` | 신규 초크포인트 확장 없음 | 0건 |
| `server/prechk/{inventory,patch,report}.py` | 소비만 한다 | 0건 |
| `server/prechk/verdicts.py` | **순수 추가만** — `CLOSED_VOCABULARIES`에 신규 부류 등록 | 순수 추가(예외로 명시됨) |
| `server/paperwork/{data,render,output}.py` | 소비만 한다 | 0건 |
| `server/looks/**` | 소비하지 않는다 | 0건 |
| `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 실행/dedupe 루프 | 무변경 — 신규 툴은 이 루프의 재호출자가 아니다 | 0건 |
| `server/rulebook/assets/v2.4.2/**` | 참조하지 않는다 — 콘솔 발화가 없다 | 0건 |

---

## §3. 흐름

```
판독 -> 인코딩 확정 -> 컬럼 별칭 해석 -> 주소 정규화 -> 설계상 리그 모델 -> (콘솔 실측 조회) -> 대조 -> 리포트
```

1. **판독.** `reader.py`는 확장자가 아니라 내용 구조로 경로 A(tab-delimited)와 경로 B(워크시트 그리드)를 판별한다. 경로 B는 별칭 매칭 ≥2인 첫 행을 헤더 후보로 삼고 컬럼 수 연속 구간만 데이터 블록으로 채택한다(`research.md` §Path B — 문서화된 구획 마커가 없으므로 이 휴리스틱이 유일한 판별 수단이다).
2. **인코딩 확정.** BOM 스니프 → `utf-8-sig` → `utf-16` → `cp1252` → `mac_roman` 순으로 판독을 시도한다. 전부 실패하면 바이트 오프셋과 함께 명시적으로 실패한다 — 모지바케를 값으로 채택하지 않는다.
3. **컬럼 별칭 해석.** `columns.py`는 대소문자·공백·구두점을 무시하는 별칭 테이블로 매칭한다. 매칭되지 않는 컬럼은 `extra`에 원문 보존한다. `instrument_type` + 해석 가능한 주소 표현 중 하나가 없으면 판독 실패로 분류한다.
4. **주소 정규화.** `address.py`는 4가지 원문 표현(`Universe/Address`, `Universe`, `DMX Address`, `Absolute Address`) 중 우선순위를 둔다 — `Universe`+`DMX Address` 쌍이 있으면 그것을 최우선 사용하고, 없을 때만 `Absolute Address` 역산을 **전제 검증 성공 시에만** 시도한다. `0`/공란은 "설계됨·미배정"으로 분류한다. 2개 이상 System 문자가 관측되면 순수 `Universe` 해석을 차단한다.
5. **설계상 리그 모델.** `rig.py`는 `Part Index`로 멀티셀 행을 접고, `Device Type`으로 `Static Accessory`를 걸러내며, 파일 내부 조인키(`unit_number`/`channel`) 중복을 거부한다. Vectorworks 자체 패치 충돌(overlap/identical/conflict)은 예외가 아니라 구조화된 부류로 통과시킨다.
6. **콘솔 실측 조회.** `diff.py`는 `read_inventory`(`server/prechk/inventory.py:344`) 또는 `build_patch_sheet`(`server/paperwork/data.py:67`)를 호출해 콘솔 실측 `Inventory`/`PatchSheet`를 얻는다. `server.bridge`를 직접 호출하지 않는다.
7. **대조.** 조인 키는 **(유니버스, 주소) + 픽스처 타입**이다. `FID`/`CID`는 비교 연산자의 피연산자로 절대 쓰지 않는다. 타입·모드 명칭은 퍼지 매칭으로 판정하고 해결 불가는 "미해결"로 남긴다. `DMX Footprint` 폭 출처가 있으면 `_range_overlaps`(`server/prechk/patch.py:440`)를 `FootprintPolicy(enabled=True)`로 재사용해 구간 겹침을 추가 판정한다.
8. **리포트.** `report.py`는 3부류(`missing_in_console`/`address_collision`/`quantity_mismatch`) + `skipped_checks`(FID/CID 항상 포함) + `read_failures`를 구조화된 최상위 키로 담는다. 사용자 대면 문자열은 한국어이며 `server/prechk/report.py`의 라벨 표를 확장해 재사용한다.

---

## §4. 위험 검토

| 위험 | 흡수 설계 | 고정 AC |
|---|---|---|
| `research.md` §Path A/B: export가 하나의 포맷이 아니라 2경로·6+ 확장자다. 확장자가 구분자를 결정하지 않는다. | 내용 구조(별칭 매칭 개수·컬럼 수 연속성)로 경로를 판별하고, 문서화된 구획 마커가 없음을 인정해 추측 구간을 만들지 않는다(못 찾으면 판독 실패). | `AC-VWX-002`, `AC-VWX-003` |
| `research.md` §1.3: `Instrument Summary`는 주소 열이 없어 패치 출처가 아니다. | 주소 관련 별칭 컬럼이 0개면 판독 실패로 거부한다. | `AC-VWX-004` |
| `research.md` §Encoding: 인코딩이 문서화되어 있지 않다. | 폴백 체인 + 전부 실패 시 명시적 실패(바이트 오프셋). 모지바케를 값으로 채택하지 않는다. | `AC-VWX-005` |
| `research.md` §Address: 4가지 동시 표현, 미패치는 값이 아니라 `0`/공란. `Absolute Address` 공식은 조건부로만 안전하다. | 쌍 컬럼 우선, `Absolute Address`는 전제 검증 성공 시에만, 미패치는 제3의 분류로 명시. | `AC-VWX-009`, `AC-VWX-010` |
| `research.md` §Pitfalls ①: 멀티셀 픽스처(Part Index)가 N행=1픽스처를 만든다. | 대조 전에 폴딩한다. | `AC-VWX-013` |
| `research.md` §Pitfalls ②: 액세서리(Static/DMX)가 계수를 오염시킨다. | `Device Type`으로 대조 이전 필터링. | `AC-VWX-014` |
| `research.md` §Pitfalls ③: 타입/모드 명칭이 VW·콘솔 간 절대 문자열 일치하지 않는다. | `==` 금지, 퍼지 매칭 + 미해결 표시. | `AC-VWX-015` |
| `research.md` §Pitfalls ④: 미패치가 "콘솔에 없음"과 혼동될 수 있다. | 별도 sentinel 분류(주소 처리 단계에서 미리 분리). | `AC-VWX-009` |
| `research.md` §Pitfalls ⑤: 파일 내부 조인키 중복/공란이 last-write-wins 손실을 만든다. | 자동 병합 거부 + 충돌 보고. | `AC-VWX-016` |
| `research.md` §Pitfalls ⑥: Vectorworks 자체 패치 충돌이 export에 흘러든다. | 구조화된 부류로 통과(예외 아님). | `AC-VWX-017` |
| `research.md` §Pitfalls ⑦: 멀티시스템(A-Z)이 유니버스를 혼동시킨다. | 모호 시 차단 + 사유. | `AC-VWX-011` |
| §A 사전 확정 사실 3: 슬롯==FID 쇼파일에서 FID/CID 아이덴티티 대조가 불가능하다. | 조인 키를 (유니버스,주소)+타입으로 한정하고 `SkippedCheck` 동형 구조로 미수행을 명시. | `AC-VWX-018`, `AC-VWX-019` |
| `ASSUMPTION-68` 부정/부분GO: 별칭 테이블이 실물 헤더와 불일치. | 별칭 테이블 확장(계약 위반 아님) — REQ-VWX-005의 매칭 규약 자체는 불변. | `AC-VWX-006` |
| `ASSUMPTION-70` 부정: 워크시트 데이터 블록을 구조적으로 못 찾는다. | 헤더 체크박스 활성 파일로 지원 범위 축소, 리포트에 명시. | `AC-VWX-003` |

위험의 공통 처리 원칙은 하나다. 포맷 미탐, 판독 실패, 미수행, 부정 전제는 모두 **정상 페이로드의 구조화된 부류**이며 예외 산문으로만 흘리지 않는다.

---

## §5. 설계 슬롯

열린 슬롯은 0건이다. 아래 결정은 run-phase 재량이 아니라 이 문서의 설계 계약이다.

| 슬롯 | 결정 | 기각한 대안 | 연결 토큰 |
|---|---|---|---|
| A. 경로 A/B 판별 전략 | 확장자를 무시하고 내용 구조(구분자 시도 + 별칭 매칭 개수)로 판별한다. 경로 B는 별칭 매칭 ≥2인 첫 행을 헤더로, 컬럼 수 연속 구간만 데이터로 채택한다. | 확장자 기반 분기(`.xlsx`=경로B, `.txt`=경로A로 단정), 첫 행을 무조건 헤더로 가정하는 대안, 워크시트 마커 문서를 기다리는 대안(존재하지 않음). | `REQ-VWX-001`, `REQ-VWX-002`, `AC-VWX-002`, `AC-VWX-003` |
| B. 주소 표현 우선순위 | `Universe`+`DMX Address` 쌍을 최우선 사용하고, `Absolute Address` 역산은 전제(연속 512블록) 검증 성공 시에만 수행한다. `0`/공란은 별도 sentinel. | `Absolute Address`를 기본 소스로 쓰는 대안(비연속 유니버스에서 조용히 틀린다), 미패치를 "콘솔에 없음"과 합치는 대안. | `REQ-VWX-008`, `REQ-VWX-009`, `AC-VWX-009`, `AC-VWX-010` |
| C. 대조 조인 키 | (유니버스, 주소) + 픽스처 타입. `FID`/`CID`는 조인 연산자 피연산자로 0건. | 슬롯 번호를 FID로 대체하는 대안(REQ-LOOKLIB-008 계열 금지 위반), FID를 "참고 수준"으로라도 조인에 섞는 대안(우연일치 리그에서 조용히 틀린다). | `REQ-VWX-018`, `AC-VWX-018` |
| D. 판정 부류의 닫힌 집합 | `read_failure_kind`, `address_classification`, `diff_kind`(`missing_in_console`/`address_collision`/`quantity_mismatch`), `skipped_check_kind`(`fid_cid_identity_unreachable`/`footprint_overlap_descope`/`worksheet_block_undetected`)를 코드 상수로 닫는다. | 자유 문자열 사유만 반환하는 대안, 미패치와 콘솔부재를 한 카운터에 합치는 대안. | `REQ-VWX-020`, `REQ-VWX-023`, `AC-VWX-020`, `AC-VWX-022` |
| E. 리포트 페이로드 스키마 | `designed_rig`, `console_rig`, `diffs{missing_in_console, address_collision, quantity_mismatch}`, `skipped_checks`, `read_failures`, `summary_ko`를 최상위 키로 둔다. | 집계만 반환하는 대안, 콘솔 실측을 다시 계산하는 대안(재사용 대신 재구현). | `REQ-VWX-020`, `REQ-VWX-023`, `AC-VWX-020`, `AC-VWX-022` |

### §5.1 리포트 페이로드 스키마

| 키 | 값 | 필수성 |
|---|---|---|
| `designed_rig` | `{path, encoding, path_kind(A/B), records, extra_columns_seen}` | 항상 |
| `console_rig` | `read_inventory`/`build_patch_sheet` 산출을 그대로 참조(재계산 없음) | 항상 |
| `diffs` | `{missing_in_console, address_collision, quantity_mismatch}`이며 각 항목은 관여 요소 전량을 싣는다 | 항상, 비어 있어도 포함 |
| `skipped_checks` | `{kind, reason}` 목록. `fid_cid_identity_unreachable`이 항상 포함 | 항상 |
| `read_failures` | `{row, column, kind, detail}` 목록 | 항상, 비어 있어도 포함 |
| `summary_ko` | 한국어 요약 문자열 | 항상 |

---

## §6. 테스트 설계

### §6.1 인메모리 픽스처

M0 실물 샘플이 fixture의 근거이지만, 결함을 심은 합성 fixture 없이는 탐지 로직이 참임을 보일 수 없다(정합 샘플만으로는 모든 판정이 "이상 없음"으로 수렴한다).

| 픽스처 이름 | 심은 사실 | 죽이는 결함 | 관련 AC |
|---|---|---|---|
| `clean_export_a` | 경로 A tab-text, 헤더 있음, 정상 20행 | 정상 판독 실패 | `AC-VWX-002` |
| `worksheet_with_subtotals` | 제목행+헤더행+데이터행+소계행 혼재 | 소계행 오분류 | `AC-VWX-003` |
| `instrument_summary_only` | 주소 열 없음 | 요약을 패치 출처로 오채택 | `AC-VWX-004` |
| `mixed_encoding_korean` | utf-16/cp1252/mac_roman 각 인코딩, 한국어 포지션명 | 모지바케 값 채택 | `AC-VWX-005` |
| `alias_variant_headers` | `"DMX Address"`/`"dmx address"`/이중공백/하이픈 4변형 | 위치 기반 매칭 | `AC-VWX-006` |
| `unknown_column_present` | 별칭표 밖 컬럼 1개 | extra 폐기 | `AC-VWX-007` |
| `missing_instrument_type` | instrument_type 공란 | 예외 발생 | `AC-VWX-008` |
| `unpatched_zero_and_blank` | 주소 `0`과 공란 각 1행 | 콘솔부재와 혼동 | `AC-VWX-009` |
| `absolute_only_noncontiguous` | Absolute Address만, 비연속 유니버스 | 무검증 역산 | `AC-VWX-010` |
| `multi_system_ab` | System A·B 둘 다 Universe 1 | 임의 병합 | `AC-VWX-011` |
| `part_index_multicell` | Part Index 1~3, 1픽스처 | 위양성 수량 불일치 | `AC-VWX-013` |
| `static_accessory_row` | Device Type=Static Accessory | 계수 오염 | `AC-VWX-014` |
| `type_name_variant` | `"Robe Robin MMX Spot"` vs 콘솔 `"Robin MMX Spot"` | `==` 비교 | `AC-VWX-015` |
| `duplicate_unit_number` | 동일 unit_number 2행 | last-write-wins 손실 | `AC-VWX-016` |
| `vw_identical_patch` | 같은 universe+address+channel | 예외 발생 | `AC-VWX-017` |
| `fid_coincidence_rig` | 콘솔 슬롯==FID, 도면 fixture_id 조작 | 조인 키가 FID를 쓴다 | `AC-VWX-018` |
| `footprint_available` | DMX Footprint 값 존재 | 구간겹침 미판정 | `AC-VWX-021` |
| `openpyxl_unapproved_xlsx` | `.xlsx` 확장자, 승인 없음 상태 시뮬레이션 | 사유 문자열 누락 | (§D 대응, 코드 경로 확인용) |

### §6.2 AC별 검증 파일

| AC | 검증 파일 | 핵심 픽스처 |
|---|---|---|
| `AC-VWX-001` | `progress.md` M0 절 | 실물 샘플 |
| `AC-VWX-002` | `test_vwx_reader.py` | `clean_export_a` |
| `AC-VWX-003` | `test_vwx_reader.py` | `worksheet_with_subtotals` |
| `AC-VWX-004` | `test_vwx_reader.py` | `instrument_summary_only` |
| `AC-VWX-005` | `test_vwx_reader.py` | `mixed_encoding_korean` |
| `AC-VWX-006` | `test_vwx_columns.py` | `alias_variant_headers` |
| `AC-VWX-007` | `test_vwx_columns.py` | `unknown_column_present` |
| `AC-VWX-008` | `test_vwx_columns.py` | `missing_instrument_type` |
| `AC-VWX-009` | `test_vwx_address.py` | `unpatched_zero_and_blank` |
| `AC-VWX-010` | `test_vwx_address.py` | `absolute_only_noncontiguous` |
| `AC-VWX-011` | `test_vwx_address.py` | `multi_system_ab` |
| `AC-VWX-012` | `test_vwx_address.py` | `clean_export_a`(정상값 대조) |
| `AC-VWX-013` | `test_vwx_rig.py` | `part_index_multicell` |
| `AC-VWX-014` | `test_vwx_rig.py` | `static_accessory_row` |
| `AC-VWX-015` | `test_vwx_rig.py` | `type_name_variant` |
| `AC-VWX-016` | `test_vwx_rig.py` | `duplicate_unit_number` |
| `AC-VWX-017` | `test_vwx_rig.py` | `vw_identical_patch` |
| `AC-VWX-018` | `test_vwx_diff.py` | `fid_coincidence_rig` |
| `AC-VWX-019` | `test_vwx_diff.py` | 임의 정상 대조 결과 |
| `AC-VWX-020` | `test_vwx_diff.py` | missing/collision/mismatch 합성 |
| `AC-VWX-021` | `test_vwx_diff.py` | `footprint_available` |
| `AC-VWX-022` | `test_vwx_report.py` | 전 결함 합성 리포트 |
| `AC-VWX-023` | `test_vwx_report.py` | 라벨 표 대조 |
| `AC-VWX-024` | `test_vwx_tool.py`, 기존 `test_architecture.py` | 툴 디스패치 픽스처 |
| `AC-VWX-025` | 기존 전체 스위트와 diff 게이트 | PRESERVE diff 비공허성 주입 |
| `AC-VWX-026` | 종단 실행(라이브 아님) | M0 샘플 + 대역 |

### §6.3 마일스톤별 뮤테이션 제안

| 마일스톤 | 주입할 결함 | 죽어야 하는 AC |
|---|---|---|
| M1 | 확장자만으로 구분자를 정한다. | `AC-VWX-002`, `AC-VWX-003` |
| M1 | `Instrument Summary`를 패치 출처로 채택한다. | `AC-VWX-004` |
| M1 | 인코딩 실패 시 조용히 통과시킨다. | `AC-VWX-005` |
| M2 | 위치 기반 컬럼 매칭을 쓴다. | `AC-VWX-006` |
| M2 | `extra` 필드를 버린다. | `AC-VWX-007` |
| M2 | 최소조건 미달 레코드에서 예외를 던진다. | `AC-VWX-008` |
| M3 | `0`/공란을 콘솔부재와 합친다. | `AC-VWX-009` |
| M3 | 전제 검증 없이 절대주소를 역산한다. | `AC-VWX-010` |
| M3 | 멀티시스템에서 임의 유니버스를 추측한다. | `AC-VWX-011` |
| M3 | 정규화 표현이 `AddressParse`와 다른 형태를 갖는다. | `AC-VWX-012` |
| M4 | `Part Index` 폴딩을 생략한다. | `AC-VWX-013` |
| M4 | Static Accessory를 계수에 포함한다. | `AC-VWX-014` |
| M4 | 타입/모드를 `==`로 비교한다. | `AC-VWX-015` |
| M4 | 중복 조인키를 last-write-wins로 병합한다. | `AC-VWX-016` |
| M4 | VW 자체 충돌을 예외로 던진다. | `AC-VWX-017` |
| M5 | `FID`/`CID`를 조인 키에 쓴다. | `AC-VWX-018` |
| M5 | FID/CID 미수행을 산문으로만 적는다. | `AC-VWX-019` |
| M5 | 3부류 중 하나를 생략한다. | `AC-VWX-020` |
| M5 | `FootprintPolicy` 미주입 상태에서 구간겹침을 판정한다. | `AC-VWX-021` |
| M6 | 구조화 페이로드 대신 산문 예외를 던진다. | `AC-VWX-022` |
| M6 | 한국어 라벨을 밑줄 식별자 직접 import로 가져온다. | `AC-VWX-023` |
| M6 | `TOOL_NAMES`에 툴을 넣지 않거나 `execution_port`를 직접 호출한다. | `AC-VWX-024` |
| M7 | PRESERVE diff를 `<BASE>..HEAD` 없이 검사한다. | `AC-VWX-025` |
| M7 | `console/lua/**` 또는 `server/prechk/{inventory,patch,report}.py`를 수정한다. | `AC-VWX-025` |
| M8 | 툴을 거치지 않고 내부 함수를 직접 호출해 종단 검증한다. | `AC-VWX-026` |

제안 뮤테이션은 총 25개다(M1 3 · M2 3 · M3 4 · M4 5 · M5 4 · M6 3 · M7 2 · M8 1 = 25, plan-audit 지적 반영 — 표 25행과 재계산 일치시킴).

---

## §7. 안티패턴

| 안티패턴 | 왜 금지인가 | 걸리는 토큰 |
|---|---|---|
| 확장자만으로 구분자·경로를 단정한다. | `.txt`가 tab-text일 수도, `.csv`가 워크시트 그리드일 수도 있다(`research.md` §Path A/B). | `REQ-VWX-001`, `REQ-VWX-002` |
| `Instrument Summary`를 재시도한다. | 주소 열이 없다. 죽은 출처를 다시 탐색하는 것이다. | `REQ-VWX-003` |
| `Absolute Address`를 기본 소스로 쓴다. | 비연속 유니버스 파일에서 조용히 틀린다. | `REQ-VWX-009` |
| 타입/모드 표시 문자열을 `==`로 비교한다. | 서로 다른 소스(VW vs 콘솔)의 명명 체계는 절대 일치하지 않는다. | `REQ-VWX-015`, `AC-VWX-015` |
| 슬롯이나 `fixture_id`/`uid`를 조인 키에 섞는다. | 슬롯==FID인 쇼파일에서 조용히 틀린 대조를 낸다. | `REQ-VWX-018`, `AC-VWX-018` |
| 절단된/미탐된 데이터 블록에서 "차이 없음"을 보고한다. | 관측하지 않은 것에 대한 정합 단정이다. | `REQ-VWX-023`, `AC-VWX-003` |
| `server/vwx/`가 `server.bridge`를 직접 import한다. | 단일 초크포인트 경계를 우회한다. | `AC-VWX-024` |
| 콘솔 실측을 재구현하고 `read_inventory`/`build_patch_sheet`를 재호출하지 않는다. | 이미 라이브 검증된 경로를 이중 구현하면 두 경로가 드리프트한다. | `AC-VWX-024` |
| 리포트를 자유 산문으로만 반환한다. | 산술 정합과 닫힌 판정 어휘를 검증할 수 없다. | `REQ-VWX-023`, `AC-VWX-022` |

---

## §8. 교차 참조

### §8.1 REQ 대응

| 토큰 | 설계 위치 | 주요 AC |
|---|---|---|
| `REQ-VWX-001` | §3 판독, §5 슬롯 A | `AC-VWX-002` |
| `REQ-VWX-002` | §3 판독, §5 슬롯 A | `AC-VWX-003` |
| `REQ-VWX-003` | §4 위험 검토 | `AC-VWX-004` |
| `REQ-VWX-004` | §3 인코딩 확정 | `AC-VWX-005` |
| `REQ-VWX-005` | §3 컬럼 별칭 해석 | `AC-VWX-006` |
| `REQ-VWX-006` | §3 컬럼 별칭 해석 | `AC-VWX-007` |
| `REQ-VWX-007` | §3 컬럼 별칭 해석 | `AC-VWX-008` |
| `REQ-VWX-008` | §3 주소 정규화, §5 슬롯 B | `AC-VWX-009` |
| `REQ-VWX-009` | §3 주소 정규화, §5 슬롯 B | `AC-VWX-010` |
| `REQ-VWX-010` | §3 주소 정규화 | `AC-VWX-011` |
| `REQ-VWX-011` | §3 주소 정규화 | `AC-VWX-012` |
| `REQ-VWX-012` | §3 설계상 리그 모델 | `AC-VWX-013` |
| `REQ-VWX-013` | §3 설계상 리그 모델 | `AC-VWX-013` |
| `REQ-VWX-014` | §3 설계상 리그 모델 | `AC-VWX-014` |
| `REQ-VWX-015` | §3 설계상 리그 모델, §7 안티패턴 | `AC-VWX-015` |
| `REQ-VWX-016` | §3 설계상 리그 모델 | `AC-VWX-016` |
| `REQ-VWX-017` | §3 설계상 리그 모델 | `AC-VWX-017` |
| `REQ-VWX-018` | §3 대조, §5 슬롯 C, §7 안티패턴 | `AC-VWX-018` |
| `REQ-VWX-019` | §3 대조 | `AC-VWX-019` |
| `REQ-VWX-020` | §3 리포트, §5 슬롯 D·E | `AC-VWX-020` |
| `REQ-VWX-021` | §3 대조 | `AC-VWX-021` |
| `REQ-VWX-022` | §3 콘솔 실측 조회, §7 안티패턴 | `AC-VWX-024` |
| `REQ-VWX-023` | §3 리포트, §5 슬롯 D | `AC-VWX-022` |
| `REQ-VWX-024` | §2.2 | `AC-VWX-023` |
| `REQ-VWX-025` | §2.3 툴 등재 | `AC-VWX-024` |

### §8.2 AC와 마일스톤 대응

| 마일스톤 | AC | 설계 검증 초점 |
|---|---|---|
| M0 | `AC-VWX-001` | 실물 샘플 확보, `ASSUMPTION-68` 판정 |
| M1 | `AC-VWX-002`~`005` | 경로 A/B 판독, 인코딩, `Instrument Summary` 거부 |
| M2 | `AC-VWX-006`~`008` | 별칭 매칭, `extra` 보존, 최소 유효성 |
| M3 | `AC-VWX-009`~`012` | 미패치 분류, 절대주소 조건부 역산, 멀티시스템 차단, 표현 일치 |
| M4 | `AC-VWX-013`~`017` | 멀티셀 폴딩, 액세서리 필터링, 퍼지 매칭, 조인키 충돌, VW 충돌 통과 |
| M5 | `AC-VWX-018`~`021` | 조인 키, FID/CID 미수행, 3부류 리포트, 옵션 구간겹침 |
| M6 | `AC-VWX-022`~`024` | 구조화 페이로드, 한국어 표현, 툴 배선 |
| M7 | `AC-VWX-025` | PRESERVE diff, 회귀, 비공허성 게이트 |
| M8 | `AC-VWX-026` | 종단 통합(라이브 없음) |

### §8.3 ASSUMPTION 대응

| 토큰 | 설계 결정 |
|---|---|
| `ASSUMPTION-68` | M0가 실물 샘플로 판정한다. 부정/부분GO는 별칭 테이블 확장(계약 위반 아님)으로 흡수한다. |
| `ASSUMPTION-69` | `Absolute Address` 역산 경로의 실행 여부를 가른다. 부정이어도 코드는 방어적으로 존재한다. |
| `ASSUMPTION-70` | 경로 B 자동 데이터 블록 식별의 동작 축소 전제다. 부정이면 헤더 체크박스 활성 파일로 지원 범위를 좁힌다. |

열린 설계 슬롯은 0건이다.
