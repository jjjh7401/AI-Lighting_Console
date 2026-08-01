---
id: SPEC-COPILOT-SCENE-001
title: "씬 컴파일러 — 룩 + 이펙트 + 타이밍을 하나의 큐로 (Scene Compiler)"
version: "0.1.0"
status: draft
created: 2026-08-01
updated: 2026-08-01
author: manager-spec
priority: P1
phase: "Phase 2 연출 계층 — 씬 합성 (의도→메모리 파이프라인 2단계)"
module: "server/scene/ (신규), server/orchestrator/tools.py"
lifecycle: spec-anchored
tags: "scene-compiler, look-fx-merge, cue-only, tracking, sequence-cue, trigger, nl-matching, safety-gate, value-line-guard"
tier: L
related_specs: [SPEC-COPILOT-FXLIB-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-SONGCUE-001, SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-OVERLAP-001, SPEC-COPILOT-PRECHK-001]
---

# SPEC-COPILOT-SCENE-001 — 씬 컴파일러

> **이 SPEC의 자리는 선행 SPEC이 명시적으로 비워 두었다.** FXLIB이 세 곳에서 이 좌석을 예약했다: `SPEC-COPILOT-FXLIB-001/spec.md:42`("프리셋 저장은 명시적 비목표다 … **그 축은 씬 컴파일러 후속 SPEC의 몫이다**"), `:140`(§D 제외 범위 — "**이 축은 씬 컴파일러 후속 SPEC의 몫이다**"), `:70`(REQ-FXLIB-001 — "**후속 소비자(씬 컴파일러·큐리스트 이펙트 축)가 소비 가능한 형상이어야 한다**"). 본 SPEC은 그 예약을 이행한다. 출처 서술과 인용 전문은 plan.md §A가 소유한다.
>
> **파이프라인의 위치**: LOOKLIB(정지 화면 어휘) · FXLIB(시간축 어휘)이 **1단계 — 의도**를 세웠다. 본 SPEC은 **2단계 — 메모리**다: 두 어휘를 하나의 큐로 합성해 콘솔의 기억(시퀀스·큐)에 새긴다. 두 계층과 같은 2단 형상(**match(순수·라이브러리 한정) → instantiate/compile(리그 바인딩·문자열 전용)**)을 미러한다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-08-01 | manager-spec | 최초 작성 (draft, Tier L). 출처: FXLIB이 예약한 후속 좌석(spec.md:42, :70, :140) + 사용자 결정 4건(2026-08-01, 증거 리포트 후 확정 — 재질의 금지): **D1** 트래킹 정책 = 전 큐 `/CueOnly`, **D2** 결합 순서 = 룩 먼저·충돌은 이펙트 우선, **D3** `/Merge` 미사용·신규 큐 번호 전용, **D4** Tier L. 조사: 코디네이터 직접 판독(`/CueOnly` 전수 grep · fx/looks 소스 · dedupe 경계 · 게이트 어휘 · 선행 SPEC 실측 기록). REQ **20건** · AC **22건** · ASSUMPTION **41~45(5건)** · clarification 마커 **0건** · 라이브 세션 **2회(M0·M8)**. 아티팩트 6종 동시 생성. |

## A. 개요

**씬(Scene)** 은 하나의 큐다. 그 큐 안에는 세 가지가 함께 들어간다:

1. **룩** — 정적 attribute 값(색·딤머·포지션). 출처는 `server/looks/` 라이브러리.
2. **이펙트** — 시간축 페이저(스텝 열 + 위상 + 속도 + MAtricks 분할). 출처는 `server/fx/` 라이브러리.
3. **타이밍** — 시퀀스 번호·큐 번호·트리거(`TrigType` / `TrigTime`)·라벨.

지금 이 세 가지는 **서로 다른 툴이 서로 다른 큐를 만든다**. `instantiate_look`은 프리셋을 만들고, `instantiate_fx`는 `Cue 1` 고정의 시퀀스를 만들고, `prepare_songcue`는 큐리스트를 만든다. 사용자가 "파란 백라이트가 천천히 웨이브하는 씬"을 원하면 지금은 그 씬이 **하나의 큐로 존재할 수 없다**. 본 SPEC은 그 합성을 하는 단일 툴(`compile_scene`)을 세운다.

아키텍처 전제: **LOOKLIB·FXLIB 파이프라인의 세 번째 미러**. 씬 데이터는 신규 패키지 `server/scene/`의 자기 소유 스키마이고, 커맨드는 문자열로만 구성되며, 실행은 기존 `run_commands` → `gate.screen()` 단일 관문만 쓴다. `server/looks/**` · `server/fx/**` · `console/lua/**` · `server/rulebook/assets/**` · `server/safety/**`는 전부 **PRESERVE**이며 **읽기 import만** 한다(plan.md §A.5).

### 사전 확정 사실 (사용자 확정 D1~D4 — 재질의 금지, 전부 2026-08-01 확정)

#### D1 — 트래킹 정책: 전 큐 `/CueOnly`

씬 컴파일러가 내는 **모든 Store는 `/CueOnly`를 단다.** 씬의 값이 다음 큐로 트래킹되지 않게 하기 위함이다. 룰북 근거: `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:59` — *"`/CueOnly` stops the change tracking into the next cue"*, 그리고 `:130-134`의 트래킹 모델 서술(*"MA3 is a TRACKING console … `ClearAll` between looks does NOT stop this"*).

