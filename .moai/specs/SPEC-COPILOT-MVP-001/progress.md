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

### M4 — Safety gate + audit (2026-07-16, manager-develop cycle_type=tdd)

**Scope**: REQ-MVP-011~018, 026~029, 030~034, 035~036 · AC-MVP-004/006/007a/007b/008/009/015/017/019①②/020/021/022/023/024 + AC-MVP-018 invocation-gate half · plan.md §C row M4 (① 문법 밸리데이터 ② 위험 분류 ③ 인간 승인 + 우회 봉쇄 + 원자성 + 장애 모드 + 라이브 잠금 + 백업 + 감사 로그) · §A-4 (감사 로그) · §A-6 (밸리데이터 깊이 확정)

**AC matrix (M4 subset)**

| AC | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| AC-MVP-004 블랙리스트 FN 코퍼스 (SSOT 전수 × ≥3 변형 = 18+, 미탐 0) | PASS | `uv run pytest server/tests/test_safety_corpus.py -q` (corpus reads `server/safety/blacklist.yaml` dynamically — 6 entries × 3 variants direct/bundle/indirect + port-level defense = 18+6 cases; deny-all port, `console.executed == []` asserted per case) | `82 passed in 0.11s`; `test_no_send_without_approval[0..2-Delete/…/Format] PASSED` |
| AC-MVP-006 감사 4종 이벤트 완전성 (누락 0) | PASS | `uv run pytest server/tests/test_safety_e2e_audit.py -v` (fake-console loopback E2E: executed/approved/rejected/blocked reconciled vs scenario expectations, zero misses per type) | `test_every_send_reconciles_with_a_gate_passage_record PASSED` |
| AC-MVP-007a 잠금 중 송신 0 + 제안 카드 | PASS | `uv run pytest server/tests/test_safety_gate.py -v -k lock` | `test_lock_active_produces_proposal_only PASSED` |
| AC-MVP-007b 잠금 해제 후 경로 복원 | PASS | same | `test_unlock_restores_the_normal_path PASSED` |
| AC-MVP-008 백업 3규칙 + 비위험 미개입 | PASS | `uv run pytest server/tests/test_safety_backup.py server/tests/test_safety_gate.py -v -k backup` (①세션시작 ②주기(fake clock, 600s 기본) ③위험 직전 — backup→execute 순서 assert ④비위험 경로 backup 0회) | `test_pre_risky_backup_runs_before_execution PASSED`, `test_safe_bundle_needs_no_approval_and_no_backup PASSED` |
| AC-MVP-009 번들 all-or-nothing | PASS | `uv run pytest server/tests/test_safety_gate.py -v -k rejection` (1건 거부 → 전체 미실행, OSC 0건, 안전 명령 clearance도 미발급) | `test_rejection_is_all_or_nothing PASSED` |
| AC-MVP-015 ① 게이트 3단계 순서 | PASS | `uv run pytest server/tests/test_safety_gate.py -v -k order or stages` (stage_observer records) | `test_stages_run_grammar_then_classify_then_approval PASSED` — `["grammar","classify","approval"]` |
| AC-MVP-015 ② 파싱 불가 차단 + 자가 수정 회신 | PASS | `uv run pytest server/tests/test_safety_gate.py -v -k grammar or correction` (runner E2E: blocked reason이 ToolResultsMessage로 회신, 교정 턴 성공, retries_used=1) | `test_grammar_block_reason_feeds_the_self_correction_loop PASSED` |
| AC-MVP-017 invoking 전수 FN 코퍼스 (10동사+2베어 × 4시나리오 = 48, 송신 0) | PASS | `uv run pytest server/tests/test_safety_corpus.py -q` (SSOT 파일 순회 × {risky-body, unverifiable, depth-4, cycle}; 전 케이스 `console.executed == []` + 승인 보류 도달 assert; 클린 바디 전개-통과 카운터 케이스 포함) | `82 passed` (48 invoking cases 포함) |
| AC-MVP-018 호출 게이트 절반 (②매회 승인 ③비파괴도 게이트 경유+감사) | PASS | `uv run pytest server/tests/test_safety_gate.py -v -k plugin` (destructive 플래그 2회 호출 → 승인 2회; 비파괴 등록 플러그인 → 무승인 통과 + executed 감사 기록) | `test_destructive_flagged_plugin_requires_approval_every_time PASSED` — deploy-scan 절반은 M7 |
| AC-MVP-019 ① 임포트 경계 | PASS | `uv run pytest server/tests/test_architecture.py -v` (서버 전 트리 스캔: server.bridge/pythonosc 임포트는 server/safety+bridge+tests+명시 2개 운영 도구만; positive control 포함) | `test_only_the_safety_gate_reaches_the_osc_send_surface PASSED` |
| AC-MVP-019 ② 송신↔감사 1:1 대조 | PASS | `uv run pytest server/tests/test_safety_e2e_audit.py -v` (real OscBridge UDP loopback + fake console: exec 수신 multiset == executed(command/backup) multiset; ping↔heartbeat; state↔state_query; 미승인 위험 명령 wire 0건) | `test_unapproved_risky_command_never_reaches_the_wire PASSED` |
| AC-MVP-020 오프라인/저하/실행 미확인 | PASS | `uv run pytest server/tests/test_safety_gate.py server/tests/test_safety_lock_monitor.py -v -k offline or degraded or unconfirmed` (①오프라인 → 차단+상태 노출 ②저하 → 부수효과 미개시 ③미확인 → 보고+자동 재전송 0 — 재화면 시 승인 보류 전환) | `test_console_offline_blocks_new_executions PASSED`, `test_unconfirmed_result_is_reported_and_never_auto_resent PASSED` |
| AC-MVP-021 번들 부분 실패 원자성 (게이트+러너) | PASS | `uv run pytest server/tests/test_safety_gate.py -v -k partial` (3건 중 2번째 실패 → 즉시 중단, 3번째 not_executed, 교정 턴에서 1번째 재전송 0 — 총 실행 시퀀스 assert) | `test_bundle_partial_failure_atomicity PASSED` — 승인 요청은 명령문+위험 사유 포함(UI 렌더는 M5) |
| AC-MVP-022 백업 실패 fail-safe | PASS | `uv run pytest server/tests/test_safety_gate.py -v -k backup_failure` (백업 예외 → blocked_backup_failed, 송신 0, notice 통지, 감사 blocked) | `test_backup_failure_blocks_execution_and_notifies PASSED` |
| AC-MVP-023 잠금-우선 | PASS | `uv run pytest server/tests/test_safety_gate.py -v -k lock_first` (승인 대기 중 잠금 활성 → 승인 True 반환에도 실행 불가 + 이후 port 호출도 거부; executor 재확인 별도 테스트) | `test_lock_first_wins_over_a_pending_approval PASSED` |
| AC-MVP-024 대상 미특정 결정적 보류 (≥5 케이스) | PASS | `uv run pytest server/tests/test_safety_corpus.py -v -k unspecified` (게이트 직접 주입 6케이스: `Delete`/`Delete *`/`Delete Sequence Thru`/`Delete Thru 10`/`Remove All`/`Off Everything` → 전건 실행 0 + 승인 보류 + 경고가 ApprovalRequest.warnings에 표면화) | `test_held_with_unspecified_target_warning_and_zero_sends[...] PASSED` ×6 |

**TDD evidence (RED → GREEN → REFACTOR, 4 cycles)**

- Cycle 1 RED: ruleset/grammar tests → collection errors `No module named 'server.safety'` (log: `.moai/state/verify/m4/red-cycle1.log`) → GREEN: blacklist.yaml SSOT + ruleset loader + structural validator; `36 passed` (log: `green-cycle1.log`)
- Cycle 2 RED: classify/expand tests → 2 collection errors (log: `red-cycle2.log`) → GREEN: syntax-based classification + expand-or-hold + plugin registry; `48 passed` (log: `green-cycle2.log`)
- Cycle 3 RED: audit/backup/lock/monitor → 3 collection errors (log: `red-cycle3.log`) → GREEN: JSONL audit + 3-rule backup + lock + health monitor; `31 passed` (log: `green-cycle3.log`)
- Cycle 4 RED: console/gate/corpus/e2e → 4 collection errors (log: `red-cycle4.log`) → GREEN: ConsoleLink + SafetyGate + orchestrator wiring; 1 test-expectation fix (heartbeat-after-success는 degraded가 옳은 분류); `138 passed` (log: `green-cycle4.log`)
- REFACTOR: ruff --fix(미사용 import) + format 적용, E501 2건 수동 정리, `_query_state` 실패 시에도 감사 기록(1:1 대조 무결성); full suite `431 passed in 16.64s` (log: `final-suite.log`)

**Quality gates**

- Tests: `uv run pytest` → exit 0, `431 passed` (178 M1~M3 baseline 유지 + 253 new)
- Coverage (NEW modules, ≥85% each): safety/{expand,lock,monitor,registry} 100%, gate 98%, console 98%, classify 98%, grammar 97%, audit 96%, approval 95%, backup 94%, ruleset 93%; orchestrator/{ports,tools,runner,fallback} 100% (wiring 포함) (log: `.moai/state/verify/m4/cov.log`)
- Lint: `uv run ruff check .` → `All checks passed!` · `uv run ruff format --check .` → `62 files already formatted`
- Dependency pin (REQ-MVP-043 discipline): `pyyaml==6.0.3` (uv.lock) — blacklist.yaml SSOT가 plan.md §C에서 YAML로 지정됨

**Design decisions (check-in ratification 대상)**

1. **밸리데이터 깊이 (plan §A-6 확정)**: **구조적 파서** — 단일행 토큰화 + 따옴표 균형 + 선두 verb-shape 검사 (키워드 화이트리스트도 완전 문법도 아님). 근거: ① stage ①의 역할은 파싱 불가 거부 + verb/args 토큰 공급이며 안전은 stage ② 분류가 담당 ② 완전 문법·키워드 화이트리스트는 정당한 MA3 명령 과차단으로 오류율 측정(M6)을 오염 ③ 과차단은 자가 수정 루프로 회수(FP 허용). 숫자 선행 선택 단축형(`1 Thru 10 At 50`)은 거부됨 — 모델이 키워드형으로 재생성
2. **키워드 매칭 = 축약 인지(FP-safe 방향)**: MA3가 키워드 축약(`Del`→`Delete`)을 허용하므로 ci-정확 일치 OR ≥3자 접두(옵션은 1자부터, `/o`→`/overwrite`)로 매칭 — 축약으로 폐쇄 집합을 우회하는 FN 경로 차단. 과잉 매칭은 승인으로 해소
3. **운영 도구 2종 게이트 예외 (아키텍처 테스트 파일-정확 화이트리스트)**: `server/tools/osc_smoke.py`, `responder_roundtrip.py` — 게이트 **아래** transport 계층을 진단하는 비프로덕션 운영 CLI(수동 실행 전용, 헤드리스 문맥에 승인 채널 부재). 신규 파일은 자동으로 검사 대상 (예외는 파일명 고정 + 존재 검증)
4. **백업 명령 = `SaveShow` (onPC 미검증 가정)**: exec 경로로 송신, 결과 미확인 시 BackupError(fail-safe). M6 라이브 캘리브레이션 항목
5. **감사 로그 경로 = `server/audit_logs/`** (plan §A-4 "server/ 하위" 위임 이행; gitignore 처리). 모든 콘솔 송신을 kind 구분(command/backup/heartbeat/state_query)으로 executed 이벤트에 기록 — 1:1 대조가 4종 이벤트 완전성보다 강한 불변식이 됨
6. **타임아웃 기본값**: exec 확인 5.0s / ping 2.0s / state 조회 5.0s / 활동 윈도 15.0s — 전부 설정 가능(LinkTimeouts, HealthMonitor)
7. **클리어런스 토큰 실행 모델**: screen()이 번들 클리어런스 발급, 실행 포트는 1회 소비 후 거부 — 포트를 직접 쥔 호출자도 심사 없이 송신 불가(우회 원천 봉쇄). 새 screen은 기존 클리어런스 무효화, 잠금/건강 상태는 송신 직전 재확인
8. **승인 기본값 = deny-all + 동기 ApprovalPort**: 승인 채널 미배선 시 위험 명령 실행 불가(REQ-MVP-014). M5가 WebSocket 블로킹 포트로 구현
9. **expand-or-hold 인식 타입 = {Macro, Plugin, Sequence}**: 인식 불가 참조(`Goto Cue 3` 등)는 전부 미검증 보류 — `Go Cue` 상용 패턴도 보류됨(과보류 인정, M5/M6에서 fetcher map 튜닝; 안전 기본값 유지). Body-path 템플릿(`DataPool/Macros/{ref}` 자식 name = 바디 라인)은 onPC 미검증 placeholder
10. **미확인 명령 재전송 = 인간 승인 필요**: 실행 미확인 이력 명령은 재심사 시 자동 클리어 대신 승인 보류(REQ-MVP-032의 "자동 재전송 금지"를 게이트 수준 불변식으로)
11. **러너 재시도 계정**: gate "blocked"(문법/건강/백업)는 교정 라운드로 계수(≤3 상한이 REQ-MVP-012 루프를 bound); 인간 "rejected"/잠금 "proposal"은 기술 실패가 아니므로 미계수
12. **runner.py/tools.py/ports.py 최소 수정 (B10 정당화)**: BundleGate 프로토콜 추가(ports), run_commands 번들 사전 심사(tools), blocked 재시도 계수(runner) — M3 테스트 178건 전부 무수정 green 유지
13. **초기 폐쇄 집합 내용을 테스트로 핀 고정**: SSOT 파일 개정 시 테스트도 갱신 필요(의도된 리뷰 마찰 — 무단 집합 변경 불가). FN 코퍼스 자체는 파일을 동적으로 읽어 개정 시 자동 확장

