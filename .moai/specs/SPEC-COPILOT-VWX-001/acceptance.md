# SPEC-COPILOT-VWX-001 — 인수 기준 (acceptance)

status: draft (v0.1.4, 2026-08-05) · Tier L · AC 29건 계획. 본 문서는 spec.md의 요구를 관측 가능한 검증 기준으로 전개한다.

> **v0.1.0 — 최초 작성.** **AC 26건**(AC-VWX-001~026) · **REQ 25건**(REQ-VWX-001~025) 전량 커버. 라이브 AC는 **0건**이다 — `plan.md` §C가 라이브 세션 0회 결정의 근거를 적는다.
>
> **참조 규약**: 본 SPEC의 정본(spec.md · 본 문서)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다.

---

## §A. 개요

가져오기 → 컬럼/주소 정규화 → 설계상 리그 모델 → precheck_patch 대조 → 리포트. 검증의 축은 넷이다.

| 축 | 내용 | 왜 이것이 축인가 |
|---|---|---|
| **① 형식 관용성** | 포맷을 추측하지 않고 구조적으로 판별한다 | Vectorworks export가 하나의 포맷이 아니라 2경로·6+ 확장자이며 확장자가 구분자를 결정하지 않는다(`research.md` §Path A/B) |
| **② 조인 정직성** | 대조 조인 키에 `FID`/`CID`를 쓰지 않고 그 미수행을 숨기지 않는다 | 슬롯==FID 쇼파일에서는 원리적으로 판별 불가하다(§A 사전 확정 사실 3) |
| **③ 판정 분리** | 미패치·판독 실패·조인키 충돌·정상을 섞지 않는다 | 넷은 사용자가 취할 조치가 다르다 |
| **④ 경계 유지** | PRESERVE·단일 초크포인트·신규 의존성 승인 경계를 깨지 않는다 | 신규 모듈이 이미 검증된 콘솔 읽기 경로를 재사용해야 하는 첫 SPEC이다 |

---

## §B. Given-When-Then 시나리오

**시나리오 1 — 경로 A(tab-text) 정상 파일**: **Given** 헤더 있는 tab-delimited Instrument Data 파일, **When** 가져오기를 실행하면, **Then** 확장자와 무관하게 tab 구분자로 판독되고 별칭 테이블로 컬럼이 해석된다.

**시나리오 2 — 경로 B(워크시트) 소계행 혼재**: **Given** 제목행·헤더행·데이터행·소계행이 섞인 워크시트 export, **When** 가져오기를 실행하면, **Then** 데이터행만 레코드로 채택되고 소계행은 판독 실패(또는 스킵 사유)로 분류된다.

**시나리오 3 — `Instrument Summary` 오인 방지**: **Given** 주소 열이 없는 요약 리포트, **When** 패치 출처로 지정하면, **Then** 판독 실패로 거부되고 사유가 "패치 출처 아님"으로 명시된다.

**시나리오 4 — FID 우연일치 리그에서 조인 키 무시**: **Given** 슬롯과 FID가 우연히 일치하는 콘솔 실측 리그와 그와 다른 FID/CID 유사값을 가진 설계상 리그, **When** 대조를 실행하면, **Then** 대조 결과가 FID/CID 값 변화에 영향받지 않고 (유니버스, 주소)+타입만으로 판정된다.

**시나리오 5 — 멀티셀 픽스처 폴딩**: **Given** `Part Index` 1~3을 가진 3개 행이 하나의 물리 픽스처를 나타내는 도면, **When** 설계상 리그 모델을 생성하면, **Then** 논리적 픽스처 1개로 접혀 대조 시 위양성 수량 불일치가 발생하지 않는다.

**시나리오 6 — 멀티시스템 모호 차단**: **Given** System A와 System B가 둘 다 `Universe 1`을 쓰는 도면, **When** 주소를 해석하면, **Then** 순수 `Universe` 컬럼 해석이 모호로 차단되고 사유가 리포트에 남는다.

---

## §C. 인수 기준

### §C.0 역추적표

