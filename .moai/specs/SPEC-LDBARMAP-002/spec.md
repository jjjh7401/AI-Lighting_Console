---
id: SPEC-LDBARMAP-002
title: "마디 지도 진입 경로 — 오디오에서 마디 지도까지 서버 쪽 입구"
version: "0.1.2"
status: completed
created: 2026-10-14
updated: 2026-10-14
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "server/web/messages.py, server/web/app.py, server/web/session.py, server/audio/bar_map_entry.py, server/tests/test_prechk_tool.py"
lifecycle: spec-anchored
tags: "bar-map, entry-path, ws-message, audio-analysis, draft-timeline, protocol-freeze"
tier: M
related_specs: [SPEC-LDARRANGE-001, SPEC-LDBEAT-001, SPEC-LDRHYTHM-001]
depends_on: [SPEC-LDBARMAP-001]
---

# SPEC-LDBARMAP-002 — 마디 지도 진입 경로: 오디오에서 마디 지도까지 서버 쪽 입구

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-14 | 최초 작성(카드 t638). 입력: `SPEC-LDBARMAP-001`(status: completed — 분석기·저장 관문이 이미 있고 이 SPEC은 그 둘 사이를 잇는다), `SPEC-LDARRANGE-001` §5 항목 1(소비자 쪽 입력 모양), 코드 직접 읽기(아래 §3 전제표 — 인용한 줄은 전부 이 plan-phase에서 열어 읽은 줄이다). **plan만 — 코드 변경 0줄, 시험 실행 0회, 콘솔 접촉 0건, 다른 SPEC 디렉터리 수정 0건.** REQ 접두사는 `REQ-LDBARENTRY-`, AC 접두사는 `AC-LDBARENTRY-`다 — `REQ-LDBARMAP-001~016`·`AC-LDBARMAP-001~016`(SPEC-LDBARMAP-001 소유)과 grep에서 섞이지 않게 접두사를 갈랐다(origin/main에서 `LDBARENTRY` 0건 확인). |
| 2026-10-14 | plan-audit 1차 FAIL(MP-7만, 0.84) — F1~F12 반영; 표지 6개는 감독 결정 대기로 유지 |
| 2026-10-14 | plan-audit 2차 FAIL(MP-7만, 0.94) — N1·N2 반영; 표지 6개는 감독 결정 대기 |
| 2026-10-14 | base 갱신 — `origin/main` `f5eada95` → `cca88d23`로 rebase(커밋 `9484aab9`, 카드 t635 계열: `SongTimelineStore.beat_grid_snapshots` 추가, `ChatSession._beat_grid_snapshots`가 그 저장소를 가리킴, `ChatSession.song_timeline_replay()` 추가, `app.py` 새 연결 재생이 그 메서드를 호출). `session.py`·`app.py` 줄 번호 인용을 `cca88d23` 기준으로 고쳤다(spec.md 54곳, 아래 plan.md·acceptance.md 각 3곳). 전제 P1~P18은 줄 번호만 이동했고 내용은 그대로이며, 서술이 바뀐 것은 Gaps 5번(재생 경로)뿐이다. 처음 감사한 base는 `f5eada95`였고 `.moai/reports/plan-audit/`의 감사 보고서는 그 base의 줄 번호를 유지한다. REQ·AC의 번호와 개수(16/16)는 그대로다. |
| 2026-10-14 | 감독 결정 반영 — 「전부 권고안대로」: D1(`first_beat_offset`은 필수 요청 필드)·D2(4/4 전용)·D3(새 타입 `bar_map_analyse`)·E1(두 배 BPM 채택은 저장 거절)·E2(거절도 `status` `ok` + 요약)·E3(첨부 오디오와 타임라인의 곡 대응은 확인하지 않음 — 알려진 한계, Gaps 8번)를 확정했고 E4(저장 `bpm`은 검출기 값만)도 확정을 확인했다. `plan.md`의 미결 표지 6개를 해소했다. D4(화면 자리)는 후속 UI 카드의 결정으로 남는다. REQ·AC 개수와 번호는 그대로(16/16)이고 REQ-LDBARENTRY-012·AC-LDBARENTRY-007·AC-LDBARENTRY-015의 문구만 E2에 맞췄다. 위 두 행의 「감독 결정 대기」는 그 일자의 기록이며 이 행으로 해소됐다. |
| 2026-10-14 | 실행 단계 결정 E5 반영(카드 t647 배차서의 「D1」 — 이 SPEC의 D1은 `first_beat_offset` 출처라서 이름을 E5로 적는다). 거절 사유 문장은 본문(`text`)에 싣고, `summary`는 성공과 그 밖의 결과를 가르는 고정 라벨로 쓴다. 기존 응답 모양과 같다(`server/web/session.py` base `7cfc80c2`의 `:9378-9385`와 `:9428`). REQ-LDBARENTRY-012, §5 표의 E2 행, plan.md §B 3번, AC-LDBARENTRY-007을 이 결정에 맞췄다. 본문을 고쳐서 plan-audit 3차 PASS(0.91)를 기록한 산출물 해시가 바뀌었다. 다시 감사할지는 리드가 정한다. |
| 2026-10-14 | 본문 정정 3건(카드 t647, 실행 단계에서 발견). (a) REQ-LDBARENTRY-010·AC-LDBARENTRY-004 (5): 저장 관문이 `draft` 표식을 얹으므로 「`bar_map` 키 외 바이트 동일」을 「`bar_map`과 `draft` 표식 외 바이트 동일」로 고쳤다. (b) AC-LDBARENTRY-006 (다): 패치 대상은 `analyze.py:229`의 정의가 아니라 `bar_map.py`가 가져다 쓰는 이름(`bar_map.py:36` 가져오기, `:179` 사용)이다. (c) 전제 P13: 업로드가 지우는 것은 `_song_analysis`뿐이고 `_song_bpm`은 유지한다. REQ·AC 개수와 번호(16/16)는 그대로다. 본문을 고쳐서 plan-audit 3차 PASS(0.91)를 기록한 산출물 해시가 다시 바뀌었다. |

## §0. Tier 선택 근거

**Tier M.** 이 SPEC은 신규 서버 코드를 만든다 — 합성 모듈 1개, 세션 메서드 1개, 프레임 파서 1개, 디스패치 분기 1개, 동결 스냅샷 1행 — 그리고 시험 파일 4개를 더한다. 영향 파일은 9개 안팎(운영 코드 4개, 기존 시험 수정 1개, 신규 시험 4개)이고 줄 수는 시험을 포함해 대략 635~955줄로 본다. 둘 다 Tier S 상한(5파일, 300줄)을 넘고 Tier L 기준(15파일, 1000줄, 헌법급 결정)에는 못 미친다. 이 추정은 코드를 짜 본 값이 아니라 아래 plan.md §C의 파일 목록을 센 값이다 — 틀릴 수 있다(Gaps 10번). REQ 16개·AC 16개로 Tier M 상한(각 16개)에 정확히 닿는다. 상한에 닿았다는 것은 이 SPEC이 더 커지면 쪼개야 한다는 신호다 — UI 입구가 같은 SPEC으로 들어오려 하면 그때 분리한다(§8). frontmatter `module`의 `server/audio/bar_map_entry.py`는 가칭이다 — 신규 합성 모듈의 파일 이름은 run-phase에서 확정한다. `research.md`는 두지 않는다(Tier M).

## §1. 배경 — 왜 지금인가

`SPEC-LDBARMAP-001`은 completed다. 그 결과 서버에는 마디 지도를 **만들 수 있는** 것(분석기)과 **저장할 수 있는** 것(저장 관문)과 **읽어 쓰는** 것(소비자)이 모두 있다. 없는 것은 그 셋을 잇는 입구 하나다.

