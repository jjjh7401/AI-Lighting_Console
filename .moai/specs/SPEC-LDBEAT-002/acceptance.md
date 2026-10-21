# SPEC-LDBEAT-002 — 인수 기준 (as-built)

각 AC 는 `AC-LDBEAT2-NNN` 이며 `spec.md` 의 같은 번호 REQ 를 검증한다. 검증은 **저장소에 이미 있는 시험**을 가리킨다. 이 SPEC 을 쓰며 시험을 실행하지는 않았다(`spec.md` §7). 시험 이름이나 파일이 없는 곳은 「시험 없음」이라고 적었다.

실행 방법(참고): 서버 `python -m pytest server/tests/<파일>` (`pyproject.toml` `testpaths = ["server/tests"]`), 화면 `npm --prefix ui test -- <파일>` (`ui/package.json` `"test": "vitest run"`).

## AC-LDBEAT2-001 — 소유 기록 확인 후 재사용 [REQ-LDBEAT2-001]

- **Given** 이 곡으로 반영한 소유 기록이 있고 콘솔 시퀀스 풀에서 기록된 번호가 사라졌거나 다른 이름이 쓰고 있다
- **When** 감독이 「⇪ 콘솔에 반영」을 다시 누르면
- **Then** 그 트랙은 소유 목록에서 빠져 빈 번호에 새로 만들어지고 다른 곡의 번호는 건드리지 않으며, 번호와 이름이 모두 맞는 트랙만 재사용된다. 풀을 못 읽으면 명령 0줄로 거절된다.
- **시험**: `server/tests/test_beat_grid_stale_owner_play.py`, `server/tests/test_beat_grid_recreate_missing_sequence.py`, `server/tests/test_beat_grid_apply_safety.py`(`test_d14_reapply_over_app_timecode_reuses_its_sequence_and_allocates_none`)

## AC-LDBEAT2-002 — 재반영의 삭제 범위와 감김 해제 [REQ-LDBEAT2-002]

- **Given** 앱이 만든 `LDBEAT Timecode N` 이 콘솔에 있고, 새 격자 그룹과 짝이 안 맞는 옛 `LDBEAT ` 시퀀스와 외부 시퀀스가 함께 있다
- **When** 같은 번호로 다시 반영한 승인 카드를 만들면
- **Then** 번들 맨 앞에 `Delete Timecode N /NoConfirm` 이 있고, 짝 없는 `LDBEAT ` 시퀀스만 같은 카드 안에서 삭제되며 외부 시퀀스는 삭제되지도 재사용되지도 않는다.
- **시험**: `test_beat_grid_apply_safety.py`(`test_d14_unmatched_old_app_sequence_is_deleted_inside_the_same_card`, `test_d14_foreign_sequences_are_never_deleted_or_reused`)
- **부분 확인**: 새 시퀀스의 `Set Sequence S Property 'WrapAround' 0` 은 `test_beat_grid_play_resets_sequences.py`·`test_beat_grid_sequence_suffix.py`·`test_beat_grid_emit_entry_t576.py` 가 `WrapAround` 를 인용하지만, 어느 시험이 그 줄을 직접 단언하는지는 이 SPEC 을 쓰며 확인하지 못했다.

## AC-LDBEAT2-003 — 줄이 많은 곡의 타임코드 분할 [REQ-LDBEAT2-003]

- **Given** 격자의 줄이 30개이고 `measured_console.yaml` 의 `max_timecode_tracks` 가 16이다
- **When** 반영 카드를 만들고 ▶·■ 를 보내면
- **Then** 줄이 두 타임코드로 나뉘어 모두 배정되고, 사용 중이거나 예약된 번호는 건너뛰며, ▶·■ 는 소유한 타임코드 전부에 같은 동작을 보낸다. 줄이 16개이면 타임코드는 하나다. 다른 곡의 시퀀스를 가리키는 추가 타임코드나 이름이 바뀐 추가 타임코드는 재생하지 않는다.
- **시험**: `server/tests/test_timecode_split.py`(`test_thirty_rows_emit_two_timecodes_and_every_row_is_assigned`, `test_the_split_counts_rows_not_fixtures`), `server/tests/test_beat_grid_timecode_split_session.py`

## AC-LDBEAT2-004 — 소속 장비 기준 트랙 [REQ-LDBEAT2-004]

