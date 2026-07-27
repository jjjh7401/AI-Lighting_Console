# SPEC-COPILOT-BUSKWIZ-001 — 구현 계획 (plan)

status: draft (v0.1.0, 2026-07-27) · Tier L · 본 문서는 spec.md의 요구를 마일스톤으로 전개한다.

> **v0.1.0 — 최초 작성.** 마일스톤 **M0~M7**, 결정 **7건(A~G)**, 미해결 마커 **0건**. 결정 폐쇄 경로는 두 갈래다 — **사용자 사전 확정 4건**(A 익스큐터 게이트 · B 팔레트 축 상속 · C 실행 단위 · D 라이브 세션 2회, spec.md §A 사전 확정 사실)과 **엔지니어링 판단 3건**(E 슬롯 원장 · F dedupe 무개정 · G 장르 조회 경로). 본 SPEC은 선행 `SPEC-COPILOT-LOOKLIB-001`(completed)이 **런타임 실행을 만들지 않고 넘긴** 장르 묶음 인스턴스화(`SPEC-COPILOT-LOOKLIB-001/spec.md:182`)를 구현하며, 계획 구조는 그 SPEC의 plan.md(M0 프로브 + 라이브 세션 회계 + §A.4a 결정 표 + §G 모드 사전평가)를 그대로 계승한다. **마일스톤별 `- **AC**:` 배정은 `acceptance.md` §C.0의 배정표와 1:1이며, 한쪽을 고치면 다른 쪽도 고친다**(`acceptance.md 서두 개정 블록쿼트`, `:87`).
>
> **본 계획이 만드는 것은 조율 계층 하나다.** 룩 스키마·로더·역할 어휘·역할 해석기·풀 해석기·단일 룩 번들 빌더·라이브러리 32룩은 전부 **소비**되고 변경되지 않는다(§A.5). 신규 코드는 장르 조회 · 슬롯 원장 · 번들 결합 · 집계 보고 · 툴 1종, 그리고 M0가 GO일 때만 익스큐터 레이아웃이다.

## §A. 접근 요약 (Context)

본 절은 **변경 가능성이 높은 결정을 먼저** 배치한다(가장 되돌리기 어렵거나 후속 결정을 규정하는 순서). 빌드 순서(§B)와 다를 수 있다 — §A.2가 그 편차를 설명한다.

### §A.1 결정 검토 우선순위 (되돌리기 어려운 순 — 빌드 순서 아님)

**미해결 결정은 0건이다.** 이 표는 "무엇을 물어볼까"가 아니라 **"확정된 것 중 무엇을 먼저 재검토해야 하는가"**의 순서다 — 사람이 이 SPEC을 리뷰할 때 위에서부터 보면 변경 파급이 큰 순서로 읽게 된다. 상위 3건은 확정 후 파괴 변경 시 **라이브 세션 재실시** 또는 **본 SPEC의 존재 이유 소멸**을 유발한다.

