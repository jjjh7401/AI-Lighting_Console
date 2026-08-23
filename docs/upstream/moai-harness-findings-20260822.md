# MoAI 하네스 상류 보고 후보 — 2026-08-22

카드 t16(`/code-review` 하네스 결함) 판별 결과 중 **이 저장소에서 고칠 수 없는 5건**이다.
이유는 하나로 같다 — 근거 파일이 `moai update` 관리 경로에 있어, 로컬에서 고쳐도 다음
동기화가 덮는다.

발사(`/moai feedback` → 상류 GitHub 이슈 생성)는 하지 않았다. 저장소 밖으로 나가고 공개되는
일이라 감독 결정 사항이다. 이 문서는 그 결정이 내려질 때까지 목록이 유실되지 않게 남기는
추적 대상 사본이다.

## 판별 근거 — 왜 로컬에서 못 고치는가

도메인 전용 도구로 쟀다. 텍스트 추정이 아니다.

```
$ moai update --templates-only --dry-run --yes
[dry-run] managed cleanup  399 files removed under managed paths (398 re-deployed from templates, 1 not restored)
·  .moai/config removed entirely  contents backed up and restored via 3-way merge
```

| 경로 | 동작 | 로컬 수정 |
|---|---|---|
| `.claude/**` | 삭제 후 템플릿 재배포 | 소멸 |
| `.moai/config/**` | 백업 후 3-way 병합 복원 | 생존 가능 |
| `.gitignore` 의 User Custom Patterns 구역 | 병합 | 생존(실측) |

생존 여부는 추정이 아니라 사례로 확인했다. `.claude/` 아래 파일은 커밋 이력이 템플릿 동기화
`f30ab4c` 와 최초 커밋 `2b8c28e` 둘뿐이다 — 로컬 편집이 살아남은 전례가 없다. 반대로
`.gitignore` 는 로컬 커밋 `76e7c51` 이 넣은 `.playwright-cli/` 가 `f30ab4c`(14 insertions,
17 deletions)를 넘어 249행에 남아 있다.

---

## U-2 (최우선) — 문서 4곳이 존재하지 않는 설정 키를 안내한다

**오타가 아니라 조용한 무동작이다.** 우리 문서를 따라 설정한 사람은 아무 효과도 없는 키를 넣고
설정을 마쳤다고 믿는다. 실패 신호가 없으므로 스스로 발견할 수 없다.

실제 키 경로는 `workflow.audit.model` 이다. 문서가 쓰는 `audit_model` 은 설정 트리에 없다.

```
$ grep -rn "audit_model" .moai/config/
(출력 없음)

$ moai doctor config dump
"workflow.audit.model": {
  "value": "claude",
  "source": "builtin",
  "origin": "internal/config/defaults.go",
  "overridden": false,
  "default": true
}
```

부수 결함 둘이 같은 자리에 있다.

1. **기본값 기재가 서로 다르고 한쪽이 반증된다.**
   - `.claude/skills/moai-ref-cross-model-audit/SKILL.md:37` — `audit_model: claude` (default) → 실측과 일치
   - `.claude/rules/moai/core/moai-mcp-tools.md:73` — `codex+glm` (default) → **틀림**

   이 오기는 무해하지 않다. 문서를 믿고 `codex+glm` 을 설정한 사용자는 지금 호출되지 않는
   외부 백엔드(codex · z.ai GLM)를 발화시키게 된다. 동작 변경이 문서 신뢰의 결과로 일어난다.

2. **enum 집합이 두 문서에서 다르다.** SKILL.md 는 {claude, codex, glm, multi}, moai-mcp-tools.md
   는 {codex+glm, glm, codex, none} 이다. 겹치는 토큰은 codex · glm 둘뿐이다.

근거 파일:행
- `.claude/rules/moai/core/moai-mcp-tools.md:73`
- `.claude/skills/moai-ref-cross-model-audit/SKILL.md:12, 29, 37-40`
- `.claude/agents/moai/plan-auditor.md:168, 172, 468`
- `.claude/agents/moai/sync-auditor.md:147, 151, 166`

