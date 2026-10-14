# SPEC-LDBARMAP-003 — 수락 기준

모든 기준은 Given-When-Then 형식이며, 이진 판정(PASS/FAIL)이 가능하도록 값과 문구를 명시한다. 각 기준은 검증하는 REQ와 작성할 시험 파일을 적는다. 시험 파일 이름은 가칭이며 run-phase가 확정한다. 이 문서는 plan-phase 산출물이라 어떤 시험도 아직 돌리지 않았다.

> 공통 전제: 화면 시험은 기존 `ui/src/components/*.test.tsx`와 `ui/src/App.test.tsx`의 시험 틀을 따른다. 소켓은 가짜로 두고 보낸 프레임을 기록하며, 받은 프레임을 밀어 넣어 상태를 본다. 곡 파일명은 시험 안에서 가짜 이름 `sample-track.wav`만 쓴다. 실제 곡 파일을 저장소에 두지 않는다(REQ-LDBARUI-010 관련 검사).

## AC-LDBARUI-001 (REQ-LDBARUI-001) — 정상 요청은 한 번만 나간다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`(클릭), `ui/src/protocol.test.ts`(빌더)

**Given** 곡 오디오가 첨부돼 있고, 채팅 응답이 진행 중이 아니고, 연결이 열려 있고, 드롭다운에서 `2`를 고른 상태일 때
**When** 마디 지도 분석 버튼을 한 번 누르면
**Then** 보낸 프레임은 정확히 1개이고, 키 집합이 `v`, `type`, `first_beat_offset`뿐이며, 값이 `{"v":1,"type":"bar_map_analyse","first_beat_offset":2}`와 같다.
**And Given** `responding`이 참일 때 **Then** 분석 버튼이 비활성이고, 누를 수 없으며, 보낸 프레임은 0개다.

## AC-LDBARUI-002 (REQ-LDBARUI-002) — 빈 값으로 시작하고 기본값이 없다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 화면이 처음 그려졌을 때
**When** 아무것도 고르지 않으면
**Then** 드롭다운은 「선택」(빈 값)을 보이고, 분석 버튼은 비활성이며, 보낸 프레임은 0개다.

## AC-LDBARUI-003 (REQ-LDBARUI-003) — 선택지는 네 개이고, 박자표 사실은 범위를 바꾸지 않는다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 드롭다운을 열었을 때
**When** 선택지 목록을 읽으면
**Then** 값은 빈 값과 `0`, `1`, `2`, `3`뿐이다.
**And Given** 곡 타임라인 박자표가 `3/4`일 때 **When** 화면을 보면 **Then** 「이 분석기는 4/4 곡만 다룬다」가 보이고, 선택지는 여전히 `0`~`3`이다.
**And Given** 곡 타임라인 박자표가 `4/4`이거나 없을 때 **When** 화면을 보면 **Then** 「이 분석기는 4/4 곡만 다룬다」가 보이지 않는다.
**And Given** 빈 값을 고른 상태일 때 **Then** 분석 버튼이 비활성이다.

## AC-LDBARUI-004 (REQ-LDBARUI-004) — 대기의 수명

시험 파일: `ui/src/components/BarMapEntry.test.tsx`, `ui/src/App.test.tsx`

**Given** 분석 요청을 보낸 직후일 때
**When** 응답이 아직 없으면
**Then** 분석 버튼, 드롭다운, 기존 「분석」 버튼이 비활성이고, 「분석 중」과 「취소」가 보이며, 같은 요청을 다시 보내는 경로가 없다.
**And When** 「취소」를 누르면 **Then** 대기가 풀려 버튼이 다시 활성이고, 보낸 프레임은 추가로 0개다.
**And When** 결과 라벨 `chat_response` 또는 `error`(REQ-LDBARUI-007의 두 종류)가 도착하면 **Then** 대기가 끝난다.
**And When** 소켓이 끊기면 **Then** 대기가 끝나고 「결과를 받지 못했을 수 있습니다」가 보인다.
**And Given** 연결이 열려 있지 않을 때 **When** 분석 버튼을 누르면 **Then** 보낸 프레임은 0개이고 대기는 시작하지 않는다.

## AC-LDBARUI-005 (REQ-LDBARUI-005) — 저장 성공은 파일명과 함께 보인다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 곡 파일명이 `sample-track.wav`일 때
**When** `summary`가 `마디 지도 저장`인 `chat_response`가 도착하면
**Then** 저장 성공 문구가 보이고 `sample-track.wav`가 함께 보인다. 대기 상태가 이미 꺼져 있었어도 같은 결과가 보인다.
**And Given** 「취소」를 눌러 대기가 꺼진 뒤 **When** 같은 라벨(`마디 지도 저장` 또는 `마디 지도 분석 거절`)의 결과가 늦게 도착하면 **Then** 그 결과 문구가 보이고, 대기 표시는 다시 켜지지 않는다. 늦은 결과를 무시하지 않는다.

## AC-LDBARUI-006 (REQ-LDBARUI-006) — 거절 사유는 서버 문장 그대로 보인다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** `summary`가 `마디 지도 분석 거절`이고 `text`가 `시험용 사유 문장`인 `chat_response`가 도착하면
**Then** 화면에 `시험용 사유 문장`이 그대로 보이고, 클라이언트가 만든 다른 사유 문구는 보이지 않는다.

이 시험은 사유 문자열을 직접 단언한다. 「거절됐다」는 사실만 확인하고 끝내지 않는다.

