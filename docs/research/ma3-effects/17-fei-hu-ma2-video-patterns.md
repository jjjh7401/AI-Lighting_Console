# Fei Hu Facebook MA2 영상 사례 분류 — Copilot 입력 지식

> 수집일: 2026-09-11  
> 출처: `https://www.facebook.com/fei.hu.148015` 공개/로그인 세션에서 보이는 Facebook 피드와 릴스 캡션  
> 범위: 개별 영상을 전부 목록화하지 않고, 반복되는 조명 효과 유형과 MA 기능 연결을 추출한다.  
> 한계: Facebook 피드의 캡션·날짜·영상 플레이어 표시는 확인했지만, 모든 영상의 전체 프레임을 다운로드/분석하지 않았다. 아래 내용은 "영상 내부 구현을 실측했다"가 아니라 "게시자가 명명한 MA2/onPC 효과 사례를 Copilot 지식으로 분류한 것"이다.

## 1. 페이지 성격

Fei Hu 프로필은 "Lighting Design Trainer | Learn Stage Lighting Programming" 계열의 MA2 / DMX / stage lighting 교육·효과 템플릿 채널이다. 피드에는 짧은 튜토리얼과 효과 프리셋 팩 홍보 영상이 반복적으로 올라오며, 캡션은 효과명을 직접 붙이는 방식이다.

이 자료는 grandMA3 Copilot에 그대로 실행 명령으로 넣기보다, 사용자의 자연어 요청을 다음 범주로 해석하는 사전으로 쓰는 것이 맞다.

- 사용자가 말하는 "MA onPC 효과"는 대개 MA2 이펙트/템플릿 용어다.
- grandMA3에서는 같은 의도를 Phaser + Sequence/Cue + Executor + SpeedMaster/MAtricks 조합으로 번역해야 한다.
- "Preset Pack", "Template Pack", "Effect Library"는 단일 룩이 아니라 재사용 가능한 프리셋/시퀀스/익스큐터 묶음 요청으로 해석한다.

## 2. 관측된 캡션 근거

| 날짜 표시 | 캡션/사례명 | 영상 길이 표시 | Copilot 분류 |
|---|---|---:|---|
| 14시간 | `MA2 Beam Prism Chase Lighting Effect` | 1:11 | 빔/프리즘 체이스 |
| 1일 | `MA2 Lighting Effect Preset Pack for stage lighting programming` | 0:35 | 이펙트 프리셋 팩 |
| 1일 | `MA2 Bounce Chase Effect` | 1:59 | 바운스 체이스 |
| 2일 | `MA2 Effect Template Pack｜Import For Instant Effects` | 0:45 | 템플릿/임포트 팩 |
| 2일 | `MA2 Audience Blinder Beat Effect Tutorial` | 0:52 | 블라인더 비트 |
| 3일 | `MA2 BPM Thru Method` | 1:17 | BPM/SpeedMaster |
| 6일 | `How to Make MA2 Dim + Tilt Phase Offset` | 1:49 | 디머+틸트 위상차 |
| 9월 4일 | `MA2 Bounce Chase｜Lighting Run Effect` | 2:14 | 런/체이스 |
| 9월 2일 | `MA2 Symmetric V-Shape Pan Swing Effect` | 2:52 | 대칭 V 팬 스윙 |
| 9월 1일 | `MA2 Beam Bounce Beat-Sync Effect Tutorial` | 2:17 | 빔 바운스 + 비트 싱크 |
| 8월 29일 | `Creating Horizontal Chase Effect on MA2` | 2:06 | 수평 체이스 |
| 8월 27일 | `MA2 Console: Flash fade out effect` | 1:16 | 플래시 페이드아웃 |
| 8월 27일 | `MA2 Prism Beat Effect Creation` | 2:41 | 프리즘 비트 |
| 8월 23일 | `MA2: Fade-out & Delay-out` | 2:54 | 큐 타이밍/딜레이 |
| 8월 21일 | `Fade-in and Delay-in for MA2` | 2:01 | 큐 타이밍/딜레이 |
| 8월 19일 | `Zoom & Dimmer Effect Programming` | 2:26 | 줌+디머 브리딩/펄스 |
| 8월 18일 | `How to Make Pan & Tilt Sweep Effect on MA2` | 2:30 | 팬/틸트 스윕 |
| 8월 14일 | `Tips for Beat Programming on MA2` | 2:03 | 비트 프로그래밍 |
| 8월 12일 | `Set Trigger Timing Macro | MA2` | 2:25 | 매크로/트리거 타이밍 |
| 8월 10일 | `MA2 Tip: One-Click Delete All Presets` | 2:16 | 프리셋 관리 매크로 |
| 8월 7일 | `Switch RGB Mixing Mode on MA2 Console` | - | 컬러 믹싱 모드 |
| 8월 5일 | `Creating Symmetric Effects for Circular Fixture Layout` | - | 원형 배치 대칭 이펙트 |
| 8월 4일 | `How to Make Circle Effects with MA2` | - | 서클/발리후 |

