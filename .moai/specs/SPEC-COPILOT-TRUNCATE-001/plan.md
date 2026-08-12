# 구현 계획 — 절단 고지의 구조적 강제

base `origin/main` = `b1a630e` · 브랜치 `spec/truncate-001` · 판정 원칙: **성공은 구조에 걸고 라이브는 반증 전용이다**(REQ-TRUNCATE-013).

> **base 이동 예정 — 머지 후 rebase 필요.** WRITEGATE-001의 PR #26이 `origin/main`에 들어가면 base가 `b1a630e`를 넘어 WRITEGATE를 포함한다. 본 문서·`acceptance.md`·`research.md`의 base 표기와 `git diff origin/main -- …` 경계 확인(§G · AC-TRUNCATE-009 ①)은 **rebase 후 새 base 기준으로 다시 읽는다.** 파일 무교차(`server/safety/**` vs `server/orchestrator/tools.py`)이므로 충돌은 예상되지 않으며, 경계 diff의 기대값(비어 있음)도 바뀌지 않는다.

## A. 승계된 결정 (재논의하지 않는다)

1. **설계 방향은 조사 결과가 아니라 승계된 판정이다.** SPATIAL sync가 *"회신을 구조적으로 다르게 만들어야 한다"*를 이미 처방했다(`progress.md:502-503`, `:645`). 본 계획이 더한 것은 *어느 키를, 왜, 어느 폭발반경으로* 다.
2. **문면 강화는 수단에서 제외된다.** `progress.md:499`가 *"툴 설명은 지시일 뿐 강제가 아니다"*를 천장으로 기록했고, GROUPGEN-024 amendment의 `topology_partial` 추가가 **한 SPEC 앞서 같은 축을 이미 소진했다**(`tools.py:3559-3575`).
3. **성공 기준은 라이브에 걸지 않는다.** 결함이 *모델이 지시를 무시한 사건*이므로 라이브 통과는 증거가 아니다 — 비대칭(`research.md` §6).

## B. 설계 결정 — 왜 키의 부재인가

### B.1 채택안 — Shape divergence (부분 회신의 최상위 스키마 분기)

분기 술어는 **`coverage.complete == False` 하나**다(`tools.py:798-800` — 이미 `truncated` OR `roundtrip_capped` OR 카운트 불일치를 합쳐 놓았다). 새 판정 로직은 없다.

| | 완전 회신 (오늘 그대로) | 부분 회신 (신규 형상) |
|---|---|---|
| 픽스처 목록 | `fixtures` | **`partial_fixtures`** — `fixtures` 키는 **부재** |
| 행 구조 | `analysis` | **부재** → `analysis_withheld{reason, …}` |
| 결손 산술 | — | `missing{expected, received, unseen_count}` |
| 절단 신호 | `truncated` · `roundtrip_capped` | **동일하게 분리 유지**(REQ-TRUNCATE-005) |
| `coverage` | 그대로 | 그대로 |
| `is_error` | `False` | **`False`**(REQ-TRUNCATE-006) |

**왜 부재가 강제인가**: boolean은 데이터 옆에 있어 읽지 않아도 payload가 온전히 소비된다. **부재는 무시할 수 없다 — 무시할 대상이 없다.** 완전 형상을 향해 쓰인 코드는 `KeyError`를 받고, 완전 형상을 향해 쓰인 프롬프트는 참조할 것을 찾지 못한다.

**왜 `analysis` 제거가 핵심인가**: §1의 모델이 제시한 것은 **좌우 정렬**이며 그것이 `analysis.row_order`다. 그리고 `analyze_spatial_records`는 records 외 인자를 받지 않으므로(`server/spatial/rows.py:202-204`) 그 필드는 **자신이 부분임을 표현할 능력이 없다** — 측정 리그에서 `low_confidence: False`다. **인용 가능한 정렬 결과를 남기지 않는 것**이 요구의 본질이다.

### B.2 기각한 대안과 그 이유

