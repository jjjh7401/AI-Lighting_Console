---
id: SPEC-COPILOT-LOOKLIB-001
title: "연출 어휘 계층 — 룩 라이브러리 (Look Library)"
version: "0.2.0"
status: draft
created: 2026-07-26
updated: 2026-07-26
author: manager-spec
priority: P1
phase: "Phase 2 연출 계층 (v1.2.0 target)"
module: "server/looks/ (신규), server/orchestrator/tools.py, server/rulebook/assets/v2.4.2/"
lifecycle: spec-anchored
tags: "look-library, choreography, presets, groups, rig-context, nl-matching, genre-templates, design-layer, safety-gate"
tier: L
related_specs: [SPEC-COPILOT-MVP-001, SPEC-COPILOT-DASHUI-001, SPEC-COPILOT-EXECBODY-001]
---

# SPEC-COPILOT-LOOKLIB-001 — 연출 어휘 계층 (룩 라이브러리)

> **본 SPEC은 제안서 P1-3(연출 어휘 계층)의 구현이자 로드맵 Phase 2 목표("'코러스에서 금색 톤으로 웅장하게' 수준의 추상 지시를 리그에 맞게 실행", product.md:38)의 실체화다.** 현재 앱은 문법 계층(자연어→커맨드/큐/프리셋/Lua)이 완성되어 있으나, "무엇을 만들지 아는" 연출 계층이 비어 있다(제안서 §2 격차 분석). 본 SPEC은 그 첫 조각 — 추상 무드 지시를 **컬러·강도·빔·역할 조합의 '룩'**으로 변환하는 디자인 지식 레이어 — 를 만든다. P1-1(송 구조 큐리스트 생성기)·P1-2(버스킹 마법사)가 이 어휘를 공통 기반으로 소비할 예정이므로, 룩 스키마는 그 소비를 전제로 설계된다(research.md §10).
>
> **로드맵 위치의 정직한 표기 (감사 D17)**: 본 SPEC이 충족하는 성공 기준은 Phase 2의 것(product.md:38)이지만, 그 수단인 **"장르별 룩 템플릿"은 로드맵상 Phase 3 산출물**이다(product.md:39). 즉 본 SPEC은 **Phase 3 산출물을 앞당겨 착지시켜 Phase 2 성공 기준을 충족시키는** 구조이며, frontmatter의 `phase: "Phase 2 연출 계층"` 표기는 그 충족 대상 기준을 가리킨다 — Phase 3 항목을 Phase 2로 재분류한다는 뜻이 아니다.
>
> **빔 축의 출처 정정 (감사 D18)**: "빔"을 v1 속성 축에 포함한 근거는 P1-3이 아니라 **제안서 P1-2**의 "컬러/포지션/빔 프리셋 팔레트"(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:78`)다. P1-3 본문이 나열한 축은 "앵글·컬러·강도·무브먼트"(:84)이며 빔을 포함하지 않는다. 본 SPEC은 P1-2의 축 하나를 P1-3 어휘 계층으로 끌어와 대체했고(앵글 → 역할 추상, +빔), 그 치환을 여기에 기록한다. 이 치환이 D2(빔 attribute 어휘 부재)의 발원지다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-26 | manager-spec | 최초 작성 (draft, Tier L). 출처: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` §3 P1-3. 사용자 사전 확정 3건(§A) 반영: ① v1 속성 범위(컬러/강도/빔 구체값 + 포지션 역할 추상), ② 내장 장르 4종(워십/록/발라드/EDM, 장르당 약 6~10룩), ③ v1 = 데이터 계층 + MA3 인스턴스화 + 자연어 매칭 전부(완결된 사용자 기능). 아티팩트 6종(spec/plan/acceptance/design/research/progress) 동시 생성. |
| 0.2.0 | 2026-07-26 | manager-spec | **독립 감사(FAIL 0.65 / Tier L 기준 0.85) 반영 개정.** 감사를 권위로 수용하고 원문을 방어하지 않는다. (a) **D2** — REQ-001/003 상호 충족 불가 해소: 빔 attribute 문자열은 리포지토리 전체에서 0건 실측(`Dimmer`/`ColorRGB_R,G,B`/`Pan`/`Tilt` 6종만 존재)이므로 M0 라이브 프로브 게이트로 이관, REQ-003은 프로브 대기 부분집합 + Pan/Tilt 용도 한정으로 개정. §A의 빔 그룹핑 오류(zoom은 Beam이 아니라 Focus — `10_object_model.md:39`) 정정. (b) **D5** — `server/web/preview.py` 안전 계층(스트로브 `danger` 분류) 연구 누락 보강, 데이터 흐름·위험표·교차참조 반영. (c) **D3/D13** — 역할 어휘의 사전 근거 부재 실측 확인 후 "신규 어휘"로 정정, REQ-006을 명명 관례 *스타일* 준수로 재진술(PRESERVE 파일 무변경). (d) **D6/D8** — 마커↔슬롯 1:1 주장 정정, 마커 ①⑤ 리포지토리 증거로 폐쇄, 다이내믹스 척도를 명시 결정으로 승격. (e) **D4/D12** — 미커버 REQ-006/013/014/016/021에 AC 신설 + REQ↔AC 역추적표 도입. (f) **D7** — REQ-010 범위 누출(장르 묶음) 제거. (g) **D9** — M1 과적재 분해 + M0 라이브 프로브 신설(EXECBODY M1-GO 패턴), 라이브 세션 2회로 정정. (h) **D10/D11/D14/D15/D17/D18** 및 인용 정정(`tools.py:231-272`). 사용자 확정 4건(§A) 추가 반영. |

## A. 개요

룩(Look)은 하나의 무대 그림을 만드는 속성 조합이다: 어떤 역할의 조명(백라이트/FOH 워시/사이드…)이, 어떤 컬러·강도·빔 상태로, 어떤 무브먼트를 하는가. 본 SPEC은 (1) 장르별 룩 템플릿을 담는 **구조화 데이터 계층**, (2) 역할 추상을 사용자 리그의 실제 그룹으로 매핑해 콘솔에 프리셋/데모 시퀀스로 만들어 넣는 **MA3 인스턴스화**, (3) "웅장한 금색 코러스" 같은 채팅 지시를 룩으로 매칭해 적용하는 **자연어 매칭**까지를 v1로 정의한다.

아키텍처 전제: **기존 파이프라인 전면 재사용**. 룩 데이터는 서버측 신규 패키지의 정적 자산이 단일 진실원이고(고정 룰북 프리픽스에는 구조화 룩 데이터를 넣지 않는다 — research.md §2), 리그 인식은 기존 `get_rig_context` 데이터 형상을, 인스턴스화는 라이브 검증된 프로그래밍 커맨드 패턴(룰북 31)을, 실행은 기존 안전 게이트의 유일한 스크리닝 경로(`gate.screen()`, gate.py:260-265 `@MX:ANCHOR`)를 그대로 사용한다. 콘솔측 Lua(`copilot_responder.lua`)는 무변경이다.

### 사전 확정 사실 (합의된 접근 — 재질의 금지)

- **v1 룩 속성 범위**: 컬러·강도는 **구체값**으로; 포지션은 **역할 기반 추상**(역할 어휘 집합은 미확정 — plan.md §A.4 마커 1)으로 표현하고 인스턴스화 시점에 사용자 리그의 그룹으로 매핑한다 — 하드 pan/tilt 값을 룩 데이터에 넣지 않는다 (사용자 확정 ①).
- **빔 축: v1 범위 유지 + M0 라이브 프로브 선행** (사용자 확정 ④, 감사 D2): 빔은 v1 속성 축에서 **빠지지 않는다**. 단, 그 커맨드 문법이 리포지토리 어디에도 실측 근거를 갖지 않으므로(아래 실측 참조) **라이브러리 저작 착수 전 실물 콘솔 프로브로 attribute 문자열을 실측**한다 — `SPEC-COPILOT-EXECBODY-001`의 M1 GO/DESCOPE 라이브 프로브 패턴 계승(`SPEC-COPILOT-EXECBODY-001/acceptance.md:117-123` AC-EXECBODY-010). 프로브는 plan.md §B의 **M0**이며, ASSUMPTION-15가 그 대상이다.
  - **실측 근거 (재확인)**: `grep -rhoE "Attribute '[A-Za-z_0-9]+'" server/ console/ docs/` → `ColorRGB_B` / `ColorRGB_G` / `ColorRGB_R` / `Dimmer` / `Pan` / `Tilt` **6종만**. `grep -rn 'Zoom\|Strobe\|Shutter\|Iris' server/rulebook/assets/v2.4.2/` → **0건**(산문에도 없음). 빔 계열 attribute 문자열은 이 프로젝트에 존재하지 않는다.
  - **그룹핑 오류 정정**: v0.1.0 본문은 빔을 "스트로브/줌 등"으로 예시했으나, `10_object_model.md:39`는 **zoom을 Focus 패밀리**(`Focus (zoom/focus)`)로, Beam은 `Beam (iris/prism/frost)`로 분류한다. 줌은 Beam이 아니다. M0 프로브는 패밀리 경계와 무관하게 **실제 수용되는 `Attribute '<Name>'` 문자열**을 측정한다.
  - **스트로브/셔터의 v1 사전 결정 규칙**: `server/web/preview.py:131-139`가 `strobe|shutter|hz`를 **`severity="danger"`**("스트로브/셔터 변화" — 관객·카메라 직접 영향)로 분류하며, 이 분류는 스크리닝되는 모든 번들에 대해 발화한다(§E 표 참조). 따라서 **v1 라이브러리는 스트로브/셔터를 기본 제외한다.** 포함은 (a) M0 프로브의 문법 실측 성공 **그리고** (b) 매 인스턴스화가 danger 프리뷰를 유발함을 알고도 포함하겠다는 사용자 결정이 M0 게이트에 기록될 때에만 성립한다 — 둘 중 하나라도 없으면 제외가 유지된다. 이는 미해결 질문이 아니라 **기본값이 정의된 폐쇄 결정**이다.
- **v1 내장 장르**: 워십, 록, 발라드, EDM 4종. 장르당 약 6~10룩으로 섹션 다이내믹스(잔잔함→클라이맥스)를 스팬한다 (사용자 확정 ②).
- **v1 범위**: 라이브러리 데이터 계층 + MA3 인스턴스화(콘솔에 프리셋 생성) + 자연어 매칭("웅장한 금색 코러스" 채팅 지시 → 룩 매칭·적용) **전부 v1** — 데이터 계층만이 아니라 완결된 사용자 대면 기능이다 (사용자 확정 ③).
- **프리셋 슬롯 배정: 런타임 빈 슬롯 탐색** (사용자 확정 ⑤): 고정 예약 대역도, 사용자 설정값도 쓰지 않는다. 인스턴스화 시점에 기존 드릴다운 쿼리 상한(`RIG_DRILLDOWN_QUERY_CAP = 16`, `server/orchestrator/tools.py:88`) 안에서 점유를 실측해 빈 슬롯을 고른다. 근거: 이 프로젝트가 반복 학습한 "검증되지 않은 관례를 하드코딩하지 않는다" 원칙 — 고정 대역은 그 자체가 미검증 관례다.
- **인스턴스화 산출물: 프리셋만** (사용자 확정 ⑥): v1은 데모 시퀀스도, 익스큐터 바인딩도 만들지 않는다. 익스큐터 주소 체계는 이 프로젝트가 두 번 데인 영역이므로 범위 밖으로 유지한다(§D).
- **기존 프리셋 충돌: 건너뛰고 명시 보고** (사용자 확정 ⑦): 덮어쓰지 않고, 재슬롯도 하지 않는다. 충돌 항목은 건너뛰고 "N개 건너뜀"을 명시 보고한다 — 본 SPEC의 정직한 축소 원칙(plan.md §A.3)과 동일 방향.
- **스키마는 P1-1/P1-2의 공통 기반**: 섹션 다이내믹스는 순서 있는 축으로, 인스턴스화 **API 형상**은 룩 단위/장르 묶음 단위 모두 표현 가능하게 설계한다. 단 **장르 묶음 인스턴스화의 런타임 실행은 v1 범위 밖**이다(§D, 감사 D7) — v1은 스키마 형상만 예약한다 (제안서 §3, research.md §10).
- **안전 철학 계승**: AI는 초안 생성·사람이 확정(product.md §6). 룩 적용은 기존 게이트·승인 카드·실행 프리뷰·LiveLock 제안 강등 플로우를 그대로 소비한다.

### ⚠️ 역할 매핑의 명시적 한계 — 그리고 역할 어휘가 **신규**라는 사실

**정정 (감사 D3/D13).** v0.1.0 본문은 포지션 역할 어휘가 `20_korean_terms.md`의 showfile 행에 "이미 확립된 사전 기반"을 갖는다고 서술했다. **이는 사실이 아니다.** 실측:

- `20_korean_terms.md`는 36행이며, 그 showfile 행은 **샤막 / 워시 / 무빙 / 스팟 / 빔 / 핀조명·폴로스팟 / 객석등**(:11-16, :29)이다 — 이들은 전부 **픽스처 타입 클래스**(Wash-class, Spot/Profile-class, Beam FixtureType…)이지 무대 위 **공간적 포지션 역할**이 아니다.
- `백라이트` / `FOH` / `사이드` / `스페셜`은 `server/`·`console/`·`docs/`·`ui/`·`.moai/project/` 전체에서 **매치 0건**이다.

따라서 본 SPEC의 포지션 역할 어휘는 **신규로 도입되는 어휘**다. 기존 사전을 상속하지 않으며, 그 구성은 아직 미확정이다(plan.md §A.4 마커 1). 다만 어휘를 *새로 만든다*는 사실이 명명 방식까지 자유롭게 만들지는 않는다 — 신규 역할 이름은 `20_korean_terms.md` showfile 행의 **명명 관례 스타일**(한국어 현장어 1급 + 영어 병기 + `Group named like 'X'/'한국어'` 형태의 매핑 서술)을 따른다. 이는 **스타일 준수이지 그 파일에 행을 추가하는 것이 아니다** — `20_korean_terms.md`는 PRESERVE 대상이며(plan.md §A.5) 본 SPEC은 이 파일을 수정하지 않는다.

역할→그룹 매핑 자체는 사용자 쇼파일의 **그룹 명명 관례**(예: 'Wash', '워시', 'Back', '백라이트' 류)에 기반한 휴리스틱이다. 이름 관례가 전혀 없는 리그에서는 역할이 매핑되지 않을 수 있으며, 그 경우 시스템은 **매핑 실패를 명시적으로 보고하고 해당 역할을 제외한 채 진행하거나 중단**한다 — 절대 임의의 그룹·픽스처를 추측해 대입하지 않는다(룰북 `31_choreography_patterns.md:190-191` "NEVER invent a `Group 3` that `get_rig_context` did not list", 슬롯≠FID gotcha). 이는 의도된 트레이드오프이며 UI 응답에도 명시된다. 휴리스틱이 실제로 통하는지는 **미검증**이며 M0 프로브에서 실측한다(ASSUMPTION-13).

## B. 요구사항 (GEARS)

### B.1 룩 데이터 계층 (스키마 + 내장 라이브러리)

- **REQ-LOOKLIB-001** [Ubiquitous] — 룩 스키마 **shall** 다음 축을 정의한다: 아이덴티티(안정적 look id, 표시 이름, 한국어 별칭/무드 키워드), 장르, **순서 있는 섹션 다이내믹스 레벨**(척도는 plan.md §A.4 마커 2에서 확정), 속성 페이로드(컬러·강도 구체값 + **빔 구체값(M0 프로브 게이트)**), **역할 기반 포지션 목록**, 선택적 무브먼트(페이저) 지정. 스키마는 명시적 `schema_version`을 가지며, P1-1(다이내믹스 축 소비)·P1-2(장르 묶음 인스턴스화 API 형상)가 소비 가능한 형상이어야 한다(research.md §10).
  - **빔 축의 게이트 (REQ-003과 한 쌍 — 따로 충족될 수 없다)**: 빔 속성이 스키마에 실제 값으로 등장하는 것은 **ASSUMPTION-15가 M0 프로브에서 긍정 실측된 경우에 한한다.** 부정 실측(수용되는 빔 attribute 문자열 없음) 시 스키마는 빔 필드를 **정의하되 v1 라이브러리에서 미사용**으로 두고, 그 사실을 progress.md에 기록한다(plan.md §A.3 정직한 축소). 스키마 필드의 존재 자체는 P1-2 소비 계약이므로 유지된다.
- **REQ-LOOKLIB-002** [Ubiquitous] — 내장 라이브러리 **shall** 워십/록/발라드/EDM 4개 장르를 제공하고, 각 장르는 6~10개 룩으로 섹션 다이내믹스 스펙트럼을 스팬하며, 장르와 다이내믹스 레벨은 기계적으로 조회 가능한 축이다. "스팬"의 판정 기준은 plan.md §A.4 마커 2가 확정하는 다이내믹스 척도의 **최저 단계와 최고 단계를 각각 1개 이상 포함**함이다.
- **REQ-LOOKLIB-003** [Ubiquitous] — 룩의 속성 페이로드 **shall** 아래 3구간으로 나뉜 어휘만 사용한다. 미검증 attribute 이름이 **프로브 대기 표시 없이** 라이브러리에 등장하는 것은 금지된다.
  1. **실측 확정 어휘 (무조건 허용)** — `Attribute 'Dimmer'`, `Attribute 'ColorRGB_R'/'ColorRGB_G'/'ColorRGB_B'` + 검증된 페이저/MAtricks 문법(`31_choreography_patterns.md:33-39, 61-94`). 리포지토리 실측으로 존재가 확인된 어휘.
  2. **용도 한정 어휘 — `Attribute 'Pan'` / `Attribute 'Tilt'`** — **무브먼트(페이저) 지정 안에서만** 허용된다(예: `Attribute 'Pan' At Phase 0 Thru 360`, `31_choreography_patterns.md:69`). **정적 포지션 값으로는 금지**된다 — 하드 pan/tilt는 §A 사용자 확정 ①과 REQ-LOOKLIB-009가 금지하는 대상이다. v0.1.0의 평면 나열은 이 구분을 하지 않아 "허용 집합이 금지 대상을 포함"하는 모순을 만들었다(감사 D2).
  3. **프로브 대기 어휘 (M0 게이트)** — 빔 계열(ASSUMPTION-15). 라이브러리 저작 시점에 M0 실측 결과로 확정된 문자열만 진입한다. M0 이전에는 스키마·자산 어디에도 구체 빔 문자열을 쓰지 않는다. 스트로브/셔터는 §A의 사전 결정 규칙에 따라 **기본 제외**다.
- **REQ-LOOKLIB-004** [Unwanted] — 룩 데이터 **shall not** per-show 값(구체 그룹 번호, 프리셋 슬롯 번호, FID, 익스큐터 번호)을 포함한다 — 리그 바인딩은 오직 인스턴스화 시점에 일어난다(20_korean_terms.md:31-36 분리 원칙 계승).
- **REQ-LOOKLIB-005** [Event-driven] — **When** 라이브러리가 로드되면, the 로더 **shall** 스키마를 검증하고 위반(미지 필드/역할/attribute, 다이내믹스 범위 이탈, 중복 look id)을 명시적 에러로 보고한다 — 부분적으로 깨진 라이브러리를 조용히 서빙하지 않는다.

### B.2 역할 기반 포지션 추상화 + 리그 매핑

- **REQ-LOOKLIB-006** [Ubiquitous] — 포지션 역할 **shall** 스키마에 정의된 **폐쇄 어휘**로만 표현되며(집합 자체는 plan.md §A.4 마커 1이 Kickoff 전에 확정), 각 역할은 한국어·영어 별칭을 갖는다. 이 어휘는 **신규**다(§A 정정) — `20_korean_terms.md`의 showfile 행에는 대응 행이 존재하지 않는다. 따라서 본 요구는 그 파일과의 *행 단위 정합*을 요구하지 않으며, **명명 관례 스타일**(한국어 현장어 1급 + 영어 병기 + `Group named like 'X'/'한국어'` 형태의 매핑 서술)의 준수만을 요구한다. **`20_korean_terms.md`를 포함한 룰북 자산 4파일은 무변경이다**(plan.md §A.5 PRESERVE) — 본 요구는 어떤 PRESERVE 파일의 수정도 유발하지 않는다.
- **REQ-LOOKLIB-007** [Event-driven] — **When** 룩 인스턴스화 또는 매칭이 리그 매핑을 요구하면, the 리졸버 **shall** 기존 `get_rig_context` 데이터 형상(`rig_object`/`rig_section`, tools.py:185-230 — 실제 풀 번호 `no` 키잉)의 groups 섹션에서 실존 그룹만을 후보로 사용하고, `truncated`/`path_not_resolved`/`console_unreachable` 신호를 매핑 결과에 전파한다.
- **REQ-LOOKLIB-008** [Unwanted] — the 리졸버 **shall not** fixtures 섹션의 번호를 FID로 취급해 `Fixture ... Thru ...` 범위를 합성하지 않으며(슬롯≠FID, tools.py:33-36), rig context에 등재되지 않은 그룹 번호·이름을 발명하지 않는다(룰북 31:184-191).
- **REQ-LOOKLIB-009** [Event-driven] — **When** 어떤 역할이 리그의 어느 그룹에도 매핑되지 않으면, the 시스템 **shall** 그 역할을 **명시적 미매핑(unmapped)으로 보고**하고, 해당 역할에 대한 콘솔 커맨드를 생성하지 않는다 — 미매핑 역할을 위한 하드 pan/tilt 값 합성·임의 그룹 대입은 금지된다.

### B.3 MA3 인스턴스화 (게이트 경유)

- **REQ-LOOKLIB-010** [Event-driven] — **When** 사용자가 **하나의 룩**에 대한 인스턴스화를 지시하면, the 시스템 **shall** 라이브 검증된 프로그래밍 패턴으로 커맨드 번들을 구성해(**프리셋 저장 + Label만** — 사용자 확정 ⑥) **기존 `run_commands` → `gate.screen()` 경로로만** 실행한다 — 제2 실행 경로·신규 REST 실행 엔드포인트·OSC 표면 직접 import는 구성상 금지된다. **장르 묶음의 런타임 일괄 인스턴스화는 v1 범위 밖이며**(§D P1-2, 감사 D7) 스키마의 API 형상 예약에 그친다.
- **REQ-LOOKLIB-011** [Ubiquitous] — 인스턴스화 번들 **shall** 검증된 프로그래밍 규율을 따른다: 번들 선두 `ChangeDestination Root` 1회(31:9-23), 각 룩 캡처 전과 각 `Store` 후 `ClearAll`(트래킹 오염 방지, 31:40-41, 128-134), 생성 오브젝트마다 `Label`로 사람이 읽을 이름 부여(00_grammar.md:66-68 레시피).
- **REQ-LOOKLIB-012** [Unwanted] — 인스턴스화 **shall not** 어떤 경로로도 `Store /Overwrite`를 발화하지 않으며, 점유된 슬롯을 **재슬롯하지도 않는다**. 충돌 처리는 **건너뛰기 하나**다(사용자 확정 ⑦). `Store /overwrite`는 블랙리스트 항목(`server/safety/blacklist.yaml:18`)으로 승인 보류를 유발하고, `server/web/preview.py:113-121`은 이를 `severity="caution"`("덮어쓰기")으로 분류한다 — 두 방어 모두 우회 대상이 아니라 하한선이다.
- **REQ-LOOKLIB-013** [Event-driven] — **When** 인스턴스화가 완료되면, the 시스템 **shall** 다음을 구조화 요약으로 보고한다: (a) 생성된 프리셋의 풀·슬롯·이름, (b) **미매핑 역할 목록**, (c) **충돌로 건너뛴 항목 수와 그 슬롯**("N개 건너뜀" — 사용자 확정 ⑦), (d) 드릴다운 캡 도달 시 `drilldown_capped` 표시. 부분 성공을 전체 성공으로 위장하지 않는다. 이 보고 형상은 라이브 세션과 독립적으로 유닛 레벨에서 검증 가능해야 한다(AC-LOOKLIB-018).
- **REQ-LOOKLIB-014** [Where] — **Where** 생성형 Lua 플러그인 경로(`31_choreography_patterns.md:136-171`)가 인스턴스화 구현에 사용되는 빌드에서, the 룩 계층 **shall** 그 경로의 모든 발화를 기존 배포 파이프라인(pcall compile → destructive `Cmd()` scan → 사람 리뷰 게이트, `server/deploy/pipeline.py:5-12`)을 **무변경으로** 경유시키고, 파이프라인을 우회하는 제2 배포 표면을 갖지 않는다.
  - **[Where]의 의미 (감사 D11 정정)**: v0.1.0의 표현("**Where** 인스턴스화가 … 사용하면")은 GEARS `Where`를 이벤트 트리거처럼 썼고, "쓰면 쓰는 대로 한다"는 동어반복이라 검증 불가였다. `Where`는 **역량 게이트**(빌드에 그 경로가 존재하는가)이며, 검증 대상은 "우회 표면이 존재하지 않는다"는 **정적 성질**이다 — AC-LOOKLIB-016이 이를 확인한다. v1 산출물이 프리셋만이므로(사용자 확정 ⑥) 이 경로는 **v1에서 사용되지 않을 전망**이며, 그 경우 AC-LOOKLIB-016은 "우회 표면 0건"으로 여전히 참이다(공허하게 참이 아니라, 정적 부재를 실제로 확인한다).

### B.4 자연어 매칭

- **REQ-LOOKLIB-015** [Event-driven] — **When** 채팅 지시가 추상 무드/장르/섹션 표현(예: "웅장한 금색 코러스", "잔잔한 발라드 인트로")을 담으면, the 시스템 **shall** 룩 라이브러리의 무드 키워드/별칭/장르/다이내믹스 축에 대해 매칭을 수행하고, 매칭된 룩을 기존 채팅 파이프라인(단일 지시 턴, session.py:354)을 통해 제안·적용한다.
- **REQ-LOOKLIB-016** [Ubiquitous] — 매칭의 단일 진실원 **shall** 구조화 룩 라이브러리 데이터이며, the 매칭 표면 **shall** 제공자 중립(anthropic/gemini 공통 툴·프롬프트 표면, factory.py:17-28)으로 동작한다. 매칭 결과가 만드는 최종 콘솔 커맨드는 항상 게이트를 경유한다(REQ-LOOKLIB-010).
- **REQ-LOOKLIB-017** [Event-driven] — **When** 어떤 룩도 신뢰할 만하게 매칭되지 않으면, the 시스템 **shall** 기존 룰북 무드 폴백(31:173-206 "Concept / mood instructions")으로 강등한다 — 라이브러리 히트를 조작하거나 무관한 룩을 강제 매칭하지 않으며, 폴백 경로 자체는 무변경으로 보존된다.
- **REQ-LOOKLIB-018** [Ubiquitous] — 매칭 **shall** 한국어 우선으로 동작한다: 룩의 무드 키워드/별칭은 한국어 현장 어휘를 1급으로 포함하고, showfile 종속 용어는 기존 20_korean_terms.md 관례(어휘 클래스 → rig context 실체 조회)를 따른다.

### B.5 안전·캐시 규율 계승

- **REQ-LOOKLIB-019** [Ubiquitous] — 스크리닝 경로 **shall** 정확히 하나만 존재한다(gate.py:260-265 `@MX:ANCHOR` + classify.py:169 분류 의미론 단일). 룩 관련 신규 모듈 **shall not** OSC 송신 표면(`server/bridge/`)을 import하지 않는다(`test_architecture.py` 통과가 증거).
- **REQ-LOOKLIB-020** [State-driven] — **While** LiveLock이 활성인 동안, 룩 인스턴스화·적용 **shall** 제안(Proposal) 전용으로 강등되고 콘솔 송신은 0건이다(lock.py:23, gate.py:318-321 lock-FIRST 재확인 계승).
- **REQ-LOOKLIB-021** [Ubiquitous] — 기존 안전 불변식 전부 **shall** 무변경 유지된다: health gate, 문법 검증, 위험 분류(개방형 타깃 승인 보류 포함), deny-all 기본 승인 포트, 위험 커맨드 사전 쇼파일 백업 fail-closed, 미확인 이력 재승인·자동 재전송 금지, **그리고 스크리닝 전 실행 프리뷰 발화**(`_ObservingBundleGate.screen`, `server/web/session.py:161-165` — 프리뷰는 `gate.screen()` 호출을 **감싸고** 있으며 룩발 번들도 예외 없이 이를 거친다) — 본 SPEC은 `gate.screen()` 파이프라인과 그 관찰 래퍼를 소비만 하고 수정하지 않는다.
- **REQ-LOOKLIB-022** [Unwanted] — 고정 룰북 프리픽스 **shall not** per-show/per-turn 값 또는 구조화 룩 데이터 본문을 담는다 — 룰북 자산 변경이 있다면 정적 안내 텍스트에 한정되며(assembly.py:1-15 byte-stability 계약), 그 변경은 배포 시점 1회의 캐시 무효화로 수렴해야 한다.

## C. 환경 및 전제 (Environment / Assumptions)

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 동일 머신 로컬 공존. OSC `127.0.0.1` UDP. site config(`osc_slot=2`, `receive_port`, `reply_port`)는 항상 effective 값에서 읽는다 — 하드코딩 금지.
- **기능 전제**: MVP-001 파이프라인(4-툴 레지스트리, `gate.screen()` 단일 관문, 승인/제안 카드, `_last_created` 크로스턴 메모리), `get_rig_context` 10경로 + 드릴다운(라이브 캘리브레이션 완료, tools.py:53-55), 룰북 31 프로그래밍 패턴(전부 라이브 검증), DASHUI-001 채팅 표면. 모두 구현·라이브 검증 완료 상태이며 `related_specs`(비차단)로 참조한다 — 엄격 충족(completed) 전제의 pre-flight 차단 회피 선례(SHOWUI-001·EXECBODY-001 §C) 계승.
- **기술 스택**: 기존 스택 그대로 — 서버: FastAPI + python-osc + pytest, UI: React + Vite + Vitest(단, 본 SPEC은 UI 무변경 목표). **신규 런타임 의존성 0**(YAML을 쓸 경우 PyYAML은 이미 의존성 — ruleset.py:16).
- **콘솔측**: `console/lua/copilot_responder.lua` **무변경**. 인스턴스화는 커맨드라인 패턴으로 표현하며, 생성형 Lua 경로를 쓰더라도 배포 파이프라인의 기존 계약만 소비한다.
- **미검증 전제 (ASSUMPTION 규율, EXECBODY-001 ASSUMPTION-12 다음 번호 계승)** — **세 건 모두 M0 라이브 프로브에서 실측**한다(plan.md §B M0). v0.1.0은 이들을 M6(최종 라이브)에서만 검증하도록 배치해, **전제에 의존하는 저작 작업이 검증보다 먼저 오는 순서 결함**이 있었다(감사 D9). M0가 그 순서를 뒤집는다.
  - **ASSUMPTION-13 (그룹 명명 관례 기반 역할 매핑 실효성)**: 실제 사용자 쇼파일의 그룹 이름이 역할 휴리스틱(한/영 관례 어휘)으로 유의미하게 매핑된다. **미검증** — M0에서 실물 리그의 groups 목록을 판독해 실측하며, 실패 방향은 명시적 미매핑 보고(REQ-LOOKLIB-009)로 안전하다. 부정 실측 시 역할 어휘 집합(마커 1)의 확정 근거가 바뀌므로 **M1 착수 전에 알아야 한다**.
  - **ASSUMPTION-14 (`Store Preset`의 속성 선택 캡처 의미론)**: 프로그래머에 활성화된 값으로 `Store Preset <pool>.<slot>`을 실행하면 해당 풀 타입에 맞는 속성이 캡처된다는 `00_grammar.md:66-68` 레시피가 onPC 2.4.2에서 풀 타입별로 기대대로 동작한다. 레시피는 룰북에 있으나 `31_choreography_patterns.md`처럼 "validated" 표기가 없으므로 **미검증으로 취급** — M0 실측 항목. 부정 실측 시 인스턴스화 번들의 형상 자체가 바뀌므로 M3 착수 전에 알아야 한다.
  - **ASSUMPTION-15 (빔 계열 attribute 문자열의 실재 — 신설, 감사 D2)**: onPC 2.4.2가 수용하는 빔/줌 계열 `Attribute '<Name>'` 문자열이 존재하며 값 범위가 확인 가능하다. **미검증** — 리포지토리 전체 실측 결과 빔 계열 attribute 문자열은 **0건**이다(§A 실측 근거). M0에서 후보 문자열(`'Zoom'`, `'Focus'`, `'Iris'`, `'Frost'`, `'Prism1'`, 그리고 §A 규칙에 따라 v1 제외 대상이지만 문법만 측정할 `'Shutter'`)을 실물 콘솔에 발화해 수용 여부·값 범위를 실측한다. 부정 실측 시 REQ-LOOKLIB-001의 빔 게이트가 발동한다(필드 정의 유지 + v1 라이브러리 미사용).
- **측정된 기준선 (감사 D15 갱신)**: 브랜치 `feat/lighting-direction-features`, HEAD **`fd59163`**. 본 SPEC의 아티팩트 6종은 **전부 git에 추적·커밋되어 있다**(`8325b9b` 최초 작성, `fd59163` 잔여 런타임 상태 파일 untrack). v0.1.0이 기록한 "HEAD `81e2232` / 파일은 워킹 트리에만 존재"는 그 시점의 사실이었으나 **지금은 낡았다**. run-phase 킥오프 시점에 신선한 pytest/vitest 기준선을 재측정한다(baseline-integrity 원칙).

## D. 제외 범위 (Out of Scope)

### Out of Scope — P1-1 송 구조 큐리스트 생성기

- 음원 분석(구간/BPM/에너지), 타임코드 트랙·섹션 마커 생성, 곡당 시퀀스 자동화 전부. 본 SPEC은 그 소비자를 위한 스키마 형상만 예약한다(research.md §10). 별도 SPEC.

### Out of Scope — P1-2 버스킹 준비 마법사

- "이 리그로 버스킹 준비해줘" 일괄 팔레트 + 익스큐터 페이지 레이아웃 생성. **장르 묶음 인스턴스화는 스키마의 API 형상만 예약하고 런타임 실행은 만들지 않는다**(REQ-LOOKLIB-010, 감사 D7). 마법사 UX·페이지 레이아웃도 별도 SPEC.

### Out of Scope — 데모 시퀀스 · 익스큐터 바인딩

- 룩을 "눌러볼 수 있게" 하는 데모 시퀀스 생성(`Store Sequence ... Cue ...`), 빈 익스큐터 탐색, `Assign Sequence ... At Executor ...` 바인딩 일체. v1 산출물은 **프리셋만**이다(사용자 확정 ⑥). 익스큐터 주소 체계는 SHOWUI-001·EXECREF-001·EXECBODY-001이 반복해서 데인 영역이므로 v1에서 열지 않는다.

### Out of Scope — 스트로브 · 셔터 속성

- v1 라이브러리는 스트로브/셔터 값을 담지 않는다(§A 사전 결정 규칙). 근거: `server/web/preview.py:131-139`가 이를 `severity="danger"`(관객·카메라 직접 영향)로 분류하므로, 스트로브를 담은 룩은 **인스턴스화할 때마다 danger 등급 프리뷰를 유발**한다. M0 프로브는 문법만 실측하고, 라이브러리 진입은 별도 사용자 결정 사안이다.

### Out of Scope — 사용자 커스텀 룩 저작 UI

- 룩 생성/편집 UI, 온보딩 마법사. v1 라이브러리는 내장 4장르 템플릿이다(사용자 확정 ②). 스키마의 파일 수준 확장 가능성은 열어두되 저작 표면은 만들지 않는다.

### Out of Scope — 레퍼런스 이미지 → 룩 변환

- 무드보드/사진에서 팔레트·무드 추출(제안서 P3-7). 장기 항목.

### Out of Scope — UI 표면 변경

- `ui/src/**` 및 대시보드/패널 타일 추가(룩 전용 타일·팔레트 UI 포함). v1 자연어 매칭의 표면은 기존 채팅이며, 룩의 패널 노출은 기존 `_last_created` 핀 경로가 이미 제공하는 범위를 넘지 않는다.

### Out of Scope — 콘솔측 Lua 변경

- `copilot_responder.lua` 및 신규 콘솔측 프로토콜 동사 일체(research.md §7 기각 (c)).

### Out of Scope — 비게이트 실행 경로

- 실행용 REST 엔드포인트, 제2 스크리닝, 룩 모듈의 OSC 표면 직접 import(REQ-LOOKLIB-019, gate.py:260-265 ANCHOR).

### Out of Scope — 라이브 잠금 중 자율 적용

- LiveLock 활성 중 어떤 형태의 콘솔 송신도 없음 — 제안 카드 전용(product.md §6 비목표 계승).

### Out of Scope — 임베딩/벡터 검색 인프라

- 매칭을 위한 신규 검색 의존성 도입(research.md §7 기각 (b)). 매칭은 구조화 데이터 제시 + LLM 판단/키워드 축으로 해결한다.

## E. 참조 구현 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 참조 원본 (file:line) |
|---|---|
| 고정 프리픽스 byte-stability + 단일 조립 | `server/rulebook/assembly.py:1-15, 69-76` |
| 정적 어휘 클래스 vs 런타임 구체값 분리 원칙 | `server/rulebook/assets/v2.4.2/20_korean_terms.md:31-36` |
| 검증된 프로그래밍 규율(목적지/ClearAll/Store/Label) | `31_choreography_patterns.md:9-59`, `00_grammar.md:66-68` |
| 무드 폴백(매칭 실패 시 보존 대상) | `31_choreography_patterns.md:173-206` |
| rig 데이터 형상 + 실번호 키잉 + 드릴다운 | `server/orchestrator/tools.py:65-88, 185-230, 231-272` (`drill_into`는 **231**행에서 시작 — v0.1.0의 `233-265`는 오인용) |
| 실행 프리뷰(스크리닝을 감싸는 관찰 계층) | `server/web/session.py:161-165, 213, 236-244`, `server/web/preview.py:99-170` |
| 스트로브/셔터 = `danger`, Pan/Tilt·덮어쓰기 = `caution` | `server/web/preview.py:113-121, 131-139, 149-157`, 핀: `server/tests/test_web_preview.py:39-43` |
| 슬롯≠FID + 그룹 발명 금지 | `tools.py:33-36`, `31_choreography_patterns.md:184-191` |
| 툴 레지스트리 확장 지점 | `tools.py:23, 304`, `server/web/session.py:210` |
| 채팅 1턴 + 크로스턴 메모리 | `session.py:354, 202, 387-409` |
| 단일 스크리닝 경로 + 분류 단일 | `server/safety/gate.py:260-265`, `classify.py:169` |
| 충돌 경계(블랙리스트) | `server/safety/blacklist.yaml:15-18` |
| LiveLock + lock-FIRST | `server/safety/lock.py:23`, `gate.py:318-321` |
| 서버측 정적/런타임 데이터 선례 | `server/safety/blacklist.yaml`(정적 YAML), `server/web/panel.py:186-330`(런타임 JSON, 원자 쓰기) |
| 생성형 Lua 배포 파이프라인 | `server/deploy/pipeline.py:5-12`, `pack.py:60` |
| 제공자 중립 표면 | `server/llm/factory.py:17-28` |
