# SPEC-COPILOT-FXLIB-001 — 설계 근거 (design)

## §1. 설계 의도

LOOKLIB이 "무엇을 켤까"(정지 화면)의 디자인 지식을 구조화했다면, FXLIB은 "어떻게 움직일까"(시간축)를 같은 파이프라인 형상으로 구조화한다. 설계의 제1원칙은 **미러이지 확장이 아니다**: looks 6파일(`{schema,loader,roles,resolver,instantiate,matching}.py`)+`library/`는 OVERLAP PRESERVE 잠금이고(OVERLAP spec.md:114-116 — busking/report는 본 SPEC이 추가 잠금) FXLIB은 자기 패키지(`server/fx/`)를 갖고, looks의 검증된 형상(스키마 폐쇄 필드 · 로더 명시 에러 · 매칭 폴백 · 번들 문자열 규율 · 한국어 리포트)을 **모방**한다. 두 번째 원칙은 **미검증 문법의 게이트 격리**: 룰북에 완전한 커맨드 라인 리터럴이 있는 것만 무조건 어휘이고, 조각만 있는 것(다단 — 완전 리터럴 부재)은 M0 실측 뒤에만 들어온다.

**제3원칙 — 스텝 축이 페이저의 생성 조건이다 (M0 2026-07-31 실측 귀결).** 페이저는 **2개 이상의 스텝**을 요구한다(제조사 문서 `help.malighting.com/grandMA3/2.0/HTML/phaser.html` — `[문서]`; 라이브 재현은 progress.md §E.2 — `[실측]`). `Relative` · `Phase` · `Speed`는 **이미 존재하는** 페이저를 **변형**하는 커맨드이지 **생성**하는 커맨드가 아니다. 따라서 v0.1.0의 번들 형상(값 라인 1개 + Phase + Speed)은 `ok:true`를 전량 받으면서도 **모션을 0회** 만든다 — M0 전반부의 실패 3회가 그 형상이었다. 본 개정(v0.2.0)은 모든 패턴이 `<값>` → `Step 2` → `<값>` **스텝 쌍**을 내도록 형상을 바꾸고, 스텝 축을 스키마의 1급 필수 필드로 승격시킨다. 아울러 M0는 **효과의 기계 증거 채널이 부정**임을 측정된 경계로 확정했다(§5 · REQ-FXLIB-014 (c)) — 이 SPEC에서 이펙트의 효과는 **사람의 GUI 관측이 유일한 증거 채널**이다.

## §2. 모듈 맵

| 파일 | 역할 | looks 대응 (미러 원형) |
|---|---|---|
| `server/fx/__init__.py` | 패키지 경계 문서(게이트 경유 원칙 독스트링) | `server/looks/__init__.py` |
| `server/fx/schema.py` | FX 데이터클래스 + 폐쇄 필드 + **스텝 축(§2.1)** + 어휘 3구간 상수 | `schema.py` (MovementSpec :86-102가 직계 원형) |
| `server/fx/loader.py` | YAML 로드 + 명시 에러 검증 | `loader.py` |
| `server/fx/matching.py` | 한국어 우선 매칭 + 폴백 3종 + 동점 None | `matching.py` |
| `server/fx/instantiate.py` | 번들 구성 + 값 라인 충돌 가드 + 시퀀스 번호 실측 | `instantiate.py` + `busking.py`(가드 사유) |
| `server/fx/report.py` | 한국어 2단 리포트 | `report.py` |
| `server/fx/library/*.yaml` | 내장 패턴 엔트리 (정적 자산) | `library/*.yaml` |
| `server/orchestrator/tools.py` | `find_fx` / `instantiate_fx` 등록 (2툴 추가만) | `find_looks` / `instantiate_look` |

**resolver가 없는 이유**: LOOKLIB의 리졸버는 역할 추상(백라이트/프론트…)→그룹 매핑을 위해 존재했다. FXLIB v1에는 역할 축이 없다 — 대상 그룹은 호출자가 지정하고 툴은 **실존 검증만** 한다(REQ-FXLIB-016). looks의 resolver를 읽기 import로 참조할 필요도 없다. 역할 축이 필요해지면(예: "백라이트만 웨이브") 그건 looks 역할 어휘의 **소비**이지 재정의가 아니며, 후속 개정에서 `server/looks/roles.py`를 읽기 import한다.

### §2.1 스키마의 스텝 축 — M0 귀결 (M1 구현 계약)

