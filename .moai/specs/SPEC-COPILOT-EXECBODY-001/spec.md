---
id: SPEC-COPILOT-EXECBODY-001
title: "익스큐터 할당 시퀀스 아이덴티티 노출 — 안전 게이트 본문 해석 확장"
version: "0.1.0"
status: draft
created: 2026-07-23
updated: 2026-07-23
author: manager-spec
priority: P2
phase: "Post-MVP 연출 UI 하드닝 (v1.1.0 target)"
module: "console/lua/copilot_responder.lua, server/safety/console.py"
lifecycle: spec-anchored
tags: "safety-gate, executor, lua-responder, wire-protocol, reference-resolution, single-press, reverse-address"
tier: L
related_specs: [SPEC-COPILOT-EXECREF-001, SPEC-COPILOT-SHOWUI-001]
---

# SPEC-COPILOT-EXECBODY-001 — 익스큐터 할당 시퀀스 아이덴티티 노출

> **본 SPEC은 SPEC-COPILOT-EXECREF-001(completed)의 직접 후속이다.** EXECREF-001은 안전 게이트가 `Executor`를 인식 가능한 참조 타입으로 인정하도록 만들었으나(S1, 출하됨), 익스큐터 타일 1회 누름의 실제 마찰(승인 카드 1장 + `SaveShow` 1회)은 **줄어들지 않았다** — 콘솔 응답기가 익스큐터 노드의 자식(할당 시퀀스의 큐)을 노출하지 않기 때문이다(EXECREF-001 design.md §5.1 Q2, 4/4 샘플 `childCount: 0`, 아키텍처적 사실). 본 SPEC은 그 구조적 갭을 응답기 확장으로 닫는다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-23 | manager-spec | 최초 작성 (draft, Tier L). 출처: SPEC-COPILOT-EXECREF-001/research.md §5.3 "SPEC-COPILOT-EXECBODY-001 — 익스큐터 할당 시퀀스 아이덴티티 노출" (2026-07-23 라이브 프로브 후 추가된 후속 SPEC 권고). 사용자 결정(이번 세션): SPEC-COPILOT-CUECMD-001(큐 커맨드 프로퍼티 스크리닝, 별도 권고 SPEC)은 번들하지 않는다 — 독립 계획. |

## A. 개요

패널/채팅이 만드는 `Go+ Executor <no>` 커맨드는 EXECREF-001 이후 안전 게이트에 **인식되지만**(참조 타입 `Executor`가 `RECOGNIZED_REFERENCE_TYPES`에 있음), 여전히 **본문을 읽을 수 없어** 매번 보류된다. 원인은 콘솔측 Lua 응답기(`console/lua/copilot_responder.lua`)의 `build_snapshot`이 완전히 범용이라는 데 있다 — 어떤 오브젝트 클래스를 조회하든 `handle:Children()`을 그대로 호출할 뿐, 익스큐터 전용 분기가 없다. grandMA3에서 익스큐터의 시퀀스 할당은 부모-자식 포함 관계가 아니라 프로퍼티/포인터 관계로 노출되므로, 범용 `Children()` 호출은 익스큐터에 대해 항상 빈 배열을 반환한다(EXECREF-001 design.md §5.1 Q2 근본 원인, `.moai/state/verify/showui-m6-resume/5-probe-body.log`).

본 SPEC의 범위는 정확히 두 곳이다:

1. **`console/lua/copilot_responder.lua`의 `build_snapshot` 확장** — 익스큐터 노드에 대해서는 범용 `handle:Children()` 경로 대신, 익스큐터 전용 로직으로 **할당된 시퀀스의 아이덴티티**(시퀀스 번호 또는 그에 준하는 안정적 식별자)를 노출한다.
2. **`server/safety/console.py`의 `StateBodyFetcher`(또는 그 후속 메커니즘) 확장** — 위에서 노출된 아이덴티티를 익스큐터 참조의 본문 해석 진입점으로 사용한다. 시퀀스의 본문(큐 목록)은 이미 신뢰되는 기존 조회 경로다 — `Go+ Sequence N`이 오늘 사용하는 것과 동일한 오브젝트 집합이다.

### 선행 조건 (구현 순서가 아니라 배포 현실)

콘솔측 Lua 변경이 포함되므로, 구현은 순수 Python 변경이 아니다. 확립된 프로젝트 배포 루프를 그대로 따른다: **응답기 Lua 편집 → `plugin_pack.py` 재패키징(네이티브 인라인 Base64) → 콘솔측 Import → 라이브 재검증.** 이 루프 한 사이클마다 실물 콘솔 접근이 필요하다 — plan-phase에서 배포를 가정하지 않는다.

