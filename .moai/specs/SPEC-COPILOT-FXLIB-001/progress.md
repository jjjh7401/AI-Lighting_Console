# SPEC-COPILOT-FXLIB-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 타 SPEC 아티팩트**에만 쓰고, **각 마일스톤 착수 직전 재실측**한다(plan-phase에서 이미 scout 인용 2건의 드리프트를 정정했다 — research.md §2/§4). 요구·인수 토큰은 슬러그 포함 완전형만(축약 0건). 근거 등급 `[코드]` · `[문서]` · `[실측]` · `[미확정]` — **`[실측]`은 라이브 콘솔 직접 관측만**이며, 룰북의 "validated live" 선언은 `[문서]`다.

## §0 인수인계 — 여기서 시작한다 (2026-07-31)

### 한 문단

**무엇**: 이펙트(시간축 움직임) 어휘 계층 — LOOKLIB(정지 화면)의 자매편. 페이저+MAtricks+원형 조합의 폐쇄 패턴 어휘(무조건 4종 + M0 게이트 2종)를 `server/fx/` 신규 패키지에 세우고, 자연어 매칭(`find_fx`)과 시퀀스+큐 인스턴스화(`instantiate_fx`)를 기존 `run_commands`→`gate.screen()` 경로로만 배선한다.
**상태**: **plan-phase 완료 + plan-audit 1회차 처리 + M0 라이브 프로브 완료 + M0 폴드인 완료(v0.2.0) + M1 완료.** `status: in-progress`(M1 커밋에서 전환). REQ **22** · AC **23** · ASSUMPTION **5(36~40)** · clarification 마커 **0** · 라이브 세션 2회(M0 완료 · M7 대기). 다음 단계 = **M2·M3·M4**(M1 완료로 병렬 가능 — plan.md §F). M0가 바꾼 것 한 줄: **페이저는 2스텝 이상을 요구하므로 전 패턴이 스텝 쌍을 내야 하고, 이펙트 효과는 기계로 검증되지 않는다**(§E.2).

### 읽는 순서

1. **§E.2 (M0 기록)** — 여기가 지금 가장 중요한 절이다. 확립된 스텝 문법 + 증거 채널 부정 + 귀결 3건.
2. `design.md` **§2.1(스텝 축 형상 계약)** · **§4(번들 형상 — v0.2.0 전면 개정)** · **§5(값 라인 가드 — 등급 상승·주장 철회)** — 왜 그런 형상인지의 정본
3. `spec.md` §A(개요·사전 확정 ①~④·패턴 표) → §C(**ASSUMPTION-36~40** + M0 판정) → §D(제외 13항)
4. `plan.md` §A.2(차단 표 + M0 판정) → §A.4(결정 **A~I**) → §B(M0~M7)
5. `acceptance.md` §C.0/§C.0a(역추적·배정 — 합 **23**·중복 0·누락 0)
6. `research.md` — 근거 등급과 드리프트 정정 기록

### 함정 (다음 소유자가 알아야 할 것)

1. **M0는 게이트 미경유(bridge 직결)** — 감사 로그가 없다. 감사 로그 대조는 M7의 몫이다.
2. **`Cmd` 접수 `ok`는 효과 증거가 아니다** — 각 프로브 축에서 날조 대조군 1발을 먼저 발화해 `ok`의 변별력을 확립한 뒤에만 증거로 쓴다.
3. **값 라인 dedupe는 지시 턴 경계(instruction-scoped)다** — `executed_ok`가 툴 호출을 넘어 축적된다(runner.py:216). 면제는 `Clear`/`ClearAll`/bare 선택 3종뿐(tools.py:283-287). 중복 값 라인은 조용히 `skipped_already_executed`로 탈락하고 Store는 실행된다 — **같은 지시 턴에서 같은 패턴을 두 그룹에 얹는 흐름이 정확히 이 함정이다**(2번째 번들 값 라인 전량 접힘 → 빈 큐 무음 성공). dedupe 개정은 기각 선례 — 번들 내는 형상+가드, 교차 호출은 outcome 검출로 회피(REQ-FXLIB-011 (a)(b)).
4. **기존 시퀀스 번호 무플래그 Store는 "Not allowed"로 거부된다**(안전 방향이지만 계획 경로가 아님). 신규 번호는 재조회 실측, truncated=참이면 자동 배정 거부.
5. **"39/39" 인용 금지** — 그 수치는 리포지토리에 없다(전수 grep 0건).
6. **Speed 단위 미확정** — 룰북 자신이 BPM/Hz/sec를 병기(`:70`). ASSUMPTION-38.
7. **OVERLAP 정본은 다른 브랜치**(`feature/SPEC-COPILOT-OVERLAP-001`) — 본 트리에 그 SPEC 디렉터리가 없는 것은 정상이다.
8. **줄 앵커는 착수 직전 재실측** — plan-phase에서 이미 2건 드리프트를 잡았다.
9. **`server/looks/**`는 PRESERVE** — 읽기 import만. 수정하고 싶어지면 그건 설계 오류 신호다(design.md AP-4).
10. **스텝 축 없이는 페이저가 안 생긴다** (M0) — `Phase`/`Speed`/`Relative`는 **변형** 커맨드다. `Attribute 'X' At Step N`은 **금지 형태**(`ok:true`인데 효과 없음). 그리고 `Step 2` 라인은 dedupe 면제가 아니어서 **같은 지시 턴의 2번째 인스턴스화는 접힌다** — v1은 지시 턴당 1회가 운용 경계다(design.md §5).
11. **효과는 기계로 확인할 수 없다** (M0 측정된 경계) — 큐 내용·프로퍼티·픽스처 실시간 값 어느 쪽도 안 읽히고 빈 큐와 구별 불가다. 형상 결함은 런타임에서 **아무 신호도 내지 않는다** → 테스트와 로더 검증이 유일한 그물이다. `ok`를 성공으로 읽는 순간 이 SPEC은 실패한다.
12. **v0.1.0 번들 형상 인용 금지** — design.md §4는 v0.2.0에서 전면 교체됐다. 옛 형상(값 라인 1개 + Phase + Speed)은 M0가 3회 발화해 모션 0을 확인한 **반례**다.

### 기계 확인 (인수인계 무결성)

```bash
git branch --show-current                      # → feature/SPEC-COPILOT-FXLIB-001
ls .moai/specs/SPEC-COPILOT-FXLIB-001/         # → 6파일 (spec/plan/acceptance/design/research/progress)
grep -c "REQ-FXLIB-" .moai/specs/SPEC-COPILOT-FXLIB-001/spec.md      # ≥ 22
grep -c "^### AC-FXLIB-" .moai/specs/SPEC-COPILOT-FXLIB-001/acceptance.md  # = 23
grep -cE "ASSUMPTION-(3[6-9]|40)" .moai/specs/SPEC-COPILOT-FXLIB-001/spec.md  # ≥ 5
grep -c "Step 2" .moai/specs/SPEC-COPILOT-FXLIB-001/design.md        # ≥ 3 (§4 번들 3종 전부 스텝 쌍)
uv run pytest server/tests/ -q                 # 킥오프 baseline — 직접 실측(이월 금지)
```

### 다음 소유자 킥오프 킷

- **M1 착수 준비물**: `design.md §2.1`(스텝 축 형상 계약 — 정본) + `plan.md §B M1`(로더 검증 4종 + 뮤테이션 4종). 착수 직전 baseline(`uv run pytest server/tests/ -q`) 직접 실측.
- **재감사(2회차)가 볼 곳**: ① 1회차 지적 1~11의 델타, ② **M0 폴드인 델타** — 스텝 축이 스키마·번들·AC에 일관되게 반영됐는가, "번들 내 중복이 구조적으로 없다"의 철회가 전 표면에서 정합한가(design.md §5 · plan.md 결정 E · acceptance.md AC-009), ASSUMPTION-40의 게이트가 부정 비용을 정말 Pan/Tilt 4종으로 한정하는가, 리포트 문면의 **무조건성**이 조건부 잔재 없이 반영됐는가.
- **Kickoff 결정 없음**: 결정 **A~I** 전부 해소, clarification 0, 승인 대기 0 — 재질의할 것이 없다.

## Plan-phase log

### v0.1.0 (최초 작성 — 2026-07-31)

- 아티팩트 6종 동시 생성. 출처: 사용자 지시 격차 분석(제안서 항목 아님 — 전수 grep 재확인, research.md §1).
- 사용자 사전 확정 4건 반영(어휘 범위 / 시퀀스+큐 저장 / 라이브 2회 / 브랜치). clarification 마커 0건으로 닫힘.
- 조사: 병렬 read-only scout 3개 + 코디네이터 직접 재확인. 정정 2건 — `matricks` 재조회 경로 `tools.py:126→:125`, dedupe 인용 `:227-237→:241-293(면제)/:603-609(판정)`. 무드표·발명 금지 앵커도 LOOKLIB 인용 대비 드리프트 확인(research.md §2).
- SPEC ID 사전 검증: `SPEC-COPILOT-FXLIB-001` — 정규식 분해 SPEC ✓ | COPILOT ✓ | FXLIB ✓ | 001 ✓ → PASS (Bash 실행 검증).

