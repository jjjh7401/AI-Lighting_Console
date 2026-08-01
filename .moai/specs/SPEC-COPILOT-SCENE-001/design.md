# SPEC-COPILOT-SCENE-001 — 설계 근거 (design)

> **이 문서는 병렬 브리프의 인용 원본이다.** §3(결합 순서)과 §4(가드 정책)는 **공유 계약**이며, 병렬 슬라이스가 착수할 때 **양쪽 프롬프트에 문면 그대로** 주입된다. 두 작업자가 각자 해석하면 라이브러리 값과 빌더 산출이 어긋나고, **그 불일치는 런타임에서 아무 신호도 내지 않는다**(§7 위험 1). FXLIB이 같은 함정을 §F에 기록해 두었다(`SPEC-COPILOT-FXLIB-001/plan.md:186`).

## §1. 설계 의도

LOOKLIB이 "무엇을 켤까"(정지 화면)를, FXLIB이 "그것이 어떻게 움직일까"(시간축)를 구조화했다. 두 계층은 각자 **자기 산출물**을 만든다 — 룩은 프리셋을, 이펙트는 `Cue 1` 고정 시퀀스를. 그 결과 **"파란 백라이트가 천천히 웨이브하는 씬"은 하나의 큐로 존재할 수 없다.** 본 SPEC은 그 합성을 하는 계층이다.

설계의 세 원칙:

1. **미러이지 확장이 아니다.** `server/looks/**` · `server/fx/**`는 PRESERVE다. 씬은 자기 패키지(`server/scene/`)를 갖고, 두 계층의 검증된 형상(스키마 폐쇄 필드 · 로더 명시 에러 · 매칭 폴백 · 번들 문자열 규율 · 한국어 리포트)을 **모방**한다.
2. **문자열의 단일 출처.** 씬은 룩·이펙트의 값 라인을 **재조립하지 않고 상류에서 가져온다**(§2.2). 재조립은 두 곳을 갈라지게 하고, 갈라짐은 무음이다.
3. **접수와 효과를 절대 뭉개지 않는다.** `/CueOnly`가 접수됐다는 것과 트래킹이 막혔다는 것은 **다른 주장**이다. 이 SPEC에서 후자의 증거 채널은 **사람의 GUI 관측뿐**이다(§6).

## §2. 모듈 맵

| 파일 | 역할 | 미러 원형 |
|---|---|---|
| `server/scene/__init__.py` | 패키지 경계 문서(게이트 경유 원칙 독스트링) | `server/fx/__init__.py` |
| `server/scene/schema.py` | 씬 데이터클래스 + 폐쇄 필드 + 트리거 폐쇄 집합 | `server/fx/schema.py` |
| `server/scene/loader.py` | YAML 로드 + 명시 에러 검증 | `server/fx/loader.py` |
| `server/scene/matching.py` | 2축(룩·이펙트) 분리 매칭 + 부분 매칭 신호 | `server/fx/matching.py` + `server/looks/matching.py` |
| `server/scene/compile.py` | **결합(§3) + 충돌 열거 + 가드(§4) + 번호 획득(§5)** | `server/fx/instantiate.py` |
| `server/scene/report.py` | 한국어 2단 리포트 + **3주장 분리 상수** | `server/fx/report.py` + `server/looks/songcue_report.py` |
| `server/scene/library/*.yaml` | 내장 씬 엔트리 (정적 자산) | `server/fx/library/*.yaml` |
| `server/orchestrator/tools.py` | `find_scene` / `compile_scene` 등록 (2툴 추가만) | `find_fx` / `instantiate_fx` |

### §2.1 왜 단일 툴인가 — 강제이지 선호가 아니다

`instantiate_look` → `instantiate_fx`를 한 지시 턴에서 연쇄하는 설계는 **원리적으로 성립하지 않는다.** FXLIB이 이를 제외 범위로 명문화했다(`spec.md:146-148`):

> 한 지시 턴에서 `instantiate_fx`를 2회 이상 온전히 성립시키는 축. **dedupe 경계가 지시 턴 전체이고 `Step <k>`·스텝 값 라인이 패턴 간 공통 문자열이므로, 2회차 번들은 접힌다** … v1은 넓히는 대신 **명시 실패로 막는다**.

