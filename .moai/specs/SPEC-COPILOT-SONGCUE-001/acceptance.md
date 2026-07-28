# SPEC-COPILOT-SONGCUE-001 — 인수 기준 (acceptance)

status: draft (v0.1.0, 2026-07-28) · Tier L · 본 문서는 spec.md의 요구를 관측 가능한 검증 기준으로 전개한다.

> **v0.1.0 — 최초 작성.** **AC 18건**(AC-SONGCUE-001~018) · **REQ 21건**(REQ-SONGCUE-001~021) 전량
> 커버. 라이브 AC 2건(**AC-SONGCUE-017** M0 프로브 · **AC-SONGCUE-018** M7 종단)은 라이브 세션 회계 2회에 대응한다.

---

## §A. 개요

곡 섹션 목록 → 룩 매핑 → **곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개** 번들 → 승인 1회 → 재조회 확인.
검증의 축은 넷이다: **① 입력 정합**(추정 보정 금지), **② 번호 전진**(큐 번호가 되돌아가지 않음),
**③ 무손실**(dedupe에 한 줄도 잃지 않음), **④ 정직한 보고**(관측하지 않은 것을 보고하지 않음).

---

## §B. Given-When-Then 시나리오

**시나리오 1 — 정상 경로**
Given 이름 있는 그룹이 있는 쇼파일과 6개 섹션 목록(`Intro 0:00 / Verse 0:18 / Chorus 0:52 / …`),
When 사용자가 "이 구조로 록 큐리스트 만들어줘"라고 지시하면,
Then 시퀀스 1개에 큐 6개가 생성되고, 각 큐 이름이 ASCII 섹션명이며, 보고가 섹션별 판정 6건을 담는다.

**시나리오 2 — 시각이 어긋난 입력**
Given `Verse 0:52 / Chorus 0:18`처럼 시각이 역행하는 목록,
When 생성을 지시하면,
Then 시스템은 **거부**하고 어느 항목이 왜 어긋났는지 보고한다. 정렬해서 진행하지 않는다.

**시나리오 3 — 어휘에 없는 섹션 이름**
Given `Breakdown`처럼 기존 어휘에 없는 이름,
When 생성을 지시하면,
Then 다이내믹스를 추정하지 않고 사용자에게 명시적 지정을 요구한다.

**시나리오 4 — 후렴 반복으로 값 라인이 겹침**
Given 같은 룩이 배정될 섹션이 둘 이상(`Chorus 1` · `Chorus 2`),
When 번들을 만들면,
Then 뒤 섹션의 저장은 **사유와 함께 건너뛰어지고**, 콘솔이 받은 커맨드에
`skipped_already_executed`가 **0건**이다.

**시나리오 5 — LiveLock**
Given LiveLock이 활성인 상태,
When 생성을 지시하면,
Then 콘솔 송신 **0건**이고 반환은 제안이며 `is_error=False`다.

**시나리오 6 — 타임코드 DESCOPE**
Given M0가 ASSUMPTION-20을 부정 판정한 상태,
When 큐리스트를 생성하면,
Then 번들에 타임코드 대상 커맨드가 **0건**이고, `progress.md` M0 절에 `DESCOPE: ASSUMPTION-20 <사유>`
형태의 **`DESCOPE:` 접두 행이 1건 이상** 존재한다(행 존재 판정이며 산문 해석이 아니다).

---

## §C. 인수 기준

### §C.0 REQ → AC 역추적표

