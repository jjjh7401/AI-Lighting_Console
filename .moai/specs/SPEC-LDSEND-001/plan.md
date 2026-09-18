# 구현 계획 — SPEC-LDSEND-001

[요구사항](spec.md) · [인수](acceptance.md) · 선행: [SPEC-LDRECV-001](../SPEC-LDRECV-001/spec.md)

## 1. 착수 경계

개발 방법론은 **TDD (RED-GREEN-REFACTOR)** 다 —
`.moai/config/sections/quality.yaml` `constitution.development_mode: tdd`.

이 계획은 **Implementation Kickoff Approval 을 아직 받지 않았다.** 승인 없이
구현을 시작하지 않는다.

[HARD] **착수 전에 §2.0 의 두 인터페이스 결정(`ExecutionResult.outcome` 확장
여부, `SafetyGate` 클리어런스 회수 메서드 시그니처)을 먼저 사람에게 확인받는다.**
둘 다 되돌리기 가장 비싼 결정이다 — 테스트가 한 번 그 형태에 고정되면 이후
바꾸는 비용이 크다. 이 문서는 각 결정에 권고안을 제시하지만 최종 확정은
Implementation Kickoff Approval 단계에서 사람이 한다.

## 2.0 인터페이스 결정 — 가장 먼저 확인받아야 하는 것

### (가) `ExecutionResult`(게이트 쪽) 에 명시적 `outcome` 필드를 추가할지

**문제**: `server/orchestrator/ports.py` 의 `ExecutionResult` 는 `ok: bool`,
`detail: str` 두 필드뿐이다(24~28행 실측). `SafetyGate._execute_cleared`
(`gate.py:904-950`)는 콘솔의 `ExecOutcome.status`(`"ok"`/`"failed"`/
`"unconfirmed"`, `console.py:79-87`)를 이 두 필드로 접는데, `"failed"` 와
`"unconfirmed"` 가 **둘 다 `ok=False`** 로 뭉개진다 — 구분은 `detail` 문자열
안에 "execution unconfirmed" 라는 문구가 있는지로만 가능하다(`gate.py:943-948`).

이 SPEC 의 REQ-LDSEND-003(번들 상태 매핑)은 정확히 이 구분에 의존한다 —
"확인 안 됨"(콘솔이 확인을 안 줬다, timeout)과 "명시적으로 실패"(콘솔이
거부를 확인해 줬다)를 갈라야 `unknown`/`failed` 를 정직하게 나눌 수 있다
(계약 §10, "blind 하게 success/failed 로 확정하지 않는다").

**대안 A(비권장)**: `detail` 문자열에서 `"unconfirmed"` 부분 문자열을 찾아
구분한다. 코드 변경이 없다는 장점이 있지만, 사람이 읽으라고 쓴 안내 문구를
제어 흐름 신호로 쓰는 것은 취약하다 — 문구가 바뀌면 조용히 깨진다.

**대안 B(권장)**: `ExecutionResult` 에 선택적 필드
`outcome: str = "ok"`(값: `"ok"`/`"failed"`/`"unconfirmed"`)를 추가하고,
`gate.py` 안의 기존 `ExecutionResult(...)` 생성 지점 5곳(880~900행,
917~950행 각각 lock/health 차단·성공·unconfirmed·failed 분기)에서 이 값을
명시적으로 채운다. 새 필드는 기본값을 가지므로 기존 호출자
(`server/measurement/runner.py`, `server/web/session.py`,
`server/web/panel.py`, `server/deploy/pipeline.py` — 전부 `.ok`/`.detail`
만 읽는 소비자, grep 확인)는 아무 영향을 받지 않는다.

**채택(잠정, 사람 확인 대상)**: 대안 B. 문자열 스니핑보다 명시적 필드가
싸고(추가 LOC ~15줄) 덜 취약하다. [NEEDS CLARIFICATION: 대안 B 로
`server/orchestrator/ports.py` 를 확장하는 것을 승인하는지, 아니면 대안 A 의
문자열 판별을 받아들이고 그 취약성을 문서화하는 것으로 충분한지 — Implementation
Kickoff Approval 전에 확인.]

### (나) `SafetyGate` 클리어런스 회수 메서드

