# SPEC-COPILOT-SPATIAL-001 — 인수 기준 (acceptance)

status: draft (v0.2.0, 2026-08-03) · Tier L · 본 문서는 spec.md의 요구를 관측 가능한 검증 기준으로 전개한다.

## §A. 개요

본 SPEC의 성공 기준은 세 층위다:

1. **무조건** — 공간 분석 계층(순수)·룰북·경계·안전 규율은 M0 판정과 무관하게 훼손되지 않는다.
2. **조건부(READ — ASSUMPTION-53 GO)** — 공간 판독 툴이 출하되고, 같은 지시가 배치에 따라 다른 커맨드를 낸다. **READ NEGATIVE면 SPEC 전체 중단**이므로 이 층위의 미달성은 "정직한 중단 기록"으로만 존재한다.
3. **조건부(WRITE — ASSUMPTION-54 GO)** — 배치 생성이 출하된다. NEGATIVE면 AC-SPATIAL-018~022/027/031은 `[DEFERRED]`로 정직하게 기록되고 READ 축은 전량 PASS여야 한다.

**부분 성공을 성공으로 위장하지 않되, 실패로도 위장하지 않는다.** `(LIVE)` 표시 AC는 실물 onPC 2.4.2 왕복으로만 판정되며 소프트웨어 AC와 구분 집계한다. 검증 천장(spec.md §C.1)의 NO 행 — 특히 **웨이브 방향의 실제 시각 효과** — 에 기계 증거를 주장하는 판정은 그 자체로 결함이다.

## §B. Given-When-Then 시나리오

### 시나리오 1 — 같은 지시, 다른 리그 (본 SPEC의 존재 이유)

- **Given** 픽스처 30대가 각각 1행×30 배치와 3행×10 배치로 패치돼 있다.
- **When** 두 리그에 같은 지시("왼쪽에서 오른쪽으로 웨이브")가 주어진다.
- **Then** 두 리그의 발화 커맨드가 **구조적으로 다르다** — 행 검출 결과(1행 vs 3행)와 선택 순서가 다르고, 그 차이가 기계로 판독 가능하다(정적). 무대 관측의 적합성은 사람이 판정하고 결론 문장으로 기록된다.

### 시나리오 2 — 좌표 없는 리그는 정직하게 강등된다

- **Given** 어떤 출처에서도 공간 데이터를 얻지 못하는 쇼파일이 있다.
- **When** 공간 연출이 지시된다.
- **Then** 명시적 강등 신호와 함께 기존 비공간 연출 경로가 실행된다. 좌표를 발명해 공간 연출을 위장하지 않는다.

### 시나리오 3 — 배치 생성은 백업→기록→재조회→복원 왕복이다

- **Given** 30대 파가 임의 좌표에 흩어져 있다.
- **When** 사용자가 "3×10 그리드로 정렬"을 요청하고 승인한다.
- **Then** 기록 전 원좌표가 백업되고, 기록 후 재조회가 목표 좌표와 일치하며, 리포트에 복원 번들이 동봉된다. 복원 번들 실행 시 재조회가 원좌표와 일치한다.

### 시나리오 4 — 날조 대조군이 판독 채널의 변별력을 세운다

- **Given** M0 프로브가 진행 중이다.
- **When** 존재하지 않는 프로퍼티 이름(`poszz`)이 판독·기록으로 발화된다.
- **Then** 실패가 관측되거나 — `ok`로 통과하면 **그 사실 자체가 `CONDITION_NOT_MET` 판정으로 기록**되고 값 대조 기반 판정으로 대체된다. 어느 쪽이든 대조군 없는 `ok` 채택은 발생하지 않는다.

### 시나리오 5 — 절단은 반드시 드러난다

- **Given** 판독 결과가 회신·왕복 예산을 넘기는 규모의 리그가 있다.
- **When** 공간 판독이 실행된다.
- **Then** 회신은 축소된 채로 오되 절단/캡 신호가 세워져 있다. 신호 없는 부분 판독은 발생하지 않는다.

### 시나리오 6 — 명시 대상 외에는 아무것도 기록되지 않는다

