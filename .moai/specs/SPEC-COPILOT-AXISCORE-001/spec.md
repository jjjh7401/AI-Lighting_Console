---
id: SPEC-COPILOT-AXISCORE-001
title: "축 점수 비교 가능성 — 정규화로 배제 규칙을 불필요하게 만든 뒤 삭제 (Axis Score Comparability)"
version: "0.2.0"
status: draft
created: 2026-08-05
updated: 2026-08-05
author: manager-spec
priority: P2
phase: "Phase 2 공간 인식 — 위상 경합 채점"
module: "server/spatial/topology.py, server/tests/test_topology.py"
lifecycle: spec-anchored
tags: "topology-scoring, axis-comparability, normalisation, scale-invariance, contention-rule, policy-removal, variation-sweep, groupgen-followup"
tier: S
related_specs: [SPEC-COPILOT-GROUPGEN-001, SPEC-COPILOT-SPATIAL-001, SPEC-COPILOT-WRITEGATE-001]
---

# SPEC-COPILOT-AXISCORE-001 — 축 점수 비교 가능성

> **이 SPEC이 갚는 부채**: GROUPGEN-001의 머지 전 리뷰가 `_compute_depth`의 공허성을 잡았고, **그 근본
> 원인은 정책으로 덮였다.** 저장소가 스스로 그렇게 적었다:
>
> > ⚠ **남는 질문(후속)**: 영성을 고쳐도 점수만으로는 depth 60 vs vertical 80이다. 이 배제 규칙이 없으면
> > 여전히 vertical이 이긴다 — 근본적으로 **축 간 점수 비교 가능성**이 미해결이다.
> > — `.moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md:804-805` · 동일 문장 `spec.md:44`
>
> 점수를 비교 가능하게 만드는 대신 **후보 하나를 경합에서 빼는 규칙**(`topology.py:469-470`)이 들어갔다.
> 본 SPEC은 순서를 되돌린다 — 점수를 비교 가능하게 만들고, **그 결과 규칙이 잉여임을 증명한 뒤 삭제한다.**
>
> **가설이 아니라 실측이다**: `three_rows_two_trims`에서 depth **60.00** 대 vertical **80.00**을
> 재현했고(`research.md` §3.1), 규칙을 오늘 그대로 지우면 전체 스위트가 **1 failed / 4715 passed**로
> 정확히 그 리그 1건에서 깨진다(`research.md` §5.1).
>
> **파이프라인의 위치**: `classify()` 내부의 **채점 단계 하나**를 고친다. 검출기 6종도, `TopologyResult`
> 형상도, `naming.py`도, 쓰기 경로도 건드리지 않는다. 이 모듈은 콘솔 무접촉이다(`tools.py:3464-3469`).

## A. 배경

### A.1 오늘의 점수는 축을 넘어 비교할 수 있는 물건이 아니다

네 축이 서로 다른 식으로 채점된다(`research.md` §2 전수표):

| 축 | 분자 | 분모 | 실질 단위 |
|---|---|---|---|
| `lateral` · `vertical` · `concentric` | `min_boundary_gap` (`topology.py:160`) | `max(within_spread, 0.05)` | 정렬 리그에서 **미터 / 0.05** |
| `depth_rows` | **`max_gap`** (`topology.py:204`) | 동일 | 동일 |
| `bilateral_pairs` | — | — | **쌍의 개수** (`topology.py:306`) |

원인은 넷이고 전부 실측했다(`research.md` §3):

1. **분모 하한이 비율을 원시 거리로 붕괴시킨다.** 완벽 정렬 리그(= 이 앱의 grid 프리셋이 직접 쓰는
   리그)에서 `within_spread == 0`이므로 분모가 상수 `0.05`로 고정되고, 점수는 `20 × 그 축의 미터`가 된다.
   무대의 깊이·폭·높이는 물리적 크기가 다르므로 **축을 넘어 미터를 비교하는 것 자체가 단위 오류**다.
2. **분자의 순서통계량이 depth만 다르다.** depth는 자신의 **최선** 경계(`max_gap`)로, 나머지 세 축은
   자신의 **최악** 경계(`min_boundary_gap`)로 채점된다.
3. **분할 품질 항이 없다.** 버킷 수도 버킷 크기도 점수에 들어가지 않는다. `m6_mirror_flat`에서 틀린
   해석(`concentric` `[2]×9`)이 옳은 해석(`lateral` `[9,9]`)보다 **27배** 높은 점수를 받는다(20.00 대 0.75).
