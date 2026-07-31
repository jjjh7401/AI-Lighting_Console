# SPEC-COPILOT-FXLIB-001 — 구현 계획 (plan)

> **v0.1.0 — 최초 작성.** 마일스톤 **M0~M7**, 결정 등록부 **8건(A~H) 전부 해소**, 열린 결정 **0건**, clarification 마커 **0건**. 정본 토큰 계약: REQ 21건 · AC 22건 · ASSUMPTION 4건(36~39) · 라이브 세션 2회. 마일스톤별 `- **AC**:` 줄은 `acceptance.md §C.0a`와 1:1이며, 합 **22 · 중복 0 · 누락 0**이다.

## §A. 접근 요약 (Context)

### §A.1 결정 검토 우선순위 (되돌리기 어려운 순 — 빌드 순서 아님)

리뷰는 아래 순서로 본다 — 가장 바꾸기 어려운 결정이 먼저다.

| 순위 | 결정 | 왜 먼저 보나 |
|---|---|---|
| 1 | **저장 형태 = 시퀀스+큐** (사용자 확정 ② — 결정 A) | 데이터 모델의 뿌리. 프리셋 축은 미측정이라 열지 않았고, 이 선택이 번들 형상·증거 채널·후속 씬 컴파일러 인터페이스를 전부 결정한다 |
| 2 | **fx-own 스키마 (looks 확장 기각)** (결정 B) | 신규 타입 인터페이스. `server/looks/schema.py`는 OVERLAP PRESERVE 잠금(spec.md:114-116 — 잠금 명단은 looks 6파일+`library/`)이라 확장이 애초에 불가하며, 읽기 import만 허용된다 — design.md §3 트레이드오프 |
| 3 | **패턴 폐쇄 집합 4+2 + 리포트 문면** (결정 D) | 사용자 대면 어휘·문구. ASSUMPTION-36/37 판정이 문면을 바꾼다 |
| 4 | **기계적 미러 구현** (로더/매칭/툴 배선) | LOOKLIB 선례를 따르는 기계 작업 — 마지막에 본다 |

### §A.2 빌드 순서 vs 차단 표 — 무엇이 무엇을 막는가

빌드 순서는 M0 → M1 → … → M7 선형이지만, **M0의 네 항목이 전부 뒤를 막는 것은 아니다**(LOOKLIB v0.3.0 교훈 — 과일반화 금지):

| 항목 | 막는 대상 | 성격 |
|---|---|---|
| ASSUMPTION-37 (다단 문법) | **M2 저작 + M1 다단 필드 사용 여부** | **진짜 순서 제약** — 유일하게 저작을 막는다 |
| ASSUMPTION-36 (효과 재조회) | M4 리포트 문면 + M7 증거 형상 | 문면·증거 채널 결정 — 저작은 막지 않음 |
| ASSUMPTION-38 (Speed 단위) | 없음 — 해석 기록 | 의도적 배칭 |
| ASSUMPTION-39 (MAtricks 재조회) | 없음 — 증거 채널 폭 기록 | 의도적 배칭 |

즉 다단 문법이 M0의 존재 이유이고, 나머지 셋은 같은 세션에 배칭된 측정이다. M0 접근 불가 시: ASSUMPTION-37만 보수 분기(다단 DESCOPE 가정)로 M1~M2를 진행할 수 있으나, 그 경우 GO 전환은 재프로브 없이 불가함을 progress.md에 기록한다.

### §A.3 정직한 축소 원칙 (계승)

부정 실측은 실패가 아니라 유효한 완료 상태다. 축소가 일어나면 (a) 무엇이 축소됐는지, (b) 어느 판정이 유발했는지, (c) 사용자 대면 문면에 어떻게 반영되는지를 progress.md에 기록한다. 부분 성공을 전체 성공으로 위장하지 않는다.

### §A.4 결정 등록부 — **해소 8건 / 미해결 0건** (재질의 금지)

