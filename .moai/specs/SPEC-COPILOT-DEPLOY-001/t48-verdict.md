# t48 — CodeRabbit 절에 적용 조건을 적는다

- 카드: t48 · 브랜치 `WT-coderabbit-scope` · base `0634947`
- 대상: `.claude/rules/moai/workflow/kanban-dispatch.md` § CodeRabbit is not read from `gh pr checks`
- 측정일: 2026-08-25 · 저장소 `jjjh7401/AI-Lighting_Console`

## 1. 무엇이 문제였나

그 절은 「`gh pr checks` 에 CodeRabbit 행이 **있을 때** 그 행을 어떻게 읽는가」를 정한 것이다.
행이 없으면 애초에 읽을 것이 없으므로 **발동하지 않는다.** 그런데 그 조건이 문면에 없었다.

문면에 없는 조건은 읽는 사람이 채워 넣는다. 채워 넣는 값은 대개 「아직 `Review completed`
가 아니니 못 나간다」이고, 그러면 카드는 **오지 않을 신호를 기다린다.** 그것은 대기가 아니라
정지이고, 정지는 리뷰에서 안 보인다.

이 오독은 가설이 아니라 관측이다 — 오늘 밤 리드가 t64·t55 배차서에서 두 번 밟았고 두 레인이
없는 신호를 기다렸다. 이 카드는 그 비용을 다시 안 치르게 하는 것이다.

## 2. 실측 — 인용이 아니라 다시 잰 값

리드가 전수에 가까운 근거를 줬지만 「인용하지 말고 다시 재라」고 했으므로, 이 트리에서 새로 쟀다.

