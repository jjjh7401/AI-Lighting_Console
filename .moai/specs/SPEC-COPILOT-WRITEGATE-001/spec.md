---
id: SPEC-COPILOT-WRITEGATE-001
title: "쓰기 경로 무결성 — 좌표 기록의 게이트 risky 분류 + 승인 흐름 (Write-Path Integrity)"
version: "0.2.0"
status: in-progress
created: 2026-08-05
updated: 2026-08-05
author: manager-spec
priority: P0
phase: "Phase 2 안전 계층 — 쓰기 경로 무결성"
module: "server/safety/blacklist.yaml, server/tests/test_safety_ruleset.py, server/tests/test_spatial_arrange.py, server/tests/test_overlap_preserve.py (비준 그랜트)"
lifecycle: spec-anchored
tags: "safety-gate, risky-classification, approval-flow, closed-set-revision, coordinate-write, showfile-backup, ratification, deferred-resolution"
tier: M
related_specs: [SPEC-COPILOT-SPATIAL-001, SPEC-COPILOT-MVP-001, SPEC-COPILOT-OVERLAP-001, SPEC-COPILOT-GROUPGEN-001, SPEC-COPILOT-EXECREF-001, SPEC-COPILOT-DEPLOY-001]
---

# SPEC-COPILOT-WRITEGATE-001 — 쓰기 경로 무결성

> **이 SPEC이 닫는 구멍**: 앱은 오늘 **사람 확인 없이 쇼파일을 변형할 수 있다.** `Set Fixture … Pos*`가 `safe`로 분류되므로(`server/safety/classify.py:241` 종단 반환) 게이트가 승인 카드를 띄우지 않고, showfile 백업 규칙 ③(`server/safety/gate.py:362-365`)도 발동하지 않는다.
>
> **가설이 아니라 관측이다**: SPATIAL M6 라이브에서 **요청하지 않은 좌표 기록 54건**이 무승인으로 콘솔에 도달했다(SPATIAL `progress.md` §E.2.20). 모델이 이전 턴의 미완 목표를 이어 완성한 것이고 의도는 합리적이었으나 **그 사이에 사람이 없었다.** 같은 턴의 `Go+ Page 1.202`는 카드를 정상 표시했다 — **게이트는 건강하고 쓰기 명령만 그 그물을 통과한다.**
>
> **파이프라인의 위치**: MVP M4가 세운 3단 게이트의 **분류 단계 하나**를 고친다. 새 계층도, 새 승인 창구도 만들지 않는다.

## A. 배경

### A.1 무엇이 이미 작동하는가 (건드리지 않는다)

`REQ-SPATIAL-024`의 세 절 중 둘은 이미 참이다 — 실측으로 확인했다(`research.md` §2, §6):

| 절 | 상태 | 근거 |
|---|---|---|
| **단일 관문** | ✅ 충족 | `screen()`이 유일 경로(`gate.py:299-301` @MX:REASON) + 클리어런스 토큰이 미승인 실행을 구조적으로 거부(`gate.py:604-610`) |
| **감사** | ✅ 충족 | `log_executed`가 위험 분류와 무관하게 **모든** 송신에 기록(`gate.py:613-616`) — §E.2.20이 54건 전부를 감사 로그로 재구성했다 |
| **승인 흐름** | ❌ **오늘 거짓** | `safe` 분류 → `held`가 비어 승인 블록·백업 규칙 ③ 둘 다 건너뛰어진다 |

그리고 SPATIAL 자체의 4중 방어(원좌표 백업 · 재조회 검증 · 복원 번들 · 범위 봉쇄)는 **설계대로 작동했다** — §E.2.20의 복구도 그 경로로 했고 쇼파일 잔여 0이다. 즉 `[DEFERRED]`는 *"방어가 없다"*가 아니라 *"승인 게이트 계층의 방어만 없다"*다.

### A.2 발화 주체가 둘이라는 사실이 설계를 결정한다

| 경로 | 발화자 |
|---|---|
| 조립기 | `arrange_write_commands` (`tools.py:917-926`) — 관측된 54건이 이 경로 |
| 모델 직접 작성 | `run_commands` = `TOOL_NAMES[0]`에 임의 커맨드라인. 룰북이 **산문으로만** 금지 |

