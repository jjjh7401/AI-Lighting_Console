# grandMA3 Phaser 엔진 기초 연구

> 리서치 태스크 A — grandMA3 공식 도움말(help.malighting.com), MA Lighting 포럼, 커뮤니티 튜토리얼을 web-search/web-fetch로 조사한 결과를 정리한 문서. 모든 항목에 출처 URL을 병기한다.

## 0. 요약

grandMA3의 **Phaser**는 grandMA2의 "Effect Engine(이펙트 엔진)"을 대체하는 동적 출력 생성기다. 하나의 프리셋/큐 값에서 출발해, 2개 이상의 **Step(스텝)**에 저장된 값을 시간에 따라 순환·보간하며 지속적으로 변화하는 출력을 만든다. 이 문서는 다음을 다룬다.

- Phaser란 무엇인가, MA2 이펙트와의 차이
- Step 개념 — 절대값(Absolute)과 상대값(Relative)
- Phaser Editor의 구조와 조작 도구
- 핵심 파라미터: Speed, Phase, Measure, Width, Attack/Decay(Accel/Decel), Transition, Grouping/Wings/Blocks, Speed Group(SpeedMaster)
- Phase 오프셋(0..360도)으로 파도(wave) 효과를 만드는 원리와 실측 수치 예시

---

## 1. Phaser란 무엇인가

grandMA3 공식 도움말은 Phaser를 다음과 같이 정의한다.

> "Phasers change the output for attributes using a set of information in two or more steps."
> (Phaser는 2개 이상의 스텝에 담긴 정보 집합을 이용해 속성(attribute)의 출력을 변화시킨다.)

정적인 큐(Cue)가 한 시점의 단일 값 집합을 담는 것과 달리, Phaser는 여러 Step을 순환시켜 **연속적으로 변화하는 출력**을 만든다. grandMA3 커뮤니티에서는 Phaser를 "grandMA3의 이펙트이자 체이서(chaser)"로 요약한다 — 하나의 프리셋이나 큐로부터 동적인 출력을 파생시키는 도구라는 뜻이다.

