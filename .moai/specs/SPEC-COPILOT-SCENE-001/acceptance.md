# SPEC-COPILOT-SCENE-001 — 인수 기준 (acceptance)

> 검증 철학 3줄: (1) **`Cmd` 접수 `ok`는 효과 증거가 아니다** — 효과는 재조회 또는 명시된 관측 채널로만, 그리고 `ok`를 증거로 쓰기 전에 **날조 대조군**으로 그 축의 변별력을 먼저 확립한다(SONGCUE 선례). (2) 라이브 AC는 정확히 2건(AC-SCENE-019 M0 · AC-SCENE-021 M8)이며 나머지 22건은 콘솔 무접촉으로 판정 가능하다. (3) 부분 성공을 전체 성공으로 위장하지 않는다.
>
> **이 문서를 읽는 사람이 먼저 알아야 할 것**: 본 SPEC에서 **효과(모션·발색)와 트래킹 차단은 기계로 검증되지 않는다**(spec.md §C.1 — 큐 내용을 돌려주는 경로가 존재하지 않는다). 따라서 아래 AC 대부분은 "효과"가 아니라 **형상·계약·거부 동작**을 검증한다. 형상 결함이 런타임에서 아무 신호도 내지 않으므로 **테스트가 유일한 그물이다**(design.md §8).
>
> 그리고 이 SPEC에는 다른 SPEC에 없는 축이 하나 더 있다: **트래킹 정책이 M0 실측으로 한 번 뒤집혔다.** `/CueOnly`(미발화 커맨드)를 버리고 **속성 집합 균일화 + 미주장 속성 전수 열거**를 택했으나 — **관측 천장은 바뀌지 않았다.** 그래서 "균일 집합을 발화했다"와 "트래킹이 무해해졌다"를 뭉치지 않는 것이 AC 설계의 축이다(AC-SCENE-015). 정책은 바뀌었고 인지 함정은 그대로다.

## §A. 개요

AC는 **24건**이다. §C.0이 REQ(**21건**) ↔ AC 역추적을, §C.0a가 마일스톤 배정(합 **24** · 중복 0 · 누락 0)을 고정한다.

## §B. Given-When-Then 시나리오

### 시나리오 1 — 룩 + 이펙트 합성의 종단 적용 (행복 경로)

- **Given** 이름 있는 그룹이 존재하는 리그, 빈 시퀀스·큐 번호가 재조회로 실측 가능, LiveLock 비활성.
- **When** 사용자가 "파란 백라이트가 천천히 웨이브하는 씬 만들어줘"라고 지시한다.
- **Then** `find_scene`이 룩 축(파란·백라이트)과 이펙트 축(천천히·웨이브)을 분리 해석해 씬을 매칭하고, `compile_scene`이 **design.md §3.1 순서**로 단일 번들을 조립한다: 룩 값 라인이 fx 스텝 열 **앞**에 오고 **균일 집합 4개를 이 순서로** 담으며, Store는 **플래그 0건**이고, 산출물은 **시퀀스 1개 + 큐 1개**다. 한국어 2단 리포트가 **주장을 분리해** 보고한다 — 큐 생성·균일성은 기계 확인, 효과는 사람 확인 필요, 트래킹 무해화는 관측 채널 부재, 그리고 **이 씬이 주장하지 않는 속성이 전수 열거**된다.

### 시나리오 2 — 룩/이펙트 attribute 충돌의 명시적 열거

- **Given** 룩이 `Dimmer At 80`을 담고 이펙트가 `Dimmer` 스텝 열(100/0)을 담는 씬.
- **When** `compile_scene`이 호출된다.
- **Then** 이펙트가 승자다(§3.1 골격이 fx 라인을 뒤에 두므로 형상이 강제한다). **그리고 `Dimmer`가 "덮인 attribute" 목록에 실려 리포트에 나타난다.** 열거가 비어 있으면 이 시나리오는 실패다 — 조용한 덮어쓰기는 결함이다.

### 시나리오 3 — 부분 매칭의 정직한 신호

- **Given** 이펙트 축은 명확하나 룩 축이 모호한 지시("웨이브하는 뭔가").
- **When** `find_scene`이 호출된다.
- **Then** 매칭기는 **부분 매칭 신호**를 무매칭과 구분해 반환한다. 이펙트 단독 씬을 세우는 것은 적법하지만, **룩 축을 임의 기본값으로 채우는 것은 금지**된다.

### 시나리오 4 — Store 안전 방향 (`/Merge` 없음, 점유 번호 없음)

- **Given** 사용자가 지정한 큐 번호가 이미 점유돼 있다(또는 재조회가 `truncated=참`).
- **When** `compile_scene`이 호출된다.
- **Then** 덮어쓰기도 재슬롯도 없다: 점유 번호는 무플래그 Store의 `Not allowed` 거부에 **앞서** 툴이 거부·보고하고, `truncated`에서는 자동 배정을 거부한다. `/Overwrite`와 **`/Merge`** 는 어떤 경로로도 발화되지 않는다(대소문자 무관).

### 시나리오 5 — 값 라인 충돌의 생성 전 차단

- **Given** 구성된 번들에 비면제 커맨드 문자열이 중복으로 들어가는 형상(가정 주입). **씬에서 가장 현실적인 주입은 룩과 이펙트가 같은 attribute·같은 값을 내는 엔트리다.**
- **Then** 번들은 콘솔로 가지 않는다 — 구성기가 `VALUE_LINE_COLLISION` 동형 사유로 생성을 **거부(raise)** 한다. 건너뛰기가 아닌 이유: 씬 번들은 하나의 Store이고 보고할 잔여가 없다(design.md §4.1).
- **그리고(교차 호출)** 같은 지시 턴의 앞선 호출이 이미 발화한 라인과 겹치면 — 구성 시점에는 보이지 않으므로 — 실행 outcome의 비면제 `skipped_already_executed` 검출이 성공 보고를 차단하고 명시 실패로 보고한다. **`Step 2` 라인이 씬 간 공통이므로 이 경로는 서로 다른 씬 사이에서도 성립한다** — v1은 지시 턴당 컴파일 1회가 운용 경계다.

### 시나리오 6 — LiveLock 중 제안 강등

- **Given** LiveLock 활성.
- **When** `compile_scene`이 호출된다.
- **Then** 콘솔 송신 0건 — **Store 라인을 포함해** 전 커맨드가 `status == "proposal"`이고, `is_error is False`(강등은 실패가 아니라 답이다), `succeeded is False`다.

## §C. AC (GEARS 형식 — 검증 레시피는 각 AC 하위 상세)

### §C.0 REQ ↔ AC 역추적표