- **Given** 리그에 픽스처 30대가 있고 사용자가 그중 10대의 정렬만 요청했다.
- **When** 배치 생성이 실행된다.
- **Then** 나머지 20대의 좌표는 기록 전후 재조회에서 불변이고, rot* 는 어느 픽스처에서도 기록되지 않는다.

## §C. AC (GEARS 형식 — 통과 판정 방법을 각 AC에 명시)

### B.1 공간 판독 (READ)

#### AC-SPATIAL-001 — 패치 3D 판독 (조건부: READ GO, LIVE 포함)

**When** 공간 판독 툴이 호출되면, the 시스템 **shall** 픽스처별 `(fid, name, x, y, z)` 맵을 반환한다.

- 대상 요구: REQ-SPATIAL-001 · **통과 판정**: 단위(모의 포트) + 라이브 왕복 1건 — 물리적으로 아는 좌표와 판독값 일치.

#### AC-SPATIAL-002 — 출처 명시

The 회신 **shall** 어느 출처(patch 3D / layout pool)가 답했는지 담는다.

- 대상 요구: REQ-SPATIAL-002 · **통과 판정**: 출처 필드 부재 회신이 하나라도 있으면 FAIL. 두 출처 좌표의 합성 부재(코드 리뷰 + 단위).

#### AC-SPATIAL-003 — Layout pool 요소 맵 (조건부: ASSUMPTION-55 GO)

**When** Layout pool이 판독되면, the 시스템 **shall** children 반복으로 요소→오브젝트→(x,y) 맵을 구축한다.

- 대상 요구: REQ-SPATIAL-003 · **통과 판정**: 단위(모의 layout) + 라이브 1건. NEGATIVE 시 `[DEFERRED]` 기록.

#### AC-SPATIAL-004 — 좌표 발명 금지 (무조건, **뮤테이션 필수**)

**When** 일부 픽스처의 좌표 판독이 실패하면, the 맵 **shall** 그 픽스처를 사유와 함께 부재로 싣고 어떤 기본값도 채우지 않는다.

- 대상 요구: REQ-SPATIAL-004 · **통과 판정**: 판독 실패 주입 시 부재+사유 반환. **뮤테이션**: 기본값 채움을 넣으면 반드시 빨개져야 한다.

#### AC-SPATIAL-005 — 공간 데이터 전무 강등

**When** 어떤 출처도 답하지 못하면, the 시스템 **shall** 명시 신호와 함께 기존 비공간 경로로 강등한다.

- 대상 요구: REQ-SPATIAL-005 · **통과 판정**: 전무 주입 시 신호 확인 + 기존 경로 테스트 무수정 PASS.

#### AC-SPATIAL-006 — 절단·캡 신호 (무조건, **뮤테이션 필수**)

**When** 판독이 회신·왕복 예산을 초과하면, the 시스템 **shall** 축소하고 신호를 세운다.

- 대상 요구: REQ-SPATIAL-006 · **통과 판정**: **상한을 확실히 넘기는 재료**로 축소 유발 + 신호 확인. **뮤테이션**: 신호 세우는 줄 제거 시 빨개져야 한다. 재료가 상한 미만이면 이 AC는 무효(재료 선택 오류).

#### AC-SPATIAL-007 — FID 규율

The 좌표 맵 **shall not** 목록 위치를 픽스처 식별자로 대체한다.

- 대상 요구: REQ-SPATIAL-007 · **통과 판정**: 식별자 미확립 항목이 번호 없이(이름만+사유) 반환됨 — `rig_object` 규율과 동형의 단위 테스트.

#### AC-SPATIAL-008 — rig context 가산성 (무조건, 협상 불가)

The 기존 `get_rig_context` 경로·형상 **shall** 무변경이다.

- 대상 요구: REQ-SPATIAL-008 · **통과 판정**: 기존 rig context 테스트 전량 **무수정** PASS + `DEFAULT_RIG_CONTEXT_PATHS` diff 없음.

### B.2 공간 분석

#### AC-SPATIAL-009 — 1×30 vs 3×10 구조 구별 (무조건)

