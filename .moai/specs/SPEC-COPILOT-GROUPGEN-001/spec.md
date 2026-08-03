---
id: SPEC-COPILOT-GROUPGEN-001
title: "배치 인식 그룹 생성 — 위상 분류(topology) + 장비 종류 분류 (Arrangement-Aware Group Generation)"
version: "0.1.0"
status: draft
created: 2026-08-03
updated: 2026-08-03
author: orchestrator (pre-plan)
priority: P1
phase: "Phase 2 연출 계층 — 공간 축 후속 (배치를 영속 자산으로)"
module: "server/spatial/topology.py (신규), server/spatial/naming.py (신규), server/orchestrator/tools.py, server/safety/** (조건부)"
lifecycle: spec-anchored
tags: "group, topology, classification, downstage-upstage, stage-left-right, concentric, fixture-type, gdtf, store-group, membership-readback, industry-terminology"
tier: L
related_specs: [SPEC-COPILOT-SPATIAL-001, SPEC-COPILOT-SCENE-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-FXLIB-001, SPEC-COPILOT-OVERLAP-001]
---

# SPEC-COPILOT-GROUPGEN-001 — 배치 인식 그룹 생성

> **이 SPEC이 닫는 구멍**: SPATIAL-001은 좌표를 읽고 **선택 순서**를 만들 수 있게 했지만, 선택은
> 프로그래머 상태이고 `ClearAll`로 사라진다. 매 발화가 순서를 다시 세운다. 그래서 *"뒷줄만 파랗게"* ·
> *"바깥 링만 반짝"* 을 표현할 수 없고, 사용자가 콘솔에서 손으로 그 부분 리그를 잡을 수도 없다.
> 그리고 더 나쁜 것: **현재 분석 계층은 행이 아닌 배치를 고신뢰로 오독한다** — 2겹 동심원을 넣으면
> `rows=9`, 구성 `[1,2,2,2,4,2,2,2,1]`, `low_confidence=False`를 답한다(실측). 위상 가설이 하나뿐이기 때문이다.

> **status 주의**: 본 문서는 `/moai plan` **전에** 작성된 draft다. `acceptance.md`(AC) · `design.md`는
> 아직 없다. 근거는 `research.md`(v0.5.0)와 `plan.md`(v0.1.0)이며 **`research.md`의 `[실측]`은
> 라이브 onPC 2.4.2 직접 관측**이므로 구속력을 갖는다.

## HISTORY

| version | date | 변경 |
|---|---|---|
| 0.1.0 | 2026-08-03 | 초안. `research.md` v0.5.0(요구 정정 · 업계 표준 어휘 · 세분화 축 6개 · 장비 종류·명칭 실측)과 `plan.md` v0.1.0(M0~M6 · 게이트 A~D)을 REQ로 전개. ASSUMPTION 61~67 배정 |

## A. 개요

### A.1 핵심 원리 — 이름은 결과이고 **판별이 본체**다

사용자 요구는 *"3열이면 Front/Center/Back"* 이라는 **고정 사상표가 아니다**:

> *"2겹의 원형이면 Inner, Outer, 좌우로 배치되면 Left, Right 등과 같이 **배치되는 특성에 맞게**
> 그룹을 잡고 라벨을 설정해달라는 거야."*

따라서 이 SPEC의 중심은 **배치의 위상(topology) 분류**이고, 그룹 쓰기는 그 결과의 출력이다.
깊이 방향 행인가 · 동심원인가 · 좌우 분할인가 · 수직 층인가 — 이것을 먼저 판별해야 이름을 고를 수 있다.

### A.2 그룹이 선택 순서를 대체하지 않는다 — 3층 분업

```
GROUPGEN 그룹   = 누구를      (영속 · 이름 있음 · 콘솔에서 손으로도 쓸 수 있음)
SPATIAL 선택순서 = 어떤 순서로  (런타임 · 방향을 만든다)
MAtricks        = 어떻게 재성형 (런타임 · 윙 · 블록 · 홀짝 · 셔플)
```

