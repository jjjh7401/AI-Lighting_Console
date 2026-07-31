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

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기 — 소유: manager-develop>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기 — 소유: manager-docs. `sync_commit_sha` 필드가 여기 실린다>_