**정직 제약 (이 SPEC에서 가장 중요한 한 줄)**: **`/CueOnly`는 이 리포지토리에서 한 번도 발화된 적이 없다.** 전수 grep 실측(2026-08-01, 코디네이터 직접) — `CueOnly` / `Block Sequence` / `Unblock` 세 토큰이 `server/` · `ui/src/` · `console/` 어디에도 **코드로는 0건**이고, 유일한 출현이 룰북 산문 2곳(`:59`, `:132-133`)이다. 따라서:

- **접수(acceptance)와 효과(effect)를 분리해 다룬다.** M0 라이브 프로브가 판정하는 것은 **접수**뿐이다: `/CueOnly` 플래그를 단 Store가 `ok:true`를 받고, **재조회로 그 큐가 기대한 이름·`cueNo`로 실존하는지** 확인된다(ASSUMPTION-41).
- **트래킹이 실제로 차단되는지는 기계로 검증할 수 없다.** 큐의 내용을 돌려주는 경로가 존재하지 않기 때문이다(§C 검증 천장). 그 축은 **사람의 GUI 관측이 유일한 채널**이며, 리포트는 두 주장을 **뭉뚱그리지 않는다**(REQ-SCENE-014).
- **상속된 부채의 표면화**: 이 저장소의 유일한 다중 큐 작성자인 SONGCUE는 **플래그 없이** Store한다(`server/looks/songcue.py:462-466` — `Store Sequence {n} Cue {c} '{name}'`). 즉 SONGCUE가 만든 큐들의 값은 **오늘 앞으로 트래킹되고 있으며**, 그 사실은 문서화·단언·측정 어디에도 없다. 씬 컴파일러가 정책을 바꾸면 그 잠재 부채가 표면화된다 — 본 SPEC은 그것을 **기록하되 고치지 않는다**(SONGCUE는 PRESERVE, research.md §5).

#### D2 — 결합 순서: 룩 먼저, 충돌은 이펙트 우선

하나의 씬 번들 안에서 커맨드 조립 순서는 아래 골격을 따른다. **정본은 design.md §3이며, 병렬 브리프는 그 절을 문면 그대로 인용한다.**

```
ChangeDestination Root
ClearAll
Group <n>
<룩 값 라인 — 하나의 ';' 체인 라인>
<fx step1 값 라인들>
Step 2
<fx step2 값 라인들>
[Step 3 …]
<위상 라인들>
<속도 라인>
[Set Selection MAtricks …]
Store Sequence <s> Cue <c> '<이름>' /CueOnly
[Reset Selection MAtricks]
ClearAll
```

**왜 룩이 먼저인가 — 이건 취향이 아니라 강제다.** 페이저는 2개 이상의 스텝을 요구하고(`server/fx/schema.py:66` `MIN_STEPS = 2`), 빌더는 `Step 1` 라인을 **발화하지 않는다**(`server/fx/instantiate.py:326-342` — *"`Step 1` is never emitted — the first step is the current one"*). 즉 **첫 스텝은 "현재 프로그래머 상태"이며 이펙트가 그 위에서 변형을 시작한다.** 룩은 그 현재 상태를 채우는 값이므로 스텝 1에 **자연히** 착지해야 하고, 그러려면 첫 `Step 2` 라인보다 앞에 있어야 한다. 룩을 이펙트 뒤에 놓으면 룩 값이 마지막 스텝에 얹혀 페이저의 종점이 되어 버린다.

**충돌 시 이펙트가 이긴다.** 같은 attribute를 룩과 이펙트가 모두 지정하면, 나중 라인이 프로그래머 값을 덮으므로 **이펙트가 승자**다. 이는 자연 귀결이지만 **조용해서는 안 된다** — 컴파일러는 덮인 attribute를 **전수 열거**해 리포트에 싣는다. 조용한 덮어쓰기는 결함이다(REQ-SCENE-005, AC-SCENE-005).

#### D3 — `/Merge` 미사용, 신규 큐 번호 전용

씬 컴파일러는 `/Merge`를 **0건** 발화하고, **비어 있는 큐 번호에만** 쓴다.

라이브 실측 근거 (`SPEC-COPILOT-SONGCUE-001/progress.md:337-344` — 실측 표 전재):

| 시퀀스 | 발화 | 재조회 childCount | 사용자 큐 | 앞 큐 |
|---|---|---|---|---|
| 101 | `Store … Cue 2 'PROBEA2' CueFade 2 /Merge` | **4** | **2** | **보존** |
| 102 | `Store … Cue 2 'PROBEB2' CueFade 2` (**`/Merge` 없음**) | **4** | **2** | **보존** |
| 102 | `Store … Cue 1 'PROBEB3' CueFade 2` (**기존 큐**, `/Merge` 없음) | 4 (불변) | 2 | **거부 — `Not allowed`** |

읽는 법: **새 큐 번호에는 `/Merge`가 있으나 없으나 결과가 같고**(둘 다 가산·보존), **기존 큐 번호에는 플래그 없는 Store가 거부되며 쇼파일이 불변**이다. 그 거부가 `server/fx/instantiate.py:225`가 *"the LAST line of defence"* 라고 부르는 안전망이다. `/Merge`를 달면 그 안전망이 **꺼진다** — 실익 0(새 번호에서 동작 동일)에 안전망만 잃는 거래이므로 채택하지 않는다.

`/Overwrite`는 **절대 금지**다. 4곳에서 블랙리스트로 봉쇄돼 있다: 룰북 `:57-58`(DESTRUCTIVE 표시), `server/safety/blacklist.yaml:18`(`"Store /overwrite"`), `DESIGN.md:133`, `server/web/preview.py:113`(`store_overwrite` 액션 라벨). 부재 단언은 **대소문자 무관**으로 쓴다 — 런타임 매칭이 이미 대소문자 무관이라 대소문자 고정 assert는 빌더가 `/overwrite`를 내도 **조용히 통과**하는 위양성 테스트가 된다(`SPEC-COPILOT-BUSKWIZ-001/design.md:209`).

