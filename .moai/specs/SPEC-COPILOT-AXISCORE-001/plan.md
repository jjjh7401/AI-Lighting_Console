# 구현 계획 — 축 점수 비교 가능성

base `origin/main` = `b1a630e` · branch `spec/axiscore-001` · worktree `~/orca/workspaces/AI-Lighting_Console/axiscore`

## A. 이 계획이 서 있는 실측 위에서

착수 전에 다섯 가지를 이미 측정했다(`research.md`). 이 계획의 모든 판단은 그 숫자에서 나온다.

| 측정 | 값 | 함의 |
|---|---|---|
| `three_rows_two_trims` depth 대 vertical | **60.00 대 80.00** | 배제 규칙 없이는 vertical 승 — 부채의 재현 |
| 배제 규칙을 **오늘 그대로** 삭제 시 전체 스위트 | **1 failed · 4715 passed · 7 skipped** | 코퍼스 판별력 = 테스트 1건 |
| 같은 현상의 매개변수 스윕 | **126 / 252 리그 (50.0%)** 판정 변경 | 골든 1종이 현상의 0.8% |
| 오늘 이미 존재하는 라이브 결함 | 스케일 의존 1건 + 링 오독 2종 | 규칙과 무관 · 정규화가 닫는다 |
| 후보 정규화 N1 (규칙 제거 상태) | 고정 19 리그 **불일치 0** · 스윕 A **252/252** | **1차 AC가 달성 가능하다** |

**착수 조건이 이미 성립한다**: 성공 기준(배제 규칙 삭제 + 코퍼스 그린)이 달성 불가능한 목표가 아님을
시뮬레이션으로 확인했다(ASSUMPTION-76). 남은 것은 그것을 트리에 착지시키고, **현상에 결속된 테스트**로
고정하는 일이다.

## B. 설계 결정 — 무엇을 어떻게 정규화하는가

### B.1 방향

오늘의 점수는 세 곳이 어긋나 있다(`research.md` §3). 셋을 각각 닫는 항 셋으로 구성한다.

| 오늘의 결함 | 닫는 항 | 대응 REQ |
|---|---|---|
| 분모 하한 → 원시 미터 | 분리도를 **검출 임계로 포화**시켜 무차원 [0,1]로 | REQ-AXISCORE-001 · 003 |
| depth만 `max_gap` | 전 축 **가장 약한 경계 갭** | REQ-AXISCORE-002 |
| 분할 품질 항 없음 | **최소 버킷의 리그 내 몫** | REQ-AXISCORE-004 |
| 동점 시 우연한 삽입 순서 | **문면화된 축 전순서** | REQ-AXISCORE-005 |

### B.2 후보 N1 — 실측된 출발점 (확정 아님)

```
k = 버킷 수, n = 픽스처 수
k < 2                    -> 0.0
sep   = min_boundary_gap / max(max_within_bucket_span, SPATIAL_ROW_NOISE_SPAN)
s     = min(sep / SPATIAL_ROW_GAP_RATIO, 1.0)
score = s * (min_bucket_size / n)                                        # [0, 1]
동점  -> depth_rows > lateral_split > concentric > vertical_levels
```

성질(전부 실측 · `research.md` §7):

- **스케일 불변**: `sep`은 같은 축 위 두 길이의 비이므로 축 좌표 ×k에 불변. `min_bucket_size / n`은 개수
  비. 오늘의 결함(`golden_vertical_levels` z×0.1에서 판정 뒤집힘)이 사라진다.
- **포화가 요점**: `min(…, 1.0)`이 없으면 `three_rows_two_trims`에서 z의 4 m 갭이 y의 3 m 갭을 계속
  이긴다. 임계(`SPATIAL_ROW_GAP_RATIO = 4.0`)에서 포화시키는 이유는 그것이 **검출기가 이미 "경계다"라고
  판정하는 지점**이기 때문이다 — 새 상수를 발명하지 않는다.
- **전순서는 새 정책이 아니다**: 오늘 `scored.sort`가 안정 정렬이므로 `contenders` 삽입 순서
  (`topology.py:464-470`)가 이미 동점을 그렇게 깨고 있다. 문면화가 변경분이다.

**N1을 확정으로 적지 않는 이유**: `min_bucket_size / n`은 최소 버킷만 본다 — 중간 버킷들의 분포를 무시한다.
`[5,5,5]`와 `[5,4,6]`이 같은 점수를 받는다. 실측 리그에서는 문제가 되지 않았지만(불일치 0) **더 나은 항이
있을 수 있다**. M1의 첫 작업이 대안 2~3종을 같은 스윕에 걸어 비교하는 것이다(§C.M1).

### B.3 검토했으나 채택하지 않은 방향

