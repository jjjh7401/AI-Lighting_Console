---
id: SPEC-COPILOT-VWX-001
title: "Vectorworks 연계 1단계 — Instrument Data CSV/엑셀 가져오기 + 설계상 리그 모델 + precheck_patch 대조 리포트"
version: "0.1.3"
status: draft
created: 2026-08-05
updated: 2026-08-05
author: manager-spec
priority: P0
phase: "Phase 3 이후 차별화 기능 — P0 신설 항목(Vectorworks 연계 1단계, 자동 패치·MVR은 후속 SPEC으로 분리)"
module: "server/vwx/ (신규), server/orchestrator/tools.py (수정), server/prechk/ (재사용·무변경), server/paperwork/ (재사용·무변경), pyproject.toml (의존성 조건부 1건: openpyxl)"
lifecycle: spec-anchored
tags: "vectorworks, csv, excel, instrument-data, precheck, rig, import"
tier: L
related_specs: [SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-OVERLAP-001]
---

# SPEC-COPILOT-VWX-001 — Vectorworks 연계 1단계 — Instrument Data CSV/엑셀 가져오기 + 설계상 리그 모델 + precheck_patch 대조 리포트

> **본 SPEC은 `.moai/reports/ma3-copilot-overview.html` §7의 P0 항목**(원문 인용): *"P0. Vectorworks 연계 — 디자인 도면을 콘솔 셋업으로. Vectorworks Spotlight에서 확정한 조명 디자인(장비 종류·수량·패치·배치)을 그대로 가져와 콘솔 셋업의 출발점으로 씁니다. 세 단계로 나누면: 1단계 — 엑셀/CSV 장비 리스트 가져오기: Vectorworks가 내보내는 Instrument Data(픽스처 타입·수량·유니버스·주소·포지션)를 읽어 '설계상 리그' 모델을 만듭니다. 이미 있는 공연 전 점검(precheck_patch)과 붙이면 '도면 vs 실제 콘솔 패치' 차이 리포트가 바로 나옵니다 — 빠진 장비, 주소 충돌, 수량 불일치를 공연 전에 잡습니다. 2단계 — 자동 패치 생성: 차이 리포트에서 사람이 승인하면, 라이브 검증이 끝난 Lua 패치 기법(AddFixtures)으로 부족한 픽스처를 콘솔에 자동 패치합니다. 3단계 — MVR/GDTF 가져오기: MVR 파일(3D 배치+GDTF 장비 정의)을 파싱하면 무대 위 실제 좌표까지 확보됩니다."*
>
> **본 SPEC은 1단계만을 범위로 한다.** 2단계(자동 패치)와 3단계(MVR/GDTF)는 §D가 명시적으로 배제하고 후속 SPEC으로 분리한다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-05 | manager-spec | 최초 작성 (draft, Tier L). 출처는 `.moai/reports/ma3-copilot-overview.html` §7 P0 항목. **아티팩트 6종**(spec/plan/acceptance/design/research/progress). REQ **25건**, AC **26건**, ASSUMPTION **3건**(68~70), 마일스톤 **9개**(M0~M8), 라이브 세션 **0회**(§C가 근거를 적는다), clarification 마커 **0건**. Vectorworks 형식 조사(경로 A/B, 인코딩, 컬럼 별칭표, 주소 표현, 7가지 대조 함정)는 `research.md`가 소유. **승인 대기 1건** — 신규 의존성 `openpyxl` 채택 여부(§C, `plan.md` 사용자 접점). |
| 0.1.1 | 2026-08-05 | (run-phase worker) | **Implementation Kickoff Approval 확정.** `openpyxl` 신규 의존성 **승인** — 경로 B `.xlsx` 지원을 v1 범위에 포함(§C 갱신, §D `.xlsx` 조건부 Out-of-Scope 절 무효화 명시). 실물 Vectorworks export 샘플은 **여전히 미제공** — M0는 완료 처리하지 않고 BLOCKED로 유지, M1~M7은 합성 픽스처(문서 근거·실물 미검증)로 선행 진행한다(`progress.md` §E.2). |
| 0.1.2 | 2026-08-05 | (run-phase worker) | **실물 파일 투입이 드러낸 P0 결함 2건 수정 + 잔존 지적 1건 교정.** 결함 1(CR 전용 줄바꿈 예외 탈출)·결함 2(패치 출처 아닌 파일에 "이상 없음" 오발) 최초 수정 후, 결함 2의 핵심(사용자가 읽는 `summary_ko` 문장이 여전히 "차이 없음"으로 시작하던 거짓 안전 신호)이 잔존한다는 재현이 들어와 교정했다. `REQ-VWX-023` 문구를 이 규칙을 명시하도록 갱신(§B), `AC-VWX-022`/`AC-VWX-023`에 대응 기대 결과 각 1건 추가(비공허성 포함). 코드 변경 상세는 `progress.md` §E.2 이번 라운드 기록. |
| 0.1.3 | 2026-08-05 | (run-phase worker) | **거짓 안전 신호 3라운드째 — kind 열거를 불변식으로 대체.** v0.1.2의 미수행 판정이 `read_failures`의 특정 kind 2종(`not_patch_source`·`worksheet_block_undetected`)에만 걸려 있어, 그 목록에 없는 새 경로(주소 열은 있어 판독 자체는 성공하지만 `unit_number`/`channel`이 전부 공란이라 `join_key_conflicts`로 전 행이 탈락하는 경우 — `read_failures`는 빈 튜플)에서 정확히 같은 거짓 안전 신호가 다시 샜다(코디네이터 재현). `REQ-VWX-023`을 "설계상 리그 픽스처 0대 = 대조 미수행" **불변식**으로 재정의해 트리거 목록 열거 방식을 폐기했다 — 이제 원인이 무엇이든(판독 실패·조인키 충돌·그 밖의 무엇이든) 픽스처 0대이면 동일하게 처리된다. 기존 두 read_failure 경로의 사유 문구는 그대로 유지(회귀 테스트로 검증). |