### plan-audit 1회차 — FAIL 0.84 → 지적 11건 전건 처리 (2026-07-31)

원문: `.moai/reports/plan-audit/SPEC-COPILOT-FXLIB-001-audit-1.md`(로컬 아티팩트 — 본 절이 추적되는 처리 기록이다). Tier L 문턱 0.85 대비 **0.84 — 수정-후-재감사형 FAIL**(범위·아키텍처 기각 아님). 사용자 확정 ①~④ 재개봉 불요. 필수 1~5 + 권고 6~11 **전건** 반영 — 전부 plan 아티팩트 편집, 코드 변경 0, debt 0.

| # | 등급 | 지적 | 처리 |
|---|---|---|---|
| 1 | **높음** | **dedupe 경계 오인** — 가드가 지키는 경계(번들 내)와 실제 경계(지시 턴 전체)가 다르다. `executed_ok`는 툴 호출을 넘어 축적(runner.py:216, tools.py:603-609 주석 "in a prior tool call") — 한 지시 턴에서 같은 패턴을 두 그룹에 얹으면 2번째 번들 값 라인 전량이 접히고 Store만 실행 → 빈 큐 무음 성공 | **닫힘** — REQ-FXLIB-011을 **경계 2중**으로 확장: (a) 번들 내 구성 시점 가드(기존) + (b) **교차 호출 outcome 검출**(비면제 `skipped_already_executed` 검출 시 성공 보고 금지 + 명시 실패; `context.executed_ok` 도달 가능 시 실행 전 거부로 강화 — M4/M5 실측). REQ-FXLIB-014 (b)에 `skipped_already_executed` 전파 + 성공 금지 + 불완전 큐 생성 가능성 명시. research.md §4 "in-bundle" → instruction-scoped 정정, design.md §5 위협 모형·검출 지점 개정, AC-FXLIB-009 (b)/AC-FXLIB-012 교차 호출 시나리오+뮤테이션(plan.md M4 ⑥) 추가 |
| 2 | 중간 | design.md §5 `_is_programmer_state` top-level 읽기 import는 **순환 import**(tools.py는 등록 시 fx를 import — :19-43 선례 방향) | **닫힘** — busking `_guard_collision`(busking.py:240-275) 선례 채택: 빌더가 자기 라인의 면제/비면제를 스스로 분류(tools import 0 — 판정 규칙 재정의가 아니라 자기 산출물 분류). 집합 동치는 `test_fx_boundary.py`가 assert(동기화 의무 명문화) |
| 3 | 중간 | AC-008/009 "패턴 6종" 고정이 ASSUMPTION-37 DESCOPE 분기(§A.3 유효 완료)와 모순 — DESCOPE에서 평가 불능 | **닫힘** — "무조건 4종 + ASSUMPTION-37 GO 시 6종" 조건부 문구로 정정(AC-008 검증·AC-009 본문) |
| 4 | 중간 | "줄당 66-73ms" 상한 73은 저장소 근거 0건(실측치 66.3/66.5/66.7) — 자기 원칙("저장소에 없는 수치 인용 금지") 위반 | **닫힘** — "~66ms/줄(66.3-66.7ms — BUSKWIZ progress.md:278-281)"로 정정. spec §C · plan §C.4 · research §4 3곳 |
| 5 | 중간 | AC-FXLIB-010/013/014/019 GEARS 문형 위반(shall 부재 명사구·주어 생략) — §C 자기 선언과 불일치 | **닫힘** — 전건 주어+shall 문형으로 재기술 |
| 6 | 낮음 | 판정 어휘 원출처 오귀속 — 정본은 PRECHK acceptance.md:289 + progress.md P1-2/P1-3(감사 신설), plan.md에는 `DESCOPE:`만 | **닫힘** — plan §B M0 · research §6 귀속 정정 |
| 7 | 낮음 | OVERLAP `spec.md:115` off-by-one(제목 :114, 본문 :116) + PRESERVE 열거 과대 귀속(OVERLAP 잠금은 looks 6파일+library/뿐 — busking/report 미포함) | **닫힘** — 앵커 :114-116으로, 귀속을 "OVERLAP 6파일+library/ 계승 + busking/report/songcue*는 본 SPEC 추가 잠금"으로 spec §A/§D/§E · plan §A.1/§A.4/§A.5 · design §1 · research §6 전 표면 재기술 |
| 8 | 낮음 | ":75-77 산문만·리터럴 없음" 과잉 단정 — `Step 2`/`Step 1 At Accel -100` 인라인 조각 실재 | **닫힘** — "완전한 번들급 커맨드 라인 리터럴 부재(조각만 실재 — 조합 문법 미검증)"로 정밀화. **게이트 결정 자체는 유지**(정확한 논거로 교체) |
| 9 | 낮음 | REQ-009 번호형 vs acceptance §D Edge 1 인용명형 불일치 | **닫힘** — v1 발화 = **번호형 단일**(라이브 검증 — instantiate.py:302-304; 인용명형은 [문서] 문법 유도라 미발화), 이름 그룹은 rig context 등재 번호로 변환 발화. REQ-009·§D Edge 1 양쪽 정합 |
| 10 | 낮음 | progress.md "제외 12항" 계수 오류(실제 H3 11개) | **닫힘** — 11로 정정 |
| 11 | 낮음 | REQ-FXLIB-017 본문 shall-not인데 [Ubiquitous] 태그 | **닫힘** — [Unwanted]로 전환 |

**처리 후 재측정** (grep 범위: 정본 문면 — 본 처리 절의 지적 인용은 제외): REQ 21 · AC 절 22 · 역추적 21/21 · 배정 합 22(중복 0·누락 0) **불변** · clarification 마커 0 · `66-73`/`73ms` 0건 · "제외 12항" 0건 · 무조건 "패턴 6종" 고정 표현 0건(조건부 문구만 잔존) · OVERLAP `:115` 단독 앵커 0건 · "산문만" 잔존 0건. 재감사(2회차)는 결함 1~11 델타 한정(감사 리포트 재감사 계약). **감사가 재검증하지 않은 상태다** — 1회차 정정이 새 불일치를 만들지 않았다는 증명은 2회차 델타 감사의 몫이다.

### v0.2.0 — M0 폴드인 (2026-07-31, 코드 변경 0, 커밋 없음)

M0 라이브 프로브(§E.2)의 판정을 plan 아티팩트에 반영했다. **M0가 열어 놓고 문서가 따라가지 못한 상태**를 닫는 작업이며, §E.2가 스스로 지목한 "귀결 3건"이 착수 조건이었다. M0 기록 자체는 여기서 재서술하지 않는다 — §E.2가 정본이다.

**무엇이 왜 바뀌었나** (전부 §E.2의 실측이 몰아붙인 것이다):

| # | 변경 | 유발한 M0 증거 |
|---|---|---|
| 1 | **번들 형상 전면 개정** — 전 패턴이 `<값>`→`Step 2`→`<값>` 스텝 쌍을 낸다. v0.1.0 예시 2종 폐기, M0 실측 Dimmer 형상을 §4.0 앵커로 신설 | 페이저는 2스텝 이상을 요구하고 `Relative`/`Phase`/`Speed`는 **변형** 커맨드다 — 옛 형상은 `ok:true` 전량에 모션 0(실패 3회) |
| 2 | **스키마에 스텝 축 필수화** — `steps`(길이 ≥ 2, attribute→값 매핑) + 로더 검증 4종. v0.1.0의 "다단 필드(선택적)"은 **철회** | 같은 실측. 스텝 없이는 어떤 엔트리도 페이저를 못 만든다 |
| 3 | **값 라인 가드 등급 상승 + 주장 철회** — "(attribute×동사)마다 1줄이라 번들 내 중복이 구조적으로 없다"는 v0.1.0 문장은 **거짓이 됐다**(한 패턴이 같은 attribute에 여러 줄). 가드 (a)·검출 (b)가 방어적 항목에서 상시 검사로 승격 | 스텝 값 라인(`At 100`/`At 0`)은 패턴 간 중복 가능성이 매우 높고, **`Step 2` 라인은 전 패턴 공통 + dedupe 면제 아님** → 같은 지시 턴 2회차는 다른 패턴이어도 접힌다. v1 운용 경계를 "지시 턴당 1회"로 명시 |
| 4 | **REQ-FXLIB-022 신설** [Unwanted] — `Attribute '<attr>' At Step <k>` 금지 + **AC-FXLIB-023** 신설(M4 배정, 라이브러리·번들 전수 스캔) | 그 형태는 `ok:true`를 받고 **효과가 없다**. M0 프로브 자신이 이 형태로 3회 실패했다 |
| 5 | **리포트 문면의 무조건화** — REQ-FXLIB-014 (c)의 "ASSUMPTION-36 판정 분기" 폐기, 성공 경로 포함 **모든** 리포트가 "효과는 기계로 확인 불가 — 사람 확인 필요"를 싣는다 | 증거 채널 부정이 **측정된 경계**로 확정(큐 트리 바닥·`property not readable`·빈 큐와 구별 불가·이펙트 전용 풀 없음) |
| 6 | **ASSUMPTION-40 신설** (M7 측정) — 스텝 형상의 Pan/Tilt 일반화 + `Relative`의 스텝 값 성립 여부 | M0의 관측은 **Dimmer 축에서만** 이뤄졌고 `Relative 30`은 1스텝(페이저 미성립) 문맥에서만 발화됐다 — 실측을 조용히 일반화하지 않기 위해 별도 항목으로 연다 |
| 7 | **결정 I 신설**(plan §A.4) — 스텝 축 필수 / `At Relative` 미발화 / Pan/Tilt는 M7 게이트 | M0가 **강제한 것**(측정)과 이 폴드인이 **선택한 것**(설계)을 분리해 남기기 위해 |
| 8 | ASSUMPTION-37/38/39 게이트 해소 반영 — `pulse`/`chase` 진입, Speed = **BPM**, MAtricks 재조회 가능. **잔여**: `Accel`/`Decel`은 효과 미관측(SKIP)이라 구간 3에 남고 v1 미사용 | 판정 4건 GO + SKIP 1건 |

