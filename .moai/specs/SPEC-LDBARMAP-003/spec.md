---
id: SPEC-LDBARMAP-003
title: "마디 지도 진입 화면 — 첫 박 오프셋 입력과 분석 요청 UI"
version: "0.1.0"
status: draft
created: 2026-10-14
updated: 2026-10-14
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "ui/src/protocol.ts, ui/src/protocol.test.ts, ui/src/useCopilotSocket.ts, ui/src/App.tsx, ui/src/components/BarMapEntry.tsx"
lifecycle: spec-anchored
tags: "bar-map, entry-screen, ui, protocol, draft-timeline"
tier: M
related_specs: [SPEC-LDBARMAP-002, SPEC-LDBEAT-001]
depends_on: []
---

# SPEC-LDBARMAP-003 — 마디 지도 진입 화면: 첫 박 오프셋 입력과 분석 요청

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-14 | 최초 작성(카드 t648, 워크트리 `t648`, 브랜치 `WT-barmap-entry-ui`, 기준 `origin/main` `d6ca8c8b`). 입력: SPEC-LDBARMAP-002 §8 「화면 입구와 오프셋 입력」(후속 UI 카드의 일, D4), `server/web/PROTOCOL.md` 26행(`bar_map_analyse` 서버 계약, PR #693으로 main 반영). 화면 자리(D4)는 감독 결정 대기다 — §4. |

## 1. 배경

- SPEC-LDBARMAP-002가 서버 쪽 입구를 만들었다. 클라이언트 메시지 `bar_map_analyse`(첫 박 오프셋을 필수 정수로 싣는다)를 서버가 받아 마디 지도를 분석하고 저장한다. PR #693으로 main에 들어와 있다.
- 클라이언트에는 아직 이 요청을 만들고 보낼 길이 없다. `ui/src/protocol.ts`에 등록이 없고(SPEC-LDBARMAP-002 Gaps 9번), 화면에도 분석 버튼과 오프셋 입력 칸이 없다.
- 같은 SPEC §8은 분석 버튼, 첫 박 오프셋 입력 칸, 진행 표시, 결과 표시를 이 후속 UI 카드의 일로 넘겼다.

## 2. 범위

포함:
- 요청 빌더 `buildBarMapAnalyse(firstBeatOffset)`와 클라이언트 등록, 그 시험(`ui/src/protocol.ts`, `ui/src/protocol.test.ts`).
- 전송 함수 노출(`ui/src/useCopilotSocket.ts`). 누른 행동을 화면 기록에 남기는 모양은 `sendSongAudioAnalyse`와 같다.
- 입력 칸, 분석 버튼, 대기 표시, 결과 표시. 화면 자리는 §4 D4가 정한다.
- 첨부된 곡의 파일명 표시(SPEC-LDBARMAP-002 Gaps 8번 E3의 완화).

제외:
- 귀로 첫 박을 정하는 재생 화면(SPEC-LDBARMAP-002 §8).
- 4/4 밖의 박자표(D2), 분석기와 저장 스키마 변경. 서버 코드는 바꾸지 않는다.
- 콘솔 읽기와 쓰기, `SongTimelineLibrary` 저장(SPEC-LDBARMAP-002 §8).
- BPM 확정 흐름(`song_audio_analyse`와 확인 카드). 이 요청은 별도 버튼과 별도 프레임이다.

## 3. 요구사항 (EARS)

- REQ-LDBARUI-001 [HARD] **When** 곡 오디오가 첨부돼 있고, 다른 응답이 진행 중이 아니며, 사용자가 정수 오프셋 0~3을 고른 채 분석을 누르면, 클라이언트 **shall** `{"v": 1, "type": "bar_map_analyse", "first_beat_offset": <정수>}`를 정확히 한 번 보낸다.
- REQ-LDBARUI-002 [HARD] 오프셋 입력 칸은 **shall** 기본값 없이 빈 칸으로 시작한다. 서버 계약에 기본값이 없다(`server/web/PROTOCOL.md` 26행, "required int, no default"). 클라이언트는 기본값을 지어내지 **shall not** 한다.
- REQ-LDBARUI-003 정수가 아니거나 0~3 밖인 값이면, 클라이언트 **shall** 분석 버튼을 비활성으로 두고 이유를 한 줄로 보인다. 최종 판정은 서버가 한다(`server/audio/bar_map_entry.py`의 `first_beat_offset_problem`, 79~89행).
- REQ-LDBARUI-004 **While** 분석 요청이 대기 중인 동안, 클라이언트 **shall** 버튼을 비활성으로 두고 「분석 중」 상태를 보인다. 대기는 마디 지도 응답 또는 `error` 프레임으로 끝난다.
- REQ-LDBARUI-005 **When** `chat_response`의 `summary`가 `마디 지도 저장`이면, 클라이언트 **shall** 저장 성공을 보이고 곡 파일명을 함께 보인다.
- REQ-LDBARUI-006 **When** `chat_response`의 `summary`가 `마디 지도 분석 거절`이면, 클라이언트 **shall** 사유를 `text`에서 읽어 그대로 보인다. 사유 문장을 클라이언트가 지어내지 **shall not** 한다.
- REQ-LDBARUI-007 **When** `error` 프레임의 `kind`가 `song_audio_missing`이면, 클라이언트 **shall** 곡 오디오를 먼저 첨부하라는 안내를 보인다.
- REQ-LDBARUI-008 **When** 사용 중(busy) 응답이 오면, 클라이언트 **shall** 대기를 끝내고 사용 중이라는 사실을 보인다.
- REQ-LDBARUI-009 [HARD] `bar_map_analyse`는 **shall** `ui/src/protocol.ts`의 클라이언트 등록과 `ui/src/protocol.test.ts`의 시험에 같은 변경으로 들어간다(`protocol.test.ts` 93~96행의 주석과 SPEC-LDBARMAP-002 Gaps 9번).
- REQ-LDBARUI-010 [HARD] 구현은 곡 고유값(곡 제목, BPM 리터럴, 오프셋 기본값)을 상수로 박지 **shall not** 한다. SPEC-LDBARMAP-002 REQ-LDBARENTRY-016과 같은 원칙이다.
- REQ-LDBARUI-011 [HARD] 분석 요청은 BPM 확정 흐름(`song_audio_analyse`)과 **shall not** 섞인다.
- REQ-LDBARUI-012 [HARD] 진입 컨트롤은 **shall not** 콘솔에 쓰거나 콘솔을 읽는다.
- REQ-LDBARUI-013 곡 파일명은 **shall** 분석 컨트롤과 같은 자리에 보인다. 첨부된 곡을 사람이 확인할 수 있게 하기 위해서다(SPEC-LDBARMAP-002 Gaps 8번).
- REQ-LDBARUI-014 [HARD] 진입 컨트롤은 **shall** D4에서 정한 자리에 놓인다. 이 요구는 감독 결정 전까지 확정되지 않았다.

## 4. 설계 결정

### D4 — 진입 컨트롤의 화면 자리 (감독 결정 대기)

| 선택지 | 내용 | 시안과의 관계 |
|---|---|---|
| (가) 런북 상단 바 | 상단 바에 분석 컨트롤을 더한다 | 제안서 1번 항목이 상단 바 구성을 정했다(`.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-20261008.md`). 구성이 바뀐다 |
| (나) 곡 첨부 위젯 곁 | 첨부 위젯 옆에 분석 컨트롤을 둔다 | 제안서와 시안에 첨부 위젯이 없다. 새 요소다 |
| (다) 별도 패널 | 마디 지도 전용 패널을 만든다 | 제안서와 시안에 없는 새 패널이다 |

- 확인한 사실: 제안서와 시안(md·html)에는 마디 지도 진입 위치와 오프셋 입력 칸이 없다. 세 선택지 모두 시안이 정하지 않은 요소를 건드린다.
- 권고: 없음. 이 결정은 감독이 한다. 런북 UI 시안은 구속력 있는 설계이므로, 시안 밖의 배치는 감독의 명시 승인을 받은 뒤에만 한다.
- 잘못 골랐을 때: 오프셋 입력 칸이 재생 컨트롤과 멀면 사람이 값을 대충 찍고 넘어갈 수 있다. 이 위험은 SPEC-LDBARMAP-002 D4에서 이미 적었다. 이 자리 판단 자체는 근거가 없는 의견이다.

### 응답 식별

- 요청에 번호가 없다. 응답은 `summary`의 고정 라벨(`마디 지도 저장`, `마디 지도 분석 거절`)로 가린다.
- 대기 중에는 같은 화면에서 다른 전송을 막는다. 서버도 분석 중에는 다른 요청에 사용 중 응답을 돌려준다(`server/web/app.py`의 busy 가드, SPEC-LDBARMAP-002 REQ-LDBARENTRY-004).
- 남는 위험: 대기 중인 응답과 다른 흐름의 `chat_response`를 구분하는 장치가 프로토콜에 없다. run-phase에서 대기 상태 동안 채팅 흐름을 막는 방식으로 줄인다.

### 화면 기록

- 분석 요청은 화면 기록에 한 줄로 남긴다. 예: 「마디 지도 분석 요청 (첫 박 오프셋 2)」. `sendSongAudioAnalyse`가 `dispatch`로 남기는 방식을 따른다.

## 5. 의존과 선결 조건

- `depends_on`을 비워 두었다. SPEC-LDBARMAP-002가 `status: draft`라서 `depends_on`으로 걸면 `/moai run` Phase 1 선결 점검이 막힌다(완료 상태만 충족으로 본다). 서버 계약은 이미 main에 있으므로 `related_specs`로 연결한다.

## 6. Gaps — 확인하지 않은 것

1. 화면 자리(D4)는 감독 결정 전이다. REQ-LDBARUI-014는 확정이 아니다.
2. 채팅 기록에 마디 지도 응답을 그대로 올릴지는 정하지 않았다.
3. 사용 중 응답이 이 요청의 응답인지 다른 프레임의 응답인지 구분하는 방법은 run-phase에서 실측한다.
4. 실제 곡 분석 시간과 브라우저 실기 동작은 재지 않았다.
5. 한국어 안내 문구의 최종 표현은 run-phase에서 정한다.
