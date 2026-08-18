# wip 스냅숏 819aa6f 판정서 (2026-08-18)

대상: `research/ma3-effects-phaser` 브랜치의 보존 커밋 `819aa6f` vs 현재 `main`(410a9a7).
방법: 파일별 3-way 대조(wip diff ↔ main 현재본 ↔ main 이후 12커밋 이력).

## 총평

wip은 "미커밋 잡동사니"가 아니라 **2026-08-18 라이브 onPC 실측 세션에서 나온 3개의 응집된 미완 기능**이다.
main의 이후 작업(introspect responder v1.6.1)과 겹치는 것은 **프로토콜 층의 `props` 동사 하나뿐**이고, 그 층만 main이 권위. 오케스트레이터 층 기능 3종은 main에 어떤 형태로도 없다.

## 기능 단위 판정

### A. 반자동 패치 재설계 (`patch_fixtures`) — UNIQUE, 이식 가치 높음
- 콘솔 실측 모드/폭(`prechk/mode_read.py` 신규, TotalFootprint 기반 — Esprite 40ch vs 폭49 실기 근거), 모드 다수면 사용자 선택 카드, 서버가 게이트 경유 자동 실행 후 재조회 판정, `not_created`/`partially_created` 상태 신설.
- 소비자 측 8파일(question.py `commands` 필드, session.py 라벨 2종, QuestionCard 복사버튼 UI, protocol.ts, styles.css, web/PROTOCOL.md, 테스트 2본)은 main 무충돌 클린 어플라이 — 단 생산자(tools.py ③)와 원자적으로만 의미 있음.
- stagedpatch.py 문구·test_vwx_stagedpatch(+371) 계약 반전(TestTheServerFiresItThenVerifies)도 이 묶음. main의 현행 "조작자 수동 타이핑" 계약과 정면 교체 관계.

### B. 타입 해석 개선 (`resolve_fixture_type`) — UNIQUE, 최소 단위 분리 이식 가능
- `librarywatch.candidate_names()` 토큰 매칭(«robe esprite»→«Robin Esprite» 실기 버그 처방, MIN_DISTINCTIVE_TOKEN=4), 후보 1개 자동 진행, ANSWER_SUPPLY_FILE 폐기(실측: Import 실패).
- 동반 필수: test_librarywatch_matching.py(신규 77줄), test_resolve_type_tool.py(신규 143줄), test_vwx_address.py 경계 등기 10줄, tools.py 호출부.
- A와 독립적으로 이식 가능한 가장 작은 묶음.

### C. 공간 좌표 배치 읽기 (페이지드 props) — 프로토콜 층 SUPERSEDED, 문제는 미해결
- wip 1.6.0 `props` = 자식 페이지드 배치(start/count/next). main 1.6.1 `props` = 단일 노드 다속성(introspect). **와이어 포맷 상호 배타** — bridge/protocol.py·safety/console.py·responder lua의 wip 판은 폐기.
- 그러나 wip이 실측으로 증명한 문제(66.7ms/왕복 → 80대 ~26초, 200대 불가)는 main에 그대로 남음(tools.py:942 "Candidate B: bulk spatial verb" D-1 미결, per-property 상한 60회).
- 재이식하려면 새 동사명(+VERSION 1.7.0, PROTOCOL 새 §)으로 별도 SPEC. tools.py ①·test_spatial_batch_read.py는 그때까지 보류.

### D. 폐기·잡동사니
- 버전 범프 테스트 변경(test_responder_deploy/roundtrip): main이 1.6.1로 이미 앞섬 — SUPERSEDED.
- safety/console.py 재포매팅 5곳: JUNK(main에 재포맷 원복 정책 존재).
- src/artifacts/*.html 14본 + INDEX.md: 세션 산출물 — JUNK(앱 무관, 필요 시 아카이브만).
- .moai 백업/로그: JUNK.

## 권고 이식 순서
1. **B** (candidate_names + 테스트 3본 + tools.py 호출부) — 독립, 저위험.
2. **A** (mode_read.py + tools.py patch_fixtures + 웹/UI 8파일 + stagedpatch 문구/테스트) — 원자적 이식. run_commands 재진입이 main 게이트 계약 테스트(test_the_execution_port_is_only_named_inside_run_commands)와 정합인지 확인 필요.
3. **C** — 별도 SPEC로 재설계 후에만. wip의 실측 수치(66.7ms, TotalFootprint 검증값)는 SPEC/커밋 메시지로 보존.
4. 이후 `research/ma3-effects-phaser` 브랜치 + 기본 워크트리 삭제.

상세 근거: 스카우트 전문 history://LuaResponder, history://OrchTools, history://VwxSuite, history://WebUi.
