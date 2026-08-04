# SPEC-COPILOT-GROUPGEN-001 — 설계 (design)

status: **draft v0.1.0** · 2026-08-03 · plan-phase 워커 A 작성 · 소스 코드 변경 0

> 본 문서는 `.moai/specs/SPEC-COPILOT-GROUPGEN-001/.plan-contract.md`(고정 계약)를 따른다.
> 계약과 상충하는 서술은 이 문서의 오류다. 근거는 `research.md`(v0.5.0) · `spec.md`(v0.1.0) ·
> `plan.md`(v0.1.0)이며, `[실측]`은 라이브 onPC 2.4.2 직접 관측이므로 구속력을 갖는다.
> **`ok:true`는 어디에서도 증거로 쓰지 않는다 — 재조회만이 증거다.**

## HISTORY

| version | date | 변경 |
|---|---|---|
| 0.1.0 | 2026-08-03 | 초안. §1~§12 신설 |

---

## §1. 3층 분업 — 그룹 · 선택순서 · MAtricks

이 SPEC이 만드는 것과 만들지 않는 것을 구분하는 가장 중요한 경계다. 후속 작업이 이 표를 놓치면
MAtricks를 그룹으로 재구현하려 든다(함정 16).

```
GROUPGEN 그룹    = 누구를       (영속 · 이름 있음 · 콘솔에서 손으로도 쓸 수 있음)
SPATIAL 선택순서  = 어떤 순서로   (런타임 · `ClearAll`로 사라짐 · 방향을 만든다)
MAtricks         = 어떻게 재성형 (런타임 · 윙 · 블록 · 홀짝 · 셔플 · 미러)
```

| 층 | 소유 SPEC | 영속성 | 산출 |
|---|---|---|---|
| **그룹 (누구)** | 본 SPEC(GROUPGEN-001) | **영속** — 쇼파일에 저장, `ClearAll` 영향 없음 | `Group <n>` (예: `GEO Downstage`) |
| **선택 순서 (어떤 순서로)** | SPATIAL-001 (`choreography.py::build_spatial_selection_chain`) | 런타임 — 매 발화가 재구성 | 픽스처 선택 시퀀스 |
| **재성형 (어떻게)** | MAtricks (MA3 기존 기능) | 런타임 — 선택 위의 변형 | Wings/Block/Group/Shuffle/Mirror |

**경계 규칙**: `topology.py`와 `naming.py`는 위상을 분류하고 이름을 고를 뿐, **그 어떤 재성형도 수행하지
않는다.** `bilateral_pairs`는 이 경계의 리트머스 시험지다 — 대칭은 **속성**으로 보고되고,
`Mirror`/`Pan Invert`로 재성형하는 것은 MAtricks의 일이지 그룹의 일이 아니다(§5.3 D-Q10 계승).

**과약속 금지**: 정직한 약속은 *"연출에 쓸 수 있는 형태로 위치 그룹을 만들어 둔다"*이며,
*"연출 의도를 자동 해석한다"*가 아니다(계약 §6.5).

---

## §2. `server/spatial/topology.py` — 위상 6종 검출 설계

### §2.1 순수성 경계

`topology.py`는 **transport(`server.bridge`/`pythonosc`) import 0, 게이트 import 0**이다
(REQ-GROUPGEN-006). 입력은 이미 판독된 픽스처 좌표 목록뿐이며, 콘솔에 접촉하지 않는다.
`server/tests/test_architecture.py`의 전역 스캔에 자동 포섭되고 예외 명단을 추가하지 않는다.

### §2.2 입력·출력 스키마

```python
# server/spatial/topology.py

from dataclasses import dataclass
from server.spatial.schema import SpatialFixture  # 기존 좌표 스키마 재사용 (PRESERVE)

TopologyKind = Literal[
    "depth_rows", "lateral_split", "concentric",
    "vertical_levels", "grid", "bilateral_pairs", None,
]

@dataclass(frozen=True)
class TopologyResult:
    """단일 위상 후보에 대한 판정 — 위상별로 하나씩 생성되고, 경합 규칙(§2.4)이 최종 선택을 고른다."""
    kind: TopologyKind
    # 단일 축 판정의 버킷. 버킷 순서 = 명명 순서(§4가 소비).
    # `kind == "grid"` 일 때는 **반드시 빈 튜플**이며 축별 버킷은 `grid_axes`가 싣는다.
    fids_by_bucket: tuple[tuple[int, ...], ...]
    low_confidence: bool
    reason: str | None = None  # low_confidence=True일 때 왜 뚜렷하지 않은지
    # grid 전용 필드. `kind == "grid"` 일 때만 not-None이며, 그 외 위상에서는 항상 None.
    # 축 키는 폐쇄 집합이고 값의 버킷 순서는 각 축의 명명 순서다(depth: DS→US, lateral: SR→SL).
    grid_axes: Mapping[Literal["depth", "lateral"], tuple[tuple[int, ...], ...]] | None = None

    # [HARD] 타입 불변식 — M1/M2 병렬의 교차 계약이며 M1이 단위 테스트로 고정한다:
    #   kind == "grid"  <=>  fids_by_bucket == () and grid_axes is not None
    #   kind != "grid"  <=>  grid_axes is None
    # 같은 필드가 두 타입을 갖는 일은 없다. `naming.py`는 `kind`로 분기해
    # grid면 `grid_axes`만, 그 외면 `fids_by_bucket`만 읽는다(§4).

@dataclass(frozen=True)
class TopologyClassification:
    """`classify()`의 최종 반환 — 경합 해소 후 단 하나의 위상(또는 None)."""
    selected: TopologyResult
    candidates: tuple[TopologyResult, ...]  # 감사·golden 비교용 — 모든 축의 원 판정 보존


def classify(fixtures: tuple[SpatialFixture, ...]) -> TopologyClassification: ...

# 개별 검출기 — 각각 순수 함수, 서로 독립적으로 단위 테스트 가능
def detect_depth_rows(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult: ...       # y축 갭
def detect_lateral_split(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult: ...    # x축 갭
def detect_concentric(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult: ...       # 중심으로부터 반지름 갭
def detect_vertical_levels(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult: ...  # z축 갭
def detect_grid(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult: ...             # y·x 양축 동시 유의
def detect_bilateral_pairs(fixtures: tuple[SpatialFixture, ...]) -> TopologyResult: ...  # x=0 대칭 쌍 — 신호만(§5.3 D-Q10)
```