- 저장 관문 `store_timeline_bar_map`(`server/web/session.py:9317`)을 부르는 곳은 시험뿐이다(`grep -rn store_timeline_bar_map server tools` 결과 — 정의 1곳, 호출은 `server/tests/test_session_bar_map_store.py`만).
- 분석기 `server/audio/bar_map.py`를 운영 코드에서 import하는 곳은 없다(`grep -rn "audio.bar_map" server tools src-tauri console` 결과 — import하는 파일은 시험 4개 `test_audio_bar_map.py`·`test_audio_bar_map_store.py`·`test_audio_mp3_zero_gap_t552.py`·`test_audio_tempo_t546.py`와 도구 2개 `tools/barmap/gen_bar_features_fixture.py`·`gen_ear_check_candidates.py`뿐이다. `session.py:40`이 import하는 것은 분석기가 아니라 `bar_map_store`다).
- 소비자는 이미 배선돼 있다. `session.py:10450`과 `:11427`가 `build_song_timing_from_bar_map(timeline.get("bar_map"))`를 부른다. 그런데 `bar_map` 키에 값을 넣어 줄 운영 경로가 없으니, 이 두 줄은 지금 실제 곡에서는 늘 `None`을 받는다.
- 웹 계층에 마디 지도 표면이 없다. `server/web/*.py` 중 `bar_map`을 언급하는 파일은 `session.py` 하나뿐이고, `ui/src`·`src-tauri`·`console`에는 `bar_map`·`barmap`·`마디 지도`가 0건이다.

그래서 감독이 오디오를 첨부해도 마디 지도는 생기지 않고, `SPEC-LDARRANGE-001`이 입력으로 기다리는 값(`SPEC-LDARRANGE-001` REQ-LDARRANGE-001 근거 칸: "실제 곡의 마디 지도 데이터가 `timeline["bar_map"]`에 들어온 적은 아직 없다")은 만들어질 길이 없다. 이 SPEC은 그 길 하나 — **서버 쪽 입구** — 만 낸다. 화면의 버튼과 첫 박 오프셋 입력은 후속 UI 카드다.

## §2. 범위

**들어오는 것(서버 쪽 입구 전체)**: 요청 접수(프레임) → 분석(오디오 → 마디 지도) → 저장(기존 `store_timeline_bar_map`과 `validate_bar_map`을 그대로 통과) → 응답. 쓰는 곳은 초안 타임라인의 `bar_map` 키 하나다. 콘솔과 라이브러리는 건드리지 않는다.

**확정 설계(2026-10-14 감독 결정 — 대안과 근거는 §5)**:

- 새 클라이언트 메시지 타입 `bar_map_analyse`. 정수 `first_beat_offset`을 필수 필드로 싣는다. 기본값이 없다 — `REQ-LDBARMAP-016`이 "첫 박은 사람이 귀로 확정한다"고 했기 때문이다.
- 핸들러는 기존 `song_audio_analyse` 분기(`server/web/app.py:760-794`)의 틀을 따른다. 첨부 오디오 없음 오류, busy 가드, `create_task` + `to_thread`로 수신 루프를 막지 않는 구조다.
- 합성 순서: 디코드 → `detect_beat_grid` → `derive_bars` → `extract_bar_features` → `classify_bar_events` → `build_bar_map_payload` → `store_timeline_bar_map`.
- 어느 단계든 실패하면 응답이 사유를 싣고, 타임라인과 되돌리기 깊이는 그대로다.

**이 SPEC이 정하는 것과 정하지 않는 것**은 §6(LDARRANGE 매핑)과 §8(제외 범위)에 있다.

## §3. 전제와 증거

아래 모든 줄은 이 plan-phase에서 파일을 열어 읽은 것이다(base `origin/main` = `cca88d23`, 2026-10-14에 rebase했다. 처음 감사한 base는 `f5eada95`였고 `.moai/reports/plan-audit/`의 감사 보고서는 그 base의 줄 번호를 그대로 유지한다. 두 base 사이에 바뀐 운영 파일은 `server/web/app.py`와 `server/web/session.py`뿐이며(커밋 `9484aab9`, 카드 t635 계열) 이 문서의 두 파일 인용은 `cca88d23` 기준으로 새로 확인했다). **시험은 하나도 돌리지 않았다** — "읽음"은 코드를 읽은 것이지 동작을 잰 것이 아니다.

| # | 전제 | 근거(file:line) | 판독 |
|---|---|---|---|
| P1 | 저장 관문은 유효성 검사 → 되돌리기 기록 → 배지 → 저장 → 이벤트 순서로 일한다. 성공 시 `song_timeline`·`chat_response` 두 프레임을 보낸다 | `server/web/session.py:9317-9363`(검사 `:9336`, 기록 `:9346`, 저장 `:9351`, 전송 `:9352`·`:9362`) | 읽음 |
| P2 | 그 관문의 **거절 경로는 이벤트를 반환만 하고 `_send`하지 않는다** — 타임라인 없음(`:9330-9335`), 검증 거절(`:9338-9345`). 성공 경로만 `_send`한다 | `session.py:9330-9345` 대 `:9352`·`:9362`; `_send`는 연결이 주입한 콜백(`session.py:4046`) | 읽음 |
| P3 | 저장 스키마의 정본은 `validate_bar_map`. 최상위 키 6개, 마디 키 3개, 사건 키 5개 외에는 거절한다 | `server/audio/bar_map_store.py:54-58`(키 집합), `:165-224`(검증), `:175-177`(알 수 없는 필드 거절) | 읽음 |
| P4 | 페이로드 빌더는 만들고 나서 스스로 `validate_bar_map`을 부른다 | `bar_map_store.py:100-157`(자기 검증 `:154-156`) | 읽음 |
| P5 | 분석기는 4/4 전용이다 — 한 마디 박 수 상수 4, `derive_bars`는 오프셋이 0~3 밖이면 거절한다 | `server/audio/bar_map.py:55`, `:452-457` | 읽음 |
| P6 | 반대로 저장 쪽은 박자표에 일반적이다(분자 1~16, 분모 1·2·4·8·16) | `bar_map_store.py:203-209` | 읽음 |
| P7 | 마디 번호 공간이 `derive_bars`와 `build_bar_map_payload`에서 같다 — 첫 다운비트가 마디 1이고, 그 앞 박은 마디 0(못갖춘마디) | `bar_map.py:461-471`(다운비트는 `(i - offset) % 4 == 0`), `bar_map_store.py:129-141`(앞 `offset`개 박이 마디 0, 나머지는 분자 개씩 마디 1, 2, …). `extract_bar_features`는 경계 목록의 i번째 창을 마디 `i+1`로 번호 매긴다(`bar_map.py:699-708`) | 읽음 |
| P8 | `detect_beat_grid`가 `adopt_double`을 채택해도 박 격자는 다시 만들지 않는다. 반환 `bpm`은 보정된 값이고 `beat_times_ms`는 원래 격자다 | `bar_map.py:107-111`(알려진 한계 명시), `:264-270`(`bpm=bpm_check.adopted_bpm`), `:401-409`(채택 분기) | 읽음 |
| P9 | 소비자는 저장된 `bpm`으로 마디 시작 시각을 계산한다 — `마디 N 시작 = 1마디 시작 + (N-1) × 분자 × 60/bpm` | `server/design/beat_grid_emit.py:206-216`; `bar_map`에서 `SongTiming`을 만드는 곳 `server/design/beat_grid_send.py:232-284`(`bpm` `:245`, 1마디 `start_ms` `:261-267`) | 읽음 |
| P10 | `BarEvent`에는 `start_beat` 필드가 없고, 저장 변환은 기본값 1을 채운다 — 이 경로는 `start_beat != 1`인 사건을 만들 수 없다 | `bar_map.py:584-598`, `bar_map_store.py:76-95` | 읽음 |
| P11 | `song_audio_analyse` 분기는 첨부 없음(`:774-783`) → busy(`:784-786`) → `create_task(to_thread(...))`(`:787-794`) 순서다. `create_task`를 쓰는 이유는 **사람의 답을 기다리는 확인 카드**(상한 600초) 때문이라고 분기 주석이 적었다(`:766-773`) | `server/web/app.py:760-794`, 상수 `:89`·`:92` | 읽음 |
| P12 | `analyse_song_audio`는 BPM을 확정하고 `_song_bpm`(`:13737`)과 `_song_analysis`(`:13780`)를 쓴다. 이 메시지 계약은 바뀌면 안 된다 | `session.py:13675-13781` | 읽음 |
| P13 | 첨부 오디오는 세션이 들고 있고(`session.py:4190`, 읽기 창 `:13541-13547`), 업로드는 이전 확정 기록(`_song_analysis`)만 지우고 `_song_bpm`은 유지한다(`:13569-13570`; 현재 트리 `d6ca8c8b`에서는 `:13767-13769`, 주석 「`_song_bpm` 은 손대지 않는다」) | `session.py:13549-13599` | 읽음 |
| P14 | HTTP `POST /api/timelines/{id}/load`가 `store.latest`를 통째로 바꾼다. 이 경로에는 WS의 `current_task` busy 가드가 없다 | `server/web/timeline_api.py:56-72`(`deps.store.latest = timeline` `:71`) | 읽음 |
| P15 | 곡을 가르는 기존 열쇠는 `(song_title, sequence_number)`다 | `session.py:10158-10162` | 읽음 |
| P16 | 프로토콜 동결 게이트: 허용 목록은 `CLIENT_MESSAGE_TYPES`(`server/web/messages.py:116-188`), 파서의 거절은 `:389`. 시험은 `*_MESSAGE_TYPES` 튜플을 AST로 모아 정렬해 `_EXPECTED_CLIENT_MESSAGE_TYPES`와 같은지 비교한다 | `server/tests/test_prechk_tool.py:1248-1331`(튜플), `:1417-1426`(수집), `:1438-1465`(정렬 `:1463`), `:1484-1500`(단언 `:1499`) | 읽음 — 결과는 §7 |
| P17 | 실패 객체는 사유 문자열 하나를 든다. 일부 사유는 예외 문구를 그대로 끼운다 | `bar_map.py:119-127`, `:145-149`, `:577-581`; 예외 끼움 `:192`·`:251`·`:681` | 읽음 |
| P18 | 소비자 쪽 입력 모양 대조는 §6에 있다 | `bar_map_store.py` 대 `SPEC-LDARRANGE-001/spec.md:142-146` | 읽음 |

