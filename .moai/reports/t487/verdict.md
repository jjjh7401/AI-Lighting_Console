# t487 판정서 — SPEC-LDDESIGN-001 닫기 (implemented → completed)

- 카드: t487 · 감독 결정 5건(2026-09-28) 반영 · 리드 승인 범위 확장 2건(AC-040 문면, REQ-093·불릿 원천 문면)
- 브랜치: `WT-lddesign-close` · 워크트리 `.claude/worktrees/t487`
- base: 착수 시점 `origin/main` = `81bbb916`(t485 #540 머지 포함, `git merge-base --is-ancestor 81bbb916 HEAD` 성공, 분기 `0 0`)
- 커밋:

| 커밋 | 내용 | 카드 단계 |
|---|---|---|
| `f687a9e8` | `GLANCE_RULE` → `director-confirmed-2026-09-28`, 화면 「(감독 확인 전)」 제거 | ④ |
| `beabbbc1` | SPEC 본문 문면 정정(AC-021·044·040·018·046, REQ-013·032·080·093, HISTORY 1행) | ①②③ + 확장 |
| `924871e5` | `implemented → completed · 3-phase close`, progress.md 「종결」 절 | ⑤⑦ |
| `ffdc46f2` | `sync_commit_sha` 백필(`pending-backfill-close` → `924871e5`) | ⑥ |
| (이 커밋) | progress.md 재집계 줄의 틀린 문장·행 인용 정정 + 이 판정서·증거 | 검수 |

## 판정: PASS

## 1. 단계별

### ① AC-021 — PASS
`acceptance.md:270` 「동일한 색(노랑 계열)」 → 「동일한 색(후렴 주색 하나 — 회차 전부 동일)」. 근거: 실기 육안 색은 파랑(`.moai/reports/t474/verdict.md:52-66`). `grep -n "노랑" acceptance.md` → 0건.

### ② AC-044 — PASS
Then 「1 증가」 → 「N만큼 증가 — 생성기는 바뀐 줄마다 별도 요청」. 근거: `sync-evidence/ac_ui_closeout.md:50`(2줄 → 깊이 2). REQ-095 에는 「+1」 주장이 없다(`grep` 확인 — spec.md 의 `+1` 1건은 REQ-083 의 다른 문맥).

### ③ AC-018 — 부분 PASS(t492 후속)
인과 불릿 원천 = 인터뷰 Q1 원문(감독 확인 2026-09-28, `.moai/reports/t485/verdict.md` §2). 「워크시트 `concept` 필드가 불릿 원천」이라 적힌 자리 **5곳** 전부에 앱 경로 원천을 병기했다(워크시트 문장은 지우지 않음): REQ-013·REQ-032·REQ-080·AC-018·AC-046 Given. 나머지 3곳(「그래서 보이는 것」·불릿 클릭 4칸·탭 2·3)은 카드 t492(queued, 큐에서 확인)로 이월.

### ④ AC-049 — PASS
TDD 로 했다.
- RED: 시험 기대값을 먼저 바꿨다 — 서버 `1 failed, 10 passed`(`red_server.txt`), UI `2 failed | 28 passed`(`red_ui.txt`). UI 실패 둘은 정확히 「(감독 확인 전)」 꼬리가 있는 자리.
- 표식이 화면에 **안 남는지**를 재는 부정 단언을 추가했다(`runbookM7.test.tsx` — 기존 `toContain` 만으로는 꼬리가 남아도 통과한다).
- GREEN: 서버 관련 4파일 `39 passed`(`green_server.txt`), UI 전체 `34 files · 741 passed`(`vitest_full.txt`), `tsc --noEmit` exit 0(`tsc.txt`).
- `runbookServerPayload.json`(t493 영역)에는 표식이 0건이라 건드리지 않았다.

### ⑤ 카드 폭 280px — 기록만
progress.md 「종결」 절에 감독 결정 기록(`.moai/reports/t481/verdict.md:55` 인용). 코드 변경 0.

### ⑥ sync_commit_sha — `924871e5`
**필드 뜻을 관행으로 맞췄다(리드 조건).** 같은 두 커밋 구조로 닫은 SPEC-COPILOT-PRESETGUARD-001 을 git 으로 확인했다:

```
0d5760c8 docs(SPEC-COPILOT-PRESETGUARD-001): sync-phase 산출물 — …implemented 전이   -status: in-progress / +status: implemented
5b30a666 chore(SPEC-COPILOT-PRESETGUARD-001): implemented → completed · 3-phase close  -status: implemented / +status: completed
progress.md:192  `sync_commit_sha: 5b30a66` (종결 커밋 …) sync 산출물 커밋은 `0d5760c`.
```

→ 값은 **completed 커밋**. 이번: sync 산출물 커밋 `9c1ec62a`(in-progress→implemented, #529 머지 `30f02eb5` 의 둘째 부모), 종결 커밋 `924871e5`(`git show 924871e5 -- spec.md` → `-status: implemented / +status: completed`). 자리표시자 `pending-backfill-close` → 후속 커밋 `ffdc46f2` 에서 채움.

### ⑦ AC 재집계 → completed
sync 기준선(`sync-evidence/ac_class_recount.txt` 53건: PASS-measured 12 · PASS-test 33(실행 19 + 미실행 14) · n/a 3 · UNVERIFIED 5)에 이후 증거를 이어붙였다:

| 묶음 | 지금 | 근거 |
|---|---|---|
| 미실행 14 | 10 PASS · 037 PASS · 044 PASS · 049 PASS · 018 부분 PASS | `ac_ui_closeout.md` §3(14건 전부 실행) · t481:45 · ②·④ |
| UNVERIFIED 5 | 017·020·039·041·040 전부 PASS(040 은 (2)(6) n/a) | t480:20 · `ac_ui_closeout.md:39,45,47` · `ac_server_closeout.md:13` + t481:46 + t467:6 |
| AC-021 | PASS | ① |

**결과: PASS 49 · 부분 PASS 1(AC-018) · n/a 3 · UNVERIFIED 0 · FAIL 0 = 53.** 레인이 먼저 센 값과 manager-docs 가 따로 센 값이 같다.

## 2. 범위 확장(리드 승인 2026-09-28)

- AC-040 문면 + 같은 사실의 REQ-093: (2) 팬 폭·(6) 페이저=BPM 은 감독 결정 2026-09-27 n/a(`.moai/reports/t467/verdict.md:6,56`). 근거 `sync-evidence/ac_server_closeout.md:108` 「마지막 닫기에서 반영해야」.
- ③ 의 불릿 원천 문면을 AC-018 한 곳이 아니라 같은 주장이 있는 5곳 전부로.

## 3. 검수에서 고친 것 — 에이전트 산출물의 틀린 문장 둘

manager-docs 가 쓴 progress.md 재집계 줄(674행):
1. 「14건 중 13건이 실행 확인됐다」 → 틀림. `ac_ui_closeout.md` §3 은 14건 **전부** 돌렸고 018 은 실행 결과가 FAIL(일부)였다. → 「14건 전부 실행됐다」로 정정.
2. 10건 PASS 의 인용 「라인 39/45/47」 → 그 행은 AC-020·039·041(UNVERIFIED 쪽)이다. 10건의 실제 행은 38·40·41·42·44·48·49·52·54·55 → 정정.

## 4. 검증

- `moai spec lint .moai/specs/SPEC-LDDESIGN-001/spec.md` → `No findings`, exit 0(`spec_lint_after.txt`·`spec_lint_final.txt`)
- `grep -n "^status:" spec.md` → `5:status: completed`
- `grep -n sync_commit_sha progress.md` → `583:sync_commit_sha: 924871e5`
- progress.md 의 기존 줄 중 지운 것은 `sync_commit_sha: pending-backfill` 한 줄뿐(`git diff beabbbc1 HEAD` 의 `-` 줄 전수). 날짜 붙은 sync 기록 숫자는 그대로 두고 「종결」 절로 대체 고지.

## 5. 관찰 — `moai spec drift` 출력에 이 SPEC 이 없다 (이 카드가 원인 아님)

`moai spec drift --json --no-cache` → 기록 62개, **SPEC-LDDESIGN-001 없음**(`spec_drift_after.json`). sync 때 파일(`sync-evidence/spec_drift_before.json`)은 63개이고 이 SPEC 이 있었다(`in-progress`, era-exempt, Drifted=false). 두 집합의 차이는 이 SPEC 하나뿐이다.

원인이 이 카드인지 대조군 넷으로 쟀다(전부 커밋 안 한 임시 교체 → 즉시 복원):

| 대조 | LDDESIGN 기록 |
|---|---|
| spec.md 의 status 만 `implemented` 로 | 없음(`spec_drift_control_implemented.json`) |
| spec.md 를 origin/main 판으로 | 없음(`spec_drift_control_base.json`) |
| progress.md 를 origin/main 판으로 | 없음(`spec_drift_control_progress_base.json`) |
| spec·acceptance·progress 셋 다 origin/main 판으로 | 없음, 기록 62개(`spec_drift_control_all_base.json`) |

양성 대조: 다른 completed SPEC(PRESETGUARD·EVAL·FXLIB)은 같은 출력에 있다. → **파일 내용이 origin/main 과 같아도 빠진다 — 이 카드의 변경이 원인이 아니다.** 원인은 재지 않았다(범위 밖). 카드 후보로 리드에 올린다.

## 6. 안 잰 것

- 전체 pytest 는 로컬에서 안 돌렸다 — 서버 변경은 상수 1개·주석이라 관련 4파일만. 전체는 CI 가 PR 헤드에서.
- 브라우저에서 화면을 띄워 「감독 확인 전」이 사라진 것을 보지 않았다 — 렌더 시험(`renderToStaticMarkup`)의 부정 단언으로만.
- `ui/src/components/cueRequestWarnings.ts:1-5` 주석이 (2)(6) 을 「t467 로 넘긴다」고 적고 있지만 t467 은 n/a 로 닫혔다(dropped). 낡은 주석 — 범위 밖이라 두었다.
- drift 누락의 원인(§5).