| REQ | 커버하는 AC | 담당 M | 비고 |
|---|---|---|---|
| REQ-SONGCUE-001 | AC-SONGCUE-001 | M1 | 시각 포맷 3종 파싱 |
| REQ-SONGCUE-002 | AC-SONGCUE-002 | M1 | 거부 + 사유. 정렬 금지 |
| REQ-SONGCUE-003 | AC-SONGCUE-003 | M1 | AST 식별자 스캔으로 재정의 0건 |
| REQ-SONGCUE-004 | AC-SONGCUE-004 | M1 | 추정 금지 |
| REQ-SONGCUE-005 | AC-SONGCUE-005 | M2 | `looks_for_genre` 재사용 |
| REQ-SONGCUE-006 | AC-SONGCUE-005 | M2 | 동일 AC 구간 ③ (승격 금지) |
| REQ-SONGCUE-007 | AC-SONGCUE-006 | M3 | 시퀀스 1 · 큐 N |
| REQ-SONGCUE-008 | AC-SONGCUE-007 · AC-SONGCUE-009 | M3 | ASCII 고정 + 표현 계층. **발화 형태 한정**(`Store` 인라인 3번째 토큰 · 독립 동사 금지)은 AC-SONGCUE-009 구간 ①② |
| REQ-SONGCUE-009 | AC-SONGCUE-008 | M3 | 빈 시퀀스 번호의 출처 |
| REQ-SONGCUE-010 | AC-SONGCUE-009 | M3 | 파괴적 커맨드 0건 |
| REQ-SONGCUE-011 | AC-SONGCUE-010 | M3 | 무손실 + dedupe 무개정 |
| REQ-SONGCUE-012 | AC-SONGCUE-011 | M3 | 값 라인 충돌 가드 |
| REQ-SONGCUE-013 | AC-SONGCUE-012 | M4 | 타임코드 축 — 동일 AC 구간 ①②(GO / 부정) |
| REQ-SONGCUE-014 | AC-SONGCUE-012 | M4 | 자동 진행 축(`TrigType`) — 동일 AC 구간 ③④(GO / 부정) |
| REQ-SONGCUE-015 | AC-SONGCUE-009 | M3 | 동일 AC 구간 ② (`/trig=` 금지) |
| REQ-SONGCUE-016 | AC-SONGCUE-013 | M4 | 섹션 축 2단 보고 |
| REQ-SONGCUE-017 | AC-SONGCUE-014 | M4 | 재조회 + 한계 명시 |
| REQ-SONGCUE-018 | AC-SONGCUE-015 | M5 | 단일 실행 경로 AST 스캔 |
| REQ-SONGCUE-019 | AC-SONGCUE-015 | M5 | 동일 AC 구간 ② (등록 3곳) |
| REQ-SONGCUE-020 | AC-SONGCUE-010 | M3 | 정적 진입 금지 — 동일 AC 구간 ③④. **M6는 회귀 재확인** |
| REQ-SONGCUE-021 | AC-SONGCUE-016 | M6 | PRESERVE 무변경 — `matching.py`·`instantiate.py` diff 빈 출력 |

**마일스톤별 AC 집합 (SSOT)** — 중복·누락 0:

| M | 소유하는 AC | 성격 |
|---|---|---|
| M0 | 017 | LIVE 1/2 — 전제 5건 판정 (ASSUMPTION-21은 **블로킹**) |
| M1 | 001 · 002 · 003 · 004 | 섹션 입력 |
| M2 | 005 | 섹션 → 룩 |
| M3 | 006 · 007 · 008 · 009 · 010 · 011 | 큐리스트 번들 |
| M4 | 012 · 013 · 014 | 타이밍 GO/DESCOPE · 보고 |
| M5 | 015 | 툴 배선 · 실행 경로 |
| M6 | 016 (+ 010·011 **재확인만**) | 회귀 · PRESERVE · 정적 스캔 |
| M7 | 018 | LIVE 2/2 — 종단 |

**AC 개수 = 18** (001~018). **표에 행이 없는 AC는 017·018 둘뿐이며 의도된 것이다** — 전자는 전제
판정 AC, 후자는 종단 통합 AC로 단일 REQ에 귀속되지 않는다(각 AC 본문의 '대상 요구사항'이 명시).
위 표의 소유 AC를 합치면 18건이며 재확인(010·011)은 소유가 아니다 —
최초 판정은 M3 소관이고 M6는 회귀로 재확인만 한다(BUSKWIZ의 AC 소유 구분 규율 계승).

### §C.1 AC 본문

### AC-SONGCUE-001 — 섹션 입력 파싱

**When** 섹션 목록이 주어지면, the 시스템 **shall** 이름 · 시작 시각 · 순서를 구조화해 돌려준다.

- 대상 요구사항: REQ-SONGCUE-001
- 검증 방법: `pytest server/tests/test_songcue_sections.py -q`
- 기대 결과: `mm:ss` · `mm:ss.mmm` · 초 실수 3종이 같은 초 단위 값으로 정규화된다. 파싱 결과의
  순서가 입력 순서와 동일하다.
- 검증 구간: ① 3종 포맷 각각 1건 이상. ② 정규화 결과가 부동소수 비교가 아니라 밀리초 정수로 고정된다.

### AC-SONGCUE-002 — 어긋난 시각은 거부한다

**If** 시작 시각이 단조 증가하지 않거나 중복되면, **then** the 시스템 **shall** 거부하고 사유를 보고한다.

- 대상 요구사항: REQ-SONGCUE-002
- 검증 방법: `pytest server/tests/test_songcue_sections.py -q`
- 기대 결과: 역행·중복 각각에서 예외 또는 구조화된 거부가 발생하고, **어느 인덱스가 어긋났는지**가
  사유에 담긴다.
- 추가 assert: **정렬해서 진행하지 않는다** — 거부 후 반환에 섹션 목록이 들어 있지 않거나, 들어
  있다면 입력 순서와 동일하다(임의 재배열 0건).

### AC-SONGCUE-003 — 섹션 어휘 재정의 금지

