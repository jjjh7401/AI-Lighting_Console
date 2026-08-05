# 인수 조사 — 축 점수 비교 가능성

base `origin/main` = `b1a630e` · worktree `axiscore` · branch `spec/axiscore-001` · 2026-08-05

이 문서는 **실측 기록**이다. 모든 숫자는 이 워크트리에서 직접 돌려 얻었고, 추정은 `[INFERENCE]`로 표기한다.
측정에 쓴 프로브는 `server/` 밖(`/tmp`)에서 실행했으며, 배제 규칙 제거 측정만 소스를 **일시 수정 후 되돌렸다**
(§6 절차 기록).

---

## 1. 이 SPEC이 존재하는 이유 — 저장소가 스스로 남긴 미해결 항목

GROUPGEN-001의 머지 전 리뷰가 `_compute_depth`의 `median_gap > 0` 공허성을 잡았고, 그 수정과 함께
**배제 규칙**이 들어갔다. 그 자리에서 남긴 기록이 본 SPEC의 출발점이다:

> ⚠ **남는 질문(후속)**: 영성을 고쳐도 점수만으로는 depth 60 vs vertical 80이다. 이 배제 규칙이 없으면
> 여전히 vertical이 이긴다 — 근본적으로 **축 간 점수 비교 가능성**이 미해결이다.
>
> — `.moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md:804-805` (동일 문장이 `spec.md:44` 결정표에도 있다)

즉 **점수를 비교 가능하게 만드는 대신 후보 하나를 경합에서 빼는 정책이 들어갔다.** 본 SPEC은 그 순서를
되돌린다: 점수를 비교 가능하게 만들고, 그 결과 배제 규칙이 **불필요해졌음을 증명한 뒤** 삭제한다.

`depth 60 vs vertical 80`은 본 세션에서 재현했다(§3.1 표, `three_rows_two_trims` 행: **depth 60.00 ·
vertical 80.00**).

---

## 2. 점수를 만드는 함수들 — 전수 (file:line)

| 축 | 산출 함수 | 점수 식 | 위치 |
|---|---|---|---|
| `lateral_split` | `_compute_lateral` → `_axis_buckets(f.x)` | `min_boundary_gap / max(within_spread, 0.05)` | `topology.py:161` · 호출 `:213` |
| `vertical_levels` | `_compute_vertical` → `_axis_buckets(f.z)` | 동일 | `topology.py:161` · 호출 `:230` |
| `concentric` | `_compute_concentric` → `_axis_buckets(hypot(x,y))` | 동일 | `topology.py:161` · 호출 `:246` |
| `depth_rows` | `_compute_depth` (rows.py 경유) | **`analysis.gaps.max_gap` / `max(within_spread, 0.05)`** | `topology.py:204` |
| `bilateral_pairs` | `_compute_bilateral` | **`float(len(pairs))`** — 순수 개수 | `topology.py:306` |
| `grid` | `_compute_grid` | **점수 없음** — 경합 이전에 단락 | `topology.py:318-339` · 단락 `:402-403` |

상수: `SPATIAL_ROW_NOISE_SPAN = 0.05` (`rows.py:61`, "5 cm 리깅 공차 · 의도적으로 **절대** 하한"),
`SPATIAL_ROW_GAP_RATIO = 4.0` (`rows.py:80`).

경합 지점: `topology.py:464-470`이 `contenders`를 만들고, `:483-487`이 `scored`로 거르고,
`:495-496`이 `scored.sort(key=score, reverse=True)` 후 `[0]`을 고른다.

---

## 3. 왜 비교 불가능한가 — 근본 원인 4건

### 3.1 원인 1 (지배적) — 분모 하한이 비율을 **원시 절대 거리**로 붕괴시킨다

`score = boundary_gap / max(within_spread, 0.05)`. 여기서 `within_spread`가 **0이 되는 리그가 정상**이다 —
`rows.py:66-68`이 스스로 적는다: *"in a real multi-row rig the fixtures of a row SHARE a depth, so
within-row gaps collapse to zero"*. 그러면 분모가 상수 `0.05`로 고정되고 점수는