Facebook 날짜 링크에서 확인된 예시 permalink는 `/reel/1097811506088350/`, `/reel/1356070376688458/`, `/reel/1588449559567305/`, `/reel/27848848878112828/`, `/reel/37677024158578759/`, `/reel/968477166197657/` 등이다. Facebook의 세션 파라미터는 저장하지 않는다.

## 3. 효과 카테고리와 MA 기능 매핑

| 카테고리 | 사용자가 말할 법한 표현 | MA2/onPC 관점 | grandMA3 Copilot 해석 |
|---|---|---|---|
| 빔/프리즘 체이스 | 프리즘 체이스, 빔이 튀게, 프리즘 비트 | Beam/Prism attribute effect, chase order, beat speed | `beam` 계열 Phaser 후보. Prism In/Out 또는 Prism Rotate가 픽스처별 GDTF에 의존하므로 안전하게는 수동 확인/리그 가드 필요 |
| 바운스/런 체이스 | bounce chase, lighting run, 좌우로 달리게 | 선택 순서 또는 MAtricks phase spread | `movement` + `dimmer` 조합. Phase 0 thru 360, X/Y spread, reverse, wings를 우선 파라미터로 본다 |
| 비트 싱크 | BPM thru, beat-sync, beat programming | Speed/BPM, Speed Master, tap tempo, executor speed | 고정 `speed`보다 `speed_master` 우선. 여러 효과를 같은 SpeedMaster에 묶는 요청으로 해석 |
| 팬/틸트 모션 | Pan & Tilt sweep, V-shape, circle, circular layout | Pan/Tilt effect, symmetry, layout/grid | 기존 `sweep`, `circle`, `diagonal` 확장. V-shape는 Pan 양끝 + Tilt 중심 또는 Tilt offset을 가진 대칭 패턴 후보 |
| 디머/줌 브리딩 | zoom & dimmer, dim+tilt offset, flash fade out | Dimmer/Zoom step, phase offset, fade timing | `dimmer` Phaser + beam Zoom axis 후보. Flash는 위험도가 있어 full-range rapid flash로 자동 생성하지 않는다 |
| 블라인더 비트 | audience blinder beat | Dimmer cue/chase, executor flash | 관객 방향 블라인더는 안전 가드 필요. 낮은 duty/낮은 speed 또는 수동 승인 후보 |
| 페이드/딜레이 | fade-in, delay-in, fade-out, delay-out | Cue fade/delay, fixture delay fan | Phaser가 아니라 Cue timing/Recipe. Store Cue 후 per-fixture/group Fade/Delay를 넣는 시퀀스 작업 |
| 템플릿/프리셋 팩 | preset pack, template pack, effect library | Preset pool, effect pool, macro import | 사용자가 "팩"을 요청하면 한 효과가 아니라 카테고리별 여러 프리셋/시퀀스/매크로 묶음을 생성하도록 라우팅 |
| 매크로/관리 | trigger timing macro, one-click delete presets | Macro, trigger, pool operation | 삭제 계열은 금지/확인 대상. Trigger timing은 매크로 생성 또는 시퀀스 트리거 설정 작업 |
| 컬러 믹싱 | RGB mixing mode, color effect | ColorRGB/HSB, color mixing mode | `color` Phaser 전 단계로 픽스처 색상 모델 확인 필요. RGB/HSB/Hue 지원 여부를 리그에서 읽고 적용 |

## 4. Copilot 의도 분류 규칙

