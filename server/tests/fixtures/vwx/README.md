# server/vwx 픽스처 — 실물 음성 사례 1건 + 실물 양성 사례 1건 + 합성 그리드 1건

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
