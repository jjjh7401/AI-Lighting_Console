# t650 판정 — 박 격자 초 표기 뒤의 0 떼기 (표시만, 저장값 불변)

## 1. 주장 (Claim)

- `ui/src/components/beatGridTransition.ts` 의 `trimSeconds` 가 소수 둘째 자리로 맞춘 뒤 끝의 0을 뗀다. 시안 `beatsToS`(`.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.html` 314행)와 `tc`(같은 파일 331행)와 같은 식이다. 예: `2.00초 (1마디)` → `2초 (1마디)`, `2.50` → `2.5`, `10.00` → `10`.
- 바뀌는 것은 화면과 콘솔 미리보기 문자열뿐이다. 저장값(`fade_bars`, `fade_beats`, `trigger_beat`)과 그 값을 읽는 계산은 바뀌지 않는다.
- 이번 카드에서 손대지 않은 것: `fadeBeforeLabel`(§4 5번), 같은 축의 직접 `toFixed` 자리 세 곳(§4 4번).
- 새 단언은 수정 전 코드에서 실패한다(재현 먼저).

## 2. 증거 (Evidence)

**(a) 수정 전 재현 (RED).** 새 단언과 고친 기대값을 넣은 뒤 수정 전 `trimSeconds` 로 실행했다.

명령: `unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && npm --prefix ui run test -- src/components/beatGridTransition.test.ts src/components/BeatGridPanels.test.tsx`

원문 (실패 줄 전체):

```
 ❯ src/components/beatGridTransition.test.ts (45 tests | 3 failed) 9ms
   × formatFadeSecondsFirst — 초 먼저, 마디는 괄호(REQ-LDBEAT-020(e)) > 끝의 0은 뗀다 — 시안 beatsToS 와 같은 표기(2.00 → 2, 10.00 → 10) 3ms
     → expected '2.00초 (1마디)' to be '2초 (1마디)' // Object.is equality
   × entry 확장 필드(SPEC 0.5.0, 카드 t574) > 박 페이드 표시는 초 먼저, 박은 괄호 0ms
     → expected '1.00초 (2박)' to be '1초 (2박)' // Object.is equality
   × 박 페이드·트리거 박이 이음매·경고·명령에 반영(카드 t574) > 전환 명령: 박 페이드 CueFade 초, 트리거 박 시각, 딜레이 [미확인]·트래킹 송신 없음 0ms
     → expected 'Store Sequence <시퀀스> Cue <큐> CueFade …' to match /CueFade 1\n/
 ❯ src/components/BeatGridPanels.test.tsx (43 tests | 1 failed) 12ms
   × AC-LDBEAT-020(d)(e) — 전환 화면 > 저장된 박 페이드·트리거 박·트래킹을 보여 준다 4ms
     → expected '<div class="beat-grid-transition-view…' to contain '1초 (2박)'
 Test Files  2 failed (2)
      Tests  4 failed | 84 passed (88)
```

수정 전 실제 출력의 CueFade 줄: `Store Sequence <시퀀스> Cue <큐> CueFade 1.00`, 트리거 줄: `(트리거: 4마디 3박 = 곡 9.00초 · 타임코드 이벤트)`. 화면 쪽은 `<b class="beat-grid-tr-fade-value">1.00초 (2박)</b>` 였다.

**(b) 수정 후 (GREEN).** 같은 명령:

```
 ✓ src/components/beatGridTransition.test.ts (45 tests) 6ms
 ✓ src/components/BeatGridPanels.test.tsx (43 tests) 8ms
 Test Files  2 passed (2)
      Tests  88 passed (88)
```

**(c) 전체 UI 시험.** `unset … && npm --prefix ui run test` (전체):

```
 Test Files  60 passed (60)
      Tests  1274 passed (1274)
```

**(d) 타입 검사와 빌드.** `npm --prefix ui run build` (`tsc && vite build`):

```
✓ 97 modules transformed.
dist/assets/index-DMquN6JU.js   364.89 kB │ gzip: 120.70 kB
✓ built in 377ms
EXIT=0
```

**(e) 커밋.** 수정과 시험을 한 커밋(`4ffcddd9`)에 넣었다. `.git/hooks/pre-commit` 은 `moai` 가 PATH 에 있을 때 `moai gate` 를 부른다(이 환경에서는 PATH 에 있다). 훅이 성공으로 끝나 커밋이 만들어졌다. 결과 줄: `[WT-seconds-label 4ffcddd9] fix(t650): … 3 files changed, 12 insertions(+), 4 deletions(-)`. `moai gate` 의 세부 출력은 커밋 출력에 나오지 않아 따로 캡처하지 않았다.

**(f) 표기 근거 (시안).**
- 시안 314행: `const beatsToS=b=>(b*BEAT).toFixed(2).replace(/\.?0+$/,"");`
- 시안 331행: `const tc=t=>(LEAD+t).toFixed(2).replace(/\.?0+$/,"");`
- 수정 후 `trimSeconds`: `seconds.toFixed(2).replace(/\.?0+$/, "")` — 같은 식이다.

**(g) 콘솔 미리보기는 송신 경로가 아니다.** `BeatGrid.tsx:3120–3140` 구간에서 `transitionConsoleCommandLines` 의 결과는 `BeatGridConsoleCommand` 의 `lines` 로만 넘어간다. 이 구간에 송신 호출은 없다.

**(h) 송신 문장에 `before` 라벨이 들어간다 (`fadeBeforeLabel` 을 뺀 근거).**
- `PlanCueRequestGenerator.tsx:342` — `before: fadeBeforeLabel(section)` 를 `upsertChange` 에 넘긴다.
- `PlanCueRequestGenerator.tsx:381·383·389` — `buildCueRequestSentences(...)` 로 문장을 만들고 `onSend(first.sentence, cueNumber)` 로 보낸다.
- `cueRequestSentence.ts:193` — `~ 페이드 ${change.before} → ${change.value}초` 문장을 만든다. `cueRequestSentence.ts:217` 이 `buildCueRequestSentences` 안에서 이 함수를 쓴다.

