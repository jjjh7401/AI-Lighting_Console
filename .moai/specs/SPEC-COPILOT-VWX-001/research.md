# SPEC-COPILOT-VWX-001 — 조사 기록 (research)

status: draft (v0.1.0, 2026-08-05) · Tier L · 본 문서는 **읽기 전용 정적 조사(저장소) + Vectorworks 공식 문서 조사**의 기록이다. 라이브 콘솔 관측은 0건이다(본 SPEC은 콘솔에 쓰지 않으며, 대조 절반은 이미 라이브 검증된 `precheck_patch`를 재사용한다).

> **참조 규약** (PRECHK research.md의 규약을 계승한다). 본 SPEC의 정본(spec.md · acceptance.md)은 **줄번호로 인용하지 않는다** — `REQ-VWX-nnn` · `AC-VWX-nnn` · `ASSUMPTION-nn` · 절 제목 같은 **안정 토큰**만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. **요구·인수 토큰은 예외 없이 슬러그를 포함한 완전형으로만 쓴다.** 근거 등급은 `[코드]` · `[문서]` · `[Vectorworks 문서]` · `[미확정]`으로 구분 표기한다. `[실측]`은 이 문서에서 쓰지 않는다 — 라이브 콘솔 세션이 0회이기 때문이다.

---

## 0. 출처와 실물 샘플 부재

**출처**: `.moai/reports/ma3-copilot-overview.html` §7 P0 항목("Vectorworks 연계"). 1단계는 "엑셀/CSV 장비 리스트 가져오기 → 설계상 리그 모델 → precheck_patch와 대조해 차이 리포트"다 `[문서]`.

**이 저장소에 실물 Vectorworks export 샘플이 없다.** 저장소 전체 grep(`Vectorworks`, `Instrument Data`, `.vwx`, `Spotlight`, `GDTF`, `MVR`) 결과는 `.gitignore`의 `.Spotlight-V100`(macOS 시스템 인덱스 디렉터리, 무관) 노이즈와 `server/tests/test_looks_schema.py`의 문자열 값 우연 일치 외에는 0건이다. **따라서 본 문서의 Vectorworks 형식 서술은 저장소 코드 조사가 아니라 Vectorworks 공식 도움말 문서 조사에 근거하며, 컬럼 계약은 M0의 실물 샘플로 검증되기 전까지 확정이 아니라 강력한 초안이다.**

---

## 1. 조사 방법과 그 한계

| 층 | 수단 | 산출물 | 한계 |
|---|---|---|---|
| 저장소 정적 조사 | grep + 관련 SPEC(PRECHK) 아티팩트 재사용 | 본 문서 §5·§6 | 콘솔 실측 재사용 계약만 확립. 신규 프로토콜 조사는 없음 |
| Vectorworks 공식 문서 조사 | WebFetch 3건(도움말 페이지) | 본 문서 §2·§3·§4 | 문서가 절차 기준(GUI 조작)이지 파일 포맷 스펙이 아니다. 실물 파일로만 최종 검증 가능 |

**Vectorworks 공식 도움말 URL 3건**(전부 검증됨):
1. `https://app-help.vectorworks.net/2018/eng/VW2018_Guide/Export/Exporting_Instrument_Data.htm` — Export Instrument Data(경로 A)
2. `https://app-help.vectorworks.net/2022/eng/VW2022_Guide/Worksheets/Exporting%20worksheets.htm` — Export Worksheet(경로 B)
3. `https://app-help.vectorworks.net/2023/eng/VW2023_Guide/LightingDesign2/Creating_an_instrument_summary.htm` — Instrument Summary(별개 기능, 패치 출처 아님)

---

## 2. 두 export 경로 — 하나의 포맷이 아니다

### 2.1 경로 A — `File > Export > Export Instrument Data`

- **tab-delimited text 전용**이다. csv도 xlsx도 아니다 `[Vectorworks 문서]`.
- 헤더 존재 여부는 `Export field names as first record` 체크박스로 **선택적**이다 — 즉 헤더 없는 파일이 정상 산출물일 수 있다.
- `UID`(Unique ID) 열이 **자동 추가**된다. 이것이 경로 A 파일에서 유일하게 안정적인 아이덴티티 컬럼이다(`fixture_id`는 별개, 네이티브 파라미터가 아니다).
- 이름이 "Instrument Data"라서 워크시트 export와 헷갈리기 쉽지만, **경로 A는 tab-text 고정이며 xlsx가 아니다.**

### 2.2 경로 B — `File > Export > Export Worksheet`("Instrument Data" 워크시트에서)