| REQ | 커버 AC | M | 비고 |
|---|---|---|---|
| REQ-VWX-001 | AC-VWX-002 | M1 | 경로 A tab-text 판독 |
| REQ-VWX-002 | AC-VWX-003 | M1 | 경로 B 데이터 블록 구조적 식별 |
| REQ-VWX-003 | AC-VWX-004 | M1 | Instrument Summary 거부 |
| REQ-VWX-004 | AC-VWX-005 | M1 | 인코딩 폴백 + 명시적 실패 |
| REQ-VWX-005 | AC-VWX-006 | M2 | 별칭 테이블 매칭(비위치) |
| REQ-VWX-006 | AC-VWX-007 | M2 | 미지 컬럼 보존(extra) |
| REQ-VWX-007 | AC-VWX-008 | M2 | 최소 유효 레코드 판정 |
| REQ-VWX-008 | AC-VWX-009 | M3 | 미패치 sentinel 분류 |
| REQ-VWX-009 | AC-VWX-010 | M3 | Absolute Address 조건부 역산 |
| REQ-VWX-010 | AC-VWX-011 | M3 | 멀티시스템 모호 차단 |
| REQ-VWX-011 | AC-VWX-012 | M3 | normalize_address 표현 일치 |
| REQ-VWX-012 | AC-VWX-013 | M4 | 설계상 리그 모델 생성 |
| REQ-VWX-013 | AC-VWX-013 | M4 | 멀티셀 폴딩(같은 AC의 별 구간) |
| REQ-VWX-014 | AC-VWX-014 | M4 | 액세서리 필터링 |
| REQ-VWX-015 | AC-VWX-015 | M4 | 타입·모드 퍼지 매칭 |
| REQ-VWX-016 | AC-VWX-016 | M4 | 내부 조인키 충돌 거부 |
| REQ-VWX-017 | AC-VWX-017 | M4 | VW 자체 충돌 분류 통과 |
| REQ-VWX-018 | AC-VWX-018 | M5 | 조인 키 = 주소+타입, FID/CID 금지 |
| REQ-VWX-019 | AC-VWX-019 | M5 | FID/CID 구조화된 미수행 |
| REQ-VWX-020 | AC-VWX-020 | M5 | 대조 리포트 3부류 |
| REQ-VWX-021 | AC-VWX-021 | M5 | 옵션 구간 겹침 재사용 |
| REQ-VWX-022 | AC-VWX-024 | M6 | 콘솔 실측 경유(같은 AC의 별 구간) |
| REQ-VWX-023 | AC-VWX-022 | M6 | 구조화된 페이로드 |
| REQ-VWX-024 | AC-VWX-023 | M6 | 한국어 표현 계층 |
| REQ-VWX-025 | AC-VWX-024 | M6 | 툴 배선 4지점(같은 AC의 별 구간) |
| REQ-VWX-026 | AC-VWX-027 | M2 | fixture_name·gdtf_fixture 정규 필드 승격 |
| REQ-VWX-027 | AC-VWX-028 | M3 | 주소 3중 표현 교차검증 |
| REQ-VWX-028 | AC-VWX-029 | M5 | 설계 측 구간 겹침 판정 |

**REQ 28/28 커버, 누락 0.** 역추적표에 행이 없는 AC는 **3건**이며 의도다 — **AC-VWX-001**(M0 전제 확보 게이트) · **AC-VWX-025**(회귀·PRESERVE, 단일 REQ가 아니라 형상 전체가 대상) · **AC-VWX-026**(종단 통합).

### §C.0a 마일스톤별 AC 배정 (정본)

| 마일스톤 | AC | 수 |
|---|---|---|
| M0 — 실물 Vectorworks export 샘플 확보 | AC-VWX-001 | 1 |
| M1 — 파일 판독 + 인코딩 | AC-VWX-002 · AC-VWX-003 · AC-VWX-004 · AC-VWX-005 | 4 |
| M2 — 컬럼 해석 | AC-VWX-006 · AC-VWX-007 · AC-VWX-008 · AC-VWX-027 | 4 |
| M3 — 주소 처리 | AC-VWX-009 · AC-VWX-010 · AC-VWX-011 · AC-VWX-012 · AC-VWX-028 | 5 |
| M4 — 설계상 리그 모델 | AC-VWX-013 · AC-VWX-014 · AC-VWX-015 · AC-VWX-016 · AC-VWX-017 | 5 |
| M5 — precheck_patch 대조 | AC-VWX-018 · AC-VWX-019 · AC-VWX-020 · AC-VWX-021 · AC-VWX-029 | 5 |
| M6 — 보고 + 툴 배선 | AC-VWX-022 · AC-VWX-023 · AC-VWX-024 | 3 |
| M7 — 회귀 · PRESERVE | AC-VWX-025 | 1 |
| M8 — 종단 검증 | AC-VWX-026 | 1 |

**합 29 · 중복 0 · 누락 0.** 이 표가 정본이며 `plan.md`의 마일스톤별 `AC` 줄과 1:1이다(v0.1.4 — M0 실물 샘플 반영으로 M2/M3/M5에 각 1건씩 추가).

---

### AC-VWX-001 — M0 실물 샘플 확보 게이트 (전제 게이트, M0)

**When** run-phase가 M0를 완료하면, the 시스템 **shall** 실물 Vectorworks export 샘플을 확보하고 `ASSUMPTION-68`에 결과를 배정한다.

- 대상 요구사항: **없음 — 전제 확보 게이트 AC다.**
- 검증 방법: 사용자 제공 실물 파일 + `progress.md` 기록.
- 기대 결과:
  - ① 실물 Vectorworks export 파일 최소 1개(가능하면 경로 A 1개 + 경로 B 1개)가 `.moai/state/verify/vwx-m0/`에 존재한다.
  - ② 그 파일의 원문 헤더가 `progress.md`에 요약 없이 전재된다.
  - ③ `ASSUMPTION-68`에 GO/부분GO/NEGATIVE 중 하나가 배정된다.
  - ④ 이 AC가 PASS하기 전에는 M1의 컬럼 계약이 "확정"으로 표시되지 않는다 — M1 자체의 코드 구조 설계는 `research.md`를 근거로 진행할 수 있으나, fixture는 M0 샘플을 반영해야 한다.

### AC-VWX-002 — 경로 A(tab-text) 판독 (M1)

**When** 경로 A tab-delimited Instrument Data 파일을 판독하면, the 가져오기 파서 **shall** 구분자를 tab으로 고정하고 확장자를 무시한다.

