# MBLightArts YouTube 6편 기반 showfile 프로세스와 Copilot 역할

> 수집일: 2026-09-11  
> 출처: YouTube playlist `PLLoCapjFPUOrfh3Q9dNqe_tTT5bGmOE7I`, 시작 영상 `_f0TaTWQ-d4`  
> 범위: MBLightArts grandMA3 busking/template showfile 튜토리얼 6편의 수동 영어 자막을 기반으로, 조명감독의 단계별 작업과 AI Lighting Copilot이 실제 콘솔 객체에 연결할 수 있는 지원 범위를 정리한다.  
> 한계: 영상 화면의 모든 클릭·풀 번호를 프레임 단위로 실측한 것은 아니다. 문서의 번호·객체명은 자막에서 확인된 범위와 grandMA3의 일반 객체 구조를 결합한 구현 설계 자료다. 실제 쇼파일 적용 전에는 콘솔 상태 조회와 operator 확인이 필요하다.

## 1. 6개 영상 범위

| # | 영상 ID | 제목 | 길이 | 핵심 주제 |
|---:|---|---|---:|---|
| 1 | `_f0TaTWQ-d4` | Create your grandMA3 BUSKING SHOWFILE in under 30 min | 10:02 | 템플릿 구조, patch → groups → presets → master macro → layout |
| 2 | `vnQLTFxY75Y` | How to adapt our MA3 SHOWFILE for new stage layouts | 54:27 | 새 무대 레이아웃 적응, patch, 2D selection grid, preset 보정, color merge |
| 3 | `kt99UOEzyrI` | Set up MA3 SEQUENCES FOR SOLO SPOTS without effort | 5:23 | override preset/sequence, solo spot, playback override master |
| 4 | `Qy1QK3YxTww` | Build your own flexible SHOWFILE FOR MA3 version 1.9 | 10:55 | auto position macro, straight down/up 기준 preset, master fade/FX control |
| 5 | `6NAFFvqTz0o` | Generate CHASER AND DELAY SWEEPS IN MA3 using cue recipes | 21:21 | tap chaser, cue recipe, Matricks pool, delay speed rate master, cook |
| 6 | `usGX42BMQAw` | Create COLOR FX in a MA3 SHOWFILE for busking | 11:07 | color FX layout, Color Picker, color bump, cfx speedmaster, recipe 기반 수정 |

이 6편은 하나의 일관된 showfile 운용 철학을 보여준다. 조명감독은 매번 새 쇼를 빈 파일에서 만들지 않고, 이미 설계된 템플릿 쇼파일을 새 무대와 fixture type에 맞게 조정한다. 핵심 작업은 다음 세 가지다.

1. **무대와 fixture를 템플릿의 객체 구조에 맞게 넣는다.**
2. **템플릿이 의존하는 groups, presets, sequences, macros, layout을 다시 생성하거나 보정한다.**
3. **실전 운용에서는 executor, group master, speedmaster, override, cue recipe로 빠르게 변형한다.**

## 2. 전체 조명연출 프로세스

### 2.1 Stage/rider 분석과 fixture inventory

조명감독은 먼저 실제 무대의 fixture category를 템플릿의 5개 main fixture group에 매핑한다. 영상 예시는 spots, washes, beams, pixel tubes/floods, LED strobes/front dimmers 계열로 구성된다.

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 입력 | rider, fixture list, truss/floor 위치, universe/address, fixture mode, front/dimmer 회로 |
| Copilot 자동화 | fixture category 후보 분류, 템플릿 main group과 매핑, patch plan 초안 생성 |
| 사용자 확인 | 실제 장비 모드, physical orientation, pan/tilt invert 필요 여부, front light group A/B 분리 |
| 콘솔 객체 | `Fixture`, `Patch`, `DMX Universe`, `Group`, `FixtureType` |
| 금지/주의 | fixture mode와 GDTF가 불명확한 상태에서 preset/sequence를 대량 저장하지 않는다. |

Copilot은 이 단계에서 "무빙 16대, 워시 14대, 빔 12대, 픽셀튜브 16개, 스트로브 8대" 같은 자연어를 곧바로 command로 바꾸면 안 된다. 먼저 `FixtureInventory`와 `TemplateRoleMapping`을 만들어야 한다.

```json
{
  "fixture_inventory": [
    {
      "label": "Spot Front",
      "count": 8,
      "fixture_type": "moving_profile",
      "role": "spot",
      "physical_position": "front_truss",
      "orientation": "hung_normal"
    }
  ],
  "template_mapping": {
    "spot": "main_fixture_group_1",
    "wash": "main_fixture_group_2",
    "beam": "main_fixture_group_3",
    "flood_pixel": "main_fixture_group_4",
    "strobe": "main_fixture_group_5"
  }
}
```

### 2.2 Patch와 fixture type 적응

영상의 핵심은 "기존 템플릿 fixture를 가능한 유지하며 type만 교체하거나, 필요하면 삭제 후 다시 patch한다"는 방식이다. 48대씩 미리 patch된 fixture group이 있고, 실제 리그가 더 적으면 중심을 기준으로 대칭을 유지하며 남기거나 교체한다.

실무 판단:

- 기존 patch를 유지하면 preset과 sequence 연결이 살아 있을 가능성이 높다.
- 완전히 삭제하면 group/preset이 grayed out 되므로 다시 생성해야 한다.
- fixture ID는 category와 truss 위치를 알아보기 쉬운 체계로 정리한다.
- 같은 fixture category라도 front/floor/mid/back 위치가 다르면 group grid에서 줄을 나눠 표현한다.

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 자동화 가능 | patch diff 생성, 기존 template fixture 유지/삭제 후보 제안, fixture ID range 제안 |
| 확인 필요 | pan/tilt invert, DMX address 충돌, fixture mode, 물리 배치와 patch 순서 일치 여부 |
| 콘솔 객체 | `Patch`, `Fixture`, `FixtureType`, `Universe`, `Fixture ID` |
| 실패 증상 | position preset이 뒤집힘, color preset 미동작, grayed out group/preset, pixel order 불일치 |

특히 Pan/Tilt 계열은 patch 직후 preset이 이상하게 보일 수 있다. 영상에서는 wash position이 반대편으로 보이자 patch의 pan/tilt invert를 조정해 해결한다. Copilot은 이 상황을 "preset을 다시 만들기" 전에 `PatchOrientationCheck`로 분리해야 한다.

### 2.3 Group construction과 2D selection grid

showfile의 이펙트 품질은 group의 2D selection grid에 강하게 의존한다. 영상에서는 main group을 `simrik` 계열로 설명하며, 이 group이 fixture category 전체를 stage geometry에 맞게 grid에 배치한다. 대칭 effect, color recipe, delay sweep, rig FX가 모두 이 grid를 기준으로 계산된다.

핵심 원칙:

- 같은 fixture category의 전체 fixture를 하나의 main `simrik` group에 넣는다.
- truss/floor 줄은 grid의 Y축 또는 별도 row로 표현한다.
- 좌우 순서와 실제 무대 방향이 맞아야 horizontal chase, odd/even, center-out이 자연스럽다.
- gap을 유지하면 실제 거리감은 반영되지만 개별 effect가 다르게 보일 수 있다.
- gap을 제거하면 템플릿 effect가 깔끔하지만 실제 무대 간격과 다를 수 있다.
- pixel fixture는 master fixture group과 sub-fixture/pixel `simrik` group을 분리한다.

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 자동화 가능 | `GroupLayoutPlan` 생성, grid 좌표 제안, gap 제거/유지 옵션 비교, sub-fixture grid 계산 |
| 확인 필요 | 실제 fixture가 좌→우인지 우→좌인지, pixel tube의 sub-fixture direction, 중앙축 위치 |
| 콘솔 객체 | `Group`, `Selection Grid`, `MAtricks`, `Grid` command |
| 위험 | 잘못된 group grid는 모든 movement/color/delay recipe를 "정상 저장됐지만 이상한 룩"으로 만든다. |

예시 `GroupLayoutPlan`:

```json
{
  "group_label": "SPOT_ALL_SIMRIK",
  "fixture_category": "spot",
  "grid": [
    { "row": 0, "source": "front_truss", "fixtures": ["1101 thru 1108"], "direction": "stage_left_to_right" },
    { "row": 1, "source": "mid_truss", "fixtures": ["1201 thru 1208"], "direction": "stage_left_to_right" }
  ],
  "gap_policy": "remove_for_template_fx",
  "symmetry_axis": "center_x",
  "requires_human_visual_check": true
}
```

### 2.4 Basic presets: position, global, prism, strobe, zoom, color

