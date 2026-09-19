# 구현 계획 — SPEC-LDRELEASE-001

[요구사항 + 인수 기준](spec.md#3-안정-요구사항) — Tier S, AC 는 spec.md §3 에 REQ 와
1:1 인라인(`acceptance.md` 없음, 1차 감사 D3 반영).

## §A. 컨텍스트

- 위치: `server/director/execution.py` (`ExecutionJournal`, `ApplyCoordinator`) — 단일 파일 변경.
- 근본 원인: `_reserve_destination_locked`(`execution.py:634-666`)가 create-only 이고, `release_destination()`(`:668-675`)의 유일한 호출 지점(`:961`)이 **송신 전 거부**에만 걸려 있다 — `execute_bundles()`가 실제로 콘솔에 무언가를 보낸 뒤 `partial`/`unknown`으로 끝나는 경우는 그 즉시-해제 대상이 아니다(의도된 설계 — 콘솔 상태 불확실).
- 실측 선례: `.moai/specs/SPEC-LDSEND-001/progress.md` §M5(2026-09-18) — 032 시나리오에서 원본이 `partial`로 끝난 뒤 recovery 가 원본 destination(9903)을 못 쓰고 새 destination(9904)을 썼다. 사람이 이 우회를 AC-LDPLUGIN-032 관측으로 인정하며 release 절차를 t422 로 미뤘다.
- PRESERVE: `ApplyCoordinator.apply()`의 재검사 순서(승인 신선도 → LiveLock → destination 예약 → `execute_preapproved` → `execute_bundles`), `record_recovery_link`의 원본 행 불변 불변식, `execute_bundles()`의 상태 우선순위 계산 전부.
- 개발 방법론: TDD (quality.yaml `constitution.development_mode: tdd`) — RED(예약 이전 실패 재현) → GREEN(이전 로직 구현) → REFACTOR.

## §B. 설계 결정 (D1, D2) — 되돌리기 가장 어려운 결정부터

### D1 — partial/unknown 예약의 release 경로

**후보:**

- (a) **release-on-recovery** — `recovery_of` apply 가 원본 destination 을 그대로 targeting 하면, journal 이 `begin_execution` 트랜잭션 안에서 예약을 원자적으로 이전한다(원본은 `partial`로 남고, 링크는 오늘처럼 `record_recovery_link`로 기록).
- (b) 명시적 운영자 release 검증/엔드포인트 — director API 에 `release_destination`을 노출하고 감사 로그를 남긴다.
- (c) 원본이 `partial`로 최종 확정되면 자동 해제(`unknown`은 콘솔 상태 불확실이므로 거부).

**채택: (a), `partial` 원본에 한정 + `unknown` 원본은 (c)의 거부 방향을 그대로 가져와 결합.**

- (a)를 고른 이유: `recovery_of`는 이미 apply 요청 body 를 관통하는 필드이므로(LDRECV M6), 새 엔드포인트나 새 승인 경로 없이 기존 apply 흐름 안에서 자연스럽게 해소된다 — 승인·직렬화·journal 판정 순서를 하나도 바꾸지 않는다.
- (b)를 기각한 이유: 새 HTTP 표면·새 자격 문제를 만든다 — `SPEC-LDSEND-001` D9 가 이미 "관측 도구가 director-apply 경로를 우회하지 않는다"는 원칙을 세웠는데, 별도 release 엔드포인트는 그 경로 밖의 새 승격 지점이 된다.
- (c)를 그대로 채택하지 않은 이유(자동·무조건 해제): `partial`로 확정된 즉시 아무 recovery 요청 없이도 슬롯이 열리면, 그 destination 을 가리키는 recovery_of 가 없는 무관한 apply 도 같은 슬롯을 재사용할 수 있어 create-only 의 "누가 이 슬롯을 다시 쓸 자격이 있는가" 감사 가능성이 약해진다. (a)는 그 자격을 `recovery_of` 링크로 명시적으로 요구한다.
- **콘솔 안전 고려(원본이 `unknown`이면 이전을 거부하는 이유)**: scratch Sequence(예: 9903)는 partial 실행이 이미 부분적으로 병합한 cue 를 담고 있다. `partial`은 어떤 bundle 이 확인됐고 어떤 것이 실패했는지 정확히 아는 상태이므로, recovery 가 그 위에 `Store Sequence 9903 Cue N /Merge` 류 명령을 이어 보내는 것은 알려진 상태 위의 알려진 조작이다. 반면 `unknown`은 콘솔에 무엇이 실제로 도달했는지 모르는 상태다 — 그 위에 다시 쓰면 이미 있을 수도 있는 명령과 뜻하지 않게 충돌하거나 중복 적용될 위험이 있다. 그래서 `unknown` 원본은 이전 대상에서 제외하고 오늘과 동일한 `TARGET_BUSY`로 남긴다 — 사람이 콘솔을 readback 으로 직접 확인한 뒤에만 그 슬롯을 다룰 수 있다(이 SPEC 밖의 수동 조치, §4 Out of Scope).
- 이전 조건은 **명시적 일치**를 요구한다 — recovery apply 의 요청 destination(show_id+sequence_id)이 `recovery_of`가 가리키는 원본이 실제로 점유한 destination 과 정확히 같을 때만 이전이 성립한다. `recovery_of`만으로 원본의 destination 을 암묵적으로 신뢰해 자동 대입하지 않는다 — 호출자가 무엇을 재사용하려는지 요청 자체에서 감사 가능해야 한다.

**D1 보완 — 이전-후-게이트-거부 복합 실패(1차 plan-audit D1, FAIL 0.667, blocking).** `ApplyCoordinator.apply()`는 `begin_execution`(destination 예약/이전 단계, `:926-935`)을 호출한 *뒤에야* `gate.execute_preapproved()`(`:951`)를 부른다. 그래서 recovery apply 의 이전이 성공(destination 을 새 recovery execution 이 원자적으로 넘겨받음)한 **직후**, 그 SafetyGate 가 (destination 점유와 무관한 사유 — 문법/분류/backup/health/중재자 lock — 로) `cleared=False`를 반환하면, 기존 REQ-LDRELEASE-004 의 무조건 `release_destination()`(`:961`)이 그대로 걸린다. 이건 그 슬롯을 완전히 `released`로 열어버린다는 뜻이다 — `recovery_of` 링크 없는 무관한 apply 도 곧바로 그 슬롯을 재사용할 수 있게 된다. 이 SPEC 도입 이전에는 이 경로가 존재조차 하지 않았다(점유된 destination 을 targeting 하는 recovery 는 예약 단계에서 곧바로 `TARGET_BUSY`로 실패해 게이트 단계에 아예 도달하지 않았다) — REQ-LDRELEASE-001 이 새로 여는 이전 경로가 이 복합 실패의 원인이다.

- **채택: 전이가 일어난 경우, 게이트 거부는 무조건 release 대신 원본에게 소유권을 되돌린다(REQ-LDRELEASE-008).** (a)의 "recovery_of 링크가 재사용 자격을 명시적으로 증명한다"는 감사 가능성을 이 복합 경로에서도 지킨다 — 원본이 `partial`로 남아있는 한, 그 원본을 가리키는 **다른** recovery 가 다시 그 슬롯을 이전받을 수 있다(REQ-LDRELEASE-001 이 이미 하는 검사가 그대로 재사용됨). 완전 해제(오늘의 무조건 동작을 그대로 둠)를 기각한 이유: 위에서 서술한 대로 무관한 apply 가 자격 없이 그 슬롯을 가져갈 수 있다.
- 전이가 없었던 일반 경로(REQ-LDRELEASE-005/006 이 다루는, `recovery_of`가 없거나 다른 destination 을 targeting 하는 apply)는 이 보완의 영향을 받지 않는다 — REQ-LDRELEASE-004 의 무조건 release 가 오늘과 동일하게 적용된다.

### D2 — 명시적 `failed`가 섞인 `partial`의 `recovery_required`

**후보:** (i) `False` 유지 + 이 SPEC 에 의도적 계약으로 문서화, (ii) `True`로 뒤집기.

**채택: (i) `False` 유지, 문서화만.**

- 이유: `partial`은 이미 "어떤 bundle 이 확인됐고 어떤 것이 실패했는지" 클라이언트가 아는 **확정 상태**다 — `recovery_required`는 `execution.py` 모듈 자신의 계약("blind 하게 success/failed 로 확정하지 않는다")과 `../SPEC-LDRECV-001/acceptance.md:21,157`이 함께 가리키듯 **상태 자체가 불확실**(`unknown`)할 때만 켜지는 신호다. `partial`에서 recovery 를 걸지 여부는 클라이언트(또는 사람)의 판단이지, journal 이 강제할 결정이 아니다.
- (ii)를 기각한 이유: 뒤집으면 `test_director_execution_failure.py:133`(`recovery_required is False` 를 `partial`에 대해 단언하는 기존 회귀)이 깨지고, `SPEC-LDRECV-001` 이 이미 완결한 계약(§157)을 이 SPEC 이 소급 변경하는 셈이 된다 — 이 SPEC 의 목적(destination release)과 무관한 계약 변경이라 범위 이탈이다.
- 코드 변경 없음 — REQ-LDRELEASE-007 은 기존 동작을 확정하는 문서 전용 요구사항이다. 바뀌는 문서: 이 SPEC 의 spec.md §2/§3 뿐(LDRECV/LDSEND 본문은 완결된 채 그대로 둔다, §4 Out of Scope).

`[NEEDS CLARIFICATION]` 마커: 없음 — 두 결정 모두 위 근거로 확정한다.

## §C. 기술 접근 — 변경 파일과 줄 포인터

모두 `server/director/execution.py` 안이다 (새 파일 없음, Enforce Simplicity — 기존 함수 셋의 시그니처 확장만).

1. **`ExecutionJournal._reserve_destination_locked`(`:634-666`)** — `transfer_from: str | None = None` 파라미터 추가. 기존 로직(existing None → INSERT, existing RESERVED → TARGET_BUSY)은 그대로 두고, `existing`이 RESERVED 이고 `transfer_from`이 주어졌을 때의 분기를 삽입:
   - `existing["reserved_by_execution_id"] == transfer_from`이 아니면 → 오늘과 동일한 TARGET_BUSY(REQ-LDRELEASE-006).
   - 같으면 `self.status(transfer_from)`을 읽는다(`:589-609`, 같은 connection·같은 transaction 안이라 추가 lock 불필요).
     - `STATE_PARTIAL`이면 UPDATE 로 `reserved_by_execution_id`/`reserved_at`을 새 execution_id 로 이전(REQ-LDRELEASE-001)하고, 이전이 실제로 일어났음을 호출자에게 알린다(아래 2번 항목의 `transferred_from` 참고).
     - 그 외(특히 `STATE_UNKNOWN`)면 TARGET_BUSY(REQ-LDRELEASE-002) — 메시지에 "원본 상태가 unknown 이라 이전할 수 없다"를 명시해 오늘의 일반 TARGET_BUSY 메시지와 구분한다.
2. **`ExecutionJournal.begin_execution`(`:356-441`)** — 새 키워드 인자 `recovery_of: str | None = None` 추가(기본값 None — 기존 호출자 전부 하위 호환). `:434-441`의 `_reserve_destination_locked` 호출에 `transfer_from=recovery_of`를 전달. **1차 감사 D1 반영**: 반환값 `ExecutionResult`에 `transferred_from: str | None = None` 필드를 추가한다 — `_reserve_destination_locked`가 1번 항목의 이전 분기를 실제로 탔으면 원본 execution_id, 아니면 `None`. 새 API 왕복이나 새 조회는 필요 없다 — 같은 트랜잭션 안에서 이미 아는 값을 반환값에 실어 나르는 것뿐이다.
3. **`ApplyCoordinator.apply()`의 `begin_execution` 호출(`:926-935`)** — `recovery_of=recovery_of`를 추가로 전달한다(이 메서드는 이미 `recovery_of` 파라미터를 함수 앞부분에서 검증하고 있다, `:872-878` — 같은 지역 변수를 그대로 넘긴다). 반환된 `result.transferred_from`을 지역 변수로 보관해 5번 항목의 게이트-거부 분기에서 쓴다.
4. **`ExecutionJournal.restore_destination`(신규 메서드, `release_destination`(`:668-675`) 바로 아래에 추가)** — `release_destination`과 동형의 단일 UPDATE 문. 시그니처: `restore_destination(*, project_id, show_id, sequence_id, to_execution_id) -> None`. `release_destination`이 `status`를 `released`로 바꾸는 것과 달리, 이 메서드는 `status`를 `reserved`로 **유지**한 채 `reserved_by_execution_id`/`reserved_at`만 `to_execution_id`(원본 execution_id)로 되돌린다 — REQ-LDRELEASE-008 이 요구하는 유일한 신규 메서드다.
5. **`ApplyCoordinator.apply()`의 게이트 거부 분기(`:952-965`, 특히 `:961`)** — 1차 감사 D1 반영. 조건 분기 삽입:
   - `result.transferred_from`이 있으면(이전이 일어난 recovery 가 지금 거부됨) → `self._journal.restore_destination(project_id=..., show_id=..., sequence_id=..., to_execution_id=result.transferred_from)`(REQ-LDRELEASE-008).
   - 없으면(오늘과 동일, REQ-LDRELEASE-004) → 기존 `release_destination(...)` 호출 그대로.
   - `finalize_execution(result.execution_id, STATE_FAILED)` 호출은 두 분기 모두에서 오늘과 동일하게 유지된다 — 바뀌는 것은 destination 처리뿐이다.
6. **변경 없음(회귀 확인만)**: `execute_bundles`의 상태 우선순위 로직 전체.

새 추상화(별도 클래스, 새 테이블, 새 엔드포인트)는 만들지 않는다 — 기존 세 함수의 파라미터/반환값 확장 + 조건 분기 + 대칭 메서드 하나(`restore_destination`)로 닫는다.

## §D. 마일스톤

Tier S — 단일 마일스톤.

- **M1 — 예약 이전 로직 + 회귀 (TDD RED-GREEN-REFACTOR)**
  1. RED: `test_director_execution_journal.py`에 `TestDestinationReservation` 아래 새 케이스 추가 — `partial` 원본을 가리키는 `transfer_from`로 재예약 시 이전 성공(현재 코드에서는 TARGET_BUSY 로 실패해야 RED 성립), `unknown` 원본을 가리키는 `transfer_from`는 여전히 TARGET_BUSY, `transfer_from`가 현재 점유자와 다르면 여전히 TARGET_BUSY.
  1b. RED(1차 감사 D1 반영) — `test_director_apply_rejection.py`에 새 클래스(예: `TestDestinationRestoredAfterTransferThenRejection`) 추가: `partial` 원본 → recovery apply 가 REQ-LDRELEASE-001 이전으로 destination 을 넘겨받음 → 그 recovery 자체가 `FakeGate`를 `cleared=False`로 설정해 거부되게 함 → 오늘 코드(§C 5번 항목 구현 전)에서는 `release_destination`이 무조건 호출되므로 `destination_status(...).status == "released"`가 되어야 RED 가 성립한다(REQ-LDRELEASE-008 이 요구하는 "reserved, 원본으로 복원"과 반대 결과). 구현 후에는 `status == "reserved"`, `reserved_by_execution_id == <원본>`이 되어야 GREEN.
  1c. RED(1차 감사 D2 반영, characterization/regression pin — RED-first 아님) — `test_director_execution_failure.py::TestStatePriority`에 `test_partial_with_explicit_failed_recovery_required_stays_false` 추가: sender 를 `[STATE_ACKNOWLEDGED, STATE_FAILED]`(또는 동형)로 스크립트해 `state == STATE_PARTIAL`을 만들고 `recovery_required is False`를 단언한다. **주의**: 이 값은 오늘 코드에서 이미 `False`이므로 이 시험은 추가하자마자 곧바로 PASS 한다 — RED 단계가 없다. D2 채택("코드 변경 없음")에 따라 이 시험은 새 동작을 드라이브하는 것이 아니라 REQ-LDRELEASE-007 이 문서화하는 기존 계약을 고정하는 **회귀 핀**이다. spec.md/§3 REQ-LDRELEASE-007 의 판정 명령이 이 시험 이름을 정확히 가리키도록 갱신한다(1차 감사가 지적한 대로 `test_director_execution_failure.py:133`은 이 케이스를 검증하지 않았다 — 그 줄은 `test_failed_when_nothing_confirmed_and_no_unknown`(전부 `failed`)의 단언이다).
  2. GREEN: §C의 5개 지점(1~5번 항목) 구현 — `transfer_from`/`transferred_from` 배선 + `restore_destination` 신설 + `ApplyCoordinator.apply()`의 게이트-거부 분기 조건화. `uv run pytest server/tests/test_director_execution_journal.py server/tests/test_director_apply_rejection.py -q`로 1번·1b번 케이스 통과 확인.
  3. `ApplyCoordinator` 통합 테스트 추가 — `test_director_ops_lifecycle.py::TestRecoveryFlow`에 "recovery_of 가 원본과 같은 destination 을 다시 써서 성공"하는 케이스(기존 `test_recovery_apply_creates_a_separate_execution_linked_by_recovery_of`/`test_recovery_of_accepts_partial_source`는 다른 `sequence_id`를 쓰므로 그대로 통과해야 한다 — 회귀).
  4. 회귀 전체: `uv run pytest server/tests/test_director_execution_journal.py server/tests/test_director_ops_lifecycle.py server/tests/test_director_execution_failure.py server/tests/test_director_apply_rejection.py -q`.
  5. REFACTOR: 필요 시 `transfer_from` 분기의 에러 메시지 문구를 원본 TARGET_BUSY 메시지와 일관되게 다듬는다(로직 변경 없음).

## §E. 위험·안티패턴

- **위험 — 이전 조건이 너무 느슨해지면 create-only 원칙을 약화시킬 수 있다.** 완화: `existing["reserved_by_execution_id"] == transfer_from` 정확 일치 + `STATE_PARTIAL` 정확 일치라는 이중 조건으로 좁힌다(REQ-LDRELEASE-001/002/006).
- **위험 — `begin_execution`이 이미 다른 호출자(비-recovery apply)에서 쓰이므로 시그니처 확장이 회귀를 낼 수 있다.** 완화: `recovery_of: str | None = None` 기본값으로 기존 호출자는 전부 바이트 동일하게 동작 — REQ-LDRELEASE-005/006 이 그 회귀 부재를 인수 기준으로 고정한다. 반환값에 추가되는 `transferred_from` 필드도 기본값 `None` 이므로 기존 호출자가 반환값을 구조 분해/속성 접근하는 방식은 바뀌지 않는다.
- **위험(1차 감사 D1 반영) — 이전-후-게이트-거부 복합 실패를 놓치면 create-only 감사 가능성이 그 경로에서만 조용히 무너진다.** 완화: REQ-LDRELEASE-008 + `restore_destination` 신설로, 게이트 거부가 전이된 destination 을 완전 해제하지 않고 원본에게 되돌린다 — `test_director_apply_rejection.py`의 신규 케이스(§D M1 1b)가 회귀를 고정한다.
- **안티패턴 회피**: 새 release 엔드포인트/새 승인 타입을 추가하지 않는다(D1 (b) 기각). `recovery_required` 산출 로직을 건드리지 않는다(D2 (ii) 기각). `execute_bundles`의 상태 우선순위나 `ApplyCoordinator.apply()`의 재검사 순서를 재배열하지 않는다.
- **잔여 위험(문서화만으로 닫히지 않는 것)**: 이 SPEC 의 pytest 판정은 fake 콘솔/게이트로만 이전 로직을 확인한다 — LDSEND M5 032 시나리오를 이 변경 반영 후 실기로 재실행해 9903 재사용을 직접 관측하는 것은 이 SPEC 의 로컬 판정 범위 밖이다(spec.md §3 AC-LDRELEASE-005, 콘솔 필요).
