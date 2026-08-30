# t197 — Bash 가드 방아쇠를 격리 측정으로 가른다

측정: 2026-08-31 · 워크트리 `.claude/worktrees/t197` (브랜치 `WT-guard-axis-isolation`) · 베이스 `c94edfd`
계기: 카드 t197. 기존 메모리 항목과 t192 레인 표본과 리드 t184 표본이 서로 어긋났고, 셋 다 한 줄에 두 형태를 담아 축이 안 갈렸다.

---

## 요약 — 다섯 줄

1. **가드는 문구로 갈린다.** 네 종류의 거절 문구가 서로 바이트 다르고, 소유 바이너리까지 갈린다 (`claude` 대 `moai`).
2. **다만 한 가드 안에서 접힌다.** 워크트리 실행 가드는 서로 다른 다섯 형태에 대해 **바이트 동일한** 사유를 낸다. 카드가 느낀 「못 가른다」의 실체는 가드 사이가 아니라 가드 안이다.
3. **방아쇠는 「중괄호 쌍」이 아니라 「중괄호 확장」이다.** `{}` 와 `a{b}c` 는 통과하고 `{1,2}`·`{1..2}` 만 거절.
4. **「히어독 뒤 리다이렉트」가 아니라 히어독 단독이다.** 리다이렉트는 무관 — `> file` 단독은 통과.
5. **환경 축이 셋이고, 방아쇠는 EnterWorktree 격리가 켜져 있을 때만 산다.** 세션 시작 디렉터리는 그 자체가 워크트리인데도 거절이 0건이었다.

---

## 1. 가드 목록 — 소유 바이너리로 갈린다

바이너리에서 문자열을 세어 확인했다.

```
B=/Users/studiox/.local/share/claude/versions/2.1.251
strings -n 8 $B | grep -c 
```

| # | 가드 | 사는 곳 | 표식 문자열 | 이번 세션에서 발사됨 |
|---|---|---|---|---|
| A | 워크트리 **실행** 가드 | `claude` 2.1.251 | `is isolated in the worktree` (5건) | 예 |
| B | 워크트리 **쓰기** 가드 | `claude` 2.1.251 | `Edit the worktree copy of this file instead of the shared-checkout path.` | 예 |
| C | 프로젝트 디렉터리 쓰기 가드 | `claude` 2.1.251 | `Path traversal detected: file is outside project directory` | 예 |
| D | 브랜치·위험명령 가드 | `moai` | `BRANCH_GUARD_VIOLATION` (3건) · dangerous/destructive (81건) | 아니오 |

🔴 **결정적 계수: `moai` 바이너리에 `isolated in the worktree` 는 0건이다.** 즉 A·B·C 와 D 는 같은 문구를 쓰는 것이 아니라 **아예 다른 프로그램**이다. 카드가 든 전제 「세 가드의 거절 문구가 서로 비슷해서 어느 가드가 물었는지 문구로 못 가른다」는 이 축에서 반증된다.

### 1.1 가드 A 는 안에 사유 표를 들고 있다

`claude` 바이너리 안에 워크트리 실행 가드의 사유 문자열이 20개 넘게 연달아 있다. 발췌:

```
is too complex to verify that it stays inside the worktree
spells its command as a glob (...) that bash resolves at runtime, so it cannot be verified as anything but git
names git more than once in a single command, which cannot be verified to stay inside the worktree
passes more than one -C/--chdir to env (last-wins semantics), which cannot be verified
changes directory via env to the shared checkout (...)
redirects git through a glob pattern that expands at runtime
points git at a directory computed at runtime (-C ...)
redirects git to the shared checkout via ...
feeds git its arguments from stdin at runtime (xargs/parallel), so the repository it targets cannot be verified
changes directory per match (find -execdir/-okdir) before running git, so its repository cannot be verified
```

⚠️ **사유 문자열이 전부 git 을 말한다는 사실에 속지 마라.** 나는 이것을 읽고 「가드는 git 을 낀 명령만 본다」고 예측했고, **실측에서 틀렸다** — git 이 한 글자도 없는 `echo {1,2}` 가 거절된다. 소스의 사유 문면은 *왜 막는지*를 말할 뿐 *무엇이 방아쇠인지*를 말하지 않는다.

