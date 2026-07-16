# SPEC-COPILOT-MVP-001 — progress

## §E.1 Plan-phase Audit-Ready Signal

plan_status: audit-ready
plan_complete_at: 2026-07-15

Plan-phase 산출물: **Tier L 5종**(spec.md / plan.md / acceptance.md / design.md / research.md) + progress.md 생성 완료, `status: draft` (v0.2.0).

amendment 이력: **v0.2.0 (2026-07-15)** — LLM 프로바이더 전략 정식 amendment (사용자 결정 "Gemini 평가 + 멀티 프로바이더 추상화"): §B.12 REQ-MVP-038~041 신설, REQ-MVP-006/007 개정, `/cmd`→`/copilot/cmd` 지연 정합 해소(spec·acceptance·design·research 전면), AC-MVP-026~027 신설, design §A.1 추상화 계층, research §F Gemini 제약. **delta re-audit 필요** (plan.md §F Amendment 이력 참조).

plan-audit 이력: iteration 1 **FAIL (0.59)** → 전건 반영 → iteration 2 **PASS-with-debt (0.92)** → 잔여 지적 반영 완료 — MVP-M9(invoking_verbs 폐쇄 집합 + 재귀 상한 3 + 순환 감지 보류 + AC-MVP-017 동사별 FN 코퍼스), m5(Cmd() 스캔 잔여 위험 명시 — 인간 리뷰가 권위 통제), m6(GEARS 태그 표준화 + REQ-036 shall 절 정비), m7(왕복 조작적 정의 축소 해석 명시 + plan.md §A-7 마커), m8(design §F 백업×측정 정합), m9(AC-MVP-024 결정적 재작업).

clarification gate: **resolved** — plan.md §A 마커 6건 전원 사용자 결정(AskUserQuestion 라운드)으로 해소, "결정됨 (2026-07-15)" 기록으로 대체 (React / Phase 0 버전 승계 / 코퍼스 기본값 승인 / JSONL·90일 감사 로그 / `/copilot/*` OSC 네임스페이스 / 왕복 조작적 정의 승인).

선행 의존: SPEC-COPILOT-EVAL-001 완료 + plan.md §F EVAL 격차 fold-in amendment 필요 (`/cmd`→`/copilot/cmd` 정합은 v0.2.0 amendment에서 해소 완료).

## §E.2 Run-phase Evidence

### M1 — OSC bridge (2026-07-16, manager-develop cycle_type=tdd)

**Scope**: REQ-MVP-001~002 · AC-MVP-011 · plan.md §C row M1 (greenfield scaffold + python-osc bridge)

**AC matrix (M1 subset)**

| AC | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| AC-MVP-011 ① send (`/copilot/cmd` UDP) | PASS | `uv run pytest -v` (TestCommandSending, 4 tests — loopback OSC server asserts address + payload) | `14 passed in 4.35s`; `test_command_is_sent_as_udp_osc_to_copilot_cmd_address PASSED` |
| AC-MVP-011 ② feedback (`/copilot/feedback` → confirmation path) | PASS | `uv run pytest -v` (TestFeedbackReceiving, 4 tests — consumer queue/callback delivery asserted) | `test_feedback_message_is_delivered_to_result_confirmation_path PASSED` |
| REQ-MVP-029 chokepoint invariant (forward design only) | DEFERRED (M4/M6, AC-MVP-019) | n/a — single-module send surface + docstring contract + @MX:ANCHOR in `server/bridge/osc.py` | import-boundary architecture test not yet built (M4 scope) |

**TDD evidence (RED → GREEN → REFACTOR)**

- RED: tests authored first; `uv run pytest` → exit 2, `ModuleNotFoundError: No module named 'server.bridge.osc'` (log: `.moai/state/verify/m1/red.log`)
- GREEN: `server/bridge/osc.py` implemented; `uv run pytest -v` → exit 0, `14 passed in 4.35s` (log: `.moai/state/verify/m1/green.log`)
- REFACTOR: smoke-tool double-instantiation removed; ruff format applied; suite re-green `14 passed in 4.86s` (log: `.moai/state/verify/m1/final.log`)

**Quality gates**

- Coverage: `uv run pytest --cov=server.bridge --cov-report=term-missing` → `server/bridge/osc.py 76 stmts, 2 miss, 97%` (≥85% target; log: `.moai/state/verify/m1/cov.log`)
- Lint: `uv run ruff check .` → `All checks passed!` · `uv run ruff format --check .` → `7 files already formatted` (all NEW code — greenfield, no pre-existing baseline)
- Reproducible install (REQ-MVP-043 seed): uv 0.11.4, Python pinned 3.11 (`.python-version`, resolved 3.11.15), `uv.lock` pins `python-osc==1.10.2` (pure Python — cross-platform)
- Smoke tool self-check (loopback, no console): `uv run python -m server.tools.osc_smoke --port 59999 --listen-port 0 --wait 0.5 "List"` → exit 0 (log: `.moai/state/verify/m1/smoke-selfcheck.log`)

