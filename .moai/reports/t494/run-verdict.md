# t494 판정서 — `moai spec drift` 출력에서 SPEC 이 빠지는 원인

lane-2, 2026-10-12. 기준 트리 `WT-spec-drift-gap` @ origin/main `3b91933c`. 도구는 이 저장소 소스가 아니라 설치본(`~/.local/bin/moai`, `moai-adk 3.1.2`)이다. 원인이 도구 쪽이라 **고치지 않았다** — 재현 조건과 우회만 적는다. 코드 diff 0줄.

## 1. 결론

`moai spec drift`는 git 기록을 **로컬 `main` 브랜치**에서 읽는다. 이 저장소의 로컬 `main`은 2026-09-22의 `b661da2d`에 멈춰 있다(주 체크아웃이 그 브랜치를 체크아웃하고 있다 — `git worktree list` 첫 줄 `b661da2d [main]`). 다음 두 조건이 겹치는 SPEC 은 기록에서 **조용히 빠진다**(오류·경고 없음, stderr 0바이트).

1. `progress.md`에 `## §E.2`·`## §E.4` 제목과 줄 맨 앞 `sync_commit_sha:` 값이 있어 V3R6 시대로 판정된다(`moai spec audit`의 `H-4 (§E.2 + §E.4 + sync_commit_sha)`).
2. 그 SPEC 의 기록이 로컬 `main`에 **하나도 없다**.

V3R6이 아닌 SPEC(era-exempt)은 git 기록을 보지 않으므로 `main`에 없어도 나온다.

SPEC-LDDESIGN-001 은 둘 다 해당한다. 9-22 뒤에 만들어진 SPEC 이라 `git log main -- .moai/specs/SPEC-LDDESIGN-001/` 결과가 0줄이고, t487 종결 때 `sync_commit_sha: 924871e5`가 들어가며 V3R6 으로 바뀌었다. 그래서 t487 sync 때는 63개 안에 있다가(in-progress, era-exempt) 종결 뒤 사라졌다. t487 §5 대조가 「spec·acceptance·progress 를 origin/main 판으로 되돌려도 빠진다」고 적은 것도 맞다. origin/main 판 progress.md 에 이미 `sync_commit_sha` 줄이 있었기 때문이다.

## 2. 다시 센 결과 — 빠진 건 하나가 아니라 다섯

`moai spec drift --json --no-cache` → 기록 67, `.moai/specs/SPEC-*` 디렉터리 72(`count.py`, `drift.json`). 빠진 다섯은 다음과 같다.

| SPEC | 빠진 이유 |
|---|---|
| SPEC-LDDESIGN-001 | 이 카드의 결함 — 위 §1 |
| SPEC-COPILOT-CUETIME-001 | spec.md 에 YAML 프런트매터가 없다(첫 줄이 `# SPEC-…` 제목) |
| SPEC-COPILOT-SONGSTD-001 | 위와 같다 |
| SPEC-COPILOT-IMGLAYOUT-001 | 위와 같다(`status:`가 본문 3행에 있을 뿐 `---` 블록이 아니다) |
| SPEC-COPILOT-RESTORE-001 | spec.md 자체가 없다 |

아래 넷은 파서가 SPEC 으로 보지 않는 디렉터리라 이 카드의 결함과는 다른 것이다. t487 이 62/63 이라고 적은 것은 그 넷이 처음부터 빠져 있었기 때문이다.

## 3. 실험 — 무엇을 바꾸면 들어오고 무엇은 상관없나

전부 이 워크트리 안에서 하고 되돌렸다. 마지막 `drift-after-cleanup.json`은 기준과 같다(67건, 빠진 다섯 동일). `git status`는 이 보고서 폴더 하나뿐이다.

| # | 바꾼 것 | LDDESIGN |
|---|---|---|
| 1 | spec.md 를 프런트매터만 남김 | 빠짐 |
| 2 | spec.md 를 최소 9필드 프런트매터로 | 빠짐 |
| 3 | spec-compact.md 치움 | 빠짐 |
| 4 | **progress.md 를 빈 파일로** | **들어옴**(completed, era-exempt) |
| 5 | **progress.md 에서 `sync_commit_sha:` 줄만 뺌** | **들어옴** |
| 6 | §E.2~§E.5 제목만 뺌 | 빠짐 |
| 7·8 | sha 값을 없는 sha(`deadbeef`)·`pending-backfill-x`로 | 빠짐 — 값과 무관하게 줄이 있으면 빠진다 |
| 10~12 | `design/`·`sync-evidence/` 하위 폴더 치움(하나씩·둘 다) | 빠짐 |
| 16 | progress.md 를 §E.2/3/4 제목 + sha 줄만 남긴 최소판으로 | 빠짐 |
| 17·18 | 나머지 md 전부 치우고 spec.md 를 LDCOMPILE 본문(ID 만 바꿈)으로 | 빠짐 — 파일 내용이 아니라 이 SPEC ID 에 묶인 무엇 |
| 21 | `git-strategy.yaml` `main_branch: origin/main` | 빠짐 — 설정은 안 읽는다(브랜치 이름이 박혀 있다) |

**도구가 무엇을 읽는지 대조**(내 브랜치에 임시 커밋 → 확인 → `git reset --soft 3b91933c`로 되돌림): SPEC-COPILOT-EVAL-001 에 정식 종결 제목(`docs(SPEC-COPILOT-EVAL-001): sync-phase artifacts — 3-phase close`)으로 spec 경로 커밋을 얹어도 `GitImpliedStatus`가 `in-progress` 그대로였다(`exp20_control_close.json`). 그래서 drift 는 **작업 브랜치 HEAD 를 읽지 않는다**. 이 결과로 #13·14·19(내 브랜치 커밋으로 기록을 흉내 낸 실험)는 판정 불가로 버렸다.

