# 진행 기록 — SPEC-LDSEND-001

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-09-18
- plan_revision: 3 (iter1 plan-audit `.moai/reports/plan-audit/SPEC-LDSEND-001-review-1.md`,
  FAIL 0.75 — D1-D8 반영, version 0.1.0 → 0.2.0. iter2 plan-audit
  `.moai/reports/plan-audit/SPEC-LDSEND-001-review-2.md`, FAIL 0.63(STOP
  신호, D1-D8 전부 회귀 확인됨) — D9-D12 반영, version 0.2.0 → 0.3.0)
- tier: M
- artifact_count: 4 (spec.md + plan.md + acceptance.md + progress.md)
- REQ/AC 수: 15/15 (Tier M 상한 16 이내 — iter2 개정으로 REQ-LDSEND-015/
  AC-LDSEND-015 신설, 14→15)
- depends_on 사전 검사: `SPEC-LDRECV-001` `status: completed`(로컬 checkout,
  `git log` 최근 5커밋에 3-phase close 확인) — 충족.
- 사람 확인 대기 항목: **전부 해소됨(2026-09-18)**. plan.md §2.0(가)
  `ExecutionResult.outcome` 필드 확장 — 채택(대안 B). §2.0(나) `SafetyGate.
  revoke_clearances()` + 전용 세션 격리(`run_director_apply()` 내부, iter2
  개정으로 바인딩 위치가 `post_apply()` 개별 구현에서 공유 함수로 이동) —
  채택. §2.0(다) 021 readback 질의 경로 — 코드 선례로 해소
  (`state_port.query_state("DataPool/Sequences/<N>")`). §2.0(라) AC-024
  실패 유발 명령 — M4a 실기 탐색으로 이연(후보 2개 목록화 완료, HALT 조건
  명시). §2.0(마, 신설) 관측 도구의 apply 경로 — 공유 함수 `run_director_
  apply()`(`server/director/execution.py`)로 `post_apply()` 의 apply
  흐름을 추출하고, 관측 도구도 그 함수만 호출해 실제 `GateBundleSender`/
  `execute_bundles()` 를 탄다; 도구는 자기 로컬 `DirectorStore`/
  `ApprovalRegistry.approve()`(공개 API)로 진짜 `ApprovalBinding` 을
  발급한다 — 채택.
- iter2 감사(D9-D12) 반영 요약: **D9(critical)** — 관측 도구가 `screen()`
  단독으로는 `GateBundleSender`/`execute_bundles()` 를 전혀 타지 않아 M5
  가 AC-LDPLUGIN-021/024/032 를 실제로 관측할 수 없었다 → §2.0-마 신설 +
  REQ-LDSEND-007/012/013 재정의 + REQ-LDSEND-015 신설로 해소. **D10** —
  관측 도구 자신의 세션 격리 미비 → 세션 바인딩을 공유 함수 내부로 옮겨
  구조적으로 해소. **D11** — dry-run 이 `build_console_stack()` 기본값
  (`attempt_session_backup=True`)으로 세션 시작 `SaveShow` 를 실제로 보낼
  수 있었다 → REQ-LDSEND-009 확장(dry-run 시 `attempt_session_backup=False`
  명시)으로 해소. **D12(minor)** — REQ-008 "run" 범위 모호 → "run = CLI
  1회 호출 = 시나리오 1개" 명문화로 해소.
- 개정 중 추가 발견(iter1): §1 규범표의 "콘솔 명령 안전 분류" 인용이
  낡았다 — `blacklist.yaml`(version 9)이 `Store Sequence`(v6)·`Store
  Cue`(v7)를 이미 블랙리스트에 넣었다. 인용을 정정하고 REQ-LDSEND-007/012
  를 그에 맞게 다시 썼다(iter2 에서 007/012 는 D9 로 추가로 재정의됨).

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F Phase 4 Mode Selection

- 입력: Tier M · 예상 파일 7~8개(ports.py·gate.py·execution.py·director_api.py EXTEND, sender.py·director_apply_observe.py 신규 + 시험 3개) · 도메인 2(safety·director) · Python 100% · 코딩 위주(병렬 이득 낮음)
- 평가: `direct` 아님(다파일) · `fanout` 아님(코딩 위주) · `sweep` 아님(기계적 일괄 변환 아님) · `serial` 선택
- Decision: serial
- 근거: 코딩 위주 작업은 순차 하위 에이전트가 기본값이다. M1→M2→M3→M4 는 앞 단계 인터페이스에 의존한다.

## §G Implementation Kickoff (2026-09-18)

- plan-audit: iter1 FAIL 0.75 → iter2 FAIL 0.63 → iter3 **PASS 0.86** (`.moai/reports/plan-audit/SPEC-LDSEND-001-review-3.md`). iter3 D13(문장 잔재)은 `3c6aa451`·`7804dc13` 으로 정정.
- 사람 결정(2026-09-18): ① `ExecutionResult.outcome` 필드 추가 ② apply 별 전용 세션 + `revoke_clearances()` — 바인딩은 `run_director_apply()` 안 ③ 도구는 `Delete` 를 보내지 않고 정리 명령만 출력 ④ 실패 유발 명령·readback 경로는 M4a 실기 탐색 후 HALT 해 사람 확인 ⑤ 착수 승인: **M1 부터 시작, M4a 앞에서 반드시 정지**.
- 상태: 착수 승인됨, 구현 미착수(M1 커밋 없음). 콘솔 쓰기(M4a·M5)는 보낼 명령을 보여 주고 다시 확인받은 뒤에만.
