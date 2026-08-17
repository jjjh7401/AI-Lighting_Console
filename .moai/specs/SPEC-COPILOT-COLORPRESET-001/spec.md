---
id: SPEC-COPILOT-COLORPRESET-001
title: "표준 무대 팔레트 컬러 프리셋 10종 — 포지션 프리셋과 동형의 저장·가드·재생성 (Color Preset)"
version: "0.1.0"
status: draft
created: 2026-08-16
updated: 2026-08-16
author: manager-spec
priority: P2
phase: "Phase 3 연출 자산 — 프리셋 팔레트 확장"
module: "server/web/session.py (프리셋 저장/재생성 공용 몸통의 풀 매개변수화 + 컬러 시퀀스), server/spatial/ 무접촉, server/tests/test_web_session.py"
lifecycle: spec-anchored
tags: "color-preset, palette, preset-store, fail-closed, family-filter, pool-resolution, capability-exclusion"
tier: M
related_specs: [SPEC-COPILOT-PRESETGUARD-001, SPEC-COPILOT-PRESETGUARD-002, SPEC-COPILOT-LOOKLIB-001]
---

# SPEC-COPILOT-COLORPRESET-001 — 표준 무대 팔레트 컬러 프리셋 10종

> **한 문장**: "기본 컬러 프리셋을 N번부터 저장해줘"가 표준 무대 팔레트 10색을
> Color 풀에 저장한다 — 포지션 프리셋(BASIC 10종)과 **완전 동형**의 안전 장치
> (점유 검사 → 덮어쓰기 카드 → 룩별 독립 번들 → 페이지드 되읽기 산술 → 라벨
> 가족 재생성) 위에서.
>
> **사용자 결정 3건 (2026-08-16 인터뷰)**:
> ① 팔레트 = **표준 무대 10색** (무드 어휘 연동 아님 — 고정 시퀀스로 예측 가능)
> ② 범위 = **저장 10종만** (프리셋 참조 컬러 체이스 등 소비 경로는 별도 SPEC —
>    기존 fx 라이브러리에 컬러 체이스 3종이 이미 있어 중복 여부 확인이 선행)
> ③ 컬러 미보유 장비 = **제외 + 산술 고지** (포지션 P4′ 규율 선반영)

## A. 배경

### A.1 무엇이 이미 있는가 (전부 재사용 대상이다)

| 자산 | 위치 | 상태 |
|---|---|---|
| 저장 흐름 공용 몸통 (점유 검사·덮어쓰기 카드·승낙 판정·룩별 번들·되읽기 산술) | `session.py` `_store_position_preset_sequence` | ✅ 2026-08-16 FX 포지션이 이미 두 번째 소비자 — 세 번째 소비자를 받도록 **풀 번호 매개변수화**만 필요 |
| 재생성 공용 몸통 (풀 미상 거부·라벨 가족 필터·제자리 갱신) | `session.py` `_regenerate_position_preset_sequence` | ✅ 동일 — 가족 필터의 `first_label`은 이미 매개변수 |
| 페이지드 풀 판독 (24캡 극복, 이름 동반) | `_position_preset_pool_children` + 응답기 1.6.0 | ✅ 경로가 `PresetPools/2` 하드코딩 — **풀 번호 인자화** 필요 |
| 컬러 값 문법 | `Attribute 'ColorRGB_R' At <0-100>` (G/B 동일) | ✅ 룰북 라이브 검증 (`31_choreography_patterns.md`) |
| 컬러 프리셋 저장 선례 | `server/looks/instantiate.py` — 해석된 풀에 `Store Preset <pool>.<slot>` | ✅ `/Overwrite` 금지·점유 슬롯 비표적 규율 포함 |
| **Color 풀 번호 해석** | `server/looks/instantiate.py:220` — *"`Preset 4.1 = Color`는 룰북 예시 프로즈이지 이 쇼파일의 계약이 아니다"* | ⚠️ **함정 문서화됨**: 풀 이름은 운영자가 바꿀 수 있다. 4를 하드코딩하면 손으로 만든 프리셋을 덮는다 |

즉 이 SPEC의 실체는 **신규 기능이 아니라 세대화(generalization)다** — 포지션 전용으로
태어난 기계에서 `POSITION_PRESET_POOL = 2` 상수와 `PresetPools/2` 경로를 인자로
끌어올리고, 컬러 시퀀스 하나를 새 소비자로 꽂는다.

### A.2 표준 무대 팔레트 10색 (고정 시퀀스 — 슬롯 순서가 계약)

| # | 라벨 | 의도 | RGB (0-100, 설계 단계 실측 조정 허용) |
|---|---|---|---|
| 1 | **Warm White** | 기본 워시·발라드 | 100 / 75 / 40 |
| 2 | Cool White | 클린·테크 | 85 / 95 / 100 |
| 3 | Red | 드롭·강조 | 100 / 0 / 0 |
| 4 | Amber | 노을·웜 무드 | 100 / 55 / 5 |
| 5 | Yellow | 팝·경쾌 | 100 / 85 / 0 |
| 6 | Green | 포레스트·이색 | 0 / 100 / 10 |
| 7 | Cyan | 시원함·EDM | 0 / 90 / 100 |
| 8 | Blue | 딥 블루·서정 | 5 / 20 / 100 |
| 9 | Magenta | 클럽·화려함 | 100 / 0 / 70 |
| 10 | Lavender | 몽환·엔딩 | 55 / 35 / 100 |