**원인 확인 — 새 탐침 SPEC 으로 두 갈래**(git 조작 없음, 추적 안 되는 디렉터리라 어느 브랜치 기록에도 없음):

| 갈래 | 탐침 `SPEC-ZZPROBE-001` | 결과 |
|---|---|---|
| A | completed + §E.2/3/4 + `sync_commit_sha:` | **빠짐**(`exp22`) |
| B | 같고 `sync_commit_sha:` 줄만 없음 | 들어옴, era-exempt(`exp23`) |
| C | in-progress + §E.2/4 + `sync_commit_sha:` | **빠짐**(`exp24`) — 상태와 무관 |

**반대편 확인**: 기록에 나오는 git 판정 SPEC(era-exempt·terminal-exempt 아님) 28개는 전부 로컬 `main`에 spec.md 기록이 있다(`stale_main.txt`의 `main=` 열이 28줄 모두 1 이상). LDDESIGN·LDBEAT 는 `git log main -- .moai/specs/SPEC-…/` 결과가 0줄이다.

**예측 하나(이미 측정함)**: SPEC-LDBEAT-001 은 지금 `- **sync_commit_sha**: pending-…`(굵은 글머리) 꼴이라 era.go 가 필드를 못 읽어 V3R5(`H-3 … sync_commit_sha missing`)로 판정되고, 그래서 아직 나온다. 그 줄을 줄 맨 앞 `sync_commit_sha: 48e51135` 꼴로 백필하면 LDBEAT 도 빠진다(`exp9_ldbeat_bare_sha.json` — 빠진 목록에 LDBEAT 추가).

## 4. 낡은 main 이 drift 판정 자체를 흔드나 — 이번 범위에서는 아니다

기록이 있는 V3R6 SPEC 28개 각각에 대해 spec.md 커밋 수를 `main`과 `origin/main`에서 세면 28개 모두 같았다(`stale_main.txt`, STALE-GAP 0). 지금 `Drifted: true`인 23건(completed 인데 git 이 in-progress/implemented 로 보는 것)은 낡은 main 탓이 아니다 — 그건 이 카드 밖의 다른 문제(종결 제목 꼴 등)이고 원인은 재지 않았다. 다만 이 측정은 spec.md 경로만 셌다. 도구가 progress.md 등 다른 경로나 커밋 제목으로 판정한다면 그 몫은 재지 않았다.

## 5. 우회

| 방법 | 효과 | 주의 |
|---|---|---|
| **A. 로컬 `main`을 origin/main 으로 당긴다** | 빠짐의 원인 자체를 없앤다(예상 — 실행은 안 함) | 주 체크아웃이 `main`을 체크아웃하고 있어 `git fetch origin main:main`은 거절된다. 주 체크아웃에서 `git pull --ff-only` 해야 하는데, 그 트리의 미커밋 상태를 감독이 먼저 봐야 한다. 레인 권한 밖(공유 체크아웃 브랜치 상태 변경)이라 하지 않았다. 당긴 뒤에도 새 커밋이 쌓이면 다시 낡는다 |
| **B. SPEC 존재 확인은 `moai spec audit --json --include-grandfathered`로** | audit 은 LDDESIGN 을 V3R6 으로 정상 보고한다(`audit.json`, total_specs 71) | drift 기록이 아니라 era 판정만 준다 |
| **C. drift 결과를 디렉터리 목록과 대조** | 빠진 SPEC 을 바로 드러낸다(`count.py`) | 원인은 못 고친다 |

도구 쪽 수정 제안(이 저장소 밖, `moai-adk`): drift 가 V3R6 SPEC 의 git 기록을 못 찾으면 기록을 버리지 말고 `GitImpliedStatus: unknown`(또는 경고) 기록을 낸다. 비교 대상 브랜치는 `origin/<main>`을 우선하거나 설정(`git_strategy.*.main_branch`)을 읽는다.

## 6. 안 잰 것

- 우회 A 를 실제로 해서 LDDESIGN 이 들어오는지 — 공유 브랜치 상태 변경이라 하지 않았다(예측만).
- drift 가 `main`을 정확히 어떤 git 명령으로 읽는지 — 바이너리만 있어 소스를 못 읽었다. 「로컬 main 을 읽는다」는 §3의 대조 실험(작업 HEAD 무시)과 갈래 A/B/C, 반대편 21개 확인에서 추론한 것이다.
- `Drifted: true` 23건의 원인(§4).
- 빠진 넷(프런트매터 없음)이 의도된 제외인지 — 파서가 SPEC 으로 안 보는 것은 맞지만, 그게 맞는 동작인지는 판단하지 않았다.

## 7. 새 카드 후보

- **SPEC-LDBEAT-001 `sync_commit_sha` 백필 꼴**: 지금 굵은 글머리 꼴이라 era.go 가 못 읽어 V3R5 로 잘못 판정된다(t494 가 발견, 2026-10-12 sync 커밋 `48e51135`가 만든 꼴). 줄 맨 앞 꼴로 백필하면 이번엔 위 결함으로 drift 에서 빠진다. 우회 A 와 같이 처리해야 한다.
- **로컬 `main` 갱신**(우회 A) — 감독·리드 판단.