`fids_by_bucket`의 버킷 순서는 명명 순서와 1:1 대응한다 — 예를 들어 `depth_rows`에서
`fids_by_bucket[0]`은 항상 downstage 버킷(가장 작은 y), 마지막은 upstage 버킷이다. `naming.py`는
이 순서 계약만 알면 되고 검출 알고리즘 내부를 알 필요가 없다(plan.md §E가 명시한 M1/M2 병렬 전제).

### §2.3 결정론 (REQ-GROUPGEN-002)

모든 검출기는 **같은 입력 → 같은 출력**을 반환한다. 갭 클러스터링은 `rows.py`의 기존 y축 알고리즘을
편입하며(REQ-GROUPGEN-005 — 대체 아님), 나머지 축(x·z·반지름)은 동일한 갭-클러스터링 원리를
**표준 `math`만으로** 재사용한다(원문: 정렬 후 인접 간격의 이상치 검출). 신규 런타임 의존성 0
(REQ-GROUPGEN-007 — SPATIAL §C.1 계승, sklearn·numpy 클러스터링 라이브러리 금지).

반지름·각도 계산은 `math.hypot(x, y)`(반지름) · `math.atan2(y, x)`(각도, `concentric` 세부 판정이
필요할 경우) 만으로 충분하다 — 표준 라이브러리 밖으로 나가지 않는다.

동률·모호 상황은 임의 선택(예: 사전순 · 처리순)이 아니라 **명시 신호**로 처리한다 — 두 위상이
동시에 근접 유의하면 `low_confidence=True` + `reason`에 경합 축을 명시한다. SPATIAL
REQ-SPATIAL-010의 규율을 계승한다.

### §2.4 경합 규칙 (계약 D-Q2)

y축과 x축이 **동시에 유의**하면(예: 3×10 그리드), `classify()`는 위상을 `grid`로 **판정**하되
**산출 그룹은 축별로 분리**한다:

```
grid 판정 → 산출 = depth_rows 3버킷(Downstage/Center/Upstage)
                  + lateral_split 3버킷(Stage Right/Centerline/Stage Left)
                  (9칸 교차 그룹은 만들지 않는다 — 계약 §1 D-Q2)
```

경합 규칙 알고리즘:

1. `detect_depth_rows`와 `detect_lateral_split`을 **둘 다** 실행한다.
2. 두 결과 모두 `low_confidence=False`이고 버킷 수 ≥ 2이면 → `kind="grid"`로 판정하고,
   축별 버킷을 **`grid_axes`** 에 담는다(`fids_by_bucket`은 `()` — §2.2 불변식).
   `naming.py`는 `kind == "grid"`를 보고 `grid_axes["depth"]`·`grid_axes["lateral"]`을 각각
   명명해 6개 이름(`Downstage`/`Center`/`Upstage` + `Stage Right`/`Centerline`/`Stage Left`)을
   도출한다. **`fids_by_bucket`에 딕셔너리를 넣지 않는다** — 한 필드에 두 타입을 두면
   M1/M2 병렬이 의존하는 스키마 계약이 깨진다.
3. 한 축만 유의하면 → 그 축 하나(`depth_rows` 또는 `lateral_split`)만 선택된다.
4. 어느 축도 뚜렷하지 않으면 → `kind=None`, `low_confidence=True`.

9칸 복합 명명(`DSR…USL`)은 **`naming.py`에 폐쇄 어휘로 정의되지만 v1은 호출하지 않는다**(§4.3) —
삭제가 아니라 미발화다.

### §2.5 golden 시나리오 (M1이 만들 픽스처)

| golden | 배치 | 기대 판정 |
|---|---|---|
| 1×N 바 | y만 갭 분리, x·z 균일 | `depth_rows` |
| 3×10 그리드 | y·x 둘 다 갭 분리 | `grid` (분리 산출) |
| **2겹 동심원**(내륜 6대 r=2.0 · 외륜 12대 r=5.0) | y축 갭 없음, 반지름 완벽 이분 | `concentric` — **`depth_rows`가 아니어야 한다**(§3) |
| 좌/우 2분할 | x만 갭 분리 | `lateral_split` |
| 3층 수직 | z만 갭 분리 | `vertical_levels` |
| 불규칙(무작위 산포) | 어느 축도 뚜렷하지 않음 | `kind=None`, `low_confidence=True` |
| 전대 동일좌표(모두 원점) | 갭 계산 불능(분산 0) | `kind=None`, `low_confidence=True` |
| x=0 대칭 배치 | 좌우 대칭 쌍 존재 | `bilateral_pairs` 신호(그룹 미생성 — §5.3) |

---

## §3. 비공허성 설계 — 2겹 동심원이 `depth_rows`로 오독되지 않는 이유

`research.md` §3의 실측: 현재 `rows.py`는 2겹 동심원(내륜 6대 r=2.0 · 외륜 12대 r=5.0)에
`rows=9, low_confidence=False`를 답한다. 이는 **y축 갭 클러스터링 하나만** 갖고 모든 리그에
적용하기 때문이다 — 원주 위의 y좌표들이 우연히 9개의 갭을 만들고, 그 갭이 진짜로 존재하므로
저신뢰 신호조차 뜨지 않는다.

`topology.py`가 이 오독을 막는 메커니즘은 다음 세 가지의 **결합**이다:

1. **다중 가설 병렬 실행** — `classify()`는 y축 가설(`depth_rows`) **하나만**이 아니라 6개 검출기를
   모두 실행한다. 2겹 동심원 입력에서 `detect_concentric`은 반지름 `2.0`/`5.0`의 **완벽한 이분**을
   보므로 `low_confidence=False`로 뚜렷하게 응답하는 반면, `detect_depth_rows`가 보는 y축 갭은
   원주 위 좌표의 부산물일 뿐이다.
2. **경합 시 우선순위** — 여러 검출기가 동시에 `low_confidence=False`를 반환할 때, `classify()`는
   **분산 설명력이 더 큰 축**(반지름 방향의 분리도가 y축 갭보다 명확할 때)을 우선한다. golden
   시나리오(§2.5)가 이 우선순위를 **고정**한다: 동심원 golden이 `depth_rows`로 나오면 회귀다.
