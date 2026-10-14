# t642 수정 기록 — 재연결 뒤에도 끄기·미리보기가 반영 번호를 쓰게 함

카드 t642 · 브랜치 WT-beat-grid-reconnect · 수정 커밋 2d5be6d9 · 기준 origin/main 7cfc80c2 (카드 브랜치에 합친 머지 커밋 0ba1af82)

## 1. 주장

재연결(새 WebSocket)을 하면 새 ChatSession 이 만들어지고, 그 세션의 「반영 번호」는 비어 있었다. 그래서 끄기와 미리보기가 「아직 콘솔에 반영된 적이 없다」며 거절했다. 번호를 프로세스 단위인 SongTimelineStore 로 옮겨서, 재연결 뒤에도 같은 번호로 Off Sequence 와 Goto Cue 를 낸다. RED 시험 3건이 모두 초록이다.

## 2. 증거

명령 1 (RED 시험, 이번 실행):

    unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && uv run pytest -v -rs server/tests/test_beat_grid_reconnect_t642.py; echo "exit=$?"

관측 (발췌):

    test_off_after_reconnect_still_turns_off_applied_sequences PASSED
    test_preview_after_reconnect_still_goes_to_applied_cues PASSED
    test_off_in_same_session_after_apply_control PASSED
    ============================== 3 passed in 0.43s ===============================
    exit=0

명령 2 (관련 시험, 이번 실행):

    unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && uv run pytest -q -rs server/tests/test_beat_grid_send_t563.py server/tests/test_web_beat_grid_send_t563.py server/tests/test_beat_grid_reapply_t572.py server/tests/test_beat_grid_console_play_t578.py server/tests/test_web_beat_grid_console_play_t578.py server/tests/test_write_dispatch_census.py server/tests/test_web_first_connect_apply_t635.py; echo "exit=$?"

관측:

    80 passed, 1 skipped, 1 warning in 4.27s
    exit=0

- 건너뜀 1건: server/tests/test_write_dispatch_census.py:387. 「WRITE_WITHOUT_SEAM_DISPATCHES 가 비어 있다」는 기존 건너뜀이다. 같은 파일의 두 census 검사(test_no_dispatch_site_is_unregistered, test_each_showfile_write_site_has_a_seam_in_its_function)는 이 실행에서 통과했다.
- 경고 1건: starlette testclient 의 httpx 사용 중단 경고(기존 경고).

명령 3 (린트, 같은 파일):

    uv run ruff check server/web/session.py       → All checks passed!            (exit=0)
    uv run ruff format --check server/web/session.py → 1 file already formatted   (exit=0)

## 3. 기준선 귀속

- 브랜치: WT-beat-grid-reconnect. 기준은 origin/main 7cfc80c2이고, 카드 브랜치에는 머지 커밋 0ba1af82로 합쳤다.
- 수정 커밋 2d5be6d9: server/web/session.py 한 파일, 25 insertions(+), 11 deletions(-). 테스트 파일은 건드리지 않았다.
- 같은 트리에서 RED 시험은 수정 전에 2 failed, 1 passed(exit=1)였고, 수정 뒤에는 3 passed(exit=0)였다. 두 값 모두 이 워크트리에서 직접 돌려 얻었다.

## 4. 설계 결정: 곡별이 아니라 가장 최근 반영 하나

선택: 번호를 「가장 최근 성공한 반영」 하나로 두고, 프로세스 단위 저장소(SongTimelineStore)에 보관한다. 곡별 열쇠로 나누지 않는다.

이유 (읽은 코드 근거):

1. 필드의 정의가 이미 그렇게 되어 있다. session.py 의 _BeatGridAppliedState 설명문은 「가장 최근 성공한 「콘솔에 반영」이 실제로 쓴 번호들」이라고 적고, 끄기와 미리보기가 번호를 얻는 유일한 출처라고 명시한다. 곡별로 바꾸면 이 정의를 바꾸는 일이다.
2. 콘솔의 현재 상태는 가장 최근 반영과 같다. 곡별로 나누려면 「지금 콘솔에 어느 곡의 시퀀스가 켜져 있는가」를 알아야 하는데, 코드는 그것을 추적하지 않는다. 대신 쓸 수 있는 store.latest 는 화면에 보이는 마지막 타임라인이라서 반영과 무관하게 바뀔 수 있다(저장소 설명문). 그 값으로 곡 열쇠를 정하면 콘솔에 없는 곡의 번호를 끄거나 가리키게 될 수 있다.
3. 카드의 범위는 수명이다. 번호가 연결마다 사라지는 것만 고치라고 했다. 곡별 열쇠는 끄기·미리보기가 건드리는 시퀀스 집합을 바꾸므로 동작 변경이 된다.

기각한 대안: 곡별 열쇠(song_key). 위 2번 때문에 콘솔 상태를 잘못 가리킬 수 있다.

## 5. 한 일과 의도적으로 하지 않은 일

한 일:

- SongTimelineStore 에 메모리 전용 슬롯 _beat_grid_applied 와 프로퍼티 beat_grid_applied 를 추가했다(session.py 3719~3730행).
- ChatSession 의 필드 초기화를 지웠고, 쓰기(beat_grid_apply, 10774행)와 두 읽기(_beat_grid_preview_commands 10854행, beat_grid_preview 10911행)를 저장소로 바꿨다.
- 설명문과 주석에서 옛 위치를 가리키는 말을 고쳤다.

하지 않은 일:

- _preview_approval 은 옮기지 않았다. 재연결 뒤 다시 묻는 것이 설계다(리드 지시).
- _beat_grid_pool_slots, _beat_grid_empty_marks, _beat_grid_suggestions 는 그대로 두었다.
- 저장 파일은 바꾸지 않았다. _save 는 version, timeline, setlist, beat_grid_allocations 네 키만 쓰므로 새 필드는 파일에 들어가지 않는다(읽기로 확인).
- 디스패치 호출 위치는 바꾸지 않았다. census 파일이 그 위치를 고정한다.

## 6. 미검증 (Gaps)

- 실제 WebSocket 재연결 경로. 이 시험은 단위 층이며, app.py 의 재연결 처리 자체는 돌리지 않았다.
- 살아 있는 콘솔. 리드 지시에 따라 이번 범위 밖이다.
- 전체 시험 묶음. CI 가 돌린다.
- 서버 재시작 뒤의 동작. 번호는 메모리에만 있으므로 재시작하면 「반영된 적 없음」으로 거절된다. 이전과 같다. 파일에 저장할지는 따로 판단할 일이다.

## 7. 잔여 위험

- 테스트 파일 상단 설명문에 옛 이름 `ChatSession._beat_grid_applied` 가 남아 있다. 동작과 무관한 문서 불일치이며, 테스트 파일은 이번 커밋에서 건드리지 않았다.
- 같은 수명 문제가 연결별 필드 _beat_grid_pool_slots, _beat_grid_empty_marks 에도 있을 수 있다. 조사 보고는 이 둘을 재생(replay) 경로가 읽는다고 했으나 이번에 실행으로 확인하지 않았다. 범위 밖이므로 별도 카드가 필요한지 리드가 정해야 한다.
- 두 곡 이상을 반영한 뒤 재연결하는 경우는 이 시험이 다루지 않는다(scope.md 7절과 같다).

상태: 수정 완료, 관련 시험과 린트 초록. PR, CI, 머지는 다음 단계다.
