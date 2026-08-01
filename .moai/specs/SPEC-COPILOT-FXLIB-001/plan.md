# SPEC-COPILOT-FXLIB-001 — 구현 계획 (plan)

> **v0.2.0 — M0 라이브 프로브 폴드인.** 마일스톤 **M0~M7**(M0 **실행 완료** — 판정 정본 progress.md §E.2), 결정 등록부 **9건(A~I) 전부 해소**, 열린 결정 **0건**, clarification 마커 **0건**. 정본 토큰 계약: REQ 22건 · AC 23건 · ASSUMPTION 5건(36~40) · 라이브 세션 2회. 마일스톤별 `- **AC**:` 줄은 `acceptance.md §C.0a`와 1:1이며, 합 **23 · 중복 0 · 누락 0**이다.
>
> **M0가 바꾼 것 한 줄**: 페이저는 2스텝 이상을 요구하므로 전 패턴이 `<값>` → `Step 2` → `<값>` **스텝 쌍**을 내야 하고(M1 스키마·M4 번들), 이펙트 효과는 **기계로 검증되지 않는다**(사람 GUI 관측이 유일 채널). 상세는 spec.md HISTORY v0.2.0 · design.md §2.1/§4/§5.

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

빌드 순서는 M0 → M1 → … → M7 선형이지만, **M0의 네 항목이 전부 뒤를 막는 것은 아니었다**(LOOKLIB v0.3.0 교훈 — 과일반화 금지). **M0는 2026-07-31 실행 완료**됐고, 아래 표에 판정을 덧붙인다:

| 항목 | 막는 대상 | 성격 | M0 판정 (2026-07-31) |
|---|---|---|---|
| ASSUMPTION-37 (다단 문법) | **M2 저작 + M1 다단 필드 사용 여부** | **진짜 순서 제약** — 유일하게 저작을 막았다 | **GO** — 스텝 문법 확립(`<값>`→`Step 2`→`<값>`). `pulse`/`chase` 진입. `Accel`/`Decel`만 **SKIP**(효과 미관측) |
| ASSUMPTION-36 (효과 재조회) | M4 리포트 문면 + M7 증거 형상 | 문면·증거 채널 결정 — 저작은 막지 않음 | **GO**(기능) / **부정**(증거 채널) — 리포트 문면 무조건 강화 + M7 GUI 관측 강등 |
| ASSUMPTION-38 (Speed 단위) | 없음 — 해석 기록 | 의도적 배칭 | **GO** — **BPM** |
| ASSUMPTION-39 (MAtricks 재조회) | 없음 — 증거 채널 폭 기록 | 의도적 배칭 | **GO** — `childCount 1`, `truncated:false` |
| **ASSUMPTION-40** (스텝 형상의 Pan/Tilt 일반화 + `Relative`의 스텝 값 성립) — **M0가 새로 연 항목** | **없음 — v1 저작을 막지 않는다** | **M7 측정.** 신규 항목이므로 M0 판정의 재측정이 아니다(AC-FXLIB-021 덮어쓰기 금지와 무충돌) | 미측정 |

즉 다단 문법이 M0의 존재 이유였고 그것은 **GO로 닫혔다.** 남은 미확정은 ASSUMPTION-40 하나이며, 그 **게이트는 형상에 있다**: v1 라이브러리가 스텝 값을 절대 수치로만 저작하고 `At Relative`를 발화하지 않으므로(결정 I), 부정 실측의 비용은 **Pan/Tilt 패턴 4종(`sweep`/`wave`/`circle`/`diagonal`)의 효과**에 한정되고 스키마·로더·매칭·툴·리포트는 무영향이다 — `pulse`가 `[실측]` 앵커로 남아 파이프라인 전체의 종단 성립을 증명할 수 있다.

### §A.3 정직한 축소 원칙 (계승)

부정 실측은 실패가 아니라 유효한 완료 상태다. 축소가 일어나면 (a) 무엇이 축소됐는지, (b) 어느 판정이 유발했는지, (c) 사용자 대면 문면에 어떻게 반영되는지를 progress.md에 기록한다. 부분 성공을 전체 성공으로 위장하지 않는다.

### §A.4 결정 등록부 — **해소 9건 / 미해결 0건** (재질의 금지)

