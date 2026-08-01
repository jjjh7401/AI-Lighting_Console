---
id: SPEC-COPILOT-FXLIB-001
title: "이펙트 어휘 계층 — FX 라이브러리 (Effect Vocabulary Layer)"
version: "0.2.0"
status: completed
created: 2026-07-31
updated: 2026-08-01
author: manager-spec
priority: P1
phase: "Phase 2 연출 계층 — 시간축 어휘 (의도→메모리 파이프라인 1단계)"
module: "server/fx/ (신규), server/orchestrator/tools.py"
lifecycle: spec-anchored
tags: "fx-library, effects, phaser, matricks, sequence-cue, nl-matching, choreography, safety-gate, value-line-guard"
tier: L
related_specs: [SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-SONGCUE-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-FXLIB-001 — 이펙트 어휘 계층 (FX 라이브러리)

> **본 SPEC은 제안서에서 나오지 않았다.** `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md`에는 이펙트 **저작** 항목이 없다 — "이펙트" 문자열은 배경 서술 2건(`:26` 버스킹형 정의, `:52` 현재 앱 요약)뿐이며, 본 plan-phase에서 전수 grep으로 재확인했다(research.md §1). 제안서 밖 출처의 선례는 `SPEC-COPILOT-OVERLAP-001`(spec.md:20, `feature/SPEC-COPILOT-OVERLAP-001` 브랜치)이고 본 SPEC이 두 번째다. 출처는 **사용자 지시 격차 분석(2026-07-31)** — "의도→메모리 파이프라인"의 1단계이며, **LOOKLIB(정지 화면 어휘)의 시간축 자매편**이다: 룩이 "무엇을 켤까"의 디자인 지식이라면, FX는 "그것이 시간 위에서 어떻게 움직일까"의 디자인 지식이다.
>
> **어휘의 원천은 이미 라이브 검증돼 있다.** `server/rulebook/assets/v2.4.2/31_choreography_patterns.md`는 파일 수준으로 "validated live on onPC 2.4.2"를 선언하고(`:7`), 페이저·MAtricks·시퀀스 저장 리터럴을 담는다. 본 SPEC은 그 산문 지식을 **구조화 데이터 + 툴 표면**으로 승격시킨다. 단, "39/39" 류의 검증 카운트는 **리포지토리 어디에도 존재하지 않으므로 인용하지 않는다**(전수 grep 0건 — research.md §2).

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-31 | manager-spec | 최초 작성 (draft, Tier L). 출처: 사용자 지시 격차 분석 2026-07-31(제안서 항목 아님 — 개요 인용주 참조). 조사 방법: 병렬 read-only scout 3개 + 코디네이터 직접 재확인(제안서 grep · 룰북 리터럴 · 코드 슬롯 · 줄 앵커 재실측). 사용자 사전 확정 4건(§A) 반영: ① 어휘 범위(페이저+MAtricks+원형 조합, 다단은 M0 게이트), ② 저장 형태(시퀀스+큐만), ③ 라이브 세션 2회 수용, ④ 브랜치 생성 완료. REQ **21건** · AC **22건** · ASSUMPTION **4건(36~39)** · clarification 마커 **0건** · 라이브 세션 **2회(M0·M7)**. 아티팩트 6종(spec/plan/acceptance/design/research/progress) 동시 생성. |
| 0.2.0 | 2026-07-31 | manager-spec | **M0 라이브 프로브 폴드인** (판정 정본: progress.md §E.2 · 원문 `.moai/reports/m0-probe/raw-log-01.md` §10). 판정: ASSUMPTION-36 **GO**(생성·저장 캡처 성립 / 증거 채널 **부정**) · 37 **GO**(스텝 문법 확립) · 38 **GO**(Speed = BPM) · 39 **GO**(MAtricks 재조회 가능) · `Accel`/`Decel` 곡선 **SKIP**(효과 미관측). 반영: ① **스텝 축을 스키마 필수 1급 필드로 승격**(REQ-FXLIB-001 — 페이저는 2스텝 이상을 요구하며 `Relative`/`Phase`/`Speed`는 변형 커맨드다; v0.1.0의 '다단 필드 선택적'은 철회), ② 번들 형상 전면 개정(design.md §4 — 전 패턴이 `<값>`→`Step 2`→`<값>` 스텝 쌍을 낸다), ③ **REQ-FXLIB-022 신설** — 금지 형태 `Attribute '<attr>' At Step <k>`(`ok:true`이나 효과 없음), ④ REQ-FXLIB-014 (c)를 **무조건 문면**으로 강화(효과는 기계 검증 불가 — 사람 확인 필요), ⑤ **ASSUMPTION-40 신설**(스텝 형상의 Pan/Tilt 일반화 + `Relative`의 스텝 값 성립 여부 — M7 측정, 부정 비용은 Pan/Tilt 패턴 4종의 효과로 한정), ⑥ 값 라인 충돌 가드 등급 상승(design.md §5 — '번들 내 중복이 구조적으로 없다'는 v0.1.0 주장 **철회**). 토큰: REQ **22건** · AC **23건** · ASSUMPTION **5건(36~40)** · clarification 마커 **0건** · 라이브 세션 **2회** 불변. 코드 변경 0. |

## A. 개요

FX(이펙트)는 하나의 **시간축 움직임 패턴**이다: 어떤 attribute가(Pan/Tilt…), 어떤 위상 분포로(Phase 확산·원형 조합), 어떤 속도로(Speed), 어떤 분할 규칙 위에서(MAtricks) 달리는가. 본 SPEC은 (1) 이펙트 패턴 폐쇄 어휘를 담는 **구조화 데이터 계층**(`server/fx/`), (2) 패턴을 실제 리그의 그룹에 얹어 **시퀀스+큐로 저장**하는 MA3 인스턴스화, (3) "부드러운 웨이브 돌려줘" 같은 채팅 지시를 패턴으로 매칭하는 **자연어 매칭**까지를 v1로 정의한다.

아키텍처 전제: **LOOKLIB 파이프라인의 미러 + 전면 재사용**. FX 데이터는 서버측 신규 패키지 `server/fx/`의 정적 YAML 자산이 단일 진실원이고, 커맨드는 문자열로만 구성되며, 실행은 기존 `run_commands` → `gate.screen()` 단일 관문만 쓴다. `server/looks/` 중 `{schema,loader,roles,resolver,instantiate,matching}.py` + `library/`는 **PRESERVE**(OVERLAP spec.md:114-116, `feature/SPEC-COPILOT-OVERLAP-001` 브랜치 — OVERLAP의 잠금 명단은 이 6파일+`library/`이고 busking/report/songcue*는 포함하지 않는다)이며, `busking.py`·`report.py`·`songcue*.py`는 **본 SPEC이 같은 규율로 추가 잠금**한다 — 어느 쪽도 수정하지 않고 **읽기 import만** 한다(§A 결정, design.md §3). 콘솔측 Lua(`copilot_responder.lua`)·룰북 자산·`server/safety/**`는 전부 무변경이다.

### 사전 확정 사실 (사용자 확정 ①~④ — 재질의 금지, 전부 2026-07-31 확정)

- **어휘 범위 (사용자 확정 ①)**: v1 어휘는 **페이저**(`At Relative` / `At Phase … Thru …` / `At Speed` — `31_choreography_patterns.md:68-70`) + **MAtricks 분할 5축**(`PhaseFromX` / `PhaseToX` / `X` / `XWings` / `XShuffle` — `:85-89`, 정리 `Reset Selection MAtricks` `:90`) + **원형 조합**(Pan Phase 0 + Tilt Phase 90 — `:78-79`)이다. **Step/Accel/Decel 다단 문법은 M0 라이브 프로브 게이트 뒤였다**: 룰북 `:75-77`에는 인라인 조각(`Step 2` / `Step 3` / `Step 1 At Accel -100` / `At Decel -100`)만 실재하고 완전한 번들급 커맨드 라인 리터럴이 없었다.
  - **M0 게이트 결과 (2026-07-31 실측 — v0.2.0 폴드인)**: **스텝 문법 GO.** 확립된 생성 형상은 `<값>` → `Step 2` → `<값>`이며(progress.md §E.2), 룰북 `:73`이 이미 그 절차를 적어 두었다 — 미검증이었던 것은 룰북이 아니라 조합의 실측이었다. 이로써 `pulse`/`chase`가 v1에 진입한다. 단 **`Accel`/`Decel` 곡선은 효과 미관측(SKIP)이므로 v1 라이브러리에 값으로 등장하지 않는다** — 그 축에만 DESCOPE 형상(**"스키마 필드 정의 유지 + v1 라이브러리 미사용"** — LOOKLIB `server/looks/schema.py:86-102` MovementSpec "v1 defines this field but does not emit it")을 적용한다.
  - **스텝 축은 게이트 뒤의 부가 기능이 아니라 페이저의 생성 조건이다.** 페이저는 2개 이상의 스텝을 요구하고 `Relative`/`Phase`/`Speed`는 **변형** 커맨드다 — 따라서 스텝 축은 `pulse`/`chase`만이 아니라 **전 패턴**이 낸다(REQ-FXLIB-001, design.md §2.1/§4).
- **저장 형태 (사용자 확정 ②)**: **시퀀스+큐만** — `Store Sequence <n> Cue 1 '<이름>'`(룰북 검증 리터럴 `:71`). **프리셋 저장은 명시적 비목표다**: 프리셋이 페이저 같은 동적 값을 담는지는 미측정이며(리포지토리 실측 기록 0건), 그 축은 씬 컴파일러 후속 SPEC의 몫이다(§D).
- **라이브 세션 2회 수용 (사용자 확정 ③)**: M0 프로브(cycle_type=none, 코드 변경 0) + M7 종단 라이브. LOOKLIB·PRECHK의 2회 회계 선례를 그대로 따르며, 병합 불가 논거는 plan.md §B 말미가 소유한다.
- **브랜치 (사용자 확정 ④)**: `feature/SPEC-COPILOT-FXLIB-001` (origin/main `85a4b23` 기반, 이미 생성됨).

### v1 패턴 폐쇄 어휘 — 무조건 4종 + 게이트 2종

패턴 집합은 **명시 열거된 폐쇄 어휘**다(REQ-FXLIB-002). 무드→설계 표(`31_choreography_patterns.md:236-241` — warm/ballad Speed 10-20 · energetic/club Speed 90-180 · dramatic accelerating)를 값의 **시드**로 쓰되, 그 표는 폴백 설계 지침이지 라이브 검증 결과가 아니다([문서] 등급 — research.md §2).

**전 패턴은 스텝 쌍을 낸다 (M0 귀결).** 아래 골격 열은 전부 `<값>` → `Step 2` → `<값>` 스텝 쌍을 **선행**한 뒤의 **변형 라인**을 가리킨다 — 스텝 쌍 없이 변형 라인만 발화하면 `ok:true` 전량에 모션 0이다(M0 §3 실패 3회).

| 패턴 | 의미 | 스텝 쌍 (M0 형상) + 변형 라인 (검증 리터럴 근거) | 진입 조건 | 효과 실측 |
|---|---|---|---|---|
| `sweep` | Pan 축 위상 확산 (좌우 스윕) | Pan 스텝 쌍 → `At Phase 0 Thru 360` + `At Speed` (`:68-71`) | 무조건 | **ASSUMPTION-40** (M7) |
| `wave` | Tilt 축 위상 확산 (상하 웨이브) | sweep과 동일 골격, attribute만 Tilt | 무조건 | **ASSUMPTION-40** (M7) |
| `circle` | 원형/발리후 | Pan·Tilt 스텝 쌍 → `Attribute 'Pan' At Phase 0` + `Attribute 'Tilt' At Phase 90` (`:78-79`) | 무조건 | **ASSUMPTION-40** (M7) |
| `diagonal` | 대각선 | Pan·Tilt 스텝 쌍 → 동상(0°) 또는 역상(180°) (`:79` 괄호) | 무조건 | **ASSUMPTION-40** (M7) |
| `pulse` | Dimmer 다단 페이저 (사인 딤머) | Dimmer 스텝 쌍 → `At Phase … Thru …` + `At Speed` | **ASSUMPTION-37 GO 확정** | **[실측] — M0 앵커** |
| `chase` | Color 다단 체이스 | ColorRGB 스텝 쌍 → 위상/속도 (`:75`) | **ASSUMPTION-37 GO 확정** | ASSUMPTION-40 계열(attribute 일반화 미측정) |

- **실측 범위의 정직한 표기**: M0가 생성·저장 캡처를 **직접 관측한 attribute는 Dimmer뿐이다.** 따라서 `pulse`가 유일한 `[실측]` 앵커이고, Pan/Tilt(·Color)로의 일반화는 **ASSUMPTION-40**이다. 표의 "무조건"은 **저작 진입**을 뜻하며 **효과 보증이 아니다** — 두 축을 열로 분리한 이유가 그것이다.
- **역방향은 패턴이 아니라 파라미터다**: `At Phase 0 Thru -360`(`:80`)으로 표현되는 `reverse` 불리언 축.
- **`Accel`/`Decel`은 여전히 프로브 대기다**: M0에서 `Step 1 At Accel -100` / `At Decel -100`은 `ok:true`를 받았으나 **효과가 관측되지 않았다(SKIP)**. 무엇을 재면 갈리는가 — 2스텝 페이저 위에 얹고 가감속이 눈에 보이는지 GUI 관측. v1 라이브러리는 이 축에 값을 넣지 않는다.
- **Speed 단위는 확정됐다**: **BPM**(ASSUMPTION-38 GO — GUI 표시 판독). 룰북이 병기했던 3후보(`:70` "BPM/Hz/sec")는 해소됐고, 라이브러리 시드 값(무드→설계 표)은 BPM 해석으로 재보정하며 리포트 문면도 BPM으로 적는다.

## B. 요구사항 (GEARS)

### B.1 FX 데이터 계층 (스키마 + 내장 라이브러리)

- **REQ-FXLIB-001** [Ubiquitous] — FX 스키마 **shall** 다음 축을 정의한다: 아이덴티티(안정적 fx id, 표시 이름, 한국어 별칭/무드 키워드), 패턴 종별(§A 폐쇄 어휘), 대상 attribute, **스텝 축(`steps` — 필수)**, 위상(`phase_from`/`phase_to`), 속도(`speed`), 상대 진폭(`relative`), 역방향(`reverse`), MAtricks 분할 축(`phase_from_x`/`phase_to_x`/`x`/`x_wings`/`x_shuffle` — 전부 선택적), 가감속 곡선(`accel`/`decel` — 선택적, v1 미사용), 명시적 `schema_version`. 후속 소비자(씬 컴파일러·큐리스트 이펙트 축)가 소비 가능한 형상이어야 한다.
  - **스텝 축은 필수다 (M0 귀결 — v0.1.0의 "다단 필드(선택적)"은 철회)**: `steps`는 **길이 ≥ 2의 순서 있는 열**이며 각 원소는 **attribute → 값** 매핑이다. 페이저는 2개 이상의 스텝을 요구하고 `At Relative`/`At Phase`/`At Speed`는 **이미 존재하는 페이저를 변형**할 뿐 **생성하지 않으므로**(progress.md §E.2 실측), `steps` 길이 < 2인 엔트리는 **정의상 페이저를 만들지 못한다**. 스키마는 이를 표현 불가능하게 하고 로더는 명시 에러로 거부한다(REQ-FXLIB-005). 스텝 값은 **절대 수치만** 담는다 — `At Relative <n>`이 스텝 값으로 성립하는지는 ASSUMPTION-40이며 v1은 발화하지 않는다.
  - **`Accel`/`Decel` 필드의 게이트**: 다단 스텝 문법 자체는 ASSUMPTION-37 **GO**로 확정됐으므로 `pulse`/`chase`가 v1 라이브러리에 진입한다. 단 **`accel`/`decel` 곡선 필드는 효과 미관측(M0 SKIP)이므로 정의만 하고 v1 라이브러리는 값으로 사용하지 않는다** — LOOKLIB movement DESCOPE 형상(`server/looks/schema.py:86-102`)과 동형이며, 그 사실은 progress.md에 기록돼 있다.
- **REQ-FXLIB-002** [Ubiquitous] — 내장 라이브러리 **shall** §A의 패턴 폐쇄 어휘만 사용한다: 무조건 4종(`sweep`/`wave`/`circle`/`diagonal`)은 항상, 게이트 2종(`pulse`/`chase`)은 ASSUMPTION-37 GO에서만. 각 엔트리는 무드 키워드·별칭에 **한국어 현장 어휘를 1급**으로 담고, 속도·진폭 값은 무드→설계 표(`31_choreography_patterns.md:236-241`)를 시드로 한다. 집합 밖 패턴 종별은 로더가 명시적 에러로 거부한다(REQ-FXLIB-005).
- **REQ-FXLIB-003** [Ubiquitous] — FX의 커맨드 어휘 **shall** 아래 3구간으로 나뉜 것만 사용한다. 미검증 문법이 프로브 대기 표시 없이 라이브러리에 등장하는 것은 금지된다.
  1. **실측 확정 어휘 (무조건 허용)** — **스텝 생성 라인 `Step <k>`(단독 라인만)** 과 **스텝 값 라인 `Attribute '<attr>' At <값>`(스텝 문맥 안에서만)** — 둘 다 M0 실측(progress.md §E.2) + 룰북 `:73`; 페이저 변형 라인(`At Relative` / `At Phase … Thru …` / `At Speed`, 역방향 `Thru -360` — `:68-70, :78-80`), MAtricks 5축 `Set Selection MAtricks '<축>' <값>` + `Reset Selection MAtricks`(`:85-90`), `Store Sequence <n> Cue 1 '<이름>'`(`:71`), 번들 규율 커맨드(`ChangeDestination Root` `:14`, `ClearAll` `:40-41`), `;` 체이닝(`:39` — **스텝 값 라인에는 쓰지 않는다**, design.md §4.3).
  2. **용도 한정 어휘** — `Pan`/`Tilt`는 **페이저 문맥에서만** 쓴다. `At <n>` 형태는 **스텝 문맥 안에서만** 허용된다: 번들이 `Step <k>` 라인을 담고 해당 attribute의 값 라인이 **2개 이상** 있을 때만 적법하며, 스텝 축 없는 단독 `At <n>`과 `At Absolute …`는 **금지**다(정적 포지션 값 — LOOKLIB 사용자 확정 ① 하드 pan/tilt 금지의 계승, looks 스키마 Band 2 `server/looks/schema.py:46-47` MOVEMENT_ONLY_ATTRIBUTES와 동형). 이 정밀화는 M0 귀결이다 — 스텝 값 라인은 형태상 정적 값과 구별되지 않으므로 **문맥이 구분자**다.
  3. **프로브 대기 어휘 (잔여)** — `At Accel` / `At Decel` 가감속 계열만 남는다. M0에서 `ok:true`는 받았으나 **효과가 관측되지 않았다(SKIP)** — 실측으로 효과가 확인된 리터럴만 진입한다. (`Step <k>` 다단 계열과 그에 얹히는 `Dimmer`/`ColorRGB_R/G/B` 페이저는 ASSUMPTION-37 **GO**로 구간 1에 승격됐다.)
  - **looks 어휘와의 관계**: attribute 이름 집합은 `server/looks/schema.py`의 `KNOWN_ATTRIBUTES`(`:52-54`)와 겹치지만 **정의를 공유하지 않는다** — fx-own 스키마가 자기 허용 집합을 선언하고, looks의 상수는 읽기 import로 참조만 할 수 있다(수정 금지 — PRESERVE, design.md §3).
- **REQ-FXLIB-004** [Unwanted] — FX 데이터 **shall not** per-show 값(구체 그룹 번호·이름, 시퀀스 번호, 큐 번호, FID, 익스큐터 번호)을 포함한다 — 리그 바인딩은 오직 인스턴스화 시점에 일어난다(LOOKLIB REQ-LOOKLIB-004 계승).
- **REQ-FXLIB-005** [Event-driven] — **When** 라이브러리가 로드되면, the 로더 **shall** 스키마를 검증하고 위반을 명시적 에러로 보고한다 — 부분적으로 깨진 라이브러리를 조용히 서빙하지 않는다. 검증 대상: 미지 필드/패턴 종별/attribute, 수치 범위 이탈, 중복 fx id, 게이트 미충족 필드 사용(`accel`/`decel`), **그리고 스텝 축 4종**: ① `len(steps) < 2` 거부(페이저 미성립 — REQ-FXLIB-001), ② 스텝 원소의 attribute 집합이 전 스텝에서 동일하지 않으면 거부(저작 규율), ③ **같은 attribute의 두 스텝이 같은 값이면 거부** — 2번째 값 라인이 dedupe로 접혀 스텝이 1개가 되고 페이저가 무음으로 미성립하기 때문이다(design.md §5), ④ `steps` 없이 변형 축(`phase_*`/`speed`/`relative`)만 선언된 엔트리 거부.

### B.2 자연어 매칭

- **REQ-FXLIB-006** [Event-driven] — **When** 채팅 지시가 움직임/이펙트 표현(예: "부드러운 웨이브", "빠르게 도는 서클", "좌우로 쓸어줘")을 담으면, the 매칭기 **shall** FX 라이브러리의 무드 키워드/별칭/패턴 축에 대해 매칭을 수행한다. 매칭 규율은 `server/looks/matching.py`의 미러다: **한국어 조사 처리**, **폴백 3종**(무매칭/저신뢰/모호), **동점은 None**(임의 선택 금지), **결정론적 정렬**(같은 입력 → 같은 출력).
- **REQ-FXLIB-007** [Ubiquitous] — 매칭의 단일 진실원 **shall** 구조화 FX 라이브러리 데이터이며, `find_fx`는 **라이브러리에 실존하는 엔트리만** 반환한다 — 엔트리 발명·조작은 금지된다.
- **REQ-FXLIB-008** [Event-driven] — **When** 어떤 FX도 신뢰할 만하게 매칭되지 않으면, the 시스템 **shall** 명시적 폴백 신호를 반환하고 기존 룰북 무드 폴백(`31_choreography_patterns.md:236-241` 표)으로 강등한다 — 폴백 경로 자체는 무변경으로 보존된다.

### B.3 MA3 인스턴스화 (게이트 경유, 시퀀스+큐만)

- **REQ-FXLIB-009** [Event-driven] — **When** 사용자가 하나의 FX에 대한 인스턴스화를 지시하면, the 시스템 **shall** 검증 리터럴만으로 커맨드 번들을 구성한다: 선두 `ChangeDestination Root` 정확 1회(`:11-23`) → `ClearAll` → 그룹 선택(bare `Group <n>` **번호형 단일** — `:27-31`, `Select` 접두 금지. 번호형만 라이브 검증됐고(`server/looks/instantiate.py:302-304` 주석) 인용명형 `Group '<이름>'`은 문법 유도([문서] — `:200-201`, `00_grammar.md:107`)이므로 v1은 발화하지 않는다 — 이름으로 지정된 그룹도 rig context 등재 번호로 변환해 번호형으로 발화한다) → **스텝 열**(스텝 1의 값 라인들 → `Step 2` → 스텝 2의 값 라인들 → … — **스텝 ≥ 2**, M0 실측 형상) → 페이저 변형 라인들(`At Phase … Thru …` / `At Speed`) → (패턴이 선언한 경우만) MAtricks 라인들 → `Store Sequence <n> Cue 1 '<라벨>'` → (MAtricks 사용 시) `Reset Selection MAtricks` → `ClearAll`. **산출물은 시퀀스+큐뿐이다**(사용자 확정 ②).
- **REQ-FXLIB-010** [Ubiquitous] — 인스턴스화 번들 **shall** 검증된 프로그래밍 규율을 따른다: 목적지 1회, 캡처 전·Store 후 `ClearAll`(트래킹 오염 방지 — `:40-41`, `:128-134`), MAtricks를 쓴 번들은 Store 후 `Reset Selection MAtricks`로 서브선택을 정리(`:90` — 다음 번들 오염 방지), 라벨은 Store 리터럴에 인라인(`:71`). **스텝 규율(M0 실측)**: `Step 1` 라인은 발화하지 않고(첫 스텝이 현재 스텝이다), 둘째 스텝부터 **단독 `Step <k>` 라인**을 그 스텝의 값 라인 **앞에** 놓으며, 스텝 값 라인은 `;` 체이닝하지 않는다(스텝 문맥과의 조합 미측정 — design.md §4.3). 변형 라인(`At Phase`/`At Speed`)은 **스텝 열이 끝난 뒤**에 온다 — 변형은 이미 존재하는 페이저에만 걸린다.
- **REQ-FXLIB-011** [Ubiquitous] — **값 라인 충돌 가드 (1급 요구 — 경계 2중)**:
  - **(a) 번들 내 경계 (구성 시점)**: 번들 구성기 **shall** 구성 완료 시점에 비면제 커맨드 문자열의 **번들 내 유일성**을 검사하고, 중복이 존재하면 번들을 **생성하지 않고** 명시적 에러(`VALUE_LINE_COLLISION` 동형 사유 — `server/looks/busking.py:230-237` 계승)로 보고한다.
  - **(b) 지시 턴 경계 (교차 호출 — 실행 결과 시점)**: dedupe의 실제 경계는 번들이 아니라 **지시 턴 전체(instruction-scoped)**다 — `executed_ok`는 툴 호출을 넘어 축적되고(`server/orchestrator/runner.py:216` `ExecutionContext(executed_ok=frozenset(executed_ok))`), 판정 주석 원문이 "either **in a prior tool call** (context.executed_ok) or earlier in THIS bundle"이다(`tools.py:603-609`). 같은 지시 턴의 앞선 호출이 발화한 값 라인을 구성기는 구성 시점에 볼 수 없으므로, the 툴 **shall** 실행 결과의 커맨드별 outcome을 검사해 **비면제 라인에 `skipped_already_executed`가 1건이라도 있으면 해당 인스턴스화를 성공으로 보고하지 않고** 교차 호출 충돌을 명시적 실패로 보고한다(REQ-FXLIB-014 (b)와 한 쌍). `context.executed_ok`가 툴 등록 계층에서 도달 가능하면(디스패치가 ExecutionContext를 전달 — `tools.py:496`) 실행 **전** 대조·거부로 강화할 수 있다(불완전 Store 자체를 차단) — 도달 가능성 확정은 M4/M5 착수 시 `[코드]` 실측 몫이며, outcome 검사는 그와 무관하게 유지되는 최소 방어선이다.
  - **근거**: `run_commands`의 dedupe는 면제 3종(`Clear` / `ClearAll` / bare `Fixture|Group` 선택 — `:283-287` `_PROGRAMMER_STATE_COMMANDS`) 외의 중복 문자열을 **재실행하지 않는다**. 값 라인은 그룹과 무관한 문자열이므로, **한 지시 턴에서 같은 패턴을 두 그룹에 인스턴스화하면(자연스러운 버스킹 흐름) 2번째 번들의 값 라인 전량이 `skipped_already_executed`로 접히고 Store(시퀀스 번호가 달라 유일 문자열)만 실행된다** — 빈 프로그래머 Store 무음 성공, BUSKWIZ 함정의 교차 호출 재현이다. 부분 실패 후 자기 교정 재시도 경로도 동일 위험이다. dedupe 규칙 자체의 개정은 **기각된 선례**이므로(BUSKWIZ 결정) 회피는 **형상 + 검출**로 한다.
  - **M0 이후의 등급 상승 (v0.2.0 — 이 요구가 방어적 항목에서 상시 검사로 바뀐 지점)**: 스텝 축이 들어오면서 v0.1.0의 두 가정이 모두 깨졌다. ① **번들 내 유일성은 더 이상 구조적 보장이 아니다** — 한 패턴이 같은 attribute에 스텝 수만큼 값 라인을 내고 `Attribute 'Dimmer' At 100`/`At 0`은 값만 다르므로, 두 스텝에 같은 값을 적으면 2번째가 접혀 **스텝 1개짜리 프로그래머로 Store**가 실행된다(모션 0, 무음). 로더가 1차로 거부하고(REQ-FXLIB-005 ③) 가드 (a)가 구성 시점에 최종 차단한다. ② **교차 호출 충돌의 성립 조건이 넓어졌다** — 스텝 값 라인은 어휘에서 가장 일반적인 문자열이고, 결정적으로 **`Step 2` 라인이 전 패턴 공통**이며 면제 3종에 속하지 않는다(`[코드]` — 착수 직전 재실측 대상). 따라서 **같은 지시 턴의 2번째 인스턴스화는 서로 다른 패턴이어도 `Step 2`부터 접힌다.** 귀결로 **v1은 지시 턴당 `instantiate_fx` 1회만 온전히 성립하며, 2회차 이상은 경계 (b)가 명시 실패로 보고한다**(조용한 부분 성공 금지 — 리포트 문면은 REQ-FXLIB-014 (b), 설계 논거는 design.md §5).
- **REQ-FXLIB-012** [Unwanted] — the 인스턴스화 **shall not**: (a) 어떤 경로로도 `Store /Overwrite`를 발화하지 않고(블랙리스트 `Store /overwrite` — 승인 보류 하한선), (b) 기존 시퀀스 번호에 무플래그 Store를 시도하지 않으며(콘솔이 "Not allowed"로 거부 — SONGCUE progress.md:344 실측, 안전 방향이지만 계획된 경로가 아니다), (c) 시퀀스 번호를 발명하지 않는다 — 신규 번호는 **재조회(`DataPool/Sequences` — `tools.py:120`)로 실측한 빈 번호만** 쓰고, 재조회 결과의 `truncated`가 참이면(절단 상한 max_children=24 — SONGCUE F-3) 자동 배정을 **거부**하고 명시 보고한다. 새 큐 번호의 Store는 플래그 불요다(SONGCUE 실측).
- **REQ-FXLIB-013** [Unwanted] — the 시스템 **shall not** 익스큐터를 자동 배치하지 않는다 — 빈 익스큐터는 식별 불가다(BUSKWIZ 측정 2). `Assign Sequence <n> At Executor <m>`(`:99`)은 **사용자가 익스큐터 번호를 명시 지정한 경우에만** 선택적으로 번들 말미에 붙는다.
- **REQ-FXLIB-014** [Event-driven] — **When** 인스턴스화가 완료되면, the 시스템 **shall** 한국어 2단 리포트(요약 1단 + 상세 1단 — `server/looks/report.py` 선례)를 반환한다: (a) 생성 시퀀스·큐·라벨·대상 그룹·패턴, (b) 실행 결과(발화 커맨드 수; 실패 시 stop-on-first-failure로 인한 `not_executed` 목록 전파; **비면제 라인의 `skipped_already_executed` 발생 시 그 목록도 전파하고 성공 보고를 금지한다** — 교차 호출 dedupe 접힘은 실패로 보고하며, 이미 실행된 Store로 불완전 시퀀스·큐가 생성됐을 수 있음을 문면에 명시한다, REQ-FXLIB-011 (b)), (c) **효과 증거 상태 — 기계 검증 불가의 무조건 명시**: `Cmd` 접수 `ok`는 효과 증거가 아니며(BUSKWIZ progress.md:275-283, :314), M0 실측으로 **이펙트 효과의 기계 증거 채널이 부정임이 측정된 경계로 확정됐다** — 저장된 큐는 `Cue → Part(childCount 0)`에서 트리가 바닥나고 **내용이 있는 큐와 빈 큐가 구별되지 않으며**, `Phase`·`Speed`·`CueFade`는 `"property not readable"`이고, 픽스처 실시간 값도 읽히지 않으며, MA3는 이펙트를 별도 풀에 두지 않는다(progress.md §E.2 · raw-log-01.md §10.3). 따라서 리포트 **shall** "**이 축의 효과는 기계로 확인되지 않는다 — 무대/GUI에서 사람이 확인해야 한다**"는 취지를 **항상** 싣는다(ASSUMPTION-36 분기 조건부가 아니라 **무조건**이다). 재조회로 확인 가능한 것은 **시퀀스·큐의 존재**뿐이며, 그것을 효과 확인으로 제시하는 것은 금지된다. 부분 성공을 전체 성공으로 위장하지 않는다. Speed는 **BPM**으로 적는다(ASSUMPTION-38 GO).

### B.4 툴 표면

- **REQ-FXLIB-015** [Event-driven] — **When** 모델이 `find_fx`를 호출하면, the 툴 **shall** 매칭 결과(REQ-FXLIB-006)를 반환하고, 무매칭 시 폴백 신호를 반환한다(REQ-FXLIB-008). 룰북 자산은 PRESERVE이므로 **툴 발견성은 툴 스키마 설명에만 실린다** — 룰북 고정 프리픽스에 안내 축을 추가하지 않는다(REQ-FXLIB-020).
- **REQ-FXLIB-016** [Event-driven] — **When** 모델이 `instantiate_fx`를 호출하면, the 툴 **shall** fx id + 대상 그룹 + (선택) 시퀀스 번호/익스큐터 번호를 받아 번들을 구성하고 기존 `run_commands` 경로로만 실행한다. 대상 그룹은 **rig context 재조회에 등재된 실존 그룹만** — 등재되지 않은 그룹 번호·이름의 발명은 금지되고(`31_choreography_patterns.md:210-211` "NEVER invent a `Group 3`"), `Fixture <slot>` 직접 타깃은 금지된다(슬롯≠FID).

### B.5 안전·경계 규율 계승

- **REQ-FXLIB-017** [Unwanted] — 단일 초크포인트: `server/fx/` **shall not** 어떤 transport(`server.bridge`/`pythonosc`)도 import하지 않는다 — 커맨드는 문자열로만 구성되고, 실행은 `run_commands` → `gate.screen()` 경로 하나다. 신규 `server/fx/`는 `server/tests/test_architecture.py`의 전역 import 스캔에 **자동 포섭**되며(`:12-13` "any NEW module … touching the bridge fails this test"), `_NAMED_TOOL_EXEMPTIONS`(`:34-39`)에 예외를 추가하는 것은 금지된다.
- **REQ-FXLIB-018** [State-driven] — **While** LiveLock이 활성인 동안, FX 인스턴스화 **shall** 제안(Proposal) 전용으로 강등되고 콘솔 송신은 0건이다 — `run_commands` 경로 소비의 귀결이며, 본 SPEC은 그 강등 기제를 소비만 하고 수정하지 않는다.
- **REQ-FXLIB-019** [Ubiquitous] — 기존 안전 불변식 전부 **shall** 무변경 유지된다. 스크리닝 의미론: 닫힌 블랙리스트 아래에서 `Phase`/`Speed`/`MAtricks`/`At`/무플래그 `Store`는 보류 없이 통과하고, `Off …` 변형은 invoking-verb expand-or-hold에 걸리며, 이는 전부 **현행 의미 그대로**다 — `server/safety/**` 변경 0건, 승인 대기 0건.
- **REQ-FXLIB-020** [Unwanted] — the 본 SPEC **shall not** 룰북 자산(`server/rulebook/assets/v2.4.2/**`)과 고정 프리픽스를 변경하지 않는다(PRESERVE — byte-diff 0). 구조화 FX 데이터 본문을 프리픽스에 담는 것도 금지된다(LOOKLIB REQ-LOOKLIB-022 계승).
- **REQ-FXLIB-021** [Ubiquitous] — 매칭·툴 표면 **shall** 제공자 중립(anthropic/gemini 공통 — `server/llm/factory.py` 선례)으로 동작한다.
- **REQ-FXLIB-022** [Unwanted] — **금지 형태 `At Step <k>`**: 라이브러리 자산과 번들 산출물 **shall not** `Attribute '<attr>' At Step <k>` 형태를 포함한다. 이 형태는 콘솔이 **`ok:true`로 접수하지만 의도한 효과가 없다**(M0 실측 — progress.md §E.2, raw-log-01.md §10.0: M0 프로브 자신이 이 형태를 발화해 페이저 생성에 실패했고, 그것이 실패 3회의 직접 원인이었다). 스텝 전환은 **단독 `Step <k>` 라인**으로만 발화하고 그 뒤에 해당 스텝의 값 라인을 잇는다(REQ-FXLIB-010). **`ok`를 성공 신호로 읽으면 무음 실패가 되는 축**이므로 — 그리고 효과는 기계로 확인되지 않으므로(REQ-FXLIB-014 (c)) 사후 검출 수단이 없으므로 — 형태 자체를 금지하고 로더·번들 양쪽에서 전수 차단한다.

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 동일 머신 로컬 공존, OSC `127.0.0.1` UDP. site config는 effective 값에서만 읽는다 — 하드코딩 금지.
- **기능 전제**: LOOKLIB 계층(`server/looks/` — 스키마/로더/매칭/인스턴스화/버스킹/리포트, `status: completed`), SONGCUE·BUSKWIZ(머지 완료 — PR #6), PRECHK(머지 완료 — PR #7, 현 origin/main `85a4b23`), MVP 파이프라인(`run_commands`·`gate.screen()` 단일 관문·승인/제안 카드), `get_rig_context` 재조회 + 드릴다운. 전부 `related_specs`(비차단) 참조이며, **run-phase 킥오프 시 각 전제의 실제 상태를 재확인하고 어긋남을 progress.md에 기록한다**(LOOKLIB §C 선례).
- **실행 특성 (선행 SPEC 실측 전재 — [실측] 원출처는 해당 SPEC 기록)**: `run_commands`는 stop-on-first-failure이며 실패 이후 커맨드는 `not_executed`로 전파된다. 번들 규모 기준선은 87줄/5.77s, 줄당 ~66ms(66.3-66.7ms — BUSKWIZ progress.md:278-281 실측 전재) — v1 FX 번들은 십수 줄 규모이므로 여유가 크다.
- **미검증 전제 (ASSUMPTION 규율 — OVERLAP이 31~35를 사용, 본 SPEC은 36부터)**. 36~39는 M0에서 실측했고, 40은 M0가 **새로 열었다**. **각각이 실제로 막는 대상은 서로 다르다**(plan.md §A.2 표 소유 — LOOKLIB의 순서 결함 교훈 계승):
  - **M0 판정 요약 (2026-07-31 실측 — 정본은 progress.md §E.2, 원문은 `.moai/reports/m0-probe/raw-log-01.md` §10; §7은 SUPERSEDED)**: ASSUMPTION-36 **GO** · 37 **GO** · 38 **GO** · 39 **GO** · `Accel`/`Decel` 곡선 **SKIP**(효과 미관측). 아래 네 항목의 본문은 **판정 전 문면을 보존**하고 각 항목 말미에 판정을 덧붙인다 — 무엇을 몰랐고 무엇이 답이 됐는지가 함께 읽혀야 한다.
  - **ASSUMPTION-36 (저장 큐의 페이저 효과 증거 채널)**: 저장된 큐가 페이저 모션을 실제로 담고, 그 값을 **재조회로 판독**할 수 있다. **미검증** — 재조회로 페이저 값을 확인한 기록은 리포지토리에 0건이고, rig snapshot은 페이저와 정적 값을 구분하지 못한다(`server/web/panel.py:78-82`). **M0 1순위.** 막는 대상: **M4의 리포트 문면(REQ-FXLIB-014 (c)) + M7의 증거 형상**. 부정 실측 시 본 SPEC은 이 축을 **"기계 재조회로 효과 증거를 얻을 수 없는 축"으로 명기**하고, M7 종단 확인을 GUI 사람 관측으로 강등하며 리포트 문면에 그 한계를 싣는다 — 기능 자체의 DESCOPE가 아니라 **증거 채널의 정직한 축소**다.
    - **M0 판정: GO (기능) / 부정 (증거 채널)** — 기능은 성립한다: 프로그래머를 `ClearAll`로 비운 뒤 저장물만 발화한 상태에서 모션이 관측됐으므로 **생성과 저장 캡처가 한 관측으로 동시에 증명**됐다. 그러나 증거 채널은 **부정으로 확정**됐고 이는 추측이 아니라 **측정된 경계**다 — 큐 트리는 `Cue → Part(childCount 0)`에서 바닥나 내용 있는 큐와 빈 큐가 구별되지 않고, `Phase`/`Speed`/`CueFade`는 `"property not readable"`이며, 픽스처 실시간 값도 읽히지 않고, MA3는 이펙트 전용 풀을 두지 않는다. 발동된 분기: 리포트 문면의 **무조건** 한계 명시(REQ-FXLIB-014 (c)) + M7 인수의 GUI 관측 강등(AC-FXLIB-022). **사람의 GUI 관측이 이 SPEC에서 효과의 유일한 증거 채널이다.**
  - **ASSUMPTION-37 (Step/Accel/Decel 다단 문법 완전형)**: onPC 2.4.2가 수용하는 다단 페이저 커맨드 리터럴이 존재한다. **미검증** — 룰북 `:75-77`은 인라인 조각만 담고 완전한 번들급 커맨드 라인 리터럴이 없다(조합 문법 미검증). 막는 대상: **M2(pulse/chase 저작) + M1 스키마 다단 필드의 사용 여부**. GO면 실측 리터럴만 REQ-FXLIB-003 구간 3에 진입, 부정이면 REQ-FXLIB-001 게이트 발동(필드 정의 유지 + v1 미사용) — **네 항목 중 유일하게 저작(M2)을 실제로 막는 항목이다.**
    - **M0 판정: GO** — 확립된 형상은 `<값>` → `Step 2` → `<값>`이며, 룰북 `:73`이 이미 그 절차를 적어 두었다(*"set a value, `Step 2`, set the next value"*). **틀린 것은 룰북이 아니라 그 줄을 놓친 프로브였다** — 문서와 관측이 어긋날 때 문서를 먼저 의심한 것이 성급했다는 기록이 raw-log-01.md §10.0에 보존돼 있다. 발동된 분기: `Step <k>` 계열이 REQ-FXLIB-003 **구간 1로 승격**되고 `pulse`/`chase`가 v1에 진입한다. **잔여**: `At Accel`/`At Decel`은 `ok:true`이나 **효과 미관측(SKIP)** — 구간 3에 남고 v1 라이브러리는 값으로 쓰지 않는다. **파급**: 이 판정은 게이트 2종만 여는 데 그치지 않고 **전 패턴의 번들 형상을 바꿨다**(스텝 축 필수 — REQ-FXLIB-001).
  - **ASSUMPTION-38 (Speed 단위)**: `At Speed <n>`의 n이 무엇(BPM/Hz/sec)인지 확정 가능하다. **미확정** — 룰북 자신이 3후보를 병기한다(`:70`). 막는 대상: **없음(차단 아님)** — 발화 문법은 검증돼 있으므로 M0는 해석만 실측해 기록하고, 라이브러리 시드 값 재보정과 리포트 문면에 반영한다. 의도적 배칭.
    - **M0 판정: GO — 단위는 BPM** (GUI Speed 표시 판독). 룰북이 병기했던 3후보(`:70`)는 해소됐다. 반영: 라이브러리 시드 값의 BPM 해석 재보정 + 리포트 문면 표기(REQ-FXLIB-014 (c)).
  - **ASSUMPTION-39 (MAtricks 풀 재조회 가능성)**: `DataPool/MAtricks` 경로(`tools.py:125` — 매핑만 존재, 실측 0건)로 MAtricks 상태를 재조회할 수 있다. 막는 대상: **없음(v1 형상 불변)** — v1은 `Set Selection`/`Reset`만 쓰므로 부정이어도 형상이 바뀌지 않고 **증거 채널의 폭**만 기록된다. 의도적 배칭.
    - **M0 판정: GO** — `state 'DataPool/MAtricks'` → `childCount 1`(`MAtrick 11 'Wave'`), `truncated:false`. v1 형상은 예정대로 불변이며 증거 채널의 폭만 넓어졌다.
  - **ASSUMPTION-40 (스텝 생성 형상의 Pan/Tilt 일반화 — M0가 새로 연 항목)**: M0가 **Dimmer로 확립한** 2스텝 생성 형상(`<값>` → `Step 2` → `<값>`)이 **Pan/Tilt에서도 동일하게 성립하며**, `At Relative <n>`이 **스텝 값**으로 쓰일 수 있는가. **미측정** — M0의 관측은 Dimmer 축에서만 이뤄졌고(progress.md §E.2), `Relative 30`은 **1스텝(페이저 미성립) 문맥에서만** 발화돼 그 문맥에서는 무엇도 판정될 수 없었다(raw-log-01.md §3 시도 3). 실측을 조용히 일반화하지 않기 위해 별도 항목으로 연다.
    - **측정 시점: M7 종단 라이브.** ASSUMPTION-40은 **M0가 판정하지 않은 신규 항목**이므로 M7 측정은 **재측정이 아니다** — AC-FXLIB-021의 "M0 판정 덮어쓰기 금지"와 충돌하지 않는다.
    - 막는 대상: **없음 — v1 저작은 그대로 진행한다.** 형상을 게이트해 두었으므로 **부정 실측의 비용은 Pan/Tilt 패턴 4종(`sweep`/`wave`/`circle`/`diagonal`)의 효과에 한정**되고, 스키마·로더·매칭·툴·리포트 계층은 **무영향**이다: 스텝 축 자체는 Dimmer 실측으로 이미 정당화됐고(`pulse`가 그 축의 `[실측]` 앵커다), 부정 시 필요한 것은 Pan/Tilt 스텝 값의 재저작 또는 후속 프로브뿐이다.
    - 형상 게이트의 구체: v1 라이브러리는 스텝 값을 **절대 수치로만** 저작하고 `At Relative`를 **발화하지 않는다**(design.md §2.1/§4) — 미측정 형태를 기본 경로에 넣지 않는다는 본 SPEC의 규율(REQ-FXLIB-003)의 적용이다.
- **측정된 기준선**: 브랜치 `feature/SPEC-COPILOT-FXLIB-001`, 기반 origin/main `85a4b23`. pytest/vitest 수치는 plan-phase가 단언하지 않는다 — **각 마일스톤 착수 직전 직접 실측**한다(baseline-integrity 원칙, PRECHK plan.md §B 관례). 본 아티팩트 6종의 커밋 SHA는 자기참조 불가이므로 `pending-backfill`이다(LOOKLIB F4 교훈).

## D. 제외 범위 (Out of Scope)

### Out of Scope — 프리셋 저장 형태

- FX를 프리셋으로 저장하는 축 일체. 프리셋이 페이저 동적 값을 담는지는 **미측정**이며(재조회 확인 기록 0건), 룩(정지 값)과 이펙트(동적 값)의 프리셋 의미론이 같다는 보장이 없다. 이 축은 씬 컴파일러 후속 SPEC의 몫이다 (사용자 확정 ②).

### Out of Scope — 익스큐터 자동 배치·바인딩

- 빈 익스큐터 탐색·자동 `Assign` 일체 — 빈 익스큐터는 식별 불가다(BUSKWIZ 측정 2). 사용자 명시 지정 시의 `Assign Sequence <n> At Executor <m>` 리터럴 1줄만 선택적으로 허용된다(REQ-FXLIB-013).

### Out of Scope — 지시 턴당 2회 이상의 인스턴스화 (M0 귀결)

- 한 지시 턴에서 `instantiate_fx`를 2회 이상 온전히 성립시키는 축. dedupe 경계가 **지시 턴 전체**이고 `Step <k>`·스텝 값 라인이 패턴 간 공통 문자열이므로, 2회차 번들은 접힌다(design.md §5). 경계를 넓히려면 dedupe 규칙 자체를 다뤄야 하고 그 개정은 **기각된 선례**다(결정 E). v1은 넓히는 대신 **명시 실패로 막는다**(REQ-FXLIB-011 (b)) — 조용한 부분 성공을 만들지 않는 것이 이 축의 선택이다.

### Out of Scope — Accel/Decel 가감속 곡선 (M0 SKIP)

- `Step <k> At Accel <n>` / `At Decel <n>`의 v1 사용 일체. M0에서 `ok:true`는 받았으나 **효과가 관측되지 않았다** — 무엇을 재면 갈리는가: 2스텝 페이저 위에 얹고 가감속이 눈에 보이는지 GUI 관측. 스키마는 필드를 정의하되 v1 라이브러리는 값으로 쓰지 않는다(REQ-FXLIB-001 — LOOKLIB movement DESCOPE 형상 동형).

### Out of Scope — MAtricks 풀 오브젝트

- `Store MAtricks <n>` / `Label` / `Call MAtricks <n>`(`:93-94`)의 풀 오브젝트 저장·재사용. v1 MAtricks 어휘는 `Set Selection` + `Reset`뿐이다 (사용자 확정 ①). ASSUMPTION-39는 재조회 가능성만 기록한다.

### Out of Scope — 스트로브·셔터 이펙트

- 스트로브/셔터 값을 담는 FX 일체 — `server/web/preview.py:131-139`가 `danger`(관객·카메라 직접 영향)로 분류하는 영역이며, LOOKLIB의 사전 결정 규칙(기본 제외)을 그대로 계승한다.

### Out of Scope — 정적 포지션 값

- `At Absolute …`·하드 pan/tilt 정적 값 일체. Pan/Tilt는 페이저 값 라인 안에서만 산다(REQ-FXLIB-003 구간 2).

### Out of Scope — 큐 트리거 자동화

- `Set Cue … Property 'TrigType' …`(`:111`) 류 트리거/팔로우 설정. 그 축은 SONGCUE(큐리스트)의 영역이며, v1 FX는 단일 큐 시퀀스만 만든다.

### Out of Scope — 생성형 Lua 경로

- FX 인스턴스화를 Lua 플러그인 생성으로 구현하는 축. v1 번들은 커맨드라인 문자열로 충분한 규모다.

### Out of Scope — UI 표면 변경

- `ui/src/**` 및 패널 타일 추가. v1 표면은 기존 채팅 + 툴 2종이다.

### Out of Scope — 콘솔측 Lua 변경

- `console/lua/copilot_responder.lua` 및 신규 프로토콜 동사 일체 (PRESERVE).

### Out of Scope — 비게이트 실행 경로

- 실행용 REST 엔드포인트, 제2 스크리닝, `server/fx/`의 OSC 표면 직접 import (REQ-FXLIB-017).

### Out of Scope — 룰북 자산 변경

- `server/rulebook/assets/v2.4.2/**` 일체 (PRESERVE — OVERLAP spec.md:114-116 계승). `find_fx` 발견성은 툴 스키마 설명에만 실린다(REQ-FXLIB-015).

## E. 참조 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 참조 원본 (file:line — 착수 직전 재실측 관례 적용) |
|---|---|
| **M0 판정 정본** (스텝 생성 문법 · 증거 채널 부정 · 판정 4건 · 귀결 3건) | `.moai/specs/SPEC-COPILOT-FXLIB-001/progress.md` §E.2 — `[실측]` |
| **M0 원문 전량** (§7은 SUPERSEDED, §10이 정본, §0·§10.0은 자기 정정 2건) | `.moai/reports/m0-probe/raw-log-01.md` §10 — `[실측]` |
| 페이저는 2스텝 이상을 요구한다 (제조사 문서) | `help.malighting.com/grandMA3/2.0/HTML/phaser.html` — `[문서]` (raw-log-01.md §10.0 인용) |
| 스텝 절차 서술 (M0가 뒤늦게 재발견한 줄) | `31_choreography_patterns.md:73` — `[문서]`, M0에서 `[실측]`으로 확인 |
| 페이저 검증 리터럴 (Relative/Phase/Speed/Store) | `31_choreography_patterns.md:61-73` (Speed 단위는 M0에서 **BPM** 확정 — `:70`의 3후보 병기는 해소) |
| 원형 조합·역방향 | `31_choreography_patterns.md:78-80` |
| MAtricks 5축 + Reset | `31_choreography_patterns.md:85-90` |
| 다단 문법 조각 — 완전 리터럴 부재 (M0 대상) | `31_choreography_patterns.md:75-77` |
| 무드→설계 시드 표 | `31_choreography_patterns.md:236-241` |
| 그룹 발명 금지·슬롯≠FID | `31_choreography_patterns.md:202-211` |
| 트래킹 모델·ClearAll 규율 | `31_choreography_patterns.md:40-41, 128-134` |
| looks 스키마 빈 슬롯 (MovementSpec — 미러 원형) | `server/looks/schema.py:46-47, 52-54, 86-102, 116` |
| 번들 규율 기계화 선례 | `server/looks/instantiate.py:1-31, 59-71` |
| 값 라인 충돌 사유 코드 선례 | `server/looks/busking.py:230-237` |
| instruction-scoped dedupe 판정 + 면제 3종 | `server/orchestrator/tools.py:241-293, 603-609` |
| dedupe 비교 집합의 교차 호출 축적 (`executed_ok`) | `server/orchestrator/runner.py:216` |
| 재조회 경로 표 (sequences·matricks) | `server/orchestrator/tools.py:117-127` |
| 단일 초크포인트 자동 스캔 | `server/tests/test_architecture.py:1-39` |
| rig snapshot의 페이저 비구분 | `server/web/panel.py:78-82` |
| PRESERVE 게이트 (looks 6파일+library/·룰북·dedupe 루프 — busking/report는 본 SPEC 추가 잠금) | `SPEC-COPILOT-OVERLAP-001/spec.md:114-116` (`feature/SPEC-COPILOT-OVERLAP-001` 브랜치) |
| Cmd OK ≠ 효과 증거 + 날조 대조군 | `SPEC-COPILOT-BUSKWIZ-001/progress.md:275-283, 314` · SONGCUE 선례 |
| Store 안전 (기존 번호 Not allowed·truncation 24) | `SPEC-COPILOT-SONGCUE-001/progress.md:344` · SONGCUE F-3 |
