# 진행 기록 — 축 점수 비교 가능성

base `origin/main` = `4b4156e` (WRITEGATE-001 머지 후 rebase 완료) · branch `spec/axiscore-001` ·
worktree `axiscore`

**상태**: **M1~M5 완료.** 배제 규칙 **삭제됨** · 위상 코퍼스 **전부 GREEN** · 전 스위트
`5242 passed, 7 skipped` (기준선 `4763 passed, 7 skipped` + 신규 479) · 뮤테이션 **7종 전부 사살** ·
`server/` 변경 **2파일**(`server/spatial/topology.py` · `server/tests/test_topology.py`).

## A. 마일스톤

| 마일스톤 | 상태 | 산출 |
|---|---|---|
| **M0** 결정 게이트 | 접힘 | 결정 4건은 착수 전 종료 — `plan.md` §D |
| **M1** 정규화 식 확정 | **완료** | 기준선 전항 재현 후 N1 확정 — §B.1 |
| **M2** 정규화 착지 (규칙 유지) | **완료** | 코퍼스 60 + 인접 174 = **234 GREEN** · 규칙 무접촉 |
| **M3** 규칙 삭제 (**1차 AC**) | **완료** | 코퍼스 **60/60 GREEN** · `depth_partitions` grep 공백 |
| **M4** 현상 결속 테스트 | **완료** | 신규 **479건** · 스윕 405 전수 상시 · 뮤테이션 7종 RED |
| **M5** 판정 변경 전수 열거 | **완료** | **33건** · 예고 밖 **0건** — §D |

## B. 실행 기록

### B.1 M1 — 기준선을 먼저 재현했다

코드를 건드리기 전에 `research.md`의 측정값을 전부 다시 냈다. **어긋난 항목 0건**이므로 조사 기록을
그대로 신뢰하고 진행했다(전표는 `research.md` §9.1). 핵심 두 줄:

```
three_rows_two_trims   depth 60.00  vs  vertical 80.00     <- 규칙 없이는 vertical 승
m6_mirror_flat         lateral 0.75 vs  concentric 20.00   <- 틀린 해석이 27배 높다
배제 규칙만 삭제        1 failed, 59 passed                <- 코퍼스 판별력 = 테스트 1건
스윕 A 규칙만 삭제      126 / 252 판정 변경 (50.0%)         <- 골든 1건이 덮는 현상의 크기
```

### B.2 변경 집합 — 2파일

| 파일 | 성격 | 삭제 |
|---|---|---|
| `server/spatial/topology.py` | `_partition_score` 신설 · 4개 산출부 교체 · `AXIS_TIE_BREAK_ORDER` 신설 · **배제 규칙 삭제** | 정책 **24행** (`@MX:ANCHOR`/`@MX:REASON` 21 + `depth_partitions` 1 + 조건부 삽입 2). `contenders` 5행은 남되 `vertical`이 무조건 들어간다 |
| `server/tests/test_topology.py` | 신규 479건 · 기존 docstring 2건 갱신 | — |

`server/spatial/rows.py` · `schema.py` · `naming.py` · `server/orchestrator/**` · `server/safety/**`
**무접촉**(REQ-AXISCORE-011 · 경계 확인 §E).

### B.3 무엇을 어떻게 바꿨는가 — 원인 4건 대 항 4개

| 원인 (`research.md` §3) | 닫은 것 | 위치 |
|---|---|---|
| 1. 분모 하한이 점수를 원시 미터로 붕괴 | `min(sep / GAP_RATIO, 1.0)` 포화 | `_partition_score` |
| 2. depth만 `max_gap`, 나머지는 `min_boundary_gap` | 전 축 **가장 약한 경계 갭**. depth는 `analysis.rows`에서 국소 유도 | `_compute_depth` |
| 3. 분할 품질 항 없음 | `min(bucket_sizes) / count` | `_partition_score` |
| 4. `bilateral` 점수가 원시 개수 | `2 × len(pairs) / n` — 같은 닫힌 구간, 여전히 `scored` 밖 | `_compute_bilateral` |
| (동점) 우연한 삽입 순서 | `AXIS_TIE_BREAK_ORDER` 명명 시퀀스 + 명시적 정렬 키 | `classify` |

