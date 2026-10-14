# t654 검증 기록 — 수정 요청 생성기 「이전 값」의 페이드 초 표기 (표시만, 저장값 불변)

이 문서는 관측한 결과만 적는다. 판정과 카드 닫기는 리드가 한다. PR·CI·머지 SHA 는 이 문서에 적지 않는다(PR 헤드에 들어가는 문서에 CI 결과를 적으면 헤드가 밀린다, t650 §4-1 · t653 §4-1 과 같은 규약). 그 값은 PR 과 리드 메시지에 있다.

## 1. 주장 (Claim)

- `fadeBeforeLabel`(`ui/src/components/PlanCueRequestGenerator.tsx`)이 원시 실수 대신 시안 tc 표기(소수 둘째 자리, 뒤 0 제거)로 찍는다. 예: `3.1573333333333267` → `3.16초`, `2` → `2초`, `2.5` → `2.5초`, `null` → `—`.
- 저장값(`fade_seconds`), 송신 값(`value`), 송신 문장은 바뀌지 않는다.
- 이 변경은 송신 경로에 들어가지 않는다. 송신 문장에 `before` 가 없다는 것을 착수 전 grep 으로 확인했다(§2-1).

## 2. 증거 (Evidence)

### 2-1. 착수 전 게이트 — `before` 값이 송신 경로로 나가는지 (읽기만, 수정 없음)

명령 1 — 서버와 UI 에서 `before` 를 키나 속성으로 읽는 곳 (발췌, 테스트 줄 생략):

```
$ git grep -n -P "\"before\"|'before'|\.before\b" -- server ui/src ':!*.test.*' ':!*__fixtures__*'
server/director/schemas/exchange.schema.json:1602:        "before": {
server/director/schemas/exchange.schema.json:1630:        "before",
server/director/schemas/exchange.schema.json:1884:        "before": {
server/director/schemas/exchange.schema.json:1898:        "before",
server/director/validate/diagnostics.py:42:    "before",
server/director/validate/diagnostics.py:121:            "before": self.before if self.before is not None else absent(),
server/director/validate/pipeline.py:299:        "before": internal["before"],
server/web/session.py:6124:        pre_state_unknown = run.before is None
server/web/session.py:6125:        preexisting = frozenset() if pre_state_unknown else run.before
ui/src/components/cueRequestSentence.ts:185 … 203   (`change.before` 를 화면 라벨 `~ … ${change.before} → …` 에서만 읽는다)
```

명령 2 — UI 에서 `before` 단어가 나오는 곳 (발췌):

```
$ git grep -n -w before -- ui/src ':!*.test.*' ':!*__fixtures__*'
ui/src/components/PlanCueRequestGenerator.tsx:332:      before: beforeIntensityLabel(),
ui/src/components/PlanCueRequestGenerator.tsx:342:      before: fadeBeforeLabel(section),
ui/src/components/PlanCueRequestGenerator.tsx:348:    upsertChange({ field: "trans", value, before: section.trans ?? "—" });
ui/src/components/cueRequestSentence.ts:23:  before: string;          (…타입 정의 줄 23–99, 값 읽기 없음…)
ui/src/components/cueRequestSentence.ts:185:      return `~ ${groupPrefix(change.groups)}밝기 ${change.before} → ${change.value}%`;
ui/src/components/cueRequestSentence.ts:193:      return `~ 페이드 ${change.before} → ${change.value}초`;
ui/src/components/cueRequestSentence.ts:203:      return `~ 포지션 ${change.before} → ${change.presetNo} ${change.value}`;
```

`cueRequestSentence.ts` 의 100–184행(문장 생성 `cueRequestSentence` 포함)에는 `before` 가 한 번도 나오지 않는다. 문장 생성 함수는 `value` 만 쓴다.

명령 3 — 변경 객체가 직렬화되는지:

```
$ git grep -n -e "GeneratorChange" -e "JSON.stringify" -- ui/src/components/PlanCueRequestGenerator.tsx ui/src/components/SongTimeline.tsx ui/src/App.tsx ui/src/components/cueRequestSentence.ts
(타입 선언과 import 줄만 나온다. JSON.stringify 는 이 네 파일에 없다.)
```