```
score = gap / 0.05 = 20 × (그 축에서 잰 미터)
```

**차원이 없는 비율이 아니라 "5 cm 단위로 센 갭 길이"** 다. 축마다 물리적 스케일이 다르므로(무대는 깊이
10~20 m · 폭 10~20 m · 트림 4~10 m) **미터끼리 축을 넘어 비교하는 것 자체가 단위 오류**다.

실측 해부(축별 분자/분모, 본 세션):

```
=== three_rows_two_trims ===
  depth   numer=max_gap       3.000  median_gap=  0.000  denom=max(within_spread=0.000,0.05)  ->    60.00   rows=3
  vertic  numer=min_bnd_gap   4.000  median_gap=  0.000  denom=max(within_spread=0.000,0.05)  ->    80.00   buckets=2
=== golden_concentric ===
  depth   numer=max_gap       1.830  median_gap=  0.000  denom=max(within_spread=0.000,0.05)  ->    36.60   rows=9
  concen  numer=min_bnd_gap   3.000  median_gap=  0.000  denom=max(within_spread=0.000,0.05)  ->    60.00   buckets=2
=== m6_mirror_flat ===
  lateral numer=min_bnd_gap   6.000  median_gap=  1.000  denom=max(within_spread=8.000,0.05)  ->     0.75   buckets=2
  concen  numer=min_bnd_gap   1.000  median_gap=  0.000  denom=max(within_spread=0.000,0.05)  ->    20.00   buckets=9
```

`three_rows_two_trims`에서 **y 행 간격 3 m 대 z 트림 간격 4 m**를 그대로 비교해 60 대 80이 나온다.
`m6_mirror_flat`에서는 반대로 `within_spread=8.000`인 `lateral`만 진짜 비율(0.75)로 계산되고,
`within_spread=0`인 `concentric`은 원시 거리(20.00)로 계산되어 **같은 리그 안에서 두 축이 서로 다른
척도로 채점된다** — 27배 차이가 구조가 아니라 분모 종류에서 나온다.

**결정적 반례 — 같은 리그, 축 하나의 단위만 바꾸면 판정이 뒤집힌다** (본 세션 실측):

| 리그 / 변환 | raw depth | raw vertical | **오늘의 판정** | N1 판정 |
|---|---|---|---|---|
| `golden_vertical_levels` ×1 | 0.00 | 60.00 | `vertical_levels` | `vertical_levels` |
| `golden_vertical_levels` **z ×10** | 0.00 | 600.00 | `vertical_levels` | `vertical_levels` |
| `golden_vertical_levels` **z ×0.1** | 0.00 | **6.00** | **`lateral_split`** ⚠ | `vertical_levels` |
| `three_rows_two_trims` z ×10 | 60.00 | **800.00** | `depth_rows`(배제 규칙 덕) | `depth_rows` |
| `three_rows_two_trims` ALL ×100 | 6000.00 | 8000.00 | `depth_rows`(배제 규칙 덕) | `depth_rows` |

3행이 핵심이다: **골든 코퍼스 안의 리그가, 구조는 그대로인 채 z 좌표만 1/10로 축소되면 다른 위상으로
분류된다.** 오늘의 점수는 `within_spread <= 0.05`인 순간 스케일 불변성을 잃는다. (`within_spread > 0.05`
구간에서는 분자·분모가 함께 스케일되므로 불변이다 — 그래서 결함이 "항상"이 아니라 "정렬된 리그에서만"
나타나고, 정렬된 리그가 곧 이 앱이 직접 쓰는 리그다: `progress.md:790-792`.)

### 3.2 원인 2 — 분자가 축마다 **다른 순서통계량**이다