| 안 | 기각 이유 (실측) |
|---|---|
| **D1 · Refuse-or-narrow** — 절단 시 목록 미반환, 좁히라는 에러 회신 | ① **라이브 기능 사망**: `prechk/inventory.py:5-9`가 *"Truncation is the DEFAULT path, not an edge case"*라 적고 측정 리그가 19대에서 이미 절단된다 → `get_spatial_context`가 캘리브레이션 리그에서 **항상 실패**한다. ② **교차 SPEC 계약 파괴**: `classify_arrangement_topology`의 부분 토폴로지(`tools.py:3547-3569`)는 *부분 판독이 존재한다*는 전제 위에 있다 → `topology_partial`이 도달 불가 죽은 코드가 되고 `test_groupgen_tools.py` **9건**이 무의미해진다. ③ `fx`/`scene`이 거부할 수 있는 것은 그쪽 질문이 *"빈 번호를 골라라"*(부분 목록으로 **답이 틀려진다**)이기 때문이다. **18대의 좌표는 18대에 대해 여전히 참이다** — 질문의 성격이 달라 규율을 그대로 옮길 수 없다. |
| **D3 · 오염된 payload / 필수 확인응답** | ① 새 툴 → `TOOL_NAMES` 22→23, `test_tools.py:148`의 `== 22` 리터럴 파괴. ② 필수 인자 → `get_spatial_context`는 **인자 0개**(`tools.py:4884`)이고, 토큰을 알려면 먼저 호출해야 하는데 호출하려면 토큰이 필요하다 → **첫 호출 불가**. ③ 호출 간 토큰 보관 = 무상태 툴 계층에 **새 상태면**. → **유일하게 확인응답을 구조적으로 강제하는 안**이므로 ASSUMPTION-71 NEGATIVE 시 승격 경로로 보류(§E 위험 2). |
| **D4 · 하류 거부 (전면)** | **결함을 오진한다.** `arrange_fixtures`는 이미 명시 `fids`를 요구하고(`tools.py:3104-3110` *"never widens the set itself"*), `tools.py:3550-3553`은 쓰기 경로가 리그 절단에 영향받지 않도록 **의도적으로 설계**되어 있다. 관측도 같다 — **fid 19는 원점에 남았고 쓰기는 지시받은 대로 정확히 동작했다**(`progress.md:491`). 결함은 나쁜 쓰기가 아니라 **침묵**이다. 툴은 *"18개인 이유가 운영자의 뜻인지 절단인지"*를 호출 간 상태 없이 구별할 수 없다(D3와 같은 벽). **단 좁은 한 조각은 채택**(REQ-TRUNCATE-008) — `create_arrangement_groups`가 `topology_partial`을 **전혀 읽지 않는다**(grep 0건)는 실측 누락. |
| **`analyze_spatial_records`에 커버리지 인자 추가** | `server/spatial/**`는 순수 기하 계층이다. 판독 완전성을 주입하면 `low_confidence`가 두 축(기하 확산 / 커버리지)으로 오염되고, `tools.py:4876-4879`가 그 필드를 *"패치됐으나 위치 미설정"*으로 못박은 계약이 깨진다. **보류는 툴 계층에서 한다**(REQ-TRUNCATE-012). |
| **`rig_section`까지 동시 분기** | 호출 **11건** + `server/web/dash.py`·`server/web/panel.py` 웹 계층 + 절단 거부 4모듈 + `looks/resolver.py:200` + `paperwork/data.py:183` + `paperwork/render.py:118-125`. 한 창에 담을 수 없다 → spec.md §D. |

### B.3 파괴적 변경의 성격 — 정직하게

이것은 **출하된 회신 형상의 파괴적 변경**이다. 완화 요소와 비완화 요소를 모두 적는다:

- **완화**: 회신 JSON을 파싱하는 **서버측 프로덕션 코드는 없다**(`research.md` §4.1). `json.dumps`(`tools.py:3073`) 이후 소비자는 모델뿐이고, 함수 dict의 인프로세스 소비자는 `classify_arrangement_topology` **1곳**이다. `TOOL_NAMES`·툴 파라미터·웹 계층은 무접촉이므로 **폐쇄 툴 집합에는 비파괴**다.
- **비완화**: 그럼에도 모델을 향한 **계약**이 바뀐다. SPATIAL `progress.md:646`은 동류 변경(`left_to_right` 개명)을 *"출하된 폐쇄 집합의 파괴적 변경이므로 **SemVer major 창에서만**"*으로 판정했다. **본 변경에는 그 선례를 적용하지 않기로 사용자가 결정했다**(2026-08-05 — §C M0 결정 ①). 선례의 폐기가 아니라 **명시적 예외**이며, 개명 과제 자체는 여전히 major 창 대기다(spec.md §D — 정렬 어휘 개명). 두 사안이 갈리는 지점과 예외의 대가는 §C M0.1에 적는다.

## C. 마일스톤

### M0 — 결정 게이트 (완료 · 코드 변경 없음)

**세 건 모두 2026-08-05에 결정됐다. 게이트는 열렸다** — 결정 ①이 APPROVE이므로 M1이 착수 가능하다. 이 절은 더 이상 미결 항목이 아니라 **결정의 기록**이며, 표 아래 M0.1~M0.3이 각 결정의 배후 분석과 **기각된 갈래 및 그 기각 사유**를 보존한다(재논의하지 않기 위해 남긴다).

| # | 물음 | 결정 | 결정자 | 근거 | 거동 귀결 |
|---|---|---|---|---|---|
| ① | 출하된 회신 형상의 파괴적 변경을 **이번 창에서** 허용하는가 (ASSUMPTION-72) | **이번 창에서 수행** (갈래 ①) | **사용자** · 2026-08-05 | 폐쇄 툴 집합에는 **반파괴**다 — `TOOL_NAMES` 22 유지, `test_tools.py:148`의 `== 22` 무접촉, 툴 파라미터 스키마 무접촉, 인프로세스 소비자는 **정확히 1곳**(`classify_arrangement_topology`). 지연 비용이 확정적이다(M0.1) | M1 착수. 부분 회신에서 `fixtures`·`analysis` 키가 **사라진다.** 갈래 ②③④ 기각 확정. `progress.md:646` 선례에 대한 **명시적 예외**로 기록한다(M0.1) |
| ② | `roundtrip_capped`도 같은 형상 분기를 촉발하는가 (ASSUMPTION-73) | **동급 처리** (갈래 ①) — **신호는 분리 유지 · 분기만 통합** | **에이전트** · 2026-08-05 | 두 신호 모두 *"이 목록은 전부가 아니다"*를 뜻하고 `coverage.complete`가 이미 둘을 OR로 합친다(`tools.py:798-800`) → 분기 술어는 하나로 족하다. 분리하면 **30대 초과 리그에서 같은 침묵이 재발**한다(M0.2의 경계 산술) | 분기 술어 = `coverage.complete == False` **단일**. 부분 회신에서도 `truncated`·`roundtrip_capped`는 **개별 필드로 나란히** 남는다(REQ-TRUNCATE-005 · REQ-SPATIAL-006). AC-TRUNCATE-005가 두 전건을 모두 판정 |
| ③ | `create_arrangement_groups` 거부가 본 SPEC 범위인가 (ASSUMPTION-75) | **포함** (갈래 ①). 확인 인자는 **미판독 fid의 명시 열거** — 불리언 아님 | **에이전트** · 2026-08-05 | 실측된 누락이고(`:3642` 이하 `topology_partial` grep **0건**) 변경이 핸들러 국소다. 제외하면 `:3575`가 그룹마다 실어 보낸 플래그가 계속 죽은 채 남는다. 인자 형태의 근거는 M0.3 | REQ-TRUNCATE-008 · AC-TRUNCATE-008이 M2에 **무조건** 남는다(조건부 아님). 확인 인자 `acknowledged_unread_fids: list[int]`가 M0.3의 수용 조건을 전건 만족할 때만 통과. **불리언 수용은 AC RED** |

