# 설계 결정 — SPEC-LDWIRE-001

[요구사항](spec.md) · [계획](plan.md) · [인수](acceptance.md)

이 문서는 `SPEC-LDRECV-001`/`SPEC-LDSEND-001` 의 선례를 따라, 되돌리기 비싸거나
기존 안전장치·저장 스키마 경계와 맞닿은 seam 결정만 다룬다 — 우산
`SPEC-LDPLUGIN-001` 의 `design.md` 를 대체·복제하지 않는다. plan-audit 단계에서
아래 각 결정의 재검토를 요청한다; 사람 검토자가 다른 판단을 하면 뒤집을 수 있다.

## (가) 운영 자격증명의 수명 — 매 기동 재발급 vs 영속 저장

**문제**: `CredentialRegistry` 는 순수 in-memory dict 다(`server/director/auth.py:135-136`
실측 — 영속화 코드가 전혀 없다). 서버 프로세스가 재기동하면 등록된 모든
credential 메타데이터가 사라진다. `PairingSecretStore` 는 OS keyring 을 쓰므로
secret 자체는 재기동을 견디지만, 그 secret 이 가리키는 `credential_id` 의
scope·만료·project_id 를 아는 유일한 자리(`CredentialRegistry`)가 사라지면 그
secret 은 고아가 된다.

**대안 A(채택 후보) — 매 기동 재발급**: 서버가 시작될 때마다 새 `credential_id` 로
새 app-human `Credential` 을 발급하고, 이전 기동에서 발급된 credential 은 (등록
자체가 메모리에서 사라졌으므로) 자동으로 무효가 된다. `lighting-director` 플러그인
/ 운영자는 서버가 재기동할 때마다 새 bearer token 을 다시 받아야 한다.

- 장점: 새 영속 저장소가 필요 없다. `LAUNCH_TOKEN_ENV`/`generate_launch_token()`
  (`server/web/launcher.py`)이 이미 같은 "매 기동 재발급" 패턴을 쓰고 있어
  코드베이스 관례와 일치한다. 재기동 후 예전 secret 이 keyring 에 남아 있어도
  registry 에 매칭되는 credential 이 없으므로 `authenticate()` 가 이미
  `UNAUTHENTICATED` 로 정직하게 거절한다(추가 무효화 로직 불필요).
- 단점: 서버가 재기동될 때마다 운영자가 재페어링해야 한다 — 장시간 연결을 유지하는
  MCP 클라이언트가 있다면(이 SPEC 의 범위 밖) 그쪽에도 재인증 흐름이 필요해진다.

**대안 B — `CredentialRegistry` 에 파일 기반 영속화 추가**: `server/deploy/keystore.py`
류의 JSON/SQLite 영속화를 `CredentialRegistry` 에 새로 만든다.

- 장점: 재기동을 견디는 장기 pairing.
- 단점: 이 SPEC 의 범위를 새 저장 스키마 설계로 확장한다 — `auth.py` 자신은
  `CredentialRegistry` 를 "credential **메타데이터**(scope·만료·철회 — 비밀
  아님)만 보관한다"고 이미 규정했을 뿐 영속 형태를 규정하지 않았으므로, 영속화
  스키마 자체가 새로운 설계 표면이다. `SPEC-LDRECV-001`/`SPEC-LDSEND-001` 어느
  쪽도 이 확장을 예정하지 않았다.

**결정: 대안 A 채택 (2026-09-19 사용자 확인).** "재기동마다 재페어링"은 운영상
허용 가능한 trade-off 로 확정됐다 — plan.md §2 항목 1.

## (나) `ValidationReport` 영속화 + `validation_id` 채번 스킴

**문제**: `service.py` `SubmitResult.validation` 은 `PlanValidator.validate()` 가
돌려주는 dict 그대로다 — `validation_id` 필드가 없다(`store.py:38` 자신의 주석:
"validation_id·approval_id·execution_id 는 아직 없는 관계이므로 생략된다").
우산 `contract.md` §3 은 `GET P/validations/{validation_id}` 를 별도 route 로
정의하지만 `director_api.py` 는 이 route 를 아예 배선하지 않았고(§1.1 실측),
`POST .../approvals` 의 `ValidationProvider.get()` 도 이 저장소가 있어야 동작한다.