4. **`bilateral`의 점수는 개수다.** 오늘은 `scored`에 들어가지 않아 무해하지만, 같은 이름의 필드에 전혀
   다른 척도가 담겨 있다는 사실이 "이 필드는 비교 가능하다"는 계약의 부재를 증명한다.

### A.2 결함은 이미 라이브다 — 규칙과 무관한 두 곳에서

- **스케일 의존**: `_golden_vertical_levels`의 z 좌표만 **1/10로 축소**하면 구조가 그대로인데 판정이
  `vertical_levels` → `lateral_split`으로 **뒤집힌다**(`research.md` §3.1 표 3행). 골든 코퍼스 안의
  리그다.
- **창립 오독의 생존**: 2겹 링 리그 `6@r=3.0 + 12@r=5.0` · `6@r=3.0 + 8@r=5.0`이 오늘 **`depth_rows`로
  오독된다**(`research.md` §5.3) — GROUPGEN이 존재하는 바로 그 결함이 코퍼스 바깥에서 살아 있다. 원인은
  §A.1의 2번과 3번이다.

### A.3 코퍼스의 판별력은 리그 1종이다 — 기록된 함정의 재현

배제 규칙을 오늘 그대로 지우면 **정확히 1건**이 깨진다
(`test_depth_rows_beats_a_vertical_reading_that_merges_two_rows`, `research.md` §5.1). 그런데 그 리그의
형상(행 수 × 열 수 × 트림 수 × y 피치 × z 갭)을 계통적으로 흔들면 **252 리그 중 126건(50.0%)**이
`vertical_levels`로 넘어간다(`research.md` §5.2). **골든 1종이 현상의 0.8%를 덮고 있다.**

이것은 이 저장소가 이미 대가를 치른 함정이다:

> 같은 결함을 **두 번** 놓쳤다. 첫 수정이 *증상이 나타난 리그*를 고정했을 뿐 *원인*을 고정하지 않았기
> 때문이다. 골든이 회귀를 막아주지만 **골든과 같은 형상만** 막아준다.
> — `GROUPGEN progress.md:778-779` (미러 아티팩트 강등이 여분 장비 1대로 재발한 사건)

따라서 본 SPEC의 AC는 **리그가 아니라 현상**에 걸린다(REQ-AXISCORE-012).

### A.4 배제와 동점 처리는 다른 물건이다

오늘도 `scored.sort`는 안정 정렬이므로 `contenders`의 삽입 순서(`topology.py:464-470`: depth · lateral ·
concentric · vertical)가 **이미 동점을 깨고 있다** — 다만 문서화되지 않은 우연이다. 본 SPEC이 도입하는
축 전순서는 **그 우연을 문면화한 것**이며, 오늘의 배제 규칙과 성질이 다르다:

| | 오늘의 배제 규칙 (`:469-470`) | 본 SPEC의 동점 전순서 |
|---|---|---|
| 발화 조건 | `depth`가 ≥2 버킷이면 **항상** | 두 점수가 **정확히 같을 때만** |
| 하는 일 | **더 높은 점수의 후보를 제거** — `three_rows_two_trims`에서 **80.00점 `vertical`을 빼서 60.00점 `depth`를 당선**시킨다 | **정확히 동점인 후보 중에서만 선택** — 순위 자체는 건드리지 않는다 |
| vertical이 더 높으면 | 그래도 진다 | **이긴다** — `_golden_vertical_levels`(`lateral` 0.250 대 `vertical` 0.333)에서 전순서는 **개입하지 않는다** |
| 오늘 이미 쓰이는가 | 명시적 정책 분기(`@MX:ANCHOR :442-462`) | **그렇다** — 안정 정렬 + `contenders` 삽입 순서(`topology.py:464-470`)가 이미 같은 순서로 동점을 깬다. 변경분은 **우연을 문면화한 것**뿐이다 |

요컨대 작동 구간이 다르다: 배제는 **점수가 다를 때** 승자를 뒤집고, 전순서는 **점수가 같을 때만**
발화한다. 전자를 지우고 후자를 남기는 것은 정책을 옮겨 적는 것이 아니라 **정책을 없애고 오늘의 우연을
문서화하는 것**이다.

