# grandMA3 컬러·디머·빔 이펙트(Phaser) 리서치

> 연구 목적: grandMA3의 페이저(Phaser)로 디머(chase/pulse/sine/strobe), 컬러(2색 체이스/레인보우/컬러 웨이브), 빔(gobo/prism/iris/zoom/focus) 이펙트를 만드는 구체적 절차와 파라미터(Attack/Decay, Measure, Integration Grid 등)를 정리한다. 웹 검색 기반 리서치이며, 실물 콘솔/onPC 라이브 검증은 포함하지 않았다 — 아래 각 레시피는 공식 문서·포럼 근거를 인용하되, 실기 확인이 필요한 항목은 별도로 표시한다.

## 0. 페이저(Phaser) 기본 개념

grandMA3의 페이저는 "이펙트/체이서" 엔진으로, 하나의 프리셋/큐에서 **2개 이상의 스텝(Step)**을 순환시켜 값이 계속 변화하는 출력을 만든다. 정적인 큐가 값 1세트만 갖는 것과 달리, 페이저는 여러 스텝을 반복 재생한다.[^phaser-overview]

핵심 용어:

| 용어 | 의미 |
|---|---|
| **Step** | 페이저를 구성하는 개별 값 세트(절대값 또는 상대값) |
| **Width** | 한 스텝의 시작부터 다음 스텝 시작까지의 시간, 1비트(beat) 대비 퍼센트로 표시 |
| **Transition** | Width 중 값이 실제로 변화(페이드)하는 데 쓰이는 비율(%) |
| **Accel/Decel** | 스텝 전환의 가속/감속 곡선 — Attack/Decay에 대응하는 파라미터(§4 참조) |
| **Speed** | 페이저 전체 재생 속도(BPM, Hz, 또는 초/비트) |
| **SpeedMaster** | 페이저 속도를 지정 익스큐터 마스터에 연동 |
| **Phase** | 각 픽스처가 루프 안에서 차지하는 시간 오프셋, 0~360°로 표시 |
| **Measure** | 전체 루프 길이를 몇 비트로 볼지 지정하는 스케일 레이어(§5 참조) |
| **Form(파형)** | 스텝 전환 곡선의 형태 — Rectangle(사각/스냅), Sawtooth(톱니), Sine(사인), Circle(원) 등[^phaser-editor] |

페이저는 Dimmer, ColorRGB/HSB, Gobo, Prism, Iris, Zoom, Focus, PanTilt 등 표준 어트리뷰트 전반에 동일한 구조로 적용된다.[^phaser-overview] Stomp 기능은 재생 중인 페이저를 정적 스텝 하나로 강제 정지시키며, 페이저 위에 정적 프리셋을 호출하면 자동으로 stomp된다.[^phaser-overview]

---

## 1. 디머 이펙트 (Dimmer Phaser)

### 1.1 체이스(Chase) — 두 값 사이 순환

가장 단순한 형태: 0%와 100% 두 스텝을 만들고 픽스처가 두 스텝 사이를 루프하는 체이서.[^phaser-overview]

**절차 (커맨드라인 방식)**[^dimmer-create]:
1. 픽스처 선택 후 디머 0으로: `At 0 Please`
2. 스텝 2 생성: `MA + Next`(Next Step)
3. 해당 스텝을 100%로: `Full`
4. 두 스텝 모두 선택: `MA + Set`(Step Toggle)

이 상태로도 이미 "온/오프 체이스"가 완성된다. 여기에 페이즈(Phase)를 0~360°로 분산시키면(§1.3) 픽스처가 순차적으로 점등되는 러닝 라이트(chase light) 형태가 된다.

### 1.2 펄스(Pulse)

펄스는 디머가 짧게 튀어 오르는 형태로, 스텝을 3개 이상으로 구성하거나(0% → 100% → 0%) Transition/Width를 좁게 잡아 "짧게 튀는" 모양을 만든다. Width가 좁고 Transition이 크면 순간적으로 확 밝아졌다 사라지는 펄스가 되고, Width가 넓으면 느린 브리딩(breathing) 효과가 된다. Accel/Decel을 -100%로 주면 사인형 브리딩, 0%(리니어)면 각진 펄스가 된다.[^phaser-overview]

### 1.3 사인파(Sine Wave) 디머 페이저 — 공식 레시피

MA Lighting 공식 문서의 "Create a Sinus Dimmer Phaser" 절차:[^dimmer-create]

