---
id: SPEC-COPILOT-TREEID-001
type: plan
version: "0.1.0"
status: draft
created: 2026-08-25
updated: 2026-08-25
cycle_type: tdd
---

# SPEC-COPILOT-TREEID-001 — 구현 계획

`quality.yaml` 의 `development_mode: tdd` 를 따른다 — 검사를 먼저 빨갛게 만들고 통과시킨다.

## M0 — 임포트 부작용 측정, C 절 결정 확정

**왜 먼저인가.** A 안(호출을 임포트 뒤에)은 「남의 트리 모듈이 임포트는 된다」를 받아들인다.
그 대가가 무해한지는 아직 안 쟀다. 재고 나서 고른다.

1. `server/` 하위 모듈을 하나씩 임포트하며 관측 가능한 부작용을 잰다 —
   파일 쓰기 · 소켓 개설 · 프로세스 생성 · 전역 상태 변형.
2. 결과를 `.moai/reports/t80/import-side-effects.md` 에 기록.
3. 부작용 0건이면 **A**. 하나라도 있으면 **B**(`per-file-ignores` 1줄).
4. 결정과 근거를 `spec.md` C 절에 반영.

산출: 측정 기록 · 확정된 배치 안.

## M1 — 가드 모듈과 테스트 (빨강 먼저)

1. **빨강**: `server/tests/test_tree_identity.py` 를 먼저 쓴다.
   - 양성: `server/` 를 tmp 로 복사(테스트·`__pycache__` 제외) → `PYTHONPATH` 로 얹고
     실제 도구를 스크립트 경로로 실행 → **exit 2** 단언 (AC-001)
   - 음성: 같은 도구를 `--help` 로 자기 트리에서 실행 → 가드로 죽지 않음 단언 (AC-002)
   - 이 시점에는 `tree_identity.py` 가 없으므로 두 테스트 모두 빨갛다.
2. **초록**: `server/tools/tree_identity.py` 를 쓴다.
   - `_tree_of(path)` — `__file__` 상위를 훑어 `server` 디렉터리를 찾고 그 부모 반환.
     못 찾으면 죽는다 (REQ-006).
   - 모듈 수준 `_GUARD_TREE = _tree_of(__file__)`.
   - `assert_same_tree(caller_file)` — 다르면 stderr 두 경로 + 원인 + 고칠 형태를 찍고
     `SystemExit(2)`.
   - `server.bridge` · `pythonosc` 미임포트 (REQ-007).
3. 복사 fixture 는 세션 스코프로 한 번만 (실측 3.9MB · 1초 미만).

산출: 가드 모듈 · 테스트 1파일 · 빨강→초록 전이 로그.

## M2 — 19개 전수 적용과 완전성 검사

1. **빨강**: 완전성 검사를 먼저 쓴다 — `server/tools/*.py` 를 훑어
   「`server` 를 임포트하는데 `assert_same_tree` 를 안 부르는 파일」 목록이 비어 있음을 단언.
   대상 개수 ≥ 19 도 함께 단언한다(공허한 통과 방지, AC-005).
   이 시점에는 19개 전부 위반이므로 빨갛다.
2. **초록**: 19개 도구에 M0 이 정한 자리로 호출 한 줄씩 삽입.
   - 3+ 파일 변경이므로 논리 단위로 쪼갠다: `t60_*` 7개 · `t66_*` 2개 · `*_e2e` 5개 ·
     나머지 5개. 단위마다 검사를 돌린다.
3. `make ci-local` 로 ruff format · lint 통과 확인.

산출: 도구 19개 · 완전성 검사 · 단위별 통과 로그.

## M3 — 뮤테이션·실기·증거

1. **뮤테이션** (AC-004): 도구 1개에서 가드 호출을 뺀다 → 치환이 실제로 들어갔는지 먼저
   단언 → AC-001 검사 실행 → 빨간 출력을 붙인다 → 원복 → 재통과.
2. **실기** (AC-006): 진짜 형제 워크트리 venv 인터프리터로 도구 1개를 스크립트 경로 실행.
   명령과 출력을 그대로 붙인다.
3. **전량 스위트**: 기준선 수치와 함께 실패 0 확인.
4. `.moai/reports/t80/verdict.md` 작성 → `git add -f` 로 커밋·푸시 →
   `git ls-tree -r origin/WT-tree-identity` 로 도달 확인.

산출: `verdict.md` · 전량 스위트 로그 · CI 통과.

## 검증 부하 원칙

레인 로컬 검사는 이 카드가 건드린 범위로 좁힌다. 전량은 푸시 후 CI 가 깨끗한 환경에서
돌린다 — 부하 걸린 개발 기계의 전량은 코드가 아니라 기계를 잰다. 배경 부하를 만들지 않는다.
