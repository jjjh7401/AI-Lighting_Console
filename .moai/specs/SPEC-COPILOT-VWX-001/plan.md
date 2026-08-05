# SPEC-COPILOT-VWX-001 — 구현 계획 (plan)

status: draft (v0.1.0, 2026-08-05) · Tier L

> **v0.1.0 — 최초 작성.** 마일스톤 **M0~M8**(9개), 결정 등록부 **7건(A~G)**, 열린 결정 **0건**. 본 계획은 닫힌 정본 3종의 토큰 계약을 따른다: REQ 25건, AC 26건, ASSUMPTION 3건(68~70), 라이브 세션 **0회**. 마일스톤별 `- **AC**:` 줄은 `acceptance.md §C.0a`와 1:1이며, 합 **26 · 중복 0 · 누락 0**이다.
>
> **참조 규약.** 본 SPEC의 정본 3종은 줄번호로 인용하지 않고 `REQ-VWX-001`, `AC-VWX-001`, `ASSUMPTION-68` 같은 안정 토큰과 절 제목으로만 참조한다. 코드·룰북·응답기 프로토콜·타 SPEC 아티팩트는 `파일:줄` 좌표를 쓴다.

---

## §A. 맥락과 우선순위

가장 큰 위험은 코드 결함이 아니라 **실물 Vectorworks export 샘플의 부재**다(§A.2). 결정이 가장 자주 바뀔 수 있는 지점(데이터 모델·컬럼 계약)을 먼저 검토하도록 아래를 배치한다.

### §A.1 우선순위 매핑 — 제안서 P0 항목과 1단계 범위의 반영

| 우선순위 | 항목 | 계획 반영 |
|---|---|---|
| 1 | **가져오기 + 컬럼/주소 해석** — 두 export 경로, 별칭 테이블, 주소 4형식, 인코딩 | `REQ-VWX-001`~`REQ-VWX-011` |
| 2 | **설계상 리그 도메인 모델** — 멀티셀 폴딩, 액세서리 필터링, 타입/모드 퍼지 매칭, 조인키 충돌, VW 자체 충돌 통과 | `REQ-VWX-012`~`REQ-VWX-017` |
| 3 | **precheck_patch 대조** — 조인 키(주소+타입), FID/CID 구조화된 미수행, 3부류 리포트, 옵션 구간겹침 | `REQ-VWX-018`~`REQ-VWX-022` |
| 4 | **보고 · 툴 배선** — 구조화 페이로드, 한국어 표현, 툴 등록 4지점 | `REQ-VWX-023`~`REQ-VWX-025` |
| 제외 | **자동 패치(AddFixtures) · MVR/GDTF · 도면 이미지 반영 · 패치 재배치** | §D — 후속 SPEC |

### §A.2 빌드 순서 vs 리뷰 순서, 그리고 무엇이 무엇을 막는가

빌드 순서는 **M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8**이며 강한 순차 데이터 사슬이다(각 마일스톤이 앞 마일스톤의 산출을 입력으로 받는다). 리뷰는 아래 차단 표를 먼저 본다.

| 항목 | 막는 대상 | 성격 | 부정·미승인 시 처리 |
|---|---|---|---|
| **실물 Vectorworks export 샘플 부재** | **M1 이후 전체.** 샘플 없이 컬럼 계약을 동결하지 않는다 | **최대 위험.** 코드 착수 게이트 | M0가 사용자에게 요청·확보한다. 확보 전 M1 미착수 |
| **`openpyxl` 신규 의존성 승인 대기** | **M1의 `.xlsx` 분기만.** 텍스트 경로(`.txt`/`.csv`)는 막지 않는다 | 조건부 — 축소 가능 | 미승인이면 `.xlsx`는 v1 범위 밖(§D)으로 축소하고 M1은 텍스트 경로만 구현한다 |
| `ASSUMPTION-68`(별칭 테이블 실효성) | M2의 컬럼 계약 확정 | 동작 조정 — 블로킹 아님 | 부정/부분 GO면 별칭 테이블을 실물 헤더로 확장하고 확장분을 `progress.md`에 기록. 매칭 규약(REQ-VWX-005) 자체는 불변 |
| `ASSUMPTION-69`(Absolute Address 단일값 파일 존재) | 본 SPEC 마일스톤 없음(M3 내부 분기) | 동작 축소 — 블로킹 아님 | 부정이면 역산 경로는 방어적으로 존재하되 미실행 |
| `ASSUMPTION-70`(경로 B 데이터 블록 구조적 식별) | M1의 경로 B 자동 탐지만 | 동작 축소 — 블로킹 아님 | 부정이면 헤더 체크박스 활성 파일에 한정하고 그 축소를 리포트에 명시 |

