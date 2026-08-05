# server/vwx 픽스처 — 실물 음성 사례 1건

`drop_dk_rigging_not_a_vectorworks_export.csv`

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