- `_axis_buckets` (`topology.py:160`): `min_boundary_gap` = 경계 갭 중 **최소** (가장 약한 경계)
- `_compute_depth` (`topology.py:204`): `analysis.gaps.max_gap` = y 수열 전체 갭 중 **최대**
  (경계로 채택된 갭에 국한되지도 않는다)

같은 데이터에서 `max_gap >= min_boundary_gap`이 항상 성립하므로 **depth는 자신의 최선 경계로, 나머지 세
축은 자신의 최악 경계로 채점된다.** 실측 영향(본 세션, `_compute_depth` 분자만 `min_boundary_gap`으로
바꿔 계산):

| 리그 | depth 분자 = `max_gap` | depth 분자 = `min_boundary_gap` |
|---|---|---|
| `golden_concentric` (창립 오독 리그) | 1.830 → 점수 **36.60** | 0.670 → 점수 **13.40** |
| `rings 6@3.0 + 12@5.0` | 2.500 → 점수 **50.00** (오늘 `depth_rows` 승) | **0.098** → 점수 **1.96** |
| `rings 6@3.0 + 8@5.0` | 2.598 → 점수 **51.96** (오늘 `depth_rows` 승) | **0.937** → 점수 **18.75** |

`rings 6@3.0 + 12@5.0`은 오늘 **`depth_rows`로 오독된다**(§5.3). 원인 2가 그 오독의 절반이다.

### 3.3 원인 3 — 버킷 수·버킷 크기가 점수에 **전혀** 들어가지 않는다

점수는 갭 하나와 스프레드 하나만 본다. 그래서 "18대를 2대짜리 9링으로 쪼갠 해석"과 "18대를 6+12로 쪼갠
해석"이 **분할 품질 항 없이** 갭 크기만으로 겨룬다. 실측:

| 리그 | 축 | 버킷 형상 | 오늘 점수 |
|---|---|---|---|
| `golden_concentric` | depth | `[1,2,2,2,4,2,2,2,1]` (9행 — 링의 y 투영 artefact) | 36.60 |
| `golden_concentric` | concentric | `[6,12]` (진짜 구조) | 60.00 |
| `m6_mirror_flat` | concentric | `[2]×9` (|x| 접힘) | 20.00 |
| `m6_mirror_flat` | lateral | `[9,9]` (진짜 구조) | **0.75** |

`m6_mirror_flat` 행이 보여주듯 오늘은 **틀린 해석이 27배 높은 점수를 받는다.** 이것이 미러 아티팩트 강등
규칙(`topology.py:405-441`)이 존재해야 했던 이유이기도 하다 — 그 규칙은 의미론적 붕괴(hypot→|x|)를
막는 별개 사안이라 본 SPEC의 범위 밖이지만(§spec.md D), **점수가 분할 품질을 못 보는 것**은 본 SPEC의
소관이다.

### 3.4 원인 4 (잠재) — `bilateral_pairs`의 점수는 **개수**다

`topology.py:306` `score = float(len(pairs))`. 갭 비율도 정규화도 아닌 **쌍의 개수**. 오늘은 `scored`에
들어가지 않으므로(`:483-487`, D-Q10) 무해하지만, `score`라는 같은 이름의 필드에 **전혀 다른 척도**가
담겨 있다는 사실 자체가 "이 필드는 비교 가능하다"는 계약이 없음을 증명한다. 실측: `golden_grid`에서
bilateral 15.00 · lateral 20.00 — 우연히 순서가 맞을 뿐이고, 큰 리그에서는 아무 관계가 없다.

---

## 4. 골든 코퍼스 전수 목록

### 4.1 파일별 테스트 수