> **결정 기록 (에이전트, 2026-08-05)** — 이 전순서가 배제 규칙의 **정당한 후계**임이 확정됐다
> (`plan.md` §D **D3**, ASSUMPTION-78 닫힘). 같은 성질 판단이 평면 격자의 `lateral` 기본값
> (§C.3 ASSUMPTION-77 · `plan.md` §D **D1**)에도 그대로 적용된다 — 그 기본값 역시 **동점에서만**
> 발화하며 더 높은 점수를 덮지 않는다. 덮게 만들면 배제 규칙을 좌우 방향으로 다시 세우는 것이라
> REQ-AXISCORE-008 위반이다.

## B. 요구 (GEARS)

### B.1 비교 가능성 — 점수가 만족해야 할 계약

- **REQ-AXISCORE-001** [Ubiquitous] — 각 축 점수 **shall** 무차원이며 **그 축 좌표의 균일 스케일 변환에
  불변**이다. 즉 어떤 축의 모든 좌표에 양의 상수 `k`를 곱해도 그 축의 점수와 `classify()`의 최종 선택이
  변하지 않는다. 이는 §A.1 원인 1을 닫는 기계 검증 가능한 불변식이며, 오늘은 `within_spread <= 0.05`
  구간에서 거짓이다(`research.md` §3.1).
- **REQ-AXISCORE-002** [Ubiquitous] — 모든 축의 점수 **shall** **동일한 순서통계량**으로 산출된다 —
  구체적으로 경계로 채택된 갭 중 **가장 약한 것**을 쓴다. `depth_rows`도 예외가 아니며,
  `analysis.gaps.max_gap`(`topology.py:204`) 사용은 폐기된다.
- **REQ-AXISCORE-003** [Ubiquitous] — 점수 **shall** 모든 축에 대해 **닫힌 공통 구간**에 놓이고, 축 간
  비교는 오직 그 구간을 통해서만 성립한다. 구간을 벗어나는 값·무한대·`NaN`은 산출되지 않는다.
- **REQ-AXISCORE-004** [Ubiquitous] — 점수 **shall** **분할 품질**을 반영한다: 같은 분리도라면, 최소
  버킷이 리그에서 차지하는 몫이 큰 분할이 더 높은 점수를 받는다. 이는 §A.1 원인 3을 닫으며, "18대를
  1~2대짜리 9조각으로 쪼갠 해석"이 "6+12로 쪼갠 해석"을 이기지 못하게 하는 항이다.
- **REQ-AXISCORE-005** [Event-driven] — **When** 두 축이 모두 확신 분할을 내고 정규화 점수가 **정확히
  같으면**, the `classify()` **shall** **문면에 기록된 축 전순서**로 해소하며, 그 전순서는 오늘 안정
  정렬이 암묵적으로 쓰고 있는 순서(`depth_rows` → `lateral_split` → `concentric` → `vertical_levels`,
  `topology.py:464-470`)와 일치한다.

### B.2 배제 규칙의 삭제 — 이 SPEC의 존재 이유

- **REQ-AXISCORE-006** [Ubiquitous] — the 구현 **shall** `topology.py:469-470`의
  `if not depth_partitions: contenders = (*contenders, (vertical, vertical_score))`와 그것이 의존하는
  `depth_partitions` 계산(`:463`), 그리고 해당 `@MX:ANCHOR`/`@MX:REASON` 블록(`:442-462`)을 **삭제**하고,
  `vertical_levels`를 **무조건** `contenders`에 넣는다.
- **REQ-AXISCORE-007** [Event-driven] — **When** 배제 규칙이 삭제된 상태로 위상 골든 코퍼스 전체를
  돌리면, the 스위트 **shall** 전부 GREEN이다. **이것이 본 SPEC의 1차 성공 판정이며**, 이것이 성립해야만
  정책이 잉여였음이 증명된다(`acceptance.md` AC-AXISCORE-001).
- **REQ-AXISCORE-008** [Unwanted] — the 구현 **shall not** 배제 규칙을 다른 형태로 대체한다 — 새로운
  후보 제거, 조건부 점수 0 설정, 축별 가중 상수, 축별 특례 분기는 모두 금지된다. 축 간 순위는 **단일
  정규화 식 + 동점 전순서** 둘로만 결정된다.

### B.3 보존 — 건드리지 않는 것

