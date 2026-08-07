# SPEC-COPILOT-AUTOPATCH-001 — 구현 계획 (plan)

status: draft (v0.1.4, 2026-08-06) · Tier L · 마일스톤 M0~M8 · 라이브 세션 2회 · **M5 축소(반자동 실행 모델 amendment)**

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

**착수 전제**: ① 독립 코드 감사 PASS(round11·12 모두 FAIL이었다 — 세 번째 자기수정에 대한
재감사가 통과해야 한다) · ② 세션 전 쇼파일 테스트용 재확인 · ③ 파괴적 조작 전 사전 상태 기록 ·
④ 테스트 자원 분리(기존과 겹치지 않는 FID·유니버스) · ⑤ **원복 절차 사전 합의**.
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