#### D4 — Tier L

아티팩트 5종(spec/plan/acceptance/design/research) + progress + 자동 생성 spec-compact. plan-auditor 문턱 **0.85**.

### 씬의 폐쇄 어휘 — 무엇을 합성할 수 있는가

씬은 **새 어휘를 만들지 않는다.** 룩 어휘는 LOOKLIB이, 이펙트 어휘는 FXLIB이 소유하고, 씬 컴파일러는 **두 라이브러리에 실존하는 엔트리만** 조합한다(REQ-SCENE-002). 씬이 자기 것으로 갖는 축은 **결합 규칙 + 타이밍**뿐이다:

| 씬의 축 | 내용 | 근거 |
|---|---|---|
| `look_id` | LOOKLIB 라이브러리 실존 id (선택 — 이펙트 단독 씬 허용) | `server/looks/loader.py` |
| `fx_id` | FXLIB 라이브러리 실존 id (선택 — 룩 단독 씬 허용) | `server/fx/loader.py` |
| 대상 그룹 | rig context 등재 번호 (발명 금지) | `31_choreography_patterns.md:210-211` |
| 시퀀스 번호 | 재조회 실측 또는 사용자 지정 | `server/fx/instantiate.py:218` |
| **큐 번호** | **임의 신규 번호** (fx의 `Cue 1` 상수 고정을 넘는 축) | D3 |
| 트리거 | `TrigType` / `TrigTime` (선택) | `31_choreography_patterns.md:106-117` |
| 라벨 | ASCII, Store 리터럴에 인라인 | `server/looks/songcue.py:462` |

**`look_id`와 `fx_id`가 둘 다 비면 씬이 아니다** — 로더·툴이 거부한다(REQ-SCENE-003).

## B. 요구사항 (GEARS)

### B.1 씬 데이터 계층 (스키마 + 결합 규칙)

- **REQ-SCENE-001** [Ubiquitous] — 씬 스키마 **shall** 다음 축을 정의한다: 아이덴티티(안정적 scene id, 표시 이름, 한국어 별칭/무드 키워드), 참조 축(`look_id` / `fx_id` — 각각 선택이되 **최소 1개 필수**), 타이밍 축(`cue_number` / `sequence_number` / `trig_type` / `trig_time` — 전부 선택), 라벨 축, 명시적 `schema_version`. 씬 스키마는 **룩·이펙트의 값 축을 복제하지 않는다** — 참조만 담는다.
- **REQ-SCENE-002** [Ubiquitous] — 씬 컴파일러 **shall** `look_id` / `fx_id`를 각각 LOOKLIB · FXLIB 라이브러리의 **실존 엔트리로만** 해석하고, 미등재 id를 명시 에러로 거부한다 — 엔트리 발명·합성·인라인 정의는 금지된다(LOOKLIB REQ-LOOKLIB-007 · FXLIB REQ-FXLIB-007 계승).
- **REQ-SCENE-003** [Unwanted] — the 로더·툴 **shall not** `look_id`와 `fx_id`가 **모두 부재**한 씬을 성립시킨다 — 합성할 것이 없는 씬은 씬이 아니며, 명시 에러로 거부된다.
- **REQ-SCENE-004** [Unwanted] — 씬 데이터 **shall not** per-show 값(구체 그룹 번호·이름, FID, 익스큐터 번호)을 정적 자산에 포함한다 — 리그 바인딩은 오직 컴파일 시점에 일어난다(LOOKLIB REQ-LOOKLIB-004 · FXLIB REQ-FXLIB-004 계승). 타이밍 축(시퀀스·큐 번호)은 **호출 인자**이지 정적 자산 필드가 아니다.
- **REQ-SCENE-005** [Event-driven] — **When** 룩과 이펙트가 같은 attribute를 지정하면, the 컴파일러 **shall** 이펙트 값을 승자로 삼고(D2 — 나중 라인이 이긴다), **덮인 attribute 전량을 열거해** 컴파일 결과에 싣는다. 조용한 덮어쓰기는 금지된다 — 열거가 비어 있는데 실제로 충돌이 있었다면 그것은 결함이다.
- **REQ-SCENE-006** [Event-driven] — **When** 씬 라이브러리가 로드되면, the 로더 **shall** 스키마를 검증하고 위반을 명시적 에러로 보고한다 — 부분적으로 깨진 라이브러리를 조용히 서빙하지 않는다. 검증 대상: 미지 필드, 중복 scene id, `look_id`/`fx_id` 동시 부재(REQ-SCENE-003), 수치 범위 이탈(`cue_number` > 0, `trig_time` ≥ 0), 미지 `trig_type`(폐쇄 집합 밖).

### B.2 자연어 매칭

- **REQ-SCENE-007** [Event-driven] — **When** 채팅 지시가 룩 축과 이펙트 축을 **함께** 담으면(예: "파란 백라이트가 천천히 웨이브하는 씬"), the 매칭기 **shall** 두 축을 분리해 각각 `find_looks` · `find_fx`의 매칭 규율로 해석하고, 씬 후보를 조합해 반환한다. 매칭 규율은 두 선행 계층의 미러다: **한국어 조사 처리**, **폴백 3종**(무매칭/저신뢰/모호), **동점은 None**(임의 선택 금지), **결정론적 정렬**(같은 입력 → 같은 출력).
- **REQ-SCENE-008** [Event-driven] — **When** 두 축 중 **한쪽만** 신뢰 매칭되면, the 매칭기 **shall** 그 사실을 **부분 매칭 신호로 구분해** 반환한다 — 매칭된 축만으로 씬을 세우는 것은 허용되지만(룩 단독·이펙트 단독 씬은 적법), **매칭되지 않은 축을 임의 기본값으로 채우는 것은 금지**된다.
- **REQ-SCENE-009** [Event-driven] — **When** 어느 축도 신뢰 매칭되지 않으면, the 시스템 **shall** 명시적 폴백 신호를 반환하고 기존 룰북 무드 폴백으로 강등한다 — 폴백 경로 자체는 무변경으로 보존된다.

