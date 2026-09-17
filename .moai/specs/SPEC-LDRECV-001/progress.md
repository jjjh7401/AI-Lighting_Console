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

### M1 완료 (REQ-LDPLUGIN-018 · REQ-LDPLUGIN-019)

작업 트리 기준 HEAD `d6122990` · 커밋 전.

**환경 메모(투명성)**: M1 착수 직전, 이 세션이 격리된 워크트리가 배차서가 전제한
`.claude/worktrees/ldrecv-m1` 이 아니라 다른(오래된, SPEC 문서 병합 이전) 워크트리임을
발견해 Missing Inputs 로 1차 보고했다. 오케스트레이터가 "하네스가 정상적으로 재격리한
것"이라 확인해 주었고, 실제로 환경이 `ldrecv-m1`(브랜치 `worktree-ldrecv-m1`, HEAD
`d6122990`)으로 재조정된 것을 실측 확인한 뒤 구현을 진행했다. 아래 전 과정은 이
재조정 이후, 실제 `ldrecv-m1` 워크트리 안에서 수행했다.

**Claim**: M1 의 두 요구사항을 TDD 로 구현했다 — 인증·ACL·Host/Origin 검증(018)과
evidence 신뢰 경계·audio 외부 전송 동의 게이트(019). `server/director/auth.py`(신규)가
두 REQ 를 모두 담당하고, `server/director/director_api.py`(신규)가 계약 §3 공통
route 의 HTTP 골격을 그 인증 뒤에 배선하며, `server/web/app.py`(EXTEND, router 등록
1곳)가 조건부(`deps.director is not None`) 마운트를 추가했다.

**Evidence — RED (구현 삭제 후 실제로 실패시킨 verbatim 출력)**

TDD 규율에 따라 `auth.py` 를 먼저 작성한 것을 인지한 뒤, 두 시험 파일이 실제로 RED
상태에서 시작했음을 증명하기 위해 `auth.py` 를 삭제하고 재확인했다:

```
$ rm server/director/auth.py
$ uv run pytest server/tests/test_director_auth.py server/tests/test_director_evidence_trust.py -q
ERROR collecting server/tests/test_director_auth.py
ModuleNotFoundError: No module named 'server.director.auth'
ERROR collecting server/tests/test_director_evidence_trust.py
ModuleNotFoundError: No module named 'server.director.auth'
2 errors in 0.08s
```

이후 `auth.py` 를 복원해 GREEN 으로 이행했다(아래).

**Evidence — GREEN (신규 시험 31개, 첫 시도에 전부 통과)**

```
$ uv run pytest server/tests/test_director_auth.py server/tests/test_director_evidence_trust.py -q
...............................                                          [100%]
31 passed in 0.43s
```

| AC | 시험 파일 | PASS 조건 커버 | Status |
|---|---|---|---|
| AC-LDPLUGIN-018 | `test_director_auth.py` (23개) | human-only scope 7종 각각 SCOPE_DENIED(파라미터화) · 만료/철회/부재/위조 credential UNAUTHENTICATED · Origin 불일치·Host allowlist 밖 ORIGIN_DENIED · **양성 대조**(MCP 공통 scope 통과, human 전용 scope 통과, Origin 부재 stdio proxy 허용) · secret 비노출(로그·응답·예외 str/repr/ErrorEnvelope 전부 grep) | PASS |
| AC-LDPLUGIN-019 | `test_director_evidence_trust.py` (8개) | claim 만으로 미승격(negative) · 서버 record 역참조 시 승격(**양성 대조**) · project/principal/scope 불일치 시 미승격(3-way 파라미터화) · audio 전송 동의 없이 차단 · 목적/수신자/범위 결여 시 차단(3-way 파라미터화) · 완전한 기록 시 통과(**양성 대조**) | PASS |

**Baseline-attribution**: 기준선(착수 시 재측정, 같은 HEAD `d6122990`) `13376 passed, 35
skipped` (배차서 지시값과 일치). 신규 테스트 **31개**(2파일). 13376 + 31 = **13407** —
아래 최종 회귀와 정확히 일치, skipped 불변(35), 실패 0.

**Evidence — 최종 회귀 (전체, async-def 수정 반영 후 재실행)**

```
$ uv run pytest -q
13407 passed, 35 skipped, 1 warning in 182.18s (0:03:02)
```
verbatim 저장: `.moai/state/verify/ldrecv-m1/m1-full-regress.txt`

**Evidence — ruff**

```
$ uv run ruff check server/director/ server/tests/test_director_auth.py server/tests/test_director_evidence_trust.py server/web/app.py
All checks passed!
$ uv run ruff format --check server/director/auth.py server/director/director_api.py server/tests/test_director_auth.py server/tests/test_director_evidence_trust.py server/web/app.py
5 files already formatted
```
(2개 findings — `SIM105`try/except/pass → `contextlib.suppress`, `SIM300` Yoda 조건 — 를
GREEN 뒤 수정해 반영했다. `ruff format` 이 최초 3개 파일을 자동 재포맷했다 — 순수 공백
정리, 재실행으로 초록 확인.)

**Evidence — 경계 grep (전부 실측, 날조 대조군 없음)**

```
$ grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/   → 0 매치 (exit 1)
$ grep -rnE "^\s*(from|import)\s+server\.(looks|web\.session)" server/director/  → 0 매치 (exit 1)
$ grep -rn "approval_bridge\|DenyAllApprovalPort\|request_approval(" server/director/
  → 1 매치: auth.py:15, docstring 산문(`server/web/approval_bridge.py` 를 "이것과
    다른 채널"이라 설명하는 문장) — import/호출 아님. `^import\|^from` grep 으로
    재확인: `server.web` import 없음(auth.py/director_api.py 모두).
$ grep -rn "def " server/director/ | wc -l  → 194 (양성 대조 — grep 자체가 헛돌지 않음을 확인)
```

**Evidence — secret 비노출 (in-test + 외부 재확인 둘 다)**

