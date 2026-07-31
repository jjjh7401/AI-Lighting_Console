# SPEC-COPILOT-FXLIB-001 — 설계 근거 (design)

## §1. 설계 의도

LOOKLIB이 "무엇을 켤까"(정지 화면)의 디자인 지식을 구조화했다면, FXLIB은 "어떻게 움직일까"(시간축)를 같은 파이프라인 형상으로 구조화한다. 설계의 제1원칙은 **미러이지 확장이 아니다**: looks 6파일(`{schema,loader,roles,resolver,instantiate,matching}.py`)+`library/`는 OVERLAP PRESERVE 잠금이고(OVERLAP spec.md:114-116 — busking/report는 본 SPEC이 추가 잠금) FXLIB은 자기 패키지(`server/fx/`)를 갖고, looks의 검증된 형상(스키마 폐쇄 필드 · 로더 명시 에러 · 매칭 폴백 · 번들 문자열 규율 · 한국어 리포트)을 **모방**한다. 두 번째 원칙은 **미검증 문법의 게이트 격리**: 룰북에 완전한 커맨드 라인 리터럴이 있는 것만 무조건 어휘이고, 조각만 있는 것(다단 — 완전 리터럴 부재)은 M0 실측 뒤에만 들어온다.

## §2. 모듈 맵

| 파일 | 역할 | looks 대응 (미러 원형) |
|---|---|---|
| `server/fx/__init__.py` | 패키지 경계 문서(게이트 경유 원칙 독스트링) | `server/looks/__init__.py` |
| `server/fx/schema.py` | FX 데이터클래스 + 폐쇄 필드 + 어휘 3구간 상수 | `schema.py` (MovementSpec :86-102가 직계 원형) |
| `server/fx/loader.py` | YAML 로드 + 명시 에러 검증 | `loader.py` |
| `server/fx/matching.py` | 한국어 우선 매칭 + 폴백 3종 + 동점 None | `matching.py` |
| `server/fx/instantiate.py` | 번들 구성 + 값 라인 충돌 가드 + 시퀀스 번호 실측 | `instantiate.py` + `busking.py`(가드 사유) |
| `server/fx/report.py` | 한국어 2단 리포트 | `report.py` |
| `server/fx/library/*.yaml` | 내장 패턴 엔트리 (정적 자산) | `library/*.yaml` |
| `server/orchestrator/tools.py` | `find_fx` / `instantiate_fx` 등록 (2툴 추가만) | `find_looks` / `instantiate_look` |

**resolver가 없는 이유**: LOOKLIB의 리졸버는 역할 추상(백라이트/프론트…)→그룹 매핑을 위해 존재했다. FXLIB v1에는 역할 축이 없다 — 대상 그룹은 호출자가 지정하고 툴은 **실존 검증만** 한다(REQ-FXLIB-016). looks의 resolver를 읽기 import로 참조할 필요도 없다. 역할 축이 필요해지면(예: "백라이트만 웨이브") 그건 looks 역할 어휘의 **소비**이지 재정의가 아니며, 후속 개정에서 `server/looks/roles.py`를 읽기 import한다.

## §3. fx-own 스키마 vs looks MovementSpec 확장 — 트레이드오프와 결정

| 축 | (a) looks MovementSpec 확장 | (b) fx-own 스키마 (채택) |
|---|---|---|
| PRESERVE 정합 | **불가** — `server/looks/schema.py` 수정은 OVERLAP PRESERVE 위반, 사용자 승인 필요 | 위반 없음 — 신규 파일만 |
| 소비자 파급 | MovementSpec은 P1-1/P1-2가 소비하는 공통 기반(looks schema.py @MX:NOTE) — 필드 추가가 두 하류를 동시에 흔든다 | 파급 0 — fx 스키마는 자기 소비자만 가진다 |
| 표현력 | MovementSpec은 페이저 1축(attribute/phase/speed/relative)만 — MAtricks·패턴 종별·다단·reverse를 담을 자리가 없다 | 필요한 축을 전부 1급 필드로 |
| 중복 비용 | 낮음 | attribute 이름 집합이 겹침 — **읽기 import**(`KNOWN_ATTRIBUTES` 참조)로 완화, 정의 소유는 fx가 별도 선언 |

