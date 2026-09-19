---
id: SPEC-LDWIRE-001
title: "Director HTTP 운영 배선 — 자격증명 발급·ContextProvider·ValidationProvider·DirectorApiDeps 조립"
version: "0.1.0"
status: in-progress
created: 2026-09-19
updated: 2026-09-19
author: jaihyun
priority: P1
phase: "Lighting Director v1.0 target"
module: "server/director"
lifecycle: spec-anchored
tags: "lighting-director, auth, context-provider, validation-provider, deps-assembly, serve-wiring"
tier: L
depends_on: [SPEC-LDRECV-001, SPEC-LDSEND-001, SPEC-LDSTORE-001, SPEC-LDCOMPILE-001]
related_specs: [SPEC-LDPLUGIN-001]
---

# SPEC-LDWIRE-001

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-09-19 | 최초 작성. 큐 카드 t421("LDRECV 후속 B: director HTTP 운영 배선") — `SPEC-LDRECV-001`·`SPEC-LDSEND-001`·`SPEC-LDSTORE-001`·`SPEC-LDCOMPILE-001` 네 SPEC 모두 `status: completed`·`origin/main` merge 확인(`01c81fa8` 기준 로컬 checkout 실측) 후 착수. 이 SPEC 은 `SPEC-LDPLUGIN-001` 을 쪼갠 원래 "여섯 자식"(우산 분할 시점 목록)에 속하지 않는다 — 네 완료 형제가 각각 남긴 배선 seam 이 프로덕션 `server/web/serve.py` 에서 실제로 연결된 적이 없다는 사실이 실측(§1)으로 드러나, 그 gap 을 닫기 위한 후속 SPEC 이다. |

## 1. 목적과 경계

`server/director/director_api.py` 의 `DirectorApiDeps`/`build_director_router()`, `server/web/app.py` 의 `WebDeps.director` 필드, 그리고 `run_director_apply()`(`SPEC-LDSEND-001`)까지 — director HTTP 층을 구성하는 조각은 이미 전부 존재하고 각자 자신의 SPEC 에서 pytest 로 검증됐다. 그런데 **프로덕션 기동 경로(`server/web/serve.py` `main()` → `WebDeps(...)` → `create_app(deps)`)는 이 조각들을 한 번도 실제로 조립한 적이 없다** — 실측(아래 §1.1)으로 확인했다: `WebDeps.director` 는 정의된 이후 오늘까지 프로덕션 `serve.py` 어디에서도 값이 채워지지 않았고, 기본값 `None` 그대로 남아 있다. 그 결과 `app.py` `create_app()` 의 `if deps.director is not None: app.include_router(build_director_router(deps.director))` 분기가 실제로 실행된 적이 없다 — director HTTP 표면(`/api/director/v1/...`) 전체가 오늘 배포된 앱에는 마운트되지 않는다.

이 SPEC 은 그 **조립과 기동 배선**만을 다룬다 — 이미 완료된 네 형제가 만든 컴포넌트의 동작(승인 규칙, 검증 규칙, apply 재검사, bundle 전송)을 바꾸지 않는다. 다만 그 조립을 완결하려면 **오늘 어떤 프로덕션 구현도 갖지 못한 seam 셋**을 새로 채워야 한다는 것이 실측으로 드러났다(§1.2) — 이것이 이 SPEC 의 실제 구현 대상이다.

### 1.1 실측 — 오늘 무엇이 있고 무엇이 없는가