## AC-LDBARUI-007 (REQ-LDBARUI-007) — 두 오류 종류는 정해진 문구로 끝낸다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** `kind`가 `song_audio_missing`인 `error` 프레임이 도착하면
**Then** 화면에 정확히 「곡 오디오를 먼저 첨부해 주세요.」가 보이고, 「분석 중」은 사라진다.
**And When** `kind`가 `protocol`인 `error` 프레임이 도착하면 **Then** 화면에 정확히 「분석 요청 형식이 맞지 않아 시작하지 못했습니다.」가 보이고, 「분석 중」은 사라진다.
**And When** `kind`가 그 둘이 아닌 `error` 프레임이 도착하면 **Then** 대기 상태와 화면 문구가 바뀌지 않는다.

## AC-LDBARUI-008 (REQ-LDBARUI-008) — busy 는 안내만 하고 대기는 유지한다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** `message`가 `처리 중`인 `busy` 프레임이 도착하면
**Then** 컨트롤 안에 `처리 중`이 보이고, 「분석 중」이 그대로 남고, 분석 버튼은 계속 비활성이다.

## AC-LDBARUI-009 (REQ-LDBARUI-009) — 빌더와 시험이 같이 들어간다

검사 명령: `git grep -n "bar_map_analyse" -- ui/src/protocol.ts ui/src/protocol.test.ts`

**Given** 변경이 끝난 뒤
**When** 위 검사 명령을 실행하면
**Then** 두 파일 모두에서 최소 한 줄이 나오고, `protocol.test.ts`의 시험이 통과한다.

## AC-LDBARUI-010 (REQ-LDBARUI-010) — 박 수 사본에는 출처가 적혀 있고 컴포넌트에는 숫자 4가 없다

검사 명령: `git grep -n "bar_map_entry.py" -- ui/src/protocol.ts` 와 `git grep -n -w "4" -- ui/src/components/BarMapEntry.tsx`

**Given** 구현이 끝난 뒤
**When** 첫 번째 검사를 실행하면 **Then** `BAR_MAP_BEATS_PER_BAR` 주석에 `server/audio/bar_map_entry.py`와 52행이 나온다.
**And When** 두 번째 검사를 실행하면 **Then** 출력이 없다(컴포넌트에 숫자 리터럴 4가 없다).

## AC-LDBARUI-011 (REQ-LDBARUI-011) — 두 분석 버튼은 섞이지 않는다

시험 파일: `ui/src/App.test.tsx`

**Given** 「분석」 버튼과 「마디 지도 분석」 버튼이 있을 때
**When** 「마디 지도 분석」을 누르면 **Then** 보낸 프레임은 `bar_map_analyse` 하나다.
**And When** 「분석」을 누르면 **Then** 보낸 프레임은 `song_audio_analyse` 하나이고 `bar_map_analyse`는 없다.

## AC-LDBARUI-012 (REQ-LDBARUI-012) — 콘솔에 아무것도 쓰거나 읽지 않는다

시험 파일: `ui/src/App.test.tsx`

**Given** 곡 오디오가 첨부되고 오프셋이 골라져 있을 때
**When** 「마디 지도 분석」을 누르고 응답을 받으면
**Then** 보낸 프레임 집합은 `{bar_map_analyse}` 한 개뿐이다. 콘솔 읽기와 쓰기 프레임은 없다.

## AC-LDBARUI-013 (REQ-LDBARUI-013) — 파일명 줄과 문구 줄이 블록 안에 있고 넘치지 않는다

시험 파일: `ui/src/App.test.tsx`

**Given** 곡 파일명이 `sample-track.wav`일 때
**When** 화면을 보면
**Then** `곡 «sample-track.wav» 첨부됨`이 진입 컨트롤과 같은 `composer-status` 블록 안에 있다.
**And Given** 파일명이 80자를 넘는 긴 문자열이고 거절 사유도 긴 문장일 때 **When** 화면을 보면 **Then** 대기·결과·안내 문구는 블록 안의 자기 요소에 있고, 컨트롤 요소가 블록의 가로 경계를 넘지 않는다(줄바꿈은 허용).

## AC-LDBARUI-014 (REQ-LDBARUI-014) — 상단 바·무대·폭 규칙은 바뀌지 않는다

검사 명령(기준점 B = `git merge-base origin/main HEAD`, 구현 시작 시점에 고정):
- `git diff --name-only B -- ui/src/components/BeatGridTopBar.tsx ui/src/components/BeatGridTopBar.test.tsx ui/src/components/BeatGridStage.tsx ui/src/components/beatGridStageModel.ts` — 출력이 없어야 한다.
- `git diff -U0 B -- ui/src/styles.css` — 원본 쪽 hunk 범위가 795~815행 안에 있어야 하고, 4386~4401행과 겹치지 않아야 한다.
- `git diff -U0 B -- ui/src/App.tsx` — 원본 쪽 hunk 범위가 23~47행(임포트), 404~429행(훅 구조분해), 1031~1042행(곡 첨부 상태 블록) 안에만 있어야 한다.
- `npm --prefix ui test -- BeatGridTopBar` — 폭 규칙을 지키는 기존 시험이 모두 통과해야 한다.

**Given** 구현이 끝난 뒤
**When** 위 네 검사를 실행하면
**Then** 네 검사가 모두 기준을 만족한다.

## AC-LDBARUI-015 (REQ-LDBARUI-015) — 채팅 기록 처리는 그대로다

시험 파일: `ui/src/protocol.test.ts`(기존 `reduceServerEvent` 시험에 한 줄 추가)

**Given** 마디 지도 결과 `chat_response`(`summary`가 `마디 지도 저장`)가 도착할 때
**When** `reduceServerEvent`에 넣으면
**Then** 채팅 기록 항목이 기존과 같은 모양으로 한 개 추가된다.
