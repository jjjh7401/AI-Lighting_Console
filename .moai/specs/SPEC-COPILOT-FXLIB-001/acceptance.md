# SPEC-COPILOT-FXLIB-001 — 인수 기준 (acceptance)

> 검증 철학 3줄: (1) **`Cmd` 접수 `ok`는 효과 증거가 아니다**(BUSKWIZ progress.md:275-283, :314) — 효과는 재조회 또는 명시된 관측 채널로만, 그리고 `ok`를 증거로 쓰기 전에 **날조 대조군**으로 그 축의 변별력을 먼저 확립한다(SONGCUE 선례). (2) 라이브 AC는 정확히 2건(AC-FXLIB-021 M0 · AC-FXLIB-022 M7)이며 나머지 21건은 콘솔 무접촉으로 판정 가능하다. (3) 부분 성공을 전체 성공으로 위장하지 않는다.
>
> **v0.2.0 M0 폴드인 — 이 문서를 읽는 사람이 먼저 알아야 할 것**: M0 실측으로 **이펙트 효과의 기계 증거 채널이 부정**임이 확정됐다(progress.md §E.2). 큐 내용도, 프로퍼티도, 픽스처 실시간 값도 읽히지 않으며 내용 있는 큐와 빈 큐가 구별되지 않는다. 따라서 **효과의 유일한 증거 채널은 사람의 GUI 관측**이고, 나머지 AC 전부는 "효과"가 아니라 **형상·계약·거부 동작**을 검증한다. 형상 결함이 런타임에서 아무 신호도 내지 않으므로 **테스트가 유일한 그물이다**(design.md §7).

## §A. 개요

AC는 23건이다. §C.0이 REQ(22건) ↔ AC 역추적을, §C.0a가 마일스톤 배정(합 23 · 중복 0 · 누락 0)을 고정한다.

## §B. Given-When-Then 시나리오

### 시나리오 1 — 추상 움직임 지시의 종단 적용 (행복 경로)

- **Given** 이름 있는 그룹이 존재하는 리그, LiveLock 비활성.
- **When** 사용자가 "무버들 좌우로 부드럽게 쓸어줘"라고 지시한다.
- **Then** `find_fx`가 `sweep` 계열 엔트리를 매칭하고, `instantiate_fx`가 rig context에 실존하는 그룹을 대상으로 검증 리터럴 번들을 구성해 `run_commands` 경로로 실행하며, 한국어 2단 리포트가 시퀀스·큐·라벨과 효과 증거 상태를 보고한다.

### 시나리오 2 — 매칭 실패의 정직한 폴백

- **When** 어떤 엔트리에도 신뢰 매칭이 없는 지시("우주적인 무언가")가 온다.
- **Then** `find_fx`는 폴백 신호를 반환하고 어떤 엔트리도 발명하지 않는다 — 모델은 룰북 무드표 폴백으로 강등하며 그 사실을 말한다.

### 시나리오 3 — 시퀀스 번호 충돌의 안전 방향

- **Given** 사용자가 지정한 시퀀스 번호가 이미 점유돼 있다(또는 재조회가 truncated=참).
- **When** `instantiate_fx`가 호출된다.
- **Then** 덮어쓰기도 재슬롯도 없다: 점유 번호는 무플래그 Store의 "Not allowed" 거부에 앞서 툴이 거부·보고하고, truncated에서는 자동 배정을 거부한다. `/Overwrite`는 어떤 경로로도 발화되지 않는다.

### 시나리오 4 — 값 라인 충돌의 생성 전 차단

