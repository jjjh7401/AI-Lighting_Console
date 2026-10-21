---
id: SPEC-LDRHYTHM-002
title: "리듬 연출 앱 구현 — 프리셋 계획·재사용·리듬층·뒤옆 출력 (as-built)"
version: "0.1.0"
status: implemented
created: 2026-10-21
updated: 2026-10-21
author: jaihyun
priority: P2
phase: "Lighting Copilot v1.2 target"
module: "server/design/preset_plan.py, server/design/preset_plan_store.py, server/design/wave_presets.py, server/design/wave_custom.py, server/design/speed_master_registry.py, server/design/arrange_segments.py, server/design/arrange_generator.py, server/design/arrange_policy.py, server/design/arrange_apply.py, server/design/arrange_draft_store.py, server/design/capability_join.py, server/design/beat_grid_stage.py, server/design/beat_grid_planned.py, server/design/grid_shape.py, server/prechk/capability_read.py, server/audio/rhythm.py, server/fx/phase_patterns.py, server/web/session.py(beat_grid_preset_plan·beat_grid_draft_*·_beat_grid_wave_*), ui/src/components/beatgrid/(presetPlan·PresetPlanPanel·WavePresetControls·moverMotion), ui/src/components/BeatGridStage.tsx"
lifecycle: spec-anchored
tags: "as-built, rhythm, preset-plan, preset-reuse, wave-preset, speed-master, auto-arrangement, music-ending, back-side-output, sub-light"
tier: M
related_specs: [SPEC-LDRHYTHM-001, SPEC-LDARRANGE-001, SPEC-LDBEAT-001, SPEC-LDBEAT-002, SPEC-LDBEAT-003, SPEC-LDBARMAP-001]
---

# SPEC-LDRHYTHM-002 — 리듬 연출 앱 구현: 프리셋 계획·재사용·리듬층·뒤옆 출력 (as-built)

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-21 | 최초 작성. **as-built SPEC** — `SPEC-LDRHYTHM-001` 이 스스로 「앱 구현은 다음 SPEC 의 일(M4+)」이라고 선언(`spec.md` §2, §4 첫 항목, frontmatter `module`)했는데 그 다음 SPEC 이 없었다. 그 사이 PR 99건·커밋 제목 202개가 LDRHYTHM-001 태그를 빌려 앱 코드를 출하했다(인벤토리 §1). 이 SPEC 이 그 정식 후속이다. 입력: 인벤토리 클러스터 C4(프리셋 계획·재사용·웨이브), C5 중 리듬층·자동 배치 구간 규칙·곡 끝, C6(뒤·옆 줄 출력, 서브 광원). 새 요구사항이 아니라 `origin/main` `e4bf3f03` 코드에서 읽은 현재 동작이다. 코드·시험·UI·콘솔·서버 런타임은 바꾸지 않았다. |

## §0. as-built SPEC 읽는 법

1. 요구사항은 현재 동작의 기술이다. 「코드 근거」는 이 SPEC 을 쓰며 읽은 `파일:함수`, 「시험」은 저장소에 있는 시험 파일이다. 시험이 없으면 「시험 없음」이다.
2. 「소스 PR」은 인벤토리 §4.2 값이다. 이 SPEC 을 쓰며 머지 커밋을 직접 확인한 것은 #861(`ccd28188`)과 #865(`e4bf3f03`)뿐이다.
3. 인벤토리와 코드가 달랐던 곳은 §6 에 적었다. 둘이 다르면 코드를 따랐다.
4. 시험을 실행하지 않았다. 「시험」 열은 존재 증거이지 통과 증거가 아니다(§7).

## §1. 범위와 소스 PR

| 클러스터 | 다루는 동작 | 소스 PR(인벤토리 §4.2) |
|---|---|---|
| C4 프리셋 계획·재사용·웨이브 | 색·위치·디머·효과 프리셋을 승인 카드 한 장으로 계획해 저장, 콘솔에 있는 같은 프리셋 재사용, 웨이브 프리셋 5종과 직접 만들기, 곡별 스피드 마스터 | #731 #750 #752 #754 #762 #766 #775 #782 #805 #810 #819 #838 #861 |
| C5 자동 배치와 리듬층 | 마디 지도로 구간 단위 초안, 브레이크·후렴 직전·박 나누기·곡 끝 규칙 | #707 #713 #760 #767 #770 #771 #772 #774 #778 #803 #807 #811 #814 #818 #840 #849 #850 #852 #853 #865 (+ 직계 #768) |
| C6 뒤·옆 줄 출력 | 뒤·옆 줄 기본 위치, 서브 광원(뒤 점 범위), 둘째 디머, 그룹 소속 장비 | #800 #806 #817 #824 #826 #828 |