M0 실측으로 페이저 생성에는 **2개 이상의 스텝**이 필요함이 확립됐다(progress.md §E.2 — `<값>` → `Step 2` → `<값>`). v0.1.0이 계획한 페이저 축(`phase_from` / `phase_to` / `speed` / `relative`)만으로는 **어떤 엔트리도 페이저를 만들지 못한다**. 스키마는 스텝 축을 **필수 1급 필드**로 갖는다.

- **`steps`** — **필수**, 길이 **≥ 2**의 **순서 있는** 열. 인덱스 `i`가 콘솔 스텝 번호 `i+1`에 대응한다: 첫 원소는 현재 스텝(`Step 1` 라인을 **발화하지 않는다**), 둘째 원소부터 `Step <i+1>` 라인을 **선행 발화**한 뒤 그 스텝의 값 라인을 잇는다.
- 각 원소는 **attribute → 값**의 매핑이다(예: `{Dimmer: 100}`, `{Pan: -20, Tilt: -10}`). attribute 집합은 REQ-FXLIB-003 구간 1·2의 허용 집합 안이어야 한다.
- **값은 절대 수치만** 담는다. `At Relative <n>` 형이 **스텝 값**으로 성립하는지는 **미측정이다(ASSUMPTION-40)** — M0는 `Relative 30`을 1스텝(페이저 미성립) 문맥에서만 발화했으므로 그 문맥에서는 무엇도 판정될 수 없었다(raw-log-01.md §3 시도 3 — §7은 SUPERSEDED, §10이 정본). v1 라이브러리는 진폭을 **스텝 값의 차이**로 표현하고 `At Relative`를 **발화하지 않는다**.
- **페이저 변형 축**(`phase_from` / `phase_to` / `speed` / `relative` / `reverse` / MAtricks 5축)은 필드로 유지되되 의미가 재정의된다 — **스텝 축이 만든 페이저 위에 얹히는 후행 라인**이다. `steps` 없이 변형 축만 선언된 엔트리는 로더가 거부한다(REQ-FXLIB-005).
- **로더 검증 4종**: ① `len(steps) >= 2`, ② 스텝 원소의 attribute 집합이 전 스텝에서 동일(저작 규율 — 콘솔 사실이 아니라 형상 일관성 요구), ③ 같은 attribute의 스텝 값이 **패턴 내 서로 다름**(같은 값이면 2번째 라인이 dedupe로 접혀 페이저가 성립하지 않는다 — §5), ④ 변형 축 단독 선언 거부.
- **`Accel` / `Decel` 곡선 필드**: 스키마는 정의하되 **v1 라이브러리는 값으로 사용하지 않는다** — M0에서 `ok:true`는 받았으나 효과가 **미관측(SKIP)**이기 때문이다. LOOKLIB `MovementSpec`의 "정의하되 발화하지 않는다" 형상(`server/looks/schema.py:86-102`)을 **이 축에만** 적용한다.

## §3. fx-own 스키마 vs looks MovementSpec 확장 — 트레이드오프와 결정

| 축 | (a) looks MovementSpec 확장 | (b) fx-own 스키마 (채택) |
|---|---|---|
| PRESERVE 정합 | **불가** — `server/looks/schema.py` 수정은 OVERLAP PRESERVE 위반, 사용자 승인 필요 | 위반 없음 — 신규 파일만 |
| 소비자 파급 | MovementSpec은 P1-1/P1-2가 소비하는 공통 기반(looks schema.py @MX:NOTE) — 필드 추가가 두 하류를 동시에 흔든다 | 파급 0 — fx 스키마는 자기 소비자만 가진다 |
| 표현력 | MovementSpec은 페이저 1축(attribute/phase/speed/relative)만 — MAtricks·패턴 종별·다단·reverse를 담을 자리가 없다 | 필요한 축을 전부 1급 필드로 |
| 중복 비용 | 낮음 | attribute 이름 집합이 겹침 — **읽기 import**(`KNOWN_ATTRIBUTES` 참조)로 완화, 정의 소유는 fx가 별도 선언 |

**결정 (플랜 §A.4 결정 B)**: (b) fx-own. (a)는 PRESERVE 잠금 하나만으로도 탈락이며 — 이는 강제된 선택이지만, 강제가 없더라도 표현력 축에서 (b)가 옳다. looks import는 **읽기 전용**이고(`test_architecture.py`는 bridge import만 금지 — fx→looks 읽기 참조는 적법), looks 쪽 파일은 1바이트도 바뀌지 않는다.