두 툴 연쇄는 그 함정의 정확한 재현이다: 2번째 툴 호출의 값 라인이 1번째와 겹치면 `skipped_already_executed`로 조용히 접히고 Store만 실행된다. 게다가 **두 툴은 각자 Store한다** — 룩은 프리셋을, 이펙트는 시퀀스를. 하나의 큐라는 산출물이 애초에 나오지 않는다.

따라서 씬 컴파일러는 **하나의 툴이 하나의 번들을 통째로 조립**한다. 이것은 dedupe 아키텍처가 강제한 형상이며, 취향의 문제가 아니다.

### §2.2 상류 재사용 — 문자열의 단일 출처 (결정 D)

씬 번들의 라인은 세 출처에서 온다. **씬은 어느 것도 재조립하지 않는다.**

| 라인 | 출처 | 공개 여부 |
|---|---|---|
| 룩 값 라인 (`;` 체인) | `server/looks/instantiate._values_line` | **비공개**(`_` 접두) |
| fx 스텝 열 / 위상 / 속도 / MAtricks | `server/fx/instantiate._step_lines` · `_phase_lines` · `_speed_line` · `_matricks` | **비공개** |
| dedupe 면제 판정 | `server/fx/instantiate.is_programmer_state` | **공개**(`__all__`) |

**비공개 이름 import는 이 저장소의 확립된 선례다.** `server/looks/busking.py:30`이 `_values_line`을 import하며 주석으로 이유를 적었고 — *"dedupe가 비교하는 문자열의 단일 출처"* — `server/looks/songcue.py:11`이 같은 것을 한다. 논거 원문(`busking.py:250-251`):

> 값 라인 문자열은 `instantiate._values_line`에서 온다 — dedupe가 실제로 비교하는 바로 그 문자열이며, **여기서 다시 조립하면 두 곳이 갈라진다**.

**트레이드오프 (정직 표기)**: 비공개 API에 결합하는 대가가 있다. 상류가 그 함수를 바꾸면 씬이 조용히 깨진다. 그러나 **대안이 더 나쁘다**: 재구현하면 두 벌이 갈라지고, 갈라짐은 **효과가 기계로 확인되지 않으므로 런타임에서 아무 신호도 내지 않는다**(spec.md §C.1). 선례가 같은 계산을 이미 했고 같은 답을 냈다. 차이는 **선례가 패키지 내부(looks→looks)였고 씬은 패키지 간(fx→scene)** 이라는 점이며, 그 간격은 **경계 테스트가 메운다**: `test_scene_boundary.py`가 상류 함수의 산출 형상을 고정한다(§8).

**면제 집합은 세 번째 사본을 만들지 않는다.** `is_programmer_state`가 **공개 API**이므로 씬은 그것을 호출한다 — fx가 `_PROGRAMMER_STATE_COMMANDS` 사본을 두면서 `test_fx_boundary.py:256-379`에 동치 단언 의무를 진 것과 달리, 씬은 **사본 자체를 만들지 않으므로 그 의무를 상속하지 않는다.** 이것이 사본을 늘리지 않는 유일한 경로다.

### §2.3 resolver가 없는 이유

씬 v1에는 역할 추상 축이 없다. 대상 그룹은 호출자가 지정하고 툴은 **실존 검증만** 한다(REQ-SCENE-018). 역할 축이 필요해지면(예: "백라이트만 웨이브") 그건 `server/looks/roles.py`의 **소비**이지 재정의가 아니며, 후속 개정에서 읽기 import한다. FXLIB이 같은 판단을 했다(`design.md §2` "resolver가 없는 이유").

## §3. 결합 순서 — 정본 (D2) 【공유 계약 — 병렬 브리프 인용 대상】

### §3.1 골격

씬 번들은 **정확히 이 순서**로 구성된다. 이 절이 정본이며, 다른 문서의 요약은 이 절을 가리킨다.