3. **golden이 서로를 구별해야 한다는 계약** — REQ-GROUPGEN-003이 명시적으로 요구한다. 위상별
   golden 스위트가 서로 다른 위상을 산출하지 못하면 "항상 `depth_rows`"를 답하는 분류기가
   테스트를 통과하게 되므로, **동심원 golden의 기대값이 `concentric`인 단위 테스트 자체가
   비공허성의 증거**다. 이 테스트가 없으면 §3의 실측 결함이 조용히 재발한다.

즉 비공허성은 "더 똑똑한 알고리즘 하나"로 보장되지 않는다 — **경쟁하는 다중 가설 + 그 경쟁을
검증하는 golden 세트**로 보장된다. `detect_concentric`이 `detect_depth_rows`보다 반지름 분리도가
높다고 판단하는 구체적 임계값(갭/평균간격 비율 등)은 M1 구현 세부이며, 여기서 고정하는 것은
**계약**(golden이 이겨야 한다)이지 임계값 자체가 아니다.

---

## §4. `server/spatial/naming.py` — 명명 어휘 설계

### §4.1 폐쇄 어휘표 (계약 §5 — 문자 그대로 일치)

| 축 | 2분할 | 3분할 | 4+ 폴백 |
|---|---|---|---|
| 깊이 | `Downstage` / `Upstage` | + `Center` | `Electric 1..N` (**DS→US**) |
| 좌우 | `Stage Right` / `Stage Left` | + `Centerline` | (미정 — 아래 §4.2) |
| 동심원 | `Inner` / `Outer` | + `Mid` | `Ring 1..N` (**안→밖**) |
| 수직 | `Low Side` / `High Side` | — | `Level 1..N` (**위→아래**) |
| 그리드 | 축별 분리(D-Q2) | 축별 분리 | 축별 분리 |
| 종류 | 패치 구조화 필드 그대로 | — | — |

모든 자동 생성 그룹 이름은 `"GEO "` 접두를 갖는다(D-Q3). 예: `GEO Downstage` · `GEO Ring 2` ·
`GEO Stage Left` · `GEO Robe Robin MMX Spot`.

### §4.2 좌우 4+ 폴백 — 미정 방향 명시

계약 §5는 좌우 축 4+ 폴백을 "미정 — design이 방향 명시"로 남겼다. `research.md` §7.1의 붐 번호
관례(*"SR Boom #1 is the downstage boom on stage right"*)를 좌우 축에 적용하면, 좌우 4+ 분할은
**측면 접두 + downstage부터 번호**가 표준형이다:

```python
def _lateral_fallback_name(side: Literal["right", "left"], index: int) -> str:
    """4+ lateral_split fallback — side prefix + downstage-first numbering.

    e.g. "GEO SR Boom 1" (stage-right, downstage-most) .. "GEO SR Boom N"
         "GEO SL Boom 1" (stage-left, downstage-most) .. "GEO SL Boom N"
    """
```

`SR`/`SL` 접두는 stage 기준을 이름에 박아 house 기준과의 충돌(§4.4)을 원천 차단한다.
번호는 §2.2 버킷 순서 계약에 따라 downstage(가장 작은 y)부터 1로 매긴다 — `Electric 1..N`과
동일한 방향 규율(DS→US)을 좌우 축에도 일관 적용한다.

### §4.3 깊이 vs 좌우 Center 충돌 회피

깊이 축과 좌우 축이 동시에 3분할될 때(D-Q2 grid 경합) `Center`라는 동일 문자열이 **서로 다른
픽스처 집합**을 가리키는 충돌이 생긴다. 코드 구조로 이를 표현한다:

```python
def name_depth_bucket(index: int, total: int) -> str: ...   # -> "GEO Downstage" | "GEO Center" | "GEO Upstage" | "GEO Electric N"
def name_lateral_bucket(index: int, total: int) -> str: ...  # -> "GEO Stage Right" | "GEO Centerline" | "GEO Stage Left"
```

**두 함수는 별도 심볼이며, 좌우 축의 중앙은 `name_depth_bucket`이 반환하는 `"Center"`가 아니라
`name_lateral_bucket`이 반환하는 `"Centerline"`이다.** 이 구분은 함수 시그니처 층위에서
강제되므로, grid 경합 산출 시 `name_depth_bucket(1, 3)` = `"GEO Center"`와
`name_lateral_bucket(1, 3)` = `"GEO Centerline"`이 동시에 나와도 **문자열 충돌이 없다**.

### §4.4 9칸 어휘 — 정의하되 v1 미발화

```python
# 폐쇄 집합으로 정의됨 — v1의 어떤 검출·명명 경로도 이 심볼을 호출하지 않는다.
GRID_9CELL_VOCAB: tuple[str, ...] = (
    "DSR", "DSC", "DSL",   # Downstage Right/Center/Left
    "CSR", "CS", "CSL",    # Center-stage Right/Center/Left
    "USR", "USC", "USL",   # Upstage Right/Center/Left
)

def name_grid_9cell(depth_idx: int, lateral_idx: int) -> str:
    """정의는 하되 v1 어떤 호출자도 이 함수를 호출하지 않는다 (D-Q2 — 슬롯 경제).
    9칸 복합 명명이 업계 표준임(research §6.4)을 삭제 없이 기록하는 것이 목적이며,
    미래에 슬롯 여유가 생기거나 사용자가 9칸을 명시 요청하면 재활성화 지점이 된다."""
```

`classify()`의 grid 경합 분기(§2.4)는 `name_grid_9cell`을 호출하지 않고 `name_depth_bucket`
+ `name_lateral_bucket`만 호출한다 — 함수는 존재하되 그래프에서 도달 불가(dead-but-defined,
삭제 아님).

### §4.5 stage vs house 함정 — 확정 근거

`research.md` §6.1(MA Lighting 공식 문서): MA3는 **+x = stage left**로 정의한다. stage 기준
(연기자 기준)과 house 기준(객석 기준)은 정반대다. `naming.py`는 이 부호 규약을 단일 지점에
고정한다:

```python
STAGE_LEFT_IS_POSITIVE_X = True  # MA Lighting 공식 문서 — research.md §6.1
```