| 파일 | 테스트 | 축 판정을 고정하는 단정 |
|---|---|---|
| `server/tests/test_topology.py` | **48** | `.kind ==` 계열 24개소 |
| `server/tests/test_topology_naming_seam.py` | **12** | `grid_3x10`(`:53`) · `two_ring_concentric`(`:47`) 2 리그 |
| `server/tests/test_groupgen_tools.py` | (툴 경로) | `:173` `payload["topology"]["selected"]["kind"] == "lateral_split"` — `_LATERAL_FIXTURES`(`:88-93`) |
| `server/tests/test_spatial_analysis.py` | — | **rows.py 전용**. `topology.classify`를 임포트하지 않는다(§4.3) |
| `server/tests/test_naming.py` | — | `TopologyResult` 형상을 **로컬 스텁**으로 재선언(`:5-7`) — topology.py 비의존 |

합계 **60개 topology 테스트**. 축 선택이 걸린 리그는 다음 19종이다.

### 4.2 리그 인벤토리 — 기대 축과 오늘의 점수 (본 세션 실측)

| # | 리그 | 정의 위치 | 기대 축 | depth | lateral | concen | vertic | bilat |
|---|---|---|---|---|---|---|---|---|
| 1 | `_golden_bar` | `test_topology.py:39` | `depth_rows` (1행) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 2 | `_golden_grid` 3×10 | `:49` | `grid` | 60.00 | 20.00 | 2.20 | 0.00 | 15.00 |
| 3 | `_golden_concentric` 6@2+12@5 | `:61` | `concentric` `[6,12]` | 36.60 | 0.00 | **60.00** | 0.00 | 8.00 |
| 4 | `_golden_lateral_split` | `:78` | `lateral_split` `[4,4]` | 0.00 | **11.11** | 6.00 | 0.00 | 4.00 |
| 5 | `_golden_vertical_levels` | `:85` | `vertical_levels` `[4,4,4]` | 0.00 | 10.00 | 10.00 | **60.00** | 0.00 |
| 6 | `_golden_irregular` | `:96` | `None` | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 7 | `_golden_all_origin` | `:110` | `None` | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 8 | `_golden_bilateral` | `:116` | **비고정** (오늘 `concentric`) | 10.00 | 0.00 | 17.36 | 0.00 | 5.00 |
| 9 | `_MIRRORED_LEFT_RIGHT` 평면 | `:384` | `lateral_split` `[9,9]` | 0.00 | **0.75** | 20.00 | 0.00 | 9.00 |
| 10 | +여분 x=-3 | `:485` | `lateral_split` `[10,9]` | 0.00 | 0.75 | 20.00 | 0.00 | 0.00 |
| 11 | +여분 x=11 | `:533` | `!= concentric` | 0.00 | 0.75 | 20.00 | 0.00 | 0.00 |
| 12 | +중앙 x=0 | `:519` | `depth_rows` | 0.00 | 0.00 | 0.38 | 0.00 | 9.00 |
| 13 | `mirror-4x2-dup` | `:535` | `!= concentric` | 0.00 | 0.00 | 20.00 | 0.00 | 0.00 |
| 14 | `mirror-5x2-dup` | `:536` | `!= concentric` | 0.00 | 0.00 | 40.00 | 0.00 | 0.00 |
| 15 | `mirror-gapped-dup` | `:537` | `!= concentric` | 0.00 | 0.00 | 20.00 | 0.00 | 0.00 |
| 16 | `_electrics_three_bars` | `:558` | `depth_rows` `[5,5,5]` | **60.00** | 0.00 | 0.00 | 30.00 | 0.00 |
| 17 | **`_three_rows_two_trims`** | `:575` | `depth_rows` `[5,5,5]` | **60.00** | 0.00 | 0.00 | **80.00** | 0.00 |
| 18 | 3×10 tiered grid | `:690` | `grid` | 60.00 | 20.00 | 2.20 | 60.00 | 15.00 |
| 19 | `_LATERAL_FIXTURES` (툴) | `test_groupgen_tools.py:88` | `lateral_split` | 0.00 (`kind=None`) | **8.00** | 0.00 (`kind=None`) | 0.00 | — |

**#17이 유일하게 배제 규칙에 의존한다** (depth 60 < vertical 80). 나머지 18종은 규칙과 무관하게 오늘의
판정이 나온다 — §5.1이 이를 전수로 확인했다.

