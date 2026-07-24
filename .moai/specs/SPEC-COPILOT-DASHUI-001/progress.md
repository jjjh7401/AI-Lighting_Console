# SPEC-COPILOT-DASHUI-001 — progress

## Plan-phase log

- 2026-07-24 — Tier L 판정: UI 레이아웃 재구성(App.tsx/styles.css) + 신규 좌측 컴포넌트 3종 + 서버 카탈로그 확장 + 프로토콜 additive 확장 — 15+ 파일·1000+ LOC 예상, UI-surfaced SPEC. 아티팩트 5종(spec/plan/acceptance/design/research) + 본 progress 스켈레톤 생성 (v0.1.0, status: draft).
- 2026-07-24 — 브랜치 실측: SHOWUI-001 M1~M3은 본 브랜치 조상(서버/프로토콜 기반 실재), M4/M5 UI는 타 브랜치(`feat/app-deploy-file-import`) — 본 SPEC UI는 신규 작성, reconciliation은 범위 제외(research.md §3).
- 2026-07-24 — plan-audit review-1(PASS-WITH-DEBT 0.89) findings D1-D6 folded, D7 no-op(`related_specs` 유지): D1 AC-DASHUI-017 신설(REQ-015 전담) · D2 핀 UI Out of Scope 명시 · D3 stylesheet-guard 교차-브랜치 정정 · D4 PANEL_ITEM_KINDS 배지 확장 명시 · D5 anchor 553-566 정정 · D6 Zone/풀 접힘 세션-휘발 확장. spec.md v0.1.1.
- 다음 단계: plan-audit(Tier L PASS 기준 0.85) → Implementation Kickoff Approval → design phase(UI-surfaced route, D1-D5) → run.

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-07-24T00:00:00Z
- plan_status: audit-ready
- artifacts: spec.md / plan.md / acceptance.md / design.md / research.md (5-file Tier L) + progress.md
- next: plan-audit → Implementation Kickoff Approval (plan→run HUMAN GATE) → design phase → run

## §E.2 Run-phase Evidence

### M1 — 프로토콜·데이터 모델 계약 (2026-07-24, TDD RED→GREEN)

**범위**: plan.md §B M1 3항목 전부 — ① `dash_catalog_request`/`dash_catalog` additive 타입(DashSection = `{name, status, truncated?, drilldown_capped?, contents_unavailable?, items}`, DashItem = `{no, name, appearance?|null, meta?}` — 발화 target 필드 부재, REQ-DASHUI-007 구조적 비발화), ② `PANEL_TARGET_KINDS` + 형제 `PANEL_ITEM_KINDS`/`PanelItemKind` 양측 additive `macro` + `playback_command` 룰북 검증 형태 `Macro <no>`(00_grammar.md:60, one-shot — `Off`+macro는 구성 불가), ③ `UiState.dash`(`{sections, lastSyncAt, stale}`) + `reduceServerEvent` case(replace + nowMs 주입 신선도 스탬프) + `clearOnDisconnect` 확장(동기화된 카탈로그 stale 표기 — 섹션은 잔존, 신선도 주장만 철회). `PROTOCOL_VERSION = 1` 유지, PROTOCOL.md 반영.

**RED 증적**: 서버 — `pytest server/tests/test_web_messages.py` collection ImportError(dash 미구현); UI — `vitest run src/protocol.test.ts` 13 failed / 52 passed. GREEN 후 전량 통과.

| 검증 항목 | 커맨드 | 결과 |
|---|---|---|
| 서버 프로토콜+패널 스위트 | `.venv/bin/python -m pytest -q server/tests/test_web_messages.py server/tests/test_web_panel.py server/tests/test_web_panel_execute.py` | `277 passed, 1 warning in 0.74s` |
| UI 프로토콜 스위트 | `(cd ui && npx vitest run src/protocol.test.ts)` | `Tests 65 passed (65)` (기준선 48 → +17) |
| TS 타입체크 (macro enum은 타입 레벨) | `(cd ui && npx tsc --noEmit)` | exit 0 |
| 전체 pytest | `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest -q` | `3 failed, 1793 passed, 2 skipped` — 실패 3건 전부 **기존 실패**(stash A/B로 M1 무관 귀속: test_lua_responder 1건, test_web_provision_api 1건, test_web_reply_discovery 1건. 셋 다 M1 변경 stash 제거 상태에서도 동일 실패) → **신규 실패 0건** |
| 전체 vitest | `(cd ui && npx vitest run)` | `Tests 115 passed (115)` |
| dash 형상 발화 필드 부재 | `grep -rn "target_kind" ui/src/protocol.ts \| grep -i dash` | 0건 |
| 프로토콜 버전 동결 | `grep -n "PROTOCOL_VERSION = 1" server/web/messages.py ui/src/protocol.ts` | 양측 1 유지 |
| OSC 경계 (AC-016 grep 절반) | `grep -rn "bridge.osc\|from server.bridge" server/web/panel.py` | 0건 (기준선과 동일) |
| ruff | `ruff check` 4개 터치 파일 | clean; `ruff format --check`는 기존 편차만 지적(baseline에서도 동일 실패 — M1 신규 라인 위반 0건) |

**M1 시점 AC 스냅샷** (전체 판정은 M6):

| AC | M1 상태 | 비고 |
|---|---|---|
| AC-DASHUI-001 | PASS | 신규 타입 양측 수락 + 미등록 타입 측별 계약(TS null-drop / 서버 ProtocolError) 회귀 없음 + v==1 양측 assert |
| AC-DASHUI-003 | 부분 PASS | 타입 레벨 절반 완료(DashItem 발화 필드 부재 + `dash_section`이 fire-shaped 항목 거부). membership 거부 절반은 M2 |
| AC-DASHUI-006 | 부분 PASS | 빌더 절반: `playback_command("Go+","macro",3) == "Macro 3"`, `Off`+macro 구성 불가. 게이트 경유·보류는 M2/M5 |
| AC-DASHUI-013 | PASS(M1 시점) | 킥오프 기준선 대비 신규 실패 0건(기존 실패 3건 stash 귀속 기록) |
| AC-DASHUI-016 | PASS(M1 시점) | bridge grep 0건 + `test_architecture.py` 전체 스위트 내 그린 |
| AC-DASHUI-017 | 부분 PASS | reducer 절반: `clearOnDisconnect`가 동기화된 dash를 stale 표기(섹션 보존·미동기화 시 무표기·재수신 시 해제) assert. 재접속 이중 카탈로그+status dispatch는 M5 |

**M2 인계 노트**: `dash_catalog_request`가 이제 파싱되므로 `server/web/app.py` ws 디스패치의 최종 `else:  # status_request` 분기(app.py:409)로 흘러들어가 status 이벤트로 응답된다 — M1 파일 범위(app.py 제외) 밖이라 미수정. M2에서 dash 카탈로그 빌더 배선 시 이 else **앞에** 전용 분기를 추가할 것. 또한 macro가 `panel_stop` parse를 통과하므로(닫힌 집합 공유), M2 membership/M5 UI가 macro stop 경로를 차단해야 함(빌더는 이미 ValueError로 방어).

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