`lateral_split`의 양(+) 버킷은 `Stage Left`, 음(−) 버킷은 `Stage Right`로 명명한다. 이름에
"house"를 쓰지 않는다 — 계약 §5 폐쇄 어휘 어디에도 `house`가 없다.

### §4.6 라벨 길이 상한 — 미검증

라벨 길이 제약은 실측되지 않았다(계약 §1 D-Q3). `naming.py`가 생성하는 최장 이름
(`GEO Stage Right Robe Robin MMX Spot` 같은 위상×종류 조합 없음 — 교차는 v1 제외되므로 실제
최장은 `GEO SR Boom 12` 류)의 길이는 M0 프로브에서 실측 확인한다(§9 P1a 신설).
`design.md`는 이 사실을 명시적으로 기록하며, 검증 전까지 `naming.py`는 길이 절단·검증 로직을
갖지 않는다 — 미검증 전제를 조용히 가정하지 않는다.

---

## §5. 종류 축 — 제조사·타입명 (2-hop, 구조화 필드 그대로)

### §5.1 2-hop 경로

```python
# server/spatial/topology.py 또는 별도 server/spatial/fixture_type.py (naming.py와 분리 — 명명 어휘가 아니라 판독 로직이므로)

@dataclass(frozen=True)
class FixtureTypeInfo:
    """픽스처 1대의 종류 정보 — 2-hop 판독 결과."""
    fid: int
    fixturetype_ref: str      # 예: 'FixtureType 1' — 패치 오브젝트의 fixturetype 필드 그대로
    type_name: str            # Patch/FixtureTypes/<n>.name — 예: 'Robin MMX Spot'
    short_name: str           # Patch/FixtureTypes/<n>.ShortName — 예: 'RMMXSm1'
    manufacturer: str         # Patch/FixtureTypes/<n>.Manufacturer — 예: 'Robe'

def resolve_fixture_types(
    fixtures: tuple[SpatialFixture, ...],
    *, query_fn: Callable[[str], dict],  # server.bridge 계층 주입 — topology 자체는 여전히 transport import 0
) -> tuple[FixtureTypeInfo, ...]: ...
```

**구조화 필드 문자열 가공 0** — `type_name` · `short_name` · `manufacturer`는 패치가 반환한 값을
그대로 옮긴다. 어떤 파싱·분리·정규화도 하지 않는다(REQ-GROUPGEN-009).

`query_fn` 주입은 §2.1의 순수성 경계(`topology.py` 자체는 transport import 0)를 지키면서도
2-hop 판독을 가능하게 하는 설계다 — 실제 판독은 `resolve_fixture_types`를 호출하는 상위 계층
(툴 표면, §8)이 `query_fn`으로 `server.bridge` 클라이언트를 주입한다. `topology.py`는 이미
판독된 `FixtureTypeInfo` 튜플만 받아 분류한다.

### §5.2 카테고리 토큰 매칭 — v1 범위 밖 (계약 D-Q9 반영)

계약 §1 D-Q9/Q11에 따라 업계 카테고리(`Spot`/`Wash`/`Beam`/`PAR`/`Fresnel`/`Profile`/`Strobe`/
`Blinder`/`Effect`/`Follow Spot`) **폐쇄 어휘 토큰 매칭은 v1 범위 밖**이다. GDTF 스펙
FixtureType 노드에 `Categories` 필드가 없어(research §7.3.2, gdtf.eu Table 3) 타입명 문자열이
유일한 근거이며, 이는 추측이다.

v1이 만드는 것은 **제조사·타입명 그룹뿐**이다:

```python
def group_by_manufacturer(infos: tuple[FixtureTypeInfo, ...]) -> dict[str, tuple[int, ...]]:
    """manufacturer 값 그대로 그룹핑 — 문자열 가공 0."""

def group_by_type_name(infos: tuple[FixtureTypeInfo, ...]) -> dict[str, tuple[int, ...]]:
    """type_name 값 그대로 그룹핑 — 문자열 가공 0."""
```

카테고리 토큰 매칭 함수·`Blinder` 분리 규칙·교차 폭발 제어는 **본 설계에 포함하지 않는다** —
REQ-010/011/012/027이 §D 이관 대상이며(spec.md 개정은 Task C 소유), 축이 v1에 없으므로 설계할
대상 자체가 없다. 카테고리 축이 복원되면(별도 SPEC) REQ-012(Blinder 분리)가 선결 조건이라는
연쇄는 계약이 이미 기록했다.

### §5.3 위상 × 종류 교차 — 미구현

계약 D-Q9에 따라 교차 그룹(`Upstage Wash` 류)은 v1에서 **만들지 않는다**. `naming.py`는 위상
버킷 이름과 종류 그룹 이름을 각각 독립적으로 생성할 뿐, 둘을 곱하는 함수를 갖지 않는다 —
교차를 만들지 않으므로 상한 로직도 필요 없다(계약 §1 D-Q9 근거 그대로).

### §5.4 동종 리그 — 산출 0 (REQ-GROUPGEN-030)

`Patch/FixtureTypes` childCount가 1이면(실측: 본 리그가 정확히 이 경우), `group_by_manufacturer`
· `group_by_type_name` 모두 **정확히 하나의 그룹**(전체 리그)만 반환한다. 이는 결함이 아니라
정직한 보고다 — 종류 축이 나눌 것이 없다는 사실 자체를 M6 라이브 판정에 `SKIP: CONDITION_NOT_MET`
행으로 남긴다(§9).

---

## §6. 그룹 쓰기 경로 — 슬롯 실측 + 발화 사슬 + 정적 단언

### §6.1 슬롯 실측 — `_select_cue_number` 패턴 계승

`server/scene/compile.py:243` (`_select_cue_number`, 실제 확인됨)의 3단 방어를 그대로 계승한다:

```python
# server/scene/compile.py (실제 코드, PRESERVE — 읽기 참조만)
def _select_cue_number(cues_section: Mapping[str, object], *, requested: int | None = None) -> int:
    unavailable = cues_section.get("reason")
    if isinstance(unavailable, str) or cues_section.get("ok") is False:
        raise SceneCompilationError(CUE_SECTION_UNAVAILABLE, "...")
    if cues_section.get("truncated"):
        raise SceneCompilationError(CUE_TRUNCATED, "...")
    occupied = _cue_numbers(cues_section)
    ...
```