**When** 1행×30 좌표와 3행×10 좌표가 입력되면, the 행 검출 **shall** 각각 1행·3행 구조를 반환한다.

- 대상 요구: REQ-SPATIAL-011 · **통과 판정**: golden 픽스처 2종 단위 테스트 — 행 수·행 구성원이 기대와 정확 일치.

#### AC-SPATIAL-010 — 결정론 + 동률 None (무조건)

The 분석 **shall** 같은 입력에 같은 출력을 내고, 동률·모호를 임의 선택하지 않는다.

- 대상 요구: REQ-SPATIAL-010 · **통과 판정**: 동일 입력 반복 호출 결과 동일(순서 포함) + 동률 케이스가 명시 신호 반환.

#### AC-SPATIAL-011 — 저신뢰 신호 (무조건)

**When** 불규칙 배치로 클러스터링 신뢰도가 미달이면, the 분석 **shall** 저신뢰 신호와 함께 반환한다.

- 대상 요구: REQ-SPATIAL-012 · **통과 판정**: 불규칙 golden 픽스처에서 신호 세워짐 + 정규 배치에서 신호 부재.

#### AC-SPATIAL-012 — 정렬 4종 정확성 (무조건)

The 정렬 **shall** left_to_right / right_to_left / center_out / diagonal을 좌표 기준으로 정확히 산출한다.

- 대상 요구: REQ-SPATIAL-009 · **통과 판정**: golden 픽스처별 기대 순서 정확 일치(4종 × 최소 2배치).

#### AC-SPATIAL-013 — 분석 계층 경계 (무조건, 협상 불가)

`server/spatial/` **shall not** transport·게이트 표면을 import한다.

- 대상 요구: REQ-SPATIAL-013 · **통과 판정**: `test_architecture.py` 전역 스캔 PASS(자동 포섭 확인 — 예외 명단 diff 0) + grep 0건.

### B.3 연출 통합

#### AC-SPATIAL-014 — 선택 순서 발화 + 커맨드 내 좌표 0 (조건부: READ GO)

**When** 공간 연출이 컴파일되면, the 발화 커맨드 **shall** 정렬 순서의 선택 사슬을 담고 좌표 수치를 담지 않는다.

- 대상 요구: REQ-SPATIAL-014 · **통과 판정**: 산출 문자열 정적 검사 — 선택 순서가 정렬 결과와 1:1, 커맨드 전문에 좌표 실수값 부재.

#### AC-SPATIAL-015 — 공간 한정어 매칭 (조건부: READ GO)

**When** 지시가 공간 한정어를 담으면, the 매칭기 **shall** 폐쇄 정렬 어휘로 해석하고, 미지 한정어는 폴백 신호로 처리한다.

- 대상 요구: REQ-SPATIAL-015 · **통과 판정**: 한정어별 매핑 단위 테스트 + 미지 한정어 폴백 + 동점 None.

#### AC-SPATIAL-016 — 룰북 신설 + 접두 안정 (무조건, 협상 불가)

The 룰북 변경 **shall** `32_spatial_design.md` 1개 신설뿐이며, 접두는 byte-stable하고 기존 자산 5개는 byte-diff 0이다.

- 대상 요구: REQ-SPATIAL-016 · **통과 판정**: `test_rulebook.py` 전량 PASS(5회 조립 바이트 동일) + `git diff` 기존 자산 0건 + 정렬 순서상 32가 31 뒤.

#### AC-SPATIAL-017 — 룰북 per-show 값 부재 (무조건)

The 신설 룰북 파일 **shall not** per-show 값(그룹 번호·FID·좌표·시퀀스 번호)을 포함한다.

- 대상 요구: REQ-SPATIAL-017 · **통과 판정**: 기존 per-show 패턴 테스트가 32 포함 전체 접두에 대해 PASS.

### B.4 배치 생성 (WRITE — ASSUMPTION-54 GO 시)

#### AC-SPATIAL-018 — 프리셋 좌표 계산 (조건부)

**When** grid / row / circle 프리셋이 요청되면, the 계산 **shall** 결정론적 목표 좌표를 산출한다.

