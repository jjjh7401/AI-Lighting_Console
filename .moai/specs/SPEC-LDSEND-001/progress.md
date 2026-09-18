# 진행 기록 — SPEC-LDSEND-001

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-09-18
- plan_revision: 3 (iter1 plan-audit `.moai/reports/plan-audit/SPEC-LDSEND-001-review-1.md`,
  FAIL 0.75 — D1-D8 반영, version 0.1.0 → 0.2.0. iter2 plan-audit
  `.moai/reports/plan-audit/SPEC-LDSEND-001-review-2.md`, FAIL 0.63(STOP
  신호, D1-D8 전부 회귀 확인됨) — D9-D12 반영, version 0.2.0 → 0.3.0)
- tier: M
- artifact_count: 4 (spec.md + plan.md + acceptance.md + progress.md)
- REQ/AC 수: 15/15 (Tier M 상한 16 이내 — iter2 개정으로 REQ-LDSEND-015/
  AC-LDSEND-015 신설, 14→15)
- depends_on 사전 검사: `SPEC-LDRECV-001` `status: completed`(로컬 checkout,
  `git log` 최근 5커밋에 3-phase close 확인) — 충족.
- 사람 확인 대기 항목: **전부 해소됨(2026-09-18)**. plan.md §2.0(가)
  `ExecutionResult.outcome` 필드 확장 — 채택(대안 B). §2.0(나) `SafetyGate.
  revoke_clearances()` + 전용 세션 격리(`run_director_apply()` 내부, iter2
  개정으로 바인딩 위치가 `post_apply()` 개별 구현에서 공유 함수로 이동) —
  채택. §2.0(다) 021 readback 질의 경로 — 코드 선례로 해소
  (`state_port.query_state("DataPool/Sequences/<N>")`). §2.0(라) AC-024
  실패 유발 명령 — M4a 실기 탐색으로 이연(후보 2개 목록화 완료, HALT 조건
  명시). §2.0(마, 신설) 관측 도구의 apply 경로 — 공유 함수 `run_director_
  apply()`(`server/director/execution.py`)로 `post_apply()` 의 apply
  흐름을 추출하고, 관측 도구도 그 함수만 호출해 실제 `GateBundleSender`/
  `execute_bundles()` 를 탄다; 도구는 자기 로컬 `DirectorStore`/
  `ApprovalRegistry.approve()`(공개 API)로 진짜 `ApprovalBinding` 을
  발급한다 — 채택.
- iter2 감사(D9-D12) 반영 요약: **D9(critical)** — 관측 도구가 `screen()`
  단독으로는 `GateBundleSender`/`execute_bundles()` 를 전혀 타지 않아 M5
  가 AC-LDPLUGIN-021/024/032 를 실제로 관측할 수 없었다 → §2.0-마 신설 +
  REQ-LDSEND-007/012/013 재정의 + REQ-LDSEND-015 신설로 해소. **D10** —
  관측 도구 자신의 세션 격리 미비 → 세션 바인딩을 공유 함수 내부로 옮겨
  구조적으로 해소. **D11** — dry-run 이 `build_console_stack()` 기본값
  (`attempt_session_backup=True`)으로 세션 시작 `SaveShow` 를 실제로 보낼
  수 있었다 → REQ-LDSEND-009 확장(dry-run 시 `attempt_session_backup=False`
  명시)으로 해소. **D12(minor)** — REQ-008 "run" 범위 모호 → "run = CLI
  1회 호출 = 시나리오 1개" 명문화로 해소.
- 개정 중 추가 발견(iter1): §1 규범표의 "콘솔 명령 안전 분류" 인용이
  낡았다 — `blacklist.yaml`(version 9)이 `Store Sequence`(v6)·`Store
  Cue`(v7)를 이미 블랙리스트에 넣었다. 인용을 정정하고 REQ-LDSEND-007/012
  를 그에 맞게 다시 썼다(iter2 에서 007/012 는 D9 로 추가로 재정의됨).

## §E.2 Run-phase Evidence

### M1 — 인터페이스 확정 (REQ-LDSEND-003/005/006/013/015)

