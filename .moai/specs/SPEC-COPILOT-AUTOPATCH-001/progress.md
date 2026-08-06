# SPEC-COPILOT-AUTOPATCH-001 — 진행 기록 (progress)

> **인용 규율**: 본 SPEC의 `spec.md`·`acceptance.md`는 행 번호로 인용하지 않는다 — 안정 토큰만 쓴다.
> `file:line`은 코드·룰북·`console/lua/PROTOCOL.md`·**다른** SPEC의 아티팩트에만.
> **증거 등급**: `[코드]` · `[문서]` · `[실측]` · `[미확정]`.

## §0 인수인계 — 여기서 시작한다 (2026-08-05)

**상태**: **plan-phase 아티팩트 6종 작성 완료 · plan-audit 대기.**
REQ **26건**(REQ-AUTOPATCH-001~026) · AC **27건** · ASSUMPTION 5건(71~75) · 마일스톤 9개(M0~M8) ·
라이브 세션 **2회 계획** · clarification 마커 0건 · 설계 슬롯 5건 전부 종결.

**이 SPEC이 1단계와 근본적으로 다른 점**: **콘솔에 쓴다.** 1단계는 읽고 비교만 했다.
패치는 픽스처를 **생성**하고, 이 앱에는 실행 취소·백업 복원 경로가 **없다**.
그래서 요구사항의 절반 이상이 기능이 아니라 **되돌릴 수 없는 쓰기를 사람이 통제하게 만드는 장치**다.

### 읽는 순서

| # | 무엇을 | 어디서 |
|---|---|---|
| 1 | 무엇을 만들기로 했나 | `spec.md` — REQ 26건 · §C `의존 범위 한정` · §C ASSUMPTION 71~75 · §C PRESERVE · §D Out of Scope 6건 |
| 2 | 왜 M0가 먼저인가 | `plan.md` §A.2 — 쓰기에 필요한 값 둘(FID · DMXMode 핸들)이 **읽히는지조차 미확정**이다 |
| 3 | 부정이면 어떻게 되나 | `plan.md` §A.3 — 가정 5건의 부정 처리표. 부정은 실패가 아니라 **기능 축소**다 |
| 4 | 무엇을 통과해야 하나 | `acceptance.md` — AC 27건 · §C.0 역추적표(REQ 26/26) · §C.0a 마일스톤 배정 · §F DoD |
| 5 | 어떻게 만들 것인가 | `design.md` — §3 흐름도 · §5 설계 슬롯 5건 · §6.3 비공허성 대조군 8건 · §7 안티패턴 10건 |
| 6 | 근거는 무엇인가 | `research.md` — 패치 기법 · FID 난제 · 타입 핸들 · 비가역성 · 1단계 상속 |

### 함정 6건 — 먼저 읽어라