**MAtricks는 MA3의 기존 기능이며 이 SPEC이 재구현하지 않는다**(§D). 룰북
`31_choreography_patterns.md:85-90`이 이미 `XWings`·`XShuffle`·`PhaseFromX/ToX`를 검증된 문법으로 싣고 있다.

### A.3 어휘는 발명하지 않는다 — 업계 표준을 조사로 확정했다

`research.md` §6이 근거다. **MA Lighting 공식 문서가 축 의미를 규정한다**:
**+x = stage left 방향** · **+y = upstage** · +z = height.

그리고 **stage left/right(배우 기준)와 house left/right(객석 기준)는 정반대**다.
→ 그룹 이름에 **맨 `Left`/`Right`를 쓰지 않는다**(REQ-GROUPGEN-013).

| 위상 | 2분할 | 3분할 | 4+ 폴백 | 표준성 |
|---|---|---|---|---|
| 깊이 | Downstage / Upstage | + Center | `Electric 1..N` (DS→US) | **표준** |
| 좌우 | Stage Right / Stage Left | + Center | — | **표준** |
| 그리드 | — | `DSR…USL` 9칸 | `Area N` | **표준** |
| 동심원 | Inner / Outer | + Mid | `Ring 1..N` | **표준 없음** — 관례 |
| 수직 | Low Side / High Side | — | `Level 1..N` | 부분 표준 |

### A.4 M0 게이트 — 멤버십을 읽을 수 없으면 이 SPEC은 성립하지 않는다

`[실측]` `Group 13 'All'`은 `exec`이 `OK`인 실사용 그룹인데 `query_state`는 `childCount: 0`을 준다.
→ **그룹 멤버십은 오브젝트 트리 경로로 노출되지 않는다.** `0`은 *"비었다"*가 아니라 *"이 채널로는 안 보인다"*다.

3중 잠금이 생긴다: **재조회 검증 불가** + **백업 불가**(못 읽으니 보관 못 함) +
**복구 불가**(`Delete` 블랙리스트 · restore SEND 부재 T-B2).

| 게이트 | GO | NEGATIVE |
|---|---|---|
| **A. 멤버십 판독 채널** | 자동 생성 진행 | **자동 생성 중단 → 제안(발화 목록) 전용 강등.** 대체 정책을 에이전트가 고르지 않는다 |
| **B. `Store Group` 생성** | M3 진행 | **SPEC 전체 중단** |
| **C. 점유 슬롯 덮어쓰기** | 차단 규칙 실측 확정 | 조용히 덮으면 차단이 **더욱 절대적** (강화, NEGATIVE 아님) |

## B. 요구사항 (GEARS)

### B.1 위상 분류 (순수 계층)

- **REQ-GROUPGEN-001** [Ubiquitous] — 신규 모듈 `server/spatial/topology.py` **shall** 순수 위상 분류를
  제공한다: `depth_rows`(y축) · `lateral_split`(x축) · `concentric`(중심으로부터 반지름) ·
  `vertical_levels`(z축) · `grid`(y·x 양축) · `bilateral_pairs`(x=0 대칭 쌍). 콘솔 무접촉이며 단위
  테스트만으로 완전 검증 가능하다.
- **REQ-GROUPGEN-002** [Ubiquitous] — 분류 **shall** 결정론적이다: 같은 입력 → 같은 출력.
  동률·모호는 임의 선택 대신 **명시 신호**로 처리한다(SPATIAL REQ-SPATIAL-010 규율 계승).
- **REQ-GROUPGEN-003** [Ubiquitous] — 분류 **shall** 서로 다른 위상을 **구조적으로 구별**한다.
  특히 **2겹 동심원과 3행 그리드가 다른 위상으로 판정**되어야 한다 — 현재 계층이 동심원을 9행
  고신뢰로 오독하는 것이 이 요구의 존재 이유이며, "항상 `depth_rows`"를 답하는 분류기는 신호가 아니다.
