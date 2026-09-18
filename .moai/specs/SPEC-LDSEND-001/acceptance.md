# 인수기준 — SPEC-LDSEND-001

[요구사항](spec.md) · [구현 계획](plan.md) · 선행: [SPEC-LDRECV-001](../SPEC-LDRECV-001/spec.md)

## 1. 판정 수단과 그 한계

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이
유일한 자동 판정 근거다.

**증거 규율**: 각 기준의 PASS 는 그 기준의 검증 명령을 **실제로 돌려서 본
출력**으로만 주장한다. 명령을 안 돌린 항목은 PASS 가 아니라 **Gap** 이다.

**콘솔 게이트 주의**: AC-LDSEND-010 은 로컬 pytest 로 닫을 수 없다 — onPC
실기 관측 기록이 별도 증거다. AC-LDSEND-011·014 는 **부분적으로만** 로컬로
닫힌다 — 011 은 도구의 출력 형태(로컬)와 사람이 그 출력을 실행한 뒤의 결과
(콘솔 필요)로 나뉘고, 014 는 백업 실패 처리 로직(로컬, fake backup manager)
과 실제 백업 통과 여부(콘솔 필요)로 나뉜다(§2 표의 분해 참고).

## 2. 기준 — REQ 와 1:1

| AC | REQ | 종류 | 기준 |
|---|---|---|---|
| AC-LDSEND-001 | 001 | S+D | **Given** `GateBundleSender` 모듈, **When** `grep -rnE "^\s*(from\|import)\s+server\.bridge" server/orchestrator/bundle_sender.py`, **Then** 매치 0. **Given** `send()` 호출, **When** 명령을 보냄, **Then** 그 호출이 오직 주입된 `gate.execution_port.execute()` 경로로만 관측된다(fake gate 의 호출 카운트로 확인). |
| AC-LDSEND-002 | 002 | D | **Given** 3개 명령을 담은 bundle, **When** 2번째 명령이 미확인(failed 또는 unconfirmed) 결과를 내는 fake 콘솔, **Then** 3번째 명령은 `gate.execution_port.execute()` 가 호출되지 않는다(mock 호출 카운트 2). |
| AC-LDSEND-003 | 003 | D | 아래 표의 각 조건을 fake gate/콘솔로 재현해 `send()` 반환값이 표와 일치하는지 확인한다(5개 시나리오 전부). |
| AC-LDSEND-004 | 004 | D | **Given** fake 콘솔 링크가 `execute()` 호출 시 예외를 던지도록 구성, **When** `send(bundle)` 호출, **Then** 예외가 `send()` 밖으로 전파되지 않고 반환값은 `STATE_UNKNOWN` 이다. |
| AC-LDSEND-005 | 005 | D | **Given** 3개 명령 중 1번째만 성공하고 나머지가 미확인이라 조기 중단된 bundle, **When** `post_apply()` 가 `send()`(→ `execute_bundles()`) 반환 직후 `revoke_clearances()` 를 호출하면, **Then** 그 호출은 정확히 1회이고(mock 카운트), 그 뒤 **같은** 전용 세션 키로 남은 두 명령을 `execution_port.execute()` 로 직접 불러도 거부된다(`ok=False`, "not cleared" 사유). |
| AC-LDSEND-006 | 006, 013 | S+D | **실제 `DEFAULT_SESSION_KEY` 공유 구성 재현(D2 정정 — 두 fabricated 키가 아니다).** **Given** `bind_session_key` 로 세션을 바인딩하지 **않은** fake 호출자(`server/measurement/runner.py` 흉내)가 `execute_preapproved()` 로 클리어런스를 발급, **When** 별도의 전용 세션에서 apply 가 `revoke_clearances()` 호출, **Then** 그 fake 호출자(`DEFAULT_SESSION_KEY`)의 클리어런스는 그대로 남아 실행 가능하다. **역방향**: **Given** apply 가 전용 세션에서 클리어런스 발급, **When** `DEFAULT_SESSION_KEY` 로 남은 다른 호출자가 `revoke_clearances()` 호출, **Then** apply 의 전용 세션 클리어런스는 지워지지 않는다. **예외 경로**: **Given** `execute_bundles()` 도중 예외 발생, **When** `post_apply()` 의 `finally` 가 실행되면, **Then** `reset_session_key()` 가 호출돼 다음 요청이 이 세션을 물려받지 않는다(mock 토큰 확인). |
| AC-LDSEND-007 | 007 | S+D | **Given** 관측 도구 모듈, **When** `grep -rnE "^\s*(from\|import)\s+server\.bridge" server/tools/director_apply_observe.py`, **Then** 매치가 있다면 그 import 는 `build_console_stack()` 을 거치는 것이 아니라 도구가 직접 `OscBridge`/새 소켓을 여는 것이므로 FAIL — 이 기준은 도구가 `server.safety.bootstrap.build_console_stack` 만 호출하는지를 코드 리뷰로 확인한다(단일 호출 지점). **추가(D9, D6 정정)**: `grep -nE "^\s*(from\|import)\s+server\.director\.director_api" server/tools/director_apply_observe.py` 는 매치 0 이어야 한다 — 그 파일은 `fastapi` 를 끌어오므로 순수 관측 하네스가 import 하면 안 된다. `grep -n "run_director_apply" server/tools/director_apply_observe.py` 는 매치 1개 이상이어야 한다 — apply 시나리오 실행은 오직 그 공유 함수를 통해서만 이뤄진다(§2.0-마 plan.md). |
| AC-LDSEND-008 | 008 | D | **Given** fake 콘솔이 대상 destination 이 이미 점유돼 있다고 응답, **When** 도구가 그 destination 에 쓰려고 시도, **Then** 진행을 거부하고 콘솔에 쓰기 명령을 보내지 않는다(fake 콘솔 호출 카운트로 확인). **Given** 대상이 비어 있다고 응답, **When** 같은 시도, **Then** 진행한다. **추가(D12)**: **Given** AC-024 시나리오가 같은 실행(run) 안에서 먼저 채운 destination, **When** 그 시나리오의 후속 bundle 이 같은 destination 에 다시 쓰려고 시도, **Then** 이 "처음 쓰기" 점유 확인 가드는 그 시도를 막지 않는다(그 destination 은 이미 이 run 이 스스로 채운 것이므로 "처음 쓰기"가 아니다 — §2.0-라 plan.md와 모순 없음을 확인). |
| AC-LDSEND-009 | 009 | S+D | **Given** `--execute` 없이 도구 실행, **When** 임의의 시나리오 인자 조합, **Then** fake 콘솔에 대한 실제 송신 호출이 0회이고 계획(명령 목록)만 표준출력에 나타난다. **추가(D11)**: **Given** dry-run 모드, **When** 도구가 `build_console_stack(...)` 을 호출, **Then** 그 호출의 `attempt_session_backup` 인자가 `False` 다(mock 호출 인자 확인) — 세션 시작 백업(`SaveShow`)을 포함해 콘솔로 나가는 송신이 정확히 0회임을 이 인자로 재확인한다. |
| AC-LDSEND-010 | 010 | H(콘솔 필요) | **Given** onPC 실기, **When** `--execute` 로 021/024/032 세 시나리오를 각각 구동, **Then** 각 시나리오의 결과가 `BundleSender` 반환값이 아니라 별도 readback 조회 결과로 보고된다 — 관측 기록에 readback 질의와 그 응답이 그대로 인용된다. |
| AC-LDSEND-011 | 011 | S+D(출력 형태) / H(사람 실행 뒤 결과, 콘솔 필요) | **로컬(S+D)**: **Given** `--execute` 실행이 끝난 직후, **When** cleanup 단계 실행, **Then** 도구는 `Delete Sequence <N>` 형태의 명령 문자열만 표준출력에 출력하고 fake 콘솔에 대한 송신 호출은 0회다(mock 카운트). **콘솔 필요(H)**: 사람이 그 출력된 명령을 직접 콘솔에 실행한 뒤, 관측 기록에 cleanup 전/후 콘솔 상태(destination 점유 여부)가 각각 기록되고 후가 "비어 있음"이다. |
| AC-LDSEND-012 | 012 | S+D | **로컬 승인 발급 경로(D9 개정)**: **Given** 도구가 시나리오 구동을 위해 만든 `ApprovalBinding`(로컬 `DirectorStore`+`ApprovalRegistry.approve()` 로 발급, §2.0-마 plan.md), **When** 그 `ApprovalBinding.principal_id` 를 조회, **Then** 고정된 구분 문자열 `ldsend-observe-harness` 를 포함하고, `grep -n "director_apply_observe" server/web/serve.py` 는 매치 0 이다 — 도구의 로컬 `DirectorStore`/`ApprovalRegistry` 인스턴스는 운영 조립(`server/web/serve.py`)의 어느 전역 인스턴스와도 동일 객체가 아니다(mock/id 비교로 확인). **Given** cleanup 단계, **When** 실행되면, **Then** 어떤 `ApprovalBinding` 도 생성되지 않는다(cleanup 은 실행하지 않으므로, REQ-LDSEND-011) — mock `ApprovalRegistry.approve` 호출 카운트 0. |
| AC-LDSEND-013 | 013 | D | **Given** `run_director_apply()` 처리 중(호출자가 `post_apply()`(HTTP)이든 관측 도구든), **When** `execute_preapproved()` 호출 시점부터 `execute_bundles()` 반환·`revoke_clearances()` 호출 직후까지, **Then** `bind_session_key`/`reset_session_key` 가 정확히 한 쌍 호출되고(mock 카운트), 그 사이 `current_session_key()` 가 매 단계 동일한 전용 키를 반환한다(AC-LDSEND-006 의 격리 시나리오가 이 배선 위에서 성립함을 재확인). **추가(D10)**: 관측 도구가 `run_director_apply()` 를 호출하는 경로에서도 이 시나리오를 재현한다 — 도구가 별도 세션 바인딩 코드를 갖고 있지 않아도(§2.0-마) 전용 세션을 얻는지 확인한다. |
| AC-LDSEND-014 | 014 | D(로직) / H(실제 통과 여부, 콘솔 필요) | **로컬(D)**: **Given** fake `BackupManager`(성공/실패 두 경로), **When** held(블랙리스트) 시나리오 명령을 실행, **Then** 실패 시 그 사실이 readback 판정과 별도 필드/로그로 기록된다(readback 결과를 덮어쓰지 않음, mock 검증). **콘솔 필요(H)**: onPC 실기에서 시나리오 실행 시 백업 선행조건이 실제로 통과했는지 관측 기록에 인용된다. |
| AC-LDSEND-015 | 015 | S+D | **행동 보존(회귀)**: **Given** 기존 LDRECV apply route 시험(`test_director_ops_lifecycle.py`·`test_director_apply_rejection.py`), **When** `post_apply()` 본문이 `run_director_apply()` 호출로 교체된 뒤 그 시험들을 재실행, **Then** 응답 상태·본문·journal 기록이 추출 전과 바이트 동일하다(회귀 없음). **단위(신규)**: **Given** fake `ApplyCoordinator`/`ExecutionJournal`/`BundleSender`, **When** `run_director_apply()` 를 직접 호출, **Then** replay 경로(`result.replayed=True`)에서는 `execute_bundles()` 가 호출되지 않고, gate-rejected 경로에서는 `execute_bundles()` 호출 전에 함수가 반환되며, 두 경로 모두 세션 바인딩/회수(REQ-013)가 `finally` 에서 정확히 1회 일어난다(mock 카운트). |

