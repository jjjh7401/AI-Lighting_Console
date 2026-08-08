# SPEC-COPILOT-AUTOPATCH-001 — 구현 계획 (plan)

status: draft (v0.1.5, 2026-08-06) · Tier L · 마일스톤 M0~M8 · 라이브 세션 2회 · **M5 축소(반자동 실행 모델 amendment)**

---

## §A. 맥락과 우선순위

### §A.1 우선순위 매핑

`.moai/reports/ma3-copilot-overview.html` §7의 **P0 — Vectorworks 연계**의 **2단계**다.
1단계(`SPEC-COPILOT-VWX-001`)가 "무엇이 다른가"를 답했고, 본 SPEC은 "그중 고른 것을 실제로 채워라"를
답한다. 3단계(MVR/GDTF)는 별도 SPEC이다.

### §A.2 build-vs-review 순서 — 왜 M0가 먼저인가

본 SPEC은 **콘솔에 쓰는 첫 Vectorworks 기능**이다. 그런데 쓰기에 필요한 값 두 개
(**FID**, **DMXMode 핸들**)가 모두 **읽을 수 있는지조차 확정되지 않았다**(`ASSUMPTION-71`, `-72`).
확정 없이 구현하면 "동작하는 것처럼 보이지만 엉뚱한 픽스처를 덮는" 실패로 간다 —
룰북이 두 번 경고한 그 실패다(`20_korean_terms.md:34-36`, `31_choreography_patterns.md:203-209`).

따라서 `SPEC-COPILOT-PRECHK-001`의 **probe-before-authoring** 규율을 그대로 따른다:
**M0에서 6개 전제를 실기로 측정하고, 그 판정이 M2·M3·M5·M6의 설계를 확정한다.**
(**[v0.1.3]** 5 → 6: `ASSUMPTION-76`이 M0 3~5차에서 사후 식별돼 편입됐고, 그 판정이 **M5**를
반자동 실행 모델로 축소시켰다 — 그래서 영향 마일스톤에 M5가 추가된다. AC-AUTOPATCH-001과 일치.)
M0 없이 M2 이후를 착수하지 않는다.

### §A.3 ASSUMPTION 부정 시 처리

| 가정 | 부정이면 |
|---|---|
| `ASSUMPTION-71` FID 가독 | REQ-AUTOPATCH-009의 충돌 사전검사 **descope**. 리포트에 축소 명시. **추가로 REQ-AUTOPATCH-026이 발동한다** — 산문 경고로 끝내지 않고, "FID 범위가 콘솔에서 비어 있음을 눈으로 확인했다"를 **일반 승인과 구분되는 별도 페이로드 필드**로 요구하며 없으면 실행을 거부한다(건별 감사 가능). 이 분기에서는 그 확인이 유일한 독립 안전망이다 — 멱등 검사(주소·타입·모드)도 검증 읽기(유니버스·주소·타입)도 **FID 충돌은 탐지하지 못한다** |
| `ASSUMPTION-72` DMXModes 드릴다운 | REQ-AUTOPATCH-014의 점유폭 일치 확인 **descope**. 모드 선택은 사용자 확인 단독. 드라이런 표에 "점유폭 미검증" 열 추가 |
| `ASSUMPTION-73` 다중 유니버스 patch 배열 | 유니버스별로 플러그인을 **분할 실행**하는 것으로 대체. 분할 사실을 드라이런에 명시 |
| `ASSUMPTION-74` 패치 후 즉시 관측 | REQ-AUTOPATCH-023의 검증 읽기에 **재시도 대기**를 넣되, 대기 후에도 미관측이면 "확인 불가"로 보고(성공으로 간주 금지) |
| `ASSUMPTION-75` Patch 편집기 상태 감지 | 사전 안내를 포기하고 **사후 안내만** 한다(REQ-AUTOPATCH-024가 이미 그 경로를 규정) |
| **`ASSUMPTION-76`** 서버 발화 플러그인이 patch 목적지를 갖는가 **[v0.1.3 신설 · NEGATIVE 확정]** | **부정이 실측 확정됐다** — 서버가 패치를 실행하지 않는다. REQ-AUTOPATCH-018을 **반자동 실행 모델**로 조정하고(검토용 Lua 전달 → 사람 실행 → 서버 검증) M5를 "실행"에서 "실행 안내 + 검증 인계"로 축소한다. M4(Lua 생성)·M6(검증 읽기)·M7(툴 배선)은 **무영향**. **단 L2(패치 편집 세션 활성)는 미측정** — 긍정으로 나오면 REQ-AUTOPATCH-018을 v0.1.2 형태로 복원 가능(`progress.md` §E.2aa). 또 이 NEGATIVE는 "원인이 목적지다"의 반증이 **아니다**(전건 미실현 — 원인 미확정) |

