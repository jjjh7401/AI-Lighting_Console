---
id: SPEC-COPILOT-PRECHK-001
title: "프리쇼 패치 점검 + 응답 확인 매크로 생성 (Pre-Show Patch Check)"
version: "0.1.0"
status: completed
created: 2026-07-29
updated: 2026-07-30
author: manager-spec
priority: P2
phase: "Phase 3 이후 차별화 기능 (P2 계층 착수)"
module: "server/prechk/ (신규), server/orchestrator/tools.py"
lifecycle: spec-anchored
tags: "patch, fixture, dmx-address, collision, macro, preshow, checklist, executor, page"
tier: L
related_specs: [SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-SONGCUE-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-DASHUI-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-PRECHK-001 — 프리쇼 패치 점검 + 응답 확인 매크로 생성

> **본 SPEC은 제안서 P2-6**(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:102-105`)**이며 P2 계층의 첫 항목이다.** P1 계층 3건(LOOKLIB 룩 어휘 · BUSKWIZ 다중 룩 조율 · SONGCUE 시간축)이 전부 `status: completed`로 닫힌 뒤 착수한다. 선행 3건이 **저작**(쇼파일에 무엇을 만드는가)을 다뤘다면 본 SPEC은 **점검**(쇼파일에 이미 있는 것이 정합한가)을 다룬다 — 읽기가 주된 축인 첫 SPEC이다.
>
> **범위는 제안서 원문과 다르다.** 착수 전 조사가 제안서의 전제 2건을 거짓으로 확인했고 사용자가 재범위를 승인했다(2026-07-29). 근거 전문은 `research.md` §3이며, 그 귀결이 아래 §A와 §D다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-07-29 | manager-spec | 최초 작성 (draft, Tier L). 출처는 제안서 P2-6. **아티팩트 6종**(spec/plan/acceptance/design/research/progress). 조사 방법은 병렬 read-only scout 4개 + **비파괴 라이브 사전 프로브**이며 후자가 요구 3건의 성립 여부를 착수 전에 갈랐다(`research.md` §2). 사용자 재범위 확정 1건(무응답 자동 탐지 DESCOPE), ASSUMPTION **6건**(25~30), REQ **20건**, clarification 마커 **0건**. **승인 대기 1건** — `server/safety/**` PRESERVE의 조건부 예외(프로퍼티 조회가 프로덕션 경로로 도달 불가하며 초크포인트 확장이 강제된다, `research.md` §7.4). 승인 절차는 `plan.md`의 사용자 접점이 소유한다. |

---

## A. 개요

**한 줄**: 쇼 시작 전에 *"패치가 정합한가"*를 콘솔에서 읽어 판정하고, *"픽스처가 실제로 응답하는가"*는 사람이 눈으로 확인할 **매크로를 만들어 준다.**

전자는 기계가 끝까지 답할 수 있고, 후자는 **응답기가 하드웨어 피드백을 수집하지 않으므로** 기계가 답할 수 없다(`research.md` §3.2). 본 SPEC은 그 경계를 흐리지 않는다 — **자동화할 수 있는 것만 자동화하고, 나머지는 사람이 판단할 도구를 만든다.**

### 사전 확정 사실 (사용자 확정 — 재질의 금지)

1. **무응답 픽스처 자동 탐지는 범위 밖이다.** 제안서 원문이 요구했으나 관측 경로가 저장소 전체에서 0건이며, 두 조사가 독립적으로 같은 결론에 도달했다(`research.md` §3.2). **명시적 DESCOPE이고 실패가 아니다.** 우회(발화 후 무반응 시간을 응답 실패로 간주하는 등)는 금지다 — 그 시간은 아무것도 관측하지 않은 시간이다.
2. **BUSKWIZ 후속 측정 4건을 본 SPEC의 라이브 세션에 함께 상정한다.** `ASSUMPTION-28`(G1 페이지·익스큐터 저작 문법) · `ASSUMPTION-29`(빈 익스큐터 식별) · `ASSUMPTION-30`(`Assign Preset … At Executor` 효과 + `page × 100 + slot`의 page ≥ 2 일반화). 라이브 세션 1회의 실제 비용은 실물 콘솔·사람 일정 확보이지 항목 하나를 더 발화하는 한계비용이 아니다.
3. **응답기(`console/lua/**`)는 변경하지 않는다.** 필요한 읽기 전량이 현재 `state`·`prop` 표면으로 달성됨을 사전 프로브가 실측했다(`research.md` §4). SONGCUE가 응답기를 확장한 것은 `plan.md`와 `spec.md`의 모순이라는 강제 사유 때문이었고, 본 SPEC에는 그 사유가 없다.

### 조사가 확립한 제약 — 본 SPEC이 이 위에 선다

선행 SPEC들이 "하드 결함"으로 불렀던 자리에, 본 SPEC은 **읽기 표면의 실측된 한계 4건**을 둔다. 셋은 조사가 닫았고 하나는 남아 있다.

1. **절단이 기본 경로다** (`research.md` §4.4 · §4.7). 픽스처 **19개**(반환 18개)에서 이미 `truncated = true`가 떴다 — 자식 수 상한(24)이 아니라 **페이로드 예산**(1900바이트)이 먼저 걸린다(`console/lua/copilot_responder.lua:634-639`). 패치 점검은 픽스처가 많은 것이 정상인 도메인이므로 절단 처리는 부가 기능이 아니라 **1급 요구**다.
2. **절단되어도 계수는 정확하다** (`research.md` §4.7). `node.childCount`는 참 전체 수이고(`console/lua/copilot_responder.lua:607`) 페이로드 루프는 목록만 자른다. **"몇 개인가"는 정확하고 "무엇인가"만 불완전하다** — 완전성을 `truncated` 플래그가 아니라 **읽은 개수와 `childCount`의 비교**로 판정한다.
3. **`ok = true`가 값의 유효성을 보증하지 않는다** (`research.md` §4.3). `prop <fixture> Index`가 `ok = true`와 함께 `'function: 0x105b0f048'`을 반환했다 — Lua 함수 참조다. 원인은 `safe_property`가 `handle[name]`을 그대로 돌려주는 것이다(`console/lua/copilot_responder.lua:204-217`). **값 형태 검증이 필수다.**
4. **`FID` 값의 의미는 이 쇼파일로 증명할 수 없다** (`research.md` §4.6). `console/lua/PROTOCOL.md:322-324`가 명시한다 — 현장 캘리브레이션 쇼파일은 슬롯 == FID라서 **올바른 FID 프로브와 슬롯 프로브를 구별할 수 없다.** 따라서 본 SPEC은 FID를 판정 근거로 쓰지 않는다.

---

## B. 요구사항 (GEARS)

### B.1 픽스처 인벤토리 읽기

- **REQ-PRECHK-001** `[Ubiquitous]` The 시스템 **shall** 픽스처 목록을 `Patch/Stages/1/Fixtures` 열거로 얻고, 각 픽스처의 속성은 **조사가 실측으로 확정한 프로퍼티명에 한정해** `prop`으로 읽는다 — `Patch` · `FixtureType` · `Mode` · `Name`(`research.md` §4.2). 그 목록 밖의 이름을 추측 발화하지 않는다. 응답기는 프로퍼티명을 열거할 수 없으므로(`console/lua/copilot_responder.lua:204-217`) 화이트리스트가 유일하게 안전한 형상이다.
- **REQ-PRECHK-002** `[Unwanted]` The 시스템 **shall not** `Patch/Fixtures` 또는 `DataPool/Presets` 경로를 사용한다 — 둘 다 2.4.2에서 **죽은 것으로 실측**되었다(`REQ-DASHUI-022`, `.moai/specs/SPEC-COPILOT-DASHUI-001/spec.md:82`). 선행 실측을 재확인하지 않고 판정을 계승한다.
- **REQ-PRECHK-003** `[Ubiquitous]` The 시스템 **shall** `prop` 응답의 `ok` 참만으로 값을 채택하지 않고 **기대 형태에 대해 검증**한다. 형태를 만족하지 않는 값은 **판독 실패**로 분류하고 판정에 쓰지 않으며, 그 사실을 리포트에 싣는다. 근거는 실측이다 — `ok = true`와 함께 Lua 함수 참조가 반환된 사례가 있다(§A 제약 3).
- **REQ-PRECHK-004** `[Event-driven]` **When** 열거의 **읽은 개수가 `node.childCount`보다 작으면**, the 시스템 **shall** 그 판정을 **불완전(incomplete)**으로 표시하고 **못 읽은 개수를 수치로** 리포트에 싣는다 — 불완전한 집합에 대해 "이상 없음"을 단정하지 않는다. 판정의 근거는 `truncated` 플래그가 아니라 **개수 비교**다(§A 제약 2).
- **REQ-PRECHK-005** `[Unwanted]` The 시스템 **shall not** 슬롯 번호를 FID로 취급하고, `FID`로 읽은 값을 **정합성 판정의 근거로 사용**하며, `Fixture <n>` 형태의 픽스처 선택 커맨드를 **생성**한다 — 세 금지가 모두 적용된다. 근거는 `REQ-LOOKLIB-008`(`.moai/specs/SPEC-COPILOT-LOOKLIB-001/spec.md:124`)과 `console/lua/PROTOCOL.md:305-324`다. `FID` 값은 `미확정` 표시와 함께 **참고로만** 리포트에 실을 수 있다.

### B.2 패치 정합성 판정

- **REQ-PRECHK-006** `[Ubiquitous]` The 시스템 **shall** `Patch` 값을 `<유니버스>.<주소>` 형태로 파싱해 **유니버스 정수와 주소 정수**로 정규화한다. 실측 표본은 `'1.001'` · `'2.351'`이다(`research.md` §4.5). 파싱 불가는 REQ-PRECHK-003의 판독 실패로 분류하며 **0이나 1 같은 기본값으로 채우지 않는다.**
- **REQ-PRECHK-007** `[Ubiquitous]` The 시스템 **shall** 같은 `(유니버스, 주소)` 시작점을 둘 이상의 픽스처가 점유하는 경우를 **주소 중복 충돌**로 판정하고, 충돌에 관여한 픽스처 전량을 **슬롯과 이름으로** 열거한다.
- **REQ-PRECHK-008** `[Option]` **Where** `ASSUMPTION-27`(픽스처 → 픽스처타입 → 모드 → 점유폭 연결)이 GO로 판정되면, the 시스템 **shall** 픽스처의 채널 점유 구간이 서로 겹치는 경우를 **구간 겹침 충돌**로 판정한다. 점유폭의 출처는 `Patch/FixtureTypes/<t>/DMXModes/<m>/DMXChannels`의 `childCount`다(`research.md` §4.7). **부정이면** 구간 겹침 판정을 수행하지 않고 그 **축소를 리포트에 명시**한다 — 주소 중복 판정(REQ-PRECHK-007)은 어느 판정에서도 수행된다.
- **REQ-PRECHK-009** `[Ubiquitous]` The 시스템 **shall** 픽스처타입·모드가 **판독 실패이거나 미확정인 픽스처를 정합 판정에서 제외**하고 그것을 **별도 부류**로 보고한다 — 정합으로도 부적합으로도 세지 않는다. 관측하지 않은 것에 판정을 붙이지 않는다.
- **REQ-PRECHK-010** `[Unwanted]` The 시스템 **shall not** 충돌이 0건인 것을 **정합성 증명으로 보고**한다 — 읽기가 불완전하면(REQ-PRECHK-004) "관측된 범위에서 충돌 0건"으로만 보고한다.

### B.3 응답 확인 매크로 생성

- **REQ-PRECHK-011** `[Event-driven]` **When** 사용자가 응답 확인 매크로 생성을 요청하면, the 시스템 **shall** **리그가 정의한 그룹을 하나씩 점등·소등하는** 매크로를 저작해 **사람이 콘솔에서 실행하고 눈으로 확인**할 수 있게 한다. 매크로의 목적은 판정이 아니라 **관측 보조**다.
  - **단위가 픽스처가 아니라 그룹인 이유는 강제된 것이다.** 픽스처를 개별 선택하려면 FID가 필요하고, `FID` 값의 의미는 현재 쇼파일로 증명할 수 없어 판정 근거에서 배제했다(REQ-PRECHK-005, `research.md` §4.6). 슬롯을 FID로 대신 쓰는 것은 `REQ-LOOKLIB-008`이 금지하며 조용히 틀린 리그를 선택한다. **따라서 "픽스처별 응답 확인"은 본 SPEC의 산출물이 아니다** — 슬롯 ≠ FID로 패치된 쇼파일이 준비되면 후속 SPEC이 그 단위를 연다.
  - 검증 가능한 형상: 그룹 **1개당 점등·소등 1쌍**이며 대상 그룹 수와 커맨드 쌍 수가 일치한다(AC-PRECHK-010 ④).
- **REQ-PRECHK-012** `[Option]` **Where** `ASSUMPTION-26`(매크로 저작 문법)이 GO로 판정되면, the 시스템 **shall** M0가 실측한 리터럴로만 매크로를 저작한다. **부정이면** 매크로 대상 커맨드를 **0건** 발화하고, `progress.md` M0 절에 `DESCOPE: ASSUMPTION-26 <사유>` 형태의 **접두 행**이 존재한다.
- **REQ-PRECHK-013** `[Unwanted]` The 시스템 **shall not** 픽스처 선택에 `Fixture <n>`을 사용한다(REQ-PRECHK-005) — 매크로는 리그가 이미 정의한 **그룹**을 대상으로 하거나, 그것이 불가능하면 매크로를 생성하지 않고 사유로 답한다. 슬롯을 FID로 오인하는 경로를 만들지 않는 것이 유일하게 안전한 형상이다.
- **REQ-PRECHK-014** `[Unwanted]` The 시스템 **shall not** 매크로 실행 결과를 응답 여부의 증거로 해석한다 — `Macro <n>` 실행의 `ok`는 **커맨드가 접수되었다**는 뜻이고 픽스처가 점등했다는 뜻이 아니다(`console/lua/copilot_responder.lua:690-706`).

### B.4 보고

- **REQ-PRECHK-015** `[Ubiquitous]` The 리포트 **shall** 집계와 **픽스처별 2단**을 함께 싣는다 — (a) 관측된 픽스처 전량의 슬롯·이름·주소·타입, (b) 충돌 부류별 목록, (c) 판독 실패 목록과 사유, (d) 완전성(읽은 개수 / `childCount` / 못 읽은 개수), (e) 수행하지 않은 판정과 그 사유(축소·DESCOPE). **집계만 내고 픽스처별을 생략하는 것은 금지다** — 어느 픽스처가 문제인지 사용자가 알 수 없게 된다.
- **REQ-PRECHK-016** `[Ubiquitous]` The 리포트의 **집계 수치는 픽스처별 목록의 합과 일치**해야 하며 불일치는 실패다. 관측된 모든 픽스처가 정확히 한 번 판정에 나타난다. 판정 어휘는 **닫힌 집합**이다.
- **REQ-PRECHK-017** `[Ubiquitous]` 사용자 대면 문자열 **shall** 한국어이며 매핑은 **표현 계층 코드**에 둔다. 라벨 재사용은 `server/looks/report.py`의 **공개 접근자**를 통하며 밑줄 식별자를 직접 import하지 않는다 — SONGCUE 결정 I의 계승이다.

### B.5 실행 경로 · 경계

- **REQ-PRECHK-018** `[Ubiquitous]` 콘솔 발화가 필요한 경우 the 시스템 **shall** 기존 `run_commands` → `bundle_gate.screen()` 경로로**만** 실행한다. 신규 REST 라우트 · 웹소켓 메시지 타입 · `execution_port` 직접 접근 **0건**. 신규 툴은 그 경로의 **호출자**이며 제2 실행 표면이 아니다.
- **REQ-PRECHK-019** `[Ubiquitous]` 프로퍼티 조회 the 시스템 **shall** **단일 초크포인트를 경유**한다 — `server/safety/`의 조회 메서드를 통하며 신규 모듈은 `server.bridge`를 **직접 import하지 않는다**. 이는 `REQ-MVP-029`의 계승이고 `server/tests/test_architecture.py:48-61`이 기계로 강제한다. 초크포인트 확장의 승인 상태는 §C PRESERVE의 조건부 예외가 소유한다.
- **REQ-PRECHK-020** `[Unwanted]` The 시스템 **shall not** 프로퍼티 조회를 위해 `server/tools/`의 운영 유틸 예외 목록에 파일을 추가한다 — 그 예외는 운영 유틸용이며 프로덕션 기능 경로가 아니다(`server/tests/test_architecture.py:33-39`). 기능을 유틸로 위장하는 것은 경계를 우회하는 것이다.

---

## C. 환경 및 전제

### 측정된 기준선

착수 SHA `95687a0`에서 **직접 실측**한 값은 `uv run pytest server/tests/ -q` → **2490 passed · 5 skipped · 0 failed**다. 전체 스위트 수는 **각 마일스톤이 착수 직전 직접 실측**하며 **이월 인용을 금지**한다.

라이브 세션 조건도 실측했다: onPC 2.4.2, 응답기 `CopilotResponder` **v1.5.0**, OSC **send 8000 / receive 9005**(기본 9000이 아니다 — 이 값을 읽지 않아 선행 SPEC이 오진 1건을 냈다, `.moai/specs/SPEC-COPILOT-BUSKWIZ-001/progress.md:191`). 쇼파일 규모는 픽스처 18 · 픽스처타입 1 · 그룹 4 · 매크로 1 · 페이지 1이다(`research.md` §4 · §5).

### 미검증 전제 (ASSUMPTION)

번호는 선행 SPEC 이후를 이어받는다(SONGCUE가 `ASSUMPTION-20~24`를 썼다).

- **ASSUMPTION-25** — **픽스처 주소 읽기.** `prop <fixture> Patch`가 `<유니버스>.<주소>` 형태의 값을 준다. 사전 프로브가 `'1.001'`을 포함해 **19개 중 관측된 18개**를 읽었으므로(`research.md` §4.2 · §4.5) 판정은 **GO 방향**이며 M0는 **재확인만** 한다. 부정이면 결과 어휘 `REOPEN_SCOPE`이며 **폐쇄가 아니다** — 오케스트레이터 접점으로 올려 범위를 재개정한다(`acceptance.md` AC-PRECHK-016의 결과 어휘 표).
- **ASSUMPTION-26** — **매크로 저작 문법.** `Store Macro <n>`과 라인 추가(`Set Macro <m>.<line> Property 'Command' '<cmd>'`)가 수용되고 **효과가 재조회로 확인된다.** 현재 등급 **T3** — 룰북에만 있고 라이브 `OK` 기록이 **0건**이다(`research.md` §5). **본 SPEC의 유일한 블로킹 전제다** — 부정이면 산출물 2(매크로 생성)가 성립하지 않는다. 차단 대상: 매크로 생성 마일스톤.
- **ASSUMPTION-27** — **픽스처 → 픽스처타입 → 모드 → 점유폭 연결.** 픽스처가 주는 `FixtureType`·`Mode`는 **표시 문자열**이고 경로 인덱스가 아니다(`research.md` §4.7). 연결 경로가 표시 문자열 파싱 없이 확립되는가. **동작 축소 — 블로킹 아님**: 부정이면 구간 겹침 판정만 빠지고 주소 중복 판정은 남는다(REQ-PRECHK-008).
- **ASSUMPTION-28** — **페이지·익스큐터 저작 문법의 존부** (BUSKWIZ G1 / `ASSUMPTION-16` 승계). BUSKWIZ가 *"결정적 테스트가 쇼파일 쓰기를 요구하고 그 결과가 v1 판정을 바꾸지 못한다"*는 이유로 미측정으로 남긴 항목이다. **본 SPEC은 쓰기 세션을 어차피 갖는다.** 차단 대상: 없음(본 SPEC의 산출물이 아니라 선행 SPEC의 미결을 닫는다).
- **ASSUMPTION-29** — **빈 익스큐터의 식별.** BUSKWIZ는 미점유 인덱스를 어떤 주소형으로도 해석하지 못해 DESCOPE했다. **`ASSUMPTION-28` 조건부** — 그것이 안전한 테스트 익스큐터를 확보할 때만 측정한다.
- **ASSUMPTION-30** — **`Assign Preset … At Executor <n>`의 효과와 `page × 100 + slot`의 page ≥ 2 일반화.** 전자는 파싱만 확인됐고 효과가 미검증이며(BUSKWIZ G2), 후자는 page 1만 재확인됐다(BUSKWIZ G5). 현재 페이지 풀 자식이 **1개**이므로(`research.md` §5) `ASSUMPTION-28`의 페이지 생성 없이는 측정 불가다. **`ASSUMPTION-28` 조건부.**

> **`FID` 값의 의미는 ASSUMPTION이 아니다.** 어떤 라이브 세션도 현재 쇼파일로 그것을 닫을 수 없다 — `console/lua/PROTOCOL.md:322-324`가 슬롯 ≠ FID로 패치된 쇼파일을 검증 조건으로 명시한다. 그것은 사용자의 GUI 작업을 요구하는 **선행 조건**이며 본 SPEC은 그것을 기다리지 않고 FID를 판정 근거에서 배제한 형상으로 출하한다(REQ-PRECHK-005, `research.md` §10.2).

### PRESERVE — 무변경 대상

`server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `server/looks/library/` · `server/web/preview.py` · **`console/lua/**`** · `server/rulebook/assets/v2.4.2/**` · `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 dedupe 실행 루프 · **`server/safety/**` — 단 아래 한 가지 예외(승인·집행 완료)**.

> **`server/safety/**`의 조건부 예외 — 강제된 것이며 사용자 승인을 요구했다.** 본 SPEC의 1차 산출물은 픽스처 **주소**를 읽어야 하고 주소는 **프로퍼티에만** 있다(`research.md` §4.2). 그런데 프로퍼티 조회(`prop`)는 **프로덕션 경로로 도달할 수 없었다** — OSC 송신 표면을 import할 수 있는 디렉터리가 `server/bridge/` · `server/safety/` · `server/tests/` 셋으로 **테스트에 의해 강제**되고(`server/tests/test_architecture.py:27-39`, `server/tests/test_architecture.py:48-61` — `REQ-MVP-029`), `build_prop_query`에는 프로덕션 소비자가 **0건**이었다. 즉 신규 모듈은 구조적으로 프로퍼티를 읽을 수 없고, 유일한 경로는 **초크포인트에 조회 메서드를 추가하는 것**이었다. 우회 4종을 전수로 배제한 근거는 `research.md` §7.4다.
>
> **예외의 범위는 순수 추가 4지점으로 한정한다** — `server/safety/console.py`에 `query_property`(기존 `query_state`와 동형) · `server/orchestrator/ports.py`에 대응 포트 프로토콜 · `server/safety/gate.py`에 위임 노출 · 테스트 대역 1건. **기존 심볼·시그니처는 무변경**이며 게이트의 스크리닝 의미론과 `REQ-MVP-029`의 단일 초크포인트 원칙은 **강화된다**(새 읽기가 초크포인트 밖으로 새지 않는다).
>
> **이 예외는 승인되고 집행됐다 (승인 2026-07-29 · 집행 2026-07-30).** `plan.md`의 사용자 접점이 승인 절차를 소유했고 승인 기록은 `progress.md` §F의 사용자 접점 표다. M1이 4지점을 순수 추가로 집행했으며 그 hunk 내역은 `progress.md` §E.2의 M7 절이 전수로 적는다 — `server/safety/console.py`는 hunk 3개 전부 순수 추가(삭제 0행)이고 `server/safety/gate.py`는 추가 2개와 독스트링 1행 정정이다. **금지 항목(기존 심볼·시그니처 변경 · 프로토콜 변경 · 스크리닝 의미론 변경)에 해당하는 hunk는 0건**이며 `AC-PRECHK-015` ③이 그것을 기계로 확인한다. 목록 밖의 `server/safety/**` hunk는 여전히 실패로 판정된다.
>
> **거부 분기는 발동하지 않았다.** 승인이 거부되면 1차 산출물이 성립하지 않아 범위 재조정이 필요했고 그 분기는 `plan.md`가 적었으나, 승인으로 해소됐다. 이 문장을 지우지 않고 남기는 이유는 절차적이다 — 조건부 예외가 **어떤 조건으로** 열렸는지가 후속 SPEC이 같은 예외를 요구할 때의 선례다.

`server/looks/report.py`는 **재사용하되 확장 가능**하다(REQ-PRECHK-017의 공개 접근자) — 다만 선행 SPEC의 테스트가 그 계약을 고정하므로 파괴적 변경은 즉시 회귀로 드러난다.

> **`console/lua/**`를 다시 PRESERVE로 두는 근거를 명시한다.** BUSKWIZ가 잠갔고(`.moai/specs/SPEC-COPILOT-BUSKWIZ-001/spec.md:56`) SONGCUE v0.2.0이 `plan.md`와의 모순 때문에 풀었다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md:245-246`). **본 SPEC에는 그 강제 사유가 없다** — 사전 프로브가 필요한 읽기 전량을 현재 `state`·`prop` 표면으로 달성했다(`research.md` §4). 이 문장을 남기는 이유는 절차적이다: SONGCUE에서 오케스트레이터가 `plan.md`의 좁은 목록만 보고 이 정본 절을 읽지 않아 응답기 변경을 지시한 실수가 있었고, **잠금·해제의 근거가 문서에 없으면 그 실수가 반복된다.**

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — 무응답 픽스처 자동 탐지

**제안서 원문이 요구했으나 관측 경로가 존재하지 않는다.** `build_exec_result`는 `pcall(Cmd, command)` 하나를 감싸 그 결과 문자열을 분류할 뿐이고 **픽스처 하드웨어 피드백을 수집하는 코드가 없다**(`console/lua/copilot_responder.lua:690-706`). 동사 디스패치 표가 `ping` · `state` · `prop` · `exec` · `deploy` **5종으로 닫혀 있어**(`console/lua/copilot_responder.lua:884-946`) 텔레메트리 동사를 추가할 자리도 없다. 룰북·선행 실측 전수에서도 판정 커맨드가 **0건**이다(`research.md` §3.2).

**사용자 확정 ①로 DESCOPE이며 실패가 아니다.** 본 SPEC이 대신 주는 것은 산출물 2 — 사람이 눈으로 확인할 매크로다.

### Out of Scope — DMX 출력값 판독

응답기의 읽기 표면은 오브젝트 트리 `state`와 단일 프로퍼티 `prop` 둘뿐이며 출력·DMX 스트림 동사가 없다(`research.md` §3.2). 출력값을 읽어 "실제로 무엇이 나가고 있는가"를 판정하는 것은 응답기 확장을 요구하고, 그것은 사용자 확정 ③이 배제했다.

### Out of Scope — 쇼파일 파일 직접 파싱

파서가 존재하지 않으며(`research.md` §3.1) 디스크의 export 스냅샷은 **라이브 상태가 아니다** — BUSKWIZ가 OSC 설정 XML을 근거로 삼아 오진한 실측 선례가 있다(`.moai/specs/SPEC-COPILOT-BUSKWIZ-001/progress.md:191`). 모든 읽기는 라이브 응답기를 경유한다.

### Out of Scope — 패치 수정 · 주소 재배치

본 SPEC은 **판정하고 보고**한다. 충돌을 발견해도 주소를 옮기지 않는다 — 패치 변경은 리그의 물리 배선과 결합된 결정이고 되돌리기 비용이 크다. 자동 재배치는 별도 SPEC이며 그 SPEC은 먼저 "무엇이 올바른 배치인가"를 정의해야 한다.

### Out of Scope — 익스큐터·페이지 저작 기능

`ASSUMPTION-28`~`ASSUMPTION-30`은 **측정 대상이지 산출물이 아니다.** 본 SPEC은 그 판정을 `progress.md`에 기록해 후속 SPEC에 넘기며, 페이지·익스큐터를 저작하는 **기능**을 만들지 않는다. BUSKWIZ가 그 축을 v1에서 닫은 판정은 유효하다.

---

## E. 참조 구현

| 참조 | 좌표 | 무엇을 계승하는가 |
|---|---|---|
| 2단 보고 형상 | `server/looks/report.py` | 집계 + 개체별 2단, 사유 부류 분리, 한국어 라벨을 코드 표에 두는 형상 |
| 단일 실행 경로 앵커 | `server/orchestrator/tools.py`의 `instantiate_look` · `prepare_busking` · `prepare_songcue` | 신규 툴이 `run_commands`의 **호출자**임을 문서화한 선례 |
| 읽기 조회 경로 | `server/web/dash.py` | 풀 열거 · 절단 신호 전파 · `meta.console_no` fail-closed 관례 |
| 라이브 프로브 드라이버 | `.moai/state/verify/songcue-m0/probe.py` | M0가 재사용한다(`.gitignore` 대상이므로 판정은 `progress.md`에 전재한다) |
| DESCOPE 접두 행 규약 | `.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md` §E.2 | `DESCOPE: ASSUMPTION-nn <사유>` 행 존재를 기계 판정으로 삼는 형상 |