### B.3 MA3 컴파일 (게이트 경유, 단일 큐)

- **REQ-SCENE-010** [Event-driven] — **When** 사용자가 하나의 씬에 대한 컴파일을 지시하면, the 컴파일러 **shall** D2 결합 순서(design.md §3 정본)로 커맨드 번들을 구성한다: 선두 `ChangeDestination Root` 정확 1회 → `ClearAll` → 그룹 선택(bare `Group <n>` **번호형 단일**, `Select` 접두 금지) → **룩 값 라인**(하나의 `;` 체인) → **fx 스텝 열**(스텝 1 값 → `Step 2` → 스텝 2 값 → …) → 위상 라인들 → 속도 라인 → (선언 시) MAtricks 라인들 → `Store Sequence <s> Cue <c> '<라벨>' /CueOnly` → (MAtricks 사용 시) `Reset Selection MAtricks` → `ClearAll`. **산출물은 시퀀스 1개 + 큐 1개다.**
- **REQ-SCENE-011** [Ubiquitous] — 컴파일 번들 **shall** 검증된 프로그래밍 규율을 따른다: 목적지 1회, 캡처 전·Store 후 `ClearAll`, MAtricks를 쓴 번들은 Store 후 `Reset Selection MAtricks`, 라벨은 Store 리터럴에 인라인. **스텝 규율(FXLIB M0 실측 계승)**: `Step 1` 라인은 발화하지 않고, 둘째 스텝부터 **단독 `Step <k>` 라인**을 그 스텝의 값 라인 **앞에** 놓으며, 스텝 값 라인은 `;` 체이닝하지 않는다. **금지 형태 `Attribute '<attr>' At Step <k>` 0건**(FXLIB REQ-FXLIB-022 계승 — `ok:true`이나 효과 없음).
- **REQ-SCENE-012** [Ubiquitous] — **모든 Store 라인 shall `/CueOnly` 플래그를 담는다**(D1). 플래그 없는 Store, `/Merge` 달린 Store, `/Overwrite` 달린 Store는 어느 경로로도 발화되지 않는다.
- **REQ-SCENE-013** [Unwanted] — the 컴파일 **shall not**: (a) `/Overwrite`를 어떤 경로로도 발화하지 않고(블랙리스트 — `server/safety/blacklist.yaml:18`), (b) **`/Merge`를 어떤 경로로도 발화하지 않으며**(D3 — 대소문자 무관 부재), (c) 기존 큐 번호에 Store를 시도하지 않고(재조회로 실측한 빈 번호만 — 콘솔의 `Not allowed` 거부는 마지막 방어선이지 계획 경로가 아니다), (d) 시퀀스·큐 번호를 발명하지 않는다 — 재조회 결과의 `truncated`가 참이면 자동 배정을 **거부**하고 명시 보고한다.
- **REQ-SCENE-014** [Event-driven] — **When** 컴파일이 완료되면, the 시스템 **shall** 한국어 2단 리포트(요약 1단 + 상세 1단)를 반환하며, 그 문면은 아래 **세 주장을 분리해** 싣는다 — 뭉뚱그려 "확인했다"고 적는 것은 금지된다(SONGCUE REQ-SONGCUE-017 규율 계승, 구현 선례 `server/looks/songcue_report.py:15` `PROPERTY_UNOBSERVED_NOTE`):
  - **(a) 기계 확인된 사실** — 생성 시퀀스·큐의 **존재**와 이름·`cueNo`(재조회 실측), 발화 커맨드 수, 실행 결과(실패 시 `not_executed` 목록 전파; **비면제 라인의 `skipped_already_executed` 발생 시 그 목록도 전파하고 성공 보고를 금지**).
  - **(b) 기계 확인 불가 — 효과** — 이펙트의 모션·룩의 발색은 **기계로 확인되지 않는다.** 리포트 **shall** "무대/GUI에서 사람이 확인해야 한다"는 취지를 **무조건**(성공 경로 포함 전 경로에서) 싣는다. FXLIB이 같은 형상의 상수를 이미 갖는다(`server/fx/report.py:52` `EFFECT_EVIDENCE_NOTICE`) — 씬 리포트는 **동형의 자기 상수**를 갖고, 테스트는 **상수 동일성 검사**로 확인한다(산문 비교 금지 — 선례 `server/tests/test_songcue_report.py:119`).
  - **(c) 기계 확인 불가 — 트래킹 차단** — `/CueOnly`가 **접수됐다는 것**과 **트래킹이 실제로 막혔다는 것**은 다른 주장이다. 전자만 기계로 확인되며(큐 실존 재조회), 후자는 **관측 채널이 존재하지 않는다.** 리포트 **shall** 이 둘을 분리해 적고, 접수 확인을 트래킹 차단의 증거로 제시하지 않는다.
