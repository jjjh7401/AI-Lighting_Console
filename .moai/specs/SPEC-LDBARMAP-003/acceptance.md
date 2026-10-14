# SPEC-LDBARMAP-003 — 수락 기준

모든 기준은 Given-When-Then 형식이며, 이진 판정(PASS/FAIL)이 가능하도록 값과 문구를 명시한다. 각 기준은 검증하는 REQ와 작성할 시험 파일을 적는다. 시험 파일 이름은 가칭이며 run-phase가 확정한다. 이 문서는 plan-phase 산출물이라 어떤 시험도 아직 돌리지 않았다.

> 공통 전제: 화면 시험은 기존 `ui/src/components/*.test.tsx`의 시험 틀을 따른다. 소켓은 가짜(fake)로 바꿔 보낸 프레임을 기록하고, 받은 프레임을 밀어 넣어 상태를 본다. 곡 파일은 시험 안에서 가짜 이름(`sample-track.wav`)만 쓰고, 실제 곡 파일을 저장소에 두지 않는다(REQ-LDBARUI-010).

## AC-LDBARUI-001 (REQ-LDBARUI-001) — 정상 요청은 한 번만 나간다

시험 파일: `ui/src/protocol.test.ts`(빌더), `ui/src/components/BarMapEntry.test.tsx`(클릭)

**Given** 곡 오디오가 첨부돼 있고, 응답 대기가 없고, 오프셋 칸에 `2`가 있을 때
**When** 분석 버튼을 한 번 누르면
**Then** 보낸 프레임은 정확히 1개이고, 그 JSON의 키 집합이 `v`, `type`, `first_beat_offset`뿐이며, 값이 `{"v":1,"type":"bar_map_analyse","first_beat_offset":2}`와 같다.

## AC-LDBARUI-002 (REQ-LDBARUI-002) — 기본값 없음

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 화면이 처음 그려졌을 때
**When** 아무것도 입력하지 않으면
**Then** 오프셋 칸은 빈 값이고, 분석 버튼은 비활성이며, 보낸 프레임은 0개다.

## AC-LDBARUI-003 (REQ-LDBARUI-003) — 범위 밖 값은 막는다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 곡 오디오가 첨부된 상태
**When** 오프셋 칸에 `-1`, `4`, `1.5`, 빈 값을 차례로 넣으면
**Then** 네 경우 모두 분석 버튼이 비활성이고 이유 한 줄이 보이며, 보낸 프레임은 0개다.
**And When** `0`, `1`, `2`, `3`을 차례로 넣으면 **Then** 네 경우 모두 분석 버튼이 활성이다.

## AC-LDBARUI-004 (REQ-LDBARUI-004) — 대기 표시

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 분석 요청을 보낸 직후
**When** 응답이 아직 도착하지 않았으면
**Then** 분석 버튼은 비활성이고 「분석 중」이 보이며, 같은 요청을 다시 보내는 경로가 없다.
**And When** 마디 지도 응답 또는 `error` 프레임이 도착하면 **Then** 「분석 중」 표시가 사라진다.

## AC-LDBARUI-005 (REQ-LDBARUI-005) — 저장 성공 표시

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중이고 곡 파일명이 `sample-track.wav`일 때
**When** `summary`가 `마디 지도 저장`인 `chat_response`가 도착하면
**Then** 저장 성공 표시가 보이고 `sample-track.wav`가 함께 보인다.

## AC-LDBARUI-006 (REQ-LDBARUI-006) — 거절 사유는 서버 문장 그대로

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** `summary`가 `마디 지도 분석 거절`이고 `text`가 `시험용 사유 문장`인 `chat_response`가 도착하면
**Then** 화면에 `시험용 사유 문장`이 그대로 보인다. 클라이언트가 만든 다른 사유 문구는 보이지 않는다.

이 시험은 사유 문자열을 직접 단언한다. 성공과 실패를 이분법으로 나눠 「거절됐다」만 확인하지 않는다.

## AC-LDBARUI-007 (REQ-LDBARUI-007) — 첨부 없음 안내

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 곡 오디오가 첨부돼 있지 않을 때
**When** 화면을 보면
**Then** 분석 버튼은 비활성이다.
**And Given** 대기 중일 때 **When** `kind`가 `song_audio_missing`인 `error` 프레임이 도착하면 **Then** 「곡 오디오를 먼저 첨부하세요」에 준하는 안내가 보이고, 대기 표시는 사라진다.

## AC-LDBARUI-008 (REQ-LDBARUI-008) — 사용 중 응답

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** 사용 중(busy) 응답이 도착하면
**Then** 대기 표시가 사라지고, 「사용 중」이라는 사실이 보이며, 조건이 맞으면 분석 버튼이 다시 활성이다.

## AC-LDBARUI-009 (REQ-LDBARUI-009) — 등록과 시험이 같이 들어간다

검사 명령: `grep -n "bar_map_analyse" ui/src/protocol.ts ui/src/protocol.test.ts`

**Given** 변경이 끝난 뒤
**When** 위 검사 명령을 실행하면
**Then** 두 파일 모두에서 최소 한 줄이 나온다. 그리고 `protocol.test.ts`의 시험이 통과한다.

## AC-LDBARUI-010 (REQ-LDBARUI-010) — 기본값과 곡 고유값을 박지 않는다

검사: `ui/src/components/BarMapEntry.tsx`에서 오프셋 상태의 초기값을 읽는다.

**Given** 구현이 끝난 뒤
**When** 오프셋 상태의 초기값을 보면
**Then** 빈 값(빈 문자열 또는 `null`)이다. 숫자 리터럴, 곡 제목, BPM 리터럴이 초기값이나 상수로 들어 있지 않다.

## AC-LDBARUI-011 (REQ-LDBARUI-011) — 두 흐름은 섞이지 않는다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 두 버튼(마디 지도 분석, 곡 분석)이 있을 때
**When** 마디 지도 분석 버튼을 누르면 **Then** 보낸 프레임은 `bar_map_analyse` 하나다.
**And When** 곡 분석 버튼을 누르면 **Then** 보낸 프레임은 `song_audio_analyse` 하나이고 `bar_map_analyse`는 없다.

## AC-LDBARUI-012 (REQ-LDBARUI-012) — 콘솔에 아무것도 쓰지 않는다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 곡 오디오가 첨부되고 오프셋이 유효할 때
**When** 분석 버튼을 누르고 응답을 받으면
**Then** 보낸 프레임 집합은 `{bar_map_analyse}` 한 개뿐이다. 콘솔 쓰기나 읽기 프레임은 없다.

## AC-LDBARUI-013 (REQ-LDBARUI-013) — 파일명은 컨트롤 곁에 보인다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 곡 파일명이 `sample-track.wav`일 때
**When** 화면을 보면
**Then** `sample-track.wav`가 분석 컨트롤과 같은 영역 안에 보인다.

## AC-LDBARUI-014 (REQ-LDBARUI-014) — 화면 자리 (감독 결정 대기)

이 기준은 D4 결정 전까지 확정할 수 없다. 결정이 나면 다음과 같이 고친다.

**Given** 감독이 (가), (나), (다) 중 하나를 정했을 때
**When** 화면을 보면
**Then** 분석 컨트롤은 그 자리에만 있다. 다른 두 자리에는 같은 컨트롤이 없다.