---

## A. 개요

**한 줄**: Vectorworks가 내보내는 Instrument Data(엑셀/CSV/tab-text)를 읽어 **설계상 리그(designed rig)** 모델을 만들고, 이미 있는 `precheck_patch`(콘솔 실측)와 대조해 **"도면 vs 실제 콘솔 패치"** 차이 리포트를 낸다 — 빠진 장비, 주소 충돌, 수량 불일치를 공연 전에 잡는다.

본 SPEC은 **읽고 대조만** 한다. 콘솔에 아무것도 쓰지 않는다 — 자동 패치(2단계)와 MVR/GDTF 좌표 확보(3단계)는 §D가 명시적으로 배제한다.

### 사전 확정 사실 (조사 확정 — 재질의 금지)

1. **Vectorworks export는 하나의 포맷이 아니라 두 경로다.** (A) `File > Export > Export Instrument Data` — **tab-delimited text 전용**(csv도 xlsx도 아니다), 헤더 존재 여부는 체크박스로 선택적이며 `UID` 열이 자동 추가된다. (B) `File > Export > Export Worksheet`(Instrument Data 워크시트에서) — `.xls/.xlsx/.txt(tab)/.csv/.dif/.slk`를 낼 수 있으나 파일 자체가 **워크시트 그리드**(제목행 + DB 헤더행 + 개체별 서브행 + 소계행이 한 파일에 섞임)다. 사용자의 "CSV/엑셀" 표현은 경로 B를 가리킨다(`research.md` §1). 파서는 **확장자만으로 구분자를 단정하지 않는다.**
2. **`Instrument Summary`는 패치 출처가 아니다.** 도면 오브젝트 썸네일·수량용 리포트이며 **주소 열이 아예 없다**(`research.md` §1). 발견되면 거부한다.
3. **FID/CID 기반 픽스처 아이덴티티 대조는 이 단계에서 원리적으로 불가능하다.** `server/prechk/inventory.py:57 PROPERTY_WHITELIST`는 `Patch`·`FixtureType`·`Mode`·`Name` 4종만 읽고, 콘솔 슬롯과 FID가 우연히 일치하는 캘리브레이션 쇼파일에서는 **올바른 FID 프로브와 슬롯 프로브를 구별할 수 없다**(`console/lua/PROTOCOL.md:305-324`, `server/rulebook/assets/v2.4.2/20_korean_terms.md:34-36`, `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:203-209`). 따라서 본 SPEC의 대조 조인 키는 **(유니버스, 주소) + 픽스처 타입**이며, ID 대조는 `SkippedCheck`/`not_performed` 구조로 명시한다(REQ-VWX-018, REQ-VWX-019) — 숨기지 않는다.
4. **실물 Vectorworks export 샘플이 이 저장소에 없다.** 저장소 전체 grep에서 `.gitignore`의 `.Spotlight-V100` 노이즈와 무관한 문자열 일치 외에는 아무것도 없다(`research.md` §0). **컬럼 계약은 실물 파일 없이 동결하지 않는다** — M0가 사용자 제공 실물 export를 선행조건으로 요구한다(§C).

