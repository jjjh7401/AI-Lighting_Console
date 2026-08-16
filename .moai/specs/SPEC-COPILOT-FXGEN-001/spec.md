---
id: SPEC-COPILOT-FXGEN-001
title: "파라메트릭 이펙트 생성 — compose_fx와 열린 축 (Parametric Effect Generation)"
version: "0.2.0"
status: completed
created: 2026-08-15
updated: 2026-08-16
author: manager-spec
priority: P1
phase: "Phase 2 연출 계층 — 시간축 어휘 확장 (FXLIB 후속: 폐쇄 라이브러리 → 파라메트릭 저작)"
module: "server/fx/ (확장), server/orchestrator/tools.py, server/rulebook/assets/v2.4.2/33_effect_editors.md (신규)"
lifecycle: spec-anchored
tags: "fx-generation, compose-fx, phaser, accel-decel, relative, speed-master, width, measure, preset-universal, effect-editors, safety-gate"
tier: L
branch: research/ma3-effects-phaser
related_specs: [SPEC-COPILOT-FXLIB-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-SCENE-001, SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-SONGCUE-001]
---

# SPEC-COPILOT-FXGEN-001 — 파라메트릭 이펙트 생성 (compose_fx와 열린 축)

> **본 SPEC은 FXLIB(SPEC-COPILOT-FXLIB-001, `status: completed`)의 직접 후속이다.** FXLIB v1은 페이저 생성을 **폐쇄 라이브러리 어휘**(6패턴)로 한정하고, `Accel`/`Decel`을 M0 SKIP(효과 미관측)으로 게이트했으며, 저장 형태를 시퀀스+큐로만 고정했다(FXLIB 사용자 확정 ②). 본 SPEC의 출처는 두 가지다: (1) **2026-08-14 오케스트레이션 리서치**(`docs/research/ma3-effects/00~07` — research.md 참조)가 드러낸 갭 G1~G6, (2) **2026-08-15 라이브 검증 세션** — onPC 2.4.2에서 `tools/console_probe.py`로 발화하고 오퍼레이터가 GUI로 효과를 관측한 V1~V7 실측. 이 실측이 FXLIB의 게이트 4곳(Accel/Decel SKIP · ASSUMPTION-40 · 고정 BPM 한정 · 프리셋 저장 Out of Scope)을 **측정으로** 열었다.
>
> **실측 표기 규율 (FXLIB research.md §전문 계승)**: 본 문서의 `[실측 2026-08-15]`는 전부 onPC 2.4.2에서 `tools/console_probe.py`로 커맨드를 발화하고 **오퍼레이터가 GUI/무대 출력을 직접 관측**한 기록이다. 이펙트 **효과**의 기계 증거 채널은 FXLIB M0에서 부정으로 확정된 그대로다(큐/프리셋 내용 `childCount 0`, `Phase`/`Speed` "property not readable") — 유일한 예외는 **프리셋 풀 리스팅 재조회**로, 이는 프리셋 오브젝트의 **생성 여부**를 기계로 판독한다(효과가 아니라 존재의 증거 — V6). 효과 증거는 여전히 사람 관측뿐이다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-08-15 | manager-spec | 최초 작성 (draft, Tier L). 출처: 리서치 코퍼스(`docs/research/ma3-effects/`, 커밋 `2ba4989`) + 2026-08-15 라이브 검증 세션 V1~V7. 열린 축 6종(accel/decel/relative/speed_master/width/measure — `server/fx/schema.py` 확장 실측 반영), `compose_fx` 툴 계약, 프리셋-All 저장 목적지(`/Universal`), 에디터 라우팅 자산(33_effect_editors.md), 레시피 쓰기 경로 DESCOPE 정의. |

## A. 배경 · 실측 요약