| # | 결정 | 내용 · 근거 |
|---|---|---|
| **A** | 저장 형태 = 시퀀스+큐만 | 사용자 확정 ②. `Store Sequence <n> Cue 1 '<이름>'`(룰북 `:71` 검증 리터럴). 프리셋은 동적 값 수용 미측정 — 씬 컴파일러 후속 SPEC 몫 |
| **B** | fx-own 스키마 — looks MovementSpec 확장 기각 | `server/looks/schema.py` 등 looks 6파일 PRESERVE(OVERLAP spec.md:114-116) → 확장은 사용자 승인 없이는 불가하고, 승인을 구할 실익도 없다(트레이드오프: design.md §3). looks 상수(KNOWN_ATTRIBUTES 등)는 **읽기 import만** 허용 — `test_architecture.py`는 bridge import만 금지하므로 looks→fx 방향이 아닌 fx→looks 읽기 참조는 적법 |
| **C** | 시퀀스 번호 = 런타임 재조회 실측 | 하드코딩·발명 금지. `DataPool/Sequences` 재조회로 빈 번호 실측, `truncated` 참이면 거부(REQ-FXLIB-012). LOOKLIB 슬롯 탐색(사용자 확정 ⑤) 선례의 시퀀스판 |
| **D** | 패턴 폐쇄 집합 = 무조건 4종 + 게이트 2종 | `sweep`/`wave`/`circle`/`diagonal`(검증 리터럴 조합) + `pulse`/`chase`(ASSUMPTION-37 GO 시). 역방향은 파라미터. 시드는 무드→설계 표(`:236-241`) |
| **E** | 값 라인 충돌 = 형상 회피 + 구성 시점 가드 + 교차 호출 outcome 검출 | dedupe 규칙 개정은 기각 선례(BUSKWIZ). dedupe 경계는 **지시 턴 전체(instruction-scoped)** — v1은 1호출=1시퀀스=1큐로 **번들 내** 유일성을 구조 보장하고 가드(REQ-FXLIB-011 (a))가 위반을 생성 전에 잡으며, **교차 호출(같은 지시 턴의 앞선 호출) 충돌은 툴의 outcome 검사가 잡는다**(REQ-FXLIB-011 (b) — 비면제 `skipped_already_executed` 검출 시 성공 보고 금지). `VALUE_LINE_COLLISION`(busking.py:230) 사유 계승 |
| **F** | 라이브 세션 회계 = 2회 (M0·M7), 병합 불가 | 사용자 확정 ③. M0는 저작 전 전제 측정, M7은 통합 후 종단 — 시간축 양 끝이라 물리적으로 병합 불가(§B 말미 표) |
| **G** | 룰북 무변경 — 발견성은 툴 설명만 | 룰북 자산 PRESERVE의 귀결. LOOKLIB는 M5에서 룰북 안내 축을 추가했지만 본 SPEC은 그 선택지가 없다 — `find_fx`/`instantiate_fx`의 발견성은 툴 스키마 설명 문면이 전담한다(REQ-FXLIB-015) |
| **H** | Speed 값 = 수치 시드 + 해석 별도 기록 | 발화 문법(`At Speed <n>`)은 검증됐고 단위 해석만 미확정(`:70`). 라이브러리는 무드표 시드 수치를 담고, ASSUMPTION-38 판정을 리포트 문면·재보정에 반영 |

### §A.5 PRESERVE 목록 (무변경 대상)

| 대상 | 규율 |
|---|---|
| `server/looks/**` (schema/loader/roles/resolver/instantiate/matching/busking/report/songcue* + library/) | 수정 금지 — 읽기 import만. schema/loader/roles/resolver/instantiate/matching + library/는 OVERLAP PRESERVE(spec.md:114-116) 계승이고, busking/report/songcue*는 **본 SPEC이 추가 잠금**한다(OVERLAP 잠금 명단에는 없음) |
| `server/rulebook/assets/v2.4.2/**` | byte-diff 0 (REQ-FXLIB-020) |
| `console/lua/**` | 무변경 |
| `server/safety/**` (gate/classify/blacklist/lock/preview) | 무변경 — 스크리닝 의미론 소비만 (REQ-FXLIB-019) |
| `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`(:283-287)·dedupe 판정(:603-609) | 무변경 — 툴 2종 등록만 추가 |
| `server/bridge/**` | import 자체 금지 (REQ-FXLIB-017) |

## §B. 마일스톤 (M0..M7)

각 마일스톤은 착수 직전 baseline(전체 pytest)을 직접 실측한다 — plan-phase 수치를 이월하지 않는다. 줄 앵커는 착수 직전 재실측한다(드리프트 관례 — progress.md 인용 규율).