## 3. 기준별 검증 명령

### AC-LDSEND-001~006, 013, 015 — 송신기·클리어런스·세션 격리·공유 함수

```bash
uv run pytest server/tests/test_bundle_sender.py -q
uv run pytest server/tests/test_safety_gate.py -q
uv run pytest server/tests/test_run_director_apply.py -q   # 013, 015의 공유 함수 자체
uv run pytest server/tests/test_director_ops_lifecycle.py server/tests/test_director_apply_rejection.py -q   # 015 행동 보존(회귀)
```

**AC-LDSEND-003 판정 표(재확인 — plan.md §4 와 동일)**:

| 조건 | 기대 반환 |
|---|---|
| 모든 명령 확인됨 | `STATE_ACKNOWLEDGED` |
| 첫 명령부터 명시적 실패, 그 전 확인 없음 | `STATE_FAILED` |
| 어떤 명령이든 미확인(timeout) | `STATE_UNKNOWN` |
| 앞서 확인된 명령 이후 명시적 실패(부분 완료) | `STATE_UNKNOWN` |
| 콘솔 링크 예외 | `STATE_UNKNOWN` |

### AC-LDSEND-007~009, 014(로직 절반) — 관측 도구 골격

```bash
uv run pytest server/tests/test_director_apply_observe.py -q
grep -n "build_console_stack" server/tools/director_apply_observe.py
grep -nE "^\s*(from|import)\s+server\.director\.director_api" server/tools/director_apply_observe.py \
  && echo "FAIL: director_api(fastapi 의존) import" || echo "PASS: director_api 미참조(D9)"
grep -n "run_director_apply" server/tools/director_apply_observe.py || echo "FAIL: 공유 apply 경로 미사용"
```