**부정을 실패로 취급하지 않는다.** 부정은 기능 축소이며, 축소는 리포트에 구조화되어 드러난다.

### §A.4 결정 등록부

| # | 결정 | 근거 | 상태 |
|---|---|---|---|
| A | 신규 도메인 패키지를 만들지 않고 **`server/vwx/` 확장** | 입력이 1단계 산출물이고 타입·주소 어휘를 공유한다. 새 패키지는 계약 중복을 낳는다 | 확정 |
| B | 신규 툴 **1종**(`apply_vectorworks_patch`)만 추가 | 드라이런과 실행을 별도 툴로 쪼개면 승인 상태가 툴 경계를 넘어 흐른다. 한 툴 + `dry_run` 인자가 상태를 한곳에 둔다 | 확정 |
| C | 드라이런이 **기본값** | REQ-AUTOPATCH-003·004. 실행이 기본이면 오호출 한 번이 되돌릴 수 없는 쓰기가 된다 | 확정 |
| D | FID 범위는 **호출 인자**, 설정 파일 아님 | 쇼파일마다 다르다. 설정에 박으면 다른 쇼에서 조용히 틀린다 | 확정 |
| E | 타입 별칭표는 **재사용 가능하게 저장**하되 자동 적용은 사용자 확인 후 | 같은 리그를 반복 패치할 때 매번 묻는 것은 실용적이지 않다. 다만 첫 확정은 사람이 한다 | 확정 |
| F | 패치 후 검증은 **`precheck_patch` 재사용**, 자체 읽기 경로 금지 | 읽기 계약이 둘로 갈라지면 판정이 갈라진다. `server/prechk/`는 PRESERVE이므로 소비만 한다 | 확정 |
| G | 실패 시 **자동 재시도·자동 보정 금지** | 되돌릴 수 없는 쓰기에서 자동 보정은 손해를 키운다. 사람에게 돌려준다 | 확정 |

**미결 0건.** 사용자 입력이 필요한 것은 결정이 아니라 **런타임 인자**(FID 범위)이며 결정 D가 그 위치를 정했다.

### §A.5 PRESERVE 재잠금

`spec.md` §C의 PRESERVE 목록을 그대로 잠근다. 각 마일스톤 종료 시 게이트를 재측정하고,
**M7이 비공허성까지 증명**한다(금지 대상을 일부러 심어 게이트가 실제로 잡는지 확인).

`server/vwx/**`는 확장 대상이라 PRESERVE가 아니다. 대신 **1단계 공개 계약 무변경**을
AC-AUTOPATCH-025가 지킨다 — `precheck_vectorworks_diff`의 payload 키 집합과 값 의미가 그대로여야 한다.

---

## §B. 마일스톤

### M0 — 라이브 전제 측정 (cycle_type=none)

