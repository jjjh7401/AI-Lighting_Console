# 인수 기준 — 절단 고지의 구조적 강제

base `origin/main` = `b1a630e` · 판정 원칙: **성공은 구조에 걸고 라이브는 반증 전용이다**(REQ-TRUNCATE-013).

**뮤테이션 규약**: 각 AC는 *"어떤 코드를 제거하면 RED가 되는가"*를 명시한다. 표적은 **분기 코드 자체**이며 테스트 리그가 아니다. 그리고 각 AC는 **비공허성 짝**을 갖는다 — 완전 판독 경로에서 같은 단정이 반대로 성립해야 한다. 하드코딩된 상수가 통과시킬 수 있는 AC는 무효다.

**공용 재료**: 라이브 실측 형상 — `childCount 19` / 반환 `children` 18 / `truncated: true`(SPATIAL `progress.md:113-120`). `test_spatial_context.py:338-354`가 이미 이 리그를 만든다. 재료가 절단 경계를 넘는다는 사실이 뮤테이션 함정을 무력화한다(plan.md §E 위험 6).

---

## A. 시나리오 (Given–When–Then)

### 시나리오 1 — 부분 리그에서 정렬 결과가 아예 존재하지 않는다 (핵심)

- **Given** 스테이지 패치 컨테이너가 `childCount 19`를 보고하고 `children` 18개만 넘기며 `truncated: true`다.
- **When** `get_spatial_context`가 호출된다.
- **Then** 회신에 **`fixtures` 키가 없고 `analysis` 키도 없다.** 18대의 좌표는 `partial_fixtures`에 있고, `analysis_withheld`가 보류 사유를, `missing`이 `{expected: 19, received: 18, unseen_count: 1}`을 운반한다. **모델이 인용할 수 있는 좌우 정렬은 어디에도 계산되어 있지 않다.**

### 시나리오 2 — 완전 리그는 어제와 똑같다 (비공허성)

- **Given** 컨테이너가 `childCount 18` / `children` 18 / `truncated: false`다.
- **When** 같은 툴이 호출된다.
- **Then** 회신은 **오늘 형상 그대로**다 — `fixtures` **존재**, `analysis` **존재**, `partial_fixtures`·`analysis_withheld`·`missing` **부재**. 시나리오 1의 단정을 하드코딩으로 통과시킬 수 없다는 짝이다.

### 시나리오 3 — 완전 형상을 향해 쓰인 코드가 조용히 지나갈 수 없다

- **Given** 완전 회신을 전제로 `reply["fixtures"]`를 읽는 소비자가 있다.
- **When** 부분 회신이 그에게 전달된다.
- **Then** **`KeyError`가 난다.** 부분 목록을 완전 목록으로 오소비하는 경로가 **구조적으로 존재하지 않는다.** 이것이 boolean 플래그와 키 부재의 차이다.

### 시나리오 4 — 이 툴이 멈춘 것도 같은 분기를 탄다

- **Given** 리그가 라운드트립 상한을 넘는다(`SPATIAL_PROPERTY_QUERY_CAP = 120` / 4프로퍼티 = **30대** 경계, `tools.py:615`·`:628`).
- **When** 판독이 예산 고갈로 멈춘다(`roundtrip_capped: true`, `truncated: false`).
- **Then** 부분 형상이 **동일하게** 적용된다. 그러나 두 신호는 **분리 보고를 유지한다** — `truncated: false` / `roundtrip_capped: true`. 오직 후자만 다시 물어 고칠 수 있다는 REQ-SPATIAL-006의 구분은 보존된다.

### 시나리오 5 — 부분 판독은 실패가 아니다

- **Given** 절단이 측정 리그의 **기본 경로**다(`prechk/inventory.py:5-9`).
- **When** 부분 회신이 반환된다.
- **Then** `is_error=False`다. 자기수정 루프가 같은 리그를 재판독하는 재시도로 낭비되지 않는다.

### 시나리오 6 — 부분 토폴로지 계약은 살아 있다 (교차 SPEC)

- **Given** `classify_arrangement_topology`가 같은 판독 함수를 재사용한다(`tools.py:3533`).
- **When** 부분 판독 위에서 토폴로지가 판정된다.
- **Then** `topology_partial: true` · `topology_partial_reason` · `topology.partial` · 그룹별 `axis`/`topology_partial`이 **문면 그대로** 나온다(`tools.py:3559-3575`, `:3608-3632`). 본 SPEC은 GROUPGEN-024 amendment를 **대체하지 않는다.**

### 시나리오 7 — 죽어 있던 플래그가 일한다

