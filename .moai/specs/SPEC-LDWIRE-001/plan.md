# 구현 계획 — SPEC-LDWIRE-001

[요구사항](spec.md) · [설계 결정](design.md) · [인수](acceptance.md) · 선행:
[SPEC-LDRECV-001](../SPEC-LDRECV-001/spec.md) ·
[SPEC-LDSEND-001](../SPEC-LDSEND-001/spec.md) ·
[SPEC-LDSTORE-001](../SPEC-LDSTORE-001/spec.md) ·
[SPEC-LDCOMPILE-001](../SPEC-LDCOMPILE-001/spec.md)

## 1. 착수 경계

개발 방법론은 **TDD (RED-GREEN-REFACTOR)** 다 —
`.moai/config/sections/quality.yaml` `constitution.development_mode: tdd`.
근거: 이 SPEC 이 조립하는 컴포넌트(`ApplyCoordinator`·`execute_bundles`·
`authenticate`·`PipelineValidator`)는 전부 이미 테스트된 새 코드이고, 이 SPEC
자신이 새로 만드는 세 seam(credential 발급·`ValidationReport` 저장·
`ContextProvider` 실물)도 명세가 분명한 신규 동작이다 — `server/tests/
test_director_*.py` 24개 파일이 이미 보여주는 "먼저 route 층 fixture 로 실패를
관찰하고 seam 을 채운다" 패턴을 그대로 잇는다. 기존 동작 보존(DDD)이 아니라
새 동작 추가이므로 TDD 가 맞다.

이 계획은 **Implementation Kickoff Approval 을 아직 받지 않았다.** 승인 없이
구현을 시작하지 않는다.

## 2. 확정된 인터페이스 결정 — 2026-09-19 사용자 확인 완료

design.md 의 네 결정 중 사람 확인이 필요했던 항목을 여기 기록한다. 2026-09-19
사용자가 아래 확정안(전부 design.md 의 권고 대안)을 확인했다 — Implementation
Kickoff Approval 의 일부로 반영됐다. 각 항목은 design.md 의 해당 절을 가리킨다
— 여기서 다시 논거를 반복하지 않는다.

1. **운영 자격증명 수명 — 대안 A 채택(design.md §가, 매 기동 재발급)**: 서버가
   기동할 때마다 새 credential 을 발급하고, 영속 저장은 새로 만들지 않는다.
   `CredentialRegistry` 는 계속 in-memory dict 로 남고 이 축을 위한 새 스키마·
   저장소를 이 SPEC 에서 추가하지 않는다. 운영자는 서버 재기동마다
   `lighting-director` 플러그인을 재페어링해야 한다 — design.md §가가 이미
   단점으로 명시한 trade-off 를 그대로 수용한다.
2. **`ValidationReport` 저장 위치 — 대안 A 채택(design.md §나, `DirectorStore`
   확장)**: 별도 store 모듈을 새로 만들지 않고, 기존 `DirectorStore`(sqlite) 에
   `validations` 테이블을 추가하는 마이그레이션으로 흡수한다 — 기존 저장
   인프라·마이그레이션 규율을 재사용한다. `SPEC-LDSTORE-001` 의 완료 경계를
   넘는 결정임을 인지한 채 채택한다(design.md §나가 이미 명시한 낮은 회귀 위험
   근거 — 기존 컬럼·시험을 깨지 않는 추가 마이그레이션).
3. **`PipelineValidator` per-request context 주입 — 대안 A 채택(design.md §다,
   route 층 재구성)**: `PlanValidator` Protocol 자체를 넓혀 `service.py`(형제
   SPEC `SPEC-LDSTORE-001` 소유)를 수정하는 대안 B 는 채택하지 않는다. 대신
   `POST .../validations`·`PUT .../plans/{plan_id}` route handler 가 요청마다
   `PipelineValidator(context=...)` 를 새로 구성한다 — 이 SPEC 의 영향 범위를
   자기 파일로 한정한다.