**방법 1 — Phaser Editor 사용**
1. 픽스처 선택 (예: `Fixture Thru Please`)
2. `Step` 키를 누른 채 0% 디머 프리셋을 탭 → 스텝 1
3. `Step` 키를 누른 채 100% 디머 프리셋을 탭 → 스텝 2
4. Step Bar에서 전체 선택(select-all) 버튼으로 모든 스텝 선택
5. 왼쪽 툴바에서 **Select Form** 툴 선택
6. 오른쪽 툴바에서 **사인파(Sine) 버튼**을 탭 → 전환 곡선이 사인 형태로 바뀜
7. 왼쪽 툴바에서 **Edit Phase** 툴 선택
8. 오른쪽 툴바에서 **360 버튼**을 탭 → 선택된 픽스처들이 파형 위에 고르게 분산(phase distribution)

**방법 2 — 커맨드라인 + 인코더 툴바**
1. 픽스처 선택 후 `At 0 Please`
2. `MA + Next`로 스텝 2 생성 → `Full`
3. `MA + Set`으로 두 스텝 모두 선택
4. 인코더 툴바에서 가속(Accel) = **-100**, 감속(Decel) = **-100** 입력 → 사인형 곡선
5. 인코더 툴바에서 **Phase** 레이어 선택
6. 커맨드라인에 `0 Thru 360 Please` 입력 → 픽스처를 파형 전체에 균등 분산

두 방법 모두 동일한 사인 디머 페이저를 만들며, 프리셋/큐로 저장 가능하다.[^dimmer-create]

### 1.4 스트로브(Strobe) — 디머 기반 사각파

grandMA3 포럼 논의에 따르면 스트로브는 두 가지 접근이 있다:[^strobe]

- **디머 스트로브(구형파)**: 사각형(Rectangle) 폼의 디머 페이저를 만들어 익스큐터에 배치 — 페이더로 속도, 버튼으로 온/오프 토글. 단, 실제 디머 채널을 초당 여러 번 갱신하므로 **데이터 레이트 부하가 크고**, 셔터가 아닌 디머를 쓰는 구조적 한계가 있다는 지적이 있다.
- **셔터(Shutter) 스트로브(권장)**: Open/Closed 두 값으로 셔터 어트리뷰트에 페이저를 만들고, 익스큐터의 페이더/로터리에 속도 컨트롤을 연결. 시퀀스 스피드 마스터를 페이더에 배정해 속도를 조절하는 방법도 언급된다.
- 더 복잡한 스트로브 패턴은 **12스텝 디머 페이저 + Measure=1**로 구성하고, 전체 스텝을 Width 합계 100 이내로 채운 뒤 페이저 그리드의 50% 지점 이전에 모두 배치하는 방식이 예시로 제시된다.

**Form = Rectangle**(사각파)을 선택하면 Transition이 0에 가까워지며 값이 순간적으로 스냅(snap)되어, 사인파의 부드러운 페이드와 대비되는 "딱딱 끊기는" 스트로브/체이스 룩이 나온다(§4 참조).

---

## 2. 컬러 이펙트 (Color Phaser)

### 2.1 2색 체이스 (Two-Color Chase)

포럼에서 제시된 실전 레시피: 곡에 쓰던 컬러 프리셋을 1스텝으로, 페이드해 갈 목표 컬러를 2스텝 템플릿으로 넣는다. 페이저 전용 프리셋 2개를 만들고 매크로로 그 프리셋의 내용을 교체하는 방식이 실무적으로 잘 작동한다는 언급이 있다.[^color-two]

기본 형태:
1. 컬러 믹싱(RGB/HSB) 가능한 픽스처 선택
2. `Step` 홀드 + 색상 A 프리셋 탭 → 스텝 1
3. `Step` 홀드 + 색상 B 프리셋 탭 → 스텝 2
4. Form을 Sine으로 주면 두 색 사이를 부드럽게 크로스페이드, Rectangle이면 두 색이 스냅 전환(하드 컷 체이스)

### 2.2 무지개(Rainbow) — ColorRGB 3스텝 공식 레시피

MA Lighting 공식 문서 "Create Color Rainbow Phaser" 절차:[^rainbow]

**준비물**
- 컬러 믹싱 픽스처(컬러 휠 방식 불가)
- Red / Green / Blue 3개의 컬러 프리셋(컬러 믹싱 시스템으로 저장된 것)
- Phaser Editor 창, 컬러 프리셋 풀

