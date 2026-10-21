# SPEC-LDRHYTHM-002 — 인수 기준 (as-built)

각 AC 는 `AC-LDRHYTHM2-NNN` 이며 `spec.md` 의 같은 번호 REQ 를 검증한다. 검증은 **저장소에 이미 있는 시험**을 가리킨다. 이 SPEC 을 쓰며 시험을 실행하지는 않았다(`spec.md` §7). 시험이 없는 곳은 「시험 없음」이라고 적었다. 시험 경로의 서버 쪽은 `server/tests/`, 화면 쪽은 `ui/src/components/`(하위 `beatgrid/` 포함)다.

## AC-LDRHYTHM2-001 — 계획 카드 한 장과 승인 뒤 기록 [REQ-LDRHYTHM2-001]

- **Given** 콘솔 풀을 읽을 수 있는 곡과 격자
- **When** 「프리셋 계획 만들기」 후 승인 카드를 승인·거절·무응답으로 각각 처리하면
- **Then** 승인이면 칸의 번호 참조와 승인 기록이 적히고, 거절·차단·무응답이면 격자가 바이트까지 그대로다. 승인 직후 송신 직전 재확인이 묶음을 막으면 걸린 프리셋만 빼고 새 카드가 한 번 더 올라오며 그 이상은 올라오지 않는다.
- **시험**: `test_preset_plan.py`, `test_preset_plan_entry.py`, `test_preset_plan_presend.py`, `test_preset_plan_fill.py`, `test_preset_plan_store_all.py`, `test_preset_plan_latency.py`

## AC-LDRHYTHM2-002 — 계획 규칙(묶기·빈 번호·미정·저장 줄) [REQ-LDRHYTHM2-002]

- **Given** 같은 디머 값을 쓰는 칸 여럿, 점유된 번호가 섞인 풀, 값이 정해지지 않은 후보, 칸에 이미 번호가 있는 색·위치
- **When** 계획을 만들고 저장 줄을 붙이면
- **Then** 같은 값은 한 프리셋으로 묶여 칸 수가 세어지고, 번호는 빈 번호만 받으며, 미정은 지어내지 않고 「미정」으로 남고, 이미 번호가 있는 칸은 덮이지 않는다. 같은 값을 여러 그룹이 쓰면 그룹 한 선택 줄 하나로 저장된다.
- **시험**: `test_preset_plan.py`, `test_preset_plan_store_all.py`, `test_preset_plan_fill.py`, `test_planned_positions.py`
- **부분 확인**: 둘째 디머(`Dimmer2`) 그룹의 별도 저장과 `split` 후보 줄을 어느 시험이 직접 단언하는지는 이 SPEC 을 쓰며 확인하지 못했다.

## AC-LDRHYTHM2-003 — 같은 프리셋 재사용과 기록 이월 [REQ-LDRHYTHM2-003]

- **Given** 콘솔에 앞서 저장한 프리셋이 있고 같은 곡 재분석, 다른 곡 새 분석, 저장 작업본 불러오기 중 하나가 일어난 뒤
- **When** 다음 계획을 만들면
- **Then** 번호가 콘솔에 있고 이름·기록이 같은 디머·색·효과는 다시 저장하지 않고 재사용되며(색은 소속 장비가 덮일 때도), 번호가 사라졌거나 이름이 바뀌었거나 효과 풀을 못 읽었으면 재사용되지 않는다. 서브 광원 범위 없이 저장된 디머는 범위가 필요한 계획에서 재사용되지 않는다.
- **시험**: `test_preset_reuse_after_new_analysis.py`, `test_preset_reuse_cross_song.py`, `test_preset_reuse_after_library_load.py`, `test_color_reuse_by_members.py`, `test_effect_reuse_and_gate_t_gatefix.py`, `test_preset_plan_dimmer_reuse.py`, `test_movement_effect_preset.py`

## AC-LDRHYTHM2-004 — 웨이브 프리셋 [REQ-LDRHYTHM2-004]

- **Given** 확인된 콘솔 그룹의 줄, 곡 BPM, 정해진 스피드 마스터, 읽힌 효과 풀
- **When** 기본 다섯 개 또는 직접 만들기로 저장을 요청하면
- **Then** 마스터 BPM 줄이 묶음 맨 앞에 한 번만 있고 다섯 개가 한 승인 카드로 나가며, 이름은 영문·숫자뿐이고 효과 풀의 낮은 빈 번호부터 받는다. 같은 이름이 모두 있으면 아무것도 보내지 않고 카드도 열지 않는다. 확인된 그룹 번호 없는 줄, 알 수 없는 줄, 곡 템포 없음, 읽지 못한 효과 풀은 거절된다. 직접 만들기는 잘못된 값을 이유와 함께 거절하고 이미 있는 콘솔 이름도 거절한다. 서브 광원 줄은 뒤 점 범위 선택으로 저장된다.
- **시험**: `test_wave_presets.py`, `test_beat_grid_wave_presets.py`, `test_wave_custom.py`, `test_beat_grid_wave_custom.py`, `test_wave_sub_selection.py`, `ui/src/components/beatgrid/wavePresets.test.tsx`, `waveCustom.test.tsx`, `ui/src/components/BeatGrid.waveDrawer.test.tsx`