- 대상 요구사항: REQ-VWX-001
- 검증 방법: `server/tests/test_vwx_reader.py`
- 기대 결과:
  - ① 헤더가 있는 파일과 없는 파일 둘 다 별칭 매칭 개수로 헤더 유무를 스니핑해 올바르게 판독한다.
  - ② `.txt` 확장자이며 값 안에 comma를 포함한 tab-text 파일에서 구분자를 comma로 오인하지 않는다(확장자·내용 혼동 방지, 비공허성 — 실제로 comma 포함 값이 온전히 한 필드로 보존됨을 확인).
  - ③ 자동 추가된 `UID` 컬럼이 별칭 테이블의 `uid` 필드로 인식된다.

### AC-VWX-003 — 경로 B(워크시트) 데이터 블록 구조적 식별 (M1)

**When** 워크시트 export 파일에서 데이터 블록을 찾으면, the 가져오기 파서 **shall** 별칭 매칭 ≥2인 첫 행을 헤더로 삼고 컬럼 수가 연속으로 일치하는 구간만 채택한다.

- 대상 요구사항: REQ-VWX-002
- 검증 방법: `server/tests/test_vwx_reader.py`
- 기대 결과:
  - ① 제목행 + 헤더행 + 데이터행 + 소계행이 섞인 합성 워크시트에서 데이터행만 레코드로 채택되고 소계행은 판독 실패(또는 스킵 사유 기록)로 분류된다.
  - ② 헤더를 못 찾는(체크박스 미선택) 워크시트에서 예외 없이 빈 레코드 + 사유("헤더 없음 — 데이터 블록 미탐")를 반환한다(비공허성 — 임의 추측으로 블록을 자르는 지점이 0건임을 함께 확인).
  - ③ `ASSUMPTION-70`이 NEGATIVE로 판정된 경우, 이 AC는 "Export field names as first record" 활성 파일에 한정해 PASS로 재정의되며 그 축소가 `progress.md`에 기록된다(계약 위반이 아니라 §A.3의 정의된 결과).

### AC-VWX-004 — `Instrument Summary` 거부 (M1)

The 가져오기 파서 **shall not** `Instrument Summary`(주소 열 없음)를 패치 출처로 채택한다.

- 대상 요구사항: REQ-VWX-003
- 검증 방법: `server/tests/test_vwx_reader.py`
- 기대 결과:
  - ① 별칭 테이블의 `universe`/`address`/`absolute_address` 계열 컬럼이 전혀 매칭되지 않는 파일은 판독 실패로 분류되고 사유에 "패치 출처 아님(주소 열 없음)"이 명시된다.
  - ② 정상 파일에서는 이 판정이 오발동하지 않는다(비공허성).

### AC-VWX-005 — 인코딩 폴백 + 명시적 실패 (M1)

**When** 인코딩이 불확실하면, the 가져오기 파서 **shall** BOM → `utf-8-sig` → `utf-16` → `cp1252` → `mac_roman` 순으로 시도하고 전부 실패 시 바이트 오프셋과 함께 실패한다.

- 대상 요구사항: REQ-VWX-004
- 검증 방법: `server/tests/test_vwx_reader.py`
- 기대 결과:
  - ① 각 인코딩으로 저장된 동일 내용의 한국어 포함 파일(예: 포지션명 "무대 좌측")이 모두 올바르게 판독된다.
  - ② 5종 전부 실패하는 임의 바이너리에서 모지바케 문자열이 아니라 명시적 실패 + 바이트 오프셋이 반환된다(조용한 통과 0건).

### AC-VWX-006 — 별칭 테이블 컬럼 매칭 (M2)

The 컬럼 해석기 **shall** 대소문자·공백·구두점 무시 별칭 매칭을 수행하며 위치 기반 매칭을 하지 않는다.

- 대상 요구사항: REQ-VWX-005
- 검증 방법: `server/tests/test_vwx_columns.py`
- 기대 결과:
  - ① `"DMX Address"`, `"dmx address"`, `"DMX  Address"`(이중공백), `"DMX-Address"` 넷이 모두 같은 정규 필드로 해석된다.
  - ② 컬럼 순서를 뒤섞은 파일에서도 동일 필드가 동일하게 해석된다(위치 무관성, 비공허성).

### AC-VWX-007 — 미지 컬럼 보존 (M2)

The 컬럼 해석기 **shall** 별칭 테이블 밖 컬럼을 `extra`에 보존한다.

- 대상 요구사항: REQ-VWX-006
- 검증 방법: `server/tests/test_vwx_columns.py`
- 기대 결과:
  - ① 별칭 테이블에 없는 임의 컬럼명(`"Custom Field 1"`)이 원문 그대로 `extra["Custom Field 1"]`에 남는다.
  - ② 값이 폐기되지 않는다(비공허성 — `extra` 딕셔너리가 비어 있지 않음을 확인).

### AC-VWX-008 — 최소 유효 레코드 판정 (M2)

**When** 레코드가 `instrument_type` + 해석 가능한 주소 표현을 갖지 못하면, the 컬럼 해석기 **shall** 구조화된 판독 실패로 분류한다.

- 대상 요구사항: REQ-VWX-007
- 검증 방법: `server/tests/test_vwx_columns.py`
- 기대 결과:
  - ① `instrument_type` 없는 행이 예외를 던지지 않고 판독 실패 레코드로 반환된다.
  - ② 정상 레코드는 판독 실패로 오분류되지 않는다(비공허성).

