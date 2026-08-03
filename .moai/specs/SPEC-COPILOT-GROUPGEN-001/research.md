# SPEC-COPILOT-GROUPGEN-001 — 사전 조사 (research)

status: **pre-plan (킥오프 브리프) v0.2.0** · 2026-08-03 · `/moai plan` 미실행

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

## §6. 위상 어휘 후보 (plan-phase가 확정)

**폐쇄 집합**이어야 한다 — 임의 작명은 SPATIAL이 금지한 "조용한 임의 선택"과 같은 결함이다.

| 위상 | 검출 축 | 어휘 후보 | 현재 지원 |
|---|---|---|---|
| `depth_rows` | y축 갭 | Front / Center / Back · 4행+ → `Row 1..N` | **있음** (`rows.py`) |
| `lateral_split` | x축 갭 (또는 부호) | Left / Right · 3분할 → Left / Center / Right | 없음 |
| `concentric` | 중심으로부터 **반지름** 갭 | Inner / Outer · 3링+ → `Ring 1..N` | 없음 |
| `vertical_levels` | z축 갭 | Low / Mid / High · 4층+ → `Level 1..N` | 없음(`vertical_span`만 관측) |
| `grid` | y·x 양축 유의 | 복합 — 행 그룹 + 열 그룹 | 없음 |

**미해결 난점**(plan-phase 대상):

- **위상 경합** — 3×10 그리드는 `depth_rows`이면서 `lateral_split`이다. 우선순위 규칙 또는 복합 산출?
- **모호 시 거동** — 어느 위상도 뚜렷하지 않으면? SPATIAL 규율대로 **단정하지 않고 저신뢰 + 거부**
- **비공허성** — 위상 분류가 "항상 depth_rows"를 답하면 신호가 아니다. 위상별 golden이 서로를 **구별**해야 한다

## §7. ASSUMPTION 번호

전역 카운터: INTROSPECT-001 ~52 · SPATIAL-001 **53~60** → **본 SPEC은 61부터.**

## §8. 다음 세션의 첫 명령

```
/moai plan SPEC-COPILOT-GROUPGEN-001
```

브랜치 준비됨(`feature/SPEC-COPILOT-GROUPGEN-001`) — `--branch` 불필요.
`progress.md` §0 → 본 문서 §2 · §3 → `plan.md` §A 순서로 읽을 것.
