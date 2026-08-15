# 06. Recipe Editor 딥다이브 — 그룹/프리셋/MAtricks/페이저를 "값 없이" 연결하는 참조 레이어

리서치 태스크. grandMA3의 **Recipe(레시피)** — 셀렉션(그룹) + 프리셋 + MAtricks + 페이저
레퍼런스를 큐 파트나 프리셋 안에 "구운(baked) 값" 없이 조합해 넣는 기능 — 를
help.malighting.com(v2.x), MA Lighting 포럼, 서드파티 튜토리얼(Consoletrainer)에서 조사한다.
**핵심 발견**: Recipe는 grandMA2에는 없던 grandMA3 고유 개념으로("Recipes are new to us, and
they're also brand new to the OS" — Consoletrainer), 큐/프리셋에 **값 대신 "값을 어떻게
만들 것인가에 대한 지시문"**을 저장한다. 재료(그룹·프리셋·MAtricks)가 바뀌면 레시피를
다시 "쿠킹(cook)"해서 큐를 갱신할 수 있다 — 투어링 쇼처럼 리그가 자주 바뀌는 환경을 위해
설계된 기능이다.

---

## 1. Recipe란 무엇인가

### 1.1 정의

공식 매뉴얼은 레시피를 이렇게 정의한다:

> "A recipe contains one or multiple recipe lines describing what should happen based on
> a set of information." — [Recipes](https://help.malighting.com/grandMA3/2.2/HTML/recipes.html)

Quick Start Guide는 레시피 라인 하나가 담는 정보를 더 구체적으로 풀어준다:

> "A recipe line can contain a set of information. This often involves a selection of
> fixtures (possibly from a group), a set of values (often from a preset), and some
> information about how to apply the value to the fixtures."
> — [Recipes — Quick Start Guide](https://help.malighting.com/grandMA3/2.2/HTML/qsg_recipes.html)

즉 레시피 라인 하나는 최소 3요소로 구성된다:

1. **셀렉션(Selection)** — 어떤 픽스처에 적용할지 (그룹, 또는 프로그래머의 현재 선택)
2. **값(Values)** — 무엇을 적용할지 (보통 프리셋. 페이저 레시피면 페이저/Shape 레퍼런스)
3. **적용 방법(How)** — MAtricks, 필터, 페이드/딜레이/스피드/페이즈, 그리드 값 등

### 1.2 Recipe vs 구운 값(baked values) — 핵심 차이

레시피는 "쿠킹(cook)"되기 전까지는 값이 아니라 **지시문(instruction)**으로 남는다:

> "The cue part recipe needs to be cooked into the cue part." — Recast/Recipes 문서

쿠킹은 두 가지 방식이 있다 — `Merge`(기존 값 보존하며 병합)와 `Overwrite`(파괴적 덮어쓰기).
쿠킹된 결과는 **팟(pot) 아이콘**으로 표시되지만, 레시피 자체는 지워지지 않고 남아있다 —
언제든 다시 쿠킹해서 갱신할 수 있다는 뜻이다. 이것이 레시피의 핵심 가치다: 재료(그룹 멤버,
프리셋 내용)가 바뀌면 **큐를 하나하나 다시 프로그래밍하지 않고 레시피를 재쿠킹해서 전체를
갱신**할 수 있다.

Consoletrainer 튜토리얼은 이 목적을 다음과 같이 요약한다:

> "how to use these Recipe Presets in cues so that you don't end up with hard values"
> — [22: Recipe Presets | grandMA3 for grandMA2 Programmers](https://consoletrainer.com/22-recipe-presets-grandma3-for-grandma2-programmers/)

### 1.3 팟(pot) 아이콘 — 레시피 상태 표시

큐나 프리셋에 레시피가 들어있으면 작은 냄비(pot) 아이콘이 표시된다. 색으로 상태를 구분한다:

| 팟 아이콘 | 의미 |
|---|---|
| 초록(green) | 모든 레시피 라인이 유효함(cook 가능) |
| 빨강(red) | 하나 이상의 레시피 라인이 쿠킹 불가 상태(예: 참조하는 그룹이 비어있거나 프리셋이 선택에 적용 불가) |
| 열린 냄비(open pot) | Recipe Template — 아직 구체적 셀렉션 없이 값만 정의된 재사용용 틀 |

출처: [Recipe Editor](https://help.malighting.com/grandMA3/2.4/HTML/recipe-sheet.html) §상태 설명.

### 1.4 우선순위 — 값과 레시피가 같은 속성을 건드릴 때

같은 속성에 대해 "직접 저장된 값"과 "레시피에서 나온 값"이 충돌하면, 우선순위는:

```
큐 파트 직접 저장 값  >  큐 파트 레시피  >  프리셋 직접 저장 값  >  프리셋 레시피
```

(값이 명시적으로 저장돼 있으면 레시피보다 항상 우선한다 — 레시피는 "빈 곳을 채우는" 하위
레이어로 동작한다.)

### 1.5 레시피는 어디에 저장되나

- **큐 파트(Cue Part)** — 시퀀스 시트의 "Show Recipes" 마스크로 노출/편집
- **프리셋(Preset)** — 값이 하나도 없는 빈 프리셋만 레시피로 전환 가능 (§3 참조)
- **프로그래머(Programmer)** — `EditRecipe` 모드로 진입해 프로그래머 위에서 직접 편집

Cue Recipe에 대한 공식 설명:

> "Recipes should only be able to be added to cue PARTS, not to cues directly" —
> [Adding Cue Recipes](https://help.malighting.com/grandMA3/2.0/HTML/cue_recipe.html)에
> 대응하는 forum 정정 사항(포럼 스레드 `commands-for-new-recipe`).

---

## 2. Recipe 해부 — 레시피 라인이 가진 열(column)들

Recipe Editor 창의 컬럼 구조(및 큐/프리셋 시트에 "Show Recipes" 마스크로 노출되는 컬럼)는
다음과 같다. **일반(standard) 레시피는 초록 배경, 페이저(phaser) 레시피는 보라 배경**으로
구분되며 색이 있는 셀만 편집 가능하다.

| 컬럼 | 설명 |
|---|---|
| Selection | 어떤 그룹/픽스처에 적용할지. 탭&홀드하면 그룹 풀 드롭다운이 열림. 없는 그룹은 그 자리에서 "New"로 생성 가능 |
| Values | 적용할 프리셋(또는 페이저 레시피 링크, 또는 World 값). 탭&홀드로 "Edit Values" 팝업 |
| Shape (페이저 전용) | 기존 페이저 레시피를 참조 — 표준 레시피 라인을 기존 페이저 레시피에 추가할 때 이 컬럼에 연결 |
| MAtricks | 기존 MAtricks 풀 오브젝트 참조. 개별 값은 셀 우하단에 작게 표시 |
| Filter/World | 추가 제약 조건 / 월드 값 |
| Fade / Delay | 개별 페이드·딜레이 시간 (픽스처 단위로 오버라이드 가능) |
| Speed / Phase / Measure (페이저 전용) | 페이저 레시피에만 있는 열 — 속도, 위상, 스텝 비율 |
| Playback: NShot / Direction / Adaptive Measure·Width (페이저 전용) | 페이저 재생 방식 제어 |
| Grid | MAtricks 그리드 값(XWings, Fade From/To 등) |

2.4 버전에서 추가된 열: Step, Curve, Transition/Width/Acceleration (페이저 세부 파라미터).
출처: [Features 2.4](https://help.malighting.com/grandMA3/2.4/HTML/rn_features-2-4.html),
[Recipe Editor](https://help.malighting.com/grandMA3/2.4/HTML/recipe-sheet.html).

### 2.1 페이저 레시피 — 표준 레시피와의 관계

> "Phaser recipes are recipes that have 2 or more steps." — Recipe Editor 문서

즉 페이저 레시피는 일반 레시피의 특수 형태다: 스텝이 1개면 표준(초록) 레시피, 2개 이상이면
페이저(보라) 레시피로 취급된다. 이는 `04-programmatic-phasers.md` §1.1에서 확인한 "스텝 2개
이상이어야 페이저가 성립한다"는 원칙과 정확히 대응한다 — 명령줄 경로와 Recipe Editor 경로가
같은 최소 스텝 규칙을 공유한다.

표준 레시피 라인을 기존 페이저 레시피에 추가하려면, 값(Values) 셀을 탭&홀드해 "Edit Values"
팝업에서 그 페이저 레시피를 선택해 링크한다 — 이렇게 하면 새 표준 라인이 페이저의 한 스텝처럼
편입된다.

### 2.2 MAtricks와의 관계

MAtricks 컬럼은 **기존 MAtricks 풀 오브젝트에 대한 참조**다. 레시피 자체가 MAtricks 값을
품고 있는 게 아니라, MAtricks 풀 오브젝트를 가리키기만 한다 — 그래서 MAtricks 풀 오브젝트를
수정하면 그걸 참조하는 모든 레시피가 함께 갱신된다(재쿠킹 시). 이것도 "재료가 바뀌면 요리가
같이 바뀐다"는 레시피의 일관된 설계 철학이다.

---

## 3. Recipe Preset — 프리셋 자체를 레시피로 만들기

일반 프리셋은 속성값을 직접 담지만, **Recipe Preset**은 값 대신 레시피 라인을 담는다.

> "Recipes can only be added to presets that do not contain attribute values when using
> the user interface." — [Recipe Presets](https://help.malighting.com/grandMA3/2.2/HTML/presets_recipes.html)

즉 UI로는 **빈 프리셋만** 레시피로 전환할 수 있다(값이 이미 있으면 먼저 지워야 함).

### 3.1 동작 방식 — "프로그래머로 로드되는 게 아니다"

Recipe Preset이 다른 프리셋과 결정적으로 다른 점:

> "This recipe works with the programmers' current selection of fixtures. The recipe
> preset is not loaded into the programmer. Instead, the recipe value links and grid
> values are used with the current selection of fixtures to cook values directly to the
> programmer." — Recipe Presets 문서

일반 프리셋을 호출하면 그 값이 프로그래머로 들어가지만, Recipe Preset을 호출하면 **그 순간의
현재 선택(current selection)**에 대해 레시피가 즉석에서 쿠킹되어 프로그래머에 값으로 찍힌다.
이게 바로 "셀렉션 무관(selection-agnostic)" 동작의 근원이다 — 같은 Recipe Preset을 그룹 A에
호출하든 그룹 B에 호출하든, 그 순간의 선택 기준으로 다시 요리된다.

### 3.2 생성 절차 (UI)

1. 빈 프리셋을 열어 "Edit Preset Object" 팝업 접근
2. "Turn Into Recipe" 탭 — 빈 프리셋을 레시피 프리셋으로 전환
3. "Insert New Recipe"로 레시피 라인 추가
4. 프리셋 필드를 탭해서 Preset Pool에서 참조할 프리셋 선택
5. 그리드 값 설정(XWings, Fade From/To 등)
6. 에디터를 닫으면 — 그룹 선택이 포함된 경우 — 프리셋이 쿠킹됨

### 3.3 Recast — 참조 대상이 바뀌었을 때 갱신

> "This will recast the preset where it is referenced. This means that if attributes are
> added or deleted after the preset is used in cues, then the preset might need to be
> recast for the cues to reflect the new content." — Recipe Presets 문서

`Recast`는 레시피 자체를 다시 쓰는 명령이 아니라, **그 프리셋이 참조되고 있는 모든 곳**
(이미 쿠킹된 큐 등)을 프리셋의 최신 상태로 다시 반영시키는 명령이다. 레시피의 "재료가
바뀌면 요리를 다시 한다"는 철학이 프리셋 레벨까지 확장된 형태다.

---

## 4. Recipe Editor 워크플로우 — 창을 여는 법부터 스텝 추가까지

### 4.1 창 열기 / 진입

- 레시피 편집기 창 자체를 열려면: 큐/프리셋 시트에서 **Edit Recipe**를 탭하거나, At Overlay에서
  **Edit Recipes**를 활성화
- 새 레시피를 만들려면: **New Recipe** 셀을 탭&홀드하거나, 셀을 선택 후 좌상단 `+` 탭
- 컨텍스트 영역의 전용 버튼으로도 추가 가능: **Add Standard Recipe** / **Add Phaser Recipe**

### 4.2 시퀀스 시트에서의 최소 흐름 (Quick Start Guide 예제)

1. 시퀀스를 만들고 픽스처(예: 201, 202)를 선택해 그룹으로 저장
2. 시퀀스 시트에서 "New Recipe"를 우클릭(또는 탭&홀드)
3. Selection 컬럼을 우클릭해 방금 만든 그룹을 선택
4. Values 필드를 우클릭해 색상 프리셋 등을 선택
5. 디머·포지션 등 다른 속성에 대해 추가 레시피 라인을 더 만듦
6. Fade/Delay 컬럼에서 픽스처별 타이밍을 조정

이 흐름이 만들어낸 결과를 명령줄로 재현/보완하는 두 명령:

```
Cook Sequence 6              # 레시피 데이터를 큐로 수동 쿠킹 (Merge/Overwrite 선택 가능)
Store Cue 1 /Remove          # 직접 저장된 값만 제거하고 레시피 참조만 남김
```

출처: [Recipes — Quick Start Guide](https://help.malighting.com/grandMA3/2.2/HTML/qsg_recipes.html).

### 4.3 페이저 레시피 만들기 (Recipe Editor 안에서)

1. Recipe Editor 열기
2. **Add Phaser Recipe** 탭
3. 첫 스텝에 셀렉션과 값을 채움
4. 페이저 레시피 아래 **New Step**(2.4 이후는 **Insert Step**) 탭해 스텝 추가 — 이후 스텝은
   이전 스텝의 값을 상속한 채로 시작
5. Speed/Phase/Measure, Playback(NShot/Direction/Adaptive Measure·Width) 컬럼에서 페이저
   전용 파라미터 조정

### 4.4 2.4 버전에서 강화된 편집기

2.4는 Recipe Editor에 하단 컨텍스트 영역(Pool/Sheet/Editor 3탭), 7개 빠른 액션 버튼(Add
Programmer Part / Add Standard Recipe / Add Phaser Recipe / Insert Step / Add Value Source /
Adjust Shape / Adjust MAtricks), 잘라내기/복사/붙여넣기 툴바, "Auto Focus to Next Cell"
설정, "Group by Attribute"(속성별로 레시피 라인을 묶어 접이식 스텝 헤더로 표시)를 추가했다.
Recipe Template도 이제 표준 레시피의 Values 컬럼 값으로 지정할 수 있게 됐다.
출처: [Features 2.4](https://help.malighting.com/grandMA3/2.4/HTML/rn_features-2-4.html).

---

## 5. 명령줄 문법 후보 — Assign / Store / Label / EditRecipe / Cook

> ⚠️ 이 절의 명령들은 **공식 매뉴얼 키워드 페이지 + MA Lighting 포럼(스태프·경험자 답변)**에서
> 수집한 것으로, `04-programmatic-phasers.md`의 페이저 명령줄 문법과 달리 **이 저장소에서
> onPC 라이브로 재검증되지 않았다.** 실제 파이프라인에 편입하기 전에는 §7의 원칙대로 콘솔
> 실측이 필요하다.

### 5.1 EditRecipe — 레시피 편집 모드 진입 (공식 키워드)

```
EditRecipe                          # 레시피 편집기 활성화(포커스된 대상 기준)
EditRecipe Cue 1                    # 큐 1의 레시피 편집 모드
EditRecipe 1                        # (동일, 축약)
EditRecipe Preset 2.2               # 프리셋 풀 2번, 2번 위치의 레시피 편집
EditRecipe Sequence 1               # 시퀀스 1의 현재 실행 중인 큐 레시피 편집
EditRecipe Page 1.204               # 실행기 204(1페이지)의 현재 큐 레시피 편집
```

MA + Edit 키 조합, 또는 타이핑 `EditRecipe`(축약 `Editr`)로도 진입 가능.
출처: [EditRecipe Keyword](https://help.malighting.com/grandMA3/2.2/HTML/keyword_editrecipe.html).

### 5.2 새 레시피 라인 생성 + 셀렉션 할당 (포럼 검증 패턴)

포럼 스레드 `assign-group-at-recipe-in-command-line`(julien.grandma 질문)이 제시한 패턴 —
먼저 `Store`로 빈 레시피 라인 자리를 만들고, `Assign`으로 그룹을 채운다:

```
# 1) 레시피 라인 생성 (대상별로 문법이 다름)
Store Preset x.y.z              # 프리셋 x번 풀, y번 위치, z번 레시피 라인
Store Cue x Part y.z            # 큐 x, 파트 y, z번 레시피 라인
Store Programmer y.z            # 프로그래머 파트 y, z번 레시피 라인

# 2) 그룹(셀렉션)을 그 레시피 라인에 할당
Assign Group a At Preset x.y.z
Assign Group a At Cue x Part y.z
Assign Group a At Programmer y.z

# 여러 프리셋에 한 번에: 덧셈/범위 연산자 지원
Assign Group 1 At Preset 2 + 4 + 21.1 Thru 5.1
```

### 5.3 저장 + 라벨링을 한 번에 (스레드 `store-and-label-recipe-in-a-cue`)

사용자 Morganevans가 "방금 만든 레시피의 변수 번호를 모르는 문제"를 질문했고, MA 스태프
Andreas가 답한 패턴:

```
Store Part 0."myBrandNewRecipe"              # Cue/Merge 키워드 없이 — 현재 큐에 새 레시피 추가
Assign Group 1 At Part 0."myBrandNewRecipe"
Label Part 0."myBrandNewRecipe" "myRecipe"
```

**중요 제약** (Morganevans 확인): 레시피 파트 이름에 **숫자만으로는 참조할 수 없고 반드시
문자를 포함해야 한다.**

### 5.4 시퀀스 전체 큐의 레시피 셀렉션 일괄 변경 (스레드 `change-recipe-selection-in-a-sequence-via-cli`)

```
Assign Group 2 at seq 151 cue 1 thru 5 part thru.1     # 특정 시퀀스, 큐 범위 지정
Assign group 2 at Cue 1 thru part *.*                   # 선택된 시퀀스의 모든 큐/파트 (와일드카드)
Assign group 2 at Cue 1 thru 13 part thru.1             # 와일드카드가 프리셋을 날리는 버전(1.9.3.1)이 있어 우회한 명시적 범위
```

⚠️ `cue 1 thru`(끝을 안 정함) 형태는 **Off Cue에도 영향**을 준다는 지적이 있음 — 정확한 큐
범위를 명시하는 편이 안전.

### 5.5 페이저 레시피 스텝 값 설정 (스레드 `commands-for-new-recipe`)

```
# 프리셋 안의 페이저 레시피 스텝에 프리셋 할당
Assign Preset 1.1 At Preset 21.1.1."PhaserRecipeSteps".1.1

# 시퀀스 큐 안의 페이저 레시피 스텝에 프리셋 할당
Assign Preset 1.1 At Sequence 1 Cue 1 Part 0.1."PhaserRecipeSteps".1.1

# Shape(형태) 오브젝트 안의 페이저 레시피 스텝에 프리셋 할당
Assign Preset 1.1 At Shape 1.1."PhaserRecipeSteps".1.1

# 페이저 레시피에 Shape를 연결 (Shape 프로퍼티)
Assign Shape 11 At Preset 22.1.1 Property "Shape"
Assign Shape 1 At Sequence 1 Cue 1 Part 0.1 Property "Shape"

# 페이저 재생 방식 (NShot/Direction)
Set Preset 21.1.1 Property "PlaybackNShot" 10
Set Preset 21.1.1 Property "PlaybackDirection" "Forward"

# 스텝 값을 절대값으로 지정
Set Sequence 1 Cue 1 Part 0.1."PhaserRecipeSteps".1.1 Property "ValueAbsolute" 100

# Phase 스왑 (모더레이터 Ryan Kanarek 추가 답변)
Set Sequence 101 Cue 2 Part 0.1 Property "PhaseFromX" "Swap Phase"
```

2.4에서 새로 추가된 명령줄 키워드: `NShot` — `At NShot [number]`로 페이저 사이클 수를 직접
지정 가능 ([Features 2.4](https://help.malighting.com/grandMA3/2.4/HTML/rn_features-2-4.html)).

### 5.6 쿠킹 명령 (Cook)

```
Cook [object] (/option)
```

옵션: `Merge`(기본값 — 기존 값 보존하며 병합) / `MergeLowPriority` / `Overwrite`(파괴적) /
`Remove`. 예: `Cook Sequence 6`.

### 5.7 정리(CleanUp)의 `/Recipe` 옵션 키워드 — Store/Assign이 아니라 CleanUp 전용

여기서 한 가지 함정: `/Recipe`(축약 `/Rec`) 옵션 키워드는 **`Store`나 `Assign`에 붙는 게
아니라 `CleanUp` 명령 전용**이다. `Type "Recipe"`와 함께 써야 하며, 목적은 저장이 아니라
**쓸모없어진 레시피를 골라 삭제**하는 것이다:

```
CleanUp [Object] ["Object_Name" or Object_Number] /Type "Recipe" (/Recipe "Recipe_Value")
```

`/Recipe` 값:

| 값 | 의미 |
|---|---|
| `NoOutput` (기본값) | 출력을 만들지 않는 레시피 삭제 (`NotCooked` + `CookedButOverwritten`의 합) |
| `NotCooked` | 참조한 프리셋이 선택에 적용 불가하거나, 참조한 그룹이 비어서 쿠킹 자체가 안 된 레시피 |
| `CookedButOverwritten` | 쿠킹은 성공했지만 이후 다른 레시피에 덮어써져 결과적으로 출력에 안 잡히는 레시피 |

출처: [/Recipe Option Keyword](https://help.malighting.com/grandMA3/2.2/HTML/ok_recipe.html).

---

## 6. Recipe vs 구운 값(baked values) — 트레이드오프

| 축 | Recipe (참조) | 구운 값 (Baked) |
|---|---|---|
| **리그 변경 대응** | 그룹/프리셋을 갱신 후 재쿠킹(Cook/Recast)하면 관련 큐 전체가 따라 바뀜 | 큐마다 수동으로 다시 프로그래밍해야 함 |
| **셀렉션 무관성** | Recipe Preset은 호출 시점의 현재 선택 기준으로 즉석 쿠킹 — 그룹 A/B에 재사용 가능 | 저장 당시 선택된 픽스처에 고정 |
| **예측 가능성** | "지금 이 순간" 쿠킹 결과가 참조 대상 상태에 의존 — 참조가 깨지면(그룹 비어있음 등) 빨간 팟(쿠킹 불가) | 저장된 그대로 항상 동일하게 재생 — 참조 깨짐이 원천적으로 없음 |
| **디버깅 난이도** | 레이어가 하나 더 있음(레시피→쿠킹→출력) — 우선순위 규칙(§1.4)을 알아야 함 | 큐를 보면 값이 그대로 보임 — 직관적 |
| **투어링/대형 쇼 적합성** | 높음 — 리그가 바뀌는 순회 공연, 다중 콘솔 협업에서 "한 곳만 고치면 전체 갱신" | 낮음 — 리그 변경마다 재프로그래밍 부담 |
| **일회성 룩** | 과함 — 레시피 레이어를 유지관리할 이유가 없음 | 적합 — 바로 저장하고 끝 |
| **기계적 상태 확인** | 팟 아이콘(초록/빨강/열림)으로 유효성 확인 가능 — 단 "레시피가 존재한다"와 "출력이 기대한 대로 나온다"는 별개 질문 | 저장된 값 자체가 진실 — read-back이 곧 검증 |

---

## 7. 언제 Recipe가 맞는 도구인가 — 의사결정 가이드

### 7.1 Recipe를 쓰기 좋은 상황

- **같은 룩을 여러 그룹/여러 큐에서 재사용하되, 원본 프리셋이 업데이트되면 전부 같이 갱신되길
  원할 때** — 예: "Cyan Wash"라는 프리셋을 여러 큐가 참조하다가, 색을 조금 조정하면 참조하는
  모든 큐가 재쿠킹만으로 따라옴
- **투어링 쇼처럼 리그(픽스처 배치, 그룹 구성)가 공연마다 바뀌는 경우** — 그룹만 새로 짜고
  레시피를 재쿠킹하면 큐 전체가 새 리그에 맞춰짐
- **셀렉션 무관 이펙트가 필요할 때** — Recipe Preset을 호출 시점의 현재 선택에 대해 즉석
  쿠킹하도록 설계하면, 같은 페이저/컬러 레시피를 그룹 A에도 그룹 B에도 그대로 재사용 가능
  (단 §7.3의 포지션 함정 주의)
- **대형 쇼에서 여러 프로그래머가 협업할 때** — "이 프리셋을 고치면 관련된 모든 큐가
  자동으로 갱신 대상이 된다"는 성질이 분업에 유리

### 7.2 Phaser Editor(또는 직접 프로그래머 값)가 더 나은 상황

- **한 번만 쓰는 특정 순간의 룩** — 레시피 레이어를 유지관리할 이유가 없으면 그냥 구워서
  저장하는 편이 단순하고 예측 가능
- **정확한 포지션(Pan/Tilt) 값이 핵심인 이펙트** — §7.3 참조. 포지션은 본질적으로
  픽스처별 고유값(selective)이라 "셀렉션 무관 유니버설 레시피"로 만들기 어렵다
- **페이저의 세부 파라미터(Speed/Phase/Width/Measure/Accel/Decel)를 시각적으로 다듬어야
  할 때** — Phaser Editor는 "그래픽 뷰와 강력한 조작"을 위한 전용 도구로, 스텝 정보를
  2D/1D로 보여주고 모든 페이저 레이어(속도/위상/측정/폭/트랜지션/가속/감속)를 편집하게
  해준다. Recipe Editor는 "레시피 라인의 구조(무엇을 참조하는가)"를 다루고, Phaser Editor는
  "이미 만들어진 페이저의 움직임 파라미터(어떻게 변화하는가)"를 다룬다 — 목적이 다르다
- **기계적으로 결과를 검증해야 하는 자동화 파이프라인** (이 저장소의 맥락) — 레시피는
  "레시피가 유효하다(초록 팟)"까지만 기계적으로 확인 가능하고, "출력이 기대한 룩과
  일치한다"는 이 저장소가 이미 겪은 함정(`04-programmatic-phasers.md` §1.3 함정 3, 사람
  관측 필요)과 동일하게 별도 검증이 필요하다. 오히려 **구운 값 + `run_commands`로 즉시
  실행**하는 현재 파이프라인이 "저장 즉시 검증 가능"이라는 면에서 더 단순한 신뢰 모델을
  갖는다

### 7.3 알려진 함정 — "셀렉션 무관 유니버설 레시피"는 포지션에서 특히 어렵다

포럼 스레드 `how-to-create-recipe-friendly-position-phasers`(UnfundedFish)가 보고한 문제:
포지션 프리셋을 페이저 레시피에 넣으면 항상 "selective"(픽스처별 고유값)로 저장되어, 다른
그룹에 재사용할 수 없게 된다. 커뮤니티가 제시한 우회책:

- **Universal 모드 포지션 프리셋** — 단, Home/Straight/Left/Right/Up 같은 "일반적(generic)"
  포지션에만 통함. Bentoylight: "positions are selective : when you point at the center of
  the stage, any fixture has unique value." (무대 중앙을 조준하는 값은 픽스처마다 다르므로
  본질적으로 유니버설이 될 수 없다)
- **상대(Relative) 포지션 페이저** — MA스타트쇼의 서클 페이저처럼 절대 좌표가 아니라 상대
  오프셋을 쓰면 재사용성이 올라갈 수 있음(Melchsteffen 제안, 미검증)
- **프리셋 풀 자체를 Universal로 설정** — 풀 메뉴에서 기본 저장 모드를 바꿔보라는 제안
  (Darnold74112)

값 컬럼에서 `<From Value>`를 선택하면 "그 값(프리셋)이 지정된 모든 픽스처"를 셀렉션으로
자동 채우는 방식으로 재사용성을 높이려는 시도도 있으나, 실제로는 "포지션 프리셋이 결합되면
유니버설+셀렉티브가 뒤섞여 복잡해진다"는 한계가 보고됐다(스레드
`universal-recipe-phaser-presets-without-selective`).

**결론**: 색상/디머처럼 값이 그룹 전체에 동일하게 적용되는 속성은 레시피로 셀렉션 무관 재사용이
잘 되지만, **포지션(Pan/Tilt)처럼 픽스처마다 고유해야 하는 속성은 레시피의 재사용성 이점이
약하다** — 이 경우 애초에 매번 새로 프로그래밍하거나(구운 값), 상대 오프셋 방식의 페이저를
따로 설계하는 편이 낫다.

### 7.4 이 저장소(`server/fx/`)와의 관계 — 지금 당장 채택 여부

이 저장소는 현재 §7.2에서 설명한 "구운 값 + `run_commands` 즉시 실행" 모델을 채택하고 있고
(`04-programmatic-phasers.md` §3), 아직 Recipe/Recipe Preset 경로를 사용하지 않는다. 이는
의도적 선택이라기보다는 다음 이유로 지금까지 필요가 없었던 것으로 보인다:

- 이 시스템은 라이브 쇼 진행 중 리그가 바뀌는 투어링 워크플로우가 아니라, AI가 그때그때
  요청받은 룩을 만들어 저장하는 "온디맨드 생성" 워크플로우다 — 레시피의 핵심 가치(재료
  변경 시 일괄 갱신)가 아직 절실하지 않다
- `find_fx`/`instantiate_fx`가 이미 "라이브러리 → 스키마 검증 → 명령줄 조립 → 즉시 실행"의
  단일 경로를 갖고 있어, Recipe의 참조 레이어를 추가하면 검증해야 할 상태(레시피 유효성 +
  쿠킹 결과)가 하나 더 늘어난다 — `verification-claim-integrity.md`의 "기계 검증 없는 주장
  금지" 원칙과 마찰이 생긴다(레시피가 초록 팟이어도 출력이 기대와 다를 수 있음)

향후 "같은 룩을 여러 그룹에 반복 적용하고 나중에 일괄 수정해야 하는" 요구가 생기면(예:
여러 무빙헤드 그룹에 공통 컬러 팔레트를 걸고 나중에 팔레트만 바꾸는 시나리오) Recipe
Preset 경로가 후보가 될 수 있다 — 단, §7.3의 포지션 함정 때문에 색상/디머 계열부터
시작하는 것이 안전하다.

---

## 요약

| 질문 | 답 |
|---|---|
| Recipe란? | 그룹(셀렉션) + 프리셋(값) + MAtricks/페이저 참조를, 값을 굽지 않고 큐 파트/프리셋에 저장하는 지시문. `Cook`으로 실제 값으로 변환 (§1) |
| 페이저 레시피와 표준 레시피의 차이? | 스텝 2개 이상이면 페이저(보라), 1개면 표준(초록) — `04` 문서의 최소 스텝 규칙과 동일 원리 (§2.1) |
| Recipe Preset의 특별한 점? | 프로그래머로 로드되지 않고, 호출 시점의 "현재 선택"에 즉석 쿠킹됨 — 셀렉션 무관 재사용의 근원 (§3.1) |
| 명령줄로 만들 수 있는가? | 가능 — `EditRecipe`(공식 키워드) + `Store`/`Assign`/`Label`/`Set …Property`(포럼 검증, 이 저장소 미검증) 조합 (§5) |
| 언제 쓰는 게 맞는가? | 재료(그룹/프리셋)가 바뀔 때 큐 전체를 일괄 갱신해야 하는 투어링/대형 협업 상황, 색상·디머처럼 유니버설하게 재사용 가능한 속성. 일회성 룩이나 포지션처럼 픽스처별 고유값이 필요한 경우는 구운 값(Phaser Editor/직접 프로그래머)이 더 단순하고 안전 (§6, §7) |
| 이 저장소는 채택했는가? | 아니오 — 현재는 구운 값 + `run_commands` 즉시 실행 모델. 레시피는 검증 부담(레시피 유효성 ≠ 출력 정확성)을 하나 더 얹으므로, 반복 갱신 요구가 생기기 전까지는 후순위 (§7.4) |

---

## Sources

- [Recipes](https://help.malighting.com/grandMA3/2.2/HTML/recipes.html) — 레시피 정의, 쿠킹, 팟 아이콘, 우선순위
- [Recipes — Quick Start Guide](https://help.malighting.com/grandMA3/2.2/HTML/qsg_recipes.html) — 최소 워크플로우 예제, `Cook`/`Store …/Remove` 명령
- [Recipe Presets](https://help.malighting.com/grandMA3/2.2/HTML/presets_recipes.html) — Recipe Preset 정의, 즉석 쿠킹 동작, Recast
- [Recipe Editor](https://help.malighting.com/grandMA3/2.4/HTML/recipe-sheet.html) — 편집기 창, 컬럼, 표준/페이저 색 구분, 스텝 추가
- [Adding Cue Recipes](https://help.malighting.com/grandMA3/2.0/HTML/cue_recipe.html) — 큐 파트 레시피, Show Recipes 마스크, `Cook` 옵션
- [/Recipe Option Keyword](https://help.malighting.com/grandMA3/2.2/HTML/ok_recipe.html) — `CleanUp …/Type "Recipe" /Recipe` 정리 명령
- [EditRecipe Keyword](https://help.malighting.com/grandMA3/2.2/HTML/keyword_editrecipe.html) — 레시피 편집 모드 진입 명령 문법
- [Features 2.4](https://help.malighting.com/grandMA3/2.4/HTML/rn_features-2-4.html) — 2.4 페이저 레시피, 편집기 강화, `NShot` 키워드
- [Phasers](https://help.malighting.com/grandMA3/2.0/HTML/phaser.html) — 페이저 정의, Phaser Editor 도구 설명
- [22: Recipe Presets | grandMA3 for grandMA2 Programmers — Consoletrainer](https://consoletrainer.com/22-recipe-presets-grandma3-for-grandma2-programmers/) — grandMA2 대비 레시피의 존재 이유, 실전 튜토리얼 개요
- [Commands for new Recipe — MA Lighting Forum](https://forum.malighting.com/forum/thread/69919-commands-for-new-recipe/) — 페이저 레시피 스텝 `Assign`/`Set …Property` 명령 예시
- [Assign "Group" at Recipe in command line — MA Lighting Forum](https://forum.malighting.com/forum/thread/4782-assign-group-at-recipe-in-command-line/) — `Store`+`Assign`으로 레시피 라인 생성
- [Store and Label Recipe in a Cue — MA Lighting Forum](https://forum.malighting.com/forum/thread/7845-store-and-label-recipe-in-a-cue/) — 저장+라벨링 패턴, 숫자만으론 참조 불가 제약
- [Change Recipe "Selection" in a Sequence via CLI — MA Lighting Forum](https://forum.malighting.com/forum/thread/8522-change-recipe-selection-in-a-sequence-via-cli/) — 시퀀스 전체 큐 셀렉션 일괄 변경, 와일드카드 주의
- [How To Create Recipe Friendly Position Phasers — MA Lighting Forum](https://forum.malighting.com/forum/thread/68367-how-to-create-recipe-friendly-position-phasers/) — 포지션 레시피의 유니버설화 한계와 우회책
- [Universal Recipe Phaser Presets without selective — MA Lighting Forum](https://forum.malighting.com/forum/thread/69925-universal-recipe-phaser-presets-without-selective/) — `<From Value>` 셀렉션 및 한계
