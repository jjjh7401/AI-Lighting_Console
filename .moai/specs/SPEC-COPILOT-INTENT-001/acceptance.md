---
id: SPEC-COPILOT-INTENT-001
document: acceptance
version: "0.1.0"
updated: 2026-08-19
---

# 수용 기준 — SPEC-COPILOT-INTENT-001

## A. 자동 검증 (pytest)

테스트 클래스: `server/tests/test_web_session.py::TestPositionFxIntentFrame`

| AC | 계약 | 검증 | 상태 |
|---|---|---|---|
| AC-INTENT-001 | 명시적 부정 4문장이 좌표 판독 0회·카드 0장·저장 0건으로 빠진다 | `test_an_explicit_negation_vetoes_the_position_builder` (parametrize 4) | PASS |
| AC-INTENT-002 | 축 충돌 시 카드 정확히 1장, 선택지에 `색`·`빔`이 각각 등장 | `test_a_non_position_attribute_asks_one_axis_card` | PASS |
| AC-INTENT-003 | 카드에서 속성축을 고르면 저장 0건 + 좌표 판독 0회 | 위 동일 테스트 | PASS |
| AC-INTENT-004 | 카드에서 빔축을 고르면 좌표 판독 1회 + 저장 1건 (기존 몸통 보존) | `test_choosing_the_beam_axis_keeps_the_position_body` | PASS |
| AC-INTENT-005 | (t34 개정) 포지션 축 단어가 있어도 경쟁 축이 지목되면 카드 1장 + 저장 1건 — 개정 REQ-INTENT-008 이 명시한 **받아들인 비용**의 실례다. 원 기대치는 「카드 0장」이었고, 그 동작이 배제 문장을 긍정으로 뒤집는 것이 t34에서 측정됐다(원본 대비 16문장 중 13문장 누출) | `test_an_explicit_position_word_still_gets_the_card` | PASS |
| AC-INTENT-006 | 회신에 `좌표 해석` · `FID 순서` · 실측 X 범위가 실린다 | `test_the_reply_states_how_the_geometry_was_derived` | PASS |

측정: `8 passed` (parametrize 4 + 개별 4), 1.08s.

## B. 회귀

| 대상 | 결과 |
|---|---|
| `server/tests/test_web_session.py` 전체 | **406 passed** |
| `server/tests` 전체 | **9583 passed · 6 skipped · 3 failed** |

3건의 실패는 **전부 이 SPEC 이전부터 main에 존재**한다. `git stash`로 본 SPEC의 변경을 제거한 clean HEAD에서 동일 재현:

| 실패 | 원인 | 이 SPEC과의 관계 |
|---|---|---|
| `test_the_preserved_paths_are_unchanged` | `BASE..HEAD` 기준 `server/web/preview.py`가 pinned 형태와 다름(4행 컴프리헨션 → 1행) | 무관 · §F.1 등재 |
| `test_ruff_format_reports_no_change` | 같은 파일에 대해 ruff는 **1행 형태**를 요구 — PRESERVE와 **상호 배타** | 무관 · §F.1 등재 |
| `test_tools_hunks_are_only_songcue_registration...` | `tools.py` 헝크핀 드리프트 (본 SPEC은 `tools.py` 미변경) | 무관 · §F.1 등재 |
| `TestSidecarSelfReap::...without_a_pipe` | 사이드카 상태파일 타이밍 — 재실행 시 통과 | 플레이크 |

## C. 라이브 수용 (재현 케이스 실기 재실행)

| AC | 절차 | 기대 |
|---|---|---|
| AC-INTENT-007 | 앱에 `"컬러 페이저만 만들어줘, 포지션은 건드리지 말고 원형으로 도는 색"` 전송 | 서클 빌더 진입 0회 · 컬러 경로로 처리 |
| AC-INTENT-008 | 앱에 `"좌우 스윕 시퀀스 만들어줘"` 전송 | 회신에 `좌표 해석:` 줄 등장 |

## D. 반증 로그

- 구현 전 동일 테스트 실행 → **6 failed / 2 passed** (RED 확인). 통과한 2건은 카드 없이 기존 몸통이 도는 경로(AC-004·005)로, 베토·카드 미구현 상태에서도 성립하는 것이 정상이다.
