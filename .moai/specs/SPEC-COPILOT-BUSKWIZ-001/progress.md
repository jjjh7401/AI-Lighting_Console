# SPEC-COPILOT-BUSKWIZ-001 — 진행 기록 (progress)

> **인용 규율 (v0.1.3 확정)**: 본 문서가 **정본(spec.md · acceptance.md)** 을 가리킬 때는 줄번호를 쓰지 않고 **안정 토큰**만 쓴다 — `REQ-BUSKWIZ-nnn` · `AC-BUSKWIZ-nnn` · `ASSUMPTION-nn` · 절 제목 · 명명된 하위 절. **`파일:줄` 앵커는 코드 · 룰북 · 타 SPEC 아티팩트에만** 남긴다(그것들은 커밋 없이 움직이지 않고 달리 안정 식별자가 없다). 형제 아티팩트(plan.md · design.md · research.md)는 절 이름으로만 부른다. 근거는 §v0.1.3 절에 있다.

## Plan-phase log

### v0.1.0 (최초 작성 — 2026-07-27)

- **출처**: 제안서 §3 **P1-2**(버스킹 준비 마법사 — `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:76-80`)와, 선행 SPEC `SPEC-COPILOT-LOOKLIB-001`(**completed**)이 남긴 **예약 조항**이다. LOOKLIB은 룩 1개 단위 인스턴스화까지만 출하하고 그 이상을 명시적으로 본 SPEC에 넘겼다 — "장르 묶음 인스턴스화는 스키마의 API 형상만 예약하고 런타임 실행은 만들지 않는다"(`SPEC-COPILOT-LOOKLIB-001/spec.md:180-182`, 예약 문구 `:70`), 그리고 소비 계약 원문(`SPEC-COPILOT-LOOKLIB-001/research.md:226`). 즉 본 SPEC은 **새 기반을 놓는 SPEC이 아니라 출하된 룩 계층 위에 N개 룩을 가로지르는 조율 계층을 처음 만드는 SPEC**이다(spec.md 서두 주석 · §A 아키텍처 전제).
- **정체**: id `SPEC-COPILOT-BUSKWIZ-001` · 착수 시점 version `0.1.0` · status `draft` · **Tier L** · priority `P1` · phase `Phase 2 연출 계층 (v1.3.0 target)`(spec.md frontmatter). 로드맵 위치는 **3중 표기**로 정직하게 적었다 — "버스킹" 낱말이 등재된 유일한 행은 Phase 4(`product.md:40`)이나 성공 기준이 TBD라 판정 불가, 본 SPEC이 실제로 충족하는 기준은 Phase 2(`product.md:38`), 소비 자산은 Phase 3 산출물이나 LOOKLIB이 선착지시켰다(spec.md 로드맵 3중 표기 문단).
- **동시 생성 아티팩트 6종**: `spec.md` · `plan.md` · `acceptance.md` · `design.md` · `research.md` · 본 `progress.md`. Tier L의 5-file 구성 + progress 기록으로, LOOKLIB이 같은 6종을 동시 생성한 선례(`SPEC-COPILOT-LOOKLIB-001/progress.md:7`)를 그대로 따른다. **6종 전부 plan-phase 산출물이며 run 증거는 아직 0건이다** — 아래 §E.2 이하는 자리만 만들어 둔 상태다.

#### 사용자 사전 확정 4건 (전문 — 재질의 금지, spec.md §A 사전 확정 사실 수록)

1. **① 익스큐터 페이지 레이아웃 = M0 라이브 프로브 GO/DESCOPE 게이트.** 페이지 생성·라벨·복사, 익스큐터 번호 배정 규칙, 익스큐터 라벨링, 빈 익스큐터 탐색은 **리포지토리 전체에서 근거 0건**이다. 페이지 커맨드가 등장하는 유일한 곳 `server/measurement/corpus.yaml`은 스스로 그 블록이 mock 전용이고 커맨드가 "structurally valid"할 뿐이라고 한정한다(`corpus.yaml:8-10`). 따라서 근거 없는 문법을 만들지 않고 `SPEC-COPILOT-EXECBODY-001`의 GO/DESCOPE 프로브 패턴(`SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123` AC-EXECBODY-010)을 계승한다(spec.md §A 사전 확정 ①).
2. **② 팔레트 축 = LOOKLIB in-scope 4풀 그대로 상속.** `Dimmer`·`Color`·`Beam`·`Focus`를 본 SPEC이 재정의하지 않고 `IN_SCOPE_POOL_FAMILIES`(`server/looks/schema.py:58` — 실측 확인: 정확히 4종 튜플)를 import해 쓴다. 제안서 :78이 요구한 **포지션 축은 v1에 존재할 수 없다** — 선행 SPEC이 "담을 것이 없다"는 이유로 닫았고(`SPEC-COPILOT-LOOKLIB-001/spec.md:57`, `:192-194`) 본 SPEC은 그 결정을 번복하지 않고 계승한다(spec.md §A 사전 확정 ②).
3. **③ 실행 단위 = 단일 번들 · 승인 1회 · 부분 성공 구조화 보고.** 장르 1개(룩 6~10개)가 **하나의 번들 / 하나의 승인 카드**다. 착수 시점 추정은 "최대 40여 커맨드"였고 plan-phase 계수로 **51~87행**으로 확정되었다(spec.md §A 사전 확정 ③ 하위 절 — 번들 규모의 실측). 룩 단위 분할 승인(6~10회 왕복)은 "한 마디에 일괄"이라는 기능의 가치를 무력화하므로 기각. 실패한 저장은 건너뛰고 **"N개 건너뜀"의 단위는 프리셋 저장 1회이지 룩이 아니다**(`SPEC-COPILOT-LOOKLIB-001/spec.md:65` 결정 I 계승; spec.md §A 사전 확정 ③).
4. **④ 라이브 세션 2회.** **M0**(익스큐터 문법 프로브 + 다중 룩 번들 왕복 실측)와 **M7**(종단 검증)만 실물 콘솔을 요구한다. LOOKLIB의 라이브 세션 회계(계획 2회)를 그대로 따른다(spec.md §A 사전 확정 ④).

#### 결정 현황 — 해소 7건(A~G) / 미해결 0건 / clarification 마커 0건

착수 시점에 **결정은 전부 폐쇄되었다.** 사용자 확정 4건(A~D)과 엔지니어링 판단 3건(E~G)이며, plan-phase에서 이연한 미해결 항목은 없다. LOOKLIB이 v0.1.0에서 마커 6건으로 출발해 v0.3.0에 이르러서야 0건에 도달한 경로(`SPEC-COPILOT-LOOKLIB-001/progress.md:9`, `:97`)를 반복하지 않기 위해, 본 SPEC은 **폐쇄된 상태로 착수한다**.

| # | 결정 | 확정 내용 | 확정 경로 |
|---|---|---|---|
| A | 익스큐터 페이지 레이아웃 | **M0 라이브 프로브 GO/DESCOPE 게이트**. 부정이면 v1은 익스큐터·페이지 커맨드 **0건** (게이트는 v0.1.2에서 ASSUMPTION-16 ∧ 17 ∧ 19로 3항화) | 사용자 확정 ① |
| B | 팔레트 축 | LOOKLIB `IN_SCOPE_POOL_FAMILIES` 4종 그대로 상속(`server/looks/schema.py:58`). 포지션은 선행 SPEC이 닫음 | 사용자 확정 ② |
| C | 실행 단위 | 단일 번들 · 승인 1회 · 부분 성공 구조화 보고. 룩 단위 분할 승인 / dry-run 선보고 기각 | 사용자 확정 ③ |
| D | 라이브 세션 | **2회** — M0 프로브 + M7 종단 | 사용자 확정 ④ |
| E | 슬롯 원장 | 풀 패밀리별 **누적 슬롯 원장**으로 다중 룩의 슬롯 재청구를 0건화. 원장 시작값은 **콘솔 관측 점유**이며 미관측 풀을 비었다고 가정하지 않는다 | 엔지니어링 판단 |
| F | dedupe 처리 | **`tools.py` dedupe 규칙 무개정.** 장르 번들이 `ChangeDestination Root`를 **선두 1회만** 발화하는 형상으로 회피 | 엔지니어링 판단 (근거: LOOKLIB M7 라이브 관측 `SPEC-COPILOT-LOOKLIB-001/progress.md:799-805`, `:1167-1170`) |
| G | 장르 룩 조회 | `LookLibrary` **직접 순회**. `match_looks` 툴 경로는 `MAX_TOOL_MATCHES = 8`(`server/looks/matching.py:71` — 실측 확인)에서 절단되어 **EDM 9룩이 1건 잘린다** | 엔지니어링 판단 |

- **E·F·G는 사용자 질의 없이 닫았다.** 셋 다 "무엇을 원하는가"가 아니라 "리포지토리가 이미 무엇을 강제하는가"의 문제이기 때문이다 — E는 frozen 데이터클래스의 귀결, F는 라이브 실측이 이미 답을 준 항목, G는 상수 하나가 산출을 절단한다는 기계적 사실이다. LOOKLIB이 결정 H·I를 같은 근거로 사용자 질의 없이 닫은 선례(`SPEC-COPILOT-LOOKLIB-001/progress.md:59-61`)와 동형이다.
- **참조 표기 규율**: 본 SPEC의 모든 문서는 REQ/AC를 **완전 토큰**(`REQ-BUSKWIZ-005`, `AC-BUSKWIZ-004`)으로만 쓴다. SPEC 슬러그를 뺀 축약형(`REQ-` + 세 자리 숫자 꼴, 슬래시로 두 개를 잇는 형태 포함)은 선행 SPEC 감사가 D12로 지적한 결함이며(`SPEC-COPILOT-LOOKLIB-001/progress.md:35`), 본 SPEC은 착수 시점부터 금지한다. 본 문단이 그 축약형을 리터럴로 적지 않는 이유도 같다 — 적는 순간 자기 자신이 위반 스캔에 잡힌다(LOOKLIB이 clarification 마커 토큰에서 겪은 자기 오염과 동형, `SPEC-COPILOT-LOOKLIB-001/progress.md:116`).

#### ASSUMPTION 번호 계승 — LOOKLIB의 15 다음인 16부터

미검증 전제는 **본 SPEC이 새로 1번부터 매기지 않고** LOOKLIB이 소진한 15 다음 번호를 잇는다(spec.md HISTORY v0.1.0 행 · §C 미검증 전제). 같은 기반 위의 두 SPEC이 서로 다른 ASSUMPTION-3을 갖는 상황을 만들지 않기 위해서다. **착수 시점 3건(16/17/18)에 v0.1.2가 ASSUMPTION-19를 더해 현재 4건**이다.