**Deliverables**: `server/safety/{__init__,ruleset,grammar,classify,expand,registry,audit,backup,lock,monitor,console,approval,gate}.py` + `blacklist.yaml`(SSOT v1), `server/orchestrator/{ports,tools,runner}.py`(최소 wiring), tests 12종(`test_safety_{ruleset,grammar,classify,expand,audit,backup,lock_monitor,console,gate,corpus,e2e_audit}` + `test_architecture`), `pyproject.toml`+`uv.lock`(pyyaml), `.gitignore`(audit_logs), `README.md`(M4 섹션)

**Commits**: `3b0ed8e` M4 safety ruleset SSOT + grammar validator · `4b6e876` M4 risk classification + expand-or-hold + plugin flag registry · `e0b4114` M4 audit log + backup policy + live lock + health monitor · `5e59c5c` M4 safety gate pipeline + chokepoint architecture tests + orchestrator wiring · (본 evidence 커밋) — push: N/A (no origin remote)

**Gaps (M4)**

- **onPC 2.4.2 라이브 미검증**: `SaveShow` 백업 명령의 실제 효과, 하트비트/핑의 실콘솔 의미론, body-path 템플릿(`DataPool/Macros/{ref}` 자식 name=바디 라인) — 전부 fake-console/mocked 검증; M6 라이브 캘리브레이션 필요 (M2 ASSUMPTION 규율과 동일 관리)
- **UI 승인 표면은 M5**: ApprovalRequest가 명령문+위험 사유+경고를 운반(AC-MVP-021의 데이터 절반)하나 WebSocket 승인/거부 UI·잠금 토글·상태 표시는 M5 범위
- **AC-MVP-018 deploy-scan 절반은 M7**: pcall 컴파일 + Cmd() 파괴 스캔 + 리뷰 게이트 + 레지스트리 등록이 M7; M4는 호출-시점 게이트(플래그 레지스트리 소비)만
- **주기 백업 스케줄러 미배선**: BackupManager.tick()은 fake-clock 검증 완료; 실제 타이머 구동은 M5/M6 런타임(서버 수명주기) 소관
- **AC-MVP-019 ② "모든 송신"의 해석**: 심사 중 바디 조회(state query)는 read-only이며 코퍼스 테스트는 in-memory fetcher로 문자 그대로 OSC 0건을 보장; 프로덕션 심사의 state 조회 송신도 감사 대상(kind=state_query)이나 "승인 전 실행성 송신 0건"이 안전 불변식의 본체

### M5 — Korean chat UI: FastAPI + WebSocket server + React frontend (2026-07-17, manager-develop cycle_type=tdd)

**Scope**: REQ-MVP-020~022, 044 · AC-MVP-016 ①②③ / AC-MVP-030 ①②③ (양 프로바이더) + REQ-MVP-030~036 UI halves · plan.md §C row M5 (FastAPI+WebSocket 서버, 한국어 채팅 화면, 승인/거부 UI, 라이브 잠금 토글, 결과 보고 — React, §A-1 확정) + AD4-m1 라이더 (왕복 측정 훅 + 폴백 감지 피드)

**AC matrix (M5 subset)**

| AC | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| AC-MVP-016 ① 한국어 지시 WS 왕복 (실 WS + UDP 루프백 fake console + 실 게이트) | PASS | `uv run pytest server/tests/test_web_e2e.py -v` | `test_korean_instruction_round_trip PASSED` — wire에 `Store Group 3` 도달, 한국어 chat_response, judged 측정 레코드 1건 |
| AC-MVP-016 ② 승인 대기 → WS에 명령+위험 사유+승인/거부, 결정→게이트 | PASS | same (approve: 실행 + rule ③ 백업 선행 wire 확인 / reject: OSC 0건 + 번들 무효) | `test_approve_executes_the_risky_bundle PASSED`, `test_reject_voids_the_bundle PASSED` — `exec_commands == ["SaveShow", "Delete Sequence 5"]` / `== []` |
| AC-MVP-016 ③ 완료/실패 한국어 보고 | PASS | same (완료: `실행 완료` 라벨 / 실패: retries_exhausted + `실패` 요약) | `test_completion_report_is_korean PASSED`, `test_failure_report_is_korean_after_retries_exhausted PASSED` |
| AC-MVP-030 ①②③ Anthropic 경로 (실 어댑터 + 실 SDK 예외 3종: rate_limit/auth/server) | PASS | `uv run pytest server/tests/test_web_session.py -v -k anthropic` | `test_anthropic_rate_limit/auth_failure/server_error PASSED` — ① 표면 전 이벤트에 raw 문자열 0건 ② 한국어 메시지 ③ audit `provider_error.raw_detail`에 원문 |
| AC-MVP-030 ①②③ Gemini 경로 (실 어댑터 + APIError 429/401/503) | PASS | `uv run pytest server/tests/test_web_session.py -v -k gemini` | `test_gemini_rate_limit/auth_failure/server_error PASSED` — 동일 3분리 검증 |
| REQ-MVP-030 UI half — 콘솔 오프라인 표시 + 신규 실행 차단 표기 | PASS | `test_web_session.py::TestFailureModeSurfaces` + `test_web_app.py::TestRuntimeLoops` (heartbeat 루프 status push) | `test_console_offline_blocks_and_reports_in_korean PASSED`, `test_heartbeat_loop_pushes_status_changes PASSED` — `executions_blocked: true` |
| REQ-MVP-031 UI half — responder 저하 표시 | PASS | `test_responder_degraded_blocks_and_reports_in_korean` | PASSED — 요약에 "응답기 … 저하" |
| REQ-MVP-032 UI half — 명령 단위 "실행 미확인" 보고 | PASS | `test_unconfirmed_execution_reports_and_never_claims_success` + `test_unconfirmed_execution_is_reported_as_unconfirmed_not_failed` | PASSED — status `unconfirmed`, 라벨 `실행 미확인 (자동 재전송 안 함)`, 요약에 "완료" 부재 |
| REQ-MVP-033 UI half — 번들 부분 실행 보고 | PASS | `test_partial_execution_summary` (executed_ok+failed+not_executed 혼합) | PASSED — "일부 명령만 실행되었습니다 (부분 실행)" |
| REQ-MVP-034 UI half — 백업 실패 통지 | PASS | `test_backup_failure_notifies_and_blocks` | PASSED — notice 이벤트 "백업" + 요약 "차단", OSC 0건 |
| REQ-MVP-035 UI half — 잠금-우선 (비동기 브리지 생존) | PASS | `test_lock_first_wins_over_an_in_flight_approval` (세션) + `test_lock_first_beats_a_pending_approval_over_ws` (실 WS+wire) | PASSED ×2 — 승인 True에도 wire 0건, proposal 전환 |
| REQ-MVP-036b UI half — 대상 미특정 경고 표시 | PASS | approval_request 이벤트 `items[].warnings` 운반 (`test_approval_request_event_carries_commands_reasons_warnings_actions`) + UI ApprovalCard 경고 렌더 | PASSED — 경고가 WS payload로 표면화, React 카드가 ⚠ 렌더 |
| REQ-MVP-016 UI half — 잠금 토글 + 제안 카드 | PASS | `test_lock_yields_proposal_cards_and_zero_wire_sends` (실 WS) + `test_set_lock_emits_status_events` | PASSED — proposal 이벤트 + wire 0건 + status live_lock 토글 |

**TDD evidence (RED → GREEN → REFACTOR, 3 cycles + serve)**

- Cycle 1 RED: protocol/errors/measure 테스트 → 3 collection errors `No module named 'server.web'` (log: `.moai/state/verify/m5/red-cycle1.log`) → GREEN: messages/korean_errors/measure; `61 passed` (log: `green-cycle1.log`)
- Cycle 2 RED: approval bridge/session → 2 collection errors (log: `red-cycle2.log`) → GREEN: ApprovalChannel + ChatSession; `34 passed` (log: `green-cycle2.log`)
- Cycle 3 RED: bootstrap/app/E2E → 3 collection errors (log: `red-cycle3.log`) → GREEN 반복(부트스트랩 세션 백업 API 재구성, rule ③ 백업 wire 기대 정정, 초기 status 프레임 소비): `28 passed` (log: `green-cycle3.log`) · serve RED (log: `red-serve.log`) → GREEN `19 passed` (log: `green-serve.log`)
- REFACTOR: ruff --fix + format (SIM117/SIM105/SIM103/E501/F841), heartbeat 루프 테스트 경합 수정(pre-connect 전이 수용 — 무한 receive 차단 제거); full suite `560 passed in 37.13s` (log: `final-suite.log`)

**Quality gates**

- Tests: `uv run pytest` → exit 0, **`560 passed`** (431 M1~M4 baseline 유지 + 129 new)
- Coverage (NEW modules): safety/bootstrap 100%, web/{__init__,__main__,korean_errors,messages,serve} 100%, web/session 99%, web/{app,approval_bridge,measure} 97% — 전 모듈 ≥85% (log: `.moai/state/verify/m5/cov.log`)
- Lint: `uv run ruff check .` → `All checks passed!` · `uv run ruff format --check .` → `81 files already formatted`
- UI toolchain (node v22.22.3 / npm 10.9.8 PRESENT): `npm install` OK (lockfile 커밋), `npm test` → vitest **9 passed** (log: `.moai/state/verify/m5/ui-vitest.log`), `npm run build` (tsc+vite) → **`✓ built in 206ms`**, `dist/index.html + assets` 생성 (log: `ui-build.log`), `npx tsc --noEmit` → exit 0
- CLI smoke: `uv run python -m server.web --help` → exit 0
- Dependency pins (REQ-MVP-043): server `fastapi==0.139.1`, `uvicorn==0.51.0`, `websockets` (uv.lock) + dev `httpx`; UI `react 18.3.1`, `vite 5.4.11`, `typescript 5.6.3`, `vitest 2.1.8` (package.json 정확 핀 + package-lock.json)
- Architecture boundary (AC-MVP-019 ①): `test_architecture.py` **무수정 통과** — server/web는 bridge/pythonosc import 0건; 프로덕션 조립은 게이트 소유 `server/safety/bootstrap.py`

