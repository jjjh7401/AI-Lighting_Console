# 인수 조사 — 절단 고지의 구조적 강제

base `origin/main` = `b1a630e` · 워크트리 `spec/truncate-001` · 측정일 2026-08-05

모든 인용은 **이 워크트리의 실측**이다. `[INFERENCE]`가 붙지 않은 문장은 파일을 열어 확인한 것이다.

---

## 1. 닫으려는 구멍 — 관측된 사고

SPATIAL-001 M6 라이브, **결함 1**(`progress.md:488-503`):

| 사실 | 값 | 출처 |
|---|---|---|
| 컨테이너가 보고한 총수 | `childCount: 19` | `progress.md:115` |
| 실제 도착한 children | 18 | `progress.md:115` |
| 응답기 플래그 | `truncated: true` | `progress.md:115` |
| 배치된 픽스처 | 18대 | `progress.md:490-491` |
| 최종 실측 잔여 | **fid 19만 원점(0,0,0)** | `progress.md:491` |

**툴은 제 몫을 다했다** — `progress.md:493`이 그대로 적는다: *"`truncated: true` 보고 · `unreadable: []` · fid 19 좌표 **발명 0**"*. 그리고 툴 설명문은 이미 **명령형**이다(`tools.py:4868-4870`):

> *"Either way the list is NOT the whole rig — **say so** rather than presenting a left-to-right order over the part you happened to receive."*

모델은 **금지된 바로 그것**을 했다(`progress.md:498`). 판정은 *"툴 결함이 아니라 모델 준수 갭"*이며, 기록된 천장은 **"툴 설명은 지시일 뿐 강제가 아니다"**(`progress.md:499`, `:599` ④).

그리고 직전 sync가 처방까지 이미 적어두었다(`progress.md:502-503`, `:645`):

> *"강제하려면 툴 계층이 `truncated: true`일 때 **회신을 구조적으로 다르게** 만들어야 한다(예: 부분 리그임을 나타내는 별도 상태값, 또는 정렬 결과 자체의 보류)."*

본 SPEC은 그 처방의 집행이다. **설계 방향은 조사 결과가 아니라 승계된 판정이며**, 본 조사가 더한 것은 *어느 키를, 왜, 어느 폭발반경으로* 다.

---

## 2. 실측 — 현재 회신 형상

### 2.1 `read_spatial_fixtures` (`tools.py:699-802`)

반환 dict는 **경로가 하나다**(`:783-802`). 완전 판독과 절단 판독이 **같은 키 집합**을 낸다:

```
source · path · fixtures · unreadable · truncated · roundtrip_capped · coverage{judged, of, complete}
```

| 키 | 행 | 성격 |
|---|---|---|
| `fixtures` | `:786` | 데이터 — 절단 시에도 **같은 이름 그대로** 부분 목록을 담는다 |
| `truncated` | `:788` | **데이터 옆에 놓인 boolean** — 읽지 않아도 payload는 온전히 소비된다 |
| `roundtrip_capped` | `:789` | 별개 신호(REQ-SPATIAL-006) — 콘솔이 자른 것과 이 툴이 멈춘 것은 다른 사건 |
| `coverage.complete` | `:798-800` | `not truncated and not roundtrip_capped and len(fixtures) == total` |

절단 판정은 **두 경로**다(`:730-732`) — 응답기 플래그 **또는** `childCount > len(children)` 산술. 한쪽만 지워도 다른 쪽이 잡는다. **이 판정 자체는 건강하며 본 SPEC이 건드리지 않는다.**

라운드트립 상한은 `SPATIAL_PROPERTY_QUERY_CAP = 120`(`:628`), 픽스처당 4프로퍼티(`:615` `("fid","posx","posy","posz")`) → **30대**에서 `roundtrip_capped`(`:761-763`).

### 2.2 `get_spatial_context` (`tools.py:3029-3082`) — 사고가 난 지점

```
:3051  reply = read_spatial_fixtures(...)
:3059  reply["analysis"] = spatial_analysis_to_dict(analyze_spatial_records(reply["fixtures"]))
:3073  content = json.dumps(reply)
:3080  is_error = False        ← 절단이어도 항상
```

**핵심 결함은 `truncated` 플래그가 아니라 `analysis`다.** 모델이 제시한 것은 좌우 정렬이고, 좌우 정렬은 `analysis.row_order`다.

### 2.3 `analysis`는 자신이 부분임을 **표현할 수 없다** (본 조사의 최중요 발견)