**The** 시스템 **shall not** 섹션 어휘·다이내믹스 매핑을 본 SPEC의 신규 모듈에 재정의한다.

- 대상 요구사항: REQ-SONGCUE-003
- 검증 방법: AST 식별자 스캔 + `pytest server/tests/test_songcue_sections.py -q`
- 기대 결과: 신규 모듈이 `matching.py`의 표를 **import해서** 쓰고, 자체 매핑 리터럴이 **0건**이다.
- 검증 구간: ① 신규 모듈의 AST에 섹션어→숫자 매핑 딕셔너리 리터럴 0건. ② `matching` 모듈의
  심볼을 실제로 import함(비공허성). **raw 텍스트 grep이 아니라 AST**인 이유는 산문이 어휘를
  설명할 수 있기 때문이다(BUSKWIZ M1의 교훈 — `SPEC-COPILOT-BUSKWIZ-001/progress.md` M1 절).

### AC-SONGCUE-004 — 모르는 섹션 이름은 추정하지 않는다

**Where** 섹션 이름이 어휘에 없는 경우, the 시스템 **shall** 명시적 지정을 요구한다.

- 대상 요구사항: REQ-SONGCUE-004
- 검증 방법: `pytest server/tests/test_songcue_sections.py -q`
- 기대 결과: 다이내믹스가 임의 기본값으로 채워지지 않고, 그 섹션이 "지정 필요"로 표시된다.
- 추가 assert: 어휘에 있는 이름과 없는 이름이 **섞인** 입력에서 있는 것만 해석되고 없는 것만
  표시된다(전량 실패로 접지 않는다).

### AC-SONGCUE-005 — 섹션 → 룩 매핑

**The** 시스템 **shall** 장르와 섹션 다이내믹스로 룩을 고르며, 없으면 승격하지 않는다.

- 대상 요구사항: REQ-SONGCUE-005 / REQ-SONGCUE-006
- 검증 방법: `pytest server/tests/test_songcue_map.py -q`
- 기대 결과: 전량 PASS.
- 검증 구간: ① 다이내믹스 `1..5` 각 값에서 선택된 룩의 `dynamics`가 요구값과 일치한다.
  ② 후보 순회가 `looks_for_genre`를 **재사용**함을 AST 식별자로 확인(재구현 0건).
  ③ 그 장르에 해당 다이내믹스 룩이 없을 때 **가장 가까운 룩으로 승격하지 않고** 미매핑으로 보고한다.

### AC-SONGCUE-006 — 곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개

**The** 생성 번들 **shall** 시퀀스 1개와 섹션 수만큼의 큐를 만든다.

- 대상 요구사항: REQ-SONGCUE-007
- 검증 방법: `pytest server/tests/test_songcue_bundle.py -q`
- 기대 결과: 생성 커맨드에서 추출한 `(시퀀스 번호, 큐 번호)` 집합이 시퀀스 1종 × 큐 `1..N`이다.
- 검증 구간: ① 시퀀스 번호가 정확히 1종. ② 큐 번호가 `1`부터 `N`까지 **빠짐없이 한 번씩**
  (중복·건너뜀 0건) — 하드 결함 1(번호 비전진)의 기계 판정. **(값 라인 충돌이 없는 픽스처 기준.
  충돌 픽스처는 AC-SONGCUE-011이 소유하며 생성 번호가 섹션 인덱스의 부분집합이다.)** 결정 F가
  **건너뜀에도 번호를 당기지 않는다**고 확정했으므로 두 픽스처를 하나로 합치지 않는다 — 이 구간을
  통과시키려고 번호를 당기는 '수리'는 AC-SONGCUE-011의 보고를 거짓으로 만든다.
  ③ 섹션 6개·10개 두 크기에서 모두 성립.

### AC-SONGCUE-007 — 큐 이름은 ASCII, 한국어는 표현 계층

**The** 시스템 **shall** ASCII 큐 이름을 발화하고 한국어는 표현 계층에서만 쓴다.

- 대상 요구사항: REQ-SONGCUE-008
- 검증 방법: `pytest server/tests/test_songcue_bundle.py -q`
- 기대 결과: 생성 커맨드 전수에서 비-ASCII 문자가 **0건**이고, 사용자 보고에는 한국어가 있다.
- 검증 구간: ① 커맨드 문자열 전수 `c.isascii()` 전량 True(비공허성: 커맨드 목록이 비어 있지 않음).
  ② 보고 렌더에 한글 음절이 존재. ③ 룩 자산·스키마에 한국어 필드 추가 **0건**.

### AC-SONGCUE-008 — 시퀀스 번호의 출처

**The** 시스템 **shall** 시퀀스 번호를 리그 조회 결과의 여집합에서만 고른다.