FXLIB이 세운 파이프라인(스키마 → 로더 → 매칭 → 번들 빌더 → `run_commands` 단일 관문)은 보존한 채, 본 SPEC은 세 축을 확장한다: **(1) 어휘의 축** — 게이트돼 있던 페이저 레이어 6종을 실측으로 열고, **(2) 저작의 축** — 라이브러리 엔트리 선택(`find_fx`)을 넘어 자연어로 기술된 **임의의** 페이저를 스키마 검증 하에 조립하는 `compose_fx`, **(3) 목적지의 축** — 시퀀스+큐 외에 **프리셋("All" 풀, `/Universal`)** 저장을 허용한다.

### A.1 라이브 검증 세션 V1~V7 — 무엇이 측정됐는가

전 항목 [실측 2026-08-15] — onPC 2.4.2, `tools/console_probe.py` 발화 + 오퍼레이터 GUI 관측. V6의 풀 리스팅 재조회만 기계 증거다.

| # | 측정 대상 | 측정된 사실 | FXLIB 게이트와의 관계 |
|---|---|---|---|
| **V1** | Accel/Decel 곡선 | 2스텝 디머 페이저 위에서 `Step <k> At Accel -100` / `At Decel -100`을 **스텝 열 전체가 끝난 뒤** 발화하면 부드러운 **사인형 페이드**가 무대에서 관측된다. | M0 SKIP의 해소. M0는 `ok:true`+무효과였다 — 빠져 있던 조각은 문법이 아니라 **순서**였다(스텝 2개가 존재하기 전에 곡선 라인을 쏘면 효과 없음). |
| **V2** | `At Relative <n>` 스텝 값 | 스텝 값으로 발화된 `At Relative <n>`은 픽스처의 **현재 위치를 중심으로** 스윕한다. | ASSUMPTION-40 잔여 절반의 해소. 상대 페이저(베이스 룩 위 오프셋 서클)가 저작 가능해진다. |
| **V3** | SpeedMaster 바인딩 | `Attribute '<a>' At SpeedMaster <n>`은 페이저 속도를 **라이브 마스터**에 결속한다 — 마스터 BPM 변경이 페이저에 실시간 반영. **고정 `At Speed`와의 조합은 미측정** — 본 SPEC은 조합을 거부한다(REQ-FXGEN-005). | 갭 G4의 해소(단, 조합 축은 미측정으로 남는다). |
| **V4** | Width / Measure 레이어 | `At Width 25`(스텝을 비트의 25%로 좁힘) + `At Measure 4`(루프를 4비트로 스케일) 조합 확인. | 갭 G6의 해소. |
| **V5** | 3스텝 페이저 | 3스텝 RGB + 채널별 `At Phase 0 Thru 360` → **이동하는 무지개**가 무대에서 관측. | `MIN_STEPS=2`는 하한일 뿐 상한이 아님을 실측 — 3+스텝 저작이 열린다. |
| **V6** | 프리셋 저장 | `Store Preset 21.101 '<label>' /Universal`이 멀티스텝(페이저) 프리셋을 풀 **"All 1"**(2.4.2 기본 쇼파일에서 풀 21)에 저장한다. **풀 리스팅 재조회가 생성을 확인 — 기계 증거.** | FXLIB Out of Scope "프리셋 저장 형태"의 해소. "프리셋이 페이저 동적 값을 담는가"는 V7 리콜 관측과 합쳐 긍정. |
| **V7** | 프리셋 리콜 → 큐 | `Group <g>` + `At Preset 21.101` + `Store Sequence <n> Cue 1` 접수, 큐 생성 확인. **단, 프리셋 내용은 여전히 기계 판독 불가(`childCount 0`)** — 효과 검증은 사람 관측으로 남는다. | 증거 채널 경계의 재확인: 생성(존재)은 기계, 효과는 사람. |

### A.2 미측정으로 남는 것 (정직한 경계)

