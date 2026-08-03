# SPEC-COPILOT-GROUPGEN-001 — 사전 조사 (research)

status: **pre-plan (킥오프 브리프) v0.5.0** · 2026-08-03 · `/moai plan` 미실행

> **성격.** plan-phase 전 **인계용 조사 기록**이다. `spec.md` · `acceptance.md` · `design.md`는 아직 없다.
> 여기 담긴 `[실측]`은 라이브 onPC 2.4.2 직접 관측이며 **다시 재기 전에는 복구할 수 없는 정보**다.
> plan-phase는 이 문서를 확장하되 실측값을 추측으로 대체하지 않는다.
>
> 근거 등급: `[실측]` · `[코드]` · `[문서]` · `[미확정]`
>
> **v0.2.0 개정**: 요구가 정정되었다(§1). 고정 사상표(3행→Front/Center/Back)가 아니라
> **배치의 위상(topology)을 판별해 그에 맞는 어휘로 이름을 붙이는 것**이 목적이다.
> 이 정정으로 SPEC의 중심이 "그룹 쓰기"에서 **"위상 분류"**로 이동했다(§3 신설).

---

## §1. 요구 (사용자 정정 반영)

> *"장비를 배치하면 자동으로 배치에 맞게 그룹을 설정하는 게 목적이야. **반드시 각 열을 Front, Center,
> Back 그룹으로 설정하라는 게 아니야.** 2겹의 원형이면 Inner, Outer, 좌우로 배치되면 Left, Right 등과
> 같이 **배치되는 특성에 맞게** 그룹을 잡고 라벨을 설정해달라는 거야."*

### §1.1 요구의 핵심 — 이름이 아니라 판별이다

Front/Center/Back은 **하나의 예시**일 뿐이다. 요구되는 것은:

1. **배치의 구조적 성격을 판별한다** — 깊이 방향 행인가, 동심원인가, 좌우 분할인가, 수직 층인가
2. **그 성격에 맞는 어휘를 고른다** — 행→Front/Center/Back · 동심원→Inner/Outer · 좌우→Left/Right
3. **그룹으로 저장하고 라벨을 붙인다** — 연출·이펙트가 바로 쓸 수 있게

즉 **위상 분류(topology classification)가 이 SPEC의 중심**이고, 그룹 쓰기는 그 결과의 출력이다.
v0.1.0은 이 관계를 거꾸로 봤다.

### §1.2 왜 그룹으로 굳히는가

SPATIAL-001의 **선택 순서는 프로그래머 상태**다 — `ClearAll`로 사라지고 매 발화가 다시 세운다.
웨이브 *방향*에는 충분하나 *"뒷줄만 파랗게"* · *"바깥 링만 반짝"* 은 표현할 수 없다.
그룹은 **쇼파일에 영속**하므로 앱이 `Group <n>` 한 줄로 부분 리그를 잡고, **사용자가 콘솔에서 손으로도**
쓴다. 선택 순서와 그룹은 경쟁이 아니라 보완이다 — **그룹 = 누구, 선택 순서 = 어떤 순서로.**

## §2. ⚠ 최우선 발견 — 그룹 멤버십을 읽을 수 없다 `[실측]`

| 대상 | `query_state` 결과 | `exec` 결과 |
|---|---|---|
| `DataPool/Groups/13` (`'All'`) | `childCount: 0` · `children: []` | `Group 13` → **`executed_ok`** |
| `DataPool/Groups/1` (`'Copilot Grp'`) | `childCount: 0` · `children: []` | — |
| `DataPool/Groups/11` (`'Back'`) | `childCount: 0` · `children: []` | — |

`'All'`이 실행되는 실사용 그룹인데 `childCount: 0`이다. → **그룹 멤버십은 오브젝트 트리 경로로
노출되지 않는다.** `childCount: 0`은 *"비었다"*가 아니라 *"이 채널로는 안 보인다"*다.

### §2.1 이것이 만드는 3중 잠금

1. **재조회 검증 불가** — 저장소 최상위 규율은 *"`ok`는 증거가 아니다, 재조회만이 증거"*다
   (SCENE M0 `/CueOnlyy` · SPATIAL 음수 좌표 3형태가 `OK`+틀린 값). 그룹에는 **그 규율을 적용할
   채널이 아직 없다.**
2. **백업 불가** — 멤버십을 읽을 수 없으므로 덮어쓰기 전 원본을 보관할 수 없다.
   SPATIAL의 WRITE 안전 설계(원좌표 백업 → 기록 → 재조회 → 복원 번들)가 **그대로 이식되지 않는다.**
3. **복구 불가** — `Delete`는 블랙리스트, showfile restore SEND 경로 부재(T-B2).

→ **점유 슬롯 덮어쓰기는 백업도 복구도 불가능하다.** 이는 선호가 아니라 **강제 제약**이다:
설계는 점유 슬롯 기록을 **정적으로 차단**해야 한다.

→ **M0의 최우선 과제는 멤버십 검증 채널 탐색이며, 그 결과가 SPEC 전체의 GO/NO-GO다**(plan.md §A.2).

## §3. ⚠ 두 번째 발견 — 현재 분석 계층은 행이 아닌 위상을 고신뢰로 오독한다 `[실측]`

`server/spatial/rows.py`는 **y축 갭 클러스터링 하나만** 한다. 2겹 동심원(내륜 6대 r=2.0 · 외륜 12대 r=5.0)을
넣은 결과:

```
rows = 9 · 구성 [1, 2, 2, 2, 4, 2, 2, 2, 1] · low_confidence = False
```

**무의미한 9행을 고신뢰로 단정한다.** 같은 데이터의 반지름 분포는 `2.0`×6 / `5.0`×12로 **완벽히 갈린다** —
극좌표에서는 자명하고 y축 갭에서는 보이지 않는다.

