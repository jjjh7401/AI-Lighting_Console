# 구현 계획 — SPEC-LDRECV-001

[요구사항](spec.md) · [인수](acceptance.md) · [seam 설계 결정 3건](design.md) · 우산:
[계약](../SPEC-LDPLUGIN-001/contract.md) · [설계](../SPEC-LDPLUGIN-001/design.md) ·
[근거](../SPEC-LDPLUGIN-001/research.md) ·
형제: [저장층](../SPEC-LDSTORE-001/spec.md) · [검증층](../SPEC-LDCOMPILE-001/spec.md)

## 1. 착수 경계

개발 방법론은 **TDD (RED-GREEN-REFACTOR)** 다 —
`.moai/config/sections/quality.yaml` `constitution.development_mode: tdd`. 선행 두 형제와
동일하다.

이 계획은 **Implementation Kickoff Approval 을 아직 받지 않았다.** 우산
`SPEC-LDPLUGIN-001/spec.md:23` 과 같은 조건이 승계된다. 승인 없이 구현을 시작하지 않는다.

[HARD] **착수 전에 §2.0 의 seam 결정 셋(SafetyGate 승인 이중화, `tools.py` 접점,
destination occupancy 저장 위치)을 먼저 사람에게 확인받는다 — 세 결정의 근거와 대안
비교는 [design.md](design.md)에 있다.** 앞의 둘은 이 문서 작성 시점(2026-09-16)에
이미 조사했고, plan-audit(2026-09-16, FAIL, ≈0.75)의 D3 지적에 따라 `tools.py` 접점은
이번 보완에서 확정했다(§2.0-나 — 수정하지 않는다). 세 번째(destination occupancy)는
D5 지적에 따라 이번 보완에서 새로 조사·결정했다(§2.0-다). 특히 SafetyGate 의 기존
`ApprovalPort` 를 우회하는 새 public 메서드를 `gate.py` 에 추가하는 결정은 기존
안전장치의 동작을 바꾸는 것이므로, M3 착수 전에 별도 확인이 필요하다.

## 2. 마일스톤

착수 순서를 정하는 원리: 아무것도 인증 없이는 존재할 수 없고(M1), 승인 없이는 apply 가
없고(M2), 직렬화 없이 apply 를 먼저 만들면 나중에 안전 구멍을 메우는 재작업이
된다(M3→M4→M5 순), 운영 중단·recovery 는 앞의 모든 조각을 재사용한다(M6, 마지막).

| 단계 | REQ | 파일 소유 | 완료 산출물 | 콘솔 | 얇은 왕복 |
|---|---|---|---|---|---|
| M1 인증·공통 route 골격 | 018, 019 | 신규 `server/director/{director_api,auth}.py`; 기존 `server/web/app.py` **EXTEND**(router 등록) | audience·scope·principal/project/session ACL·Host/Origin·CSRF·만료/철회 검증, OS credential store 저장, 계약 §3 공통 route(GET context/knowledge/plan, POST validations, PUT plan, GET execution, POST feedback-proposals) HTTP 골격이 `LDSTORE`/`LDCOMPILE` service 를 호출, `ErrorEnvelope` shape | 아니오 | **예 — 필수** |
| M2 사람 승인/거절 | 020 | 신규 `server/director/approvals.py` | `POST .../approvals`·`POST .../rejections` route, `ApprovalBinding`(9필드) 발급, 세 digest·principal·target·policy·만료 묶음, mutation/context/compiler/target/policy 변경·만료·head 변경 시 무효화 | 아니오 | **예 — 필수** |
| M3 공유 programmer 중재자 | 022 | 신규 `server/director/programmer_arbiter.py`; 기존 `server/safety/gate.py` **EXTEND**(새 public 메서드 `execute_preapproved` + 공유 private 스테이지에 lock 획득/해제 추가); `server/orchestrator/tools.py` — **확정: 수정하지 않는다**(design.md §2 — lock 이 `gate.py` 안에 있어 `tools.py`·`session.py`·`measurement/runner.py` 세 호출부 모두 그대로 둔다) | director/chat/import 모든 shared mutation 이 하나의 lock 을 거침, 충돌 `TARGET_BUSY`, 오래 대기시켜 낡은 승인을 실행하지 않음 | 아니오 | 권장(누락 시 race 가능) |
| M4 durable journal·idempotency | 023 | 신규 `server/director/execution.py`; 신규 `server/director/migrations/002_execution_journal.sql`(**EXTEND** — `SPEC-LDSTORE-001` 의 001 뒤에 이어붙인다, 스키마 재정의 아님 — destination 예약 테이블도 이 마이그레이션에 포함, design.md §3) | 첫 write 전 승인 소비·execution·bundle journal·idempotency fingerprint·destination 예약을 하나의 transaction 으로 SQLite 저장, 동일 key+동일 request 는 최초 응답 replay, 다른 payload 는 409 | 아니오 | **예 — 필수** |
| M5 apply·실패 분류 | 021, 024 | 신규 `server/director/execution.py`(M4 이어서 확장) | `POST .../apply` route, lock 안 재검사(bindings·LiveLock·승인 + M4 의 destination 예약 테이블 조회로 occupancy 재검사 — `ContextSnapshot.target` 이 아니다, design.md §3), destination create-only 예약, SafetyGate 연결(§2.0), 실패/간섭/crash/불확실 시 후속 bundle 중단, failed/partial/unknown 구분 | **예(승격부만)** | **예 — lock 안 적용까지 필수, 승격 확정은 유보** |
| M6 운영 중단·recovery | 032 | 신규 `server/director/ops.py`(또는 `auth.py`/`execution.py` 에 흡수 — M 시작 시 판단) | 인증 철회, 신규 apply 차단, journal 보존, 새 revision→검증→승인→apply(`recovery_of`)의 명시 recovery 흐름 | **예(recovery apply 확정)** | 아니오 — 유보 |