**Design decisions (check-in ratification 대상)**

1. **`server/safety/bootstrap.py` 신설 (B10 범위 이탈 — 정당화)**: OscBridge+ConsoleLink+SafetyGate 프로덕션 조립은 아키텍처 테스트가 bridge 접근을 허용하는 유일한 프로덕션 패키지(server/safety) 안에만 둘 수 있음. web 계층에 두면 AC-MVP-019 위반, 테스트 예외 추가는 금지(스폰 프롬프트) → 게이트 소유 부트스트랩이 최소 권한 해법. 테스트 8건 + 100% 커버
2. **"실행 미확인" 감지 = ExecutionResult.detail 접두 문자열 계약** (`execution unconfirmed`): 게이트 무수정 제약 하에서 M4가 구성하는 결정적 문자열을 UI 절반이 소비. 양쪽 테스트가 문자열을 핀 고정(변경 시 양쪽 실패)
3. **폴백 감지 피드 단일화**: Orchestrator는 fallback_detector 없이 구성 — web 계층 RoundTripRecorder가 승인 대기 공제된 측정값(§1–3)으로 judged turn만 피드(§4: retry/오류/실행0건 턴 제외). 이중 계상 원천 차단 (AD4-m1)
4. **왕복 종료 이벤트 = 마지막 콘솔 결과 수신 시각** (acceptance §2 충실): 말미 모델 텍스트 생성 시간 미포함. 콘솔 실행 0건 턴은 기록되나 judged 제외
5. **승인 채널 fail-safe 4중 거부**: UI 미연결/notify 실패/타임아웃(기본 600s, 설정 가능)/연결 해제 전부 deny (REQ-MVP-014)
6. **세션 동시성 = 연결당 1지시** (busy 이벤트): 승인 결정·잠금 토글은 지시 진행 중에도 수신 루프에서 처리(잠금-우선의 전송로)
7. **런타임 루프 배선 (M4 gap 해소)**: FastAPI lifespan에서 주기 하트비트(상태 변화 시 status push) + BackupManager.tick() 폴링(실패는 audit `backup_tick_failed` 기록, 루프 생존)
8. **세션 시작 백업은 부팅을 죽이지 않음**: BackupError → stack.session_backup_ok=False 기록 (REQ-MVP-034는 실행 차단이지 서버 차단 아님); 테스트용 ephemeral 포트에서는 `stack.attempt_session_backup()` 후행 호출
9. **expand-or-hold 바디 페처 = 게이트 state port 경유** (audited): 바디 조회 state query도 1:1 감사 대조에 포함 (AC-MVP-019 ②)
10. **UI 버전 정확 핀**: react 18.3.1 / vite 5.4.11 / typescript 5.6.3 / vitest 2.1.8 — 구현 시점 지식 기준 안정 버전, npm install로 존재 확인됨. UI 테스트는 순수 함수(protocol/reducer)만 vitest로 검증(jsdom 미도입 — 저비용 원칙)
11. **정적 서빙**: `ui/dist` 존재 시 FastAPI가 `/`에 마운트(라우트 우선) — 단일 포트 배포

**Deliverables**: `server/web/{__init__,messages,korean_errors,measure,approval_bridge,session,app,serve,__main__}.py` + `PROTOCOL.md`, `server/safety/bootstrap.py`, tests 8종(`test_web_{messages,errors,measure,approval_bridge,session,app,e2e,serve}` + `test_safety_bootstrap`), `ui/`(package.json+lockfile, vite/tsconfig, index.html, src/{protocol.ts,protocol.test.ts,useCopilotSocket.ts,App.tsx,main.tsx,styles.css,components/{ChatView,ApprovalCard,LockToggle,StatusBanner}.tsx}), `pyproject.toml`+`uv.lock`(fastapi/uvicorn/websockets/httpx), `README.md`(M5 섹션)

**Commits**: `48b47c3` M5 WebSocket protocol v1 + Korean error catalog + round-trip measurement · `5424799` M5 async approval bridge + Korean chat session · `d8800b4` M5 FastAPI WebSocket server + gate-owned console bootstrap + E2E · `5a31493` M5 React chat UI (Vite) · `7cf6383` M5 heartbeat-loop test race fix · (본 evidence 커밋) — push: N/A (no origin remote)

**Gaps (M5)**

- **React 브라우저 렌더링 미검증**: `npm run build`(tsc+vite)와 vitest(순수 함수 9건)는 통과했으나 실제 브라우저에서의 컴포넌트 렌더/조작 검증은 미수행 — 브라우저 레벨 E2E는 M6 범위 (계획된 이연)
- **live 키 오류 경로 미검증**: AC-MVP-030은 실 어댑터 + 실 SDK 예외 객체 주입으로 검증(mocked 클라이언트) — 실제 API의 rate limit/인증 실패 재현은 키 부재로 미수행
- **onPC 2.4.2 라이브 미검증**: 전 E2E가 M2/M4 fake-console(UDP 루프백) 기준 — M6 라이브 캘리브레이션 항목 유지 (SaveShow 효과, 하트비트 의미론 등 M4 gap 승계)
- **다중 클라이언트 동시 접속은 설계상 단일 운영자 가정**: 승인 채널은 마지막 bind된 연결로 라우팅 — 다중 운영자 시나리오는 Phase 1 범위 밖 (미테스트)
- **왕복 측정치는 M6 판정용 수집 전 단계**: recorder가 레코드를 메모리에 축적 + judged 피드만 배선 — 코퍼스 실행·중앙값/p95 산출·기록은 M6

### M7 — Lua plugin deployment gate (2026-07-17, manager-develop cycle_type=tdd)

**Scope**: REQ-MVP-019, 027(deploy-scan half), 028(레지스트리 인구) · AC-MVP-010 ①②③ + AC-MVP-018 deploy-scan 절반 + 레지스트리→호출 E2E · plan.md §C row M7 (deploy_plugin pcall 컴파일 하네스 + 리뷰 게이트, M3 도구 스텁 위에 구현, 승인 UI(M5) 연동)

**AC matrix (M7 subset)**

| AC | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| AC-MVP-010 ① 컴파일 실패 → 배포 차단 (+자가 수정 회귀, GWT 5) | PASS | `uv run pytest server/tests/test_deploy_pipeline.py::TestCompileGate server/tests/test_runner_deploy_correction.py::TestDeployRetryCap -v` (컴파일 실패 시 리뷰/배포 0건 + 교정 deploy 시도가 동일 ≤3 재시도 상한에 계수 — 4 model calls, no 5th) | `4 passed` — `test_compile_failure_blocks_the_deploy PASSED`, `test_compile_failures_hit_the_same_three_retry_cap PASSED` (log: `.moai/state/verify/m7/ac-010-1.log`) |
| AC-MVP-010 ② 리뷰 미승인 → 배포 보류 | PASS | `uv run pytest server/tests/test_deploy_pipeline.py::TestReviewGate ... -v` (기본 포트 deny-all — 리뷰 채널 미배선이면 어떤 경로로도 배포 불가; 거부 시 void + 감사; 한국어 "거부됨" 보고) | `5 passed` — `test_default_review_port_denies_everything PASSED`, `test_review_rejection_voids_the_deploy PASSED` (log: `ac-010-2.log`) |
| AC-MVP-010 ③ `Cmd("Delete ...")` 스캔 결과 리뷰어 표시 | PASS | `uv run pytest server/tests/test_deploy_scan.py::TestBlacklistedFindings server/tests/test_web_review.py::TestReviewEvents ... ::TestAppReviewFlow -v` (스캔 결과가 ReviewRequest → review_request WS 이벤트(라인·매칭 엔트리·best-effort caveat) → 실 WS 왕복에서 리뷰어 화면 payload로 도달) | `11 passed` — `test_review_request_event_carries_everything_the_reviewer_needs PASSED`, `test_full_review_round_trip_over_websocket PASSED` (log: `ac-010-3.log`) |
| AC-MVP-018 deploy-scan 절반 (① 스캔 표시 + "파괴적" 플래그 등록) | PASS | `uv run pytest server/tests/test_deploy_gate_e2e.py server/tests/test_deploy_pipeline.py::TestApprovedDeploy -v` (승인 시 `Plugin <name>` 파괴 플래그 등록; 송신 실패/미확인에도 플래그 유지 — 안전 방향) | `7 passed` — `test_destructive_plugin_registers_with_the_flag PASSED` (log: `ac-018.log`) |
| AC-MVP-018 레지스트리→호출 E2E (M4 게이트 즉시 발효) | PASS | same (`test_deploy_gate_e2e.py`) — 배포(승인) → `Plugin "Cleaner"` 호출 → 매회 승인 요구(1차 거부: wire 0건 / 2차 승인: 실행, 승인 요청 2회); 리뷰 거부 플러그인은 미등록 → expand-or-hold 보류 | `test_every_invocation_of_a_deployed_destructive_plugin_needs_approval PASSED` |
| AC-MVP-018 ②③ 호출-시점 게이트 (M4 회귀 — DO NOT REGRESS) | PASS (unmodified) | `uv run pytest server/tests/test_safety_gate.py -v -k plugin` + corpus/e2e-audit 스위트 | `2 passed` + `84 passed` (log: `m4-invocation-regression.log`) — M4 테스트 무수정 green |

**TDD evidence (RED → GREEN → REFACTOR, 3 cycles)**

- Cycle 1 RED: deploy 코어 테스트 → `ModuleNotFoundError: No module named 'server.deploy'` (log: `.moai/state/verify/m7/red-cycle1.log`) → GREEN: compile/scan/review/pipeline; `45 passed` (log: `green-cycle1.log`)
- Cycle 2 RED: transport/E2E/responder → `ImportError: build_deploy_request` (log: `red-cycle2.log`) → GREEN: 프로토콜 빌더 + ConsoleLink.deploy_plugin + gate deploy surface + responder deploy verb; `80 passed` incl. M2 회귀 (log: `green-cycle2.log`)
- Cycle 3 RED: web/runner/tools → `ImportError: review_request_event` + serve/bootstrap 배선 테스트 2 failed (log: `red-cycle3.log`) → GREEN: messages/session/app/serve/bootstrap + UI (vitest 4 RED → 13 passed); `651 passed` (logs: `green-cycle3a.log`, `green-cycle3b.log`)
- REFACTOR: ruff --fix + format 적용; full suite 재green `651 passed` (log: `final-suite.log`)

**Quality gates**

- Tests: `uv run pytest` → exit 0, **`651 passed`** (560 M1~M5 baseline 유지 + 91 new) (log: `.moai/state/verify/m7/final-suite.log`)
- Coverage (M7 new/modified, ≥85% each): deploy/{review 100%, pipeline 99%, compile 87%, scan 86%}, orchestrator/{tools,runner} 100%, web/{messages,serve} 100%, web/session 99%, web/app 96%, web/approval_bridge 97%, safety/{bootstrap 100%, gate 99%, console 97%}, bridge/protocol 98% (log: `cov.log`)
- Lint: `uv run ruff check .` → `All checks passed!` · `uv run ruff format --check .` → `94 files already formatted`
- UI: `npm test` → vitest **13 passed** (9 baseline + 4 review) (log: `ui-vitest.log`) · `npm run build` → `✓ built in 227ms` (log: `ui-build.log`) · `npx tsc --noEmit` → exit 0
- Dependency (REQ-MVP-043 discipline): `lupa==2.8` **dev → runtime 승격** (uv.lock 재잠금; cross-platform wheels 존재 — M2 검증 패턴 승계, ratification 항목)

**Design decisions (check-in ratification 대상)**