### §3.1 이것이 뜻하는 것

- 현재 계층은 **"행"이라는 단 하나의 위상 가설**을 갖고 모든 리그에 적용한다.
- 가설이 틀린 리그에서 **저신뢰 신호도 뜨지 않는다** — 갭이 실제로 존재하기 때문이다(원주 위 y값들).
- SPATIAL의 `vertical_span`(§E.2.18)은 z를 **측정만 하고 쓰지 않는다**고 명시했다. 이제 요구가
  수직 층(Low/Mid/High)을 포함하므로 **그 필드가 분류의 입력으로 승격**된다.
- `arrange_fixtures`는 이미 `circle`(orientation `xy`/`xz`)을 **쓸 수 있다.** 즉 **WRITE는 만들 수 있고
  READ는 분류할 수 없는 비대칭**이 존재한다. 이 SPEC이 그 비대칭을 메운다.

## §4. 선행 자산

**의존: SPEC-COPILOT-SPATIAL-001 (미머지).** 본 브랜치는 `feature/SPEC-COPILOT-SPATIAL-001`
(`115eb6d`)에서 분기했다 — `server/spatial/`이 main에 없다. **머지되면 rebase할 것.**

| 자산 | 위치 | 이 SPEC의 사용 |
|---|---|---|
| 행 검출 | `server/spatial/rows.py` | **위상 후보 1종**으로 편입(대체 아님) |
| `SpatialRow.fids` | `schema.py` | `(x, fid)` 오름차순 — 행 멤버십 |
| `vertical_span` | `schema.py` | z 층 분류의 입력으로 **승격** |
| 프리셋 기하 | `presets.py` | `circle`/`grid`/`row` — 위상 golden 생성기로 재사용 |
| 선택 사슬 조립 | `choreography.py::build_spatial_selection_chain` | `Store Group` 앞의 선택 발화 |
| **빈 슬롯 실측 선례** | `server/scene/compile.py::_select_cue_number` | 아래 §4.1 |
| 역할 해석기 | `server/looks/resolver.py` | 신규 이름이 기존 6역할 해석과 충돌하는지 검사 대상 |
| 그룹 문법 | `00_grammar.md:66` | `Fixture 101 Thru 110` → `Store Group 7` → `Label Group 7 'Vocals'` `[문서]` — **"(validated)" 표기 없음** |

### §4.1 승계할 선례 — 절단 시 거부

`_select_cue_number` `[코드]`:

> *"the cue pool listing was truncated, so an unlisted cue may hold any candidate number;
> automatic assignment is **refused**"*

**보이지 않는 슬롯이 후보 번호를 점유할 수 있으므로 자동 할당을 거부한다.** 그룹 슬롯도 동일해야 한다.
번호를 세지 않고 **재조회 실측**하며, 절단이면 거부한다.

## §5. 라이브 실측 — 다시 재지 않아도 되는 값

### §5.1 그룹 풀 `[실측]`

| no | name |
|---|---|
| 1 | `Copilot Grp` |
| 11 | `Back` |
| 12 | `Front` |
| 13 | `All` |
| 15 | `Inner Outer Opp` |

- **슬롯 비연속** (2~10, 14가 빈다) → "다음 번호" 계산 금지
- **`Front`·`Back`·`Inner Outer Opp`가 이미 존재** → 사용자가 예시로 든 어휘와 **정면 충돌**.
  §2.1에 따라 이들은 **백업도 복구도 불가**하므로 덮어쓰기는 배제된다
- **`Group 11`은 룰북의 검증된 페이저 예시가 사용**(`31_choreography_patterns.md:48,67,163`) —
  건드리면 룰북 문면이 거짓이 된다
- `Inner Outer Opp`의 존재는 **LD가 이미 내/외 개념으로 사고한다**는 신호다. 요구의 어휘가 현장 관례와 맞는다

### §5.2 픽스처 · 절단 `[실측]`

- `Patch/Stages/1/Fixtures` → `childCount: 19`, 반환 **18**, `truncated: true`
- 19번째가 스냅샷에서 탈락한다. SPATIAL §E.2.20 결함 1의 원인 — 18대만 배치되고 fid 19가 원점에 남았고
  모델은 그 사실을 알리지 않았다
- → **그룹에서 더 위험하다**: 18대만 담긴 그룹은 조용히 틀린 자산으로 **영속**한다.
  선택은 사라지지만 그룹은 남는다

### §5.3 좌표 기록 채널 `[실측]` (SPATIAL 승계)

- `Set Fixture <fid> <Posx|Posy|Posz> '<value>'` — **작은따옴표 필수**
- 음수 5형태 중 3형태가 `OK` + 부호 소실/무동작/엉뚱한 값
- float32 드리프트 `9.9` → `9.8999996185303` → 검증은 **수치 허용오차**
- `exec`는 **큰따옴표 거부**(`server/bridge/protocol.py:109`)
- 상세: `SPEC-COPILOT-SPATIAL-001/progress.md` §E.2.6a

### §5.4 안전 게이트 `[실측]`

- 블랙리스트 v1 `[코드]`: `Delete` · `Remove` · `Off Everything` · `Store /overwrite` · `Shutdown` · `Format`
  → **`Store Group`(무플래그)은 없다.** 점유 슬롯 덮어쓰기가 게이트를 통과하는지 `[미확정]`
- `Set Fixture … Pos*`는 현재 **`safe`** → 승인 카드 없음 · 백업 규칙 ③ 미발동
  (AC-SPATIAL-031 `[DEFERRED]`)
- **관측된 사고**: 연출만 요청한 턴에서 모델이 대화 이력의 미완 목표를 이어 **요청하지 않은 좌표 기록
  54건을 무승인 실행**(SPATIAL §E.2.20 결함 2). 같은 사고가 **복구 불가 자산**에서 일어나면 끝이다