**작업 위치 정정**: 이 M1 작업은 원래 배차서가 지정한 `.claude/worktrees/t420`
(브랜치 `WT-bundle-sender`, HEAD `ecaaa2e5`)가 아니라, 이 세션이 격리된
`.claude/worktrees/agent-a099cef1337871355` 에서 수행됐다 — 샌드박스가
`t420` 으로의 `cd` 를 거부했다(worktree-isolated agent 는 자신의 워크트리
밖에서 git 을 작동시킬 수 없다). `ecaaa2e5` 가 이 워크트리 HEAD(`f12d590e`)의
직계 후손임을 `git merge-base HEAD ecaaa2e5` 로 확인한 뒤, 같은 커밋
(`ecaaa2e5`)에서 새 로컬 브랜치 `agent-a099cef1337871355-ldsend-m1` 을 만들어
작업했다(`WT-bundle-sender` 자체는 다른 워크트리에 체크아웃돼 있어 여기서
체크아웃할 수 없다). 병합은 오케스트레이터가 이 브랜치를
`WT-bundle-sender`/`t420` 으로 반영해야 한다.

**§6 중단 조건 재확인(착수 전)**: `gate.py`(917·921·927·940·943·950행
`_execute_cleared`, 861·865·890·892·900행 `deploy_plugin_source`, 540-552행
ANCHOR, 553-657행 `execute_preapproved`), `execution.py`(219행 `GatePort`,
231행 `BundleSender`, 722행 `ApplyCoordinator`, 798행 `apply`, 974행
`execute_bundles`), `director_api.py`(404행 `post_apply`), `approvals.py`
행 번호는 재확인 결과 plan.md 인용과 **행 번호 드리프트 없이 일치**했다.
`blacklist.yaml` `version: 9` 도 plan.md 인용과 일치. 중단 조건 미해당 —
착수 진행.

**RED (E8, 명령 + 그대로의 출력)**:

```
$ uv run pytest server/tests/test_safety_gate.py::TestClearanceRevocation server/tests/test_safety_gate.py::TestExecutionResultOutcomeField -q -p no:cacheprovider
...
E       AttributeError: 'ExecutionResult' object has no attribute 'outcome'
...
FAILED server/tests/test_safety_gate.py::TestClearanceRevocation::test_revoke_clearances_empties_only_the_callers_own_session
FAILED server/tests/test_safety_gate.py::TestClearanceRevocation::test_revoke_clearances_does_not_touch_another_sessions_clearance
FAILED server/tests/test_safety_gate.py::TestExecutionResultOutcomeField::test_outcome_is_ok_on_a_confirmed_send
FAILED server/tests/test_safety_gate.py::TestExecutionResultOutcomeField::test_outcome_is_unconfirmed_on_an_unconfirmed_send
FAILED server/tests/test_safety_gate.py::TestExecutionResultOutcomeField::test_outcome_is_failed_on_an_explicit_console_failure
FAILED server/tests/test_safety_gate.py::TestExecutionResultOutcomeField::test_outcome_is_failed_when_not_cleared
6 failed in 0.78s
```

`test_run_director_apply.py` 는 구현(execution.py/director_api.py)을 먼저
작성해 버린 절차 오류를 바로잡기 위해, 두 파일의 diff 를 임시로 되돌린 뒤
(`git checkout -- server/director/execution.py server/director/director_api.py`,
diff 는 사전에 패치 파일로 저장) 시험을 다시 돌려 진짜 RED 를 얻고, 그
뒤 패치를 재적용(`git apply`)했다:

```
$ uv run pytest server/tests/test_run_director_apply.py -q -p no:cacheprovider
...
E   ImportError: cannot import name 'run_director_apply' from 'server.director.execution'
...
1 error in 0.41s
```

**GREEN — 구현**:
- `server/orchestrator/ports.py`: `ExecutionResult` 에 `outcome: str = "ok"` 필드 추가.
- `server/safety/gate.py`: `_execute_cleared()` 의 6곳(917·921·927·940·943·950)에
  `outcome=` 명시 채움(917/921/927/950 → `"failed"`, 940 → `"ok"`, 943 →
  `"unconfirmed"`). `deploy_plugin_source()` 의 5곳은 PRESERVE — 손대지 않음.
  신규 public 메서드 `revoke_clearances()` 추가(호출 세션 자신의 Counter만
  비움, `_clearances_lock` 재사용).