상류에 청하는 것
- (a) `moai-mcp-tools.md:73` 의 기본값을 `claude` 로 정정
- (b) 두 문서의 enum 을 하나로 통일
- (c) 키 이름을 `audit_model` → `workflow.audit.model` 로 전 참조 지점 교정
- (d) `workflow.audit.gates.{claude, codex, glm}` 을 문서화 — 실재하고 기본값이
  required / required / advisory 인데 문서 어디에도 없다

미검증으로 남긴 것: **enum 유효값의 전수.** 덤프는 현재 값만 보여준다. 어느 집합이 코드의 진짜
enum 인지는 값을 넣어 봐야 알 수 있고, 그것은 동작 변경이라 하지 않았다.

---

## U-1 (MED) — /moai goal verb 문서가 실물과 어긋난다

실물을 CLI 로 쟀다.

```
$ moai goal --help
Verbs:
  goal arm "<condition>"   register + arm a goal
  goal status              print the active session goal state
  goal clear               clear the active session goal
  goal render              render the live goal dashboard to a self-contained HTML file
```

문서가 두 방향으로 틀린다.

- **없는 것을 있다고 다룬다** — `.claude/skills/moai/workflows/goal.md:79` 가
  `### /moai goal resume — deferred (follow-up), NOT delivered` 로 절 하나를 할애한다.
- **있는 것을 빠뜨린다** — `render` 가 두 문서 어디에도 없다.
  `.claude/rules/moai/workflow/goal-directive.md` 는 "The delivered verbs are ... arm ...
  status ... clear" 로 셋만 적는다.

근거 파일:행
- `.claude/skills/moai/workflows/goal.md:79, 81, 87`
- `.claude/rules/moai/workflow/goal-directive.md` § What It Is

상류에 청하는 것: `resume` 절을 삭제하거나 CLI 에 존재하지 않음을 명시하고, 두 문서의 verb
목록에 `render` 를 추가할 것.

---

## U-3 (MED) — 폐지된 --team 이 카탈로그 멤버로 남아 있다

```
$ grep -n -- --team .claude/rules/moai/workflow/orchestration-mode-selection.md
245:| Team | Mode 3 (`agent-team`) — RETIRED | ... a forced `--team` flag emits
     MODE_TEAM_UNAVAILABLE and falls back per §C.1. The scale label is retained for
     backward-compat; it no longer resolves to a live team mode. |
```

같은 계열의 참조가 `.claude/` 아래 10개 이상 파일에 흩어져 있다 — `output-styles/moai/moai.md` ·
`rules/moai/workflow/{worktree-integration, spec-workflow, session-handoff,
session-handoff-examples}.md` · `commands/moai/{fix, mx, run}.md` ·
`agents/moai/manager-kanban.md` 등. 로컬에서 부분만 고치면 참조 지점 사이의 불일치가 오히려
커진다.

상류에 청하는 것: 폐지된 모드를 카탈로그에서 제거하거나, 하위호환으로 남길 경우 전 참조
지점에 폐지 표기를 일관되게 붙일 것.

---

## U-4 (LOW, 그러나 논쟁의 여지 없음) — 한 파일이 자기 자신과 정반대다

```
$ grep -n team .claude/rules/moai/workflow/spec-workflow.md
 89:| `/moai run` | ... | `autopilot` (harness `minimal`/`standard`); `team` (harness
    `thorough` + prereqs) | ...
107:- Harness `thorough` → default mode = `autopilot` (the former `team` auto-select is
    retired with the Agent Teams static layer; ...)
```

**같은 파일에서 18행 차이로 정반대다.** 89행 표는 harness `thorough` 의 기본 모드를 `team` 이라
하고, 107행 산문은 그 자동 선택이 폐지됐다고 한다.

근거 파일:행 — `.claude/rules/moai/workflow/spec-workflow.md:89` ↔ `:107`

상류에 청하는 것: 89행 표의 기본 모드 칸을 `autopilot` 으로 정정.

---

## U-5 (LOW) — lifecycle-dormant.log 에 회전이 없다

```
$ grep -rln "lifecycle-dormant" . --exclude-dir=.git
(출력 없음)
```

이 저장소 어디에도 생산자가 없다. `moai` 바이너리 내부다. 로컬에 고칠 대상 파일 자체가 없다.

상류에 청하는 것: 크기 또는 세대 상한에 의한 로그 회전 추가.