### 4.3 `test_spatial_analysis.py`는 코퍼스가 아니다

`grep`으로 확인: 이 파일은 `server.spatial.topology`를 **임포트하지 않는다**. `rows.py`의 행 검출과 정렬
어휘만 다룬다(`:6-10` docstring). 축 선택을 고정하는 단정은 0건이다. 과제 지시가 이 파일을 지목했으므로
명시적으로 기록한다: **여기에는 축 경합 픽스처가 없다.**

---

## 5. 배제 규칙을 **오늘 그대로** 제거하면 무슨 일이 일어나는가

### 5.1 전체 스위트 (실측 · 소스 일시 수정 후 되돌림)

`topology.py:469-470`의 두 줄을 무조건 추가로 바꾼 뒤 `uv run --frozen pytest -q`:

```
1 failed, 4715 passed, 7 skipped, 1 warning in 97.56s
FAILED server/tests/test_topology.py::test_depth_rows_beats_a_vertical_reading_that_merges_two_rows
  AssertionError: assert 'vertical_levels' == 'depth_rows'
```

기준선은 `4716 passed · 7 skipped`(`GROUPGEN progress.md:850`과 일치). **정확히 1건**이 깨지고, 그것은
리그 #17이다. GROUPGEN이 기록한 뮤테이션 실측(*"깊이 우선 제거 → 1 failed"*, `progress.md:855`)과 일치한다.

즉 **오늘 코퍼스가 이 규칙에 대해 갖는 판별력은 리그 1종·테스트 1건뿐이다.**

### 5.2 그 1건이 현상 전체가 아니다 — 변형 스윕 252 리그

리그 #17의 형상(행 수 × 열 수 × 트림 수 × y 피치 × z 갭)을 계통적으로 흔들었다
(`rows∈{2,3,4,5} × cols∈{3,5,8} × trims∈{2,3} × ypitch∈{1,3,6} × zgap∈{0.5,2,4,10}`, `trims<=rows`):