**결정 (플랜 §A.4 결정 B)**: (b) fx-own. (a)는 PRESERVE 잠금 하나만으로도 탈락이며 — 이는 강제된 선택이지만, 강제가 없더라도 표현력 축에서 (b)가 옳다. looks import는 **읽기 전용**이고(`test_architecture.py`는 bridge import만 금지 — fx→looks 읽기 참조는 적법), looks 쪽 파일은 1바이트도 바뀌지 않는다.

**MovementSpec과의 관계 정직 표기**: looks의 MovementSpec은 "정의됐으나 발화되지 않는" 빈 슬롯이다(schema.py 독스트링 — "v1 defines this field but does not emit it"; instantiate.py의 movement 참조 0건; 라이브러리 movement 엔트리 0건; rig snapshot은 페이저를 구분 못함 — panel.py:78-82). FXLIB은 그 빈 슬롯을 **채우는 것이 아니라** 시간축 어휘를 자기 패키지에 세운다. MovementSpec은 looks 소비자(P1-1/P1-2)의 계약으로 남는다.

## §4. 번들 형상

패턴 2종의 대표 번들 (문자열 수준 — `test_fx_instantiate.py`가 이 형상을 assert):

```
# sweep (Group 11, phase 0→360, speed 60, relative 30)
ChangeDestination Root
ClearAll
Group 11
Attribute 'Pan' At Relative 30
Attribute 'Pan' At Phase 0 Thru 360
Attribute 'Pan' At Speed 60
Store Sequence 12 Cue 1 'Pan Sweep'
ClearAll
```

```
# circle (Pan/Tilt 90° 위상차) + XWings 미러 분할
ChangeDestination Root
ClearAll
Group 11
Attribute 'Pan' At Relative 20
Attribute 'Tilt' At Relative 20
Attribute 'Pan' At Phase 0
Attribute 'Tilt' At Phase 90
Attribute 'Pan' At Speed 45 ; Attribute 'Tilt' At Speed 45
Set Selection MAtricks 'XWings' 2
Store Sequence 13 Cue 1 'Circle Wings'
Reset Selection MAtricks
ClearAll
```

- 전 라인이 룰북 검증 리터럴 골격이다(`:11-14, :27-31, :35-39, :68-71, :78-79, :85-90`). `;` 체이닝은 attribute가 다른 독립 세트에만 쓴다(`:39`).
- `Reset Selection MAtricks`는 **Store 뒤**다 — 서브선택은 저장 대상 형상의 일부이므로 저장 전에 풀면 분할이 사라진다. Store 후 정리는 다음 번들 오염 방지(`:90` 취지).
- 트래킹 유의: `ClearAll`은 트래킹을 멈추지 않는다(`:128-134`). v1은 신규 시퀀스 Cue 1만 만들므로 트래킹 파급이 없다 — 기존 시퀀스에 큐를 **추가하지 않는 것**이 트래킹 안전의 형상적 근거다.

## §5. 값 라인 충돌 가드 설계