M1 → M2 → M3 → M4 → M5 → M6. M2 는 M1 의 인증·route 골격 없이 발급할 곳이 없다. M3 는
M5 의 apply 가 안전하게 동작하기 위한 전제이므로 apply 보다 먼저 만든다 — 순서를
뒤집으면(먼저 apply 를 만들고 나중에 lock 을 끼우면) 그 사이에 만들어진 apply 경로가
직렬화 없이 동작한 이력을 남긴다. M4 도 같은 이유로 M5 보다 먼저다 — 계약 §10 이 journal
commit 을 "첫 execution allocation" 의 일부로 규정하므로, journal 없는 apply 를 먼저
만들면 되짚을 수 없는 상태를 만든다. M6 은 M1~M5 의 조각을 재사용만 하므로 마지막이다.

### 2.0 형제와의 이음새 — 가장 중요한 세 발견 (계약·코드 대조, 2026-09-16; plan-audit
D3·D5 지적으로 2026-09-16 보완 — 결정 근거는 [design.md](design.md) §1·§2·§3 참고)

**(가) SafetyGate 가 이미 "그 자신의" human 승인 채널을 갖고 있다 — director 승인과
충돌하지 않는 자리를 찾아야 한다.**

`server/safety/gate.py` `SafetyGate.screen()` 을 읽으면(358~479행), 분류 단계에서
`held` 로 표시된 명령(또는 호출자가 번들 위험을 선언한 명령)에 대해 **내부적으로
`self._approval_port.request_approval(approval_request)` 를 호출**한다. 이 `ApprovalPort`
는 기존 일반 채팅/WS 승인 채널(`server/safety/approval.py`, `server/web/approval_bridge.py`,
REQ-MVP-013/014/015/021)이며, 세션에 UI 가 안 붙어 있으면 fail-safe 로 **항상 거부**한다
(`DenyAllApprovalPort`).

director 의 apply 경로가 `screen()` 을 그대로 호출하면, 사람이 이미 director 자신의
`ApprovalBinding` 으로 승인한 뒤인데도 **두 번째로, 이번엔 존재하지 않는 UI 세션을 향해**
승인을 요청하고 자동으로 거부당한다. 계약이 금지하는 것은 정확히 반대 방향이다 — "일반
chat/WS boolean 을 director 승인으로 재사용하지 않는다"(LD-APPROVAL-001)이지, "director
가 SafetyGate 의 나머지 파이프라인을 우회해도 된다"가 아니다.

