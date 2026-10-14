---
id: SPEC-LDBARMAP-003
title: "마디 지도 진입 화면 — 첫 박 오프셋 입력과 분석 요청 UI"
version: "0.1.3"
status: draft
created: 2026-10-14
updated: 2026-10-14
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "ui/src/protocol.ts, ui/src/protocol.test.ts, ui/src/useCopilotSocket.ts, ui/src/App.tsx, ui/src/components/barMapEntryState.ts, ui/src/components/barMapEntryState.test.ts, ui/src/components/BarMapEntry.tsx, ui/src/components/BarMapEntry.test.tsx, ui/src/styles.css"
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
| 2026-10-14 | 0.1.1 | D4 결정 「나」 반영(리드 세션 AskUserQuestion 경유). `server/web/PROTOCOL.md` 26행 보강을 반영했다. 오프셋은 빈 값으로 시작하는 드롭다운으로 했다. |
| 2026-10-14 | 0.1.2 | plan-audit 1차 FAIL(0.68, 기준 0.80) 반영. 감독 결정으로 「취소」 버튼을 넣었다. `busy`는 안내만 보이고 대기는 끝나지 않는다. 대기는 결과·오류·끊김·취소로만 끝난다. 입력창은 막지 않고 「분석」 버튼만 막는다. |
| 2026-10-14 | 0.1.3 | plan-audit 2차 FAIL(0.77) 반영. (1) 프로젝트에 DOM 시험 환경이 없으므로 시험을 순수 리듀서, 정적 HTML, 소스·CSS 텍스트 검사로 바꿨다. (2) 박자표 사본을 분자와 분모 전체로 하고, 「4/4」 문구와 선택지를 상수에서 만든다. (3) 결과 라벨 집합을 서버 코드 기준으로 고쳤다. 저장 관문의 거절 라벨 두 개를 더했다. (4) 저장 성공 문구와 모든 안내 문구를 고정했다. (5) 취소 뒤 늦은 결과는 표시하고, 결과 줄에는 오프셋을 적지 않는다. (6) 변경 파일 허용 목록과 내용 검사로 AC-014를 다시 썼다. |
| 2026-10-14 | 0.1.4 | 3차 재검수 PASS(0.85, 감사 대상 `a74093e7`) 뒤에 반영. 리드 요청으로 PROTOCOL 문서 항목(구 Gaps 6번)을 뺐고, 결과 라벨 네 개를 문구 고정표에 넣었다. 검수관 권고(D1·D2·D3·D5·D6)와 선택 소견(D4·D7~D11)을 반영했다. |

## 1. 배경