`analyze_spatial_records`의 시그니처(`server/spatial/rows.py:202-204`):

```python
def analyze_spatial_records(records: Sequence[Mapping[str, object]]) -> SpatialAnalysis:
    """Parse the read tool's fixture records, then detect rows over them."""
    return analyze_spatial_rows(spatial_fixtures_from_records(records))
```

**records 외의 인자가 없다.** 절단 플래그도, coverage도 들어가지 않는다. 따라서 `spatial_analysis_to_dict`(`server/spatial/schema.py:244-257`)의 어떤 필드도 커버리지 불완전성을 실을 수 없다:

| 필드 | 행 | 절단을 알 수 있나 |
|---|---|---|
| `row_order` | `schema.py:245` | **NO** — 도착한 좌표만 본다 |
| `fixture_count` | `schema.py:248` | **NO** — 판독된 18을 리그 크기로 보고한다 |
| `low_confidence` | `schema.py:249` | **NO** — 기하학적 확산만 본다 |
| `confidence_reason` | `schema.py:250` | **NO** — 동일 |

**귀결 — 그리고 이것은 추론이 아니라 실측이다**: 같은 절단 리그에서 `progress.md:485`가 *"전부 z=5.0이므로 `vertical_span = 0.0`, x 확산으로 **1행 고신뢰**"*를 기록했다. 즉 **`low_confidence: False`가 18대 판독 위에서 관측됐다.** **존재하지 않는 리그에 대한 고신뢰 좌우 정렬**이 완전 판독과 **구별 불가능한 형상**으로 회신에 실렸다. `low_confidence`는 *"패치됐지만 위치가 안 잡힌 리그"*를 위한 신호이고(`tools.py:4876-4879`), **커버리지 신호가 아니다.**

그러므로 §1의 모델은 `low_confidence: False`인 `row_order`를 인용했다. **인용할 것이 있었다는 게 결함이다.**

**그래서 고칠 수 있는 자리가 하나뿐이다.** `analysis`에 커버리지를 실어 *"이것은 부분이다"*라고 **플래그하는 길은 구조적으로 막혀 있다** — 시그니처에 그 인자가 없으므로(`rows.py:202-204`) 주입하려면 `server/spatial/**`를 고쳐야 하고, 그것은 순수 기하 계층에 판독 완전성을 밀어 넣어 `low_confidence`의 의미를 두 축으로 오염시킨다(§5의 기각 항목 · REQ-TRUNCATE-012). 남는 유일한 수단은 **툴 계층에서 그 필드를 아예 계산하지 않는 것**, 즉 **보류**다. 이것이 D2의 두 절반 중 **하중을 받는 쪽**이며, `fixtures` → `partial_fixtures` 개명은 보류가 목록 쪽으로 우회되지 않도록 형상을 함께 옮기는 보강이다.

### 2.4 두 번째 절단 지점 — `rig_section` (`tools.py:474-489`)

`{objects, truncated, total}`(`:486-488`). 같은 병리(데이터 옆의 boolean)이나 **폭발반경이 전혀 다르다** — §4.2.

---

## 3. 저장소는 이미 "절단이면 거부"를 규율로 갖고 있다 — `get_spatial_context`가 예외다

이것이 권고안의 가장 강한 근거다. 같은 `truncated` 신호를 받는 **네 모듈이 전부 거부한다**:

| 모듈 | 행 | 거동 |
|---|---|---|
| `server/fx/instantiate.py` | `:236-241` | `SEQUENCE_TRUNCATED` **raise** — *"'free' is not a property of the numbers that happened to arrive"*(`:223-226`) |
| `server/scene/compile.py` | `:258-263` | `CUE_TRUNCATED` **raise** |
| `server/looks/songcue.py` | `:290-291`, `:300-301` | `SEQUENCE_TRUNCATED` **raise** |
| `server/prechk/macro.py` | `:448-453`, `:473-474` | `PARTIAL_GROUP_COVERAGE` — 부정 소견이 아니라 **불완전 보고** |

`prechk/inventory.py:5-9`는 더 세게 적는다: *"**Truncation is the DEFAULT path, not an edge case.** `Patch/Stages/1/Fixtures` already truncated at 19 fixtures"*.

**`get_spatial_context`만 부분 데이터를 플래그와 함께 돌려주고 판단을 호출자에게 넘긴다.** 그리고 그 호출자는 모델이다. §1이 그 위임의 대가다.