- **REQ-GROUPGEN-004** [Event-driven] — **When** 어느 위상도 뚜렷하지 않으면, the 분류 **shall**
  위상 `None` + 저신뢰 신호를 반환한다 — 위상을 조용히 단정하지 않는다.
- **REQ-GROUPGEN-005** [Unwanted] — 본 SPEC **shall not** `server/spatial/rows.py` ·
  `sorting.py` · `presets.py` · `choreography.py`의 동작을 변경한다. 기존 행 검출은 **위상 후보 1종으로
  편입**되며 대체되지 않는다. SPATIAL 테스트 전량 무수정 PASS.
- **REQ-GROUPGEN-006** [Unwanted] — `server/spatial/topology.py` **shall not**
  transport(`server.bridge`/`pythonosc`)·게이트 표면을 import한다 —
  `server/tests/test_architecture.py` 전역 스캔에 자동 포섭되며 예외 명단 추가는 금지된다.
- **REQ-GROUPGEN-007** [Ubiquitous] — 분류 **shall** 신규 런타임 의존성 0으로 구현된다.
  반지름·각도는 표준 `math`로 충분하다(SPATIAL §C.1 계승 — 클러스터링 라이브러리 금지).

### B.2 장비 종류·명칭 분류

- **REQ-GROUPGEN-008** [Ubiquitous] — 종류 판독 **shall** 실측 확인된 2-hop 경로를 쓴다:
  픽스처 `fixturetype` → `Patch/FixtureTypes/<n>` → `name` / `ShortName` / `Manufacturer`.
  (`[실측]` `fixturetype` → `'FixtureType 1'` · `ShortName` → `'RMMXSm1'` · `Manufacturer` → `'Robe'`)
- **REQ-GROUPGEN-009** [Ubiquitous] — 제조사·타입명 그룹 **shall** 패치의 구조화 필드를 **그대로** 쓴다
  (문자열 가공 0). 이것이 종류 축의 가장 안전한 층위다.
- **REQ-GROUPGEN-010** [Event-driven] — **When** 업계 카테고리(`Spot`/`Wash`/`Beam`/`PAR`/`Fresnel`/
  `Profile`/`Strobe`/`Blinder`/`Effect`/`Follow Spot`) 그룹을 만들면, the 분류 **shall** 타입명에 대한
  **폐쇄 어휘 토큰 매칭**으로만 판정한다 — **GDTF 스펙 FixtureType 노드에 `Categories` 필드가 없어**
  타입명 문자열이 유일한 근거이기 때문이다.
- **REQ-GROUPGEN-011** [Unwanted] — 카테고리 판정 **shall not** 추측한다: **무매칭이면 그룹을 만들지
  않고**, 다중 매칭(예: `Wash Beam`)은 **모호로 표기**한다.
- **REQ-GROUPGEN-012** [Unwanted] — `Blinder`로 판정된 픽스처 **shall not** 무대 위상 그룹에 포함된다 —
  블라인더는 **관객을 비추는** 장비이며, 위상 그룹에 섞이면 연출이 관객을 향한다.
- **REQ-GROUPGEN-013** [Unwanted] — 본 SPEC **shall not** 픽스처 **명칭**(자유 문자열)으로 그룹을
  자동 생성한다. 근거는 실측이다: 동일 타입 19대에 명명 패턴이 **3가지**다
  (자동 `RMMXSm1 1` = `ShortName`+번호 · 사용자 `Copilot MMX n` · 사용자 `MMX n`).
  이름 그룹은 의미 없는 3그룹을 쇼파일에 **영속**시킨다.
- **REQ-GROUPGEN-014** [Optional] — 명칭 클러스터가 감지되면 the 앱 **may** 이를 **제안**으로 보고하고
  사용자 확정을 받는다. 자동 작명 패턴(`ShortName + " " + n`)은 **신호가 아니므로 제외**한다.