1. **`ChangeDestination`/`CD`를 어디에서도 보내지 마라.** 플러그인 안에서도, `run_commands`로도.
   보내면 패치가 `nil`을 반환하고 **아무것도 생성되지 않는다**
   (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:20-29`).
2. **슬롯은 FID가 아니다.** `precheck_patch`는 FID를 읽지 못한다
   (`server/prechk/inventory.py:57`, REQ-PRECHK-005). 슬롯을 FID로 쓰면
   **MA3가 조용히 받아들이고 엉뚱한 픽스처를 덮는다**
   (`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:203-209`).
3. **`FixtureType`·`Mode`는 표시 문자열이다.** 거기서 채널 수를 파싱하지 마라 —
   `ASSUMPTION-27`이 이미 반증했다(`server/prechk/patch.py:14-22`).
4. **플러그인이 오류 없이 끝난 것은 성공이 아니다.** `AddFixtures`는 실패 시 `nil`을 반환할 뿐이다.
   **검증 읽기가 성공의 유일한 근거다**(REQ-AUTOPATCH-023).
5. **`run_commands` 배열 길이는 1이다.** 플러그인 실행 호출에 다른 명령을 함께 넣지 마라.
   이름은 **작은따옴표**(큰따옴표는 거부됨).
6. **역산된 주소로 패치할 수 있다.** 1단계가 `absolute_back_calculated` 등급을 붙여 넘긴다.
   금지하지 않되 **승인 화면에 등급과 전제를 노출**해야 한다(design.md §5 슬롯 D).

### 기계 확인 커맨드

```bash
W=/Users/studiox/orca/workspaces/AI-Lighting_Console/spec-vwx-001
git -C "$W" rev-parse --abbrev-ref HEAD          # feature/SPEC-COPILOT-VWX-001 (1단계 위에 스택)
uv run pytest server/tests -q                    # 착수 기준선: 4898 passed / 7 skipped
uv run ruff check server/vwx server/tests/test_vwx_*.py
git -C "$W" diff --stat ca00bc5..HEAD -- console/lua server/safety server/prechk server/paperwork server/looks
```

### 다음 담당자가 먼저 결정할 것

- **M0 라이브 세션 일정**. 이것 없이 M2·M3·M6 설계가 확정되지 않는다.
- **테스트 쇼파일 확보**. M0·M8 둘 다 파괴적 측정을 포함하므로 **운영 쇼파일에서 하지 않는다.**
- `ASSUMPTION-71` 측정을 위해 **슬롯과 FID가 다른 픽스처**가 있는 쇼파일이 필요하다.
  없으면 판정이 INCONCLUSIVE로 끝나고 충돌 사전검사가 descope된다.

---

## Plan-phase log

### v0.1.0 — plan-phase 아티팩트 6종 작성 (2026-08-05)

착수 SHA **`ca00bc5c853bfe5d9391290f1b9db263610b4bfa`**(1단계 v0.1.7 완료 시점),
착수 baseline **4,898 passed · 7 skipped · 1 warning · 92.28s** — **직접 실측, 이월 인용 아님.**

작성 방식: **오케스트레이터 직접 작성.** 1단계 run-phase에서 dispatch 왕복이
코디네이터 재검증 → 지시문 번역 → 워커 해석 → 재검증의 **번역 왕복 2회**를 만들어 3라운드를
되돌려보낸 이력이 있다. 작성은 직접 하고 **감사만 분리**해 독립성을 올린다(작성자 ≠ 감사자).

| 아티팩트 | 내용 | 라인 수 |
|---|---|---|
| `spec.md` | REQ 26건 · ASSUMPTION 71~75 · Out of Scope 6개 H3 · PRESERVE 5경로 · `depends_on` | v0.1.1 |
| `plan.md` | 마일스톤 M0~M8 · 결정 A~G(미결 0) · 라이브 2회 · 테스트 골격 · §G Mode 권고 | 192 |
| `acceptance.md` | AC 27건 · §C.0 역추적표(REQ 26/26) · §C.0a 배정 합 27 · §F DoD | v0.1.1 |
| `design.md` | 변경 표면 · 흐름 · 위험 7건 · 설계 슬롯 5건(전부 종결) · 비공허성 8건 · 안티패턴 10건 | 216 |
| `research.md` | 증거 등급별 조사 8절 · 미확정 5건을 ASSUMPTION으로 승격 | 202 |
| `progress.md` | 본 문서 | 158 |

**합 1,476줄** — 커밋 시점 실측(`wc -l`).

---

## §E.1 Plan-phase Audit-Ready Signal

**상태: plan-audit 6회차(재시도 상한 3회차 이후 독립 위임 재확인) PASS(1.000 ≥ Tier L 0.85, round5
0.923보다 +0.077 — 개선, 역행 아님) — audit-ready 유지.**
감사 통과 전에는 신호를 쓰지 않았다. 이는 **의도된 규율**이다 — 감사가 FAIL이면 신호가 거짓이 되기
때문이며, 실제로 1회차는 FAIL(0.80)이었다. (이 브랜치의 `.moai/specs/` 에는 같은 규율을 쓴 선행
SPEC이 없다. 유사 선례가 미머지 형제 브랜치에 존재하나 여기서 인용 가능한 자산이 아니다.)
2회차 이후 N1~N4 반영으로 **v0.1.2**가 되었으며, 그 반영은 신규 요구·AC를 만들지 않고
기존 요구를 인터페이스 계약과 일치시킨 것이라 감사 판정을 무효화하지 않는다(§E.1a 2회차 반영 절).
**3회차가 v0.1.2를 독립 재검증해 PASS(0.857, round2와 동일 점수 — 역행 아님)를 재확인했다.**
3회차는 N1~N4 CLOSED를 재확인하는 한편 신규 지적 2건(N5 major · N6 minor)을 발견했다 — 둘 다
PASS를 막지 않는 경량 후속 항목이다(§E.1a 3회차 절 참조). N5(design.md §6.2 표 행 손실)는
Implementation Kickoff Approval 전 경량 패치를 권고하나, audit-ready 신호를 철회할 사유는 아니다
(요구·AC 수 불변, must-pass 전부 PASS/N/A 유지).
**4회차(재시도 상한 이후 오케스트레이터 재량 위임)가 작성자의 N5·N6 자기수정을 독립 재검증해
PASS(0.923, round3보다 +0.066 — 개선, 역행 아님)를 확인했다.** N5·N6은 원문 대조로 **genuinely
CLOSED** 확인됨(§E.1a 4회차 절 참조). 4회차는 이번 회차의 전수 스윕 지시(`design.md` §6.2 27개
AC 전부를 acceptance.md 자체 인용과 대조)로 **신규 지적 3건**(N7 major · N8·N9 minor)을 발견했다 —
전부 `design.md` §6.2(테스트 파일 포인터 표, 추적성 SSOT인 §C.0/§C.0a와는 별개)에 국한되며,
PASS를 막지 않는다. N7(AC-AUTOPATCH-015가 잘못된 테스트 파일 행에 배정됨)은 §6.2 표가 4회차 연속
동일 위치에서 결함을 낸다는 **공정 관찰**(§E.1a 4회차 절 "공정 관찰" 참조)의 근거이며, Implementation
Kickoff Approval 전 경량 패치를 권고하나 audit-ready 신호를 철회할 사유는 아니다.
**5회차가 N7 자기수정을 독립 재검증해 PASS(0.923, round4와 동일 — 횡보)를 확인했다.** N7은 여섯
AC(013~019) 전부 대조로 **genuinely CLOSED** 확인됨(§E.1a 5회차 절 참조). N8·N9는 작성자의 신고대로
미반영 상태로 정확히 남아 있음을 원문 대조로 확인했다. 5회차는 전수 스윕(27개 AC 전부를
acceptance.md 자체 인용과 대조)에서 **신규 지적 1건**(N10 minor — AC-004 이중 인용의 두 번째 파일
누락, round4가 "무결"로 인증했던 배치 안에서 발견)을 찾았다 — PASS를 막지 않으며, §6.2 표가
5회차 연속 동일 결함 클래스를 낸다는 공정 관찰을 심화한다(§E.1a 5회차 절 "공정 관찰" 참조,
구조적 대안 — §6.2 삭제 — 을 자문으로 제시).
**6회차(재시도 상한 이후 오케스트레이터 재량 위임)가 작성자의 §6.2 폐지 자기수정(N8·N9·N10 구조적
해소 주장)을 독립 재검증해 PASS(1.000, round5보다 +0.077 — 개선, 역행 아님)를 확인했다.** N8·N9·N10
전부 원문 대조로 **genuinely CLOSED** 확인됨(§E.1a 6회차 절 참조) — §6.2 표가 진짜로 삭제되었고,
6개 아티팩트 전체에 §6.2를 권위 출처로 참조하는 곳이 0건이며, N8·N10의 실제 대상이었던 AC-004·
AC-025 자신의 검증방법 필드가 이미 두 파일 모두 완전히 명시하고 있었음을 확인했다(삭제가 정보를
옮긴 게 아니라 부정확한 사본만 제거). round1 이후 처음으로 **4개 축 전부 잔여 결함 0건**이다.

기록된 값 (6회차 감사 PASS로 갱신 — round6 리포트 참조):

```yaml
plan_status: audit-ready
plan_complete_at: "2026-08-06 — round6 plan-auditor PASS (1.000 ≥ Tier L 0.85, round5(0.923)보다 +0.077 — 개선, 역행 아님), 감사 대상 작업트리(round3 HEAD fa70cf3 + round4·round5·round6 미커밋 자기수정 4파일)"
spec_version: "0.1.2"     # round6은 spec.md에 손대지 않은 미커밋 §6.2 폐지 자기수정을 감사 대상으로 재검증. 요구·AC 수 불변(26/27)
base_sha: ca00bc5c853bfe5d9391290f1b9db263610b4bfa
baseline_measured: "uv run pytest server/tests -q → 4898 passed, 7 skipped, 1 warning in 92.28s"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
requirements: 26          # REQ-AUTOPATCH-001~026 (v0.1.1에서 026 신설)
acceptance_criteria: 27   # AC-AUTOPATCH-001~027 (v0.1.1에서 027 신설)
milestones: 9             # M0~M8. M0·M8만 cycle_type=none (라이브 측정)
assumptions_open: 5       # ASSUMPTION-71~75 — 전부 M0 라이브 판정 대상
live_sessions_planned: 2  # M0 전제 측정 · M8 종단 검증
decisions_closed: 7       # plan.md §A.4 결정 A~G
decisions_open: 0
design_slots_closed: 5    # design.md §5 슬롯 A~E
design_slots_open: 0
clarification_markers: 0
machine_gates:
  req_to_ac_coverage: "26/26 — acceptance.md 역추적표 REQ 행 26, 커버 누락 0"
  ac_milestone_assignment: "27 — M0 1 · M1 3 · M2 5 · M3 4 · M4 4 · M5 3 · M6 3 · M7 3 · M8 1. 중복 0 · 누락 0"
  ac_absent_from_traceability_table: "5 — AC-AUTOPATCH-001(전제 게이트) · AC-AUTOPATCH-023(툴 등록) · AC-AUTOPATCH-024(PRESERVE) · AC-AUTOPATCH-025(1단계 회귀) · AC-AUTOPATCH-026(라이브 통합). acceptance.md가 의도로 명시"
  out_of_scope_h3_headings: "6"
  nonvacuity_controls_required: 8   # design.md §6.3
known_gaps:
  - "ASSUMPTION-71~75 5건 전부 미판정 — M0 라이브 세션 전에는 M2·M3·M6 설계가 확정되지 않는다."
  - "테스트 쇼파일이 아직 지정되지 않았다. M0·M8 둘 다 파괴적 측정을 포함한다."
  - "ASSUMPTION-71 판정에는 슬롯≠FID 픽스처가 있는 쇼파일이 필요하다. 없으면 INCONCLUSIVE."
  - "CID/다른 idtype 축(research.md §3.3 경로 c)은 조사 부족으로 이번 범위 밖이다."
  # round2 N1~N4는 v0.1.2에서 전량 CLOSED — §E.1a "2회차 지적 반영" 절 참조. 잔여 gap 아님.
  # round3 N5·N6은 round4가 원문 대조로 독립 재검증해 CLOSED 확정(§E.1a 4회차 절). 잔여 gap 아님.
  - "[CLOSED · round4 독립 검증] round3 N5(major) — design.md §6.2 표에 `002 · 003 · 004 |
    test_autopatch_candidates.py` 행 복원 확인(누락 지점에 정확히 삽입, 27/27 행 커버로 복귀 —
    전수 재열거로 재확인, 복원 편집 자체의 부수 손상 없음)."
  - "[CLOSED · round4 독립 검증] round3 N6(minor) — acceptance.md:3·plan.md:3 상태줄이
    `v0.1.2, 2026-08-06`로 갱신되고 acceptance.md:3의 'AC 27건 계획'이 §C.0a '합 27'과 일치함을
    직접 대조로 확인. 6개 아티팩트 전체 26/27건 언급 광역 재스캔에서 잔여 staleness 0건."
  - "[CLOSED · round5 독립 검증] round4 N7(major) — design.md §6.2에서 AC-AUTOPATCH-015를
    `013·014·016 | test_autopatch_lua.py` 행에서 분리해 `015·017·018·019 |
    test_autopatch_execute.py` 행으로 재배정. AC-013·014·015·016·017·018·019 여섯 건 전부를
    acceptance.md 자체 검증방법과 개별 대조해 확인, git diff로 단일 훅·부수 손상 없음 확인.
    잔여 gap 아님."
  - "[CLOSED · round6 독립 검증] round4 N8(minor) — design.md §6.2 폐지로 `024·025` 행 자체가
    소멸. AC-025 자신의 검증방법(acceptance.md:427-429)이 test_vwx_*.py 전수 + 골든스냅샷
    test_autopatch_contract.py를 이미 완전히 명시하고 있었음을 원문 대조로 확인 — 삭제가
    정보를 옮긴 게 아니라 부정확한 사본만 제거했다. 잔여 gap 아님."
  - "[CLOSED · round6 독립 검증] round4 N9(minor) — design.md:3 상태줄 접미사가
    '1~5회차 지적 반영 · §6.2 폐지'로 갱신됨을 원문 대조로 확인. 잔여 gap 아님."
  - "[CLOSED · round6 독립 검증] round5 N10(minor) — design.md §6.2 폐지로 `002·003·004` 행 자체가
    소멸. AC-004 자신의 검증방법(acceptance.md:159)이 test_autopatch_candidates.py ·
    test_autopatch_execute.py 두 파일을 이미 완전히 명시하고 있었음을 원문 대조로 확인. 잔여
    gap 아님."
  - "[CLOSED · round6 독립 검증] §6.2 폐지가 다른 참조를 깨뜨리지 않음 — 6개 아티팩트 전체를
    '§6.2'·'design.md §6' 패턴으로 광역 재스캔해 §6.2를 권위 출처로 참조하는 곳 0건을 확인
    (매치는 전부 다른 절 참조이거나 progress.md 자체 감사기록). plan.md §E 테스트 골격이
    §6.2와 독립적으로 이미 파일→주제 매핑을 제공하고 있어 온보딩 가독성도 유지됨. 잔여
    gap 아님 — round1 이후 최초로 4개 축 전부 잔여 결함 0건."
next: "M0 라이브 세션 일정과 테스트 쇼파일 확보 → Implementation Kickoff Approval. round2 지적 N1~N4는 v0.1.2에서 전량 반영 완료(round3 독립 재검증 PASS). round3 N5~N6은 round4가 독립 재검증해 CLOSED 확정. round4 N7(major)은 round5가 독립 재검증해 CLOSED 확정. round4 N8·N9·round5 N10은 round6이 design.md §6.2 폐지 자기수정을 독립 재검증해 전량 CLOSED 확정 — 잔여 plan-audit 결함 0건. 남은 전제는 M0 라이브 세션 일정과 테스트 쇼파일 확보뿐이며 run-phase 착수 전제이지 plan-audit 지적 사항이 아니다."
```

---

## §E.1a Plan-audit 결과

### 1회차 (round1) — 2026-08-06 — plan-auditor 독립 감사

**판정: FAIL** — Overall Score **0.80**(조화평균) < Tier L 임계 **0.85**.
전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round1.md`

**Must-Pass**: MP-1~MP-7 **전부 기계적 PASS/N/A**(MP-4 N/A: 단일 언어 프로젝트).
다만 MP-5(D7)는 좁은 검증구문(retired/superseded/archived만 검사) 상 기계적 PASS이나,
그 인접 위험을 **D1(critical)**로 별도 승격했다 — `SPEC-COPILOT-VWX-001`(직접 선행 SPEC, spec.md에
명시)이 `status: draft` · `run_status: partial-blocked`(M8 여전히 BLOCKED)인데도 본 SPEC이
`related_specs:`(게이트 미작동 필드)만 쓰고 `depends_on:`(게이트 작동 필드)을 선언하지 않아
Phase 1 Depends_on Pre-flight Check가 이 불일치를 전혀 잡지 못한다.

**축별 점수** (조화평균 산정):

| 축 | 점수 | 근거 |
|---|---|---|
| Clarity | 0.75 | D1(1단계 완료 여부 모순) · D7(REQ-AUTOPATCH-022 멱등 매칭 기준 미정) · D8(AC-AUTOPATCH-001 Where/When 오용) |
| Completeness | 0.75 | D1(`depends_on:` 부재) · D3(design.md §5 슬롯 D "근거 등급 노출" 미보증) · D5(AC-AUTOPATCH-025 "계약 스냅샷" 메커니즘 미정의 — `test_vwx_report.py` grep 확인, 현재 그런 스냅샷 테스트 없음) |
| Testability | 0.75 | D4(AC-AUTOPATCH-014③ "구조적으로 보인다"가 ①②와 같은 검증법 재서술 — AC-AUTOPATCH-007①의 진짜 AST 구조 검사와 대비됨) · D5(AC-AUTOPATCH-025① "의미가 그대로다" 준-위즐워드) |
| Traceability | 1.0 | §C.0 25행 전량 재대조 PASS. 공유-AC REQ쌍 **4건**(디스패치 힌트의 "3건"보다 1건 더 발견) 전부 독립 검증 가능 확인 — 은폐 없음 |

**지적표 요약**(전문 참조): D1 critical(1) · D2·D3·D4·D5 major(4) · D6·D7·D8·D9·D10 minor(5).
P0/P1 상당 지적 5건(D1~D5)이 이번 회차의 핵심 — 전부 "design.md가 약속한 안전장치가 REQ/AC로
집행되지 않음" 또는 "1단계 상태 주장이 1단계 자신의 progress.md와 불일치" 패턴이다.

**권고 수정 순서**: D1(`depends_on:` 추가 + 1단계 상태 조정) → D3(근거 등급 컬럼 추가) →
D5(계약 스냅샷 구체화) → D4(AC-AUTOPATCH-014③ AST 구조 검사로 교체) → D2(FID 부정 분기 완화책 강화) →
D6~D10 일괄. 구조적 결함이 아니라 열거 가능한 구체적 gap이므로, 2회차에서 PASS 도달이 현실적이다
(scope-reduction 불필요 — LEAN Workflow STOP 에스컬레이션 조건 미해당, 1회차뿐이라 회귀 비교 대상 없음).

### 1회차 지적 반영 — v0.1.1 (2026-08-06, 작성자=오케스트레이터)

**10건 전량 반영. 미반영 0건.**

| # | 반영 내용 | 반영 위치 |
|---|---|---|
| D1 critical | frontmatter `depends_on: [SPEC-COPILOT-VWX-001]` 추가로 run-phase 진입에 Phase 1 의존성 게이트를 물린다. **동시에** "1단계 완료" 주장을 좁혀 §C `의존 범위 한정` 신설 — 무엇에 의존하고(리포트 스키마·멀티셀/액세서리 분류·`address_basis`·`diffs.performed` 불변식, 전부 M1~M7 구현·검증 완료) 무엇에 의존하지 않는지(`ASSUMPTION-70`·1단계 M8·`status: draft`) 표로 분리 | `spec.md` frontmatter · 도입 blockquote · §C |
| D2 major | **REQ-AUTOPATCH-026 신설** — `ASSUMPTION-71` 부정/INCONCLUSIVE 시 "FID 범위가 콘솔에서 비어 있음을 눈으로 확인했다"를 일반 승인과 구분되는 **별도 페이로드 필드**로 요구하고 없으면 실행 거부. 산문 경고에서 **건별 감사 가능한 구조 데이터**로 승격. AC-AUTOPATCH-027이 GO/부정 대조로 비공허하게 검증 | `spec.md` §B.2 · `acceptance.md` · `plan.md` §A.3 |
| D3 major | REQ-AUTOPATCH-003의 드라이런 표 필수 열에 **`address_basis` 추가**. AC-AUTOPATCH-004③이 역산 전제 문구 노출을 검증하고, 전 항목 직접값인 입력에서는 그 문구가 **안 나오는지**까지 대조 | `spec.md` REQ-AUTOPATCH-003 · `acceptance.md` AC-AUTOPATCH-004 · `design.md` §4 R5 |
| D4 major | AC-AUTOPATCH-014를 **두 기법 분리**로 재작성 — ①② 산출물 문자열 스캔, ③ `server/vwx/luagen.py` **소스 AST 스캔**(금지 리터럴 0건 + 자유 문자열이 명령 배열/Lua 본문에 도달하는 경로 0건). AC-AUTOPATCH-007① AST 패턴 계승 | `acceptance.md` AC-AUTOPATCH-014 |
| D5 major | AC-AUTOPATCH-025에 **골든 스냅샷 기법 정의** — 최상위 키 집합 + 키별 타입 시그니처를 JSON 픽스처로 고정(값은 고정하지 않음), 키 내부 의미는 1단계 기존 구조 assert에 위임. 파일명·픽스처 경로 명시, `plan.md` §E 테스트 표에 등재 | `acceptance.md` AC-AUTOPATCH-025 · `plan.md` §E |
| D6 minor | M0에 **진입 전제** 신설 — 테스트 쇼파일 확보는 권고가 아니라 차단 전제. 끝내 미확보 시 `ASSUMPTION-73`·`-74`는 INCONCLUSIVE로 판정하고 M8은 BLOCKED로 남는다(운영 쇼파일 대체 금지) | `plan.md` §B M0 |
| D7 minor | REQ-AUTOPATCH-022에 멱등 일치 튜플 **(유니버스, 주소, FixtureType, DMXMode 이름)** 명시. **주소 일치 + 타입/모드 불일치는 멱등이 아니라 충돌**로 보고 | `spec.md` REQ-AUTOPATCH-022 · `acceptance.md` AC-AUTOPATCH-020 |
| D8 minor | AC-AUTOPATCH-001 `**Where**` → `**When**`(이벤트 트리거이지 capability gate가 아니다) | `acceptance.md` AC-AUTOPATCH-001 |
| D9 minor | 존재하지 않는 선례 인용 삭제. 감사 전 신호 보류가 **의도된 규율**임을 직접 서술하고, 유사 선례가 미머지 형제 브랜치에 있어 인용 불가함을 명시 | `progress.md` §E.1 |
| D10 minor | `design.md` §4에 **R8 신설** — 미리보기와 실행이 툴 호출 수준에서 결속되지 않는 잔여 위험을 **수용된 위험으로 명시**. 승인은 오케스트레이터/사람 대화 계층에서 강제되며 이는 저장소의 다른 쓰기 툴과 동일 패턴. plan-hash/preview-token 결속은 도입하지 않는다(이 SPEC만 다른 규약을 쓰면 일관성이 깨진다) | `design.md` §4 |

**반영 후 기계 재검증**(작성자 실측): REQ 26 · AC 27 · 역추적 26/26 누락 0 · 표 밖 AC 5(의도) ·
§C.0a 합 27 · `plan.md` 마일스톤 AC 줄과 **1:1 전수 일치** · 약어 토큰 0 · 명료화 마커 0 ·
레거시 EARS 조건절 키워드 0 · 레거시 패턴 라벨 0 · `depends_on` 1건.

**2회차 감사 필요.** 이 절의 반영 주장은 작성자 자신의 것이므로 독립 확인 대상이다.

### 2회차 (round2) — 2026-08-06 — plan-auditor 독립 감사

**판정: PASS** — Overall Score **0.857**(조화평균) ≥ Tier L 임계 **0.85**(여유 +0.007, 근소).
1회차 0.80 → 2회차 0.857로 **상승**(LEAN 점수 역행 STOP 미해당). 전문:
`.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round2.md`

**회귀 확인**: D1~D10 **10건 전량 각 지적의 원문 required-fix 문구 기준으로 CLOSED 재확인**됨
(작성자의 claimed-fix 표를 그대로 신뢰하지 않고 인용 위치를 직접 재열람·재검증). 어느 지적도
미반영 상태로 재발하지 않았다. D1만 예외적으로 "핵심은 CLOSED, 잔향(research.md의 미조정 문구)은
새 지적 N3로 별도 기록" — round1의 D1 required-fix가 명시적으로 지목한 위치(spec.md §A/§C)는
둘 다 충족되었으므로 D1 자체는 재개방하지 않는다.

**신규 지적 4건**(모두 PASS를 막지 않음, N1만 major): 이 라운드는 회귀 확인에 그치지 않고
"수정 자체가 새 결함을 낳았는가"를 별도로 스캔했다 — REQ-AUTOPATCH-026/AC-AUTOPATCH-027이 닿은
모든 아티팩트의 전체 동기화 여부를 확인.

- **N1 (major)** — design.md §2.3 파라미터 스키마 초안이 REQ-AUTOPATCH-026/AC-AUTOPATCH-027의
  구조화된 확인 필드를 위한 필드명을 여전히 갖지 않는다 — D3가 잡았던 결함 **패턴**(안전 요구가
  REQ/AC 산문에는 있으나 구체 스키마엔 없음)이 새 요구사항에서 재발했다.
- **N2 (minor)** — design.md §6.2 "AC → 테스트 파일" 표에 AC-AUTOPATCH-027 행 누락.
- **N3 (minor, D1 잔향)** — research.md:23이 여전히 "본 SPEC의 입력은 확정되어 있다"는 무조건
  문구를 쓴다 — spec.md §C `의존 범위 한정`과 미조정. research.md는 v0.1.1에서 손대지 않았다.
- **N4 (minor)** — AC-AUTOPATCH-027(M2)이 문서 순서상 AC-AUTOPATCH-026(M8) **뒤**에 위치 —
  자매 SPEC `SPEC-COPILOT-VWX-001`의 v0.1.4 증분 삽입 관례(신규 AC는 M7/M8 말미 쌍보다 **앞**에
  삽입)와 어긋난다. §C.0a 배정표는 정확해 추적성·검증가능성 피해는 없다.

**축별 점수**: Clarity 0.75(변화 없음 — D7·D8 CLOSED로 상쇄, N3·N4가 잔여) · Completeness 0.75
(변화 없음 — D1·D3·D5 CLOSED이나 N1·N2가 같은 결함급을 재도입) · Testability 1.0(D4·D5 완전
CLOSED, weasel word 재스캔 0건) · Traceability 1.0(REQ-AUTOPATCH-026→AC-AUTOPATCH-027 신규 1:1, 26/26 유지).

**권고**: PASS이므로 3회차 의무 아님. N1(major)은 M2 착수 전 경량 v0.1.2 패치로 필드명을
확정하는 것을 권한다 — required fix는 round2 리포트 Defects Found N1 참조. N2~N4는 선택.

### 2회차 지적 반영 — v0.1.2 (2026-08-06, 작성자=오케스트레이터)

**N1~N4 4건 전량 반영. 미반영 0건.** 2회차가 PASS(0.857)였으므로 의무는 아니나,
N1은 D3와 **같은 결함 패턴**(설계가 약속한 것이 인터페이스 계약에 없음)의 재발이라 방치하지 않는다.

| # | 반영 내용 | 위치 |
|---|---|---|
| N1 major | `design.md` §2.3 툴 스키마에 **`fid_range_visually_confirmed_empty: boolean`** 필드 신설 — `ASSUMPTION-71` 부정·INCONCLUSIVE 분기 필수, 생략 시 실행 거부, `selected`·`dry_run`과 독립임을 주석에 명시. AC-AUTOPATCH-027 기대결과가 **그 정확한 필드명을 인용**하도록 재작성해 요구와 인터페이스 계약이 같은 자산을 지목하게 했다 | `design.md` §2.3 · `acceptance.md` AC-AUTOPATCH-027 |
| N2 minor | `design.md` §6.2 AC→테스트 파일 표의 `test_autopatch_fid.py` 행에 `027` 추가 | `design.md` §6.2 |
| N3 minor | `research.md` §1의 무조건적 "입력은 확정되어 있다" 문단 아래에 v0.1.1 갱신 주석 추가 — 확정 범위가 `spec.md` §C `의존 범위 한정`으로 좁혀졌고 1단계 전체 완료를 뜻하지 않음을 명시. `status:` 줄도 v0.1.2로 갱신 | `research.md` §1 · status |
| N4 minor | AC-AUTOPATCH-027 절을 AC-AUTOPATCH-008 **직후**로 이동 — 개정 AC를 종단 마일스톤(M7/M8) 뒤가 아니라 소속 마일스톤(M2) 그룹에 두는 `SPEC-COPILOT-VWX-001` v0.1.4 관례를 따른다. 문서 순서: … 007 · 008 · **027** · 009 … | `acceptance.md` |

**반영 후 기계 재검증**(작성자 실측): REQ 26 · AC 27 · 역추적 26/26 누락 0 · 표 밖 AC 5 ·
§C.0a 합 27 · `plan.md` 1:1 일치 · 약어 토큰 0 · 명료화 마커 0 · 필드명이 `design.md`와
`acceptance.md` 양쪽에 동일 문자열로 존재.

### 3회차 (round3) — 2026-08-06 — plan-auditor 독립 감사

**판정: PASS** — Overall Score **0.857**(조화평균, round2와 **동일** — 역행 아님, LEAN 점수 역행
STOP 미해당). 전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round3.md`

**공정 이상 사항 발견**: 감사 지시는 v0.1.2가 "미커밋 작업트리 변경"이라 전제했으나, 실제로는 이미
`fa70cf3`(0869fdd의 자식 1커밋)로 커밋되어 있었다(`git status --short`가 SPEC 디렉터리에 대해
비어 있음을 반환). 3회차 감사는 이 사실을 그대로 보고하고, `0869fdd..HEAD` diff를 감사 대상으로
삼아 진행했다 — 감사 자체의 유효성에는 영향이 없다(대상 텍스트는 동일).

**N1~N4 전량 CLOSED 재확인**(작성자의 claimed-fix 표를 신뢰하지 않고 원문 재대조): N1(필드명
`fid_range_visually_confirmed_empty`가 `design.md` §2.3와 `acceptance.md` AC-027 양쪽에 정확히
일치) · N2(`design.md` §6.2에 027 추가, 문구 그대로 충족) · N3(`research.md` 갱신 문구가
`spec.md` §C와 무모순, `status:` v0.1.2로 갱신 확인) · N4(VWX-001의 실제 `acceptance.md`를
**직접 재조회**해 관례를 독립 재검증 — AC-VWX-027/028/029가 M7/M8 종단쌍보다 앞에 위치함을 확인).

**신규 지적 2건 발견**(모두 PASS를 막지 않음, N5는 major):
- **N5 (major)** — `design.md` §6.2에 027을 추가한 바로 그 편집이 기존 `002 · 003 · 004 →
  test_autopatch_candidates.py` 행을 **삭제**했다. 실제 테스트 파일 매핑은 `acceptance.md`의
  각 AC 본문과 `plan.md` §E에 여전히 정확하게 남아 있어 실질 피해는 design.md 로컬이지만,
  round2 이후에도 자기검증 범위가 "전체 표 재대조"가 아니라 "대상 행만"이었다는 동일 실패
  패턴이 재발했다. `progress.md`의 N2 claimed-fix 행은 이 삭제를 언급하지 않아 과소 신고다.
- **N6 (minor)** — `acceptance.md:3` · `plan.md:3` 상태줄이 여전히 `v0.1.0`이며,
  `acceptance.md:3`의 "AC 26건 계획"은 같은 문서 §C.0a의 "합 27"과 **자기모순**이다.

**축별 점수**: Clarity 0.75(N3·N4 CLOSED로 상쇄되나 N6이 같은 밴드를 유지) · Completeness 0.75
(N1 CLOSED가 개선이나 N5가 같은 결함 패턴을 더 나쁜 형태로 재도입 — round2의 26/27 커버가
24/27로 후퇴) · Testability 1.0(AC-027이 구체 필드명을 얻어 오히려 개선, weasel word 0건) ·
Traceability 1.0(§C.0/§C.0a는 design.md §6.2와 별개 SSOT, N5 영향 없음, 26/26·27/27 유지).

**권고**: 3회차(재시도 상한)이므로 4회차 의무 아님. N5(major)를 경량 패치로 되돌리기를 권한다 —
`design.md` §6.2에 `002 · 003 · 004 | test_autopatch_candidates.py` 행 복원. N6은 선택.

### 4회차 (round4) — 2026-08-06 — plan-auditor 독립 감사 (재시도 상한 이후, 오케스트레이터 재량 위임)

**판정: PASS** — Overall Score **0.923**(조화평균, round3의 0.857보다 **+0.066 개선** — 역행 아님,
LEAN 점수 역행 STOP 미해당). 전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round4.md`

**감사 대상**: round3 이후 오케스트레이터(작성자, 감사 에이전트 아님)가 직접 손댄 `acceptance.md`·
`design.md`·`plan.md` 3개 파일의 미커밋 작업트리 변경(round3 N5·N6 자기수정) — `progress.md` §E.1
`known_gaps`에 `[반영됨·미검증]` 접두로 기록된 바로 그 변경. 이 접두 자체가 "자기검증만 거쳤다"는
신호이므로, 이전 라운드와 동일한 규율로 신뢰하지 않고 원문 대조로 독립 재검증했다.

**N5·N6 전량 CLOSED 확인**(claimed-fix 표를 신뢰하지 않고 `git diff fa70cf3`로 실제 diff를 직접
대조): N5(`design.md` §6.2에 `002 · 003 · 004 | test_autopatch_candidates.py` 행이 정확한 위치에
복원되었고, 표 전체를 처음부터 다시 세어 27/27 AC 커버·중복 0·누락 0을 확인. 복원 편집 자체는
`git diff` 상 1줄 추가뿐으로 부수 손상 없음) · N6(양쪽 상태줄이 `v0.1.2, 2026-08-06`으로 갱신되고
acceptance.md:3의 "AC 27건"이 §C.0a "합 27"과 일치함을 직접 대조로 확인, 6개 아티팩트 전체에 대한
광역 "26건/27건" 재스캔에서 잔여 staleness 0건).

**신규 지적 3건 발견**(모두 PASS를 막지 않음, N7만 major) — 이번 회차의 과제 지시가 요구한 "터치된
행뿐 아니라 27개 AC 전부를 acceptance.md 자체 검증방법과 대조"하는 전수 스윕에서 처음 발견됨:

- **N7 (major)** — `design.md` §6.2의 `013·014·015·016 | test_autopatch_lua.py` 행에
  AC-AUTOPATCH-015가 잘못 배정되어 있다. AC-015 자신의 `acceptance.md:313` 검증방법
  (`test_autopatch_execute.py`)과 `plan.md:180`의 파일별 주제 설명이 모두 execute.py를 가리킨다.
  v0.1.0부터 존재해온 결함으로 이번 라운드의 N5 복원 편집이 만든 것이 아니다(`git diff`로 확인 —
  그 행은 이번 회차에 손대지 않았다). §C.0/§C.0a 추적성 SSOT는 무영향.
- **N8 (minor)** — `design.md` §6.2의 `024·025` 행이 AC-025의 신설 골든스냅샷 파일
  `test_autopatch_contract.py`를 명시하지 않는다(`plan.md:183`·`acceptance.md:427-428`은 명시).
- **N9 (minor)** — `design.md:3` 상태줄 접미사 "plan-audit 1·2회차 지적 반영"이 이번 회차 N5 반영
  사실을 반영하지 못해 이 파일 자체의 변경사항과 어긋난다.

**축별 점수**: Clarity 1.0(N6 CLOSED로 상승 — 잔여 Clarity급 결함 없음, weasel word 재스캔 0건) ·
Completeness 0.75(N5는 깨끗이 닫혔으나 N7이 같은 결함급을 다른 구체적 사유로 재도입 — round3와
동일 밴드 유지) · Testability 1.0(무변화) · Traceability 1.0(무변화 — N7~N9는 §6.2 국소, SSOT
무영향).

**공정 관찰(과제 명시 요청)**: round2→round3는 "수정이 직접 새 결함(N5)을 낳음"(N2의 편집이 N5를
유발)이었으나, round3→round4는 그 특정 하위 패턴이 재발하지 **않았다**(N5 복원 편집 자체는
`git diff`로 확인된 대로 깨끗함). 그러나 더 넓은 패턴 — "`design.md` §6.2가 4회차 동안 한 번도
전수·정확성 기준으로 완전히 검증된 적이 없다" — 는 여전히 살아 있다: 1회차는 §6.2를 아예 감사하지
않았고, 2회차(N2)는 027 등재 여부만, 3회차(N5)는 행의 존재 여부만 확인했을 뿐 행 **내용의 정확성**은
아무도 확인하지 않았다. 이번 회차가 처음으로 27개 AC 전부에 대해 acceptance.md 자체 인용과 대조하는
전수 스윕을 수행했고, 그 즉시 v0.1.0부터 있던 N7을 찾아냈다. **Kickoff 전에 N7 수정 후 다시 한 번
전수 대조를 권고한다** — round2→round3의 "좁은 범위 자기검증이 새 결함을 놓친다" 실패 패턴이 N7 수정
자체에서도 재발하지 않는지 확인하기 위함이다.

**권고**: 재시도 상한(3회차) 이후 재량 위임 검증이므로 5회차 의무 아님. N7(major)을 경량 패치로
수정하기를 권한다 — `013·014·016 | test_autopatch_lua.py`와 `015·017·018·019 |
test_autopatch_execute.py`로 행 분리. N8·N9는 선택(같은 패치에 묶어도 무방).

### 5회차 (round5) — 2026-08-06 — plan-auditor 독립 감사 (재시도 상한 이후, 오케스트레이터 재량 위임)

**판정: PASS** — Overall Score **0.923**(조화평균, round4와 **동일** — 역행도 개선도 아닌 **횡보**,
LEAN 점수 역행 STOP 미해당). 전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round5.md`

**감사 대상**: round4 이후 오케스트레이터(작성자, 감사 에이전트 아님)가 직접 손댄 `design.md` §6.2
표의 미커밋 작업트리 변경(round4 N7 자기수정 — `013·014·015·016` 행을 `013·014·016`과
`015·017·018·019`로 분리) — `progress.md` §E.1 `known_gaps`에 `[반영됨·미검증]` 접두로 기록된 바로
그 변경. N8·N9는 이번 회차에 손대지 않았다고 기록되어 있어(각각 `[신규 · round4 발견]` 접두, 
`[반영됨]` 아님), 이 주장 자체를 원문 대조로 독립 검증했다.

**N7 전량 CLOSED 확인**(claimed-fix 표를 신뢰하지 않고 AC-013·014·015·016·017·018·019 여섯 건
전부를 acceptance.md 자체 검증방법과 개별 대조): `design.md` §6.2가 `013·014·016 |
test_autopatch_lua.py`와 `015·017·018·019 | test_autopatch_execute.py`로 정확히 분리되었고,
여섯 AC 전부 자체 인용과 정확히 일치함을 확인. `git diff fa70cf3`로 이 편집이 단일 훅(hunk)이며
그 두 행 외 다른 어떤 행도 건드리지 않았음을 확인 — 부수 손상 없음.

**N8·N9 원문 대조로 미반영 확정**(작성자 기록이 정확함을 독립 검증): `024·025` 행은 여전히
`test_autopatch_contract.py`를 명시하지 않고, `design.md:3` 상태줄 접미사는 여전히 "1·2회차
지적 반영"에 머문다. `git diff fa70cf3 -- design.md`가 두 지점 모두 이번 회차에 손대지 않았음을
확인 — 작성자가 은폐 없이 정확히 신고한 대로다.

**신규 지적 1건 발견**(PASS를 막지 않음, minor) — 이번 회차의 과제 지시가 요구한 "27개 AC 전부를
acceptance.md 자체 인용과 대조"하는 전수 스윕에서 발견됨. round4의 "25건 무결" 주장의 범위(001-014
포함) 안에 있었으나 round4가 놓쳤다:

- **N10 (minor)** — `design.md` §6.2의 `002 · 003 · 004 | test_autopatch_candidates.py` 행이
  AC-AUTOPATCH-004 자신의 검증방법(`acceptance.md:159` — `test_autopatch_candidates.py` ·
  `test_autopatch_execute.py` 이중 인용)의 두 번째 파일을 표에 담지 않는다. v0.1.0(`db95781`)부터
  존재해온 결함(`git show`로 확인) — 이번 회차 편집이 만든 것이 아니다. N8과 같은 결함급(행이
  일부 파일만 담고 나머지를 누락)이며, round4가 "무결"이라 인증한 바로 그 배치(001-014) 안에서
  나왔다는 점이 이번 회차 공정 관찰의 근거다.

**축별 점수**: Clarity 1.0(무변화) · Completeness 0.75(N7은 깨끗이 닫혔으나 N10이 같은 결함급을
같은 표에서 재도입 — round4와 동일 밴드, 이산 루브릭상 항목 수와 무관하게 0이 아니면 0.75) ·
Testability 1.0(무변화) · Traceability 1.0(무변화 — N8~N10은 §6.2 국소, SSOT 무영향).

**공정 관찰(과제 명시 요청)**: round2→round3의 "수정이 직접 새 결함을 낳는" 하위 패턴은 두 회차
연속(round3→round4, round4→round5) 재발하지 않았다 — N7 분리 편집 자체는 `git diff`로 확인된 대로
깨끗하다. 그러나 더 넓은 패턴은 이번 회차가 한층 더 구체적으로 보여준다: round4가 "전수"라 부른
스윕조차 "행 배정이 맞는가"만 확인했을 뿐 "행이 그 AC가 인용하는 모든 파일을 담는가"는 확인하지
않았다 — AC-004(이중 인용)가 그 사각지대에 있었다. §6.2는 acceptance.md 각 AC의 검증방법 필드를
손으로 베낀 중복 표이며, 5회차 연속 발견된 모든 결함(N2·N5·N7·N8·N9·N10)이 "두 문서가 불일치"
패턴이다. **권고(자문, 차단 아님)**: §6.2를 유지·재검증하는 대신 **삭제하고 "각 AC의 검증방법
필드를 보라"는 한 문장으로 대체**하는 편이 이 결함 클래스 자체를 없앤다 — 손으로 유지되는 요약은
아무리 신중히 재검증해도 다음 편집에서 또 어긋날 수 있다.