### AC-VWX-009 — 미패치 sentinel 분류 (M3)

**When** `DMX Address`/`Absolute Address`가 `0` 또는 공란이면, the 주소 해석기 **shall** "설계됨·미배정"으로 분류한다.

- 대상 요구사항: REQ-VWX-008
- 검증 방법: `server/tests/test_vwx_address.py`
- 기대 결과:
  - ① 값 `0`인 레코드와 공란인 레코드 둘 다 같은 분류를 받는다.
  - ② 이 분류가 대조 단계의 `missing_in_console`과 **다른 코드값**을 갖는다(비공허성 — 두 값이 서로 다름을 직접 assert).

### AC-VWX-010 — `Absolute Address` 조건부 역산 (M3)

**Where** Universes 창이 연속 기본 512블록이라는 전제가 검증 가능할 때만, the 주소 해석기 **shall** `abs=(u-1)*512+a` 역산을 수행한다.

- 대상 요구사항: REQ-VWX-009
- 검증 방법: `server/tests/test_vwx_address.py`
- 기대 결과:
  - ① `Universe`/`DMX Address` 쌍 컬럼이 존재하면 그 쌍을 우선 사용하고 역산을 시도하지 않는다.
  - ② `Absolute Address` 단일값만 있고 전제를 검증할 근거가 없으면 역산하지 않고 판독 실패로 분류한다(추측 0건).
  - ③ `ASSUMPTION-69`가 GO로 판정된 경우에 한해 M0 샘플의 실측 역산 값이 `progress.md`에 재검증 기록으로 추가된다.

### AC-VWX-011 — 멀티시스템 모호 차단 (M3)

**When** System 문자 2개 이상이 관측되면, the 주소 해석기 **shall** 순수 `Universe` 해석을 모호로 차단한다.

- 대상 요구사항: REQ-VWX-010
- 검증 방법: `server/tests/test_vwx_address.py`
- 기대 결과:
  - ① System A와 System B가 둘 다 `Universe 1`을 쓰는 합성 파일에서 두 유니버스를 임의로 병합하지 않고 차단 + 사유("멀티시스템 — Universe 컬럼만으로 구분 불가")를 반환한다.
  - ② 단일 System 파일에서는 이 차단이 오발동하지 않는다(비공허성).

### AC-VWX-012 — `normalize_address` 표현 일치 (M3)

The 주소 해석기가 산출하는 정규화 표현 **shall** `normalize_address`의 `AddressParse`와 동일한 폭·의미론을 갖는다.

- 대상 요구사항: REQ-VWX-011
- 검증 방법: `server/tests/test_vwx_address.py`
- 기대 결과:
  - ① 동일 논리 주소(유니버스 1, 주소 1)를 `server/prechk/patch.py normalize_address('1.001')`과 본 SPEC의 파생기 양쪽에 넣었을 때 산출되는 (유니버스, 주소) 정수 값이 **동치**다(자료구조가 달라도 필드 대 필드 비교가 가능하다).
  - ② 파싱 불가 입력에서 두 파서가 같은 "실패" 신호 형태(예외가 아니라 실패를 나타내는 구조)를 낸다.

### AC-VWX-013 — 설계상 리그 모델 + 멀티셀 폴딩 (M4)

**When** `Part Index`로 여러 셀 행이 관측되면, the 시스템 **shall** 대조 전에 논리적 픽스처 1개로 접는다.

- 대상 요구사항: REQ-VWX-012 · REQ-VWX-013
- 검증 방법: `server/tests/test_vwx_rig.py`
- 기대 결과:
  - ① `Part Index` 1~3을 가진 3행이 설계상 리그 모델에서 1개 픽스처로 접힌다.
  - ② 접힌 픽스처의 `unit_number`/`instrument_type`은 **정본 대표 규칙 — `Part Index` 최솟값 행을 대표로 채택한다**(닫힌 결정, 대안 아님)에서 오며 임의 값이 아니다.
  - ③ `Part Index`가 없는 일반 픽스처는 접힘 없이 1:1로 반영된다(비공허성).

### AC-VWX-014 — 액세서리 필터링 (M4)

The 시스템 **shall** `Device Type`으로 Light-class와 비-DMX `Static Accessory`를 대조 계수 이전에 필터링한다.

- 대상 요구사항: REQ-VWX-014
- 검증 방법: `server/tests/test_vwx_rig.py`
- 기대 결과:
  - ① `Device Type = "Static Accessory"`인 행이 설계상 리그의 대조 대상 픽스처 수에서 제외된다.
  - ② `Device Type = "Accessory"`(DMX 소비, 예: 컬러 스크롤러)는 포함된다.
  - ③ `Device Type` 컬럼이 아예 없는 파일에서는 필터링을 수행하지 않고 그 사실을 리포트에 명시한다(임의 배제 금지 — 비공허성).

### AC-VWX-015 — 타입·모드 퍼지 매칭 (M4)

The 시스템 **shall not** 타입·모드 명칭을 동등 비교로 판정한다.