- **`At Speed`(고정 BPM) + `At SpeedMaster` 동시 지정** — 미측정. 어느 쪽이 이기는지, 무음 충돌인지 알 수 없으므로 **조합 자체를 거부**한다(REQ-FXGEN-005, 사유 코드 `SPEED_SOURCE_CONFLICT`).
- **레시피 쓰기 경로 커맨드라인**(`EditRecipe` / `Assign … At Recipe` / `Cook`) — 공식 키워드 페이지+포럼 수집([문서] 등급, `06-recipe-editor.md` §5의 자체 경고 인용: *"이 저장소에서 검증되지 않았다"*). **리포지토리 실측 0건** → 발화 금지, 미래 프로브 뒤로 게이트(REQ-FXGEN-013).
- **프리셋 내용의 기계 판독** — V7에서 재확인된 **측정된 경계**(부정). 프리셋/큐의 효과 증거는 사람 관측뿐이다.
- **Grid x/y 서브선택, Shape/StepCreator 계열** — 미측정, Out of Scope(§C).

### A.3 신규 표면 4종 (본 SPEC이 정의하는 역량)

1. **열린 축의 스키마 승격** — `server/fx/schema.py`가 `accel`/`decel`(스텝 단위), `relative` 스텝 값, `speed_master`, `width`, `measure`를 실측 어휘로 정의한다(범위 상수 포함 — CURVE −100~100, SPEED_MASTER 1~16, WIDTH 0~100, MEASURE > 0).
2. **`compose_fx` LLM 툴** — 자연어 기술("가운데를 중심으로 도는 느린 서클, 마스터 1에 물려줘")로부터 **라이브러리에 없는 임의의** 페이저를 조립한다. 조립물은 라이브러리 엔트리와 **동일한 `Fx` 스키마 검증**을 통과해야 하며, 실행은 기존 `run_commands` 단일 관문뿐이다.
3. **저장 목적지 선택** — 시퀀스+큐(기존) **또는** "All" 풀 프리셋(`/Universal`). 프리셋 풀 번호와 빈 슬롯은 **리그 재조회로 실측**하며 발명하지 않는다.
4. **에디터 라우팅 자산** — 신규 룰북 자산 `33_effect_editors.md`가 모델에게 세 에디터 패러다임(Phaser Editor / Recipe Editor / MAtricks Editor — 연구 05/06/07)의 소관과 커맨드라인 대응 경계를 안내한다.

## B. 요구사항 (GEARS)

### B.1 열린 축 — 방출 규칙