송신 경로 코드 (`PlanCueRequestGenerator.tsx` 378–390행, 발췌):

```ts
  function sendAll() {
    if (stack.length === 0 || sendingId !== null) return;
    const items: GeneratorChangeItem[] = stack.map((entry) => ({ id: entry.id, change: entry.change }));
    const sentences = buildCueRequestSentences(cueNumber, items, freeText);
    ...
    onSend(first.sentence, cueNumber);
  }
```

앱 쪽 (`App.tsx` 696–701행):

```ts
  const sendGeneratorRequest = useCallback(
    (text: string, cueNumber: number) => {
      sendChat(text, cueNumber);
    },
    [sendChat],
  );
```

결론: 클라이언트 밖으로 나가는 것은 문장 한 줄(`first.sentence`)뿐이다. `before` 는 그 문장에 들어가지 않는다. 게이트 통과.

서버 쪽 `before` 필드 (§4-2 의 갭)는 클라이언트 라벨과 다른 경로로 보이지만, 의미는 읽지 않았다.

### 2-2. RED — 수정 전 시험 원문

명령: `npm --prefix ui run test -- src/components/fadeBeforeLabel.t654.test.tsx`

```
 ❯ src/components/fadeBeforeLabel.t654.test.tsx (3 tests | 1 failed) 3ms
   × 수정 요청 생성기 이전 값 — 페이드 표시 (카드 t654) > 원시 실수는 소수 둘째 자리로 맞춘다 3ms
     → expected '3.1573333333333267초' to be '3.16초' // Object.is equality

 FAIL  src/components/fadeBeforeLabel.t654.test.tsx > 수정 요청 생성기 이전 값 — 페이드 표시 (카드 t654) > 원시 실수는 소수 둘째 자리로 맞춘다
AssertionError: expected '3.1573333333333267초' to be '3.16초' // Object.is equality

Expected: "3.16초"
Received: "3.1573333333333267초"

 Test Files  1 failed (1)
      Tests  1 failed | 2 passed (3)
```

실패는 기대한 이유다(원시 실수가 그대로 찍힘). 나머지 두 건(뒤 0 제거, `null` → `—`)은 수정 전에도 통과했다.

### 2-3. GREEN — 수정 후 시험 원문

명령: `npm --prefix ui run test -- src/components/fadeBeforeLabel.t654.test.tsx`

```
 ✓ src/components/fadeBeforeLabel.t654.test.tsx (3 tests) 1ms

 Test Files  1 passed (1)
      Tests  3 passed (3)
```

명령: `npm --prefix ui run test` (전체 UI 시험)

```
 ✓ src/components/nullFade.t490.test.tsx (7 tests) 16ms
 ✓ src/components/PlanCueRequestGenerator.test.tsx (30 tests) 15ms
 ✓ src/components/cueRequestSentence.test.ts (26 tests) 4ms
 ✓ src/components/fadeBeforeLabel.t654.test.tsx (3 tests) 1ms
 …
 Test Files  61 passed (61)
      Tests  1279 passed (1279)
```

명령: `ui/node_modules/.bin/tsc -p ui/tsconfig.json --noEmit; echo tsc_exit=$?`

```
tsc_exit=0
```

### 2-4. 변경 범위

`git status --short` (수정 전, 커밋 준비 시점):

```
 M ui/src/components/PlanCueRequestGenerator.tsx
?? ui/src/components/fadeBeforeLabel.t654.test.tsx
```

(이 문서 `.moai/reports/t654/verdict.md` 와 두 파일이 커밋 대상이다.)

`git diff -- ui/src/components/PlanCueRequestGenerator.tsx` 의 핵심:

```diff
+import { trimSeconds } from "./beatGridTransition";
...
- * 없는 키와 같이 「—」다(`null초` 로 찍지 않는다). */
+ * 없는 키와 같이 「—」다(`null초` 로 찍지 않는다). 카드 t654 — 시안 tc 표기(소수 둘째,
+ * 뒤 0 제거)로 찍는다. 표시 전용이고 `fade_seconds` 는 그대로다. */
 export function fadeBeforeLabel(section: SongTimelineSection): string {
-  return section.fade_seconds != null ? `${section.fade_seconds}초` : "—";
+  return section.fade_seconds != null ? `${trimSeconds(section.fade_seconds)}초` : "—";
 }
```

기존 헬퍼 `trimSeconds`(`beatGridTransition.ts:20`, `seconds.toFixed(2).replace(/\.?0+$/, "")`)를 그대로 재사용했다. 새 함수를 만들지 않았다.

## 3. 기준선 귀속 (Baseline-attribution)

- 기준 `origin/main`: `3f67e525`. 명령 `git fetch origin main` 뒤 `git rev-parse --short origin/main` 으로 확인했다. 배차서의 기준과 같다.
- 워크트리 생성: `git worktree add -b WT-fade-before-label <repo>/.claude/worktrees/t654 origin/main` → `HEAD is now at 3f67e525 fix(t651): …(#689)`.
- 진입 후 확인: `git rev-parse --short HEAD` → `3f67e525`, `git branch --show-current` → `WT-fade-before-label`, `git status --short` → 빈 출력.
- 원격 중복 확인: `git rev-parse --verify -q origin/WT-fade-before-label` → 종료 코드 1(없음).
- 의존성: 이 워크트리에는 `ui/node_modules` 가 없어 `npm --prefix ui ci` 로 설치했다(`added 101 packages`).
- 위 §2 의 시험과 타입 검사는 모두 이 워크트리, 이 기준 커밋에서 실행한 결과다.

## 4. 미검증 (Gaps)

1. 송신 뒤 경로(서버 파서가 문장을 해석해 `CueFade` 명령을 만들고 콘솔에 쓰는 과정)는 추적하지 않았다. t653 판정 §4-4 와 같은 갭이다. 확인한 것은 「클라이언트가 보내는 문장에 `before` 가 없다」까지다.
2. 서버 쪽 `before` 필드(`server/director/validate/diagnostics.py:121`, `pipeline.py:299`, `server/web/session.py:6124–6125`, `exchange.schema.json:1602,1884`)의 의미를 읽지 않았다. 클라이언트 라벨과 다른 경로로 보이지만 확정은 아니다.
3. 실제 앱 화면은 보지 않았다. 시험은 `fadeBeforeLabel` 을 직접 호출하는 단위 시험이다(이 프로젝트에는 jsdom 이 없다).
4. `npm ci` 가 보고한 감사 경고(10건: moderate 4, high 4, critical 2)는 이 카드 범위 밖이라 `npm audit fix` 를 실행하지 않았다.
5. 경계값 `0`, `120`, `0.005` 는 시험하지 않았다. 규칙은 기존 `trimSeconds` 를 그대로 따른다.

## 5. 잔여 위험 (Residual-risk)

- 표기 규칙이 바뀌면 `3.16초` 단언도 같이 고쳐야 한다.
- 소수 둘째 자리로 반올림하므로 0.005 미만의 값은 `0초` 로 보인다. 저장값은 그대로다.
- `trimSeconds` 는 이 라벨 말고도 쓰인다: `BeatGridTimelineParts.tsx:151`, `BeatGridTransitionView.tsx:155`, `beatGridTransition.ts:30,88,303,307`. 이 함수를 바꾸면 그 화면들도 함께 바뀐다. 이번 변경은 그 함수를 건드리지 않았다.
- 화면 라벨만 바뀌므로 콘솔에 가는 값은 이 변경으로 바뀌지 않는다는 것이 §2-1 의 결론이다. 다만 송신 뒤 경로가 확인되기 전까지는 「콘솔 영향 없음」을 완전히 보증하지 않는다(§4-1).

## 6. 판정

- 이 문서는 증거만 적었다. 판정과 카드 닫기는 리드가 한다.
