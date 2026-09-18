# 인수기준 — SPEC-LDSEND-001

[요구사항](spec.md) · [구현 계획](plan.md) · 선행: [SPEC-LDRECV-001](../SPEC-LDRECV-001/spec.md)

## 1. 판정 수단과 그 한계

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이
유일한 자동 판정 근거다.

**증거 규율**: 각 기준의 PASS 는 그 기준의 검증 명령을 **실제로 돌려서 본
출력**으로만 주장한다. 명령을 안 돌린 항목은 PASS 가 아니라 **Gap** 이다.

**콘솔 게이트 주의**: AC-LDSEND-010·011 은 로컬 pytest 로 닫을 수 없다 —
onPC 실기 관측 기록이 별도 증거다.

## 2. 기준 — REQ 와 1:1

| AC | REQ | 종류 | 기준 |
|---|---|---|---|
| AC-LDSEND-001 | 001 | S+D | **Given** `GateBundleSender` 모듈, **When** `grep -rnE "^\s*(from\|import)\s+server\.bridge" server/director/sender.py`, **Then** 매치 0. **Given** `send()` 호출, **When** 명령을 보냄, **Then** 그 호출이 오직 주입된 `gate.execution_port.execute()` 경로로만 관측된다(fake gate 의 호출 카운트로 확인). |
| AC-LDSEND-002 | 002 | D | **Given** 3개 명령을 담은 bundle, **When** 2번째 명령이 미확인(failed 또는 unconfirmed) 결과를 내는 fake 콘솔, **Then** 3번째 명령은 `gate.execution_port.execute()` 가 호출되지 않는다(mock 호출 카운트 2). |
| AC-LDSEND-003 | 003 | D | 아래 표의 각 조건을 fake gate/콘솔로 재현해 `send()` 반환값이 표와 일치하는지 확인한다(5개 시나리오 전부). |
| AC-LDSEND-004 | 004 | D | **Given** fake 콘솔 링크가 `execute()` 호출 시 예외를 던지도록 구성, **When** `send(bundle)` 호출, **Then** 예외가 `send()` 밖으로 전파되지 않고 반환값은 `STATE_UNKNOWN` 이다. |
| AC-LDSEND-005 | 005 | D | **Given** 3개 명령 중 1번째만 성공하고 나머지가 미확인이라 조기 중단된 bundle, **When** `send()` 반환 직후, **Then** 회수 메서드(§2.0-나)가 정확히 1회 호출되고(mock 카운트), 그 뒤 같은 세션 키로 남은 두 명령을 `execution_port.execute()` 로 직접 불러도 거부된다(`ok=False`, "not cleared" 사유). |
| AC-LDSEND-006 | 006 | S+D | **Given** 두 개의 서로 다른 세션 키(`bind_session_key` 로 각각 바인딩)에 각각 클리어런스 발급, **When** 세션 A 에서 회수 메서드 호출, **Then** 세션 A 의 클리어런스만 비고 세션 B 의 클리어런스는 그대로 남아 실행 가능하다. |
| AC-LDSEND-007 | 007 | S+D | **Given** 관측 도구 모듈, **When** `grep -rnE "^\s*(from\|import)\s+server\.bridge" server/tools/director_apply_observe.py`, **Then** 매치가 있다면 그 import 는 `build_console_stack()` 을 거치는 것이 아니라 도구가 직접 `OscBridge`/새 소켓을 여는 것이므로 FAIL — 이 기준은 도구가 `server.safety.bootstrap.build_console_stack` 만 호출하는지를 코드 리뷰로 확인한다(단일 호출 지점). |
| AC-LDSEND-008 | 008 | D | **Given** fake 콘솔이 대상 destination 이 이미 점유돼 있다고 응답, **When** 도구가 그 destination 에 쓰려고 시도, **Then** 진행을 거부하고 콘솔에 쓰기 명령을 보내지 않는다(fake 콘솔 호출 카운트로 확인). **Given** 대상이 비어 있다고 응답, **When** 같은 시도, **Then** 진행한다. |
| AC-LDSEND-009 | 009 | S+D | **Given** `--execute` 없이 도구 실행, **When** 임의의 시나리오 인자 조합, **Then** fake 콘솔에 대한 실제 송신 호출이 0회이고 계획(명령 목록)만 표준출력에 나타난다. |
| AC-LDSEND-010 | 010 | H(콘솔 필요) | **Given** onPC 실기, **When** `--execute` 로 021/024/032 세 시나리오를 각각 구동, **Then** 각 시나리오의 결과가 `BundleSender` 반환값이 아니라 별도 readback 조회 결과로 보고된다 — 관측 기록에 readback 질의와 그 응답이 그대로 인용된다. |
| AC-LDSEND-011 | 011 | H(콘솔 필요) | **Given** `--execute` 실행이 끝난 직후, **When** cleanup 단계 실행, **Then** 관측 기록에 cleanup 전/후 콘솔 상태(destination 점유 여부)가 각각 기록되고 후가 "비어 있음"이다. |
| AC-LDSEND-012 | 012 | S+D | **Given** 도구가 cleanup 또는 시나리오 구동을 위해 만든 approval 객체, **When** 그 객체의 principal/reason 필드를 조회, **Then** 고정된 구분 문자열(예: `ldsend-observe-harness`)을 포함하고, `grep -n "director_apply_observe" server/web/serve.py` 는 매치 0 이다. |

## 3. 기준별 검증 명령

### AC-LDSEND-001~006 — 송신기·클리어런스

```bash
uv run pytest server/tests/test_director_sender.py -q
uv run pytest server/tests/test_safety_gate.py -q
```