- 대상 요구사항: REQ-SONGCUE-009
- 검증 방법: `pytest server/tests/test_songcue_bundle.py -q`
- 기대 결과: 리그가 알려준 기존 시퀀스 번호와 **겹치지 않는** 번호가 선택된다.
- 검증 구간: ① 리그 픽스처를 바꾸면 선택된 번호가 따라 바뀐다(하드코딩 0건).
  ② 조회가 실패하거나 절단 신호가 오면 **번호를 추측하지 않고** 거부한다 —
  BUSKWIZ가 익스큐터에서 데인 함정("비어 있음"과 "미확인"의 미구분)의 시퀀스 축 방어.

### AC-SONGCUE-009 — 파괴적 커맨드 · 금지 문법 0건

**The** 시스템 **shall not** `/Overwrite`·`/Remove`·`Delete`·MA2형 `/trig=`·독립 동사 `Label Cue`·`Goto Cue`를 발화한다.

- 대상 요구사항: REQ-SONGCUE-008(**발화 형태 한정** — 구간 ①②의 `Label Cue`) / REQ-SONGCUE-010 /
  REQ-SONGCUE-015. `Goto Cue`는 REQ가 아니라 **범위 경계**에서 온다 — spec.md §D의
  `Out of Scope — 재생 · 섹션 점프` 절이 근거이며, 그래서 이 AC가 그 경계의 기계 판정을 맡는다.
- 검증 방법: 생성 커맨드 전수 스캔 + `pytest server/tests/test_songcue_bundle.py -q`
- 기대 결과: 각 패턴 **0건**.
- 검증 구간: ① **소스 grep이 아니라 생성된 커맨드 튜플 전수**에 스캔을 걸고 그 목록이 비어 있지
  않음을 함께 assert한다(AC-BUSKWIZ-013의 감사 D3 교훈 계승). 금지 패턴 집합은 **여섯**이다 —
  `/Overwrite` · `/Remove` · `Delete` · MA2형 `/trig=` · 독립 동사 **`Label Cue`** · **`Goto Cue`**
  (매칭은 대소문자 무관). 뒤 둘의 근거: `Label Cue`는 룰북 0건이고 큐 이름의 발화 형태가 `Store`
  인라인 3번째 토큰으로 **한정**되므로(REQ-SONGCUE-008) 사후 명명 커맨드가 애초에 존재하지 않는다.
  `Goto Cue`는 spec.md §D의 `Out of Scope — 재생 · 섹션 점프` 절이 닫은 축이며, 게이트가 참조를
  추출하지 못해 보류로 떨어지는 형태다. ② 스캐너가 금지 형태를 실제로 잡는지 **심어서** 확인한다 —
  `Store Cue 5 /overwrite` · `Cue 1 /trig=Time` · `Label Cue 1 'X'` · `Goto Cue 2 Sequence 5`
  **넷을 각각 주입해 넷 다 잡히는지** 본다(한 패턴만 심어 통과시키면 나머지 스캐너는 공허하다).

### AC-SONGCUE-010 — 무손실 + dedupe 무개정 + 정적 진입 금지

**The** 번들 **shall** dedupe에 한 줄도 잃지 않으며, dedupe 규칙과 per-show 값의 정적 진입은 무변경이다.

- 대상 요구사항: REQ-SONGCUE-011 / REQ-SONGCUE-020
- 검증 방법: 실제 `run_commands` 경로 + 정적 스캔
- 기대 결과: `skipped_already_executed` **0건**, 콘솔이 받은 목록이 번들과 일치.
- 검증 구간: ① 목적지 커맨드가 선두 1회, 섹션 단위 `ClearAll` 전량 생존.
  ② `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`·dedupe 블록이 `<BASE>..HEAD`
  diff에서 무변경. ③ 신규 모듈에서 시퀀스·큐·그룹·풀·슬롯 번호 리터럴이 커맨드 조립에 쓰이는
  지점 0건(**독스트링 제외** 문자열 상수 + f-string 숫자 상수 + 리그 파라미터 숫자 기본값 3종 스캔).
  ④ 세 스캐너 전부 금지 형태 주입으로 비공허성 증명.

### AC-SONGCUE-011 — 값 라인 충돌 가드 (섹션 축)

**If** 두 섹션의 값 라인이 같아지면, **then** the 시스템 **shall** 뒤 섹션을 사유와 함께 건너뛴다.

- 대상 요구사항: REQ-SONGCUE-012
- 검증 방법: `pytest server/tests/test_songcue_bundle.py -q`
- 기대 결과: 건너뛴 섹션이 사유 코드와 함께 보고되고, 콘솔 송신에 `skipped_already_executed` 0건.
- 검증 구간: ① 같은 룩이 배정되는 섹션 2개 픽스처에서 뒤엣것이 건너뛰어진다. ② 사유에 충돌
  상대가 담긴다. ③ **거부(예외)가 아니라 건너뛰기**임을 확인 — 번들은 여전히 실행 가능하고 앞
  섹션은 온전하다. ④ 서로 다른 값이면 발동하지 않는다(비공허성).

