# SPEC-COPILOT-RECVOBS-001 — 진행 기록

칸반 카드 **t57** · 워크트리 `.claude/worktrees/t57` · 브랜치 `WT-recv-observability`

## A. 플랜 단계 요약

- Tier **M** · 산출물 4종(spec / plan / acceptance / progress)
- 대상: `server/tests/conftest.py`(트리거 헬퍼 승격) · `server/tests/test_ws_wait_guard.py`(관측 검사)
- 기존 65자리는 **0곳** 개조. 관측은 새 검사 안에서 일어난다
- 미해소 질문 **0건** — 최초 3건은 2026-08-25 리드 재정에서 전부 닫혔다 (plan §D.1 · §F M5 · §G.1)

## §E.1 Plan-phase Audit-Ready Signal

| 항목 | 값 |
|---|---|
| SPEC ID 정규식 자체 검사 | `PASS` (Bash 실행 · `^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$`) |
| ID 충돌 | 없음 (`.moai/specs/` 43개 대조) |
| 산출물 | `spec.md` 305줄 · `plan.md` 233줄 · `acceptance.md` 201줄 |
| Out of Scope | H3 6절, 각 절에 `-` 항목 있음 |
| 미해소 질문 | **0건** (리드 재정 후 — 응답 프레임 조달 · t98 · 강제 수단) |
| 코드 변경 | **0건** — 플랜 단계 |
| 커밋 | `ef79481` (최초 3종) + 재정 반영분 미커밋 |

**리드 재정 3건 (2026-08-25)**

| 질문 | 재정 | 반영 자리 |
|---|---|---|
| 응답 프레임 조달 방식 | 파싱 오류 형태 유지(`ws.send_text("{ not json")`) — 프로토콜 층에 묶는다 | plan §D.1 · §F M3 |
| `status` 아닌 트리거 | 새 카드 **`t98`** (후보 C 워커 스레드 인터리브) | plan §F M5 · spec.md §5 · AC-RECVOBS-018 |
| REQ-RECVOBS-010 강제 수단 | 산문 경고 + AC-RECVOBS-014. 상시 스캐너는 **t94 로 연기** | plan §G.1 · AC-RECVOBS-014 |

**이 단계에서 잰 것**: 없음. 이 SPEC 은 `.moai/reports/t57/design-brief.md` §9·§10·§11·§12 의
**읽은 값**과, 이 세션에서 직접 읽은 소스(`test_web_e2e.py` 5자리 · `test_ws_wait_guard.py`
158줄 · `conftest.py:80`·`:116` · `app.py:239`·`:255`·`:381`·`:447`)에 근거한다.

**이 단계가 정정한 것**: t54 §12.5 의 「e2e 5자리가 가장 먼저 갈릴 후보」는 이 트리거에 대해
성립하지 않는다 — 5자리 전부 기대 타입이 `status` 이고 트리거가 미는 것도 `status` 다
(`test_web_e2e.py:197` · `:216` · `:282` · `:306` · `:325`). 리드가 독립 grep 으로 재확인했다
(브리프 §12) — 검증된 정정이지 추정이 아니다. (spec.md §C · plan.md §C.1)

**미해소 위험(가장 큰 것)**: 브리프 §9·§10 의 도착·순서 측정은 `_safe_send` 를 갈아끼운 상태에서
났다. 브리프 §11 이 계측기를 전부 뺀 프로브에서 순서 20/20 · 음성 대조군 0/20 을 재현해 그 구멍을
좁혔다. 남은 위험은 **출하 형태** — `test_ws_wait_guard.py` 안에서 승격 헬퍼를 거쳐 같은 값이
나오는가다. plan M1 이 그것을 재는 중단 관문이고, AC-RECVOBS-001·002·003 은 글자 그대로 유지된다.
**이 절을 「관문이 이미 충족됐다」로 읽지 말 것.**

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