**Deliverables**: `pyproject.toml`, `uv.lock`, `.python-version`, `README.md` (install stub), `server/__init__.py`, `server/bridge/{__init__.py,osc.py}`, `server/tests/{__init__.py,test_osc_bridge.py}`, `server/tools/{__init__.py,osc_smoke.py}` · spec.md frontmatter `draft → in-progress`

**Commits**: `2998120` feat(SPEC-COPILOT-MVP-001): M1 OSC bridge — /copilot/* UDP send + feedback receive (TDD) · push: N/A (no origin remote)

**Gaps (M1)**

- onPC 2.4.2 real-console smoke NOT executed — manual user step via `server/tools/osc_smoke.py` (usage in README.md); reported as gap, not pass
- Feedback loss/timeout ("실행 미확인") handling deliberately absent — M4 scope by design (REQ-MVP-032); M1 delivers only what arrives
- Chokepoint import-boundary architecture test deferred to M4/M6 (AC-MVP-019)

### M2 — Lua responder (2026-07-16, manager-develop cycle_type=tdd)

**Scope**: REQ-MVP-003~004 · AC-MVP-012 · plan.md §C row M2 (Lua 5.4 responder plugin: state snapshot query + execution result retrieval; round-trip verification against the M1 bridge)

**AC matrix (M2 subset — AC-MVP-012 split into automated sub-evidence vs live onPC)**

| AC | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| AC-MVP-012 ①a snapshot logic (automated) | PASS | `uv run pytest server/tests/test_lua_responder.py -v` (31 tests — production `copilot_responder.lua` executed in embedded Lua 5.4 via lupa, mocked MA3 globals; replies decoded with the PYTHON codec = cross-language contract) | `31 passed`; `test_snapshot_of_datapool_sequences PASSED`, `test_child_cap_sets_truncated_flag PASSED` |
| AC-MVP-012 ①b result capture (automated) | PASS | same suite (TestExecResult, 5 tests — Cmd() success/error-string/lua-error classification + command pass-through) | `test_success_result PASSED`, `test_lua_error_in_cmd_is_captured PASSED` |
| AC-MVP-012 ①c full protocol loop (automated, simulated console) | PASS | `uv run pytest server/tests/test_responder_roundtrip.py -v` (9 tests — round-trip tool → OSC/UDP → fake console running the REAL Lua plugin → OSC/UDP replies; only the MA3 API surface is simulated) | `9 passed`; `test_full_roundtrip_passes_all_steps PASSED` |
| AC-MVP-012 ①d Lua syntax/load check | PASS | plugin chunk compiled + loaded by Lua 5.4 (lupa) in every responder test (no system `lua`/`luac` on host — see Gaps) | chunk compiles; `test_plugin_returns_callable_main PASSED` |
| AC-MVP-012 ② live onPC 2.4.2 round-trip (SEMI-AUTOMATIC) | **DEFERRED-gap** | runnable tool shipped: `uv run python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9000` + setup doc `console/lua/README.md` | NOT executed — no live console in this environment; reported as gap, not pass |
| REQ-MVP-002 regression (state reply delivery) | PASS | `uv run pytest server/tests/test_osc_bridge_state.py -v` (4 tests — `/copilot/state` mapped into the same FeedbackConsumer path, address-discriminated) | `4 passed`; M1 suite stays green |

**TDD evidence (RED → GREEN → REFACTOR, 3 cycles)**

- Cycle 1 RED: protocol codec + state-address tests authored first; `uv run pytest` → collection errors `ModuleNotFoundError`/`ImportError: STATE_ADDRESS` (log: `.moai/state/verify/m2/red-cycle1.log`) → GREEN: `server/bridge/protocol.py` + osc.py state mapping; `35 passed` (log: `green-cycle1.log`)
- Cycle 2 RED: 31 lupa-based responder tests against missing `console/lua/copilot_responder.lua` → `1 failed, 30 errors` (log: `red-cycle2.log`) → GREEN: plugin implemented; `31 passed` (log: `green-cycle2.log`)
- Cycle 3 RED: round-trip tool tests → collection error (log: `red-cycle3.log`) → GREEN: `responder_roundtrip.py`; `9 passed` (log: `green-cycle3.log`)
- REFACTOR: inline import hoisted, `ruff format` applied repo-wide; full suite re-green `75 passed in 15.67s` (log: `final-suite.log`)

**Quality gates**

- Tests: `uv run pytest` → exit 0, `75 passed` (14 M1 + 61 new)
- Coverage: `uv run pytest --cov=server.bridge --cov=server.tools` → NEW modules: `server/bridge/protocol.py` 98%, `server/tools/responder_roundtrip.py` 90% (≥85% each); `server/bridge/osc.py` 97% unchanged; `osc_smoke.py` 0% is the pre-existing M1 dev tool, first included in scope this milestone (log: `.moai/state/verify/m2/cov.log`)
- Lint: `uv run ruff check .` → `All checks passed!` · `uv run ruff format --check .` → `14 files already formatted`
- Dependency pin: `lupa==2.8` added as dev-group dependency (uv.lock) — project-local embedded Lua 5.4 for testing the production plugin; no system packages installed (REQ-MVP-043 reproducible-install discipline)

**Design decisions (recorded — see PROTOCOL.md for full contract)**

- `/copilot/state` interpreted as the snapshot REPLY address; state queries ride `/copilot/cmd` as plugin-invoking command lines (MA3 native OSC input executes only `<prefix>/cmd` — plan.md §A-5 namespace honored within the console's actual OSC model)
- REQ-MVP-004 via wrapped execution (`exec <id> <cmd>` → responder runs `Cmd()`, classifies, replies); raw command lines stay fire-and-forget — M3 opts into wrapping for result confirmation
- Serialization v1: percent-encoded JSON (comma/quote-free, pure ASCII) — survives MA3 packed OSC-send string forms; versioned (`"v":1`), documented in `console/lua/PROTOCOL.md` §3-4
- MA3 plugin packaging: XML wrapper + Lua component (Option A import) with a guaranteed paste-into-plugin-editor fallback (Option B) — `console/lua/README.md` §2
- 5 named live-console assumptions (plugin argument delivery, SendOSCMessage signature, Cmd() result tokens, handle accessors, outbound prefix) recorded in PROTOCOL.md §6 with per-assumption mitigations (CONFIG variants, uservar fallback, --diagnose)

**Deliverables**: `console/lua/{copilot_responder.lua,copilot_responder.xml,PROTOCOL.md,README.md}`, `server/bridge/protocol.py`, `server/bridge/osc.py` (state mapping — minimal edit, send surface untouched), `server/tools/responder_roundtrip.py`, `server/tests/{lua_mock_env.py,test_lua_responder.py,test_osc_bridge_state.py,test_responder_protocol.py,test_responder_roundtrip.py}`, `pyproject.toml`+`uv.lock` (lupa dev dep), `README.md` (M2 section)

**Commits**: `f9f3004` feat(SPEC-COPILOT-MVP-001): M2 Lua responder — state snapshot + exec result capture over /copilot/* (TDD) · push: N/A (no origin remote)

**Gaps (M2)**

- onPC 2.4.2 live round-trip NOT executed (no console in this environment) — semi-automatic user step via `server/tools/responder_roundtrip.py` + `console/lua/README.md` §4; AC-MVP-012 ② remains open until run against a live console
- No system Lua toolchain on host (`lua`/`luac`/`luacheck` absent); Lua verification performed via project-local lupa 2.8 (embedded Lua 5.4) — runtime-level fidelity to the REAL MA3 sandbox is bounded by the mocked API surface
- 5 MA3 API assumptions made without a live console (PROTOCOL.md §6 ASSUMPTION-1..5); each has a documented on-site mitigation but none is live-verified
- XML wrapper import format (Option A) unverified against a real 2.4.2 import dialog — Option B paste path is the guaranteed fallback
- `Cmd()` success-token table (`""`/`"OK"`) is a placeholder classification pending live calibration (ASSUMPTION-3)

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F Phase 4 Mode Selection

- Decision: **sub-agent** (Mode 5 — sequential manager-develop per milestone, cycle_type=tdd)

### Run-phase entry record (2026-07-16)

- audit_gate: **SKIP** per spec-workflow.md § Plan Audit Gate skip policy — 4/4 conditions verified: ① verdict=PASS (0.95, `.moai/reports/plan-audit/plan-audit-20260716.md`) ② score ≥ 0.90 ③ plan-artifact hash unchanged (`git status --porcelain .moai/specs/` → empty, HEAD=c380f62 = audited commit) ④ within 24h (audit 16:04 / verified 16:37 same day)
- depends_on pre-flight: SPEC-COPILOT-EVAL-001 `status: completed` (v0.3.2) — strict fulfillment PASS
- harness_level: **standard** (auto-detection: multi-domain feature; thorough triggers — auth/payment/critical — absent; escalation path retained)
- Implementation Kickoff Approval: **APPROVED** (2026-07-16, AskUserQuestion) — entry from M1; progression = **semi-autonomous (per-milestone check-in)**; commit strategy = **main-direct** (no origin remote — PR unavailable; commit-only, no push)

### Input parameters

- tier: L | scope: greenfield full-SPEC ≥15 files (M1 scope ~4-6 files) | domains: 3 (Python server / Lua console / React UI) — per-milestone single-domain | language mix: Python (M1/M3/M4), Lua (M2/M7), TS/React (M5) | concurrency benefit: LOW (coding-heavy)

### Mode evaluation

| Mode | Selected | Rationale |
|---|---|---|
| 1 trivial | no | multi-file semantic implementation |
| 2 background | no | write-capable blocking implementation |
| 3 agent-team | no | RETIRED |
| 4 parallel | no | coding-heavy, not research fan-out (Anthropic coding-task parallelism caveat) |
| 5 sub-agent | **YES** | sequential per-milestone delegation matches M1→M2→…→M6 dependency chain |
| 6 workflow | no | greenfield new-code, not a uniform mechanical transform |

Justification: coding-heavy greenfield implementation with strict inter-milestone dependencies fits the sequential sub-agent default. Per-milestone check-in selected at the Kickoff gate keeps a human review point between milestones.