- **Given** 구성된 번들에 비면제 커맨드 문자열이 중복으로 들어가는 형상(가정 주입) — **M0 이후 가장 현실적인 주입은 같은 attribute의 두 스텝에 같은 값을 적은 엔트리다**.
- **Then** 번들은 콘솔로 가지 않는다 — 로더가 1차로 거부하고(REQ-FXLIB-005 ③), 통과하더라도 구성기가 `VALUE_LINE_COLLISION` 동형 사유로 생성을 거부하고 명시 에러를 반환한다. 통과시켰다면 스텝 1개짜리 프로그래머로 Store가 실행돼 **모션 0이 무음으로** 발생했을 것이다.
- **그리고(교차 호출)** 같은 지시 턴의 앞선 호출이 이미 발화한 값 라인과 겹치는 경우 — 구성 시점에는 보이지 않으므로(dedupe는 instruction-scoped), 실행 outcome의 비면제 `skipped_already_executed` 검출이 성공 보고를 차단하고 명시 실패로 보고한다(AC-FXLIB-009 (b)). **`Step 2` 라인이 전 패턴 공통이므로 이 경로는 서로 다른 패턴 사이에서도 성립한다** — v1은 지시 턴당 인스턴스화 1회가 운용 경계다(design.md §5).

### 시나리오 5 — LiveLock 중 제안 강등

- **Given** LiveLock 활성.
- **When** `instantiate_fx`가 호출된다.
- **Then** 콘솔 송신 0건 — 제안 카드 전용으로 강등된다(기존 기제 소비).

## §C. AC (GEARS 형식 — 검증 레시피는 각 AC 하위 상세)

### §C.0 REQ ↔ AC 역추적표

| REQ | AC | | REQ | AC |
|---|---|---|---|---|
| REQ-FXLIB-001 | AC-001, AC-003 | | REQ-FXLIB-012 | AC-010 |
| REQ-FXLIB-002 | AC-002 | | REQ-FXLIB-013 | AC-011 |
| REQ-FXLIB-003 | AC-003 | | REQ-FXLIB-014 | AC-012 |
| REQ-FXLIB-004 | AC-004 | | REQ-FXLIB-015 | AC-013 |
| REQ-FXLIB-005 | AC-001 | | REQ-FXLIB-016 | AC-014 |
| REQ-FXLIB-006 | AC-005 | | REQ-FXLIB-017 | AC-015 |
| REQ-FXLIB-007 | AC-006 | | REQ-FXLIB-018 | AC-016 |
| REQ-FXLIB-008 | AC-007 | | REQ-FXLIB-019 | AC-017 |
| REQ-FXLIB-009 | AC-008 | | REQ-FXLIB-020 | AC-018 |
| REQ-FXLIB-010 | AC-008 | | REQ-FXLIB-021 | AC-019 |
| REQ-FXLIB-011 | AC-009 | | REQ-FXLIB-022 | AC-023 |
| | | | (횡단) | AC-020, AC-021, AC-022 |

(AC 번호는 본 문서 내 AC-FXLIB-0NN의 축약 표기다 — 정본 토큰은 완전형.)

### §C.0a 마일스톤 배정표 (합 23 · 중복 0 · 누락 0)

| 마일스톤 | AC | 수 |
|---|---|---|
| M0 | AC-FXLIB-021 | 1 |
| M1 | AC-FXLIB-001 | 1 |
| M2 | AC-FXLIB-002, 003, 004 | 3 |
| M3 | AC-FXLIB-005, 006, 007 | 3 |
| M4 | AC-FXLIB-008, 009, 010, 011, 012, 023 | 6 |
| M5 | AC-FXLIB-013, 014, 019 | 3 |
| M6 | AC-FXLIB-015, 016, 017, 018, 020 | 5 |
| M7 | AC-FXLIB-022 | 1 |

### §C.1 AC 상세

### AC-FXLIB-001 — 스키마 로딩 + 명시 에러 (REQ-001, 005)

- **When** 정상 라이브러리를 로드하면 the 로더 **shall** 전 엔트리를 스키마 형상으로 반환하고, 위반 주입 각각에 대해 **개별 명시 에러**를 낸다. 위반 종별: 미지 필드/패턴/attribute, 범위 이탈, 중복 fx id, 게이트 미충족 `accel`/`decel` 사용, **그리고 스텝 축 4종**(REQ-FXLIB-005) — ① `len(steps) < 2`, ② 스텝 간 attribute 집합 불일치, ③ 같은 attribute의 두 스텝이 **같은 값**, ④ `steps` 없이 변형 축만 선언.
- 검증: `test_fx_schema.py` — 위반 종별마다 독립 테스트(병합 금지). `accel`/`decel` 필드는 **정의 존재 + 직렬화 왕복**을 별도 assert(DESCOPE 형상 유지 확인 — v1 미사용).
- 뮤테이션: `len(steps) >= 2` 검사를 지우면 이 AC가 죽어야 한다. 스텝 값 동일성 검사(③)를 지워도 죽어야 한다 — **이 둘이 무음 실패의 유일한 자동 검출 지점이다**(효과는 기계로 확인되지 않는다).

