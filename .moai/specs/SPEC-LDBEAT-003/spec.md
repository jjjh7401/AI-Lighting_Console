---
id: SPEC-LDBEAT-003
title: "작업본·음원 수명주기 — 곡을 열면 소리와 격자가 같이 온다 (as-built)"
version: "0.1.0"
status: implemented
created: 2026-10-21
updated: 2026-10-21
author: jaihyun
priority: P2
phase: "Lighting Copilot v1.2 target"
module: "server/web/song_audio_store.py, server/web/timeline_library.py, server/web/timeline_api.py, server/web/question.py, server/web/session.py(SongTimelineStore·request_song_audio_link·_start_analysis_timeline), server/design/analysis_timeline.py, server/audio/bar_map.py(extend_beats_to_duration), server/audio/bar_map_entry.py, ui/src/components/TimelineLibrary.tsx, ui/src/timelineLibrary.ts, ui/src/timelineLoadReconnect.ts, ui/src/components/barMapEntryState.ts, ui/src/components/beatgrid/(songAudioLink·audioAutoConnect)"
lifecycle: spec-anchored
tags: "as-built, timeline-library, song-audio-link, unsaved-guard, reconnect, analysis-working-copy, bar-map-tail"
tier: M
related_specs: [SPEC-LDBEAT-001, SPEC-LDBEAT-002, SPEC-LDRHYTHM-002, SPEC-LDBARMAP-001, SPEC-LDBARMAP-002, SPEC-LDBARMAP-003]
---

# SPEC-LDBEAT-003 — 작업본·음원 수명주기 (as-built)

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-21 | 최초 작성. **as-built SPEC** — 이미 출하된 동작을 사후에 문서로 닫는다. 새 요구사항이 아니라 `origin/main` `e4bf3f03` 코드에서 읽은 현재 동작이다. 입력: SPEC 커버리지 인벤토리 클러스터 C7(음원 링크)·C8(작업본 라이브러리·불러오기·재접속)·C9 중 마디 지도 꼬리와 분석 중 표시. 인벤토리 §3.4 가 이름도 태그도 없는 파일로 꼽은 `TimelineLibrary.tsx`(237줄)·`timelineLoadReconnect.ts`(9줄)가 여기서 파일 단위로 추적된다. 한 사용자 흐름 — 「곡을 열면 소리와 격자가 같이 온다」 — 으로 묶었다. 코드·시험·UI·콘솔·서버 런타임은 바꾸지 않았다. |

## §0. as-built SPEC 읽는 법

1. 요구사항은 현재 동작의 기술이다. 「코드 근거」는 이 SPEC 을 쓰며 읽은 `파일:함수`, 「시험」은 저장소에 있는 시험 파일이다. 시험이 없으면 「시험 없음」이다.
2. 「소스 PR」은 인벤토리 §4.2 값이다. 머지 커밋을 직접 확인한 것은 #860(`75039bd7`), #863(`0ddae3d2`), #864(`ef61869a`)뿐이다. 마디 지도 꼬리 수정은 커밋 `d719978d` 를 직접 읽었으나 그것이 #859 의 머지에 들어 있는지는 확인하지 않았다.
3. 인벤토리와 코드가 달랐던 곳은 §6 에 적었다. 둘이 다르면 코드를 따랐다.
4. 시험을 실행하지 않았다. 「시험」 열은 존재 증거이지 통과 증거가 아니다(§7).

## §1. 범위와 소스 PR

| 클러스터 | 다루는 동작 | 소스 PR(인벤토리 §4.2) |
|---|---|---|
| C7 음원 링크 | 곡 음원을 곡 열쇠에 영구 보관, 다른 브라우저·재시작 뒤에도 재생, 제목이 바뀐 작업본도 원래 곡 열쇠로 찾기 | #755 #776 #779 #825 |
| C8 작업본 라이브러리·불러오기·재접속 | 이름·버전 저장본, 미저장 작업본 보호, 불러온 뒤 상태 재수신, 재접속에서 살아남는 상태 | #684 #751 #756 #759 #863 + 직계 #689 #692 + 직계 `0a573071` |
| C9 곡 끝·마디 지도 꼬리 (이 SPEC 이 맡는 쪽) | 마디 지도가 음원 끝까지 덮기, 분석 중 표시 해제 | #859 #860 (곡 끝 조명 규칙은 `SPEC-LDRHYTHM-002`) |

