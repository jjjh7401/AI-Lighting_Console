# SPEC-LDBARMAP-003 — 수락 기준

모든 기준은 Given-When-Then 형식이며, 이진 판정(PASS/FAIL)이 가능하도록 값과 문구를 명시한다. 각 기준은 검증하는 REQ와 작성할 시험 파일을 적는다. 시험 파일 이름은 가칭이며 run-phase가 확정한다. 이 문서는 plan-phase 산출물이라 어떤 시험도 아직 돌리지 않았다.

> 공통 전제: 화면 시험은 기존 `ui/src/components/*.test.tsx`의 시험 틀을 따른다. 소켓은 가짜로 두고 보낸 프레임을 기록하며, 받은 프레임을 밀어 넣어 상태를 본다. 곡 파일명은 시험 안에서 가짜 이름 `sample-track.wav`만 쓴다. 실제 곡 파일을 저장소에 두지 않는다(REQ-LDBARUI-011).

## AC-LDBARUI-001 (REQ-LDBARUI-001) — 정상 요청은 한 번만 나간다

시험 파일: `ui/src/protocol.test.ts`(빌더), `ui/src/components/BarMapEntry.test.tsx`(클릭)

**Given** 곡 오디오가 첨부돼 있고, 채팅 응답이 진행 중이 아니고, 드롭다운에서 `2`를 고른 상태일 때
**When** 마디 지도 분석 버튼을 한 번 누르면
**Then** 보낸 프레임은 정확히 1개이고, 키 집합이 `v`, `type`, `first_beat_offset`뿐이며, 값이 `{"v":1,"type":"bar_map_analyse","first_beat_offset":2}`와 같다.

## AC-LDBARUI-002 (REQ-LDBARUI-002) — 빈 값으로 시작하고 기본값이 없다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 화면이 처음 그려졌을 때
**When** 아무것도 고르지 않으면
**Then** 드롭다운은 「선택」(빈 값)을 보이고, 분석 버튼은 비활성이며, 보낸 프레임은 0개다.

## AC-LDBARUI-003 (REQ-LDBARUI-003) — 선택지는 0~3 네 개뿐이다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 드롭다운을 열었을 때
**When** 선택지 목록을 읽으면
**Then** 값은 빈 값과 `0`, `1`, `2`, `3`뿐이다.
**And Given** 빈 값을 고른 상태일 때 **When** 화면을 보면 **Then** 분석 버튼이 비활성이다.

## AC-LDBARUI-004 (REQ-LDBARUI-004) — 대기 중에는 막고, 「분석 중」을 보인다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 분석 요청을 보낸 직후일 때
**When** 응답이 아직 없으면
**Then** 분석 버튼과 드롭다운이 비활성이고 「분석 중」이 보이며, 같은 요청을 다시 보내는 경로가 없다.

## AC-LDBARUI-005 (REQ-LDBARUI-005) — 저장 성공을 파일명과 함께 보인다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 곡 파일명이 `sample-track.wav`일 때
**When** `summary`가 `마디 지도 저장`인 `chat_response`가 도착하면
**Then** 저장 성공 표시가 보이고 `sample-track.wav`가 함께 보인다. 대기 상태가 꺼져 있어도 같은 결과가 보인다(결과 판별은 라벨로 한다).

## AC-LDBARUI-006 (REQ-LDBARUI-006) — 거절 사유는 서버 문장 그대로 보인다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** `summary`가 `마디 지도 분석 거절`이고 `text`가 `시험용 사유 문장`인 `chat_response`가 도착하면
**Then** 화면에 `시험용 사유 문장`이 그대로 보이고, 클라이언트가 만든 다른 사유 문구는 보이지 않는다.

이 시험은 사유 문자열을 직접 단언한다. 「거절됐다」는 사실만 확인하고 끝내지 않는다.

## AC-LDBARUI-007 (REQ-LDBARUI-007) — 곡이 없다는 오류는 안내하고 대기를 끝낸다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** `kind`가 `song_audio_missing`인 `error` 프레임이 도착하면
**Then** 「곡 오디오를 먼저 첨부하세요」에 준하는 안내가 보이고, 「분석 중」 표시는 사라진다.

## AC-LDBARUI-008 (REQ-LDBARUI-008) — 사용 중 응답은 서버 문구를 보이고 대기를 끝낸다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** `message`가 `처리 중`인 `busy` 프레임이 도착하면
**Then** 「분석 중」 표시가 사라지고, `처리 중`이 보이며, 조건이 맞으면 분석 버튼이 다시 활성이다.

