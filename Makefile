# ── ci-local: 저장소 로컬 CI 미러 ──────────────────────────────────────────
#
# 이 파일이 존재하는 이유 (카드 t55):
#   `.git/hooks/pre-push` 훅이 `make -C <repo-root> -s ci-local` 을 부르는데
#   저장소 루트에 Makefile 이 없어서, 훅은 매번 아래 한 줄만 찍고 exit 0 했다.
#       [pre-push] No Makefile found — skipping ci-local
#   실측(2026-08-24, 훅 자신의 로그 집계): primary 85행 + 워크트리 15그루 80행
#   = 165회 호출, 165회 전부 skip. pass 0 · fail 0. 단 한 번도 돈 적이 없다.
#   즉 「푸시가 성공했다」는 지금까지 아무것도 통과시키지 않았다.
#   이 Makefile 은 그 빈 칸을 실재하게 만든다.
#
# 훅은 moai 관리 파일이다 (moai-adk 3.1.2 내장 템플릿 templates/.git_hooks/pre-push).
# 2행 마커 `# MoAI-ADK pre-push hook` 이 있으면 `moai update` 가 덮어쓴다 —
# 그래서 방어선을 훅 본문이 아니라 추적 파일인 이 Makefile 에 둔다.
# 2팔 실험 증거: .moai/reports/t55/managed-file-verdict.md
#
# 범위 원칙 — 조용히 건너뛰는 갈래를 새로 만들지 않는다.
#   이 카드가 없애려는 결함이 바로 그것이므로, 여기서 「있으면 돌고 없으면
#   건너뛴다」를 새로 만들면 결함을 자리만 옮긴 것이다. 도구가 없으면 실패한다.
#
# 전체 게이트는 CI 몫이다(.github/workflows/test.yml: pytest 전량 + vitest 전량).
# ci-local 은 가볍고 빠른 미러다 — 실측 목표 20초 이내.
# 전량을 여기 넣지 않는 이유: 실측 153.21s(10023 passed)이고, 부하가 걸린
# 개발 기계에서의 전량은 코드가 아니라 기계를 잰다.
#
# ── 범위 선정 근거 (전부 2026-08-24 실측, load avg 3.97) ──────────────────
#
# ruff lint  : `ruff check .` 은 570 errors 인데 570/570 전부
#              src/Lighting_Designer/ (RIG 빌드 파이프라인) 이다. 별건 부채로 t63 에 등재됨 — 이 카드에서 손대지 않는다.
#              `ruff check server tools packaging console` → All checks passed (0).
# ruff format: `ruff format --check .` 은 13파일 드리프트
#              (11 src/Lighting_Designer, 2 packaging).
#              `ruff format --check server tools console` → 415 files already
#              formatted (0). packaging 2건은 고치지 않고 뺀다 — pyproject
#              [tool.ruff.format] 주석이 기록한 PRESERVE 핀 사고(ruff format 이
#              바이트 핀을 두 번 깨뜨림, 원복 6d0b58c)가 있어 이 카드에서
#              packaging 을 재포맷하는 것은 위험 대비 이득이 없다.
#              lint 에는 packaging 이 들어간다(0건이므로).
# fast tests : 느린 테스트를 깎는 방식은 성립하지 않는다 — `--durations=40`
#              최댓값 5.04s, 40위 0.51s 로 153s 가 10023건에 고르게 퍼져 있다.
#              상위 40개를 전부 빼도 ~97s 다. 그래서 좁은 지명 선택으로 간다:
#              저장소가 스스로 지키는 구조 불변식 가드 13파일.
#              실측 352 passed in 18.15s.
# typecheck  : ci-local 에 넣지 않는다. TS 타입검사는 `npm --prefix ui run
#              build`(tsc)인데 갓 만든 워크트리에는 ui/node_modules 가 없다.
#              「있으면 돌고 없으면 건너뛴다」로 넣으면 그것이 바로 이 카드가
#              없애려는 조용한 생략이다. 그래서 별도 타깃으로 빼고, ci-local
#              에서는 뺀 사실을 여기 적는다. 전량 타입검사는 CI 가 한다.
#              파이썬 쪽 타입체커는 이 저장소 툴체인에 없다(pyproject dev =
#              httpx/pytest/pytest-cov/ruff) — 없는 것을 있는 척 부르지 않는다.
#
# 범위를 넓히려면 위 숫자를 다시 재고 이 주석을 같이 고칠 것.
# 숫자 없이 경로만 늘리면 게이트가 첫날부터 빨개져서 아무도 안 쓴다.

RUFF_LINT_PATHS := server tools packaging console
RUFF_FMT_PATHS  := server tools console

