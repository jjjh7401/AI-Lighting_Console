# SPEC-COPILOT-AUTOPATCH-001 — 인수 기준 (acceptance)

status: draft (v0.1.0, 2026-08-05) · Tier L · AC 26건 계획. 본 문서는 `spec.md`의 요구를 관측 가능한 검증 기준으로 전개한다.

> **인용 규율**: 본 SPEC의 `spec.md`·`acceptance.md`는 행 번호로 인용하지 않는다 — 안정 토큰
> (`REQ-AUTOPATCH-…`, `AC-AUTOPATCH-…`, `ASSUMPTION-nn`, `§C`)만 쓴다. `file:line`은 코드·룰북·
> responder 프로토콜·**다른** SPEC의 아티팩트에만 쓴다.

---

## §A. 개요

| 검증 축 | 어떻게 |
|---|---|
| 승인 통제 | 드라이런 기본 · 항목 단위 선택 · 승인 없는 쓰기 0(AST + 호출 기록) |
| FID 안전 | 범위 강제 · 슬롯 유래 값 금지 · 충돌 사전검사 on/off 분기 |
| 타입 해석 | 라이브러리 열거 기반 · 부재 시 하드 스톱 · 표시문자열 파싱 0 |
| 콘솔 문법 | `AddFixtures` 형태 · **CD 0건** · 단일 명령 실행 · 점유폭 간격 |
| 비가역 대비 | 멱등 · 검증 읽기 · 자동 보정 0 · 비가역 경고 |
| 경계 | `deploy_plugin` 경유 · `execution_port` 직접 호출 0 · PRESERVE 0-diff |
| 회귀 | 1단계 공개 계약 무변경 · 전체 스위트 무회귀 |

**비공허성 원칙**: "0건"을 주장하는 모든 항목은 **금지 대상을 일부러 심어** 스캐너가 실제로 잡는지
확인하는 대조군을 동반한다. 대조군 없는 0건 주장은 인수 불가다.

---

## §B. Given-When-Then 시나리오

**시나리오 1 — 정상 패치**: **Given** 1단계 대조가 수행되어 `missing_in_console` 3건이 나왔고 사용자가
빈 FID 범위를 주었을 때, **When** 3건을 승인하고 실행하면, **Then** 3대가 도면 주소에 도면 타입으로
생성되고 검증 읽기가 3건 모두를 확인한다.

**시나리오 2 — 드라이런**: **Given** 같은 상황에서, **When** 드라이런을 호출하면, **Then** Lua 소스와
대상 표가 나오고 **콘솔 쓰기는 0건**이다.

**시나리오 3 — FID 범위 미제공**: **Given** 사용자가 FID 범위를 주지 않았을 때, **When** 실행을
시도하면, **Then** 패치를 거부하고 무엇을 입력해야 하는지 안내한다.

**시나리오 4 — 라이브러리 부재**: **Given** 도면 타입이 콘솔 라이브러리에 없을 때, **When** 그 항목을
승인하면, **Then** 그 항목만 하드 스톱되고 GDTF 임포트 선행 필요를 사유로 보고한다.

**시나리오 5 — 주소 점유**: **Given** 도면 주소가 이미 콘솔에서 점유되어 있을 때, **When** 실행하면,
**Then** 그 항목을 제외하고 사유를 보고하며 **임의의 빈 주소로 옮기지 않는다**.

**시나리오 6 — 재실행**: **Given** 이미 패치한 승인 집합을, **When** 다시 실행하면, **Then** 중복을
만들지 않고 건너뛴 사실을 보고한다.

**시나리오 7 — 검증 불일치**: **Given** 플러그인이 오류 없이 끝났으나 검증 읽기에서 0건이 관측될 때,
**When** 결과를 보고하면, **Then** 성공으로 간주하지 않고 Patch 편집기 안내를 함께 낸다.

**시나리오 8 — 미대조 리포트**: **Given** 1단계가 다중 시스템 미매핑으로 대조를 수행하지 않았을 때,
**When** 패치를 시도하면, **Then** 거부한다.

---

## §C. 인수 기준

### §C.0 역추적표

