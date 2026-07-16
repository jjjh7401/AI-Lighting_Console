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

### M3 — Tool-runner server + LLM abstraction (2026-07-16, manager-develop cycle_type=tdd)

**Scope**: REQ-MVP-005~010, 037, 038~041, 042(룰북 축) · AC-MVP-005/013/014①/025/026①/028①②/031 · plan.md §C row M3 (LLM 프로바이더 추상화 우선 구축 + 4종 도구 + 룰북 캐싱 + 자가 수정 루프 + 오류율 측정 지원)

**AC matrix (M3 subset)**

| AC | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| AC-MVP-013 도구 4종 등록 + 단일 활성 프로바이더 + 핀 모델 | PASS | `uv run pytest server/tests/test_tools.py server/tests/test_llm_config.py -v` (registry asserts exactly 4 tools; factory returns single provider; shipped config pins `claude-opus-4-8` / `gemini-2.5-pro`) | `test_exactly_four_tools_registered PASSED`, `test_anthropic_model_is_pinned_to_opus_4_8 PASSED`, `test_exactly_one_active_provider PASSED` |
| AC-MVP-014 ① 프리픽스 바이트 동일성 (N≥5, 가변 값 0건) | PASS | `uv run pytest server/tests/test_rulebook.py -v` (5회 조립 바이트 동일 + 타임스탬프/날짜/UUID/세션 패턴 스캔 0건) | `test_assembly_is_byte_identical_across_five_builds PASSED`, `test_prefix_contains_no_variable_value_patterns PASSED` |
| AC-MVP-014 ② 캐시 읽기 토큰 >0 (조건부 — live) | **N/A (explicit)** | live keys ABSENT in this environment (`ANTHROPIC_API_KEY`/`GEMINI_API_KEY` unset) — evidence path shipped: `uv run python -m server.tools.provider_smoke` ×2 (warm-cache) | 판정은 ①만으로 수행 (acceptance AM-M2a 규정); usage.cache_read_tokens는 중립 인터페이스로 노출됨 (`test_usage_maps_cache_tokens PASSED`) |
| AC-MVP-005 자가 수정 ≤3회 상한 + 실패 보고 | PASS | `uv run pytest server/tests/test_runner_self_correction.py -v` (항상 실패 명령 + scripted provider → 정확히 3회 재시도, 4회 모델 호출, retries_exhausted 실패 보고) | `test_exactly_three_retries_then_failure_report PASSED` |
| AC-MVP-025 get_rig_context showfile 기본 요약 | PASS | `uv run pytest server/tests/test_tools.py -v -k rig` (표준 테스트 스냅샷 픽스처 → patch/groups/presets 어휘 각각 존재) | `test_summarizes_patch_group_preset_vocabulary PASSED` |
| AC-MVP-026 ① 설정 변경만으로 전환 (자동 부분) | PASS | `uv run pytest server/tests/test_llm_config.py -v -k switch` (config A/B가 active 1행만 상이함을 diff assert + 동일 factory로 양 어댑터 mocked boot) | `test_configs_differ_only_in_the_active_line PASSED`, `test_same_factory_boots_anthropic/gemini PASSED` |
| AC-MVP-026 ②③ 양 프로바이더 live 스모크 + 캐시 경로 | PARTIAL (automated) / **live DEFERRED-gap** | 캐시/비캐시 양 경로는 mocked 자동 테스트로 검증 (`test_cache_created_once_and_reused`, `test_cache_failure_falls_back_to_uncached_path`); live 왕복 스모크는 키 부재로 미실행 | `test_cache_failure_falls_back_to_uncached_path PASSED` — live smoke는 M6/키 확보 시 `provider_smoke`로 수행 |
| AC-MVP-028 ①② 용어 사전 축 + 캐시 안정성 | PASS | `uv run pytest server/tests/test_rulebook.py -v -k korean` (사전 축 섹션 존재, 매핑 20항목 ≥10, 샤막·워시 포함, 전 항목이 고정 프리픽스 내부) | `test_at_least_ten_term_mappings PASSED`, `test_includes_shamak_and_wash PASSED` (③ 측정 코퍼스 한국어 변형은 M6 코퍼스 범위) |
| AC-MVP-031 폴백 감지 규칙 (N=20/M=2, 재정의) | PASS | `uv run pytest server/tests/test_fallback_detector.py -v` (합성 시계열: 트리거/회복 미트리거/N·M 재정의/latch 1회 감사 이벤트) | `test_triggers_on_m_consecutive_violating_windows PASSED`, `test_recovery_after_one_violating_window_resets_the_count PASSED`, `test_n_and_m_overrides_are_respected PASSED` |
| REQ-MVP-029 chokepoint forward design | PASS (M3 분량) | `uv run pytest server/tests/test_tools.py -v -k architecture` (orchestrator 소스 import 스캔: server.bridge/pythonosc 0건 + 프로바이더명 0건) | `test_orchestrator_never_touches_the_osc_send_surface PASSED`, `test_orchestrator_is_provider_neutral PASSED` — 정식 AC-MVP-019는 M4/M6 |