### 조사가 확립한 제약 — 본 SPEC이 이 위에 선다

1. **주소는 콘솔의 단일 `<유니버스>.<주소>` 표기와 달리 Vectorworks가 4가지 동시 표현을 갖는다** — `Universe/Address`(구분자 가변, 기본 `/`, 무제로패딩) · `Universe`(정수) · `DMX Address`(1..512) · `Absolute Address`(`(u-1)*512+a`, **Universes 창이 연속 기본 512블록일 때만** 안전하다). `DMX Address`/`Absolute Address`가 `0`이거나 공란이면 **"미패치"**이며, 이것은 "콘솔에 없음"과 다른 **제3의 분류**다(`research.md` §Address).
2. **컬럼 헤더는 별칭 테이블로만 해석한다.** 같은 값이 파일 버전에 따라 `U Dimmer`/`User U Address`/`DMX Address`/`User Address` 등 여러 철자로 나타난다(`research.md` §Address). 위치 기반 파싱은 금지한다.
3. **대조에는 7가지 알려진 함정이 있다** — 멀티셀 픽스처, 액세서리 오분류, 타입/모드 명칭 불일치, 미패치 오분류, 파일 내부 조인키 중복, Vectorworks 자체 패치 충돌 통과, 멀티시스템(A-Z) 유니버스 혼동(`research.md` §Pitfalls). 각각 REQ로 승격했다.
4. **인코딩은 문서화되어 있지 않다.** BOM 스니프를 우선하고, 실패 시 순차 폴백하며, 모지바케를 조용히 삼키지 않는다(`research.md` §Encoding).

---

## B. 요구사항 (GEARS)

### B.1 가져오기 (Import)

- **REQ-VWX-001** `[Ubiquitous]` The 가져오기 파서 **shall** Vectorworks **경로 A**(`Export Instrument Data`, tab-delimited text) 파일을 판독한다. 헤더 존재 여부는 첫 행의 별칭 테이블 매칭 개수로 스니핑하며, 확장자를 구분자 판단에 쓰지 않는다.
- **REQ-VWX-002** `[Ubiquitous]` The 가져오기 파서 **shall** Vectorworks **경로 B**(`Export Worksheet`, xls/xlsx/txt/csv) 파일에서 **데이터 블록을 구조적으로 식별**한다 — 별칭 테이블 컬럼명을 2개 이상 해석 가능한 첫 행을 헤더 후보로 삼고, 그 아래 컬럼 수가 연속으로 일치하는 구간만 레코드로 채택한다. 문서화된 구획 마커는 존재하지 않는다(`research.md` §Path B).
- **REQ-VWX-003** `[Unwanted]` The 가져오기 파서 **shall not** `Instrument Summary` 리포트(주소 열이 없는 요약)를 패치 출처로 채택한다. 발견 시 판독 실패로 분류하고 사유를 리포트에 싣는다.
- **REQ-VWX-004** `[Event-driven]` **When** 파일 인코딩이 불확실하면, the 가져오기 파서 **shall** BOM 스니프 → `utf-8-sig` → `utf-16` → `cp1252` → `mac_roman` 순으로 판독을 시도하고, 전부 실패하면 **바이트 오프셋과 함께 명시적으로 실패**한다 — 모지바케 상태로 조용히 통과시키지 않는다.

### B.2 컬럼 해석과 정규화

