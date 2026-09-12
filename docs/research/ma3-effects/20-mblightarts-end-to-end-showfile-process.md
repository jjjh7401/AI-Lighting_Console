# MBLightArts 단일 영상 기반 end-to-end 조명연출 프로세스

> 수집일: 2026-09-11  
> 출처: YouTube `https://www.youtube.com/watch?v=5wm88LvScSk`  
> 범위: 영상 자막 전체 1,136 segment를 기준으로, 새 stage layout에서 grandMA3 template showfile을 실제 운용 가능한 상태로 만드는 전 과정을 정리한다. 역할 기준은 "조명감독은 기획·자료 제공·판단·요청, AI Lighting Copilot은 콘솔 조작·상태 점검·반복 작업 실행"이다.  
> 한계: 자막 기반 분석이므로 영상 화면의 모든 pool 번호와 클릭 위치를 프레임 단위로 실측한 것은 아니다. 다만 영상에서 명시된 메뉴, 버튼, macro, preset 저장 방식, group/grid 구성, override 방식은 Copilot 적용용 runbook으로 상세화했다.

## 1. 영상의 핵심 가치

이 영상은 개별 효과 튜토리얼이 아니라 **새 무대에 showfile을 처음부터 끝까지 적용하는 실제 작업 흐름**이다. 영상의 stage는 기존 demo stage를 바꿔 다음 fixture type을 추가한 예시다.

| Stage 요소 | 영상의 fixture | showfile 관점 |
|---|---|---|
| Front lighting | profile moving lights in front truss | front/spot 또는 key light role |
| Main rig | hybrid LED moving lights | position, gobo, prism, strobe, iris, zoom, focus, FX 전체 사용 |
| Pixel background | Astera LED tubes | sub-fixture pixel grid 중심 |
| Tilt pixel bar | GP X4 bars | 픽셀 마스터 그룹 + sub-fixture simrik group 분리 필요 |

영상의 전체 순서는 다음 5단계다.

1. **Patch**: 새 fixture를 넣고 fixture ID, mode, universe/address, naming을 정리한다.
2. **Groups / 2D selection grid**: showfile이 사용할 `simrik` group과 픽셀 마스터 그룹을 실제 stage layout에 맞춘다.
3. **Presets**: position, gobo, gobo rotation, strobe, prism, iris, zoom, focus, color preset을 category별로 저장한다.
4. **Regenerate / Layout 검증**: showfile menu의 `regen all`, feature grid, FX calculator, creative position UI를 사용해 layout을 정리하고 효과를 검증한다.
5. **Override**: solo spot/highlight override를 별도로 생성하고 move-in-black 방식으로 확인한다.

Copilot에 넣을 때 중요한 점은 **감독이 직접 콘솔을 조작하는 모델이 아니라, 감독이 의도와 판단을 제공하고 Copilot이 콘솔 조작을 맡는 모델**로 설계하는 것이다. 감독은 fixture 자료, stage plot, 연출 의도, safety 판단, 최종 시각 판단을 제공한다. Copilot은 patch 입력, group/grid 생성, preset 저장 절차, macro 실행, layout 생성, override sequence 재생성, 실행 전후 검증을 담당한다.

## 2. End-to-end 프로세스 맵

| 단계 | 조명감독이 제공·판단할 일 | Copilot이 콘솔에서 수행할 일 | 주요 grandMA3 객체/기능 |
|---|---|---|---|
| 1. Stage 분석 | 장비 리스트, stage plot, 회로표, fixture mode, 연출 의도 제공 | `FixtureInventory` 생성, template category A/B/C 매핑, 누락 자료 질문 | Fixture, FixtureType, Patch |
| 2. Patch | 장비 mode/address 승인, ID/naming 규칙 승인 | `Patch` menu에서 fixture insert, type/mode/count/address 입력, fixture ID와 label 정리 | Patch Menu, Insert New Fixture |
| 3. Hybrid group | truss 위치, gap 반영 여부, 좌우 방향 판단 | `Group View`와 `Setup Mode`에서 2D selection grid 구성·저장·검증 진행 | Group View, Selection Grid, Setup Mode |
| 4. Pixel tube group | pixel 방향과 row 구조 확인 | `Grid` command, dot-through sub-fixture selection, transform/flip, simrik group 저장 | Grid command, Transform/Flip |
| 5. Tilt pixel bar group | master/sub-fixture 구조와 tilt/zoom/strobe가 master에 있는지 확인 | sub-pixel simrik group과 픽셀 마스터 그룹을 분리 저장하고 feature target 설정 | Simrik Group, 픽셀 마스터 그룹 |
| 6. Position preset | straight down/up, ambient, blind의 최종 조준 판단 | fixture 선택, dimmer/output 준비, store/merge/overwrite, `Auto pos` 실행과 생성 preset 검증 | Position Preset, Auto Pos |
| 7. Gobo/Focus | 어떤 gobo를 쓸지와 sharp focus 판단 | gobo wheel open 조건 관리, focus-only 3×3 preset 저장 절차 수행 | Gobo, Focus, Zoom Presets |
| 8. Beam presets | strobe 안전성, prism/iris/zoom 룩 판단 | strobe/prism/iris/zoom preset 저장, 없는 feature fallback 처리 | Beam, Prism, Iris, Zoom |
| 9. Color presets | 실제 무대 색상 매칭 판단 | `regen groups`, category selection, color preset `Merge` 저장 수행 | Color Preset, Color Picker |
| 10. Regen all | 전체 재생성 승인, 결과 시각 확인 | `regen all` 실행, postflight checklist 수행 | Showfile Menu, Regen All |
| 11. Layout cleanup | 운용에 필요한 기능 선택 | feature grid 설정, `Generate Layouts` 실행, layout 정리 확인 | Feature Grid, Generate Layouts |
| 12. Override | solo 대상, MIB 여부, Stop IFX/PFX 여부 판단 | override look 저장, `regen override`, move-in-black 동작 검증 | Global Preset, Override, MIB |

