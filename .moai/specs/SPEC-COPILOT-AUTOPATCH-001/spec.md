---
id: SPEC-COPILOT-AUTOPATCH-001
title: "Vectorworks 연계 2단계 — 차이 리포트 승인 기반 자동 패치 생성 (AddFixtures Lua 플러그인)"
version: "0.1.0"
status: draft
created: 2026-08-05
updated: 2026-08-05
author: orchestrator
priority: P0
phase: "Vectorworks 연계 2단계 — 자동 패치 생성 (1단계 대조 리포트의 후속, MVR/GDTF는 3단계)"
module: "server/vwx/ (확장), server/orchestrator/tools.py (신규 툴 1종), server/prechk/ (재사용·무변경)"
lifecycle: spec-anchored
tags: "vectorworks, autopatch, addfixtures, lua-plugin, fid, fixturetype, dmxmode, approval-gate, idempotency, irreversible"
tier: L
related_specs: [SPEC-COPILOT-VWX-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-OVERLAP-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-AUTOPATCH-001 — Vectorworks 연계 2단계: 승인 기반 자동 패치

> **본 SPEC은 `SPEC-COPILOT-VWX-001`(1단계)의 직접 후속이다.** 1단계가 내는 차이 리포트의
> `missing_in_console`(도면에는 있으나 콘솔 실측에 없는 장비)을 입력으로 받아, **사람이 항목 단위로
> 승인한 것만** 라이브 검증된 Lua `AddFixtures` 기법으로 콘솔에 실제 패치한다.
>
> **1단계와 결정적으로 다른 점: 이 SPEC은 콘솔에 쓴다.** 1단계는 읽고 비교만 했다. 패치는
> 픽스처를 **생성**하며, 이 앱에는 아직 실행 취소·백업 복원 경로가 없다. 따라서 본 SPEC의 요구사항
> 절반 이상은 기능이 아니라 **되돌릴 수 없는 쓰기를 사람이 통제하게 만드는 장치**다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-05 | orchestrator | 최초 작성 (draft, Tier L). 출처는 `.moai/reports/ma3-copilot-overview.html` §7 P0 항목의 **2단계**와 `SPEC-COPILOT-VWX-001` §D `### Out of Scope — Lua AddFixtures 자동 패치`. **아티팩트 6종**(spec/plan/acceptance/design/research/progress). REQ **25건**(REQ-AUTOPATCH-001~025), AC **26건**, ASSUMPTION **5건**(71~75), 마일스톤 **9개**(M0~M8), 라이브 세션 **2회**(M0 프로브 · M8 종단), clarification 마커 **0건**. 위험 4건(FID 충돌 · FixtureType 핸들 해석 · 비가역성 · 멀티셀/액세서리)을 각각 요구·가정·마일스톤으로 구조화했다. **사용자 결정 대기 1건** — FID 배정 전략(§C `ASSUMPTION-71` 판정에 따라 분기). |

---

## A. 개요

**한 줄**: 1단계 차이 리포트에서 사람이 고른 장비만, 콘솔 라이브러리에서 확정한 FixtureType·DMXMode
핸들과 사용자가 명시한 빈 FID 범위를 써서, `deploy_plugin` 안전 파이프라인을 거친 Lua 플러그인으로
콘솔에 패치하고, **패치 직후 다시 읽어 실제로 그렇게 되었는지 확인**한다.

본 SPEC은 **생성만** 한다. 기존 픽스처의 수정·삭제·재주소는 §D가 배제한다.

### 사전 확정 사실 (조사 확정 — 재질의 금지)

1. **커맨드라인으로는 픽스처를 만들 수 없다.** 패치는 Lua `AddFixtures` 전용이며 정확히 2단계다 —
   ① `deploy_plugin(name, lua_source)` ② `run_commands(["Plugin 'YourName'"])`.
   2번 호출에는 **그 명령 하나만** 들어가고 작은따옴표를 쓴다(큰따옴표는 거부됨)
   (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:13-18`).
2. **`ChangeDestination`/`CD`를 어디에서도 보내면 안 된다** — 플러그인 안에서도, `run_commands`로도.
   `AddFixtures`는 콘솔의 **현재 command destination**(이미 patch fixtures 레이어)을 읽으며, CD를
   보내면 패치가 `nil`을 반환하고 아무것도 만들지 않는다. 패치가 안 되면 사용자에게
   **Patch > Fixtures 편집기를 먼저 열라고 안내**하는 것이 정답이다
   (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:20-29`).
3. **`AddFixtures{...}` 필드**: `mode`(필수, DMX 모드 핸들) · `amount`(필수, 정수) · `fid`(문자열) ·
   `idtype = "Fixture"` · `name`(문자열) · `patch`(선택, `{"universe.address"}`).
   **모드의 DMX footprint 만큼 간격을 두어야 겹치지 않는다**
   (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:31-38`, 워크된 예제 `:40-53`, stride 42).
4. **`deploy_plugin`은 이미 컴파일 검사 + 정적 스캔 + 사람 리뷰 파이프라인을 태운다**
   (`server/orchestrator/tools.py:1266`). 새 배포 경로를 만들지 않는다.
5. **콘솔로 나가는 유일한 통로는 `run_commands` → `bundle_gate.screen()`이다.**
   `server/tests/test_prechk_tool.py:330-343`의 AST 스캔이 `execution_port` 직접 호출을 금지한다.
6. **1단계는 이미 멀티셀을 접고 액세서리를 분류한다.** 도면 8행짜리 멀티셀 바는 **1대**로,
   DMX를 소비하는 액세서리는 **별도 장비**로, 비DMX 액세서리는 **제외**로 나온다
   (`SPEC-COPILOT-VWX-001` REQ-VWX-013~017). 본 SPEC은 그 분류를 신뢰하고 다시 세지 않는다.

### 조사가 확립한 제약 — 본 SPEC이 이 위에 선다

1. **콘솔의 기존 FID를 읽을 수 없다.** `server/prechk/inventory.py:57`
   `PROPERTY_WHITELIST = ("Patch","FixtureType","Mode","Name")` 4개뿐이고, 슬롯과 FID가 우연히
   일치하는 캘리브레이션 쇼파일에서는 **올바른 FID 프로브와 슬롯 프로브를 구별할 수 없다**
   (`console/lua/PROTOCOL.md:305-324`, REQ-PRECHK-005). 그런데 `AddFixtures`는 `fid`를 요구한다.
   → **FID 배정은 이 SPEC의 최대 난제이며 §B.2가 전담한다.**
2. **`FixtureType`·`Mode`는 표시 문자열이다.** `server/prechk/patch.py:14-22` — `ASSUMPTION-27`은
   **부정**이며, 표시명에서 인덱스를 파싱하는 것은 슬롯을 FID로 읽는 것과 같은 실수다.
   그러나 `AddFixtures`의 `mode`는 `Patch().FixtureTypes["<정확한 이름>"].DMXModes["<정확한 이름>"]`
   **정확한 핸들**을 요구한다. → **§B.3이 전담한다.**
3. **Vectorworks 타입명은 MA3 라이브러리 이름과 문자열이 일치하지 않는다.**
   실물 샘플에서 관측: VW `Fixture Type` = `Robe MegaPointe`, GDTF = `Robe Lighting@MegaPointe`.
   MA3 라이브러리 이름은 제3의 표기일 수 있다(`SPEC-COPILOT-VWX-001/research.md`).
4. **되돌릴 수 없다.** 자동 백업은 찍히지만 **복원 경로가 없고**, 잘못 만든 픽스처는 사람이 콘솔에서
   지워야 한다(`.moai/reports/ma3-copilot-overview.html` §7 P2). → **§B.5가 전담한다.**
5. **다중 유니버스 시스템(A–Z)에서는 콘솔 조인 자체가 미수행이다**
   (`SPEC-COPILOT-VWX-001` REQ-VWX-024, `multi_system_mapping_absent`). 조인이 없으면
   `missing_in_console`이 성립하지 않는다. → 패치 입력이 없으므로 **패치도 거부**한다.

---

## B. 요구사항 (GEARS)

### B.1 입력과 승인 게이트

- **REQ-AUTOPATCH-001** `[Ubiquitous]` The 패치 계획기 **shall** 1단계 차이 리포트의
  `missing_in_console` 항목만을 패치 후보로 삼는다 — 도면 파일을 스스로 다시 읽지 않고,
  콘솔 실측을 스스로 다시 하지 않는다. 입력의 출처는 언제나 1단계 산출물이다.
- **REQ-AUTOPATCH-002** `[Ubiquitous]` The 패치 계획기 **shall** 후보를 **항목 단위**로 제시하고,
  사용자가 **명시적으로 고른 항목만** 패치 대상에 넣는다. "전부 승인"은 항목 전수를 고른 것과
  같은 절차를 거치며, 기본 선택 상태는 **아무것도 선택되지 않음**이다.
- **REQ-AUTOPATCH-003** `[Ubiquitous]` The 패치 계획기 **shall** **드라이런을 기본 동작**으로 하여,
  생성될 Lua 소스 전문과 대상 장비 표(타입 · 모드 · FID · 유니버스 · 주소 · 점유폭)를 **먼저** 낸다.
  드라이런 산출물은 콘솔에 아무것도 보내지 않고 얻을 수 있어야 한다.
- **REQ-AUTOPATCH-004** `[Unwanted]` The 패치 실행기 **shall not** 사용자의 명시 승인 없이 콘솔에
  쓰기를 발생시킨다 — 드라이런 호출이 실행으로 승격되는 경로, 기본값이 실행인 인자,
  승인을 함축하는 재시도가 모두 금지된다.
- **REQ-AUTOPATCH-005** `[Ubiquitous]` The 승인 화면 **shall** **되돌릴 수 없음**을 명시한다 —
  "이 앱에는 실행 취소·백업 복원 경로가 없고, 잘못 생성된 픽스처는 콘솔에서 사람이 지워야 한다"를
  승인 시점에 보여준다.

### B.2 FID 배정 — 최대 난제

- **REQ-AUTOPATCH-006** `[Ubiquitous]` The FID 배정기 **shall** 사용자가 명시한 **빈 FID 범위**
  안에서만 FID를 배정한다. 범위는 호출 인자로 받으며 추론하지 않는다.
- **REQ-AUTOPATCH-007** `[Event-driven]` **When** 빈 FID 범위가 주어지지 않았으면, the 패치 실행기
  **shall** 패치를 **거부**하고 사유와 함께 무엇을 입력해야 하는지 안내한다 — 임의의 시작 번호나
  "가장 큰 슬롯 + 1" 같은 추정으로 진행하지 않는다.
- **REQ-AUTOPATCH-008** `[Unwanted]` The FID 배정기 **shall not** 콘솔 슬롯 번호를 FID로 사용하고,
  `get_rig_context`·`precheck_patch`가 준 번호를 FID로 해석하며, `fid_note`가 `미확정`인 값을
  배정 근거로 쓴다 — 세 금지가 모두 적용된다(REQ-PRECHK-005 계승).
- **REQ-AUTOPATCH-009** `[Where]` **Where** `ASSUMPTION-71`(FID가 콘솔에서 읽히는 프로퍼티인가)이
  **GO**로 판정되면, the FID 배정기 **shall** 배정 전에 **기존 FID와의 충돌 사전검사**를 수행하고
  충돌 시 해당 항목을 패치 대상에서 제외한다. **부정이면** 사전검사를 수행하지 않고
  그 **축소를 리포트에 명시**하며, 사용자가 준 범위의 정확성에 전적으로 의존함을 함께 알린다.
- **REQ-AUTOPATCH-010** `[Ubiquitous]` The FID 배정기 **shall** 배정 결과를 드라이런 표에 **전수
  나열**한다 — 어느 장비가 어느 FID를 받는지 사용자가 승인 전에 볼 수 있어야 한다.

### B.3 FixtureType · DMXMode 핸들 해석

- **REQ-AUTOPATCH-011** `[Ubiquitous]` The 타입 해석기 **shall** 콘솔 쇼파일의 픽스처 라이브러리를
  `Patch/FixtureTypes` 열거로 얻어 후보 집합을 만든다(`server/orchestrator/tools.py:202`) —
  라이브러리 이름을 코드에 상수로 박지 않는다.
- **REQ-AUTOPATCH-012** `[Ubiquitous]` The 타입 해석기 **shall** Vectorworks의 `Fixture Type`·
  `GDTF Fixture` 값을 콘솔 라이브러리 이름과 **퍼지 매칭**하고 **사용자 확인을 거쳐** 확정한다.
  문자열 동등 비교로 단정하지 않으며, 확정된 대응은 재사용 가능한 별칭으로 남긴다.
- **REQ-AUTOPATCH-013** `[Event-driven]` **When** 콘솔 라이브러리에 대응 FixtureType 또는 DMXMode가
  존재하지 않으면, the 패치 실행기 **shall** 그 항목의 패치를 **수행하지 않고** 사유를 구조화해
  보고한다 — GDTF 라이브러리 임포트가 선행되어야 함을 사용자에게 알린다(§D 참조).
- **REQ-AUTOPATCH-014** `[Ubiquitous]` The 모드 해석기 **shall** 선택된 DMXMode의 채널 점유폭이
  1단계가 읽은 `DMX Footprint`와 일치하는지 확인하고, 불일치를 **승인 전에** 사용자에게 제시한다 —
  멀티셀 장비에서 셀 수가 다른 모드를 고르면 주소 계획 전체가 어긋난다.
- **REQ-AUTOPATCH-015** `[Unwanted]` The 모드 해석기 **shall not** 표시 문자열에서 인덱스·채널 수를
  파싱해 모드를 특정한다(`ASSUMPTION-27` 부정 계승).

### B.4 Lua 생성

- **REQ-AUTOPATCH-016** `[Ubiquitous]` The Lua 생성기 **shall** `AddFixtures{ mode, amount, fid,
  idtype = "Fixture", name, patch }` 형태만 생성하고, `mode`는
  `Patch().FixtureTypes["<이름>"].DMXModes["<이름>"]` 핸들로, 공백이 든 이름은 대괄호 표기로 쓴다.
- **REQ-AUTOPATCH-017** `[Unwanted]` The Lua 생성기와 명령 생성기 **shall not** `ChangeDestination`
  또는 `CD`를 **어떤 형태로도** 산출물에 포함한다 — 플러그인 소스 안, `run_commands` 배열 안,
  주석 안의 실행 가능 코드가 모두 금지된다.
- **REQ-AUTOPATCH-018** `[Ubiquitous]` The 실행기 **shall** 플러그인 실행을
  `run_commands(["Plugin '<이름>'"])` **단일 명령 호출**로 보낸다 — 그 배열에 다른 명령을 함께 넣지
  않으며, 이름은 작은따옴표로 감싼다.
- **REQ-AUTOPATCH-019** `[Ubiquitous]` The 주소 계획기 **shall** 각 장비를 **해당 모드의 점유폭만큼
  간격**을 두어 배치하고, 1단계 도면이 지정한 유니버스·주소를 우선 사용한다. 도면 주소가 이미
  콘솔에서 점유되어 있으면 그 항목을 패치 대상에서 제외하고 사유를 보고한다 —
  임의의 빈 주소로 옮겨 붙이지 않는다.

### B.5 안전 · 멱등 · 검증

- **REQ-AUTOPATCH-020** `[Ubiquitous]` The 배포기 **shall** 기존 `deploy_plugin` 파이프라인
  (컴파일 검사 + 정적 스캔 + 사람 리뷰)을 그대로 경유한다 — 별도 배포 경로를 만들지 않는다.
- **REQ-AUTOPATCH-021** `[Unwanted]` The 패치 모듈 **shall not** `execution_port`를 직접 호출한다 —
  콘솔로 나가는 모든 문장은 `run_commands` → `bundle_gate.screen()`을 통과한다
  (`server/tests/test_prechk_tool.py:330-343`의 AST 스캔 대상).
- **REQ-AUTOPATCH-022** `[Ubiquitous]` The 패치 실행기 **shall** **멱등**하다 — 같은 승인 집합을 두 번
  실행해도 중복 픽스처를 만들지 않는다. 실행 전에 대상 주소·이름의 기존 점유를 재조회해 이미 존재하는
  항목을 건너뛰고, 건너뛴 사실을 보고한다.
- **REQ-AUTOPATCH-023** `[Ubiquitous]` The 패치 실행기 **shall** 실행 직후 `precheck_patch`로 **다시
  읽어**, 승인된 각 항목이 실제로 그 유니버스·주소에 그 타입으로 생성되었는지 확인하고 결과를
  건별로 보고한다 — 플러그인이 오류 없이 끝난 것을 성공의 근거로 삼지 않는다.
- **REQ-AUTOPATCH-024** `[Event-driven]` **When** 검증 읽기가 승인 항목과 어긋나면, the 패치 실행기
  **shall** 불일치를 구조화해 보고하고 **자동 재시도·자동 보정을 하지 않는다**. 생성된 픽스처가
  0건이면 "Patch > Fixtures 편집기를 먼저 열라"는 안내를 함께 낸다
  (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:28-29`).

### B.6 경계와 보고

- **REQ-AUTOPATCH-025** `[Event-driven]` **When** 1단계 리포트가 `multi_system_mapping_absent`
  등으로 콘솔 대조를 수행하지 않았거나 `diffs.performed`가 거짓이면, the 패치 실행기 **shall**
  패치를 **거부**한다 — 대조되지 않은 리포트에서 "빠진 장비"를 도출할 수 없다.

---

## C. 환경 및 전제

### 측정된 기준선

착수 SHA와 테스트 기준선은 `progress.md` §E.1이 **직접 실측한 값**으로 기록한다. 이월 인용하지 않는다.
1단계 완료 시점 실측치는 **4,898 passed · 7 skipped**(`SPEC-COPILOT-VWX-001` v0.1.7)이며, 본 SPEC의
착수 기준선은 그 이상이어야 한다.

### 미검증 전제 (ASSUMPTION)

전역 카운터를 이어 **71부터** 시작한다(`SPEC-COPILOT-VWX-001`이 68~70을 소비했다).

- **ASSUMPTION-71** — 콘솔에서 픽스처의 **FID를 프로퍼티로 읽을 수 있다.** 현재
  `PROPERTY_WHITELIST`는 4개뿐이고 슬롯==FID 우연일치 쇼파일에서는 프로브를 구별할 수 없다
  (REQ-PRECHK-005). **M0 라이브 프로브 대상.** 부정이면 REQ-AUTOPATCH-009의 충돌 사전검사가
  descope되고, 사용자가 준 FID 범위의 정확성에 전적으로 의존한다.
- **ASSUMPTION-72** — `Patch/FixtureTypes` 열거가 **DMXModes까지 드릴다운**되어 모드 이름과 채널
  점유폭을 얻을 수 있다. `server/prechk/patch.py:22`가 그 경로
  (`Patch/FixtureTypes/<t>/DMXModes/<m>/DMXChannels`)를 언급하지만 실측되지 않았다.
  **M0 라이브 프로브 대상.** 부정이면 REQ-AUTOPATCH-014의 점유폭 일치 확인이 불가능해지고
  모드 선택은 전적으로 사용자 확인에 의존한다.
- **ASSUMPTION-73** — `AddFixtures`의 `patch` 배열로 준 **다중 유니버스 주소**가 그대로 적용된다.
  룰북의 워크된 예제는 단일 유니버스(`"1." .. addr`)만 검증했다. **M0 라이브 프로브 대상.**
- **ASSUMPTION-74** — 패치 직후 `precheck_patch` 재조회에서 **신규 픽스처가 관측된다**(콘솔 캐시나
  갱신 지연 없이). REQ-AUTOPATCH-023의 검증 읽기가 여기에 의존한다. **M0 라이브 프로브 대상.**
- **ASSUMPTION-75** — Patch 편집기가 열려 있지 않은 상태를 **패치 전에 감지**할 수 있다.
  감지 가능하면 사전에 안내할 수 있고, 불가능하면 실패 후 안내만 가능하다(REQ-AUTOPATCH-024).
  **M0 라이브 프로브 대상.**

### PRESERVE — 무변경 대상

`git diff --stat <BASE>..HEAD -- <아래 목록>`이 **빈 출력**이어야 한다. `<BASE>`는 `progress.md` §E.1이
실측 기록한 착수 SHA다.

- `console/lua/**` — 콘솔 상주 응답기
- `server/safety/**` — 안전 게이트
- `server/prechk/**` — 8개 파일 전량. 본 SPEC은 `precheck_patch`를 **소비**하지 변경하지 않는다
- `server/paperwork/**`
- `server/looks/**`

`server/vwx/**`는 **확장 대상이므로 PRESERVE가 아니다.** 대신 1단계가 확정한
**공개 payload 키와 함수 시그니처의 무변경**을 회귀 인수 기준으로 잡는다(AC 참조) — 1단계의
`precheck_vectorworks_diff` 출력 계약이 깨지면 안 된다.

### 사용자 결정 대기

- **FID 배정 전략** — `ASSUMPTION-71` 판정에 따라 분기한다. GO면 충돌 사전검사 + 사용자 범위의
  이중 안전망, 부정이면 사용자 범위 단독. **M0 이전에는 확정할 수 없으므로** 이 SPEC은 두 분기를
  모두 정의하고 M0가 선택하게 한다. 사용자에게 물어야 할 것은 "빈 FID 범위를 어디로 둘 것인가"이며
  이는 쇼파일마다 다르므로 **호출 인자**로 남긴다.

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — MVR/GDTF 가져오기

- 3D 배치와 GDTF 장비 정의 파싱은 **3단계** SPEC이 담당한다.
- 본 SPEC은 1단계가 이미 읽어 둔 설계상 리그만 소비한다.

### Out of Scope — 기존 픽스처 수정 · 삭제 · 재주소

- 본 SPEC은 **생성만** 한다. `Delete`·`Move`·재주소 명령을 생성하지 않는다.
- 도면 주소가 이미 점유되어 있으면 **옮기지 않고 제외 + 보고**한다(REQ-AUTOPATCH-019).

### Out of Scope — GDTF 라이브러리 임포트

- 콘솔 쇼파일에 FixtureType이 없으면 **하드 스톱**이다(REQ-AUTOPATCH-013).
- 라이브러리에 장비 정의를 넣는 작업은 사람이 콘솔에서 수행한다.

### Out of Scope — 실행 취소 · 백업 복원

- 되돌리기는 안전 계층의 별도 빈칸이며 독립 SPEC이 담당한다
  (`.moai/reports/ma3-copilot-overview.html` §7 P2).
- 본 SPEC은 되돌릴 수 없음을 **승인 시점에 명시**하는 것까지만 책임진다(REQ-AUTOPATCH-005).

### Out of Scope — 콘솔 측 구간 겹침 폭 주입

- 1단계가 `console_footprint_width_injection_deferred`로 이연한 2차 작업이다.
- 본 SPEC의 주소 계획은 **설계 측 점유폭**과 **콘솔 실측 주소 점유**만 사용한다.

### Out of Scope — 다중 유니버스 시스템 매핑

- System A–Z를 MA3 유니버스로 옮기는 매핑 정의는 본 SPEC이 만들지 않는다.
- 매핑이 없어 1단계 조인이 미수행이면 **패치를 거부**한다(REQ-AUTOPATCH-025).

---

## E. 참조 구현

| 참조 | 위치 | 무엇을 가져오는가 |
|---|---|---|
| `AddFixtures` 2단계 절차 · 필드 · CD 금지 | `server/rulebook/assets/v2.4.2/30_plugin_patterns.md:11-53` | 패치 기법 정본 |
| `deploy_plugin` 안전 파이프라인 | `server/orchestrator/tools.py:1266` | 컴파일 + 정적 스캔 + 사람 리뷰 |
| 콘솔 쓰기 단일 통로 | `server/orchestrator/tools.py` `run_commands` → `bundle_gate.screen()` | 게이트 경유 강제 |
| AST 경계 스캔 | `server/tests/test_prechk_tool.py:330-343` | `execution_port` 직접 호출 금지 검증 |
| 인벤토리 재조회 | `server/prechk/inventory.py:348` `read_inventory` | 패치 후 검증 읽기 |
| 주소 정규화 | `server/prechk/patch.py:100-147` `normalize_address` | 주소 비교 계약 |
| 1단계 차이 리포트 | `server/vwx/diff.py` · `server/vwx/report.py` | 패치 후보 입력 |
| FixtureTypes 열거 경로 | `server/orchestrator/tools.py:202` | 라이브러리 후보 집합 |
| 슬롯≠FID 경고 | `server/rulebook/assets/v2.4.2/20_korean_terms.md:34-36` · `31_choreography_patterns.md:203-209` | FID 오용 금지 근거 |
| 툴 등록 5지점 | `server/preshow/TOOLS_REGISTRATION.md` | 신규 툴 배선 절차 |