**문제**: `execute_preapproved()`(`gate.py:645`)는 성공 시
`self._clearances[session_key] = Counter(commands)` 로 세션별 카운터를
덮어쓴다. `_execute_cleared()`(`gate.py:922-930`)는 명령 하나를 보낼 때마다
그 카운터에서 하나씩 줄인다. **문제는 이 카운터를 명시적으로 비우는 API 가
오늘 존재하지 않는다는 것이다** — 다음 `screen()`/`execute_preapproved()`
호출이 같은 세션 키로 다시 올 때까지, 다 안 쓴 클리어런스는 그대로
남는다. `BundleSender` 가 REQ-LDSEND-002 대로 번들 중간에 송신을 멈추면,
남은 명령들의 클리어런스는 이 apply 요청이 끝난 뒤에도 살아 있다 — 같은
세션 키로 오는 **다른, 무관한** `execution_port.execute(command)` 호출이
그 클리어런스를 우연히 재사용할 수 있다는 뜻이다(같은 명령 문자열이 우연히
같을 때).

**채택**: `SafetyGate` 에 최소 public 메서드를 하나 추가한다 —
`def revoke_clearances(self) -> None:` — 호출한 세션의
`self._clearances[current_session_key()]` 를 빈 `Counter()` 로 되돌린다.
`_clearances_lock` 을 그대로 재사용해 동시성 안전을 지킨다. 다른 세션 키의
카운터는 건드리지 않는다 — `screen()`/`execute_preapproved()` 의 세션별
스코프 불변식(M6c-1, `gate.py` 머리말 19~26행)을 그대로 지킨다.

`ApplyCoordinator`(`server/director/execution.py`) 또는 새 송신기 호출부가
`execute_bundles()` 반환 직후(성공이든 조기 중단이든) 이 메서드를 부른다 —
REQ-LDSEND-005.

## 2. 마일스톤

착수 순서를 정하는 원리: 되돌리기 가장 비싼 인터페이스 결정을 먼저
확정하고(M1), 그 인터페이스 위에 실물 송신기를 얹고(M2), 사람이 보는 CLI
동작(dry-run/`--execute`)을 정하고(M3), 그 위에 실제 시나리오 배선을
쌓고(M4), 마지막으로 코드가 아닌 실기 관측을 수행한다(M5).

| 단계 | REQ | 파일 소유 | 완료 산출물 | 콘솔 | TDD |
|---|---|---|---|---|---|
| M1 인터페이스 확정 | 003, 005, 006 | 기존 `server/orchestrator/ports.py` **EXTEND**(§2.0-가 채택 시 `outcome` 필드); 기존 `server/safety/gate.py` **EXTEND**(`revoke_clearances()` 추가 + 5곳 `ExecutionResult(...)` 생성에 `outcome=` 채움); 기존 `server/tests/test_safety_gate.py` **EXTEND** | `revoke_clearances()` 가 자기 세션 카운터만 비운다, 다른 세션 영향 없음, `ExecutionResult.outcome` 이 ok/failed/unconfirmed 를 정확히 구분 | 아니오 | RED 먼저 |
| M2 실물 송신기 | 001, 002, 004 | 신규 `server/director/sender.py`(`GateBundleSender` 클래스, `BundleSender` Protocol 구현); 신규 `server/tests/test_director_sender.py` | 순서대로 송신, 첫 미확인 뒤 중단, 넷 중 하나의 상태 반환, 콘솔 링크 예외를 unconfirmed 로 흡수, `send()` 반환 뒤 M1 의 회수 메서드 호출 | 아니오 | RED 먼저 |
| M3 관측 도구 골격 | 007, 009 | 신규 `server/tools/director_apply_observe.py`; 신규 `server/tests/test_director_apply_observe.py` | `build_console_stack()` 재사용, 인자 파싱, dry-run 기본값, `--execute` 없이는 콘솔에 아무것도 쓰지 않는다는 것을 fake 콘솔로 확인 | 아니오 | RED 먼저 |
| M4 시나리오 배선 | 008, 010, 011, 012 | `server/tools/director_apply_observe.py` 계속 확장 | AC-021/024/032 세 시나리오 함수, destination 점유 확인, cleanup 단계, labelled auto-approve `ApprovalPort`(cleanup 용) | 아니오(로직) / 예(§4 실행 자체) | RED 가능한 부분만(dry-run 출력 형태) |
| M5 실기 관측 | (spec.md §5 콘솔 필요 항목) | 코드 없음 — `progress.md` 기록만 | 021 승격부·024 관측부·032 실행부·cleanup 이 실제로 지워졌는지의 관측 기록 | **예** | n/a — 수동 |

