# SPEC-COPILOT-FXLIB-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 타 SPEC 아티팩트**에만 쓰고, **각 마일스톤 착수 직전 재실측**한다(plan-phase에서 이미 scout 인용 2건의 드리프트를 정정했다 — research.md §2/§4). 요구·인수 토큰은 슬러그 포함 완전형만(축약 0건). 근거 등급 `[코드]` · `[문서]` · `[실측]` · `[미확정]` — **`[실측]`은 라이브 콘솔 직접 관측만**이며, 룰북의 "validated live" 선언은 `[문서]`다.

## §0 인수인계 — 여기서 시작한다 (2026-07-31)

### 한 문단

**무엇**: 이펙트(시간축 움직임) 어휘 계층 — LOOKLIB(정지 화면)의 자매편. 페이저+MAtricks+원형 조합의 폐쇄 패턴 어휘(무조건 4종 + M0 게이트 2종)를 `server/fx/` 신규 패키지에 세우고, 자연어 매칭(`find_fx`)과 시퀀스+큐 인스턴스화(`instantiate_fx`)를 기존 `run_commands`→`gate.screen()` 경로로만 배선한다.
**상태**: **plan-phase 완료 — 아티팩트 6종 작성, plan-audit 대기.** `status: draft`, 커밋 0건(작성만). REQ 21 · AC 22 · ASSUMPTION 4(36~39) · clarification 마커 0 · 라이브 세션 2회(M0·M7). 다음 단계 = plan-auditor 감사 → Implementation Kickoff Approval → M0.

### 읽는 순서

1. `spec.md` §A(개요·사전 확정 ①~④·패턴 표) → §C(ASSUMPTION-36~39) → §D(제외 11항)
2. `plan.md` §A.2(차단 표 — **ASSUMPTION-37만 저작을 막는다**) → §A.4(결정 A~H) → §B(M0~M7)
3. `acceptance.md` §C.0/§C.0a(역추적·배정 — 합 22·중복 0·누락 0)
4. `design.md` §3(fx-own 결정)·§5(값 라인 가드) — 왜 그런 형상인지의 정본
5. `research.md` — 근거 등급과 드리프트 정정 기록

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

### 기계 확인 (인수인계 무결성)

```bash
git branch --show-current                      # → feature/SPEC-COPILOT-FXLIB-001
ls .moai/specs/SPEC-COPILOT-FXLIB-001/         # → 6파일 (spec/plan/acceptance/design/research/progress)
grep -c "REQ-FXLIB-" .moai/specs/SPEC-COPILOT-FXLIB-001/spec.md      # ≥ 21
grep -c "^### AC-FXLIB-" .moai/specs/SPEC-COPILOT-FXLIB-001/acceptance.md  # = 22
grep -c "ASSUMPTION-3[6-9]" .moai/specs/SPEC-COPILOT-FXLIB-001/spec.md     # ≥ 4
uv run pytest server/tests/ -q                 # 킥오프 baseline — 직접 실측(이월 금지)
```

### 다음 소유자 킥오프 킷