- **REQ-FXGEN-001** [Ubiquitous] — FX 스키마 **shall** 다음 축을 실측 어휘로 정의한다: 스텝 단위 곡선 `accel`/`decel`(−100~100 — 실측 리터럴은 −100 사인형), 스텝 값 종별 `relative`(절대값의 대안 — V2), `speed_master`(1~16 — 마스터 **번호**이며 BPM이 아니다), `width`(0~100, 비트 대비 %), `measure`(> 0, 비트 수). 각 축의 방출 문법은 실측된 형상만 쓴다: `Step <k> At Accel <n>` / `Step <k> At Decel <n>`, `Attribute '<a>' At Relative <n>`(스텝 값 위치), `Attribute '<a>' At SpeedMaster <n>`, `Attribute '<a>' At Width <n>`, `Attribute '<a>' At Measure <n>`. [실측 2026-08-15 V1~V4]
- **REQ-FXGEN-002** [Event-driven] — **When** 번들이 `accel`/`decel` 값을 담으면, the 빌더 **shall** 해당 `Step <k> At Accel/Decel` 라인을 **스텝 열(값 라인 전체) 뒤에** 배치한다. 순서는 측정된 성립 조건이다: M0는 스텝이 완성되기 전에 곡선 라인을 발화해 `ok:true`+무효과를 얻었고, V1은 2스텝 완성 **후** 발화해 사인 페이드를 관측했다. 스텝 열 앞·중간의 곡선 라인 방출은 금지된다. [실측 2026-08-15 V1]
- **REQ-FXGEN-003** [Event-driven] — **When** 엔트리 또는 compose_fx 조립물이 `relative` 스텝 값을 쓰면, the 시스템 **shall** (a) `At Relative <n>` 형상으로만 방출하고, (b) 리포트에 **"현재 위치 기준"** 의미론을 명시한다 — 상대 페이저의 결과는 발화 시점의 픽스처 위치에 의존하므로(V2 실측 의미론), 동일 번들이라도 무대 결과는 재현 불변이 아니다. 절대/상대 스텝 값을 **한 attribute 안에서 혼합**하는 것은 미측정이므로 거부한다. [실측 2026-08-15 V2 / 혼합은 미측정]
- **REQ-FXGEN-004** [Event-driven] — **When** `speed_master`가 지정되면, the 빌더 **shall** attribute별 `At SpeedMaster <n>` 라인을 방출하고, 리포트에 "속도는 SpeedMaster <n>에 결속 — 마스터 BPM 변경이 실시간 반영된다"를 명시한다. 마스터 번호 범위는 1~16이다(16개 마스터, 각 0~225 BPM — [문서] help.malighting.com Speed Masters; 결속 동작 자체는 [실측 2026-08-15 V3]). [실측 + 문서]
- **REQ-FXGEN-005** [Unwanted] — the 시스템 **shall not** 하나의 fx에서 고정 `speed`(BPM)와 `speed_master`를 **동시에** 받지 않는다 — 조합은 미측정이며(어느 쪽이 우선하는지, 충돌이 무음인지 알 수 없음), 스키마/빌더는 사유 코드 `SPEED_SOURCE_CONFLICT`로 명시 거부한다. 효과가 기계로 확인되지 않는 어휘에서(FXLIB REQ-FXLIB-014 (c)) 미측정 조합은 무음 실패 축이므로 형태 자체를 차단한다. [미측정 — 거부가 규율]
- **REQ-FXGEN-006** [Ubiquitous] — 스텝 축 **shall** 3개 이상의 스텝을 허용한다(`MIN_STEPS=2`는 하한 유지). 3스텝 RGB + 채널별 위상 확산의 무대 효과(이동 무지개)가 실측 앵커다. 스텝 수 상한은 실측 근거가 없으므로 발명하지 않는다. [실측 2026-08-15 V5]

### B.2 compose_fx — 파라메트릭 저작 툴

- **REQ-FXGEN-007** [Event-driven] — **When** 모델이 `compose_fx`를 호출하면, the 툴 **shall** 자연어 파라미터로부터 **라이브러리에 존재하지 않는 임의의** 페이저를 조립한다. 조립물은 라이브러리 엔트리와 **완전히 동일한 `Fx` 스키마 검증**을 통과해야 한다: 폐쇄 attribute 집합(`KNOWN_ATTRIBUTES`), `MIN_STEPS` 이상의 스텝, 축별 수치 범위(PHASE/PERCENT/SWING/CURVE/SPEED_MASTER/WIDTH/MEASURE), 동일 attribute 동일 값 스텝 거부(dedupe 접힘 방지 — FXLIB REQ-FXLIB-005 ③), `steps` 없는 변형 축 단독 선언 거부. **검증 실패는 조립 거부다** — 스키마를 우회하는 "자유 조립" 경로는 존재하지 않는다.
- **REQ-FXGEN-008** [Ubiquitous] — `compose_fx` **shall** 실측 확정 어휘만으로 커맨드를 구성한다: FXLIB REQ-FXLIB-003 구간 1(스텝 생성·페이저 변형·MAtricks 5축·Store) + 본 SPEC이 여는 축(REQ-FXGEN-001). 리터럴 발명은 금지된다 — 자연어가 미측정 문법(예: Grid 서브선택, 레시피 쓰기, Speed+SpeedMaster 조합)을 요구하면 **거부와 사유 보고**가 정답이지 근사 조립이 아니다. 금지 형태 `Attribute '<a>' At Step <k>`(FXLIB REQ-FXLIB-022)도 전량 차단을 계승한다.
- **REQ-FXGEN-009** [Ubiquitous] — 단일 초크포인트 계승: `compose_fx` **shall** 커맨드를 문자열로만 구성하고 기존 `run_commands` → `gate.screen()` 경로 **하나로만** 실행한다 — `instantiate_fx`와 동일하게 로컬 `run_commands` 클로저를 재진입하며(제2 실행 표면 금지), `server/fx/`의 transport import 금지는 `server/tests/test_architecture.py` 전역 스캔에 그대로 포섭된다. instruction-scoped dedupe 경계도 계승한다: **한 지시 턴에 fx 인스턴스화(라이브러리든 조립이든)는 1회만 온전히 성립**하고, 2회차는 공유 문자열(`Step 2` 등)부터 접히므로 교차 호출 충돌 검출(FXLIB REQ-FXLIB-011 (b))이 명시 실패로 보고한다.
- **REQ-FXGEN-010** [Event-driven] — **When** `compose_fx` 실행이 완료되면, the 툴 **shall** FXLIB 리포트 규율(REQ-FXLIB-014)을 전량 계승한 한국어 2단 리포트를 반환하고, **조립 파라미터 전문**(스텝 값·축 값·목적지)을 상세단에 싣는다 — 라이브러리 id가 없는 조립물은 리포트가 유일한 재현 기록이기 때문이다. 효과의 기계 검증 불가 문면은 무조건 명시한다.

