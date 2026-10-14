# SPEC-LDBARMAP-003 — 수락 기준

모든 기준은 Given-When-Then 형식이며, 이진 판정(PASS/FAIL)이 가능하도록 값과 문구를 명시한다. 시험은 세 방식만 쓴다(spec.md §4): (a) 순수 리듀서 `barMapEntryState.ts`의 전이, (b) `renderToStaticMarkup`으로 본 `BarMapEntry`의 정적 HTML, (c) `readFileSync`로 읽은 소스와 CSS의 텍스트 검사. 이 문서는 plan-phase 산출물이라 어떤 시험도 아직 돌리지 않았다.

> 공통 전제: 시험 파일 이름은 가칭이며 run-phase가 확정한다. 곡 파일명은 시험 안에서 가짜 이름 `sample-track.wav`만 쓴다. 실제 곡 파일을 저장소에 두지 않는다.

## AC-LDBARUI-001 (REQ-LDBARUI-001) — 요청 문자열과 조건부 전송

시험 파일: `ui/src/protocol.test.ts`(빌더), `ui/src/components/BarMapEntry.test.tsx`(정적 HTML)

**Given** 빌더 `buildBarMapAnalyse(2)`일 때
**When** 결과 문자열을 파싱하면
**Then** 값이 `{"v":1,"type":"bar_map_analyse","first_beat_offset":2}`와 같고 키가 세 개뿐이다.
**And Given** `responding`이 참인 `BarMapEntry`일 때 **When** 정적 HTML을 보면 **Then** 마디 지도 분석 버튼에 `disabled` 속성이 있다.
**And** 검사: `grep -n "sendBarMapAnalyse" ui/src/App.tsx`의 출력은 정확히 두 줄이다. 한 줄은 훅 구조분해의 이름이고, 다른 한 줄은 「마디 지도 분석」 버튼의 `onClick` 안의 호출이다.

## AC-LDBARUI-002 (REQ-LDBARUI-002) — 빈 값으로 시작하고 기본값이 없다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`(정적 HTML)

**Given** 오프셋이 `null`인 상태로 그려진 `BarMapEntry`일 때
**When** 정적 HTML을 보면
**Then** 드롭다운의 선택된 옵션은 값이 빈 문자열인 「선택」이고, 마디 지도 분석 버튼에 `disabled`가 있다.

## AC-LDBARUI-003 (REQ-LDBARUI-003) — 선택지 네 개, 사실 문구는 범위를 바꾸지 않는다

시험 파일: `ui/src/components/barMapEntryState.test.ts`(`isOffMeter`), `ui/src/components/BarMapEntry.test.tsx`(정적 HTML)

**Given** 정적 HTML을 볼 때
**When** 드롭다운의 옵션 값을 읽으면
**Then** 빈 값을 뺀 옵션 값은 정확히 `0`, `1`, `2`, `3`이다.
**And Given** `isOffMeter`에 `"3/4"`를 넣으면 **Then** `true`다.
**And Given** `isOffMeter`에 `"4/4"`, `" 4 / 4 "`, `null`, `""`를 넣으면 **Then** 모두 `false`다.
**And Given** 사실 문구가 켜진 `BarMapEntry`일 때 **Then** 정적 HTML에 「이 분석기는 4/4 곡만 다룬다.」가 있고, 옵션 값은 여전히 `0`~`3`이다.

## AC-LDBARUI-004 (REQ-LDBARUI-004) — 대기 시작과 조건부 시작

시험 파일: `ui/src/components/barMapEntryState.test.ts`(전이), `ui/src/components/BarMapEntry.test.tsx`(정적 HTML)

**Given** 상태가 `idle`일 때
**When** 리듀서에 `sent` 이벤트를 넣으면
**Then** 상태가 `waiting`이 된다.
**And When** 리듀서에 `not-connected` 이벤트를 넣으면 **Then** 상태는 `idle`로 남고, 안내 줄이 정확히 「연결되어 있지 않아 분석을 시작하지 못했습니다.」다.
**And Given** 상태가 `waiting`인 `BarMapEntry`일 때 **When** 정적 HTML을 보면 **Then** 마디 지도 분석 버튼과 드롭다운에 `disabled`가 있고, 「분석 중」과 「취소」 글자가 있다.
**And** 검사: `grep -c "disabled={barMapWaiting}" ui/src/App.tsx`의 결과가 정확히 2다(「마디 지도 분석」 버튼과 기존 「분석」 버튼).

## AC-LDBARUI-005 (REQ-LDBARUI-005) — 대기는 결과, 오류, 끊김, 취소로만 끝나고 busy는 끝내지 않는다

시험 파일: `ui/src/components/barMapEntryState.test.ts`

