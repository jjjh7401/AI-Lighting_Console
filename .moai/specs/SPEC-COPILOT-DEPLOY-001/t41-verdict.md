# t41 — label-sync 체크아웃 상향 · 머지 전 미리보기

- 카드: t41 · 브랜치 `WT-label-sync-bump` · base `06cfba6` · 커밋 `.github/` 1파일 1줄
- 측정일: 2026-08-25 · 저장소 `jjjh7401/AI-Lighting_Console`
- **상태: ②에서 멈춤. 머지 안 함.**

## 0. 한 줄

미리보기 전수는 **생성 22 · 변경 1(색만) · 삭제 0**이다. 삭제가 0인 것은 주석을 믿어서가
아니라 **액션 기본값과 소스 두 곳에서 확인**했고, dry-run 이 정말 아무것도 안 바꾼다는 것도
**코드와 효과 양쪽으로** 쟀다.

**이 카드가 이루는 것은 버전 일관성뿐이다.** t35 의 제목이 내건 「Node 20 지원 종료 경고
제거」는 **이 워크플로에서 이뤄지지 않는다** — 경고를 내는 것이 `checkout` 이 아니라
`EndBug/label-sync@v2` 자신이기 때문이다(§6). 목적을 못 이룬 채 완료로 세지 않기 위해
여기 먼저 적는다.

**머지 직전 재측정**(승인 직후, 머지 전): 저장소 라벨 9개·색 동일, `labels.yml` 은
브랜치와 main 이 무차이, 브랜치는 `0 2`(main 대비 뒤처지지 않음). **§4 예측 유효.**

## 1. 배차서 전제를 먼저 독립 확인했다

| 전제 | 확인 | 자리 |
|---|---|---|
| push 트리거의 `paths` 가 자기 자신을 포함 | ✅ | `label-sync.yml:29` |
| push 실행에는 입력이 없어 `dry-run` 이 false 로 떨어짐 | ✅ | `:51` `github.event.inputs.dry_run \|\| 'false'` |

즉 **이 파일을 고쳐 머지하면 머지 즉시 실제 동기화가 돈다.** 전제는 맞다.

## 2. [HARD] dry_run=true 가 정말 읽기 전용인가 — 이름이 아니라 코드로

**한 층 아래에 있었다.** 액션(`EndBug/label-sync@v2`)은 `dryRun` 을 직접 쓰지 않고
`github-label-sync` 패키지에 넘긴다(`src/index.ts:60`, v2 태그 `5207415`).

그 패키지(`github-label-sync@2.3.1`, 액션의 선언 의존)의 갈래:

```js
.then((labelDiff) => {
  if (options.dryRun) {
    return labelDiff;          // ← 여기서 반환
  }
  ...
  const diffActions = actionLabelDiff(...)   // ← 유일한 변이 호출
  return Promise.all(diffActions);
})
```

**변이 호출 앞에서 반환한다.** dry-run 이 하는 일은 `apiClient.getLabels()` 한 번 — 읽기다.

### 2.1 그리고 효과로도 쟀다

미리보기 실행 뒤 라벨을 되읽었다:

```
실행 전  9개 · good first issue = 7057ff
실행 후  9개 · good first issue = 7057ff      ← 아무것도 안 바뀜
```

> 코드를 읽어 확인한 뒤에도 **효과를 되읽은** 이유: 로그에 패키지가 낸다고 되어 있는
> `This is a dry run. No changes have been made on GitHub` 줄이 **안 보였다.** 번들된
> 판이 내가 읽은 2.3.1 과 다를 수 있어 그 불일치를 해소하지 못했으므로, **선언이 아니라
> 결과로 닫았다.** (§6 Gap)

## 3. [HARD] 삭제가 정말 0인가 — 주석을 믿지 않았다

워크플로에는 `delete-other-labels: false` 가 **주석 처리**돼 있고 「기본값이 보존」이라는
주석만 있다. 주석은 동작이 아니므로 두 곳에서 쟀다:

| 근거 | 값 |
|---|---|
| `action.yml` 의 `delete-other-labels.default` | `'false'` |
| `src/index.ts` — `allowAddedLabels: getInput('delete-other-labels') != 'true'` | 입력 부재 → `'' != 'true'` → **true**(보존) |

그리고 미리보기 실물에 **`[added]` 0건** — 저장소에만 있는 라벨은 diff 에 아예 안 나온다.

## 4. 미리보기 전수 (실행 `32781480005`, 브랜치 `WT-label-sync-bump`, `dry-run: true`)

**생성 22** — `[missing]`

```
stale · pinned · security · dependencies
type:feature · type:fix · type:docs · type:chore · type:ci
type:refactor · type:security · type:test · type:performance
priority:P0 · priority:P1 · priority:P2 · priority:P3 · priority:P4
status:in-progress · status:review · status:blocked · status:needs-info
```

**변경 1** — `[changed]`

```
good first issue   #7057ff → #7ae07a      ← 색만. 이름·설명 그대로
```

**삭제 0** — `[added]` 0건. 저장소에만 있는 5개(`bug` `documentation` `enhancement`
`invalid` `question`)는 **보존**된다.

**무변경 3** — `help wanted` · `wontfix` · `duplicate` (선언 26 = 22 + 1 + 3)

## 5. [HARD] 지워지는 라벨이 지금 쓰이고 있는가

삭제가 0이므로 이 질문은 비지만, 배차서 지시대로 쟀다.

```
이슈   0건
PR     136건 (--limit 200 이므로 전수)
이슈·PR 에 붙어 있는 라벨   []   ← 하나도 없음
```

**양성 대조군**(같은 명령·같은 jq, 다른 저장소): `kubernetes/kubernetes` 이슈 5건 →
고유 라벨 **8종**. 즉 위의 `[]` 는 계기가 안 본 0 이 아니라 **잰 0** 이다.