1. **lupa 런타임 승격**: pcall 컴파일 하네스가 프로덕션 코드(`server/deploy/compile.py`)에서 embedded Lua 5.4를 사용 — load-only(청크 미실행, text-only 모드로 바이너리 청크 거부), check당 fresh runtime. M2 check-in에서 수용된 lupa 패턴의 연장
2. **Deploy verb 설계 (ASSUMPTION-6, onPC 미검증)**: `deploy <id> <enc-name> <enc-source>` — name·source 모두 percent-encode(따옴표/공백 무관 와이어 안전), 콘솔측 재컴파일(방어 심층) 후 `DataPool/Plugins` Acquire/Append + content setter 4종 probe(pcall-guard). responder 1.1.0(+xml), PROTOCOL.md §2/§4.5/§6 개정 — 와이어 프로토콜 v1 유지(additive)
3. **리뷰 = 별도 요청 타입, M5 채널 재사용**: ApprovalChannel을 payload-generic화(+`request_review` alias) — 두 번째 인스턴스(`id_prefix="review"`)가 ReviewRequest 운반, quadruple-deny(미연결/notify 실패/타임아웃 600s/연결 해제) 그대로 상속. WS 프로토콜 v1 additive: `review_decision`/`review_request`/`review_resolved`
4. **레지스트리 등록 시점 = 리뷰 승인 직후(송신 전)**: REQ-MVP-027 "승인 시 등록" 충실 + 송신 실패/미확인에도 플래그 미회수(unconfirmed 송신은 콘솔에 존재할 수 있음 — 플래그 상실은 M4 호출 게이트 무장해제라 안전 비대칭상 금지)
5. **감사 이벤트 확장(보수적)**: `deploy_requested`/`deploy_blocked`/`deploy_review_approved`/`deploy_review_rejected`/`deployed` + 게이트 송신은 `executed` kind="deploy"(1:1 대조 합류) — 4종 완전성 대조(AC-MVP-006) 무영향(스위트 green)
6. **runner 재시도 계정 확장**: `deploy_plugin` 교정 시도가 run_commands와 동일 ≤3 상한 공유(1-line 변경, M3 178 테스트 무수정 green). 리뷰 거부는 인간 결정 → 재시도 미계수(M4 승인 거부 규칙 대칭)
7. **게이트 deploy surface (gate.py additive method)**: 정책(컴파일+스캔+리뷰)은 `server/deploy/pipeline.py`, 송신-시점 재확인(잠금/건강)+감사는 게이트 소유 `deploy_plugin_source` — 잠금 중 배포는 wire 0건 차단. 스캔/리뷰 통과 후 잠금 차단이면 리뷰 1회 낭비 가능(단일 enforcement 지점 유지 위한 수용)
8. **소스 크기 상한 16KB(설정 가능)**: percent-encode 팽창 후 UDP/MA3 명령 라인 한계는 미검증 가정 — ASSUMPTION-6에 기재, M6 캘리브레이션
9. **스캔 finding 3종**: `blacklisted`(파괴 플래그 구동) / `invoking`(간접 호출 — 리뷰어 경고만, 호출-시점 게이트가 실행 커버) / `unparseable`(경고). 동적 조립(`..`/format/변수)은 `dynamic_calls`로 표면화 — REQ-MVP-027 best-effort 프레이밍 유지(스캔 FP 수용, FN은 인간 리뷰가 권위 통제)
10. **M2 잠복 버그 수정 (범위 내 cascade)**: responder `json_string`의 Lua `%c` 클래스가 로케일 의존으로 0x80–0x9F 바이트를 이스케이프 → 비ASCII 응답(한국어 오브젝트명 등) UTF-8 훼손. 바이트 명시 클래스 `[\0-\31"\\\127]`로 교정(M7 유니코드 배포명 테스트가 발견·핀 고정)

**Deliverables**: `server/deploy/{__init__,compile,scan,review,pipeline}.py`, `server/bridge/protocol.py`(+build_deploy_request), `server/safety/{console,gate,bootstrap}.py`(deploy transport/surface/공유 배선), `console/lua/{copilot_responder.lua(1.1.0),copilot_responder.xml,PROTOCOL.md}`, `server/orchestrator/{tools,runner}.py`(도구 배선+재시도 계정), `server/web/{approval_bridge,messages,session,app,serve}.py` + `PROTOCOL.md`, `ui/src/{protocol.ts,protocol.test.ts,useCopilotSocket.ts,App.tsx,styles.css,components/ReviewCard.tsx}`, tests 7종(`test_deploy_{compile,scan,pipeline,transport,gate_e2e}`, `test_responder_deploy`, `test_runner_deploy_correction`, `test_web_review` + `test_tools`/`test_safety_bootstrap`/`test_web_serve` 확장), `pyproject.toml`+`uv.lock`(lupa 승격), `README.md`(M7 섹션)

**Commits**: `3d23d4e` M7 deploy core (pcall harness + scan + review + pipeline) · `6aa5455` M7 deploy transport (responder verb + gate surface + E2E) · `c445383` M7 tool wiring + review WS flow + React review card · (본 evidence 커밋) — push: N/A (no origin remote)

**Gaps (M7)**

- **onPC 2.4.2 라이브 배포 미실행**: deploy verb의 플러그인-오브젝트 생성 API(ASSUMPTION-6 — Acquire/Append, content setter, 와이어 길이 한계)는 mocked pool 기준 검증 — 실콘솔에서 무해 플러그인으로 우선 검증 필요 (M2/M4 ASSUMPTION 규율과 동일 관리; PROTOCOL.md §6 mitigation 기재)
- **스캔 회피 한계(설계상 잔여 위험)**: 동적 Lua 문자열 조립은 정적 스캔으로 탐지 불가 — `dynamic_calls` 경고로 표면화되나 검증은 불가, REQ-MVP-027 규정대로 인간 리뷰가 권위 통제(스캔은 보조 신호). FP(주석 내 Cmd 등도 스캔)는 수용
- **리뷰 카드 브라우저 렌더링 미검증**: vitest(순수 함수)+tsc+vite build까지 — 실브라우저 조작 검증은 M6 범위(M5 gap 승계)
- **배포 턴 왕복 측정 마킹 미배선**: deploy 송신은 `_MeasuredExecutionPort`를 타지 않아 judged 코퍼스에서 제외됨 — M6 코퍼스(대표 작업 10종 중 "Lua 플러그인 배포") 측정 시 deploy 결과 수신 마킹 배선 필요(리뷰 대기 공제는 recorder 연결로 준비됨)
- **번호 호출 미커버(안전 방향)**: 레지스트리는 이름 기준(`Plugin <name>`) — `Plugin 5`(풀 번호) 호출은 미등록 참조로 expand-or-hold 보류(과보류 수용)
- **잠금 중 배포 시 리뷰 낭비 가능**: 게이트 단일 enforcement 유지의 트레이드오프 (decision 7)

### M6a — 통합 검증 (오프라인) (2026-07-17, manager-develop cycle_type=tdd)

**Scope**: 사용자 승인 M6 분할(M6a 오프라인 / M6b 라이브 — 현재 Gemini 키만 보유, Anthropic 키·onPC 부재) 중 M6a. 측정 코퍼스(≥20종) + 측정 러너(mock 전용, 라이브 미실행) + AC-MVP-001~031 오프라인 증거 스윕 + AC-MVP-029②③ 자동화 절반 + M7 잔여 갭(배포 턴 측정 마킹) 해소. **라이브 LLM API 호출 0건 — 전 테스트가 프로바이더 키 제거 환경에서 통과.**

**AC matrix (전 31건 분류: PASS = 오프라인 자동 테스트 검증 / DEFERRED-M6b = 라이브·onPC 의존)**