- **REQ-AXISCORE-009** [Unwanted] — the 구현 **shall not** `bilateral_pairs`를 `scored`에 넣는다.
  `.plan-contract.md` §2 D-Q10(*"신호만 보고 · 그룹 생성 안 함"*)은 유효하며 그 구조적 근거도 유효하다:
  `naming.py`의 공개 네이머 5종(`:48` · `:70` · `:115` · `:143` · `:182`)에 대칭용 어휘가 **없으므로**
  `bilateral_pairs`가 선택되면 제안 그룹이 0개가 된다. `@MX:ANCHOR` 블록(`topology.py:472-482`)은 문면
  그대로 유지된다.
- **REQ-AXISCORE-010** [Unwanted] — the 구현 **shall not** 미러 아티팩트 강등(`topology.py:405-441`)과
  `grid` 2축 단락(`:402-403`)의 동작·조건·발화 순서를 바꾼다. 둘 다 **점수 이전에** 결정되는 의미론적
  판단이며 본 SPEC의 범위 밖이다(§D).
- **REQ-AXISCORE-011** [Unwanted] — the 구현 **shall not** `server/spatial/rows.py`,
  `server/spatial/schema.py`, `server/spatial/naming.py`를 수정한다. `SpatialGapProfile`에
  `min_boundary_gap`이 없으므로(`schema.py:122-133`) `_compute_depth`는 경계 갭을 `analysis.rows`에서
  **국소 유도**한다(`research.md` §8).
- **REQ-AXISCORE-012** [Unwanted] — the 구현 **shall not** `SPATIAL_ROW_NOISE_SPAN`(`rows.py:61`)과
  `SPATIAL_ROW_GAP_RATIO`(`rows.py:80`)의 **값**을 바꾼다. 두 상수는 *버킷 경계를 어디서 자르는가*를
  결정하며, 본 SPEC은 *잘린 버킷을 어떻게 채점하는가*만 다룬다. 분할 자체가 바뀌면 측정 기준선이 사라진다.
- **REQ-AXISCORE-013** [Unwanted] — the 구현 **shall not** `TopologyResult` · `TopologyClassification`의
  필드·타입 불변식(`topology.py:75-90`)과 `candidates` 보고 내용을 바꾼다 — 경합에서 진 축도 오늘처럼
  전부 보고된다.
- **REQ-AXISCORE-014** [Unwanted] — the 구현 **shall not** 신규 런타임 의존을 추가한다(REQ-GROUPGEN-007
  계승). `math` · `statistics` 표준 라이브러리만 쓴다.
- **REQ-AXISCORE-015** [Ubiquitous] — the 결정성 **shall** 유지된다(REQ-GROUPGEN-002 계승): 같은 입력은
  같은 출력을, 입력 순서를 뒤집어도 같은 선택을 낸다.

### B.4 잠재 부채

- **REQ-AXISCORE-016** [Ubiquitous] — `_compute_bilateral`이 반환하는 점수 **shall** REQ-AXISCORE-003의
  공통 구간 위에 놓인다. 원시 쌍 개수(`topology.py:306`)는 폐기된다. `bilateral`은 계속 `scored` 밖에
  있으므로(REQ-AXISCORE-009) 판정에는 영향이 없으며, 이는 **미래에 누군가 그것을 경합에 되돌릴 때
  조용히 이기는 일을 막는** 조치다.

### B.5 검증 방식 — 함정에 대한 방어

- **REQ-AXISCORE-017** [Where] — **Where** AC가 축 판정을 고정하는 경우, the 그 AC **shall** 단일 리그가
  아니라 **매개변수 스윕**에 걸린다 — 최소한 픽스처 수 · 버킷 수 · 버킷 크기 · 축별 물리 갭을 각각
  변화시킨다. 근거는 실측이다: 오늘의 코퍼스는 배제 규칙 현상 252 리그 중 **1건**만 덮는다
  (`research.md` §5.2), 그리고 이 저장소는 같은 이유로 같은 결함을 두 번 놓쳤다(`progress.md:778-779`).
- **REQ-AXISCORE-018** [Ubiquitous] — 뮤테이션 대상 **shall** **정규화 식 자체**다 — 골든 픽스처가
  아니다. 구체적으로 (a) 분모 하한을 되살리기 (b) `depth` 분자를 `max_gap`으로 되돌리기 (c) 분할 품질
  항 제거 (d) 동점 전순서 제거 — 각각이 명명된 테스트를 RED로 만들어야 한다.
