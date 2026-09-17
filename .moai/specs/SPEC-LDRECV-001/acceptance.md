# 인수기준 — SPEC-LDRECV-001

[요구사항](spec.md) · [구현 계획](plan.md) · [seam 설계 결정 3건](design.md) · 우산 계약: [contract.md](../SPEC-LDPLUGIN-001/contract.md)

## 1. 판정 수단과 그 한계

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이 유일한 자동
판정 근거다. 아래 모든 기준은 로컬에서 판정 가능하도록 작성했으며, 원격 체크 초록에
의존하는 기준은 없다.

**기준선은 착수 시점에 재측정한다.** 이 문서를 쓴 시점에 로컬 checkout 이 origin/main 보다
6 커밋 뒤져 있었으므로(`plan.md` §7), 형제 SPEC 들이 적은 숫자를 그대로 옮기지 않는다.
착수 전 `uv run pytest -q` 를 한 번 돌려 그 출력을 이 SPEC 의 기준선으로 기록한다.

**증거 규율**: 각 기준의 PASS 는 그 기준의 검증 명령을 **실제로 돌려서 본 출력**으로만
주장한다. 명령을 안 돌린 항목은 PASS 가 아니라 **Gap** 으로 적는다. 실패 신호가 없다는
것은 통과의 증거가 아니다.

**콘솔 게이트 주의**: 아래 AC 중 021·024·032 각각 일부(§3 의 "**콘솔 필요**" 표시부)는
로컬 pytest 로 닫을 수 없다. 그 부분은 실기(또는 인증 onPC+rig) 관측 기록이 별도
증거이며, 관측 전에는 `unsupported`/`unknown+recovery_required` 로 정직하게 답하는 것이
이 SPEC 이 요구하는 상태다.

## 2. 기준 — REQ 와 1:1

id 는 우산에서 승계한다 (`../SPEC-LDPLUGIN-001/spec.md:45` — id 는 파일 이동과 무관하게
유지).