**토큰 규율**: 본 표는 **완전형 토큰만** 쓴다 — 축약(`AC-001`)은 완전형 grep(`grep 'AC-SCENE-005'`)이 자기 역추적 행을 반환하지 못하게 만들어 **기계 확인 가능한 역추적을 무효화**한다(progress.md §0 인용 규율: *"요구·인수 토큰은 슬러그 포함 완전형만(축약 0건)"*).

| REQ | AC |
|---|---|
| REQ-SCENE-001 | AC-SCENE-001 |
| REQ-SCENE-002 | AC-SCENE-003 |
| REQ-SCENE-003 | AC-SCENE-002 |
| REQ-SCENE-004 | AC-SCENE-004 |
| REQ-SCENE-005 | AC-SCENE-005 |
| REQ-SCENE-006 | AC-SCENE-001, AC-SCENE-002 |
| REQ-SCENE-007 | AC-SCENE-006 |
| REQ-SCENE-008 | AC-SCENE-007 |
| REQ-SCENE-009 | AC-SCENE-008 |
| REQ-SCENE-010 | AC-SCENE-009 |
| REQ-SCENE-011 | AC-SCENE-009, AC-SCENE-012 |
| REQ-SCENE-012 | AC-SCENE-023 |
| REQ-SCENE-013 | AC-SCENE-010, AC-SCENE-013 |
| REQ-SCENE-014 | AC-SCENE-015, AC-SCENE-016, AC-SCENE-024 |
| REQ-SCENE-015 | AC-SCENE-011 |
| REQ-SCENE-016 | AC-SCENE-014 |
| REQ-SCENE-017 | AC-SCENE-014 |
| REQ-SCENE-018 | AC-SCENE-018 |
| REQ-SCENE-019 | AC-SCENE-017 |
| REQ-SCENE-020 | AC-SCENE-020 |
| REQ-SCENE-021 | AC-SCENE-019, AC-SCENE-021 |
| (횡단 — 회귀) | AC-SCENE-022 |

**미커버 REQ 0건 · 앵커 없는 AC 1건**(AC-SCENE-022 — 전체 회귀는 성질상 특정 REQ에 귀속되지 않는다). 개정 전 앵커 없던 AC-SCENE-019, AC-SCENE-021은 **REQ-SCENE-021 신설로 앵커를 얻었다.**

### §C.0a 마일스톤 배정표 (합 24 · 중복 0 · 누락 0)

| 마일스톤 | AC | 수 |
|---|---|---|
| M0 | AC-SCENE-019 | 1 |
| M1 | AC-SCENE-001, AC-SCENE-002 | 2 |
| M2 | AC-SCENE-003, AC-SCENE-004 | 2 |
| M3 | AC-SCENE-006, AC-SCENE-007, AC-SCENE-008 | 3 |
| M4 | AC-SCENE-005, AC-SCENE-009, AC-SCENE-010, AC-SCENE-011, AC-SCENE-012, AC-SCENE-013, AC-SCENE-014, AC-SCENE-023 | 8 |
| M5 | AC-SCENE-015, AC-SCENE-016, AC-SCENE-024 | 3 |
| M6 | AC-SCENE-018 | 1 |
| M7 | AC-SCENE-017, AC-SCENE-020, AC-SCENE-022 | 3 |
| M8 | AC-SCENE-021 | 1 |
| **합** | | **24** |

### §C.1 AC 상세

### AC-SCENE-001 — 스키마 로딩 + 명시 에러 (REQ-SCENE-001, REQ-SCENE-006)

- **When** 정상 라이브러리를 로드하면 the 로더 **shall** 전 엔트리를 스키마 형상으로 반환하고, 위반 주입 각각에 대해 **개별 명시 에러**를 낸다. 위반 종별 5종: ① 미지 필드, ② 중복 scene id, ③ `look_id`·`fx_id` 동시 부재(AC-SCENE-002가 소유), ④ 수치 범위 이탈(`cue_number` ≤ 0 또는 비정수, `trig_time` < 0), ⑤ 미지 `trig_type`(폐쇄 집합 `Go`/`Time`/`Follow`/`Sound`/`BPM` 밖 — **소문자 변형도 거부**).
- 검증: `test_scene_schema.py` — 위반 종별마다 독립 테스트(병합 금지).
- 뮤테이션: 소문자 `trig_type` 검사를 지우면 이 AC가 죽어야 한다. 트리거 토큰이 Capitalized여야 한다는 것은 룰북 명시 사실이다(`31_choreography_patterns.md:115`).

### AC-SCENE-002 — 참조 최소 1개 필수 (REQ-SCENE-003, REQ-SCENE-006)

- the 로더·툴 **shall** `look_id`와 `fx_id`가 **모두 부재**한 씬을 명시 에러로 거부한다 — 합성할 것이 없는 씬은 씬이 아니다. 룩 단독·이펙트 단독은 **적법**하므로 그 두 경우가 통과함을 대조군으로 함께 단언한다(비공허성).
- 검증: `test_scene_schema.py` — 3케이스(둘 다 있음 / 룩만 / fx만) 통과 + 1케이스(둘 다 없음) 거부.
- 뮤테이션: 동시 부재 검사를 지우면 이 AC가 죽어야 한다.

### AC-SCENE-003 — 라이브러리 커버리지 + 실존 참조 (REQ-SCENE-002)

- 내장 라이브러리 **shall** 룩+이펙트 결합 씬 ≥ 3, 룩 단독 씬 ≥ 1, 이펙트 단독 씬 ≥ 1, **충돌 있는 씬 ≥ 1**을 담고, 전 엔트리가 한국어 무드 키워드 ≥ 1을 가지며, **모든 `look_id`·`fx_id`가 상류 라이브러리에서 실제로 해석된다**(끊긴 참조 0건).
- 검증: `test_scene_library.py` — 상류 LOOKLIB·FXLIB 라이브러리를 실제로 로드해 전 참조를 해석. 존재하지 않는 id를 주입하면 죽는 뮤테이션 포함.
- **충돌 씬 ≥ 1이 요구되는 이유**: AC-SCENE-005의 충돌 열거 경로가 **자산으로도** 실증돼야 한다. 합성 테스트 픽스처만으로 검증하면 라이브러리 증보 시 발현을 놓친다.

### AC-SCENE-004 — per-show 값 부재 (REQ-SCENE-004)

- 라이브러리 자산 전수에서 그룹 번호/이름·FID·익스큐터 번호 필드 **shall** 0건 — 스키마에 그런 필드 자체가 없고 로더가 미지 필드를 거부한다. 타이밍 축(시퀀스·큐 번호)은 **호출 인자**이지 정적 자산 필드가 아님을 함께 단언한다.
- 검증: `test_scene_library.py` + 스키마 필드 집합 assert.

### AC-SCENE-005 — 충돌 attribute 전수 열거 (REQ-SCENE-005)