**대안 A — `DirectorStore` 의 sqlite 파일에 `validations` 테이블 추가**: `store.py`
의 마이그레이션 파일 규율(`IF NOT EXISTS`, 파일명 순서 적용)을 그대로 따라
`validation_id, project_id, plan_id, plan_digest, context_digest, created_at,
expires_at, outcome, diagnostics_json, compiled_json` 컬럼을 갖는 테이블을 추가한다.
`validation_id` 는 `PlanRecord.plan_digest`·`revision`·발급 시각의 결정론적 해시로
채번한다(재제출 idempotency 재생 경로와 같은 원칙 — 같은 입력이면 같은 id).

- 장점: `DirectorStore` 가 이미 같은 파일에 대해 여러 sqlite 연결을 허용하는
  설계(`ExecutionJournal` 이 같은 패턴을 씀, `execution.py:300-303` docstring)이므로
  마이그레이션 규율만 따르면 충돌이 없다.
- 단점: `DirectorStore` 스키마를 확장한다 — `SPEC-LDSTORE-001` 의 완료된 스키마를
  건드리는 것이므로 그 SPEC 의 "완료" 경계를 넘는다(다만 **기존 컬럼/시험을
  깨지 않는 추가 마이그레이션**이므로 회귀 위험은 낮다).

**대안 B — 별도 파일(별도 store 클래스)**: `ExecutionJournal` 과 같은 방식으로
`validations.db` 를 별도로 연다.

- 장점: `DirectorStore` 스키마에 전혀 손대지 않는다.
- 단점: `validation_digest → context_digest → plan_digest` 를 한 트랜잭션으로 묶어
  검증해야 하는 자리(승인 시 세 digest 대조, `director_api.py` `post_approval`)가
  두 개의 서로 다른 sqlite 파일을 가로질러야 한다 — 원자성 이점이 없다.

**결정: 대안 A 채택 (2026-09-19 사용자 확인).** `DirectorStore` 스키마 확장이
`SPEC-LDSTORE-001` 소유 경계를 넘는 결정임을 인지한 채 확정됐다 — plan.md §2
항목 2.

## (다) `PipelineValidator` 의 per-request context 주입

**문제**: `PipelineValidator.__init__(context: dict | None = None)` 은 **생성
시점**에 context 를 받는다(`validate/pipeline.py:314-320` 실측, 그 클래스 자신의
docstring: "context 는 검증기를 만들 때 주입한다"). 그런데 `GET context` 의
snapshot 은 REQ-LDWIRE-004/005 대로 project 마다·시간에 따라 바뀐다 — `deps.validator`
에 **하나의 고정 인스턴스**를 넣으면 그 인스턴스가 생성될 때의 context 로 이후
모든 요청을 검증하게 되어, context 가 갱신돼도(REQ-005 의 재발급 조건) 검증
결과가 낡은 context 기준으로 남는다.

**대안 A(채택 후보) — 요청마다 `PipelineValidator(context=...)` 재구성**: `POST
.../validations`·`PUT .../plans/{plan_id}` handler 가 호출되는 시점에 (1)
`ContextProvider.current(project_id)` 로 현재 snapshot 을 얻고 (2) 그 snapshot 으로
`PipelineValidator(context=snapshot)` 를 새로 만들어 (3) 그 인스턴스로만
`validate()` 를 호출한다. `deps.validator` 필드 자체는 고정 인스턴스를 담지 않고,
"검증기를 만드는 factory"(project_id → PlanValidator)로 재정의하거나, 두 route
handler 가 직접 `PipelineValidator` 를 생성한다.

- 장점: `validate/pipeline.py`/`service.py` 어느 쪽 코드도 수정하지 않는다 —
  `PipelineValidator` 자신의 docstring 이 명시한 "service.py 를 수정하지 않는다"
  선례를 그대로 지킨다. context 는 항상 그 요청 시점의 것이다.
- 단점: `DirectorApiDeps.validator: PlanValidator | None` 필드의 의미가
  "고정 인스턴스"에서 "factory 또는 route 층 조립"으로 바뀐다 — `director_api.py`
  의 타입을 그대로 두려면 route handler 쪽에서 재구성 로직을 갖는다(스키마
  변경 없이 조립 층에서만 흡수 가능한지는 실제 구현 시 재확인).

**대안 B — `PlanValidator` Protocol 에 context 매개변수 추가**: `validate(self,
plan, context=None)` 로 시그니처를 넓혀 `DirectorService.submit()` 이 매 호출마다
현재 context 를 넘기게 한다.