| # | 결정 | 내용 · 근거 |
|---|---|---|
| **A** | 저장 형태 = 시퀀스+큐만 | 사용자 확정 ②. `Store Sequence <n> Cue 1 '<이름>'`(룰북 `:71` 검증 리터럴). 프리셋은 동적 값 수용 미측정 — 씬 컴파일러 후속 SPEC 몫 |
| **B** | fx-own 스키마 — looks MovementSpec 확장 기각 | `server/looks/schema.py` 등 looks 6파일 PRESERVE(OVERLAP spec.md:114-116) → 확장은 사용자 승인 없이는 불가하고, 승인을 구할 실익도 없다(트레이드오프: design.md §3). looks 상수(KNOWN_ATTRIBUTES 등)는 **읽기 import만** 허용 — `test_architecture.py`는 bridge import만 금지하므로 looks→fx 방향이 아닌 fx→looks 읽기 참조는 적법 |
| **C** | 시퀀스 번호 = 런타임 재조회 실측 | 하드코딩·발명 금지. `DataPool/Sequences` 재조회로 빈 번호 실측, `truncated` 참이면 거부(REQ-FXLIB-012). LOOKLIB 슬롯 탐색(사용자 확정 ⑤) 선례의 시퀀스판 |
| **D** | 패턴 폐쇄 집합 = 무조건 4종 + 게이트 2종 | `sweep`/`wave`/`circle`/`diagonal`(검증 리터럴 조합) + `pulse`/`chase`(ASSUMPTION-37 GO 시). 역방향은 파라미터. 시드는 무드→설계 표(`:236-241`) |
| **E** | 값 라인 충돌 = 형상 회피 + 구성 시점 가드 + 교차 호출 outcome 검출 | dedupe 규칙 개정은 기각 선례(BUSKWIZ). dedupe 경계는 **지시 턴 전체(instruction-scoped)** — 가드(REQ-FXLIB-011 (a))가 번들 내 위반을 생성 전에 잡고, **교차 호출 충돌은 툴의 outcome 검사가 잡는다**(REQ-FXLIB-011 (b) — 비면제 `skipped_already_executed` 검출 시 성공 보고 금지). `VALUE_LINE_COLLISION`(busking.py:230) 사유 계승. **M0 갱신(v0.2.0)**: v0.1.0이 근거로 삼았던 *"1호출=1시퀀스=1큐라 번들 내 유일성이 구조 보장된다"*는 **철회한다** — 스텝 축으로 한 패턴이 같은 attribute에 값 라인을 여러 줄 내므로 유일성은 **저작 제약**이 됐고, `Step 2` 라인이 전 패턴 공통이라 교차 호출 충돌이 **다른 패턴 사이에서도** 성립한다. 두 검사는 방어적 항목에서 **상시 발화 가능한 1급 검사**로 승격됐고, v1은 **지시 턴당 인스턴스화 1회**를 운용 경계로 명시한다(design.md §5) |
| **F** | 라이브 세션 회계 = 2회 (M0·M7), 병합 불가 | 사용자 확정 ③. M0는 저작 전 전제 측정, M7은 통합 후 종단 — 시간축 양 끝이라 물리적으로 병합 불가(§B 말미 표) |
| **G** | 룰북 무변경 — 발견성은 툴 설명만 | 룰북 자산 PRESERVE의 귀결. LOOKLIB는 M5에서 룰북 안내 축을 추가했지만 본 SPEC은 그 선택지가 없다 — `find_fx`/`instantiate_fx`의 발견성은 툴 스키마 설명 문면이 전담한다(REQ-FXLIB-015) |
| **H** | Speed 값 = 수치 시드 + 해석 별도 기록 | 발화 문법(`At Speed <n>`)은 검증됐고 단위 해석만 미확정이었다(`:70`). **M0로 해소 — 단위는 BPM.** 라이브러리 시드 수치를 BPM 해석으로 재보정하고 리포트 문면도 BPM으로 적는다 |
| **I** | **스텝 축 필수 + `At Relative` 미발화 + Pan/Tilt 일반화는 M7 게이트** (M0 폴드인, v0.2.0 신설) | M0가 **강제한 것**과 **선택한 것**을 분리해 적는다. **강제**: 페이저는 2스텝 이상을 요구하고 `Relative`/`Phase`/`Speed`는 변형 커맨드이므로, 스텝 축 없이는 어떤 패턴도 페이저를 만들지 못한다 — 이건 결정이 아니라 측정이다. **선택 3건**: ① 스텝 축을 **선택 필드가 아니라 필수 필드**로 둔다(길이 < 2를 표현 불가능하게 — 무음 실패가 유일한 대안 결과이므로 로더에서 죽이는 편이 낫다), ② 진폭을 **스텝 값의 차이**로 표현하고 `At Relative`는 **발화하지 않는다**(스텝 값으로서의 성립이 미측정 — 미검증 형태를 기본 경로에 넣지 않는다는 REQ-FXLIB-003 규율의 적용), ③ Pan/Tilt 일반화를 **새 프로브로 막지 않고 ASSUMPTION-40으로 열어 M7에 배치**한다(형상 게이트가 부정 비용을 Pan/Tilt 패턴 4종의 효과로 한정하므로 라이브 세션 3회차를 사는 것보다 싸다 — 사용자 확정 ③의 2회 회계 유지) |

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