`server/safety/**` 또는 그룹 쓰기 모듈(호출부, §7이 다룸)에 이 패턴을 **그룹 슬롯**용으로
재구현한다(같은 파일을 import하지 않는다 — 큐 도메인과 그룹 도메인은 다른 오류 코드 체계를 갖는다):

```python
class GroupSlotError(Exception):
    """그룹 슬롯 선택 실패 — 오류 코드 2종."""

GROUP_POOL_TRUNCATED = "GROUP_POOL_TRUNCATED"     # 재조회 풀이 절단됨 → 할당 거부
GROUP_SLOT_OCCUPIED = "GROUP_SLOT_OCCUPIED"       # 대상 슬롯이 이미 점유됨 → 정적 차단

def select_group_slot(groups_section: Mapping[str, object], *, requested: int) -> int:
    """빈 그룹 슬롯을 재조회 풀에서 실측한다. 번호를 세지 않는다.

    _select_cue_number(server/scene/compile.py:243)의 문면을 그룹 도메인에 계승:
    절단이면 자동 할당을 거부한다 — 보이지 않는 슬롯이 후보 번호를 점유할 수 있다.
    """
    if groups_section.get("truncated"):
        raise GroupSlotError(
            GROUP_POOL_TRUNCATED,
            "the group pool listing was truncated, so an unlisted group may hold "
            "any candidate number; automatic assignment is refused",
        )
    occupied = _group_numbers(groups_section)  # 재조회 풀에서 실측 — REQ-GROUPGEN-020
    if requested in occupied:
        raise GroupSlotError(
            GROUP_SLOT_OCCUPIED,
            f"group {requested} is already occupied; group writes never target an "
            "existing slot (membership cannot be read back for backup — research.md §2.1)",
        )
    return requested
```

`_select_cue_number`와의 결정적 차이: 큐 도메인은 `candidate = 1; while candidate in occupied`로
**빈 번호를 자동 계산**하지만, 그룹 도메인은 계약 §2 D-Q6(절단 리그 정책=거부)에 더해
`GROUP_SLOT_OCCUPIED`가 예외이지 않고 **정적 차단**이라는 점에서 더 엄격하다 — 점유 슬롯은
읽지도 쓰지도 않는다(계약 §6 금지 4).

### §6.2 발화 사슬

```
ClearAll
  → build_spatial_selection_chain(fixture_fids)   # SPATIAL choreography.py 재사용 — PRESERVE
  → Store Group <n>
  → Label Group <n> '<name>'
  → ClearAll
```

`build_spatial_selection_chain`은 SPATIAL-001이 이미 검증한 선택 발화 조립기이며, 본 SPEC은
그 출력을 소비만 한다(수정 0). `Store Group <n>`과 `Label Group <n> '<name>'`은 `00_grammar.md:66`
문법을 따르되 **"(validated)" 표기가 없으므로**(계약 §1 D-Q4, ASSUMPTION-63/64) M0 P3/P4가
라이브로 검증한다.

### §6.3 절단 거부 오류 코드

`GROUP_POOL_TRUNCATED`(§6.1)이 **그룹 풀**(빈 슬롯 목록) 절단을, 다음 오류 코드가 **픽스처
목록**(그룹에 담을 대상) 절단을 다룬다 — REQ-GROUPGEN-021과 REQ-GROUPGEN-024는 계약에 따라
같은 등급으로 통일된다(D-Q6):

```python
FIXTURE_LIST_TRUNCATED = "FIXTURE_LIST_TRUNCATED"  # 대상 픽스처 목록이 절단됨 → 그룹 생성 거부

def guard_fixture_list_truncation(fixtures_section: Mapping[str, object]) -> None:
    """18/19만 담긴 그룹은 조용히 틀린 자산으로 영속한다(research §5.2) — 절단이면 거부한다.

    선택은 ClearAll로 사라지지만 그룹은 남는다는 비대칭이 이 거부를 강제한다(함정 7).
    """
    if fixtures_section.get("truncated"):
        raise GroupSlotError(
            FIXTURE_LIST_TRUNCATED,
            "the fixture list to be grouped was truncated, so an incomplete group "
            "would silently persist as a wrong asset; automatic grouping is refused",
        )
```

`SceneCompilationError`의 문면 형식(오류 코드 + 사람이 읽는 이유 문자열)을 그대로 계승한다
(계약 §2 D-Q6).

### §6.4 점유 슬롯 정적 차단

`select_group_slot`의 `GROUP_SLOT_OCCUPIED` 분기가 이를 담당한다. 이는 **협상 불가**다
(research §2.1) — 멤버십을 읽을 수 없으므로 백업이 불가하고, `Delete`는 블랙리스트, restore
SEND 경로가 없다(T-B2). 기존 그룹 슬롯 `1·11·12·13·15`는 이 함수가 **항상 거부**한다
(단위 테스트로 정적 단언 — §11).

### §6.5 범위 봉쇄 정적 단언

```python
def assert_write_scope(requested_slots: set[int], measured_empty_slots: set[int]) -> None:
    """발화 슬롯 집합 == 실측 빈 슬롯 집합. 기존 슬롯 접촉 0 (REQ-GROUPGEN-025)."""
    assert requested_slots <= measured_empty_slots, (
        f"write scope {requested_slots} exceeds measured empty slots {measured_empty_slots}"
    )
```

이 단언은 M5 회귀 스위트에서 **뮤테이션 필수** 항목이다(계약 대상 아니나 plan.md §B M5가 요구) —
가드를 제거하면 반드시 빨개져야 한다.

---

## §7. `server/safety/**` 게이트 확장 설계 (계약 D-Q4)

### §7.1 선례 계승 — EXECREF-001 패턴

`server/safety/classify.py:44`(실제 확인됨)의 `RECOGNIZED_REFERENCE_TYPES`가 선례다:

```python
# 기존 (server/safety/classify.py:44, PRESERVE)
RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence", "Executor")
```