- 슬롯 1은 **항상 Warm White** — 재생성 가족 필터의 `first_label`이 된다
  (포지션의 'Home'·FX의 'Sweep L'과 같은 규율).
- 4·8번 RGB는 기존 `fx/library/color.yaml`의 실측 대역(따뜻함 100/55/5,
  차가움 5/20/100)에서 가져왔다 — 저장소가 이미 쓰는 색과 일관.
- 전 장비 **동일 값**(Selective 저장이지만 값이 균일) — Global/Universal 프리셋
  플래그는 미검증 문법이므로 쓰지 않는다(§D).

## B. 요구사항 (GEARS)

- **REQ-COLORPRESET-001** [Event] — WHEN 지시가 `(기본|베이직|basic) + (컬러|색|color) + (프리셋)? + (저장|만들|잡아|생성)`을 담을 때, the 세션 **shall** 표준 팔레트 10색을 Color 풀의 연속 10칸에 저장한다. 시작 번호는 지시("N번부터") 또는 질문 카드 1장 — 추측 금지(PRESETGUARD-001 규율 승계).
- **REQ-COLORPRESET-002** [Ubiquitous] — the Color 풀 번호 **shall** 리그 판독으로 해석된다(`get_rig_context`/풀 목록에서 이름 기반) — `4` 하드코딩 금지. 해석 실패는 거부이며 "풀을 찾지 못했다"를 명시한다(`instantiate.py:220` 함정의 세션 계층 적용).
- **REQ-COLORPRESET-003** [Ubiquitous] — 저장 흐름 **shall** 기존 공용 몸통을 재사용한다: 명시 번호 점유 검사 → 충돌 시 덮어쓰기 확인 카드(`_preset_answer_intent` 어휘 그대로) → 색별 독립 번들(적용 → `Store` → `Label` → `ClearAll`) → 페이지드 되읽기 산술 보고. 컬러 전용 카드·어휘 신설 금지.
- **REQ-COLORPRESET-004** [Event] — WHEN 지시가 `(기본|베이직) + (컬러|색) + 다시/재생성`을 담을 때, the 세션 **shall** 라벨 가족(`Warm White`, `#N` 접미 허용) 구간을 제자리 갱신한다 — 포지션·FX 재생성과 동일 몸통, 풀 미상 시 거부(unknown ≠ empty).
- **REQ-COLORPRESET-005** [Event] — WHEN 대상 픽스처에 컬러 어트리뷰트가 없을 때, the 핸들러 **shall** 그 픽스처를 번들에서 제외하고 제외 대수·FID를 회신에 산술로 명시한다(침묵 축소 금지). 판별 채널(픽스처 타입 어트리뷰트 판독)은 설계 단계 라이브 프로브 1회로 확정한다.
- **REQ-COLORPRESET-006** [Ubiquitous] — 공용 몸통의 풀 매개변수화 **shall** 기존 포지션(2번 풀) 경로의 문면·동작을 바꾸지 않는다 — 기존 테스트 전건 그린이 그 증거다.
- **REQ-COLORPRESET-007** [Unwanted] — the 개정 **shall not** `/Merge`·`/Overwrite`를 쓰거나, `server/orchestrator/tools.py`·`server/spatial/**`·`console/lua/**`를 변경한다. tools.py가 불가피하면 헝크핀 재실측 별도 커밋(상례).
- **REQ-COLORPRESET-008** [Unwanted] — the 개정 **shall not** Global/Universal 프리셋 저장 플래그를 도입한다 — 미검증 문법이다. Selective(프로그래머 경유) 저장만 쓴다.

## C. Out of Scope

- **프리셋 참조 컬러 이펙트/체이스 시퀀스** — 사용자 결정 ②로 제외. 기존 fx
  라이브러리(삼색 체이스·무지개 웨이브·따뜻함↔차가움)와의 중복/차별 분석이
  선행돼야 하며, 하게 되면 position_fx의 동형 확장이다.
- 무드 어휘 → 컬러 자동 매핑 (looks 시스템의 영역).
- CMY 전용 장비의 RGB→CMY 변환 — 판별 채널 실측에서 CMY 장비가 관측되면
  설계 단계에서 재론(관측 전 추측 구현 금지).
- 컬러 프리셋의 큐/타임라인 소비 — 기존 경로가 프리셋 번호를 이미 받는다.

## D. 열린 결정 (설계 단계 확정)

- **[NEEDS CLARIFICATION: 컬러 어트리뷰트 판별 채널]** — 픽스처 타입의
  어트리뷰트 목록 판독 경로(2-hop 타입 조회는 SPATIAL에서 실측됨). 라이브
  프로브 1회 필요: 측정 리그의 Sha25Bea·Sphere가 ColorRGB를 갖는지.
- **[NEEDS CLARIFICATION: 풀 이름 매칭 규칙]** — Color 풀 탐색을 이름
  `Color`(영) 정확 일치로 할지, 풀 목록에서 기본 4번 위치+이름 교차 검증으로
  할지. 기본 권고: 이름 일치 우선, 실패 시 거부(추측 금지).

## 이력

| 버전 | 일자 | 작성 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-16 | manager-spec | 최초 작성 (draft, Tier M). 사용자 인터뷰 3결정 반영: 표준 10색 · 저장만(소비 별도) · 미보유 장비 제외+고지. REQ 8 · 열린 결정 2. |