**TDD evidence (RED → GREEN → REFACTOR, 3 cycles)**

- Cycle 1 RED: rulebook tests → `ModuleNotFoundError: No module named 'server.rulebook'` (log: `.moai/state/verify/m3/red-cycle1.log`) → GREEN: assets(v2.4.2 3종) + assembly; `10 passed` (log: `green-cycle1.log`)
- Cycle 2 RED: config/adapter tests → 3 collection errors `server.llm` missing (log: `red-cycle2.log`) → GREEN: types/errors/config/factory + Anthropic·Gemini 어댑터; `55 passed` (log: `green-cycle2.log`)
- Cycle 3 RED: tools/runner/fallback tests → 3 collection errors `server.orchestrator` missing (log: `red-cycle3.log`) → GREEN: ports/tools/runner/fallback + provider_smoke; `34+5 passed` (log: `green-cycle3.log`)
- REFACTOR: ruff format 적용, B008 기본값 수정, 아키텍처 테스트를 import문 스캔으로 정밀화; full suite `178 passed` (log: `final-suite.log`)

**Quality gates**

- Tests: `uv run pytest` → exit 0, `178 passed` (75 M1/M2 baseline 유지 + 103 new)
- Coverage (NEW modules, ≥85% each): llm/types 100%, llm/factory 100%, llm/anthropic_adapter 96%, llm/errors 96%, llm/config 91%, llm/gemini_adapter 89%, orchestrator/{ports,tools,runner,fallback} 100%, rulebook/assembly 90%, tools/provider_smoke 88% (log: `.moai/state/verify/m3/cov.log`)
- Lint: `uv run ruff check .` → `All checks passed!` · `uv run ruff format --check .` → `37 files already formatted`
- Dependency pins (REQ-MVP-043 discipline): `anthropic==0.116.0`, `google-genai==2.12.0` (uv.lock); default suite는 네트워크/키 0 의존 (mocked clients)

**Design decisions (check-in ratification 대상)**