**MovementSpec과의 관계 정직 표기**: looks의 MovementSpec은 "정의됐으나 발화되지 않는" 빈 슬롯이다(schema.py 독스트링 — "v1 defines this field but does not emit it"; instantiate.py의 movement 참조 0건; 라이브러리 movement 엔트리 0건; rig snapshot은 페이저를 구분 못함 — panel.py:78-82). FXLIB은 그 빈 슬롯을 **채우는 것이 아니라** 시간축 어휘를 자기 패키지에 세운다. MovementSpec은 looks 소비자(P1-1/P1-2)의 계약으로 남는다.

## §4. 번들 형상 (v0.2.0 — M0 스텝 축 반영)

> **v0.1.0 형상은 폐기됐다.** 이전 판의 두 예시(값 라인 1개 + Phase + Speed)는 **페이저를 만들지 못한다** — M0가 그 형상을 3회 발화해 `ok:true` 전량 + 모션 0회를 관측했다(raw-log-01.md §3). 아래가 정본이다.

### §4.0 앵커 — M0 실측 확정 형상 (Dimmer)

라이브에서 **생성과 저장 캡처를 동시에 증명한** 유일한 형상이다(progress.md §E.2 §10.1/§10.2 — 프로그래머를 `ClearAll`로 비운 뒤 저장물만 발화해 관측했으므로 관측 1건이 양쪽을 증명한다). 나머지 번들은 전부 이 골격의 파생이다.

```
# pulse (Dimmer 2스텝 페이저 + 위상 팬) — [실측] 앵커
ChangeDestination Root
ClearAll
Group 11
Attribute 'Dimmer' At 100                 # 스텝 1의 값 (Step 1 라인은 발화하지 않는다)
Step 2                                    # 스텝 2 생성
Attribute 'Dimmer' At 0                   # 스텝 2의 값 → 여기서 페이저가 성립한다
Attribute 'Dimmer' At Phase 0 Thru 360    # 선택 전체에 위상 팬 → 웨이브
Attribute 'Dimmer' At Speed 60            # BPM (ASSUMPTION-38 GO)
Store Sequence 12 Cue 1 'Dimmer Pulse'
ClearAll
```

**GUI 관측(사용자)**: 2스텝만 → *"깜빡인다 / 움직인다"*; 위상 확산 추가 → *"파도처럼 순차적으로"*(일제 점멸 아님).

### §4.1 sweep — Pan 축 (ASSUMPTION-40 게이트)

```
# sweep (Group 11, Pan 스텝 쌍 -20/20, phase 0→360, speed 60)
ChangeDestination Root
ClearAll
Group 11
Attribute 'Pan' At -20                    # 스텝 1의 값
Step 2
Attribute 'Pan' At 20                     # 스텝 2의 값 → 페이저 성립
Attribute 'Pan' At Phase 0 Thru 360
Attribute 'Pan' At Speed 60
Store Sequence 12 Cue 1 'Pan Sweep'
ClearAll
```

**게이트 표시**: 스텝 생성 형상은 **Dimmer로만 실측**됐다. Pan/Tilt로의 일반화는 **ASSUMPTION-40**(M7 측정)이며, 부정 실측의 비용은 Pan/Tilt 패턴 4종의 **효과**에 한정된다(스키마·로더·매칭·툴·리포트 무영향 — spec.md §C). `At Relative`는 v1이 발화하지 않는다(§2.1).

### §4.2 circle — Pan/Tilt 90° 위상차 + XWings 미러 분할 (ASSUMPTION-40 게이트)

```
# circle (Pan/Tilt 90° 위상차) + XWings 미러 분할
ChangeDestination Root
ClearAll
Group 11
Attribute 'Pan' At -20                    # 스텝 1
Attribute 'Tilt' At -10
Step 2
Attribute 'Pan' At 20                     # 스텝 2 → 페이저 성립
Attribute 'Tilt' At 10
Attribute 'Pan' At Phase 0
Attribute 'Tilt' At Phase 90
Attribute 'Pan' At Speed 45 ; Attribute 'Tilt' At Speed 45
Set Selection MAtricks 'XWings' 2
Store Sequence 13 Cue 1 'Circle Wings'
Reset Selection MAtricks
ClearAll
```

### §4.3 형상 규율