| REQ | 커버 AC | M | 비고 |
|---|---|---|---|
| REQ-AUTOPATCH-001 | AC-AUTOPATCH-002 | M1 | 입력은 1단계 산출물 한정 |
| REQ-AUTOPATCH-002 | AC-AUTOPATCH-003 | M1 | 항목 단위 · 기본 비선택 |
| REQ-AUTOPATCH-003 | AC-AUTOPATCH-004 | M1 | 드라이런 기본 |
| REQ-AUTOPATCH-004 | AC-AUTOPATCH-019 | M5 | 승인 없는 쓰기 0 |
| REQ-AUTOPATCH-005 | AC-AUTOPATCH-004 | M1 | 비가역 경고 (같은 AC의 별 구간) |
| REQ-AUTOPATCH-006 | AC-AUTOPATCH-005 | M2 | 범위 내 배정 |
| REQ-AUTOPATCH-007 | AC-AUTOPATCH-006 | M2 | 범위 미제공 거부 |
| REQ-AUTOPATCH-008 | AC-AUTOPATCH-007 | M2 | 슬롯 유래 값 3금지 |
| REQ-AUTOPATCH-009 | AC-AUTOPATCH-008 | M2 | 충돌 사전검사 on/off |
| REQ-AUTOPATCH-010 | AC-AUTOPATCH-008 | M2 | 배정 전수 나열 (같은 AC의 별 구간) |
| REQ-AUTOPATCH-011 | AC-AUTOPATCH-009 | M3 | 라이브러리 열거 |
| REQ-AUTOPATCH-012 | AC-AUTOPATCH-010 | M3 | 퍼지 매칭 + 사용자 확인 |
| REQ-AUTOPATCH-013 | AC-AUTOPATCH-011 | M3 | 라이브러리 부재 하드 스톱 |
| REQ-AUTOPATCH-014 | AC-AUTOPATCH-012 | M3 | 점유폭 일치 |
| REQ-AUTOPATCH-015 | AC-AUTOPATCH-012 | M3 | 표시문자열 파싱 금지 (같은 AC의 별 구간) |
| REQ-AUTOPATCH-016 | AC-AUTOPATCH-013 | M4 | `AddFixtures` 형태 |
| REQ-AUTOPATCH-017 | AC-AUTOPATCH-014 | M4 | **CD 0건** |
| REQ-AUTOPATCH-018 | AC-AUTOPATCH-015 | M4 | 단일 명령 실행 |
| REQ-AUTOPATCH-019 | AC-AUTOPATCH-016 | M4 | 점유폭 간격 · 점유 주소 제외 |
| REQ-AUTOPATCH-020 | AC-AUTOPATCH-017 | M5 | `deploy_plugin` 경유 |
| REQ-AUTOPATCH-021 | AC-AUTOPATCH-018 | M5 | `execution_port` 직접 호출 0 |
| REQ-AUTOPATCH-022 | AC-AUTOPATCH-020 | M6 | 멱등 |
| REQ-AUTOPATCH-023 | AC-AUTOPATCH-021 | M6 | 검증 읽기 |
| REQ-AUTOPATCH-024 | AC-AUTOPATCH-022 | M6 | 불일치 보고 · 자동 보정 0 |
| REQ-AUTOPATCH-025 | AC-AUTOPATCH-002 | M1 | 미대조 리포트 거부 (같은 AC의 별 구간) |
| REQ-AUTOPATCH-026 | AC-AUTOPATCH-027 | M2 | `ASSUMPTION-71` 부정 시 구조화된 FID 범위 확인 |

**REQ 26/26 커버, 누락 0.** 역추적표에 행이 없는 AC는 **5건**이며 의도다 —
**AC-AUTOPATCH-001**(M0 전제 판정 게이트) · **AC-AUTOPATCH-023**(툴 등록, 형상) ·
**AC-AUTOPATCH-024**(PRESERVE, 형상 전체가 대상) · **AC-AUTOPATCH-025**(1단계 계약 회귀) ·
**AC-AUTOPATCH-026**(라이브 종단 통합).

### §C.0a 마일스톤별 AC 배정 (정본)

| 마일스톤 | AC | 수 |
|---|---|---|
| M0 — 라이브 전제 측정 | AC-AUTOPATCH-001 | 1 |
| M1 — 후보 입력 모델 | AC-AUTOPATCH-002 · 003 · 004 | 3 |
| M2 — FID 배정 | AC-AUTOPATCH-005 · 006 · 007 · 008 · 027 | 5 |
| M3 — 타입·모드 해석 | AC-AUTOPATCH-009 · 010 · 011 · 012 | 4 |
| M4 — Lua 생성 · 주소 계획 | AC-AUTOPATCH-013 · 014 · 015 · 016 | 4 |
| M5 — 배포 · 실행 | AC-AUTOPATCH-017 · 018 · 019 | 3 |
| M6 — 멱등 · 검증 | AC-AUTOPATCH-020 · 021 · 022 | 3 |
| M7 — 배선 · 회귀 · PRESERVE | AC-AUTOPATCH-023 · 024 · 025 | 3 |
| M8 — 라이브 종단 | AC-AUTOPATCH-026 | 1 |