| AC | REQ | 종류 | 기준 |
|---|---|---|---|
| AC-LDPLUGIN-018 | 018 | S+D | **Given** MCP credential 로 human-only route(승인/거절/apply/feedback approve·revoke/reconcile) 호출, 또는 만료·철회된 credential, 또는 Host/Origin 불일치, **When** 요청, **Then** 각각 `SCOPE_DENIED`/`UNAUTHENTICATED`/`ORIGIN_DENIED` 를 반환하고 secret 이 로그·응답·model context 어디에도 노출되지 않는다. |
| AC-LDPLUGIN-019 | 019 | D+H | **Given** 서버 immutable record 로 역참조되지 않는 `actor_ref`/`origin`/`confirmation` 주장, **When** 권한 판단에 소비, **Then** 그 주장만으로 승격하지 않는다. **Given** audio 의 외부 provider 전송 요청, **When** 앱 명시 동의가 없음, **Then** 차단하고 목적/수신자/범위 기록 없이 전송하지 않는다. |
| AC-LDPLUGIN-020 | 020 | S+D+H | **Given** `ready_for_review` plan, **When** human 이 APP route 로 승인, **Then** `ApprovalBinding`(approval_id·plan_id·plan_revision·plan_digest·context_digest·compiled_digest·principal_id·console_id·session_id·safety_policy_revision·approved_at·expires_at) 을 발급하고 만료는 생성+10분과 validation/context 만료 중 빠른 값이다. **Given** 일반 chat/WS boolean 또는 MCP 호출, **When** 승인 시도, **Then** director 승인으로 인정하지 않는다. |
| AC-LDPLUGIN-021 | 021 | D+H | **Given** apply 요청이 lock 을 얻은 직후, **When** current bindings·target/destination occupancy·LiveLock·승인 신선도를 재검사, **Then** 하나라도 stale/점유/lock-active/만료면 차단하고 destination 은 server-selected 새 Sequence create-only 만 허용한다. **Given** 그 명령 bundle 이 SafetyGate 의 grammar/classify/backup/health/audit 를 통과해야 하는 경로, **When** apply, **Then** 그 다섯을 우회하지 않는다(§2.0-가는 여섯째인 일반 `ApprovalPort` 재질문만 건너뛴다). **콘솔 필요**: 통과한 apply 가 실제로 콘솔에 객체를 만들었는지(applied 판정)는 실기 관측이 있어야 한다. |
| AC-LDPLUGIN-022 | 022 | D | **범위(design.md §2.5, M3 착수 후 확정): director·chat·import — panel(대시보드 실행기 조작, REQ-SHOWUI-013)은 제외.** **Given** director apply 가 중재자 lock 을 쥔 동안 동시 chat/import mutation 요청, **When** 그 요청 도착, **Then** `TARGET_BUSY` 로 거부하고 오래 대기시켜 낡은 승인을 실행하지 않는다. 역방향(chat 이 먼저 쥔 lock 에 director 가 요청)도 동일하다. **Given** panel 조작(`PanelRuntime.fire()`)이 도착, **When** director apply 나 chat 이 중재자 lock 을 쥔 상태, **Then** panel 은 `arbitrate=False` 로 그 lock 을 건너뛰어 REQ-SHOWUI-013("chat 진행 중에도 panel 은 busy 로 막히지 않는다")대로 정상 통과한다 — busy 로 거부되지 않는다. |
| AC-LDPLUGIN-023 | 023 | D+H | **Given** 같은 `(project_id, principal_id, operation, idempotency_key)` + 같은 request fingerprint 로 재제출, **When** 처리, **Then** 최초 status·body 그대로 replay 한다. **Given** 같은 key + 다른 request, **When** 제출, **Then** `IDEMPOTENCY_CONFLICT`(409). **Given** socket send 후 DB commit 전 crash(합성), **When** 재시작 후 조회, **Then** 그 execution 은 `unknown` 이며 blind 하게 success/failed 로 확정하지 않는다. |
| AC-LDPLUGIN-024 | 024 | D | **Given** bundle 시퀀스 중 하나가 실패/간섭/불확실 전송, **When** 이후 bundle 평가, **Then** 후속 bundle 은 전송하지 않고(`not_sent` 로 receipt 에 보존) `failed`/`partial`/`unknown` 을 정확히 구분한다(하나라도 확인 불가면 `unknown` 이 `partial` 보다 우선). blind retry 나 atomic OSC rollback 을 주장하지 않는다. |
| AC-LDPLUGIN-032 | 032 | D+H | **Given** release/운영 중단 결정, **When** 실행, **Then** 해당 principal 의 MCP/human credential 을 즉시 철회하고 신규 apply 를 차단하며 journal 을 삭제·수정하지 않고 보존한다. **Given** 과거 execution 이 partial/unknown, **When** recovery 흐름(새 revision→검증→승인→apply `recovery_of`), **Then** 원본 execution 기록은 불변으로 남고 새 execution 이 별도로 생긴다. **콘솔 필요**: recovery apply 가 실제로 적용됐는지는 실기 관측이 있어야 한다. |

종류 표기는 우산 `acceptance.md` 와 같다 — S=schema/static, D=결정적(합성 입력),
H=사람 확인(또는 콘솔 관측).

## 3. 기준별 검증 명령

### AC-LDPLUGIN-018 — 인증·ACL·CSRF·Origin

```bash
uv run pytest server/tests/test_director_auth.py -q
```

**PASS 조건**: MCP credential 로 human-only scope 6종(`plan:approve plan:reject
plan:apply feedback:read feedback:approve feedback:revoke execution:reconcile`) 각각
호출 시도 시 `SCOPE_DENIED`. 만료·철회 credential → `UNAUTHENTICATED`. Origin 불일치
(exact-match 아닌 모든 경우) → `ORIGIN_DENIED`. loopback Host allowlist 밖 요청 거부.
**secret 비노출 assertion**: 테스트 로그·응답 body·예외 메시지 전체를 캡처해
pairing secret 문자열이 등장하지 않는지 grep 으로 단언한다 — "노출 안 됨" 을 관찰
부재로 주장하지 않는다.