**요구·설계 지시**: 실기 onPC 2.4.2에서 `ASSUMPTION-71`~`-76`을 **비파괴 우선**으로 측정한다.
(**[v0.1.3]** `ASSUMPTION-76`은 착수 시점에 목록에 없었고 **M0 3~5차 진행 중 사후 식별**되어
편입됐다 — plan-phase가 놓친 전제였다. M0 5차에서 **NEGATIVE** 판정.)
**진입 전제 (D6)**: **테스트 쇼파일이 확보되어 콘솔에서 열려 있어야 M0를 착수한다.**
절차 4(파괴적 측정)가 그것을 요구하므로 이는 권고가 아니라 **차단 전제**다.
테스트 쇼파일을 끝내 확보하지 못하면 `ASSUMPTION-73`·`-74`는 **INCONCLUSIVE**로 판정하고
(`ASSUMPTION-71`의 "적합 픽스처 없음 → INCONCLUSIVE" 처리와 동일한 규율),
그 결과 M8은 **BLOCKED로 남으며 SPEC은 완결되지 않는다.** 운영 쇼파일로 대체하지 않는다.

71·72·75는 읽기만으로 판정 가능하다. 73·74는 **최소 1대 패치**가 필요하므로 사용자 승인을 받고
테스트용 쇼파일에서 수행하며, 세션 종료 시 생성물을 사람이 제거한다.

측정 절차:
1. `ASSUMPTION-72` — `query_state("Patch/FixtureTypes")` 열거 → 임의 타입 1개 드릴다운 →
   `DMXModes` 관측 여부 → 모드 1개 드릴다운 → 채널 점유폭 관측 여부. **읽기 전용.**
2. `ASSUMPTION-71` — 이미 패치된 픽스처 1대에 대해 `FID`·`CID` 프로퍼티 읽기 시도.
   **슬롯과 값이 다른 픽스처**를 골라야 판정이 성립한다(슬롯==FID 쇼파일에서는 무의미).
   그런 픽스처가 없으면 판정 **INCONCLUSIVE**로 기록하고 부정과 같이 취급한다.
3. `ASSUMPTION-75` — Patch 편집기를 닫은 상태와 연 상태에서 각각 관측 가능한 차이를 찾는다.
   **읽기 전용.**
4. `ASSUMPTION-73`·`-74` — 사용자 승인 후 테스트 쇼파일에 **1대**를 패치(단일 유니버스),
   재조회로 관측 확인. 이어서 **2개 유니버스에 걸친 2대**를 패치해 73을 판정.
5. `ASSUMPTION-76` — 서버가 발화한 플러그인 실행의 command destination을 플러그인 안에서
   직접 판독하고, 명령줄 목적지를 옮긴 컨텍스트(매크로 2줄)에서 재측정한다.
   **목적지 이동이 실제로 일어났고 듣는다**는 것을 목적지-상대 명령으로 **짝지은 양성·음성
   대조군**과 함께 독립 증명해야 판정이 성립한다(대조군 없는 판정은 §E.2z가 금지한 과잉주장이 된다).

**baseline**: 착수 SHA에서 `uv run pytest server/tests -q`를 직접 실측해 `progress.md`에 적는다.
**AC**: AC-AUTOPATCH-001

### M1 — 패치 후보 입력 모델 (cycle_type=tdd)

**요구·설계 지시**: 1단계 리포트 payload를 받아 패치 후보 목록으로 정규화한다. 리포트가
`diffs.performed == false`이거나 다중 시스템 미매핑이면 이 단계에서 거부한다.
후보는 항목 단위 식별자를 갖고, 기본 선택 상태는 **비선택**이다.
**AC**: AC-AUTOPATCH-002 · AC-AUTOPATCH-003 · AC-AUTOPATCH-004

### M2 — FID 배정 (cycle_type=tdd)

**요구·설계 지시**: 사용자 범위 안에서만 배정. 범위 미제공 시 거부. 슬롯 유래 값 사용 금지.
M0의 `ASSUMPTION-71` 판정에 따라 충돌 사전검사를 켜거나 descope한다 — **어느 쪽이든 리포트에
어떤 안전망이 작동 중인지 명시**한다.
**AC**: AC-AUTOPATCH-005 · AC-AUTOPATCH-006 · AC-AUTOPATCH-007 · AC-AUTOPATCH-008 · AC-AUTOPATCH-027