**절차**
1. 픽스처 선택 (예제는 1~8번)
2. 디머를 풀로 설정
3. `X5 | Step` 키를 누른 채 Red 컬러 프리셋 탭 → 스텝 1
4. `X5 | Step` 홀드 + Green 프리셋 탭 → 스텝 2
5. `X5 | Step` 홀드 + Blue 프리셋 탭 → 스텝 3
6. 결과: 모든 픽스처가 함께 R→G→B 무지개색으로 변화

**Phase 분산**
- Phaser Editor의 **Change Phase** 버튼 진입
- 오른쪽 메뉴에서 **360**을 탭 → 픽스처가 파형 전체에 균등 분산 → 픽스처마다 다른 색이 동시에 걸리는 "무지개 스윕" 룩

**주의**: 이 절차는 기본적으로 디머 값도 함께 활성화되므로, 컬러만 출력하고 싶다면 저장 전에 디머 레이어를 비활성화해야 한다.[^rainbow]

포럼에도 동일한 3스텝 레시피가 언급된다: "Step 1 > Preset Ref(Red) → Step 2 > Preset Ref(Green) → Step 3 > Preset Ref(Blue)"로 무지개 효과가 나오며 속도·트랜지션을 조절해 다듬으라는 조언이 있다.[^phaser-overview]

### 2.3 HSB Hue 레이어를 이용한 컬러 웨이브 (Phase 활용)

레인보우 페이저는 ColorRGB 프리셋 3스텝으로도 만들 수 있지만, **HSB 모델의 Hue 레이어만 단독으로 스윕**하면 스텝 수를 늘리지 않고도 연속적인 색상환 회전을 만들 수 있다(Hue 0→360이 색상환 한 바퀴와 대응). 절차 개념:

1. 픽스처의 **Hue** 어트리뷰트에 스텝 1(예: Hue 0), 스텝 2(예: Hue 360, 즉 한 바퀴)를 잡는다
2. Form = **Sine**을 주면 색이 부드럽게 순환하는 것이 아니라 "왕복"하게 되므로, 색상환을 한 방향으로 계속 돌리려면 Form = **Sawtooth(톱니)**가 적합 — 톱니파는 0→360으로 선형 상승 후 다시 0으로 스냅되는 파형으로, Hue처럼 순환(wrap-around)하는 어트리뷰트에 자연스럽다.
3. Saturation/Brightness는 별도 레이어에서 상수 값으로 고정하거나, 별도 페이저로 얹어 밝기·채도 변조를 추가할 수 있다.
4. Phase를 `0 Thru 360`으로 분산하면 픽스처마다 다른 위상에서 색상환을 도는 컬러 웨이브(레인보우 체이스와 시각적으로 유사하되 연속 그라디언트) 효과가 된다.

> 참고: 공식 문서에서 검색으로 확인된 것은 ColorRGB 3스텝 레인보우 레시피이며, HSB Hue 단독 스윕의 구체적 스텝별 화면 캡처는 이번 리서치에서 별도로 확인하지 못했다 — 위 3단계는 페이저 구조(§0)와 Sawtooth 폼의 일반 동작으로부터 도출한 개념적 절차이므로, 실기에서 Hue 레이어의 wrap-around 거동을 먼저 확인 후 적용을 권장한다.

---

## 3. 빔 이펙트 (Gobo / Prism / Iris / Zoom / Focus)

공식 문서는 페이저가 Gobo, Prism, Iris, Zoom, Focus, PanTilt에도 동일한 스텝/폼/페이즈 구조로 적용된다고 명시한다.[^phaser-overview] 다만 각 어트리뷰트의 물리적 성격에 따라 실무 팁이 갈린다.

### 3.1 고보(Gobo) 이펙트