| 컴포넌트 | 상태 | 근거 |
|---|---|---|
| `DirectorApiDeps`/`build_director_router()` | 존재, 완결 | `server/director/director_api.py`(481줄) — 10개 route 전부 배선됨(`grep -c "^    @router\." server/director/director_api.py` 실측) |
| `WebDeps.director: DirectorApiDeps \| None = None` | 존재, **프로덕션에서 항상 `None`** | `server/web/app.py:253`; `server/web/serve.py:377-432` 의 `WebDeps(...)` 호출부 실측 — `director=` 키워드가 없다 |
| `run_director_apply()`(apply 판정 공유 함수) | 존재, 완결 | `server/director/execution.py` — `SPEC-LDSEND-001` |
| `GateBundleSender`(실제 콘솔 송신) | 존재, 완결 | `server/director/execution.py` — `SPEC-LDSEND-001`; `server/tools/director_apply_observe.py` 가 프로덕션과 무관한 로컬 관측 하네스로 이미 실사용 중(그 SPEC §1 규범표) |
| `ApplyCoordinator(journal, approvals, store, gate)` 프로덕션 생성 지점 | **없음** | `grep -rn "ApplyCoordinator("` → `server/tools/director_apply_observe.py`(관측 하네스, `server/web/serve.py` 조립과 무관) 한 곳뿐 |
| `Credential(...)` 프로덕션 생성 지점 | **없음** | `grep -rn "Credential("` → `server/tests/test_director_{approvals,ops_lifecycle,auth}.py` 세 시험 파일뿐 |
| `ContextProvider` 실물 구현 | **없음** | `grep -rn "ContextProvider"` → `director_api.py`(Protocol 선언)와 `server/tests/test_director_{approvals,ops_lifecycle}.py` 의 `_FakeContextProvider`/`_StubContextProvider` 뿐 |
| `ValidationProvider` 실물 구현 | **없음** | `grep -rn "ValidationProvider"` → `director_api.py`(Protocol 선언)와 `server/tests/test_director_approvals.py` 의 `_StubValidationProvider` 뿐 |
| `PipelineValidator`(LDCOMPILE 실제 검증기) 프로덕션 주입 | **없음** | `grep -rn "PipelineValidator("` → 정의 자리(`server/director/validate/pipeline.py`)와 그 파일 자신의 시험뿐. `DirectorService.__init__` 은 `validator=None` 이면 `NotInstalledValidator()`(항상 `blocked`)로 대체한다(`server/director/service.py:81`) |
| `validation_id` 로 `ValidationReport` 를 되찾는 저장소 | **없음** | `server/director/store.py:38` 자신의 주석: `` `validation_id`·`approval_id`·`execution_id` 는 아직 없는 관계이므로 생략된다 `` — `DirectorService.submit()` 이 돌려주는 `SubmitResult.validation` 에도 `validation_id` 필드가 없다(`service.py` `SubmitResult`/`submit()` 실측) |

### 1.2 이 SPEC 이 실제로 만드는 것 — 세 개의 새 seam

1. **운영 자격증명 발급 경로** — `CredentialRegistry`/`PairingSecretStore` 로 `plan:apply` 를 포함한 human-only scope 를 가진 app-human `Credential` 을 실제로 만들어 등록하고, secret 을 OS credential store 에 심는 절차. 오늘은 이 절차가 시험 헬퍼(`server/tests/test_director_auth.py` `_issue()`)에만 있다.
2. **`ContextProvider`/`ValidationProvider` 실물** — `director_api.py` 가 선언한 두 Protocol 을 실제 서버 상태에서 채우는 구현. `ContextProvider` 는 `SPEC-LDSTORE-001` 이 이미 만든 `server/director/context.py`(snapshot **조립**)를 소비하되, 그 모듈이 스스로 밝히듯 "관측을 수행하는 것은 이 층의 일이 아니다" — 그 관측(무엇을 `ContextObservations` 에 채울지)을 이 SPEC 이 프로덕션에서 처음 연결한다. `ValidationProvider` 는 `PipelineValidator` 를 `plan:validate`/`plan:submit` 경로에 실제로 주입하고, `validation_id` 로 되찾을 수 있는 저장을 새로 만든다(오늘 부재 — §1.1).
3. **`DirectorApiDeps` 조립 + `serve.py` 기동 배선** — 위 두 seam 과 이미 완료된 `ApplyCoordinator`/`ExecutionJournal`/`GateBundleSender`(`SPEC-LDSEND-001`)를 하나의 `DirectorApiDeps` 로 묶고, `server/web/serve.py` 의 `WebDeps(...)` 호출에 `director=` 로 주입한다.

이 세 가지 중 (1)과 (2)는 **오늘 이 저장소 어디에도 프로덕션 구현이 없는 새 설계 결정**을 필요로 한다 — plan.md §2.0/design.md 가 그 결정을 다룬다. (3)은 기계적 조립이지만, `director_api.py` 자신의 docstring 이 명시한 스레드 제약(§3 REQ-LDWIRE-007)을 지켜야 한다.