1. `test_director_auth.py::test_secret_never_exposed_in_errors_body_or_logs` — 위조
   secret 시도·scope 거부·성공 경로 세 시나리오 각각의 예외 `str()`/`repr()`/
   `ErrorEnvelope` dict, 성공 `Credential` 의 `str()`/`repr()`, `caplog.text` 전부를
   캡처해 실제 secret 문자열이 없는지 단언 — PASS(위 31개 중 하나).
2. **외부 재확인**(모듈 경계 밖에서 별도 스크립트로) — canary secret 을 생성해 위조
   시도/scope 거부/성공 세 시나리오를 실행하고 `DEBUG` 레벨 로깅까지 캡처한 뒤,
   canary 를 **의도적으로 출력한 한 줄만 제외**하고 나머지 출력에서 canary 를 grep:
   ```
   canary length: 43
   matches outside marker line: 0
   ```
   **부수 발견 및 정리**: 이 재확인 스크립트는 pytest 의 autouse in-memory keyring
   fixture 밖에서 실행되어 실제 macOS Keychain 에 `com.grandma3copilot.director`
   서비스로 항목을 하나 남겼다 — `security delete-generic-password` 로 즉시 삭제하고
   `security find-generic-password` 재조회로 부재를 확인했다(exit 44). 스크래치
   스크립트 자체는 `.moai/specs` 밖의 워크트리 루트에 임시로 썼다가 사용 후 삭제해
   `git status --short` 를 clean 상태로 유지했다.

**부수 발견 — SQLite 스레드 친화성 위험 (RED 시험 범위 밖, 스스로 찾아 고침)**

M1 시험 파일 두 개는 `director_api.py` 의 HTTP 배선 자체를 시험하지 않는다(배차서
절차가 명시한 RED 대상은 `test_director_auth.py`·`test_director_evidence_trust.py`
두 개뿐이었다). 그럼에도 "LDSTORE service 를 실제로 호출하는가"를 비공식으로
검증하려고 FastAPI `TestClient` 로 router 를 직접 왕복시키자 실제 결함이 나왔다:

```
sqlite3.ProgrammingError: SQLite objects created in a thread can only be used
in that same thread. The object was created in thread id 8496078208 and this
is thread id 6163034112.
```

`server/director/store.py`(PRESERVE, 수정 금지)의 `DirectorStore` 는
`sqlite3.connect()` 를 생성 스레드에 고정한다. 내가 처음 `def`(동기) handler 로
짠 route 는 FastAPI 가 매 요청을 threadpool 의 임의 스레드로 보내(`run_in_threadpool`)
이 제약을 깼다. **고침**: 7개 handler 전부를 `async def` 로 바꿨다 — event loop
스레드에서 직접 실행되므로, `deps`(따라서 `DirectorStore`)를 그 스레드에서 구성하면
(앱 startup/lifespan) 문제가 사라진다. `httpx.ASGITransport` + `AsyncClient`(스레드
포털 없이 단일 이벤트 루프에서 실행)로 재확인 — 인증 실패(401)·PUT plan 저장(200,
`DirectorStore.submit` 실제 호출)·GET plan 조회(200, 저장한 값 그대로 왕복)·
IDENTITY_MISMATCH(422)·미배선 context provider(503 DEPENDENCY_UNAVAILABLE)·
POST validations(200, `NotInstalledValidator` stub) 전부 통과, cross-thread 오류
재발 없음. 이 수정은 이번 M1 delegation 범위 안에서(같은 파일, `def`→`async def`
전환만) 처리했고, `store.py` 는 손대지 않았다(PRESERVE 준수).

**만든 파일**

```
server/director/auth.py           인증·ACL·CSRF/Origin 검증 + evidence 신뢰 경계 (413줄)
server/director/director_api.py   계약 §3 공통 route HTTP 골격, async def (289줄)
server/tests/test_director_auth.py            REQ-018 시험 23개
server/tests/test_director_evidence_trust.py  REQ-019 시험 8개
```

EXTEND: `server/web/app.py` — `WebDeps.director: DirectorApiDeps | None = None` 필드
추가 + `if deps.director is not None: app.include_router(...)` 조건부 등록 1곳(기존
`settings`/`provision`/`presets` 관례와 동일 패턴). 다른 곳은 건드리지 않았다.

**Gaps — M1 에서 하지 않은 것**

- **`test_director_api_routes.py` 를 시험 스위트에 커밋하지 않았다.** `director_api.py`
  의 HTTP 배선은 위 "부수 발견" 절의 **비공식** 스크래치 스크립트(사용 후 삭제)로만
  왕복 확인했다 — TDD "test-first" 규율상 커밋된 `.py` 구현은 커밋된 실패 시험이
  선행해야 하므로, 이 router 골격은 배차서가 지정한 RED 두 파일의 보호를 받지
  않는다는 것을 정직하게 남긴다. plan.md §4 M1 TDD 순서의 예시(대표 마일스톤 예시)는
  이 파일도 언급하지만, 이번 배차서의 §"절차" 는 명시적으로 두 파일만 지정했다 —
  둘 사이 불일치를 여기 기록한다. 후속(다음 배차 또는 이번 세션 연장)에서
  `test_director_api_routes.py` 를 커밋 시험으로 만드는 것을 권고한다.
- **GET context/knowledge, GET execution, POST feedback-proposals 는 실제 배선이
  없다.** `context_provider`/`execution_provider`/`feedback_service` seam(Protocol)만
  있고 구현은 이 SPEC 의 뒤 마일스톤(M2 feedback 저장소, M4 execution journal) 또는
  범위 밖(콘솔 관측 배선)이다 — 미주입이면 계약 §5 `503 DEPENDENCY_UNAVAILABLE` 을
  정직하게 답한다.