- 대상 요구사항: REQ-VWX-015
- 검증 방법: `server/tests/test_vwx_rig.py`
- 기대 결과:
  - ① Vectorworks의 `"Robe Robin MMX Spot"`과 콘솔의 `"Robin MMX Spot"`이 정규화·부분 매칭으로 동일 타입으로 해석된다(완전 문자열 일치가 아니어도 매칭).
  - ② 매칭이 해결되지 않는 임의 문자열 쌍은 "미해결"로 표시되고 정합/부적합 어느 쪽으로도 세지 않는다.
  - ③ 타입/모드 비교 지점에서 `==` 연산자를 직접 쓰는 코드가 AST 스캔으로 **0건**이다(비공허성 — 스캔이 실제 비교 지점을 방문했음을 함께 확인).

### AC-VWX-016 — 파일 내부 조인키 충돌 거부 (M4)

**When** `unit_number`/`channel`이 중복이거나 공란인 레코드가 2개 이상이면, the 시스템 **shall** 자동 병합을 거부하고 충돌로 보고한다.

- 대상 요구사항: REQ-VWX-016
- 검증 방법: `server/tests/test_vwx_rig.py`
- 기대 결과:
  - ① 동일 `unit_number`를 가진 서로 다른 두 행이 last-write-wins로 조용히 병합되지 않고 둘 다 충돌 목록에 남는다.
  - ② `unit_number`가 모두 공란인 서로 다른 픽스처는 대체 조인키(채널명)를 시도하고, 그것도 실패하면 충돌로 보고한다.

### AC-VWX-017 — VW 자체 충돌 분류 통과 (M4)

The 시스템 **shall** Vectorworks 자체 패치 충돌 분류를 구조화된 부류로 통과시킨다.

- 대상 요구사항: REQ-VWX-017
- 검증 방법: `server/tests/test_vwx_rig.py`
- 기대 결과:
  - ① `Patch overlap`·`Identical Patch`·`Patch conflict` 셋이 서로 다른 코드값으로 분류되며 예외를 던지지 않는다.
  - ② 세 부류 어느 것도 발생하지 않는 정상 파일에서 이 필드가 빈 목록으로 존재한다(비공허성).

### AC-VWX-018 — 조인 키 = 주소+타입, `FID`/`CID` 금지 (M5)

The 대조기 **shall not** 대조 조인 키로 `FID` 또는 `CID`를 사용한다.

- 대상 요구사항: REQ-VWX-018
- 검증 방법: `server/tests/test_vwx_diff.py`
- 기대 결과:
  - ① 슬롯과 FID가 우연히 일치하는 합성 콘솔 실측 리그에서, 설계상 리그의 `fixture_id`/`uid` 유사 컬럼 값을 조작해도 대조 결과가 변하지 않는다(조인 키가 실제로 주소+타입임을 증명 — 시나리오 4).
  - ② 대조기 소스에서 `fixture_id`/`uid` 필드를 조인 비교 연산자 피연산자로 쓰는 지점이 AST 스캔으로 **0건**이다(비공허성 — 스캔이 실제로 식별자를 방문했음을 함께 확인).

### AC-VWX-019 — `FID`/`CID` 구조화된 미수행 (M5)

The 대조기 **shall** `FID`/`CID` 대조 불가를 `SkippedCheck` 동형 구조로 명시한다.

- 대상 요구사항: REQ-VWX-019
- 검증 방법: `server/tests/test_vwx_diff.py`
- 기대 결과:
  - ① 모든 대조 실행 결과에 `skipped_checks` 목록이 존재하고 `fid_cid_identity_unreachable` 부류가 **항상** 포함된다(조건부가 아니라 본 SPEC 범위에서는 상시 미수행).
  - ② 그 항목이 자유 산문 문자열만으로 존재하지 않고 고정 코드 + `reason` 필드의 구조를 갖는다.

### AC-VWX-020 — 대조 리포트 3부류 (M5)

The 대조 리포트 **shall** `missing_in_console`·실제 `address_collision`·`quantity_mismatch` 3부류를 싣는다.

- 대상 요구사항: REQ-VWX-020
- 검증 방법: `server/tests/test_vwx_diff.py`
- 기대 결과:
  - ① 도면에만 있는 픽스처가 `missing_in_console`에 열거된다(콘솔 실측에 대응 항목 없음).
  - ② 콘솔 실측이 이미 아는 주소 중복이 대조 리포트에도 반영된다(`precheck_patch`의 판정을 재사용, 재계산하지 않는다).
  - ③ 도면 수량과 콘솔 관측 수량이 타입별로 다른 경우 `quantity_mismatch`에 타입·도면수·콘솔수가 함께 열거된다.
  - ④ 3부류 전부가 항상 응답에 존재한다(비어 있어도 포함 — 비공허성).

### AC-VWX-021 — 옵션 구간 겹침 재사용 (M5)

**Where** `DMX Footprint` 폭 출처가 확보되면, the 대조기 **shall** `_range_overlaps`를 재사용해 구간 겹침을 판정한다.

- 대상 요구사항: REQ-VWX-021
- 검증 방법: `server/tests/test_vwx_diff.py`
- 기대 결과:
  - ① `FootprintPolicy(enabled=True)`가 주입되고 도면에 `DMX Footprint` 값이 있으면 구간 겹침이 판정된다.
  - ② 주입되지 않으면 이 축은 `skipped_checks`에 미수행으로 기록되고 예외를 던지지 않는다(REQ-VWX-019와 동형 구조 재사용을 확인).