## §4. 요구사항 (GEARS)

### 4.1 R1 — 요청 접수 (REQ-LDBARENTRY-001~005)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARENTRY-001 | [HARD] **When** 클라이언트가 마디 지도 분석 프레임을 보내고 세션에 곡 오디오가 붙어 있으면, 서버 **shall** 그 오디오를 박 격자 검출, 첫 박 오프셋 적용 마디 파생, 마디별 특징 추출, 변화 이벤트 분류의 순서로 분석해 마디 지도 한 벌을 만들고, 기존 `store_timeline_bar_map`을 거쳐 초안 타임라인의 `bar_map` 키에 저장한다. | P1, P3. 오디오 → 지도 사슬의 각 마디는 이미 있다(`SPEC-LDBARMAP-001` M2~M4). 비어 있는 것은 사슬을 잇는 입구뿐이다(§1) |
| REQ-LDBARENTRY-002 | [HARD] **The** 마디 지도 분석 프레임 **shall** 정수 `first_beat_offset`을 필수 필드로 싣고 오디오 바이트를 싣지 않는다. 파서는 이 필드가 없거나 null이거나 bool·실수·문자열이면 기본값(0 포함)으로 채워 통과시키지 **shall not** 하고 프로토콜 오류로 거절한다. | `REQ-LDBARMAP-016`(첫 박은 사람이 귀로 확정한다). 자동 위상 선택은 M1에서 0/82로 실패했다(`SPEC-LDBARMAP-001` HISTORY 카드 t530 행). `bool`을 먼저 거르는 관행은 `messages.py:740-742`의 주석과 같다. 범위(0~3) 판정은 분석 첫 점검이 맡는다(REQ-LDBARENTRY-007) — 파서가 박 수 상수를 따로 들지 않게 한다 |
| REQ-LDBARENTRY-003 | **When** 마디 지도 분석 프레임이 오는데 세션에 곡 오디오가 없으면, 서버 **shall** 분석을 시작하지 않고 종류 `song_audio_missing`의 오류를 돌려주며 타임라인과 되돌리기 깊이를 바꾸지 않는다. | P11(`app.py:774-783`가 같은 조건에 같은 종류와 문구를 쓴다 — 같은 조건이니 같은 이름이 맞다) |
| REQ-LDBARENTRY-004 | **While** 이전 지시나 분석이 처리 중인 동안, 서버 **shall** 마디 지도 분석 프레임에 busy 응답을 돌려주고 새 분석을 시작하지 않는다. | P11(`app.py:784-786`), 같은 가드가 `app.py:541`·`:556`·`:569`·`:580` 등 모든 쓰기 분기에 있다 |
| REQ-LDBARENTRY-005 | [HARD] **The** 서버 **shall** 분석을 수신 루프 밖의 백그라운드 작업으로 돌리고 루프가 그 완료를 기다리지 **shall not** 한다 — 분석 중에도 다른 프레임(예: 상태 요청)을 읽고 답한다. | P11. `song_audio_analyse`가 `create_task`를 쓰는 이유는 사람 응답 대기였다(`app.py:766-773`). **이 경로의 이유는 다르다**: 사람 대기는 없지만 전곡 분석은 CPU를 오래 쓴다(분석 시간은 미측정, Gaps 1번). 이유가 달라도 구조는 같아야 한다 |