### M0 — 라이브 프로브 (cycle_type=none — 측정 세션, 코드 변경 0) — **실행 완료 (2026-07-31)**

> **완료 기록**: 판정 정본 progress.md §E.2, 원문 전량 `.moai/reports/m0-probe/raw-log-01.md` §10(§7은 SUPERSEDED, §0·§10.0은 자기 정정 2건). 판정 — 36 **GO**(기능) / 증거 채널 **부정** · 37 **GO** · 38 **GO**(BPM) · 39 **GO** · `Accel`/`Decel` **SKIP**. 쇼파일 복구 확인(프로브 생성 오브젝트 잔여 0건). 아래 절차 문면은 **실행 계약의 기록**으로 보존한다.

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

- **요구·설계 지시**: REQ-FXLIB-001/003/004/005. fx-own 스키마(결정 B — **형상 계약의 정본은 design.md §2.1**): 패턴 종별 폐쇄 어휘, **스텝 축 `steps`(필수 — 아래)**, 페이저 변형 축, MAtricks 5축(선택), `accel`/`decel`(**정의하되 v1 라이브러리 사용 금지** — M0 SKIP), `schema_version`.
  - **스텝 축 (M0 귀결 — 이 마일스톤의 핵심 변경)**: `steps`는 **길이 ≥ 2의 순서 있는 열**이고 각 원소는 **attribute → 값** 매핑이다. 인덱스 `i`가 콘솔 스텝 번호 `i+1`에 대응하며 첫 원소는 현재 스텝(`Step 1` 미발화)이다. 값은 **절대 수치만** — `At Relative`는 스텝 값으로서 미측정이므로(ASSUMPTION-40) 스키마가 그 형태를 스텝 값으로 받지 않는다(결정 I). 페이저 변형 축(`phase_from`/`phase_to`/`speed`/`relative`/`reverse`/MAtricks)은 필드로 유지되되 **스텝 축이 만든 페이저 위에 얹히는 후행 라인**으로 의미가 재정의된다.
  - **로더 검증**: 미지 필드/패턴/attribute, 범위 이탈, 중복 fx id, 게이트 미충족 `accel`/`decel` 사용 — **그리고 스텝 축 4종**: ① `len(steps) < 2` 거부, ② 스텝 간 attribute 집합 불일치 거부, ③ **같은 attribute의 두 스텝이 같은 값이면 거부**(dedupe 접힘 → 무음 페이저 미성립), ④ `steps` 없이 변형 축만 선언 거부. 전부 순수 함수, 콘솔 무접촉.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측 + M0 판정 접두 행(progress.md §E.2 — `GO:` 4행 + `SKIP:` 1행) 존재 확인.