- **REQ-VWX-005** `[Ubiquitous]` The 컬럼 해석기 **shall** 대소문자·공백·구두점을 무시하는 **별칭 테이블**로 컬럼을 매칭한다(`research.md`의 별칭표가 정본). 위치(순번) 기반 매칭은 금지한다.
- **REQ-VWX-006** `[Ubiquitous]` The 컬럼 해석기 **shall** 별칭 테이블 밖의 컬럼을 폐기하지 않고 레코드의 `extra` 딕셔너리에 원문 그대로 보존한다.
- **REQ-VWX-007** `[Event-driven]` **When** 레코드가 최소 유효 조건(`instrument_type` + 해석 가능한 주소 표현 하나)을 만족하지 못하면, the 컬럼 해석기 **shall** 그 레코드를 **구조화된 판독 실패**로 분류하고 판정에 쓰지 않는다 — 예외를 던지지 않는다.

### B.3 주소 처리

- **REQ-VWX-008** `[Event-driven]` **When** `DMX Address` 또는 `Absolute Address`가 `0`이거나 공란이면, the 주소 해석기 **shall** 그 픽스처를 **"설계됨·미배정"**으로 별도 분류한다 — "콘솔에 없음"(대조 단계의 결과)과 혼동하지 않는다.
- **REQ-VWX-009** `[Where]` **Where** 파일이 `Universe`/`DMX Address` 쌍 컬럼을 갖지 못해 `Absolute Address` 단일값에서 유니버스·주소를 파생해야 하고 **그 파일의 Universes 창이 연속 기본 512블록이라는 전제가 검증 가능할 때만**, the 주소 해석기 **shall** `abs=(u-1)*512+a` 역산을 수행한다. 전제를 검증할 수 없으면 파생을 수행하지 않고 판독 실패로 분류한다(추측 금지).
- **REQ-VWX-010** `[Event-driven]` **When** 파일에서 System 문자(A-Z) 2개 이상이 관측되면, the 주소 해석기 **shall** 순수 `Universe` 정수 컬럼만으로의 해석을 **모호로 차단**하고 그 사유를 리포트에 명시한다 — 임의로 추측하지 않는다.
- **REQ-VWX-011** `[Ubiquitous]` The 주소 해석기가 산출하는 정규화 표현(유니버스 정수, 주소 정수)은 `server/prechk/patch.py:118 normalize_address`가 산출하는 `AddressParse`와 **동일한 표현 규약**을 따른다 — 값을 재사용하는 것이 아니라 표현 형태(정수 튜플)를 일치시켜 대조 단계(§B.5)가 하나의 비교 로직만 갖게 한다.

### B.4 설계상 리그(designed rig) 모델

- **REQ-VWX-012** `[Ubiquitous]` The 시스템 **shall** 파싱된 레코드를 정규화하는 **설계상 리그(designed rig)** 도메인 모델을 생성한다 — 콘솔 슬롯 대응이 아니라 도면이 선언한 장비 목록의 구조화된 표현이다.
- **REQ-VWX-013** `[Event-driven]` **When** 동일 픽스처의 여러 셀/액세서리 행이 `Part Index` 컬럼으로 관측되면, the 시스템 **shall** 대조 전에 **논리적 픽스처 1개로 접는다** — 셀 N행 = 픽스처 1대는 정상이며 위양성 수량 불일치로 세지 않는다.
- **REQ-VWX-014** `[Ubiquitous]` The 시스템 **shall** `Device Type` 컬럼으로 Light-class와 비-DMX Static Accessory를 대조 계수 이전에 **필터링**한다. Static Accessory는 콘솔 패치 대상이 아니다.
- **REQ-VWX-015** `[Unwanted]` The 시스템 **shall not** Vectorworks 타입·모드 표시 문자열과 콘솔 타입·모드 표시 문자열을 **동등 비교(`==`)**로 판정한다. 별칭·퍼지 매칭을 쓰고, 해결되지 않으면 **미해결 표시**를 판정에 남긴다 — 둘의 명명 체계는 서로 다른 소스에서 온다.
- **REQ-VWX-016** `[Event-driven]` **When** 파일 내부에서 조인 키(`unit_number` 또는 `channel`)가 중복이거나 공란인 레코드가 2개 이상이면, the 시스템 **shall** 자동 last-write-wins 병합을 **거부**하고 그 충돌을 판독 실패로 보고한다.
- **REQ-VWX-017** `[Ubiquitous]` The 시스템 **shall** Vectorworks 자체 패치 충돌 분류(Patch overlap · Identical Patch · Patch conflict)를 **판정 실패로 만들지 않고 구조화된 부류로 통과**시킨다 — MA3의 `Multipatch` IDType과 동형으로 취급한다.

