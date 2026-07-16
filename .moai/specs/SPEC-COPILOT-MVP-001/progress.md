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