## AC-LDRHYTHM2-005 — 곡마다 스피드 마스터 번호 [REQ-LDRHYTHM2-005]

- **Given** 비어 있거나 일부 곡이 적힌 기록 파일
- **When** 곡의 스피드 마스터 번호를 요청하면
- **Then** 첫 곡은 가장 큰 빈 번호(15)를, 둘째 곡은 다음 빈 번호를 받고, 이미 기록된 곡은 같은 번호를 다시 받으며 두 번 기록되지 않는다. 공백·밑줄·대소문자만 다른 제목은 같은 곡이다. 15개가 모두 찼거나 기록을 읽지 못했거나 범위(1~15) 밖 번호가 기록돼 있으면 번호를 만들지 않고 거절한다.
- **시험**: `test_song_speed_master.py`

## AC-LDRHYTHM2-006 — 계획표 패널과 웨이브 컨트롤 [REQ-LDRHYTHM2-006]

- **Given** 서버가 보낸 「연출 프리셋 계획」 마크다운 표
- **When** 화면이 그것을 읽으면
- **Then** 행(종류·이름·값·후보 번호·칸 수·상태·감독이 고칠 값)과 「이 카드 밖」·「미정」 사유가 값을 지어내지 않고 나온다. 웨이브 컨트롤은 그룹 번호가 확인된 줄만 고르게 하고, 직접 만들기 값 검사는 서버와 같은 규칙으로 사유를 낸다.
- **시험**: `ui/src/components/beatgrid/presetPlan.test.tsx`, `wavePresets.test.tsx`, `waveCustom.test.tsx`

## AC-LDRHYTHM2-007 — 구간 단위 초안 [REQ-LDRHYTHM2-007]

- **Given** 마디 지도(킥 진입·빌드업·브레이크·드롭 사건)와 줄 구성
- **When** `generate_segment_draft` 로 초안을 만들면
- **Then** 구간은 첫 마디·모든 이벤트 시작 마디·드롭 다음 마디에서 시작해 모든 마디를 정확히 한 번씩 덮고, 구간 종류는 규칙 순서대로 정해지며(브레이크는 뒤 2마디 안에 드롭이 올 때만 브릿지, 에너지로는 정하지 않음), 마지막 드롭이 마지막 마디에 있으면 그 뒤 구간이 없다. 도입·벌스·후렴에서 옆(SIDE) 줄과 역할 없는 줄도 켜진다. 빌드·브레이크·벌스·도입에는 강조가 없다.
- **시험**: `test_arrange_segments.py`(112개), `test_arrange_side_allocation.py`, `test_arrange_generator.py`, `test_arrange_colors.py`, `test_arrange_structured_values.py`, `test_section_kinds_from_bar_map.py`

## AC-LDRHYTHM2-008 — 곡별 규칙과 브레이크·후렴 직전·예고 [REQ-LDRHYTHM2-008]

- **Given** 브레이크가 있는 마디 지도와 기본 정책
- **When** 초안을 만들면
- **Then** 브레이크 마디에서 리듬·강조 줄은 쉬고 워시·FOH 는 그대로이며 무빙은 건드리지 않고, 브레이크 다음 마디에 리듬이 돌아온다. 정책에서 `break_hold_wash` 를 끄면 이 규칙이 빠진다. 후렴 직전 마디는 리듬 줄이 쉬고 무빙은 이미 어두울 때만 쉬며 강조·MIB 문제를 새로 만들지 않는다. 강조 구간 직전에 블라인드 줄의 예고 칸이 서고 후렴·드롭 안에서는 무빙이 비워지지 않는다. 실제 LOVE ATTACK 마디 지도에서 브레이크 마디가 워시를 유지한다.
- **시험**: `test_arrange_segments.py`(`test_break_bars_rest_the_rhythm_and_accent_lines_and_keep_the_rest`, `test_rhythm_comes_back_on_the_bar_after_a_break`, `test_break_hold_can_be_turned_off_per_song`, `test_real_love_attack_break_bars_hold_the_wash`, `test_movers_rest_before_a_chorus_only_when_already_dark`, `test_pre_chorus_blackout_adds_no_strobe_blind_or_mib_trouble`, `test_the_notice_*`, `test_movers_are_never_darkened_inside_a_chorus_or_a_drop`)