---

## U-6 (MED) — pre-commit 훅이 위험한 우회를 힌트로 광고한다

`moai gate` 가 실패할 때마다 `.git/hooks/pre-commit` 은 세 자리에서 같은 문장을 찍는다.

```
.git/hooks/pre-commit:28   [pre-commit] Override: SKIP_MOAI_PRECOMMIT=1 git commit
.git/hooks/pre-commit:54   (동일)
.git/hooks/pre-commit:68   (동일)
```

세 자리 모두 우회 방법만 알려주고, **그 우회가 무엇을 남기는지는 어디에도 없다.**
`SKIP_MOAI_PRECOMMIT=1` 로 만든 커밋은 게이트를 통과한 커밋과 겉보기로 구분되지
않는다. 나중에 그 커밋을 보는 사람은 검사가 돌았다고 믿는다. 트리에도 커밋 메시지에도,
검사가 건너뛰어졌다는 기록이 어디에도 남지 않는다.

이것이 가설이 아니라는 증거가 이 카드에서 나왔다. t13 의 수정 커밋은 pre-commit
게이트를 **통과했는데**, 같은 시점 전량 스위트는 빨갰다(t20 산출물의 서식 결함,
`6296af3`). 즉 게이트 통과와 검사 초록은 이미 갈려 있고, 훅은 그 간극을 넓히는
쪽만 안내한다.

근거 파일:행 — `.git/hooks/pre-commit:28, 54, 68`

로컬 불가 사유: 이 훅은 `moai update` 가 설치한다. `moai update --no-hooks` 플래그의
설명이 "Skip git hook installation" 인 것이 그 증거다. 로컬에서 문면을 고쳐도 다음
동기화가 덮는다.

상류에 청하는 것
- (a) 힌트 문면에 그 우회가 남기는 것을 명시할 것 — 게이트가 돌지 않은 커밋이 되며
  이력에 아무 표시도 남지 않는다는 사실
- (b) 또는 우회 커밋에 기계로 읽을 수 있는 표식(커밋 트레일러 등)을 남길 것. 그래야
  나중에 검사된 커밋과 갈라볼 수 있다

---

## U-7 (MED) — 템플릿이 같은 게이트 설정을 두 곳에 서로 반대값으로 배포한다

`ast_grep_gate` 블록이 배포 템플릿의 `gate.yaml` 과 `quality.yaml` 양쪽에 있고,
`block_on_error` 가 서로 반대값이다.

```
$ grep -n "block_on_error" <template-snapshot>/gate.yaml
32:    block_on_error: false

$ sed -n "89,96p" <template-snapshot>/quality.yaml
  ast_grep_gate:
    enabled: true
    rules_dir: ".moai/config/astgrep-rules"
    block_on_error: true
```

로컬이 만든 것이 아니다. 미머지 하네스 브랜치(49c235a)의 `quality.yaml` 89행과
템플릿 스냅샷의 같은 구간이 **바이트 동일**하다. `main` 의 `quality.yaml` 에는 그
블록이 아예 없다 — 즉 `main` 이 옛 템플릿 판이고, 새 템플릿이 중복을 들여온다.

로컬에서 지울 수 없다. `.moai/config` 는 삭제+재배포가 아니라 백업 후 3-way 병합으로
복원되므로, 지워도 다음 `moai update` 가 템플릿 쪽 값을 다시 들여온다.

미검증: 코드가 둘 중 어느 쪽을 읽는지는 확인하지 못했다. `moai` 바이너리 소스가 이
저장소에 없어 판독할 대상이 없다. 따라서 "어느 값이 실제로 적용되는가"는 상류만
답할 수 있다.

상류에 청하는 것: 한 곳으로 통일하거나, 둘 다 유지해야 한다면 어느 쪽이 우선인지
명시. 지금은 같은 이름의 설정이 두 파일에서 반대를 지시한다.

---

## U-8 (MED) — 워크트리에서 Write · Edit 도구가 막힌다

**상류: Claude Code** (MoAI 아님)

워크트리 격리 세션에서 `Write` · `Edit` 이 절대경로 · 상대경로 · 스크래치패드 경로 전부
`Path traversal detected: file is outside project directory` 로 거부한다. 같은 세션에서
`Read` 는 정상 동작한다 — 읽기는 되고 쓰기만 막힌다.