템플릿이 정상 동작하려면 fixture category별 basic preset을 다시 맞춰야 한다. 영상에서 반복되는 preset 종류는 다음과 같다.

| preset 영역 | 내용 | Copilot 해석 |
|---|---|---|
| Position | 10개 안팎의 stage/audience/fanned/blind position | movement FX와 override, layout button의 기반 |
| Global/Gobo | gobo wheel open/selection + focus value 포함 | gobo가 sharp하게 보이도록 focus까지 저장 |
| Gobo rotation | off, slow, fast 또는 방향 변형 | profile-dependent attribute |
| Prism | open, prism variant 1/2 | beam fixture만, fixture profile 확인 필요 |
| Strobe | normal, random | 안전 게이트 필요, 과속 flash 제한 |
| Zoom/Focus | wide, mid, narrow | fixture마다 range가 다름 |
| Color | Color Picker가 참조할 basic color preset | fixture type 교체/삭제 후 merge 필요 |

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 자동화 가능 | preset checklist 생성, fixture category별 미동작 preset 탐지 후보, merge/overwrite 계획 |
| 확인 필요 | gobo/prism/strobe/zoom의 실제 attribute name과 range, focus 값, 색상 매칭 |
| 콘솔 객체 | `Preset Pool`, `Global Preset`, `Position Preset`, `Color Preset`, `Beam Preset` |
| 금지/주의 | strobe/audience blind는 자동 full intensity 저장 금지. operator 확인 후 낮은 기본값에서 시작한다. |

`PresetBootstrapPlan`은 아래처럼 console write와 human aim을 분리해야 한다.

```json
{
  "fixture_category": "spot",
  "target_group": "SPOT_ALL_SIMRIK",
  "preset_tasks": [
    {
      "pool": "Position",
      "slot": "spot_position_01",
      "label": "Down Stage Wash",
      "method": "human_aim_then_store",
      "store_policy": "overwrite_template_slot"
    },
    {
      "pool": "Beam",
      "slot": "spot_prism_open",
      "method": "attribute_range_select_then_store",
      "requires_profile_check": true
    }
  ],
  "safety": {
    "allow_audience_blind": false,
    "allow_random_strobe": "manual_confirm_only"
  }
}
```

### 2.5 Master macro와 plugin 재생성

Patch, groups, presets가 정리되면 `Master` macro를 실행해 layout, appearances, sequences, Color Picker generator, hardware layout 연결을 재생성한다. 영상에서는 이 macro가 여러 작은 macro와 Lua script/plugin을 실행하고, Color Picker generator 팝업에서 reinstall/generate/confirm 단계를 거친다.

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 자동화 가능 | preflight checklist, macro 실행 순서 안내, 실행 후 검증 목록 생성 |
| 확인 필요 | plugin 팝업 응답, 저장 위치, 기존 custom layout 덮어쓰기 여부 |
| 콘솔 객체 | `Macro`, `Plugin`, `Layout`, `Appearance`, `Sequence`, `Executor` |
| 검증 | group master, flash key, position layout, intensity FX, pixel FX, color picker가 실제로 동작하는지 확인 |

Copilot은 `Master macro 실행`을 단순 버튼 클릭으로 처리하지 말고 `ShowfileRegenerationPlan`으로 취급해야 한다. 실행 전에는 pool 충돌, 사용자 custom object, 백업 여부를 확인한다.

### 2.6 Layout views와 hardware executor mapping

완성된 showfile은 화면 layout과 hardware executor가 동시에 작동해야 busking에 쓸 수 있다.

영상에서 확인되는 layout 영역:

- Show Layout A/B
- fixture group별 position button
- movement/intensity FX layout
- Color Picker와 color FX form layout
- tap chaser layout
- override position layout
- rig FX layout
- hardware fader/button layout
- group master, flash key, strobe/random strobe, white/color bump

Copilot 적용 포인트:

| 자동화 가능 | 확인 필요 | 콘솔 객체 |
|---|---|---|
| layout item existence 점검, executor assignment 표 생성, selected tap chaser와 executor 연결 확인 | 실제 command wing/console 화면 수, executor page 정책, operator 손 위치 | `Layout`, `Executor`, `Page`, `Sequence`, `Group Master` |

## 3. 세부 운용: solo override, auto position, chaser, color FX

### 3.1 Solo spot / override sequence workflow

Override section은 공연 중 특정 fixture를 기존 effect에서 빼서 singer/solo musician을 비추는 장치다. 일반 rig effect 안에서 돌던 fixture를 부드럽게 override position으로 보내고, deselect하면 다시 기존 rig/effect로 복귀한다.

작업 순서:

1. override에 쓸 fixture를 선택한다.
2. `Global Override Base` preset을 호출해 movement FX를 멈추고 global wheel/open 상태를 만든다.
3. position, color, beam 값을 원하는 solo look으로 조정한다.
4. Global override preset slot에 store/overwrite한다.
5. `Setup Overwrites` 계열 macro를 실행해 override sequences를 갱신한다.
6. Show Layout B의 override button으로 테스트한다.
7. playback override master로 override fixture intensity를 독립 제어한다.

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 자동화 가능 | override 후보 fixture 목록, preset slot 계획, sequence regeneration checklist |
| 확인 필요 | solo 위치 조준, fade 품질, 기존 rig effect로 복귀하는지 visual check |
| 콘솔 객체 | `Global Preset`, `Sequence`, `Cue`, `Macro`, `Playback Override Master`, `Group Master` |
| 금지/주의 | 공연 중 active fixture를 갑자기 snap으로 빼지 않는다. fade time과 base preset 적용 여부를 확인한다. |

`OverrideSequencePlan`:

```json
{
  "intent": "create_solo_override",
  "fixture_selection": ["Fixture 1105"],
  "base_preset": "Global Override Base",
  "override_slot": 6,
  "look": {
    "position": "human_aimed_singer_center",
    "color": "warm_white",
    "beam": "open_no_movement"
  },
  "macro_after_store": "Setup Overwrites",
  "playback_control": "Playback Override Master",
  "return_behavior": "release_to_previous_rig_fx_with_fade"
}
```

### 3.2 Auto position macro workflow

Version 1.9 영상의 핵심은 auto positioning, 즉 position cheat function이다. 모든 position을 사람이 처음부터 만드는 대신, 첫 두 기준 preset만 사람이 조준하고 macro가 나머지 preset을 생성한다.

핵심 규칙:

- fixture category별 macro pool에 `Auto pos` main macro와 개별 position macro가 있다.
- 첫 두 position preset은 자동 생성할 수 없고 사람이 만들어야 한다.
- 두 기준 preset은 `straight down`과 `straight up` 계열이다.
- 이 두 preset은 Pan 값을 쓰지 않는 직선 방향이며 Tilt 기준값을 제공한다.
- auto macro는 이 기준값에서 fanning, crossed variant, pan manipulation, alignment, MAtricks를 적용해 나머지 position을 만든다.
- macro는 line-by-line으로 작성되어 있어 사용자가 복사/수정하기 쉽다.

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 자동화 가능 | 기준 preset 누락 검사, auto macro 실행 전 checklist, 생성된 preset label/table 작성 |
| 확인 필요 | straight down/up의 실제 조준, audience 방향 안전성, 생성된 fanned/crossed position 품질 |
| 콘솔 객체 | `Position Preset`, `Macro`, `Align`, `MAtricks`, `Group`, `Selection Grid` |
| 위험 | 기준 Tilt가 부정확하면 생성된 모든 position이 부정확하다. |

Pan/Tilt 관점에서 Copilot이 반드시 구분해야 할 세 종류:

| 종류 | 목적 | 저장 위치 | 자동화 수준 |
|---|---|---|---|
| 기준 position preset | straight down/up Tilt 기준 | `Position Preset Pool` | 사람이 조준 후 저장 |
| 생성 position preset | fan/cross/variant position | `Position Preset Pool` | macro 실행 가능, visual 검증 필요 |
| movement effect | circle/sweep/ballyhoo 등 반복 움직임 | `Sequence/Cue` 또는 effect layout | group grid와 speed/size master 필요 |

### 3.3 Tap chaser와 delay sweep recipe workflow

Tap chaser section은 흰색 계열 simple chaser와 보라색 계열 delay sweep으로 나뉜다. layout에서 tap chaser를 선택하면 hardware executor의 해당 sequence가 바뀌고, operator는 executor Go 버튼이나 layout으로 tap할 수 있다.

확인된 chaser/delay form:

- odd/even two-step chase
- four-step chase
- left-to-right chaser
- up/down chaser
- center-out delay sweep
- bottom-to-top 또는 top-to-bottom delay sweep
- center에서 퍼지는 circular wave
- two horizontal lines
- vertical center line + outside lines