| 대안 | 왜 아닌가 (실측 근거) |
|---|---|
| **분모 하한만 제거** (`within_spread` 그대로) | `within_spread == 0`이 정상이므로 0으로 나눈다. 하한은 제거 대상이 아니라 **포화로 감싸야 할** 대상이다 |
| **축 스팬으로 정규화** (`gap / axis_span`) | `three_rows_two_trims`에서 y = 3/6 = 0.5, z = 4/4 = **1.0** → z 승. 버킷 2개짜리 완벽 분할은 갭이 곧 스팬이라 항상 만점 — 반대 방향으로 편향된다 |
| **평균 갭으로 정규화** (`gap / (span/(n-1))`) | 같은 리그에서 y = 7.0, z = **14.0** → z 승. 버킷이 적을수록 기계적으로 유리 |
| **분산비(eta² / Calinski-Harabasz 류)** | 이 리그들은 버킷 내 스프레드가 **정확히 0**이라 모든 분리도 측도가 1.0으로 포화한다 — 판별력이 0. 실측: `research.md` §3.1의 `within_spread=0.000` 행 전부 |
| **버킷 수 패리티**(적을수록/많을수록 유리) | 두 방향 다 실패한다. 적을수록 유리 → `three_rows_two_trims`에서 z(2버킷) 승. 많을수록 유리 → `golden_concentric`에서 depth(9버킷) 승 = **창립 오독 재발** |
| **축별 가중 상수** | REQ-AXISCORE-008이 금지. 배제 규칙을 숫자로 옮겨 적은 것에 불과하고, 새 상수마다 어느 리그에 맞춘 것인지 물어야 한다 |

### B.4 구현 제약

- `SpatialGapProfile`(`schema.py:122-133`)에 `min_boundary_gap`이 없으므로 `_compute_depth`가
  `analysis.rows`에서 **국소 유도**한다. `rows.py`·`schema.py`는 무변경(REQ-AXISCORE-011).
- `_axis_buckets`(`topology.py:103-163`)는 이미 `min_boundary_gap`·`bucket_spans`를 계산하고 있다
  (`:156`, `:160`). 반환 시점에 점수만 새 식으로 바꾼다 — 분할 로직은 손대지 않는다.
- `_compute_bilateral`(`:306`)은 개수 대신 공통 구간 값을 반환하되 `scored` 밖에 남는다
  (REQ-AXISCORE-016 · 009).

## C. 마일스톤

### M0 — 결정 게이트 (사람)

착수 전에 §D의 `[NEEDS CLARIFICATION]` **4건**을 사용자에게 올린다. 특히 **평면 격자 판정**은 30 리그의
동작을 바꾸므로 구현 전에 확정돼야 한다 — 나중에 뒤집으면 정규화 식 자체를 다시 고른다.

산출: 결정 4건이 `plan.md`에 확정 표로 기록되고, 그중 3건에 대응하는 ASSUMPTION-77/78/79의 상태가
갱신된다(네 번째 CI 축약 항목은 ASSUMPTION 없이 실측으로 닫는다).

### M1 — 정규화 식 확정 (측정 우선, 코드 나중)

1. `/tmp` 프로브를 테스트 가능한 형태로 옮겨, 후보 N1과 대안 2~3종을 **동일한 스윕**에 건다:
   고정 19 리그 · 스윕 A(252) · 스윕 B(72) · 스윕 C(81).
2. 각 후보에 대해 **판정이 바뀌는 리그를 전수 열거**한다(REQ-AXISCORE-019).
3. 스케일 불변성을 후보별로 직접 측정한다: 축별 ×0.1 / ×10 / 전축 ×100.
4. 승자를 고르고, **고르지 않은 후보의 탈락 이유를 숫자로** 남긴다.

**게이트**: 승자가 고정 19 리그 전부와 스윕 A 252건을 배제 규칙 없이 보존하지 못하면 **M2로 넘어가지
않는다** — ASSUMPTION-76 NEGATIVE로 판정하고 §E 위험 1의 축소 경로를 탄다.

### M2 — 정규화 착지 (배제 규칙은 아직 그대로)

`_axis_buckets` · `_compute_depth` · `_compute_bilateral`의 **점수 산출만** 교체한다. 배제 규칙은
**손대지 않는다.** 이 시점에서 스위트는 GREEN이어야 한다 — 배제 규칙이 여전히 있으므로 리그 #17도 통과한다.

이 단계에서 이미 닫히는 것(`research.md` §A.2): 스케일 의존 1건 · 링 오독 2종. **배제 규칙 삭제가
실패해도 이 이득은 남는다.**