## 2. 범위 결정

- **판단·검증 로직은 바꾸지 않는다.** `ApplyCoordinator`(재검사)·`execute_bundles()`(전송·상태 매핑)·`authenticate()`(인증 규칙)·`PipelineValidator`(검증 규칙)의 동작은 이 SPEC 의 범위 밖이다 — 이미 각자의 SPEC 이 완결했다. 이 SPEC 은 그것들을 **연결**할 뿐이다.
- **자격증명 발급은 app-human audience 만 다룬다.** `aud=director-mcp` (MCP credential) 발급 경로는 이 SPEC 의 범위가 아니다 — 카드 t421 이 명시한 것은 `plan:apply`(human-only scope)이고, `lighting-director` 플러그인의 MCP adapter 자체는 미작성 형제 `SPEC-LDHOST-001`(우산 §1.1 각주) 소유다.
- **`ContextProvider` 는 관측 가능한 만큼만 채운다.** `context.py` 의 아홉 축(§1.2) 전부가 snapshot 에 있어야 하지만, 오늘 서버가 실제로 관측할 수 있는 축과 아직 관측 수단이 없는 축이 다르다 — 후자는 그 모듈이 이미 마련한 정직한 미관측 상태(`unreadable`/`unconfirmed`/`absent` 류)로 채운다. 값을 지어내지 않는다(값을 지어내면 `SPEC-LDSTORE-001` 의 "못 읽은 값을 승격하지 않는다" 불변식을 이 SPEC 이 깨는 것이 된다).
- **`ExecutionProvider`/`FeedbackProposalService` 는 이 SPEC 의 범위가 아니다.** `director_api.py` 자신의 docstring 이 "각각 M4 durable execution journal, M2 사람 승인/feedback 저장소"라고 이미 못박았다 — `GET execution`/`POST feedback-proposals` 는 이 SPEC 이후에도 503 을 계속 답한다.
- **t422(목적지 예약 해제)와는 분리한다.** 큐에 있는 형제 카드 t422("파샬 실패 후 destination-reservation 해제")는 `ApplyCoordinator`/`ExecutionJournal` 의 재검사 로직 자체를 다루는 별도 관심사다 — 이 SPEC 이 그 로직을 조립에 끌어다 쓰긴 하지만, 그 로직을 바꾸지 않는다.
- **credential 영속성 범위는 매 기동 재발급으로 확정됐다(design.md §(가), 2026-09-19 사용자 확인).** `CredentialRegistry` 는 오늘 순수 in-memory dict 다(`server/director/auth.py:135-136` 실측 — 영속화 없음). 이 SPEC 은 그 사실을 그대로 두고 매 기동마다 새로 발급하는 설계를 채택한다 — 별도 영속화는 이 SPEC 의 범위가 아니다. 서버 재기동 시 등록된 credential 이 전부 사라지며, 운영자는 매 재기동마다 재페어링해야 한다(수용된 trade-off).

### Out of Scope — 판단·검증 로직 변경

- `ApplyCoordinator` 의 재검사 순서·조건, `execute_bundles()` 의 상태 매핑, `authenticate()` 의 인증 규칙, `PipelineValidator` 의 검증 stage 내용은 변경하지 않는다 — 전부 선행 완료 SPEC 소유다.
- `POST /validations`(무저장 재검증)·`PUT plan`(제출) 의 계약 형태(요청/응답 스키마)는 바꾸지 않는다 — `PipelineValidator` 를 실제로 주입할 뿐이다.

### Out of Scope — 미작성 형제·별도 카드

- `aud=director-mcp` MCP credential 발급, MCP adapter 자체는 포함하지 않는다 — `SPEC-LDHOST-001`(미작성) 소유.
- `GET execution`/`POST feedback-proposals` 의 실물 배선(durable execution journal 조회, feedback 저장소)은 포함하지 않는다 — 각각 `director_api.py` 자신이 명시한 대로 별도 마일스톤/SPEC 소유이며, 이 SPEC 종료 후에도 503 을 유지한다.
- 큐 카드 t422(파샬 실패 후 destination-reservation 해제)는 포함하지 않는다 — `ApplyCoordinator`/`ExecutionJournal` 재검사 로직 자체의 변경이 필요한 별도 관심사다.
- 두 기존 예술 producer(`server/looks/songcue.py`, `server/web/session.py` 의 `_ARC_*`)의 director 경로 cutover 는 포함하지 않는다 — `SPEC-LDCUTOVER-001`(미작성) 소유.