Cue recipe 구조:

- two-step chaser는 보통 2 cues로 구성된다.
- 각 cue는 2개 이상의 recipe를 갖고, odd/even 또는 block selection을 다르게 적용한다.
- recipe는 group, value preset, MAtricks/matrix pool object, fade/delay를 참조한다.
- left-to-right chaser는 fixture count가 바뀌면 X block 값을 조정해야 한다. 예: 12대 기준 X block 6 → 8대 rig는 X block 4.
- delay sweep은 cue recipe의 delay 값을 `0.5 to 0` 또는 `0 to 0.5`처럼 뒤집어 방향을 바꾼다.
- delay speed rate master를 연결하면 live에서 delay timing을 조절할 수 있다.
- group/preset/fixture content를 바꾸면 sequence cook이 필요할 수 있고, setup tap macro가 cook을 수행한다.

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 자동화 가능 | recipe plan 생성, X block 재계산, matrix pool object 수정 후보, cook 필요 여부 판단 |
| 확인 필요 | chaser 방향, delay sweep 시각 품질, executor assignment |
| 콘솔 객체 | `Sequence`, `Cue`, `Recipe`, `MAtricks Pool`, `Group`, `Preset`, `Rate Master`, `Executor`, `Macro` |
| 금지/주의 | fixture count가 다른데 기존 matrix block을 그대로 두면 룩은 저장되지만 stage에서 어색하게 보인다. |

`TapChaserRecipePlan`:

```json
{
  "intent": "adapt_tap_chaser",
  "fixture_category": "spot",
  "sequence": "Spot Tap 3",
  "form": "left_to_right",
  "cue_count": 2,
  "recipe_basis": {
    "group": "SPOT_ALL_SIMRIK",
    "value_pool": "Dimmer Preset",
    "matrix_pool_object": "X_BLOCK_6"
  },
  "adaptation": {
    "fixture_count_per_row": 8,
    "new_x_block": 4,
    "direction": "stage_left_to_right"
  },
  "rate_master": null,
  "requires_cook": true,
  "verification": ["executor_go_triggers_selected_sequence", "visual_direction_matches_stage"]
}
```

`DelaySweepRecipePlan`:

```json
{
  "intent": "create_delay_sweep",
  "fixture_category": "beam",
  "form": "vertical_center_outside_lines",
  "recipes_per_cue": 3,
  "group": "BEAM_ALL_SIMRIK",
  "matrix_blocks": [
    { "label": "left_outer", "x_block": 4 },
    { "label": "center", "x_block": 4 },
    { "label": "right_outer", "x_block": 4 }
  ],
  "timing": {
    "fade": 0.25,
    "delay": "0.5 thru 0",
    "delay_rate_master": "Delay Speed"
  },
  "requires_cook": true
}
```

### 3.4 Color FX workflow

Color FX section은 Color Picker 아래 새 layout view로 제공된다. operator는 main color와 effect color를 선택하고, color FX form button을 눌러 two-step/four-step/soft/star 계열 color effect를 실행한다.

핵심 구조:

- main color: fixture category별 현재 active color.
- effect color: Color Picker 하단 row에서 선택하는 두 번째 색.
- two bars: two-step behavior.
- four bars: four-step behavior.
- cloud/number: soft running sine wave 계열.
- star: impact가 큰 effect.
- color bump key: 기존 white flash 대신 selected effect color로 bump.
- 기본적으로 IFX SpeedMaster가 color FX speed도 담당한다.
- `separate cfx Speedmaster` macro를 실행하면 color FX를 별도 `cfx speed`에 연결한다.
- color FX sequence는 MA3 cue recipe 기반이며, spot 기준 sequence 1701~1715 부근에서 시작하고 fixture category별 대응 range가 있다.
- Color Picker가 active selected color/effect color를 9001~9006 계열 preset으로 만들어 다른 custom sequence에서도 사용할 수 있다.

Copilot 적용 포인트:

| 항목 | 내용 |
|---|---|
| 자동화 가능 | color FX form 분류, recipe value preset 교체 계획, separate speedmaster 적용 여부 제안 |
| 확인 필요 | fixture category별 색상 매칭, white/blue처럼 출력 차이가 큰 색의 main/effect swap, color bump 밝기 |
| 콘솔 객체 | `Color Preset`, `Sequence`, `Cue Recipe`, `Color Picker Plugin`, `SpeedMaster`, `Macro`, `Layout` |
| 주의 | color recipe는 fixture category별 color combination이 다를 수 있어 전체 rig에 같은 preset을 강제하지 않는다. |

`ColorFxRecipePlan`:

```json
{
  "intent": "adapt_color_fx",
  "fixture_category": "spot",
  "sequence_range_hint": "1701-1715",
  "selected_sequence": 1701,
  "form": "odd_even_two_step",
  "recipe": {
    "group": "SPOT_ALL_SIMRIK",
    "value_preset": "SPOT_COLOR_STEP_1_50_WHITE_50_BLUE",
    "matrix": "odd_even"
  },
  "color_inputs": {
    "main_color_source": "Color Picker active spot color",
    "effect_color_source": "Color Picker active effect color",
    "dynamic_presets": ["9001", "9002", "9003", "9004", "9005", "9006"]
  },
  "speed_control": {
    "current": "IFX SpeedMaster",
    "optional_macro": "separate cfx Speedmaster",
    "target": "cfx speed"
  },
  "verification": ["effect_color_changes_live", "main_effect_swap_has_expected_output_balance"]
}
```

## 4. 조명감독 역할과 Copilot 역할 매핑

| 단계 | 조명감독의 실제 역할 | Copilot이 도울 일 | Copilot이 자동 실행하면 안 되는 일 |
|---|---|---|---|
| Rider 분석 | fixture type, 위치, 회로, 무대 의도 파악 | inventory 구조화, 템플릿 role 매핑 | 확인 없는 fixture mode 추정 |
| Patch | 기존 템플릿 fixture를 유지/교체/삭제 | patch diff, ID range, address 충돌 검사 | DMX address 확정 없는 patch write |
| Group/Grid | 2D selection grid를 실제 무대처럼 구성 | grid 좌표 초안, gap 정책 비교 | visual 확인 없는 group overwrite |
| Position preset | 장비를 실제 무대/관객/솔로 위치로 조준 | preset checklist, store slot 관리 | audience blind/full strobe 자동 저장 |
| Beam/Color preset | gobo/prism/strobe/zoom/color range 탐색 | profile-dependent attribute 확인 질문, merge plan | attribute name 불명 상태의 command 실행 |
| Master macro | 템플릿 객체 재생성 | preflight, 실행 후 검증 checklist | 사용자 custom object 덮어쓰기 |
| Busking layout | executor/page/layout로 운용성 확인 | layout mapping 표, 누락 sequence 탐지 | operator 손 배치 무시한 executor 재배치 |
| Override | solo musician을 부드럽게 강조 | override plan, base preset 적용 확인 | 공연 중 active fixture snap override |
| Tap chaser | beat에 맞춰 chaser 선택/수정 | recipe/matrix/block 계산, cook 필요 판단 | fixture count 불일치 무시 |
| Color FX | main/effect color로 감정과 impact 조절 | color recipe 분류, speedmaster 분리 제안 | 색 출력 차이 확인 없는 전체 rig color 강제 |
| Rehearsal | 실제 무대에서 크기, 속도, 방향, fade 조정 | 검증 checklist, 문제 원인 후보 제시 | 시각 확인 없이 성공 판정 |

## 5. Copilot 구현을 위한 최소 상태 모델

AI Lighting Copilot이 이 자료를 실행 가능한 지식으로 쓰려면 다음 상태를 읽거나 사용자에게 받아야 한다.

```json
{
  "showfile_state": {
    "ma_version": "required",
    "template_version": "required",
    "fixture_categories": ["spot", "wash", "beam", "flood_pixel", "strobe"],
    "groups": {
      "simrik_groups_verified": false,
      "all_simrik_verified": false
    },
    "presets": {
      "position_basic_complete": false,
      "color_merge_complete": false,
      "beam_profile_checked": false
    },
    "macros": {
      "master_macro_available": true,
      "setup_tap_available": true,
      "separate_cfx_speedmaster_available": true
    },
    "speedmasters": {
      "ifx_speed": "existing",
      "delay_speed": "optional",
      "cfx_speed": "optional"
    }
  }
}
```

### 5.1 안전 게이트

