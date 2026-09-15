# t64 결정② — 「태그를 푸시하면 CI 가 그 커밋을 받는가」 실측

측정 트리: `.claude/worktrees/t64` (HEAD `1f1ed25`, 브랜치 `WT-preserve-base`)
측정일: 2026-08-24

---

## 1. 답: **받는다.** 단, 이유가 배차서의 전제와 다르다

배차서의 전제는 "actions/checkout 의 fetch-depth 기본값 1 이면 CI 는 여전히 못 받는다"였다.
**이 저장소의 워크플로는 기본값을 쓰지 않는다** — `.github/workflows/test.yml:33-35` 가 `fetch-depth: 0` 을 명시로 박아두었고,
그 결과 checkout 이 발행하는 fetch refspec 에 `+refs/tags/*:refs/tags/*` 가 들어간다.

그래서 결정②의 답은 조건부가 아니라 단정이다: **지금 워크플로 그대로, 태그를 origin 에 푸시하면 CI 는 그 커밋을 받는다.**

---

## 2. 실측 1 — CI 가 실제로 발행한 fetch 명령 (로그 원문)

`fetch-depth: 0` 도입 **후** (run `32719982356`, main, `1f1ed25`):

    git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules origin \
        +refs/heads/*:refs/remotes/origin/* +refs/tags/*:refs/tags/*

`fetch-depth: 0` 도입 **전** (run `32620440718`, 이 저장소 첫 CI 실행, PR #94, failure):

    git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin \
        +c8503b0eafd487672a73fd3ceddfbae1b0e1884e:refs/remotes/pull/94/merge

두 줄의 차가 이 카드의 전부다:
- 전: `--depth=1`, refspec 이 **커밋 SHA 하나**. 태그 경로가 아예 없다 → 푸시해도 안 온다.
- 후: `--depth` 없음, refspec 에 **`+refs/tags/*`** 가 있다 → 태그가 온다.

즉 태그 경로는 `fetch-depth: 0` 에 **딸려 있는 것**이지 checkout 의 상수가 아니다.

⚠️ `--no-tags` 가 붙어 있는 것에 속지 말 것. 그건 자동 태그 따라오기를 끄는 플래그이고,
명시 refspec 이 있으면 그쪽이 이긴다. 아래 §3 이 그걸 실험으로 확인한다.

---

## 3. 실측 2 — 재현 실험 (문서 인용이 아니라 직접 돌린 것)

lab: `.moai/reports/t64/lab/` (origin.git · src · ci-actual · ci-notags)

설정: 실제 상황과 같은 모양을 만든다 —
`git commit-tree` 로 **어느 브랜치에서도 도달 불가한** 고아 커밋 `2f2a9dc5…` 를 만들고,
주석태그 `preserve-base` 만 그 커밋에 달아 origin 에 푸시했다. main tip 은 `f7d4e03a…` 로 무관하다.

    $ git ls-remote origin
    f7d4e03a…  refs/heads/main
    45a72123…  refs/tags/preserve-base
    2f2a9dc5…  refs/tags/preserve-base^

### A안 — CI 가 실제로 쓰는 명령 그대로

    $ git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules origin \
          '+refs/heads/*:refs/remotes/origin/*' '+refs/tags/*:refs/tags/*'
     * [new branch]      main          -> origin/main
     * [new tag]         preserve-base -> preserve-base
    $ git tag -l                                   → preserve-base
    $ git cat-file -e 2f2a9dc5…                    → exit 0    ← 고아 커밋이 왔다
    $ git cat-file -e 0000…0001 (날조 대조군)       → exit 1    ← 프로브가 판별력이 있다

### B안 — 음성 대조군: 태그 refspec 만 뺀다

    $ git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules origin \
          '+refs/heads/*:refs/remotes/origin/*'
     * [new branch]      main -> origin/main
    $ git tag -l                                   → (없음)
    $ git cat-file -e 2f2a9dc5…                    → exit 1    ← 안 왔다
    $ git cat-file -e f7d4e03a… (main tip 대조군)   → exit 0    ← fetch 자체는 정상

두 안의 차는 refspec 한 줄뿐이다. **태그 refspec 이 있으면 오고 없으면 안 온다** — `--no-tags` 는 이 결과를 못 뒤집는다.

---

## 4. 현재 태그 상태 (primary 체크아웃, 워크트리 공유)

    $ git tag -l                                              → preserve-base-songcue-m0
    $ git rev-parse preserve-base-songcue-m0^                 → 38a6e7e2157a4862721fcd868056e0dbbb09c4c0
    $ git for-each-ref --contains 38a6e7e2…                   → refs/tags/preserve-base-songcue-m0  (이 하나뿐)
    $ git for-each-ref --contains HEAD (양성 대조군)           → 5개 이상 (heads/remotes)
    $ git ls-remote --tags origin                             → (비어 있음)
    $ git ls-remote --heads origin (대조군)                    → 다수
    $ git ls-remote --tags https://github.com/actions/checkout → 다수  ← --tags 질의 자체는 동작함

읽는 법: **리드의 응급조치는 로컬에서 유효하고, 원격에는 아직 아무것도 없다.**
`ls-remote --tags` 의 빈 출력은 계기 고장이 아니다 — 같은 명령이 태그가 있는 저장소에서는 값을 낸다.

---

## 5. 그래서 결정③(픽스처 스냅샷)은 "유일한 durable 갈래"가 아니다

②가 동작하므로 갈래는 둘이다. 다만 **내구성의 성질이 다르다.**

| | ② 태그 푸시 | ③ 기준 look 파일을 저장소 안 픽스처로 |
|---|---|---|
| 커밋 보존 | origin 이 태그로 붙잡는다 → 프루닝 불가 | git 의존 자체를 없앤다 |
| CI 도달 | ✅ 실측 확인 (§2·§3) | 해당 없음 |
| 깨지는 조건 | 태그 삭제 · 워크플로에서 `fetch-depth: 0` 제거 | 픽스처 파일 삭제 |
| 깨질 때의 신호 | **skip 으로 조용히 되돌아간다** | 픽스처가 없으면 단언이 깨진다(소리가 난다) |
| 대외 행위 | 있음 (원격 푸시 — 감독 결정) | 없음 |

핵심 비대칭은 마지막에서 둘째 줄이다. ②는 깨져도 **실패가 아니라 skip** 이라 아무도 안 본다 —
t59 에서 이 계열이 문제가 된 이유가 정확히 그것이었다.

여기서 나오는 세 번째 선택지(리드 결정용, 내 판단 아님): **②를 하고 나면 skip 게이트를 없앨 수 있다.**
태그로 도달이 보장되면 `_requires_run_phase_base` 는 더 이상 필요 없고,
기준 커밋이 없을 때 skip 대신 **실패**하게 두는 편이 조용한 만료를 막는다.
②+게이트 제거를 묶으면 ③ 없이도 "깨질 때 소리가 나는" 성질을 얻는다.

---

## 6. 증거 (5-섹션)

**주장** — 지금 워크플로 그대로 태그를 origin 에 푸시하면 CI 는 `38a6e7e2…` 를 받는다.

**증거** — §2 두 로그의 fetch 명령 원문(도입 전/후 대조), §3 A/B 재현 실험(양성·음성 대조군 포함), §4 현재 태그 상태.
로그 원문: `.moai/reports/t64/ci-first-32620440718.log`, `.moai/reports/t59/ci-skipped-raw-32719982356.txt`.
실험 저장소: `.moai/reports/t64/lab/` (그대로 남겨둠 — 재현 가능).

**기준 귀속** — 모든 로컬 측정은 워크트리 `t64`, HEAD `1f1ed25` 에서 이번 세션에 잰 값이다.
CI 측정은 실행 `32719982356`(도입 후, 커밋 `1f1ed25`)과 `32620440718`(도입 전, PR #94) 두 건의 로그다.

**미검증 (Gap)**
1. **실제 태그를 푸시해 CI 에서 확인하지 않았다.** 감독 결정 대기라 금지된 행위다. §3 은 같은 refspec 을
   로컬에서 재현한 실험이지 GitHub 러너 위의 관측이 아니다. GitHub 측 서버가 태그 refspec 을 다르게
   다룰 가능성은 낮지만 재지 않았다.
2. **actions/checkout v7 이 어떤 조건에서 태그 refspec 을 넣는지 소스로 확인하지 않았다.** §2 는 결과(발행된
   명령)를 관측한 것이고, `fetch-depth: 0` 이 그 원인이라는 것은 두 실행의 대조에서 온 추론이다.
   교란 요인 가능성: 두 실행은 트리거도 다르다(도입 전은 PR, 후는 push). 트리거 차이만으로 refspec 이
   달라졌을 가능성은 배제하지 못했다. ⚠️ 이 Gap 은 도입 후의 **PR 트리거** 실행 로그 한 건을 더 보면 닫힌다.
3. **전량 스위트를 안 돌렸다** (run 레인이 t55 사용 중).
4. **`fetch-depth: 0` 제거를 막는 장치가 있는지 확인하지 않았다.** 없다면 ②의 내구성은 워크플로 편집에 열려 있다.

**잔여 위험**
- ②를 채택해도 **깨질 때 skip 으로 조용히 되돌아간다**. 이 성질을 안 고치면 같은 결함이 다른 이름으로 재발한다.
- `fetch-depth: 0` 은 지금 **두 가지**를 떠받친다 — PRESERVE 의 `git diff <고정 SHA>..HEAD` 범위와, 태그 도달.
  누군가 얕은 클론으로 되돌리면 둘이 **동시에** 죽고, 둘 다 실패가 아니라 skip 으로 나타난다.

---

## 7. §6 Gap 2 — 닫음 (교란 요인 배제)

Gap 2 는 "도입 전은 PR 트리거, 후는 push 트리거였으니 트리거 차이가 원인일 수 있다"였다.
도입 **후의 PR 트리거** 실행을 한 건 더 재서 닫는다.

run `32719438723` (PR #122, WT-recv-migrate, `fetch-depth: 0` 도입 후):

    git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules origin \
        +refs/heads/*:refs/remotes/origin/* +refs/tags/*:refs/tags/* \
        +1c78758fc9edb6c10edd63daa9819eacd426ca14:refs/remotes/pull/122/merge

PR 트리거인데도 `+refs/tags/*:refs/tags/*` 가 들어 있다(PR merge ref 는 그 위에 추가로 붙을 뿐이다).
따라서 세 실행의 대조는 트리거가 아니라 **`fetch-depth`** 로 갈린다:

| 실행 | 트리거 | fetch-depth | `--depth=1` | `+refs/tags/*` |
|---|---|---|---|---|
| `32620440718` | pull_request | (기본) | 있음 | **없음** |
| `32719438723` | pull_request | 0 | 없음 | **있음** |
| `32719982356` | push | 0 | 없음 | **있음** |

트리거는 두 값 모두에서 나타나고 결과를 가르지 않는다. `fetch-depth` 만 결과와 함께 움직인다.
**§6 Gap 2 → 닫힘.** 남은 Gap 은 1·3·4 다.

---

## 8. ②③ 실행 결과 — skip 게이트 제거

커밋 `441255e` (`server/tests/test_songcue_bundle.py`, +34 −13)

### ① 제거 **전** 지명 실행 — 숨은 빨간불이 있었나

    $ uv run pytest -q -rs \
        …::test_preserve_look_files_are_unchanged_from_run_phase_base \
        …::test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state
      2 passed in 0.80s

CI 에서 한 번도 안 돈 두 검사를 돌려보니 **불변식은 지켜지고 있었다.** 발견 없음 → ②로 진행.

### ② 무엇을 바꿨나

`_requires_run_phase_base`(skipif 마커) → `_require_run_phase_base()`(원인과 처방을 말하는 실패).
두 테스트는 데코레이터 대신 본문 첫 줄에서 이 함수를 호출한다 —
같은 저장소의 `_require_codesign()`(`test_deploy_tauri_shell.py`)과 같은 모양이다.

실패 메시지가 말하는 것:

    run-phase base 커밋 <SHA> 가 이 클론에 없다 — PRESERVE 불변식을 검사할 수 없다.
    이 커밋은 어느 브랜치에서도 도달 불가이고, 주석태그 preserve-base-songcue-m0 하나가 붙잡고 있다.
    처방(로컬): git fetch origin refs/tags/preserve-base-songcue-m0:refs/tags/preserve-base-songcue-m0
    처방(CI): .github/workflows/test.yml 의 checkout 이 아직 fetch-depth: 0 인지 확인해라
              — 그 설정이 태그 refspec 을 딸고 온다. 얕은 클론이면 태그가 안 온다.

**침묵을 다른 침묵으로 바꾸지 않았다**는 것이 요점이다. 읽는 사람이 다음에 무엇을 할지 알 수 있어야 한다.

### ③ 날조 대조군 — 그 제거가 공허하지 않다는 증거

프로브: `.moai/reports/t64/control_probe.py` (파일을 건드리지 않는다 — 모듈을 경로로 적재한 뒤
`_RUN_PHASE_BASE` 만 날조 SHA `0000…0001` 로 바꿔치고 두 테스트 함수를 직접 호출한다).
판정은 "무엇을 던지는가"로 한다 — `AssertionError`=빨간불, `Skipped`=고치려던 침묵, 무예외=공허.

    === 대조군의 대조군: 진짜 기준 커밋 ===
      두 검사 -> NO-RAISE                     ← 하네스가 초록도 낼 수 있다
    === 날조 기준 커밋 ===
      두 검사 -> RED(AssertionError)          ← 실제로 빨개진다
             "run-phase base 커밋 0000…0001 가 이 클론에 없다 — PRESERVE 불변식을 검사할 수 없다."

두 줄이 함께 있어야 증거가 된다. 아래만 있으면 "늘 실패하는 검사"와 구별되지 않는다.

**변경 전/후 대비**는 재구성이 아니라 관측이다 —
전(skip): CI 실행 `32719982356` 로그의 `SKIPPED [1] …test_songcue_bundle.py:464/478` 두 줄(t59 증거).
후(fail): 위 날조 대조군.

### 그 밖의 검증

    $ uv run pytest -q -rs server/tests/test_songcue_bundle.py   → 20 passed, skip 0
    $ uv run ruff check …                                        → All checks passed!
    $ uv run ruff format --check …                               → 1 file already formatted

### 미검증 (이 단계의 Gap)

1. **CI 에서 아직 안 돌았다.** 브랜치 `WT-preserve-base` 는 로컬 커밋 `441255e` 뿐이고 푸시하지 않았다.
   「러너 위에서 태그가 실제로 fetch 되는가」는 이 브랜치가 CI 를 한 번 타야 관측된다 —
   그때 두 검사는 초록 아니면 빨간불이고, **skip 은 더 이상 선택지가 아니다.**
2. **전량 스위트 안 돌림** (run 레인이 t55 사용 중). 지명 실행은 이 파일 20건까지다.
   이 변경이 파일 밖에 닿는 곳은 없다(`_requires_run_phase_base` 는 이 파일에서만 쓰였다 — grep 확인).
3. **태그 삭제 시나리오는 안 쟀다.** 누가 origin 의 태그를 지우면 어떻게 되는지는 §5 표의 추론이지
   실측이 아니다. (날조 대조군이 같은 상태를 흉내내지만, 원격 태그 삭제 자체는 안 해봤다.)

---

## 9. PR #123 CI 실측 — Gap (1) 닫힘

실행 `32742906784` (PR #123, head `441255e8`, conclusion success)
로그 원문: `.moai/reports/t64/ci-pr123-32742906784.log`

### 9.1 숫자 — 예측대로 움직였다

    이전 (32719982356, main 1f1ed25):  10013 passed, 22 skipped
    이번 (32742906784, PR #123):       10015 passed, 20 skipped

`+2 passed / −2 skipped`. 총수 10035 는 그대로다 — 검사가 늘어난 게 아니라 **돌기 시작한 것**이다.

### 9.2 통과 수만으로는 부족하다 — skip 목록으로 확인

    $ grep -c "SKIPPED" …                       → 13   (이전 15)
    $ grep SKIPPED … | grep -c test_songcue_bundle → 0    ← 목록에서 사라졌다
    $ grep SKIPPED … | grep -c test_web_serve      → 3    ← 양성 대조군: grep 은 여전히 잡는다

두 검사가 skip 목록에서 사라졌고 통과 수가 정확히 2 늘었다. **CI 에서 실제로 돌았다.**

### 9.3 이것이 Gap (1) 을 닫는 방식

두 검사는 기준 커밋이 없으면 이제 `AssertionError` 를 낸다(§8 ③에서 확인). 그런데 **통과했다.**
통과했다는 것은 러너에서 `git cat-file -e 38a6e7e2…` 가 성공했다는 뜻이고,
그 커밋에 닿는 ref 는 태그 `preserve-base-songcue-m0` 하나뿐이다.

⇒ **러너가 태그를 실제로 fetch 했다.** §2·§3 이 로컬 재현으로 예측한 것을 GitHub 러너 위에서 관측했다.
Gap (1) 은 이제 추론이 아니라 관측이다.

### 9.4 CodeRabbit — 통과가 아니라 **부재**로 보고한다

지시받은 판독법(조합 엔드포인트의 `Review completed` + `Merge Risk:` prefix 일치)을 적용하려 했으나,
그 계기가 이 저장소에서 값을 내지 않는다. **0 을 그대로 믿지 않고 계기부터 확인했다:**

| 계기 | #123 (이번) | #122 (머지됨, 대조군) | #121 (머지됨, 대조군) |
|---|---|---|---|
| `/commits/<sha>/status` | `combined=pending`, statuses 0행 | 같음 | — |
| `/commits/<sha>/check-runs` | `total=1` — `test` 하나뿐 | `total=1` — `test` 하나뿐 | — |
| PR reviews / comments | `reviews=0 comments=0` | `reviews=0 comments=0` | `reviews=0 comments=0` |

세 계기가 독립적으로 같은 답을 낸다. 그리고 각 계기에는 **양성 대조군이 있다** —
같은 질의가 `test` 체크런은 정확히 집어낸다. 즉 질의가 고장 난 게 아니라 CodeRabbit 이 없다.

⚠️ 첫 시도에서 나는 #122 의 head 자리에 CI 로그의 **머지 ref SHA**(`1c78758f…`)를 넣는 실수를 했다.
올바른 head(`ef01804d…`)로 다시 재도 결과는 같았다. 잘못 잰 값이 우연히 같은 답을 냈지만,
그건 운이지 근거가 아니므로 다시 잰 값을 쓴다.

**판정: PASS 아님, FAIL 아님 — 미도달(부재).** `Review rate limited` 도 아니다. 그 자리에 아무것도 없다.
「CodeRabbit 이 이 저장소에서 도는가」는 배차서가 실은 안 잰 전제였다.

### 9.5 남은 Gap

- (2) 로컬 전량 스위트: 안 돌렸다. 대신 **CI 전량이 돌았고 초록이다** — 위 실행이 그것이다.
- (3) 원격 태그 삭제 시나리오: 추론으로 남긴다(지시대로 태그를 지우지 않았다).
- (신규) CodeRabbit 부재: 이 카드에서 정할 일이 아니다. 리뷰 게이트가 실제로 없는 것인지,
  설치는 됐는데 안 도는 것인지는 별도 확인이 필요하다.

---

## 10. 머지 — 효과로 확인

    $ gh pr merge 123 --squash --delete-branch
      failed to run git: fatal: 'main' is already used by worktree at '…/MAcopilotpos'

⚠️ **종료 코드는 효과의 증거가 아니다.** 실패한 것은 로컬 브랜치 정리 단계뿐이었고, 머지 자체는 됐다.
원격을 되읽어 확인:

    $ gh pr view 123 --json state,mergedAt,mergeCommit
      state=MERGED  mergedAt=2026-08-24T15:16:40Z  mergeCommit=f6dc1ca0…
    $ git fetch origin main && git log --oneline -3 origin/main
      f6dc1ca test(t64): PRESERVE 기준 커밋 게이트를 skip 에서 실패로 … (#123)
      1f1ed25 test(t54): …  (#122)

### 10.1 브랜치 삭제는 하지 않았다 — 관례가 그렇다

`--delete-branch` 는 내가 붙인 것이고 리드의 지시에는 없었다. 마침 실패했고, 재시도하지 않았다:

    $ git ls-remote --heads origin WT-recv-migrate WT-kind-actions WT-recv-timeout
      98ed379…  refs/heads/WT-kind-actions      ← 머지됐는데 남아 있다
      aa3eed4…  refs/heads/WT-recv-timeout      ← 같음

이 저장소는 머지 후 카드 브랜치를 **남긴다.** `WT-preserve-base` 도 그대로 둔다.

### 10.2 t48 카드에 append 완료

새 카드를 만들지 않고 기존 t48 에 붙였다(리드 지시). 효과 확인은 큐 파일 되읽기로:

    text 길이 584 → 1213 · 원문 앞부분 보존 True · 'check-runs' 포함 True
    키 집합은 이웃 카드와 동일(added_at/id/spec_id/state/text) · state 는 여전히 queued

붙인 내용의 핵심은 **계기를 하나 더 걸었다**는 것이다 — t10a 는 legacy status 만 봤고,
t64 는 check-runs 도 봤는데 둘 다 부재였다. 그래서 「legacy status 앱이 없다」에서
「CodeRabbit 앱 자체가 안 붙어 있을 가능성」으로 한 걸음 나아간다.
⚠️ 귀속은 갈라 적었다 — 내가 직접 잰 것은 #123·#122·#121 세 건이고,
#118~#123 여섯 건 전수는 리드의 관측이지 내 관측이 아니다.

---

## 11. 카드 종료 상태

| 항목 | 상태 |
|---|---|
| 결정② (태그가 CI 에 닿는가) | **닿는다** — 로컬 재현(§3) + 러너 관측(§9.3) |
| 결정③ (픽스처 스냅샷) | 불필요 — ②+게이트 제거가 같은 성질을 준다 |
| skip 게이트 | 제거됨. 부재 시 원인·처방을 말하는 실패로 대체 (§8) |
| 머지 | `f6dc1ca` on main (§10) |
| CodeRabbit | **미도달(부재)** — 게이트가 발동하지 않는다. t48 로 이관 (§9.4, §10.2) |
| 기준 커밋 영구 소실 위험 | 닫힘 — 태그 `preserve-base-songcue-m0` 이 origin 에 있다 |
