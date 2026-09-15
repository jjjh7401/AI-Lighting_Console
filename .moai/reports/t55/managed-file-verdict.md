# t55 — `.git/hooks/pre-push` 관리 주체 판정

트리: `.claude/worktrees/t55` · 브랜치 `WT-prepush-gate` · HEAD `1f1ed25` (= origin/main)
측정일: 2026-08-24 · 측정자: run 레인 (session 19f2ce27)

## 주장 (Claim)

`.git/hooks/pre-push` 는 **moai 관리 파일이다.** moai-adk 3.1.2 에 내장된 템플릿
`templates/.git_hooks/pre-push` 의 산출물이고, `moai update` 는 파일 2행의
마커 `# MoAI-ADK pre-push hook` 이 **있으면 덮어쓰고, 없으면 보존한다.**

## 증거 (Evidence)

### E1 — 훅 본문이 moai 바이너리 안에 그대로 들어 있다

    $ strings /Users/studiox/.local/bin/moai | grep -n "MoAI-ADK pre-push hook"
    14720:# MoAI-ADK pre-push hook
    14787:# MoAI-ADK pre-push hook      (동일 템플릿 2사본)

    $ strings /Users/studiox/.local/bin/moai | grep -o "templates/.git_hooks/pre-push"
    templates/.git_hooks/pre-push

`moai update --help` 에도 `--no-hooks  Skip git hook installation (REQ-CIAUT-002)` 가 있다.

### E2 — 살아 있는 훅은 템플릿과 바이트 동일

    $ shasum <primary>/.git/hooks/pre-push
    4b1fabd63358789a5816a46a969c70a3e13c1e6b
    $ shasum <격리 클론에 moai update 가 방금 설치한 훅>
    4b1fabd63358789a5816a46a969c70a3e13c1e6b

즉 현재 저장소의 훅에는 로컬 수정이 하나도 없다.

### E3 — 2팔 실험 (격리 클론, 공유 트리 무접촉)

격리 위치: `<scratchpad>/hookprobe/clone` (`git clone --depth 1 file://<primary>`).
갓 만든 클론에는 훅이 **하나도 없다** (`ls .git/hooks | grep -v sample` -> 빈 출력)
— 훅은 저장소 추적물이 아니라 클론 단위 산출물이라는 카드의 관측과 일치.

| 팔 | 심은 훅 | `moai update --templates-only --yes` 이후 | 판정 |
|---|---|---|---|
| A | 마커 **있음** + 본문 `ARM-A-SENTINEL` | `grep -c ARM-A-SENTINEL` -> **0**, sha `302506e7...` -> `4b1fabd6...`, 출력에 `Pre-push hook installed (.git/hooks/pre-push)` | **덮어씀** |
| B | 마커 **없음** + 본문 `ARM-B-SENTINEL` | `grep -c ARM-B-SENTINEL` -> **1**, 본문 그대로, 설치 메시지 없음 | **보존됨** |

B 는 음성 대조군이다. A 만 보면 "항상 덮어쓴다"와 구별이 안 되는데,
B 가 살아남았으므로 **레버는 마커 한 줄**이라는 것이 갈린다.

### E4 — 코드가 스스로 밝힌 두 갈래 (문자열 전수)

`pre-push hook` 결과 메시지는 전부 다음뿐이다 (sort -u):

    Pre-push hook installed (.git/hooks/pre-push)
    existing pre-push hook preserved (no MoAI-ADK marker found)
    pre-existing user hook found without MoAI-ADK marker
    pre-push hook install failed

"마커 있는 훅을 보존한다"는 메시지는 **존재하지 않는다.** 갈래는 둘뿐이다.

## Baseline 귀속

전부 이 트리(`.claude/worktrees/t55`, HEAD `1f1ed25`)와 격리 클론에서
이번에 직접 실행해 관측한 출력이다. 옮겨온 값 없음.

## 미검증 (Gaps)

