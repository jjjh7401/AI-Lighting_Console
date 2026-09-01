# t226 — `moai gate` 는 실효가 아니고, ast-grep 을 부르는 자리는 커밋 경로가 아니다

베이스: `origin/main 24f11e5` · 브랜치: `WT-hook-observability`
환경: 자체 워크트리(`.claude/worktrees/t226`) · 자체 venv(`uv sync --group dev`) · 콘솔 접촉 0
증거 경로: 배차서가 지정한 `.moai/reports/t226/` 는 **다른 작업이 점유**(커밋 `d0481ab`, PR #271, 퇴화 가드)라 리드 승인 후 이 디렉터리로 옮겼다.

## 0. 두 줄 판정

- **A.** `moai gate` 는 이 저장소에서 **실효가 아니다.** 스테이징된 파이썬 구문 오류를 보고도 `exit 0` · 출력 0바이트다. 세 갈래 중 「검사가 실효 아님」이며, 「대상 0건」도 「계기 고장」도 아니다. **따라서 어떤 카드도 「gate 통과」를 검증 근거로 쓸 수 없다.**
- **B.** `ast-grep domain rule scan results:` 를 내는 자리는 **커밋 경로가 아니다.** 산출 문자열은 `moai` 바이너리 안에 있고, 그것을 태우는 훅은 매처가 `Write|Edit|MultiEdit` 인 **PostToolUse** 다. `Bash` 도 `git commit` 도 그 매처에 안 걸린다.

## 1. A — `moai gate` 실효 확인

### 1.1 두 팔 대조군

| 팔 | 명령줄 | 결과 |
|---|---|---|
| 양성(계기가 잡는가) | `.venv/bin/python -m ruff check server/t226_probe_syntax_error.py` | **Found 4 errors** |
| 팔1(gate 가 잡는가) | 구문오류 `.py` 스테이징 후 `moai gate` | **exit 0 · stdout 0B · stderr 0B** |
| 팔1'(도구 부재 배제) | `PATH="$PWD/.venv/bin:$PATH" moai gate` | **exit 0 · 0B** (동일) |
| 팔2(계기가 벙어리인가) | `moai ast-grep --dry server` | **3,923B · `rules to apply (26)`** |
| 팔2'(gate 가 말하기는 하는가) | `/tmp/t226-min2` 에서 `moai gate` | **exit 1 · stderr 697B** |

팔2 둘이 「대상 0건」과 「계기 고장」을 동시에 배제한다. 남는 갈래는 하나다.

### 1.2 부가 실측 셋

1. **시간** — 이 트리에서 gate 는 `elapsed=1.01s`. `npm test`(vitest 500건)를 돌렸다면 불가능하다.
2. **디버그 로그** — `MOAI_LOG_LEVEL=debug moai gate` 는 3,868B 를 내는데 **설정 로드에서 끝나고 단계 실행 로그가 0건**이다. min2 의 같은 로그에는 `pretest` · `npm ci` 실행이 찍힌다. (증거: `gate-debug-silent.txt` 대 `gate-minimal-loud.txt`)
3. **도구의 자기 선언** — `moai gate --help` 가 적고 있다: *"Exit code 0: gate passed (**or no recognized language toolchain detected**)."* exit 0 이 두 뜻을 겸한다는 것은 추론이 아니라 도구의 선언이다.

### 1.3 뿌리 — 어디까지 좁혔나

`/tmp/t226-min2` 에 이 저장소의 조각을 하나씩 이식하며 쟀다. **전부 여전히 말했다** = 그 축이 원인이 아니다.

| 이식한 것 | min2 결과 | 판정 |
|---|---|---|
| `gate.yaml` 단독 | exit 1 · 405B | 원인 아님 |
| 설정 30개 전량 | exit 1 · 405B | 원인 아님 |
| 워크트리 형태(min2 의 워크트리) | exit 1 · 703B | 원인 아님 |
| 마커 둘(py+node) | exit 1 · 405B | 원인 아님 |
| 이 저장소의 실제 `package.json` | exit 1 · 1,482B | 원인 아님 |
| `.python-version` + `uv.lock` | exit 1 · 1,482B | 원인 아님 |
| `astgrep-rules/` + 자격증명 파일 | exit 0 · **0B** | — (아래) |
| **node 마커를 치우고 파이썬만** | **exit 0 · 0B** | **갈렸다** |

**갈린 것은 하나다: 파이썬만 있는 프로젝트에서 gate 는 재현되게 침묵한다.**

그런데 이 저장소엔 node 마커도 있다 — 리드 힌트(「node 마커가 `ui/` 하위일 것」)는 **반증됐다**: 루트에 `package.json` · `package-lock.json` 둘 다 있고 `"test": "npm --prefix ui run test"` 스크립트도 있다. 그런데도 침묵한다. **이 자리는 안 갈렸다.**

리드 지시 프로브(트리 축 가르기): `origin/main` 에서 **깨끗한 새 워크트리**를 떠서 `moai gate` → **exit 0 · 0B**(증거: `gate-clean-worktree-silent.txt`). 리드 판정표대로 **원인은 트리가 아니라 저장소 내용**이고, 주 체크아웃 실행은 값이 없어졌다.

## 2. B — ast-grep 출처

### 2.1 커밋 경로는 범인이 아니다 (실제 커밋 2회)

합성 호출을 안 썼다. 이 워크트리 안에서 실제 `git commit` 을 돌렸다.

| 회차 | 스테이징한 것 | 커밋 출력의 스캔 산출 |
|---|---|---|
| 1 | 무해한 `.keep` | **0건** (663B, 전부 git 자신의 메시지) |
| 2 | **규칙에 걸리는 자격증명** `.ts` | **0건** (644B) |

2회차가 결정적이다. 미끼가 실제로 걸린다는 것은 따로 쟀다(양성 대조군, 아래).
경로 명시: 두 커밋 모두 `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t226` 에서 났다. 리드가 본 출력의 `/tmp/verify-main-1432900/` 와 **다른 트리**다.

### 2.2 미끼의 양성 대조군 — 첫 미끼는 내가 틀렸다

첫 미끼 `password = "hunter2"` → `moai ast-grep` **`no findings`**. 규칙 문면을 읽으니 술어가 실제 키 접두사(`sk-` · `AKIA…` · `ghp_…`)였다. 미끼를 규칙에 맞추니:

    moai ast-grep ui/src/t226_probe_cred.ts
    exit=1 · findings (1): [sec-hardcoded-credential-typescript] (error)

**계기는 멀쩡했고 미끼가 틀렸다.** 대조군이 없었으면 「스캔이 안 돈다」로 잘못 결론냈을 자리다.

### 2.3 산출을 내는 자리 — 바이너리 안, PostToolUse 매처

    strings ~/.local/bin/moai | grep "ast-grep domain rule scan"
      → 바이너리 안에 실재
    같은 덤프에서: post_tool__ast_grep_scan.py · QualityGate.Run.astgrep

    jq '.hooks.PostToolUse[] | .matcher' .claude/settings.json
      → "Write|Edit|MultiEdit"

배제한 것들(전부 실측):

- `.git/hooks/pre-commit` 은 `moai gate` **만** 부른다(`grep -nE "ast-grep|moai " → 65행 `moai gate` 하나`). ast-grep 직접 호출 0건
- `moai init` 이 새로 까는 **최신 훅 템플릿도 73행, ast-grep 0건** — 우리 훅이 낡아서가 아니다
- `moai gate` 자체도 아니다: min2 에 규칙셋과 자격증명 파일을 넣고 앞 단계를 통과시켜도 **0B**
- 훅 스크립트 본문 22개에 ast-grep 문자열 **0건**(`grep -rlnE .claude/hooks/moai/`)
- 훅 stderr 로그(2.3MB)에도 **0건**

**결론**: 그 산출은 PostToolUse 훅 계보가 낸다. `Bash` 는 매처에 없으므로 `git commit` 을 Bash 로 돌린 전사에서는 **인접해 보일 뿐 커밋이 낸 것이 아니다.** 리드가 「git commit 출력에 섞여 나왔다」로 읽은 것은 **동거 산출물의 오귀속**으로 보인다.

## 3. 안 잰 것 (Gap)

- 🔴 **PostToolUse 를 실제로 못 쐈다.** 매처가 요구하는 `Write`/`Edit` 가 이 워크트리 세션에서 **둘 다 path traversal 로 거절**된다(규약 §2 가 적어 둔 그대로, 탈출로는 `Bash` 뿐인데 `Bash` 는 매처 밖이다). 그래서 §2.3 의 결론은 **다섯 배제 + 두 문자열 + 매처**로 이뤄진 것이고 **발화 재현이 아니다.** 워크트리 밖 세션이면 한 번의 `Write` 로 닫힌다 — 리드 판단 요청.
- **합성 호출은 안 했다.** t219 가 그것으로 실패했고 카드가 금지했다. 그래서 「post-tool 이 원인이다」를 **발화로 증명하지 않았다** — t219 의 유보를 그대로 이어받는다.
- **파이썬 침묵의 뿌리를 못 좁혔다.** 여섯 축을 반증했고 「파이썬만 → 침묵」까지 왔으나, node 마커가 있는데도 침묵하는 이 저장소의 자리는 안 갈렸다.
- **주 체크아웃 gate 거동 미측정** — 리드가 불허했고, 깨끗한 워크트리 프로브가 그 값을 대체했다.
- `moai` 바이너리 소스는 안 읽었다(이 저장소 것이 아니다, 카드 함정 4). 전부 실행으로 쟀다.

## 4. 잔여 위험

- **A 의 함의가 넓다.** 이 게이트는 파이썬 변경에 대해 아무것도 안 본다. 과거 카드가 「gate 통과」로 적은 초록은 **재검토 대상**이다. 다만 이 저장소엔 pytest CI 가 따로 있어(`.github/workflows/test.yml`) 회귀 자체가 무방비였던 것은 아니다 — **게이트가 무효인 것과 검증이 없는 것은 다른 진술이다.**
- **B 의 결론은 배제로 이뤄졌다.** 배제는 「여기가 아니다」를 쌓을 뿐 「저기가 맞다」를 발화로 세우지 않는다. 매처와 바이너리 문자열이 강하게 가리키지만, 한 번의 `Write` 재현이 그것을 사실로 바꾼다.
- **미끼가 틀릴 수 있다는 것을 한 번 겪었다.** 이 판정의 다른 술어들도 같은 위험을 진다 — 각 절에 명령줄을 실은 이유다.

## 5. 카드 전제의 출처 — 리드 오귀속 (리드 본인 정정, 2026-09-01)

이 카드 본문의 「부르는 자리가 gate 는 아니지만 **커밋 경로 어딘가에는 있다**」는 전제는
리드의 직접 관측에서 나왔다: `git commit` 출력에 스캔 산출이 섞여 나왔다는 것.

**그 관측은 오귀속이었다** — 리드가 본인 정정으로 확인했다. 커밋을 `Bash` 도구로 돌린
전사에서 `Write`/`Edit` 의 PostToolUse 산출이 **인접해** 보였고, 그 인접이 인과로 읽혔다.

§2.1 의 실제 커밋 2회(2회차는 규칙에 걸리는 미끼 스테이징)가 산출 **0건**을 냈고,
§2.3 의 매처(`Write|Edit|MultiEdit`)가 `Bash` 를 배제한다. 둘이 같은 방향을 가리킨다.

🔴 **다음 사람에게**: 카드 문면의 「커밋 경로」를 근거로 다시 뒤지지 마라. 그 전제는
철회됐다. 남은 미지는 커밋 경로가 아니라 **PostToolUse 발화 재현**(§3 첫 항목)이다.

**전사에서의 인접은 인과가 아니다.** 이 회차가 그것을 두 번 겪었다 — 리드의 오귀속과,
내 첫 미끼(`hunter2`)가 `no findings` 를 낸 것을 「스캔이 안 돈다」로 읽을 뻔한 것.
둘 다 대조군이 갈랐다.