## AC-LDRHYTHM2-009 — 박 나누기와 무빙 축 [REQ-LDRHYTHM2-009]

- **Given** 박자표가 있는 마디 지도와 `motion_period_beats` 설정
- **When** 초안의 무빙 칸을 보면
- **Then** 기본 4박이면 4/4 곡의 무빙 웨이브는 한 바퀴가 한 마디(`("bar", 1)`)이고 규칙을 끄면 기존 마디 주기이며 2~4 밖의 값은 거절된다. 웨이브 축은 실측 기록의 보이는 축을 따른다.
- **시험**: `test_arrange_segments.py`(`test_real_love_attack_mover_waves_turn_once_every_four_beats`, `test_beat_division_rule_can_be_turned_off_per_song`, `test_a_wave_outside_two_to_four_beats_is_refused`), `test_wave_axes_follow_measured_visibility.py`

## AC-LDRHYTHM2-010 — 곡 끝이 음악의 실제 끝을 따른다 [REQ-LDRHYTHM2-010]

- **Given** 곡 끝으로 에너지가 잦아드는 마디 지도, 큰 한 방으로 끝나는 마디 지도, 끝까지 큰 마디 지도
- **When** 곡 끝 따르기가 켜진 초안을 만들면
- **Then** 잦아드는 곡은 조용한 꼬리에서 모든 리듬층이 쉬고 새로 켜지는 줄이 없고 음악이 끝나는 자리에서 정리되며, 정지된 빛은 꼬리 시작에서 끊기지 않고 잦아듦과 함께 정착한다. 꼬리 안의 브레이크는 구간 경계가 아니다. 큰 한 방 곡은 임팩트 룩을 내고 모든 것이 꺼진다. 끝까지 큰 곡은 마지막 마디까지 리듬을 유지한다. 규칙은 곡별 기본값이라 끌 수 있고, 실제 LOVE ATTACK 꼬리는 음악을 따라 나간다.
- **시험**: `test_arrange_song_ending.py`(`test_a_decaying_ending_*`, `test_static_light_settles_with_the_decay_instead_of_cutting_at_its_start`, `test_breaks_inside_the_quiet_tail_are_not_section_boundaries`, `test_the_ending_rule_is_a_per_song_default_that_can_be_turned_off`, `test_a_final_hit_lands_an_impact_look_then_everything_goes_out`, `test_a_song_loud_to_the_very_end_keeps_its_rhythm_to_the_last_bar`, `test_love_attack_tail_follows_the_music_out`)
- **부분 확인**: 「꼬리 마디에서 켜진 채 끝나는 줄에 꺼진 끝 칸」(`_ending_dark`)은 `test_arrange_segments.py` 의 `test_every_line_ends_dark_with_release_at_the_last_bar` 가 관련 있어 보이나 이 SPEC 을 쓰며 단언 내용을 읽지는 않았다.

## AC-LDRHYTHM2-011 — 초안 보류·적용·거절 [REQ-LDRHYTHM2-011]

- **Given** 마디 지도가 있는 곡
- **When** 자동 배치를 제안·적용·거절·재적용하면
- **Then** 제안은 초안을 보류만 하고 격자는 바뀌지 않으며, 마디 지도가 없으면 거절된다. 적용은 격자를 한 번만 쓰고 알리며 같은 초안의 두 번째 적용은 거절된다. 칸이 없는 마디에는 칸이 만들어지고 감독이 고친 칸은 남으며 같은 초안을 두 번 적용해도 같은 격자다. 바뀐 칸이 0개면 실패로 알린다. 새 분석 작업본은 빈 격자로 시작해 자동 배치가 칸을 놓는다.
- **시험**: `test_arrange_apply.py`, `test_arrange_draft_wiring.py`, `test_new_analysis_timeline.py`

## AC-LDRHYTHM2-012 — 리듬 분석 값 [REQ-LDRHYTHM2-012]

- **Given** 곡 소리와 마디 지도
- **When** `build_rhythm` 이 `rhythm` 블록을 만들고 검증을 통과하면
- **Then** 킥 박과 스네어 박이 분리되고 큰 히트가 잡히며, 점수는 이 곡 안에서 중심화된 상대값이고 평평한 곡에서도 0 으로 나누지 않는다. 구간 경계는 마디 시작으로 옮겨지고 겹침이 가장 큰 구간의 등급을 갖는다. `rhythm` 은 선택 키로서 일관된 블록만 검증을 통과하고 모르는 최상위 키는 여전히 거절된다. 박 시각이 마디 지도의 박과 맞지 않으면 거절된다.
- **시험**: `test_rhythm_features.py`