```
ChangeDestination Root                        # 목적지 — 정확히 1회, 선두
ClearAll                                      # 캡처 전 프로그래머 비우기
Group <n>                                     # bare 번호형 단일 (Select 접두 금지)
<룩 값 라인>                                    # 하나의 ';' 체인 라인 — _values_line 산출물
<fx step1 값 라인들>                            # Step 1 라인은 발화하지 않는다
Step 2                                        # 단독 라인
<fx step2 값 라인들>
[Step 3]                                      # 스텝이 3 이상이면 반복
[<fx step3 값 라인들>]
<위상 라인들>                                    # At Phase … Thru … — 스텝 열이 끝난 뒤
<속도 라인>                                     # At Speed <n> (BPM)
[Set Selection MAtricks '<축>' <값>]            # 패턴이 선언한 경우만
Store Sequence <s> Cue <c> '<이름>' /CueOnly    # ← 유일한 Store. 플래그 필수 (D1)
[Reset Selection MAtricks]                    # MAtricks 사용 시 — Store 뒤
ClearAll                                      # 다음 번들 오염 방지
[Set Cue <c> Sequence <s> Property 'TrigType' '<Token>']   # 트리거 지정 시
[Set Cue <c> Sequence <s> Property 'TrigTime' <절대초>]
[Assign Sequence <s> At Executor <m>]         # 사용자 명시 지정 시만 — 말미
```

### §3.2 왜 룩이 먼저인가 — 강제된 순서

**이것은 취향이 아니라 fx 빌더의 형상이 강제하는 결과다.**

두 가지 실측 사실이 맞물린다:

1. **페이저는 2개 이상의 스텝을 요구한다** — `server/fx/schema.py:66` `MIN_STEPS = 2`, 그리고 그 위의 `@MX:ANCHOR`가 이유를 적는다: *"M0 measured that `Relative`/`Phase`/`Speed` MODIFY an existing phaser rather than create one."*
2. **`Step 1` 라인은 발화되지 않는다** — `server/fx/instantiate.py:326-342` `_step_lines` 독스트링: *"`Step 1` is never emitted — the first step is the current one."*

두 사실의 귀결: **스텝 1은 "지금 프로그래머에 들어 있는 것"이다.** 이펙트는 그 위에서 변형을 시작한다. 룩은 바로 그 "지금 들어 있는 것"을 채우는 값이므로, **첫 `Step 2` 라인보다 앞에 있어야 스텝 1에 착지한다.**

룩을 이펙트 뒤에 놓으면 어떻게 되는가: 룩 값이 **마지막 스텝**에 얹혀 페이저의 종점이 된다. 사용자가 "파란색으로 웨이브"를 지시했는데 파란색이 웨이브의 한쪽 끝에서만 나타난다 — 그리고 **그 결함은 기계로 검출되지 않는다**(spec.md §C.1).

### §3.3 충돌 규칙 — 이펙트가 이긴다, 그러나 조용히는 아니다

룩과 이펙트가 **같은 attribute**를 지정할 수 있다(예: 룩이 `Dimmer At 80`, 이펙트 `pulse`가 `Dimmer` 스텝 열). 이때:

- **이펙트가 승자다.** 나중 라인이 프로그래머 값을 덮으므로 자연 귀결이다. §3.1 골격에서 fx 라인이 룩 라인 뒤에 오므로, **형상이 규칙을 강제한다** — 별도 우선순위 로직이 필요 없다.
- **덮인 attribute는 전수 열거된다.** 컴파일러는 룩의 attribute 집합과 이펙트가 건드리는 attribute 집합의 **교집합**을 계산해 결과에 싣는다(REQ-SCENE-005). 이 계산은 **컴파일 시점 정적 계산**이므로 관측 채널과 무관하게 정확하다 — 콘솔에 물어볼 필요가 없다.
- **조용한 덮어쓰기는 결함이다.** 열거가 비어 있는데 실제로 교집합이 있었다면 AC가 죽어야 한다(AC-SCENE-005 뮤테이션).

### §3.4 형상 규율

