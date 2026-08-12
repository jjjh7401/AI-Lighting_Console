---
id: SPEC-COPILOT-TRUNCATE-001
title: "절단 고지의 구조적 강제 — 부분 판독 회신의 형상 분기 (Truncation Disclosure)"
version: "0.2.0"
status: draft
created: 2026-08-05
updated: 2026-08-05
author: manager-spec
priority: P1
phase: "Phase 2 안전 계층 — 판독 완전성 고지"
module: "server/orchestrator/tools.py (read_spatial_fixtures · get_spatial_context · classify_arrangement_topology · create_arrangement_groups), server/tests/test_spatial_context.py, server/tests/test_groupgen_tools.py, server/tests/test_truncate_disclosure.py (신규)"
lifecycle: spec-anchored
tags: "truncation-disclosure, reply-shape, structural-enforcement, partial-read, coverage, breaking-change, model-compliance-gap, closed-set-reply"
tier: M
related_specs: [SPEC-COPILOT-SPATIAL-001, SPEC-COPILOT-GROUPGEN-001, SPEC-COPILOT-WRITEGATE-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-TRUNCATE-001 — 절단 고지의 구조적 강제

> **이 SPEC이 닫는 구멍**: 절단된 리그 판독의 회신이 **완전 판독과 같은 형상**이다. `fixtures`(`tools.py:786`)에 부분 목록이 담기고 `truncated`(`:788`)는 **그 데이터 옆의 boolean**이며, `analysis`(`:3059-3060`)는 **부분 집합 위에서 계산된 고신뢰 좌우 정렬**을 완전 판독과 구별 불가능하게 싣는다. 완전 회신을 향해 쓰인 소비자·프롬프트는 부분 회신을 **조용히 소비할 수 있다.**
>
> **가설이 아니라 관측이다**: SPATIAL M6 라이브에서 `childCount 19` / 반환 18 / `truncated: true`인 판독 위에 모델이 **18대 배치를 제시하고 불완전성을 말하지 않았다.** fid 19는 원점에 남았다(SPATIAL `progress.md:488-503`).
>
> **툴은 결백하다**: 절단을 보고했고(`truncated: true`), 좌표를 **0건 발명했고**(`unreadable: []`), 설명문은 이미 명령형으로 *"say so"*라 적는다(`tools.py:4868-4870`). 모델이 **금지된 바로 그것**을 했다. 기록된 천장은 **"툴 설명은 지시일 뿐 강제가 아니다"**(`progress.md:499`).
>
> **그러므로 성공 기준은 문면 강화가 아니라 형상이다.** 직전 sync가 처방까지 남겼다(`progress.md:502-503`, `:645`): *"회신을 구조적으로 다르게 만들어야 한다 — 부분 리그 상태값, 또는 정렬 결과 자체의 보류."* 본 SPEC은 그 집행이다.

## A. 배경

### A.1 무엇이 이미 작동하는가 (건드리지 않는다)

| 절 | 상태 | 근거 |
|---|---|---|
| 절단 **판정** | ✅ 건강 | 두 경로 — 응답기 플래그 **또는** `childCount > len(children)` 산술(`tools.py:730-732`). 한쪽이 죽어도 다른 쪽이 잡는다 |
| 두 신호 **분리** | ✅ 건강 | `truncated`(콘솔이 자름) ≠ `roundtrip_capped`(이 툴이 멈춤) — REQ-SPATIAL-006 |
| 좌표 **발명 금지** | ✅ 건강 | `unreadable`이 사유와 함께 열거되고 기본값 0을 채우지 않는다 |
| 커버리지 산술 | ✅ 존재 | `coverage{judged, of, complete}`(`tools.py:795-801`) |
| **고지 강제** | ❌ **오늘 거짓** | 부분 회신이 완전 회신과 같은 키 집합을 갖는다 |

즉 이 SPEC은 *"절단을 감지하지 못한다"*를 고치는 것이 **아니다.** 감지는 정확하다. **감지 결과가 무시 가능한 자리에 놓여 있다**를 고친다.

### A.2 결함의 진짜 표적은 `truncated`가 아니라 `analysis`다

모델이 제시한 것은 **좌우 정렬**이고, 좌우 정렬은 `analysis.row_order`다. 그리고 `analyze_spatial_records`는 **records 외의 인자를 받지 않는다**(`server/spatial/rows.py:202-204`):

```python
def analyze_spatial_records(records: Sequence[Mapping[str, object]]) -> SpatialAnalysis:
    return analyze_spatial_rows(spatial_fixtures_from_records(records))
```

따라서 `analysis`의 어떤 필드도 커버리지 불완전성을 실을 수 없다 — `low_confidence`(`server/spatial/schema.py:249`)는 **기하학적 확산** 신호이고(`tools.py:4876-4879`) 커버리지 신호가 아니다. 그리고 이것은 추론이 아니다: 같은 절단 리그에서 `progress.md:485`가 *"x 확산으로 **1행 고신뢰**"*를 기록했다 — **`low_confidence: False`가 18대 판독 위에서 실제로 관측됐다.**

> **존재하지 않는 리그(18대)에 대한 고신뢰 좌우 정렬이, 완전 판독과 형상으로 구별되지 않는다.** 모델이 인용할 것이 있었다는 사실 자체가 결함이다.
>
> **그러므로 요구는 *플래그*가 아니라 *보류*다.** `analysis`에 *"이것은 부분이다"*를 붙이는 길은 **구조적으로 막혀 있다** — `analyze_spatial_records`는 **records 하나만** 받고 절단·커버리지 인자가 **없으므로**(`server/spatial/rows.py:202-204`), 그 산출물에 부분성을 실으려면 `server/spatial/**`의 시그니처를 고쳐야 하고 그것은 REQ-TRUNCATE-012가 금지한다. 남는 유일한 수단은 **툴 계층에서 그 필드를 아예 계산하지 않는 것**이다. 즉 채택안(D2)의 두 절반 중 **`analysis` 보류가 하중을 받는 쪽**이고, `fixtures` → `partial_fixtures` 개명은 그 보류가 목록 쪽으로 우회되지 않도록 형상을 함께 옮기는 보강이다.

### A.3 저장소는 이미 "절단이면 거부"를 규율로 갖고 있다

같은 `truncated` 신호를 받는 **네 모듈이 전부 거부한다** — `fx/instantiate.py:236-241` · `scene/compile.py:258-263` · `looks/songcue.py:290-291` · `prechk/macro.py:448-453`. `prechk/inventory.py:5-9`는 *"Truncation is the DEFAULT path, not an edge case"*라 적는다.

**`get_spatial_context`만 부분 데이터를 플래그와 함께 돌려주고 판단을 호출자에게 넘기며, 그 호출자는 모델이다.** `server/spatial/choreography.py:356-358`이 위임을 한 겹 더 쌓는다. 본 SPEC은 이 예외를 규율 쪽으로 되돌린다 — 단 §D의 이유로 *거부*가 아니라 *형상 분기*로.

### A.4 이 SPEC은 "더 센 문면"을 만들지 않는다 — 이미 실패한 수단이다

GROUPGEN-001의 REQ-GROUPGEN-024 amendment는 **한 SPEC 앞서 정확히 그 시도를 했다**: `classify_arrangement_topology`에 `topology_partial` + `topology_partial_reason` + 그룹별 `topology_partial`을 얹었다(`tools.py:3559-3575`). 그것도 **추가 필드**이고, 형상은 완전 판독과 동일하다. 그리고 형제 툴에서 §1의 사고가 일어났다.

더 나쁜 실측: `create_arrangement_groups`(`tools.py:3642-`)는 `topology_partial`을 **한 번도 읽지 않는다**(grep 0건). `:3575`가 그룹마다 실어 보낸 플래그가 **쓰기 툴에서 아무 일도 하지 않고 죽는다.**

> **플래그를 늘리는 축은 소진됐다.** 남은 축은 형상이다.

## B. 요구 (GEARS)

### B.1 형상 분기 — 부분 회신은 완전 회신과 다른 스키마다

- **REQ-TRUNCATE-001** [Event-driven] — **When** 리그 좌표 판독의 커버리지가 불완전하면(`coverage.complete == False` — 즉 `truncated` **또는** `roundtrip_capped` **또는** 두 카운트 불일치, `tools.py:798-800`), the 회신 **shall** 완전 회신과 **다른 최상위 키 집합**을 갖는다. 분기 조건은 **`coverage.complete` 단일 술어**이며 새 판정 로직을 도입하지 않는다.
- **REQ-TRUNCATE-002** [Event-driven] — **When** 회신이 부분이면, the 픽스처 목록 **shall** `fixtures`가 **아닌** 키(`partial_fixtures`)에 담기고, `fixtures` 키는 **회신에 존재하지 않는다.** 부재가 강제 수단이다 — 완전 형상을 향해 쓰인 소비자는 `KeyError`를 받고, 완전 형상을 향해 쓰인 프롬프트는 참조할 것을 찾지 못한다.
- **REQ-TRUNCATE-003** [Event-driven] — **When** 회신이 부분이면, the `analysis` 키 **shall** 회신에 **존재하지 않으며**, 대신 `analysis_withheld`가 보류 사유와 부분 판독의 산술을 운반한다. 부분 집합 위의 행 구조는 **계산되어 실리지 않는다** — 모델이 제시한 것이 바로 그 필드이므로(§A.2), 인용 가능한 정렬 결과를 남기지 않는 것이 요구의 본질이다.
- **REQ-TRUNCATE-004** [Ubiquitous] — the 부분 회신 **shall** 결손의 산술을 명시한다: 콘솔이 보고한 총수, 실제 도착 수, 미판독 수. *"불완전하다"*가 아니라 *"19 중 18, 1대 미판독"*이다(`prechk/inventory.py:10-17`이 같은 규율을 적는다 — 플래그는 *얼마나* 를 말하지 않고 결손량이 바로 독자가 필요한 값이다).
- **REQ-TRUNCATE-005** [Unwanted] — the 형상 분기 **shall not** 두 절단 신호를 병합한다. `truncated`와 `roundtrip_capped`는 **분리 보고를 유지**한다(REQ-SPATIAL-006 — 오직 후자만 다시 물어 고칠 수 있다). 통합되는 것은 **분기 조건**이지 신호가 아니다.
- **REQ-TRUNCATE-006** [Unwanted] — the 부분 회신 **shall not** `is_error=True`로 표시되지 않는다. 부분 판독은 **답**이며(측정 리그에서 절단은 기본 경로 — `prechk/inventory.py:5-9`), 에러 표시는 자기수정 루프에 같은 리그를 다시 읽는 재시도만 먹인다(`tools.py:3074-3079`의 기존 판정 계승).

### B.2 인프로세스 소비자 — 교차 SPEC 계약 보존

- **REQ-TRUNCATE-007** [Where] — **Where** `classify_arrangement_topology`가 같은 판독 함수를 재사용하는 경우(`tools.py:3533`), the 툴 **shall** 새 키에서 부분 목록을 읽어 **기존 부분 토폴로지 계약을 무변경으로 유지한다** — `topology_partial` · `topology_partial_reason` · 그룹별 `axis`/`topology_partial`(`tools.py:3559-3575`, `:3608-3632`)은 문면 그대로 산다. 본 SPEC은 GROUPGEN-024 amendment를 **대체하지 않고 그 위에 형상 분기를 얹는다.**
- **REQ-TRUNCATE-008** [Event-driven] — **When** `create_arrangement_groups`가 `topology_partial: true`를 실은 그룹을 받으면, the 툴 **shall** 확인 인자 `acknowledged_unread_fids` 없이는 이를 **거부**한다. 이는 실측 구멍의 소인이다 — 해당 핸들러(`tools.py:3642-`)는 오늘 `topology_partial`을 **한 번도 읽지 않는다**(grep 0건). **확인 인자는 미판독 픽스처의 fid를 정수로 명시 열거한 비어 있지 않은 리스트이며, the 툴 shall not 불리언 확인 인자(`acknowledge_partial: true` 형태)를 정의하거나 수용한다.** 수용 조건 넷: ① 각 원소가 `isinstance(fid, int) and not isinstance(fid, bool)` — 같은 핸들러가 `groups[].fids`에 이미 쓰는 판정이며(`tools.py:3673-3676`), 파이썬에서 `True`가 `int`의 부분형이므로 **이 배제가 불리언 확인을 기계적으로 막는 지점**이다 ② 중복 없음 ③ **`⋃ groups[].fids`와 서로소** — 이미 쓰고 있는 fid를 *미판독*이라 부를 수 없다 ④ 결손량이 판독 가능하면 열거 크기가 그 값과 일치(`fixtures_section.total` − 도착 `objects` 수, `tools.py:3699-3703`; `total`이 `None`이면 총수 자체가 미상이므로 — `tools.py:483-488` *"unknown total, never 'the count equals what arrived'"* — 크기 검증은 성립하지 않고 ①~③만 적용된다). **왜 열거인가**: 불리언은 무엇이 빠졌는지 읽지 않아도 참이 되므로 확인 인자가 다시 *"그 데이터 옆의 boolean"* — 본 SPEC 서두와 §A.1이 오늘의 결함으로 지목한 바로 그 형상 — 이 된다. ③과 ④는 호출자가 **판독된 fid 집합과 결손 산술을 실제로 읽어야** 값을 만들 수 있게 한다. 본 SPEC의 표적이 *"툴 설명은 지시일 뿐 강제가 아니다"*(`progress.md:499`)이므로 **그 자신의 확인 절차도 같은 기준을 받는다** — 무심코 통과되는 확인은 SPEC이 닫으려는 결함의 재생산이다(결정 근거: plan.md §C M0.3).

### B.3 무엇을 바꾸지 않는가 (범위 봉쇄)

- **REQ-TRUNCATE-009** [Unwanted] — the 개정 **shall not** `rig_section`(`tools.py:474-489`)의 형상을 변경한다. 소비자가 **호출 11건 + 웹 2파일**(`server/web/dash.py` · `server/web/panel.py`) + 거부 4모듈 + `looks/resolver.py:200` + `paperwork/data.py:183`에 걸쳐 있다(§D).
- **REQ-TRUNCATE-010** [Unwanted] — the 개정 **shall not** 폐쇄 툴 집합을 변경한다. `TOOL_NAMES`는 **22종 그대로**이며(`tools.py:127-150`) `test_tools.py:147-148`의 `== 22` 고정은 **무접촉**이다. 새 툴 신설·필수 인자 추가는 금지된다 — 후자는 인자 0개 툴(`tools.py:4884`)의 첫 호출을 불가능하게 만든다.
- **REQ-TRUNCATE-011** [Unwanted] — the 개정 **shall not** 절단 **판정** 로직을 변경한다. `tools.py:730-732`의 이중 판정(플래그 OR 산술)과 `coverage` 산술(`:795-801`)은 문면 그대로 보존되며, 본 SPEC은 그 결과의 **배치**만 바꾼다.
- **REQ-TRUNCATE-012** [Unwanted] — the 개정 **shall not** `server/spatial/**`를 변경한다. `analyze_spatial_records`에 커버리지 인자를 추가하는 설계는 **기각**이다 — 순수 기하 계층에 판독 완전성 개념을 주입하면 `low_confidence`의 의미가 두 축으로 오염된다(`tools.py:4876-4879`가 그 필드를 *"패치됐으나 위치 미설정"*으로 못박았다). 보류는 **툴 계층에서** 일어난다.

### B.4 성공 기준의 성격

- **REQ-TRUNCATE-013** [Ubiquitous] — the 성공 기준 **shall** **구조적**이다: *키의 부재*처럼 모델 없이 기계 검증되는 명제에만 걸린다. 라이브 관측은 **성공의 근거가 될 수 없고 반증의 근거만 된다** — 결함 자체가 모델이 지시를 무시한 사건이므로 라이브 1턴의 통과는 *"그 모델이 그 턴에 순응했다"* 이상을 증명하지 못한다(비대칭 — `research.md` §6). WRITEGATE-001 `REQ-WRITEGATE-014`의 판정을 승계하며 본 SPEC에서는 더 강하게 적용한다.
- **REQ-TRUNCATE-014** [Unwanted] — the 검증 **shall not** 툴 설명문의 문면 강화를 성공 기준으로 삼는다. 설명문 갱신은 형상 변경의 **귀결로서 의무**이나(`tools.py:4847-4849`의 `Returns {...}`가 거짓이 되므로), *"더 강하게 적었다"*는 어떤 AC의 통과 조건도 아니다.

## C. 환경 및 전제

### C.1 검증 가능성

| 항목 | 기계 검증 | 수단 |
|---|---|---|
| 부분 회신에 `fixtures` 키 **부재** | **YES** | `assert "fixtures" not in reply` — 콘솔·모델 무접촉 |
| 부분 회신에 `analysis` 키 **부재** | **YES** | `assert "analysis" not in reply` |
| 완전 회신은 오늘 형상 **불변** | **YES** | 기존 회귀 32건(`test_spatial_context.py`) |
| 결손 산술(19/18/1) 정확성 | **YES** | 라이브 형상 재현 리그(`test_spatial_context.py:338-354`) |
| 두 신호 분리 보존 | **YES** | 기존 `roundtrip_capped` 단정 7건 |
| 부분 토폴로지 계약 보존 | **YES** | `test_groupgen_tools.py` 9건 회귀 |
| `create_arrangement_groups` 거부 | **YES** | 단위 — 확인 인자 없이 `topology_partial: true` 그룹 투입 |
| 불리언 확인 인자가 통과하지 못함 | **YES** | 단위 — `acknowledged_unread_fids`에 `True` / `[True]` 투입 → 거부. `isinstance(fid, bool)` 배제가 판정한다 |
| 확인 열거가 쓰기 fid와 서로소 | **YES** | 단위 — 이미 쓰는 fid를 열거하면 거부 |
| `TOOL_NAMES` 22 불변 | **YES** | `test_tools.py:147-148` |
| **모델이 실제로 고지하는가** | **NO** | ASSUMPTION-71 — 원리적 미검증(§B.4 비대칭) |
| **파괴적 변경의 허용 창** | **검증 대상 아님 — 결정됨** | ASSUMPTION-72 — **사용자 결정 2026-08-05**: 이번 창에서 수행하며 `progress.md:646` 선례에 대한 **명시적 예외**로 기록한다(plan.md §C M0.1) |

### C.2 PRESERVE

- `server/spatial/**` — **무변경**(REQ-TRUNCATE-012). 순수 기하 계층은 판독 완전성을 모르는 상태로 유지한다.
- `server/safety/**` · `server/measurement/**` — **무접촉**. 본 SPEC은 게이트 축과 파일 무교차이며 WRITEGATE-001과 병렬 가능하다.
- `tools.py`의 `rig_section` 및 그 소비자 전부(§D) — **무변경**(REQ-TRUNCATE-009).
- `TOOL_NAMES` · 툴 파라미터 스키마 — **무변경**(REQ-TRUNCATE-010).
- 절단 판정 및 `coverage` 산술(`tools.py:730-732`, `:795-801`) — **문면 보존**(REQ-TRUNCATE-011).
- `console/lua/**` · `server/web/**` — 무접촉.

### C.3 ASSUMPTION

레포 전역 최대 사용 id는 **67**이고 WRITEGATE-001이 68-70을 점유했다. 본 SPEC은 **71-75만** 사용한다.

- **ASSUMPTION-71 (형상 분기의 실효성)** — `fixtures`/`analysis` 키 제거가 모델의 고지를 유도한다. **키 부재는 기계 검증 완료 가능 · 모델 순응은 원리적 미검증**(§B.4). NEGATIVE면 D3(필수 확인응답)으로 승격하되 그 비용은 `TOOL_NAMES` 파괴다(`research.md` §5).
- **ASSUMPTION-72 (파괴적 변경 허용 창)** — 출하된 회신 형상의 파괴적 변경이 이번 창에서 허용된다. **결정됨 (사용자, 2026-08-05) — 허용.** 동류 변경(`left_to_right` 개명)을 *"출하된 폐쇄 집합의 파괴적 변경이므로 SemVer major 창에서만"*으로 판정한 선례가 있으나(SPATIAL `progress.md:646`), **본 변경에는 그 선례를 적용하지 않는 명시적 예외**로 결정됐다 — 모델을 향한 계약은 바뀌지만 **코드 계약은 바뀌지 않기 때문**이다(`TOOL_NAMES` 22 불변 · `test_tools.py:148`의 `== 22` 무수정 · 툴 파라미터 스키마 무변경 · 인프로세스 소비자 1곳이 같은 창에서 함께 전환). 선례 자체는 개명 과제에 대해 **여전히 유효**하다(§D 범위 밖). 기록: plan.md §C M0 결정 ① · M0.1.
- **ASSUMPTION-73 (`roundtrip_capped` 동급 처리)** — 두 절단 사유가 같은 형상 분기를 촉발해야 한다. `coverage.complete`가 이미 둘을 OR로 합치므로 분기 술어는 하나로 족하다. **결정됨 (에이전트, 2026-08-05) — 동급 처리.** 코드 확인 완료 + 설계 승인 완료. 결정 근거는 경계 산술이다 — 분기를 `truncated`에만 걸면 `SPATIAL_PROPERTY_QUERY_CAP = 120` ÷ 4프로퍼티 = **30대** 초과 리그에서 같은 침묵이 재발한다. **신호는 분리 유지 · 분기만 통합**(REQ-TRUNCATE-005). 기록: plan.md §C M0 결정 ② · M0.2.
- **ASSUMPTION-74 (인프로세스 전환 무해)** — `classify_arrangement_topology`가 새 키를 읽어도 GROUPGEN 계약이 유지된다. **부분 검증** — 소비 키 5개를 전수 확인했다(`research.md` §4.1).
- **ASSUMPTION-75 (`create_arrangement_groups` 거부의 운영 수용성)** — 부분 유래 그룹의 쓰기를 명시 확인 없이 거부해도 운영이 막히지 않는다. **결정됨 (에이전트, 2026-08-05) — 본 SPEC 범위에 포함.** 확인 인자는 **미판독 fid의 명시 열거**이며 불리언이 아니다(REQ-TRUNCATE-008). 열거를 요구하면 호출자가 판독된 fid 집합과 결손 산술을 **실제로 읽어야** 하므로 확인이 형식화되지 않으며, 이것이 운영 수용성의 근거이기도 하다 — 거부는 무조건이 아니라 *읽으면 통과*다. 기록: plan.md §C M0 결정 ③ · M0.3.

## D. 범위 밖 (Out of Scope)

### Out of Scope — `rig_section` / `get_rig_context`의 형상 분기
- 두 번째 절단 지점(`tools.py:474-489`)을 같은 방식으로 분기시키는 일은 **범위 밖이다.** 근거는 실측된 폭발반경이다: `rig_section(` 호출 **11건**, 소비자가 `server/web/dash.py`·`server/web/panel.py`의 **웹 계층까지** 뻗고, 거기에 절단 거부 4모듈(`fx/instantiate.py:236` · `scene/compile.py:258` · `looks/songcue.py:290` · `prechk/macro.py:448`) + `looks/resolver.py:200` + `paperwork/data.py:183`이 이 dict를 직접 읽으며 `paperwork/render.py:118-125`가 그 파생값(`listing.truncated`)에 붙는다.
- 좌표 축을 먼저 하는 이유는 **거기서 사고가 관측됐기 때문**이다(`progress.md:488-503`). 다른 축의 동종 사고는 아직 가설이다.
- 본 SPEC이 **형상 분기의 첫 선례를 만들므로**, 후속 SPEC은 규약을 재발명하지 않고 소비자 전환과 웹 계층 갈래만 다루면 된다.

### Out of Scope — 필수 확인응답 / 오염된 payload (설계 D3)
- 토큰 에코를 요구하는 2단 프로토콜은 **채택하지 않는다.** 새 툴이면 `TOOL_NAMES` 22→23으로 `test_tools.py:148`의 리터럴을 깨고, 필수 인자면 인자 0개 툴(`tools.py:4884`)의 첫 호출이 불가능해지며, 어느 쪽이든 호출 간 토큰 보관을 위한 **새 상태면**이 생긴다.
- 유일하게 확인응답을 구조적으로 강제하는 안이라는 점은 인정하며, **ASSUMPTION-71이 NEGATIVE일 때의 승격 경로**로 보류한다(plan.md §E 위험 2).

### Out of Scope — 쓰기 툴의 절단 유래 집합 거부 (설계 D4 전면)
- `arrange_fixtures`가 절단 유래 fid 집합을 거부하게 만드는 일은 범위 밖이다. **결함을 오진하기 때문이다**: 해당 툴은 이미 명시 `fids`를 요구하고(`tools.py:3104-3110`) `tools.py:3550-3553`은 쓰기 경로가 리그 절단에 영향받지 않도록 **의도적으로 설계**되어 있다. 관측 사실도 같은 방향이다 — **fid 19는 원점에 남았고 쓰기는 지시받은 대로 정확히 동작했다**(`progress.md:491`). 결함은 나쁜 쓰기가 아니라 **침묵**이다.
- 툴은 *"18개인 이유가 운영자의 뜻인지 절단인지"*를 호출 간 상태 없이 구별할 수 없다.
- **단 좁은 한 조각은 범위 안이다**(REQ-TRUNCATE-008): `create_arrangement_groups`가 `topology_partial`을 **전혀 읽지 않는다**는 것은 오진이 아니라 실측 누락이다.

### Out of Scope — 절단 자체의 완화 (재조회·페이지네이션)
- 미판독 픽스처를 **추가 판독으로 메우는** 일(1..childCount 스윕, 페이지네이션, 상한 인상)은 범위 밖이다. `prechk/inventory.py:400-404`에 이미 `recover_truncated` 슬롯이 있으나 그 축은 별건이며, 본 SPEC은 *"메우지 못했을 때 어떻게 말하는가"*만 책임진다. 상한 인상은 라운드트립 비용(측정 66.7 ms/read, `tools.py:755-757`)과 맞바꿈이다. **※ 2026-08-07 정정 — 이 문면이 후속을 잘못 유도한다. 상한 인상은 트레이드오프가 아니라 봉쇄다.** MA3 커맨드라인이 **~2048바이트를 넘는 회신을 조용히 드롭**하고 `Cmd()`는 그때도 성공을 보고한다(`console/lua/copilot_responder.lua:33`, `:36-39` — 라이브 스윕 **2000 배달 / 2100 유실**; `.moai/specs/SPEC-COPILOT-DASHUI-001/progress.md:213`). `max_payload = 1900`은 그 **하드 한계의 마진**이며 올릴 여지가 없다. **실현 가능한 완화는 페이지네이션(offset 인자) 하나이고 응답기 개정을 요구한다** — 그 자리가 위에 적힌 `prechk/inventory.py:400-404`의 `recover_truncated` 슬롯이다. 라운드트립 비용은 **페이지네이션을 택했을 때의 부수 고려사항**이지 상한 인상의 대가가 아니다.

### Out of Scope — 정렬 어휘 개명 · 축 점수 비교
- SPATIAL `progress.md:646`의 후속 과제 2(`left_to_right` → house 기준 명시)와 `SPEC-COPILOT-AXISCORE-001`. 본 SPEC과 파일 교차는 `tools.py` 한 파일이나 **표적 심볼이 분리**되어 병렬 가능하다.

### Out of Scope — 툴 설명문의 문면 강화를 성공 기준으로 삼는 일
- 설명문 갱신은 **의무이나 증거가 아니다**(REQ-TRUNCATE-014). `tools.py:4847-4849`의 `Returns {...}` 문면은 형상 변경으로 **거짓이 되므로 반드시 갱신**된다. 그러나 *"say so"*를 더 강하게 적는 것은 이미 실패한 수단이며(`progress.md:499`) 어떤 AC의 통과 조건도 아니다.

## E. 성공 기준

**모든 기준은 구조적이다** — 모델 순응에 의존하는 항목은 성공 기준에 **없다**(REQ-TRUNCATE-013).

| 기준 | 확인 수단 | 성격 |
|---|---|---|
| 부분 회신에 `fixtures` 키 **부재** | `assert "fixtures" not in reply` + 뮤테이션 | **구조** |
| 부분 회신에 `analysis` 키 **부재** | `assert "analysis" not in reply` + 뮤테이션 | **구조** |
| 부분 회신이 결손 산술(총수/도착/미판독)을 운반 | 라이브 형상 재현 단위 | **구조** |
| 완전 회신은 오늘 형상 그대로 | 기존 회귀 (비공허성 짝) | 회귀 |
| `truncated` / `roundtrip_capped` 분리 보존 | 기존 단정 7건 | 회귀 |
| 부분 토폴로지 계약(GROUPGEN-024) 무변경 | `test_groupgen_tools.py` 9건 | 회귀 |
| `create_arrangement_groups`가 부분 유래 그룹 거부 | 단위 | **구조** |
| `TOOL_NAMES` 22 불변 · `rig_section` 무변경 | `test_tools.py:147-148` + byte-diff | 회귀 |
| `server/spatial/**` byte-diff 0 | byte-diff | 회귀 |
| 라이브 1턴에서 모델이 고지 | ASSUMPTION-71 | **보조 증거 — 반증 전용** |
