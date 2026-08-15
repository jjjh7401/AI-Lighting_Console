# grandMA3 MAtricks 에디터 딥다이브

리서치 태스크: help.malighting.com(v2.x)·MA Lighting 포럼·튜토리얼을 웹 검색하여 **MAtricks 에디터**의
전체 축 레퍼런스, 풀(Pool) 워크플로우, 선택 그리드·페이저와의 상호작용, RECIPES 안에서의 역할, 커맨드라인
문법, 그리고 "언제 MAtricks가 Phaser Editor보다 나은가"를 정리한다. 페이저 엔진 자체의 기초(Speed/Phase/
Width/Transition/Accel·Decel)는 `01-phaser-fundamentals.md`에서 이미 다뤘으므로, 이 문서는 **선택을
쪼개는 도구(MAtricks)** 쪽에 집중한다.

---

## 0. MAtricks란 무엇인가

> "MAtricks is a tool that can be used to divide a selection of fixtures into sub-selections."

MAtricks는 하나의 픽스처 선택(selection)을 **부분 선택(sub-selection)** 으로 나누는 도구다. 페이저가
"시간 축(Speed/Phase/Width)을 따라 값을 어떻게 바꿀지"를 정의한다면, MAtricks는 "선택된 픽스처 전체를
공간적으로 어떻게 그룹·분산·반전·섞을지"를 정의한다 — 두 도구는 서로 다른 축(시간 vs 공간)을 담당하며,
실무에서는 거의 항상 함께 쓰인다: **먼저 MAtricks로 선택을 쪼개고, 그 위에 Phaser Editor로 Phase 범위를
얹는다.**

MAtricks 값 자체는 "부분 선택을 결정하는 파라미터"이지 어트리뷰트 값(pan/tilt/color 등)이 아니다.
프로그래머(Programmer) 안에서 선택을 조작하는 임시 상태이며, 필요하면 **MAtricks 풀(Pool)** 에 저장해
재사용할 수 있다(§3).