## 2. 환경 축 — 둘이 아니라 셋이다

| 자리 | 경로 | git-dir vs common-dir | EnterWorktree 격리 | 결과 |
|---|---|---|---|---|
| primary 체크아웃 | `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console` | 같음 | — | **미측정** (세션을 거기 둘 수 없다) |
| 세션 시작 디렉터리 | `/Users/studiox/orca/workspaces/AI-Lighting_Console/LX-SEQ` | **다름 = 워크트리** (브랜치 `jjjh7401/LX-SEQ`) | 없음 | (a)~(h) + 히어독+리다이렉트 + `git -C` 타 워크트리 — **10형태 전부 통과, 거절 0건** |
| 카드 워크트리 | `.claude/worktrees/t197` | 다름 | **있음** | 아래 3절대로 갈림 |

🔴 **이 표의 둘째 행이 이 카드의 핵심 발견이다.** 세션 시작 디렉터리는 **그 자체가 git 워크트리**인데도 가드가 한 번도 안 물었다. 즉 가드 A 의 조건은 「cwd 가 워크트리인가」가 아니라 **「이 세션에 EnterWorktree 격리가 활성인가」**다.

부수 발견: `ExitWorktree` 는 primary 체크아웃이 아니라 **세션 시작 디렉터리**로 돌아간다. 규약 §2 의 서술(「launch dir 로 돌아가고」)이 맞고, `kanban-dispatch.md` 의 서술(「returns the session to the primary checkout」)은 이 세션에서 틀렸다.

---

## 3. 형태 축 — 카드가 지정한 (a)~(h) 를 한 줄씩

전부 `echo` 기반 무해 명령. 한 호출에 한 형태만 담았다 (규약 §3.3).

| 카드 표기 | 명령줄 (전문) | 1팔: 격리 없음 | 2팔: 격리 안 |
|---|---|---|---|
| (a) 중괄호 쌍 단독 | `echo {1,2}` | 통과 | **거절 (i)** |
| (a) 인용 중괄호 | echo 뒤 홑따옴표로 감싼 {"a": 1} | 통과 | 통과 |
| (b) f-string 중괄호 | `python3 -c ...print(f...)` (홑따옴표) | 통과 | 통과 |
| (c) 히어독 단독 | `cat <<EOF` … `EOF` | 통과 | **거절 (i)** |
| (d) 히어독 뒤 리다이렉트 | `cat > probe_d_in.txt <<EOF` … | 통과 | **거절 (i)** |
| (e) 명령 치환 단독 | `echo $(pwd)` | 통과 | **거절 (i)** |
| (f) && 사슬 단독 | `echo one && echo two` | 통과 | **통과** |
| (g) for 루프 단독 | `for i in 1 2; do echo $i; done` | 통과 | **거절 (i)** |
| (h) 파이프 단독 (대조군) | echo hello 파이프 wc -c | 통과 | 통과 |

🔴 **(f) 가 카드에 실린 t192 표본과 정반대다.** 카드는 「(f) && 사슬 → 거절, 문구 (i)」로 적고 있는데, 격리 안에서 `&&` 단독은 통과하고 git 을 낀 `git status --short && echo done` 도 통과한다.

### 3.1 경계를 더 좁혀서 — 통과/거절 전수

카드가 지정한 여덟보다 넓게 쐈다. 여덟만으로는 「확장 구문」이라는 이름이 맞는지 안 갈리기 때문이다 (범위 확대 사유는 §7).

**거절 — 인용되지 않은, 스캐너가 모델링 못 하는 확장/복합문**

| 형태 | 명령줄 |
|---|---|
| 중괄호 목록 확장 | echo {1,2} |
| 중괄호 범위 확장 | echo {1..2} |
| 중괄호 매개변수 확장 | echo ${HOME} |
| 명령 치환 | echo $(pwd) |
| 명령 치환, 큰따옴표로 감싸도 | echo "$(pwd)" |
| 백틱 치환 | echo `pwd` |
| 히어독 | cat <<EOF … EOF |
| 히어독 + 리다이렉트 | cat > f.txt <<EOF … EOF |
| for 루프 | for i in 1 2; do echo $i; done |
| while 루프 | while read x; do echo $x; done < /dev/null |
| **리다이렉트 대상이 변수** | R=f.txt; echo hi > $R |
| git 리다이렉트 | git -C <다른 트리> log --oneline -1 → 사유 (ii) |