# 구조 불변식 가드 — 13파일을 명시 나열한다. glob 으로 고르지 않는다:
# 이름 패턴은 찾는 도구가 판정까지 하는 형태라, 패턴에 안 걸리는 가드는
# 조용히 빠지고 다르게 이름 붙은 새 가드는 영영 안 들어온다.
# 실측 2026-09-11: 13파일 / 352 passed / 18.15s.
# 목록을 늘리거나 줄이면 이 세 숫자를 다시 재서 같이 고칠 것.
#
# t349 — `test_songcue_bundle.py` 를 넣었다. 그 파일이 유일하게 잠그는 경로가
# 있다: `server/looks/instantiate.py` 는 형제 게이트(`test_overlap_preserve.py`)
# 의 `_PRESERVE_PATHS` 아홉 항목에 없고(t348 이 감독 승인으로 뺐다), 이 파일의
# `_PRESERVE_LOOK_FILES` 여섯 항목에만 남아 다이제스트로 고정돼 있다. 그래서
# 목록에 없는 동안 훅은 초록인데 전량 스위트는 빨간 상태가 성립했다 — t348 이
# 실제로 그 문턱까지 갔고, 그 레인이 전량을 따로 돌려서야 걸렸다.
#
# 실측한 대조군(t349): `instantiate.py` 의 주석 한 줄을 포맷·린트가 통과하는
# 형태로 고쳐 **커밋**하면, 12파일 목록은 exit 0 인데 이 파일은 빨개진다
# (`assert 80 == 79`). 두 게이트 모두 `<base>..HEAD` 범위를 보므로 작업 트리의
# 미커밋 변경은 안 잡힌다 — 대조군은 반드시 커밋해서 재야 한다.
#
# 위 296 / 14.34s 는 내 추가 이전에 이미 낡아 있었다(실측 328 / 22.39s, 12파일).
# 같은 12파일 안에서 검사가 늘어난 것이다. 352 중 24건이 새로 들어온 파일 몫이다.
FAST_TESTS := \
	server/tests/test_address_verdict_parity.py \
	server/tests/test_architecture.py \
	server/tests/test_autopatch_contract.py \
	server/tests/test_deploy_safety_invariants.py \
	server/tests/test_fx_boundary.py \
	server/tests/test_looks_boundary.py \
	server/tests/test_matching_endings_parity.py \
	server/tests/test_overlap_preserve.py \
	server/tests/test_paperwork_boundary.py \
	server/tests/test_scene_boundary.py \
	server/tests/test_sheets_registry.py \
	server/tests/test_songcue_bundle.py \
	server/tests/test_ws_wait_guard.py

.PHONY: ci-local require-uv fmt lint test-fast test typecheck

# 훅은 `make -s ci-local >/dev/null` 로 부른다 — stdout 이 버려진다.
# 그래서 각 단계는 성공하면 조용하고, 실패하면 출력을 통째로 stderr 로 낸다.
# 그러지 않으면 개발자는 무엇이 깨졌는지 한 글자도 못 본다.

ci-local: require-uv fmt lint test-fast

require-uv:
	@if ! command -v uv >/dev/null 2>&1; then \
		printf 'ci-local: uv 가 PATH 에 없다. https://docs.astral.sh/uv/ 로 설치할 것.\n' >&2; \
		printf 'ci-local: 건너뛰지 않는다 — 도구가 없으면 게이트는 실패한다.\n' >&2; \
		exit 1; \
	fi

fmt: require-uv
	@out=$$(uv run ruff format --check $(RUFF_FMT_PATHS) 2>&1); \
	if [ $$? -ne 0 ]; then \
		printf '\n--- ci-local: ruff format --check 실패 ---\n' >&2; \
		printf '%s\n' "$$out" >&2; \
		printf 'ci-local: 고치려면  uv run ruff format %s\n' '$(RUFF_FMT_PATHS)' >&2; \
		exit 1; \
	fi

lint: require-uv
	@out=$$(uv run ruff check $(RUFF_LINT_PATHS) 2>&1); \
	if [ $$? -ne 0 ]; then \
		printf '\n--- ci-local: ruff check 실패 ---\n' >&2; \
		printf '%s\n' "$$out" >&2; \
		exit 1; \
	fi

test-fast: require-uv
	@out=$$(uv run pytest -q $(FAST_TESTS) 2>&1); \
	if [ $$? -ne 0 ]; then \
		printf '\n--- ci-local: 빠른 단위 부분집합 실패 ---\n' >&2; \
		printf '%s\n' "$$out" >&2; \
		exit 1; \
	fi

# 전량 — ci-local 에는 없다. 사람이 명시적으로 부를 때만 (실측 153.21s).
test: require-uv
	@uv run pytest -q -rs

# TS 타입검사 — ci-local 에는 없다. 조건부 생략을 만들지 않기 위해
# 의존성이 없으면 조용히 넘어가지 않고 실패한다.
typecheck:
	@if [ ! -d ui/node_modules ]; then \
		printf 'typecheck: ui/node_modules 없음. 먼저  npm --prefix ui ci --no-audit --no-fund\n' >&2; \
		exit 1; \
	fi
	@npm --prefix ui run build