#### M0.1 — 결정 ①: 선례에 대한 명시적 예외, 그리고 그 대가

**선례**: SPATIAL `progress.md:646`(후속 과제 2)은 동류 변경 — `left_to_right` → house 기준 개명 — 을 *"출하된 폐쇄 집합의 파괴적 변경이므로 SemVer major 창에서만"*으로 판정했다.

**판정**: 그 선례를 **본 변경에는 적용하지 않는다**(사용자, 2026-08-05). 선례를 뒤집는 것이 아니라 **예외를 두는 것**이며, 개명 과제 자체는 여전히 major 창 대기다(spec.md §D 범위 밖 — 정렬 어휘 개명 · `SPEC-COPILOT-AXISCORE-001`).

**왜 갈리는가 — 바뀌는 계약의 *면*이 다르다.** 본 변경은 **모델을 향한 계약**만 바꾸고 **코드 계약은 바꾸지 않는다.** 실측 4건이 그 경계다:

| 코드 계약 항목 | 본 변경에서 | 근거 |
|---|---|---|
| `TOOL_NAMES` 종수 | **22 그대로** | `tools.py:127-150` · REQ-TRUNCATE-010 |
| `test_tools.py:148`의 `len(names) == len(TOOL_NAMES) == 22` | **무수정** | AC-TRUNCATE-009 ③ |
| 툴 파라미터 스키마(`tools.py:4884` — 인자 0개) | **무변경** | AC-TRUNCATE-009 ④ |
| 회신 dict의 인프로세스 소비자 | **정확히 1곳** — `classify_arrangement_topology` | `research.md` §4.1 전수 |

회신 JSON을 파싱하는 서버측 프로덕션 코드는 **없다**(`json.dumps`, `tools.py:3073` 이후의 소비자는 모델뿐). 단 하나의 인프로세스 소비자는 **같은 창에서 함께 전환된다**(M2 · REQ-TRUNCATE-007). 즉 파괴는 **모델의 기대**에만 닿는다.

**지연 비용 — 보류하면 무엇이 열린 채 남는가.** 관측된 결함이 그대로 산다: `childCount 19` / 반환 18 / `truncated: true`인 판독 위에서 **`low_confidence: False`인 고신뢰 좌우 정렬**이 완전 판독과 형상으로 구별되지 않은 채 회신에 실린다(`progress.md:485` — *"x 확산으로 1행 고신뢰"*, 18대 판독 위 실측). **존재하지 않는 19대 리그에 대한 정렬을 툴이 계속 발행한다**는 상태를 major 창까지 유지한다는 뜻이며, 이 결함이 본 SPEC의 존재 이유다. 사용자는 이 대가를 알고 예외를 승인했다.

**기각된 갈래(재논의 없음)**:
- **② major 창까지 보류** — 위 지연 비용을 감수한다. 기각.
- **③ 가산 절충**(`fixtures` 유지 + `partial_fixtures` 추가) — **강제력이 0이다.** 완전 형상을 향해 쓰인 소비자가 계속 조용히 동작하므로 오늘과 같다. AC-TRUNCATE-002가 이 갈래를 기계적으로 RED로 만든다.
- **④ 빈 리스트**(부분 회신에서 `fixtures: []`) — 키는 있으나 데이터가 없다. `KeyError` 대신 *"0대 리그"*라는 **새로운 거짓말**을 만든다. 기각.

#### M0.2 — 결정 ②: `roundtrip_capped` 동급 처리 (신호 분리 · 분기 통합)