4. **`ContextProvider` 관측 축 범위 — 오늘 관측 가능한 세 축만 채운다
   (design.md §라)**: 구현 스파이크 없이 범위를 확정한다 — `identity`/`expiry`/
   `policy` 세 축(`context.py` `NINE_AXES` 의 아홉 키 중 `stack.gate`/서버가
   이미 계산하는 정책값으로 오늘 관측·산출 가능한 것들)만 실제 관측 소스를
   배선한다. 나머지 여섯 축(`show`/`audio`/`group_membership`/
   `preset_content`/`compiler`/`capability`)은 이 SPEC 에서 관측 배선을 추가
   하지 않고, `ContextProvider` 출력에서 그 축의 기존 정직한 미관측 상태
   (`unreadable`/`unconfirmed`/`absent` 류)로 채운다 — 값을 지어내거나 관측을
   가장하지 않는다. M3(§5) 는 이 세 축의 관측 소스 배선에만 집중하며, 여섯
   축에 대한 스파이크·관측 범위 확장은 이 SPEC 의 범위 밖이다.

## 3. 사전 점검 (Pre-flight)

```bash
git branch --show-current
git rev-parse HEAD
uv run pytest server/tests/test_director_ops_lifecycle.py server/tests/test_run_director_apply.py -q
grep -n "director=" server/web/serve.py   # 오늘은 무매치 — 이 SPEC 이 만드는 최초 등장이어야 한다
grep -rn "ApplyCoordinator(\|Credential(" server --include="*.py" | grep -v /tests/
```

## 4. 제약 (PRESERVE)

- **손대지 않는다**: `server/director/execution.py`(`ApplyCoordinator`/
  `execute_bundles`/`GateBundleSender`/`run_director_apply`), `server/director/
  auth.py` 의 `authenticate()`/`Credential`/`resolve_trust`/`authorize_audio_transfer`
  본문 로직, `server/director/approvals.py`, `server/director/validate/pipeline.py`
  의 검증 stage 내용, `server/safety/gate.py`, `server/safety/bootstrap.py` 의
  기존 `build_console_stack()` 시그니처.
- **확장은 허용**(§2 결정에 따라 필요한 경우만): `server/director/auth.py` 에
  발급 헬퍼 함수 추가, `server/director/store.py` 마이그레이션에 `validations`
  테이블 추가(대안 A 채택 시), `server/director/context.py` 소비자 코드 신설,
  `server/web/serve.py` 의 `WebDeps(...)` 호출부.
- **새 파일 후보**: `ContextProvider`/`ValidationProvider` 실물 구현을 담을 신규
  모듈(예: `server/director/provision.py` — 정확한 이름/위치는 M1 착수 시
  확정, 기존 `server/director/` 평면 구조를 따른다).
- 병행 세션이 있을 경우 다른 director 파일(특히 `execution.py`)을 건드리지
  않는다.

## 5. 마일스톤 — 되돌리기 비싼 결정부터

### M1 — 인터페이스 결정 확정 반영 (design.md §2, 2026-09-19 확정)

Implementation Kickoff Approval 의 일부로 사람이 위 §2 를 확인했다(2026-09-19,
전 항목 권고안 채택). 코드 변경 없음 — design.md/plan.md 갱신만.

### M2 — `ValidationReport` 영속화 + `validation_id` 채번 (design.md §나)

데이터 모델 신설이라 가장 되돌리기 비싸다. `DirectorStore`(또는 결정된 대안)에
저장 스키마를 추가하고, `DirectorService.submit()` 이 검증 결과를 그 스키마로
저장하도록 확장한다. RED: `validation_id` 로 저장 후 조회가 왕복하는 실패
시험부터 작성한다.

- REQ-LDWIRE-006 (저장 + 조회 왕복), REQ-LDWIRE-007 (`ValidationProvider.get()`
  배선 — 존재하지 않는/다른 project 의 id 는 정직하게 거절)

### M3 — `ContextProvider` 실물 (design.md §라)

새 관측 소스 매핑이라 두 번째로 되돌리기 비싸다(축마다 소스가 정해지면 이후
호출자가 그 형태에 의존하기 시작한다). §2 항목 4 에서 이미 확정한 범위대로
`identity`/`expiry`/`policy` 세 축의 관측 소스를 배선한다 — 나머지 여섯 축은
정직한 미관측 상태로 채우기만 하며, 이 마일스톤에서 그 여섯 축을 위한 새
관측 배선을 추가하지 않는다.