**합 27 · 중복 0 · 누락 0.** 이 표가 정본이며 `plan.md`의 마일스톤별 `AC` 줄과 1:1이다.

---

### AC-AUTOPATCH-001 — 5개 전제 판정 게이트 (M0)

**When** 라이브 세션이 종료되면, the M0 **shall** `ASSUMPTION-71`~`-75`에 GO / NEGATIVE /
INCONCLUSIVE 중 하나를 배정한다.

- 대상 요구사항: (전제 게이트 — 특정 REQ가 아니라 M2·M3·M6의 설계를 확정한다)
- 검증 방법: 실기 onPC 2.4.2 라이브 세션. `progress.md` §E.2 M0 절에 접두 행으로 기록.
- 기대 결과:
  - ① 5건 **전부** 판정이 배정된다. 미판정 0건. INCONCLUSIVE는 **부정과 동일하게** 후속 설계에 반영한다.
  - ② `ASSUMPTION-71` 판정은 **슬롯과 FID가 다른 픽스처**에서 측정했음을 근거로 함께 기록한다.
       그런 픽스처를 찾지 못했으면 INCONCLUSIVE다 — 슬롯==FID 쇼파일의 측정은 판정 근거가 되지 못한다.
  - ③ 파괴적 측정(73·74)은 **테스트 쇼파일**에서 수행했고 사용자가 그 사실을 확인했음이 기록된다.
  - ④ 각 판정이 어느 요구를 켜거나 끄는지 명시된다(§A.3 표와 1:1).

### AC-AUTOPATCH-002 — 입력은 1단계 산출물 한정 · 미대조 리포트 거부 (M1)

**When** 패치 후보를 만들면, the 시스템 **shall** 1단계 리포트만을 출처로 쓰고, 대조되지 않은
리포트를 거부한다.

- 대상 요구사항: REQ-AUTOPATCH-001 · REQ-AUTOPATCH-025
- 검증 방법: `server/tests/test_autopatch_candidates.py` — 인메모리 리포트 payload. 콘솔 무접촉.
- 기대 결과:
  - ① 후보 목록의 모든 항목이 입력 리포트의 `missing_in_console`에서 유래한다. 파일 판독 호출 **0건**,
       콘솔 실측 호출 **0건**. **비공허성**: 파일 판독기와 실측 포트에 호출 기록기를 달고,
       그 기록기가 다른 테스트(1단계 경로)에서는 실제로 호출을 잡는지 함께 확인한다.
  - ② `diffs.performed == false`인 리포트는 거부되고, 사유가 리포트의 `reason`을 인용한다.
  - ③ `multi_system_mapping_absent`가 `skipped_checks`에 있으면 거부된다.
  - ④ 거부는 예외가 아니라 **구조화된 페이로드**로 나온다.

### AC-AUTOPATCH-003 — 항목 단위 선택 · 기본 비선택 (M1)

**Ubiquitous** The 후보 목록 **shall** 항목 단위 식별자를 갖고 기본 선택 상태가 비선택이다.

- 대상 요구사항: REQ-AUTOPATCH-002
- 검증 방법: `server/tests/test_autopatch_candidates.py`
- 기대 결과:
  - ① 각 후보가 안정적인 식별자를 갖는다(같은 입력 → 같은 식별자).
  - ② 선택 인자를 주지 않으면 패치 대상이 **0건**이다. **비공허성**: 선택 인자를 주면 정확히 그만큼
       대상이 되는 대조군을 함께 둔다.
  - ③ 존재하지 않는 식별자를 선택하면 조용히 무시하지 않고 오류로 보고한다.

### AC-AUTOPATCH-004 — 드라이런 기본 · 소스 전문 · 비가역 경고 (M1)

**When** 드라이런을 호출하면, the 시스템 **shall** 생성될 Lua 소스와 대상 표를 내고 비가역성을 명시한다.

