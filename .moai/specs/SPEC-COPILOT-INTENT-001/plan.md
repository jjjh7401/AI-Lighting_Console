---
id: SPEC-COPILOT-INTENT-001
document: plan
version: "0.1.0"
updated: 2026-08-19
tier: M
---

# 구현 계획 — SPEC-COPILOT-INTENT-001

## A. 마일스톤

| M | 내용 | 파일 | 상태 |
|---|---|---|---|
| M1 | 명시적 부정 하드 베토 | `session.py` `_POSITION_FX_VETO` + `_position_fx_sequence` 진입 | 완료 |
| M2 | 축 충돌 카드 1장 | `session.py` `_NON_POSITION_ATTRIBUTE` · `_POSITION_AXIS_CLAIM` + `_ask_one` | 완료 |
| M3 | 기하 해석 근거 회신 | `session.py` `_axis_interpretation_note` + 회신 조립 | 완료 |
| M4 | 기하 생성기 6종 + 큐 프리뷰 · 형제 핸들러 베토 확장 | `server/effects/` 신설 (예정) | 이연 |
| M5 | 사용자별 해석 기본값 세션 메모리 | `session.py` + 타임라인 스토어 | 이연 |

## B. 설계 결정

**D1 — 베토는 회신을 만들지 않는다.** 컬러 요청에 포지션 질문·거부 문면을 붙이면 사용자는 자기 요청이 거부된 것으로 읽는다. `None` 반환으로 기존 폴백(모델 → `compose_fx`)에 문장을 그대로 넘긴다. 이 폴백은 2026-08-19 실측에서 컬러 페이저를 정상 처리했다(`Store Preset 21.17 'RG Rotate' /Universal`).

**D2 — 카드 무답은 포지션 미저장.** `Store Sequence`는 비가역이고 이 앱에 복원 경로가 없다. 축이 확정되지 않은 상태에서 팬/틸트 데이터를 쓰는 쪽이 더 비싼 오류다.

**D3 — 해석 문장은 저장 성공 여부와 무관.** 해석은 저장보다 앞에서 확정되므로, 실패 회신에서도 "무엇을 어떻게 읽었는지"가 남아야 재시도 판단이 가능하다.

**D4 — 어휘 정규식 109개를 이번에 손대지 않는다.** 재현 케이스가 있는 축 하나(`position_fx`)에서 기전을 검증한 뒤 M4에서 확장한다. 일괄 리팩터는 첫-매치 순서에 얹힌 기존 계약(REQ-PRESETGUARD-015 등)을 동시에 흔든다.

**D5 — `아니면` 제외.** `아니(?!면|냐|니)` 부정 전방탐색으로 선택 접속을 베토에서 뺀다. `"팬 아니면 틸트로 스윕"`은 포지션 요청이다.

## C. 구현 순서 (실행됨)

1. 계약 테스트 8건 작성 → 실행 → **6 failed / 2 passed** (RED 확인).
2. `_POSITION_FX_VETO` · `_NON_POSITION_ATTRIBUTE` · `_POSITION_AXIS_CLAIM` 상수 신설.
3. `_position_fx_sequence` 진입에 베토 → 충돌 카드 순서로 삽입 (좌표 판독 **앞**).
4. `_axis_interpretation_note` 정적 헬퍼 신설 + 회신 조립에 삽입.
5. 테스트 재실행 → **8 passed**.
6. 회귀: `test_web_session.py` 406 passed · `server/tests` 9583 passed(기존 실패 3건은 §F.1).
7. 라이브 수용: 재현 케이스 2건 실기 재실행 (AC-INTENT-007·008).

## D. PRESERVE / 게이트

- 본 SPEC은 PRESERVE 핀 파일(`server/web/preview.py`·`server/safety/console.py`)을 건드리지 않는다.
- `tools.py` 미변경 → 헝크핀 대상 아님.
- 신규 명령 문법 0건 → 문법 검증기·블랙리스트 변경 없음.