| AC | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| AC-MVP-001 대표 작업 10종 한국어 수행 | DEFERRED-M6b (onPC 내부 상태 확인) — 오프라인 절반 PASS: 10종 전 태스크 코퍼스 21시나리오가 mock 파이프라인 E2E(게이트+오케스트레이터) 전건 ok | `uv run pytest server/tests/test_measurement_runner.py -q` (turn_statuses == {ok: 21}, gate_anomalies == {}) | `11 passed` (log: `.moai/state/verify/m6a/ev-measurement.log`) |
| AC-MVP-002 문법 오류율 < 5% (pooled) | DEFERRED-M6b (라이브 프로바이더별 판정) — 측정 기계 PASS: 분모=생성 라인 전수, 분자=최초 생성 거부(교정 성공 후에도 계수), ≥300 라인 반복 상향, 회차별+pooled 산출 | `uv run python -m server.measurement.runner --mode mock` | `pooled 0.0000 = 0/315 lines (threshold 5.00%, pass=True)`, `9 executed (configured 3, escalated=True)` (log: `ev-mock-run.log`) |
| AC-MVP-003 왕복 중앙값 < 10초 | DEFERRED-M6b (라이브 판정) — 측정 기계 PASS: 승인 대기 공제(RoundTripRecorder 재사용), 재시도 턴 분리, 웜캐시(콜드스타트 제외·참고치 보고), median 판정 + p95 보고 | same | `median … / p95 … over 171 judged turns (median pass=True)`, `retry turns (segregated): 0`, `cold-start reference: 0.00086s` |
| AC-MVP-004 블랙리스트 전수 + FN 코퍼스 ≥18 | PASS | `uv run pytest server/tests/test_safety_corpus.py -q` (SSOT 6종 × 3변형 = 18 파라미터 케이스 + 실행 포트 직접 거부) | `130 passed` — no_send_without_approval 18케이스 수집 확인 (log: `ev-ac004-017-024.log`) |
| AC-MVP-005 재시도 ≤3 상한 | PASS | `uv run pytest server/tests/test_runner_self_correction.py -q` (항상 실패 명령 → 3회 후 실패 보고; deploy 교정도 동일 상한 — M7) | `107 passed` (클러스터, log: `ev-llm.log`) |
| AC-MVP-006 감사 4종 이벤트 완전성 | PASS | `uv run pytest server/tests/test_safety_e2e_audit.py -q` (실행·승인·거부·차단 4종 E2E 대조, 누락 0건) | `15 passed` (log: `ev-ac006-019.log`) |
| AC-MVP-007a 잠금 중 송신 0건 + 제안 카드 | PASS | `uv run pytest server/tests/test_safety_gate.py -q` | `86 passed` (클러스터, log: `ev-gate.log`) |
| AC-MVP-007b 잠금 해제 후 정상 실행 복원 | PASS | same | same |
| AC-MVP-008 백업 3규칙 + 비위험 미개입 | PASS | `uv run pytest server/tests/test_safety_backup.py server/tests/test_safety_gate.py -q` | same |
| AC-MVP-009 번들 all-or-nothing | PASS | `uv run pytest server/tests/test_safety_gate.py -q` (1건 거부 → 전체 미실행 OSC 0건) | same |
| AC-MVP-010 배포 게이트 ①②③ | PASS | `uv run pytest server/tests/test_deploy_compile.py test_deploy_scan.py test_deploy_pipeline.py test_deploy_gate_e2e.py test_web_review.py -q` (M7 검증 유지) | `85 passed` (log: `ev-ac010-018.log`) |
| AC-MVP-011 OSC 루프백 송수신 | PASS | `uv run pytest server/tests/test_osc_bridge.py test_osc_bridge_state.py -q` (로컬 루프백 UDP `/copilot/cmd` 송신 + `/copilot/feedback` 수신) | `75 passed` (클러스터, log: `ev-ac011-012.log`) |
| AC-MVP-012 responder 상태 조회·결과 회수 | DEFERRED-M6b (onPC 반자동) — 오프라인 절반 PASS: 프로토콜/Lua mock env 단위 검증 | `uv run pytest server/tests/test_lua_responder.py test_responder_protocol.py test_responder_roundtrip.py -q` | same (`75 passed` 클러스터) |
| AC-MVP-013 도구 4종 + 단일 프로바이더·핀 | PASS | `uv run pytest server/tests/test_tools.py test_llm_config.py -q` (4종 등록 assert + active 정확히 1 + `claude-opus-4-8`/`gemini-3.5-flash` 핀) | `107 passed` (클러스터, log: `ev-llm.log`) |
| AC-MVP-014 ① 프리픽스 바이트 안정성 | PASS | `uv run pytest server/tests/test_rulebook.py -q` (N≥5 조립 바이트 동일 + 가변 값 패턴 0건) | same |
| AC-MVP-014 ② 캐시 읽기 토큰 > 0 | DEFERRED-M6b — 활성 구성(anthropic, prompt_caching=true)은 캐싱 지원이므로 **N/A 아님**, 라이브 API 필요. 오프라인 절반 PASS: cache_control 프리픽스 부착 + cache 토큰 중립 매핑(adapter 테스트) | `uv run pytest server/tests/test_anthropic_adapter.py -q` | same |
| AC-MVP-015 게이트 순서 + 문법 차단 회신 | PASS | `uv run pytest server/tests/test_safety_gate.py test_safety_grammar.py -q` (문법→위험분류→승인 순서 관측 + 파싱 불가 차단 사유 자가 수정 회신) | `86 passed` (log: `ev-gate.log`) |
| AC-MVP-016 한국어 채팅 UI E2E | PASS (mock 프로바이더 WS E2E) | `uv run pytest server/tests/test_web_e2e.py test_web_app.py test_web_approval_bridge.py -q` + `cd ui && npx vitest run` | `122 passed` (log: `ev-web.log`) + `Tests 13 passed` (log: `ev-vitest.log`) |
| AC-MVP-017 invoking_verbs 전수 (10동사+베어 2형) | PASS | `uv run pytest server/tests/test_safety_corpus.py test_safety_expand.py -q` (12형 × 4시나리오(위험 본문/조회 불가/깊이 4/순환) = 48케이스, 승인 전 송신 0건 + 폐쇄 집합 전수 iterate assert) | `130 passed` — 48 파라미터 케이스 수집 확인 (log: `ev-ac004-017-024.log`) |
| AC-MVP-018 배포 스캔 + 호출 게이트 | PASS | `uv run pytest server/tests/test_deploy_gate_e2e.py test_safety_gate.py -q` (파괴 플래그 등록→매회 승인, 비파괴도 게이트 경유 감사) | `85 passed` (log: `ev-ac010-018.log`) |
| AC-MVP-019 단일 관문 불변식 ①② | PASS | `uv run pytest server/tests/test_architecture.py test_safety_e2e_audit.py test_safety_bootstrap.py -q` (① 임포트 경계 정적 스캔 — 신규 `server/measurement/` 포함 전 트리 위반 0건 ② 송신↔게이트 기록 1:1) | `15 passed` (log: `ev-ac006-019.log`) |
| AC-MVP-020 콘솔 오프라인·저하·미확인 | PASS | `uv run pytest server/tests/test_safety_gate.py test_safety_lock_monitor.py -q` (3종 장애 시뮬레이션: 차단/degraded 미개시/미확인+재전송 0건) | `86 passed` (log: `ev-gate.log`) |
| AC-MVP-021 번들 부분 실패 원자성 | PASS | same (k번째 실패 → 중단+잔여 미실행+기실행 재전송 0건+부분 보고) | same |
| AC-MVP-022 백업 실패 fail-safe | PASS | same (백업 실패 주입 → 실행 차단+통지) | same |
| AC-MVP-023 잠금-우선 | PASS | same (승인 대기 중 잠금 → 승인 클릭에도 실행 0건) | same |
| AC-MVP-024 대상 미특정 결정적 게이트 ≥5 | PASS | `uv run pytest server/tests/test_safety_corpus.py test_safety_classify.py -q` (결정적 6케이스 직접 주입 — 전건 자동 실행 0건+보류+경고) | `130 passed` — 6케이스 수집 확인 (log: `ev-ac004-017-024.log`) |
| AC-MVP-025 get_rig_context 기본 요약 | PASS | `uv run pytest server/tests/test_tools.py -q` (패치·그룹·프리셋 어휘 존재) | `107 passed` (클러스터, log: `ev-llm.log`) |
| AC-MVP-026 ① 설정만으로 전환 (코드 diff 0) | PASS | `uv run pytest server/tests/test_llm_config.py -q` (두 구성 diff가 `active` 1행뿐 + 동일 팩토리로 양쪽 기동) | same |
| AC-MVP-026 ②③ 스모크 + 캐시/비캐시 경로 | 오프라인 절반 PASS (fake client 스모크 + anthropic cache_control 경로/gemini 캐시 실패 시 비캐시 폴백) / 라이브 스모크 DEFERRED-M6b | `uv run pytest server/tests/test_provider_smoke.py test_anthropic_adapter.py test_gemini_adapter.py -q` | same |
| AC-MVP-027 ①② 프로바이더별 측정·선정 술어 | DEFERRED-M6b (반자동 — 라이브 실측 + 선정 문서화; 러너가 프로바이더별 실행 준비 완료) | — | — |
| AC-MVP-027 ③ 폴백 설정 전환 + 감사 기록 | PASS | `uv run pytest server/tests/test_fallback_detector.py -q` (트리거 시 감사 이벤트 + latch) | `107 passed` (클러스터, log: `ev-llm.log`) |
| AC-MVP-028 ①② 용어 사전 축 + 프리픽스 안정 | PASS | `uv run pytest server/tests/test_rulebook.py -q` (사전 섹션 존재 + ≥10항목(샤막·워시 포함) + 사전 포함 프리픽스 바이트 동일·가변 값 0건) | same |
| AC-MVP-028 ③ 측정 코퍼스 현장 용어 ≥3종 | PASS (신규) | `uv run pytest server/tests/test_measurement_corpus.py -q` (5시나리오·5용어: 워시/샤막/무빙/암전/페이드 — 룰북 사전 실파일 대조) | `13 passed` (log: `ev-measurement.log`) |
| AC-MVP-029 ① macOS 클린 설치 기동 | DEFERRED-M6b (반자동) | — | — |
| AC-MVP-029 ② lockfile + 설치 문서 존재 | PASS (신규) | `uv run pytest server/tests/test_install_docs.py -q` (uv.lock + ui/package-lock.json + .python-version + README 서버·UI·responder 설치 절차) | `6 passed` (log: `ev-measurement.log`) |
| AC-MVP-029 ③ 비공개 자원 의존 0건 | PASS (자동 슬라이스 + 문서 검수 — README 설치 경로는 uv/npm 공개 자원만 사용, 베타 신청·수동 번들 참조 0건) | same | same |
| AC-MVP-030 raw 오류 미노출 + 한국어 + 로그 | PASS | `uv run pytest server/tests/test_web_errors.py test_web_session.py test_anthropic_adapter.py test_gemini_adapter.py -q` (SDK 오류 3종+(rate limit/인증/malformed) → 표면 raw 0건 + 한국어 메시지 + 감사 로그 원문 — 양 어댑터) | `122 passed` (log: `ev-web.log`) |
| AC-MVP-031 롤링 윈도우 N=20/M=2 | PASS | `uv run pytest server/tests/test_fallback_detector.py test_llm_config.py -q` (합성 시계열: M연속 트리거 / 1회 초과 회복 미트리거 / N·M 재정의 반영) | `107 passed` (클러스터, log: `ev-llm.log`) |

**TDD evidence (RED → GREEN, 3 cycles)**

- Cycle 1 RED: 코퍼스 스키마 테스트 → `ModuleNotFoundError: No module named 'server.measurement'` → GREEN: corpus.yaml(21종) + 로더 `13 passed` → commit `9ed4fd4`
- Cycle 2 RED: 러너 테스트 → collection error (runner 부재) → GREEN: mock provider + 러너 + CLI `11 passed` (첫 GREEN에서 11/11) → commit `b94c266`
- Cycle 3 RED: 배포 턴 judged 코퍼스 편입 테스트 → `2 failed` (M7 갭 재현) → GREEN: `_MeasuredDeployPipeline` 배선 `11 passed` → commit `345c723`
- AC-MVP-029② 검증 테스트는 기존 산출물(uv.lock/README) 검증형 — 작성 즉시 `6 passed` → commit `5eced32`

**Quality gates**

- Tests: `uv run pytest -q` → exit 0, **`681 passed`** (651 M1~M7 baseline 유지 + 30 신규: corpus 13 / runner 11 / install-docs 6) (log: `.moai/state/verify/m6a/ev-final-suite.log`)
- Coverage: `uv run pytest --cov=server -q` → **TOTAL 98%** (7,700 stmts / 173 miss; measurement 신규 모듈: corpus 99%, runner ~96%(라이브 조립 경로 제외), mock_provider 100%) (log: `ev-coverage.log`)
- Lint: `uv run ruff check server` → `All checks passed!` · `uv run ruff format --check server` → `101 files already formatted` (신규 이슈 0건, 기존 baseline 0건)
- UI: `npx vitest run` → **13 passed** (M7 baseline 유지, UI 변경 없음) (log: `ev-vitest.log`)
- 오프라인 불변식: 러너 테스트 전건이 `ANTHROPIC_API_KEY`/`GEMINI_API_KEY`/`GOOGLE_API_KEY` 제거 fixture 하에서 통과 + CLI smoke도 `env -u` 3종 제거로 실행 — 라이브 API 호출 0건
- 아키텍처: `server/measurement/`는 bridge/pythonosc 미임포트 — AC-MVP-019 임포트 경계 테스트가 신규 트리 포함 green

**Design decisions (check-in 보고 대상)**

1. **코퍼스에 mock 블록 내장**: 시나리오별 `mock:` 블록(commands/query_path/plugin 택1)은 M6a mock 러너 전용 — M6b 라이브는 `instruction`만 사용. 코퍼스 SSOT 1벌로 양 모드 공용
2. **분모/분자 계수 지점 = BundleGate 래퍼**: 생성 라인 전수(교정 재생성 포함)가 분모, `grammar:` 사유 차단 라인만 분자(동반 차단 "bundle blocked"는 미계수) — 게이트 진실 기준, 오케스트레이터 우회 불가
3. **RoundTripRecorder 재사용**: M5 measure.py를 그대로 러너에 배선(승인 공제·재시도 분리·judged 술어 동일) — 측정 의미론 fork 방지
4. **배포 턴 judged 편입 (M7 갭 해소)**: `deployed` 확인만 콘솔 결과로 마킹(blocked/rejected는 콘솔 미도달, deploy_failed는 미확인 가능성 — 보수적). 러너 측정 경로에 한정; 프로덕션 ChatSession 배선은 M6b 라이브 측정 시 필요하면 확장
5. **mock 러너의 gate 구성**: DenyAll 승인(기본) + 백업 미부착 + OfflineConsole — 코퍼스가 전건 비위험이므로 승인 미발생이 정상(happy-path 테스트가 gate_anomalies=={}로 고정). 위험 명령이 코퍼스에 유입되면 즉시 anomaly로 가시화
6. **라이브 모드 조립만 제공, 미실행**: `--mode live`는 provider.toml+환경 키+콘솔 스택으로 조립되나 M6a에서 실행·테스트 0건 (deploy 파이프라인 미배선 deny-by-default — 라이브 배포 시나리오는 웹 서버 경유가 전제)

**Deliverables**: `server/measurement/{__init__,corpus,mock_provider,runner}.py`, `server/measurement/corpus.yaml`(21시나리오), `server/tests/{test_measurement_corpus,test_measurement_runner,test_install_docs}.py` · mock 측정 리포트 샘플: `.moai/state/verify/m6a/mock-measurement-report.json`

**Commits**: `9ed4fd4` M6a corpus · `b94c266` M6a runner + CLI · `5eced32` AC-029②③ 자동화 절반 · `345c723` 배포 턴 측정 마킹 · (본 evidence 커밋) — push: N/A (**no origin remote — commit-only**)