**Given** 상태가 `waiting`일 때
**When** `cancel` 이벤트가 오면 **Then** 상태가 `idle`이고, 안내 줄이 정확히 「취소했습니다. 서버의 분석은 계속될 수 있으며, 끝나면 이 자리에 결과가 표시됩니다.」다.
**And When** `socket-closed` 이벤트가 오면 **Then** 상태가 `idle`이고, 안내 줄이 정확히 「연결이 끊겨 분석 결과를 받지 못했을 수 있습니다.」다.
**And When** `busy` 이벤트가 오면 **Then** 상태는 `waiting`으로 남는다(AC-LDBARUI-009).
**And Given** 상태가 `idle`일 때 **When** `cancel`이나 `socket-closed`가 오면 **Then** 상태와 안내 줄이 바뀌지 않는다.

## AC-LDBARUI-006 (REQ-LDBARUI-006) — 저장 성공은 고정 문구로 보이고 늦은 결과도 보인다

시험 파일: `ui/src/components/barMapEntryState.test.ts`

**Given** 파일명이 `sample-track.wav`인 상태에서 요청을 보내 `waiting`일 때
**When** `chat-response` 이벤트(`summary`가 `마디 지도 저장`)가 오면
**Then** 안내 줄이 정확히 「곡 «sample-track.wav» 마디 지도를 초안에 저장했습니다.」이고, 상태가 `idle`이다.
**And Given** 파일명이 없는 상태에서 **When** 같은 이벤트가 오면 **Then** 안내 줄이 정확히 「마디 지도를 초안에 저장했습니다.」다.
**And Given** `cancel`로 `idle`이 된 뒤 **When** 같은 이벤트가 늦게 오면 **Then** 안내 줄이 같은 문구로 바뀌고, 상태는 `idle`로 남는다.

## AC-LDBARUI-007 (REQ-LDBARUI-007) — 세 거절 라벨은 서버 사유를 그대로 보인다

시험 파일: `ui/src/components/barMapEntryState.test.ts`

**Given** 상태가 `waiting`일 때
**When** `summary`가 `마디 지도 분석 거절`, `마디 지도 저장 거절`, `마디 지도 저장 불가` 각각이고 `text`가 `시험용 사유 문장`인 `chat-response` 이벤트가 오면
**Then** 세 경우 모두 안내 줄이 정확히 `시험용 사유 문장`이고, 상태는 `idle`이다.
**And Given** `cancel`로 `idle`이 된 뒤 **When** 세 라벨 중 하나가 늦게 오면 **Then** 안내 줄이 같은 방식으로 바뀌고, 상태는 `idle`로 남는다.
**And When** `summary`가 `일반 답변`인 `chat-response`가 오면 **Then** 상태와 안내 줄이 바뀌지 않는다.

## AC-LDBARUI-008 (REQ-LDBARUI-008) — 두 오류 종류만 이 컨트롤의 문구로 끝낸다

시험 파일: `ui/src/components/barMapEntryState.test.ts`

**Given** 상태가 `waiting`일 때
**When** `error` 이벤트의 `kind`가 `song_audio_missing`이면 **Then** 안내 줄이 정확히 「곡 오디오를 먼저 첨부해 주세요.」이고, 상태는 `idle`이다.
**And When** `kind`가 `protocol`이면 **Then** 안내 줄이 정확히 「분석 요청 형식이 맞지 않아 시작하지 못했습니다.」이고, 상태는 `idle`이다.
**And When** `kind`가 `song_audio_missing`도 `protocol`도 아니면 **Then** 상태와 안내 줄이 바뀌지 않는다.
**And Given** 상태가 `idle`일 때 **When** `error` 이벤트(`kind`가 `song_audio_missing` 또는 `protocol`)가 오면 **Then** 상태와 안내 줄이 바뀌지 않는다.

## AC-LDBARUI-009 (REQ-LDBARUI-009) — 대기 중 busy는 안내만 하고 대기는 유지한다

시험 파일: `ui/src/components/barMapEntryState.test.ts`

**Given** 상태가 `waiting`일 때
**When** `busy` 이벤트(`message`가 `처리 중`)가 오면
**Then** 안내 줄이 정확히 `처리 중`이고, 상태는 `waiting`으로 남는다.
**And Given** 상태가 `idle`일 때 **When** 같은 `busy` 이벤트가 오면 **Then** 안내 줄과 상태가 바뀌지 않는다.

## AC-LDBARUI-010 (REQ-LDBARUI-010) — 빌더와 시험이 같은 변경에 있다

검사 명령(작업 트리에서 실행한다. `git grep`은 추적되지 않은 파일을 보지 못하므로 쓰지 않는다):
- `grep -n "bar_map_analyse" ui/src/protocol.ts ui/src/protocol.test.ts`

**Given** 변경이 끝난 뒤
**When** 위 검사 명령을 실행하면
**Then** 두 파일 모두에서 한 줄 이상 나온다. `protocol.test.ts`의 시험이 통과한다.

## AC-LDBARUI-011 (REQ-LDBARUI-011) — 박자표 사본에는 출처가 있고 컴포넌트에는 숫자 4가 없다

검사 명령(작업 트리에서 실행한다):
- `test -f ui/src/components/BarMapEntry.tsx && grep -n -w "4" ui/src/components/BarMapEntry.tsx` — 파일이 있어야 하고, `grep`의 출력이 없어야 한다(주석 포함).
- `grep -n "bar_map_entry.py" ui/src/protocol.ts` — 한 줄 이상 나오고, 그 줄이나 바로 아래 줄에 `52`가 있다.