### B.3 저장 목적지 — 시퀀스+큐 또는 프리셋("All" 풀)

- **REQ-FXGEN-011** [Event-driven] — **When** 저장 목적지로 프리셋이 선택되면, the 빌더 **shall** `Store Preset <pool>.<slot> '<label>' /Universal` 리터럴로 저장한다. `/Universal`은 실측된 문법 그대로다 — Feature Group과 무관하게 페이저(멀티스텝) 데이터를 받는 풀은 **"All" 풀**이며, 2.4.2 기본 쇼파일에서 "All 1"은 풀 21이다. [실측 2026-08-15 V6 — `Store Preset 21.101 '<label>' /Universal` 저장 + 풀 리스팅 재조회로 생성 확인]
- **REQ-FXGEN-012** [Ubiquitous] — 프리셋 풀 번호와 슬롯 번호 **shall** 리그 재조회로 실측한 값만 쓴다 — **"풀 21"을 하드코딩하거나 빈 슬롯을 추측하는 것은 금지된다**(쇼파일마다 풀 배치가 다를 수 있고, FXLIB REQ-FXLIB-012 (c)의 시퀀스 번호 규율과 동형). 재조회가 불가하면 `PRESET_POOL_UNAVAILABLE`, 리스팅이 절단되면 `PRESET_POOL_TRUNCATED`, 번호 없는 자식이 있으면 `PRESET_NUMBER_UNAVAILABLE`, 지정 슬롯이 점유돼 있으면 `PRESET_OCCUPIED`로 각각 명시 거부한다 — "빈 슬롯"은 도착한 번호들의 속성이 아니라 풀 전체의 속성이므로 절단 하에서는 판정 불가다.
- **REQ-FXGEN-013** [Event-driven] — **When** 프리셋 저장이 실행되면, the 시스템 **shall** 증거를 2계로 분리해 보고한다: **(기계 증거)** 풀 리스팅 재조회가 해당 슬롯의 프리셋 오브젝트 생성을 확인한다 — 이것은 실측으로 성립이 확인된 채널이다(V6). **(효과 증거)** 프리셋 **내용**은 기계 판독 불가다 — `childCount 0`에서 트리가 바닥나고(V7 재확인) 페이저를 담은 프리셋과 빈 프리셋이 구별되지 않으므로, 효과 확인은 **사람의 GUI 관측**임을 리포트에 무조건 명시한다. `Cmd` 접수 `ok`를 효과 증거로 쓰는 것은 금지된다(FXLIB REQ-FXLIB-014 (c) 계승).
- **REQ-FXGEN-014** [Event-driven] — **When** 저장된 프리셋을 큐에 싣는 지시가 오면, the 시스템 **shall** 실측 형상만 쓴다: `Group <g>` 선택 → `At Preset <pool>.<slot>` 리콜 → `Store Sequence <n> Cue 1 '<label>'`. 큐 생성은 접수·확인됐다. 단, 큐에 실리는 것은 값이 아니라 프리셋 **참조**이므로([문서] — 05 §8.6, Recast 의미론) 프리셋 변경이 큐에 파급됨을 리포트 문면에 싣는다. [실측 2026-08-15 V7 — 접수·큐 생성 확인 / 참조 의미론은 문서 등급]
- **REQ-FXGEN-015** [Unwanted] — the 시스템 **shall not** 하나의 인스턴스화에서 시퀀스+큐와 프리셋 **두 목적지를 동시에** 저장하지 않는다 — 목적지는 배타 선택이다. 한 지시 턴 안의 "프리셋 저장 후 그 프리셋으로 큐 저장" 연쇄는 dedupe 경계(REQ-FXGEN-009)와 무관하게 성립하는지 미측정이므로, v1은 **지시 턴당 저장 1건**으로 유지하고 연쇄는 오퍼레이터의 후속 지시로 나눈다.