**양성 대조 필수**: 올바른 scope·올바른 audience·올바른 Origin 의 정상 요청이 실제로
통과하는지 같은 실행에서 확인한다. 전부 거부하는 미들웨어도 모든 거부 케이스를
"통과"시키므로, 양성 대조 없이는 이 기준이 공허하다.

### AC-LDPLUGIN-019 — evidence 권한 불신·audio 동의

```bash
uv run pytest server/tests/test_director_evidence_trust.py -q
```

**PASS 조건**: `actor_ref`/`origin`/`confirmation` 필드만으로 권한을 부여하지 않고,
같은 project/principal/scope 의 immutable 서버 record 로 역참조했을 때만 human-confirmed/
approved-feedback 로 인정한다. audio 외부 전송 API(또는 그 경로)는 명시 동의 플래그가
없으면 호출 자체가 차단된다.

### AC-LDPLUGIN-020 — 사람 승인/거절

```bash
uv run pytest server/tests/test_director_approvals.py -q
```

**PASS 조건**: `ApprovalBinding` 9필드가 모두 채워지고, `approved_at`+10분과
`validation.expires_at`/`context.expires_at` 중 **빠른 값**이 `expires_at` 이 된다.
승인 뒤 plan head 변경·context stale·compiler/target/policy 변경 시 승인이 무효화되는지
(재조회 시 에러 또는 무효 플래그) 확인한다. 일반 WS 승인 boolean 이나 MCP 호출로
`ApprovalBinding` 발급을 시도하면 라우트 자체가 없거나(404) 거부되는지 확인한다.

### AC-LDPLUGIN-021 — apply 재검사·SafetyGate 연결 (부분 콘솔 게이트)

```bash
uv run pytest server/tests/test_director_apply_rejection.py server/tests/test_director_gate_bridge.py -q
```

**PASS 조건 (로컬로 닫히는 부분 — 거부 방향)**:
1. lock 을 쥔 직후 재검사에서 stale approval(head 변경/만료)·점유된 destination·활성
   LiveLock 각각이 apply 를 차단한다.
2. destination 예약은 create-only 다 — 이미 점유된 slot 을 조용히 다른 빈 slot 으로
   재선택하지 않는다(테스트가 그 재선택이 **일어나지 않음**을 단언).
3. `execute_preapproved`(또는 동등 경로)가 grammar/classify/backup/health/audit
   단계를 실제로 통과시키는지 — 위반 명령을 넣었을 때 기존 `screen()` 과 동일하게
   거부되는지 대조 시험으로 확인한다. 동시에 `self._approval_port.request_approval`
   이 director 경로에서는 **호출되지 않는지**(mock 호출 횟수 0) 단언한다.
4. 기존 `SafetyGate.screen()` 의 회귀 없음 — 새 메서드 추가가 `screen()` 자체의
   동작을 바꾸지 않았는지 기존 gate 테스트 스위트가 그대로 통과하는지 확인한다.

**콘솔 필요 (로컬로 닫히지 않는 부분 — 승격 방향)**: 통과한 apply 가 실제로 콘솔에
객체를 만들었는지(`applied` 판정, object-existence confirmed)는 실기 관측 기록이
별도 증거다. 이 기준은 이 문서가 go 로 판정할 수 없다.

### AC-LDPLUGIN-022 — 공유 programmer 중재자 (범위: director·chat·import — panel 제외)

```bash
uv run pytest server/tests/test_director_arbiter.py -q
uv run pytest "server/tests/test_web_panel_execute.py::TestSerialization" -q
```

**PASS 조건**: 두 동시 요청(둘 다 합성 — director 시뮬레이션 + chat 시뮬레이션) 중
정확히 하나만 lock 을 얻고 나머지는 `TARGET_BUSY`. lock 보유 중 재시도가 아니라
즉시 거부인지(폴링/대기 없음) 확인한다. lock 해제 후 대기 중이던 승인이 그대로
실행되지 않고 신선도를 다시 검사하는지(§AC-021 항목 1 과 결합) 확인한다.