- **위협 모형**: dedupe의 실제 경계는 **지시 턴 전체(instruction-scoped)**다 — 비교 집합 `executed_ok`는 툴 호출을 넘어 축적되고(runner.py:216 `ExecutionContext(executed_ok=frozenset(executed_ok))`), 판정 지점(tools.py:603-609)의 주석 원문이 "either **in a prior tool call** (context.executed_ok) or earlier in THIS bundle"이다. 면제는 `_PROGRAMMER_STATE_COMMANDS` 3종(:283-287 — `Clear`/`ClearAll`/bare 선택)뿐이다. 값 라인이 중복 탈락하면 프로그래머가 불완전한 채 `Store`가 실행된다 — **무음 실패**(빈 프리셋/불완전 큐가 성공 보고됨). 위험 형상은 둘이다: (i) **번들 내 중복**(단일 번들 저작 결함), (ii) **교차 호출** — 한 지시 턴에서 같은 패턴을 두 그룹에 인스턴스화하면(값 라인은 그룹 무관 문자열) 2번째 번들의 값 라인 전량이 `skipped_already_executed`로 접히고 Store(시퀀스 번호가 달라 유일)만 실행된다; 부분 실패 후 자기 교정 재시도 경로도 동일하다. BUSKWIZ가 실증했고, dedupe 규칙 개정은 기각됐다(형상+검출로 회피 — 결정 E).
- **v1의 구조적 안전 (번들 내)**: 1호출 = 1시퀀스 = 1큐 = 그룹 선택 1회. 패턴이 내는 값 라인은 (attribute × 동사) 조합마다 1줄이라 **번들 내** 중복이 **구조적으로 없다**.
- **가드의 역할 (경계 a — 구성 시점)**: 그 성질을 **assert로 못박는다** — 구성 완료 시점에 비면제 라인 집합의 유일성을 검사하고, 위반 시 `VALUE_LINE_COLLISION` 동형 사유(busking.py:230-237 계승 — "이 저장은 안전하게 일어날 수 없다" 부류)로 생성을 거부한다. 이는 현재를 지키는 방어선이자, 미래의 다중 큐/다중 FX 배칭 확장이 이 위험을 조용히 재도입하는 것을 막는 회귀 장벽이다. **단, 이 가드는 번들 내 경계만 지킨다** — 같은 지시 턴의 앞선 호출이 발화한 라인을 구성기는 원리적으로 볼 수 없다.
- **교차 호출 검출 (경계 b — 실행 결과 시점)**: the 툴은 실행 결과의 커맨드별 outcome을 검사해 **비면제 라인의 `skipped_already_executed`를 1건이라도 발견하면 성공 보고를 금지**하고 교차 호출 충돌을 명시 실패로 보고한다(REQ-FXLIB-011 (b) + REQ-FXLIB-014 (b) — 불완전 시퀀스·큐가 이미 생성됐을 수 있음을 문면에 명시). 검출 지점이 실행 결과인 이유: fx가 확실히 볼 수 있는 표면이 그것뿐이다 — `executed_ok`는 runner가 디스패치에 주입하는 컨텍스트라 구성기(server/fx)에서는 접근 불가. 디스패치가 ExecutionContext를 전달하므로(tools.py:496) 툴 등록 계층에서 실행 **전** `context.executed_ok` 대조·거부로 강화할 수 있는지는 M4/M5 착수 시 `[코드]` 실측한다(도달 가능하면 불완전 Store 자체를 차단하는 상위 방어).
- **면제 판정의 소유 (순환 import 금지)**: 가드는 tools.py를 **import하지 않는다** — tools.py는 툴 등록 시 fx를 import하게 되므로(looks 선례 방향: tools.py:19-43) fx→tools top-level import는 **순환 import**다(tools가 부분 초기화 상태에서 ImportError). 미러 선례는 busking의 `_guard_collision`(busking.py:240-275): tools를 import하지 않고 **자기 빌더가 만든 라인만 대조**하며, 독스트링이 재조립 발산 위험까지 명시한다. FXLIB도 같은 형상을 채택한다 — **빌더가 전 라인을 생성하므로 빌더 자신이 각 라인의 면제/비면제를 분류한다**(판정 규칙의 재정의가 아니라 자기 산출물의 분류다). 두 집합의 어긋남 방지(가드가 통과시킨 라인을 dedupe가 떨어뜨리는 사고)는 경계 테스트가 소유한다: `test_fx_boundary.py`가 fx의 면제 분류 집합과 tools.py `_PROGRAMMER_STATE_COMMANDS`의 집합 동치를 assert한다(테스트는 양쪽을 import해도 무방 — 런타임 순환이 아니다).

## §6. 위험 검토