### §5.5 예산 `[실측]`

- 왕복 **66.7 ms** · 18대×3축 = 54왕복 = 3.6s
- `DEFAULT_MAX_MODEL_CALLS = 12` — *"배치 + 그룹 + 연출"* 복합 지시는 `loop_limit`(부분 실행) 실측 확인
- `CONFIG.max_payload = 1900` — 초과는 조용한 드롭

### §5.6 Gemini `[실측]`

- `additionalProperties`는 자동 제거된다(커밋 `a5fa16a`). 단 `_GEMINI_UNSUPPORTED_KEYS`는 **DENY 리스트**라
  다른 미지원 키워드를 쓰면 요청 전체가 400으로 죽는다

## §6. 위상 어휘 — 업계 표준 조사 결과 (v0.3.0 신설)

> **조사 방법**: 웹 검색으로 무대조명 표준 용어를 조사했다. 근거 등급 `[인수-웹]`은 외부 문헌이며
> **우리 콘솔의 실측이 아니다**. 단 §6.1(MA3 축 의미)은 **MA Lighting 공식 문서**이므로 사실상 규범이다.
> **결론부터: v0.2.0에서 제가 제안한 `Front/Back`·`Left/Right`는 업계 용어가 아니며, `Left/Right`는
> 위험하다.**

### §6.1 축 의미 — MA Lighting 공식 `[인수-웹, 규범]`

`help.malighting.com/grandMA3/2.2/HTML/qsg_3d_setup.html` ·
`.../patch_position_fixtures.html`:

| 축 | 의미 | 부호 규약 |
|---|---|---|
| **X** | stage left / right | **양수 = stage left 방향** · *"Stage right will be negative numbers if 0 is on the centerline"* |
| **Y** | downstage / upstage | **양수 = upstage** (객석에서 멀어지는 방향) |
| **Z** | height | 양수 = 바닥 위 |

기본 무대: 폭(X) 30m × 깊이(Y) 30m, **중앙이 0** · 높이(Z) 0~15m. 신규 패치 픽스처는 전부 `(0,0,0)`에
0° 회전으로 생성된다 — **우리 리그 19대가 전부 원점이었던 이유가 이것이다**(§5.2와 일치, 교차 확인됨).

### §6.2 깊이 축 — `Downstage / Center / Upstage` (표준)

`Front/Back`이 아니다. 표준은 **Downstage(DS)** = 객석에 가장 가까움 · **Upstage(US)** = 가장 멂 ·
**Center Stage(CS)** = 중앙. 어원은 객석 쪽으로 기울어진 옛 raked stage다 — upstage로 가면 물리적으로
높아졌다. 투어/콘서트 현장은 **downstage / mid-stage / upstage** 를 쓰며 트러스도 같은 어휘를 상속한다
(*downstage truss · mid truss · upstage truss*).