## 3. Stage 분석과 Patch

### 3.1 Patch의 기본 원칙

영상에서는 showfile이 clone-show 구조를 따르지 않는다고 설명한다. 따라서 기존 download showfile의 patch를 유지할 필요가 없고, 새 stage라면 전체 patch를 지운 뒤 새 fixture를 넣어도 된다.

Copilot 콘솔 작업:

1. `Patch` menu로 들어간다.
2. download showfile에 이미 patch된 demo fixture가 보인다.
3. 기존 stage와 다르면 전체 patch를 clear/delete할 수 있다.
4. `Insert New Fixture` button을 누른다.
5. `Library`로 이동해 showfile 안에 이미 있는 fixture만 보지 말고 전체 fixture library를 검색한다.
6. fixture type을 검색한다. 영상 예시는 JB `P9 BeamSpot` 계열 hybrid fixture.
7. fixture mode를 선택한다. 영상 예시는 mode 1.
8. fixture name을 정한다. 예: `hybrid`.
9. count를 입력한다. 예: 16.
10. fixture ID 시작값을 임시 입력한다. 영상에서는 처음 1000으로 넣고 이후 수정한다.
11. patch universe/address를 입력한다. 영상 예시는 Universe 1, count 1부터.
12. confirm한다.
13. 다른 fixture type도 같은 방식으로 반복한다.

Copilot이 할 일:

- 사용자의 fixture list를 받아 patch 작업 단위로 쪼갠다.
- `Insert New Fixture`에 필요한 fixture type, mode, count, fixture ID, universe/address 후보를 만든다.
- "기존 patch 유지"와 "전체 삭제 후 새 patch"의 차이를 설명한다.
- 주소 충돌, fixture count mismatch, fixture mode 누락을 검사한다.
- patch 후 다음 단계 group/grid에서 쓸 수 있도록 category role을 붙인다.

Copilot이 하면 안 되는 일:

- fixture mode를 추측해서 확정하지 않는다.
- 실제 DMX address를 모르는 상태에서 patch write를 강행하지 않는다.
- pan/tilt orientation이 확인되지 않은 상태에서 position preset을 자동 저장하지 않는다.

### 3.2 Fixture ID와 naming 구조

영상은 fixture ID를 truss 단위로 100번대 block으로 나누는 방식을 쓴다.

예시:

| 위치 | fixture ID | 의미 |
|---|---|---|
| hybrid front truss 8대 | `1101 thru 1108` | 첫 번째 truss/block |
| hybrid back truss 8대 | `1201 thru 1208` | 두 번째 truss/block |
| Titan tube upper row | `2101 thru 2108` | fixture category B upper row |
| Titan tube lower row | `2201 thru 2208` | fixture category B lower row |
| X4 bar upper row | `3101 thru 3108` | fixture category C upper row |
| X4 bar lower row | `3201 thru 3208` | fixture category C lower row |

조명감독이 제공·판단할 일:

- 자기 머릿속 stage 구조와 맞는 ID 체계를 선택한다.
- truss, floor, row, fixture type을 ID와 label로 빠르게 구분할 수 있게 한다.
- real stage와 visualization/capture의 DMX layout이 맞는지 확인한다.

Copilot의 콘솔 수행 역할:

- fixture ID block 규칙을 제안한다.
- "A/B/C fixture category"와 "physical truss/row"를 분리해서 저장한다.
- 이후 group command, preset 작업, override fixture 선택에 ID range를 재사용한다.

```json
{
  "fixture_id_scheme": {
    "hundreds_block": "physical_row_or_truss",
    "category_prefix": {
      "1xxx": "hybrid_moving_lights",
      "2xxx": "titan_tubes",
      "3xxx": "x4_tilt_bars"
    },
    "examples": [
      { "range": "1101-1108", "label": "Hybrid Front Truss" },
      { "range": "1201-1208", "label": "Hybrid Back Truss" }
    ]
  }
}
```

## 4. Group과 2D Selection Grid

### 4.1 Group View 준비

영상은 onPC 환경에서 big console용 group view가 화면에 맞지 않아 `Groups Small` view를 할당한다.

Copilot 콘솔 작업:

1. `Group View`로 이동한다.
2. onPC 화면이면 기존 group view가 너무 크거나 복잡할 수 있다.
3. `View Pool`에서 `Groups Small` view를 찾는다.
4. swipe command 또는 assign으로 현재 view에 할당한다.
5. selection grid가 함께 보이는 작업 화면을 만든다.

Copilot의 콘솔 수행 역할:

- 사용자의 장비가 full console인지 Command Wing/onPC인지 묻거나 상태를 읽는다.
- view 변경은 연출 데이터 자체는 아니지만 작업 효율에 중요하므로 runbook에 넣는다.
- "작업 화면 준비"와 "showfile 데이터 변경"을 분리한다.

### 4.2 Hybrid moving light group

목표는 front/back truss의 hybrid moving lights를 하나의 fixture category A `simrik` group으로 저장하는 것이다.

Copilot 콘솔 작업:

1. fixture `1101 thru 1108`을 선택한다.
2. selection grid에서 다음 row로 이동한다.
3. fixture `1201 thru 1208`을 선택한다.
4. showfile은 이 selection grid를 대칭 효과 계산에 사용하므로 stage layout과 최대한 맞게 만들어야 한다.
5. Capture에서 실제 truss 사이 gap이 보이면 grid에도 gap을 표현한다.
6. MA3 2.x 이상의 `Setup Mode`로 들어간다.
7. fixture cell을 drag and drop해 gap을 재구성한다.
8. setup mode를 닫는다.
9. index 0부터 제대로 시작하도록 정렬/normalize command를 실행한다. 영상에서는 "start from first index zero correctly"라고 설명한다.
10. `Store` 또는 console의 Store key를 누른다.
11. category A `simrik` group에 저장한다.
12. 처음부터 새로 만드는 작업이면 `Override`를 선택한다.
13. `Highlight` key를 켠다.
14. `Next` key로 fixture selection이 실제 stage 순서대로 진행되는지 확인한다.
15. selection grid와 Capture/stage가 일치하면 `Clear`를 세 번 눌러 programmer를 비운다.
16. category name group을 `hybrid`로 label한다. 이 이름은 layout view에도 표시된다.

조명감독이 제공·판단할 일:

- gap을 실제 거리처럼 둘지, effect 편의를 위해 줄일지 판단한다.
- `Next` key로 실제 stage 방향과 순서를 확인한다.
- category label을 operator가 이해하기 쉬운 이름으로 정한다.

Copilot의 콘솔 수행 역할:

- row별 fixture selection을 계산한다.
- gap policy를 제안한다.
- Next/Highlight 검증 checklist를 만든다.
- category name이 layout에 반영된다는 점을 알려준다.

### 4.3 Titan tube pixel group

Titan tube는 sub-fixture pixel이 있으므로 2D pixel grid가 핵심이다. 영상의 stage는 8개의 tube가 horizontal line으로 있고, 2개의 vertical line/row가 있어 전체 pixel resolution이 16×8 또는 row별 8×8로 설명된다.

상단 row group 작업:

1. fixture sheet에서 tube가 8 pixel mode인지 확인한다.
2. `Grid` command를 command line에 입력한다.
3. 시작점 `0/0`을 입력한다.
4. 8×8 grid를 만들기 위해 `thru 7/7`을 입력한다. MA3는 0부터 세므로 0~7이 8칸이다.
5. pre-selected grid가 생긴다.
6. upper row fixture `2101 thru 2108.`을 입력한다.
7. 끝의 `.` 또는 `dot through`는 sub-fixture만 선택하는 용도다.
8. 이 selection을 별도 group으로 저장하고 `upper row`처럼 label한다.
9. lower row도 같은 방식으로 반복한다.

Transform 작업:

1. upper row group을 다시 선택한다.
2. 실제 stage에서는 tube pixel이 vertical alignment인데 grid에는 horizontal alignment로 들어갈 수 있다.
3. transform/flip tool을 누른다.
4. grid가 vertical orientation으로 바뀌는지 확인한다.
5. 첫 fixture `2101.1`부터 `2101.8`까지 top-to-bottom 또는 bottom-to-top 순서가 맞는지 확인한다.
6. `Store` → `Override`로 row group을 갱신한다.
7. lower row도 flip 후 store/overwrite한다.
8. upper row group과 lower row group을 순서대로 선택해 전체 Titan tube arrangement를 만든다.
9. category B `simrik` group에 store/override한다.

검증:

- category B `simrik` group을 선택한다.
- Capture에서 모든 tube pixels가 나타나는지 확인한다.
- `Highlight` + `Next`로 grid order를 stepping한다.
- `Set` key로 전체 selection을 다시 불러온다.
- flip/transform tool로 pixel movement가 top-to-bottom 또는 left-to-right로 자연스러운지 테스트한다.

Copilot이 할 일:

- sub-fixture selection command 후보를 만든다.
- grid size를 fixture count × pixel count로 계산한다.
- MA3의 zero-based grid를 반영한다.
- transform 필요 여부를 질문/검증한다.
- row group을 만든 뒤 최종 simrik group으로 합치는 순서를 저장한다.

### 4.4 GP X4 tilt bar: 픽셀 마스터 그룹

X4 bar는 pixel과 tilt movement가 함께 있는 복합 fixture다. 이 경우 showfile은 **sub-fixture simrik group**과 **픽셀 마스터 그룹**을 구분해야 한다.

Sub-fixture simrik group:

1. fixture sheet에서 X4 bar가 bar당 20 pixels인지 확인한다.
2. upper row `3101 thru 3108.`을 입력한다.
3. `.` selection으로 8×20 = 160 pixels가 선택된다.
4. selection grid에서 다음 row로 이동한다.
5. lower row `3201 thru 3208.`을 입력한다.
6. category C `simrik` group에 store/override한다.

Pixel master group:

1. upper row main fixture `3101 thru 3108`을 선택한다. `.`를 붙이지 않는다.
2. fixture sheet에서 sub-fixture 번호가 선택되지 않았는지 확인한다.
3. 다음 row로 이동한다.
4. lower row main fixture `3201 thru 3208`을 선택한다.
5. `픽셀 마스터 그룹`에 store한다.

왜 필요한가:

- pixel intensity FX는 sub-fixture simrik group이 필요하다.
- tilt movement, position, strobe, zoom 같은 master-level 기능은 픽셀 마스터 그룹이 필요하다.
- sub pixel에는 개별 strobe/zoom/tilt가 없을 수 있다.

Copilot 체크:

```json
{
  "pixel_bar_grouping": {
    "simrik_group": "sub_fixtures_only",
    "pixel_master_group": "main_fixtures_only",
    "master_features": ["position", "strobe", "optics", "zoom"],
    "pixel_features": ["dimmer_pixel_fx", "color_pixel_fx"],
    "must_verify": [
      "no_sub_fixture_in_pixel_master_group",
      "all_sub_fixtures_in_simrik_group"
    ]
  }
}
```

## 5. Showfile Menu 설정: 픽셀 마스터 그룹과 Dim Default

