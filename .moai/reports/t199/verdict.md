# t199 — kanban-dispatch.md 워크트리 절 정정 (verdict)

- 브랜치: `WT-worktree-doc-fix` (워크트리 `.claude/worktrees/t199`)
- 환경: claude 2.1.251 / moai-adk 3.1.2, 표본 1환경·1빌드
- 정정 대상: `.claude/rules/moai/workflow/kanban-dispatch.md` (always-loaded [HARD] 파일)

## 정본 판정

`kanban-dispatch.md` 가 워크트리 절의 정본이다. `.moai/docs/lane-protocol.md` §2 는
이미 올바른 문면("ExitWorktree 뒤에는 세션이 launch dir 로 돌아가고")을 담고 있었고
어긋난 쪽은 `kanban-dispatch.md` 였다 — 그래서 두 파일을 하나로 합치치 않고
`kanban-dispatch.md` 쪽만 고쳤다. `lane-protocol.md` 는 그대로 둔다.

## 결함 1 — `moai worktree done` 의 L1/L2 경계 (kanban-dispatch.md:156)

원문은 두 주장을 담고 있었다:
- (a) 행동 주장 — "L1 에 대한 done 은 처분이 아니라 범주 오류다"
- (b) 등록부 주장 — "L1 은 레지스트리에 절대 없다"

**(a) 반증됨.** 실측(t198): PR #241 이 main a07d86c 로 머지된 뒤, 실작업 트리가 아닌
throwaway L1 트리(`t198-disposal-test`)에 대고 `moai worktree done <branch>` 실행 →
exit 0, `Worktree removed` 출력, `git worktree list` 에서 소멸. `done` 은 L1 에도
동작한다.

**(b) 미측정 — 반증 아님.** `moai worktree --help` 는 `recover`("Repair worktree
registry")를 통해 레지스트리 개념의 존재를 확인해 준다. 그러나:
- `list` verb 가 없고 `--help` 자신이 "For inspection, use git directly"로 안내 —
  이 CLI 로는 레지스트리 내용을 물을 수단이 없다.
- `moai` 바이너리는 이 저장소의 소스가 아니다. `~/.local/bin/moai` (moai-adk 3.1.2)
  로 설치되어 있고, 로컬에서 소스 저장소를 찾지 못했다(`find`·`pip`·`python3 -c
  "import moai_adk"` 전부 실패) — 그래서 구현을 직독하지 못했다.
- `recover` 는 레지스트리 상태를 바꾸는 명령이라, 확인하려고 쏘면 확인과 사고가
  같은 행위가 된다 — 실행하지 않았다.

→ (b)는 "미측정"으로 문서에 표기했다. "반증됨"이라고 쓰지 않았다.

정정은 원문을 지우지 않고, 원문 바로 아래에 blockquote 로 날짜·환경 고지와 함께
추가했다(diff 참조).

## 결함 2 — `ExitWorktree` 의 복귀 자리 (kanban-dispatch.md:214)

원문: "`ExitWorktree` returns the session to the primary checkout"

**반증됨.** 두 레인이 독립으로 확인:
- t198 레인 — ExitWorktree 뒤 primary 체크아웃이 아니라 **세션 시작 디렉터리**
  (`~/orca/workspaces/AI-Lighting_Console/LX-SEQ`)로 돌아갔다.
- t197 레인 — 독립 재확인 + 한 겹 더: 그 시작 디렉터리 자체가 git 워크트리다
  (git-dir ≠ common-dir, 브랜치 `jjjh7401/LX-SEQ`).

그래서 "primary 로 돌아간다"도 "워크트리를 벗어난다"도 둘 다 틀린다. 참인 서술은
"시작 디렉터리로 돌아간다 — 그것이 워크트리일 수도 있다"이다. `lane-protocol.md`
§2 의 문면이 이미 이 형태였다.

정정도 원문을 지우지 않고 blockquote 로 추가했다.

## 부수 — 격리-활성 축 (문서에 추가하지 않기로 결정)

t197 이 낸 셋째 발견 — "워크트리 실행 가드는 cwd 가 아니라 세션의 EnterWorktree
격리가 활성인가로 작동한다" — 는 카드 본문에서 스스로 "부수(관측만, 넓히지 마라)"로
표시되어 있었다. 이번 카드 범위(정본 판정 + 결함 1·2 정정)에 포함되지 않으므로
**문서에 추가하지 않았다.** 별도 카드로 세울지는 리드 판단.

## 미검증 (Gaps)

- 결함 1(b) — 위에서 서술한 대로 이 환경에서는 원리적으로 CLI 로 못 잰다. moai
  소스 저장소 위치를 찾으면(다른 머신·다른 클론 등) 직독으로 닫을 수 있다.
- `moai worktree recover` 의 실제 동작 — 관측 시도 자체가 상태를 바꾸므로 미시도.
- 이번 정정이 다른 always-loaded 파일(worktree-integration.md 등)의 상충하는
  서술까지 전부 훑은 것은 아니다 — grep 으로 "returns the session to the primary
  checkout"·"moai worktree done"·"ExitWorktree" 세 패턴만 대조했다
  (worktree-integration.md:186 의 "returns to the originating checkout"는
  lane-protocol.md 의 launch-dir 서술과 상충하지 않아 손대지 않았다).

## 잔여 위험

- 표본이 claude 2.1.251 / moai-adk 3.1.2 한 환경·한 빌드다. 다른 빌드에서
  `moai worktree done` 이나 `ExitWorktree` 의 동작이 달라질 수 있다.
- kanban-dispatch.md 는 always-loaded [HARD] 파일이라 이 편집이 전 세션 프롬프트
  캐시를 무효화한다(카드 지시대로 편집을 카드 끝에 한 번으로 몰았다 — 이번 카드의
  유일한 always-loaded 편집).

## 증거

- `git diff --stat` → `.claude/rules/moai/workflow/kanban-dispatch.md | 6 ++`
  (2개 blockquote 삽입, 6줄 순증)
- `moai worktree --help` 원문 재확인, 본문에 인용
- `find /Users/studiox -maxdepth 4 -iname "*moai-adk*" -type d` → 0건
- `python3 -c "import moai_adk"` → `ModuleNotFoundError`