### AC-VWX-022 — 구조화된 페이로드 (M6)

The 대조 리포트 **shall** 판독 실패·데이터블록 미탐·미수행·부정 전제를 구조화된 페이로드 부류로 담는다.

- 대상 요구사항: REQ-VWX-023
- 검증 방법: `server/tests/test_vwx_report.py`
- 기대 결과:
  - ① 4종(판독 실패·데이터블록 미탐·미수행·부정 전제) 각각이 최상위 리포트 키에 독립적으로 존재한다.
  - ② Python 예외 traceback 문자열이 사용자 대면 필드에 노출되는 지점이 0건이다(비공허성 — 정상 케이스에서 각 필드가 빈 목록으로 존재).
  - ③ **(v0.1.3 — kind 열거에서 불변식으로 재설계)** **설계상 리그 픽스처가 0대이면**(트리거 무관 — 판독 실패든 파일 내부 조인키(`unit_number`/`channel`) 충돌로 전 행이 탈락한 경우든 그 밖의 원인이든) `diffs`는 `missing_in_console`/`address_collision`/`quantity_mismatch` 빈 배열 3종을 **생략**하고 `{"performed": false, "reason": …}` 형태로만 존재한다 — "찾아봤는데 없다"(빈 배열)와 "애초에 수행하지 않았다"(미수행)를 구조적으로 구별한다. `reason`은 실제 원인을 지목한다(판독 실패 사유 · 조인키 충돌 상세 · 그 밖의 경우 방어적 폴백 문구). 정상 대조(픽스처 ≥1)에서는 `{"performed": true, ...}` + 기존 3키가 그대로 유지된다(비공허성 — 정상 케이스에서 `performed: true` + 3키가 실제로 존재함을 함께 확인).

### AC-VWX-023 — 한국어 표현 계층 (M6)

사용자 대면 문자열 **shall** 한국어이며 라벨 재사용은 `report.py`의 공개 접근자를 통한다.

- 대상 요구사항: REQ-VWX-024
- 검증 방법: `server/tests/test_vwx_report.py`
- 기대 결과:
  - ① **(v0.1.1 — run-phase 확정 설계로 갱신)** 신규 판정 부류(`missing_in_console` 등)가 `server/vwx/report.py`의 독립 닫힌 어휘 레지스트리 `VWX_CLOSED_VOCABULARIES`에 등재되고 동일 파일의 라벨 표에 대응 한국어 라벨을 갖는다(키 집합 정확히 일치). `server/prechk/verdicts.py`의 공유 `CLOSED_VOCABULARIES`는 **건드리지 않는다** — 시도 시 기존 `test_prechk_verdicts.py`/`test_prechk_report.py`의 정확-집합 assert가 깨짐이 실측으로 확인됐다(`progress.md` M6). 이 변경으로 `verdicts.py`도 PRESERVE 0-diff에 포함된다(spec.md §C 갱신).
  - ② 밑줄 식별자(내부 라벨 딕셔너리)를 본 SPEC의 신규 코드가 직접 import하는 지점이 AST 스캔으로 **0건**이다(비공허성 — 스캔이 실제 코드 트리를 방문했음을, 임시로 밑줄 식별자 직접 import를 심어 스캔이 잡아내는지 확인 후 되돌리는 방식으로 함께 assert한다).
  - ③ **(v0.1.3 — kind 열거에서 불변식으로 재설계)** `summary_ko()`는 대조가 성립하지 않을 때(위 AC-VWX-022 ③ 불변식 조건 — 픽스처 0대) **"차이 없음"이라는 문구를 절대 포함하지 않는다** — 대신 실제 원인으로 문장을 시작한다(판독 실패 경로: "패치 출처로 성립하지 않는다 — …. 대조를 수행하지 않았다." · 조인키 충돌 경로: "조인 키 충돌 N건으로 설계상 리그를 세우지 못했다 — …. 대조를 수행하지 않았다."). 정상 대조(픽스처 ≥1, 차이 없음)에서는 "차이 없음" 문구가 그대로 등장한다(비공허성 — 판독 실패·조인키 충돌·정상 3경로 모두 실제로 검증해 문자열 검사기가 살아 있음을 증명한다).

### AC-VWX-024 — 툴 배선 · 콘솔 실측 경유 · 경계 (M6)

신규 툴 **shall** 기존 실행 경로의 호출자이며 `server.bridge`를 직접 import하지 않는다.

- 대상 요구사항: REQ-VWX-022 · REQ-VWX-025
- 검증 방법: `server/tests/test_vwx_tool.py`, 기존 `server/tests/test_architecture.py`
- 기대 결과:
  - ① 툴 등록 4지점(`TOOL_NAMES`·핸들러·`definitions`·`handlers`) 전부에 등재되며 **디스패치**로 확인한다(dict 조회만으로 확인하지 않는다).
  - ② `server/vwx/` 어느 파일도 `server.bridge`·`pythonosc`를 직접 import하지 않는다(기존 `_FORBIDDEN_MODULE_PREFIXES` 테스트가 통과).
  - ③ 콘솔 실측 데이터가 `read_inventory` 또는 `build_patch_sheet` 호출을 경유함을 대역 모킹으로 확인한다.
  - ④ 신규 REST 라우트·웹소켓 메시지·`execution_port` 직접 접근이 AST 스캔으로 **0건**이다(비공허성 — 스캔이 실제 트리를 방문했음을, 임시로 REST 라우트 데코레이터 또는 `execution_port` 직접 호출을 심어 스캔이 잡아내는지 확인 후 되돌리는 방식으로 함께 assert한다).