출처: [MAtricks and Shuffle](https://help.malighting.com/grandMA3/2.3/HTML/matricks.html)

---

## 1. MAtricks 에디터 창 — UI 레이아웃

MAtricks 창은 다른 창과 동일하게 새로 생성하거나, **인코더 바(Encoder Bar) 메뉴**에서 열 수 있다.
창은 축(axis)별로 색상 코딩된 3개 구역으로 나뉜다:

| 축 | 배경색 |
|---|---|
| X축 | 빨강 |
| Y축 | 파랑 |
| Z축 | 초록 |

각 축은 좌측 사이드바 버튼으로 개별 On/Off 토글이 가능하다. 값 조정은 `+`/`−` 버튼, Next/Prev 커맨드,
또는 커맨드라인 직접 입력(`Set Selection MAtricks 'X' 6` 형태) 세 가지 방법을 모두 지원한다.

창 내부는 기능별로 다음 4개 구역으로 구성된다:

| 구역 | 포함 파라미터 |
|---|---|
| **Grid** | Axis(X/Y/Z), Block, Group, Wings, Width |
| **Layers** | Fade From/To, Delay From/To, Speed From/To, Phase From/To (Swap 기능 포함) |
| **Shuffle & Shift** | Shuffle, Shift — 축별 독립 |
| **Invert Options** | InvertStyle, InvertX/Y/Z, Transform(Mirror) |

회전 파라미터(Rx/Ry/Rz)에는 정렬(Align) 기능이 추가로 제공된다.

출처: [MAtricks and Shuffle](https://help.malighting.com/grandMA3/2.3/HTML/matricks.html), [15: MAtricks | grandMA3 for grandMA2 Programmers — Consoletrainer (Cat West)](https://consoletrainer.com/15-matricks-grandma3-for-grandma2-programmers/)

---

## 2. 축 전체 레퍼런스

### 2.1 Grid 구역 — 선택을 나누는 4가지 방식

이 4개 파라미터는 **모두 "하나의 선택을 몇 개의 부분 선택으로, 어떤 규칙으로 나눌지"** 를 정의한다는
공통점이 있지만 분배 규칙이 서로 다르다. X/Y/Z 각 축에 독립적으로 적용되므로 커맨드라인 프로퍼티명은
`XGroup`/`YGroup`/`ZGroup`처럼 축 접두어가 붙는다.

| 파라미터 | 정의 | 분배 규칙 | 그리드 위치 |
|---|---|---|---|
| **Group** | 선택을 지정한 그룹 수만큼 나눈다 | **교대(interleave)** — 1번 픽스처→그룹1, 2번→그룹2, 3번→그룹1 … 순서로 픽스처가 없을 때까지 반복 | 그룹에 속한 픽스처는 **동일한** 그리드 칸을 공유 |
| **Block** | 지정한 크기만큼 픽스처를 묶어 "하나의 픽스처"처럼 취급 | **연속(contiguous)** — 1~2번=블록1, 3~4번=블록2 … | 블록 수만큼 그리드 칸 수가 줄어듦(10대·Block=2 → 5칸, Block=5 → 2칸) |
| **Wings** | 선택을 지정한 윙 수로 나누고, 각 윙이 **반대 방향**에서 선택을 진행 | 윙1은 앞에서, 윙2는 뒤에서 중앙을 향해 진행 | `+`는 중앙 쪽으로, `−`는 바깥쪽으로 하이라이트 이동 |
| **Width** | 픽스처를 **다음 축으로 밀어내어** 다차원 배열을 만든다 | Group과 달리 같은 칸을 공유하지 않고 X/Y 좌표 조합으로 분리(예: XWidth=3 → 10대가 3열로 재배열, X=2·Y=1로 특정 픽스처 선택) | 여러 축을 동시에 조합 가능 |

**Group vs Block 핵심 차이** (공식 문서 인용): "The difference is that groups place the grouped
fixtures in the same grid positions where width moves the fixtures out on the next axis." — Group은
그리드 칸을 공유시키고, Width는 새 축으로 픽스처를 분리 배치한다.

**"Interleave"라는 용어에 대해**: 이 리서치 태스크가 별도 항목으로 요청한 Interleave는 grandMA3
공식 문서에서 독립된 파라미터명이 아니라, **Group이 픽스처를 그룹에 배분하는 방식 자체**(교대/인터리브
분배)를 가리키는 서술어로 등장한다 — "Groups... alternates through the selection putting fixtures
into each group." 즉 "Group=인터리브 분배, Block=연속 분배"로 이해하면 된다. (레거시 grandMA2 계열
매뉴얼에는 "Interleave"가 Next/Prev 탐색 모드를 가리키는 별도 UI 용어로도 등장하므로 버전 간 용어
혼용에 주의.)

출처: [MAtricks Groups](https://help.malighting.com/grandMA3/2.1/HTML/matricks_group.html), [MAtricks Blocks](https://help.malighting.com/grandMA3/2.0/HTML/matricks_block.html), [MAtricks Wings](https://help.malighting.com/grandMA3/2.0/HTML/matricks_wings.html), [MAtricks Width](https://help.malighting.com/grandMA3/2.3/HTML/matricks_width.html)

### 2.2 Layers 구역 — Fade/Delay/Speed/Phase From·To

Layers 구역은 페이저의 시간축 파라미터를 **선택 전체에 걸쳐 범위(From→To)로 분산**시키는 역할을 한다.
Phaser Editor의 Change Phase 도구(01문서 §4.3)와 사실상 같은 결과를 만들지만, MAtricks 창에서는 축마다
독립적으로 수치를 직접 입력할 수 있다.

| 레이어 | 커맨드라인 프로퍼티명(예) | 의미 |
|---|---|---|
| Fade From/To | `XFadeFrom` / `XFadeTo` | 페이드 타임을 선택 전체에 걸쳐 분산 |
| Delay From/To | `XDelayFrom` / `XDelayTo` | 딜레이를 선택 전체에 걸쳐 분산 |
| Speed From/To | `SpeedFromX` / `SpeedToX` | 페이저 속도를 축을 따라 분산(예: `Set Selection MAtricks "SpeedFromX" "Hz 10"`) |
| Phase From/To | `PhaseFromX` / `PhaseToX` | 위상을 축을 따라 분산 — Phaser의 Phase 레이어와 동일 개념 |

각 From/To 쌍에는 **Swap** 기능이 있어 시작·끝 값을 즉시 뒤바꿀 수 있다(예: `0→360`을 `360→0`으로,
즉 진행 방향 반전).

**함정 — Phase 0과 360은 같은 지점이다.** grandMA3 개발자(DanielK)의 공식 답변: "in the MAtricks
window 0 thru 360 is really 0 thru 360 - so the first and the last fixture will do exactly the same."
MAtricks 창에 `Phase 0 Thru 360`을 문자 그대로 입력하면 원(360도)이 한 바퀴 돌아 첫 픽스처와 마지막
픽스처가 정확히 같은 값을 갖게 되어 "분산 효과가 사라진 것처럼" 보인다. 회피 방법은 둘 중 하나다:
① 값을 `0 Thru 180`처럼 360 미만으로 지정, ② **인코더 바에서 조작** — 인코더 바는 선택된 픽스처
개수에 맞춰 자동으로 값을 재계산하므로 절대값이 아닌 상대적 분산이 적용된다.

출처: [MAtricks and Shuffle](https://help.malighting.com/grandMA3/2.3/HTML/matricks.html), [Phaser + MATricks not working as expected (forum, DanielK)](https://forum.malighting.com/forum/thread/5253-phaser-matricks-not-working-as-expected/), [MAtricks Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_matricks.html)

### 2.3 Shuffle & Shift

| 파라미터 | 정의 | 주의점 |
|---|---|---|
| **Shuffle** | 현재 픽스처 선택의 **선택 순서**를 무작위로 섞는다("Shuffle is used to shuffle the selection order of the current fixture selection") | **출력 값 자체는 바뀌지 않는다** — 선택 순서만 바뀌므로, 원하는 룩을 얻으려면 셔플 후 값을 다시 적용해야 한다. X/Y 등 여러 축에 동시에 적용 가능 |
| **Shift** | 현재 선택을 그리드 위치 내에서 **이동(offset)** 시킨다. 축별(XShift/YShift/ZShift) 독립 적용 | 양수는 오른쪽(X축)·아래쪽(Y축)·앞쪽(Z축)으로 이동, 음수는 반대 방향 |

실무 팁: MAtricks 창에서 **Shuffle을 원하는 패턴이 나올 때까지 반복 탭**한 뒤, **Y값을 `+`로 증가**시켜
행(row) 단위로 이동하며 각 행에 다른 프리셋을 순차 적용하는 워크플로우가 문서에 소개되어 있다 — 셔플로
"무작위처럼 보이지만 반복 가능한" 룩을 만들고, 그 위에 프리셋을 얹는 조합.

**Shuffle이 선택 순서를 바꾸는 것이지 InvertX/Y/Z는 아니다.** MA Lighting 스태프(Thomas Koppers)의
공식 답변: InvertX/Y/Z는 "페이저 진행 방향과 어트리뷰트 범위를 반전"(예: `0..360`→`360..0`)시키는
것이지 선택 순서 자체를 뒤집는 도구가 아니다 — 선택 순서를 바꾸려면 셀렉션 그리드 조작이나 Shuffle을
써야 한다는 것이 정확한 구분이다.

출처: [MAtricks Shuffle](https://help.malighting.com/grandMA3/2.0/HTML/matricks_shuffle.html), [Modify selection order via MAtricks (forum, Thomas Koppers)](https://forum.malighting.com/forum/thread/9084-modify-selection-order-via-matricks/)

### 2.4 Invert Options — InvertStyle / InvertX·Y·Z / Transform(Mirror)

Invert 구역은 창 하단에 위치하며, **"선택 그리드의 어느 축에 있는 값을 반전시킬지"** 를 정의한다.

| 파라미터 | 값/역할 |
|---|---|
| **InvertStyle** | 반전을 적용할 어트리뷰트 범위 — `Pan` / `Tilt` / `Pan+Tilt` / `All` 중 선택 |
| **InvertX** | 선택된 X축상의 개별 MAtricks 프로퍼티별 인버트를 전체적으로(overall) 다시 반전 |
| **InvertY** | Y축에 대해 동일 |
| **InvertZ** | Z축에 대해 동일 |
| **Transform (Mirror)** | Invert Options 안의 별도 설정. 활성화하면 대칭 오브젝트를 빠르게 만들고, **홀수 개** 픽스처 선택에서도 대칭적인 인상을 유지시킨다 |

**Transform(Mirror)의 동작**:
- 활성화 시 버튼 폰트 색이 노랑으로 바뀌고, InvertStyle이 자동으로 `Pan`으로 전환된다.
- `XWings=2` + Transform Mirror 활성 조합의 실전 예시: 11대(홀수) 픽스처로 미러 서클을 만들면, 정중앙에
  위치하는 "엣지 픽스처" 1대는 팬(pan)은 따라가지 않고 **틸트(tilt)만** 따라가는 방식으로 대칭이
  유지된다.
- **저장 주의**: Transform으로 만들어진 반전 값을 큐에 직접 Store하면 원본 프리셋 참조가 저장되지
  않는다 — 값이 이미 페이저 프리셋의 일부일 때만 참조가 유지된다.

**실전 조합 레시피 — 유니버설 미러 서클** (포럼 사용자 Miko의 워크플로우, §6에서 레시피 맥락과 함께
재론): `XWings=2` + `InvertWings ON` + `InvertStyle=P+T`(Pan+Tilt)를 조합하면, 좌우 어느 쪽에서 봐도
대칭인 원형 궤적을 만들 수 있다. 단, 이 조합을 **레시피 라인**(사용자 지정 시퀀스 안)에 넣으면 수동으로
적용했을 때와 다른 결과가 나올 수 있다는 미해결 이슈가 보고되어 있다(§6.3 참고).

출처: [MAtricks and Shuffle](https://help.malighting.com/grandMA3/2.3/HTML/matricks.html), [MAtricks Transform](https://help.malighting.com/grandMA3/2.3/HTML/matricks_transform.html), [Recipes, Invert Options and Phase in the MAtricks (forum, Miko)](https://forum.malighting.com/forum/thread/5298-recipes-invert-options-and-phase-in-the-matricks/), [Inverting pan when doing wings? (forum)](https://forum.malighting.com/forum/thread/9235-inverting-pan-when-doing-wings/)

---

## 3. MAtricks 풀(Pool) 워크플로우

MAtricks 값 자체는 **오브젝트 타입**으로 취급된다 — 프리셋·시퀀스와 마찬가지로 풀에 저장하고, ID로
참조하고, 큐/레시피 라인에 할당할 수 있다.

### 3.1 저장·호출·라벨

| 동작 | 커맨드 |
|---|---|
| 현재 MAtricks 설정을 풀에 저장 | `Store MAtricks ["MAtricks_Name" or MAtricks_Number]` (설정이 비어 있어도 저장됨) |
| 저장된 MAtricks 호출/적용 | `Call MAtricks <N>` |
| 이름 붙이기 | `Label MAtricks <N> "이름"` |
| 삭제 | `Delete MAtricks <N>` |
| 복사 | `Copy MAtricks <N> At MAtricks <M>` (표준 오브젝트 커맨드 패턴) |

### 3.2 프로퍼티 직접 조작 (Set Selection MAtricks)

프로퍼티 하나하나를 직접 세팅하는 표준 패턴은 다음과 같다:

```text
# 현재/지정 선택에 프로퍼티 값 지정
Set Selection [Selection_Number] MAtricks 'Property' [Value]
Set Selection MAtricks 'X' 6                  # X축 그룹 수를 6으로
Set Selection MAtricks 'XWing' 2              # X축 윙을 2로
Set Selection MAtricks 'PhaseFromX' 0
Set Selection MAtricks 'PhaseToX' 360         # 함정: 실제로는 180 권장(§2.2)
Set Selection MAtricks 'SpeedFromX' 'Hz 10'
Set Selection MAtricks 'XShuffle' 1234        # 시드 고정 랜덤(같은 시드=같은 룩)

# 함수/오브젝트 참조로 저장된 풀 아이템을 그대로 적용
Set Selection [Selection_Number] MAtricks [Function] MAtricks ["MAtricks_Name" or MAtricks_Number]

# 일시적 On/Off/Toggle (설정을 지우지 않고 효과만 껐다 켰다)
Off Selection MAtricks
Toggle Selection MAtricks

# 초기화(선택의 MAtricks 값을 리셋)
Reset Selection 1 MAtricks
```

**Lua 조합 예시** (포럼): X축 폭을 전체의 절반으로 자동 계산해 세팅 —

```lua
Lua "local r = select(2, SelectionComponentX()); Cmd('Set Selection MAtricks XWidth '..math.floor((r+1)/2))"
```

### 3.3 시퀀스/큐 파트에 MAtricks 풀 아이템 할당(Assign)

**오브젝트 참조는 `Assign`, 오브젝트 프로퍼티 값은 `Set`** — 이 구분이 MAtricks 커맨드 문법의 핵심
원칙이다(MA Lighting 모더레이터 Ryan Kanarek). 저장된 MAtricks 풀 아이템을 시퀀스의 특정 큐/레시피
라인에 연결하려면:

```text
Assign MAtricks 4 At Cue 1 Part 0.1
Assign MAtricks <x> At Sequence <y> Cue <z> Part <a>.<b>
#   a = 큐 파트(기본 0), b = 그 파트 안의 레시피 라인 번호(레시피 라인은 큐 파트의 자식 요소)

# 할당 해제(빈 문자열로 프로퍼티를 지움)
Set Sequence <a> Cue <b> Part <c>.<d> Property "MAtricks" ""
```

### 3.4 프리셋에 MAtricks 저장하기 — `/MAtricks` 옵션 키워드

프리셋을 저장할 때 현재 활성 MAtricks 설정을 함께 저장하려면 `/MAtricks`(단축형 `/MA`) 옵션 키워드를
붙인다:

```text
Store Preset ["FeatureGroup_Name" or FeatureGroup_Number].["Preset_Name" or Preset_Number] /MAtricks
Store Preset 1.3 /MAtricks     # 예: 3번 디머 프리셋에 현재 MAtricks 설정을 함께 저장
```

UI에서는 **Store 버튼을 길게 누르면** Presets 섹션에 `{MAtricks}` 토글이 나타나 Yes/No로 제어할 수
있다. 이는 "여러 어트리뷰트에 각각 다른 MAtricks를 걸었는데 프리셋 저장 시 하나만 남는다"는 흔한 불만에
대한 공식 해법이다 — 매크로로 Store를 호출하는 사용자는 이 롱프레스 토글을 놓치기 쉬우므로, 매크로 안에
`/MAtricks` 옵션 키워드를 명시적으로 넣어야 한다.

출처: [MAtricks Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_matricks.html), [/MAtricks Option Keyword](https://help.malighting.com/grandMA3/2.1/HTML/ok_matricks.html), [Syntax for assigning MAtricks Pool Item to Recipe Line in Sequence (forum, Ryan Kanarek)](https://forum.malighting.com/forum/thread/8242-syntax-for-assigning-matricks-pool-item-to-recipe-line-in-sequence/), [is it possible to filter out MAtricks info saved in presets (forum, Ryan Kanarek)](https://forum.malighting.com/forum/thread/8033-is-it-possible-to-filter-out-matricks-info-saved-in-presets/), ["Set Selection MAtricks" Lua 예시 (forum)](https://forum.malighting.com/forum/thread/68392-list-variable/)

---

## 4. 선택 그리드(Selection Grid)와의 상호작용

**Selection Grid**는 픽스처 선택을 3차원 가상 좌표계로 배치하는 시스템이다 — "a virtual coordinate
system that can be used to arrange the selection of fixtures in a true three-dimensional space", 그리고
"the distribution of things like Phaser looks, transition timing and delay sweeps can then be applied
over any axis of that space." MAtricks는 이 좌표계 위에서 동작하는 **조작 도구**이고, Selection Grid
자체는 좌표계 데이터(각 픽스처의 X/Y/Z 위치)를 제공하는 **데이터 계층**이라는 역할 분담으로 이해하면
된다.

### 4.1 단일 축 원칙

10×10 그리드에서 세로(상하) 방향으로만 이펙트를 걸고 싶다면, **Y축에만 MAtricks 설정을 걸고 X축은
None으로 유지**해야 한다. 두 축 모두에 값이 걸려 있으면 두 축의 위상 분산이 겹쳐 원치 않는 대각선
패턴이 나타난다(03문서 §6.2와 동일한 함정).

### 4.2 그리드 위상 분산 공식 — "줄줄이 진행" 만들기

X×Y 그리드에서 **행(row) 단위로 순차 진행**하는 위상차를 자동 계산하려면 (포럼, Sebastian):

```text
PhaseToX = 360 / Y - 360 / (X * Y)
```

예: 10열×5행 그리드라면 X축 Phase 범위는 약 **64.8도**(`360/5 - 360/50`)로 설정하고, Y축은 전체
`0→360` 범위를 그대로 쓴다. 대안으로 **Width/Transition** 조합(스텝 폭을 좁게, 예 10%/오프 스텝
90%)으로 특정 행만 순차 강조하는 방법도 보고되어 있으나, 정밀도는 픽스처 수에 따라 실험이 필요하다.

### 4.3 실무 트레이드오프 — 그리드 vs 리니어 선택 전환

한 사용자(djj)는 8×4 그리드 전체를 줄 단위로 훑는 페이저를 만들려다, 그리드 기반 위상 계산만으로는
원하는 결과가 나오지 않아 결국 **필요에 따라 그리드 선택과 리니어(순번) 선택을 오가며 MAtricks 설정을
바꾸는 실용적 절충**으로 정착했다고 보고한다. 즉 그리드 위상 공식은 "이론적으로 맞는 시작점"이지, 항상
자동으로 원하는 룩이 나온다고 보장하지는 않는다.

출처: [DOING THE MATHEMATICS WITH GRANDMA3 — CX Network (Jason Allen, 2023-04-19)](https://www.cxnetwork.com.au/doing-the-mathematics-with-grandma3/), [Grid Selection - MaTricks - Phaser (forum, Sebastian/strobie/djj)](https://forum.malighting.com/forum/thread/69260-grid-selection-matricks-phaser/), [circle phaser in grid/layout (forum)](https://forum.malighting.com/forum/thread/7991-circle-phaser-in-grid-layout/)

---

## 5. 페이저와의 상호작용 — 올바른 작업 순서

MAtricks와 Phaser Editor는 **같은 프로그래머 상태를 공유**하지만, 적용 순서에 따라 결과가 달라지는
알려진 함정이 있다.

### 5.1 권장 순서: 선택 → 페이저 활성화 → MAtricks 적용

포럼 사례("MAtricks not sticking"): 사용자가 그룹에 MAtricks를 먼저 걸고 **그 다음** MAtricks가 없는
페이저 프리셋을 불러오자, 이펙트가 "활성(active)"으로는 표시되지만 실제로는 동작하지 않고 재적용이
필요했다. MA Lighting 커뮤니티(strobie)의 진단: **순서가 거꾸로였다.** 올바른 순서는

```
1) 픽스처 선택
2) 페이저(프리셋) 활성화
3) 그 위에 MAtricks 적용
```

단, 이 순서를 따라도 "한 번만" 정상 동작하며, 다른 MAtricks로 다시 바꾸면 또 오작동할 수 있다는 한계가
보고되어 있다 — 근본 해결책이 아니라 완화책이다. 실전에서는 **매크로 기반 레시피**(선택+페이저
+MAtricks 조합을 한 번에 실행기 버튼에 저장하고 "Recipe On/Off" 토글로 관리)로 우회하는 것이
커뮤니티에서 권장되는 버스킹 워크플로우다.

### 5.2 Phase 0/360 겹침이 "페이저가 안 먹는 것처럼" 보이는 함정

§2.2에서 다룬 Phase 0=360 문제가 실전에서는 종종 "MAtricks+Phaser 조합이 아예 작동하지 않는다"는
증상으로 보고된다: 4×2 그리드에 red↔white 컬러 애니메이션 페이저를 걸고 `Phase 0→360` + `XBlock`을
적용했더니 위상 분산이 사라지고 모든 픽스처가 동일한 색으로 붙어버린 사례가 있다. 원인은 새로운 버그가
아니라 §2.2의 원 위상 겹침(0°=360°)이며, 해법은 동일하다(180도 미만으로 범위 지정, 또는 인코더 바로
자동 재계산 사용). 이 특정 재현 케이스는 v2.3.2.0에서는 정상 동작한다는 후속 모더레이터 확인이
있으므로, 버전에 따라 체감 정도가 다를 수 있다.

출처: [MAtricks not sticking (forum, strobie)](https://forum.malighting.com/forum/thread/69098-matricks-not-sticking/), [Phaser + MATricks not working as expected (forum, DanielK)](https://forum.malighting.com/forum/thread/5253-phaser-matricks-not-working-as-expected/)

---

## 6. RECIPES 안의 MAtricks

### 6.1 레시피란 무엇인가

> "A recipe contains one or multiple recipe lines describing what should happen based on a set of
> information."

레시피는 큐 파트·프리셋·프로그래머 안에 저장할 수 있는 "값 + MAtricks + 선택"의 템플릿 묶음이다.
투어링 쇼에서 공연장마다 리그 구성이 달라져도 같은 레시피를 재사용해 빠르게 적응하기 위한 도구다.

### 6.2 4단계 값 우선순위

레시피는 다음 우선순위(위가 더 높음)로 최종 출력값을 결정한다:

1. 큐 파트 값(Cue part values)
2. 큐 파트 레시피 값(Cue part recipe values)
3. 프리셋 값(Preset values)
4. 프리셋 레시피 값(Preset recipe values)

이 4단계 중 어트리뷰트별로 정확히 하나의 값만 최종 출력에 반영되도록 grandMA3 내부 플로우차트가
결정한다.

### 6.3 레시피 시트(Recipe Sheet)의 MAtricks "Grid" 컬럼

레시피 라인 하나하나는 레시피 시트에서 다음과 같은 열(column)로 표현된다 — 이 열들이 사실상 MAtricks
파라미터를 레시피 문맥에 노출한 것이다:

| 컬럼 | 내용 |
|---|---|
| Axis (X/Y/Z) | 그리드 좌표 |
| Fade From/To | 페이드 타임 분산 범위 |
| Delay From/To | 딜레이 분산 범위 |
| Speed From/To | 속도 분산 범위 |
| Phase From/To | 위상 분산 범위 |
| Group / Block / Wings | §2.1과 동일한 분배 규칙 |
| Transform | 그리드 설정 기반 미러링 활성화 |

레시피 라인은 프리셋을 참조하며(값 참조), 페이저는 **범위 값을 가진 템플릿 프리셋**으로서 레시피 라인에
그대로 통합된다 — 예: 페이저 프리셋의 레시피 라인에 Phase `0°→360°` 값을 얹는 패턴.

### 6.4 Recipe Editor 워크플로우 (4단계)

1. **Edit Recipe 모드 활성화** — Edit/Esc 버튼이 깜빡이는 것으로 표시
2. **그룹 선택** — 선택된 그룹은 초록 테두리로 표시
3. **프리셋 선택 후 MAtricks/Worlds/Filters 추가**
4. **큐/프리셋에 Store, 에디터 클리어**

풀 창(Pool window)은 편집 모드 동안 초록 화분 아이콘으로 표시되고, 현재 레시피와 호환되지 않는
프리셋은 회색으로 비활성 표시된다.

### 6.5 Recipe Preset — 프리셋 안에 레시피를 넣는 방법

일반 프리셋은 고정된 어트리뷰트 값만 담지만, **Recipe Preset**은 "레시피 라인"(값 참조 + MAtricks
그리드 설정 + 선택적 선택 범위)을 담는다. 라인을 추가하면 새 라인은 자동으로 **첫 라인의 MAtricks
값을 참조**해 여러 어트리뷰트 타입이 일관되게 동작하도록 조율된다.

**UI로 만들기**: 빈 프리셋 열기 → Swipey 메뉴 → Edit Setting → "Add Standard Recipe" → Values 필드에
참조할 프리셋 지정 → 추가 라인은 "Insert [selected object]" → MAtricks 파라미터 조정 → 필요 시 선택
범위 지정 또는 **Recipe Template** 모드 활성화. 이미 값이 있는 프리셋은 "Turn Into Recipe" 버튼으로
변환 가능.

**3가지 동작 모드**:

| 모드 | 동작 |
|---|---|
| 선택 있음 + Recipe Template 꺼짐 | 프리셋 참조가 고정된 픽스처 할당으로 "쿠킹"되어 프로그래머에 로드됨 |
| 선택 없음 + Recipe Template 꺼짐 | 프로그래머의 **현재 선택**에 동적으로 값이 적응 |
| Recipe Template 켜짐 | 레시피 라인이 활성 프로그래머 파트에 실시간 편집·쿠킹 가능한 상태로 로드됨 |

### 6.6 알려진 이슈 — Edit Recipe 모드에서 MAtricks 에디터가 회색으로 비활성화됨

v2.2.5.2 → v2.3.1.1 업그레이드 후 보고된 이슈(포럼): Edit Recipe 모드에서 (1) 프로그래머의 MAtricks가
사용자가 Clear를 누르지 않았는데도 자동으로 사라지고, (2) **MAtricks 에디터 자체가 회색으로
비활성화되어 레시피 편집 중에는 새 페이저를 만들 수 없다**(구 MA Tools 플러그인 시절에는 가능했던
워크플로우). 스레드 시점 기준 MA Lighting 공식 답변은 없고, 커뮤니티는 서드파티 플러그인(MA Tools)
채널로 문의를 안내하는 수준에 그쳤다 — **레시피를 편집하기 전에 MAtricks/페이저를 먼저 프로그래머에서
완성해 두는 순서**가 현재로선 실무 우회책이다.

또한 §2.4에서 언급한 "수동 적용과 레시피 라인 적용의 Invert 결과가 다르다"는 이슈도 동일 계열의
문제로, 레시피 문맥에서 MAtricks의 재계산 로직이 순수 프로그래머 문맥과 다르게 동작할 수 있음을
시사한다 — 레시피에 MAtricks를 심을 때는 라이브 픽스처로 반드시 결과를 재확인해야 한다.

출처: [Recipes (grandMA3 2.2 Help)](https://help.malighting.com/grandMA3/2.2/HTML/recipes.html), [Recipe Presets (grandMA3 2.4 Help)](https://help.malighting.com/grandMA3/2.4/HTML/presets_recipes.html), [Recipes QSG](https://help.malighting.com/grandMA3/2.2/HTML/qsg_recipes.html), [Recipe Editor](https://help.malighting.com/grandMA3/2.4/HTML/recipe-sheet.html), [MAtricks, phasers and edit recipe workflow (forum, littlelightingguy/Jomartin)](https://forum.malighting.com/forum/thread/69643-matricks-phasers-and-edit-recipe-workflow/), [Recipes, Invert Options and Phase in the MAtricks (forum, Miko)](https://forum.malighting.com/forum/thread/5298-recipes-invert-options-and-phase-in-the-matricks/), [Width and phases in recipes (forum)](https://forum.malighting.com/forum/thread/7661-width-and-phases-in-recipes/)

---

## 7. 커맨드라인 문법 종합 참조표

§3의 세부 문법을 한 곳에 모은 요약표.

| 목적 | 커맨드 |
|---|---|
| 프로퍼티 직접 세팅 | `Set Selection [N] MAtricks 'Property' Value` |
| 저장된 풀 아이템을 선택에 적용 | `Set Selection [N] MAtricks [Function] MAtricks [Name\|N]` |
| 풀에 현재 설정 저장 | `Store MAtricks [Name\|N]` |
| 호출 | `Call MAtricks N` |
| 이름 붙이기 | `Label MAtricks N "이름"` |
| 삭제 | `Delete MAtricks N` |
| 일시 비활성/활성/토글 | `Off Selection MAtricks` / `On Selection MAtricks`(대칭) / `Toggle Selection MAtricks` |
| 리셋 | `Reset Selection [N] MAtricks` |
| 큐/레시피 라인에 풀 아이템 연결 | `Assign MAtricks N At Sequence A Cue B Part C.D` |
| 큐 파트 MAtricks 참조 해제 | `Set Sequence A Cue B Part C.D Property "MAtricks" ""` |
| 프리셋에 현재 MAtricks도 함께 저장 | `Store Preset F.P /MAtricks` (단축 `/MA`) |

대표 프로퍼티명(축 접두어 `X`/`Y`/`Z` 공통 패턴): `Group`, `Block`, `Wing`(Wings), `Width`, `Shuffle`,
`Shift`, `FadeFrom`/`FadeTo`, `DelayFrom`/`DelayTo`, `SpeedFrom`/`SpeedTo`, `PhaseFrom`/`PhaseTo`,
`Invert`. 실제 문서/포럼에 등장한 표기는 `XWing`, `XWidth`, `XShuffle`, `PhaseFromX`, `PhaseToX`,
`SpeedFromX`처럼 **접두어(축) 위치가 프로퍼티에 따라 앞/뒤로 섞여 등장**하므로, 콘솔의 자동완성이나
인코더 바에서 실제 프로퍼티명을 먼저 확인한 뒤 스크립트/매크로에 반영하는 것이 안전하다.

출처: [MAtricks Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_matricks.html), [/MAtricks Option Keyword](https://help.malighting.com/grandMA3/2.1/HTML/ok_matricks.html), [Syntax for assigning MAtricks Pool Item to Recipe Line in Sequence (forum)](https://forum.malighting.com/forum/thread/8242-syntax-for-assigning-matricks-pool-item-to-recipe-line-in-sequence/)

---

## 8. MAtricks vs Phaser 에디터 — 언제 무엇을 쓸까

두 도구는 경쟁 관계가 아니라 **직교하는 두 축**(공간 분할 vs 시간 파형)을 담당하므로, "둘 중 하나만
써야 하는 상황"은 드물다. 다만 어느 쪽이 **일차 진입점**이 되어야 하는지는 목적에 따라 갈린다.

| 상황 | 1차 도구 | 이유 |
|---|---|---|
| 선택을 홀/짝, 좌/우, 앞/뒤로 쪼개고 싶다 | **MAtricks** (Group/Wings) | 페이저는 "누가 어떤 값을 갖는지"를 모르며, 그 배분은 MAtricks의 역할 |
| 좌우 대칭(미러) 룩이 필요하다 | **MAtricks** (Wings + Transform Mirror + InvertStyle) | Phaser Editor에는 대칭 전용 도구가 없음 — MAtricks의 Invert Options가 이 역할을 전담 |
| 2D/3D 그리드에서 행/열 단위로 순차 진행시키고 싶다 | **MAtricks** (Selection Grid 좌표 + PhaseFromX/ToX 공식) | 그리드 좌표 인식 자체가 Selection Grid+MAtricks의 영역(§4) |
| 사인파/톱니파/원형 등 부드러운 파형 궤적이 필요하다 | **Phaser Editor** | Accel/Decel·Transition·Select Form(01문서 §4.3)이 파형 성형 전담 |
| 스텝이 3개 이상인 복잡한 시퀀스(무지개 3색 체이스 등) | **Phaser Editor** | 스텝 추가·개별 스텝 타이밍 편집은 Phaser Editor의 영역 |
| 랜덤이지만 재현 가능한 배치가 필요하다 | **MAtricks** (Shuffle + 고정 시드) | 셔플은 선택 순서를 섞는 도구이며 페이저 파라미터가 아님 |
| 무대 어디에 있든 같은 모양을 그리는 "중심+오프셋" 이펙트 | **Phaser Editor** (상대(Relative) 스텝) | 02문서 §②의 상대 페이저 워크플로우 — MAtricks가 아니라 페이저의 절대/상대 스텝 구분이 담당 |

**실전 결론**: 대부분의 완성된 룩은 두 도구를 순서대로 조합한다 —
`선택 → (선택을 MAtricks로 분할: Group/Wings/Width) → (그 분할 위에 Phaser 파형 얹기: Phase/Speed/
Accel·Decel) → 결과를 프리셋/레시피에 저장(선택적으로 /MAtricks 포함)`. §5.1의 순서 함정을 피하려면
이 순서를 지키는 것이 중요하다.

출처: [MAtricks and Shuffle](https://help.malighting.com/grandMA3/2.3/HTML/matricks.html), [Grid Selection - MaTricks - Phaser (forum)](https://forum.malighting.com/forum/thread/69260-grid-selection-matricks-phaser/), `01-phaser-fundamentals.md`(본 저장소, 04·5.6절 교차 참조)

---

## 9. 프리셋이 MAtricks 설정을 참조할 수 있는가 — 결론: 그렇다

세 가지 방식으로 가능하다(강도 순):

1. **일반 프리셋 + `/MAtricks` 옵션 키워드**(§3.4) — 어트리뷰트 값과 함께 "현재 MAtricks 설정 스냅샷"을
   프리셋에 동결 저장. 가장 단순하지만, 다른 선택에 그 프리셋을 불러올 때 셀렉션 크기가 다르면 MAtricks
   재계산이 어색할 수 있다.
2. **Recipe Preset**(§6.5) — 값 참조 + MAtricks 그리드 설정 + 선택(옵션)을 레시피 라인으로 캡슐화.
   "선택 없음" 모드로 저장하면 어느 선택에 불러오든 동적으로 재적응하므로, 리그가 바뀌는 투어링
   상황에 가장 강건하다.
3. **MAtricks 풀 아이템을 레시피 라인에 `Assign`**(§3.3) — MAtricks 설정 자체를 독립 오브젝트로 재사용
   하면서, 특정 큐/레시피 라인이 그 풀 아이템을 참조하도록 연결. 프리셋의 어트리뷰트 값과 MAtricks
   설정을 완전히 분리해서 관리하고 싶을 때 적합.

주의점(§2.4, §6.6에서 이미 확인): (a) 여러 어트리뷰트에 서로 다른 MAtricks를 걸어 저장하면 롱프레스
Store 토글 또는 `/MAtricks` 옵션을 명시하지 않는 한 하나만 남을 수 있고, (b) 레시피 라인 문맥에서
Invert/Phase 재계산이 프로그래머 직접 조작과 다르게 동작하는 사례가 보고되어 있으므로 라이브 검증
없이 "프리셋에 저장했으니 항상 동일하게 재현된다"고 가정해서는 안 된다.

---

## 10. 이 저장소(server/fx)에 대한 시사점

`00-summary-and-plan.md` §2 G5("MAtricks Grid 서브선택 미지원 — 5축 phase/wings/shuffle만")를 이번
딥다이브로 다음과 같이 구체화할 수 있다:

- 현재 스키마(`server/fx/schema.py`)가 지원하는 5축(`phase_from_x`/`phase_to_x`/`x`/`x_wings`/
  `x_shuffle`)은 §2.1·§2.2의 **Group·Wings·Phase From/To·Shuffle**에 해당하고, **Block·Width·Shift·
  Y/Z축 전체·InvertStyle·Transform(Mirror)** 는 아직 미방출 상태다.
- §2.2에서 확인한 **Phase 0=360 겹침 함정**은 이 저장소의 페이저 빌더가 `phase_to_x=360`을 그대로
  방출하고 있다면 동일하게 재현될 가능성이 높다 — 값 방출 시 360 미만으로 클램프하거나, 인코더 바
  상대 재계산과 동등한 로직(개수 기반 나눗셈)을 빌더 쪽에서 흉내 내는 방향이 §4.2의 공식
  (`PhaseToX = 360/Y - 360/(X*Y)`)과 함께 검토할 만하다.
- §5.1의 "선택→페이저→MAtricks" 순서 함정은 이 저장소가 명령을 어떤 순서로 방출하는지
  (`server/fx/instantiate.py`)를 재검토할 근거가 된다 — 순서가 뒤바뀌어 있다면 라이브에서 "ok:true인데
  무효과"라는 이미 알려진 함정(00문서 §1.4 ①)의 또 다른 원인일 수 있다.
- Recipe Preset(§6.5)·풀 Assign(§3.3)은 이 저장소가 아직 다루지 않는 상위 레이어로, 향후 "리그가
  바뀌어도 재적응하는 이펙트 프리셋"을 만들고 싶다면 참고할 확장 방향이다.

이 항목들은 라이브 콘솔 실측 없이는 스키마/빌더에 반영하지 않는다는 저장소 원칙(`00-summary-and-plan.md`
§3 Phase 1)을 그대로 따른다 — 본 문서는 방향성 자료이며, 반영 여부는 온PC 라이브 검증 이후 결정한다.

---

## 11. 출처 목록 (전체)

**공식 문서 (help.malighting.com)**
- [MAtricks and Shuffle (2.3)](https://help.malighting.com/grandMA3/2.3/HTML/matricks.html)
- [MAtricks Groups (2.1)](https://help.malighting.com/grandMA3/2.1/HTML/matricks_group.html)
- [MAtricks Blocks (2.0)](https://help.malighting.com/grandMA3/2.0/HTML/matricks_block.html)
- [MAtricks Wings (2.0)](https://help.malighting.com/grandMA3/2.0/HTML/matricks_wings.html)
- [MAtricks Width (2.3)](https://help.malighting.com/grandMA3/2.3/HTML/matricks_width.html)
- [MAtricks Shuffle (2.0)](https://help.malighting.com/grandMA3/2.0/HTML/matricks_shuffle.html)
- [MAtricks Transform (2.3)](https://help.malighting.com/grandMA3/2.3/HTML/matricks_transform.html)
- [MAtricks Keyword (2.0)](https://help.malighting.com/grandMA3/2.0/HTML/keyword_matricks.html)
- [/MAtricks Option Keyword (2.1)](https://help.malighting.com/grandMA3/2.1/HTML/ok_matricks.html)
- [Recipes (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/recipes.html)
- [Recipes QSG (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/qsg_recipes.html)
- [Recipe Editor (2.4)](https://help.malighting.com/grandMA3/2.4/HTML/recipe-sheet.html)
- [Recipe Presets (2.4)](https://help.malighting.com/grandMA3/2.4/HTML/presets_recipes.html)
- [EditRecipe Keyword (2.2)](https://help.malighting.com/grandMA3/2.2/HTML/keyword_editrecipe.html)

**MA Lighting 포럼**
- [MAtricks, phasers and edit recipe workflow](https://forum.malighting.com/forum/thread/69643-matricks-phasers-and-edit-recipe-workflow/)
- [Recipes, Invert Options and Phase in the MAtricks](https://forum.malighting.com/forum/thread/5298-recipes-invert-options-and-phase-in-the-matricks/)
- [Grid Selection - MaTricks - Phaser](https://forum.malighting.com/forum/thread/69260-grid-selection-matricks-phaser/)
- [Phaser + MATricks not working as expected](https://forum.malighting.com/forum/thread/5253-phaser-matricks-not-working-as-expected/)
- [MAtricks not sticking](https://forum.malighting.com/forum/thread/69098-matricks-not-sticking/)
- [Modify selection order via MAtricks](https://forum.malighting.com/forum/thread/9084-modify-selection-order-via-matricks/)
- [Syntax for assigning MAtricks Pool Item to Recipe Line in Sequence](https://forum.malighting.com/forum/thread/8242-syntax-for-assigning-matricks-pool-item-to-recipe-line-in-sequence/)
- [is it possible to filter out MAtricks info saved in presets?](https://forum.malighting.com/forum/thread/8033-is-it-possible-to-filter-out-matricks-info-saved-in-presets/)
- [Inverting pan when doing wings?](https://forum.malighting.com/forum/thread/9235-inverting-pan-when-doing-wings/)
- [circle phaser in grid/layout](https://forum.malighting.com/forum/thread/7991-circle-phaser-in-grid-layout/)
- [Width and phases in recipes](https://forum.malighting.com/forum/thread/7661-width-and-phases-in-recipes/)
- [List variable??? (Set Selection MAtricks Lua 예시)](https://forum.malighting.com/forum/thread/68392-list-variable/)

**튜토리얼/2차 자료**
- [15: MAtricks | grandMA3 for grandMA2 Programmers — Consoletrainer (Cat West)](https://consoletrainer.com/15-matricks-grandma3-for-grandma2-programmers/)
- [DOING THE MATHEMATICS WITH GRANDMA3 — CX Network (Jason Allen, 2023-04-19)](https://www.cxnetwork.com.au/doing-the-mathematics-with-grandma3/)

**본 저장소 교차 참조**
- `docs/research/ma3-effects/00-summary-and-plan.md` §2 G5, §3 Phase 1
- `docs/research/ma3-effects/01-phaser-fundamentals.md` §5.6 (Grouping/Wings/Blocks 버전 이력), §5.7 (SpeedMaster)
- `docs/research/ma3-effects/02-pantilt-effects.md` §① 상대 페이저, MAtricks XWings/Phase 사용 레시피
- `docs/research/ma3-effects/03-color-dimmer-beam-effects.md` §6 Integration Grid/MAtricks 연동
- `docs/research/ma3-effects/04-programmatic-phasers.md` §1.1 MAtricks 커맨드라인, §3.4 미방출 축 갭 분석