- **When** 룩과 이펙트가 같은 attribute를 지정하면, the 컴파일러 **shall** 이펙트를 승자로 삼고(형상이 강제 — §3.1), **덮인 attribute 전량을 열거해** 컴파일 결과에 싣는다.
- 검증: `test_scene_compile.py` — ① 충돌 있는 씬에서 열거가 **정확히** 교집합과 일치(부분집합·상위집합 모두 실패), ② 충돌 없는 씬에서 열거가 **빈 집합**(위양성 없음), ③ 산출 번들에서 이펙트 라인이 룩 라인보다 **뒤에** 온다.
- 뮤테이션: 열거를 빈 값으로 고정하면 죽어야 한다. 교집합 대신 합집합을 내도 죽어야 한다.
- **이 계산은 콘솔에 묻지 않는다** — 컴파일 시점 정적 교집합이므로 관측 채널과 무관하게 정확하다(design.md §3.3). 그래서 이 AC는 기계로 완전히 판정 가능한 몇 안 되는 "동작" AC다.

### AC-SCENE-006 — 2축 매칭 규율 (REQ-SCENE-007)

- 매칭기 **shall** 한국어 조사가 붙은 지시("웨이브로", "파란색을")를 처리하고, 룩 축과 이펙트 축을 분리 해석하며, 동점에서 None을 반환하고, 같은 입력에 같은 출력을 낸다(결정론).
- 검증: `test_scene_matching.py` — 조사 변형·2축 분리·동점·결정론 각각 독립 테스트.
- 뮤테이션: 동점에서 첫 후보를 임의 반환하면 죽어야 한다.

### AC-SCENE-007 — 부분 매칭 신호 (REQ-SCENE-008)

- **When** 두 축 중 한쪽만 신뢰 매칭되면, the 매칭기 **shall** 부분 매칭 신호를 **무매칭과 구분해** 반환하고, **매칭되지 않은 축을 임의 기본값으로 채우지 않는다**.
- 검증: `test_scene_matching.py` — 룩만 매칭 / fx만 매칭 / 둘 다 매칭 / 둘 다 무매칭 4케이스가 **서로 구분되는** 신호를 낸다.
- 뮤테이션: 부분 매칭에서 나머지 축을 라이브러리 첫 엔트리로 채우면 죽어야 한다.

### AC-SCENE-008 — 폴백 신호 (REQ-SCENE-009)

- **When** 어느 축도 신뢰 매칭되지 않으면, the 매칭기 **shall** 무매칭·저신뢰·모호 각각에 대해 **구분된** 폴백 신호를 반환하고, 최저점 후보를 강제 반환하지 않는다.
- 검증: `test_scene_matching.py` 폴백 3종 독립 테스트.

### AC-SCENE-009 — 번들 형상 + 결합 순서 + Store 플래그 0건 (REQ-SCENE-010, REQ-SCENE-011)

- 구성된 번들 **shall**: 선두 `ChangeDestination Root` 정확 1회, `ClearAll` 캡처 전·Store 후, bare `Group <n>` 선택(`Select` 접두 0건), `Store Sequence <s> Cue <c> '<라벨>'` **정확 1회**, MAtricks 사용 시 Store 후 `Reset Selection MAtricks`, (트리거 지정 시) 트리거 PROPERTY 2줄이 `ClearAll` **뒤**, (익스큐터 명시 지정 시) `Assign` 1줄이 **최말미**.
- **결합 순서 (이 항목이 이 AC의 핵심)**: 구체 assert 6종 — ① 룩 값 라인이 **첫 `Step` 라인보다 앞**에 온다, ② `Step <k>` 라인이 **단독 라인**이고 그 수가 `len(steps) - 1`과 같다, ③ `Step 1` 라인은 **0건**, ④ 각 `Step <k>`가 그 스텝의 값 라인 **앞**에 온다, ⑤ 변형 라인(`At Phase` / `At Speed`)이 **스텝 열 전체보다 뒤**에 온다, ⑥ 룩 값 라인은 `;` 체인 **1줄**이고 스텝 값 라인에는 `;` 체이닝 **0건**.
- **Store 플래그 0건**: Store 라인의 라벨 종료 따옴표 뒤에 **어떤 토큰도 오지 않는다** — `/`로 시작하는 잔여 토큰 **0건**, 검사는 **대소문자 무관**이다. 이 검사가 특별히 중요한 이유는 콘솔이 **미지 플래그를 조용히 접수하기 때문**이다(`/CueOnlyy`가 `ok`+저장 — spec.md §C.1). **오타 플래그는 런타임에서 아무 신호도 내지 않으므로 이 assert가 유일한 그물이다.**
- 검증: `test_scene_compile.py` 문자열 수준 assert — 라이브러리 전 씬 × 형상.
- 뮤테이션: **Store 라인에 `/CueOnly`(또는 임의의 `/Foo`)를 붙이면 죽어야 한다.** **룩 값 라인을 fx 스텝 열 뒤로 옮기면 죽어야 한다**(결합 순서 역전 차단 — 이 뮤테이션이 §3.2의 기계적 고정이며, ASSUMPTION-44 `GO` 실측이 그 형상을 뒷받침한다). `Step 2`를 빼거나 변형 라인을 스텝 열 앞으로 옮겨도 죽어야 한다. 트리거 2줄을 `ClearAll` 앞으로 옮기면 죽어야 한다.

### AC-SCENE-010 — Store 안전: `/Overwrite` · `/Merge` 부재 (REQ-SCENE-013 (a)(b))

- the 컴파일 **shall** `/Overwrite` **0건**과 **`/Merge` 0건**을 유지한다. 두 검사 모두 **대소문자 무관**이다 — 런타임 매칭이 이미 대소문자 무관이므로 대소문자 고정 assert는 빌더가 `/overwrite`를 내도 **조용히 통과**하는 위양성 테스트다(`SPEC-COPILOT-BUSKWIZ-001/design.md:209`).
- 검증: `test_scene_compile.py` — 라이브러리 전 씬 번들 전수 스캔 + 대소문자 변형 4종(`/Merge`, `/merge`, `/MERGE`, `/mErGe`) 각각 주입 뮤테이션.
- **`/Merge`가 금지인 이유(비직관적이므로 명시)**: `/Merge`는 파괴적이지 않다. 금지 이유는 **새 큐 번호에서 동작이 무플래그와 동일한데**(SPEC-COPILOT-SONGCUE-001/progress.md:337-344 실측) **기존 번호의 `Not allowed` 안전망만 꺼지기 때문**이다 — 실익 0에 방어선만 잃는 거래다.

### AC-SCENE-011 — 값 라인 충돌 가드 2중 (REQ-SCENE-015)

