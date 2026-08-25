# SPEC-COPILOT-RECVOBS-001 — 진행 기록

칸반 카드 **t57** · 워크트리 `.claude/worktrees/t57` · 브랜치 `WT-recv-observability`

## A. 플랜 단계 요약

- Tier **M** · 산출물 4종(spec / plan / acceptance / progress)
- 대상: `server/tests/conftest.py`(트리거 헬퍼 승격) · `server/tests/test_ws_wait_guard.py`(관측 검사)
- 기존 65자리는 **0곳** 개조. 관측은 새 검사 안에서 일어난다
- 착수 승인 전 해소 필요: plan.md 의 미해소 질문 3건

## §E.1 Plan-phase Audit-Ready Signal

| 항목 | 값 |
|---|---|
| SPEC ID 정규식 자체 검사 | `PASS` (Bash 실행 · `^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$`) |
| ID 충돌 | 없음 (`.moai/specs/` 43개 대조) |
| 산출물 | `spec.md` 295줄 · `plan.md` 184줄 · `acceptance.md` 196줄 |
| Out of Scope | H3 6절, 각 절에 `-` 항목 있음 |
| 미해소 질문 | 3건 (전부 `plan.md`. `spec.md` · `acceptance.md` 에는 0건) |
| 코드 변경 | **0건** — 플랜 단계 |
| 커밋 | 없음 (오케스트레이터 몫) |

**이 단계에서 잰 것**: 없음. 이 SPEC 은 `.moai/reports/t57/design-brief.md` §9·§10 의 **읽은
값**과, 이 세션에서 직접 읽은 소스(`test_web_e2e.py` 5자리 · `test_ws_wait_guard.py` 158줄 ·
`conftest.py:80`·`:116` · `app.py:239`·`:255`·`:381`·`:447`)에 근거한다.

**이 단계가 정정한 것**: t54 §12.5 의 「e2e 5자리가 가장 먼저 갈릴 후보」는 이 트리거에 대해
성립하지 않는다 — 5자리 전부 기대 타입이 `status` 이고 트리거가 미는 것도 `status` 다
(spec.md §C · plan.md §C.1).

**미해소 위험(가장 큰 것)**: 브리프 §9·§10 의 모든 도착·순서 측정은 `_safe_send` 를 갈아끼운
상태에서 났다. 실물 검사에는 그 계측기가 없다 — plan M1 이 이 구멍을 닫는 중단 관문이다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