- **CSRF token 검사 미구현.** 계약 §5 는 "cookie 사용 APP route 도 CSRF token 도
  요구한다"고 규정하나, 이 코드베이스 전체에 쿠키 기반 세션 패턴이 없음을
  실측했다(`grep -rn "set_cookie\|request.cookies" server/` 무매치, 이 파일의 docstring
  인용 제외). Bearer 인증만 쓰는 현재 경로에는 조건부로 적용되지 않는다 — 쿠키 세션이
  추가되면 `authenticate()` 에 CSRF 검사를 보강해야 한다.
- **CredentialRegistry/PairingSecretStore 는 인메모리·keyring 뿐, MCP pairing
  발급/철회 흐름(사람이 앱에서 최초 pairing 을 승인하는 UI 경로)은 이 SPEC 의
  범위 밖이다(계약 §5: "최초 pairing은 앱에서 사용자가 승인한다") — M1 은 인증
  판정 로직만 제공하고, 실제 pairing UX 배선은 다루지 않는다.

**Residual-risk**

- acceptance.md §3 AC-018 본문이 human-only scope 를 "6종"이라 세지만 실제 나열된
  토큰은 7개(spec.md·contract.md 도 동일 7개) — 문서 불일치를 실측했고, 더 넓은
  실측 집합(7개)을 시험이 전부 돈다. 이 문서 불일치 자체는 spec.md 소유이므로 이
  run-phase 에이전트가 고치지 않았다(SPEC 본문 수정 금지 경계) — sync-phase 나
  독립 plan-audit 재검토 시 참고할 사항으로 남긴다.
- `authenticate()` 의 Host/Origin 판정 순서(Host → Origin → credential → scope)는
  내가 설계한 순서다 — AC-018 원문이 세 결과(SCOPE_DENIED/UNAUTHENTICATED/
  ORIGIN_DENIED)를 매핑하는 것은 확인했지만, 세 검사의 **상대 순서**까지 계약이
  강제하지는 않는다. 다른 순서를 선호하는 감사 의견이 있으면 조정 여지가 있다.
- M3(공유 programmer 중재자)가 아직 없으므로, 이 M1 router 골격 자체는 동시 요청
  직렬화를 하지 않는다 — SQLite 스레드 친화성 수정(async def)은 "같은 스레드"
  문제만 풀었을 뿐 "동시 쓰기 경쟁"(CAS 가 있으므로 안전하긴 하다, `store.py` 의
  `REVISION_CONFLICT` 재시도 없는 실패로 처리됨)까지 다루지 않는다 — 이는 원래
  M3 의 몫이다.

### M2 완료 (REQ-LDPLUGIN-020)

작업 트리 기준 M1 완료 커밋 `e297b03a` 위에서 진행 — 커밋 전 HEAD `abc3e92d`
(이 에이전트 워크트리가 `e297b03a` 를 `--no-ff` merge 한 결과. 배차서가 전제한
HEAD 상태와 다른 워크트리에서 시작했음을 착수 직전 실측 확인했고, `e297b03a` 를
찾아 병합한 뒤 진행했다 — 추측 없이 재조정했다).

**Claim**: M2 의 REQ-LDPLUGIN-020(사람 승인/거절)을 TDD 로 구현했다 —
`server/director/approvals.py`(신규)가 `ApprovalBinding`(계약 §4 나열 12필드)
발급·만료 계산(approved_at+10분과 validation/context 만료 중 빠른 값)·무효화
판정(`check_validity`)·거절 오버레이를 담당하고, `server/director/director_api.py`
(EXTEND)가 `POST .../approvals`·`POST .../rejections` route 2개를 M1 의 인증
뒤에 배선한다.

**Evidence — RED (구현 삭제 전 실제로 실패시킨 verbatim 출력)**

```
$ uv run pytest server/tests/test_director_approvals.py -q
ImportError while importing test module '.../server/tests/test_director_approvals.py'.
server/tests/test_director_approvals.py:26: in <module>
    from server.director.approvals import (
E   ModuleNotFoundError: No module named 'server.director.approvals'
1 error during collection
```
(`approvals.py` 는 이 RED 확인 **후에** 작성했다 — test-first 준수.)

**Evidence — GREEN (신규 시험 21개, 서비스 층 17 + route 층 4)**

```
$ uv run pytest server/tests/test_director_approvals.py -q
.....................                                                    [100%]
21 passed, 1 warning in 0.66s
```

| AC | 시험 커버 | Status |
|---|---|---|
| AC-LDPLUGIN-020 | `ApprovalBinding` 12필드 전부 채워짐(계약 §4 원문 나열 승계 — plan.md/acceptance.md 의 "9필드" 표기는 auth.py `HUMAN_ONLY_SCOPES` "6종" vs 실제 7개 나열과 같은 문서 불일치, 이 시험은 나열된 쪽을 고정) · 만료 = approved_at+10분과 validation/context 만료 중 빠른 값(3-way 파라미터화) · plan head 변경·context stale(compiler/target/policy 를 context_digest 하나가 덮음, context.py NINE_AXES 근거)·만료 각각 무효화(`check_validity`, 개별+복합 케이스) · validation.outcome≠ready_for_review 시 VALIDATION_BLOCKED(422) · body/record/context/validation digest 어긋남 시 CONTEXT_STALE(409) · revision 이 head 아니면 REVISION_CONFLICT(409, superseded) · idempotent replay + 다른 요청 시 IDEMPOTENCY_CONFLICT(409) · `plan_revisions` 행 불변 확인(before==after) · reject() 빈 reason 거부·store 미변경·거절 오버레이 반환 · **route 층**: MCP credential(`plan:approve` 없음) → SCOPE_DENIED(403, `auth.authenticate` 가 approvals.py 도달 전에 차단) · 일반 WS boolean(`{"approved": true}`) → SCHEMA_INVALID(422, 구조적 거부) · human credential 정상 승인(201, `ApprovalBinding` 12필드+`record.state=="approved"`) · human credential 정상 거절(200, `state=="rejected"`) | PASS |