- **Given** 콘솔 그룹과 소속 장비 목록(연기 장비 그룹, 밝기 채널 없는 그룹, 어느 그룹에도 없는 장비 포함)
- **When** `plan_console_tracks` 를 부르면
- **Then** 겹치지 않는 그룹이 줄이 되고, 묶음 그룹은 이름이 아니라 소속으로 빠지며, 연기 장비 그룹은 「일부러 뺌」으로, 밝기 없는 비연기 그룹과 미소속 장비는 사유와 함께 남는다. 소속을 다 못 읽은 그룹은 짐작해 넣지 않는다.
- **시험**: `server/tests/test_console_tracks.py`(열 개 시험), `ui/src/components/beatgrid/ConsoleCoverageNotice.test.tsx`

## AC-LDBEAT2-005 — 프로브 의존 칸 보류와 카드 첫 줄 [REQ-LDBEAT2-005]

- **Given** M1 프로브 항목 일부가 PASS 가 아니다
- **When** 반영 카드를 만들면
- **Then** 그 항목에 의존하는 칸만 보류되고 나머지는 나가며, 모두 PASS 이면 보류 줄이 없다. 카드 첫 줄은 대상 타임코드·시퀀스 범위·큐 수를 말하고, 게이트 `SaveShow` 백업은 카드와 승인=송신 대조 목록에 있다. 백업 관리자가 없으면 `SaveShow` 를 보내지도 선언하지도 않는다.
- **시험**: `test_beat_grid_apply_safety.py`(`test_d15_*`, `test_d16_*`, `test_d17_card_leads_with_target_timecode_sequences_and_cue_count`)

## AC-LDBEAT2-006 — 반영 계측·장비 판독 재사용·예열 [REQ-LDBEAT2-006]

- **Given** 595칸 격자의 반영
- **When** 반영을 한 번 돌리면
- **Then** 단계마다 한 줄과 합계가 남고 승인 카드 크기가 보고되며, 같은 장비 판독은 한 번 묻고 이후 읽기는 받아 둔 값으로 답한다. 예열은 콘솔이 답한 장비를 기억하고 고장 난 콘솔이면 `False` 를 돌려주며 캐시를 비워 둔다. 패치 에포크가 바뀌면 옛 판독을 버린다.
- **시험**: `server/tests/test_apply_timing.py`, `server/tests/test_fixture_snapshot.py`, `server/tests/test_rig_warm.py`

## AC-LDBEAT2-007 — 첫 반영은 곡 전체, 이후는 바뀐 칸 [REQ-LDBEAT2-007]

- **Given** 서버가 보낸 `partial_baseline` 이 `null` 이다(첫 반영)
- **When** `partialApplyPlan` 이 계획을 세우면
- **Then** 결과는 `whole`(이유 `no-record`)이고 주 버튼은 켜져 「전체 다시 반영」과 같은 콜백을 부르며 안내는 「아직 반영 기록이 없어 곡 전체를 보내요」이다. 기준이 `"record"` 이고 고른 칸이 없으면 `whole`(`nothing-picked`), 칸을 골랐으면 고른 칸 전부와 「지운 값은 콘솔에 남을 수 있어요」 안내, 기준이 `"snapshot"` 이면 바뀐 칸과 콘솔 상태를 모르는 칸만이다. 0마디 칸은 빠지고, 바뀐 칸이 없으면 막히며, 400칸을 넘으면 막힌다.
- **시험**: `ui/src/components/beatgrid/cellApply.test.ts`, `ConsoleApplyButton.cellApply.test.tsx`, `ui/src/components/BeatGrid.cellSelect.test.tsx`, `ui/src/protocol.cellApply.test.ts`

## AC-LDBEAT2-008 — 서버 칸 단위 반영 [REQ-LDBEAT2-008]

- **Given** 반영 기록이 있는 곡에서 `cells` 를 단 `beat_grid_apply`
- **When** 서버가 처리하면
- **Then** 고른 칸의 큐만 `/Merge` 로 나가고 타임코드·프리셋·새 시퀀스 줄은 없으며, 기록이 없거나 이미 콘솔과 같은 칸뿐이거나 빈 프리셋과 얽힌 칸이면 아무것도 보내지 않고 거절된다. 첫 성공은 부분 칸 기록을 남기고 기록에 없는 칸은 같다고 보지 않는다. `cells` 가 없으면 전체 반영이다.
- **시험**: `server/tests/test_beat_grid_cells_subset.py`(215개; 프로토콜 해석 시험과 `/Merge`·`PartialCellSnapshot` 시험 포함)

