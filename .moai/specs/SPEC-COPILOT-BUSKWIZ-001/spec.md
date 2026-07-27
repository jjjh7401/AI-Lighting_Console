---
id: SPEC-COPILOT-BUSKWIZ-001
title: "버스킹 준비 마법사 (Busking Preparation Wizard)"
version: "0.1.4"
status: draft
created: 2026-07-27
updated: 2026-07-27
author: manager-spec
priority: P1
phase: "Phase 2 연출 계층 (v1.3.0 target)"
module: "server/looks/ (확장), server/orchestrator/tools.py, server/web/session.py"
lifecycle: spec-anchored
tags: "busking, wizard, genre-bundle, preset-palette, batch-instantiation, slot-ledger, executor-layout, look-library, safety-gate"
tier: L
related_specs: [SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-EXECBODY-001, SPEC-COPILOT-DASHUI-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-BUSKWIZ-001 — 버스킹 준비 마법사

> **본 SPEC은 제안서 P1-2(버스킹 준비 마법사)의 구현이며, 선행 SPEC `SPEC-COPILOT-LOOKLIB-001`(P1-3, completed)이 스키마 형상으로만 예약해 둔 "장르 묶음 인스턴스화"의 **런타임 실행부를 처음 만드는 SPEC**이다.** 제안서 원문(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:76-80`)은 "리그 컨텍스트를 읽어 '이 리그로 버스킹 준비해줘' 한 마디에 컬러/포지션/빔 프리셋 팔레트 + 장르별 익스큐터 페이지 레이아웃을 일괄 생성"을 요구한다. LOOKLIB은 룩 1개 단위 인스턴스화(`instantiate_look`)까지를 출하했고, 그 이상은 명시적으로 본 SPEC에 넘겼다 — "장르 묶음 인스턴스화는 스키마의 API 형상만 예약하고 런타임 실행은 만들지 않는다"(`SPEC-COPILOT-LOOKLIB-001/spec.md:182`).
>
> **로드맵 위치의 정직한 3중 표기 (LOOKLIB spec.md:20-24 선례 계승)**: "버스킹"이라는 낱말이 등재된 유일한 로드맵 행은 **Phase 4**(`product.md:40`, "버스킹 팔레트 추천")이나 그 행의 성공 기준은 **미정(TBD)** 이라 충족 여부를 판정할 수 없다. 본 SPEC이 실제로 충족하는 성공 기준은 **Phase 2**(`product.md:38`)의 "'코러스에서 금색 톤으로 웅장하게' 수준의 추상 지시를 **리그에 맞게 실행**"이며, 같은 행 목표 열의 "**프리셋 어휘 온보딩 마법사**"가 본 SPEC의 마법사와 직접 대응하는 로드맵 항목이다. 소비하는 자산인 "장르별 룩 템플릿"은 **Phase 3**(`product.md:39`) 산출물이나 LOOKLIB이 이미 선(先)착지시켰다. frontmatter의 `phase:` 표기는 **충족 대상 기준**(Phase 2)을 가리키며, Phase 4 항목을 Phase 2로 재분류한다는 뜻이 아니다.
>
> **제안서 3축 중 1축이 선행 SPEC에서 닫혀 있다 (정직한 축소, 착수 시점 고지)**: 제안서가 적은 "컬러/**포지션**/빔" 3축 중 **포지션은 v1에 존재할 수 없다** — Position 풀은 LOOKLIB이 "담을 것이 없다"는 이유로 v1 제외했고(`SPEC-COPILOT-LOOKLIB-001/spec.md:57`, `:192-194`), 정적 pan/tilt를 룩 데이터에 넣는 것은 사용자 확정 ①이 금지했다(`spec.md:44`). 반면 **빔은 열려 있다** — LOOKLIB M0 프로브가 `Zoom`/`Iris`를 GO 판정해 실값이 출하되었다(`server/looks/schema.py:50` `PROBE_GATED_ATTRIBUTES`, 라이브러리 실측 `Iris` 8룩 / `Zoom` 16룩). 본 SPEC의 팔레트 축은 제안서 3축이 아니라 **LOOKLIB이 실제로 출하한 in-scope 4풀**(`schema.py:58`)이다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-27 | manager-spec | 최초 작성 (draft, Tier L). 출처: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` §3 P1-2(76-80행) + `SPEC-COPILOT-LOOKLIB-001/spec.md:180-182`(P1-2 예약 조항) + `research.md:226`(소비 계약). 사용자 사전 확정 4건(§A) 반영: ① 익스큐터 페이지 레이아웃은 M0 라이브 프로브 GO/DESCOPE 게이트, ② 팔레트 축은 LOOKLIB in-scope 4풀 그대로 상속, ③ 단일 번들·승인 1회·부분 성공 구조화 보고, ④ 라이브 세션 2회(M0 프로브 + 종단 검증). 아티팩트 6종(spec/plan/acceptance/design/research/progress) 동시 생성. ASSUMPTION 번호는 LOOKLIB의 15 다음인 **16**부터 계승. |
| 0.1.1 | 2026-07-27 | manager-spec | **plan-phase 실측 반영 — 요구 집합·AC 집합·결정 집합 무변경(REQ 20건 / AC 17건 / 결정 A~G / 마커 0건 그대로).** 나머지 5종 아티팩트 저작 중 리포지토리를 직접 계수·실행해 확인한 6건을 반영했다. (a) **번들 규모**: "최대 약 40여 커맨드"는 쌍(pair) 수에서 나온 추정치였고 실제 행 수는 **51~87행**(상한 edm·4풀 87행)이다 — ASSUMPTION-18의 측정 기준을 실제 상한으로 올렸다(§A, §C). (b) **stop-on-first-failure**: `run_commands`는 첫 실패 이후 전량을 `not_executed`로 만들며(`tools.py:527-536`, `:562`) 이는 REQ-BUSKWIZ-010의 "슬롯 부족 부분 성공"과 다른 사건이다 — 보고 요소 (e)를 신설하고 합산·자동 재시도를 금지했다(REQ-BUSKWIZ-013). (c) **라벨 원장**: `_plan_stores`의 충돌 검사는 콘솔 기존 라벨만 보므로(`instantiate.py:359-361`) 같은 번들 안의 동명 룩을 막는 기제가 없다 — 원장이 라벨도 누적하도록 REQ-BUSKWIZ-005에 명시(현행 32룩은 중복 0건이라 지금 깨진 것은 아니다). (d) **캡처 형상 고정**: `per_family_capture`에서 서로 다른 룩의 값 라인이 문자열로 같아지는 경우가 실재해(edm `Attribute 'Dimmer' At 100` 2건, rock `Attribute 'Iris' At 100` 2건) 두 번째가 dedupe로 탈락하면 빈 프로그래머로 `Store`가 실행된다 — 장르 번들은 `shared_capture` 고정이고 `capture_shape`는 툴 인자가 아니다(REQ-BUSKWIZ-006 / REQ-BUSKWIZ-020). (e) **미매핑 사유는 3종이 아니라 최대 5종**: 판정 3종 + 섹션 실패 전파 2종(`resolver.py:128-137`)이며 두 부류를 구분해 보고한다. 집계 단위는 `(룩, 역할)` 쌍이다(REQ-BUSKWIZ-013). (f) **인용 정정 3건**: `tools.py:53-55`→`:77-79`, `blacklist.yaml:19`→`:18`, 미매핑 사유 상수 위치 `resolver.py:70`→`roles.py:22-23` + `resolver.py:50`. 아울러 REQ-BUSKWIZ-018의 금지 근거를 정직하게 재기술했다 — dotted form은 LOOKLIB M7에서 모델의 창발 발화로 **실제 실행되었으므로**(`LOOKLIB progress.md:790`, `:858-862`) 금지의 근거는 "콘솔이 거부한다"가 아니라 출처·단일 형식 일관성이다. |
| 0.1.2 | 2026-07-27 | manager-spec | **요구 정합 결함 1건 해소 — ASSUMPTION-19 신설, REQ/AC 개수 무변경(REQ 20 / AC 17 / 결정 A~G / 마커 0).** REQ-BUSKWIZ-016은 ASSUMPTION-16/17이 둘 다 GO이면 "팔레트에 대응하는 익스큐터 레이아웃"을 생성하도록 쓰여 있었으나, **라이브 검증된 유일한 바인딩 커맨드의 목적어는 시퀀스**이고(`31_choreography_patterns.md:99`) §D는 시퀀스·큐 생성을 범위 밖으로 두었다 — 즉 게이트가 열려도 **얹을 대상이 없어** 요구가 충족 불가였다. 실측으로 확인: `Assign Preset` · `Preset <p>.<s> At (Executor\|Page) <n>` · `Store Executor` 계열은 `server/`·`console/`·`docs/` 전체에서 **0건**. 따라서 "팔레트를 익스큐터에 얹는 문법의 존부"를 **ASSUMPTION-19**로 명시하고 REQ-BUSKWIZ-016의 게이트를 3항 논리곱으로 바꿨다. 우회로(시퀀스를 만들어 배정)는 §D 위반이므로 M0가 문법을 찾지 못하면 답은 **DESCOPE**다. acceptance.md의 §A · 시나리오 6 · §C.0 표 · AC-BUSKWIZ-012 · AC-BUSKWIZ-016(측정 항목 4 신설)에 전파했다. |
| 0.1.3 | 2026-07-27 | manager-spec | **독립 plan-audit(FAIL 0.78 / Tier L 기준 0.85) 반영 — 지적 8건 처리, REQ 20건·AC 17건·결정 A~G·마커 0건 무변경.** 감사를 권위로 수용하고 원문을 방어하지 않는다. (D1) REQ-BUSKWIZ-016 GO 분기의 충족 불가는 **v0.1.2의 ASSUMPTION-19로 이미 해소**되었고 감사가 이를 확인했다. (D2) **REQ-BUSKWIZ-010의 트리거가 도달 불가였다** — "슬롯이 부족해"는 `_first_free_slot`(`instantiate.py:307-312`)에 상한이 없고 풀 용량 상수가 리포지토리 0건이며 `_observed_contents`가 풀 크기를 보고하지 않아 발생할 수 없는 상태였다. 트리거를 실제 도달 가능한 3경로(패밀리 수 차이 / 풀 미해석 / 라벨 충돌)로 교체하고 AC-BUSKWIZ-004 구간 3을 그에 맞췄다. (D3) **AC-BUSKWIZ-013 ②가 구조적으로 항상 참이었다** — 소스 정규식은 `f"Page {page}.{executor}"` 형태를 볼 수 없다. 빌더가 실제 생성한 커맨드 튜플 전수 + 비공허성 assert로 교체. (D4) **AC-BUSKWIZ-014의 `git diff`에 베이스 리비전이 없어 커밋 후 항상 빈 출력**이었다 — `<BASE>..HEAD`로 교체하고 `server/looks/instantiate.py`를 PRESERVE에 추가(결정 E의 반증을 diff로 드러내기 위함). (D5) **AC-BUSKWIZ-012 ①이 번호 출처를 `resolved_executor_nos`(=점유된 익스큐터)로 못박아 ASSUMPTION-17(빈 익스큐터 판별)과 모순**이었다 — 출처를 "M0가 GO로 판정한 빈-익스큐터 식별 경로"로 바꾸고 그 경로의 식별을 AC-BUSKWIZ-016 측정 항목 2의 산출물로 요구. (D6) **acceptance.md §D가 결정 등록부 밖에서 fail-closed 번들 전체 거부를 신설**했고 그것이 REQ-BUSKWIZ-010과 반대 방향이었다 — 도달 불가 분기이므로 **미결로 강등**. (D7) `product.md:43`은 빈 줄 — `:44`로 정정(research.md가 처음부터 옳았다). (D8) **형제→SSOT 줄 앵커가 한 사이클에 세 번 붕괴** — 형제 아티팩트의 SSOT 참조를 **안정 토큰**(`REQ-BUSKWIZ-nnn` / `ASSUMPTION-nn` / 절 제목 / 명명된 하위 절)으로 전면 전환하는 규율을 채택했다. `파일:줄`은 **코드 인용에만** 쓴다 — 코드는 커밋 없이 움직이지 않고 다른 안정 식별자가 없기 때문이다. (D9) AC-BUSKWIZ-002 ③의 import 스캔은 중복 정의를 판정할 수 없어 AST 스캔으로 교체. |
| 0.1.4 | 2026-07-27 | manager-spec | **재감사(PASS 0.88 / 기준 0.85) 조건부 지적 처리 — 요구·AC·결정·마일스톤 집합 무변경.** (재D2 부분 닫힘) **REQ-BUSKWIZ-010의 도달 가능 트리거 열거에서 1건을 삭제했다** — "룩마다 값을 가진 패밀리 수가 다르다"는 부분 성공이 **아니다**. `_plan_stores`는 값이 없는 패밀리를 `if not values: continue`로 넘기며 `SkippedStore`를 만들지 않아(`instantiate.py:332-334`) `planned=P, skipped=0, complete=True`가 된다(실행 확인: `ballad-single-key` P=4 / `ballad-moonlight` P=2 둘 다 완전 성공). 남는 트리거는 **풀 미해석·미주소**와 **라벨 충돌** 둘이며, 점유 미관측은 REQ-BUSKWIZ-009가 따로 덮는다. acceptance.md의 §C.0 REQ-BUSKWIZ-010 행 비고(잔존한 "원장 소진" 표현)와 AC-BUSKWIZ-004 구간 3을 함께 정정하고 **건너뜀 항목 비공허성** assert를 추가했다. (재P3) §E·§F에 남아 있던 **슬러그 없는 세 자리 축약형 4건**을 완전 토큰으로 교체 — 6종 전체 축약 토큰 스캔 **0건** 확인. **이 행 자체가 그 축약형을 리터럴로 적지 않는 이유도 같다**: 적는 순간 자기 자신이 위반 스캔에 잡힌다(LOOKLIB 자기오염 선례 계승). |

## A. 개요

버스킹(busking)은 사전에 큐를 짜 두지 않고 팔레트·익스큐터를 즉석에서 조합해 진행하는 운용 방식이다. 실무의 성패는 **사전 준비물의 품질**에 달려 있고, "큐 작성 전 프리셋 구축"이 최대 시간 소모처다(제안서 :78-80). LOOKLIB은 "룩 1개를 프리셋으로"를 완성했으나, 버스킹 준비는 **한 장르 전체(6~10룩)를 한 번에** 필요로 한다.

본 SPEC은 (1) 장르 단위로 룩 집합을 절단 없이 조회하고, (2) 리그를 **1회만** 해석해 그 집합 전체를 **하나의 커맨드 번들**로 구성하며, (3) 기존 안전 게이트의 단일 스크리닝 경로로 **한 번의 승인**을 받아 실행하고, (4) 부분 성공을 부분 성공으로 보고하는 것을 v1로 정의한다. 익스큐터 페이지 레이아웃은 **M0 라이브 프로브의 GO/DESCOPE 판정에 종속**된다(사용자 확정 ①).

아키텍처 전제: **LOOKLIB 파이프라인 전면 재사용, 신규 실행 표면 0**. 룩 데이터·스키마·역할 어휘·역할 해석기·풀 해석기·단일 룩 번들 빌더는 전부 그대로 소비하고 변경하지 않는다. 본 SPEC이 새로 만드는 것은 **N개 룩을 가로지르는 조율 계층**뿐이다 — 장르 조회, 슬롯 원장, 번들 결합, 집계 보고.

### 사전 확정 사실 (합의된 접근 — 재질의 금지)

- **팔레트 축 = LOOKLIB in-scope 4풀 그대로 상속** (사용자 확정 ②): `Dimmer` · `Color` · `Beam` · `Focus` — `server/looks/schema.py:58` `IN_SCOPE_POOL_FAMILIES`를 **본 SPEC이 재정의하지 않고 import해 쓴다**. 본 SPEC은 attribute 어휘를 새로 만들지 않으므로 빔 문법에 대한 신규 프로브가 필요 없다(LOOKLIB M0가 이미 `Zoom`/`Iris` GO를 실측했고, 라이브러리에 실값이 출하되어 있다).
  - **포지션 축은 v1에 존재하지 않는다**: 제안서 :78이 요구한 "포지션 프리셋 팔레트"는 선행 SPEC이 닫았다(`LOOKLIB spec.md:57` Position 풀 제외, `:192-194` Out of Scope, 사용자 확정 ① 정적 pan/tilt 금지). 본 SPEC은 그 결정을 **번복하지 않고 계승**하며, §D에 제외 사유를 명시한다.
- **익스큐터 페이지 레이아웃 = M0 라이브 프로브 게이트 (GO/DESCOPE 분기)** (사용자 확정 ①): 페이지 생성·라벨·복사, 익스큐터 번호 배정 규칙, 익스큐터 라벨링, 빈 익스큐터 탐색은 **리포지토리 전체에서 근거 0건**이다(아래 실측 참조). `SPEC-COPILOT-EXECBODY-001`의 M1 GO/DESCOPE 라이브 프로브 패턴(`SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123` AC-EXECBODY-010)과 LOOKLIB의 빔 축 처리(`LOOKLIB spec.md:45`)를 그대로 계승한다. 프로브는 plan.md §B의 **M0**이며 ASSUMPTION-16/17이 그 대상이다.
  - **실측 근거 (근거 0건의 확인)**: 페이지 관련 커맨드가 리포지토리에 등장하는 유일한 곳은 `server/measurement/corpus.yaml`이며(`:84`, `:90`, `:98-99`, `:105`, `:146`, `:153`), 이 파일은 스스로 그 블록이 **"the deterministic offline action for M6a mock runs ONLY"** 이고 커맨드 라인은 **"structurally valid"** 할 뿐이라고 한정한다(`corpus.yaml:8-10`) — 콘솔 수용을 주장하지 않는다. 더욱이 `Label Page 3 "Ballad"`(`:99`)는 큰따옴표를 쓰는데 `00_grammar.md:26-29`가 생성 커맨드에서 이를 금지한다(전송 계층이 커맨드 라인을 큰따옴표로 감싸므로 내장 큰따옴표는 커맨드를 깨뜨린다). **즉 그대로 발화하면 깨지는 형태다.** 룰북 `v2.4.2/` 전체에서 `Store Page` / `Label Page` / `Label Executor` / 빈 익스큐터 열거 커맨드는 **0건**이다.
  - **바인딩 커맨드만은 라이브 근거가 있다**: `Assign Sequence 11 At Executor 191`(`31_choreography_patterns.md:99`, 파일 헤더 `:7` — "Every pattern below was validated live on onPC 2.4.2"), 재확인 `:168`. 안전 게이트도 이를 `safe`로 분류한다(`server/tests/test_safety_classify.py:152`). **그러나 "어느 익스큐터 번호에 놓을지"는 여전히 근거 0건**이므로(아래) 바인딩 커맨드의 존재만으로 레이아웃 생성이 성립하지는 않는다.
  - **역주소 문제는 미해결로 상속된다**: 콘솔 발화 번호와 페이지-로컬 인덱스가 다르고(`SPEC-COPILOT-EXECBODY-001/spec.md:43` 실측 `1,5,11,91,92,93,95,101` ↔ `101,105,111,191,192,193,195,201`), `page_no*100 + slot` 관례는 **페이지 1에서만** 관측되었다(`server/web/dash.py:150-152`, 2026-07-24 라이브 실측). `REQ-EXECBODY-007/008`(`spec.md:69-70`)이 "2개 이상 서로 다른 페이지에서 라이브 검증되기 전에는 일반 해석 규칙으로 하드코딩하지 않으며, 미검증이면 해당 메커니즘을 출하하지 않는다"고 못 박았고 그 조건은 **아직 충족되지 않았다**. 본 SPEC은 이 금지를 REQ-BUSKWIZ-017로 계승한다.
- **실행 단위: 단일 번들 · 승인 1회 · 부분 성공 구조화 보고** (사용자 확정 ③): 장르 1개 전체가 **하나의 번들**로 구성되어 **하나의 승인 카드**로 스크리닝된다. 마법사의 가치가 "한 마디에 일괄"이므로 룩 단위 분할 승인(6~10회 왕복)은 기능 자체를 무력화한다. 실패한 저장은 LOOKLIB과 동일하게 **건너뛰고 "N개 건너뜀"을 구조화 보고**하며, **N의 단위는 프리셋 저장 1회이지 룩이 아니다**(`LOOKLIB spec.md:65` 결정 I 계승).
  - **번들 규모의 실측 (plan-phase에서 출하 라이브러리를 직접 계수)**: 규모는 `_bundle`의 `CAPTURE_SHARED` 형상(`server/looks/instantiate.py:395-404`)에서 결정론적으로 나온다 — 룩 1개 = `ClearAll` + 선택 + 값 + (`Store`+`Label`)×P + `ClearAll`, 여기에 번들 선두 `ChangeDestination Root` 1행. 4풀 전량 가용 시 **ballad 67 / rock 77 / worship 77 / edm 87행**, Dimmer·Color만 가용 시 57~73행이며, 룩 경계의 인접 `ClearAll`을 1회로 접으면 각각 N−1행 줄어 **51~79행**이 된다(접기 여부는 M2의 형상 결정이다). **즉 상한은 87행이고 하한도 51행이다.** LOOKLIB M7 라이브의 실측 최대는 21행이므로 미측정 구간은 약 4배다 — ASSUMPTION-18의 M0 측정은 **실제 상한(edm · 4풀)** 에서 해야 하며, 그보다 작은 합성 번들에서의 통과는 GO 근거가 되지 못한다.
  - **수용된 잔여 위험**: 이 길이의 프리뷰는 사람이 실질 검토하기 어렵다. 이 논거는 사용자에게 제시되었고(대안: 룩 단위 분할 승인 / dry-run 선보고), 사용자는 이를 알고 단일 승인을 선택했다. 따라서 **기각된 반론이 아니라 표면화된 뒤 수용된 위험**으로 design.md §4에 존치한다. 완화는 REQ-BUSKWIZ-013의 집계 보고가 담당한다. (사용자에게 제시될 당시의 추정치는 "40여 줄"이었고 실측은 그보다 크다 — **결정은 불변이고 갱신된 것은 그 결정이 안고 가는 비용의 크기**다.)
- **라이브 세션 2회** (사용자 확정 ④): **M0**(익스큐터 문법 프로브 + 다중 룩 번들 왕복 실측)와 **종단 검증**(M7)이 실물 콘솔을 요구한다. LOOKLIB의 라이브 세션 회계(계획 2회)를 그대로 따른다.
- **PRESERVE — 본 SPEC이 변경하지 않는 것**: `server/looks/schema.py`, `server/looks/loader.py`, `server/looks/roles.py`, `server/looks/resolver.py`, **`server/looks/instantiate.py`**, `server/looks/library/*.yaml`, `server/safety/**`, `server/web/preview.py`, `console/lua/copilot_responder.lua`, `server/rulebook/assets/v2.4.2/**`, 그리고 `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(`:227-231`)와 dedupe 블록(`:526-550`). 룩 스키마는 P1-1/P1-2 공통 기반이므로 파괴 변경이 두 소비자를 함께 깨뜨린다(`server/looks/schema.py:20-25` `@MX:NOTE`) — 본 SPEC은 그 스키마의 **소비자**이지 개정자가 아니다.
  - **`instantiate.py`가 목록에 있는 이유 (v0.1.3 — 감사 D4)**: 결정 E(슬롯 원장)는 "frozen 자료구조를 **바깥에서 감싼다**"는 형상이며, 그것이 성립하지 않아 `PoolIndex`/`PoolBinding`/`_plan_stores`를 고치게 되는 경우가 **결정 E의 반증**이다. 이 파일을 PRESERVE에 넣으면 그 반증이 diff로 즉시 드러난다 — 목록에 없으면 조용히 개정하고 지나갈 수 있고, 그 개정은 단일 룩 경로(`instantiate_look`)와 P1-1까지 함께 흔든다. **변경이 정말 필요하다고 판단되면 그것은 결정 E를 다시 여는 사건이며, 사용자 확인 없이 진행하지 않는다.**

### ⚠️ 선행 구현에서 발견된 하드 결함 2건 — 본 SPEC이 그 위에 선다

LOOKLIB의 단일 룩 경로는 **룩마다 리그를 다시 읽는 왕복 구조**(`server/orchestrator/tools.py:739-744`)라서 아래 두 결함이 가려져 있었다. 다중 룩을 하나의 번들로 묶는 순간 둘 다 즉시 발현한다.

1. **슬롯 비전진 (본 SPEC이 반드시 해결)** — `PoolBinding`/`PoolIndex`가 `@dataclass(frozen=True)`이고(`server/looks/instantiate.py:78-79`, `:96-97`), `_plan_stores`는 `binding.occupied`를 **읽기만** 한다(`:346`, `:358`). `_first_free_slot`(`:307-312`)은 인자로 받은 점유 목록에서 1부터 오름차순 첫 미점유를 고를 뿐 어디에도 쓰기·전진이 없다. 따라서 **하나의 `PoolIndex`로 N개 룩을 `build_instantiation` 하면 N개 전부가 같은 슬롯을 겨냥한다.** 라벨이 서로 다르므로 `CONFLICT` 판정에도 걸리지 않고(`:359-361`은 이미 콘솔에 있는 라벨만 본다), 결과는 **같은 슬롯에 N번 `Store`** — 정확히 이 프로젝트가 막으려 한 "사람이 만든 프리셋 위에 쓰기"의 자기 재현이다.
2. **`ChangeDestination Root`의 dedupe 탈락 (본 SPEC이 설계로 회피, 코드 개정 없음)** — `_PROGRAMMER_STATE_COMMANDS` 면제 집합은 `Clear` / `ClearAll` / 맨-형태 `Fixture|Group` 선택 **3종뿐**이고(`server/orchestrator/tools.py:227-231`), `run_commands`의 dedupe는 `context.executed_ok`를 시드로 번들 내에서도 누적한다(`:526`, `:537`). LOOKLIB M7 라이브 세션이 이 탈락을 **실물에서 관측**했다 — `skipped_already_executed` 정확히 1건이며 그것이 `ChangeDestination Root`였다(`LOOKLIB progress.md:799-805`, `:1167-1170`). **그 세션의 두 번째 번들은 그럼에도 정상 왕복했다** — 목적지 상태가 세션에 남아 있기 때문이다. 본 SPEC은 이 실측을 근거로 **면제 집합을 개정하지 않고**(즉 `tools.py`를 PRESERVE에 유지하고) 번들 형상 쪽에서 해결한다: 장르 번들은 `ChangeDestination Root`를 **번들 선두에 정확히 1회만** 발화한다(REQ-BUSKWIZ-006). LOOKLIB이 "dedupe 규칙 개정 여부는 M4가 단독으로 정하지 않는다"고 넘긴 판단(`LOOKLIB progress.md:1330`)에 대한 본 SPEC의 답은 **"개정하지 않는다"** 이며 그 근거는 위 라이브 관측이다.

## B. 요구사항 (GEARS)

### B.1 장르 룩 집합 조회

- **REQ-BUSKWIZ-001** [Ubiquitous] — 장르 조회 API **shall** 주어진 장르에 속한 룩을 **절단 없이 전량** 반환하며, 반환 순서는 다이내믹스 레벨 오름차순 → 동률 시 `look_id` 사전순의 **결정론적 전순서**다. 기존 `match_looks` 툴 경로는 `MAX_TOOL_MATCHES = 8`에서 결과를 자르므로(`server/looks/matching.py:71`, `:279-292` `truncated` 신호) **장르 전량 조회에 사용할 수 없다** — EDM 9룩은 1건이 잘린다(실측: worship 8 / rock 8 / ballad 7 / edm 9).
- **REQ-BUSKWIZ-002** [Event-driven] — **When** 사용자가 한국어 또는 영어 장르명으로 버스킹 준비를 지시하면, the 시스템 **shall** 기존 `GENRE_ALIASES` 표(`server/looks/matching.py:73-90`)로 장르를 해석하고, 해석에 실패하면 **후보 장르 목록과 함께 정직하게 실패**한다 — 가장 비슷한 장르로 임의 승격하지 않는다.
- **REQ-BUSKWIZ-003** [Unwanted] — 본 SPEC **shall not** 룩 스키마·로더·역할 어휘·역할 해석기·라이브러리 자산을 변경한다(§A PRESERVE). 장르 조회는 이미 로드된 `LookLibrary`에 대한 **읽기 전용 순회**로 구현한다.

### B.2 다중 룩 번들 구성

- **REQ-BUSKWIZ-004** [Ubiquitous] — 장르 번들 빌더 **shall** 리그를 **정확히 1회** 해석해(`resolve_roles` 1회 + `resolve_pools` 1회) 그 결과를 집합의 모든 룩에 재사용한다. 이것이 LOOKLIB이 예약한 "API 형상"의 실체다 — `build_instantiation`이 해석 결과를 키워드 전용 파라미터로 받는 형상(`server/looks/instantiate.py:416-423`)이 재사용을 문법적으로 허용한다.
- **REQ-BUSKWIZ-005** [Ubiquitous] — 번들 빌더 **shall** 풀 패밀리별 **슬롯 원장**을 유지하여, 앞선 룩이 청구한 슬롯을 뒤 룩이 다시 청구하지 않게 한다. 원장의 초기값은 콘솔이 관측 보고한 점유 목록이며, 룩마다 청구된 슬롯이 누적된다. **§A 하드 결함 1의 해소 요구이며, 본 SPEC의 존재 이유 중 하나다.**
  - **원장은 관측을 대체하지 않는다**: 점유 미관측(`binding.occupied is None`, `instantiate.py:82-85`)인 풀은 원장이 있든 없든 `NO_FREE_SLOT`으로 건너뛴다(REQ-BUSKWIZ-009). 원장은 **관측된 점유에 본 번들이 만들 점유를 더하는 것**이지, 관측되지 않은 풀을 비었다고 가정하는 장치가 아니다.
  - **원장은 슬롯과 함께 라벨도 누적한다**: `_plan_stores`의 충돌 검사는 **콘솔에 이미 있는 라벨만** 본다(`server/looks/instantiate.py:359-361` — `binding.labels`). 같은 번들이 만들어 낼 라벨끼리는 비교 대상이 아니므로, 표시 이름이 같은 두 룩이 한 장르에 있으면 서로를 모른 채 각자 저장된다. 현행 32룩의 `display_name`은 장르 내·간 모두 중복 0건이라 **지금 깨져 있는 것은 아니지만 막는 기제가 없다** — 원장이 이번 번들에서 청구한 라벨도 누적해 동일 판정(대소문자·공백 무시 일치 = 건너뛰기)을 적용한다.
- **REQ-BUSKWIZ-006** [Ubiquitous] — 장르 번들 **shall** `ChangeDestination Root`를 **번들 선두에 정확히 1회** 포함하고, 룩 단위 캡처 사이클마다 `ClearAll` 규율(`31_choreography_patterns.md:9-23`, `:40-41`)을 유지한다. 룩별 번들을 단순 연접(concatenate)하는 형상은 금지된다 — 2..N번째의 `ChangeDestination Root`가 dedupe로 탈락해(`server/orchestrator/tools.py:537`) 번들의 문자열과 콘솔이 실제로 받은 것이 어긋나기 때문이다(§A 하드 결함 2).
  - **캡처 형상은 `shared_capture` 고정이며 모델 인자로 노출하지 않는다**: `per_family_capture` 형상은 룩마다 **패밀리별 값 라인**을 따로 발화하는데(`server/looks/instantiate.py:406-411`), 서로 다른 룩의 값 라인이 문자열로 같아지는 경우가 실재한다(실측: edm 두 룩의 `Attribute 'Dimmer' At 100`, rock 두 룩의 `Attribute 'Iris' At 100`). 값 라인은 dedupe 면제 집합에 없고(`server/orchestrator/tools.py:227-231`) 직전 `ClearAll`은 면제라 살아남으므로, 두 번째 값 라인이 탈락하면 **빈 프로그래머 상태로 `Store`가 실행되고 콘솔은 성공으로 답한다.** `shared_capture`는 룩당 값 라인이 1개이고 그 전체 문자열이 4장르 32룩 전수에서 중복 0건이므로 이 경로가 존재하지 않는다. 이는 REQ-BUSKWIZ-006이 금지한 "번들 문자열과 콘솔이 받은 것의 어긋남"의 다른 형태이며, 새 요구가 아니라 그 금지의 귀결이다.
- **REQ-BUSKWIZ-007** [Unwanted] — 번들 **shall not** 어떤 경로로도 `Store /Overwrite`를 발화하지 않으며, 점유된 슬롯을 재슬롯하지도 않는다. 충돌 처리는 **건너뛰기 하나**다(`LOOKLIB REQ-LOOKLIB-012` 계승; `server/safety/blacklist.yaml:18`이 `Store /overwrite`를 블랙리스트로 유지한다 — LOOKLIB이 인용한 `:19`는 현재 트리에서 `Shutdown`이므로 본 SPEC은 정정된 줄을 쓴다).
- **REQ-BUSKWIZ-008** [Unwanted] — 본 SPEC **shall not** 그룹 번호·풀 번호·슬롯 번호·FID·익스큐터 번호를 정적 데이터(코드 상수·YAML 자산·룰북)에 넣는다. 모든 실번호는 **런타임에 콘솔이 답한 값**이어야 한다(`server/orchestrator/tools.py:77-79` — "Guessed paths are how \"Patch/Fixtures\" and \"DataPool/Presets\" shipped dead for the whole of Stage 1"; `server/looks/resolver.py:113-119` 번호 날조 금지 `@MX:WARN`). **인용 정밀도 주석**: LOOKLIB이 같은 사고를 `tools.py:53-55`로 인용했으나(`LOOKLIB spec.md:58`) 현재 트리에서 그 위치는 같은 주석 블록의 앞부분(`rig_paths` 오버라이드 안내)이고 해당 문장은 `:77-79`에 있다. 본 SPEC은 정정된 줄을 인용하며, 결정 내용에는 영향이 없다(같은 블록·같은 사고).
- **REQ-BUSKWIZ-009** [State-driven] — **While** 어떤 in-scope 풀의 점유가 관측되지 않은 상태이면, the 시스템 **shall** 그 풀을 대상으로 하는 모든 저장을 `no_free_slot` 사유로 건너뛰고 보고한다 — 미관측을 빈 풀로 취급하지 않는다(`server/looks/instantiate.py:82-85`, `:346-357`).
- **REQ-BUSKWIZ-010** [Ubiquitous] — 장르의 룩 중 **일부만 저장 가능한 경우**, the 시스템 **shall** 저장 가능한 것을 저장하고 나머지를 건너뛴 것으로 보고한다 — 전량 실패로 되돌리지 않고, 부분 성공을 전체 성공으로 위장하지도 않는다.
  - **트리거의 실측 (v0.1.3 — 감사 D2; v0.1.4에서 열거 1건 정정 — 재감사 D2 부분 닫힘)**: v0.1.2까지 이 요구는 "**슬롯이 부족해**"를 트리거로 적었으나 **그 상태는 발생할 수 없다.** `_first_free_slot`(`server/looks/instantiate.py:307-312`)은 `slot = 1`에서 시작해 점유 집합에 없을 때까지 증가할 뿐 상한이 없고, 리포지토리 어디에도 풀 용량 상수가 없으며(`max_slot`/`pool_size`/`POOL_CAPACITY` 계열 0건), `_observed_contents`(`:195-215`)는 점유된 자식만 반환할 뿐 **풀 크기를 보고하지 않는다** — 즉 런타임에도 상한을 알 방법이 없다. 상한을 발명해 테스트하는 것은 REQ-BUSKWIZ-008이 금지한 per-show 값의 정적 진입이다.
    - **실제로 도달 가능한 부분 성공 트리거는 둘이다**: (i) 어떤 풀만 `pool_unresolved`/`pool_unaddressable`이라 그 풀 대상 저장만 전량 건너뛰어진다(`_plan_stores`의 `binding.reason` 분기, `instantiate.py:336-345`), (ii) 콘솔에 이미 같은 이름의 프리셋이 있어 `conflict`로 건너뛰어진다(`:359-371`; 같은 장르를 연속 2회 실행하는 경우가 그것이다). 여기에 REQ-BUSKWIZ-009의 점유 미관측(`no_free_slot`)이 세 번째 경로로 겹치지만 그것은 그 요구가 따로 덮는다.
    - **"룩마다 값을 가진 패밀리 수가 다르다"는 부분 성공이 아니다 (v0.1.4 정정)**: v0.1.3이 이를 첫 번째 트리거로 열거했으나 **틀렸다.** `_plan_stores`는 룩이 그 패밀리에 값을 갖지 않으면 `if not values: continue`로 넘어가며 **`SkippedStore`를 만들지 않는다**(`instantiate.py:332-334`). 실행 확인: 4풀이 전부 해석·관측된 리그에서 `ballad-single-key`(P=4) → `planned=4 skipped=0 complete=True`, `ballad-moonlight`(P=2) → `planned=2 skipped=0 complete=True`. 둘 다 **완전 성공**이며 보고할 건너뜀이 없다 — 패밀리 수의 차이는 그 룩이 원래 갖는 속성이지 실패가 아니다. 이 열거를 근거로 "건너뜀이 있다"를 assert하면 거짓이 된다.

### B.3 실행 · 승인 · 보고

- **REQ-BUSKWIZ-011** [Event-driven] — **When** 사용자가 버스킹 준비 실행을 지시하면, the 시스템 **shall** 구성된 번들을 **기존 `run_commands` → `gate.screen()` 경로로만** 실행한다. 제2 실행 경로·신규 REST 엔드포인트·`execution_port` 직접 접근은 금지된다(`server/safety/gate.py:260-265` `@MX:ANCHOR`; `server/orchestrator/tools.py:686-696` `@MX:ANCHOR`/`@MX:REASON`이 같은 경계를 이미 문서화한다).
- **REQ-BUSKWIZ-012** [Unwanted] — 본 SPEC **shall not** 새로운 실행 표면을 만들거나 안전 게이트를 우회·완화한다. 승인 카드·실행 프리뷰·블랙리스트·LiveLock은 전부 기존 구현을 그대로 통과한다.
- **REQ-BUSKWIZ-013** [Event-driven] — **When** 버스킹 준비가 완료되면, the 시스템 **shall** 다음을 **집계 + 룩별** 2단 구조화 요약으로 보고한다: (a) 생성된 프리셋의 풀·슬롯·이름 전량, (b) **미매핑 역할 목록**과 사유, (c) **건너뛴 프리셋 저장의 개수와 각각의 풀·슬롯·사유**(단위는 프리셋 저장 1회이지 룩이 아니다), (d) **룩별 판정**(전량 성공 / 부분 / 저장 0건)과 그 근거, (e) **미실행 커맨드 수**(아래 stop-on-first-failure). 집계만 보고하고 룩별을 생략하는 것은 금지된다 — 수십 줄 중 어느 룩이 죽었는지 사용자가 알 수 없게 된다.
  - **(b)의 사유는 3종이 아니라 최대 5종이다**: 매칭 판정 3종 — `ambiguous` · `no_match`(`server/looks/roles.py:22-23`) · `unaddressable`(`server/looks/resolver.py:50`) — 에 더해, 그룹 섹션 자체가 오지 않았을 때 **섹션의 사유 문자열이 모든 역할에 그대로 전파**된다(`server/looks/resolver.py:128-137` — 예: `path_not_resolved` / `console_unreachable`). 보고는 이 두 부류를 구분해야 한다: 전자는 리그의 문제(그룹을 만들거나 이름을 고치면 해소)이고 후자는 **관측 자체가 실패한 것**(같은 리그를 다시 읽으면 달라질 수 있음)이다. 후자를 "이 리그에 백라이트가 없다"로 보고하면 보지 않은 리그에 대한 주장이 된다.
  - **(c)와 (e)를 합산하지 않는다**: `run_commands`는 **stop-on-first-failure**다 — 한 줄이 실패하면 그 뒤 전량이 `not_executed`가 된다(`server/orchestrator/tools.py:527-536`, `:562`). 이것은 REQ-BUSKWIZ-010이 말하는 "일부만 저장 가능"과 **원인도 조치도 다른 사건**이다 — 건너뜀은 **빌드 시점** 판정(그 저장은 애초에 서지 않았다)이고 미실행은 **실행 시점** 귀결(앞줄이 실패해 뒤가 전송되지 않았다)이다. 두 수를 한 칸에 합치면 사용자가 조치를 고를 수 없으므로 **별도 항목으로 싣는다.** 자동 재시도도 하지 않는다 — 재시도는 이미 성공한 앞부분의 콘솔 효과를 중복시킬 수 있고, 그 판단은 사람 몫이다.
  - **(b)의 집계 단위는 `(룩, 역할)` 쌍이다**: 리그를 1회만 해석하므로(REQ-BUSKWIZ-004) 미매핑 역할은 그것을 선언한 **모든 룩에서 반복**된다. 집계를 distinct 역할 수로 세면 룩별 합계와 어긋나 AC-BUSKWIZ-008 구간 1(산술 일치)이 깨진다. 따라서 집계 수치는 `(룩, 역할)` 쌍의 개수로 정의하고, 사람이 읽을 **distinct 역할 목록은 별도 필드로 병기**한다.
- **REQ-BUSKWIZ-014** [State-driven] — **While** LiveLock 상태이면, the 시스템 **shall** 버스킹 준비를 실행하지 않고 **제안으로 강등**한다(`.moai/project/product.md:44` §6 비목표 — "**라이브 실시간 자율 운영 배제**: … 라이브 잠금 모드에서는 read-only + 제안 카드만 생성하며, 실행 버튼은 항상 사람이 누른다"; `LOOKLIB REQ-LOOKLIB-020` 계승). **인용 정정(v0.1.3 — 감사 D7)**: v0.1.2까지 `product.md:43`으로 적었으나 그 줄은 **빈 줄**이다(`:42`가 `## 6. 명시적 비목표` 헤딩, 본문은 `:44`). research.md가 처음부터 `:44`로 정확히 적었으므로 정본을 그쪽에 맞춘다.
- **REQ-BUSKWIZ-015** [Ubiquitous] — 사용자 대면 보고는 **한국어를 1급**으로 한다(`LOOKLIB REQ-LOOKLIB-018` 계승). 장르·역할·사유 코드의 한국어 표현은 **표현 계층**에서 매핑하며, 룩 자산이나 스키마에 한국어 필드를 추가하지 않는다(`server/looks/matching.py:17-19`가 같은 이유로 별칭을 자산이 아닌 코드 표에 둔 선례).

### B.4 익스큐터 페이지 레이아웃 (M0 게이트 — ASSUMPTION-16/17/19와 한 쌍)

- **REQ-BUSKWIZ-016** [Where] — **Where** ASSUMPTION-16(페이지·익스큐터 저작 문법) · ASSUMPTION-17(빈 익스큐터 판별) · ASSUMPTION-19(팔레트를 익스큐터에 얹는 문법)이 **셋 다** M0 프로브에서 긍정 실측된 경우에 한하여, the 시스템 **shall** 생성한 팔레트에 대응하는 익스큐터 레이아웃을 생성한다. 이 요구는 **역량 게이트이지 이벤트 트리거가 아니다** — 게이트가 열리지 않으면 요구 자체가 발동하지 않는다.
  - **하나라도 부정이면 DESCOPE**: v1은 익스큐터·페이지 대상 커맨드를 **0건** 발화하고, 그 사실과 사유를 progress.md에 기록한다(`LOOKLIB spec.md:45` 빔 축 처리와 동형의 "정직한 축소"). DESCOPE는 실패가 아니라 **정의된 결과**다.
  - **ASSUMPTION-19가 게이트에 추가된 이유 (v0.1.2 — 요구 정합 결함의 해소)**: 라이브 검증된 유일한 바인딩 커맨드는 `Assign Sequence <n> At Executor <m>`(`31_choreography_patterns.md:99`, `:168`)이며 그 목적어는 **시퀀스**다. 그런데 본 SPEC의 산출물은 **프리셋**이고, §D는 시퀀스·큐 생성을 범위 밖으로 두었다. 즉 ASSUMPTION-16/17이 둘 다 GO여도 **얹을 대상이 없다** — v0.1.1까지의 REQ-BUSKWIZ-016은 그 상태로 발동 가능한 것처럼 쓰여 있었고, 이는 §D와 정면으로 어긋나는 요구였다. 실측: `Assign Preset` · `Preset <p>.<s> At (Executor|Page) <n>` · `Store Executor` 계열은 `server/`·`console/`·`docs/` 전체에서 **0건**이다. 따라서 "팔레트를 익스큐터에 얹는" 문법의 존부 자체가 미검증 전제이며, 그것이 ASSUMPTION-19다.
  - **GO여도 발화 형식은 M0가 실측한 것 하나뿐**: 시퀀스를 만들어 우회하는 것은 금지된다(§D "시퀀스·큐 생성" — 그 순간 시퀀스 생성이 암묵적으로 범위에 들어온다). M0가 프리셋을 직접 얹는 문법을 찾지 못하면 답은 **DESCOPE**이지 "그럼 시퀀스를 만들자"가 아니다.
- **REQ-BUSKWIZ-017** [Unwanted] — 본 SPEC **shall not** `page_no*100 + slot` 관례를 익스큐터 주소의 일반 해석 규칙으로 하드코딩한다. 이 관례는 **페이지 1에서만** 라이브 관측되었고(`server/web/dash.py:150-152`; 표본 `SPEC-COPILOT-EXECBODY-001/spec.md:43`), `REQ-EXECBODY-007/008`(`spec.md:69-70`)이 2개 이상 페이지의 라이브 검증 전 하드코딩을 금지하며 그 조건은 미충족이다. 익스큐터 번호가 필요하면 **콘솔이 확인해 준 번호만** 쓴다(`server/web/dash.py:129-143` `_confirm_executor_no`, `:309-317` `resolved_executor_nos`).
- **REQ-BUSKWIZ-018** [Unwanted] — 본 SPEC **shall not** `Page <page>.<executor>` dotted 주소형을 발화한다. 이 형식은 룰북 `00_grammar.md:19`, `:47`, `:70-71`과 `10_object_model.md:23-25`에 진술되어 있으나 **해당 파일들에는 라이브 검증 표시가 없고**(라이브 검증을 선언하는 파일은 `31_choreography_patterns.md:7` 하나다), 리포지토리에서 이 형식을 실제로 발화하는 코드 경로도 **0건**이다(모든 경로가 `Executor <n>` 형식만 쓴다: `server/web/panel.py:592-622`, `server/orchestrator/last_created.py:12-15`, `console/lua/copilot_responder.lua:405`).
  - **금지의 성격을 정확히 적는다 — "콘솔이 거부한다"가 아니다**: LOOKLIB M7 라이브 세션에서 모델이 **툴 위에서 창발적으로** `Assign Sequence 17 At Page 1.102`와 `Go+ Page 1.102`를 발화했고, 전자는 실제로 **executed 로그에 남았다**(`LOOKLIB progress.md:790`, `:858-859`). 그 세션은 이를 "본 SPEC의 요구가 아닌 모델의 창발 행동"으로 규정해 인수 계수에서 제외했다(`:862`). 즉 dotted form이 콘솔에 거부당한다는 증거는 없다. 본 SPEC이 금지하는 근거는 다른 두 가지다: (a) **출처** — 이 저장소가 라이브 검증을 선언한 룰북 파일은 하나뿐이고(`31_choreography_patterns.md:7`) 그 파일은 `Executor <n>` 형식만 담는다, (b) **단일 형식 일관성** — 게이트의 참조 인식(`server/safety/classify.py:44`), 본문 해석(`server/safety/console.py:414-421`), 응답기 주소 해석(`console/lua/copilot_responder.lua:403-405` — "the ONLY address form resolve_path special-cases")이 모두 `Executor <n>`에 맞춰져 있어, 두 번째 주소형을 도입하면 그 세 계층이 각각 무엇을 보는지가 갈린다. 금지를 되열려면 (a) 룰북에 라이브 검증된 형식으로 등재되고, (b) 세 계층의 인식이 함께 확장되며, (c) 역주소 문제(REQ-BUSKWIZ-017)가 먼저 닫혀야 한다.

### B.5 툴 배선 · 표면

- **REQ-BUSKWIZ-019** [Ubiquitous] — 마법사는 LLM 툴 **1종 신설**로 노출되며, 기존 등록 관례를 그대로 따른다: `ToolDefinition`(`server/llm/types.py:16-26`) + `build_toolset` 내부 클로저 핸들러 + `TOOL_NAMES` 등재 + `definitions`/`handlers` 병렬 갱신(`server/orchestrator/tools.py:40-47`, `:448-457`, `:1052-1060`). 정정 가능한 실수는 `is_error=True`, **답변인 실패**(장르 미해석·저장 0건)는 `is_error=False`로 반환한다(`:419-429`, `:677-681`, `:783-791` 선례).
- **REQ-BUSKWIZ-020** [Ubiquitous] — 리그 데이터는 **모델 인자로 받지 않고** 툴 핸들러가 직접 읽는다(`server/orchestrator/tools.py:735-738`의 근거를 계승 — "리그 섹션을 모델이 재타이핑하면 이름을 바꿔 적거나, 절단 신호를 떨어뜨리거나, 콘솔이 준 적 없는 번호를 공급할 수 있다"). 툴 인자는 **장르 식별자 하나**로 한정한다 — **캡처 형상은 인자가 아니다**(REQ-BUSKWIZ-006의 `shared_capture` 고정; `instantiate_look`이 `capture_shape`를 노출한 것은 단일 룩 경로의 선택이며 장르 번들에는 안전하지 않다).

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC **2.4.2**. 룰북 자산 버전 `server/rulebook/assets/v2.4.2/`.
- **기능 전제**: `SPEC-COPILOT-LOOKLIB-001`이 **completed** 상태로 출하되어 있고(`server/looks/{schema,roles,loader,resolver,instantiate,matching}.py` + `library/*.yaml` 32룩), `find_looks`/`instantiate_look` 툴이 등록되어 있다(`server/orchestrator/tools.py:40-47`). `related_specs`의 나머지 3건은 **비차단 참조**다 — DASHUI-001·EXECBODY-001은 completed이나 MVP-001은 in-progress이며, LOOKLIB이 같은 불균일을 정직하게 기술한 선례를 따른다(`LOOKLIB spec.md:157`).
- **기술 스택**: 신규 런타임 의존성 **0**. 순수 파이썬 + 기존 패키지 내부 확장.
- **콘솔측**: `console/lua/copilot_responder.lua` **무변경**. 인스턴스화는 이미 검증된 커맨드라인 패턴만 쓴다.
- **미검증 전제 (ASSUMPTION-n — LOOKLIB의 15 다음 번호 계승)**:
  - **ASSUMPTION-16** — grandMA3 2.4.2가 **페이지·익스큐터 저작 문법**을 수용하는가. 대상: 페이지 생성/라벨(`Store Page <n>` / `Label Page <n> '<name>'` 계열의 실제 수용 형태), 익스큐터 라벨링. **리포지토리 근거 0건**이며 유일 등장처 `server/measurement/corpus.yaml`은 스스로 mock 전용임을 선언한다(`:8-10`). M0에서 실측하며, 부정이면 REQ-BUSKWIZ-016이 DESCOPE된다.
  - **ASSUMPTION-17** — **비어 있는(미할당) 익스큐터를 열거하거나 판별**할 수 있는가. 현재 페이지 드릴다운은 **이미 존재하는 자식만** 열거하고(`server/web/dash.py:200-206`), 확인 실패한 후보는 "없음"과 "미확인"이 구별되지 않는다(`:210-231`). LOOKLIB은 "빈 익스큐터 탐색"을 명시적 Out of Scope로 두었다(`LOOKLIB spec.md:186`). M0에서 실측하며, 부정이면 REQ-BUSKWIZ-016이 DESCOPE된다.
  - **ASSUMPTION-18** — **다중 룩 단일 번들이 한 번의 `run_commands` 왕복에서 절단·타임아웃 없이 왕복**하는가. 규모는 추정이 아니라 실측이다 — §A "번들 규모의 실측"에 따라 **51~87행**이며 상한은 edm · 4풀 가용 시 **87행**이다. LOOKLIB M7 라이브가 실측한 최대 번들은 FALLBACK 형상 **21줄**이므로 미측정 구간은 약 4배다. M0에서 **실제 상한(87행)** 으로 실측하며, 함께 **중도 실패의 사후 상태**(stop-on-first-failure가 87행 번들에서 어느 지점에서 끊고 프로그래머 상태를 어떻게 남기는지 — REQ-BUSKWIZ-013 (e))를 기록한다. 부정이면 **번들 분할 정책**이 필요해지고, 그것은 사용자 확정 ③(단일 승인)과 충돌하므로 **M0 게이트에 사용자 결정 항목으로 기록**한다 — SPEC이 임의로 분할하지 않는다.
  - **ASSUMPTION-19** — **팔레트(프리셋)를 익스큐터에 얹는 문법이 존재하는가.** 라이브 검증된 유일한 바인딩 커맨드의 목적어는 시퀀스이며(`31_choreography_patterns.md:99`), 프리셋을 익스큐터에 직접 배치하는 형태는 **리포지토리 전체에서 0건**이다 — `Assign Preset`, `Preset <p>.<s> At (Executor|Page) <n>`, `Store Executor` 계열 전부 `server/`·`console/`·`docs/`에서 검색 결과 없음. 이것이 부정이면 본 SPEC의 산출물(프리셋)과 익스큐터 레이아웃 사이에 **연결 수단 자체가 없으므로** REQ-BUSKWIZ-016은 DESCOPE된다. 우회로(시퀀스를 만들어 거기에 프리셋을 담고 시퀀스를 배정)는 §D가 금지한다. M0에서 실측한다.
    - **기본 기대값은 부정(DESCOPE)이다 — M0는 그것을 뒤집을 기회이지 확인 절차가 아니다**: 근거 두 가지. (i) 룰북이 아는 프리셋 동사 4개가 **전부 프로그래머 쪽**이다 — `Store Preset`(`00_grammar.md:67`) · `Label Preset`(`:68`) · `Call Preset 4.1`(`:59`, "Recall an object into **the programmer**") · `At Preset 4.1`(`:72`, **선택**에 적용). 익스큐터 쪽 프리셋 동사는 하나도 없다. "grep 0건"보다 **어휘 자체가 프로그래머 쪽으로 닫혀 있다**가 더 강한 진술이다. (ii) 룰북이 이 공백을 스스로 메우는 방식이 곧 답이다 — `31_choreography_patterns.md:225-227`은 "`instantiate_look` creates presets only — no cue, no sequence, no executor assignment. Build whatever the operator has to FIRE afterwards with `run_commands`, **recalling the presets it reports**"라고 지시한다. 즉 "프리셋을 어떻게 발사하는가"에 대한 룰북 자신의 답은 "익스큐터에 얹어라"가 아니라 **"큐로 되불러라"**이고, 그 경로가 정확히 §D가 닫은 시퀀스·큐 생성이다.
- **측정된 기준선 (run-phase 킥오프에서 재측정 의무)**: 본 SPEC 착수 시점의 전체 스위트·커버리지 수치는 **plan-phase에서 인용하지 않는다**. LOOKLIB이 M1~M4에 걸쳐 baseline 3건 불일치를 규명하지 못한 전례(`LOOKLIB progress.md` M3/M4 baseline 주의 절)에 따라, 각 마일스톤은 **착수 직전 자신이 직접 실측한 수**에만 델타를 귀속시킨다.

## D. 제외 범위 (Out of Scope)

### Out of Scope — 포지션 프리셋 팔레트

- 제안서 :78이 P1-2 산출물로 적었으나 **선행 SPEC이 닫았다**: Position 풀은 "담을 것이 없다"는 이유로 v1 제외(`LOOKLIB spec.md:57`, `:192-194`), 정적 pan/tilt를 룩 데이터에 넣는 것은 사용자 확정 ①이 금지, `Pan`/`Tilt`는 무브먼트 지정 안에서만 등장하며 어떤 풀에도 귀속되지 않는다(`server/looks/schema.py:47` `MOVEMENT_ONLY_ATTRIBUTES`, `:62-69` 매핑에 부재). 본 SPEC은 그 결정을 번복하지 않는다 — 번복하려면 새 근거(리그별 포지션의 재사용 가능성 증명)와 라이브러리 자산 증보가 함께 필요하고, 그것은 본 SPEC의 조율 계층 범위 밖이다.

### Out of Scope — 무브먼트(페이저) 인스턴스화

- 스키마는 무브먼트 지정을 담지만 v1 라이브러리는 그 필드에 값을 넣지 않고(실측 0건), 번들 빌더도 읽지 않는다(`server/looks/instantiate.py`의 `_bundle`/`_plan_stores`에 `look.movement` 참조 0건). 페이저가 프리셋에 저장되는지는 리포지토리에 실측 근거가 없다(`LOOKLIB spec.md:62`). 본 SPEC은 이 상태를 **그대로 상속**하며 켜지 않는다.

### Out of Scope — 시퀀스 · 큐 생성

- 시퀀스/큐 저작 문법은 라이브 검증되어 있으나(`31_choreography_patterns.md:50`, `:55`, `:71`), 버스킹 준비의 산출물은 **팔레트**다. 시퀀스는 P1-1(송 구조 큐리스트 생성기)의 영역이며 별도 SPEC이다. REQ-BUSKWIZ-016이 GO되어 익스큐터 바인딩을 하게 되더라도 **바인딩 대상은 본 SPEC이 새로 만든 시퀀스가 아니라 이미 존재하는 오브젝트**여야 한다 — 그렇지 않으면 시퀀스 생성이 암묵적으로 범위에 들어온다.

### Out of Scope — P1-1 송 구조 큐리스트 생성기

- 음원 분석(구간/BPM/에너지), 타임코드 트랙·섹션 마커 생성, 곡당 시퀀스 자동화 전부. 타임코드 문법은 룰북 전체에서 **0건**이라 별도 라이브 프로브가 선행되어야 한다. 별도 SPEC.

### Out of Scope — 마법사 대화형 UX · 신규 화면

- 본 SPEC은 **기존 채팅 표면의 툴 1종**으로 노출된다. 전용 위저드 화면, 단계별 폼, 진행 표시기는 만들지 않는다. UI 무변경.

### Out of Scope — 사용자 커스텀 룩 저작 · 라이브러리 증보

- 장르 추가, 룩 추가·수정, 사용자 정의 팔레트 저작 UI. 본 SPEC은 출하된 32룩을 **소비**할 뿐이다.

### Out of Scope — `run_commands` dedupe 규칙 개정

- §A 하드 결함 2에 대한 본 SPEC의 답은 "개정하지 않는다"이며, 근거는 LOOKLIB M7 라이브 관측(`progress.md:799-805`)이다. `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(`:227-231`)와 dedupe 로직(`:526-550`)은 **무변경**이다. 본 SPEC이 `tools.py`에 하는 일은 신규 툴 1종의 등록뿐이다(REQ-BUSKWIZ-019).

## E. 참조 구현 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 참조 원본 (file:line) |
|---|---|
| 룩 1개 → 번들 빌더 (재사용 대상) | `server/looks/instantiate.py:416-423` `build_instantiation` |
| 리그 해석 2반쪽 (1회 해석의 대상) | `server/looks/resolver.py:121` `resolve_roles` · `server/looks/instantiate.py:217` `resolve_pools` |
| 빈 슬롯 선택 (원장이 감쌀 대상) | `server/looks/instantiate.py:307-312` `_first_free_slot` |
| 점유 미관측 ≠ 빈 풀 | `server/looks/instantiate.py:80-85`, `:346-357` |
| 충돌 = 건너뛰기 (라벨 대소문자·공백 무시) | `server/looks/instantiate.py:359-371` |
| 번들 발화 형태 (`Store Preset` / `Label Preset`) | `server/looks/instantiate.py:395-413` |
| 프로그래밍 규율 (`ChangeDestination Root` / `ClearAll`) | `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:9-23`, `:40-41` |
| in-scope 풀 패밀리 (상속 대상) | `server/looks/schema.py:58`, 매핑 `:62-69` |
| 장르 별칭 한/영 | `server/looks/matching.py:73-90` `GENRE_ALIASES`, `:197-207` `resolve_genre` |
| 툴 등록 표준 형태 | `server/orchestrator/tools.py:448-457`, `:1052-1060`; `server/llm/types.py:16-26` |
| 단일 스크리닝 경로 (`@MX:ANCHOR`) | `server/safety/gate.py:260-265`; 소비 선례 `server/orchestrator/tools.py:686-696` |
| 실행 프리뷰 severity 분류 | `server/web/preview.py:99-172`; 번들 등급 = 최고 severity `:198-203` |
| 익스큐터 바인딩 (라이브 검증된 유일 형식) | `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:99`, `:168` |
| 익스큐터 번호 확인 (날조 금지 경로) | `server/web/dash.py:129-143`, `:309-317` |
| 익스큐터 주소 하드코딩 금지 | `SPEC-COPILOT-EXECBODY-001/spec.md:69-70` REQ-EXECBODY-007/008 |
| GO/DESCOPE 라이브 프로브 패턴 | `SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123` AC-EXECBODY-010; 계승 선례 `LOOKLIB spec.md:45` |
| dedupe 탈락의 라이브 관측 | `SPEC-COPILOT-LOOKLIB-001/progress.md:799-805`, `:1167-1170` |
| 소비자 계약 원문 (본 SPEC의 근거) | `SPEC-COPILOT-LOOKLIB-001/research.md:226`; 예약 조항 `spec.md:70`, `:180-182` |