`Executor`가 SPEC-COPILOT-EXECREF-001 M1에서 추가된 방식 — **닫힌 튜플에 원소 하나를 추가하고,
`@MX:NOTE`로 변경 근거를 남기는 것** — 을 본 SPEC이 그대로 계승한다. `RECOGNIZED_REFERENCE_TYPES`에
`"Group"`을 추가할지, 별도의 그룹 쓰기 참조 타입 인식 경로를 둘지는 M0 P7(게이트 분류 실측) 이후
확정한다(ASSUMPTION-66) — 여기서 고정하는 것은 **확장 지점의 형태**다:

```python
# 확장 후 (개정 대상 — server/safety/classify.py, 사용자 승인 획득된 유일한 소스 파일 변경)
RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence", "Executor", "Group")
```

### §7.2 경계 — 인식 + 분류에 한정

게이트 확장은 **그룹 쓰기 참조 타입 인식 + 위험도 분류**에 한한다(계약 §1 D-Q4). 다음은
**무변경 계승**이다:

- **3-stage screen** (`server/safety/gate.py` — grammar → risk classification → human approval)
- **expand-or-hold** (`server/safety/expand.py::evaluate_reference` — 본문 미검증 시 hold)
- **LiveLock** (`server/safety/gate.py` 락 재확인)
- **백업** (`server/safety/backup.py` — `before_risky_execution`)
- **감사 의미론** (`server/safety/audit.py`)

`Store Group <n>`(무플래그)은 블랙리스트 v1에 **없다**(research §5.4 실측) — ASSUMPTION-66이
GO/NEGATIVE를 가른다:

| ASSUMPTION-66 결과 | 게이트 분류 | 승인 카드 |
|---|---|---|
| `Store Group` = `risky` (분류됨) | 정규 승인 흐름 경유 | 카드 발행 |
| `Store Group` = `safe` (미분류) | **본 SPEC이 blacklist.yaml 또는 classify.py에 그룹 쓰기 명령을 명시 추가** | 카드 발행 강제 |

**함정 6 대응**: 툴 설명문은 지시일 뿐 강제가 아니다(SPATIAL의 "say so" 무시 사례). 승인 요구는
설명문이 아니라 **게이트 구조**로 강제된다 — 이것이 D-Q4가 이 선택지를 고른 이유다.

### §7.3 PRESERVE 경계 재확인

`server/safety/**`의 다른 모든 파일(`approval.py`·`audit.py`·`backup.py`·`bootstrap.py`·
`console.py`·`gate.py`·`grammar.py`·`lock.py`·`monitor.py`·`registry.py`·`ruleset.py`·
`session_context.py`)은 그룹 참조 타입 인식이 요구하는 최소 변경(위 `classify.py` 튜플 확장
+ 필요 시 `blacklist.yaml` 엔트리 추가) 외에는 **손대지 않는다**.

---

## §8. 툴 표면 — 정확히 2개 추가 (20 → 22)

계약 §5: 현재 **20**(`server/tests/test_tools.py:144` 실제 확인 —
`assert len(names) == len(TOOL_NAMES) == 20`). 본 SPEC은 **정확히 2개 추가 → 22**
(REQ-GROUPGEN-028 — 읽기/제안과 쇼파일 변형 분리, SPATIAL D-4 선례).

```python
# server/orchestrator/tools.py (개정 대상)

TOOL_NAMES = (
    ...,  # 기존 20개, 무변경
    "classify_arrangement_topology",   # ①읽기/제안 — 위상 분류 + 종류 분류 + 명칭 클러스터 제안을 반환
    "create_arrangement_groups",       # ②변형 — 쇼파일에 그룹 Store + Label (게이트 A·B GO 전제)
)
```

- **`classify_arrangement_topology`**: 읽기 전용. `topology.classify()` + `naming` 매핑 +
  `resolve_fixture_types` + 명칭 클러스터 감지(§4.6 계약 D-Q12 — 제안으로만)를 조합해
  구조화 결과를 반환한다. 콘솔 쓰기 0. 안전 게이트 경유 0(읽기이므로).
- **`create_arrangement_groups`**: 변형. §6의 발화 사슬을 실행한다. 안전 게이트(§7 확장분)를
  경유하며, 게이트 A(멤버십 판독) NEGATIVE 시 이 툴은 **제안 전용 강등**되어 발화 문자열만
  반환하고 콘솔에 아무것도 보내지 않는다(§10 게이트 A NEGATIVE 분기).

두 툴을 분리하는 이유는 승인 카드 분류가 흐려지지 않게 하기 위함이다(SPATIAL D-4 선례) — 읽기와
변형이 한 툴에 있으면 안전 게이트가 "이 호출이 위험한가"를 일관되게 판단할 수 없다.

`server/tests/test_tools.py:144`의 고정 테스트를 **22**로 갱신하는 것은 run-phase(M4) 작업이며,
본 design.md는 목표 개수만 고정한다.

---

## §9. M0 라이브 프로브 설계 — 발화 커맨드 구체화

정리 경로를 프로브 전에 확정한다(함정 21) — `Delete`가 블랙리스트이므로 **빈 슬롯 1개만**
표적으로 쓰고, 정리는 사용자 GUI 삭제 1건으로 끝나도록 설계한다. 표적 슬롯 후보: 실측 빈 슬롯
집합 `{2..10, 14, 16+}`(계약 §5) 중 **14**를 우선 후보로 고정한다(사전 결정 — 프로브 중 재선택 없음).