- REQ-LDWIRE-004 (아홉 축 충족 — 세 축은 실제 관측, 여섯 축은 정직한 미관측
  상태), REQ-LDWIRE-005 (재발급 억제 — `should_reissue` 소비)

### M4 — `PipelineValidator` per-request context 주입 (design.md §다)

M2/M3 이 끝나야 실제로 시험 가능하다(검증기가 저장·context 둘 다에 의존).
§2 항목 3 의 결정에 따라 route 층 재구성 또는 Protocol 확장을 구현한다.

- REQ-LDWIRE-006 의 `PipelineValidator` 실제 주입 부분 마무리

### M5 — 운영 자격증명 발급 경로 (design.md §가)

UX/운영 흐름 결정이라 세 번째로 되돌리기 비싸다(발급 채널이 CLI 인지, 기동
시 stdout 인지, 별도 HTTP bootstrap 인지는 이 마일스톤에서 §2 항목 1 의 결정에
따라 구체화한다 — design.md 는 "매 기동 재발급"이라는 수명 정책만 권고했고,
정확한 발급 **채널**(어디에 bearer token 을 노출하는가)은 이 마일스톤의
구현 세부다. 기존 `generate_launch_token()`(`launcher.py`) 패턴을 참고하되
새 채널을 만들 필요가 있으면 이 마일스톤 안에서 결정하고 기록한다).

- REQ-LDWIRE-001, REQ-LDWIRE-002, REQ-LDWIRE-003

### M6 — `DirectorApiDeps` 조립 + `serve.py` 배선 (기계적)

M2~M5 가 만든 조각을 하나로 묶는다 — 새 설계 결정이 가장 적은 마일스톤이므로
마지막에 둔다. 스레드 제약(REQ-LDWIRE-010)을 지키는 `async def` lifespan-style
조립을 따른다(`server/tests/test_director_ops_lifecycle.py` `client` fixture의
패턴이 이미 이 제약을 프로덕션과 같은 형태로 보여준다).

- REQ-LDWIRE-008, REQ-LDWIRE-009, REQ-LDWIRE-010

### M7 — 프로덕션 경로 통합 시험

`server.web.serve` 의 실제 조립 함수(또는 그와 동등한 테스트 전용 wrapper)를
호출해 `create_app(deps)` 가 만든 앱에 director 라우트가 실제로 마운트됐는지,
M5 에서 발급한 credential 로 실제 인증이 통과하는지를 `TestClient` 로 확인한다
— 이것이 §1.1 이 실측한 gap("연결된 적이 없다")을 이 SPEC 이 닫았다는 직접
증거다.

## 6. 위험

- **범위 확정 완료(잔여 위험 낮음)**: §2 의 네 결정이 전부 사람 확인을 거쳐
  대안 A(design.md 권고안, 더 가벼운 쪽)로 확정됐다 — "대안 B 로 확정될 경우"
  의 범위 팽창 위험은 더 이상 없다. 다만 §나(`DirectorStore` 스키마 확장)는
  여전히 `SPEC-LDSTORE-001` 의 완료 경계를 넘는 결정이므로, M2 구현 중 기존
  컬럼·시험과의 충돌이 예상보다 크면 별도 plan-audit 재검토가 필요할 수 있다.
- **`ContextProvider` 세 축 한정의 하류 영향**: §2 항목 4 에 따라 `show`/
  `audio`/`group_membership`/`preset_content`/`compiler`/`capability` 여섯
  축은 이 SPEC 에서 정직한 미관측 상태로 남는다 — 그 축을 요구하는
  `PipelineValidator` 의 검증 stage 가 있다면(예: time-reference stage 류),
  그 stage 는 이 SPEC 이후에도 계속 `blocked` 를 반환할 수 있다. 이는 결함이
  아니라 정직한 결과다 — REQ-LDWIRE-004 가 요구하는 바로 그 정직함이며,
  감춰서는 안 된다.
- **credential 재발급 UX**: §2 항목 1 에서 "매 기동 재발급"을 확정 채택했으므로
  운영자는 서버 재기동마다 재페어링해야 한다 — 이 trade-off 는 Kickoff 단계에서
  이미 명시적으로 확인받았다(더 이상 열린 질문이 아니다).