영상에서 가장 중요한 설정 중 하나는 showfile menu에서 fixture category별 feature가 어떤 group을 사용할지 지정하는 부분이다.

### 5.1 픽셀 마스터 그룹 사용 체크박스

Tilt bar 같은 pixel fixture는 showfile menu에서 category C, 즉 tilt bars를 선택하고 오른쪽 checkbox를 설정한다.

Checkbox의 의미:

| Checkbox | 의미 | X4 tilt bar에서 설정 |
|---|---|---|
| Position uses 픽셀 마스터 그룹 | position preset/position FX가 simrik이 아니라 픽셀 마스터 그룹을 사용 | 켬 |
| Strobe uses 픽셀 마스터 그룹 | strobe control이 픽셀 마스터 그룹을 사용 | 켬 |
| Optics/Zoom uses 픽셀 마스터 그룹 | zoom/iris/optics가 픽셀 마스터 그룹을 사용 | 켬 |

영상의 판단:

- X4 bar의 sub pixel에는 개별 strobe control이 없다.
- zoom 등 optics도 individual pixel에 없고 master fixture에 있다.
- 따라서 position, strobe, zoom/optics 모두 픽셀 마스터 그룹을 사용하게 한다.

Copilot의 콘솔 수행 역할:

- fixture가 master/sub-fixture 구조인지 확인한다.
- feature별 attribute가 master fixture에 있는지 sub-fixture에 있는지 판단한다.
- 픽셀 마스터 그룹 사용 체크박스 설정 후보를 만든다.
- 설정 전후 어떤 presets가 픽셀 마스터 그룹을 참조할지 보고한다.

### 5.2 Dim Default helper macro

Tilt bar는 main dimmer와 sub pixel dimmer 기본값을 바꿔야 pixel intensity FX가 제대로 작동한다.

문제 상황:

- programmer가 비어 있을 때 main dimmer는 닫혀 있고 sub dimmer는 열려 있다.
- 이 상태에서는 pixel intensity effect control이 직관적이지 않다.

`dim default` helper macro:

1. showfile menu로 이동한다.
2. `dim default` gear/macro를 누른다.
3. macro는 픽셀 마스터 그룹의 main fixture dimmer default를 100%로 만든다.
4. sub pixel dimmers default를 0%로 만든다.
5. fixture sheet에서 main open, sub dimmers closed 상태가 되었는지 확인한다.

왜 중요한가:

- main dimmer가 열려 있어야 individual pixel dimmer가 실제 output을 제어한다.
- sub dimmer가 닫혀 있어야 bump와 predefined intensity FX가 pixel을 선명하게 제어한다.

Copilot의 콘솔 수행 역할:

- 픽셀 마스터 그룹 구조가 감지되면 `dim default` 실행 여부를 물어본다.
- 실행 전 fixture sheet 상태를 기록한다.
- 실행 후 main/sub dimmer default가 반대로 바뀌었는지 검증한다.

## 6. Preset 작업

### 6.1 Preset 작업 화면

Preset area는 fixture category별로 잘 구조화되어 있다.

영상에서 언급된 preset 영역:

- Position
- Gobo
- Gobo rotation
- Strobe
- Prism
- Iris
- Zoom
- Focus
- Color

상단 macro/view:

- fixture group별 preset view 전환 macro가 있다.
- 이 macro를 누르면 우측 view bar도 함께 바뀐다.
- group view와 preset view 사이를 빠르게 오갈 수 있다.
- 아래쪽에는 현재 작업 category의 group button이 있어 빠르게 selection할 수 있다.

Copilot의 콘솔 수행 역할:

- 사용자가 "하이브리드 프리셋 잡아줘"라고 하면 category A preset view로 이동해야 하는 작업으로 해석한다.
- "preset 저장"을 단일 작업으로 보지 말고 preset pool별 checklist로 분해한다.

### 6.2 Position preset과 Auto Position

중요한 전제:

- `straight down`과 `straight up` 두 position preset을 먼저 만들어야 한다.
- 이후 `Auto pos` macro가 나머지 basic position preset을 생성한다.
- special position, ambient, audience blind, FX suppress 관련 preset은 자동 생성하지 않는다.

Copilot 콘솔 작업:

1. 해당 group을 선택한다.
2. `Highlight` 또는 `Edit`로 output을 보이게 한다.
3. `straight down` position을 만든다. moving light가 stage 쪽으로 내려가는 기본 look이다.
4. `Store` key를 누른다.
5. preset이 비어 있으면 `Overwrite`, 기존 값과 합칠 때는 `Merge`를 선택한다.
6. `straight up` position을 만든다.
7. 전체 rig를 tilt up해도 되고, front truss만 선택해 audience 쪽으로 올려도 된다.
8. `Store`한다.
9. `Miscellaneous` section 또는 showfile menu로 이동한다.
10. feature grid 안의 gear icon `Auto pos`를 누른다.
11. override all positions 여부를 묻는 prompt가 뜬다.
12. 이미 수동 조정한 position을 덮을 수 있으므로 주의한다.
13. 실행하면 fan out, fan in, two fans, three fans, four fans, five fans 등 basic look이 생성된다.
14. preset area로 돌아가 생성 preset을 눌러 확인한다.

Fan divisibility:

- 영상에서는 selection grid width가 10이면 three fan이 잘 맞지 않는다고 설명한다.
- 10은 3으로 나누기 어렵기 때문이다.
- two fan은 5+5로 잘 맞는다.
- five fan은 2칸 단위로 잘 맞는다.
- three fan을 쓰려면 12 fixture 또는 9 fixture처럼 3으로 나눠지는 구조가 유리하다.

Fine tuning:

1. 생성 preset을 starting point로 쓴다.
2. 특정 truss fixture만 선택한다.
3. Tilt 값을 조금 낮추거나 높인다.
4. 해당 preset에 `Store`.
5. `Merge`로 변경값만 반영한다.