따라서 **되돌리기 어려운 대외 변경은 이 실행에 없다.** 생성 22 · 색 변경 1 뿐이고,
둘 다 되돌릴 수 있다.

## 6. 부수 발견 — 🔴 이 카드는 t35 의 목적을 다 이루지 못한다

t35 의 커밋 제목은 「Node 20 지원 종료 경고 제거」다. 그런데 이번 미리보기 실행 로그
**마지막 줄**이 이렇다:

```
##[warning]Node.js 20 is deprecated. The following actions target Node.js 20 but are
being forced to run on Node.js 24: EndBug/label-sync@v2
```

경고를 내는 것은 **`checkout` 이 아니라 `EndBug/label-sync@v2` 자신**이다. 체크아웃을
v7 로 올려도 이 워크플로의 Node 20 경고는 **안 사라진다.** 이 카드는 형제 워크플로와
**버전 일관성**은 이루지만(아래 §7) 경고 제거는 못 이룬다.

**별도 카드감**: `EndBug/label-sync` 상위 판(또는 대체)으로 올리는 것. 다만 그 카드는
**같은 머지-즉시-실행 부작용을 그대로 갖는다** — 같은 파일이기 때문이다.

## 7. 일관성인가 단독 변경인가

```
test.yml        actions/checkout@v7 · setup-python@v7 · setup-node@v7   (t35, #104)
label-sync.yml  actions/checkout@v4 → v7                                (이 카드)
```

**일관성이다.** 이 저장소의 워크플로는 둘뿐이고, 이 변경으로 `actions/checkout` 은
두 파일에서 같은 판이 된다.

## 8. 판정 대기 — 내가 닫지 않는다

배차서 [HARD] 대로 ②에서 멈춘다. 「의도한 것뿐이다」를 **내가 선언하지 않는다.**
판단에 필요한 것은 위 §4 전수이고, 남는 질문은 하나다:

> **`labels.yml` 의 22개를 지금 실제로 만들 것인가.** 이슈 0건 · PR 136건에 라벨이
> 하나도 안 붙어 있는 저장소에 라벨 체계 26종을 세우는 것이 지금 의도한 것인지.

기술적 위험은 없다(삭제 0 · 되돌릴 수 있음). 이건 **의도의 문제**라 리드가 판단한다.

## 9. Gaps — 재지 않은 것

- **로그에 dry-run 확인 문구가 없는 이유는 못 밝혔다.** 번들 판과 내가 읽은 2.3.1 이
  다를 수 있다. §2.1 에서 **효과 되읽기로 닫았고**, 「로그가 그렇게 말했다」로는 안 적었다.
- **`labels.yml` 26종이 이 프로젝트에 맞는지는 안 봤다.** 이 카드는 동기화가 **무엇을
  바꾸는지**만 잰다.
- **머지 후 push 실행은 아직 안 일어났다.** §4는 브랜치판 dry-run 이고, 머지 시점에
  `labels.yml` 이나 저장소 라벨이 달라져 있으면 결과도 달라진다. **머지 직전에 다시 재라.**
- **`EndBug/label-sync@v2` 는 움직이는 메이저 태그다.** 오늘 `5207415` 로 해소됐고
  머지 시점에 다를 수 있다.

---

## 10. 머지 후 실측 — 미리보기가 맞았는가 (이 카드의 마지막 검산)

머지 `6306f3b` → **push 실행 `32781954418`**(`event=push`, `branch=main`) 이 **즉시** 떴고
`success` 로 끝났다. 배차서가 예고한 부작용이 예고된 그대로 일어났다.

실행 뒤 저장소 라벨을 되읽어 §4 예측과 **계산으로** 대조했다(눈으로 맞추지 않았다):

```
predicted total: 31 | actual total: 31
안 생긴 것   : []            ← 예측에 있는데 실제에 없는 것
예상 못 한 것: []            ← 실제에 있는데 예측에 없는 것
created: 22   (예측 22)
deleted: 0    (예측 0)
good first issue color: 7ae07a   (예측 7ae07a)
저장소 전용 5개 보존: True
```

**집합 차를 양방향으로 냈다.** 개수만 맞추면 「하나 사라지고 하나 생긴」 경우가 통과한다 —
`|A|−|B|` 는 `A\B` 가 아니다. 두 방향이 모두 빈 집합이어야 같은 집합이다.

### 10.1 판정

| 축 | 예측 | 실제 | |
|---|---|---|---|
| 총계 | 31 | 31 | ✅ |
| 생성 | 22 | 22 | ✅ |
| 삭제 | 0 | 0 | ✅ |
| `good first issue` 색 | `7ae07a` | `7ae07a` | ✅ |
| 저장소 전용 5개 | 보존 | 보존 | ✅ |

**dry-run 미리보기가 실제 실행을 정확히 예측했다.** 이 저장소에서 이 워크플로의 미리보기는
믿을 수 있는 계기라는 것이 **한 번 실측으로 확인됐다** — 다음에 이 파일을 건드리는 카드
(예: `EndBug/label-sync` 상향)는 같은 절차를 쓸 수 있다.

### 10.2 남는 것

- **경고는 그대로다.** §6 대로 Node 20 경고를 내는 것은 `EndBug/label-sync@v2` 자신이므로
  이 머지로 사라지지 않았다. 별도 카드.
- **라벨 26종이 지금 쓰이지는 않는다.** 이슈 0 · PR 136 에 붙은 라벨 여전히 0건.
  체계가 생겼을 뿐 운용은 시작되지 않았다 — **생겼다는 것과 쓰인다는 것은 다른 문장이다.**