- **(a) 번들 내 (구성 시점)**: 비면제 라인 중복이 주입된 형상에서 the 구성기 **shall** 번들 생성을 **거부(raise)** 하고 `VALUE_LINE_COLLISION` 동형 사유를 반환한다 — 건너뛰기가 아니다(design.md §4.1). 정상 씬 전수의 번들은 **비면제 라인 전수 유일**함을 함께 assert한다(비공허성).
- **(b) 지시 턴 경계 (실행 결과 시점)**: 실행 outcome에 비면제 라인 `skipped_already_executed`가 포함된 형상에서 the 툴 **shall** 해당 컴파일을 성공으로 보고하지 않고 교차 호출 충돌을 명시 실패로 보고한다.
- 검증: `test_scene_compile.py` — 면제 3종(`Clear`/`ClearAll`/bare 선택)의 중복은 통과함을 대조군으로 확인(면제 판정은 `is_programmer_state` 호출 결과여야 하며, **씬 자체 정규식 사본이 존재하지 않음**을 함께 단언한다 — 결정 E). 교차 호출은 fake outcome 주입 + 뮤테이션으로 확인하며 **"같은 씬 × 두 그룹"과 "다른 씬 × 두 그룹" 양쪽**을 세운다(`Step 2`가 씬 간 공통 문자열이므로).
- **가드 (a)의 비공허성이 특히 중요하다**: 효과가 기계로 확인되지 않으므로 이 가드를 통과한 결함은 **라이브에서 사람이 볼 때까지 아무 신호도 내지 않는다.** 가드 검사를 지운 뮤테이션이 반드시 죽어야 한다.

### AC-SCENE-012 — 금지 형태 `At Step N` 부재 (REQ-SCENE-011)

- 라이브러리 자산과 **발화되는 모든 번들**에서 `Attribute '<attr>' At Step <k>` 형태 **shall** 0건이다. 스텝 전환은 단독 `Step <k>` 라인으로만 나타난다. 검사는 대소문자 무관이다.
- 검증: `test_scene_compile.py`(번들 산출물 전수) + `test_scene_library.py`(자산 전수). 뮤테이션: 빌더가 `Attribute 'Dimmer' At Step 2`를 내도록 1줄 주입하면 죽어야 한다.
- **왜 별도 AC인가**: 이 형태는 콘솔이 `ok:true`로 접수하고 효과는 기계로 확인되지 않는다 — **런타임의 어떤 신호도 이 결함을 드러내지 않는다.** FXLIB M0 프로브 자신이 이 형태로 페이저 생성에 3회 실패했다. 형태 금지의 전수 검사가 유일한 방어선이므로 형상 AC(AC-SCENE-009)에 섞지 않고 독립시킨다.

### AC-SCENE-013 — 번호 획득 안전 (REQ-SCENE-013 (c)(d))

- the 컴파일 **shall** 시퀀스·큐 번호를 발명하지 않는다: ① 시퀀스는 `select_sequence_number`(fx 판, `requested=` 지원) 소비 — **씬 자체 구현 0건**, ② 큐 번호는 재조회 실측 빈 **정수** 번호만, ③ `truncated=참`이면 자동 배정 **거부** + 명시 보고, ④ 사용자 지정 점유 번호 **거부**(콘솔의 `Not allowed`에 앞서), ⑤ 재조회 섹션 자체가 오지 않으면(`path_not_resolved`/`console_unreachable`) 거부 + 신호 전파.
- 검증: `test_scene_compile.py` — fake 재조회(점유/빈/truncated/미도달 각 시나리오).
- 뮤테이션: `truncated` 검사를 지우면 죽어야 한다. 점유 큐 번호를 통과시켜도 죽어야 한다. 씬이 `select_sequence_number` 자체 구현을 갖게 만들면 ①의 단언이 죽어야 한다.

### AC-SCENE-014 — 트리거 형태 + 익스큐터 비자동 (REQ-SCENE-016, REQ-SCENE-017)

- **When** 트리거가 지정되면 the 컴파일러 **shall** PROPERTY 형태 2줄만 발화한다: `Set Cue <c> Sequence <s> Property 'TrigType' '<Token>'` + `Set Cue <c> Sequence <s> Property 'TrigTime' <절대초>`. 토큰은 **Capitalized 폐쇄 집합**이고, `TrigTime`은 **시퀀스 시작 기준 절대 초**다.
- the 컴파일 **shall** `Assign Cue … /trig=` 형태를 **0건** 유지하고(onPC 2.4.2에서 `"Illegal object"`), 익스큐터를 자동 배치하지 않는다 — 미지정 호출의 번들에 `Assign` **0건**, 명시 지정 시에만 말미 1줄.
- 검증: `test_scene_compile.py` — 트리거 지정/미지정, 토큰 대소문자 변형, `/trig=` 부재, 익스큐터 지정/미지정.
- 뮤테이션: 소문자 토큰(`'follow'`)을 통과시키면 죽어야 한다. `/trig=`를 내면 죽어야 한다. 미지정 익스큐터에 `Assign`을 붙이면 죽어야 한다.

### AC-SCENE-015 — 리포트 주장 분리 (REQ-SCENE-014) 【이 SPEC의 중심 AC】

- 리포트 **shall** 아래 **네 주장을 분리해** 싣고, 뭉뚱그려 "확인했다"고 적지 않는다:
  - **(a) 기계 확인됨 — 산출물** — 시퀀스·큐의 **존재**, 이름, 실제 `cueNo`(재조회 실측).
  - **(a′) 기계 확인됨 — 균일성** — 값 라인이 균일 속성 집합을 이 순서로 담았다(정적 검사).
  - **(b) 효과 — 기계 확인 불가** — 이펙트의 모션·룩의 발색은 **무대/GUI에서 사람이 확인해야 한다**. 이 문면은 **무조건**이다: 성공 경로를 포함한 **모든** 리포트가 담는다.
  - **(c) 트래킹 무해화 — 기계 확인 불가, 관측 채널 부재** — **균일 집합을 발화했다는 것**(a′)과 **그래서 트래킹이 무해해졌다는 것**은 다른 주장이다. **(a′)를 (c)의 증거로 제시하면 이 AC는 실패한다.**
- **(a′)와 (c)는 같은 문단에 오지 않는다** — 붙여 쓰면 독자가 전자를 후자의 증거로 읽는다. 이것이 `/CueOnly` 때의 실패 모드였고, **정책이 바뀌어도 인지 함정은 그대로다**(design.md §6.2).
- **검증은 상수 동일성으로 한다**: 각 문면은 모듈 상수이고 테스트는 `payload[...] == CONSTANT`로 확인한다 — **산문 부분 일치 비교 금지**(선례 `server/tests/test_songcue_report.py:119`; 동형 상수 선례 `server/fx/report.py:52` `EFFECT_EVIDENCE_NOTICE`, `server/looks/songcue_report.py:15` `PROPERTY_UNOBSERVED_NOTE`).
- 뮤테이션: ① 성공 경로에서 (b) 문면을 빼면 죽어야 한다(무조건성의 비공허성). ② (c)를 (a′)에 합쳐 "확인했다"로 적으면 죽어야 한다. ③ **균일성 확인을 트래킹 무해화의 근거로 문면화하면 죽어야 한다.** ④ 큐 재조회 결과를 효과 확인으로 문면화하면 죽어야 한다.