`server/spatial/choreography.py:356-358`이 같은 위임을 한 겹 더 한다 — *"Whether to USE the result is the caller's call, made against `analysis.low_confidence`"*. **판단 위임이 두 겹 쌓여 있고 최종 판단자가 모델이다.**

---

## 4. 회신 형상 소비자 전수 — 폭발반경

### 4.1 `read_spatial_fixtures` 회신 (본 SPEC의 표적)

**프로덕션 코드 소비자는 2건뿐이며 둘 다 `tools.py` 안이다.** 회신 JSON을 파싱하는 서버측 파이썬은 **없다** — `json.dumps`(`:3073`) 이후의 유일한 소비자는 **모델**이다.

| 소비자 | 행 | 읽는 키 |
|---|---|---|
| `get_spatial_context` | `:3051` | `reply["fixtures"]`(`:3059-3060`), 이후 dict 전체를 그대로 직렬화 |
| `classify_arrangement_topology` | `:3533` | `reply["fixtures"]`(`:3541`) · `reply.get("coverage")`(`:3554`) · `truncated`(`:3610`) · `roundtrip_capped`(`:3611`) · `unreadable`(`:3612`) |

→ **함수 dict의 키를 바꾸면 깨지는 프로덕션 코드는 `classify_arrangement_topology` 하나다.** 인프로세스이므로 새 키를 읽게 하면 된다.

### 4.2 `rig_section` 회신 (두 번째 지점 — 범위 밖 근거)

`rig_section(` 호출 **11건**, 그리고 소비자가 **웹 계층까지 뻗는다**:

```
server/orchestrator/tools.py · server/web/dash.py · server/web/panel.py
+ 테스트 5파일 (test_fx_instantiate · test_looks_instantiate · test_looks_resolver
                · test_scene_compile · test_scene_report)
```

거기에 **직접 소비자**로 §3의 거부 4모듈(`fx/instantiate` · `scene/compile` · `looks/songcue` · `prechk/macro`) + `looks/resolver.py:200` + `paperwork/data.py:183`이 이 dict를 읽고, **파생 소비자**로 `paperwork/render.py:118-125`가 그 한 홉 뒤(`data.py:183` → `PoolListing.truncated` → `listing.truncated`)에 붙는다.

→ **`rig_section` 형상 변경은 11 호출점 + 웹 2파일 + 거부 4모듈을 동시에 건드린다. 범위 밖(spec.md §D).**

### 4.3 형상을 고정한 테스트 (실측 카운트)

| 파일 | 총 테스트 | `["fixtures"]` | `truncated` | `roundtrip_capped` | `coverage` | `topology_partial` |
|---|---|---|---|---|---|---|
| `test_spatial_context.py` | 32 | **17** | 8 | 7 | 0 | 0 |
| `test_tools.py` | 71 | 10 | 4 | 0 | 0 | 0 |
| `test_groupgen_tools.py` | 26 | 1 | 6 | 0 | 7 | **9** |
| `test_spatial_arrange.py` | 65 | 0※ | — | — | — | — |

※ `test_spatial_arrange.py:61`의 `["fixtures"]`는 `DEFAULT_RIG_CONTEXT_PATHS["fixtures"]` — **회신 형상이 아니라 rig_paths 키**다. arrange 테스트는 이 회신을 고정하지 않는다.

가장 직접적인 고정(`test_spatial_context.py:338-354`, 라이브 형상 재현):

```python
assert reply["truncated"] is True
assert len(reply["fixtures"]) == 18      # ← 절단 시 fixtures 키의 존재를 고정
assert reply["roundtrip_capped"] is False
```

그리고 `:375-379`가 **비공허성 짝**을 이미 갖고 있다 — *"Non-vacuity for the three above: a hardcoded True would pass them all."*

### 4.4 폐쇄 툴 집합

`TOOL_NAMES`(`tools.py:127-150`) = **22종**. 고정처는 `test_tools.py:147-148`:

```python
assert sorted(names) == sorted(TOOL_NAMES)
assert len(names) == len(TOOL_NAMES) == 22
```

→ **툴을 1건이라도 추가하면 이 리터럴 `22`가 깨진다.** 후속 툴 신설형 설계(§5 D3)의 확정 비용이다. 회신 형상만 바꾸는 설계는 이 파일을 건드리지 않는다.

`get_spatial_context`의 파라미터는 **인자 0개**다(`tools.py:4884`):