- 대상 요구: REQ-SPATIAL-019 · **통과 판정**: golden — 3×10 그리드·1행·원형 각각 기대 좌표 정확 일치(간격·원점 포함).

#### AC-SPATIAL-019 — 기록 전 백업 (조건부, **뮤테이션 필수**)

**When** 좌표 기록이 실행되면, the 시스템 **shall** 기록 전 대상 전 픽스처의 원좌표를 판독·기록하고 복원 번들을 리포트에 싣는다.

- 대상 요구: REQ-SPATIAL-020 · **통과 판정**: 백업 없는 기록 경로가 존재하지 않음(단위 — 백업 실패 주입 시 기록 차단). **뮤테이션**: 백업 선행을 제거하면 빨개져야 한다.

#### AC-SPATIAL-020 — 기록 후 재조회 검증 (조건부, **뮤테이션 필수**)

**When** 기록이 완료되면, the 시스템 **shall** 재조회로 목표값 일치를 확인하고, 불일치를 명시 실패로 보고한다.

- 대상 요구: REQ-SPATIAL-021 · **통과 판정**: 재조회 불일치 주입 시 성공 보고가 나가지 않음. **뮤테이션**: 재조회 검증 제거 시 빨개져야 한다. `ok:true`만으로 성공 보고하는 경로 부재(코드 리뷰).

#### AC-SPATIAL-021 — 기록 범위 봉쇄 (조건부)

The 기록 **shall not** 명시 대상 외 픽스처·rot* 를 건드리고, 선제 재배치를 실행하지 않는다.

- 대상 요구: REQ-SPATIAL-022 · **통과 판정**: 발화 번들 정적 검사 — 대상 외 fid 0건 + rot* 0건. 선제 재배치 트리거 경로 부재(코드 리뷰).

#### AC-SPATIAL-022 — LiveLock 제안 강등 (조건부)

**While** LiveLock 활성 중, 배치 기록 **shall** 제안 전용이고 콘솔 송신 0건이다.

- 대상 요구: REQ-SPATIAL-023 · **통과 판정**: `test_fx_boundary.py:459` 패턴 계승 — `status == "proposal"` · `is_error is False` · `succeeded is False`.

### B.5 경계 · 툴 · 판정 기록

#### AC-SPATIAL-023 — 게이트 단일 관문 (무조건, 협상 불가)

The 좌표 기록 경로 **shall** 스크리닝·감사 없이 콘솔에 도달하지 않는다.

- 대상 요구: REQ-SPATIAL-024 · **통과 판정**: `test_architecture.py` PASS + 기록 경로가 `run_commands`/게이트 관문 경유임의 코드 리뷰 + 감사 로그에 기록 1건당 항목 존재(단위).

#### AC-SPATIAL-024 — 툴 등재 일관성 (무조건)

The 툴 등재 **shall** 이름·개수·개수 고정 테스트 기대값이 일관되다 — 호출 사건과 무관한 정적 구성 속성(REQ-SPATIAL-025와 동형의 Ubiquitous)이다.

- 대상 요구: REQ-SPATIAL-025 · **통과 판정**: `ToolDefinition(` 계수 = 확정 개수(기본 20) = 개수 고정 테스트 기대값. 불일치 0.

#### AC-SPATIAL-025 — 판정 기록 어휘 (무조건)

The 라이브 판정 **shall** `progress.md §E.2`에 폐쇄 어휘 + 행두 접두 행으로 기록된다.

- 대상 요구: REQ-SPATIAL-026 · **통과 판정**: `grep -E "^(GO|DESCOPE|SKIP|REOPEN):" progress.md` ≥ 판정 수 — M0 판정 8건(ASSUMPTION-53~60) 전건에 대응 행 존재, 한 판정당 정확 1행. **미프로브 전제 처리**: ASSUMPTION-56(D-3이 Layout 기록을 v1에 포함하지 않는 한 프로브 없음)·ASSUMPTION-59(M6 여유 시 후보)는 M0 시점에 `SKIP:`(`CONDITION_NOT_MET`) 행을 받는다 — 8행 요건은 이 행들을 포함해 충족 가능하다.