- **ASSUMPTION-16** — grandMA3 2.4.2가 **페이지·익스큐터 저작 문법**(페이지 생성/라벨, 익스큐터 라벨링)을 수용하는가. 리포지토리 근거 0건이며, 유일 등장처 `server/measurement/corpus.yaml`이 스스로 mock 전용임을 선언한다(`:8-10`). 부정이면 REQ-BUSKWIZ-016 DESCOPE.
- **ASSUMPTION-17** — **비어 있는 익스큐터를 열거·판별**할 수 있는가. 현재 페이지 드릴다운은 **이미 존재하는 자식만** 열거하며(`server/web/dash.py:200-206` — 실측 확인: `page.get("contents", [])` 순회로 존재하는 항목만 후보에 넣는다), "없음"과 "미확인"이 구별되지 않는다. 부정이면 REQ-BUSKWIZ-016 DESCOPE.
- **ASSUMPTION-18** — **단일 번들이 한 번의 `run_commands` 왕복에서 절단·타임아웃 없이** 왕복하는가. 착수 시점 spec.md는 규모를 "최대 약 40여 커맨드"로 적었으나 그것은 **쌍(pair) 수에서 나온 추정치**였고, plan.md **§A.2 계수 각주**가 출하 라이브러리를 직접 계수해 실제 행 수를 냈다(장르별 표 포함) — **v1 형상(`CAPTURE_SHARED`) 밴드 51~87행, 상한은 edm 9룩 · 4풀 가용 시 87행**. spec.md v0.1.1이 이 실측을 §A와 ASSUMPTION-18에 반영했다. LOOKLIB M7 라이브 실측 최대는 **21줄**이므로 미측정 구간은 **약 4배**다(표기는 plan.md·design.md와 동일).
  - **측정 대상은 v1 형상 87행 하나다**: `per_family_capture` 형상은 **도달 불가**로 닫혀 있다 — REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)이 캡처 형상을 `shared_capture`로 고정하고 모델 인자로 노출하지 않으며, REQ-BUSKWIZ-020이 툴 인자를 **장르 식별자 하나**로 좁혔다. `instantiate_look`이 `capture_shape`를 노출하는 것은(`server/orchestrator/tools.py:1035-1046`) **단일 룩 경로의 선택**이며 장르 번들에는 안전하지 않다.
  - **차단 근거 (형상이 아니라 안전 문제)**: per-family는 룩마다 패밀리별 값 라인을 따로 발화하는데(`server/looks/instantiate.py:406-411`), 서로 다른 룩의 값 라인이 문자열로 같아지는 경우가 실재한다(실측: edm 두 룩의 `Attribute 'Dimmer' At 100`, rock 두 룩의 `Attribute 'Iris' At 100`). 값 라인은 dedupe 면제 집합에 없고(`server/orchestrator/tools.py:227-231`) 직전 `ClearAll`은 면제라 살아남으므로, 두 번째 값 라인이 탈락하면 **빈 프로그래머 상태로 `Store`가 실행되고 콘솔은 성공으로 답한다**(REQ-BUSKWIZ-006 하위 절). v1 형상은 룩당 값 라인이 1개이고 4장르 전부 중복 0건이다.
  - **회귀 경고 (규율이 아니라 감시 항목)**: 따라서 M0는 87행만 재면 충분하다. 다만 **`capture_shape`가 어떤 경로로든 장르 툴 인자로 되살아나면 그 순간 135행이 미측정 경로가 되고 값 라인 탈락도 함께 돌아온다** — 되살리려는 변경은 규모 재측정과 값 라인 중복 재계수를 함께 요구한다.
  - **함께 기록할 것 하나**: `run_commands`는 **stop-on-first-failure**라 한 줄이 실패하면 그 뒤 전량이 `not_executed`가 되며(`server/orchestrator/tools.py:527-536` — 실측 확인: `if failed:` 분기가 남은 커맨드를 `status="not_executed"`로 적재), 87행 규모에서 이 성질이 어떻게 관측되는지가 REQ-BUSKWIZ-010의 계획 시점 부분 성공과 **다른 종류의 부분 상태**다(plan.md §B M0의 "함께 측정할 것").
  - 부정 실측이면 번들 분할이 필요해지고 그것은 사용자 확정 ③과 충돌하므로, **SPEC이 임의로 분할하지 않고 M0 게이트에 사용자 결정 항목으로 올린다**(ASSUMPTION-18 본문; plan.md §G 조건부 접점).