### B.4 에디터 라우팅 자산

- **REQ-FXGEN-016** [Ubiquitous] — 신규 룰북 자산 `server/rulebook/assets/v2.4.2/33_effect_editors.md` **shall** 세 에디터 패러다임의 소관 경계를 모델에게 안내한다: **Phaser Editor**(구운 값 저작 — 커맨드라인 대응 = 본 저장소의 검증 경로, 연구 05), **Recipe Editor**(참조 기반 지시문 — 커맨드라인 쓰기 경로는 리포지토리 미검증, 읽기 전용 안내만, 연구 06), **MAtricks Editor**(선택 분할 — v1 어휘는 `Set Selection`/`Reset` 5축뿐, Grid는 범위 밖, 연구 07). 자산은 각 패러다임에 대해 "무엇을 하라"가 아니라 **"어느 경로가 검증돼 있고 어느 경로가 금지인가"**를 적는다 — 미검증 문법이 검증 표기 없이 자산에 등장하는 것은 금지된다(FXLIB REQ-FXLIB-003 규율의 자산 판).
- **REQ-FXGEN-017** [Ubiquitous] — 룰북 변경 범위 **shall** 정밀하다: (a) `33_effect_editors.md` **신설**과 (b) `31_choreography_patterns.md`에 2026-08-15 실측 기록(V1~V7 "OBSERVED EFFECT" 항 — 코드 주석이 이미 인용하는 앵커) **추가**만 허용된다. FXLIB REQ-FXLIB-020의 PRESERVE(byte-diff 0)는 **FXLIB 자신의 범위 제약**이었고, 본 SPEC은 새 실측이 코드가 인용하는 위치에 실려야 한다는 이유로 그 두 파일에 한해 명시적으로 완화한다 — 기존 검증 리터럴의 **수정·삭제는 여전히 금지**이며 추가만 한다. 그 외 자산(30/32 등)과 고정 프리픽스는 무변경이다.

### B.5 레시피 쓰기 경로 — DESCOPE 게이트

- **REQ-FXGEN-018** [Unwanted] — the 시스템 **shall not** 레시피 쓰기 경로 커맨드(`EditRecipe …` / `Assign Group … Preset … At Recipe …` 류 / `Cook …` / `Store … /Remove` 레시피 문맥)를 어떤 표면(라이브러리 자산·compose_fx 조립·번들 빌더·룰북 자산의 발화 지시)에서도 방출하지 않는다. 근거: 해당 문법은 공식 키워드 페이지+포럼 수집의 [문서] 등급이며 **이 저장소의 라이브 실측이 0건**이다(연구 06 §5가 스스로 경고를 명기). 효과가 기계로 확인되지 않는 환경에서 미검증 쓰기 문법은 무음 실패 또는 파괴적 부작용(`Cook /Overwrite`, `Store preset … Step 2`의 스텝 삭제 보고 — 연구 04 §1.2 포럼 사례) 축이다.
- **REQ-FXGEN-019** [State-driven] — **While** 레시피 쓰기 경로의 라이브 프로브가 수행되지 않은 동안, the 스키마·빌더 **shall** 레시피 축을 **정의조차 하지 않는다** — FXLIB의 accel/decel DESCOPE("필드 정의 유지 + v1 미사용")보다 한 단계 강한 형상이며, 이유는 등급 차이다: accel/decel은 `ok:true`까지는 실측된 어휘였지만 레시피 쓰기 문법은 **접수 여부조차 미측정**이다. 미래 프로브가 열면 그때 스키마 확장이 별도 SPEC/개정으로 온다.