**게이트**: 전체 스위트 기준선(`4716 passed · 7 skipped`) 유지 + `rows.py`·`schema.py`·`naming.py`
byte-diff 0.

### M3 — 규칙 삭제 (1차 AC)

`topology.py:442-462`(`@MX:ANCHOR` 블록) · `:463`(`depth_partitions`) · `:469-470`을 삭제하고
`vertical`을 무조건 `contenders`에 넣는다.

**게이트**: `AC-AXISCORE-001` — 위상 코퍼스 60 테스트 전부 GREEN. 여기서 RED가 나면 그 리그가
ASSUMPTION-76의 반례이므로 M1로 되돌아간다.

### M4 — 현상 결속 테스트 (함정 방어)

`test_topology.py`에 추가한다:

1. **스케일 불변 스윕** — 리그 × 축 × 배율(0.1 / 1 / 10 / 100)의 매개변수화. 오늘 실패하는
   `golden_vertical_levels z×0.1`을 명시 케이스로 포함.
2. **행×트림 스윕** — `rows∈{2,3,4,5} × cols∈{3,5,8} × trims∈{2,3} × ypitch∈{1,3,6} × zgap∈{0.5,2,4,10}`.
   252건 전수는 CI 비용이 크므로 **대표 부분집합 + 경계값**으로 축약하되, 축약 근거를 docstring에 남기고
   전수 스윕은 재현 스크립트로 보존한다.
3. **분할 품질 단정** — `[1,2,2,…]` 대 `[6,12]`의 순위가 링 반지름 간격과 무관하게 유지된다.
4. **공통 구간 단정** — 전 리그 전 축의 점수가 닫힌 구간 안.
5. **동점 전순서 단정** — `three_rows_two_trims`·`electrics_three_bars`에서 두 점수가 **정확히 같음**을
   먼저 단정하고, 그 위에서 승자를 단정한다. (점수가 같다는 사실 자체가 비공허성 증거다.)

**게이트**: 뮤테이션 4종 각각 RED(REQ-AXISCORE-018).

### M5 — 판정 변경 리그의 문서화

M1에서 열거한 변경 리그를 `progress.md`에 전수 기록하고, 각각 새 판정이 옳은 이유를 적는다. 오늘 알려진
세 무리: 평면 격자 30/72 · 링 오독 정정 2건 · `_golden_bilateral` 1건.

**게이트**: 열거되지 않은 판정 변경이 0건임을 스윕으로 확인.

## D. `[NEEDS CLARIFICATION]` — 사람이 결정해야 하는 것

### `[NEEDS CLARIFICATION: 평면 격자에서 lateral과 vertical 중 무엇이 이겨야 하는가]`

y에 깊이가 없는 `cols × trims` 격자에서 두 축은 **대칭적 가설**이다. 오늘은 물리적 갭이 큰 축이 이기고,
그래서 같은 리그도 `zgap`을 바꾸면 판정이 뒤집힌다. 정규화 후 **30 / 72 리그**의 판정이 바뀐다
(18건 `lateral`→`vertical`, 12건 반대 — `research.md` §7.3).

코퍼스가 고정하는 것은 `_golden_vertical_levels` 1종뿐이고 후보 N1은 그것을 맞힌다. 나머지 29건에
**정답이 없다.** 필요한 결정: (a) 최소 버킷 몫으로 결정 + 동점은 전순서(N1 현행), (b) 평면 리그에서는
`vertical`을 항상 선호(트림은 눈에 보이는 구조라는 도메인 근거), (c) 둘 다 확신이면
`low_confidence` 반환. ASSUMPTION-77.

### `[NEEDS CLARIFICATION: 동점 전순서가 배제 규칙의 정당한 후계인가]`

본 SPEC은 배제 규칙을 지우고 그 자리에 **동점일 때만 발화하는 축 전순서**를 남긴다. 성질은 다르다
(`spec.md` §A.4 비교표): 배제는 더 높은 후보를 제거하고, 전순서는 대등한 후보 중 고른다. 그리고 그
순서는 오늘 안정 정렬이 이미 암묵적으로 쓰고 있다.

그래도 이것은 **여전히 도메인 선호**다. 필요한 결정: 이 축소를 수용하는가, 아니면 depth 선호를 정규화
항으로 흡수해야 하는가(후자면 ASSUMPTION-76 재측정). ASSUMPTION-78.

### `[NEEDS CLARIFICATION: 오늘 depth_rows로 나오는 2겹 링 2종의 정답]`