### AC-SONGCUE-012 — 타임코드 축 · 자동 진행 축의 **독립** GO/부정 판정

**Where** ASSUMPTION-20(타임코드)이 M0에서 긍정 실측된 경우, the 시스템 **shall** 타임코드 커맨드를
M0가 실측한 형식으로만 발화한다. **Where** ASSUMPTION-22(`TrigType`/`TrigTime`)가 M0에서 긍정 실측된
경우, the 시스템 **shall** 자동 진행 커맨드를 M0가 실측한 토큰으로만 발화한다. 어느 축이든 부정이면
the 시스템 **shall not** **그 축의** 커맨드를 발화하며, 사유를 기록한다.

- 대상 요구사항: REQ-SONGCUE-013(**축 1** — 구간 ①②) / REQ-SONGCUE-014(**축 2** — 구간 ③④)
- 검증 방법: `pytest server/tests/test_songcue_timing.py -q` — **두 축을 각각 독립으로 판정한다.**
  ASSUMPTION-20의 판정이 ①·② 중 하나를, ASSUMPTION-22의 판정이 ③·④ 중 하나를 고르며 **네 조합
  전부에서 판정이 정의된다** — GO·GO → ①③ / GO·부정 → ①④ / 부정·GO → ②③ / 부정·부정 → ②④.
  **두 축을 하나의 논리곱으로 접지 않고 "둘 중 정확히 하나"로도 세지 않는다**: 결정 B가 두 판정을
  **독립**으로 확정했고, 등급이 서로 달라(ASSUMPTION-20은 **T5**로 부정 기대 · ASSUMPTION-22는
  **T2**) **혼합 결과가 가장 개연성이 높다.** 논리곱으로 접으면 혼합에서 어느 분기도 참이 아니게 되어
  M4가 판정 불가로 멈춘다.
- 기대 결과: 두 축이 **각각** GO 또는 부정으로 판정되고, 부정으로 판정된 축의 커맨드가 0건이다.
  **한 축의 부정이 다른 축의 GO를 취소하지 않는다.**
- 검증 구간 (축별 독립 — 축 1은 ①②, 축 2는 ③④):
  - **축 1 — 타임코드 (ASSUMPTION-20 / REQ-SONGCUE-013)**
    - ① **GO**: 타임코드 발화 형식이 **M0가 실측한 것 하나뿐**이고(실측되지 않은 오브젝트명·문법의
      발화 0건), 시간값은 섹션 입력에서 **계산된 것만** 쓴다.
    - ② **부정**: 생성 번들에 타임코드 대상 커맨드가 **0건**이고, `progress.md` M0 절에
      `DESCOPE: ASSUMPTION-20 <사유>` 형태의 **`DESCOPE:` 접두 행이 1건 이상** 존재한다
      (행 존재 판정이며 산문 해석이 아니다).
  - **축 2 — 자동 진행 (ASSUMPTION-22 / REQ-SONGCUE-014)**
    - ③ **GO**: `Set Cue <m> Sequence <n> Property 'TrigType' <token>` / `'TrigTime' <t>` 발화가
      **M0가 실측한 토큰만** 쓴다. `'Follow'`와 `'Time'`은 M0가 **각각 따로 재고 구분 기록한** 결과를
      각각 따르며(AC-SONGCUE-017 측정 항목 4), 룰북 주석의 토큰 메뉴(`Go / Time / Follow / Sound /
      BPM` — `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:111`의 줄 끝 주석)를
      **실측 없이 발화하지 않는다**. 트리거 토큰은 대문자로 시작한다(같은 파일 `:115`).
    - ④ **부정**: 생성 번들에 `Set Cue … Property 'TrigType'`·`'TrigTime'` 계열이 **0건**이고,
      `progress.md` M0 절에 `DESCOPE: ASSUMPTION-22 <사유>` 형태의 **`DESCOPE:` 접두 행이 1건 이상**
      존재한다.
- 비고: 실행되지 않은 분기는 **축별로** `skip` 사유를 명시한 채 **남긴다 — 삭제하지 않는다**.
  축 1이 GO여도 축 2의 ④는 남고 그 역도 같다 — 네 구간 중 실행되는 것은 **항상 2개**이고 나머지
  2개는 `skip`으로 남는다. 후속 SPEC이 게이트를 다시 열 때 출발점이 된다(AC-BUSKWIZ-012 비고의 계승).

### AC-SONGCUE-013 — 섹션별 2단 보고

**The** 보고 **shall** 집계와 **섹션별** 판정을 함께 낸다.