### AC-SCENE-016 — 실행 결과 전파 + 충돌 열거 게재 (REQ-SCENE-014)

- 리포트 **shall** 요약/상세 2단이며, 생성 산출물(시퀀스·큐·라벨·그룹·룩·이펙트), **덮인 attribute 열거**(AC-SCENE-005), **미주장 속성 열거**(AC-SCENE-024가 정확성을 소유하고 본 AC는 **게재 여부**만 본다 — 두 열거가 서로 다른 것임을 문면이 구분해야 한다), `not_executed` **및 비면제 라인 `skipped_already_executed`** 를 전파한다. 후자 발생 시 **성공 문면을 금지**하고 **불완전 시퀀스·큐가 이미 생성됐을 수 있음**을 명시한다.
- 검증: `test_scene_report.py` — 실패 주입 시 부분 성공 위장 없음. 비면제 `skipped_already_executed` 주입 시 성공 문면이 나오면 죽는 뮤테이션 포함.

### AC-SCENE-017 — 단일 실행 경로 + 경계 + PRESERVE (REQ-SCENE-019)

- `server/scene/**` **shall** transport·게이트 표면 import 0건: ① `test_architecture.py` 전역 스캔 그린(자동 포섭), ② 실행 위치 식별자 **AST 스캔** offender 0건 — 금지 식별자 `SafetyGate` / `screen` / `execution_port` / `CommandExecutionPort` / `ExecutionPort` / `ConsoleLink`, 금지 모듈 접두 `server.safety.gate` / `server.safety.console` / `server.orchestrator.ports` / `server.bridge`(raw grep 금지 — 독스트링 위양성 선례; 방식은 `test_looks_boundary.py:85` / `test_fx_boundary.py:132`), ③ `_NAMED_TOOL_EXEMPTIONS`가 정확히 `{server/tools/osc_smoke.py, server/tools/responder_roundtrip.py}`로 유지(`test_fx_boundary.py:228-230` 계승 — **`server/scene/` 추가 금지**).
- **PRESERVE diff 0**: `git diff --stat <BASE>..HEAD -- server/looks server/fx console/lua server/rulebook/assets server/safety` 가 **빈 출력**이다. 룰북은 byte-diff 0이며 **씬 어휘를 학습하지 않는다**(`test_fx_boundary.py:595` 계승).
- 검증: `test_scene_boundary.py` — bridge import 1줄 주입 뮤테이션으로 비공허성 확인 + 스캔이 실제로 씬 모듈 전체에 도달했는지 비공허성 단언(`test_fx_boundary.py:135-140` 형상).

### AC-SCENE-018 — 툴 계약 + 발명 금지 (REQ-SCENE-018)

- the `find_scene` · `compile_scene` 툴 **shall** 스키마 설명과 함께 툴 레지스트리에 등록되고, `compile_scene`은 rig context **미등재 그룹을 거부**하며, `Fixture <slot>` 타깃을 **0건**으로 유지하고, 실행을 **`run_commands` 경로 소비로만** 수행한다(fake runner로 호출 경로 assert — 제2 실행 표면 0건). 룰북 자산은 무변경이며 발견성은 툴 스키마 설명 문면만이 전담한다. 매칭·툴 표면은 제공자 중립(anthropic/gemini)이다.
- 검증: `test_scene_tool.py` — 미등재 그룹 주입 뮤테이션, `Fixture <slot>` 주입 뮤테이션, execution_port 직접 호출 주입 뮤테이션.

### AC-SCENE-019 — M0 라이브 프로브 기록 (LIVE — 2건 중 1번째 · **실행 완료 2026-08-01**) (REQ-SCENE-021)

- 실물 onPC에서 **ASSUMPTION-41/42/43/44/45** 판정 **shall** 각각 명시적 섹션 + 접두 행(`GO:` / `DESCOPE:` / `SKIP:` / `REOPEN:`)으로 `progress.md §E.2`에 기록된다. 판정 어휘는 **GO / NEGATIVE / CONDITION_NOT_MET / INCONCLUSIVE / REOPEN_SCOPE** 폐쇄 집합이다.
- **필수 절차 4종**: ① 각 축의 `ok` 채택 전 **날조 대조군 1발** 선행 — 오타 플래그가 not-ok임을 확립하고, **그것도 `ok`라면 `ok`의 증거력 상실을 판정으로 기록**한다, ② 접수 판정은 `ok`만으로 성립하지 않는다 — 재조회로 큐가 기대 이름·`cueNo`로 실존함을 확인해야 하며, **재조회마저 비변별이면 그 사실 자체가 판정**이다, ③ 트래킹 축은 **A/B 대조군 없이 판정하지 않는다** — 단독 관측은 판정 불능이며 그 경우 `INCONCLUSIVE`로 적는다, ④ **접수와 효과를 한 판정으로 합치지 않는다**.
- **부정 분기**: 사용자 확정 정책의 전제가 `NEGATIVE` 또는 `CONDITION_NOT_MET`이면 **run-phase 중단 + 블로커 보고**다. 에이전트가 대체 정책을 골라 조용히 진행하면 이 AC는 **실패**한다 — 대체 결정은 사용자 몫이다(REQ-SCENE-021 (b)).
- **실행 결과 (정본 `progress.md §E.2` — 여기에 증거 원문을 복제하지 않는다)**: ASSUMPTION-41 `CONDITION_NOT_MET`(기계 채널 소진 — 날조 플래그가 `ok`+저장) · 42 `INCONCLUSIVE`(A=B) · **43 `GO`**(판정 대상을 v1 범위 = 정수·신규·오름으로 좁혀서다 — 신규 정수 큐 성립 / 역순 저장 거부 / `truncated: True` 실측) · 44 `GO`(파란색 유지 + 딤머 웨이브) · 45 `GO`(딤머 펄스 — 이펙트 승). 다섯 판정 전부 **폐쇄 어휘 안의 값**이다. **부정 분기(41)가 실제로 발동해 run-phase가 중단·보고됐고, 그 결과가 D1 개정이다** — 이 AC의 부정 분기 요건은 그 경로로 충족됐다(단 AC 전체의 완결은 아래 정리 기록에 걸려 있다).
- **정리 기록 (이행 완료 — 2026-08-01, M8 세션)**: 사용자가 GUI에서 시퀀스 **191·192·193·194·195·196·197**을 삭제했고(`Delete`는 블랙리스트이므로 툴 경로 불가), 게이트 경유 재조회로 **잔여 0건**을 확인했다 — `DataPool/Sequences` childCount **24 → 17**, `truncated` **True → False**, 191~197 전건 부재. **이 항목이 닫히면서 AC-SCENE-019가 완결됐다.** 정본 기록은 `progress.md §E.2` M8 절 ③이며 접두 행은 `GO: AC-SCENE-019`다.
- M0는 게이트 미경유이므로 감사 로그를 증거로 요구하지 않는다(그건 M8 몫).
- 검증(레시피): plan.md §B M0 기록 + `progress.md §E.2` 대조. 기계 확인: `grep -E '^(GO|DESCOPE|SKIP|REOPEN):' progress.md` 및 ASSUMPTION-41~45 각각의 판정 어휘 존재. **접두 행은 반드시 행두(column 0)에서 시작해야 한다** — 헤딩·볼드·코드 스팬 안에 있으면 `^` 앵커가 잡지 못하고, **정규식을 완화해 헤딩을 잡게 만드는 것은 금지**다(앵커가 이 검사를 기계 판정으로 만드는 유일한 요소다).
- **실측(2026-08-01, v0.2.1)**: 위 grep을 그대로 실행한 결과 **6행**(`SKIP:` 41 · `DESCOPE:` 42 · `GO:` 43 · `GO:` 44 · `GO:` 45 · `REOPEN:` D1), exit 0. 직전 v0.2.0에서는 **0행 · exit 1**이었다 — 판정 어휘가 H4 헤딩과 볼드 코드 스팬 안에만 있었기 때문이며, `progress.md §E.2` 말미의 "판정 접두 행" 블록이 그것을 닫았다. **v0.2.3(M8) 이후 같은 grep은 8행**이다 — M8이 `GO: AC-SCENE-019`와 `GO: AC-SCENE-021` 두 행을 더했다. M0분 6행은 **무변경**이다.

