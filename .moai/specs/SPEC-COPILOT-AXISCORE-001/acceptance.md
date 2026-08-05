# 인수 기준 — 축 점수 비교 가능성

base `origin/main` = `b1a630e` · 판정 원칙: **성공은 "배제 규칙 없이도 코퍼스가 그린이다"로 걸고, 변이
표적은 정규화 식 자체다 — 골든 픽스처가 아니다.**

> **base 이동 예정**: WRITEGATE PR #26 머지 후 `origin/main`이 이동하므로 이 브랜치는 **rebase가
> 필요하고**, AC-AXISCORE-011의 `<BASE>` 기준점도 그때 갱신한다(`plan.md` 머리말 · 배치 결정 4).

측정 기준선(본 세션 실측): 전체 스위트 `4716 passed · 7 skipped` · 위상 테스트 **60건**
(`test_topology.py` 48 + `test_topology_naming_seam.py` 12) · 인접 회귀 **174건**
(`test_groupgen_tools` · `test_groupgen_write` · `test_groupgen_choreography_seam` · `test_naming` ·
`test_spatial_analysis`).

---

## A. 시나리오 (Given–When–Then)

### 시나리오 1 — 정책이 잉여였음이 증명된다 (본 SPEC의 존재 이유)

- **Given** 축 점수가 정규화되어 축을 넘어 비교 가능하다.
- **When** `topology.py:463` · `:469-470`의 배제 규칙과 그 `@MX:ANCHOR` 블록(`:442-462`)을 **삭제하고**
  `vertical_levels`를 무조건 경합에 넣은 뒤 위상 골든 코퍼스 전체를 돌린다.
- **Then** **전부 GREEN이다.** 규칙이 없어도 `_three_rows_two_trims`는 `depth_rows` `[5,5,5]`로,
  `_electrics_three_bars`는 `depth_rows` `[5,5,5]`로, `_golden_vertical_levels`는 `vertical_levels`
  `[4,4,4]`로 답한다.
- **대조(오늘)**: 같은 삭제를 정규화 없이 하면 `1 failed · 4715 passed`
  (`test_depth_rows_beats_a_vertical_reading_that_merges_two_rows`, `research.md` §5.1).

### 시나리오 2 — 같은 리그, 다른 단위, 같은 답

- **Given** `_golden_vertical_levels`(z 트림 3단, x 4열, y 평면)가 있다.
- **When** z 좌표 전부에 **0.1을 곱한다** — 구조는 그대로고 단위만 바뀐다.
- **Then** 판정은 `vertical_levels` 그대로다.
- **대조(오늘)**: 판정이 **`lateral_split`으로 뒤집힌다**(vertical 60.00 → 6.00, lateral 10.00 고정 —
  `research.md` §3.1). 골든 코퍼스 안의 리그에서 오늘 이미 일어나는 일이다.

### 시나리오 3 — 두 완벽한 분할은 동점이고, 승부는 문면으로 갈린다

- **Given** 3개 깊이 행이 2개 트림에만 걸린 리그(`_three_rows_two_trims`) — y는 `[5,5,5]`로,
  z는 `[10,5]`로 답하며 **둘 다 버킷 내 스프레드 0**이다.
- **When** 두 축을 정규화 점수로 채점한다.
- **Then** 두 점수가 **정확히 같다.** 그 위에서 문면화된 축 전순서(`depth_rows` 우선)가 승자를 고르고,
  선택은 `depth_rows` `[5,5,5]`다. `vertical_levels`는 `candidates`에 **고신뢰 그대로** `[10,5]`로 남는다.
- **대조(오늘)**: 60.00 대 **80.00**으로 z가 이기고, 배제 규칙이 z를 경합에서 **빼서** 막는다.

### 시나리오 4 — 창립 오독이 코퍼스 바깥에서도 닫힌다

- **Given** 2겹 링 리그 `6@r=3.0 + 12@r=5.0`(오늘 골든에 없다).
- **When** 분류한다.
- **Then** `concentric` `[6,12]`다.
- **대조(오늘)**: **`depth_rows` `[1,2,2,2,4,2,2,2,1]`** — 링의 y 투영 artefact를 9개 행으로 읽는다
  (`research.md` §5.3). GROUPGEN이 존재하는 바로 그 결함이다.