### LIVE 축

#### AC-SPATIAL-026 — (LIVE) M0 READ 프로브 + 날조 대조군

**When** M0 READ 프로브가 실행되면, the 판정 **shall** 실좌표 판독 성공과 날조 프로퍼티(`poszz`)의 거동을 분리 기록한다.

- 대상 요구: ASSUMPTION-53 / REQ-SPATIAL-026 (c) · **통과 판정**: 프로브 로그에 (a) 채택 변형(대소문자) 명시 (b) 날조 대조군 결과 명시 (c) `ok` 비변별 판명 시 값 대조 대체 기록. 대조군 없는 `ok` 채택이 1건이라도 있으면 FAIL.

#### AC-SPATIAL-027 — (LIVE) M0 WRITE 프로브 + 원상복구 왕복 (조건부: WRITE 축 진행 시)

**When** M0 WRITE 프로브가 실행되면, the 프로브 **shall** 기록→재조회 일치→원상복구→재조회 원값 일치의 전 왕복을 로그로 남긴다.

- 대상 요구: ASSUMPTION-54 / REQ-SPATIAL-026 (d) · **통과 판정**: 로그에 4단 왕복 전건 + 원상복구 후 값이 기록 전 값과 일치. 복구 미완의 프로브 종료는 FAIL이며 즉시 블로커.

#### AC-SPATIAL-028 — (LIVE) 선택 순서 → 방향 (사람 관측)

**When** 서로 다른 두 순서의 선택 + 딤머 페이저가 발화되면, the 웨이브 방향 차이 **shall** 사람 GUI 관측으로 판정되고 결론 문장으로 기록된다.

- 대상 요구: ASSUMPTION-58 · REQ-SPATIAL-014(선택 순서 실현 축) · REQ-SPATIAL-026(판정 기록 규율) · **통과 판정**: progress.md §E.2에 관측 기록 + "방향이 순서를 따랐다/따르지 않았다" 명시 결론. **기계 증거 주장 금지**(§C.1 천장). 모호한 "아마도"는 FAIL.

#### AC-SPATIAL-029 — (LIVE) E2E: 같은 지시, 두 리그 (조건부: READ GO)

**When** 같은 공간 연출 지시가 1행 리그와 3행 리그에 실행되면, the 발화 **shall** 구조적으로 다르고(기계 — 행 수·선택 순서), 무대 적합성 관측과 결론 문장이 기록된다(사람).

- 대상 요구: 시나리오 1 / REQ-SPATIAL-011/014 · **통과 판정**: 두 리그의 커맨드 diff가 행 구조 차이를 반영(정적) + 사람 관측 결론 문장 존재.

#### AC-SPATIAL-030 — 전체 회귀 (무조건, 협상 불가, **횡단 품질 게이트 AC**)

The 전체 테스트 스위트 **shall** run-phase 킥오프 기준선 대비 신규 실패 0건이다.

- 대상 요구: 전 SPEC 공통 — 특정 REQ 1건에 속하지 않는 **횡단 품질 게이트 AC**이며, 판정 기록 규율은 REQ-SPATIAL-026에 정박한다 · **통과 판정**: pytest + vitest 전량. 기준선은 **킥오프 시점 재측정** — plan-phase 수치 재사용 금지.

### 감사 fold-in 추가 AC (v0.2.0)

#### AC-SPATIAL-031 — 기록 번들 risky 분류 + 규칙 ③ 발동 — **해소 (SPEC-COPILOT-WRITEGATE-001이 `server/safety/`와 함께 소유·폐쇄)**

**When** 배치 기록 번들이 게이트 스크리닝에 들어가면, the 게이트 **shall** 번들을 risky로 분류하고 showfile 백업 규칙 ③(`before_risky_execution()`)을 발동한다.

