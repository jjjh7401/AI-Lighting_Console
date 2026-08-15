# grandMA3 Pan/Tilt(포지션) 이펙트 — 페이저(Phaser) 리서치

리서치 태스크 B: grandMA3 공식 문서·포럼·튜토리얼을 웹 검색하여 대표적인 움직임(Pan/Tilt) 이펙트 6종 이상의
정확한 제작 절차, 페이저 에디터 사용법, 커맨드라인 문법을 정리한다.

---

## 0. 페이저(Phaser) 기본 개념

grandMA3의 이펙트 엔진은 **Phaser**라고 부른다. 큐(cue)나 프리셋(preset)이 "1개의 스텝(step)"만 가지는
정적인 값인 것과 달리, 페이저는 **2개 이상의 스텝**을 순서대로 재생·반복(loop)하면서 pan/tilt·컬러·줌 등
속성 값을 동적으로 바꾼다. 이 값 집합을 사용하는 오브젝트를 "multi-step"이라고 부른다.

### 핵심 레이어(파라미터)

| 레이어 | 의미 |
|---|---|
| **Speed(Rate)** | 페이저가 루프를 도는 속도. BPM(분당 비트) · Hz(초당 비트) · Seconds(비트당 초) 세 단위로 표시 가능. 60 BPM·60 스텝이면 1바퀴가 1분 |
| **Phase** | 선택된 각 픽스처가 루프 사이클 내 어느 지점에서 출발할지의 시간 오프셋. 0~360도로 표시 |
| **Width** | 한 스텝의 시작부터 다음 스텝 시작까지 걸리는 시간(비트 대비 %). 기본값 100%면 모든 스텝이 균등 |
| **Transition** | 스텝의 Width 중 실제 값이 페이드(전환)되는 비율(%) |
| **Accel/Decel** | 전환 곡선. 0% = 선형(linear), −100% = 완만한 사인/코사인 곡선, 양수 = 급격한 전환 |
| **Measure** | 루프가 몇 비트마다 반복될지(선택 항목) |

### 절대(Absolute) vs 상대(Relative) 값

페이저의 스텝 값은 **절대값**(예: pan/tilt를 특정 좌표로 고정)과 **상대값**(예: 현재 위치에서 ±오프셋)을
동시에 가질 수 있다. 페이저 에디터에서 절대 스텝은 채워진 사각형(노랑/시안), 상대 스텝은 빈 사각형으로
표시되며, 상대-절대 짝은 빨간 선으로 연결되어 보인다.

- **절대 페이저**: 항상 지정된 절대 좌표로 픽스처를 이동시킨다(예: "무조건 이 원형 경로를 그려라").
- **상대 페이저**: 현재 프로그래머/프리셋에 있는 절대 위치(Base Position)를 기준으로 오프셋만 더한다.
  같은 상대 페이저를 서로 다른 절대 위치 프리셋과 조합하면, 무대 어디에 있든 그 자리를 중심으로
  같은 모양(원, 8자 등)을 그리게 할 수 있다 — **"중심 위치(center) + 상대 오프셋"** 워크플로우의 핵심.