**AC-LDSEND-003 판정 표(재확인 — plan.md §4 와 동일)**:

| 조건 | 기대 반환 |
|---|---|
| 모든 명령 확인됨 | `STATE_ACKNOWLEDGED` |
| 첫 명령부터 명시적 실패, 그 전 확인 없음 | `STATE_FAILED` |
| 어떤 명령이든 미확인(timeout) | `STATE_UNKNOWN` |
| 앞서 확인된 명령 이후 명시적 실패(부분 완료) | `STATE_UNKNOWN` |
| 콘솔 링크 예외 | `STATE_UNKNOWN` |

### AC-LDSEND-007~009 — 관측 도구 골격

```bash
uv run pytest server/tests/test_director_apply_observe.py -q
grep -n "build_console_stack" server/tools/director_apply_observe.py
```

**PASS 조건**: `build_console_stack` 호출이 정확히 1곳(또는 시나리오별로
여러 곳이더라도 전부 그 함수를 통해서만)이고, 도구 자신이 `OscBridge` 를
직접 인스턴스화하는 코드가 없다.

### AC-LDSEND-010~011 — 콘솔 필요 (로컬로 닫히지 않는 부분)

수동 절차 — `progress.md` §M5(run-phase)에 다음을 기록한다:

1. `--execute` 로 021 시나리오 구동 → readback 질의 명령·응답 verbatim 인용.
2. `--execute` 로 024 시나리오 구동(의도적 실패 유발) → 후속 bundle 이
   실기에서도 안 갔는지 readback 으로 확인한 결과 verbatim 인용.
3. `--execute` 로 032 recovery 시나리오 구동 → recovery apply 의 readback
   결과 verbatim 인용.
4. 각 시나리오 뒤 cleanup 실행 → cleanup 전/후 destination 점유 상태 인용.

**주의**: 이 넷은 이 문서가 go/no-go 를 내리지 않는다 — 관측했다는 사실과
그 결과를 정직하게 기록하는 것이 이 SPEC 의 완결 조건이다(spec.md §1.1).

### AC-LDSEND-012 — labelling 경계

```bash
grep -n "director_apply_observe" server/web/serve.py || echo "PASS: not wired into serve.py"
grep -n "ldsend-observe" server/tools/director_apply_observe.py
```

### 경계 기준 (공통)

```bash
# 이 SPEC 이 만드는 코드는 OSC 를 직접 만지지 않는다
grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/sender.py \
  server/tools/director_apply_observe.py ; test $? -ne 0 && echo "PASS: no direct OSC import"

# ExecutionResult 소비자 넷의 회귀 없음(§2.0-가 전제 검증)
uv run pytest -q

# 회귀
uv run pytest -q
```

**양성 대조**: grep 자체가 동작하는지 확인한다 — `grep -rn "def " server/director/sender.py`
가 매치를 내는지 같은 회차에서 본다.

## 4. go / no-go

**go 조건 (전부 충족)**:
- AC-LDSEND-001~009, 012 — 로컬 pytest 로 PASS, 검증 명령의 실제 출력이
  인용되어 있다.
- 경계 기준 grep 이 기대대로 0 또는 매치이고 양성 대조가 성립한다.
- `uv run pytest` 전체 실패 0(회귀 없음).
- §2.0(plan.md)의 두 인터페이스 결정에 대한 사람 확인 기록이 있다.
- AC-LDSEND-010·011 은 관측 기록이 존재한다 — PASS/FAIL 이 아니라 **관측
  완료 여부**로 판정한다(콘솔 필요 항목).

**콘솔 필요 항목(AC-010·011)은 이 SPEC 만으로 go/no-go 를 내지 않는다.**
그 최종 판정은 `SPEC-LDCERT-001`(미작성)의 몫이다.

**no-go**:
- AC 중 하나라도 검증 명령 출력 없이 PASS 로 표시된 경우.
- `revoke_clearances()`(또는 동등 메서드)가 다른 세션의 클리어런스에
  영향을 주는 것이 발견된 경우 — M6c-1 세션 격리 불변식 위반.
- `ExecutionResult` 확장이 §2.0-가가 전제한 네 소비자 중 하나라도 깨뜨린
  경우.
- 회귀 실패가 하나라도 있는 경우.

## 5. 이 SPEC 이 판정하지 않는 것

- **연출 품질을 판정하지 않는다.** 이 층은 판단을 하지 않는다.
- **first-release go/no-go 를 판정하지 않는다.** `SPEC-LDCERT-001`(미작성)
  의 몫이다.
- **HTTP 라우팅·자격 발급을 판정하지 않는다.** 큐 카드 t421 소관이다.
- **operator 개입 감지(`InterferenceDetector`)의 실물 구현을 판정하지
  않는다.** 이 SPEC 은 그 프로토콜을 구현하지 않는다(§4 spec.md 비목표).

## 6. 미검증 (Gaps — 작성 시점)

- **기준선 숫자 미확정.** 착수 전 `uv run pytest -q` 를 재실행해야 한다.
- AC-024 관측 시나리오의 "안전한 실패 유발 명령"이 plan.md §7 대로
  미확정이다 — M5 착수 시 실기로 먼저 확정한다.
- 021 승격부의 정확한 readback 질의 경로(모델·property 이름)가 미확정이다
  — plan.md §7 참고.
- `server/orchestrator/ports.py` 확장(§2.0-가)이 실제로 채택될지는
  Implementation Kickoff Approval 단계의 사람 결정에 달려 있다 — 채택되지
  않으면 AC-LDSEND-003 의 판정 로직(문자열 판별 대안 A)이 이 문서와
  달라질 수 있다.
