# SPEC-LDBEAT-003 — 인수 기준 (as-built)

각 AC 는 `AC-LDBEAT3-NNN` 이며 `spec.md` 의 같은 번호 REQ 를 검증한다. 검증은 **저장소에 이미 있는 시험**을 가리킨다. 이 SPEC 을 쓰며 시험을 실행하지는 않았다(`spec.md` §7). 시험이 없는 곳은 「시험 없음」이라고 적었다. 서버 시험은 `server/tests/`, 화면 시험은 `ui/src/`(하위 `components/`, `components/beatgrid/`)에 있다.

## AC-LDBEAT3-001 — 음원 저장소 [REQ-LDBEAT3-001]

- **Given** 경로가 있는 저장소와 경로가 없는 저장소
- **When** 곡 열쇠로 음원을 링크하고 다시 읽으면
- **Then** 링크는 재시작 뒤에도 살아 있고, 모르는 곡은 `none` 이며, 같은 곡의 두 번째 링크는 첫째를 교체하고, 다른 곡은 서로 다른 링크를 가진다. 경로 없는 저장소는 디스크를 건드리지 않고 다른 인스턴스와 상태를 나누지 않는다. 운영 경로는 저장소 밖 사용자 데이터 폴더에 있다.
- **시험**: `test_song_audio_link_store.py`
- **부분 확인**: 해시 불일치·파일 없음 → `missing` 은 `test_web_song_audio_link.py`(`test_a_missing_link_answers_missing_with_no_content`)가 서버 응답 수준에서 덮는다. 같은 바이트 재업로드의 멱등성을 직접 단언하는 시험은 이 SPEC 을 쓰며 이름으로 확인하지 못했다.

## AC-LDBEAT3-002 — 업로드가 곡 열쇠에 묶이는 규칙 [REQ-LDBEAT3-002]

- **Given** 열린 작업본이 있거나 없는 세션, 그리고 열린 작업본이 다른 음원으로 분석된 경우
- **When** 음원을 올리면
- **Then** 곡을 알면 영구 링크가 남고, 곡을 모르면 세션 첨부만 남고 링크는 비며(거절이 아님), 같은 곡의 두 번째 업로드는 링크를 교체한다. 열린 곡이 다른 음원으로 분석된 곡이면 열린 곡의 음원을 덮어쓰지 않고 새 곡을 위한 보관 열쇠에 두며, 분석이 새 작업본을 열 때 그 곡에 묶인다. 분석되지 않은 열린 곡은 예전처럼 업로드를 받는다.
- **시험**: `test_web_song_audio_link.py`, `test_song_audio_other_browser.py`(`test_uploading_a_new_song_does_not_overwrite_the_open_songs_audio`, `test_an_unanalysed_open_song_still_takes_the_upload_as_before`)

## AC-LDBEAT3-003 — 링크 요청 응답 [REQ-LDBEAT3-003]

- **Given** 음원이 링크된 곡, 링크가 덮인 곡, 제목이 바뀐 작업본
- **When** 화면이 `song_audio_link_request` 를 보내면
- **Then** 분석한 음원의 해시로 원래 음원이 찾아져 재생되고 곡 열쇠가 다시 묶이며(LOVE ATTACK 을 열면 원래 음원이 재생·재결합), 다른 브라우저도 분석한 새 곡의 음원을 받는다. 제목이 달라도 격자의 원래 곡 제목 열쇠로 찾고(같은 제목이면 대체 열쇠 없음), 모르는 곡은 `none`, 링크는 있는데 파일이 없으면 `missing`(내용 없음), 작은 링크는 한 프레임, 큰 링크는 분할 프레임으로 답한다.
- **시험**: `test_song_audio_other_browser.py`, `test_song_audio_link_fallback_1016.py`, `test_web_song_audio_link.py`

## AC-LDBEAT3-004 — 화면 음원 자동 연결 [REQ-LDBEAT3-004]

- **Given** 세션 첨부 음원이 있거나 없는 박자 격자 전체화면
- **When** 화면을 열거나 첨부 음원이 바뀌면
- **Then** 첨부가 있고 같은 음원(이름+크기)으로 아직 연결하지 않았으면 자동 연결하고, 첨부가 없으면 서버에 링크를 물으며, 저장된 링크가 없다는 답은 `missing`(「음원 없음」)으로 `idle` 과 구별된다. 서버가 준 base64 는 같은 이름·MIME 의 `File` 이 된다.
- **시험**: `ui/src/components/beatgrid/audioAutoConnect.test.ts`, `songAudioLink.test.ts`, `ui/src/songAudioLinkRequest.test.tsx`

## AC-LDBEAT3-005 — 라이브러리 저장·목록·불러오기·삭제 [REQ-LDBEAT3-005]