- **결정 기록**: 이 리그(와 `6@r=3.0 + 8@r=5.0`)의 정답이 `concentric`이라는 것은 **사용자 결정**이다
  (2026-08-05 · `plan.md` §D **D2**). `low_confidence` 대안은 채택되지 않았다.

### 시나리오 5 — 대칭은 여전히 신호일 뿐이다

- **Given** `_MIRRORED_LEFT_RIGHT` 평면 미러 리그.
- **When** 분류한다.
- **Then** 선택은 `lateral_split` `[9,9]`이고 `bilateral_pairs`는 **고신뢰로 보고되되 선택되지 않는다**.
  `concentric`은 `concentric_reading_is_a_mirror_artefact`로 강등된 채 보고된다.
- 정규화는 이 세 판정 중 **무엇도 바꾸지 않는다.**

### 시나리오 6 — 현상이 리그 하나에 걸리지 않는다

- **Given** `_three_rows_two_trims`의 형상을 행 수 · 열 수 · 트림 수 · y 피치 · z 갭으로 흔든 리그군.
- **When** 배제 규칙이 삭제된 상태로 전부 분류한다.
- **Then** z 판독이 깊이 행을 융합해 이기는 리그가 **0건**이다.
- **대조(오늘)**: 정규화 없이 규칙만 지우면 **252 리그 중 126건(50.0%)**이 넘어간다. 오늘의 코퍼스는
  그중 **1건**만 잡는다(`research.md` §5.2).

### 시나리오 7 — 이긴 축이 바뀐 리그는 하나도 숨지 않는다

- **Given** 정규화가 착지했다.
- **When** 고정 19 리그 + 스윕 A(252) + B(72) + C(81)를 전후 비교한다.
- **Then** 판정이 바뀐 리그가 **전수 열거**되고 각각 새 판정의 근거가 문서에 있다. 오늘 알려진 세 무리:
  평면 격자 30/72 · 링 오독 정정 2건 · `_golden_bilateral` 1건.

---

## B. 인수 기준

### AC-AXISCORE-001 — **[1차]** 배제 규칙 삭제 후 코퍼스 전부 GREEN

**When** `topology.py:463` · `:469-470` · `:442-462`가 삭제되고 `vertical_levels`가 무조건 경합에
들어가면, the 위상 골든 코퍼스 **shall** 전부 GREEN이다.

- 대상 요구: REQ-AXISCORE-006 · 007 · 008
- **통과 판정**:
  `uv run --frozen pytest server/tests/test_topology.py server/tests/test_topology_naming_seam.py -q`
  → **0 failed**. 명시 리그: `_three_rows_two_trims` → `depth_rows` `[5,5,5]` ·
  `_electrics_three_bars` → `depth_rows` `[5,5,5]` · `_golden_vertical_levels` → `vertical_levels`
  `[4,4,4]` · `_golden_concentric` → `concentric` `[6,12]` · `_MIRRORED_LEFT_RIGHT` →
  `lateral_split` `[9,9]`.
  추가로 `grep -n "depth_partitions" server/spatial/topology.py`가 **빈 출력**이어야 한다 — 규칙이 다른
  이름으로 살아남지 않았음의 증거.
- **비공허성 (필수 · 이것이 AC를 의미 있게 만든다)**: 정규화를 되돌리고 규칙만 삭제한 상태에서 같은
  명령이 **1 failed**여야 한다. 본 세션 실측으로 이 값을 이미 확보했다(`research.md` §5.1) — 즉
  **이 AC가 통과하는 유일한 이유는 정규화다.**
- **뮤테이션**: `research.md` §7의 정규화 식에서 (a) 포화 `min(…, 1.0)` 제거 → RED
  (b) `depth` 분자를 `analysis.gaps.max_gap`으로 복원 → RED (c) 분할 품질 항 `min_bucket_size / n`
  제거 → RED (d) 동점 축 전순서 제거(불안정 정렬로 대체) → RED. **네 변이 모두 정규화 식이 표적이며
  골든 픽스처는 건드리지 않는다**(REQ-AXISCORE-018).