- 출력 형식: `.xls` / `.xlsx` / `.txt`(tab) / `.csv` / `.dif` / `.slk` `[Vectorworks 문서]`.
- **파일 자체가 워크시트 그리드**다 — 제목행 + 데이터베이스 헤더행 + 개체별 서브행 + 소계/요약행이 **한 파일에 섞여 있다.** 텍스트 형식(txt/csv)에는 이 구조를 구분할 문서화된 마커가 없다 — Excel 형식(xls/xlsx)에서는 회색 음영으로 시각적으로만 구분된다.
- **사용자의 "CSV/엑셀" 표현은 경로 B를 가리킨다.** 경로 A는 tab-text뿐이므로 "엑셀"이라 부를 산출물이 없다.
- `Recalculate worksheet prior to exporting` 체크박스가 있다 — 즉 **stale 데이터가 export될 수 있다.**

### 2.3 `Instrument Summary` — 별개 기능, 패치 출처 아님

`Instrument Summary`는 도면에 그려진 오브젝트의 **썸네일 + 수량** 요약이며 별도 Vectorworks 기능(`Creating an Instrument Summary`)이다 `[Vectorworks 문서]`. **주소 열이 아예 없다.** 패치 대조 출처로 오인하면 안 된다 — 가져오기 단계에서 구조적으로 거부해야 한다(REQ-VWX-003).

---

## 3. 컬럼 별칭 테이블 — 강력한 초안, M0로 검증 필요

Vectorworks Instrument Data 워크시트가 노출하는 컬럼은 버전마다 이름이 다르다. 아래는 Vectorworks 공식 문서와 일반적으로 알려진 필드 배치에 근거한 **별칭 테이블 초안**이다. 매칭은 대소문자·공백·구두점을 무시하며 **비위치 기반**이다.

| 정규 필드 | 별칭(대소문자·공백·구두점 무시) | 비고 |
|---|---|---|
| `instrument_type` | Instrument Type, InstrumentType, Type, Fixture Type | `Type`은 VW2020+에서 재명명됨 |
| `symbol_name` | Symbol Name, SymbolName | |
| `mode` | Fixture Mode, GDTF Fixture Mode, Mode | GDTF가 있으면 우선 |
| `footprint` | DMX Footprint, Num Channels, NumChannels | |
| `channel` | Channel, Chan, Ch | 숫자가 아닌 "채널 이름"일 수 있다 |
| `unit_number` | Unit Number, UnitNumber, Unit, U# | |
| `position` | Position, Hanging Position | Braceworks의 "load section" Position과 헤더명 충돌 주의 |
| `purpose` | Purpose | |
| `universe_address` | Universe/Address, Universe Address, Uni/Addr, U/A | 구분자 가변(`/` 기본, `.`·`-`·`:`도 관측됨) |
| `universe` | Universe, Uni | |
| `address` | DMX Address, U Address, UAddress, User U Address, U Dimmer, Addr | 1..512, `0`=미패치 |
| `absolute_address` | Absolute Address, Address, User Address, Abs Address | 단독 `"Address"`는 VW≤2019에서는 절대주소, 이후 버전은 `Universe`+`Address`가 함께면 모호 |
| `system` | System | 유니버스-시스템 문자(A-Z)와 조명감독 컨트롤 시스템 문자가 **같은 헤더명을 공유** — 값 도메인으로 구분 |
| `dimmer` | Dimmer, Dim | ≤2019 문서는 "dimmer 또는 DMX address"라 신뢰 불가한 주소 소스 |
| `circuit_number` | Circuit Number, Circuit #, Circuit | |
| `circuit_name` | Circuit Name | |
| `color` | Color, Colour, Gel | 다중 젤은 `+`로 결합될 수 있다 |
| `frame_size` / `focus` / `wattage` / `weight` | (각 자체 헤더) | 대조와 무관, `extra`로 보존. **문서-구현 정본 정리(v0.1.4)**: 이 4개는 `server/vwx/columns.py` `ALIAS_TABLE`(구현)에 실제로는 등록돼 있지 않다 — 등록 없이도 `extra`로 보존되는 동작은 동일하므로 기능 결함은 아니지만, "정규 필드 후보"였다는 이 표의 언급과 "실제 정규 필드 여부"는 별개다. **정본은 `ALIAS_TABLE`(구현)**이다 — 이 표는 조사 기록이지 구현 약속이 아니며, 이 4개를 정규 필드로 승격할지는 범위 밖 결정으로 남겨둔다. |
| `device_type` | Device Type, DeviceType | 액세서리 필터링 필수(REQ-VWX-014) |
| `layer` | Layer, Design Layer, Class | |
| `uid` | UID, Unique ID, EID, External ID, VW_ID | 경로 A의 자동 추가 컬럼 |
| `fixture_id` | Fixture ID, FixtureID, FID | **네이티브 VW 파라미터가 아니다** — 사용자/서드파티가 추가한 경우에만 존재. 존재하면 가치가 높으나 신뢰 전제는 M0가 판정 |