### ⚠️ 핵심 설계 입력 — "역주소 문제" (설계 초반에 명시적으로 다뤄야 함, 각주로 미룰 수 없음)

익스큐터의 **페이지-로컬 자식 인덱스**(오브젝트-트리 경로 해석에 쓰이는 번호 — 실측값 1, 5, 11, 91, 92, 93, 95, 101)와 **콘솔 발화/표시에 쓰이는 번호**(채팅·패널이 만드는 `Go+ Executor <no>`의 `<no>`, 물리 콘솔의 커맨드라인이 이해하는 번호 — 실측값 101, 105, 111, 191, 192, 193, 195, 201)는 **서로 다른 두 숫자 체계**다. 페이지 1에서는 8/8 샘플 전부 `console-no = local-index + 100`이라는 균일한 오프셋이 관측되었다(`.moai/state/verify/showui-m6-resume/executor-offset.jsonl`, EXECREF-001 design.md §5.1 Q1 부속 발견). **이 오프셋이 다른 페이지에서도 성립한다는 보장은 없다** — 페이지 1 8행 외에는 관측이 전무하다.

이 SPEC이 만드는 본문 해석 경로가 (a) 콘솔 발화 번호를 역산해 `(page, local_index)`를 재구성하는 방식이라면, 그 역산은 **미검증 out-of-band 관례**에 안전-인접 코드가 의존하는 것이 된다 — EXECREF-001 REQ-EXECREF-007이 "익스큐터의 표시 이름에서 할당 시퀀스를 파싱하지 않는다"고 금지한 것과 **정확히 같은 취약성 부류**다(둘 다 "관측된 관례가 안정적이라고 가정하고 안전 로직을 얹는" 패턴). EXECREF-001 design.md §5.6이 바로 이 위험을 미리 경고하며 본 SPEC에 설계 입력으로 인계했다.

따라서 본 SPEC은 이 문제를 **회피 우선, 검증 차선**의 순서로 다룬다(B.3 요구사항, plan.md M1):

1. **1순위 — 회피**: grandMA3 Lua API가 콘솔 자신의 커맨드-라인 주소 해석(콘솔이 `Off Executor 201`을 실행할 때 스스로 수행하는 바로 그 해석)에 접근할 수 있는 메커니즘을 제공하는지 조사한다. 존재한다면 페이지-로컬 인덱스 역산 자체가 필요 없어진다 — 콘솔이 자신의 주소 체계를 스스로 풀게 한다.
2. **2순위 — 검증 후 사용**: 회피 메커니즘이 없다면, 오프셋(또는 다른 관례)을 **최소 2개 이상의 서로 다른 페이지**에서 라이브로 검증한 뒤에만 안전 게이트 코드에 반영한다. 검증되지 않으면 해당 메커니즘은 출하하지 않는다.
3. **3순위 — DESCOPE**: 1과 2가 모두 막히면, EXECREF-001 M2가 그랬듯 이 SPEC의 본문 해석 부분을 정직하게 이연한다 — 미검증 관례를 강행 배포하는 것보다 "마찰이 줄지 않음"을 인정하는 편이 안전하다(EXECREF-001 design.md AP-8 원칙 계승).

## B. 요구사항 (GEARS)

### B.1 익스큐터 아이덴티티 노출 (Lua 응답기 측)

- **REQ-EXECBODY-001** [Event-driven] — **When** 콘솔측 Lua 응답기가 클래스가 Executor인 노드를 조회하면, the 응답기 **shall** 범용 자식 열거 대신 익스큐터 전용 로직으로 그 익스큐터에 **할당된 시퀀스의 아이덴티티**(시퀀스 번호 또는 그에 준하는 안정적 식별자)를 스냅샷 페이로드에 노출한다(구체적 함수/파일 앵커는 §E 참조 구현 참고).
- **REQ-EXECBODY-002** [Unwanted] — 익스큐터-시퀀스 아이덴티티 도출 로직 **shall not** 익스큐터의 표시 이름(`name`)을 파싱하는 방식을 사용한다. `name`은 할당된 시퀀스의 표시 이름이며, rename에 깨진다는 사실은 EXECREF-001 REQ-EXECREF-007이 이미 기각한 사유와 동일하다.
- **REQ-EXECBODY-003** [Ubiquitous] — 스냅샷 페이로드 스키마 변경 **shall** 가산적(additive)이며 하위 호환을 유지한다 — 기존 `{name, class, i}` 형상을 읽는 소비자는 무변경으로 계속 동작한다. 스키마가 실제로 바뀌면 `console/lua/PROTOCOL.md`의 `PROTOCOL_VERSION` 범프 관례를 따른다.

