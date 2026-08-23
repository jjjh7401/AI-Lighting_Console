---
id: SPEC-COPILOT-INTENT-001
title: "의도 프레임 라우팅 — 어휘를 판정자에서 후보로 (Intent Frame)"
version: "0.1.0"
status: in-progress
created: 2026-08-19
updated: 2026-08-19
author: manager-spec
priority: P1
phase: "Phase 3 대화 정확도 — 요청 해석 계층"
module: "server/web/session.py (_position_fx_sequence · _axis_interpretation_note · 어휘 베토/충돌 상수), server/tests/test_web_session.py"
lifecycle: spec-anchored
tags: "intent-frame, slot-filling, lexical-router, hard-veto, axis-disambiguation, spatial-grounding, hijack-prevention"
tier: M
related_specs: [SPEC-COPILOT-SPATIAL-001, SPEC-COPILOT-FXGEN-001, SPEC-COPILOT-PRESETGUARD-001, SPEC-COPILOT-LDGUIDE-001]
---

# SPEC-COPILOT-INTENT-001 — 의도 프레임 라우팅

> **이 SPEC이 닫는 구멍 셋**:
> ① **어휘가 판정자다.** `session.py`의 정규식 라우터 **109개**가 `if/elif` 첫-매치-우선 체인(`:9498~9600`)으로 늘어서 있고, 매치가 곧 행선지다. 어휘를 하나 등록한 대가로 무관한 요청이 영구히 그 핸들러로 끌려간다.
> ② **부정을 읽을 자리가 없다.** 정규식은 `"포지션이 아니라 컬러다"`를 표현하지 못한다. 사용자가 명시적으로 축을 배제해도 같은 핸들러가 다시 잡는다.
> ③ **기하 해석이 조용히 성립한다.** 방향·형상 지시를 좌표 없이 FID 순서로 풀어도 회신에 그 사실이 적히지 않아 사용자가 오해를 잡을 지점이 없다.
>
> **가설이 아니라 2026-08-19 실측이다.**
>
> | 발화 | 잡아간 곳 | 결과 |
> |---|---|---|
> | `"원형 회전 R/G 컬러 페이저 만들어줘"` | `_POSITION_FX_VOCABULARY` circle (`:1755`) | 팬/틸트 서클 생성 · 컬러 무시 · Sequence 201 저장 · Exec 104 배정 |
> | `"컬러 페이저만, 포지션이 아니라"` (2차) | 같은 정규식 | **명시적 부정 무시** · 같은 빌더 재진입 · `Store Sequence 201` failed(점유) |
> | `"지금 이 큐 디머를 30%로"` | `_timeline_edit_target_position` → None → 모델 폴백 | 승인 카드 없이 `Store Sequence 1 Cue 1 /Merge` — Exec 101의 실제 시퀀스는 400이었다 |
> | `"좌→우로 흰색이 파랑으로"` | (좌표 미판독) | FID 1~80 순서를 좌우로 가정 — 실측은 FID 1이 x=+3.0(우측), FID 49~53이 x=−9.0(좌측) |
>
> **왜 중대한가**: ①②는 요청과 다른 오브젝트에 **비가역 쓰기**를 유발한다(`Store Sequence`는 슬롯을 그대로 바꾸고 이 앱에 복원 경로가 없다). ③은 틀린 연출이 "성공"으로 보고되어 무대에서만 발견된다.

## 1. 배경 — 왜 트리거를 정교화하는 방향이 실패하는가

어휘 하나를 추가하면 체인 앞의 모든 요청 해석이 바뀐다. `circle` 어휘에 `원|회전`을 넣은 대가로 **컬러 회전 요청이 영구 봉쇄**됐고, 봉쇄를 푸는 유일한 방법은 어휘를 좁히는 것(= 기존 사용자의 포지션 서클 요청을 깨뜨리는 것)뿐이다. 첫-매치-우선 체인에서 표현력을 늘리는 모든 변경은 이 트레이드오프에 걸린다.

전환의 요지: **어휘의 출력은 `handler`가 아니라 `candidate(축, 근거, 점수)`여야 한다.** 판정은 (a) 명시적 부정, (b) 슬롯 충족도, (c) 필요 시 카드 1장이 한다.

## 2. 요구사항

### M1 — 명시적 부정은 하드 베토