- **`moai update --dry-run` 은 이 질문에 답하지 못한다.** 실제로 돌려봤고
  출력에 훅 관련 행이 한 줄도 없다 (managed cleanup 400파일만 보고). 배차서가
  지목한 계기는 이 판정의 계기가 아니었다 — 위 E1~E4 로 대신 쟀다.
- `moai update` 가 아닌 `moai init` 경로의 훅 처리는 안 봤다.
- 3.1.2 가 아닌 다른 moai 버전의 동작은 안 봤다.
- `.git/hooks/pre-commit` 도 같은 형태로 설치되지만(`Pre-commit hook installed`
  관측) 마커 이름/본문은 이 카드에서 안 읽었다.

## 잔여 위험

- 마커를 떼어 사용자 훅으로 만들면 보존되지만, 그 순간부터 upstream 훅 수정이
  영영 안 내려온다. 되돌리려면 사람이 다시 붙여야 한다.
- 실험은 `--templates-only` 로 했다. 바이너리 갱신까지 도는 전체 `moai update`
  에서 훅 처리가 같은 경로인지는 별도로 재지 않았다.

## 처방에 미치는 영향

| 후보 | 지속성 |
|---|---|
| (b) 훅 본문을 고쳐 Makefile 부재를 실패로 낸다 (마커 유지) | X 다음 `moai update` 에 지워진다 |
| (b') 같은 수정 + 마커 삭제 | O 남지만 upstream 과 영구 분기, moai 가 못 본다 |
| (a) 저장소 루트에 `Makefile` 추가 | O Makefile 은 **추적 파일**이라 moai update 와 무관. 갈래 (1)을 skip->pass/fail 로 바꾼다 |
| 갈래 (4) `enforce_on_push: false` | O `.moai/config/sections/git-convention.yaml` 은 설정 파일 — 훅을 안 건드리고 고칠 수 있다 |
| 갈래 (2)(3) (moai 부재 / SUBJECTS 빈 문자열) | 훅 본문 안 — (b)/(b') 와 운명을 같이한다 |
| 문서 결함 (L3/L49 거짓 힌트) | 템플릿 안에 있다 -> 로컬 수정은 지워진다. **upstream 버그 리포트** 감이다 |

---

# t55 — 처방 (a) 실행: 루트 Makefile 로 ci-local 실재화

리드 결정: (a) 루트 Makefile. 커밋 `13434bc` (branch `WT-prepush-gate`, base `1f1ed25`).

## 주장 (Claim)

1. ci-local 이 실재한다 — 훅이 더 이상 조용히 건너뛰지 않는다.
2. 범위 **안** 빨강은 푸시를 **막는다**.
3. 범위 **밖**(`src/Lighting_Designer/`) 빨강은 **안 막힌다** — 구멍은 실측된 사실이다(t63 입력).
4. ci-local 의 세 단계가 **각각** 실패할 수 있다 — 공허한 검사가 아니다.

## 증거 (Evidence)

### 초록 기준선 — 전량 스위트

    $ uv run pytest -q -rs --durations=40
    10023 passed, 12 skipped, 1 warning in 153.21s   exit=0
    (load avg 3.97, 트리 .claude/worktrees/t55 @ 1f1ed25)
    전문: .moai/reports/t55/full-suite-durations.txt

### 초록 — ci-local

    $ time make -s ci-local
    (출력 없음)   exit=0   14.495s total

### 단계별 날조 대조군 — 세 단계 각각이 죽는다

대상 `server/__init__.py` (원본 sha `dfc03203…`, 매 회차 후 복원해 sha 재확인).

| 단계 | 심은 결함 | 결과 | 판정 |
|---|---|---|---|
| fmt | `x = [ 1,2 ,3 ]` 추가 | `Would reformat: server/__init__.py`, `make: *** [fmt] Error 1`, exit 2 | KILL |
| lint | `import os` 추가 | `F401 os imported but unused`, `make: *** [lint] Error 1`, exit 2 | KILL |
| test-fast | `import server.bridge  # noqa: F401` 추가 | 3건 F — `REQ-MVP-029 single-chokepoint violation`, `--- ci-local: 빠른 단위 부분집합 실패 ---` | KILL |

test-fast 대조군은 **선택이 이빨을 갖는다**는 것까지 잰다. pytest 가 돌기만 한 게
아니라, 지명 나열한 12파일 중 `test_architecture.py` 의 아키텍처 경계 가드가
날조한 위반을 실제로 잡았다.

### 발사 대조군 — 실제 `git push` 두 팔

격리 bare 리모트(`<scratchpad>/t55-probe-remote.git`)에 대고 진짜 훅을 통과시켰다.
origin 은 건드리지 않았다.

| 팔 | 트리 | `git push` exit | 훅 로그 |
|---|---|---|---|
| 초록 | 깨끗 | **0** (`* [new branch] WT-prepush-gate`) | `pass 15s` |
| **A — 범위 안 빨강** | `server/__init__.py` 에 `import os` | **1** — `[pre-push] FAILED: local CI mirror reported errors.` `error: failed to push some refs` | `fail 0s` |
| **B — 범위 밖 빨강** | `src/Lighting_Designer/90_빌드파이프라인/exec_data.py` 에 `import os` + `y = [ 1,2 ,3 ]` | **0 — 푸시 성공** | `pass 14s` |

훅 로그 전문 (이 저장소 역사상 첫 `pass`/`fail` 행이다 — 직전까지 165/165 가 skip):

    1787583558	studiox	WT-prepush-gate	pass	15s
    1787583578	studiox	WT-prepush-gate	fail	0s
    1787583629	studiox	WT-prepush-gate	pass	14s

A 만 있으면 "막긴 막는다"까지고, B 가 있어야 **어디까지 안 막는지**가 가정에서
실측으로 바뀐다. B 는 t63(`src/Lighting_Designer/` 570건)의 입력이다.

## Baseline 귀속

전부 `.claude/worktrees/t55` @ `13434bc` (base `1f1ed25`)에서 이번에 직접 실행해
관측했다. 대조군 대상 두 파일은 회차마다 백업본에서 복원하고 sha 로 확인했다
(`dfc03203…`, `b2820c99…` 둘 다 원본과 일치).

## 미검증 (Gaps)

- **A 팔은 fmt 단계에서 죽었다** — `import os` 를 docstring 뒤에 붙이니 포맷
  드리프트가 먼저 걸렸다. 발사 수준에서 **lint 단계만 단독으로** 막는 것은 따로
  안 쟀다. lint 단독 사망은 단계별 대조군에서만 확인했다.
- `typecheck` 타깃은 **실행해 보지 않았다** — 이 워크트리에 `ui/node_modules` 가
  없다. 의존성 없으면 실패하도록 지었지만, 있는 트리에서 tsc 가 초록/빨강을
  가르는 것은 미측정이다. ci-local 밖이라 게이트에는 영향 없다.
- `require-uv` 실패 갈래(uv 부재)는 미측정 — uv 를 지울 수 없었다.
- 원격 `origin` 에 대고는 안 쐈다. 격리 bare 리모트만 썼다.
- 다른 개발자 기계/CI 러너에서의 ci-local 소요는 미측정 (여기 14.5s, load 3.97).

## 잔여 위험

- ci-local 은 이제 **모든 워크트리의 모든 푸시**에 14~15초를 얹는다. 부하가 큰
  기계에서는 더 길어질 수 있다.
- `FAST_TESTS` 12파일은 손으로 유지하는 목록이다. 새 가드가 생겨도 자동으로
  안 들어온다 — 목록이 자라기만 하는지 검사하는 장치는 이 카드에 없다.
- 범위 밖(`src/Lighting_Designer/`, `packaging` 포맷)은 여전히 무방비다. B 팔이
  그것을 증거로 남겼다. t63 몫.
- 훅 자체의 나머지 조용한 갈래(②`moai` 부재 ③`SUBJECTS` 빈 문자열
  ④`enforce_on_push: false`)는 훅 본문 = moai 관리 파일이라 이 카드로 못 고친다.

## 닫기 전 전량 재측정 (Makefile 이 올라간 트리에서)

첫 전량은 `1f1ed25`(Makefile 없는 트리)에서 잰 값이라, 루트에 파일이 하나
늘어난 것이 어떤 가드에 걸리는지는 그 값으로 답할 수 없다. 그래서 `13434bc`
에서 다시 쟀다.

    $ uv run pytest -q -rs        # 트리 .claude/worktrees/t55 @ 13434bc
    10023 passed, 12 skipped, 1 warning in 147.00s   exit=0
    전문: .moai/reports/t55/full-suite-at-13434bc.txt

숫자와 skip 목록이 `1f1ed25` 회차와 동일하다 — 루트 Makefile 추가로 깨지는
가드는 없다.

미측정: vitest(UI 전량)는 이 트리에 `ui/node_modules` 가 없어 안 돌렸다.
이 변경은 파이썬/TS 소스를 한 줄도 건드리지 않으므로 UI 에 닿을 경로가 없다고
보지만, **재지는 않았다.** CI 가 잰다.

## 머지 (2026-08-24)

    PR   https://github.com/jjjh7401/AI-Lighting_Console/pull/124
    head 13434bc24f04a8316813b8e4cdb82a784cce304d
    CI   test  pass  5m26s  (pytest 전량 + vitest 전량)
         → 로컬에서 못 잰 vitest Gap 이 여기서 닫혔다
    push origin 푸시가 자기 훅을 탔고 통과했다 — 훅 로그 `pass 14s`
    merge --squash → origin/main `8189971` (state=MERGED, 2026-08-24T15:29:12Z)

종료 코드로 판정하지 않았다. `gh pr view 124 --json state,mergeCommit` 와
`git log origin/main` 을 되읽어 확인했고, 내용도 대조했다:

    $ git show origin/main:Makefile | shasum   →  2176adae02fdeac90a276e6610068c7da761a533
    $ shasum Makefile                          →  2176adae02fdeac90a276e6610068c7da761a533   (128행, 동일)

### CodeRabbit — PASS 도 FAIL 도 아닌 **미발동**

이 저장소에는 CodeRabbit 이 붙어 있지 않다. 이 PR 에서 직접 확인:

    $ gh api repos/.../commits/13434bc2.../check-runs --jq '.total_count, [.check_runs[].name]'
    1
    ["test"]
    $ gh api repos/.../pulls/124/reviews --jq 'length'
    0

양성 대조군이 있다 — 같은 질의가 `test` 는 정확히 집어낸다. 그러므로 이 부재는
질의 실패가 아니라 실제 부재다. 선례도 있다(카드 t48: `#117·#116·#110·#104`
같은 상태에서 셋이 머지됨). `kanban-dispatch.md` 의 CodeRabbit 절은 **행이 있을 때
그 행을 어떻게 읽는지**를 정한 것이라 행이 없으면 발동하지 않는다.
「미통과」가 아니라 **미발동**이다.

### 머지 후 달라진 것

이 순간부터 이 저장소의 **모든 푸시가 ci-local(실측 14~15초)을 탄다.**
푸시가 느려지거나 막히면 고장이 아니라 게이트가 켜진 것이다.

### 남긴 것

- **t62** — 훅 주석 L3/L49 의 거짓 바이패스 힌트. 템플릿 안이라 upstream 몫.
- **t63** — `src/Lighting_Designer/` ruff 570건. **B 팔이 그 구멍을 실측으로 남겼다**
  (범위 밖 빨강이 `git push` exit 0 으로 통과). 추론이 아니라 관측이다.