### AC-SCENE-020 — LiveLock 제안 강등 (REQ-SCENE-020)

- **While** LiveLock이 활성인 동안 컴파일 **shall** 콘솔 송신 0건 + 제안 전용이다: **Store 라인을 포함해** 전 커맨드가 `status == "proposal"`이고, `is_error is False`(강등은 실패가 아니라 답이다), `succeeded is False`다.
- 검증: `test_scene_boundary.py` — `test_fx_boundary.py:459` 패턴 계승. **강등이 "상속되므로 공짜"라는 추론에 의존하지 않고 실제로 잠긴 씬 번들을 통과시켜 본다** — fx가 M5에서 같은 추론을 했고 M6에서야 실제로 쏴 봤다는 기록이 그 근거다.
- 뮤테이션: Store만 송신되게 바꾸면 죽어야 한다.

### AC-SCENE-021 — 종단 라이브 인수 (LIVE — 2건 중 2번째, M8) (REQ-SCENE-021)

- 실물 onPC에서 채팅 지시 → `find_scene` 매칭 → `compile_scene` → **게이트 감사 로그 대조** → 생성 시퀀스·큐 **재조회 확인** → **효과의 GUI 사람 관측** → **리포트 주장 분리 문면 + 미주장 열거가 실물과 일치하는지 확인**이 종단 1회 **shall** 성립한다.
- **대조 순서**: M0 프로브 C와 같은 씬을 **먼저** 발화해 파이프라인 생존을 확립한 뒤 라이브러리 씬을 발화한다 — 그래야 부정 관측이 "파이프라인 결함"이 아니라 "저작 결함"으로 귀속된다.
- M0 판정(41/44)의 **재측정·덮어쓰기는 금지**된다. 어긋남이 관측되면 그 불일치 자체를 기록한다. M0 프로브 D가 `INCONCLUSIVE`였던 경우에만 트래킹 A/B를 게이트 경유로 1회 반복한다.
- **큐 재조회 확인을 효과 확인으로 기록하면 이 AC는 실패**한다(§C.1 검증 천장).
- 검증(레시피): plan.md §B M8. 리포트 문면과 실물 관측의 불일치는 그 자체로 기록 대상.
- **실행 결과 (정본 `progress.md §E.2` M8 절 — 여기에 증거 원문을 복제하지 않는다)**: **`GO`.** 게이트 경유 `compile_scene` 2회가 각 11/11 `executed_ok`로 시퀀스 3·4를 만들었고, **감사 로그가 전 커맨드를 기록**했으며(M0가 갖지 못한 채널 — 날조 대조군 `ZzzNotACommand 999`가 `ok:false`로 갈려 이 채널의 변별력이 먼저 확립됐다), 재조회가 두 큐를 기대한 이름·`cueNo 1`로 돌려줬다. 효과는 **에이전트의 computer-use 화면 캡처 다중 표본**으로 관측했다(사용자 지시) — 씬마다 **fx가 구동하는 축만** 프레임마다 변하고 룩의 정지 값은 고정이었다(1회차 Dimmer 변동·RGB 프레임차 0.00 / 2회차 PanTilt 변동·Dimmer·RGB 프레임차 0.00). **관측 채널의 한계는 그대로 기록됐다** — GUI 시트 판독이지 무대 실물이 아니고 표본은 이산이다. M0 판정(41/44/45)은 **재측정·덮어쓰기하지 않았다**. 부수 발견 1건(비차단): SPEC 표제 문장이 상류 어휘 부재로 매칭되지 않는다 — `progress.md §E.2` M8 절 ⑦.

### AC-SCENE-022 — 전체 회귀 (협상 불가)

- pytest 전체 + vitest 전체 **shall** 킥오프 기준선 대비 신규 실패 0건.
- 검증: M7에서 전량 실행 + 기준선 대조(수치는 착수 직전 실측분 — plan-phase 수치 이월 금지).
- 참고 기준선(오케스트레이터 세션 실측, 2026-08-01 `main`=`e4bc78e`): pytest **3432 passed / 5 skipped**, vitest **223**. **이 수치는 참고이며 대조 기준은 각 마일스톤 착수 직전 직접 실측분이다.**

### AC-SCENE-023 — 룩 값 라인 균일 속성 집합 (REQ-SCENE-012) 【개정 신설】

- **룩을 담은 씬의 값 라인 shall** 균일 집합 `("Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B")` 를 **전부, 이 순서로** 포함한다. 순회 대상은 **룩 라이브러리 32개 룩 전수**다.
- **단언은 자산이 아니라 출력을 잡는다** — 라이브러리 YAML의 키 집합 검사로는 부족하다(정렬·상류 `_values_line`·씬 조립 어느 단계에서 깨져도 자산 검사는 통과한다). 산출된 값 라인 문자열에서 속성명을 추출해 판정한다:
  ```python
  names = re.findall(r"Attribute '([^']+)' At", values_line)
  assert tuple(n for n in names if n in set(SCENE_UNIFORM_ATTRIBUTES)) == SCENE_UNIFORM_ATTRIBUTES
  assert set(names) - set(SCENE_UNIFORM_ATTRIBUTES) <= {"Zoom", "Iris"}
  ```