- SPEC-LDBARMAP-002가 서버 쪽 입구를 만들었고, sync까지 끝나 completed다(#694, `dca7fa43`). 클라이언트 메시지 `bar_map_analyse`(첫 박 오프셋을 필수 정수로 싣는다)는 `server/web/PROTOCOL.md` 26행에 있다.
- 클라이언트에는 아직 이 요청을 만드는 함수도, 화면 컨트롤도 없다. `ui/src`에 마디 지도 코드가 없다.
- 같은 SPEC §8은 분석 버튼, 첫 박 오프셋 입력 칸, 진행 표시, 결과 표시를 이 후속 UI 카드의 일로 넘겼다.

## 2. 범위

### 포함

- 요청 빌더 `buildBarMapAnalyse(firstBeatOffset)`와 박자표 사본 상수(`ui/src/protocol.ts`), 그 시험(`ui/src/protocol.test.ts`).
- 순수 상태 리듀서(`ui/src/components/barMapEntryState.ts`)와 그 시험. 대기, 결과, 오류, 취소, 끊김의 전이는 모두 여기에 둔다.
- 컨트롤 컴포넌트 `BarMapEntry`(props만 받는다)와 그 시험(`ui/src/components/BarMapEntry.test.tsx`).
- 전송 함수와 수신 알림 옵션(`ui/src/useCopilotSocket.ts`).
- 배선과 상태 줄(`ui/src/App.tsx`), 입력창 스타일(`ui/src/styles.css`).

### 2.1 Out of Scope — 상단 바·무대·폭 규칙

- 상단 바(`ui/src/components/BeatGridTopBar.tsx`), 무대(`ui/src/components/BeatGridStage.tsx`), 1490/1520px 폭 규칙. REQ-LDBARUI-014가 동결한다.

### 2.2 Out of Scope — 재생 화면과 분석기

- 귀로 첫 박을 정하는 재생 화면(SPEC-LDBARMAP-002 §8).
- 4/4 밖의 박자표(D2), 서버 코드, 분석기, 저장 스키마. 서버는 바꾸지 않는다.

### 2.3 Out of Scope — 콘솔과 라이브러리

- 콘솔 읽기와 쓰기, `SongTimelineLibrary` 저장(SPEC-LDBARMAP-002 §8).

### 2.4 Out of Scope — 기존 BPM 확정 흐름

- 기존 「분석」 버튼과 BPM 확정 흐름(`song_audio_analyse`)의 동작은 바꾸지 않는다. 대기 중에는 그 버튼을 잠시 비활성으로 둘 뿐이다(REQ-LDBARUI-004).

### 2.5 Out of Scope — 서버 박자표 사본의 자동 동기화

- 서버가 박자표를 바꾸면(`server/audio/bar_map_entry.py` 52행) 이 UI의 사본(`BAR_MAP_TIME_SIGNATURE`)도 같이 바꿔야 한다. 이 SPEC은 그 연동을 자동으로 하지 않는다(REQ-LDBARUI-011).

### 2.6 Out of Scope — 브라우저 클릭과 실제 넘침

- DOM이 없는 시험 환경에서는 클릭 동작과 실제 넘침을 자동으로 재지 않는다. 수동 확인 항목으로 남긴다(plan.md §4).

## 3. 요구사항 (EARS)

- REQ-LDBARUI-001 [HARD] **When** 곡 오디오가 첨부돼 있고, 채팅 응답이 진행 중이 아니고(`responding`이 거짓), 연결이 열려 있고, 첫 박 오프셋을 골랐을 때 마디 지도 분석 버튼을 누르면, 클라이언트 **shall** `{"v": 1, "type": "bar_map_analyse", "first_beat_offset": <정수>}`를 정확히 한 번 보낸다.
- REQ-LDBARUI-002 [HARD] 첫 박 오프셋 드롭다운은 **shall** 「선택」이라는 빈 값으로 시작한다. 기본값을 미리 고르지 **shall not** 한다. 서버 계약에 기본값이 없다(`server/web/PROTOCOL.md` 26행, "required int, no default").
- REQ-LDBARUI-003 드롭다운의 선택지는 **shall** `BAR_MAP_BEATS_PER_BAR`에서 만든 0부터 (그 값 − 1)까지다. 곡 타임라인의 `time_signature` 문자열(`ui/src/protocol.ts` 840행)이 있고, 공백을 뺀 값이 `BAR_MAP_METER_LABEL`과 다르면, 컨트롤 곁에 「이 분석기는 4/4 곡만 다룬다.」를 **shall** 보인다. 이때 선택지 범위는 바꾸지 **shall not** 한다. 박자표가 없거나 같으면 클라이언트 **shall** 이 문구를 보이지 않게 한다. 범위를 곡 박자표에서 계산하지 **shall not** 한다. 빈 값이면 클라이언트 **shall** 분석 버튼을 비활성으로 둔다.
- REQ-LDBARUI-004 [HARD] **When** 요청을 보낼 수 있는 상태에서 분석 버튼이 눌리면, 클라이언트 **shall** 「분석 중」 대기 상태로 들어가고, 마디 지도 분석 버튼, 드롭다운, 기존 「분석」 버튼을 비활성으로 두며, 「취소」 버튼을 보인다. 연결이 열려 있지 않으면 요청을 보내지 **shall not** 하고 대기도 시작하지 **shall not** 한다. 그때는 「연결되어 있지 않아 분석을 시작하지 못했습니다.」를 보인다.
- REQ-LDBARUI-005 [HARD] **While** 대기 중일 때, 클라이언트 **shall** 대기를 다음 중 하나로만 끝낸다: 결과 라벨(REQ-LDBARUI-006, 007), 오류 종류(REQ-LDBARUI-008), 소켓 끊김, 사용자의 「취소」. 소켓이 끊기면 「연결이 끊겨 분석 결과를 받지 못했을 수 있습니다.」를, 「취소」를 누르면 「취소했습니다. 서버의 분석은 계속될 수 있으며, 끝나면 이 자리에 결과가 표시됩니다.」를 보인다. 「취소」는 화면의 대기만 끄고, 서버의 분석을 멈추지 **shall not** 한다. `busy`(REQ-LDBARUI-009)는 대기를 끝내지 **shall not** 한다.
- REQ-LDBARUI-006 [HARD] **When** `chat_response`의 `summary`가 `마디 지도 저장`이면, 클라이언트 **shall** 「곡 «파일명» 마디 지도를 초안에 저장했습니다.」를 보인다. 파일명이 없으면 「마디 지도를 초안에 저장했습니다.」를 보인다. 이 결과는 대기 중이든 「취소」 뒤든 같은 문구로 보이고, 늦은 결과를 무시하지 **shall not** 한다. 대기 중이었다면 대기를 끝낸다.
- REQ-LDBARUI-007 [HARD] **When** `chat_response`의 `summary`가 `마디 지도 분석 거절`, `마디 지도 저장 거절`, `마디 지도 저장 불가` 중 하나이면, 클라이언트 **shall** 그 `text`를 그대로 보인다. 사유 문장을 클라이언트가 지어내지 **shall not** 한다. 대기 중이었다면 대기를 끝내고, 「취소」 뒤에 도착했다면 같은 방식으로 보인다(REQ-LDBARUI-006과 같은 늦은 결과 규칙).
- REQ-LDBARUI-008 [HARD] **When** `error` 프레임의 `kind`가 `song_audio_missing`이면 「곡 오디오를 먼저 첨부해 주세요.」를, `kind`가 `protocol`이면 「분석 요청 형식이 맞지 않아 시작하지 못했습니다.」를 **shall** 보이고 대기를 끝낸다. 그 밖의 `kind`는 이 컨트롤과 무관하므로 **shall** 무시한다. 대기 중이 아닐 때는 `error` 프레임이 와도 이 컨트롤의 상태와 안내를 **shall not** 바꾼다.
- REQ-LDBARUI-009 [HARD] **While** 대기 중일 때 `busy` 프레임이 오면, 클라이언트 **shall** 프레임의 `message`를 컨트롤 안에 안내로 보이고, 대기는 **shall not** 끝낸다. 대기 중이 아니면 `busy`는 이 컨트롤의 상태를 바꾸지 **shall not** 한다. `busy`에는 요청 번호가 없어서, 이 요청의 거절인지 다른 요청(예: 채팅)의 거절인지 가를 수 없다(§4).
- REQ-LDBARUI-010 [HARD] `bar_map_analyse`의 클라이언트 빌더와 그 시험은 **shall** 같은 변경에 들어간다(`ui/src/protocol.test.ts` 93~96행의 주석, SPEC-LDBARMAP-002 Gaps 9번).
- REQ-LDBARUI-011 [HARD] 클라이언트 **shall** 박자표 사본 `BAR_MAP_TIME_SIGNATURE`(`[4, 4]`, 분자와 분모 모두)를 서버 값의 사본으로 둔다. 상수 주석에 `server/audio/bar_map_entry.py` 52행을 **shall** 적는다. 「4/4」 표시 문구, 선택지, 대기 문구의 숫자는 이 상수에서 만든다. `ui/src/components/BarMapEntry.tsx`에는 숫자 토큰 4가 **shall not** 나타난다(주석 포함). 곡 제목과 BPM 수치도 상수로 두지 **shall not** 한다.
- REQ-LDBARUI-012 [HARD] 「마디 지도 분석」과 기존 「분석」(`song_audio_analyse`)은 이름과 보내는 프레임이 다르고, 섞이지 **shall not** 한다. 「마디 지도 분석」 버튼이 보내는 프레임은 `bar_map_analyse` 하나뿐이며, 콘솔을 읽거나 쓰지 **shall not** 한다.
- REQ-LDBARUI-013 곡 파일명 표시(`곡 «…» 첨부됨`)는 진입 컨트롤과 같은 `composer-status` 블록 안에 **shall** 남는다. 「분석 중」, 결과, 안내 문구는 그 블록 안의 별도 요소(자기 줄)에 보인다. 컨트롤 묶음(클래스 `composer-bar-map`)은 `flex-wrap: wrap`과 `max-width: 100%`를 **shall** 가진다(CSS 텍스트 검사). 긴 파일명과 긴 거절 사유에서 넘치지 않는지는 수동 확인 항목이다(§2.6).
- REQ-LDBARUI-014 [HARD] 진입 컨트롤은 **shall** 곡 첨부 상태 블록 곁에 놓인다(D4 「나」). 상단 바(`ui/src/components/BeatGridTopBar.tsx`), 무대(`ui/src/components/BeatGridStage.tsx`), 1490/1520px 폭 규칙(`ui/src/styles.css`의 「카드 t630」 블록과 `.beat-grid-` 규칙)은 **shall not** 바뀐다.
- REQ-LDBARUI-015 [HARD] 결과 `chat_response`는 기존 리듀서 처리 그대로 채팅 기록에 **shall** 남는다. 이 SPEC은 채팅 기록 처리를 바꾸지 **shall not** 한다.

## 4. 설계 결정

### 시험 방식 (DOM 없음)

- 이 프로젝트에는 DOM 시험 환경이 없다(`ui/package.json`의 devDependencies에 jsdom과 testing-library가 없다. `ui/src/App.test.tsx` 머리말).
- 그래서 시험은 세 가지만 쓴다. (a) 순수 함수: 상태 전이와 판별(`barMapEntryState.ts`). (b) `renderToStaticMarkup`: 컴포넌트의 정적 HTML(기존 `ui/src/components/BeatGrid.test.tsx` 선례). (c) 소스와 CSS 텍스트 검사: `readFileSync`(기존 `ui/src/attachmentCopy.test.ts` 선례).
- 클릭과 실제 소켓 동작은 자동 시험하지 않는다. 수동 확인 항목으로 둔다(plan.md §4).

### D4 — 진입 컨트롤의 화면 자리: 「나」 (감독 결정, 2026-10-14)

- 결정: 곡 첨부 상태 블록 곁에 첫 박 오프셋 드롭다운과 「마디 지도 분석」 버튼을 둔다.
- 경위: 감독의 결정이다. 리드 세션의 AskUserQuestion을 거쳐 2026-10-14에 전달받았다.
- 결정 조건: 상단 바와 무대 배치는 그대로 둔다. 1490/1520px 폭 규칙도 건드리지 않는다.
- 위치: 입력창(composer)의 곡 첨부 상태 블록 `곡 «파일명» 첨부됨 [분석]`(`ui/src/App.tsx` 1031~1042행)에서, 기존 「분석」 버튼 옆에 새 컨트롤을 더한다.
- 확인한 사실: 상단 바의 `accept="audio/*"` 입력(`ui/src/components/BeatGridTopBar.tsx` 249행)은 재생용 음원 입력이라 곡 첨부와 다르다.

### 대기의 수명과 busy

- 결정 기록(2026-10-14, 감독 결정 — 리드 세션 AskUserQuestion 경유): 「취소」 버튼을 넣는다. `busy`는 안내만 보이고 대기는 끝나지 않는다. 대기는 결과·오류·끊김·「취소」로만 끝난다. 「취소」는 화면의 대기만 끈다.
- 근거(2026-10-14 코드 확인): `busy`는 `message`만 있는 프레임이다(`server/web/messages.py` 1192행). 한 연결의 작업 칸은 하나(`current_task`)이고, 채팅(`server/web/app.py` 586~588행), 분석(830~832행, 856~858행), 곡 업로드 끝(797~799행)이 모두 같은 칸을 보며 같은 `_BUSY_MESSAGE`(99행)로 `busy`를 보낸다. 그래서 `busy`의 내용이나 순서로 보낸 쪽을 가를 수 없다.
- 상태 요청(`status_request`, 1091~1092행)은 가드 밖이라 순서로 나눠 볼 수 있다. 그러나 앞에 다른 가드 요청이 없다는 것을 화면이 보장할 수 없어서 쓰지 않는다. 큐 모니터 요청(`cue_monitor_request`, 1031~1090행)은 `busy`를 받지 않고 합쳐서 처리하므로, 5초 폴링(`ui/src/useCopilotSocket.ts` 149행, `CUE_MONITOR_POLL_INTERVAL_MS = 5_000`)은 대기를 깨지 않는다.
- 기각한 대안: `busy`로 바로 대기를 푼다. 그러면 분석 중 채팅이 대기 표시를 일찍 끈다. 결과 표시는 라벨이 정하므로 데이터 오류는 없지만, 대기 표시가 실제 분석과 어긋난다.

### 늦은 결과

- 취소 뒤 늦게 온 결과는 표시한다(REQ-LDBARUI-006, 007). 무시하면 이미 초안 타임라인에 저장된 마디 지도가 화면에 나타나지 않는다.
- 한 연결에서 분석은 하나만 돈다(`server/web/app.py` 856~858행의 작업 칸). 그러므로 늦은 결과는 가장 최근에 받아들여진 분석의 결과다.
- 결과 줄에는 오프셋을 적지 않는다. 요청한 오프셋은 요청 시점의 화면 기록(「마디 지도 분석 요청 (첫 박 오프셋 N)」)에 남는다(Gaps 2번).

### 결과 라벨 집합 (서버 코드 기준)

- 성공 라벨: `마디 지도 저장`. 저장 관문이 성공하면 보낸다(`server/web/session.py` 9421행 이후).
- 거절 라벨 세 개:
  - `마디 지도 분석 거절`: 범위 밖 오프셋(`session.py` 9531~9534행), 분석 단계의 거절과 실패, 분석 중 곡 교체 거절(9508~9523행, 9559~9562행).
  - `마디 지도 저장 거절`: 저장 검사 거절(`session.py` 9441~9449행).
  - `마디 지도 저장 불가`: 초안 타임라인이 없음(`session.py` 9433~9439행).
- 저장 관문의 거절 이벤트는 그대로 나간다(`session.py` 9569~9572행).

### 박자표 사본과 사실 문구

- `BAR_MAP_TIME_SIGNATURE = [4, 4]`는 `server/audio/bar_map_entry.py` 52행 `_TIME_SIGNATURE = (4, 4)`의 사본이다. `BAR_MAP_BEATS_PER_BAR`는 그 분자, `BAR_MAP_METER_LABEL`은 `분자/분모` 문자열이다.
- 곡 타임라인 박자표를 읽는 `parseBeatsPerBar`(`ui/src/components/beatGridTransition.ts` 34행)는 쓰지 않는다.
- 서버 검사는 분석기의 고정 4/4를 쓴다(`server/web/session.py` 9478행 `analyse_bar_map`). 곡 타임라인 박자표가 4/4가 아니어도 서버는 거절하지 않는다. 진입 경로는 타임라인 박자표를 읽지 않고, 곡 열쇠는 `(song_title, sequence_number)`뿐이다(`session.py` 10358행).
- 사실 문구는 `isOffMeter(timelineMeter)`로 가린다. 공백을 뺀 값이 있고 `BAR_MAP_METER_LABEL`과 다를 때만 참이다.

### 문구 고정표

| 용도 | 문구 |
|---|---|
| 저장 성공(파일명 있음) | 곡 «{파일명}» 마디 지도를 초안에 저장했습니다. |
| 저장 성공(파일명 없음) | 마디 지도를 초안에 저장했습니다. |
| 첨부 없음 오류 | 곡 오디오를 먼저 첨부해 주세요. |
| 형식 오류 | 분석 요청 형식이 맞지 않아 시작하지 못했습니다. |
| 연결 없음 | 연결되어 있지 않아 분석을 시작하지 못했습니다. |
| 끊김 | 연결이 끊겨 분석 결과를 받지 못했을 수 있습니다. |
| 취소 | 취소했습니다. 서버의 분석은 계속될 수 있으며, 끝나면 이 자리에 결과가 표시됩니다. |
| 사실 | 이 분석기는 {BAR_MAP_METER_LABEL} 곡만 다룬다. |
| 버튼 | 마디 지도 분석 |
| 드롭다운 이름과 빈 값 | 첫 박 오프셋 / 선택 |
| 대기 표시와 취소 | 분석 중 / 취소 |

### 결과 라벨 네 개

| 서버 라벨(`summary`) | 뜻 | 화면에 보이는 것 |
|---|---|---|
| `마디 지도 저장` | 저장 성공 | 저장 성공 문구 두 개 중 파일명 유무에 따른 하나(§4 문구 고정표) |
| `마디 지도 분석 거절` | 범위 밖 오프셋, 분석 실패와 거절 | 서버 `text` 그대로 |
| `마디 지도 저장 불가` | 초안 타임라인 없음 | 서버 `text` 그대로 |
| `마디 지도 저장 거절` | 저장 검사(`validate_bar_map`) 실패 | 서버 `text` 그대로 |

### 화면 기록과 채팅 기록

- 분석 요청은 화면 기록에 한 줄로 남긴다: 「마디 지도 분석 요청 (첫 박 오프셋 N)」. `sendSongAudioAnalyse`가 `dispatch`로 남기는 방식을 따른다.
- 결과 `chat_response`는 채팅 기록에도 기존처럼 남는다(REQ-LDBARUI-015).

## 5. 의존과 선결 조건

- `depends_on: [SPEC-LDBARMAP-002]`. 선행 SPEC은 `status: completed`다(2026-10-14 확인, `origin/main`).

## 6. Gaps — 확인하지 않은 것

1. 「취소」 뒤에도 서버의 분석은 계속될 수 있다. 서버에는 분석을 멈추는 요청이 없으므로 확인할 수 없다. 화면은 그 사실을 안내 문구로 적는다.
2. 취소 뒤 늦은 결과가 지금 드롭다운에 고른 오프셋과 다를 수 있다. 결과 줄은 오프셋을 적지 않는다. 요청한 오프셋은 요청 시점의 화면 기록에 남는다.
3. 연결이 끊긴 뒤 결과가 어느 세션으로 가는지는 읽지 않았다. 화면은 「받지 못했을 수 있다」고만 안내한다.
4. 「분석 중」 동안 채팅 `busy`가 실제로 얼마나 오는지는 재지 않았다(run-phase 실측 항목).
5. 실제 곡의 분석 시간과 브라우저 클릭, 긴 문구의 넘침은 자동 시험 대상이 아니다. 수동 확인한다(plan.md §4).
6. E3: 표시되는 곡 파일명은 요청 시점의 값이다. 타임라인 곡과 같은지는 확인하지 않는다(SPEC-LDBARMAP-002 Gaps 8번).
7. 채팅 기록의 `busy` 항목과 컨트롤 안의 `busy` 안내가 함께 보이는 중복은 허용한다(REQ-LDBARUI-015).
8. 배선 확인: 훅과 리듀서의 연결(요청을 보낼 때의 연결 확인, 소켓 끊김, `busy` 전달)은 DOM이 없어 자동 시험하지 않는다. 수동 확인 항목으로 둔다(plan.md §4).
9. t639는 리드 확인에 따르면 폭 규칙의 승인을 SPEC에 적는 기록 카드다. 그 승인은 PR #695(병합 커밋 `b8ac5719`, 기록 커밋 `ca43cbec`)로 `origin/main`에 들어와 있다(2026-10-14 확인). 폭 규칙의 구현 카드는 t630이다(`ui/src/styles.css`의 주석).
10. 문구를 바꾸려면 SPEC 개정이 필요하다(§4 문구 고정표).