- **REQ-AXISCORE-019** [Ubiquitous] — the 구현 **shall** 판정이 바뀌는 리그를 **전수 열거**하고 각각에
  대해 새 판정이 옳은 이유를 문서화한다. 오늘 실측된 변경 후보는 세 무리다: 평면 격자 30/72
  (`research.md` §7.3) · 2겹 링 오독 정정 2건(§5.3) · `_golden_bilateral` 1건(§7.3).

## C. 환경 및 전제

### C.1 검증 가능성

| 항목 | 기계 검증 | 수단 |
|---|---|---|
| 배제 규칙 삭제 후 코퍼스 GREEN | **YES** | `pytest server/tests/test_topology.py …` — 1차 AC |
| 축 스케일 불변성 | **YES** | 좌표 ×k 변환 후 점수·선택 동일 단정 |
| 동일 순서통계량 | **YES** | 링 리그에서 depth 분자 실측 비교 |
| 공통 구간 | **YES** | 전 리그 전 축 점수의 범위 단정 |
| 분할 품질 | **YES** | `[1,2,2,…]` 대 `[6,12]` 순위 단정 |
| 252 리그 스윕 무회귀 | **YES** | 매개변수화 테스트 |
| 콘솔 무접촉 유지 | **YES** | 기존 아키텍처 테스트 |
| **평면 격자에서 어느 축이 맞는가** | **결정으로 닫힘** | ASSUMPTION-77 — `lateral` 기본값 (사용자 2026-08-05 · `plan.md` §D D1) |
| **동점 전순서가 배제 규칙의 정당한 후계인가** | **결정으로 닫힘** | ASSUMPTION-78 — 정당함 (에이전트 2026-08-05 · `plan.md` §D D3) |
| **새로 `concentric`이 된 링 2종이 옳은가** | **결정으로 닫힘** | ASSUMPTION-79 — `concentric` 확정 (사용자 2026-08-05 · `plan.md` §D D2) |
| 스윕 전수 상시 실행의 비용 | **YES · 실측 완료** | 288 리그 0.017초(0.06 ms/리그) · `plan.md` §D D4 — ASSUMPTION 없이 닫힘 |

### C.2 PRESERVE

- `server/spatial/rows.py` · `schema.py` · `naming.py` · `presets.py` · `sorting.py` ·
  `fixture_type.py` · `choreography.py` — **무변경**(REQ-AXISCORE-011).
- `server/groupgen/**` · `server/orchestrator/tools.py` — **무변경**. 소비 계약(`TopologyResult` 형상,
  `candidates` 보고)이 그대로이므로 접촉할 이유가 없다.
- `server/safety/**` · `server/measurement/**` — **무접촉**. 본 SPEC은 읽기 전용 모듈만 다루므로
  게이트·코퍼스와 교차하지 않는다.
- `topology.py`의 검출기 6종(`_compute_depth`의 **분자 산출**과 `_axis_buckets`의 **점수 산출**을 제외한
  버킷 분할 로직 일체) — **무변경**. 어떤 리그가 몇 개 버킷으로 갈리는지는 바뀌지 않는다.

### C.3 ASSUMPTION

- **ASSUMPTION-76 (정규화 가능성)** — 표준 라이브러리만으로, 결정적이고, 네 축 모두에 같은 식으로
  적용되는 정규화가 존재해 배제 규칙 없이도 고정된 19 리그 전부와 252 리그 스윕을 보존한다.
  **시뮬레이션으로 검증 · 트리 미반영**: 후보 N1이 고정 19 리그 **불일치 0**, 스윕 A **252/252 보존**,
  스윕 C에서 오독 **2건 정정**(`research.md` §7). NEGATIVE면 배제 규칙 삭제는 불가능하며 본 SPEC은
  **정규화만 착지시키고 규칙 삭제는 재개방**한다(그 경우에도 §A.2의 라이브 결함 2종은 닫힌다).
- **ASSUMPTION-77 (평면 격자 판정)** — y에 깊이가 없는 `cols × trims` 격자에서 `lateral`과 `vertical`은
  대칭적 가설이고, 정규화 후 판정이 30/72 리그에서 바뀐다(18건 `lateral`→`vertical`, 12건 반대 —
  `research.md` §7.3). 그 변경이 운영상 수용 가능하다. **결정됨 (사용자, 2026-08-05)**: 평면 격자의
  기본값은 **`lateral`(좌우)**이다 — 사람은 조명 버드를 "없어진 열"로 읽고 무대 언어가 좌우 중심이며,
  이 기본값은 간격 크기와 무관하게 안정적이다. 30건 판정 변경을 **그대로 수용**한다. 이 기본값은
  전순서의 `lateral_split > vertical_levels` 항으로 착지하며 **동점에서만** 발화한다 — 코퍼스가 고정하는
  `_golden_vertical_levels`는 점수로(0.250 대 0.333) 여전히 `vertical`이다. 상세: `plan.md` §D **D1**.