**통과**

| 형태 | 명령줄 |
|---|---|
| 빈 중괄호 쌍 | echo {} |
| 낱말 안 중괄호 쌍 | echo a{b}c |
| 홑따옴표 구간 (전부) | echo 로 감싼 {1,2} · ${VAR} · $(pwd) — 홑따옴표 안이면 전부 통과 |
| 단순 매개변수 확장 | echo $HOME |
| 변수를 인자로 | R=f.txt; echo $R |
| 산술 확장 | echo $((1+1)) |
| glob | echo * |
| 세미콜론 | echo one; echo two |
| && 사슬 | echo one && echo two · git status --short && echo done |
| 이중파이프 사슬 | grep -c EOF README.md 또는 true |
| 부정 | ! false |
| 파이프 2단·3단 | echo a 파이프 wc -c 파이프 cat |
| 서브셸 | ( echo sub ) |
| 평범한 리다이렉트 | echo x > probe_redir.txt |
| if 블록 | if true; then echo y; fi |
| 대입 | x=1; echo $x |
| awk 프로그램 안 중괄호 | awk 홑따옴표 BEGIN {print 1} 홑따옴표 |
| 실사용형 | moai todo 2>/dev/null 파이프 awk -F 탭 |

---

## 4. 거절 문구 전문

### (i) — 다섯 형태가 이 문구 하나로 접힌다

This session is isolated in the worktree /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t197, but this command is too complex to verify that it stays inside the worktree. Refusing to run it — a worktree-isolated session's git operations must target its own worktree. Split it into plain, separate commands and run them from /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t197.

중괄호 확장 · 히어독 · 명령 치환 · 백틱 · for/while · 변수 리다이렉트 대상 — 이 여섯 원인이 **바이트 동일한** 이 문구를 낸다.

🔴 규약 §3.6 의 판정 기준(「서로 다른 원인이 여전히 서로 다른 사유를 내는가」)으로 보면 이 가드는 **구별을 접고 있다.** 카드가 「문구로 못 가른다」고 느낀 지점의 실체가 이것이다 — 가드 **사이**가 아니라 가드 **안**이다. 가드 사이는 오히려 잘 갈린다 (1절).

### (ii) — git 리다이렉트

This session is isolated in the worktree /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t197, but this command redirects git to the shared checkout via -C. Refusing to run it — a worktree-isolated session's git operations must target its own worktree. Run the equivalent from /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t197 without the redirect.

⚠️ **문구에 거짓 세부가 있다.** 내가 쏜 대상은 `shared checkout` 이 아니라 **다른 워크트리**(`.claude/worktrees/t196`)였는데도 문구는 shared checkout 이라고 말한다. 두 경우 모두 같은 문장이 나온다 — 이 문구를 읽고 「내가 primary 를 건드렸구나」로 진단하면 틀린다.

### (iii) — 쓰기, 워크트리 경로

Path traversal detected: file is outside project directory

`Write` 로 워크트리 안 파일을 만들려 할 때. 여기서 project directory 는 **세션 시작 디렉터리**(LX-SEQ)이지 워크트리가 아니다.

### (iv) — 쓰기, 시작 디렉터리 경로

This session is isolated in the worktree /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t197. Edit the worktree copy of this file instead of the shared-checkout path.

🔴 (iii) 과 (iv) 는 **서로 반대를 가리킨다.** 워크트리 경로엔 「프로젝트 밖이다」, 시작 디렉터리 경로엔 「워크트리 사본을 고쳐라」. `Write` 는 이 세션에서 **완전히 막혀 있고 탈출로는 Bash 하나뿐**이다 — 규약 §2 의 서술이 이 세션에서 그대로 재현됐다.

⚠️ 다만 §2 가 지목한 탈출로 「Bash 히어독」은 **이 세션에서 막힌다.** 실제로 이 보고서는 히어독이 아니라 `printf` 로 썼다. §2 의 처방은 격리가 없는 세션에서만 성립한다.

---

## 5. 전제 판정