**ASSUMPTION-40이 라이브 세션 3회차를 만들지 않는 이유**: 형상 게이트(결정 I)가 부정 비용을 **Pan/Tilt 패턴 4종의 효과**로 한정하고 스키마·로더·매칭·툴·리포트를 무영향으로 두므로, 별도 프로브를 사는 대신 M7에 배칭한다 — ASSUMPTION-38/39를 M0에 배칭했던 것과 같은 기준(**저작을 막지 않는 측정은 배칭한다**)이다. 사용자 확정 ③(라이브 2회)은 **불변**이다.

**변경 파일 4종**: `spec.md`(v0.1.0→v0.2.0) · `plan.md` · `acceptance.md` · `design.md`. 코드 변경 0 · `research.md` 무변경(M0는 새 조사가 아니라 측정이며, 그 기록은 §E.2 + `.moai/reports/m0-probe/`가 소유한다).

**재측정 후 토큰**: REQ **22**(21+022) · AC 절 **23**(22+023) · 역추적 22/22 · 마일스톤 배정 합 **23**(중복 0·누락 0, M4가 5→6) · ASSUMPTION **5**(36~40) · clarification 마커 **0**. **감사가 재검증하지 않은 상태다** — 본 폴드인이 새 불일치를 만들지 않았다는 증명은 재감사(2회차)의 몫이며, 그 시선의 위치는 §0 킥오프 킷에 적어 두었다.

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-07-31
plan_amended_at: 2026-07-31            # M0 폴드인 (v0.2.0)
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
tokens: { req: 22, ac: 23, assumption: 5, clarification_markers: 0, live_sessions: 2 }
live_probe: { m0: complete, m7: pending }
commit_sha: pending-backfill
```

## §E.2 Run-phase Evidence

### M0 — 라이브 프로브 1회차 (2026-07-31, cycle_type=none, 코드 변경 0)

원문 전량: `.moai/reports/m0-probe/raw-log-01.md` (게이트 미경유 — 감사 로그 없음. 응답 원문 + 사용자 GUI 관측이 증거)

**세션 조건 (직접 실측, 이월 없음)**: onPC `127.0.0.1:8000` · 수신 9005 · `osc_slot` 2 · 응답기 **v1.5.0** · `DataPool/Sequences` `childCount 17` `truncated:false` · `DataPool/Groups` 4개(1·11·12·13) · `DataPool/MAtricks` 1개(11 `Wave`).

**날조 대조군 — 양 축 확립**: exec 축 `ZzzBogusVerb 1` → `ok:false "Illegal object"` / 양성 `List` → `ok:true "OK"`; state 축 `DataPool/ZzzBogusPath` → `ok:false "path segment not found"`. 이 세션에서 `ok`는 **구문 유효성**의 증거로 사용 가능하다(효과의 증거는 아니다).

#### 접두 행 (판정 4건)

```
GO:     ASSUMPTION-36 — 페이저 생성·저장 캡처 모두 성립(GUI 관측). 단 증거 채널은 부정 — 재조회 불가, 사람 관측이 유일 채널
GO:     ASSUMPTION-37 — 다단 스텝 문법 확립: <값> → `Step 2` → <값>. Accel/Decel 개별 효과는 미측정
GO:     ASSUMPTION-38 — Speed 단위 = BPM (GUI 표시 판독)
GO:     ASSUMPTION-39 — DataPool/MAtricks 재조회 가능 (childCount 1, truncated:false)
SKIP:   Accel/Decel 곡선 — ok:true이나 효과 미관측. 2스텝 페이저 위에 얹어 가감속을 GUI로 보면 갈린다
```

#### 확립된 페이저 생성 문법 (라이브 실측)

```
ClearAll
Group 11
Attribute 'Dimmer' At 100          # 스텝 1의 값
Step 2                             # 스텝 2 생성
Attribute 'Dimmer' At 0            # 스텝 2의 값 → 여기서 페이저가 성립
Attribute 'Dimmer' At Phase 0 Thru 360   # 선택 전체에 위상 팬 → 웨이브
Attribute 'Dimmer' At Speed 60           # BPM
Store Sequence <n> Cue 1 '<라벨>'
```

**GUI 관측(사용자)** — 프로그래머를 `ClearAll`로 비운 뒤 저장물만 발화한 상태에서 관측했으므로 관측 1건이 **생성**과 **저장 캡처**를 동시에 증명한다:
- 2스텝만: *"깜빡인다 / 움직인다"*
- 위상 확산 추가: *"파도처럼 순차적으로"* (일제 점멸 아님)

#### 정정 — 실패 3회의 원인은 콘솔이 아니라 프로브였다

본 세션 전반부의 페이저 생성 실패 3회는 **프로브가 스텝을 1개만 만든 결함**이었다. 페이저는 2개 이상의 스텝을 요구하며(MA Lighting 공식 문서), `Relative`·`Phase`·`Speed`는 **이미 존재하는** 페이저를 변형하는 커맨드이지 생성 커맨드가 아니다. 룰북 `31_choreography_patterns.md:73`이 이미 *"set a value, `Step 2`, set the next value"*라고 적어 두었고 프로브가 그 줄을 놓쳤다 — **룰북의 "validated" 선언은 옳았다.** 원문과 두 차례의 자기 정정은 `raw-log-01.md` §0 · §10.0에 보존했다.

`Attribute 'X' At Step N` 형태는 **잘못된 문법**이다(`ok:true`를 받으나 효과 없음) — 라이브러리·빌더에서 금지 형태로 명시할 것.

#### 증거 채널 — 저장된 큐의 내용은 기계로 읽히지 않는다

`state 'DataPool/Sequences/98/3/1'` → `Part`, `childCount 0`(트리 바닥). `prop` 은 `TrigType`→`"Go"`로 읽히나 `CueFade`·`Phase`·`Speed`는 `"property not readable"`. 결정적으로 **빈 프로그래머로 저장된 큐와 객체 트리상 구별되지 않는다**(양쪽 다 `Cue → Part(childCount 0)`).

#### 부수 — 무응답 ≠ 미실행

프로브 드라이버 결함으로 응답을 못 받던 구간에도 `Store`는 실제 실행됐다(`childCount` 17→18, 재조회 확인). 드라이버 결함의 원인은 `kind="result"`(응답기) vs `kind="exec"`(드라이버) 불일치였고, **콘솔 결함이 아니었다** — 1차 기록의 오진을 `raw-log-01.md` §0에 정정 보존했다.

#### 쇼파일 복구 — 확인됨

`Delete Sequence 98` · `Delete Sequence 99` 후 재조회 `childCount 17`, 번호 집합이 착수 시와 동일. 프로브 생성 오브젝트 잔여 **0건**.

#### 귀결 — M1 착수 가능, 단 design.md 개정이 선행한다

ASSUMPTION 4건 전부 `GO`이므로 run-phase 진행 조건은 충족됐다. 다만 M0가 **스텝 축을 새로 확립**했으므로 착수 전에 다음 3건을 반영해야 한다.

1. **번들 형상 개정 (design.md §4 · M4 선행 조건)** — 현재 형상(값 라인 1개 + Phase + Speed)으로는 페이저가 생기지 않는다. 패턴마다 `<값> → Step 2 → <값>` **스텝 쌍**을 담아야 한다. M4 착수 전 design.md 개정 필요.
2. **스키마에 스텝 축 추가 (M1)** — `server/fx/schema.py`가 스텝 값 배열을 표현해야 한다. 기존 계획의 페이저 축(phase_from/phase_to/speed/relative)만으로는 부족하다.
3. **값 라인 충돌 가드의 중요도 상승 (REQ-FXLIB-011)** — 스텝 값 라인은 `Attribute 'Dimmer' At 100` / `At 0` 처럼 **패턴 간 중복 가능성이 매우 높다.** 감사 F1이 지적한 교차 호출 접힘 위험이 실제로 커졌다.

**효과 검증은 사람 관측이 유일 채널이다.** 큐 내용은 트리·프로퍼티 어느 쪽으로도 읽히지 않고(내용 있는 큐와 빈 큐가 구별 불가), 픽스처 실시간 값도 읽히지 않으며, MA3는 페이저를 별도 풀에 두지 않는다. 리포트 문면은 "효과는 기계로 확인되지 않음 — 사람 확인 필요"를 명시해야 한다(plan M4의 NEGATIVE 분기와 동일 취급).

### M1 — FX 스키마 + 로더 (2026-07-31, cycle_type=tdd)

**착수 baseline (직접 실측, 이월 없음)**: `.venv/bin/python -m pytest server/tests/ -q` → **2758 passed, 5 skipped** (exit 0). 브랜치 `feature/SPEC-COPILOT-FXLIB-001`, 착수 HEAD `04cc79b`. M0 판정 접두 행 존재 확인(`GO:` 4행 + `SKIP:` 1행 — 위 §E.2).

**산출 (신규 4파일, 기존 파일 수정 0)**: `server/fx/__init__.py` · `server/fx/schema.py` · `server/fx/loader.py` · `server/tests/test_fx_schema.py`(86 tests).

#### AC-FXLIB-001 — PASS

| 항목 | 검증 | 결과 |
|---|---|---|
| 정상 라이브러리 로드 + 전 축 노출 | `pytest server/tests/test_fx_schema.py -q` | **86 passed** |
| 위반 종별 개별 명시 에러 (병합 0건) | 위반 1종 = 테스트 1건 규율 | 로더 거부 경로 전수 개별 테스트 |
| 스텝 축 4종 ①~④ | `TestStepAxisIsRequiredAndValidated` 13건 | 전건 PASS |
| `accel`/`decel` 정의 존재 + 직렬화 왕복 | `TestAccelDecelAreDefinedButGated` 5건 | 전건 PASS |
| 커버리지 | `--cov=server.fx` | **100%** (237/237 stmts, 기준 85%) |
| 경계 | `pytest server/tests/test_architecture.py -q` | **4 passed** |
| 전체 회귀 | `pytest server/tests/ -q` | **2844 passed, 5 skipped** (= 2758 + 86, 신규 실패 0) |
| ruff | `ruff check server/fx/ server/tests/test_fx_schema.py` | clean |

#### 뮤테이션 — 7건 전건 KILLED (plan §B M1 지정 4건 + 추가 3건)

| # | 주입 | 결과 | 죽인 테스트(대표) |
|---|---|---|---|
| ① | 미지 패턴 종별 통과 | KILLED | `test_an_unknown_pattern_kind_is_rejected` |
| ② | per-show 필드(group_number/sequence/executor) 스키마 추가 | KILLED | `test_a_smuggled_sequence_number_field_is_rejected` |
| ③ | `len(steps) >= 2` 검사 제거 | KILLED | `test_a_single_step_entry_is_rejected` |
| ④ | 스텝 값 동일성 검사 제거 | KILLED | `test_two_steps_carrying_the_same_value_for_one_attribute_are_rejected` |
| ⑤ (추가) | 스텝 간 attribute 집합 동일성 검사 제거 | KILLED | `test_steps_with_differing_attribute_sets_are_rejected` |
| ⑥ (추가) | 변형 축 단독 선언 거부 제거 | KILLED | `test_a_modifier_axis_declared_without_steps_is_rejected` |
| ⑦ (추가) | `server/fx/schema.py`에 `server.bridge` import 1줄 주입 | KILLED | `test_only_the_safety_gate_reaches_the_osc_send_surface` |

⑦은 plan.md §B M1의 *"`server/fx/` 생성 시점부터 `test_architecture.py` 전역 스캔에 자동 포섭된다"* 주장의 **비공허성 증명**이다 — 주장을 문서로 남기는 대신 실제로 죽는지 봤다. (AC-FXLIB-015의 정식 판정은 M6 몫이며 여기서 선점하지 않는다.)

뮤테이션 복원은 **스크래치패드 백업본에서** 수행했다 — M1 파일은 아직 untracked이므로 `git checkout --`는 복원이 아니라 **삭제**다. 복원 후 4파일 SHA1 대조로 원본 동일성을 확인했고, 각 회차 전후로 `__pycache__`를 지워 mutant 바이트코드 잔류를 배제했다.

#### 설계 결정 (M1이 선택한 것 — 측정이 강제한 것과 분리해 적는다)

1. **`대상 attribute` 축은 저장하지 않고 파생시킨다** — REQ-FXLIB-001이 축으로 열거하지만, 로더가 "전 스텝 attribute 집합 동일"을 보장하므로 별도 필드는 **스텝과 어긋날 수만 있는 사본**이다. `Fx.attributes`는 스텝 1의 저작 순서를 그대로 돌려주는 프로퍼티다(빌더가 쓸 순서가 그것이다).
2. **Pan/Tilt 값 범위는 ±360 "저작 봉투"** — 리포지토리에 `Attribute 'Pan' At <n>`의 단위(퍼센트/도)도 픽스처 한계도 **실측이 없다**. 퍼센트 판독과 도 판독 어느 쪽도 담을 만큼 넓게 두되 오타(2000)는 잡는다. 더 좁은 "콘솔 최대치"를 적는 것은 **저장소에 없는 수치를 인용하는 것**이라 본 SPEC 규율 위반이다.
3. **`speed` 상한 미설정** — 같은 이유. `speed > 0`(BPM, ASSUMPTION-38 GO)만 강제한다.
4. **`accel`/`decel`은 정의 + 로더 거부** — LOOKLIB `MovementSpec`은 "정의하되 발화 안 함"이고 로더는 값을 **받아준다**. FXLIB은 REQ-FXLIB-005의 "게이트 미충족 필드 사용" 거부 항목이 명시돼 있으므로 **한 단계 더 조인다**: 필드는 존재하고 직접 생성자로 값도 담기지만, 로더가 값을 거부해 미실측 어휘가 라이브러리에 들어올 수 없다.
5. **looks `KNOWN_ATTRIBUTES` 읽기 import는 테스트 계층에만** — design.md §3이 허용한 "읽기 import로 중복 비용 완화"를 **런타임 결합 없이** 얻는 방식. `server/fx/`는 stdlib + PyYAML만 import하고, 드리프트(오타 attribute)는 `test_fx_schema.py`의 부분집합 assert가 잡는다.
6. **`x_shuffle`은 카운트가 아니라 시드** — 룰북 `31_choreography_patterns.md`의 `Set Selection MAtricks 'XShuffle' 1234  # seeded random order` 리터럴을 착수 직전 재실측해 확인했다. 따라서 상한을 두지 않고 0을 허용한다(`x`/`x_wings`는 분할 카운트라 ≥ 1).