**Gaps (M6b-deferred — 라이브·onPC 의존 잔여 목록)**

| 항목 | M6b에서 할 일 | 오프라인에서 이미 검증된 것 |
|---|---|---|
| AC-MVP-001 | onPC 연결 후 10종 E2E — onPC 내부 상태로 결과 확인 | 10종 코퍼스 + mock 파이프라인 E2E 전건 ok |
| AC-MVP-002 | `--mode live`로 프로바이더별(현재 Gemini 키 보유) pooled 오류율 실측·판정 | 계수 규칙·반복 상향·리포트 전부 테스트 완료 — 실행만 남음 |
| AC-MVP-003 | 동일 실행에서 중앙값 판정 + p95 보고 (웜업 1턴 자동) | recorder 의미론·판정 로직 테스트 완료 |
| AC-MVP-012 | onPC 반자동: 오브젝트 트리 조회 스냅샷 + 결과 회수 | 프로토콜·파서·mock env 단위 green |
| AC-MVP-014② | 라이브 2턴째 캐시 읽기 토큰 > 0 확인 (활성 구성 캐싱 지원 — N/A 불가) | cache_control 부착 + 토큰 매핑 green |
| AC-MVP-026② 라이브 절반 | 양 프로바이더 실기동 스모크 (Anthropic 키 확보 필요) | fake-client 스모크 + config-diff-0 green |
| AC-MVP-027①② | 프로바이더별 실측 기록 + REQ-MVP-040 술어로 기본 프로바이더 선정·문서화 (Anthropic 키 부재 시 선정 입력 불완전 — 체크인 결정 필요) | 폴백 규칙(③)은 자동 테스트 green |
| AC-MVP-029① | macOS 클린 환경 설치→기동 (onPC 미연결 "콘솔 오프라인" 표시 확인) | lockfile·문서 존재+개방성 자동 테스트 green |
| M7 ASSUMPTION-6 | deploy verb 실콘솔 캘리브레이션 (M7 gap 승계) | mocked pool 검증 green |
| 브라우저 렌더링 | 실브라우저 조작 검증 (M5/M7 gap 승계) | vitest+tsc+vite build green |

### M6b-1 — Gemini 문법 오류율 실측 (2026-07-17, manager-develop cycle_type=tdd)

**Scope (사용자 승인)**: 라이브 LLM = **Gemini 전용** (`gemini-3.5-flash` 핀, GEMINI_API_KEY만 보유 — Anthropic 키·onPC 부재), 콘솔 측 = mock 유지. 따라서 본 실행의 왕복 수치는 **참고치 전용 — AC-MVP-003 증거 아님**. AC-MVP-002 최종 판정은 M6b-3에서 선정되는 기본 프로바이더 기준(acceptance §8)이며 본 결과는 그 **Gemini 측 입력**이다. 측정 전용 설정 `server/measurement/provider-gemini.toml` 사용 — 출하 기본값 `config/provider.toml`(active=anthropic)은 미변경 (기본 프로바이더 선정은 AC-MVP-027/M6b-3 결정).

**실측 결과** (전문: `.moai/specs/SPEC-COPILOT-MVP-001/measurements/gemini-error-rate-2026-07-17.{json,md}`)

| 항목 | 값 |
|---|---|
| **Pooled 오류율** | **0.0586 = 19/324 — 5% 임계 초과 (Gemini 측 FAIL)** |
| 회차별 (6회) | 4.88% / 8.00% / 6.35% / 4.00% / 5.45% / 6.15% |
| 분모/분자 | 324 라인 (≥300 충족, 3회→6회 자동 상향) / 최초 생성 문법 거부 19 |
| 고정 추론 설정 (§5) | `gemini-3.5-flash`, context_caching=true, cache_ttl=3600s, 생성 파라미터 SDK 기본값 |
| 웜캐시 (§3) | 워밍업 1턴 수행 — 콜드스타트 13.87s 참고치 분리 |
| 재시도 분리 (§4) | 재시도 턴 9건 별도 집계 (judged 제외) |
| 텔레메트리 | 786 model calls · input 3,286,290 / output 38,607 tok · **cache-read 2,288,046 tok (69.6%)** · 429 백오프 0건 · wall clock 2,152.6s |
| 참고 왕복 (mock 콘솔) | median 11.49s / p95 33.56s / judged 106턴 — 판정 비대상 |
| 오류 분해 | 분자 19건 전수가 `misplaced quote inside token` — 모델의 `/Cmd='...'` 옵션 대입 구문 vs 구조 밸리데이터 의도적 과차단(plan §A-6)의 상호작용; loop_limit 11턴 동일 패턴. 밸리데이터 구문 수용 여부는 체크인 결정 사항 |
| 게이트 관측 | rejected 번들 16건 (위험 생성 → deny-all 승인 — 정상 게이트 동작, 감사 로그 기록) |

**AC-MVP-014② (Gemini 구성) 라이브 증거**: 2턴째 이후 캐시 읽기 토큰 > 0 확인 — cache-read 총 2,288,046 tok. 단 활성 출하 구성은 anthropic이므로 **본 AC의 판정 대상 구성(캐싱 지원 = anthropic) 확인은 여전히 M6b 잔여** (Gemini 구성 측 증거는 확보됨).

**라이브 경로 결함 2건 발견·수정 (TDD — 재현 테스트 선행)**

1. **Gemini cached-path 400 (M3 잠복 프로덕션 결함)**: 컨텍스트 캐시 활성 시 어댑터가 generate 요청에 `tools`를 함께 전달 — 실API가 `CachedContent can not be used with GenerateContent request setting system_instruction, tools or tool_config` 400으로 전건 거부 (스모크 1차: 60/60턴 invalid_request, model calls 0). M3 fake는 이 경계 제약을 강제하지 않았음(경계 결함 교과서 사례). **수정**: 시스템 프리픽스 + 고정 툴셋을 CachedContent에 베이크, 캐시 요청은 cached_content만 운반; 캐시와 다른 툴셋 호출은 캐시 우회(무캐시 경로). 재현 테스트 3건이 양 경로 요청 형태를 핀 고정 — commit `3ea66f1`
2. **반복 상향 폭주 (쿼터 가드)**: 전 턴 실패 시(라인 0 추가) ≥300 상향 루프가 max_repetitions(30)까지 공회전 — 라이브 API 호출 소진 위험. **수정**: 직전 회차 라인 추가 0이면 상향 중단 + `denominator_satisfied=false`로 정직 표기 — commit `d1e9bb9`

**신규 인프라 (TDD)**: `--mode live-llm` (라이브 프로바이더 + mock 콘솔 조립 — 기존 `--mode live`는 실콘솔 스택이라 onPC 부재 시 오프라인 차단→재시도 루프로 쿼터 소진했을 구성), `TelemetryBackoffProvider` (retryable ProviderError 지수 백오프 base·2^n 상한 5회, kind별 계수, 토큰 사용량 누계), 지시 단위 provider_error 격리(1턴 실패가 런 전체를 죽이지 않음), `--scenario-limit` 스모크 플래그, 리포트 `wall_clock_seconds`+`provider_telemetry` — commit `a2e72ad`

**Credential 규율**: 키는 각 Bash 호출 내 `source .env`로만 주입(로그·리포트·커밋·CLI 인자 무기록); 커밋 대상 전 파일 키 누출 가드(정확 키 + `AIza` 패턴 grep) **0건 확인**; `.env`는 gitignore 상태로 staged set 미출현; 감사 로그는 gitignored `.moai/state/verify/m6b1/`.

**Quality gates**: `uv run pytest -q` → **692 passed** (M6a 681 + live-llm 7 + gemini 어댑터 재현 3 + 상향 가드 1) (log: `.moai/state/verify/m6b1/ev-final-suite-m6b1.log`) · `uv run ruff check server` → clean · 러너/어댑터 신규 테스트 전건 키 제거 환경 통과 (오프라인 불변식 유지)

**Commits**: `a2e72ad` live-llm mode + backoff · `3ea66f1` Gemini cached-path 400 fix · `d1e9bb9` escalation quota guard · (본 evidence 커밋) — push: N/A (no origin remote)

**M6b 잔여 (M6b-1 이후)**

- **M6b-2 (onPC)**: AC-MVP-001/003/012 라이브 절반 + M7 ASSUMPTION-6 캘리브레이션 — onPC 확보 시
- **M6b-3 (선정)**: AC-MVP-027①② — 기본 프로바이더 선정 술어 적용. **입력 현황**: Gemini pooled 5.86% (>5% — 현 측정으로는 부적격), Anthropic 미측정(키 부재). 선정 결정 + 밸리데이터 `/Cmd='...'` 구문 수용 여부(수용 시 Gemini 분자 19→0 가능성 — 게이트 동작 변경이라 스펙 검토 필요)는 **체크인 인간 결정 필요**
- AC-MVP-029① macOS 클린 설치 (반자동)

### M6b-1r2 — 룰북 보강 후 Gemini 재측정 (2026-07-17, manager-develop cycle_type=tdd)

**Scope**: M6b-1 (`49f729f`) pooled 5.86% FAIL의 원인 조사 + 수정 + 재측정. 사용자 승인 범위: 룰북 보강 + 밸리데이터 재작성-힌트(거부 동작 불변) + 오늘 중 재측정(쿼터 가드). 콘솔은 여전히 mock — 왕복 수치 참고치 전용.

**조사 결론 (두 read-only 에이전트 교차 검증 — 밸리데이터는 정당했음)**

1. `X='...'`/`/opt="..."` 첨부형 대입 구문은 **grandMA2 문법이며 grandMA3 v2.x에서 무효**. 공식 매뉴얼(help.malighting.com v2.4) 근거: `keyword_set.html`(`Set [Obj] Property ["Name"] ["Value"]` — 분리 토큰), `keyword_equal.html`(`Set Macro 3.1 "Enabled" = "No"` — `=`이 별도 토큰), `ok_file.html`(`Export Preset 2.5 /File "Endor"` — 값 옵션은 공백 분리), `extended_command_line.html`(옵션은 bare flag) + MA 포럼 스레드 2건(MA2 스타일 `/cmd=`/`/Color=` 실MA3 실패 사례). **밸리데이터 거부 동작은 변경하지 않음.**
2. 실제 원인은 룰북 교육 공백: (a) 매크로가 실행 대상으로만 교육되고 저작 레시피 부재 → 모델이 MA2 문법으로 공백 충전(16/19), (b) 네이밍 규칙+점 표기 풀 id 조합이 `Preset 4.'Blue'` 유도(3/19), (c) 차단 사유에 재작성 힌트 부재로 자가 수정 루프 소진(11회 loop_limit).

**변경 사항**

- ① 룰북 보강 (`server/rulebook/assets/v2.4.2/00_grammar.md`, commit `b43dafa`): "Authoring a macro" 레시피 — `Set Macro <pool>.<line> Property 'Command' '<text>'` + MA2 anti-example. 이름-참조 명확화 — 인용 이름은 별도 토큰, `pool.'Name'` 점-인용 조합 금지(`Preset 4.'Blue'` anti-example). AC-MVP-028 용어 사전(≥10항목, 샤막·워시) 무변경; 프리픽스 가변-값-없음 유지; `test_rulebook.py` 프리픽스 안정성 테스트 green(콘텐츠 변경은 세션당 캐시 재작성 1회 비용 — 스모크에서 실측 확인).
- ② 밸리데이터 재작성 힌트 (`server/safety/grammar.py`, commit `0ee7992`): 거부 동작 **불변**; MA2 대입 형태 토큰의 "misplaced quote inside token" 거부에만 힌트 부가. 일반 misplaced quote는 힌트 없음. `grammar:` 접두사 유지 — 분자 계수 무영향.

**재측정 결과 vs r1** (전문: `.moai/specs/SPEC-COPILOT-MVP-001/measurements/gemini-error-rate-2026-07-17-r2.{json,md}`)