### AC-FXLIB-002 — 라이브러리 커버리지 + 패턴 폐쇄 (REQ-002)

- 내장 라이브러리 **shall** 무조건 4종(`sweep`/`wave`/`circle`/`diagonal`) 각각에 ≥1 엔트리를 갖고, 전 엔트리의 패턴 종별이 폐쇄 집합 소속이며, 게이트 2종(`pulse`/`chase`)은 ASSUMPTION-37 GO 기록이 있을 때만 존재한다(**M0에서 GO 확정 — 6종 평가가 유효 분기다**). 전 엔트리는 한국어 무드 키워드 ≥1을 갖고, **전 엔트리가 `len(steps) >= 2`를 만족한다**(REQ-FXLIB-001 — 스텝 축 없는 엔트리는 페이저를 만들지 못한다).
- 검증: `test_fx_library.py` 전수 스캔. `accel`/`decel`에 값이 실린 엔트리 **0건**(M0 SKIP — v1 미사용)을 함께 assert.

### AC-FXLIB-003 — 어휘 3구간 한정 + 다단 게이트 (REQ-003, REQ-001 게이트)

- 라이브러리와 번들 산출물 **shall** REQ-FXLIB-003의 3구간 어휘만 사용한다: ① `At Absolute` 0건, **그리고 스텝 문맥 밖의 단독 `At <n>` 0건**(스텝 문맥 = 번들이 `Step <k>` 라인을 담고 해당 attribute의 값 라인이 2개 이상 — M0 귀결로 "정적 값"과 "스텝 값"은 형태가 같고 **문맥이 구분자**다), ② 프로브 대기 어휘(`At Accel`/`At Decel`) 0건 — M0 SKIP이므로 실측 없이 진입 금지, ③ 스트로브/셔터 0건, ④ `At Relative` 0건(v1 미발화 — ASSUMPTION-40).
- 검증: `test_fx_library.py` — 금지 문법 주입 시 로더가 거부함을 뮤테이션으로 확인. 스텝 문맥 판정은 **번들 전체를 보고** 내린다(라인 단독 판정 금지 — 위양성으로 스텝 값을 거부하면 전 패턴이 죽는다).

### AC-FXLIB-004 — per-show 값 부재 (REQ-004)

- 라이브러리 자산 전수에서 그룹 번호/이름·시퀀스 번호·큐 번호·FID·익스큐터 번호 필드 **shall** 0건 — 스키마에 그런 필드 자체가 없고 로더가 미지 필드를 거부한다.
- 검증: `test_fx_library.py` + 스키마 필드 집합 assert.

### AC-FXLIB-005 — 자연어 매칭 규율 (REQ-006)

- 매칭기 **shall** 한국어 조사가 붙은 지시("웨이브로", "서클을")를 처리하고, 동점에서 None을 반환하며, 같은 입력에 같은 출력을 낸다(결정론).
- 검증: `test_fx_matching.py` — 조사 변형·동점·결정론 각각 독립 테스트.

### AC-FXLIB-006 — 단일 진실원 + 발명 금지 (REQ-007)

- `find_fx` 반환 엔트리 **shall** 전부 라이브러리 실존 id다 — 존재하지 않는 id·합성 엔트리 0건.
- 검증: `test_fx_matching.py` + `test_fx_tool.py` 반환값 대조.

### AC-FXLIB-007 — 폴백 신호 (REQ-008)

- 무매칭·저신뢰·모호 각각에서 **shall** 구분된 폴백 신호를 반환하고 최저점 후보를 강제 반환하지 않는다.
- 검증: `test_fx_matching.py` 폴백 3종 독립 테스트.