- **REQ-SCENE-015** [Ubiquitous] — **값 라인 충돌 가드 (1급 요구 — 경계 2중, FXLIB REQ-FXLIB-011 계승)**:
  - **(a) 번들 내 경계 (구성 시점)**: 번들 구성기 **shall** 구성 완료 시점에 비면제 커맨드 문자열의 **번들 내 유일성**을 검사하고, 중복이 존재하면 번들을 **생성하지 않고** 명시적 에러(`VALUE_LINE_COLLISION` 동형 사유)로 보고한다. 씬 번들은 룩 값 라인과 fx 스텝 값 라인을 **함께** 담으므로 FXLIB 번들보다 값 라인 수가 크고, 따라서 충돌 표면이 넓다.
  - **(b) 지시 턴 경계 (교차 호출 — 실행 결과 시점)**: dedupe의 실제 경계는 번들이 아니라 **지시 턴 전체**다(`server/orchestrator/runner.py` 가 `ExecutionContext(executed_ok=…)`를 다음 호출로 전달; 판정 주석 원문 "either **in a prior tool call** … or earlier in THIS bundle" — `server/orchestrator/tools.py:699-703`). the 툴 **shall** 실행 결과의 커맨드별 outcome을 검사해 **비면제 라인에 `skipped_already_executed`가 1건이라도 있으면 해당 컴파일을 성공으로 보고하지 않고** 교차 호출 충돌을 명시적 실패로 보고한다.
  - **(c) 1차 가드의 정책**: 위반 시 the 컴파일러 **shall** 번들 생성을 **거부(raise)** 한다 — 건너뛰기(skip)가 아니다. 근거: 씬 컴파일은 **하나의 Store**이고 남는 잔여가 없으므로, 부분 산출이라는 개념이 성립하지 않는다(FXLIB `server/fx/instantiate.py:432` 정책 계승 — 세 선례의 비교는 design.md §4).
- **REQ-SCENE-016** [Event-driven] — **When** 사용자가 트리거를 지정하면, the 컴파일러 **shall** 검증된 PROPERTY 형태만 발화한다: `Set Cue <c> Sequence <s> Property 'TrigType' '<Token>'` + `Set Cue <c> Sequence <s> Property 'TrigTime' <절대초>`(`31_choreography_patterns.md:106-117` · `server/looks/songcue.py:488-499`). 트리거 토큰은 **Capitalized 폐쇄 집합**(`Go` / `Time` / `Follow` / `Sound` / `BPM`)이며, `TrigTime`은 **시퀀스 시작 기준 절대 초**다(SONGCUE 라이브 실측 — `progress.md:502`: Cue 2에 `TrigTime 14`를 넣고 readback이 `"14.0"`이었다; 상대 해석이었다면 `"4.0"`이 관측됐어야 한다).
- **REQ-SCENE-017** [Unwanted] — the 컴파일 **shall not** `Assign Cue … /trig=<token>` 옵션 형태를 발화한다 — onPC 2.4.2에서 `"Illegal object"`를 반환한다(`31_choreography_patterns.md:115-117`). 또한 익스큐터를 **자동 배치하지 않는다**(빈 익스큐터는 식별 불가 — BUSKWIZ 측정 2); 사용자가 번호를 명시 지정한 경우에만 `Assign Sequence <n> At Executor <m>` 1줄이 번들 말미에 붙는다.

### B.4 툴 표면

- **REQ-SCENE-018** [Event-driven] — **When** 모델이 `compile_scene`을 호출하면, the 툴 **shall** (룩 id | fx id | 양쪽) + 대상 그룹 + (선택) 시퀀스/큐 번호·트리거·라벨·익스큐터 번호를 받아 **단일 번들을 통째로 조립**하고 기존 `run_commands` 경로로만 실행한다. 대상 그룹은 **rig context 재조회에 등재된 실존 그룹만**이며, 미등재 그룹 번호·이름의 발명과 `Fixture <slot>` 직접 타깃은 금지된다(슬롯≠FID).
  - **단일 툴은 강제된 형상이지 선호가 아니다**: `instantiate_look` → `instantiate_fx`를 한 지시 턴에서 연쇄하는 경로는 **원리적으로 성립하지 않는다.** dedupe 경계가 지시 턴 전체이고 `Step <k>`·스텝 값 라인이 패턴 간 공통 문자열이므로 2회차 번들은 접힌다 — FXLIB이 이를 제외 범위로 명문화했다(`SPEC-COPILOT-FXLIB-001/spec.md:146-148` §D). 따라서 씬은 **하나의 툴이 하나의 번들을 조립**해야 한다(design.md §2).

### B.5 안전·경계 규율 계승