**경계 산술이 근거다.** `SPATIAL_PROPERTY_QUERY_CAP = 120`(`tools.py:628`) ÷ 픽스처당 4프로퍼티(`:615` — `("fid","posx","posy","posz")`) = **30대**. 30대를 넘는 리그는 콘솔이 자르지 않아도 **이 툴이 스스로 멈춘다**(`:761-763`). 그러므로 분기를 `truncated`에만 걸면 **30대 초과 리그에서 §1의 침묵이 그대로 재발한다** — 결함의 형상은 같고 사유만 다르다. 두 신호 모두 *"이 목록은 전부가 아니다"*이므로 분기 술어를 나눌 근거가 없다.

**분리와 통합의 선**: 통합되는 것은 **분기 술어 하나**(`coverage.complete`, `tools.py:798-800` — 이미 `truncated` OR `roundtrip_capped` OR 카운트 불일치를 합쳐 놓았다)이고, **신호 자체는 분리 보고를 유지한다**(REQ-TRUNCATE-005 · REQ-SPATIAL-006 — 오직 `roundtrip_capped`만 다시 물어 고칠 수 있으므로 독자에게 구분이 필요하다). 부분 회신에서도 두 필드는 개별로 나란히 실린다. 병합하면 AC-TRUNCATE-005가 RED다.

**기각된 갈래**: **②** `truncated`만 분기 — 위 30대 경계 산술로 기각.

#### M0.3 — 결정 ③: 범위 포함, 그리고 확인 인자는 **fid 열거**다

**범위 포함의 근거**: 실측 누락이다 — `create_arrangement_groups`(`tools.py:3642-`)에서 `topology_partial`을 grep하면 **0건**이다. `:3575`가 기하 그룹마다 붙여 보낸 플래그가 **쓰기 툴에서 아무 일도 하지 않고 죽는다.** 변경은 해당 핸들러 국소이므로 별건으로 미룰 이유가 없고, 미루면 그 플래그가 계속 죽은 채 남는다(갈래 ② 기각).

**인자 형태 — 불리언이 아니라 미판독 fid의 명시 열거로 한다.** 이것이 본 결정의 실질이다:

- 불리언 `acknowledge_partial: true`는 **무심코 참으로 채워진다.** 무엇이 빠졌는지 읽지 않아도 값이 성립하므로, 확인 인자가 다시 *"데이터 옆의 boolean"* — **본 SPEC이 §B.1에서 기각한 바로 그 형상**이 된다.
- 미판독 fid를 열거하게 하면 호출자는 **판독된 fid 집합과 결손 산술을 실제로 읽어야** 값을 만들 수 있다. 회신이 이미 그 재료를 운반한다(`missing{expected, received, unseen_count}` · REQ-TRUNCATE-004).
- **자기일관성이 결정 근거다.** 본 SPEC의 표적은 *"툴 설명은 지시일 뿐 강제가 아니다"*(`progress.md:499`)이고 처방은 *"무시할 대상이 없게 만든다"*이다. 그 SPEC의 **확인 절차가 무심코 통과되는 불리언**이라면, SPEC은 자기가 닫으려는 결함을 자기 안에서 재생산한다.

**수용 조건**(전건 만족 시에만 쓰기 진행 · REQ-TRUNCATE-008에 고정):

1. `acknowledged_unread_fids`가 **비어 있지 않은 정수 리스트**다. 각 원소는 `isinstance(fid, int) and not isinstance(fid, bool)` — 같은 핸들러가 `groups[].fids`에 이미 쓰는 판정이다(`tools.py:3673-3676`). 불리언 `True`는 파이썬에서 `int`의 부분형이므로 **이 배제가 불리언 확인 인자를 기계적으로 막는 지점**이다.
2. 중복이 없다.
3. **쓰기 대상 fid 집합과 서로소**다 — `⋃ groups[].fids`에 이미 들어 있는 fid를 *미판독*이라 부를 수 없다. 이 조건이 *"판독된 목록을 실제로 읽어야 한다"*를 강제한다.
4. 결손량이 판독 가능하면 **열거 크기가 그 결손량과 일치**한다. 핸들러가 이미 읽는 `fixtures_section`(`tools.py:3699-3703`)의 `total` − 도착 `objects` 수가 그 값이다. `total`이 `None`인 경우(응답기가 `childCount`를 주지 않음 — `tools.py:483-488`이 이를 *"unknown total, never 'the count equals what arrived'"*로 못박는다) 크기 검증은 성립하지 않으므로 1~3만 적용한다.