| # | 전제 | 출처 | 판정 |
|---|---|---|---|
| 1 | 세 가드의 거절 문구가 비슷해 어느 가드가 물었는지 문구로 못 가른다 | 카드 t197 | **반증** — 네 문구가 서로 바이트 다르고 소유 바이너리까지 갈린다. 접히는 것은 가드 사이가 아니라 가드 A 안 |
| 2 | 방아쇠는 확장 구문(중괄호 쌍) | 메모리 lesson-bash-guard-trigger-is-the-unquoted-brace-pair | **부분 반증** — 「쌍」이 아니라 **확장**이다. `{}` · `a{b}c` 통과. 또 「확장 구문」이라는 이름이 너무 넓다: glob · `$VAR` · `$(( ))` 는 확장인데 통과 |
| 3 | 방아쇠는 히어독 뒤 리다이렉트 | 같은 메모리 항목 | **반증** — 히어독 **단독**이 방아쇠다. 리다이렉트는 무관 (평범한 `> file` 통과) |
| 4 | (a)(b) 중괄호·f-string 히어독이 통과했다 | t192 레인 2026-08-31 | **격리 안에서는 재현 안 됨.** 화해 가설: 그 세션에 EnterWorktree 격리가 없었다 — 내 1팔에서는 실제로 전부 통과했다. **그 세션의 격리 상태는 안 쟀다** |
| 5 | (f) && 사슬이 거절됐다, 문구 (i) | t192 레인 | **반증** — `&&` 단독도, git 을 낀 `&&` 도 통과. 그 거절은 `&&` 가 아니라 같은 줄의 다른 형태가 물었을 것 |
| 6 | (g) for 루프가 문구 (i) 로 거절됐다 | 리드 t184 | **재현 확인** |
| 7 | git -C 타 워크트리가 문구 (ii) 로 거절됐다 | 리드 t184 | **재현 확인** (다만 문구의 shared checkout 은 거짓 세부 — 4절) |
| 8 | 쓰기 가드 경계는 세션 시작 디렉터리다 | 메모리 lesson-write-guard-boundary-is-the-launch-dir | **재현 확인** — (iii) 의 project directory 가 LX-SEQ 다 |
| 9 | 도구별로 갈린다 (Edit 거절, 같은 경로 Bash 통과) | 리드 관측 | **재현 확인** — Write 는 (iii), 같은 경로 Bash 리다이렉트는 통과 |

---

## 6. 규약·메모리에 반영할 것

1. **메모리 항목 `lesson-bash-guard-trigger-is-the-unquoted-brace-pair` 의 제목이 틀렸다.** 「brace pair」가 아니라 「모델링 못 하는 확장」이다. 제목이 곧 처방으로 읽히는 자리라 고쳐야 한다.
2. **규약 §2 의 탈출로 서술에 조건을 붙여야 한다.** 「Bash 히어독은 통과한다」는 격리 없는 세션에서만 참이다. 격리 안에서는 히어독도 막히고 남는 것은 홑따옴표 `printf` 다.
3. **`kanban-dispatch.md` 의 ExitWorktree 서술이 틀렸다** — primary 체크아웃이 아니라 세션 시작 디렉터리로 돌아간다.
4. **레인이 격리 안에서 쓸 수 있는 관용구**를 규약에 실어야 한다. 거절되는 형태가 흔한 것들이라 레인이 반복해서 밟는다.

### 6.1 격리 안에서 쓰는 관용구

| 하고 싶은 것 | 막히는 형태 | 되는 형태 |
|---|---|---|
| 명령 결과를 인자로 | echo $(git rev-parse HEAD) | 두 줄로 나눠서 각각 실행 |
| 파일 여러 개 만들기 | touch {a,b}.txt | touch a.txt b.txt |
| 파일에 여러 줄 쓰기 | cat > f <<EOF | printf 형식문자열 뒤에 홑따옴표 줄들 |
| 목록 순회 | for … do … done | 한 줄씩 따로 실행 |
| 경로를 변수로 두고 리다이렉트 | R=f; echo x > $R | 리다이렉트 대상을 리터럴로 |
| 다른 트리의 git 을 보기 | git -C <다른 트리> log | 그 트리로 세션을 옮기거나, 리드에게 물어라 |