- 대상 요구사항: REQ-AUTOPATCH-003 · REQ-AUTOPATCH-005
- 검증 방법: `server/tests/test_autopatch_candidates.py` · `test_autopatch_execute.py`
- 기대 결과:
  - ① `dry_run` 인자를 **생략**하면 드라이런이다. 실행은 명시적 값을 요구한다.
  - ② 산출물에 Lua 소스 **전문**과 대상 표가 들어가고, 표의 열이 최소한
       **타입 · 모드 · FID · 유니버스 · 주소 · 점유폭 · `address_basis`**를 포함한다.
  - ③ 선택 항목 중 하나라도 `address_basis`가 `absolute_back_calculated`이면 산출물에
       **역산 전제 문구**("Universes pane이 기본 연속 512블록이라는 전제 위에서 역산했다 …")가
       포함된다. **비공허성**: 전 항목이 `universe_address_direct`인 입력에서는 그 문구가
       **나오지 않음**을 함께 assert한다.
  - ④ 산출물에 "실행 취소·백업 복원 경로가 없다"는 취지의 경고 문구가 포함된다.
       **비공허성**: 그 문구의 부재를 검사하는 테스트가 실제로 실패하는지 확인한다.

### AC-AUTOPATCH-005 — 사용자 범위 내 FID 배정 (M2)

**Ubiquitous** The FID 배정기 **shall** 주어진 범위 안에서만 배정한다.

- 대상 요구사항: REQ-AUTOPATCH-006
- 검증 방법: `server/tests/test_autopatch_fid.py`
- 기대 결과:
  - ① 배정된 모든 FID가 범위 안이다. 범위보다 후보가 많으면 초과분을 배정하지 않고 사유를 보고한다.
  - ② 같은 입력 · 같은 범위면 배정이 **결정적**이다.

### AC-AUTOPATCH-006 — 범위 미제공 시 거부 (M2)

**When** 빈 FID 범위가 주어지지 않았으면, the 시스템 **shall** 패치를 거부한다.

- 대상 요구사항: REQ-AUTOPATCH-007
- 검증 방법: `server/tests/test_autopatch_fid.py`
- 기대 결과:
  - ① 범위 인자 부재 시 실행이 거부되고, 사유에 무엇을 입력해야 하는지 담긴다.
  - ② 추정 배정(최대 슬롯+1, 고정 시작 번호 등)이 **0건**이다. **비공허성**: 추정 로직을 심으면
       테스트가 잡는지 확인한다.

### AC-AUTOPATCH-007 — 슬롯 유래 값 3금지 (M2)

**Unwanted** The FID 배정기 **shall not** 슬롯 번호를 FID로 쓰지 않는다.

- 대상 요구사항: REQ-AUTOPATCH-008
- 검증 방법: `server/tests/test_autopatch_fid.py` — AST 스캔 + 동작 검사
- 기대 결과:
  - ① 배정 경로가 `FixtureRecord.slot`을 읽지 않는다(AST 스캔). **비공허성**: 슬롯 참조를 심으면 잡힌다.
  - ② `fid_note`가 `미확정`인 값이 배정 근거로 흘러들지 않는다.
  - ③ 생성된 Lua에 `Fixture <n>` 형태의 선택 명령이 **0건**이다.

### AC-AUTOPATCH-008 — 충돌 사전검사 분기 · 배정 전수 나열 (M2)

**Where** `ASSUMPTION-71`이 GO면, the 시스템 **shall** 충돌 사전검사를 수행하고, 부정이면 축소를 명시한다.

- 대상 요구사항: REQ-AUTOPATCH-009 · REQ-AUTOPATCH-010
- 검증 방법: `server/tests/test_autopatch_fid.py` — 두 분기 각각
- 기대 결과:
  - ① GO 분기: 기존 FID와 충돌하는 후보가 대상에서 제외되고 사유가 보고된다.
  - ② 부정 분기: 사전검사가 수행되지 않고, `skipped_checks`에 축소가 실린다. **정상 페이로드의
       구조화된 부류**여야 하며 예외 산문이 아니다.
  - ③ 어느 분기든 드라이런 표에 **어느 장비가 어느 FID를 받는지 전수** 나열된다.
  - ④ 어느 안전망이 작동 중인지가 산출물에서 읽힌다.

### AC-AUTOPATCH-009 — 콘솔 라이브러리 열거 (M3)

**Ubiquitous** The 타입 해석기 **shall** `Patch/FixtureTypes` 열거로 후보를 얻는다.