**범위 제외 확인(design.md §2.5, M3 착수 후 확정)**: panel(대시보드 실행기 조작)은
이 중재자 대상이 아니다 — director apply 나 chat 이 lock 을 쥔 동안에도 panel
조작(`PanelRuntime.fire()`, `arbitrate=False`)은 `TARGET_BUSY` 없이 정상 통과해야
한다(REQ-SHOWUI-013). `test_web_panel_execute.py::TestSerialization`의
`test_the_chat_turn_lock_is_not_shared_with_the_panel`·
`test_a_stop_is_exempt_from_the_busy_guard` 가 이 조건을 고정한다.

### AC-LDPLUGIN-023 — durable journal·idempotency

```bash
uv run pytest server/tests/test_director_execution_journal.py -q
```

**PASS 조건**: 같은 idempotency key + 같은 request fingerprint 재제출 → 최초 status·
body **그대로**(재실행 아님) replay. 같은 key + 다른 request → `IDEMPOTENCY_CONFLICT`
409. fingerprint 는 `sha256(JCS({operation, project_id, principal_id, request}))` 이고
`request` 는 body 에서 `idempotency_key` 만 제거한 객체다(계약 §9.7 — 형제 `LDSTORE`
`AC-LDPLUGIN-015` 와 같은 계산 규칙).

**crash 시뮬레이션**: socket send 직후·DB commit 직전에 강제 예외를 주입하고 재시작 →
그 execution 이 `unknown` 으로 읽히는지(성공/실패로 조용히 확정되지 않는지) 확인한다.

**주의**: DB 파일을 지우고 다시 만드는 방식으로 durability 를 확인하지 않는다.
프로세스 재시작 후 **같은 파일에서 되읽어** 확인한다(형제 `LDSTORE`
`AC-LDPLUGIN-015` 와 동일 주의).

### AC-LDPLUGIN-024 — 실패/간섭 시 중단

```bash
uv run pytest server/tests/test_director_execution_failure.py -q
```

**PASS 조건**: N개 bundle 중 k번째가 실패/불확실 전송이면, k+1 번째부터는 전송을
시도하지 않고 receipt 에 `not_sent` 로 남는다(실제로 호출되지 않았는지 mock 호출
카운트로 단언). 상태 우선순위 — 확인 불가 항목이 하나라도 있으면 `unknown` 이
`partial` 보다 우선. 어떤 bundle 도 confirmed 되지 않고 미확정 전송도 없으면
`failed`. operator 개입(programmer 변경) 감지 시 진행 중이던 execution 이
`unknown`+`recovery_required` 로 전환되는지 확인한다.

### AC-LDPLUGIN-032 — 운영 중단·recovery (부분 콘솔 게이트)

```bash
uv run pytest server/tests/test_director_ops_lifecycle.py -q
```

**PASS 조건 (로컬로 닫히는 부분)**:
1. 철회 실행 직후 해당 principal 의 credential 로 어떤 route 를 호출해도
   `UNAUTHENTICATED`.
2. 철회 이후 신규 apply 요청이 credential 확인 단계에서 즉시 거부된다(뒤 단계까지
   가지 않는다).
3. journal(bundle 기록·idempotency 응답)을 조회하면 철회 전과 바이트 동일 — 삭제·
   수정된 필드가 없다.
4. recovery 흐름에서 원본 execution 의 partial/unknown 기록이 새 execution 생성
   후에도 그대로 남아 있다(`recovery_of` 로만 연결되고 덮어쓰지 않는다).

**콘솔 필요**: recovery apply 가 실제로 콘솔에 적용됐는지는 실기 관측이 별도
증거다.

### 경계 기준 (모든 마일스톤 공통)

```bash
# 이 층은 OSC 를 직접 만지지 않는다
grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/ ; test $? -ne 0 && echo "PASS: no direct OSC import"

# 이 층은 예술 판정/세션을 호출하지 않는다
grep -rnE "^\s*(from|import)\s+server\.(looks|web\.session)" server/director/ ; test $? -ne 0 && echo "PASS: no artistic producer"

# 이 층은 기존 일반 승인 채널을 director 승인으로 재사용하지 않는다
grep -rn "approval_bridge\|DenyAllApprovalPort" server/director/ ; test $? -ne 0 && echo "PASS: no general WS approval reuse"

# 회귀
uv run pytest -q
```