→ **y 오름차순 = downstage → upstage.** SPATIAL의 `SPATIAL_ROW_ORDER = "y_ascending"`("stage front to
back")은 **의미는 맞고 낱말이 틀렸다.** 그룹 이름은 `Downstage` / `Center` / `Upstage`여야 한다.

### §6.3 ⚠ 좌우 축 — 여기가 함정이다

**stage left/right 는 배우 기준이고, house left/right 는 객석 기준이며, 둘은 정반대다.**

- *"Stage left is the area to the performer's left when standing on stage and facing the audience"*
- *"stage left sits on the audience's right, and stage right sits on the audience's left"*
- house left/right 는 FOH 스태프가 좌석·조명 위치를 말할 때 쓴다

MA3는 **+x = stage left**로 정의한다(§6.1). 따라서:

| | −x | +x |
|---|---|---|
| 무대 기준 | **stage right** | **stage left** |
| 객석 기준 | **house left** | **house right** |

#### §6.3.1 소급 결함 — SPATIAL-001의 `left_to_right` `[실측]`

실증했다(3대 리그, x = −4 / 0 / +4):

```
left_to_right = (1, 2, 3)
  fid 1: x=-4.0 → stage RIGHT = house LEFT
  fid 3: x=+4.0 → stage LEFT  = house RIGHT
```

→ **`left_to_right`는 house left → house right, 즉 stage RIGHT → stage LEFT 다.**
조명 디자이너가 *"stage left에서 stage right로"* 라고 말하면 **이 정렬의 역방향**을 뜻한다.

**평가**: *동작*은 순진한 사용자 기대와 맞는다 — P8 라이브 관측에서 사용자가 3D 뷰를 보며 최소 x를
"왼쪽에서 4번째"로 확인했고 이는 객석 시점과 일치한다. 그러나 *용어*가 전문 표준이 아니고, **한국어
"왼쪽/오른쪽"도 누구 기준인지 명시하지 않아 같은 모호성을 갖는다.**

**GROUPGEN의 대응**: 그룹 이름에 **맨 `Left`/`Right`를 쓰지 않는다.** `Stage Left` / `Stage Right`처럼
기준을 이름에 박는다. SPATIAL의 정렬 어휘 개명은 **출하된 폐쇄 집합의 파괴적 변경**이므로 이 SPEC의
범위 밖이며, **sync-phase 인계 사항으로 등록**한다(§6.9).

### §6.4 그리드 — 업계에 이미 표준 복합 명명이 있다 `[인수-웹]`

*"Most stages can be divided into a 3×3 grid, three columns (left, center, right) crossed with three rows
(downstage, center, upstage), producing nine positions, each with its own abbreviation used in blocking
scripts, stage plots, and **lighting plots**"* — 앞이 깊이(DS/CS/US), 뒤가 좌우:

|  | stage right | centre | stage left |
|---|---|---|---|
| **Upstage** | USR | USC | USL |
| **Center** | CSR | CS | CSL |
| **Downstage** | DSR | DSC | DSL |

→ **`plan.md` Q2(위상 경합: 3×10은 rows인가 grid인가)의 답이 업계에 이미 있다.** 그리드는 복합 명명이
표준이므로, 깊이 그룹 3개 + 좌우 그룹 3개를 따로 만들 수도, 9개 교차 그룹을 만들 수도 있다.
**plan-phase가 고를 것** — 다만 어휘는 발명하지 않는다.

### §6.5 수직 축 — 층 어휘는 표준이 없고, 대신 **기능** 어휘가 있다 `[인수-웹]`

찾은 것은 `Low/Mid/High` 같은 층 이름이 아니라 **방향·기능** 어휘였다:

- **High side** *"mounted at the horizontal edge of the stage at an angle above the subject"* ·
  **Low side** = 바닥 근처. 무용에서 low sidelight 붐을 60~90°로 쓰고, 붐 위치는 **upstage / midstage /
  downstage** 로 부른다 — 즉 **붐도 깊이 어휘를 상속한다**
- **Front light**(키라이트) · **Back light**(윤곽·입체감) · **Side light**(중흉·어깨·발) ·
  **Top light**(전반 조명, 앞→뒤로 열 단위 구분) · **Uplight**(아래에서)
- 3점 조명: **key / fill / back**

→ **z축 층에 붙일 표준 어휘는 발견되지 않았다.** `High side`/`Low side`가 가장 가까운 실제 쌍이다.
3층 이상은 `Level 1..N`처럼 **번호가 정직하다** — 없는 표준을 발명하는 것보다.

### §6.6 동심원 — **업계 표준이 존재하지 않는다** (정직한 결과) `[인수-웹]`

원형 트러스는 실재하고 널리 쓰인다(*"places lamps at measured intervals around a continuous loop"*).
그러나 **inner/outer 링 그룹 명명의 확립된 표준은 찾지 못했다.** 검색 결과가 명시적으로 그렇게 말한다 —
프로젝트·업체별 내부 관례이거나 아직 표준화되지 않았다는 것이다. (`inner chord`는 트러스 *구조* 용어이며
픽스처 그룹 이름이 아니다.)

**그런데 우리 리그에 `Inner Outer Opp`(no 15) 그룹이 이미 있다** — 이 LD는 이미 내/외 개념으로 사고한다.

→ **`Inner`/`Outer`를 채택하되 "업계 표준 아님 · 현장 관례 기반"으로 명시**한다. 3링 이상은 `Ring 1..N`.
표준이 없다는 사실 자체를 기록하는 것이 나중의 "왜 이 이름인가"를 막는다.

### §6.7 ⚠ 가장 중요한 반론 — 전문가는 **기능**으로 묶는다 `[인수-웹]`

ETC 공식 조명 용어집:

> *"The control channel is the numerical name the designer uses for a luminaire or set of luminaires that
> are controlled together. Control channels are used to group sets of luminaires or devices together in a
> **logical way relating to how the designer thinks about the design, rather than to their physical
> location in the venue**."*

**이것은 본 SPEC의 전제를 정면으로 겨눈다.** 전문가의 1차 그룹 축은 **기능**(front/side/back/top wash,
key/fill/back, 밴드 멤버별 존)이고 **물리적 위치가 아니다.**

**그러므로 본 SPEC은 기능 그룹을 대체하지 않는다 — 보완한다.** 설계 함의:

1. **기하 그룹은 기하 그룹으로 보이게 이름 붙인다.** 기능 그룹으로 위장하면 LD의 사고 모델과 충돌한다.
   → 접두 규칙(§5.1 이름 충돌 대응과 동일한 해법)이 **두 이유에서** 정당해진다:
   기존 이름 충돌 회피 + 기하/기능 축 구분.
2. **`Downstage`라는 이름이 곧 "front light"를 뜻하지 않는다.** downstage에 걸린 픽스처가
   백라이트로 쓰일 수 있다. 이름은 **위치**를 말하고 **역할**을 말하지 않는다 — 문서에 명시할 것.
3. SPEC은 *"배치 인식 그룹"* 이라는 좁은 약속만 한다. **연출 의도의 자동 해석까지 주장하지 않는다.**

### §6.8 McCandless acting areas — 번호 관례는 표준화되지 않았다 `[인수-웹]`

무대를 **acting areas**로 쪼개는 것은 고전 방법론이다(영역당 픽스처 2대, 소형 무대 6영역 ·
대형 최대 15영역, *"3 across and 2 deep"*가 출발점). 존 번호(1~7 + 특수 8·9) 예시는 있으나
**번호를 어느 방향으로 매기는지는 표준이 없다** — 극장·디자인별이다.

→ `Area N` / `Ring N` / `Level N` 같은 번호 폴백을 쓸 때 **순서 규칙을 문서화**해야 한다.
번호 자체는 정당하나 순서를 암묵에 두면 안 된다.

### §6.9 확정 어휘 제안 (plan-phase 최종 확정 대상)

| 위상 | 검출 축 | 2분할 | 3분할 | 4+ 폴백 | 근거 |
|---|---|---|---|---|---|
| `depth_rows` | y 갭 (**+y = upstage**) | `Downstage` / `Upstage` | `Downstage` / `Center` / `Upstage` | `Row 1..N` (DS→US) | **표준** §6.2 |
| `lateral_split` | x 갭 (**+x = stage left**) | `Stage Right` / `Stage Left` | `Stage Right` / `Center` / `Stage Left` | `Column 1..N` | **표준** §6.3 — 맨 Left/Right 금지 |
| `grid` | y·x 양축 | — | 9칸 `DSR…USL` 또는 축별 분리 | `Area N` | **표준** §6.4 |
| `concentric` | 반지름 갭 | `Inner` / `Outer` | `Inner` / `Mid` / `Outer` | `Ring 1..N` | **표준 없음** §6.6 — 관례 기반 명시 |
| `vertical_levels` | z 갭 | `Low Side` / `High Side` | — | `Level 1..N` | 부분 표준 §6.5 |

**전부 폐쇄 집합 + 번호 폴백.** 임의 작명 0. 접두 규칙(예: `SP ` 또는 `Spatial `)은 §5.1 충돌 회피와
§6.7 기하/기능 구분을 **동시에** 해결하므로 강하게 권고한다.

### §6.10 미해결 난점 (plan-phase)

- **위상 경합** — 3×10은 `depth_rows`인가 `grid`인가. §6.4가 어휘는 주지만 *선택 규칙*은 우리 몫
- **모호 시 거동** — 어느 위상도 뚜렷하지 않으면 SPATIAL 규율대로 **단정하지 않고 저신뢰 + 위상 `None`**
- **비공허성** — 위상별 golden이 서로를 **구별**해야 한다. 현재 계층이 2겹 동심원을 9행 고신뢰로 오독한
  것이 정확히 이 결함이다(§3)
- **`left_to_right` 개명** — SPATIAL의 출하된 폐쇄 정렬 어휘는 house 기준이다(§6.3.1).
  개명은 파괴적 변경이므로 **본 SPEC 범위 밖 · sync-phase 인계**. 최소한 SPATIAL 문서에
  *"left/right는 house(객석) 기준"* 을 명기해야 한다

## §7. 세분화 축 분류 — 조명 연출·디자인 영역 심층 조사 (v0.4.0 신설)

> 사용자 요구: *"좀더 세분화할 수 있도록"* · *"조명 연출과 디자인 영역을 중점으로"*.
> 조사 결과 **디자이너가 리그를 쪼개는 축은 6개**(C가 둘로 갈림)이며, 그중 **본 SPEC이 다루는 것은
> A(위치) + C1(종류)** 이고 C2(명칭)는 *제안만*, B·D·E는 범위 밖이다. 나머지는 원리적으로 다른 정보원을 요구하거나 **이미 콘솔이 한다.**
> 축을 혼동하면 SPEC이 할 수 없는 것을 약속하게 된다.

### §7.0 여섯 축 요약 (C가 종류/명칭으로 갈린다)

| 축 | 무엇으로 쪼개는가 | 정보원 | 본 SPEC | 
|---|---|---|---|
| **A. 위치(기하)** | 좌표 위상 | `posx/posy/posz` **판독 가능** | **주 대상** |
| **B. 기능/시스템** | 빛의 역할·방향 | 디자이너 의도 (좌표로 유도 불가) | **범위 밖** — 이름으로 위장 금지 |
| **C1. 장비 종류** | 타입·제조사 | `fixturetype`→풀→`name`/`ShortName`/`Manufacturer` **실측 확인** | **v1 채택**(사용자 요구) |
| **C2. 장비 명칭** | 이름 문자열 | `name` 판독 가능하나 **자유 문자열** | **자동 생성 금지 · 제안만** |
| **D. 리깅 위치** | 하드웨어 구조명 | 리그 도면 (패치에 없음) | 범위 밖 |
| **E. 런타임 효과 분할** | 선택 재성형 | **MAtricks가 이미 한다** | **명시적 제외** |

### §7.1 축 A — 위치(기하) · 본 SPEC의 주 대상

§6.9 어휘표가 이 축을 덮는다. 조사로 **하나가 더 추가**됐다:

**오버헤드 바 번호 관례** `[인수-웹]` — theatrecrafts:
> *"Lighting bars over the stage are numbered from the proscenium arch towards upstage. The bar closest
> to the proscenium is **LX1** (or **Electrics 1** / **Number 1 Electric** in the USA)"* · 다음은
> Second Electric …

→ **4행 이상 폴백의 정답이 `Row 1..N`이 아니라 `Electric 1..N`(또는 `LX1..N`)이다.**
그리고 **방향이 표준으로 정해져 있다 — 프로시니엄(downstage)에서 upstage로.** §6.8에서 "번호 순서
규칙을 문서화해야 한다"고 적었는데, **깊이 축만은 업계 표준 방향이 존재한다.**

**붐(수직 측면) 번호** `[인수-웹]`: *"Booms are named by their position (e.g. **SR Boom #1** is the
downstage boom on stage right)"* → **측면 접두 + downstage부터 번호.** 좌우 그룹을 여러 개로 쪼갤 때의
표준 형태다(`SR Boom 1` / `SR Boom 2` …).