- 대상 요구사항: REQ-AUTOPATCH-011
- 검증 방법: `server/tests/test_autopatch_types.py` — `RigPort` 더블
- 기대 결과:
  - ① 조회 경로가 `Patch/FixtureTypes`다. 소스에 라이브러리 이름 상수가 **0건**.
       **비공허성**: 상수를 심으면 스캐너가 잡는다.
  - ② 열거가 절단되면 절단 사실이 보고되고 "후보에 없음"으로 단정하지 않는다.

### AC-AUTOPATCH-010 — 퍼지 매칭 + 사용자 확인 + 별칭 (M3)

**When** VW 타입명을 콘솔 이름과 맞추면, the 시스템 **shall** 퍼지 매칭 후 사용자 확인을 거친다.

- 대상 요구사항: REQ-AUTOPATCH-012
- 검증 방법: `server/tests/test_autopatch_types.py`
- 기대 결과:
  - ① 문자열 동등 비교만으로 확정하는 경로가 **0건**. **비공허성**: 동등 확정을 심으면 잡힌다.
  - ② 실물 관측값(`Robe MegaPointe` / `Robe Lighting@MegaPointe`)이 후보를 만들어낸다.
  - ③ 확인 없이 자동 확정되지 않는다. 저장된 별칭이 있으면 재사용하되 그 사실이 산출물에 보인다.

### AC-AUTOPATCH-011 — 라이브러리 부재 하드 스톱 (M3)

**When** 대응 FixtureType 또는 DMXMode가 없으면, the 시스템 **shall** 그 항목을 패치하지 않는다.

- 대상 요구사항: REQ-AUTOPATCH-013
- 검증 방법: `server/tests/test_autopatch_types.py`
- 기대 결과:
  - ① 해당 항목만 제외되고 나머지는 진행된다(전체 실패가 아니다).
  - ② 사유에 GDTF 임포트 선행 필요가 담긴다.
  - ③ 유사 이름으로 **대체 배정하지 않는다**. **비공허성**: 대체 배정을 심으면 잡힌다.

### AC-AUTOPATCH-012 — 점유폭 일치 · 표시문자열 파싱 금지 (M3)

**When** 모드를 고르면, the 시스템 **shall** 점유폭을 1단계 `DMX Footprint`와 대조한다.

- 대상 요구사항: REQ-AUTOPATCH-014 · REQ-AUTOPATCH-015
- 검증 방법: `server/tests/test_autopatch_types.py`
- 기대 결과:
  - ① `ASSUMPTION-72` GO 분기에서 불일치가 승인 **전에** 제시된다.
  - ② 부정 분기에서는 확인이 descope되고 축소가 명시된다.
  - ③ 표시 문자열에서 숫자를 파싱해 채널 수를 얻는 경로가 **0건**. **비공허성**: 파싱을 심으면 잡힌다.
  - ④ 멀티셀 케이스(1단계가 8행→1대로 접은 장비)에서 8셀 모드가 선택되는지 확인한다.

### AC-AUTOPATCH-013 — `AddFixtures` 호출 형태 (M4)

**Ubiquitous** The Lua 생성기 **shall** 룰북이 정한 필드 집합만 생성한다.

- 대상 요구사항: REQ-AUTOPATCH-016
- 검증 방법: `server/tests/test_autopatch_lua.py` — 생성 문자열 파싱
- 기대 결과:
  - ① `mode`가 `Patch().FixtureTypes[...].DMXModes[...]` 형태이고 공백 이름은 대괄호 표기다.
  - ② `amount` · `idtype = "Fixture"` · `fid`(문자열) · `name`이 모두 있다.
  - ③ 룰북 필드 집합 밖의 키가 **0건**.

### AC-AUTOPATCH-014 — `ChangeDestination` 0건 (M4)

**Unwanted** The 생성기 **shall not** `ChangeDestination`/`CD`를 산출물에 포함한다.

- 대상 요구사항: REQ-AUTOPATCH-017
- 검증 방법: `server/tests/test_autopatch_lua.py` — **두 기법을 분리해서** 쓴다.
  ①② 는 산출물 문자열 스캔, ③ 은 `server/vwx/luagen.py` **소스 AST 스캔**
  (`server/tests/test_prechk_tool.py:330-343` 의 AST 패턴 계승, AC-AUTOPATCH-007① 과 동일 기법).
