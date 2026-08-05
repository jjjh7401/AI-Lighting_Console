# server/vwx 픽스처 — 실물 음성 사례 1건 + 실물 양성 사례 1건

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