**기물 번호 방향** `[인수-웹, 단일 출처]`: *"label instruments from stage left to right (for battens),
and top to bottom for booms and ladders"* — 바텐은 좌우, 붐·래더는 위→아래. 단일 출처이므로
`[미확정]`으로 다루되, **수직 축 번호는 위→아래**라는 신호다(§6.5의 `Level 1..N` 방향 근거).

**추가 위상 후보 — 좌우 대칭(bilateral symmetry)** `[인수-웹]`:
> *"If you set half your symmetrical rig to **Pan Invert**, you can speed up positioning… program an
> entire rig with only half of it working"* · MA3 MAtricks의 **`Mirror` transform**이 이를 구현한다

→ **리그가 x=0 기준 대칭 쌍을 이루는지**는 좌표로 **검출 가능**하며, 검출되면 (a) `Stage Left`/`Stage Right`
분할의 근거가 확실해지고 (b) LD에게 *"이 리그는 미러링 가능"* 이라는 실용 정보를 준다.
**§6.9에 없던 위상 후보로 추가할 것.**

### §7.2 축 B — 기능/시스템 · **전문가의 1차 축이지만 본 SPEC의 범위 밖**

§6.7의 ETC 인용을 조사가 더 강하게 확증했다. Vectorworks 광플롯 가이드 `[인수-웹]`:

> *"One common method of channeling is to think of the different groups of lights as **'systems.'**
> You'll have a **front light system**, a **backlight system** (or two if using two-color backlight),
> a **cross left (xl) sidelight system**, a **cross right (xr) sidelight system**, and possibly
> **gobo or template systems**"* · *"Channel numbering in a plot organizes lights according to how the
> designer wants to control them — organized by the different groups or 'systems'"*

**"System" = 전문가가 실제로 채널·그룹을 조직하는 단위**이며 **(방향/각도) × (색/타입)** 의 곱이다.

전통 디자인 어휘 `[인수-웹]`:

| 용어 | 정의 |
|---|---|
| **Acting area** | *"those spaces on the stage where specific scenes are played"* — 영역당 픽스처 2대(McCandless) |
| **Wash** | Jean Rosenthal: *"bathes a section of the stage with an even field of light using a circuit of two or more lamps"* — front/side/back/down wash |
| **Special** | *"any instrument which is not an acting area light, a toning and blending light, or a background light"* |
| **Background** | cyc / 배경 조명 |
| **Two-color system** | warm(≈3200K) / cool(≈5600K) 대비 — 자연광 표현의 기본 |
| 방향 어휘 | Front(키) · Back(윤곽·분리) · Side(중흉·어깨·발) · Top · Up · **Cross Left(XL) / Cross Right(XR)** |
| 3점 조명 | key / fill / back |

**왜 범위 밖인가**: 이 축은 **빛이 무엇을 하는가**이고 좌표는 **장비가 어디 있는가**만 안다.
downstage에 걸린 픽스처가 백라이트일 수 있고 upstage 픽스처가 프론트일 수 있다 — 조준 방향과
연출 의도가 결정한다.

**`[미확정]` 미래 가능성**: 우리는 `rotx/roty/rotz`도 **판독 가능**하다(SPATIAL §E.2.1 실측).
위치 + 회전이면 **조준 방향**을 유도할 수 있어 front/back/side 추론이 원리적으로 가능하다.
그러나 (a) 회전값의 의미(좌표계·영점)가 미검증이고 (b) *추론된* 기능을 확정 이름으로 붙이는 것은
이 저장소가 금지한 "발명"에 가깝다. **v1 제외 · 별도 SPEC 후보로 기록.**

**설계 함의(§6.7 강화)**: 기하 그룹 이름이 기능 어휘를 **차용하면 안 된다.**
`Front` 같은 이름은 front light system으로 읽힌다 — **§6.2가 `Downstage`를 쓰라고 한 이유가
표준 준수만이 아니라 기능 축과의 충돌 회피이기도 하다.**

### §7.3 축 C — 장비 종류·명칭 · **v1 포함 (사용자 요구)** — 단 두 하위축은 성질이 다르다

사용자 요구: *"장비의 명칭이나 종류에 따른 구분도 필요해."*
조사·실측 결과 **"종류"와 "명칭"은 안전성이 정반대**다. 하나는 구조화된 패치 데이터,
다른 하나는 자유 문자열이다. **한 축으로 묶으면 안 된다.**

#### §7.3.1 라이브 실측 — 픽스처는 자기 타입을 알려준다 `[실측]`

`prop` 사다리 + 날조 대조군(2026-08-03, `Patch/Stages/1/Fixtures/2`):

| 프로퍼티 | 결과 |
|---|---|
| **`fixturetype`** | **`'FixtureType 1'`** — 타입 풀 **참조** |
| `FixtureType` | `'FixtureType 1'` (대소문자 무관) |
| **`mode`** | **`'1 Mode 1'`** — DMX 모드 |
| `fid` · `name` | `'2'` · `'Copilot MMX 2'` |
| `type`·`subtype`·`manufacturer`·`shortname`·`longname`·`fixtureid`·`DMXMode` | **전부 `property not readable`** |

**날조 대조군 3/3 FAIL**(`fixturetypez` · `NotARealTypeField` · `typ`) → **채널 변별적.**

타입 오브젝트 쪽 `[실측]`:

| `Patch/FixtureTypes/1` | 값 |
|---|---|
| `name` | `'Robin MMX Spot'` |
| **`ShortName`** | **`'RMMXSm1'`** |
| **`Manufacturer`** | **`'Robe'`** |
| `LongName` | `''` (빈 값) |
| `FixtureTypeID` | **판독 불가** |

→ **2-hop 경로가 성립한다**: 픽스처 `fixturetype` → `Patch/FixtureTypes/<n>` → `name`/`ShortName`/`Manufacturer`.
**축 C는 기술적으로 확실히 가능하다.** 비용도 싸다 — 30대면 타입 참조 30왕복(≈2s) + 타입별 소수 왕복.

#### §7.3.2 하위축 C1 — **종류(type)** · 안전, v1 채택 권고

세 층위가 있고 **안전성이 다르다**:

| 층위 | 성질 | 그룹 이름 예 | 위험 |
|---|---|---|---|
| **제조사** | GDTF 표준 필드 · **완전 구조화** | `Robe` | **없음** |
| **타입명 전체** | 패치 문자열 그대로 | `Robin MMX Spot` | 없음(그대로 씀) |
| **업계 카테고리** | 타입명에서 **토큰 매칭** | `Spot` · `Wash` · `Beam` | **휴리스틱** — 아래 |

**⚠ 카테고리는 표준 필드가 아니다** `[인수-웹, 규범]` — GDTF 스펙 FixtureType 노드의 속성은
`Name` · `ShortName` · `LongName` · `Manufacturer` · `Description` · `FixtureTypeID` · `Thumbnail` ·
`RefFT` · `CanHaveChildren` **뿐이며 `Categories`가 없다**(gdtf.eu 파일 스펙 Table 3 직접 확인).