- `server/director/execution.py`: `GatePort` Protocol 에 `revoke_clearances`
  시그니처 추가. `ApplyCoordinator.revoke_clearances()` 순수 위임 메서드
  추가. 신규 공유 함수 `run_director_apply()` 추가 — `bind_session_key
  (new_session_key())` → `coordinator.apply(...)` → (sender 배선 & not
  replayed 일 때만) `execute_bundles(...)` → `finally` 에서
  `coordinator.revoke_clearances()` + `reset_session_key(token)`.
- `server/director/director_api.py`: `post_apply()` 본문을
  `run_director_apply(...)` 호출 + 반환 튜플을 `JSONResponse` 로 감싸는
  코드로 교체(얇은 adapter).
- `server/tests/test_director_ops_lifecycle.py`: `_SpyApplyCoordinator` 에
  no-op `revoke_clearances()` 추가(구조적 호환성 — `run_director_apply()` 가
  `finally` 에서 무조건 호출하므로 없으면 `AttributeError` 로 회귀).

**E1 AC PASS/FAIL 매트릭스 (M1 관련 5개 — 003·005·006·013·015)**:

| AC | 시험 | 결과 |
|---|---|---|
| AC-LDSEND-003 | `TestExecutionResultOutcomeField::*` (3), `TestUnconfirmedExecution`(기존) | PASS |
| AC-LDSEND-005 | `TestClearanceRevocation::test_revoke_clearances_empties_only_the_callers_own_session` | PASS |
| AC-LDSEND-006 | `TestClearanceRevocation::test_revoke_clearances_does_not_touch_another_sessions_clearance`, `test_run_director_apply.py::TestCrossSessionClearanceIsolationDuringRunDirectorApply::test_a_default_session_callers_clearance_survives_applys_own_revoke` | PASS |
| AC-LDSEND-013 | `test_run_director_apply.py::TestSessionBindingAroundApply::*`(2), `TestExceptionInsideExecuteBundlesStillClosesTheSession::*` | PASS |
| AC-LDSEND-015 | `test_director_ops_lifecycle.py`(기존, 재실행 회귀), `test_director_apply_rejection.py`(기존, 재실행 회귀), `test_run_director_apply.py::TestReplaySkipsExecuteBundles::*`, `TestGateRejectedRaisesBeforeExecuteBundles::*` | PASS |

**E2 명령 + 관측 출력 (전체 verbatim 은 아래 파일 참고)**:

```
$ uv run pytest server/tests/test_safety_gate.py server/tests/test_run_director_apply.py \
  server/tests/test_director_ops_lifecycle.py server/tests/test_director_apply_rejection.py \
  -q -p no:cacheprovider
........................................................................ [ 73%]
..........................                                               [100%]
98 passed, 1 warning in 1.48s
```

**E3 다섯 소비자 회귀** (§2.0-가 전제, D3 정정 — "넷"이 아니다):
```
$ uv run pytest server/tests/test_measurement_runner.py server/tests/test_web_session.py \
  server/tests/test_web_panel_execute.py server/tests/test_deploy_pipeline.py \
  -q -p no:cacheprovider
532 passed, 1 warning in 4.75s
```
`server/tests/test_orchestrator_tools.py` 는 plan.md 가 이미 "추정 이름"으로
표시한 대로 이 저장소에 **존재하지 않는다** — `server/orchestrator/tools.py`
(`:2436` 소비자)는 대신 아래 §E3-전체회귀 의 `uv run pytest -q` 최종 백스톱이
전이적으로 커버한다(`tools.py` 를 import 하는 시험 수십 개 포함).

**E5 lint**: `uv run ruff check server/orchestrator/ports.py server/safety/gate.py
server/director/execution.py server/director/director_api.py
server/tests/test_safety_gate.py server/tests/test_run_director_apply.py
server/tests/test_director_ops_lifecycle.py` → `All checks passed!`
(초회 `I001` import-sort 오류 1건을 수동으로 재정렬해 해소).

**전체 회귀 (baseline 대비)**:

```
$ uv run pytest -q -p no:cacheprovider     # 착수 전 baseline
13515 passed, 35 skipped, 1 warning in 221.83s

$ uv run pytest -q -p no:cacheprovider     # M1 구현 뒤(MX 태그 포함 최종)
13528 passed, 35 skipped, 1 warning in 181.83s
```