- **Given** 현재 작업본이 있거나 없는 서버와 이름 붙은 저장본들
- **When** `/api/timelines` 로 저장·목록·불러오기·삭제를 차례로 부르면
- **Then** 왕복이 보존되고 목록 요약에는 구간 본문이 없으며, 이름이 비었거나 작업본이 없으면 저장이 거절되고, 자동 저장은 이름별로 버전 번호를 매기고 수동 이름이나 삭제로 생긴 빈 번호를 무시한다. 깨진 파일은 빈 라이브러리로 열린다. 화면은 접힌 손잡이에서 개수를 말하고 못 읽었으면 개수를 말하지 않는다.
- **시험**: `test_timeline_library.py`, `ui/src/components/TimelineLibrary.test.tsx`, `ui/src/timelineLibrary.test.ts`

## AC-LDBEAT3-006 — 불러온 곡 제목과 링크 복제 [REQ-LDBEAT3-006]

- **Given** 새 이름으로 불러오는 저장본, 자동 저장 이름의 저장본
- **When** 불러오면
- **Then** 일반 저장본은 저장 이름이 곡 제목이 되고 음원 링크가 새 열쇠에서 찾아지며, 자동 백업을 불러오면 저장된 곡 제목이 유지된다.
- **시험**: `test_timeline_load_audio_link.py`, `test_timeline_library.py`(`test_loading_an_auto_backup_keeps_the_song_title`)

## AC-LDBEAT3-007 — 불러오기 전 백업 [REQ-LDBEAT3-007]

- **Given** 「수정됨 · 미저장」 표식이 있는 작업본, 표식이 없는 작업본, 같은 내용이 이미 저장된 작업본, 백업 쓰기가 실패하는 라이브러리
- **When** 다른 저장본을 불러오면
- **Then** 미저장 작업본은 먼저 자동 백업되고 응답이 백업 항목을 싣는다. 깨끗한 작업본은 백업 없이 교체되고 `no_unsaved_edits` 를 싣는다. 같은 내용의 저장본이 있으면 백업을 또 만들지 않고 `same_as_saved` 와 그 이름을 싣는다. 백업이 실패하면 불러오지 않고 지금 작업본이 그대로다. 막 불러온 판은 미저장 표식이 없다.
- **시험**: `test_timeline_load_unsaved_guard.py`(8개)

## AC-LDBEAT3-008 — 미저장 확인과 안내 [REQ-LDBEAT3-008]

- **Given** 「수정됨 · 미저장」이고 이 창이 마지막으로 저장한 작업본이 아닌 작업본
- **When** 「불러오기」를 누르면
- **Then** 확인 창이 뜨고 취소하면 불러오지 않으며, 이 창이 방금 저장했거나 미저장이 아니면 묻지 않는다. 불러온 뒤 안내는 백업 여부와 건너뛴 이유를 사실대로 말하고, 실패하면 서버가 말한 이유를 그대로 보인다.
- **시험**: `ui/src/timelineLibrary.test.ts`, `ui/src/components/TimelineLibrary.test.tsx`

## AC-LDBEAT3-009 — 응답 파생 필드와 프리셋 기록 이월 [REQ-LDBEAT3-009]

- **Given** 반영 기록이 있는 곡과 다른 작업본의 프리셋 저장 기록
- **When** 저장본을 불러오면(이름이 바뀌어도)
- **Then** 응답의 파생 필드가 새 연결의 재생과 같고, 반영 기록의 콘솔 시퀀스 번호가 보이며, 이름을 바꿔 불러와도 다른 곡의 번호를 빌리지 않고, 지금 작업본의 콘솔 프리셋 저장 기록이 새 판에 이월된다.
- **시험**: `test_timeline_load_derived_t644.py`, `test_timeline_load_seq_no.py`, `test_preset_reuse_after_library_load.py`

## AC-LDBEAT3-010 — 불러온 뒤 재연결 [REQ-LDBEAT3-010]

- **Given** 불러오기 결과가 있거나 없는 경우
- **When** `reconnectAfterTimelineLoad` 가 불리면
- **Then** 결과가 있으면 재연결이 정확히 한 번 불리고 `true`, 결과가 없으면(`null`) 한 번도 불리지 않고 `false` 이다.
- **시험**: `ui/src/timelineLoadReconnect.test.ts`(2개)
- **부분 확인**: 의도한 재연결이 끊김 배너를 건너뛴다는 부분은 `ui/src/useCopilotSocket.test.ts` 가 `closeFollowUp` 을 다루는 것으로 보이나 이 SPEC 을 쓰며 단언 내용을 읽지는 않았다.

## AC-LDBEAT3-011 — 재접속 뒤에도 남는 상태 [REQ-LDBEAT3-011]

- **Given** 한 저장소를 공유하는 재접속 전·후의 두 세션
- **When** 앞 세션이 「콘솔에 반영」을 마친 뒤 새 세션이 같은 저장소 위에서 「끄기」·「미리보기」를 보내면
- **Then** 새 세션이 반영한 시퀀스·큐 번호를 알아 `Off Sequence`·`Goto Cue` 를 보낸다. 칸 기록 스냅샷과 풀 판독 기억도 재접속 뒤 남는다.
- **시험**: `test_beat_grid_reconnect_t642.py`, `test_beat_grid_field_life_t651.py`, `test_web_first_connect_apply_t635.py`
- **시험 없음**: 서버를 다시 띄운 뒤 파일 저장분(작업본·세트리스트·반영 소유 기록)이 복원되는지를 이름으로 단언하는 시험은 이 SPEC 을 쓰며 확인하지 못했다.