#### M0 미완료 시 처리 지침

**하는 것**

- `progress.md`에 실물 샘플 확보 상태(부재/부분/완료)를 기록한다.
- 조사(`research.md`)가 이미 확립한 별칭 테이블·주소 4형식·7가지 함정을 근거로 M1~M6의 **코드 구조**는 설계할 수 있다. 다만 **테스트 fixture는 M0 샘플의 실제 헤더를 반영해야 하며**, 그 전에는 M1 완료로 표시하지 않는다.
- 오케스트레이터에게 본 SPEC의 최대 위험이 샘플 부재임을 다시 보고한다.

**하지 않는 것**

- 컬럼 별칭 테이블을 조사 문서만 근거로 **동결**하지 않는다 — `research.md`의 표는 강력한 초안이지 정본이 아니다. M0 샘플로 확인·확장한다.
- `Absolute Address` 단일값 파일이 존재한다고 가정하고 그 경로만 우선 구현하지 않는다 — `Universe`/`DMX Address` 쌍이 있으면 항상 그것을 우선한다(REQ-VWX-009).
- 워크시트(경로 B) 데이터 블록 경계를 추측으로 자르지 않는다 — 식별 실패는 판독 실패로 보고한다(REQ-VWX-002).

### §A.3 ASSUMPTION 부정 시 처리 지침

| 축 | M0/M1~M3 판정 대상 | 부정 시 정의된 결과 | 후속 |
|---|---|---|---|
| `ASSUMPTION-68` | 별칭 테이블 vs 실물 헤더 | 별칭 테이블 확장(계약 위반 아님). 확장 diff를 `progress.md`에 기록 | M2는 확장된 테이블로 계속 |
| `ASSUMPTION-69` | Absolute Address 단일값 파일 존재 여부 | 역산 경로 미실행 상태로 존재. 코드 삭제 없음 | M3 나머지 축(쌍 컬럼 경로)은 그대로 |
| `ASSUMPTION-70` | 경로 B 데이터 블록 구조적 식별 | 헤더 체크박스 활성 파일로 지원 범위 축소, 리포트에 명시 | M1 나머지(경로 A)는 그대로 |

### §A.4 결정 현황 — 해소 7건 / 열린 결정 0건

| 결정 | 이름 | 확정 내용 | 반영 마일스톤 |
|---|---|---|---|
| **A** | 신규 모듈 위치 | 신규 기능은 `server/vwx/`에 둔다. `server.bridge`를 직접 import하지 않고, 콘솔 실측은 `server/prechk/`·`server/paperwork/`의 공개 함수만 소비한다 | M1~M6 |
| **B** | 신규 의존성 채택 범위 | 승인 시 `.xlsx` 지원 추가(`pyproject.toml` 1건, `openpyxl`). 미승인 시 경로 B는 텍스트 기반(`.txt`/`.csv`)만 지원하고 `.xlsx`는 판독 실패("미승인 의존성")로 분류 | M1 |
| **C** | 대조 조인 키 정책 | (유니버스, 주소) + 픽스처 타입만 사용. `FID`/`CID`는 조인에 0건 | M5 |
| **D** | 판정 부류의 닫힌 집합 | `read_failure_kind`, `address_classification`(`patched`/`unpatched_designed`/`multi_system_ambiguous`), `diff_kind`(`missing_in_console`/`address_collision`/`quantity_mismatch`), `skipped_check_kind`(`fid_cid_identity_unreachable`/`footprint_overlap_descope`/`worksheet_block_undetected`)를 코드 상수로 닫는다 | M3, M4, M5, M6 |
| **E** | 멀티셀·액세서리 처리 정책 | `Part Index` 폴딩과 `Device Type` 필터링을 대조 이전 고정 단계로 둔다(설계상 리그 모델 생성 시점) | M4 |
| **F** | 라이브 세션 회계 | **0회.** `server/prechk/`가 이미 검증한 콘솔 읽기를 재사용하고 신규 FID/CID 라이브 프로브를 열지 않는다(§C가 근거를 적는다) | 전 마일스톤 |
| **G** | 리포트 스키마 | 최상위 키는 `designed_rig`, `console_rig`(재사용), `diffs`(`missing_in_console`/`address_collision`/`quantity_mismatch`), `skipped_checks`, `read_failures`, `summary_ko`다 | M5, M6 |