### AC-FXLIB-008 — 번들 형상 + 프로그래밍 규율 (REQ-009, 010)

- 구성된 번들 **shall**: 선두 `ChangeDestination Root` 정확 1회, `ClearAll` 캡처 전·Store 후, bare `Group` 선택(`Select` 접두 0건), 검증 리터럴만, `Store Sequence <n> Cue 1 '<라벨>'` 정확 1회, MAtricks 사용 시 Store 후 `Reset Selection MAtricks`.
- **스텝 쌍 (M0 귀결 — 이 항목이 빠지면 번들은 페이저를 만들지 못한다)**: 전 패턴의 번들 **shall** `<값 라인>` → `Step 2` → `<값 라인>` 형태의 **스텝 열**을 담는다. 구체 assert 5종: ① `Step <k>` 라인이 **단독 라인**으로 존재하고 그 수가 `len(steps) - 1`과 같다, ② `Step 1` 라인은 **0건**(첫 스텝은 현재 스텝이다), ③ 각 `Step <k>` 라인이 그 스텝의 값 라인 **앞에** 온다, ④ 변형 라인(`At Phase …` / `At Speed …`)은 **스텝 열 전체보다 뒤에** 온다, ⑤ 스텝 값 라인에 `;` 체이닝 **0건**(Speed 라인의 체이닝은 허용 — design.md §4.3).
- 검증: `test_fx_instantiate.py` 문자열 수준 assert (무조건 4종 × 형상 + ASSUMPTION-37 GO 확정에 따른 pulse/chase 2종 = 6종). **M0 앵커 대조**: `pulse` 번들의 스텝 골격이 progress.md §E.2의 실측 형상과 문자열 수준에서 일치함을 별도 assert한다 — 실측된 유일한 형상이 회귀 기준선이다.
- 뮤테이션: `Step 2` 라인을 빼면 이 AC가 죽어야 한다. 변형 라인을 스텝 열 **앞으로** 옮겨도 죽어야 한다(v0.1.0 형상의 재도입 차단).

### AC-FXLIB-009 — 값 라인 충돌 가드 (REQ-011)

- (a) **번들 내**: 비면제 라인 중복이 주입된 형상에서 the 구성기 **shall** 번들 생성을 거부하고 `VALUE_LINE_COLLISION` 동형 사유를 반환한다. 정상 패턴 전수(무조건 4종 + ASSUMPTION-37 GO 확정에 따른 pulse/chase = 6종)의 번들은 **비면제 라인 전수 유일**함을 함께 assert한다(비공허성). **주입 형상은 스텝 값 중복이 1급이다**(M0 귀결): 같은 attribute의 두 스텝에 같은 값을 넣은 엔트리로 번들을 구성하면 거부돼야 한다 — 통과하면 스텝 1개짜리 프로그래머로 Store가 실행되고 **무음으로** 모션 0이 된다. (b) **교차 호출(지시 턴 경계)**: 실행 outcome에 비면제 라인 `skipped_already_executed`가 포함된 형상에서 the 툴 **shall** 해당 인스턴스화를 성공으로 보고하지 않고 교차 호출 충돌을 명시 실패로 보고한다(REQ-FXLIB-011 (b)).
- 검증: `test_fx_instantiate.py` — 면제 3종(`Clear`/`ClearAll`/bare 선택)의 중복은 통과함을 대조군으로 확인. 교차 호출 시나리오는 fake outcome 주입 + 뮤테이션(성공 문면이 나오면 죽는다)으로 확인하며, **재현 형상은 `Step 2` 접힘을 포함한다** — `Step <k>`는 면제 3종이 아니고 전 패턴 공통 문자열이므로, 같은 지시 턴의 2번째 인스턴스화는 **서로 다른 패턴이어도** 접힌다(design.md §5). 따라서 교차 호출 테스트는 "같은 패턴 × 두 그룹"과 "다른 패턴 × 두 그룹" **양쪽**을 세운다.
- **가드 (a)의 비공허성이 특히 중요하다**: 효과가 기계로 확인되지 않으므로(§A 폴드인 주) 이 가드를 통과한 결함은 **라이브에서 사람이 볼 때까지 아무 신호도 내지 않는다**. 가드 검사를 지운 뮤테이션이 반드시 죽어야 한다.

