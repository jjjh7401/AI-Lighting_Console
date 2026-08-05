# server/vwx 픽스처 — 실물 음성 1건 + 실물 양성 4건 + 합성 그리드 1건

## `drop_dk_rigging_not_a_vectorworks_export.csv` (음성 사례)

- **출처**: <https://d3cvt6oaff0blz.cloudfront.net/drop.dk/website/Downloads/Examples%20Shows/csv_example1.csv>
- **이것은 Vectorworks Instrument Data export가 아니다.** drop.dk의 리깅 포인트/하중(rigging
  point/load) CSV다. 헤더는 `Name,PT-NAME,X_Coordinate,Y_Coordinate,LOAD` — 픽스처 타입 ·
  유니버스 · DMX 주소 컬럼이 전부 없다(주소 계열 컬럼 0개).
- **줄바꿈**: CR 전용(classic Mac 스타일) — `\r` 120개, `\n` 0개.
- **본 SPEC(M0)의 실물 검증 산출물이 아니다.** M0는 여전히 BLOCKED다
  (`.moai/specs/SPEC-COPILOT-VWX-001/progress.md` §E.2 참조). 이 파일은 오직
  REQ-VWX-003(패치 출처 아님 거부) 경로의 실물 음성(negative) 사례로만 쓰인다 —
  결함 1(CR 전용 줄바꿈에서 예외 탈출)·결함 2(패치 출처 아닌 파일에 "이상 없음" 오발)의
  회귀 테스트 픽스처다.

## `vectorworks_export_sample_with_data.csv` (양성 사례 — M0 실물 컬럼 계약 검증)

- **원본 경로(사용자 제공, 2026-08-05)**:
  `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/vectorworks_export_sample_with_data.csv`
- **실물 형식 샘플로 취급한다.** UTF-8 BOM · CRLF · 쉼표 구분 · 25컬럼 × 10행. `UID`는
  Vectorworks UID 형식, `GDTF Fixture`는 `Martin Professional@MAC Encore Performance CLD`
  정품 GDTF 표기. 경로 A(`path_kind=A`, flat 단일 테이블, 헤더 있음)로 판독된다.
- **이 파일이 덮는 것** (M0를 PARTIAL로 만든 근거):
  - `ASSUMPTION-68`(별칭표 실효성) — **NEGATIVE(부정) 판정**. 별칭표 밖으로 떨어진 실물 컬럼
    10개(`Fixture Name`·`GDTF Fixture`·`Gobo`·`Focus`·`X`·`Y`·`Z`·`Rotation Z`·`Pan`·`Tilt`) 중
    2개(`Fixture Name`→`fixture_name`, `GDTF Fixture`→`gdtf_fixture`)를 정규 필드로 승격해 해소.
  - 주소 3중 표현(Universe·DMX Address·Absolute Address) 교차검증의 **음성 대조군**(10/10 일치,
    `(u-1)*512+a` 공식과 전수 일치).
  - `DMX Footprint` 폭 출처 — 설계 측 구간 겹침 판정의 **음성 대조군**(stride 38 == footprint 38,
    완벽 패킹, 겹침 0).