M1 → M2 → M3 → M4 → M5. M2 는 M1 의 `revoke_clearances()`/`outcome` 필드가
있어야 완결된다(TDD 로 M1 을 GREEN 으로 만든 뒤 M2 의 fake 게이트가 그
인터페이스를 흉내낸다). M4 는 M3 의 CLI 골격 위에 시나리오를 얹으므로
순서가 뒤바뀌면 다시 쓰게 된다. M5 는 M1~M4 가 전부 로컬에서 닫힌 뒤에만
의미가 있다 — 실물 송신기 없이 실기를 관측할 수는 없다.

## 3. PRESERVE — 건드리지 않는다

| 영역 | 파일 |
|---|---|
| apply 재검사·직렬화·journal | `server/director/execution.py` 의 `ApplyCoordinator`/`ExecutionJournal` 본체 — `execute_bundles()` 호출부만 새 송신기를 주입할 뿐, 그 함수 자체·`ApplyCoordinator.apply()` 의 재검사 순서는 바꾸지 않는다 |
| SafetyGate 파이프라인 본체 | `server/safety/{grammar,classify,backup,console,monitor,expand,ruleset,blacklist.yaml,programmer_arbiter}.py` — 읽기·호출만. `gate.py` 자체도 §2.0 이 명시한 최소 확장(새 메서드 1개 + 기존 5개 생성 지점에 필드 채움)만 한다 |
| OSC 송신 | `server/bridge/osc.py` — 이 SPEC 도 직접 import 하지 않는다. `SafetyGate.execution_port` 를 거친다(REQ-LDSEND-001) |
| `ExecutionResult` 소비자 넷 | `server/measurement/runner.py`, `server/web/session.py`, `server/web/panel.py`, `server/deploy/pipeline.py` — `.ok`/`.detail` 만 읽는 소비자이므로 §2.0-가의 선택적 필드 추가에 영향받지 않는다. 이 넷의 코드 자체는 건드리지 않는다 |
| 저장·검증·인증층 | `server/director/{models,store,service,context,knowledge,digest,emit,auth,approvals,director_api}.py` — 형제 SPEC 소유. 이 층은 읽고 호출만 |
| 스크래치 destination 정책 | `../SPEC-LDRECV-001/spec.md` §2 의 "server-selected 새 Sequence create-only" 원칙을 관측 도구도 그대로 따른다 — overwrite·silent reselection 없음 |

## 4. TDD 순서 (대표 마일스톤 예시)

### M1 (인터페이스)

1. **RED** `server/tests/test_safety_gate.py` 에 추가: `execute_preapproved()`
   로 클리어런스를 발급한 뒤 `revoke_clearances()` 를 부르면 그 세션의
   `execution_port.execute(command)` 가 더 이상 통과하지 않는지(`ok=False`,
   "not cleared" 사유). 다른 세션 키로 발급된 클리어런스는 어느 세션이
   `revoke_clearances()` 를 불러도 영향받지 않는지(두 세션 키를
   `bind_session_key` 로 각각 만들어 대조). `_execute_cleared` 가 반환하는
   `ExecutionResult.outcome` 이 성공/실패/미확인 세 경로 각각에서
   `"ok"`/`"failed"`/`"unconfirmed"` 인지.
2. **GREEN** `gate.py` 에 `revoke_clearances()` 추가, 5곳 생성 지점에
   `outcome=` 채움, `server/orchestrator/ports.py` 에 필드 추가.
3. **REFACTOR** 필요 시 다섯 생성 지점을 작은 헬퍼로 통일.

### M2 (실물 송신기)

1. **RED** `server/tests/test_director_sender.py`: fake 콘솔 링크(즉
   `ConsolePort` 를 흉내내는 fake — `execute(command) -> ExecOutcome`)와
   fake gate(`GatePort` Protocol — `.lock`·`.execute_preapproved()`)를
   주입해 — 전부 ok → `STATE_ACKNOWLEDGED`; 첫 명령이 명시적으로 실패(그 전
   확인된 명령 없음) → `STATE_FAILED`; 중간 명령이 확인 안 됨(timeout) →
   `STATE_UNKNOWN`; 앞선 명령이 이미 확인됐는데 뒤 명령이 명시적으로
   실패(부분 완료) → `STATE_UNKNOWN`(콘솔에 이미 일부가 도달했으므로
   `failed` 로 부를 수 없고, 전부가 확인된 것도 아니므로 `ACKNOWLEDGED` 도
   아니다 — 계약의 "atomic OSC rollback 을 주장하지 않는다"를 이 갈래가
   구체화한다); 콘솔 링크가 예외를 던짐 → 그 명령을 unconfirmed 로 잡고
   번들 전체 `STATE_UNKNOWN`; `send()` 반환 뒤 `revoke_clearances()` 가
   정확히 한 번 호출됐는지(mock 호출 카운트).