### M3 — FixtureType · DMXMode 해석 (cycle_type=tdd)

**요구·설계 지시**: `Patch/FixtureTypes` 열거 → VW 타입/GDTF 이름과 퍼지 매칭 → 사용자 확인 →
별칭 저장. 라이브러리 부재 시 하드 스톱. M0의 `ASSUMPTION-72` 판정에 따라 점유폭 일치 확인을
켜거나 descope한다.
**AC**: AC-AUTOPATCH-009 · AC-AUTOPATCH-010 · AC-AUTOPATCH-011 · AC-AUTOPATCH-012

### M4 — Lua 생성기 + 주소 계획 (cycle_type=tdd)

**요구·설계 지시**: `AddFixtures` 호출을 생성한다. **`ChangeDestination` 금지**를 생성기 차원에서
구조적으로 보장하고(문자열 검사로 사후 확인하는 것이 아니라 생성 어휘에 애초에 없게 한다),
점유폭 간격으로 배치하며, 이미 점유된 도면 주소는 제외한다.
**AC**: AC-AUTOPATCH-013 · AC-AUTOPATCH-014 · AC-AUTOPATCH-016

### M5 — 실행 전달(사람) · 검증 인계 (cycle_type=tdd) **[v0.1.3 축소]**

**요구·설계 지시**: **서버는 패치를 실행하지 않는다**(`ASSUMPTION-76` NEGATIVE 확정 —
`progress.md` §E.2 M0 5차). 검토 가능한 `AddFixtures` Lua 소스와 실행 절차를 사용자에게
**제시**하고, 사람이 콘솔에서 실행한 뒤 **M6의 검증 읽기로 인계**한다.
`RecordingExecutionPort`에 도달하는 패치 실행 발화가 **0건**임을 비공허하게 증명한다
(실행 발화를 되살린 사본에서 단정이 깨지는지 확인). 별도 배포 경로 신설 금지는 유지하되,
이 빌드에서 `deploy` 동사가 소스를 쓰지 못하므로(`spec.md` §A 사실 8) 기본 전달물은
**Lua 소스 자체**다. `execution_port` 직접 호출 0. 드라이런에서는 콘솔에 **아무것도 쓰지 않는다.**
**AC**: AC-AUTOPATCH-015 · AC-AUTOPATCH-017 · AC-AUTOPATCH-018 · AC-AUTOPATCH-019

### M6 — 멱등 · 검증 읽기 (cycle_type=tdd)

**요구·설계 지시**: 전달 전 기존 점유 재조회로 중복 방지(멱등은 **생성 산출물 수준**에서 성립),
**사람이 실행한 뒤** `precheck_patch` 재조회로 건별 확인.
불일치는 보고만 하고 자동 보정 금지. 0건 생성 시 **실행 여부·절차 재확인 안내**
(**[v0.1.3]** "Patch 편집기 안내"는 철회됐다 — `ASSUMPTION-75`·`-76` 둘 다 NEGATIVE로
그 원인 설명이 반증됐다. REQ-AUTOPATCH-024 참조).
**AC**: AC-AUTOPATCH-020 · AC-AUTOPATCH-021 · AC-AUTOPATCH-022

### M7 — 툴 배선 · 회귀 · PRESERVE (cycle_type=tdd)

**요구·설계 지시**: `server/preshow/TOOLS_REGISTRATION.md`의 5지점으로 `apply_vectorworks_patch`를
등록하고 **dispatch로 검증**한다. 1단계 공개 계약 무변경을 확인한다. PRESERVE 게이트를
**비공허하게** 증명한다(금지 변경을 심었다가 되돌린다).
**AC**: AC-AUTOPATCH-023 · AC-AUTOPATCH-024 · AC-AUTOPATCH-025