- **인덱스(Index) vs 로테이션(Rotation)**: 픽스처 프로파일에 따라 고보 휠 채널이 인덱스 슬롯과 로테이션 슬롯을 별도로 갖거나, 하나의 채널이 모드에 따라 인덱스/로테이션을 겸한다. 프리셋 저장 시 이 구분을 프로파일이 결정하므로, 고보 로테이트 프리셋이 의도대로 저장되지 않는다는 포럼 이슈가 다수 보고되어 있다.[^gobo-rotate]
- **회전 이펙트**: 고보를 계속 회전시키고 싶을 때, 일부 사용자는 고보 로테이트 프리셋이 제대로 안 잡히는 문제를 우회하기 위해 **고보를 스핀시키는 페이저**를 직접 만들어 해결했다고 보고한다.[^gobo-rotate] 절차 개념: Rotation 어트리뷰트에 스텝 1(0°) → 스텝 2(360° 상대값 또는 로테이션 채널 풀레인지)로 잡고 Form = Sawtooth(연속 회전) 또는 Rectangle(스텝식 인덱스 전환)을 선택.
- **인덱스 체이스**: 여러 고보를 스텝별로 배치(스텝 1=고보 A, 스텝 2=고보 B …)하면 고보가 스냅 전환되는 "고보 체이스"가 된다. 이때는 Form = Rectangle(즉시 전환)이 자연스럽고, Sine/Sawtooth로 보간하면 고보 휠이 인덱스 사이를 기계적으로 스위프하는 모션이 된다(픽스처가 실제 보간을 지원할 때만 유효).

### 3.2 프리즘(Prism) / 아이리스(Iris)

- 콘솔 UI에는 **Zoom, Focus, Prism, Iris**를 한 화면에서 다루는 "고보 피커(Gobo Picker)" 레이아웃 뷰가 있어, 이 4개 어트리뷰트를 묶어서 프리셋/페이저를 만들기 좋다.[^gobo-picker] 컴팩트 고보 피커 레이아웃에는 Zoom, Focus, Gobo, Animation, Iris 컨트롤이 포함된다.[^gobo-picker]
- **아이리스 펄스**: Iris를 0%(닫힘)↔100%(완전 개방) 2스텝으로 잡고 Form=Sine을 주면 빔이 조여졌다 열리는 펄스 룩. Prism도 동일 구조로 In/Out 토글 페이저를 만들 수 있다(프리즘 삽입 여부가 온/오프 성격의 어트리뷰트인 픽스처가 많으므로 Form=Rectangle이 자연스러운 경우가 많다).
- 포럼 스레드 "Iris and Prism"에서 관련 질의가 확인되나, 구체적 스텝 레시피는 공개 검색 결과에서 상세히 확인되지 않았다 — 위 절차는 §0 페이저 구조 및 어트리뷰트 특성으로부터의 일반화이며, 실기 검증이 필요하다.

### 3.3 줌(Zoom) / 포커스(Focus)

- **줌 브리딩**: Zoom을 좁은 각(Spot)↔넓은 각(Wide) 2스텝으로 잡고 Form=Sine, Accel/Decel=-100%로 주면 빔 폭이 부드럽게 좁아졌다 넓어지는 브리딩 효과. Width를 넓게(느리게) 잡을수록 유기적인 느낌을 준다.
- **포커스 스윕**: Focus는 대개 정적 세팅용이지만, 필요 시 근거리↔원거리 2스텝 + Sine 폼으로 아웃포커스↔인포커스를 오가는 몽환적 효과를 줄 수 있다. 다만 대부분의 무빙헤드에서 Focus 모터 속도가 느려 빠른 페이저 Speed에는 응답이 못 따라갈 수 있다는 점을 감안해야 한다(실측 필요).
- Zoom/Focus 페이저는 Gobo Picker 레이아웃에서 함께 다루므로, 하나의 페이저에 Zoom+Iris 두 레이어를 동시에 넣어 "숨쉬는 빔" 조합 이펙트를 만드는 것도 가능하다(레이어별로 스텝 수·폼이 달라도 무방).[^gobo-picker]

---

## 4. Attack/Decay(가속/감속) — 스냅 vs 페이드, 사각파 vs 사인파

grandMA3에는 오디오 이펙트에서 쓰는 "Attack/Decay"라는 이름의 파라미터가 그대로 있는 것은 아니고, 이에 대응하는 것이 **Accel(가속)/Decel(감속)** 레이어와 **Form(파형)** 선택이다.[^phaser-editor][^attack-decay]

- **Accel/Decel = -100%**: 전환 곡선이 사인형(sinus-like)으로 부드러워짐 — 값이 천천히 시작해 빠르게 지나갔다가 다시 천천히 도착하는 **완만한 페이드**. 브리딩, 사인 디머, 컬러 크로스페이드 등 "부드러운" 이펙트에 사용.
- **Accel/Decel = 0%**: 전환이 **리니어(linear)** — 일정한 속도로 값이 변화. 사인만큼 부드럽지도, 사각파만큼 날카롭지도 않은 중간 성격.
- **Form = Rectangle(사각파)**: Transition을 0%에 가깝게 두면 값이 **스냅(snap)**, 즉 순간적으로 전환된다 — 편집기 화면에서도 대각선 페이드 대신 **수직선**으로 표시된다.[^qsg-phasers] 체이스형 컬러/고보 전환, 스트로브에 적합.
- **Form = Sine(사인파)**: 값이 부드러운 S자 곡선으로 전환 — 디머 브리딩, 레인보우 컬러 스윕에 적합.
- **Form = Sawtooth(톱니)**: 한 방향으로 선형 상승 후 스냅 복귀 — Hue처럼 순환(wrap)하는 값의 연속 회전에 적합(§2.3).
- **Form = Circle(원)**: PanTilt 등 2축 값에서 원형 궤적을 그릴 때 사용.

