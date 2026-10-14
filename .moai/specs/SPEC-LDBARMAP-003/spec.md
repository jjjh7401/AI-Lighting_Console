---
id: SPEC-LDBARMAP-003
title: "마디 지도 진입 화면 — 첫 박 오프셋 입력과 분석 요청 UI"
version: "0.1.2"
status: draft
created: 2026-10-14
updated: 2026-10-14
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "ui/src/protocol.ts, ui/src/protocol.test.ts, ui/src/useCopilotSocket.ts, ui/src/App.tsx, ui/src/App.test.tsx, ui/src/components/BarMapEntry.tsx, ui/src/styles.css"
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
| 2026-10-14 | 0.1.1 | D4 결정 「나」 반영(리드 세션 AskUserQuestion 경유). 기준을 `origin/main`으로 옮겼고, `server/web/PROTOCOL.md` 26행 보강을 반영했다. 오프셋은 빈 값으로 시작하는 드롭다운으로 했다. |
| 2026-10-14 | 0.1.2 | plan-audit 1차 FAIL(0.68, 기준 0.80) 반영. 대기의 수명을 다시 정했다: `busy`는 대기를 끝내지 않고, 대기는 요청 자신의 응답·끊김·「취소」로만 끝난다. 입력창은 막지 않고 「분석」 버튼만 막는다. 감독 결정(2026-10-14)으로 「취소」 버튼을 넣었고, 취소 뒤 늦은 결과는 표시한다. 요구사항을 15개로 줄여 Tier M 상한 안에 두었다. Out of Scope 소제목, 문구 고정, 확인 범위(App.tsx 임포트·구조분해·입력창), 기준점(`merge-base`), `.gitignore` 재포함 규칙(`git add -f` 불필요)을 고쳤다. |

## 1. 배경