#### 미검증 (Gaps — M1이 확인하지 않은 것)

- **효과는 여전히 기계로 확인되지 않는다**(M0 측정된 경계). M1은 **형상·계약·거부 동작**만 검증했다. 스키마가 통과시킨 엔트리가 무대에서 실제로 움직이는지는 M7 사람 관측 몫이다.
- **Pan/Tilt 스텝 값의 단위·성립 여부는 ASSUMPTION-40**(M7). ②의 봉투는 저작을 막지 않기 위한 폭이지 콘솔 계약이 아니다.
- **번들 문자열은 M4 몫** — M1은 `Step <k>` 라인을 한 줄도 생성하지 않는다. 금지 형태 `At Step <k>`의 전수 차단(AC-FXLIB-023)도 M4/M2다.
- **`server/fx/library/`는 아직 없다** — `load_library_from_dir()`를 인자 없이 부르면 "not found"로 죽는다(M2가 자산을 놓을 때까지 정상 동작).
- **vitest 미실행** — M1은 서버측 순수 파이썬만 건드렸다. 전체 회귀(AC-FXLIB-020)는 M6 몫이다.

### M2·M3·M4 — 병렬 웨이브 1 (2026-08-01, cycle_type=tdd)

**오케스트레이션 형상**: plan §F가 분석한 파일 교집합 0을 근거로 3슬라이스 동시 스폰(PRECHK "병렬 웨이브 1" 선례). **커밋과 `progress.md` 쓰기는 오케스트레이터가 회수**했다 — 같은 브랜치 동시 커밋은 git 인덱스 경합, 같은 절 동시 쓰기는 3자 충돌이기 때문이다. 워커는 워킹 트리에 산출물만 남기고, 검증·커밋은 오케스트레이터가 슬라이스별로 수행했다. **`design.md` §2.1 스텝 축 계약을 세 프롬프트에 동일 문면으로 주입**했다(세 슬라이스가 이 계약에서 갈리면 M5 합류에서 깨진다).