- **뮤테이션**: ① 미지 패턴 종별을 통과시키면 AC-FXLIB-001이 죽어야 한다. ② per-show 필드(그룹/시퀀스/익스큐터 번호)를 스키마에 추가하면 AC-FXLIB-001이 죽어야 한다(미지 필드 거부 경로). ③ `len(steps) >= 2` 검사를 지우면 죽어야 한다. ④ 스텝 값 동일성 검사(③번 검증)를 지우면 죽어야 한다 — **이 둘이 무음 실패의 유일한 자동 검출 지점이다**(효과는 기계로 확인되지 않는다).
- **파일**: 신규 `server/fx/__init__.py`, `server/fx/schema.py`, `server/fx/loader.py`; 테스트 `server/tests/test_fx_schema.py`. (`server/fx/` 생성 시점부터 `test_architecture.py` 전역 스캔에 자동 포섭된다.)
- **AC**: AC-FXLIB-001.

### M2 — 내장 라이브러리 저작 (cycle_type=tdd)

- **요구·설계 지시**: REQ-FXLIB-002/003/004. 무조건 4종 패턴의 엔트리 저작(YAML — `server/fx/library/*.yaml`, looks library 선례), 한국어 무드 키워드 1급, 무드표 시드 값(**BPM 해석으로 재보정** — ASSUMPTION-38 GO). **ASSUMPTION-37은 M0에서 GO로 닫혔으므로 `pulse`/`chase`를 포함해 6종을 저작한다** — `pulse`(Dimmer)는 M0가 직접 관측한 `[실측]` 앵커이므로 그 스텝 골격을 progress.md §E.2 형상 그대로 담는다. **전 엔트리가 `len(steps) >= 2`를 만족**해야 하며, 스텝 값은 절대 수치만 쓰고 `At Relative`·`accel`/`decel`은 값으로 넣지 않는다(결정 I · M0 SKIP). 전수 검증 테스트: 패턴 폐쇄, 어휘 3구간, per-show 값 부재, 스텝 축 준수, `accel`/`decel` 값 0건.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① 라이브러리에 `At Absolute`를 넣으면 AC-FXLIB-003이 죽어야 한다. ② `accel`/`decel`에 값을 넣으면 AC-FXLIB-003이 죽어야 한다(M0 SKIP — 효과 미관측 어휘의 무단 진입). ③ 구체 그룹 번호를 엔트리에 넣으면 AC-FXLIB-004가 죽어야 한다. ④ `steps` 길이 1인 엔트리를 넣으면 AC-FXLIB-002가 죽어야 한다.
- **파일**: `server/fx/library/`(자산), `server/tests/test_fx_library.py`.
- **AC**: AC-FXLIB-002, AC-FXLIB-003, AC-FXLIB-004.

### M3 — 자연어 매칭 (cycle_type=tdd)

- **요구·설계 지시**: REQ-FXLIB-006/007/008. `server/looks/matching.py` 미러: 한국어 조사 처리, 폴백 3종, 동점 None, 결정론 정렬. 라이브러리 데이터 단일 진실원, 발명 금지, 무매칭 폴백 신호.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측.
- **뮤테이션**: ① 동점에서 첫 후보를 임의 반환하면 AC-FXLIB-005가 죽어야 한다. ② 무매칭에서 최저점 후보를 강제 반환하면 AC-FXLIB-007이 죽어야 한다.
- **파일**: `server/fx/matching.py`, `server/tests/test_fx_matching.py`.
- **AC**: AC-FXLIB-005, AC-FXLIB-006, AC-FXLIB-007.

### M4 — 인스턴스화 번들 빌더 + 충돌 가드 + 리포트 (cycle_type=tdd)