```python
parameters={"type": "object", "properties": {}, "additionalProperties": False}
```

→ 필수 인자 추가형 설계는 **첫 호출을 불가능하게 만든다**(토큰을 알려면 먼저 호출해야 하고, 호출하려면 토큰이 필요하다).

---

## 5. 설계 후보 4종 — 실측 기반 판정

### D1 · Refuse-or-narrow (절단 시 부분 목록을 아예 반환하지 않는다)

**기각.** 두 개의 독립된 치명적 근거:

1. **라이브 리그에서 기능이 죽는다.** `prechk/inventory.py:5-9`가 *"Truncation is the DEFAULT path, not an edge case"*라 적고 측정 리그가 이미 19대에서 절단된다(`progress.md:115`). 절단을 에러로 만들면 `get_spatial_context`는 **캘리브레이션 리그에서 항상 실패한다** — SPATIAL 축 전체가 사용 불가가 된다.
2. **교차 SPEC 계약 파괴.** `classify_arrangement_topology`의 부분 토폴로지 기능(REQ-GROUPGEN-024 amendment, `tools.py:3547-3569`)은 **부분 판독이 존재한다는 전제 위에 세워져 있다.** 절단이 거부되면 `topology_partial`이 도달 불가능한 죽은 코드가 되고 `test_groupgen_tools.py`의 **9건**이 무의미해진다.

`fx`/`scene`이 거부할 수 있는 이유는 그쪽 질문이 *"빈 번호를 골라라"*(부분 목록으로 답이 **틀려진다**)이기 때문이다. 좌표 질문은 *"어디에 있나"*이며 **18대의 좌표는 18대에 대해 여전히 참이다.** 질문의 성격이 달라 규율을 그대로 옮길 수 없다.

### D2 · Shape divergence (절단 회신이 완전 회신과 **다른 최상위 스키마**) — **채택**

**폭발반경**: 프로덕션 `classify_arrangement_topology` 1곳(인프로세스, 새 키 읽기) · `test_spatial_context.py` 절단 계열 단정 · 툴 설명문 `:4847-4849`. **`TOOL_NAMES` 무변경(22 유지) · `test_tools.py:148` 무접촉 · 웹 계층 무접촉 · `rig_section` 무접촉.** 폐쇄 툴 집합 **비파괴**.

핵심은 `fixtures`/`analysis` **키의 부재**다. 부재는 무시할 수 없다 — 무시할 대상이 없기 때문이다. §1의 모델은 *"받은 일부에 대한 좌우 정렬을 제시"*했는데, **좌우 정렬이 계산되지 않으면 인용할 것이 없다.**

`progress.md:502-503`의 처방(*"별도 상태값, 또는 정렬 결과 자체의 보류"*)과 **두 절 모두 일치한다.**

**두 절반의 하중은 같지 않다.** `analysis` 보류가 **하중을 받는 쪽**이다 — §2.3이 실측한 대로 그 산출물은 자신이 부분임을 **표현할 능력이 없고**(`rows.py:202-204`에 인자가 없다), 능력을 주려면 `server/spatial/**`를 고쳐야 하므로(REQ-TRUNCATE-012 금지) *플래그*라는 선택지 자체가 존재하지 않는다. 그러므로 *"보류가 아니라 표시하면 되지 않는가"*는 이 설계에서 **가능한 대안이 아니다.** `fixtures` → `partial_fixtures`는 보류가 목록 쪽으로 우회되는 것을 막는 보강이며, 단독으로는 §1의 사고를 막지 못한다(모델이 인용한 것은 목록이 아니라 정렬 결과였다).

### D3 · Poisoned payload / 필수 확인응답

**기각(주설계로서).** 확정 비용 2건: ① 새 툴이면 `TOOL_NAMES` 22→23 + `test_tools.py:148` 리터럴 파괴(§4.4) ② 필수 인자면 인자 0개 툴의 첫 호출이 불가능해진다(§4.4). 게다가 토큰을 호출 간에 보관해야 하므로 **무상태 툴 계층에 새 상태면(state surface)** 이 생긴다.

유일하게 확인응답을 *구조적으로 강제*하는 안이라는 점은 인정한다 → **D2의 라이브 증거가 부정적일 때의 대비안**으로 plan.md §E 위험 2에 보류한다.

### D4 · Downstream refusal (쓰기 툴이 절단 유래 집합을 거부)

