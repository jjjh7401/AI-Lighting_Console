# 진행 기록 — SPEC-LDRECV-001

[요구사항](spec.md) · [구현 계획](plan.md) · [인수](acceptance.md)

## §E.1 Plan-phase Audit-Ready Signal

- `plan_status: audit-ready`
- `plan_complete_at: 2026-09-16` (최초 작성) → **보완 2026-09-16** (독립 plan-audit
  FAIL, 점수 ≈0.75 지적사항 D1-D7 반영, 아래 § plan-audit 보완 기록 참고)
- 산출물: `spec.md`·`plan.md`·`acceptance.md`·`design.md`·`progress.md` (**5개** —
  `research.md` 는 여전히 만들지 않았다, 근거는 `spec.md` §1.1: 선행 두 형제
  `SPEC-LDSTORE-001`(Tier M)·`SPEC-LDCOMPILE-001`(Tier L)이 같은 선택을 했고 우산의
  `research.md` 를 참조 원본으로 쓴다. `design.md` 는 이번 보완에서 신규 작성했다 —
  전면 컴포넌트 설계가 아니라 plan-audit D3·D5 가 지적한 seam 결정 3건만 다루는 최소
  분량 문서다, 근거는 `spec.md` §1.1 갱신분).
- Tier: **L** — 근거는 REQ/파일 개수 자체가 아니라 **안전 위험** 이다. REQ 개수(8건)·
  신규 파일 5개(`director_api.py`·`auth.py`·`approvals.py`·`programmer_arbiter.py`·
  `execution.py`)만 보면 REQ/파일 수 기준으로는 Tier M 범위(§ SPEC Complexity Tier:
  M = 300-1000 LOC·5-15 파일)에 들어간다. 그럼에도 Tier L 을 선택한 것은, 공유 파일
  EXTEND 2곳(`app.py`·`gate.py` — 그중 `gate.py` 는 기존 안전장치 `SafetyGate.screen()`
  의 승인 파이프라인에 새 진입점을 잇는 변경) + 콘솔 쓰기 승인·apply 실행이라는 안전
  위험 + 콘솔 게이트 3 REQ(021·024·032 각 일부)의 조합 때문이다 — **의도적으로 보수
  방향을 택했다**. `../../reports/ldplugin-001/split-proposal.md` §1 "여전히 큰 둘"
  단락이 REQ 개수만으로 tier 를 낮추지 않는 이유를 명시한다 — 이 SPEC(8 REQ)도 같은
  논리가 적용된다. (plan-audit D7 이 이 문단의 명확화를 요구했다 — 이전 판도 같은
  취지였으나 "REQ/파일 수 기준 Tier M ↔ 안전 위험 기반 Tier L" 대비를 명시적으로
  적지 않았다.)
- depends_on: `SPEC-LDSTORE-001`(completed, origin/main `f12d590e` 계열),
  `SPEC-LDCOMPILE-001`(completed, origin/main `dd3c1121` 계열). 두 상태는 로컬
  checkout(당시 origin/main 보다 6 커밋 뒤짐)이 아니라 `git show origin/main:...` 으로
  직접 확인했다(`plan.md` §7).
- **Implementation Kickoff Approval 부여됨 (2026-09-17).** 최초 작성 시점(2026-09-16)에는
  미부여였으나, iteration 2 plan-audit 처분(PASS-with-debt) 뒤 사람이 명시적으로 착수를
  승인했다 — 상세는 아래 § plan-audit 최종 처분(2026-09-17, iteration 2) 참고.
- 사람 확인 대기 항목 (plan-audit 또는 킥오프 전 해소 권장):
  1. `spec.md` §1.1 의 design.md(최소 분량)/research.md(미생성) 판단 — 다른 판단이면
     뒤집힐 수 있다.
  2. `plan.md` §2.0-가·design.md §1 — `SafetyGate` 에 새 public 메서드
     (`execute_preapproved`)를 추가해 기존 `ApprovalPort` 재질문을 건너뛰는 설계
     방향(대안 A/B/C 비교 완료, C 채택).
  3. `plan.md` §2.0-나·design.md §2 — `server/orchestrator/tools.py` 접점 **확정**:
     수정하지 않는다(lock 을 `gate.py` 내부 공유 스테이지에 둔다). 이 결정의 전제
     (`tools.py`/`session.py`/`measurement/runner.py` 가 같은 `SafetyGate` 인스턴스를
     공유한다)는 M3 착수 시 재확인이 필요하다(design.md §2.4).
  4. `plan.md` §2.0-다·design.md §3 — destination occupancy 는 `context.py`(형제
     소유, PRESERVE)가 아니라 LDRECV 자신의 execution journal(M4,
     `002_execution_journal.sql`)에 독립 테이블로 추적한다(옵션 B 채택).

### plan-audit 보완 기록 (2026-09-16, D1-D7)