| 순위 | 결정 | 확정 경로 | 위치 | 왜 먼저 재검토해야 하는가 |
|---|---|---|---|---|
| **1위** | **익스큐터 페이지 레이아웃 = M0 라이브 프로브 GO/DESCOPE 게이트** | 사용자 확정 ① | §A.4a **결정 A**, spec.md §A 사전 확정 사실(익스큐터 게이트 + 실측 근거) + REQ-BUSKWIZ-016, §B M0/M5 | **되돌림 비용이 유일하게 라이브 세션 단위다.** 이 결정은 M0 프로브의 측정 항목(ASSUMPTION-16 · ASSUMPTION-17 · **ASSUMPTION-19**)과 M5의 존폐를 함께 규정한다. 게이트를 사후에 바꾸면 실물 콘솔 세션을 다시 잡아야 하고(사람 + 쇼파일 일정), 그것이 본 SPEC에서 가장 비싼 자원이다. **v1 착수 전에만 변경 가능**하다. |
| **2위** | **슬롯 원장** | 엔지니어링 판단 | §A.4a **결정 E** + §A.4a-E, spec.md §A 하드 결함 1 + REQ-BUSKWIZ-005, §B M2 | **이 결정이 없으면 본 SPEC은 존재 이유가 없다.** 선행 구현을 룩마다 그대로 호출하면 N개 룩이 전부 같은 슬롯을 겨냥한다(`server/looks/instantiate.py:307-312`, `:358`) — 그리고 라벨이 다르므로 `CONFLICT`에도 걸리지 않는다(`:359-361`). 번들 결합·부분 성공·보고의 건너뜀 계수가 전부 여기에 매달린다. |
| 3위 | **실행 단위 = 단일 번들 · 승인 1회 · 부분 성공 구조화 보고** | 사용자 확정 ③ | §A.4a **결정 C**, spec.md §A 사전 확정 사실(실행 단위) + REQ-BUSKWIZ-010 · REQ-BUSKWIZ-013, §B M3/M4 | 툴 인터페이스(승인 1회를 전제한 1왕복), 보고 형상(집계+룩별 2단), ASSUMPTION-18이 실측할 대상(**기본 형상 상한 87줄**의 1왕복 — §A.2 계수 각주)이 **모두 여기서 갈린다**. 룩 단위 분할 승인으로 되돌리면 세 가지가 함께 바뀐다. 반대 논거는 기각이 아니라 **표면화된 뒤 수용된 위험**으로 존치한다(spec.md §A 수용된 잔여 위험). |
| 4위 | **`tools.py` dedupe 규칙 무개정 — 번들 형상으로 회피** | 엔지니어링 판단 | §A.4a **결정 F** + §A.4a-F, spec.md §A 하드 결함 2 + REQ-BUSKWIZ-006, §B M2 | 뒤집으면 `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(`:227-231`)와 dedupe 블록(`:526-550`)이 PRESERVE에서 빠지고, 그 변경은 `run_commands`를 쓰는 **모든** 소비자(MVP·DASHUI·EXECBODY·LOOKLIB)에 파급된다. 본 SPEC의 변경 표면을 "신규 툴 등록"으로 유지하는 것이 이 결정에 달려 있다. |
| 5위 | **장르 룩 조회 = `LookLibrary` 직접 순회** | 엔지니어링 판단 | §A.4a **결정 G** + §A.4a-G, REQ-BUSKWIZ-001, §B M1 | 조회 계층에 국소적이라 **상대적으로 가역적**이다. 다만 `match_looks` 툴 경로를 쓰면 `MAX_TOOL_MATCHES = 8`(`server/looks/matching.py:71`)에서 EDM 9룩이 1건 잘리므로, 되돌리려면 그 상수 또는 그 툴의 계약을 건드려야 한다(= PRESERVE 밖으로 나간다). |
| 6위 | **팔레트 축 = LOOKLIB in-scope 4풀 상속** | 사용자 확정 ② | §A.4a **결정 B**, spec.md §A 사전 확정 사실(팔레트 축) | **본 SPEC이 정할 여지가 애초에 없다** — `IN_SCOPE_POOL_FAMILIES`(`server/looks/schema.py:58`)를 재정의하지 않고 import한다. 되돌리려면 LOOKLIB 스키마를 개정해야 하고 그것은 PRESERVE 위반이자 소비자 2개(P1-1/P1-2)를 함께 깨뜨린다(`server/looks/schema.py:20-25` `@MX:NOTE`). 포지션 축은 선행 SPEC이 이미 닫았다. |
| 7위 | **라이브 세션 2회 (M0 + M7)** | 사용자 확정 ④ | §A.4a **결정 D**, spec.md §A 사전 확정 사실(라이브 세션 2회), §B 라이브 세션 회계 | 코드 파급이 아니라 **일정 파급**이다. 세션 수를 줄이려면 M0를 없애야 하는데, 그러면 결정 A의 게이트가 판정 불가가 된다(§C.7 예외 절차 참조). 기계적 — 상위 결정이 확정되면 자연히 따라온다. |

### §A.2 빌드 순서 vs 리뷰 순서 — 그리고 M0가 필요한 이유

본 SPEC은 순수 조회 계층부터 쌓는 구조라 빌드 순서가 결정 우선순위와 대체로 일치한다. 편차는 하나다: **M0(라이브 프로브)가 M1보다 앞선다.**

**LOOKLIB의 논거를 그대로 복사하면 틀린다.** 그 SPEC에서는 프로브 항목 하나(ASSUMPTION-15, 빔 attribute 문자열)가 **로더를 기술적으로 차단**했기 때문에 M0가 M1 앞에 설 수밖에 없었다(`SPEC-COPILOT-LOOKLIB-001/plan.md:38`). 본 SPEC에는 그런 항목이 **0건**이다 — M1의 장르 조회는 이미 로드된 `LookLibrary`(`server/looks/schema.py:120-130`)에 대한 인메모리 순회이고, 콘솔·익스큐터·번들 규모 어느 것도 그 반환 형상을 규정하지 않는다. 항목별로 정확히 적으면:

| 프로브 항목 | 진짜 차단 대상 | 왜 그 마일스톤인가 | M0에 있는 이유 |
|---|---|---|---|
| **ASSUMPTION-18** (단일 번들의 1왕복 성립 — **기본 형상 상한 87줄**) | **M2 (번들 결합)** | 번들 규모 정책이 여기서 갈린다. 부정이면 분할이 필요한데 그것은 사용자 확정 ③(단일 승인)과 정면 충돌하므로 SPEC이 임의로 정할 수 없다(ASSUMPTION-18) | **결정 C의 물리적 성립 여부** — 라이브 실측 최대는 LOOKLIB의 21줄이고, 본 SPEC의 최대 번들은 그 **약 4.1배**(87/21)다(아래 계수 각주) |
| **ASSUMPTION-16** (페이지·익스큐터 저작 문법 수용) | **M5 (익스큐터 레이아웃)** | REQ-BUSKWIZ-016의 발동 여부 자체 | 라이브 세션을 요구하며, 부정이면 M5가 통째로 DESCOPE된다 |
| **ASSUMPTION-17** (빈 익스큐터 열거·판별) | **M5 (익스큐터 레이아웃)** | 같음 — 셋 중 하나만 부정이어도 DESCOPE(REQ-BUSKWIZ-016) | 같은 세션에 묶는 것이 세션을 쪼개는 것보다 싸다 |
| **ASSUMPTION-19** (팔레트를 익스큐터에 얹는 문법) | **M5 (익스큐터 레이아웃)** | **얹을 대상의 존재 여부** — 16·17이 둘 다 GO여도 이것이 부정이면 레이아웃은 성립하지 않는다(spec.md REQ-BUSKWIZ-016 하위 절(ASSUMPTION-19가 게이트에 추가된 이유)) | 같은 세션. **v0.1.2가 신설한 3번째 논리곱 항**이며, 이것이 없던 v0.1.1까지는 REQ-BUSKWIZ-016이 충족 불가였다 |
| (M1을 기술적으로 차단하는 항목) | **없음 — 0건** | 장르 조회는 순수 인메모리 순회이고 콘솔에 접촉하지 않는다 | 해당 없음 |

**계수 각주 — 번들 규모의 실측값 (plan-phase에서 라이브러리 자산을 직접 계수).** spec.md 초판은 규모를 "최대 약 40여 커맨드"로 적었으나 그것은 **쌍(pair) 수에서 나온 추정치**였고, 실제 행 수는 그보다 크다(spec.md v0.1.1이 이를 **51~87행**으로 정정했다). 번들 길이는 캡처 형상에서 결정론적으로 나온다 — v1이 쓰는 `shared_capture`(`server/looks/instantiate.py:396-404`)는 룩 1개 = `ClearAll` + 선택 + 값 + (`Store`+`Label`)×P + `ClearAll` = **4 + 2·P**, 참고로 `per_family_capture`(`:406-412`)는 패밀리마다 캡처 사이클을 격리해 **5·P + 1**. 여기에 번들 선두의 `ChangeDestination Root` 1줄을 더해 각각 **1 + Σ(4 + 2·Pᵢ)** / **1 + Σ(5·Pᵢ + 1)** (REQ-BUSKWIZ-006의 선두 1회 형상). `P`는 그 룩이 값을 가진 in-scope 풀 패밀리 수이며 실측 분포는 **{2, 3, 4}** 다.

| 장르 | 룩 수 | **v1 형상 · 4풀** | v1 형상 · Dimmer·Color만 | v1 형상 · 룩 경계 `ClearAll` 병합 | per-family (도달 불가 · 참고) |
|---|---|---|---|---|---|
| ballad | 7 | 67줄 | 57줄 | 61줄 | 103줄 |
| rock | 8 | 77줄 | 65줄 | 70줄 | 119줄 |
| worship | 8 | 77줄 | 65줄 | 70줄 | 119줄 |
| **edm** | **9** | **87줄** | 73줄 | 79줄 | **135줄** |

**따라서 M0의 ASSUMPTION-18 측정 대상은 v1 형상의 실제 상한 87줄(edm · 4풀) 하나다** — 40여 줄에서 통과했다고 GO로 판정하면 M2가 실측되지 않은 규모 위에 서게 된다. 전체 밴드 **51~87줄**은 spec.md v0.1.1 표기와 같다(최소 51 = ballad · Dimmer/Color만 · 룩 경계 병합으로, 위 표에 열로 세우지 않은 네 번째 변형이다). 열이 갈리는 두 변수 — (a) 리그가 Beam·Focus 풀을 주소지정 가능하게 보고하는가(아니면 그 저장이 건너뛰어져 줄이 준다), (b) 룩 경계에서 인접한 두 `ClearAll`을 1회로 접는가(접기 여부는 M2의 형상 결정이며 `ClearAll`은 dedupe 면제 집합에 있어 접지 않아도 손실이 없다 — `server/orchestrator/tools.py:229`). **per-family 열은 도달 불가 경로의 참고 수치다** — REQ-BUSKWIZ-006이 캡처 형상을 `shared_capture`로 고정하고 모델 인자에서 뺐기 때문이며(spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정), REQ-BUSKWIZ-020), 근거는 값 라인의 dedupe 탈락이다(plan-phase 재계수로 교차 확인: **v1 형상은 4장르 전부 값 라인 중복 0건**, per-family는 edm `Attribute 'Dimmer' At 100` ×2 · rock `Attribute 'Iris' At 100` ×2 → 두 번째가 탈락하면 빈 프로그래머에 `Store`가 걸린다). **회귀 경고 — per-family가 툴 인자로 되살아나면 그 순간 135줄이 미측정 경로가 되고 값 라인 탈락도 함께 돌아온다.** **spec.md는 SSOT이므로 본 계획이 수정하지 않는다.**

**위 표로 돌아가면** 정확한 논거는 **"기술적 순서 제약 0건 + 정책 게이트 1건 + 의도적 배칭"**이다.

- **정책 게이트의 정본은 acceptance.md다** — `AC-BUSKWIZ-016`의 기대 결과가 "**4건 전부 판정 확정** · **판정 미확정으로 M1을 착수하지 않는다**"이며, 그 사유를 스스로 적고 있다: ASSUMPTION-18 미확정이면 번들 규모 정책이 미정이고, ASSUMPTION-16 · ASSUMPTION-17 · ASSUMPTION-19 미확정이면 REQ-BUSKWIZ-016의 발동 여부가 미정이다(`AC-BUSKWIZ-016 기대 결과`). 본 계획은 그 게이트를 그대로 집행한다.
- **정책 게이트가 정당한 이유(비용 비대칭)**: M0는 **코드 변경 0**의 측정 세션이다. 반면 M2에서 ASSUMPTION-18이 부정으로 드러나면 이미 작성된 번들 결합 계층과 툴 계약이 함께 되돌아가고, M5에서 ASSUMPTION-16 · ASSUMPTION-17 · ASSUMPTION-19 중 하나라도 부정으로 드러나면 익스큐터 코드가 통째로 폐기된다. **되돌림 비용이 큰 쪽을 뒤에 두고 측정을 앞에 둔다** — 측정을 미루어 아끼는 것은 없다(세션 수는 어차피 2회다).
- **배칭 근거**: 라이브 세션 1회의 실제 비용은 실물 콘솔·쇼파일 준비와 사람의 일정 확보이지 프로브 항목 하나를 더 발화하는 한계 비용이 아니다. **네 항목**의 진짜 차단 대상이 M2와 M5로 갈리더라도 세션을 둘로 쪼갤 이유가 없다.

M0는 `SPEC-COPILOT-EXECBODY-001`의 GO/DESCOPE 라이브 프로브 패턴(`SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123` AC-EXECBODY-010)을 계승하며, LOOKLIB이 빔 축에 같은 패턴을 적용한 선례(`SPEC-COPILOT-LOOKLIB-001/spec.md:45`)를 따른다.

### §A.3 정직한 축소 원칙

본 SPEC은 **네 방향의 축소**를 전부 정상 결과로 정의한다. 축소가 발동해도 SPEC 실패가 아니며, 축소를 성공으로 위장하는 것만이 실패다.

1. **익스큐터 축의 DESCOPE** — ASSUMPTION-16 · ASSUMPTION-17 · ASSUMPTION-19 중 하나라도 부정이면 v1은 익스큐터·페이지 대상 커맨드를 **0건** 발화하고 사유를 progress.md에 기록한다(REQ-BUSKWIZ-016, `acceptance.md §A DESCOPE는 실패가 아니다`). `AC-BUSKWIZ-013`의 정적 스캔이 그 0건을 기계적으로 고정한다. **우회는 금지다** — M0가 프리셋을 직접 얹는 문법을 찾지 못하면 답은 DESCOPE이지 "그럼 시퀀스를 만들자"가 아니다(spec.md REQ-BUSKWIZ-016 하위 절(우회 금지); 시퀀스 생성은 §D 범위 밖이므로 우회가 곧 범위 누출이다).
2. **점유 미관측 = 저장 안 함** — `binding.occupied is None`인 풀은 `no_free_slot`으로 전량 건너뛴다(REQ-BUSKWIZ-009). 미관측을 빈 풀로 취급하는 것이 바로 "사람이 만든 프리셋 위에 쓰기"의 경로다(`server/looks/instantiate.py:82-85`). 슬롯 원장은 **관측된 점유에 본 번들이 만들 점유를 더하는 장치**이지 관측을 대체하는 장치가 아니다(spec.md REQ-BUSKWIZ-005 하위 절(원장은 관측을 대체하지 않는다)).
3. **부분 성공은 부분 성공** — 저장 가능한 것만 저장하고 나머지를 건너뛴다. 전량 실패로 되돌리지도, 전체 성공으로 위장하지도 않는다(REQ-BUSKWIZ-010, `acceptance.md §A 부분 성공 원칙`). **트리거는 "슬롯 부족"이 아니다**(v0.1.3 감사 D2) — 도달 가능한 **둘**은 (i) 특정 풀만 미해석·미주소라 그 풀 대상 저장만 전량 건너뜀, (ii) 같은 이름의 프리셋이 이미 있어 `conflict`로 건너뜀(연속 2회 실행이 그 경우다). 점유 미관측(`no_free_slot`)은 REQ-BUSKWIZ-009가 따로 덮는다. **"룩마다 값을 가진 패밀리 수가 다름"은 v0.1.4에서 열거에서 빠졌다**(재감사 D2) — 값 없는 패밀리는 `if not values: continue`로 넘어가 `SkippedStore`를 만들지 않으므로(`server/looks/instantiate.py:332-334`) 그 룩은 `skipped=0 complete=True`인 **완전 성공**이다. 자세한 근거는 spec.md REQ-BUSKWIZ-010 하위 절(트리거의 실측).
4. **장르 미해석 = 정직한 실패** — 가장 비슷한 장르로 임의 승격하지 않고 후보 목록과 함께 실패를 반환한다(REQ-BUSKWIZ-002, `AC-BUSKWIZ-002` ②).

실패 방향은 항상 **축소 또는 보류**이며 추측 보완이 아니다. 이는 `server/looks/resolver.py:113-119`의 `@MX:WARN`("nothing here may fabricate a number or a name")과 `server/looks/instantiate.py:291-299`의 `@MX:WARN`이 이미 코드에 새겨 둔 규율의 계승이다.

### §A.4 결정 현황 — **해소 7건 / 미해결 0건**

> **미해결 마커는 처음부터 남기지 않는다.** 본 SPEC은 착수 시점에 7건 전부가 폐쇄된 상태로 시작한다 — **사용자 사전 확정 4건**(A·B·C·D, spec.md §A 사전 확정 사실 "사전 확정 사실 — 재질의 금지")과 **엔지니어링 판단 3건**(E·F·G, 근거는 아래 §A.4a-E / §A.4a-F / §A.4a-G). 따라서 clarification 마커는 이 문서에 **0건**이며, 미해결 결정 절(§A.4b)은 존재하지 않는다.
>
> **다른 아티팩트와의 대응 관계.** §A.4a의 결정 7건(A~G)이 **정본**이며, design.md의 결정 반영 절은 이 7건을 소비한다 — 양쪽 모두 **열린 슬롯 0건**이고, 어느 쪽도 새 결정 문자를 만들지 않는다. §F 결정 기록은 같은 7건을 "반영 위치" 축으로 다시 세운 것이지 별개 집합이 아니다.

#### §A.4a 해소된 결정 (재질의 금지 — 근거 포함)

| # | 결정 | 확정 내용 | 근거 |
|---|---|---|---|
| **A** | **익스큐터 페이지 레이아웃** | **M0 라이브 프로브 GO/DESCOPE 게이트**(ASSUMPTION-16 ∧ ASSUMPTION-17 ∧ **ASSUMPTION-19** — v0.1.2에서 3항 논리곱). 셋 다 긍정일 때만 REQ-BUSKWIZ-016이 발동하고, 하나라도 부정이면 v1은 익스큐터·페이지 커맨드 **0건** | **사용자 확정 ①**(spec.md §A 사전 확정 사실(익스큐터 게이트)). 리포지토리 근거가 **0건**임이 실측으로 확인되었다 — 페이지 커맨드의 유일 등장처 `server/measurement/corpus.yaml`은 스스로 "the deterministic offline action for M6a mock runs **ONLY**"이고 라인은 "structurally valid"할 뿐이라고 한정한다(`:7-10`). 게다가 `Label Page 3 "Ballad"`(`:99`)는 큰따옴표를 써서 그대로 발화하면 깨진다(`00_grammar.md:26-29`). 룰북 `v2.4.2/` 전체에서 `Store Page`/`Label Page`/`Label Executor`/빈 익스큐터 열거는 **0건**이다. **ASSUMPTION-19의 실측도 0건**(plan-phase 재확인): `Assign Preset` · `Preset <p>.<s> At (Executor\|Page) <n>` · `Store Executor` 계열이 `server/`·`console/`·`docs/` 전체에서 검색 결과 없음 |
| **B** | **팔레트 축** | LOOKLIB `IN_SCOPE_POOL_FAMILIES` **4종 그대로 상속** — Dimmer · Color · Beam · Focus. 재정의하지 않고 import한다. **포지션 축은 v1에 존재하지 않는다** | **사용자 확정 ②**(spec.md §A 사전 확정 사실(팔레트 축)). 실체는 `server/looks/schema.py:58`이며 attribute→패밀리 매핑도 이미 출하되어 있다(`:62-69`). 빔 축은 LOOKLIB M0가 `Zoom`/`Iris`를 GO 판정해 실값이 출하되었다(`server/looks/schema.py:50` `PROBE_GATED_ATTRIBUTES`). 포지션은 선행 SPEC이 닫았다 — `Pan`/`Tilt`는 어떤 풀에도 귀속되지 않는다(`server/looks/schema.py:47`, `:62-69` 매핑에 부재) |
| **C** | **실행 단위** | **단일 번들 · 승인 1회 · 부분 성공 구조화 보고**. 룩 단위 분할 승인(6~10회 왕복)과 dry-run 선보고는 **기각**. 건너뜀의 단위는 **프리셋 저장 1회**이지 룩이 아니다 | **사용자 확정 ③**(spec.md §A 사전 확정 사실(실행 단위)). 마법사의 가치가 "한 마디에 일괄"이므로 분할 승인은 기능 자체를 무력화한다. 긴 프리뷰를 사람이 실질 검토하기 어렵다는 반대 논거는 사용자에게 제시된 뒤 **수용된 위험**으로 존치하며(spec.md §A 수용된 잔여 위험), 완화는 REQ-BUSKWIZ-013의 2단 보고가 담당한다. **실측으로 그 위험은 제시 시점보다 크다** — 프리뷰 길이는 40여 줄이 아니라 **51~87줄**(상한 edm·4풀 87)이다(§A.2 계수 각주, spec.md v0.1.1과 동일 표기). 위험의 방향과 완화 수단은 그대로이므로 결정을 재질의하지 않고 design.md 위험 절에 실측치를 싣는다. 건너뜀 단위는 `SPEC-COPILOT-LOOKLIB-001/spec.md:65` 결정 I의 계승 |
| **D** | **라이브 세션** | **2회** — M0 프로브 + M7 종단. 프로젝트 관례("라이브 마일스톤 1개")로부터의 의식적 이탈 | **사용자 확정 ④**(spec.md §A 사전 확정 사실(라이브 세션 2회)). LOOKLIB의 세션 회계(`SPEC-COPILOT-LOOKLIB-001/plan.md:205-214`)를 그대로 따른다. 두 세션은 시간축의 양 끝(저작 전 측정 / 통합 후 종단)에 있어 물리적으로 병합 불가능하다(§B 라이브 세션 회계) |
| **E** | **슬롯 원장** | 풀 패밀리별 **누적 원장**으로 다중 룩 재청구를 **0건**화 — **슬롯과 라벨을 함께 누적한다**(spec.md REQ-BUSKWIZ-005 하위 절(원장은 슬롯과 함께 라벨도 누적한다)). 원장의 시작값은 **콘솔이 관측 보고한 점유**이며, 미관측 풀을 비었다고 가정하는 장치가 아니다 | **엔지니어링 판단** — 아래 §A.4a-E. 대상 결함: spec.md §A 하드 결함 1 |
| **F** | **dedupe 처리** | **`tools.py` dedupe 규칙 무개정.** 장르 번들이 `ChangeDestination Root`를 **선두 1회만** 발화하는 형상으로 회피한다. 룩별 번들의 단순 연접은 금지 | **엔지니어링 판단** — 아래 §A.4a-F. 근거는 LOOKLIB M7 **라이브 관측**(`SPEC-COPILOT-LOOKLIB-001/progress.md:799-805`, `:1167-1170`) |
| **G** | **장르 룩 조회** | **`LookLibrary` 직접 순회.** `match_looks` 툴 경로는 쓰지 않는다 | **엔지니어링 판단** — 아래 §A.4a-G. `MAX_TOOL_MATCHES = 8`(`server/looks/matching.py:71`)에서 EDM 9룩이 1건 잘린다 |

##### §A.4a-E — 슬롯 원장이 사용자 질의 대상이 아닌 이유 (하드 결함 1의 해소)

**왜 이것이 결정이어야 했는가.** 선행 구현은 룩 1개 단위로만 호출되었고, 그 호출마다 리그를 다시 읽었다(`server/orchestrator/tools.py:739-744`). 그 구조가 결함을 가려 왔다. 다중 룩을 하나의 번들로 묶는 순간 결함이 즉시 발현하므로, **원장은 선택지가 아니라 전제**다.

**결함의 기계적 형태 (실측).**

- `PoolBinding`과 `PoolIndex`가 둘 다 `@dataclass(frozen=True)`이다(`server/looks/instantiate.py:78-79`, `:96-97`) — 청구된 슬롯을 되돌려 쓸 자리가 **구조적으로 없다**.
- `_first_free_slot(occupied)`(`:307-312`)은 인자로 받은 점유 집합에서 1부터 오름차순 첫 미점유를 고를 뿐이며, 어디에도 쓰기·전진이 없다.
- `_plan_stores`는 `binding.occupied`를 **읽기만** 한다(`:346`, `:358`).
- 따라서 **하나의 `PoolIndex`로 N개 룩을 `build_instantiation`(`:416-423`) 하면 N개 전부가 같은 슬롯을 겨냥한다.**
- 라벨 충돌 검사(`:359-361`)는 **이미 콘솔에 있는 라벨**만 보므로, 이번 번들이 방금 청구한 슬롯은 시야 밖이다. 룩마다 라벨이 다르니 `CONFLICT`에도 걸리지 않는다. 결과는 **같은 슬롯에 N번 `Store`** — 정확히 이 프로젝트가 막으려 한 "사람이 만든 프리셋 위에 쓰기"의 자기 재현이다.

**결정.**

1. 번들 결합 계층이 **풀 패밀리별 원장**을 유지한다 — 슬롯 집합(`set[int]`)과 **라벨 집합**을 함께 담는다. 시작값은 `binding.occupied` / `binding.labels`이며, 룩마다 청구한 슬롯과 라벨이 누적된다. **라벨 누적이 필요한 이유**(spec.md REQ-BUSKWIZ-005 하위 절(원장은 슬롯과 함께 라벨도 누적한다)): `_plan_stores`의 충돌 검사는 **콘솔에 이미 있는 라벨만** 본다(`server/looks/instantiate.py:359-361`). 같은 번들이 만들어 낼 라벨끼리는 비교 대상이 아니므로, 표시 이름이 같은 두 룩이 한 장르에 있으면 서로를 모른 채 각자 저장된다. 현행 32룩은 `display_name` 중복 0건이라 지금 깨져 있지는 않으나 **막는 기제가 없다** — 원장이 이번 번들의 라벨에도 동일 판정(대소문자·공백 무시 일치 = 건너뛰기)을 적용한다.
2. 원장은 `PoolBinding`을 **감싸는 계층**이지 개정하지 않는다 — frozen 데이터클래스는 PRESERVE이고(§A.5), 원장은 본 SPEC의 신규 모듈이 소유한다. 이것이 LOOKLIB이 예약한 "API 형상"이 실제로 성립하는 방식이다: `build_instantiation`이 해석 결과를 키워드 전용 파라미터로 받는 형상(`:416-423`)이 외부 원장의 주입을 문법적으로 허용한다.
3. **원장은 관측을 대체하지 않는다.** `binding.occupied is None`이면 원장이 있든 없든 `no_free_slot`이다(REQ-BUSKWIZ-009). `occupied=()`(검증된 빈 풀)와 `occupied=None`(미관측)이 **서로 다른 결과**를 내는 것을 별도 테스트로 고정한다(`AC-BUSKWIZ-007`).
4. **부분 성공은 원장 소진이 아니다**(v0.1.3 감사 D2). **원장이 소진되는 시나리오는 v1에 존재하지 않는다** — `_first_free_slot`(`server/looks/instantiate.py:307-312`)은 상한 없이 증가하고, 풀 용량 상수가 리포지토리 0건이며(`max_slot`/`pool_size`/`POOL_CAPACITY` 계열), `_observed_contents`(`:195-215`)는 점유 자식만 반환할 뿐 풀 크기를 보고하지 않아 런타임에도 상한을 알 방법이 없다. 상한을 발명해 테스트하는 것은 REQ-BUSKWIZ-008이 금지한 per-show 값의 정적 진입이다. 따라서 원장은 **재청구를 막는 장치**일 뿐이고, REQ-BUSKWIZ-010의 부분 성공은 §A.3 3항의 세 경로에서 온다.
5. **패밀리는 서로 독립이다.** Dimmer 원장과 Color 원장은 영향을 주지 않는다(`AC-BUSKWIZ-004` 구간 4) — `_plan_stores`가 이미 `IN_SCOPE_POOL_FAMILIES`를 패밀리 단위로 순회하는 구조(`:331-335`)와 정합한다.

**남은 사용자 대면 여지 — 없음.** 대안(리그를 룩마다 다시 읽기)은 사용자 확정 ③의 단일 번들과 REQ-BUSKWIZ-004의 1회 해석을 동시에 위반한다. 다른 대안(슬롯을 고정 대역으로 예약)은 LOOKLIB 결정 B가 이미 기각한 "검증되지 않은 관례의 하드코딩"이다. 판단 근거가 전부 SPEC 내부에 있어 사용자가 SPEC보다 더 잘 답할 수 없다.

##### §A.4a-F — dedupe를 개정하지 않고 번들 형상으로 회피하는 이유 (하드 결함 2)

**결함의 기계적 형태 (실측).** `_PROGRAMMER_STATE_COMMANDS` 면제 집합은 `Clear` / `ClearAll` / 맨-형태 `Fixture|Group` 선택 **3종뿐**이며(`server/orchestrator/tools.py:227-231`), `_is_programmer_state`는 그 3종에 대한 `fullmatch`다(`:234-237`). `ChangeDestination Root`는 어디에도 걸리지 않는다. 그리고 dedupe는 `context.executed_ok`를 시드로 삼아 **번들 내에서도 누적**한다(`:526`, `:537`, 주석 `:519-525`가 그 의도를 명시). 따라서 룩별 번들을 단순 연접하면 2..N번째의 `ChangeDestination Root`가 `skipped_already_executed`로 탈락하고, **계획한 문자열과 콘솔이 실제로 받은 것이 어긋난다**.

**세 갈래 대응과 선택.**

| 대응 | 판정 | 근거 |
|---|---|---|
| 면제 집합에 `ChangeDestination`을 추가 | **기각** | `server/orchestrator/tools.py`의 dedupe 블록은 `run_commands`를 쓰는 **모든** 소비자가 공유한다. 본 SPEC 하나를 위해 전역 실행 의미론을 바꾸는 것은 변경 표면과 파급이 어긋난다. LOOKLIB이 "dedupe 규칙 개정 여부는 M4가 단독으로 정하지 않는다"고 판단을 넘긴 이유가 이것이다(`SPEC-COPILOT-LOOKLIB-001/progress.md:1330`) |
| 룩마다 별도 `run_commands` 호출로 분리 | **기각** | 사용자 확정 ③(단일 번들 · 승인 1회)과 정면 충돌한다 |
| **번들 형상 쪽에서 회피 — 선두 1회만 발화** | **채택** | 아래 |

**채택 근거는 라이브 관측이다.** LOOKLIB M7 세션이 이 탈락을 **실물에서 관측**했고, `skipped_already_executed`는 정확히 1건, 그것이 `ChangeDestination Root`였다(`SPEC-COPILOT-LOOKLIB-001/progress.md:799-805`). **그럼에도 그 세션의 두 번째 번들은 정상 왕복했다**(`:1167-1170`) — 목적지 상태가 세션에 남아 있기 때문이다. 즉 `ChangeDestination Root`의 반복은 **의미상 멱등**이며, 그것을 한 번만 보내는 것은 기능 손실이 아니다. 반대로 두 번 보내려는 시도만이 "보냈다고 적었는데 안 갔다"를 만든다.

**결정의 기계적 형태(REQ-BUSKWIZ-006).** 장르 번들은 `ChangeDestination Root`(`server/looks/instantiate.py:70`)를 **선두에 정확히 1회** 포함하고, 그 뒤로 룩 단위 캡처 사이클이 `ClearAll`(`:71`) 규율을 유지한 채 이어진다(`31_choreography_patterns.md:9-23`, `:40-41`). `ClearAll`은 면제 집합에 있으므로(`tools.py:229`) 반복해도 탈락하지 않는다 — **이 형상은 dedupe를 통과하면서 한 줄도 잃지 않는다**. 유닛에서 `AC-BUSKWIZ-005` ④(목 실행 포트로 `skipped_already_executed` 0건)가, 라이브에서 `AC-BUSKWIZ-017` ②가 같은 사실을 두 층위로 고정한다.

##### §A.4a-G — 장르 조회가 `match_looks` 툴 경로를 타지 않는 이유

**실측.** `MAX_TOOL_MATCHES = 8`(`server/looks/matching.py:71`)은 툴 결과 1건이 나르는 매치 수의 상한이고, 그 곁에 `truncated` 신호가 함께 실린다(주석 `:68-70`). 라이브러리 실측 장르별 룩 수는 worship 8 / rock 8 / ballad 7 / **edm 9**이므로(REQ-BUSKWIZ-001), **EDM만 1건이 잘린다.**

**왜 상한을 올리지 않는가.** (a) `MAX_TOOL_MATCHES`는 LOOKLIB의 매칭 표면 계약이며 그 SPEC의 AC가 `truncated` 규율을 고정하고 있다 — 본 SPEC의 편의를 위해 남의 계약을 바꾸는 것은 PRESERVE 정신의 위반이다. (b) 상한을 올려도 **다음 장르가 9룩을 넘으면 같은 문제가 재발**한다 — 상한은 조회 계층이 아니라 **툴 응답 크기**를 위한 것이고, 장르 전량 조회는 애초에 상한이 있어서는 안 되는 연산이다. (c) 잘린 목록을 완전한 목록으로 제시하지 않는 규율은 이 프로젝트의 반복 규율(`drilldown_capped`, `truncated`)이며, 본 SPEC은 그 규율을 우회하는 것이 아니라 **상한이 없는 경로를 쓰는 것**으로 만족시킨다.

**결정.** 장르 조회는 이미 로드된 `LookLibrary`(`server/looks/schema.py:119-130`)의 `looks` 튜플에 대한 **읽기 전용 순회**로 구현하고, 정렬은 다이내믹스 오름차순 → 동률 시 `look_id` 사전순의 **결정론적 전순서**다(REQ-BUSKWIZ-001). 장르 별칭 해석은 **본 SPEC이 표를 새로 만들지 않고** 기존 `GENRE_ALIASES`(`server/looks/matching.py:73-90`)와 `resolve_genre`(`:197`)를 그대로 호출한다 — 중복 정의 0건을 **AST 스캔**으로 확인한다(`AC-BUSKWIZ-002` ③, v0.1.3에서 import 스캔을 대체: 텍스트·import 목록 스캔은 별칭 표를 코드 안에 다시 적은 경우를 잡지 못한다).

#### §A.4b — 삭제됨 (미해결 결정 0건)

본 SPEC은 착수 시점에 결정 7건이 전부 폐쇄된 상태로 시작하므로 미해결 결정 절을 두지 않는다. **이 문서에 clarification 마커는 0건이며**, design.md 쪽의 열린 슬롯도 0건이다.

### §A.5 PRESERVE 목록 (무변경 대상)

정본은 spec.md §A PRESERVE이며, spec.md §D의 "Out of Scope — `run_commands` dedupe 규칙 개정" 절이 `tools.py` 경계를 함께 못 박는다. 아래는 그 목록의 계획 관점 재기술이며, **`git diff <BASE>..HEAD`가 빈 출력이어야 하는 대상**이다(`AC-BUSKWIZ-014`).

- **룩 계층의 기반** — `server/looks/schema.py` · `loader.py` · `roles.py` · `resolver.py` · `library/*.yaml`. 룩 스키마는 P1-1/P1-2 공통 기반이라 파괴 변경이 소비자 둘을 함께 깨뜨린다(`server/looks/schema.py:20-25` `@MX:NOTE`). 본 SPEC은 그 스키마의 **소비자**이지 개정자가 아니다.
- **안전·표현 계층** — `server/safety/**`(게이트·분류·블랙리스트·LiveLock), `server/web/preview.py`.
- **콘솔측** — `console/lua/copilot_responder.lua` 무변경. 인스턴스화는 이미 검증된 커맨드라인 패턴만 쓴다.
- **룰북 자산** — `server/rulebook/assets/v2.4.2/**` 전체. 본 SPEC은 룰북에 안내 축을 추가하지 않는다(장르 어휘는 이미 `matching.py`에 있다).
- **`server/orchestrator/tools.py`의 두 블록** — `_PROGRAMMER_STATE_COMMANDS`(`:227-231`)와 dedupe 블록(`:526-550`). **본 SPEC의 `tools.py` 변경은 신규 툴 1종의 등록으로 한정된다**(REQ-BUSKWIZ-019). 등록이 닿는 자리는 `TOOL_NAMES`(`:40-47`) · `build_toolset` 내부 핸들러 클로저 · `definitions` 튜플(`:808` 이하) · `handlers` 사전(`:1052-1059`) 넷뿐이다.
- **`server/looks/instantiate.py`** — **v0.1.3에서 PRESERVE 정식 등재**(감사 D4). 결정 E는 "frozen 자료구조를 **바깥에서 감싼다**"는 형상이고, 감싸지 못해 `PoolIndex`/`PoolBinding`/`_plan_stores`를 고치게 되는 경우가 곧 **결정 E의 반증**이다. 이 파일이 목록에 있으면 그 반증이 **diff로 즉시 드러난다** — 없으면 조용히 개정하고 지나갈 수 있고, 그 개정은 단일 룩 경로(`instantiate_look`)와 P1-1 소비자까지 함께 흔든다. v0.1.2까지 본 계획이 "M2의 자기 규율"로 두었던 것을 SSOT가 기계 게이트로 올렸다.

## §B. 마일스톤 (M0..M7)

> **AC 배정의 정본은 `acceptance.md` §C.0**이다. 아래 각 마일스톤의 `- **AC**:` 줄은 그 배정표와 **1:1**이며, 17개 AC가 정확히 한 번씩 나타난다(001~017, 중복·누락 0). 한쪽을 고치면 다른 쪽도 고친다.

### M0 — 라이브 프로브 (실물 onPC, ASSUMPTION-16/17/18/19) — **M1의 게이트**

**EXECBODY-001 M1 GO/DESCOPE 패턴 계승**(`SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123`). **코드 변경 0** — 측정 세션이다.

각 항목의 **진짜 차단 대상은 서로 다르며 M1을 기술적으로 막는 항목은 0건이다**(§A.2 표). 그 사실은 프로브 순서를 바꾸지 않지만(정책 게이트는 `AC-BUSKWIZ-016 기대 결과`이 정본), M0 접근 불가 시의 대응(§C.7)이 항목별로 달라지는 근거가 된다.

- **ASSUMPTION-16 (페이지·익스큐터 저작 문법) — 차단: M5**: 페이지 생성/라벨, 익스큐터 라벨링 커맨드가 2.4.2에서 수용되는지 실측한다. **측정 대상은 콘솔이 실제로 받아들이는 문자열을 찾는 것**이지 `server/measurement/corpus.yaml`의 mock 문자열을 확인하는 것이 아니다 — 그 파일은 스스로 mock 전용임을 자인하고(`:7-10`), 그 안의 `Label Page 3 "Ballad"`(`:99`)는 큰따옴표 때문에 그대로 발화하면 깨진다(`00_grammar.md:26-29`). 판정: GO / DESCOPE.
- **ASSUMPTION-17 (빈 익스큐터 열거·판별) — 차단: M5**: 현재 페이지 드릴다운은 **이미 존재하는 자식만** 열거하고(`server/web/dash.py:200-206`), 확인 실패한 후보는 "없음"과 "미확인"이 구별되지 않는다. 실물에서 미할당 익스큐터를 판별할 수 있는지 관측한다. 판정: GO / DESCOPE.
  - **REQ-BUSKWIZ-016은 세 판정의 논리곱이다**(v0.1.2) — ASSUMPTION-16 ∧ ASSUMPTION-17 ∧ ASSUMPTION-19 중 하나라도 DESCOPE면 M5는 DESCOPE 분기로 확정되고, v1은 익스큐터·페이지 커맨드를 0건 발화한다. **DESCOPE는 실패가 아니라 정의된 결과다**(spec.md REQ-BUSKWIZ-016 하위 절(하나라도 부정이면 DESCOPE)).
- **ASSUMPTION-19 (팔레트를 익스큐터에 얹는 문법) — 차단: M5**: **얹을 대상이 있는가를 묻는 항목이다.** 라이브 검증된 유일한 바인딩 커맨드 `Assign Sequence <n> At Executor <m>`(`31_choreography_patterns.md:99`)의 **목적어는 시퀀스**인데 본 SPEC의 산출물은 **프리셋**이고 시퀀스 생성은 §D 범위 밖이다 — 즉 ASSUMPTION-16·ASSUMPTION-17이 둘 다 GO여도 이 항목이 부정이면 레이아웃은 성립할 수 없다(spec.md REQ-BUSKWIZ-016 하위 절(ASSUMPTION-19가 게이트에 추가된 이유)). 리포지토리 실측은 **0건**이다(plan-phase 재확인: `Assign Preset` · `Preset <p>.<s> At (Executor|Page) <n>` · `Store Executor` 계열이 `server/`·`console/`·`docs/`에서 검색 결과 없음). 측정은 **프리셋을 익스큐터에 직접 배치하는 커맨드 문자열을 실물에서 찾는 것**이다. 판정: GO / DESCOPE.
  - **우회 금지 — 못 찾으면 답은 DESCOPE다**(spec.md REQ-BUSKWIZ-016 하위 절(우회 금지)): "그럼 시퀀스를 만들어서 얹자"는 §D의 시퀀스·큐 생성 제외를 깨뜨리고 범위 누출을 만든다. M0는 **없다는 사실을 확정하는 것**으로 자기 임무를 다한다.
  - **`Assign Sequence <n> At Executor <m>`는 발화 형식이 아니라 결함의 증거다** — 이것이 라이브 검증된 유일한 바인딩 커맨드이고(`31_choreography_patterns.md:99`, `:168`; 파일 헤더 `:7`이 라이브 검증을 선언하는 유일한 룰북 파일이다) 안전 게이트도 `safe`로 분류하지만(`server/tests/test_safety_classify.py:152`), **목적어가 시퀀스라 프리셋 산출물에는 쓸 수 없다.** GO 시 발화할 형식은 **M0가 실측해 찾아낸 것 하나뿐**이며, 못 찾으면 위 우회 금지가 적용된다.
- **ASSUMPTION-18 (단일 번들의 1왕복) — 차단: M2**: 장르 1개가 한 번의 `run_commands` 왕복에서 절단·타임아웃 없이 왕복하는지 실측한다. **측정은 v1 형상의 실제 상한에서 한다 — 87줄(edm · 4풀)**(§A.2 계수 각주; LOOKLIB 라이브 실측 최대 21줄의 **약 4.1배**다). 40여 줄에서의 통과는 GO 근거가 되지 못하며, 통과·실패 어느 쪽이든 **실제로 몇 줄을 보냈는지**를 progress.md에 수치로 남긴다. **per-family 형상(135줄)은 측정 대상이 아니다** — REQ-BUSKWIZ-006이 캡처 형상을 `shared_capture`로 고정했으므로 장르 경로에서 도달 불가다(spec.md REQ-BUSKWIZ-006 하위 절(캡처 형상 고정)).
  - **함께 측정할 것 — 중도 실패의 사후 상태**: `run_commands`는 **stop-on-first-failure**다(`server/orchestrator/tools.py:527-536`, `:562`) — 한 줄이 실패하면 그 뒤 전량이 `not_executed`가 된다. 상한 규모 번들(87줄)에서 이 성질이 실제로 어떻게 관측되는지(어느 지점에서 끊기는지, 프로그래머 상태가 어떻게 남는지)를 함께 기록한다. 이는 REQ-BUSKWIZ-010의 부분 성공과 **다른 종류의 부분 상태**이며(§C.9), 보고가 둘을 섞으면 안 된다.
  - **부정 판정의 처리**: **번들 분할 정책이 필요해지고 그것은 사용자 확정 ③과 충돌하므로, SPEC이 임의로 분할하지 않고 M0 게이트에 사용자 결정 항목으로 기록한다**(ASSUMPTION-18, §G 조건부 접점).
- **정리 기록과 Gaps**: 프로브가 쇼파일에 남긴 것과 그 무해성, 그리고 **측정하지 못한 것**을 명시적으로 남긴다(`AC-BUSKWIZ-016` 측정 항목 4·5).
- 파일: **신규·수정 0**. 산출물은 `progress.md` §E.2 M0 절의 판정 3건 + 실측 원문(콘솔 응답·감사 로그·GUI 스크린샷)이며, 각주가 아니라 명시적 섹션으로 기록한다.
- **AC**: AC-BUSKWIZ-016 (LIVE — 2건 중 1번째).

### M1 — 장르 조회 계층 (cycle_type=tdd)

- **결정 G**를 구현: 장르 식별자 → 그 장르의 룩 **전량**을, **다이내믹스 오름차순 → 동률 시 `look_id` 사전순**의 결정론적 전순서로 반환(REQ-BUSKWIZ-001). 입력은 이미 로드된 `LookLibrary`(`server/looks/schema.py:119-130`)이며 **읽기 전용 순회**다(REQ-BUSKWIZ-003).
- **절단 경로를 타지 않음을 구조로 보장**: `MAX_TOOL_MATCHES`(`server/looks/matching.py:71`)를 참조하는 코드가 조회 계층에 **0건**이고, 반환 형상에 `truncated` 필드가 **존재하지 않는다**(있다면 그 자체가 절단 경로를 탄 증거다). EDM 9룩이 9건 그대로 나오는 한 케이스가 이를 증명한다(`AC-BUSKWIZ-001` ①②).
- **별칭 해석은 재사용이지 재정의가 아니다**(REQ-BUSKWIZ-002): 기존 `GENRE_ALIASES`(`server/looks/matching.py:73-90`)와 `resolve_genre`(`:197`)를 호출한다. 한국어 표현(워십·예배·찬양 / 록·락 / 발라드 / 이디엠)과 영어 슬러그가 같은 장르로 접힘을 assert하고, **미해석 입력은 후보 목록과 함께 실패**시킨다 — 가장 비슷한 장르로 승격하지 않는다(반환 장르 필드가 `None`).
- **콘솔 무접촉**: 이 마일스톤은 리그·게이트·실행 포트 어느 것도 건드리지 않는다. 인메모리 픽스처만으로 전량 검증된다.
- 파일: `server/looks/busking.py`(**신규** — 장르 조회 절), `server/tests/test_busking_genre.py`(**신규**).
- **AC**: AC-BUSKWIZ-001, AC-BUSKWIZ-002.

### M2 — 슬롯 원장 + 다중 룩 번들 빌더 (cycle_type=tdd)

**본 SPEC의 핵심 마일스톤이며 하드 결함 2건이 여기서 해소·회피된다.**

- **리그 1회 해석**(REQ-BUSKWIZ-004): `resolve_roles`(`server/looks/resolver.py:121`)와 `resolve_pools`(`server/looks/instantiate.py:217`)를 **각각 정확히 1회** 호출하고 그 결과를 집합의 모든 룩에 재사용한다. 룩 수에 비례하는 호출은 실패로 판정한다 — 호출 카운팅 스파이로 기계 고정(`AC-BUSKWIZ-003`).
- **슬롯 원장**(결정 E, REQ-BUSKWIZ-005): 풀 패밀리별 누적 원장. 시작값 = `binding.occupied`, 룩마다 청구분 누적. `PoolBinding`/`PoolIndex`(`server/looks/instantiate.py:78-79`, `:96-97`)는 frozen인 채로 두고 **바깥에서 감싼다**(§A.5 마지막 항목의 자기 규율).
- **회귀 고정을 함께 작성한다**(`AC-BUSKWIZ-004` 구간 2): 같은 입력을 `build_instantiation`에 룩마다 동일 `PoolIndex`로 직접 N회 호출하면 **전부 같은 슬롯**이 나옴을 별도로 assert한다. 결함이 실재함과 본 계층이 그것을 감쌌음을 **한 파일에서 함께** 고정한다 — 이 테스트가 사라지면 원장의 존재 이유가 문서에만 남는다.
- **번들 형상**(결정 F, REQ-BUSKWIZ-006): `ChangeDestination Root`(`server/looks/instantiate.py:70`) **선두 정확히 1회** + 룩 단위 `ClearAll`(`:71`) 규율. **룩별 번들의 단순 연접은 금지**하고, 룩 2개 번들에서 목적지 커맨드가 2회 나타나면 실패로 판정한다. dedupe 무손실은 목 실행 포트로 확인한다(`skipped_already_executed` 0건 — `AC-BUSKWIZ-005` ④).
- **파괴적 저장 0건**(REQ-BUSKWIZ-007): `Store /Overwrite` 발화 0건(**대소문자 무관** assert — 런타임 매칭이 이미 대소문자 무관이므로 대소문자를 고정한 assert는 위양성을 만든다), 라벨 충돌 시 재슬롯 금지 — 충돌 처리는 **건너뛰기 하나**다(`server/looks/instantiate.py:359-371`, `server/safety/blacklist.yaml:18`). 라벨 충돌 판정은 **원장이 이번 번들에서 청구한 라벨까지** 포함한다(spec.md REQ-BUSKWIZ-005 하위 절, `AC-BUSKWIZ-004` 구간 6) — `_plan_stores`는 콘솔 기존 라벨만 보기 때문이다.
- **미관측 ≠ 빈 풀**(REQ-BUSKWIZ-009): `occupied is None`인 풀은 `no_free_slot`으로 전량 건너뛰고 풀 번호와 사유를 남긴다(`server/looks/instantiate.py:82-85`, `:346-357`). `occupied=()`와 `occupied=None`이 **서로 다른 결과**를 냄을 별도 테스트로 고정한다.
- **부분 성공**(REQ-BUSKWIZ-010): 저장 가능한 것만 저장하고 나머지는 건너뛴 것으로 보고한다. 전량 실패로 되돌리지 않는다. **트리거는 두 경로다**(§A.3 3항 · spec.md REQ-BUSKWIZ-010 하위 절): (i) 특정 풀의 미해석·미주소(`binding.reason` 분기, `server/looks/instantiate.py:336-345`), (ii) 라벨 `conflict`(`:359-371`). 점유 미관측(`no_free_slot`)은 REQ-BUSKWIZ-009가 따로 덮는다. **"슬롯 소진"과 "룩별 패밀리 수 차이"는 둘 다 근거로 쓰지 않는다** — 전자는 v1에서 도달 불가한 상태이고(상한 없음·용량 상수 0건), 후자는 **애초에 부분 성공이 아니다**(값 없는 패밀리는 `if not values: continue`로 넘어가 `SkippedStore`를 만들지 않는다 — `:332-334`; 실행 확인 `planned=P skipped=0 complete=True`). 열거에서 지웠다고 다시 넣지 말 것 — 왜 아닌지가 여기 있다.
- **퇴화·경계 케이스는 특수 분기를 만들지 않는다**(acceptance.md §D): 룩 1개짜리 장르는 단일 룩 경로와 동형의 번들을 낸다. 역할이 하나도 매핑되지 않으면 번들은 **빈 채로** 반환되고 대체 그룹을 발명하지 않는다(`server/looks/instantiate.py:456-460` 계승).
  - **작은따옴표 표시 이름의 처리는 미결이다**(v0.1.3 강등): 룩 표시 이름에 작은따옴표가 있으면 `LookInstantiationError`가 난다(`:315-322`). v0.1.2까지 본 계획은 **번들 전체 거부(fail-closed)** 를 적었으나, 그것은 **등록부 밖의 8번째 결정**이었고 "그 룩만 건너뛰고 나머지를 계속한다"는 REQ-BUSKWIZ-010의 방향과 **반대**였다. SSOT가 미결로 강등했으므로 본 계획도 결정으로 적지 않는다 — 현행 32룩에 해당 이름이 0건이라 v1에서 발동하지 않으며, 발동 조건이 생기는 시점(라이브러리 증보)에 결정한다.
- 파일: `server/looks/busking.py`(슬롯 원장 + 번들 결합 절 추가), `server/tests/test_busking_bundle.py`(**신규**).
- **AC**: AC-BUSKWIZ-003, AC-BUSKWIZ-004, AC-BUSKWIZ-005, AC-BUSKWIZ-006, AC-BUSKWIZ-007.

### M3 — 집계 보고 계층 (cycle_type=tdd)

- **2단 구조화 보고**(REQ-BUSKWIZ-013): (a) 생성 프리셋의 풀·슬롯·이름 **전량**, (b) 미매핑 역할과 사유 — **매칭 판정 3종**(`ambiguous`·`no_match` — `server/looks/roles.py:22-23`; `unaddressable` — `server/looks/resolver.py:50`)과 **섹션 실패 전파 사유**(`server/looks/resolver.py:128-137`)를 **부류로 구분**해 싣고 병합하지 않는다, (c) 건너뛴 저장의 개수·풀·슬롯·사유(**단위는 프리셋 저장 1회이지 룩이 아니다**), (d) **룩별 판정**(`complete` / `partial` / `none`), (e) **미실행 커맨드 수**(stop-on-first-failure — (c)와 합산 금지, 자동 재시도 없음). **집계만 보고하고 룩별을 생략하는 것은 금지** — 57~87 커맨드(§A.2 계수 각주) 중 어느 룩이 죽었는지 사용자가 알 수 없게 된다. (b)의 집계 단위는 `(룩, 역할)` 쌍이며 distinct 역할 목록은 별도 필드로 병기한다.
- **산술 정합을 기계 고정**: 집계 수치(생성 N / 건너뜀 M / 미매핑 K)가 룩별 합계와 일치해야 하며, 불일치는 실패다(`AC-BUSKWIZ-008` 구간 1). 장르의 **모든** 룩이 정확히 한 번씩 판정에 나타난다(구간 5). **K의 단위는 `(룩, 역할)` 쌍이다**(spec.md REQ-BUSKWIZ-013 하위 절((b)의 집계 단위)) — 리그를 1회만 해석하므로 미매핑 역할은 그것을 선언한 모든 룩에서 반복되고, distinct 역할 수로 세면 룩별 합계와 어긋나 구간 1이 깨진다. 사람이 읽을 **distinct 역할 목록은 별도 필드로 병기**한다.
  - **픽스처 수치 (plan-phase 실측 — 라이브러리 직접 계수)**: 역할이 하나도 매핑되지 않은 리그에서 K는 **worship 25 / rock 26 / ballad 20 / edm 26**이고 distinct는 **언제나 6**이다(4장르 모두 역할 6종을 전부 쓴다) — **괴리 3.3~4.3배**. distinct로 세면 worship이 25 대신 6으로 보고돼 구간 1이 즉시 깨지므로, 이 네 수를 그대로 테스트 픽스처의 기대값으로 쓴다. **역할 하나만 미매핑이어도 쌍 카운트는 1이 아니다** — 단일 역할 최대 기여는 rock `사이드` **7**(8룩 중), worship·edm `배경` **6**이다. 이 경계 케이스도 별도 테스트로 고정한다.
- **한국어 1급**(REQ-BUSKWIZ-015): 사용자 대면 문자열은 한국어이고, 장르·역할·사유 코드의 한국어 표현 매핑은 **표현 계층 코드**에 둔다. **룩 자산이나 스키마에 한국어 필드를 추가하지 않는다** — `server/looks/matching.py:17-19`가 같은 이유로 별칭을 자산이 아닌 코드 표에 둔 선례이며, PRESERVE diff 빈 출력(`AC-BUSKWIZ-014`)이 이를 교차 확인한다.
- **드릴다운 상한 신호 전파**: `drilldown_capped`(`server/looks/instantiate.py:101`)를 보고에 그대로 싣는다 — 상한에 걸린 관측을 완전한 관측으로 취급하지 않는다(acceptance.md §D).
- **두 종류의 "부분"을 섞지 않는다**(§C.9): **계획 시점의 건너뜀**(풀 미해석·라벨 충돌·점유 미관측 → REQ-BUSKWIZ-010의 부분 성공, 커맨드가 애초에 발화되지 않음)과 **실행 시점의 중단 잔여**(`run_commands`의 stop-on-first-failure로 뒤 전량이 `not_executed` — `server/orchestrator/tools.py:527-536`)는 **원인도 조치도 다르다.** 보고는 둘을 별도 항목으로 싣고, `not_executed`를 건너뜀 카운터에 합산하지 않는다.
- **모듈 분리 결정**: 보고 계층은 `server/looks/report.py` **신규 모듈**로 둔다. 근거 — (a) 한국어 표현 매핑은 번들 조립과 다른 관심사이고, (b) `busking.py`가 조회·원장·결합으로 이미 세 책임을 진다, (c) `AC-BUSKWIZ-008`의 검증이 `server/tests/test_busking_report.py` 단일 파일이므로 **모듈 경계가 테스트 경계와 일치**한다.
- 파일: `server/looks/report.py`(**신규**), `server/tests/test_busking_report.py`(**신규**).
- **AC**: AC-BUSKWIZ-008.

### M4 — 툴 배선 · 실행 경로 · LiveLock (cycle_type=tdd)

- **툴 1종 신설**(REQ-BUSKWIZ-019): 기존 등록 관례를 그대로 따른다 — `ToolDefinition`(`server/llm/types.py:16-26`) + `build_toolset`(`server/orchestrator/tools.py:448-457`) 내부 클로저 핸들러 + `TOOL_NAMES` 등재(`:40-47`) + `definitions`/`handlers` 병렬 갱신(`:1052-1059`). **3곳 중 하나라도 누락되면 실패**로 판정한다(`AC-BUSKWIZ-011` 구간 1).
- **`is_error` 규약**(REQ-BUSKWIZ-019): 정정 가능한 실수(알 수 없는 장르 키)는 `is_error=True`, **답변인 실패**(저장 0건, LiveLock 강등)는 `is_error=False`. 선례 — `_error_result`(`:702-704`), 빈 번들의 `is_error=False`(`:779-790`), `find_looks`의 같은 처리(`:672-681`).
- **리그는 핸들러가 직접 읽는다**(REQ-BUSKWIZ-020): 툴 파라미터 스키마에 그룹·풀·슬롯·픽스처 필드가 **0개**이고, 핸들러가 `collect_rig_sections` 계열로 직접 읽는다. 근거는 이미 코드에 있다 — "a model retyping a rig section can paraphrase a name, drop the truncation signal or supply a number the console never gave"(`server/orchestrator/tools.py:735-738`).
- **단일 실행 경로**(REQ-BUSKWIZ-011 · REQ-BUSKWIZ-012): 번들은 기존 `run_commands` → `gate.screen()` 경로로**만** 실행한다. 신규 REST 라우트·웹소켓 메시지 타입·`execution_port` 직접 접근 **0건**. 두 `@MX:ANCHOR`가 이미 그 경계를 문서화한다 — `server/safety/gate.py:260-265`(스크리닝 경로 하나)와 `server/orchestrator/tools.py:686-696`(룩 계층은 `run_commands`의 **호출자**이지 제2 실행 표면이 아니다).
- **경계 검증은 AST 식별자 스캔이다**(`AC-BUSKWIZ-009` 구간 1): raw 텍스트 grep은 "호출"과 "호출을 설명하는 독스트링"을 구분하지 못한다 — LOOKLIB v0.3.2가 같은 이유로 수단을 교체했고(`SPEC-COPILOT-LOOKLIB-001/plan.md:177`), `server/tests/test_looks_resolver.py:509-529`에 동형 스캔이 이미 있다. **그 구현을 재사용**하고, 비공허성 assert(스캔이 실제로 식별자를 모았는지)를 동반한다. 독스트링을 지워 스캔을 통과시키는 것은 금지.
- **LiveLock 강등**(REQ-BUSKWIZ-014): LiveLock 상태에서 콘솔 송신 **0건**, 반환은 실행이 아니라 **제안**이며 `is_error=False`(답변인 결과이지 기술적 실패가 아니다). 근거: `.moai/project/product.md:44` §6 비목표 — 라이브 실시간 자율 운영 배제. (v0.1.3 정정: `:43`은 빈 줄이며 SSOT가 `:44`로 고쳤다.)
- **게이트 보류 확인**: 목 게이트가 승인 보류를 반환하면 콘솔 송신이 0건임을 별도 assert한다(`AC-BUSKWIZ-009` 구간 3).
- 파일: `server/orchestrator/tools.py`(**신규 툴 등록만** — dedupe 블록과 `_PROGRAMMER_STATE_COMMANDS`는 무변경), `server/tests/test_busking_tool.py`(**신규**).
- **AC**: AC-BUSKWIZ-009, AC-BUSKWIZ-010, AC-BUSKWIZ-011.

### M5 — 익스큐터 레이아웃 GO/DESCOPE (cycle_type=tdd)

**M0 판정에 따라 두 분기 중 정확히 하나를 실행한다**(`AC-BUSKWIZ-012 검증 방법`). 어느 쪽이든 이 마일스톤은 완료되며, DESCOPE는 실패가 아니다.

- **① GO 분기** (ASSUMPTION-16 ∧ ASSUMPTION-17 ∧ ASSUMPTION-19 **셋 다** 긍정, REQ-BUSKWIZ-016): 생성한 팔레트에 대응하는 익스큐터 레이아웃을 생성한다. **발화 형식은 M0의 ASSUMPTION-19가 실측한 것 하나뿐이다** — 이 SPEC의 산출물은 프리셋이므로 `Assign Sequence <n> At Executor <m>`(`31_choreography_patterns.md:99`, `:168`)은 **목적어가 맞지 않아 그대로 쓸 수 없다**(spec.md REQ-BUSKWIZ-016 하위 절(ASSUMPTION-19가 게이트에 추가된 이유)).
  - **익스큐터 번호의 출처는 `resolved_executor_nos`가 아니다**(v0.1.3 감사 — `AC-BUSKWIZ-012` ① 정정): 그 함수가 반환하는 것은 **콘솔이 확인해 준 = 이미 존재하는(점유된) 익스큐터**(`server/web/dash.py:309-317`)라, "빈 익스큐터에 얹는다"는 ASSUMPTION-17과 **정면으로 모순**된다. 번호는 **M0가 GO로 판정한 빈-익스큐터 식별 경로가 반환한 것**에서만 온다. 그 경로가 무엇인지는 M0의 실측 결과가 정하며, 미확정 상태에서 `resolved_executor_nos`로 대신하지 않는다.
  - **바인딩 대상은 이미 존재하는 오브젝트여야 한다** — 그렇지 않으면 시퀀스 생성이 암묵적으로 범위에 들어온다(`spec.md §D Out of Scope — 시퀀스 · 큐 생성`).
- **② DESCOPE 분기**: 생성 번들에 `Executor`·`Page`를 대상으로 하는 커맨드가 **0건**이고, DESCOPE 사유가 `progress.md` M0 절에 기록되어 있다. **실행되지 않은 분기의 테스트는 `skip` 사유를 명시한 채 남긴다 — 삭제하지 않는다**(후속 SPEC이 게이트를 다시 열 때 필요하다, `AC-BUSKWIZ-012 비고`).
- **익스큐터 주소 금지 규율은 분기와 무관하게 적용된다**(REQ-BUSKWIZ-017 · REQ-BUSKWIZ-018, `AC-BUSKWIZ-013`):
  - `page_no*100 + slot`을 **일반 해석 규칙으로 하드코딩하지 않는다.** 이 관례는 **페이지 1에서만** 라이브 관측되었고(`server/web/dash.py:145-157`, 2026-07-24 실측), `REQ-EXECBODY-007`·`REQ-EXECBODY-008`(`SPEC-COPILOT-EXECBODY-001/spec.md:69-70`)이 2개 이상 페이지의 라이브 검증 전 하드코딩을 금지하며 **그 조건은 아직 충족되지 않았다**. 리터럴 `100`을 익스큐터 번호 산술에 쓰는 지점 0건.
  - `Page <p>.<e>` **dotted 주소형 발화 0건**(정규식 스캔). 이 형식은 룰북 산문에 있으나(`00_grammar.md:19`, `:47`, `:70-71`; `10_object_model.md:23-25`) **해당 파일들에는 라이브 검증 표시가 없고**, 리포지토리에서 이를 발화하는 코드 경로도 **0건**이다(모든 경로가 `Executor <n>`만 쓴다: `server/web/panel.py:592-622`, `server/orchestrator/last_created.py:12-15`, `console/lua/copilot_responder.lua:405`). **금지의 성격을 오해하지 말 것 — "콘솔이 거부한다"가 아니다**(spec.md REQ-BUSKWIZ-018 하위 절(금지의 성격)): LOOKLIB M7 라이브에서 모델이 창발적으로 발화한 `Assign Sequence 17 At Page 1.102`는 실제로 **executed 로그에 남았다**(`SPEC-COPILOT-LOOKLIB-001/progress.md:790`, `:858-859`; 그 세션은 이를 요구 아닌 창발 행동으로 규정해 인수 계수에서 제외했다 — `:862`). 금지 근거는 **(a) 출처**(라이브 검증을 선언한 룰북 파일은 `31_choreography_patterns.md:7` 하나이고 그 파일은 `Executor <n>`만 담는다)와 **(b) 단일 형식 일관성**이다. 테스트·주석에 "콘솔이 거부하므로"라고 적으면 **관측되지 않은 사실을 주장하는 것**이며, 그 자체가 이 SPEC이 반복 금지하는 추측이다.
- 파일: `server/looks/busking.py`(익스큐터 레이아웃 절 — **GO 분기에서만** 추가), `server/tests/test_busking_executor.py`(**신규 — 두 분기 모두에서 생성**. DESCOPE여도 "커맨드 0건"을 고정하는 스캔 테스트가 이 파일에 산다).
- **AC**: AC-BUSKWIZ-012, AC-BUSKWIZ-013.

### M6 — 회귀 · PRESERVE · 정적 금지 스캔 (cycle_type=tdd)

- **PRESERVE 무변경**(REQ-BUSKWIZ-003, `AC-BUSKWIZ-014`): **`git diff --stat <BASE>..HEAD -- <목록>`**이 빈 출력(`AC-BUSKWIZ-014 검증 방법`). **`<BASE>..HEAD` 범위는 협상 불가다**(v0.1.3 감사) — 인자 없는 `git diff`는 커밋 직후 **항상** 빈 출력이라 게이트가 통째로 무력해진다. `<BASE>`는 본 SPEC 착수 커밋이다. 추가로 `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(`:227-231`)와 dedupe 블록(`:526-550`)이 무변경임을 확인 — 본 SPEC의 `tools.py` 변경이 신규 툴 등록으로 한정됨의 기계적 증거다.
- **전체 회귀**: `pytest server/tests/ -q` 신규 실패 **0건**. **baseline은 이 마일스톤이 착수 직전 직접 실측한 수에 귀속한다 — 이월 인용 금지**(spec.md §C 측정된 기준선; LOOKLIB이 M1~M4에 걸쳐 baseline 3건 불일치를 규명하지 못한 전례의 방지책).
- **per-show 값 정적 진입 금지**(REQ-BUSKWIZ-008, `AC-BUSKWIZ-015`): 신규·수정 파일 전체 스캔에서 그룹·풀·슬롯·FID·익스큐터 번호 리터럴이 커맨드 문자열 조립에 직접 쓰이는 지점 **0건**. 모든 번호는 리그 조회 결과 객체의 필드에서 온다. **신규 YAML·JSON 자산 0개**(본 SPEC은 자산을 추가하지 않는다). 풀 번호를 `4`(Color) 같은 룰북 예시 값으로 기본값 지정하는 코드 0건 — `resolve_pools`의 독스트링이 이미 그 함정을 적어 두었다(`server/looks/instantiate.py:220-222`).
- **AC 소유의 구분**: `AC-BUSKWIZ-009`(단일 실행 경로 AST 스캔)의 **최초 판정은 M4 소관**이며, M6는 그 스캔이 전체 스위트에서 깨지지 않았음을 **회귀로 재확인**할 뿐이다. 같은 규율로 `AC-BUSKWIZ-006`의 `/Overwrite` 0건과 `AC-BUSKWIZ-013`의 dotted form 0건도 M2·M5가 소유하고 M6가 재확인한다.
- **`ruff check` 신규 경고 0건.** 기존 비-clean 지점은 무관 재포맷을 피해 손대지 않으며, 그 사실을 progress.md에 기록한다(acceptance.md §E).
- 파일: **신규 0.** 기존 스위트 전체 + 정적 스캔. 스캔의 거처는 M2·M4·M5가 배치한 테스트 파일이며, M6는 새 테스트 파일을 만들지 않는다(회귀 마일스톤이 새 판정을 소유하면 소유 관계가 흐려진다).
- **AC**: AC-BUSKWIZ-014, AC-BUSKWIZ-015.

### M7 — 종단 라이브 검증 (실물 onPC)

- 실물 콘솔에서 장르 1개의 버스킹 준비를 **종단 1회** 실행: 지시 → 장르 해석 → 조회 → 리그 1회 해석 → 원장 → 번들 → 실행 프리뷰 관측 → 게이트 감사 로그 확인 → 생성 프리셋 재조회.
- **무손실 확인**(`AC-BUSKWIZ-017` ①②): `console.executed == plan.commands` — 한 줄도 잃지 않는다(특히 `ChangeDestination Root` 1건과 모든 `ClearAll`). `skipped_already_executed` **0건**으로 `AC-BUSKWIZ-005` ④의 유닛 판정이 실물에서 재현된다. **이것이 결정 F(코드 개정 없이 형상으로 회피)의 최종 증명이다.**
- **슬롯 원장의 라이브 확인**(③④): 생성된 프리셋이 재조회에서 **서로 다른 슬롯**에 존재하고, 보고의 집계 수치가 재조회 실측과 일치한다.
- **M0에서 이미 실측된 ASSUMPTION-16/17/18/19는 여기서 재측정하지 않는다** — M7은 종단 통합의 실측이지 전제 검증이 아니다. M0 판정과 M7 관측이 어긋나면 그 불일치 자체를 progress.md에 기록한다.
- **검증의 한계를 결과에 명시한다**: 응답기는 프리셋 **내용**을 읽을 수 없다(LOOKLIB M0 교차 발견의 계승) — 검증은 슬롯·라벨의 **존재** 수준이다(`AC-BUSKWIZ-017 비고`).
- 배포 왕복 불요(콘솔측 무변경). 선행 조건: 콘솔 실행 + 이름 있는 그룹과 관측 가능한 프리셋 풀이 있는 쇼파일(GUI 사용자 작업).
- 파일: **신규·수정 0**. 산출물은 `progress.md` M7 절의 종단 기록(감사 로그 verbatim + 재조회 결과).
- **AC**: AC-BUSKWIZ-017 (LIVE — 2건 중 2번째).

### 라이브 세션 회계

사용자 확정 ④(결정 D)의 2회를 마일스톤에 배치하면 다음과 같다. **두 세션은 시간축의 양 끝에 있어 물리적으로 병합할 수 없다.**

| | 세션 | AC | 무엇을 측정하는가 | 왜 합칠 수 없는가 |
|---|---|---|---|---|
| 1 | **M0 프로브** | AC-BUSKWIZ-016 | ASSUMPTION-16(페이지·익스큐터 저작 문법) · ASSUMPTION-17(빈 익스큐터 판별) · **ASSUMPTION-19(팔레트를 익스큐터에 얹는 문법 — 얹을 대상의 존재)** · ASSUMPTION-18(**v1 형상 상한 87줄** 단일 번들 왕복 + 중도 실패 사후 상태) | **M1 착수 전에 답이 필요하다**(`AC-BUSKWIZ-016 기대 결과` — 판정 미확정으로 M1을 착수하지 않는다). 측정 대상은 **아직 존재하지 않는 코드의 전제**이므로, 코드가 생긴 뒤로 미루면 M2·M5의 되돌림 비용을 그대로 뒤집어쓴다. 코드 변경 0의 세션이라 준비 비용이 M7보다 낮다 |
| 2 | **M7 종단** | AC-BUSKWIZ-017 | 조회→원장→번들→게이트→콘솔의 종단 통합, 번들 무손실, 슬롯 원장의 실물 확인 | **M6 완료 후에만 존재한다**. 측정 대상이 **완성된 파이프라인 전체**이므로 M0 시점에는 측정할 물건 자체가 없다. M0에서 미리 잰다는 것은 논리적으로 불가능하다 |

**라이브 세션 수 = 2.** 이는 프로젝트 관례("라이브 검증 마일스톤 1개")로부터의 의식적 이탈이며, 그 대가로 "전제 미검증 상태에서 조율 계층 전체를 저작하고 마지막에 무너지는" 위험을 제거한다. LOOKLIB이 같은 회계로 2회를 집행한 선례가 있다(`SPEC-COPILOT-LOOKLIB-001/plan.md:205-214`).

## §C. 기술 제약

1. **신규 런타임 의존성 0.** 순수 파이썬 + 기존 패키지 내부 확장(spec.md §C 기술 스택). 신규 YAML·JSON 자산도 0개(`AC-BUSKWIZ-015`).
2. **`@MX:ANCHOR` 경계 (위반 불가)**: `server/safety/gate.py:260-265`(스크리닝 경로 하나 — "exactly ONE screening path may exist; a second entry would be a gate bypass by construction")와 `server/orchestrator/tools.py:686-696`(룩 계층은 `run_commands`의 **호출자**이지 제2 실행 표면이 아니다). 본 SPEC은 두 앵커를 **소비만** 하고 신설하지 않는다.
3. **PRESERVE 경계**(§A.5): `tools.py` 변경은 **신규 툴 1종의 등록**으로 한정된다. dedupe 블록(`:526-550`)과 `_PROGRAMMER_STATE_COMMANDS`(`:227-231`)는 무변경이며, 이것이 결정 F의 집행 형태다.
4. **fail-safe는 협상 대상이 아니다.** 미매핑·충돌·미관측·풀 미해석·장르 미해석의 실패 방향은 항상 **축소 또는 보류**이지 추측 보완이 아니다(§A.3). ("슬롯 소진"은 v1에서 도달 불가하므로 이 목록에 넣지 않는다 — v0.1.3 감사 D2.)
5. **per-show 값의 정적 데이터 진입 금지**(REQ-BUSKWIZ-008): 그룹·풀·슬롯·FID·익스큐터 번호는 코드 상수·YAML 자산·룰북 어디에도 들어가지 않는다. 모든 실번호는 **런타임에 콘솔이 답한 값**이다.
   - **인용은 spec.md v0.1.1이 정정을 마쳤다**: 이 규율의 원전 문장은 `server/orchestrator/tools.py:77-79`("Guessed paths are how \"Patch/Fixtures\" and \"DataPool/Presets\" shipped dead for the whole of Stage 1")이며, 초판이 인용했던 `:53-55`는 같은 주석 블록의 앞부분(`rig_paths` 오버라이드 안내)이었다. REQ-BUSKWIZ-008이 v0.1.1에서 `:77-79`로 갱신되었으므로 **본 계획과 SSOT의 인용이 일치한다** — run-phase도 `:77-79`를 쓴다.
6. **범위 경계**: 포지션 팔레트 없음, 무브먼트 인스턴스화 없음, 시퀀스·큐 생성 없음, P1-1 없음, 전용 위저드 화면 없음, 라이브러리 증보 없음, dedupe 규칙 개정 없음(spec.md §D). UI 무변경, 콘솔측 Lua 무변경.
7. **라이브 왕복 비용 — 세션 2회**(§B 라이브 세션 회계).
   - **M0 접근 불가 시**: **M1 착수를 보류**하고 사유를 progress.md에 기록한다(`AC-BUSKWIZ-016 비고`).
     - **예외적 진행 절차**: 예외 진행은 **익스큐터 축을 DESCOPE로 선(先)확정**하는 것으로**만** 성립한다 — 그 경우 REQ-BUSKWIZ-016은 발동하지 않고 `AC-BUSKWIZ-012`는 ② 분기로 판정되며, M5는 스캔 테스트만 남는다.
     - **그러나 프로브가 사라지는 것은 아니다**: ASSUMPTION-18은 **여전히 M2를 막는다**. 따라서 예외 진행은 M0를 없애는 것이 아니라 **M1 완료 후·M2 착수 전으로 옮기는 것**이며(라이브 세션 수는 그대로 2회), 그 지점에서도 접근 불가라면 **번들 규모 위험이 열린 채 남는다는 사실을 명시 기록**한다(`AC-BUSKWIZ-016 비고`). 위험을 열어 둔 채 진행할지는 §G의 조건부 사용자 접점이다.
   - **M7 접근 불가 시**: M6까지 완료 후 progress.md에 상태를 기록하고 세션을 마무리한다(EXECBODY-001 M3 회복 절차 선례).
8. **기준선 재측정 의무**: 각 마일스톤은 **착수 직전 자신이 직접 실측한 수**에만 델타를 귀속시킨다. plan-phase는 전체 스위트·커버리지 수치를 인용하지 않는다(spec.md §C 측정된 기준선).
9. **`run_commands`는 stop-on-first-failure다 — "부분"이 두 종류로 갈린다.** 한 줄이 실패하면 그 뒤 전량이 `not_executed` 상태로 남는다(`server/orchestrator/tools.py:527-536`이 그 분기, `:562`가 `failed` 플래그). 본 SPEC의 번들은 51~87줄이라(§A.2 계수 각주) 이 성질의 노출 면적이 단일 룩 번들(최대 13줄)보다 훨씬 크다. 규율 넷: (a) **REQ-BUSKWIZ-010의 부분 성공은 계획 시점 개념**(풀 미해석·라벨 충돌·점유 미관측으로 저장이 애초에 계획되지 않음 — §A.3 3항)이고 `not_executed`는 **실행 시점 개념**이다 — 보고에서 합산하지 않는다(§B M3). (b) **룩별 판정은 실행 결과에서 산출한다** — 계획 결과에는 중단 정보가 없으므로 per-command status와 대조해야 한다(§B M3, REQ-BUSKWIZ-013 (d)의 산출 경로). (c) **재시도를 자동으로 하지 않는다.** 근거가 둘이다 — (i) 중단 지점 이후를 다시 보내려면 프로그래머 상태가 어디까지 남았는지 알아야 하는데 그것은 관측되지 않은 사실이고(§A.3 정직한 축소), (ii) **같은 instruction 안에서 번들을 그대로 재발화하면 앞서 성공한 `Store Preset`·`Label Preset` 줄이 조용히 탈락한다** — 그 둘은 `_PROGRAMMER_STATE_COMMANDS` 면제 집합(`:227-231`)에 없으므로 dedupe가 `skipped_already_executed`로 접는다(`:537`, detail `:548` "already executed successfully in this instruction"). 즉 재시도 번들의 문자열과 콘솔이 받는 것이 또 한 번 어긋나며, 이는 결정 F가 목적지 커맨드에서 이미 겪은 것과 **같은 형태의 함정**이다. (d) M0가 실물에서 이 사후 상태를 관측해 기록한다(§B M0).

## §D. @MX 태그 대상 (예상 — 실제 배치는 run-phase에서 확정)

| 태그 | 대상 | 내용 |
|---|---|---|
| `@MX:NOTE` | `server/looks/busking.py` 슬롯 원장 | 이 계층이 **하드 결함 1의 해소 지점**임을 표시 — `PoolBinding`/`PoolIndex`가 frozen이고 `_first_free_slot`이 전진하지 않으므로(`server/looks/instantiate.py:78-79`, `:307-312`), 원장을 제거하면 N개 룩이 조용히 같은 슬롯을 겨냥한다. 라벨이 달라 `CONFLICT`에도 걸리지 않는다는 점을 함께 적는다 |
| `@MX:WARN` + `@MX:REASON` | `server/looks/busking.py` 번들 결합 지점 | `ChangeDestination Root` **선두 1회** 규율이 취향이 아니라 **dedupe 탈락 회피**임을 명시(`server/orchestrator/tools.py:227-231`, `:537`). 위험 지대: "룩별 번들을 concat하면 되지 않나"라는 자연스러운 리팩터가 정확히 이 규율을 깬다. 라이브 관측 근거(`SPEC-COPILOT-LOOKLIB-001/progress.md:799-805`)를 함께 건다 |
| `@MX:NOTE` | `server/looks/report.py` | 건너뜀 카운트의 **단위가 프리셋 저장 1회이지 룩이 아님**을 표시 — 룩 단위로 세면 부분 충돌이 표현 불가능해져 "부분 성공을 전체 성공으로 위장하지 않는다"에 반한다 |
| `@MX:WARN` + `@MX:REASON` | (GO 분기 시) 익스큐터 레이아웃 지점 | 익스큐터 번호는 **콘솔이 확인해 준 것만** 쓴다(`server/web/dash.py:129-143`). `page*100+slot` 산술은 `REQ-EXECBODY-007`·`REQ-EXECBODY-008`의 미충족 조건에서 금지된다. dotted form 금지는 **콘솔 거부가 아니라 출처·일관성 근거**임을 함께 적는다(spec.md REQ-BUSKWIZ-018 하위 절(금지의 성격) — 라이브에서 executed된 관측이 있다). 위험 지대: "콘솔이 받으니 써도 되지 않나"가 정확히 이 규율을 깬다 |
| `@MX:ANCHOR` 신설 없음 | — | 기존 2앵커(§C.2)를 **소비만** 한다. 신규 툴은 `instantiate_look`과 동형의 `run_commands` 호출자이므로 그 앵커의 보호 범위 안에 들어간다 |

## §E. 테스트 스캐폴딩 계획

- **순수 함수 우선**: 조회·원장·번들 결합·보고 전부 인메모리 픽스처로 검증하며 콘솔·OSC에 접촉하지 않는다. 라이브를 요구하는 것은 `AC-BUSKWIZ-016`·`AC-BUSKWIZ-017` 둘뿐이고, **유닛 통과를 라이브 통과로 대체 인용하지 않는다**(`acceptance.md §A 라이브 층`).
- **실패 모드 개별 테스트(병합 금지) — 부류를 넘어 합치지 않는다**: ① **저장 건너뜀 2종**(`conflict` / `no_free_slot`), ② **매칭 판정 3종**(`ambiguous`·`no_match` — `server/looks/roles.py:22-23`; `unaddressable` — `server/looks/resolver.py:50`). ②는 "역할이 안 붙었다", 아래 ③은 "리그 섹션이 오지 않았다"로 **사실이 다르므로 한 카운터에 넣지 않는다**(§B M3 (b)와 같은 구분). 그 밖에 장르 미해석 / **부분 성공 2경로**(풀 미해석 · 라벨 충돌 — §A.3 3항) / 드릴다운 상한 / 역할 전멸 각각 독립 테스트다. 사유를 합쳐 세면 "무엇이 잘못됐는지"가 지워진다. **"원장 소진" 테스트는 쓰지 않는다** — v1에서 도달 불가한 상태이며 상한을 발명해야 재현되기 때문이다(v0.1.3 감사 D2). **"룩별 패밀리 수 차이" 테스트도 쓰지 않는다** — 그것은 실패가 아니라 `skipped=0 complete=True`인 완전 성공이므로(`server/looks/instantiate.py:332-334`) 부분 성공 테스트로 세우면 assert가 거짓이 된다(v0.1.4 재감사 D2).
  - **③ 섹션 실패 전파 사유는 부류로만 구분하고 테스트 대상에서는 뺀다**: `UnmappedRole.reason` 필드가 담을 수 있는 값에는 전파 사유(`server/looks/resolver.py:128-137`)까지 들어가지만, **본 SPEC의 형상에서는 보고 계층에 도달하지 않는다** — 툴 핸들러가 섹션 미도착을 번들 구성 **이전에** `is_error=True`로 조기 반환하는 선례를 그대로 따르기 때문이다(`server/orchestrator/tools.py:745-768`, `build_instantiation` 호출은 `:770`). 그래서 **테스트 어휘는 판정 3종 유지**이며(`acceptance.md`의 `AC-BUSKWIZ-008`도 3종만 열거한다), 5종으로 늘리면 **도달 불가 경로를 검증하는 테스트**가 된다. M4가 조기 반환을 채택하지 않는다면 그때 ③이 도달 가능해지므로 이 항목을 다시 연다.
- **미관측과 빈 풀의 구별을 2개 테스트로 고정**: `occupied=None`과 `occupied=()`가 서로 다른 결과를 낸다(`AC-BUSKWIZ-007`). 하나로 합치면 그 구별이 사라진 것을 테스트가 알아채지 못한다.
- **선행 구현 회귀 고정**(`AC-BUSKWIZ-004` 구간 2): `build_instantiation`을 동일 `PoolIndex`로 N회 직접 호출하면 전부 같은 슬롯이 나옴을 assert한다. **결함의 실재와 해소를 한 파일에 함께 둔다** — 이 테스트가 없으면 원장이 지워져도 스위트가 조용히 통과한다.
- **번들 문자열 불변식 assert**: 목적지 커맨드 선두 1회(`count == 1` **및** `commands[0]` 동일성 — 둘 다 필요하다, 개수만 보면 위치를 잃는다) · `ClearAll` 쌍 · `Label` 존재 · **대소문자 무관** `/Overwrite` 부재 · 미등재 그룹 부재 · `Page <숫자>.<숫자>` 패턴 0건 · **값 라인 중복 0건**(서로 다른 룩의 값 라인이 문자열로 같아지면 두 번째가 dedupe로 탈락해 **빈 프로그래머에 `Store`**가 걸린다. 현행 32룩은 v1 형상에서 4장르 전부 0건이나 라이브러리가 증보되면 깨질 수 있고, REQ-BUSKWIZ-006이 per-family를 막은 근거가 바로 이 실패이므로 v1 형상에서도 기계로 고정한다).
  - **대소문자 무관 assert의 근거**: 런타임 매칭은 이미 대소문자 무관이다(`server/safety/ruleset.py:47`, `server/safety/classify.py:64`, `server/web/preview.py:100`). 테스트가 `"/Overwrite" not in bundle`처럼 대소문자를 고정하면 빌더가 `/overwrite`를 내보내도 **조용히 통과**한다 — 위험은 런타임이 아니라 **테스트의 위양성**이다.
- **호출 카운팅 스파이**(`AC-BUSKWIZ-003`): `resolve_roles`·`resolve_pools` 각 1회. 룩 수에 비례하면 실패.
- **dedupe 무손실은 목 실행 포트로 확인**(`AC-BUSKWIZ-005` ④): 실제 `run_commands` 경로에 번들을 통과시켜 `skipped_already_executed` 0건. 문자열 assert만으로는 dedupe 통과를 증명할 수 없다.
- **AST 식별자 스캔**(`AC-BUSKWIZ-009` 구간 1): `ast.parse`로 `Attribute.attr` / `Name.id` / import 이름만 모아 `execution_port` · `ConsoleLink`와의 교집합 0을 assert. `server/tests/test_looks_resolver.py:509-529`의 동형 구현을 재사용하고 **비공허성 assert**(스캔이 실제로 식별자를 모았는지)를 동반한다 — 빈 스캔은 항상 통과하는 위양성이다.
- **보고의 산술 정합 assert**: 집계 수치 = 룩별 합계. 불일치는 실패(`AC-BUSKWIZ-008` 구간 1).
- **run-phase 자기 검증 커맨드(예상, run-phase에서 확정)**:
  - `.venv/bin/python -m pytest server/tests/test_busking_genre.py server/tests/test_busking_bundle.py server/tests/test_busking_report.py server/tests/test_busking_tool.py server/tests/test_busking_executor.py -q`
  - `.venv/bin/python -m pytest server/tests/test_looks_instantiate.py server/tests/test_looks_matching.py server/tests/test_looks_boundary.py -q` (소비 대상 계층의 무회귀)
  - `.venv/bin/python -m pytest server/tests/test_architecture.py server/tests/test_safety_gate.py server/tests/test_safety_classify.py server/tests/test_web_preview.py -q`
  - `.venv/bin/python -m pytest -q` (전체 — 해당 마일스톤 착수 직전 실측 기준선 대비 신규 실패 0건)
  - `git diff --stat <BASE>..HEAD -- server/looks/schema.py server/looks/loader.py server/looks/roles.py server/looks/resolver.py server/looks/instantiate.py server/looks/library/ server/safety/ server/web/preview.py console/lua/ server/rulebook/assets/` → **빈 출력** (`AC-BUSKWIZ-014`. **인자 없는 `git diff`는 금지** — 커밋 후 항상 빈 출력이라 게이트가 무력해진다. `instantiate.py`는 v0.1.3에서 등재되었다)
  - `git diff <BASE>..HEAD -- server/orchestrator/tools.py` → 변경 hunk가 신규 툴 등록 4자리(`TOOL_NAMES` · 핸들러 클로저 · `definitions` · `handlers`)에만 존재하고 `:227-231`·`:526-550`에 걸치지 않음
  - `grep -rniE "store\s*/\s*overwrite" server/looks/ server/orchestrator/` → 0건 (`AC-BUSKWIZ-006`)
  - **`Page <숫자>.<숫자>` 0건은 소스 grep이 아니라 생성 커맨드 튜플 전수 검사다**(`AC-BUSKWIZ-013` ②, v0.1.3 정정): 빌더가 생성할 수 있는 모든 번들의 커맨드 튜플을 픽스처로 돌려 정규식 0건을 assert하고, **비공허성 assert**(검사한 커맨드 수 > 0)를 동반한다 — 소스 grep은 문자열이 런타임에 조립되는 경우를 놓치고, 빈 튜플이면 조용히 통과한다.
  - `ruff check` → 신규 경고 0건
  - 라이브 검증(M0·M7): 감사 로그 jsonl verbatim 판독 + GUI 스크린샷(EXECBODY-001 AC-EXECBODY-010 인수 형식 계승)