### 4.2 R2 — 합성과 실패 (REQ-LDBARENTRY-006~009)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARENTRY-006 | [HARD] **The** 합성 **shall** 기존 함수(`detect_beat_grid`·`derive_bars`·`extract_bar_features`·`classify_bar_events`·`build_bar_map_payload`)와 저장 관문의 `validate_bar_map`만 쓰고, 마디 지도 검증 규칙을 다시 구현하지 **shall not** 한다. 특징과 사건의 마디 번호 공간은 저장되는 `bars[].bar`와 같아야 하고, 합성 단계는 콘솔·세션·UI 상태 없이 오디오 바이트와 오프셋만으로 돌 수 있어야 한다. | P3, P4, P7. 검증 규칙을 복제하면 두 곳이 조용히 갈라진다(`bar_map_store.py:160-164`의 `@MX:ANCHOR`가 이 함수를 "유일한 검증 관문"으로 못박았다) |
| REQ-LDBARENTRY-007 | [HARD] **When** 합성의 어느 단계든 실패하거나(첫 박 오프셋이 범위 밖인 경우와 초안 타임라인이 없는 경우 포함) 저장 관문이 거절하면, 서버 **shall** 실패한 단계의 사유를 응답에 싣고 `store.latest`와 되돌리기 깊이를 요청 전과 같게 유지한다. 오프셋 범위와 타임라인 존재 같은 싼 점검은 오디오 디코드 전에 한다. | P2, P5, P17. 실패 종류: 디코드·분석 실패(`BeatGridFailure`), 파생 실패(`BarMapFailure`), 특징 실패(`BarFeaturesFailure`), 빌더 예외(`BarMapStoreError`, `bar_map_store.py:61`), 분석 라이브러리 부재(`MANUAL_BPM_FALLBACK_REASON`, `analyze.py:188`) |
| REQ-LDBARENTRY-008 | **When** 박 격자 검출이 두 배 BPM을 채택했으면(`bpm_check.outcome`이 `adopt_double`), 서버 **shall** 마디 지도를 저장하지 않고 그 사유를 응답에 싣는다. | P8, P9. 격자는 두 배로 다시 만들어지지 않는데 `bpm`만 두 배면, 소비자가 계산하는 모든 마디 시작이 어긋난다(`beat_grid_emit.py:216`). E1 확정(2026-10-14): 저장을 거절하며 원래 BPM으로도 보정 BPM으로도 저장하지 않는다(§5) |
| REQ-LDBARENTRY-009 | **When** 분석이 끝나 저장하려는 시점의 초안 타임라인이 요청을 받은 시점과 다른 곡이거나 없으면, 서버 **shall** 저장하지 않고 그 사실을 응답에 싣는다. 두 시점의 비교에는 기존 곡 열쇠 `(song_title, sequence_number)`를 쓴다. | P14, P15. 분석은 오래 걸리고, 그 사이 HTTP 불러오기가 `store.latest`를 바꿀 수 있으며 그 경로는 WS 가드 밖이다. 이 비교는 창을 좁힐 뿐 읽기-쓰기 사이를 잠그지는 않는다(Gaps 4번) |

### 4.3 R3 — 저장 범위·접촉 경계·응답 (REQ-LDBARENTRY-010~012)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARENTRY-010 | [HARD] **When** 저장이 성공하면, 서버 **shall** 타임라인에서 `bar_map` 키와 저장 관문이 얹는 `draft` 표식만 바꾸고(그 밖의 키는 바이트까지 같다), 되돌리기 깊이를 정확히 1 올리고, `song_timeline` 프레임을 정확히 1회 보내며, 되돌리기 한 번이 직전 `bar_map` 값(또는 키 없음)을 복원하도록 이력에 기록한다. 이미 `bar_map`이 있었다면 새 값으로 교체한다. | P1(`session.py:9346-9352`이 이미 이렇게 일한다). 이 요구사항은 새 동작이 아니라 **진입 경로가 그 동작을 깨뜨리지 않는다**는 못박음이다 |
| REQ-LDBARENTRY-011 | [HARD] **The** 진입 경로 **shall not** 콘솔(게이트·실행 포트)에 쓰거나 읽고, `SongTimelineLibrary`에 저장하고, BPM 확정 상태(`_song_bpm`·`_song_analysis`)를 바꾸고, `analyse_song_audio`의 메시지 계약을 바꾼다. | P12. 저장 관문의 성공 문구도 같은 경계를 약속한다("콘솔 무접촉", "라이브러리에 남기려면 별도로 저장", `session.py:9357-9358`) |
| REQ-LDBARENTRY-012 | [HARD] **When** 요청이 분석 단계(진입 메서드)에 도달해 끝나면(성공이든 거절이든 분석 실패든), 서버 **shall** 연결로 `chat_response` 프레임을 정확히 1개 보낸다 — 고정 요약(`summary`) 라벨이 성공과 그 밖의 결과(거절·분석 실패)를 가른다. 거절과 분석 실패의 `status`는 새 값이 아니라 성공과 같은 `ok`이고, 사유 문장은 본문(`text`)에 싣는다(E2, E5). 성공의 `chat_response`는 저장 관문이 이미 보내므로 진입 경로는 성공에서 추가로 보내지 **shall not** 하고, 저장 관문이 반환만 하고 보내지 않는 거절 경로(P2)와 분석 실패에서는 진입 경로가 정확히 한 번 직접 보낸다. 분석 단계에 도달하지 못한 요청은 `chat_response`를 0개 보낸다 — 첨부 오디오 없음(REQ-003)은 `error`, busy(REQ-004)는 `busy`, 프레임·프로토콜 오류는 `error`(kind `protocol`)로 답한다. | P1(성공은 관문이 `song_timeline`·`chat_response`를 이미 전송), P2(거절은 반환만). 보내지 않으면 화면은 아무 응답도 못 받고, 성공에서 또 보내면 응답이 둘이 된다. 선례: 박자 격자 거절은 반환과 전송을 함께 한다(`session.py:9385-9393`). 분석에 도달하지 못한 세 경우의 응답 종류는 REQ-003·004와 `app.py:774-786`, 파서 거절 `app.py:534-538`이 정한다 |

### 4.4 R4 — 프로토콜 동결 (REQ-LDBARENTRY-013)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARENTRY-013 | [HARD] **The** 클라이언트 메시지 타입 추가 **shall** 같은 변경에서 `server/tests/test_prechk_tool.py`의 `_EXPECTED_CLIENT_MESSAGE_TYPES`에 손으로 한 줄과 사유 주석을 더하는 것을 동반하고, 서버 메시지 타입(`_EXPECTED_SERVER_MESSAGE_TYPES`)과 REST 라우트(`_EXPECTED_WEB_ROUTES`)는 늘리지 **shall not** 한다. | P16, §7. 선례: 카드 t551·t563·t578·t589·t565·t571(`test_prechk_tool.py:1250-1261`, `:1267-1270`, `:1274-1275`, `:1307-1310`) |

### 4.5 R5 — 소비자 호환과 일반화 (REQ-LDBARENTRY-014~016)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARENTRY-014 | **When** 저장이 성공하면, 저장된 값 **shall** `timeline_bar_map()`으로 읽히고, 그 값을 `build_song_timing_from_bar_map`에 넣으면 `None`이 아닌 `SongTiming`이 나오며 그 `downbeat_bar1_seconds`는 저장된 1마디 `start_ms`를 1000으로 나눈 값과 같다. | P9, `SPEC-LDARRANGE-001` REQ-LDARRANGE-001의 선행 조건("마디 지도 데이터가 들어오는 경로") |
| REQ-LDBARENTRY-015 | **The** 진입 경로 **shall** 4/4 박자만 다루고 저장되는 `time_signature`를 `[4, 4]`로 명시해 싣는다. 다른 박자표를 받는 필드나 옵션을 프레임에 두지 **shall not** 한다. | P5, P6. 분석기가 4/4 전용이다. 저장 쪽이 일반적이라는 사실(P6)은 이 SPEC의 분석 범위를 넓히는 근거가 아니다 — D2 |
| REQ-LDBARENTRY-016 | [HARD] **The** 구현과 시험 **shall not** 곡·장비 고유값(BPM 리터럴, 곡 제목, 시퀀스 번호, 그룹 번호, fid)을 상수로 박거나 오디오 파일을 저장소에 커밋하지 않는다. 실제 곡 시험은 저장소 밖 경로를 참조하는 로컬 전용 게이트로만 둔다. | 감독 원칙(2026-10-10, 전 레인 공통 — "조건은 바뀐다, 다른 장비·디자인·곡에서도 동작해야 한다", `SPEC-LDBARMAP-001` §5 일반화 규칙). `REQ-LDBARMAP-014`(오디오 비커밋) 선례 |

## §5. 감독 결정과 엔지니어링 확인