| 축 | 명령 | 관측값 | 대조군 |
|---|---|---|---|
| PR 리뷰 | `gh pr list --state all --limit 20 --json reviews` | **20/20 이 `0`** (#115~#134) | k8s `#141336` → `1` ✅ |
| 조합 상태 | `gh api .../commits/c6d6c84/status` | `total_count: 0` · `statuses: []` | k8s PR head → **14 contexts** ✅ |
| 체크런 | `gh api .../commits/c6d6c84/check-runs` | `total_count: 1` · `["test"]` | 자체가 비어 있지 않음 |
| 롤업 20건 | `statusCheckRollup` | 20/20 이 `["test"]` 뿐 | 자체가 비어 있지 않음 |
| 설정 파일 | `ls -a \| grep -i coderabbit` | 없음 | — |
| 봇 코멘트 | `issues/134/comments` | `[]` | — |

**대조군이 결정적이다.** 같은 토큰·같은 jq 로 쿠버네티스 PR head 를 재니 상태 14건이 나왔고,
리뷰가 달린 PR 을 재니 `1` 이 나왔다. 즉 위의 0 은 **계기가 안 본 0 이 아니라 잰 0** 이다.
대조군 없이 적었다면 「검색이 0을 냈다고 없는 게 아니다」에 그대로 걸렸을 것이다.

세 경로(상태·체크런·리뷰) 모두 0이고, 그중 둘에 양성 대조군이 붙는다.

## 3. 재면서 새로 나온 것 — `state` 로는 구분이 안 된다

배차서에 없던 값이다.

```
우리 저장소  state="pending"  total_count=0    ← 상태가 하나도 없음
쿠버네티스   state="pending"  total_count=14   ← 상태가 있고 아직 도는 중
```

조합 엔드포인트는 **0건일 때도 `pending`** 을 낸다. 「진행 중」과 **글자가 같다.**
그래서 `state` 만 보고 판단하면 미발동이 「곧 끝나겠지」로 읽힌다 — 이 카드가 막으려는
오독의 가장 그럴듯한 형태가 바로 이것이고, 문면에 [HARD] 로 넣었다.

## 4. 문면에 넣은 것 — 요구 4항 대응

| 요구 | 문면 |
|---|---|
| ① 발동 조건(행이 있을 때만) | 절 첫 문단 — "Applies only where a CodeRabbit row exists" |
| ② 행이 없으면 게이트가 아니라 미발동 | [HARD] "A missing row is not a FAIL" |
| ③ 미발동은 PASS 도 FAIL 도 아니다 | 같은 문단 — "neither PASS nor FAIL … that is not waiting, it is a stall" |
| ④ 이 저장소 실측과 날짜 | 절 끝 "Measured example" — 저장소 이름·날짜·PR 범위·대조군까지 |

추가로 §3 의 `state` 함정을 [HARD] 한 줄로 넣었다.

## 5. 공유 문서 제약을 어떻게 지켰나

[HARD] 「이 저장소엔 없다」를 본문에 못박지 말 것 — 규칙 문서는 여러 프로젝트가 공유한다.

지킨 방법은 **문장의 종류를 나눈 것**이다.

- **규범문은 조건절로만 썼다.** "where the app is not installed, the section does not fire."
  주어가 특정 저장소가 아니라 조건이다. CodeRabbit 이 붙은 저장소에서는 절이 그대로 산다.
- **실측은 예시로, 이름과 날짜를 달아 붙였다.** "an observation, not a claim about your repository",
  그리고 저장소 이름을 **명시**했다. 「이 저장소」라고 쓰지 않은 것이 요점이다 — 그 지시어는
  파일이 복사되는 순간 조용히 다른 곳을 가리킨다.
- **재는 법을 같이 줬다.** 다음 사람이 자기 저장소에서 한 줄로 확인할 수 있으면 남의 실측을
  자기 사실로 물려받지 않는다.

## 6. 부수 발견 — 이 카드에서 고치지 않은 것

**(a) `kanban-dispatch-detail.md` 가 main 에 없다.**
`kanban-dispatch.md` 는 그 companion 을 **15회** 참조하는데, `origin/main`(`0634947`) 기준으로
그 파일은 트리에도 인덱스에도 없다(`git ls-tree HEAD` 공백, gitignore 아님).
파일 자체는 `49c235a`(t16 하네스 재동기화, 204줄 추가)에 존재하지만 그 커밋은
`jjjh7401/LX-SEQ` 에만 있고 **main 의 조상이 아니다**(`git merge-base --is-ancestor` → false).
즉 잃어버린 게 아니라 **아직 머지되지 않은 것**이다. 내 절이 쓰는 기존 포인터는
CodeRabbit 이 붙은 저장소에서는 유효하므로 **지우지 않았고**, 새 포인터도 추가하지 않았다.

**(b) 그 companion 자신이 「this repository」로 오늘의 결함을 이미 갖고 있다.**
`49c235a` 판 companion § CodeRabbit endpoint measurement 는
"measured on **this repository**, exactly one CodeRabbit entry per head" 라고 적는다.
그런데 §2 에서 이 저장소는 CodeRabbit 항목이 **0건**이다. 모순이 아니라 **지시어가 옮겨 붙은 것**이다 —
그 문장은 하네스 원본 저장소에서 잰 값인데, 파일이 이 저장소로 동기화되면서 「this repository」가
조용히 여기를 가리키게 됐다. 스텁이 「앱이 붙어 있는 게 당연하다」처럼 읽히는 이유가 여기 있다.
그 문장이 리드가 [HARD] 로 금지한 형태의 실물 사례다. **다만 그 파일은 main 에 없고 남의
브랜치에 있으므로 이 카드에서 고치지 않았다** — 별도 카드감이다.

## 7. Gaps — 재지 않은 것

- **다른 저장소에서 이 절이 제대로 발동하는지는 못 쟀다.** CodeRabbit 이 붙은 저장소에
  접근이 없어 `Review completed` 실물 문자열과 `Merge Risk:` 줄은 **관측하지 못했다.**
  기존 1·2 조건은 손대지 않았고, 그것이 맞다는 판정도 내리지 않는다.
- **20건은 전수가 아니다.** `--limit 20` 으로 #115~#134 만 봤다. 그 이전 PR 에 CodeRabbit 이
  붙었다가 떨어졌을 가능성은 배제하지 못한다. 다만 카드의 주장(「지금 안 붙어 있다」)에는
  최근 20건이면 충분하고, 문면은 어차피 「재라」고 말한다.
- **앱 설치 여부를 설치 API 로 직접 확인하지 않았다.** `repos/.../installations` 는 관리자
  권한이 필요하다. 세 경로가 모두 0이고 둘에 양성 대조군이 붙는 것으로 갈음했다 —
  「설치되지 않았음을 증명했다」고는 적지 않는다.