착수 baseline: 세 워커가 각자 직접 실측 — 전부 `2844 passed, 5 skipped`(HEAD `8bd220f`). 최종 회귀 **`3119 passed, 5 skipped`** = 2844 + 36(M2) + 93(M3) + 146(M4). 산술 정합 확인, 신규 실패 0.

| 슬라이스 | 커밋 | 산출 | AC | 뮤테이션 |
|---|---|---|---|---|
| **M2** 라이브러리 | `35b8668` | `server/fx/library/{movement,dimmer,color}.yaml`(12엔트리) + `test_fx_library.py`(36) | 002/003/004 PASS (023 자산 절반) | 11/11 killed |
| **M3** 매칭 | `8162c46` | `server/fx/matching.py` + `test_fx_matching.py`(93) | 005/006/007 PASS | 10/10 killed |
| **M4** 빌더·가드·리포트 | `54887eb` | `server/fx/{instantiate,report}.py` + `test_fx_instantiate.py`(146) | 008/009/010/011/012/023 PASS | 16/16 killed |

커버리지: M3 `matching.py` 100% · M4 `instantiate.py`+`report.py` 100%. ruff clean 3슬라이스 전부. PRESERVE diff **0건**(`server/looks` · `server/safety` · `console/lua` · `server/rulebook` · `tools.py` · M1 `{schema,loader}.py`).

#### 오케스트레이터 직접 검증 — 워커가 할 수 없었던 이음매

워커는 각자 인메모리 픽스처만 썼으므로 **슬라이스 경계는 아무도 검증하지 않았다.** 오케스트레이터가 직접 잰 것:

1. **M2 자산 ↔ M1 로더**: `load_library_from_dir()`로 12엔트리 로드 확인, 패턴 6종 × 2, 금지 필드(`accel`/`decel`) 사용 0건.
2. **M2 자산 ↔ M3 매처**(실제 라이브러리 대상 한국어 질의):
   `'부드러운 웨이브'`→`wave-soft-rise` · `'빠른 체이스 돌려줘'`→`chase-club-rgb` · `'심장박동처럼 펄스'`→`pulse-beat` · `'좌우로 쓸어줘'`→`sweep-soft-wide` · `'대각선'`→`diagonal-soft-inphase` · `'아무말대잔치zzz'`→`no_match` · `''`→`empty_query`. **한국어 조사·어미가 실제 자산에 붙고, 없는 것은 지어내지 않는다.**
3. **M2 자산 ↔ M4 빌더 — `pulse-beat` 번들이 M0 실측 앵커와 바이트 동일**:
   ```
   ChangeDestination Root / ClearAll / Group 11
   Attribute 'Dimmer' At 100 / Step 2 / Attribute 'Dimmer' At 0
   Attribute 'Dimmer' At Phase 0 Thru 360 / Attribute 'Dimmer' At Speed 60
   Store Sequence 98 Cue 1 '<label>' / ClearAll
   ```
   이는 M0 §10.2에서 **라이브 발화해 "파도처럼 순차적으로"를 관측한 그 시퀀스**다. 효과가 기계 검증 불가한 이 SPEC에서 현 단계로 얻을 수 있는 가장 강한 증거다.
4. **전 12엔트리 번들 전수 스캔**: 금지 형태(`At Step` / `/Overwrite` / `At Relative`) **0건**, `ChangeDestination Root` 정확히 1회 아닌 엔트리 **없음**.
5. **circle ≠ diagonal 확인**: `circle-soft-ballyhoo` → `Pan At Phase 0` + `Tilt At Phase 90`; `diagonal-soft-inphase` → 둘 다 `Phase 0`.

#### M4가 스스로 잡은 교차 슬라이스 결함 1건

M4의 초기 구현은 위상 축을 attribute 개수로 배분해 **circle이 diagonal과 바이트 동일한 번들을 내고 있었다.** M2가 두 circle 엔트리를 `phase_from`만으로 저작하고 "90°는 필드가 아니라 **패턴 종별**이 담는다"고 기록했기 때문이다. M4가 M2의 커밋된 자산으로 자기 빌더를 돌려 발견했고, spec.md §A 패턴 표와 design.md §4.2가 형상을 지시하므로 **열린 결정이 아니라 자기 산출물의 결함으로 판단해 수정**했다 — 90°는 패턴 종별에서 파생하고, `circle`이 `phase_to`를 동시 선언하면 `CIRCLE_PHASE_CONFLICT`로 거부한다(두 메커니즘 중 하나를 조용히 고르지 않는다). **이 결함은 런타임에서 아무 신호도 내지 않았을 것이다**(효과 기계 검증 불가).

#### 후속에 넘기는 발견 3건

- **교차 호출 접힘은 design.md §5가 적은 것보다 한 줄 빠르다.** §5는 `Step 2`를 공유 라인으로 지목하지만, 실측하면 `ChangeDestination Root`도 전 번들 공통이며 면제 3종 밖이다 — 즉 같은 지시 턴의 2번째 인스턴스화는 **번들 첫 줄부터** 접힌다. SPEC의 "지시 턴당 1회" 경계를 **강화**하는 방향이며 `test_two_different_patterns_collide_on_the_lines_every_bundle_shares`가 고정한다. sync 시 §5에 한 줄 반영 대상.
- **패턴 이름만 대면 동점으로 폴백된다.** 패턴당 엔트리가 2개(느린 것/빠른 것)라 `'원형으로 돌려줘'`·`'클럽 느낌 빠르게'`가 `low_confidence`를 낸다. 설계 의도(확신 있는 오답보다 정직한 미스)대로지만, 실사용에서는 안 먹는 것처럼 보인다. **M5의 룰북 폴백 경로(REQ-FXLIB-008)가 이 케이스를 건지는지 M5에서 확인한다.**
- **`chase`의 다중 attribute 위상 배분**: R=0 / G=180 / B=360인데 360 ≡ 0이라 R과 B가 겹친다. SPEC이 `chase`의 위상 출력을 지시하지 않아 M4는 결정하지 않고 넘겼다. M5/M7 판단 대상.

#### 미검증 (Gaps)

- **효과** — 전 슬라이스의 단언이 문자열 수준이다. 무대에서 움직이는지는 M7 사람 관측뿐(M0가 확립한 경계).
- **Pan/Tilt 단위** — 여전히 ASSUMPTION-40. 라이브러리 크기값은 design.md §4.1/§4.2를 따랐을 뿐 도/퍼센트 어느 쪽이라는 주장이 아니다.
- **`test_fx_boundary.py`(M6) 미생성** — M4가 `_PROGRAMMER_STATE_COMMANDS` 집합 동치를 수동 대조해 현재 일치를 확인했으나, 그것을 고정하는 테스트는 M6 몫이다. 그 전까지 `tools.py`가 면제 집합을 넓히면 가드가 조용히 통과시킨다.
- **vitest 미실행** — 전 슬라이스가 서버측 파이썬만 건드렸다. AC-FXLIB-020은 M6.
- **시퀀스 번호 TOCTOU** — 재조회로 얻은 빈 번호를 이후 Store에서 쓴다. 그 사이 다른 오퍼레이터가 저장하는 경우는 콘솔의 무플래그 Store 거부가 마지막 방어선이다(SPEC 의도대로).

### M5 — 툴 표면 + 배선 (2026-08-01, cycle_type=tdd)

착수 baseline 직접 실측 `3119 passed, 5 skipped`(HEAD `76c809a`). 산출: `server/orchestrator/tools.py`(등록·핸들러만) + `server/tests/test_fx_tool.py`(78 tests). 커밋 `a3359b7` + `560c449`(SONGCUE 훅 위치 가드 동반 갱신).

| 항목 | 결과 |
|---|---|
| AC-FXLIB-013 `find_fx` 계약 | **PASS** — 닫힌 집합 등재, 폴백은 답(`is_error=False`), 룰북 byte-diff 0 |
| AC-FXLIB-014 `instantiate_fx` 계약 | **PASS** — 미등재 그룹 송신 0건 거부, 실행은 `run_commands` 소비만(게이트 1회 스크리닝 + AST 스캔) |
| AC-FXLIB-019 제공자 중립 | **PASS** — `server/fx/*.py` 어댑터 import 0건 |
| 전체 회귀 | **3197 passed, 5 skipped** (= 3119 + 78) |
| 뮤테이션 | **19/19 killed** |

**뮤테이션 1건이 처음 생존했고 그것이 테스트 결함이었다**: `bool`을 그룹 번호로 받아도 통과했다 — `True == 1`이고 기본 리그에 그룹 1이 없어 **리그 검사**가 대신 거부했기 때문. 그룹 1이 있는 리그로 옮기고 "타입 거부는 `groups` 키를 싣지 않는다"로 판별식을 세워 죽였다. **복원 규율 정정**: 1회차 하네스가 `tools.py`를 `git checkout --`로 복원해 미커밋 구현이 전량 삭제됐다(하네스 자체 assert가 즉시 포착). 판별 기준은 추적 여부가 아니라 **커밋 여부**다.