`REQ-LDPLUGIN-021` 원문을 다시 읽으면 우회 금지 대상이 정확히 열거되어 있다 — **"문법·
위험·백업·health·audit"**. 이 목록에 "승인" 은 없다. 즉 설계 의도는: director 는
grammar·classify·backup·health·audit 는 그대로 지나가되, **일반 `ApprovalPort` 재질문은
건너뛴다** — 이미 받은 director 승인이 그 자리를 대신한다.

**채택(design.md §1 에서 대안 A/B/C 비교 후 확정)**: `server/safety/gate.py` 에 새
public 메서드 `execute_preapproved(commands, *, risk=None)` 를 추가한다. `screen()`
과 **동일한 private stage 시퀀스**(`_check_health`→`_stage_grammar`→`_stage_classify`→
`_check_lock`→backup)를 호출하되, `approval_findings` 가 있어도 `self._approval_port`
를 부르지 않고 director 호출자가 이미 가진 `ApprovalBinding` 을 그 자리의 증거로
삼는다. `screen()` 의 **입출력 계약**(관측 가능한 결정·사유·감사 로그)은 바뀌지
않는다 — 다만 (나)의 결론에 따라 `_check_lock` 인접 지점에 중재자 lock 획득/해제가
**내부적으로 추가**되므로, "새 메서드를 나란히 추가할 뿐 screen() 은 한 글자도
안 바뀐다"는 이전 서술은 정정한다: 관측 가능한 동작은 바이트 동일(회귀 0)이지만
내부 구현에는 lock 스테이지가 하나 늘어난다. `@MX:ANCHOR`(353행, REQ-MVP-011/029)의
문면상 "심사 경로가 하나"라는 제약은 공개 메서드 개수가 아니라 심사 파이프라인의
단일성을 보호하는 것으로 읽는다(design.md §1.2) — 두 공개 메서드가 같은 private
스테이지를 호출하는 한 이 ANCHOR 는 위반되지 않는다. 이것이 `gate.py` 가 "LDRECV
전용, 충돌 없음"으로 분류된 이유다(split-proposal §3.1).

**(나) `server/orchestrator/tools.py` 접점 — 확정: 수정하지 않는다.** split-proposal
§3.1 은 `tools.py` 를 "LDCOMPILE(emitter 연결), LDRECV(shared writer)" 로 분류했다.
LDCOMPILE 의 전제(축별 emitter 를 `tools.py` 의 `per_row_timing` 조립 참고용으로
**읽기만** 함)는 확인했다. LDRECV 쪽은 이 보완에서 직접 읽어 확정했다(design.md §2):
`grep -n "gate\.screen(" server/orchestrator/tools.py` 9개 매치 중 실제 호출은
**2366·2368행의 if/else 분기 하나뿐**(주석/문서 인용 7건 제외, 실측 재확인 — 이전
문서가 "9개 실제 호출부"라 적은 것은 grep 매치 수와 실제 호출부 수를 혼동한 오류였다).
같은 패턴(`self._gate.screen(commands) if risk is None else self._gate.screen(commands,
risk=risk)`)이 `server/measurement/runner.py:167`·`server/web/session.py:4691` 에도
있다 — 그중 `session.py` 는 이 SPEC 의 PRESERVE 표(§3.1)가 "쓰지 않는다"로 명시한
파일이다. 따라서 호출부마다 lock 을 감싸는 방식(옛 가설 1)은 채택할 수 없다 —
PRESERVE 위반이 되기 때문이다. **채택하는 가설은 (가)의 `execute_preapproved` 와
기존 `screen()` 이 공유하는 private 스테이지 안에 중재자 lock 을 두는 것(옛 가설
2)이다** — `tools.py`·`session.py`·`measurement/runner.py` 세 호출부 모두 `.screen(`
를 그대로 부르기만 하므로, lock 이 `gate.py` 내부에 있으면 세 파일 중 어느 것도
수정할 필요가 없다. `tools.py` 는 **수정하지 않는다** — 이 결정으로 §2.0-나의
불확정 상태를 닫는다.