**기각(주설계로서) — 결함을 오진한다.** `arrange_fixtures`는 **이미** 명시 `fids`를 요구하고(`tools.py:3104-3110`, *"moves exactly what it is told to and never widens the set itself"*), `tools.py:3550-3553`은 쓰기 경로가 리그 절단에 **영향받지 않는다고 명시적으로 설계**되어 있다 — 호출자가 준 fids를 쓰기 때문이다.

그리고 관측 사실이 결정적이다: **fid 19는 원점에 남았고 쓰기는 지시받은 대로 정확히 동작했다**(`progress.md:491`). 결함은 나쁜 쓰기가 아니라 **침묵**이다. 툴은 *"18개인 이유가 운영자의 뜻인지 절단인지"*를 **호출 간 상태 없이 구별할 수 없다**(D3와 같은 벽).

**단, 좁은 실측 구멍 1건은 진짜다** → 채택. `create_arrangement_groups`(`tools.py:3642-`)에서 `topology_partial`을 **grep한 결과 0건**이다. 즉 `:3575`가 그룹마다 붙여 보낸 플래그가 **쓰기 툴에서 아무 일도 하지 않고 죽는다.** 이것은 오진이 아니라 실측된 누락이다.

**확인 인자의 형태는 fid 열거로 결정됐다**(에이전트, 2026-08-05 — plan.md §C M0.3). 불리언 `acknowledge_partial: true`가 아니라 **미판독 픽스처 fid의 명시 열거**(`acknowledged_unread_fids: list[int]`)다. 이유는 자기일관성이다 — 불리언은 무엇이 빠졌는지 읽지 않아도 참이 되므로 확인 인자가 다시 *"데이터 옆의 boolean"*, 즉 본 SPEC이 §2.1에서 결함으로 지목한 형상이 된다. 열거는 두 재료를 실제로 읽게 만든다: **판독된 fid 집합**(열거는 `⋃ groups[].fids`와 서로소여야 한다)과 **결손 산술**(열거 크기가 `fixtures_section.total` − 도착 `objects` 수와 일치해야 한다 — 핸들러가 이미 그 섹션을 읽는다, `tools.py:3699-3703`). 불리언 배제는 기계적으로 성립한다: 같은 핸들러가 `groups[].fids`에 이미 `isinstance(fid, int) and not isinstance(fid, bool)`를 쓰고 있고(`tools.py:3673-3676`), 파이썬에서 `True`는 `int`의 부분형이므로 그 배제가 없으면 `[True]`가 통과한다. 계약 정본은 REQ-TRUNCATE-008 / AC-TRUNCATE-008.

### 판정 요약

| 안 | 판정 | 결정 근거 (실측) |
|---|---|---|
| D1 refuse-or-narrow | **기각** | 절단이 기본 경로 → 라이브 기능 사망 + GROUPGEN 부분토폴로지 계약 파괴 |
| **D2 shape divergence** | **채택** | 폐쇄집합 비파괴 · 프로덕션 소비자 1곳 · `progress.md:502` 처방 일치 |
| D3 확인응답 | 기각(보류) | `TOOL_NAMES` 파괴 또는 인자 0개 툴 첫 호출 불가 + 새 상태면 |
| D4 하류 거부 | 기각 + **좁은 채택** | 쓰기는 이미 명시 fids · 결함은 쓰기가 아닌 침묵 / **단** `create_arrangement_groups`의 플래그 사장은 실측 구멍 |

---

## 6. 왜 "성공 기준이 구조적"이어야 하는가

WRITEGATE-001이 같은 판정을 이미 내렸다(`REQ-WRITEGATE-014`): *"라이브 관측은 성공 기준의 유일 근거가 되지 않는다."*

본 SPEC에서는 그보다 **더 강하다**. 결함 자체가 **모델이 지시를 무시한 사건**이므로:

- 라이브 1턴이 통과해도 **아무것도 증명하지 못한다** — 그 모델이 그 턴에 순응했다는 것뿐이다.
- 라이브 1턴이 실패하면 **무언가 증명한다** — 반증은 유효하다.

→ **비대칭이다. 통과는 증거가 아니고 실패만 증거다.** 그러므로 성공은 *키의 부재*처럼 모델 없이 기계 검증되는 명제에 걸어야 한다(spec.md §E).

---

## 7. ASSUMPTION (71-75, 본 SPEC 할당 범위)