- 기대 결과:
  - ① 생성된 Lua 소스와 `run_commands` 배열 전수에서 `ChangeDestination`·`CD` 토큰 **0건**.
  - ② **비공허성**: 스캐너 테스트에 `ChangeDestination`을 심은 가짜 산출물을 넣어 **실제로 잡히는지**
       확인한다. 이 대조군 없이는 인수하지 않는다.
  - ③ **구조 보장 — ①② 와 다른 기법이다.** `server/vwx/luagen.py`를 AST로 파싱해
       (a) `ChangeDestination`·`CD` 를 담은 **문자열 리터럴이 모듈 전체에 0건**이고,
       (b) 호출자가 준 자유 문자열이 `run_commands` 배열 빌더나 Lua 본문 조립부로
       **도달하는 경로가 0건**임을 확인한다(생성기가 노출하는 API가 `AddFixtures` 인자만 받고
       자유 문자열 삽입 지점을 두지 않는다는 §5 슬롯 C 주장의 기계 검증).
       **비공허성**: 자유 문자열 파라미터를 심은 모듈 사본에서 (b)가 실제로 실패하는지 확인한다.

### AC-AUTOPATCH-015 — 단일 명령 실행 (M4)

**Ubiquitous** The 실행기 **shall** `run_commands(["Plugin '<이름>'"])` 단일 명령으로 보낸다.

- 대상 요구사항: REQ-AUTOPATCH-018
- 검증 방법: `server/tests/test_autopatch_execute.py` — `RecordingExecutionPort`
- 기대 결과:
  - ① 실행 호출의 명령 배열 길이가 **정확히 1**이다.
  - ② 이름이 **작은따옴표**로 감싸이고 큰따옴표가 **0건**이다.
  - ③ 그 호출 앞뒤로 다른 콘솔 명령이 끼지 않는다.

### AC-AUTOPATCH-016 — 점유폭 간격 · 점유 주소 제외 (M4)

**When** 주소를 계획하면, the 시스템 **shall** 점유폭 간격을 두고 점유된 주소를 제외한다.

- 대상 요구사항: REQ-AUTOPATCH-019
- 검증 방법: `server/tests/test_autopatch_lua.py`
- 기대 결과:
  - ① 같은 유니버스 안에서 생성 장비들의 점유 구간이 서로 겹치지 않는다.
       **비공허성**: 간격을 좁힌 입력에서 겹침이 **잡히는지** 확인한다.
  - ② 도면 주소가 콘솔에서 이미 점유되어 있으면 그 항목이 제외되고 사유가 보고된다.
  - ③ 임의의 빈 주소로 재배치하는 경로가 **0건**.

### AC-AUTOPATCH-017 — `deploy_plugin` 파이프라인 경유 (M5)

**Ubiquitous** The 배포기 **shall** 기존 배포 파이프라인을 경유한다.

- 대상 요구사항: REQ-AUTOPATCH-020
- 검증 방법: `server/tests/test_autopatch_execute.py`
- 기대 결과:
  - ① 배포가 `deploy_plugin` 경로로만 일어난다. 별도 배포 호출 **0건**.
  - ② 컴파일 검사·정적 스캔·사람 리뷰 단계를 우회하는 인자가 **0건**.

### AC-AUTOPATCH-018 — `execution_port` 직접 호출 0 (M5)

**Unwanted** The 패치 모듈 **shall not** `execution_port`를 직접 호출한다.

- 대상 요구사항: REQ-AUTOPATCH-021
- 검증 방법: `server/tests/test_autopatch_execute.py` — AST 스캔
  (`server/tests/test_prechk_tool.py:330-343` 관례 계승)
- 기대 결과:
  - ① `server/vwx/` 신규 코드에서 `execution_port.execute` 참조 **0건**.
  - ② **비공허성**: 직접 호출을 심으면 스캐너가 잡는다.
  - ③ `server/vwx/`가 `server.bridge` · `pythonosc`를 import하지 **않는다**.

### AC-AUTOPATCH-019 — 승인 없는 쓰기 0 · 드라이런 무쓰기 (M5)

**Unwanted** The 패치 실행기 **shall not** 명시 승인 없이 콘솔 쓰기를 발생시킨다.

- 대상 요구사항: REQ-AUTOPATCH-004
- 검증 방법: `server/tests/test_autopatch_execute.py` — `RecordingExecutionPort` 호출 기록
- 기대 결과:
  - ① 드라이런 호출에서 콘솔 **쓰기 0건**. 읽기(타입 열거·주소 점유 확인)는 허용된다.
  - ② **비공허성**: 실행 호출에서는 같은 기록기가 쓰기를 **실제로 잡는다**.
  - ③ 실행을 기본값으로 만드는 인자 조합이 없다.