- **Given** `create_arrangement_groups`가 오늘 `topology_partial`을 **한 번도 읽지 않는다**(`tools.py:3642-` grep 0건).
- **When** `topology_partial: true`를 실은 그룹이 명시 확인 없이 쓰기로 들어온다.
- **Then** **거부된다.** 콘솔 송신 0건.

### 시나리오 8 — 경계는 움직이지 않는다

- **Given** 두 번째 절단 지점 `rig_section`의 소비자가 호출 11건 + 웹 2파일에 걸쳐 있다.
- **When** 본 SPEC이 착지한다.
- **Then** `rig_section`(`tools.py:474-489`) 무변경 · `TOOL_NAMES` **22 불변** · `server/spatial/**` byte-diff **0** · `server/safety/**`·`server/measurement/**` 무접촉.

---

## B. 인수 기준

### AC-TRUNCATE-001 — 부분 회신에 `fixtures` 키가 없다

**When** 커버리지가 불완전하면(`coverage.complete == False`), the 회신 **shall** `fixtures` 키를 갖지 않고 픽스처 목록을 `partial_fixtures`에 담는다.

- 대상 요구: REQ-TRUNCATE-001 · 002
- **통과 판정**: 단위 — 실측 리그(19/18/`truncated:true`)에서 `"fixtures" not in reply` **AND** `len(reply["partial_fixtures"]) == 18`. 절단 사유 3종 전건에서 성립: ① 응답기 플래그 ② `childCount` 산술(플래그 부재) ③ `roundtrip_capped`.
- **뮤테이션**: `read_spatial_fixtures`(`tools.py:783-802`)의 **형상 분기를 제거**하고 단일 반환으로 되돌리면 전건 RED. 분기 술어(`coverage.complete` 판독)를 상수 `True`로 고정해도 RED.
- **비공허성 짝**: 완전 리그(18/18/`false`)에서 `"fixtures" in reply` **AND** `"partial_fixtures" not in reply`. → 두 단정이 서로를 하드코딩으로부터 보호한다.

### AC-TRUNCATE-002 — 부분 회신에 `analysis` 키가 없다 (핵심 AC)

**When** 커버리지가 불완전하면, the 회신 **shall** `analysis` 키를 갖지 않고 `analysis_withheld`가 보류 사유를 운반한다.

- 대상 요구: REQ-TRUNCATE-003
- **근거**: 모델이 제시한 것이 **바로 이 필드**다(`progress.md:496-498`). 그리고 `analyze_spatial_records`는 records 외 인자를 받지 않으므로(`server/spatial/rows.py:202-204`) 그 산출물은 **자신이 부분임을 표현할 능력이 없다** — 실측 리그에서 `low_confidence: False`(`server/spatial/schema.py:249`).
- **통과 판정**: 단위 — `"analysis" not in reply` **AND** `"analysis_error" not in reply`(보류는 실패가 아니다) **AND** `reply["analysis_withheld"]`가 사유를 담는다. 추가로 **회신 JSON 전체에 `row_order` 문자열이 등장하지 않는다** — 중첩 어디에도 정렬 결과가 없음을 확인하는 단정.
- **뮤테이션**: `get_spatial_context`(`tools.py:3059-3060`)의 **부분 시 `analysis` 계산 생략을 제거**하면(= 오늘처럼 무조건 계산) RED. `analysis_withheld`만 추가하고 `analysis`를 함께 남기는 절충(M0 갈래 ③)도 이 AC에서 RED — **가산은 강제가 아니다.**
- **비공허성 짝**: 완전 리그에서 `"analysis" in reply` **AND** `reply["analysis"]["row_order"]`가 실제 값을 갖는다.

### AC-TRUNCATE-003 — 결손이 산술로 명시된다

**Where** 회신이 부분인 경우, the 회신 **shall** 콘솔 보고 총수·실제 도착 수·미판독 수를 명시한다.

- 대상 요구: REQ-TRUNCATE-004
- **통과 판정**: 단위 — `reply["missing"] == {"expected": 19, "received": 18, "unseen_count": 1}`. *"불완전하다"*가 아니라 *"19 중 18, 1대 미판독"*이다(`prechk/inventory.py:10-17`의 동일 규율 — 플래그는 *얼마나* 를 말하지 않고 결손량이 독자가 필요한 값이다).
- **뮤테이션**: `missing` 산술을 제거하거나 `unseen_count`를 `len(children)` 기반으로 잘못 유도하면 RED. `expected`를 `len(children)`으로 바꾸면(= 도착분을 총수로 오독 — `inventory.py:16-17`이 기록한 실제 조사 오류) RED.
- **비공허성 짝**: 캡 경로(30대 초과)에서 `expected`/`received`가 **다른 값**을 갖는다 → 상수 19/18 하드코딩 불가.