2. **GREEN** `sender.py` 의 `GateBundleSender` 최소 구현.
3. **REFACTOR** 상태 판정 로직을 표 기반 헬퍼로 정리.

**번들 내부 상태 판정 표(REQ-LDSEND-003 의 구체화)**:

| 조건 | 반환 상태 |
|---|---|
| 모든 명령이 확인됨(ok) | `STATE_ACKNOWLEDGED` |
| 첫 명령부터 명시적 실패, 그 전 확인된 명령 없음 | `STATE_FAILED` |
| 어떤 명령이든 confirm 안 됨(timeout) | `STATE_UNKNOWN` |
| 앞서 확인된 명령이 있는 상태에서 뒤 명령이 명시적 실패(부분 완료) | `STATE_UNKNOWN` |
| 콘솔 링크가 예외를 던짐 | `STATE_UNKNOWN`(그 명령을 unconfirmed 로 취급) |

`STATE_SENT` 는 이 구현이 반환하지 않는다 — `ConsoleLink.execute()` 자체가
확인 또는 timeout 까지 블록하므로(`console.py:284-286` 독스트링,
"blocks until confirmed or timeout"), "보냈지만 아직 확인 대기 중"이라는
중간 상태가 `send()` 반환 시점에는 존재하지 않는다. `STATE_SENT` 는 향후
비동기 송신기를 위해 프로토콜 어휘로 남는다.

### M3~M4 (관측 도구)

1. **RED** `server/tests/test_director_apply_observe.py`: fake 콘솔로
   `build_console_stack()` 을 대체해 — 기본 인자(플래그 없음)로 실행하면
   콘솔에 아무 명령도 안 나가고 계획만 출력되는지(`monkeypatch` 로 fake
   send 카운트 0 확인); `--execute` 없이는 어떤 인자 조합으로도 실행 경로가
   콘솔 쓰기에 도달하지 않는지.
2. **GREEN** CLI 골격 + dry-run 출력.
3. 시나리오 함수(021/024/032)는 fake 콘솔로 그 판정 로직(readback 호출 순서,
   destination 점유 확인 순서)만 pytest 로 고정한다 — 실제 onPC 대상
   `--execute` 경로는 M5 의 수동 실행이다.

각 단계마다 `uv run pytest` 관련 파일을 돌려 착수 시점 기준선이 깨지지
않는지 본다(§5).

## 5. 검증 명령

```bash
# 착수 시 기준선 재측정
uv run pytest -q

# 이 SPEC 범위
uv run pytest server/tests/test_safety_gate.py server/tests/test_director_sender.py \
  server/tests/test_director_apply_observe.py -q

# 회귀 — 특히 ExecutionResult 소비자 넷이 영향받지 않았는지
uv run pytest server/tests/test_measurement_runner.py server/tests/test_web_session.py \
  server/tests/test_web_panel_execute.py server/tests/test_deploy_pipeline.py -q 2>&1 \
  || echo "일부 파일명은 실제 존재 여부를 착수 시 확인한다 — 추정 이름"

# 전체 회귀 (기준선 대조)
uv run pytest -q

# 경계: 이 층은 OSC 를 직접 만지지 않는다
grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/sender.py server/tools/director_apply_observe.py \
  || echo "OK - no direct OSC import"

# 경계: 관측 도구의 auto-approve ApprovalPort 가 운영 조립에 배선되지 않았는지
grep -n "director_apply_observe" server/web/serve.py || echo "OK - not wired into serve.py"
```

**CI 는 과금 차단으로 죽어 있어 판정 근거가 아니다.** 위 로컬 명령의 출력만
증거로 쓴다. spec.md §5 의 「콘솔 필요 = 예」 항목은 위 명령들로 판정할 수
없다 — M5 의 별도 관측 기록이 증거다.

## 6. 중단 조건