- **REQ-SCENE-019** [Unwanted] — 단일 초크포인트: `server/scene/` **shall not** 어떤 transport(`server.bridge`/`pythonosc`)도, 게이트 표면(`server.safety.gate` / `server.safety.console` / `server.orchestrator.ports`)도 import하지 않는다 — 커맨드는 문자열로만 구성되고, 실행은 `run_commands` → `gate.screen()` 경로 하나다. 신규 `server/scene/`는 `server/tests/test_architecture.py`의 전역 import 스캔에 **자동 포섭**되며, 예외 명단(`_NAMED_TOOL_EXEMPTIONS`)에 항목을 추가하는 것은 금지된다.
- **REQ-SCENE-020** [State-driven] — **While** LiveLock이 활성인 동안, 씬 컴파일 **shall** 제안(Proposal) 전용으로 강등되고 콘솔 송신은 0건이다 — **Store 라인을 포함해** 전 커맨드가 `status == "proposal"`이며, 강등은 **실패가 아니라 답**이므로 `is_error is False`이고 `succeeded is False`다(`server/tests/test_fx_boundary.py:459` 패턴 계승). 본 SPEC은 그 강등 기제를 소비만 하고 수정하지 않는다.

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 동일 머신 로컬 공존, OSC `127.0.0.1` UDP. site config는 effective 값에서만 읽는다 — 하드코딩 금지.
- **기능 전제**: LOOKLIB(`server/looks/` — `status: completed`), FXLIB(`server/fx/` — `status: completed`, main `e4bc78e`에 머지됨), SONGCUE·BUSKWIZ·PRECHK·OVERLAP(전부 머지 완료), MVP 파이프라인(`run_commands`·`gate.screen()` 단일 관문·승인/제안 카드), `get_rig_context` 재조회 + 드릴다운. 전부 `related_specs`(비차단) 참조이며, **run-phase 킥오프 시 각 전제의 실제 상태를 재확인하고 어긋남을 progress.md에 기록한다**.
- **실행 특성 (선행 SPEC 실측 전재 — `[실측]` 원출처는 해당 SPEC 기록)**: `run_commands`는 stop-on-first-failure이며 실패 이후 커맨드는 `not_executed`로 전파된다. 번들 규모 기준선 87줄/5.77s, 줄당 ~66ms(66.3-66.7ms — BUSKWIZ progress.md:278-281 실측 전재). 씬 번들은 **~14-22줄**(룩 값 라인 1줄 + fx 스텝 열 + 트리거 2줄)이므로 여유가 크다.

### C.1 검증 천장 — 무엇이 기계로 확인되고 무엇이 안 되는가

**이 표는 본 SPEC의 인수 설계 전체를 지배한다.** 아래 "NO" 행에 대해 기계 증거를 주장하는 리포트 문면·AC는 그 자체로 결함이다.

| 항목 | 기계 검증 | 경로 |
|---|---|---|
| 큐의 **존재**, 이름, 실제 `cueNo` | **YES** | `state` 재조회 |
| 시퀀스 이름, `childCount` | **YES** | `state` 재조회 |
| `TrigType` / `TrigTime` | **YES** — 단 **게이트 우회 직결 경로** | 응답기 `prop` 동사(v1.5.0), `server/safety/console.py:391` `query_property` |
| `CueFade` | **NO** | 두 경로 모두 `property not readable: CueFade` |
| **큐의 내용(저장된 값)** | **NO** | 반환 경로가 존재하지 않는다 |
| **효과 / 모션 / 발색** | **NO** | 사람의 GUI 관측이 유일 |
| **트래킹 전파(= `/CueOnly`의 실제 작동)** | **NO** | 관측 주체가 없다(`ui/src/components/ExecutionPreviewCard.tsx:61`) |

`Cmd()` OK는 효과 증거가 아니다. FXLIB이 이를 라이브로 증명했다 — *"스텝 쌍 없이 변형 라인만 발화하면 `ok:true` 전량에 모션 0이다"*(M0 §3 실패 3회, `SPEC-COPILOT-FXLIB-001/spec.md:50`).

### C.2 미검증 전제 (ASSUMPTION — FXLIB이 36~40을 사용, 본 SPEC은 41부터)

**각각이 실제로 막는 대상은 서로 다르다** — 전부가 저작을 막는 것은 아니다(LOOKLIB 순서 결함 교훈 계승, 표의 소유는 plan.md §A.2).

- **ASSUMPTION-41 (`/CueOnly` 접수 가능성)**: onPC 2.4.2가 `Store Sequence <s> Cue <c> '<name>' /CueOnly`를 **접수**하고, 그 큐가 재조회에서 기대한 이름·`cueNo`로 실존한다. **미검증** — 리포지토리 전수 grep 0건(코드 발화 이력 없음), 근거는 룰북 산문뿐(`[문서]` 등급). **M0 1순위.** 막는 대상: **M4의 번들 형상(Store 라인) 전체.** 부정 실측(`Illegal object` 류 거부) 시: D1 정책이 성립 불가이므로 **run-phase 중단 + 블로커 보고**이며, 조용한 무플래그 폴백은 **금지**된다(정책이 사용자 확정이므로 대체 결정은 사용자 몫).
- **ASSUMPTION-42 (`/CueOnly`의 트래킹 차단 효과)**: `/CueOnly`로 저장된 큐의 값이 실제로 다음 큐로 트래킹되지 않는다. **미검증이며 기계로는 영원히 미검증이다**(§C.1). **M0에서 사람 GUI 관측으로만 기록**한다. 막는 대상: **없음 — 저작을 막지 않는다.** 부정/미관측이어도 v1 형상은 불변이고, 바뀌는 것은 **리포트 문면의 정직도**뿐이다(REQ-SCENE-014 (c)). 의도적 배칭.
- **ASSUMPTION-43 (임의 큐 번호 Store 가능성)**: `Store Sequence <s> Cue <c>`에서 `c`가 1이 아닌 임의 신규 번호일 때도 저장이 성립한다. **부분 검증** — SONGCUE가 `Cue 2`를 라이브로 성립시켰고(`progress.md:337-344`), `Cue 1.5` 류 소수 큐는 룰북 산문(`:56`)뿐이다. 막는 대상: **없음 — v1은 정수 큐 번호만 쓴다.** 소수 큐는 §D 제외.
- **ASSUMPTION-44 (룩 값 라인과 fx 스텝 열의 결합 성립)**: 룩의 `;` 체인 값 라인이 스텝 1에 착지하고, 그 위에서 fx 스텝 열이 페이저를 성립시킨다. **미검증** — 두 계층이 한 번들에서 결합된 실측이 0건이다. **M0 2순위.** 막는 대상: **M4 번들 형상 + M2 결합 규칙.** 부정 실측 시: 결합 순서의 재설계가 필요하므로 **블로커 보고**(조용한 진행 금지).
- **ASSUMPTION-45 (충돌 attribute의 승자 확인 가능성)**: 룩과 이펙트가 같은 attribute를 지정했을 때 **어느 쪽이 이겼는지**를 관측할 수 있다. **미검증이며 §C.1상 기계로는 불가**(큐 내용 판독 불가). **M0에서 GUI 사람 관측으로만 기록**한다. 막는 대상: **없음** — D2가 "나중 라인이 이긴다"를 **형상으로 강제**하므로(이펙트 라인이 뒤에 온다) 관측 실패는 리포트 열거의 신뢰도만 낮추고, 열거 자체는 **컴파일 시점 정적 계산**이라 관측과 무관하게 정확하다.
- **측정된 기준선**: 기반 `main` = `e4bc78e`(clean). pytest/vitest 수치는 plan-phase가 단언하지 않는다 — **각 마일스톤 착수 직전 직접 실측**한다(baseline-integrity 원칙). 오케스트레이터 세션 실측값(2026-08-01, 참고용): pytest 3432 passed / 5 skipped, vitest 223. 본 아티팩트 6종의 커밋 SHA는 자기참조 불가이므로 `pending-backfill`이다.