감독 결정 D1~D3은 2026-10-14에 「전부 권고안대로」 확정됐다. D4(화면 자리)는 후속 UI 카드의 결정으로 남는다. 각 항목에 선택지, 확정 내용(D4는 권고 없음), 잘못 골랐을 때 무엇이 깨지는지를 적는다.

### D1 — `first_beat_offset`의 출처

| 선택지 | 내용 |
|---|---|
| (가) 필수 요청 필드 **(2026-10-14 확정)** | 프레임이 정수 오프셋을 반드시 싣는다. 없으면 파서가 거절한다(REQ-LDBARENTRY-002) |
| (나) 기본값 0 + 후속 UI | 필드를 선택으로 두고 없으면 0으로 분석한다. 입력 화면은 나중에 |
| (다) 서버가 후보를 제안 | 자동 위상 선택. 이 SPEC에서는 **제외한다** — M1에서 후보 세 개가 모두 0/82로 실패했다(`SPEC-LDBARMAP-001` HISTORY 카드 t530 행) |

**잘못 골랐을 때**: (나)를 골랐는데 실제 오프셋이 0이 아니면, 모든 마디 시작이 한 박 이상 어긋난 지도가 **구조 검사를 통과해 조용히 저장된다**. `validate_bar_map`은 모양만 보고 위상은 보지 않는다(P3). 어긋난 오프셋의 적중률이 10% 밑이라는 것은 이미 시험으로 확인돼 있다(`server/tests/test_audio_bar_map.py:531-546`, 오프셋 0·2). 그 뒤 `SPEC-LDARRANGE-001`이 그 지도로 큐를 배치하면 전 마디가 한 박씩 밀린다. (가)를 잘못 골랐을 때의 비용은 호출하는 쪽이 항상 오프셋을 알아야 한다는 것뿐이고, 지금은 호출하는 UI가 없으므로 비용이 0에 가깝다.

### D2 — 박자표 범위

| 선택지 | 내용 |
|---|---|
| (가) 4/4 전용 **(2026-10-14 확정)** | 분석기를 그대로 쓴다. `time_signature`는 `[4, 4]`로 명시한다(REQ-LDBARENTRY-015) |
| (나) 분석기 일반화 | `_BEATS_PER_BAR` 상수와 `derive_bars`·특징 창·시험을 박자표 인자로 넓힌다 |

**잘못 골랐을 때**: (가)를 골랐는데 곡이 3/4면, 마디가 4박 단위로 묶여 모든 마디 경계가 틀린 지도가 저장된다 — 오류 없이. 완화는 `time_signature: [4, 4]`가 저장 값에 명시돼 화면이 보여 줄 수 있다는 것뿐이다. (나)를 골랐을 때의 비용은 `SPEC-LDBARMAP-001`이 completed로 닫은 분석기·시험을 다시 여는 범위 확장이다. 저장 쪽은 이미 일반적이므로(P6) 분석기만 넓히면 나중에 이 입구가 그대로 따라온다.

### D3 — 메시지 모양

| 선택지 | 내용 |
|---|---|
| (가) 새 타입 + 스냅샷 한 줄 **(2026-10-14 확정)** | `bar_map_analyse`를 허용 목록에 더하고 `_EXPECTED_CLIENT_MESSAGE_TYPES`에 한 줄을 손으로 더한다. 선례 t551·t563 |
| (나) `song_audio_analyse` 확장 | 타입 목록은 그대로. 같은 프레임에 오프셋을 선택 필드로 더하고 분석 뒤에 지도도 만든다 |

**잘못 골랐을 때**: (나)를 고르면 이 경로가 BPM 확정 계약에 섞인다. `song_audio_analyse`는 확인 카드를 띄우고 사람의 답을 기다리며(상한 600초, `app.py:766-773`) `_song_bpm`·`_song_analysis`를 쓴다(P12). 지도 분석이 그 흐름 안에 있으면 카드가 미응답으로 끝났을 때 지도를 저장할지 말지가 불명확해지고, 오프셋(귀로 정하는 값)이 BPM 카드의 입력과 뒤섞인다. REQ-LDBARENTRY-011이 지키려는 "BPM 확정 계약 불변"이 깨지는 방향이다. (가)를 골랐을 때의 비용은 동결 스냅샷 한 줄과 사유 주석, 그리고 클라이언트 쪽 허용 목록(`ui/src/protocol.ts`)에 후속 UI 카드가 같은 변경에서 등록해야 한다는 것이다(Gaps 9번).

### D4 — 진입 버튼과 오프셋 입력의 화면 자리

후속 UI 카드의 결정이다. 이 SPEC은 서버만 낸다.

| 선택지 | 내용 |
|---|---|
| (가) 런북 화면 상단 바 | 박자 격자를 보는 같은 화면에서 지도를 만든다 |
| (나) 곡 오디오 첨부 위젯 곁 | 오디오를 붙인 자리에서 바로 분석한다 |
| (다) 별도 패널 | 마디 지도 전용 패널 |

**권고 없음.** 이 plan-phase는 감독이 말한 디자인 제안서를 읽지 않았다(Gaps 3번) — 읽지 않은 문서에 비춰 권고를 낼 수 없다. **잘못 골랐을 때**: 오프셋 입력이 첫 박을 귀로 확정하는 흐름(재생과 함께 들으며 정한다)에서 멀리 놓이면, 사람이 값을 대충 찍고 넘어가 D1이 막으려던 조용한 위상 오류가 UI에서 재현된다. 화면 자리는 오디오 재생 컨트롤과의 거리로 가르는 것이 맞다고 보지만, 이것은 근거 없는 의견이다.

### 엔지니어링 확인 항목(E1~E4 모두 2026-10-14 확정, E5는 실행 단계에서 확정)