## C. 환경 및 전제

- **대상 환경**: grandMA3 onPC 2.4.2, OSC `127.0.0.1` UDP, 2.4.2 기본 쇼파일(프리셋 풀 배치의 실측 기준 — 단 REQ-FXGEN-012에 따라 풀 번호는 항상 재실측한다).
- **기능 전제**: FXLIB 전량(`server/fx/` 스키마·로더·매칭·빌더·리포트, `find_fx`/`instantiate_fx` 툴, `status: completed`), 단일 관문 `run_commands` → `gate.screen()`, `get_rig_context` 재조회, instruction-scoped dedupe(개정 불가 — 기각 선례). 안전 게이트 의미론 무변경: `SpeedMaster`/`Width`/`Measure`/`Relative`/`Accel`/`Decel`/`At Preset`/무플래그 `Store`는 닫힌 블랙리스트 하에서 보류 없이 통과한다 — `server/safety/**` 수정 0건.
- **실측 기록의 소재**: V1~V7의 정본은 `31_choreography_patterns.md`의 2026-08-15 추가 항(REQ-FXGEN-017 (b))이다. 본 spec.md의 §A.1 표는 그 요약이며, 서술이 어긋나면 룰북 기록이 이긴다.
- **브랜치**: `research/ma3-effects-phaser` (리서치 코퍼스 커밋 `2ba4989` 포함).

## D. 제외 범위 (Out of Scope)

### Out of Scope — 레시피 / StepCreator / Shape 쓰기 경로

- `EditRecipe`/`Assign … At Recipe`/`Cook` 류 레시피 쓰기, StepCreator 대량 스텝 생성, Shape(형상 라이브러리) 적용 일체. 전부 리포지토리 라이브 실측 0건([문서]/포럼 등급)이며, 레시피는 REQ-FXGEN-018/019의 DESCOPE 게이트가 정본이다. 미래 라이브 프로브가 각 축의 접수+효과를 실측하기 전까지 발화 금지.

### Out of Scope — attribute별 독립 속도

- 한 fx 안에서 attribute마다 서로 다른 `Speed`/`SpeedMaster`를 배정하는 축(예: Pan은 마스터 1, Dimmer는 고정 120 BPM). SpeedMaster 키워드가 문법상 attribute 단위임은 [문서]로 확인되지만, 혼합 배정의 무대 효과는 미측정이고 Speed/SpeedMaster 배타 규칙(REQ-FXGEN-005)의 검사 경계가 attribute 단위로 쪼개지면 무음 충돌 표면이 넓어진다. v1은 fx 전역 단일 속도원만 허용한다.

### Out of Scope — MAtricks Grid x/y 서브선택

- `Grid` 기반 셀 선택 일체(연구 07, 갭 G5). v1 MAtricks 어휘는 FXLIB 그대로 `Set Selection` 5축 + `Reset`뿐이다. Grid 문법은 리포지토리 실측 0건.

### Out of Scope — FXLIB 계승 제외 항목의 유지

- 익스큐터 자동 배치, 지시 턴당 2회 이상 인스턴스화(dedupe 경계 — 본 SPEC의 목적지 배타 규칙 REQ-FXGEN-015 포함), 스트로브·셔터 danger 축, 정적 포지션 값(`At Absolute`), 큐 트리거 자동화, 생성형 Lua 경로, UI 표면 변경, 콘솔측 Lua 변경, 비게이트 실행 경로 — 전부 FXLIB §D의 판정을 무변경 계승한다. 단 "프리셋 저장 형태"는 본 SPEC이 V6/V7 실측으로 **해소**했으므로 계승 목록에서 빠진다.