즉 **업계 표준 장비 정의 포맷에 기계 판독 가능한 분류 필드가 존재하지 않는다.**
Spot/Wash/Beam은 마케팅·브라우징 분류이지 파일 스펙의 일부가 아니다.

→ `'Robin MMX Spot'` 에서 `Spot` 을 얻으려면 **폐쇄 어휘 토큰 매칭**뿐이다. 규율:

1. 폐쇄 어휘만 매칭(§7.3.4) · **무매칭이면 그룹을 만들지 않는다**(추측 금지)
2. **다중 매칭은 모호로 처리** — `Wash Beam` 류 이름은 단정하지 않는다
3. **제조사·타입명 전체 그룹은 토큰 매칭 없이** 만들 수 있다 → **가장 안전한 시작점**

#### §7.3.3 하위축 C2 — **명칭(name)** · ⚠ 위험, 자동 그룹 생성 **비권고**

우리 리그의 픽스처 이름 `[실측]`:

| slot | name | 성질 |
|---|---|---|
| 1 | `RMMXSm1 1` | **MA3 자동 작명** = `ShortName`(`RMMXSm1`) + 번호 |
| 2~10 | `Copilot MMX 2` … | 사용자 개명 (관례 A) |
| 11~19 | `MMX 11` … | 사용자 개명 (관례 B) |

**동일 타입 19대에 명명 패턴이 3가지다.** 이름으로 그룹을 나누면 **의미 없는 3그룹**이 나오고,
그것이 쇼파일에 **영속**한다. 이름은 자유 문자열이며 일관성이 보장되지 않는다.

**그런데 유용한 판별자를 하나 얻었다**: 자동 작명은 `ShortName + " " + n` 형태다.
→ **이름이 기본값인지 사용자 의도인지 구별할 수 있다.** `RMMXSm1 1`은 정보가 0이고
`Copilot MMX 2`는 사용자가 붙인 것이다. 이 구별 없이 이름을 신뢰하면 기본값을 의도로 오독한다.

**권고**:

- **이름 기반 자동 그룹 생성 금지.** 토큰을 쪼개 그룹을 만드는 것은 이 저장소가 금지한 발명에 가깝다
- **대신 *제안*으로 보고**: 이름 클러스터를 감지해 *"`Copilot MMX` 접두 9대 · `MMX` 접두 9대가
  보입니다 — 그룹으로 만들까요?"* 사용자가 확정한다. **에이전트가 조용히 고르지 않는다**
- **기본값 이름은 신호가 아님을 명시** — `ShortName + n` 패턴은 제외

#### §7.3.4 카테고리 폐쇄 어휘 후보 `[인수-웹]`

업계에서 반복 확인된 타입 분류: **Spot** · **Wash** · **Beam** · **PAR** · **Fresnel** ·
**Profile** · **Strobe** · **Blinder** · **Effect** · **Follow Spot**.

역할 차이가 그룹 분리의 근거다:

- **Wash** — *"wide, even illumination"* · 큰 붓
- **Spot / Profile** — *"smaller more detailed brush… highlight and shape specific objects"*
- **Beam** — *"narrow aerial beams… readable over longer distances"* · 공중 효과
- **Strobe** — *"rapid flashes… synchronized with music"* · 클라이맥스
- **Blinder** — **관객을 비춘다**(*"illuminate the audience rather than the performers"*)
  → **위치 그룹과 절대 섞이면 안 되는 종류.** 무대 위상 그룹에 blinder가 섞이면 연출이 관객을 때린다

#### §7.3.5 이 리그에서의 실익은 0 — 그러나 설계는 필요하다

`Patch/FixtureTypes` **childCount 1**(`Robin MMX Spot`) `[실측]` — **완전 동종 리그**다.
타입 축은 이 리그에서 아무것도 나누지 못한다.

→ **이종 리그를 위한 설계**이며, **테스트는 합성 golden으로** 해야 한다(동종 리그로는 비공허성을
증명할 수 없다). M6 라이브 판정에서 타입 축은 `SKIP:`(`CONDITION_NOT_MET`)이 정직하다 —
**리그가 동종이라 판정 불가**임을 기록한다.

#### §7.3.6 위상 × 종류 교차 — 세분화의 실체

축 A와 C1을 교차하면 세분화가 곱으로 늘어난다: `Upstage Wash` · `Upstage Beam` ·
`Downstage Spot` … **사용자가 원한 "더 세분화"의 실체가 이것이다.**

**단 폭발을 막아야 한다** — 3위상 × 4타입 = 12그룹이고 빈 조합도 생긴다. 규율 필요:

- **빈 교차는 그룹을 만들지 않는다**(멤버 0 그룹 금지)
- **교차 그룹 수 상한**과, 상한 초과 시 거동(축별 그룹만 만들기)을 plan-phase가 정한다
- 슬롯이 유한하다 — 현재 빈 슬롯은 2~10 · 14 · 16+ 뿐이다(§5.1). **교차 폭발은 슬롯 고갈로 직결된다**

### §7.4 축 D — 리깅 위치 · 범위 밖