| # | 항목 | 선택지 | 확정 | 잘못 골랐을 때 |
|---|---|---|---|---|
| E1 | 두 배 BPM 채택 시 처리(REQ-LDBARENTRY-008) | (가) 저장 거절 + 사유 (나) 격자와 일치하는 원래 BPM(`bpm_check.raw_bpm`)으로 저장 (다) 보정 BPM으로 저장 | (가) | (다): 소비자 마디 시작이 어긋난다(P9). (나): 저장은 되지만 감독이 "분석기가 두 배라고 판단했다"는 사실을 잃는다 — 마디 지도에 그 메모를 넣을 필드가 없다(P3). (가): 두 배 채택 곡은 입구를 못 쓴다. t547 재설계 뒤 실제 10곡은 전부 keep이었다고 `SPEC-LDBARMAP-001` REQ-LDBARMAP-006 근거 칸이 적었다 — 이 plan-phase가 다시 재지는 않았다 |
| E2 | 거절 응답의 `status` 값 | (가) 선례대로 `"ok"` + 고정 요약 라벨로 구분(사유 문장은 E5) (나) 새 값 | (가) | (나): 클라이언트가 모르는 상태값 어휘를 새로 알아야 한다. 이 plan-phase는 `status`의 허용 어휘를 확인하지 못했다(Gaps 13번). 선례는 `session.py:9331`·`:9387-9390` |
| E3 | 첨부 오디오와 현재 타임라인의 곡이 같은지 | (가) 확인하지 않는다(응답에 파일명을 싣지도 않는다) (나) 저장 스키마에 출처 해시 필드를 더한다 | (가), 단 Gaps 8번에 남긴다 | (가): 다른 곡 오디오를 현재 곡 타임라인에 저장할 수 있다. (나): `validate_bar_map`이 알 수 없는 필드를 거절하므로(P3) `SPEC-LDBARMAP-001`의 completed 스키마를 열고 `SPEC-LDARRANGE-001` 미러 문단도 같이 고쳐야 한다 — 이 SPEC의 범위를 넘는다 |
| E4 | 저장되는 `bpm`의 출처(REQ-LDBARENTRY-001) | (가) 검출기 값만 쓴다 — 이 경로는 `_song_bpm`을 읽지도 쓰지도 않는다 (나) 감독이 확정한 `_song_bpm`(`session.py:13737`)이 있으면 그 값을 쓴다 (다) 두 값이 허용오차 밖으로 다르면 저장을 거절한다 | (가) | (나): 확정값은 사람이 BPM 배수를 고친 값일 수 있다(`session.py:13752`의 `is_bpm_octave_apart` 분기). 박 격자는 검출기가 만든 것이라 확정 BPM과 격자 간격이 어긋나 E1과 같은 불일치가 생기고, 두 경로(BPM 확정 카드와 마디 지도)가 한 상태를 공유해 REQ-011이 막으려는 결합이 생긴다. (다): 허용오차에 근거가 없고(고른 숫자가 된다), BPM 확정을 거치지 않은 세션은 입구를 못 쓴다. (가): 확정 BPM과 저장 `bpm`이 소수점 이하로 다를 수 있다 — 소비자가 마디 시작을 이 `bpm`으로 계산하므로(P9) 마디가 뒤로 갈수록 어긋남이 쌓인다. 이 어긋남의 크기는 AC-012의 참고 측정(`bar_start_seconds(n)` 대 저장 `start_ms`)이 처음 잰다 — 그 값이 (가)를 다시 따지는 입력이다 |
| E5 | 거절 사유 문장의 자리(REQ-LDBARENTRY-007·012) | (가) 사유 문장은 본문(`text`)에 싣고, `summary`는 성공과 그 밖의 결과를 가르는 고정 라벨로 쓴다 (나) `summary`에 사유 문장을 싣는다 | (가) — 실행 단계에서 확정(2026-10-14, 카드 t647). 근거: base 7cfc80c2의 `server/web/session.py`에서 저장 관문 거절(`:9378-9385`)과 박자 격자 수정 거절(`:9428`)이 같은 모양이다. `summary=` 고정 라벨은 13곳 | (나): 사유 문장이 바뀔 때마다 `summary`가 바뀌어 클라이언트가 성공과 거절을 라벨로 가를 수 없다(REQ-LDBARENTRY-012의 「고정 요약 라벨이 가른다」가 깨진다). 같은 기능의 기존 응답 모양과도 어긋난다 |

## §6. LDARRANGE 매핑

### 6.1 입력 모양 대조 — 생산자는 이미 맞다

`SPEC-LDARRANGE-001` spec.md §5 항목 1(`:142-146`)이 소비자 입력으로 적은 모양을 `server/audio/bar_map_store.py`의 실제 검증과 줄 단위로 맞춰 보았다. **전부 일치한다.**

| 항목 | LDARRANGE 쪽 | `bar_map_store.py` 쪽 | 일치 |
|---|---|---|---|
| 최상위 키 | `schema_version`, `bpm`, `time_signature`, `first_beat_offset`, `bars`, `events` (`:142`) | `_TOP_LEVEL_KEYS` 같은 여섯 개 (`:54-56`) | 예 |
| `bars[]` | `{bar, start_ms, beats_ms}` (`:142`) | `_BAR_KEYS` (`:57`) | 예 |
| `events[]` | `{kind, start_bar, end_bar, start_beat, grade}` (`:142`) | `_EVENT_KEYS` (`:58`) | 예 |
| `kind` 어휘 | `kick_entry`, `build`, `drop`, `break` (`:146`) | `_EVENT_KINDS` (`:45`) | 예 |
| `grade` | `measured`, `estimated` (`:146`) | `_EVENT_GRADES` (`:48`) | 예 |
| 마디 번호 | 1-base, 0 = 못갖춘마디 (`:144`) | 첫 마디는 0 또는 1, 연속 (`:243-252`) | 예 |
| 박자표 | 분자 1~16, 분모 1·2·4·8·16 (`:142`) | `:203-209` | 예 |
| `first_beat_offset` | 0~(분자−1) (`:142`) | `:211-215` | 예 |

스키마를 바꾸지 않는다. 한 가지 차이는 값의 **도달 범위**다. LDARRANGE가 임팩트로 읽는 `kick_entry`·`drop` 사건은 `start_beat`로 마디 안 위치를 갖는데(`SPEC-LDARRANGE-001` `:147`), 이 진입 경로가 만드는 사건은 `start_beat`가 항상 1이다(P10). 보고서가 적은 "67마디 4박에 당겨 들어오는 히트"는 이 경로로는 표현되지 않는다 — 스키마 문제가 아니라 분석기 출력의 한계다.

### 6.2 `SPEC-LDARRANGE-001` §5 열린 결정 4건 — 이 SPEC이 정하는 것

| 항목 | 이 SPEC이 정하는가 | 내용 |
|---|---|---|
| 1. 마디 지도 입력 인터페이스 | **부분적으로 정한다** | 생산자 모양은 이미 확정돼 있어 스키마 변경 0(§6.1). 이 SPEC이 정하는 것은 `REQ-LDARRANGE-001`의 선행 조건이 요구하는 **데이터 공급 경로**뿐이다. 소비자 쪽 공백 (가) "STROBE와 BLIND를 가를 크기 신호가 없다"와 (나) "마지막 코러스라는 이름이 없다"는 **정하지 않는다** — 이 SPEC은 사건에 크기를 싣지 않고 구간 이름도 만들지 않는다 |
| 2. LDBEAT 격자 저장 키(`arrangement_draft`) | **정하지 않는다** | 이 SPEC은 `bar_map` 키 하나만 쓴다(REQ-LDBARENTRY-010) |
| 3. "느린 곡" 기준 | **정하지 않는다** | 느린 곡 플래그를 만들지 않는다(§8) |
| 4. 무대 패치의 배치 영향 | **정하지 않는다** | 이 SPEC은 무대 패치를 읽지 않는다 |

경로가 생겨도 호출하는 클라이언트는 후속 UI 카드이므로, `REQ-LDARRANGE-001`의 근거 칸이 적은 "실제 곡 데이터 부재"는 **UI 카드가 끝나기 전까지는 운영자 관점에서 해소되지 않는다.** 시험 클라이언트나 개발 도구로는 이 SPEC이 끝나면 바로 호출할 수 있다.

## §7. 프로토콜 동결 게이트 결과

읽은 결과이고 시험을 돌린 결과는 아니다.