독립 plan-audit(FAIL, Overall ≈0.75, Tier L 기준 0.85 미달 — Category: Clarity 1.0 /
Completeness 0.60 / Testability 0.70 / Traceability 1.0)의 지적사항 D1-D7 을 아래와
같이 처리했다. Must-Pass 는 MP-1(완화 맥락 있음) FAIL, MP-2/3/5/7 PASS, MP-4/6 N/A 였다.

| 항목 | 등급 | 처리 | 반영 위치 |
|---|---|---|---|
| D1 | critical | REQ id 는 바꾸지 않았다(요구사항대로). 대신 "우산 ID 승계는 의도된 정책"이라는 명시적 문단을 추가하고, 두 형제 SPEC 의 실제 REQ id 승계 패턴(LDSTORE 4건 비연속, LDCOMPILE 7건 연속이나 우산 원본이 연속이었을 뿐)을 실측해 근거로 남겼다 | `spec.md` §1.2 |
| D2 | minor | `## HISTORY` 섹션(생성일 항목 1개) 추가 | `spec.md` (제목 바로 아래) |
| D3 | major, blocking | `design.md` 신규 작성 — §1 에서 SafetyGate 이중화 문제·ANCHOR 제약 해석·대안 A/B/C 비교·C 채택 근거·characterization 검증 방법을 다뤘다. §2 에서 `tools.py` 9개 grep 매치 중 실제 호출 1곳(2366·2368행)을 확정하고, 추가로 `session.py`(4691행)·`measurement/runner.py`(167행)에도 동일 패턴이 있음을 실측해 "호출부 wrapping은 PRESERVE 위반"이라는 결론을 도출, "lock 을 gate.py 내부에 둔다"로 확정했다 | `design.md` §1·§2, `plan.md` §2.0-가·나·§3.1·§4 M3 갱신 |
| D4 | major, blocking | `plan.md` §5 의 pytest 파일 목록을 `acceptance.md` §3 의 9파일 세분화 기준으로 맞췄다 — `test_director_execution.py`(구) 를 `test_director_execution_journal.py`/`test_director_execution_failure.py`로 대체하고, 누락됐던 `test_director_evidence_trust.py`(019)·`test_director_apply_rejection.py`(021)·`test_director_ops_lifecycle.py`(032)를 추가했다 | `plan.md` §5 |
| D5 | major, blocking | `context.py`(434줄)·`models.py`(304줄)·`001_initial.sql`을 직접 읽어 destination/occupancy 관련 필드·테이블이 전혀 없음을 확인했다. `design.md` §3 에서 옵션 A(LDSTORE amendment)/B(LDRECV 독립 테이블)를 비교 — PRESERVE 경계·`001_initial.sql` 자신의 주석("execution journal 은 LDRECV 것")·계약 §6.1 의 snapshot 불변성 원칙 셋을 근거로 B 를 채택했다 | `design.md` §3, `plan.md` §2.0-다(신설)·M4/M5 마일스톤 표 |
| D6 | minor, 기계적 | `plan.md` §2.0-나의 "9개 gate.screen(...) 호출부"를 "9개 grep 매치 중 실제 호출은 2366·2368행의 if/else 분기 하나뿐(주석 인용 7건 제외, 실측 재확인)"으로 정정했다 | `plan.md` §2.0-나 (D3 처리와 함께) |
| D7 | minor, 선택 | Tier L 선택 근거를 "REQ/파일 수 기준으로는 Tier M 범위이나 안전 위험 때문에 의도적으로 Tier L 을 선택했다"는 문장으로 명확화했다(기존 서술과 중복 없이 대비 구조로 다듬음) | `progress.md` §E.1 (이 섹션) |

**design.md 요약**: 신규 작성. 세 seam 결정 — (1) SafetyGate `execute_preapproved`:
대안 A(flag 인자, 안전 스위치가 모델 조작 표면화될 위험)·B(완전 별도 실행기, 심사
파이프라인 복제 위험)를 기각하고 C(새 public 메서드, private 스테이지 공유)를 채택.
(2) `tools.py` 접점: 실제 호출 1곳 확정 + `session.py`/`measurement/runner.py` 의
동일 패턴 추가 발견으로 "호출부마다 wrapping"이 PRESERVE 를 깬다는 것을 실측, "lock 을
gate.py 내부에 둔다"로 확정 — `tools.py` 는 수정하지 않는다. (3) destination
occupancy: `context.py` PRESERVE 경계·`001_initial.sql` 주석·계약 §6.1 불변성 원칙
셋을 근거로 LDRECV 자신의 execution journal(M4)에 독립 테이블로 추적하기로 결정.

### plan-audit 최종 처분 (2026-09-17, iteration 2 — PASS-with-debt 사람 승인)

독립 plan-audit 2차 반복(iteration 2, 2026-09-17)은 카테고리 점수 **0.95**(Tier L
기준 0.85 상회)를 기록했으나, Must-Pass 기준 **MP-1**(REQ id 비연속)이 여전히 FAIL
로 남아 verdict 자체는 FAIL 로 판정됐다. 나머지 Must-Pass(MP-2/3/5/7)는 PASS,
MP-4/6 은 N/A 로 1차(iteration 1, FAIL, Overall ≈0.75)와 동일했다.

