# 진행 기록 — SPEC-LDRELEASE-001

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-09-19
- tier: S
- artifact_count: 3 (spec.md + plan.md + progress.md — 진짜 Tier S 아티팩트셋.
  `acceptance.md`는 1차 plan-audit D3 지적 반영으로 삭제했다 — AC 는 spec.md §3 에
  REQ 와 1:1 인라인이다)
- REQ/AC 수: 8/8 (Tier S 상한 8 — 1차 감사 D1 반영으로 REQ-LDRELEASE-008 신설,
  정확히 상한)
- depends_on 사전 검사: `SPEC-LDSEND-001` `status: completed` — 충족.
- 1차 plan-audit(`.moai/reports/plan-audit/SPEC-LDRELEASE-001-review-1.md`, 반복
  1/3, verdict FAIL, 0.667) 반영 완료 — 2026-09-19 개정(spec.md HISTORY 참고):
  - D1(critical, blocking) — 이전-후-게이트-거부 복합 실패 미명세 → REQ-LDRELEASE-008
    신설 + plan.md §B D1 보완 + §C 신규 `restore_destination` 메서드 설계 + §D M1
    RED 케이스(1b) 추가.
  - D2(critical, blocking) — REQ-007/AC-007 의 `test_director_execution_failure.py:133`
    인용이 실제로는 `partial`이 아니라 전부-`failed` 케이스의 단언이었다 → 잘못된
    인용 제거, plan.md §D M1 에 신규 characterization 회귀
    (`test_partial_with_explicit_failed_recovery_required_stays_false`, RED-first
    아님, D2 "코드 변경 없음" 유지) 계획 추가, spec.md REQ-007/AC-007 판정 명령을
    그 신규 시험 이름으로 정정.
  - D3(major, blocking) — `tier: S` 인데 acceptance.md 를 별도로 둔 아티팩트셋
    불일치 → acceptance.md 삭제, AC 전부 spec.md §3 에 REQ 와 1:1 인라인으로
    이동해 진짜 Tier S 로 정렬.
  - D4(minor, optional) — "CI 가 저장소 전체가 죽어있다"는 근거 없는 승계 주장 →
    2026-09-19 `gh run list --branch main --limit 3` 실측(런 35433334782,
    `completed`/`success`, 2026-09-19T08:56:16Z)으로 대체.
  - D5(minor, optional) — REQ-005/006 인용 범위가 실제 분기 본문(create-only
    INSERT 분기, TARGET_BUSY raise 본문)을 못 덮음 → REQ-005 `634-659`,
    REQ-006 `640-651`로 확장.
  - D6(minor, optional) — REQ-003 이 조건부-부정 혼성 문형이라 정형 GEARS
    템플릿에서 벗어남 → 평서형 Ubiquitous 문장으로 재작성.
- 사람 확인 대기 항목: 없음 — D1(release-on-recovery, partial 원본만·unknown 원본
  거부 + 이전-후-거부 복원)과 D2(`recovery_required` False 유지·문서화만)를
  spec.md/plan.md 에 근거와 함께 확정했다. `[NEEDS CLARIFICATION]` 마커 없음.
- 근거: 큐 카드 t422, `.moai/specs/SPEC-LDSEND-001/progress.md` §M5(2026-09-18) 실기 관측
  기록, 1차 plan-audit 리포트(위).

## §F Phase 4 Mode Selection

- 입력: tier S · 파일 1개(`server/director/execution.py`) + 테스트 3개 · 도메인 1(director) · Python · 코딩 중심(병렬 이득 낮음)
- 평가: direct — 아님(의미 변경 있음) · fanout — 아님(단일 도메인) · sweep — 아님(기계적 대량 변환 아님) · serial — 선택
- Decision: serial
- 근거: 한 파일 안의 조건 분기·메서드 추가라 순차 단일 에이전트(manager-develop, TDD)가 가장 단순하다. Plan Audit Gate 는 2회차 PASS 1.0(≥0.75)·산출물 해시 변경 없음(커밋 3659eafb 이후 수정 없음)으로 재실행 생략. Implementation Kickoff Approval 2026-09-19 승인(자율 진행).

## §E.2 Run-phase Evidence

TDD RED-GREEN-REFACTOR, `cycle_type=tdd` — 단일 파일(`server/director/execution.py`)
변경, plan.md §C 항목1~5 + §D M1 그대로.

### RED — 항목1 (transfer 로직, `test_director_execution_journal.py`)

`recovery_of`/`transferred_from` 이 아직 없어 `TypeError`/`AttributeError` 로
실패(§D M1-1 이 예상한 그대로). 4개 신규 테스트(`TestDestinationTransferOnRecovery`)
가 이 단계에서 전부 FAIL:

```
$ uv run pytest -q server/tests/test_director_execution_journal.py -k TestDestinationTransferOnRecovery
...
E           TypeError: ExecutionJournal.begin_execution() got an unexpected keyword argument 'recovery_of'
...
E       AttributeError: 'ExecutionResult' object has no attribute 'transferred_from'
4 failed, 24 deselected in 0.43s
```
(verbatim: `.moai/state/verify/t422/red1-journal.txt`)

### RED — 항목1b (게이트-거부-후-복원, `test_director_apply_rejection.py`)

항목1~3 GREEN 이후, `restore_destination`/조건 분기(항목4~5)가 아직 없어
무조건 `release_destination` 이 걸린다 — plan.md §D M1-1b 가 예상한 그대로
`released` != `reserved` 로 FAIL:

```
$ uv run pytest -q server/tests/test_director_apply_rejection.py -k TestDestinationRestoredAfterTransferThenRejection
...
E       AssertionError: 전이된 destination 은 완전 해제가 아니라 원본에게 복원돼야 한다(REQ-LDRELEASE-008)
E       assert 'released' == 'reserved'
1 failed, 19 deselected in 0.41s
```
(verbatim: `.moai/state/verify/t422/red2-apply-rejection.txt`)

### RED — 항목1c (`recovery_required` characterization pin)

명시대로 RED-first 가 아니다 — 오늘 코드에서 이미 `False` 이므로 추가하자마자
PASS 한다(D2 "코드 변경 없음"). §D M1-1c 의 코멘트 그대로.

### GREEN — plan.md §C 항목1~5 구현

1. `_reserve_destination_locked` — `transfer_from` 파라미터 추가, 점유자가
   `transfer_from` 과 정확히 같고 그 상태가 `partial` 이면 원자적 이전, 그
   외(특히 `unknown`)면 구분되는 메시지로 TARGET_BUSY(REQ-001/002/006).
2. `begin_execution` — `recovery_of` kwarg(기본값 None) 추가, `_reserve_
   destination_locked` 에 `transfer_from=recovery_of` 전달; `ExecutionResult`
   에 `transferred_from: str | None = None` 필드 추가.
3. `ApplyCoordinator.apply()` — `begin_execution` 호출에 `recovery_of=
   recovery_of` 전달.
4. `ExecutionJournal.restore_destination(*, project_id, show_id, sequence_id,
   to_execution_id)` 신설 — `release_destination` 과 동형이나 `status` 를
   `reserved` 로 유지한다.
5. `ApplyCoordinator.apply()` 게이트-거부 분기 — `result.transferred_from`
   있으면 `restore_destination`, 없으면(오늘과 동일) `release_destination`.

REFACTOR: `_reserve_destination_locked` 의 이전 분기에 `@MX:NOTE`(한국어,
`code_comments: ko`) 추가 — REQ-001/002/008 근거 설명. 로직 변경 없음.

추가 통합 시험(plan.md §D M1 항목3, AC-LDRELEASE-005): `test_recovery_via_
run_director_apply_reuses_9903_and_preserves_the_original_row` —
`run_director_apply()` 경로 + fake `BundleSender` 로 9903 재사용·원본 행
바이트 동일을 끝까지 확인(`FakeGate.revoke_clearances()` 부재로 1회 재-GREEN:
테스트 전용 fake 에 no-op 메서드 추가, 로직 변경 없음).

### AC 판정 매트릭스

| AC | 상태 | 판정 명령 | 관측 |
|----|------|-----------|------|
| AC-LDRELEASE-001 | PASS | `uv run pytest server/tests/test_director_execution_journal.py::TestDestinationTransferOnRecovery::test_transfer_from_partial_original_succeeds_and_moves_reservation -q` | `1 passed` — `transferred_from == 원본`, `reserved_by_execution_id == recovery` |
| AC-LDRELEASE-002 | PASS(회귀) | `uv run pytest "server/tests/test_director_apply_rejection.py::TestDestinationReleasedOnPreSendRejection::test_gate_rejected_apply_releases_its_destination_reservation" -q` | `1 passed` — 전이 없는 게이트 거부는 오늘과 동일하게 `released` |
| AC-LDRELEASE-003 | PASS | `... ::test_transfer_from_a_different_execution_than_the_occupant_is_target_busy -q` | `1 passed` — `TARGET_BUSY`, 점유자 불변 |
| AC-LDRELEASE-004 | PASS | `... ::test_transfer_from_unknown_original_is_still_target_busy -q` | `1 passed` — `TARGET_BUSY`(unknown 원본), 점유자 불변 |
| AC-LDRELEASE-005 | PASS | `uv run pytest "server/tests/test_director_ops_lifecycle.py::TestRecoveryFlow::test_recovery_via_run_director_apply_reuses_9903_and_preserves_the_original_row" -q` | `1 passed` — 9903 재사용·`sent`·원본 행 전체 컬럼 바이트 동일 |
| AC-LDRELEASE-006 | PASS(신규+회귀) | 신규 `test_no_recovery_of_still_create_only_on_reserved_slot` + 기존 `TestRecoveryFlow::test_recovery_of_accepts_partial_source`(다른 destination) | 둘 다 `1 passed` |
| AC-LDRELEASE-007 | PASS(회귀 핀, RED-first 아님) | `uv run pytest "server/tests/test_director_execution_failure.py::TestStatePriority::test_partial_with_explicit_failed_recovery_required_stays_false" -q` | `1 passed` — `recovery_required is False` |
| AC-LDRELEASE-008 | PASS | `uv run pytest "server/tests/test_director_apply_rejection.py::TestDestinationRestoredAfterTransferThenRejection::test_gate_rejection_after_transfer_restores_destination_to_the_original" -q` | `1 passed` — `status=="reserved"`, `reserved_by_execution_id`=원본 |