- **요구·설계 지시**: REQ-FXLIB-009~014 + REQ-FXLIB-022. 번들 형상(**정본 design.md §4 — v0.2.0에서 전면 개정됨, v0.1.0 형상 인용 금지**): 목적지 1회 → ClearAll → bare Group 선택 → **스텝 열** → 페이저 변형 라인 → MAtricks(선언 시) → `Store Sequence <n> Cue 1 '<라벨>'` → Reset(사용 시) → ClearAll.
  - **스텝 열 (M0 귀결 — 이 마일스톤의 핵심 변경)**: 전 패턴이 `<값 라인>` → `Step 2` → `<값 라인>` **스텝 쌍**을 낸다. `Step 1`은 발화하지 않고(첫 스텝이 현재 스텝), 둘째 스텝부터 **단독 `Step <k>` 라인**을 그 스텝의 값 라인 **앞에** 놓는다. **변형 라인(`At Phase`/`At Speed`)은 스텝 열이 끝난 뒤에 온다** — 변형은 이미 존재하는 페이저에만 걸리며, 스텝 쌍 없이 변형 라인만 내면 `ok:true` 전량에 모션 0이다(M0 §3 실패 3회). 스텝 값 라인은 `;` 체이닝하지 않는다(design.md §4.3). **금지 형태 `Attribute '<attr>' At Step <k>` 0건**(REQ-FXLIB-022 — `ok:true`이나 효과 없음). `pulse` 번들은 progress.md §E.2의 `[실측]` 앵커와 문자열 수준에서 일치해야 한다.
  - 값 라인 충돌 가드(결정 E — (a) 비면제 라인 번들 내 유일성 assert, 위반 시 생성 거부; (b) **교차 호출 검출**: 실행 outcome의 비면제 `skipped_already_executed` 검출 시 성공 보고 금지 + 명시 실패 보고 — REQ-FXLIB-011 (b), design.md §5). **M0 이후 두 검사 모두 등급이 올랐다**: (a)는 스텝 값 중복이라는 현실적 결함을 잡는 상시 검사이고, (b)는 `Step 2` 공통 문자열 때문에 **서로 다른 패턴 사이에서도** 발화한다 — v1은 지시 턴당 인스턴스화 1회가 운용 경계다.
  - 시퀀스 번호 재조회 실측(결정 C — truncated 참이면 거부). `/Overwrite` 대소문자 무관 부재 assert. 익스큐터는 명시 지정 시 1줄만.
  - 한국어 2단 리포트: 요약 + 상세(not_executed **및 비면제 skipped_already_executed** 전파). **효과 증거 문면은 무조건이다** — 성공 경로를 포함한 모든 리포트가 "효과는 기계로 확인되지 않는다 — 사람이 무대/GUI에서 확인해야 한다"를 담는다(REQ-FXLIB-014 (c) — M0가 증거 채널 부정을 측정된 경계로 확정했으므로 ASSUMPTION-36 분기 문면은 폐기). Speed는 **BPM**으로 표기.
- **baseline**: 착수 직전 전체 server 테스트 직접 실측 + M0 판정 확인(progress.md §E.2 — 증거 채널 부정 + 스텝 형상).
- **뮤테이션**: ① 번들에 같은 값 라인을 2회 넣어도 통과하면 AC-FXLIB-009가 죽어야 한다(주입 형상은 **스텝 값 중복**이 1급). ② `Store /Overwrite`를 발화하면 AC-FXLIB-010이 죽어야 한다. ③ truncated=참에서 자동 배정하면 AC-FXLIB-010이 죽어야 한다. ④ 미지정 익스큐터에 Assign을 붙이면 AC-FXLIB-011이 죽어야 한다. ⑤ 리포트에서 not_executed를 빼고 성공 보고하면 AC-FXLIB-012가 죽어야 한다. ⑥ fake outcome에 비면제 라인 `skipped_already_executed`를 주입했는데도 성공 문면이 나오면 AC-FXLIB-009 (b)/AC-FXLIB-012가 죽어야 한다(교차 호출 — **같은 패턴 × 두 그룹**과 **다른 패턴 × 두 그룹** 양쪽). ⑦ `Step 2` 라인을 빼거나 변형 라인을 스텝 열 앞으로 옮기면 AC-FXLIB-008이 죽어야 한다(v0.1.0 형상 재도입 차단). ⑧ 빌더가 `Attribute 'Dimmer' At Step 2`를 내면 AC-FXLIB-023이 죽어야 한다. ⑨ 성공 경로 리포트에서 사람 확인 필요 문면을 빼면 AC-FXLIB-012가 죽어야 한다.
- **파일**: `server/fx/instantiate.py`, `server/fx/report.py`, `server/tests/test_fx_instantiate.py`.
- **AC**: AC-FXLIB-008, AC-FXLIB-009, AC-FXLIB-010, AC-FXLIB-011, AC-FXLIB-012, AC-FXLIB-023.

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