- **REQ-INTENT-001** 포지션 축을 명시적으로 배제한 문장(`포지션/무빙/빔/팬/틸트` + `아니·말고·제외·건드리지`)은 `_position_fx_sequence`의 후보 자격이 없다. 점수·순서와 무관하게 탈락한다.
- **REQ-INTENT-002** 베토는 **좌표 판독 앞**에서 끝난다. 콘솔 왕복 0회, 카드 0장, 저장 0건.
- **REQ-INTENT-003** 베토는 회신을 만들지 않고 `None`으로 빠져 기존 폴백(모델·`compose_fx`)이 같은 문장을 받는다. 컬러 요청에 포지션 질문을 붙이지 않기 위함이다.
- **REQ-INTENT-004** `아니면`(선택 접속)은 부정이 아니다 — `"팬 아니면 틸트로 스윕"`은 베토가 아니다.

### M2 — 축 충돌은 카드 1장

- **REQ-INTENT-005** 비-포지션 속성축(`컬러·색·RGB` / `디머·밝기`)이 주체로 명시되고 포지션 축 단어가 **없으면**, 조용히 포지션을 택하지 않고 카드 1장으로 축을 확정한다.
- **REQ-INTENT-006** 카드는 두 선택지를 제시한다: 속성이 바뀌는 이펙트(장비 고정) / 빔이 움직이는 포지션 이펙트.
- **REQ-INTENT-007** 속성축을 고르거나 **무답**이면 `None`으로 빠진다(fail-closed — 포지션 데이터를 쓰지 않는 쪽).
- **REQ-INTENT-008** 포지션 축 단어가 문장에 이미 있으면 카드를 띄우지 않는다 — 기존 경로가 그대로 돈다.

### M3 — 기하 해석의 근거를 회신에 싣는다

- **REQ-INTENT-009** 좌표에서 기하를 뽑은 핸들러는 회신에 `좌표 해석:` 한 줄을 싣는다 — 좌표 확인 대수 · X/Y 실측 범위 · **"FID 순서가 아니라 콘솔 패치 좌표로 판단"** 명시.
- **REQ-INTENT-010** 이 문장은 저장 성공/실패와 무관하게 붙는다(해석은 저장 전에 이미 확정됐으므로).

### 이연 (이 사이클 범위 밖 — §5)

- **M4** 기하 생성기 6종(`wipe`/`wave`/`rotate`/`radial`/`scatter`/`pulse`) + 큐 프리뷰 편집.
- **M5** 사용자별 해석 기본값 세션 메모리 축적.

## 3. 범위 경계

**포함**: `_position_fx_sequence` 진입 판정 · `_axis_interpretation_note` 헬퍼 · 신규 상수 3종.

**제외(의도적)**:
- 정규식 109개의 일괄 리팩터 — 재현 케이스가 있는 축 하나로 기전을 먼저 검증한다.
- `_fx_position_presets`·`_phaser_recall` 등 형제 핸들러 — 같은 베토가 필요하지만 재현 케이스가 없으므로 M4에서 확장 (§F.1 등재).
- `"지금 이 큐 + 디머"` 폴백 사고 — `_timeline_edit_target_position`의 도메인 공백이며 별도 SPEC 대상. 여기서 고치면 리허설 편집의 승인 불변식을 이 SPEC이 떠안는다.

## 4. 반증 조건

- **REQ-INTENT-001**은 재현 케이스 4문장이 좌표 판독 0회로 빠지지 않으면 반증된다.
- **REQ-INTENT-005**는 `"R/G 컬러가 원을 그리며 도는 시퀀스"`가 카드 없이 저장에 도달하면 반증된다.
- **REQ-INTENT-009**는 회신에 `FID 순서`가 없으면 반증된다.

## 5. 열린 질문

- **Q1** 베토 어휘를 형제 핸들러에 확장할 때, `_BASIC_POSITIONS_REQUEST` 계열의 기존 라우팅 순서 계약(REQ-PRESETGUARD-015)과 충돌하는가? — M4 착수 전 실측 필요.
- **Q2** 축 카드의 무답 기본값을 `None`(포지션 미저장)으로 둔 것은 fail-closed지만, 사용자가 카드를 닫고 같은 문장을 다시 치면 카드가 다시 뜬다. 세션 내 축 결정 캐시(M5)가 필요한가?