## E. 검증 기준

기존 `server/tests/test_fx_*.py` 6종을 확장한다 — 신규 테스트 파일 신설보다 기존 파일의 관할 확장을 우선한다(테스트는 관측 가능한 계약만 방어하고, 검증 카운트 수치는 착수 직전 실측한다 — baseline-integrity 관례).

| 파일 | 확장 관할 |
|---|---|
| `test_fx_schema.py` | 열린 축 6종의 범위 상수와 거부 경계(CURVE −100~100, SPEED_MASTER 1~16, WIDTH 0~100, MEASURE > 0), relative/절대 혼합 거부, 3+스텝 수용(REQ-FXGEN-001/003/006) |
| `test_fx_library.py` | 라이브러리 엔트리가 실측 축만 값으로 쓰는지(레시피 축 부재 — REQ-FXGEN-019), 신규 레퍼토리 엔트리의 스키마 적합성 |
| `test_fx_instantiate.py` | 곡선 라인의 스텝 열 후행 배치(REQ-FXGEN-002), SpeedMaster 라인 방출(V3 형상), Speed+SpeedMaster 동시 지정의 `SPEED_SOURCE_CONFLICT` 거부(REQ-FXGEN-005 — 기존 `test_a_fixed_bpm_and_a_master_binding_together_are_refused` 계열), Width/Measure 방출(V4 형상), 프리셋 목적지 번들 골든(`Store Preset <pool>.<slot> '<label>' /Universal` — REQ-FXGEN-011), 풀 실측 거부 4종(`PRESET_POOL_UNAVAILABLE`/`PRESET_POOL_TRUNCATED`/`PRESET_NUMBER_UNAVAILABLE`/`PRESET_OCCUPIED` — REQ-FXGEN-012), 목적지 배타(REQ-FXGEN-015) |
| `test_fx_boundary.py` | 금지 형태 전수 차단 계승(`At Step <k>`), 레시피 커맨드 미방출(REQ-FXGEN-018) |
| `test_fx_matching.py` | 신규 패턴 동의어(서클·발리후·무지개·브리딩 등 한국어 1급) 매칭 결정론 |
| `test_fx_tool.py` | `compose_fx` 계약: 스키마 검증 실패 = 조립 거부(REQ-FXGEN-007), 미측정 문법 요구 시 거부+사유(REQ-FXGEN-008), `run_commands` 재진입 단일 경로(REQ-FXGEN-009), 리포트에 조립 파라미터 전문 포함(REQ-FXGEN-010), 증거 2계 문면(REQ-FXGEN-013) |

- **아키텍처 불변식**: `server/tests/test_architecture.py` 전역 스캔이 `server/fx/` 확장분을 자동 포섭한다 — 예외 추가 금지(FXLIB REQ-FXLIB-017 계승).
- **효과의 최종 인수**: 기계 테스트는 번들 형상과 거부 경계까지만 방어한다. 무대 효과의 인수는 라이브 세션의 **사람 GUI 관측**이며(측정된 경계 — §A.2), 리포트 문면이 그 한계를 무조건 싣는지가 기계 테스트의 관할이다.

## F. 참조

- **연구 근거 정본**: `.moai/specs/SPEC-COPILOT-FXGEN-001/research.md` — `docs/research/ma3-effects/00~07` 코퍼스 색인과 등급.
- **실측 기록**: `31_choreography_patterns.md` 2026-08-15 추가 항(REQ-FXGEN-017 (b)) · `tools/console_probe.py`(발화 도구).
- **계승 정본**: `SPEC-COPILOT-FXLIB-001/spec.md` — 스키마·매칭·번들·dedupe·리포트·안전 규율의 원 판정 전량.
