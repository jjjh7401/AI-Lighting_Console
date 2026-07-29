---
id: SPEC-COPILOT-SONGCUE-001
title: "송 구조 기반 큐리스트 초안 생성기 (Song-Structure Cuelist Generator)"
version: "0.2.0"
status: completed
created: 2026-07-28
updated: 2026-07-29
author: manager-spec
priority: P1
phase: "Phase 3 음악분석 → 큐리스트 자동화 (v1.4.0 target)"
module: "server/looks/ (확장), server/orchestrator/tools.py"
lifecycle: spec-anchored
tags: "cuelist, song-structure, sections, sequence, cue, timecode, trig-type, look-library, safety-gate"
tier: L
related_specs: [SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-EXECBODY-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-SONGCUE-001 — 송 구조 기반 큐리스트 초안 생성기

> **본 SPEC은 제안서 P1-1**(`docs/proposals/2026-07-26-lighting-direction-feature-proposal.md:68-74`)**이고
> 로드맵 Phase 3의 구체화다**(`.moai/project/product.md:39`, `DESIGN.md:157-160`). LOOKLIB이 룩 어휘를,
> BUSKWIZ가 다중 룩 조율(슬롯 원장 · 번들 결합 · 2단 보고)을 만들었고, 본 SPEC은 그 위에 **시간축**을
> 얹는다. 두 선행 SPEC이 `§D`에서 "시퀀스는 P1-1의 영역"이라고 명시적으로 남겨 둔 자리다
> (`SPEC-COPILOT-LOOKLIB-001/spec.md:176-178`, `SPEC-COPILOT-BUSKWIZ-001/spec.md:140-146`).

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-07-28 | manager-spec | 최초 작성. 사용자 확정 3건(음원 분석 분리 · 타임코드 M0 게이트 · 큐 이름 ASCII 고정) 반영 |

---

## A. 개요

곡의 **섹션 목록**(이름 · 시작 시각 · 순서)을 입력받아, 각 섹션에 룩을 매핑하고
**곡 1개 = 시퀀스 1개, 섹션 1개 = 큐 1개**라는 실무 표준 구조로 MA3에 생성한다. 실행 단위는
**단일 번들 · 승인 1회**이며, 산출물은 사람이 검토·수정할 **초안**이다.

### 사전 확정 사실 (사용자 확정 — 재질의 금지)

1. **① 음원 자동 분석은 본 SPEC의 범위가 아니다.** 섹션 목록은 **사용자가 제공**한다(DAW 마커
   텍스트 또는 구조화 입력). 근거: 오디오 분석 의존성이 저장소에 **0건**이고(`pyproject.toml:8-18`,
   `uv.lock` 58패키지 전량 무매치 — numpy조차 없다), 파일 업로드 경로도 **0건**이며
   (`server/web/app.py:311` `receive_text()` 텍스트 전용, FastAPI 라우트 8개 전량에 `UploadFile` 없음,
   `ui/src/**`에 `input[type=file]` 0건), Tauri capability가 `no upload`를 **명시적으로 거부**한다
   (`src-tauri/capabilities/default.json:4`, 테스트가 강제: `server/tests/test_deploy_tauri_shell.py:347-351`).
   자동 분석을 함께 열면 신규 의존성 + 업로드 경로 + 진행률 프로토콜(현재 0건)까지 세 축이 동시에
   열린다. **별도 SPEC.**
2. **② 타임코드는 M0 라이브 프로브의 GO/DESCOPE 게이트다.** 근거: 타임코드 문법·객체가
   **저장소 전체에서 0건**이다(룰북 5파일 · `server/**` · `console/lua/**` · `.moai/**` 전량 무매치.
   유일 등장은 외부 참고 링크 텍스트 `docs/proposals/…:125`, `:127`). 선행 SPEC이 같은 사실을 이미
   기록하고 인계했다(`SPEC-COPILOT-BUSKWIZ-001/spec.md:146`, `SPEC-COPILOT-BUSKWIZ-001/research.md:385` — "별도 라이브 프로브가
   선행되어야 한다"). **DESCOPE는 실패가 아니라 정의된 결과다**(BUSKWIZ의 익스큐터 축 선례).
3. **③ 큐 이름은 ASCII로 고정하고 한국어는 표현 계층에서 매핑한다.** 근거: 큐 이름은 안전 게이트가
   **커맨드로 파싱하는 본문 라인**이 된다 — `server/safety/console.py:478-484`이 자식의 `name`을
   그대로 본문 라인으로 수집하고, `server/safety/expand.py:106-112`가 라인마다 `validate`를 걸어
   실패 시 **보류**하며, `server/safety/grammar.py:20`의 선두 토큰 규칙은 `^[A-Za-z][A-Za-z0-9_+\-]*$`
   **ASCII 전용**이다. ASCII 큐 이름의 종단 통과는 라이브 관측이 있으나
   (`SPEC-COPILOT-SHOWUI-001/progress.md:460` — 큐 `'Blue Look'`을 담은 `Sequence 90`에 대해
   `Go+`/`Off` 둘 다 `ok=True`), **한국어 큐 이름의 종단 효과는 미관측**이다. 표현 계층 매핑은
   BUSKWIZ가 이미 세운 형상이다(`server/looks/report.py:63` `_REASON_LABELS`, `:74` `_VERDICT_LABELS`).

### 하드 결함 — 본 SPEC이 닫아야 하는 것

1. **큐 번호가 전진하지 않을 위험 — 슬롯 원장과 동형이다.** BUSKWIZ가 프리셋 슬롯에서 실측으로
   드러낸 결함(`_first_free_slot`은 소비자가 누구든 전진하지 않는다,
   `server/looks/instantiate.py:307-312`)의 시간축 판본이다. 섹션마다 큐 번호가 1로 되돌아가면
   섹션 N개가 같은 큐를 덮어쓴다.
2. **값 라인 충돌 — 섹션 축에서 재발한다.** dedupe 면제 집합은 3종뿐이고(`server/orchestrator/tools.py:234-238`)
   `Store …`와 값 라인은 면제가 **아니다**. 두 섹션이 같은 값 라인을 내면 뒤엣것이 탈락하고
   **빈 프로그래머 상태로 `Store`가 실행되는데 콘솔은 성공으로 답한다.** BUSKWIZ가
   `VALUE_LINE_COLLISION`(`server/looks/busking.py:230`) + `_guard_collision`(`:240`)으로 푼 그 문제이며,
   **곡은 후렴이 반복되므로 장르 팔레트보다 충돌 확률이 구조적으로 높다.**
3. **생성한 초안을 앱이 스스로 검증할 수 없다 — 실측 확정 사실.** 응답기는
   `DataPool/Sequences/<n>/<m>`에서 `name`/`class`/`i`(+ 중첩 `Part`)만 반환하고 **커맨드·CueFade·
   TrigType 등 프로퍼티는 어떤 형태로도 반환하지 않는다**(`SPEC-COPILOT-EXECREF-001/design.md:167`
   라이브 실측). 검증은 **큐의 존재와 이름** 수준이며, 그 한계를 결과에 명시해야 한다.

---

## B. 요구사항 (GEARS)

### B.1 섹션 입력

**REQ-SONGCUE-001** `[Event-driven]` **When** 사용자가 섹션 목록을 제공하면, the 시스템 **shall**
각 항목의 이름 · 시작 시각 · 입력 순서를 파싱해 구조화된 섹션 목록으로 만든다. 시각은 `mm:ss`,
`mm:ss.mmm`, 초 단위 실수를 받는다.

**REQ-SONGCUE-002** `[Unwanted]` **If** 시작 시각이 단조 증가하지 않거나 중복되면, **then** the
시스템 **shall** 입력을 거부하고 어느 항목이 왜 어긋났는지 보고한다 — **추정 보정하지 않는다.**
순서를 임의로 정렬하면 사용자가 의도한 구조가 아닌 큐리스트가 쇼파일에 남는다.

**REQ-SONGCUE-003** `[Ubiquitous]` The 시스템 **shall** 섹션 어휘를 `server/looks/matching.py`의
기존 테이블(`:99-121` 인트로/벌스/빌드/프리코러스/코러스/드랍 한영 매핑, `DYNAMICS_TERMS` `:92`)에서만
읽는다 — 본 SPEC은 어휘를 **재정의하지 않는다.** 재정의하면 한/영 어휘가 두 곳에 살고 그 순간
갈라진다(REQ-BUSKWIZ-002가 장르 별칭에서 세운 것과 같은 규율).

**REQ-SONGCUE-004** `[Where]` **Where** 섹션 이름이 기존 어휘에 없는 경우, the 시스템 **shall**
다이내믹스를 추정하지 않고 사용자에게 명시적 지정을 요구한다. 과신 추정의 결과는 사용자가 원한 적
없는 룩이 그 섹션에 박히는 것이다.

### B.2 섹션 → 룩 매핑

**REQ-SONGCUE-005** `[Ubiquitous]` The 시스템 **shall** 장르와 섹션 다이내믹스(정수 `1..5`,
`server/looks/schema.py:35-36`)로 룩을 선택하며, 후보 순회는 `looks_for_genre`
(`server/looks/busking.py:81`, 다이내믹스 오름차순 전순서)를 **재사용**한다.

**REQ-SONGCUE-006** `[Unwanted]` **If** 요구된 다이내믹스에 맞는 룩이 그 장르에 없으면, **then**
the 시스템 **shall** 가장 가까운 룩으로 승격하지 **않고** 그 섹션을 미매핑으로 보고한다.

### B.3 큐리스트 번들

**REQ-SONGCUE-007** `[Ubiquitous]` The 시스템 **shall** **곡 1개당 시퀀스 1개**, **섹션 1개당 큐 1개**를
생성한다. 큐 번호는 섹션 입력 순서대로 `1`부터 부여한다.

**REQ-SONGCUE-008** `[Ubiquitous]` The 시스템 **shall** 큐 이름을 **ASCII 문자열**로 발화하고, 한국어
표기는 표현 계층에서만 매핑한다(사전 확정 ③). 자산·스키마에 한국어 필드를 추가하지 않는다.
**발화 형태는 `Store Sequence <n> Cue <m> '<name>'`의 인라인 3번째 토큰으로 한정한다** — 독립 동사
`Label Cue`는 룰북 전체에서 **0건**이고 유일 등장이 큰따옴표를 쓴 mock 자산이라
(`server/measurement/corpus.yaml:69`, `server/rulebook/assets/v2.4.2/00_grammar.md:26-29`의 단일인용
규칙 위반) 근거로 쓸 수 없다. 따라서 **큐 이름의 사후 수정 경로는 존재하지 않으며**, 이름은 저장
시점에 확정된다.

**REQ-SONGCUE-009** `[Ubiquitous]` The 시스템 **shall** 시퀀스 번호를 **리그 조회 결과**에서 얻은
빈 번호로만 정한다. `DataPool/Sequences` 열거가 알려주는 것은 **존재하는** 시퀀스이므로, 빈 번호는
그 집합의 여집합에서 고른다.

**REQ-SONGCUE-010** `[Unwanted]` The 시스템 **shall not** `/Overwrite`·`/Remove`·`Delete` 계열을
발화한다. 이미 존재하는 시퀀스·큐를 덮는 것은 초안 생성기의 일이 아니다.

**REQ-SONGCUE-011** `[Ubiquitous]` The 시스템 **shall** 번들 결합 형상을 BUSKWIZ 결정 F에서
계승한다 — 목적지 커맨드는 **선두 1회**, 섹션 단위 `ClearAll`은 **전량 유지**
(`server/looks/busking.py:189` `_merge`). `server/orchestrator/tools.py`의 dedupe 규칙과
`_PROGRAMMER_STATE_COMMANDS`는 **무변경**이다.

**REQ-SONGCUE-012** `[Unwanted]` **If** 두 섹션의 값 라인이 문자열로 같아지면, **then** the 시스템
**shall** 뒤 섹션의 저장을 사유와 함께 건너뛴다 — BUSKWIZ 결정 H의 계승
(`server/looks/busking.py:230`, `:240`). 곡은 후렴이 반복되므로 이 경로는 장르 팔레트보다 자주 밟힌다.

### B.4 타이밍 — M0 라이브 게이트와 한 쌍

**REQ-SONGCUE-013** `[Where]` **Where** ASSUMPTION-20(타임코드 문법 존재)이 M0에서 **긍정** 실측된
경우, the 시스템 **shall** 타임코드 트랙을 생성한다. 그렇지 않으면 타임코드 대상 커맨드를 **0건**
발화하고 DESCOPE 사유를 기록한다.

**REQ-SONGCUE-014** `[Where]` **Where** ASSUMPTION-22(`Set Cue <m> Sequence <n> Property 'TrigType'`/
`'TrigTime'`)가 M0에서 긍정 실측된 경우, the 시스템 **shall** 섹션 간 자동 진행을 **M0가 실측한
토큰으로만** 발화한다. 부정이면 자동 진행 커맨드 0건이며 큐 시간은 `CueFade`로만 표현한다.
**룰북 주석의 토큰 메뉴를 실측 없이 발화하지 않는다** — 검증 예시의 리터럴은 `'Follow'`뿐이다.

**REQ-SONGCUE-015** `[Unwanted]` The 시스템 **shall not** MA2형 `/trig=` 문법을 발화한다
(`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:116-117`가 금지한다).

### B.5 보고 · 경로 · 경계

**REQ-SONGCUE-016** `[Ubiquitous]` The 시스템 **shall** 집계 + **섹션별** 2단 구조화 보고를 낸다 —
BUSKWIZ의 보고 형상(`server/looks/report.py`)에 **섹션 축**을 얹는다(어느 곡 섹션의 룩이 죽었는가).
집계만 내고 섹션별을 생략하는 것은 금지다.

**REQ-SONGCUE-017** `[Ubiquitous]` The 시스템 **shall** 생성 후 재조회로 **큐의 존재와 이름**을
확인하고, **큐 프로퍼티(CueFade · TrigType)는 응답기가 노출하지 않는다는 한계**를 결과에 명시한다
(`SPEC-COPILOT-EXECREF-001/design.md:167` 라이브 실측). 관측하지 않은 것을 관측했다고 보고하지 않는다.

> **v0.2.0 개정 주석.** 응답기 v1.5.0이 `prop` 동사를 추가해 **큐 프로퍼티를 읽는 경로가 생겼다.**
> 그럼에도 **본 요구의 한계 명시 의무는 폐지되지 않는다** — 재조회(상태 조회) 자체는 여전히 name·class·slot
> (+`cueNo`)만 반환하며 `CueFade`·`TrigType`을 노출하지 않는다. 따라서 결과 페이로드의
> `property_unobserved`(= `songcue_report.PROPERTY_UNOBSERVED_NOTE`)는 **재조회 경로의 한계**를 계속 명시하고,
> `prop`으로 읽은 값이 있다면 그것은 **별개 경로의 관측**으로 구분해 보고한다. 두 경로를 뭉뚱그려
> "확인했다"고 적는 것은 여전히 금지다.

**REQ-SONGCUE-018** `[Ubiquitous]` The 시스템 **shall** 번들을 기존 `run_commands` → `gate.screen()`
경로로**만** 실행한다. 신규 툴은 그 경로의 **호출자**이며 제2 실행 표면이 아니다
(`server/orchestrator/tools.py:693`, `:817` 두 `@MX:ANCHOR` 두 앵커의 선례).

**REQ-SONGCUE-019** `[Ubiquitous]` The 신규 툴 **shall** 기존 등록 관례(`TOOL_NAMES` ·
`definitions` · `handlers` 3곳)를 그대로 따르고, 리그 데이터를 모델 인자로 받지 않는다.

**REQ-SONGCUE-020** `[Unwanted]` The 시스템 **shall not** 시퀀스 번호 · 큐 번호 · 그룹 · 풀 · 슬롯 ·
FID를 정적 데이터에 넣는다. 모든 번호는 리그 조회 결과 객체의 필드 또는 섹션 입력 순서에서 온다.

**REQ-SONGCUE-021** `[Unwanted]` The 본 SPEC **shall not** 아래 §C PRESERVE 목록의 파일을 변경한다.
특히 `server/looks/matching.py`와 `server/looks/instantiate.py`의 diff가 빈 출력이어야 한다 —
본 SPEC이 그 계층을 **재사용하되 고치지 않는다**는 형상의 기계적 증거이며, diff가 생기면
"섹션 축을 바깥에서 감싼다"는 설계가 성립하지 않았다는 뜻이다(BUSKWIZ 결정 E의 반증 장치 계승).

> **v0.2.0 개정 주석.** §C PRESERVE 목록에서 `console/lua/**`가 **제외**되었으므로 본 요구의 판정 대상도
> 그만큼 좁아진다. 위에 이름을 든 `matching.py`·`instantiate.py`를 포함한 **나머지 전 항목의 diff 빈 출력 요구는
> 그대로**이며, 실제로 M6가 게이트 비공허성까지 증명했다(`progress.md` §E.2 M6 절 — PRESERVE 파일에 공백을
> 주입한 커밋을 게이트가 잡아냈고 되돌렸다). 개정 사유는 §C의 개정 블록과 §F 개정 절에 있다.

---

## C. 환경 및 전제

### 측정된 기준선

전체 스위트 수는 **각 마일스톤이 착수 직전 직접 실측**하며 **이월 인용을 금지**한다. 본 SPEC 착수
시점의 수는 run-phase 킥오프에서 기록한다(BUSKWIZ가 착수 SHA에서 직접 재어 6단계 산술을 닫은
선례를 따른다 — `SPEC-COPILOT-BUSKWIZ-001/progress.md` §E.3 `arithmetic_closes`).

### 미검증 전제 (ASSUMPTION)

전제 번호는 **본 SPEC이 새로 1번부터 매기지 않고** BUSKWIZ가 소진한 19 다음을 잇는다
(`SPEC-COPILOT-BUSKWIZ-001/progress.md:37-39`의 규율 계승 — 같은 기반 위의 SPEC들이 서로 다른
ASSUMPTION-3을 갖는 상황을 만들지 않는다).

- **ASSUMPTION-20** — **타임코드 오브젝트·문법이 존재하는가.** 현재 등급 **T5(저장소 전체 0건)**.
  룰북 5파일 · `server/**` · `console/lua/**` · `.moai/**` 전량 무매치. 부정이면 REQ-SONGCUE-013 DESCOPE.
- **ASSUMPTION-21** — **같은 시퀀스에 `Cue 2` 이상을 추가할 수 있는가**
  (`Store Sequence <n> Cue <m> '<name>' CueFade <t> /Merge`). 현재 등급 **T2** — 룰북
  `31_choreography_patterns.md:55`에 있고 그 파일은 라이브 선언(`:7`)을 갖지만, **감사 로그에서
  `Cue <m≥2>`의 라이브 실행이 0건**이며 등장하는 모든 `Cue 12` 계열은 `offline mock execution`이다
  (`.moai/state/verify/m6b1/audit-full/audit-20260717.jsonl:71-73`).
  **이것은 DESCOPE 대상이 아니라 저작을 막는 블로킹 게이트다** — 부정이면 "곡 1개 = 시퀀스 1개"라는
  산출물 정의(REQ-SONGCUE-007) 자체가 성립하지 않는다. BUSKWIZ의 ASSUMPTION-18이 M2를 기술적으로 막았던
  것과 같은 성격이다.
- **ASSUMPTION-22** — **큐 자동 진행 프로퍼티가 수용되는가**
  (`Set Cue <m> Sequence <n> Property 'TrigType' <token>` / `'TrigTime' <t>`). 현재 등급 **T2**,
  라이브 실행 0건(`31_choreography_patterns.md:111-112`).
  **리터럴 주의 — 룰북이 예시로 쓴 검증 형태의 토큰은 `'Follow'` 하나다**
  (`31_choreography_patterns.md:111`). 같은 줄 주석의 `Go / Time / Follow / Sound / BPM`은
  **토큰 메뉴이지 검증된 리터럴이 아니다.** 곡 섹션 타이밍이 필요한 것은 `'Time'`인데 그 토큰은
  주석에서만 왔으므로, M0는 `'Follow'`와 `'Time'`을 **각각 따로 재고 결과를 구분해 기록한다.**
  대문자 고정 규칙도 룰북이 명시한다(`:115`). 부정이면 REQ-SONGCUE-014 DESCOPE.
- **ASSUMPTION-23** — **빈 시퀀스 번호를 식별할 수 있는가.** `DataPool/Sequences` 열거는
  **존재하는** 시퀀스만 준다(라이브 관측: childCount 17 — `SPEC-COPILOT-BUSKWIZ-001/progress.md`
  정리 기록). BUSKWIZ가 익스큐터에서 데인 함정("비어 있음"과 "존재하지 않음"이 구별 불가)이
  시퀀스 축에서도 재발하는지 **반드시 실측한다.** 익스큐터와 달리 시퀀스는 주소 공간 상한이
  문제되지 않을 가능성이 있으나, **그 판단을 실측 없이 내리지 않는다.**
  **부정이면** 여집합을 신뢰할 수 없으므로 번호를 추측하지 않고 **거부한다**
  (AC-SONGCUE-008 구간 ②) — **동작 축소이지 블로킹이 아니다.** 저작을 막는 것은
  ASSUMPTION-21 하나뿐이다.
- **ASSUMPTION-24** — **한 곡 번들의 왕복이 실용 범위인가.** BUSKWIZ M0가 **87줄 번들 87/87
  성공 · 5.77s · 66.3ms/줄 · 누적 열화 없음**을 실측했다. 곡 1개(섹션 6~10개)의 번들 규모를 그
  실측에서 계산하고, 상한을 넘으면 M0에서 다시 잰다.

### PRESERVE — 무변경 대상

`server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `server/looks/library/` ·
`server/safety/**` · `server/web/preview.py` ·
`server/rulebook/assets/v2.4.2/**` · `server/orchestrator/tools.py`의
`_PROGRAMMER_STATE_COMMANDS`(`:234-238`)와 dedupe 실행 루프(`:524-569` — stop-on-first-failure `:535-543`, 이미 실행됨 분기 `:544-557`).

> **v0.2.0 개정 — `console/lua/**`를 PRESERVE에서 제외한다.** v0.1.0은 이 항목을 목록에 두고 아래 §D에서
> "응답기 확장은 별도 범위 결정"으로 닫았으나, **M0 라이브 프로브가 그 결정과 `plan.md`가 충돌함을 드러냈다** —
> `plan.md §B M0`은 ASSUMPTION-22가 GO면 `TrigTime` 의미론을 "**반드시 함께 측정할 것**"으로 요구하는데,
> 그것을 관측할 유일한 수단(응답기의 프로퍼티 읽기)이 바로 이 PRESERVE 항목에 막혀 있었다. 두 문서 중 하나는
> 반드시 어긋나며, **오케스트레이터가 측정을 택했다**(승인 기록: `progress.md` §F). 개정 범위는
> `console/lua/**` **한 항목뿐**이고 나머지 PRESERVE 항목은 그대로다 — 실측으로 확인했다(§F 개정 절).

`server/looks/busking.py`와 `server/looks/report.py`는 **재사용하되 확장 가능**하다 — 다만 BUSKWIZ의
테스트가 그 계약을 고정하고 있으므로 파괴적 변경은 즉시 회귀로 드러난다.

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — 음원 자동 분석

구간 분할 · BPM · 에너지 곡선 추출, 오디오 의존성 도입(`librosa`/`essentia`), 파일 업로드 경로,
장시간 작업 진행률·취소 프로토콜 전부. 사용자 확정 ①. **별도 SPEC.**

### Out of Scope — 프리셋 생성

본 SPEC의 산출물은 **큐**다. 프리셋 팔레트는 BUSKWIZ의 산출물이며, 큐가 프리셋을 참조하게 만드는
문법(`Assign Preset … At Cue` 계열)은 저장소 근거 **0건**이다. 큐는 프로그래머 상태를 직접 캡처한다.

### Out of Scope — 익스큐터 바인딩 · 페이지 저작

BUSKWIZ M0가 ASSUMPTION-16/17/19를 **전부 DESCOPE**로 판정했고 그 판정은 유효하다
(`SPEC-COPILOT-BUSKWIZ-001/progress.md:197-202`). 본 SPEC은 그 축을 다시 열지 않는다. 생성한
시퀀스를 익스큐터에 얹는 것은 후속 SPEC의 일이다.

### ~~Out of Scope~~ → **In Scope (v0.2.0 개정) — 콘솔측 Lua 응답기 확장**

**v0.1.0 원문(동결)**: "큐 프로퍼티를 읽으려면 응답기 확장이 필요하지만(`SPEC-COPILOT-EXECREF-001/design.md:167`),
`console/lua/**`는 PRESERVE다. REQ-SONGCUE-017이 그 한계를 **명시**하는 것으로 처리하며, 응답기 확장은
그 자체로 별도 범위 결정이다(`SPEC-COPILOT-LOOKLIB-001/spec.md:213-215`의 선례)."

**개정 사유** — 원문이 예견한 "별도 범위 결정"을 **오케스트레이터가 내렸고 사용자가 승인했다**(2026-07-29).
원문은 관측을 포기하고 한계를 명시하는 쪽을 택했으나, 같은 SPEC의 `plan.md §B M0`이 ASSUMPTION-22 GO 시
`TrigTime` 의미론을 **반드시 측정하라**고 요구한다. M0 실측에서 ASSUMPTION-22는 GO로 나왔고, 그 순간 두 지시는
동시에 만족될 수 없게 되었다 — 상태 조회는 name·class·slot만 주고 `List`·`Get`은 `OK`만 돌려주므로
**응답기를 고치지 않고는 그 값을 볼 방법이 없다.**

**개정 내용**: 응답기 확장을 본 SPEC 범위에 포함한다. 확장은 **가산적**이며 기존 동사·필드의 의미를 바꾸지 않는다.

- 신규 동사 `prop <id> <object-path> <PropertyName>` → `kind="prop"` 응답의 `value`로 실값 반환. 못 읽으면 `ok=false`.
- Cue 자식에 `cueNo`(실제 큐 번호) 추가. **기존 `i`(나열 위치)의 의미는 불변**이며 다른 SPEC의 소비자를 깨지 않는다.
  큐 번호를 확실히 얻지 못하면 **필드를 생략한다**(추측 금지 — `copilot_responder.lua`의 기존 slot 규율과 동형).
- 응답기 버전 `1.4.1` → `1.5.0`.

**대가와 그 처리**: 이 확장이 없었다면 REQ-SONGCUE-017의 한계 명시로 끝났을 것이다. 확장 이후에도
**그 한계 명시는 유지된다**(아래 REQ-SONGCUE-017 개정) — 상태 조회의 한계는 그대로이고 `prop`은 별개 경로이므로,
"관측하지 않은 것을 보고하지 않는다"는 규율은 약해지지 않는다.

### Out of Scope — dedupe 규칙 개정

`server/orchestrator/tools.py`의 dedupe 블록과 면제 집합은 `run_commands`를 쓰는 **모든** 소비자가
공유한다. 본 SPEC 하나를 위해 전역 실행 의미론을 바꾸지 않는다(BUSKWIZ 결정 F의 계승 —
`SPEC-COPILOT-BUSKWIZ-001/spec.md:156-158`).

### Out of Scope — 재생 · 섹션 점프

생성한 큐리스트를 **돌리는 것**(`Go+`/`Goto Cue <m> Sequence <n>`)은 본 SPEC의 산출물이 아니다.
`Goto Cue`는 안전 게이트가 참조를 추출하지 못해 **보류**된다 — `server/safety/classify.py:44`의
`RECOGNIZED_REFERENCE_TYPES`에 `Cue`가 없고, 그 결과 `server/safety/expand.py`가 본문을 얻지 못해
보류로 떨어진다(회귀 테스트 `server/tests/test_safety_classify.py:114`가 `Goto Cue 3` → 참조 `None`을
고정하며, 과보류임을 인정한 기록이 `SPEC-COPILOT-MVP-001/progress.md:215`에 있다).
즉 섹션 점프는 **문법 문제가 아니라 게이트 참조 인식 확장 과제**이고, 그 확장은 `server/safety/**`가
PRESERVE인 본 SPEC의 범위 밖이다. 후속 SPEC으로 **이관**한다(예약하지 않는다 — 본 SPEC은 그쪽에
아무 형상도 남기지 않는다).

### Out of Scope — 큐 편집 · 재생성

생성한 초안의 부분 수정, 큐 삭제·재배열, 소수 큐 번호 삽입(`Cue 1.5`)은 v1 범위 밖이다.
초안은 **한 번 생성하고 사람이 콘솔에서 고친다.**

---

## E. 참조 구현

| 무엇 | 어디 | 왜 |
|---|---|---|
| 섹션 어휘 · 다이내믹스 양자화 | `server/looks/matching.py:92`(정의), `:94-130`(항목 전량) | REQ-SONGCUE-003이 재정의를 금지하는 그 표. `:99-121`은 인트로~드랍 **열거 구간 한정**이며 `:94-98`(앰비언트 계열)·`:122-130`(드랍~`finale`)이 그 밖에 있다 |
| 룩 후보 전순서 | `server/looks/busking.py:81` `looks_for_genre` | REQ-SONGCUE-005의 재사용 대상 |
| 슬롯 원장 (frozen을 바깥에서 감싸는 형상) | `server/looks/busking.py:158` `_advance` | 하드 결함 1의 시간축 판본이 같은 형상을 쓴다 |
| 번들 결합 (목적지 선두 1회) | `server/looks/busking.py:189` `_merge` | REQ-SONGCUE-011 |
| 값 라인 충돌 가드 | `server/looks/busking.py:230`, `:240` | REQ-SONGCUE-012 |
| 2단 보고 · 한국어 표현 계층 | `server/looks/report.py:63`, `:74`, `:205`, `:278` | REQ-SONGCUE-008 · REQ-SONGCUE-016 |
| 큐 저작 문법 (T1 등급) | `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:50`, `:71` | 감사 로그 실행 기록 있음 — `server/audit_logs/audit-20260719.jsonl:186`, `audit-20260726.jsonl:327` |
| 큐 자동 진행 (T2 등급) | 같은 파일 `:111-112`, 대문자 규칙 `:115` | ASSUMPTION-22의 프로브 대상. 검증 예시 토큰은 `'Follow'` 하나 |
| 시퀀스 본문 조회 경로 | `server/safety/console.py:399` `DataPool/Sequences/{ref}` | REQ-SONGCUE-017의 재조회 수단 |
| 큐 이름이 본문 라인이 되는 체인 | `server/safety/console.py:478-484` → `expand.py:106-112` → `grammar.py:20` | 사전 확정 ③의 근거 |
| 단일 실행 경로 앵커 | `server/orchestrator/tools.py:693`, `:817` 두 `@MX:ANCHOR` | REQ-SONGCUE-018 |
| 시퀀스 생성이 패널 핀에 연동됨 | `server/orchestrator/last_created.py:30` | 곡 1개 = 시퀀스 1개일 때만 정상 동작(스냅샷 최신 1건) |