### AC-AUTOPATCH-020 — 멱등 (M6)

**When** 같은 승인 집합을 두 번 실행하면, the 시스템 **shall** 중복을 만들지 않는다.

- 대상 요구사항: REQ-AUTOPATCH-022
- 검증 방법: `server/tests/test_autopatch_verify.py` — 상태를 갖는 더블
- 기대 결과:
  - ① 멱등 일치 기준은 **(유니버스, 주소, FixtureType, DMXMode 이름) 네 값 전부 일치**다.
       2회차 실행에서 그 항목의 생성 명령이 **0건**이고 건너뛴 사실이 보고된다.
  - ② **비공허성**: 1회차에서는 같은 경로가 실제로 생성한다.
  - ③ 부분 중복(일부만 이미 존재)에서 나머지만 생성된다.
  - ④ **주소는 같지만 타입 또는 모드가 다른** 기존 픽스처가 있으면 **건너뛰지 않고 충돌로 보고**한다.
       **비공허성**: 네 값이 모두 같은 경우와 대조해 두 경로가 실제로 갈라지는지 확인한다.

### AC-AUTOPATCH-021 — 검증 읽기 (M6)

**When** 실행이 끝나면, the 시스템 **shall** `precheck_patch`로 다시 읽어 건별 확인한다.

- 대상 요구사항: REQ-AUTOPATCH-023
- 검증 방법: `server/tests/test_autopatch_verify.py`
- 기대 결과:
  - ① 승인 항목마다 확인 결과(관측됨 / 미관측)가 나온다.
  - ② 플러그인 무오류 종료만으로 성공 판정하는 경로가 **0건**.
  - ③ 검증 읽기가 `server/prechk/`의 기존 진입점을 쓰고 자체 읽기 경로를 만들지 않는다.

### AC-AUTOPATCH-022 — 불일치 보고 · 자동 보정 0 (M6)

**When** 검증이 승인 항목과 어긋나면, the 시스템 **shall** 보고하고 자동 보정하지 않는다.

- 대상 요구사항: REQ-AUTOPATCH-024
- 검증 방법: `server/tests/test_autopatch_verify.py`
- 기대 결과:
  - ① 불일치가 구조화되어 나온다.
  - ② 재시도·보정 호출이 **0건**. **비공허성**: 보정 호출을 심으면 잡힌다.
  - ③ 생성 0건이면 "Patch > Fixtures 편집기를 먼저 열라"는 안내가 포함된다.

### AC-AUTOPATCH-023 — 툴 등록 (M7)

**Ubiquitous** The 신규 툴 **shall** 5지점에 등록되고 dispatch로 검증된다.

- 대상 요구사항: (형상 — 특정 REQ가 아니라 배선 전체가 대상)
- 검증 방법: `server/tests/test_autopatch_tool.py`
- 기대 결과:
  - ① 이름이 `TOOL_NAMES`에 있고 `definitions()`에 있으며 **dispatch가 'unknown tool'을 내지 않는다**.
  - ② `advertised == set(TOOL_NAMES)`.
  - ③ 파라미터 스키마에 리그 식별자(슬롯 등)가 들어가지 않는다(PRECHK 관례 계승).

### AC-AUTOPATCH-024 — PRESERVE 0-diff (M7)

**Ubiquitous** The 변경 **shall** PRESERVE 목록을 건드리지 않는다.

- 대상 요구사항: (형상 전체)
- 검증 방법: `git diff --stat <BASE>..HEAD -- <PRESERVE 목록>` — `<BASE>`는 `progress.md` §E.1 실측 SHA
- 기대 결과:
  - ① 출력이 **빈 문자열**이다.
  - ② **비공허성**: PRESERVE 대상에 변경을 일부러 심어 게이트가 **실제로 잡는지** 확인하고 되돌린다.
       이 증명 없이는 인수하지 않는다.

### AC-AUTOPATCH-025 — 1단계 공개 계약 무변경 (M7)

**Ubiquitous** The 확장 **shall** `precheck_vectorworks_diff`의 출력 계약을 바꾸지 않는다.

- 대상 요구사항: (회귀)
- 검증 방법: 기존 `server/tests/test_vwx_*.py` 전수 + **골든 계약 스냅샷** 비교
  (`server/tests/test_autopatch_contract.py` 신설, 픽스처는
  `server/tests/fixtures/vwx/stage1_contract_snapshot.json`)