**열린 결정은 0건이다.** `ASSUMPTION` 부정이나 승인 거부가 새 질문을 만들 수는 있지만, 그것은 이 등록부의 빈칸이 아니라 §A.3의 정의된 결과가 흡수한다.

### §A.5 PRESERVE 재확인

| 항목 | 계획 방침 |
|---|---|
| `console/lua/**` | 콘솔 발화 0건 — 본 SPEC은 읽고 대조만 한다. 응답기 변경 0건 |
| `server/safety/**` | 신규 초크포인트 확장 없음 — 기존 `read_inventory`/`build_patch_sheet` 경로만 소비한다 |
| `server/prechk/{inventory,patch,report}.py` | 소비만 한다. `verdicts.py`만 신규 부류 순수 추가를 허용한다(결정 D) |
| `server/paperwork/{data,render,output}.py` | 소비만 한다. `build_patch_sheet`가 대안 실측 소스다 |
| `server/looks/**` | 룩 계층 소비자가 아니다. 변경 0건 |
| `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 실행/dedupe 루프 | 신규 툴이 이 루프를 재호출하는 것이 아니라(콘솔 발화가 없으므로) 독립 판독-대조 경로다. 기존 루프는 무변경 |
| `server/rulebook/assets/v2.4.2/**` | 참조하지 않는다. 콘솔 발화가 없으므로 리터럴 매크로 문법이 불필요하다 |

---

## §B. 마일스톤 M0~M8

각 마일스톤은 착수 직전 baseline을 직접 잰다. 계약 baseline의 4716 passed · 7 skipped · 1 warning 값은 BASE 기록일 뿐, run-phase 마일스톤 baseline으로 이월하지 않는다.

### M0 — 실물 Vectorworks export 샘플 확보 (cycle_type=none — 확보 세션, 코드 변경 0)

- **요구·설계 지시**: 사용자에게 실물 Instrument Data export 파일을 요청·확보한다(가능하면 경로 A tab-text 1개 + 경로 B 워크시트 export 1개 이상). 확보된 파일의 실제 헤더를 별칭 테이블과 대조해 `ASSUMPTION-68`을 판정(GO/부분GO/NEGATIVE)한다. 인코딩(BOM 등)·경로 A/B 구분·헤더 유무를 기록한다. `ASSUMPTION-69`·`ASSUMPTION-70`은 확보된 파일의 실제 컬럼 구성으로 판정 방향을 확인한다(최종 판정은 M3/M1 테스트가 닫는다).
- **baseline**: 코드 baseline 없음. 착수 직전 실물 샘플 보유 여부를 직접 확인한다(조사 시점엔 0건이었다, `research.md` §0).
- **뮤테이션**: ① 실물 샘플 없이 컬럼 계약을 동결하고 M1을 진행하면 `AC-VWX-001`이 죽어야 한다. ② 별칭 테이블 대조 없이 `ASSUMPTION-68`에 GO를 기록하면 `AC-VWX-001`이 죽어야 한다.
- **파일**: 코드 변경 0. 기록은 `progress.md` M0 절. 확보한 샘플 파일은 `.moai/state/verify/vwx-m0/`(`.gitignore` 대상)에 두고 원문 헤더를 `progress.md`에 요약 없이 전재한다.
- **AC**: AC-VWX-001.

### M1 — 파일 판독 + 인코딩 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-VWX-001`~`REQ-VWX-004`를 구현한다. `server/vwx/reader.py` 신설 — 경로 A/B 판별, 인코딩 폴백 체인, `Instrument Summary` 거부. `openpyxl` 승인 여부(결정 B)에 따라 `.xlsx` 분기 존재/부재가 갈린다.
- **baseline**: 착수 직전 전체 스위트 실측 + M0 확보 샘플 존재 확인.
- **뮤테이션**: ① 확장자만으로 구분자를 정하면 `AC-VWX-002`/`AC-VWX-003`이 죽어야 한다. ② `Instrument Summary`를 패치 출처로 채택하면 `AC-VWX-004`가 죽어야 한다. ③ 인코딩 실패 시 조용히 깨진 문자열을 통과시키면 `AC-VWX-005`가 죽어야 한다.
- **파일**: 신규 `server/vwx/__init__.py`, `server/vwx/reader.py`; 테스트 `server/tests/test_vwx_reader.py`; 조건부 `pyproject.toml`(승인 시 `openpyxl` 1건 추가).
- **AC**: AC-VWX-002, AC-VWX-003, AC-VWX-004, AC-VWX-005.

### M2 — 컬럼 해석 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-VWX-005`~`REQ-VWX-007`을 구현한다. `server/vwx/columns.py` — 별칭 테이블(정본은 `research.md`, `ASSUMPTION-68` GO/확장 결과를 반영), `extra` 보존, 최소 유효 레코드 판정.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① 위치 기반 매칭을 쓰면 `AC-VWX-006`이 죽어야 한다. ② `extra` 필드를 버리면 `AC-VWX-007`이 죽어야 한다. ③ 최소 조건 미달 레코드에서 예외를 던지면 `AC-VWX-008`이 죽어야 한다.
- **파일**: 신규 `server/vwx/columns.py`; 테스트 `server/tests/test_vwx_columns.py`.
- **AC**: AC-VWX-006, AC-VWX-007, AC-VWX-008.

### M3 — 주소 처리 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-VWX-008`~`REQ-VWX-011`을 구현한다. `server/vwx/address.py` — 미패치 sentinel, `Absolute Address` 조건부 역산(`ASSUMPTION-69`), 멀티시스템 차단(`ASSUMPTION-70`과 독립된 결정), `normalize_address` 표현 일치.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① `0`/공란을 "콘솔에 없음"과 합치면 `AC-VWX-009`가 죽어야 한다. ② 연속 512 블록 전제 확인 없이 절대주소를 역산하면 `AC-VWX-010`이 죽어야 한다. ③ 멀티시스템 파일에서 임의 유니버스를 추측하면 `AC-VWX-011`이 죽어야 한다. ④ 정규화 표현이 `AddressParse`와 다른 형태를 가지면 `AC-VWX-012`가 죽어야 한다.
- **파일**: 신규 `server/vwx/address.py`; 테스트 `server/tests/test_vwx_address.py`.
- **AC**: AC-VWX-009, AC-VWX-010, AC-VWX-011, AC-VWX-012.

### M4 — 설계상 리그 모델 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-VWX-012`~`REQ-VWX-017`을 구현한다. `server/vwx/rig.py` — 도메인 모델, `Part Index` 멀티셀 폴딩, `Device Type` 액세서리 필터링, 타입/모드 퍼지 매칭, 조인키 충돌 거부, Vectorworks 자체 충돌 분류 통과.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① 도메인 모델 생성 없이 원시 레코드를 그대로 대조로 넘기거나 `Part Index` 폴딩을 생략하면 `AC-VWX-013`이 죽어야 한다. ② `Static Accessory`를 계수에 포함하면 `AC-VWX-014`가 죽어야 한다. ③ 타입/모드를 `==`로 비교하면 `AC-VWX-015`가 죽어야 한다. ④ 중복 조인키를 last-write-wins로 병합하면 `AC-VWX-016`이 죽어야 한다. ⑤ Vectorworks 자체 충돌을 예외로 던지면 `AC-VWX-017`이 죽어야 한다.
- **파일**: 신규 `server/vwx/rig.py`; 테스트 `server/tests/test_vwx_rig.py`.
- **AC**: AC-VWX-013, AC-VWX-014, AC-VWX-015, AC-VWX-016, AC-VWX-017.

### M5 — precheck_patch 대조 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-VWX-018`~`REQ-VWX-022`를 구현한다. `server/vwx/diff.py` — 조인 키 (유니버스,주소)+타입, `FID`/`CID` `SkippedCheck` 동형, 3부류 리포트, 옵션 구간겹침(`_range_overlaps` 재사용), 콘솔 실측은 `read_inventory`/`build_patch_sheet` 경유.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① `FID`/`CID`를 조인 키에 쓰면 `AC-VWX-018`이 죽어야 한다. ② `FID`/`CID` 미수행을 산문으로만 적으면 `AC-VWX-019`가 죽어야 한다. ③ 3부류 중 하나를 생략하면 `AC-VWX-020`이 죽어야 한다. ④ `FootprintPolicy` 미주입 상태에서 구간겹침을 판정하면 `AC-VWX-021`이 죽어야 한다.
- **파일**: 신규 `server/vwx/diff.py`; 테스트 `server/tests/test_vwx_diff.py`.
- **AC**: AC-VWX-018, AC-VWX-019, AC-VWX-020, AC-VWX-021.

### M6 — 보고 + 툴 배선 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-VWX-022`(콘솔 실측 경유 재확인)~`REQ-VWX-025`를 구현한다. `server/vwx/report.py` + `server/orchestrator/tools.py` 신규 툴 1종(`precheck_vectorworks_diff`) + `server/prechk/verdicts.py`에 신규 판정 부류 순수 추가. 현재 `precheck_patch`의 등록 좌표는 `TOOL_NAMES`(`server/orchestrator/tools.py:127`, 항목 `:136`) · 핸들러(`server/orchestrator/tools.py:1986`) · `ToolDefinition`(`server/orchestrator/tools.py:4317`) · `handlers` 맵(`server/orchestrator/tools.py:5134`, 항목 `:5143`)이며 동형 4지점에 신규 툴을 추가한다.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① 구조화 페이로드 대신 산문 예외를 던지면 `AC-VWX-022`가 죽어야 한다. ② 한국어 라벨을 밑줄 식별자 직접 import로 가져오면 `AC-VWX-023`이 죽어야 한다. ③ 툴 등록 4지점 중 하나를 빼거나 `execution_port`를 직접 호출하면 `AC-VWX-024`가 죽어야 한다.
- **파일**: 신규 `server/vwx/report.py`; 수정 `server/orchestrator/tools.py`, `server/prechk/verdicts.py`(순수 추가); 테스트 `server/tests/test_vwx_report.py`, `server/tests/test_vwx_tool.py`.
- **AC**: AC-VWX-022, AC-VWX-023, AC-VWX-024.

### M7 — 회귀 · PRESERVE (cycle_type=tdd)

- **요구·설계 지시**: 신규 파일 0. 전체 스위트, 신규·변경 파일 lint/format check, PRESERVE diff, 게이트 비공허성 증명을 검증한다. diff 범위는 `<BASE>..HEAD`이며 인자 없는 `git diff`로 대체하지 않는다.
- **baseline**: 착수 직전 전체 스위트 실측. `<BASE>`는 run-phase kickoff가 기록한 SHA를 쓴다.
- **뮤테이션**: ① PRESERVE 목록 파일에 임시 변경을 주입하면 게이트가 적발해야 하고 되돌리면 다시 빈 출력이어야 한다. ② `<BASE>..HEAD`를 인자 없는 diff로 바꾸면 절차가 실패해야 한다. ③ `console/lua/**` 또는 `server/prechk/{inventory,patch,report}.py`를 수정하면 `AC-VWX-025`가 죽어야 한다.
- **파일**: 신규 파일 0. 기존 테스트와 diff gate만 사용한다. 기록은 `progress.md` M7 절.
- **AC**: AC-VWX-025.

### M8 — 종단 검증 (cycle_type=none — 검증 세션, 코드 변경 0)

- **요구·설계 지시**: M0가 확보한 실물 Vectorworks 샘플과, 기존에 검증된 콘솔 실측 경로(`precheck_patch`)의 인메모리 대역 또는 이전 SPEC이 남긴 실측 기록을 완성된 툴로 종단 실행한다. **새 라이브 grandMA3 세션은 열지 않는다**(§C).
- **baseline**: 코드 baseline은 M7의 검증 결과가 최종이다.
- **뮤테이션**: ① 툴을 거치지 않고 내부 함수를 직접 호출해 검증하면 `AC-VWX-026`이 죽어야 한다.
- **파일**: 코드 변경 0. 기록은 `progress.md` M8 절.
- **AC**: AC-VWX-026.

---

## §C. 라이브 세션 회계

라이브 세션은 **0회**다. 이것은 검토하지 않고 생략한 것이 아니라 **적극적으로 0으로 결정**한 것이다.

| 근거 | 설명 |
|---|---|
| 콘솔측 실측은 이미 검증됨 | `read_inventory`/`build_patch_sheet`는 PRECHK SPEC이 실물 grandMA3 onPC 2.4.2에서 이미 라이브 검증했다(`.moai/specs/SPEC-COPILOT-PRECHK-001/acceptance.md` AC-PRECHK-017). 본 SPEC은 그것을 **소비**할 뿐 재검증하지 않는다 |
| FID/CID 재프로브를 열지 않는다 | PRECHK가 "슬롯==FID인 쇼파일로는 FID 의미를 판별할 수 없다"를 실측으로 이미 닫았다(`console/lua/PROTOCOL.md:322-324`). 재측정해도 같은 결론만 나오고, 본 SPEC의 조인 키 설계(`REQ-VWX-018`)가 그 결과에 애초에 의존하지 않는다 — 새 프로브는 **아무것도 바꾸지 않는다** |
| M0는 파일 확보이지 콘솔 접속이 아니다 | 실물 Vectorworks export는 사용자의 로컬 환경 산출물이며 grandMA3 세션과 무관하다 |
| M8은 대역으로 충분하다 | 종단 검증은 M0 샘플 + 기존에 기록된 콘솔 실측 값(인메모리 fixture)으로 수행한다. 새 콘솔 접속을 요구하지 않는다 |

> **검토했으나 기각한 대안**: "M0-style 라이브 프로브로 FID/CID가 이번 쇼파일에서 읽히는지 재확인" — §A 사전 확정 사실 3과 위 표의 두 번째 행이 기각 근거다. 조인 키가 FID/CID에 의존하지 않도록 설계했으므로, 그 프로브의 결과가 GO든 NEGATIVE든 본 SPEC의 어느 마일스톤도 바뀌지 않는다.

---

## §D. 제약

1. **순수 함수 우선.** `server/vwx/`는 파일 바이트를 받아 판정 결과를 산출하는 계층이다. 콘솔 접촉은 대조 단계에서 기존 포트(`read_inventory`/`build_patch_sheet`)를 통해서만 일어나며, M0/M8도 콘솔에 접속하지 않는다.
2. **테스트 파일명 고정.** `server/tests/test_vwx_{reader,columns,address,rig,diff,report,tool}.py`. run-phase가 임의로 바꾸지 않는다.
3. **실패 모드는 개별 테스트로 분리.** 인코딩 실패·데이터블록 미탐·최소조건 미달·조인키 충돌·타입불일치를 한 카운터에 합치지 않는다. 사용자 조치가 다르기 때문이다.
4. **0건 스캔은 비공허성을 동반.** 생성된 조회 목록, 스캔 대상 목록이 실제로 비어 있지 않음을 함께 assert한다.
5. **AST 스캔 우선.** import 경계와 `==` 직접 비교 검증은 raw grep이 아니라 AST 식별자 스캔을 쓴다.
6. **별칭 테이블 확장은 계약 위반이 아니다.** M0/`ASSUMPTION-68`이 실물 헤더로 확장할 때 `REQ-VWX-005`의 매칭 규약 자체는 불변이며, 확장 내역은 `progress.md`에 diff로 기록한다.
7. **`openpyxl` 미승인 시 사유 문자열을 고정한다.** `.xlsx` 판독 실패 사유에 "미승인 의존성"을 포함해 §D Out of Scope와 코드가 대조 가능하도록 한다.

---

## §E. 테스트 골격

| 파일 | 소유 AC | 핵심 fixture |
|---|---|---|
| `server/tests/test_vwx_reader.py` | AC-VWX-002, AC-VWX-003, AC-VWX-004, AC-VWX-005 | 경로 A tab-text(헤더 있음/없음), 경로 B 워크시트(제목행+헤더행+데이터행+소계행 혼재), `Instrument Summary`, BOM 각 인코딩, mojibake 실패 |
| `server/tests/test_vwx_columns.py` | AC-VWX-006, AC-VWX-007, AC-VWX-008 | 별칭 변형 헤더(대소문자/공백/구두점), 미지 컬럼, 최소조건 미달 레코드 |
| `server/tests/test_vwx_address.py` | AC-VWX-009, AC-VWX-010, AC-VWX-011, AC-VWX-012 | `0`/공란 주소, `Absolute Address` 단일값 파일 + 전제 미검증, 멀티시스템 A/B, `normalize_address` 대조 |
| `server/tests/test_vwx_rig.py` | AC-VWX-013, AC-VWX-014, AC-VWX-015, AC-VWX-016, AC-VWX-017 | `Part Index` 멀티셀, `Static Accessory`, 타입명 변형, 중복 `unit_number`, VW `Identical Patch`/`Patch conflict` |
| `server/tests/test_vwx_diff.py` | AC-VWX-018, AC-VWX-019, AC-VWX-020, AC-VWX-021 | FID 우연일치 리그(조인 키 무시 확인), `missing_in_console`, 실제 주소 충돌, 수량 불일치, `FootprintPolicy` 유/무 |
| `server/tests/test_vwx_report.py` + `server/tests/test_vwx_tool.py` | AC-VWX-022, AC-VWX-023, AC-VWX-024 | 전 결함 합성 리포트, 라벨 표 일치, 툴 디스패치·경계 |
| 기존 전체 스위트 + diff gate | AC-VWX-025 | PRESERVE diff, gate 비공허성, 전체 회귀 |
| (라이브 없음 — M0 샘플 + 대역) | AC-VWX-026 | 종단 판독→정규화→대조→보고 |

마일스톤별 뮤테이션은 §B의 각 절에 적은 항목을 소진한다. 뮤테이션 결과는 `progress.md`에 killed/survived로 기록하고, survived는 해당 마일스톤 미완료로 본다.

---

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

> **구속력 있는 기록은 progress.md §F이며 오케스트레이터 소유다**(첫 run-phase Agent() 스폰 전 작성). **본 절은 권고이며 오케스트레이터가 확정·기각한다.** 어긋나면 progress.md가 이긴다.

### 입력 파라미터

- **tier**: L.
- **scope (file count)**: 예상 10~13 파일. 신규 구현 7(`server/vwx/{__init__,reader,columns,address,rig,diff,report}.py`), 조건부 `pyproject.toml` 1, 툴 수정 1(`server/orchestrator/tools.py`), `verdicts.py` 순수 추가 1, 신규 테스트 7.
- **domain count**: 1. 파이썬 백엔드와 markdown 기록. 콘솔 Lua·프런트엔드·룰북 자산은 PRESERVE.
- **file language mix**: Python + markdown. 신규 런타임 의존성은 조건부 1건(`openpyxl`).
- **parallel benefit**: LOW. M1(판독)→M2(컬럼)→M3(주소)→M4(리그)→M5(대조)→M6(보고/툴)의 강한 순차 데이터 사슬이며, M0의 실물 샘플 확보가 M1 이후 전부를 막는다.
- **Agent Teams prereqs**: 해당 없음(Mode 3 retired).

### 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 신규 모듈 7파일, 조건부 의존성 승인, 툴 배선이 있다 |
| 2 | background | 미선택 | 코드 쓰기가 포함된다 |
| 3 | agent-team | 미선택 | retired/tombstone 모드 |
| 4 | parallel | 미선택 | 도메인 1, 단일 언어, M1→M2→M3→M4→M5→M6 데이터 사슬 때문에 병렬 이득이 낮다 |
| 5 | **sub-agent** | **선택** | Tier L이지만 순차 의존이 강한 코딩 중심 작업이라 단일 worker가 계약대로 순서대로 미는 편이 충돌이 적다 |
| 6 | workflow | 미선택 | 균일 기계 변환이 아니라 판정·미수행·보고 형상을 계속 확인해야 한다 |

### Decision: sub-agent

### 정당화

실물 샘플 확보(M0)가 최대 위험이고, 그 뒤 M1 판독 → M2 컬럼 → M3 주소 → M4 리그 모델 → M5 대조 → M6 보고/툴이 순차 데이터 사슬을 이룬다. `ASSUMPTION-68`/`69`/`70`은 모두 동작 축소이지 병렬로 나눌 독립 산출물이 아니다. 따라서 권고 모드는 **sub-agent**다.

### 사용자 접점

| 시점 | 접점 | 이유 |
|---|---|---|
| **Kickoff** | 실물 Vectorworks export 샘플 제공 | M0의 선행조건. 미제공 시 M1 이후 전체가 정지한다. 본 SPEC 최대 위험 |
| **Kickoff** | `openpyxl` 신규 의존성 채택 여부 승인 | M1의 `.xlsx` 분기 존부를 가른다. 미승인이어도 산출물은 성립한다(축소) |

### 조건부 접점

| 조건 | 접점 |
|---|---|
| `ASSUMPTION-68` 부정/부분GO | 별칭 테이블 확장 diff를 사용자에게 공유한다(승인이 아니라 고지) |
| M0에서 실물 샘플을 확보하지 못하는 경우 | 오케스트레이터에게 범위 재개정 필요를 올린다. `research.md`의 별칭 테이블만으로 계약을 동결하지 않는다 |

**Implementation Kickoff Approval은 위 접점의 승인을 받는 절차이지, §A.4 결정 등록부를 다시 여는 절차가 아니다.**