## §2. 배경

감독은 곡을 분석하고, 격자를 고치고, 작업본을 저장하고, 다른 날 다시 열고, 다른 브라우저로 본다. 그때마다 (가) 같은 곡의 음원이 따라와야 하고, (나) 저장하지 않은 수정이 말없이 사라지면 안 되고, (다) 새로고침·재접속 뒤에도 콘솔 반영 기록과 화면 값이 맞아야 한다. 이 셋이 카드 단위로 하나씩 고쳐지며 쌓였고 어느 SPEC 도 이를 서술하지 않았다.

## §3. 요구사항 (GEARS, 현재 동작)

주체 표기: 「서버」는 `server/web/session.py` 의 `ChatSession`, 「화면」은 `ui/src/` 의 순수 함수와 컴포넌트.

### 3.1 R1 — 곡 음원 링크 (REQ-LDBEAT3-001~004)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDBEAT3-001 | **The** 곡별 음원 저장소 **shall** 음원 바이트를 내용 주소(`sha256` + 원본 확장자)로 보관하고, 「이 곡 → sha256·파일 이름·MIME」 색인을 작은 JSON 리스트로 둔다. 곡 열쇠는 새 id 체계가 아니라 `(song_title, sequence_number)` 쌍이다. 같은 바이트가 다시 올라오면 이미 있는 파일을 건드리지 않아 쓰기가 멱등이고, 같은 곡의 두 번째 링크는 첫째를 교체하며, 색인·파일 쓰기는 같은 디렉터리 임시 파일 + `os.replace` 이다. 읽을 때 색인이 깨졌거나 파일이 없거나 해시가 맞지 않으면 예외 대신 `missing` 을 돌려주고(콘솔에는 영향이 없다), 경로가 없는 인스턴스는 메모리 전용이며 다른 인스턴스와 상태를 나누지 않는다. 운영 경로는 저장소 밖 사용자 데이터 폴더다. | `server/web/song_audio_store.py:SongAudioLinkStore.link`, `resolve`, `resolve_sha`, `_resolve_entry`, `_persist_index` | `server/tests/test_song_audio_link_store.py` |
| REQ-LDBEAT3-002 | **When** 감독이 곡 음원을 올리면, 서버 **shall** 세션 첨부를 끝낸 뒤 지금 곡을 알면 그 곡 열쇠로 영구 링크를 남긴다. 곡을 모르거나 쓰기가 실패해도 세션 첨부·분석·확정 경로는 그대로 동작한다(링크만 조용히 빈다). **If** 열린 작업본이 다른 음원(해시가 다른)으로 분석한 곡이면, 이 업로드는 새 곡의 음원이므로 앞 곡의 열쇠를 덮어쓰지 않고 곡이 없는 보관 열쇠(`UNBOUND_SONG_KEY`)에 둔다. 분석이 새 작업본을 열 때 그 곡에 묶는다. | `session.py`(음원 업로드 처리, `_current_song_audio_key`, `_open_song_was_analysed_from_other_audio`, `_link_session_audio_to_open_song`) | `server/tests/test_web_song_audio_link.py`, `test_song_audio_other_browser.py` |
| REQ-LDBEAT3-003 | **When** 화면이 곡 음원 링크를 요청하면(`song_audio_link_request`), 서버 **shall** 열린 작업본이 분석한 음원의 해시가 있으면 그 해시로 먼저 찾고(`resolve_sha`), 곡 열쇠가 다른 음원을 가리키거나 비어 있으면 분석 음원으로 다시 묶는다(쓰기가 실패해도 이번 재생은 해시로 찾은 음원으로 간다). 못 찾으면 곡 열쇠로, 그다음 격자가 기억하는 원래 곡 제목 열쇠로 한 번 더 찾는다(불러오기가 제목을 저장 이름으로 바꿔도 링크가 안 끊기게). 답은 `none`(곡을 모르거나 저장소 없음)·`missing`(색인은 있는데 파일 없음·해시 불일치)·`found` 셋 중 하나이고, `found` 가 한 프레임 한도(`MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH`)를 넘으면 업로드와 같은 분할 프레임을 반대 방향으로 낸다. | `session.py:request_song_audio_link`, `_song_audio_fallback_key`; `song_audio_store.py:resolve_sha` | `test_song_audio_other_browser.py`, `test_song_audio_link_fallback_1016.py`, `test_web_song_audio_link.py` |
| REQ-LDBEAT3-004 | **The** 화면 **shall** 세션에 첨부된 음원이 있으면 박자 격자 전체화면을 열 때 자동 연결하고(이름+크기로 같은 음원을 식별해 같은 음원으로 반복 연결하지 않는다), 첨부가 없으면 서버에 링크를 물어 상태를 `idle → loading → connected / failed / missing` 으로 옮긴다. `missing` 은 「확인해 봤는데 이 곡엔 저장된 링크가 없다」는 뜻이라 `idle` 과 다르게 「음원 없음」으로 보인다. 서버가 돌려준 base64(단일 프레임이든 분할 조립 결과든)는 `File` 로 되돌려 쓴다. | `ui/src/components/beatgrid/audioAutoConnect.ts:shouldAutoConnectAudio`, `audioSourceId`; `songAudioLink.ts:buildFileFromSongAudioLink` | `ui/src/components/beatgrid/audioAutoConnect.test.ts`, `songAudioLink.test.ts`, `ui/src/songAudioLinkRequest.test.tsx` |