레포 전역 최대 사용 id는 **67**(`.moai/specs/` 실측)이고 WRITEGATE-001이 68-70을 점유했다. **71-75는 미사용이며 본 SPEC 전용이다.**

- **ASSUMPTION-71 (형상 분기의 실효성)** — 절단 회신에서 `fixtures`/`analysis` 키를 **제거**하면 모델이 부분성을 고지한다. **기계 검증 가능(키 부재) · 모델 순응은 원리적으로 미검증** — §6의 비대칭 때문이다. NEGATIVE면 D3(확인응답)로 승격.
- **ASSUMPTION-72 (파괴적 변경 허용 창)** — 출하된 회신 형상의 파괴적 변경이 이번 창에서 허용된다. **결정됨 (사용자, 2026-08-05) — 허용.** `progress.md:646`이 동류 변경(`left_to_right` 개명)을 *"출하된 폐쇄 집합의 파괴적 변경이므로 **SemVer major 창에서만**"*으로 판정한 선례가 있으나, **본 변경에는 적용하지 않는 명시적 예외**로 결정됐다 — 바뀌는 것은 **모델을 향한 계약**이고 **코드 계약은 무접촉**이기 때문이다(`TOOL_NAMES` 22 유지 · `test_tools.py:148` 무수정 · 툴 파라미터 스키마 무변경 · 인프로세스 소비자 1곳, §4.1·§4.4). 예외의 대가로 인정된 것은 지연 시 관측 결함(`low_confidence: False` on 18-of-19, `progress.md:485`)이 열린 채 남는다는 점이다. 선례는 개명 과제에 대해 여전히 유효하다. 기록: plan.md §C M0 결정 ① · M0.1.
- **ASSUMPTION-73 (`roundtrip_capped` 동급 처리)** — `truncated`와 `roundtrip_capped`가 같은 형상 분기를 촉발해야 한다. `coverage.complete`(`tools.py:798-800`)가 이미 둘을 OR로 합치므로 **분기 조건은 `coverage.complete == False` 하나로 충분하다**. 단 REQ-SPATIAL-006이 두 신호의 **분리 보고**를 요구하므로 신호는 분리 유지하고 **분기만 통합**한다. **결정됨 (에이전트, 2026-08-05) — 동급 처리.** 코드 확인 완료 + 설계 승인 완료. 결정 근거는 §2.1의 경계 산술이다 — `SPATIAL_PROPERTY_QUERY_CAP = 120` ÷ 4프로퍼티 = **30대**이므로, `truncated`만 분기하면 30대 초과 리그에서 §1의 침묵이 재발한다. 기록: plan.md §C M0 결정 ② · M0.2.
- **ASSUMPTION-74 (인프로세스 소비자 전환 무해)** — `classify_arrangement_topology`가 새 키를 읽도록 바꿔도 GROUPGEN 부분토폴로지 계약(`test_groupgen_tools.py` 9건)이 유지된다. **부분 검증** — 소비 키 5개를 §4.1에서 전수 확인했다.
- **ASSUMPTION-75 (`create_arrangement_groups` 거부의 운영 수용성)** — `topology_partial: true` 그룹의 쓰기를 명시 확인 없이 거부해도 운영이 막히지 않는다. **결정됨 (에이전트, 2026-08-05) — 본 SPEC 범위에 포함.** 확인 인자는 **미판독 fid의 명시 열거**이며 불리언이 아니다(§5 D4 말미 · REQ-TRUNCATE-008). 거부는 무조건이 아니라 *읽으면 통과*이므로 운영이 막히지 않고, 열거 요구가 확인의 형식화를 막는다. 기록: plan.md §C M0 결정 ③ · M0.3.

---

## 8. 확인 명령

```bash
# 절단 회신 형상 (현재: fixtures 키가 절단 시에도 존재)
uv run --frozen pytest server/tests/test_spatial_context.py -k truncat -q

# 부분 토폴로지 계약 (GROUPGEN 교차)
uv run --frozen pytest server/tests/test_groupgen_tools.py -k partial -q

# 폐쇄 툴 집합 22 고정
uv run --frozen pytest server/tests/test_tools.py -k 'registry or definition' -q

# analysis가 절단을 알 수 없음 (시그니처 확인)
grep -n 'def analyze_spatial_records' -A 3 server/spatial/rows.py

# create_arrangement_groups가 topology_partial을 무시함 (0건이어야 함)
sed -n '3642,3760p' server/orchestrator/tools.py | grep -c topology_partial
```