### AC-FXLIB-010 — Store 안전 (REQ-012)

- the 인스턴스화 **shall** `/Overwrite` 대소문자 무관 0건을 유지하고, 시퀀스 번호는 재조회 실측 빈 번호만 쓰며, truncated=참에서 자동 배정을 거부 + 명시 보고하고, 사용자 지정 점유 번호를 거부한다.
- 검증: `test_fx_instantiate.py` — fake 재조회(점유/빈/truncated 각 시나리오).

### AC-FXLIB-011 — 익스큐터 비자동 (REQ-013)

- 익스큐터 미지정 호출의 번들에 `Assign` **shall** 0건; 명시 지정 시에만 말미 1줄.
- 검증: `test_fx_instantiate.py`.

### AC-FXLIB-012 — 한국어 2단 리포트 + 효과 증거 상태 (REQ-014)

- 리포트 **shall** 요약/상세 2단, 생성 산출물(시퀀스·큐·라벨·그룹·패턴), `not_executed` **및 비면제 라인 `skipped_already_executed`** 전파(후자 발생 시 성공 문면 금지 + 불완전 시퀀스·큐가 생성됐을 수 있음을 명시 — REQ-FXLIB-014 (b)), 그리고 **효과 증거 상태를 무조건 명시**한다.
- **효과 증거 문면은 조건부가 아니다 (M0 귀결 — v0.1.0의 분기 문면은 폐기)**: 성공 경로를 포함한 **모든** 리포트가 "효과는 기계로 확인되지 않는다 — 무대/GUI에서 사람이 확인해야 한다"는 취지를 담아야 한다(REQ-FXLIB-014 (c)). 재조회로 확인 가능한 것은 **시퀀스·큐의 존재**뿐이며, 그것을 효과 확인으로 제시하면 이 AC가 **실패**한다. Speed는 **BPM**으로 표기한다(ASSUMPTION-38 GO).
- 검증: `test_fx_instantiate.py` — 실패 주입 시 부분 성공 위장 없음(성공 문면 금지)을 뮤테이션으로 확인. 비면제 `skipped_already_executed` 주입 시에도 성공 문면이 나오면 죽는 뮤테이션을 포함. **성공 경로의 리포트에서 사람 확인 필요 문면을 제거하면 죽는 뮤테이션**을 별도로 포함한다(무조건성의 비공허성).

### AC-FXLIB-013 — find_fx 툴 계약 (REQ-015)

- the `find_fx` 툴 **shall** 스키마 설명과 함께 툴 레지스트리에 등록되고, 매칭 결과/폴백 신호 반환 계약(REQ-FXLIB-015)을 지킨다. the 룰북 자산 **shall** 무변경으로 남는다 — 발견성은 툴 스키마 설명 문면만이 전담한다.
- 검증: `test_fx_tool.py`.

### AC-FXLIB-014 — instantiate_fx 툴 계약 + 발명 금지 (REQ-016)

- the `instantiate_fx` 툴 **shall** rig context 미등재 그룹을 거부하고, `Fixture <slot>` 타깃을 0건으로 유지하며, 실행을 `run_commands` 경로 소비로만 수행한다(fake runner로 호출 경로 assert).
- 검증: `test_fx_tool.py` — 미등재 그룹 주입 뮤테이션.

### AC-FXLIB-015 — 단일 실행 경로 + 경계 (REQ-017)

- `server/fx/**` **shall** transport import 0건: ① `test_architecture.py` 전역 스캔 그린(자동 포섭), ② 실행 위치 식별자 **AST 스캔** offender 0건(raw grep 금지 — 독스트링 위양성 선례), ③ `_NAMED_TOOL_EXEMPTIONS` diff 0.
- 검증: `test_fx_boundary.py` — bridge import 1줄 주입 뮤테이션으로 비공허성 확인.

### AC-FXLIB-016 — LiveLock 제안 강등 (REQ-018)