- **요구·설계 지시**: 실물 콘솔에서 종단 1회: 채팅 지시("좌우로 부드럽게 쓸어줘" 류) → `find_fx` 매칭 → `instantiate_fx` → 실행 프리뷰 관측 → **게이트 감사 로그 확인**(M0가 못 한 몫) → 생성 시퀀스·큐 GUI 확인 → **효과의 GUI 사람 관측**(증거 채널은 M0가 부정으로 확정 — 재조회 분기는 존재하지 않는다) + 리포트의 한계 문면이 실물과 일치하는지 확인. M0에서 닫은 ASSUMPTION(36~39)을 재측정하지 않는다 — 어긋남이 관측되면 그 불일치 자체를 기록한다.
  - **ASSUMPTION-40 판정 (M0가 열고 M7이 닫는다)**: 같은 세션에서 **Pan/Tilt 패턴 1종 이상**(`sweep` 또는 `wave`)을 발화해 스텝 생성 형상이 Dimmer 밖에서도 성립하는지 GUI로 관측하고, 접두 행 `GO:` / `NEGATIVE:`와 함께 progress.md에 기록한다. 신규 항목이므로 **재측정 금지 규율에 저촉되지 않는다**(§A.2 표). 대조 순서: **`pulse`(M0 앵커) 먼저** 발화해 파이프라인 자체가 살아 있음을 확립한 뒤 Pan/Tilt를 발화한다 — 그래야 부정 관측이 "파이프라인 결함"이 아니라 "attribute 일반화 실패"로 귀속된다(M0가 자기 프로브 결함을 콘솔 결함으로 오귀속한 사례의 교훈 — raw-log-01.md §0/§10.0).
  - **NEGATIVE 분기**: 비용을 Pan/Tilt 패턴 4종의 효과로 한정해 기록하고(스키마·툴 계층 무영향), `pulse` 종단 성립이 확인되면 **AC-FXLIB-022는 PASS**다 — 정직한 축소는 유효한 완료다(§A.3). 후속 조치(스텝 값 재저작 또는 후속 프로브)는 별도 SPEC/개정으로 넘기고 여기서 즉흥 재시도하지 않는다.
- **baseline**: 착수 직전 전체 테스트 그린 확인.
- **뮤테이션**: ① 감사 로그 대조 없이 툴 반환만으로 인수하면 AC-FXLIB-022가 죽어야 한다. ② M0 판정(36~39)을 M7에서 덮어쓰면 AC-FXLIB-022가 죽어야 한다. ③ ASSUMPTION-40을 접두 행 없이 산문으로만 기록하면 AC-FXLIB-022가 죽어야 한다. ④ Pan/Tilt 부정 관측을 `pulse` 대조 없이 기록하면 죽어야 한다(귀속 오류 방지).
- **파일**: 코드 변경 0(결함 발견 시 별도 커밋). 기록은 progress.md.
- **AC**: AC-FXLIB-022.

### 라이브 세션 회계 (결정 F)

| | 세션 | AC | 측정 대상 | 왜 병합 불가인가 |
|---|---|---|---|---|
| 1 | **M0 프로브** — **완료(2026-07-31)** | AC-FXLIB-021 | ASSUMPTION-36~39 (게이트 미경유, 감사 로그 없음) | **M1~M2 저작 전**에 답이 필요했다 (ASSUMPTION-37) |
| 2 | **M7 종단** | AC-FXLIB-022 | 매칭→번들→게이트→감사 로그→GUI 종단 통합 **+ ASSUMPTION-40 판정** | **M6 완료 후**에만 존재한다 |

**라이브 세션 수 = 2 (불변).** 사용자 확정 ③으로 표면화된 뒤 수용된 비용이다. **ASSUMPTION-40은 3회차를 만들지 않는다** — M0가 새 미검증 축을 열었지만, 형상 게이트(결정 I)가 부정 비용을 Pan/Tilt 패턴 4종의 효과로 한정하므로 별도 프로브 세션을 사지 않고 M7에 배칭한다. 이는 ASSUMPTION-38/39를 M0에 배칭했던 것과 같은 판단 기준(**저작을 막지 않는 측정은 배칭한다**)의 적용이다.

## §C. 기술 제약