`[인수-웹]` 구조명: **FOH**(프로시니엄 객석측 전부) · **LX1/Electric N**(오버헤드) ·
**Boom**(수직 측면, 바닥 근처) · **Box Boom**(객석 측벽 — *"most used term for side positions in the
auditorium"*) · **Ladder**(공중 붐, 씬 체인지에 인아웃 가능) · **Torm**(Proscenium Tormentor) ·
**Floor package**(*"equipment brought by a touring band which sits on the stage deck on
ground-supported truss"*) · 콘서트 레이어: **front / back / side / floor / aerial**

**왜 범위 밖인가**: 이것들은 **하드웨어 구조의 이름**이고 패치에 없다. 좌표로 *추정*할 수는 있다
(z가 낮고 x가 극단 → boom일 가능성) 그러나 그건 추측이며, `Boom`이라 이름 붙였는데 실제로는
래더면 거짓 자산이 영속한다. **단, `Electric N` 어휘는 §7.1에서 깊이 폴백으로 차용한다** —
"몇 번째 바인가"는 좌표(y 순서)로 정직하게 말할 수 있는 것이기 때문이다.

### §7.5 축 E — 런타임 효과 분할 · **MAtricks가 이미 한다 → 명시적 제외**

MA Lighting 공식 `[인수-웹, 규범]`:

> *"**MAtricks** is a tool that can be used to **divide a selection of fixtures into sub-selections**"* ·
> 창은 축별 3구획(X 빨강 · Y 파랑 · Z 초록) · Grid 속성 = **Axis · Block · Group · Wings · Width**

| MAtricks 기능 | 공식 정의 | 연출 용도 |
|---|---|---|
| **Wings** | *"separate the selection into the number of wings set and select devices from each wing **from opposite directions**"* | 중앙 대칭 · 양끝→중앙 |
| **Block** | *"creates blocks of fixtures of the specified size… **treats blocks as one fixture**"* | 덩어리 반복 |
| **Group** | *"separate the selection into the number of groups set, **alternating** through the selection"* | 홀짝·인터리브 |
| **Shuffle** | *"XShuffle is basically a **seed**… XShuffle 42 will always be the same random order"* | 재현 가능한 랜덤 |
| **Invert / Mirror** | `Mirror`는 *"set invertstyle to pan, enable invert for enabled groupings like xwings"* | 대칭 리그 미러링 |

그리고 **Selection Grid**: *"a virtual coordinate system that can be used to arrange the selection of
fixtures in a **true three-dimensional space**"* — Phaser·딜레이·페이드를 그 축 위로 분배한다.

**결론 — 이 축의 그룹을 만들면 안 된다.** 홀짝·윙·블록은 **런타임 재성형**이며 영속 자산이 아니다.
콘솔이 이미 하고, 우리 룰북 `31_choreography_patterns.md:85-90`이 이미 `XWings`·`XShuffle`·
`PhaseFromX/ToX`를 **검증된 문법으로** 싣고 있다. 여기에 그룹을 만들면 **콘솔 기능을 중복 구현**하는 것이다.

#### §7.5.1 오히려 진짜 시너지가 여기 있다

MAtricks는 **Selection Grid 위에서** 동작하고, 그리드는 **선택 순서로** 세워진다.
공식 문서가 확인한다: *"when phasing an effect from 0 thru 360, the effect will spread evenly across
the selected fixtures… the effect will appear to **walk across the stage**"*.

→ **SPATIAL이 실측 좌표로 선택 순서를 세우고**(§SPATIAL M3), **GROUPGEN이 위상 그룹을 영속화하고**,
그 위에 **MAtricks가 윙·블록·홀짝을 얹는다.** 세 층이 각자의 일을 한다:

```
GROUPGEN 그룹  = 누구를 (영속 · 이름 있음 · 콘솔에서 손으로도 쓸 수 있음)
SPATIAL 선택순서 = 어떤 순서로 (런타임 · 방향을 만든다)
MAtricks       = 그 순서를 어떻게 재성형할지 (런타임 · 윙·블록·홀짝·셔플)
```

**이 3층 관계를 `design.md`에 명기할 것** — 그러지 않으면 후속 작업이 MAtricks를 그룹으로
재구현하려 든다.

### §7.6 §6.9 어휘표 보정 (조사 반영)

| 위상 | 2분할 | 3분할 | 4+ 폴백 | 변경점 |
|---|---|---|---|---|
| `depth_rows` | Downstage / Upstage | + Center | **`Electric 1..N`** (DS→US, **표준 방향**) | `Row N` → `Electric N` |
| `lateral_split` | Stage Right / Stage Left | + Center | `SR Boom 1..N` / `SL Boom 1..N` 형태 참조 | 붐 번호 관례 반영 |
| `grid` | — | `DSR…USL` 9칸 | `Area N` | 변경 없음 |
| `concentric` | Inner / Outer | + Mid | `Ring 1..N` | 표준 없음 유지 |
| `vertical_levels` | Low Side / High Side | — | `Level 1..N` (**위→아래**) | 번호 방향 근거 추가 |
| **`bilateral_pairs`** | — | — | — | **신설 후보**(§7.1) — 미러링 가능 신호 |

### §7.7 세분화의 상한 — 정직하게

본 SPEC이 **정당하게** 만들 수 있는 그룹은 **축 A(위치) + 축 C1(종류)** 이고, **축 C2(명칭)는
제안까지**다.
디자이너가 실제로 가장 많이 쓰는 축 B(시스템/기능)는 **좌표에 없는 정보**를 요구한다.

→ **SPEC은 *"배치 인식 위치 그룹"* 이라는 좁은 약속만 한다.** 사용자가 *"연출 의도에 맞게"* 라고 한
것을 *"연출 의도를 자동으로 해석한다"* 로 읽으면 과약속이다. 정직한 해석은:
**"연출에 쓸 수 있는 형태로 위치 그룹을 만들어 둔다"** — 의도는 사용자가 그 그룹 위에 얹는다.

## §8. ASSUMPTION 번호

전역 카운터: INTROSPECT-001 ~52 · SPATIAL-001 **53~60** → **본 SPEC은 61부터.**

## §9. 다음 세션의 첫 명령

```
/moai plan SPEC-COPILOT-GROUPGEN-001
```

브랜치 준비됨(`feature/SPEC-COPILOT-GROUPGEN-001`) — `--branch` 불필요.
읽는 순서: `progress.md` §0 → 본 문서 **§2**(GO/NO-GO) · **§3**(오독 실증) · **§6**(표준 어휘) ·
**§7**(세분화 축 — 무엇이 범위 밖인가) → `plan.md` §A.