### AC-TRUNCATE-004 — 완전 경로는 오늘 형상 그대로다

**When** 커버리지가 완전하면, the 회신 **shall** 개정 전과 **동일한 키 집합**을 갖는다.

- 대상 요구: REQ-TRUNCATE-001(대우) · plan.md §E 위험 4
- **통과 판정**: 회귀 — `test_spatial_context.py` **32건 전건 GREEN**. 완전 경로 단정(`["fixtures"]` 17건 중 절단 무관분)은 **한 줄도 수정되지 않는다.** 수정된 것은 절단 계열(8건)·캡 계열(7건)뿐이며, 수정 내역이 diff에서 그 범위를 넘으면 이 AC는 실패다.
- **뮤테이션**: 분기 술어를 반전시키면(완전 리그가 부분 형상을 받으면) 전건 RED.
- **비공허성**: `test_spatial_context.py:375-379`가 이미 *"Non-vacuity for the three above: a hardcoded True would pass them all"*라는 짝을 갖고 있으며 그것을 계승한다.

### AC-TRUNCATE-005 — 두 절단 신호는 분리 유지, 분기 조건만 통합

**While** 부분 형상이 적용되는 동안, the 회신 **shall** `truncated`와 `roundtrip_capped`를 **개별 필드로** 유지한다.

- 대상 요구: REQ-TRUNCATE-005 · ASSUMPTION-73
- **통과 판정**: 단위 — ① 콘솔 절단: `truncated: true` / `roundtrip_capped: false` ② 예산 고갈: `truncated: false` / `roundtrip_capped: true`. **두 경우 모두 부분 형상**(`"fixtures" not in reply`). 오직 후자만 다시 물어 고칠 수 있다는 구분이 보존된다.
- **뮤테이션**: 두 필드를 단일 `incomplete` boolean으로 병합하면 RED — REQ-SPATIAL-006 위반. 분기 술어를 `truncated`만으로 좁히면 ②가 RED(**30대 초과 리그에서 같은 침묵이 재발하는 경로**).
- **비공허성 짝**: 완전 리그에서 두 필드가 모두 `false`이고 형상은 완전이다(`test_spatial_context.py:375-379` 계승).

### AC-TRUNCATE-006 — 부분 판독은 에러가 아니다

**When** 부분 회신이 반환되면, the 툴 실행 **shall** `is_error=False`로 보고한다.

- 대상 요구: REQ-TRUNCATE-006
- **통과 판정**: 단위 — `execution.result.is_error is False`. 근거: 절단은 측정 리그의 **기본 경로**이며(`prechk/inventory.py:5-9`), 에러 표시는 자기수정 루프에 같은 리그 재판독만 먹인다(`tools.py:3074-3079`).
- **뮤테이션**: `is_error=True`로 바꾸면 RED. (D1 refuse-or-narrow 설계가 이 AC와 정면 충돌한다 — 기각의 기계적 표현이다.)
- **비공허성 짝**: 컨테이너가 **아예 답하지 않은** 경우는 여전히 `is_error=True`(`tools.py:3054-3057`) → 이 AC가 모든 에러를 지우는 것이 아님을 확인한다.

### AC-TRUNCATE-007 — GROUPGEN 부분 토폴로지 계약 무변경 (교차 SPEC)

**Where** `classify_arrangement_topology`가 같은 판독을 재사용하는 경우, the 툴 **shall** 기존 부분 토폴로지 계약을 문면 그대로 유지한다.

- 대상 요구: REQ-TRUNCATE-007 · ASSUMPTION-74
- **통과 판정**: 회귀 — `test_groupgen_tools.py`의 `topology_partial` **9건** + `coverage` **7건** GREEN. 부분 판독에서 `topology_partial: true`, `topology_partial_reason` 비어 있지 않음, `topology.partial: true`, 기하 그룹마다 `axis: "geometry"` + `topology_partial: true`, 종(species) 그룹은 **여전히 `topology_partial` 키를 갖지 않는다**(`tools.py:3596-3599`).
- **뮤테이션**: `classify_arrangement_topology`가 새 키를 읽지 못하게 하면(`reply["fixtures"]` 그대로 두면) **`KeyError`로 즉시 RED** — 시나리오 3의 강제력이 인프로세스에서도 작동한다는 증거다. `coverage` 폴백(`tools.py:3554-3558`)을 제거하면 RED.
- **비공허성 짝**: 완전 판독에서 `topology_partial: false` **AND** `topology_partial_reason == ""`(`tools.py:3567-3568`).

### AC-TRUNCATE-008 — 죽어 있던 플래그가 쓰기를 막는다

