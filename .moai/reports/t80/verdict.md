# t80 — 판정 증거

- 트리 `.claude/worktrees/t80` · 브랜치 `WT-tree-identity` · 기준 `86fee6c`
- SPEC `SPEC-COPILOT-TREEID-001` · 2026-08-25
- 콘솔 발사 **0건**. 이 카드는 실기 콘솔을 건드리지 않는다.

## 1. 무엇을 고쳤는가

`server/tools/` 의 도구를 다른 워크트리의 인터프리터로 **스크립트 경로**로 부르면
남의 트리 `server` 가 경고 0줄로 임포트됐다. 이제 **exit 3 으로 죽는다.**

- 신설: `server/tools/tree_identity.py` (가드)
- 신설: `server/tests/test_tree_identity.py` (검사 4건)
- 수정: `server/tools/` 도구 **19개** — 임포트 블록 뒤에 `assert_same_tree(__file__)` 한 줄

## 2. TDD 전이 — 빨강을 실제로 봤다

| 단계 | 검사 | 결과 |
|---|---|---|
| 빨강 | 가드 없이 남의 트리에서 도구 실행 | `assert 0 == 3` — **정상 실행됐다** (그것이 결함) |
| 초록 | 가드 도입 후 | exit 3 · 두 트리 경로 · 고칠 형태 출력 |
| 빨강 | 완전성 검사 (가드 붙이기 전) | **18/19 누락** — 목록이 그대로 찍힘 |
| 초록 | 19개 전수 적용 후 | 누락 0/19 |

## 3. AC 판정

| AC | 내용 | 판정 | 근거 |
|---|---|---|---|
| 001 | 빌린 인터프리터로 돌리면 exit 3 | **통과** | `test_borrowed_tree_kills_the_tool` |
| 002 | 자기 트리에서는 안 죽는다 | **통과** | `test_own_tree_runs_normally` + 도구 19개 `--help` 전부 exit 0 |
| 003 | 두 번째 venv 없이 돈다 | **통과** | 4건 전부 로컬 pytest 통과 · CI 확인은 §7 |
| 004 | 뮤테이션이 검사를 죽인다 | **통과** | §4 |
| 005 | 노출면 전수 적용 | **통과** | 완전성 검사, 대상 19 · 누락 0 |
| 006 | 실기 1회 (모델링 가정) | **통과** | §5 |
| 007 | 기존 경계 무파손 | **통과** | §6 |

## 4. 뮤테이션 (AC-004)

`osc_smoke.py` 에서 `assert_same_tree(__file__)` 한 줄만 제거했다.
**치환이 실제로 들어갔는지 먼저 단언했다** — 살아남은 뮤테이션을 「레버 없음」으로
오독하기 전에 「적용 안 됨」을 배제해야 한다.

    치환 적용 확인: 가드 호출 1줄 제거됨
    grep -c "assert_same_tree(__file__)" -> 0

결과: **3 failed, 1 passed**

| 검사 | 뮤테이션 후 | 읽기 |
|---|---|---|
| `test_borrowed_tree_kills_the_tool` | **죽음** | 레버 있음 |
| `test_message_names_the_fix` | **죽음** | 레버 있음 |
| `test_every_tool_importing_server_calls_the_guard` | **죽음** | 레버 있음 |
| `test_own_tree_runs_normally` | 살아남음 | **설계상 그래야 한다** — 음성 대조군은 가드가 없어도 자기 트리에서 정상 실행되는 것을 단언하므로 이 뮤테이션에 영향받지 않는다 |

복원은 `git checkout` 이 아니라 **백업 + 체크섬**으로 했다(미커밋 작업 보호).
복원 후 sha256 이 백업과 동일했고 `git status` 가 비었다 — 바이트 동일.
재실행 **4 passed**.

## 5. 실기 (AC-006) — 모델링 가정을 쟀다

자동 테스트는 `server/` 복사본을 `PYTHONPATH` 로 얹어 「남의 트리」를 흉내낸다.
그 대체가 유효한지는 **가정**이므로, 진짜 editable venv 로 다시 쐈다.

`/tmp/t80real` 에 `server/`(테스트 제외) + `pyproject.toml` 을 놓고 `uv sync` 로
**진짜 두 번째 venv** 를 만들었다. 그 venv 의 `.pth` 내용:

    /private/tmp/t80real

`PYTHONPATH` 없이, 그 인터프리터로 t80 의 도구를 스크립트 경로로 실행:

    /tmp/t80real/.venv/bin/python server/tools/osc_smoke.py --help

    트리 동일성 위반 — 이 도구는 남의 워크트리 코드를 부르고 있다.

      실행한 스크립트 : /…/.claude/worktrees/t80
      임포트된 server : /private/tmp/t80real

    인터프리터가 다른 트리의 venv 다. 스크립트 경로로 실행하면 sys.path[0] 이
    server/tools/ 라 자기 트리가 가려지고, venv 의 editable .pth 가 이긴다.

    고칠 것:  uv run python -m server.tools.osc_smoke <인자...>
    exit=3

**PYTHONPATH 없이 재현됐다** — 합성 트리가 진짜 venv 를 대신한다는 가정이 섰다.

같은 인터프리터로 `-m` 형태를 쏘면 cwd 가 이겨 **exit 0** 이다(가드 오탐 없음).

### 전환기 관측 — 가드 모듈이 없는 남의 트리

아직 이 커밋을 못 받은 형제 트리(t86, `86fee6c`)의 인터프리터로 쏘면 가드가 아니라
`ModuleNotFoundError: No module named 'server.tools.tree_identity'` 로 죽는다.
메시지는 못 주지만 **조용히 돌지는 않는다.** 다른 트리들이 이 커밋을 받으면 사라진다.

## 6. 기존 경계 (AC-007)