- SPEC-LDBARMAP-002가 서버 쪽 입구를 만들었고, sync까지 끝나 completed다(#694, `dca7fa43`). 클라이언트 메시지 `bar_map_analyse`(첫 박 오프셋을 필수 정수로 싣는다)는 `server/web/PROTOCOL.md` 26행에 있다.
- 클라이언트에는 아직 이 요청을 만드는 함수도, 화면 컨트롤도 없다. `ui/src`에 마디 지도 코드가 없다.
- 같은 SPEC §8은 분석 버튼, 첫 박 오프셋 입력 칸, 진행 표시, 결과 표시를 이 후속 UI 카드의 일로 넘겼다.

## 2. 범위

### 포함

- 요청 빌더 `buildBarMapAnalyse(firstBeatOffset)`와 그 시험(`ui/src/protocol.ts`, `ui/src/protocol.test.ts`). 클라이언트 등록은 빌더와 시험이 맡는다. `buildSongAudioAnalyse`와 같은 방식이다.
- 전송 함수와 대기 상태(`ui/src/useCopilotSocket.ts`). 누른 행동을 화면 기록에 남긴다.
- 컨트롤 컴포넌트 `BarMapEntry`: 첫 박 오프셋 드롭다운, 「마디 지도 분석」 버튼, 「분석 중」 표시와 「취소」 버튼, 결과와 안내 문구.
- 컨트롤을 곡 첨부 상태 블록 곁에 배치한다(`ui/src/App.tsx`의 입력창 영역, `ui/src/styles.css`의 입력창 규칙).

### 2.1 Out of Scope — 상단 바·무대·폭 규칙

- 상단 바(`ui/src/components/BeatGridTopBar.tsx`), 무대(`ui/src/components/BeatGridStage.tsx`), 1490/1520px 폭 규칙. REQ-LDBARUI-014가 동결한다.

### 2.2 Out of Scope — 재생 화면과 분석기

- 귀로 첫 박을 정하는 재생 화면(SPEC-LDBARMAP-002 §8).
- 4/4 밖의 박자표(D2), 서버 코드, 분석기, 저장 스키마. 서버는 바꾸지 않는다.

### 2.3 Out of Scope — 콘솔과 라이브러리

- 콘솔 읽기와 쓰기, `SongTimelineLibrary` 저장(SPEC-LDBARMAP-002 §8).

### 2.4 Out of Scope — 기존 BPM 확정 흐름

- 기존 「분석」 버튼과 BPM 확정 흐름(`song_audio_analyse`). 이 SPEC은 그 버튼의 동작을 바꾸지 않는다. 대기 중에는 그 버튼을 잠시 비활성으로 둘 뿐이다(REQ-LDBARUI-004).

### 2.5 Out of Scope — 서버 박자표 사본의 자동 동기화

- 서버가 4/4를 풀면(`server/audio/bar_map_entry.py` 52행 `_TIME_SIGNATURE`) 이 UI의 박 수 사본도 같이 바꿔야 한다. 이 SPEC은 그 연동을 자동으로 하지 않는다(REQ-LDBARUI-010).

## 3. 요구사항 (EARS)

- REQ-LDBARUI-001 [HARD] **When** 곡 오디오가 첨부돼 있고, 채팅 응답이 진행 중이 아니고(`responding`이 거짓), 연결이 열려 있고, 드롭다운에서 오프셋을 골랐는데, 사용자가 마디 지도 분석 버튼을 누르면, 클라이언트 **shall** `{"v": 1, "type": "bar_map_analyse", "first_beat_offset": <정수>}`를 정확히 한 번 보낸다.
- REQ-LDBARUI-002 [HARD] 첫 박 오프셋 드롭다운은 **shall** 「선택」이라는 빈 값으로 시작한다. 오프셋을 기본값으로 미리 고르지 **shall not** 한다. 서버 계약에 기본값이 없기 때문이다(`server/web/PROTOCOL.md` 26행, "required int, no default").
- REQ-LDBARUI-003 드롭다운의 선택지는 **shall** 0부터 (`BAR_MAP_BEATS_PER_BAR` − 1)까지다. 4/4 기준으로 0, 1, 2, 3 네 개다(REQ-LDBARUI-010). 빈 값이면 분석 버튼을 **shall** 비활성으로 둔다. 곡 타임라인의 박자표가 「4/4」가 아닌 것으로 알려져 있으면, 컨트롤 곁에 「이 분석기는 4/4 곡만 다룬다」를 **shall** 보이고, 선택지 범위는 바꾸지 **shall not** 한다. 박자표 정보가 없거나 4/4면 그 문구를 보이지 않는다. 범위를 곡 타임라인의 박자표에서 계산하지 **shall not** 한다.
- REQ-LDBARUI-004 [HARD] 요청을 보내면 **shall** 「분석 중」 대기 상태가 된다. 대기 중에는 마디 지도 분석 버튼, 드롭다운, 기존 「분석」 버튼을 **shall** 비활성으로 두고 「취소」 버튼을 보인다. 대기는 다음 중 하나로만 끝난다: REQ-LDBARUI-005·006의 결과 라벨, REQ-LDBARUI-007의 오류, 소켓 끊김(끊김 안내를 함께 보인다), 사용자의 「취소」. 「취소」는 화면의 대기만 푼다. 서버의 분석을 멈추지 않는다. 연결이 열려 있지 않으면 요청을 보내지 **shall not** 하고, 대기도 시작하지 **shall not** 한다.
- REQ-LDBARUI-005 [HARD] **When** `chat_response`의 `summary`가 `마디 지도 저장`이면, 클라이언트 **shall** 저장 성공 문구와 곡 파일명을 보인다. 이 판별은 대기 상태와 무관하게 `summary` 라벨로 한다.
- REQ-LDBARUI-006 [HARD] **When** `chat_response`의 `summary`가 `마디 지도 분석 거절`이면, 클라이언트 **shall** 사유를 `text` 그대로 보인다. 사유 문장을 클라이언트가 지어내지 **shall not** 한다. 범위 밖 오프셋과 분석 실패도 이 경로로 온다.
- REQ-LDBARUI-007 [HARD] **When** `error` 프레임의 `kind`가 `song_audio_missing`이면 「곡 오디오를 먼저 첨부해 주세요.」를, `kind`가 `protocol`이면 「분석 요청 형식이 맞지 않아 시작하지 못했습니다.」를 **shall** 보이고, 두 경우 모두 대기를 끝낸다. 다른 `kind`는 이 컨트롤과 무관하므로 무시한다.
- REQ-LDBARUI-008 [HARD] **When** 대기 중 `busy` 프레임이 오면, 클라이언트 **shall** 프레임의 `message`를 컨트롤 안에 안내로 보이되, 대기는 **shall not** 끝낸다. `busy`는 요청 번호가 없어서 이 요청의 거절인지 다른 요청(예: 채팅)의 거절인지 가를 수 없다(§4).
- REQ-LDBARUI-009 [HARD] `bar_map_analyse`의 클라이언트 빌더와 그 시험은 **shall** 같은 변경에 들어간다(`ui/src/protocol.test.ts` 93~96행의 주석, SPEC-LDBARMAP-002 Gaps 9번).
- REQ-LDBARUI-010 [HARD] 박 수 상수 `BAR_MAP_BEATS_PER_BAR`는 서버 값의 사본이다. 상수의 주석에 `server/audio/bar_map_entry.py` 52행(`_TIME_SIGNATURE = (4, 4)`)을 **shall** 적는다. 컴포넌트 안에 숫자 리터럴 4를 두지 **shall not** 한다. 「4/4」 표시 문구와 선택지는 이 상수에서 만든다. 곡 제목과 BPM 수치도 상수로 두지 **shall not** 한다.
- REQ-LDBARUI-011 [HARD] 기존 「분석」(`song_audio_analyse`)과 새 「마디 지도 분석」은 이름과 보내는 프레임이 다르고, 서로 섞이지 **shall not** 한다.
- REQ-LDBARUI-012 [HARD] 진입 컨트롤은 콘솔을 읽거나 쓰지 **shall not** 한다. 이 컨트롤이 보내는 프레임은 `bar_map_analyse` 하나뿐이다.
- REQ-LDBARUI-013 곡 파일명 표시(`곡 «…» 첨부됨`)는 진입 컨트롤과 같은 상태 블록(`composer-status`) 안에 **shall** 남는다. 대기·결과·안내 문구는 그 블록 안의 자기 줄(별도 요소)에 보인다. 긴 파일명이나 긴 거절 사유에서도 컨트롤이 블록 밖으로 넘치지 **shall not** 한다. 줄바꿈은 허용한다.
- REQ-LDBARUI-014 [HARD] 진입 컨트롤은 **shall** 곡 첨부 상태 블록 곁에 놓인다(D4 「나」). §2.1의 상단 바, 무대, 1490/1520px 폭 규칙(`ui/src/styles.css` 4386~4401행과 그 시험)은 **shall not** 바뀐다.
- REQ-LDBARUI-015 [HARD] 결과 `chat_response`는 기존 리듀서 처리 그대로 채팅 기록에 **shall** 남는다. 이 SPEC은 채팅 기록 처리를 바꾸지 **shall not** 한다.

## 4. 설계 결정

### D4 — 진입 컨트롤의 화면 자리: 「나」 (감독 결정, 2026-10-14)

- 결정: 곡 첨부 상태 블록 곁에 첫 박 오프셋 드롭다운과 「마디 지도 분석」 버튼을 둔다.
- 경위: 감독의 결정이다. 리드 세션의 AskUserQuestion을 거쳐 2026-10-14에 전달받았다.
- 결정 조건: 상단 바와 무대 배치는 그대로 둔다. 1490/1520px 폭 규칙도 건드리지 않는다.
- 위치: 입력창(composer)의 곡 첨부 상태 블록 `곡 «파일명» 첨부됨 [분석]`(`ui/src/App.tsx` 1031~1042행)에서, 기존 「분석」 버튼 옆에 새 컨트롤을 더한다.
- 확인한 사실: 상단 바의 `accept="audio/*"` 입력(`ui/src/components/BeatGridTopBar.tsx` 249행)은 재생용 음원 입력이라 곡 첨부와 다르다.

### 대기의 수명과 `busy` (2026-10-14 코드 확인)

- 프로토콜에 요청 번호가 없다. `busy`는 `message`만 있는 프레임이다(`server/web/messages.py` 1192행).
- 한 연결의 작업 칸은 하나(`current_task`)다. 채팅(`server/web/app.py` 586~588행), 분석(830~832행, 856~858행), 곡 업로드 끝(797~799행)이 모두 같은 칸을 보고, 같은 `_BUSY_MESSAGE`(99행)로 `busy`를 보낸다.
- 그러므로 분석 중에 들어온 채팅이 받는 `busy`와 우리 요청의 거절 `busy`는 내용과 순서로 가를 수 없다.
- 상태 요청(`status_request`, 1091~1092행)은 가드 밖이라 순서로 나눠 볼 수 있다. 그러나 앞에 다른 가드 요청이 없다는 것을 화면이 보장할 수 없으므로 쓰지 않는다.
- 큐 모니터 요청(`cue_monitor_request`, 1031~1090행)은 `busy`를 받지 않고 합쳐서 처리한다. 5초 폴링은 대기를 깨지 않는다.
- 그래서: `busy`는 대기를 끝내지 않고 안내만 보인다(REQ-LDBARUI-008). 대기는 결과·오류·끊김·「취소」로 끝난다(REQ-LDBARUI-004). 대가는 두 가지다. 거절된 요청은 「취소」로 풀어야 하고, 「취소」 버튼이 하나 늘어난다.
- 기각한 대안: `busy`로 바로 대기를 푼다. 그러면 분석 중 채팅이 대기 표시를 일찍 끈다. 결과 표시는 라벨이 정하므로 데이터 오류는 없지만, 대기 표시가 실제 분석과 어긋난다.
- **결정 기록(2026-10-14, 감독 결정 — 리드 세션 AskUserQuestion 경유)**: 「취소」 버튼을 넣는다. `busy`는 안내만 보이고 대기는 끝나지 않는다. 대기는 결과·오류·끊김·「취소」로만 끝난다. 「취소」는 화면의 대기 표시만 끄고, 서버의 분석은 멈추지 않는다.
- **취소 뒤 늦게 온 결과: 표시한다**(REQ-LDBARUI-005, AC-LDBARUI-005). 한 연결에서 분석은 하나만 돌므로(`server/web/app.py` 856~858행의 작업 칸), 늦은 결과는 가장 최근에 받아들여진 분석의 결과다. 무시하면 이미 초안 타임라인에 저장된 마디 지도가 화면에 나타나지 않는다.

### 응답 식별

- 결과는 `summary` 고정 라벨(`마디 지도 저장`, `마디 지도 분석 거절`)로 판별한다. 이 판별은 대기 상태와 무관하다(REQ-LDBARUI-005·006).

### 박 수 사본과 박자표

- 박 수 상수는 `server/audio/bar_map_entry.py` 52행 `_TIME_SIGNATURE = (4, 4)`의 사본이다.
- 곡 타임라인 박자표를 읽는 `parseBeatsPerBar`(`ui/src/components/beatGridTransition.ts` 34행)는 쓰지 않는다. 서버 검사는 분석기의 고정 4/4를 쓰기 때문이다(`server/web/session.py` 9478행 `analyse_bar_map`).
- 곡 타임라인 박자표가 4/4가 아니어도 서버는 거절하지 않는다. 진입 경로는 타임라인 박자표를 읽지 않고, 곡 열쇠는 `(song_title, sequence_number)`뿐이다(`session.py` 10358행). 그래서 화면은 범위를 바꾸지 않고 사실 문구만 보인다(REQ-LDBARUI-003).

### 오프셋 입력: 드롭다운

- 네 선택지 드롭다운을 택한 이유: 서버 계약은 정수 0~3만 받는다. 드롭다운은 범위 밖 값을 화면에서 만들 수 없게 하고, 자유 입력 칸보다 단순하다. 구현 세부 선택이다.

### 화면 기록과 채팅 기록

- 분석 요청은 화면 기록에 한 줄로 남긴다. 예: 「마디 지도 분석 요청 (첫 박 오프셋 2)」. `sendSongAudioAnalyse`가 `dispatch`로 남기는 방식을 따른다.
- 결과 `chat_response`는 채팅 기록에도 기존처럼 남는다(REQ-LDBARUI-015).

## 5. 의존과 선결 조건

- `depends_on: [SPEC-LDBARMAP-002]`. 선행 SPEC은 `status: completed`다(2026-10-14 확인, `origin/main`).

## 6. Gaps — 확인하지 않은 것

1. 「취소」 뒤에도 서버의 분석은 계속될 수 있다. 서버에는 분석을 멈추는 요청이 없으므로 확인할 수 없다. 화면은 「취소해도 분석은 계속될 수 있다」고 적는다. 결과는 라벨로 계속 보인다.
2. 연결이 끊긴 뒤 결과가 어느 세션으로 가는지는 읽지 않았다. 화면은 「결과를 받지 못했을 수 있다」고만 안내한다.
3. 「분석 중」 동안 채팅 `busy`가 실제로 얼마나 오는지는 재지 않았다(run-phase 실측 항목).
4. 실제 곡의 분석 시간과 브라우저 실기 동작은 재지 않았다.
5. t639: 리드 확인에 따르면 폭 규칙의 승인을 SPEC에 적는 기록 카드다. 그 승인은 PR #695(병합 커밋 `b8ac5719`, 기록 커밋 `ca43cbec`)로 `origin/main`에 들어와 있다(2026-10-14 확인). 폭 규칙의 구현 카드는 t630이다(`ui/src/styles.css` 4386행 주석).
6. 채팅 기록의 `busy` 항목과 컨트롤 안의 `busy` 안내가 함께 보이는 중복은 허용한다(REQ-LDBARUI-015).
7. E3: 표시되는 곡 파일명은 첨부 시점의 값이다. 타임라인 곡과 같은지는 확인하지 않는다(SPEC-LDBARMAP-002 Gaps 8번).
8. 한국어 문구의 최종 표현은 run-phase에서 다듬을 수 있다. 다만 REQ-LDBARUI-005부터 008까지의 문구를 바꾸려면 SPEC 개정이 필요하다.