- 실패 시 처리: RED가 난 리그가 ASSUMPTION-76의 반례다. 규칙 삭제를 재개방하고 정규화만 착지시킨다
  (`plan.md` §E 위험 1) — **"고쳤다"고 적지 않는다.**

### AC-AXISCORE-002 — 축 스케일 불변성

The 각 축 점수와 `classify()`의 선택 **shall** 그 축 좌표의 균일 스케일 변환에 불변이다.

- 대상 요구: REQ-AXISCORE-001
- **통과 판정**: 매개변수화 — 리그 × 축 ∈ {x, y, z, 전축} × 배율 ∈ {0.1, 0.5, 1, 10, 100}. 각 조합에서
  (a) 해당 축의 점수가 배율 무관 동일 (b) `classify().selected.kind`가 동일 (c) 버킷 형상이 동일.
  **명시 케이스**: `_golden_vertical_levels` z×0.1 → `vertical_levels`.
- **비공허성**: 같은 매개변수화를 정규화 **전** base에 걸면 `_golden_vertical_levels` z×0.1이
  `lateral_split`으로 RED여야 한다 — 오늘 실측 확보(`research.md` §3.1 표 3행).
- **뮤테이션**: 분모 하한을 `max(within_spread, NOISE)`의 **원시 나눗셈**으로 되돌리면 RED.

### AC-AXISCORE-003 — 전 축 동일 순서통계량

The 모든 축 점수 **shall** 경계 갭 중 **가장 약한 것**으로 산출된다.

- 대상 요구: REQ-AXISCORE-002
- **통과 판정**: `_compute_depth`가 링 리그에서 쓰는 분자가 `min_boundary_gap`임을 직접 단정한다.
  실측 대조값(본 세션): `_golden_concentric` — `max_gap` 1.830 대 `min_boundary_gap` **0.670** ·
  `rings 6@3.0+12@5.0` — 2.500 대 **0.098** · `rings 6@3.0+8@5.0` — 2.598 대 **0.937**.
  `analysis.gaps.max_gap` 참조가 `_compute_depth`에서 사라졌음을 grep으로 확인한다.
- **뮤테이션**: `max_gap`으로 되돌리면 AC-AXISCORE-006(링 오독)이 RED.

### AC-AXISCORE-004 — 닫힌 공통 구간

The 모든 축의 점수 **shall** 닫힌 공통 구간 안에 있다.

- 대상 요구: REQ-AXISCORE-003 · 016
- **통과 판정**: 고정 19 리그 × 5 산출 함수(`_compute_depth` · `_compute_lateral` ·
  `_compute_concentric` · `_compute_vertical` · `_compute_bilateral`) 전수에서 점수가 구간 안이며
  `math.isfinite`가 참. **`_compute_bilateral`도 포함된다** — 오늘은 원시 쌍 개수(`topology.py:306`,
  `golden_grid`에서 15.00)라 구간을 벗어난다.
- **비공허성**: 정규화 전 base에서 `_compute_bilateral(_golden_grid())[1] == 15.0`이 구간 밖임을 실측으로
  기록한다.
- **뮤테이션**: `_compute_bilateral`을 `float(len(pairs))`로 되돌리면 RED.

### AC-AXISCORE-005 — 분할 품질이 점수에 들어간다

The 점수 **shall** 같은 분리도에서 최소 버킷의 몫이 큰 분할을 높게 매긴다.

- 대상 요구: REQ-AXISCORE-004
- **통과 판정**: `_golden_concentric`에서 `concentric`(`[6,12]`) 점수 > `depth`(`[1,2,2,2,4,2,2,2,1]`)
  점수. 링 반지름을 `(2,5)` · `(3,5)` · `(1,5)` · `(2,7)` · `(3,9)`로 흔들어도 부등호가 유지된다 —
  **반지름 간격의 절대 크기에 의존하지 않는다.** (`(1,7)` · `(3,7)`은 `grid` 단락이 걸려 경합 자체가
  일어나지 않으므로 이 AC의 대상이 아니다 — 실측 확인.)