| gate | 조건 | Copilot 행동 |
|---|---|---|
| `patch_not_verified` | fixture mode/address/orientation 미확인 | command 대신 patch checklist 출력 |
| `grid_not_verified` | `simrik` group grid 미확인 | effect 생성 전 grid 검증 요구 |
| `profile_dependent_attribute` | gobo/prism/strobe/zoom attribute 불명 | profile read 또는 수동 선택 요청 |
| `destructive_store` | preset/sequence/macro overwrite | 대상 slot, 기존 label, 백업 여부 표시 |
| `audience_blind_or_strobe` | audience 방향/full flash/strobe | 낮은 값·수동 확인·안전 문구 필요 |
| `recipe_needs_cook` | group/preset/matrix 변경 후 recipe 사용 | setup/cook macro 실행 계획 포함 |
| `visual_only_success` | phaser/recipe readback 불가 | console verdict와 별개로 visual check 요청 |

### 5.2 사용자 자연어 라우팅 예시

| 사용자 말 | 내부 intent | 필요한 plan |
|---|---|---|
| "이 새 리그에 쇼파일 맞춰줘" | `adapt_template_showfile` | `ShowfileAdaptationRequest` |
| "무빙 그룹 대칭으로 다시 잡아줘" | `create_group_layout` | `GroupLayoutPlan` |
| "포지션 프리셋 빨리 만들어줘" | `bootstrap_position_presets` | `PresetBootstrapPlan` + auto position gate |
| "보컬 솔로 조명 하나 빼줘" | `create_solo_override` | `OverrideSequencePlan` |
| "좌우로 탭 체이서 만들고 비트에 찍게" | `adapt_tap_chaser` | `TapChaserRecipePlan` |
| "센터에서 위로 쓸고 올라가게" | `create_delay_sweep` | `DelaySweepRecipePlan` |
| "파랑/흰색 컬러 이펙트 부드럽게" | `adapt_color_fx` | `ColorFxRecipePlan` |
| "컬러 이펙트 속도만 따로 빼줘" | `separate_color_fx_speed` | macro execution plan |

## 6. Pan/Tilt 이펙트와 포지션 관련 핵심 정리

이 playlist의 Pan/Tilt 관련 지식은 단순한 "팬틸트 이펙트 레시피"가 아니라, position preset과 movement FX가 같은 group grid와 기준 preset에 의존한다는 점이다.

Copilot이 지켜야 할 순서:

1. **Patch orientation 확인**: pan/tilt invert가 맞지 않으면 position preset을 수정하기 전에 patch를 점검한다.
2. **2D selection grid 확인**: symmetric, V-shape, circular, center-out, left-right는 group grid가 맞아야 한다.
3. **기준 position preset 생성**: straight down/up은 사람이 실제 무대를 보고 조준한다.
4. **auto position macro 실행**: 기준 Tilt를 바탕으로 fan/cross variants를 생성한다.
5. **movement FX 적용**: position effect는 generated preset 또는 group grid를 기반으로 speed/size/fade를 조절한다.
6. **override position 분리**: solo/highlight는 일반 movement FX와 별도 override sequence로 관리한다.
7. **rehearsal tuning**: size master, fade time macro, break/release macro로 무대에서 조정한다.

Pan/Tilt 관련 잘못된 자동화의 대표 실패:

- group 순서가 실제 좌우와 반대라 left-to-right가 right-to-left로 보인다.
- pixel sub-fixture grid가 90도 돌아가 있어 wave가 세로/가로 반대로 돈다.
- fixture count가 12대 기준 matrix block인데 실제는 8대라 chaser 간격이 어색하다.
- straight down/up 기준 preset이 부정확해 auto position 전체가 어긋난다.
- patch invert를 preset으로 보정해 이후 모든 movement FX가 더 복잡해진다.

## 7. Copilot 산출물 형태 제안

Copilot은 사용자의 요청에 대해 최종적으로 다음 중 하나를 내야 한다.

1. **실행 전 계획서**: patch/group/preset/macro/recipe 중 무엇을 만질지, overwrite 대상과 safety gate를 표시.
2. **콘솔 명령 bundle**: 이미 검증된 command path만 포함. profile-dependent 값은 비워두거나 operator 선택으로 둔다.
3. **operator checklist**: 사람이 직접 조준해야 하는 position, color match, pan/tilt invert, strobe/blind 확인.
4. **검증 보고서**: 어떤 layout/executor/sequence가 동작했는지, visual check가 필요한 항목이 무엇인지 기록.

예시 `ShowfileAdaptationRequest`:

```json
{
  "intent": "adapt_template_showfile",
  "source": "mblightarts_ma3_busking_template",
  "stage": {
    "name": "new_stage_layout",
    "fixture_categories": ["spot", "wash", "beam", "pixel_tube", "strobe", "front"]
  },
  "steps": [
    "patch_or_replace_fixture_types",
    "build_simrik_groups",
    "bootstrap_basic_presets",
    "run_master_macro",
    "verify_layouts_and_executors",
    "adapt_recipes_for_tap_chasers_and_color_fx"
  ],
  "requires_operator": [
    "physical_position_confirmation",
    "straight_down_up_position_aim",
    "audience_blind_safety_check",
    "visual_recipe_verification"
  ],
  "allowed_automation": [
    "plan_generation",
    "non_destructive_state_read",
    "free_slot_detection",
    "recipe_block_math",
    "macro_run_after_confirmation"
  ]
}
```

## 8. 영상별 상세 콘솔 운용 Runbook

이 섹션은 Copilot이 실제 작업 지시로 변환할 수 있도록 영상의 조작 흐름을 grandMA3 객체와 버튼 단위로 다시 풀어 쓴 것이다. 여기서 "버튼"은 실제 콘솔의 물리 버튼만 뜻하지 않고, layout view의 button, macro pool item, executor Go, fader/master까지 포함한다.

### 8.1 영상 1: 템플릿 showfile 초기 적응

#### 8.1.1 showfile 구조

템플릿은 "push of a button" 방식으로 만든 busking showfile이다. 기본 구조는 다음과 같다.

| 구성 | 영상에서 확인된 수량/역할 | Copilot이 기억해야 할 점 |
|---|---|---|
| Main fixture groups | 5개 fixture category | spot/wash/beam/flood/strobe처럼 실제 리그를 5개 role에 매핑 |
| Position presets | fixture group별 10개 | layout A의 position button과 movement/override의 기반 |
| Global presets | fixture group별 8개 | gobo/global wheel/focus/open 상태를 포함 |
| Prism presets | fixture group별 3개 | fixture profile dependent. 없으면 빈 preset 또는 skip |
| Zoom presets | fixture group별 3개 | wide/mid/narrow. label과 실제 방향이 다를 수 있음 |
| Intensity/movement FX | fixture group별 15개 | layout button과 fader/size/speed master로 운용 |
| Tap chasers | fixture group별 10개 | layout B와 executor Go로 수동 tap |
| Multi-parameter FX | fixture group별 10개 | rig 또는 category 복합 효과 후보 |
| Override positions | fixture group별 10개 | solo/highlight override용 |

Copilot 구현 포인트:

- 이 숫자를 "항상 고정"으로 보지 말고 template default capacity로 저장한다.
- 사용자가 "이 템플릿처럼 구성해줘"라고 하면 single effect가 아니라 pool object bundle 생성 요청으로 라우팅한다.
- showfile generation은 patch/group/preset이 준비된 뒤 macro/plugin이 수행하는 후처리다.

#### 8.1.2 첫 3단계: Patch → Groups → Basic Presets

콘솔 조작 순서:

1. `Patch` menu를 연다.
2. 템플릿에 이미 들어 있는 fixture를 실제 stage fixture type으로 변경하거나, 빈 patch에서 새로 patch한다.
3. 템플릿 fixture를 유지하면 preset 일부가 이미 작동할 수 있다.
4. `Groups` view로 이동한다.
5. fixture type마다 하나의 main group을 만든다.
6. 이 group을 실제 stage position에 맞게 `2D selection grid`에 배치한다.
7. `Presets` section으로 이동한다.
8. 상단 macro button으로 fixture group view를 전환한다. 이 macro는 preset view와 우측 view를 함께 바꿔 "이전에 작업하던 위치"로 돌아가게 해준다.
9. `spot dim on`, `spot ifx off` 같은 general preset은 보통 건드리지 않는다.
10. 하단의 fixture-specific preset, 즉 position/gobo/gobo rotation/prism/strobe/random strobe/zoom을 조정한다.
11. 같은 절차를 5개 fixture group에 반복한다.

Copilot의 실제 plan 변환:

```json
{
  "runbook": "template_initial_adaptation",
  "console_steps": [
    { "view": "Patch", "action": "verify_or_replace_fixture_types" },
    { "view": "Groups", "action": "store_main_simrik_group_per_fixture_type" },
    { "view": "Presets", "action": "edit_fixture_specific_basic_presets" },
    { "view": "Macros/Global", "action": "run_master_macro_after_preflight" }
  ],
  "skip_by_default": ["general_dim_on_presets", "ifx_off_presets", "pfx_off_presets"],
  "requires_visual_check": ["2D selection grid", "position presets", "zoom/prism/strobe behavior"]
}
```

#### 8.1.3 Master macro와 plugin 팝업

콘솔 조작 순서:

1. `Macro` view로 이동한다.
2. `Global` macro pool로 이동한다.
3. `Master` macro를 찾는다.
4. `Master` macro를 실행한다.
5. macro가 내부적으로 여러 작은 macro와 Lua script를 실행하며 전체 showfile을 재생성한다.
6. 약 1분 정도 기다린다.
7. `Color Picker` plugin pop-up이 뜨면 기본값을 유지한다.
8. `reinstall`을 누른다.
9. `generate`를 누른다.
10. 변경 확인(confirm)을 누른다.

관련 macro:

| Macro | 용도 | Copilot 처리 |
|---|---|---|
| `Master` | 전체 layout/sequence/appearance/plugin 재생성 | preflight 후 실행 후보 |
| `Switch to Console` | console용 screen/hardware layout 전환 | 하드웨어 타입 설정 |
| `Switch to Command Wing` | Command Wing setup용 layout 전환 | 하드웨어 타입 설정 |
| `Reset Show File` | running sequences kill | 문제 상황 대응. 공연 중 주의 |
| `Initial File` | 필요한 sequences restart | showfile 초기 상태 복구 |

Copilot 안전 조건:

- `Master`는 많은 객체를 재생성하므로 patch/group/preset이 준비되기 전에는 실행하지 않는다.
- plugin 팝업에서 저장 위치를 바꾸는 기능이 있더라도 템플릿 기본값이 맞으면 그대로 둔다.
- 사용자 custom layout이나 sequence가 있을 경우 덮어쓰기 범위를 표시해야 한다.

#### 8.1.4 Layout A/B와 hardware layout

`Show Layout A`:

| 위치 | 기능 | 실제 운용 |
|---|---|---|
| top-left | moving light group별 position button | 저장한 position preset을 즉시 호출 |
| position 아래 | corresponding position effects / movement | circle/sweep 등 movement FX 선택 |
| upper-right | Color Picker | fixture group별 main color 선택 |
| Color Picker 아래 | intensity FX | dimmer/chase/wave 계열 선택 |

`Show Layout B`:

| 영역 | 기능 | 실제 운용 |
|---|---|---|
| Optics | gobo, prism, zoom | fixture optics preset 빠른 호출 |
| all fixture group controls | 여러 group을 동시에 제어 | busking 중 빠른 look 변형 |
| tap chaser | beat에 맞춰 수동 tap | executor Go와 연동 |
| override positions | solo/highlight | singer, piano, soloist 조명 |
| rig FX | 전체 리그 intensity/effect | `All Simrik` group grid 의존 |

Hardware layout:

- fixture group별 `Group Master`가 있어 intensity를 따로 제어한다.
- white flash key는 초기 영상 기준으로 존재하지만, color FX 업데이트 이후 color bump로 바뀐다.
- strobe/random strobe key가 있다.
- tap chaser는 selected tap sequence를 executor Go로 실행한다.
- effect size는 temp fader로 줄이거나 키울 수 있다.

Copilot은 layout item을 단순 UI로 보지 말고 `Layout Item → Sequence/Preset/Macro/GroupMaster/Executor` 연결 상태로 모델링해야 한다.

### 8.2 영상 2: 새 무대 layout 적응 상세

#### 8.2.1 Patch 상세 판단

영상의 새 stage 예시는 spot, wash, beam, pixel tube/flood, LED strobe, front light가 섞인 리그다. 작업자는 템플릿 patch를 완전히 삭제하거나 일부 fixture type을 교체하면서 새 리그를 만든다.

실제 조작 패턴:

1. 기존 fixture 중 필요 없는 것은 선택한다.
2. `Patch Editor`로 이동한다.
3. `Unpatch` 또는 삭제/교체를 수행한다.
4. 새 fixture를 insert한다.
5. fixture type을 실제 장비로 바꾼다.
6. fixture ID를 category와 위치에 맞게 재정리한다.
7. universe/address를 실제 회로에 맞게 지정한다.
8. front light처럼 dimmer/fader로 다룰 것은 group A/B 등으로 나눠 patch한다.
9. patch가 끝나면 `Save and Exit`한다.

Copilot이 생성해야 할 patch plan:

| 필드 | 예시 | 이유 |
|---|---|---|
| `template_fixture_role` | `spot`, `wash`, `beam` | 이후 preset/layout 연결 기준 |
| `fixture_id_range` | `1101-1108`, `1201-1208` | group selection과 operator 접근성 |
| `physical_location` | `front_truss`, `mid_truss`, `floor` | 2D grid row 구성 |
| `patch_strategy` | `replace_type`, `delete_and_insert`, `keep_existing` | preset 재사용 가능성 판단 |
| `orientation_group` | `hung_normal`, `floor_upright`, `rotated_90` | pan/tilt invert와 position preset 위험 |
| `dimmer_group` | `front_a`, `front_b` | hardware fader 연결 |

#### 8.2.2 Group grid 상세

Patch 후 첫 번째 작업은 group setup이다. 영상에서는 5개 main group이 항상 `simrik` 계열이며, fixture category 전체를 2D selection grid에 맞게 담는다.

Spot group 예시:

1. Capture 또는 stage plot을 보며 실제 배치를 확인한다.
2. front truss spot 8대를 선택한다. 예: `Fixture 1101 thru 1108`.
3. selection grid에서 다음 row/position으로 이동한다.
4. mid truss spot 8대를 선택한다. 예: `Fixture 1201 thru 1208`.
5. 결과가 좌우 대칭인지 확인한다.
6. 해당 `Spot All Simrik` group에 `Store`한다.
7. 기존 group이면 `Overwrite`한다.
8. `Clear Programmer`한다.

Wash/beam group 예시:

- 기존 patch 일부를 유지한 경우 group이 완전히 비어 있지는 않다.
- selection grid에 과거 truss의 gap이 남아 있을 수 있다.
- `remove gaps` 기능을 사용하면 grid row가 붙어 템플릿 effect가 더 정돈된다.
- 실제 stage distance를 반영하려면 gap을 유지할 수 있으나, 개별 effect 모양이 달라질 수 있다.

Pixel tube/flood 예시:

1. `pixel master` group에는 master fixture만 저장한다.
2. `simrik` group에는 sub-fixture, 즉 single pixel을 저장한다.
3. 16 tubes × 8 pixels 같은 경우 grid area를 먼저 만든다.
4. `Grid 0/0 thru 15/7`처럼 시작점과 범위를 잡는다. MA3는 0부터 세므로 16×8은 15/7까지다.
5. sub-fixture selection을 넣는다. `through` selection은 기본적으로 left-to-right로 채워진다.
6. 실제 pixel tube가 top-to-bottom 방향이면 90도 transform을 적용한다.
7. transform 후 order가 실제 무대와 맞는지 확인한다.
8. `Simrik Flood/Pixels` group에 store/overwrite한다.

Copilot의 grid validation checklist:

- fixture count가 row별로 맞는가?
- 실제 stage left/right와 selection order가 일치하는가?
- center-out effect의 center가 실제 중앙인가?
- gap 제거/유지 정책이 effect 목적과 맞는가?
- pixel sub-fixture가 master group에 잘못 들어가지 않았는가?
- `All Simrik` group은 개별 simrik group의 단순 합으로 충분한가, 아니면 실제 stage projection에 맞게 수동 재구성이 필요한가?

#### 8.2.3 Preset 보정 상세

Position preset:

1. 해당 fixture category의 `Group Master`를 100%로 올린다.
2. stage visualization 또는 실제 무대를 보이게 한다.
3. 해당 group을 선택한다.
4. `At 100`으로 dimmer를 올려 조준 가능한 상태를 만든다.
5. 첫 position을 조준한다.
6. `Store`를 누른다.
7. 기존 position preset slot에 `Overwrite`한다.
8. 다음 position은 audience 방향, fan 형태, stage wash, floor hit 등으로 반복한다.
9. audience blind에 쓰이는 특수 slot은 safety gate로 분리한다.

Global/Gobo preset:

1. Global wheel을 open 또는 원하는 gobo로 설정한다.
2. Focus 값을 함께 조정한다.
3. Global preset filter가 focus까지 저장하도록 되어 있는지 확인한다.
4. Gobo open, gobo 1-4, rotation off/slow/fast 등을 저장한다.
5. Gobo rotation은 방향과 속도를 fixture별로 확인한다.

Prism/Strobe/Zoom preset:

1. Beam/Prism attribute tab으로 이동한다.
2. prism open을 첫 preset에 저장한다.
3. prism variant 1/2를 저장한다. fixture에 해당 prism이 없으면 같은 값 또는 빈 preset이 될 수 있다.
4. shutter/strobe attribute로 normal strobe 값을 찾는다.
5. random strobe 값을 찾는다.
6. focus/zoom tab으로 이동한다.
7. wide/mid/narrow beam을 실제 output을 보고 저장한다.
8. label이 narrow인데 실제로 wide처럼 보이면 label이 아니라 실제 beam size 기준으로 보정한다.

Color preset merge:

1. fixture type을 삭제 후 재생성한 category는 global color preset이 연결되지 않을 수 있다.
2. Color Picker에서 blue/magenta/red/green 등 기본색을 선택한다.
3. 해당 fixture group을 선택한다.
4. 색을 맞춘다.
5. 기존 color preset slot에 `Store`한다.
6. `Merge` command를 사용해 기존 preset에 새 fixture 값을 합친다.
7. 여러 기본색을 반복한다.
8. Color Picker plugin을 다시 실행한다.
9. `reinstall → generate → confirm`을 반복한다.
10. layout으로 돌아와 category별 색이 모두 따라오는지 확인한다.

Copilot은 여기서 `Overwrite`와 `Merge`를 구분해야 한다. fixture type 교체로 빠진 값을 채우는 color preset은 대체로 `Merge`가 맞고, 의도적으로 새 position/zoom을 만드는 slot은 `Overwrite`가 맞다.

#### 8.2.4 Rig FX와 All Simrik

Rig FX는 전체 리그를 한 번에 쓰는 intensity/effect 영역이다. 개별 `simrik` group을 자동으로 합친 `All Simrik` group을 쓸 수 있지만, 실제 stage projection과 다를 수 있다.

Copilot 판단:

- spot 사이에 wash가 실제로 끼어 있으면 `All Simrik`도 그 순서를 반영해야 한다.
- 단순 category별 group concat은 effect가 이상하게 보일 수 있다.
- `All Simrik`을 수동으로 재구성한 뒤 rig FX setup macro를 다시 실행해야 할 수 있다.
- 개별 group에 실제 distance gap을 넣으면 rig FX는 좋아질 수 있지만 category별 effect는 다르게 보일 수 있다.

### 8.3 영상 3: Solo override 상세

Override는 "fixture가 이미 effect 속에서 움직이고 있어도 solo position으로 깨끗하게 빼내는" 기능이다. 영상에서 강조하는 것은 완벽한 move-in-black이 sequence 간에는 어렵기 때문에, showfile이 transition을 clean하게 보이도록 override sequence를 구성한다는 점이다.

콘솔 조작:

1. `Preset Global` section으로 이동한다.
2. override에 쓸 fixture를 선택한다. 예: front truss spotlight `Fixture 1105`.
3. fixture를 white로 만든다.
4. movement를 멈추고 global wheel을 open해야 한다.
5. encoder로 직접 open/stop 값을 맞출 수 있지만, 더 빠른 방법은 `Global Override Base` preset을 누르는 것이다.
6. `Global Override Base`는 open global wheel, movement/effect stop, highlight look의 clean starting point를 만든다.
7. position을 solo 대상 쪽으로 조준한다. 예: piano 방향.
8. zoom을 더 narrow하게 조정한다.
9. `Store` button을 누른다.
10. 원하는 Global override preset slot에 `Overwrite`한다. 영상 예시는 override preset number 6.
11. `Clear Programmer`한다.
12. `Macros Global`로 이동한다.
13. pool item 15의 `Setup Overwrites` macro를 실행한다.
14. 잠시 기다린다.
15. `Show Layout B`로 돌아간다.
16. override slot 6 button을 눌러 테스트한다.
17. fixture가 먼저 dimmer 0 상태로 위치/beam/color를 정리한 뒤 fade로 들어오는지 확인한다.
18. override button을 해제한다.
19. fixture가 원래 rig effect로 자연스럽게 복귀하는지 확인한다.

Playback override master:

- fader section에 `Playback Override Master`가 있다.
- singer/piano 등 여러 override를 켠 상태에서 override fixture intensity만 독립 제어한다.
- 일반 rig group master와 별도로 작동한다.
- 내부적으로 virtual group master를 사용하며, 이 객체들은 macro가 생성한다.

Copilot 구현:

```json
{
  "override_console_flow": [
    "select_fixture_or_group",
    "apply_global_override_base",
    "human_aim_position",
    "adjust_zoom_color_beam",
    "store_global_override_slot_overwrite",
    "clear_programmer",
    "run_macro_global_setup_overwrites",
    "test_show_layout_b_override_button",
    "test_playback_override_master"
  ],
  "must_verify_visually": [
    "fixture_fades_in_after_positioning",
    "deselect_returns_to_rig_fx",
    "override_master_controls_only_override_fixtures"
  ]
}
```

### 8.4 영상 4: Auto position과 X-key 운영 상세

#### 8.4.1 Notes와 manual

MA3 v1.9부터 showfile object에 small note를 달 수 있고, 템플릿은 이 note를 사용해 중요한 macro나 element에 안내를 넣는다. `Master` macro에도 실행 전 필요한 3단계가 note로 적혀 있다.

Copilot 적용:

- macro 실행 전 object note를 읽을 수 있으면 우선 참고한다.
- template version과 tested MA version을 상태값으로 저장한다.
- version mismatch가 있으면 자동 실행 대신 호환성 경고를 낸다.

#### 8.4.2 Auto position 조작

콘솔 조작:

1. fixture category의 `Macro Pool`로 이동한다.
2. `Auto pos` main macro를 찾는다.
3. 오른쪽에 개별 position macro들이 있다.
4. 자동 생성 가능한 position preset을 삭제/clear해도 된다.
5. 마지막 두 special position은 자동 생성 대상이 아니다. 하나는 ambient, 하나는 audience blind 용도다.
6. `Capture`나 실제 stage를 보며 preset area로 돌아간다.
7. 첫 두 preset, 즉 `straight down`과 `straight up`을 만든다.
8. 두 preset은 Pan 값을 쓰지 않고 straight 방향을 유지한다.
9. `straight down`: fixture가 stage를 균등하게 때리도록 Tilt를 조정한다.
10. floor set 등 위치가 다른 fixture는 별도로 선택해 Tilt를 보정한다.
11. `Store`한다.
12. `straight up`: fixture 일부 또는 전체를 audience 쪽으로 더 높은 Tilt로 조정해 큰 look을 만든다.
13. mid/back truss 등 필요한 fixture만 선택해 Tilt를 조정한다.
14. `Overwrite`로 저장한다.
15. 해당 fixture category macro section으로 돌아간다.
16. `Auto pos` main macro를 실행한다.
17. macro가 개별 macro를 호출해 7개 내외의 missing preset을 재생성한다.
18. 생성된 preset을 눌러 fan/cross/variant look을 검증한다.

개별 auto position macro의 내부 개념:

- target group을 선택한다.
- align을 설정한다.
- MAtricks selection을 적용한다.
- Pan 값을 조작한다.
- 기준 Tilt preset에서 fan/cross 변형을 만든다.
- line-by-line macro라서 사용자가 복사/수정 가능하다.

Copilot 주의:

- "포지션 자동 생성" 요청은 즉시 macro 실행이 아니다.
- 먼저 straight down/up이 존재하고 현재 리그에 맞는지 확인한다.
- audience blind preset은 안전 gate로 빼고 자동 생성/실행하지 않는다.
- 생성 후 모든 preset은 visual verification 항목으로 남긴다.

#### 8.4.3 X-key / hardware control

X-key section 기능:

| 버튼/매크로 | 기능 | 실제 운용 |
|---|---|---|
| Master time 0s | 모든 transition fade time을 0초로 | color/position change가 즉시 전환 |
| Master time 5s 등 | global fade time 설정 | 부드러운 전환 |
| Show Layout A/B 전환 | hardware button으로 view 전환 | Command Wing/console 운용성 향상 |
| Master FX Off | 모든 running FX 비활성화 | fade time을 고려해 effect kill |
| Kill Gobo Rotations | 모든 gobo rotation stop | 회전만 별도 정리 |
| Break FX | running FX를 pause/break | song break 중 effect 멈춤 |
| Release FX | break 상태에서 release | break 중 다른 FX 선택 후 release하면 다른 look으로 전환 가능 |