**When** `create_arrangement_groups`가 `topology_partial: true` 그룹을 명시 확인 없이 받으면, the 툴 **shall** 거부한다.

- 대상 요구: REQ-TRUNCATE-008 · ASSUMPTION-75 (M0 갈래 ① 승인 조건부)
- **통과 판정**: 단위 — 기록 콘솔 송신 **0건** + 에러 회신이 **어느 그룹이 부분 유래인지 이름으로** 지목. 명시 확인 인자를 주면 통과한다.
- **뮤테이션**: 거부 분기를 제거하면 RED. **개정 전 base에서 이 단정은 이미 RED다** — 해당 핸들러(`tools.py:3642-`)가 `topology_partial`을 **한 번도 읽지 않으므로**(grep 0건) 오늘은 그냥 통과시킨다. 즉 이 AC는 **실측된 구멍을 직접 지목한다.**
- **비공허성 짝**: `topology_partial: false` 그룹은 **정상 통과**한다 → 무조건 거부가 아니다. 그리고 종(species) 그룹은 `topology_partial` 키가 없으므로 영향받지 않는다.

### AC-TRUNCATE-009 — 경계 무접촉

**While** 본 SPEC이 진행되는 동안, the 개정 **shall not** 선언된 PRESERVE 경계를 넘는다.

- 대상 요구: REQ-TRUNCATE-009 · 010 · 011 · 012
- **통과 판정**: 기계 — ① `git diff origin/main -- server/spatial/ server/safety/ server/measurement/` **비어 있음** ② `rig_section`(`tools.py:474-489`) 및 11 호출점(`server/web/dash.py`·`server/web/panel.py` 포함) 무변경 ③ `test_tools.py:147-148`의 `len(names) == len(TOOL_NAMES) == 22` GREEN·**무수정** ④ 툴 파라미터 스키마(`tools.py:4884`) 무변경 ⑤ 절단 판정(`:730-732`)·`coverage` 산술(`:795-801`) 문면 보존.
- **뮤테이션**: 해당 없음(경계 AC). 위반 자체가 판정이다.
- **비공허성**: ③은 리터럴 `22`가 실제로 존재하므로 툴 1건만 추가해도 즉시 RED다 — 새 툴 신설형 설계(D3)가 이 AC에서 자동 기각되는 기계적 표현이다.

### AC-TRUNCATE-010 — 성공 기준의 구조성 (메타 AC)

**Where** 성공을 판정하는 경우, the 판정 **shall** 모델 순응에 의존하는 항목을 근거로 삼지 않는다.

- 대상 요구: REQ-TRUNCATE-013 · 014
- **통과 판정**: 코드 리뷰 — ① AC-001~009 전건이 **콘솔·모델 무접촉 단위/회귀**로 판정된다 ② 라이브 관측(M4)은 어떤 AC의 통과 조건에도 등장하지 않는다 ③ 툴 설명문 갱신(`tools.py:4847-4849`)은 **의무이나 어떤 AC의 통과 조건도 아니다** — 형상 변경으로 `Returns {...}` 문면이 거짓이 되므로 갱신하되, *"더 강하게 적었다"*는 증거가 아니다.
- **비대칭 명시**: 라이브 1턴의 **통과는 증거가 아니고**(그 모델이 그 턴에 순응했다는 것뿐) **실패만 증거다**(ASSUMPTION-71 NEGATIVE → D3 승격, plan.md §E 위험 2).
- **잔여 위험 명시 의무**: 모델이 `partial_fixtures`를 읽고 직접 정렬을 발명해 침묵하는 경로는 **열린 채로 남는다.** 이 AC는 그것이 **문서에 정직하게 적혀 있을 것**을 요구한다(plan.md §E 위험 1) — 은폐하면 실패다.

---

## C. 판정 매핑 (라이브 · 보조 증거)

| 판정 어휘 | 행두 접두 | 비고 |
|---|---|---|
| `GO` | `GO:` | 전제 성립 — 해당 축 진행 |
| `NEGATIVE` | `DESCOPE:` | 전제 부정 — 해당 축 강등·중단 |
| `INCONCLUSIVE` | `DESCOPE:` + `verdict=INCONCLUSIVE` 키 **의무** | 판정 불능 |
| `CONDITION_NOT_MET` | `SKIP:` | 전제 미성립(프로브 불가·미실행) |
| `REOPEN_SCOPE` | `REOPEN:` | 범위 재개 필요 |

표는 본 SPEC의 정본이다 — 교차 SPEC 포인터 상속은 결함으로 판정된 바 있다(SPATIAL REQ-SPATIAL-026 계승).