정렬 키가 `(-score, AXIS_TIE_BREAK_ORDER.index(kind))`가 되면서 **선택이 `contenders` 삽입 순서에
더 이상 의존하지 않는다.** `acceptance.md` AC-008이 제안한 *"불안정 정렬로 바꾸면 RED"* 뮤테이션은
그래서 **적용 불가**가 됐다 — 코드가 정렬 안정성에 기대지 않으므로, 그 자리를 대신하는 등가 뮤테이션은
**전순서를 뒤집는 것**이고 그쪽이 더 강하다(§C 뮤테이션 e).

### B.4 점수 전후 — 고정 리그

| 리그 | 전 (d / l / c / v) | 후 (d / l / c / v) | 판정 |
|---|---|---|---|
| `_three_rows_two_trims` | 60.00 / 0 / 0 / **80.00** | **0.3333** / 0 / 0 / **0.3333** | `depth_rows` (동점 → 전순서) |
| `_electrics_three_bars` | **60.00** / 0 / 0 / 30.00 | **0.3333** / 0 / 0 / **0.3333** | `depth_rows` (동점 → 전순서) |
| `_golden_vertical_levels` | 0 / 20.00 / 20.00 / **60.00** | 0 / 0.2500 / 0.2500 / **0.3333** | `vertical_levels` (**점수로**) |
| `_golden_concentric` | 36.60 / 0 / **60.00** / 0 | 0.0556 / 0 / **0.3333** / 0 | `concentric` |
| `m6_mirror_flat` | 0 / 0.75 / **20.00** / 0 | 0 / 0.0938 / **0.1111** / 0 | `lateral_split` (강등 후) |
| `rings 6@3.0 + 8@5.0` | **51.96** / 0 / 40.00 / 0 | 0.0714 / 0 / **0.4286** / 0 | `depth_rows` → **`concentric`** |
| `rings 6@3.0 + 12@5.0` | **50.00** / 0 / 40.00 / 0 | 0.0272 / 0 / **0.3333** / 0 | `depth_rows` → **`concentric`** |
| `_golden_grid` bilateral | 15.00 (구간 밖) | 1.0000 | 여전히 미선택 |

`_three_rows_two_trims`의 `0.3333 == 0.3333`은 **진짜 동점**이다: 두 분할 모두 완벽 분리(포화)이고
최소 버킷 몫도 같은 5/15. 억누른 선호가 아니다.

## C. 뮤테이션 — 7종, 전부 사살

표적은 **정규화 식 자체**이며 골든 픽스처는 하나도 건드리지 않았다(REQ-AXISCORE-018).
대상: `test_topology.py` + `test_topology_naming_seam.py` (539건).

| # | 뮤테이션 | 결과 | 대표 RED |
|---|---|---|---|
| a | depth 분자를 `analysis.gaps.max_gap`으로 복원 | **1 failed** | `test_depth_is_graded_on_its_weakest_boundary_like_every_other_axis` |
| b | 분할 품질 항 `min(bucket_sizes)/count` 제거 | **55 failed · 20 테스트** | `test_two_ring_rigs_with_a_narrow_radial_gap_are_concentric` · `test_the_flat_mirror_folds_27x_score_advantage_is_gone` · `test_sweep_c_...` · `test_a_rings_real_split_...` |
| c | **배제 규칙 재추가** | **1 failed** | `test_a_better_vertical_reading_beats_a_partitioning_depth` |
| d | 포화 `min(…, 1.0)` 제거 | **159 failed** | `test_the_separation_term_saturates_...` · 스윕 A/B · 스케일 |
| e | `AXIS_TIE_BREAK_ORDER` 역순 | **269 failed** | `test_the_axis_order_fires_only_on_an_exact_tie` · 스윕 A 전수 |
| f | bilateral 점수를 `float(len(pairs))`로 복원 | **7 failed** | `test_every_detector_scores_inside_one_closed_interval` |
| g | `bilateral`을 `contenders`에 투입 | **59 failed** | `test_bilateral_is_normalised_...` · `TestDeterminism` |