### 4.1 "Effect"와 "Cue timing"을 분리한다

Fei Hu 영상 캡션은 모두 "effect"처럼 보이지만 실제 작업면은 둘로 갈린다.

- 반복 재생 룩: Prism Chase, Bounce Chase, Circle, Pan/Tilt Sweep, Zoom & Dimmer
- 큐 전환 질감: Fade-in/Delay-in, Fade-out/Delay-out, Flash fade out

Copilot은 사용자가 "이펙트"라고 말해도 `phaser`가 맞는지 `sequence cue timing`이 맞는지 먼저 분류해야 한다. "처음에 순차로 켜지고 사라지게"는 Phaser보다 Cue Delay/Fade가 자연스럽다.

### 4.2 "Beat"는 SpeedMaster 우선

`BPM Thru Method`, `Beam Bounce Beat-Sync`, `Audience Blinder Beat`, `Tips for Beat Programming`이 반복된다. 이 계열은 개별 효과마다 BPM 숫자를 박는 것보다 SpeedMaster/Executor speed에 묶는 것이 실전적이다.

Copilot 기본 해석:

1. 사용자 요청에 "비트", "BPM", "템포", "sync", "beat"가 있으면 `speed_master` 후보를 우선 제안한다.
2. 여러 효과가 한 문장에 있으면 같은 SpeedMaster로 묶는다.
3. SpeedMaster가 실측/할당되지 않았으면 고정 BPM을 쓰되 보고에 "속도 마스터 미연결"을 남긴다.

### 4.3 "Symmetric", "V-shape", "Circular layout"은 MAtricks/그리드 문제다

대칭·원형 배치 영상은 단순히 Pan/Tilt 값을 바꾸는 것이 아니라, 선택 순서와 위상 분산이 룩을 결정한다.

Copilot 기본 해석:

- `symmetric`, `mirror`, `V-shape`: `x_wings: 2` 또는 좌우 그룹 분리 후 반대 phase/reverse.
- `circular fixture layout`: layout/grid 좌표 기반 phase spread. 그리드가 없으면 선택 순서 기반 phase로 낮춰 실행하고 한계를 보고한다.
- `horizontal chase`: X축 phase spread. 좌우 방향은 `reverse`로 제어.

### 4.4 "Preset Pack"은 라이브러리 빌드 요청이다

Fei Hu 피드의 큰 축은 개별 튜토리얼뿐 아니라 `Preset Pack`, `Template Pack`, `Effect Library` 판매/배포형 콘텐츠다. Copilot에서 이 요청은 다음 산출물 묶음으로 해석한다.

- Dimmer: pulse, sine breath, snap pulse, master-sync pulse
- Movement: sweep, horizontal chase, bounce chase, circle, V-shape swing
- Color: RGB chase, rainbow wave, warm/cool transition
- Beam: zoom breath, prism beat, prism chase, gobo/iris 후보
- Timing: fade-in delay-in, fade-out delay-out cue recipes
- Macros: trigger timing setup, speed assignment, safe pool management

## 5. 실제 콘솔 연동 모델

이 문서를 Copilot에 반영하려면 "조명감독 용어"를 곧바로 명령어로 바꾸면 안 된다. 중간에 구조화된 의도 객체를 만들고, 그 객체가 실제 grandMA3 객체와 안전하게 연결되는지 확인해야 한다.

### 5.1 처리 파이프라인

| 단계 | 입력 | Copilot 내부 산출물 | grandMA3 연결 |
|---|---|---|---|
| 1. 자연어 해석 | "바운스 체이스를 비트에 맞춰" | `EffectRequest(kind="bounce_chase", sync="beat")` | 아직 콘솔 명령 없음 |
| 2. 대상 해석 | "무빙", "빔", "블라인더" | `TargetResolver(group="MOVER-U", fixture_class="moving")` | Group / Fixture / Selection 확인 |
| 3. 속성 해석 | Pan, Tilt, Dimmer, Prism, Zoom | `AttributePlan(["Pan", "Tilt"], profile_checked=true)` | GDTF/fixture profile 또는 기존 patch metadata |
| 4. 저장 위치 결정 | "프리셋으로", "실행기에" | `StorePlan(destination="sequence", executor=optional)` | Preset pool / Sequence / Cue / Executor |
| 5. 명령 생성 | 구조화된 plan | command bundle | OSC `run_commands` 또는 MA3 command line |
| 6. 안전 게이트 | flash/delete/overwrite 여부 | accept / reject / ask | 위험 명령 차단, 수동 확인 |
| 7. 관측/보고 | console verdict + 사용자 관측 | `EffectReport` | 저장된 Sequence/Cue 번호, 확인 한계 |