- **ASSUMPTION-19 (v0.1.2 신설)** — **팔레트(프리셋)를 익스큐터에 얹는 문법이 존재하는가.** 라이브 검증된 유일한 바인딩 커맨드의 **목적어는 시퀀스**이고(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:99`), 프리셋을 익스큐터에 직접 배치하는 형태는 **리포지토리 전체 0건**이다 — `Assign Preset` · `Preset <p>.<s> At (Executor|Page) <n>` · `Store Executor` 계열 전부 `server/`·`console/`·`docs/`에서 검색 결과 없음. 부정이면 산출물(프리셋)과 익스큐터 레이아웃 사이에 **연결 수단 자체가 없으므로** REQ-BUSKWIZ-016은 DESCOPE된다.
  - **우회로는 답이 아니다**: "그럼 시퀀스를 만들어 거기에 프리셋을 넣자"는 §D가 범위 밖으로 둔 시퀀스·큐 생성을 암묵적으로 끌어들이는 것이므로 금지된다(spec.md REQ-BUSKWIZ-016 하위 절 — ASSUMPTION-19가 게이트에 추가된 이유). M0가 문법을 찾지 못했을 때의 정답은 **DESCOPE 하나**다.

ASSUMPTION-16·17·19는 **AC-BUSKWIZ-016(M0, LIVE)** 하나가 묶어 실측하고(측정 항목 4번이 ASSUMPTION-19이며 기대 결과는 4건 전부 판정 확정), 그 GO/DESCOPE 결과를 **AC-BUSKWIZ-012(M5)** 가 **3항 논리곱**으로 인수한다. 게이트가 3항이 된 것은 v0.1.2의 요구 정합 결함 해소다 — 16·17만으로는 게이트가 열려도 **얹을 대상이 없었다**.

#### 선행 구현에서 발견한 하드 결함 2건 — 본 SPEC이 그 위에 선다

LOOKLIB의 단일 룩 경로는 **룩마다 리그를 다시 읽는 왕복 구조**라 아래 둘이 가려져 있었다. 다중 룩을 하나의 번들로 묶는 순간 즉시 발현한다(spec.md §A 하드 결함 2건).

1. **슬롯 비전진 — 결정 E가 해소한다.** `PoolBinding`/`PoolIndex`가 `@dataclass(frozen=True)`이고(`server/looks/instantiate.py:78-79`, `:96-97` — 실측 확인), `_first_free_slot`(`:307-312`)은 인자로 받은 점유 목록에서 1부터 오름차순 첫 미점유를 고를 뿐 **어디에도 쓰기·전진이 없다**(실측 확인: `taken = set(occupied)` 후 지역 변수 `slot`만 증가시키고 반환). `_plan_stores`는 `binding.occupied`를 **읽기만** 한다(`:346`, `:358`). 따라서 하나의 `PoolIndex`로 N개 룩을 돌리면 **N개 전부가 같은 슬롯을 겨냥**하고, 라벨이 서로 달라 `CONFLICT` 판정(`:359-361`)에도 걸리지 않는다 — 결과는 같은 슬롯에 N번 `Store`, 정확히 이 프로젝트가 막으려 한 "사람이 만든 프리셋 위에 쓰기"의 자기 재현이다. **REQ-BUSKWIZ-005가 이 해소를 요구하고 AC-BUSKWIZ-004(M2)가 검증한다.**
2. **`ChangeDestination Root`의 dedupe 탈락 — 결정 F가 회피한다(코드 개정 없음).** 면제 집합 `_PROGRAMMER_STATE_COMMANDS`는 `Clear` / `ClearAll` / 맨-형태 `Fixture|Group` 선택 **3종뿐**이고(`server/orchestrator/tools.py:227-231` — 실측 확인), dedupe는 `context.executed_ok`를 시드로 **번들 내에서도 누적**한다(`:526`, `:537`). LOOKLIB M7 라이브가 이 탈락을 **실물에서 관측**했다 — 승인 이벤트 10개 vs 실행 9행, 빠진 정확히 1개가 `ChangeDestination Root`였다(`SPEC-COPILOT-LOOKLIB-001/progress.md:799-805`, 요약값 `:1167-1170`). 그 세션의 두 번째 번들은 그럼에도 정상 왕복했다(목적지 상태가 세션에 남아 있음). 본 SPEC은 이 실측을 근거로 **면제 집합을 개정하지 않고** 번들 형상 쪽에서 해결한다 — 장르 번들은 `ChangeDestination Root`를 선두에 정확히 1회만 발화한다(REQ-BUSKWIZ-006 / AC-BUSKWIZ-005). LOOKLIB이 "dedupe 규칙 개정 여부는 M4가 단독으로 정하지 않는다"고 넘긴 판단에 대한 본 SPEC의 답은 **"개정하지 않는다"** 이며, `tools.py`는 PRESERVE에 남는다 — 본 SPEC이 그 파일에 하는 일은 **신규 툴 1종의 등록뿐**이다(spec.md §D Out of Scope — `run_commands` dedupe 규칙 개정; REQ-BUSKWIZ-019).

#### 수용된 잔여 위험 1건 — 긴 프리뷰의 검토성 (제시 시점 추정 "40여 줄" → plan-phase 실측 51~87행)

사용자 확정 ③의 단일 승인은 **한 화면에 담기지 않는 프리뷰를 사람이 실질적으로 검토하기 어렵다**는 비용을 동반한다. 이 논거는 사용자에게 **대안 2개(룩 단위 분할 승인 / dry-run 선보고)와 함께 제시되었고**, 사용자는 그것을 알고 단일 승인을 선택했다. 따라서 이것은 **기각된 반론이 아니라 표면화된 뒤 수용된 위험**이며, design.md §4에 존치하고 삭제하지 않는다(spec.md §A 사전 확정 ③ 하위 절 — 수용된 잔여 위험). 완화 수단은 REQ-BUSKWIZ-013의 **집계 + 룩별 2단 구조화 보고** 하나이며 — (a) 생성 전량 (b) 미매핑 역할과 사유 (c) 건너뛴 프리셋 저장 개수·풀·슬롯·사유 (d) 룩별 판정 (e) 미실행 커맨드 수 — **집계만 보고하고 룩별을 생략하는 것은 금지**된다(검증 AC-BUSKWIZ-008, M3). (b)의 사유는 spec.md v0.1.1이 **3종이 아니라 최대 5종**으로 확정했다 — 매칭 판정 3종(`ambiguous`·`no_match` — `server/looks/roles.py:22-23`; `unaddressable` — `server/looks/resolver.py:50`)에 섹션 실패 전파를 더한 것이며 병합하지 않는다(REQ-BUSKWIZ-013 하위 절 — (b)의 사유는 최대 5종; plan.md §B M3에 반영). LOOKLIB이 사용자 확정 ⑧·⑩을 "표면화된 뒤 수용된 비용/잔여 위험"으로 기록한 처리 방식(`SPEC-COPILOT-LOOKLIB-001/progress.md:56`, `:58`)을 그대로 따른다.

- **plan-phase 실측이 이 위험의 크기를 갱신했다(결정은 불변).** 사용자에게 제시된 "40여 줄"은 쌍 수에서 나온 추정치였고, 출하 라이브러리를 직접 계수한 실제 프리뷰 길이는 **51~87행**이다(plan.md §A.2 계수 각주; SSOT 반영은 spec.md §A 사전 확정 ③ 하위 절). 상한 기준 **약 2.2배**(87/40)이며, 그 갱신은 plan.md의 결정 기록 양쪽(§A.4a 결정 C 행 · §F 결정 기록 "C — 실행 단위" 행)에 반영되어 있다. **결정 C는 그대로다** — 갱신된 것은 선택지가 아니라 그 선택이 안고 가는 비용의 크기이며, 그 사실을 여기 적어 두는 이유는 "수용된 위험"이 나중에 **제시된 적 없는 크기로 조용히 커지는 것**을 막기 위해서다. 완화(REQ-BUSKWIZ-013의 2단 보고)는 그 크기에서 동일하게 필요한 정도가 아니라 **필요성이 커진다**.
- **완화가 덮지 않는 인접 상태 1건**: `run_commands`의 stop-on-first-failure로 생기는 `not_executed` 잔여(`server/orchestrator/tools.py:527-536`)는 REQ-BUSKWIZ-013 (c)의 "건너뜀"과 **원인도 조치도 다르다** — 전자는 앞줄 실패의 귀결이고 후자는 계획 시점에 저장이 애초에 서지 않은 것이다. 보고에서 두 수를 합산하면 사용자가 조치를 고를 수 없게 되므로 **별도 항목 (e)로 싣는다**(REQ-BUSKWIZ-013 하위 절 — (c)와 (e)를 합산하지 않는다; plan.md §B M3 · §C.9). 룩별 판정 (d)의 산출 경로도 여기에 걸린다 — `created`/`skipped`는 계획 시점의 사실이라 중단 여부를 담지 않으므로, 판정은 **번들의 per-command status와 대조해 산출**한다(plan.md §B M3). 이는 새 요구가 아니라 기존 REQ-BUSKWIZ-013 (d)의 경로 특정이다.

#### 마일스톤 M0~M7 ↔ AC 17건 배정 (착수 시점 고정)

**acceptance.md §C.0의 "마일스톤별 AC 집합" 요약행이 SSOT다** — M0 = {016} · M1 = {001, 002} · M2 = {003, 004, 005, 006, 007} · M3 = {008} · M4 = {009, 010, 011} · M5 = {012, 013} · M6 = {014, 015} · M7 = {017}, 17개 AC가 정확히 한 번씩 나타나며 중복·누락 0. LOOKLIB이 재감사 N2에서 plan.md §B와 acceptance.md §C.0의 마일스톤 AC 배정 3곳 불일치를 지적받고 사후 재정합한 전례(`SPEC-COPILOT-LOOKLIB-001/progress.md:80`)에 따라, 본 SPEC은 **착수 시점부터 그 요약행을 단일 출처로 두고** 다른 아티팩트는 그것을 인용만 한다.

#### §F를 실제로 만든다 — LOOKLIB의 헤딩 갈등을 재현하지 않기 위해

선행 SPEC의 plan.md는 "구속력 있는 기록은 `progress.md` §F이며 오케스트레이터 소유다"라고 적었으나(`SPEC-COPILOT-LOOKLIB-001/plan.md:289`), **그 §F 헤딩은 LOOKLIB progress.md에 실제로 존재하지 않는다** — 그 파일의 `##` 헤딩은 `Plan-phase log` · `§E.1` · `§E.2` · `§E.3` · `§E.4` 다섯 개뿐이다(실측 확인). 즉 plan.md가 가리킨 목적지가 없는 **끊어진 참조**였다. 본 SPEC은 착수 시점에 **§F 헤딩을 실제로 생성**하고 오케스트레이터 소유의 자리표시자를 넣어 그 갈등을 재현하지 않는다.

#### 수치에 대한 규율 — plan-phase에서는 측정하지 않는다

**본 문서의 v0.1.0 로그는 테스트 개수·통과 수·커버리지를 단 하나도 적지 않는다.** plan-phase는 그것을 측정하지 않았으므로, 적으면 그 순간 근거 없는 수치가 된다. 이는 선례에서 실제로 발생한 결함이다 — LOOKLIB은 M1이 기록한 `1909`와 M2가 **같은 HEAD에서** 실측한 `1912`의 3건 차이를 끝내 규명하지 못했고(`SPEC-COPILOT-LOOKLIB-001/progress.md:1336`), M3·M4는 그 숫자를 이월하지 않고 착수 직전에 직접 실측한 값에만 델타를 귀속시키는 방식으로 우회했다(`:487`, `:1332`, `:1334`).

본 SPEC의 규율은 그 우회를 **처음부터 규칙으로** 삼는다: **각 마일스톤은 착수 직전 자신이 직접 실측한 수에만 델타를 귀속시킨다. 이월된 숫자를 baseline으로 쓰는 것은 측정이 아니라 인용이다.** spec.md §C 측정된 기준선이 같은 의무를 착수 조건으로 명문화하고 있다. 또한 커밋 SHA·HEAD 표기도 문서에 고정 기록하지 않는다 — LOOKLIB이 "미커밋"·HEAD SHA 진술이 **쓰이거나 커밋되는 순간 거짓이 되는** 자기참조 해저드를 세 번 겪었기 때문이며(`SPEC-COPILOT-LOOKLIB-001/progress.md:16`, `:53`, `:111`), 실질 위험은 위의 킥오프 재측정 의무가 이미 덮는다.

#### next

**plan-audit 실행**(Tier L PASS 기준 0.85 — 감사 보고서는 `.moai/reports/plan-audit/` 아래 **파일로 영속화**한 뒤 처리 표를 작성한다. 대화 안에만 존재한 감사는 처리 누락을 사후 검증할 방법이 없다는 것이 LOOKLIB D1·D16의 복원 불가 사례가 남긴 교훈이다 — `SPEC-COPILOT-LOOKLIB-001/progress.md:93-95`) → **M0 라이브 세션 접근 가능성 확인** → Implementation Kickoff Approval → run(M0 프로브부터). **Kickoff 전 결정 해소용 AskUserQuestion은 0건**이다 — 결정 7건이 전부 폐쇄되어 있으므로 남은 사용자 접점은 결정이 아니라 **실물 콘솔 접근 가능성**을 묻는다.

### v0.1.1 (spec.md plan-phase 실측 반영 — 2026-07-27)

- **성격**: 감사 라운드가 **아니다.** plan-phase 계수·형상 분석이 만들어 낸 실측을 SSOT에 되먹인 한정 개정이며, **요구 집합·AC 집합·결정 집합은 무변경**이다 — REQ 20건 / AC 17건 / 결정 A~G 7건 / clarification 마커 0건 그대로(spec.md HISTORY v0.1.1 행). 본 progress.md의 v0.1.0 로그는 착수 시점의 기록으로 남기고, 아래 3건만 하류 전파했다.
- **① per-family 캡처 형상이 "도달 가능"에서 "도달 불가"로 닫혔다.** spec.md v0.1.1이 REQ-BUSKWIZ-006 하위 절로 **캡처 형상을 `shared_capture`에 고정하고 모델 인자로 노출하지 않는다**를 신설했고, REQ-BUSKWIZ-020이 툴 인자를 **장르 식별자 하나**로 좁혔다. 차단 사유는 규모가 아니라 **안전**이다 — per-family는 룩마다 패밀리별 값 라인을 발화하는데(`server/looks/instantiate.py:406-411`) 서로 다른 룩의 값 라인이 문자열로 같아지는 경우가 실재하고(edm `Attribute 'Dimmer' At 100` ×2, rock `Attribute 'Iris' At 100` ×2), 값 라인은 dedupe 면제가 아니어서 두 번째가 탈락하면 **빈 프로그래머에 `Store`가 걸리고 콘솔은 성공으로 답한다**.
  - **본 문서가 한 번 틀렸다가 되돌린 지점**: 직전 개정에서 `instantiate_look`의 `capture_shape` 인자(`server/orchestrator/tools.py:1035-1046`)를 근거로 per-family를 도달 가능으로 적고 "87행만 재고 GO 선언 금지 / 인자에서 빼거나 Gaps 명시"를 규율로 올렸다. **그 인자는 단일 룩 툴의 것이고 장르 툴의 것이 아니다** — REQ-BUSKWIZ-020이 닫은 뒤로는 틀린 요구가 되므로 삭제하고 **회귀 경고**로 낮췄다(ASSUMPTION-18 항). 검증 자체는 옳았고 **대상을 잘못 잡은 사례**로 남긴다.
- **② 번들 규모 표기가 51~87행으로 확정되었다.** 착수 시점 "최대 약 40여 커맨드"는 **쌍(pair) 수에서 나온 추정치**였다. plan.md §A.2가 출하 라이브러리를 직접 계수해 행 수를 냈고, spec.md가 §A와 ASSUMPTION-18에 반영했다. **M0의 측정 대상은 v1 형상 상한 87행 하나**이며(plan.md §A.2 결론 · §B M0), 최소 51은 ballad · Dimmer/Color만 · 룩 경계 `ClearAll` 병합 조합이다 — 즉 51~87은 단일 형상의 밴드가 아니라 **포괄 봉투**다.
- **③ REQ-BUSKWIZ-013 (b)의 사유가 최대 5종으로, (e) 미실행 커맨드 수가 보고 요소로 확정되었다.** (b)는 매칭 판정 3종(`ambiguous`·`no_match` — `server/looks/roles.py:22-23`; `unaddressable` — `server/looks/resolver.py:50`)에 **섹션 실패 전파**를 더한 부류 구분이며 병합하지 않는다. (e)는 stop-on-first-failure 잔여이고 **(c)와 합산 금지**다. 룩별 판정 (d)는 계획 결과만으로 산출할 수 없어 **per-command status와 대조**한다(plan.md §B M3).
- **인용 규율 1차 분리 (형제 아티팩트)**: 정본과 코드에는 `파일:줄` 앵커를 걸고, **본 SPEC의 형제 아티팩트(plan.md · design.md · research.md)는 절 이름으로만 부른다.** plan.md 인용은 하루에 세 번 밀렸고 그때마다 본 문서가 따라 고쳐야 했다 — 줄 앵커가 사실을 더 단단히 붙드는 게 아니라 **아직 움직이는 문서에 건 앵커가 계속 끊어졌을 뿐**이다. **이 규율은 v0.1.3에서 정본까지 확대된다**(아래).
- **spec.md 앵커 전수 재매핑 (v0.1.1 시점의 작업 기록)**: spec.md가 v0.1.1에서 행이 밀렸으므로 본 문서의 spec.md 앵커를 전부 다시 읽고 갱신했다(16곳). **이월 인용을 하지 않고 각 앵커를 현재 파일에서 직접 확인**했다. 그 매핑 목록은 v0.1.2에서 한 번 더 밀렸고 v0.1.3에서 **앵커 자체가 폐기**되었으므로 여기 숫자를 다시 적지 않는다 — 폐기된 좌표계의 좌표를 보존하는 것은 기록이 아니라 잔해다.
- **불변식 재확인 (v0.1.1 시점)**: 섹션 6개 · 결정 7건(A~G) · ASSUMPTION 3건(16/17/18) · 하드 결함 2건 · 수용된 위험 1건 · 마커 0건 · 축약 토큰 0건 · plan-phase 자체 측정 수치 0건.

### v0.1.2 (SSOT 요구 정합 결함 1건 해소 — 2026-07-27)

- **성격**: 감사 라운드가 아니며, **REQ 20건 · AC 17건 · 결정 A~G 7건 · clarification 마커 0건은 그대로**다(spec.md HISTORY v0.1.2 행). 바뀐 것은 **ASSUMPTION 1건 신설과 그에 따른 게이트 논리**뿐이다.
- **결함의 정체 — 게이트가 열려도 얹을 대상이 없었다.** REQ-BUSKWIZ-016은 ASSUMPTION-16·17이 둘 다 GO이면 "팔레트에 대응하는 익스큐터 레이아웃"을 생성하도록 쓰여 있었다. 그러나 라이브 검증된 유일한 바인딩 커맨드 `Assign Sequence <n> At Executor <m>`의 **목적어는 시퀀스**이고(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:99`), 본 SPEC의 산출물은 **프리셋**이며, §D는 시퀀스·큐 생성을 명시적으로 범위 밖에 두었다. 즉 **두 전제가 모두 참이어도 요구가 충족 불가**인 상태였다 — 전제 부족이 아니라 **요구와 범위의 정합 결함**이다.
- **해소 = ASSUMPTION-19 신설 + 게이트 3항화**: "팔레트(프리셋)를 익스큐터에 얹는 문법이 존재하는가." 실측 근거는 **0건**이다 — `Assign Preset` · `Preset <p>.<s> At (Executor|Page) <n>` · `Store Executor` 계열이 `server/`·`console/`·`docs/` 전체에서 검색 결과 없음. REQ-BUSKWIZ-016의 게이트는 이제 **16 ∧ 17 ∧ 19**이고 하나라도 부정이면 DESCOPE다(spec.md §B.4 제목도 "ASSUMPTION-16/17/19와 한 쌍"으로 바뀌었다).
- **우회로 금지가 함께 명문화되었다**: M0가 문법을 찾지 못했을 때의 답은 **DESCOPE 하나**이며, "그럼 시퀀스를 만들어 거기에 프리셋을 넣자"는 §D가 닫은 범위를 암묵적으로 되여는 것이라 금지된다. **DESCOPE는 실패가 아니라 정의된 결과**라는 v0.1.0의 처리 방향과 같다.
- **acceptance 동반 개정**: AC-BUSKWIZ-016의 측정 항목이 **4번으로 ASSUMPTION-19**를 받고 정리기록·Gaps가 5·6으로 밀렸으며 기대 결과가 "4건 전부 판정 확정"이 되었다. AC-BUSKWIZ-012는 **3항 논리곱** 문형이 되었고 acceptance.md §B 시나리오 6의 Given도 3항이다. **AC 개수는 17건 그대로**다.
- **본 문서의 반영**: ASSUMPTION 목록을 **4건(16/17/18/19)**으로 확장하고, AC-BUSKWIZ-016 ↔ AC-BUSKWIZ-012 인수 문장을 3항 논리곱으로 고쳤다. 라이브 세션 회계는 **2회 그대로** — ASSUMPTION-19는 M0가 이미 여는 세션에서 함께 재는 항목이지 새 세션이 아니다.
- **불변식 재확인 (v0.1.2 시점)**: 섹션 6개 · 결정 7건(A~G) · **ASSUMPTION 4건(16/17/18/19)** · 하드 결함 2건 · 수용된 위험 1건 · 라이브 세션 2회 · 마커 0건 · 축약 토큰 0건 · plan-phase 자체 측정 수치 0건.

### v0.1.3 (독립 plan-audit FAIL 0.78 반영 — 2026-07-27)

- **감사 결과**: 독립 plan-audit **FAIL, 종합 0.78**(Tier L PASS 기준 0.85), 지적 8건. **감사를 권위로 수용하고 원문을 방어하지 않는다.** SSOT 2종이 v0.1.3으로 개정되었고 **REQ 20건 · AC 17건 · 결정 A~G · 마일스톤 M0~M7 · 마커 0건은 전부 무변경** — 바뀐 것은 **문언과 검증 수단**이다(spec.md HISTORY v0.1.3 행).
- **① 앵커 정책 전면 전환 (감사 P1 — 본 문서에 가장 크게 걸린 항목).** 감사는 형제→정본 줄 앵커 52개 중 **10개가 빈 줄을 가리키고 6개 이상이 다른 내용을 가리킨다**고 실측했다. 본 문서에도 같은 부류가 있었다 — 예컨대 REQ-BUSKWIZ-020을 가리키던 앵커가 실제로는 그 한 줄 앞을 가리켰다.
  - **전환 내용**: 정본(spec.md · acceptance.md) 참조에서 **줄번호를 전부 제거**하고 안정 토큰으로 교체했다 — `REQ-BUSKWIZ-nnn` · `AC-BUSKWIZ-nnn` · `ASSUMPTION-nn` · 절 제목 · 명명된 하위 절. **`파일:줄`은 코드 · 룰북 · 타 SPEC 아티팩트에만** 남는다.
  - **왜 토큰인가**: 토큰은 개정을 견디고, 가리키는 내용이 사라지면 **토큰도 함께 사라져 즉시 드러난다.** 줄번호는 조용히 옆 문장을 가리킬 뿐이고, 그 침묵이 정확히 감사가 잡아낸 것이다. 코드에 앵커를 남기는 이유는 반대 방향이다 — 코드는 커밋 없이 움직이지 않고 달리 안정 식별자가 없다.
  - **비용도 적는다**: 토큰 참조는 "어디를 보라"를 한 번에 주지 못한다(독자가 토큰을 검색해야 한다). 그 대가로 **틀린 곳을 자신 있게 가리키는 일**이 사라진다. 하루에 네 번(v0.1.1·v0.1.2·plan.md 이동 2회) 앵커를 따라 고친 뒤 내린 결론이다.
- **② REQ-BUSKWIZ-010의 트리거가 도달 불가였다 (감사 D2).** v0.1.2까지 이 요구는 "**슬롯이 부족해**"를 트리거로 적었으나 그 상태는 발생할 수 없다 — `_first_free_slot`(`server/looks/instantiate.py:307-312`)은 상한 없이 증가하고, 풀 용량 상수는 리포지토리 0건이며, 관측 경로가 풀 크기를 보고하지 않는다. spec.md가 트리거를 **도달 가능한 3경로**(패밀리 수 차이 / 풀 미해석 / 라벨 충돌)로 교체했다. **본 문서는 그 폐기된 트리거 표현을 근거로 쓴 곳이 0건**이었으므로(스캔 확인 — 그래서 이 문단도 그 표현을 서술어로 되풀이하지 않는다) 교체할 문장이 없었고, 대신 이 사실을 여기 기록한다. 결정 E의 슬롯 원장은 **여전히 필요하다** — 원장이 막는 것은 "자리가 모자라는 상황"이 아니라 **N개 룩이 같은 슬롯을 겨냥하는 상황**이며, 그 둘은 다른 문제다.
- **③ PRESERVE에 `server/looks/instantiate.py`가 추가되었다.** 결정 E는 "frozen을 바깥에서 감싼다"는 것이므로, 만약 구현이 그 파일을 고쳤다면 **결정 E가 틀렸다는 뜻**이다. PRESERVE에 넣어 그 반증이 `git diff`로 즉시 드러나게 했다 — 본 문서 하드 결함 1의 서술(frozen · 전진 없음 · 읽기만)은 **그 파일을 고치지 않는다는 전제 위에 서 있었고**, 이제 그 전제가 검증 대상이 되었다.
- **④ `git diff`는 `<BASE>..HEAD` 형태여야 한다.** 인자 없는 `git diff`는 커밋 후 항상 빈 출력이라 PRESERVE 게이트가 **통과를 보장받는 무의미한 검사**가 된다. 본 문서는 그 커맨드를 인용하지 않지만, "빈 출력 = 무변경"이라는 판정을 §E.3 이후에 쓸 때 이 함정을 반복하지 않도록 여기 남긴다.
- **⑤ AC-BUSKWIZ-012 ①의 번호 출처가 ASSUMPTION-17과 모순이었다.** 익스큐터 번호를 `resolved_executor_nos`(= **점유된** 익스큐터)에서 얻도록 쓰여 있었는데 ASSUMPTION-17이 묻는 것은 **빈** 익스큐터 판별이다 — "M0가 GO로 판정한 빈-익스큐터 식별 경로가 반환한 번호"로 교체되었다. 본 문서의 ASSUMPTION-17 서술("없음과 미확인이 구별되지 않는다")은 그 모순의 근원을 이미 담고 있었으나 **AC 쪽 귀결까지 따라가지 못했다** — 서술과 검증 수단을 함께 훑지 않으면 이런 결함이 남는다는 사례로 기록한다.
- **⑥ 함께 정정된 것**: `product.md:43`은 빈 줄이라 `:44`가 맞다(본 문서는 `:38`·`:40`만 인용했고 둘 다 유효 — 스캔 확인). acceptance.md §D의 "fail-closed 번들 전체 거부"는 **등록부 밖 8번째 결정**이자 REQ-BUSKWIZ-010과 반대 방향이어서 **미결로 강등**되었다 — 결정은 여전히 **7건(A~G)** 이다. AC-BUSKWIZ-013 ②의 검증 수단이 소스 grep → **생성 커맨드 튜플 전수 + 비공허성 assert**로, AC-BUSKWIZ-002 ③이 import 스캔 → **AST 스캔**으로 바뀌었다(검증 수단 변경이지 AC 신설이 아니다).
- **불변식 재확인 (v0.1.3 시점)**: 섹션 6개 · 결정 **7건(A~G)** · ASSUMPTION 4건(16/17/18/19) · 하드 결함 2건 · 수용된 위험 1건 · 라이브 세션 2회 · 마커 0건 · 축약 토큰 0건 · plan-phase 자체 측정 수치 0건 · **정본 줄 앵커 0건**(grep 확인).

### v0.1.4 (재감사 PASS 0.88 조건부 지적 처리 — 2026-07-27)

- **재감사 결과**: 독립 plan-audit 2회차 **PASS(조건부), 종합 0.88**(Tier L PASS 기준 0.85). 1회차 지적 D1~D9 중 **8건 닫힘 · 1건 부분 닫힘(D2) · 0건 미해소**, 신규 5건(P2 2 · P3 3, **P0·P1 0건**). D8(줄 앵커 붕괴)은 형제 4종의 토큰 전환으로 실측 0건 확인되어 닫혔고, D5는 권고보다 강하게 닫혔다(빈-익스큐터 경로의 **식별자와 반환 형상**을 AC-BUSKWIZ-016 산출물로 요구).
- **D2 부분 닫힘의 내용 — 정정을 하다가 하나를 잘못 끼워 넣었다.** v0.1.3이 도달 불가 트리거("슬롯 부족")를 도달 가능한 것으로 교체하면서 **"룩별 패밀리 수 차이"를 첫 번째 경로로 열거**했는데, 그것은 애초에 **부분 성공이 아니다**. `_plan_stores`는 룩이 그 패밀리에 값을 갖지 않으면 `if not values: continue`로 넘어가 `SkippedStore`를 만들지 않으므로(`server/looks/instantiate.py:332-334`) 결과는 `planned=P, skipped=0, complete=True` — **완전 성공**이며 보고할 건너뜀이 없다(실행 확인: `ballad-single-key` P=4 / `ballad-moonlight` P=2 둘 다). 이 경로로 "건너뜀이 있다"를 assert하면 거짓이 된다. v0.1.4가 열거에서 삭제하고 **왜 아닌지**를 함께 남겼다 — 이유 없이 지우면 다음 사람이 다시 넣는다.
  - **최종 열거는 둘**: 풀 미해석·미주소(`binding.reason` 분기) · 라벨 충돌(`conflict`). 점유 미관측(`no_free_slot`)은 REQ-BUSKWIZ-009가 따로 덮는다. SSOT 양쪽(spec.md REQ-BUSKWIZ-010 하위 절 · acceptance.md §C.0 비고 + AC-BUSKWIZ-004 구간 3)과 형제 4종 전부에 전파했고, **건너뜀 항목 비공허성** assert를 추가해 "0건인데 통과"를 막았다.
  - **부류의 반복**: 이것은 §9.4의 결함 ②와 같은 부류다 — 문장은 완결돼 있고 근거도 달려 있는데 **전제가 성립하지 않는다**. 결함 ①은 목적어를 다시 보지 않았고, ②는 트리거가 발생 가능한지 묻지 않았고, 이번 것은 **정정 자체를 다시 검산하지 않았다**. 셋 다 문서를 읽어서는 안 나오고 코드를 실행해야 나온다.
- **신규 P3 3건 처리**: (i) §E·§F에 남아 있던 **슬러그 없는 축약형 4건** — 저자 넷이 각자 "축약 0"을 보고했으나 **아무도 SSOT를 스캔하지 않았다.** 종료 기준에 **6종 전체 스캔**을 추가했다. (ii) design.md §5.0의 측정 열거가 3건(19 누락)이라 같은 절 안에서 모순 → 4건으로 정정. (iii) plan.md의 토큰 치환 잔여 중복 문구 정리.
- **자기오염 1건 — 그 함정을 문서화해 둔 문서에서 밟았다**: v0.1.4 HISTORY 행이 삭제한 축약 토큰을 **리터럴로 인용**해 스스로 위반 스캔에 걸렸다(6종 스캔에서 spec.md만 1건). 본 문서 참조 규약 절이 "적는 순간 자기 자신이 위반 스캔에 잡힌다"를 LOOKLIB 선례와 함께 이미 적어 둔 항목이다. 리터럴을 서술("슬러그 없는 세 자리 축약형 4건")로 바꿔 해소했다.
- **불변식 재확인 (v0.1.4 시점)**: 섹션 6개 · 결정 **7건(A~G)** · ASSUMPTION 4건(16/17/18/19) · 하드 결함 2건 · 수용된 위험 1건 · 라이브 세션 2회 · REQ **20건** · AC **17건**(중복·누락 0) · 마커 0건 · 축약 토큰 **6종 전체 0건** · 정본 줄 앵커 0건 · plan-phase 자체 측정 수치 0건.

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-07-27
spec_version: "0.1.4"
audit_rounds: 2
audit_1: { verdict: FAIL, score: 0.78, threshold: 0.85, findings: 8, breakdown: "P1 3 · P2 4 · P3 1" }
audit_2: { verdict: PASS, score: 0.88, threshold: 0.85, closed: 8, partially_closed: 1, unresolved: 0, new_findings: 5, breakdown: "P2 2 · P3 3, P0·P1 0" }
post_audit_2_fixes: "재D2 부분 닫힘(트리거 열거 1건 삭제 + 비공허성 assert) · 재P2(§C.0 비고 잔존) · 재P3 3건(축약 토큰 4건 · design §5.0 측정 3→4건 · plan 중복 문구) · 자기오염 1건(HISTORY 리터럴)"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
requirements: 20        # REQ-BUSKWIZ-001~020, §C.0 역추적 20/20
acceptance_criteria: 17 # AC-BUSKWIZ-001~017, 마일스톤 M0~M7 배정 중복·누락 0
decisions_closed: 7     # A~G, 미해결 0
clarification_markers: 0
assumptions_open: 4     # ASSUMPTION-16/17/18/19 — 전부 M0 라이브 실측 대상
live_sessions_planned: 2  # M0 프로브 + M7 종단
machine_gates:
  ssot_line_anchors_in_siblings: 0   # 토큰 참조 규율 (감사 D8)
  abbreviated_tokens_all_six: 0      # (?<![A-Z-])(AC|REQ)-\d{3}
  clarification_markers_all_six: 0
  req_to_ac_coverage: "20/20"
  ac_milestone_assignment: "17건, 중복 0 · 누락 0, plan §B ↔ acceptance §C.0 1:1"
blocking_for_run: "없음 — 단, M0(라이브 프로브)가 M1의 정책 게이트이며 ASSUMPTION-18은 M2를 기술적으로 막는다"
next: "Implementation Kickoff Approval (plan→run HUMAN GATE)"
```

## §E.2 Run-phase Evidence

### Run-phase 착수 기록 (Implementation Kickoff Approval — 2026-07-27)

```yaml
kickoff_approved_at: 2026-07-27
kickoff_gate: "Implementation Kickoff Approval (plan→run HUMAN GATE) — 오케스트레이터 AskUserQuestion, 감사 점수와 무관하게 필수"
base_sha: d176b815700829d4b50efe45cdb5d42de06bd090   # <BASE> — AC-BUSKWIZ-014의 git diff --stat <BASE>..HEAD 기준점
base_sha_short: d176b81
branch: feature/SPEC-COPILOT-BUSKWIZ-001              # main에서 분기, git-strategy branch_prefix 관례
branch_created_at_sha: d176b81                        # 분기 시점 = <BASE>, 기준점 일치
development_mode: tdd                                 # .moai/config/sections/quality.yaml
coverage_target: 85                                   # 커밋당 최소 80
auto_pr: false                                        # PR은 수동
path_selected: "A — 순서대로 (M0 라이브 먼저)"
progression_mode: "마일스톤별 체크포인트 (semi-autonomous)"
```

**사용자 확정 3건 (run-phase 착수 게이트에서 수집 — 재질의 금지)**: ⑤ 착수 경로 **A**(M0 라이브 선행, 예외 진행 없음 — 익스큐터 DESCOPE 선확정을 하지 않는다), ⑥ 브랜치 `feature/SPEC-COPILOT-BUSKWIZ-001`(PR 수동), ⑦ 진행 모드 **마일스톤별 체크포인트**(각 M 완료 시 보고 후 진행).

### M0 — 라이브 프로브 (실물 onPC 2.4.2, 2026-07-27) — **완료 · 판정 4건 확정**

#### 세션 조건

| | |
|---|---|
| 콘솔 | grandMA3 onPC 2.4.2, macOS (`app_gma3` PID 38963, `HOSTTYPE=onPC`) |
| 응답기 | `CopilotResponder` **v1.4.1** (ping 응답의 `version` 필드 실측) |
| OSC | **send 8000 / receive 9005** |
| 왕복 사전 확인 | `responder_roundtrip --listen-port 9005 --wait 5` → ping·state·exec **3/3 PASS** |
| 쇼파일 규모 | Pages 1 · Page 1 익스큐터 9 · Groups 4 · Sequences 17 · Color 풀 프리셋 1(`금빛 코러스` — LOOKLIB M7 잔여물) |
| 채널 | `responder_roundtrip`/`server.bridge.osc` **직결** — `gate.screen()` 미경유(LOOKLIB G2와 동일 등급의 매체 갭, 아래 Gaps) |

**착수 시 오진 1건 — 기록해 둔다.** 첫 프로브가 실패하자(`--listen-port` 기본값 **9000**) "인바운드 끊김"으로 단정하고 사용자에게 OSC 행 설정 점검을 요청했다. **틀렸다.** 인바운드는 처음부터 정상이었고 **응답 수신 포트만 어긋나 있었다** — LOOKLIB M0가 `send 8000 / receive 9005`로 이미 기록해 둔 값을 착수 전에 읽지 않은 것이 원인이다. 곁가지로 `~/MALightingTechnology/gma3_library/inout/osc/t OSC 1 Property Port 8000.xml`(`Port="9001" Receive="No" ReceiveCommand="No"`)을 근거로 삼았으나 그 파일은 **export 스냅샷이지 라이브 상태가 아니었다**. 교훈 두 가지: (i) **선행 SPEC의 세션 조건표를 착수 전에 읽는다**, (ii) 사용자의 GUI 관측("히스토리에 안 찍힘") 위에 결론을 쌓기 전에 **기계 증거를 먼저 소진한다**.

#### 판정 요약

| # | 전제 | 판정 | 근거 |
|---|---|---|---|
| 1 | **ASSUMPTION-16** 페이지·익스큐터 저작 문법 | **DESCOPE** | v1 미사용 확정(게이트가 2번으로 이미 닫힘). 문법의 존부 자체는 **비파괴 범위에서 판정 불가** — 아래 측정 1 |
| 2 | **ASSUMPTION-17** 빈 익스큐터 열거·판별 | **DESCOPE** | 미점유 인덱스가 **해석되지 않는다** — "비어 있음"과 "존재하지 않음"이 구별 불가. 아래 측정 2 |
| 3 | **ASSUMPTION-19** 팔레트를 익스큐터에 얹는 문법 | **DESCOPE** | 문법 **파싱 증거는 얻었으나 효과 미검증**, 그리고 그 검증에 필요한 "빈 익스큐터 식별"이 2번에서 닫혔다. 아래 측정 3 |
| 4 | **ASSUMPTION-18** 상한 규모 번들의 1왕복 | **GO** | 87/87 확인 · 총 5.77s · 66.3 ms/줄 · 사후 열화 없음. 아래 측정 4 |

**게이트 귀결**: REQ-BUSKWIZ-016은 `16 ∧ 17 ∧ 19`이고 **2번 하나만으로 이미 거짓**이다. → **M5는 ② DESCOPE 분기로 확정**, v1은 익스큐터·페이지 대상 커맨드를 **0건** 발화한다(`AC-BUSKWIZ-012` ②, `AC-BUSKWIZ-013` 스캔이 기계 고정). **DESCOPE는 실패가 아니라 정의된 결과다.** 4번 GO로 **M2의 기술적 차단이 해제**되었다.

#### 측정 1 — ASSUMPTION-16 (페이지·익스큐터 저작 문법)

비파괴 원칙으로 **존재하지 않는 대상**에 쏴서 파싱 여부만 가르려 했다. 결과는 **판정 불가**다 — 응답 문자열이 "문법 없음"과 "대상 없음"을 구분하지 못한다.

| 커맨드 | 콘솔 응답 |
|---|---|
| `Zzzblah Foo 1` *(대조: 순수 쓰레기)* | `Illegal object` |
| `Label Page 99 'probe'` | `Illegal object` |
| `Label Executor 9999 'probe'` | `Illegal object` |
| `Copy Page 99 At Page 98` | `Illegal source list` |
| `Delete Page 99` | `Illegal object` |

`Copy Page`가 **다른 문자열**(`Illegal source list`)을 낸 것은 그 동사가 파싱되어 소스 목록 평가까지 갔다는 뜻이다. 반면 `Label Page`/`Label Executor`는 대조군과 같은 `Illegal object`라 **두 해석이 모두 가능**하다. 결정적 테스트는 실제 페이지 생성(쇼파일 쓰기)을 요구하는데, **그 쓰기는 v1 판정을 바꾸지 못한다**(게이트가 이미 닫혔다). 따라서 쓰지 않았다 — 판정은 **DESCOPE(v1 미사용)**, 문법 존부는 Gaps에 남긴다.

#### 측정 2 — ASSUMPTION-17 (빈 익스큐터 판별) — **결정적**

`DataPool/Pages` → 페이지 1개. `DataPool/Pages/1` → 익스큐터 **9개**, `truncated: false`, `childCount 9 = len(children) 9`(**열거는 완전**):

```
페이지-로컬 인덱스: 1 · 2 · 5 · 11 · 91 · 92 · 93 · 95 · 101
이름:  Sequence 50 · Sequence 17 · Sequence 30 · Sequence 41 ·
       Sequence 80 · Sequence 14 · Sequence 16 · Sequence 62 · Ballad Yellow Red
```

`SPEC-COPILOT-EXECBODY-001/spec.md:43`이 기록한 표본(`1,5,11,91,92,93,95,101`)과 일치하고 `2`가 하나 늘었다. **미점유 인덱스 질의 결과**:

```
DataPool/Pages/1/3   -> {"ok": false, "error": "path segment not found: '3' (in DataPool/Pages/1/3)"}
DataPool/Pages/1/4   -> path segment not found
DataPool/Pages/1/102 -> path segment not found
DataPool/Pages/1/201 -> path segment not found
```

콘솔 번호 주소형(`copilot_responder.lua:405` 특례):

| 질의 | 결과 |
|---|---|
| `Executor 101` | **해석됨** — `{class: Executor, name: "Sequence 50", sequenceNo: 50, childCount: 0}` |
| `Executor 201` | **해석됨** — `{class: Executor, name: "Ballad Yellow Red", sequenceNo: 20}` |
| `Executor 103` | `ObjectList('Executor 103') unavailable` |
| `Executor 1` | `ObjectList('Executor 1') unavailable` — **raw 슬롯은 주소지정 불가** |

**판정 DESCOPE.** 미점유 슬롯은 어느 주소형으로도 해석되지 않으므로 **"비어 있는 익스큐터"를 식별하는 질의 경로가 존재하지 않는다** — `server/web/dash.py:200-206`(존재하는 자식만 열거)·`:210-231`("없음"과 "미확인" 미구분)의 라이브 확증이다. 열거의 **빈틈**(3·4·6~10…)에서 추론하는 우회는 두 이유로 막힌다: (i) 유효 인덱스 공간의 상한을 알려주는 질의가 없어 "빈 슬롯"과 "범위 밖"을 여전히 못 가르고, (ii) `page×100+slot` 관례를 일반 규칙으로 쓰는 것을 REQ-BUSKWIZ-017이 금지한다.

**부수 관측 — `page×100+slot`이 페이지 1에서 재확인되었다**: 로컬 `1`→콘솔 `101`, 로컬 `101`→콘솔 `201`. 그러나 **이 쇼파일에는 페이지가 1개뿐**이라 `REQ-EXECBODY-007`/`-008`이 요구하는 "2개 이상 서로 다른 페이지" 조건은 **여전히 미충족**이다. 하드코딩 금지는 그대로 유지된다.

#### 측정 3 — ASSUMPTION-19 (팔레트를 익스큐터에 얹는 문법)

동일 조건(존재하지 않는 익스큐터 `9999`)에서 **라이브 검증된 문법**과 **후보 문법**을 대조했다:

| 커맨드 | 콘솔 응답 |
|---|---|
| `Zzzblah Foo 1` *(대조)* | `Illegal object` |
| `Assign Sequence 50 At Executor 9999` *(라이브 검증된 문법)* | `Cannot Create Object` |
| `Assign Preset 4.1 At Executor 9999` *(후보)* | **`Cannot Create Object`** |
| `Assign Preset 4.1 Executor 9999` *(At 없는 변형)* | `Cannot Create Object` |
| `Assign Preset 4.1 At Page 99.99` *(dotted 변형)* | **`OK`** |
| `At Preset 4.1` *(프로그래머 리콜, 검증된 형태)* | `OK` |

**후보 문법이 대조군과 다르고 라이브 검증 문법과 같은 응답을 냈다** — 즉 `Assign Preset <p>.<s> At Executor <n>`은 **파싱된다.** plan-phase의 기본 기대값(부정)은 이 지점에서 **빗나갔다.**

**그럼에도 판정은 DESCOPE다.** 이유 둘:

1. **파싱은 효과가 아니다.** `Assign Preset 4.1 At Page 99.99`가 **`OK`를 반환하고도 아무것도 만들지 않았다**(사후 확인: Pages 여전히 1개). PROTOCOL.md `:16-17`과 LOOKLIB이 기록한 그 함정 — `Cmd()`는 거부된 커맨드에도 성공을 보고한다. **따라서 `OK`도 `Cannot Create Object`도 "프리셋이 실제로 익스큐터에 얹힌다"의 증거가 아니다.**
2. **긍정 검증 경로가 닫혀 있다.** 효과를 확인하려면 **실재하는 빈 익스큐터**에 얹어 보고 재조회해야 하는데, 측정 2가 "빈 익스큐터를 식별할 수 없다"를 확정했다. 즉 ASSUMPTION-19는 **ASSUMPTION-17에 종속되어** 닫힌다.

**우회 금지 준수**: 시퀀스를 만들어 얹는 측정은 하지 않았다(§D 시퀀스·큐 생성 제외 — 그 측정 자체가 범위 밖 기능의 근거가 된다).

#### 측정 4 — ASSUMPTION-18 (상한 규모 번들의 1왕복) — **GO**

**측정 대상의 정정**: 착수 전 이 항목을 "패킷 절단" 위험으로 읽었으나, `CommandExecutionPort.execute`는 **커맨드 1개씩** 실행하고 확인까지 블록한다(`server/orchestrator/ports.py:60-64`). 즉 87줄 번들은 하나의 거대 패킷이 아니라 **87회 순차 왕복**이며, 실제 위험은 **누적 지연과 확인 실패**다. 그렇게 측정했다.

| 측정 | 결과 |
|---|---|
| 커맨드당 왕복(지속 브리지, 10회) | **66.7 ms** (median) |
| 커맨드당 왕복(호출마다 소켓 재생성) | 566.7 ms — **하네스 아티팩트**, 실제 경로 아님 |
| **87줄 순차 실행** | **확인 87/87 · 총 5.77s · 평균 66.3 ms/줄 · 첫 실패 없음** |
| 직후 10회 재측정 | 66.5 ms — **누적 열화 없음** |

절단·타임아웃·확인 누락 **0건**. 상한 규모에서 여유가 크다(5.8초). **부정 분기(번들 분할 정책 = 사용자 결정 항목)는 발동하지 않는다.**

**중도 실패의 사후 상태**는 관측하지 못했다 — 87줄이 전부 성공해 중단 지점이 생기지 않았다. 의도적으로 실패를 주입해 재현하는 것은 쇼파일 쓰기를 요구하므로 하지 않았다(Gaps).

#### 정리 기록 — 쇼파일 잔여물 **0건**

프로브 전후 `childCount` 대조:

| 경로 | 프로브 전 | 프로브 후 |
|---|---|---|
| `DataPool/Pages` | 1 | **1** |
| `DataPool/Pages/1` (익스큐터) | 9 | **9** |
| `DataPool/PresetPools/4` (Color) | 1 | **1** |
| `DataPool/Sequences` | 17 | **17** |
| `DataPool/Groups` | — | 4 |

**생성·삭제·변경 0건.** 모든 쓰기 후보 커맨드는 존재하지 않는 대상을 겨냥해 발화했고, `OK`를 반환한 두 건(`Assign Preset 4.1 At Page 99.99`, `At Preset 4.1`)도 사후 확인에서 아무 오브젝트도 만들지 않았다. 프로그래머 상태는 `ClearAll`로 두 차례(중간·종료) 비웠다. **LOOKLIB M0가 의도적 잔여물을 남긴 것과 달리 본 세션은 잔여물이 없다** — 비파괴 프로브만으로 판정이 성립했기 때문이다.

#### 미검증 항목 (Gaps)

| # | 무엇 | 왜 측정하지 않았나 |
|---|---|---|
| **G1** | **페이지·익스큐터 저작 문법의 존부**(ASSUMPTION-16의 실체) | 결정적 테스트가 쇼파일 쓰기를 요구하고, **그 결과가 v1 판정을 바꾸지 못한다**(게이트가 측정 2로 이미 닫힘). 후속 SPEC이 익스큐터 축을 열 때 최우선 측정 항목이다 |
| **G2** | **`Assign Preset ... At Executor <n>`의 실제 효과** | 긍정 검증에 "실재하는 빈 익스큐터"가 필요한데 측정 2가 그 식별 불가를 확정했다. **파싱된다는 사실만 기록**하고 효과는 열어 둔다 |
| **G3** | **중도 실패의 사후 프로그래머 상태** | 87/87 성공으로 중단 지점이 생기지 않았다. 인위적 실패 주입은 쓰기를 요구한다 |
| **G4** | **게이트 경유 감사 로그** | 프로브가 `server.bridge.osc` **직결 채널**을 썼다(`gate.screen()` 미경유) — LOOKLIB G2와 동일 등급의 매체 갭. 판정은 콘솔 응답 원문으로 성립하나 감사 로그 항목은 생성되지 않았다. **M7 종단이 이 매체를 산출한다** |
| **G5** | **`page×100+slot`의 2페이지 이상 검증** | 이 쇼파일에 페이지가 1개뿐이다. `REQ-EXECBODY-007`/`-008` 조건 미충족 상태가 유지되며 REQ-BUSKWIZ-017의 하드코딩 금지는 그대로다 |

#### 잔여 위험

- **G2가 후속 SPEC의 출발점을 바꾼다.** plan-phase는 ASSUMPTION-19의 기본 기대값을 "부정"으로 적었으나 실측은 **파싱됨**이었다. 익스큐터 축을 다시 여는 SPEC은 "문법이 없다"가 아니라 **"문법은 있으나 효과와 대상 식별이 미검증"**에서 출발해야 한다. 이 정정을 여기 남긴다.
- **`OK`의 무의미성이 재확인되었다.** 본 세션에서 실제로 `OK`를 반환하고도 아무 일도 하지 않은 커맨드가 있었다. run-phase의 어떤 테스트도 `result == "OK"`를 효과의 증거로 써서는 안 된다 — 효과는 **재조회로만** 확인한다(`AC-BUSKWIZ-017` ③④가 이미 그 형태다).

#### AC 판정

**AC-BUSKWIZ-016 (LIVE — 2건 중 1번째) = PASS.** 측정 항목 1~4 판정 확정 · 5 정리 기록(잔여물 0건) · 6 Gaps 5건 명시. 라이브 세션 1/2 소진.

### M1 — 장르 조회 계층 (cycle_type=tdd, 2026-07-27) — **완료**

#### 산출물

| 파일 | 상태 | 내용 |
|---|---|---|
| `server/looks/busking.py` | **신규** | `GenreSelection` · `genres_in` · `looks_for_genre` · `select_genre` · `UNRESOLVED_GENRE` |
| `server/tests/test_busking_genre.py` | **신규** | 34 tests |

PRESERVE diff(`d176b81..`) **빈 출력**, `server/orchestrator/tools.py` **미접촉**(M1은 툴을 배선하지 않는다 — M4 소관). 작업 트리 변경은 위 신규 2파일뿐.

#### REQ 충족

- **REQ-BUSKWIZ-001** — `looks_for_genre`가 장르 전량을 **다이내믹스 오름차순 → `look_id` 사전순** 전순서로 반환. 반환 형상(`GenreSelection`)에 절단 신호 필드가 **없다**.
- **REQ-BUSKWIZ-002** — `select_genre`가 기존 `resolve_genre`를 호출한다(재정의 0건). 미해석은 후보 목록을 담은 실패 결과이며 **승격 없음**(`genre is None`).
- **REQ-BUSKWIZ-003** — 읽기 전용 순회. 호출 후 `library.looks`가 **동일 객체**임을 테스트가 고정.

**후보 목록은 자산에서 파생한다** — `genres_in`이 `{look.genre for look in library.looks}`를 정렬해 낸다. 상수로 박으면 라이브러리가 늘 때 한쪽만 갱신되어 거짓말이 된다.

**사유 어휘를 둘로 나눴다**: `EMPTY_QUERY`(matching에서 **재사용**)와 `UNRESOLVED_GENRE`(신설). "아무것도 안 물었다"와 "우리가 모르는 것을 물었다"는 다른 사실이고 사용자의 조치도 다르다. **한계를 함께 적었다** — `resolve_genre`는 "장르어 0개"와 "2개 이상"을 모두 `None`으로 접으므로 그 둘은 가르지 못한다. 가르려면 별칭 표를 다시 훑어야 하고 그것이 곧 재정의라 하지 않았다(모듈 독스트링에 명시).

#### AC 판정

| AC | 판정 | 근거 |
|---|---|---|
| **AC-BUSKWIZ-001** | **PASS** | 4장르 개수 실측 일치(worship 8 / rock 8 / ballad 7 / edm 9) · ① **edm 9건 그대로**(+ `9 > MAX_TOOL_MATCHES` 동반 단언) · ② `truncated`/`total` 필드 부재 · ③ 2회 호출 리스트 동등(순서 포함) |
| **AC-BUSKWIZ-002** | **PASS** | 한국어 7종·슬러그 4종 → 동일 장르 접힘(11 케이스) · ① `"재즈"` → 예외 아닌 실패 결과 + 후보 4종 · ② `genre is None`, `looks == ()` · ③ **AST 스캔** — 장르명을 담은 dict/set 리터럴 0건, `GENRE_ALIASES` 재할당 0건, 별칭 해석은 import로만 도달 |

#### 검증 수단의 정직성 — 뮤테이션 2종

통과하는 테스트가 무엇도 지키지 않는 경우를 배제했다.

| 뮤테이션 | 결과 |
|---|---|
| 정렬 키를 `look_id` 단독으로 | **4 failed** / 30 passed |
| 반환을 `[:8]`로 절단 | **4 failed** / 30 passed |
| 복원 | **34 passed** |

#### M1에서 재현된 결함 1건 — 검증 수단 쪽이었다

최초 작성한 `test_the_truncating_constant_is_not_referenced`가 **raw 텍스트 스캔**(`"MAX_TOOL_MATCHES" not in source`)이었고, 구현이 아니라 **모듈 `@MX:NOTE`의 산문**을 위반으로 잡아 실패했다 — 그 주석은 "왜 그 경로를 쓰지 않는가"를 설명하느라 이름을 적어야 했다.

이것은 `LOOKLIB v0.3.2`가 기록한 결함(**"raw 텍스트 스캔은 호출과 호출을 설명하는 독스트링을 구분할 수 없다"**)의 재현이고, 처방도 같다 — **AST 식별자 스캔**(`ast.Name.id` / `ast.Attribute.attr` / import 이름)으로 교체하고 **비공허성 2중 단언**(식별자를 실제로 모았는가 + 실제로 쓰는 `resolve_genre`·`EMPTY_QUERY`가 보이는가)을 붙였다. 독스트링을 지워 스캔을 통과시키는 방향은 택하지 않았다 — 그러면 경계를 문서화할 방법이 사라진다.

`AC-BUSKWIZ-009` 구간 1이 M4에 대해 같은 규율을 이미 요구하고 있다. **M1이 그 규율이 필요한 이유를 한 번 더 실증했다.**

#### 게이트

| 항목 | 결과 |
|---|---|
| `pytest server/tests/test_busking_genre.py -q` | **34 passed** |
| `pytest server/tests/ -q` (전체 회귀, M1 종료 시점 **직접 실측**) | **2325 passed · 0 failed** (89.11s) |
| `ruff check` (신규 2파일) | All checks passed |
| `ruff format --check` | 2 files already formatted (테스트 파일 1회 포맷 적용 후) |
| PRESERVE `git diff --stat d176b81 -- <목록>` | **빈 출력** |

**baseline 규율**: 착수 시점 전체 스위트 수를 직접 실측하지 않았으므로 **델타를 주장하지 않는다**. 위 2325는 M1 종료 시점에 본 마일스톤이 직접 측정한 수이며, 신규 실패 0건이라는 판정은 그 실행 자체로 성립한다.

### M2 — 슬롯 원장 + 다중 룩 번들 빌더 (cycle_type=tdd, 2026-07-27) — **완료**

**본 SPEC의 핵심 마일스톤.** 하드 결함 2건이 여기서 해소·회피되었다.

#### 산출물

| 파일 | 상태 | 내용 |
|---|---|---|
| `server/looks/busking.py` | 확장 | `GenreBundle` · `_advance`(슬롯·라벨 원장) · `_merge`(번들 결합) · `build_genre_bundle` · `instantiate_genre` |
| `server/tests/test_busking_bundle.py` | **신규** | 26 tests |

PRESERVE diff(`d176b81..`) **빈 출력** — `server/looks/instantiate.py` 포함. **결정 E("frozen을 바깥에서 감싼다")가 diff로 증명되었다**: 원장은 `dataclasses.replace`로 **새** `PoolBinding`/`PoolIndex`를 만들 뿐 룩 계층을 고치지 않는다. `server/orchestrator/tools.py`도 미접촉(툴 배선은 M4 소관).

#### 하드 결함 1 — 슬롯 비전진: 해소

`_advance`가 룩마다 청구한 슬롯과 **라벨을 함께** 누적해 다음 룩에 넘긴다. 라벨까지 누적하는 이유는 `_plan_stores`의 충돌 검사가 `binding.labels`(**콘솔이 이미 가진 것**)만 보기 때문이다 — 같은 번들이 만들 라벨끼리는 비교 대상이 아니라, 표시 이름이 같은 두 룩이 한 장르에 있으면 서로를 모른 채 각자 저장된다.

**결함의 실재를 같은 파일에서 함께 고정했다**(`AC-BUSKWIZ-004` 구간 2). 동일 `PoolIndex`로 `build_instantiation`을 3회 직접 호출하면 Color 슬롯이 `[1, 1, 1]`로 나온다 — 실측이다. 본 계층을 통과시키면 같은 입력이 `[1, 2, 3]`이 된다. 이 테스트가 사라지면 원장의 존재 이유가 문서에만 남는다.

미관측 풀(`occupied is None`)은 원장을 **전진시키지 않는다** — `None`을 튜플로 승격하면 미관측이 관측으로 둔갑한다(도달 불가 분기지만 방어적으로 막았다).

#### 하드 결함 2 — `ChangeDestination Root` dedupe 탈락: 회피

`_merge`가 목적지 커맨드를 **선두 1회**만 남긴다. 룩별 번들의 단순 연접은 금지다 — 2..N번째 목적지가 dedupe에 접히면서 번들 문자열과 콘솔이 받은 것이 어긋난다(LOOKLIB M7이 실물에서 관측한 그 탈락). **`tools.py`는 손대지 않았다**(결정 F).

목적지 문자열을 `_merge`에 다시 적지 않았다: **첫 비어 있지 않은 룩 번들의 선두가 정본**이고, 뒤 번들은 같은 선두를 가졌음을 확인한 뒤에만 그 한 줄을 뗀다. 리터럴을 복제하면 룩 계층이 바꿔도 여기가 모른다. 불일치는 `LookInstantiationError`다.

**결합 형상은 접지 않는다(unfolded)** — 룩 경계의 인접 `ClearAll` 두 줄을 1회로 병합하지 않았다. 근거는 **측정한 것을 출하한다**이다: M0의 ASSUMPTION-18은 접지 않은 상한 87행에서 GO를 받았고, 접는 것은 그보다 작은(따라서 안전하지만) **측정되지 않은** 형상이다. 부수적으로 룩별 사이클이 `build_instantiation`의 산출과 바이트 동일하게 유지되어 단일 룩 경로와의 동형성이 테스트로 직접 확인된다(퇴화 케이스).

#### AC 판정

| AC | 판정 | 근거 |
|---|---|---|
| **AC-BUSKWIZ-003** | **PASS** | 8룩 장르에서 `resolve_roles` 1회 · `resolve_pools` 1회(호출 카운팅 스파이). "8룩이 아니면 비례성을 못 본다"는 동반 단언으로 공허화 방지 |
| **AC-BUSKWIZ-004** | **PASS** | 구간 1 점유 `(1,2)`+룩 3개 → `{3,4,5}` 중복 0 · **구간 2 결함 실재(`[1,1,1]`)와 해소(`[1,2,3]`) 동시 고정** · 구간 3 혼합 부분 성공 2경로(풀 미해석·라벨 충돌) + **건너뜀 비공허** · 구간 4 패밀리 독립 · 구간 5 관측 우선 · 구간 6 **라벨 원장**(콘솔에 기존 라벨이 없어도 동명 룩 차단) |
| **AC-BUSKWIZ-005** | **PASS** | ① 목적지 `commands[0]`이고 count==1 · ③ 룩 2개에서도 1회 · 사이클이 `ClearAll`로 감싸짐 · ④ **실제 `run_commands` 경로**로 무손실 확인(per-command status 전량 `executed_ok`, `skipped_already_executed` 0건, `executed == commands`) · ⑤ **AST 식별자 스캔**으로 `CAPTURE_PER_FAMILY`/`capture_shape`/`shape` 부재 + 실라이브러리 4장르 값 라인 중복 0건 |
| **AC-BUSKWIZ-006** | **PASS** | 실라이브러리 4장르 전 커맨드에 `/overwrite` 0건(대소문자 무관) · 소스에도 0건 · 라벨 충돌 시 재슬롯 0건 |
| **AC-BUSKWIZ-007** | **PASS** | `occupied=None` → 전량 `no_free_slot` 스킵 · `occupied=()` → 슬롯 1 저장 · **두 상태의 산출 번들이 서로 다름**을 별도 단언 |

#### 검증 수단의 정직성 — 뮤테이션 2종

| 뮤테이션 | 결과 |
|---|---|
| `_advance`의 원장 전진 제거 | **5 failed** / 21 passed |
| `_merge`를 단순 연접으로 | **5 failed** / 21 passed |
| 복원 | **26 passed** |

#### M2에서 드러난 것 — 값 라인 충돌 위험은 **보호되지 않는다**

`run_commands` 무손실 테스트를 처음 작성했을 때 실패했다. 원인은 구현이 아니라 **픽스처**였다 — 룩 4개에 동일한 속성 페이로드를 줬더니 값 라인(`Attribute 'Dimmer' At 80`)이 겹쳐 두 번째가 dedupe에 접혔다.

**이것은 픽스처 실수인 동시에 SPEC이 경고한 위험의 재현이다.** `shared_capture`의 안전 근거는 "출하 32룩 전수에서 값 라인 중복 0건"이며 그것은 **라이브러리 데이터의 성질이지 구조적 보장이 아니다**(plan.md §E가 같은 이유로 번들 불변식에 이 assert를 넣었다). 한 장르에 전체 페이로드가 동일한 룩이 추가되면 `shared_capture`에서도 겹치고, 접힌 결과는 **빈 프로그래머 상태의 `Store`인데 콘솔은 성공으로 답한다.**

**본 마일스톤은 가드를 넣지 않았다.** 거부할지 건너뛸지는 결정 등록부(A~G) 밖의 새 결정이고, 감사 D6이 "등록부 밖에서 SPEC급 동작을 신설했다"를 지적한 바로 그 부류이기 때문이다. 대신 두 가지를 했다:

1. **불변식 테스트 유지** — 실라이브러리 4장르에서 값 라인 중복 0건(`AC-BUSKWIZ-005` ⑤). 라이브러리 증보가 이 성질을 깨면 여기서 잡힌다.
2. **characterization 테스트 신설** — `TestValueLineCollisionHazard`가 동일 페이로드 두 룩에서 dedupe 탈락이 **실제로 일어남**을 고정한다. 누군가 가드를 넣으면 이 테스트가 깨지고, 그 순간 결정이 기록을 강제받는다.

**→ 사용자 결정 대기 항목**: 값 라인 충돌에 가드를 넣을 것인가(거부 / 해당 룩 건너뛰기 / 현행 유지). v1 출하 라이브러리에서는 발동하지 않으므로 **M3~M7을 막지 않는다.**

#### 게이트

| 항목 | 결과 |
|---|---|
| `pytest server/tests/test_busking_bundle.py -q` | **26 passed** |
| `pytest server/tests/ -q` (전체 회귀, M2 종료 시점 **직접 실측**) | **2351 passed · 0 failed** (86.20s) |
| M1 종료 시점 실측 대비 | 2325 → 2351 (**+26** = 신규 테스트 수와 일치, 회귀 0건) |
| `ruff check` / `format --check` | clean / 2 files already formatted |
| PRESERVE `git diff --stat d176b81 -- <목록 + tools.py>` | **빈 출력** |

### M3 — 집계 보고 계층 (cycle_type=tdd, 2026-07-27) — **완료**

#### 산출물

| 파일 | 상태 | 내용 |
|---|---|---|
| `server/looks/report.py` | 신규 | `BuskingReport` · `LookVerdict` · `UnmappedPair` · `build_report` · `to_korean` · `reason_label` |
| `server/tests/test_busking_report.py` | 신규 | 27 tests — AC-BUSKWIZ-008 |
| `server/tests/busking_fixtures.py` | 신규 | M2·M3 공용 픽스처 (pytest 미수집 이름) |
| `server/looks/busking.py` | 변경 | `_merge`가 **룩별 구간**을 함께 반환, `GenreBundle.spans` |

#### 결정과 근거

1. **별도 모듈**. 한국어 표현 매핑은 커맨드 생성과 무관하고 `busking.py`는 이미
   조회·원장·결합 3책임을 진다.
2. **룩 귀속은 `spans`가 다리를 놓는다.** 결합 경계를 아는 유일한 자리가 `_merge`다.
   보고 계층이 결합 규칙을 다시 구현하면 두 곳이 갈라진다.
3. **`(b)`의 단위는 `(룩, 역할)` 쌍.** 리그를 1회만 해석하므로(REQ-BUSKWIZ-004)
   미매핑 역할 1종이 그것을 선언한 모든 룩에서 반복된다. distinct(언제나 6)로
   세면 룩별 합계와 어긋난다. 실측 재확인: worship 25 / rock 26 / ballad 20 / edm 26.
4. **매칭 판정 3종 ↔ 섹션 실패는 다른 부류.** 전자는 리그의 문제(그룹을 만들면
   해소), 후자는 **관측 자체의 실패**. 후자를 `no_match`로 보고하면 보지 않은
   리그에 대한 주장이 된다.
5. **`(c)`와 `(e)`를 합산하지 않는다.** 빌드 시점 건너뜀과 실행 중단은 원인도
   조치도 다르다.
6. **재시도 경로 없음.** 같은 instruction 안에서 재발화하면 앞서 성공한
   `Store Preset`/`Label Preset`이 dedupe에 조용히 접힌다(면제 집합 밖). AST 스캔이
   `execute`/`run_commands`/`retry`/`resend` 부재를 고정한다.

#### 뮤테이션 — 첫 판의 공허한 단언을 잡아냈다

| 뮤테이션 | 결과 |
|---|---|
| A: `(c)`+`(e)` 합산 렌더 | **첫 판 27 passed — 미검출** → 단언이 `N개 건너뜀`을 찾는데 렌더는 `건너뜀 N개`였다(공허). 렌더된 숫자를 직접 파싱해 대조하도록 교체 → **1 failed** |
| B: 미매핑을 distinct로 집계 | **2 failed** |
| C: 섹션 실패를 매칭 판정으로 접기 | **2 failed** |
| 복원 | 27 passed |

#### 게이트

| 항목 | 결과 |
|---|---|
| `test_busking_report.py` | **27 passed** |
| `pytest server/tests/ -q` (전체 회귀, **직접 실측**) | **2378 passed · 0 failed** (87.44s) |
| M2 종료 시점 실측 대비 | 2351 → 2378 (**+27** = 신규 테스트 수와 일치, 회귀 0건) |
| `ruff check` / `format --check` | 신규·변경 5파일 clean / already formatted |
| PRESERVE + `tools.py` `git diff --stat d176b81` | **빈 출력** |

**범위 밖 기존 결함 1건**: `server/tests/test_web_dash.py:523` E501(103>100). baseline
(stash 후 재측정)에서도 동일하고 본 SPEC의 변경 0건이라 정정하지 않는다.

**중복 제거**: M2 테스트의 지역 `FULL_RIG`/`_look`/`_bundle_for`가 신규 픽스처
모듈과 동일해 그쪽으로 통합했다(호출부 50곳 기계 치환, 87 passed 유지).

### 결정 H — 값 라인 충돌: 건너뛰기 + 사유 보고 (2026-07-27) — **확정**

M2가 characterization 테스트로 가시화하고 사용자 결정으로 남겨 둔 위험을 닫았다.

**위험**: 한 장르 안에 전체 속성 페이로드가 동일한 룩이 둘이면 `shared_capture`의
값 라인이 문자열로 같아지고, 값 라인은 dedupe 면제 집합에 없으므로 두 번째가
`skipped_already_executed`로 접힌다. 직전 `ClearAll`·선택은 면제라 살아남아
**빈 프로그래머 상태로 `Store`가 실행되고 콘솔은 성공으로 답한다.**

**결정**: 거부(예외)가 아니라 **건너뛰기 + 사유 보고**.

| 후보 | 판정 | 근거 |
|---|---|---|
| 거부(`LookInstantiationError`) | 기각 | 룩 하나의 저작 결함으로 장르 전량이 죽는다. 그 예외는 이 코드베이스에서 **구조적 기형**(알 수 없는 shape, 목적지 불일치)에만 쓰인다 |
| **건너뛰기 + `SkippedStore`** | **채택** | `_plan_stores`가 `conflict`/`no_free_slot`/`pool_unresolved`를 전부 이 형태로 답한다(`instantiate.py:325-384`) — "이 저장은 안전하게 일어날 수 없다"에 대한 기존 답이 정확히 이것이다. M3의 2단 보고가 이미 표현 채널을 갖고 있다 |
| 현행 유지 | 기각 | 조용한 오작동. 콘솔이 성공으로 답하므로 사용자가 알 방법이 없다 |

**거처**: `server/looks/busking.py`의 `_guard_collision` — `instantiate.py`는
PRESERVE이고, 결정 E("frozen을 바깥에서 감싼다")가 정한 그 형상이다. 조건이
**번들 안의 이웃 룩**에 달려 있어 룩 하나만 보는 `build_instantiation`은
원리적으로 알 수 없다는 점도 거처를 정한다.

비교 문자열은 `instantiate._values_line`에서 가져온다 — dedupe가 실제로 비교하는
바로 그 문자열이며, 여기서 다시 조립하면 두 곳이 갈라진다.

**v1 라이브러리에서는 발동하지 않는다**(출하 32룩 값 라인 중복 0건) — 오늘의
동작 변화는 0이고, 내일 라이브러리에 중복이 들어올 때 조용히 깨지는 대신
보고에 뜬다.

| 뮤테이션 | 결과 |
|---|---|
| 가드 제거 | **4 failed** |
| 빈 번들도 값 라인 예약 | **첫 판 33 passed — 미검출** → 테스트가 번들을 둘 따로 만들어 원장이 공유되지 않았다(공허). 한 번들 안에서 검사하도록 교체 → **1 failed** |
| 건너뛴 룩도 원장 전진(`created` 유지) | **2 failed** |

M2가 남긴 `TestValueLineCollisionHazard`는 예고대로 깨졌고, `TestValueLineCollisionGuard`
8건으로 교체했다. 부수적으로 `test_every_look_cycle_is_clearall_bracketed`의 픽스처가
우연히 동일 페이로드를 쓰고 있어(주제는 괄호 감싸기) 서로 다른 값으로 고쳤다.

### M4 — 툴 배선 · 실행 경로 · LiveLock (cycle_type=tdd, 2026-07-27) — **완료**

#### 산출물

| 파일 | 상태 | 내용 |
|---|---|---|
| `server/orchestrator/tools.py` | 변경 | `prepare_busking` 핸들러 + `ToolDefinition` + `TOOL_NAMES`/`handlers` 등재 (**신규 툴 등록만**) |
| `server/looks/report.py` | 변경 | `BuskingReport.to_dict()` — `LookInstantiation.to_dict()` 관례 준수 |
| `server/tests/test_busking_tool.py` | 신규 | 20 tests — AC-BUSKWIZ-009/010/011 |
| `server/tests/test_tools.py` | 변경 | 닫힌 집합 개수 6 → 7 (툴 추가의 정당한 귀결) |

#### 결정과 근거

1. **툴 1종 `prepare_busking`**, 인자는 `genre` 하나. 스키마에 그룹·풀·슬롯·픽스처
   필드 **0개**이고 핸들러가 `collect_rig_sections`로 직접 읽는다(REQ-BUSKWIZ-020) —
   근거는 `tools.py:735-738`이 이미 적어 둔 그것이다.
2. **`run_commands`의 호출자**이지 제2 실행 표면이 아니다. 게이트·LiveLock·dedupe·
   감사 로그를 그 한 경로에서 상속한다.
3. **`is_error` 규약**: 알 수 없는 장르 = `True`(후보 목록으로 정정 가능),
   저장 0건 = `False`(재시도해도 같은 리그는 같은 답), **LiveLock 강등 = `False`**.
   강등을 `True`로 두면 자기수정 루프가 같은 잠금에 다시 부딪힌다.
4. **LiveLock 감지는 `gate_status == "locked"`**. plan.md와 `gate.py:72` 주석은
   `"proposal"`을 상태로 열거하지만 **실제 발화값은 `"locked"`**이고 `"proposal"`은
   per-command status다(`gate.py:471-485` 실측). 리터럴을 `_LOCKED` 상수로 두고
   출처를 주석에 박았다.
5. **LiveLock 테스트는 실물 `SafetyGate` + 활성 `LiveLock`**. 목 게이트로 상태
   문자열만 흉내내면 "우리가 그 문자열을 읽는가"만 검증된다. 콘솔 페이크는 송신
   시도 시 `AssertionError`를 던진다.

#### 뮤테이션 — 5종 전부 검출

| 뮤테이션 | 결과 |
|---|---|
| LiveLock 강등을 `is_error=True`로 | 1 failed |
| 알 수 없는 장르를 `is_error=False`로 | 1 failed |
| 저장 0건을 `is_error=True`로 | 1 failed |
| `handlers`에서만 누락(선언은 유지) | **14 failed** |
| 스키마에 리그 필드 추가 | 1 failed |

#### 게이트

| 항목 | 결과 |
|---|---|
| `test_busking_tool.py` | **20 passed** |
| `pytest server/tests/ -q` (전체 회귀, **직접 실측**) | **2405 passed · 0 failed** (85.82s) |
| M3 종료 시점 실측 대비 | 2378 → 2405 (**+27** = 신규 20 + 가드 8 − 교체 1, 회귀 0건) |
| `ruff check` / `format --check` | All checks passed |
| PRESERVE `git diff --stat d176b81 -- <목록>` | **빈 출력** |
| `tools.py` 잠긴 구간 (`_PROGRAMMER_STATE_COMMANDS` · `_is_programmer_state` · dedupe) | **바이트 단위 무변경** (`git show d176b81:` 대조) |
| `tools.py` 변경 성격 | 175 insertions / 2 deletions — 2건은 `TOOL_NAMES`·`handlers` 등재 |

**AC 판정**: AC-BUSKWIZ-009 PASS · AC-BUSKWIZ-010 PASS · AC-BUSKWIZ-011 PASS.

### M5 — 익스큐터 레이아웃 GO/DESCOPE (cycle_type=tdd, 2026-07-27) — **완료 (② DESCOPE 분기)**

#### 분기 판정

M0 측정 2가 결정적이다: 미점유 익스큐터 인덱스가 어느 주소형으로도 해석되지
않아 **"비어 있는 익스큐터"를 식별하는 질의 경로가 존재하지 않는다.**
`REQ-BUSKWIZ-016`의 게이트는 `16 ∧ 17 ∧ 19`이므로 2번 하나로 이미 거짓이고,
v1은 익스큐터·페이지 대상 커맨드를 **0건** 발화한다. **DESCOPE는 실패가 아니라
정의된 결과다.**

#### 산출물

| 파일 | 상태 | 내용 |
|---|---|---|
| `server/tests/test_busking_executor.py` | 신규 | 10 passed + **3 skipped(GO 분기 보존)** — AC-BUSKWIZ-012 ② / AC-BUSKWIZ-013 |
| `server/looks/busking.py` | **무변경** | GO 분기에서만 추가하도록 plan.md가 정했고, 분기가 ②이므로 추가 없음 |

#### 검증 수단 — 소스 grep이 아니라 산출물 전수

dotted form이 실제로 발화되는 유일한 경로는 `f"Page {page}.{executor}"` 같은
변수 조립이고 **그 소스 문자열에는 숫자가 없어** `\d+\.\d+`가 결코 매치하지
않는다(감사 D3). 그래서 4장르 전량이 **실제로 생성한 커맨드 튜플 전수**에 스캔을
건다. 리터럴 `100` 검사도 텍스트가 아니라 **AST `BinOp` 피연산자** 검사다.

**스캐너 자체의 비공허성을 별도 테스트로 증명한다** — 금지 형태를 심어 스캐너가
그것을 잡는지 확인한다(`Assign Sequence 17 At Executor 191`,
`Assign Sequence 17 At Page 1.102`, `page_no * 100 + slot`). 이것이 없으면
"0건 통과"와 "정규식이 아무것도 안 잡음"이 구별되지 않는다.

#### GO 분기 — 삭제하지 않고 skip 사유를 달아 보존

`TestGoBranch` 3건이 `skip` 사유와 함께 남아 있다(AC-BUSKWIZ-012 비고). 사유
문자열에 **후속 SPEC의 출발점**을 함께 기록했다: 익스큐터 축은 "문법이 없다"가
아니라 **"문법은 파싱되나 효과와 대상 식별이 미검증"**에서 시작해야 한다
(M0 G2의 정정). 번호 출처가 `resolved_executor_nos`가 **아님**(그것은 정의상
점유된 익스큐터라 운영자 플레이백을 덮는다)도 테스트 본문 주석에 남겼다.

#### 뮤테이션 — 3종 전부 검출

| 뮤테이션 | 결과 |
|---|---|
| 번들에 `Assign Sequence 17 At Executor 191` 주입 | 2 failed |
| 번들에 `Assign Sequence 17 At Page 1.102` 주입 | 3 failed |
| `page * 100 + slot` 산술 도입 | 1 failed |

#### 게이트

| 항목 | 결과 |
|---|---|
| `test_busking_executor.py` | **10 passed · 3 skipped** |
| `pytest server/tests/ -q` (전체 회귀, **직접 실측**) | **2415 passed · 3 skipped · 0 failed** (87.07s) |
| M4 종료 시점 실측 대비 | 2405 → 2415 (**+10** = 신규 통과 테스트 수와 일치, 회귀 0건) |
| `ruff check` / `format` | OK |
| PRESERVE `git diff --stat d176b81 -- <목록>` | **빈 출력** |

**AC 판정**: AC-BUSKWIZ-012 PASS(② 경로) · AC-BUSKWIZ-013 PASS.

### M6 — 회귀 · PRESERVE · 정적 금지 스캔 (cycle_type=tdd, 2026-07-27) — **완료**

#### 산출물 — 신규 테스트 파일 0개

M6는 새 판정을 소유하지 않는다(소유 관계가 흐려진다). AC-BUSKWIZ-015의 정적
스캔은 커맨드 조립을 소유한 **M2의 파일**에 넣었다.

| 파일 | 상태 | 내용 |
|---|---|---|
| `server/tests/test_busking_bundle.py` | 변경 | `TestNoPerShowNumberEntersStatically` 8건 — AC-BUSKWIZ-015 |

#### AC-BUSKWIZ-015 — 무엇을 어떻게 스캔했나

| 검사 | 수단 |
|---|---|
| 커맨드 문자열에 박힌 리그 번호 | `(Group\|Preset\|Executor\|Page\|Fixture\|Sequence)\s+\d` — **독스트링을 제외한** 코드 문자열 상수 전수 |
| f-string에 끼워 넣은 숫자 상수 | AST `FormattedValue.value`가 숫자 `Constant`인 노드 |
| 리그 파라미터의 숫자 기본값 (`pool=4` 같은 룰북 예시) | AST 함수 인자 기본값 × 파라미터명 `pool\|slot\|group\|executor\|page\|fid\|fixture` |

**독스트링 제외가 핵심이다** — 산문이 "왜 그것을 피하는가"를 설명하려면 금지
토큰을 적어야 하고, 그 때문에 스캔이 무뎌지면 안 된다. `test_looks_resolver.py:495-497`이
같은 이유로 만든 `_code_string_constants`를 **재사용**했다(재구현하면 두 곳이 갈라진다).

세 스캐너 전부 **금지 형태를 심어 잡히는지 확인하는 비공허성 테스트**를 동반한다
(`Store Preset 4.1` · `Group 11 + 12` · `def store(*, pool: int = 4)`). 없으면
"0건 통과"와 "스캐너가 아무것도 안 잡음"이 구별되지 않는다.

#### 게이트 — 전량

| 항목 | 결과 |
|---|---|
| `pytest server/tests/ -q` (**M6가 직접 실측**, 이월 인용 없음) | **2423 passed · 3 skipped · 0 failed** (87.12s) |
| M5 종료 시점 실측 대비 | 2415 → 2423 (**+8** = AC-015 스캔 수와 일치, 회귀 0건) |
| PRESERVE `git diff --stat d176b81..HEAD -- <목록>` | **빈 출력** (`<BASE>..HEAD` 범위 — 인자 없는 `git diff`는 커밋 직후 항상 비어 게이트가 무력해진다) |
| `tools.py` `_PROGRAMMER_STATE_COMMANDS` · `_is_programmer_state` · dedupe 블록 | **3구간 전부 무변경** (`git show d176b81:` ↔ `git show HEAD:` 바이트 대조) |
| 신규 YAML·JSON 자산 (`--diff-filter=A`) | **0개** |
| `ruff check` — 본 SPEC 변경 10파일 | **All checks passed** |
| `ruff format --check` — 같은 10파일 | 9 formatted / **1 기존 결함** (아래) |

#### 기존 비-clean 지점 2건 — 손대지 않고 기록 (M6 규칙)

무관 재포맷은 PRESERVE 게이트의 신호를 흐리므로 정정하지 않는다.

| 위치 | 내용 | baseline 확인 |
|---|---|---|
| `server/tests/test_web_dash.py:523` | `ruff check` E501 (103>100) | stash 후 재측정 — 동일. 본 SPEC 변경 0건 |
| `server/tests/test_tools.py:567,598` | `ruff format` 미충족 2 hunk | `git show d176b81:` 사본에서도 동일. 본 SPEC 변경 위치는 122~132행으로 무관 |

#### 재확인만 하고 소유하지 않은 AC

`AC-BUSKWIZ-009`(M4) · `AC-BUSKWIZ-006`(M2) · `AC-BUSKWIZ-013`(M5)의 스캔이
전체 스위트에서 깨지지 않았음을 회귀로 확인했다. 최초 판정은 각 소유
마일스톤에 귀속한다.

**AC 판정**: AC-BUSKWIZ-014 PASS · AC-BUSKWIZ-015 PASS.

## §E.3 Run-phase Audit-Ready Signal

_<pending run>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync>_

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

> 본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다. plan.md의 대응 절은 plan-phase 권고이며 오케스트레이터가 확정·기각한다. 이 헤딩은 v0.1.0 착수 시점에 **선제 생성**되었다 — 선행 SPEC에서 plan.md가 존재하지 않는 `progress.md` §F를 구속력 있는 기록으로 지목했던 끊어진 참조(`SPEC-COPILOT-LOOKLIB-001/plan.md:289`)를 재현하지 않기 위해서다.

```yaml
decided_at: 2026-07-27
decided_by: orchestrator
mode: 5   # sub-agent (단일 순차 에이전트)
plan_recommendation: sub-agent   # plan.md §G Decision과 일치 — 오케스트레이터가 확정
rationale: >
  Tier L이나 마일스톤이 순차 의존이다(M2←M1, M3←M2, M4←M3, M5←M0 판정, M6←M4/M5, M7←M6).
  예상 파일 8~10개 · 도메인 1개(파이썬 백엔드) · 단일 언어라 병렬 이득이 없고,
  Anthropic의 coding-task 병렬성 유보("most coding tasks involve fewer truly
  parallelizable tasks than research")가 그대로 적용된다.
modes_rejected:
  mode_1_trivial: "Tier L · 신규 모듈 2개 · AC 17건 — trivial 아님"
  mode_2_background: "마일스톤별 체크포인트를 사용자가 선택 — 백그라운드 부적합"
  mode_3_agent_team: "RETIRED (정적 계층 폐기)"
  mode_4_parallel: "구현부는 순차 의존. 단 plan-phase의 read-only 조사 팬아웃에는 이미 사용했다"
  mode_6_workflow: "§C.3 역량 게이트 미충족 — 균일 기계 변환 30파일+ 조건에 해당하지 않는다"
user_touchpoints_required: 2   # 라이브 세션 2회(M0 · M7)의 착수 확인
user_touchpoints_for_decisions: 0   # 결정 7건(A~G) 전부 plan-phase에서 폐쇄
conditional_touchpoint: "ASSUMPTION-18 부정 시 번들 분할 정책 — 사용자 결정 항목"
progression: "semi-autonomous — 각 마일스톤 완료 시 체크포인트 보고 (사용자 확정 ⑦)"
ac_converge_goal: not_set   # 체크포인트 모드 선택으로 per-turn 자율 루프 미사용
```