### M0 — 라이브 프로브 (cycle_type=none — 측정 세션, 코드 변경 0)

- **요구·설계 지시**: 실물 onPC 세션에서 ASSUMPTION-36/37/38/39를 판정한다. **각 축의 프로브 전에 날조 대조군 1발을 먼저 발화**한다(고의로 무효한 커맨드 — SONGCUE 선례: `ok`가 변별적임을 그 축에서 확립한 뒤에만 `ok`를 증거로 삼는다). **M0는 게이트 미경유(bridge 직결)이므로 감사 로그가 없다** — 증거는 콘솔 응답 원문 + GUI 관측(스크린샷)이며, 게이트 경유 종단 확인은 M7 몫이다.
  - **ASSUMPTION-36 (1순위)**: 페이저 빌드(`:68-71` 리터럴) → `Store Sequence <n> Cue 1` → `ClearAll` → 큐 발화 → GUI로 모션 관측(기능) + 저장 큐의 페이저 값 **재조회** 시도(증거 채널). 판정: **GO**(재조회가 페이저 값을 돌려줌) / **NEGATIVE**(모션은 확인되나 재조회 불가 → "기계 증거 불가 축" 명기, M7은 GUI 관측 강등) / **CONDITION_NOT_MET**(모션 자체가 저장되지 않음 → 저장 형태 재설계 필요, run-phase 중단 + 블로커 보고 — 조용히 진행 금지).
  - **ASSUMPTION-37**: `Step 2` / `At Accel -100` / `At Decel -100` 후보 리터럴 발화 + 효과 관측. 판정: **GO**(실측 리터럴 확정 → pulse/chase 진입) / **NEGATIVE**(→ `DESCOPE:` 접두 행 기록, REQ-FXLIB-001 게이트 발동).
  - **ASSUMPTION-38**: 알려진 수치(예: Speed 60)를 발화하고 GUI Speed 표시를 판독해 단위 해석을 기록.
  - **ASSUMPTION-39**: `DataPool/MAtricks` 재조회 시도. GO/NEGATIVE 어느 쪽도 v1 형상 불변 — 증거 채널 폭만 기록.
  - 판정 어휘는 PRECHK 계승: **GO / NEGATIVE / CONDITION_NOT_MET / REOPEN_SCOPE**, 기록 접두 행은 **`GO:` / `DESCOPE:` / `SKIP:` / `REOPEN:`** — 정본은 PRECHK **acceptance.md:289 + progress.md P1-2/P1-3**(감사 지적으로 신설)이며, PRECHK plan.md에는 `DESCOPE:`만 등장한다. 각 판정은 progress.md §E.2에 명시적 섹션으로 기록한다(각주 금지).
- **baseline**: 코드 baseline 없음. 세션 조건(콘솔 접근성·응답기 버전·OSC 포트·쇼파일 주요 개체 수)을 직접 기록. 조사 문서의 라이브 값을 이월하지 않는다.
- **뮤테이션**: ① 날조 대조군 없이 `ok`를 증거로 기록하면 AC-FXLIB-021이 죽어야 한다. ② 부정 판정에서 접두 행을 빼면 AC-FXLIB-021이 죽어야 한다. ③ ASSUMPTION-36을 GUI 관측 없이 재조회 실패만으로 CONDITION_NOT_MET 처리하면 AC-FXLIB-021이 죽어야 한다(기능과 증거 채널의 혼동).
- **파일**: 코드 변경 0. 기록은 progress.md §E.2.
- **AC**: AC-FXLIB-021.

### M1 — FX 스키마 + 로더 (cycle_type=tdd)

- **요구·설계 지시**: REQ-FXLIB-001/003/004/005. fx-own 스키마(결정 B — design.md §2 형상): 패턴 종별 폐쇄 어휘, 페이저 축, MAtricks 5축(선택), 다단 필드(**정의하되 M0 판정 전까지 라이브러리 사용 금지**), `schema_version`. 로더는 위반을 명시 에러로 — 미지 필드/패턴/attribute, 범위 이탈, 중복 fx id, 게이트 미충족 다단 사용. 전부 순수 함수, 콘솔 무접촉.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측 + M0 판정( `GO:`/`DESCOPE:` 행) 존재 확인.
- **뮤테이션**: ① 미지 패턴 종별을 통과시키면 AC-FXLIB-001이 죽어야 한다. ② per-show 필드(그룹/시퀀스/익스큐터 번호)를 스키마에 추가하면 AC-FXLIB-001이 죽어야 한다(미지 필드 거부 경로).
- **파일**: 신규 `server/fx/__init__.py`, `server/fx/schema.py`, `server/fx/loader.py`; 테스트 `server/tests/test_fx_schema.py`. (`server/fx/` 생성 시점부터 `test_architecture.py` 전역 스캔에 자동 포섭된다.)
- **AC**: AC-FXLIB-001.