### 3.2 R2 — 작업본 라이브러리와 불러오기 (REQ-LDBEAT3-005~010)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDBEAT3-005 | **The** 작업본 라이브러리 **shall** 이름 붙인 저장본(항목 하나가 `_song_timeline_payload` 투영 전체 + id·이름·저장 시각)을 저장·목록·불러오기·삭제하는 REST(`/api/timelines`)로 노출한다. 같은 이름이 여러 번 나올 수 있다 — 이름은 곡이고 항목은 버전이다. 목록은 구간 본문 없는 요약만 낸다. 이름이 비었거나 저장할 작업본이 없으면 400, 없는 항목은 404 다. 자동 저장은 `<이름> (자동 vN)` 으로 이름별 버전 번호를 매기고, 쓰기는 원자적이며 읽기가 깨져 있으면 빈 라이브러리로 열린다(fail-open). 이 길은 콘솔 명령을 보내지 않는다 — 불러오기는 검토용 투영을 현재 작업본으로 바꿀 뿐이다. 화면은 접힌 손잡이에서도 저장본 개수를 말하되 못 읽었으면 개수를 꾸미지 않는다. | `server/web/timeline_library.py:SongTimelineLibrary`; `server/web/timeline_api.py:build_timeline_router`; `ui/src/components/TimelineLibrary.tsx:TimelineLibraryView` | `server/tests/test_timeline_library.py`, `ui/src/components/TimelineLibrary.test.tsx`, `ui/src/timelineLibrary.test.ts` |
| REQ-LDBEAT3-006 | **When** 저장본을 불러오면, 서버 **shall** 저장 이름을 곡 제목으로 쓴다. 단 저장 이름이 자동 저장 꼬리(`… (자동 vN)`)를 가졌고 저장된 곡 이름이 비지 않았으며 일반 설계 이름(`Design Interview`)이 아니면 저장된 곡 이름을 그대로 둔다. 곡 열쇠가 바뀌면(제목이 달라지면) 옛 열쇠의 음원 링크를 새 열쇠로 복제하고 옛 열쇠는 지우지 않으며, 링크가 없거나 쓰기가 실패하면 조용히 넘긴다. | `timeline_api.py:load_timeline`(`_AUTO_SAVE_NAME`, `_DESIGN_INTERVIEW_TITLE`, `links.link`) | `test_timeline_library.py`(`test_loading_an_auto_backup_keeps_the_song_title`), `test_timeline_load_audio_link.py` |
| REQ-LDBEAT3-007 | **When** 저장하지 않은 수정(`draft.dirty`)이 있는 작업본 위에 다른 저장본을 불러오면, 서버 **shall** 먼저 지금 작업본을 `<곡> 불러오기 전 백업 (자동 vN)` 으로 라이브러리에 남기고, 못 남기면(`OSError`·`ValueError`) 불러오지 않고 500 `backup_failed` 를 돌려주며 지금 작업본은 그대로다. 백업하지 않는 이유는 응답에 싣는다 — 저장하지 않은 수정이 없으면 `{reason: "no_unsaved_edits"}`, 같은 내용의 저장본이 이미 있으면 `{reason: "same_as_saved", saved_as: <이름>}`, 백업했으면 `null`. 막 불러온 판은 저장본 그대로이므로 저장 때 같이 담긴 「미저장」 표식(`draft`)을 떼어 낸다. | `timeline_api.py:_backup_skip_reason`, `load_timeline`; `timeline_library.py:auto_save` | `server/tests/test_timeline_load_unsaved_guard.py` |
| REQ-LDBEAT3-008 | **When** 감독이 「불러오기」를 누르면, 화면 **shall** 지금 작업본이 「수정됨 · 미저장」이고 이 창이 마지막으로 저장한 작업본이 아닐 때만 확인 창을 띄운다(`confirmLoadIfUnsaved`). 불러온 뒤에는 서버가 백업했는지 건너뛰었는지(이유 포함)를 안내하며 백업했다고 거짓으로 말하지 않고, 서버가 새로 만든 백업 항목이 있으면 목록을 새로 읽는다. 불러오기가 실패하면 서버가 말한 이유(`backup_failed` 등)를 일반 문구 대신 그대로 보인다. | `ui/src/timelineLibrary.ts:confirmLoadIfUnsaved`, `timelineLoadedNotice`, `parseTimelineLoadBackupSkip`, `parseTimelineLoadError`; `TimelineLibrary.tsx:handleLoad` | `ui/src/timelineLibrary.test.ts`, `ui/src/components/TimelineLibrary.test.tsx` |
| REQ-LDBEAT3-009 | **The** 불러오기 응답 **shall** 새 연결의 재생(`song_timeline_replay`)과 같은 함수로 파생 필드를 채운다 — 화면용 값(`attach_beat_grid_ui_values`), 반영 기록의 콘솔 시퀀스 번호(이름을 바꾼 **뒤의** 타임라인으로 읽음), 칸 기록·풀 기억·반영 소유 여부(`derive_beat_grid_fields`), 화면 머리말(`fill_bar_map_header`). 이 요청은 콘솔을 읽지 않는다. **When** 옛 저장본을 불러와도, 서버 **shall** 지금 작업본 격자의 콘솔 프리셋 저장 기록을 새 판에 이월한다(`carry_console_preset_records`) — 프리셋 저장 기록은 작업본이 아니라 콘솔의 사실이므로 버리지 않는다. 곡을 열면 장비 판독 예열 훅(`on_open`)을 부른다. | `timeline_api.py:load_timeline`; `server/design/analysis_timeline.py:carry_console_preset_records`; `server/design/beat_grid_ui_values.py:attach_beat_grid_ui_values` | `test_timeline_load_derived_t644.py`, `test_timeline_load_seq_no.py`, `test_preset_reuse_after_library_load.py` |
| REQ-LDBEAT3-010 | **When** 불러오기가 성공하면, 화면 **shall** 연결을 정확히 한 번 다시 맺어 세션 값(줄 머리 `sub_info` 등 — 불러오기 응답에는 없고 연결할 때 서버가 다시 보낸다)을 받는다. 결과가 없는 불러오기(실패)는 연결을 건드리지 않는다. 의도한 재연결은 「서버 연결 끊김」 배너와 소켓 끊김 콜백을 건너뛰고 대기 중 승인 카드 정리는 그대로 둔다(서버가 끊기면 대기 승인을 자동 거부하므로). | `ui/src/timelineLoadReconnect.ts:reconnectAfterTimelineLoad`; `ui/src/useCopilotSocket.ts`(`closeFollowUp`) | `ui/src/timelineLoadReconnect.test.ts`, `ui/src/useCopilotSocket.test.ts` |