- **plan-audit**: Tier L 기준(PASS ≥ 0.85). 감사가 볼 곳: ASSUMPTION-36의 기능/증거 이중 구조 분리가 유지되는가, 값 라인 가드가 dedupe 면제 판정을 재정의하지 않는가(design.md §5 마지막 불릿), 패턴 폐쇄 집합의 게이트 2종이 라이브러리에 새지 않는가.
- **M0 준비물**: 실물 onPC 실행 + 이름 있는 그룹이 있는 쇼파일(GUI 사용자 작업) + 날조 대조군 커맨드 목록(plan.md §B M0).
- **Kickoff 결정 없음**: 결정 A~H 전부 해소, clarification 0, 승인 대기 0 — 재질의할 것이 없다.

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

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-07-31
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
tokens: { req: 21, ac: 22, assumption: 4, clarification_markers: 0, live_sessions: 2 }
commit_sha: pending-backfill
```

## §E.2 Run-phase Evidence

### M0 — 라이브 프로브 1회차 (2026-07-31, cycle_type=none, 코드 변경 0)

원문 전량: `.moai/reports/m0-probe/raw-log-01.md` (게이트 미경유 — 감사 로그 없음. 응답 원문 + 사용자 GUI 관측이 증거)

**세션 조건 (직접 실측, 이월 없음)**: onPC `127.0.0.1:8000` · 수신 9005 · `osc_slot` 2 · 응답기 **v1.5.0** · `DataPool/Sequences` `childCount 17` `truncated:false` · `DataPool/Groups` 4개(1·11·12·13) · `DataPool/MAtricks` 1개(11 `Wave`).

**날조 대조군 — 양 축 확립**: exec 축 `ZzzBogusVerb 1` → `ok:false "Illegal object"` / 양성 `List` → `ok:true "OK"`; state 축 `DataPool/ZzzBogusPath` → `ok:false "path segment not found"`. 이 세션에서 `ok`는 **구문 유효성**의 증거로 사용 가능하다(효과의 증거는 아니다).

#### 접두 행 (판정 4건)

```
REOPEN: ASSUMPTION-36 — 페이저 생성 문법 미확립으로 저장 캡처 측정 불가. 증거 채널은 별도로 부정(큐 내용 판독 불가·빈 큐와 구별 불가)
SKIP:   ASSUMPTION-37 — 구문 접수 확인(ok:true)하나 효과 미판정. 페이저 생성이 확립되면 갈린다
GO:     ASSUMPTION-38 — Speed 단위 = BPM (GUI 표시 판독)
GO:     ASSUMPTION-39 — DataPool/MAtricks 재조회 가능 (childCount 1, truncated:false)
```

#### 핵심 관측 — 이펙트 커맨드는 접수되나 모션이 0회다

페이저 생성 시도 **3회**(딜머 진폭 없음 / 딜머 진폭 0~100 / 룰북 원문 Pan+Relative, 그룹 13·11 양쪽) 전부에서 모든 커맨드가 `ok:true "OK"`를 받았고 **GUI 모션 관측은 0회**다. Pan 자체는 살아 있다 — `Attribute 'Pan' At 20`으로 조준이 실제로 바뀌는 것을 관측했다. 즉 값은 먹히고 **페이저만 안 붙는다**. 재현 3회 · 반례 0회.

이는 BUSKWIZ 판정 *"`Cmd` OK는 효과의 증거가 아니다"* 가 이펙트 축에서 가장 선명하게 재현된 것이다. **FXLIB는 이 축에서 `ok`를 성공 신호로 쓸 수 없다.**

#### 증거 채널 — 저장된 큐의 내용은 기계로 읽히지 않는다

`state 'DataPool/Sequences/98/3/1'` → `Part`, `childCount 0`(트리 바닥). `prop` 은 `TrigType`→`"Go"`로 읽히나 `CueFade`·`Phase`·`Speed`는 `"property not readable"`. 결정적으로 **빈 프로그래머로 저장된 큐와 객체 트리상 구별되지 않는다**(양쪽 다 `Cue → Part(childCount 0)`).

#### 부수 — 무응답 ≠ 미실행

프로브 드라이버 결함으로 응답을 못 받던 구간에도 `Store`는 실제 실행됐다(`childCount` 17→18, 재조회 확인). 드라이버 결함의 원인은 `kind="result"`(응답기) vs `kind="exec"`(드라이버) 불일치였고, **콘솔 결함이 아니었다** — 1차 기록의 오진을 `raw-log-01.md` §0에 정정 보존했다.

#### 쇼파일 복구 — 확인됨

`Delete Sequence 98` · `Delete Sequence 99` 후 재조회 `childCount 17`, 번호 집합이 착수 시와 동일. 프로브 생성 오브젝트 잔여 **0건**.

#### 귀결 — M1 착수 보류

`REOPEN: ASSUMPTION-36`은 plan §B M0의 "run-phase 중단 + 블로커 보고, 조용히 진행 금지" 경로다. 페이저 생성 문법이 확립되기 전에는 M1 이후를 착수하지 않는다. 미발화로 남긴 경로(Effect 풀 오브젝트 · 페이저 편집기 경유 · `Step` 조합)는 추측 발화를 중단했기 때문이며, 재개 시 여기서부터 잰다.

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기 — 소유: manager-develop>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기 — 소유: manager-docs. `sync_commit_sha` 필드가 여기 실린다>_