**(다) destination occupancy 데이터는 `context.py` 가 아니라 LDRECV 자신의
실행 journal 에 둔다.** `server/director/context.py`(434줄)·`models.py`(304줄)를 직접
읽은 결과 `datapool_id`/`occupancy`/`occupancy_revision`/`Destination` 관련 필드나
타입이 전혀 없고, `ContextObservations.target` 은 타입 없는 `Mapping[str, Any]`로
스키마 검증 없이 통과한다(context.py:134, 205, 242). `context.py` 는 이 SPEC 의
PRESERVE 표(§3)가 "형제 SPEC 소유"로 명시한 파일이므로 이 SPEC 이 직접 쓸 수 없고,
`SPEC-LDSTORE-001` 은 이미 `completed` 로 닫혔다. `server/director/migrations/
001_initial.sql` 자신의 주석(1-8행)이 이미 *"approval 과 execution journal 은 형제
SPEC-LDRECV-001 의 것이므로 여기서 만들지 않는다"*고 적어 이 분리를 예견했다 —
그래서 destination 점유는 `ContextSnapshot.target`(불변, 제출 시점 값)이 아니라
M4 의 `002_execution_journal.sql` 에 LDRECV 소유의 독립 테이블로 추적한다(design.md
§3, 구체 비교는 그곳 참고). M5 의 apply 직전 재검사는 이 테이블을 조회한다 — `spec.md`
§5 표의 "apply 직전 재검사 로직" 판정 방식을 이 결정으로 구체화한다.

### 2.1 얇은 왕복(내부 마일스톤)에서 이 층이 내는 것

감독 결정(2026-09-14, 형제 SPEC 들이 승계)은 여기도 유효하다: 얇은 왕복은 **출시가
아니라 내부 마일스톤**이다. split-proposal §2 얇은 왕복 표는 이 층에 "018 pairing, 020
사람 승인, 021 lock 안 적용, 023 journal (022 중재자 포함 권장, 024·032 유보)"를
요구한다.

이 층이 얇은 왕복에 내는 것은 **M1 + M2 + M3(권장) + M4 + M5 의 lock-안-재검사부**다:

- M1·M2·M4 — 줄일 수 없다. 인증·승인·journal 없이 apply 자체가 존재하지 않는다.
- M3 — 권장이지만 필수는 아니다. 누락하면 왕복은 성립하되 동시 요청 race 가 열린다.
- M5 — **lock 안 재검사(re-check)까지만** 필수다. 실제 콘솔 적용 확인(object-existence
  confirmed)은 콘솔 게이트이므로 얇은 왕복의 관측 대상이 아니다. `unknown+
  recovery_required` 로 정직하게 답하는 것이 이 단계의 왕복 종점이다 — 형제
  `SPEC-LDCOMPILE-001` 이 `blocked` 를 "정직한 종점"으로 삼은 것과 같은 원리다.
- M6 — 유보. 왕복 관측에 필요하지 않다.

## 3. PRESERVE — 건드리지 않는다

| 영역 | 파일 |
|---|---|
| OSC 송신 (서버 유일 표면) | `server/bridge/osc.py` — 이 층은 직접 import 하지 않는다. `SafetyGate.execution_port()` 를 거친다 |
| 3단 안전 게이트 내부 | `server/safety/{grammar,classify,backup,console,monitor,expand,ruleset,blacklist.yaml}.py` — 읽기·호출만. `gate.py` 자체만 EXTEND(§2.0) |
| 기존 일반 승인 채널 | `server/safety/approval.py`, `server/web/approval_bridge.py` — director 승인과 분리 유지(§2). 재설계하지 않는다 |
| 리그·공간 | `server/spatial/{pointing,mib,preflight,presets}.py` |
| 라이브러리 | `server/fx/`, `server/looks/` (FX 22개 · 룩 34개) |
| 예술 producer 둘 | `server/looks/songcue.py`, `server/web/session.py` `_ARC_*` — cutover 는 `SPEC-LDCUTOVER-001` |
| 저장·검증층 | `server/director/{models,store,service,context,knowledge,digest,emit}.py`, `server/director/validate/*.py`, `server/director/knowledge_seed/*.py` — 형제 SPEC 소유. 이 층은 읽고 호출만 |
| 앱 UI 표면 | `ui/src/` — `SPEC-LDUI-001` 소유 |
| 데스크톱 빌드 | `src-tauri/` |
| 기존 LXSEQ/design 경로 | `server/lxseq/*.py`, `server/design/cue_*.py` — 범위 밖 |