- 대상 요구사항: REQ-SONGCUE-016
- 검증 방법: `pytest server/tests/test_songcue_report.py -q`
- 기대 결과: 전량 PASS.
- 검증 구간: ① 곡의 모든 섹션이 정확히 한 번씩 판정에 나타난다. ② 집계 수치가 섹션별 합과 일치한다.
  ③ 판정 어휘가 닫힌 집합이다. ④ 각 섹션의 이름 문자열이 한국어 요약 문자열에 **그대로(부분 문자열로)
  포함된다** — `all(name in summary for name in section_names)`. 가독성 심사가 아니라 포함 판정이다.

### AC-SONGCUE-014 — 재조회 확인 + 한계 명시

**When** 번들이 실행되면, the 시스템 **shall** 재조회로 큐의 존재와 이름을 확인하고 프로퍼티를 읽을
수 없다는 한계를 결과에 명시한다.

- 대상 요구사항: REQ-SONGCUE-017
- 검증 방법: `pytest server/tests/test_songcue_report.py -q` + M7 라이브
- 기대 결과: 재조회 결과가 생성한 큐 수·이름과 일치하고, 결과 페이로드의 `property_unobserved`
  항목이 `server/looks/songcue_report.py`의 공개 상수 **`PROPERTY_UNOBSERVED_NOTE`**와 **문자열로
  동일**하다(상수 동일성 비교이며 산문 대조가 아니다).
- 추가 assert — **상수 자신의 최소 내용 불변식**: 상수 동일성만 보면 구현이 그 상수를 대입하기만
  해도 통과하므로 **상수 값이 빈 문자열이어도 초록이 된다** — 이 SPEC이 반복해 금지한 공허한
  단언이다. 그래서 상수 자신에 대해 함께 assert한다 — ① `PROPERTY_UNOBSERVED_NOTE.strip()`이
  빈 문자열이 아니다. ② 그 값이 `CueFade`와 `TrigType` **두 토큰을 모두** 포함한다(관측하지 못한
  대상을 이름으로 지목해야 한계 문구가 정보를 갖는다). 두 assert가 없으면 상수 동일성 비교는
  자기참조로 닫혀 아무것도 지키지 않는다.
- 검증 구간: ① 큐 존재·이름 대조. ② **CueFade·TrigType을 확인했다고 주장하는 필드가 0건**
  (`SPEC-COPILOT-EXECREF-001/design.md:167` 실측 — 응답기가 그것을 반환하지 않는다).
  관측하지 않은 것을 보고하지 않는다.

### AC-SONGCUE-015 — 단일 실행 경로 + 툴 등록 관례

**The** 신규 툴 **shall** 기존 `run_commands` → `gate.screen()` 경로만 쓰고 등록 관례를 따른다.

- 대상 요구사항: REQ-SONGCUE-018 / REQ-SONGCUE-019
- 검증 방법: `pytest server/tests/test_songcue_tool.py -q` + AST 식별자 스캔
- 기대 결과: 전량 PASS.
- 검증 구간: ① 핸들러 서브트리와 신규 모듈의 AST에 `execution_port`·`ConsoleLink`·`APIRouter`
  직접 접근 **0건**(비공허성 assert 동반). ② `TOOL_NAMES`·`definitions`·`handlers` 3곳에 모두
  존재하고 **디스패치로** 확인한다(dict 조회가 아니라 모델이 닿는 경로).
  ③ 파라미터 스키마에 그룹·풀·슬롯·픽스처·시퀀스 번호 필드 **0개**.
  ④ LiveLock에서 콘솔 송신 0건 · 반환은 제안 · `is_error=False`. 게이트 보류는 `is_error=True`
  (강등과 보류는 다른 사건이다).

### AC-SONGCUE-016 — PRESERVE 무변경 + 전체 회귀

**The** 본 SPEC **shall not** PRESERVE 목록을 변경하며 기존 스위트에 신규 실패를 만들지 않는다.

- 대상 요구사항: REQ-SONGCUE-021
- 검증 방법: `git diff --stat <BASE>..HEAD -- <목록>` → **빈 출력**. 이어서 전체 스위트.
- 기대 결과: PRESERVE diff 빈 출력, 신규 실패 **0건**.
- **`<BASE>..HEAD` 범위는 협상 불가**: 인자 없는 `git diff`는 커밋 직후 항상 빈 출력이라 게이트가
  무력해진다(BUSKWIZ 감사 D4의 계승). `<BASE>`는 run-phase 킥오프에서 기록한 착수 SHA다.
- 추가 assert: `server/looks/{matching,instantiate,resolver,schema,loader,roles}.py`의 diff가 빈
  출력 — 본 SPEC이 **재사용하되 고치지 않는다**는 형상의 기계적 증거다.