출처:
- [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [MA3 Phaser vs MA2 Effect — MA Lighting Forum](https://forum.malighting.com/forum/thread/68774-ma3-phaser-vs-ma2-effect/)

---

## 2. Phaser vs grandMA2 Effect Engine

| 구분 | grandMA2 Effect Engine | grandMA3 Phaser |
|---|---|---|
| 기본 단위 | Form(폼) 번호로 선택하는 사전 정의된 파형 | 2개 이상의 Step을 직접 조합해서 구성 |
| 파형 제어 | High/Low 값 + Form 선택 | Width, Transition, Accel(Acceleration), Decel(Deceleration)의 조합 |
| 대표 예시 | Ramp 이펙트, Width 25~35 조합으로 Dim/Tilt 효과 | 동일 결과를 Step Width·Transition 값의 조합으로 재현 |
| PWM류 Form | Form 13/14/15 "Phase 1/2/3" — 작은 Attack/Decay + 120도 위상차 | Accel/Decel 값과 Phase 오프셋으로 동일 파형 재현 |
| 구조 | 단일 계층(이펙트 파라미터가 평면적) | 다층 구조 — Value 레이어(Absolute/Relative)와 Step 레이어(Width/Transition/Accel/Decel)가 분리 |

MA Lighting 포럼과 ACT Entertainment 지원 문서에 따르면, "원칙적으로 표준 grandMA2 Form은 grandMA3 Phaser Step 2개 이상의 Width·Transition·Acceleration·Deceleration 조합으로 재현할 수 있다"고 안내된다. 다만 MA2에서 Width 25~35 정도의 Ramp 이펙트로 Dim/Tilt 효과를 만들던 방식은 MA3에서 Width의 의미(스텝 시작~다음 스텝 시작까지의 전체 시간 비율)가 다르게 정의되어 있어 그대로 이식되지 않고, 값의 재계산이 필요하다.

출처:
- [MA3 Phaser vs MA2 Effect — MA Lighting Forum](https://forum.malighting.com/forum/thread/68774-ma3-phaser-vs-ma2-effect/)
- [Using grandMA3 Phasers to replicate grandMA2 Forms — ACT Entertainment](https://support.actentertainment.com/knowledgeBase/25504931)
- [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)

---

## 3. Step 개념 — 절대값(Absolute)과 상대값(Relative)

Phaser는 다층(layer) 구조로 되어 있으며, 각 Step은 크게 두 종류의 값 레이어를 가질 수 있다.

- **Absolute(절대) 레이어**: 스텝이 담는 값이 절대값이다. 예: Dimmer 50%. Phaser Editor에서는 채워진 정사각형(노란색 = 프로그래머 값, 청록색 = 프리셋 값)으로 표시된다.
- **Relative(상대) 레이어**: 스텝이 담는 값이 기존 값에 대한 상대 조정치다. 예: -20% 조정. Phaser Editor에서는 속이 빈(hollow) 정사각형으로 표시되며 색상 규칙은 Absolute와 동일하다.

한 Step이 Absolute 포인트와 Relative 포인트를 동시에 가지면, 둘을 연결하는 얇은 빨간 선이 표시된다. 이 절대/상대 분리 구조 덕분에 하나의 Phaser 안에서 "고정 기준값 + 그 위에 더해지는 변조"를 유연하게 조합할 수 있다.

Step 자체에는 값 레이어와 별도로 **시간·전환(Timing/Transition) 레이어**가 붙는다 — Width, Transition, Accel, Decel이 여기 속하며 4절에서 각각 설명한다.

출처:
- [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [Phaser Editor — help.malighting.com](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)

---

## 4. Phaser Editor 구조

Phaser Editor는 Step을 시각적으로 만들고 편집하는 창이다. 주요 구성 요소는 다음과 같다.

### 4.1 레이아웃 영역

- **2D Layout**: 팬(가로축)·틸트(세로축) 전체 범위를 나타내는 파란 격자. 선택된 픽스처는 노란 십자선(cross-hair)으로 표시되며, 필요시 강도·색상 정보를 포함한 색깔 원(beam)으로도 표시 가능.
- **1D Layout**: 스텝이 2개 이상인 속성마다 별도로 표시되는 작은 파란 격자. 세로 파란 선은 Phaser Speed 기준의 비트(beat)를 나타낸다.
- **Step Bar**: 화면 하단에 위치한 스텝 빠른 선택 도구. 스텝 상태(비어있음/선택 해제됨/선택됨)를 표시한다. "선택 해제된 스텝은 값은 갖고 있지만 선택되지 않아 스텝별 조정에 영향받지 않는다."
- **Attribute Buttons**: 타이틀바 아래 행에 위치, At Filter로 바로 연결. 노란 막대 = 활성 속성, 회색 막대 = 비활성 속성.

### 4.2 보기 모드(View Mode)

| 모드 | 설명 |
|---|---|
| Auto | 2D + 1D 레이아웃 동시 표시 |
| 2D | 팬/틸트 격자를 확대해 포지션 Phaser 작업에 집중 |
| 1D | 속성별 레이아웃을 개별적으로 표시 |
| Sheet | 스텝을 열(column), 레이어를 행(row)으로 배치한 스프레드시트 형태 |

### 4.3 편집 도구 (좌측 툴바)

1. Move Area — 화면 이동(팬)
2. Select — 단일/다중 스텝 선택(라쏘 포함)
3. Add Absolute — 절대값 스텝 삽입
4. Add Relative — 상대값 스텝 삽입
5. Move Point — 선택된 스텝의 위치 이동
6. Move Handles — 가속/감속(Accel/Decel) 곡선 조정
7. Change Size — 스텝 크기를 균등하게 스케일
8. Change Rotation — 선택 중심 기준 회전
9. Change Phase — 픽스처별 위상(Phase) 값 이동
10. Change Width — 스텝 지속시간 조정
11. Select Form — Rectangle(사각), Sawtooth(톱니), Sine(사인), Circle(원) 전환 형태 적용
12. Change Speed — Phaser 속도를 배수/분수로 조정
13. Select All Steps — 전체 선택 ↔ 단일 스텝 모드 전환

### 4.4 인코더 바(Encoder Toolbar)

현재 선택된 픽스처/스텝을 기준으로 다음 값을 직접 조작할 수 있다.

- **2D Bar 인코더**: MoveX/MoveY(위치), Size(크기), Handle(가속/감속 곡선), Rotate(회전), Aspect(가로세로 비율)
- **Phaser Bar 인코더**: Speed, Phase, Transition, Width, Measure

우측 버튼으로는 Reset spline, Delete steps, Cut/Copy/Paste(프로그래머 데이터), Mirror X/Y/Time, Swap XY axes, Flip positions, Reset Zoom 등 표준 작업을 수행한다.

출처:
- [Phaser Editor — help.malighting.com](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)

---

## 5. 핵심 파라미터 상세

### 5.1 Speed (속도)

Phaser가 스텝을 재생하는 전체 속도를 정의한다. grandMA3는 속도를 세 가지 단위 중 하나로 표시할 수 있다.

- **BPM** (Beats Per Minute, 분당 비트)
- **Hz** (초당 비트)
- **Seconds** (비트당 초)

Width, Measure 등 다른 시간 관련 파라미터는 모두 Speed가 정의하는 "1비트(beat)"를 기준 단위로 삼는다.

출처: [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)

### 5.2 Phase (위상)

Phase는 **각 픽스처(속성)가 Phaser 내에서 갖는 타이밍 오프셋**을 정의하며 **도(°) 단위**(0~360)로 표시된다. 픽스처들이 한 사이클 안에서 얼마나 빠르게 서로를 뒤따라가는지를 Phase 범위가 결정한다.

가장 대표적인 사용 패턴은 선택된 픽스처 그룹에 `Phase 0 Thru 360`을 적용하는 것 — 이렇게 하면 픽스처 수만큼 균등하게 위상이 분산되어 "파도(wave)" 효과가 만들어진다. (구체적인 원리는 6절 참고)

출처:
- [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [SPEED and PHASE for PHASER — MA Lighting Forum](https://forum.malighting.com/forum/thread/4267-speed-and-phase-for-phaser/)

### 5.3 Measure (측정 단위)

Measure는 Phaser가 한 번 순환(loop)하는 데 걸리는 전체 비트 수를 지정하는 선택적(optional) 파라미터다. MA Lighting 스태프(Andreas)는 포럼에서 Measure를 다음과 같이 설명한다.

> "the Measure layer is used as an overall scale when the phaser is running."
> (Measure 레이어는 Phaser가 재생되는 동안 전체를 스케일링하는 용도로 쓰인다.)

**동작 원리(실측 수치 예시)**:

1. Step 3개를 각각 Width 100%로 프로그램하면 합계는 300% = 60 BPM 기준 3초.
2. Measure를 4비트(4초)로 설정하면, 콘솔은 스케일 계수를 `4초 ÷ 3초 = 1.33`으로 계산해 각 스텝을 1.33배 늘려 재생 — 스텝 간 상대적인 비율은 그대로 유지된다.
3. 이후 Step 1의 Width를 100%→50%로 바꾸면 총합이 250%(2.5초)로 줄어들고, 콘솔은 계수를 `4초 ÷ 2.5초 = 1.6`으로 재계산해 다시 전체 스텝에 균일하게 적용한다.

핵심은 "Measure 레이어를 사용해도 각 스텝의 실제 Width 값 자체는 변경되지 않는다"는 점 — 스케일링은 재생 시점에만 적용된다.

출처: [Understanding Phaser Width and Measure mathematics — MA Lighting Forum](https://forum.malighting.com/forum/thread/68396-understanding-phaser-width-and-measure-mathematics/)

### 5.4 Width (폭)

Width는 **한 스텝의 시작부터 다음 스텝의 시작까지 걸리는 전체 시간**을 정의하며, Speed 레이어가 정의한 "1비트"에 대한 백분율(%)로 표시된다.

**예시 1 — Measure 계산 (5.3절과 동일 시나리오)**: Speed = 60 BPM(1비트 = 1초)일 때, Step Width = 100%이면 그 스텝은 1초간 지속된다. Measure를 2로 설정하면 매 Step이 1초가 되도록 스케일링된다는 예시가 공식 검색 요약에 등장한다.

**예시 2 — 8픽스처 체이스(chase) 공식**: MA Lighting 포럼에서 검증된 균등 체이스 계산법:

```
On(켜짐) 스텝의 Width  = (1 / 픽스처 수) × 100
Off(꺼짐) 스텝의 Width = ((픽스처 수 - 1) / 픽스처 수) × 100

8개 픽스처 예시:
  Step 1 (On)  Width = 100 / 8 = 12.5%
  Step 2 (Off) Width = 100 - 12.5 = 87.5%
  Phase = 0 Thru (360 - 360/8) = 0 Thru 315
```

이 공식은 "정확히 수학적으로 순수한(mathematically pure) 체이스 폼"을 만들기 위한 것으로, 각 픽스처가 정확히 자기 차례에만 켜지는 1-in-N 체이스를 구성한다.

**Lua를 이용한 동적 계산 예시** (선택된 픽스처 수에 따라 자동으로 Width를 계산):

```lua
Lua "SetVar( UserVars() , 'Step1Width' , 100/SelectionCount() )"
```

출처:
- [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [Width and phases in recipes — MA Lighting Forum](https://forum.malighting.com/forum/thread/7661-width-and-phases-in-recipes/)
- [Phaser Forms — MA Lighting Forum](https://forum.malighting.com/forum/thread/68474-phaser-forms/)

### 5.5 Transition / Accel(Acceleration) / Decel(Deceleration) — 흔히 부르는 "Attack/Decay"

Step 레이어는 값이 실제로 변화하는 구간과 그 곡선 형태를 다음 세 값으로 제어한다.

- **Transition**: 스텝 폭(Width) 중 값이 실제로 변화(전환)하는 데 사용되는 비율(%). 나머지 구간은 값이 고정(hold)된다.
- **Accel (Acceleration)**: 전환이 시작되는 부분의 부드러움을 제어. 범위는 대략 **-100% ~ 200%**.
- **Decel (Deceleration)**: 전환이 끝나는 부분의 급격함을 제어. 범위는 Accel과 동일하게 **-100% ~ 200%**.

공식 도움말은 다음과 같이 설명한다.

> "-100% 값은 부드러운 사인/코사인 형태의 전환을 만들고, 0%는 선형(linear) 전환을 만든다."

**"Attack/Decay"라는 용어에 대한 주의**: 이 태스크에서 요청한 "Attack/Decay"는 grandMA2 이펙트 엔진 시절 PWM류 Form(Form 13/14/15 "Phase 1/2/3")을 설명할 때 쓰이던 표현으로, "작은 Attack/Decay + 120도 위상차"로 묘사된다. grandMA3의 Phaser Editor/Encoder 상에서 이 개념에 대응하는 공식 파라미터명은 **Accel(Acceleration)과 Decel(Deceleration)**이다 — 즉 MA3에서는 "Attack"이 아니라 "Accel", "Decay"가 아니라 "Decel"이라는 명칭으로 동일한 역할(전환 곡선의 시작부/종료부 형태 제어)을 수행한다.

**실측 예시 — 사인파(Sinus) Dimmer Phaser 만들기** (공식 튜토리얼, 인코더 방식):

1. 픽스처 선택 후 Dimmer를 0으로 설정(`At 0 Please`)
2. Step 2를 생성하고 Full로 설정(`Full`)
3. Step 1, 2를 모두 선택
4. 인코더 계산기로 **Acceleration = -100** 설정
5. 인코더 계산기로 **Deceleration = -100** 설정
6. Phase 레이어에서 `0 Thru 360` 입력 → 선택된 모든 픽스처에 위상을 균등 분산
7. 결과: 모든 픽스처가 고르게 퍼진 사인파(Sinus) Phaser 완성 — 큐/프리셋으로 저장 가능

Phaser Editor를 사용하는 대안 방법도 있다: Select Form 도구로 "Sine wave" 버튼을 선택한 뒤, Edit Phase 도구에서 360 버튼을 눌러 파형 위에 픽스처를 균등 분산시킨다.

출처:
- [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [Phaser Editor — help.malighting.com](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)
- [Create a Sinus Dimmer Phaser — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser_create_dimmer.html)
- [Using grandMA3 Phasers to replicate grandMA2 Forms — ACT Entertainment](https://support.actentertainment.com/knowledgeBase/25504931) (PWM Form 13/14/15의 Attack/Decay + 120도 위상차 서술)

### 5.6 Grouping / Wings / Blocks (MAtricks)

Phaser 자체는 "선택 그리드(selection grid)에 올라간 항목"을 기준으로 동작한다. 예를 들어 서브픽스처 20개를 가진 그룹 픽스처 1개를 선택하면, Phaser는 이를 "픽스처 1개"로 인식하며 20개로 인식하지 않는다. Down 키를 눌러 서브픽스처 20개를 실제로 그리드에 펼쳐야 Phase 0..360 같은 값을 20개 단위로 적용할 수 있다.

이 "선택을 분할하는" 역할을 담당하는 도구가 **MAtricks**다. MAtricks는 크게 세 그룹의 속성으로 구성된다.

| 그룹 | 포함 속성 | 역할 |
|---|---|---|
| **Grid** | Axis, Block, Group, Wings, Width | 공간적 배치(분할 방식) 관리 |
| **Layers** | Fade From/To, Delay From/To, Speed From/To, **Phase From/To** | 시간적 속성 관리 — Phaser의 Phase와 직접 연동 |
| **Shuffle** | Shuffle 값(0~32,767) | 선택 순서를 무작위로 재배열 |

- **Blocks(블록)**: 선택된 픽스처를 작은 "덩어리(chunk)" 단위로 묶는다. 예: 2×2 블록으로 묶어 구역별로 동일한 룩을 반복.
- **Wings(윙)**: 선택을 지정한 윙 수만큼 나누고, 각 윙에서 서로 반대 방향으로 픽스처를 선택한다. **예시(10개 픽스처)**: 그리드 정보 없이 10개 픽스처(1~10번)를 단일 축(X축)에 선택한 상태에서 `XWings = 2`를 설정하면, 선택이 양 끝에서 시작해 중앙으로 향하는 두 그룹으로 나뉜다. `+`를 누르면 하이라이트된 선택이 중앙 쪽으로, `-`를 누르면 바깥쪽으로 이동한다.
- **Group(그룹)**: 스포츠 팀 배정처럼 동작 — 픽스처들이 지정된 그룹 수만큼 번갈아 배정되고 순환한다.

**Phaser와의 연동 방법**: 픽스처를 선택 → 원하는 MAtricks 값 설정(예: `XWing = 2`) → Phase 범위 적용(예: `0..360`)의 순서로 작업한다. MAtricks Editor 창을 열면 Groups/Blocks/Wings가 선택/Phaser에 미치는 영향을 시각적으로 조정할 수 있다.

**주의(버전 이력)**: 2020년 1월 포럼 기록에 따르면 당시 버전에서는 "Groups, Blocks, Wings가 Phaser Editor 안에는 아직 구현되어 있지 않다"(추후 지원 예정)는 MA Lighting 관리자(DanielK)의 답변이 있었다. 당시 권장 워크플로우는 "MAtricks로 먼저 분할 → Phaser Editor에서 Phase 값 적용"을 별도로 수행하는 것이었다. 이후 버전(2.x 계열)의 Phaser Editor 좌측 툴바에는 "Change Phase(위상 변경)" 도구가 정식으로 포함되어 있다(4.3절 참고).

또한 **자동 재계산이 필요하면 MAtricks 쪽에서 Phase 값을 함께 설정해야 한다** — 그렇지 않으면 그룹/윙/블록 파라미터를 바꿀 때마다 Phase 범위를 수동으로 다시 적용해야 한다는 점이 포럼 튜토리얼에서 지적된다.

**균등 3분할 시 주의점**: Phaser Editor에서 `0 Thru 360`을 적용하면 3개 픽스처에 대해 `0, 120, 240`으로 균등 계산되지만, MAtricks의 Phase 항목에 문자 그대로 `0 Thru 360`을 입력하면 `0, 180, 360`으로 계산되어 픽스처 1번과 3번이 동시에 점등되는 문제가 발생할 수 있다. 이를 피하려면 커맨드라인에서 `At Phase Percent 0 Thru 360` 또는 `At Phase Percent 0 Thru -360` 형태로 입력해 균등 분산을 명시적으로 강제해야 한다.

출처:
- [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [MAtricks and Shuffle — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/matricks.html)
- [MAtricks Wings — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/matricks_wings.html)
- [Phaser Groups — MA Lighting Forum](https://forum.malighting.com/forum/thread/3849-phaser-groups/)
- [Phaser basics — MA Lighting Forum](https://forum.malighting.com/forum/thread/68294-phaser-basics/)
- [Width and phases in recipes — MA Lighting Forum](https://forum.malighting.com/forum/thread/7661-width-and-phases-in-recipes/)

### 5.7 Speed Group / Speed Master (SpeedMaster)

grandMA3에는 **16개의 Speed Master**가 존재하며, 각각 **0~225 BPM** 범위의 값을 가진다. Speed Master는 여러 오브젝트의 속도를 동기화하는 마스터 채널로, 다음 대상에 할당할 수 있다.

- Executor, Special Executor
- Sequence, Cue, Cue Part
- Attribute, Preset, Generator
- **Phaser**

**동작 규칙**:

- Speed Master를 Phaser에 직접 할당할 수도 있지만, 일반적으로는 **Sequence에 할당**한다 — 그러면 해당 Sequence 안의 모든 Phaser가 그 Speed Master의 속도로 재생된다.
- **우선순위**: Phaser 레벨에 별도로 지정된 Speed Master는 항상 우선 적용되며, Sequence 레벨의 Speed Master나 Speed 함수는 이미 자체 Speed Master가 지정된 Phaser에는 영향을 주지 못한다.
- Attribute에 할당된 경우, 해당 Attribute는 활성 큐/시퀀스의 Speed Master에 항상 동기화된 상태를 유지한다. 단, 동일 마스터가 Sequence/Cue Part와 Attribute 양쪽에 할당되어 있으면 업데이트·저장 시 Attribute 쪽 할당이 제거된다.
- **Speed Master #16은 특수 목적의 "BPM 마스터"**로, 오디오 입력에 반응해 감지된 BPM을 자동으로 마스터 속도로 채택한다.
- Speed Master는 표시 단위로 BPM, Hz, Seconds 중 선택 가능하다.

**커맨드라인 문법 (SpeedMaster 키워드)**:

```
전체 명령: SpeedMaster   (약어: Speedm)

문법:
  (Attribute ["속성명" 또는 속성번호]) At SpeedMaster [번호]

예시 1 — 선택에 SpeedMaster 적용:
  User name[Fixture]>SpeedMaster

예시 2 — Pan 속성만 Speed Master 1번에 연결:
  User name[Fixture]>Attribute "Pan" At SpeedMaster 1
```

이 키워드를 이용하면 속성 단위로 서로 다른 Speed Master에 개별 연결할 수 있어, 예를 들어 Pan/Tilt는 느린 마스터에, Dimmer는 빠른 마스터에 동기화하는 식의 세밀한 제어가 가능하다.

출처:
- [Speed Masters — help.malighting.com](https://help.malighting.com/grandMA3/2.4/HTML/masters_speed.html)
- [SpeedMaster Keyword — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/keyword_speedmaster.html)
- [Applying Speed function to executor vs Master function with Speed Master — MA Lighting Forum](https://forum.malighting.com/forum/thread/69240-applying-speed-function-to-executor-versus-applying-master-function-with-a-speed/)
- [No way to use Speed Masters in Shapes or Phaser Recipes? — MA Lighting Forum](https://forum.malighting.com/forum/thread/69915-no-way-to-use-speed-masters-in-shapes-or-phaser-recipes/)

---

## 6. Phase 오프셋으로 파도(wave) 효과 만들기

Phase 값을 픽스처 선택 전체에 걸쳐 **0에서 360도까지 분산**시키면, 동일한 파형(사인파, 램프 등)이 픽스처마다 서로 다른 시점에서 시작되어 시각적으로 "파도(wave)"처럼 보이는 효과가 만들어진다. 원리는 다음과 같다.

1. 모든 픽스처가 **동일한 Step 구조(값·Width·Transition·Accel/Decel)** 를 공유한다.
2. 각 픽스처는 **서로 다른 Phase(위상, 0~360도)** 값을 가진다 — Phase는 "이 픽스처가 파형의 어느 지점에서 재생을 시작하는가"를 결정한다.
3. Phase가 균등하게 분산되어 있으면(예: 5개 픽스처 → 0°, 72°, 144°, 216°, 288°), 파형이 마치 픽스처 배열을 따라 흘러가는 것처럼 보인다.

**적용 방법 두 가지**:

- **Phaser Editor에서**: Select Form 도구로 원하는 파형(Sine 등)을 선택한 뒤, Edit Phase 도구로 전환하고 "360" 버튼을 눌러 선택된 픽스처 전체에 위상을 자동으로 균등 분산시킨다.
- **커맨드라인/인코더에서**: Phase 레이어 인코더나 커맨드라인에 `Phase 0 Thru 360`(또는 균등 분산이 필요하면 `At Phase Percent 0 Thru 360`)을 입력한다.

**실측 수치 예시 — 픽스처 개수별 위상 분산**:

| 픽스처 수 | Phaser Editor `0 Thru 360` 적용 시 계산값 | 비고 |
|---|---|---|
| 3개 | 0°, 120°, 240° | 균등 분산(3등분) |
| 5개 | 0°, 72°, 144°, 216°, 288° | 360 ÷ 5 = 72°씩 균등 |
| 8개 | 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315° | 360 ÷ 8 = 45°씩 균등 |

주의: MAtricks의 Phase 필드에 `0 Thru 360`을 **문자 그대로** 입력하면(끝값 360을 포함해서 나눔) 위 계산과 다르게 동작할 수 있다 — 3개 픽스처 예시에서 `0, 180, 360`으로 계산되어 1번과 3번 픽스처가 동시에 점등되는 문제가 보고된 바 있다(5.6절 참고). 균등 분산을 명시적으로 강제하려면 `At Phase Percent 0 Thru 360` 형태의 커맨드라인 입력을 사용한다.

Phase 분산과 Width/그룹핑을 조합하면 단순 웨이브 외에도 다양한 변형이 가능하다.

- **8픽스처 체이스** (5.4절 공식 재인용): Step 1(On) Width = 12.5%, Step 2(Off) Width = 87.5%, `Phase = 0 Thru 315`(= 0 Thru (360 - 360/8)) — 각 픽스처가 정확히 순서대로 1개씩 점등되는 체이스.
- **3-그룹 체이스** (Width 방식의 대안): Step Width를 50%/100% 같은 고정값으로 두고, MAtricks Group을 3으로 설정한 뒤 `Phase 0 Thru 360`을 적용하면, 복잡한 계산 없이도 3개 단위로 균등한 1-in-3 체이스를 만들 수 있다.

출처:
- [Phasers — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [Phaser Editor — help.malighting.com](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)
- [Create a Sinus Dimmer Phaser — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser_create_dimmer.html)
- [SPEED and PHASE for PHASER — MA Lighting Forum](https://forum.malighting.com/forum/thread/4267-speed-and-phase-for-phaser/)
- [Width and phases in recipes — MA Lighting Forum](https://forum.malighting.com/forum/thread/7661-width-and-phases-in-recipes/)
- [MAtricks and Shuffle — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/matricks.html)

---

## 7. 종합 예시 — 사인파 Dimmer Wave Phaser (전체 절차)

앞서 5.5절과 6절에서 다룬 내용을 하나의 실전 절차로 종합하면 다음과 같다.

1. 픽스처 그룹 선택 (예: `Fixture Thru Please`)
2. Dimmer 0%인 Step 1 생성: `At 0 Please`
3. Dimmer 100%(Full)인 Step 2 생성: `Full`
4. Step 1·2를 모두 선택
5. **Acceleration = -100**, **Decel = -100** 설정 → 사인/코사인 형태의 부드러운 전환 곡선 확보
6. Phase 레이어에 `0 Thru 360` 입력 → 픽스처 수만큼 위상을 균등 분산
7. (선택) Speed를 BPM 단위로 지정 — 예: 60 BPM = 1비트/초
8. (선택) Measure를 지정해 전체 루프 길이를 원하는 마디 수로 스케일링
9. 결과를 Preset이나 Cue로 저장

이 절차 하나로 "Speed(전체 속도) · Phase(픽스처 간 위상차) · Width/Transition(전환 구간 비율) · Accel/Decel(전환 곡선 형태) · Measure(전체 루프 길이 스케일)"의 5개 핵심 파라미터가 모두 실전에서 어떻게 맞물리는지 확인할 수 있다.

출처:
- [Create a Sinus Dimmer Phaser — help.malighting.com](https://help.malighting.com/grandMA3/2.0/HTML/phaser_create_dimmer.html)
- [Phaser Editor — help.malighting.com](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)

---

## 8. 전체 출처 목록

### 공식 도움말 (help.malighting.com)

- [Phasers](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [Phaser Editor](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)
- [Create a Sinus Dimmer Phaser](https://help.malighting.com/grandMA3/2.0/HTML/phaser_create_dimmer.html)
- [Speed Masters](https://help.malighting.com/grandMA3/2.4/HTML/masters_speed.html)
- [SpeedMaster Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_speedmaster.html)
- [MAtricks and Shuffle](https://help.malighting.com/grandMA3/2.0/HTML/matricks.html)
- [MAtricks Wings](https://help.malighting.com/grandMA3/2.0/HTML/matricks_wings.html)

### MA Lighting 공식 포럼

- [Phaser basics](https://forum.malighting.com/forum/thread/68294-phaser-basics/)
- [Understanding Phaser Width and Measure mathematics](https://forum.malighting.com/forum/thread/68396-understanding-phaser-width-and-measure-mathematics/)
- [Width and phases in recipes](https://forum.malighting.com/forum/thread/7661-width-and-phases-in-recipes/)
- [SPEED and PHASE for PHASER](https://forum.malighting.com/forum/thread/4267-speed-and-phase-for-phaser/)
- [Phaser Groups](https://forum.malighting.com/forum/thread/3849-phaser-groups/)
- [Phaser Forms](https://forum.malighting.com/forum/thread/68474-phaser-forms/)
- [Phaser effect width workflow](https://forum.malighting.com/forum/thread/5147-phaser-effect-width-workflow/)
- [MA3 Phaser vs MA2 Effect](https://forum.malighting.com/forum/thread/68774-ma3-phaser-vs-ma2-effect/)
- [Applying Speed function to executor versus applying Master function with a Speed Master object?](https://forum.malighting.com/forum/thread/69240-applying-speed-function-to-executor-versus-applying-master-function-with-a-speed/)
- [No way to use Speed Masters in Shapes or Phaser Recipes?](https://forum.malighting.com/forum/thread/69915-no-way-to-use-speed-masters-in-shapes-or-phaser-recipes/)

### 서드파티 자료

- [Using grandMA3 Phasers to replicate grandMA2 Forms — ACT Entertainment Customer Hub](https://support.actentertainment.com/knowledgeBase/25504931)

---

## 9. 리서치 한계 및 후속 확인 필요 항목

- **"Attack/Decay"라는 명칭 자체**는 grandMA3 공식 UI/도움말에서 독립된 파라미터로 확인되지 않았다 — 공식 명칭은 Accel(Acceleration)/Decel(Deceleration)이며, 본 문서 5.5절에서 이 대응 관계를 명시했다. grandMA3 콘솔의 실제 UI 라벨을 라이브로 재확인하는 것이 이상적이나, 이 리서치 태스크는 웹 조사로 한정되어 라이브 콘솔 검증은 수행하지 않았다.
- **버전 차이**: 인용한 도움말 페이지는 grandMA3 2.0/2.2/2.4 버전이 섞여 있다. Groups/Blocks/Wings의 Phaser Editor 내 지원 여부는 2020년 이후 버전업으로 개선된 것으로 보이나(5.6절), 정확한 도입 버전 번호는 포럼 스레드에서 명시적으로 확인되지 않았다.
- ACT Entertainment 문서는 검색 스니펫으로만 일부 확인되었고, 본문 전체를 web-fetch로 가져오는 데는 실패했다(빈 페이지 반환) — 인용은 검색 결과 요약에 근거한다.
