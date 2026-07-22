# SPEC-COPILOT-SHOWUI-001 — progress

## Plan-phase log

- 2026-07-22 — Socratic interview 2 rounds (clarity 4/10 → 8/10) → `interview.md`.
- 2026-07-22 — plan-phase 심층 리서치(`research.md`, file:line 근거) + 디자인 방향(`design-direction.md`) 작성.
- 2026-07-22 — plan proposal 제출 → **DP1 human plan-review gate APPROVED**. clarification 3건 해소: ① 페이더 v1 제외(후속 SPEC 이연), ② All Off = bounded enumeration(광역 `Thru` 금지, 한계 명시), ③ 편집 모드 v1 = unpin 전용(append-only).
- 2026-07-22 — Tier L 아티팩트 세트 생성: `spec.md` + `plan.md` + `acceptance.md` + `design.md` (v0.1.0, status: draft) + 본 `progress.md` 스켈레톤. 다음 단계: plan-audit(Tier L PASS 기준) → design phase → Implementation Kickoff Approval → run.
- 2026-07-22 — plan-audit iteration 1: **FAIL 0.81** (Tier L 기준 0.85; must-pass 7/7 PASS, 전부 텍스트 레벨). 필수 교정 6건(F1 정지/All Off 클래스 서로소 분리, F2 REQ-010 AC 커버(AC-015 신설), F3 REQ-022 target 검증 신설, F4 REQ-004/019 분할 + 잔여 singularity debt HISTORY 기록, F5 REQ-014 측별 재서술, F6 stop busy-가드 면제 명시)을 **v0.2.0**으로 fold-in. REQ-021 소각 결번 유지, 신규 REQ-022~026.
- 2026-07-22 — plan-audit iteration 2: **PASS 0.93**. 비차단 fix-forward 4건을 **v0.2.1**로 정리(재감사 불요, 감사자 승인): R1 4개 아티팩트 버전 정렬(plan.md 헤더 드리프트 해소), R3 REQ-012 gate 정정(clearance 세션-키드 리셋 의미론 — 공존 가정 삭제, 실패 방향 안전=과다 차단, stop-preempts-execute 의도), R2 plan.md silent-drop 측별 정렬, R4 AC-011 All Off 양성 구성 assert 추가. 다음 단계: design phase → Implementation Kickoff Approval → run.

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-07-22T00:00:00Z
- plan_status: audit-ready
- plan_audit: iteration 2 PASS 0.93 (Tier L 기준 0.85), fix-forward v0.2.1 반영
- artifacts: spec.md/plan.md/acceptance.md/design.md/research.md (5-file Tier L) + interview.md + design-direction.md + plan-audit.md
- next: Implementation Kickoff Approval (plan→run HUMAN GATE) → design phase (UI-surfaced route, D1-D5) → run

## §E.2 Run-phase Evidence

### M1 — 프로토콜·데이터 모델 계약 (cycle_type=tdd, RED→GREEN→REFACTOR)

기준선(변경 전, HEAD 9836714): pytest **1380 passed**, vitest **82 passed**.
결과(변경 후): pytest **1478 passed** (+98), vitest **98 passed** (+16). 신규 실패 0건.

| AC | 대상 | 상태 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|---|
| AC-SHOWUI-001 (서버 절반) | REQ-014 — client allowlist 패리티 | **PASS** | `.venv/bin/python -m pytest server/tests/test_web_messages.py -q` | `121 passed in 0.06s` (신규 5종 전부 파싱, `panel_execute_all` 오타는 여전히 `ProtocolError`) |
| AC-SHOWUI-001 (클라이언트 절반) | REQ-014 — server event allowlist 패리티 + null-drop 보존 | **PASS** | `cd ui && npx vitest run` | `Tests 98 passed (98)` (신규 3종 파싱, `v:2`·미지 타입은 여전히 `null`) |
| AC-SHOWUI-005 (parse-time 절반) | REQ-022 — target 정수 검증 | **PASS** | `pytest server/tests/test_web_messages.py -q` | 8종 기형 target × 3 메시지 타입 = 24 케이스 전부 `ProtocolError`; 번들 미구성·`gate.screen()` 미도달 (호출자 자체가 아직 없음) |
| AC-SHOWUI-005 (membership 절반) | REQ-022 — 카탈로그/핀 스토어 존재 검증 | **DEFERRED-M2** | — | 패널 스토어(`server/web/panel.py`)가 M2에 신설되므로 M1에서 구현 불가. 스텁·가짜 구현 금지 원칙에 따라 미착수 |
| AC-SHOWUI-006 | REQ-007 — 단일 스크리닝 경로 | **PASS** | `pytest server/tests/test_architecture.py -q` + `grep -rn "bridge.osc\|from server.bridge" server/web/messages.py` | `4 passed`; grep 0건 (exit 1) |
| AC-SHOWUI-012 (부분) | 전체 회귀 | **PASS** | 위 pytest/vitest 전량 | 1478 + 98, 신규 실패 0 |

부가 검증: `PROTOCOL_VERSION` 양측 모두 `1` 유지(bump 없음) · `npx tsc --noEmit` exit 0 ·
`ruff check` clean · `server/web/messages.py` 커버리지 **100%** (전체 스위트 기준) ·
`grep -rn "window.confirm" ui/src/` 0건.