- **스텝 값 라인은 `;` 체이닝하지 않는다.** `;` 체이닝은 룰북 검증 리터럴이지만(`:39`), **스텝 문맥과의 조합은 미측정**이다. FXLIB이 같은 규율을 채택했다(`design.md §4.3`). **룩 값 라인은 예외** — 그것은 스텝 문맥 밖(스텝 1의 기반)이고 `_values_line`이 이미 `;` 체인으로 산출하며 LOOKLIB이 라이브 검증했다.
- **`Step <k>`는 단독 라인으로만.** `Attribute '<attr>' At Step <k>`는 **금지 형태**다 — 콘솔이 `ok:true`로 접수하지만 효과가 없다(FXLIB M0 실측, REQ-FXLIB-022). 씬은 이 금지를 계승한다(REQ-SCENE-011).
- **`Reset Selection MAtricks`는 Store 뒤.** 서브선택은 저장 대상 형상의 일부이므로 저장 전에 풀면 분할이 사라진다(`:90` 취지).
- **트리거 라인은 `ClearAll` 뒤.** 트리거는 프로그래머 상태가 아니라 **저장된 큐의 프로퍼티**를 건드리므로 캡처 사이클 밖이다. SONGCUE가 같은 배치를 쓴다(`songcue.py:488-499`는 `_auto_advance_commands`로 별도 생성).
- **`Assign … At Executor`는 최말미.** 캡처 사이클 밖이며, FXLIB이 `_ASSIGN_IS_LAST = True`로 같은 판단을 상수화했다(`server/fx/instantiate.py:110`).
- **번들 규모**: 룩 1줄 + fx 스텝 열 ~4-8줄 + 변형 ~2-3줄 + 규율 5줄 + 트리거 2줄 ≈ **14-22줄**. ~66ms/줄 기준선 대비 여유가 크다.

## §4. 가드 정책 【공유 계약 — 병렬 브리프 인용 대상】

### §4.1 1차 가드 — 세 선례 중 무엇을 따르는가

저장소에 1차(번들 내) 가드가 **세 벌** 있고 **정책이 서로 다르다**:

| 선례 | 위치 | 범위 | 위반 시 |
|---|---|---|---|
| fx | `server/fx/instantiate.py:432` `_guard_collision` | 이 번들 | **raise** `FxInstantiationError(VALUE_LINE_COLLISION)` |
| busking | `server/looks/busking.py:240` `_guard_collision` | 이 번들 | **skip** (plan → 빈 계획, 사유 `VALUE_LINE_COLLISION`) |
| songcue | `server/looks/songcue.py:436` + `emitted` 원장(`:243`) | 번들 전체 | **skip** → 큐리스트에 구멍 (명시 수용, `SONGCUE plan.md:97`) |

**씬은 fx 정책(raise)을 따른다.** 논거는 fx 자신의 독스트링이 이미 적어 두었다(`instantiate.py:436-439`):

> It refuses rather than skips because an fx bundle is ONE store; there is no surviving remainder to report.

**씬 번들도 정확히 하나의 Store다.** 건너뛸 잔여가 없다 — 룩만 저장하거나 이펙트만 저장하는 부분 산출은 씬의 정의상 존재하지 않는다. busking이 skip을 택한 이유는 *"룩 하나의 저작 결함으로 장르 전량을 실패시키면 버스킹 준비가 아무 산출도 내지 못한다"*(`busking.py:248-249`)인데, 씬에는 "전량"이 없으므로 그 논거가 적용되지 않는다. songcue가 구멍을 수용한 이유도 다중 큐 산출물 전제이며, 씬은 단일 큐다.

**씬의 충돌 표면은 fx보다 넓다.** 씬 번들은 룩 값 라인 **과** fx 스텝 값 라인을 함께 담으므로 비면제 라인 수가 fx 단독 번들보다 크다. 가드의 등급은 그만큼 더 높다.

### §4.2 2차 가드 — 지시 턴 경계, looks 쪽에는 대응물이 없다

**중요한 비대칭**: 2차(지시 턴 전체) 가드는 **fx에만 존재한다**. `server/fx/instantiate.py:537` `collided_lines`가 그것이고, `server/looks/**` 어디에도 대응물이 없다.

`collided_lines`의 독스트링이 경계를 정확히 적는다:

> The dedupe's real boundary is the whole instruction turn, not the bundle: `executed_ok` accumulates across tool calls, so a second instantiation in one turn folds from `Step 2` onward — that line is common to every pattern and is not in the exempt set, so even two UNRELATED patterns collide.

**씬은 2차 가드를 반드시 갖는다**(REQ-SCENE-015 (b)). 두 가지 구현 선택지:

| | (a) `server.fx.instantiate.collided_lines` 재사용 | (b) `server/scene/`에 병렬 구현 |
|---|---|---|
| PRESERVE | 위반 없음 — 공개 `__all__` 등재, 읽기 import | 위반 없음 |
| 결합 | fx 공개 API에 결합 | 결합 0 |
| 드리프트 | 없음 — 한 벌 | **두 벌이 갈라질 수 있음** |
| 사유 코드 | `CROSS_CALL_COLLISION` 재사용 | 씬 자기 코드 신설 |

**채택: (a) 재사용.** `collided_lines`는 `__all__`에 등재된 **공개 API**이고(`server/fx/instantiate.py:59`), 그 로직은 fx 고유가 아니라 **`run_commands` outcome 형상에 대한 순수 함수**다 — 인자가 `Sequence[object]` outcome이고 fx 스키마를 참조하지 않는다. 씬 전용 사본을 만들 이유가 없고, 만들면 §2.2가 경계한 바로 그 갈라짐이 생긴다.

**검출 시점이 실행 결과인 이유** (fx 독스트링 전재): 구성 시점에는 원리적으로 볼 수 없다 — `executed_ok`는 runner가 디스패치에 주입하는 컨텍스트라 빌더 계층에서 접근 불가다. 비어 있지 않은 반환은 **성공 보고를 금지**하며, Store는 자기 고유 문자열을 가져 실행되므로 **불완전한 시퀀스·큐가 이미 존재할 수 있다**는 사실을 리포트가 명시해야 한다.

### §4.3 v1 운용 경계 — 정직한 명시

한 지시 턴에서 `compile_scene`이 온전히 성립하는 것은 **1회뿐이다.** 2회차 이상은 2차 가드가 **명시 실패**로 보고한다 — 조용한 부분 성공을 만들지 않는다. 경계를 넓히려면 dedupe 규칙 자체를 다뤄야 하고 그 개정은 **기각된 선례**다(BUSKWIZ 결정). v1은 넓히는 대신 정직하게 막는다.

## §5. 번호 획득 — fx의 `Cue 1` 상수를 넘는 법

**문제**: `server/fx/instantiate.py:96`이 `_CUE_NUMBER = 1`을 상수로 고정하고, `:481`의 Store가 그것을 쓴다. 씬은 **임의 큐 번호**를 써야 하는데 `server/fx/**`는 PRESERVE다.

**해법**: 씬은 fx의 **Store 라인을 재사용하지 않는다.** §2.2 표가 보인 대로 씬이 상류에서 가져오는 것은 **값 라인 생성기**(`_step_lines` / `_phase_lines` / `_speed_line` / `_matricks`)뿐이고, **번들 조립과 Store 라인은 씬이 자기 것으로 만든다.** 이유는 두 가지이고 둘 다 강제다:

1. fx의 Store는 `Cue 1` 고정이다.
2. fx의 Store는 `/CueOnly`를 달지 않는다 — 씬 정책(D1)과 다르다.

즉 `build_fx_bundle`을 호출하고 결과를 후처리하는 설계는 **성립하지 않는다**(Store 라인을 문자열 치환해야 하고, 그건 §2.2가 금지한 재조립보다 나쁘다). 씬은 **자기 조립기**를 갖고 값 라인만 상류에서 받는다.

**시퀀스 번호**: `select_sequence_number`가 **두 벌** 존재한다 — `server/fx/instantiate.py:218`(공개, `requested=` 지원, 점유 번호 거부)과 `server/looks/songcue.py:286`(비공개적 용법, `children`/`i` 키 판독 포함). **씬은 fx 판을 소비한다**: `__all__` 등재 공개 API이고, `requested=` 인자가 있어 사용자 지정 시퀀스 번호를 지원하며, 점유 번호를 명시 거부한다 — 씬이 필요로 하는 계약과 정확히 일치한다. **세 번째 판을 쓰지 않는다.**

**큐 번호**: 씬 자기 로직이다. 재조회로 해당 시퀀스의 기존 큐 번호를 읽고 빈 정수 번호를 고른다. `truncated`가 참이면 **자동 배정을 거부**한다 — "비어 있음"은 도착한 번호들의 성질이 아니기 때문이다(fx `select_sequence_number` 독스트링의 논거를 큐 축에 적용). 사용자 지정 번호가 점유돼 있으면 거부한다.

## §6. `/CueOnly` — 한 번도 쏴본 적 없는 커맨드를 다루는 법