- baseline은 각 마일스톤이 착수 직전 직접 실측하며 **이월 인용을 금지**한다.

### AC-SONGCUE-017 — M0 라이브 프로브 (LIVE — 2건 중 1번째, M0)

**When** 실물 콘솔에서 M0 프로브를 실행하면, the 시스템 **shall** ASSUMPTION-20~24를 판정 확정한다.

- 대상 요구사항: **없음 — 전제 판정 AC다.** ASSUMPTION-20~24를 확정해 REQ-SONGCUE-013/014의 분기와
  M3 착수 가능성을 정한다(단일 REQ에 귀속시키면 그 REQ가 없으면 프로브도 없다는 잘못된 함의가 생긴다).
- 검증 방법: 실물 grandMA3 onPC 세션. 코드 변경 0건.
- 기대 결과: **5건 전부 판정 확정**(GO 또는 DESCOPE). 측정 항목:
  1. **ASSUMPTION-21 (블로킹)** — 같은 시퀀스에 `Cue 2` 이상 추가. `Store Sequence <n> Cue 1 …`
     후 `Cue 2 … /Merge`를 발화하고 `DataPool/Sequences/<n>` 재조회로 **자식 2개**를 확인한다.
     **`/Merge` 있는 형태와 없는 형태를 각각 발화해 결과를 구분 기록한다** — 아래 측정 항목 4의
     `'Follow'`/`'Time'` 분리와 **동형**이다. `Store Sequence <n> Cue 2 '<name>' /Merge`와
     `Store Sequence <n> Cue 2 '<name>'`를 **서로 다른 시퀀스 번호에서** 발화하고 두 경우 모두
     재조회로 자식 수를 센다 — `/Merge` 없는 `Store`가 기존 큐에 대해 병합인지 치환인지는
     실측되지 않았으므로, 한 형태만 재면 결정 E가 말하는 "M0가 잰 리터럴 그대로"의 대상이
     정해지지 않는다. **부정이면 M3 저작을 착수하지 않는다.**
  2. **ASSUMPTION-23** — 빈 시퀀스 번호 식별. `DataPool/Sequences` 열거의 여집합에서 고른 번호가
     실제로 비어 있는지, 그리고 "비어 있음"과 "존재하지 않음"이 구별되는지.
  3. **ASSUMPTION-20** — 타임코드 오브젝트·문법. **비파괴 범위에서** 존부를 재고 판정 불가면
     그 사실을 판정으로 기록한다(BUSKWIZ 측정 1의 선례).
  4. **ASSUMPTION-22** — `Set Cue <m> Sequence <n> Property 'TrigType' <token>` / `'TrigTime' <t>`.
     **`'Follow'`와 `'Time'`을 각각 따로 재고 결과를 구분해 기록한다** — 룰북 검증 예시의 리터럴은
     `'Follow'` 하나이고 `'Time'`은 같은 줄 **주석의 토큰 메뉴**에서 왔다
     (`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:111`). 곡 섹션 타이밍이 필요한
     쪽은 `'Time'`이므로 이 구분이 REQ-SONGCUE-014의 성패를 가른다.
     **파싱 성공과 효과 발생도 구분해 기록한다** — `Cmd()`가 거부된 커맨드에도 OK를 보고한 실측
     사례가 있다(`SPEC-COPILOT-BUSKWIZ-001/progress.md` 측정 3).
  5. **ASSUMPTION-24** — 곡 1개 번들의 왕복. BUSKWIZ의 87줄/5.77s 실측을 기준으로 계산하고,
     계산이 그 범위를 넘으면 실측한다.
- 기록 형식(**반드시**): 위 다섯 항목의 판정을 `progress.md` M0 절에 남길 때, 부정·DESCOPE 판정은
  `DESCOPE: ASSUMPTION-nn <사유>` 형태의 **접두 행**으로 적는다(`nn`은 20~24이며 한 판정당 한 행).
  **AC-SONGCUE-012 구간 ②④와 §B 시나리오 6의 행 존재 판정이 그 형식에 의존한다** — 산문 안에
  녹여 쓰면 그 판정이 기계로 성립하지 않고 산문 해석으로 되돌아간다. GO 판정은 이 접두를 쓰지 않는다.
- 비고: **우회 금지** — 타임코드가 없다고 시퀀스·큐를 임의로 더 만들어 우회하지 않는다.
  DESCOPE가 답이다. 정리 기록(생성한 프로브 산물의 처분)을 남긴다.

### AC-SONGCUE-018 — 종단 라이브 검증 (LIVE — 2건 중 2번째, M7)

**When** 실물 콘솔에서 곡 1개의 큐리스트를 종단 생성하면, the 시스템 **shall** 계획 번들과 콘솔이
실행한 것의 일치를 보이고 재조회로 확인한다.