**경과**:
1. iteration 1 (2026-09-16): FAIL, Overall ≈0.75(Clarity 1.0 / Completeness 0.60 /
   Testability 0.70 / Traceability 1.0). D1-D7 지적사항 접수 — MP-1 은 "완화 맥락
   있음" FAIL 로 판정됐다(§ plan-audit 보완 기록 참고).
2. 보완: D1-D7 전항목 처리 완료 — design.md 신규 작성(D3/D5 seam 결정 3건),
   HISTORY 섹션 추가(D2), plan.md 시험 파일 목록을 acceptance.md 9파일 기준에 정합
   (D4), 9개 grep 매치 중 실제 호출 재확인(D6), Tier L 선택 근거 명확화(D7). REQ
   id 자체는 D1 처리에서 이미 "바꾸지 않는다"로 확정했고, 대신 우산 ID 승계가
   의도된 정책이라는 문단을 `spec.md` §1.2 에 추가했다.
3. iteration 2 (2026-09-17): 카테고리 점수 0.95 로 상승 — Clarity/Completeness/
   Testability/Traceability 전 항목 개선이 확인됐다. 그러나 MP-1(REQ-LDPLUGIN-018
   ~024 다음 032, 이 SPEC 안에서 비연속)은 REQ id 를 바꾸지 않는 한 원리적으로
   해소되지 않는다 — 개선 가능한 결함이 아니라 정책이 만드는 구조적 한계다.

**MP-1 이 구조적으로 해소 불가능한 근거** (`spec.md` §1.2 실측 재확인):
- 우산 `SPEC-LDPLUGIN-001/spec.md:45` 가 "구현 파일 이동과 무관하게 ID 를 유지하며
  AC 번호와 1:1 대응한다"고 명시적으로 규정하며, 유지 대상은 우산 문서에서 부여된
  **원래 번호**이지 자식 SPEC 내부에서 재배번한 연속 번호가 아니다.
- 이미 완료된 두 형제가 동일 패턴을 썼다: `SPEC-LDSTORE-001`(completed) 은
  `REQ-LDPLUGIN-004/007/015/027`(4건, 우산 순서 그대로 비연속)을,
  `SPEC-LDCOMPILE-001`(completed) 은 `REQ-LDPLUGIN-008~014`(7건, 자식 안에서는
  연속이지만 우산에서 그 구간이 원래 연속이었기 때문이지 자식이 재배번했기 때문이
  아니다)를 그대로 승계했다(각 SPEC `spec.md` §3 실측).
- 이 SPEC 의 8건(018-024, 032)이 비연속인 것은 우산 분할 시점에 032 가 다른
  구간(운영 중단)에 배정됐기 때문이며, 상속하며 재배번하면 `contract.md` 의 조항
  참조와 두 형제 SPEC 의 승계 관례가 동시에 끊긴다.
- 즉 REQ id 를 이 SPEC 안에서 연속시키는 유일한 방법은 우산 ID 승계 정책 자체를
  어기는 것이며, 이는 MP-1 을 해소하는 대신 더 심각한 결함(계약 조항 참조 단절,
  형제 SPEC 관례 이탈)을 만든다.

**사람 결정 (2026-09-17)**: 사람이 위 진단을 검토하고 다음과 같이 명시적으로
지시했다 — *"MP-1(요구사항 번호 비연속)을 정책 예외로 인정하고 PASS-with-debt로
기록한 뒤, 구현 착수를 승인한다."* 처분: **PASS-with-debt** — MP-1 FAIL 은 정책
예외로 접수하고 기록에 남기되(해소하지 않고 명시적 부채로 표기), verdict 실질을
PASS 로 취급해 Implementation Kickoff Approval 을 부여한다.

**선례 적용**: 이 판단은 아직 작성되지 않은 형제 SPEC(`SPEC-LDHOST-001`,
`SPEC-LDUI-001`, `SPEC-LDCUTOVER-001`, `SPEC-LDCERT-001`)에도 선례로 적용된다 —
우산 ID 승계 정책(`SPEC-LDPLUGIN-001/spec.md:45`)을 따르는 한, 자식 SPEC 내부의
REQ id 비연속은 동일하게 "정책 예외 / PASS-with-debt"로 처리한다. 이후
plan-audit 가 같은 패턴의 MP-1 을 다시 FAIL 로 표시하더라도, 이 선례를 인용해
재논의 없이 동일하게 처분할 수 있다.

**Implementation Kickoff Approval: 부여됨 (2026-09-17, 사람 승인, PASS-with-debt).**
run-phase 착수가 승인되었다. 위 "사람 확인 대기 항목" 4건 중 design.md/research.md
판단(#1)과 세 seam 결정(#2-#4)은 이 승인과 별개로 여전히 명시적으로 열려 있다 —
이번 사람 지시는 MP-1/PASS-with-debt/착수 승인에 한정되며, 그 항목들을 묵시적으로
확정한 것이 아니다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