### M2 — 내장 라이브러리 저작 (cycle_type=tdd)

- **요구·설계 지시**: REQ-FXLIB-002/003/004. 무조건 4종 패턴의 엔트리 저작(YAML — `server/fx/library/*.yaml`, looks library 선례), 한국어 무드 키워드 1급, 무드표 시드 값. ASSUMPTION-37 GO면 M0 실측 리터럴로 pulse/chase 추가, 부정이면 4종에서 멈추고 `DESCOPE:` 기록을 인용한다. 전수 검증 테스트: 패턴 폐쇄, 어휘 3구간, per-show 값 부재, 다단 필드 게이트 준수.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① 라이브러리에 `At Absolute`를 넣으면 AC-FXLIB-003이 죽어야 한다. ② 게이트 부정 상태에서 다단 필드에 값을 넣으면 AC-FXLIB-003이 죽어야 한다. ③ 구체 그룹 번호를 엔트리에 넣으면 AC-FXLIB-004가 죽어야 한다.
- **파일**: `server/fx/library/`(자산), `server/tests/test_fx_library.py`.
- **AC**: AC-FXLIB-002, AC-FXLIB-003, AC-FXLIB-004.

### M3 — 자연어 매칭 (cycle_type=tdd)

- **요구·설계 지시**: REQ-FXLIB-006/007/008. `server/looks/matching.py` 미러: 한국어 조사 처리, 폴백 3종, 동점 None, 결정론 정렬. 라이브러리 데이터 단일 진실원, 발명 금지, 무매칭 폴백 신호.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① 동점에서 첫 후보를 임의 반환하면 AC-FXLIB-005가 죽어야 한다. ② 무매칭에서 최저점 후보를 강제 반환하면 AC-FXLIB-007이 죽어야 한다.
- **파일**: `server/fx/matching.py`, `server/tests/test_fx_matching.py`.
- **AC**: AC-FXLIB-005, AC-FXLIB-006, AC-FXLIB-007.

### M4 — 인스턴스화 번들 빌더 + 충돌 가드 + 리포트 (cycle_type=tdd)

- **요구·설계 지시**: REQ-FXLIB-009~014. 번들 형상(design.md §4): 목적지 1회 → ClearAll → bare Group 선택 → 페이저 값 라인 → MAtricks(선언 시) → `Store Sequence <n> Cue 1 '<라벨>'` → Reset(사용 시) → ClearAll. 값 라인 충돌 가드(결정 E — (a) 비면제 라인 번들 내 유일성 assert, 위반 시 생성 거부; (b) **교차 호출 검출**: 실행 outcome의 비면제 `skipped_already_executed` 검출 시 성공 보고 금지 + 명시 실패 보고 — REQ-FXLIB-011 (b), design.md §5). 시퀀스 번호 재조회 실측(결정 C — truncated 참이면 거부). `/Overwrite` 대소문자 무관 부재 assert. 익스큐터는 명시 지정 시 1줄만. 한국어 2단 리포트: 요약 + 상세(not_executed **및 비면제 skipped_already_executed** 전파, **효과 증거 상태 문면은 ASSUMPTION-36 판정을 따른다**).
- **baseline**: 착수 직전 전체 server 테스트 직접 실측 + M0 ASSUMPTION-36 판정 확인.
- **뮤테이션**: ① 번들에 같은 값 라인을 2회 넣어도 통과하면 AC-FXLIB-009가 죽어야 한다. ② `Store /Overwrite`를 발화하면 AC-FXLIB-010이 죽어야 한다. ③ truncated=참에서 자동 배정하면 AC-FXLIB-010이 죽어야 한다. ④ 미지정 익스큐터에 Assign을 붙이면 AC-FXLIB-011이 죽어야 한다. ⑤ 리포트에서 not_executed를 빼고 성공 보고하면 AC-FXLIB-012가 죽어야 한다. ⑥ fake outcome에 비면제 라인 `skipped_already_executed`를 주입했는데도 성공 문면이 나오면 AC-FXLIB-009 (b)/AC-FXLIB-012가 죽어야 한다(교차 호출 시나리오).
- **파일**: `server/fx/instantiate.py`, `server/fx/report.py`, `server/tests/test_fx_instantiate.py`.
- **AC**: AC-FXLIB-008, AC-FXLIB-009, AC-FXLIB-010, AC-FXLIB-011, AC-FXLIB-012.