| 검사 | 결과 |
|---|---|
| `make ci-local` (ruff format · ruff check · 빠른 부분집합 296건) | **통과** · 15.3s |
| `ruff check server/tools/` · `ruff format --check server/tools/` | **통과** · 21 files formatted |
| 영향권 검사 7파일 (architecture · introspect_probe · probe_preflight · provider_smoke · tree_identity · lxseq_preset ×2) | **38 passed** |
| 도구 19개 `-m … --help` | **19/19 exit 0** — 오탐 0 |

`test_architecture.py` 의 단일 초크포인트 경계는 그대로다 — 가드는
`server.bridge` 도 `pythonosc` 도 임포트하지 않는다.

임포트 순서는 내가 정렬하지 않고 `ruff check --fix` 에 맡겼다(7파일에서 isort 가
내 정렬과 달랐다). 찾는 도구가 판정까지 하게 두지 않는다는 원칙의 반대편 — 정렬은
정렬 도구가 판정한다.

## 7. 전량 스위트 · CI

로컬 전량은 돌리지 않았다 — 부하 걸린 개발 기계의 전량은 코드가 아니라 기계를 잰다
(이 저장소 Makefile 이 같은 이유로 `ci-local` 범위를 좁혀 놓았다). 전량은 깨끗한
환경에서 CI 가 돌린다: `.github/workflows/test.yml` 의 `uv run pytest -q -rs` + vitest.

**CI 결과는 §8 에 푸시 후 채운다. 채워지기 전까지 AC-003 은 로컬 근거만 가진다.**

## 8. CI 실행 결과 (AC-003)

PR [#152](https://github.com/jjjh7401/AI-Lighting_Console/pull/152) ·
[run 32815265153](https://github.com/jjjh7401/AI-Lighting_Console/actions/runs/32815265153) · **pass · 5m33s**

    Python : 10319 passed, 16 skipped, 1 warning in 285.95s
    UI     : 21 test files, 500 passed

### CI 가 검사한 것은 내 브랜치가 아니라 머지 결과다

`on: pull_request` 이므로 `actions/checkout` 은 PR head 가 아니라 **머지 커밋**을 받는다.
로그가 그렇게 말한다:

    HEAD is now at ec0b8a6 Merge c86253d... into 5a6843a...

이건 손해가 아니라 이득이다 — 「내 트리에서 초록」이 아니라 **「머지 후 초록」**을 잰 값이다.

### 기준선 대조 — +30 을 쫓아가 +4 로 좁힌 기록

처음 대조에서 숫자가 안 맞아 그대로 적지 않고 원인을 쫓았다.

| 커밋 | 통과 | 비고 |
|---|---|---|
| `86fee6c` (내 브랜치의 base) | 10289 | 브랜치를 뗀 자리 |
| `5a6843a` (main 최신) | 10315 | 내 브랜치에 **없다**(조상 아님, 실측) |
| `ec0b8a6` (= 내 head + main 최신 머지) | **10319** | CI 가 실제로 잰 것 |

- base 대비 **+30** 인데 내가 추가한 검사는 4건뿐이었다.
- 파라미터화 검사가 내 파일을 세는지 의심해 SPEC·리포트 디렉터리를 잠시 치우고
  다시 수집했다 — **10309 → 10309**, 기여 0. 원인이 아니었다.
- 실제 원인: **CI 가 머지 결과를 쟀다.** 나머지 26건은 main 이 `5a6843a` 에서 얻은
  것이고 내 것이 아니다. 올바른 기준선은 10315 이고 증가분은 **정확히 내 검사 4건**이다.

**실패 0 · 스킵 16 (기준선과 동일).**

### 이 문서의 커밋은 위 실행보다 뒤다

`verdict.md` 가 자기 CI 결과를 적으므로, 이 절을 커밋하면 head 가 밀리고 위 run 은
그 이전 커밋(`c86253d`)을 잰 것이 된다. **낡음이지 거짓이 아니다** — 위 표의
SHA 와 run 번호가 무엇을 잰 값인지 명시한다. 이 문서 커밋 이후의 CI 는 문서 변경만
더한 것이라 코드 판정은 그대로다.


## 9. 미검증으로 남기는 것 (Gap)

- **과거에 생산된 콘솔 증거가 실제로 오염됐는지는 재지 않았다.** 이 카드는 위험을
  재현하고 막았을 뿐, 소급 검증은 하지 않았다.
- **정상 실행 형태 5팔(A·C·D1·E·F) 밖의 호출 형태는 관측 범위 밖이다.** 오탐이
  없다는 주장은 그 다섯 팔과 도구 19개 `--help` 에 한한다.
- **실기는 트리 2그루로 쟀다** — 합성 `/tmp/t80real` 과 형제 `t86`. 45그루 전수가 아니다.
- **A안(호출을 임포트 뒤에)의 근거는 M0 측정이다.** 감사 훅이 내지 않는 부작용
  (모듈 전역 변형 · `atexit` 등록 · 스레드 기동)은 못 본다. 의존성이나 모듈 구성이
  바뀌면 다시 재야 하고, 뒤집히면 B안(`per-file-ignores` 1줄)이 대기 중이다.
- **완전성 검사는 `server/tools/` 만 훑는다.** 다른 디렉터리에 같은 형태의 도구가
  생기면 이 검사는 0을 낸다 — 그때는 범위를 넓혀야 하고, 넓히는 것 자체가 결정이다.
- **가드는 `assert_same_tree(__file__)` 문자열의 존재만 검사로 확인된다.** 호출이
  주석 처리되거나 `if False:` 아래로 들어가면 완전성 검사는 통과한다. 그 형태까지
  막으려면 AST 검사가 필요하고, 이 카드는 거기까지 가지 않았다.