### B.2 안전 게이트 본문 해석 (Python 측)

- **REQ-EXECBODY-004** [Event-driven] — **When** 안전 게이트의 본문 해석 메커니즘이 `"Executor <no>"` 참조의 본문을 해석하면, the 메커니즘 **shall** REQ-EXECBODY-001이 노출한 할당-시퀀스 아이덴티티를 해석 진입점으로 사용해, 이미 신뢰되는 시퀀스 본문 조회 경로(오늘의 `Go+ Sequence N` 처리와 동일한 경로)로 위임한다(구체적 클래스/파일 앵커는 §E 참조 구현 참고).
- **REQ-EXECBODY-005** [Unwanted] — 본문 해석 **shall not** 신규 콘솔 경로, 신규 OSC 표면, 또는 기존 OSC 브리지 모듈에 대한 직접 import를 도입한다. 세이프티 모듈의 OSC import 경계 grep 결과는 무변경이어야 한다(EXECREF-001 REQ-EXECREF-005와 동일 계약; 정확한 모듈 경로는 §E 참조 구현 참고).
- **REQ-EXECBODY-006** [Event-driven] — **When** 할당-시퀀스 아이덴티티를 얻을 수 없으면(미할당 익스큐터, 프로퍼티 부재, 상태 질의 실패/타임아웃 포함), the 게이트 **shall** 해당 참조를 보류한다 — 오늘의 fail-closed 동작과 동일하다(보류 처리 함수 앵커는 §E 참조 구현 참고).

### B.3 역주소 문제 (완화의 경계 — 협상 불가)

- **REQ-EXECBODY-007** [Unwanted] — 익스큐터 아이덴티티 해석 메커니즘 **shall not** 관측된 페이지 1의 +100 오프셋 관례(콘솔 발화 번호 = 페이지-로컬 자식 인덱스 + 100)를, 최소 2개 이상의 서로 다른 페이지에서 라이브로 검증되기 전에 일반 해석 규칙으로 하드코딩한다.
- **REQ-EXECBODY-008** [Event-driven] — **When** 해석 메커니즘이 콘솔 발화 번호와 페이지-로컬 주소 사이의 수치적/위치적 관례에 의존하면, the 관례 **shall** 서로 다른 페이지 번호를 가진 최소 2개 페이지에서 라이브로 검증된 이후에만 게이트 로직에 반영된다. 검증이 수행되지 않으면 해당 메커니즘은 출하하지 않는다(plan.md M1이 이 검증을 첫 마일스톤으로 둔다 — 각주 아님).
- **REQ-EXECBODY-009** [Where] — **Where** grandMA3 Lua API가 콘솔 자신의 커맨드-라인 주소 해석에 접근하는 경로를 제공하면, 익스큐터 아이덴티티 해석 메커니즘 **shall** 그 경로를 우선 사용해 페이지-로컬 인덱스 역산 자체를 회피한다. 이는 REQ-EXECBODY-007/008의 검증 부담보다 우선하는 설계 목표다(§A "회피 우선, 검증 차선").
- **REQ-EXECBODY-010** [Event-driven] — **When** REQ-EXECBODY-009의 회피 경로도 REQ-EXECBODY-008의 다중-페이지 검증도 확보되지 않으면, the SPEC 구현 범위 **shall** 본문 해석(M2 이후)을 DESCOPE하고 인식측 변경만(있다면) 출하한다 — EXECREF-001 M2 DESCOPE 선례와 동일한 정직한 부분-성공 프레이밍을 따른다.

### B.4 Fail-closed 보존 (완화의 경계)

- **REQ-EXECBODY-011** [Ubiquitous] — 익스큐터 참조 **shall** 기존 expand-or-hold 기계의 모든 보류 사유를 참조-타입-무관하게 계속 상속한다: 재귀 상한, 순환 탐지, 블랙리스트 본문 보류, 본문 부재 보류, 파싱 불가 라인 보류(EXECREF-001 REQ-EXECREF-009와 동일 계약, 무변경 상속 확인이 회귀 테스트 대상).
- **REQ-EXECBODY-012** [Ubiquitous] — 분류 의미론 **shall** 단일하게 유지된다(기존 `@MX:ANCHOR` — 앵커 위치는 §E 참조 구현 참고). 스크리닝 경로 **shall** 정확히 하나만 존재한다(기존 `@MX:ANCHOR` — 앵커 위치는 §E 참조 구현 참고). 본 SPEC **shall not** 이 두 앵커에 익스큐터 전용 분기·제2 스크리닝을 도입한다.