### AC-VWX-027 — fixture_name·gdtf_fixture 정규 필드 승격 (M2)

The 컬럼 해석기 **shall** `Fixture Name`·`GDTF Fixture`를 정규 필드로 해석하고, 후자를 타입 퍼지 매칭에 우선 사용한다.

- 대상 요구사항: REQ-VWX-026
- 검증 방법: `server/tests/test_vwx_columns.py`, `server/tests/test_vwx_rig.py`
- 기대 결과:
  - ① `Fixture Name`/`FixtureName` 헤더가 `fixture_name`으로, `GDTF Fixture`/`GDTFFixture` 헤더가 `gdtf_fixture`로 해석된다 — `extra`에 남지 않는다.
  - ② `fixture_name`이 `symbol_name`과 다른 정규화 키를 가짐을 직접 assert한다(비공허성 — 합쳐지지 않았음을 증명).
  - ③ `gdtf_fixture`가 `mode`의 `GDTF Fixture Mode` 별칭과 다른 정규화 키를 가짐을 직접 assert한다(비공허성 — `gdtffixture` vs `gdtffixturemode`).
  - ④ `DesignedFixture.match_type`이 `gdtf_fixture`가 있으면 그것을, 없으면 `instrument_type`을 반환한다(비공허성 — 두 경로 모두 검증).

### AC-VWX-028 — 주소 3중 표현 교차검증 (M3)

**Where** `Universe`·`DMX Address`·`Absolute Address`가 모두 존재하면, the 주소 해석기 **shall** `absolute == (universe-1)*512+address`를 검증하고 불일치를 경고로 보고한다.

- 대상 요구사항: REQ-VWX-027
- 검증 방법: `server/tests/test_vwx_address.py`
- 기대 결과:
  - ① 세 표현이 일치하면(음성 대조군) 경고 없이 `Universe`+`DMX Address` 그대로 해석된다.
  - ② **불일치하면**(양성 케이스, 합성 픽스처) `address_triple_mismatch` 경고가 생성되고, 그럼에도 유니버스는 **Absolute Address로 역산되지 않는다** — `Universe`+`DMX Address` 조합 값이 그대로 유지됨을 직접 assert한다(추측 금지 원칙 준수).
  - ③ 경고가 있어도 레코드는 `resolved`에서 탈락하지 않는다(해석 성공 + 경고는 독립적인 축).

### AC-VWX-029 — 설계 측 구간 겹침 판정 (M5)

**Where** `DMX Footprint`가 해석되면, the 대조기 **shall** 설계 도면 내부에서 (유니버스,주소,폭)만으로 구간 겹침을 판정한다.

- 대상 요구사항: REQ-VWX-028
- 검증 방법: `server/tests/test_vwx_rig.py`, `server/tests/test_vwx_diff.py`, `server/tests/test_vwx_tool.py`
- 기대 결과:
  - ① stride == footprint(완벽 패킹, M0 실물 샘플과 동일 형태)이면 겹침 0건을 **필드로 명시**한다(생략이 아니다 — 비공허성).
  - ② **stride < footprint면**(양성 케이스, 합성 픽스처) 실제로 겹침이 잡힌다 — 겹침 판정 기능이 항상 빈 목록만 내지 않음을 직접 assert한다(비공허성 핵심).
  - ③ 서로 다른 유니버스 간에는 겹침이 오발동하지 않는다(비공허성 대조군).
  - ④ `DMX Footprint`가 없는 파일에서는 기존과 같이 미수행 + 사유(`footprint_overlap_descope`)로 보고된다(회귀 확인).
  - ⑤ 설계 측 판정이 수행됐으면 콘솔 측 폭 주입(2차 작업)이 의도적으로 미뤄졌다는 별도 미수행 판정(`console_footprint_width_injection_deferred`)이 `skipped_checks`에 남는다.
  - ⑥ VW 자체 다중패치(정확히 같은 시작 주소)는 이 판정으로 실패시키지 않는다 — 기존 `vw_patch_conflicts` 규약과 독립적으로 공존한다(회귀 확인).

### AC-VWX-025 — 회귀 · PRESERVE (M7)

본 SPEC **shall not** PRESERVE 목록을 변경하며 기존 스위트를 깨지 않는다.

- 대상 요구사항: 형상 전체(단일 REQ 아님)
- 검증 방법: `git diff --stat <BASE>..HEAD -- <목록>` + 전체 스위트 + `ruff`
- 기대 결과:
  - ① PRESERVE 목록 diff가 빈 출력이다(단, `server/prechk/verdicts.py`는 순수 추가 hunk만 허용). `<BASE>..HEAD` 범위는 협상 불가 — 인자 없는 `git diff`는 커밋 직후 항상 빈 출력이라 게이트가 무력해진다.
  - ② 게이트 자체의 비공허성을 증명한다 — PRESERVE 목록의 파일에 공백을 주입해 커밋하면 게이트가 적발하고, revert 후 다시 빈 출력이 된다.
  - ③ 전체 스위트 신규 실패 0건. baseline은 이 마일스톤이 착수 직전 직접 실측하며 이월 인용 금지.
  - ④ `ruff check` / `format --check`가 본 SPEC의 신규·변경 파일에서 clean이다.