- **ASSUMPTION-78 (전순서의 정당성)** — "동점일 때 depth를 먼저 본다"가 "depth가 분할하면 vertical을
  경합에서 뺀다"의 정당한 후계다. 근거는 §A.4의 성질 차이와, 그 순서가 오늘 안정 정렬이 이미 쓰고 있는
  순서라는 사실이다. **결정됨 (에이전트, 2026-08-05)**: 정당하다 — 배제는 **더 높은 점수의 후보를
  제거**하고(80점 vertical → 60점 depth 당선) 전순서는 **정확히 동점인 후보 중에서만** 고른다. N1의
  전순서를 그대로 확정하며 정규화 항 흡수(= ASSUMPTION-76 재측정) 경로는 **취하지 않는다.**
  상세: `plan.md` §D **D3**.
- **ASSUMPTION-79 (링 오독 정정의 정당성)** — 오늘 `depth_rows`로 나오는 `6@3.0+8@5.0` ·
  `6@3.0+12@5.0`이 실제로는 `concentric`이 옳은 답이다. **부분 검증**: `_golden_concentric`(6@2+12@5)이
  같은 형상이고 코퍼스가 `concentric`으로 고정한다 — 반지름 간격만 다르다. **결정됨 (사용자,
  2026-08-05)**: `concentric`이 정답이고 오늘의 `depth_rows`는 오독이다. `low_confidence` 대안은
  채택하지 않는다. 이 형상은 이 SPEC 계열의 **창립 오독과 같은 형상**이므로 정규화의 정정은 부작용이
  아니라 **이득**으로 기록한다 — `acceptance.md` **AC-AXISCORE-006**이 고정하며, "NEGATIVE면
  `low_confidence` 기대로 다시 쓴다" 분기는 닫혔다. 상세: `plan.md` §D **D2**.
- **ASSUMPTION-80 (bilateral 척도 정렬)** — `_compute_bilateral`의 점수를 공통 구간으로 옮겨도
  `bilateral`이 `scored` 밖에 남아 있는 한 어떤 판정도 바뀌지 않는다. **기계 검증 가능 — M1 회귀로
  확인.** `bilateral_score`는 오늘 `classify()` 안에서 **읽히기만 하고 쓰이지 않는다**
  (`topology.py:397`, `scored` 구성에서 제외).

## D. 범위 밖 (Out of Scope)

### Out of Scope — `bilateral_pairs`가 신호로 남는 것
- `bilateral_pairs`를 `scored`에 되돌리는 일은 **본 SPEC이 명시적으로 금지한다**(REQ-AXISCORE-009).
  `.plan-contract.md` §2 D-Q10은 **확정된 설계 결정**이고 mutation-required로 고정돼 있다. 그 근거는
  점수가 아니라 구조다 — `naming.py`에 대칭 어휘가 없으므로 `bilateral_pairs`가 이기면 제안 그룹이 0개가
  되고, 운영자에게는 *"아무것도 못 찾았다"*로 읽힌다. 실제로 M6 stage 3에서 그렇게 났다
  (`topology.py:479-481`).
- 본 SPEC은 그것을 **부채로 취급하지 않으며**, 정규화 후에도 계속 작동하게 만들 책임을 진다. 점수 척도만
  공통 구간으로 옮긴다(REQ-AXISCORE-016) — 그것도 경합 복귀를 **쉽게** 하려는 게 아니라, 미래에 누군가
  되돌릴 때 **조용히 이기지 않게** 하려는 것이다.

### Out of Scope — 미러 아티팩트 강등 규칙
- `topology.py:405-441`의 `concentric` 강등은 **정규화로 대체할 수 없다.** 이것은 점수 문제가 아니라
  의미론적 붕괴 문제다: 리그가 y로 평평하면 `math.hypot(x, y)`가 대수적으로 `|x|`이므로 반지름 축이
  독립 가설이 **아니다**. 후보 N1에서도 `m6_centre`처럼 다른 확신 축이 없는 리그는 강등 없이는
  `concentric`이 이긴다.