### B.5 관측 가능한 결과 — 실제 마찰 제거 (EXECREF-001이 달성하지 못한 목표)

- **REQ-EXECBODY-013** [Event-driven] — **When** 해석 가능하고 본문(할당 시퀀스의 큐 목록)이 양성인 익스큐터를 대상으로 `Go+ Executor <no>`가 스크리닝되면, the 게이트 **shall** 승인 요청 0건·`SaveShow` 송신 0건으로 통과시키고, 콘솔 송신 기록은 정확히 `["Go+ Executor <no>"]`가 된다(EXECREF-001 REQ-EXECREF-013이 v0.2.0에서 달성하지 못한 관측 결과의 실제 완결 — 조건부: B.3의 역주소 문제가 DESCOPE되지 않고 실제로 해소된 경우에만).
- **REQ-EXECBODY-014** [State-driven] — **While** 본 SPEC의 익스큐터 아이덴티티 노출 메커니즘이 활성 상태여도, the 게이트 **shall** 기존 안전 불변식 전부를 무변경 유지한다: health gate, 문법 검증, 위험 분류, LiveLock(lock-FIRST 재확인 포함), deny-all 기본 승인 포트, 위험 커맨드 사전 쇼파일 백업 fail-closed, 미확인 이력 재승인·자동 재전송 금지.

### B.6 cue-CMD 갭 — 계승되되 확장되지 않음

- **REQ-EXECBODY-015** [Unwanted] — 본 SPEC **shall not** 게이트가 큐의 CMD(Command) 프로퍼티를 스크리닝한다고 주장하거나 암시한다. 익스큐터의 본문이 시퀀스의 큐로 해석된 이후에도, 그 큐의 "본문 라인"은 여전히 **이름**이지 CMD가 아니다(EXECREF-001 §A "cue CMD 갭" 계승, `console.py:414-432`가 여전히 `payload["children"][*]["name"]`으로 라인을 구성한다면). 이 갭의 봉쇄는 별도 권고 SPEC `SPEC-COPILOT-CUECMD-001`(EXECREF-001 research.md §5.3, 미생성, 본 SPEC과 별도로 계획됨)의 범위다.

### B.7 범위 경계의 명시적 선언