**재현 6회**: PARITY-001 plan · t15 리드 2회 · t16 sync · t13 sync · t21 sync.
매번 같은 메시지이고, 대상 경로가 워크트리 안이어도 거부한다.

모순이 있다. 같은 도구가 주 체크아웃에서는 "워크트리 사본을 고쳐라"라고 안내한다 —
워크트리의 존재를 알면서 그 안에 쓰는 것을 막는다.

**기전**(plan 레인 실측, 2026-08-23): 세션 cwd 는 옮겨간 워크트리인데 **도구가 쥔
프로젝트 경로는 처음 붙은 워크트리에 고정돼 있다.** `EnterWorktree` 로 이동해도
그 고정 경로는 따라오지 않으므로, 현재 워크트리 안의 경로가 도구에게는 프로젝트
밖으로 보인다. 재현 횟수보다 이 한 줄이 원인에 가깝다.

설정으로 못 푼다. `.claude/settings.json` · `settings.local.json` 에
`additionalDirectories` 류 키가 없다(grep 0건).

**결과**: Bash 가 유일한 쓰기 수단이 되고, 그 우회가 형태별로 또 갈린다(U-9). 우회는
매번 다른 방식으로 실패했다 — t13 에서 JSON 을 깨뜨렸고 t21 에서 오타를 냈다. 둘 다
즉시 잡았지만, **잡는 검사를 매번 새로 발명해야 한다**는 것이 이 마찰의 실제 비용이다.
(그 비용을 줄이려고 `docs/runbooks/writing-files-in-a-worktree.md` 를 만들었다.)

상류에 청하는 것: 워크트리 격리 세션에서 그 워크트리 안의 경로에 대해 `Write` · `Edit`
을 허용할 것. 최소한 `Read` 가 되는 경로에는 쓸 수 있어야 한다.

---

## U-9 (MED) — 정적 검증이 불가능한 구조를 거부하는 판별이 과도하다

**상류: Claude Code** (MoAI 아님)

**발동 조건**: `EnterWorktree` 로 들어간 격리 세션에서만 무장한다. 범용 Bash 가드가
아니다. 리드 세션 실측(2026-08-23) — 파일시스템상 워크트리 안이지만 `ExitWorktree` 로
나온 세션에서는 아래 G 가 통과했다. 거부 메시지 문면도 조건을 말한다:
*This session is isolated in the worktree … too complex to verify that it stays
inside the worktree.*

워크트리 세션에서 일부 Bash 명령이
`this command is too complex to verify that it stays inside the worktree` 로 거부된다.
기존 기록은 원인을 "중괄호 오독"이라고 적었으나, 대조군으로 재보니 **조건이 둘이고 서로
독립**이다.

| # | 형태 | 결과 |
|---|---|---|
| A | `cat <<EOF > /tmp/f.txt` · 중괄호 없음 | 거부 |
| B | `cat <<EOF > f.txt` · 워크트리 안 · 중괄호 없음 | 거부 |
| C | `python3 - <<PY` · 중괄호 리터럴 포함 | 거부 |
| D | `python3 - <<PY` · 중괄호 없음 · 리다이렉트 없음 | 통과 |
| E | `cat <<EOF` · 리다이렉트 없음 | 통과 |
| F | `python3 - <<PY` · `dict()` 호출 | 통과 |
| G | `python3 - <<PY` · `{"a": 1}` 리터럴 하나만 | 거부 |

F 와 G 는 한 표현만 다르고 결과가 반대다 — 중괄호 리터럴이 독립 트리거임이 확정된다.
A · B 와 E 를 비교하면 셸 리다이렉트가 또 하나의 독립 트리거다. heredoc 자체는 통과한다.

두 조건 모두 **오탐**이다. B 의 대상은 워크트리 안 상대경로이고 명령문에 그대로 적혀
있는데도 "확인할 수 없다"고 거부한다. G 의 중괄호는 quoted heredoc 안이라 셸이 확장하지
않는다.