인자 이름·계약·AC 문면은 REQ-TRUNCATE-008 / AC-TRUNCATE-008이 정본이다.

### M1 — 형상 분기 (본체)

- `read_spatial_fixtures`(`tools.py:783-802`)를 `coverage.complete`에 따라 **두 형상**으로 분기. 판정 로직(`:730-732`)과 `coverage` 산술(`:795-801`)은 **문면 보존**.
- `get_spatial_context`(`:3059-3060`)에서 부분 시 `analysis` 계산 자체를 **건너뛰고** `analysis_withheld`를 싣는다. `is_error=False` 유지(`:3080`).
- `missing{expected, received, unseen_count}` 산술(REQ-TRUNCATE-004).
- **신규** `server/tests/test_truncate_disclosure.py` — AC별 단위 + 뮤테이션 표적.
- 기존 절단 계열 단정 갱신: `test_spatial_context.py`(절단 8 / 캡 7건) — **완전 경로 단정 17건 중 절단과 무관한 것은 건드리지 않는다.**
- 설명문 `tools.py:4847-4849` 갱신(형상 변경의 귀결 — `Returns {...}`가 거짓이 되므로 의무. **증거는 아니다**, REQ-TRUNCATE-014).

### M2 — 인프로세스 소비자 + 좁은 하류 거부

- `classify_arrangement_topology`(`:3533`, `:3541`, `:3554`, `:3610-3613`)가 새 키를 읽는다. **`topology_partial` 계약은 문면 무변경**(REQ-TRUNCATE-007) — `test_groupgen_tools.py` 9건이 판정.
- `create_arrangement_groups`(`:3642-`)가 `topology_partial: true` 그룹을 **미판독 fid 명시 열거**(`acknowledged_unread_fids`) 없이 거부(REQ-TRUNCATE-008). **M0 결정 ③으로 범위 확정 — 조건부가 아니다.** 불리언 확인 인자는 정의하지 않는다(§C M0.3).

### M3 — 회귀 경계 확인

- `server/spatial/**` byte-diff **0** · `rig_section` 및 11 호출점 무변경 · `TOOL_NAMES` 22 불변(`test_tools.py:147-148`) · `server/safety/**`·`server/measurement/**` 무접촉.
- 전 스위트 1회.

### M4 — 라이브 1턴 (보조 증거 · 반증 전용)

- 측정 리그(19대, 절단이 기본 경로)에서 1턴. **통과는 성공 기준이 아니다**(REQ-TRUNCATE-013). 실패면 ASSUMPTION-71 NEGATIVE → D3 승격 검토(§E 위험 2).
- 판정은 폐쇄 어휘(`GO`/`NEGATIVE`/`CONDITION_NOT_MET`/`INCONCLUSIVE`/`REOPEN_SCOPE`) + 행두 접두(`GO:`/`DESCOPE:`/`SKIP:`/`REOPEN:`)로 `progress.md §E`에 기록.

## D. 의존 그래프

```
M0 결정 게이트 ── 3건 전부 결정 완료(2026-08-05) · 결정 ① APPROVE ──> 통과
   │
   v
M1 형상 분기 ──> M2 인프로세스 소비자 + 좁은 하류 거부 ──> M3 회귀 경계 ──> M4 라이브(반증 전용)
```

WRITEGATE-001과는 **파일 무교차**(`server/safety/**` vs `server/orchestrator/tools.py`)이므로 병렬 가능하다. `SPEC-COPILOT-AXISCORE-001`과는 `tools.py` 한 파일을 공유하나 **표적 심볼이 분리**된다.

## E. 위험

