---
id: SPEC-LDBEAT-002
title: "박자 격자 콘솔 반영·재생·칸 편집 (as-built)"
version: "0.1.0"
status: implemented
created: 2026-10-21
updated: 2026-10-21
author: jaihyun
priority: P2
phase: "Lighting Copilot v1.2 target"
module: "server/web/session.py(beat_grid_apply·beat_grid_console_*·beat_grid_cell_edit), server/web/messages.py, server/web/app.py, server/web/apply_timing.py, server/web/rig_warm.py, server/design/beat_grid_send.py, server/design/beat_grid_emit.py, server/design/console_tracks.py, server/design/timecode_split.py, server/design/fixture_snapshot.py, server/design/beat_grid_cell_edit.py, server/design/beat_grid_cell_live.py, server/design/beat_grid_cell_mib.py, server/design/beat_grid_cell_split.py, server/design/beat_grid_tc_cell.py, server/design/cell_direction.py, ui/src/components/beatgrid/(cellApply·cellMove·cellSelection·CellSelectionBar·consoleFollowRelay·consoleSeekPlan·playbackClock·ConsoleApplyButton·ConsoleRunningBanner·FullscreenApprovalOverlay)"
lifecycle: spec-anchored
tags: "as-built, beat-grid, console-apply, ownership-record, timecode-split, console-follow, cell-edit, approval-card"
tier: M
related_specs: [SPEC-LDBEAT-001, SPEC-LDRHYTHM-001, SPEC-LDRHYTHM-002, SPEC-LDBEAT-003]
---

# SPEC-LDBEAT-002 — 박자 격자 콘솔 반영·재생·칸 편집 (as-built)

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-21 | 최초 작성. **as-built SPEC** — 이미 출하된 동작을 사후에 문서로 닫는다. 새 요구사항이 아니라 `origin/main` `e4bf3f03` 의 코드를 읽어 적은 현재 동작이다. 입력: SPEC 커버리지 인벤토리(`spec-inventory.md` §4.2 클러스터 C1·C2·C3·C12). `SPEC-LDBEAT-001` 은 REQ-001~025 로 2026-10-18 에 닫혔고(`completed`), 그 뒤 쌓인 콘솔 반영·소유 기록·「콘솔 같이」·칸 편집은 그 본문에 흔적이 없었다(인벤토리 §4.3: `timecode_split`·`console_tracks`·`cell_move`·`WrapAround`·`consoleSeek` 문서 검색 0건). 같은 화면·같은 에미터의 확장이라 LDBEAT 계열로 이 SPEC 을 연다. 코드·시험·UI·콘솔·서버 런타임은 바꾸지 않았다. |

## §0. as-built SPEC 읽는 법

1. 이 문서의 요구사항은 **현재 동작의 기술**이다. 각 행의 「코드 근거」는 이 SPEC 을 쓰며 실제로 읽은 `파일:함수` 이고, 「시험」은 저장소에 존재하는 시험 파일이다. 시험이 없는 항목은 「시험 없음」이라고 적었고, 지어낸 시험은 없다.
2. 「소스 PR」은 인벤토리 §4.2 의 손으로 묶은 목록이다. 경계 PR 은 한쪽 클러스터에만 적혀 있을 수 있다. 이 SPEC 을 쓰며 머지 커밋을 직접 확인한 것은 #864(`93844eb0`)뿐이고, 나머지 번호는 인벤토리 값 그대로다.
3. 인벤토리 서술이 코드와 달랐던 곳은 §6 에 적었다. 둘이 다르면 코드를 따랐다.
4. 시험을 이 SPEC 을 쓰면서 실행하지 않았다. 「시험」 열은 존재 증거이지 통과 증거가 아니다(§7).

## §1. 범위와 소스 PR