`/CueOnly`는 이 저장소에서 **발화 이력이 0건**이다(전수 grep — `server/**`·`ui/src/**`·`console/**`에 코드 0건, 룰북 산문 2곳뿐). 미검증 문법을 기본 경로에 넣는 것은 이 SPEC 계열의 규율 위반이다(FXLIB REQ-FXLIB-003 "미검증 문법이 프로브 대기 표시 없이 라이브러리에 등장하는 것은 금지"). 그러나 D1은 **사용자 확정**이다. 이 긴장을 다음과 같이 해소한다:

- **M0가 접수를 판정한다(ASSUMPTION-41).** 프로브에서 `/CueOnly` Store를 발화하고 (i) `ok:true` 접수와 (ii) **재조회로 그 큐가 기대한 이름·`cueNo`로 실존**하는지를 확인한다. 두 번째가 핵심이다 — `ok`만으로는 부족하다는 것이 이 SPEC 계열의 확립된 교훈이다.
- **날조 대조군 선행.** `ok`를 증거로 쓰기 전에 고의로 무효한 커맨드 1발을 먼저 발화해 그 축에서 `ok`가 **변별적**임을 확립한다(SONGCUE 선례).
- **부정 실측 시 조용한 폴백 금지.** `/CueOnly`가 거부되면(`Illegal object` 류) **run-phase를 중단하고 블로커를 보고**한다. 무플래그 Store로 조용히 내려앉는 것은 **사용자 확정 정책을 에이전트가 뒤집는 것**이므로 금지된다.
- **효과(트래킹 차단)는 M0에서도 기계로 판정되지 않는다(ASSUMPTION-42).** 사람 GUI 관측으로만 기록하며, **그 관측 결과와 무관하게 v1 형상은 불변**이다. 바뀌는 것은 리포트 문면의 정직도뿐이다.

**리포트가 지는 의무**: 세 주장을 분리한다(REQ-SCENE-014). 이는 SONGCUE가 확립한 규율의 계승이다 — 구현 선례가 `server/looks/songcue_report.py:15` `PROPERTY_UNOBSERVED_NOTE`이고, 그 정신은 REQ-SONGCUE-017의 *"두 경로를 뭉뚱그려 '확인했다'고 적는 것은 금지"* 다.

| 주장 | 증거 채널 | 리포트 표기 |
|---|---|---|
| 큐가 생성됐다 | 재조회(이름·`cueNo`) | **기계 확인됨** |
| 이펙트가 움직인다 / 룩이 발색한다 | 사람 GUI | **기계 확인 불가 — 사람 확인 필요** |
| 트래킹이 막혔다 | **없음** | **기계 확인 불가 — 관측 채널 부재** |

**상수 동일성 검사**: 이 문면들은 모듈 상수로 두고, 테스트는 `payload[...] == CONSTANT`로 확인한다 — 산문 부분 일치 비교는 금지다(선례 `server/tests/test_songcue_report.py:119`). FXLIB이 같은 형상의 상수를 갖는다(`server/fx/report.py:52` `EFFECT_EVIDENCE_NOTICE`).

### §6.1 상속된 부채 — SONGCUE는 오늘 무플래그로 쓴다

`server/looks/songcue.py:462-466`의 Store는 플래그가 없다. 즉 **SONGCUE가 만든 큐리스트의 값은 오늘 앞으로 트래킹되고 있다.** 이 사실은 저장소 어디에도 문서화·단언·측정돼 있지 않다 — SONGCUE spec/plan/acceptance 어디에도 트래킹 정책 결정이 없고, 그것이 이 부채가 **잠재**인 이유다.

씬 컴파일러가 `/CueOnly`를 채택하면 저장소에 **두 정책이 공존**하게 되고, 그 대비가 부채를 표면화한다. **본 SPEC은 그것을 기록하되 고치지 않는다** — `server/looks/**`는 PRESERVE이고, 소급 정책 변경은 별도 SPEC의 결정이다(spec.md §D). 기록의 목적은 후속 소유자가 "왜 두 정책이 다른가"를 재발견하느라 시간을 쓰지 않게 하는 것이다.

## §7. 위험 검토