**실질적 결과**: 격리 세션에서 `Write` · `Edit` 이 막히고(U-8) 이 판별까지 겹치면,
파일을 쓸 방법이 사실상 `printf` 하나로 좁아진다. 그리고 그 하나가 내용에 따라
실패한다 — 작은따옴표를 못 담고, 백슬래시 escape 를 틀리기 쉽다. 이 카드를 쓰는
동안에만 세 번 걸렸다(백슬래시 겹침 2회 · 인용부호 조기 종료 1회).

상류에 청하는 것: (a) quoted heredoc(`<<'EOF'`) 본문은 셸 확장 대상이 아니므로 확장
검사에서 제외할 것 (b) heredoc 명령의 리다이렉트 대상 경로가 정적으로 읽히면
워크트리 안인지 판정해 허용할 것 (c) 정적으로 못 읽는 경우에도 거부 대신 경고로
낮추는 선택지를 둘 것 — 지금은 판별 실패가 곧 금지라 우회를 강제한다.

---

## U-10 (LOW) — pre-commit 훅이 2층이고, 뒷층은 무조건 돈다

**상류: MoAI-ADK**

`.git/hooks/pre-commit` 은 두 층이다.

- 앞층(13~16행): `STAGED_GO` 가 비어 있지 않을 때만 gofmt · go vet 을 돈다.
- 뒷층(64~65행): `moai gate` 를 **무엇을 스테이징했든 무조건** 돈다.

즉 문서 한 줄만 고친 커밋도 전체 게이트를 탄다. 앞층은 스테이징 내용에 따라 건너뛰는데
뒷층은 안 건너뛴다 — 같은 파일 안에서 규율이 갈린다.

그리고 계측기 맹점이 하나 있다.

```
$ grep -in "vitest\|npm\|node_modules" .git/hooks/pre-commit
(출력 없음)
```

이 훅이 `npm test` 로 죽는데(카드 t13) 훅을 grep 해서는 그 단어가 하나도 안 나온다.
원인이 `moai gate` 안에 있기 때문이다. 훅을 읽어 원인을 찾으려는 사람은 빈손으로
돌아간다.

상류에 청하는 것: 뒷층도 스테이징 내용에 따라 범위를 좁힐 것. 최소한 훅 주석에
`moai gate` 가 어떤 툴체인을 부르는지 적어 grep 이 닿게 할 것.

---

## U-11 (MED) — moai gate 는 도구가 없으면 건너뛰지 않고 죽는다

**상류: MoAI-ADK**

같은 pre-commit 훅이 Go 에 대해서는 규율을 지킨다.

```
if command -v gofmt >/dev/null 2>&1; then ...
if command -v go >/dev/null 2>&1; then ...
```

도구가 없으면 조용히 건너뛴다. 그런데 `moai gate` 는 같은 상황에서 죽는다 — 카드 t13 에서
`sh: vitest: command not found` 하나로 게이트 전체가 실패했다.

`gate.yaml` 주석은 "Tools that are not installed are skipped gracefully" 라고 적혀 있어
실제 동작과 어긋난다.

t13 이 `package.json` 의 `pretest` 훅으로 ui 툴체인의 구체적 실패는 닫았지만, **원리는
나머지 15개 언어에 그대로 남는다.** 어느 언어든 그 툴체인이 미설치면 같은 자리에서 죽는다.

상류에 청하는 것: 게이트도 훅과 같은 `command -v` 규율을 쓸 것 — 도구 부재는 실패가
아니라 건너뛰기로 처리하고, 건너뛴 사실을 출력에 남길 것(부재를 통과로 오인하지 않게).

---

## 이 문서가 담지 않는 것

- **발사하지 않았다.** `/moai feedback` 은 상류 프로젝트에 GitHub 이슈를 만든다. 저장소 밖으로
  나가고 공개되는 일이라 감독 결정 사항이다.
- **U-2 의 설정 절반은 손대지 않았다.** 설정 키를 추가하는 것 자체가 동작 변경이다. 지금
  호출되지 않는 백엔드를 발화시킬 수 있어 측정만 하고 수정하지 않았다.
- **카드 t16 의 3번 항목(quality.yaml 중복 설정)은 U-7 로 실렸다.** 카드 t19 가 출처를 재서
  템플릿산임을 확정했다 — 로컬 결함이 아니라 상류 건이다.