- **첫 단언이 `tuple(names) == SCENE_UNIFORM_ATTRIBUTES`가 아닌 이유**(위양성 방지): `Zoom`/`Iris`를 가진 룩이 **17/32**이므로 완전 일치 단언은 그 룩들을 전부 실패시킨다 — **균일 집합은 부분 순서 보증이지 전체 일치 보증이 아니다.** 둘째 단언이 "그 밖은 무엇이든 와도 된다"를 막는다.
- **상수 동치 단언**: `SCENE_UNIFORM_ATTRIBUTES == server.looks.schema.CONFIRMED_ATTRIBUTES` 를 경계 테스트가 단언한다 — 씬이 자기 상수를 갖는 대가로 지는 의무이며(결정 E 규칙), 상류 밴드 1이 바뀌면 **먼저 시끄럽게 죽는다**(design.md §6.1).
- **적용 범위 대조군(비공허성)**: **이펙트 단독 씬은 이 AC의 대상이 아님**을 함께 단언한다 — 룩 값 라인 자체가 없는 것이 적법 형태이며(REQ-SCENE-012 (a)), 그 씬을 실패시키면 위양성이다.
- **채움 금지 대조군**: `Zoom`을 선언하지 않은 룩의 산출 값 라인에 `Attribute 'Zoom'` 이 **0건**임을 단언한다 — 컴파일러가 값을 발명해 채우지 않음의 기계 확인(spec.md §D).
- 검증: `test_scene_compile.py`(산출 전수) + `test_scene_boundary.py`(상수 동치).
- 뮤테이션: ① 균일 집합에서 한 속성을 빼면 죽어야 한다. ② 정렬을 제거하고 선언 순서를 그대로 쓰도록 바꾼 뒤, **선언 순서가 뒤집힌 룩 픽스처**를 주입하면 죽어야 한다(오늘 자산 32/32가 이미 정렬돼 있으므로 자산만으로는 이 뮤테이션이 살아남는다 — **픽스처 주입이 필수다**). ③ 미선언 `Zoom`을 상수로 채우게 만들면 채움 금지 대조군이 죽어야 한다. ④ 균일 집합 미충족 룩 픽스처에서 `raise` 대신 통과시키면 죽어야 한다.

### AC-SCENE-024 — 미주장 속성 전수 열거 (REQ-SCENE-014 (d)) 【개정 신설】

- 컴파일 결과 **shall** `KNOWN_ATTRIBUTES − (룩이 낸 속성 ∪ fx가 구동하는 속성)` 를 **전수 열거**해 리포트에 싣는다. 열거는 **결정론적으로 정렬**된다(집합 순회 순서 의존 금지).
- **정확성**: 알려진 씬에 대해 열거가 **정확히** 차집합과 일치한다 — 부분집합·상위집합 모두 실패. 최소 3케이스: ① 코어4 룩 + dimmer fx(기대 `{Zoom, Iris, Pan, Tilt}`), ② **`Zoom`만 보유하고 `Iris`는 없는** 룩 + movement fx(기대 `{Iris}`) — **`Zoom` 보유 룩 16개 중 7개는 `Iris`도 함께 갖고**(측정: Zoom 16 · Iris 8 · 양쪽 7), 그 7개를 쓰면 기대값이 `∅`가 되어 케이스가 무의미해진다. 재료는 **Zoom-only 9개**에서 고른다, ③ 이펙트 단독 씬(룩 없음 — 열거가 거의 전량).
- **유니버스 형상 고정**: `server.looks.schema.KNOWN_ATTRIBUTES`가 **오늘 정확히 8원소**(`Dimmer` · `ColorRGB_R/G/B` · `Zoom` · `Iris` · `Pan` · `Tilt`)임을 단언한다. 씬은 이 상수를 **읽기 import로 소비하며 사본을 만들지 않는다**(결정 E 동형) — 상류가 어휘를 넓히면 이 단언이 먼저 죽어 열거의 조용한 확장을 막는다.
- **문면 한계**: 리포트는 "이 축은 앞 씬의 값이 **이월될 수 있다**"까지만 적는다. **"이월됐다"고 적으면 이 AC는 실패한다** — 실제 이월은 관측 불가이며, 이는 AC-SCENE-015 (c)와 같은 규율이다.
- **Pan/Tilt 비공허성**: movement fx를 쓰지 않는 씬에서 `Pan`·`Tilt`가 **반드시 열거에 나타난다** — 이것이 spec.md §D의 "Pan/Tilt 이월을 은폐하지 않는다"를 기계로 고정하는 지점이다.
- 검증: `test_scene_report.py`(문면·정렬) + `test_scene_compile.py`(차집합 계산).
- 뮤테이션: ① 열거를 빈 튜플로 고정하면 죽어야 한다. ② 유니버스에서 `Pan`/`Tilt`를 빼면 **movement 미사용 씬 케이스가** 죽어야 한다. ③ 문면을 "이월됩니다"로 바꾸면 죽어야 한다. ④ 정렬을 제거해 집합 순회 순서에 맡기면 결정론 단언이 죽어야 한다.

## §D. Edge Cases