**PASS 조건**: `build_console_stack` 호출이 정확히 1곳(또는 시나리오별로
여러 곳이더라도 전부 그 함수를 통해서만)이고, 도구 자신이 `OscBridge` 를
직접 인스턴스화하는 코드가 없으며, `server.director.director_api` 를
import 하지 않고(D9), `run_director_apply` 호출이 1회 이상이다.

### AC-LDSEND-010, 011(콘솔 절반), 014(콘솔 절반) — 콘솔 필요 (로컬로 닫히지 않는 부분)

수동 절차 — `progress.md` §M5(run-phase)에 다음을 기록한다:

1. `--execute` 로 021 시나리오 구동 → readback 질의 명령·응답 verbatim 인용
   (§2.0-다 plan.md 가 정한 경로 사용, 존재/부재 응답 모양도 이때 확정).
2. `--execute` 로 024 시나리오 구동(M4a 가 확정한 실패 유발 명령 사용) →
   후속 bundle 이 실기에서도 안 갔는지 readback 으로 확인한 결과 verbatim
   인용.
3. `--execute` 로 032 recovery 시나리오 구동 → recovery apply 의 readback
   결과 verbatim 인용.
4. 각 시나리오 뒤 도구가 출력한 `Delete Sequence <N>` 명령을 **사람이
   직접** 콘솔에 실행 → cleanup 전/후 destination 점유 상태 인용.