### 3.1 공유 파일 직렬화

우산 `plan.md` §2 가 동시 작성을 금지한 넷 — `server/orchestrator/tools.py`,
`server/web/session.py`, `server/web/app.py`, `server/safety/gate.py`.

| 파일 | 이 SPEC 의 처리 |
|---|---|
| `tools.py` | `SPEC-LDCOMPILE-001` 가 이미 닫혔으므로(origin/main `dd3c1121` 계열) 순서 조건은 충족됐다. **확정(design.md §2): 쓰지 않는다** — 중재자 lock 은 `gate.py` 내부에 두므로 `run_commands` 의 `bundle_gate.screen(...)` 호출은 그대로 둔다. 충돌 없음 |
| `session.py` | 쓰지 않는다 — `SPEC-LDUI-001`(projection seam) 전용. 4691행에 `.screen(` 호출이 있으나(design.md §2.2 실측) lock 이 `gate.py` 내부에 있어 이 파일 수정 없이도 직렬화된다. 충돌 없음 |
| `app.py` | 이 SPEC 만 쓴다(director router 등록, M1). 충돌 없음 |
| `gate.py` | 이 SPEC 만 쓴다(새 public 메서드 `execute_preapproved` 추가 + 공유 private 스테이지에 중재자 lock 획득/해제 추가, §2.0-가·나, M3). **`screen()` 의 관측 가능한 입출력 계약(결정·사유·감사 로그)은 바뀌지 않는다**(회귀 0, 기존 gate 테스트 스위트로 확인) — 다만 내부 구현에 lock 스테이지가 하나 늘어난다(§2.0-나에서 정정). 충돌 없음 |

## 4. TDD 순서 (대표 마일스톤 예시)

### M1 (인증·route 골격)

1. **RED** `server/tests/test_director_auth.py`: MCP credential 로 human-only scope
   호출 시도 → 거부(계약 §5 `SCOPE_DENIED`). human credential 로 MCP-only 판단(향후
   확장 여지 검사). Host/Origin 불일치 → `ORIGIN_DENIED`. 만료·철회된 credential →
   `UNAUTHENTICATED`. secret 이 로그/응답/model context 어디에도 노출되지 않는지
   grep 기반 assertion.
2. **RED** `server/tests/test_director_api_routes.py`: 계약 §11 `examples/context.json`
   을 `GET .../context` 로 왕복 — `LDSTORE`/`LDCOMPILE` 을 실제로 호출하는지(mock 아님)
   확인. path/body project/plan ID 불일치 → `IDENTITY_MISMATCH`.
3. **GREEN** `auth.py` + `director_api.py` 최소 구현.
4. **REFACTOR** 인증 미들웨어를 route 공통 자리로 모은다.

### M3 (중재자 + SafetyGate 이음새) — 가장 위험한 마일스톤

1. `tools.py`·`session.py`·`measurement/runner.py` 의 `.screen(` 호출부는 **이미
   확정했다**(design.md §2, 이 문서 §2.0-나) — `tools.py` 는 실제 호출 1곳(2366·2368행
   if/else), `session.py`(4691행)·`measurement/runner.py`(167행)도 동일 패턴이며 세
   파일 모두 **수정하지 않는다**. lock 은 `gate.py` 의 공유 private 스테이지에 둔다.
2. **RED** `server/tests/test_director_arbiter.py`: director 요청이 lock 을 쥔 동안
   동시 chat 요청(또는 그 반대)이 `TARGET_BUSY` 로 거부되는지. lock 해제 후 재시도가
   통과하는지. 오래 대기한 요청이 낡은 승인으로 실행되지 않는지(만료 재검사).
3. **RED** `server/tests/test_director_gate_bridge.py`: `execute_preapproved` 가
   grammar/classify/backup/health/audit 를 그대로 통과하되 `ApprovalPort` 를 부르지
   않는지(mock 으로 호출 0회 단언). 기존 `screen()` 의 관측 가능한 동작이 바이트
   동일하게 유지되는지(회귀) — `tools.py`/`session.py`/`measurement/runner.py` 를 통해
   `screen()` 을 부르는 기존 chat/import 경로가 새 lock 스테이지 추가 후에도 동일하게
   동작하는지 포함.