- **비공허성**: 정규화 전 base에서 `(3,5)` 조합은 부등호가 **반대**다(depth 50.00 > concen 40.00) —
  즉 이 AC는 오늘 RED다.
- **뮤테이션**: 분할 품질 항 제거 → RED.

### AC-AXISCORE-006 — 링 오독 2종의 정정 (**D2가 확정한 잠재 결함 수정**)

**When** 2겹 링 리그가 좁은 반지름 간격을 가지면, the 분류 **shall** `concentric`을 답한다.

- 대상 요구: REQ-AXISCORE-002 · 004 · ASSUMPTION-79(**결정으로 닫힘**)
- **결정 근거 (사용자, 2026-08-05 · `plan.md` §D D2)**: `6@r=3.0 + 8@r=5.0` · `6@r=3.0 + 12@r=5.0`의
  정답은 **`concentric`**이고 오늘의 `depth_rows`는 **오독**이다. *"두 링이 너무 가까우니
  `low_confidence`가 정직한 답"* 이라는 대안은 **채택되지 않았다** — 이 형상이 이 SPEC 계열의 **창립
  오독과 같은 형상**이므로, 정규화가 이를 고치는 것은 부작용이 아니라 **이득**으로 기록한다. 따라서 이
  AC는 부작용 관측이 아니라 **본 SPEC이 인도하는 결함 수정**을 고정한다.
- **통과 판정**: `6@r=3.0 + 8@r=5.0`(n=14) · `6@r=3.0 + 12@r=5.0`(n=18) 모두 `concentric`이고 버킷이
  각각 `[6,8]` · `[6,12]`. 두 리그 모두 **`low_confidence`가 아니어야 한다** — 결정이 배제한 답이므로
  이것도 함께 단정한다.
- **비공허성**: 오늘 두 리그는 `depth_rows`이고 버킷이 `[1,2,2,4,2,2,1]` · `[1,2,2,2,4,2,2,2,1]`이다
  (`research.md` §5.3 실측) — **정규화 전에는 RED다.**
- **뮤테이션 — 표적은 정규화 그 자체다**(골든 픽스처가 아니다 · REQ-AXISCORE-018): (a) `depth` 분자를
  `analysis.gaps.max_gap`으로 복원 (b) 분할 품질 항 `min_bucket_size / n` 제거 — **각각 두 리그를
  `depth_rows`로 되돌려 RED**로 만든다. 실측 대조값: `max_gap` 2.598 / 2.500 대 `min_boundary_gap`
  0.937 / 0.098(`research.md` §7.2 · AC-AXISCORE-003).
- 이 AC는 **조건부가 아니다.** ASSUMPTION-79의 "NEGATIVE면 `low_confidence` 기대로 다시 쓴다" 분기는
  결정으로 **닫혔다.**

### AC-AXISCORE-007 — **변형 스윕**: 현상에 결속된 회귀

The AC **shall** 단일 리그가 아니라 매개변수 스윕에 걸린다.

- 대상 요구: REQ-AXISCORE-017
- **통과 판정 (스윕 A · 행×트림)**: `rows ∈ {2,3,4,5}` × `cols ∈ {3,5,8}` × `trims ∈ {2,3}` ×
  `ypitch ∈ {1.0,3.0,6.0}` × `zgap ∈ {0.5,2.0,4.0,10.0}`, `trims <= rows` → **252 리그**. 배제 규칙이
  삭제된 상태에서 z 판독이 깊이 행을 융합해 이기는 리그 **0건**.
  - `ypitch`와 `zgap`을 **독립으로** 흔드는 것이 핵심이다 — 오늘의 결함은 "z 갭이 y 갭보다 크면 z가
    이긴다"이므로, 두 축의 물리적 갭 비를 0.05배(`ypitch=6, zgap=0.5`)에서 10배(`ypitch=1, zgap=10`)까지
    쓸어야 현상을 덮는다.