### B.3 명명 어휘 (업계 표준 · 폐쇄)

- **REQ-GROUPGEN-015** [Ubiquitous] — 그룹 이름 **shall** §A.3 폐쇄 어휘에서만 선택된다.
  깊이 축은 **`Downstage`/`Center`/`Upstage`**이며 **`Front`/`Back`을 쓰지 않는다** — 업계 표준이
  전자이고, 후자는 front light **system**(기능 축)으로 읽혀 충돌한다.
- **REQ-GROUPGEN-016** [Unwanted] — 그룹 이름 **shall not** 기준 없는 `Left`/`Right`를 쓴다.
  stage 기준과 house 기준은 **정반대**이므로 `Stage Left`/`Stage Right`처럼 **기준을 이름에 박는다**.
- **REQ-GROUPGEN-017** [Ubiquitous] — 번호 폴백 **shall** 순서 방향을 명시한다.
  깊이 축은 **`Electric 1..N`이며 downstage → upstage**(오버헤드 바는 프로시니엄에서 upstage로 번호를
  매기는 업계 표준). 그 외 축의 번호 방향은 문서화 대상이다 — McCandless 영역 번호도 방향이
  표준화되지 않았다.
- **REQ-GROUPGEN-018** [Ubiquitous] — 생성 그룹 이름 **shall** 접두 규칙으로 기하 그룹임을 드러낸다.
  이는 두 문제를 동시에 해결한다: 기존 이름 충돌 회피(§C.3) + **기하 축과 기능 축의 구분**.
- **REQ-GROUPGEN-019** [Unwanted] — 그룹 이름 **shall not** 기능/시스템 어휘를 차용한다
  (front light system · backlight system · cross-left/right sidelight · key/fill/back · wash/special).
  이름은 **위치·종류**를 말하고 **역할**을 말하지 않는다 — `Downstage` 픽스처가 백라이트로 쓰일 수 있다.

### B.4 그룹 쓰기 (안전 — 게이트 A·B GO 전제)

- **REQ-GROUPGEN-020** [Ubiquitous] — 슬롯 선택 **shall** 재조회한 풀에서 **실측**한다.
  번호를 세지 않는다 — 실측 그룹 풀이 비연속이다(`1 · 11 · 12 · 13 · 15`).
  `server/scene/compile.py::_select_cue_number` 패턴을 계승한다.
- **REQ-GROUPGEN-021** [Event-driven] — **When** 그룹 풀 목록이 절단되면, the 슬롯 할당 **shall**
  거부된다 — 보이지 않는 슬롯이 후보 번호를 점유할 수 있다(`_select_cue_number` 선례의 문면 계승).
- **REQ-GROUPGEN-022** [Unwanted] — 기록 **shall not** 점유된 슬롯을 대상으로 한다.
  멤버십을 읽을 수 없어 **백업이 불가하고** `Delete`는 블랙리스트이며 restore SEND 경로가 없다 —
  덮어쓰기는 **복구 불가**다. 이는 선호가 아니라 강제 제약이며 **정적으로 차단**한다.
- **REQ-GROUPGEN-023** [Event-driven] — **When** 그룹이 기록되면, the 앱 **shall** 멤버십을 **재조회로
  검증**한다. 검증 채널이 부재하면(게이트 A NEGATIVE) **검증 불가를 명시**하고 제안 전용으로 강등한다 —
  `ok:true`를 증거로 삼지 않는다.
- **REQ-GROUPGEN-024** [Event-driven] — **When** 픽스처 목록이 절단된 상태면, the 그룹 생성 **shall**
  거부되거나 **명시 경고**를 동반한다. 18/19만 담긴 그룹은 조용히 틀린 자산으로 **영속**한다 —
  선택은 `ClearAll`로 사라지지만 그룹은 남는다.