둘은 `bundle_gate.screen(commands)`(`tools.py:1142-1143`)에서 합류한다. **커맨드 문면 분류만이 두 경로를 동시에 덮는다** — 툴 핸들러에 승인을 다는 설계는 직접 작성 경로를 열어둔다.

### A.3 이 저장소는 이미 우회로를 갖고 있고, 그것이 부채다

`build_toolset(group_approval_port=…)`(`tools.py:1113-1121`)은 *"because `Store Group`/`Label Group` classify as `safe` … and so never reach the gate's own approval stage on their own"* 라고 스스로 적는다. **게이트가 쓰기를 분류하지 못해 툴 계층에 제2 승인 창구가 생겼다.** 본 SPEC은 그 부채를 좌표 축에 복제하지 않는다.

### A.4 되돌려진 첫 시도 — 설계가 아니라 경계가 막았다

SPATIAL run-phase가 `blacklist.yaml` v1→v2에 `"Set Fixture"`를 넣어 **기능 테스트 3건 + 뮤테이션 RED를 통과시켰다**(`progress.md:298-299`). 막은 것은 두 경계 가드다: SPATIAL 자신의 `server/safety/**` PRESERVE 선언, 그리고 `test_overlap_preserve.py::TestSafetyChokepointFileSet`. **본 SPEC이 `server/safety/`를 소유하므로 전자는 소멸하고 후자는 비준으로 처리한다.**

## B. 요구 (GEARS)

### B.1 분류 — 폐쇄집합의 의도적 개정

- **REQ-WRITEGATE-001** [Ubiquitous] — the 폐쇄집합 개정 **shall** `server/safety/blacklist.yaml`의 **version 범프(1 → 2)** 와 **엔트리 정확히 1건 추가**(`"Set Fixture"`)로 성립하며, 그 외 어떤 엔트리·집합·스키마도 변경하지 않는다. 이는 `blacklist.yaml:2-5`가 규정한 *"revision of this file with a version bump"* 절차의 첫 실행이며, `classify.py:32-43`이 EXECREF-001의 `RECOGNIZED_REFERENCE_TYPES` 개정에 부여한 것과 **동일한 무게**로 취급된다.
- **REQ-WRITEGATE-002** [Event-driven] — **When** 픽스처 패치 쓰기 커맨드가 게이트 스크리닝에 들어가면, the 게이트 **shall** 이를 `risky=True`로 분류하고 (a) 승인 카드를 띄우며 (b) showfile 백업 규칙 ③ `before_risky_execution()`을 발동한다. 승인 거부 시 콘솔 송신은 **0건**이다.
- **REQ-WRITEGATE-003** [Unwanted] — the 본 SPEC **shall not** 게이트 밖에 새로운 승인 창구를 만든다 — 툴 계층 승인 seam 신설, `screen()`에 호출자측 risky 선언 인자 추가, 제2 분류기 도입은 모두 금지된다. 분류는 `classify_command` **단일 함수** 안에서 성립한다(`classify.py:169-172` @MX:ANCHOR · `AC-EXECBODY-009`).
- **REQ-WRITEGATE-004** [Ubiquitous] — the 분류 **shall** 발화 주체와 무관하게 동일하다: 조립기가 만든 번들이든 모델이 `run_commands`에 손으로 쓴 줄이든, 같은 문면은 같은 판정을 받는다.
- **REQ-WRITEGATE-005** [Event-driven] — **When** 패치 쓰기가 매크로 본문 또는 배포 대상 Lua 소스의 **`Cmd()` 문자열 리터럴**에 담겨 간접적으로 도달하면, the 시스템 **shall** 각각 expand-or-hold(`expand.py:110-112`)와 배포 스캔(`deploy/scan.py:138-146`)에서 **수정 없이** 이를 잡는다 — 그러므로 분류는 기존 `category` 값을 유지하며 신규 category 값을 도입하지 않는다(신규 값은 두 소비처에서 조용히 통과한다 — `research.md` §8).
  - ⚠ **`Cmd()` 리터럴 한정임을 명시한다.** `deploy/scan.py`는 `Cmd(...)`의 문자열 인자만 추출하므로(`_CMD_HEAD`), MA3 Lua API로 패치를 직접 대입하는 플러그인은 **`Cmd()`를 하나도 발화하지 않아 finding도 `dynamic_call`도 만들지 않는다.** 이 경로는 본 SPEC이 닫지 않는다(§D). 초안의 문면은 "배포 대상 Lua 소스"를 통째로 덮는다고 읽혔고 그것은 과잉 주장이었다 — `REQ-SPATIAL-024`의 두 뜻 읽기와 **같은 결함 계열**이며, 그 결함을 지적한 SPEC이 같은 실수를 했다는 사실을 남긴다.