**요약 매핑**:

| 원하는 느낌 | Form | Transition | Accel/Decel |
|---|---|---|---|
| 스냅 체이스(뚝뚝 끊김) | Rectangle | 0%에 가깝게 | 0% (곡선 무의미) |
| 부드러운 사인 페이드 | Sine | 크게(예: 50~100%) | -100% |
| 리니어 페이드 | Sine 또는 임의 | 100% | 0% |
| 연속 순환(Hue 등) | Sawtooth | 100% | 0% |
| 스트로브 | Rectangle | 0% | — |

---

## 5. Measure / 절대값·상대값(Absolute-Relative) 선택

### 5.1 Measure(마디/비트 스케일)

Measure 레이어는 **페이저 전체 루프 길이를 몇 비트(beat)로 볼지** 정의하는 스케일 파라미터다.[^measure] Width로 정의된 각 스텝의 "타고난" 길이 비율은 그대로 유지한 채, Measure 값에 맞춰 **전체 재생 시간만 비례 확대/축소**된다.

**계산 예시**[^measure-math]:
- 3개 스텝이 각각 100%(=1초)로 프로그램되어 합계 3초, Measure=4비트로 설정
  - 스케일 팩터 = 4 ÷ 3 ≈ 1.33
  - 각 스텝이 1.33배 길어져 → 전체 루프 4초, 스텝 간 비율은 유지
- 스텝 1을 50%로 바꾸면
  - 합계 2.5초, 스케일 팩터 = 4 ÷ 2.5 = 1.6
  - 스텝 1은 0.8초, 스텝 2~3은 각각 1.6초

핵심: **Measure는 저장된 Width 값 자체를 바꾸지 않고, 재생 타이밍만 비례 조정**한다.[^measure-math] 이는 음악 템포(BPM)에 맞춰 페이저를 정확히 N비트짜리 루프로 고정하고 싶을 때 유용하다(예: 4비트 스트로브 패턴을 정확히 한 마디에 맞추기).

### 5.2 절대값(Absolute) vs 상대값(Relative)

- 스텝은 **절대값**(예: 디머 50%)이나 **상대값**(예: 디머 -20%, 현재 값 기준 오프셋)을 가질 수 있고, 한 스텝에 절대·상대가 동시에 들어갈 수도 있다.[^measure]
- Phaser Editor 타이틀바의 토글 버튼으로 스텝 표시를 **Absolute / Relative**로 필터링할 수 있으며, 절대값 스텝은 채워진 사각형으로 표시된다.[^measure]
- 절대 페이저와 상대 페이저를 같은 재생에서 동시에 출력하려면 **둘 다 같은 큐에 저장**되어야 한다.[^measure]
- 실무 팁(포럼): 디머에 상대 페이저를 쓰면 "현재 밝기 대비 흔들림"을 표현할 수 있어, 다른 큐/이펙트 위에 얹어도 베이스 룩을 깨지 않고 미세한 변조를 더할 수 있다. 반대로 절대 페이저는 항상 같은 목표값으로 스냅되므로 예측 가능한 반복에 적합하다.

---

## 6. Integration Grid(그리드) / MAtricks 연동

"Integration Grid"라는 명칭 자체보다, grandMA3에서는 **레이아웃 그리드(Grid) 선택 + MAtricks**가 페이저의 Phase(위상) 자동 분산에 통합되는 방식으로 동작한다.

### 6.1 2D 레이아웃 그리드(포지션 페이저)

Phaser Editor의 2D 레이아웃 뷰는 **가로축 = 전체 Pan 범위, 세로축 = 전체 Tilt 범위**로 구성된 인터랙티브 그리드이며, 여기서 페이저 포인트를 직접 배치해 원(Circle)·8자 등 위치 이펙트를 그릴 수 있다.[^phaser-editor]