5. 각 시나리오 실행 시 백업 선행조건(`before_risky_execution()`) 통과
   여부를 관측 기록에 인용(REQ-LDSEND-014).

**주의**: 이 다섯은 이 문서가 go/no-go 를 내리지 않는다 — 관측했다는 사실과
그 결과를 정직하게 기록하는 것이 이 SPEC 의 완결 조건이다(spec.md §1.1).

### AC-LDSEND-012 — labelling 경계

```bash
grep -n "director_apply_observe" server/web/serve.py || echo "PASS: not wired into serve.py"
grep -n "ldsend-observe" server/tools/director_apply_observe.py
```

### 경계 기준 (공통)

```bash
# 이 SPEC 이 만드는 코드는 OSC 를 직접 만지지 않는다
grep -rnE "^\s*(from|import)\s+server\.bridge" server/orchestrator/bundle_sender.py \
  server/tools/director_apply_observe.py ; test $? -ne 0 && echo "PASS: no direct OSC import"

# ExecutionResult 소비자 다섯(D3 정정 — "넷"이 아니다)의 회귀 없음(§2.0-가 전제 검증)
uv run pytest server/tests/test_measurement_runner.py server/tests/test_web_session.py \
  server/tests/test_web_panel_execute.py server/tests/test_deploy_pipeline.py \
  server/tests/test_orchestrator_tools.py -q

# 회귀 (§2.0-가 "다섯 소비자" 전제의 최종 백스톱)
uv run pytest -q
```

**양성 대조**: grep 자체가 동작하는지 확인한다 — `grep -rn "def " server/orchestrator/bundle_sender.py`
가 매치를 내는지 같은 회차에서 본다.

## 4. go / no-go

**go 조건 (전부 충족)**:
- AC-LDSEND-001~009, 012, 013, 015 — 로컬 pytest 로 PASS, 검증 명령의 실제
  출력이 인용되어 있다.
- AC-LDSEND-011·014 의 **로컬 절반**(출력 형태·백업 실패 처리 로직) —
  로컬 pytest 로 PASS.
- 경계 기준 grep 이 기대대로 0 또는 매치이고 양성 대조가 성립한다.
- `uv run pytest` 전체 실패 0(회귀 없음) — 기존 LDRECV apply route 시험
  포함(AC-LDSEND-015 행동 보존).
- §2.0(plan.md)의 다섯 인터페이스 결정(가·나·다·라·마)에 대한 사람 확인
  기록이 있다 — 완료됨(2026-09-18).
- AC-LDSEND-010, 011·014 의 **콘솔 절반**은 관측 기록이 존재한다 —
  PASS/FAIL 이 아니라 **관측 완료 여부**로 판정한다(콘솔 필요 항목).

**콘솔 필요 항목(AC-010, AC-011·014 의 콘솔 절반)은 이 SPEC 만으로
go/no-go 를 내지 않는다.** 그 최종 판정은 `SPEC-LDCERT-001`(§1.1 각주
spec.md, 미작성)의 몫이다.