- **통과 판정 (스윕 B · 평면 격자)**: `cols ∈ {3,4,6,10}` × `trims ∈ {2,3,4}` × `zgap ∈ {0.5,3.0,8.0}` ×
  `xpit ∈ {0.5,2.0}` → **72 리그**. 두 가지를 단정한다:
  1. **일관성** — 판정이 `zgap`·`xpit`의 **절대 크기에 의존하지 않는다**(같은 `cols×trims`면 네 스케일
     조합이 같은 답). 이것이 §3.1 단위 오류의 직접 반증이다.
  2. **기본값 방향 (D1 · 사용자 2026-08-05)** — `lateral`과 `vertical`의 정규화 점수가 **정확히 같은**
     리그에서 선택은 **`lateral_split`**이다. `vertical`이 이기는 리그는 **점수로** 이겨야 하며
     (`_golden_vertical_levels`: `lateral` 0.250 대 `vertical` 0.333), 그 리그에서 전순서가 개입하지
     않음을 함께 단정한다 — `lateral` 기본값이 더 높은 점수를 덮지 **않는다**는 증거
     (REQ-AXISCORE-008).
  판정 변경 **30 / 72**(18건 `lateral`→`vertical`, 12건 반대 — `research.md` §7.3)는 이 결정으로
  **그대로 수용**되며, 전수 열거는 AC-AXISCORE-013이 담당한다.
- **통과 판정 (스윕 C · 2겹 링)**: `ni ∈ {4,6,8}` × `no ∈ {8,12,16}` × `ri ∈ {1.0,2.0,3.0}` ×
  `ro ∈ {5.0,7.0,9.0}` → **81 리그**. `grid` 단락이 걸리는 50건은 `grid`, 나머지는 `concentric`.
- **비공허성 (필수)**: 스윕 A를 정규화 전 base + 규칙 삭제 상태에서 돌리면 **126 / 252**가 RED여야
  한다. 이 숫자가 재현되지 않으면 스윕이 현상을 덮지 못하는 것이다.
- **왜 이 형태인가**: 이 저장소는 같은 결함을 **두 번** 놓쳤다 — 첫 수정이 *증상이 나타난 리그*를 고정했을
  뿐 *원인*을 고정하지 않았기 때문이다(`GROUPGEN progress.md:778-779`, 미러 아티팩트 강등이 여분 장비
  1대로 재발). 골든 1종은 현상의 **0.8%**만 덮는다.
- **CI 축약 — 하지 않는다 (D4 · 에이전트 2026-08-05)**: 스윕 A(252) · B(72) · C(81)은 **전수가 일반
  테스트로 상시 실행**된다. `slow` 마커도, 대표 부분집합도, 재현 스크립트로의 격리도 **없다.** 실측이
  근거다: `classify` + `analyze_spatial_records` 전 경로로 **288 리그가 0.017초**(0.06 ms/리그)이고,
  현재 `test_topology.py` 48건 전체가 **0.04초**, 전체 스위트가 약 **90초**다. 405 리그 전수는 약
  **0.03초** — 전체 스위트의 0.03 % 수준이라 **축약할 근거가 존재하지 않는다.** 부분집합으로 줄이는 것은
  이 AC가 방어하려는 바로 그 함정(*"테스트가 다시 형상에 고정된다"* · `plan.md` §E 위험 3)을 자초하는
  일이므로, 이 결정은 그 위험의 재유입도 함께 막는다.

### AC-AXISCORE-008 — 동점은 동점으로 드러난다

**When** 두 축의 정규화 점수가 같으면, the 선택 **shall** 문면화된 축 전순서로 결정된다.

- 대상 요구: REQ-AXISCORE-005
- **통과 판정**: `_three_rows_two_trims`와 `_electrics_three_bars`에서 (a) `depth`와 `vertical`의 점수가
  **정확히 같음**을 먼저 단정하고 (b) 선택이 `depth_rows`임을 단정한다. (a)가 없으면 이 테스트는
  전순서가 아니라 우연한 대소를 확인하게 된다.