증적 로그: `.moai/state/verify/showui-m1/` (00 기준선 ~ 07).

### M1에서 동결한 계약 (M2~M6이 그 위에 쌓임)

- **PanelItem**: `id`(=`"<target_kind>:<no>"`, 배열 인덱스 금지) · `kind`(look/effect/sequence) ·
  `target_kind`(executor/sequence — **fixtures 불허**, REQ-003) · `target`(정수 ≥1) ·
  `name` · `appearance`(`#rrggbb`|null) · `source`(pin/auto). 순서 = 그리드 순서(append-only, 정렬 금지).
- **PanelSection**: `name` · `status`(ok/path_not_resolved/console_unreachable — 두 실패 사유 병합 금지) ·
  `truncated` · `drilldown_capped` · `contents_unavailable`.
- **client→server**: `panel_execute`/`panel_stop`/`panel_unpin`(`target_kind`+`target` 검증) ·
  `panel_pin`/`panel_catalog_request`(무페이로드).
- **server→client**: `panel_catalog` · `panel_item_state`(`cue`는 문자열, MA3 큐 번호는 정수가 아님) · `panel_busy`(거부한 타일 명시).
- **UiState.panel**: `items`/`sections`/`running`/`busy` + `clearOnDisconnect`(running·busy 소거, 타일 목록은 보존).

### M1 미결 항목 (다음 마일스톤 의무)

1. **M3 필수** — `server/web/app.py`의 `/ws` 디스패치는 `else: # status_request` 폴백으로 끝난다
   (app.py:279). 신규 panel 타입은 파싱은 되지만 라우팅이 없어 현재 **status 스냅샷으로 응답**된다.
   무해(실행·게이트 호출 0건)하나 M3에서 반드시 분기를 추가해야 한다.
2. **M5 필수** — `useCopilotSocket.ts`의 disconnect 핸들러를 `clearPendingRequests` →
   `clearOnDisconnect`로 교체해야 REQ-015 fail-closed가 실제로 발효된다. 순수 함수는 M1에서 완비·검증됨.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F Phase 4 Mode Selection

### 입력 파라미터

- tier: L (5-artifact 세트 존재)
- scope: 약 12~15 파일 (M1~M6 누계; M1 단독은 5 파일)
- domain count: 2 (UI/TypeScript, 서버/Python) — 3 미만
- file language mix: TypeScript + Python + Markdown, 코딩 중심(신규 로직 작성)
- concurrency benefit: LOW — 프로토콜 계약이 M2~M6 전체를 규정하는 순차 의존 체인

### 모드 평가

| Mode | 선택 | 근거 |
|---|---|---|
| 1 trivial | 미선택 | 신규 모듈·신규 프로토콜 타입 5종 — trivial 아님 |
| 2 background | 미선택 | Write/Edit 수반 (read-only 아님) |
| 3 agent-team | 미선택 | RETIRED (tombstone) |
| 4 parallel | 미선택 | 코딩 중심 + 도메인 2개(<3). Anthropic coding-task parallelism caveat 적용 |
| 5 sub-agent | **선택** | 기본 폴백. 마일스톤당 순차 `Agent(manager-develop)` 1회, cycle_type=tdd |
| 6 workflow | 미선택 | 기계적 균일 변환 아님(신규 설계 코드), ~30파일 미만, 파일 간 의존 존재 |

**Decision: sub-agent**

### 정당화

M1은 프로토콜·데이터 모델 계약으로 M2~M6 전체를 규정하는 단일 응집 단위다. 5개 파일(protocol.ts / protocol.test.ts / messages.py / test_web_messages.py / PROTOCOL.md)이 하나의 계약을 양측에서 미러링하므로 분할 시 측별 드리프트 위험이 오히려 커진다. Anthropic의 coding-task parallelism caveat("most coding tasks involve fewer truly parallelizable tasks than research")에 따라 Mode 5 순차 sub-agent가 정확한 선택이며, Mode 6은 균일 기계 변환 조건을 충족하지 않는다.

### 게이트 기록

- **Plan Audit Gate**: 재실행 skip (4조건 전부 충족) — 최근 verdict PASS 0.93 (≥0.90), plan 아티팩트 무변경(전부 커밋 9836714), 24시간 이내(2026-07-22).
- **Implementation Kickoff Approval (plan→run HUMAN GATE)**: **APPROVED** 2026-07-22, 사용자 3결정 확정 —
  ① 브랜치: `feat/app-deploy-file-import` 유지 (원격 없음 → PR 불가, Route B의 PR 단계는 로컬 커밋으로 대체)
  ② 디자인 페이즈 D1~D5: **생략** — design.md v0.2.1이 이미 구현 가능한 디자인 계약(§1~§9, REQ 트레이서빌리티 포함)이며 `.moai/design/system.md` 부재는 design.md §3 + `styles.css :root`를 canonical로 삼는 것으로 갈음
  ③ 착수 범위: **M1 선행 후 사용자 확인 → M2~M6** (계획서가 M1을 최고 가역성-민감 항목으로 지정)