- **스텝 값 라인은 체이닝하지 않는다**: `;` 체이닝은 룰북 검증 리터럴이지만(`:39`), **스텝 문맥과의 조합은 미측정**이다. M0가 실측한 형태는 attribute 1개당 1줄이므로 스텝 값은 줄을 나눠 발화하고, `;`는 M0 전에도 형상이 같았던 Speed 라인에만 유지한다.
- **위 §4.1과 §4.2가 `Step 2`와 Pan 값 라인을 공유하는 것은 오타가 아니라 예시다**: 저작으로 값을 달리해도 **`Step 2`는 모든 패턴이 반드시 내는 공통 라인**이므로 교차 호출 충돌은 값 선택으로 회피할 수 없다. 그래서 회피가 아니라 **경계 명시**가 답이다 — v1은 지시 턴당 인스턴스화 1회이고 2회차는 명시 실패다(§5).
- `Step <k>`는 **단독 라인**으로만 발화한다. `Attribute '<attr>' At Step <k>`는 **금지 형태**다 — `ok:true`를 받으나 효과가 없다(REQ-FXLIB-022, progress.md §E.2).
- 전 라인이 룰북 검증 리터럴 골격 + M0 실측 형상이다(`:11-14, :27-31, :35-39, :68-73, :78-79, :85-90` · progress.md §E.2).
- `Reset Selection MAtricks`는 **Store 뒤**다 — 서브선택은 저장 대상 형상의 일부이므로 저장 전에 풀면 분할이 사라진다. Store 후 정리는 다음 번들 오염 방지(`:90` 취지).
- 트래킹 유의: `ClearAll`은 트래킹을 멈추지 않는다(`:128-134`). v1은 신규 시퀀스 Cue 1만 만들므로 트래킹 파급이 없다 — 기존 시퀀스에 큐를 **추가하지 않는 것**이 트래킹 안전의 형상적 근거다.
- **번들 규모**: 스텝 축이 패턴당 2-4줄을 더한다 — v1 번들은 ~12-18줄이다(v0.1.0 추정 ~10-15줄). ~66ms/줄 기준선 대비 여전히 여유가 크다(plan.md §C.4).

## §5. 값 라인 충돌 가드 설계