- LiveLock 활성 상태에서 인스턴스화 **shall** 콘솔 송신 0건 + 제안 전용 — 기존 기제 소비 확인.
- 검증: 기존 LiveLock 테스트 패턴 계승(`test_fx_tool.py`).

### AC-FXLIB-017 — 안전 불변식 상속 (REQ-019)

- `server/safety/**` diff **shall** 0건이고, 스크리닝 의미론(무보류 통과 집합·`Off` 변형 처리)은 기존 테스트가 무변경 그린이다.
- 검증: `git diff --stat` + 기존 safety 스위트 그린.

### AC-FXLIB-018 — 룰북·프리픽스 무변경 (REQ-020)

- `server/rulebook/assets/v2.4.2/**` byte-diff **shall** 0건, 고정 프리픽스 byte-stability 테스트 무변경 그린.
- 검증: `git diff` 0건 + 기존 프리픽스 테스트.

### AC-FXLIB-019 — 제공자 중립 (REQ-021)

- 매칭·툴 표면 **shall** anthropic/gemini 어느 어댑터에도 종속되지 않는다 — 어댑터 무접촉 유닛 검증.
- 검증: `test_fx_tool.py`.

### AC-FXLIB-020 — 전체 회귀 (협상 불가)

- pytest 전체 + vitest 전체 **shall** 킥오프 기준선 대비 신규 실패 0건.
- 검증: M6에서 전량 실행 + 기준선 대조(수치는 착수 직전 실측분).

### AC-FXLIB-021 — M0 라이브 프로브 (LIVE — 2건 중 1번째, M2의 전제)

- 실물 onPC에서 ASSUMPTION-36/37/38/39 판정 **shall** 각각 명시적 섹션 + 접두 행(`GO:` / `DESCOPE:` / `SKIP:` / `REOPEN:`)으로 progress.md §E.2에 기록된다. 각 축의 `ok` 채택 전 **날조 대조군 1발**이 선행돼야 하며, ASSUMPTION-36의 기능(모션 저장)과 증거 채널(재조회)은 **분리 판정**된다. 부정 실측도 유효한 완료다. M0는 게이트 미경유이므로 감사 로그를 증거로 요구하지 않는다(그건 M7 몫).
- 검증(레시피): plan.md §B M0 절차 + progress.md 기록 대조. 판정 어휘는 GO/NEGATIVE/CONDITION_NOT_MET/REOPEN_SCOPE 폐쇄 집합.

### AC-FXLIB-022 — 종단 라이브 인수 + ASSUMPTION-40 판정 (LIVE — 2건 중 2번째, M7)

- 실물 onPC에서 채팅 지시 → 매칭 → 인스턴스화 → **게이트 감사 로그 대조** → 생성 시퀀스·큐 GUI 확인 → **효과의 GUI 사람 관측**이 종단 1회 **shall** 성립한다. 효과 증거 채널은 **GUI 관측으로 확정**돼 있다(M0 — 기계 재조회 분기는 존재하지 않는다). M0 판정(36~39)의 재측정·덮어쓰기는 금지된다.
- **ASSUMPTION-40 판정 동반**: 같은 세션에서 **Pan/Tilt 패턴 1종 이상**을 발화해 스텝 생성 형상이 Dimmer 밖에서도 성립하는지 **shall** 판정하고, 접두 행(`GO:` / `NEGATIVE:`)과 함께 progress.md에 기록한다. ASSUMPTION-40은 **M0가 판정하지 않은 신규 항목**이므로 이 측정은 재측정 금지 규율에 저촉되지 않는다. 부정 판정 시: 비용은 Pan/Tilt 패턴 4종의 효과에 한정되고 스키마·툴 계층은 무영향임을 기록하며(spec.md §C), 그 상태로도 **`pulse`(M0 앵커)의 종단 성립이 확인되면 AC는 PASS다** — 정직한 축소는 유효한 완료다(plan.md §A.3).
- 검증(레시피): plan.md §B M7. 리포트 문면과 실물 관측의 불일치는 그 자체로 기록 대상.

### AC-FXLIB-023 — 금지 형태 `At Step N` 부재 (REQ-022)