출처: [Phasers (grandMA3 2.0 Help)](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html), [Phasers QSG](https://help.malighting.com/grandMA3/2.0/HTML/qsg_phasers.html)

---

## 1. 페이저 에디터(Phaser Editor) — 2D 뷰 사용법

포지션(Pan/Tilt) 페이저를 만들 때 핵심 도구는 **Phaser Editor**의 2D 뷰다.

### 레이아웃

- **2D 레이아웃**: 파란색 그리드가 pan 범위(가로)·tilt 범위(세로) 전체를 나타낸다. 픽스처는 노란
  십자선(crosshair)으로, 빔은 활성화 시 색이 채워진 원으로 표시된다.
- **1D 레이아웃**: 각 속성(Attribute)별로 스텝을 세로 비트 마커로 표시 — 스텝이 2개 이상인 속성만 보임.
- 표시 규칙: 채워진 사각형 = 절대 포인트, 빈 사각형 = 상대 포인트, 빨간 선 = 상대-절대 연결,
  시안 = 프리셋 값, 노랑 = 프로그래머 값, 초록 선 = 픽스처 이동 경로(움직임 궤적) 표시.

### 뷰 모드

| 모드 | 설명 |
|---|---|
| Auto | 2D + 1D 결합 표시 |
| 2D | 포지션 중심의 확대 레이아웃 |
| 1D | 전체 폭 속성 표시(Value/Transition 토글) |
| Sheet | 스프레드시트 형식 + 1D 레이아웃 내장 |

### 좌측 툴바(주요 도구)

1. **Move Area** — 좌표계 이동(팬)
2. **Select** — 단일/복수 스텝 선택
3. **Add Absolute (A+)** — 절대값 스텝 생성 (그리드를 클릭해 고정 좌표 지정)
4. **Add Relative (R+)** — 상대값 스텝 생성
5. **Move Point** — 선택한 스텝 위치 이동
6. **Move Handles** — 가속/감속 곡선 조정
7. **Change Size** — 스텝들을 균일하게 스케일
8. **Change Rotation** — 패턴 회전
9. **Change Phase** — 픽스처별로 위상(phase)을 독립적으로 분배
10. **Change Width** — 스텝 타이밍 비율 조정
11. **Select Form** — 사각형(Rectangle)·톱니(Sawtooth)·사인(Sine)·원(Circle) 등 프리셋 파형 적용.
    이 버튼들은 실제로는 Transition·Width·Accel·Decel 레이어에 미리 정해진 값을 넣어주는 단축키일 뿐이므로,
    이 4개 레이어를 직접 편집하면 어떤 파형도 자유롭게 만들 수 있다.
12. **Change Speed** — 재생 속도 변경(Loop 배수/Fixture 배수)
13. **Select All Steps** — 스텝 일괄 선택 토글

### 상단/하단 바

- **Attribute Control Bar**: 페이저에 포함된 각 속성(Pan/Tilt/Dimmer 등) 버튼 — 노랑 강조 = 편집 활성, 회색 = 비활성.
- **Step Bar(하단)**: 스텝 탐색 — 빈 스텝은 어둡게, 값이 있지만 미선택은 회색, 선택+활성은 노랑.
- **2D 인코더 바**: MoveX, MoveY, Size, Handle, Rotate, Aspect, Select Step.
- **Phaser 인코더 바**: Speed, Phase, Transition, Width, Measure.

출처: [Phaser Editor (grandMA3 2.2 Help)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)

---

## 2. 이펙트 6종 이상 — 단계별 제작 레시피

### ① 서클(Circle) — 절대(Absolute) 원형 페이저

가장 기본적인 포지션 페이저. 항상 지정한 절대 좌표로 원을 그린다.

1. 무빙라이트를 패치하고, 필요한 픽스처를 선택한 뒤 딤머를 Full로 올린다.
2. Phaser Editor 창을 연다 — 흰색 빔이 파란 2D 그리드 중앙에 표시된다.
3. **A+(Add Absolute)** 버튼을 탭한 뒤, 파란 그리드의 한 지점(예: 중앙 아래쪽)을 클릭해 첫 번째 절대
   포지션 스텝을 만든다.
4. 첫 지점에서 수직으로 약 90도 떨어진 지점을 두 번째로 클릭한다 — 이때 가로선을 가로질러 클릭하면
   8자(figure-8) 패턴이 생기므로 주의해서 피한다.
5. **Select All Steps**로 두 스텝을 모두 선택한 뒤 **Move Handle** 도구를 활성화하고, 한쪽 포인트를
   가로 방향으로 드래그해 매끄러운 원형 궤적이 나올 때까지 조정한다.
6. **Change Phase** 버튼을 탭하고, 우측 메뉴에서 **360**을 선택 — 선택된 모든 픽스처가 원형 궤적을 따라
   균등하게 위상 분산되어 배치된다.
7. 완성한 페이저를 프리셋으로 저장(Store)한다. 속도는 기본 60 BPM보다 느린 **20 BPM** 정도가 포지션
   페이저에는 자연스럽다는 것이 문서의 권장 사항이다.

출처: [Create a Circle Phaser (grandMA3 2.2 Help)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_create_circle.html)

---

### ② 서클 어라운드 포지션 프리셋 — 상대(Relative) 원 + 중심 위치

"중심 위치(center) + 상대 오프셋" 조합의 대표 예시. 무대 어디를 중심으로 잡아도 동일한 원을 그리게 한다.

1. 무빙라이트가 있는 픽스처 전체를 선택한다.
2. Phaser Editor에서 좌측 메뉴의 **R+(상대 모드)**를 탭한다.
3. 파란 2D 그리드의 중앙 바로 위를 클릭(첫 포인트), 중앙 바로 아래를 클릭(두 번째 포인트) — 이 두 점이
   원의 기준이 된다.
4. **Circle** 폼(Select Form) 버튼을 눌러 원형으로 만든다.
5. **Change Phase** → 우측 메뉴에서 **360** 선택 → 픽스처들이 원 둘레에 균등 분산된다.
6. 이 상대 원형 페이저를 프리셋으로 저장한다.
7. 실제 사용 시: 픽스처 선택 → 딤머 프리셋(Open, Full) 적용 → **포지션 프리셋(예: "Center", 다운스테이지
   중앙)** 적용 → 위에서 만든 상대 원형 페이저 프리셋 적용 → 이 조합을 새 프리셋/큐로 저장.
8. 결과: 픽스처들이 "다운스테이지 중앙 위치를 중심으로 원을 그리며" 움직인다. 절대 위치 프리셋만
   바꾸면(예: "Center" → "Stage Left") 같은 원 모양이 다른 중심점으로 그대로 이동한다.

출처: [Create a Circle Phaser Around a Position Preset (grandMA3 2.2 Help)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_create_circle_preset.html)

---

### ③ 피겨-8(Figure-8) — 위상 오프셋 + 미러(Mirror) 변환

공식 문서에 "Figure-8" 전용 페이지는 없으나, ①의 "가로선을 가로질러 클릭하면 8자가 된다"는 경고와
포럼의 대칭 이펙트 기법을 조합하면 8자 패턴을 만들 수 있다.

1. ①의 서클 레시피 1~3단계를 반복하되, 이번에는 **의도적으로** 두 절대 포인트를 수평 중심선을
   가로지르도록 배치한다(교차 지점이 생기면 궤적이 8자 형태가 된다).
2. 좌우로 대칭인 픽스처 선택(예: 무대를 가로지르는 라인 어레이)에 대해 반대 방향으로 움직이게 하려면:
   - MAtricks(선택 매트릭스)에서 **XWings를 2**로 설정 — 선택을 좌/우 두 그룹으로 나눈다.
   - 선택이 "좌우 대칭"이 되도록 정렬되어 있어야 한다.
   - **Transform → Mirror**를 적용해 한쪽 그룹의 움직임을 반전시킨다.
3. **Phase to X**(MAtricks의 위상 오프셋)를 0이 아닌 값(예: 180도)으로 설정하면, 두 그룹이 같은 순간에
   같은 동작을 하지 않고 서로 반대 지점에서 출발 — 결과적으로 서로 교차하며 8자를 그리거나, 좌/우로
   갈라지는 대칭 웨이브를 만든다.
4. MA2의 "Sin" 폼(Pan)과 "Cos" 폼(Tilt)처럼 pan과 tilt의 위상을 90도 어긋나게 주는 것이 8자·원형 패턴의
   수학적 기본 원리다 — grandMA3에서는 pan 스텝과 tilt 스텝을 별도로 만들고 각각 다른 Phase 값을
   주는 방식으로 재현한다.

출처: [How to opose fixtures (MA Lighting Forum)](https://forum.malighting.com/forum/thread/9188-how-to-opose-fixtures/), [Is it even possible to create a true circle form with selective pan/tilt presets? (MA Lighting Forum)](https://forum.malighting.com/forum/thread/68858-is-it-even-possible-to-create-a-true-circle-form-with-selective-pan-tilt-presets/), [Create a Circle Phaser](https://help.malighting.com/grandMA3/2.2/HTML/phaser_create_circle.html)

---

### ④ 웨이브(Wave) / 틸트 스윕(Tilt Sweep) — 무대를 가로지르는 순차 이동

여러 픽스처가 순서대로 이어받듯 무대를 가로질러 움직이는(walk across stage) 웨이브 효과.

1. 무대에 순서대로 배치된 픽스처를 순번대로 선택한다(예: Fixture 301 thru 308 — 선택 순서가 곧
   위상 분배 순서가 된다).
2. 각 픽스처의 Tilt(또는 Pan) 속성에 2개 이상의 스텝을 만든다(예: 위쪽 각도 스텝, 아래쪽 각도 스텝).
3. **Phase**를 **0 thru 360**으로 걸어준다 — 이렇게 하면 이펙트가 선택된 픽스처 전체에 균등하게 퍼지고,
   선택 순서가 순차적이라면(예: 301→308) 이펙트가 무대를 가로질러 "걸어가는(walk)" 것처럼 보인다.
4. Phase를 **360으로 고정**하면 360이 "선택 범위의 시작과 끝을 자동으로 그 축의 extent에 바인딩"하므로
   정상파(standing wave)처럼 보이는 웨이브 형태가 된다.
5. Width를 조정해 각 스텝이 차지하는 시간 비율을 바꾸면 웨이브의 "폭"과 체공 시간이 달라진다 — 딤머가
   저장된 스텝의 Width를 조정해 원하는 체이스(chase) 느낌을 만든다는 것이 포럼의 팁이다.
6. 랜덤한 느낌을 원하면 MAtricks 창의 **Shuffle** 키로 픽스처의 위상 배치 순서를 섞을 수 있다.

출처: [Phaser Forms (MA Lighting Forum)](https://forum.malighting.com/forum/thread/68474-phaser-forms/), [Chaser Phaser (MA Lighting Forum)](https://forum.malighting.com/forum/thread/8499-chaser-phaser/), [Grid Selection - MaTricks - Phaser (MA Lighting Forum)](https://forum.malighting.com/forum/thread/69260-grid-selection-matricks-phaser/)

---

### ⑤ 팬 스윕(Pan Sweep)

웨이브(④)와 원리는 동일하되 **Pan** 속성 한 축만 사용해 좌우로 쓸어가는 단순한 스윕. 조명 감독들이
"라인 스윕"이라고 부르는 형태다.

1. 무대 한 라인에 배치된 픽스처들을 선택한다.
2. Pan 속성에 2개의 절대 스텝(좌측 끝값 / 우측 끝값)을 만든다 — Add Absolute로 그리드 좌/우 끝을
   클릭하거나, 인코더로 직접 pan 값을 입력한다.
3. **Change Phase → 0 thru 360**을 적용해 선택 순서대로 위상을 분산시키면, 팬이 좌→우로 흐르는
   스윕처럼 보인다. 위상을 주지 않고 전부 Phase 0으로 두면 전체 픽스처가 동시에 같은 방향으로만
   움직이는 "동기화된 스윕"이 된다 — 어떤 느낌을 원하는지에 따라 선택한다.
4. Speed(BPM)를 낮추면 느린 스윕, 높이면 빠른 스캔 효과가 된다.
5. Select Form에서 **Sawtooth**를 선택하면 한쪽 끝에서 다른 쪽 끝으로 급격히 리셋되는 "스캔" 형태,
   **Sine**을 선택하면 부드럽게 왕복하는 형태가 된다 — 이 버튼들은 Transition/Width/Accel/Decel의
   조합을 자동으로 세팅해주는 단축키다.

출처: [Phaser Editor Form commands (MA Lighting Forum)](https://forum.malighting.com/forum/thread/8333-phaser-editor-form-commands/), [Syntax to change from Sawtooth to Sin wave when editing a phaser? (MA Lighting Forum)](https://forum.malighting.com/forum/thread/68488-syntax-to-change-from-sawtooth-to-sin-wave-when-editing-a-phaser/)

---

### ⑥ 발리후(Ballyhoo) — 빠른 랜덤 8자형 움직임

전통적으로 "발리후"는 스팟 오퍼레이터가 조명을 빠르게 무작위 8자 패턴으로 흔들어 에너지를 만드는
연출을 뜻하며, 콘솔에 내장 이펙트가 생기면서 버튼 하나로 재현 가능해졌다.

1. 픽스처를 선택하고, Pan/Tilt 속성에 여러 개의 스텝(보통 3~6개, 무작위 좌표)을 절대값으로 배치해
   불규칙한 이동 경로를 만든다.
2. **Speed**를 상대적으로 빠르게(예: 60~120 BPM 대) 설정 — 발리후 특유의 빠른 흔들림을 위해서다.
3. **Change Phase**로 픽스처마다 다른 시작 위상을 준다 — 모든 픽스처가 동일한 타이밍에 동일한 지점에
   있지 않도록 오프셋을 흩어놓는 것이 "자연스러운 발리후 플로우"를 만드는 핵심이라는 것이 업계
   튜토리얼의 공통된 조언이다.
4. Size(경로의 크기)와 Speed를 조정해 무대·객석 규모에 맞는 스윙 폭을 맞춘다.
5. 딤머를 함께 페이저에 넣어 깜빡임(strobe/flash)을 추가하거나, 컬러 체이스를 겹쳐 에너지를 더 끌어올릴
   수 있다.
6. 주의점(포럼 보고 사례): 발리후류 이펙트가 재생 중일 때 다음 큐로 넘어가면, 이펙트가 정지된 위상
   지점에 따라 픽스처 위치가 순간적으로 튀는 현상이 있을 수 있다 — Sync/Stomp 레이어로 완화 가능.

출처: [Making a Good Ballyhoo Great (PLSN)](https://plsn.com/blogs/tips-tricks/making-a-good-ballyhoo-great/), [Ballyhoo (Advanced Staging Productions)](https://advancedstaging.com/ballyhoo/), [Phaser speed change in cue stack (MA Lighting Forum)](https://forum.malighting.com/forum/thread/69118-phaser-speed-change-in-cue-stack/)

---

### ⑦ 플라이아웃(Fly-out) — 두 지점 간 순차 발사(waterfall)

한 프리셋 위치에서 다른 프리셋 위치로 "쏘아 보내는" 듯한 효과. 여러 픽스처가 순차적으로 발사되면
폭죽처럼 보인다("beam fly-out effects"). 하나의 페이저 안에서 A→B, C→D처럼 여러 구간을 이어 붙일 수도
있다.

1. 시작 위치(포지션 프리셋 A)와 도착 위치(포지션 프리셋 B)를 미리 만들어 둔다.
2. Phaser Editor에서 Pan/Tilt에 절대 스텝 2개를 A, B 좌표로 각각 배치한다.
3. **Width**와 **Transition**을 조정해 A→B로 튀는 순간의 체공/전환 속도를 정한다 — 짧은 Transition +
   급격한 Accel/Decel 조합이 "쏘아 보내는" 듯한 느낌을 만든다.
4. **Change Phase**로 픽스처마다 발사 타이밍을 다르게 주면(예: 왼쪽부터 순서대로), 여러 대가 순차적으로
   튀어나가는 "waterfall" 플라이아웃이 된다.
5. **상대(Relative) 모드**로 전환하면(R+), 현재 픽스처의 위치를 기준으로 오프셋만큼 튀는 형태를 만들
   수 있다 — 이 경우 절대 베이스 포지션과 조합해 "현재 픽스처가 있는 자리에서 위로 확 튀었다가
   돌아오는" 워터폴형 플라이아웃을 손쉽게 재현할 수 있다(서드파티 플러그인 FlyoutMAker가 이 워크플로우를
   GUI로 단순화해 제공).
6. 딤머(Dimmer)를 같은 페이저에 태워 어택/디케이(attack/decay) 타이밍을 조정하면 "빔이 번쩍이며
   튀어나가는" 느낌을 더할 수 있다.
7. 하나의 페이저 안에 A→B 스텝 세트와 C→D 스텝 세트를 이어 붙이면, 한 번의 재생으로 두 구간을
   연속으로 플라이아웃시킬 수 있다.

출처: [Difficulty replicating Flyout Effect (Phaser) — Following MA/Lightpower Webinar (MA Lighting Forum)](https://forum.malighting.com/forum/thread/8198-difficulty-replicating-flyout-effect-phaser-following-ma-lightpower-webinar/), [Flyout Phaser based on Position Presets (MA Lighting Forum)](https://forum.malighting.com/forum/thread/68445-flyout-phaser-based-on-position-presets/), [FlyoutMAker (MA.tools)](https://ma.tools/Phasers/FlyoutMAker/), [position from phaser (MA Lighting Forum)](https://forum.malighting.com/forum/thread/5240-position-from-phaser/)

---

## 3. 커맨드라인(Command Line) 문법

grandMA3는 GUI(페이저 에디터)뿐 아니라 커맨드라인으로도 페이저 속성을 직접 편집할 수 있다.

### 기본 문법 — `Attribute "..." at <레이어> <값>`

```text
Attribute "Pan" at Phase 180
Attribute "Pan" at Width 10
Attribute "Pan" at Speed 180
Attribute "Pan" at Relative 10
Attribute "Pan" at Fade 10
Attribute "Pan" at Delay 10
Attribute "Pan" at Accel 10
Attribute "Pan" at Decel 10
Attribute "Pan" at Transition 10
```

- `at` 뒤에 오는 키워드가 곧 "레이어 이름"이다: `Phase`, `Speed`(=Rate), `Width`, `Transition`,
  `Accel`, `Decel`, `Relative`, `Fade`, `Delay`.
- 특정 속성 없이 레이어만 바꾸고 싶을 때는 먼저 같은 키워드(`Relative`, `Fade`, `Transition` 등)로
  레이어를 선택한 뒤 값을 적용하는 방식도 동작한다(버전 1.2.0.2 기준 확인됨).

### StepCreator를 통한 스텝 속성 지정(더 안정적인 대안)

```text
Set StepCreator Property "Transition" "100"
```

`Transition`, `Width`, `Phase`, `Curve` 속성에 대해 동작하며, 문서 작성 시점 기준 `Repeat` 속성은
아직 구현되지 않았다고 포럼에 보고되어 있다.

### 스텝 삭제

```text
Delete Step 3
```

### 페이즈 분배(균등 배분) — 360도 위상 예시

원형/웨이브 계열 이펙트에서 픽스처 선택 전체에 위상을 균등 분산시킬 때 자주 쓰는 개념:

```text
Attribute "Pan" at Phase 0 thru 360
Attribute "Tilt" at Phase 0 thru 360
```

`Phase 0 thru 360`은 선택된 픽스처 수만큼 0~360도 범위를 균등하게 나눠 각 픽스처에 순서대로
배정한다 — 이것이 ①·②·④·⑤ 레시피에서 "Change Phase → 360"으로 설명한 GUI 동작의 커맨드라인
등가물이다.

> 참고: 페이저 자체를 생성하는(스텝을 추가하는) 동작은 대부분 GUI 드래그·클릭 또는 **Step 키를 누른
> 채 프리셋을 순서대로 탭**하는 방식으로 이뤄지며(새 프리셋에 이전 스텝에서 이미 쓰인 속성이 포함되어
> 있을 때만 새 스텝이 생성됨), 커맨드라인 문법은 주로 "이미 만들어진 스텝의 레이어 값을 미세 조정"하는
> 데 쓰인다. 완전한 스텝 생성 문법(예: `Store Phaser 1 Step 1`류)은 검색된 자료에서 명확히 문서화되지
> 않았으며, 이는 이번 리서치의 확인되지 않은 부분(gap)으로 남긴다.

출처: [Edit Phasers in Commandline (MA Lighting Forum)](https://forum.malighting.com/forum/thread/4468-edit-phasers-in-commandline/), [Set Attribute of Phaser via Command Line (MA Lighting Forum)](https://forum.malighting.com/forum/thread/9180-set-attribute-of-phaser-via-command-line/), [Phaser related syntax (MA Lighting Forum)](https://forum.malighting.com/forum/thread/68274-phaser-related-syntax/), [Understanding Phaser Width and Measure mathematics (MA Lighting Forum)](https://forum.malighting.com/forum/thread/68396-understanding-phaser-width-and-measure-mathematics/), [Phasers (grandMA3 2.0 Help)](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)

---

## 4. 레이어(Layer) — Absolute / Relative 구조 요약

- 페이저 스텝은 **절대 레이어**와 **상대 레이어**를 동시에 가질 수 있다. 페이저 에디터에서 이 둘을
  각각 `Absolute` / `Relative` 버튼으로 필터링해서 볼 수 있다.
- **Add Absolute** 버튼: 절대값 스텝 추가 — 인코더 바가 절대 레이어를 따라간다.
- **Add Relative** 버튼: 상대값 스텝 추가 — 인코더 바가 상대 레이어를 따라간다.
- 상대 레이어로 프로그램하면, 절대 레이어(베이스 포지션)를 나중에 바꿔도 페이저 자체(모양)에는
  영향을 주지 않는다 — 이것이 "동일한 이펙트 모양을 여러 다른 절대 위치 프리셋과 재사용"할 수 있는
  이유다(②의 레시피가 이 원리를 그대로 활용한다).
- 절대 ↔ 상대 전환: 포럼 사례에 따르면 콘솔 UI에서 페이저를 Absolute에서 Relative로(또는 그 반대로)
  바꾸는 전용 토글이 존재하며, 값 자체를 유지한 채 레이어 성격만 바꿀 수 있다.

출처: [Change Phaser from Abs to Rel (MA Lighting Forum)](https://forum.malighting.com/forum/thread/9075-change-phaser-from-abs-to-rel/), [Relative phaser issue (MA Lighting Forum)](https://forum.malighting.com/forum/thread/68407-relative-phaser-issue/), [one P,T effect works with few position relative/absolute (MA Lighting Forum)](https://forum.malighting.com/forum/thread/4599-one-p-t-effect-works-with-few-position-relative-absolute/)

---

## 5. 참고 영상 자료

- [Phasers in GrandMA3 - Movement Effects (YouTube)](https://www.youtube.com/watch?v=s1weufDsI3E) — 포지션 페이저 제작을 화면으로 시연하는 튜토리얼. 웹 검색 스니펫만 확인했으며 전체 스크립트는 본 리서치에서 직접 열람하지 못했다(향후 확인 필요).
- [E10 - Phaser Effects For Beginners - GrandMA3 OnPC Tutorial (YouTube)](https://m.youtube.com/watch?v=KMGH4YPruuc) — 초심자용 페이저 기초 튜토리얼 시리즈의 10편.

---

## 6. 확인되지 않은 부분(Gaps) — 후속 확인 필요

1. **페이저 스텝을 처음부터 커맨드라인만으로 생성하는 완전한 문법**(GUI 클릭 없이) — 검색 자료에서
   명확한 예시를 찾지 못함. `Store Phaser`류 커맨드의 정확한 문법은 공식 매뉴얼의 커맨드 레퍼런스
   섹션을 직접 열람해야 확정 가능.
2. **발리후(Ballyhoo)는 grandMA3 공식 문서에 전용 용어로 정의되어 있지 않다** — 업계 통용 개념 + 포럼의
   "ballyhoo type effects" 언급을 조합해 재구성한 레시피이며, MA Lighting 공식 프리셋/템플릿 이름으로
   존재하는지는 추가 확인이 필요하다.
3. **StepCreator 커맨드의 `Repeat` 속성 미구현** 여부는 포럼 게시 시점(구버전) 기준이라 현재 버전에서도
   유효한지 재확인이 필요하다.

---

*작성: 리서치 태스크 B — 웹 검색(WebSearch/WebFetch) 기반, 2026-08-15 기준 공식 문서·포럼 스냅샷.*