### B.5 precheck_patch 대조

- **REQ-VWX-018** `[Unwanted]` The 대조기 **shall not** 대조 조인 키로 `FID` 또는 `CID`를 사용한다. 조인 키는 **(유니버스, 주소) + 픽스처 타입**에 한정한다(§A 사전 확정 사실 3).
- **REQ-VWX-019** `[Ubiquitous]` The 대조기 **shall** `FID`/`CID` 기반 아이덴티티 대조가 이 쇼파일로 원리적으로 수행 불가함을 `server/prechk/patch.py:188 SkippedCheck`와 동형인 **`not_performed` 구조**로 명시한다 — 산문으로 흘리지 않는다.
- **REQ-VWX-020** `[Ubiquitous]` The 대조 리포트 **shall** 최소 3부류를 싣는다 — ① 도면에는 있으나 콘솔에 없는 장비(missing_in_console), ② 실제 주소 충돌(콘솔 실측 기준), ③ 도면·콘솔 간 수량 불일치. 각 부류는 관여 항목 전량을 열거한다(집계만 내지 않는다).
- **REQ-VWX-021** `[Where]` **Where** 도면에서 `DMX Footprint` 폭 출처가 확보되면, the 대조기 **shall** `server/prechk/patch.py:440 _range_overlaps`를 재사용해 **구간 겹침** 확장 판정을 수행한다(`FootprintPolicy.enabled=True`로 주입). 확보되지 않으면 이 축은 미수행으로 보고한다(REQ-VWX-019와 같은 구조).
- **REQ-VWX-022** `[Ubiquitous]` The 대조기 **shall** 콘솔 실측 데이터를 `server/prechk/inventory.py:344 read_inventory` 또는 `server/paperwork/data.py:67 build_patch_sheet`를 통해서만 얻는다. 신규 모듈은 `server.bridge`를 **직접 import하지 않는다**.

### B.6 보고 · 경계

- **REQ-VWX-023** `[Ubiquitous]` The 대조 리포트 **shall** 판독 실패·데이터 블록 미탐·미수행 판정·부정 전제를 모두 **구조화된 페이로드 부류**로 담는다 — 예외 산문으로 흘리지 않는다. **(v0.1.3 — 불변식으로 재정의)** **설계상 리그 픽스처가 0대이면 대조를 수행한 것이 아니다** — 트리거가 판독 실패(주소 열 없음·데이터 블록 미탐)이든, 파일 내부 조인키(`unit_number`/`channel`) 충돌로 전 행이 탈락한 경우이든, 그 밖의 어떤 원인으로 픽스처가 0대가 되든 동일하게 적용된다. 이때 `diffs`는 빈 배열 3종이 아니라 `performed: false` + 실제 원인을 지목하는 사유로 미수행임을 구조적으로 드러내며, `summary_ko`는 "차이 없음"을 말하지 않고 그 사유로 시작한다 — 대조를 수행하지 않은 상태를 "찾아봤는데 없다"로 오독시키지 않는다. **트리거는 kind 목록 열거가 아니라 픽스처 수 0건이라는 결과로 판정한다** — 특정 kind에만 매칭하는 방식은 목록에 없는 새 경로(조인키 충돌 등)에서 반드시 새기 때문이다(`progress.md` §E.2 v0.1.3 라운드).
- **REQ-VWX-024** `[Ubiquitous]` 사용자 대면 문자열 **shall** 한국어이며 표현 계층 코드에 둔다. 라벨 재사용은 `server/prechk/report.py:143 label()`의 공개 접근자를 통하며 밑줄 식별자를 직접 import하지 않는다.
- **REQ-VWX-025** `[Ubiquitous]` The 신규 대조 리포트 툴 **shall** `server/orchestrator/tools.py`의 **`TOOL_NAMES`·핸들러 클로저·`definitions`·`handlers`** 전 지점에 등재되며, 신규 REST 라우트·웹소켓 메시지·`execution_port` 직접 접근을 **0건**으로 유지한다.