| 항목 | r1 | r2 (룰북 보강 후) |
|---|---|---|
| **Pooled 오류율** | 0.0586 = 19/324 — **FAIL** | **0.0040 = 1/248 — PASS** |
| 회차별 | 4.88/8.00/6.35/4.00/5.45/6.15% | 0.00/0.00/0.00/2.50/0.00/0.00% |
| 분모/분자 | 324 (충족) / 19 | 248 (**300 미달**) / **1** |
| 턴 상태 | ok 115 / loop_limit 11 | ok 117 / loop_limit 9 |
| 텔레메트리 | 786 calls / cache-read 2,288,046 | 749 calls / cache-read 2,512,146 |
| 429 백오프 | 0 | 0 |

분자 19→1 (94.7% 감소) — r1의 19건(MA2 대입 16 + 점-인용 3) 전건 제거. 잔여 1건은 무관한 신규 롱테일 패턴(`Fixture 'Wash'*` — 닫는 인용 직후 와일드카드 접미사, 본 amendment 범위 밖). 0.40%는 5% 임계 대비 12배 이상 여유.

**분모 300 미달 — 정직한 기록 (판정 무영향)**: r1과 동일 반복 상한(`--max-repetitions 6`)에서 오류율 감소 자체가 분모를 줄이는 부작용(재시도 감소 → 회차당 평균 라인 54.0→40.3) → 248 라인로 종료(`denominator_satisfied: false`). 오늘 누적 사용량(중단된 시도 1회 + 스모크 2회 + 풀런 2회) 고려, 이미 결정적 마진(12배)에서 추가 반복(쿼터 소모) 대신 정직하게 미달 기록 — 경계 분해능 우려는 이 마진에서 실질적 의미 없음. 엄격한 300 하한 준수가 필요하면 별도 저비용 보충 실행(상한 10~12) 권고.

**Quality gates**: `uv run pytest -q` → **702 passed** (692 M6b-1 baseline + 10 신규: 룰북 레시피 4 + 힌트 6) (log: `.moai/state/verify/m6b1r2/ev-r2-suite.log`) · `uv run ruff check server` → clean · **credential 규율**: 전 호출 `set -a; source .env; set +a`로만 주입, 커밋 대상 전 파일(JSON/MD/progress.md) exact-key + `AIza` 패턴 grep **0건**, `.env` staged set 미출현.

**Commits**: `b43dafa` 룰북 보강 · `0ee7992` 밸리데이터 힌트 · (본 evidence 커밋) — push: N/A (no origin remote)

**잔여 (M6b 이후)**: M6b-2(onPC) 미착수 그대로; M6b-3 선정 — Gemini 이제 **적격**(0.40% < 5%), Anthropic 여전히 미측정(키 부재) → 선정 술어(REQ-MVP-040) 적용 시 Gemini가 유일 측정 후보로 적격 통과 상태, 최종 선정은 여전히 체크인 인간 결정 사항; `Fixture 'Wash'*` 롱테일 패턴은 추적 참고용으로 기록(재현 규모 작아 즉각 조치 불요).

### M6c-1 — shared-instance concurrency safety fixes (pre-sync critical/high triage) (2026-07-17, manager-develop cycle_type=tdd)

**Scope**: 독립 다중 에이전트 코드 리뷰(102개 서브 에이전트, 교차검증)가 M6b-1r2 반영 후 전체 코드베이스에 대해 발견한 CRITICAL 1건 + HIGH 2건 — 셋 모두 "production이 동시 접속 WebSocket `ChatSession`마다 정확히 하나의 공유 인스턴스(`ApprovalChannel`/`SafetyGate`)를 세션 격리 없이 배선한다"는 단일 아키텍처 패턴에 근원. REQ-MVP-014/016 안전-격리 보장은 불변, 교차-세션 누수만 제거.

**AC matrix (M6c-1 subset)**

| AC/REQ | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| REQ-MVP-014 deny-on-my-own-disconnect fail-safe (Finding 1) | PASS | `uv run pytest -q server/tests/test_web_approval_bridge.py server/tests/test_web_app.py -k "SessionScoped or ConcurrentSessions"` | 4 passed |
| Finding 1 — 교차-세션 pending 승인 비유출 (신규 불변) | PASS | 위와 동일 (`test_unbinding_one_session_does_not_deny_anothers_pending_request`, `test_disconnect_does_not_deny_another_sessions_pending_approval`) | 두 테스트 모두 PASS; git stash로 되돌린 pre-fix 코드에서 RED 확인 후 복원 |
| REQ-MVP-011/029 게이트 단일 관문 불변 (Finding 2, 회귀 없음) | PASS | `uv run pytest -q server/tests/test_safety_gate.py` | 39 passed (37 baseline + 2 신규) |
| Finding 2 — 교차-세션 clearance 비침해 (신규 불변) | PASS | `-k TestConcurrentSessionClearanceIsolation` | 2 passed (순차-컨텍스트 + `threading.Barrier` 동시성 테스트) |
| Finding 3 — heartbeat 루프 예외 생존 (신규 불변, `_backup_loop`와 대칭) | PASS | `-k test_heartbeat_loop_survives_heartbeat_failures` | 1 passed; RED 확인(가드 없이 `asyncio.to_thread` 예외가 lifespan까지 전파되어 앱 크래시) 후 GREEN |

**TDD evidence (RED → GREEN, 발견별)**

- **Finding 1** (`server/web/approval_bridge.py:88` + `server/web/session.py:177-195` + M7 `review_channel` 동일 패턴): `ApprovalChannel.bind()`가 스칼라 `_notify` 단일 슬롯이고 `ChatSession.close()`→`unbind()`→`deny_all_pending()`이 공유 `_pending` dict 전체를 무조건 강제 거부 — B의 연결 종료가 A의 무관한 대기 승인을 조용히 자동 거부. 새 `server/safety/session_context.py`(contextvars 기반 세션 키 seam) 도입 — `ChatSession.run_instruction`이 턴 전체에 걸쳐 자신의 세션 키를 ambient 컨텍스트로 바인딩(동일 스레드 내 동기 호출 체인이므로 스레드 홉 없음). `bind`/`unbind`는 명시적 `session_key` 파라미터(기본값 `DEFAULT_SESSION_KEY` — 세션 미개입 직접 호출 하위호환), `request_approval`은 ambient 키로 notify + pending을 세션별로 스코프. RED: `channel.bind(notify, session_key=...)` → `TypeError: unexpected keyword argument 'session_key'`(로그: pytest 출력, 커밋 `32ff551` 이전 상태로 `git stash`하여 재확인). GREEN: `32ff551`.
- **Finding 2** (`server/safety/gate.py:212,286` — `_clearances`): 인스턴스 레벨 단일 `Counter`가 모든 동시 `ChatSession`에 공유되어(같은 `deps.gate`) 세션 B의 `screen()` 호출이 세션 A의 이미 승인된 미실행 번들 clearance를 무단 무효화 가능. `_clearances`를 `dict[SessionKey, Counter[str]]`로 세션-키잉 + `threading.Lock`으로 mutate/read 시퀀스 가드(`screen()` 진입부 리셋, cleared 경로 write, `_execute_cleared()`의 read-decrement 전부 락 내부). 세션 자신의 screen→execute 흐름은 완전 동일 유지. RED: `test_a_sessions_screen_does_not_invalidate_anothers_clearance`, `test_concurrent_sessions_both_execute_their_own_cleared_bundle` 둘 다 pre-fix에서 `AssertionError: assert False is True`(세션 B의 screen이 A의 clearance를 무효화). GREEN: `238a6ce`.
- **Finding 3** (`server/web/app.py:77` `_heartbeat_loop`): 형제 `_backup_loop`와 달리 `gate.heartbeat()` 호출에 예외 가드 부재 — 미처리 예외가 lifespan task까지 전파되어 콘솔-오프라인 감지가 조용히 죽음. `_backup_loop`와 정확히 동일한 try/except + `audit.record({"event": "heartbeat_tick_failed", ...})` 패턴 적용. RED: `FakeConsole.ping_error` 강제 → `asyncio.to_thread(deps.gate.heartbeat)`에서 `RuntimeError`가 lifespan까지 전파(pytest traceback 확인). GREEN: `d889fc3`.

**Quality gates**

- `uv run pytest -q` → **710 passed** (702 baseline + 8 신규: Finding 1 채널-단위 3 + WS-통합 2, Finding 2 순차/동시성 2, Finding 3 heartbeat 1)
- `uv run pytest --cov=server --cov-report=term-missing -q` → TOTAL 98% (baseline 유지); 터치 파일별 — `server/safety/gate.py` 99%(신규 미커버 0건, 기존 갭 `532-534`만 잔존), `server/safety/session_context.py` 100%, `server/web/approval_bridge.py` 100%, `server/web/session.py` 99%(기존 갭 `136`만), `server/web/app.py` 98%(기존 갭 `88,95,156`만 — 전부 pre-existing, 본 변경으로 신규 미커버 라인 0건)
- `uv run ruff check server` → clean (SIM117 nested-with 2건 발견 즉시 수정 후 재확인 clean)

**Commits** (no push — no origin remote)

- `32ff551` fix(SPEC-COPILOT-MVP-001): M6c-1 approval channel per-session isolation (Finding 1, TDD)
- `238a6ce` fix(SPEC-COPILOT-MVP-001): M6c-1 safety gate clearance per-session isolation (Finding 2, TDD)
- `d889fc3` fix(SPEC-COPILOT-MVP-001): M6c-1 heartbeat loop exception guard (Finding 3, TDD)

**잔여**: 이번 배치는 3건(CRITICAL 1 + HIGH 2)만 다룸 — 102-서브에이전트 리뷰의 잔여 MEDIUM/LOW 지적은 후속 M6c-N 배치로 이연(범위 분리, scope discipline). `server/measurement/`, `server/llm/`, `server/orchestrator/runner.py`는 본 배치 범위 밖(타 배치 커버) — 미변경.

### M6c-2 — safety-gate bypass-path fixes (pre-sync critical/high triage, batch 2 of 4) (2026-07-17, manager-develop cycle_type=tdd)

**Scope**: 동일 102-서브에이전트 교차검증 리뷰가 M6b-1r2/M6c-1 반영 후 발견한 HIGH 3건 — 안전 게이트 우회 경로(bypass-path) 계열. Finding 1/2는 "위험 분류/스캔이 명령 SYNTAX만 보고 CONTENT를 보지 않는" 동일 패턴, Finding 3는 "다른 모든 콘솔 송신 경로는 라이브 잠금+헬스 체크를 강제하지만 backup 경로만 예외"인 패턴.

**AC matrix (M6c-2 subset)**

| AC/REQ | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| REQ-MVP-013 quoted `Property 'Command'/'Cmd'` 재귀 분류 (Finding 1) | PASS | `uv run pytest -q server/tests/test_safety_classify.py -k TestQuotedPropertyCommandContent` | 5 passed |
| Finding 1 — AC-MVP-004 FN 코퍼스 회귀 없음 | PASS | `uv run pytest -q server/tests/test_safety_classify.py server/tests/test_safety_gate.py server/tests/test_deploy_scan.py` | 93 passed |
| REQ-MVP-027 멀티라인 `Cmd()` 스캔 (Finding 2) | PASS | `uv run pytest -q server/tests/test_deploy_scan.py -k multiline` | 2 passed |
| AC-MVP-007a 백업 경로 라이브 잠금 0건 송신 (Finding 3) | PASS | `uv run pytest -q server/tests/test_safety_gate.py -k "backup_action_blocked or lock_skipped_backup"` | 3 passed |

**TDD evidence (RED → GREEN, 발견별)**