| # | 위험 | 방어 |
|---|---|---|
| 1 | **병렬 슬라이스가 §3 결합 순서를 각자 해석** → 라이브러리와 빌더가 어긋남 | §3을 정본으로 고정 + 병렬 브리프에 **문면 그대로** 주입(plan.md §F). 불일치는 런타임 무신호이므로 **문면 동일성이 유일한 방어**다 |
| 2 | `/CueOnly` 접수 거부 (발화 이력 0건) | ASSUMPTION-41 · M0 1순위 · 부정 시 블로커(§6 — 조용한 폴백 금지) |
| 3 | **`/CueOnly` 접수를 트래킹 차단의 증거로 오독** | 3주장 분리 + 상수 동일성 검사(REQ-SCENE-014, §6) |
| 4 | 룩 값 라인이 스텝 1에 착지하지 않음 | ASSUMPTION-44 · M0 2순위 · 부정 시 결합 순서 재설계 블로커 |
| 5 | 룩/이펙트 attribute 충돌의 조용한 덮어쓰기 | 정적 교집합 계산 + 전수 열거(REQ-SCENE-005) — 관측 불요 |
| 6 | 값 라인 dedupe 탈락 → 불완전 Store | 1차 raise 가드(§4.1) + 2차 `collided_lines` 재사용(§4.2). 씬 번들은 값 라인이 많아 **fx보다 표면이 넓다** |
| 7 | 상류 비공개 함수 변경으로 씬이 조용히 깨짐 | 선례가 이미 진 리스크(§2.2) + `test_scene_boundary.py`의 산출 형상 고정(§8) |
| 8 | **면제 집합의 세 번째 사본** | 사본을 만들지 않는다 — `is_programmer_state` 공개 API 호출(§2.2). 사본이 없으므로 동치 단언 의무도 없다 |
| 9 | 큐 번호 발명·충돌 | 재조회 실측 + `truncated` 거부 + 기존 번호 `Not allowed` fail-closed가 마지막 방어(§5) |
| 10 | `/Merge` 습관적 사용으로 안전망 해제 | D3 · 대소문자 무관 부재 단언(AC-SCENE-010) |
| 11 | 트리거 소문자 토큰 / `/trig=` 형태 | Capitalized 폐쇄 집합 + `/trig=` 부재 단언(REQ-SCENE-016/017) |
| 12 | scene 모듈의 경계 침식 | `test_architecture.py` 자동 포섭 + AST 식별자 스캔 + 예외 명단 고정(REQ-SCENE-019) |

## §8. 테스트 설계 방향

- **순수 함수 우선, 인메모리 리그.** 스키마/로더/매칭/결합은 콘솔 무접촉. fake rig(그룹·시퀀스·큐 재조회 응답 주입)와 fake runner(호출 경로 기록)로 툴 계약을 닫는다.
- **실패 모드는 개별 테스트.** 로더 위반 종별·폴백 3종·Store 안전 시나리오를 하나의 파라미터화 테스트로 뭉치지 않는다 — 죽는 이유가 이름에 보여야 한다.
- **번들 규율은 문자열 수준 assert.** 정규화·재파싱 없이 산출 문자열 그대로 비교 — dedupe·게이트가 보는 것과 같은 표면을 본다.
- **상류 산출 형상 고정 (§2.2 결합의 대가를 갚는 테스트).** `test_scene_boundary.py`가 `_values_line` · `_step_lines`의 산출 형상을 알려진 입력에 대해 고정한다. 상류가 형상을 바꾸면 이 테스트가 먼저 죽어, 씬이 조용히 깨지는 대신 **시끄럽게** 깨진다.
- **리포트 문면은 상수 동일성.** `payload[...] == CONSTANT` — 부분 문자열 비교 금지(선례 `test_songcue_report.py:119`).
- **뮤테이션 확인 동반.** 각 가드형 AC는 위반 주입 시 실제로 죽는지 확인한다 — 공허하게 참인 방어선 금지.
- **테스트가 유일한 그물이다.** 효과가 기계로 확인되지 않으므로 형상 결함은 런타임에서 **아무 신호도 내지 않는다**. 결합 순서, `/CueOnly` 존재, `Step 1` 부재, 금지 형태 부재, 충돌 열거 — 이 다섯은 각각 독립 테스트로 세우고 뮤테이션으로 비공허성을 확인한다.

