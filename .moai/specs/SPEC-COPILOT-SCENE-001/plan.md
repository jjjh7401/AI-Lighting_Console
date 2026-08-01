# SPEC-COPILOT-SCENE-001 — 구현 계획 (plan)

> 마일스톤 **M0~M8** (**M0~M8 전부 실행 완료**), 결정 등록부 **11건(A~K) 전부 해소**, 열린 결정 **0건**, clarification 마커 **0건**. 정본 토큰 계약: REQ **21건** · AC **24건** · ASSUMPTION **5건(41~45 — 41·42는 판정 후 moot)** · 라이브 세션 **2회(2/2 소진)**. 마일스톤별 `- **AC**:` 줄은 `acceptance.md §C.0a`와 1:1이며, 합 **24 · 중복 0 · 누락 0**이다.
>
> **한 줄 요약**: 룩(정적 값) + 이펙트(스텝 열) + 타이밍을 **하나의 큐**로 합성한다. 형상의 정본은 `design.md §3`(결합 순서), 가드 정책의 정본은 `design.md §4`, **트래킹 정책의 정본은 `design.md §6`(균일 집합 + 미주장 열거)** 이다 — **셋 다 병렬 브리프에 문면 그대로 주입되는 공유 계약**이다(§F).
>
> **⚠️ v0.2.0 개정 — 읽기 전에 알아야 할 것**: M0 라이브 프로브가 **D1(전 큐 `/CueOnly`)을 무너뜨렸고**, 사용자가 **속성 집합 균일화 + 미주장 속성 전수 열거**로 대체했다. 판정 정본은 `progress.md §E.2`이며, 개정 근거 조사는 `.moai/reports/scene-uniform-attribute-set-proposal.md`다. **D2·D3는 개정되지 않았고 ASSUMPTION-44/45 `GO`로 오히려 강화됐다.** plan-artifact 해시가 바뀌었으므로 **plan-audit 재실행이 강제된다.**

## §A. 접근 요약 (Context)

### §A.0 출처 — 선행 SPEC이 비워 둔 좌석

본 SPEC은 새로 발명된 범위가 아니다. FXLIB이 **세 곳에서 명시적으로** 이 좌석을 예약했다:

| 위치 | 인용 |
|---|---|
| `SPEC-COPILOT-FXLIB-001/spec.md:42` | "프리셋 저장은 명시적 비목표다 … 그 축은 **씬 컴파일러 후속 SPEC의 몫이다**(§D)." |
| `SPEC-COPILOT-FXLIB-001/spec.md:140` (§D 제외 범위) | "**이 축은 씬 컴파일러 후속 SPEC의 몫이다.**" |
| `SPEC-COPILOT-FXLIB-001/spec.md:70` (REQ-FXLIB-001) | "**후속 소비자(씬 컴파일러·큐리스트 이펙트 축)가 소비 가능한 형상이어야 한다.**" |

세 번째 인용이 특히 구속력을 갖는다 — FXLIB의 스키마는 **본 SPEC이 소비할 것을 전제로** 설계됐다. 즉 씬 컴파일러는 상류가 남긴 인터페이스 계약을 **이행**하는 것이지, 상류를 사후에 비트는 것이 아니다.

파이프라인 위치: LOOKLIB(정지 화면 어휘) · FXLIB(시간축 어휘)이 **1단계 — 의도**. 본 SPEC이 **2단계 — 메모리**.

### §A.1 결정 검토 우선순위 (되돌리기 어려운 순 — 빌드 순서 아님)

리뷰는 아래 순서로 본다 — 가장 바꾸기 어려운 결정이 먼저다.

| 순위 | 결정 | 왜 먼저 보나 |
|---|---|---|
| 1 | **트래킹 정책 = 균일 집합 + 미주장 열거** (D1 개정 — 결정 A) | **데이터 모델의 뿌리이며 이미 한 번 뒤집혔다.** 최초 정책(`/CueOnly`)이 M0 실측으로 폐기됐다 — 되돌리기 어려운 결정이 실제로 되돌려진 사례이므로 리뷰 1순위는 **개정본의 논거가 실측과 정합한가**다. 확인 지점: ① 폐기 근거 2건이 `progress.md §E.2`와 일치하는가, ② 균일 집합이 **자산 편집 0건**으로 성립하는가(32/32 측정), ③ **관측 천장이 바뀌지 않았다는 사실**이 리포트 규율에 반영됐는가(design.md §6.2 — 같은 실패 모드의 재생산이 최대 위험) |
| 2 | **결합 순서 = 룩 먼저 · 충돌은 이펙트 우선** (D2 — 결정 B) | **사용자 대면 동작 + 형상 계약.** 순서를 뒤집으면 룩이 페이저의 종점이 되어 사용자가 본 것과 지시한 것이 달라진다. 그리고 그 결함은 **기계로 검출되지 않는다**. 정본 design.md §3 |
| 3 | **상류 비공개 함수 import** (결정 D) | **신규 타입 인터페이스 결합.** 씬이 `_values_line`·`_step_lines`에 결합한다 — 저장소 선례가 2건 있으나(busking, songcue) 둘 다 **패키지 내부**였고 씬은 **패키지 간**이다. 되돌리려면 재구현이고, 재구현은 무음 드리프트다. design.md §2.2 |
| 4 | **`/Merge` 미사용 · 신규 큐 번호 전용** (D3 — 결정 C) | 안전망 유지 결정. 라이브 실측이 뒷받침하므로(SPEC-COPILOT-SONGCUE-001/progress.md:337-344) 근거는 단단하지만, 큐 편집 축을 통째로 닫는 범위 결정이기도 하다 |
| 5 | **1차 가드 = raise (fx 정책)** (결정 F) | 세 선례가 갈려 있어 **선택**이 필요했다. 논거는 "씬 번들은 하나의 Store라 잔여가 없다" — design.md §4.1 |
| 6 | **기계적 미러 구현** (스키마/로더/매칭/툴 배선) | LOOKLIB·FXLIB 선례를 따르는 기계 작업 — 마지막에 본다 |

### §A.2 빌드 순서 vs 차단 표 — 무엇이 무엇을 막는가

빌드 순서는 M0 → M1 → … → M8 선형이지만, **M0의 네 항목이 전부 뒤를 막는 것은 아니었다**(LOOKLIB 과일반화 교훈 계승). **M0는 실행 완료됐고, 아래 표는 그 판정 결과를 담는다.**

| 항목 | 막던 대상 | 판정 (2026-08-01) | 귀결 |
|---|---|---|---|
| **ASSUMPTION-41** (`/CueOnly` 접수) | **M4 번들 형상 전체** — 모든 Store 라인 | **`CONDITION_NOT_MET`** — 날조 대조군 `/CueOnlyy`가 `ok`+저장까지 되어 `ok`·재조회 **두 기계 채널이 동시에 소진** | **차단이 실제로 발동했다.** run-phase 중단 + 블로커 보고 → 사용자 재결정 → **D1 개정**. 개정 후 **moot** (플래그를 쓰지 않으므로 접수 여부가 무엇도 막지 않는다) |
| **ASSUMPTION-44** (룩+fx 결합 성립) | **M4 번들 형상 + M2 엔트리 저작** | **`GO`** — 사람 GUI: 파란색 유지 + 딤머 순차 웨이브 | **차단 해제.** `design.md §3.1` 골격이 실측으로 확정 — 이제 가정이 아니다 |
| **ASSUMPTION-42** (트래킹 차단 효과) | **없음 — 저작을 막지 않는다** | **`INCONCLUSIVE`** — A/B 대조에서 A=B(둘 다 이월) | append-only 제약으로 설명됨(spec.md §C.1a-1). 개정 후 **moot**. 부수 수확: **전방 트래킹의 실재가 확인**됐다(B군 잔존) |
| **ASSUMPTION-45** (충돌 승자 관측) | **없음** | **`GO`** — 사람 GUI: 딤머 펄스(이펙트 승) | `design.md §3.3` 규칙 확정. 열거 자체는 정적 계산이라 원래 관측 무관 |
| **ASSUMPTION-43** (임의 큐 번호) | **없음** — SONGCUE가 `Cue 2`를 이미 라이브 성립시켰다 | **`GO`** — 단 판정 대상을 **v1 범위(정수·신규·오름)** 로 좁혀서다. 좁히지 않은 원형("임의")은 역순 축에서 부정이 실측됐다 | 신규 정수 번호는 성립 / **역순 저장은 거부**(append-only) / **`truncated: True` 실측**(childCount 24, 반환 18) — REQ-SCENE-013 (d) 가드가 **실재 조건에 대한 방어**임이 확인됐다. 소수 큐는 여전히 미측정 §D |