## 3. 안정 요구사항

`SHALL` 은 필수다.

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDWIRE-001 | **When** 서버가 기동하거나 운영자가 명시적으로 재발급을 요청하면, 서버는 **SHALL** `APP_HUMAN_SCOPES` 를 가진 app-human `Credential` 을 발급하여 `CredentialRegistry` 에 등록하고 secret 을 `PairingSecretStore` 에만 저장하며, 그 secret 을 이 최초 발급 표면 밖의 어떤 로그·오류 응답·model context 에도 평문으로 남기지 않는다. | REQ-LDPLUGIN-018; `auth.py` `Credential`/`CredentialRegistry`/`PairingSecretStore` |
| REQ-LDWIRE-002 | 발급된 credential 의 secret 은 **SHALL NOT** 구조화 로그·`ExchangeError` 응답·audit 기록에 나타나며, 그 기록들에는 `credential_id`·scope·발급/만료 시각 같은 메타데이터만 나타난다. | REQ-LDPLUGIN-018 상속 — `Credential` 은 애초에 secret 필드를 갖지 않는다(`auth.py:96-111`) |
| REQ-LDWIRE-003 | **Where** 아직 유효한 credential 이 하나도 발급되지 않았으면(신규 설치·최초 기동), director HTTP route 는 **SHALL** 기존 `authenticate()` 의 `401 UNAUTHENTICATED` 를 그대로 답하고, 이 SPEC 의 발급 경로가 그 fail-closed 동작을 우회하는 별도 경로를 만들지 않는다. | `auth.py` `authenticate()`; REQ-LDPLUGIN-018 |
| REQ-LDWIRE-004 | 서버는 **SHALL** `GET context`/`GET knowledge` 에 실제 `ContextProvider` 를 배선하고, 그 구현이 반환하는 snapshot 은 `context.py` `NINE_AXES` 아홉 축 전부를 채우되, `identity`/`expiry`/`policy` 세 축은 실제 관측 소스로 채우고 나머지 여섯 축(`show`/`audio`/`group_membership`/`preset_content`/`compiler`/`capability`)은 그 축의 기존 정직한 미관측 상태(예: `unreadable`/`unconfirmed`/`absent`)로 채우며 값을 지어내지 않는다(design.md §라, 2026-09-19 확정 — 여섯 축의 관측 배선은 이 SPEC 의 범위 밖). | `context.py` `build_snapshot`/`NINE_AXES`; REQ-LDPLUGIN-004 |
| REQ-LDWIRE-005 | **When** `GET context` 가 반복 호출되고 원본(source) 상태와 live binding 이 그대로이며 만료 전이면, 서버는 **SHALL** 같은 `context_id`/`context_digest` 의 current snapshot 을 반환하고 `created_at` 만 갱신한다 — 매 호출이 새 context 를 발행해 대기 중인 plan 을 조용히 stale 로 만들지 않는다. | 우산 `contract.md` §6.1; `context.py` `should_reissue` |
| REQ-LDWIRE-006 | **When** `PUT plan` 으로 계획이 제출되면, 서버는 **SHALL** `SPEC-LDCOMPILE-001` 의 `PipelineValidator` 를 검증 seam 에 실제로 주입하여(`NotInstalledValidator` 대체) 그 결과(`outcome`/`diagnostics`/`compiled`)를 **SHALL** 안정된 `validation_id` 로 저장하고, 이후 같은 `validation_id` 로 조회하면 제출 시점과 동일한 `ValidationReport` 를 돌려준다. | `service.py` `DirectorService.submit`; `validate/pipeline.py` `PipelineValidator`; 우산 `contract.md` §3 `GET P/validations/{validation_id}` |
| REQ-LDWIRE-007 | 서버는 **SHALL** `POST .../approvals` 가 참조하는 `ValidationProvider.get(project_id, validation_id)` 를 REQ-LDWIRE-006 의 저장소에 배선하여, 존재하지 않거나 다른 project 의 `validation_id` 조회는 계약이 정한 오류로 정직하게 거절한다(값을 지어내지 않는다). | `director_api.py` `ValidationProvider`/`post_approval`; `approvals.py` |
| REQ-LDWIRE-008 | 서버는 **SHALL** 이미 완료된 `ApplyCoordinator`·`ExecutionJournal`·`GateBundleSender`(`SPEC-LDSEND-001`)와 REQ-LDWIRE-001·004·006 의 결과를 **정확히 하나의** `DirectorApiDeps` 인스턴스로 조립하며, 앱의 나머지 부분과 별개의 `SafetyGate` 나 별개의 OSC 송신 경로를 새로 만들지 않는다 — 조립은 이미 `server/web/serve.py` 가 구성한 `stack.gate`/`stack.registry`/`stack.audit` 를 그대로 재사용한다. | `director_api.py` `DirectorApiDeps`; `execution.py` `ApplyCoordinator`/`GateBundleSender`; `serve.py` `build_console_stack` 조립부 |
| REQ-LDWIRE-009 | **When** `server/web/serve.py` 가 `WebDeps` 를 구성하면, 서버는 **SHALL** REQ-LDWIRE-008 의 `DirectorApiDeps` 를 `WebDeps.director` 로 주입하여 `create_app()` 이 `build_director_router()` 를 프로덕션 앱에 실제로 마운트하게 한다. | `app.py` `WebDeps.director`/`create_app`; `serve.py` `WebDeps(...)` 호출부 |
| REQ-LDWIRE-010 | **When** director 조립이 `DirectorStore`/`ExecutionJournal`(둘 다 `sqlite3.connect()` 기반)을 생성하면, 서버는 **SHALL** 그 생성을 FastAPI event-loop 스레드에서 수행하고 별도 스레드·프로세스 풀에서 수행하지 않는다 — 어기면 `sqlite3.ProgrammingError`(다른 스레드에서 만들어진 객체 사용)가 실기에서 재현된다(`director_api.py` 모듈 docstring 이 이미 문서화한 제약). | `director_api.py` build_director_router 상단 주석; `store.py`/`execution.py` `sqlite3.connect(...)` |

