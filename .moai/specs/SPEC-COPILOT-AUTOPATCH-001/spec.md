---
id: SPEC-COPILOT-AUTOPATCH-001
title: "Vectorworks 연계 2단계 — 차이 리포트 승인 기반 반자동 패치 생성·검증 (AddFixtures Lua 생성 → 사람 실행 → 서버 검증)"
version: "0.1.5"
status: draft
created: 2026-08-05
updated: 2026-08-06
author: orchestrator
priority: P0
phase: "Vectorworks 연계 2단계 — 반자동 패치 생성·검증 (1단계 대조 리포트의 후속, MVR/GDTF는 3단계). v0.1.3 이후: 서버가 Lua를 생성·전달하고 사람이 실행하며 서버가 검증한다"
module: "server/vwx/ (확장), server/orchestrator/tools.py (신규 툴 1종), server/prechk/ (재사용·무변경)"
lifecycle: spec-anchored
tags: "vectorworks, autopatch, addfixtures, lua-plugin, fid, fixturetype, dmxmode, approval-gate, idempotency, irreversible, semi-automatic, human-in-the-loop"
tier: L
depends_on: [SPEC-COPILOT-VWX-001]
related_specs: [SPEC-COPILOT-VWX-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-OVERLAP-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-AUTOPATCH-001 — Vectorworks 연계 2단계: 승인 기반 **반자동** 패치 (생성·전달·검증)

> **본 SPEC은 `SPEC-COPILOT-VWX-001`(1단계)의 직접 후속이다.** 1단계가 내는 차이 리포트의
> `missing_in_console`(도면에는 있으나 콘솔 실측에 없는 장비)을 입력으로 받아, **사람이 항목 단위로
> 승인한 것만** 라이브 검증된 Lua `AddFixtures` 기법으로 콘솔에 실제 패치한다.
>
> **의존 상태 고지 (v0.1.1)**: 1단계는 이 문서 작성 시점에 `status: draft` ·
> `run_status: partial-blocked`이며 **M8(라이브 종단)이 BLOCKED**, M0는 PARTIAL이다.
> 따라서 frontmatter에 `depends_on: [SPEC-COPILOT-VWX-001]`을 두어 **run-phase 진입 전에
> Phase 1 의존성 게이트가 1단계 완료를 강제**하게 한다. 본 SPEC의 plan-phase 작성은 1단계의
> **설계 산출물**(차이 리포트 스키마 · 설계상 리그 모델 · 멀티셀/액세서리 분류 규약)에만 의존하며
> 이들은 M1~M7에서 구현·검증이 끝났다 — 자세한 의존 범위 한정은 §C `의존 범위 한정`을 보라.
>
> 픽스처를 **생성**하며, 이 앱에는 아직 실행 취소·백업 복원 경로가 없다. 따라서 본 SPEC의 요구사항
> 절반 이상은 기능이 아니라 **되돌릴 수 없는 쓰기를 사람이 통제하게 만드는 장치**다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-05 | orchestrator | 최초 작성 (draft, Tier L). 출처는 `.moai/reports/ma3-copilot-overview.html` §7 P0 항목의 **2단계**와 `SPEC-COPILOT-VWX-001` §D `### Out of Scope — Lua AddFixtures 자동 패치`. **아티팩트 6종**(spec/plan/acceptance/design/research/progress). REQ **25건**(REQ-AUTOPATCH-001~025), AC **26건**, ASSUMPTION **5건**(71~75), 마일스톤 **9개**(M0~M8), 라이브 세션 **2회**(M0 프로브 · M8 종단), clarification 마커 **0건**. 위험 4건(FID 충돌 · FixtureType 핸들 해석 · 비가역성 · 멀티셀/액세서리)을 각각 요구·가정·마일스톤으로 구조화했다. |
| 0.1.1 | 2026-08-05 | orchestrator | **독립 plan-audit 1회차 FAIL(0.80 / Tier L 임계 0.85) 지적 10건 반영.** REQ **25→26**(REQ-AUTOPATCH-026 신설 — `ASSUMPTION-71` 부정 시 구조화된 사용자 확인 강제, D2), AC **26→27**(AC-AUTOPATCH-027 신설). frontmatter `depends_on` 추가 + §C `의존 범위 한정` 신설(**D1 critical** — 1단계가 `partial-blocked`인데 게이트 없이 완료로 취급하던 것). REQ-AUTOPATCH-003에 `address_basis` 열 강제(D3), REQ-AUTOPATCH-022에 멱등 일치 튜플 명시(D7). AC-AUTOPATCH-014③ 구조 테스트 구체화(D4), AC-AUTOPATCH-025 계약 스냅샷 기법 정의(D5), AC-AUTOPATCH-001 `Where`→`When`(D8). `plan.md` M0 테스트 쇼파일 전제 승격(D6), `design.md` §4 잔여 위험 R8 추가(D10), `progress.md` 선례 인용 정정(D9). |
| 0.1.2 | 2026-08-06 | orchestrator | **독립 plan-audit 2회차 PASS(0.857 ≥ Tier L 0.85).** 1회차 지적 10건 전량 CLOSED가 원문 대조로 확인됨. 2회차 신규 지적 4건도 전량 반영 — N1(major, D3와 같은 결함 패턴 재발): `design.md` §2.3 툴 스키마에 `fid_range_visually_confirmed_empty` 필드 신설하고 AC-AUTOPATCH-027이 그 필드명을 직접 인용하게 해 요구와 인터페이스 계약을 일치시킴. N2: `design.md` §6.2 테스트 매핑에 AC-AUTOPATCH-027 등재. N3: `research.md` §1의 "입력 확정" 문구를 §C `의존 범위 한정`으로 좁힘. N4: AC-AUTOPATCH-027을 AC-AUTOPATCH-008 직후로 이동(소속 마일스톤 그룹 배치 관례). **요구·AC 수 불변**(REQ 26 · AC 27). 코드 변경 0. |
| 0.1.3 | 2026-08-06 | orchestrator | **반자동 실행 모델로의 amendment (M0 5차 실측 근거 · 사용자 승인 2026-08-06).** §A 사전 확정 사실 **1·2를 반증 확정으로 정정**하고 실측 사실 **7·8을 신설**(플러그인 Lua 컨텍스트는 명령줄 목적지를 물려받지 않는다 · `deploy` 동사로 소스가 써지지 않는다). **REQ-AUTOPATCH-018을 "서버가 플러그인을 실행한다"에서 "검토용 Lua를 사람에게 전달하고 사람이 실행한 뒤 서버가 검증한다"로 조정** — `AddFixtures` 자동 실행이 이 빌드에서 성립하지 않는다는 13경로 0건 실측(`progress.md` §E.2 M0 1~5차)에 따른다. REQ-AUTOPATCH-020에 배포 경로 비가용 실측을 반영. `ASSUMPTION-76`(플러그인 실행 컨텍스트의 목적지) 신설 후 **즉시 NEGATIVE 판정 기록**. **REQ 수 불변(26)** — 018의 내용만 바뀌고 신설·삭제 0건. M4·M6·M7 무영향, M5만 "실행"→"실행 안내 + 검증"으로 축소. 코드 변경 0. **재감사 대상.** |
| 0.1.4 | 2026-08-06 | orchestrator | **독립 plan-audit round7 FAIL(0.7375) 18건 + round8 FAIL(0.805) 13건 + round9 FAIL(0.8025) 8건 = 지적 39건 전량 반영** (`progress.md` §E.1a 7·8·9회차). **N11(major, 인과 과잉주장 재발)**: "원인이 command destination이 아님은 확정"이라 적은 지점 전부를 **"처방의 반증 / 원인은 미확정"**으로 교정하고 §A 사실 7에 **재질의 금지의 범위**를 명시 — §E.2z가 교정한 오류의 재발이었고, round8이 서술 잔여 2곳(N29·N30)·round9가 §E.2z 자신의 후속 블록(N43)을 더 잡아 함께 교정했다. **N42(major, round9)**: round8 N38에 대응해 넣은 `AC-AUTOPATCH-019④`가 `REQ-AUTOPATCH-003`·`AC-AUTOPATCH-004②`(드라이런은 Lua 소스 전문을 낸다)와 **정면 충돌**하고 스키마에 없는 `승인 플래그`를 인용했다(D3·round2 N1 패턴 재발) → **철회하고 `REQ-AUTOPATCH-004`가 스스로 열거한 세 금지**(승격 경로·실행 기본값·함축 재시도)를 ③④⑤로 검증하도록 재작성. **검증가능성**: `AC-019`·`020` 비공허성 대조군을 산출물 수준으로 재작성(N16), `design.md` §6.3 **8→10건** 확장 + 표의 범위 명시, 대조군 없던 0건 주장 **6건**(AC-007③·013③·014③(a)·016③·017②·021②)에 대조군 부착(N37·N47). N28: REQ-018 **복합 태그**(신규 ID 미생성). 그 외 파생 지점 전파 누락 다수(§0 상태줄·서술·함정·읽는 순서·다음 담당자 항목·§E.1 yaml 머신 게이트·캡션·§F Justification·§F DoD·§B 시나리오·§7 안티패턴·§A.2·M0 전제수·§8 레지스트리·§2 제목·H1·프론트매터·6개 아티팩트 상태줄) 반영. **REQ 26 · AC 27 · §C.0a 합 27 불변.** 코드 변경 0. **round10 독립 감사 PASS(0.865 ≥ Tier L 0.85, round9 0.8025 대비 +0.0625) — 이 사이클의 첫 비-FAIL.** round10 지적 7건도 전량 반영: **N50**(가장 실질적 — "경로 13가지"가 실행 컨텍스트와 인자 변형을 섞어 세어 재구성 불가였다 → **실행 경로 10가지 · 인자 변형 8종 · 별도 생성 기법 1종**으로 계수 단위를 분리하고 의존 지점 12곳에 전파) · N53(대조군 추가 요약을 5건·N37 → **6건·N37+N47**로 통일) · N52(§E.1 헤드라인이 `plan_status`와 모순) · N51(§E.1 전문·캡션의 round9 누락) · N55(`커밋 10건` → run-phase 11건/총 15건, 계수 기준 명시) · N54(짝 없는 `**`) · N55b(§F 항목 7의 보증이 `"0건"` 토큰에만 걸려 있던 것을 **금지·부재 주장 전부**로 확장하고 문장형 부재 주장 6건에 대조군 부착 + 라이브 검증 AC 2건을 명시적 범위 예외로 기록). **plan_status: audit-ready** |
| 0.1.5 | 2026-08-06 | orchestrator | **M8 재정의 amendment (사용자 승인 2026-08-06) + 독립 코드 감사 round13·round14 반영.** `AC-AUTOPATCH-026`이 v0.1.2 자동 실행 모델의 문장("실행"을 왕복의 한 칸으로 두고 "시스템이 1회 통과")을 그대로 이고 있었다 — v0.1.3이 REQ-AUTOPATCH-018을 반자동으로 조정할 때 함께 고쳐지지 않은 누락이다. **4관문(G1 서버 전달 · G2 사람 실행 · G3 서버 검증 · G4 원복)으로 분리**해 책임과 실패 모드를 갈랐고, **G1 통과 + G2 실패를 유효한 결과로 명시**했다(사람 실행 경로는 한 번도 시험된 적이 없으므로 그 실패는 새 실측이지 코드 결함이 아니다). **표시 문자열 판별 실험**을 세션 항목으로 편입(⑦). **REQ 26건·AC 27건 수 불변** — AC-026 내부만 정밀화했다. 함께: **독립 코드 감사 round11·12·13·14 — 넷 다 FAIL, 지적 누계 59건 반영.** round11(4명 전원 FAIL, 치명 2건)·round12(round11 수정이 만든 치명 2건)·round13(round12 수정이 만든 치명 1건)·round14(**처음으로 치명 0건·fail-open 0건**, 두 감사자 모두 "차단 문구만 고치면 코드 축 GO") — 네 건 모두 작성자 테스트를 전부 통과한 채 살아 있었다(`progress.md` §E.2 round11·round12 절, `.moai/reports/plan-audit/…-round11.md`·`-round12.md`). **[round16 #3 정정]** 이 행은 *"독립 코드 감사 round11·12·13·14 — 넷 다 FAIL"*에 멈춘 stale이었다 — v0.1.5는 이후 **round15·round16 지적 반영까지** 담았고 **독립 감사는 round11~16 여섯 라운드 전부 FAIL**이다(round15: 뮤테이션 48건 KILL 68.8% · 치명 2 · 문서 major 6/minor 2 · round16: 뮤테이션 79건 KILL 81.0% · 치명 1 · 안전 high 3 · 문서 major 4/minor 6). **REQ 26·AC 27 수는 그대로다.** 또 위 문장의 *"그 실패는 새 실측이지 코드 결함이 아니다"*는 **round14 T12가 폐기**했다 — 정본은 `acceptance.md` AC-AUTOPATCH-026⑥이며, 배제되는 것은 "전달물이 옳았는데도 실패했다"는 경우뿐이고 기본 분류는 `판별 불가`다. |

---

## A. 개요

**한 줄**: 1단계 차이 리포트에서 사람이 고른 장비만, 콘솔 라이브러리에서 확정한 FixtureType·DMXMode
핸들과 사용자가 명시한 빈 FID 범위를 써서 **검토 가능한 `AddFixtures` Lua를 생성해 사람에게 전달하고,
사람이 콘솔에서 실행한 뒤 서버가 다시 읽어 실제로 그렇게 되었는지 건별로 확인**한다.

본 SPEC은 **생성만** 한다. 기존 픽스처의 수정·삭제·재주소는 §D가 배제한다.
**서버는 패치를 직접 실행하지 않는다**(v0.1.3 amendment — 아래 사실 7·8).

### 사전 확정 사실 (조사 확정 — 재질의 금지)

1. **~~커맨드라인으로는 픽스처를 만들 수 없고, 패치는 `deploy_plugin` → `run_commands(["Plugin 'X'"])`
   2단계다~~ → [반증 확정 · v0.1.3]** 앞 절은 룰북
   (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:13-18`)의 주장이며 **이 환경에서 성립하지
   않는다.** onPC 2.4.2.2 + responder 1.6.1에서 **실행 경로 10가지와 인자 변형 8종을 측정해
   픽스처 생성 0건**이고,
   룰북이 "라이브 검증됨"으로 적은 워크된 예제(`:40-53`)를 **글자 그대로 돌려도 0건**이다
   (`progress.md` §E.2 M0 1~5차). **대체 사실은 아래 7번이다.**
2. **~~`ChangeDestination`/`CD`를 어디에서도 보내면 안 된다 — CD를 보내면 패치가 `nil`을 반환한다~~
   → [반증 확정 · v0.1.3]** **CD 유무와 무관하게 결과가 같다.** 나아가 M0 5차가 **양성 대조군**을
   확보했다 — 매크로 명령줄의 CD는 **실제로 적용되고 듣지만**(목적지 미이동 시 같은 목적지-상대
   명령은 `Illegal object`이거나 무효과) **플러그인 Lua는 그 목적지를 물려받지 않는다.**
   생성 산출물의 CD 금지(REQ-AUTOPATCH-017)는 **그대로 유효**하다 — 근거가 "CD가 실패 원인"에서
   **"CD는 아무 효과가 없으므로 생성 어휘에 둘 이유가 없다"**로 바뀔 뿐이다.
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
7. **[신설 · v0.1.3 실측] `AddFixtures`는 이 환경에서 서버 자동화로 픽스처를 만들지 못하며,
   명령줄 목적지 조작으로는 그 벽에 도달할 수 없다.** 플러그인 Lua 실행 컨텍스트의 목적지는 항상
   `TempCmdlines Cmdline 1`이고, **명령줄 목적지를 patch fixtures 컨테이너로 옮겨도 물려받지 않는다**
   (명령줄 목적지에 대한 양성 대조군 확보 · `progress.md` §E.2 M0 5차 L6). 객체 모델 생성 경로도
   부정이다(`Fixtures:Append`는 실재 `function`이나 `nil` 반환 · 0건, 허구 키 비공허성 대조군 통과).
   **단 객체 모델 프로퍼티 쓰기는 목적지와 무관하게 즉시 적용된다** — patch 레이어가 Lua로
   읽고 쓸 수 없는 것이 아니라, `AddFixtures`의 **생성**만 성립하지 않는다.
   **[재질의 금지의 범위]** 확정된 것은 위 **관측과 처방의 무효**까지다.
   **"실패 원인이 무엇인가"는 확정 사실이 아니라 미확정**이며, 특히 "원인이 플러그인의
   목적지다"라는 가설은 **반증되지 않았다**(그 전건이 실현된 컨텍스트를 10개 실행 경로 전부에서
   한 번도 만들지 못했다 — `progress.md` §0 [HARD], round7 감사 N11). 원인 규명을 재질의
   금지로 덮지 않는다.
8. **[신설 · v0.1.3 실측] responder `deploy` 동사로는 이 빌드에 플러그인 소스가 써지지 않는다.**
   `cannot confirm plugin source write`로 실패하면서 **플러그인 객체는 생성되고 소스는 빈 상태**가
   되며, 그것을 실행하면 `OK`가 돌아오고 아무 일도 일어나지 않는다. 동작하는 배포 경로는
   **콘솔 라이브러리 파일 + `Import Plugin '<파일명>'`** 하나뿐이다(`console/lua/**`가 본 SPEC의
   PRESERVE라 응답기 수정은 범위 밖 — G3, 별건 SPEC). **따라서 서버가 배포·실행을 완결할 수 없다.**

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
  생성될 Lua 소스 전문과 대상 장비 표를 **먼저** 낸다. 표의 열은 최소한
  **타입 · 모드 · FID · 유니버스 · 주소 · 점유폭 · `address_basis`**를 포함한다 —
  `address_basis`는 1단계가 붙인 주소 근거 등급(`universe_address_direct` |
  `absolute_back_calculated`)이며, 역산 등급이 하나라도 섞이면 그 전제 문구를 함께 싣는다.
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
- **REQ-AUTOPATCH-026** `[Where]` **Where** `ASSUMPTION-71`이 **부정 또는 INCONCLUSIVE**로
  판정되면, the 패치 실행기 **shall** 실행 전에 **구조화된 사용자 확인**을 요구한다 —
  "이 FID 범위가 콘솔에서 비어 있음을 눈으로 확인했다"는 사실이 일반 승인과 **구분되는 별도
  페이로드 필드**로 캡처되어야 하며, 그 필드가 없으면 실행을 **거부**한다. 산문 경고만으로는
  충족되지 않는다 — 실행 건별로 감사 가능해야 한다. **GO 분기에서는 이 확인을 요구하지 않는다**
  (충돌 사전검사가 독립 탐지를 제공하므로).

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
- **REQ-AUTOPATCH-018** `[Ubiquitous + Unwanted — 복합]` **[v0.1.3 조정 — 반자동 실행 모델]**
  두 극성을 한 요구에 담는다. **신규 ID를 만들지 않는 이유**: REQ 수 26을 유지해 §C.0 역추적표
  26행과 1:1을 지키기 위함이며, 두 반쪽은 **AC-AUTOPATCH-015의 ①과 ②가 각각** 검증한다.
  - `[Ubiquitous]` The 실행 계층 **shall** 승인된 패치를 **사람이 콘솔에서 실행하도록 전달**한다 —
    검토 가능한 `AddFixtures` Lua 소스와 실행 절차를 사용자에게 제시한다. 실행 여부·시점은
    사람이 결정하며, 서버의 다음 동작은 **REQ-AUTOPATCH-023의 검증 읽기**다. → AC-015①
  - `[Unwanted]` The 실행 계층 **shall not** 패치 실행을 **서버 스스로 발화**한다 — 사용자 승인
    여부와 무관하게 서버가 실행을 대행하는 경로를 두지 않는다. → AC-015②

  근거: §A 사전 확정 사실 7·8(실행 경로 10가지·인자 변형 8종 0건 실측 · 배포 경로 비가용) 및 제품 비목표
  *"라이브 실시간 자율 운영 배제 — 실행 버튼은 항상 사람이 누른다"*(`.moai/project/product.md` §6).
  **이전 판(v0.1.2)의 "`run_commands(["Plugin '<이름>'"])` 단일 명령 호출" 요구는 폐기한다** —
  그 경로가 픽스처를 만들지 못한다는 것이 실측으로 확정됐다. 단 서버가 어떤 이유로든 콘솔에
  문장을 보낼 때는 **REQ-AUTOPATCH-021의 단일 통로 규율**이 그대로 적용된다.
  **[가역성]** 미측정으로 남은 실행 컨텍스트가 **하나** 있다 — L2(패치 편집 세션 활성).
  L2가 긍정으로 나오면 본 요구를 v0.1.2 형태로 **되돌릴 수 있다**(`progress.md` §E.2aa).
- **REQ-AUTOPATCH-019** `[Ubiquitous]` The 주소 계획기 **shall** 각 장비를 **해당 모드의 점유폭만큼
  간격**을 두어 배치하고, 1단계 도면이 지정한 유니버스·주소를 우선 사용한다. 도면 주소가 이미
  콘솔에서 점유되어 있으면 그 항목을 패치 대상에서 제외하고 사유를 보고한다 —
  임의의 빈 주소로 옮겨 붙이지 않는다.

### B.5 안전 · 멱등 · 검증

- **REQ-AUTOPATCH-020** `[Ubiquitous]` The 배포기 **shall** 콘솔로 나가는 플러그인 배포가 필요한
  경우 기존 `deploy_plugin` 파이프라인(컴파일 검사 + 정적 스캔 + 사람 리뷰)을 그대로 경유한다 —
  별도 배포 경로를 만들지 않는다. **[v0.1.3 실측 고지]** 이 빌드에서 `deploy` 동사는 소스를 쓰지
  못하므로(§A 사실 8) **반자동 모델의 기본 전달물은 배포가 아니라 검토용 Lua 소스 자체**다.
  본 요구는 "별도 배포 경로 신설 금지"라는 **금지 규율로서 유효**하며, 우회 배포 구현을 막는다.
- **REQ-AUTOPATCH-021** `[Unwanted]` The 패치 모듈 **shall not** `execution_port`를 직접 호출한다 —
  콘솔로 나가는 모든 문장은 `run_commands` → `bundle_gate.screen()`을 통과한다
  (`server/tests/test_prechk_tool.py:330-343`의 AST 스캔 대상).
- **REQ-AUTOPATCH-022** `[Ubiquitous]` The 패치 실행기 **shall** **멱등**하다 — 같은 승인 집합을 두 번
  실행해도 중복 픽스처를 만들지 않는다. 실행 전에 **(유니버스, 주소, FixtureType, DMXMode 이름)**
  네 값이 모두 일치하는 기존 픽스처를 재조회해 그 항목만 건너뛰고, 건너뛴 사실을 보고한다.
  **주소는 일치하지만 타입 또는 모드가 다르면 멱등이 아니라 충돌이며**, 건너뛰지 않고
  충돌로 보고한다 — 무관한 픽스처가 그 주소를 점유한 것을 "이미 했음"으로 삼키지 않는다.
- **REQ-AUTOPATCH-023** `[Ubiquitous]` The 패치 실행기 **shall** 실행 직후 `precheck_patch`로 **다시
  읽어**, 승인된 각 항목이 실제로 그 유니버스·주소에 그 타입으로 생성되었는지 확인하고 결과를
  건별로 보고한다 — 플러그인이 오류 없이 끝난 것을 성공의 근거로 삼지 않는다.
- **REQ-AUTOPATCH-024** `[Event-driven]` **When** 검증 읽기가 승인 항목과 어긋나면, the 패치 검증기
  **shall** 불일치를 구조화해 보고하고 **자동 재시도·자동 보정을 하지 않는다**. 생성된 픽스처가
  0건이면 **실행 여부와 실행 절차를 재확인하도록 안내**한다.
  **[v0.1.3 정정]** 이전 판은 룰북의 *"Patch > Fixtures 편집기를 먼저 열라"*
  (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:28-29`)를 그대로 안내 문구로 못박았으나,
  그 조언은 **근거를 잃었다** — 편집기를 연 상태에서도 0건이고(`ASSUMPTION-75` NEGATIVE),
  목적지를 patch fixtures 레이어로 옮겨도 0건이다(`ASSUMPTION-76` NEGATIVE, 양성 대조군 포함 ·
  `progress.md` §E.2 M0 2~5차). **틀린 원인을 사용자에게 안내하지 않는다.**

### B.6 경계와 보고

- **REQ-AUTOPATCH-025** `[Event-driven]` **When** 1단계 리포트가 `multi_system_mapping_absent`
  등으로 콘솔 대조를 수행하지 않았거나 `diffs.performed`가 거짓이면, the 패치 실행기 **shall**
  패치를 **거부**한다 — 대조되지 않은 리포트에서 "빠진 장비"를 도출할 수 없다.

---

## C. 환경 및 전제

### 의존 범위 한정 — 1단계의 무엇에 의존하는가 (v0.1.1)

`depends_on: [SPEC-COPILOT-VWX-001]`은 **run-phase 진입 게이트**다. 다만 "1단계가 통째로 끝나야
한다"는 주장은 과하므로, 무엇에 의존하고 무엇에 의존하지 않는지 좁혀서 적는다.

**의존한다 (M1~M7에서 구현·검증 완료)**

| 의존 대상 | 1단계 상태 |
|---|---|
| 차이 리포트 payload 스키마 (`diffs` · `designed_rig` · `read_failures` · `excluded_rows` · `skipped_checks`) | 구현·테스트 완료 |
| `missing_in_console` 항목의 필드 집합 (유니버스 · 주소 · 타입 · 이름 · 유닛) | 구현·테스트 완료 |
| 멀티셀 접기 · 액세서리 분류 · 미패치 제3분류 | 실물 4종으로 검증 완료 |
| 주소 근거 등급(`address_basis`) | 구현·테스트 완료 |
| `diffs.performed` 불변식과 `multi_system_mapping_absent` 사유 | 구현·테스트 완료 |

**의존하지 않는다 (1단계에서 아직 열린 것)**

| 1단계 미완 항목 | 본 SPEC에 미치는 영향 |
|---|---|
| `ASSUMPTION-70` — 제목행 선행형 워크시트 실물 미검증 | **없다.** 그 변형이 판독되면 후보 목록이 생기고, 판독 실패면 본 SPEC이 REQ-AUTOPATCH-025로 거부한다. 어느 쪽이든 본 SPEC의 계약은 불변이다 |
| M8 — 1단계 라이브 종단 미수행 | 본 SPEC의 M0·M8이 **자체 라이브 세션**을 갖는다. 1단계 M8이 검증할 것(도면 판독 종단)과 본 SPEC이 검증할 것(패치 종단)은 다른 구간이다 |
| 1단계 `status: draft` | run-phase 게이트가 강제한다. plan-phase 작성은 위 표의 확정 산출물만 참조한다 |

**따라서**: 본 SPEC의 §A "사전 확정 사실"은 **위 표 상단(의존한다) 범위에 한정**된 주장이며,
1단계 전체가 완료되었다는 뜻이 아니다.


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
- **ASSUMPTION-76** — `[신설 v0.1.3 · 즉시 판정]` 서버가 발화한 플러그인 실행이 **patch fixtures
  레이어의 command destination을 갖는다.** plan-phase가 놓친 전제였다(룰북은 "`AddFixtures`가 현재
  목적지를 읽는다"까지만 적었고, "서버가 발화한 실행이 그 목적지를 갖는가"는 아무도 묻지 않았다).
  **판정: NEGATIVE** — 플러그인 Lua는 명령줄 목적지를 물려받지 않으며, 목적지를 옮겨도
  `AddFixtures`는 0건이다(명령줄 목적지에 대한 양성 대조군 포함, `progress.md` §E.2 M0 5차).
  **부정의 결과가 REQ-AUTOPATCH-018 조정(반자동 실행 모델)이다.**
  **단 L2(패치 편집 세션 활성)는 미측정으로 남는다** — 긍정으로 나오면
  REQ-AUTOPATCH-018을 v0.1.2 형태로 복원할 수 있다(`progress.md` §E.2aa).
  또한 이 NEGATIVE는 **"원인이 목적지다"라는 가설의 반증이 아니다** — 그 전건이 실현된
  컨텍스트를 만들지 못했으므로 원인은 미확정이다(§A 사실 7의 재질의 금지 범위 참조).

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

- **[round16 추가] M8 테스트 자원 분리의 실현 방법** — `plan.md` §B M8 착수 전제 ④(구 P4)는
  "FID·유니버스를 기존과 완전히 분리"를 요구하지만 **유니버스·주소 분리는 이 툴로 불가능**하다.
  `server/vwx/apply.py:132`가 `HandoffEntry.address`를 **"언제나 도면 주소 그대로"**로 못박고
  `patchplan.plan_addresses`는 겹치는 항목을 **제외**할 뿐 옮기지 않는다. **분리 가능한 축은
  `fid_range` 하나뿐**이며, 유니버스·주소를 옮기려면 **1단계에 넣는 도면을 그렇게 만들어야**
  한다. 사용자가 골라야 할 것: **㉠ FID 대역만 분리하고 주소는 도면대로 간다**(툴 인자만으로
  가능) / **㉡ 분리된 유니버스로 도면을 다시 만들어 1단계부터 다시 뜬다**(도면 작업 필요).
  ㉡을 고르면 `plan.md` §B M8 착수 전제 ⑥의 **리포트 동결**을 그 도면으로 다시 해야 한다.

- **[round16 추가] AC-AUTOPATCH-026④(G4)가 "제거 불가"를 판정하지 못한다 — 규정 공백** —
  ④는 *"세션 후 생성물 제거를 사용자가 확인했음이 `progress.md`에 기록된다"*를 통과 조건으로
  걸지만, 아래 §D 「Out of Scope — 기존 픽스처 수정 · 삭제 · 재주소」가 *"본 SPEC은 **생성만**
  한다. `Delete`·`Move`·재주소 명령을 생성하지 않는다"*로 삭제를 배제하고 §D 「Out of Scope —
  실행 취소 · 백업 복원」이 되돌리기를 독립 SPEC으로 넘긴다. 제거는 **사람이 콘솔에서 손으로**
  하는 일이며(`plan.md` P5가 미정인 이유), **끝내 제거하지 못했을 때 ④를 어떻게 판정하는지가
  `acceptance.md`·`plan.md`·`M8-REDEFINITION-DRAFT.md` 어디에도 없다.** 선택지: ㉠ ④를
  `제거 확인`/`제거 불가(사유 기록)` 두 결과로 나누고 후자도 통과 · ㉡ 제거 불가면 M8을
  미완으로 둔다 · ㉢ P5 합의를 세션 착수 **차단 조건**으로 승격해 그 상태가 생기지 않게 한다.
  **AC 본문 수정은 사용자 승인 사항이므로 이 SPEC은 임의로 메우지 않는다** — 공백을 공백으로
  기록해 둔다(`M8-REDEFINITION-DRAFT.md` §3 아래 round16 (b) 블록).

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
| `AddFixtures` 필드 집합 · `mode` 핸들 형식 · 점유폭 원칙 | `server/rulebook/assets/v2.4.2/30_plugin_patterns.md:11-53` | **[v0.1.3] 이 부분만 유효.** 같은 문서의 2단계 절차(`:13-18`) · CD 인과(`:25-27`) · 편집기 안내(`:28-29`) · 워크된 예제(`:40-53`)는 **반증됐다**(`research.md` §2 주석 · `progress.md` §E.2 M0 1~5차) |
| `deploy_plugin` 안전 파이프라인 | `server/orchestrator/tools.py:1266` | 컴파일 + 정적 스캔 + 사람 리뷰 |
| 콘솔 쓰기 단일 통로 | `server/orchestrator/tools.py` `run_commands` → `bundle_gate.screen()` | 게이트 경유 강제 |
| AST 경계 스캔 | `server/tests/test_prechk_tool.py:330-343` | `execution_port` 직접 호출 금지 검증 |
| 인벤토리 재조회 | `server/prechk/inventory.py:348` `read_inventory` | 패치 후 검증 읽기 |
| 주소 정규화 | `server/prechk/patch.py:100-147` `normalize_address` | 주소 비교 계약 |
| 1단계 차이 리포트 | `server/vwx/diff.py` · `server/vwx/report.py` | 패치 후보 입력 |
| FixtureTypes 열거 경로 | `server/orchestrator/tools.py:202` | 라이브러리 후보 집합 |
| 슬롯≠FID 경고 | `server/rulebook/assets/v2.4.2/20_korean_terms.md:34-36` · `31_choreography_patterns.md:203-209` | FID 오용 금지 근거 |
| 툴 등록 5지점 | `server/preshow/TOOLS_REGISTRATION.md` | 신규 툴 배선 절차 |