### AC-VWX-026 — 종단 검증 (M8, 라이브 아님)

**When** 완성된 대조 파이프라인을 M0 실물 샘플로 실행하면, the 시스템 **shall** 판독-정규화-대조-보고 전 구간의 통합을 보인다.

- 대상 요구사항: **(종단 통합 — §B 시나리오 전체). 단일 REQ 아님.**
- 검증 방법: 완성된 툴을 통한 종단 실행(라이브 콘솔 접속 없음 — M0 샘플 + 기존 검증된 콘솔 실측 대역).
- 기대 결과:
  - ① M0가 확보한 실물 파일이 예외 없이 판독되어 설계상 리그 모델을 산출한다.
  - ② 그 모델이 기존 `precheck_patch` 실측 대역과 대조되어 3부류 리포트를 낸다.
  - ③ `skipped_checks`에 FID/CID 미수행이 항상 포함된다.
  - ④ 우회 경로(내부 함수 직접 호출)가 아니라 **툴을 통해** 실행됐음을 확인한다.

---

## §D. 퇴화 · 경계 케이스 — 특수 분기를 만들지 않는다

| 케이스 | 정의된 결과 |
|---|---|
| 도면 픽스처 **0개**(파일이 비어 있음) | 거부가 아니라 정상이다. `missing_in_console` 0건 · `quantity_mismatch` 0건. 다만 "관측 픽스처 0개" 사실을 리포트에 싣는다 |
| 콘솔 실측 픽스처 **0개** | 도면의 전 픽스처가 `missing_in_console`로 열거된다(정상 결과) |
| 도면·콘솔 **완전 일치** | 3부류 전부 빈 목록이며 `summary_ko`가 "차이 없음"류 문구를 낸다 |
| `Device Type` 컬럼 자체가 없는 파일 | 액세서리 필터링을 수행하지 않고 그 축소를 명시(AC-VWX-014 ③) |
| `Part Index` 컬럼 자체가 없는 파일 | 폴딩을 수행하지 않고(대상이 없으므로 자연 결과) 1:1 반영이 곧 정답이다 |
| `openpyxl` 미승인 상태에서 `.xlsx` 파일 제공 | 판독 실패 + 사유 "미승인 의존성"(§D Out of Scope와 코드가 대조 가능) |

---

## §E. 품질 게이트

| 게이트 | 기준 |
|---|---|
| 전체 스위트 | 신규 실패 **0건**. baseline은 각 마일스톤이 착수 직전 직접 실측(이월 인용 금지) |
| PRESERVE | 목록 diff 빈 출력(`verdicts.py` 순수 추가 예외) + 게이트 비공허성 증명(AC-VWX-025 ②) |
| 뮤테이션 | 각 마일스톤이 지정한 뮤테이션 전건 killed |
| 비공허성 | 모든 "0건" 스캔에 비어 있지 않음 assert 동반 |
| AST 스캔 | 경계·`==` 직접 비교 검증은 raw grep이 아니라 AST 식별자 스캔이며 스캔이 식별자를 모았음을 함께 assert |
| 라이브 | **0회**(`plan.md` §C가 근거를 적는다) |
| 마커 | clarification 마커 **0건** · 축약 토큰 **0건** |

---

## §F. Definition of Done

**(v0.1.4 갱신 — REQ 25→28·AC 26→29. 3행 status 줄과의 자기모순을 바로잡음. 코디네이터 검증 중 발견.)**

1. AC-VWX-001~029 **29건 전량 PASS**(§C.0a 마일스톤 배정 합 29와 일치).
2. REQ-VWX-001~028 **28건 전량** 커버(§C.0 "REQ 28/28 커버, 누락 0"과 일치).
3. `ASSUMPTION-68`~`70` **3건 전부 판정 확정**. **아직 참이 아니다** — `68`은 v0.1.4에서 NEGATIVE로 해소됐지만 `69`(Absolute Address 단독 파일)·`70`(경로 B 워크시트)은 M0가 PARTIAL에 머물러 있는 한 미해소다. 이 항목은 **M8이 실제로 닫혀야 참이 되는 DoD**다 — M8이 BLOCKED인 현재는 이 조건이 미충족이며, 그것이 SPEC 전체가 아직 완결이 아닌 이유 그 자체다(`progress.md` §E.2 M0 절 참조).
4. `openpyxl` 신규 의존성 승인 여부가 `progress.md`에 기록되고, 미승인 시 §D의 `.xlsx` 축소가 실제 코드 사유 문자열과 일치. **(충족됨 — 승인 확정, `progress.md` Implementation Kickoff Approval 절)**
5. PRESERVE diff 빈 출력(`server/prechk/**` 8개 파일 전량, `verdicts.py` 포함 완전 0-diff) + 게이트 비공허성 증명.
6. 전체 스위트 0 failed · `ruff` clean(신규·변경 파일).
7. CHANGELOG · frontmatter · `progress.md` §E.1~§E.4가 갱신.
