# t653 판정 — 전환 화면·장면 전환 머리글의 초 표기 뒤 0 떼기 (표시만, 저장값 불변)

## 1. 주장 (Claim)

- `ui/src/components/BeatGridTransitionView.tsx:154` 의 「박 = 곡 N초」와 `ui/src/components/BeatGridTimelineParts.tsx:150` 의 장면 전환 머리글 「(곡 N초)」가 `toFixed(2)` 뒤에 0을 남기던 것을 `trimSeconds` 로 바꿨다. 예: `8.00초` → `8초`, `120.00초` → `120초`. 시안 `tc`·`beatsToS` 와 같은 식이다.
- `trimSeconds` 는 t650 에서 만든 함수를 `export` 로 열었다. 정의와 식은 그대로다(`beatGridTransition.ts:20-22`).
- 저장값(`fade_bars`, `trigger_beat` 등)과 그 값을 쓰는 계산은 바뀌지 않는다.
- `BeatGrid.tsx:3166` 의 `seconds.toFixed(1)` 은 그대로 둔다. 시안 `#stT` 가 같은 자리를 한 자리 소수로 찍는다(§2 (g)).
- `fadeBeforeLabel`(`PlanCueRequestGenerator.tsx:101-103`)은 손대지 않았다. 배차서의 「송신 문장에 들어간다」는 전제는 코드를 다시 읽어 보니 틀렸다(§2 (h)).
- 새 단언 두 개는 수정 전 코드에서 실패한다(RED, §2 (b)).

## 2. 증거 (Evidence)

**(a) 의존성 설치.** 명령: `npm --prefix ui ci --no-audit --no-fund --loglevel=error`. 출력: `added 101 packages in 1s`. 종료 코드 0.

**(b) 수정 전 재현 (RED).** 새 단언 두 개를 넣고 수정 전 코드로 실행했다. 명령: `unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && FORCE_COLOR=0 npm --prefix ui run test -- src/components/BeatGridPanels.test.tsx`

원문 (색 코드만 뺐다):

```
× 카드 t653 — 초 표기 뒤의 0 떼기 (시안 tc·beatsToS 와 같은 표기) > 전환 화면 「박 = 곡 N초」는 8.00 대신 8로 쓴다 5ms
  → expected '<div class="beat-grid-transition-view…' to contain '박 = 곡 8초'
× 카드 t653 — 초 표기 뒤의 0 떼기 (시안 tc·beatsToS 와 같은 표기) > 장면 전환 머리글 「(곡 N초)」는 120.00 대신 120으로 쓴다 1ms
  → expected '<div class="beat-grid-scene-panel" ar…' to contain '(곡 120초)'
 Test Files  1 failed (1)
      Tests  2 failed | 43 passed (45)
```

수정 전 받은 HTML 의 해당 조각: `…<div>4마디 <select aria-label="트리거 박">…</select> 박 = 곡 8.00초</div>…` 과 `<span>장면 전환 · 60마디 (곡 120.00초)</span>`.

**(c) 수정 후 대상 두 파일 (GREEN).** 같은 명령에 파일 두 개를 넣었다: `src/components/BeatGridPanels.test.tsx src/components/beatGridTransition.test.ts`. 출력: `Test Files 2 passed (2)`, `Tests 90 passed (90)`. 종료 코드 0.

**(d) 전체 UI 시험.** 명령: `FORCE_COLOR=0 npm --prefix ui run test` (`vitest run`). 출력: `Test Files 60 passed (60)`, `Tests 1276 passed (1276)`. 종료 코드 0. 수정 전 전체 시험은 돌리지 않았다.

**(e) 타입 검사와 빌드.** 명령: `npm --prefix ui run build` (`tsc && vite build`). 종료 코드 0. 끝부분:

```
dist/index.html                   0.46 kB │ gzip:   0.32 kB
dist/assets/index-Bt-LQBE2.css   74.81 kB │ gzip:  14.44 kB
dist/assets/index-qCfCezuL.js   364.88 kB │ gzip: 120.70 kB
✓ built in 421ms
```

**(f) 변경 범위.** 커밋 전 `git diff --stat`: `4 files changed, 41 insertions(+), 3 deletions(-)`. 대상은 `BeatGridPanels.test.tsx`, `BeatGridTimelineParts.tsx`, `BeatGridTransitionView.tsx`, `beatGridTransition.ts` 네 파일이다. 남은 원시 `toFixed` 확인: `grep -n "toFixed" ui/src/components/BeatGridTransitionView.tsx ui/src/components/BeatGridTimelineParts.tsx` 는 출력이 없었다(종료 코드 1).