**문서화된 리네임 예**: VW2025 문서는 "U Dimmer가 User U Address로, Address가 User Address로 표시된다"(pre-2020 파일 기준)고 적는다 — 즉 **한 파일이 `DMX Address` + `U Address` + `User U Address` + `U Dimmer`를 같은 값의 네 철자로 동시에 가질 수 있다.**

**최소 유효 레코드** = `instrument_type` + 해석 가능한 주소 표현 하나. 그 미만은 구조화된 판독 실패다(REQ-VWX-007). 별칭 테이블 밖 컬럼은 폐기하지 않고 `extra`에 보존한다(REQ-VWX-006).

---

## 4. 주소 표현 — 4가지 동시 형식

Vectorworks는 **한 픽스처의 주소를 네 가지 컬럼으로 동시에** 노출할 수 있다.

| 표현 | 형태 | 신뢰도 |
|---|---|---|
| `Universe/Address` | 사용자 변경 가능한 구분자(기본 `/`, `.`·`-`·`:`도 관측), 무제로패딩 | 조합형 — 파싱 시 구분자 가변 처리 필요 |
| `Universe` | 정수, 시스템(A-Z)별 기본 255 유니버스 × 512 주소 | 단독으로는 시스템 모호(§5) |
| `DMX Address` | 1..512(유니버스 내 상대 주소) | `Universe`와 짝일 때 가장 신뢰 |
| `Absolute Address` | `abs=(u-1)*512+a`, **Universes 창이 연속 기본 512블록일 때만** 안전 | 사용자가 Start#/End#를 편집하거나 유니버스를 삭제하면 공식이 깨진다 |

**미패치 sentinel**: `DMX Address` 또는 `Absolute Address`가 `0`이거나 공란/누락이면 **미패치**다. 이것은 콘솔 대조 결과(`missing_in_console`)와 **다른 제3의 분류**("설계됨·미배정") — 절대주소 `1`로 정규화하지 않는다(REQ-VWX-008).

**멀티시스템 모호**: System 문자(A-Z)는 MA3에 대응 개념이 없다. 2개 이상의 System이 관측되면 `A.1`과 `B.1`이 같은 순수 `Universe 1`로 보일 수 있으므로 — 추측하지 않고 차단한다(REQ-VWX-010).

---

## 5. 인코딩 — 문서화되어 있지 않다

Vectorworks는 export 파일의 인코딩을 문서화하지 않는다. 안전한 폴백 순서(우선순위):

1. BOM 스니프(UTF-8/UTF-16 BOM 감지)
2. `utf-8-sig`
3. `utf-16`(Windows Excel tab export에서 흔함)
4. `cp1252`
5. `mac_roman`

전부 실패하면 **바이트 오프셋과 함께 명시적으로 실패**한다. 한국어 포지션명("무대 좌측" 등)이 조용히 깨지는 것을 방지한다(REQ-VWX-004).

---

## 6. 대조 7가지 함정

경로 B 파일은 구조화 마커 없는 워크시트 그리드이므로 데이터 블록 자체를 구조적으로 찾아야 한다(모드-길이 연속 구간 + 별칭 매칭 ≥2인 첫 행을 헤더 후보로). `Recalculate worksheet prior to exporting`는 체크박스이므로 stale 데이터 가능성이 있다.