4. **GREEN** `programmer_arbiter.py` + `gate.py` 의 새 메서드 + 공유 private 스테이지의
   lock 획득/해제.
5. **REFACTOR** 필요 시 `@MX:ANCHOR`/`@MX:REASON` 주석을 두 공개 진입점(`screen()`·
   `execute_preapproved()`)이 같은 심사 파이프라인을 공유한다는 사실을 반영해 갱신한다
   (design.md §1.3 — `tools.py` 접점 배선은 없다, §2 확정).

각 단계마다 `uv run pytest` 전체를 돌려 착수 시점 기준선이 깨지지 않는지 본다(§5).

## 5. 검증 명령

```bash
# 착수 시 기준선 재측정 (로컬 checkout 이 origin/main 보다 뒤져 있었으므로 새로 잰다)
uv run pytest -q

# 이 SPEC 범위 — acceptance.md §3 의 REQ 별 파일 목록과 일치시켰다(plan-audit D4 보완,
# 2026-09-16). test_director_execution.py(옛 이름)는 REQ-023/024 로 세분화된
# test_director_execution_journal.py / test_director_execution_failure.py 로 대체했다.
uv run pytest server/tests/test_director_auth.py server/tests/test_director_evidence_trust.py \
  server/tests/test_director_approvals.py server/tests/test_director_apply_rejection.py \
  server/tests/test_director_gate_bridge.py server/tests/test_director_arbiter.py \
  server/tests/test_director_execution_journal.py server/tests/test_director_execution_failure.py \
  server/tests/test_director_ops_lifecycle.py server/tests/test_director_api_routes.py -q

# 회귀 (기준선 대조 — 숫자는 착수 시 재측정한 값으로 교체)
uv run pytest -q

# 경계: 이 층이 OSC 를 직접 import 하지 않는지 (SafetyGate.execution_port() 를 거친다)
grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/ || echo "OK - no direct OSC import"

# 경계: 예술 producer 를 호출하지 않는지
grep -rnE "^\s*(from|import)\s+server\.(looks|web\.session)" server/director/ || echo "OK - no artistic producer"

# 경계: 기존 일반 승인 채널을 director 자신의 승인으로 재사용하지 않는지
grep -rn "approval_bridge\|DenyAllApprovalPort\|request_approval(" server/director/ \
  || echo "OK - director approval independent of the general WS channel"

# 경계: 저장/검증층(형제 SPEC 소유)을 수정하지 않았는지
git diff --name-only origin/main -- server/director/models.py server/director/store.py \
  server/director/service.py server/director/context.py server/director/knowledge.py \
  server/director/digest.py server/director/emit.py server/director/validate | grep . \
  && echo "FAIL: PRESERVE 위반" || echo "OK"
```

**CI 는 과금 차단으로 죽어 있어 판정 근거가 아니다.** 위 로컬 명령의 출력만 증거로 쓴다.
§5(spec.md) 의 「콘솔 필요 = 예」 항목은 위 명령들로 판정할 수 없다 — 별도 관측 기록이
증거다.

## 6. 중단 조건

- **§2.0-가(SafetyGate 승인 이중화) 의 해석을 사람에게 확인받기 전에 M3 를 시작하지
  않는다.** `gate.py` 에 새 public 메서드를 추가해 기존 `ApprovalPort` 호출을
  건너뛰는 것은 안전장치의 동작을 바꾸는 결정이며, 이 문서 혼자의 판단으로 확정하지
  않는다 — design.md §1 이 대안 비교와 채택 근거를 남겼지만, 사람 확인은 여전히
  M3 착수 전제다(§1).
- **§2.0-다(destination occupancy 저장 위치) 의 결정(design.md §3, LDRECV 자신의
  execution journal 에 독립 테이블로 추적)을 M4 착수 시 재확인한다.** 이 결정은
  코드를 직접 읽어 내렸지만, `context.py`/`models.py`/`001_initial.sql` 세 파일에
  대한 전수 대조는 아니다(§7) — M4 착수 시 스키마 세부(컬럼·인덱스)를 확정하며 이
  방향 자체가 틀렸다고 판명되면 중단하고 재조정한다.