**M0가 남긴 교훈 3건 (승계 필수)**:

1. **차단 항목의 판정이 "실측 불가"로 끝날 수 있다.** 플랜은 `GO`/`NEGATIVE`/`CONDITION_NOT_MET` 세 갈래를 예상했으나, 실제로는 **대비책까지 무너지는** 네 번째 상태였다("`ok`가 무력하면 재조회에 의존한다"가 성립하지 않음). 프로브 설계는 **대비책 자체의 실패 가능성**을 예상 분기에 넣어야 한다.
2. **프로브별 시퀀스를 분리하라.** 플랜의 프로브 A와 B가 같은 `Sequence 191 Cue 1`을 대상으로 삼아 대조군이 표적을 점유했다. 우연히 그 충돌이 판정의 핵심 근거(A′)를 낳았으나, 설계로는 결함이다.
3. **거부 메시지 리터럴에 의존하지 마라.** 원인마다 다르다(`User Canceled Command` vs `Not allowed`).

### §A.3 정직한 축소 원칙 (계승)

부정 실측은 실패가 아니라 유효한 완료 상태다. 축소가 일어나면 (a) 무엇이 축소됐는지, (b) 어느 판정이 유발했는지, (c) 사용자 대면 문면에 어떻게 반영되는지를 progress.md에 기록한다. 부분 성공을 전체 성공으로 위장하지 않는다.

**단, D1은 예외다.** ASSUMPTION-41 부정은 축소가 아니라 **중단**이다 — 사용자 확정 정책이 성립 불가임이 드러난 것이므로, 에이전트가 대체 정책을 골라 진행하는 것은 결정 월권이다.

> **이 예외는 가정이 아니라 실행 이력이다.** 2026-08-01 M0에서 ASSUMPTION-41이 `CONDITION_NOT_MET`으로 닫히자 run-phase가 중단·블로커 보고됐고, 사용자가 대체 정책을 확정했다. **에이전트가 무플래그 폴백을 골랐다면 사용자는 정책이 바뀐 사실조차 몰랐을 것이다.** 규칙이 실제로 값을 한 사례이므로 후속 SPEC도 이 예외를 유지한다(REQ-SCENE-021 (b)로 요구화됨).

### §A.4 결정 등록부 — **해소 11건 / 미해결 0건** (재질의 금지)

| # | 결정 | 내용 · 근거 |
|---|---|---|
| **A** | **트래킹 정책 = 속성 집합 균일화 + 미주장 전수 열거** (D1 **개정** — `/CueOnly` 폐기) | 사용자 재확정(2026-08-01, M0 실측 후). **폐기 근거 2건 전부 `[실측]`**: ① 미지 플래그가 조용히 접수돼 접수 판정의 기계 채널이 소진, ② 큐 생성이 실질 append-only라 `/CueOnly`의 보정 대상이 존재할 수 없음(정본 `progress.md §E.2`). **개정본**: 균일 집합 = 코어 4(`Dimmer`+RGB3) — 라이브러리 32/32가 이미 충족하고 LOOKLIB이 이미 3개 테스트로 강제 중이므로 **자산 편집 0건**. `Zoom`/`Iris`는 균일 보장 밖(방향 미측정 — 채움값 발명 금지). 닫지 못한 축(Pan/Tilt 포함)은 **매 컴파일 전수 열거**. 정본 design.md §6, 조사 `.moai/reports/scene-uniform-attribute-set-proposal.md`. 주장 분리 보고 의무는 REQ-SCENE-014 |
| **B** | **결합 순서 = 룩 먼저, 충돌은 이펙트 우선** | 사용자 확정 D2. **정본 design.md §3.** 강제 근거: `MIN_STEPS = 2`(`server/fx/schema.py:66`) + `Step 1` 미발화(`server/fx/instantiate.py:326-342`) → 스텝 1 = 현재 프로그래머 상태 = 룩의 자리. 충돌 열거는 정적 교집합 계산(REQ-SCENE-005) |
| **C** | **`/Merge` 0건 · 신규 큐 번호 전용** | 사용자 확정 D3. SONGCUE 라이브 실측(SPEC-COPILOT-SONGCUE-001/progress.md:337-344): 새 번호는 `/Merge` 유무 무관 동일, 기존 번호는 무플래그가 **`Not allowed` 거부** — 그 거부가 `server/fx/instantiate.py:225`가 "the LAST line of defence"라 부르는 안전망. `/Merge`는 실익 0에 안전망만 잃는 거래 |
| **D** | **상류 재사용 = 비공개 함수 읽기 import** | design.md §2.2. 선례 2건: `server/looks/busking.py:30`(`_values_line`, 주석 "dedupe가 비교하는 문자열의 단일 출처") · `server/looks/songcue.py:11`. 재구현은 두 벌을 갈라지게 하고 **갈라짐은 무음**이다. 패키지 간 결합이라는 간격은 `test_scene_boundary.py`의 산출 형상 고정이 메운다 |
| **E** | **면제 집합 사본 0** | `is_programmer_state`가 fx `__all__` 등재 **공개 API**(`server/fx/instantiate.py:144`)이므로 호출만 한다. fx가 자기 사본을 두면서 `test_fx_boundary.py:256-379`에 동치 단언 의무를 진 것과 달리, **씬은 사본을 만들지 않으므로 그 의무를 상속하지 않는다** |
| **F** | **1차 가드 = raise (fx 정책)** | 세 선례가 갈림: fx=raise(`instantiate.py:432`) · busking=skip(`busking.py:240`) · songcue=skip+원장(`songcue.py:436`, `:243`). **씬은 fx를 따른다** — fx 독스트링의 논거가 그대로 적용된다: "an fx bundle is ONE store; there is no surviving remainder to report." 씬 번들도 정확히 하나의 Store다(design.md §4.1) |
| **G** | **2차 가드 = `collided_lines` 재사용** | `server/fx/instantiate.py:537`, `__all__` 등재 공개 API. 인자가 `Sequence[object]` outcome이고 fx 스키마를 참조하지 않는 **순수 함수**이므로 씬 전용 사본을 만들 이유가 없다. **looks 쪽에는 대응물이 아예 없다** — 2차 가드는 fx에만 존재한다(design.md §4.2) |
| **H** | **시퀀스 번호 = fx `select_sequence_number` 소비 / 큐 번호 = 씬 자기 로직** | `select_sequence_number`가 **두 벌** 존재(`server/fx/instantiate.py:218` 공개·`requested=` 지원·점유 거부 / `server/looks/songcue.py:286`). 씬은 fx 판을 쓴다 — 계약이 정확히 일치. **세 번째 판을 쓰지 않는다.** 큐 번호는 fx가 `_CUE_NUMBER = 1` 상수 고정(`:96`)이라 재사용 불가 → 씬 자기 로직(design.md §5) |
| **I** | **번들 조립기는 씬이 자기 것으로 갖는다** | `build_fx_bundle`을 호출하고 Store 라인을 치환하는 설계는 기각. **개정으로 논거 하나가 약해졌다 — 정직 표기**: 원래 이유는 ① `Cue 1` 고정 + ② `/CueOnly` 부재였는데, 씬도 무플래그가 됐으므로 ②는 소멸했다(두 Store 라인은 이제 **큐 번호에서만** 다르다). 그래도 결정은 유지된다 — ①이 단독 성립하고, 더 근본적으로 **fx 번들에는 룩 값 라인을 끼울 자리가 없다**(`:475-477`이 `Group` 다음 곧바로 스텝 열). 씬은 **값 라인만** 상류에서 받고 조립·Store는 자기가 한다(design.md §5, AP-5) |
| **J** | **SONGCUE 상속 부채는 기록만** (개정으로 **범위 축소**) | SONGCUE는 무플래그 Store(`server/looks/songcue.py:462-466`) → 오늘 그 큐 값들은 트래킹된다. **개정 전에는 "두 플래그 정책의 공존"이 부채를 표면화한다고 적었으나, 씬도 무플래그가 됐으므로 그 분기는 사라졌다**(게다가 M0 실측상 플래그를 달았어도 차이가 없었을 것이다). 남는 대비는 하나 — **SONGCUE는 균일 집합을 강제하지 않는다.** `server/looks/**`는 PRESERVE이므로 **기록하되 고치지 않는다**(design.md §6.4, spec.md §D) |
| **K** | **미주장 열거의 유니버스 = `server.looks.schema.KNOWN_ATTRIBUTES` 읽기 import** (개정 신설) | 오늘 정확히 8원소(유니온6 ∪ {Pan, Tilt}). **사본을 만들지 않는다**(결정 E와 동형) — 만들면 동치 단언 의무가 생기고 두 벌이 갈라질 수 있다. 대신 경계 테스트가 **오늘의 8원소 구성을 형상 고정**해 상류 어휘 확장이 조용히 열거를 넓히는 것을 막는다. **대비되는 선택**: `SCENE_UNIFORM_ATTRIBUTES`는 의미 소유권이 달라(상류 `CONFIRMED_ATTRIBUTES` = "측정된 속성", 씬 = "반드시 주장할 속성") **씬 소유 상수 + 동치 단언**을 택했다 — 결정 E가 경계한 사본의 대가를 **알고 지불한다**(design.md §6.1) |