### 5.2 공통 의도 스키마

Copilot의 FX 요청은 최소한 아래 필드를 가져야 한다.

```json
{
  "intent": "create_lighting_effect",
  "effect_kind": "bounce_chase",
  "target": {
    "group_label": "MOVER-U",
    "fixture_class": "moving_head"
  },
  "attributes": ["Pan", "Tilt", "Dimmer"],
  "timing": {
    "sync": "speed_master",
    "speed_master": 1,
    "phase": "x_spread",
    "reverse": false
  },
  "store": {
    "destination": "sequence",
    "sequence_label": "FX Bounce Chase",
    "cue": 1,
    "executor": null
  },
  "safety": {
    "audience_blinder": false,
    "destructive_pool_operation": false,
    "profile_dependent_attributes": []
  }
}
```

이 스키마가 있어야 사용자의 "효과 만들어줘"가 다음 중 어디에 해당하는지 분명해진다.

- Phaser 생성: Step 2개 이상, Phase/Speed/Width/Measure 적용, Sequence 또는 Preset 저장
- Cue timing 생성: Fade/Delay fan, Cue 저장, Phaser 아님
- Macro 생성: Trigger timing, SpeedMaster 할당, 반복 조작 자동화
- Pack 생성: 여러 Phaser/Sequence/Macro를 묶은 라이브러리

### 5.3 사례별 콘솔 연결 방식

| 사용자/영상 표현 | Copilot 의도 | 필요한 확인 | MA 객체 | 명령 생성 골격 |
|---|---|---|---|---|
| "바운스 체이스", `Bounce Chase` | `bounce_chase` Phaser | 대상 그룹, X/Y 또는 선택 순서 | Sequence Cue 1, optional Executor | `ClearAll → Group <target> → Step 1/2 값 → At Phase 0 Thru 360 → At SpeedMaster 1 → Store Sequence <n> Cue 1` |
| "비트에 맞춰", `BPM Thru`, `Beat-Sync` | speed binding | SpeedMaster 번호, 기존 할당 여부 | SpeedMaster, Executor speed | 기존 Phaser 생성 시 `speed_master` 사용. 여러 효과면 같은 SpeedMaster로 묶음 |
| "페이드 인 딜레이", `Fade-in and Delay-in` | cue timing recipe | 적용 그룹, 순서, fade/delay 값 | Sequence Cue | `Group <target> → At <look> → Store Cue → cue/group별 Fade/Delay fan 입력` |
| "프리즘 비트", `Prism Beat` | beam Phaser | Prism 어트리뷰트명, prism in/out 또는 rotate 지원 | Sequence 또는 Preset | profile 확인 후 Prism Step 1/2. 확인 전에는 실행 계획만 생성 |
| "줌이랑 디머 숨쉬게", `Zoom & Dimmer` | combo Phaser | Zoom 어트리뷰트명, 모터 속도 한계 | Sequence Cue 1 | Dimmer + Zoom Step 1/2, 느린 speed, Accel/Decel |
| "트리거 타이밍 매크로" | macro helper | 어떤 시퀀스/큐를 트리거할지 | Macro, Sequence trigger | 명령 묶음을 Macro에 저장. 기존 객체 overwrite 여부 확인 |
| "프리셋 한 번에 지워" | destructive pool op | 사용자가 명시한 삭제 범위 | Preset pool | 기본 거절. 백업/범위/확인 없이는 명령 생성 금지 |

### 5.4 명령 생성 골격 예시

아래는 개념 골격이다. 실제 번호와 어트리뷰트명은 리그/콘솔 상태를 읽은 뒤 채워야 한다.