C5 의 **배치 화면 쪽 첫 묶음**(생성기의 데이터 모양과 역할×마디 초안)은 `SPEC-LDARRANGE-001`(draft)이 서술한다. 이 SPEC 은 그 뒤에 쌓인 구간 단위 생성기와 규칙을 서술한다.

## §2. 요구사항 (GEARS, 현재 동작)

주체 표기: 「서버」는 `server/web/session.py` 의 `ChatSession`.

### 2.1 R1 — 프리셋 계획·재사용 (REQ-LDRHYTHM2-001~006)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDRHYTHM2-001 | **When** 감독이 「프리셋 계획 만들기」를 누르면(`beat_grid_apply` 의 `mode: "preset_plan"`), 서버 **shall** 콘솔 풀(디머·색·위치·효과)을 읽기만 하고, 계획(순수 함수)을 만들고, 색·위치의 그룹·장비를 읽어 저장 줄을 붙인 뒤 디머·색·위치 프리셋과 칸의 `app_movement` 마다 만든 움직임 효과 프리셋(`_movement_effect_presets`, 저장 줄이 붙거나 재사용되는 것)을 승인 카드 한 장·승인 한 번으로 올린다. 승인이 **통과한 뒤에만** 칸의 번호 참조와 승인 기록을 적고, 거절·차단·무응답이면 격자는 바이트까지 그대로다. 승인 창이 떠 있는 사이 저장할 번호가 채워졌거나 풀을 다시 못 읽으면 송신 직전 재확인이 묶음 전체를 0줄로 막고, 서버는 걸린 프리셋만 계획에서 빼 새 카드를 한 번 더(한 번 눌러 두 장까지) 올린다. 계획표는 `chat_response`(summary 「연출 프리셋 계획」)의 마크다운 표로 먼저 보낸다. | `session.py:beat_grid_preset_plan`; `server/web/app.py`(`mode == "preset_plan"` 분기); `preset_plan.py:build_preset_plan`, `save_commands`, `apply_plan_references`, `plan_table_markdown`, `card_reason` | `server/tests/test_preset_plan.py`, `test_preset_plan_entry.py`, `test_preset_plan_presend.py`, `test_preset_plan_fill.py`, `test_preset_plan_store_all.py`, `test_preset_plan_latency.py` |
| REQ-LDRHYTHM2-002 | **The** 계획 **shall** 같은 값은 한 프리셋으로 묶고 칸 수를 센다. 번호는 읽은 콘솔 풀에서 빈 번호만 고르며(이 계획이 이미 고른 번호도 점유로 친다) 있는 번호는 덮지 않는다. 값·이름·대상 그룹이 확정되지 않은 것은 지어내지 않고 「미정」으로 남기고, 앱이 기본값을 쓴 항목은 승인 카드의 「감독이 고칠 값」으로 모은다. 같은 디머 값을 여러 그룹이 쓰면 프리셋은 하나이고 저장은 그룹 한 선택(`Group 4 + 7 …`)으로 한 번에 한다. 둘째 디머(`Dimmer2`)를 가진 그룹은 그 속성을 따로 저장해 한 프리셋에 `Dimmer2` 가 빠지지 않게 한다. 색은 기존 색 경로(`color_preset_outcomes`)로, 위치는 그룹마다 따로 장비마다 「x 유지·y=cy·z=0」 바닥점으로 저장 줄을 만들고(근사값이라 「감독이 고칠 값」을 한 줄 남긴다) 칸을 이미 번호가 가리키면 덮어쓰지 않는다. 칸의 `split`(왼쪽·오른쪽 색)은 색이 정해진 쪽마다 후보 한 줄을 내되 이름·저장 줄·칸 참조는 만들지 않는다. | `preset_plan.py:_dimmer_value_lines`, `_reserve_next`, `_planned_color_presets`, `_planned_position_presets`; `preset_plan_store.py:attach_color_store`, `attach_floor_position_store`, `store_candidates` | `test_preset_plan.py`, `test_preset_plan_store_all.py`, `test_preset_plan_fill.py`, `test_planned_positions.py` |
| REQ-LDRHYTHM2-003 | **When** 콘솔에 이미 같은 내용의 프리셋이 있으면, 계획 **shall** 새 번호에 다시 저장하지 않고 그 번호를 재사용한다. 판정은 콘솔 이름과 격자의 저장 기록 대조다. 디머는 콘솔이 이름에 붙인 `#숫자` 를 허용하되 서브 광원 범위가 같아야 하고, 색은 같은 RGB·같은 그룹이거나 소속 장비가 저장 그룹들에 모두 덮일 때(읽은 소속만 인정) 재사용하며, 위치는 같은 번호·이름·기록이고, 효과는 같은 이름·같은 내용의 앱이 만든 것이다. 번호가 콘솔에서 사라졌거나 이름이 바뀌었거나 풀을 못 읽었으면 재사용하지 않는다. **When** 같은 곡을 다시 분석하거나, 다른 곡을 새로 분석하거나, 저장한 작업본을 불러오면, 서버 **shall** 직전 격자의 콘솔 프리셋 저장 기록을 새 작업본에 이월해(`carry_console_preset_records`) 이 재사용이 끊기지 않게 한다. | `preset_plan.py:_reusable_dimmer_slot`, `_reusable_color_slot`, `_members_covered`, `_reusable_position_slot`, `_reusable_effect_slot`; `server/design/analysis_timeline.py:carry_console_preset_records`; `server/web/timeline_api.py`(불러오기); `session.py:_start_analysis_timeline` | `test_preset_reuse_after_new_analysis.py`, `test_preset_reuse_cross_song.py`, `test_preset_reuse_after_library_load.py`, `test_color_reuse_by_members.py`, `test_effect_reuse_and_gate_t_gatefix.py`, `test_preset_plan_dimmer_reuse.py`, `test_movement_effect_preset.py` |
| REQ-LDRHYTHM2-004 | **When** 감독이 줄 하나에서 「웨이브 프리셋 만들기」를 누르면(`mode: "wave_presets"` 또는 `"wave_custom"`), 서버 **shall** 출하 효과 라이브러리의 틀에 한 주기 박 수를 얹은 웨이브 프리셋을 「All 1」 효과 풀(풀 21)의 빈 번호에 `/Universal` 로 저장하는 묶음을 한 송신·한 승인 카드로 낸다. 기본 다섯 개는 디머 사인 1박·2박·4박과 컬러 무지개 2박·웜쿨 2박이다. 속도는 곡 BPM 을 `Master 3.<n> At BPM` 으로 묶음 맨 앞에 한 번만 깔고 한 주기 박 수를 `At Measure`·`At SpeedMaster <n>` 으로 묶으며 고정 `At Speed` 는 쓰지 않는다. 콘솔 이름은 영문·숫자만이다. 같은 이름이 효과 풀에 이미 있으면 건너뛰고, 보낼 것이 없으면 카드도 열지 않는다. 콘솔 그룹 번호가 확인되지 않은 줄, 곡 BPM 을 못 읽은 곡, 스피드 마스터 번호를 못 정한 곡, 못 읽은 효과 풀은 아무것도 보내지 않고 거절한다. 감독이 모양(사인·무지개·웜쿨)·박 수(1·2·4)·이름을 고르는 「직접 만들기」는 같은 검사(`wave_custom`)를 거치고 콘솔 이름이 이미 있으면 거절한다. 서브 광원에 밝기가 실린 줄은 뒤 점 범위로 선택한다. | `server/design/wave_presets.py:WAVE_PRESETS`, `plan_wave_writes`, `wave_save_commands`; `server/design/wave_custom.py:wave_spec_from_fields`, `custom_wave_problem`; `session.py:_beat_grid_wave_setup`, `_beat_grid_wave_send`, `beat_grid_wave_presets`, `beat_grid_wave_custom`; `server/web/messages.py:BEAT_GRID_APPLY_MODES` | `test_wave_presets.py`, `test_beat_grid_wave_presets.py`, `test_wave_custom.py`, `test_beat_grid_wave_custom.py`, `test_wave_sub_selection.py`, `ui/src/components/beatgrid/wavePresets.test.tsx`, `waveCustom.test.tsx`, `ui/src/components/BeatGrid.waveDrawer.test.tsx` |
| REQ-LDRHYTHM2-005 | **The** 앱 **shall** 곡마다 스피드 마스터 번호를 하나씩 기록해(`speed_masters.json`, 곡 열쇠는 대소문자·공백·밑줄을 무시) 곡이 같은 번호를 써 다른 곡의 효과·웨이브 속도를 덮는 일을 막는다. 기록이 없는 곡은 아직 어느 곡에도 없는 번호 가운데 가장 큰 번호를 15부터 내려가며 받고, 16 은 콘솔 오디오 입력 BPM 마스터라 쓰지 않는다. 이미 콘솔에 쓴 번호는 시드로 먼저 적힌다. 기록을 읽지 못했거나 모양이 틀리거나 범위(1~15) 밖이거나 번호가 모두 찼으면 번호를 지어내지 않고 배정하지 않는다. | `server/design/speed_master_registry.py:assign_speed_master`, `read_registry`, `is_speed_master`, `with_song_speed_master` | `server/tests/test_song_speed_master.py` |
| REQ-LDRHYTHM2-006 | **The** 화면 **shall** 서버가 `chat_response`(summary 「연출 프리셋 계획」)로 보낸 마크다운 계획표를 행으로 읽어(종류·이름·값·후보 번호·칸 수·상태·감독이 고칠 값 여부) 격자 위 패널로 보이되 값을 지어내지 않고, 패널은 모달이 아니어서 승인 카드를 가리지 않는다. 웨이브 컨트롤은 콘솔 그룹 번호가 확인된 줄만 고르게 하고 직접 만들기 값을 서버와 같은 규칙으로 먼저 검사한다. | `ui/src/components/beatgrid/presetPlan.ts`, `PresetPlanPanel.tsx`, `WavePresetControls.tsx:waveTrackChoices`, `waveCustomProblem` | `presetPlan.test.tsx`, `wavePresets.test.tsx`, `waveCustom.test.tsx` |