홑따옴표는 스캐너가 접으므로, **인용 안에 들어가는 텍스트는 무엇이든 통과한다.** 중괄호·달러·백틱이 든 내용을 파일에 쓸 때는 홑따옴표 `printf` 가 유일하게 안전한 길이다.

---

## 7. 범위를 넓힌 곳과 그 사유

카드는 (a)~(h) 여덟을 지정했다. 나는 22형태를 쐈다. 사유는 하나다 — **여덟만으로는 방아쇠의 이름이 안 갈린다.** (a) 하나만 쏘면 「중괄호가 방아쇠」로 읽히는데, `echo {}` 를 같이 쏘면 그것이 **확장**임이 드러난다. 이름을 틀리게 붙이는 것은 안 재는 것보다 나쁘다 (규약 §3.6).

넓힌 축은 형태 축 하나뿐이다. 환경 축과 도구 축은 카드가 이미 지정했다.

---

## 8. 안 잰 것

| # | 안 잰 것 | 왜 |
|---|---|---|
| 1 | primary 체크아웃에서의 동작 | 세션을 거기 둘 수 없다. 시작 디렉터리가 LX-SEQ 워크트리로 고정돼 있다 |
| 2 | `moai` BRANCH_GUARD 실발사 | 기본 비활성이고, 발사하려면 공유 체크아웃에서 브랜치를 옮겨야 한다 — **확인과 사고가 같은 행위**가 되는 자리라 안 쐈다. 바이너리 안에 문자열이 있다는 것까지만 쟀다 |
| 3 | 가드 A 의 나머지 사유 문자열 ~20개 | 바이너리에서 읽었을 뿐 실발사 안 함. env · xargs · find -execdir · GIT_CONFIG 등 |
| 4 | 서브에이전트 축 | 바이너리에 `This agent is isolated in the worktree` 가 따로 있다. `Agent(isolation: worktree)` 로는 안 쐈다 |
| 5 | claude 2.1.251 외 버전 | t192 표본과의 불일치가 격리 상태 차이가 아니라 **버전 차이**일 가능성을 배제하지 못한다 |
| 6 | t192 레인 세션의 격리 상태 | 5절 4번 화해 가설의 유일한 미검증 고리 |
| 7 | 큰따옴표 안 `${VAR}` · glob 을 리다이렉트 대상으로 두는 형태 | 형태 축을 더 넓히지 않았다 |

---

## 9. 측정 방법

- 모든 자극은 한 호출에 한 형태 (규약 §3.3). 두 형태를 한 줄에 담은 자극은 이 보고서에 없다.
- 두 팔 대조 (규약 §3.6): 1팔 = 격리 없음, 2팔 = 격리 안. 같은 명령줄을 두 팔에 각각 쐈다.
- 개수는 `grep -c`, 자리는 `grep -n`. `head` 를 개수나 부재의 근거로 쓰지 않았다 (규약 §4.0).
- 한 번 하네스 잘림 배너(52.6KB)를 만났고, §4.0 대로 **먼저 내 명령줄을 읽었다** — `head` 가 없었으므로 진짜 하네스 잘림이었고, 파이프를 바꿔 다시 떴다.
- 모든 자극은 `echo` 기반 무해 명령. 콘솔 쓰기 0건, 파괴 명령 0건.

---

## 10. 이 카드가 남기는 것

**소스를 읽고 세운 가설이 실측에서 틀렸다.** 가드 A 의 사유 문자열은 스무 개가 넘고 **전부 git 을 말한다.** 나는 그것을 읽고 「git 을 낀 명령만 본다」고 예측했고, `echo {1,2}` 한 줄이 그것을 반증했다.

문면은 *왜 막는지*를 말한다. 방아쇠는 *무엇이 오는지*로 결정된다. 둘은 같은 자리에 있지 않다 — **소스를 읽을 수 있게 된 것이 실측을 면제해 주지 않는다.**

그리고 이 보고서를 쓰는 중에 내가 그 방아쇠를 밟았다. `R=파일; printf … >> $R` 이 거절됐고, 축을 갈라 재보니 **리다이렉트 대상이 변수인 것**이 아홉째 방아쇠였다. 카드가 지정하지 않은 형태이고, 내 실수가 없었으면 안 나왔을 것이다.