**회귀 워치(미발동)**: N8·N9가 이제 2회 연속(round4, round5) 미반영으로 남았다 — 정체 감지
조항은 3회 연속을 요구하므로 아직 미해당이나, round6이 있다면 주시 대상이다.

**권고**: 재시도 상한(3회차) 이후 재량 위임 검증이므로 6회차 의무 아님. N8·N9·N10을 한 번에 묶어
경량 패치하거나, 공정 관찰의 구조적 대안(§6.2 삭제)을 고려하기를 권한다.

### 6회차 (round6) — 2026-08-06 — plan-auditor 독립 감사 (재시도 상한 이후, 오케스트레이터 재량 위임)

**판정: PASS** — Overall Score **1.000**(조화평균, round5(0.923)보다 **+0.077 개선** — 역행 아님,
LEAN 점수 역행 STOP 미해당). 전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round6.md`

**감사 대상**: round5 이후 오케스트레이터(작성자, 감사 에이전트 아님)가 직접 손댄 `design.md`
§6.2 — 8행 표 전체를 삭제하고 "유일한 출처는 acceptance.md 각 AC의 검증 방법 줄" 이라는 안내
문단으로 대체(v0.1.3), 상태줄도 "1·2회차 지적 반영" → "1~5회차 지적 반영 · §6.2 폐지"로 갱신.
`progress.md` §E.1 `known_gaps`에 `[구조적으로 해소 · 재검증 대상 아님]` 접두로 기록되었으나, 그
항목 자신이 "폐지가 다른 참조를 깨지 않았는지는 6회차 독립 재확인 전까지 미검증으로 취급"이라고
명시한 바로 그 주장을 원문 대조로 독립 검증했다.

**N8·N9·N10 전량 genuinely CLOSED 확인**(작성자의 "구조적으로 해소" 주장을 신뢰하지 않고 6가지
과제로 독립 재검증): (1) §6.2 표가 진짜로 삭제되었고 잔여 표·주석 표 없음을 직접 읽어 확인. (2)
6개 아티팩트 전체를 "§6.2"·"design.md §6" 패턴으로 광역 재스캔 — §6.2를 권위 출처로 참조하는
곳 0건(발견된 매치는 전부 다른 절(§2.3·§5) 참조이거나 progress.md 자체 감사기록). (3) N8·N10의
실제 대상이었던 AC-004·AC-025 자신의 검증방법 필드를 직접 읽어 두 파일 모두 필드 안에 이미
완전히 명시되어 있었음을 확인 — 삭제가 정보를 옮긴 게 아니라 부정확한 사본만 제거했음을 실증.
(4) 새 안내 문단 자체에 과장·잘못된 리포트 경로·구조 넘버링 붕괴 없음을 확인(§6 넘버링 §1~§8
전부 재추출, 간극·중복 없음, §6.2 제목 자체는 보존되어 있어 참조 넘버링 붕괴 없음). N9는 상태줄
자체가 "1~5회차 지적 반영"으로 갱신되어 직접 재확인으로 해소 확인.

**신규 지적 0건.** 과제가 명시 요청한 "새 지적을 감추지 말 것"에 따라 인용 정밀도 관점(§6.2 폐지
사유 인용이 "round5 N7/N8/N10"만 들고 N9를 뺀 점)을 별도로 조사했으나, N9는 §6.2 표-드리프트와
다른 결함급(같은 파일의 별개 상태줄 문제)이며 같은 편집의 다른 훅으로 이미 해소되어 있어 결함으로
접수하지 않았다(전문 참조).

**축별 점수**: Clarity 1.0(무변화) · **Completeness 0.75→1.0**(N7은 round5가, N8·N9·N10은 이번
회차가 각각 원문 대조로 genuinely CLOSED 확인 — round1 이후 최초로 4개 축 전부 잔여 결함 0건) ·
Testability 1.0(무변화) · Traceability 1.0(§C.0a 9행을 plan.md M0~M8 `AC` 줄과 행 단위로 재대조,
합 27 확인).

**공정 관찰 마무리**: round2~round5에 걸쳐 4연속으로 새 결함을 낸 §6.2가 이번 회차로 완전히
사라졌다 — round5 리포트가 제안한 구조적 대안이 실행되었고, 독립 검증으로 그 대안이 실제로
결함 클래스 자체를 제거했음이 확인됐다(표가 없으므로 더 이상 드리프트할 대상이 없다). `plan.md
§E 테스트 골격`이 이미 파일→주제 매핑을 독립적으로 제공하고 있어 온보딩 가독성 손실도 크지
않다는 점도 확인했다(전문 과제 6 참조).

**회귀 워치**: N8·N9가 2회 연속(round4·round5) 미반영이었으나 3회 연속에 도달하기 전(이번
회차)에 해소되어 정체(stagnation) 플래그는 발동하지 않았다.

**권고**: 4연속 라운드 재발 패턴이 근본 원인(수기 사본 구조) 제거로 종결됨. 잔여 결함 0건 —
추가 delta-check 불필요. Implementation Kickoff Approval로 진행 가능(plan-phase 관점에서;
M0 라이브 세션 일정·테스트 쇼파일 확보는 run-phase 착수 전제이며 plan-audit 지적 사항 아님).

---

## §E.2 Run-phase Evidence

(마일스톤별 증거를 기록한다. M0는 `GO:` / `NEGATIVE:` / `INCONCLUSIVE:` 접두 행으로
`ASSUMPTION-71`~`-75` 판정을 남긴다.)

### M0 checkpoint — live access blocked (2026-08-06 10:42 KST)

**상태: BLOCKED — M0 전제 측정 미착수.** Implementation Kickoff Approval은 통과했으나,
현재 디스패치에서 실기 onPC/responder 왕복이 성립하지 않아 `ASSUMPTION-71`~`75`에
`GO:` / `NEGATIVE:` / `INCONCLUSIVE:` 판정 행을 쓰지 않는다. 이 판정 행들은 실제 라이브
증거가 있을 때만 추가한다.

**실측한 환경 값**: `resolve_effective_settings()` 기준 site config는
`console_host=127.0.0.1`, `console_port=8000`, `receive_port=9005`, `osc_slot=2`,
`plugin_import_dir=~/MALightingTechnology/gma3_library/datapools/plugins`.

**읽기 전용 프로브 결과**:

| probe | command | result |
|---|---|---|
| FixtureType root | `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9005 --path "Patch/FixtureTypes" --skip-exec --wait 3` | `ping` timeout · `state` timeout · `result: FAIL` |
| reply-port control | `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9000 --path "Patch/FixtureTypes" --skip-exec --wait 3` | `ping` timeout · `state` timeout · `result: FAIL` |
| existing DataPool root | `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9005 --path "DataPool/Sequences" --skip-exec --wait 3` | `ping` timeout · `state` timeout · `result: FAIL` |
| passive receive check | `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9005 --diagnose --wait 3` | listened for 3s; no OSC messages observed |

**Orca coordinator decision**: `record_blocked`. Coordinator instructed this worker to record M0 as blocked
using the observed timeout evidence and missing immediate destructive-write/showfile details, and to not proceed
to AddFixtures or M0-dependent implementation milestones.

**후속 차단 사유**:

- 테스트 쇼파일의 실제 이름/상태를 이 디스패치에서 관측하지 못했다.
- `ASSUMPTION-73`·`74`의 AddFixtures 측정은 파괴적 쓰기라 즉시 승인 없이는 수행하지 않았다.
- `plan.md` §A.2·§B M0가 **M2·M3·M6** 설계를 M0 판정에 의존시켜 두었으므로 **M2 이후**를 착수하지
  않는다. **[정정 · 후속 디스패치]** 이 절의 최초 기록은 "M1 이후 코드 마일스톤도 착수하지 않는다"고
  적었으나 그것은 과했다 — `plan.md` §A.2가 막는 것은 "M2 이후"이고 M1은 콘솔 무접촉이라
  차단 대상이 아니다. M1은 아래 절에서 완료되었다.

### M1 — 패치 후보 입력 모델 (완료)

**상태: COMPLETE — M1은 콘솔 무접촉 인메모리 리포트 payload 범위에서 완료.** 직전 M0 checkpoint의
"M1 이후 코드 마일스톤도 착수하지 않는다" 판단은 이번 디스패치 handoff가 정정했다. 근거:
`plan.md` §A.2 문구는 "M0 없이 M2 이후를 착수하지 않는다"이며, M1의 AC-002·003·004는
1단계 리포트 payload 기반이라 라이브 콘솔 없이 검증 가능하다.

**TDD RED 증거**: `uv run pytest server/tests/test_autopatch_candidates.py -q` →
`ModuleNotFoundError: No module named 'server.vwx.patchplan'`, `1 error in 0.06s`.

**구현 산출**:

- `server/vwx/verdicts.py` — `candidate_rejection_reason` · `selection_error_reason` 닫힌 어휘와
  라벨표-어휘 키집합 일치 검증. 후보 거부 사유는 `comparison_not_performed` ·
  `invalid_report_payload` · `multi_system_mapping_absent`, 선택 오류 사유는 `unknown_candidate_id`.
- `server/vwx/patchplan.py` — `build_patch_plan(report, selected=None, dry_run=True)` 리포트 전용
  후보 정규화, 결정적 후보 ID, 항목 단위 선택, 구조화 거부/선택 오류, 드라이런 대상 표 산출.
  M2·M3·M4 산출물인 FID·모드·점유폭·Lua 소스는 추측하지 않고 `None` + `deferred_to_*` 표식으로 둔다.
- `server/tests/test_autopatch_candidates.py` — AC-AUTOPATCH-002·003 전체, AC-AUTOPATCH-004 부분
  비공허 테스트 13건.

**AC 판정**:

- AC-AUTOPATCH-002: PASS. `test_candidates_are_derived_only_from_missing_in_console_without_new_reads`,
  `test_reader_and_console_recorders_are_nonvacuous_on_a_phase_one_control_path`,
  `test_diffs_not_performed_is_rejected_with_the_report_reason_quoted`,
  `test_multi_system_mapping_absent_skip_rejects_as_structured_payload`로 검증.
- AC-AUTOPATCH-003: PASS. `test_candidate_ids_are_stable_for_the_same_report_payload`,
  `test_default_selection_has_zero_targets_and_explicit_selection_targets_only_that_item`,
  `test_unknown_candidate_id_is_reported_as_an_error_not_silently_ignored`로 검증.
- AC-AUTOPATCH-004: PARTIAL. `dry_run` 생략 기본값, 대상 표 필수 열, `address_basis` 전제 문구,
  비가역 경고는 `test_dry_run_is_the_default_and_target_table_carries_required_unresolved_columns`,
  `test_absolute_back_calculated_basis_reuses_phase_one_premise_note`,
  `test_direct_address_basis_does_not_emit_the_back_calculation_note`,
  `test_irreversible_warning_is_present_and_the_absence_checker_is_nonvacuous`로 검증. Lua 소스 전문은
  `server/vwx/luagen.py`가 M4 산출물이고 주소 계획이 `ASSUMPTION-72` 판정에 의존하므로 M1에서
  완결 주장하지 않는다.

**비공허성 대조군**:

- 도면 재판독 0건: planner 호출에서 `RecordingDrawingReader.calls == []`를 assert했고,
  대조군 `exercise_phase_one_recorders()`에서 같은 기록기가 1건을 잡음을 assert.
- 실측 호출 0건: planner 호출에서 `RecordingConsolePort.state_calls/property_calls == []`를 assert했고,
  대조군에서 `read_inventory()` 경유 호출 기록이 실제로 생김을 assert.
- 기본 비선택 0건: `selected` 생략 시 `targets == []`를 assert했고, 특정 ID 1건 선택 시 정확히
  그 1건만 대상이 됨을 같은 테스트에서 assert.
- 비가역 경고 부재 검출: 결과 payload에서 warning을 제거한 사본을 검사해 `AssertionError`가
  실제로 발생함을 `with pytest.raises(AssertionError)`로 assert.

**실측 결과**:

| command | result |
|---|---|
| `uv run pytest server/tests/test_autopatch_candidates.py -q` | `13 passed in 0.06s` |
| `uv run pytest server/tests -q` | `4911 passed, 7 skipped, 1 warning in 91.81s` |
| `uv run ruff check server/vwx server/tests/test_autopatch_candidates.py` | `All checks passed!` |
| `git diff --stat -- console/lua server/safety server/prechk server/paperwork server/looks` | 빈 출력(PRESERVE 0-diff) |
| `uv run python -c '...build_patch_plan(report, selected=[candidate_id])...'` | `{'ok': True, 'dry_run': True, 'target_count': 1, 'lua_source': None, 'warnings': 1}` |

### M0 라이브 세션 1차 — 읽기 프로브 3건 판정 (2026-08-06, 오케스트레이터 직접 실측)

**세션 성립.** onPC를 기동하자 이전 세션의 OSC 설정이 유지되어 responder 왕복이 즉시 성립했다 —
직전 checkpoint의 BLOCKED 사유(프로브 timeout)는 **콘솔 미기동**이 원인이었고 설정 문제가 아니었다.

```
uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 \
  --listen-port 9005 --skip-exec --wait 4
  [PASS] ping: ok   live version=1.6.1 plugin=CopilotResponder
  [PASS] state: ok  node={'childCount': 21, 'class': 'Sequences'} children=18