### M5 — 툴 표면 + 배선 (cycle_type=tdd)

- **요구·설계 지시**: REQ-FXLIB-015/016/021. `find_fx`·`instantiate_fx`를 기존 툴 레지스트리(`build_toolset`)에 등록. 대상 그룹 실존 검증(rig context 등재분만 — 발명 금지, `Fixture <slot>` 금지). 실행은 기존 `run_commands` 경로 소비만. 툴 스키마 설명이 발견성 전담(결정 G — 룰북 무변경). 제공자 중립 확인.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① rig context 미등재 그룹을 통과시키면 AC-FXLIB-014가 죽어야 한다. ② 툴이 게이트를 우회해 bridge를 직접 부르면 AC-FXLIB-014(및 test_architecture)가 죽어야 한다.
- **파일**: `server/orchestrator/tools.py`(툴 등록만), `server/tests/test_fx_tool.py`.
- **AC**: AC-FXLIB-013, AC-FXLIB-014, AC-FXLIB-019.

### M6 — 회귀 + 경계 전체 그린

- **요구·설계 지시**: pytest 전체 + vitest 전체 — 킥오프 기준선 대비 신규 실패 0건. `test_architecture.py` 그린 + `server/fx/**` 실행 경로 AST 식별자 스캔(offender 0건 — LOOKLIB AC-008 ③의 AST 방식 계승, raw grep은 독스트링 위양성으로 기각된 선례) + `server/safety/**`·룰북 byte-diff 0 + LiveLock 강등 + 안전 불변식 상속 확인. 전용 경계 테스트 `test_fx_boundary.py`가 여기 실린다.
- **baseline**: 착수 직전 전체 테스트 직접 실측.
- **뮤테이션**: ① `server/fx/`에 bridge import 1줄을 주입하면 AC-FXLIB-015가 죽어야 한다. ② 룰북 자산 1바이트를 바꾸면 AC-FXLIB-018이 죽어야 한다.
- **파일**: `server/tests/test_fx_boundary.py`; 수정 0(검증 마일스톤).
- **AC**: AC-FXLIB-015, AC-FXLIB-016, AC-FXLIB-017, AC-FXLIB-018, AC-FXLIB-020.

### M7 — 종단 라이브 검증 (실물 onPC)

- **요구·설계 지시**: 실물 콘솔에서 종단 1회: 채팅 지시("좌우로 부드럽게 쓸어줘" 류) → `find_fx` 매칭 → `instantiate_fx` → 실행 프리뷰 관측 → **게이트 감사 로그 확인**(M0가 못 한 몫) → 생성 시퀀스·큐 GUI 확인 → 효과 확인(**증거 채널은 M0 ASSUMPTION-36 판정을 따른다**: GO면 재조회 대조, NEGATIVE면 GUI 관측 + 리포트의 한계 문면 확인). M0에서 닫은 ASSUMPTION을 재측정하지 않는다 — 어긋남이 관측되면 그 불일치 자체를 기록한다.
- **baseline**: 착수 직전 전체 테스트 그린 확인.
- **뮤테이션**: ① 감사 로그 대조 없이 툴 반환만으로 인수하면 AC-FXLIB-022가 죽어야 한다. ② M0 판정을 M7에서 덮어쓰면 AC-FXLIB-022가 죽어야 한다.
- **파일**: 코드 변경 0(결함 발견 시 별도 커밋). 기록은 progress.md.
- **AC**: AC-FXLIB-022.

### 라이브 세션 회계 (결정 F)