- 장점: `deps.validator` 는 계속 고정 인스턴스로 둘 수 있다.
- 단점: `PlanValidator` Protocol과 `service.py`(형제 SPEC 소유, `SPEC-LDSTORE-001`)
  를 수정해야 한다 — 완료된 형제 SPEC 의 seam 계약을 바꾸는 것이므로 영향 범위가
  이 SPEC 하나를 넘는다(다른 `PlanValidator` 구현체가 있다면 전부 시그니처를
  맞춰야 한다 — 오늘은 `NotInstalledValidator`/`PipelineValidator` 둘뿐이라
  영향은 작지만, seam 계약 변경 자체가 더 무거운 결정이다).

**결정: 대안 A 채택 (2026-09-19 사용자 확인).** `DirectorApiDeps.validator` 는
조립 층(route handler)에서 요청마다 재구성하는 방식으로 확정됐다 — `PlanValidator`
Protocol 은 건드리지 않는다. plan.md §2 항목 3.

## (라) `ContextProvider` 의 관측 소스 매핑 — 아홉 축 중 무엇을 오늘 채울 수 있는가

**문제**: `context.py` `NINE_AXES` 아홉 축은 각각 서로 다른 관측 수단을 요구한다.
이 SPEC 은 "값을 지어내지 않는다"(REQ-LDWIRE-004)는 불변식을 지키면서 오늘
서버가 실제로 가진 정보만으로 최대한 채워야 한다.

| 축 | 오늘 서버가 가진 것 | 이 SPEC 이 채우는 방법 |
|---|---|---|
| `identity`(target) | `server/safety/bootstrap.py` `build_console_stack()` 이 구성한 `console_id`/`session_id` 상당의 값 — `stack.gate`/`session_context.py` 실측 필요(정확한 필드명은 구현 시 재확인) | `stack.gate` 로부터 채운다(관측 가능) |
| `expiry` | 서버가 스스로 계산하는 값(TTL 정책) | 서버가 계산해 채운다(관측이 아니라 정책값) |
| `policy`(safety, safety_policy_revision, limits) | `server/safety/gate.py` 의 `ruleset`/정책 revision 이 이미 존재 — 실측 필요 | `stack.ruleset`/`stack.gate` 로부터 채운다(관측 가능, 구현 시 정확한 접근자 재확인) |
| `show` | `server/web/session.py` 의 현재 세션/쇼 상태 — 실측 필요 | 가능하면 채운다; 없으면 `context.py` 의 기존 정직한 미관측 상태로 채운다 |
| `audio`/`group_membership`/`preset_content`/`compiler`/`capability` | `SPEC-LDCOMPILE-001` 이 이미 capability 선언 범위까지는 다룬다고 명시했지만(그 SPEC 의 유보 목록), 실제 콘솔 판독(OSC round-trip)·오디오 분석 연결은 이 SPEC 저장소 실측만으로 아직 확인되지 않았다 | **결정 (2026-09-19 확정)** — 이 SPEC 은 이 여섯 축의 관측 배선을 추가하지 않는다. `ContextProvider` 출력에서 이 여섯 축은 명시적으로 "정직한 미관측" 상태(`unreadable`/`unconfirmed`/`absent` 류)로 채운다 — 스파이크로 관측 가능성을 재확인하는 절차 자체를 이 SPEC 의 범위에서 제외한다. `context.py` 자신의 경고("COUNT 0 은 부재의 증거가 아니다")가 이 축들에도 그대로 적용된다는 원칙은 유지된다 — "미관측"이라고 명시하는 것과 "값이 없다고 추정"하는 것은 다르다. |

**결정 (2026-09-19 확정)**: `identity`/`expiry`/`policy` 세 축만 이 SPEC 에서
관측 소스를 배선한다. 나머지 여섯 축(`show`/`audio`/`group_membership`/
`preset_content`/`compiler`/`capability`)은 실행 가능한 조회 확인(스파이크)
없이, 처음부터 정직한 미관측 상태로 채우기로 확정했다 — plan.md §2 항목 4.

## 세 결정의 공통 성격

(가)(나)(다) 셋 모두 "되돌리기 비싼가"의 기준을 충족한다 — (가)는 운영자
경험(재페어링 빈도)을, (나)는 저장 스키마 소유 경계를, (다)는 완료된 형제 SPEC 의
Protocol 계약을 건드릴 수 있다. (라)는 되돌리기 비용 자체보다 **관측 가능성의
사실 확인**이 안 끝난 문제라 다른 성격이지만, REQ-LDWIRE-004 의 "값을 지어내지
않는다" 불변식을 지키려면 똑같이 Implementation Kickoff Approval 이전에 정리해야
했다 — 2026-09-19 사용자 확인으로 네 결정 모두 확정됐다(plan.md §2).