#### 지정 발견 3건 — 판정

1. **패턴 지명 폴백은 룰북 경로가 건지지 못한다.** 실측하니 보고보다 좁다 — `circle`·`chase` 2종에서만 동점이고 `pulse`·`wave`는 선택된다. 그러나 룰북의 폴백 문장(`31_choreography_patterns.md:233`)은 **`find_looks`를 지목**하고 룰북은 byte-diff 0 PRESERVE라 fx 폴백을 보내는 문장이 없다. → `find_fx` **설명이 그 다리를 단독으로 싣는다**: 한 단어 더 붙여 재질의(`'빠른 펄스로 해줘'` → 선택 성공, 실측), 그래도 폴백이면 무드표 movement 열로 설계. 두 문장 모두 뮤테이션 고정.
2. **교차 호출 접힘은 번들 첫 줄부터다** — `ChangeDestination Root`가 전 번들 공통이며 면제 밖. 툴은 `run_commands`가 `all_ok: true`를 줘도 실패로 보고한다(`Store`는 시퀀스 번호가 달라 유일하므로 실행되어 불완전한 큐가 남는다).
3. **`chase` 위상 축퇴는 실재 — 오케스트레이터가 수정**(아래).

### 수정 — `chase` 다중 attribute 위상 축퇴 (2026-08-01, 커밋 `bd451df`)

**발견**: M5 이음매에서 `chase-warm-cool`이 R=0 / G=180 / B=360을 내고 있었다. 위상은 순환하므로 **360 ≡ 0이고 R·B가 동상** — 3색 체이스가 2상 점멸로 렌더된다. 이는 콘솔 사실이 아니라 **우리 산술**이므로 측정 없이 판정 가능하다(위상의 정의).

**판단**: M5는 "M4 소유 파일이라 PRESERVE"로 넘겼고 M7 관측 목록 등재를 권고했으나, 오케스트레이터가 수정을 택했다 — 기계로 검출할 수단이 없어(효과 비검증) 라이브 세션 1회를 소모한 뒤에야 드러날 결함이고, 산술은 자명하기 때문이다.

**수정 범위 한정**: M5가 제안한 "항상 배타적 끝점"은 부분 호를 깨뜨린다(`0 Thru 180`에 3개면 0/90/180이 옳은데 배타면 180에 닿지 못한다). 따라서 **한 바퀴를 도는 호에만**(`span % 360 == 0`) 끝점을 배타로 둔다.

| 케이스 | 수정 전 | 수정 후 |
|---|---|---|
| 3 attr, 0→360 (닫힘) | 0 / 180 / **360 ≡ 0** | 0 / 120 / 240 |
| 3 attr, 0→180 (부분 호) | 0 / 90 / 180 | **불변** |
| 단일 attr 확산 | `Phase 0 Thru 360` | **불변** (M0 실측 리터럴) |
| circle · diagonal | 0/90 · 0/0 | **불변** |

**뮤테이션 검증**: 구 형태를 복원하면 2건 사망하고 **부분 호·단일 attribute 테스트는 통과 유지** — 수정이 닫히는 호에만 범위 한정됨을 증명한다. 복원 후 바이트 동일 확인. 전체 회귀 `3201 passed, 5 skipped`.

#### 오케스트레이터 직접 검증 (M5)

전체 회귀 `3197 passed` 재측정, 닫힌 툴 집합에 `find_fx`·`instantiate_fx` 등재 확인(총 11종).

#### 미검증 (Gaps)

- **효과** — 전 단언이 문자열·구조 수준. M7 사람 관측뿐.
- **`test_fx_boundary.py` 미생성(M6)** — `_PROGRAMMER_STATE_COMMANDS` 집합 동치는 아직 훅 가드의 보호 구간으로만 고정된다.
- **`get_rig_context` → `group` 인자 왕복 미검증** — M7 대상.
- **@MX ANCHOR 상한 초과** — `tools.py` 6건 vs `mx.yaml anchor_per_file: 3`. 착수 시점 이미 4건(모델 도달 툴마다 1건, 기존 관례). sync-phase MX 패스 판단 대상.

### M6 — 회귀 + 경계 전체 그린 (2026-08-01, 수정 0)

착수 baseline 직접 실측 `3201 passed, 5 skipped`(HEAD `4b9dbd2`). 산출: `server/tests/test_fx_boundary.py` **38건 신설, 구현 파일 무변경**. 커밋 `c927f60`.

| AC | 결과 |
|---|---|
| AC-FXLIB-015 단일 실행 경로 | **PASS** — `server/fx/**` 식별자 AST 스캔 offender 0(6모듈), 독스트링·주석에 금지 심볼을 전부 심은 **비판별 통제 2건이 설계대로 생존** |
| AC-FXLIB-016 LiveLock 강등 | **PASS** — 목이 아닌 **실물 게이트 + 활성 잠금**으로 실제 라이브러리 발화: 송신 0, 16줄 전량 `proposal`. 해제 대조군은 16줄 송신 |
| AC-FXLIB-017 안전 불변식 상속 | **PASS** — safety diff 0, `452 passed`, 실물 게이트가 **12엔트리 전량** 무보류 통과 |
| AC-FXLIB-018 룰북 무변경 | **PASS** — 자산 byte-diff 0, fx 툴 어휘 0건(결정 G — 툴 **설명**이 전담) |
| AC-FXLIB-020 전체 회귀 | **PASS** — pytest **3239**(= 3201 + 38) · vitest **223 / 13 files**(본 SPEC 최초 실행) |

**M4가 남긴 의무 이행 — dedupe 면제 집합 동치 고정.** 구문 축((패턴, 플래그) 양방향) + 행동 축(실제 12엔트리 번들 **153줄** + 반례 13종에서 두 술어 동일 판정). 비공허성 명시(면제 36 / 비면제 117). tools 측을 **넓히면 5건**, fx 측을 좁히면 3건 사망 — 넓히는 쪽이 위험한 방향이고 그것이 이 테스트의 존재 이유다.

**뮤테이션 16건 — 13 killed · 통제 2건 설계대로 생존 · 무효 3건은 교정 후 재실행하고 기록에 남겼다.** 무효 3건이 유익했다: ① 없는 심볼 import는 수집 단계에서 죽어 스캔이 돌지도 않았다(실심볼로 교정) ② **최상위** fx→tools import는 파이썬이 먼저 순환 `ImportError`를 냈다 — kill은 아니지만 M4 `@MX:ANCHOR`의 전제를 **논증에서 관측으로** 바꿨다. 실제로 착지할 형태인 **함수 지역 import**로 교정하니 스캔이 잡았다 ③ blacklist 엔트리 개명은 3자 접두 매칭 때문에 여전히 매칭돼 뮤테이션 자체가 무효였다.

**뮤테이션이 잡은 자기 테스트 결함 2건**: ① "제안됐다"를 이름에 건 테스트가 첫 줄·`Store` 존재만 봐서 **실제로 발화된 번들도 통과**시켰다(M5의 `is_error` 단독 단언과 같은 형태) — `status == proposal` + 송신 0을 합쳐 교정 ② 툴 어휘 테스트가 스키마 전체를 훑어 **툴 이름** 때문에 설명이 비어도 통과했다 — 설명 필드만 훑도록 좁힘.

#### @MX ANCHOR 상한 초과 — 판단: 기록, 판정은 sync-phase

`tools.py` ANCHOR **6건** vs `anchor_per_file: 3`. **착수 시점 이미 4건** — 본 SPEC 이전부터 초과였고 FXLIB이 2건을 더했다. 조치하지 않은 근거: M6은 수정 0이고, 프로토콜상 ANCHOR 강등 권한은 sync-phase 소유이며, **처방 자체가 여기서 축퇴한다** — "최저 fan_in부터 강등"인데 AST 실측 결과 6개 핸들러 전부 Load 참조 1·직접 호출 0으로 **동률**이다. 정직한 해석은 "6건 중 3건이 틀렸다"가 아니라 **모든 항목이 구조상 초크포인트인 툴 레지스트리 파일에 per-file 상한이 맞지 않는다**이고, 해소는 `mx.yaml` 소유자의 설정 결정이다.

### 수정 — LiveLock 강등은 답변이지 실패가 아니다 (2026-08-01, 커밋 `52d94de`)

**M6의 발견**: `instantiate_fx`만 잠금 강등을 `is_error=True`로 돌려주고 있었다. `prepare_busking`(`tools.py:1060-1064`, REQ-BUSKWIZ-014)과 `precheck_patch`(`:1579`)는 같은 사건을 `is_error=False`로 처리하며 주석이 이유를 명시한다 — **제안이 곧 산출물이고, `True`는 자기수정 루프를 먹여 같은 잠금에 다시 부딪히게 한다.**