1. **Gemini 모델 핀 = `gemini-2.5-pro`**: research.md §F가 구체 모델 ID를 명시하지 않음 → 구현 시점 최신 문서화 안정(GA, non-preview) 모델을 config에 핀. 근거·변경 가능성(코드 무변경 config 전환)은 config/provider.toml 주석에 기록. **웹 검증 미수행** (이 환경에 검색 도구 없음) — M6 측정 전 사용자 확인 권장
2. **Provider config 포맷 = TOML(stdlib tomllib), 위치 `config/provider.toml`**: 의존성 0 추가 (M4 blacklist.yaml은 별도 SSOT — plan.md M4 소관 불변)
3. **Config 로더가 credential-like 키를 거부** (api_key/token/secret/password 등) — Secured 제약의 코드 수준 강제
4. **실행 포트 계약**: `CommandExecutionPort.execute(command) -> ExecutionResult(ok, detail)` 동기·결과확인 포함 — M4 게이트가 유일한 프로덕션 구현 예정; state 조회도 `StateQueryPort` 경유 (tool 코드의 bridge 직접 참조 0건, import 스캔 테스트로 고정)
5. **재시도 정의**: 재시도 1회 = 오류 피드백 후 모델의 run_commands 재호출 1회 (초기 시도 + 최대 3회 교정 = 최대 4회 모델 호출). 기실행 성공 명령은 instruction 범위 dedupe로 재실행 차단(skipped_already_executed)
6. **폴백 감지 의미론**: 윈도우 평가는 매 judged turn마다(윈도우 충족 후), M회 연속 위반 시 트리거 + latch(감사 이벤트 정확히 1회); retry turn은 orchestrator가 피드에서 제외 (acceptance 왕복 측정 §4와 정합)
7. **Anthropic 추론 설정을 config에 핀**: thinking=adaptive, effort=high, max_tokens=16000 — 오류율 측정 §5의 "프로덕션 추론 설정 고정·기록" 요건 대비
8. **get_rig_context 기본 경로** (`Patch/Fixtures`/`DataPool/Groups`/`DataPool/Presets`)는 placeholder — live 캘리브레이션(M6) 전까지 M2 ASSUMPTION 규율과 동일하게 관리, `build_toolset(rig_paths=...)`로 재정의 가능
9. **런어웨이 가드**: max_model_calls=12 (비용 상한 제약 §C 대응; AC 판정 대상 상한은 재시도 3회)
10. **Gemini function_response role="tool"** 등 SDK 배치 관례는 mocked 테스트로는 미확증 — live 검증 항목으로 Gaps에 기재

**Deliverables**: `server/llm/{__init__,types,errors,config,factory,anthropic_adapter,gemini_adapter}.py`, `server/rulebook/{__init__,assembly}.py` + `assets/v2.4.2/{00_grammar,10_object_model,20_korean_terms}.md`, `server/orchestrator/{__init__,ports,tools,runner,fallback}.py`, `server/tools/provider_smoke.py`, `config/provider.toml`, tests 7종(`test_rulebook`, `test_llm_config`, `test_anthropic_adapter`, `test_gemini_adapter`, `test_tools`, `test_runner_self_correction`, `test_fallback_detector`, `test_provider_smoke`), `pyproject.toml`+`uv.lock` (anthropic/google-genai 핀), `README.md` (M3 섹션)

**Commits**: `7e869e6` M3 rulebook assets + deterministic fixed-prefix assembly · `6a2e994` M3 LLM provider abstraction · `099ce76` M3 tool-runner · (본 evidence 커밋) — push: N/A (no origin remote)

**Gaps (M3)**

- **AC-MVP-014 ② live cache-read-token assert 미실행** — 양 프로바이더 키 부재 (explicit N/A; 판정은 ①로 수행, live 증거 경로는 `server/tools/provider_smoke.py`)
- **AC-MVP-026 ②③ live 스모크 미실행** — 키 부재; 자동(mocked) 부분만 PASS. 키 확보 시 `provider_smoke`를 anthropic/gemini 양 구성으로 실행
- **Gemini SDK live 관례 미확증** (research.md §F [구현 시 검증] 잔여): function_response의 role="tool" 배치, context cache 최소 토큰 임계(모델별), 병렬 함수 호출/tool_choice 세부, 무료 등급 rate limit 하 측정 가능성 — mocked 테스트로는 원리 검증만 됨
- **Gemini 모델 핀 웹 재검증 미수행** — `gemini-2.5-pro`는 구현 시점 지식 기준 최신 안정 GA; config 전환만으로 교체 가능
- **get_rig_context 경로 3종 live showfile 미검증** — placeholder 경로 (M6 캘리브레이션)
- **룰북 문법 커버리지는 plan-phase 리서치 한도** — 품질(오류율 <5%)은 M6 측정에서 판정 (M3는 구조+바이트 안정성만 보증)
- **AC-MVP-028 ③** (측정 코퍼스 한국어 지시문 변형에 현장 용어 ≥3종) — M6 코퍼스 작성 범위

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