| # | 함정 | 왜 발생하는가 | 흡수 설계 |
|---|---|---|---|
| ① | 멀티셀 픽스처 | VW는 셀/액세서리를 `Part Index`로 개별 행 패치한다. N행 = 픽스처 1대가 정상. 폴딩 없이 대조하면 위양성 수량 불일치 | 대조 전 접기(REQ-VWX-013) |
| ② | 액세서리 오분류 | `Device Type`이 Light-class / Static Accessory(비-DMX) / Accessory(DMX 소비)를 구분한다. 필터링 없이 세면 계수가 틀린다 | `Device Type` 사전 필터링(REQ-VWX-014) |
| ③ | 타입/모드 명칭 불일치 | VW `Fixture Mode`/`GDTF Fixture Mode`/`DMX Footprint` 3종 경쟁 소스, VW 모드명이 콘솔 라이브러리 모드명과 절대 문자열 일치하지 않는다, 값이 자주 공란 | `==` 금지, 별칭+퍼지 매칭, 미해결 표시(REQ-VWX-015) |
| ④ | 미패치 오분류 | `0`/공란을 "콘솔에 없음"과 합치면 두 서로 다른 상태가 뒤섞인다 | 제3의 분류(REQ-VWX-008) |
| ⑤ | 파일 내부 조인키 중복/공란 | 여러 unit_number/channel이 비어 있거나 중복이면 last-write-wins가 손실을 만든다 | 자동 병합 거부, 충돌 보고(REQ-VWX-016) |
| ⑥ | VW 자체 패치 충돌이 그대로 export에 흐른다 | VW는 Patch overlap(2개 이상 같은 주소) · Identical Patch(같은 universe+address+channel — "케이블 배선에 따라 문제가 아닐 수도 있음") · Patch conflict(같은 universe+address, 다른 channel)를 구분한다. MA3는 `Multipatch`가 1급 IDType이다 | 예외로 만들지 않고 구조화된 부류로 통과(REQ-VWX-017) |
| ⑦ | 멀티시스템 유니버스 혼동 | System 문자를 무시하고 순수 `Universe` 값만 병합하면 서로 다른 시스템의 같은 번호 유니버스가 충돌로 오판된다 | 모호 시 차단(REQ-VWX-010) |

---

## 7. 재사용 계약 — precheck_patch / paperwork

### 7.1 콘솔 실측은 재구현하지 않는다

콘솔측(대조의 "실제" 절반)은 PRECHK SPEC이 이미 라이브 검증한 경로를 그대로 소비한다.

| 재사용 대상 | 좌표 | 계약 |
|---|---|---|
| 인벤토리 진입점 | `server/prechk/inventory.py:344 read_inventory(port, policy) -> Inventory` | 화이트리스트 프로퍼티(`Patch`·`FixtureType`·`Mode`·`Name`, `server/prechk/inventory.py:57`)만 읽는다 |
| 패치 판정 진입점 | `server/prechk/patch.py:684 evaluate_patch(inventory, footprint=None, walk=None) -> PatchEvaluation` | 주소 중복·구간 겹침 판정을 재사용 가능 |
| 주소 정규화 | `server/prechk/patch.py:118 normalize_address(raw) -> AddressParse` | 콘솔 표기(`<유니버스>.<주소>`)의 정규화 계약 — 본 SPEC은 값이 아니라 **형태**를 일치시킨다 |
| 구간 겹침 | `server/prechk/patch.py:440 _range_overlaps(assessed, policy)` | `FootprintPolicy(enabled=True)` 주입 시 재사용(REQ-VWX-021) |
| 콘솔 실측 패치 시트(대안) | `server/paperwork/data.py:67 build_patch_sheet(port, *, policy=None) -> PatchSheet` | `PatchRow{slot,name,universe,address,patch_raw,fixture_type,mode}`(`server/paperwork/data.py:36`) |
| 닫힌 판정 어휘 | `server/prechk/verdicts.py:52 CLOSED_VOCABULARIES` | 신규 부류 순수 추가만 허용 |
| 한국어 라벨 접근자 | `server/prechk/report.py:143 label(vocabulary, code)` | 미등록 코드에 예외를 던지는 방어 패턴을 계승 |
| 아키텍처 경계 | `server/tests/test_architecture.py:48 _FORBIDDEN_MODULE_PREFIXES = ("server.bridge", "pythonosc")` | 신규 `server/vwx/`가 이 경계 밖에서 콘솔에 닿지 않도록 강제 |

### 7.2 순환 import 주의

`server.paperwork.data`가 `server.orchestrator.tools`를 import하므로(`build_patch_sheet`를 `tools.py`에서 쓰려면 함수 지역 지연 import가 필요하다) — `server/vwx/diff.py`가 `build_patch_sheet`를 대체 소스로 쓸 경우 동일한 지연 import 패턴을 따른다.

### 7.3 툴 등록 4지점

`precheck_patch`가 이미 확립한 등록 패턴을 그대로 따른다 — `TOOL_NAMES`(`server/orchestrator/tools.py:127`, 항목 `:136`) · 핸들러 클로저(`:1986`) · `ToolDefinition`(`:4317`) · `handlers` 맵(`:5134`, 항목 `:5143`). 검증은 dict 조회가 아니라 **디스패치**로 한다(선행 SPEC들의 확립된 테스트 패턴).