| # | 프로브 | 발화 커맨드 (구체) | 판정 |
|---|---|---|---|
| **P1** | 멤버십 채널 사다리 | `prop Group 13 Object` → `prop Group 13 Fixtures` → `prop Group 13 Content` → `prop Group 13 Count` → `prop Group 13 Members` → `prop Group 13 Selection` (실패마다 다음 후보로 진행) | ASSUMPTION-61 (게이트 A) |
| **P1a** *(신설 — 계약 §1 D-Q3)* | 라벨 길이 상한 | `Label Group 14 'GEO Stage Right Robe Robin MMX Spot Copilot Probe Extra Long Name Test'` (의도적으로 긴 문자열) → `prop Group 14 Name` 재조회로 절단 여부 확인 | §4.6 라벨 길이 상한 실측 |
| **P2** | 날조 대조군 | `prop Group 13 NotARealPropertyXYZ` (존재하지 않는 속성) → 실패해야 채널 변별적 | ASSUMPTION-62 |
| **P3** | 그룹 생성 | `Fixture 1 Thru 2` → `Store Group 14` → `prop Group 14 Name` 재조회 | ASSUMPTION-63 (게이트 B) |
| **P4** | 라벨 | `Label Group 14 'GroupgenProbe'` → `prop Group 14 Name` 재조회 → `'GroupgenProbe'` 확인 | ASSUMPTION-64 |
| **P5** | 멤버십 왕복 | P1이 채택한 채널로 `Group 14`의 멤버가 `{1, 2}`인지 재조회 확인 — 실패면 게이트 A NEGATIVE | ASSUMPTION-61 확정 |
| **P6** | 점유 슬롯 거동 | `Fixture 3 Thru 4` → `Store Group 14` (이미 점유된 14 재발화) → `prop Group 14 Name`/멤버십 재조회로 **조용히 덮였는지 vs 거부됐는지** 확인 | ASSUMPTION-65 (게이트 C) |
| **P7** | 게이트 분류 정적 확인 | (라이브 발화 없음) `server/safety/blacklist.yaml` + `classify.py` 정적 열람 — `Store Group`/`Label Group` 무플래그 형태가 어느 분류에 해당하는지 | ASSUMPTION-66 |
| **P8** | 정리 | `ClearAll` → 사용자 GUI로 `Group 14` 삭제(1건 허용) → `prop Group 14 Object` 재조회로 슬롯 원복 확인 | — |

산출물: 프로브 로그 · 판정 7건(P1a 추가로 계약 6건에서 확장) · 게이트 A~D 결정 ·
`progress.md §E.2`에 폐쇄 어휘 + 행두 접두로 기록(REQ-GROUPGEN-029). 미프로브 전제는
`SKIP: CONDITION_NOT_MET` 행을 받는다.

---

## §10. 게이트 조건부 분기 — GO/NEGATIVE 양 분기 서술

계약 §3의 표를 설계 관점으로 확장한다. **`ok:true`는 게이트 판정의 증거로 쓰지 않는다** — 아래
모든 GO 분기는 재조회 확인을 전제로 한다.

### 게이트 A — 멤버십 판독 채널

- **GO 분기** (P1/P5가 판독 가능한 채널을 찾음): `create_arrangement_groups`는 그룹 생성 후
  §6.4의 채널로 **재조회 검증**을 수행한다. 검증이 실패하면(생성했는데 멤버가 다름) 이는 게이트 A
  GO 분기 내부의 별도 실패이며 그룹 생성 자체를 거부한다(REQ-GROUPGEN-023).
- **NEGATIVE 분기** (P1/P5 전부 실패 — `query_state`가 답하지 않음): **자동 생성 축 전체 중단.**
  `create_arrangement_groups` 툴은 콘솔에 **아무것도 송신하지 않고**, `classify_arrangement_topology`
  가 이미 반환한 위상 판정 + 이름 매핑을 그대로 **발화 목록 텍스트**로 재포장해 사용자에게
  제시한다(예: `"Fixture 1 Thru 6 / Store Group 14 / Label Group 14 'GEO Downstage'"` 형태의
  문자열 나열). 사용자가 그 텍스트를 콘솔에 손으로 입력한다. **대체 정책(어느 채널을 대신 쓸지,
  얼마나 자주 재시도할지)을 에이전트가 스스로 고르지 않는다** — 블로커 보고로 전달한다.

### 게이트 B — `Store Group <n>` 생성

- **GO 분기**: M3(그룹 쓰기) 구현을 진행한다. `select_group_slot` + 발화 사슬(§6.2) +
  게이트 A 검증(위)이 정상 결합된다.
- **NEGATIVE 분기**: **SPEC 전체 중단.** 그룹을 만들 수 없으면 위상 분류(§2)와 명명(§4)은
  구현되어 있어도 산출할 곳이 없다 — `topology.py`/`naming.py`는 순수 모듈로 남아 다른 SPEC이
  재사용할 수 있으나, `create_arrangement_groups` 툴 자체는 존재하지 않는다. 이 분기에서는
  `classify_arrangement_topology`(읽기 툴)만 출하하는 축소판을 고려할 수 있으나, 이는 SPEC 범위를
  재정의하는 결정이므로 이 문서가 자동으로 채택하지 않고 사용자 확인을 요구한다.

### 게이트 C — 점유 슬롯 덮어쓰기

- **GO 분기** (차단 규칙이 실측으로 확정 — 예: 콘솔이 확인 프롬프트 없이 조용히 덮음이 확인됨):
  `select_group_slot`의 `GROUP_SLOT_OCCUPIED` 정적 차단(§6.4)이 **그대로 강제**된다 — 이 결과는
  차단 로직을 완화하지 않는다.
- **NEGATIVE 분기 없음 — 강화만 있다** (계약 §3 표 그대로): 콘솔이 조용히 덮어쓴다는 실측이
  나오면, 이는 REQ-GROUPGEN-022 정적 차단이 **더욱 절대적으로 필요하다는 근거**가 된다.
  두 결과 모두 같은 코드 경로(§6.4)로 이어진다 — P6의 실측값이 무엇이든 `select_group_slot`
  구현은 바뀌지 않는다.

### 게이트 D — 절단 시 슬롯 안전 (분기 없음)

계약 §3: D는 분기가 없다. `GROUP_POOL_TRUNCATED`(§6.1)와 `FIXTURE_LIST_TRUNCATED`(§6.3)는
`_select_cue_number` 선례(§6.1)를 따라 **항상 거부**다 — 실측 결과와 무관하게 정책이 고정되어
있으므로 M0 프로브 대상이 아니다.

### AC 서술 규율

`acceptance.md`(워커 B 소유)는 게이트별로 **GO 시 검증 커맨드**와 **NEGATIVE 시 강등 동작 검증**을
**둘 다** 가져야 한다(계약 §3). 미프로브 전제는 `SKIP: CONDITION_NOT_MET` 행을 받는다
(REQ-GROUPGEN-029).

---

## §11. @MX 태그 대상 식별

`.claude/rules/moai/workflow/mx-tag-protocol.md` 규율에 따라 run-phase(M1~M4)가 부착할 태그
후보를 미리 식별한다 — design.md는 태그를 부착하지 않고(소스 코드 변경 0), 대상만 지목한다.