## §F. 결정 기록 (재질의 금지)

| 결정 | 내용 | 반영 위치 |
|---|---|---|
| **A — 익스큐터 페이지 레이아웃** | **M0 라이브 프로브 GO/DESCOPE 게이트**(ASSUMPTION-16 ∧ ASSUMPTION-17 ∧ **ASSUMPTION-19** — v0.1.2에서 3항 논리곱). 하나라도 부정이면 v1은 익스큐터·페이지 커맨드 0건이며 DESCOPE는 **정의된 결과**다. GO여도 발화 형식은 M0가 실측한 것 하나뿐이고, **못 찾으면 시퀀스를 만들어 우회하지 않는다**(§D 범위 누출) — 사용자 확정 ① + v0.1.2 요구 정합 | spec.md §A 사전 확정 사실(익스큐터 게이트 + 실측 근거) + REQ-BUSKWIZ-016(+ spec.md REQ-BUSKWIZ-016 하위 절(ASSUMPTION-19 사유 · 우회 금지), ASSUMPTION-19 = ASSUMPTION-19), plan.md §A.4a A · §B M0/M5, acceptance.md AC-BUSKWIZ-012 · AC-BUSKWIZ-016 |
| **B — 팔레트 축** | LOOKLIB `IN_SCOPE_POOL_FAMILIES` 4종(Dimmer·Color·Beam·Focus, `server/looks/schema.py:58`) **그대로 상속**(재정의 없이 import). 포지션 축은 선행 SPEC이 닫았으므로 v1에 없다 — 사용자 확정 ② | spec.md §A 사전 확정 사실(팔레트 축) + §D, plan.md §A.4a B, design.md 결정 반영 절 |
| **C — 실행 단위** | **단일 번들 · 승인 1회 · 부분 성공 구조화 보고.** 룩 단위 분할 승인과 dry-run 선보고는 기각. 긴 프리뷰의 검토 난이도는 기각된 반론이 아니라 **수용된 위험**으로 존치 — 사용자 확정 ③. **plan-phase 실측 정정**: 프리뷰 길이는 초판의 "40여 줄"이 아니라 **51~87줄**(상한 87)이며 spec.md v0.1.1이 같은 값으로 갱신되어 있다. 결정은 불변, 위험의 크기만 갱신 | spec.md §A 사전 확정 사실(실행 단위) + REQ-BUSKWIZ-010 · REQ-BUSKWIZ-013, plan.md §A.2 계수 각주 · §A.4a C · §B M0/M3/M4 · §C.9, design.md 위험 절 |
| **D — 라이브 세션 수** | **2회**(M0 프로브 + M7 종단). 프로젝트 관례 1회로부터의 의식적 이탈. 두 세션은 시간축의 양 끝에 있어 병합 불가 — 사용자 확정 ④ | spec.md §A 사전 확정 사실(라이브 세션 2회), plan.md §B 라이브 세션 회계 · §C.7, acceptance.md AC-BUSKWIZ-016 · AC-BUSKWIZ-017 |
| **E — 슬롯 원장** | 풀 패밀리별 **누적 원장**으로 다중 룩 슬롯 재청구 0건화. 시작값은 콘솔 관측 점유이며 **미관측 풀을 비었다고 가정하지 않는다.** `PoolBinding`/`PoolIndex`는 frozen인 채 **바깥에서 감싼다** — 엔지니어링 판단 폐쇄 | plan.md §A.4a E + §A.4a-E, spec.md §A 하드 결함 1 + REQ-BUSKWIZ-005 · REQ-BUSKWIZ-009 · REQ-BUSKWIZ-010, acceptance.md AC-BUSKWIZ-004 · AC-BUSKWIZ-007, §B M2 |
| **F — dedupe 처리** | **`tools.py` dedupe 규칙 무개정.** 장르 번들이 `ChangeDestination Root`를 선두 1회만 발화하는 형상으로 회피하고 룩별 번들 연접을 금지. 근거는 LOOKLIB M7 **라이브 관측**(반복 목적지는 의미상 멱등, 두 번째 번들도 정상 왕복) — 엔지니어링 판단 폐쇄 | plan.md §A.4a F + §A.4a-F, spec.md §A 하드 결함 2 + §D + REQ-BUSKWIZ-006, acceptance.md AC-BUSKWIZ-005 ④ + AC-BUSKWIZ-017 ②, §B M2/M7 |
| **G — 장르 룩 조회** | **`LookLibrary` 직접 순회.** `match_looks` 툴 경로는 `MAX_TOOL_MATCHES=8`에서 EDM 9룩을 1건 자르므로 쓰지 않는다. 별칭 표는 **새로 만들지 않고** 기존 `GENRE_ALIASES`/`resolve_genre`를 호출한다 — 엔지니어링 판단 폐쇄 | plan.md §A.4a G + §A.4a-G, REQ-BUSKWIZ-001 · REQ-BUSKWIZ-002 + REQ-BUSKWIZ-001 · REQ-BUSKWIZ-002 · REQ-BUSKWIZ-003, acceptance.md AC-BUSKWIZ-001 · AC-BUSKWIZ-002, §B M1 |
| frontmatter 참조 | `related_specs`(비차단) — LOOKLIB(completed) · EXECBODY-001(completed) · DASHUI-001(completed) · MVP-001(in-progress). 상태 불균일을 정직하게 기술한 LOOKLIB 선례 계승(`SPEC-COPILOT-LOOKLIB-001/spec.md:157`) — 엄격 충족 전제의 pre-flight 차단 회피 | spec.md frontmatter `related_specs`, spec.md §C 기능 전제 |
| Tier 판단 | **L** — 신규 조율 계층(조회·원장·결합·보고) + 툴 배선 + **라이브 AC 2건** + GO/DESCOPE 조건부 마일스톤이 결합. 예상 파일 8~10 | spec.md frontmatter `tier: L`, plan.md §G |
| 소비자 SPEC 관계 | 본 SPEC은 LOOKLIB 룩 계층의 **소비자**이지 개정자가 아니다(`server/looks/schema.py:20-25` `@MX:NOTE` — 스키마는 P1-1/P1-2 공통 기반). 반대로 본 SPEC은 P1-1(송 구조 큐리스트)에 아무것도 예약하지 않는다 — 시퀀스·타임코드는 §D Out of Scope | spec.md §A PRESERVE + §D, plan.md §A.5, research.md 소비 계약 절 |

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