### 2.2 R2 — 자동 배치와 리듬층 (REQ-LDRHYTHM2-007~012)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDRHYTHM2-007 | **When** 감독이 자동 배치를 요청하면(`beat_grid_draft_propose`), 서버 **shall** 마디 지도(`timeline["bar_map"]`)로 곡을 구간으로 나누고 줄(콘솔 그룹 트랙)마다 값이 바뀌는 마디에만 칸을 내는 희소 초안을 만든다. 구간은 첫 마디·모든 이벤트의 시작 마디·드롭이 끝난 다음 마디에서 시작한다. 구간 종류는 시작 마디에서 위에서부터 먼저 맞는 것으로 정한다: 도입, 드롭, 마지막 후렴, 킥 진입 분기(도입 뒤 곧바로 오는 곡의 첫 킥이면 벌스, 그 밖의 킥 진입은 후렴), 빌드, 브릿지(브레이크 끝 뒤 2마디 안에 드롭), 그 밖은 벌스이며 마디 에너지로는 종류를 정하지 않는다. 주인공 리듬층은 구간 종류가 정하고, 보조층과 움직이는 무빙은 4마디 창마다 교대한다. 역할을 정하지 못한 줄은 체이스 층으로 넣는다. 강조(블라인드·스트로브)는 큰 히트에만 두고 느린 곡이면 스트로브를 두지 않는다. 줄 구성은 콘솔 그룹·소속 장비를 읽어 빠진 장비의 줄을 붙인다(`plan_console_tracks`). 마디 지도가 없으면 거절한다. | `session.py:beat_grid_draft_propose`; `server/design/arrange_segments.py:generate_segment_draft`, `split_sections`, `_section_kind`, `_plan_windows`, `_LEAD_OF_KIND`; `arrange_generator.py:_cell_plan`; `console_tracks.py:plan_console_tracks` | `server/tests/test_arrange_segments.py`(112개), `test_arrange_side_allocation.py`, `test_arrange_generator.py`, `test_arrange_colors.py`, `test_arrange_structured_values.py`, `test_section_kinds_from_bar_map.py` |
| REQ-LDRHYTHM2-008 | **The** 배치 규칙 값 **shall** 곡마다 들며 불변 객체(`ArrangementPolicy`)로 전역 상수가 아니다. 기본값: 창 4마디, 후렴 기준 에너지 0.5, 브레이크 워시 유지 켬, 무빙 웨이브 한 바퀴 4박, 후렴 직전 비움 켬, 곡 끝 따르기 켬. **While** 마디 지도에 브레이크 사건이 덮는 마디인 동안, 생성기 **shall** 워시·FOH 줄만 켜 두고 리듬·강조 줄은 쉬게 하며 무빙 줄은 건드리지 않는다. 후렴·마지막 후렴 바로 앞 마디는 리듬 줄이 쉬고 무빙은 앞 마디가 이미 어두울 때만 쉰다(켜진 칸 사이의 한 마디 어둠은 사전이동에 모자라기 때문). 강조 구간이 바로 이어 시작하는 구간의 끝 마디에는 블라인드 줄에 예고 칸을 둔다. 무빙의 위치가 바뀌는 칸 앞은 쉼으로 비워 어둠 속 사전이동(MIB)이 가능하게 하되 후렴·드롭 안에서는 비우지 않는다. | `server/design/arrange_policy.py:ArrangementPolicy`; `arrange_segments.py`(`break_hold_wash`·`pre_chorus_blackout` 분기, `_break_bars`, `_pre_chorus_bars`, `_pre_hit_bars`, `_darken_before_moves`) | `test_arrange_segments.py`(`test_break_bars_rest_the_rhythm_and_accent_lines_and_keep_the_rest`, `test_break_hold_can_be_turned_off_per_song`, `test_movers_rest_before_a_chorus_only_when_already_dark`, `test_the_notice_*`, `test_movers_are_never_darkened_inside_a_chorus_or_a_drop`) |
| REQ-LDRHYTHM2-009 | **Where** 박 나누기 규칙이 켜져 있으면(`motion_period_beats`, 기본 4), 생성기 **shall** 무빙 웨이브 한 바퀴를 그 박 수로 적는다. 박 수가 박자표의 한 마디 박 수와 같으면 `("bar", 1)`, 아니면 `("beat", 박 수)` 이다. 규칙을 끄면(`None`) 기존 마디 주기이고, 2~4 밖의 값은 정책 생성에서 거절된다. 무빙 웨이브의 축은 확인된 그룹 번호로 실측 기록(`measured_movements.yaml`)을 읽어 실기에서 보이는 축으로 고른다. | `arrange_segments.py:_motion_period`, `_motion_axes`; `arrange_policy.py:ArrangementPolicy.__post_init__`; `server/design/beat_grid_data/measured_movements.yaml` | `test_arrange_segments.py`(`test_real_love_attack_mover_waves_turn_once_every_four_beats`, `test_beat_division_rule_can_be_turned_off_per_song`, `test_a_wave_outside_two_to_four_beats_is_refused`), `test_wave_axes_follow_measured_visibility.py` |
| REQ-LDRHYTHM2-010 | **Where** 곡 끝 따르기가 켜져 있으면(`ending_follows_music`, 기본 켬, 2026-10-21 #865), 생성기 **shall** 마디 에너지(곡 안 상대값)로 곡이 어떻게 끝나는지 읽는다. 곡 끝까지 이어지는 에너지 0.1 이하 마디들이 조용한 꼬리이고, 0.01 이하 마디들이 무음이다. 조용한 꼬리에서는 리듬·강조 줄(역할 `back`·`side`·없음·`effect`)이 쉬고 나머지 줄은 꼬리 직전 마디의 값을 붙들되 움직임만 멈춘다(무빙 웨이브는 정지, 꼬리 직전에 꺼져 있던 줄은 꺼진 채). 무음부터는 모든 줄이 꺼진다. 꼬리 바로 앞 마디에 리듬 블록의 큰 히트가 있거나, 후렴만큼 큰데 곧바로 무음이 이어지면 큰 한 방으로 읽어 강조 줄에 강조 칸을 둔다. 꼬리에서는 프레이즈마다 켜는 칸을 다시 세우지 않는다. 마지막 마디가 박이 모자란 꼬리 마디이고 줄이 켜진 채 끝나면 그 마디에 꺼진 끝 칸을 둔다. 조용한 꼬리가 없으면(곡이 끝까지 크면) 마지막 마디까지 구간 규칙대로 돈다. | `arrange_segments.py:_music_ending`, `_quiet_tail_start`, `_follow_music_ending`, `_tail_bar`, `_ending_dark`, `_ENDING_QUIET_ENERGY`, `_ENDING_SILENCE_ENERGY` | `server/tests/test_arrange_song_ending.py`(9개) |
| REQ-LDRHYTHM2-011 | **The** 자동 배치 초안 **shall** 보류 상태로만 존재한다 — 제안은 `PendingDraftStore` 에 id 로 담기고 격자와 콘솔은 바뀌지 않는다. **When** 감독이 「적용」을 누르면 서버 **shall** 보류 초안을 한 번만 꺼내 칸이 없는 마디에도 칸을 만들어 격자에 한꺼번에 반영한다(전부 맞거나 전부 안 바뀜). 감독이 직접 고친 칸은 남기고 같은 초안을 두 번 적용하면 거절한다. 바뀐 칸이 0개이면 성공처럼 보이게 두지 않고 실패로 알린다. 적용은 되돌리기 기록을 남기고 콘솔에는 쓰지 않는다. 「거절」은 보류 초안을 버린다. 보류 초안은 재연결하면 버려진다. 곡 분석이 새 작업본을 열 때 줄 구성은 비어 있고 자동 배치가 콘솔 그룹으로 만든다. | `session.py:beat_grid_draft_propose`, `beat_grid_draft_apply`, `beat_grid_draft_reject`; `server/design/arrange_apply.py:apply_arrangement_draft`; `arrange_draft_store.py:PendingDraftStore` | `test_arrange_apply.py`, `test_arrange_draft_wiring.py`, `test_new_analysis_timeline.py` |
| REQ-LDRHYTHM2-012 | **The** 오디오 분석 **shall** 마디 지도의 선택 키 `rhythm` 을 만들어(`build_rhythm`, `attach_rhythm`) 박·히트·구간 특징을 낸다. 박마다 킥·스네어·온셋은 이 곡 박들 가운데의 백분위(0~1)이고 킥·스네어 히트는 이 곡 점수가 평균 + σ 배수 이상인지 여부이며, 큰 히트(`hits[]`)는 합성 점수의 백분위와 `kind: "big"` 을 갖고, 구간(`sections[]`)은 경계를 가장 가까운 마디 시작에 맞춰 원래 구간의 D 등급과 종류를 단다. 모든 점수는 이 곡 안에서 상대로 정하고 곡마다 다른 절대 문턱을 코드에 두지 않는다. 마디 지도 진입 모듈(`bar_map_entry.py`, 세션의 `analyse_bar_map` 이 부르는 경로)이 `build_rhythm` 을 호출해 저장 모양에 붙인다. | `server/audio/rhythm.py:build_rhythm`, `big_hit_indices`, `snap_sections`, `classify_section_kinds`; `server/audio/bar_map_store.py:attach_rhythm`; `server/audio/bar_map_entry.py` | `server/tests/test_rhythm_features.py` |

### 2.3 R3 — 뒤·옆 줄 출력과 능력 판독 (REQ-LDRHYTHM2-013~014)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDRHYTHM2-013 | **When** 줄이 조준할 수 있는 뒤(`back`)·옆(`side`) 줄(`pan_tilt` 참, 소속 장비의 Pan·Tilt 능력으로 판정)이고 칸이 켜져 있으면, 생성기 **shall** 그 칸에 무대 중앙(`Center`)을 계획 위치로 준다(`STAGE_FACING_POSITION`, `AIMING_LINE_ROLES`). 감독이 칸별로 바꿀 수 있고 조준값은 장비 3D 좌표·방향에서 읽는다. 판독을 못 한 장비·줄은 기본 위치도 범위도 주지 않는다. **When** 밝기(Dimmer) 채널이 본체가 아닌 지오메트리(서브 광원)에 실린 기종의 연속 소속 줄이 있으면, 서버 **shall** 큐 밝기 줄과 단일 그룹 디머 저장을 그룹 선택이 아니라 뒤 점 범위(`Fixture a Thru b.`)로 낸다. | `server/design/arrange_policy.py:STAGE_FACING_POSITION`, `AIMING_LINE_ROLES`; `arrange_segments.py`(`pan_tilt` 분기); `capability_join.py:FixtureCapability.sub_geometry_dimmer`; `server/design/beat_grid_stage.py:mark_sub_selection_tracks`, `mark_pan_tilt_tracks`; `preset_plan.py`(`sub_selections`, `with_dimmer_sub_selections`) | `test_sub_geometry_selection.py`, `test_planned_positions.py`, `test_beat_grid_pan_tilt_tracks.py`, `test_wave_sub_selection.py`, `test_capability_join.py` |
| REQ-LDRHYTHM2-014 | **The** 장비별 능력 판독 **shall** 장비 번호(fid)마다 기종·모드·조정 가능한 축과 물리 범위를 콘솔에서 읽기만으로 조인하되, 못 읽은 장비와 부분만 읽힌 장비를 부재와 구별해 따로 두고 속성 이름은 콘솔이 답한 철자 그대로 나르며 범위를 정렬하지 않는다(Zoom 처럼 역방향인 축이 있다). 둘째 디머(`Dimmer2`)는 기종에 따라 있는 속성으로 읽혀 디머 프리셋 저장과 계획이 그 속성을 가진 그룹만 따로 다룬다. | `server/design/capability_join.py:read_rig_capabilities`; `server/prechk/capability_read.py:read_mode_capabilities`(`Dimmer2` 논리채널 읽기); `preset_plan.py`(`Dimmer2` 저장 선택) | `test_capability_join.py`, `test_capability_read.py` |

### 2.4 R4 — 화면 표현과 앱 경로 밖의 모듈 (REQ-LDRHYTHM2-015~016)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-LDRHYTHM2-015 | **The** 2D 무대 **shall** 재생 시계의 지금 시각에서 무빙 칸을 읽어 빔 각도를 계산한다. 움직임은 구조화 값에서만 읽는다: 앱 2단계 무빙(`app_movement`)이 먼저, 다음은 칸의 방향 값(`direction.movement`), 없으면 효과 번호의 격자 기록·앱 이름·콘솔 이름(「WAVE PAN 2 BEAT」 꼴) 순서이며 라벨 글자는 읽지 않는다. 주기를 모르면 움직이지 않는다. 팬 폭은 30도, 틸트 폭은 도달 거리의 0.4배이며 이는 그림 값이지 콘솔 값이 아니다. **The** 격자 **shall** 콘솔에 아직 없는 계획 값(계획 색·디머 이름·위치 이름)을 점선·흐린 글자로 구분해 보이되 원본 격자는 바꾸지 않고 「반영 이후 바뀐 칸」 비교에서 뺀다. | `ui/src/components/beatgrid/moverMotion.ts:moverMotionOf`, `PAN_SWING_DEG`, `TILT_SWING`; `ui/src/components/BeatGridStage.tsx`; `server/design/beat_grid_planned.py:attach_planned_marks` | `moverMotion.test.ts`, `ui/src/components/beatgrid/StageConceptSvg.test.ts`, `StageConceptSvgMotion.test.tsx`, `server/tests/test_beat_grid_planned_marks.py`, `test_app_movement_t548.py` |
| REQ-LDRHYTHM2-016 | **The** 장비 좌표 기반 위상 디머 효과 생성기(`server/fx/phase_patterns.py`)는 좌→우 차례·홀짝·바깥에서 안쪽(날개)·위아래 줄·높이 단의 위상을 장비 좌표만으로 정하고 `/Selective` 프리셋 저장 묶음을 만들며 장비·그룹 번호를 코드에 두지 않고, 위상이 둘 미만이면 이유와 함께 거절한다. 그러나 이 모듈은 **비테스트 호출처가 없다** — 앱 경로에 배선되어 있지 않다. 같은 방식으로 `server/design/grid_shape.py` 는 자동 배치 결과를 손으로 설계한 기본 격자와 여섯 지표(칸 수·길이 분포·구간 경계 정렬·박 패턴·강조·색)로 견주는 읽기 전용 검증 도구이고 앱 호출처가 없는 명령줄(`main`) 도구다. 판정 기준은 제안값이며 정답지 한 곡(LOVE ATTACK 기본 격자)으로만 교정됐다. | `server/fx/phase_patterns.py:fixture_phases`, `phase_effect_commands`; `server/design/grid_shape.py:compare_grids`, `main` | `server/tests/test_phase_patterns.py`, `server/tests/test_grid_shape.py` |

## §3. 제외 범위

### Out of Scope — 새 동작과 코드 변경

- 이 SPEC 은 사후 기록이다. 코드·시험·UI·콘솔·서버 런타임을 바꾸지 않는다.
- `phase_patterns` 를 앱 경로에 배선하는 일과 `grid_shape` 를 정식 검사로 승격하는 일은 이 SPEC 이 하지 않는다.

### Out of Scope — 다른 SPEC 이 맡는 동작

- 콘솔 반영·소유 기록·「콘솔 같이」·칸 편집은 `SPEC-LDBEAT-002` 가 맡는다.
- 작업본 불러오기·음원 링크·재접속·마디 지도 꼬리는 `SPEC-LDBEAT-003` 이 맡는다.
- 마디 지도 검출 자체(박·다운비트·마디 경계·사건)는 `SPEC-LDBARMAP-001`·`SPEC-LDBARMAP-002` 가 맡는다. 이 SPEC 은 그 위의 `rhythm` 특징과 소비자(배치)만 다룬다.
- 대본·시연·규칙화(M1~M3)는 `SPEC-LDRHYTHM-001` 본문이다.

## §4. 알려진 한계 (코드에서 읽은 것)

1. 곡 끝 문턱(조용한 꼬리 0.1·무음 0.01)과 브릿지 판정의 「브레이크 뒤 2마디」는 곡별 정책이 아니라 모듈 상수다(`@MX:DEBT` 가 코드에 있다). 꼬리 울림이 곡 바닥 10% 위에 머무는 곡은 잦아듦을 꼬리로 읽지 못하고 구간 규칙대로 돈다.
2. 위치 프리셋의 바닥점 목표는 근사값이다(장비마다 「x 유지·y=cy·z=0」). 그래서 항상 「감독이 고칠 값」이 한 줄 붙는다.
3. 속도 마스터 기록은 이 앱이 쓴 번호만 안다. 효과·시퀀스가 묶은 스피드 마스터를 콘솔에서 읽는 경로는 확인되지 않았다(`speed_master_registry.py` 독스트링).
4. 웨이브 프리셋은 같은 이름이 있으면 「있다」로 보고 내용을 확인하지 않는다(`plan_wave_writes` 독스트링).

## §5. 소스 문서와의 대응 — `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012 의 M4+ 후보

LDRHYTHM-001 이 후보로만 적은 네 항목이 이 앱에서 어떻게 되었는지는 이 SPEC 이 판정하지 않는다. 읽은 사실만 적는다. (a) 박·다운비트·킥 검출: `server/audio/rhythm.py`(REQ-LDRHYTHM2-012)와 `SPEC-LDBARMAP-001` 의 `bar_map.py` 가 있다. (b) 타임코드 이벤트 송신: `beat_grid_emit.py` 가 `Store Timecode`·이벤트를 만든다(`SPEC-LDBEAT-002` REQ-LDBEAT2-002·003). LDRHYTHM-001 이 인용한 `server/director/emit.py:51` 의 `PLAYBACK_MODES` 는 이제 `server/director/validate/timing.py:44` 에 있고 `emit.py` 는 삭제됐다(`06d4f4c6`). (c) `position_fx`·`plan_movement` 연결: `server/design/app_movement.py` 가 `position_fx` 를 쓴다. `plan_movement` 의 비테스트 호출처는 이 조사에서 확인하지 못했다. (d) 장면 연결 규칙: 이 조사에서 대응 코드를 찾지 않았다.

## §6. 인벤토리와 코드가 달랐던 곳

| 인벤토리 서술 | 코드에서 읽은 것 |
|---|---|
| 「위상 디머 패턴을 생성하며」 (C5) | `phase_patterns.py` 는 존재하고 시험이 있으나 비테스트 호출처가 0건이다(REQ-LDRHYTHM2-016). |
| `grid_shape.py` 를 자동 배치 구성 파일로 취급 | 읽기 전용 비교 명령줄 도구다(`argparse`, `main`). |
| `capability_read.py`·`capability_join.py` 를 C6 파일로 취급 | 두 파일은 2026-09-10 카드(t344·#395·#396)에서 생겼고, C6 에서는 `Dimmer2`(`cbab1557`)·서브 광원 판정(`0a3fdc2f`)이 더해졌다. |
| `session.beat_grid_preset_plan` 독스트링 「이 메서드는 UI 메시지에 연결돼 있지 않다」 | `app.py` 가 `mode == "preset_plan"` 일 때 이 메서드를 부른다. 독스트링이 낡았다(코드는 바꾸지 않았다). |

## §7. 검증하지 못한 것

- 시험을 실행하지 않았다. 「시험」 열은 `ls`·`grep` 으로 존재와 이름을 확인한 것이다.
- 실기 콘솔 동작은 확인하지 않았다.
- 소스 PR 번호는 인벤토리 값이며 #861·#865 만 머지 커밋을 확인했다.
- `preset_plan.py`(2,143줄)와 `arrange_segments.py`(1,190줄)는 독스트링·함수 목록·인용한 구간을 읽었고 전체 분기를 한 줄씩 따라가지는 않았다.