## AC-LDBEAT3-012 — 확인 카드 중복 방지 [REQ-LDBEAT3-012]

- **Given** 답이 정해진 물음, 답 없이 남은 물음, 같은 묶음의 새 곡 분석 확인 카드
- **When** 새 연결이 붙거나 새 카드가 서면
- **Then** 답이 정해진 물음은 다시 오지 않고, 답 없는 물음은 연결마다 정확히 한 장 오며, 새 카드가 서면 옛 카드는 거둬져 화면에서도 닫히고 옛 분석은 BPM·구간 기록을 쓰지 않는다. 거둠을 끄면 시험 세 개가 빨개진다고 커밋 메시지가 적었다.
- **시험**: `server/tests/test_web_question_supersede.py`

## AC-LDBEAT3-013 — 새 분석으로 새 작업본 [REQ-LDBEAT3-013]

- **Given** 확정 분석이 있는 곡에서 끝난 마디 지도 분석
- **When** `_start_analysis_timeline` 이 새 작업본을 열면
- **Then** 새 작업본은 분석 구간·마디 지도·빈 격자로 시작하고 같은 분석을 두 번 시작하지 않으며, 다시 확정한 같은 곡은 새로 시작한다. 구간에는 큐 번호가 실리고 BPM 은 마디 지도에서 보충된다(`test_bpm_falls_back_to_the_bar_map`). 같은 곡의 새 작업본은 콘솔 반영 소유를 이어받고 다른 곡은 아무것도 이어받지 않는다(소유 기록 기준). 자동 배치가 빈 격자에 칸을 놓는다. 바뀐 것이 없는 적용은 실패로 보고된다. 백업이 실패하면 새 작업본으로 바꾸지 않는다.
- **시험**: `test_new_analysis_timeline.py`, `test_analysis_timeline_meter.py`, `test_preset_reuse_after_new_analysis.py`, `test_preset_reuse_cross_song.py`
- **부분 확인**: 「백업 실패 → 새 작업본으로 바꾸지 않음」 분기를 직접 단언하는 시험은 이 SPEC 을 쓰며 이름으로 확인하지 못했다.

## AC-LDBEAT3-014 — 마디 지도가 음원 끝까지 덮는다 [REQ-LDBEAT3-014]

- **Given** 클릭 20초 + 무음 20초 합성 음원(검출기가 끝 박을 잘라 내는 경우)
- **When** 마디 지도를 만들고 격자·타임코드·화면이 그것을 읽으면
- **Then** 마디 지도가 음원 끝에 닿고, 검출된 박은 그대로 유지된 채 꼬리가 곡 BPM 으로 이어지며, 타임코드 `Duration` 이 음원 끝에 닿고, 분석 작업본의 마지막 구간이 음원 끝까지의 마디를 가지고, 화면 마디 수가 전체 마디 지도를 따른다. 확장은 음원 끝을 넘지 않고, 확장할 수 없거나 필요 없으면 격자를 건드리지 않는다.
- **시험**: `test_bar_map_covers_audio_tail.py`(8개), `test_audio_bar_map_entry.py`

## AC-LDBEAT3-015 — 분석 중 표시가 풀린다 [REQ-LDBEAT3-015]

- **Given** 「분석 중」 대기 상태의 마디 지도 진입 컨트롤
- **When** 서버의 끝 응답(저장, 분석 거절, 저장 거절, 저장 불가, 새 분석으로 새 작업본, 새 분석 작업본 만들기 실패)이 오면
- **Then** 대기가 끝나고 서버 문장이 그대로 보인다(저장 성공만 고정 문구). 취소 뒤에 온 결과도 마찬가지다. 분석 한 건이 지나는 세 메서드의 끝 응답 라벨은 모두 리듀서가 아는 라벨에 들어 있다.
- **시험**: `ui/src/components/barMapEntryState.test.ts`, `server/tests/test_bar_map_entry_ui_summaries.py`

## Definition of Done (as-built)

- [x] 요구사항 15개가 코드 `파일:함수` 로 추적된다(`spec.md` §3).
- [x] AC 15개가 존재하는 시험 파일에 대응한다. 직접 단언을 확인하지 못한 곳은 「부분 확인」·「시험 없음」으로 적었다.
- [ ] 위 시험들을 `origin/main` `e4bf3f03` 이후 트리에서 실행한 통과 증거 — 이 SPEC 에는 없다. 후속 sync 검증 몫이다.
- [ ] 실기 브라우저·콘솔 확인 — 이 SPEC 은 대체하지 않는다.
