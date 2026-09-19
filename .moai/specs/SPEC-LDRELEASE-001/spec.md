---
id: SPEC-LDRELEASE-001
title: "Director apply destination 예약 해제(release) 절차"
version: "0.2.0"
status: in-progress
created: 2026-09-19
updated: 2026-09-19
author: jaihyun
priority: P2
phase: "Lighting Director v1.0 target"
module: "server/director"
lifecycle: spec-anchored
tags: "lighting-director, destination-reservation, recovery, execution-journal, safety-gate"
tier: S
depends_on: [SPEC-LDSEND-001]
---

# SPEC-LDRELEASE-001

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-09-19 | 최초 작성. 큐 카드 t422 를 SPEC 으로 승격. 근본 원인은 `SPEC-LDSEND-001` M5 실기 관측(`../SPEC-LDSEND-001/progress.md` §M5, 2026-09-18)에서 드러났다 — 032 시나리오에서 원본 apply 가 `partial` 로 끝난 뒤, 그 원본이 점유한 scratch destination(`show=1, sequence=9903`)을 recovery apply 가 재사용하지 못해 새 destination(`sequence=9904`)에 써야 했다. 사람이 2026-09-19 이 우회를 AC-LDPLUGIN-032 실행부 관측으로 **인정**하면서, 예약 해제 절차 자체는 후속 카드 t422 로 넘겼다(`../SPEC-LDSEND-001/progress.md` 892행). |
| 2026-09-19 | 1차 plan-audit(`.moai/reports/plan-audit/SPEC-LDRELEASE-001-review-1.md`, 반복 1/3, FAIL 0.667) 반영 개정. D1(전이-후-게이트-거부 복합 실패 미명세) → REQ-LDRELEASE-008 신설. D2(REQ-007 근거 인용 오류) → 잘못된 인용 제거, M1 에 신규 characterization 시험 추가 계획, AC 판정 명령 정정. D3(tier: S 인데 acceptance.md 를 따로 둔 아티팩트셋 불일치) → ACs 를 본 문서 §3 에 REQ 와 1:1 인라인으로 옮기고 `acceptance.md` 를 삭제해 진짜 Tier S 로 정렬. D4("CI 가 저장소 전체가 죽어있다") → 근거 없는 승계 주장 대신 2026-09-19 실측(`gh run list --branch main --limit 3`)으로 대체. D5(REQ-005/006 인용 범위가 실제 분기 본문을 못 덮음) → 인용 범위 확장. D6(REQ-003 문형이 정형 GEARS 템플릿에서 벗어남) → 평서형 Ubiquitous 문장으로 재작성. |

## 1. 목적과 경계