### 6.2 픽스처 레이아웃 그리드 × Phase 자동 분산 (MAtricks)

픽스처를 사각 그리드(X행 × Y열)로 배치해 놓았을 때, MAtricks의 그리드 좌표를 이용해 **행 단위로 순차 진행**하는 위상차를 자동 계산할 수 있다.[^matricks-grid]

- 예: 10×5 그리드에서 `Phase X 0 Thru 64.8` + `Phase Y 0 Thru 360`을 걸면 행(row) 단위로 순차 진행하는 웨이브가 만들어진다.
- 일반 공식: **PhaseToX = 360 / Y − 360 / (X × Y)** (X = 한 행의 픽스처 수, Y = 행 수) — 그리드 크기에 맞춰 각 행 사이의 위상차를 보정해 "줄줄이" 이어지는 순차 진행을 만든다.[^matricks-grid]
- 한 축만 이펙트를 걸고 싶으면(예: 세로만 웨이브), **원치 않는 축의 MAtricks는 None으로 유지**해야 한다 — X/Y 둘 다 값이 걸려 있으면 두 축 모두 위상 분산이 적용되어 원치 않는 대각선 패턴이 나올 수 있다.[^matricks-grid]
- 주의점(공식 한계): Phase는 원형(0°와 360°가 동일 지점)이므로, MAtricks/레시피 다이얼로그에서 Phase를 설정할 때 재계산이 자동으로 일어나지 않아 0과 360이 같은 지점으로 겹치는 문제가 보고된 바 있다 — `0 Thru 180`처럼 360 미만으로 지정하면 회피 가능하다는 논의가 있다.[^matricks-grid]

### 6.3 실무 적용 — 빔/컬러 이펙트에 그리드 연동

위 §6.2의 그리드 위상 분산은 디머 체이스뿐 아니라 **컬러 웨이브(Hue), 고보 회전, 줌 브리딩** 등 모든 어트리뷰트의 Phase 레이어에 동일하게 적용된다 — 즉 "행마다 순차적으로 무지개색이 도는" 또는 "줄마다 시간차를 두고 줌이 열리는" 그리드 이펙트를 동일한 MAtricks 레시피로 구현할 수 있다.

---

## 7. 사전 정의 페이저(Predefined Phasers) / At Filter / 프리셋 풀 기본값

- Phaser Editor 타이틀바 바로 아래에는 **현재 활성 페이저에 포함된 각 어트리뷰트마다 버튼 하나씩**이 배치되며, 이 버튼들은 **At Filter**로 바로 연결되는 단축 링크로 동작한다.[^phaser-editor] 즉 페이저 안에 Dimmer+ColorRGB+Gobo가 섞여 있으면 3개 버튼이 뜨고, 각각을 눌러 해당 어트리뷰트만 필터링해 편집할 수 있다.
- 필터 풀(Filter Pool) 오브젝트를 편집하는 창은 At Filter 창과 거의 동일한 구성이며, 필터는 페이저 스텝의 픽스처·어트리뷰트를 필터링하는 데 쓰인다 — 즉 페이저와 필터 시스템은 같은 UI/개념을 공유한다.[^at-filter]
- **프리셋 풀의 사전 정의(공장 출하) 페이저 목록**에 대해서는 이번 웹 검색 리서치에서 신뢰할 만한 공식 문서 근거를 확보하지 못했다 — MA Lighting 공식 매뉴얼이나 포럼에서 "preset pool default phaser 목록"을 명시적으로 다루는 페이지를 찾지 못했다. 이 부분은 **미검증(Unverified)**으로 남기며, 실기 확인이 필요하다: onPC/콘솔에서 Preset Pool → Effects(또는 Phaser) 타입 오브젝트를 열어 공장 기본 프리셋이 존재하는지, 있다면 어떤 폼/스텝 구성인지 직접 확인할 것을 권장한다.

---

## 8. 요약 레시피 표