**판단**: 오케스트레이터가 수정했다. AC-FXLIB-016은 어느 쪽이든 통과하므로 기계로는 안 잡히지만, **LiveLock이 켜지는 때가 바로 공연 중**이라 실패 양상이 구체적이고, 형제 툴 **둘**과 어긋난 쪽이 fx 하나다.

**범위 한정**: 잠금에만 적용한다. 교차 호출 충돌은 여전히 진짜 실패이고(불완전한 큐가 남는다) 다른 게이트 거부(`held` 등)도 모델이 행동해야 할 사건이므로 `is_error=True`를 유지한다.

M6가 "승인이 아니라 기록"으로 명시한 특성화 테스트 2건을 새 계약으로 갱신하고, **예외가 잠금에만 걸리는지 확인하는 `held` 대조 테스트를 신설**했다. **뮤테이션 양방향**: 예외 제거 → 2건 사망 / 예외를 모든 게이트 거부로 확대 → `held` 대조 테스트 사망. 전체 회귀 **3240 passed, 5 skipped**.

#### 오케스트레이터 직접 검증 (M6)

pytest `3239` + vitest `223 / 13 files` 재측정(수정 후 `3240`). 뮤테이션 앵커가 3곳(busking·prechk·fx 공통)이라 1회차가 적용되지 않은 것을 자체 assert가 포착 — fx 고유 문맥으로 재앵커해 재실행했다.

### M7 — 종단 라이브 검증 (2026-08-01, 실물 onPC, 코드 변경 0)

**세션 조건 (직접 실측)**: onPC `127.0.0.1:8000` · 수신 9005 · 응답기 **v1.5.0** · `DataPool/Sequences` 착수 `childCount 17`. 착수 baseline `3240 passed, 5 skipped`.

**M0와 결정적으로 다른 점**: M0는 bridge 직결이라 게이트를 경유하지 않았고 감사 로그가 없었다. M7은 **실물 게이트 스택**(`build_console_stack` → `build_toolset`)을 세워 **모델이 닿는 그 지점**(`registry.dispatch`)으로 진입했다. 하네스: `.moai/reports/m0-probe/fx_e2e.py`(BUSKWIZ `busking_e2e.py` 형상 계승; `server/tools/`에 두면 bridge-import 예외 목록에 걸리므로 리포트 디렉터리에 둔다).

#### 종단 1 — `pulse` (M0 앵커 먼저, 귀속 규율)

```
find_fx '심장박동처럼 펄스' → pulse-beat (fallback=false, total=1)
instantiate_fx pulse-beat group=11 → executed=true succeeded=true is_error=false
  ChangeDestination Root / ClearAll / Group 11
  Attribute 'Dimmer' At 100 / Step 2 / Attribute 'Dimmer' At 0
  Attribute 'Dimmer' At Phase 0 Thru 360 / Attribute 'Dimmer' At Speed 60
  Store Sequence 3 Cue 1 '박자 펄스' / ClearAll        ← 10줄 전량 executed_ok
```

**시퀀스 번호 3은 재조회 실측값**이다(하드코딩 아님 — 리그의 빈 번호를 측정해 채웠다).

**GUI 관측(사용자)**: 프로그래머를 비우고 `Go+ Sequence 3` → *"파도처럼 순차적으로"*. **앱이 자연어 질의로 실제 이펙트를 만들었다.**

#### 감사 로그 대조 — M0가 못 한 몫 (인수 조건)

`server/audit_logs/audit-20260801.jsonl` — **첫 종단(`pulse`) 직후 판독 시점에 18건**(인덱스 0~17; 이후 `sweep` 종단이 같은 파일에 이어 쓰므로 최종 개수는 더 크다). 번들 10줄이 **전량 개별 기록**됐다:

```
executed  ChangeDestination Root                  True
executed  ClearAll                                True
executed  Group 11                                True
executed  Attribute 'Dimmer' At 100               True
executed  Step 2                                  True
executed  Attribute 'Dimmer' At 0                 True
executed  Attribute 'Dimmer' At Phase 0 Thru 360  True
executed  Attribute 'Dimmer' At Speed 60          True
executed  Store Sequence 3 Cue 1 '박자 펄스'        True
executed  ClearAll                                True
```

리그 조회(`DataPool/Groups`·`DataPool/Sequences`)와 세션 백업(`SaveShow`)도 같은 로그에 남아 **1:1 송신↔감사 정합**이 확인된다.

**자기 정정 1건**: 처음에 `~/Library/Application Support/GrandMA3 Copilot/audit_logs/`를 보고 "오늘 자 로그 없음 → 게이트 미경유"로 판단할 뻔했다. 그 경로는 **패키지 앱(frozen)용**이고 개발 체크아웃은 `server/audit_logs/`에 쓴다(`resolve_runtime_audit_dir` 실측). **결론 전에 자기 하네스를 먼저 의심하는 규율이 세 번째로 값을 냈다**(M0 §0·§10.0에 이은 3회차).

#### 종단 2 — `sweep` (ASSUMPTION-40 판정)

```
find_fx '좌우로 쓸어줘' → sweep-soft-wide (fallback=false)
instantiate_fx sweep-soft-wide group=11 → executed=true succeeded=true
  ... Attribute 'Pan' At -30 / Step 2 / Attribute 'Pan' At 30
      Attribute 'Pan' At Phase 0 Thru 360 / Attribute 'Pan' At Speed 14
      Store Sequence 4 Cue 1 '부드러운 좌우 스윕'      ← 10줄 전량 executed_ok
```

**GUI 관측(사용자)**: *"좌우로 움직인다"* — **스텝 생성 형상이 Dimmer 밖에서도 성립한다.**

#### 접두 행

```
GO:     ASSUMPTION-40 — 스텝 생성 형상의 Pan/Tilt 일반화 성립. sweep(Pan 2스텝 -30↔30, 위상 확산, 14 BPM)이 GUI에서 좌우 이동 관측. 대조 순서 준수 — pulse(M0 앵커)를 먼저 발화해 파이프라인 생존을 확립한 뒤 측정했으므로, 부정이 나왔다면 attribute 일반화 실패로 귀속됐을 것이다
```

**M0 판정(ASSUMPTION-36~39)은 재측정하지 않았다**(§A.2 재측정 금지 규율). 어긋난 관측 **0건**.

#### 부수 관측 — 폴백이 실제로 작동한다

`'좌우로 부드럽게 쓸어줘'`는 sweep 2엔트리 동점으로 `low_confidence` 폴백을 냈고, 하네스가 **추측하지 않고 정지**했다. M5가 기록한 "패턴 지명 동점" 현상이 라이브에서 재현된 것이며, **설계된 정직한 미스가 실물에서도 그대로 동작함**을 보여준다. 한 단어를 덜어낸 `'좌우로 쓸어줘'`는 선택에 성공했다.

#### 리포트 문면 ↔ 실물 일치

```
[pulse] 시퀀스 3 큐 1 '박자 펄스' · 그룹 11 · 커맨드 10개 · 판정 전량 실행
  실행 10개 · 실패 0개 · 미실행 0개 · 접힘 0개
상세:
  패턴 pulse · 대상 Dimmer · 스텝 2단 / 속도 60 BPM
  ※ 이펙트 효과는 기계로 확인되지 않습니다 — 무대/GUI에서 사람이 직접 확인해야 합니다.
  ※ 재조회로 확인할 수 있는 것은 시퀀스·큐의 존재뿐입니다 — 그것은 효과의 증거가 아닙니다.
```

커맨드 수·시퀀스 번호·라벨·속도 단위(BPM) 전부 실물과 일치하고, **효과 한계 문면이 무조건 실린다**(REQ-FXLIB-014 (c)) — 실제로 이 세션에서 효과 판정은 사람 관측이 유일 채널이었다.

#### 쇼파일 복구 — 확인됨

`Off Sequence 4` · `ClearAll` · `Delete Sequence 3` · `Delete Sequence 4` 후 재조회 `childCount 17` — 착수 시와 동일. 잔여 **0건**.

#### AC-FXLIB-022 — **PASS**

매칭 → 번들 → 게이트 → **감사 로그** → GUI 종단이 실물에서 1회 성립했고, ASSUMPTION-40이 같은 세션에서 GO로 닫혔다.

#### 미검증 (Gaps)

- **효과의 기계 검증은 여전히 불가** — M0가 측정한 경계 그대로다. 본 세션의 두 판정 모두 사람 GUI 관측이다.
- **`wave`·`circle`·`diagonal`·`chase` 4패턴의 효과는 직접 관측하지 않았다** — ASSUMPTION-40은 "Pan/Tilt 축에서 스텝 형상이 성립하는가"를 `sweep` 1종으로 닫았고 plan이 요구한 것도 "Pan/Tilt 패턴 1종 이상"이다. 나머지는 같은 축·같은 형상의 파생이나 개별 관측은 없다.
- **`chase` 위상 수정(0/120/240)의 효과 미관측** — 수정은 산술로 판정했고 라이브 관측은 하지 않았다.
- **승인 채널 미발동** — fx 번들이 위험 분류에 걸리지 않아 승인 요청이 0건이었다(예상된 동작). 승인 경로 자체는 이 세션이 검증하지 않았다.