```

**측정 도구**: `tools/console_probe.py`(게이트 하위 M0 전용 프로브, FXLIB·SPATIAL·GROUPGEN M0에서
이미 쓰인 도구). 아래 3건은 **전부 읽기 전용**이며 콘솔에 아무것도 쓰지 않았다.

**responder 버전 드리프트 고지**: 라이브 responder는 **1.6.1**인데 저장소 `console/lua/`는
**1.5.0**이다(299줄 차이). 아래 판정은 **1.6.1 동작에 대한 실측**이다. 저장소 사본이 더 낡았으므로
덮어쓰지 않았고, `console/lua/**`는 본 SPEC의 PRESERVE라 여기서 조정하지 않는다 — 별도 건이다.

#### `GO: ASSUMPTION-71` — FID는 콘솔에서 읽히는 프로퍼티다

**판정 근거가 성립하는 쇼파일이다.** AC-AUTOPATCH-001 ②가 요구한 **슬롯≠FID** 조건을 현재 로드된
쇼파일이 이미 만족한다 — 슬롯 `n` → FID `n+19`가 표본 7개 전부에서 일관된다.

| slot | FID | Patch | FixtureType(표시문자열) | Mode(표시문자열) |
|---|---|---|---|---|
| 1 | 20 | 3.001 | `FixtureType 3` | `2 Mode 2` |
| 2 | 21 | 3.017 | `FixtureType 3` | `2 Mode 2` |
| 3 | 22 | 3.033 | `FixtureType 3` | `2 Mode 2` |
| 4 | 23 | 3.049 | `FixtureType 3` | `2 Mode 2` |
| 5 | 24 | 3.065 | `FixtureType 3` | `2 Mode 2` |
| 9 | 28 | 3.129 | `FixtureType 3` | `2 Mode 2` |
| 14 | 33 | 3.209 | `FixtureType 3` | `2 Mode 2` |

읽기 가능한 프로퍼티 이름: `FID` · `Fid` · `fid` · `No` · `no` — 다섯 이름이 **모두 같은 값 20**을
반환한다(slot 1). `FixtureId`/`FixtureID`는 not readable. `CID`는 readable이나 값이 nil.
`IDType` = `Fixture`.

**부수 성과 — `PROTOCOL.md:319-321`의 미해소 모호성이 해소됐다.** 그 문서는 ASSUMPTION-7 프로브가
읽는 `child.no`가 슬롯인지 FID인지 "responder가 둘을 구별할 수 없다"고 적었다. 슬롯≠FID 쇼파일에서
`no`가 **FID(20)를 반환**하므로 `no`는 슬롯이 아니라 FID다. (본 SPEC은 이 사실을 소비만 하고
`server/prechk/**`·`console/lua/**`를 고치지 않는다 — 둘 다 PRESERVE다.)

**요구에 미치는 영향**: REQ-AUTOPATCH-009의 **충돌 사전검사를 켠다**(GO 분기). 따라서
REQ-AUTOPATCH-026의 `fid_range_visually_confirmed_empty` 강제는 **발동하지 않는다**
(`spec.md` REQ-AUTOPATCH-026 마지막 문장 — GO 분기에서는 요구하지 않는다).

#### `GO(한정): ASSUMPTION-72` — 드릴다운은 되지만 점유폭은 얻지 못한다

**되는 것**: `Patch/FixtureTypes` 열거(3종: `Robin MMX Spot` · `FixtureType 2` ·
`Robin LEDBeam 350`) → 타입 드릴다운(`DMXModes` 자식 존재) → 모드 열거 → 모드 이름 읽기
(`prop:…/DMXModes/1|Name` → `Mode 1`) → `DMXChannels` 자식 수 읽기.

| 타입 | 모드 | `DMXChannels` childCount |
|---|---|---|
| Robin MMX Spot | Mode 1 · 2 · 3 | 29 · 29 · 29 |
| Robin MMX Spot | Mode 4 | 31 |
| Robin LEDBeam 350 | Mode 1 · 2 | 14 · 14 |
| Robin LEDBeam 350 | Mode 3 | 16 |

**안 되는 것 — 그리고 이것이 핵심이다**: `DMXChannels` childCount는 **DMX 점유폭이 아니다.**
실측 반증: 위 표의 패치된 픽스처는 전부 `Robin LEDBeam 350` **Mode 2**(childCount **14**)인데
실제 주소 간격은 **16**이다(`3.001 → 3.017 → 3.033 …`, slot 14가 `3.209 = 1 + 13x16`으로 일관).
**14를 점유폭으로 쓰면 픽스처마다 2채널씩 겹친다** — `design.md` §4 R4가 경고한 주소 계획 붕괴다.

정확한 점유폭 획득 시도, 전부 실패:

| 시도 | 결과 |
|---|---|
| `prop:…/DMXModes/1\|DMXFootprint` | **존재하나 `table: 0x600001b703c0`** — responder 1.6.1이 테이블을 직렬화하지 못한다(`inventory.py:64-72` POINTER_TEXT 사례) |
| `prop:…/DMXModes/1\|Footprint` · `ChannelCount` · `Channels` · `ChannelWidth` · `Width` · `Size` | 전부 `property not readable` |
| `prop:…/DMXChannels/1\|Offset` · `Resolution` | 전부 `property not readable` |
| `state:…/DMXModes/1/DMXFootprint` | `path segment not found` — 프로퍼티이지 자식 객체가 아니다 |
| `prop:…/DMXChannels/1\|DMXBreak` | readable(`1`) — 점유폭과 무관 |

**요구에 미치는 영향**: REQ-AUTOPATCH-014(점유폭 일치 확인)를 **읽기 표면만으로는 충족할 수 없다.**
`plan.md` §A.3의 `ASSUMPTION-72` 부정 처리를 적용한다 — 점유폭 일치 확인 **descope**, 모드 선택은
사용자 확인 단독, 드라이런 표에 "점유폭 미검증" 열 추가. 근본 해결(responder가 `DMXFootprint`
테이블을 직렬화)은 `console/lua/**` 변경이 필요하고 그것은 본 SPEC의 PRESERVE이므로 **범위 밖**이다.

#### `NEGATIVE: ASSUMPTION-75` — Patch 편집기 상태는 감지되지 않는다

객체 트리를 전수 열거해 편집기/윈도우/커맨드 목적지를 노출하는 객체를 찾았으나 **0건**이다.

| 열거한 경로 | 자식 |
|---|---|
| `Root` | MessageCenter · StationSettings · Interfaces · KeyRegistry · MAnetSocket · Cloud · NDI · UsbNotifier · WebServer · VirtualKeys · HardwareConfigurations · KeyboardLayouts · ShowData · TimecodeSlots |
| `ShowData` | ShowSettings · MediaPools · Scribbles · Appearances · Tags · GelPools · Meshes · RDMData · LivePatch · Patch · PsrPatch · Output · Masters · DataPools |
| `Patch` | DmxCurves · AttributeDefinitions · Layers · Classes · PsrExtraData · FixtureTypes · Stages · UIChannels · RTChannels · IDTypes · DmxUniverses · DmxAddresses · FixtureTypesOverview · PatchFilter |
| `ShowData/ShowSettings` | DefaultPlaybackSettings · GlobalSettings · MidiSettings · SoundSettings · TimecodeStatuses · GlobalVariables · AddonVariables · ShowMetaData · ShowDeletedData · ScreenEncoder |
| `ShowData/DataPools` | Default · Preview |

보조 확인: `orca computer list-windows --app grandMA3` → `windows: []`,
`get-app-state` → `window_not_found`. grandMA3는 접근성 API에 창을 노출하지 않아 **GUI 관측 경로도
없다.** `ChangeDestination`/`CD` 전송은 룰북이 무조건 금지하므로 시도하지 않았다.

**요구에 미치는 영향**: `plan.md` §A.3대로 **사전 안내를 포기하고 사후 안내만** 한다 —
REQ-AUTOPATCH-024가 이미 그 경로("생성 0건이면 Patch > Fixtures 편집기를 먼저 열라")를 규정한다.

#### 미판정 2건 — 파괴적 측정, 쇼파일 확인 대기

`ASSUMPTION-73`(다중 유니버스 `patch` 배열) · `ASSUMPTION-74`(패치 직후 관측)는 **AddFixtures 실제
쓰기**를 요구한다. 현재 로드된 쇼파일은 **픽스처 39대가 패치된 리그**이며(`Patch/Stages/1/Fixtures`
childCount = 39), 이름을 읽을 수 있는 경로가 없다(`ShowData|ShowName`·`ShowFileName` 둘 다
not readable, `ShowMetaData` childCount 0). **테스트 쇼파일임이 확인되지 않았다.**

`plan.md` §C는 "세션 시작 전 사용자에게 쇼파일이 테스트용임을 확인받고 그 확인을 `progress.md`에
기록한다"를 요구한다. 그 확인은 오케스트레이터가 자체 발급할 수 없다 — **73·74는 확인 전까지
미판정으로 남긴다.** 운영 쇼파일로 대체하지 않는다(`plan.md` §B M0 진입 전제 D6).

#### 후속 마일스톤 확정 사항

| 마일스톤 | M0가 확정한 것 |
|---|---|
| M2 | **충돌 사전검사 ON**(ASSUMPTION-71 GO). REQ-AUTOPATCH-026 확인 필드 강제 **미발동**. `FID` 프로퍼티명으로 읽는다 |
| M3 | **점유폭 일치 확인 descope**(ASSUMPTION-72 한정). 드라이런 표에 "점유폭 미검증" 열 추가. 모드 이름은 `DMXModes/<i>` 열거 + `Name` 프로퍼티로 확정 |
| M6 | 사전 안내 없음, **사후 안내만**(ASSUMPTION-75 NEGATIVE) |
| M4·M5 | ASSUMPTION-73·74 미판정이라 **주소 배열 형태와 검증 읽기 재시도 정책이 아직 확정되지 않았다** |

### M2 — FID 배정 (완료)

**상태: COMPLETE — FID 배정은 사용자 `fid_range` 안에서만 수행하며, `ASSUMPTION-71` 런타임 입력에
따라 GO 분기는 `FID` 프로퍼티 충돌 사전검사를 수행하고 부정/INCONCLUSIVE 분기는 구조화된 축소와
`fid_range_visually_confirmed_empty` 별도 확인을 요구한다.** M1 호환을 위해 `fid_range`나
`assumption_71` 등 M2 표면이 주입되지 않은 기존 `build_patch_plan()` 호출은 M1의 `deferred_to_m2`
산출을 유지한다.

**TDD RED 증거**: `uv run pytest server/tests/test_autopatch_fid.py -q` →
`ImportError: cannot import name 'ASSUMPTION_71_GO' from 'server.vwx.patchplan'`, `1 error in 0.06s`.

**구현 산출**:

- `server/vwx/patchplan.py` — `fid_range` 파라미터, `ASSUMPTION_71_*` 런타임 분기, 순차 FID 배정,
  범위 초과/기존 FID 충돌 건별 제외, `FID` 프로퍼티 기반 기존 FID 읽기, 안전망/축소/확인 감사 payload.
- `server/vwx/verdicts.py` — FID 범위 거부, 대상 제외, skipped-check 닫힌 어휘와 라벨 추가.
- `server/tests/test_autopatch_fid.py` — AC-AUTOPATCH-005·006·007·008·027 인메모리 더블 기반 9건.

**AC 판정**:

| AC | 판정 근거 | 실측 명령 · 결과 |
|---|---|---|
| AC-AUTOPATCH-005 | `test_fids_stay_inside_user_range_and_excess_targets_are_reported` — FID 100·101만 배정, 3번째 항목은 `fid_range_exhausted` 제외, 같은 입력/범위 재호출도 같은 배정 | `uv run pytest server/tests/test_autopatch_fid.py -q` → `9 passed in 0.07s` |
| AC-AUTOPATCH-006 | `test_missing_fid_range_rejects_m2_and_does_not_guess_from_slots` — M2 표면에서 `fid_range` 부재 시 `fid_range_required` 거부, `start`·`end` 입력 안내, 배정 0건 | 동 |
| AC-AUTOPATCH-007 | `test_fid_assignment_source_does_not_read_fixture_record_slot`, `test_unresolved_fid_note_is_not_assignment_basis_and_no_fixture_selection_is_generated` — `patchplan.py` AST에서 `.slot`/`'slot'` 참조 0건, `fid_note`의 `999 (미확정)` 대신 범위 FID 100 배정, payload 내 `Fixture <n>` 선택 명령 0건 | 동 |
| AC-AUTOPATCH-008 | `test_go_branch_reads_fid_property_and_excludes_existing_fid_collisions`, `test_negative_branch_skips_precheck_structurally_and_lists_all_assignments` — GO는 `Patch/Stages/1/Fixtures/<i>`에서 `FID`만 읽고 기존 100 충돌 항목 제외, 부정은 포트를 호출하지 않고 `fid_conflict_precheck_descope`를 `skipped_checks`에 기록, 양쪽 모두 대상별 FID 표를 산출 | 동 |
| AC-AUTOPATCH-027 | `test_negative_or_inconclusive_execution_requires_separate_visual_empty_confirmation`, `test_visual_confirmation_is_independent_and_audited_when_present` — 부정/INCONCLUSIVE에서 확인 필드 누락·거짓 거부, GO는 필드 없이 통과, 부정+확인 참은 통과하고 건별 row에 확인 사실 기록 | 동 |

**비공허성 대조군**:

- 추정 배정 로직: `FixtureRecord(slot=41)`에서 `slot+1` 추정 FID 42를 심은 payload를
  `assert_no_fid_assignments()`에 통과시켜 `AssertionError`가 실제 발생함을 확인.
- 슬롯 참조 AST: 가짜 소스 `record.slot`과 `row['slot']`를 `ast` 스캐너에 넣어 검출되는 대조군 확인.
- GO vs 부정 확인필드: 같은 입력에서 GO는 `fid_range_visually_confirmed_empty` 없이 통과하고,
  부정은 같은 필드 누락 시 거부되며 참일 때만 통과함을 확인.

**M0 GO 판정 소비**: `ASSUMPTION-71`은 GO로 소비해 충돌 사전검사 ON이 기본 분기이며, 기존 FID는
정규 프로퍼티명 `FID`로만 읽는다. 부정/INCONCLUSIVE 분기도 런타임 입력으로 구현·테스트했다.

**실측 결과**:

| command | result |
|---|---|
| `uv run pytest server/tests/test_autopatch_fid.py -q` | `9 passed in 0.07s` |
| `uv run pytest server/tests/test_autopatch_candidates.py -q` | `13 passed in 0.06s` |
| `uv run pytest server/tests -q` | `4920 passed, 7 skipped, 1 warning in 91.78s` |
| `uv run ruff check server/vwx server/tests/test_autopatch_*.py` | `All checks passed!` |
| `git diff --stat -- console/lua server/safety server/prechk server/paperwork server/looks` | 빈 출력(PRESERVE 0-diff) |
| 인메모리 planner driver | GO: 기존 FID 100 충돌 제외 후 101 배정. 부정: `fid_conflict_precheck_descope` 기록 후 200·201 배정 |

### M3 — FixtureType · DMXMode 해석 (완료)

**상태: COMPLETE — 타입·모드는 `Patch/FixtureTypes` 열거에서만 얻고, 퍼지 매칭 후보는 사람이
확인해야 확정되며, 부재는 항목 단위 하드 스톱이다. 점유폭 일치 확인은 `ASSUMPTION-72` 런타임
입력으로 갈라져 GO 분기는 불일치를 승인 전에 제시하고, 부정/INCONCLUSIVE 분기(= M0 실측이 만든
현실 기본값)는 확인을 descope하고 축소를 건별로 명시한다.**

**TDD RED 증거**: `uv run pytest server/tests/test_autopatch_types.py -q` →
`ModuleNotFoundError: No module named 'server.vwx.typemap'`, `1 error in 0.08s`.

**구현 산출**:

- `server/vwx/typemap.py` — 신규. `Patch/FixtureTypes` → `<t>/DMXModes` → `<m>|Name` →
  `<m>/DMXChannels` 열거·드릴다운, `rig.fuzzy_type_equal` 재사용 퍼지 매칭(새 헬퍼 신설 0건),
  별칭 재사용, 항목 단위 하드 스톱, `ASSUMPTION_72_*` 런타임 분기, `점유폭 미검증` 열을 가진
  `type_table`.
- `server/vwx/verdicts.py` — 어휘 추가: 제외 사유 `fixture_type_not_in_library` ·
  `dmx_mode_not_in_library`, skipped-check `footprint_match_descope` ·
  `fixture_type_library_truncated` · `fixture_type_library_unreadable`, 신규 닫힌 어휘
  `type_resolution_status`(4종) + 라벨.
- `server/tests/test_autopatch_types.py` — 신규 23건. 전부 `RigPort` 관례 더블 기반 인메모리,
  콘솔 접촉 0.

**AC 판정**:

| AC | 판정 근거 | 실측 명령 · 결과 |
|---|---|---|
| AC-AUTOPATCH-009 | ① `test_candidates_come_from_patch_fixture_types_enumeration_not_source_constants` — 첫 state 호출이 `Patch/FixtureTypes`이고 타입·모드 이름이 전부 열거 응답에서 나온다. ② `test_truncated_enumeration_is_reported_and_absence_is_not_asserted` — `truncated: true`면 `library_incomplete` + `fixture_type_library_truncated`이고 하드 스톱 0건, 같은 입력에서 `truncated: false`면 `library_absent` + `fixture_type_not_in_library`로 갈라진다. 열거 실패·모드 열거 실패·모드 열거 절단도 각각 부재 단정이 아님을 별도 3건이 확인 | `uv run pytest server/tests/test_autopatch_types.py -q` → `23 passed in 0.06s` |
| AC-AUTOPATCH-010 | ① `test_string_equality_alone_never_confirms_a_mapping` — 이름이 완전히 같아도 `needs_confirmation`이고 `console_type`은 `None`. ② `test_observed_vw_and_gdtf_names_both_produce_candidates` — `Robe MegaPointe`(VW)와 `Robe Lighting@MegaPointe`(GDTF) 둘 다 콘솔 `MegaPointe` 후보를 만든다. ③ `test_stored_alias_is_reused_and_the_reuse_is_visible_in_the_payload` — 별칭이 있으면 `resolved` + `confirmation_source: type_alias` + `alias_reuse` 행이 남고, 없으면 같은 입력이 `needs_confirmation`. 별칭이 라이브러리에 없는 이름을 가리키면 신뢰하지 않고 하드 스톱(`test_alias_naming_a_type_outside_the_library_is_not_trusted`) | 동 |
| AC-AUTOPATCH-011 | ① `test_only_the_unmatched_item_is_excluded_and_the_rest_proceed` — 2건 중 미대응 1건만 `hard_stops`에 실리고 나머지는 후보 제시로 진행, `ok`는 참(전체 실패 아님). ② `test_hard_stop_reason_names_the_gdtf_import_prerequisite` — 사유에 `GDTF`·`임포트` 포함. ③ `test_no_similar_name_substitute_assignment` — 미대응 항목의 `console_type`이 `None`. 모드 부재는 `dmx_mode_not_in_library`로 별도 하드 스톱 | 동 |
| AC-AUTOPATCH-012 | ① `test_go_branch_presents_the_footprint_mismatch_before_approval` — GO 분기에서 도면 16 vs 콘솔 24 불일치가 `presented_before_approval: true` + `footprint_mismatches` 행으로 나오고 상태가 `resolved`에서 `needs_confirmation`으로 강등된다(승인 전 제시). ② `test_descoped_branch_states_the_reduction_and_adds_the_unverified_column`(negative·inconclusive·기본값 3분기) — `footprint_match_descope`가 `skipped_checks`에 실리고 사유에 `DMXFootprint`·`직렬화`·`DMXChannels`·`14`·`16`이 담기며 `type_table`에 `점유폭 미검증` 열이 생긴다. 채널 수를 못 읽으면 일치로 간주하지 않고 `match: null`로 보고. ③ `test_channel_count_is_never_parsed_out_of_a_display_string` — 표시문자열 `2 Mode 2`의 열거 인덱스는 **3**(선행 숫자 2와 일부러 어긋냄)이고 채널 수는 `DMXChannels` 자식 수 16이다. ④ `test_multicell_eight_cell_mode_is_the_one_selected` — 8셀 장비에서 `Standard`가 아니라 `8 Cell Mode`(인덱스 2, 96ch)가 선택되고 GO 분기 점유폭이 일치한다 | 동 |

**비공허성 대조군 4건 — 전부 실제로 잡혔다**:

| 심은 것 | 스캐너 | 결과 |
|---|---|---|
| 라이브러리 이름 상수 `LIBRARY = "Robin MMX Spot"` · `GDTF = "Robe Lighting@MegaPointe"` | `library_name_constants` (AST 문자열 상수) | 가짜 소스에서 검출됨 · `typemap.py` 실소스는 0건 |
| 동등 확정 `designed.instrument_type == entry.name` · `type_name == "X"` · `any(key == entry.name ...)` | `equality_confirmation_locations` (AST Compare) | 3종 전부 검출됨 · 실소스 0건 |
| 대체 배정 (하드 스톱 행에 `console_type` 주입) | `assert_no_substitute_assignment` | `AssertionError` 발생 확인 |
| 표시문자열 파싱 `int(mode.name.split(' ')[0])` · `re.search(r"(\d+)", name)` | `display_string_parse_locations` | 2종 전부 검출됨 · 실소스 0건 |

**추가 뮤테이션 검증 5건**(테스트가 구현을 실제로 붙잡는지 — 각각 `typemap.py`를 일시 변조 후 복원):

| 뮤테이션 | 결과 |
|---|---|
| 별칭 없이 자동 확정 | 2건 RED |
| 퍼지 매칭을 `==`로 교체 | 4건 RED (AST 스캐너 포함) |
| 절단된 열거에서 부재 단정 | 1건 RED |
| 점유폭 불일치를 조용히 통과 | 1건 RED |
| descope 분기에서도 `DMXChannels` 읽기 | 3건 RED (`ExplodingChannelPort`가 잡음) |

**M0 GO(한정) 판정을 어떻게 소비했는가**: `ASSUMPTION-72`의 드릴다운은 되지만 점유폭은 못 얻는다는
실측을 그대로 반영해, `plan.md` §A.3의 **부정 처리를 현실 기본 분기로 삼았다** — `assumption_72`의
기본값이 `negative`이고 GO는 명시 입력이어야 한다. descope 사유에 근거를 그대로 적는다:
`DMXFootprint`는 responder 표면에서 table 포인터로만 돌아와 직렬화되지 않고, `DMXChannels` 자식
수는 점유폭이 아니다(**실측 14 vs 실제 주소 stride 16**). 근본 해결은 `console/lua/**` 변경이라
본 SPEC의 PRESERVE이며 범위 밖임을 축소 사유 문자열에 명시했다. GO 분기도 함께 구현·테스트했으므로
판정은 컴파일 타임 상수가 아니라 런타임 입력이다(M2의 `ASSUMPTION_71_*`과 같은 패턴).

**범위 경계**: `점유폭 미검증` 열은 M3 산출물인 `typemap`의 `type_table`에 있다. `patchplan`의
`target_table`과의 병합은 주소 계획을 소유하는 **M4**의 일이다 — 본 마일스톤은 `patchplan.py` ·
`server/orchestrator/tools.py`를 건드리지 않았고 `luagen.py`도 만들지 않았다.

**실측 결과**:

| command | result |
|---|---|
| `uv run pytest server/tests/test_autopatch_types.py -q` | `23 passed in 0.06s` |
| `uv run pytest server/tests/test_autopatch_candidates.py server/tests/test_autopatch_fid.py -q` | `22 passed in 0.10s` (M1·M2 회귀 0) |
| `uv run pytest server/tests -q` | `4943 passed, 7 skipped, 1 warning in 91.23s` (직전 baseline 4920 + 신규 23, 회귀 0) |
| `uv run ruff check server/vwx server/tests/test_autopatch_*.py` | `All checks passed!` |
| `git diff --stat -- console/lua server/safety server/prechk server/paperwork server/looks` | 빈 출력(PRESERVE 0-diff) |
| `uv run pytest server/tests/test_architecture.py -q` | `4 passed` (`server.bridge`·`pythonosc` 미import 경계 유지) |

**미검증 잔여**: 콘솔 접촉 0건이므로 본 마일스톤의 모든 판정은 **더블 기반**이다. 실기에서
`Patch/FixtureTypes` 열거가 대형 쇼파일에서 절단되는 실제 임계, 별칭 표의 영속화 위치,
GO 분기를 켤 수 있는 점유폭 출처(=responder 확장)는 전부 미해결이며 M8/별건 대상이다.

### M0 라이브 세션 2차 — 테스트 쇼파일 확인 · 파괴적 측정 착수 전 기록 (2026-08-06)

#### 사용자 확인 (`plan.md` §C 요구사항)

`plan.md` §C는 "세션 시작 전 사용자에게 쇼파일이 테스트용임을 확인받고, 그 확인을 `progress.md`에
기록한다"를 요구한다. **본 절이 그 기록이며, 파괴적 측정보다 앞서 쓰였다.**

| 항목 | 값 |
|---|---|
| 쇼파일 | `NewShow_2026.07.15_05.44.02UTC` (onPC 2.4.2.2 타이틀바, 사용자 스크린샷) |
| 사용자 확인 | **"그냥 이 쇼파일을 사용해도 될거 같아"** — 테스트용 사용 승인 (2026-08-06) |
| 오케스트레이터가 만든 것인가 | **아니다.** 본 세션은 콘솔 쓰기 0이었고 쇼파일 생성·로드도 하지 않았다. onPC 기동 시 이미 열려 있었다 |

**확인을 뒷받침하는 콘솔 실측 근거**(추론이 아니라 관측):

| 근거 | 관측값 |
|---|---|
| Plugins 풀 | `CopilotResponder` · `CopilotBusk`(BUSKWIZ 산출물) · `kpop_summer_twinkle` · `GenSequence100Look` — **4개 전부 본 프로젝트 생성물** |
| Macros 풀 | `Copilot Go` 1건 — 본 프로젝트 매크로 |
| 이름 형식 | `NewShow_<UTC타임스탬프>` = MA3가 새 쇼에 붙이는 기본명 |
| 저장소 교차 | `SPEC-COPILOT-DASHUI-001/progress.md:192`가 당시 **픽스처 19대**로 기록 → 현재 39대. 선행 라이브 세션(MVP·PRECHK·LOOKLIB·EXECBODY·BUSKWIZ·DASHUI) 누적으로 정합 |

운영 쇼파일이라면 `CopilotBusk`·`kpop_summer_twinkle`이 존재할 수 없다.

#### 파괴적 측정 전 사전 상태 (원복 기준선)

| 항목 | 값 |
|---|---|
| `Patch/Stages/1/Fixtures` childCount | **39** |
| 사용 중 FID | **1 … 39** (빈틈 0) |
| 사용 중 유니버스 | **1 · 2 · 3** |
| U1 주소 범위 | 1 … 437 (n=10) |
| U2 주소 범위 | 1 … 401 (n=9) |
| U3 주소 범위 | 1 … 305 (n=20) |

**테스트 자원은 기존과 완전히 분리한다** — FID `501`~`503`(기존 최대 39보다 훨씬 위),
유니버스 `10`·`11`(둘 다 미사용). 충돌 가능성 0.

#### `ASSUMPTION-71` 근거 보강 — 슬롯↔FID에 고정점이 없다

1차 세션은 표본 7개(slot 1~5·9·14)에서 `slot n → FID n+19`를 관측하고 그렇게 기록했다.
전수 조사 결과 실제 매핑은 **단순 오프셋이 아니라 회전(rotation)** 이다:

| slot | 1 | 20 | 21 | 39 |
|---|---|---|---|---|
| FID | 20 | 39 | 1 | 19 |

슬롯 1~20 → FID 20~39, 슬롯 21~39 → FID 1~19. **고정점(slot == FID)이 하나도 없다.**
1차 기록의 "표본 7개에서 `n+19`"는 그 표본 범위 안에서 정확하며, 전수 확인은 판정을 **강화**한다 —
이 쇼파일의 어떤 픽스처에서 측정해도 FID 프로브와 슬롯 프로브가 구별된다.

#### 파괴적 측정 시도 — `AddFixtures`가 조용히 `nil`을 반환한다 (미판정 유지)

**결과: `ASSUMPTION-73`·`74` 여전히 미판정.** 생성된 픽스처 **0건**(39 → 39 불변).
측정을 3회 시도했고, 실패 지점을 **단계별로 특정**했다. 실패를 성공으로 적지 않으며 판정도 내리지 않는다.

측정 도구: `tools/console_probe.py`(게이트 하위, M0 전용). 플러그인은 `deploy_plugin` 게이트 경로가
아니라 라이브러리 폴더 배치 + `Import Plugin` 경로로 넣었다 — M0 측정은 승인 채널 밖이라는
그 도구의 규약을 따른다.

**시도 1 — 편집기 닫힘 상태**

| 단계 | 결과 |
|---|---|
| `Import Plugin 'autopatch_m0_probe'` | `OK` — 풀 슬롯 5에 `AutopatchM0Probe` 생성 확인 |
| `Plugin 'AutopatchM0Probe'` | `OK` |
| `Patch/Stages/1/Fixtures` 재조회 | **39 → 39. 생성 0건** |

`exec` 결과가 `OK`인데 아무것도 만들어지지 않았다 — **`progress.md` §0 함정 4의 실물 재현이자
REQ-AUTOPATCH-023(검증 읽기가 성공의 유일한 근거)의 라이브 정당화**다. 플러그인 무오류 종료를
성공으로 삼았다면 이 SPEC은 여기서 거짓 성공을 보고했을 것이다.

**시도 2 — 사용자가 Patch > Fixtures 편집기를 연 상태**

룰북 처방(`30_plugin_patterns.md:28-29`)대로 사용자에게 편집기 개방을 요청하고 재실행했다.
결과 **동일 — 39 → 39, 생성 0건.**

**시도 3 — 실패 지점 특정 프로브(v2)**

`AddFixtures`가 왜 실패하는지 단계별로 갈라 각 분기가 플러그인 슬롯 5의 **라벨**에 판정을 쓰게 했다
(응답기가 읽을 수 있는 유일한 출력 채널 — `Printf`는 서버로 돌아오지 않는다).

| 단계 | 결과 |
|---|---|
| `Patch()` | **non-nil** |
| `Patch().FixtureTypes["Robin LEDBeam 350"]` | **해석됨** |
| `.DMXModes["Mode 1"]` | **해석됨** |
| `AddFixtures{...}` | **`nil` 반환** — 예외 아님(`pcall` 통과), 조용한 실패 |

읽어낸 라벨: **`AM0_ADD_NIL`**.

**부수 성과 — `ASSUMPTION-72`의 쓰기측 핸들 경로가 라이브로 확인됐다.**
`Patch().FixtureTypes["<이름>"].DMXModes["<이름>"]`이 실기에서 실제로 핸들을 반환한다
(REQ-AUTOPATCH-016이 요구하는 정확한 형태). 1차 세션의 `GO(한정)` 판정에서 "읽기 표면으로 점유폭을
못 얻는다"는 제약은 그대로이나, **핸들 해석 자체는 이제 미확정이 아니다.**

**배제된 원인**

| 가설 | 반증 |
|---|---|
| 타입 이름 오타 / 핸들 미해석 | 위 표 — 3단계 전부 해석됨 |
| 유니버스 10·11 미구성 | `Patch/DmxUniverses` childCount = **1024**. 10·11 전부 존재 |
| 기존 픽스처와 FID·주소 충돌 | 기존 FID 1~39 · 유니버스 1~3. 프로브는 FID 501~503 · 유니버스 10~11 |
| 예외 발생 | `pcall`이 참을 반환 — 던지지 않고 `nil`을 반환했다 |
| `ChangeDestination` 오염 | 플러그인 소스·명령 어디에도 `CD`/`ChangeDestination` 없음 |

**남은 원인 가설 — command destination의 컨텍스트 분리 (미확정)**

룰북이 지목한 원인은 하나뿐이다: `AddFixtures`는 **현재 command destination**을 읽으며 그것이
patch fixtures 레이어여야 한다. 사용자가 GUI에서 편집기를 열었는데도 OSC 경로가 실패했다는 사실은
**목적지가 세션/컨텍스트별로 분리되어 GUI 조작이 OSC 명령줄의 목적지를 바꾸지 않는다**는 가설을
가리킨다. `ChangeDestination` 전송은 룰북이 무조건 금지하므로 서버측 우회 수단이 없다.

판별 프로브를 콘솔에 배치해 두었다 — 슬롯 6 `AutopatchM0Probe3`을 **GUI에서 직접 탭**하면
GUI 사용자 컨텍스트에서 실행되며, 결과가 슬롯 5 라벨(`AM0 T1 <OK|NIL> T2 <OK|NIL>`)에 기록된다.
**OSC 대조군은 이미 확보했다: `AM0 T1 NIL T2 NIL`.**

#### 이 발견이 위협하는 것 — REQ-AUTOPATCH-018 / M5 실행 경로 (미결, 사용자 결정 대기)

GUI 탭이 성공하고 OSC가 실패한다면, `spec.md` §A 사전 확정 사실 1이 규정한 2단계 실행 경로
(`deploy_plugin` → `run_commands(["Plugin '<이름>'"])`)가 **실기에서 픽스처를 만들지 못한다.**
REQ-AUTOPATCH-018은 그 경로를 요구사항으로 못박고 있고 M5 전체가 그 위에 서 있다.

이 위험은 `spec.md` §C의 ASSUMPTION 71~75 어디에도 없다 — **plan-phase가 놓친 전제**다.
`AddFixtures`가 command destination을 읽는다는 사실은 룰북에 있었으나, "서버가 OSC로 발화한
플러그인 실행이 그 목적지를 갖는가"는 아무도 묻지 않았다.

**오케스트레이터가 임의로 승격하지 않는다.** 이것을 `ASSUMPTION-76`으로 신설하고
REQ-AUTOPATCH-018을 조정하는 것은 plan-phase 아티팩트 개정(amendment)이며 재감사 대상이다.
사용자 결정 항목으로 남긴다.

#### 근본 원인 확정 — command destination이 `TempCmdlines Cmdline 1`이고 옮길 수단이 없다

측정을 계속해 **원인을 특정했다.** 아래는 전부 라이브 실측이다.

**증거 1 — GUI 탭도 동일하게 실패한다(destination 컨텍스트 분리 가설 기각).**
슬롯 5 라벨을 `AM0 WAITING GUI TAP` 센티넬로 두고 사용자가 GUI에서 플러그인을 탭했다.
라벨이 `AM0 T1 NIL T2 NIL`로 **바뀌었다** — 실행은 됐고 결과는 OSC 경로와 **동일**하다.
GUI/OSC 컨텍스트 차이는 원인이 아니다. (부수 효과: 이후 반복 측정을 서버측에서 자유롭게 수행했다.)

**증거 2 — `patch` 배열도 유니버스도 원인이 아니다.**

| 변형 | 결과 |
|---|---|
| `patch` 배열 **생략**(룰북상 optional) | `NIL` |
| 유니버스 **1**(기존 픽스처가 사는 살아있는 유니버스), 빈 주소 `1.461` | `NIL` |

**증거 3 — `AddFixtures`는 컨테이너 메서드가 아니다.**
`Patch().Stages[1].Fixtures`는 `userdata`로 해석되고 `:Count()` = **39**로 정상 동작하나,
`.AddFixtures` 필드는 **nil**이다. 즉 대상을 명시적으로 지정해 호출할 방법이 없고,
**앰비언트 목적지에만 의존하는 전역 함수**다.

**증거 4 — 현재 목적지를 직접 읽었다.**

```
CmdObj() → class = Cmdline · name = 'Cmdline 1' · AddrNative = 'TempCmdlines Cmdline 1'
```

patch fixtures 레이어가 아니라 **임시 명령줄 객체**다. 룰북이 전제한
"`…/Patch/Stages/Stage 1/Fixtures>` 상태"가 플러그인 실행 시점에 성립하지 않는다.

**증거 5 — 목적지를 옮길 Lua API가 존재하지 않는다.** (존재 여부만 조회, 호출 없음)

| 심볼 | 존재 |
|---|---|
| `SetCmdObj` · `SetDestination` · `ChangeDestination`(Lua 전역) | **전부 없음** |
| `CurrentCommandLine()` | **없음**(이 빌드에서 미제공 — 선행 세션의 `CheckDest.xml`이 쓰던 API다) |
| `Patch` · `AddFixtures` · `CmdIndirect` · `CurrentExecPage` | function |
| `Obj` | table |

`CurrentCommandLine().destination`에 컨테이너를 대입하는 비-CD 경로도 시도했으나
`CurrentCommandLine()` 자체가 없어 성립하지 않았다.

**증거 6 — 선행 세션이 같은 벽에 부딪혔다(콘솔 라이브러리 고고학).**
콘솔 플러그인 라이브러리 폴더에 본 세션과 무관한 선행 산물이 남아 있다:
`CheckDest.xml` · `CheckDest2.xml`(목적지 판독 시도) · `patch_here.xml`(CD 없이 현재 목적지로
패치 시도) · `patch_proper.xml` · `PatchMMX.xml` · `patch_order.xml` · `patch_rest.xml`.
`patch_proper.xml`을 디코딩하면 **`Cmd("ChangeDestination " .. Patch():Addr(), undo)`로 목적지를
옮긴 뒤 `AddFixtures`를 부르고 다시 `ChangeDestination Root`로 되돌리는** 구조다
(`CreateUndo`/`CloseUndo` 세션 안에서). 즉 선행 세션도 CD 없이는 성립하지 않는다고 판단해
CD 경로를 만들었다. 그 결과는 이 파일들만으로 알 수 없다.

#### 판정

```
INCONCLUSIVE: ASSUMPTION-73 — 다중 유니버스 patch 배열. AddFixtures가 어떤 인자로도
              실행되지 않아 배열 의미론을 관측할 기회 자체가 없었다.
INCONCLUSIVE: ASSUMPTION-74 — 패치 직후 관측. 생성이 0건이라 관측 대상이 없었다.
```

`plan.md` §A.3의 부정 처리를 적용한다(INCONCLUSIVE는 부정과 동일 취급):
`ASSUMPTION-73` → 유니버스별 분할 실행으로 대체하되 **그 대체안도 미검증**이다.
`ASSUMPTION-74` → 검증 읽기에 재시도 대기를 넣되 미관측 시 "확인 불가" 보고.

**M0 최종: 5건 중 3건 판정(71 GO · 72 GO(한정) · 75 NEGATIVE), 2건 INCONCLUSIVE.**
`plan.md` §B M0 D6에 따라 **M8은 BLOCKED로 남고 SPEC은 완결되지 않는다.**

#### 이것이 무효화하는 plan-phase 전제 — 사용자 결정 필요

`spec.md` §A **"사전 확정 사실 (조사 확정 — 재질의 금지)"** 의 두 항목이 이 빌드에서
**동시에 성립할 수 없다**:

| # | 내용 | 실측 결과 |
|---|---|---|
| 1 | 패치는 정확히 2단계 — `deploy_plugin` → `run_commands(["Plugin '<이름>'"])` | 그 경로로는 목적지가 `TempCmdlines Cmdline 1`이라 **항상 0건 생성** |
| 2 | `ChangeDestination`/`CD`를 **어디에서도** 보내면 안 된다 | 목적지를 옮길 다른 수단이 **존재하지 않음**(증거 5) |

1을 지키면서 2를 지키면 **픽스처가 만들어지지 않는다.** 이는 조사 부족이 아니라
**plan-phase가 놓친 전제**다 — 룰북은 "`AddFixtures`가 현재 목적지를 읽는다"까지 적었으나
"서버가 발화한 플러그인 실행이 그 목적지를 갖는가"는 아무도 묻지 않았다.
ASSUMPTION-71~75 어디에도 이 항목이 없다.

**오케스트레이터는 다음 중 어느 것도 임의로 하지 않는다** — 전부 사용자 결정이다:

| 선택지 | 내용 | 대가 |
|---|---|---|
| A | **CD 경로를 M0 측정으로 1회 승인** — `patch_proper.xml` 방식(`Patch():Addr()`로 CD → `AddFixtures` → `CD Root`, undo 세션)을 테스트 쇼파일에서 측정. 룰북의 CD 금지가 과일반화인지 실측으로 판정한다 | `spec.md` §A 사전 확정 사실 2 · `design.md` §7 안티패턴 1을 **의도적으로 1회 위반**. 승인 없이는 불가 |
| B | **`ASSUMPTION-76` 신설 + REQ-AUTOPATCH-018 조정** — plan-phase amendment. spec/plan/acceptance/design 개정 후 **plan-auditor 재감사** | 아티팩트 개정 + 재감사 비용. round6 PASS 1.000이 재평가된다 |
| C | **여기서 마감** — 73·74 INCONCLUSIVE 확정, M8 BLOCKED, SPEC 미완결로 기록 | M4~M8 미착수. M1·M2·M3 성과는 보존 |

#### 콘솔 잔여물 — **전량 정리 완료**

세션 종료 시점 실측(`plan.md` §C "세션 후 생성물 제거" 이행):

| 항목 | 세션 전 | 세션 후 | 상태 |
|---|---|---|---|
| `Patch/Stages/1/Fixtures` | 39 | **39** | 무손상 — 생성 0건이었으므로 삭제할 픽스처도 없었다 |
| Plugins 풀 | 4 (`CopilotResponder`·`CopilotBusk`·`kpop_summer_twinkle`·`GenSequence100Look`) | **4 (동일)** | 프로브 8종 전량 `Delete Plugin` 완료 |
| Macros 풀 | 1 (`Copilot Go`) | **1 (동일)** | 프로브가 매크로를 만들지 않았다 |
| 라이브러리 폴더 | — | — | `autopatch_m0_probe{,2..7}` · `am0p8` 파일 전량 삭제 |
| FID · 유니버스 | 1~39 · U1~3 | **동일** | 프로브는 FID 501~503 · U10~11만 겨냥했고 하나도 생성되지 않았다 |

저장소 무변경: 프로브 파일은 전부 콘솔 라이브러리 폴더였고 `console/lua/**`(PRESERVE)는 무접촉이다
(`git diff --stat -- console/lua` 빈 출력).

### M0 라이브 세션 3차 — `ChangeDestination` 승인 측정 (2026-08-06)

#### 승인 기록

사용자가 **"쓰고 측정해라"** 로 `ChangeDestination` 1회 사용을 명시 승인했다(2026-08-06).
이는 `spec.md` §A 사전 확정 사실 2 · `design.md` §7 안티패턴 1을 **의도적으로 위반하는
측정**이며, 위반 사실과 승인 근거를 여기 남긴다. 생성 코드에 CD를 넣는 것이 아니라
**M0 측정 프로브에 한정**된다 — REQ-AUTOPATCH-017(생성기 산출물의 CD 금지)은 불변이다.

#### 측정 결과 — CD로도 목적지를 옮기지 못한다

| # | 경로 | CD 명령 결과 | 이후 `CmdObj()` | `AddFixtures` |
|---|---|---|---|---|
| 1 | 플러그인 내부 `Cmd("ChangeDestination " .. Patch():Addr(), undo)`<br/>(`patch_proper.xml` 방식, `CreateUndo`/`CloseUndo`로 감쌈) | — | `TempCmdlines Cmdline 1` **불변** | `T1 NIL · T2 NIL` |
| 2 | 플러그인 내부 CD, 대상을 `Fixtures:AddrNative()`로 교체 | — | **불변** | — |
| 3 | OSC 명령줄 `ChangeDestination 149712`(숫자 주소) | **`Failed`** | 불변 | `T1 NIL · T2 NIL` |
| 4 | OSC 명령줄 `ChangeDestination ShowData.LivePatch.Stages.'Stage 1'.Fixtures` | **`OK`** | **불변** | `T1 NIL · T2 NIL` |
| 5 | 플러그인 내부 `CmdIndirect("ChangeDestination " .. 위 경로)` | 호출 성공 | **불변** | `T1 NIL` |

**기계적 원인**: `Cmd()`·OSC exec는 호출마다 **일회용 임시 명령줄**에서 실행된다.
CD는 그 임시 명령줄의 목적지를 바꾸고 함께 소멸한다 — 플러그인이 `AddFixtures`를 부를 때
보는 앰비언트 목적지에는 도달하지 못한다. 4번이 `OK`를 반환하고도 다음 호출에 남지 않는 것이
그 직접 증거다.

#### 확보한 부수 사실 (후속 SPEC 자산)

| 사실 | 값 |
|---|---|
| `Patch()`가 가리키는 실제 객체 | **`ShowData.LivePatch`** (`ShowData.Patch`가 아니다) |
| Fixtures 컨테이너 네이티브 경로 | `ShowData.LivePatch.Stages.'Stage 1'.Fixtures` |
| 동 숫자 주소 | `149712` |
| 유효한 CD 인자 형식 | 위 **경로 형식은 `OK`**, **숫자 주소는 `Failed`**, `LivePatch` 단독은 `Failed`, `Patch`·`Root`는 `OK` |
| 라벨 문자열 특성 | MA3 라벨이 `.`·`/` 구분자를 제거한다(경로를 라벨로 실어 나를 때 주의) |

#### 남은 단 하나의 시나리오 — 룰북이 실제로 기술한 상태

지금까지의 GUI 탭 측정은 **콘솔 메인 명령줄의 목적지를 명시적으로 옮기지 않은 채** 수행됐다.
사용자는 Patch 편집기 **창**을 열었을 뿐이고, 그것이 메인 명령줄 목적지를 옮긴다는 보장이 없다.
룰북이 기술한 상태는 정확히 이것이다:

> `AddFixtures`는 콘솔의 **현재 command destination**을 읽으며, 그것은 이미 patch fixtures
> 레이어다 — **프롬프트가 `…/Patch/Stages/Stage 1/Fixtures>` 로 읽히기 때문**이다.

즉 **프롬프트 자체가 그 경로여야** 한다. 미측정 상태로 남은 시나리오:
콘솔 메인 명령줄에 직접 `ChangeDestination ShowData.LivePatch.Stages.'Stage 1'.Fixtures`를
입력해 프롬프트를 옮긴 뒤, GUI에서 플러그인을 탭한다. 이 경로만 남았고 프로브를 배치해 두었다
(슬롯 6 `AM0FINAL`, 결과는 슬롯 5 `AM0 RESULT HERE` 라벨로 회수).

이 시나리오가 성공하면 **서버 자동화로는 패치할 수 없고 사람이 목적지를 잡아 줘야 한다**는
결론이 되며, 그것은 REQ-AUTOPATCH-018과 M5 설계를 근본에서 바꾼다.
실패하면 이 빌드에서 `AddFixtures` 경로 자체가 성립하지 않는다는 결론이다.

---

## §E.3 Run-phase Audit-Ready Signal

(run-phase 완료 시 기록한다.)

---

## §E.4 Sync-phase Audit-Ready Signal

(sync-phase 완료 시 기록한다.)

---

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

Decision: `sub-agent`

본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다.
`plan.md` §G의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다.
어긋나면 **본 절이 이긴다.** 본문이 채워지기 전까지 이 절은 **비어 있음이 정상**이다.

### Input Parameters

```yaml
tier: L
scope: "server/vwx 확장 + 신규 orchestrator tool + tests, but M0 blocked before code"
domain_count: 2
file_language_mix: "Python + Markdown"
concurrency_benefit: LOW
agent_teams_prereq_status: "retired / not selectable"
implementation_kickoff_approval: "passed by coordinator handoff"
```

### Mode Evaluation

| mode | result | rationale |
|---|---|---|
| trivial | not selected | Tier L SPEC이며 M0 이후 여러 코드 마일스톤이 예정되어 있다. |
| background | not selected | run-phase 증거와 차단 판단은 동기 체크포인트가 필요하다. |
| agent-team | not selected | Mode 3 is retired. |
| parallel | not selected | M0가 M2·M3·M6 설계를 직렬로 결정하므로 병렬 이득이 낮다. |
| sub-agent | selected | coding-heavy work의 기본 안전 모드이며 `plan.md` §G 권고와 일치한다. |
| workflow | not selected | 고볼륨 기계적 변환이 아니며 M0 전제 측정이 먼저 필요하다. |

### Justification

`sub-agent`를 확정한다. 이 SPEC은 콘솔 쓰기를 포함하고 M0 판정이 후속 설계를 결정하므로,
한 번에 한 마일스톤씩 진행하는 직렬 모드가 맞다. 실제 진행: M0는 라이브 접근 부재로 BLOCKED
(§E.2 M0 checkpoint), M1은 콘솔 무접촉 범위라 같은 sub-agent 모드로 완료(§E.2 M1 절).
M2 이후는 `ASSUMPTION-71`~`75` 판정 전까지 착수하지 않는다.