Copilot은 `Master FX Off`와 `Break/Release`를 구분해야 한다. `Master FX Off`는 running FX를 끄는 동작이고, `Break`는 잠시 멈췄다가 `Release`로 다시 내보내는 busking transition 도구다.

### 8.5 영상 5: Tap chaser와 delay sweep 상세

#### 8.5.1 Layout/executor 운용

기본 개념:

1. `Show Layout B` 또는 tap chaser layout으로 이동한다.
2. fixture category별 tap chaser section을 본다.
3. white section은 simple chaser step이다.
4. purple section은 delay sweep이다.
5. layout에서 `Spot Tap 1`, `Spot Tap 3`, `Spot Tap 6`처럼 tap chaser button을 선택한다.
6. 선택한 tap chaser에 해당하는 sequence가 hardware layout의 executor에 로드된다.
7. operator는 executor의 `Go` button으로 tap한다.
8. Command Wing/console setup에 따라 공통 executor 1개로 5개 category를 바꿔 쓰거나, category별 executor 5개를 쓸 수 있다.
9. effect amount master/fader를 올리면 full effect, 50%면 줄어든 effect, 0%면 effect 없음이 된다.
10. `Delay Speed` group/rate master로 delay timing을 live에서 조절한다.

Delay sweep 종류:

| Form | 영상 설명 | Recipe 의미 |
|---|---|---|
| center start | center에서 시작 | center block에 먼저 값, outside가 뒤따름 |
| bottom to top | 아래에서 위로 이동 | delay `0.5 thru 0` 또는 반대값으로 방향 제어 |
| circled wave | center에서 원형 wave | grid center와 matrix selection 의존 |
| two horizontal lines | 두 수평 라인 | row/block 분리 |
| vertical center/outside lines | center line과 outside line | 3 recipes per cue 구조 |

Simple chaser 종류:

- odd/even chase
- four-step odd/even variant
- left-to-right chaser
- up/down two-step
- up/down four-step 또는 fewer lamps variant

#### 8.5.2 Cue Recipe editor 상세

Odd/even chaser 수정 절차:

1. `Sequence` section으로 이동한다.
2. fixture category의 tap sequence를 찾는다. 예: spot tap 1.
3. sequence를 swipe해서 edit menu를 연다.
4. sequence 안의 cue를 선택한다.
5. recipe editor를 연다.
6. two-step chaser는 보통 2 cues다.
7. 각 cue는 2 recipes로 구성된다.
8. cue 1: odd group은 dimmer 100%, even group은 dimmer 0%.
9. cue 2: odd/even을 반대로 적용한다.
10. recipe의 `Group` 필드는 보통 `Spot All Simrik`이다.
11. 이 group의 selection grid가 matrix를 대칭적으로 적용하게 해준다.
12. recipe의 `Value`는 preset pool의 preset이다. 예: dimmer on/off.
13. recipe의 matrix 필드는 MAtricks/matrix pool object를 참조한다.
14. 숫자만 있으면 editor에서 직접 입력한 값이다.
15. 기호가 붙어 있으면 matrix pool object에서 온 값이다.
16. MA3 recipe editor에 selection index 직접 입력 기능이 부족해, x at 0 / x at 1 같은 선택은 pool object로 우회한다.
17. odd/even intensity chase를 color chase로 바꾸려면 value preset을 red/blue color preset으로 교체한다.
18. cue 1은 red/blue, cue 2는 blue/red로 반대로 넣는다.
19. layout으로 돌아가 tap chaser를 눌러 정상 동작을 확인한다.

Left-to-right chaser 수정:

1. spot tap 3 같은 left-to-right sequence를 선택한다.
2. edit menu에서 matrix pool object를 확인한다.
3. 12대 기준이면 X block 6 같은 object가 쓰일 수 있다.
4. 실제 row fixture가 8대면 X block 4로 바꿔야 한다.
5. `Matricks Global` 또는 `Matrix` pool section으로 이동한다.
6. 해당 matrix pool object를 edit한다.
7. X block 값을 6에서 4로 변경한다.
8. object label도 `X_BLOCK_4`처럼 바꾼다.
9. recipe에 연결된 다른 object도 같은 방식으로 수정한다.
10. 실제 stage에서 direction이 맞는지 확인한다.

Delay sweep 수정:

1. purple delay sweep sequence를 선택한다.
2. sequence edit menu를 연다.
3. vertical lines 예시는 cue마다 3 recipes가 있다.
4. 12 fixtures를 left outer 4, center 4, right outer 4로 나누기 때문이다.
5. 각 recipe는 다른 matrix block selection을 가진다.
6. fade는 editor에서 직접 설정한다. 영상 예시는 0.25.
7. delay는 `0.5 to 0`처럼 설정한다.
8. 방향을 반대로 하려면 `0 to 0.5`로 뒤집는다.
9. settings menu에서 `Rate Master to Delay`를 `Delay Speed` rate master에 연결한다.
10. 그래야 hidden recipe delay 값을 매번 수정하지 않고 live master로 timing을 조절할 수 있다.
11. group/preset/matrix content를 바꿨으면 sequence `Cook`이 필요할 수 있다.
12. 템플릿의 `Setup Tap` macro가 tap sequences cook을 수행한다.

#### 8.5.3 Manual tap recording macro

Recipe/matrix로 원하는 chaser를 만들기 어렵거나 더 빠르게 즉석 step을 만들고 싶을 때 help macro를 쓴다.

실제 절차:

1. layout에서 수정할 tap chaser를 선택한다. 예: tap 5.
2. macro `Clear Spot Tap Selected`를 누른다.
3. 해당 sequence 전체가 clear된다.
4. 첫 step을 만든다.
5. 예: `Group 1` spot 전체를 선택한다.
6. `At 0`으로 전체를 끈다.
7. MAtricks에서 `Wings 2`를 설정한다.
8. `Next` button을 눌러 첫 selection을 얻는다.
9. 선택된 fixture를 `At 100`으로 올린다.
10. macro `Store Spot Tap Selected`를 누른다.
11. 두 번째 step을 만든다.
12. 다시 전체를 `At 0`으로 한다.
13. `Next`를 눌러 다음 selection을 얻는다.
14. 선택된 fixture를 `At 100`으로 올린다.
15. `Store Spot Tap Selected`를 누른다.
16. 세 번째 step도 같은 방식으로 반복한다.
17. `Clear Programmer`한다.
18. layout으로 돌아간다.
19. tap 5를 선택한다.
20. executor Go로 tap하여 방금 기록한 step sequence가 도는지 확인한다.

Executor 재배치 macro:

1. 특정 fixture category tap executor를 옮기려면 helper macro를 누른다.
2. dialogue가 뜬다.
3. 예: spot tap executor를 206에서 207로 바꾸려면 `207`을 입력한다.
4. confirm한다.
5. 해당 tap을 한 번 선택하면 새 executor에 표시된다.

Copilot은 tap chaser를 두 방식으로 분류해야 한다.

- `recipe_based_tap_chaser`: cue recipe, group, value preset, matrix pool, cook이 핵심.
- `recorded_step_tap_chaser`: clear selected tap, programmer state, store selected tap macro가 핵심.

### 8.6 영상 6: Color FX 상세

#### 8.6.1 Layout 조작

Color FX 업데이트 이후 화면 구성:

1. `Color Picker` 아래에 color effect form layout view가 추가된다.
2. 이 view는 intensity effect section과 유사하게 effect form을 고르는 버튼 묶음이다.
3. Color Picker 하단에 second/effect color row가 추가된다.
4. main color는 fixture category별 active color다.
5. effect color는 하단 row에서 고르는 두 번째 색이다.
6. effect form button을 누르면 main color와 effect color 조합으로 color FX가 실행된다.

Button icon/형태 해석:

| 표시 | 의미 | Copilot 분류 |
|---|---|---|
| two bars | two-step behavior | odd/even, 2 cue/2 value |
| four bars | four-step behavior | 4 cue 또는 4-step color chase |
| cloud + number | soft running sine wave | 부드러운 wave, 낮은 impact |
| star | high impact effect | 강한 hit/flash성, safety/brightness 확인 |

운용 팁:

- running effect 중에도 main color를 바꾸면 effect 색이 바뀐다.
- fixture category 하나만 바꾸거나, 상단 all-category icon으로 전체 category를 바꿀 수 있다.
- effect color도 live로 바꿀 수 있다.
- main/effect color를 swap하면 step behavior가 뒤집힌다.
- white/blue처럼 출력 차이가 큰 색은 swap에 따라 느낌이 크게 달라진다.