### sync-audit 1회차 — PASS-WITH-DEBT 0.915 · 지적 처리 (2026-08-01)

원문: `.moai/reports/sync-audit/SPEC-COPILOT-FXLIB-001-audit-1.md`. Functionality 0.96 · Security 0.97 · Craft 0.88 · Consistency 0.86 → **조화 평균 0.915**(Tier L 문턱 0.85). 치명 0 · 높음 0 · 중간 3 · 낮음 4. 감사자는 구현자 테스트를 쓰지 않고 **자기 하네스로 12엔트리 번들 전수 생성·스캔**, **실제 레지스트리로 교차 호출 가드 재현**, **AST + 런타임 전이 폐포 두 각도로 경계 검증**, **감사 로그 직접 판독**, **전 감사 로그 16파일로 라이브 세션 2회 확인**을 수행했다.

| # | 등급 | 지적 | 처리 |
|---|---|---|---|
| F1 | 중간 | **감사자 뮤테이션 24건 중 유일 생존** — 라이브러리 레벨 폐쇄 키 집합이 고정돼 있지 않다. `_LIBRARY_KEYS`에 `group_number`를 넣고 출하 자산에 실제 탑재해도 482건이 전부 통과한다. 두 방어가 함께 눈을 감았다: 스키마 테스트는 `"rig"`로 검사해 **미지 키 거부는 증명하나 멤버십을 고정 못 하고**, `PER_SHOW_PATTERN`은 키워드 뒤 숫자를 요구해 `Group 11`은 잡아도 **`group_number: 11`은 못 잡는다** | **닫힘** — 두 구멍을 각각 막았다: ① `test_the_library_level_key_set_is_exactly_these_two`(집합 동치 고정) ② `test_no_asset_declares_a_key_NAMED_after_a_per_show_binding`(YAML 키 **이름** 축 스캔, 임의 깊이). **감사자의 뮤테이션을 그대로 재현해 2건 사망 확인**, 복원 바이트 동일 |
| F2 | 중간 | design.md §5의 접힘 시작점이 `Step 2`로 적혀 있으나 실측은 첫 줄(`ChangeDestination Root`). 은폐는 아니나(3곳에 기록) 규범 문서가 부정확한 채 닫혔고 **승계 SPEC이 없다** | **이관 — 수취인 지명**(아래 §이관) |
| F3 | 중간 | @MX:ANCHOR 6 vs 상한 3. 진단(fan_in 동률로 처방 축퇴)은 타당하나 **"`mx.yaml` 소유자"는 역할명일 뿐 지명된 주체가 없어 아무도 집어들지 않는다** | **이관 — 수취인 지명**(아래 §이관) |
| F4 | 낮음 | 감사 로그 "18건"이 시점 의존 표기 | **닫힘** — "첫 종단 직후 판독 시점 기준(이후 `sweep`이 이어 씀)"으로 명시 |
| F5 | 낮음 | CHANGELOG "결함 5건" 표제가 코드 결함 3건 + 다항목 범주 2개를 한 수로 묶어 훑어보는 독자를 오도할 수 있다(본문은 정확) | **닫힘** — "코드 결함 3건(1~3) + 두 부류의 자기 정정(4~5)"으로 표제 분해 |
| F6 | 낮음 | 잔존 워크트리(`.claude/worktrees/nice-satoshi-f58b50`, DASHUI-001 시절)가 루트 vitest를 오염 | **이관 — 본 SPEC 범위 밖**(다른 SPEC의 산물이며 삭제는 그 SPEC 이력에 대한 판단이 필요하다). 본 SPEC의 vitest 정본 명령은 `npm --prefix ui run test`이고 감사자도 그 명령으로 223/13파일을 확인했다 |
| F7 | 낮음·범위 | "효과는 기계로 검증 불가"가 단정형이나 측정은 응답기 **5동사 표면**에 한정. `SaveShow` → 디스크 쇼파일 판독 경로는 열거되지도 배제되지도 않았다(`server/deploy/pack.py:16`에 쇼파일에서 소스를 발견한 독립 관측이 이미 있다). 감사자도 콘솔 없이 검증 불가하므로 **결함이 아니라 가설**로 제기 | **이관 — 가설로 기록**(아래 §이관). 사용자 대면 문면(`EFFECT_EVIDENCE_NOTICE`)은 **그대로 둔다** — 5동사 표면에서 참이고, 사람 확인을 요구하는 쪽이 안전 방향이다 |

#### 이관 — 수취인이 지명된 후속 항목 3건

감사자의 지적이 정확했다: "이관"만 적고 수취인을 안 적으면 부채가 증발한다. 아래는 **PR 본문에도 그대로 실어** 사용자가 보는 자리에 남긴다.

| # | 항목 | 수취인 · 착수 조건 | 비용 |
|---|---|---|---|
| 1 | **design.md §5 접힘 시작점 정정** — `Step 2` → `ChangeDestination Root`(첫 줄). SPEC 경계를 **강화**하는 방향이라 재감사 불요 | **manager-spec**(design.md 소유). FXLIB이 `completed`이므로 `completed → in-progress (amendment)` 전환으로 in-place 개정하거나, 다음 fx 계열 SPEC이 승계 시 함께 정정 | 문서 1줄. 라이브 불요 |
| 2 | **@MX ANCHOR 상한 결정** — `tools.py` 6 vs `anchor_per_file: 3`. **본 SPEC 착수 전부터 4건으로 초과**했고 FXLIB이 2건 추가. 프로토콜 처방("최저 fan_in부터 강등")이 축퇴한다(6개 전부 Load 1·호출 0 동률) | **사용자**(`.moai/config/sections/mx.yaml` 소유). 선택지 2개 — (a) 툴 레지스트리 파일에 한해 상한 상향 또는 문서화된 예외, (b) ANCHOR 기준을 fan_in에서 "모델 도달 초크포인트"로 재정의. **어느 쪽도 코드 변경 아님** | 설정 판단 1회 |
| 3 | **`SaveShow` → 디스크 쇼파일 판독 가설** — 열리면 이 SPEC의 **가장 비싼 제약**(효과 기계 검증 불가)이 풀릴 수 있다. 현재 응답기 5동사는 닫혀 있고 코드베이스에 쇼파일 판독기도 없으나, 이 경로는 **배제된 적이 없다** | **후속 SPEC**(신규). 착수 조건: 라이브 콘솔 세션 1회 + `SaveShow` 산출물 구조 조사. `server/deploy/pack.py:16`의 기존 관측이 출발점 | 조사 1회 + 라이브 1회 |

#### 감사자가 반증에 실패한 것 (방어가 실제로 작동함)

무음 실패 방어 전량(1스텝 수용 · 금지 형태 방출 · `Step 1` 발화 · 가드 무력화 · 효과 문면 제거) **전부 사망**. 부분 성공 위장 3축 전부 사망. LiveLock 예외의 범위 한정과 `chase` 위상 수정이 부분 호를 건드리지 않는다는 주장도 **양방향 확인**됐다. 감사자가 독립 생성한 `pulse` 번들이 구현자 산출·감사 로그와 **세 경로에서 같은 문자열에 도달**했다.

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기 — 소유: manager-develop>_

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_status: synced
sync_complete_at: 2026-08-01
sync_commit_sha: 4b62f79   # 백필 완료 — spec-frontmatter-schema.md § SHA placeholder backfill exemption 준용 (full: 4b62f795ed05e7518a3dc500a32f0e633f2ad4d8)
b12_self_test_a: "grep -c 'SPEC-COPILOT-FXLIB-001' CHANGELOG.md → 0 (사전) → 1 (사후, 신규 엔트리 1개) — 중복 없음"
b12_self_test_b: "acceptance.md SSOT AC count = 23 (grep -cE '^### AC-FXLIB-') == CHANGELOG 엔트리 인용 AC 수 23"
b12_self_test_c: "CHANGELOG 인용 경로 전건 ls 확인 — server/fx/{schema,loader,library,matching,instantiate,report}.py · server/orchestrator/tools.py · server/tests/test_fx_{schema,library,matching,instantiate,tool,boundary}.py"
changelog_entry_position: "CHANGELOG.md [Unreleased] > ### Added — SPEC-COPILOT-PRECHK-001 엔트리 바로 다음(SONGCUE 앞), 날짜순 최신 우선"
frontmatter_status_transitions:
  spec_md: "in-progress → completed (updated: 2026-08-01)"
  plan_md: "frontmatter 없음 — 본문 상태 표기는 progress.md §0/§E.1이 소유"
  acceptance_md: "frontmatter 없음 — 상태는 spec.md가 유일 SSOT"
canary_compliance_check: n/a   # 본 SPEC은 forward-looking 정책을 정의하지 않으며 자기 sync가 검증하는 canary 대상이 없다
```
