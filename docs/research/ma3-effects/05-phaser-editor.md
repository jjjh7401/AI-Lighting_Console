# 05. Phaser Editor 창 딥다이브 — 레이아웃, 레이어, 그리고 프리셋 저장 의미론

리서치 태스크: grandMA3 **Phaser Editor**(GUI 창)를 심층 조사한다. 명령줄 문법(04 문서)과
달리 이 문서는 (1) 에디터 창 자체의 레이아웃·도구, (2) 스텝/레이어 편집 방식, (3) Form
프리셋(sine/square/saw), (4) 에디터가 명령줄과 실질적으로 무엇이 다른지, (5) 에디터가
적합한 상황 vs 대안, 그리고 (6, 핵심) **페이저가 프리셋(Preset)에 저장되는 정확한 의미론** —
어떤 프리셋 풀이 페이저 스텝을 받는지, `All` 풀의 정체, `Store Preset`의 `/Universal`·
`/Global`·`/Selective` 정확한 문법, 그리고 페이저를 담은 프리셋이 프로그래머·큐로 리콜될 때
벌어지는 일 — 을 다룬다.

> 이 저장소(`AI-Lighting_Console`)는 콘솔 화면을 직접 조작하지 않고 OSC/Lua로만 명령줄을
> 구동한다(04 문서 참고). Phaser Editor 자체는 이 저장소가 **쓸 수 없는 도구**이지만, 에디터가
> 내부적으로 조작하는 레이어(Accel/Decel/Transition/Width/Phase/Speed/Measure)는 명령줄
> `Attribute '<a>' At <Layer> <value>` 문법과 1:1로 대응하므로, 이 문서는 "GUI가 어떤 레이어를
> 어떻게 건드리는가"를 통해 명령줄 페이저 제어의 정확도를 높이는 데도 쓰인다. 프리셋 저장
> 의미론(§6)은 향후 "페이저를 프리셋으로 캡슐화해 재사용"하는 기능을 설계할 때 직접 필요하다.

---

## 1. Phaser Editor 열기

- **저장 가능한 창**으로 열기: Add Window 팝업 → Phaser Editor 선택.
- **임시 창**으로 열기: 인코더 바(Encoder Bar)의 Phaser 버튼을 탭.
- 2.0 → 2.2 → 2.4까지 별도 창으로 존재하며, 2.4 릴리스 노트를 봐도 "Recipe Editor로 통합"
  같은 표현은 없다 — Phaser Editor와 (2.4에서 신설된) Recipe Editor/Phaser Recipe는
  **공존하는 별개의 두 경로**다(§5.1 참고).

> Phaser Editor는 "실행 중인 페이저를 시각화하는 여러 방법 + 페이저를 동적으로 만들고
> 편집하는 도구"를 제공하며, 포지션(Pan/Tilt) 속성을 조정하는 단순 트랙패드로도 쓸 수 있다.

