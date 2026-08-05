# 구현 계획 — 절단 고지의 구조적 강제

base `origin/main` = `b1a630e` · 브랜치 `spec/truncate-001` · 판정 원칙: **성공은 구조에 걸고 라이브는 반증 전용이다**(REQ-TRUNCATE-013).

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
- **비완화**: 그럼에도 모델을 향한 **계약**이 바뀐다. SPATIAL `progress.md:646`은 동류 변경(`left_to_right` 개명)을 *"출하된 폐쇄 집합의 파괴적 변경이므로 **SemVer major 창에서만**"*으로 판정했다. **그 선례가 본 변경에도 적용되는지는 사람이 결정한다** → M0 `[NEEDS CLARIFICATION]` ①.

## C. 마일스톤

### M0 — 결정 게이트 (라이브 프로브 아님, 코드 변경 없음)

세 건의 사람 결정을 받는다. **①이 NEGATIVE면 M1은 시작하지 않는다.**

- **[NEEDS CLARIFICATION: 출하된 회신 형상의 파괴적 변경이 이번 창에서 허용되는가 (ASSUMPTION-72)]** — 부분 회신에서 `fixtures`/`analysis` 키가 **사라진다.** 선례는 SemVer major 창을 요구한다(`progress.md:646`). 갈래 넷: **①** 이번 창에서 수행(권장 — 폐쇄 툴 집합에는 비파괴이고 프로덕션 소비자가 1곳이다, §B.3) **②** major 창까지 보류(그동안 관측된 결함이 열린 채 남는다) **③** 가산만 하는 절충 — `fixtures`를 남기고 `partial_fixtures`를 **추가**한다(→ **강제력이 0이다.** 완전 형상 소비자가 계속 조용히 동작하므로 오늘과 같다. 기각 권고) **④** 부분 회신에서 `fixtures`를 **빈 리스트**로 남긴다(→ 키는 있으나 데이터가 없다. `KeyError` 대신 *"0대 리그"*라는 **새로운 거짓말**을 만든다. 기각 권고).
- **[NEEDS CLARIFICATION: `roundtrip_capped`도 같은 분기를 촉발하는가 (ASSUMPTION-73)]** — `coverage.complete`는 이미 둘을 OR로 합친다. 갈래 둘: **①** 동급 처리(권장 — 둘 다 *"이 목록은 전부가 아니다"*이며 분기 술어가 하나로 족하다. 신호 자체의 분리는 REQ-TRUNCATE-005로 유지된다) **②** `truncated`만 분기(→ 30대 초과 리그에서 같은 침묵이 재발한다. `SPATIAL_PROPERTY_QUERY_CAP = 120` / 4프로퍼티 = **30대**가 경계이고 실제 리그는 그 위에 있다).
- **[NEEDS CLARIFICATION: `create_arrangement_groups` 거부가 본 SPEC 범위인가 (ASSUMPTION-75)]** — REQ-TRUNCATE-008. 갈래 둘: **①** 포함(권장 — 실측 누락이고 변경이 국소적이다) **②** 별건 분리(→ `:3575`의 플래그가 계속 죽은 채 남는다). 포함 시 추가 결정: 확인 인자의 형태(불리언 `acknowledge_partial` vs 미판독 fid 명시 열거).

### M1 — 형상 분기 (본체)

- `read_spatial_fixtures`(`tools.py:783-802`)를 `coverage.complete`에 따라 **두 형상**으로 분기. 판정 로직(`:730-732`)과 `coverage` 산술(`:795-801`)은 **문면 보존**.
- `get_spatial_context`(`:3059-3060`)에서 부분 시 `analysis` 계산 자체를 **건너뛰고** `analysis_withheld`를 싣는다. `is_error=False` 유지(`:3080`).
- `missing{expected, received, unseen_count}` 산술(REQ-TRUNCATE-004).
- **신규** `server/tests/test_truncate_disclosure.py` — AC별 단위 + 뮤테이션 표적.
- 기존 절단 계열 단정 갱신: `test_spatial_context.py`(절단 8 / 캡 7건) — **완전 경로 단정 17건 중 절단과 무관한 것은 건드리지 않는다.**
- 설명문 `tools.py:4847-4849` 갱신(형상 변경의 귀결 — `Returns {...}`가 거짓이 되므로 의무. **증거는 아니다**, REQ-TRUNCATE-014).

### M2 — 인프로세스 소비자 + 좁은 하류 거부

- `classify_arrangement_topology`(`:3533`, `:3541`, `:3554`, `:3610-3613`)가 새 키를 읽는다. **`topology_partial` 계약은 문면 무변경**(REQ-TRUNCATE-007) — `test_groupgen_tools.py` 9건이 판정.
- `create_arrangement_groups`(`:3642-`)가 `topology_partial: true` 그룹을 명시 확인 없이 거부(REQ-TRUNCATE-008, M0 ③ 승인 시).

### M3 — 회귀 경계 확인

- `server/spatial/**` byte-diff **0** · `rig_section` 및 11 호출점 무변경 · `TOOL_NAMES` 22 불변(`test_tools.py:147-148`) · `server/safety/**`·`server/measurement/**` 무접촉.
- 전 스위트 1회.

### M4 — 라이브 1턴 (보조 증거 · 반증 전용)

- 측정 리그(19대, 절단이 기본 경로)에서 1턴. **통과는 성공 기준이 아니다**(REQ-TRUNCATE-013). 실패면 ASSUMPTION-71 NEGATIVE → D3 승격 검토(§E 위험 2).
- 판정은 폐쇄 어휘(`GO`/`NEGATIVE`/`CONDITION_NOT_MET`/`INCONCLUSIVE`/`REOPEN_SCOPE`) + 행두 접두(`GO:`/`DESCOPE:`/`SKIP:`/`REOPEN:`)로 `progress.md §E`에 기록.

## D. 의존 그래프

```
M0 (사람 결정 3건) ──①NEGATIVE면 중단──> ✗
   │ ①APPROVE
   v
M1 형상 분기 ──> M2 인프로세스 소비자 + 좁은 하류 거부 ──> M3 회귀 경계 ──> M4 라이브(반증 전용)
```

WRITEGATE-001과는 **파일 무교차**(`server/safety/**` vs `server/orchestrator/tools.py`)이므로 병렬 가능하다. `SPEC-COPILOT-AXISCORE-001`과는 `tools.py` 한 파일을 공유하나 **표적 심볼이 분리**된다.

## E. 위험

| # | 위험 | 완화 |
|---|---|---|
| 1 | **모델이 형상 분기도 무시한다** — `partial_fixtures`를 읽고 직접 정렬을 발명해 침묵할 수 있다. 이것이 남는 진짜 잔여 위험이다. | 완화하되 **은폐하지 않는다.** 개선은 실재한다: 인용할 필드가 없으므로 모델은 **원좌표로 직접 산술**해야 하고, 회신 자체가 결손량을 문장으로 운반한다(REQ-TRUNCATE-004). 그러나 이것은 **순응의 증명이 아니다** → ASSUMPTION-71, M4는 반증 전용. |
| 2 | **ASSUMPTION-71 NEGATIVE** — 라이브에서 여전히 침묵. | D3(필수 확인응답)로 승격. 비용은 확정적이다 — `TOOL_NAMES` 22→23 + `test_tools.py:148` 파괴 + 새 상태면(§B.2). **M0에서 이 비용을 미리 알려둔다.** |
| 3 | **파괴적 변경의 창 오판** — major 창이 아닌데 진행. | M0 ①이 게이트다. 코드 변경 전에 결정한다. |
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