### B.2 무엇을 바꾸지 않는가 (범위 봉쇄)

- **REQ-WRITEGATE-006** [Unwanted] — the 개정 **shall not** `Store` 계열(`Store Group`·`Store Preset`·`Store Cue`·`Store Page`·`Store Macro`)·`Assign`·`Copy`·`Label`의 분류를 변경한다. `Store Group`의 risky 화는 **명시적으로 본 SPEC의 범위 밖**이며(§D) 별도 결정 게이트를 갖는다.
- **REQ-WRITEGATE-007** [Unwanted] — the 개정 **shall not** `server/measurement/corpus.yaml`을 수정한다. 코퍼스 `:10`의 *"non-risky verbs only"* 불변식은 **문면 그대로 보존**되며, 21 시나리오·대표 작업 10종은 하나도 교체되지 않는다.
- **REQ-WRITEGATE-008** [Unwanted] — the 개정 **shall not** `Set Selection MAtricks '<property>' <v>`(프로그래머 상태)와 `Set Macro <p>.<l> Property 'Command' '<safe command>'`(매크로 저작)의 분류를 변경한다. 보장 기전은 **인용이 아니다**: `_match_blacklist`는 동사가 `Set`에 맞고 **동시에 인용되지 않은 인자 하나가 `Fixture`에 맞을 것**을 요구하므로(`classify.py`), 위 두 형태를 막는 것은 *"`Fixture`를 철자한 비인용 인자가 없다"*는 사실이다. 실측: `Set Selection MAtricks PhaseFromX 0`(**비인용**)도 `safe`이고 `Set Selection MAtricks Fixture 0`은 `risky=True`다 — 즉 `PhaseFromX`의 인용 여부는 무관하다. 초안이 인용을 기전으로 적었던 것은 오기이며, `Store` 축 후속 SPEC이 *"인용이 프로그래머 상태를 보호한다"*를 물려받으면 안 되므로 정정한다.

### B.3 예외 목록 — 비준

- **REQ-WRITEGATE-009** [Where] — **Where** 어떤 설계로도 `server/safety/` 아래 파일 접촉을 피할 수 없는 경우(`screen()`에 호출자측 risky seam이 없다는 구조적 사실 — SPATIAL `progress.md:294-296`), the 개정 **shall** `test_overlap_preserve.py`의 `_SAFETY_EXPECTED_DELETIONS`에 **항목 1건**(`"server/safety/blacklist.yaml": 1`)과 `_SAFETY_ALLOWED_DELETED_LINES`에 **삭제 행 1건**(`version: 1`)을 추가하며, 그 추가는 **같은 파일에 이미 존재하는 그랜트 블록 2건**(`:64-77` SPATIAL M3 룰북 자산 · `:88-95` 상류 어휘 확장)과 **동일한 형식**의 날짜·SPEC·`user-approved` 표기 주석을 동반한다.
- **REQ-WRITEGATE-010** [Unwanted] — the 비준 **shall not** 트립와이어를 약화시킨다: 파일 집합·삭제 카운트·삭제 행 텍스트의 **세 겹 고정은 유지**되고 새 항목도 같은 세 겹을 받는다. 넓히는 것은 허용 범위이며 **판정 방식이 아니다**.

### B.4 `[DEFERRED]` 해소

- **REQ-WRITEGATE-011** [Ubiquitous] — the 본 SPEC **shall** `AC-SPATIAL-031` 전체와 `REQ-SPATIAL-024`의 **승인 흐름 절**의 `[DEFERRED]` 표기를 해소하고, SPATIAL `spec.md` REQ-020의 규칙 ③ 연동 절도 함께 갱신한다 — 정본은 SPATIAL 문서이며 본 SPEC이 그 판정을 운반한다.
- **REQ-WRITEGATE-012** [Event-driven] — **When** 분류가 착지하면, the `test_spatial_arrange.py::test_a_coordinate_bundle_is_not_yet_classified_risky` 트립와이어 **shall** 삭제되지 않고 **승인 흐름 단정으로 교체**된다 — 그 테스트의 실패 메시지가 스스로 지시한 처리(*"must be replaced by the approval-flow assertions it was standing in for"*)를 그대로 따른다.