- **Finding 1** (`server/safety/classify.py:55` — quoted-property content never risk-classified): M6b-1r2 룰북이 가르친 매크로 저작 레시피(`Set Macro <pool>.<line> Property 'Command'/'Cmd' '<text>'`)는 명령 LINE을 quoted property value로 저장하는데, `classify_command`는 outer assignment의 verb/unquoted args만 보고 quoted value 내용은 절대 검사하지 않았음 — `Set Macro 1.1 Property "Command" "Delete Everything"`이 승인 없이 "safe"로 통과. 신규 `_quoted_property_command_value()`(narrow shape-specific: `Property` 키워드 + quoted `Command`/`Cmd` 이름 + quoted value)로 감지 시 quoted value를 `classify_command`에 재귀 호출 — outer verb-agnostic(Set/Assign 무관). 기존 "quoted 토큰은 절대 키워드 매치 안 함"(오브젝트 이름 FP 방지) 규칙은 그대로 보존(`Label ... 'Delete old look'` 등 기존 테스트 무회귀). RED: `git stash push -- server/safety/classify.py` → `test_destructive_content_in_command_property_is_blacklisted` 등 3건 `AssertionError: assert 'safe' == 'blacklisted'`(pytest 출력 확인). GREEN: `313ad8f`.
- **Finding 2** (`server/deploy/scan.py:167` — 멀티라인 `Cmd()` 스캔 회피): `Cmd(` → 인자 사이, 그리고 trailing `..` concatenation tail 체크 둘 다 space/tab만 skip — `Cmd(\n"Delete Everything"\n)` 같은 개행-포맷 호출이나 개행을 낀 concatenation이 분류/`dynamic_calls` 신호 모두 회피. `_LUA_WHITESPACE = " \t\n\r\v\f"`(Lua 자체 whitespace 집합)로 두 지점 모두 교체. RED: `git stash push -- server/deploy/scan.py` → 신규 2 테스트 `AssertionError`(멀티라인 호출이 `destructive=False`로 미탐지, concatenation이 `dynamic_calls=()`로 미탐지 — pytest 출력 확인). GREEN: `a2c953b`.
- **Finding 3** (`server/safety/gate.py:189` — `SaveShow` backup이 라이브 잠금+헬스 체크 우회): `_execute_cleared`/`deploy_plugin_source`는 매 송신 직전 `lock.is_active`/`monitor.executions_blocked`를 재검사하지만 `make_showfile_backup_action()`의 `action()`은 `self._console.execute(BACKUP_COMMAND)`를 직접 호출 — 잠금 활성 중에도 backup이 콘솔로 송신 가능(AC-MVP-007a "0건" 직접 위반) 또는 오프라인 중에도 송신 가능. `action()` 진입부에 동일한 lock/health 체크 추가, 블록 시 raise(→ `BackupManager._backup()`가 이미 모든 예외를 `BackupError`로 변환하므로 REQ-MVP-034 fail-safe 실행-차단 로직과 자동 합류) — `_last_backup_at`도 예외 시 갱신 안 됨(기존 `_backup()` 구현)이라 스킵된 backup이 조용히 성공으로 취급되지 않음(REQ-MVP-034 downstream 검토 완료, 별도 상태 필드 불요). RED: `git stash push -- server/safety/gate.py` → 신규 3 테스트 `AssertionError`(action이 raise 안 하고 조용히 통과 — pytest 출력 확인). GREEN: `7fbfd91`.

**Quality gates**

- `uv run pytest -q` → **720 passed** (710 baseline + 10 신규: Finding 1 quoted-property 5건, Finding 2 멀티라인 2건, Finding 3 backup-bypass 3건)
- `uv run pytest --cov=server --cov-report=term-missing -q` → TOTAL **98%** (baseline 유지); 터치 파일별 — `server/safety/classify.py` 96%(기존 미커버 라인만 잔존, 신규 미커버 0건), `server/deploy/scan.py` 87%(기존 미커버 라인만 잔존, 신규 미커버 0건), `server/safety/gate.py` 99%(신규 미커버 0건 — 잔존 3라인 `559-561`은 본 배치 범위 밖)
- `uv run ruff check server` → clean

**Commits** (no push — no origin remote)

- `313ad8f` fix(SPEC-COPILOT-MVP-001): M6c-2 quoted Command-property content bypass (TDD)
- `a2c953b` fix(SPEC-COPILOT-MVP-001): M6c-2 multi-line-formatted Cmd() scan evasion (TDD)
- `7fbfd91` fix(SPEC-COPILOT-MVP-001): M6c-2 SaveShow backup live-lock/health bypass (TDD)

**잔여**: 이번 배치는 3건(HIGH 3)만 다룸 — 102-서브에이전트 리뷰의 잔여 지적은 후속 M6c-3/M6c-4 배치로 이연(범위 분리, scope discipline). `server/web/`, `server/llm/`, `server/orchestrator/runner.py`, `console/lua/`, `ui/`는 본 배치 범위 밖(타 배치 커버) — 미변경.

### M6c-3 — LLM/orchestrator correctness fixes (pre-sync critical/high triage, batch 3 of 4) (2026-07-17, manager-develop cycle_type=tdd)

**Scope**: 동일 102-서브에이전트 교차검증 리뷰가 M6b-1r2/M6c-1/M6c-2 반영 후 발견한 HIGH 3건 — LLM 어댑터/오케스트레이터 정확성 계열. Finding 1/2는 Gemini 어댑터 계층(응답 파싱·에러 분류), Finding 3는 오케스트레이터 재시도 회계.

**AC matrix (M6c-3 subset)**

| AC/REQ | Status | Verification command | Actual output (tail) |
|---|---|---|---|
| Finding 1 — 정상 STOP 무회귀 + 비정상 finish_reason 5종 에러화 | PASS | `uv run pytest -q server/tests/test_gemini_adapter.py -k TestFinishReasonInspection` | 7 passed |
| Finding 2 — httpx 연결성 예외 분류 (builtin 무회귀 포함) | PASS | `uv run pytest -q server/tests/test_gemini_adapter.py -k TestConnectivityErrorClassification` | 4 passed |
| AC-MVP-005 재시도 상한 ≤3 무회귀 (Finding 3) | PASS | `uv run pytest -q server/tests/test_runner_self_correction.py -k "TestRetryCap or TestWithinTurnRetryAccounting"` | 5 passed |

**TDD evidence (RED → GREEN, 발견별)**

- **Finding 1** (`server/llm/gemini_adapter.py:185` — `finish_reason` never inspected): `_parse_response`는 `Candidate.finish_reason`을 전혀 읽지 않아 SAFETY/RECITATION 차단이나 `MAX_TOKENS`로 잘린 function call이 빈 `parts` 리스트와 함께 조용히 "성공한 빈 턴"으로 파싱됨 — 모델이 응답을 거부/차단당한 실패가 은폐됨. 신규 `_OK_FINISH_REASONS = {"STOP", "FINISH_REASON_UNSPECIFIED"}`(미지정·attribute 부재는 구버전 mock 하위호환을 위해 통과) 도입, 그 외 명시적 finish_reason은 기존 `malformed_response` 에러 채널(빈 candidates 처리와 동일 kind)로 표면화. RED: `git stash push -- server/llm/gemini_adapter.py server/llm/errors.py server/orchestrator/runner.py` → 신규 `TestFinishReasonInspection` 파라미터화 5건(SAFETY/RECITATION/MAX_TOKENS/MALFORMED_FUNCTION_CALL/PROHIBITED_CONTENT) `AssertionError`(ProviderError 미발생 — pytest 출력 확인). GREEN: `4f78e1d`.
- **Finding 2** (`server/llm/errors.py:79` — connectivity-error misclassification): `normalize_gemini_error`의 연결성 체크가 Python 빌트인 `ConnectionError`/`TimeoutError`만 검사하지만 `google-genai` SDK(httpx 기반)는 실제 네트워크 장애 시 `httpx.ConnectError`/`httpx.TimeoutException`을 발생시킴 — 이는 빌트인의 서브클래스가 아니므로(`isinstance` 확인: `uv run python3 -c "import httpx; print(httpx.ConnectError.__mro__)"` — Exception 직계, builtin 미상속) 실제 연결 장애가 `kind="unknown", retryable=False`로 오분류되어 재시도되지 않음. `connectivity_errors` 튜플에 `httpx.ConnectError`/`httpx.TimeoutException`을 빌트인과 **나란히**(대체 아님) 추가. RED: 동일 stash → 신규 `TestConnectivityErrorClassification` 4건 중 httpx 2건만 `AssertionError: assert 'unknown' == 'connection'`(빌트인 2건은 기존 코드에서도 이미 통과 — 회귀 없음 확인). GREEN: `4f78e1d`.
- **Finding 3** (`server/orchestrator/runner.py:132` — retry accounting over-counts within-turn multi-tool-calls): 재시도 회계가 per-call dispatch 루프 **내부**에서 `last_run_failed` 플래그를 검사·증분했는데, 이 플래그는 같은 턴 안에서 **이전 호출의 실패로 인해 방금 True로 설정**될 수 있음 — 한 턴에 `run_commands`/`deploy_plugin` 호출이 2개 이상이고 첫 호출이 실패하면, 모델 피드백 왕복이 전혀 없었던 같은 턴의 두 번째 호출이 "교정 라운드"로 오카운트되어 AC-MVP-005의 ≤3 상한을 조기 소진할 위험. 수정: 재시도 증분 결정을 per-call 루프 **이전**, 턴 경계에서 **1회만** 수행 — `last_run_failed`는 오직 **이전 턴 종료 시점**의 값만 참조하고 이번 턴의 dispatch 루프 도중에는 절대 재평가하지 않음(`has_retryable_call` 사전 계산 + 루프 진입 전 단일 증분 + 즉시 리셋). RED: 동일 stash → 신규 `TestWithinTurnRetryAccounting.test_first_call_failure_does_not_charge_the_second_call_in_the_same_turn` `AssertionError: assert 1 == 0`(2-호출 턴에서 첫 호출만 실패했는데 재시도 1회로 오카운트 — pytest 출력 확인); 나머지 2건(2-성공-호출 0회, 교정 턴 2-호출 1회)은 기존 코드에서도 이미 통과(회귀 검증용). 기존 `TestRetryCap` 2건(정확히 3회 소진, 성공 시 카운트 정지)은 신규 회계 하에서도 byte-for-byte 동일 결과 확인. GREEN: `a8bc341`.

**Quality gates**

- `uv run pytest -q` → **734 passed** (720 baseline + 14 신규: Finding 1 파싱 7건, Finding 2 연결성 4건, Finding 3 재시도 회계 3건)
- `uv run pytest --cov=server --cov-report=term-missing -q` → TOTAL **98%** (baseline 유지); 터치 파일별 — `server/llm/gemini_adapter.py` 91%(기존 미커버 라인만 잔존 — `_ensure_cache` 예외분기 96-100, `_to_contents` 방어분기 169-179, 재-raise 283; 신규 미커버 0건), `server/llm/errors.py` 98%(기존 미커버 라인 `28`만 잔존 — `ValueError` 방어분기, 신규 미커버 0건), `server/orchestrator/runner.py` 100%(신규 미커버 0건)
- `uv run ruff check server` → clean

**Commits** (no push — no origin remote)

- `4f78e1d` fix(SPEC-COPILOT-MVP-001): M6c-3 Gemini finish_reason inspection + httpx connectivity misclassification (TDD)
- `a8bc341` fix(SPEC-COPILOT-MVP-001): M6c-3 self-correction retry accounting over-counts within-turn multi-tool-calls (TDD)

**잔여**: 이번 배치는 3건(HIGH 3)만 다룸 — 102-서브에이전트 리뷰의 잔여 지적은 후속 M6c-4 배치로 이연(범위 분리, scope discipline). `server/web/`, `server/safety/`, `server/deploy/`, `console/lua/`, `ui/`, `server/measurement/`는 본 배치 범위 밖(타 배치 커버) — 미변경.

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