- **REQ-EXECBODY-016** [Unwanted] — 본 SPEC **shall not** `SPEC-COPILOT-CUECMD-001`(큐 커맨드 프로퍼티 스크리닝)의 작업을 번들한다. 두 SPEC 모두 응답기 Lua 재배포를 필요로 하여 시퀀싱 가치가 있을 수 있다는 점은 EXECREF-001 research.md §5.3이 메모로 남겼으나, 실제 번들 여부는 두 SPEC을 함께 계획하는 별도 세션의 사용자 결정에 맡긴다 — 본 SPEC은 EXECBODY 단독으로 완결된다(이번 세션 사용자 결정).
- **REQ-EXECBODY-017** [Unwanted] — 익스큐터 발화의 제2 구문 `Go+ Page <page>.<executor>`(룰북 `10_object_model.md:23-25`) **shall not** 본 SPEC에서 별도 해석 대상이 된다 — 계속 EXECREF-001 REQ-EXECREF-015의 fail-closed 경계(보류)를 상속한다.

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 동일 머신 로컬 공존. OSC는 `127.0.0.1` UDP. site config(`osc_slot`, `receive_port`, `reply_port`)는 항상 effective 값에서 읽는다 — 하드코딩 금지.
- **기능 전제**: `SPEC-COPILOT-EXECREF-001`(completed, HEAD `226e8cb`가 그 sync 커밋)이 안전 게이트에 `Executor` 참조 타입 인식을 도입한 상태다. `SPEC-COPILOT-SHOWUI-001`은 연출 컨트롤 패널을 구현하는 관련 SPEC이다 — 이 워크트리의 트리에서 확인한 바로는 `status: in-progress`이며 git 히스토리가 M1(프로토콜 계약 동결)까지만 진행되어 있다(`git log --oneline -- .moai/specs/SPEC-COPILOT-SHOWUI-001/spec.md`로 확인, 이 세션 기준 — 다른 브랜치/세션에서 더 진행되어 있을 가능성은 배제하지 않되, 이 워크트리 기준으로는 독립 검증되지 않은 완료 상태를 단정하지 않는다). 본 SPEC은 SHOWUI-001의 완료 여부나 특정 마일스톤 상태에 의존하지 않는다 — 본 SPEC이 확장하는 것은 안전 게이트의 본문 해석 능력 자체이며, 이는 SHOWUI-001의 UI 진행 상태와 독립적으로 검증 가능하다. 따라서 `EXECREF-001`(completed 확인됨)은 `depends_on`으로도 참조 가능하나, `SHOWUI-001`은 완료 여부가 본 세션에서 확정되지 않았으므로 `related_specs`(비차단)로만 참조한다 — EXECREF-001·SHOWUI-001의 선례(엄격 충족 전제의 pre-flight 차단 회피)와도 일관된다.
- **기술 스택**: 기존 스택 그대로. **신규 런타임 의존성 0.** Lua 응답기 측도 기존 grandMA3 Lua API 표면 안에서 해결한다(신규 외부 라이브러리 없음).
- **콘솔측**: `console/lua/copilot_responder.lua` **변경 대상**(EXECREF-001과의 핵심 차이 — EXECREF-001은 이 파일을 무변경으로 유지했다). 와이어 프로토콜은 REQ-EXECBODY-003에 따라 가산적으로만 변경 가능; `PROTOCOL_VERSION` 범프 여부는 M2에서 결정한다.
- **배포 루프 전제**: 본 SPEC의 M2 이후 마일스톤은 실물 콘솔 접근 및 `plugin_pack.py` 재배포 사이클을 요구한다. plan-phase는 이 접근을 가정하지 않는다 — M1(역주소 문제 해소)까지는 순수 조사/설계이며, M2부터 배포 루프가 시작된다.
- **미검증 전제 (ASSUMPTION 규율, EXECREF-001 ASSUMPTION-8/9 다음 번호 계승)**:
  - **ASSUMPTION-10 (콘솔 네이티브 주소 해석 API 존재)**: grandMA3 Lua API가 커맨드-라인 문자열(예: `"Executor 201"`)을 핸들로 직접 해석하는 함수를 제공한다. **미검증** — M1에서 조사·확정한다.
  - **ASSUMPTION-11 (오프셋 관례의 다중-페이지 안정성)**: 콘솔 발화 번호 = 페이지-로컬 인덱스 + 100 관례가 페이지 1 이외에서도 성립한다. **미검증, 페이지 1 8/8행만 관측됨**(EXECREF-001 executor-offset.jsonl) — ASSUMPTION-10이 참으로 확정되면 이 가정은 불필요해진다(회피 우선 원칙).
  - **ASSUMPTION-12 (익스큐터→시퀀스 프로퍼티 접근성)**: 익스큐터 핸들이 할당된 시퀀스의 아이덴티티(번호 또는 포인터)를 프로퍼티/접근자로 노출한다 — `Children()`과는 다른 API 경로를 통해서다. **미검증** — M1/M2 조사 대상.
- **측정된 기준선**: 이번 plan-phase 세션 시작 시점 HEAD `226e8cb`(EXECREF-001 완료 sync 커밋). run-phase 킥오프 시점에 신선한 pytest/vitest 기준선을 재측정한다 — EXECREF-001 종료 시점(HEAD `0576553` 이후 `267257f`/`6591efad6`)의 기준선을 그대로 재사용하지 않는다(baseline-integrity 원칙, 이 SPEC의 HEAD가 다르므로).

## D. 제외 범위 (Out of Scope)

### Out of Scope — 큐 커맨드 프로퍼티 스크리닝

- 큐의 CMD/Command 프로퍼티를 게이트가 읽고 분류하는 기능. 이는 별도 권고 SPEC `SPEC-COPILOT-CUECMD-001`(EXECREF-001 research.md §5.3, 미생성)의 범위다. 본 SPEC은 익스큐터→시퀀스 본문 해석만 다루며, 그 본문 라인이 여전히 큐 이름이지 CMD가 아니라는 사실은 변경하지 않는다(B.6).

### Out of Scope — 제2 스크리닝 진입점