**Baseline-attribution**: 기준선(이번 착수 시 재측정, 같은 HEAD `abc3e92d`)
`13407 passed, 35 skipped` — M1 §E.2 가 기록한 값과 정확히 일치(이 SPEC 은 M1
이후 다른 커밋이 없었으므로 재측정값이 같다). 신규 테스트 **21개**(1파일). 13407
+ 21 = **13428** — 아래 최종 회귀와 정확히 일치, skipped 불변(35), 실패 0.

**Evidence — 최종 회귀 (전체)**

```
$ uv run pytest -q
13428 passed, 35 skipped, 1 warning in 185.18s (0:03:05)
```
verbatim 저장: `.moai/state/verify/ldrecv-m2/m2-full-regress.txt`

**Evidence — ruff**

```
$ uv run ruff check server/director/ server/tests/test_director_approvals.py
All checks passed!
$ uv run ruff format --check server/director/ server/tests/test_director_approvals.py
26 files already formatted
```
(GREEN 뒤 정리: import 정렬 자동수정 1건 + 함수 시그니처 줄바꿈 6건(E501) +
`approvals.py` 자체 포맷 1건 — 전부 수정 후 재확인 초록.)

**Evidence — 경계 grep**

```
$ grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/       → 0 매치
$ grep -rnE "^\s*(from|import)\s+server\.(looks|web\.session)" server/director/  → 0 매치
$ grep -rn "approval_bridge\|DenyAllApprovalPort\|request_approval(" server/director/
  → 2 매치: auth.py:15(M1 기존, docstring 산문) · approvals.py:9(이번 신규,
    같은 성격의 docstring 산문 — "이 채널과는 다르다"는 설명이지 import/호출이
    아니다). `git status --short` 로 실제 변경 파일 확인: approvals.py(신규)·
    director_api.py(EXTEND)·test_director_approvals.py(신규) 세 개뿐, gate.py·
    tools.py·session.py·approval.py·approval_bridge.py 미접촉.
$ git diff --name-only origin/main -- server/director/models.py server/director/store.py \
    server/director/service.py server/director/context.py server/director/knowledge.py \
    server/director/digest.py server/director/emit.py server/director/validate
  → 0 매치 — PRESERVE(형제 SPEC 소유) 위반 없음.
```

**설계 판단 — console_id/session_id 출처** (배차서가 명시적으로 요구한 판단)

`Credential`(auth.py)에는 `console_id` 필드가 없다 — credential 의 `session_id`
는 사람/plugin 세션이지 콘솔 세션이 아니다. 계약 §6.1 이 ContextSnapshot 의
identity 축으로 `target={console_id,session_id,identity_status,
identity_evidence_refs,mode,destination}` 를 명시적으로 규정하므로, LDSTORE 의
`ContextObservations.target`(context.py, PRESERVE·읽기 전용)에서 값을 가져오는
쪽을 채택했다 — `ContextRef.from_snapshot()` 이 `snapshot["target"]["console_id"]`
/`["session_id"]` 를 꺼낸다(`context.py` 자체는 `target` 을 구조화 없는
`Mapping[str, Any]` 로 취급하므로 이 층이 처음 구조를 부여한다). credential 로부터
passthrough 하는 대안은 기각했다 — 계약이 `console_id`/`session_id` 를 target(콘솔
identity) 축의 값으로 규정했지, credential(사람 인증) 축의 값으로 규정하지 않았다.

**만든 파일**

```
server/director/approvals.py           ApprovalBinding·만료·무효화·승인/거절 오버레이 (신규)
server/tests/test_director_approvals.py REQ-020 시험 21개 (신규)
```

EXTEND: `server/director/director_api.py` — `POST .../approvals`·
`POST .../rejections` route 2개 + `DirectorApiDeps.approvals`/`validation_provider`
필드 추가. 계약 §4 의 route 형태를 그대로 따랐다(plan.md 가 이 EXTEND 를 M2 의
정당한 범위로 명시).

**Gaps — M2 에서 하지 않은 것**

- **`ValidationProvider` 의 실제 구현이 없다.** `SPEC-LDCOMPILE-001` 이 만든
  validation 산출물을 durable 하게 저장·HTTP 로 노출하는 저장소가 이 코드베이스에
  아직 없다(M1 의 `ContextProvider`/`ExecutionProvider` 와 같은 이유 — 미주입이면
  503). route 층 시험은 stub(`_StubValidationProvider`/`_StubContextProvider`)으로
  왕복만 확인했다.
- **ApprovalRegistry 는 in-memory 다.** durable 저장(SQLite, 승인 소비 추적)은
  계획 §2 M4 행이 만든다 — REQ-020 자체가 console 게이트가 아니므로(spec.md §5)
  이 범위는 의도된 것이다(approvals.py 모듈 docstring에 명시).
- **재승인(같은 revision 에 대한 두 번째 approve 호출, 다른 idempotency_key)의
  상태-기계 제약을 추가로 걸지 않았다.** 계약 §10 은 만료된 승인이 있는 revision
  은 재승인이 아니라 새 revision 제출을 요구한다고 규정하지만, 이 세부는 M5(apply
  직전 재검사)의 몫으로 남겼다 — M2 는 발급·무효화 판정만 책임진다.
- **`test_director_api_routes.py` 를 별도로 만들지 않았다** — M1 이 남긴 동일한
  gap(§E.2 M1 Gaps 참고)이며, 이번 M2 의 route 층 시험(4개)은 그 파일 대신 이번
  시험 파일(`test_director_approvals.py`) 안에 함께 두었다. `director_api.py` 의
  기존 M1 route(GET context/knowledge/plan 등)는 이번에도 여전히 HTTP 표면
  시험을 갖지 않는다 — 이 SPEC 의 후속 마일스톤(또는 별도 delegation)에서
  `test_director_api_routes.py` 로 채우는 것을 권고한다.

**Residual-risk**