| 클러스터 | 다루는 동작 | 소스 PR(인벤토리 §4.2) |
|---|---|---|
| C1 콘솔 반영·소유 기록·트랙 모델 | 「⇪ 콘솔에 반영」, 앱이 만든 시퀀스·타임코드를 알아보고 같은 번호로 다시 만들기, 줄이 많을 때 타임코드 나눠 담기, 단계별 시간 로그 | #655 #658 #660 #661 #680 #742 #749 #761 #763 #764 #784 #785 #787 #791 #795 #799 #801 #821 #822 #827 #829 #830 #845 #864 |
| C2 「콘솔 같이」 재생·정지·마디 이동 | ▶/❚❚/■, Space, 방향키로 마디를 옮기면 콘솔 커서도 이동, 시퀀스 감김(WrapAround) 해제 | #777 #781 #796 #809 #813 #815 #816 #823 #833 #842 #844 #847 #862 |
| C3 칸 단위 편집·반영 | 칸 고르기, 옮기기, 고른 칸만 콘솔에 반영, 사전이동(MIB) 큐 동반 이동 | #758 #836 #839 #841 #843 #846 #851 |
| C12 승인 카드 문구·전체화면 승인 | 카드 머리를 감독 말로, 전체화면에서도 카드가 보임 | #789 #804 #835 #862 |

## §2. 배경

`SPEC-LDBEAT-001` 은 박자 격자 화면과 박자 전용 에미터(`server/design/beat_grid_emit.py`)를 닫았다. 그 위에서 감독이 실기로 쓰면서 다음이 필요해졌고, 모두 카드 단위로 출하됐다.

- 같은 곡을 두 번째 이후 반영할 때 콘솔에 새 번호가 쌓이지 않아야 한다(소유 기록).
- 장비가 수십 종·수백 대인 무대에서 줄(콘솔 그룹) 수에 고정 상한을 두지 않아야 한다.
- 앱의 ▶ 가 콘솔 타임코드를 함께 돌리고, 마디를 옮기면 콘솔 커서가 따라와야 한다.
- 칸 하나를 옮기거나 고쳤을 때 곡 전체를 다시 보내지 않고 그 칸만 콘솔에 반영해야 한다.

## §3. 요구사항 (GEARS, 현재 동작)

주체 표기: 「서버」는 `server/web/session.py` 의 `ChatSession`, 「화면」은 `ui/src/components/beatgrid/` 의 순수 함수와 `BeatGrid.tsx`.