## AC-LDRHYTHM2-013 — 뒤·옆 줄 기본 위치와 서브 광원 범위 [REQ-LDRHYTHM2-013]

- **Given** Pan·Tilt 능력이 판독된 뒤·옆 줄과 서브 광원에 밝기가 실린 기종의 연속 소속 줄
- **When** 초안과 디머 저장을 만들면
- **Then** 조준할 수 있는 줄의 켜진 칸에 `Center` 계획 위치가 붙고, 서브 광원 줄은 큐 밝기와 단일 그룹 디머 저장이 뒤 점 범위(`Fixture a Thru b.`)로 나가며, 판독을 못 한 줄에는 기본 위치도 범위도 붙지 않는다. 일반 줄은 그룹 선택을 그대로 쓴다.
- **시험**: `test_sub_geometry_selection.py`, `test_planned_positions.py`, `test_beat_grid_pan_tilt_tracks.py`, `test_wave_sub_selection.py`, `test_capability_join.py`

## AC-LDRHYTHM2-014 — 능력 판독 [REQ-LDRHYTHM2-014]

- **Given** 기종·모드가 읽히는 장비와 잘린 읽기
- **When** `read_rig_capabilities` 를 부르면
- **Then** 움직이는 헤드는 기종·모드와 Pan·Tilt 를 갖고, 고정 장비는 Pan·Tilt 가 없으며, 속성 철자는 콘솔이 답한 대로 나오고, 역방향 Zoom 범위는 방향을 유지하고, 잘린 읽기는 부재가 아니라 사유와 함께 못 읽음으로 보고된다.
- **시험**: `test_capability_join.py`, `test_capability_read.py`

## AC-LDRHYTHM2-015 — 무대 빔 움직임과 계획 표시 [REQ-LDRHYTHM2-015]

- **Given** `app_movement`·방향 값·효과 번호 기록 중 하나를 가진 무빙 칸과 재생 시각
- **When** 화면이 빔 자세를 계산하면
- **Then** 구조화 값에서만 읽고(라벨 글자는 읽지 않음) 주기를 모르면 움직이지 않으며, 콘솔 번호가 없는 자리에만 계획 표시(점선·흐린 글자)가 붙고 원본 격자는 바뀌지 않는다.
- **시험**: `ui/src/components/beatgrid/moverMotion.test.ts`, `StageConceptSvg.test.ts`, `StageConceptSvgMotion.test.tsx`, `server/tests/test_beat_grid_planned_marks.py`, `server/tests/test_app_movement_t548.py`

## AC-LDRHYTHM2-016 — 앱 경로 밖 모듈의 현재 상태 [REQ-LDRHYTHM2-016]

- **Given** `server/fx/phase_patterns.py` 와 `server/design/grid_shape.py`
- **When** 비테스트 호출처를 찾고 시험을 보면
- **Then** `phase_patterns` 의 위상 순서·홀짝·날개·높이 단·`/Selective` 묶음은 시험이 덮고 같은 위상 장비는 함께 선택되며 장비 번호를 바꿔도 모양이 같다. `grid_shape` 는 칸 모양 분류·구간 분포 거리·비교 범위 자르기를 시험이 덮는다. 두 모듈 모두 서버 앱 코드의 호출처가 없다.
- **시험**: `test_phase_patterns.py`, `test_grid_shape.py`
- **측정(이 SPEC 을 쓰며 한 것)**: `grep -rn "phase_patterns\|phase_effect_commands" server --include='*.py'` 에서 시험·자기 파일을 뺀 결과가 비어 있었고, `grep -rn "grid_shape" server tools` 에서 시험·자기 파일을 뺀 결과도 비어 있었다(`spatial/presets.py` 의 `_grid_shape` 는 이름만 같은 다른 함수다).

## Definition of Done (as-built)

- [x] 요구사항 16개가 코드 `파일:함수` 로 추적된다(`spec.md` §2).
- [x] AC 16개가 존재하는 시험 파일에 대응한다. 직접 단언을 확인하지 못한 곳은 「부분 확인」으로 적었다.
- [ ] 위 시험들을 `origin/main` `e4bf3f03` 이후 트리에서 실행한 통과 증거 — 이 SPEC 에는 없다. 후속 sync 검증 몫이다.
- [ ] 실기 콘솔 확인 — 이 SPEC 은 대체하지 않는다.