- 패널 전용 룰셋, "패널 커맨드는 expansion을 건너뛴다" 류의 좁은 carve-out, 제2 분류기, 실행용 REST 엔드포인트. `gate.py:260-264` + `classify.py:158-161` 두 `@MX:ANCHOR`가 계속 금지한다(REQ-EXECBODY-012).

### Out of Scope — `Go+ Page <page>.<executor>` 구문

- 익스큐터 발화의 제2 구문은 본 SPEC에서 해석 대상이 아니다(REQ-EXECBODY-017). EXECREF-001 REQ-EXECREF-015의 fail-closed 경계를 그대로 상속한다.

### Out of Scope — UI 및 페이더/엔코더 표면

- `server/web/**`, `ui/src/**` 변경 없음. 페이더·엔코더 등 연속 파라미터 표면은 SHOWUI-001 §D에서 이미 이연된 상태 그대로 유지.

### Out of Scope — 다른 미인식/미해석 오브젝트 타입

- `Group`, `Preset`, `World`, `MAtricks` 등 여타 오브젝트 타입의 본문 해석. 각각 고유한 본문 의미론을 가지며 개별 false-negative 검토를 요구한다. 본 SPEC은 `Executor` 하나만 다룬다.

### Out of Scope — SPEC-COPILOT-CUECMD-001 번들

- 큐 커맨드 프로퍼티 스크리닝(위 첫 항목과 동일 SPEC)을 본 SPEC과 함께 계획·구현하는 것. 두 SPEC 모두 응답기 재배포를 요구하여 시퀀싱 가치가 있을 수 있으나(EXECREF-001 research.md §5.3의 시퀀싱 메모), 이번 세션에서는 EXECBODY-001만 독립적으로 계획한다(REQ-EXECBODY-016, 사용자 결정).

## E. 참조 구현 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 참조 원본 (file:line) |
|---|---|
| 익스큐터 노드 조회 시 범용 자식 열거의 실측 실패 | `console/lua/copilot_responder.lua` `build_snapshot`(~429-465행) — `handle:Children()` 호출, 익스큐터 전용 분기 없음. 증거: `.moai/state/verify/showui-m6-resume/5-probe-body.log`(4/4 샘플 `childCount: 0`) |
| 로컬-인덱스 vs 콘솔-발화 번호 이중 체계 | `.moai/state/verify/showui-m6-resume/executor-offset.jsonl`(페이지 1, 8/8행, `local-index + 100 = console-no` 균일) |
| 익스큐터 페이지-로컬 경로 해석(확인됨, ASSUMPTION-8) | `.moai/state/verify/showui-m6-resume/5-probe-body.log` — `DataPool/Pages/<page>/<local-index>` → `ok:true, class:"Executor"` |
| 시퀀스 본문 조회(이미 신뢰되는 진입점) | `server/safety/console.py` `StateBodyFetcher.fetch_body`(414-432행), `DEFAULT_BODY_PATHS`(396-400행) |
| 게이트-감사 상태 조회 seam | `_GateStatePort`(gate.py:114-121), 배선(`bootstrap.py:162`) |
| 참조-타입-무관 보류 기계 | `_evaluate`(expand.py:72-125) |
| 아이덴티티 조회 실패 시 보류 처리 (REQ-EXECBODY-006 근거) | `server/safety/expand.py` `_hold`(보류 처리 함수, `_evaluate`와 동일 파일) |
| 단일 분류 의미론 앵커 (REQ-EXECBODY-012 근거) | `server/safety/classify.py` `classify_command`(158-161행) `@MX:ANCHOR` |
| 단일 스크리닝 경로 앵커 (REQ-EXECBODY-012 근거) | `server/safety/gate.py` `SafetyGate.screen`(260-264행) `@MX:ANCHOR` |
| 이름-파싱 기각의 선례(역주소 문제와 병렬 논증) | EXECREF-001 REQ-EXECREF-007 + design.md §5.6 |
| 익스큐터 주소 규약 | 룰북 `server/rulebook/assets/v2.4.2/10_object_model.md:23-25` — `Page <page>.<executor>` |
| 재생 동사 | 룰북 `31_choreography_patterns.md` "Playback"(`Go+ Executor N` / `Off Executor N`) |
| 프로젝트 확립된 응답기 배포 루프 | `plugin_pack.py`(네이티브 인라인 Base64 배포) — 콘솔측 Import 후 라이브 재검증 필요 |
| ASSUMPTION 번호 체계 계승 | `console/lua/PROTOCOL.md` §6(ASSUMPTION-1~7), EXECREF-001 design.md §5.5(ASSUMPTION-8~9) |