- 대상 요구사항: **(종단 통합 — B.1~B.5 전체)**. 단일 REQ가 아니라 파이프라인 전체가 대상이므로
  §C.0 역추적표에 행을 두지 않는다(AC-BUSKWIZ-017의 선례).
- 검증 방법: 실물 콘솔 세션. 툴 반환의 per-command status와 **감사 로그**를 대조한다.
- 기대 결과:
  1. `console.executed == plan.commands` — 순서까지 동일, 전 행 `ok=True`.
  2. `skipped_already_executed` **0건**.
  3. 재조회에서 시퀀스 1개에 큐 N개가 **서로 다른 번호로** 존재하고 이름이 일치한다.
  4. 보고의 집계 수치가 재조회 실측과 일치한다.
- 비고: 큐 프로퍼티(CueFade·TrigType)는 응답기가 노출하지 않으므로 검증은 **존재와 이름** 수준이며,
  그 한계를 결과에 명시한다. 증거는 툴 자신의 목록이 아니라 **감사 로그**여야 한다(BUSKWIZ M7의 교훈).

---

## §D. Edge Cases

| 상황 | 기대 동작 | 근거 |
|---|---|---|
| 섹션 0개 입력 | 거부. 빈 번들은 "완전 성공"이 아니다 | BUSKWIZ `GenreBundle.complete`의 규율 |
| 섹션 1개 | 정상 — 시퀀스 1개 + 큐 1개 | ASSUMPTION-21의 `Cue 2` 경로를 타지 않음 |
| 같은 이름 섹션 반복(`Chorus` ×3) | 큐 이름에 순번을 붙여 구별. 값 라인 충돌 가드가 별도로 작동 | REQ-SONGCUE-012 |
| 리그가 역할을 하나도 주소 못 함 | 저장 0건이 **답변**이다(`is_error=False`), 보고가 이유를 담는다 | AC-BUSKWIZ-011 ② 선례 |
| 리그 섹션 미도착 | 번들 구성 **이전에** `is_error=True` 조기 반환 | `server/orchestrator/tools.py`의 `instantiate_look` 리그 미도착 조기 반환 절 |
| 섹션 시각이 모두 동일 | REQ-SONGCUE-002가 중복으로 거부 | — |
| 시퀀스 번호 여집합이 비어 있음(모든 번호 점유) | 거부. 추측하지 않는다 | AC-SONGCUE-008 ② |

---

## §E. Quality Gate 기준

- `uv run pytest server/tests/ -q` 신규 실패 **0건** (baseline은 각 마일스톤 직접 실측)
- `uv run ruff check` / `format --check` — 본 SPEC이 신규·변경한 파일 clean.
  **기존 비-clean 지점은 무관 재포맷을 피해 손대지 않으며 그 사실을 progress.md에 기록한다.**
- PRESERVE `git diff --stat <BASE>..HEAD -- <목록>` **빈 출력**
- 뮤테이션 테스트: 각 마일스톤의 핵심 불변식을 깨는 뮤테이션이 **실제로 테스트를 죽이는지** 확인한다.
  BUSKWIZ에서 이 단계가 **공허한 단언 3건**을 잡았다(통과하지만 아무것도 지키지 않던 테스트).

## §F. Definition of Done

1. AC-SONGCUE-001~018 **18건 전량 판정 확정**(PASS 또는 정의된 DESCOPE 경로).
2. §C.0 역추적표의 모든 REQ가 최소 1개 AC로 커버되고, 표가 최종 REQ 목록과 일치한다.
3. 큐 번호가 `1..N` 빠짐없이 한 번씩임이 기계로 고정되어 있다(하드 결함 1).
4. 생성 커맨드 전수에 비-ASCII **0건** · 파괴적 커맨드 **0건** · MA2형 `/trig=` **0건** · 독립 동사
   `Label Cue`·`Goto Cue` **0건**이고, 각 스캐너의 비공허성이 금지 형태 주입으로 증명되어 있다.
5. 값 라인 충돌 가드가 섹션 축에서 작동하고, 그것이 **거부가 아니라 건너뛰기**임이 고정되어 있다.
6. PRESERVE 무변경 확인 — 특히 `server/looks/matching.py`와 `instantiate.py`의 diff가 빈 출력이다.
7. 라이브 2회(M0 · M7)가 집행되고 **관측하지 않은 것을 보고하지 않았다**는 한계 명시가 결과에 있다.
8. 음원 자동 분석 · 프리셋 생성 · 익스큐터 바인딩 · 응답기 변경 · dedupe 개정이 본 SPEC의 커밋
   범위에 **등장하지 않는다**(§D 범위 경계).
9. CHANGELOG · frontmatter · progress.md §E.1~§E.4가 갱신되어 있다.