### 3.3 R3 — 재접속에서 살아남는 상태 (REQ-LDBEAT3-011~012)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDBEAT3-011 | **The** 서버 프로세스 단위 저장소(`SongTimelineStore`)는 재접속·새로고침·두 번째 탭이 같은 값을 보게 한다. 파일에 저장되는 것(원자적 쓰기)은 현재 작업본, 세트리스트, 곡별 반영 소유 기록(`beat_grid_allocations`)이다. 파일에 저장되지 않고 서버를 다시 띄우면 사라지는 것은 「콘솔에 반영」 스냅샷(곡별 칸 기록), 콘솔 프리셋 풀의 마지막 완전 판독과 그 시각, 가장 최근 반영이 쓴 시퀀스·큐 번호이다 — 그래서 재접속해도 「끄기」·「미리보기」가 같은 번호를 쓰고 격자의 「빈 프리셋」 표식이 사라지지 않는다. 미리보기·재생과 칸 편집 즉시 반영의 세션 1회 승인도 연결이 아니라 서버 프로세스 단위로 기억한다. | `session.py:SongTimelineStore`(`_save`, `beat_grid_snapshots`, `beat_grid_pool_slots`, `beat_grid_pool_read_at`, `beat_grid_applied`, `preview_approval`, `cell_live_approval`) | `server/tests/test_beat_grid_reconnect_t642.py`, `test_beat_grid_field_life_t651.py`, `test_web_first_connect_apply_t635.py` |
| REQ-LDBEAT3-012 | **The** 확인 카드(물음) **shall** 답이 정해진 뒤에는 재접속 재생 목록에서 곧바로 빠지고, 답 없이 남은 물음은 새 연결마다 정확히 한 장만 다시 온다. 곡 분석 확인 카드는 묶음(`SONG_CONFIRMATION_GROUP`)으로 묶여, 같은 묶음의 새 카드가 서면 답 없이 남은 옛 카드는 `SUPERSEDED` 로 거둬지고 화면에서도 `question_resolved` 로 닫힌다. 옛 분석은 그 답을 받아 BPM·구간 기록을 쓰지 않고 끝난다. | `server/web/question.py`(`SUPERSEDED`, `SONG_CONFIRMATION_GROUP`); `session.py` | `server/tests/test_web_question_supersede.py` |