---

## C. 환경 및 전제

### 측정된 기준선

착수 SHA **`b1a630eb9380fd37436252e366289350bd22feff`**에서 **직접 실측**한 값은 `uv run pytest server/tests -q` → **4716 passed · 7 skipped · 1 warning · 91.35s(0:01:31)**다. 각 마일스톤은 착수 직전 직접 실측하며 이월 인용을 금지한다.

### 미검증 전제 (ASSUMPTION)

번호는 선행 SPEC 이후를 이어받는다(GROUPGEN이 `ASSUMPTION-67`까지 썼다, `.moai/specs/SPEC-COPILOT-GROUPGEN-001/spec.md:324`).

- **ASSUMPTION-68** — **별칭 테이블의 실효성.** `research.md`가 열거한 별칭 테이블(instrument_type, symbol_name, mode, footprint, channel, unit_number, position, universe_address, universe, address, absolute_address, system, dimmer, circuit_number/name, color, device_type, layer, uid, fixture_id 등)이 **실물 Vectorworks export 파일의 실제 헤더와 합치하는가.** M0가 사용자 제공 실물 샘플로 판정한다. **본 SPEC의 컬럼 계약 동결을 막는 유일한 전제다** — 부정(또는 부분 GO)이면 별칭 테이블을 실물 헤더로 확장하고 그 확장분을 `progress.md`에 기록한다(테이블 확장은 계약 위반이 아니라 계약이 예정한 조정이다 — 별칭 매칭 규약 자체(REQ-VWX-005)는 불변).
- **ASSUMPTION-69** — **`Absolute Address` 단일값만 있는 파일의 존재.** 실물 파일이 `Universe`/`DMX Address` 쌍을 항상 함께 제공하는가, 아니면 `Absolute Address` 단일값만 제공하는 파일이 실제로 존재하는가. **동작 축소 — 블로킹 아님**: 부정(쌍 컬럼이 항상 있음)이면 REQ-VWX-009의 역산 경로는 방어적으로 존재하되 실행되지 않는다. GO(단일값 파일이 존재)면 그 경로가 M0 샘플로 검증된다.
- **ASSUMPTION-70** — **경로 B(워크시트 export) 데이터 블록의 구조적 식별 가능성.** 헤더가 없거나 소계행이 섞인 실물 워크시트 export에서 REQ-VWX-002의 "별칭 매칭 2개 이상인 첫 행 + 컬럼 수 연속 구간" 휴리스틱이 실제로 데이터 블록을 정확히 잘라내는가. **동작 축소 — 블로킹 아님**: 부정이면 경로 B는 "Recalculate worksheet"·"Export field names as first record" 체크박스를 사용자가 명시적으로 켠 파일만 지원하고, 그 제약을 리포트와 사용자 안내에 명시한다. 우회(추측으로 블록을 자르는 것)는 금지한다.

> **FID/CID의 의미는 ASSUMPTION이 아니다.** `console/lua/PROTOCOL.md:322-324`가 슬롯 ≠ FID로 패치된 쇼파일을 검증 조건으로 명시하며, 그것은 선행 SPEC(PRECHK)이 이미 구조적으로 배제하고 출하한 사실이다(`.moai/specs/SPEC-COPILOT-PRECHK-001/spec.md` §C). 본 SPEC은 그 판정을 재측정하지 않고 **조인 키 설계로 그 필요 자체를 우회한다**(REQ-VWX-018) — 새 라이브 프로브를 열지 않는다(라이브 세션 회계는 `plan.md` §C 소유이며 0회다).

### 신규 의존성 — **승인 확정 (v0.1.1)**