- **§2.0(가)·(나) 의 두 인터페이스 결정을 사람에게 확인받기 전에 M1 을
  시작하지 않는다.**
- `server/measurement/runner.py`/`server/web/session.py`/
  `server/web/panel.py`/`server/deploy/pipeline.py` 중 하나라도 `.ok`/
  `.detail` 외의 필드를 구조 분해나 위치 인자로 소비하고 있는 것이
  발견되면(§2.0-가의 "읽기 전용 소비자" 전제가 반증되면) 중단하고 대안 A
  (문자열 판별)로 재조정한다.
- `SPEC-LDRECV-001` 이 확정한 `ApplyCoordinator.apply()` 의 재검사 순서나
  `execute_bundles()` 의 시그니처가 이 문서가 인용한 것과 다르면(코드가
  이 문서 작성 뒤 바뀌었으면) 중단하고 다시 읽는다.
- M4 착수 시 AC-024 관측 시나리오에 쓸 "안전하게 콘솔에서 실패를 유발하는
  명령"이 §7 미검증 항목대로 여전히 불확실하면, 그 명령을 확정하기 전에는
  `--execute` 경로를 스크립트에 굳히지 않는다 — dry-run 출력까지만 완성하고
  M5 에서 사람이 직접 후보를 시도해 확정한다.

## 7. 미검증 (착수 전 남은 것)

- **AC-024 관측 시나리오의 "안전한 실패 유발 명령"이 미확정이다.**
  `Store Sequence <N> Cue <M> /Merge` 가 safe 로 분류된다는 것은 실측했다
  (`test_bulkgate_declaration.py:38-41`). 그러나 그 명령이 **콘솔에서**
  안정적으로 `failed`(거부 확인)를 내는 malformed 변형(예: 존재하지 않는
  참조를 포함한 조작)이 무엇인지는 이 문서 작성 시점에 코드만으로 확정할 수
  없다 — 그 판정은 grammar/classify 가 아니라 콘솔 자신의 응답이 정한다.
  [NEEDS CLARIFICATION: 어떤 구체적 MA3 명령이 게이트를 통과하면서도
  콘솔에서 신뢰성 있게 명시적 실패를 내는지 — M5 착수 시 실기로 먼저
  탐색하고, 그 결과를 이 문서에 반영한다.]
- **021 승격부의 정확한 readback 질의 경로가 미확정이다.** "responder 를
  통한 state/property 재조회로 object-existence 를 확인한다"는 spec.md §5
  가 요구하지만, `DataPool/Sequences/<N>` 형태의 정확한 경로 문법과
  존재/부재를 구분하는 응답 모양은 `server/director/context.py`/
  `models.py` 전문을 읽지 않았고 실기로 확인한 적도 없다. [NEEDS
  CLARIFICATION: M5 착수 시 `server/tools/responder_roundtrip.py` 로 먼저
  경로 문법을 확인한다.]
- **cleanup 의 스크래치 destination 정확한 번호 범위는 정책만 정했다.**
  "높은 미사용 Sequence 번호대, 쓰기 전 비어 있는지 확인, 점유돼 있으면
  거부"라는 정책(REQ-LDSEND-008)만 확정했고, 정확한 시작 번호는 M3~M4
  착수 시 CLI 인자(`--sequence-range-start`, 기본값 제안 9900)로 남긴다 —
  스크립트에 하드코딩하지 않는다.
- **§2.0-가의 "읽기 전용 소비자" 전제는 grep 확인이지 전수 대조가
  아니다.** 넷 중 하나가 실은 `ExecutionResult` 를 위치 기반으로 소비하고
  있을 가능성은 M1 착수 시 각 파일을 직접 읽어 다시 확인한다.
- **LOC 추정 없음.** Tier M 으로 잡았으나(§1, spec.md — 새 파일 4개 + 공유
  파일 2개(EXTEND) + 콘솔 게이트 항목 몇 건의 규모로 판단, 예상 600~1000
  LOC), 실제 구현 규모는 재지 않았다.
- **계획 내용에 대한 독립 plan-audit 없음.** 형제 SPEC 들이 이 저장소에서
  착수 전 컨텍스트 초과로 `plan-auditor` 가 죽는다고 기록했다(`SPEC-LDRECV-001
  plan.md` §7). 이 SPEC 에 대한 plan-audit 이 같은 이유로 죽으면, 오케스트
  레이터 자기 검수임을 숨기지 않고 기록한다.
