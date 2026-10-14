---
id: SPEC-LDBARMAP-003
title: "마디 지도 진입 화면 — 첫 박 오프셋 입력과 분석 요청 UI"
version: "0.1.1"
status: draft
created: 2026-10-14
updated: 2026-10-14
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "ui/src/protocol.ts, ui/src/protocol.test.ts, ui/src/useCopilotSocket.ts, ui/src/App.tsx, ui/src/components/BarMapEntry.tsx, ui/src/styles.css"
lifecycle: spec-anchored
tags: "bar-map, entry-screen, ui, protocol, draft-timeline"
tier: M
related_specs: [SPEC-LDBARMAP-002, SPEC-LDBEAT-001]
depends_on: [SPEC-LDBARMAP-002]
---

# SPEC-LDBARMAP-003 — 마디 지도 진입 화면: 첫 박 오프셋 입력과 분석 요청

## HISTORY

| 일자 | 버전 | 내용 |
|---|---|---|
| 2026-10-14 | 0.1.0 | 최초 작성(카드 t648, 브랜치 `WT-barmap-entry-ui`). 화면 자리(D4)는 감독 결정 대기로 남겼다. |
| 2026-10-14 | 0.1.1 | D4 결정 반영 — 「나」: 곡 첨부 상태 줄 곁(§4). 감독 결정이며 리드 세션의 AskUserQuestion을 거쳐 전달받았다. 기준을 `origin/main` `dca7fa43`(#694 병합, SPEC-LDBARMAP-002 completed)으로 옮겼다. `server/web/PROTOCOL.md` 26행이 보강돼 범위 밖 오프셋은 거절 응답, 사용 중은 `busy`, 형식 오류는 `error` `protocol`로 고정됐다. 그 행을 기준으로 REQ를 고쳤다. 오프셋 입력은 빈 값으로 시작하는 네 선택지 드롭다운으로 바꿨다. `depends_on`을 채웠다(선행 SPEC이 completed가 됐다). |

## 1. 배경

- SPEC-LDBARMAP-002가 서버 쪽 입구를 만들었고, sync까지 끝나 completed다(#694, `dca7fa43`). 클라이언트 메시지 `bar_map_analyse`(첫 박 오프셋을 필수 정수로 싣는다)는 `server/web/PROTOCOL.md` 26행에 있다.
- 클라이언트에는 아직 이 요청을 만드는 함수도, 화면 컨트롤도 없다. `ui/src`에 마디 지도 코드가 없다.
- 같은 SPEC §8은 분석 버튼, 첫 박 오프셋 입력 칸, 진행 표시, 결과 표시를 이 후속 UI 카드의 일로 넘겼다.

## 2. 범위

포함:
- 요청 빌더 `buildBarMapAnalyse(firstBeatOffset)`와 그 시험(`ui/src/protocol.ts`, `ui/src/protocol.test.ts`). 클라이언트 등록은 빌더와 시험이 맡는다. `buildSongAudioAnalyse`와 같은 방식이다.
- 전송 함수와 응답 상태(`ui/src/useCopilotSocket.ts`). 누른 행동을 화면 기록에 남긴다.
- 컨트롤 컴포넌트 `BarMapEntry`: 첫 박 오프셋 드롭다운, 「마디 지도 분석」 버튼, 대기 표시, 결과 표시.
- 컨트롤을 곡 첨부 상태 줄 곁에 배치한다(`ui/src/App.tsx`의 입력창 영역, `ui/src/styles.css`의 입력창 규칙).

제외:
- 상단 바, 무대 배치, 1490/1520px 폭 규칙(REQ-LDBARUI-015).
- 귀로 첫 박을 정하는 재생 화면(SPEC-LDBARMAP-002 §8).
- 4/4 밖의 박자표(D2), 서버 코드, 분석기, 저장 스키마. 서버는 바꾸지 않는다.
- 콘솔 읽기와 쓰기, `SongTimelineLibrary` 저장.
- 기존 「분석」 버튼과 BPM 확정 흐름(`song_audio_analyse`).

## 3. 요구사항 (EARS)

- REQ-LDBARUI-001 [HARD] **When** 곡 오디오가 첨부돼 있고, 채팅 응답이 진행 중이 아니고(`responding`이 거짓), 드롭다운에서 0~3 중 하나를 골랐는데, 사용자가 마디 지도 분석 버튼을 누르면, 클라이언트 **shall** `{"v": 1, "type": "bar_map_analyse", "first_beat_offset": <정수>}`를 정확히 한 번 보낸다.
- REQ-LDBARUI-002 [HARD] 첫 박 오프셋 드롭다운은 **shall** 「선택」이라는 빈 값으로 시작한다. 0~3 중 하나를 기본값으로 미리 고르지 **shall not** 한다. 서버 계약에 기본값이 없기 때문이다(`server/web/PROTOCOL.md` 26행, "required int, no default").
- REQ-LDBARUI-003 드롭다운의 선택지는 **shall** 0, 1, 2, 3 네 개뿐이다(4/4 기준, D2). 빈 값이면 분석 버튼을 **shall** 비활성으로 둔다. 범위 판정의 최종 권한은 서버에 있다. 범위 밖 값이 서버에 닿으면 그 답은 거절 응답(REQ-LDBARUI-006)으로 온다.
- REQ-LDBARUI-004 **While** 분석 요청이 대기 중인 동안, 클라이언트 **shall** 분석 버튼과 드롭다운을 비활성으로 두고 「분석 중」 상태를 보인다. 대기는 REQ-LDBARUI-005부터 009까지 중 하나로 끝난다.
- REQ-LDBARUI-005 **When** `chat_response`의 `summary`가 `마디 지도 저장`이면, 클라이언트 **shall** 저장 성공을 보이고 곡 파일명을 함께 보인다. 결과 판별은 대기 상태와 무관하게 `summary` 라벨로 한다.
- REQ-LDBARUI-006 **When** `chat_response`의 `summary`가 `마디 지도 분석 거절`이면, 클라이언트 **shall** 사유를 `text`에서 읽어 그대로 보인다. 사유 문장을 클라이언트가 지어내지 **shall not** 한다. 범위 밖 오프셋과 분석 실패도 이 경로로 온다.
- REQ-LDBARUI-007 **When** `error` 프레임의 `kind`가 `song_audio_missing`이면, 클라이언트 **shall** 곡 오디오를 먼저 첨부하라는 안내를 보이고 대기를 끝낸다.
- REQ-LDBARUI-008 **When** `busy` 프레임이 오면, 클라이언트 **shall** 대기를 끝내고 프레임의 `message`를 보인다. 다른 작업이 돌고 있다는 뜻으로 읽는다.
- REQ-LDBARUI-009 **When** `error` 프레임의 `kind`가 `protocol`이면, 클라이언트 **shall** 요청 형식 오류라는 일반 안내를 보이고 대기를 끝낸다. 이 경우는 클라이언트 검사가 막았어야 할 일이라서, 나타나면 결함으로 본다.
- REQ-LDBARUI-010 [HARD] `bar_map_analyse`의 클라이언트 빌더와 그 시험은 **shall** 같은 변경에 들어간다(`ui/src/protocol.test.ts` 93~96행의 주석, SPEC-LDBARMAP-002 Gaps 9번).
- REQ-LDBARUI-011 [HARD] 구현은 곡 고유값(곡 제목, BPM 리터럴, 오프셋 기본값)을 상수로 박지 **shall not** 한다. SPEC-LDBARMAP-002 REQ-LDBARENTRY-016과 같은 원칙이다.
- REQ-LDBARUI-012 [HARD] 분석 요청은 기존 「분석」 버튼 및 BPM 확정 흐름(`song_audio_analyse`)과 **shall not** 섞인다. 두 버튼은 이름과 보내는 프레임이 다르다.
- REQ-LDBARUI-013 [HARD] 진입 컨트롤은 **shall not** 콘솔을 읽거나 쓴다.
- REQ-LDBARUI-014 곡 파일명 표시(`곡 «…» 첨부됨`)는 진입 컨트롤과 같은 줄에 **shall** 남는다. 첨부된 곡을 사람이 확인할 수 있게 하기 위해서다(SPEC-LDBARMAP-002 Gaps 8번, E3).
- REQ-LDBARUI-015 [HARD] 진입 컨트롤은 **shall** 곡 첨부 상태 줄 곁에 놓인다(§4 결정 「나」). 상단 바(`ui/src/components/BeatGridTopBar.tsx`), 무대 배치, 1490/1520px 폭 규칙(`ui/src/styles.css`의 「카드 t630」 블록, 4279~4400행, 그리고 `ui/src/components/BeatGridTopBar.test.tsx` 157~162행)은 **shall not** 바뀐다.
- REQ-LDBARUI-016 채팅 기록에 남는 `chat_response`는 기존 처리 그대로 **shall** 남는다. 이 SPEC은 채팅 기록 처리를 바꾸지 않는다.

## 4. 설계 결정

### D4 — 진입 컨트롤의 화면 자리: 「나」 (감독 결정, 2026-10-14)

- 결정: 곡 첨부 상태 줄 곁에 첫 박 오프셋 드롭다운과 「마디 지도 분석」 버튼을 둔다.
- 결정 경위: 감독의 결정이다. 리드 세션의 AskUserQuestion을 거쳐 2026-10-14에 전달받았다.
- 결정 조건(감독이 함께 정한 것): 상단 바와 무대 배치는 그대로 둔다. 1490/1520px 폭 규칙도 건드리지 않는다.
- 위치의 실제 모습: 입력창(composer) 영역의 곡 첨부 상태 줄 `곡 «파일명» 첨부됨 [분석]`(`ui/src/App.tsx`의 `songAudioName` 블록, 1031~1042행)에서, 기존 「분석」 버튼 옆에 새 컨트롤을 더한다.
- 확인한 사실: 상단 바의 `accept="audio/*"` 입력(`BeatGridTopBar.tsx` 249행)은 재생용 음원 입력이라 곡 첨부와 다르다. 곡 첨부 상태는 입력창의 줄이다.
- 이름 구분: 기존 「분석」 버튼은 BPM 확정 흐름(`song_audio_analyse`)이다. 새 버튼은 「마디 지도 분석」으로 이름을 달리해 혼동을 막는다.

### 응답 식별과 상태

- 요청에 번호가 없다. 결과는 `summary` 고정 라벨(`마디 지도 저장`, `마디 지도 분석 거절`)로 판별한다. 대기는 `busy`와 `error`로도 끝난다.
- 대기 표시는 잘못 끝날 수 있다. 예를 들어 다른 요청 때문에 생긴 `busy`를 우리 요청의 것으로 읽을 수 있다. 그래도 결과 표시는 틀리지 않는다. 결과는 라벨이 정하기 때문이다. 틀릴 수 있는 것은 「분석 중」 표시뿐이다.
- 버튼은 채팅 응답이 진행 중일 때(`responding`) 비활성이다. 이 값은 `useCopilotSocket`이 이미 노출하고 있다.

### 오프셋 입력: 드롭다운

- 네 선택지 드롭다운을 택한 이유: 서버 계약이 정수 0~3만 받는다. 드롭다운은 범위 밖 값을 클라이언트에서 만들 수 없게 하고, 자유 입력 칸보다 단순하다. 이것은 구현 세부 선택이다. 바꾸려면 REQ-LDBARUI-003만 고치면 된다.

### 화면 기록과 채팅 기록

- 분석 요청은 화면 기록에 한 줄로 남긴다. 예: 「마디 지도 분석 요청 (첫 박 오프셋 2)」. `sendSongAudioAnalyse`가 `dispatch`로 남기는 방식을 따른다.
- 채팅 기록에는 `chat_response`가 기존처럼 남는다(REQ-LDBARUI-016).

## 5. 의존과 선결 조건

- `depends_on: [SPEC-LDBARMAP-002]`. 이 SPEC은 `status: completed`이므로(`origin/main` `dca7fa43`) 선결 점검을 통과한다. 0.1.0에서는 draft 상태라 비웠었다.

## 6. Gaps — 확인하지 않은 것

1. 대기 표시가 우리 요청의 응답인지 다른 요청의 `busy`인지는 프로토콜로 가를 수 없다(요청 번호가 없다). §4의 대응으로 결과 표시는 틀리지 않게 했지만, 대기 표시 오류는 run-phase 시험으로 실측한다.
2. 「마디 지도 분석」 요청을 기존 BPM 분석(`song_audio_analyse`)이 도는 중에 보내면 서버가 어떻게 답하는지는 서버 가드를 읽었을 뿐 재지 않았다.
3. 실제 곡의 분석 시간과 브라우저 실기 동작은 재지 않았다.
4. 한국어 안내 문구와 「첫 박 오프셋」 라벨의 최종 표현은 run-phase에서 정한다.
5. 「t639」라는 표기는 리드의 전달문에만 있다. 커밋 이력과 코드 어디에도 없다. 1490/1520px 폭 규칙의 코드 주석은 「카드 t630」이다. 이 SPEC은 규칙의 위치(파일과 행)로 가리킨다.