## AC-LDBEAT2-009 — ▶ ■ ❚❚ 의 명령 [REQ-LDBEAT2-009]

- **Given** 이 곡의 소유 기록이 있고 타임코드가 앱 이름·앱 시퀀스를 가리킨다
- **When** ▶, ■, ❚❚, 일시정지 뒤 ▶ 를 차례로 보내면
- **Then** ▶ 는 시퀀스 Off 뒤 `Top`·`Go`, ■ 는 `Off Timecode` 와 시퀀스 Off, ❚❚ 는 `Off Timecode` 만(시퀀스 유지), 이어 재생은 `Go Timecode` 만 보낸다. 외부 타임코드 이름·외부 시퀀스·기록 없음이면 0줄로 거절된다. 승인 카드는 서버를 켠 뒤 첫 한 번만 묻고 거절되면 다시 묻는다.
- **시험**: `test_beat_grid_console_play_t578.py`, `test_beat_grid_pause_resume_1018.py`, `test_beat_grid_console_play_fresh_session_1016.py`, `test_web_beat_grid_console_play_t578.py`

## AC-LDBEAT2-010 — 마디 이동 [REQ-LDBEAT2-010]

- **Given** 「콘솔 같이」가 켜져 있고 소유 타임코드가 있다
- **When** 마디를 옮기면(정지 중, 재생 중, 연타)
- **Then** 소유 타임코드마다 `Set Timecode N Property 'Cursor'` 한 줄만 나가고 재생은 켜지지 않는다. 연타 중에는 가장 새 이동만 콘솔에 쓰고, 재생 중 주기 확인은 허용 오차 안이면 쓰지 않으며 커서를 못 읽으면 쓰지 않는다. 화면은 재생 중 `live`, 일시정지 뒤 `seek`, 그 밖에는 `none` 을 고르고 지연 측정값이 없으면 시각을 만들지 않는다.
- **시험**: `server/tests/test_beat_grid_console_seek.py`, `server/tests/test_web_console_seek_queue.py`, `ui/src/components/beatgrid/consoleSeekPlan.test.ts`, `consoleSeekDelay.test.ts`

## AC-LDBEAT2-011 — 재생 중계와 어긋남 알림 [REQ-LDBEAT2-011]

- **Given** ▶ 를 눌러 승인 카드 때문에 전체화면을 닫았다 다시 연 상태
- **When** 서버의 콘솔 재생 응답이 닫혀 있는 동안 도착하면
- **Then** 중계 객체가 의도·시작 시각을 들고 있어 다시 열린 화면이 이어받고, 앞 응답은 답으로 오인되지 않으며, 재생 성공에서 `consoleMayRun` 이 켜지고 정지 성공에서만 꺼진다. 어긋남 알림은 유예 시간(지연+2.5초) 전에는 나오지 않는다.
- **시험**: `ui/src/components/beatgrid/consoleFollowRelay.test.ts`, `ConsoleRunningBanner.test.tsx`, `ui/src/components/BeatGrid.consoleFollowResume.test.tsx`, `playbackClock.test.ts`

## AC-LDBEAT2-012 — 카드 문구와 전체화면 승인 [REQ-LDBEAT2-012]

- **Given** 재생·정지·일시정지·이어 재생 중 하나의 승인 카드와 박자 배치 전체화면
- **When** 카드가 올라오면
- **Then** 카드 머리는 감독 말(곡·쇼 백업·끄는 시퀀스 수·타임코드)이고, 일시정지 카드는 시퀀스를 끄지 않는다고 말하며, 머리 키는 묶음을 보내는 동안 올라온 승인에만 붙는다. 전체화면에서는 대기 승인이 겹쳐 보인다(여럿이면 전부).
- **시험**: `server/tests/test_beat_grid_approval_card_title.py`, `ui/src/components/beatgrid/FullscreenApprovalOverlay.test.tsx`

## AC-LDBEAT2-013 — 칸 규칙과 옮기기만 받는 경로 [REQ-LDBEAT2-013]