| 위치 | 태그 | 사유 |
|---|---|---|
| `topology.py::classify()` | `@MX:ANCHOR` + `@MX:REASON` | fan_in ≥ 3 예상(두 개 명명 함수 + 툴 표면 + 회귀 스위트가 모두 호출) — 위상 경합 규칙(§2.4)이 계약 D-Q2를 구현하는 유일한 지점이므로 변경 시 계약 재검토 필요 |
| `naming.py::name_depth_bucket` / `name_lateral_bucket` | `@MX:NOTE` | §4.3의 `Center`/`Centerline` 충돌 회피가 왜 두 함수로 분리됐는지, 코드만 봐서는 비자명함 |
| `server/safety/classify.py::RECOGNIZED_REFERENCE_TYPES` (기존 `@MX:NOTE` 확장) | `@MX:NOTE` 갱신 | 이미 EXECREF-001의 `@MX:NOTE`가 있음(§7.1) — `"Group"` 추가 시 동일 주석 블록에 GROUPGEN-001 근거를 이어 붙인다(교체 아님) |
| `select_group_slot::GROUP_SLOT_OCCUPIED` 분기 | `@MX:WARN` + `@MX:REASON` | 이 분기를 제거하거나 완화하면 백업·복구 불가 자산을 조용히 덮어쓸 수 있다(research §2.1) — 위험 구조 |
| `detect_concentric` (§3 비공허성의 핵심) | `@MX:ANCHOR` + `@MX:REASON` | 이 함수가 §3의 오독 결함을 막는 유일한 지점 — golden 테스트와의 계약이 여기 있다 |
| M1~M6 곳곳의 `REQ-GROUPGEN-010/011/012/027` 이관 대상 코드(있다면) | `@MX:TODO` (없음 — v1 미구현이므로 코드 자체가 부재. 대신 `naming.py` 상단에 `@MX:NOTE`로 "카테고리 축은 v1 범위 밖, 계약 D-Q9 참조"를 남긴다) | 향후 카테고리 축 복원 시 재발견 지점 |

---

## §12. 검증 천장 — 설계 관점 확장

`spec.md` §C.1을 설계 관점에서 확장한다. **무엇이 기계로 확인 불가한지 정직하게 명시**한다.

| 대상 | 기계 확인 | 수단 | 설계 근거 |
|---|---|---|---|
| 위상 분류(`classify()`) 정확성 | **YES** | `topology.py` 단위 테스트(golden §2.5) — 순수 함수, 콘솔 무접촉 | §2.1 순수성 경계 |
| 명명 어휘 매핑(`naming.py`) 정확성 | **YES** | 단위 테스트 — 폐쇄 어휘 문자열 정적 비교 | §4.1~§4.5 |
| 슬롯 실측·절단 거부·점유 차단 로직 | **YES** | `select_group_slot`/`guard_fixture_list_truncation` 단위 테스트 + 뮤테이션(§6.5) | §6.1~§6.5 |
| 범위 봉쇄(발화 슬롯 == 실측 빈 슬롯) | **YES** | 정적 단언(§6.5) | §6.5 |
| 발화 커맨드 문자열 형상 | **YES** | 산출 문자열 정적 검사(콘솔 미송신 상태로도 검증 가능) | §6.2, §9 |
| **그룹 생성이 의도한 픽스처를 실제로 담았는가** | **조건부** — 게이트 A GO 시에만 | 라이브 멤버십 재조회(P5, M6) | §10 게이트 A |
| **점유 슬롯 실제 거동(조용히 덮는가/거부하는가)** | **조건부** — P6 라이브 실측 전까지 미확정 | 라이브 프로브(P6) | §10 게이트 C |
| **`Store Group`/`Label Group`의 실제 게이트 분류** | **조건부** — 정적 열람(P7)이나, 콘솔 런타임 동작과 문서가 다를 가능성 배제 못함 | `blacklist.yaml`/`classify.py` 정적 확인 + P3/P4 라이브 발화 시 실제 승인 카드 발행 여부 관찰 | §7.2, §9 |
| 라벨 길이 상한 | **NO (design 시점)** — M0 P1a 라이브 프로브가 실측할 때까지 미확정 | 라이브 프로브(P1a) | §4.6 |
| 종류 축(제조사·타입명)의 이종 리그 거동 | **NO** (이 리그로는 — 실측 리그가 동종) | 합성 golden 필수 | §5.4 |
| 카테고리 토큰 매칭(`Spot`/`Wash`/…)의 실효성 | **해당 없음** — v1 범위 밖(계약 D-Q9), 설계 대상 자체가 없음 | — | §5.2 |
| 위상 × 종류 교차 그룹 | **해당 없음** — v1 미구현(계약 D-Q9) | — | §5.3 |
| 그룹이 연출에서 "맞게" 동작하는가(뒷줄만 파랗게 등) | **NO** | 사람 관측만(M6, SPATIAL §C.1 계승) | §9, plan.md M6 |
| 세 배치(그리드/동심원/좌우)가 서로 다른 위상·어휘를 내는가 | **YES**(기계) + **NO**(그 결과가 무대에서 "맞게" 잡혔는지는 사람) | golden 단위 테스트(기계) + M6 라이브 관측(사람) | §2.5, plan.md M6 |

**정직성 규율**: 이 표의 "NO"/"조건부" 행은 결함이 아니라 **설계가 인정하는 한계**다. run-phase가
이 한계를 넘어서는 주장(예: "라벨 길이는 안전하다"를 P1a 없이 단언)을 하면 그것이
`verification-claim-integrity.md`가 금지하는 미관측 주장이다.

---

## 참조

계약 파일(`.plan-contract.md`) §0~§6 전체, `research.md` §1~§9, `spec.md` A~E,
`plan.md` §A~§E, `server/scene/compile.py:243`(`_select_cue_number`),
`server/safety/classify.py:44`(`RECOGNIZED_REFERENCE_TYPES`),
`server/tests/test_tools.py:144`(`TOOL_NAMES` 개수 고정 테스트),
`SPEC-COPILOT-SPATIAL-001/progress.md` §E.2.14/§E.2.18/§E.2.19/§E.2.20/§E.2.21.