델타 +13 (신규 시험 6개 `test_safety_gate.py` + 7개
`test_run_director_apply.py`), skip 수 불변, 실패 0 — 회귀 없음.
전체 출력: `.moai/state/verify/agent-a099cef1337871355/{baseline-pytest.txt,m1-full.txt}`
(이 세션의 워크트리 상대 경로 — `t420` 쪽 경로가 아님, 위 작업 위치 정정 참고).

**경계 grep** (M2/M3 대상 파일(`server/director/sender.py`,
`server/tools/director_apply_observe.py`)은 M1 범위 밖이라 아직 존재하지
않는다 — 그 파일들을 대상으로 하는 OSC-import 경계 grep 은 M2/M3 에서
수행한다):
```
$ grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/execution.py server/safety/gate.py server/director/director_api.py
(매치 없음 — PASS)
```

**Gaps**: M2(실물 송신기)·M3(관측 도구 골격)·M4(시나리오 배선)·M4a(실기
탐색)·M5(실기 관측)는 이 M1 커밋의 범위가 아니다 — 배차서의 지시대로 M1
커밋 뒤 정지한다. `test_orchestrator_tools.py` 파일 부재로 인한 직접 재실행
생략(위 E3 설명). §2.0-가가 전제한 "다섯 소비자가 위치 기반으로 소비하지
않는다"는 grep + 직접 읽기로 재확인했으나(§6 재확인 절 참고), 전수 정적
분석 도구로 검증한 것은 아니다.

**Residual risk**: 이 M1 산출물은 `.claude/worktrees/agent-a099cef1337871355`
의 로컬 브랜치(`agent-a099cef1337871355-ldsend-m1`, `ecaaa2e5` 위)에만
존재한다 — `WT-bundle-sender`/`t420` 로 병합·반영되기 전까지는 원래 배차
대상 브랜치에 반영되지 않은 상태다.

#### M1 오케스트레이터 재측정 (2026-09-18, t420)

- 반영: `git merge --ff-only 7b4004a0` → `WT-bundle-sender` 에 fast-forward(부모가 `ecaaa2e5` 그대로). 위 Residual risk 는 해소됐다.
- **위 13528 수치는 커밋 전 작업 트리에서 잰 것이라 무효였다.** `test_overlap_preserve.py` 는 `<base>..HEAD` 커밋 diff 로 판정하므로 커밋 전에는 gate.py 변경을 못 본다. 커밋 뒤 `uv run pytest -q -p no:cacheprovider` → `3 failed, 13525 passed, 35 skipped` (`.moai/state/verify/ae8e2656/m1-full.txt`): `TestSafetyChokepointFileSet` 2건(gate.py 삭제 `74 == 69`) + `TestTouchedFilesPassLint::test_ruff_format_reports_no_change`(`test_run_director_apply.py` 서식).
- 수정 `75ed61c7`: 핀에 `_execute_cleared()` 옛 문면 5줄 추가, 69→74, ruff format.
- 재측정 @`75ed61c7`: `uv run pytest -q -p no:cacheprovider` → exit 0, `13528 passed, 35 skipped, 1 warning` (`.moai/state/verify/ae8e2656/m1-full-2.txt`).

### M2 — 실물 송신기 (REQ-LDSEND-001/002/003/004)

**작업 위치**: `.claude/worktrees/agent-a1b3c914ba0dc22fd` 가 격리된 별도
워크트리라, `d1d91e5e`(`WT-bundle-sender`, M1 완료 커밋) 위에 로컬 브랜치
`ldsend-001-m2` 를 새로 만들어 작업했다(`git switch -c ldsend-001-m2
d1d91e5e`) — `d1d91e5e` 가 이 워크트리에서 직접 reachable(`git cat-file -t`
확인)했으므로 별도 병합-베이스 확인 없이 그 커밋 위에 바로 분기했다. 병합은
오케스트레이터가 이 브랜치를 `WT-bundle-sender`/`t420` 으로 반영해야 한다
(M1 과 동일한 절차, §E.2 M1 Residual risk 참고).

**RED (E8, 명령 + 그대로의 출력)** — `server/director/sender.py` 작성 전:

```
$ uv run pytest server/tests/test_director_sender.py -q -p no:cacheprovider
==================================== ERRORS ====================================
____________ ERROR collecting server/tests/test_director_sender.py _____________
ImportError while importing test module '.../server/tests/test_director_sender.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
.../importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
server/tests/test_director_sender.py:21: in <module>
    from server.director.sender import GateBundleSender
E   ModuleNotFoundError: No module named 'server.director.sender'
=========================== short test summary info ============================
ERROR server/tests/test_director_sender.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.69s
```

**GREEN — 구현**:
- 신규 `server/director/sender.py`: `GateBundleSender`(`BundleSender`
  프로토콜 구현). 주입된 `execution_port.execute(command)`(공유
  `SafetyGate.execution_port`)로만 `bundle["commands"]` 를 순서대로 보내고,
  `result.outcome`(`"ok"`/`"failed"`/`"unconfirmed"`, 문자열 스니핑 아님)을
  직접 읽어 판정한다 — 전부 ok → `STATE_ACKNOWLEDGED`; 첫 명령부터 확인 없이
  명시적 실패 → `STATE_FAILED`; 어떤 명령이든 미확인 → `STATE_UNKNOWN`;
  확인된 명령 뒤 명시적 실패(부분 완료) → `STATE_UNKNOWN`; `execute()` 예외 →
  흡수해 `STATE_UNKNOWN`(예외가 `send()` 밖으로 전파되지 않음). `STATE_SENT`
  는 반환하지 않는다. `revoke_clearances()` 는 호출하지 않는다(회수는
  `run_director_apply()` 책임, M1 이 이미 배선).
- 신규 `server/tests/test_director_sender.py`: fake
  `CommandExecutionPort`(구조적 타이핑, 이름 import 없음)와 예외를 던지는
  fake 만 주입하는 10개 시험 — 콘솔/OSC 트래픽 없음.

**경계 가드 위반 발견 및 수정(post-commit 재측정에서 발견)**: 첫 GREEN 커밋
(`eb953842`)의 `sender.py` 가 `from server.orchestrator.ports import
CommandExecutionPort` 로 타입을 이름으로 import 했는데, 이것이
`server/tests/test_director_boundary.py::TestDirectorNeverTouchesTheConsole
::test_no_module_names_an_execution_port`(SPEC-LDSTORE-001 소유 경계
시험 — `server/director/*.py` 전체에서 `"CommandExecutionPort"`/
`"BundleGate"` 문자열을 금지)를 깨뜨렸다. 가드 시험은 손대지 않고,
`sender.py` 를 로컬 구조적 `Protocol`(`_ExecutionPort`, 이름 없이 같은
덕타이핑 계약)로 고쳐 해소했다(`41151c0d`) — 런타임 동작 변경 없음, 시험
10개 그대로 PASS.

**E1 AC PASS/FAIL 매트릭스 (M2 관련 4개 — 001·002·003·004)**:

| AC | 시험 | 결과 |
|---|---|---|
| AC-LDSEND-001 | `TestAllCommandsOk::test_commands_are_sent_only_through_the_injected_execution_port`; `grep -rnE "^\s*(from\|import)\s+server\.bridge" server/director/sender.py` → 매치 0 | PASS |
| AC-LDSEND-002 | `TestFirstCommandExplicitFailure::test_first_command_failed_with_none_confirmed_before_returns_failed`(3개 중 2·3번째 미전송, `port.calls == ["cmd-1"]`) | PASS |
| AC-LDSEND-003 | `TestAllCommandsOk`(1), `TestFirstCommandExplicitFailure`(1), `TestAnyUnconfirmedStopsAndReturnsUnknown`(1), `TestConfirmedThenFailedIsPartialAndUnknown`(1), `TestNeverReturnsStateSent`(1) — 판정 표 5 경로 전부 | PASS |
| AC-LDSEND-004 | `TestConsoleLinkExceptionIsAbsorbed::*`(2 — 첫 명령 예외·중간 명령 예외 둘 다) | PASS |

**E2 명령 + 관측 출력**:

```
$ uv run pytest server/tests/test_director_sender.py server/tests/test_director_boundary.py -q -p no:cacheprovider
...............                                                          [100%]
15 passed in 0.51s
```