| 이펙트 | 핵심 레이어 | 스텝 구성 | 권장 Form | Phase |
|---|---|---|---|---|
| 디머 체이스 | Dimmer | 0%→100% 2스텝 | Rectangle(스냅) 또는 Sine | 0 Thru 360 |
| 디머 펄스 | Dimmer | 0→100→0 또는 좁은 Width | Sine, Accel/Decel -100% | 개별 조정 |
| 사인 디머 페이저 | Dimmer | 0%/100% 2스텝 | Sine | 0 Thru 360 |
| 스트로브 | Shutter(권장) 또는 Dimmer | Open/Closed 2스텝 | Rectangle | 보통 0(동시) |
| 2색 체이스 | ColorRGB/HSB | 색A/색B 2스텝 | Rectangle(하드컷) 또는 Sine(크로스페이드) | 필요시 분산 |
| 레인보우 | ColorRGB | R/G/B 3스텝 | Sine | 0 Thru 360 |
| 컬러 웨이브(Hue) | HSB Hue | 0°/360° 2스텝 | Sawtooth | 0 Thru 360 |
| 고보 회전 | Gobo Rotation | 0°/360°(상대) | Sawtooth | 개별/그리드 |
| 고보 인덱스 체이스 | Gobo Index | 고보A/B/C 다중 스텝 | Rectangle | 개별 |
| 아이리스 펄스 | Iris | 닫힘/열림 2스텝 | Sine | 개별 |
| 프리즘 토글 | Prism | In/Out 2스텝 | Rectangle | 개별/동시 |
| 줌 브리딩 | Zoom | 좁음/넓음 2스텝 | Sine, Accel/Decel -100% | 개별 |
| 그리드 순차 웨이브(임의 어트리뷰트) | 대상 레이어 + Phase X/Y | 그리드 X×Y | 임의 | `PhaseToX = 360/Y − 360/(X·Y)` |

---

## 출처 (Sources)