### B.5 라이브 판정

- **REQ-WRITEGATE-013** [Ubiquitous] — the 라이브 세션 판정 **shall** 폐쇄 판정 어휘(`GO`/`NEGATIVE`/`CONDITION_NOT_MET`/`INCONCLUSIVE`/`REOPEN_SCOPE`)와 행두 접두(`GO:`/`DESCOPE:`/`SKIP:`/`REOPEN:`)로 `progress.md §E`에 기록된다. 매핑 표는 본문 내장(SPATIAL REQ-SPATIAL-026 계승 — 교차 SPEC 포인터 상속은 결함으로 판정된 바 있으므로 아래 표가 본 SPEC의 정본이다).

| 판정 어휘 | 행두 접두 | 비고 |
|---|---|---|
| `GO` | `GO:` | 전제 성립 — 해당 축 진행 |
| `NEGATIVE` | `DESCOPE:` | 전제 부정 — 해당 축 강등·중단 |
| `INCONCLUSIVE` | `DESCOPE:` + `verdict=INCONCLUSIVE` 키 **의무** | 판정 불능 |
| `CONDITION_NOT_MET` | `SKIP:` | 전제 미성립(프로브 불가·미실행) |
| `REOPEN_SCOPE` | `REOPEN:` | 범위 재개 필요 |

- **REQ-WRITEGATE-014** [Unwanted] — the 라이브 관측 **shall not** 성공 기준의 **유일 근거**가 되지 않는다. 성공은 **구조**(단위 테스트 + 뮤테이션)에 걸리고 라이브는 보조 증거다 — 모델 준수를 성공 기준으로 세울 수 없다는 판정(계획서 §위험 3)을 계승한다.

## C. 환경 및 전제

### C.1 검증 가능성

| 항목 | 기계 검증 | 수단 |
|---|---|---|
| 좌표 기록의 `risky=True` | **YES** | `classify_command` 단위 — 콘솔 무접촉 |
| `before_risky_execution()` 발동 | **YES** | 모의 백업 훅 |
| 승인 거부 시 송신 0건 | **YES** | `DenyAllApprovalPort` + 기록 콘솔 |
| `Store`·MAtricks·`Set Macro` 분류 불변 | **YES** | 회귀 단정 |
| 코퍼스 불변식 보존 | **YES** | `corpus.yaml` byte-diff 0 + `gate_anomalies == {}` |
| 매크로 본문·Lua 소스 간접 경로 | **YES** | `expand.py`·`deploy/scan.py` 단위 |
| **라이브에서 카드가 실제로 뜨는가** | **조건부** | ASSUMPTION-68 — M2 라이브 1턴 |
| **과잉매칭 범위의 운영 수용성** | **NO** | ASSUMPTION-69 — 사람 결정(M0) |

### C.2 PRESERVE

- `server/spatial/**` · `server/orchestrator/tools.py`의 arrange 경로 — **무변경**. 4중 방어는 읽기 전용으로 계승하고 회귀로만 확인한다.
- `server/measurement/**` — **byte-diff 0**(REQ-WRITEGATE-007).
- `server/safety/` 중 `classify.py`·`ruleset.py`·`gate.py`·`expand.py` — **무변경**. 개정은 `blacklist.yaml` 데이터에만 일어난다(설계 귀결: 로더 스키마도 손대지 않는다).
- `server/looks/**` · `server/fx/**` · `server/scene/**` · `console/lua/**` — 무접촉.

### C.3 ASSUMPTION