- **허용 목록**: `server/web/messages.py:116-188`의 `CLIENT_MESSAGE_TYPES`. 파서는 `:389`에서 목록 밖 타입을 거절한다. 새 타입은 이 튜플에 직접 들어가야 한다(별도 `*_MESSAGE_TYPES` 튜플로 두어도 AST 수집이 `*_MESSAGE_TYPES` 이름으로 모으므로 결과는 같다, `test_prechk_tool.py:1417-1426`).
- **동결 튜플**: `server/tests/test_prechk_tool.py:1248-1331`의 `_EXPECTED_CLIENT_MESSAGE_TYPES`. 단언은 `:1499`(`surface.client_message_types == _EXPECTED_CLIENT_MESSAGE_TYPES`), 이 줄이 든 시험은 `TestBoundaryProhibitions.test_the_axis_adds_no_web_surface`(`:1468`, `:1484`)다.
- **판정 방식**: `_scan_web_surface`(`:1438-1465`)가 `server/web/*.py`의 `*_MESSAGE_TYPES` 튜플 원소를 AST로 모아 정렬한다(`:1463`). 그 정렬된 튜플을 리터럴 튜플과 `==`로 비교하므로(`:1499`) **리터럴도 정렬 순서여야 하고**, 허용 목록에만 더하고 동결 튜플에 안 더하면 `:1499`에서 실패한다. 순서가 어긋난 리터럴도 같은 단언에서 실패한다 — 코드를 읽은 추론이다.
- **삽입 자리(정확히)**: `:1249`의 `"approval_decision",` **바로 다음 줄**, 그리고 t551 주석 블록(`:1250-1261`) **앞**이다(`bar` < `beat`). 새 원소와 그 사유 주석을 이 자리에 넣으면 t551 주석 블록이 계속 `beat_grid_apply`(`:1262`)에 붙어 있다. 블록 뒤나 `beat_grid_apply` 아래에 넣으면 정렬이 어긋나거나 t551 주석이 새 원소의 주석처럼 읽힌다. 사유 주석은 `:1250-1261`·`:1267-1270`의 양식(카드 번호, 날짜, SPEC, 콘솔 접촉 여부, "PRECHK/OVERLAP 축과 무관한 정당한 확장" 문장)을 따른다.
- **서버 쪽은 늘지 않는다**: 이 경로의 응답은 기존 `chat_response`(`messages.py:909`)·`song_timeline`(`:1561`)·`error`(`:1168`)·`busy`(`:1173`)뿐이므로 `_EXPECTED_SERVER_MESSAGE_TYPES`(`:1335`)는 그대로다. REST 라우트도 늘지 않는다.
- **동결 스냅샷(2026-10-14 확정)**: 프레임 이름 `bar_map_analyse`와 모양 `{v, type, first_beat_offset}`(정수 `first_beat_offset` 필수, 오디오 바이트 없음)는 이 결정 시점부터 동결이다.
- **D3(나)는 채택하지 않았다(2026-10-14)**: 골랐다면 타입 목록은 그대로이고 동결 시험은 영향이 없지만, `messages.py:731-760`의 파서와 `app.py:760-794`의 분기가 BPM 확정 계약과 같은 곳에서 갈라진다(D3).
- **기록할 선례**: 카드 t551(`beat_grid_edit` 등 편집 세 길), t563(콘솔 버튼 셋), t578, t589, t565, t571.

## §8. 제외 범위 (Out of Scope)

### Out of Scope — 화면 입구와 오프셋 입력

- 마디 지도 분석 버튼, 첫 박 오프셋 입력 칸, 진행 표시, 결과 표시는 후속 UI 카드의 일이다(D4). `ui/src/protocol.ts`에 새 타입을 등록하는 일도 그 카드가 같은 변경에서 한다.
- 오디오를 재생하며 귀로 첫 박을 정하는 화면 흐름.

### Out of Scope — 일반 박자표

- 4/4 밖의 박자표 분석(D2). 분석기 `server/audio/bar_map.py`는 이 SPEC이 수정하지 않는다.

### Out of Scope — 배치 자동 생성과 격자 저장

- `SPEC-LDARRANGE-001`의 생성 로직, `timeline["arrangement_draft"]` 키, `timeline["beat_grid"]` 키는 이 SPEC의 일이 아니다.
- "느린 곡" 플래그, 스트로브 크기 신호, 구간 이름("마지막 코러스" 등)은 만들지 않는다(§6.2).

### Out of Scope — 분석기·저장 스키마 변경

- `detect_beat_grid`·`derive_bars`·`extract_bar_features`·`classify_bar_events`의 수정, 두 배 BPM 판정 재설계, 박 격자 재구성은 하지 않는다(P8의 한계는 E1로 우회한다).
- `validate_bar_map`과 저장 스키마(`schema_version` 1)의 변경, 출처 해시 필드 추가(E3 (나)).
- 자동 위상 선택기(D1 (다)).

### Out of Scope — 콘솔과 라이브러리

- 콘솔 쓰기·읽기, `SongTimelineLibrary` 저장은 하지 않는다. 라이브러리에 남기려면 기존의 별도 저장 경로를 쓴다.
- 이 plan-phase 자신은 문서만 쓴다 — 코드 수정, 시험 실행, 콘솔 접촉, 다른 SPEC 디렉터리 수정 0건.

## §9. Gaps — 확인하지 못한 것