- **REQ-GROUPGEN-025** [Ubiquitous] — 발화 슬롯 집합 **shall** 실측 빈 슬롯 집합과 일치한다
  (정적 단언 가능). 기존 슬롯 접촉 0.
- **REQ-GROUPGEN-026** [State-driven] — **While** LiveLock이 활성이면, the 전 단계 **shall** 제안으로
  강등된다 — 콘솔 송신 0(멤버십 판독조차 하지 않는다).
- **REQ-GROUPGEN-027** [Ubiquitous] — 위상 × 종류 **교차** 그룹 **shall** 폭발 제어를 갖는다:
  **멤버 0 교차는 그룹을 만들지 않으며**, 교차 그룹 수 상한과 초과 시 거동을 정의한다.
  빈 슬롯이 유한하므로(`2~10 · 14 · 16+`) 교차 폭발은 **슬롯 고갈로 직결된다**.

### B.5 툴 표면 + 라이브 판정 기록

- **REQ-GROUPGEN-028** [Ubiquitous] — 툴 표면 **shall** 읽기/제안과 쇼파일 변형을 **분리**한다
  (SPATIAL D-4 선례: 한 툴에 두면 승인 카드 분류가 흐려진다). 닫힌 툴 집합 개수 갱신 필수.
- **REQ-GROUPGEN-029** [Ubiquitous] — M0 라이브 판정 **shall** `progress.md §E.2`에 폐쇄 어휘 +
  행두 접두 행으로 기록된다. 미프로브 전제도 `SKIP:`(`CONDITION_NOT_MET`) 행을 받는다.
- **REQ-GROUPGEN-030** [Event-driven] — **When** 리그가 동종(타입 1종)이면, the 종류 축 산출 **shall**
  0이며 그 사실이 보고된다 — 실측 리그가 정확히 이 경우다(`FixtureTypes` childCount **1**).

## C. 환경 및 전제

### C.1 검증 천장 — 무엇이 기계로 확인되고 무엇이 안 되는가

| 대상 | 기계 확인 | 수단 |
|---|---|---|
| 위상 분류·명명·교차 산출의 정확성 | **YES** | 순수 Python — 콘솔 무접촉 |
| 슬롯 실측·절단 거부·점유 차단·범위 봉쇄 | **YES** | 단위 테스트 + 정적 단언 |
| 발화 커맨드 형상 | **YES** | 산출 문자열 정적 검사 |
| **그룹 멤버십이 의도한 픽스처인가** | **조건부** — ASSUMPTION-61 GO 시 | 멤버십 재조회 |
| 종류 축의 이종 리그 거동 | **NO** (이 리그로는) | 합성 golden 필수 — 리그가 동종 |
| 그룹이 연출에서 "맞게" 동작하는가 | **NO** | 사람 관측만(SPATIAL §C.1 계승) |

### C.2 미검증 전제 (ASSUMPTION — SPATIAL-001이 53~60 사용, 본 SPEC은 **61부터**)

- **ASSUMPTION-61 (그룹 멤버십 판독 채널)** — 그룹의 멤버 픽스처를 판독할 채널이 존재한다.
  `[실측]` `query_state`로는 **불가**(`Group 13 'All'` → `childCount: 0`인데 `exec`은 `OK`).
  `prop` 사다리로 후보 속성을 탐색해야 한다. **NEGATIVE면 자동 생성 축 중단 → 제안 전용 강등**(§A.4 게이트 A).
- **ASSUMPTION-62 (그룹 속성 채널의 변별력)** — 날조 속성 판독이 **실패**한다.
  `ok`로 통과하면 그 사실 자체를 `CONDITION_NOT_MET`으로 기록하고 값 대조로 판정을 대체한다.
- **ASSUMPTION-63 (`Store Group <n>` 생성)** — 선택 후 `Store Group <n>`이 그룹을 만든다.
  문법은 `00_grammar.md:66`에 있으나 **"(validated)" 표기가 없다.** **NEGATIVE면 SPEC 전체 중단.**