- **ASSUMPTION-68 (라이브 승인 카드)** — 개정된 폐쇄집합이 라이브 onPC에서 좌표 기록에 실제 카드를 띄우고, 승인 후 기록이 정상 완료된다. **기계 검증 완료 · 라이브 미검증**(`research.md` §5). NEGATIVE면 분류는 유지하되 카드 경로 결함으로 별건 처리.
- **ASSUMPTION-69 (과잉매칭 수용성)** — `Set Fixture` 엔트리는 좌표뿐 아니라 **모든 픽스처 패치 쓰기**를 잡는다(`Set Fixture 11 Name '…'` 등). 이 과잉매칭이 운영상 수용 가능하다. **미검증 — M0 결정 게이트에서 사람이 확인한다.** NEGATIVE면 엔트리 형상을 재설계하되, 프로퍼티 이름 열거는 `blacklist.yaml:3-4`의 *"open-ended lists are prohibited"*에 걸린다는 제약을 함께 고려한다.
- **ASSUMPTION-70 (4중 방어 무변경 작동)** — 승인 카드가 끼어든 뒤에도 원좌표 백업·재조회·복원 번들·범위 봉쇄가 그대로 작동한다. **부분 검증**: 실측 파탄 5건 중 2건이 *제품이 옳고 하네스가 낡은* 경우임을 확인했다(`research.md` §6). M1 회귀가 판정.

## D. 범위 밖 (Out of Scope)

### Out of Scope — `Store` 계열의 risky 화
- `Store Group`을 risky로 만드는 일(계획서 "후보 3", `run_commands` 우회 경로)은 **본 SPEC에 흡수하지 않는다.** 사용자 결정(2026-08-05 범위 분리). **실측 근거(정정됨)**: 엔트리 `Store`는 `corpus.yaml`의 21 시나리오 중 **10건 / 대표 10종 중 5종**과 충돌하고, 엔트리 `Store Group`은 **3건 / 1종**(`group-create-1/2/3`)과 충돌한다. 그리고 `Store Group`은 DEPLOY 테스트 **정확히 3건**을 깨뜨린다 — `Store Group 3`을 정캐논 안전 픽스처로 쓰는 `test_deploy_gate_e2e` · `test_deploy_pipeline` · `test_deploy_scan`. ⚠ **초안은 "13건 / 7종"이라 적었고 그것은 틀렸다** — `Store|Set|Assign|Copy` 광역 정규식으로 센 **커맨드 13개**를 `Store`의 시나리오 수로 옮겨 적은 것이다(대표 작업도 6→7로 틀렸다). 결정 자체는 정정된 숫자에서도 유지된다(`group_create`는 AC-MVP-001 10대 대표 중 1이고, DEPLOY 충돌은 코퍼스 규모와 무관하다) — 그러나 **대안의 비용을 과대계상했다는 사실을 남긴다.**
- 남는 손실을 명시한다: 손으로 쓴 `Store Group`의 무승인 경로는 이번 창에 **열린 채로 남는다.** 이는 관측 사고가 아니라 가설이며(관측된 54건은 전부 좌표 기록), GROUPGEN의 툴 계층 seam이 조립기 경로는 이미 덮는다.
- 본 SPEC이 **폐쇄집합 개정 절차의 첫 선례를 만들므로**, 후속 SPEC은 절차를 재발명하지 않고 엔트리 추가와 코퍼스 갈래 결정만 다루면 된다.

### Out of Scope — 툴 계층 승인 seam의 정리
- GROUPGEN `group_approval_port`(`tools.py:1071`)를 게이트 분류로 대체하고 제거하는 일은 `Store` 축이 열린 뒤에만 가능하다. 본 SPEC은 **그 부채를 늘리지 않는 것**까지만 책임진다(REQ-WRITEGATE-003).

### Out of Scope — 복원 SEND 경로
- `server/safety/backup.py`에는 복원 송신 경로가 없고 `gate.py:283`이 그 자리를 의도적 미구현으로 표기한다. 규칙 ③ 스냅샷은 **발동 사실**까지가 본 SPEC의 범위이며, 되돌리기는 SPATIAL의 복원 번들(`tools.py:939-946`)이 계속 담당한다.

### Out of Scope — `rotx`/`roty`/`rotz` 기록 기능
- 방향 축 기록을 **가능하게 만드는** 일은 범위 밖이다(REQ-SPATIAL-022c가 v1 금지). 다만 `Set Fixture 11 Rotx '90.0'`가 **분류상 risky가 되는 것**은 본 SPEC의 귀결이며 의도된 것이다 — 방향 쓰기도 무승인 쇼파일 변형이므로.