Special presets:

| Preset | 자동 생성 여부 | 작업 방식 |
|---|---|---|
| ambient | 자동 생성하지 않음 | wall projection, gobo ambience 등 수동 조준 |
| audience blind | 자동 생성하지 않음 | audience safety 확인 후 수동 조준 |
| IFX/PFX suppress 관련 | 별도 기능 | position과 effect suppress 결합. 향후 설명 대상 |

Copilot의 콘솔 수행 역할:

- `straight down/up` 누락 시 auto position 실행을 막는다.
- 현재 grid width를 읽고 fan preset이 잘 나눠지는지 계산한다.
- auto pos 실행 전 "all positions override" 위험을 경고한다.
- 생성 후 "이 preset은 stage layout상 부적합할 수 있음"을 표시한다.

### 6.3 Gobo와 Focus 분리

영상은 gobo와 focus를 같은 preset에 섞지 말고 분리하라고 강조한다.

원칙:

- Gobo preset에는 gobo wheel 선택만 저장한다.
- Focus preset에는 focus 값만 저장한다.
- 이렇게 해야 zoom range 전체에서 sharp gobo projection을 사용할 수 있다.

Gobo preset 작업:

1. position preset으로 beam이 보이는 위치를 만든다.
2. `Edit` 또는 수동으로 dimmer 100%를 만든다. `Highlight`는 gobo가 보이지 않을 수 있으므로 피한다.
3. `Gobo` tab으로 이동한다.
4. `Gobo Open` preset을 만든다.
5. gobo wheel 1과 gobo wheel 2가 모두 open인지 확인한다.
6. encoder wheel, UI click, Smart Bar 중 편한 방법으로 gobo wheel을 조작한다.
7. Store한다.
8. gobo wheel 1의 gobo 3개를 저장한다.
9. wheel 1 gobo를 저장할 때 wheel 2는 반드시 open이어야 한다.
10. gobo wheel 2의 gobo를 저장할 때 wheel 1은 반드시 open이어야 한다.

Gobo rotation:

1. rotation off preset을 저장한다. 예: rotate stop.
2. slow rotation preset을 저장한다.
3. fast rotation preset을 저장한다.
4. fixture에 wheel별 rotation 기능이 다를 수 있으므로 attribute가 실제 있는지 확인한다.

Copilot의 콘솔 수행 역할:

- gobo wheel 1/2 상호 open 조건을 checklist로 만든다.
- "focus와 gobo를 같이 저장"하려는 작업을 경고한다.
- Smart Bar/encoder/UI click은 모두 같은 attribute 조작으로 추상화한다.

### 6.4 Strobe, Prism, Iris, Zoom

Strobe:

- showfile에는 normal strobe fast/slow, random strobe fast/slow preset이 있다.
- 현재는 bump section에서 주로 사용된다.
- 따라서 꼭 "strobe"만 넣어야 하는 것은 아니고 다른 shutter effect를 저장할 수도 있다.
- 그러나 관객 안전을 위해 Copilot은 full-speed strobe를 자동 저장하지 않는다.

Prism:

- group 선택 후 full intensity.
- Beam section에서 prism attribute를 찾는다.
- open preset을 저장한다.
- fixture에 3 facet prism만 있으면 prism 1 preset과 prism 2 preset에 같은 값을 저장해 "Prism 2 버튼을 눌렀는데 아무 동작 없음"을 피할 수 있다.

Iris:

- iris wide/mid/narrow preset을 저장한다.
- narrow는 fixture의 최솟값까지 닫지 않고, 실제로 보기 좋은 좁은 beam을 선택할 수 있다.

Zoom:

- Focus tab에서 zoom wide/mid/narrow를 저장한다.
- 저장 전 programmer clear로 다른 값이 섞이지 않게 한다.
- label보다 실제 beam size가 기준이다.

Copilot의 콘솔 수행 역할:

- fixture profile에서 prism/iris/zoom/strobe 지원 여부를 확인한다.
- 없는 feature는 skip하거나 같은 fallback preset을 저장하는 계획을 제안한다.
- strobe는 safety gate로 분리한다.

### 6.5 Focus preset 3×3 matrix

이 영상의 아주 중요한 부분이다. Focus preset은 zoom과 gobo 조합별로 3×3 stack을 만든다.

축:

| 축 | 값 |
|---|---|
| Zoom stage | wide, mid, narrow |
| Optic scenario | gobo open, gobo wheel 1 active, gobo wheel 2 active |

결과:

- 총 9개 focus preset이 필요하다.
- focus preset에는 **actual Focus value만** 들어가야 한다.
- zoom preset이 함께 active/record되면 show control 결과가 나빠진다.

Copilot 콘솔 작업:

1. group을 선택한다.
2. dimmer 100%.
3. optic scenario를 선택한다. 예: gobo open.
4. zoom stage를 선택한다. 예: zoom wide.
5. `Clear`를 두 번 누른다.
6. active feature가 모두 deselect되어 record 대상에서 빠진다.
7. group selection도 빠질 수 있으므로 group을 다시 선택한다.
8. 이때 "record될 active value가 없음"을 확인한다.
9. focus 값만 조정한다.
10. Focus preset에 store한다.
11. gobo wheel 1 scenario를 선택한다. gobo는 다른 preset pool이라 focus preset에 기록되지 않는다.
12. focus를 sharp하게 맞춘다.
13. store한다.
14. gobo wheel 2도 반복한다.
15. zoom mid로 이동한다.
16. 같은 절차를 반복한다.
17. zoom narrow로 이동한다.
18. 같은 절차를 반복한다.

Copilot의 focus preset plan:

```json
{
  "focus_matrix": {
    "zoom_stages": ["wide", "mid", "narrow"],
    "optic_scenarios": ["gobo_open", "gobo_wheel_1", "gobo_wheel_2"],
    "store_rule": "focus_value_only",
    "operator_steps": [
      "select_group",
      "select_zoom_stage",
      "select_optic_scenario",
      "clear_twice_to_remove_zoom_from_recording",
      "reselect_group",
      "adjust_focus",
      "store_focus_preset"
    ]
  }
}
```

## 7. Complex fixture preset: Titan tubes와 X4 bars

### 7.1 Titan tubes

영상에서는 Titan tubes가 strobe 기능 외에는 관련 preset이 거의 없다고 설명한다. 따라서 fixture category B는 필요한 strobe preset만 같은 방식으로 처리하고, 없는 기능은 그대로 둔다.

Copilot의 콘솔 수행 역할:

- fixture category별 feature availability를 만든다.
- 없는 feature의 preset 작업은 skip한다.
- layout feature grid에서 position/optics 등을 숨길 후보로 표시한다.

### 7.2 X4 tilt bars

X4 bars는 master/sub-fixture 구조 때문에 intensity output 확인 방식이 다르다.

작업 전제:

- 픽셀 마스터 그룹 사용 체크박스가 position/strobe/optics에 설정되어 있어야 한다.
- `dim default`로 main open, sub dimmers closed 상태가 되어야 한다.

Preset 작업 주의:

1. 픽셀 마스터 그룹을 선택하면 dimmer가 이미 open일 수 있다.
2. 하지만 실제 light output을 보려면 simrik group의 sub pixels도 dimmer 100%로 올려야 할 수 있다.
3. `Highlight`도 쓸 수 있지만 fixture profile의 highlight value가 zoom 등 다른 attribute를 건드릴 수 있다.
4. 영상의 작업자는 highlight보다 simrik group dimmer 100% 방식을 선호한다.
5. position은 master/tilt 기준으로 저장한다.
6. auto position macro는 Pan을 주로 조작하므로 tilt bar에서는 큰 효과를 기대하지 않는다.
7. zoom wide/mid/narrow 등 master-level optics는 픽셀 마스터 그룹 기준으로 저장한다.

Copilot의 콘솔 수행 역할:

- "100% dimmer인데 output이 안 보임" 상황에서 main/sub dimmer 구조를 의심한다.
- highlight 사용이 zoom 등 다른 값을 바꿀 수 있음을 경고한다.
- tilt bar에 auto position을 적용해도 큰 결과가 없을 수 있음을 알려준다.

## 8. Color presets와 Regen Groups

Color presets는 simrik group과 픽셀 마스터 그룹이 모두 작동하도록 main group을 사용한다.

작업 순서:

1. color preset 저장 전 main groups down below를 확인한다.
2. 이 main group들은 fixture category naming 외에도 color preset 저장에 사용된다.
3. showfile menu로 이동한다.
4. `regen groups` icon/macro를 누른다.
5. group A/B/C active main groups가 재생성된다.
6. color preset 저장 시 all three groups를 선택한다.
7. dimmer를 100%로 올린다.
8. 원하는 color를 선택한다.
9. `Store`한다.
10. visualization에서 준비 중이면 빠르게 기본색만 저장해도 된다. 실제 stage에서는 색이 다르게 보일 수 있기 때문이다.
11. real stage에서는 fixture category 하나만 선택해 색을 fine-tune한다.
12. 기존 color preset에 `Store + Merge`로 넣어 다른 category의 color information을 지우지 않는다.

Copilot의 콘솔 수행 판단:

- color preset은 `Overwrite`보다 `Merge`가 필요한 경우가 많다.
- category별 색상 출력 차이는 사람이 보고 맞춰야 한다.
- visualization color는 실제 무대와 다를 수 있으므로 "임시 준비값"으로 표시한다.

## 9. Regen All과 Show View 검증

### 9.1 Regen All

Preset 작업이 끝나면 showfile menu로 이동해 `regen all`을 실행한다.

영상에서 설명한 `regen all` 결과:

- plugin이 background에서 많은 것을 조정/최적화한다.
- color effects가 integrated color preset 기반으로 생성된다.
- bumps가 rig size에 맞게 생성된다.
- layout/show views에서 기능을 테스트할 준비가 된다.

Copilot 실행 전 점검:

- patch 완료 여부
- simrik group 검증 여부
- 픽셀 마스터 그룹/픽셀 마스터 그룹 사용 체크박스 여부
- basic presets 완료 여부
- color preset/regen groups 완료 여부
- custom object overwrite 위험 여부

Postflight 검증:

1. hybrid spots와 tilt bars group master를 올린다.
2. all fixtures에 color를 적용한다.
3. tilt bars에 intensity FX를 적용한다.
4. symmetrical behavior가 pixel element에서도 잘 나오는지 확인한다.
5. hybrid spots에 color IFX 또는 CFX를 적용한다.
6. layout button이 누락/불필요한 fixture category를 표시하지 않는지 확인한다.

### 9.2 FX calculator icon

Show view의 작은 calculator icon은 showfile 내 FX를 수정하는 기능이다.

조작:

1. calculator icon을 누른다.
2. 수정할 running FX를 선택한다.
3. dialog에서 wing, block 등 parameter를 바꾼다.
4. 예: wing setting 수정, block 8 추가.
5. running FX가 즉시 바뀌는지 확인한다.
6. 다른 `SYM group`을 선택할 수 있다.
7. tilt bars처럼 복잡한 rig에서는 2-line simrik 대신 straight single-line alternative simrik group을 선택하면 다른 효과가 나온다.
8. dialog를 닫으면 저장 버튼 없이도 변경된 FX design이 유지된다.
9. 다른 FX로 갔다가 돌아와도 designed FX가 유지된다.