- 기대 결과:
  - ① **스냅샷 정의**: M1 착수 시점에 1단계 실물 픽스처
       (`vectorworks_worksheet_multisystem_full.csv`)로 `precheck_vectorworks_diff`를 돌려
       payload의 **최상위 키 집합 + 키별 타입 시그니처**(dict/list/str/int/bool, 리스트는 원소 타입)를
       JSON으로 고정한다. 값 자체는 고정하지 않는다 — 값 고정은 무관한 변경에도 깨져 무의미해진다.
  - ② **변경 후 비교**: 같은 픽스처로 다시 돌려 **최상위 키 집합이 정확히 동일**하고
       키별 타입 시그니처가 동일함을 assert한다. 키 추가·삭제·타입 변경이 전부 실패로 잡힌다.
  - ③ 키 **내부** 의미는 기존 구조 assert로 지킨다 — 1단계의
       `test_all_four_structured_categories_exist_independently` 계열을 그대로 통과해야 한다.
       ("각 값의 의미" 를 사람이 판단하는 문장 대신 기존 기계 assert에 위임한다.)
  - ④ **비공허성**: 최상위 키를 하나 추가한 사본에서 ②가 실제로 실패하는지 확인한다.
  - ⑤ 1단계 테스트 전수 통과 · 전체 스위트 무회귀(착수 기준선 이상).

### AC-AUTOPATCH-026 — 라이브 종단 (M8)

**When** 실기에서 대조→승인→드라이런→실행→검증을 왕복하면, the 시스템 **shall** 1회 통과한다.

- 대상 요구사항: (통합)
- 검증 방법: 실기 onPC 2.4.2 라이브 세션 2. **테스트 쇼파일**에서만 수행.
- 기대 결과:
  - ① 승인한 장비가 도면 주소에 도면 타입으로 생성되고 검증 읽기가 확인한다.
  - ② 세션 전에 쇼파일이 테스트용임을 사용자가 확인했음이 기록된다.
  - ③ 세션 후 생성물 제거를 사용자가 확인했음이 기록된다.
  - ④ 실패했으면 실패로 기록한다 — 부분 성공을 통과로 적지 않는다.

### AC-AUTOPATCH-027 — `ASSUMPTION-71` 부정 시 구조화된 FID 범위 확인 (M2)

**When** `ASSUMPTION-71`이 부정 또는 INCONCLUSIVE인 상태에서 실행을 시도하면, the 시스템
**shall** 별도 페이로드 필드로 캡처된 사용자 확인을 요구하고, 없으면 거부한다.

- 대상 요구사항: REQ-AUTOPATCH-026
- 검증 방법: `server/tests/test_autopatch_fid.py` — 세 분기(GO · 부정+확인있음 · 부정+확인없음)
- 기대 결과:
  - ① 부정/INCONCLUSIVE 분기에서 확인 필드가 **없으면 실행이 거부**되고, 사유가
       "FID 범위를 콘솔에서 눈으로 확인했다는 별도 확인이 필요하다"를 담는다.
  - ② 확인은 **일반 승인과 구분되는 별도 필드**로 캡처된다 — 항목 선택이나 `dry_run=false`가
       그 확인을 함축하지 않는다. 실행 결과 페이로드에 그 확인이 기록되어 **건별로 감사 가능**하다.
  - ③ **GO 분기에서는 이 확인을 요구하지 않는다.** **비공허성**: 같은 입력에서 GO는 통과하고
       부정은 거부되는 것을 대조로 확인한다 — 확인이 항상 요구되면 이 AC는 공허하다.
  - ④ 산문 경고만 있고 필드가 없는 페이로드는 ①에 의해 거부된다.

---

## §F. Definition of Done

1. AC-AUTOPATCH-001~027 **27건 전량 PASS**(§C.0a 마일스톤 배정 합 27과 일치).
2. REQ-AUTOPATCH-001~026 **26건 전량** 커버(§C.0 "REQ 26/26 커버, 누락 0"과 일치).
3. `ASSUMPTION-71`~`-75` **5건 전부 판정 확정**(GO / NEGATIVE / INCONCLUSIVE).
4. 라이브 세션 2회 수행 및 기록. 두 세션 모두 테스트 쇼파일.
5. PRESERVE diff 빈 출력 + 게이트 **비공허성 증명**.
6. 전체 스위트 0 failed · `ruff` clean(신규·변경 파일).
7. "0건" 주장 AC 전부에 **비공허성 대조군**이 붙어 있다.