## AC-LDBARUI-009 (REQ-LDBARUI-009) — 형식 오류는 일반 안내로 끝낸다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 대기 중일 때
**When** `kind`가 `protocol`인 `error` 프레임이 도착하면
**Then** 요청 형식 오류라는 일반 안내가 보이고, 「분석 중」 표시는 사라진다.

## AC-LDBARUI-010 (REQ-LDBARUI-010) — 빌더와 시험이 같이 들어간다

검사 명령: `git grep -n "bar_map_analyse" -- ui/src/protocol.ts ui/src/protocol.test.ts`

**Given** 변경이 끝난 뒤
**When** 위 검사 명령을 실행하면
**Then** 두 파일 모두에서 최소 한 줄이 나오고, `protocol.test.ts`의 시험이 통과한다.

## AC-LDBARUI-011 (REQ-LDBARUI-011) — 곡 고유값을 박지 않는다

검사: `ui/src/components/BarMapEntry.tsx` 리뷰 검사와 AC-LDBARUI-002의 초기값 검사.

**Given** 구현이 끝난 뒤
**When** 컴포넌트 소스를 읽으면
**Then** 오프셋 초기값은 빈 값이다. 숫자 리터럴은 선택지 0~3뿐이다. 곡 제목과 BPM 수치 리터럴이 없다.

## AC-LDBARUI-012 (REQ-LDBARUI-012) — 두 분석 버튼은 섞이지 않는다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 「분석」 버튼과 「마디 지도 분석」 버튼이 같은 줄에 있을 때
**When** 「마디 지도 분석」을 누르면 **Then** 보낸 프레임은 `bar_map_analyse` 하나다.
**And When** 「분석」을 누르면 **Then** 보낸 프레임은 `song_audio_analyse` 하나이고 `bar_map_analyse`는 없다.

## AC-LDBARUI-013 (REQ-LDBARUI-013) — 콘솔에 아무것도 쓰거나 읽지 않는다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`

**Given** 곡 오디오가 첨부되고 드롭다운에서 오프셋을 골라 둔 상태일 때
**When** 「마디 지도 분석」을 누르고 응답을 받으면
**Then** 보낸 프레임 집합은 `{bar_map_analyse}` 한 개뿐이다. 콘솔 읽기와 쓰기 프레임은 없다.

## AC-LDBARUI-014 (REQ-LDBARUI-014) — 파일명은 컨트롤과 같은 줄에 보인다

시험 파일: `ui/src/components/BarMapEntry.test.tsx`(또는 `App` 배선 시험)

**Given** 곡 파일명이 `sample-track.wav`일 때
**When** 화면을 보면
**Then** `곡 «sample-track.wav» 첨부됨`이 진입 컨트롤과 같은 상태 줄(`composer-status`) 안에 있다.

## AC-LDBARUI-015 (REQ-LDBARUI-015) — 상단 바, 무대 배치, 폭 규칙은 바뀌지 않는다

검사 명령(모두 `git diff` 기반 검사):
- `git diff --name-only origin/main -- ui/src/components/BeatGridTopBar.tsx ui/src/components/BeatGridTopBar.test.tsx` — 출력이 없어야 한다.
- `git diff -U0 origin/main -- ui/src/styles.css` — hunk 헤더의 원본 범위(`-a,b`)가 4279~4400행과 겹치지 않아야 한다.
- `git diff -U0 origin/main -- ui/src/App.tsx` — hunk가 입력창 곡 첨부 상태 줄 블록(1028~1045행 근처) 안에만 있어야 한다.

**Given** 구현이 끝난 뒤
**When** 위 세 검사를 실행하면
**Then** 세 검사가 모두 기준을 만족한다.

## AC-LDBARUI-016 (REQ-LDBARUI-016) — 채팅 기록 처리는 그대로다

시험 파일: `ui/src/protocol.test.ts`(기존 `reduceServerEvent` 시험에 한 줄 추가)

**Given** 마디 지도 결과 `chat_response`(`summary`가 `마디 지도 저장`)가 도착할 때
**When** `reduceServerEvent`에 넣으면
**Then** 채팅 기록 항목이 기존과 같은 모양으로 한 개 추가된다.