## D. 제외 범위 (Out of Scope)

### Out of Scope — 오디오 분석 / 음악 구조 추출

- 오디오 파일 판독, BPM 자동 검출, 섹션 경계 자동 분할 일체. 본 SPEC의 타이밍은 **호출자가 주는 수치**이며, 곡 구조 축은 SONGCUE(큐리스트)의 영역이다.

### Out of Scope — 프리셋 참조 큐

- 큐가 프리셋을 참조하게 만드는 축 일체. `Assign Preset … At Cue` 계열 문법은 **저장소 근거 0건**이며, "큐는 프로그래머 상태를 직접 캡처한다"가 확립된 사실이다(`SPEC-COPILOT-SONGCUE-001/spec.md:264-267`). 씬 컴파일러는 룩의 **값**을 큐에 재캡처하며, `instantiate_look`이 만든 프리셋을 **가리키지 않는다**.

### Out of Scope — 익스큐터 자동 배치·바인딩

- 빈 익스큐터 탐색·자동 `Assign` 일체 — 빈 익스큐터는 식별 불가다(BUSKWIZ 측정 2). 사용자 명시 지정 시의 `Assign Sequence <n> At Executor <m>` 1줄만 선택적으로 허용된다(REQ-SCENE-017).

### Out of Scope — 큐 편집 · 재배열 · 삭제

- 기존 큐의 값 수정, 큐 번호 재배열, `Delete Cue` 일체. v1은 **비어 있는 큐 번호에 새로 쓰는 것**만 한다(D3). 편집 경로는 기존 큐 번호를 건드리므로 `Not allowed` 안전망과 정면 충돌한다.

### Out of Scope — 섹션 점프 / `Goto Cue`

- `Goto Cue <n>` 류 큐 이동 커맨드 일체. 게이트의 `RECOGNIZED_REFERENCE_TYPES`(`server/safety/classify.py:44`)는 `("Macro", "Plugin", "Sequence", "Executor")`이며 **`Cue`가 없다** — 큐 참조 커맨드는 게이트가 인식하는 참조 종별이 아니므로, 그 축을 여는 것은 게이트 어휘 확장을 요구한다. 본 SPEC은 `server/safety/**` 무변경이므로 보류한다.

### Out of Scope — `CueFade` 및 판독 불가 프로퍼티

- `CueFade` 설정 축 일체. 두 경로 모두 `property not readable: CueFade`이므로 **설정해도 확인할 수 없다**(§C.1). 확인 불가 프로퍼티를 v1 산출물에 넣지 않는다.

### Out of Scope — 소수 큐 번호

- `Cue 1.5` / `1.55` 류 소수 큐 번호. 룰북 산문(`:56`)에만 존재하고 라이브 실측 0건이다(ASSUMPTION-43). v1은 정수 큐 번호만 쓴다.

### Out of Scope — 지시 턴당 2회 이상의 컴파일

- 한 지시 턴에서 `compile_scene`을 2회 이상 온전히 성립시키는 축. dedupe 경계가 **지시 턴 전체**이고 `Step <k>`·값 라인이 씬 간 공통 문자열이므로 2회차 번들은 접힌다(FXLIB `spec.md:146-148` 계승). v1은 넓히는 대신 **명시 실패로 막는다**(REQ-SCENE-015 (b)).

### Out of Scope — dedupe 전역 의미론 변경

- `_PROGRAMMER_STATE_COMMANDS` 면제 집합 확장, dedupe 판정 루프 개정 일체. dedupe 규칙 개정은 **기각된 선례**다(BUSKWIZ 결정). SONGCUE가 같은 규율을 명문화했다 — *"본 SPEC 하나를 위해 전역 실행 의미론을 바꾸지 않는다"*(`spec.md:298-302`).

### Out of Scope — 룰북 자산 변경

- `server/rulebook/assets/v2.4.2/**` 일체 (PRESERVE — byte-diff 0). `server/tests/test_fx_boundary.py:595`가 *"the rulebook never learned about fx"* 를 단언하는 것과 같은 규율로, **씬 계층도 룰북 어휘를 추가하지 않는다.** 툴 발견성은 툴 스키마 설명 문면이 전담한다.

### Out of Scope — SONGCUE 트래킹 정책 소급 변경

- SONGCUE가 무플래그로 Store하는 사실(= 오늘 그 큐들의 값이 트래킹된다)은 **기록하되 고치지 않는다**. `server/looks/**`는 PRESERVE이며, 소급 정책 변경은 별도 SPEC의 결정이다.