**Given** 구현이 끝난 뒤
**When** 두 검사를 실행하면
**Then** 첫 검사는 파일 존재와 빈 출력을 보이고, 둘째 검사는 출처 줄을 보인다.

## AC-LDBARUI-012 (REQ-LDBARUI-012) — 두 분석 버튼은 섞이지 않고, 콘솔 프레임은 없다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`(정적 HTML), 검사 명령

**Given** 「마디 지도 분석」 버튼이 `BarMapEntry`에 있을 때
**When** 정적 HTML을 보면 **Then** 그 버튼의 글자는 정확히 「마디 지도 분석」이고, 「분석」 글자만 있는 버튼은 `BarMapEntry`에 없다.
**And** 검사: `grep -n "song_audio_analyse\|bar_map_analyse\|console" ui/src/components/BarMapEntry.tsx`의 결과에 `song_audio_analyse`가 없고, `console`이라는 식별자가 전송 코드에 없다(출력이 없어야 한다).

## AC-LDBARUI-013 (REQ-LDBARUI-013) — 파일명 줄과 문구 줄은 블록 안의 별도 요소이고, 묶음 CSS는 줄바꿈을 허용한다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`(정적 HTML, CSS 텍스트)

**Given** 파일명이 있는 상태에서 **When** `BarMapEntry`가 `waiting`이고 안내 줄이 있을 때 정적 HTML을 보면
**Then** 「분석 중」 문구와 안내 문구는 컨트롤 묶음(`composer-bar-map` 클래스)과 다른 요소에 들어 있다.
**And Given** `ui/src/styles.css`를 텍스트로 읽을 때 **When** `.composer-bar-map` 규칙 블록을 찾으면 **Then** 그 블록에 `flex-wrap: wrap`과 `max-width: 100%`가 모두 있다.
**And** 검사: `grep -n "<BarMapEntry" ui/src/App.tsx`의 줄 번호가 `songAudioName !== null` 블록의 시작 줄과 끝 줄 사이에 있다(블록은 1031~1042행 부근이고, 줄 번호는 기준점 B 기준의 참고값이다).
**And** 수동 확인(시험 아님): 1450, 1490, 1520, 1700px 폭에서 긴 파일명과 긴 거절 사유를 넣어 스크린샷을 찍고, 컨트롤이 블록 밖으로 나가지 않는지 본다.

## AC-LDBARUI-014 (REQ-LDBARUI-014) — 변경 파일과 변경 내용이 허용 범위 안에 있다

검사 명령(기준점 B = `git merge-base origin/main HEAD`. 구현을 시작할 때 고정하고, 모든 변경을 커밋한 뒤 실행한다):
- `git diff --name-only B` — 출력이 다음 목록의 부분집합이어야 한다: `ui/src/protocol.ts`, `ui/src/protocol.test.ts`, `ui/src/useCopilotSocket.ts`, `ui/src/App.tsx`, `ui/src/styles.css`, `ui/src/components/barMapEntryState.ts`, `ui/src/components/barMapEntryState.test.ts`, `ui/src/components/BarMapEntry.tsx`, `ui/src/components/BarMapEntry.test.tsx`, `.moai/specs/SPEC-LDBARMAP-003/` 아래 파일, `.moai/reports/t648/` 아래 파일(수동 확인 결과).
- `git diff -U0 B -- ui/src/styles.css` — 바뀐 줄 어디에도 `beat-grid-`가 없고 「카드 t630」이 없어야 한다.
- `git diff -U0 B -- ui/src/App.tsx` — 바뀐 줄 어디에도 `BeatGrid`, `beat-grid`, `beatGrid`가 없어야 한다. 바뀐 줄은 다음 세 곳 안에만 있어야 한다. (가) 임포트 블록의 `import` 줄들. (나) 훅 구조분해 블록(`const {`로 시작해 `} = useCopilotSocket(`로 끝나는 392~429행 부근)과 `songAudioName` 선언(446행 부근) 사이의 상태 선언. (다) `songAudioName !== null` 블록(1031~1042행 부근). 행 번호는 기준점 B 기준의 참고값이고, 판정은 식별자로 한다.
- `npm --prefix ui test -- BeatGridTopBar` — 폭 규칙을 지키는 기존 시험이 모두 통과해야 한다.

**Given** 구현이 끝난 뒤
**When** 네 검사를 실행하면
**Then** 네 검사가 모두 기준을 만족한다.

## AC-LDBARUI-015 (REQ-LDBARUI-015) — 결과 chat_response는 채팅 기록에 기존처럼 남는다

시험 파일: `ui/src/protocol.test.ts`(기존 `reduceServerEvent` 시험에 한 줄 추가)

**Given** 결과 `chat_response`(`summary`가 `마디 지도 저장`)가 도착할 때
**When** `reduceServerEvent`에 넣으면
**Then** 채팅 기록 항목이 기존과 같은 모양으로 한 개 추가된다.