Copilot의 콘솔 수행 역할:

- 사용자가 "이 FX 모양 바꿔줘"라고 하면 calculator/action editor로 라우팅한다.
- wing/block/SYM group 변경 후보를 제시한다.
- alternative simrik group을 만들거나 선택하는 옵션을 제공한다.

### 9.3 Creative position up icon

Position layout의 작은 up icon은 공간을 아끼면서 fan position과 creative position preset을 바꾸는 도구다.

동작:

- up icon을 누르면 position layout의 number/fan style이 바뀐다.
- five fan, two fan 등 다른 fanning style로 전환할 수 있다.
- Magic icon 또는 creative position 영역은 사용자가 자유롭게 special look을 저장할 공간이다.

Copilot의 콘솔 수행 역할:

- 사용자가 "팬 스타일 바꿔줘"라고 하면 position preset 자체 수정인지 layout의 fan selector 변경인지 구분한다.
- creative preset slot은 사용자가 만든 show-specific look 저장 공간으로 보호한다.

### 9.4 Feature Grid와 Generate Layouts

영상 말미에 불필요한 layout element를 제거한다. 현재 design에는 3개 fixture category만 필요하므로, 각 category가 실제로 가진 기능만 layout에 남긴다.

조작:

1. showfile menu로 이동한다.
2. feature grid를 연다.
3. fixture category별 필요한 function을 선택/해제한다.
4. 예: tilt bars는 IFX, color FX, CFX, optics/zoom은 필요하지만 position FX는 제한적일 수 있다.
5. Titan tubes는 intensity FX, color, color FX만 필요하고 positions, position FX, optics, multi FX는 필요 없다.
6. hybrid spots는 모든 기능을 사용한다.
7. `Generate Layouts` 또는 `Gen Layouts`를 누른다.
8. 몇 초 기다린다.
9. layout view가 실제 fixture category와 feature set만 표시하는 clean overview로 정리된다.

Copilot의 콘솔 수행 역할:

- fixture feature availability matrix를 만든다.
- layout에 보여야 할 기능만 자동 추천한다.
- "보여주기"와 "기능 삭제"를 구분한다. feature grid는 UI 정리이지 장비 자체 삭제가 아니다.

## 10. Override section: Solo spot / Highlight

Override section은 기본적으로 functional하지 않으며, 필요에 맞게 별도 setup해야 한다.

### 10.1 Override look 생성

Copilot 콘솔 작업:

1. `Preset` area로 이동한다.
2. 아래쪽 `Global presets`를 선택한다.
3. override look용으로 준비된 10개 slot을 확인한다.
4. solo spot에 사용할 fixture를 선택한다. 예: front truss spot `1103`.
5. dimmer를 100%로 설정한다.
6. white color를 만든다.
7. position을 piano/person 쪽으로 조준한다.
8. zoom을 tighter하게 조정한다.
9. 저장 전에 `Stop IFX` preset을 누른다.
10. `Stop PFX` preset을 누른다.
11. 이렇게 하면 override icon을 눌렀을 때 running IFX/PFX가 멈춘다.
12. solo spot 표준 사용에는 둘 다 누르는 것이 좋다.
13. 특정 연출에서는 effect를 유지하고 싶을 수 있으므로 이 부분은 자동화하지 않는다.
14. look이 만족스러우면 `Store`.
15. 첫 override all preset slot에 `Override`한다.

### 10.2 Regen Override와 Move In Black

1. showfile menu로 이동한다.
2. `regen override` icon을 누른다.
3. showfile이 해당 override sequence를 생성한다.
4. show view에서 override look을 눌러 확인한다.
5. 기본값으로 move in black이 active다.
6. active면 fixture가 어두운 상태에서 위치로 이동한 뒤 부드럽게 켜진다.
7. move in black을 비활성화하면 movement와 feature change가 직접 보인다.
8. 직접 이동이 보이는 것도 특정 연출에서는 쓸 수 있다. 예: back spot이 앞으로 움직이며 piano guy를 잡는 장면.

Copilot의 콘솔 수행 역할:

- override slot 10개를 관리한다.
- Stop IFX/PFX 적용 여부를 사용자에게 묻는다.
- MIB on/off를 연출 의도에 따라 제안한다.
- regen override 후 sequence 생성 여부를 검증한다.
- "solo spot"은 대부분 MIB on + Stop IFX/PFX on으로 기본 추천한다.
- "움직임을 보여줘" 요청이면 MIB off 후보를 제시한다.

## 11. 감독 요청별 Copilot 라우팅

| 감독 요청 | Copilot intent | Copilot이 콘솔에서 수행할 일 | 감독이 제공·판단할 일 |
|---|---|---|---|
| "이 새 리그에 쇼파일 맞춰줘" | `adapt_showfile_to_new_stage` | fixture inventory, patch plan, group/preset/regen checklist 생성 | fixture mode/address/orientation 자료 제공과 승인 |
| "하이브리드 무빙 16대 넣어줘" | `patch_fixture_category` | Insert New Fixture 입력값, ID block, naming 제안 | 장비 mode와 universe/address 자료 제공과 승인 |
| "픽셀튜브가 8개씩 두 줄이야" | `build_pixel_simrik_group` | Grid 0/0 thru 7/7, sub-fixture selection, transform 후보 | 실제 pixel 방향 판단 |
| "X4 바는 틸트가 있어" | `setup_pixel_master_group` | 픽셀 마스터 그룹, 픽셀 마스터 그룹 사용 체크박스, dim default checklist | master/sub-fixture output 판단 |
| "포지션 자동으로 만들어줘" | `run_auto_position_with_guard` | straight down/up 존재 확인, fan divisibility 계산, auto pos 위험 경고 | 기준 position 최종 조준 판단 |
| "3팬이 이상해" | `diagnose_fan_divisibility` | grid width와 fan count 나눗셈 검사 | 어떤 fan look을 쓸지 판단 |
| "고보랑 포커스 잡아줘" | `build_gobo_focus_presets` | gobo/focus 분리, 3×3 focus matrix checklist | sharp focus 최종 판단 |
| "컬러 프리셋 전체 맞춰줘" | `merge_color_presets` | regen groups, all category selection, merge policy | 실제 색상 매칭 판단 |
| "레이아웃에 안 쓰는 버튼 지워줘" | `generate_feature_grid_layout` | feature availability matrix와 Gen Layouts 계획 | 실제 운용에 필요한 기능 판단 |
| "이 FX 모양 바꿔줘" | `modify_fx_calculator_params` | calculator icon, wing/block/SYM group 변경 후보 | stage에서 효과 모양 판단 |
| "피아노 솔로 스팟 만들어줘" | `create_override_solo_spot` | override slot, Stop IFX/PFX, regen override, MIB plan | fixture 조준 판단과 연출 의도 제공 |

