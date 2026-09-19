# 인수 기준 — SPEC-LDWIRE-001

[요구사항](spec.md) · [설계 결정](design.md) · [계획](plan.md)

## 1. Given-When-Then 시나리오

### AC-LDWIRE-001 — 운영 자격증명 발급 + secret 비노출

**Given** 서버가 새로 기동했고 아직 credential 이 등록되지 않았다
**When** 발급 절차(REQ-LDWIRE-001)가 실행되면
**Then** `CredentialRegistry` 에 `APP_HUMAN_SCOPES` 를 가진 `Credential` 하나가
등록되고, `PairingSecretStore.get(credential_id)` 로 조회한 secret 이 그
credential 의 bearer 인증을 실제로 통과시키며, 그 발급 절차의 반환값/로그
어디에도 secret 원문이 발급 표면 밖으로 노출되지 않는다.

### AC-LDWIRE-002 — secret 은 구조화 로그·오류 응답에 나타나지 않는다

**Given** 위 발급이 끝났다
**When** 잘못된 secret 으로 인증을 시도해 `authenticate()` 가 `ExchangeError` 를
던지면
**Then** 그 오류 envelope 의 어떤 필드에도 올바른 secret 값이 포함되지 않는다
(발급 절차·`Credential` dataclass 어느 쪽도 secret 필드를 갖지 않는다는 구조적
보장을 재확인한다).

### AC-LDWIRE-003 — credential 부재 시 fail-closed 유지

**Given** 아직 아무 credential 도 발급되지 않은 상태(신규 설치 시뮬레이션 —
빈 `CredentialRegistry`)
**When** director HTTP route 에 유효하지 않은 Authorization 헤더로 요청한다
**Then** 서버는 `401 UNAUTHENTICATED` 를 답하며, 이 SPEC 의 발급 경로가 만든
어떤 우회 경로도 그 요청을 통과시키지 않는다.

### AC-LDWIRE-004 — `ContextProvider` 가 아홉 축 전부를 채운다(세 축 실관측 + 여섯 축 정직한 미관측)