Sources:
- [Phaser Editor (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)
- [Phaser Editor (2.4)](https://help.malighting.com/grandMA3/2.4/HTML/phaser_editor.html)
- [Phasers (2.0)](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)

---

## 2. 창 레이아웃

### 2.1 메인 표시 영역

| 구성 요소 | 설명 |
|---|---|
| 2D 레이아웃(파란 격자) | 가로축=Pan 전체 범위, 세로축=Tilt 전체 범위. 선택된 픽스처는 노란 십자선으로 표시. "Show Beams" 켜면 밝기·색을 원으로 함께 표시 |
| 1D 레이아웃 | 속성별 개별 타임라인(스텝을 시간축 위에 표시) |
| 속성 버튼(타이틀 바 아래) | At Filter와 직결 — 노란 막대=활성 속성, 회색 막대=비활성 |
| 좌측 도구 버튼 | 편집 기능(§3) |
| 우측 조작 버튼 | 리셋/삭제/복사/미러 등 단축 기능(§3.2) |
| Step Bar(하단) | 스텝 빠른 선택 도구(기본 활성). 스텝 상태를 빈칸(어두움)/선택 해제(연회색)/선택됨(노랑)으로 표시. 네비게이션 화살표 + 현재 스텝 카운터 + 라디오 버튼 3개(다른 인코더 툴바 접근) |

### 2.2 View Mode 4종

| 모드 | 내용 |
|---|---|
| **Auto** | 2D + 1D 레이아웃을 함께 표시 |
| **2D** | 포지션 페이저 작업을 위해 2D 격자를 확대. Values 버튼으로 Absolute / Relative / Abs+Rel 표시를 순환 |
| **1D** | 속성별 개별 타임라인. 두 가지 드로잉 모드 — **Value 모드**(세로축=속성 전체 범위), **Transition 모드**(세로축=스텝 간 값 변화량) |
| **Sheet View** | 픽스처 시트와 유사한 스프레드시트 형식. 스텝=열, 레이어=행으로 배치하고 아래에 1D 레이아웃도 함께 표시 |

### 2.3 창 설정(Window Settings)

View mode, Line height(50–500px 또는 Auto), Beam 시각화 토글, 1D 드로잉 모드(Value/
Transition), 포지션 속성(PanTilt/XY/XZ/YZ), Step Bar·Layer Bar 표시 여부, 리드아웃
포맷(Natural/Percent/Physical/Decimal/Hex), 속도 표시(Hertz/BPM/Seconds), 프리셋 정보
표시, 컬러 모드(RGB/CMY), Sheet의 행·열 설정.

Sources:
- [Phaser Editor (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)
- [Phaser Editor (2.4)](https://help.malighting.com/grandMA3/2.4/HTML/phaser_editor.html)

---

## 3. 도구 (Toolbar)

### 3.1 좌측 편집 도구

| 도구 | 기능 |
|---|---|
| Move Area | Pan/Tilt 사각형을 이동시켜 표준 범위 밖의 상대값을 표시 |
| Select | 단일/올가미 선택. Absolute/Relative 스텝으로 필터 가능 |
| Add Absolute | 절대값으로 스텝 추가. Single Step Mode 활성화 |
| Add Relative | 상대값으로 스텝 추가. Single Step Mode 활성화 |
| Move Point | 선택된 스텝 이동(Align 기능 지원) |
| Move Handles | 선택된 스텝의 가속/감속 핸들 조정 |
| Change Size | 선택된 스텝 전체를 중심점 기준으로 균등 확대/축소 |
| Change Rotation | 선택된 스텝 회전. MA 키를 누르면 5° 단위로 고정 |
| Change Phase | 오버레이를 열어 픽스처별 Phase 값을 노란 점으로 표시·조정 |
| Change Width | 스텝 너비 조정. Equalize Width로 이동 거리와 무관하게 균일한 속도 확보 |
| Select Form | Transition/Accel/Decel 레이어를 덮어씀. 옵션: Rectangle, Sawtooth, Sine, Circle(§4) |
| Change Speed | 페이저 속도를 곱하거나 나눔. Loop=스텝 수만큼 곱함, Fixture=픽스처 수만큼 나눔 |
| Select All Steps | 전체-스텝 선택 ↔ 단일-스텝 선택 토글 |

### 3.2 우측 조작 기능

Reset(spline), Delete, Cut/Copy/Paste Programmer, Mirror X/Y/Time, Swap XY, Flip,
Reset Zoom.

### 3.3 인코더 툴바 2종

- **2D Bar**: MoveX, MoveY, Size, Handle, Rotate, Aspect, Select Step — 포지션 조작용.
- **Phaser Bar**: Speed, Phase, Transition, Width, Measure — 현재 선택/At Filter 상태에
  따라 조정.

### 3.4 점(포인트) 시각화 규약

- 노란 십자선 = 선택된 픽스처
- 채워진 사각형 = 절대(Absolute) 포인트, 빈 사각형 = 상대(Relative) 포인트
- 빨간 선 = 상대 포인트와 그에 대응하는 절대 포인트를 연결
- 초록 선 = 픽스처 이동 경로 궤적
- 선택된 포인트는 노란 원 표시

### 3.5 워크플로 메모

2D 레이아웃에 점을 추가하면 스텝이 생성된다 — 첫 점은 픽스처 위치를 잡고, 이후 점들이
스텝을 추가한다. Step Bar로 빠른 스텝 선택·수정이 가능하고, 점/핸들을 조작하는 동안
Single Step Mode가 자동 활성화된다. At Filter가 어떤 속성이 조정을 받을지 제어한다.
공식 문서의 팁: "일부 도구는 점을 정확히 터치할 필요가 없다 — 원하는 스텝이 Step Bar에서
활성화되어 있는지 확인하고, 파란 격자 영역을 트랙패드처럼 사용하라."

Source: [Phaser Editor (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)

---

## 4. Form 프리셋 (Sine / Square / Sawtooth / Circle)

**Select Form** 도구는 Rectangle(사각파), Sawtooth(톱니파), Sine(사인파), Circle(원형)
4종을 제공한다. 이 버튼들은 **Transition 레이어 + Accel 레이어 + Decel 레이어의 값을
한 번에 덮어쓰는 단축키**일 뿐이다.

> "there is no command to change the form....you need to adjust the individual
> parameter in the command wing bar" — Thomas Koppers(MA Lighting)
>
> "Changing the values of those layers can be done using syntax, and then you can
> make them anything you want — not just limited to the existing small list."
> — Ryan Kanarek(MA Lighting)

즉 Form 버튼은 **명령줄에 대응하는 단일 키워드가 없다**. 대신 아래 세 레이어를 직접
지정하면 동일한 효과(및 그 이상의 커스텀 파형)를 명령줄로도 만들 수 있다:

```
Attribute "Pan" at Transition 10
Attribute "Pan" at Width 10
Attribute "Pan" at Accel -100
Attribute "Pan" at Decel -100
Attribute "Pan" at Phase 180
```

Sine 파형(부드러운 사인 곡선)은 대략 Accel −100 / Decel −100 조합에 대응한다는 것이
04 문서(§ G2)의 미검증 가정(ASSUMPTION)과도 일치한다 — 이번 조사로 그 근거가 Form
버튼의 "레이어 프리셋" 구조에 있음을 확인했다.

Sources:
- [Phaser Editor Form commands 포럼](https://forum.malighting.com/forum/thread/8333-phaser-editor-form-commands/)
- [Edit Phasers in Commandline 포럼](https://forum.malighting.com/forum/thread/4468-edit-phasers-in-commandline/)
- [Change form of Phaser with command line 포럼](https://forum.malighting.com/forum/thread/5146-change-form-of-phaser-with-command-line/)

---

## 5. 레이어 총정리 (Absolute / Relative / Accel / Decel / Transition / Width / Phase / Speed / Measure)

페이저는 **값 레이어**와 **스텝 레이어**, **페이저 전역 레이어** 세 층으로 나뉜다.

| 레이어 | 범위 | 의미 |
|---|---|---|
| **Absolute** | 스텝별 | 하드 값(예: Dimmer 50%). 에디터에서 채워진 사각형으로 표시 |
| **Relative** | 스텝별 | 프리셋/기준값 대비 오프셋(예: −20%). 빈 사각형으로 표시, 빨간 선으로 대응 절대 포인트와 연결 |
| **Width** | 스텝별 | 해당 스텝 시작부터 다음 스텝 시작까지의 길이(한 비트의 퍼센트). 기본 100%면 이동 거리와 무관하게 균등한 타이밍 |
| **Transition** | 스텝별 | 스텝 너비 중 값이 실제로 변화하는 데 쓰이는 비율(퍼센트) |
| **Accel / Decel** | 스텝별 | 가속/감속 곡선. Decel 값 −100%=부드러운 끝, 200%=급격한 끝(공식 문서 표현) |
| **Speed** | 페이저 전역 | 전체 재생 속도(BPM/Hz/초 단위로 표시 가능) |
| **SpeedMaster** | 페이저 전역 | 페이저 속도를 Speed Master 이그제큐터에 연결 |
| **Phase** | 픽스처/속성별, 페이저 전역 개념 | 픽스처 간 타이밍 오프셋(도 단위) — 파도/서클 이펙트의 핵심 |
| **Measure** | 페이저 전역 | 반복 루프 안의 비트 수 |

주의: "모든 스텝에 적용되는" 페이저 전역 레이어(Speed/SpeedMaster/Phase/Measure)는 **스텝 1 아래에서만** 나타난다 — 에디터/Sheet View에서 이 레이어들을 스텝 2 이후에서 찾으면 보이지 않는 것이 정상이다.

또한 프리셋에 저장할 때 중요한 규칙 하나: **"이 레이어들(Speed/Phase/Transition/Width/Measure) 중 하나를 프리셋에 추가하면, 사실상 페이저 레이어 전체가 함께 추가된다"** — 즉 부분 레이어만 골라 저장하는 것은 불가능하고, 페이저 레이어는 세트로 움직인다(§6.4).

Sources:
- [Phaser Editor (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)
- [Phasers (2.0)](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [Use Preset (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/presets_use.html)
- [Phase in phaser editor 포럼](https://forum.malighting.com/forum/thread/5130-phase-in-phaser-editor/)

---

## 5.5. 특수 기능 — Stomp / Sync / DelayToPhase

- **Stomp**: 실행 중인 페이저를 정지시키고 마지막 출력값만 남긴 단일 스텝으로 고정한다.
  프로그래머가 스텝 1 상태에서 실행 중인 페이저 속성 위에 정적(static) 프리셋을 호출하면
  자동으로 Stomp가 적용된다(§6.5 참고).
- **Sync**: 페이저를 리콜할 때 타이밍과 위상 오프셋을 예측 가능하게 고정한다.
- **DelayToPhase**: 켜면 속성 Delay 시간이 끝난 뒤부터 위상 계산이 시작되고, 끄면 큐
  트리거와 동시에 모든 위상이 시작된다.

Source: [Phasers (2.0)](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)

---

## 6. Phaser Editor vs 명령줄 — 실질적 차이

### 6.1 표현력 차이는 없다, 워크플로가 다르다

포럼의 정리된 결론: **Form 버튼조차 결국 Transition/Accel/Decel 레이어 값의 조합**이므로,
GUI로 만들 수 있는 페이저는 이론상 전부 명령줄로도 만들 수 있다. 차이는 "어떻게 도달하는가"다.

| 축 | Phaser Editor | 명령줄 |
|---|---|---|
| 포지션 이펙트(원, 8자, 랜덤 워크) | 2D 격자에서 점을 찍고 드래그 — 결과를 즉시 눈으로 확인 | `Attribute 'Pan' At <n>` / `Step 2` 반복 — 도형을 눈으로 보며 만들 수 없음 |
| 파형 미세조정(Accel/Decel 곡선) | Move Handles로 베지어 핸들을 직접 드래그 | `At Accel <n>` 숫자만 입력, 곡선 형태를 시각적으로 가늠 불가 |
| 여러 픽스처의 Phase 분산 | Change Phase 오버레이에서 노란 점으로 실시간 확인 | `At Phase 360` 등 단일 값만 입력(MAtricks 없이는 그리드 축별 분산 불가 — §Phase 포럼 참고) |
| 매크로/스크립트 자동화 | 불가(사람의 마우스 조작 필요) | 가능 — Lua 플러그인, OSC, 매크로에서 100% 재현 가능 |
| 라이브 중 실시간 반응 편집 | 가능(실행 중인 페이저를 보면서 조정) | 가능하지만 결과를 눈으로 즉시 확인하기 어려움 |
| 신뢰성 | 상대적으로 안정적 | 포럼에서 "명령줄 편집은 알려진 신뢰성 문제가 있다(MA 지원팀도 인정)"는 언급 있음 — 레이어를 먼저 선택해야 일관성이 개선됨 |

### 6.2 StepCreator — 두 세계를 잇는 다리

명령줄에서도 GUI Phaser Editor의 내부 상태 오브젝트인 **StepCreator**를 조작할 수 있다:

```
Set Stepcreator property "[property name]" "[value]"
Assign Attribute [number] At Stepcreator Property "SELECTEDATTRIBUTE"
```

이는 GUI 없이도 GUI가 만드는 것과 동일한 내부 구조를 명령줄에서 프로그래밍적으로 채울 수
있다는 뜻이며, StepRecipe Pool은 이렇게 구성한 StepCreator 설정을 버튼 하나로 저장·리콜하는
용도다.

### 6.3 2.4 신기능 — Recipe Editor / Phaser Recipe / Shape Pool

2.4 릴리스에서 **레시피 에디터(Recipe Editor)에 페이저 레시피(Phaser Recipe)** 기능이
추가됐다. 이는 Phaser Editor를 대체하지 않는 **병행 경로**다.

- 레시피 에디터에서 2스텝 이상의 "레시피"를 바로 만들 수 있다.
- 신규 열: Step, Shape, Attributes, Value Absolute, Value Relative, Curve,
  Transition/Width/Accel/Decel(X/Y/Z 축별).
- 페이저 레시피는 보라색 배경으로 일반(초록색) 레시피와 구분된다.
- **Shape Pool**: 커브/트랜지션/Width/Accel/Decel 값을 미리 정의해 재사용하는 신규
  풀. 기본 22종 Shape가 내장된다. "Shapes span across the entire phaser" — 즉 Shape는
  Select Form의 4종(Rectangle/Sawtooth/Sine/Circle)을 22종으로 확장한 것에 가깝다.
  수동으로 입력한 값이 Shape 값보다 우선한다.

### 6.4 페이저 레이어는 "전부 아니면 전무"

§5에서 언급한 규칙을 다시 강조: 프리셋(또는 큐)에 Speed/Phase/Transition/Width/Measure
레이어 중 하나라도 프로그래머에 존재하면, 해당 저장 동작은 **페이저 레이어 세트 전체**를
함께 저장한다. "일부 레이어만 저장"은 UI/명령줄 어느 경로로도 지원되지 않는다.

Sources:
- [Edit Phasers in Commandline 포럼](https://forum.malighting.com/forum/thread/4468-edit-phasers-in-commandline/)
- [Phaser Editor Form commands 포럼](https://forum.malighting.com/forum/thread/8333-phaser-editor-form-commands/)
- [Features 2.4 릴리스 노트](https://help.malighting.com/grandMA3/2.4/HTML/rn_features-2-4.html)
- [Recipe Editor / recipe-sheet (2.4)](https://help.malighting.com/grandMA3/2.4/HTML/recipe-sheet.html)
- [Use Preset (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/presets_use.html)

---

## 7. Phaser Editor가 적합한 상황 vs 대안

| 상황 | 권장 도구 | 이유 |
|---|---|---|
| 포지션 이펙트(원, 8자, 부채꼴, 랜덤 웨이브)를 처음부터 디자인 | **Phaser Editor 2D View** | 도형을 눈으로 보며 만들 수 있는 유일한 경로. 명령줄로는 "숫자를 넣고 결과를 상상"해야 함 |
| Accel/Decel 커브를 세밀하게 튜닝(부드러운 vs 급격한 전환) | **Phaser Editor + Move Handles**, 또는 22종 Shape Pool(2.4+) | 베지어 핸들 드래그가 숫자 입력보다 직관적 |
| 이미 검증된 문법을 반복 재생성(매크로, 자동화, AI 코파일럿) | **명령줄 / StepCreator / Lua API** | GUI는 사람의 조작이 필요해 자동화 불가. 이 저장소(`server/fx/`)의 접근법 |
| 다수 픽스처에 위상을 균등 분산(웨이브) | 단일 축이면 **Phaser Editor Change Phase**, 다축 그리드면 **MAtricks 창** | Phase 360 버튼은 다축 선택에서 "모든 축에 균등 분산"이라 그리드에서는 축별 제어가 불가능(포럼 실측: 8×4 그리드에서 마지막 픽스처 Phase가 585°까지 감) — MAtricks가 축별 제어를 제공 |
| 라이브 공연 중 실행 중인 페이저를 즉석에서 조정 | **Phaser Editor**(실행 중 파형을 보며 조정) 또는 인코더 바 | 시각 피드백이 즉시 필요 |
| 스프레드시트처럼 여러 스텝·레이어를 한눈에 검토/일괄 수정 | **Sheet View** 또는 2.4 **Recipe Editor**(Group by Attribute) | Sheet View는 열=스텝 행=레이어라 컬럼이 좁아지면 가독성이 떨어진다는 사용자 불만이 있음(포럼) — Recipe Editor의 Group by Attribute가 이를 개선 |
| 콘솔 화면에 접근할 수 없는 원격/헤드리스 제어(OSC, AI 코파일럿) | **명령줄만 가능** | GUI 도구는 애초에 선택지가 아님 |

Sources:
- [Understanding the Phaser Editor Window 포럼](https://forum.malighting.com/forum/thread/68859-understanding-the-phaser-editor-window/)
- [Phase in phaser editor 포럼](https://forum.malighting.com/forum/thread/5130-phase-in-phaser-editor/)
- [Phaser basics 포럼](https://forum.malighting.com/forum/thread/68294-phaser-basics/)

---

## 8. ⭐ 페이저 → 프리셋 저장 의미론 (핵심 조사 항목)

### 8.1 멀티스텝 프리셋이란

프로그래머에 페이저(2스텝 이상) 정보가 있는 상태로 `Store Preset`을 실행하면, 그 프리셋은
**멀티스텝 프리셋**(=페이저를 담은 프리셋)이 된다. 풀 창에서 **점 3개(⋯) 아이콘**으로
표시되어 일반 단일-스텝 프리셋과 구분된다.

> "With Phaser information in the programmer, a preset can be stored. This will
> then be a multistep preset."

### 8.2 어떤 프리셋 풀이 페이저 스텝을 받는가

grandMA3는 **Feature Group(기능 그룹)마다 하나씩 프리셋 풀**을 자동 생성한다. 커스텀
Feature Group을 만들지 않은 기본 쇼에는 기본 Feature Group 이름을 딴 풀 9개가 있다고
공식 문서가 명시한다(Dimmer, Position, Colour/Color, Gobo, Beam, Focus, Control, Shaper,
Video가 문서에 등장하는 기본 Feature Group 이름들 — 단, 공식 문서에서 이 9개를 번호까지
매긴 표는 찾지 못했다. §8.6 GAP 참고).

- **Feature Group 풀**은 기본 **입력 필터(input filter)** 를 갖는다 — 예: Position 풀은
  Pan/Tilt류 속성만 받아들이도록 필터링된다.
- **`All` 풀 5개**(`All 1` ~ `All 5`)는 기본 입력 필터가 **없다** — 어떤 속성 값이든
  (당연히 페이저 스텝을 포함해) 저장할 수 있다. 필요에 맞게 이름을 바꿔 쓸 수 있다.
- 결론: **페이저가 여러 종류의 속성(예: Pan/Tilt + Dimmer)을 동시에 담고 있다면 `All` 풀에
  저장해야** 입력 필터에 막히지 않는다. 단일 Feature Group(예: Position만) 페이저라면 해당
  Feature Group 풀에도 저장 가능하다.
- **Dynamic 풀**이라는 특수 풀도 있다 — 선택된 Feature Group에 따라 자동으로 해당
  Feature Group 프리셋 풀로 전환된다.

### 8.3 Store Preset 정확한 명령줄 문법

```
Store Preset [FeatureGroup_Name_또는_Number].[Preset_Name_또는_Number] [/Option]
```

기본 워크플로(GUI): 픽스처 선택 → 프로그래머에 값(또는 페이저) 설정 → **Store**를 약 1초
길게 눌러 Store Options 팝업 호출 → 프리셋 풀 오브젝트를 탭.

**모드 옵션 키워드** 3종(Store Options 팝업 또는 명령줄 `/` 옵션으로 지정):

| 모드 | 약어 | 의미 |
|---|---|---|
| **Selective** | `/Selective` | 프로그래머에 활성 데이터가 있는 각 픽스처별로 개별(selective) 데이터로 저장 |
| **Global** | `/Global` (강제: `/ForceGlobal`) | 주로 전역(global) 플래그로 저장. 같은 Fixture Type의 여러 픽스처 값이 다르면 평균값을 전역값으로 쓰고, 나머지 편차는 selective로 별도 저장 |
| **Universal** | `/Universal` (단축 `/U`) | 전역(global) 데이터로 저장하되, 프리셋 모드 자체를 Universal로 설정 — Fixture Type과 무관하게 호환되는 모든 픽스처에 적용 가능 |

`/Universal` 옵션 키워드의 정확한 정의:

> "The /Universal option keyword is used to store or update universal data into
> presets regardless their mode."

문법(공식 문서 예시):

```
Store Preset ["FeatureGroup_Name" 또는 FeatureGroup_Number].["Preset_Name" 또는 Preset_Number] /Universal
```

실사용 예:

```
Store Preset 1.2 /Universal
```

기타 확인된 옵션: `/Merge`(기존 데이터에 새 값을 병합), `/KeepActivation`(저장 후 프리셋
활성 상태 유지 여부), `/MAtricks`(MAtricks 설정 포함 저장), `/Active`, `/All`, `/Ask`,
`/Auto`, `/Overwrite`, `/Screen` 등. 대상(Object)을 생략하면 기본 오브젝트는 `Cue`이며,
지정 위치가 없으면 풀의 첫 빈 자리를 자동 사용한다(Cue 기준 예시지만 Store 키워드 전체의
공통 동작).

**Global 데이터 제거**:

```
Cleanup Preset x.y /Global
Cleanup Preset x.y /Selective
```

단, 포럼 실측 보고에 따르면 `All` 프리셋 등 일부 상황에서 `/Global` 정리가
`"nothing to be done"`을 반환하며 동작하지 않는 사례가 있다 — 프리셋 편집기의
Fixture Sheet에서 우상단 노란 박스가 전역(Global) 플래그 표시이므로, 정리 전 이걸로
먼저 확인하는 것이 권장된다.

### 8.4 페이저 레이어는 세트로 저장된다

프리셋에 Speed/Phase/Transition/Width/Measure 레이어 중 하나라도 있으면, 저장 시
**페이저 레이어 전체가 함께 추가된다**("adding one of these layers in a preset
effectively adds all the phaser layers") — 부분 레이어만 골라 저장할 수 없다.

### 8.5 페이저를 담은 프리셋을 프로그래머로 리콜

- 리콜 절차는 프리셋 종류(단일 스텝/MAgic/Recipe/Multistep)와 무관하게 동일하다: 픽스처
  선택 → 프리셋 탭. 픽스처 선택이 없는 상태로 프리셋을 탭하면 첫 탭이 "이 프리셋을 쓸 수
  있는 모든 픽스처"를 선택한다(그룹처럼 동작).
- **Stomp와의 상호작용**: 프로그래머가 스텝 1 상태에서, 이미 실행 중인 페이저 위에
  정적(static) 프리셋을 호출하면 자동으로 Stomp가 적용되어 페이저가 멈추고 그 프리셋의
  정적 값만 출력된다.
- 프리셋에 저장된 타이밍(Fade/Delay) 값은 리콜 시 자동 적용되며, Programmer Time
  마스터보다 **우선순위가 높다**.

### 8.6 페이저를 담은 프리셋이 큐(Cue)에 저장될 때

- 프리셋을 큐에 저장하면 값이 그대로 박히는 게 아니라 **프리셋에 대한 참조(reference)**
  가 저장된다. 즉 이후 프리셋 값을 바꾸면 그 프리셋을 참조하는 모든 큐가 자동으로 갱신된다
  — 프리셋을 아예 삭제하면 그때는 값이 큐로 전사(transfer)된다.
  - 예외: 타이밍-only 프리셋이 다른 값 프리셋과 결합해 큐에 들어가는 경우, 그 타이밍
    정보는 "프리셋 참조 없는 개별 타이밍 값"으로 저장된다. 값+타이밍을 함께 가진 프리셋은
    참조를 유지한다.
- 프리셋에 나중에 속성을 추가/삭제하면, 이미 그 프리셋을 참조하는 큐들을 갱신하기 위해
  **`Recast`** 키워드를 써야 한다.
- **`Extract /Single`**: 계층을 한 단계 아래로 추출하는 옵션. 프리셋 안에 다른 프리셋이
  내장된 경우(임베디드 프리셋) 또는 스텝 안에 프리셋이 들어있는 페이저 프리셋을 추출할
  때, 원본 프리셋 값을 직접 호출하도록 만든다.
- **절대값 vs 상대값의 Fade/Delay 우선순위**: 절대값에 연결된 Fade/Delay가 상대값에
  연결된 Fade/Delay보다 우선순위가 높다.

### 8.7 GAP — 확인하지 못한 항목 (정직한 한계 고지)

`verification-claim-integrity` 원칙에 따라, 조사했으나 **공식 문서·포럼에서 명시적 숫자를
확인하지 못한** 항목을 아래에 명시한다. 이 항목들은 추정으로 채우지 않았다:

1. **`All` 풀의 정확한 기본 풀 번호(2.4.2 기준)**: 공식 매뉴얼은 "`All 1` ~ `All 5`라는
   이름의 풀 5개가 있고 입력 필터가 없다"까지는 명시하지만, 이 풀들의 기본 풀 번호가
   몇 번(예: 10~14 또는 91~95)인지 숫자로 못 박은 문서를 찾지 못했다. 커뮤니티 경험상
   Feature Group 풀 9개 뒤에 이어지는 경우가 흔하나, 이는 **1차 출처로 확인된 사실이
   아니라 미검증 추정**이므로 이 문서에서는 사실로 기재하지 않는다. 실제 사용 시
   `Pool Preset` 창(또는 `List Preset`)에서 라이브로 확인할 것을 권장한다.
2. **Feature Group 풀 9개의 정확한 번호 순서**(Dimmer=1, Position=2, … 순인지 여부):
   위와 같은 이유로 동일하게 미확인. 공식 문서는 "이름을 딴 풀 9개가 있다"고만 서술한다.
3. **`Shaper`라는 Feature Group 풀과 이 문서 앞부분의 "Phaser"라는 용어의 관계**:
   `Shaper`는 grandMA3의 **Feature Group 이름**(빔 셰이퍼/블레이드류 속성 그룹으로
   추정)이고, `Phaser`는 **스텝 기반 이펙트 엔진**을 가리키는 별개의 용어다. 이름이
   유사해 혼동하기 쉬우나 문서상 직접적 연결 근거는 찾지 못했다 — 페이저는 Feature
   Group과 무관하게 어떤 풀에도(입력 필터가 허용하면) 저장될 수 있다.

---

## 9. 요약 표 — 이 문서의 핵심 결론

| 질문 | 답 | 근거 |
|---|---|---|
| Phaser Editor는 명령줄보다 표현력이 더 크다? | 아니다. Form 버튼조차 Transition/Accel/Decel 레이어 값의 조합일 뿐 — 이론상 모든 결과를 명령줄로도 만들 수 있다 | §4, §6.1 |
| 언제 GUI, 언제 명령줄? | 도형을 눈으로 보며 만들 때=GUI, 자동화·재현·헤드리스 제어=명령줄 | §7 |
| 페이저를 프리셋에 저장할 수 있나? | 그렇다 — 멀티스텝 프리셋(⋯ 아이콘)이 된다 | §8.1 |
| 어떤 풀에 저장해야 하나? | 단일 Feature Group 페이저는 해당 Feature Group 풀, 여러 Feature Group에 걸친 페이저는 입력 필터가 없는 `All 1~5` 풀 | §8.2 |
| 정확한 저장 문법은? | `Store Preset <그룹>.<번호> /Universal`(또는 `/Global`, `/Selective`) | §8.3 |
| 페이저를 담은 프리셋을 큐에 넣으면? | 값이 아니라 프리셋 **참조**가 저장됨(속성 변경 시 `Recast` 필요) | §8.6 |
| 프리셋의 레이어 중 일부만 저장 가능한가? | 불가 — 페이저 레이어(Speed/Phase/Transition/Width/Measure)는 세트로 함께 저장됨 | §8.4, §5 |

---

## 10. 참고 문헌 (Sources)

- [Phaser Editor (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/phaser_editor.html)
- [Phaser Editor (2.4)](https://help.malighting.com/grandMA3/2.4/HTML/phaser_editor.html)
- [Phasers (2.0)](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html)
- [Features 2.4 릴리스 노트](https://help.malighting.com/grandMA3/2.4/HTML/rn_features-2-4.html)
- [Recipe Editor / recipe-sheet (2.4)](https://help.malighting.com/grandMA3/2.4/HTML/recipe-sheet.html)
- [Presets (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/presets.html)
- [Create New Presets (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/presets_create.html)
- [Preset Pools (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/presets_pools.html)
- [Use Preset (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/presets_use.html)
- [/Universal Option Keyword (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/ok_universal.html)
- [Store Keyword (2.3)](https://help.malighting.com/grandMA3/2.3/HTML/keyword_store.html)
- [Pool Windows (2.3)](https://help.malighting.com/grandMA3/2.3/HTML/wvm_pool.html)
- [Understanding the Phaser Editor Window 포럼](https://forum.malighting.com/forum/thread/68859-understanding-the-phaser-editor-window/)
- [Phaser Editor Form commands 포럼](https://forum.malighting.com/forum/thread/8333-phaser-editor-form-commands/)
- [Edit Phasers in Commandline 포럼](https://forum.malighting.com/forum/thread/4468-edit-phasers-in-commandline/)
- [Change form of Phaser with command line 포럼](https://forum.malighting.com/forum/thread/5146-change-form-of-phaser-with-command-line/)
- [Phase in phaser editor 포럼](https://forum.malighting.com/forum/thread/5130-phase-in-phaser-editor/)
- [Phaser basics 포럼](https://forum.malighting.com/forum/thread/68294-phaser-basics/)
- [what is universal/global/selective in a preset 포럼](https://forum.malighting.com/forum/thread/9153-what-is-universal-global-selective-in-a-preset-removing-global-data/)
- [Difficulty understanding Selective vs. Global Presets 포럼](https://forum.malighting.com/forum/thread/8188-difficulty-understanding-selective-vs-global-presets/)
- [Command Line "Store Universal" Preset 포럼](https://forum.malighting.com/forum/thread/4026-command-line-store-univeral-preset/)
- [Universal selective preset 포럼](https://forum.malighting.com/forum/thread/68923-universal-selective-preset/)