| | 세션 | AC | 측정 대상 | 왜 병합 불가인가 |
|---|---|---|---|---|
| 1 | **M0 프로브** | AC-FXLIB-021 | ASSUMPTION-36~39 (게이트 미경유, 감사 로그 없음) | **M1~M2 저작 전**에 답이 필요하다 (ASSUMPTION-37) |
| 2 | **M7 종단** | AC-FXLIB-022 | 매칭→번들→게이트→감사 로그→GUI 종단 통합 | **M6 완료 후**에만 존재한다 |

**라이브 세션 수 = 2.** 사용자 확정 ③으로 표면화된 뒤 수용된 비용이다.

## §C. 기술 제약

1. **신규 런타임 의존성 0.** stdlib + PyYAML(기존 의존) + 기존 스택만.
2. **@MX:ANCHOR 경계 (위반 불가)**: `gate.screen()` 단일 스크리닝 경로, dedupe 판정 루프(tools.py:603-609), `_PROGRAMMER_STATE_COMMANDS`(:283-287) — 전부 소비만.
3. **stop-on-first-failure**: 실패 이후 `not_executed` — 리포트가 반드시 전파(REQ-FXLIB-014 (b)).
4. **번들 규모**: 기준선 87줄/5.77s, ~66ms/줄(66.3-66.7ms — BUSKWIZ progress.md:278-281 전재). v1 FX 번들은 ~10-15줄 — 여유 큼.
5. **줄 앵커 드리프트**: 본 계획의 모든 file:line은 plan-phase 실측 시점 값이다. **각 마일스톤 착수 직전 재실측**한다(scout 인용 대비 이미 2건 드리프트 정정: matricks 경로 :126→:125, dedupe 블록 :227-237→:241-293/:603-609).

## §D. @MX 태그 대상 (예상 — 실제 배치는 run-phase 확정)

- `server/fx/schema.py` 모듈 헤더: `@MX:NOTE` — 폐쇄 필드 집합이 REQ-FXLIB-004(per-show 값 부재)의 강제 기제라는 사실(looks schema.py 선례).
- `server/fx/instantiate.py` 충돌 가드: `@MX:WARN` + `@MX:REASON` — dedupe 탈락 → 빈 프로그래머 Store의 무음 실패 경로.

## §E. 테스트 스캐폴딩 계획

| 파일 | 대상 | 콘솔 접촉 |
|---|---|---|
| `server/tests/test_fx_schema.py` | 스키마·로더 (M1) | 무접촉 |
| `server/tests/test_fx_library.py` | 라이브러리 전수 (M2) | 무접촉 |
| `server/tests/test_fx_matching.py` | 매칭 (M3) | 무접촉 |
| `server/tests/test_fx_instantiate.py` | 번들·가드·리포트 (M4) | 무접촉 (문자열 수준 assert) |
| `server/tests/test_fx_tool.py` | 툴 계약 (M5) | 무접촉 (fake rig/fake runner) |
| `server/tests/test_fx_boundary.py` | 경계 AST 스캔 (M6) | 무접촉 |

전부 순수 함수 우선 + 인메모리 리그 — 라이브 접촉은 M0/M7 두 세션뿐.

## §F. 병렬 가능성 분석 + 결정 기록

- **의존 사슬**: M0 → M1 → {M2, M3, M4} → M5 → M6 → M7. **M2(라이브러리 YAML 저작) · M3(matching.py) · M4(instantiate.py/report.py)는 파일이 서로 겹치지 않아 M1 완료 후 병렬 가능**하다(PRECHK "병렬 웨이브 1"(M2+M3+M4) 선례). 단 M4의 리포트 문면은 M0 ASSUMPTION-36 판정을 입력으로 요구한다(§A.2). M5는 M3+M4 산출물을 배선하므로 병렬 불가. 오케스트레이터가 Mode 4 병렬을 택할 경우 write-충돌 없음을 이 표로 확인한다.
- **결정 A~H**: §A.4 등록부가 정본. 전부 해소 — run-phase가 재질의할 결정은 없다.
- **DoD 요약**: acceptance.md §F가 정본.

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

- 입력: tier L · 신규 패키지 1 + tools.py 소폭 · 도메인 1(서버 파이썬) · 코딩 중심 · 병렬 이득 = M2/M3/M4 구간 한정.
- 권고: **sub-agent (Mode 5) 기본 + M2/M3/M4 구간만 선택적 병렬** — 코딩 중심 작업의 순차 기본 원칙. 확정과 기록(progress.md §F)은 오케스트레이터 몫.