#### 8.6.2 Color bump와 speedmaster

Hardware layout 변화:

- 기존 white flash key가 color bump key로 바뀐다.
- color bump는 항상 selected effect color를 사용한다.
- 예: spot main color가 green이고 effect color가 red면 flash key는 red bump가 된다.
- 따라서 show의 color scheme에 맞는 hit를 만들 수 있다.

Speed control:

1. 기본 상태에서는 `IFX Speed` master가 intensity FX와 color FX speed를 함께 제어한다.
2. `Macros Global`로 이동한다.
3. `separate cfx Speedmaster` macro를 찾는다.
4. macro를 실행한다.
5. color FX는 더 이상 IFX SpeedMaster에 묶이지 않는다.
6. 새 speedmaster `cfx speed`가 color FX speed를 담당한다.

Copilot 판단:

- 사용자가 "컬러 이펙트만 속도를 다르게"라고 하면 `separate cfx Speedmaster` macro 실행 계획을 제안한다.
- 이미 분리되어 있는지 상태를 확인한다.
- intensity FX와 color FX가 함께 움직이길 원하면 macro 실행을 제안하지 않는다.

#### 8.6.3 Color FX recipe 수정

콘솔 조작:

1. color FX form을 하나 activate한다.
2. `Sequence` section으로 이동한다.
3. spot color FX는 sequence 1701~1715 부근에서 찾는다.
4. 다른 fixture category도 대응 sequence range를 가진다.
5. 방금 켠 sequence를 찾아 edit menu를 연다.
6. cue를 선택한다.
7. recipe editor를 연다.
8. `Group` 필드는 `Spot All Simrik` 같은 category simrik group이다.
9. 대칭 효과가 필요하므로 selection grid가 맞아야 한다.
10. `Value` 필드에서 FX adapted color preset을 선택한다.
11. fixture category마다 color combination이 다르므로 spot/wash/beam preset이 분리되어 있다.
12. 예: `Spot Color Step 1 50% white 50% blue`를 더 작은 white bump preset으로 바꾼다.
13. `X group` 같은 MAtricks 값을 `none`으로 바꿔 effect density를 바꿀 수 있다.
14. editor를 닫는다.
15. layout으로 돌아가 main/effect color를 바꿔 같은 form이 다른 색으로 작동하는지 확인한다.

Dynamic Color Picker presets:

- Color pool의 9001~9006 부근에 active selected color preset이 생성된다.
- 이 preset들은 Color Picker의 현재 선택값을 반영한다.
- 마지막 preset은 active selected effect color에 해당한다.
- 이 preset들은 color FX sequence뿐 아니라 custom sequence나 tap chaser에도 사용할 수 있다.
- Color Picker 변경 시 계속 update되는 동적 preset으로 취급한다.

Copilot은 color FX를 단일 RGB 값이 아니라 다음 관계로 저장해야 한다.

```json
{
  "color_fx_binding": {
    "main_color": "fixture_category_active_color",
    "effect_color": "color_picker_effect_row",
    "dynamic_color_presets": "9001-9006",
    "effect_form_sequence": "category_sequence_range",
    "recipe_value": "FX adapted category color preset",
    "speedmaster": "IFX Speed or cfx speed"
  }
}
```

## 9. Copilot 실행 엔진에 넣을 상세 action catalog

아래 catalog는 자연어 intent를 실제 grandMA3 작업으로 바꾸는 중간 표현이다. 모든 action은 바로 command 실행이 아니라, 상태 확인과 safety gate를 거쳐야 한다.

| Action | 필요한 화면/객체 | 사용자 입력 | 자동화 가능 | 완료 검증 |
|---|---|---|---|---|
| `open_patch_and_replace_fixture_type` | Patch, FixtureType | fixture type/mode/address | patch plan 생성, 충돌 검사 | fixture sheet와 output 확인 |
| `store_simrik_group_grid` | Group, Selection Grid | fixture IDs, row/column 방향 | grid plan 생성, group store command 후보 | stage left/right/center visual |
| `remove_grid_gaps` | Selection Grid tool | gap 제거 여부 | 옵션 비교 | effect form 비교 |
| `transform_pixel_grid_90` | Grid command, sub-fixture selection | pixel tube 방향 | 16×8 등 grid 계산 | pixel wave 방향 확인 |
| `store_position_preset_overwrite` | Position Preset Pool | 조준 완료 신호 | slot/label 관리 | 실제 beam position |
| `merge_color_preset` | Color Preset Pool, Color Picker | 색상 선택 | merge 대상 plan | fixture category별 색 일치 |
| `run_master_macro` | Macro Global `Master`, Plugin popup | 실행 확인 | preflight, macro 실행 후보 | layout/executor 동작 |
| `run_setup_overwrites` | Macro Global `Setup Overwrites` | override slot | macro 실행 후보 | override fade/return |
| `run_auto_pos_macro` | fixture category Macro Pool | straight down/up 검증 | macro 실행 후보 | 생성 preset visual |
| `edit_cue_recipe_value` | Sequence, Cue, Recipe editor | value preset | recipe diff | layout에서 effect 확인 |
| `edit_matrix_pool_object` | MAtricks/Matrix Pool | block/wings/index | fixture count 기반 계산 | chase 방향/간격 |
| `assign_delay_rate_master` | Cue Recipe settings | target master | Delay Speed 연결 plan | fader로 timing 변화 |
| `cook_tap_sequences` | Macro `Setup Tap` 또는 sequence cook | 변경 범위 | cook 실행 후보 | recipe 최신값 반영 |
| `record_manual_tap_step` | Programmer, Next, Store Tap Selected macro | step별 look | programmer capture 지원 | executor Go로 step 재생 |
| `separate_cfx_speedmaster` | Macro Global | 분리 여부 | macro 실행 후보 | CFX만 speed 변화 |

### 9.1 Copilot 답변 형식 예시

사용자: "새 리그에 맞게 탭 체이서 좌우로 다시 잡아줘."

Copilot이 내부적으로 만들어야 하는 답:

```json
{
  "intent": "adapt_tap_chaser",
  "preconditions": [
    "SPOT_ALL_SIMRIK grid verified",
    "fixture_count_per_row known",
    "tap sequence selected"
  ],
  "console_path": [
    "Show Layout B에서 Spot Tap 3 선택",
    "Sequence section에서 해당 sequence edit",
    "Recipe editor에서 matrix pool object 확인",
    "Matricks Global/Matrix pool에서 X block 수정",
    "필요 시 Setup Tap macro로 cook",
    "Executor Go로 방향 검증"
  ],
  "objects": ["Sequence", "Cue", "Recipe", "MAtricks Pool", "Group", "Executor"],
  "blocked_if": ["fixture_count_unknown", "grid_unverified"],
  "human_visual_check": "stage left to right direction"
}
```

사용자: "보컬 솔로 위치 하나 만들어줘."

```json
{
  "intent": "create_solo_override",
  "console_path": [
    "Preset Global section으로 이동",
    "대상 fixture 선택",
    "Global Override Base preset 적용",
    "operator가 position/zoom/color 조준",
    "Store → Global override preset slot overwrite",
    "Clear Programmer",
    "Macros Global → Setup Overwrites 실행",
    "Show Layout B override button 테스트",
    "Playback Override Master 테스트"
  ],
  "objects": ["Fixture", "Global Preset", "Macro", "Sequence", "Playback Override Master"],
  "must_not_automate": ["human_aim_position", "unsafe_audience_blind"]
}
```

## 10. 결론

이 6편의 실질적 가치는 개별 효과명을 외우는 데 있지 않다. 템플릿 showfile을 유지하면서 새 무대에 빠르게 적응시키는 작업 순서, 그리고 그 순서가 grandMA3 객체에 어떻게 걸리는지가 핵심이다.

Copilot에 반영할 때의 우선순위는 다음과 같다.

1. `patch → simrik group grid → basic presets → master macro → layout/executor verification`을 표준 runbook으로 만든다.
2. Pan/Tilt와 delay/color recipe는 모두 2D selection grid 검증을 선행 조건으로 둔다.
3. auto position은 첫 두 기준 preset을 사람이 조준하고, 나머지만 macro 지원으로 본다.
4. tap chaser와 color FX는 Phaser가 아니라 `Sequence + Cue Recipe + MAtricks/Matrix + SpeedMaster` 작업으로 분류한다.
5. 조명감독의 감각적 판단이 필요한 부분은 Copilot이 대신하지 않고, console object와 검증 항목으로 명확히 안내한다.