- 전순서가 `topology.py`에 **주석이 아니라 코드 구조로** 드러나야 한다 — 축 순서를 담은 명명된 시퀀스.
- **뮤테이션**: 전순서를 뒤집으면(`vertical` 우선) 두 리그가 RED. 정렬을 불안정 정렬로 바꿔도 RED.
- **비공허성**: `_golden_vertical_levels`에서는 점수가 **다르고**(vertical 승) 전순서가 개입하지
  않음을 단정한다 — 전순서가 vertical을 이기게 하는 것이 아니라 동점만 처리한다는 증거.

### AC-AXISCORE-009 — `bilateral_pairs`는 여전히 선택되지 않는다

The 정규화 **shall not** `bilateral_pairs`를 경합에 넣는다.

- 대상 요구: REQ-AXISCORE-009 · 016
- **통과 판정**: 기존 `test_bilateral_pairs_is_reported_but_never_selected` GREEN 유지. 추가로
  `_compute_bilateral`의 점수가 공통 구간으로 옮겨진 **뒤에도** `scored` 구성에서 제외됨을 구조로
  단정한다(`classify()`가 `bilateral_score`를 순위 결정에 쓰지 않음).
- **뮤테이션**: `(bilateral, bilateral_score)`를 `contenders`에 넣으면 RED — `.plan-contract.md` §2
  D-Q10의 기존 뮤테이션 요구를 그대로 계승한다.
- 근거 보존: `naming.py`에 대칭 어휘가 없다는 사실(`:48`·`:70`·`:115`·`:143`·`:182` 5종뿐)이
  변하지 않았음을 확인한다.

### AC-AXISCORE-010 — 미러 아티팩트 강등과 `grid` 단락 무변경

The 정규화 **shall not** 점수 이전 단계의 두 판단을 바꾼다.

- 대상 요구: REQ-AXISCORE-010
- **통과 판정**: 기존 6건 GREEN 유지 — `test_mirrored_left_right_rig_is_lateral_not_nine_rings` ·
  `test_flat_mirror_rig_plus_one_spare_fixture_is_still_lateral_not_rings` ·
  `test_flat_mirror_rig_plus_a_centre_fixture_is_not_rings` ·
  `test_no_flat_mirror_bar_variant_is_ever_read_as_rings`(6 파라미터) ·
  `test_a_genuine_two_ring_rig_still_wins_as_concentric` ·
  `test_grid_two_axis_contract_survives_the_vertical_policy`.
- **강등이 여전히 필요함을 실측으로 기록한다**: 강등을 끄면 정규화 후에도 `m6_mirror_flat`에서
  `concentric` **0.111** > `lateral` **0.094**로 `concentric`이 이긴다(오늘은 20.00 대 0.75).
  격차만 27배 → 1.18배로 줄고 **부호는 바뀌지 않는다.** `m6_centre`는 `lateral`이 비확신이라 더 분명하다
  (`concentric` 0.0049가 유일한 양수 후보). 즉 **정규화는 이 규칙을 대체하지 못하며 대체하려 해서도
  안 된다.**

### AC-AXISCORE-011 — 경계 보존

The 정규화 **shall not** `topology.py` 밖의 `server/spatial/**`와 소비 계약을 건드린다.

- 대상 요구: REQ-AXISCORE-011 · 012 · 013 · 014
- **통과 판정**:
  `git diff --stat <BASE>..HEAD -- server/spatial/rows.py server/spatial/schema.py server/spatial/naming.py`
  → **빈 출력**. `SPATIAL_ROW_NOISE_SPAN == 0.05` · `SPATIAL_ROW_GAP_RATIO == 4.0` 값 단정.
  `TopologyResult` 타입 불변식 테스트 **7건**(`test_topology.py:135-193`) GREEN.
  인접 회귀 **174건**(`test_groupgen_*` · `test_naming` · `test_spatial_analysis`) GREEN.
  신규 import 0(표준 라이브러리 `math`·`statistics` 외).
