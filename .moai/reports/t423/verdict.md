# t423 판정 (LDWIRE 후속 죽은 코드 정리)

## 1. `server/director/store.py:47 _STATUS_REPLAYED`

- grep: `git grep -n '_STATUS_REPLAYED' -- server` → `server/director/store.py:47` (정의 자체) 1건만.
- 판정: 삭제. `_STATUS_CREATED`(201)는 여전히 사용됨(line 257) — 함께 남기고 주석만 "201 for a new record"로 정정.

## 2. `server/director/director_api.py:108 DirectorApiDeps.service`

- grep: `git grep -n 'deps\.service' -- server` → `director_api.py:433`(주석), `test_director_validator_injection.py:7`(독스트링) 2건, 실제 런타임 참조 0.
- 그 자리(line 440)는 `request_service = DirectorService(deps.store, validator=validator)` — 매 요청마다 새로 만든 `DirectorService`를 쓰고, `deps.service`는 읽지 않음(M4 이후 배선).
- `DirectorService` import(`director_api.py:52`)는 그 자리에서 여전히 쓰이므로 유지.
- 판정: `DirectorApiDeps.service` 필드 삭제 + 생성자 kwarg 3곳 삭제:
  - `server/director/provision.py:381` (`service=DirectorService(store)`)
  - `server/tests/test_director_approvals.py:569`
  - `server/tests/test_director_ops_lifecycle.py:403`
  - `server/tests/test_director_validator_injection.py:94`
  - 부수: provision.py의 `DirectorService` import는 그 자리 삭제 후 미사용 → 제거. test_director_ops_lifecycle.py/test_director_validator_injection.py도 `DirectorService` import가 그 kwarg 하나에만 쓰였으므로 제거. test_director_approvals.py는 `OUTCOME_READY`와 함께 import되어 있어 `DirectorService`만 골라 제거.
  - director_api.py:433 근처 "deps.service is NOT used directly any more" 주석은 이제 없는 필드를 설명하므로 재작성(필드 언급 제거, 나머지 근거는 유지).

## 3. `server/director/provision.py DirectorBoot.credential_id`

- grep: `git grep -nE '\bboot\.credential_id|director_boot\.credential_id|result\.credential_id' -- server` → 0건 (기존 매칭은 전부 `Credential.credential_id`, `DirectorBoot`와 무관).
- `server/web/serve.py`는 `director_boot.deps`와 `director_boot.bearer_token`만 읽음(grep 확인) — `.credential_id`는 어디서도 읽지 않음.
- 테스트 중 `DirectorBoot`를 직접 참조하는 파일 0건(`git grep -n 'DirectorBoot' -- server/tests` → 무결과).
- 판정: 삭제. `DirectorBoot.credential_id` 필드, `build_director_deps` 내부 지역변수 `credential_id`(초기화 + else-분기 대입), `return DirectorBoot(..., credential_id=credential_id)` 인자 모두 제거. `credential.credential_id`(Credential 객체 필드, bearer_token 인코딩에 사용)는 무관하며 그대로 유지.

## 테스트

- PRESERVE 베이스라인(변경 전, HEAD 8f7d4fc9):
  `uv run pytest -q server/tests/test_director_*.py server/tests/test_bundle_sender.py server/tests/test_run_director_apply.py` → **664 passed**
- IMPROVE 이후 동일 세트: **664 passed** (동일 개수, 회귀 없음)
- 추가: `server/tests/test_director_boundary.py server/tests/test_director_production_wiring.py` → **11 passed**
- 전체: `uv run pytest -q` → **13685 passed, 35 skipped** (실패 0)
- `uv run ruff check .` → All checks passed
- `uv run ruff format --check .` → 831 files already formatted; 이 커밋과 무관한 `packaging/rust_scan.py`, `packaging/verify_packaged_e2e.py` 2건만 사전부터 미포맷 상태(내 diff에 없음, 손대지 않음)