- 그러므로 본 SPEC은 이 규칙을 **유지하며 작동을 보증한다**(REQ-AXISCORE-010). 정규화는 그 규칙을
  대체하지 못한다 — 실측: `m6_mirror_flat`에서 강등을 끄면 후보 N1도 `concentric` **0.111**이
  `lateral` **0.094**를 이긴다(오늘은 20.00 대 0.75). 격차가 27배에서 1.18배로 줄 뿐 **부호는
  바뀌지 않는다.** `m6_centre`는 더 분명하다: `lateral`이 비확신이라 강등 없이는 `concentric`
  0.0049(`[1,18]`)가 유일한 양수 후보로 이긴다.

### Out of Scope — `grid` 2축 단락
- `depth`와 `lateral`이 둘 다 ≥2 버킷이면 `grid`가 무조건 이기는 계약(`topology.py:402-403`, D-Q2)은
  **점수 이전에** 결정되며 본 SPEC이 접촉하지 않는다. 스윕 C의 81 리그 중 50건이 이 단락으로 처리되고,
  후보 N1에서도 동일하다(`research.md` §7.2).

### Out of Scope — 버킷 분할 알고리즘과 두 상수
- `SPATIAL_ROW_NOISE_SPAN` · `SPATIAL_ROW_GAP_RATIO`의 값 변경과 갭 클러스터링 방식 교체는 범위 밖이다
  (REQ-AXISCORE-012). *어디서 자르는가*는 그대로 두고 *잘린 것을 어떻게 채점하는가*만 바꾼다 — 그래야
  본 SPEC의 측정 기준선(`research.md` §4.2 리그별 버킷 형상)이 전후로 유지된다.

### Out of Scope — 운영자 대면 어휘와 UI
- 선택 축이 바뀌면 `classify_arrangement_topology`가 제안하는 그룹 이름이 바뀐다
  (`tools.py:3470-3495`). 어휘 자체의 개명·UI 표기·설명 문구는 범위 밖이다. 본 SPEC은 **어느 축이
  선택되는가**까지만 책임진다.

### Out of Scope — 다른 후속 SPEC
- `SPEC-COPILOT-TRUNCATE-001`(절단 고지)과 정렬 어휘 개명은 파일 무교차이며 병렬 가능하다.

## E. 성공 기준

| 기준 | 확인 수단 | 성격 |
|---|---|---|
| **배제 규칙(`:463`,`:469-470`) 삭제 후 위상 코퍼스 전부 GREEN** | `pytest` 60 테스트 | **1차 판정** |
| 축 좌표 ×k 변환에 점수·선택 불변 | 매개변수화 단정 | 구조 |
| 네 축 전부 동일 순서통계량 | depth 분자 실측 단정 | 구조 |
| 전 축 점수가 닫힌 공통 구간 안 | 전 리그 범위 단정 | 구조 |
| 252 리그 행×트림 스윕 무회귀 — z 판독이 깊이 행을 융합해 이기는 리그 **0건** | 매개변수화 스윕 | **현상 결속** |
| **2겹 링 2종(`6@3.0+8@5.0` · `6@3.0+12@5.0`)이 `concentric`** — D2가 확정한 **잠재 결함 수정** | `AC-AXISCORE-006` | **결함 정정** |
| 스윕 A(252) · B(72) · C(81) **전수가 상시 테스트** · `slow` 마커 없음 (D4) | 매개변수화 스윕 · 실측 0.03초 | **현상 결속** |
| 평면 격자에서 동점 시 `lateral` 승 (D1) · 스윕 B가 `zgap`·`xpit` 절대 크기에 불변 | `AC-AXISCORE-007` 스윕 B | **현상 결속** |
| 평면 격자·링 스윕에서 판정 변경 리그 전수 열거·정당화 | 문서 + 스윕 | 절차 |
| 정규화 식 4항목 뮤테이션 각각 RED | 뮤테이션 실측 | **판별력** |
| `bilateral_pairs` 미선택 · `candidates` 보고 유지 | 기존 테스트 | 회귀 |
| 미러 아티팩트 강등 · `grid` 단락 무변경 | 기존 테스트 | 회귀 |
| `rows.py`·`schema.py`·`naming.py` byte-diff 0 | diff | 회귀 |
| 결정성 · 순서 무관성 | 기존 테스트 | 회귀 |
| 전체 스위트 기준선 유지(`4716 passed · 7 skipped` + 신규) | `pytest` | 회귀 |