## 12. Copilot 내부 스키마

### 12.1 EndToEndShowfileAdaptation

```json
{
  "intent": "adapt_showfile_to_new_stage",
  "source_video": "5wm88LvScSk",
  "stage": {
    "fixture_categories": [
      {
        "category": "A",
        "role": "hybrid_moving_lights",
        "fixtures": ["1101 thru 1108", "1201 thru 1208"],
        "features": ["position", "gobo", "strobe", "prism", "iris", "zoom", "focus", "color", "ifx", "pfx", "cfx"]
      },
      {
        "category": "B",
        "role": "titan_tubes",
        "fixtures": ["2101 thru 2108", "2201 thru 2208"],
        "features": ["pixel_color", "pixel_ifx", "strobe_optional"]
      },
      {
        "category": "C",
        "role": "tilt_pixel_bars",
        "fixtures": ["3101 thru 3108", "3201 thru 3208"],
        "features": ["pixel_ifx", "tilt_position", "strobe_master", "zoom_master", "color"]
      }
    ]
  },
  "workflow": [
    "patch",
    "build_groups",
    "configure_pixel_master_group",
    "store_presets",
    "regen_groups",
    "store_color_presets",
    "regen_all",
    "generate_layouts",
    "setup_overrides"
  ]
}
```

### 12.2 FeatureGridPlan

```json
{
  "intent": "configure_feature_grid",
  "categories": {
    "hybrid": {
      "positions": true,
      "position_fx": true,
      "ifx": true,
      "color": true,
      "cfx": true,
      "optics": true,
      "multi_fx": true
    },
    "titan_tubes": {
      "positions": false,
      "position_fx": false,
      "ifx": true,
      "color": true,
      "cfx": true,
      "optics": false,
      "multi_fx": false
    },
    "tilt_bars": {
      "positions": true,
      "position_fx": false,
      "ifx": true,
      "color": true,
      "cfx": true,
      "optics": true,
      "multi_fx": false
    }
  },
  "after_change": "generate_layouts"
}
```

### 12.3 OverrideLookPlan

```json
{
  "intent": "create_override_solo_spot",
  "target": {
    "fixture": "1103",
    "purpose": "piano_solo"
  },
  "look": {
    "dimmer": 100,
    "color": "white",
    "position": "director_approved_aim",
    "zoom": "tight"
  },
  "fx_suppression": {
    "stop_ifx": true,
    "stop_pfx": true,
    "automate": false
  },
  "store": {
    "pool": "Global Override All Presets",
    "slot": 1,
    "policy": "override"
  },
  "regen": "regen_override",
  "transition": {
    "move_in_black": true,
    "alternative": "direct_visible_move"
  }
}
```

## 13. 구현 우선순위

이 영상을 Copilot 기능으로 반영할 때 우선순위는 다음과 같다.

1. **FixtureInventory + PatchPlan**: 새 stage 정보를 구조화하고 patch 입력값을 만든다.
2. **GroupLayoutPlan**: simrik group, pixel sub-fixture grid, 픽셀 마스터 그룹을 정확히 만든다.
3. **PixelMasterGroup/DimDefault Guard**: master/sub-fixture 구조를 가진 fixture에서 feature target group을 올바르게 설정한다.
4. **PresetChecklist**: position, gobo, strobe, prism, iris, zoom, focus, color를 category별 feature availability에 맞게 안내한다.
5. **FocusMatrixPlan**: zoom × optic scenario 3×3 focus preset을 focus-only 저장으로 강제한다.
6. **RegenerationPlan**: regen groups, regen all, generate layouts, regen override를 실행 전후 검증과 함께 관리한다.
7. **RequestRouter**: 감독의 자연어 요청을 patch/group/preset/layout/override action으로 나눈다.

## 14. 결론

이 영상에서 조명감독의 본질적 역할은 "무대의 실제 물리 구조와 미적 판단"을 확정하는 것이다. fixture가 어디에 있고, 어떤 방향으로 설치됐고, 어떤 position이 좋은지, 어떤 색이 실제로 맞는지, solo spot이 어디를 비춰야 하는지는 감독이 결정한다.

Copilot의 본질적 역할은 그 판단을 grandMA3 showfile 구조에 정확히 연결하는 것이다. 즉 patch, fixture ID, selection grid, simrik group, 픽셀 마스터 그룹, 픽셀 마스터 그룹 사용 체크박스, dim default, preset pool, focus matrix, color merge, regen macro, feature grid, override sequence 같은 반복적이고 실수하기 쉬운 작업을 단계별로 안내하고, 위험한 자동화를 막고, 실행 후 검증해야 한다.