### 3.4 R4 — 분석이 여는 새 작업본과 마디 지도 꼬리 (REQ-LDBEAT3-013~015)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDBEAT3-013 | **When** 확정 분석이 있는 곡에서 마디 지도 분석이 끝나면, 서버 **shall** 마디 지도를 옛 작업본에 붙이지 않고 새 작업본을 연다 — 곡 이름은 새로 붙인 오디오의 파일 이름(확장자 뗀 것)에서 오고, 구간은 확정 분석 구간이며, 줄 구성은 비어 있다(자동 배치가 콘솔 그룹으로 만든다). 옛 작업본을 `<곡> 분석 전 백업` 으로 라이브러리에 먼저 남기고, 못 남기면 새 작업본으로 바꾸지 않으며 마디 지도도 저장하지 않는다(되돌리기 기록은 메모리에만 있어서). 같은 곡의 새 작업본은 직전 작업본의 반영 소유 기록을 이어받고 다른 곡이면 이어받지 않는다. 콘솔 프리셋 저장 기록은 곡이 아니라 콘솔의 사실이라 다른 곡이어도 이어받는다. 분석한 음원을 새 작업본의 곡에 묶는다. 응답 `chat_response` 는 정확히 한 개이고 콘솔에는 아무것도 쓰지 않는다. | `session.py:_start_analysis_timeline`, `_same_song_working_copy`; `server/design/analysis_timeline.py:build_analysis_timeline`, `section_kinds_from_bar_map`, `timeline_meter_from_bar_map` | `server/tests/test_new_analysis_timeline.py`, `test_analysis_timeline_meter.py`, `test_preset_reuse_after_new_analysis.py`, `test_preset_reuse_cross_song.py` |
| REQ-LDBEAT3-014 | **The** 마디 지도 합성 **shall** 검출된 박은 그대로 두고 마지막 박에서 곡 BPM 간격(`60000 / bpm` ms)으로 음원 끝 **앞**까지 박을 이어 붙인 뒤 마디를 만든다. 박 검출기가 끝의 약한 박을 잘라 내는 조용한 아웃트로 곡에서 마디 지도·배치 격자의 마지막 구간·콘솔 타임코드 `Duration`(마지막 마디 끝)·화면 재생 끝이 음원 끝에서 멈추지 않게 하기 위해서다. 박이 없거나 BPM·음원 길이를 모르면 늘리지 않고(길이 기본값 `None`), 끝을 넘는 박은 만들지 않는다. | `server/audio/bar_map.py:extend_beats_to_duration`, `BeatGridResult.duration_ms`, `synthesize_bar_map`; `server/audio/bar_map_entry.py` | `server/tests/test_bar_map_covers_audio_tail.py`, `test_audio_bar_map_entry.py` |
| REQ-LDBEAT3-015 | **When** 마디 지도 분석 한 건이 끝나면, 화면 **shall** 서버가 보내는 끝 응답 라벨 전부 — 저장(`마디 지도 저장`), 분석 거절, 저장 거절, 저장 불가, 새 분석으로 새 작업본, 새 분석 작업본 만들기 실패 — 에서 「분석 중」 대기를 풀고 서버 문장을 그대로 보인다(저장 성공만 고정 문구). 화면 리듀서가 아는 라벨이 서버가 분석 한 건이 지나는 세 메서드의 끝 응답 라벨을 모두 덮는지는 경계 계약 시험이 `session.py` 에서 라벨을 모아 맞춘다. | `ui/src/components/barMapEntryState.ts`(`SUMMARIES_SHOW_SERVER_TEXT`); `session.py`(끝 응답 라벨) | `ui/src/components/barMapEntryState.test.ts`, `server/tests/test_bar_map_entry_ui_summaries.py` |