- **ASSUMPTION-64 (`Label Group <n> '<name>'`)** — 라벨이 적용되고 이름이 재조회된다.
- **ASSUMPTION-65 (점유 슬롯 덮어쓰기 거동)** — 점유 슬롯에 `Store Group`을 쏘면 조용히 덮는가,
  거부하는가. 조용히 덮으면 차단 요구(REQ-GROUPGEN-022)가 **더욱 절대적**이 된다.
- **ASSUMPTION-66 (게이트 분류)** — `Store Group <n>` · `Label Group <n> '…'`이 안전 게이트에서
  `safe`/`risky` 어느 쪽으로 분류되는가. 블랙리스트 v1에 `Store Group`(무플래그)은 **없다**.
- **ASSUMPTION-67 (카테고리 토큰 매칭의 실효성)** — 실제 이종 리그의 타입명이 폐쇄 어휘로 판정 가능한가.
  **우리 리그로는 검증 불가**(타입 1종) — 합성 golden + 별도 리그 필요.

### C.3 상속 제약 (선행 SPEC·조사 실측 — 재발 방지)

1. **기존 그룹 `1 · 11 · 12 · 13 · 15`는 절대 PRESERVE** — 슬롯 비연속이며 `Front`·`Back`·
   `Inner Outer Opp`가 **이미 존재**해 사용자 예시 어휘와 충돌한다. 멤버십을 읽을 수 없어 백업 불가다.
2. **`Group 11`은 룰북의 검증된 페이저 예시가 사용**(`31_choreography_patterns.md:48,67,163`) —
   건드리면 룰북 문면이 거짓이 된다.
3. **`exec`는 큰따옴표를 거부**(`server/bridge/protocol.py:109`). 값은 작은따옴표.
4. **`ok`는 증거가 아니다** — SCENE `/CueOnlyy`(날조가 `ok` 통과) · SPATIAL 음수 좌표 5형태 중 3형태가
   `OK`+틀린 값. 재조회만이 증거다.
5. **좌표 기록이 현재 무승인으로 나간다**(AC-SPATIAL-031 `[DEFERRED]`). 요청하지 않은 기록 54건이
   실제로 통과한 관측 사례가 있다 — 그룹은 복구 불가라 이 위험이 더 크다.
6. **툴 설명문은 지시일 뿐 강제가 아니다** — SPATIAL이 설명문에 "say so"를 명령형으로 적었는데 모델이
   무시했다. 중요한 불변식은 **구조로** 강제한다.
7. **M0 프로브 정리 경로를 프로브 전에 정한다** — `Delete`가 블랙리스트다. SCENE M0의 "시퀀스 7개 GUI
   삭제" 부채를 반복하지 않는다. **빈 슬롯 1개만** 표적으로 쓴다.
8. **`DEFAULT_MAX_MODEL_CALLS = 12`** — 복합 지시는 `loop_limit`(부분 실행)이 된다(실측).
   왕복 66.7 ms · `CONFIG.max_payload = 1900`.

## D. 제외 범위 (Out of Scope)

### Out of Scope — 런타임 효과 분할 (MAtricks 중복 구현)
`Wings` · `Block` · `Group`(MAtricks) · `Width` · `Shuffle` · `Invert`/`Mirror`는 **MA3의 기존 기능**이며
공식 정의가 *"divide a selection of fixtures into sub-selections"*다. 룰북 `31:85-90`이 이미 검증된
문법으로 싣고 있다. 홀짝·윙·블록은 **런타임 재성형**이며 영속 자산이 아니다 — 그룹으로 만들지 않는다.