| # | 위험 | 완화 |
|---|---|---|
| 1 | **모델이 형상 분기도 무시한다** — `partial_fixtures`를 읽고 직접 정렬을 발명해 침묵할 수 있다. 이것이 남는 진짜 잔여 위험이다. | 완화하되 **은폐하지 않는다.** 개선은 실재한다: 인용할 필드가 없으므로 모델은 **원좌표로 직접 산술**해야 하고, 회신 자체가 결손량을 문장으로 운반한다(REQ-TRUNCATE-004). 그러나 이것은 **순응의 증명이 아니다** → ASSUMPTION-71, M4는 반증 전용. |
| 2 | **ASSUMPTION-71 NEGATIVE** — 라이브에서 여전히 침묵. | D3(필수 확인응답)로 승격. 비용은 확정적이다 — `TOOL_NAMES` 22→23 + `test_tools.py:148` 파괴 + 새 상태면(§B.2). **M0 결정 ①에서 이 비용을 미리 고지했고 사용자는 그것을 알고 승인했다**(2026-08-05, M0.1). |
| 3 | **파괴적 변경의 창 오판** — major 창이 아닌데 진행. | **해소됨.** M0 결정 ①(사용자, 2026-08-05)이 `progress.md:646` 선례에 대한 **명시적 예외**로 이번 창 수행을 승인했다 — 코드 변경 **전에** 결정됐다(M0.1). 예외의 근거는 코드 계약 무접촉 4건이고, 선례 자체는 개명 과제에 대해 여전히 유효하다. |
| 4 | **완전 경로 회귀 파손** — 절단 단정을 고치다 완전 경로 17건을 함께 건드림. | 완전 회신은 **오늘 형상 그대로**가 요구다. `test_spatial_context.py:375-379`의 기존 **비공허성 짝**(*"a hardcoded True would pass them all"*)이 그대로 판정한다. |
| 5 | **GROUPGEN 부분 토폴로지 계약 파손** — M2에서 키 전환 중 `topology_partial`이 죽음. | `test_groupgen_tools.py` **9건**이 회귀. D1을 기각한 이유가 바로 이 계약이므로 **채택안이 그것을 깨면 자기모순**이다. |
| 6 | **뮤테이션 함정 — 재료가 절단 경계 미만** | 측정 리그 19대가 이미 경계를 넘고(`progress.md:113-120`), 캡 경계는 30대다. `test_spatial_context.py:338-354`의 라이브 형상 리그를 재료로 쓰면 함정이 성립하지 않는다 — SPATIAL이 같은 함정을 `design.md §7`로 이미 문서화했다. |
| 7 | **`is_error` 오설정** — 부분 회신을 에러로 표시. | REQ-TRUNCATE-006. 절단은 기본 경로이므로 에러 표시는 자기수정 루프에 **같은 리그 재판독**만 먹인다(`tools.py:3074-3079` 기존 판정 계승). |

## F. 진행 방식

- TDD. AC별로 RED를 먼저 만들고, **개정 전 base에서 그 RED가 실제로 빨간지**를 확인한다(비공허성 — `research.md` §4.3의 기존 관행).
- 각 AC는 **뮤테이션 표적**을 갖는다(acceptance.md §B). 표적은 **분기 코드 자체**이며 테스트 리그가 아니다.
- 커밋은 마일스톤 경계에서. `server/spatial/**`·`server/safety/**`·`server/measurement/**`·`rig_section` 소비자에 **한 줄도 닿지 않는다**.

## G. 확인 명령

```bash
uv run --frozen pytest server/tests/test_truncate_disclosure.py -q          # 신규
uv run --frozen pytest server/tests/test_spatial_context.py -q              # 32건 회귀
uv run --frozen pytest server/tests/test_groupgen_tools.py -q               # 부분 토폴로지 9건
uv run --frozen pytest server/tests/test_tools.py -q                        # TOOL_NAMES 22
git diff --stat origin/main -- server/spatial/ server/safety/ server/measurement/   # 비어야 함
uv run ruff check server/ && uv run ruff format --check server/
```
