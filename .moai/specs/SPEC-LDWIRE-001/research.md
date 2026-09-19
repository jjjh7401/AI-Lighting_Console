# 코드 근거 조사 — SPEC-LDWIRE-001

[요구사항](spec.md) · [설계 결정](design.md) · [계획](plan.md)

이 문서는 spec.md §1.1 실측 표의 원 근거(정확한 grep/Read 결과)를 보존한다.
`SPEC-LDPLUGIN-001` 의 우산 `research.md` 를 대체하지 않는다 — 이 SPEC 고유의
gap(조립 미배선 + 세 신규 seam)에 한정된 조사다.

## 1. 조립 미배선 — 원시 grep/Read 근거

```
$ wc -l server/director/director_api.py server/web/app.py server/web/panel.py server/web/serve.py
     481 server/director/director_api.py
     968 server/web/app.py
     966 server/web/panel.py
     578 server/web/serve.py
```

`server/web/app.py:31` — `from server.director.director_api import DirectorApiDeps,
build_director_router`. `server/web/app.py:253` — `WebDeps` 의 `director:
DirectorApiDeps | None = None` 필드, 주석: "``None`` = not wired (pre-LDRECV
behaviour — no director routes are mounted)". `server/web/app.py:962-963`:

```python
if deps.director is not None:
    app.include_router(build_director_router(deps.director))
```

`server/web/serve.py:377-432` — `WebDeps(...)` 생성자 호출 전체를 Read 로 확인.
`gate=`, `provider=`, `system_prefix=`, `audit=`, `approval_channel=`,
`review_channel=`, `question_channel=`, `deploy_pipeline=`, `recorder=`,
`ui_dist=`, `backup_manager=`, `heartbeat_interval_seconds=`,
`backup_poll_seconds=`, `settings=`, `provision=`, `paperwork=`, `presets=`,
`handshake=`, `console_input_probe=`, `preshow_receive_port=`,
`preshow_osc_slot=`, `song_timeline_store=`, `timeline_library=` — 22개
키워드 인자가 나열되고, `director=` 는 **없다**. `grep -n "director" server/web/
serve.py` 결과도 `director` 문자열 자체가 이 파일에 나타나지 않음을 확인했다
(첫 검색 시 0 매치 — argparse 의 `--ui-dist` 도움말 문자열과 `Runbook director
timeline`(음악 연출 기능의 무관한 동음이의) 만 매치, 도입부 grep 재확인).

## 2. 프로덕션 생성 지점 부재 — 원시 grep 근거

```
$ grep -rn "ApplyCoordinator(" server --include="*.py" | grep -v __pycache__ | grep -v test_
server/tools/director_apply_observe.py:482:    coordinator = ApplyCoordinator(
```

`server/tools/director_apply_observe.py` 는 `SPEC-LDSEND-001` 이 만든 **로컬
관측 하네스**다 — 그 SPEC 자신의 spec.md §2 가 "이 로컬 `DirectorStore`/
`ApprovalRegistry` 인스턴스는 `server/web/serve.py` 의 운영 조립과 무관하다 —
별도 프로세스 수명 안에서만 존재한다"고 명시한다. 즉 이 한 곳조차 이 SPEC 이
찾는 "프로덕션 조립 지점"이 아니다.

```
$ grep -rl "Credential(" server --include="*.py" | grep -v __pycache__
server/tests/test_director_approvals.py
server/tests/test_director_ops_lifecycle.py
server/tests/test_director_auth.py
```

세 파일 모두 `server/tests/` 아래다 — 프로덕션 코드에는 `Credential(` 생성
지점이 전무하다.

```
$ grep -rn "ContextProvider\|ValidationProvider" server --include="*.py" | grep -v __pycache__
server/director/execution.py:766:       compiled manifest 접근(LDCOMPILE `ValidationProvider`)이 필요하다).
server/director/director_api.py:46:class ContextProvider(Protocol):
server/director/director_api.py:66:class ValidationProvider(Protocol):
server/director/director_api.py:...(같은 파일의 필드 선언 3곳)
server/director/approvals.py:130-131:(주석 — ValidationProvider seam 미배선 언급)
server/tests/test_director_approvals.py:660-661,698,706: _StubValidationProvider / _StubContextProvider
server/tests/test_director_ops_lifecycle.py:389,402: context_provider=_FakeContextProvider(), class _FakeContextProvider
```

Protocol 선언과 시험 전용 Fake/Stub 뿐 — 프로덕션 구현은 전무하다.

## 3. `ValidationReport` 영속화 부재 — 원시 근거

`server/director/store.py:38`(Read 로 확인) — `PlanRecord` 필드 docstring:
"`validation_id`·`approval_id`·`execution_id` 는 아직 없는 관계이므로
생략된다". `server/director/service.py`(Read, 전체 90줄) — `SubmitResult` 는
`record: PlanRecord`, `validation: dict[str, Any]`, `state: str` 세 필드뿐이며
`validation` dict 자체는 `PlanValidator.validate()` 의 **직접 반환값**이라
`validation_id` 를 포함하지 않는다(`NotInstalledValidator.validate()` 반환
dict 도 `PipelineValidator.validate()` 반환 dict 도 `outcome`/`diagnostics`/
`compiled` 세 키만 가짐 — 두 구현 모두 Read 로 본문 확인).