### Out of Scope — 기능/시스템 축 자동 판정
front/back/side light system · cross-left/right sidelight · key/fill/back · wash/special/background ·
two-color warm/cool. **전문가의 1차 그룹 축이지만 좌표에 없는 정보**다 — downstage 픽스처가
백라이트일 수 있다. `rot*`로 조준 방향 추론은 원리적으로 가능하나 회전 좌표계가 미검증이고 *추론된*
기능에 확정 이름을 붙이는 것은 발명이다. **별도 SPEC 후보.**

### Out of Scope — 리깅 하드웨어 위치 판정
FOH · Boom · Box Boom · Ladder · Torm · floor package. 하드웨어 **구조명**이며 패치에 없다.
좌표로 추정해 이름 붙이면 거짓 자산이 영속한다. 단 `Electric N` 어휘는 깊이 폴백으로 **차용**한다 —
"몇 번째 바인가"는 y 순서로 정직하게 말할 수 있는 것이기 때문이다.

### Out of Scope — 명칭 기반 자동 그룹 생성
REQ-GROUPGEN-013. 제안(REQ-GROUPGEN-014)까지만.

### Out of Scope — 기존 그룹의 수정·삭제·재배치
점유 슬롯은 읽지도 쓰지도 않는다. 정리·병합·개명은 사용자의 일이다.

### Out of Scope — SPATIAL 정렬 어휘 개명
`left_to_right`가 house 기준이라는 소급 발견(SPATIAL §E.2.21)의 **개명은 출하된 폐쇄 집합의 파괴적
변경**이다. SPATIAL sync-phase 인계 사항이며 본 SPEC은 **자신의 이름에 기준을 박는 것**으로 대응한다.

### Out of Scope — MVR / GDTF 임포트
GDTF 파일을 직접 파싱하지 않는다. 콘솔이 이미 임포트한 결과(`Patch/FixtureTypes`)만 소비한다.

### Out of Scope — 물리 검증
트러스 하중·충돌·중력·조준 가능성 일체. 그룹은 좌표·타입의 분류일 뿐이다.

### Out of Scope — 기존 룰북 자산 변경
`00~32` byte-diff 0. 신설 시에도 **OVERLAP-001 불변식 게이트 예외 절차를 다시 밟아야 한다**
(SPATIAL §E.2.19 선례 — 룰북 디렉터리는 5개 명명 자산으로 정밀화되어 있고 추가는 이름으로 핀된다).

## E. 참조 (연구 근거 — 구속력 있음)

| 근거 | 위치 | 등급 |
|---|---|---|
| 그룹 풀 실측 · 멤버십 판독 불가 · 타입 2-hop · 명명 패턴 3종 | `research.md` §2 · §5.1 · §7.3.1 · §7.3.3 | `[실측]` |
| 동심원 고신뢰 오독 (`rows=9`) | `research.md` §3 | `[실측]` |
| MA3 축 의미 (+x = stage left · +y = upstage) | `research.md` §6.1 — `help.malighting.com` | `[인수-웹, 규범]` |
| stage/house 좌우 반전 · `left_to_right` 소급 결함 | `research.md` §6.3 · SPATIAL `progress.md` §E.2.21 | `[인수-웹]` + `[실측]` |
| 표준 어휘 (DS/CS/US · 9칸 그리드 · Electric N · 붐 번호) | `research.md` §6.2 · §6.4 · §7.1 | `[인수-웹]` |
| 동심원 표준 부재 | `research.md` §6.6 | `[인수-웹]` |
| 기능 축이 전문가의 1차 축 (ETC · Vectorworks) | `research.md` §6.7 · §7.2 | `[인수-웹]` |
| MAtricks 공식 정의 (Wings/Block/Group/Shuffle) | `research.md` §7.5 | `[인수-웹, 규범]` |
| **GDTF에 `Categories` 필드 없음** | `research.md` §7.3.2 — `gdtf.eu` 파일 스펙 Table 3 | `[인수-웹, 규범]` |
| 마일스톤·게이트 분기표·열린 질문 | `plan.md` §A · §B · §C.0 · §D | — |