- **룩 단독 씬** — fx 라인 0건, `Step` 라인 0건, 룩 값 라인 + Store만. **균일 집합은 여전히 강제**되고, 미주장 열거는 `{Zoom?, Iris?, Pan, Tilt}`가 된다.
- **이펙트 단독 씬** — 룩 값 라인 0건, 스텝 1이 비어 있는 상태에서 fx 스텝 열이 시작된다. FXLIB의 기존 형상과 동일하므로 회귀 위험이 가장 낮은 경로다. **균일 집합 AC(AC-SCENE-023)의 대상이 아니며**(룩 값 라인이 없다), 이 씬의 미주장 축은 전적으로 AC-SCENE-024의 열거가 전담한다 — 열거가 거의 전량이 되는 것이 **정상이자 의도**다.
- **movement fx 씬** — 룩 ∩ fx 교집합이 **항상 ∅**이므로 충돌 열거가 비고(룩은 Pan/Tilt를 가질 수 없다), 미주장 열거에서 `Pan`·`Tilt`가 **빠진다**(fx가 구동하므로). 이 두 특성이 동시에 성립하는지가 AC-SCENE-005 위양성 대조군 + AC-SCENE-024 케이스 ②의 재료다.
- **룩과 이펙트가 attribute를 전혀 공유하지 않음** — 덮인 attribute 열거가 **빈 집합**(위양성 없음).
- **룩과 이펙트가 같은 attribute에 같은 값** — 값 라인이 문자열로 중복될 수 있다 → 1차 가드가 **거부(raise)**. 조용한 통과 금지.
- 그룹은 실존하나 이름이 한글/공백 포함 — rig context 등재 **번호로 변환해 bare `Group <n>` 번호형으로 발화**(인용명형은 `[문서]` 등급 문법 유도이므로 v1 미발화).
- 재조회 sequences/cues 섹션 자체가 오지 않음 — 자동 배정 거부 + 신호 전파.
- 시퀀스·큐 풀 점유 24개 초과(`truncated`) — 자동 배정 거부 경로.
- **사용자가 큐 번호를 지정했고 그것이 비어 있음** — 재조회 확인 후 그대로 사용.
- **사용자가 큐 번호를 지정했고 그것이 점유됨** — 툴이 거부(콘솔 `Not allowed`에 앞서).
- MAtricks 선언 없는 이펙트 — `Set Selection`/`Reset` 라인 0건(불필요 라인 금지).
- 트리거 미지정 — `Set Cue …` 라인 0건.
- **`trig_time = 0`** — 적법(범위 검사는 `< 0`만 거부). `Set Cue … Property 'TrigTime' 0` 발화.
- 매칭 입력이 빈 문자열/공백 — 폴백 신호(예외 아님).
- **같은 지시 턴의 2회차 컴파일** — `Step 2`(또는 공통 값 라인)부터 접히므로 outcome 검출이 명시 실패로 보고. **1회차 성공 + 2회차 무음 성공은 금지된 결과다.**
- **LiveLock 중 Store** — 제안 카드에 Store 라인이 **문면 그대로 보이는 채로** 강등된다(사용자가 무엇이 발화될 뻔했는지 볼 수 있어야 한다).
- **균일 집합을 채우지 못하는 룩** — 오늘 라이브러리에는 **0건**이나(32/32 충족), 미래 저작·외부 자산에 대한 방어로 `UNIFORM_ATTRIBUTES_INCOMPLETE` raise. 픽스처 주입으로만 도달 가능한 경로다.

## §E. Quality Gate 기준

- 신규 `server/scene/**` 커버리지 ≥ 85%(프로젝트 기준 — `.moai/config/sections/quality.yaml` `test_coverage_target: 85`), **`server/scene/**` + `server/tests/test_scene_*.py` 범위** ruff 클린, 신규 실패 0. **범위를 밝히는 이유**: 저장소 전역 `ruff check server/`는 이 SPEC 착수 전부터 기존 3건을 내고 `ruff format --check server/`는 20파일을 지목한다 — 무범위로 "ruff 클린"이라 적으면 저장소 전역 클린으로 읽힌다(sync-phase 감사 지적). 씬이 만든 파일은 실측 `All checks passed` · `13 files already formatted`.
- 경계: AC-SCENE-017의 3중 검증(전역 스캔·AST·예외 명단) + PRESERVE diff 0 전부 그린.
- 문서: progress.md M0/M8 기록이 **행두 접두 행 grep으로 기계 확인 가능** — M0분은 v0.2.1에서 **실측 6행**으로 확인됐고(AC-SCENE-019 실측 줄), M8분 2행이 v0.2.3에서 같은 형태로 **추가됐다 — 현재 8행**.
- 뮤테이션: 각 가드형 AC(**AC-SCENE-005, AC-SCENE-009, AC-SCENE-010, AC-SCENE-011, AC-SCENE-012, AC-SCENE-013, AC-SCENE-014, AC-SCENE-015, AC-SCENE-017, AC-SCENE-020, AC-SCENE-023, AC-SCENE-024**)에서 위반 주입이 실제로 죽는지 확인 — **survived = 마일스톤 미완료**.
- **뮤테이션 재료 규율 2건 (개정 신설 — 승계 필수)**: ① **AC-SCENE-005의 충돌 열거 비공허성은 dimmer/color fx 조합으로만 세운다** — movement fx는 룩과 교집합이 항상 ∅이라 정답도 빈 집합이고, 그 조합으로 뮤테이션을 세우면 **통과해 버린다**(design.md §3.3 각주). ② **AC-SCENE-023의 순서 뮤테이션은 픽스처 주입이 필수다** — 오늘 자산 32/32가 이미 정렬돼 있어 자산만으로는 정렬 제거 뮤테이션이 살아남는다.

## §F. Definition of Done

1. AC-SCENE-001~024 전부 PASS (부정 실측 분기 포함 — DESCOPE는 기록과 함께 PASS다. **단 사용자 확정 정책 전제의 부정은 PASS가 아니라 중단이다** — plan.md §A.3 예외 · REQ-SCENE-021 (b). **이 분기는 M0에서 실제로 발동했고 D1 개정으로 닫혔다.**).
2. clarification 마커 0건 유지, **ASSUMPTION-41~45 전부 판정 기록 존재** — 전량이 AC-SCENE-019의 커버리지 안에 있고 **판정은 전부 폐쇄 어휘 안의 값**이다(41 `CONDITION_NOT_MET` · 42 `INCONCLUSIVE` · 43 `GO`(v1 범위 = 정수·신규·오름) · 44 `GO` · 45 `GO`). **M0 프로브 잔여 시퀀스(191~197) 정리 기록이 닫혀 있어야 한다.**
3. PRESERVE 목록(plan.md §A.5) diff 0건 — `git diff --stat <BASE>..HEAD` 빈 출력으로 기계 확인.
4. 전체 회귀 그린(AC-SCENE-022) + 라이브 2건 기록 완결.
5. 리포트 문면에 **주장 분리**((a)/(a′)/(b)/(c))가 성공 경로를 포함한 모든 경로에서 실재하며, **상수 동일성 검사**로 확인됨(AC-SCENE-015). **(a′)와 (c)가 같은 문단에 있지 않음**을 함께 확인.
6. 전 씬 번들에서 **룩 값 라인이 첫 `Step` 라인보다 앞**, **모든 Store에 플래그 0건**(`/CueOnly` 포함), **`/Merge`·`/Overwrite`·`At Step N`·`/trig=` 각 0건**(AC-SCENE-009, AC-SCENE-010, AC-SCENE-012, AC-SCENE-014).
7. **면제 집합 사본 0건** — 씬은 `is_programmer_state`를 호출할 뿐 자기 정규식을 갖지 않는다(AC-SCENE-011 부수 단언).
8. **룩을 담은 전 씬의 값 라인이 균일 집합 4개를 이 순서로 담고**(AC-SCENE-023, 32개 룩 전수), **미주장 속성 열거가 정확히 차집합과 일치**한다(AC-SCENE-024). 미선언 `Zoom`/`Iris`에 대한 **채움 0건**이 함께 확인된다.