```text
// Bounce Chase / Run Effect
ChangeDestination Root
ClearAll
Group <target_group>
At <base_intensity>
Step 2
At <accent_intensity>
Attribute "Dimmer" At Phase 0 Thru 360
Attribute "Dimmer" At SpeedMaster 1
Store Sequence <free_sequence> Cue 1
Label Sequence <free_sequence> "FX Bounce Chase - <target>"
ClearAll
```

```text
// Fade-in Delay-in은 Phaser가 아니라 Cue timing
ChangeDestination Root
ClearAll
Group <target_group>
At Preset <look_preset>
Store Sequence <sequence> Cue <cue>
// 이후 Cue editor 또는 검증된 command path로 group/fixture별 Fade/Delay fan 입력
```

```text
// Prism Beat는 profile-dependent
// Prism 어트리뷰트가 확인되지 않으면 여기서 멈추고 사용자에게 계획만 보여준다.
ChangeDestination Root
ClearAll
Group <beam_group>
Attribute "<verified_prism_attribute>" At <prism_off_value>
Step 2
Attribute "<verified_prism_attribute>" At <prism_on_or_rotate_value>
Attribute "<verified_prism_attribute>" At SpeedMaster 1
Store Sequence <free_sequence> Cue 1
```

### 5.5 Copilot에 반영할 구현 단위

| 구현 위치 | 넣을 내용 | 비고 |
|---|---|---|
| `server/fx/matching.py` | "바운스 체이스", "프리즘 비트", "V자 팬 스윙" 같은 자연어 매칭 | 바로 실행하지 않는 후보도 `requires_profile_check`로 분리 |
| `server/fx/library/movement.yaml` | 수평 체이스, 바운스 런, V-shape pan swing | Pan/Tilt 계열, 기존 phase/wings 필드 활용 |
| `server/fx/library/dimmer.yaml` | 안전한 low-duty blinder beat 후보 | 관객 방향이면 확인 카드 필요 |
| 새 `beam.yaml` 또는 별도 beam registry | prism, zoom, iris, gobo 후보 | GDTF/attribute 검증 레이어 없이는 실행 금지 |
| sequence recipe 모듈 | fade-in/out delay fan | FX 라이브러리와 분리 |
| safety gate | flash/delete/overwrite/profile-dependent 차단 | 콘솔 명령 생성 전 실행 |

## 6. FX 라이브러리 확장 후보

아래 항목은 `server/fx/library/*.yaml`에 바로 넣을 수 있는 "검증 완료"가 아니라, Fei Hu 영상 사례에서 수요가 확인된 후보 목록이다.

| 후보 ID | 표시명 | 패턴 | 필요한 축 | 근거 캡션 | 구현 메모 |
|---|---|---|---|---|---|
| `beam-prism-chase` | 프리즘 체이스 | beam/chase | Prism, Dimmer 또는 Pan/Tilt | `Beam Prism Chase Lighting Effect` | Prism attribute 이름이 기종 의존. `profile_dependent_attributes=["Prism"]`로 실행 전 가드 |
| `prism-beat` | 프리즘 비트 | beam/pulse | Prism In/Out 또는 Rotate | `Prism Beat Effect Creation` | beat 요청이면 SpeedMaster 연결 |
| `bounce-run-x` | 바운스 런 체이스 | movement/pulse | Pan 또는 Tilt + Dimmer | `Bounce Chase`, `Lighting Run Effect` | X spread + reverse/wings 조합 |
| `vshape-pan-swing` | V 팬 스윙 | movement | Pan, optional Tilt | `Symmetric V-Shape Pan Swing` | 좌우 wings 또는 그룹 split. center aim 필요 |
| `horizontal-chase` | 수평 체이스 | movement/chase | Pan or Dimmer, X phase | `Creating Horizontal Chase Effect` | 기존 `phase_from_x/to_x` 활용 가능 |
| `dim-tilt-offset` | 딤 틸트 위상차 | combo | Dimmer + Tilt | `Dim + Tilt Phase Offset` | 속성별 90/180도 offset 지원이 스키마에 있는지 확인 필요 |
| `zoom-dimmer-breath` | 줌 디머 브리딩 | beam+dimmer | Zoom + Dimmer | `Zoom & Dimmer Effect Programming` | Zoom axis는 fixture profile 의존. 느린 speed 기본 |
| `blinder-beat-safe` | 안전 블라인더 비트 | dimmer | Dimmer | `Audience Blinder Beat` | audience blinder라 자동 full flash 금지. 낮은 duty/speed 또는 확인 카드 |
| `flash-fade-out` | 플래시 페이드아웃 | cue timing | Cue fade/delay | `Flash fade out effect` | Phaser보다 cue recipe. 높은 강도의 반복 플래시로 만들지 않음 |
| `fade-delay-fan-in` | 페이드 딜레이 인 | cue timing | Cue Fade/Delay | `Fade-in and Delay-in` | group/fixture delay fan |
| `fade-delay-fan-out` | 페이드 딜레이 아웃 | cue timing | Cue Fade/Delay | `Fade-out & Delay-out` | out cue 또는 stomp cue와 연계 |
| `circle-layout-symmetric` | 원형 배치 서클 | movement/grid | Pan/Tilt + layout grid | `Circle Effects`, `Circular Fixture Layout` | grid 없으면 selection order 기반으로 downgrade |