### M8 — 라이브 종단 검증 (cycle_type=none) **[v0.1.5 재정의]**

**요구·설계 지시**: 실기 onPC에서 대조 → 후보 승인 → 드라이런 → **사람 실행** → 검증 읽기를
왕복하되, **4관문으로 나눠 책임과 실패 모드를 분리해 기록한다** — G1 서버 전달(콘솔 쓰기 0건) ·
G2 사람 실행(받은 것을 그대로) · G3 서버 검증(건별·자동 보정 0) · G4 원복(제거 확인 기록).
되돌릴 수 없으므로 **테스트 쇼파일**에서만 수행한다.
**G1 통과 + G2 실패는 유효한 결과**다 — 사람 실행 경로는 한 번도 시험된 적이 없고, 그 실패는
REQ-AUTOPATCH-018을 다시 열어야 한다는 새 실측이다.
**표시 문자열 판별 실험**(이름 `FixtureType k`인 타입을 index `j≠k`에)을 같은 세션에서 수행한다.

> **[2026-08-07 사용자 결정 — 착수 전제 ④⑤⑥이 확정됐다]** 정본 등기는 `spec.md` §C
> 「사용자 결정 대기」다. 아래 ①~⑥의 논거·선택지는 근거 보존을 위해 **그대로 남긴다** —
> 확정값만 여기 먼저 적는다.
>
> - **④ 자원 분리 = ㉠ FID 대역만 분리(501~503), 주소는 도면 그대로.**
>   **㉠의 형제 경로 경고는 그대로 유효하다** — 세션 전 **드라이런으로 적격 대상 수를 먼저
>   확인**하고 **0건이면 ㉡(도면 재작성)으로 내려간다.** 0건 세션은 `G1 미검증`이며 M8 PASS가 아니다.
> - **⑤ 원복 절차 = P5-D**(세션 전 GUI Save As 사본 → 세션 후 Load) **+ P5-0 필수**
>   (`Delete Plugin <slot>` 역순, responder 자기 슬롯 금지). P5-C는 무해한 병행 조사로 허용.
> - **⑥ `names` = `ZZAP1` · `ZZAP2` · `ZZAP3`**(공백·인용부호·대문자 `CD` 없음). 키 확보 절차는
>   아래 ⑥ 본문이 정본 — **리포트 payload를 한 번 뜨고 동결**한 뒤 드라이런의
>   `plan.candidates[].id`를 복사한다.
>
> **⑦ [신설 · AC-026④ ㉢ 승격] `P5 절차가 세션 전에 문서로 확정되지 않으면 세션에 착수하지
> 않는다.`** 사용자가 ㉢(P5를 차단 조건으로 승격)을 택했으므로 `acceptance.md`는 **개정하지
> 않는다**(AC 27 · AC-026 ①~⑦ 불변). 대신 그 강제가 **여기**에 있다. 구체적으로 세션 착수 전
> `progress.md` §E.2 M8 절에 **① 스냅샷 파일명 ② 스냅샷을 뜬 시각 ③ 재로드 절차 ④ 재로드 후
> responder 재배포·OSC 토글 계획**이 적혀 있어야 한다.
>
> **[HARD] ㉢은 "제거 불가" 상태를 배제하지 않는다.** P5-D 행이 *"스냅샷이 없거나 로드 실패 →
> A/B/C로 폴백"*을 스스로 명시하고 폴백 3안은 전부 `[추정]`이다. **실제로 제거하지 못한 채
> 세션이 끝나면 AC-026④는 여전히 판정 불가**이며, 그때는 **AC-026⑤대로 "G4에서 제거 수단
> 부재로 실패"라 적고** ㉠·㉡을 사용자에게 다시 묻는다. 그 상태를 "통과"로 적지 마라.