`6@r=3.0 + 8@r=5.0` · `6@r=3.0 + 12@r=5.0`이 오늘 `depth_rows`로 분류된다 — 이 SPEC 계열의 창립 오독과
같은 형상이다. 정규화 후 `concentric`이 된다. 도메인 확인이 필요하다: 안쪽 반지름 3.0 · 바깥 5.0의
2겹 링은 `concentric`이 맞는가, 아니면 두 링이 너무 가까워 `low_confidence`가 정직한 답인가.
ASSUMPTION-79.

### `[NEEDS CLARIFICATION: 252 리그 스윕의 CI 축약 기준]`

전수 스윕은 CI에서 매번 돌리기에 크다. 대표 부분집합으로 줄이면 **다시 "형상에 고정"되는 것 아닌가**가
문제다. 필요한 결정: (a) 전수를 `slow` 마커로 분리하고 CI는 부분집합, (b) 전수를 그대로 돌리되 리그
생성을 경량화, (c) 경계값 + 무작위 시드 고정 샘플. 실측 필요: 252 리그 전수의 실제 소요 시간.

## E. 위험

### 위험 1 — 정규화가 배제 규칙을 완전히 대체하지 못한다 (ASSUMPTION-76 NEGATIVE)

**징후**: M1 게이트에서 어떤 후보도 고정 19 리그 + 스윕 A를 동시에 보존하지 못한다.

**대응**: 배제 규칙 삭제를 **재개방**하고 정규화만 착지시킨다(M2까지). 그래도 스케일 의존 1건과 링 오독
2종은 닫히므로 순이득이다. 이 경우 SPEC의 `status`는 `partial`로 내리고 남은 부채를 다시 기록한다 —
**"고쳤다"고 적지 않는다.** 이 SPEC이 존재하는 이유가 바로 그렇게 적힌 부채이기 때문이다.

### 위험 2 — 판정 변경이 스윕 밖에 숨어 있다

**징후**: 알려진 세 무리(평면 30 · 링 2 · bilateral 1) 외의 리그에서 조용히 판정이 바뀐다.

**대응**: M5의 게이트가 이것을 잡는다 — 스윕을 리그 생성기로 넓혀 "열거되지 않은 변경 0건"을 단정한다.
`[INFERENCE]` 리그 공간은 무한하므로 이 게이트는 **스윕 범위 안에서만** 보증한다. 범위를 문서에 명시한다.

### 위험 3 — 테스트가 다시 형상에 고정된다

**징후**: 새 테스트가 `three_rows_two_trims` 하나에 다시 걸린다.

**대응**: REQ-AXISCORE-017이 이를 금지하고 M4가 강제한다. 이 저장소는 같은 이유로 같은 결함을 **두 번**
놓쳤다(`GROUPGEN progress.md:778-779`) — 그 기록이 이 위험의 근거다.

### 위험 4 — `min_bucket_size / n`이 중간 분포를 못 본다

**징후**: `[5,5,5]`와 `[5,4,6]`이 구분되지 않는 리그가 실전에서 나온다.

**대응**: M1에서 대안 항(예: 버킷 크기 분포의 정규화 엔트로피, 최소 버킷 대 균등 몫 비)을 같은 스윕에
걸어 비교한다. 실측 리그에서는 아직 문제가 관측되지 않았다 — 이 위험은 `[INFERENCE]`다.

### 위험 5 — CI 시간

**징후**: 스윕이 스위트 시간을 눈에 띄게 늘린다.

**대응**: `[NEEDS CLARIFICATION: 252 리그 스윕의 CI 축약 기준]`이 이 결정을 담당한다. 참고: 현재 전체
스위트는 **97.56s**이고 위상 테스트 60건은 **0.2s**다 — 여유는 있으나 측정 후 결정한다.

## F. 검증 계획

| 단계 | 명령 | 기대 |
|---|---|---|
| 단위(빠름) | `uv run --frozen pytest server/tests/test_topology.py server/tests/test_topology_naming_seam.py -q` | 60 + 신규 전부 GREEN |
| 인접 회귀 | `uv run --frozen pytest server/tests/test_groupgen_tools.py server/tests/test_groupgen_write.py server/tests/test_groupgen_choreography_seam.py server/tests/test_naming.py server/tests/test_spatial_analysis.py -q` | 기준선 234 GREEN |
| 전체 | `uv run --frozen pytest -q` | `4716 passed · 7 skipped` + 신규 (M3 이후 1회) |
| 뮤테이션 | 정규화 식 4항목 각각 되돌리기 | 각각 명명된 테스트 RED |
| 경계 | `git diff --stat -- server/spatial/rows.py server/spatial/schema.py server/spatial/naming.py` | **공백** |
| 린트 | `uv run ruff check server/spatial/topology.py server/tests/test_topology.py` | 신규 지적 0 |

전체 스위트는 **M2 게이트와 M3 게이트에서 각 1회**만 돌린다(97.56s).