1. **신규 런타임 의존성 0.** stdlib + PyYAML(기존 의존) + 기존 스택만.
2. **@MX:ANCHOR 경계 (위반 불가)**: `gate.screen()` 단일 스크리닝 경로, dedupe 판정 루프(tools.py:603-609), `_PROGRAMMER_STATE_COMMANDS`(:283-287) — 전부 소비만.
3. **stop-on-first-failure**: 실패 이후 `not_executed` — 리포트가 반드시 전파(REQ-FXLIB-014 (b)).
4. **번들 규모**: 기준선 87줄/5.77s, ~66ms/줄(66.3-66.7ms — BUSKWIZ progress.md:278-281 전재). v1 FX 번들은 **~12-18줄**(스텝 축이 패턴당 2-4줄을 더한다 — M0 폴드인 전 추정은 ~10-15줄) — 여유 큼.
5. **줄 앵커 드리프트**: 본 계획의 모든 file:line은 plan-phase 실측 시점 값이다. **각 마일스톤 착수 직전 재실측**한다(scout 인용 대비 이미 2건 드리프트 정정: matricks 경로 :126→:125, dedupe 블록 :227-237→:241-293/:603-609).

## §D. @MX 태그 대상 (예상 — 실제 배치는 run-phase 확정)

- `server/fx/schema.py` 모듈 헤더: `@MX:NOTE` — 폐쇄 필드 집합이 REQ-FXLIB-004(per-show 값 부재)의 강제 기제라는 사실(looks schema.py 선례).
- `server/fx/schema.py` 스텝 축(`steps`): `@MX:ANCHOR` — **길이 ≥ 2는 페이저의 생성 조건이다**(M0 실측). 이 불변식이 깨지면 콘솔은 `ok:true`를 주고 무대는 정지한다.
- `server/fx/instantiate.py` 충돌 가드: `@MX:WARN` + `@MX:REASON` — dedupe 탈락 → 빈/불완전 프로그래머 Store의 무음 실패 경로. `Step <k>`가 면제 3종이 아니라 지시 턴당 1회 경계가 생긴다는 사실을 사유에 적는다.
- `server/fx/report.py` 효과 증거 문면: `@MX:ANCHOR` — 효과는 기계로 검증되지 않는다(M0 측정된 경계). 이 문면을 지우면 사용자가 `ok`를 효과로 오독하게 된다.

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

- **의존 사슬**: M0 → M1 → {M2, M3, M4} → M5 → M6 → M7. **M2(라이브러리 YAML 저작) · M3(matching.py) · M4(instantiate.py/report.py)는 파일이 서로 겹치지 않아 M1 완료 후 병렬 가능**하다(PRECHK "병렬 웨이브 1"(M2+M3+M4) 선례). M0는 완료됐으므로 그 판정은 이제 **입력 상수**다 — M2(스텝 값 저작)·M4(스텝 열 형상 + 무조건 리포트 문면)가 함께 소비한다. M5는 M3+M4 산출물을 배선하므로 병렬 불가. 오케스트레이터가 Mode 4 병렬을 택할 경우 write-충돌 없음을 이 표로 확인한다.
  - **병렬 시 주의(M0 폴드인)**: M2와 M4는 파일이 겹치지 않지만 **스텝 축 형상이라는 공유 계약**을 갖는다(design.md §2.1 = 정본). 두 작업자가 각자 형상을 해석하면 라이브러리 스텝 값과 빌더 스텝 열이 어긋나고, **그 불일치는 런타임에서 아무 신호도 내지 않는다**(효과는 기계로 확인되지 않는다). 병렬 착수 시 design.md §2.1/§4를 양쪽 프롬프트에 **동일 문면으로** 주입한다.
- **결정 A~I**: §A.4 등록부가 정본. 전부 해소 — run-phase가 재질의할 결정은 없다.
- **DoD 요약**: acceptance.md §F가 정본.

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

- 입력: tier L · 신규 패키지 1 + tools.py 소폭 · 도메인 1(서버 파이썬) · 코딩 중심 · 병렬 이득 = M2/M3/M4 구간 한정.
- 권고: **sub-agent (Mode 5) 기본 + M2/M3/M4 구간만 선택적 병렬** — 코딩 중심 작업의 순차 기본 원칙. 확정과 기록(progress.md §F)은 오케스트레이터 몫.
