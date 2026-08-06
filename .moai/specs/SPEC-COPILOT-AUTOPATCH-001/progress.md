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

---

## §E.3 Run-phase Audit-Ready Signal

(run-phase 완료 시 기록한다.)

---

## §E.4 Sync-phase Audit-Ready Signal

(sync-phase 완료 시 기록한다.)

---

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다.
`plan.md` §G의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다.
어긋나면 **본 절이 이긴다.** 본문이 채워지기 전까지 이 절은 **비어 있음이 정상**이다.