### Out of Scope — 콘솔측 Lua 변경 / 비게이트 실행 경로

- `console/lua/copilot_responder.lua` 및 신규 프로토콜 동사 일체 (PRESERVE). 실행용 REST 엔드포인트, 제2 스크리닝, `server/scene/`의 OSC·게이트 표면 직접 import 일체 (REQ-SCENE-019).

### Out of Scope — UI 표면 변경

- `ui/src/**` 및 패널 타일 추가. v1 표면은 기존 채팅 + 툴이다.

### Out of Scope — 생성형 Lua 경로

- 씬 컴파일을 Lua 플러그인 생성으로 구현하는 축. v1 번들은 ~14-22줄 규모이므로 커맨드라인 문자열로 충분하다.

## E. 참조 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 참조 원본 (file:line — 착수 직전 재실측 관례 적용) |
|---|---|
| 후속 좌석 예약 3곳 (본 SPEC의 존재 근거) | `SPEC-COPILOT-FXLIB-001/spec.md:42, :70, :140` — `[문서]` |
| **`/CueOnly` 코드 발화 0건 (전수 grep)** | `server/**` · `ui/src/**` · `console/**` — 매치 0건, 2026-08-01 코디네이터 직접 실행 — `[코드]` |
| `/CueOnly` 문법·트래킹 모델 | `31_choreography_patterns.md:59, :130-134` — `[문서]` |
| Store 플래그 라이브 실측 (신규 번호 = `/Merge` 불요 · 기존 번호 = `Not allowed`) | `SPEC-COPILOT-SONGCUE-001/progress.md:337-344` — `[실측]` |
| `Not allowed` = 마지막 방어선 | `server/fx/instantiate.py:225` — `[코드]` |
| `/Overwrite` 봉쇄 4곳 | `31_choreography_patterns.md:57-58` · `server/safety/blacklist.yaml:18` · `DESIGN.md:133` · `server/web/preview.py:113` — `[코드]` |
| 대소문자 무관 assert 논거 (대소문자 고정은 위양성) | `SPEC-COPILOT-BUSKWIZ-001/design.md:209` — `[문서]` |
| **`MIN_STEPS = 2` + `Step 1` 미발화** (룩 먼저의 강제 근거) | `server/fx/schema.py:66` · `server/fx/instantiate.py:326-342` — `[코드]` |
| fx 큐 번호 상수 고정 (씬이 넘어야 할 축) | `server/fx/instantiate.py:96` (`_CUE_NUMBER = 1`), `:481` (Store 라인) — `[코드]` |
| `select_sequence_number` 2벌 (fx는 `requested=` 지원) | `server/fx/instantiate.py:218` · `server/looks/songcue.py:286` — `[코드]` |
| 1차 가드 정책 3갈래 (raise / skip / skip+ledger) | `server/fx/instantiate.py:432` · `server/looks/busking.py:240` · `server/looks/songcue.py:436` + ledger `:243` — `[코드]` |
| 2차 가드 (지시 턴 경계) — **looks 쪽에 대응물 없음** | `server/fx/instantiate.py:537` `collided_lines` — `[코드]` |
| dedupe 판정 + 면제 3종 + 축적 경계 | `server/orchestrator/tools.py:327-331, :688-712` · `runner.py` ExecutionContext — `[코드]` |
| 툴 핸들러 = `run_commands`의 **caller** (제2 실행 표면 금지) | `server/orchestrator/tools.py:638, :848-858, :1116, :1688-1698` — `[코드]` |
| 트리거 PROPERTY 형태 + `/trig=` 금지 | `31_choreography_patterns.md:106-117` · `server/looks/songcue.py:488-499` — `[문서]`+`[코드]` |
| `TrigTime` = 절대 초 (라이브 2점 판별) | `SPEC-COPILOT-SONGCUE-001/progress.md:502` — `[실측]` |
| 시퀀스 라벨 위치 (첫 Store 직후) | `server/looks/songcue.py:258-266`, `_first_store_index:520` — `[코드]` |
| 큐 사후 개명 경로 부재 (`Label Cue` 0건) | SONGCUE REQ-SONGCUE-008 — `[문서]` |
| 프리셋 참조 문법 근거 0건 | `SPEC-COPILOT-SONGCUE-001/spec.md:264-267` — `[문서]` |
| 게이트 참조 종별에 `Cue` 부재 | `server/safety/classify.py:44` — `[코드]` |
| `query_property` (게이트 우회 직결 경로) | `server/safety/console.py:391` — `[코드]` |
| 효과 증거 상수 선례 + 상수 동일성 검사 선례 | `server/fx/report.py:52` · `server/looks/songcue_report.py:15` · `server/tests/test_songcue_report.py:119` — `[코드]` |
| 경계 AST 스캔 · 예외 명단 고정 · LiveLock 강등 패턴 | `server/tests/test_fx_boundary.py:132, :228-230, :459` · `test_looks_boundary.py:85` — `[코드]` |
| 룰북 무학습 단언 선례 | `server/tests/test_fx_boundary.py:595` — `[코드]` |
| 한 턴 2회 인스턴스화 불가 (단일 툴의 강제 근거) | `SPEC-COPILOT-FXLIB-001/spec.md:146-148` — `[문서]` |
| 전역 실행 의미론 불변 규율 | `SPEC-COPILOT-SONGCUE-001/spec.md:298-302` — `[문서]` |
| 트래킹 미관측 진술 | `ui/src/components/ExecutionPreviewCard.tsx:61` — `[코드]` |