**PASS 조건**: 세 grep 이 각각 0 매치. `uv run pytest` 가 착수 시 기준선 대비 실패 0.

**양성 대조**: grep 자체가 동작하는지 확인한다 — `grep -rn "def " server/director/`
가 매치를 내는지 같은 회차에서 본다. 매치 0 이 "깨끗함" 인지 "grep 이 헛돎" 인지
구분되지 않으면 이 기준은 공허하다.

## 4. go / no-go

**go 조건 (전부 충족)**:
- 로컬로 닫을 수 있는 AC 전부 — PASS. 검증 명령을 실제로 돌린 출력이 인용되어 있다.
- 경계 기준 세 grep 이 0 매치이고 양성 대조가 매치를 냈다.
- `uv run pytest` 실패 0.
- 계약 §4·§5·§9·§10 과 구현의 대조가 기록되어 있다.
- §2.0(plan.md)의 SafetyGate 이음새 해석에 대한 사람 확인 기록이 있다.

**콘솔 필요 항목(AC-021·024·032 각 승격부)은 이 SPEC 만으로 go/no-go 를 내지 않는다.**
그 판정은 실기 관측 뒤 `SPEC-LDCERT-001`(미작성, first-release go/no-go 를 담당) 수준에서
내려진다. 이 SPEC 의 go 는 "거부·직렬화·journal 이 정직한가"까지다.

**no-go**:
- AC 중 하나라도 검증 명령 출력 없이 PASS 로 표시된 경우.
- 계약과 구현이 어긋난 채 남은 경우.
- 회귀 실패가 하나라도 있는 경우.
- `execute_preapproved`(또는 동등 경로)가 grammar/classify/backup/health/audit 중
  하나라도 건너뛰는 경우 — 이것은 "승인 재질문만 건너뛴다"는 §2.0-가의 범위를
  넘는다.

## 5. 이 SPEC 이 판정하지 않는 것

- **연출 품질을 판정하지 않는다.** 이 층은 판단을 하지 않으므로 예술 품질 기준이
  없다.
- **왕복 전체를 판정하지 않는다.** 얇은 왕복의 UI 쪽 관측은 `SPEC-LDUI-001` 기준이다.
- **first-release go/no-go 를 판정하지 않는다.** 실기 fidelity/visual/readback 전체
  판단은 `SPEC-LDCERT-001`(미작성)이다.
- **MCP adapter·플러그인 패키지의 동작을 판정하지 않는다.** `SPEC-LDHOST-001` 기준이다.

## 6. 미검증 (Gaps — 작성 시점)

- **기준선 숫자 미확정.** 착수 전 `uv run pytest -q` 를 재실행해야 한다(§1).
- 우산 `contract.md` §4(APP human routes)·§10(state machine)은 이 문서 작성 시 읽었으나,
  `ApprovalBinding`·idempotency fingerprint 의 정확한 필드 순서·타입을 스키마 파일
  (`schemas/exchange.schema.json`)과 줄 단위로 대조하지 않았다.
- SafetyGate `execute_preapproved` 의 구체적 시그니처는 아직 코드로 존재하지 않는다
  (`plan.md` §2.0-가는 제안이지 확정 설계가 아니다) — 이 acceptance 의 AC-021 항목 3
  은 그 제안이 실제로 구현된 형태에 맞춰 재확인이 필요할 수 있다.
- `server/orchestrator/tools.py` 접점(`plan.md` §2.0-나)이 미확정이므로, 그 접점에서
  나올 수 있는 추가 AC(예: 기존 chat/import 호출부의 회귀 없음)는 이 문서에 아직 없다.
  M3 착수 시 조사 결과에 따라 추가될 수 있다.
- 이 자식 SPEC 에 대한 독립 plan-audit 이 없다(형제 두 SPEC 모두 컨텍스트 초과로
  `plan-auditor` 가 죽었다고 기록했다).