**E5 lint**: `uv run ruff format server/director/sender.py
server/tests/test_director_sender.py` → `1 file left unchanged` /
`2 files left unchanged`(재측정 시). `uv run ruff check` 양쪽 →
`All checks passed!`.

**전체 회귀 (post-commit, `41151c0d`)**:

```
$ uv run pytest -q -p no:cacheprovider
13538 passed, 35 skipped, 1 warning in 183.30s (0:03:03)
```

exit=0. baseline(M1 뒤, `d1d91e5e`) `13528 passed, 35 skipped` 대비 델타
+10(`test_director_sender.py` 신규 10개), skip 수 불변, 실패 0 — 회귀 없음.
전체 출력: `.moai/state/verify/m2-full.txt`(첫 커밋 뒤, 경계 가드 FAIL 1건
관측 — `1 failed, 13537 passed`), `.moai/state/verify/m2-full-2.txt`(수정
커밋 뒤, exit=0, `13538 passed`).

**Gaps**: M3(관측 도구 골격)·M4(시나리오 배선)·M4a(실기 탐색)·M5(실기
관측)는 이 M2 커밋의 범위가 아니다 — 배차서의 지시대로 M2 커밋 뒤 정지한다.
AC-LDSEND-005/006/013/015(클리어런스 회수·세션 격리·공유 함수 추출)는 M1
범위이며 M2 의 새 코드는 그 계약을 변경하지 않는다(M2 는 `revoke_clearances`
를 호출하지 않는다는 사실만 명시적으로 시험했다).

**Residual risk**: 이 M2 산출물은 `.claude/worktrees/agent-a1b3c914ba0dc22fd`
의 로컬 브랜치(`ldsend-001-m2`, `d1d91e5e` 위)에만 존재한다 —
`WT-bundle-sender`/`t420` 으로 병합·반영되기 전까지는 원래 배차 대상
브랜치에 반영되지 않은 상태다. 경계 가드 위반이 post-commit 전체 회귀에서
처음 발견됐다는 점은, M2 범위 파일에 대한 사전 경계 시험 실행(`server/tests/
test_director_boundary.py` 단독 실행)이 커밋 전 검증 루틴에 아직 없다는
잔여 위험을 시사한다 — 이번엔 즉시 수정했지만, 후속 마일스톤(M3 이 `server/
tools/director_apply_observe.py` 신설 시)도 같은 경계 시험(있다면 해당
패키지의 경계 시험)을 커밋 전에 별도로 돌려보는 편이 안전하다.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F Phase 4 Mode Selection

- 입력: Tier M · 예상 파일 7~8개(ports.py·gate.py·execution.py·director_api.py EXTEND, sender.py·director_apply_observe.py 신규 + 시험 3개) · 도메인 2(safety·director) · Python 100% · 코딩 위주(병렬 이득 낮음)
- 평가: `direct` 아님(다파일) · `fanout` 아님(코딩 위주) · `sweep` 아님(기계적 일괄 변환 아님) · `serial` 선택
- Decision: serial
- 근거: 코딩 위주 작업은 순차 하위 에이전트가 기본값이다. M1→M2→M3→M4 는 앞 단계 인터페이스에 의존한다.

## §G Implementation Kickoff (2026-09-18)

- plan-audit: iter1 FAIL 0.75 → iter2 FAIL 0.63 → iter3 **PASS 0.86** (`.moai/reports/plan-audit/SPEC-LDSEND-001-review-3.md`). iter3 D13(문장 잔재)은 `3c6aa451`·`7804dc13` 으로 정정.
- 사람 결정(2026-09-18): ① `ExecutionResult.outcome` 필드 추가 ② apply 별 전용 세션 + `revoke_clearances()` — 바인딩은 `run_director_apply()` 안 ③ 도구는 `Delete` 를 보내지 않고 정리 명령만 출력 ④ 실패 유발 명령·readback 경로는 M4a 실기 탐색 후 HALT 해 사람 확인 ⑤ 착수 승인: **M1 부터 시작, M4a 앞에서 반드시 정지**.
- 상태: 착수 승인됨, 구현 미착수(M1 커밋 없음). 콘솔 쓰기(M4a·M5)는 보낼 명령을 보여 주고 다시 확인받은 뒤에만.