- **위협 모형**: dedupe의 실제 경계는 **지시 턴 전체(instruction-scoped)**다 — 비교 집합 `executed_ok`는 툴 호출을 넘어 축적되고(runner.py:216 `ExecutionContext(executed_ok=frozenset(executed_ok))`), 판정 지점(tools.py:603-609)의 주석 원문이 "either **in a prior tool call** (context.executed_ok) or earlier in THIS bundle"이다. 면제는 `_PROGRAMMER_STATE_COMMANDS` 3종(:283-287 — `Clear`/`ClearAll`/bare 선택)뿐이다. 값 라인이 중복 탈락하면 프로그래머가 불완전한 채 `Store`가 실행된다 — **무음 실패**(빈 프리셋/불완전 큐가 성공 보고됨). 위험 형상은 둘이다: (i) **번들 내 중복**(스텝 값 저작 결함 — M0 이후 **현실적** 위험으로 승격, 아래 정정 항 참조), (ii) **교차 호출** — 한 지시 턴에서 같은 패턴을 두 그룹에 인스턴스화하면(값 라인은 그룹 무관 문자열) 2번째 번들의 값 라인 전량이 `skipped_already_executed`로 접히고 Store(시퀀스 번호가 달라 유일)만 실행된다; 부분 실패 후 자기 교정 재시도 경로도 동일하다. BUSKWIZ가 실증했고, dedupe 규칙 개정은 기각됐다(형상+검출로 회피 — 결정 E).
- **정정 — v0.1.0의 "구조적 안전" 주장은 철회한다 (M0 귀결)**: 이전 판은 *"패턴이 내는 값 라인은 (attribute × 동사) 조합마다 1줄이라 **번들 내** 중복이 **구조적으로 없다**"*고 적었다. **스텝 축이 들어온 지금 이 문장은 거짓이다.** 한 패턴이 같은 attribute에 대해 스텝 수만큼 값 라인을 내며, `Attribute 'Dimmer' At 100`과 `Attribute 'Dimmer' At 0`은 (attribute × 동사)가 **같고 값만 다르다**. 번들 내 유일성은 이제 **구조가 주는 보장이 아니라 저작이 지켜야 할 제약**이다 — 같은 attribute의 두 스텝에 같은 값을 적으면 2번째 라인이 접히고 **스텝 1개짜리 프로그래머로 Store가 실행된다**. 그 결과는 M0 전반부의 실패 3회와 **정확히 같은 형상**(모션 0)이며, 이번에는 그것이 **무음으로** 일어난다.
- **가드의 역할 (경계 a — 구성 시점) — 승격**: 가드는 구성 완료 시점에 비면제 라인 집합의 유일성을 검사하고, 위반 시 `VALUE_LINE_COLLISION` 동형 사유(busking.py:230-237 계승 — "이 저장은 안전하게 일어날 수 없다" 부류)로 생성을 **거부**한다. v0.1.0에서 이 가드는 "구조가 이미 보장하는 성질을 못박는" 회귀 장벽이었다. **v0.2.0에서는 상시 발화 가능한 1급 검사다** — 스텝 값 저작 실수 하나가 곧 무음 실패이므로, 이 가드가 그 실수를 잡는 **유일한** 자동 장치다(효과는 기계로 확인되지 않으므로 테스트가 뒤에서 받아줄 수 없다). **단, 가드는 번들 내 경계만 지킨다** — 같은 지시 턴의 앞선 호출이 발화한 라인을 구성기는 원리적으로 볼 수 없다.
- **교차 호출 검출 (경계 b — 실행 결과 시점) — 승격**: the 툴은 실행 결과의 커맨드별 outcome을 검사해 **비면제 라인의 `skipped_already_executed`를 1건이라도 발견하면 성공 보고를 금지**하고 교차 호출 충돌을 명시 실패로 보고한다(REQ-FXLIB-011 (b) + REQ-FXLIB-014 (b) — 불완전 시퀀스·큐가 이미 생성됐을 수 있음을 문면에 명시). 검출 지점이 실행 결과인 이유: fx가 확실히 볼 수 있는 표면이 그것뿐이다 — `executed_ok`는 runner가 디스패치에 주입하는 컨텍스트라 구성기(server/fx)에서는 접근 불가. 디스패치가 ExecutionContext를 전달하므로(tools.py:496) 툴 등록 계층에서 실행 **전** `context.executed_ok` 대조·거부로 강화할 수 있는지는 M4/M5 착수 시 `[코드]` 실측한다(도달 가능하면 불완전 Store 자체를 차단하는 상위 방어).
- **교차 호출 위험의 실제 크기 (M0 이후 급상승)**: 스텝 값 라인은 어휘 전체에서 **가장 일반적인 문자열**이고(`At 100` / `At 0` / `At 20`…), 결정적으로 **`Step 2` 라인 자체가 전 패턴 공통 문자열**이다. `Step <k>`는 면제 3종(`Clear` / `ClearAll` / bare 선택 — tools.py:283-287 `[코드]` — 착수 직전 재실측 대상)에 속하지 않으므로, **같은 지시 턴의 2번째 인스턴스화는 `Step 2`부터 접힌다.** v0.1.0에서 교차 호출 충돌은 "두 그룹에 같은 패턴을 얹는" 특정 흐름의 위험이었지만, 이제는 **서로 다른 패턴끼리도** `Step 2` 한 줄로 충돌한다.
- **v1 운용 경계 (정직한 명시)**: 한 지시 턴에서 `instantiate_fx`가 온전히 성립하는 것은 **1회뿐이다.** 2회차 이상은 경계 (b)가 **명시 실패**로 보고한다 — 조용한 부분 성공을 만들지 않는다. 이 경계는 사용자 대면 리포트 문면에 실린다(REQ-FXLIB-014 (b)). 다중 인스턴스화를 한 턴에서 지원하려면 dedupe 경계 자체를 다뤄야 하고 그 개정은 기각된 선례이므로(결정 E), v1은 **경계를 넓히는 대신 정직하게 막는다**.
- **면제 판정의 소유 (순환 import 금지)**: 가드는 tools.py를 **import하지 않는다** — tools.py는 툴 등록 시 fx를 import하게 되므로(looks 선례 방향: tools.py:19-43) fx→tools top-level import는 **순환 import**다(tools가 부분 초기화 상태에서 ImportError). 미러 선례는 busking의 `_guard_collision`(busking.py:240-275): tools를 import하지 않고 **자기 빌더가 만든 라인만 대조**하며, 독스트링이 재조립 발산 위험까지 명시한다. FXLIB도 같은 형상을 채택한다 — **빌더가 전 라인을 생성하므로 빌더 자신이 각 라인의 면제/비면제를 분류한다**(판정 규칙의 재정의가 아니라 자기 산출물의 분류다). 두 집합의 어긋남 방지(가드가 통과시킨 라인을 dedupe가 떨어뜨리는 사고)는 경계 테스트가 소유한다: `test_fx_boundary.py`가 fx의 면제 분류 집합과 tools.py `_PROGRAMMER_STATE_COMMANDS`의 집합 동치를 assert한다(테스트는 양쪽을 import해도 무방 — 런타임 순환이 아니다).