> 구속력 있는 기록은 `progress.md` §F이며 오케스트레이터 소유다(첫 run-phase `Agent()` 스폰 전 작성). 본 절은 plan-phase 권고이며 오케스트레이터가 확정·기각한다.

### 입력 파라미터

- **tier**: L (5-artifact 세트 + progress.md)
- **scope (file count)**: 예상 **8~10 파일** — 신규 구현 2(`server/looks/busking.py` · `server/looks/report.py`) + 신규 테스트 5(`test_busking_genre.py` · `test_busking_bundle.py` · `test_busking_report.py` · `test_busking_tool.py` · `test_busking_executor.py`) + 수정 1(`server/orchestrator/tools.py`, 신규 툴 등록만) + M0/M7 기록 반영 1~2(`progress.md`). **신규 자산 0**(YAML·JSON 추가 없음), UI·Lua·룰북 무변경.
- **domain count**: **1** — 파이썬 백엔드 단일 도메인. 콘솔 Lua·프런트엔드·룰북 자산이 전부 PRESERVE라 도메인이 확장되지 않는다.
- **file language mix**: **단일 언어**(Python) + markdown 기록. 정적 데이터 저작 없음.
- **concurrency benefit**: **LOW** — 마일스톤 간 순차 의존이 사슬을 이룬다: **M2 ← M1**(번들 결합은 조회가 낸 룩 집합과 그 순서를 입력으로 받는다), **M3 ← M2**(보고는 번들 결과의 생성·건너뜀·미매핑 구조를 입력으로 받는다), **M4 ← M3**(툴 핸들러가 반환하는 것이 그 보고다). 게다가 M1~M5가 **같은 신규 모듈 2개**를 순차로 키우므로 병렬 편집의 충돌 비용이 이득을 상쇄한다. M5만 상대적으로 독립이나 그 존폐가 M0 판정에 걸려 있어 선행 병렬화 대상이 아니다.
- **Agent Teams prereqs**: 해당 없음 (Mode 3 RETIRED)

