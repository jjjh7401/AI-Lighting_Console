---
id: SPEC-COPILOT-PRESETGUARD-002
title: "프리셋 확인 카드 승낙 어휘 확장 · 고정 등기구 프리셋 제외 (Preset Guard 후속)"
version: "0.1.0"
status: draft
created: 2026-08-16
updated: 2026-08-16
author: manager-spec
priority: P2
phase: "Phase 2 안전 계층 — 사용성 간극 · 대상 정합"
module: "server/web/session.py (_PRESET_CONSENT_WORDS · _PRESET_ANSWER_SUFFIXES · _basic_position_presets), server/tests/test_web_session.py"
lifecycle: spec-anchored
tags: "consent-vocabulary, fail-closed-usability, fixed-fixture-exclusion, position-pool, pan-tilt-applicability"
tier: S
related_specs: [SPEC-COPILOT-PRESETGUARD-001, SPEC-COPILOT-SPATIAL-001]
---

# SPEC-COPILOT-PRESETGUARD-002 — 승낙 어휘 확장 · 고정 등기구 제외

> PRESETGUARD-001이 `completed`로 마감하며 **닫지 않고 남긴 열린 항목 ①·②**를 묶는다
> (`SPEC-COPILOT-PRESETGUARD-001/progress.md` 잔여 항목 표 1·2번, CHANGELOG.md:20).
> 둘 다 안전 방향(쓰기 0)이라 P1이 아니지만, 하나는 운영자가 승낙했는데 저장이 안 되고,
> 하나는 Pan/Tilt가 없는 장비에 Pan/Tilt 프리셋이 저장된다.

## A. 결함 두 건 — 전부 실측이다

### A.1 승낙 미인식 4형 (사용성 간극, fail-closed라 쓰기 사고는 0)

`_preset_answer_intent()`(`session.py:1852`)는 어절 단위 전량 일치 판정이다(부분 매칭이
비승낙을 승낙으로 삼킨 실측 5문장 때문 — `:1787~1794` 주석). 그 규칙 아래에서 다음
네 답이 `unrecognised`로 떨어져 저장이 진행되지 않는다 (PRESETGUARD-001 R2 직접 측정):

| 답 | 탈락 경로 |
|---|---|
| `그래` | `_PRESET_CONSENT_WORDS`(`:1795`)에 부재 |
| `덮어써줘` | 어미 표 `_PRESET_ANSWER_SUFFIXES`(`:1761`)에 `줘`가 없다 — `해줘`만 있어 `덮어써줘`가 통어절로 남는다 |
| `ㅇㅇ` | 초성 승낙어 미등재 |
| `덮어써 주세요` | `덮어써`는 승낙 ✓ 이나 둘째 어절 `주세요`→`주세`가 비승낙 → 전량 일치 규칙에 걸린다 |

**고칠 방향은 어절 규칙의 보존이다** — 규칙을 느슨하게 하지 않고 **어휘·어미 표를 늘린다**:
승낙어에 `그래`·`ㅇㅇ`, 어미에 `줘`(단, `줘`보다 긴 `해줘` 계열이 먼저 매칭되는 기존
길이순 원칙 유지), 그리고 보조용언 어절(`주세요`·`줘요` 등)을 "승낙문 안에서 무시 가능한
어절"로 다루는 방식 중 하나를 설계에서 확정한다. `확인`·`네가`류 오탐 실측 5문장은
회귀 코퍼스로 **반드시 그대로 비승낙 유지**.

### A.2 P4′ — 고정 등기구에 Pan/Tilt 프리셋 (설계 간극)

`_basic_position_presets()`(`session.py:2800~`)는 좌표 확인된 **모든** 픽스처를 대상으로
Position 프리셋을 저장한다. 그러나 조준 계산 계층 `server/spatial/pointing.py`는 문서상
**무빙헤드 조준용**이고, PAR·블라인더 같은 고정 등기구는 Pan/Tilt 어트리뷰트가 없거나
무의미하다 — 받은 Pan/Tilt 프리셋은 죽은 데이터이거나 콘솔 에러다.

**고칠 방향**: 프리셋 대상 집합을 Pan/Tilt 보유 장비로 좁힌다. 판별 근거(픽스처 타입의
어트리뷰트 판독 경로)는 설계에서 확정 — REQ-PRESETGUARD-017(spatial 순수성)을 승계하여
`server/spatial/**` 무변경, 판별·필터링은 `session.py`에 둔다.

## B. 요구사항 (GEARS)

- **REQ-PG2-001** [Event] — WHEN 확인 카드 답이 `그래`·`ㅇㅇ`·`덮어써줘`·`덮어써 주세요`
  (및 각각의 기존 어미 변형)일 때, the 판정기 **shall** `consent`를 반환한다.
- **REQ-PG2-002** [Ubiquitous] — the 판정기 **shall** 어절 단위 전량 일치 원칙을 유지한다.
  실측 오탐 5문장("잠깐 확인해보고요"·"안 되네요"·"확인 안 했어요"·"네가 판단해"·
  "예전 값으로 되돌려줘")은 계속 비승낙이다 — 회귀 테스트로 고정.
- **REQ-PG2-003** [Event] — WHEN `_basic_position_presets()`가 대상 픽스처를 모을 때,
  the 핸들러 **shall** Pan/Tilt 어트리뷰트가 없는 픽스처를 제외하고, 제외 사실과 대수를
  회신 문면에 산술로 보고한다(침묵 축소 금지 — TRUNCATE-001의 고지 규율 승계).
- **REQ-PG2-004** [Unwanted] — the 개정 **shall not** `server/spatial/**`·
  `server/orchestrator/tools.py`를 변경한다(PRESETGUARD-001 REQ-017·018 승계).
  tools.py가 불가피하면 헝크핀 재실측을 별도 커밋으로 동반한다.
- **REQ-PG2-005** [Unwanted] — the 개정 **shall not** 기존 안전 동작을 퇴행시킨다:
  fail-closed(`unrecognised` → 저장 안 함) · `/Merge`·`/Overwrite` 금지 · 겹침 확인 카드
  경로 유지.

## C. Out of Scope

- 자유 대화 승낙(카드 밖 문장) 인식 — 카드 응답 채널만 다룬다.
- `arrange_fixtures`·조준(`pointing.py`) 자체의 고정 등기구 처리 — READ/WRITE 툴 계층은
  별도 축이다.
- Pan/Tilt 판별의 콘솔 실측 프로토콜 — 설계 단계에서 채널 확정(라이브 프로브 1회 예상).

## 이력

| 버전 | 일자 | 작성 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-16 | manager-spec | 최초 작성 (draft, Tier S). PRESETGUARD-001 마감 시 잔여 열린 항목 ①(승낙 미인식 4형)·②(P4′ 고정 등기구) 묶음. |