- 버킷 형상 보존 단정: 고정 19 리그 각각에서 **네 축의 버킷 형상이 정규화 전후 동일**하다
  (`research.md` §4.2 표가 기준선). 점수만 바뀌고 분할은 바뀌지 않았음의 증거.

### AC-AXISCORE-012 — 결정성

The 분류 **shall** 결정적이며 입력 순서에 무관하다.

- 대상 요구: REQ-AXISCORE-015
- **통과 판정**: 기존 `TestDeterminism` 9건(8 파라미터 + 셔플 1) GREEN 유지. 스윕 A/B/C의 각 리그에
  대해서도 역순 입력이 같은 선택을 낸다.
- 동점 전순서가 **입력 순서가 아니라 축 정체성**에 걸려 있음을 이 AC가 보증한다.

### AC-AXISCORE-013 — 판정 변경 리그의 전수 열거

The 구현 **shall** 판정이 바뀌는 리그를 전수 열거하고 각각을 정당화한다.

- 대상 요구: REQ-AXISCORE-019
- **통과 판정**: `progress.md`에 세 무리가 리그 좌표와 전후 판정으로 기록된다 — 평면 격자
  **30 / 72**(18건 `lateral`→`vertical`, 12건 반대) · 링 오독 정정 **2건** · `_golden_bilateral`
  **1건**(`concentric` → `depth_rows`, depth 0.200 대 concen 0.200 **정확한 동점**을 전순서가 깬 결과).
  스윕 전수 재실행으로 **열거되지 않은 변경 0건**을 확인한다.
- `[INFERENCE]` 이 보증은 **스윕 범위 안에서만** 성립한다. 리그 공간은 무한하므로 스윕의 매개변수 범위를
  문서에 명시한다.

### AC-AXISCORE-014 — 전체 회귀

The 변경 **shall** 전체 스위트 기준선을 유지한다.

- **통과 판정**: `uv run --frozen pytest -q` → `4716 passed · 7 skipped` + 신규 테스트분, `0 failed`.
  M2 게이트와 M3 게이트에서 **각 1회**만 실행한다(1회 약 90초 · 이전 측정 97.56s).
- 스윕 A·B·C는 이 전체 실행에 **상시 포함**된다(D4) — 별도 마커나 별도 실행 경로가 없으므로
  `uv run --frozen pytest server/tests/test_topology.py -q` 한 번으로도 전수가 돈다. 추가 소요 약
  **0.03초**.
- `uv run ruff check server/spatial/topology.py server/tests/test_topology.py` 신규 지적 0.

---

## C. AC ↔ 요구 대응

| AC | 요구 | 성격 |
|---|---|---|
| AC-AXISCORE-001 | REQ-006 · 007 · 008 | **1차 판정** |
| AC-AXISCORE-002 | REQ-001 | 구조 |
| AC-AXISCORE-003 | REQ-002 | 구조 |
| AC-AXISCORE-004 | REQ-003 · 016 | 구조 |
| AC-AXISCORE-005 | REQ-004 | 구조 |
| AC-AXISCORE-006 | REQ-002 · 004 · ASSUMPTION-79(닫힘) | **결함 정정** (D2 확정) |
| AC-AXISCORE-007 | REQ-017 | **현상 결속** |
| AC-AXISCORE-008 | REQ-005 | 구조 |
| AC-AXISCORE-009 | REQ-009 · 016 | 회귀(D-Q10) |
| AC-AXISCORE-010 | REQ-010 | 회귀 |
| AC-AXISCORE-011 | REQ-011 · 012 · 013 · 014 | 경계 |
| AC-AXISCORE-012 | REQ-015 | 회귀 |
| AC-AXISCORE-013 | REQ-019 | 절차 |
| AC-AXISCORE-014 | — | 회귀 |

전 19 요구 중 REQ-AXISCORE-018(뮤테이션 표적)은 **AC 하나에 대응되지 않고** AC-001 · 002 · 003 · 004 ·
005 · 008 · 009의 뮤테이션 절에 분산 구현된다 — 뮤테이션 표적이 정규화 식이라는 요구는 개별 AC의
성질이지 별도 시험이 아니다.