전체 9개 판정 명령 통합 실행 결과: `9 passed, 1 warning in 0.51s`
(`.moai/state/verify/t422/ac-matrix.txt`).

### 불변식 보존 (plan.md §A PRESERVE)

- `ApplyCoordinator.apply()` 재검사 순서(승인 신선도→LiveLock→destination
  예약→execute_preapproved→execute_bundles) — 변경 없음, 회귀 전부 PASS.
- `record_recovery_link` 원본 행 불변 불변식 — `test_recovery_apply_creates_
  a_separate_execution_linked_by_recovery_of`(기존) + 신규
  `test_recovery_via_run_director_apply_reuses_9903_and_preserves_the_
  original_row`(전체 컬럼 바이트 동일 확인) 둘 다 PASS.
- `execute_bundles()` 상태 우선순위 — 코드 변경 없음, 신규 pin 테스트로 고정.
- 전이 없는 apply 의 `release_destination` 즉시 해제(REQ-004) — 회귀 PASS.

### 타겟 판정 (targeted) 최종

```
$ uv run pytest -q server/tests/test_director_execution_journal.py server/tests/test_director_ops_lifecycle.py server/tests/test_director_execution_failure.py server/tests/test_director_apply_rejection.py
........................................................................ [ 98%]
.                                                                        [100%]
73 passed, 1 warning in 1.18s
```
(baseline HEAD 3659eafb: 65 passed → +8 신규/확장 테스트 = 73)

### ruff

```
$ uv run ruff check server/director/execution.py server/tests/test_director_apply_rejection.py server/tests/test_director_execution_journal.py server/tests/test_director_ops_lifecycle.py server/tests/test_director_execution_failure.py
All checks passed!
$ uv run ruff format --check <위 5개 파일>
5 files already formatted
```

## §E.3 Run-phase Audit-Ready Signal

- run_status: audit-ready
- run_complete_at: 2026-09-19
- run_commit_sha: f72b442b (M1 커밋 — 자기 SHA 는 그 커밋 안에서 알 수 없으므로
  placeholder 로 시작했다가 이 후속 커밋에서 backfill 했다, SHA 필드 backfill
  예외 — spec.md/plan.md 본문은 건드리지 않는다)
- ac_pass_count: 8/8 (AC-LDRELEASE-001~008 전부 PASS)
- ac_fail_count: 0
- preserve_list_post_run_count: 4/4 (§A PRESERVE 4항목 전부 회귀 확인)
- l44_pre_commit_fetch: 해당 없음(main-direct Route A, PR 없음)
- l44_post_push_fetch: 해당 없음(main-direct Route A, PR 없음)
- new_warnings_or_lints_introduced: 0 (`ruff check`/`ruff format --check` 둘 다 clean)
- cross_platform_build.python: N/A — Python 프로젝트, `GOOS`/`GOARCH` 빌드
  태그 대상 아님(server/director 는 순수 Python)
- total_run_phase_files: 6 (`server/director/execution.py` + 5개 테스트 파일:
  `test_director_execution_journal.py`, `test_director_ops_lifecycle.py`,
  `test_director_execution_failure.py`, `test_director_apply_rejection.py`,
  `.moai/specs/SPEC-LDRELEASE-001/{spec.md,progress.md}`)
- m1_to_mN_commit_strategy: 단일 마일스톤(M1) — 단일 커밋으로 RED-GREEN-REFACTOR
  전체를 담는다(Tier S, 최소 delegation)
- full_regression: `uv run pytest -q -p no:cacheprovider` → **13619 passed, 35
  skipped, exit 0** (`.moai/state/verify/t422/pytest-run-final.txt`; baseline
  HEAD 3659eafb: 13611 passed, 35 skipped → +8, 정확히 신규 테스트 8개와
  일치 — targeted 스위트 기준으로도 65→73, +8)

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