### §A.5 PRESERVE 목록 (무변경 대상 — 읽기 import만)

| 대상 | 규율 |
|---|---|
| `server/looks/**` (schema/loader/roles/resolver/instantiate/matching/busking/report/songcue*) | 수정 금지 — 읽기 import만. `_values_line` 읽기 참조는 선례가 있는 적법 경로(결정 D). **개정으로 읽기 대상 2건 추가**: `schema.KNOWN_ATTRIBUTES`(미주장 열거 유니버스 — 결정 K) · `schema.CONFIRMED_ATTRIBUTES`(균일 집합 동치 단언 대상). **둘 다 공개 이름이며 자산·로직 무편집** — 옵션 D는 자산 무편집이므로 경계 교차가 없다 |
| `server/fx/**` (schema/loader/matching/instantiate/report + library/) | 수정 금지 — 읽기 import만. `_step_lines`·`_phase_lines`·`_speed_line`·`_matricks`(비공개) + `is_programmer_state`·`collided_lines`·`select_sequence_number`(공개) |
| `console/lua/**` | 무변경 |
| `server/rulebook/assets/**` | byte-diff 0. **씬 어휘를 룰북에 추가하지 않는다** — `test_fx_boundary.py:595`가 fx에 대해 단언한 것과 같은 규율 |
| `server/safety/**` (gate/classify/blacklist/lock/console/preview) | 무변경 — 스크리닝 의미론 소비만 |
| `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(:327-331)·dedupe 루프(:688-712) | 무변경 — 툴 2종 등록만 추가 |
| `server/bridge/**` | import 자체 금지 (REQ-SCENE-019) |

**게이트**: 각 마일스톤 완료 시 `git diff --stat <BASE>..HEAD -- server/looks server/fx console/lua server/rulebook/assets server/safety` 가 **빈 출력**이어야 한다(AC-SCENE-017). BASE는 착수 시점 SHA를 progress.md에 기록하고 그것을 쓴다.

## §B. 마일스톤 (M0..M8)

각 마일스톤은 착수 직전 baseline(전체 pytest)을 직접 실측한다 — plan-phase 수치를 이월하지 않는다. 줄 앵커는 착수 직전 재실측한다.

### M0 — 라이브 프로브 (cycle_type=none — 측정 세션, 코드 변경 0) 【**실행 완료 2026-08-01 · 정리 잔여는 M8에서 닫힘 — AC-SCENE-019 충족**】

> **판정 정본은 `progress.md §E.2`다.** 본 절은 완료 기록이며 증거 원문을 복제하지 않는다. M0의 존재 이유였던 두 차단 항목(ASSUMPTION-41 `/CueOnly` 접수 · ASSUMPTION-44 룩+fx 결합)은 **하나가 차단을 발동시켰고 하나가 해제됐다.**

- **세션 조건 (기록)**: onPC `127.0.0.1:8000`, 응답기 수신 `9005`, **CopilotResponder v1.5.0**, 착수 시 `DataPool/Sequences` childCount **17**, 프로브 그룹 **13 (All)**. **게이트 미경유(bridge 직결)이므로 감사 로그가 없다** — 증거는 콘솔 응답 원문 + 사용자 GUI 관측이며, 게이트 경유 종단 확인은 M8 몫이다.

- **실행된 프로브 5종과 판정**:

  | 프로브 | 대상 | 시퀀스 | 판정 | 채널 |
  |---|---|---|---|---|
  | **A / A′** | 날조 대조군(`/CueOnlyy`) + 점유 큐 무플래그 Store | 191 | — (판정 재료) | 기계 |
  | **B** | ASSUMPTION-41 `/CueOnly` 접수 | 191 | **`CONDITION_NOT_MET`** | 기계 채널 소진 |
  | **C** | ASSUMPTION-44 룩 + fx 결합 | 192 | **`GO`** | 사람 GUI |
  | **D (A/B군)** | ASSUMPTION-42 트래킹 차단 효과 | 193 / 194 | **`INCONCLUSIVE`** | 사람 GUI |
  | **D″** | 저장 순서 역전 시도 (설계 실패 → 발견) | 196 / 197 | — (append-only 실측) | 기계 |
  | **E** | ASSUMPTION-45 충돌 승자 | 195 | **`GO`** | 사람 GUI |

- **판정이 낸 3개의 결과**:
  1. **D1 정책 폐기 → 개정.** 41의 `CONDITION_NOT_MET`이 §A.3 예외를 발동시켜 run-phase가 중단·블로커 보고됐고, 사용자가 **균일 집합 + 미주장 열거**로 재결정했다. 41·42는 개정으로 **moot**이 됐으나 **삭제하지 않고 이력으로 남긴다** — 개정의 직접 원인이기 때문이다.
  2. **D2·D3 강화.** 44·45 `GO`로 `design.md §3.1` 결합 골격과 `§3.3` 충돌 규칙이 **실측 확정**됐다. 이제 가정이 아니다.
  3. **콘솔 제약 2건 + 가드 근거 1건 신규 확보.** 큐 생성 실질 append-only · 거부 메시지 리터럴 비신뢰(spec.md §C.1a) · **`truncated: True` 실측**(childCount 24 / 반환 18 — REQ-SCENE-013 (d) 가드가 실재 조건에 대한 방어임을 확인).

- **판정 어휘**: **GO / NEGATIVE / CONDITION_NOT_MET / INCONCLUSIVE / REOPEN_SCOPE**, 기록 접두 행은 **`GO:` / `DESCOPE:` / `SKIP:` / `REOPEN:`**이다. **어휘 5종 → 접두어 4종의 매핑 정본은 `spec.md` REQ-SCENE-021의 인라인 표**이며(형태의 출처는 PRECHK `acceptance.md:289` + `progress.md` P1-2/P1-3이지만, 공유 계약을 타 SPEC 요약으로 참조하지 않는다는 §F.3 규율에 따라 본 SPEC이 인라인으로 소유한다), PRECHK에 대응이 없던 `INCONCLUSIVE` 행은 본 SPEC이 신설했다. 각 판정은 progress.md §E.2에 **명시적 섹션**으로 기록하고 **접두 행은 행두(column 0)** 에 둔다(각주 금지 · 헤딩/볼드 스팬 안 금지 — `^` 앵커 grep이 판독 수단이다). ⇒ 이 의무는 v0.2.0에서 **REQ-SCENE-021로 요구화**됐고, 접두 행의 실물은 v0.2.1에서 `progress.md §E.2` 말미에 신설됐다.

- **정리 의무 — 이행 완료 (2026-08-01, M8)**: 프로브가 만든 시퀀스 **191·192·193·194·195·196·197**은 **`Delete`가 블랙리스트라 툴 경로로 지울 수 없어** 사용자가 GUI에서 직접 삭제했고, 기계 재조회로 확인됐다 — childCount **24 → 17** · `truncated` **True → False** · 191~197 **전건 부재**(`progress.md §E.2` M8 절 ③ · 접두 행 `GO: AC-SCENE-019`). **이 항목이 닫히면서 AC-SCENE-019가 완결됐다.**

- **승계 필수 — 프로브 설계 결함 2건**:
  - **프로브 A와 B가 같은 `Sequence 191 Cue 1`을 대상으로 삼았다.** 대조군이 표적을 점유해 설계대로는 B를 실행할 수 없었고, 실제로는 그 충돌을 이용한 A′(점유 큐 무플래그 Store)가 판정의 핵심 근거가 됐다 — **결함이 관측을 도운 우연**이다. 후속 프로브는 프로브별 시퀀스를 분리한다.
  - **대비책의 실패를 분기에 넣지 않았다.** 플랜은 "`ok`가 무력하면 재조회에 의존"을 대비책으로 적었으나 재조회 역시 비변별이었다. 프로브 설계는 **대비책 자체가 무너지는 경우**를 예상 분기에 포함해야 한다.

- **baseline**: 코드 baseline 없음(코드 변경 0).
- **뮤테이션 (설계 시점 항목 — 전부 실제 실행에서 준수됨)**: ① 날조 대조군 없이 `ok`를 증거로 기록하면 AC-SCENE-019가 죽어야 한다 → **대조군이 선행됐고, 그것이 41 판정의 근거가 됐다.** ② 프로브 D를 대조군(B군) 없이 A군만으로 기록하면 죽어야 한다 → **A/B 양군 발화됨.** ③ ASSUMPTION-41 부정에서 무플래그로 폴백해 진행하면 죽어야 한다(결정 월권) → **폴백하지 않고 중단·보고됨.** ④ 접수(41)와 효과(42)를 한 판정으로 합치면 죽어야 한다 → **분리 기록됨.**
- **파일**: 코드 변경 0. 기록은 progress.md §E.2.
- **AC**: AC-SCENE-019.

### M1 — 씬 스키마 + 로더 (cycle_type=tdd)

- **요구·설계 지시**: REQ-SCENE-001, REQ-SCENE-003, REQ-SCENE-004, REQ-SCENE-006. 씬 스키마: 아이덴티티, 참조 축(`look_id`/`fx_id` — 각각 선택, **최소 1개 필수**), 타이밍 축(전부 선택), 라벨, `schema_version`. **값 축을 복제하지 않는다** — 참조만 담는다. 트리거 토큰 폐쇄 집합(`Go`/`Time`/`Follow`/`Sound`/`BPM` — Capitalized).
  - **로더 검증 5종**: ① 미지 필드 거부, ② 중복 scene id 거부, ③ **`look_id`·`fx_id` 동시 부재 거부**(REQ-SCENE-003), ④ 수치 범위(`cue_number` > 0 정수, `trig_time` ≥ 0), ⑤ 미지 `trig_type` 거부. 전부 순수 함수, 콘솔 무접촉.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측 + M0 판정 접두 행 존재 확인(progress.md §E.2).
- **뮤테이션**: ① 미지 필드를 통과시키면 AC-SCENE-001이 죽어야 한다. ② `look_id`/`fx_id` 동시 부재를 통과시키면 AC-SCENE-002가 죽어야 한다. ③ per-show 필드(그룹/FID/익스큐터)를 스키마에 추가하면 AC-SCENE-004가 죽어야 한다. ④ 소문자 `trig_type`을 통과시키면 AC-SCENE-001이 죽어야 한다.
- **파일**: 신규 `server/scene/__init__.py`, `server/scene/schema.py`, `server/scene/loader.py`; 테스트 `server/tests/test_scene_schema.py`.
- **AC**: AC-SCENE-001, AC-SCENE-002.

### M2 — 내장 씬 라이브러리 저작 (cycle_type=tdd) 【병렬 슬라이스 A】

- **요구·설계 지시**: REQ-SCENE-002, REQ-SCENE-004. 씬 엔트리 저작(YAML — `server/scene/library/*.yaml`). 각 엔트리의 `look_id`·`fx_id`는 **실존 라이브러리 id만** 참조하며, 전수 테스트가 상류 라이브러리를 로드해 **모든 참조가 해석되는지** 확인한다(끊긴 참조 0건). 한국어 무드 키워드 1급. per-show 값 0건.
  - **커버리지**: 룩+이펙트 결합 씬 ≥ 3, 룩 단독 씬 ≥ 1, 이펙트 단독 씬 ≥ 1. **충돌 있는 씬 ≥ 1**을 의도적으로 포함한다 — 충돌 열거 경로(REQ-SCENE-005)가 라이브러리 자산으로도 실증돼야 하기 때문이다. **그 충돌 씬의 fx는 dimmer 또는 color여야 한다** — movement fx는 룩과 교집합이 항상 ∅이라 "충돌 있는 씬"이 될 수 없다(design.md §3.3 각주) `[측정]`. **movement 씬 ≥ 1**도 함께 담는다 — AC-SCENE-024의 Pan/Tilt 케이스와 AC-SCENE-005 위양성 대조군의 자산 재료다.
  - **균일 집합과의 관계**: 씬 엔트리는 룩 **참조**만 담으므로 균일 집합을 직접 만족시키지 않는다 — 만족은 참조된 룩이 한다(오늘 32/32 충족). 다만 저작자는 **미선언 `Zoom`/`Iris`가 채워지지 않는다**는 것을 알고 엔트리를 골라야 한다(§F.3 SC-3).
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① 존재하지 않는 `look_id`를 넣으면 AC-SCENE-003이 죽어야 한다. ② 구체 그룹 번호를 엔트리에 넣으면 AC-SCENE-004가 죽어야 한다. ③ 충돌 씬을 라이브러리에서 빼면 AC-SCENE-005의 자산측 비공허성이 죽어야 한다.
- **파일**: `server/scene/library/*.yaml`(자산), `server/tests/test_scene_library.py`.
- **AC**: AC-SCENE-003, AC-SCENE-004.

### M3 — 2축 자연어 매칭 (cycle_type=tdd) 【병렬 슬라이스 B】

- **요구·설계 지시**: REQ-SCENE-007, REQ-SCENE-008, REQ-SCENE-009. 지시를 룩 축·이펙트 축으로 **분리 해석**하고 각각 상류 매칭 규율을 소비. 한국어 조사 처리, 폴백 3종, 동점 None, 결정론 정렬. **부분 매칭 신호**를 무매칭과 구분해 반환하며, **매칭되지 않은 축을 임의 기본값으로 채우지 않는다**.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① 동점에서 첫 후보를 임의 반환하면 AC-SCENE-006이 죽어야 한다. ② 한 축만 매칭됐을 때 나머지를 기본값으로 채우면 AC-SCENE-007이 죽어야 한다. ③ 무매칭에서 최저점 후보를 강제 반환하면 AC-SCENE-008이 죽어야 한다.
- **파일**: `server/scene/matching.py`, `server/tests/test_scene_matching.py`.
- **AC**: AC-SCENE-006, AC-SCENE-007, AC-SCENE-008.

### M4 — 결합 + 컴파일 번들 빌더 + 가드 + 번호 획득 (cycle_type=tdd) 【병렬 슬라이스 C — 최대 슬라이스】

- **요구·설계 지시**: REQ-SCENE-005, REQ-SCENE-010, REQ-SCENE-011, REQ-SCENE-012, REQ-SCENE-013, REQ-SCENE-015, REQ-SCENE-016, REQ-SCENE-017. **형상 정본은 design.md §3, 가드 정본은 §4, 번호 획득은 §5** — 이 세 절을 인용하며, 요약본을 만들어 쓰지 않는다.
  - **결합**: 룩 값 라인(`_values_line` 상류 소비) → fx 스텝 열(`_step_lines`) → 위상(`_phase_lines`) → 속도(`_speed_line`) → MAtricks(`_matricks`). **재조립 금지**(결정 D).
  - **충돌 열거**: 룩 attribute 집합 ∩ 이펙트 attribute 집합을 정적 계산해 결과에 싣는다. 승자는 이펙트(형상이 강제).
  - **Store**: `Store Sequence <s> Cue <c> '<라벨>'` — **플래그 0건**(`/CueOnly` 포함, 대소문자 무관). `/Merge` 0건, `/Overwrite` 0건(둘 다 대소문자 무관).
  - **균일 집합 강제 (D1 개정 — 정본 design.md §6)**: 룩을 담은 씬의 값 시퀀스를 *(균일 집합 순서 우선 → 나머지는 선언 순서 유지)* 로 정렬해 `_values_line`에 넘긴다(**인자 순서 선택이지 재조립이 아니다** — 결정 D 무위반). 균일 집합을 채우지 못하는 룩은 **`UNIFORM_ATTRIBUTES_INCOMPLETE`로 raise**. `Zoom`/`Iris`는 **선언된 경우에만** 싣고 **채움값을 발명하지 않는다**. 이펙트 단독 씬은 이 강제의 대상이 아니다(룩 값 라인 부재).
  - **미주장 열거**: `KNOWN_ATTRIBUTES`(상류 읽기 import — 결정 K) − (룩 속성 ∪ fx 구동 속성)을 **정적 계산**해 결과에 싣는다. 결정론적 정렬. 문면은 M5 소유.
  - **가드**: 1차 = 비면제 라인 번들 내 유일성 → 위반 시 **raise**(결정 F). 면제 판정은 `is_programmer_state` 호출(사본 0 — 결정 E). 2차 = `collided_lines` 재사용(결정 G).
  - **번호**: 시퀀스는 `select_sequence_number`(fx 판, `requested=` 지원) 소비. 큐는 씬 자기 로직 — 재조회 실측 빈 정수 번호, `truncated` 참이면 자동 배정 거부, 사용자 지정 점유 번호 거부.
  - **트리거**: PROPERTY 형태 2줄, Capitalized 토큰, `TrigTime` 절대 초. `/trig=` 0건. 익스큐터는 명시 지정 시 말미 1줄.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측 + **M0 판정 확인 — ASSUMPTION-44 `GO`**(룩+fx 결합 순서 골격이 실측 확정됐다는 것이 M4의 실질 전제다). **ASSUMPTION-41은 D1 개정으로 moot이며 착수를 막지 않는다** — 41은 `CONDITION_NOT_MET`으로 닫혔고 기계 채널이 소진돼 `GO`로 올릴 경로가 없으므로, 41의 `GO`를 게이트로 두면 M4가 영구 차단된다(개정 전 게이트의 잔재였다. 41이 게이트였던 이유는 `/CueOnly` 발화 여부였고, 씬은 이제 어떤 store 플래그도 쓰지 않는다).
- **뮤테이션**: ① **Store에 `/CueOnly`(또는 임의의 `/Foo`)를 붙이면 AC-SCENE-009가 죽어야 한다** — 콘솔이 미지 플래그를 조용히 접수하므로(M0 실측) 이 assert가 오타 플래그의 유일한 그물이다. ② `/Merge`를 붙이면 AC-SCENE-010이 죽어야 한다(대소문자 변형 포함). ③ `/Overwrite`를 발화하면 AC-SCENE-010이 죽어야 한다. ④ 룩 값 라인을 fx 스텝 열 **뒤로** 옮기면 AC-SCENE-009가 죽어야 한다(결합 순서 역전 차단). ⑤ `Step 2` 라인을 빼면 죽어야 한다. ⑥ 변형 라인을 스텝 열 앞으로 옮기면 죽어야 한다. ⑦ `Attribute 'Dimmer' At Step 2`를 내면 AC-SCENE-012가 죽어야 한다. ⑧ 충돌 attribute 열거를 빈 값으로 고정하면 AC-SCENE-005가 죽어야 한다. ⑨ 번들에 같은 값 라인을 2회 넣어도 통과하면 AC-SCENE-011이 죽어야 한다. ⑩ fake outcome에 비면제 `skipped_already_executed`를 주입했는데 성공 보고가 나오면 AC-SCENE-011 (b)가 죽어야 한다. ⑪ `truncated=참`에서 자동 배정하면 AC-SCENE-013이 죽어야 한다. ⑫ 점유 큐 번호를 통과시키면 AC-SCENE-013이 죽어야 한다. ⑬ 소문자 트리거 토큰(`'follow'`)을 통과시키면 AC-SCENE-014가 죽어야 한다. ⑭ `/trig=` 형태를 내면 AC-SCENE-014가 죽어야 한다. ⑮ 미지정 익스큐터에 `Assign`을 붙이면 AC-SCENE-014가 죽어야 한다. ⑯ **균일 집합에서 한 속성을 빼면 AC-SCENE-023이 죽어야 한다.** ⑰ **정렬을 제거한 뒤 선언 순서가 뒤집힌 룩 픽스처를 주입하면 죽어야 한다** — 오늘 자산 32/32가 이미 정렬돼 있어 **자산만으로는 이 뮤테이션이 살아남는다.** ⑱ **미선언 `Zoom`을 상수로 채우게 만들면 채움 금지 대조군이 죽어야 한다.** ⑲ **미주장 열거를 빈 튜플로 고정하면 AC-SCENE-024가 죽어야 한다.** ⑳ **유니버스에서 `Pan`/`Tilt`를 빼면 movement 미사용 씬 케이스가 죽어야 한다.**

  > **⚠️ 뮤테이션 재료 규율 (승계 필수)**: ⑧(충돌 열거 비공허성)은 **dimmer/color fx 조합으로만** 세운다. **movement fx 8개는 룩과 교집합이 항상 ∅**이므로(룩은 Pan/Tilt를 가질 수 없다) 정답도 빈 집합이고, 그 재료로 세우면 **뮤테이션이 통과해 버린다**(design.md §3.3 각주).
- **파일**: `server/scene/compile.py`, `server/tests/test_scene_compile.py`.
- **AC**: AC-SCENE-005, AC-SCENE-009, AC-SCENE-010, AC-SCENE-011, AC-SCENE-012, AC-SCENE-013, AC-SCENE-014, AC-SCENE-023.

### M5 — 리포트 (주장 분리 + 미주장 열거) (cycle_type=tdd)

- **요구·설계 지시**: REQ-SCENE-014. 한국어 2단 리포트(요약 + 상세). **주장을 분리한 모듈 상수**를 정의하고 리포트가 그것을 싣는다(정본 design.md §6.2 표):
  - (a) 기계 확인됨 — 시퀀스·큐 존재/이름/`cueNo`, 발화 수, `not_executed`·비면제 `skipped_already_executed` 전파.
  - (a′) 기계 확인됨 — **값 라인이 균일 집합을 이 순서로 담았다**(정적 검사).
  - (b) 효과 — **무조건** "기계 확인 불가, 사람 GUI 필요"(성공 경로 포함 전 경로).
  - (c) 트래킹 무해화 — **관측 채널 부재**를 명시하고, **(a′)를 (c)의 증거로 제시하지 않는다.** **(a′)와 (c)는 같은 문단에 두지 않는다** — 붙여 쓰면 독자가 전자를 후자의 증거로 읽으며, 그것이 `/CueOnly` 때의 실패 모드다.
  - (d) **미주장 속성 전수 열거** — M4가 계산한 차집합을 싣는다. 문면은 "이월될 **수 있다**"까지만 주장하고 **"이월됐다"고 적지 않는다.**
  - 충돌 열거(AC-SCENE-005)와 미주장 열거(AC-SCENE-024)는 **서로 다른 것**이며 문면이 둘을 구분해야 한다. 비면제 `skipped_already_executed` 발생 시 **성공 문면 금지** + 불완전 큐 생성 가능성 명시.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① 성공 경로 리포트에서 (b) 문면을 빼면 AC-SCENE-015가 죽어야 한다(무조건성의 비공허성). ② (c)를 (a′)와 합쳐 "확인했다"로 적으면 죽어야 한다. ③ **균일성 확인을 트래킹 무해화의 근거로 문면화하면 죽어야 한다.** ④ 상수 대신 산문 부분 일치로 검증하도록 테스트를 바꾸면 그 테스트가 뮤테이션을 놓쳐야 한다(= 상수 동일성 검사의 필요 실증). ⑤ 비면제 `skipped_already_executed`가 있는데 성공 문면이 나오면 죽어야 한다. ⑥ **미주장 열거 문면을 "이월됩니다"로 바꾸면 AC-SCENE-024가 죽어야 한다.** ⑦ **열거 정렬을 제거해 집합 순회 순서에 맡기면 결정론 단언이 죽어야 한다.**
- **파일**: `server/scene/report.py`, `server/tests/test_scene_report.py`.
- **AC**: AC-SCENE-015, AC-SCENE-016, AC-SCENE-024.

### M6 — 툴 표면 + 배선 (cycle_type=tdd)

- **요구·설계 지시**: REQ-SCENE-018. `find_scene`·`compile_scene`을 기존 툴 레지스트리(`build_toolset`)에 등록. **핸들러는 `run_commands` 클로저의 caller다** — 제2 실행 표면 금지(`server/orchestrator/tools.py:848-858`·`:1688-1698`의 `@MX:ANCHOR` 형상 계승). 대상 그룹 실존 검증(rig context 등재분만, `Fixture <slot>` 금지). 툴 스키마 설명이 발견성 전담(룰북 무변경). 제공자 중립.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① rig context 미등재 그룹을 통과시키면 AC-SCENE-018이 죽어야 한다. ② 툴이 게이트를 우회해 bridge/execution_port를 직접 부르면 AC-SCENE-018(및 `test_architecture`)이 죽어야 한다. ③ `Fixture <slot>` 타깃을 통과시키면 죽어야 한다.
- **파일**: `server/orchestrator/tools.py`(툴 등록만), `server/tests/test_scene_tool.py`.
- **AC**: AC-SCENE-018.

### M7 — 회귀 + 경계 전체 그린

- **요구·설계 지시**: pytest 전체 + vitest 전체 — 킥오프 기준선 대비 신규 실패 0건. `test_architecture.py` 그린 + `server/scene/**` **AST 식별자 스캔**(offender 0건 — raw grep은 독스트링 위양성으로 기각된 선례, `test_looks_boundary.py:85`/`test_fx_boundary.py:132` 방식) + 예외 명단 고정 확인(`_NAMED_TOOL_EXEMPTIONS`가 정확히 `{server/tools/osc_smoke.py, server/tools/responder_roundtrip.py}` — `test_fx_boundary.py:228-230`) + PRESERVE byte-diff 0 + **LiveLock 강등**(locked ⇒ 송신 0, 전 커맨드 `status == "proposal"`(Store 포함), `is_error is False`, `succeeded is False` — `test_fx_boundary.py:459` 패턴) + **상류 산출 형상 고정**(`_values_line`·`_step_lines`의 알려진 입력 대비 산출 고정 — 결정 D의 대가를 갚는 테스트) + **상류 상수 결합 2건 고정(개정 신설)**: ① `SCENE_UNIFORM_ATTRIBUTES == server.looks.schema.CONFIRMED_ATTRIBUTES` **동치 단언**(결정 K의 대가), ② `server.looks.schema.KNOWN_ATTRIBUTES`가 **오늘 정확히 8원소**임을 형상 고정(미주장 열거 유니버스의 조용한 확장 차단).
- **baseline**: 착수 직전 전체 테스트 직접 실측.
- **뮤테이션**: ① `server/scene/`에 bridge import 1줄을 주입하면 AC-SCENE-017이 죽어야 한다. ② `server/scene/`를 예외 명단에 추가하면 죽어야 한다. ③ 룰북 자산 1바이트를 바꾸면 AC-SCENE-017이 죽어야 한다. ④ LiveLock 상태에서 Store만 송신되게 바꾸면 AC-SCENE-020이 죽어야 한다. ⑤ 상류 산출 형상을 바꾸면 형상 고정 테스트가 죽어야 한다(무음 드리프트 차단의 비공허성). ⑥ **`SCENE_UNIFORM_ATTRIBUTES`에 원소를 하나 더하면 동치 단언이 죽어야 한다.** ⑦ **`KNOWN_ATTRIBUTES` 유니버스 형상 고정을 지우면, 상류에 속성을 1개 추가한 픽스처에서 미주장 열거가 조용히 넓어지는 것이 잡히지 않아야 한다**(= 형상 고정의 필요 실증).
- **파일**: `server/tests/test_scene_boundary.py`; 수정 0(검증 마일스톤).
- **AC**: AC-SCENE-017, AC-SCENE-020, AC-SCENE-022.

### M8 — 종단 라이브 검증 (실물 onPC)

- **요구·설계 지시**: 실물 콘솔에서 종단 1회: 채팅 지시("파란 백라이트가 천천히 웨이브하는 씬 만들어줘") → `find_scene` 매칭 → `compile_scene` → 실행 프리뷰 관측 → **게이트 감사 로그 확인**(M0가 못 한 몫) → 생성 시퀀스·큐 **재조회 확인** → **효과의 GUI 사람 관측** + **리포트 주장 분리 문면 + 미주장 열거가 실물과 일치하는지 확인**. M0에서 닫은 ASSUMPTION(41/44)을 재측정하지 않는다 — 어긋남이 관측되면 그 불일치 자체를 기록한다.
  - **대조 순서**: **M0 프로브 C와 같은 씬을 먼저** 발화해 파이프라인이 살아 있음을 확립한 뒤 라이브러리 씬을 발화한다 — 그래야 부정 관측이 "파이프라인 결함"이 아니라 "저작 결함"으로 귀속된다(FXLIB M0의 오귀속 교훈).
  - **트래킹 재확인 — 반복하지 않는다 (개정으로 삭제된 항목)**: 개정 전에는 "M0 프로브 D가 INCONCLUSIVE면 M8에서 A/B를 게이트 경유로 1회 반복"이 선택 항목이었다. **D는 실제로 INCONCLUSIVE였으나 반복하지 않는다** — `/CueOnly`를 쓰지 않으므로 반복할 A군이 존재하지 않고, 균일화의 효과는 §C.1상 **어떤 라이브 세션으로도 관측되지 않는다**(관측 주체 부재). 라이브에서 확인할 수 있는 것은 **균일 집합이 실린 값 라인이 실제로 발화되고 큐가 생성된다**는 것까지이며, 그것은 이미 다른 항목이 덮는다. **"라이브로 한 번 더 보면 알 수 있을 것"이라는 기대 자체가 검증 천장을 오해한 것이다.**
  - **미주장 열거의 실물 대조(신규)**: 리포트가 낸 미주장 목록이 **실제로 그 씬이 발화하지 않은 속성과 일치하는지**를 발화 커맨드 원문과 대조한다. 이것은 정적 계산의 확인이지 **이월의 확인이 아니다** — 후자는 관측 불가다.
- **baseline**: 착수 직전 전체 테스트 그린 확인.
- **뮤테이션**: ① 감사 로그 대조 없이 툴 반환만으로 인수하면 AC-SCENE-021이 죽어야 한다. ② M0 판정(41/44)을 M8에서 덮어쓰면 죽어야 한다. ③ 큐 재조회 확인을 효과 확인으로 기록하면 죽어야 한다. ④ 대조 발화 없이 부정 관측을 저작 결함으로 귀속하면 죽어야 한다.
- **파일**: 코드 변경 0(결함 발견 시 별도 커밋). 기록은 progress.md.
- **AC**: AC-SCENE-021.

### 라이브 세션 회계 (결정 A·B의 비용 — **2/2 소진, 0회 잔여**)

| | 세션 | AC | 측정 대상 | 왜 병합 불가인가 |
|---|---|---|---|---|
| 1 | **M0 프로브** — **완료 2026-08-01** | AC-SCENE-019 | ASSUMPTION-41/42/43/44/45 (게이트 미경유, 감사 로그 없음) | **M4 저작 전**에 답이 필요했다 (41·44가 번들 형상을 막았다). **41이 실제로 막았고 정책이 바뀌었다** |
| 2 | **M8 종단** — **완료 2026-08-01** | AC-SCENE-021 | 매칭→결합→게이트→감사 로그→재조회→GUI 종단 통합 | **M7 완료 후**에만 존재한다 |

**라이브 세션 수 = 2.** LOOKLIB·FXLIB·PRECHK의 2회 회계 선례를 그대로 따른다. 42·45는 3회차를 만들지 않는다 — 저작을 막지 않으므로 M0에 배칭한다.

## §C. 기술 제약

1. **신규 런타임 의존성 0.** stdlib + PyYAML(기존 의존) + 기존 스택만.
2. **@MX:ANCHOR 경계 (위반 불가)**: `gate.screen()` 단일 스크리닝 경로, dedupe 판정 루프(`tools.py:688-712`), `_PROGRAMMER_STATE_COMMANDS`(`:327-331`), fx의 `MIN_STEPS`(`schema.py:66`) — 전부 소비만.
3. **stop-on-first-failure**: 실패 이후 `not_executed` — 리포트가 반드시 전파(REQ-SCENE-014).
4. **번들 규모**: 기준선 87줄/5.77s, ~66ms/줄(66.3-66.7ms — SPEC-COPILOT-BUSKWIZ-001/progress.md:278-281 전재). 씬 번들은 **~14-22줄** — 여유 큼.
5. **`Delete` 블랙리스트**: 프로브·테스트가 만든 콘솔 오브젝트는 툴 경로로 지울 수 없다. 정리는 사용자 GUI 조작이며 그 사실을 기록한다.
6. **줄 앵커 드리프트**: 본 계획의 모든 file:line은 plan-phase 실측 시점(2026-08-01, `main` = `e4bc78e`) 값이다. **각 마일스톤 착수 직전 재실측**한다.

## §D. @MX 태그 대상 (Phase 14 — 예상, 실제 배치는 run-phase 확정)

| 위치 | 태그 | 사유 |
|---|---|---|
| `server/orchestrator/tools.py` `compile_scene` 핸들러 | **@MX:ANCHOR** | 씬 체인의 **유일한 모델 도달 입구**이며 `run_commands`의 **caller**다 — 제2 실행 표면을 만들면 게이트에 보이지 않는다. `instantiate_look`(`:848-858`) · `prepare_songcue`(`:1116`) · `instantiate_fx`(`:1688-1698`)의 형상을 계승 |
| `server/scene/compile.py` 결합 순서 | **@MX:ANCHOR** | **룩은 첫 `Step 2`보다 앞에 있어야 한다** — 스텝 1이 현재 프로그래머 상태이기 때문이다(design.md §3.2). 순서가 뒤집히면 룩이 페이저 종점이 되고, **런타임은 아무 신호도 내지 않는다** |
| `server/scene/compile.py` Store 라인 | **@MX:WARN** + **@MX:REASON** | **플래그를 붙이지 않는다.** 콘솔은 **미지 store 플래그를 조용히 접수한다**(M0 실측 — `/CueOnlyy`가 `ok`+저장). 즉 오타 플래그는 `ok`로도 재조회로도 잡히지 않으므로, 플래그 축을 여는 순간 **런타임 신호가 0인 결함 표면**이 생긴다 |
| `server/scene/compile.py` 균일 집합 정렬·강제 | **@MX:ANCHOR** | 트래킹 정책의 **유일한 기계 집행 지점**이다. 정렬을 빼면 오늘 자산에서는 **아무 일도 일어나지 않고**(32/32가 이미 정렬돼 있다) 미래 저작에서 조용히 깨진다 — 자산이 우연히 보장을 대신하고 있다는 사실이 이 앵커의 이유다 |
| `server/scene/compile.py` 미주장 열거 | **@MX:NOTE** | 닫지 못한 축(특히 **Pan/Tilt** — 룩이 구조적으로 가질 수 없고 fx 12개 중 8개가 전용)을 은폐하지 않고 노출하는 지점. 열거를 빼면 "구조적 회피" 서술이 **과잉 주장**이 된다 |
| `server/scene/compile.py` 가드 | **@MX:WARN** + **@MX:REASON** | dedupe 탈락 → 불완전 Store의 무음 실패. 씬 번들은 룩+fx 값 라인을 함께 담아 **fx보다 충돌 표면이 넓다**. 1차는 raise(잔여 없음), 2차는 지시 턴 경계 |
| `server/scene/compile.py` 상류 import 블록 | **@MX:WARN** + **@MX:REASON** | 비공개 함수 결합. 재구현하면 두 벌이 갈라지고 **갈라짐은 무음**이다(design.md §2.2). 형상 고정 테스트가 이 결합의 안전벨트다 |
| `server/scene/report.py` 주장 분리 상수 | **@MX:ANCHOR** | 산출물·**균일성**·효과·트래킹은 **다른 주장**이다. 뭉치면 사용자가 정적 확인을 효과·트래킹 증거로 오독한다 — 정책이 `/CueOnly`에서 균일 집합으로 바뀌어도 **이 오독 경로는 그대로다** |

**면제 집합 사본이 없으므로 그에 딸린 @MX:ANCHOR 동치 의무도 없다**(결정 E) — fx가 `instantiate.py:113-129`에 진 의무를 씬은 상속하지 않는다.

## §E. 테스트 스캐폴딩 계획

| 파일 | 대상 | 콘솔 접촉 |
|---|---|---|
| `server/tests/test_scene_schema.py` | 스키마·로더 (M1) | 무접촉 |
| `server/tests/test_scene_library.py` | 라이브러리 전수 + 상류 참조 해석 (M2) | 무접촉 |
| `server/tests/test_scene_matching.py` | 2축 매칭 (M3) | 무접촉 |
| `server/tests/test_scene_compile.py` | 결합·가드·번호·트리거 (M4) | 무접촉 (문자열 수준 assert) |
| `server/tests/test_scene_report.py` | 리포트 주장 분리 상수 동일성 + 미주장 열거 문면 (M5) | 무접촉 |
| `server/tests/test_scene_tool.py` | 툴 계약 (M6) | 무접촉 (fake rig/fake runner) |
| `server/tests/test_scene_boundary.py` | 경계 AST 스캔 · LiveLock · 상류 형상 고정 (M7) | 무접촉 |

전부 순수 함수 우선 + 인메모리 리그 — 라이브 접촉은 M0/M8 두 세션뿐.

## §F. 병렬 가능성 분석 + 결정 기록

### §F.1 의존 사슬

```
M0 → M1 → {M2, M3, M4} → M5 → M6 → M7 → M8
           └── 병렬 창 ──┘
```

- **M0 → M1**: ASSUMPTION-41/44 판정이 M4 형상을 막으므로 M0가 선행한다. M1(스키마)은 엄밀히는 M0와 무관하지만, 41 부정 시 SPEC 자체가 중단되므로 M0 뒤에 둔다(헛수고 방지).
- **M1 → {M2, M3, M4}**: 세 슬라이스 모두 스키마 타입을 소비한다. M1이 닫히기 전에는 병렬 착수 불가.
- **{M2, M3, M4} → M5**: 리포트는 M4의 컴파일 결과 데이터클래스를 소비하므로 **병렬 불가**.
- **M5 → M6**: 툴 핸들러가 M3(매칭)·M4(컴파일)·M5(리포트) 산출물을 배선하므로 **병렬 불가**.
- **M6 → M7 → M8**: 검증 마일스톤 순차.

### §F.2 병렬 슬라이스 파일 명세 — 교집합 실증

| 슬라이스 | 생성/수정 파일 | 읽기 전용 참조 |
|---|---|---|
| **A (M2)** | `server/scene/library/*.yaml`<br>`server/tests/test_scene_library.py` | `server/scene/schema.py`(M1)<br>`server/looks/library/**`, `server/fx/library/**` |
| **B (M3)** | `server/scene/matching.py`<br>`server/tests/test_scene_matching.py` | `server/scene/schema.py`(M1)<br>`server/looks/matching.py`, `server/fx/matching.py` |
| **C (M4)** | `server/scene/compile.py`<br>`server/tests/test_scene_compile.py` | `server/scene/schema.py`(M1)<br>`server/looks/instantiate.py`, `server/fx/instantiate.py` |

**교집합 = ∅.** 세 슬라이스의 쓰기 대상 집합은 다음과 같고, 어느 두 집합의 교집합도 비어 있다:

```
A = { server/scene/library/*.yaml, server/tests/test_scene_library.py }
B = { server/scene/matching.py,    server/tests/test_scene_matching.py }
C = { server/scene/compile.py,     server/tests/test_scene_compile.py }

A ∩ B = ∅    A ∩ C = ∅    B ∩ C = ∅
```

읽기 전용 참조는 겹치지만(세 슬라이스 모두 `schema.py`를 읽는다) **쓰기가 겹치지 않으므로 write-충돌이 없다.** `schema.py`는 M1에서 이미 닫힌 상태로 병렬 창에 들어간다 — 병렬 중에 수정되지 않는다.

**검증 명령** (병렬 착수 직전 오케스트레이터가 실행):
```bash
git status --porcelain server/scene/ server/tests/   # 착수 전 클린 확인
# 각 슬라이스 완료 후:
git diff --name-only <BASE>..HEAD -- server/scene/ server/tests/
# 세 슬라이스의 출력 집합이 서로소인지 대조
```

### §F.3 공유 계약 — 세 브리프에 **동일 문면**으로 주입할 것

**이것이 §F에서 가장 중요한 항목이다.** 파일이 겹치지 않는다고 안전한 것이 아니다 — FXLIB이 같은 함정을 기록했다(`plan.md:186`): *"M2와 M4는 파일이 겹치지 않지만 **스텝 축 형상이라는 공유 계약**을 갖는다 … 두 작업자가 각자 형상을 해석하면 … **그 불일치는 런타임에서 아무 신호도 내지 않는다**."*

씬의 공유 계약은 **셋**이고(SC-3은 D1 개정으로 신설됐다), 셋 다 `design.md`가 소유한다:

| # | 공유 계약 | 정본 | 누가 소비하나 | 어긋나면 |
|---|---|---|---|---|
| **SC-1** | **결합 순서 규칙 (D2)** — 골격, 룩 먼저의 강제 근거, 충돌 시 이펙트 우선 + 전수 열거 | **design.md §3** (§3.1 골격 · §3.2 근거 · §3.3 충돌 · §3.4 규율) | **A(M2)**: 엔트리의 룩·이펙트 조합이 이 순서로 컴파일될 것을 전제로 저작<br>**C(M4)**: 이 순서로 조립 | A가 "룩이 이길 것"으로 저작하고 C가 이펙트 우선으로 조립하면 **라이브러리 의도와 산출이 어긋난다**. 테스트는 각자 통과하고 **런타임은 침묵한다** |
| **SC-2** | **가드 정책 (1차 raise / 2차 재사용 / 면제 사본 0)** | **design.md §4** (§4.1 1차 · §4.2 2차 · §4.3 운용 경계) | **A(M2)**: 값 라인이 번들 내에서 중복되지 않는 엔트리를 저작<br>**C(M4)**: 가드 구현 | A가 룩·이펙트가 같은 attribute·같은 값을 내는 엔트리를 저작하면 C의 1차 가드가 **컴파일 자체를 거부**한다. A가 그 규칙을 모르면 "왜 내 씬만 안 되지"가 된다 |
| **SC-3** | **트래킹 정책 (균일 집합 + 미주장 열거)** — 개정 신설 | **design.md §6** (§6.1 세 조각 · §6.2 관측 천장 · §6.3 단언 위치) | **A(M2)**: **미선언 `Zoom`/`Iris`가 채워지지 않는다**는 전제로 엔트리를 고르고, movement 씬의 충돌 열거가 항상 ∅임을 안다<br>**C(M4)**: 정렬·강제·차집합 계산 구현 | A가 "씬 컴파일러가 `Zoom`을 알아서 채워 주겠지"로 저작하면 산출이 저작 의도와 다르고, **테스트는 각자 통과하며 런타임은 침묵한다**. 그리고 A가 충돌 씬을 movement fx로 저작하면 C의 충돌 열거 뮤테이션이 **통과해 버린다**(§3.3 각주) |

**주입 방법**: 병렬 브리프의 "공유 계약" 절에 `design.md §3` · `§4` · **`§6`** 전문을 **요약 없이 그대로** 붙인다. 요약본을 만들면 요약이 세 번째 해석이 된다.

**§F.2의 쓰기 집합은 개정으로 바뀌지 않는다** — SC-3은 파일이 아니라 **계약**을 추가한다. A·C의 생성/수정 파일 목록은 그대로이므로 교집합 ∅ 증명이 유지되고, 병렬 창의 성립 조건은 변하지 않는다. 바뀐 것은 **주입해야 할 정본 절이 2개(§3·§4)에서 3개(§3·§4·§6)로 늘었다**는 점뿐이다.

**B(M3)는 공유 계약을 갖지 않는다** — 매칭은 씬 id를 고르는 일이고 번들 형상과 무관하다. B는 SC-1/SC-2/SC-3 없이 착수해도 안전하다.

### §F.4 병렬 웨이브 HARD 불변식 (공통 브리프 — 7항)

`.moai/reports/handoff/TEMPLATE-병렬웨이브-파이프라인.md:76-81`의 **템플릿 6항**을 본 SPEC 문맥으로 이행하고, 여기에 **본 SPEC이 개정에서 신설한 7항(뮤테이션 재료 규율)** 을 더해 **총 7항**이 된다. **전부 충족 가능하다**:

1. **전송 표면 무접촉** — `server/scene/`는 `server.bridge`·`pythonosc`·`gate`·`execution_port`를 import하지 않는다. → REQ-SCENE-019 · AC-SCENE-017 · M7 AST 스캔.
2. **PRESERVE 경계** — `server/looks/**` · `server/fx/**` · `console/lua/**` · `server/rulebook/assets/**` · `server/safety/**` · `tools.py`의 dedupe 축. 읽기 import만. → §A.5 + `git diff --stat` 게이트.
3. **`/Overwrite` 금지** — 대소문자 무관 부재 단언. → AC-SCENE-010. **본 SPEC은 `/Merge`까지 확장한다**(D3).
4. **`Cmd()` OK ≠ 효과 증거** — 재조회로 확인 가능한 것은 큐의 **존재**뿐이고, 효과·트래킹은 기계 증거 불가다. **M0가 여기에 한 층을 더했다: 미지 store 플래그에 대해서는 `ok`도 재조회도 비변별이다.** → REQ-SCENE-014 주장 분리 · AC-SCENE-015 · REQ-SCENE-013 (e).
5. **값 라인 dedupe는 지시 턴 전체 경계** — 면제 3종뿐, 중복은 조용히 접히고 Store만 실행된다. → REQ-SCENE-015 (a)(b) · AC-SCENE-011.
6. **TDD** — 실패 테스트 먼저. 마일스톤별 뮤테이션 항목을 소진하고 killed를 기록한다. **survived = 마일스톤 미완료.** → §B 각 마일스톤 뮤테이션 목록(**M4는 20항**).
7. **뮤테이션 재료 규율(개정 신설)** — 충돌 열거 비공허성은 **dimmer/color fx로만**, 균일 집합 순서 뮤테이션은 **픽스처 주입 필수**(자산 32/32가 이미 정렬돼 있어 자산만으로는 살아남는다). → design.md §3.3 각주 · acceptance.md §E.

### §F.5 병렬 채택 여부 — 권고

**M2/M3/M4 병렬은 가능하지만 필수가 아니다.** 채택 조건:

- **채택**: M1이 닫혔고, **SC-1/SC-2/SC-3**을 `design.md` 전문 인용으로 주입할 수 있으며, 세 슬라이스의 쓰기 집합 서로소가 §F.2 명령으로 확인됐을 때.
- **미채택(순차)**: 위 조건 중 하나라도 불확실하면 **M2 → M3 → M4 순차**가 기본이다. 코딩 중심 작업의 순차 기본 원칙이며, M4가 세 슬라이스 중 압도적으로 크므로(**AC 8건, 뮤테이션 20항** — §B M4의 `- **AC**:` 줄과 뮤테이션 ①~⑳, §F.4-6과 동일 수치) 병렬 이득이 M4의 크기에 가려진다.

**결정 A~K**: §A.4 등록부가 정본. 전부 해소 — run-phase가 재질의할 결정은 없다. (D1은 2026-08-01 M0 실측 후 사용자 재확정으로 닫혔다.)
**DoD 요약**: acceptance.md §F가 정본.

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

- **입력**: tier L · 신규 패키지 1(`server/scene/`) + `tools.py` 소폭 · 도메인 1(서버 파이썬) · 파일 언어 단일(Python + YAML) · 코딩 중심 · 병렬 이득 = M2/M3/M4 구간 한정 · 예상 파일 수 ~14(소스 6 + 테스트 7 + tools.py).
- **권고**: **sub-agent (Mode 5) 기본**, M2/M3/M4 구간만 §F.5 조건 충족 시 선택적 병렬. 근거: 코딩 중심 작업은 Mode 5가 기본이고(Anthropic coding-task parallelism caveat), 파일 수 ~14는 Mode 6(≥~30 기계적 변환) 문턱에 미달하며, 도메인 1개는 Mode 4(≥3 도메인) 문턱에 미달한다.
- 확정과 기록(progress.md §F)은 오케스트레이터 몫이다.