`ExecutionJournal._reserve_destination_locked`(`server/director/execution.py:634-666`)는
destination 예약을 **create-only** 로 영구 유지한다 — 명시적으로
`release_destination()`(`execution.py:668-675`)이 호출되기 전에는, 그 슬롯을
점유했던 execution 이 이후 `partial`/`unknown`/`failed` 어느 상태로 끝나든
예약이 저절로 풀리지 않는다. 그런데 `release_destination()`은 오늘 정확히
**한 곳**에서만 호출된다 — `ApplyCoordinator.apply()`(`execution.py:961`) 안,
`execute_preapproved()`가 **송신 시도 전에** 거부했을 때뿐이다(`execution.py`
952-969행 주석 — "실제 송신은 시도된 적이 없다는 것이 이 분기에 도달했다는
사실 자체로 확정되므로"). `execute_bundles()`가 실제로 콘솔에 무언가를
보낸 뒤 `STATE_PARTIAL`/`STATE_UNKNOWN`으로 끝나는 경우는 이 즉시-해제
대상이 **아니다** — 콘솔에 무엇이 도달했는지 불확실하기 때문이다(같은 주석).

이 SPEC 은 그 뒤에 남는 빈 자리를 채운다: `partial`로 끝난 원본이 점유한
destination 을, 그 원본을 가리키는 `recovery_of` apply 가 **다시 쓸 수
있게** 한다. `SPEC-LDRECV-001`/`SPEC-LDSEND-001`이 이미 세운 재검사·직렬화·
승인 소비 순서는 바꾸지 않는다 — 이 SPEC 이 건드리는 것은 `destination_
reservations` 테이블의 소유권 이전·복원 로직뿐이다(1차 감사 D1 반영 —
전이가 일어난 뒤 그 recovery 자체가 게이트에서 거부되는 복합 실패까지
포함한다, §3 REQ-LDRELEASE-008).

| 규범 | 위치 |
|---|---|
| create-only 예약 본체 | `server/director/execution.py:634-666` `_reserve_destination_locked` |
| 공개 예약/해제 API | `execution.py:614-632` `reserve_destination`, `:668-675` `release_destination` |
| destination 상태 조회 | `execution.py:677-692` `destination_status` |
| 유일한 기존 release 호출 지점(송신 전 거부) | `execution.py:952-969`(`ApplyCoordinator.apply()`), 특히 `:961` |
| execution 상태 집계·`recovery_required` 판정 | `execution.py` `execute_bundles`(약 1063-1145행), 특히 상태 우선순위 표(1121-1129행) |
| `recovery_of` 대상 상태 검사(partial/unknown 만 허용) | `execution.py:872-878` |
| recovery 링크 기록(원본 행 불변) | `execution.py:942-945` `record_recovery_link`; 검증: `server/tests/test_director_ops_lifecycle.py:540-619` |
| `recovery_required`↔`partial` 계약 | `../SPEC-LDRECV-001/acceptance.md:21,157` — `recovery_required`는 `unknown` 에만 결부된다 |
| 실기 관측 선례(이 SPEC 의 동기) | `../SPEC-LDSEND-001/progress.md` §M5(878-881행) — 032 시나리오, 9903→9904 우회 |

## 2. 범위 결정

- **판정·직렬화·승인 순서는 바꾸지 않는다.** `ApplyCoordinator.apply()`의
  기존 단계(승인 신선도 → LiveLock → destination 예약 → `execute_preapproved`
  → `execute_bundles`)는 그대로다. 이 SPEC 은 그 중 "destination 예약" 단계
  하나의 **가능한 결과**를 넓힌다 — 지금까지는 점유된 슬롯이면 무조건
  `TARGET_BUSY` 였던 것을, `recovery_of` 가 그 슬롯의 현재 점유자를 정확히
  가리키고 그 점유자가 `partial` 이면 **원자적 이전**을 허용한다.
- **이전은 `begin_execution` 의 기존 단일 transaction 안에서 일어난다.**
  새 API 왕복이나 새 lock 을 추가하지 않는다 — `_reserve_destination_locked`
  가 이미 `begin_execution`(`execution.py:356-441`)의 transaction 안에서
  호출되므로, 그 자리에서 원본 상태를 확인하고 소유권을 넘긴다.
- **원본 execution 행은 이 SPEC 으로도 바뀌지 않는다.** `record_recovery_link`
  가 이미 지키는 불변식(원본 테이블 행 불변, `test_director_ops_lifecycle.py`
  588-619행)을 그대로 유지한다 — 바뀌는 것은 `destination_reservations`
  테이블의 `reserved_by_execution_id`/`reserved_at` 뿐이다.
- **`unknown` 원본은 이전 대상이 아니다(D1 채택, 안전 사유는 plan.md 참고).**
  콘솔에 무엇이 실제로 도달했는지 불확실한 상태에서 같은 destination 에
  다시 쓰면 이미 남아있을 수도 있는 명령과 충돌할 위험이 있다 — `unknown`
  원본을 가리키는 recovery 는 오늘과 같은 `TARGET_BUSY` 로 거부되고, 사람이
  콘솔을 직접 확인(readback)한 뒤 별도 조치를 하게 남긴다.
- **`recovery_of` 가 다른 destination 을 쓰거나 아예 없으면 오늘과 동일하다.**
  create-only 규칙은 그대로 적용된다 — 이 SPEC 은 "같은 슬롯을 원본이
  가리키는 recovery 가 다시 쓰는" 경로 하나만 추가한다.
- **`recovery_required` 계약은 코드로 바꾸지 않는다(D2 채택).** `partial`
  결과에 명시적 `failed` 가 섞여도 `recovery_required` 는 오늘처럼 `False`
  로 남는다 — 이 SPEC 은 그것이 의도적 계약임을 §3 REQ-LDRELEASE-007 로
  문서화만 한다.
- **이전이 일어난 recovery 가 그 뒤 게이트에서 거부되면, 슬롯은 완전
  해제가 아니라 원본에게 되돌아간다(1차 감사 D1 반영, D1 보완).**
  REQ-LDRELEASE-001 로 destination 을 넘겨받은 recovery execution 이
  `execute_preapproved()`에서 (destination 점유와 무관한 사유로) 거부되면,
  기존 REQ-LDRELEASE-004 의 무조건 `release_destination()` 을 그대로
  적용할 경우 그 슬롯이 완전히 `released` 로 열려 `recovery_of` 링크 없는
  무관한 apply 도 재사용할 수 있게 된다 — create-only 가 지키려던 "누가
  이 슬롯을 다시 쓸 자격이 있는가" 감사 가능성이 이 경로에서만 무너진다.
  이 SPEC 은 그 경로를 REQ-LDRELEASE-008 로 명세하고, 전이가 없었던 일반
  경로에는 REQ-LDRELEASE-004 의 무조건 해제를 그대로 남긴다.

## 3. 안정 요구사항

`SHALL` 은 필수다. Tier S — 인수 기준(Given-When-Then)은 각 REQ 바로 아래
인라인으로 REQ 와 1:1 대응한다.

### REQ-LDRELEASE-001

**When** `recovery_of=<원본 execution_id>` 를 실은 apply 가 그 원본이 현재
점유한 destination(show_id+sequence_id 일치)을 targeting 하고, **Where**
그 원본의 journal 상태가 `partial` 이면, `ExecutionJournal` 은 **SHALL**
`begin_execution` 의 같은 transaction 안에서 그 destination 예약을 원본
execution 에서 새 recovery execution 으로 원자적으로 이전하고, 그 apply 를
`TARGET_BUSY` 로 거부하지 않는다.

**규범 참조**: `execution.py:634-666`(`_reserve_destination_locked`);
`:356-441`(`begin_execution`); `:926-935`(호출 지점)

**AC-LDRELEASE-001**: **Given** `partial`로 확정된 원본 execution 이
destination(show=1, sequence=9903)을 점유하고 있다, **When** 새 apply 가
`recovery_of=<원본 execution_id>`와 함께 같은 destination(show=1,
sequence=9903)을 targeting 하며 도착한다, **Then** 그 apply 는
`TARGET_BUSY`로 거부되지 않고 destination 예약이 원본에서 새 recovery
execution 으로 이전되며, `destination_status(show=1, sequence=9903)`의
`reserved_by_execution_id`가 새 recovery execution_id 로 바뀐다.

### REQ-LDRELEASE-002

**When** `recovery_of=<원본 execution_id>` 를 실은 apply 가 그 원본이 현재
점유한 destination 을 targeting 하고, **Where** 그 원본의 journal 상태가
`unknown` 이면, `ExecutionJournal` 은 **SHALL** 예약 이전을 거부하고
`TARGET_BUSY` 를 반환한다 — 콘솔에 실제로 무엇이 도달했는지 불확실한
상태에서는 자동 이전하지 않는다.

**규범 참조**: `execution.py:872-878`(원본 상태 검사 선례); D1 안전
사유(plan.md)

**AC-LDRELEASE-004**: **Given** `unknown`으로 확정된 원본 execution 이
destination(show=1, sequence=9903)을 점유하고 있다, **When** 새 apply 가
`recovery_of=<원본 execution_id>`와 함께 같은 destination 을 targeting 하며
도착한다, **Then** 예약은 이전되지 않고 `TARGET_BUSY`로 거부되며,
`destination_status`의 점유자는 원본 execution_id 그대로다.

### REQ-LDRELEASE-003

The `ExecutionJournal` SHALL leave the original `executions` row unchanged
during a transfer; only `destination_reservations.reserved_by_execution_id`/
`reserved_at` change. (평서형 Ubiquitous — REQ-LDRELEASE-001 이 수행하는
예약 이전이 일어나는 동안, 원본 execution 의 `executions` 테이블 행
(상태·bundle·타임스탬프)은 단 한 바이트도 바뀌지 않는다.)

**규범 참조**: `record_recovery_link` 가 지키는 기존 불변식과 동형;
`test_director_ops_lifecycle.py:588-619`

**AC-LDRELEASE-005**: **Given** `SPEC-LDSEND-001` M5 032 시나리오의
재구성(원본 apply 가 `Store Sequence 9903 Cue 1 /Merge` 뒤 확정 실패
명령으로 `partial` 종결), **When** `run_director_apply()` 경로로
`recovery_of=<원본>`과 destination(show=1, sequence=**9903**, 9904 가
아님)을 실은 recovery apply 를 fake `BundleSender`/fake 콘솔로 구동한다,
**Then** recovery 는 새 destination 을 만들지 않고 9903 을 재사용해
`sent`로 끝나며, 원본 execution 행(`state`/`bundles`/`created_at`)은
recovery 전후로 완전히 동일하다. **콘솔 필요(선택, 후속 확인 권장)**:
실기에서 이 시나리오를 재실행해 9903 재사용을 readback 으로 확인하는 것은
이 SPEC 의 로컬 판정 범위 밖이다.

### REQ-LDRELEASE-004

`ApplyCoordinator.apply()`의 기존 송신-전 거부 경로(`execute_preapproved`
가 `cleared=False` 를 반환하는 경우)는 **SHALL** — 이 apply 가
REQ-LDRELEASE-001 원자적 이전으로 destination 을 넘겨받은 것이 **아닌**
한 — 오늘과 동일하게 `release_destination()`을 호출해 그 destination 을
즉시 해제한다. 전이가 일어난 apply 에 대한 처리는 REQ-LDRELEASE-008 이
좁힌다.

**규범 참조**: `execution.py:952-969`, 특히 `:961`

**AC-LDRELEASE-002**: **Given** apply 요청이 `execute_preapproved()`에
의해 송신 시도 전에 거부된다(`cleared=False`), 그리고 이 apply 는
REQ-LDRELEASE-001 이전을 거치지 않았다(recovery_of 없음, 또는
recovery_of 가 있어도 destination 이전이 일어나지 않은 경우), **When**
`ApplyCoordinator.apply()`가 그 거부를 처리한다, **Then** 오늘과 동일하게
`finalize_execution(..., STATE_FAILED)`과 `release_destination(...)`이
호출되고 그 destination 은 즉시 `released` 상태가 된다 — 이 SPEC 반영
전후로 이 경로의 관측 가능 동작이 바이트 동일하다(`test_director_apply_
rejection.py` 회귀).

### REQ-LDRELEASE-005

**When** apply 가 `recovery_of` 없이 오거나, `recovery_of` 는 있지만
targeting 하는 destination 이 그 원본이 점유한 destination 과 다르면,
`ExecutionJournal` 은 **SHALL** 오늘과 동일한 create-only 규칙(점유돼
있으면 무조건 `TARGET_BUSY`, 조용한 재선택 없음)을 적용한다.

**규범 참조**: `execution.py:634-659`(기존 create-only 분기 — `existing`
None 이면 INSERT `:653-659`, `RESERVED` 면 `TARGET_BUSY` `:646-651`);
`test_director_execution_journal.py:335-352`

**AC-LDRELEASE-006**: **Given** `partial`로 확정된 원본 execution 이
destination(show=1, sequence=A)을 점유하고 있다, **When** 새 apply 가
`recovery_of=<원본 execution_id>`와 함께 **다른** destination(show=1,
sequence=B, 비어있음)을 targeting 하며 도착한다, **Then** 예약 이전
로직은 관여하지 않고 오늘과 동일한 create-only 규칙으로 destination B 가
새로 예약된다(`test_recovery_of_accepts_partial_source`가 이미 이 형태로
회귀를 고정한다).

### REQ-LDRELEASE-006

**While** 한 destination 슬롯이 `recovery_of` 가 가리키지 않는 다른
execution 에 의해 점유돼 있으면, `ExecutionJournal` 은 **SHALL** 오늘과
동일하게 `TARGET_BUSY` 로 거부한다 — REQ-LDRELEASE-001 의 이전 경로는
정확히 그 슬롯의 현재 점유자를 `recovery_of` 가 직접 가리킬 때만 열린다.

**규범 참조**: `execution.py:640-651`(기존 `TARGET_BUSY` 분기 — 조건
`:640-646` + `raise _target_busy(...)` 본문 `:647-651`);
`test_director_execution_journal.py:335-352`

**AC-LDRELEASE-003**: **Given** destination(show=1, sequence=1)이
execution A 에 의해 점유돼 있다, **When** execution B 가 `recovery_of`
없이, 또는 `recovery_of`가 execution A 가 아닌 다른(또는 존재하지 않는)
execution 을 가리키며 같은 destination 을 예약하려 한다, **Then** 오늘과
동일하게 `TARGET_BUSY`(HTTP 409)로 거부되고 `destination_status`의
점유자는 execution A 그대로다(조용한 재선택 없음,
`test_reservation_does_not_silently_reselect_a_different_slot` 회귀와
동형).

### REQ-LDRELEASE-007

`execute_bundles()`의 집계 `recovery_required` 플래그는 **SHALL**
`partial` 결과(명시적 `failed` 가 섞인 경우 포함)에 대해 오늘과 동일하게
`False` 로 남는다 — `recovery_required=True` 는 `unknown`(간섭 감지
포함) 결과에만 결부된 계약이며, 이 SPEC 은 그 계약을 코드로 바꾸지 않고
문서로만 확정한다(D2).

**규범 참조**: `execution.py` `execute_bundles` 상태 우선순위 표;
`../SPEC-LDRECV-001/acceptance.md:21,157`;
`server/tests/test_director_execution_failure.py::TestStatePriority::
test_partial_with_explicit_failed_recovery_required_stays_false`(M1 신규
— plan.md §D 참고. 1차 감사가 지적한 대로 `:133`은 `partial`이 아니라
`test_failed_when_nothing_confirmed_and_no_unknown`(전부 `failed`인
경우)의 단언이었다 — 이 인용은 삭제한다.)

**AC-LDRELEASE-007**: **Given** `execute_bundles()`가 여러 bundle 중 하나
이상 `failed`, 나머지 confirmed(acknowledged/sent) 로 끝나 `partial`을
반환한다, **When** 그 결과의 `recovery_required` 필드를 읽는다, **Then**
`False`다 — 이 SPEC 반영 전후로 값이 바뀌지 않는다. 이 값은 M1 에서 새로
추가하는 characterization 회귀
(`test_partial_with_explicit_failed_recovery_required_stays_false`)가
단언한다 — 오늘 코드에서 이미 `False`이므로 이 시험은 RED-first 가 아니라
**기존 동작을 고정하는 회귀 핀**이다(D2, "코드 변경 없음"). 판정 명령:
`uv run pytest server/tests/test_director_execution_failure.py -q -k
test_partial_with_explicit_failed_recovery_required_stays_false`.

### REQ-LDRELEASE-008

**When** `execute_preapproved()`가 송신 전 apply 를 거부하고
(`cleared=False`), **Where** 그 apply 가 REQ-LDRELEASE-001 원자적 이전으로
destination 소유권을 원본 execution 에서 넘겨받은 recovery execution
이면, `ExecutionJournal` 은 **SHALL** 그 destination 예약을
`release_destination()`으로 완전히 풀지(`released`) 않고 원본
execution(`recovery_of` 가 가리키던 execution_id)에게 되돌린다
(`reserved_by_execution_id` = 원본 execution_id, `status` 는 `reserved`
로 유지) — 그래야 이후 원본을 가리키는 다른 recovery 시도가 같은
슬롯을 다시 겨냥할 수 있다. 전이가 없었던 execution(REQ-LDRELEASE-005/
006 경로)에는 이 REQ 가 적용되지 않는다 — REQ-LDRELEASE-004 의 무조건
해제가 오늘처럼 그대로 적용된다.

**규범 참조**: `execution.py:926-935`(전이 발생 지점,
`begin_execution` 호출); `:952-965`(gate 거부 분기), 특히 `:961`(기존
무조건 `release_destination` 호출을 이 REQ 가 조건부로 좁힌다);
plan.md §C(신규 `restore_destination` 메서드 + `ApplyCoordinator.apply()`
분기 설계) — 1차 plan-audit D1 반영.

**AC-LDRELEASE-008**: **Given** `partial`로 확정된 원본 execution 이
destination(show=1, sequence=9903)을 점유하다가, `recovery_of=<원본>`을
실은 recovery apply 가 REQ-LDRELEASE-001 이전으로 그 destination
소유권을 넘겨받았다(`destination_status`의 `reserved_by_execution_id`가
recovery execution_id 로 바뀐 상태), **When** 그 recovery apply 자체가
이어서 `execute_preapproved()`에 의해 송신 전 거부된다(`cleared=False`,
문법/분류/backup/health/중재자 lock 등 destination 점유와 무관한 사유),
**Then** `destination_status(show=1, sequence=9903)`은 `released` 상태가
되지 않고 `reserved_by_execution_id`가 원본 execution_id 로 되돌아가며
`status`는 `reserved`로 남는다 — 이후 원본을 가리키는 또 다른 recovery
apply 가 같은 destination 을 다시 시도할 수 있다(`test_director_apply_
rejection.py` 신규 케이스 계획, plan.md §D M1).

## 4. 비목표

### Out of Scope — 판정·승인·직렬화

- `ApplyCoordinator.apply()`의 재검사 순서(승인 신선도·LiveLock·게이트 연결)
  변경은 포함하지 않는다 — `SPEC-LDRECV-001`/`SPEC-LDSEND-001` 소유다.
- 새 HTTP 엔드포인트나 운영자용 "수동 release" API 는 만들지 않는다(D1 에서
  기각한 대안 — plan.md 참고). 이전은 오직 `recovery_of` 를 통한 apply
  경로 안에서만 일어난다.
- `unknown` 상태 원본에 대한 자동/수동 release 절차는 포함하지 않는다 —
  REQ-LDRELEASE-002 가 명시하는 대로 그 경로는 계속 거부된다. 사람의 콘솔
  확인 뒤 조치는 이 SPEC 범위 밖이다.
- `InterferenceDetector` 실물 구현, SafetyGate 문법/분류/backup/health/audit
  변경은 포함하지 않는다.

### Out of Scope — LDRECV 계약·콘솔 게이트 최종 판정

- `execute_bundles()`의 `recovery_required` 산출 로직 자체를 바꾸는 것(D2
  에서 기각한 대안 — "partial+failed 이면 True 로 뒤집기")은 포함하지
  않는다. REQ-LDRELEASE-007 은 현재 동작을 문서화할 뿐이다.
- `SPEC-LDRECV-001`/`SPEC-LDSEND-001` 의 spec.md/plan.md/acceptance.md 본문
  변경은 포함하지 않는다 — 둘 다 `completed` 로 닫혔다.
- 실기 콘솔에서 이 SPEC 의 REQ-LDRELEASE-001/002 를 관측하는 것(LDSEND M5
  032 시나리오를 이 SPEC 반영 후 재실행해 9903 재사용을 확인하는 것)은
  이 SPEC 의 로컬 pytest 판정 범위 밖이다 — §5 참고.

## 5. 검증 수단의 한계 (착수 전 고지)

**CI 상태(2026-09-19 실측)**: `gh run list --branch main --limit 3` 결과,
`test` 워크플로우가 2026-09-19T08:56:16Z 에 `completed`/`success`로
끝났다(런 35433334782, `main`, PR #463 머지 트리거). CI 는 죽어있지
않다 — `uv run pytest` 로컬 실행이 이 SPEC 의 1차 자동 판정 근거이고, CI
는 이를 보조 확인하는 2차 수단이다.

| 판정 | 수단 | 콘솔 필요 |
|---|---|---|
| REQ-001~006, 008(예약 이전·거부·원본 행 불변·전이-후-거부 복원) | fake 콘솔/게이트 + pytest (`ExecutionJournal` 단위 시험 + `ApplyCoordinator` 통합 시험) | 아니오 |
| REQ-007(`recovery_required` 계약 문서화) | M1 신규 characterization 회귀(`test_partial_with_explicit_failed_recovery_required_stays_false`) | 아니오 |
| LDSEND M5 032 시나리오가 이 SPEC 반영 후 9903 을 재사용하는지 | onPC 실기 관측 — 이 SPEC 의 로컬 pytest 로는 fake 콘솔로만 재현한다(AC-LDRELEASE-005) | 예(선택 — 후속 SPEC/M 에서 재확인 권장) |