**(g) 시안 확인 — `BeatGrid.tsx:3166` 판단.** 시안 `.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.html` 을 직접 읽었다.

- 314행: `const beatsToS=b=>(b*BEAT).toFixed(2).replace(/\.?0+$/,"");` — 초, 뒤의 0 제거.
- 331행: `const tc=t=>(LEAD+t).toFixed(2).replace(/\.?0+$/,"");` — 타임코드, 뒤의 0 제거.
- 437행: `document.getElementById("stT").textContent=`${b===0?"앞박":b+"마디"} · ${barT(b).toFixed(1)}초`;` — 무대 머리글, 한 자리 고정, 뒤의 0을 떼지 않는다.
- 앱의 `BeatGrid.tsx:3158-3159` 주석이 이 자리를 시안 `#stT` 「12마디 · 25.1초」로 적는다.

→ 판단: 무대 머리글은 시안이 한 자리 소수로 정한 표기다. 같은 축의 값이라도 시안이 다른 규칙을 쓰므로 `toFixed(1)` 을 바꾸지 않는다. 시안의 다른 길이 표기(433·478·496행)도 `toFixed(1)` 이다.

**(h) `fadeBeforeLabel` 송신 경로 조사 (읽기만, 수정 없음).** 각 줄은 이 워크트리에서 직접 읽었다.

1. `PlanCueRequestGenerator.tsx:101-103` `fadeBeforeLabel` 은 `section.fade_seconds != null ? `${section.fade_seconds}초` : "—"` 이다. 원시 실수를 그대로 찍는다.
2. `PlanCueRequestGenerator.tsx:336-343` `applyFade` 는 `upsertChange({ field: "fade_seconds", value: Number(fadeInput), before: fadeBeforeLabel(section) })` 를 부른다. `value` 는 입력한 수, `before` 는 이전 값 라벨이다.
3. `before` 를 읽는 곳은 두 군데뿐이다. (i) `cueRequestSentence.ts:192-193` 의 `cueRequestDiffLabel` 은 `~ 페이드 ${before} → ${value}초` 라는 화면 라벨을 만든다. 호출처는 `PlanCueRequestGenerator.tsx:660` 의 `<span>{cueRequestDiffLabel(entry.change)}</span>` 하나다(grep). (ii) 송신 문장을 만드는 `cueRequestSentence`(`cueRequestSentence.ts:156-180`)의 `fade_seconds` 분기(166-167행)는 `큐 ${cueNumber} 페이드 ${change.value}초로 바꿔줘` 이고, `before` 를 읽지 않는다.
4. 송신 경로: `PlanCueRequestGenerator.tsx:378-390` `sendAll` → `buildCueRequestSentences`(`cueRequestSentence.ts:212-224`, 217행에서 `cueRequestSentence` 를 부른다) → `onSend(first.sentence, cueNumber)`(389행) → `SongTimeline.tsx:255` `onSend={onGeneratorSend}` → `App.tsx:1251` `onGeneratorSend={sendGeneratorRequest}` → `App.tsx:696-701` `sendGeneratorRequest` → `sendChat(text, cueNumber)`. 주석(`App.tsx:693-695`)대로 감독이 직접 친 채팅과 같은 대화 경로다. 이 카드는 `sendChat` 아래, 즉 채팅을 받는 쪽과 콘솔 쓰기까지는 추적하지 않았다.

→ 결론: `fadeBeforeLabel` 의 형식과 반올림은 송신 문장에 들어가지 않는다. 송신되는 수는 `value`(입력한 수 그대로)이고, 이 경로에는 반올림이 없다. 그러므로 「콘솔이 반올림 값을 같은 뜻으로 받는가」라는 질문은 이 경로에서 성립하지 않는다.

→ t650 판정 §2(h) 의 「송신 문장의 일부」는 틀렸다. 근거로 든 `cueRequestSentence.ts:193` 은 화면 라벨이다. 정정이 필요하다(§6).

→ 원시 실수 표시(예: `3.1573333333333267초`)는 변경 스택 화면 라벨에만 나타나는 표시 문제다. 이 예시는 t650 판정 §4-5 에서 옮긴 것이고 이번에 다시 관측하지 않았다. 콘솔 영향은 없다. 카드 범위 밖이라 손대지 않았다. 처리 여부는 리드가 정한다.