- CONTEXT_STALE 의 세부 사유 셋(body 어긋남 / validation 만료 / context 만료)을
  하나의 코드(409 CONTEXT_STALE)로 묶었다 — 계약이 이 세 경우를 서로 다른 코드로
  구분하라고 명시하지 않았으므로 설계 판단이지만, 감사 의견에 따라 세분화될
  여지가 있다.
- `check_validity()` 의 "context_changed" 판정이 compiler/target/policy 변경을
  context_digest 하나로 뭉뚱그린다는 설계 판단(context.py NINE_AXES 근거)은
  design.md 의 destination occupancy 결정(§3, "context_digest 하나가 아홉 축을
  덮는다")과 같은 원리를 재사용한 것이지만, 이 SPEC 자신의 design.md 는 이
  재사용을 명시적으로 다루지 않는다 — sync-phase 나 감사 시 이 설계 판단을
  design.md 에 소급 기록할지 검토 권장.
- M3(공유 programmer 중재자)가 아직 없으므로, 두 요청이 동시에 같은 plan 을
  승인/거절하는 race 는 이 M2 코드 자체로는 막히지 않는다(idempotency 는 같은
  key 재제출만 방어) — 이는 원래 M3(§2.0-나·design.md §2)의 몫이다.

### M3 완료 (REQ-LDPLUGIN-021 §2.0-가 항목 3·4 · REQ-LDPLUGIN-022, 범위 확정: director/chat/import — panel 제외)

작업 트리 기준 M2 완료 커밋 `8af5d570` 위에서 진행. **1차 구현 뒤 전체 회귀에서
이 SPEC 문서 어디에도 없던 기존 요구사항(REQ-SHOWUI-013)과의 충돌을 발견해
Missing Inputs로 중단·보고했고(아래 "발견된 충돌" 절), 사람 확인
(2026-09-17, 옵션 1 채택) 후 스코프 가드를 구현해 재해소했다** — design.md
§2.5, plan.md M3 행 + §3.1, acceptance.md AC-022 를 모두 그 결정에 맞춰
갱신했다. 최종 회귀 실패 0 확인 후 커밋했다(아래 SHA).

**Claim**: `server/safety/gate.py`에 `execute_preapproved()`(신규 public
메서드) + `server/director/programmer_arbiter.py`(신규, `ProgrammerArbiter`)를
design.md §1.3 대안 C·§2.3 그대로 TDD 로 구현했다. `screen()`은 회귀 0으로
유지했고, `tools.py`/`session.py`/`measurement/runner.py` 세 파일은 전혀
건드리지 않았다(§2.3 전제대로 lock 이 `gate.py` 내부 공유 private 스테이지에
있어 자동으로 세 호출부를 직렬화한다). 그러나 **전체 회귀에서 이 SPEC 문서
어디에도 언급되지 않은 기존 요구사항(`REQ-SHOWUI-013`)과의 충돌을
발견했다** — 아래 "발견된 충돌" 참고.

**Evidence — RED (구현 삭제 후 실제로 재확인한 verbatim 출력)**

최초 작성 순서 오류를 스스로 발견했다 — `programmer_arbiter.py`를 그 단위
시험보다 먼저 써서 test-after 가 됐다. 파일을 삭제하고 RED 를 다시 확인한
뒤 재작성했다(test-first 준수 재확립).

```
$ uv run pytest server/tests/test_director_arbiter.py server/tests/test_director_gate_bridge.py -q
ERROR collecting server/tests/test_director_arbiter.py
ModuleNotFoundError: No module named 'server.director.programmer_arbiter'
1 error in 0.09s
```

**Evidence — GREEN (신규 시험 17개: arbiter 파일 9 + gate_bridge 파일 8)**

```
$ uv run pytest server/tests/test_director_arbiter.py server/tests/test_director_gate_bridge.py -q
.................                                                        [100%]
17 passed in 0.17s
```

| AC | 시험 커버 | Status |
|---|---|---|
| AC-LDPLUGIN-022 | `ProgrammerArbiter` 단위(즉시 거부·holder 이름·해제 후 재획득·역방향) · `SafetyGate` 배선(director `execute_preapproved()`가 잡은 lock에 chat `screen()` 요청이 `blocked_target_busy`로 거부 · 역방향(chat이 잡은 lock에 director 요청)도 동일) · lock 해제 후 재시도가 캐시가 아니라 파이프라인을 처음부터 재실행함(콘솔 미도달 확인 후 재시도 시 도달) — 신선도 판정 자체는 M5 몫, 이번엔 seam까지 | PASS |
| AC-LDPLUGIN-021 항목 3 | `execute_preapproved`가 안전한 명령은 승인 요청 0회로 클리어, 위험 명령도 승인 요청 0회로 클리어(감사엔 approved로 기록) · grammar 위반·console offline·live lock 활성 셋 다 `screen()`과 동일한 status 로 거부(대조 시험) · backup rule ③(위험 경로만 백업)이 `execute_preapproved`에서도 유지됨 | PASS |
| AC-LDPLUGIN-021 항목 4 | 기존 `screen()` characterization — 아래 "characterization" 참고 | PASS |

**Evidence — characterization (기존 gate 테스트 스위트 전체, 회귀 0)**

```
$ uv run pytest server/tests/test_bulkgate_declaration.py server/tests/test_bulkgate_songcue_seam.py \
    server/tests/test_deploy_gate_e2e.py server/tests/test_responder_import_gate.py \
    server/tests/test_safety_gate.py server/tests/test_showfile_replacement_gate.py \
    server/tests/test_worktree_gate_deps.py server/tests/test_writegate_declaration_wiring.py \
    server/tests/test_writegate_layout.py server/tests/test_writegate_merge_gap.py \
    server/tests/test_writegate_model_tool.py server/tests/test_writegate_session_sites.py \
    server/tests/test_writegate_song_finalize.py server/tests/test_writegate_tool_seams.py \
    server/tests/test_writegate.py -q
283 passed, 22 skipped in 4.10s
```
`screen()`의 관측 가능한 입출력 계약(결정·사유·감사 로그)은 바이트 동일 —
design.md §1.4 의 characterization 요구를 이 15개 파일 305개 시험 전체
실행으로 충족했다.

**Evidence — ruff**

```
$ uv run ruff check server/director/ server/safety/gate.py \
    server/tests/test_director_arbiter.py server/tests/test_director_gate_bridge.py
All checks passed!
$ uv run ruff format --check (동일 범위)
29 files already formatted
```
(중간에 재인덴트로 인한 E501 2건 + 미사용 import 1건을 발견해 고쳤다 —
`_check_lock` 직후부터 `try/finally`로 감싸며 4칸 들여쓰기가 늘어 100자를
넘긴 줄 2개.)

**Evidence — 경계 3개 금지 파일 미접촉**

```
$ git diff --name-only 8af5d570..HEAD -- server/orchestrator/tools.py \
    server/web/session.py server/measurement/runner.py
(빈 출력 — 세 파일 전혀 수정 안 됨, 확인됨)
```

**Evidence — @MX:ANCHOR 갱신 (fan_in >= 3 cap 준수)**

`gate.py`는 이미 `anchor_per_file: 3` 상한에 있었다(기존 `screen()` +
introspect 2개). `execute_preapproved()`에 두 번째 ANCHOR 를 추가하면 4개가
되어 한도 초과 — design.md §1.3 자체가 "두 진입점이 같은 파이프라인을
공유한다"는 사실 하나로 갱신하라고 했으므로, `screen()`의 기존 ANCHOR/REASON
만 갱신(두 entry point 언급)하고 `execute_preapproved()`에는 `@MX:NOTE`로
격하해 그 ANCHOR 를 참조하게 했다(design.md 의도를 정확히 지키면서 hard
limit 도 지키는 선택).

```
$ grep -nE "^\s*#\s*@MX:ANCHOR:" server/safety/gate.py
362:    # @MX:ANCHOR: [AUTO] the shared screening pipeline — run_commands (via the
964:        # @MX:ANCHOR: [AUTO] introspect audit subject is path-only.
981:        # @MX:ANCHOR: [AUTO] props audit subject is path plus requested names only.
```
(3개, 한도 내 — 갱신된 REASON 은 두 entry point 를 모두 언급한다)

**만든 파일**

```
server/director/programmer_arbiter.py       ProgrammerArbiter · TargetBusyError (신규)
server/tests/test_director_arbiter.py       REQ-022 시험 (신규)
server/tests/test_director_gate_bridge.py   REQ-021 §2.0-가 대조 시험 (신규)
```

EXTEND: `server/safety/gate.py` — `execute_preapproved()`(신규 public
메서드) + `_acquire_arbiter()`(신규 private 스테이지, `_check_lock` 직후) +
`__init__`에 `arbiter` 파라미터 추가 + `screen()`에 arbiter 획득/해제
`try/finally` 삽입(관측 가능한 입출력은 불변, 내부 구현만 확장 —
design.md §2.0-나 정정 그대로).

**Baseline-attribution**: 기준선(M2 §E.2 가 기록한 최종값, 같은 HEAD `8af5d570`)
`13428 passed, 35 skipped`. 신규 테스트 **17개**(2파일). 13428 + 17 = **13445**
— 전체 회귀 시도 수(passed+failed 합)와 정확히 일치. skipped 불변(35). **실패
2건** — 아래 "발견된 충돌" 참고, 회귀 0 이 아니므로 no-go.

**Evidence — 최종 회귀 (전체, 실패 2건 포함)**

```
$ uv run pytest -q
2 failed, 13443 passed, 35 skipped, 1 warning in 181.34s (0:03:01)
```
verbatim 저장: `.moai/state/verify/ldrecv-m3/m3-full-regress.txt`

---

**발견된 충돌 — REQ-LDPLUGIN-022 vs REQ-SHOWUI-013 (BLOCKER, 사람 판단 필요)**

전체 회귀(`uv run pytest -q`)에서 이 SPEC 문서(spec.md·plan.md·design.md·
acceptance.md) 어디에도 언급되지 않은 기존 시험 2개가 실패했다:

```
$ uv run pytest server/tests/test_web_panel_execute.py::TestSerialization -q
FAILED test_a_stop_is_exempt_from_the_busy_guard
  assert 'Off Executor 5' in ['Go+ Executor 191']  (Off Executor 5 가 콘솔에 안 닿음)
FAILED test_the_chat_turn_lock_is_not_shared_with_the_panel
  assert 'Go+ Executor 191' in ['Store Group 3']  (Go+ Executor 191 이 콘솔에 안 닿음)
2 failed, 3 passed in 2.10s
```

`test_the_chat_turn_lock_is_not_shared_with_the_panel`의 원문 주석:
*"REQ-SHOWUI-013: a chat turn in flight must not busy-out the panel."*
— 이 기존 요구사항은 **chat 이 진행 중이어도 panel(대시보드 실행기 버튼)은
busy 로 막히지 않고 진짜로 콘솔에 도달해야 한다**는 것이다. 즉 chat 과
panel 의 `screen()` 호출은 **의도적으로 동시에(직렬화 없이) 통과**하도록
이미 설계·시험돼 있다(같은 파일의 `test_a_panel_screen_does_not_invalidate_
a_chat_bundles_clearance` 등 다른 테스트도 이 동시성 전제를 공유).

REQ-LDPLUGIN-022 원문: *"director/chat/import 등 모든 shared programmer
mutation을 하나의 중재자로 직렬화"*. 이 SPEC 의 design.md/plan.md/
acceptance.md 는 director·chat·import 세 갈래만 언급하고, **panel(대시보드
실행기 조작)을 한 번도 명시적으로 다루지 않았다** — grep 결과 이 SPEC
문서 5개(spec/plan/design/acceptance/progress) 어디에도 "panel"·
"REQ-SHOWUI" 문자열이 없다.

이 SPEC 이 채택한 대로 arbiter 를 `gate.py`의 공유 private 스테이지에
두면(design.md §2.3 의 핵심 이점 — tools.py/session.py/runner.py 무수정),
`.screen(`을 부르는 **모든** 경로가 자동으로 같은 lock 을 거친다 — panel
경로(`server/web/session.py`의 panel 전용 코드, 위 세 "금지 파일" 목록엔
없는 부분)도 예외가 아니다. 그 결과 REQ-022 가 요구하는 "모든" 직렬화가
문자 그대로 실현되지만, 그로 인해 기존 REQ-SHOWUI-013 이 명시적으로
보장하던 "chat 과 panel 은 서로 busy 시키지 않는다"가 깨진다.

**멈춘 이유**: 이 둘 중 하나를 조용히 고치는 것(예: panel 경로만 arbiter
에서 제외)은 design.md/plan.md가 승인하지 않은 새로운 대안을 이 에이전트가
임의로 만드는 것과 같다 — 배차서 원문: "design.md의 사양과 다르게
판단해야 할 상황이 생기면 추측하지 말고 Missing Inputs로 멈추고 보고하라
— 이건 안전 게이트라 임의 판단이 특히 위험하다." 두 요구사항 다 안전
관련(하나는 승인 우회 방지, 하나는 조작 반응성 방지)이라 어느 쪽을
좁히는 결정도 사람이 내려야 한다.

**옵션 (사람 판단 필요, 추측하지 않음)**:
1. **panel 경로를 arbiter 범위에서 명시적으로 제외** — REQ-022 의 "모든
   shared mutation"을 "director/chat/import(패널 제외)"로 재해석. 근거:
   panel 은 사람이 지금 이 순간 누른 실행기 버튼이라 "낡은 승인" 개념이
   원천적으로 없다(REQ-022 의 동기, "오래 대기시켜 낡은 승인을
   실행하지 않는다"). 위험: REQ-022 원문의 "모든"을 좁히는 재해석이며,
   panel 을 통한 shared programmer mutation 도 여전히 director apply 와
   경합할 수 있다(이 경우는 그냥 통과시킨다는 뜻).
2. **REQ-SHOWUI-013 을 이 SPEC 의 M3 로 인해 재조정** — "chat 과 panel 은
   서로 busy 시키지 않는다"를 "chat/panel 과 director apply 는 경합할 수
   있다"로 완화. 근거: REQ-022 가 이 SPEC 의 새 요구사항이므로 우선한다.
   위험: 기존 UI 반응성 계약을 깨는 결정이며 SPEC-LDRECV-001 범위 밖의
   SPEC(SHOWUI)을 건드리는 것 — plan.md PRESERVE 표가 "예술 producer 둘"
   외의 UI 계약을 명시하지 않아 이 SPEC 의 권한 범위가 불명확하다.
3. **panel 도 arbiter 를 타되, "충돌 시에만" busy** — 현재 구현은 이미
   "충돌 시에만 busy"다(진짜 동시 요청일 때만 TARGET_BUSY). 실패한 두
   테스트가 실패하는 이유는 테스트가 기대하는 것이 "충돌해도 busy 없이
   둘 다 통과"이기 때문이다 — 이 옵션은 사실상 옵션 1 과 같은 결론(패널
   제외)으로 수렴한다.

**이번에 하지 않은 것**: 위 세 옵션 중 어느 것도 코드로 반영하지 않았다.
`execute_preapproved`/`_acquire_arbiter`/`ProgrammerArbiter` 구현은
design.md §1.3·§2.3 이 승인한 그대로이며, 범위를 좁히거나 넓히는 어떤
추가 판단도 넣지 않았다.

**중단 시점의 상태**(2026-09-17, 사람 확인 이전): 위 회귀 2건이 해소되지
않은 채 커밋하면 acceptance.md §4 "회귀 실패가 하나라도 있는 경우 →
no-go"를 어기게 되므로 코드는 작업 트리에만 두고 커밋하지 않았다.

---

### 해소 (2026-09-17, 사람 확인 — 옵션 1 채택: design.md §2.5)

**결정**: REQ-LDPLUGIN-022 의 범위를 "director/chat/import"로 좁히고
panel(REQ-SHOWUI-013)은 중재자 대상에서 제외한다. 근거는 design.md §2.5.2
에 기록(요약: panel 은 "낡아질 승인"이 없는 즉시성 조작이라 REQ-022 의
동기가 애초에 적용되지 않는다).

**구현한 가드**: `SafetyGate.screen()`에 키워드 전용 `arbitrate: bool =
True` 추가(기본값 유지로 기존 3개 호출부 무수정) + `server/web/panel.py`
`PanelRuntime.fire()` 단 1줄만 `arbitrate=False` 로 명시 호출.

**Evidence — RED (재확장 전 실제로 재확인한 verbatim 출력)**

```
$ uv run pytest server/tests/test_director_arbiter.py::TestScreenArbitrateScopeGuard -q
TypeError: SafetyGate.screen() got an unexpected keyword argument 'arbitrate'
3 failed, 1 passed in 0.49s
```
(4번째 테스트 `test_arbitrate_defaults_to_true` 는 새 키워드를 안 써서
이미 통과 — 정상, 기존 동작이 안 바뀌었다는 신호.)

**Evidence — GREEN (신규 시험 4개 추가, arbiter 파일 합계 9→13)**

```
$ uv run pytest server/tests/test_director_arbiter.py -q
.............                                                            [100%]
13 passed in 0.11s
```

**구현 중 발견·수정한 버그**: 최초 구현에서 `finally: self._arbiter.release()`
를 `arbitrate` 값과 무관하게 무조건 실행했다 — `arbitrate=False` 경로는
애초에 lock 을 획득하지 않으므로, 이 상태로는 **다른 호출자가 쥐고 있는
lock 을 엉뚱하게 풀어버릴 수 있었다**(Python `threading.Lock.release()`
는 소유권을 확인하지 않는다). `test_arbitrate_false_does_not_busy_a_
concurrent_arbitrated_caller` 를 쓰다가 이 위험을 발견해 `finally`
블록을 `if arbitrate: self._arbiter.release()`로 고쳤다(회귀 테스트로
고정됨) — 커밋 전에 잡힌 결함이라 프로덕션에 나간 적은 없다.

**Evidence — 부작용 수정: test harness `spy()` 시그니처 확장**

`server/tests/test_web_panel_execute.py::make_harness` 의 `spy()` 가
`arbitrate=`를 못 받아 panel 을 부르는 시험 27개가 `TypeError`로
실패했다(카드 t323 이 남긴 것과 같은 모양의 결함 — `risk=` 때도 같은
문제였다). `spy(commands, *, risk=None, arbitrate=True)`로 확장 —
실제 게이트 시그니처를 그대로 따라 받아 넘기는 방식(기존 `risk=` 처리와
동일 패턴).

```
$ uv run pytest server/tests/test_web_panel_execute.py -q   # 수정 전
27 failed, 49 passed in 237.44s

$ uv run pytest server/tests/test_web_panel_execute.py -q   # 수정 후
76 passed, 1 warning in 1.58s
```
(**주의**: 최초 "27 failed"는 오염된 대조군이었다 — 배경에서 같은 파일을
중복 실행 중이었고, 그 두 프로세스가 자원을 놓고 경합해 무관한 시험군
(`TestGotoGateRouting`·`TestApprovalRoundTrip`·`TestLiveLock` 등)까지
같이 무너졌다. 배경 프로세스를 끝낸 뒤 **단독**으로 다시 돌려 진짜
"27 failed"(전부 `arbitrate=` `TypeError`, panel 을 부르는 경로 전부)를
확인했다 — 오염된 1차 결과와 진짜 2차 결과를 둘 다 여기 남긴다.)

**Evidence — REQ-SHOWUI-013 회귀 두 건 재확인**

```
$ uv run pytest "server/tests/test_web_panel_execute.py::TestSerialization" -q
......                                                                   [100%]
6 passed in 0.03s
```
(`test_the_chat_turn_lock_is_not_shared_with_the_panel`·
`test_a_stop_is_exempt_from_the_busy_guard` 포함 6개 전부 PASS.)

**Evidence — 최종 전체 회귀 (실패 0)**

```
$ uv run pytest -q
13449 passed, 35 skipped, 1 warning in 182.86s (0:03:02)
```
**Baseline-attribution**: M2 §E.2 기록값 13428 + M3 신규 21(arbiter 파일
13 + gate_bridge 파일 8) = **13449** — 정확히 일치. skipped 불변(35),
실패 0. verbatim 저장:
`.moai/state/verify/ldrecv-m3/m3-final-full-regress.txt`.

**Evidence — ruff (전체 대상 파일)**

```
$ uv run ruff check server/director/ server/safety/gate.py server/web/panel.py \
    server/tests/test_director_arbiter.py server/tests/test_director_gate_bridge.py \
    server/tests/test_web_panel_execute.py
All checks passed!
$ uv run ruff format --check (동일 범위)
31 files already formatted
```

**Evidence — 경계 확인 (panel.py/session.py 실제 수정 여부 — 정직 보고)**

```
$ git diff --name-only 8af5d570..HEAD -- server/orchestrator/tools.py \
    server/web/session.py server/measurement/runner.py
(빈 출력 — 원래 3개 금지 파일은 여전히 완전 미접촉, 확인됨)
```

**`server/web/panel.py`는 수정했다** — 위 3개 금지 파일에 포함되지 않은
파일이며, M3 착수 후 새로 발견한 SHOWUI 소유 파일이다. diff:

```diff
-            decision = self._gate.screen([command])
+            # SPEC-LDRECV-001 M3 scope narrowing (design.md §2.5): ... (주석 6줄)
+            decision = self._gate.screen([command], arbitrate=False)
```
1줄(호출 인자)만 실질 변경, 나머지는 이유를 남기는 주석. `git diff --stat`:
`server/web/panel.py | 9 +-`.

**`server/tests/test_web_panel_execute.py`도 수정했다** — SHOWUI 소유
**테스트** 코드(프로덕션 아님). `spy()` 시그니처 확장(위 참고).
`git diff --stat`: `13 +-`.

**PASS/FAIL 최종 표**

| AC | 항목 | 검증 명령 | Status |
|---|---|---|---|
| AC-LDPLUGIN-022 | director↔chat 양방향 TARGET_BUSY, 즉시 거부, panel 제외 | `test_director_arbiter.py` (13) | PASS |
| AC-LDPLUGIN-022 | panel 이 REQ-SHOWUI-013 대로 busy 없이 통과 | `test_web_panel_execute.py::TestSerialization` (6) | PASS |
| AC-LDPLUGIN-021 항목 3 | `execute_preapproved` 승인 재질문 0회, screen()과 동일 거부 | `test_director_gate_bridge.py` (8) | PASS |
| AC-LDPLUGIN-021 항목 4 | 기존 `screen()` characterization | `test_safety_gate.py` 등 gate 스위트 15파일 305개 | PASS |
| 전체 회귀 | 실패 0 | `uv run pytest -q` | PASS (13449 passed, 35 skipped) |
| 경계 | 3개 금지 파일 미접촉 | `git diff --name-only` | PASS |
| MX 한도 | ANCHOR ≤3 | `grep -cE "^\s*#\s*@MX:ANCHOR:"` | PASS (3) |

**커밋**: 아래 M3 완료 커밋 SHA 참고(§E.2 이 절 상단 — commit 직후 이
placeholder 를 실제 SHA 로 백필한다). push 는 하지 않았다.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase — M3 blocked, see §E.2 M3 for the REQ-022/REQ-SHOWUI-013 conflict>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