따라서 `before` 는 화면 표시가 아니라 송신 문장의 일부다. 카드 본문의 「표시만」 전제가 성립하지 않는다.

## 3. 기준선 귀속 (Baseline-attribution)

- 기준 `origin/main` `00d9b86c`. 착수 때 `git fetch origin main` 뒤 `origin/main` 과 워크트리 HEAD 가 모두 `00d9b86c` 였다.
- 워크트리 `.claude/worktrees/t650`, 브랜치 `WT-seconds-label`, 수정 커밋 `4ffcddd9`.
- 의존성은 이 워크트리에 `uv sync --group dev` 와 `npm --prefix ui ci --no-audit --no-fund --loglevel=error` 로 설치했다.
- (a)–(d) 는 커밋 전 작업 트리에서 돌렸다. 커밋 훅(`moai gate`)은 커밋 시점에 다시 돌았고, 커밋이 만들어졌다(e).
- 큐 카드 본문은 주 체크아웃의 `.moai/state/kanban/backlog.json` 에서 `jq` 로 읽었다(읽기 전용). 항목 `t650`, `state: picked`.

## 4. 미검증 (Gaps)

1. **PR 과 CI.** 이 문서를 쓸 때는 PR 이 없었다. PR 번호, 헤드 SHA, `gh pr checks`, 머지 SHA 는 이 문서에 적지 않는다. PR 헤드에 들어가는 문서에 CI 결과를 적으면 헤드가 밀린다(t641 판정 §4-6 과 같은 규약). 그 값은 PR 과 리드 메시지에 있다.
2. **운영 47010 화면.** 머지와 재배포 전이라 실제 런북·박자격자 화면은 보지 않았다. 시험은 함수 단위다.
3. **수정 전 전체 시험.** RED 는 대상 두 파일로만 확인했다. 전체 시험은 수정 후 한 번 돌렸다.
4. **같은 축의 직접 `toFixed` 세 자리 (카드 범위 밖, 손대지 않음).**
   - `ui/src/components/BeatGridTransitionView.tsx:154` — `박 = 곡 ${triggerAt.toFixed(2)}초`. 화면에 `9.00초` 로 남는다. 시안 `tc`(0을 뗌) 기준이면 `9초` 다.
   - `ui/src/components/BeatGridTimelineParts.tsx:150` — `(곡 ${(bar * secondsPerBar).toFixed(2)}초)`.
   - `ui/src/components/BeatGrid.tsx:3166` — `seconds.toFixed(1)`. 소수 한 자리 표기라 규칙이 다르다. 손대기 전에 리드의 판단이 필요하다.
5. **`fadeBeforeLabel` (카드 본문이 지목, 이번에는 뺌).** `PlanCueRequestGenerator.tsx:101–103` 은 `${section.fade_seconds}초` 로 원시 실수를 찍는다(예: `3.1573333333333267초`). 이 라벨은 송신 문장에 들어가므로 표시만 바꾸는 것이 아니다. 문장 형식을 바꿔도 되는지는 리드가 정한다.
6. **콘솔 쪽 해석.** `CueFade 1` 과 `CueFade 1.00` 을 콘솔이 똑같이 받아들이는지는 확인하지 않았다. 이 줄은 미리보기다(§2 (g)).
7. **`moai gate` 세부 결과.** 커밋이 만들어졌다는 사실(훅 성공)만 봤다. `moai gate` 의 항목별 출력은 캡처하지 않았다.

## 5. 잔여 위험 (Residual-risk)

- 소수 둘째 자리 반올림이라 0.005 미만 값은 `0초` 로 보인다. 저장값은 그대로다(t641 과 같은 잔여 위험).
- 시험 문자열이 `2초`, `CueFade 1` 줄, `곡 9초` 같은 표기에 고정돼 있다. 표기 규칙을 다시 바꾸면 시험도 같이 고쳐야 한다.
- `CueFade` 미리보기 숫자가 `1.00` 에서 `1` 로 바뀌었다. 송신 호출은 그 자리에 없다(§2 (g)).

## 6. 진행 메모 (Process notes)

- 세션이 t641 워크트리 안에서 떠서 `EnterWorktree` 가 처음 거절됐다. `ExitWorktree(keep)` 로 나온 뒤 `EnterWorktree(name: t650)` 로 워크트리를 만들었다. t641 워크트리는 그대로 두었다.
- 생성 브랜치 `worktree-t650` 은 카드 id 가 든 이름이라, 착수 규약(`WT-<slug>`, 카드 id 없음)에 맞춰 `WT-seconds-label` 로 바꿨다. 커밋 전에 한 일이다.
- 배차서의 `fadeBeforeLabel` 지목은 §2 (h) 근거로 뺐다. 그 사실을 배차자에게 한 줄로 알린다.
- 쓰지 않은 것: `moai session list`, 주 체크아웃에서의 브랜치 변경, `git worktree add` 직접 호출.
- 변경 범위: `trimSeconds` 한 줄과 주석 한 줄. 새 단언은 `it` 한 개(3 단언)와 `formatEntryFade` 줄 한 개다. 고친 기존 기대값은 세 곳이다: `beatGridTransition.test.ts` 의 `CueFade` 줄과 `곡 9초` 줄, `BeatGridPanels.test.tsx` 의 `1초 (2박)` 줄. 기존 기대값은 표기 규칙 변경을 따라 고쳤다.