### 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 신규 모듈 2개 + 툴 배선 + **라이브 AC 2건** + 조건부 마일스톤 — 단일 라인 변경이 아니다 |
| 2 | background | 미선택 | 쓰기 작업(신규 파일 생성·툴 등록) 포함 |
| 3 | agent-team | 미선택 | RETIRED (tombstone) |
| 4 | parallel | 미선택 | 도메인 **1**(<3), 단일 언어, M1→M2→M3→M4의 순차 의존 사슬 — 병렬화 이득이 낮고 같은 모듈을 동시에 키우는 충돌 비용이 이를 넘어선다 |
| 5 | **sub-agent** | **선택** | 순차 의존 사슬 + 코딩 중심 + Tier L Section A-E 위임 템플릿 적용 |
| 6 | workflow | 미선택 | 8~10 파일(30 미만)이고 **균일 기계 변환이 아니다** — 슬롯 원장 형상·보고 모듈 분리·GO/DESCOPE 분기 처리 등 마일스톤마다 설계 판단이 들어간다 |

### Decision: sub-agent

### 정당화

M0(프로브)가 M1의 정책 게이트를, M1(조회)이 M2의 입력을, M2(번들)가 M3의 입력을, M3(보고)가 M4의 반환 형상을 규정하는 순차 게이트 사슬이므로 병렬화 이득이 없다. 도메인 1·단일 언어·예상 8~10 파일은 Mode 4와 Mode 6의 임계를 둘 다 밑돈다. 코딩 중심 작업은 순차 sub-agent가 안전한 기본값이며, Tier L이므로 `manager-develop` 위임에 Section A-E 전체 템플릿을 적용한다.