## §4. 제외 범위

### Out of Scope — 새 동작과 코드 변경

- 이 SPEC 은 사후 기록이다. 코드·시험·UI·콘솔·서버 런타임을 바꾸지 않는다.

### Out of Scope — 다른 SPEC 이 맡는 동작

- 콘솔 반영·소유 기록 사용·「콘솔 같이」·칸 편집은 `SPEC-LDBEAT-002` 가 맡는다.
- 프리셋 계획·재사용 판정 자체와 곡 끝 조명 규칙은 `SPEC-LDRHYTHM-002` 가 맡는다. 이 SPEC 은 기록 이월(REQ-LDBEAT3-009·013)만 다룬다.
- 마디 지도 검출·저장 모양·진입 경로·진입 화면은 `SPEC-LDBARMAP-001`·`-002`·`-003` 이 맡는다. 이 SPEC 은 그 꼬리 합성과 대기 해제만 다룬다.
- 타임라인 라이브러리 패널의 최초 도입(2026-08-14)과 `CueMonitor` 등은 `SPEC-COPILOT-ASBUILT-001` 이 짧게 기록한다.

## §5. 알려진 한계 (코드에서 읽은 것)

1. 음원 저장소는 곡 열쇠가 `(song_title, sequence_number)` 이므로 제목이 바뀌면 열쇠가 달라진다. 이를 막는 것은 불러오기의 링크 복제(REQ-LDBEAT3-006)와 원래 제목 열쇠 대체 조회(REQ-LDBEAT3-003)이며, 그 밖의 경로로 제목이 바뀌는 경우는 이 조사에서 따라가지 않았다.
2. 「콘솔에 반영」 스냅샷·풀 판독·반영 번호는 파일에 저장되지 않아 서버를 다시 띄우면 사라진다(REQ-LDBEAT3-011). 칸 단위 반영은 이때 소유 기록 기준으로 떨어진다(`SPEC-LDBEAT-002` REQ-LDBEAT2-008).
3. 보류 초안(자동 배치)은 재연결하면 버려진다(`SPEC-LDRHYTHM-002` REQ-LDRHYTHM2-011).

## §6. 인벤토리와 코드가 달랐던 곳

| 인벤토리 서술 | 코드에서 읽은 것 |
|---|---|
| C8 「재접속 때 보류 카드·빈 프리셋 표식이 사라지지 않게 한다」(직계 #689·#692) | 이 조사는 #689·#692 커밋을 직접 확인하지 못했다. 코드에서 읽은 재접속 수명은 REQ-LDBEAT3-011(빈 프리셋 표식=풀 판독 기억)과 REQ-LDBEAT3-012(확인 카드, `622187fb`)다. 둘이 #689·#692 와 일대일인지는 모른다. |
| `TimelineLibrary.tsx` 를 「무이름·무태그」로 분류 | 인벤토리 §4.2 C8 열은 `SPEC-LDBEAT-001` REQ-006·`SPEC-LDBARMAP-001` 이 라이브러리를 저장소 개념으로 서술한다고 적었다(이 조사는 그 문서들을 다시 읽지 않았다). 이 SPEC 이 이 화면 파일의 동작을 처음 `파일:함수` 단위로 적는다. |

## §7. 검증하지 못한 것

- 시험을 실행하지 않았다. 「시험」 열은 `ls`·`grep` 으로 존재와 이름을 확인한 것이다.
- 실기 브라우저·콘솔 동작은 확인하지 않았다.
- 소스 PR 번호는 인벤토리 값이며 위 §0 에 적은 것만 머지 커밋을 확인했다.
- `session.py` 는 인용한 함수·구간만 읽었다.