- 대상 요구: REQ-SPATIAL-020(발동 조건 절) / REQ-SPATIAL-024 · **통과 판정**: 단위 — arrange 번들에 대한 게이트 스크리닝 판정 `risky=True` + `before_risky_execution()` 호출 확인(모의 백업 훅). **뮤테이션(복원 — §E의 필수 5건에 재편입)**: `server/safety/blacklist.yaml:50`의 `"Set Fixture"` 항목을 지우면 `Set Fixture <fid> Pos[xyz] '<v>'`가 다시 `safe`로 떨어져 **승인 흐름 단언이 반드시 빨개져야 한다.** v0.3.0에서 이 AC는 *"없는 코드는 변이시킬 수 없다"* 를 근거로 뮤테이션에서 빠져 있었다 — **변이 대상 리터럴이 실재하므로 그 면제는 소멸했다**(§E 뮤테이션 필수 5건 목록이 031을 계속 열거해 온 것과의 문면 모순도 이로써 해소된다).
- **해소 (SPEC-COPILOT-WRITEGATE-001 · 2026-08-05)**: `server/safety/blacklist.yaml`을 **version 1 → 2**로 개정하고 폐쇄 집합에 **항목 단 1건 — `"Set Fixture"`** 를 추가했다(`blacklist.yaml:24` 버전 · `:50` 항목). **코드 변경 0** — `classify.py` · `ruleset.py` · `gate.py` · `expand.py` 전부 무수정이며, 테스트가 이 파일 내용을 직접 순회하므로 개정이 FN 코퍼스를 자동 확장한다. 결과: 좌표 기록이 `risky=True` · `category="blacklisted"` · `matched_entry="Set Fixture"`로 분류되어 **승인 카드가 뜨고** 규칙 ③ `before_risky_execution()`이 발동한다(`server/safety/gate.py:362-365`). **v0.3.0이 든 유예 사유 3건은 각각 무너졌다** — (a) `server/safety/**` PRESERVE 경계는 **WRITEGATE-001이 `server/safety/`를 소유**하면서 해소된다(경계가 사라진 게 아니라 소유자가 생겼다). (b) *"기존 테스트 10건이 깨진다"* 는 **미측정 추정이었고 실측은 5건**이다 — 수정 전 전체 스위트가 `4 failed, 4716 passed, 7 skipped`이고, 여기에 커밋 이후에만 관측되는 1건(`test_overlap_preserve.py::TestSafetyChokepointFileSet::test_exactly_the_expected_files_changed` — 워킹트리가 아니라 `_PRECHK_BASE..HEAD` **커밋 범위**를 읽기 때문)을 더한 값이다. (c) `server/measurement/corpus.yaml`의 *"non-risky verbs only"* 불변식은 **편집 0으로 보존된다** — 코퍼스에 `Set` 토큰이 **0건**이라 `Set Fixture` 항목과 충돌할 지면 자체가 없다. 충돌하는 것은 `Store Group` risky화(21개 시나리오 중 **13개** 적중)이며, 이는 **2026-08-05 사용자 결정으로 명시 descope**되어 후속 SPEC 몫으로 남는다.
- **실측 폐쇄 범위 (19/19 커맨드 형태 · 불일치 0)**: 부호 탈락형 `Set Fixture 11 Posx -3.5` · 무성 no-op형 `Set Fixture 11 Posx - 3.5` · 3자 약어형 `Set Fixture 11 Pos -3.5` · RANGE형 `Set Fixture 1 Thru 18 Posz '5.0'` · 방향축형 `Set Fixture 11 Rotx '90.0'` · 매크로 프로퍼티 밀반입형 `Set Macro 1.1 Property 'Command' "Set Fixture 11 Posx '5.0'"` 이 **전부 보류(held)** 된다. 반대편도 실측으로 고정했다 — `Set Selection MAtricks 'PhaseFromX' 0` · `Set Macro … Property 'Command' '<safe>'` · `Store`/`Assign`/`Copy`/`Label` 전 형태는 **기존 `safe` 분류를 그대로 유지**한다. 즉 폐쇄는 `Set Fixture`에 **정확히 범위 한정**됐고 과차단이 없다.
- **선례 가치 — 이 리터럴의 사상 첫 개정**: SPEC-COPILOT-OVERLAP-001 `research.md:365-367`이 *"확장 선례 0건 … 절차를 문서화하는 것 자체가 산출물이어야 한다"* 로 남긴 공백을, 이 개정이 **첫 실행 사례로 채운다.** 무게는 SPEC-COPILOT-EXECREF-001의 `RECOGNIZED_REFERENCE_TYPES` 개정(`server/safety/classify.py:32-44`)과 **동일하게** 취급한다 — 폐쇄 집합 리터럴의 개정은 버전 범프 + 사유의 코드 내 명기 + 승인된 삭제 허용이 함께 가야 한다.
- **되돌림의 대가가 라이브에서 실현됐다 — 폐쇄의 정당화 근거(보존)**: §E.2.20 결함 2에서 **사용자가 요청하지 않은 좌표 기록 54건이 승인 카드 없이 콘솔에 나갔다.** 모델이 이전 턴의 미완 목표를 이어 완성한 것이고 의도는 합리적이었으나 **그 사이에 사람이 없었다.** `Set Fixture … Pos*`가 `safe`이므로 게이트가 통과시키고 규칙 ③ 백업도 발동하지 않았다. 같은 턴의 `Go+ Page 1.202`(reference-invoking)는 **정상적으로 카드를 띄웠다** — 즉 **게이트는 건강하고 좌표 기록만 그 그물을 통과한다.** 이것은 §E.2.14가 *"되돌림의 대가"* 로 적어둔 위험의 **가설이 아닌 관측 사례**였고, **후속 SPEC은 실제로 이 관측을 우선순위 근거로 인용했으며 착지했다 — 그 SPEC이 SPEC-COPILOT-WRITEGATE-001이다.** 이 문단은 폐쇄 후에도 삭제하지 않는다: 54건은 *"승인 계층이 없으면 무슨 일이 나는가"* 에 대한 이 저장소의 **유일한 실측 사례**이고, 재유예 논의가 나올 때 되돌아올 자리다.
- **남은 방어선은 설계대로 작동했다**: 원좌표 백업 · 재조회 검증 · 복원 번들 · 범위 봉쇄. §E.2.20의 복구도 이 경로로 했고 쇼파일 잔여 **0**이다. 유예 당시의 결손은 *"방어가 없다"* 가 아니라 *"승인 게이트 계층의 방어만 없다"* 였고, **그 한 계층이 이제 닫혔다** — 본 SPEC 자체 방어선 4종 위에 승인 카드와 규칙 ③ 쇼파일 스냅샷이 얹힌다.
- **종속 항목도 함께 열렸다**: REQ-SPATIAL-024의 **승인 흐름** 절과 REQ-SPATIAL-020의 **규칙 ③ 연동** 절이 이 AC에 종속돼 있었고 **둘 다 해소**됐다(spec.md REQ-020 · REQ-024 · §C.1 승인 카드 행 갱신). `plan.md §B M4`의 risky 분류 확장 행도 같은 표기로 맞췄다 — **정본은 spec.md REQ-020 · 024이며 이 AC가 그 판정을 운반한다.**