**착수 전제**: ① 독립 코드 감사 PASS — **[round16 #3 정정] round11·12·13·14·15·16
여섯 라운드 전부 FAIL이었다.** 이전 판은 *"round11·12·13·14 넷 다 FAIL이었다"*에 멈춰
**round15를 누락한 stale**이었고, 그 옆의 `M8-REDEFINITION-DRAFT.md` P1은 같은 시점에
이미 "다섯 라운드"라 적고 있었다 — **반례가 형제 문서에 있었다.** round14는 처음으로
치명 0건·fail-open 0건이었고 두 감사자 모두 "차단 문구 결함만 고치면 코드 축은 GO"로
판정했으나, round15는 *"코드는 옳은데 그것을 지키는 테스트가 게이트가 아니다"*로,
round16은 *"게이트를 네 표에 붙이고 형제 두 표에는 붙이지 않았다"*(뮤테이션 79건 KILL
81.0% · 치명 SURVIVED 1 · 안전 high 3)로 다시 FAIL했다. **round16 지적 반영에 대한
재감사가 통과해야 한다** · ② 세션 전 쇼파일 테스트용 재확인 · ③ 파괴적 조작 전 사전 상태 기록 ·
④ 테스트 자원 분리 — **[round16 추가 · 사용자 결정 대기] 분리는 FID 대역(`fid_range`)으로만
가능하다.** `server/vwx/apply.py:127`이 `HandoffEntry`의 `address`는 **"언제나 도면 주소
그대로"**라고 못박고 있고 `patchplan.plan_addresses`는 겹치는 항목을 **제외**할 뿐
**옮기지 않는다**(*"빈 주소를 찾아 옮겨 붙이는 경로가 이 함수에 없다"*). 따라서 유니버스·주소를
기존과 분리하려면 **1단계에 넣는 도면을 그렇게 만드는 수밖에** 없다 — 툴 인자로는 불가능하다.
세션 전에 사용자가 **㉠ FID 대역만 분리하고 주소는 도면대로 간다** / **㉡ 분리된 유니버스로
도면을 다시 만든다** 중 하나를 골라야 한다(`spec.md` §C 「사용자 결정 대기」 등록).
**[round17 추가 · ㉠의 형제 경로 경고]** ㉠은 주소가 도면대로 나가므로 그 주소를 기존
픽스처가 점유하고 있으면 항목이 **제외**된다(재배치 경로 없음). 도면 주소가 전부 기존 리그와
겹치면 **적격 대상이 0건**이 되어 ⑥을 지켜도 세션이 아무것도 증명하지 못한다 —
㉠을 고르면 **세션 전 드라이런으로 적격 대상 수를 먼저 확인**하고 0건이면 ㉡으로 내려가라 ·
⑤ **원복 절차 사전 합의** — **[round17 추가]** 선택지는 4안이며
`M8-REDEFINITION-DRAFT.md` §3 「P5 선택지」가 정본이다:
**P5-A** `Delete Fixture <fid>`(`[R]+[추정]`, 위험 최상) ·
**P5-B** 매크로+목적지 상대 삭제(`[M]` 기법 + `[추정]` 동사, A보다 높은 위험) ·
**P5-C** 객체 모델 삭제 메서드 조사(조사만 하면 위험 0) ·
**P5-D** 세션 전 쇼파일 스냅샷 → 세션 후 재로드(**권고 기본값**, 위험 가장 낮음).
**P5-0(임포트한 플러그인 슬롯 제거)은 어느 안을 고르든 필수**다.
**P5-D의 강점은 문법 증거가 아니라 FID·슬롯 오지정 위험이 0이라는 구조적 성질에서 온다** —
Save As / Load 콘솔 절차는 전면 미실측이고, `server/safety/gate.py:286-293`이 restore를
의도적으로 미구현으로 둔 사유를 명시한다. 사용자가 **세션 전에** 하나를 확정해야 한다
(`spec.md` §C 「사용자 결정 대기」 등록) ·
⑥ **[round15 #6 신설 · round16 #2 전면 정정] 후보→픽스처 이름 매핑(`names` 인자) 사전 작성.**
`design.md` §2.3이 "이름 없는 후보는 `fixture_name_missing`으로 **제외**하고 이 계층은 이름을
지어내지 않는다"고 못박고 있으므로, `names` 없이 세션에 들어가면 **대상이 구조적으로 0건**이 된다.
형식은 `{후보 식별자: 콘솔에 만들 픽스처 이름}` JSON 객체다
(`tools.py` 스키마: *"Candidate id -> the fixture name to create. A candidate with no name here
is excluded with a reason; this layer never invents a name."*).

  **[round16 #2] 이전 판은 "1단계 리포트의 `missing_in_console` 식별자를 그대로 키로 쓴다"고
  적었다 — 거짓이다. 그대로 준비하면 세션 당일 전 항목이 `fixture_name_missing`으로 제외된다.**
  키는 리포트에 존재하지 않는다. `server/vwx/patchplan.py`의 `_candidate_id`(약 1005-1021)가
  **여섯 값의 sha256 해시**로 만든다 — **사람이 손으로 만들 수 없다**:

  ```python
  identity = {"address": address, "detail": detail, "instrument_type": instrument_type,
              "source_index": index, "unit_number": unit_number, "universe": universe}
  encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
  return "vwx-missing-" + sha256(encoded.encode("utf-8")).hexdigest()[:16]
  ```

  **얻는 방법은 하나뿐이다** — 1단계 리포트를 넣고 `apply_vectorworks_patch(report=…,
  dry_run=true)`를 **한 번 호출**해 payload의 `plan.candidates[].id`를 **그대로 복사**한다.

  **[HARD] 그리고 그 1단계 리포트 payload를 동결한다 — 재생성하지 않는다.** 이것이 ⑥의
  실질 계약이다. `source_index`가 해시 입력이고 그 값은 `missing_in_console`의
  **행 순서**(`enumerate`)에서 온다(`_candidates_from_report`, 약 951-960행). 도면을 다시
  export하거나 1단계 대조를 다시 뜨면 행 순서가 바뀔 수 있고, 그러면 **준비한 `names`의 키가
  전부 무효**가 되어 세션 당일 모든 후보가 `fixture_name_missing`으로 제외된다 —
  **대상 0건**, round15 #6이 경고한 바로 그 상태다. 그래서 세션 준비는
  ⓐ 1단계 리포트 payload를 **한 번** 뜬다 → ⓑ 그 payload를 파일로 동결해
  `progress.md` §E.2 M8 절에 붙인다 → ⓒ 그 payload로 드라이런을 한 번 돌려 나온
  `plan.candidates[].id`를 키로 `names` 표를 만들어 함께 붙인다 → ⓓ **세션 당일에는 ⓑ의
  동결본을 그대로 `report=` 인자로 넘긴다**(새로 뜨지 않는다) 순서로 한다.
  ⓑ를 다시 떠야 할 사정이 생기면 **`names` 표 전체를 ⓒ부터 다시 만든다.**

**대상 0건 세션은 G1을 검증하지 못하며 M8 PASS로 적지 않는다**(`acceptance.md`
AC-AUTOPATCH-026 아래 고지 블록).

**[round15 #3] G1 전달물 원문 보존 의무**: 세션 중 `lua_source` 전문 · 사람에게 건넨 실행
절차 전문 · 대상 표를 **G2 착수 전에** `progress.md` §E.2 M8 절에 그대로 적는다. 이 보존본이
없으면 G2 실패를 "코드 결함인가 아닌가"로 가를 수 없고, AC-AUTOPATCH-026⑥의 면책도
원용할 수 없다(AC-026① · ⑥의 판별 절차).
**AC**: AC-AUTOPATCH-026

---

## §C. 라이브 세션 회계

**계획 2회.** 1단계는 라이브 0회였지만 본 SPEC은 콘솔에 쓰므로 실기 없이 닫을 수 없다.

| 세션 | 마일스톤 | 성격 | 파괴성 |
|---|---|---|---|
| 1 | M0 | 전제 측정 | 읽기 4건 + **테스트 쇼파일에 1~3대 패치**(사용자 승인 후, 세션 후 제거) |
| 2 | M8 | 종단 검증 | **사람이** 테스트 쇼파일에 승인 항목 패치(세션 후 제거). 서버 쓰기 0건 |

두 세션 모두 **운영 쇼파일에서 수행하지 않는다.** 세션 시작 전 사용자에게 쇼파일이 테스트용임을
확인받고, 그 확인을 `progress.md`에 기록한다.

---

## §D. 제약

1. `console/lua/**` · `server/safety/**` · `server/prechk/**` · `server/paperwork/**` ·
   `server/looks/**` 무변경(PRESERVE 게이트).
2. `server/vwx/**` 신규 코드는 `server.bridge` · `pythonosc`를 import하지 않는다
   (`server/tests/test_architecture.py:33,49`).
3. ruff: py311 · line-length 100 · select E,F,W,I,UP,B,SIM.
4. 새 판정 어휘는 `server/vwx` 자체 레지스트리에 등록한다 — `server/prechk/verdicts.py`는 PRESERVE다.
5. 신규 런타임 의존성 **0건**을 목표로 한다. 필요해지면 사용자 승인 항목으로 승격한다.
6. 드라이런 경로는 **콘솔 읽기만** 허용된다(타입 라이브러리 열거·주소 점유 확인). 쓰기 0.

---

## §E. 테스트 골격

| 파일 | 무엇을 지키나 |
|---|---|
| `server/tests/test_autopatch_candidates.py` | 입력 정규화 · 미대조 리포트 거부 · 비선택 기본값 |
| `server/tests/test_autopatch_fid.py` | 범위 내 배정 · 범위 미제공 거부 · 슬롯 유래 값 금지 · 충돌 사전검사 on/off |
| `server/tests/test_autopatch_types.py` | 라이브러리 열거 · 퍼지 매칭 · 부재 시 하드 스톱 · 점유폭 일치 |
| `server/tests/test_autopatch_lua.py` | `AddFixtures` 형태 · **CD 0건(비공허)** · 점유폭 간격 · 점유 주소 제외 |
| `server/tests/test_autopatch_execute.py` | **사람 실행 전달 · 패치 실행 발화 0건(비공허)** · 별도 배포 경로 0 · `execution_port` 직접 호출 0 · 드라이런 무쓰기 |
| `server/tests/test_autopatch_verify.py` | 멱등 · 검증 읽기 건별 · 불일치 보고 · 자동 보정 0 |
| `server/tests/test_autopatch_tool.py` | 5지점 등록을 **dispatch로** 검증 · 파라미터 스키마 |
| `server/tests/test_autopatch_contract.py` | 1단계 공개 계약 골든 스냅샷(최상위 키 집합 + 키별 타입 시그니처) 비교 |

테스트 더블은 `server/tests/test_prechk_tool.py:41-228`의 `RigPort` / `RecordingExecutionPort` /
`_registry()` 관례를 복사한다. **"0건" 주장에는 전부 비공허성 대조군을 붙인다** —
금지 대상을 일부러 심어 스캐너가 실제로 잡는지 확인한다.

---

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

**권고: sub-agent 순차(Mode 5).**

근거: (1) M0가 M2·M3·M6의 설계를 확정하므로 **의존 사슬이 직선**이다 — 병렬 이득이 없다.
(2) 되돌릴 수 없는 쓰기를 다루므로 **한 번에 한 사람이 보는 편**이 안전하다.
(3) 라이브 세션 2회가 사용자 접점을 포함하므로 동시 실행이 오히려 조율 비용을 만든다.

확정 기록은 `progress.md` §F가 소유하며, 어긋나면 **§F가 이긴다.**