**오케스트레이터가 확보해야 할 사용자 접점 2건**(전부 AskUserQuestion, 전부 **물리적 접근 가능성**을 묻는다):

1. **Kickoff 시점** — **M0 라이브 세션 접근 가능성** 확인. `AC-BUSKWIZ-016`이 M1 착수의 정책 게이트이므로 run-phase 진입 자체가 여기에 걸린다(§C.7 M0 접근 불가 절차 — 접근 불가 시 익스큐터 축을 DESCOPE로 선확정하고 M1까지만 진행한 뒤 M2 직전에 프로브를 재시도하는 경로가 있다).
2. **M6 완료 직후** — **M7 라이브 세션 접근 가능성** 재확인.

**조건부 접점 1건** (측정 결과가 만들어 낼 때만 발생): M0에서 **ASSUMPTION-18이 부정**으로 실측되면 번들 분할 정책이 필요해지는데, 그것은 사용자 확정 ③(단일 번들·승인 1회)과 정면 충돌한다. **SPEC이 임의로 분할하지 않는다**(ASSUMPTION-18) — 이 경우에 한해 M0 게이트에서 사용자 결정을 받는다. 이는 §A.4a의 7건 중 하나가 열려 있다는 뜻이 **아니다**: 결정 C는 닫혀 있고, 열리는 것은 **측정이 새로 만들어 낸 별개의 결정**이다. 부정 실측 없이는 이 접점이 발생하지 않는다.

**§A.4a 결정 7건(A~G)의 해소용 접점은 0건이다.** 사용자 사전 확정 4건과 엔지니어링 판단 3건으로 착수 시점에 전부 폐쇄되었고, §A.4b는 미해결 결정이 **0건**임을 적은 tombstone일 뿐 열린 항목을 담지 않으며, 이 문서의 clarification 마커는 **0건**이다. 따라서 Implementation Kickoff Approval은 "이 계획대로 진행할지"의 승인 게이트로만 남는다. 위 두 접점은 결정이 아니라 **사람과 실물 콘솔의 일정 확보**를 묻는다 — SPEC이 스스로 답할 수 없는 유일한 종류의 질문이다.