#### AC-SPATIAL-032 — look/fx/scene PRESERVE (무조건, 협상 불가)

The 본 SPEC의 변경 집합 **shall not** `server/looks/**`·`server/fx/**`·`server/scene/**`을 수정하며, 통합은 읽기 import 방향으로만 성립한다.

- 대상 요구: REQ-SPATIAL-018 · **통과 판정**: `git diff --stat <base> -- server/looks server/fx server/scene` 0건 + import 방향 검사 — spatial→looks/fx/scene 읽기 import만 존재하고 역방향(looks/fx/scene→spatial) import 0건(`test_architecture.py` 계열).

## §D. Edge Cases

- **동일 좌표 픽스처 2대**(같은 트러스 지점): 정렬 동률 — 임의 선택 금지, fid 오름차순 등 **문서화된 2차 키**로 결정론 확보(2차 키 자체는 design.md §3이 소유, "동률을 조용히 임의 처리"만이 금지 대상).
- **좌표 (0,0,0) 전대**(패치만 하고 배치 안 한 쇼): 전 픽스처 동일 좌표 = 행 검출 무의미 → 저신뢰 신호 + 강등(AC-SPATIAL-011/005). (0,0,0)을 "데이터 없음"으로 오독하지 않는다 — 판독 성공한 실좌표다.
- **음수 좌표**: 무대 좌표계는 원점 좌우로 음수가 정상이다. 정렬·클러스터링이 부호를 그대로 다루는지 golden에 음수 케이스 포함.
- **판독 도중 일부 실패**(30대 중 3대 실패): 부분 맵 + 부재 사유 3건(AC-SPATIAL-004). 27대만으로 연출을 계속할지는 저신뢰 신호와 함께 호출자 판단.
- **기록 도중 실패**(stop-on-first-failure): 이미 기록된 픽스처 존재 — 복원 번들이 **전 대상**을 담고 있으므로 부분 실패 후에도 복원 가능해야 한다(백업이 기록 전 일괄 선행인 이유).
- **LiveLock 중 WRITE 요청**: 제안 강등 — 백업 판독도 송신이므로 함께 강등되는지 형상 확인(제안 카드에 백업·기록·검증 전 단계가 제안으로 표시).
- **회신 절단으로 일부 픽스처 누락**: 절단 신호 + 누락분을 "판독 실패"가 아니라 "미판독"으로 구분(신호 어휘 분리 — 값 축약과 항목 탈락은 다른 사건).