## 7. Copilot 응답/생성 정책

1. **MA2 캡션을 MA3 명령으로 단정 변환하지 않는다.** MA2 Effect/MA3 Phaser는 개념상 대응하지만 명령·저장 구조는 다르다.
2. **빔 속성은 픽스처 프로파일 확인 전 자동 확정하지 않는다.** Prism, Gobo, Iris, Zoom, Focus는 GDTF별 어트리뷰트명이 다를 수 있다.
3. **반복 플래시/블라인더는 안전 가드를 우선한다.** `Audience Blinder Beat`, `Flash` 계열은 낮은 속도/짧은 duration/수동 확인으로 제한한다.
4. **비트 계열은 SpeedMaster 묶음을 우선한다.** 단발 BPM보다 운영자가 공연 중 조절 가능한 구성이 Fei Hu 사례의 실전 톤과 맞다.
5. **템플릿 팩 요청은 "여러 카테고리의 재사용 객체"로 만든다.** 단일 큐가 아니라 프리셋/시퀀스/익스큐터/매크로 세트를 계획한다.
6. **큐 타이밍과 페이저를 섞되 저장 단위를 분리한다.** 룩은 Phaser/Sequence Cue 1, 전환은 별도 Cue Fade/Delay 또는 follow cue로 분리하면 Copilot이 설명하기 쉽다.

## 8. 자연어 매칭 사전 후보

| 사용자 표현 | 라우팅 |
|---|---|
| "Fei Hu 스타일", "MA2 템플릿팩 느낌" | effect-pack plan |
| "프리즘 체이스", "빔 프리즘 돌려" | beam-prism-chase |
| "바운스 체이스", "통통 튀게", "런 이펙트" | bounce-run-x |
| "비트에 맞춰", "BPM으로", "템포 동기" | speed_master binding |
| "V자로 흔들어", "대칭 팬 스윙" | vshape-pan-swing |
| "수평 체이스", "좌우로 달리게" | horizontal-chase |
| "원형 배치로 돌려", "서클 이펙트" | circle-layout-symmetric |
| "줌이랑 디머 같이 숨쉬게" | zoom-dimmer-breath |
| "페이드 인 딜레이", "순서대로 켜져" | fade-delay-fan-in |
| "페이드 아웃 딜레이", "순서대로 사라져" | fade-delay-fan-out |
| "트리거 타이밍 매크로" | macro trigger timing |
| "프리셋 한 번에 지워" | destructive pool operation; refuse or require explicit safe plan |

## 9. 다음 구현 순서 제안

1. `matching.py`에 위 자연어 표현을 "후보"로 추가하되, 빔/블라인더/삭제 계열은 바로 실행하지 말고 안전/리그 확인 라우트로 보낸다.
2. `movement.yaml`에는 비교적 안전한 `horizontal-chase`, `bounce-run-x`, `vshape-pan-swing`부터 추가한다.
3. `dimmer.yaml`에는 `fade-delay`가 아니라 `blinder-beat-safe` 후보만 별도 안전 분류로 둔다.
4. `beam.yaml`을 새로 만들려면 Prism/Zoom attribute 검증 레이어를 먼저 둔다.
5. Cue timing 레시피는 FX 라이브러리가 아니라 별도 sequence recipe로 설계한다.