- [Create a Sinus Dimmer Phaser (MA Lighting 공식 문서, 2.2)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_create_dimmer.html)
- [Create Color Rainbow Phaser (MA Lighting 공식 문서, 2.0)](https://help.malighting.com/grandMA3/2.0/HTML/phaser_create_rainbow.html)
- [Phasers — 개요 (MA Lighting 공식 문서, 2.0)](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [Phaser Editor (MA Lighting 공식 문서, 2.2)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)
- [Phasers — Quick Start Guide (MA Lighting 공식 문서, 2.0)](https://help.malighting.com/grandMA3/2.0/HTML/qsg_phasers.html)
- [Phasers (2.1) (MA Lighting 공식 문서)](https://help.malighting.com/grandMA3/2.1/HTML/phaser.html)
- [Understanding Phaser Width and Measure mathematics — MA Lighting Forum](https://forum.malighting.com/forum/thread/68396-understanding-phaser-width-and-measure-mathematics/)
- [Grid Selection - MaTricks - Phaser — MA Lighting Forum](https://forum.malighting.com/forum/thread/69260-grid-selection-matricks-phaser/)
- [Gobo rotate presets — MA Lighting Forum](https://forum.malighting.com/forum/thread/8864-gobo-rotate-presets/)
- [Gobo Rotate Preset Help — MA Lighting Forum](https://forum.malighting.com/forum/thread/5471-gobo-rotate-preset-help/)
- [Gobo rotate in cues — MA Lighting Forum](https://forum.malighting.com/forum/thread/8884-gobo-rotate-in-cues/)
- [Iris and Prism — MA Lighting Forum](https://forum.malighting.com/forum/thread/70027-iris-and-prism/)
- [Simple question on Relative Phaser in Dimmer — MA Lighting Forum](https://forum.malighting.com/forum/thread/5413-simple-question-on-relative-phaser-in-dimmer/)
- [We need to talk about phasers honestly — MA Lighting Forum](https://forum.malighting.com/forum/thread/68645-we-need-to-talk-about-phasers-honestly/)
- [Change effect colors on the fly — MA Lighting Forum](https://forum.malighting.com/forum/thread/5770-change-effect-colors-on-the-fly/)
- [Absolute Color Phasers - Questions/Suggestions — MA Lighting Forum](https://forum.malighting.com/forum/thread/68881-absolute-color-phasers-questions-suggestions/)
- [Question about variable strobe rate on a rotary knob — MA Lighting Forum](https://forum.malighting.com/forum/thread/9194-question-about-variable-strobe-rate-on-a-rotary-knob/)
- [Create fader for strobe speed — MA Lighting Forum](https://forum.malighting.com/forum/thread/68084-create-fader-for-strobe-speed/)
- [Create a Filter (MA Lighting 공식 문서, 2.3)](https://help.malighting.com/grandMA3/2.3/HTML/worldfilter_filter_create.html)
- [Phasers in GrandMA3 - MxU](https://app.getmxu.com/lessons/phasers-in-grandma3)
- [Phasers in GrandMA3 - Chase Effects (YouTube)](https://www.youtube.com/watch?v=296WRfavW80)
- [E10 - Phaser Effects For Beginners - GrandMA3 OnPC Tutorial (YouTube)](https://www.youtube.com/watch?v=KMGH4YPruuc)

[^phaser-overview]: [Phasers 개요](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html) — 페이저 정의, 스텝/Width/Transition/Accel/Decel/Speed/Phase/Measure, 지원 어트리뷰트(Dimmer/ColorRGB·HSB/Gobo/Prism/Iris/Zoom/Focus/PanTilt), Stomp 기능.
[^phaser-editor]: [Phaser Editor](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html) — Step Bar, Select Form(Rectangle/Sawtooth/Sine/Circle), Move Handles(Accel/Decel), Phaser Bar 인코더(Speed/Phase/Transition/Width/Measure), 어트리뷰트별 At Filter 단축 버튼, 2D 레이아웃 그리드(Pan/Tilt).
[^dimmer-create]: [Create a Sinus Dimmer Phaser](https://help.malighting.com/grandMA3/2.2/HTML/phaser_create_dimmer.html) — 사인 디머 페이저 생성 2가지 방법(Phaser Editor / 커맨드라인+인코더).
[^strobe]: [Question about variable strobe rate](https://forum.malighting.com/forum/thread/9194-question-about-variable-strobe-rate-on-a-rotary-knob/), [Create fader for strobe speed](https://forum.malighting.com/forum/thread/68084-create-fader-for-strobe-speed/) — 디머 vs 셔터 스트로브, 12스텝 Measure=1 구성 예.
[^color-two]: [Change effect colors on the fly](https://forum.malighting.com/forum/thread/5770-change-effect-colors-on-the-fly/) — 2색 체이스에서 프리셋 교체를 이용한 색상 전환 실무 팁.
[^rainbow]: [Create Color Rainbow Phaser](https://help.malighting.com/grandMA3/2.0/HTML/phaser_create_rainbow.html) — R/G/B 3스텝 레인보우 페이저 생성 절차, Change Phase 360 분산, 디머 레이어 주의사항.
[^gobo-rotate]: [Gobo rotate presets](https://forum.malighting.com/forum/thread/8864-gobo-rotate-presets/), [Gobo Rotate Preset Help](https://forum.malighting.com/forum/thread/5471-gobo-rotate-preset-help/), [Gobo rotate in cues](https://forum.malighting.com/forum/thread/8884-gobo-rotate-in-cues/) — 고보 인덱스/로테이션 채널 구분, 페이저로 회전 우회 사례.
[^gobo-picker]: 검색 결과 요약(공식 문서 파생) — Zoom/Focus/Prism/Iris/Gobo/Animation을 한 화면에 두는 Gobo Picker 레이아웃 뷰.
[^attack-decay]: [Understanding Phaser Width and Measure mathematics](https://forum.malighting.com/forum/thread/68396-understanding-phaser-width-and-measure-mathematics/) 및 [Phaser Editor](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html) — Accel/Decel과 Form(Rectangle/Sine/Sawtooth)의 스냅 vs 페이드 대응.
[^qsg-phasers]: [Phasers — Quick Start Guide](https://help.malighting.com/grandMA3/2.0/HTML/qsg_phasers.html) — Transition 0%일 때 스냅(수직선) 표시, Restart Mode 등.
[^measure]: [Phasers (2.1)](https://help.malighting.com/grandMA3/2.1/HTML/phaser.html), [Simple question on Relative Phaser in Dimmer](https://forum.malighting.com/forum/thread/5413-simple-question-on-relative-phaser-in-dimmer/) — 절대/상대 스텝, Measure 레이어 정의, Absolute/Relative 필터 토글.
[^measure-math]: [Understanding Phaser Width and Measure mathematics](https://forum.malighting.com/forum/thread/68396-understanding-phaser-width-and-measure-mathematics/) — Width×Measure 스케일 팩터 계산 예시.
[^matricks-grid]: [Grid Selection - MaTricks - Phaser](https://forum.malighting.com/forum/thread/69260-grid-selection-matricks-phaser/) — 그리드 X/Y Phase 자동 분산 공식(PhaseToX), 단일 축 이펙트 시 MAtricks None 유지, Phase 0/360 겹침 이슈.
[^at-filter]: [Create a Filter](https://help.malighting.com/grandMA3/2.3/HTML/worldfilter_filter_create.html) — 필터 풀 편집 창과 At Filter 창의 구성 동일성, 필터-페이저 연동.