**Given** `identity`/`expiry`/`policy` 세 축에 실제 관측 소스가 배선된
`ContextProvider`(design.md §라, 2026-09-19 확정 범위)
**When** `GET .../context` 를 호출하면
**Then** 응답 snapshot 은 `context.py` `NINE_AXES` 가 나열한 최상위 key 전부를
포함하고, `identity`/`expiry`/`policy` 축은 실제 값을, 나머지 여섯 축
(`show`/`audio`/`group_membership`/`preset_content`/`compiler`/`capability`)은
그 축의 기존 정직한 미관측 상태(값을 지어내지 않음)를 담는다 —
`missing_axes(snapshot)` 가 빈 튜플을 반환한다(모든 축이 최소한 "정직한
미관측 상태"로라도 존재).

### AC-LDWIRE-005 — 반복 `GET context` 는 pending plan 을 stale 로 만들지 않는다

**Given** 어떤 plan 이 현재 `context_id`/`context_digest` 에 바인딩된 채
`ready_for_review` 상태로 대기 중이다
**When** 원본 상태가 바뀌지 않은 채 `GET .../context` 를 다시 호출하면
**Then** 새 응답의 `context_id`/`context_digest` 는 이전과 동일하고
`created_at` 만 달라지며, 대기 중이던 plan 의 바인딩은 여전히 current 로
남는다(REQ-LDWIRE-005, `should_reissue()` 가 `False`).

### AC-LDWIRE-006 — `PUT plan` → `ValidationReport` 저장 → `validation_id` 로 재조회

**Given** `PipelineValidator` 가 실제 검증 seam 에 주입된 서버
**When** 유효한 plan 을 `PUT .../plans/{plan_id}` 로 제출하면
**Then** 응답의 `validation` 이 `PipelineValidator.validate()` 가 계산한
`outcome`/`diagnostics`/`compiled` 를 그대로 담고, 그 제출이 발급한
`validation_id` 로 `deps.validation_provider.get(project_id, validation_id)` 를
호출하면 제출 시점과 바이트 동일한 `ValidationReport` 가 돌아온다.

### AC-LDWIRE-007 — 존재하지 않는/다른 project 의 `validation_id` 는 정직하게 거절

**Given** project `A` 에서 발급된 `validation_id`
**When** project `B` 의 컨텍스트로 그 `validation_id` 를 `POST .../approvals`
본문에 실어 요청하면
**Then** 서버는 그 validation 을 존재하는 것처럼 승격하지 않고 계약이 정한
오류로 거절한다(값을 지어내지 않는다).

### AC-LDWIRE-008 — `DirectorApiDeps` 조립이 기존 `SafetyGate`/`OSC` 경로를 재사용한다

**Given** `server/web/serve.py` 가 `build_console_stack()` 으로 만든 `stack`
**When** director 조립(REQ-LDWIRE-008)이 실행되면
**Then** 조립된 `ApplyCoordinator.gate`/`GateBundleSender` 가 참조하는 객체는
`stack.gate`/`stack.gate.execution_port` 와 **동일 인스턴스**이며, 별도의
`SafetyGate` 나 별도의 `OscBridge` 가 새로 생성되지 않는다(identity 비교로
검증 — `is` 비교).

### AC-LDWIRE-009 — `serve.py` 가 실제로 `director=` 를 주입하고 라우트가 마운트된다

**Given** `server/web/serve.py` 의 실제 조립 경로(또는 그 조립을 그대로 구동하는
테스트 wrapper)
**When** `create_app(deps)` 를 호출하면
**Then** `deps.director` 는 `None` 이 아니며, 반환된 FastAPI 앱의 `app.routes`
경로 집합이 `build_director_router()` 가 배선한 10개 route 경로(prefix
`/api/director/v1/projects/{project_id}`) 전부를 부분집합으로 포함한다 —
`GET .../context`, `GET .../knowledge`, `GET .../plans/{plan_id}`,
`POST .../plans/{plan_id}/revisions/{revision}/approvals`,
`POST .../plans/{plan_id}/revisions/{revision}/rejections`,
`POST .../validations`, `PUT .../plans/{plan_id}`,
`POST .../plans/{plan_id}/revisions/{revision}/apply`,
`GET .../executions/{execution_id}`, `POST .../feedback-proposals`
(경로 리스트를 (method, path) 튜플 집합으로 비교 — 바레 개수가 아니라 각
경로의 실제 존재를 단언하여, route 가 추가·제거될 때 이 AC 가 조용히 낡은
숫자로 남는 것을 막는다).

### AC-LDWIRE-010 — 발급된 credential 로 프로덕션 경로에서 실제 인증이 통과한다

**Given** AC-LDWIRE-009 로 마운트된 앱과 M5 에서 발급된 credential
**When** 그 credential 의 bearer token 으로 `GET .../context` 를 요청하면
**Then** `401`/`403` 없이 `200`(또는 관측 소스가 아직 없는 축만 정직한
미관측 상태로 채운 유효 snapshot)이 돌아온다 — §1.1 이 실측한 "director HTTP
표면이 오늘 배포된 앱에 마운트되지 않는다" gap 이 닫혔다는 end-to-end 증거다.

### AC-LDWIRE-011 — `DirectorStore`/`ExecutionJournal` 생성이 event-loop 스레드 안에서 일어난다(REQ-LDWIRE-010)

**Given** `DirectorApiDeps` 조립이 FastAPI `lifespan`(`async def`) 컨텍스트
안에서 `DirectorStore`/`ExecutionJournal` 을 생성하는 구조(`server/tests/
test_director_ops_lifecycle.py` `client` fixture 의 `_lifespan` 패턴을 프로덕션
조립에도 그대로 적용 — `route_store = DirectorStore(db_path)` 가 `async def
_lifespan(app: FastAPI)` 본문 안에서 호출되고, handler 는 전부 `async def`
여서 FastAPI 가 별도 threadpool(`run_in_threadpool`)로 보내지 않는다)
**When** `TestClient(app)` 로 director 라우트에 연속 요청을 보내 sqlite 기반
객체(`DirectorStore`/`ExecutionJournal`)를 실제로 사용하면
**Then** `sqlite3.ProgrammingError: SQLite objects created in a thread can
only be used in that same thread.` 가 발생하지 않는다 — 조립 코드의 route
handler 가 전부 `async def` 임을 구조로 확인하고(`grep -n "def "
<신규 조립 모듈>` 로 `def`(동기) handler 부재를 확인), 실제 요청 시퀀스가
예외 없이 완료됨을 pytest 로 관측한다(`director_api.py` 모듈 docstring 156-159
행이 이미 문서화한 스레드 제약의 회귀 방지).

**REQ↔AC 추적**: REQ-LDWIRE-010 ↔ AC-LDWIRE-011.

## 2. 엣지 케이스

- 서버가 재기동돼 `CredentialRegistry` 가 비워진 뒤, 재기동 전에 발급된
  bearer token 으로 요청하면 `401`(새로 발급된 credential 이 아니므로) —
  design.md §가 확정 채택(대안 A, 2026-09-19 확정)의 의도된 동작.
  `validation_id` 가 만료된 뒤 조회하면 계약이 정한 만료 오류를 답하고 값을
  지어내지 않는다 — **만료 정책(TTL 의 정확한 값·산식)은 M2 구현 시 확정한다**
  (design.md §나·REQ-LDWIRE-006 어느 쪽도 구체적인 TTL 값을 규정하지 않는다 —
  이 SPEC 은 "만료가 존재하고 만료 후 정직하게 거절한다"는 동작만 요구하며,
  정확한 시간 산식은 plan.md M2 구현 결정 사항이다).
- `ContextProvider` 가 관측 소스를 갖지 못한 여섯 축(`show`/`audio`/
  `group_membership`/`preset_content`/`compiler`/`capability` — design.md
  §라, 2026-09-19 확정 범위)에 대해 `GET context` 를 호출해도 서버가 예외로
  죽지 않고 그 축을 정직한 미관측 상태로 채운 유효 응답을 계속 돌려준다.
- 두 개의 서로 다른 `project_id` 가 동시에 `PUT plan` 을 제출해도 각자의
  `validation_id` 가 서로 뒤섞이지 않는다(project 경계 격리).

## 3. 품질 게이트 기준

- `uv run pytest server/tests/test_director_*.py` 전부 PASS (기존 24개 파일 +
  이 SPEC 이 추가하는 신규 파일).
- 신규 코드 커버리지 ≥ 85% (TRUST 5 Tested 원칙).
- `grep -rn "AskUserQuestion" server/director/ server/web/serve.py` 무매치
  (subagent 경계 — 이 코드는 사람과 직접 상호작용하지 않는다).
- `PipelineValidator`/`NotInstalledValidator` 어느 쪽도 이 SPEC 의 구현으로
  인해 기존 시험이 깨지지 않는다(회귀 없음).

## 4. Definition of Done

- [ ] REQ-LDWIRE-001~010 전부 PASS 증거(명령 + 검증한 출력)와 함께 보고됨
- [ ] design.md 의 네 가지 인터페이스 결정(plan.md §2, 2026-09-19 확정)이
  Implementation Kickoff Approval 전체 게이트(plan-auditor 검토 포함)를
  통과함
- [ ] `server/web/serve.py` 의 `WebDeps(...)` 호출에 `director=` 가 실제로
  나타남(`grep -n "director=" server/web/serve.py` 매치 ≥ 1)
- [ ] `ContextProvider`/`ValidationProvider` 실물 구현이 신규 모듈에 존재하고
  `director_api.py` 의 Protocol 을 만족함(타입 체크 또는 실행 시 duck-typing
  확인)
- [ ] t422(destination-reservation 해제)의 로직에 손대지 않았음을 diff 로
  확인
- [ ] 관련 4개 선행 SPEC(`LDRECV`/`LDSEND`/`LDSTORE`/`LDCOMPILE`)의 기존 시험
  전부 여전히 PASS(회귀 없음)