**뮤테이션 a와 c가 각각 정확히 1건씩 RED**인 것이 중요하다 — 둘 다 그 결함만을 겨냥해 지은 테스트가
받아냈다는 뜻이고, 특히 **c는 규칙을 조용히 되돌릴 수 없음**을 보증한다. 그 테스트는 골든 리그가 아니라
*"depth가 분할하는데 vertical이 점수로 더 높은 리그"* 라는 **조건**에 걸려 있다(2·8 행 × 5·5 트림,
depth 0.200 대 vertical 0.500).

## D. 판정 변경 전수 (AC-AXISCORE-013) — 33건, 예고 밖 0건

정규화 전 base(규칙 있음) 대 착지 후(규칙 없음) 전수 비교.

| 무리 | 건수 | 근거 |
|---|---|---|
| 스윕 B 평면 격자 | **30** (18 `lateral`→`vertical`, 12 반대) | **D1**(사용자). 평면 격자에서 두 축은 대칭 가설이고 코퍼스가 고정하는 1건은 그대로다 |
| 스윕 C 링 오독 정정 | **2** (`depth_rows`→`concentric`) | **D2**(사용자). 창립 오독과 같은 형상 — 부작용이 아니라 **인도하는 결함 수정** |
| 고정 리그 `_golden_bilateral` | **1** (`concentric`→`depth_rows`) | **D3**. depth 0.200 대 concen 0.200 **정확한 동점**을 전순서가 깬 결과. 이 리그는 코퍼스가 축을 고정하지 않는다(`research.md` §4.2 #8) |
| **스윕 A** | **0** | **규칙을 지웠는데 252 리그 중 하나도 안 바뀌었다 — 규칙이 잉여였다는 증거 그 자체** |
| 그 밖 | **0** | 고정 19 리그 중 위 1건 외 변경 없음 |

`[INFERENCE]` 이 보증은 **스윕 범위 안에서만** 성립한다. 범위: A `rows∈{2..5} × cols∈{3,5,8} ×
trims∈{2,3} × ypitch∈{1,3,6} × zgap∈{0.5,2,4,10}` · B `cols∈{3,4,6,10} × trims∈{2,3,4} ×
zgap∈{0.5,3,8} × xpit∈{0.5,2}` · C `ni∈{4,6,8} × no∈{8,12,16} × ri∈{1,2,3} × ro∈{5,7,9}`.

## E. 발견 — SPEC이 과대 주장한 성질 1건

`plan.md` §B.2와 `research.md` §7이 N1의 스케일 불변성을 **무조건**으로 적었다. 실측 결과 그것은
**`within_bucket_span == 0`일 때 거짓**이고, `rows.py`가 스스로 적듯 그것이 **정상 케이스**다.
스프레드가 0이면 같은 축 위에 비를 만들 두 번째 길이가 없어 분모가 절대 하한으로 떨어지고, 포화
아래에서 점수는 여전히 미터 비례다.

| 모집단 (405 리그 × 4 축 × 5 배율 = 8100) | 조합 | 판정 변동 |
|---|---|---|
| 포화 구간 **안** (보증 대상) | **5510** | **0** |
| 포화 구간 **밖** | 165 | 165 |
| 절대 하한이 **분할 자체를 다시 자름** | 2163 | 불변성 질문이 아니다 — 다른 리그다 |

**식의 결함이 아니다.** 포화 아래에서 무차원 점수를 만들려면 새 기준 길이를 발명해야 하고 그것은
REQ-AXISCORE-008이 금지한다. 임계는 `SPATIAL_ROW_GAP_RATIO × SPATIAL_ROW_NOISE_SPAN`이며 실제 리그의
행 간격보다 훨씬 아래라 실무 영향은 없다. **식은 재론하지 않았다** — 바꾼 것은 문서와 테스트다:

- REQ-AXISCORE-001에 정식 조건절 + 실측 표 + 스윕 상한을 넣었다.
- `plan.md` §B.2 · `research.md` §7에 각각 경고를, `research.md` §9.2에 경계 유도와 두 모집단 분리를
  기록했다 — **다음 사람이 배율을 넓혔다가 회귀를 발견했다고 착각하지 않도록.**
- 테스트는 참인 불변식에 걸었다: 포화 여부를 **공개 점수만으로** 판정하고(포화하면 점수가 정확히
  `min(bucket)/n`), 분할이 바뀐 조합은 세어서 제외하며, `exercised > 400` 하한이 그 제외가 테스트를
  공허하게 만들지 못하게 막는다.

**이것은 되풀이되는 결함 유형의 세 번째 사례다** — 조건부 보증을 무조건으로 적는 것. 선례:
`REQ-SPATIAL-024`(약한 의미에서만 참) · `REQ-WRITEGATE-005`(`Cmd()` 리터럴만 덮으면서 "배포 대상 Lua
소스" 전체를 주장). 패턴으로 REQ-AXISCORE-001에 명시했다.

## F. 검증

| 단계 | 명령 | 결과 |
|---|---|---|
| 위상 + 시임 | `pytest server/tests/test_topology.py server/tests/test_topology_naming_seam.py -q` | **539 passed in 0.84s** |
| 인접 회귀 | `pytest test_groupgen_tools test_groupgen_write test_groupgen_choreography_seam test_naming test_spatial_analysis -q` | **174 passed** |
| 전체 | `pytest server/tests/ -q` | **5242 passed, 7 skipped in 92.59s** (기준선 4763 + **479**) |
| 규칙 삭제 확인 | `grep -c depth_partitions server/spatial/topology.py` | **0** |
| 경계 | `git status --porcelain -- server/orchestrator server/safety server/spatial/rows.py` | **공백** |
| 린트 | `ruff format --check` · `ruff check` (2파일) | **통과** |

**스윕 405 리그는 `slow` 마커도 부분집합도 없이 상시 실행**된다(D4). 추가 비용: `test_topology.py`가
0.04초 → 0.84초, 전 스위트 대비 **0.8%**. 대부분은 스케일 스윕 8100 조합이다.

## G. 이 SPEC이 남기는 것

배제 규칙은 **점수를 비교 가능하게 만드는 대신 후보 하나를 경합에서 빼는 정책**이었고, GROUPGEN-001이
그 자리에 *"근본적으로 축 간 점수 비교 가능성이 미해결이다"* 라고 적어 두었다. 그 순서를 되돌렸다:
점수를 비교 가능하게 만들고, **252 리그 중 판정이 하나도 바뀌지 않음을 보여** 규칙이 잉여였음을 증명한
뒤 삭제했다.

덤으로 닫힌 것 둘 — 둘 다 규칙과 무관하게 **오늘 라이브였던 결함**이다:

1. **스케일 의존 1건**: `_golden_vertical_levels`의 z를 1/10로 줄이면 `lateral_split`으로 뒤집혔다.
   골든 코퍼스 **안**의 리그에서 일어나던 일이다.
2. **링 오독 2종**: `6@r=3.0 + 8@r=5.0` · `6@r=3.0 + 12@r=5.0`이 `depth_rows`로 분류됐다 — 이 SPEC
   계열의 **창립 오독과 같은 형상**. 그리고 그 리그는 초록색 골든 픽스처(`_golden_concentric`,
   내측 r=2.0)에서 **반지름 1 미터** 떨어진 곳에 있었다. 코퍼스는 그 사이를 보지 않았다.