## §6. 위험 검토

| # | 위험 | 방어 |
|---|---|---|
| 1 | 저장 큐가 페이저를 안 담는데 성공 보고 (무음 실패) | **M0 해소** — ASSUMPTION-36 GO(생성·저장 캡처 성립). 잔여는 위험 9로 이관 |
| 2 | `ok`를 효과 증거로 오독 | 날조 대조군 선행 규율 + **효과 기계 검증 불가의 무조건 명시** (REQ-FXLIB-014 (c)) |
| 3 | 값 라인 dedupe 탈락 → 불완전 Store (번들 내 + 교차 호출) | **등급 상승(M0)** — 스텝 축으로 번들 내 중복이 현실화(§5 정정). 가드 (a)는 상시 검사로 승격, 교차 호출은 outcome 검출 (REQ-FXLIB-011 (a)(b)) |
| 4 | 시퀀스 번호 발명·충돌 | 재조회 실측 + truncated 거부 + 무플래그 Store의 fail-closed(Not allowed)가 최종 방어 (REQ-FXLIB-012) |
| 5 | 미검증 다단 문법의 무단 진입 | **부분 해소** — 스텝 문법은 M0 GO로 구간 1 승격. `Accel`/`Decel`은 효과 미관측(SKIP)이므로 구간 3 잔류 + 로더 게이트 (REQ-FXLIB-003/005, AC-003 뮤테이션) |
| 6 | Speed 단위 오해로 의도와 다른 속도 | **M0 해소** — BPM 확정(ASSUMPTION-38 GO). 리포트 문면·시드 재보정에 반영 (결정 H) |
| 7 | fx 모듈의 경계 침식 (bridge 접근) | test_architecture 자동 포섭 + AST 스캔 + 예외 추가 금지 (REQ-FXLIB-017, AC-015) |
| 8 | M0 판정의 M7 덮어쓰기 (측정 이력 오염) | M7 재측정 금지 + 불일치는 불일치로 기록 (AC-022 뮤테이션). ASSUMPTION-40은 **신규 항목**이므로 M7 측정이 재측정에 해당하지 않는다 |
| 9 | **효과를 기계로 확인할 수 없다** (M0 측정된 경계) | 큐 내용·프로퍼티·픽스처 실시간 값 어느 쪽도 판독 불가 — 방어가 아니라 **한계의 문면화**가 대응이다: 리포트가 사람 확인 필요를 항상 명시(REQ-FXLIB-014 (c)), M7 인수는 GUI 관측 (AC-022) |
| 10 | **스텝 형상의 Pan/Tilt 미일반화** — sweep/wave/circle/diagonal이 모션 0일 가능성 | ASSUMPTION-40(M7) + 형상 게이트: 부정 비용을 Pan/Tilt 패턴 4종의 효과로 한정, 스키마·툴 계층 무영향 (spec.md §C) |
| 11 | **금지 형태 `At Step N` 혼입** — `ok:true`인데 효과 없음 | REQ-FXLIB-022 명시 금지 + AC-FXLIB-023 전수 assert(라이브러리·번들 양쪽) + 뮤테이션 |

## §7. 테스트 설계 방향