## 4. 비목표

(§2 의 Out of Scope 참고 — REQ 표와 중복 서술하지 않는다.)

## 5. 검증 수단의 한계 (착수 전 고지)

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이 유일한 자동 판정 근거다(선행 네 형제가 남긴 것과 같은 제약). 기준선은 착수 시점에 재측정한다.

**이 SPEC 은 콘솔 게이트가 아니다.** 위 REQ 열 개는 전부 "조립과 배선이 올바른가"를 다루며, 조립 대상 컴포넌트 자신의 콘솔 동작(실제 apply·전송·readback)은 이미 `SPEC-LDRECV-001`/`SPEC-LDSEND-001` 이 각자의 방식으로(로컬 pytest + 부분 콘솔 관측) 검증했다 — 이 SPEC 은 그 컴포넌트를 재검증하지 않고, 프로덕션 `serve.py` 가 그것들을 실제로 연결했는지만 시험한다(예: `TestClient(create_app(real_serve_deps))` 로 director 라우트가 실제로 마운트됐는지, 발급된 credential 로 실제 인증이 통과하는지).

| 판정 | 수단 | 콘솔 필요 |
|---|---|---|
| credential 발급·secret 격리·재발급 거부(001~003) | 합성 입력 + pytest (`_neutralize_os_keyring` in-memory keyring) | 아니오 |
| ContextProvider 아홉 축 충족·재발급 억제(004~005) | fake/합성 관측 소스 + pytest | 아니오 |
| ValidationProvider 저장·조회·PipelineValidator 실제 주입(006~007) | 합성 plan + pytest | 아니오 |
| DirectorApiDeps 조립·serve.py 배선(008~009) | `create_app(real_deps)` 를 `TestClient` 로 구동 + pytest — 실제 `main()` 조립 경로를 최대한 재사용 | 아니오 |
| 스레드 제약 준수(010) | 조립 코드가 event-loop 스레드 안에서 실행됨을 구조로 보장(`async def` lifespan 패턴, 기존 route 시험이 이미 이 패턴을 씀) + pytest | 아니오 |