### Out of Scope — 배포 플러그인의 Lua 직접 대입 경로
- `deploy/scan.py`는 `Cmd(...)`의 문자열 리터럴만 추출한다. MA3 Lua API로 패치를 직접 대입하는 플러그인(`f.posx = 5.0`, `AddFixtures{...}`)은 **`Cmd()`를 발화하지 않으므로 finding도 `dynamic_call`도 만들지 않고**, `pipeline.py:166`이 `destructive=False`로 등록하며, 호출 시 `expand.py:96-104`가 `hold=False`를 돌려준다 — **카드도 규칙 ③도 없다.** 본 SPEC은 이 경로를 **닫지 않는다.**
- **가설이 아니다**: 저장소 룰북 `server/rulebook/assets/v2.4.2/30_plugin_patterns.md:13-19`가 모델에게 *"Command lines CANNOT create fixtures. The patch is exactly TWO steps"*라고 가르치고 `:42-52`에 fid·name·패치 주소를 쓰는 `AddFixtures{...}` 예제를 싣는다. 즉 **저장소가 권장하는 패치 경로가 곧 이 구멍이다.**
- 남은 방어선: 배포는 deny-by-default이고 사람이 소스를 **한 번** 리뷰한다(`pipeline.py:150-160`). 그리고 이 잔여 위험은 `deploy/scan.py:10-16`이 **이미 규범적으로 선언**해 둔 것이다(REQ-MVP-027 — *"best-effort … the HUMAN REVIEW GATE remains the authoritative control"*). 본 SPEC이 만든 구멍이 아니다.
- 닫으려면 Lua AST 수준 스캔이나 패치 쓰기 능력 플래그가 필요하다 — 별도 SPEC의 몫이다.

### Out of Scope — Layout 요소 좌표 기록
- `Set Layout <l>.<e> 'PositionX' <v>`는 **오늘도 `safe`다.** 이는 저장소가 문서화한 두 번째 좌표 쓰기이며(SPATIAL `research.md:19`·`:103` — 포럼 moderator 확인, ASSUMPTION-56), SPATIAL `spec.md`가 Layout pool의 `PositionX`/`PositionY`를 **보조 공간 출처**로 명시한다.
- 본 SPEC의 엔트리는 `Set Fixture`이므로 이 형태를 잡지 않는다. 어떤 툴도 이 형태를 발화하지 않으니 제품이 깨지는 것은 아니지만, `run_commands`는 모델이 손으로 쓴 줄을 받으므로(REQ-WRITEGATE-004가 존재하는 이유) **경로가 열려 있다.** Layout 축 자체가 SPATIAL에서 `[DEFERRED]`이므로 함께 후속으로 넘긴다.

### Out of Scope — 정렬 어휘 개명 · 절단 고지 강제 · 축 점수 비교
- 계획서의 SPEC B/C/D. 본 SPEC과 파일 무교차이며 승인 흐름이 열린 뒤 병렬 가능하다.

## E. 성공 기준

| 기준 | 확인 수단 | 성격 |
|---|---|---|
| **픽스처 패치 행** 쓰기가 무승인으로 콘솔 도달하는 커맨드라인 경로 **0건** | 단위 + 뮤테이션 | 구조 |
| `before_risky_execution()` 발동 | 모의 백업 훅 | 구조 |
| 승인 거부 시 콘솔 송신 0건 | `DenyAllApprovalPort` + 기록 콘솔 | 구조 |
| `AC-SPATIAL-031` · `REQ-SPATIAL-024` `[DEFERRED]` 해소 | SPATIAL 문서 표기 갱신 | 문서 |
| 코퍼스 불변식 문면 무수정 + `gate_anomalies == {}` | byte-diff 0 + 기존 테스트 | 회귀 |
| `Store`·MAtricks·`Set Macro`·DEPLOY 픽스처 분류 불변 | 회귀 단정 | 회귀 |
| 매크로 본문·Lua 소스의 **`Cmd()` 리터럴** 간접 경로 차단 | `expand.py`·`deploy/scan.py` 단위 + 신규 category 뮤테이션 | 구조 |
| 트립와이어 개정이 날짜·소유자·승인 표기를 갖춘 그랜트 | 코드 리뷰 | 절차 |
| 닫지 않은 두 경로가 §D에 명시 (Lua 직접 대입 · Layout 요소) | 문서 | **정직성** |
| 라이브 1턴에서 카드 관측 | ASSUMPTION-68 | **보조 증거** |