**no-go**:
- AC 중 하나라도 검증 명령 출력 없이 PASS 로 표시된 경우.
- `revoke_clearances()`(또는 동등 메서드)가 다른 세션의 클리어런스에
  영향을 주는 것이 발견된 경우 — M6c-1 세션 격리 불변식 위반, 또는
  `run_director_apply()` 가 전용 세션을 바인딩하지 않고 `DEFAULT_SESSION_KEY`
  를 그대로 쓰는 것이 발견된 경우(D2/AC-LDSEND-013).
- `ExecutionResult` 확장이 §2.0-가가 전제한 **다섯** 소비자(D3 정정 —
  "넷"이 아니다) 중 하나라도 깨뜨린 경우.
- 관측 도구가 `run_director_apply()` 를 거치지 않고 `execute_bundles()`/
  `GateBundleSender` 를 우회하는 별도 경로로 시나리오를 실행하는 것이
  발견된 경우(D9 — M5 의 관측이 이 SPEC 의 목적을 달성하지 못한다).
- 관측 도구가 만드는 `ApprovalBinding` 이 `server/web/serve.py` 운영
  조립의 실제 `DirectorStore`/`ApprovalRegistry` 인스턴스에 등록되는 것이
  발견된 경우(D9/AC-LDSEND-012).
- `post_apply()` 추출(REQ-LDSEND-015) 뒤 기존 LDRECV apply route 시험의
  응답 상태·본문·journal 기록이 추출 전과 달라진 경우(행동 보존 위반).
- dry-run 모드에서 `build_console_stack()` 이 `attempt_session_backup=True`
  로 호출돼 세션 시작 백업이 실제로 나가는 것이 발견된 경우(D11).
- cleanup 단계가 콘솔에 실제로 명령을 보내는 것이 발견된 경우(REQ-011 —
  출력만 해야 한다).
- 회귀 실패가 하나라도 있는 경우.

## 5. 이 SPEC 이 판정하지 않는 것

- **연출 품질을 판정하지 않는다.** 이 층은 판단을 하지 않는다.
- **first-release go/no-go 를 판정하지 않는다.** `SPEC-LDCERT-001`(§1.1
  각주 spec.md, 미작성)의 몫이다.
- **HTTP 라우팅·자격 발급을 판정하지 않는다.** 큐 카드 t421 소관이다.
- **operator 개입 감지(`InterferenceDetector`)의 실물 구현을 판정하지
  않는다.** 이 SPEC 은 그 프로토콜을 구현하지 않는다(§4 spec.md 비목표).

## 6. 미검증 (Gaps — 작성 시점)

- **기준선 숫자 미확정.** 착수 전 `uv run pytest -q` 를 재실행해야 한다.
- AC-024 관측 시나리오의 "안전한 실패 유발 명령"은 두 후보로 좁혀졌다
  (plan.md §2.0-라) — M4a 에서 실기로 확정한다. 더 이상 완전 미지수가
  아니다.
- 021 승격부의 readback 질의 경로는 코드로 확정됐다(plan.md §2.0-다) —
  남은 것은 존재/부재 응답 모양뿐이고 M5 한 항목으로 축소됐다.
- `server/orchestrator/ports.py` 확장(§2.0-가)은 채택이 확정됐다
  (plan.md §2.0-가, 2026-09-18) — 대안 A 로 되돌아갈 가능성은 §5 plan.md
  중단 조건("읽기 전용 소비자" 전제가 반증되는 경우)에만 남아 있다.
- REQ-LDSEND-014 의 백업 실패 시 후속 절차(중단 vs 경고-후-계속)가 M4
  착수 시 코드로 결정된다 — 잠정 기본값은 "중단+기록"이다(plan.md §7).
- **`ApprovalRegistry.approve()` 를 실제로 호출하는 관측 도구 코드 규모는
  재지 않았다(plan.md §7 — iter2 D9 신규 gap).** 공개 API 라 호출은
  가능하지만, `ValidationRef`/`ContextRef` 구성 + `store.submit()`
  헬퍼의 정확한 형태는 M3 착수 시 확정한다.
- 세션 바인딩은 `run_director_apply()` 안에 둔다(REQ-LDSEND-013/015). 그
  함수 안에서의 정확한 위치(`ApplyCoordinator.apply()` 호출 직전부터
  `revoke_clearances()` 이후 `finally` 까지)는 추출 착수 시 다시 읽어
  확정한다 — credential 검증은 `post_apply()` adapter 에 남는다.