- **순수 함수 우선, 인메모리 리그**: 스키마/로더/매칭/번들은 콘솔 무접촉. fake rig(그룹·시퀀스 재조회 응답 주입)와 fake runner(호출 경로 기록)로 툴 계약을 닫는다.
- **실패 모드는 개별 테스트**: 로더 위반 종별·폴백 3종·Store 안전 시나리오를 하나의 파라미터화 테스트로 뭉치지 않는다 — 죽는 이유가 이름에 보여야 한다.
- **번들 규율은 문자열 수준 assert**: 정규화·재파싱 없이 산출 문자열 그대로 비교 — dedupe·게이트가 보는 것과 같은 표면을 본다.
- **뮤테이션 확인 동반**: 각 가드형 AC(003/009/010/015/023)는 위반 주입 시 실제로 죽는지 확인한다 — 공허하게 참인 방어선 금지.
- **스텝 축은 테스트가 유일한 그물이다**: 효과가 기계로 확인되지 않으므로(§6 위험 9) 스텝 형상의 결함은 런타임에서 **아무 신호도 내지 않는다**. `len(steps) >= 2`, 스텝 값의 패턴 내 유일성, `Step <k>` 단독 라인, 금지 형태 부재 — 이 넷은 각각 독립 테스트로 세우고 뮤테이션으로 비공허성을 확인한다.

## §8. 반-패턴 (이 SPEC 근처의 유혹)

- **AP-1**: "룰북이 validated라니까 다단도 되겠지" — 산문은 리터럴이 아니다. M0 없이 다단 진입 금지. (M0 결과는 **룰북이 옳았다**였다 — 그러나 옳음은 실측으로 확인된 뒤에 어휘가 되며, M0가 확인하기 전까지는 진입 금지가 맞았다.)
- **AP-8**: "`Attribute 'Pan' At Step 2`로 스텝을 지정하자" — **금지 형태다.** `ok:true`를 받지만 효과가 없다(M0 실측). 스텝 전환은 **단독 `Step <k>` 라인**뿐이다(REQ-FXLIB-022).
- **AP-9**: "`Phase`랑 `Speed`를 주면 페이저가 생긴다" — **거짓이다.** 그 둘은 **이미 존재하는** 페이저를 변형한다. 스텝 쌍 없이 발화하면 전 라인 `ok:true`에 모션 0이다(M0 §3의 실패 3회).
- **AP-10**: "스텝 값 두 개 다 100으로 두고 Phase로만 흔들자" — 2번째 값 라인이 dedupe로 접혀 스텝이 1개가 되고 페이저가 성립하지 않는다. 그것도 **무음으로**. 로더·가드가 거부한다(§2.1 로더 검증 ③, §5).
- **AP-11**: "한 턴에 두 그룹 다 걸어주자" — 2번째 번들은 `Step 2`부터 접힌다. v1은 지시 턴당 1회다(§5 v1 운용 경계).
- **AP-2**: "39/39 검증됐다" — 그 수치는 리포지토리에 존재하지 않는다. 인용 금지.
- **AP-3**: "재조회 안 되면 그냥 ok로 성공 보고" — 증거 채널의 한계는 리포트 문면에 실려야 한다. 침묵 금지.
- **AP-4**: "looks 스키마에 필드 몇 개만 추가하자" — PRESERVE 위반 + 하류 2 SPEC 파급. fx-own이 결정이다.
- **AP-5**: "빈 익스큐터 하나 잡아서 바로 걸어주자" — 빈 익스큐터는 식별 불가(BUSKWIZ 측정 2). 자동 Assign 금지.
- **AP-6**: "dedupe 면제에 값 라인 패턴 하나만 추가" — 기각된 선례의 재시도다. 형상으로 회피한다.
- **AP-7**: "기존 시퀀스에 Cue 2로 붙이면 편하다" — 트래킹 파급 + 무플래그 Store 거부. v1은 신규 시퀀스 Cue 1만.

## §9. 교차 참조

- **M0 라이브 프로브 정본**: progress.md §E.2 (판정 4건 + 확립된 스텝 문법 + 귀결 3건) · 원문 전량 `.moai/reports/m0-probe/raw-log-01.md` **§10**(§7은 SUPERSEDED, §0·§10.0은 자기 정정 2건)
- 정본 요구: spec.md §B (REQ-FXLIB-001~022), 인수: acceptance.md (AC-FXLIB-001~023)
- 결정 등록부: plan.md §A.4 (A~I — **I는 M0 폴드인 신설**), PRESERVE: plan.md §A.5
- 조사 근거: research.md §2(룰북)·§3(코드 슬롯)·§5(미검증 축)·§6(상속 판정)
- 선례: LOOKLIB(미러 원형·M0 패턴), BUSKWIZ(dedupe·값 라인·익스큐터), SONGCUE(Store 안전·truncation·날조 대조군), PRECHK(판정 어휘·접두 행), OVERLAP(PRESERVE 게이트·비제안서 출처)