- **Given** 줄의 칸 목록과 옮기기·만들기·지우기 요청
- **When** 순수 규칙에 적용하면
- **Then** 마디가 같은 칸이 있는 만들기는 거절되고, 옮기기는 마디만 바꾸고 순서를 지키며 전부 되거나 하나도 안 되고, 입력은 고쳐지지 않는다. 웹 소켓 `beat_grid_cell_edit` 는 `move` 만 받고 그 밖의 `op`·알 수 없는 키·빈 `ops` 는 한국어 사유 또는 프로토콜 오류로 거절된다.
- **시험**: `server/tests/test_beat_grid_cell_edit.py`, `test_beat_grid_cell_edit_message.py`, `test_web_beat_grid_cell_edit_route.py`
- **시험 없음**: 칸 만들기·지우기를 서버·화면에서 부르는 경로(배선돼 있지 않음, `spec.md` §3.3).

## AC-LDBEAT2-014 — 옮기기의 즉시 콘솔 반영 [REQ-LDBEAT2-014]

- **Given** 반영 기록과 소유 타임코드가 있는 곡에서 칸 옮기기 요청
- **When** 서버가 처리하면
- **Then** 보내는 줄은 이 곡 소유 트랙의 `Set Timecode … Property 'Time'` 한 꼴뿐이고 다른 꼴은 거절되며, 이벤트 번호는 시각으로 찾는다. 줄이 모두 나가면 격자·소유 기록·칸 기록이 함께 확정되고 일부만 나가면 격자만 옮겨져 「미반영」으로 남으며, 한 줄도 나가지 않으면 셋 다 그대로다. 첫 옮기기만 카드로 묻고 이후는 승인된 범위로 카드 없이 같은 줄을 보낸다. 사전이동 큐는 칸을 따라 이동하고 새 큐가 필요하면 거절된다.
- **시험**: `server/tests/test_web_beat_grid_cell_move.py`, `test_beat_grid_cell_live.py`, `test_beat_grid_tc_cell.py`, `test_beat_grid_cell_mib.py`, `test_cell_live_approval.py`

## AC-LDBEAT2-015 — 칸 선택과 끌기 [REQ-LDBEAT2-015]

- **Given** 격자 화면에서 칸을 누르거나 끄는 포인터 입력
- **When** Shift·Ctrl·Cmd 와 함께 누르거나 3px 이상 끌고 놓으면
- **Then** Shift 는 범위, Ctrl/Cmd 는 토글이며 둘이 겹치면 Shift 가 이기고, 3px 미만은 클릭이고 3px 이상은 끌기이며, 놓을 때만 옮기기 목록이 나오고, 끈 손짓 뒤의 클릭은 무시된다. 0마디로 반올림되거나 1마디 미만으로 가는 끌기는 보내지 않는다.
- **시험**: `ui/src/components/beatgrid/cellSelection.test.ts`, `cellMove.test.ts`, `CellSelectionBar.test.tsx`, `ui/src/components/BeatGrid.cellMove.test.tsx`

## AC-LDBEAT2-016 — 칸 좌우 색과 방향 값 [REQ-LDBEAT2-016]

- **Given** `split` 이 있거나 없는 칸, 그리고 규칙 결정에서 만든 방향 값
- **When** 저장 경계에서 검증하고 서빙 경계에서 화면용 값을 달면
- **Then** `split` 이 없는 칸은 키를 만들지 않고, 모양이 틀린 `split` 은 `ValueError` 이며, 풀 수 없는 색 이름은 RGB 를 지어내지 않고 `null` 이다. 방향 값은 라벨 글자를 읽지 않고 같은 입력이면 같은 값이며, 라벨과 값이 어긋난 칸은 불일치로 보고된다.
- **시험**: `server/tests/test_beat_grid_cell_split.py`, `test_cell_split_payload_fixture.py`, `test_cell_direction_model.py`, `test_cell_direction_unit.py`, `ui/src/components/beatgrid/cellSplit.test.ts`, `cellSplitRoundTrip.test.tsx`

## Definition of Done (as-built)

- [x] 요구사항 16개가 코드 `파일:함수` 로 추적된다(`spec.md` §3).
- [x] AC 16개가 존재하는 시험 파일에 대응한다. 시험이 없는 곳은 위에 「시험 없음」으로 적었다.
- [ ] 위 시험들을 `origin/main` `e4bf3f03` 이후 트리에서 실행한 통과 증거 — 이 SPEC 에는 없다. 후속 sync 검증 몫이다.
- [ ] 실기 콘솔 확인 — `SPEC-LDBEAT-001` 의 t608 체크리스트가 기준이다.