- 계약 §4·§9·§10 과 구현이 어긋나는 것이 발견되면 **중단하고 보고한다.** 계약이 단일
  원본이므로 자식이 임의로 다르게 구현하지 않는다.
- `SPEC-LDSTORE-001`(`PlanRecord`/`ContextSnapshot`) 또는 `SPEC-LDCOMPILE-001`
  (`ValidationReport`/`emit_compiled`)의 실제 shape 이 이 문서가 가정한 것과 다르면
  중단하고 조정한다 — 이 문서는 두 형제의 코드를 읽었지만 전수 대조는 아니다(§7).
- **§2.0-나(`tools.py`·`session.py`·`measurement/runner.py` 세 호출부는 수정하지
  않는다, design.md §2)의 전제 — 세 파일이 같은 `SafetyGate` 인스턴스를 공유한다 —
  가 M3 착수 시 조사로 반증되면(별도 인스턴스라면), lock 을 모듈 레벨 공유 객체로
  바꿔야 하므로 착수를 중단하고 재설계한다(design.md §2.4).**

## 7. 미검증 (착수 전 남은 것)

- **우산 `contract.md` §4(APP human routes) 는 이 문서 작성 시 전문을 읽었으나, §9(hash)·
  §10(state machine)은 스키마 조항 대조까지는 하지 않았다.** M2·M4 착수 시 다시 읽어
  `ApprovalBinding`/idempotency fingerprint 계산을 그 원문과 줄 단위로 대조한다.
- **`server/director/context.py`(434줄)·`store.py`(276줄)·`digest.py`(81줄)를 전문
  읽지 않았다.** destination/occupancy 필드가 없다는 것은 확인했다(design.md §3 —
  `context.py`/`models.py`/`001_initial.sql` grep + 관련 구간 실측). revision CAS
  API·digest 계산 함수의 정확한 시그니처는 여전히 M1·M4·M5 착수 시 확인한다.
- **`server/safety/gate.py` 의 `_check_lock`·`_stage_classify`·`_check_health` 세
  private 메서드 본문을 전문 읽지 않았다.** `screen()`(358-475행) 전체 흐름은 이번
  보완에서 읽었지만, 세 private 메서드 내부 구현까지는 아니다. `execute_preapproved`
  가 이들을 그대로 재사용할 수 있는지, 그리고 중재자 lock 을 정확히 어느 지점(예:
  `_check_lock` 직후 신설 스테이지)에 넣을지는 M3 착수 시 확정한다(design.md §1.3,
  §4).
- **`server/web/session.py:4691`·`server/measurement/runner.py:167` 의 `.screen(`
  호출부가 `tools.py` 와 같은 `SafetyGate` 인스턴스를 공유하는지 확인하지 않았다.**
  design.md §2 의 "세 호출부 모두 수정 불필요" 결론은 이 공유 전제 위에 서 있다 —
  M3 착수 시 먼저 확인한다(design.md §2.4, 이 문서 §6).
- **LOC 추정 없음.** Tier L 로 잡았으나(§1.1, spec.md — REQ 개수 8건은 Tier S 한도
  안이지만 신규 파일 5개 + 공유 파일 3개(EXTEND) + 콘솔 게이트 2건의 규모로 판단),
  실제 구현 규모는 재지 않았다.
- **계획 내용에 대한 독립 판정 없음.** 두 형제 SPEC 모두 `plan-auditor` 가 이 저장소에서
  착수 전 컨텍스트 초과로 죽는다고 기록했다(LDSTORE `progress.md` §F 실측 ≈114K 토큰).
  이 SPEC 에 대한 plan-audit 이 같은 이유로 죽으면, 오케스트레이터 자기 검수임을
  숨기지 않고 기록한다.
- **로컬 checkout 이 origin/main 보다 6 커밋 뒤져 있었다(이 문서 작성 시점 실측).**
  이 계획은 `git show origin/main:...` 으로 형제 SPEC 코드를 읽어 작성했다. 실제 구현
  착수 전에 로컬 checkout 을 origin/main 과 동기화해야 한다(`main-checkout-branch-guard.md`
  가 금지하는 `git switch`/`reset --hard` 가 아니라, 워크트리 격리 또는 정상적인
  fast-forward 로 — 이 결정은 오케스트레이터의 사전 동기화 절차에 맡긴다).
