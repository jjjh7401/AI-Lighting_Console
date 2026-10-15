# t633 — CI 에 ruff 검사 추가: 사전 실측

> 카드 t633 · 브랜치 WT-ci-ruff · 측정 기준은 origin/main 이다.

## 기준선 귀속

- 기준 커밋: `origin/main` = `5054b800`. 측정 직전에 `git fetch origin main` 으로 갱신했다. 워크트리 `WT-ci-ruff` 의 HEAD 도 `5054b800` 과 같다 (`git rev-parse --short HEAD`).
- 도구: `uv run ruff --version` → `ruff 0.15.21`. 이 값은 `uv.lock` 의 잠금값이다 (`name = "ruff"`, `version = "0.15.21"`). 로컬 게이트와 CI 가 같은 `uv run` 을 쓰므로 같은 버전을 쓴다.
- 파이썬 `3.11.15` (`.python-version`), uv `0.11.4`.
- 모든 실행에 `--no-cache` 를 붙였다. CI 는 캐시 없이 돈다.

## 게이트가 쓰는 범위와 설정

- `Makefile` `RUFF_LINT_PATHS := server tools packaging console` → `make lint`
- `Makefile` `RUFF_FMT_PATHS := server tools console` → `make fmt`
- 설정은 `pyproject.toml` 의 `[tool.ruff]` 다 (`line-length = 100`, `target-version = "py311"`, `force-exclude = true`, 규칙 `E F W I UP B SIM`, 파일별 무시 11건, format 제외 `server/web/preview.py`).
- 로컬 pre-push 훅 `.git_hooks/pre-push` 은 `make -C <repo-root> -s ci-local` 을 부른다. `ci-local` 은 `fmt lint test-fast` 순서다.

## 주장

게이트 범위에서 위반은 0이다 (린트 0건, 포맷 대상 0건). 그래서 카드의 2번 경로, 곧 CI 에 단계를 추가하는 길을 탄다.

## 증거 (명령과 출력, 이 실행에서 관찰)

| 명령 | 종료 코드 | 출력 |
|------|-----------|------|
| `uv run ruff check --no-cache --output-format concise server tools packaging console` | 0 | `All checks passed!` (`ruff_check.txt`) |
| `uv run ruff format --check --no-cache server tools console` | 0 | `858 files already formatted` (`ruff_format.txt`) |
| `make -s lint` | 0 | 성공 시 무출력 |
| `make -s fmt` | 0 | 성공 시 무출력 |

**음성 대조군.** 게이트가 실제로 빨개지는지 확인했다. `server/_t633_negative_control.py` 에 `import os` 와 `x=1` 두 줄을 쓰고 측정한 뒤 지웠다.

| 명령 | 종료 코드 | 잡힌 것 |
|------|-----------|---------|
| `make -s lint` | 2 | `F401` (`os` imported but unused), `I001` (Import block is un-sorted) |
| `make -s fmt` | 2 | `Would reformat: server/_t633_negative_control.py`, `1 file would be reformatted` |

지운 뒤 `git status --short` 에는 `.moai/reports/t633/` 만 남았다.

**게이트 밖 범위 (참고용).** 저장소 전체도 깨끗하다.

- `uv run ruff check --no-cache .` → 종료 0, `All checks passed!`. 검사 파일은 1,381개다: `server` 844, `.moai` 442, `reports` 63, `tools` 15, `src` 11, `packaging` 5, `pyproject.toml` 1.
- `uv run ruff format --check --no-cache .` → 종료 0, `1379 files already formatted`.
- `console/` 에는 파이썬 파일이 없다 (`find console -name '*.py'` → 0개). 그래서 게이트의 `console` 항목은 지금 검사 대상이 0개다.

**낡은 숫자.** `Makefile` 주석은 2026-08-24 실측으로 `ruff check .` 570건, `ruff format --check .` 13파일 드리프트라고 적고 있다. 오늘 측정으로는 둘 다 0이다. 이 카드에서는 그 주석을 고치지 않았다 (범위 밖). 리드에게 따로 알린다.

**CI 기준선.** `origin/main` 의 `test` 워크플로 최근 5건이 모두 `success` 다. 최신 run `38579840052` 의 headSha 는 `5054b800` 이다.

## 미검증 (Gaps)

- `actionlint` 가 설치돼 있지 않다 (`command -v actionlint` 결과 없음). 워크플로 문법은 PyYAML 파싱과 단계 목록 확인으로만 본다. GitHub Actions 의 실제 실행은 PR 의 CI 로 확인한다.
- CI 러너(ubuntu-latest, `pip install uv` 로 받는 uv)에서 실행한 결과가 아니다. 이 측정은 로컬 실측이다.
- push 때 도는 pre-push 훅(`make ci-local` = fmt·lint·test-fast)의 결과는 push 뒤 `.moai/logs/prepush-bypass.log` 로 확인한다.

## 잔여 위험

- 게이트 범위 밖(`src`, `.moai`, `reports`)에 드리프트가 생겨도 CI 와 로컬 게이트 모두 잡지 않는다. 범위를 넓힐지는 리드가 정한다. 지금은 전부 깨끗하다.
- 워크플로의 `pip install uv` 는 uv 버전을 고정하지 않는다. ruff 버전은 `uv.lock` 이 고정하므로 ruff 결과에는 영향이 없다고 본다. 다만 uv 자체의 해석 차이는 남는다.