- 라이브러리 자산과 **발화되는 모든 번들**에서 `Attribute '<attr>' At Step <k>` 형태 **shall** 0건이다. 스텝 전환은 단독 `Step <k>` 라인으로만 나타난다. 검사는 대소문자 무관이며, 라이브러리 전수 + 패턴 전수(6종) 번들 산출물 양쪽을 스캔한다.
- 검증: `test_fx_instantiate.py`(번들 산출물 전수) + `test_fx_library.py`(자산 전수). 뮤테이션: 빌더가 `Attribute 'Dimmer' At Step 2`를 내도록 1줄 주입하면 이 AC가 죽어야 한다.
- **왜 별도 AC인가**: 이 형태는 콘솔이 `ok:true`로 접수하고(M0 실측), 효과는 기계로 확인되지 않는다 — 즉 **런타임의 어떤 신호도 이 결함을 드러내지 않는다.** M0 프로브 자신이 이 형태로 페이저 생성에 3회 실패했다(raw-log-01.md §10.0). 형태 금지의 전수 검사가 유일한 방어선이므로 어휘 AC(AC-FXLIB-003)에 섞지 않고 독립시킨다.

## §D. Edge Cases

- 그룹은 실존하나 이름이 한글/공백 포함 — v1은 인용명형(`Group '<이름>'`)을 발화하지 않는다: rig context 등재 **번호로 변환해 bare `Group <n>` 번호형으로 발화**함을 확인(REQ-FXLIB-009 — 번호형만 라이브 검증, 인용명형은 [문서] 등급 문법 유도).
- 재조회 sequences 섹션 자체가 오지 않음(`path_not_resolved`/`console_unreachable`) — 자동 배정 거부 + 신호 전파.
- 시퀀스 풀 점유 24개 초과(truncated) — 자동 배정 거부 경로.
- MAtricks 선언 없는 패턴 — `Set Selection`/`Reset` 라인 0건(불필요 라인 금지).
- reverse=참 — `Thru -360` 형만 변경, 다른 라인 불변.
- 매칭 입력이 빈 문자열/공백 — 폴백 신호(예외 아님).
- **`steps` 길이 1인 엔트리** — 로더가 명시 에러로 거부(페이저 미성립). 조용한 통과 금지.
- **`steps` 3단 이상** — `Step 2`·`Step 3` 라인이 각각 단독으로, 각 스텝 값 라인 앞에 나온다. `Step 1`은 여전히 0건.
- **같은 attribute의 두 스텝 값이 동일** — 로더 거부(REQ-FXLIB-005 ③) + 구성기 가드 거부. 어느 쪽도 통과시키지 않는다.
- **같은 지시 턴의 2회차 인스턴스화** — `Step 2`부터 접히므로 outcome 검출이 명시 실패로 보고. 1회차 성공 + 2회차 무음 성공은 **금지된 결과**다.

## §E. Quality Gate 기준

- 신규 `server/fx/**` 커버리지 ≥ 85%(프로젝트 기준), ruff 클린, 신규 실패 0.
- 경계: AC-FXLIB-015의 3중 검증 전부 그린.
- 문서: progress.md M0/M7 기록이 접두 행 grep으로 기계 확인 가능.

## §F. Definition of Done

1. AC-FXLIB-001~023 전부 PASS (부정 실측 분기 포함 — DESCOPE는 기록과 함께 PASS다).
2. clarification 마커 0건 유지, **ASSUMPTION-36~40** 전부 판정 기록 존재(36~39는 M0 §E.2, 40은 M7).
3. PRESERVE 목록(plan.md §A.5) diff 0건.
4. 전체 회귀 그린(AC-FXLIB-020) + 라이브 2건 기록 완결.
5. 리포트 문면에 **효과의 기계 검증 불가 + 사람 확인 필요**가 성공 경로를 포함한 모든 경로에서 실재(REQ-FXLIB-014 (c) — 무조건 문면).
6. 전 패턴 번들에 스텝 쌍 실재 + 금지 형태 `At Step <k>` 0건(AC-FXLIB-008 · AC-FXLIB-023).