**(i) 커밋 훅과 게이트.** `.git/hooks/pre-commit` 은 `moai` 가 PATH 에 있으면 `moai gate` 를 부른다. `/bin/sh -c 'command -v moai'` 가 `/Users/studiox/.local/bin/moai` 를 찾았으므로 커밋 훅은 게이트를 실행했다. 커밋 `7ec8f3cd` 가 만들어졌으므로(커밋 종료 코드 0) 게이트도 통과했다. 게이트를 따로 실행한 결과는 종료 코드 0, 출력 없음(로그가 비어 있음), 실행 뒤 `git status --short` 출력 없음이었다.

## 3. 기준선 귀속 (Baseline-attribution)

- 기준 `origin/main`: `58d3da69`. 이 세션에서 `git fetch origin main` 뒤 확인했다. 착수 때 워크트리 HEAD 도 `58d3da69` 였다. 이 커밋에는 t650 판정 수정(#688)이 들어 있어 `trimSeconds` 가 이미 있었다.
- 워크트리 `.claude/worktrees/t653`, 브랜치 `WT-seconds-rest`, 수정 커밋 `7ec8f3cd`.
- §2 의 (b)–(e) 는 커밋 전 작업 트리에서 돌렸다. (i) 의 게이트는 커밋 시점에 한 번, 커밋 뒤에 한 번 더 돌렸다.
- 배차 본문의 줄 번호 154·150·3166·101–103 은 이 워크트리에서 다시 읽어 확인했다.

## 4. 미검증 (Gaps)

1. PR, CI, 머지 SHA 는 이 문서에 적지 않았다. PR 헤드에 들어가는 문서에 CI 결과를 적으면 헤드가 밀린다(t650 §4-1 과 같은 규약). 그 값은 PR 과 리드 메시지에 있다.
2. 실제 앱 화면(운영 47010 런북, 박자 격자)은 보지 않았다. 시험은 `renderToStaticMarkup` 으로 만든 HTML 문자열 단언이다. 이 프로젝트에는 jsdom 이 없다.
3. 수정 전 전체 UI 시험은 돌리지 않았다. RED 는 대상 파일 한 개로만 확인했다.
4. `fadeBeforeLabel` 의 송신 뒤 처리(채팅을 받는 쪽이 `CueFade` 명령을 만드는 과정과 콘솔 쓰기)는 추적하지 않았다. 확인한 것은 「`before` 는 송신 문장에 없다」는 사실뿐이다.
5. `moai gate` 의 항목별 결과는 얻지 못했다. 출력이 없었다. 이 저장소의 UI 시험과 빌드는 §2 (d)·(e) 에서 따로 확인했다.
6. `BeatGrid.tsx:3166` 을 그대로 둔 판단은 시안 텍스트에 근거한다. 화면에서 대조하지 않았다.

## 5. 잔여 위험 (Residual-risk)

- 표기 규칙이 바뀌면 단언(`8초`, `120초`)도 같이 고쳐야 한다. t650 과 같은 잔여 위험이다.
- 소수 둘째 자리로 반올림하므로 0.005 미만 값은 `0초` 로 보인다. 저장값은 그대로다.
- `fadeBeforeLabel` 의 원시 실수 표시는 남아 있다. 표시 전용이고 송신에는 영향이 없다(§2 (h)).

## 6. 진행 메모 (Process notes)

- 세션은 t650 워크트리에서 떴다. `ExitWorktree` 는 이 세션이 `EnterWorktree` 로 들어온 워크트리가 아니어서 할 일이 없었다(호출하지 않았다). 주 체크아웃이나 다른 워크트리를 `git -C` 로 가리키는 명령은 하네스가 거절했다. 그래서 현재 디렉터리에서 `git worktree add -b WT-seconds-rest <path> origin/main` 을 실행한 뒤 `EnterWorktree(path)` 로 그 워크트리에 들어갔다.
- **t650 판정 정정.** t650 판정 §2(h) 는 `fadeBeforeLabel` 이 「송신 문장의 일부」라고 했다. 코드를 다시 읽어 보니 틀렸다(§2 (h)). t650 판정 §4-5 의 「송신 문장에 들어가므로」도 같은 근거에 기댄다. 리드에게 한 줄로 알린다.
- 쓰지 않은 것: `moai session list`, 주 체크아웃에서의 브랜치 변경, `git stash`.