1. **실제 곡의 분석 지연을 재지 않았다.** `detect_beat_grid`와 `extract_bar_features`는 각각 `_decode_mono_audio`로 같은 오디오를 디코드하고(`bar_map.py:229`, `:625`), 앞쪽에는 base64 디코드가 한 번 더 있다. 특징 추출은 STFT 위에서 화성·타악 분리를 돈다(`bar_map.py:650-651`). 전곡 길이에서 걸리는 시간과 메모리는 측정하지 않았다. REQ-LDBARENTRY-005의 근거("오래 걸린다")는 이 구조를 읽은 추정이다.
2. **어떤 시험도 돌리지 않았다.** §7의 "실패한다"는 코드를 읽은 추론이다. 동결 시험, 기존 `test_web_song_audio.py`, `test_session_bar_map_store.py`의 현재 통과 여부도 확인하지 않았다.
3. **감독이 말한 디자인 제안서를 읽지 않았다.** D4에 권고가 없는 이유다.
4. **`store.latest`의 읽기-쓰기 사이는 잠기지 않는 것으로 보인다.** REQ-LDBARENTRY-009의 곡 열쇠 비교는 분석 시작 시점과 저장 시점의 두 점만 비교한다. 저장 관문이 `store.latest`를 읽고(`session.py:9328`) 쓰는(`:9351`) 사이에 HTTP 불러오기(`timeline_api.py:71`)가 끼어들 가능성은 닫지 못했다. 그 좁은 창에 대한 잠금 유무는 확인하지 않았다.
5. **분석 중 WS 연결이 끊기면 어떻게 되는지** 확인하지 않았다. `_send`는 연결이 주입한 콜백(`session.py:4046`)이고 끊긴 뒤의 거동은 읽지 않았다. 새 연결이 붙으면 `app.py:489-491`이 `session.song_timeline_replay()`(`session.py:10206-10218`)를 불러 저장소의 마지막 타임라인을 다시 밀어 준다. 이 메서드는 원본 `latest`에 라이브 송신과 같은 자리(`_beat_grid_refresh_unsent_cells`)에서 파생 필드를 채워 보내므로, 저장된 `bar_map`은 접속 직후 다시 보일 것으로 추정한다 — 시험으로 확인하지 않았다.
6. **두 배 BPM 채택이 실제 곡에서 얼마나 나는지** 이 plan-phase가 다시 재지 않았다. 10곡이 전부 keep이라는 것은 `SPEC-LDBARMAP-001`이 인용한 값이다.
7. **실패 사유가 예외 문구를 그대로 끼운다**(`bar_map.py:192`, `:251`, `:681`). 이를 응답에 그대로 싣는지 정제하는지 이 SPEC은 정하지 않았다. 코드베이스에는 "사용자용 오류는 SDK 원문을 싣지 않는다"는 관행이 있다(`messages.py:1168-1170`의 `error_event` 주석).
8. **알려진 한계(E3, 2026-10-14 확정): 첨부 오디오가 현재 타임라인의 곡과 같은 곡인지 확인하지 않는다.** 확인할 수단도 없다. 오디오는 세션이 들고 다니고 타임라인은 HTTP로 바뀐다. 다른 곡 오디오의 지도를 현재 곡 타임라인에 저장하는 사고는 이 SPEC으로 막히지 않는다.
9. **`ui/src/protocol.ts`는 건드리지 않는다.** 서버에만 있는 타입은 클라이언트에서 부를 수 없다 — 도달 불가능한 상태가 후속 UI 카드 전까지 유지된다. `ui/src/protocol.test.ts:93-96` 주석이 "서버 허용 목록에 등록한 것과 같은 변경에서 여기도 등록한다"고 적었는데 이 SPEC은 그 반대 방향(서버만)의 의도적 예외다.
10. **파일·줄 수 추정(§0)은 코드를 짜 보지 않은 값이다.**
11. **PRESERVE 핀 파일 전체 목록을 확인하지 못했다.** `pyproject.toml:115-125`가 `server/web/preview.py` 하나를 포매터 제외 핀으로 적은 것만 읽었다. 수정 대상 세 파일(`messages.py`·`app.py`·`session.py`)이 바이트 핀 대상인지는 확인하지 않았다.
12. **실기 콘솔 확인은 해당 없음**이다 — 이 SPEC은 콘솔을 만지지 않는다.
13. **응답의 `status` 값 어휘를 확인하지 못했다**(E2는 2026-10-14에 `ok`로 확정됐지만 허용 어휘 전체는 읽지 않았다). 선례가 `"ok"`를 거절에도 쓴다는 것만 읽었다.
14. **실패 처리 시험 경로**(librosa 부재 폴백)는 `server/tests/test_audio_fallback.py`가 판정한다고 `test_audio_bar_map.py:64-67`이 적었다 — 그 파일은 열어 읽지 않았다.
15. **수용한 단순화 (가) — 저장 단계에 잠금이 없다.** 같은 곡을 다시 불러온 경우 곡 열쇠 `(song_title, sequence_number)`가 같아 REQ-LDBARENTRY-009의 대조가 잘못 통과하고, `sequence_number`가 없는 타임라인은 `(제목, None)`으로 겹친다. 비용은 새로 불러온 같은 곡 타임라인에 지도가 저장되는 것인데, 같은 곡이므로 해가 작다고 보고 수용했다. 닫으려면 저장 단계의 읽기-쓰기를 잠그거나 타임라인에 변경 번호를 두어야 한다(이 SPEC 밖).
16. **수용한 단순화 (나) — busy 가드는 같은 WS 연결만 막는다.** 타임라인 저장소는 앱 전체에서 하나다(`server/web/app.py:412` `timeline_store=deps.song_timeline_store`). 다른 연결의 동작이 같은 저장소를 바꿀 수 있고 이 연결의 `current_task`는 그것을 보지 못한다. REQ-009의 곡 열쇠 대조가 유일한 방어다.
17. **`keep` + `ambiguous` 결과는 평범한 성공으로 저장된다**(`bar_map.py:342`, `:384`, `:412`). 위험: 박자가 두 배나 절반일 수 있다는 검출기의 의심이 저장값에 남지 않아, 소비자는 의심 없이 그 `bpm`으로 모든 마디 시작을 계산한다. 수용한 이유: `adopt_double`과 달리 `ambiguous`는 `bpm`이 원래 격자 간격과 같아(`adopted_bpm = raw_bpm`) 저장값이 구조적으로 일관되고, 의심은 음악적인 것이지 데이터가 서로 모순되는 것이 아니다. 닫는 변경: 응답 문구에 `ambiguous`를 싣는 요구사항 한 줄을 더하거나(REQ 상한 16개에 이미 닿아 있어 다른 REQ를 합쳐야 한다), 스키마에 필드를 더하는 것(`schema_version` 상승, 이 SPEC 밖).
18. **다중 연결.** 두 번째 브라우저의 `chat` 등이 같은 타임라인 저장소를 바꿀 수 있고, 그 연결의 `current_task`는 이 연결의 분석 중 상태를 보지 못한다(Gaps 4번, 16번과 같은 뿌리). 분석 중 저장소가 어떻게 바뀌었는지는 곡 열쇠 대조로만 걸러진다.
19. **P7 번호 공간의 실제 분류기 검증**: AC-005는 분류기를 기록용 대역으로 바꿔(특징을 가로채고 마디 하나에 사건을 주입) 특징 번호와 저장 마디 번호의 대응을 CI에서 잰다. 실제 분류기가 실제 오디오에서 낸 사건의 번호가 맞는지는 로컬 전용 AC-016만 잰다.

## as-built 보강 (2026-10-21)

> 이 절은 사후 보강이다. 위 본문(HISTORY·요구사항·제외 범위·Gaps)은 한 글자도 지우거나 고치지 않았다. frontmatter 의 `status`·`version`·`updated` 도 바꾸지 않았다. 출처: SPEC 커버리지 인벤토리(`origin/main` `e4bf3f03`, 2026-10-21)와 코드 판독. 이 SPEC 의 진입 경로에 이후 더해진 동작이다.

1. **마디 지도 꼬리 보정(인벤토리 #859, 커밋 `d719978d`, 2026-10-20).** 박 검출기(`librosa.beat.beat_track`, 기본 `trim=True`)가 끝의 약한 박을 잘라 내 조용한 아웃트로 곡의 마디 지도가 음원 끝보다 한참 앞에서 멈췄다. 이제 합성 단계(`synthesize_bar_map`)가 마디를 만들기 전에 검출된 박을 그대로 두고 마지막 박에서 곡 BPM 간격으로 음원 끝 **앞**까지 박을 이어 붙인다(`server/audio/bar_map.py:extend_beats_to_duration`, `BeatGridResult.duration_ms` 기본값 `None` = 늘리지 않음). 본문 제외 범위가 말한 `detect_beat_grid` 자체의 수정은 아니다 — 검출기는 그대로다. 시험: `server/tests/test_bar_map_covers_audio_tail.py`, `test_audio_bar_map_entry.py`. 현재 동작: `SPEC-LDBEAT-003` REQ-LDBEAT3-014.
2. **분석 중 표시 해제(인벤토리 #860, 커밋 `ab2e82e2`).** 서버가 분석 한 건에 보내는 끝 응답 라벨에 「새 분석으로 새 작업본」·「새 분석 작업본 만들기 실패」가 더해져, 화면 리듀서(`ui/src/components/barMapEntryState.ts`)가 이 둘도 서버 문장을 그대로 보이고 「분석 중」 대기를 푼다. 서버 끝 응답 라벨과 리듀서 라벨의 일치는 경계 계약 시험 `server/tests/test_bar_map_entry_ui_summaries.py` 가 `session.py` 에서 라벨을 모아 맞춘다. 현재 동작: `SPEC-LDBEAT-003` REQ-LDBEAT3-015.
3. **저장 관문의 분기(2026-10-16 추가).** 이 SPEC 이 서술한 「마디 지도를 현재 타임라인에 저장」은 확정 분석이 있는 곡에서는 옛 작업본에 붙지 않고 새 작업본을 연다(`session.py:_start_analysis_timeline` — 구간은 확정 분석 구간, 격자는 빈 격자, 옛 작업본은 라이브러리에 자동 백업, 못 하면 바꾸지 않음). 현재 동작: `SPEC-LDBEAT-003` REQ-LDBEAT3-013.
4. **저장 모양의 선택 키 `rhythm`.** 진입 모듈이 마디 지도 저장 모양에 선택 키 `rhythm`(박·히트·구간 특징)을 붙인다(`server/audio/bar_map_entry.py` → `attach_rhythm`). 필수 키 집합(`schema_version`·`bpm`·`time_signature`·`first_beat_offset`·`bars`·`events`)과 `schema_version` 1 은 그대로이고 모르는 최상위 키는 여전히 거절된다(`server/tests/test_rhythm_features.py`). 현재 동작: `SPEC-LDRHYTHM-002` REQ-LDRHYTHM2-012.