## §9. 반-패턴 (이 SPEC 근처의 유혹)

- **AP-1**: *"`instantiate_look` 다음에 `instantiate_fx`를 부르면 되잖아"* — **한 지시 턴에서 성립하지 않는다.** 2회차는 `Step 2`부터 접힌다(FXLIB `spec.md:146-148`). 게다가 두 툴은 각자 다른 산출물을 Store한다 — 하나의 큐가 나오지 않는다(§2.1).
- **AP-2**: *"이펙트를 먼저 놓고 룩으로 색만 덮자"* — 룩 값이 마지막 스텝에 얹혀 페이저의 종점이 된다. 스텝 1은 "현재 프로그래머 상태"이고 룩이 그것을 채워야 한다(§3.2).
- **AP-3**: *"`/CueOnly` 붙었으니 트래킹은 해결됐다고 적자"* — **접수 ≠ 효과.** 트래킹 차단은 관측 채널이 없다. 세 주장을 분리해 적는다(§6).
- **AP-4**: *"`/Merge` 달면 안전하겠지"* — 반대다. 새 큐 번호에서는 동작이 **동일**하고(SONGCUE 실측), 대신 기존 번호의 `Not allowed` 안전망이 꺼진다. 실익 0에 안전망만 잃는다(D3).
- **AP-5**: *"`build_fx_bundle` 부르고 Store 라인만 갈아끼우자"* — 문자열 치환은 §2.2가 금지한 재조립보다 나쁘다. 씬은 자기 조립기를 갖고 **값 라인만** 상류에서 받는다(§5).
- **AP-6**: *"면제 판정 정규식을 씬에도 한 벌 두자"* — **세 번째 사본**이다. `is_programmer_state`가 공개 API이므로 호출하면 된다(§2.2).
- **AP-7**: *"`Attribute 'Pan' At Step 2`로 스텝을 지정하자"* — **금지 형태.** `ok:true`를 받지만 효과가 없다(FXLIB M0 실측).
- **AP-8**: *"충돌 나면 룩이 이기게 하자, 사용자가 색을 지정했으니까"* — D2는 **이펙트 우선**으로 확정됐고, §3.1 골격이 그것을 강제한다. 우선순위를 뒤집으려면 골격을 뒤집어야 하고 그건 §3.2가 막는다.
- **AP-9**: *"충돌 열거는 나중에 붙이자"* — 조용한 덮어쓰기가 곧 결함이다. 열거는 정적 계산이라 비용이 거의 없다(§3.3).
- **AP-10**: *"SONGCUE도 `/CueOnly`로 고쳐두자"* — PRESERVE 위반. 기록하되 고치지 않는다(§6.1).
- **AP-11**: *"`Goto Cue`로 섹션 점프도 넣자"* — 게이트 `RECOGNIZED_REFERENCE_TYPES`에 `Cue`가 없다(`classify.py:44`). 게이트 어휘 확장을 요구하므로 보류다.
- **AP-12**: *"`CueFade`도 설정하자"* — 두 경로 모두 판독 불가다. 확인할 수 없는 것을 산출물에 넣지 않는다.
- **AP-13**: *"한 턴에 씬 두 개 만들어주자"* — 2회차는 접힌다. v1은 지시 턴당 1회다(§4.3).

## §10. 교차 참조

- **정본 요구**: spec.md §B (REQ-SCENE-001~020) · **인수**: acceptance.md (AC-SCENE-001~021)
- **결정 등록부**: plan.md §A.4 · **PRESERVE**: plan.md §A.5 · **병렬 분석**: plan.md §F
- **조사 근거**: research.md §2(`/CueOnly` 실측)·§3(코드 슬롯)·§4(가드 3선례)·§5(상속 부채)
- **본 문서의 공유 계약 절**: **§3**(결합 순서) · **§4**(가드 정책) — 병렬 브리프 인용 대상
- **선례**: FXLIB(미러 원형·M0 패턴·2차 가드·스텝 형상), LOOKLIB(값 라인·비공개 import 선례), SONGCUE(Store 안전·트리거·3주장 분리·상속 부채), BUSKWIZ(대소문자 무관 assert·익스큐터), PRECHK(판정 어휘·접두 행), OVERLAP(PRESERVE 게이트)
