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

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