## §E. Quality Gate 기준

- pytest/vitest 전체: run-phase 킥오프 기준선 대비 신규 실패 0건.
- `ruff check`: 터치 파일 전용 clean(기존 baseline 위반은 별도 표기).
- `server/spatial/` transport·게이트 import grep 0건 + `test_architecture.py` 자동 포섭.
- 룰북: 기존 자산 5개 byte-diff 0 + 접두 byte-stable 5회 + per-show 값 부재.
- rig context 기존 테스트 무수정 PASS.
- 툴 개수 고정 테스트 = 확정 개수, 불일치 0.
- 뮤테이션 필수 5건(AC-SPATIAL-004/006/019/020/031): 각 가드 제거 시 반드시 빨개짐 — 통과하면 재료 선택 오류로 재작성.
- 라이브 프로브 로그: READ 프로브는 판독 전용임이 로그로 확인 가능, WRITE 프로브는 원상복구 왕복 완결이 로그로 확인 가능.

## §F. Definition of Done

1. **M0 판정 8건(ASSUMPTION-53~60)이 전건 폐쇄 어휘로 `progress.md §E.2`에 기록**되어 있다 — 부정 판정도 DoD를 충족한다(AC-SPATIAL-025/026).
2. **READ GO인 경우**: M1~M6 완료, AC 전량 PASS 또는 사유가 기록된 `[DEFERRED]`/N/A.
3. **READ NEGATIVE인 경우**: SPEC 중단이 블로커 보고와 함께 기록되고, 코드 변경 0으로 닫힌다 — 이 경우도 "콘솔이 좌표를 노출하지 않는다"는 확정 사실이 산출물이다.
4. **WRITE NEGATIVE인 경우**: WRITE 축 AC(018~022/027/031)가 `[DEFERRED]`로 정직하게 기록되고(manager-spec 재위임 경유), READ 축 AC는 전량 PASS.
5. **협상 불가 AC는 어느 분기에서든 문자 그대로 전량 PASS**: 008(rig context 가산성), 013(분석 경계), 016(룰북 접두 안정), 023(게이트 관문), 030(전체 회귀), 032(look/fx/scene PRESERVE).
6. **AC-SPATIAL-029의 결론 문장이 존재한다**(READ GO 분기) — 같은 지시가 두 리그에서 다른, 배치에 맞는 결과를 냈는가에 대한 명시 답. 이것이 본 SPEC의 실질 산출물이다.
7. WRITE가 출하된 경우, 라이브 왕복(기록→검증→복원)이 M6에서 재확인되었다(AC-SPATIAL-027).
8. 룰북 `32_spatial_design.md`의 커맨드 문법이 전건 라이브 확인분이다 — 미확인 문법이 실린 채로 닫지 않는다(REQ-SPATIAL-016).