**경로 B의 `.xlsx` 바이너리 포맷 지원은 신규 의존성(`openpyxl`)을 요구한다.** 기존 `pyproject.toml`의 런타임 의존성은 `anthropic`·`fastapi`·`google-genai`·`keyring`·`lupa`·`python-osc`·`pyyaml`·`uvicorn`·`websockets` 9건이며 CSV/Excel 파싱 라이브러리가 **0건**이었다(직접 확인). `.xls/.txt/.csv`는 표준 라이브러리(`csv`, 텍스트 판독)로 충분하지만 `.xlsx`는 아니다. **Implementation Kickoff Approval에서 사용자가 채택을 승인했다** — `openpyxl`을 `pyproject.toml` 런타임 의존성에 추가하고, 경로 B의 `.xlsx`를 v1 범위에 **포함**한다. §D의 조건부 Out-of-Scope 절("`.xlsx` 바이너리 지원(신규 의존성 미승인 시)")은 이 승인으로 **무효화**된다.

### PRESERVE — 무변경 대상

`console/lua/**` · `server/safety/**` · `server/prechk/{__init__,inventory,patch,report,verdicts,footprint,macro,query}.py`(8개 파일 전량, 본 SPEC은 **소비만** 한다; `verdicts.py`는 신규 부류 순수 추가만 예외) · `server/paperwork/{data,render,output}.py`(소비만 한다) · `server/looks/**` · `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 실행/dedupe 루프 · `server/rulebook/assets/v2.4.2/**`.

> **`server/prechk/**`를 PRESERVE로 두는 근거(plan-audit 지적 반영 — 8개 파일 전량 잠금).** 본 SPEC의 대조 절반(콘솔 실측 측)은 이미 라이브 검증된 `read_inventory`/`evaluate_patch`/`build_patch_sheet`를 그대로 소비한다 — 재구현하지 않는다. `footprint.py`/`macro.py`/`query.py`/`__init__.py`는 본 SPEC이 직접 호출하지 않는 무관 기능이지만, PRESERVE 게이트가 파일 단위가 아니라 **디렉터리 단위**로 명확하도록 8개 파일 전량을 명시한다. **run-phase에서 실제로 확정된 설계(당초 계획보다 더 안전한 결과, `progress.md` §E.2 M6 기록 참조): 신규 판정 어휘를 `server/prechk/verdicts.py`의 공유 `CLOSED_VOCABULARIES`에 추가하지 않는다.** 시도 결과 `verdicts.py`/`report.py`의 기존 테스트(정확한 집합을 assert)가 깨졌기 때문이다 — 대신 `server/vwx/report.py`가 **독립된** 닫힌 어휘 레지스트리(`VWX_CLOSED_VOCABULARIES` + `vwx_label()`)를 동일한 패턴(닫힌 집합 + 라벨표 + 미등록 코드에 예외를 던지는 접근자)으로 자체 소유한다. 이로써 `verdicts.py`도 **순수 추가 예외 없이 완전 0-diff**가 된다(당초 계획의 "순수 추가만 허용" 예외보다 엄격). 게이트 검증: `git diff --stat <BASE>..HEAD -- server/prechk/__init__.py server/prechk/inventory.py server/prechk/patch.py server/prechk/report.py server/prechk/footprint.py server/prechk/macro.py server/prechk/query.py server/prechk/verdicts.py`가 **8개 파일 전부** 빈 출력이어야 한다 — 예외 없음.

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — Lua `AddFixtures` 자동 패치

**제안서 원문의 2단계다.** 차이 리포트에서 사람이 승인한 뒤 라이브 검증된 `AddFixtures` 기법으로 콘솔에 자동 패치하는 것은 **본 SPEC의 산출물이 아니다.** 본 SPEC은 차이를 **읽고 보고**만 한다. 콘솔에 대한 `exec` 발화는 0건이다. 후속 SPEC(2단계)이 본 SPEC의 대조 리포트를 입력으로 받는다.

- 본 SPEC이 만드는 차이 리포트를 소비해 자동 패치를 수행하는 코드는 0건이다.
- `console/lua/**`의 `AddFixtures` 관련 로직은 PRESERVE이며 본 SPEC이 호출하지 않는다.

### Out of Scope — MVR/GDTF 가져오기

**제안서 원문의 3단계다.** MVR 파일(3D 배치 + GDTF 장비 정의) 파싱과 무대 좌표 확보는 본 SPEC 범위가 아니다. MVR/GDTF는 SPATIAL/GROUPGEN이 이미 구축한 공간 인식 계층과의 결합이 필요하며 별도 SPEC이 다룬다.

- 본 SPEC은 `.mvr` 확장자 파일을 다루지 않는다.
- GDTF 장비 정의 파싱 코드는 0건이다.

### Out of Scope — 도면 이미지 자동 반영

Vectorworks 도면의 시각적 이미지(플롯·뷰포트 렌더)를 자동으로 가져와 반영하는 것은 범위 밖이다. 좌표 정밀도가 없는 참고 자료일 뿐이며 본 SPEC의 패치 대조와 무관하다.

- 이미지·PDF·플롯 파일을 파싱하는 코드는 0건이다.

### Out of Scope — FID/CID 기반 픽스처 아이덴티티 대조

§A·§C가 근거를 적었다 — 현재 쇼파일로는 원리적으로 불가능하다. 본 SPEC은 이 축을 열지 않고 `SkippedCheck` 구조로 명시한다(REQ-VWX-019). 슬롯 ≠ FID로 패치된 쇼파일이 준비되면 후속 SPEC이 이 축을 연다.

- 본 SPEC이 `FID`/`CID` 값을 대조 조인 키로 사용하는 코드는 0건이다(REQ-VWX-018).
- 슬롯≠FID 검증용 신규 라이브 프로브를 여는 코드는 0건이다(`plan.md` §C).

### Out of Scope — 패치 자동 재배치·충돌 해소

본 SPEC은 대조하고 보고한다. 차이가 발견되어도 콘솔 패치를 옮기거나 도면을 수정하지 않는다. 자동 재배치는 물리 배선 정책을 요구하는 별도 산출물이다.

- 콘솔에 `exec` 발화를 보내 패치를 옮기거나 재배치하는 코드는 0건이다.
- 도면 파일을 되쓰는(write-back) 코드는 0건이다.

### Out of Scope — `.xlsx` 바이너리 지원(신규 의존성 미승인 시) — **v0.1.1: 무효화됨**

**이 절은 §C의 승인으로 무효화됐다.** `openpyxl`이 승인되어 경로 B의 `.xlsx` 형식은 v1 범위에 **포함**된다. 이 절은 승인 전 조건부 축소 규칙이 실제로 무엇이었는지 감사 가능하도록 기록으로만 남긴다 — 승인 전에는 `.txt(tab)`·`.csv`(텍스트 기반 워크시트 export)만 지원하고 `.xlsx` 파일을 판독 실패("미승인 의존성")로 분류하는 규칙이었다.

- `.xlsx` 파서를 바이트 단위로 자체 구현(우회)하는 코드는 여전히 0건이다 — `openpyxl` 표준 API만 사용한다.

---

## E. 참조 구현

| 참조 | 좌표 | 무엇을 계승하는가 |
|---|---|---|
| 주소 정규화 계약 | `server/prechk/patch.py:118 normalize_address` | (유니버스, 주소) 정수 튜플 표현 규약 — 값이 아니라 형태를 일치 |
| 콘솔 실측 인벤토리 | `server/prechk/inventory.py:344 read_inventory` | 콘솔측 대조 입력의 단일 진입점, 화이트리스트 프로퍼티 읽기 |
| 콘솔 실측 패치 시트 | `server/paperwork/data.py:67 build_patch_sheet` | 재사용 가능한 실측 표(대안 소스) |
| 구간 겹침 판정 | `server/prechk/patch.py:440 _range_overlaps` | `FootprintPolicy` 주입 시 재사용(REQ-VWX-021) |
| 닫힌 판정 어휘 + 한국어 라벨 | `server/prechk/verdicts.py:52`, `server/prechk/report.py:143 label()` | 신규 부류를 순수 추가하는 확장 패턴 |
| 아키텍처 경계 | `server/tests/test_architecture.py:48 _FORBIDDEN_MODULE_PREFIXES` | 신규 `server/vwx/`가 `server.bridge`·`pythonosc`를 직접 import하지 않는 강제 |
| 툴 등록 4지점 패턴 | `server/orchestrator/tools.py:127,1986,4317,5134`(`precheck_patch` 등록 좌표) | `TOOL_NAMES`·핸들러·`definitions`·`handlers` 등재 절차 |