| 측정 | 결과 |
|---|---|
| 리그 수 | **252** |
| 규칙을 오늘 그대로 제거했을 때 판정이 바뀌는 리그 | **126 / 252 (50.0%)** — 전부 `depth_rows` → `vertical_levels` |
| 그중 코퍼스가 잡는 것 | **1** (리그 #17) |

**골든 1종이 현상의 0.8%를 덮고 있다.** 이것이 저장소가 기록한 함정의 정확한 재현이다:

> 같은 결함을 **두 번** 놓쳤다. 첫 수정이 *증상이 나타난 리그*를 고정했을 뿐 *원인*을 고정하지 않았기
> 때문이다. 골든이 회귀를 막아주지만 **골든과 같은 형상만** 막아준다.
> — `GROUPGEN progress.md:778-779`

### 5.3 규칙과 무관한 두 스윕 — 배제 규칙은 여기서 아무것도 하지 않는다

| 스윕 | 리그 | 규칙 제거로 판정이 바뀌는 리그 |
|---|---|---|
| B: 평면(y 무깊이) 격자 `cols×trims`, `zgap`·`xpit` 변형 | 72 | **0** (depth가 1버킷이라 규칙 자체가 발화하지 않는다) |
| C: 2겹 링 `ni@ri + no@ro` 변형 | 81 | **0** |

스윕 C에서 **오늘 이미 오독하는 리그 2종을 발견했다**(배제 규칙과 무관한 별개 잠재 결함):

```
rings 6@3.0 + 8@5.0   n=14  today -> depth_rows  raw: depth=51.96 concen=40.00
                                    depth buckets=[1,2,2,4,2,2,1]   rings=[6,8]
rings 6@3.0 + 12@5.0  n=18  today -> depth_rows  raw: depth=50.00 concen=40.00
                                    depth buckets=[1,2,2,2,4,2,2,2,1] rings=[6,12]
```

**이 SPEC의 창립 오독(2겹 링을 y 행으로 읽음)이 골든 코퍼스 바깥에서 여전히 살아 있다.** 원인은 §3.2
(depth가 `max_gap`으로 채점됨)와 §3.3(분할 품질 항 없음)이다. 코퍼스의 `_golden_concentric`(6@2+12@5)은
반지름 간격이 3.0으로 커서 우연히 통과할 뿐이다.

**정답 — 결정됨(사용자, 2026-08-05)**: 이 두 리그의 옳은 판정은 **`concentric`**이고 오늘의
`depth_rows`(버킷 `[1,2,2,4,2,2,1]` · `[1,2,2,2,4,2,2,2,1]`)는 **오독**이다(`plan.md` §D **D2**).
*"두 링이 너무 가까우니 `low_confidence`가 정직한 답 아닌가"* 라는 대안은 **채택되지 않았다** — 이
형상이 이 SPEC 계열의 창립 오독과 같은 형상이므로, 정규화가 이를 고치는 것은 부작용이 아니라 **이득**
으로 기록한다. 따라서 §7.2 스윕 C의 "차이 2건"은 회귀가 아니라 **본 SPEC이 인도하는 잠재 결함 수정**
이며, `acceptance.md` **AC-AXISCORE-006**이 그것을 고정한다.

---

## 6. 측정 절차 기록 (재현 가능성)

- 점수·해부·스윕 프로브는 전부 `/tmp` 아래 스크립트로 실행했다 — `server/` 무접촉.
- §5.1만 `server/spatial/topology.py:469-470`을 일시 치환해 측정했고, 측정 직후
  `git checkout -- server/spatial/topology.py`로 되돌렸다. 최종 상태 `git status --porcelain` 공백 확인.
- 전체 스위트 1회(97.56s)만 돌렸다.

---

## 7. 후보 정규화 N1 — 실현 가능성 실측

본 SPEC의 1차 인수 기준(배제 규칙 제거 + 코퍼스 그린)이 **달성 가능한지**를 먼저 확인해야 한다. 아래는
구현안이 아니라 **가능성 증거**다. 최종 식은 계획 단계에서 확정한다(`plan.md` §B).

```
k = 버킷 수, n = 픽스처 수
k < 2                  -> score = 0.0                       (아무것도 분할하지 않음)
sep  = min_boundary_gap / max(max_within_bucket_span, 0.05)  (모든 축 동일 순서통계량 — 원인 2 해소)
s    = min(sep / SPATIAL_ROW_GAP_RATIO, 1.0)                 (검출 임계로 포화 — 원인 1 해소)
score = s × (min_bucket_size / n)                            (분할 품질 — 원인 3 해소), 범위 [0, 1]
동점  -> 문서화된 축 전순서: depth > lateral > concentric > vertical
```

축 전순서는 **새 정책이 아니다**: 오늘도 `scored.sort`가 안정 정렬이므로 `contenders` 삽입 순서
(`topology.py:464-470`: depth, lateral, concentric, vertical)가 이미 동점을 그렇게 깨고 있다.
차이는 **문서화 여부와, 동점일 때만 발화한다는 점**이다 — 후보를 빼지 않는다.

### 7.1 고정된 19 리그 — 전수 통과

배제 규칙을 **제거한 채** N1로 채점한 결과:

```
mismatches vs pins: 0    (19 리그 전수)
```

주요 행:

| 리그 | 오늘 | N1(규칙 제거) | N1 점수 d / l / c / v |
|---|---|---|---|
| `_golden_concentric` | `concentric` | `concentric` | 0.056 / 0.000 / **0.333** / 0.000 |
| `_golden_vertical_levels` | `vertical_levels` | `vertical_levels` | 0.000 / 0.250 / 0.000 / **0.333** |
| `_electrics_three_bars` | `depth_rows` | `depth_rows` | **0.333** / 0 / 0 / **0.333** → 동점, 전순서 |
| **`_three_rows_two_trims`** | `depth_rows` | **`depth_rows`** | **0.333** / 0 / 0 / **0.333** → 동점, 전순서 |
| `m6_mirror_flat` | `lateral_split` | `lateral_split` | 0.000 / **0.094** / 0.000 / 0.000 |
| `_LATERAL_FIXTURES` (툴) | `lateral_split` | `lateral_split` | 0.000 / **0.500** / 0 / 0 |

**리그 #17이 60 대 80(vertical 승)에서 0.333 대 0.333(동점)으로 바뀐다.** 두 분할 모두 완벽 분리이고
최소 버킷도 같은 몫(5/15)이므로 **숫자상 진짜로 대등하다** — 억누른 선호가 아니라 실제 동점이다.
`[INFERENCE]` 이것이 "정책을 옮긴 것"이 아닌 이유: 오늘의 규칙은 **80점짜리 후보를 60점짜리 때문에
제거**하지만, N1의 전순서는 **동점일 때만** 발화하고 vertical이 더 높으면 vertical이 이긴다.

### 7.2 변형 스윕 — 현상에 붙는가

| 스윕 | 리그 | 오늘(규칙 있음) == N1(규칙 제거) | 비고 |
|---|---|---|---|
| A (행×트림) | 252 | **252 / 252** | 규칙 없이도 z가 행을 융합하는 리그 **0건** (오늘 규칙 제거 시 126건) |
| C (2겹 링) | 81 | 79 / 81 | 차이 2건은 **N1이 §5.3의 오독을 고치는 쪽** (`depth_rows` → `concentric`) |
| B (평면 격자) | 72 | 42 / 72 | **30건 판정 변경** — 아래 §7.3 |

스윕 A의 252/252는 y 피치 1~6 m와 z 갭 0.5~10 m를 교차한 결과다. 즉 **물리적 갭 크기가 판정에 영향을
주지 않는다**는 것이 그 표의 내용이다(§3.1의 단위 오류 해소).

스윕 C의 개선 2건:

```
rings 6@3.0 + 8@5.0   today depth_rows -> N1 concentric   (n1: depth=0.0714 concen=0.4286)
rings 6@3.0 + 12@5.0  today depth_rows -> N1 concentric   (n1: depth=0.0272 concen=0.3333)
```

### 7.3 정직한 부작용 — 평면 격자 30 / 72 판정 변경 (결정 완료)

y에 깊이가 없는 `cols × trims` 격자에서 `lateral`과 `vertical`은 **대칭적 가설**이다. 오늘은
"물리적으로 갭이 큰 축"이 이기고, 그래서 같은 리그도 `zgap`을 바꾸면 판정이 뒤집힌다(§3.1 표 3행).
N1은 "최소 버킷 몫이 큰 쪽, 그다음 전순서"로 이긴다.

```
SWEEP B flip directions: {('lateral_split','vertical_levels'): 18, ('vertical_levels','lateral_split'): 12}
```

**이 30건 중 코퍼스가 고정하는 것은 `_golden_vertical_levels` 1종뿐이고 N1은 그것을 맞힌다**(0.250 대
0.333으로 vertical 승 — 전순서 개입 없음).

**나머지 29건의 정답 — 결정됨(사용자, 2026-08-05)**: 코퍼스가 말해주는 답은 없었고, 조사 시점에는
*"사람 결정이 필요하다"*로 남겨 두었다. 그 결정이 내려졌다 — **평면 격자의 기본값은 `lateral`(좌우)**
이다(`plan.md` §D **D1**). 근거는 도메인이다: 사람은 조명 버드를 기본적으로 **"없어진 열"**로 읽고,
무대 언어("오른쪽부터 웨이브")가 좌우 중심이며, 이 기본값은 **간격 크기와 무관하게 안정적**이라 §3.1의
단위 오류를 되불러오지 않는다.

이 결정이 위 측정에 대해 뜻하는 것:

| 항목 | 결정 전 | 결정 후 |
|---|---|---|
| 스윕 B 72 리그 중 판정 변경 | **30건**(측정값) | **30건 — 그대로 수용**. 감축도 예외도 없다 |
| 그중 코퍼스가 고정하는 1건 | `_golden_vertical_levels` → `vertical` | **변동 없음** — 점수로(0.250 대 0.333) vertical이 이기고, `lateral` 기본값은 **동점에서만** 발화하므로 개입하지 않는다 |
| 나머지 **29건** | *정답 없음 · 사람 결정 대기* | **정답 있음** — N1 전순서(`… > lateral_split > … > vertical_levels`)의 `lateral` 우선이 그 답이고, 각 리그는 REQ-AXISCORE-019에 따라 M5에서 전후 판정과 함께 전수 열거된다 |
| 18건 `lateral`→`vertical` 방향 | 방향의 정당성 미확정 | **점수로 갈린 리그이며 그대로 유효하다.** `lateral` 우선은 더 높은 점수를 덮지 않는다 — 덮게 만들면 배제 규칙을 좌우로 뒤집어 다시 세우는 것이라 REQ-AXISCORE-008 위반이고 `_golden_vertical_levels`가 RED가 된다 |

즉 이 절의 숫자는 **하나도 바뀌지 않고**, 바뀐 것은 그 30건이 *"미결 부작용"*이 아니라 **결정된 동작**
이라는 지위다. `acceptance.md` AC-AXISCORE-007 스윕 B의 기대값도 그에 따라 "일관성만 단정"에서
"일관성 + 동점 시 `lateral`"로 승격됐다.

또 하나: `_golden_bilateral`(리그 #8, **고정 없음**)이 오늘 `concentric`에서 N1 `depth_rows`로 바뀐다
— depth 0.200 대 concentric 0.200 **정확한 동점**을 전순서가 깬 결과다. 이 전순서의 정당성 역시
`plan.md` §D **D3**에서 결정됐다(에이전트, 2026-08-05).

---

## 8. 구현 제약 (실측)

- `SpatialGapProfile`(`server/spatial/schema.py:122-133`)은 `max_gap` · `median_gap` ·
  `split_threshold`만 담는다. **`min_boundary_gap`이 없다.** 따라서 원인 2를 고치려면
  `_compute_depth`가 `analysis.rows`에서 경계 갭을 **국소적으로 유도**해야 하며, 그러면
  `rows.py`·`schema.py`는 **무변경**으로 남는다. `[INFERENCE]` 대안(스키마에 필드 추가)은 `rows.py`
  소비처 전부에 파급되므로 채택하지 않는다.
- 표준 라이브러리만 사용 가능(REQ-GROUPGEN-007). `math` · `statistics` 외 신규 의존 금지.
- `topology.py`는 콘솔·포트·전송 참조가 0이어야 한다(REQ-GROUPGEN-006). 본 SPEC은 순수 함수 내부만
  바꾸므로 이 불변식에 접촉하지 않는다.
- `naming.py`의 공개 네이머는 5종뿐이다: `name_depth_bucket`(`:48`) · `name_lateral_bucket`(`:70`) ·
  `name_concentric_bucket`(`:115`) · `name_vertical_bucket`(`:143`) · `name_grid_9cell`(`:182`).
  **`bilateral_pairs`용 어휘는 없다** — D-Q10의 구조적 근거이며 본 SPEC이 보존해야 할 사실이다.
- 소비 경로: `server/orchestrator/tools.py:118` `classify as classify_topology` →
  `classify_arrangement_topology`(`:3518`) → `_name_topology_buckets`(`:3470`)의 `.get(result.kind)`
  디스패치(`:3495` 부근). **선택 축이 바뀌면 운영자가 보는 그룹 이름이 바뀐다** — 이것이 §7.3 부작용의
  실제 파급 범위다(쓰기는 아니다: 이 툴은 읽기 전용, `tools.py:3464-3469`).