- **이 파일이 덮지 못하는 것** (M8 종단 검증을 이 샘플로 닫으면 안 되는 이유 — "행복 경로만
  검증했다"):
  - `ASSUMPTION-69`(Absolute Address 단독 파일) — **미해소**. 이 파일은 Universe+DMX Address가
    항상 함께 있어 역산 경로(추측 금지 분기)가 한 번도 실행되지 않았다.
  - `ASSUMPTION-70`(경로 B 워크시트 데이터 블록 구조적 식별) — **미해소, 전혀 건드리지 못함**.
    이 파일은 `path_kind=A`(flat 단일 테이블)라 제목행·DB헤더행·서브행·소계행이 섞인 워크시트
    그리드 휴리스틱을 한 번도 실행하지 않았다.
  - 단일 유니버스(1) · 단일 픽스처 타입 · `Device Type` 열 없음(액세서리 필터링 미검증) ·
    `Part Index` 없음(멀티셀 폴딩 미검증) · `System` 열 없음(멀티시스템 차단 미검증) ·
    미패치 행(주소 0/공란) 없음 · 조인키 중복 없음 · 탭 구분 아님(경로 A tab-text 실물 미검증).
  - 구간 겹침 **양성 케이스**(stride < footprint)도, 주소 3중 표현 **불일치 케이스**도 이
    파일 자체에는 없다 — 두 기능의 비공허성은 합성 픽스처로 별도 증명했다
    (`test_vwx_rig.py::TestDesignSideOverlapDetection`,
    `test_vwx_address.py::TestTripleRepresentationCrossCheck`).

## `vectorworks_worksheet_multisystem_full.csv` (실물 — 9번째 라운드, 멀티시스템·멀티셀·집계행)

- **REAL.** 코디네이터가 직접 준비한 실물 형식 파일(2026-08-05). UTF-8 BOM ·
  CRLF · 쉼표 구분 · 29컬럼 × 20행(제목행 없이 DB 헤더 + 데이터 + 소계행이
  섞인 경로 B 워크시트 형태지만 헤더가 0번 행이라 `path_kind=A`로 판독됨).
- **이 파일이 덮는 것**:
  - 결함 1(P0) 재현·회귀 — System 2개(A/B) 관측 시 예전에는 전 행이
    `blocked`로 차단돼 `fixture_count=0`이었다. 이제는 `(system, universe,
    address)` 스코프 확장으로 설계 측 산출이 전부 정상 수행되고, 콘솔
    대조(`diffs`)만 별도로 미수행 처리된다(`skipped_checks`에 사유 명시).
  - 결함 2(P1) 재현·회귀 — SUBTOTAL×2·TOTAL×1(집계행)과 Top Hat(비-DMX
    액세서리)이 "판독 실패"가 아니라 `excluded_rows`로 별도 분리된다.
  - 결함 4(P1) 재현·회귀 — Channel "1"을 공유하는 부모 픽스처(S4 26 1)와
    액세서리 2개(Unit 2A/2B)가 channel 우선 조인으로 잘못 접히지 않는다
    (액세서리는 `(position, unit_number)` 스코프로 라우팅).
  - 멀티셀 폴딩(Part Index 1~8, ColorForce 72) → 정확히 1개 픽스처.
  - DMX 소비 액세서리(Coloram 스크롤러, footprint 1)는 포함, 비-DMX
    액세서리(Top Hat, footprint 0)는 배제 — 둘 다 `Device Type=Accessory`
    리터럴을 공유해 문자열만으로는 구분 불가함을 실물로 증명.
  - 미패치(Titan Tube, DMX Address 0) → `unpatched_designed` 3번째 분류.
  - `(system, universe)` 스코프 도입 후 설계 측 구간 겹침이 정확히 0건
    (System을 무시했다면 A/U1/1과 B/U1/1이 오탐 겹침이었을 것).
- **이 파일이 덮지 못하는 것**: 콘솔 실측 대조 자체(멀티시스템이라 항상
  미수행) — 단일 System 콘솔 조인은 기존 실물 샘플
  (`vectorworks_export_sample_with_data.csv`)이 이미 덮는다.

## `vectorworks_worksheet_absolute_address_only.csv` (실물 — 9번째 라운드, ASSUMPTION-69)

- **REAL.** 위 파일과 같은 리그를 Universe/DMX Address 컬럼 없이 Absolute
  Address만으로 내보낸 변형(27컬럼, CRLF). System별로 Absolute Address가
  독립적으로 매겨진다는 사실(A/U1/abs=1과 B/U1/abs=1이 완전히 같은 값)을
  실물로 증명한다.
- **덮는 것**: `ASSUMPTION-69`(Absolute Address 단독 파일) — 이제 실물로
  판정 가능. Universe/DMX Address 쌍이 전혀 없으므로 역산 경로가 실제
  실행되고, `contiguous_512_confirmed=False`(기본값)에서는 여전히 추측하지
  않고 `absolute_address_premise_unverified`로 보류함을 확인. System 문자가
  `fields["system"]`에 별도로 보존되지 않으면 abs=1만으로는 A/U1과 B/U1을
  원리적으로 구분할 수 없음(NEGATIVE 판정의 근거)도 함께 확인.

## `vectorworks_export_instrument_data_no_header.txt` (실물 — 9번째 라운드, 결함 3)

- **REAL.** 경로 A(`Export Instrument Data`) 진짜 헤더 없는 내보내기 — 탭
  구분 · LF · BOM 없음 · 28필드 × 17행. "Export field names as first
  record" 체크박스를 끈 상태의 실물 재현.
- **덮는 것**: 결함 3(P1) — 헤더 없는 경로 A 파일이 예전에는 행마다
  개별 `min_record_incomplete` 17건을 냈다. 이제는 파일 단위 판정 1건
  (`headerless_path_a_export`) + 실행 가능한 해결책("Export field names as
  first record"를 켜고 재수출)으로 압축된다. 헤더 유무 스니퍼 자체가
  정확히 "헤더 없음"을 식별한 것은 REQ-VWX-001을 뒷받침하는 **긍정** 증거로
  기록한다(`progress.md` §E.2 참조) — 실패가 아니다.

## `synthetic_path_b_worksheet_grid.csv` (⚠ 합성물 — 실물 워크시트 export 아님)

- **이 파일은 손으로 만든 합성물이다. 실물 Vectorworks 워크시트 export 가 아니다.** 제목행
  (`Instrument Data`) + DB 헤더행 + 4개 데이터행(포지션 2종 `FOH`/`Truss 1`, 각 포지션 안에서
  `Unit Number` 1·2가 재사용됨 — v0.1.5 조인 키 스코프 수정의 재현 조건과 동일한 형태) + 소계행
  (`Totals,4`, 헤더보다 적은 필드 수로 구조적 감지 대상)으로 구성했다. CRLF.
- **목적**: 경로 B(워크시트 그리드) 판별 휴리스틱(`path_kind=B` 판정 · 헤더 행 구조적 식별 ·
  소계행을 필드 수 불일치로 걸러내기)이 **최초로 실행**되도록 만든 입력이다 — M0가 확보한
  실물 샘플(`vectorworks_export_sample_with_data.csv`)은 `path_kind=A`(flat 단일 테이블)라 이
  경로를 한 번도 타지 않았다.
- **결과(직접 실측)**: `path_kind=B` 정확히 판별 · 소계행 1건이 `worksheet_subtotal_row`로
  구조적으로 배제(데이터 행에 섞이지 않음) · 데이터 4행 전량 판독 · 조인 키 우선순위(포지션별
  스코프) 정상 동작(fixture_count 4, 충돌 0) — **전부 확인됨**.
- **이 파일이 증명하지 않는 것**: 이건 합성물이므로 실물 워크시트 export의 실제 마커·서식·
  인코딩 특이성을 대변하지 않는다. **`ASSUMPTION-70`(경로 B 데이터 블록의 구조적 식별 가능성)
  은 여전히 미해소로 남는다** — 이 파일은 "휴리스틱 코드 경로가 실제로 실행되고 구조적으로
  동작한다"는 것만 보이며, "실물 워크시트에서도 그렇다"는 것은 보이지 않는다. 실물로 오인해
  ASSUMPTION-70을 GO로 닫으면 안 된다(`.moai/specs/SPEC-COPILOT-VWX-001/progress.md` §E.2 M0
  절 참조).