우산 `contract.md:81`(Read 로 확인) — `GET P/validations/{validation_id}`
route 가 계약에는 정의돼 있지만, `director_api.py` 의 `build_director_router()`
가 배선한 10개 route(`GET context`, `GET knowledge`, `GET plans/{plan_id}`,
`POST .../approvals`, `POST .../rejections`, `POST validations`(무저장
재검증 — 다른 route), `PUT plans/{plan_id}`, `POST .../apply`, `GET
executions/{execution_id}`, `POST feedback-proposals`) 안에 `GET
validations/{validation_id}` 는 없다(라우터 소스 전체 Read 로 확인, §4 표
참고).

## 4. `PipelineValidator` 미주입 — 원시 근거

`server/director/service.py:81`(Read) — `DirectorService.__init__(self, store,
validator=None)`: `self._validator: PlanValidator = validator or
NotInstalledValidator()`. `grep -rn "PipelineValidator("` 결과:

```
server/director/validate/pipeline.py:306:class PipelineValidator:
server/tests/test_director_validate_pipeline.py: (그 클래스 자신의 시험)
```

`server/web/serve.py` 어디에도 `DirectorService(store, validator=
PipelineValidator(...))` 형태의 생성이 없다(§1 근거 — `WebDeps(...)` 호출부에
`service=`/`validator=` 자체가 아예 없다, `director` 관련 인자가 전무하므로).

`server/director/validate/pipeline.py:314-320`(Read) — `PipelineValidator.
__init__(self, context: dict[str, Any] | None = None)`: context 는 **생성
시점** 주입이며 그 docstring 이 "seam 은 계획만 넘기므로 context 는 검증기를
만들 때 주입한다"고 명시한다 — 요청마다 달라지는 `ContextSnapshot` 을 고정
인스턴스로 담으면 낡은 context 로 검증하게 된다는 design.md §다의 문제
근거다.

## 5. `CredentialRegistry` 영속화 부재 — 원시 근거

`server/director/auth.py:135-136`(Read):

```python
def __init__(self) -> None:
    self._by_id: dict[str, Credential] = {}
```

순수 in-memory dict — 파일/DB 쓰기 코드가 이 클래스 어디에도 없다(클래스
전체를 Read 로 확인, `register`/`get`/`revoke`/`for_principal` 네 메서드
전부 `self._by_id` 딕셔너리 연산뿐). `PairingSecretStore`(같은 파일,
166-205행)는 `keyring.set_password`/`get_password`/`delete_password` 를 직접
호출해 OS credential store 를 쓴다 — 두 클래스의 영속성 수준이 다르다는
비대칭이 design.md §가 문제의 근거다.

## 6. `context.py` 의 조립-전용 경계 — 원시 근거

`server/director/context.py`(모듈 docstring, 1-40행 Read) — "이 모듈은 관측을
**조립**한다. 관측을 **수행**하는 것(콘솔 판독, 오디오 분석)은 이 층의 일이
아니다." `NINE_AXES`(62-72행)가 아홉 축 → 최상위 key 매핑의 단일 원본임을
확인. `ContextObservations`(112-120행 부근) — snapshot 하나를 만들기 위해
서버가 **관측한** 값 전부를 담는 dataclass이며, `context_digest` 는 여기 없음
(관측의 함수이지 관측 자체가 아니므로). 즉 이 모듈은 "관측 결과가 이미 있다"고
가정한다 — 그 관측을 실제로 수행해 `ContextObservations` 를 채우는 코드가
이 SPEC 이전에는 프로덕션에 없다(§1.1의 `ContextProvider` 부재와 같은 사실의
다른 단면).

## 7. 관측 소스 후보 — 미확정 (design.md §라로 이관)

`server/safety/bootstrap.py` `build_console_stack()`, `server/safety/gate.py`
의 `ruleset`/정책 revision 접근자, `server/web/session.py` 의 세션/쇼 상태를
`identity`/`policy`/`show` 축의 후보 소스로 스캔했으나, 이 SPEC 의 조사 예산
안에서는 **각 접근자의 정확한 필드명·반환 형태까지 실행 확인하지 못했다** —
design.md §라가 이를 구현 시 재확인이 필요한 항목으로 남겼던 이유다(2026-09-19 사용자 확인으로 3축/6축 분리 결정 확정, 아래 참고). 이
문서는 "후보가 존재한다"까지만 확인했고 "그 후보로 아홉 축을 실제로 채울 수
있다"는 미검증 주장이다 — `.claude/rules/moai/core/verification-claim-
integrity.md` §1.1 의 미검증-전제 위반을 피하기 위해, plan.md M3 의 스파이크
결과가 나오기 전까지 이 절의 어떤 문장도 "확인됨"으로 격상하지 않는다.