---

## 8. 기각한 대안

| # | 대안 | 기각 사유 |
|---|---|---|
| 1 | 확장자로 경로 A/B를 구분한다(`.txt`=A, `.xlsx`=B). | 경로 A도 `.txt`로 저장될 수 있고, 경로 B도 `.txt`/`.csv`로 export될 수 있다. 확장자는 구분자를 결정하지 않는다 |
| 2 | 컬럼을 위치(순번)로 파싱한다. | 별칭 테이블이 필요한 이유 자체가 컬럼 순서·이름이 버전마다 다르다는 사실이다 |
| 3 | `Absolute Address`를 기본 주소 소스로 삼는다. | Universes 창이 비연속이면 공식이 깨져 조용히 틀린 유니버스·주소를 낸다 |
| 4 | 슬롯 번호나 `fixture_id`를 대조 조인 키로 쓴다. | 슬롯==FID 우연일치 쇼파일에서 원리적으로 검증 불가능한 조인을 만든다(`console/lua/PROTOCOL.md:322-324`, PRECHK 선례) |
| 5 | 타입·모드 명칭을 동등 비교로 판정한다. | VW와 콘솔의 명명 체계가 서로 다른 소스이며 문서화된 대응표가 없다 |
| 6 | 콘솔 실측을 `server/vwx/`에서 재구현한다. | 이미 라이브 검증된 `read_inventory`/`evaluate_patch`를 재사용하지 않으면 두 구현이 드리프트한다 |
| 7 | M0 없이 `research.md`의 별칭 테이블만으로 컬럼 계약을 동결한다. | 이 테이블은 공식 문서 조사에 근거한 강력한 초안이지 실물 파일로 검증되지 않았다 |

---

## 9. 핵심 파일

| 파일 | 역할 | 본 SPEC과의 관계 |
|---|---|---|
| `server/prechk/inventory.py` | 콘솔 실측 인벤토리 | **소비만**. `read_inventory` 재사용 |
| `server/prechk/patch.py` | 주소 정규화 · 패치 판정 · 구간 겹침 | **소비만**. `normalize_address`·`_range_overlaps` 재사용 |
| `server/prechk/verdicts.py` | 닫힌 판정 어휘 | 신규 부류 순수 추가 |
| `server/prechk/report.py` | 한국어 라벨 접근자 | 재사용 패턴 계승 |
| `server/paperwork/data.py` | 콘솔 실측 패치 시트(대안 소스) | `build_patch_sheet` 재사용 가능 |
| `server/tests/test_architecture.py` | 아키텍처 경계 강제 | `server/vwx/`가 이 경계를 준수함을 검증 |
| `pyproject.toml` | 의존성 목록 | CSV/Excel 파싱 라이브러리 0건 확인. `openpyxl` 추가 여부가 승인 대상 |

---

## 10. 미해결로 남기는 것

### 10.1 M0가 소유하는 열린 판정 3건

| # | 항목 | 성격 |
|---|---|---|
| 1 | **별칭 테이블의 실효성**(`ASSUMPTION-68`) — 실물 헤더와의 합치 여부 | **블로킹** — 컬럼 계약 동결의 유일한 전제 |
| 2 | **`Absolute Address` 단일값 파일의 존재**(`ASSUMPTION-69`) | 동작 축소 — 블로킹 아님 |
| 3 | **경로 B 데이터 블록의 구조적 식별 가능성**(`ASSUMPTION-70`) | 동작 축소 — 블로킹 아님 |

### 10.2 사용자 승인이 필요한 것 1건

**`openpyxl` 신규 의존성 채택.** 현재 저장소에 CSV/Excel 파싱 라이브러리가 0건이며, `.xlsx` 지원은 이 의존성을 요구한다. 승인 절차는 `plan.md`의 사용자 접점이 소유한다.

### 10.3 이 단계에서 원리적으로 닫을 수 없는 것 1건

**`FID`/`CID` 기반 픽스처 아이덴티티 대조.** PRECHK SPEC이 이미 "슬롯==FID인 캘리브레이션 쇼파일로는 FID 프로브와 슬롯 프로브를 구별할 수 없다"를 실측으로 닫았다(`console/lua/PROTOCOL.md:322-324`, `.moai/specs/SPEC-COPILOT-PRECHK-001/spec.md` §C). 본 SPEC은 그 판정을 재측정하지 않고 조인 키 설계(REQ-VWX-018)로 그 필요 자체를 우회한다.