### 3.1 R1 — 콘솔 반영 (REQ-LDBEAT2-001~008)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDBEAT2-001 | **When** 감독이 한 곡을 두 번째 이후 「⇪ 콘솔에 반영」할 때, 서버 **shall** 소유 기록의 트랙마다 그 시퀀스가 콘솔에 그 번호·그 이름으로 있는지 확인하고 일치하는 번호만 재사용한다. 번호가 콘솔에서 사라졌거나 같은 번호를 다른 이름이 쓰고 있으면 그 트랙은 소유 목록에서 빼고 건드리지 않은 채 빈 번호에 새로 만든다. 시퀀스 풀을 못 읽었거나 잘렸으면 「있다」도 「없다」도 단정하지 않고 사유를 들어 거절한다. | `server/design/beat_grid_send.py:verify_owned_sequences`, `apply_beat_grid_ownership_reuse`; `server/web/session.py:beat_grid_apply` | `server/tests/test_beat_grid_stale_owner_play.py`, `server/tests/test_beat_grid_recreate_missing_sequence.py`, `server/tests/test_beat_grid_apply_safety.py`(d14) |
| REQ-LDBEAT2-002 | **When** 앱이 만든 타임코드(`LDBEAT Timecode N`)를 같은 번호로 다시 반영할 때, 서버 **shall** 번들 맨 앞에 `Delete Timecode N /NoConfirm` 을 두어 옛 트랙이 쌓이지 않게 하고, 새 격자의 그룹과 짝이 안 맞는 옛 앱 시퀀스(이름이 `LDBEAT ` 로 시작하는 것)만 같은 승인 카드 안에서 `Delete Sequence <n> /NoConfirm` 로 지운다. 외부(앱이 만들지 않은) 시퀀스는 지우지도 재사용하지도 않는다. 새로 만드는 시퀀스에는 `Set Sequence S Property 'WrapAround' 0` 을 붙여 마지막 큐 뒤에 큐 1 로 감기지 않게 한다. | `beat_grid_send.py:clear_app_timecode_before_rebuild`; `beat_grid_emit.py`(`Set Sequence … Property 'WrapAround' 0`); `session.py`(`Delete Sequence` 안내 문구) | `test_beat_grid_apply_safety.py`(d14 셋), `test_beat_grid_play_resets_sequences.py`·`test_beat_grid_sequence_suffix.py`·`test_beat_grid_emit_entry_t576.py`(`WrapAround` 를 인용하는 시험) |
| REQ-LDBEAT2-003 | **While** 격자의 줄(콘솔 그룹) 수가 한 타임코드에 실측으로 확인된 트랙 수(`measured_console.yaml` 의 `max_timecode_tracks`, 현재 16)보다 많은 동안, 서버 **shall** 줄을 격자 순서대로 그 수씩 끊어 타임코드 여러 개에 나눠 담는다. 기준은 줄 수이며 장비 대수가 아니다. 추가 타임코드 번호는 사용 중인 번호와 `reserved_timecodes`(현재 `[3, 4]`)를 건너뛰고 이전에 기록한 번호를 먼저 재사용한다. ▶·■·❚❚·마디 이동은 이 곡이 소유한 타임코드 전부에 같은 동작을 보낸다. | `server/design/timecode_split.py:split_rows_by_timecode`, `pick_extra_timecode_numbers`, `transport_commands`; `server/design/beat_grid_data/measured_console.yaml`; `session.py:_beat_grid_owned_extra_timecodes` | `server/tests/test_timecode_split.py`, `server/tests/test_beat_grid_timecode_split_session.py` |
| REQ-LDBEAT2-004 | **The** 배치 줄 **shall** 콘솔 그룹의 소속 장비로 정한다. 이미 있는 줄은 두고, 나머지 그룹을 소속 장비가 적은 순서(같으면 그룹 번호 순)로 보아 이미 덮인 장비와 하나도 안 겹칠 때만 새 줄로 넣는다. 소속 장비가 모두 연기 장비(채널 속성으로 판정)인 그룹은 일부러 빼고 목록에 「일부러 뺌」으로 남긴다. 연기 장비가 아닌데 밝기(Dimmer) 채널이 없는 그룹과 어느 줄에도 못 든 장비는 사유와 함께 `uncovered` 에 남겨 조용히 빠지지 않게 한다. 이 규칙은 콘솔을 읽지 않는 순수 함수이며 그룹 이름·번호를 하나도 모른다. | `server/design/console_tracks.py:plan_console_tracks`, `coverage_payload`; `session.py:_beat_grid_console_track_plan`; 화면 `ConsoleCoverageNotice.tsx` | `server/tests/test_console_tracks.py`, `ui/src/components/beatgrid/ConsoleCoverageNotice.test.tsx` |
| REQ-LDBEAT2-005 | **While** M1 콘솔 프로브 항목 가운데 PASS 로 확인되지 않은 항목에 의존하는 칸이 있는 동안, 서버 **shall** 그 칸만 송신에서 보류하고 나머지는 보낸다. 승인 카드는 보류된 칸 수를 적고, 카드 첫 줄에 `대상: Timecode N · 시퀀스 a–b · 큐 K개` 를 적으며, 게이트가 직전에 보내는 `SaveShow` 백업을 카드 위험 줄과 승인=송신 대조 목록에 명시한다. 「쓰기 잠김」이라는 화면 문구는 콘솔 잠금이 아니라 이 프로브 보류를 뜻한다. | `server/design/beat_grid_emit.py:blocked_m1_items_for_cue`; `session.py:beat_grid_apply`(D15·D16·D17 주석) | `test_beat_grid_apply_safety.py`(d15·d16·d17) |
| REQ-LDBEAT2-006 | **The** 반영 한 번 **shall** 단계마다 경과 시간과 그 사이에 게이트를 거친 콘솔 읽기 수·합계 시간·가장 오래 걸린 읽기를 서버 로그(표준 오류)에 한 줄씩 남기되 동작은 바꾸지 않는다. 같은 반영 안에서 같은 장비는 콘솔에 한 번만 묻고(`FixtureSnapshotPort`), 서버를 띄울 때와 곡을 열 때 장비·기종 판독을 백그라운드에서 한 번 돌려 첫 「⇪」이 기종 채널을 처음부터 걷지 않게 한다. 콘솔이 답을 준 장비는 「없음」도 기억하고 답을 못 받은 장비는 기억하지 않는다. | `server/web/apply_timing.py:ApplyClock`, `apply_stage`, `timed_apply`; `server/design/fixture_snapshot.py:FixtureSnapshotPort`; `server/web/rig_warm.py:warm_device_layers`, `warm_until_answered` | `server/tests/test_apply_timing.py`, `server/tests/test_fixture_snapshot.py`, `server/tests/test_rig_warm.py` |
| REQ-LDBEAT2-007 | **When** 바뀐 칸을 가려낼 기준이 없을 때(첫 반영, `partial_baseline` 이 `null`) 또는 기록 기준(`"record"`)에서 고른 칸이 없을 때, 화면 **shall** 「⇪ 콘솔에 반영」을 막지 않고 「전체 다시 반영」과 같은 콜백으로 곡 전체를 보낸다(2026-10-21 #864). 칸 기록 기준(`"snapshot"`)이면 바뀐 칸과 콘솔 상태를 모르는 칸만 보내고 콘솔과 같은 칸은 뺀다. 기록 기준에서 칸을 골랐으면 고른 칸을 모두 보내며 「지운 값은 콘솔에 남을 수 있어요」를 안내한다. 보낼 칸이 없거나 한 번에 400칸(`CELL_WIRE_MAX`)을 넘으면 막고 사유를 말한다. 서버가 받지 못하는 0마디(앞박) 칸은 빼고 그 사실을 말한다. | `ui/src/components/beatgrid/cellApply.ts:partialApplyPlan`, `wirePlan`; `ConsoleApplyButton.tsx`; `ui/src/components/beatgrid/cellSelection.ts:CELL_WIRE_MAX`; `server/web/messages.py:BEAT_GRID_CELLS_MAX` | `ui/src/components/beatgrid/cellApply.test.ts`, `ConsoleApplyButton.cellApply.test.tsx`, `ui/src/components/BeatGrid.cellSelect.test.tsx`, `ui/src/protocol.cellApply.test.ts` |
| REQ-LDBEAT2-008 | **When** `beat_grid_apply` 가 `cells` 와 함께 오면, 서버 **shall** 계획은 전체 반영과 같게 세우고 고른 칸의 큐만 남겨 콘솔에 있는 시퀀스에 `/Merge` 로 덮어쓴다. 타임코드 만들기·프리셋 만들기·시퀀스 새로 만들기는 한 줄도 보내지 않는다. 기준은 마지막 반영의 칸 기록(바뀐 칸만 보냄, 지운 항목이 있는 칸은 `not_applied`) 아니면 소유 기록(고른 칸을 모두 보냄, `subset.baseline = "record"`)이다. 둘 다 없는 곡, 콘솔에 아직 없는 줄, 이미 콘솔과 같은 칸뿐인 선택, 빈 프리셋 보류나 새로 만들 프리셋과 얽힌 칸은 아무것도 보내지 않고 거절한다. 첫 성공은 보낸 칸만 담은 부분 칸 기록(`PartialCellSnapshot`)을 남기고, 기록에 없는 칸은 같다고 보지 않고 보낸다. | `session.py:beat_grid_apply`(`cells` 분기); `beat_grid_send.py:partial_apply_baseline`, `cell_apply_units`, `cells_needing_whole_apply`, `merge_store_line`, `merge_cell_snapshot`, `PartialCellSnapshot` | `server/tests/test_beat_grid_cells_subset.py`(215개) |

### 3.2 R2 — 「콘솔 같이」 재생 (REQ-LDBEAT2-009~012)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDBEAT2-009 | **When** 감독이 ▶ 를 누르면, 서버 **shall** 이 곡이 소유한 시퀀스를 `Off Sequence` 로 끈 뒤 `Top Timecode N`, `Go Timecode N` 순으로 보낸다(지난 재생의 마지막 큐에 선 시퀀스가 두 번째 ▶ 부터 꺼져 있던 결함 방지). ■ 는 `Off Timecode N` 뒤에 소유 시퀀스를 하나씩 끄고 타임코드 커서로 멈췄는지 확인하며, ❚❚ 는 `Off Timecode N` 만 보내 시퀀스를 끄지 않고, 일시정지 뒤 ▶ 는 `Go Timecode N` 만 보내 되감지 않는다. 앱이 소유한 타임코드·시퀀스로 확인되지 않으면 아무것도 보내지 않는다. 승인은 서버를 켜 둔 동안 첫 한 번만 카드로 묻고, 카드가 거절되면 다음에도 다시 묻는다. | `session.py:_beat_grid_console_transport`, `beat_grid_console_play`, `beat_grid_console_stop`, `beat_grid_console_pause`, `beat_grid_console_resume`, `_beat_grid_owned_timecode` | `server/tests/test_beat_grid_console_play_t578.py`, `test_beat_grid_pause_resume_1018.py`, `test_beat_grid_console_play_fresh_session_1016.py`, `test_web_beat_grid_console_play_t578.py` |
| REQ-LDBEAT2-010 | **When** 감독이 마디를 옮기면, 서버 **shall** 옮긴 마디의 시각으로 소유 타임코드마다 `Set Timecode N Property 'Cursor' <초>` 한 줄만 보내고 재생은 켜지 않는다. 앞선 이동이 쓰는 중이면 기다리다가 더 새 요청이 오면 옛 요청은 콘솔에 쓰지 않고 답만 한다. 재생 중 주기 확인(resync)은 커서를 먼저 읽어 허용 오차 0.3초 안이면 쓰지 않으며, 읽지 못하면 눈감고 쓰지 않는다. 보낸 뒤 커서를 되읽어 목표에 섰는지 말하고 「ok」만으로 맞췄다고 말하지 않는다. 화면은 「콘솔 같이」가 켜져 있을 때만 이동을 보내고(재생 중 `live`, 일시정지 뒤 `seek`, 멈춘 적 없는 정지는 `none`), 방향키 연타는 250ms 로 모으되 400ms 안에 한 번은 보내며, 재생 중 2초마다 다시 맞춰 본다. 콘솔 시각은 곡 시각에 측정된 콘솔→음원 지연을 더한 값이고, 지연 측정값이 없으면 시각을 지어내지 않는다. | `session.py:beat_grid_console_seek`, `_beat_grid_console_seek_now`; `ui/src/components/beatgrid/consoleSeekPlan.ts:consoleSeekPlan`, `consoleSeekStep`, `consoleTimecodeSeconds`, `consoleResyncDue` | `server/tests/test_beat_grid_console_seek.py`, `test_web_console_seek_queue.py`, `ui/src/components/beatgrid/consoleSeekPlan.test.ts`, `consoleSeekDelay.test.ts` |
| REQ-LDBEAT2-011 | **The** 화면 **shall** 「콘솔 같이」의 의도(켬/끔·응답 대기)와 콘솔이 출발한 시각을 `App` 이 쥔 가변 중계 객체에 담아, 전체화면을 닫았다 다시 열어도 이어지게 한다. ▶ 를 누를 때 화면에 있던 응답 객체와 다른 객체가 와야 이번 요청의 답으로 받는다. `consoleMayRun` 은 재생 성공 응답에서 켜지고 정지 성공 응답에서만 꺼진다. 앱은 멈췄는데 콘솔이 돌 수 있는 상태가 지연+2.5초 이상 이어질 때만 타임코드 번호와 끄기 버튼을 크게 알린다(`ConsoleRunningBanner`). 정지 카드를 기다리는 중이면 카드에서 승인하라고 말하고 버튼은 숨긴다. 새 탭은 「콘솔 같이 끔」으로 시작하므로 그 사실을 알린다. | `ui/src/components/beatgrid/consoleFollowRelay.ts`(`createConsoleFollowRelay`, `consoleRunningGraceMs`, `consoleRunningMismatchShown`, `consolePlayNote`), `ConsoleRunningBanner.tsx`, `playbackClock.ts` | `consoleFollowRelay.test.ts`, `ConsoleRunningBanner.test.tsx`, `ui/src/components/BeatGrid.consoleFollowResume.test.tsx`, `playbackClock.test.ts` |
| REQ-LDBEAT2-012 | **When** 재생·정지·일시정지·이어 재생의 승인 카드를 올릴 때, 서버 **shall** 카드 머리를 감독 말로 적는다(`<곡> 재생 시작 — 쇼 백업 1 · 이 곡 시퀀스 N개 끄기 · TC.. 처음으로·재생` 꼴). 영어 게이트 사유는 판정에 쓰지 않고 카드의 「자세히」 안에 그대로 남긴다. **While** 박자 배치 전체화면이 열려 있는 동안, 화면 **shall** 대기 중인 승인 카드(승인·거부·명령 펼치기)를 겹쳐 보인다. | `session.py:_beat_grid_transport_card_title`, `_beat_grid_pause_card_reason`, `_beat_grid_stop_card_reason`, `_BEAT_GRID_CARD_TITLE`; `ui/src/components/beatgrid/FullscreenApprovalOverlay.tsx` | `server/tests/test_beat_grid_approval_card_title.py`, `ui/src/components/beatgrid/FullscreenApprovalOverlay.test.tsx` |

### 3.3 R3 — 칸 편집 (REQ-LDBEAT2-013~016)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDBEAT2-013 | **The** 줄 하나의 칸 규칙 **shall** `bar` 오름차순의 칸들로 다루며, 칸은 자기 마디부터 다음 칸 직전까지를 덮고 마지막 칸은 끝이 열려 있다. 칸 만들기(`row_create`)·옮기기(`row_move`·`row_move_many`, 전부 되거나 하나도 안 됨)·지우기(`row_delete`)를 입력을 고치지 않는 순수 함수로 두고 규칙을 어기면 한국어 사유로 거절한다. 서버의 웹 소켓 경로 `beat_grid_cell_edit` 는 `{"op": "move", "group_name", "bar", "to_bar"}` 하나만 받고(한 번에 64건까지) 그 밖의 `op` 는 「이 버전은 칸 옮기기만 지원합니다」로 거절한다. 만들기와 지우기는 순수 함수와 시험만 있고 서버·화면에 배선돼 있지 않다. | `server/design/beat_grid_cell_edit.py`; `server/web/messages.py:BEAT_GRID_CELL_EDIT_OPS_MAX`, `_parse_beat_grid_cell_edit`; `session.py:_cell_moves_from_ops` | `server/tests/test_beat_grid_cell_edit.py`, `test_beat_grid_cell_edit_message.py`, `test_web_beat_grid_cell_edit_route.py` |
| REQ-LDBEAT2-014 | **When** 감독이 칸을 옮기면, 서버 **shall** 칸이 설 콘솔 타임코드 이벤트 시각을 에미터와 같은 식으로 계산하고 이벤트 번호는 읽은 목록에서 시각으로 찾아(없거나 모호하면 거절) `Set Timecode T.1.K.1.1.N Property 'Time' S` 한 꼴의 줄만 보낸다. 그 줄은 이 곡이 소유한 타임코드·트랙의 것일 때만 허용되고 지우기·만들기(Store)·`cd` 같은 줄은 모두 거절한다. 반영 단계가 사전이동(MIB) 큐를 끼우는 줄이면 그 큐도 옮긴 자리에 맞춰 이벤트 시각만 고치고, 큐를 새로 세우거나 지워야 하거나 옮긴 뒤 켜진 채 시작하면 거절한다. 줄이 모두 나갔을 때만 격자·소유 기록·칸 기록을 함께 확정하고, 일부만 나갔으면 격자만 옮긴 대로 두어 옮긴 칸이 「미반영」으로 남는다. 줄이 하나라도 나갔으면 초안 되돌리기·다시하기 기록을 비운다. 옮기기 범위는 서버를 켜 둔 동안 첫 한 번만 카드로 승인받고 그 뒤에는 카드 없이 같은 줄만 보낸다. | `session.py:beat_grid_cell_edit`, `_plan_cell_moves`, `_send_cell_moves`, `_commit_cell_moves`; `beat_grid_cell_live.py:move_bundle_allowed`, `cue_event_seconds`, `console_tracks_for_groups`; `beat_grid_tc_cell.py:plan_tc_cell_commands`; `beat_grid_cell_mib.py:move_mib_premoves` | `server/tests/test_web_beat_grid_cell_move.py`, `test_beat_grid_cell_live.py`, `test_beat_grid_tc_cell.py`, `test_beat_grid_cell_mib.py`, `test_cell_live_approval.py` |
| REQ-LDBEAT2-015 | **When** 감독이 칸을 누르거나 끌면, 화면 **shall** Shift 로 범위를, Ctrl 또는 Cmd 로 토글을 고르게 하고(둘을 함께 누르면 Shift 가 이긴다), 칸 막대를 3px 이상 끌어야 끌기로 보며 놓을 때만 옮기기 목록을 만든다. 끌었으면 뒤따르는 클릭은 무시하고, 마디 수가 0 으로 반올림되거나 옮길 자리가 1마디 미만이면 보내지 않는다. 고른 칸에 디머·색 프리셋을 일괄로 바꾸는 「적용」은 `beat_grid_edit` 를 `cells` 주소로 한 번만 보낸다. | `ui/src/components/beatgrid/cellSelection.ts`, `cellMove.ts:reduceCellMove`, `CellSelectionBar.tsx`; `ui/src/protocol.ts`(`beat_grid_cell_edit` 직렬화) | `cellSelection.test.ts`, `cellMove.test.ts`, `CellSelectionBar.test.tsx`, `ui/src/components/BeatGrid.cellMove.test.tsx` |
| REQ-LDBEAT2-016 | **The** 격자 칸 **shall** 선택 키 `split`(`left`·`right` 쪽마다 표준 팔레트 색 이름 또는 `null`)을 가질 수 있고, 서버는 모양이 틀리면 조용히 버리지 않고 `ValueError` 로 거절하며 서빙 경계에서만 쪽마다 `color_rgb` 를 단다. 「칸 나누기」라고 불러 온 이 기능은 시간으로 칸을 쪼개는 것이 아니라 한 칸의 왼쪽·오른쪽 색을 따로 정하는 것이다. **The** 칸의 방향 값(`direction`: 밝기·색·위치·효과 종류·움직임·진입)은 규칙 결정에서 한 번 만들어져 라벨·색 이름·무대 미리보기·프리셋 계획·콘솔 송신이 모두 같은 값을 읽고, 라벨 글자는 읽지 않는다. | `server/design/beat_grid_cell_split.py:validate_cell_split`, `attach_cell_split_to_cues`; `server/design/cell_direction.py:build_direction`, `normalize_direction`, `direction_label`, `label_value_mismatches`; `ui/src/components/beatgrid/cellSplit.ts`, `lrSplit.ts` | `server/tests/test_beat_grid_cell_split.py`, `test_cell_split_payload_fixture.py`, `test_cell_direction_model.py`, `test_cell_direction_unit.py`, `ui/src/components/beatgrid/cellSplit.test.ts`, `cellSplitRoundTrip.test.tsx` |

## §4. 제외 범위

### Out of Scope — 새 동작과 코드 변경

- 이 SPEC 은 이미 출하된 동작의 사후 기록이다. 코드·시험·UI·콘솔·서버 런타임을 바꾸지 않는다.
- 칸 만들기·지우기를 서버와 화면에 배선하는 일(순수 함수 `row_create`·`row_delete` 는 있으나 호출처가 없다)은 후속 카드의 몫이다.

### Out of Scope — 다른 SPEC 이 맡는 동작

- 프리셋 계획·재사용·웨이브 프리셋·자동 배치·뒤옆 출력은 `SPEC-LDRHYTHM-002` 가 맡는다.
- 작업본 라이브러리·음원 링크·재접속 뒤 상태 복원은 `SPEC-LDBEAT-003` 이 맡는다.
- 박자 격자 화면 자체(구간 색·에너지·큐 패널·무대 개념도)와 M1 프로브는 `SPEC-LDBEAT-001` 본문이다. 인벤토리 C10(#701~#757 무태그 26건)은 그 본문 범위 안이며 이 SPEC 이 다시 서술하지 않는다.

## §5. 알려진 한계 (코드에서 읽은 것)

1. 서버 `beat_grid_apply(cells=…)` 는 마지막 반영 기록도 소유 기록도 없는 곡이면 「이 곡은 아직 콘솔 반영 기록이 없어요 — 「전체 다시 반영」으로 먼저 맞춰 주세요」로 거절한다. 첫 반영에서 화면이 곡 전체를 보내도록 바뀐 것(REQ-LDBEAT2-007)은 이 거절을 우회하는 화면 쪽 해법이며 서버 거절은 그대로다.
2. `Delete Sequence <n> /NoConfirm` 줄은 코드 주석이 「실기 선례가 없는 가설 문법」(`@MX:WARN`)이라고 적는다. 거절되면 승인 카드가 그 줄을 보이므로 감독이 보게 된다.
3. 새 시퀀스 첫 큐 저장 어순(`Store Sequence S Cue N`)은 코드 주석이 「이 에미터가 낸 줄을 실기에서 받았다는 확인은 아직 없다」고 적는다.

## §6. 인벤토리와 코드가 달랐던 곳

| 인벤토리 서술 | 코드에서 읽은 것 |
|---|---|
| 「칸을 옮기고, 나누고」 (C3) | `cell_split`·`cellSplit.ts` 는 시간으로 칸을 쪼개지 않고 한 칸의 왼쪽·오른쪽 색을 따로 정한다(REQ-LDBEAT2-016). |
| 「쓰기 잠김은 칸 보류로 처리한다」 (C1) | 「쓰기 잠김」은 콘솔 잠금이 아니라 M1 프로브 미통과 항목에 의존하는 칸의 보류다(REQ-LDBEAT2-005). |
| 「줄이 16개를 넘으면 16줄 단위로」 (C1) | 16 은 코드 상수가 아니라 실측 데이터 파일 `measured_console.yaml` 의 값이다(REQ-LDBEAT2-003). |
| 칸 편집 PR-1 이후 칸 만들기·지우기가 있는 듯한 서술 | 서버 경로는 옮기기만 받는다. 만들기·지우기는 배선돼 있지 않다(REQ-LDBEAT2-013). |

## §7. 검증하지 못한 것

- 시험을 실행하지 않았다. 「시험」 열의 파일은 `ls` 와 `grep` 으로 존재와 이름만 확인했다.
- 실기 콘솔 동작은 확인하지 않았다. 콘솔에 닿는 경로의 실기 확인 상태는 `SPEC-LDBEAT-001` `progress.md` 의 t608 체크리스트가 기준이며, 이 SPEC 은 그것을 대체하지 않는다.
- 소스 PR 번호는 인벤토리 값이며 #864 만 머지 커밋을 확인했다.
- `session.py`(약 18,000줄)는 이 SPEC 이 인용한 함수만 읽었다. 허브 파일이라 다른 클러스터의 코드가 같은 파일에 있다.