| # | 위험 | 방어 |
|---|---|---|
| 1 | 저장 큐가 페이저를 안 담는데 성공 보고 (무음 실패) | ASSUMPTION-36을 M0 1순위로 — CONDITION_NOT_MET면 run-phase 중단 + 블로커 (plan.md §B M0) |
| 2 | `ok`를 효과 증거로 오독 | 날조 대조군 선행 규율 + 리포트 증거 상태 문면 (REQ-FXLIB-014 (c)) |
| 3 | 값 라인 dedupe 탈락 → 불완전 Store (번들 내 + 교차 호출) | §5 가드(번들 내) + 형상 보장 + 교차 호출 outcome 검출 (REQ-FXLIB-011 (a)(b)) |
| 4 | 시퀀스 번호 발명·충돌 | 재조회 실측 + truncated 거부 + 무플래그 Store의 fail-closed(Not allowed)가 최종 방어 (REQ-FXLIB-012) |
| 5 | 미검증 다단 문법의 무단 진입 | 어휘 3구간 + 로더 게이트 검증 (REQ-FXLIB-003/005, AC-003 뮤테이션) |
| 6 | Speed 단위 오해로 의도와 다른 속도 | 단위 해석의 M0 기록 + 리포트 문면 반영 (ASSUMPTION-38, 결정 H) — 값 자체는 안전(위험 등급 아님) |
| 7 | fx 모듈의 경계 침식 (bridge 접근) | test_architecture 자동 포섭 + AST 스캔 + 예외 추가 금지 (REQ-FXLIB-017, AC-015) |
| 8 | M0 판정의 M7 덮어쓰기 (측정 이력 오염) | M7 재측정 금지 + 불일치는 불일치로 기록 (AC-022 뮤테이션) |

## §7. 테스트 설계 방향

- **순수 함수 우선, 인메모리 리그**: 스키마/로더/매칭/번들은 콘솔 무접촉. fake rig(그룹·시퀀스 재조회 응답 주입)와 fake runner(호출 경로 기록)로 툴 계약을 닫는다.
- **실패 모드는 개별 테스트**: 로더 위반 종별·폴백 3종·Store 안전 시나리오를 하나의 파라미터화 테스트로 뭉치지 않는다 — 죽는 이유가 이름에 보여야 한다.
- **번들 규율은 문자열 수준 assert**: 정규화·재파싱 없이 산출 문자열 그대로 비교 — dedupe·게이트가 보는 것과 같은 표면을 본다.
- **뮤테이션 확인 동반**: 각 가드형 AC(003/009/010/015)는 위반 주입 시 실제로 죽는지 확인한다 — 공허하게 참인 방어선 금지.

## §8. 반-패턴 (이 SPEC 근처의 유혹)

- **AP-1**: "룰북이 validated라니까 다단도 되겠지" — 산문은 리터럴이 아니다. M0 없이 다단 진입 금지.
- **AP-2**: "39/39 검증됐다" — 그 수치는 리포지토리에 존재하지 않는다. 인용 금지.
- **AP-3**: "재조회 안 되면 그냥 ok로 성공 보고" — 증거 채널의 한계는 리포트 문면에 실려야 한다. 침묵 금지.
- **AP-4**: "looks 스키마에 필드 몇 개만 추가하자" — PRESERVE 위반 + 하류 2 SPEC 파급. fx-own이 결정이다.
- **AP-5**: "빈 익스큐터 하나 잡아서 바로 걸어주자" — 빈 익스큐터는 식별 불가(BUSKWIZ 측정 2). 자동 Assign 금지.
- **AP-6**: "dedupe 면제에 값 라인 패턴 하나만 추가" — 기각된 선례의 재시도다. 형상으로 회피한다.
- **AP-7**: "기존 시퀀스에 Cue 2로 붙이면 편하다" — 트래킹 파급 + 무플래그 Store 거부. v1은 신규 시퀀스 Cue 1만.

## §9. 교차 참조

- 정본 요구: spec.md §B (REQ-FXLIB-001~021), 인수: acceptance.md (AC-FXLIB-001~022)
- 결정 등록부: plan.md §A.4 (A~H), PRESERVE: plan.md §A.5
- 조사 근거: research.md §2(룰북)·§3(코드 슬롯)·§5(미검증 축)·§6(상속 판정)
- 선례: LOOKLIB(미러 원형·M0 패턴), BUSKWIZ(dedupe·값 라인·익스큐터), SONGCUE(Store 안전·truncation·날조 대조군), PRECHK(판정 어휘·접두 행), OVERLAP(PRESERVE 게이트·비제안서 출처)
