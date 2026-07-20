# SPEC-COPILOT-DEPLOY-001 — progress

## §E.1 Plan-phase Audit-Ready Signal

plan_status: audit-ready
plan_complete_at: 2026-07-20

Plan-phase 산출물: **코어 3종**(spec.md / plan.md / acceptance.md) + progress.md 생성 완료, `status: draft` (v0.1.0). Tier L 분류(§A.0) — 정식 5종의 design.md/research.md 추가 작성 여부는 plan.md §F #1 오픈 결정.

범위 요약: 기능이 검증된 MVP(SPEC-COPILOT-MVP-001)에 배포 셸을 씌우는 SPEC. 합의된 2단계 — 패키징 Stage 1(PyInstaller onefile 로컬 런처) → Stage 2(Tauri v2 데스크톱 앱, Electron은 대안 문서화). 크로스컷 요구: 인앱 설정 UI + OS 자격 증명 저장, responder provisioning, health UI, 코드 서명·공증, 자동 업데이트, 오류 UX. 핵심 HARD 제약: onPC와 동일 머신/LAN 로컬 구동 — 클라우드/SaaS out of scope.

요구/AC: REQ-DEPLOY-001~026 (10개 그룹 B.1~B.10) → AC-DEPLOY-001~015 (고아 REQ 0건). 마일스톤 M1~M10 (Stage 1: M1~M6, Stage 2: M7~M9, 통합: M10).

오픈 결정: plan.md §F [NEEDS CLARIFICATION] 8건 — Implementation Kickoff Approval 전 해소 대상 (Tier 산출물 / 설정 포맷 / keyring / 온보딩 / sidecar 통신 / 업데이트 호스팅 / 서명 인증서 / onefile-vs-onedir).

선행 의존: SPEC-COPILOT-MVP-001 (`depends_on`).

### Plan-audit fold-in (v0.2.0, 2026-07-20)

plan-audit 판정 PASS-WITH-DEBT(~0.79, 확정 blocker 0)를 SSOT에 반영 — run-phase가 교정된 표준으로 구현하도록 debt를 접음. `status: draft` 유지, version 0.1.0 → 0.2.0.

- **spec.md**: AC-014 ③ 근거 REQ 정합; REQ-004 "(또는 동일 LAN)" 삭제 + [Unwanted]/[Ubiquitous](REQ-004a) 분리(TRACE-1/GEARS-3); REQ-006a([Unwanted] 자격 저장소 미가용/잠금/거부 — GEARS-1/TRACE-3)·REQ-011a(앱 발행 Import Plugin 게이트 경유+감사로그 — SAFETY-3)·REQ-027([Event-driven] updater 재시작 안전상태 보존 — SAFETY-4) 신설; REQ-015 검증 가능 서명 행위로 재작성·SmartScreen를 §C로 이동(GEARS-2/FEAS-7); §A 사전 확정 결정 + §C 서명 사실 반영.
- **plan.md**: §A.0/1/2/3/6/7 RESOLVED, §A.4/5 Stage-2 DEFERRED(§A.4에 FEAS-9 보안축 추가); §C M2 frozen 스모크 검증(FEAS-2)·M6 collect/hidden-import·SPIKE 조기 서명 스파이크(FEAS-4)·M7 process-tree(FEAS-5)·M9 HIGH-RISK 재분류+entitlements/stapling(FEAS-3); §D 리스크(keyring 재작성·크래시 env-scrub DECIDE-M6·교차언어 OSC SAFETY-2); §F 6 resolved + 2 Stage-2-deferred, Stage-1-open 0건.
- **acceptance.md**: AC-014 ③ 구체화(allowlist+Python·Rust 스캔+wire-level+fail-closed — SAFETY-1/2); AC-016(REQ-006a)·AC-017(SAFETY-3)·AC-018(REQ-027) 신설; AC-004(크래시덤프+저장소미가용 참조)·AC-009(universal2 .app/.dmg+stapling FEAS-6)·AC-011(서명검증-실패 자동 단위테스트 TRACE-2)·AC-015(process-tree FEAS-5) 강화; responder_degraded GWT 시나리오(TRACE-4); REQ→AC 매트릭스 고아 0건; DoD 갱신.

**미반영/이연 항목**: DECIDE-M4(릴리스 시퀀싱)·M5(버전 SoT)·M3(Windows 인스톨러 형식)·M8(아이콘)·M10(EULA)·GEARS-4/7(경미 복합 분리)·FEAS-10(REQ-021 "재현 가능" 문구)·SAFETY-5(라이브 포트 편집)는 Stage-2 kickoff 또는 run-phase 구현 재량으로 이연 — 확정 blocker 아님. F5/F6는 Stage-2-deferred로 명시(본 프롬프트 지시대로 full-spec 금지).

## §E.2 Run-phase Evidence

### M1 — 설정·config 저장 계층 (2026-07-20, cycle_type=tdd)

신규 모듈 `server/deploy/settings.py` (사용자 설정 저장 계층) + `server/tests/test_deploy_settings.py` (43 tests). OS별 표준 사용자 config 경로 해석(stdlib, 신규 의존성 0), 비민감 설정(OSC 콘솔/수신 포트·웹 host/port·플러그인 임포트 디렉터리·활성 프로바이더)만 TOML로 저장/로드, 자격증명 유사 키 거부(`server.llm.config._reject_credentials` 재사용 — 단일 SSOT, 드리프트 0), precedence 오버레이(built-in < seed provider.toml < 사용자 파일 < 명시 override). 통합 seam = `resolve_effective_settings()` (serve.py는 미변경 — M3/M6 배선). 기본 포트값은 MVP serve.py 값 재사용(DECIDE-M9). `server/llm/config.py` 및 그 자격증명 거부는 PRESERVE.

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-005 (비민감 설정 사용자 config 경로 저장 + 자격증명 미포함) | PASS | `.venv/bin/python -m pytest server/tests/test_deploy_settings.py -q --cov=server.deploy.settings` | `43 passed`; `server/deploy/settings.py 141 stmts, 97% cover` (미커버 = save 실패 시 temp-file 정리 방어 분기) |
| — 저장/로드 왕복 지속 (Windows 백슬래시 경로 포함) | PASS | `TestSaveLoadRoundtrip` (4 tests) | `4 passed` |
| — 자격증명 유사 키 거부(top-level + 중첩 테이블, resolve 경로 포함) | PASS | `TestCredentialRejection` (9 params/tests) | `9 passed` — api_key/token/secret/password/credential/apikey 모두 raise |
| — precedence(default<seed<user<override, None override 무시) | PASS | `TestPrecedence` (10 tests) | `10 passed` |
| — 타입·범위 검증(포트 1-65535, bool 거부, 빈 host, 미지원 provider) | PASS | `TestValidation` (8 tests) | `8 passed` |
| — OS별 경로 해석(macOS/Windows/Linux + XDG) | PASS | `TestUserConfigPath` (7 tests) | `7 passed` |

**Regression**: full suite `.venv/bin/python -m pytest server/tests/ -q` → `824 passed` (baseline 781 + 신규 43, 회귀 0). **Lint**: `ruff check server/` → 2 pre-existing baseline (safety/console.py E501) only, NEW 0. **Format**: `ruff format --check` 신규 2파일 clean.

**@MX tags added**: `server/deploy/settings.py` `load_user_settings` 위 `@MX:ANCHOR` (자격증명 거부 경계, `@MX:REASON` + `@MX:SPEC` 포함) 1건; `resolve_effective_settings` 내 `@MX:NOTE` (precedence 순서 load-bearing) 1건.

### M2 — 보안 키 저장 어댑터 (2026-07-20, cycle_type=tdd)

신규 모듈 `server/deploy/keystore.py` + `server/tests/test_deploy_keystore.py` (38 tests, 100% cover). OS 자격 증명 저장소(keyring, Python 직접) 저장/조회/삭제 어댑터를 단일 안정 서비스명(`SERVICE_NAME = "com.grandma3copilot.app"` — 번들 식별자, ACL/identity 앵커, churn 금지)으로 구현. 키 → 백엔드 프로세스 env 주입(`inject_key_for_provider`/`inject_active_provider_key` — M1 `resolve_effective_settings` active-provider seam 통합), gemini는 `GEMINI_API_KEY`+`GOOGLE_API_KEY` 별칭 동시 주입·anthropic은 `ANTHROPIC_API_KEY`. **저장소 미가용/잠금/거부 시 명시적 `KeystoreUnavailableError` + 세션 한정(in-memory `SessionKeyStore`) 폴백** — 평문 디스크 폴백 0(REQ-006a). **env-scrub 가드 `scrub_environ`**(DECIDE-M6): 크래시/진단 덤프에 env 직렬화 시 자격증명 유사 var 이름을 redact. `keyring>=25,<26` 추가·핀(F3 승인, macOS Keychain + Windows Credential Manager 단일 인터페이스, REQ-DEPLOY-021 재현 빌드 → uv.lock 락). 테스트는 실제 Keychain 미접촉(hand-rolled in-memory/broken 백엔드 + teardown 복원). `server/llm/config.py` env-only 주입 + 자격증명 거부는 PRESERVE.

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-004 (키는 자격 증명 저장소에만; 앱이 쓰는 모든 파일에 키 문자열 0건 + env-scrub + config 로더 credential 거부 유지) | PASS | `.venv/bin/python -m pytest server/tests/test_deploy_keystore.py::TestNoPlaintextLeak server/tests/test_deploy_keystore.py::TestEnvScrub server/tests/test_deploy_keystore.py::TestCredentialRejectionPreserved -q` | `13 passed` |
| AC-DEPLOY-016 (저장소 미가용/잠금/거부 → 평문 0 + 세션 한정 입력 동작 + 명시적 오류) | PASS | `.venv/bin/python -m pytest server/tests/test_deploy_keystore.py::TestStoreUnavailable server/tests/test_deploy_keystore.py::TestNoPlaintextLeak::test_broken_store_session_fallback_leaves_no_disk_plaintext -q` | `9 passed` |
| — 신규 모듈 커버리지 ≥85% | PASS | `pytest test_deploy_keystore.py --cov=server.deploy.keystore` | `88 stmts, 100% cover` |

**Regression**: full suite `.venv/bin/python -m pytest server/tests/ -q` → `862 passed` (baseline 824 + 신규 38, 회귀 0). **Lint**: `ruff check server/` → 2 pre-existing baseline (safety/console.py:221,258 E501) only, NEW 0. **Format**: 신규 2파일 clean. **Boundary**: `grep AskUserQuestion|mcp__askuser` 신규 파일 → 0.

**@MX tags added**: `server/deploy/keystore.py` `inject_key_for_provider` 위 `@MX:ANCHOR`(credential→process-env 경계) 1건 + `scrub_environ` 위 `@MX:ANCHOR`(env-scrub 경계, DECIDE-M6) 1건 (각 `@MX:REASON`+`@MX:SPEC` 포함); 모듈 docstring에 `@MX:NOTE`급 FEAS-2 M6 요건 기록.

**FEAS-2 (M6 이연·재검증)**: `keyring`은 `importlib.metadata` entry-point로 OS 백엔드를 선택 → PyInstaller frozen 번들이 strip 시 null 백엔드 조용한 폴백. M2는 dev venv라 미영향이나, **M6 onedir 번들 스펙에 `--collect-all keyring` + `keyring.backends.macOS`/`keyring.backends.Windows` hidden-imports(+ Windows pywin32) 필수**, 그리고 **M2 keychain 왕복을 frozen onedir 스모크 빌드 안에서 재검증**(AC 증거는 M6). 모듈 docstring에 기록됨.

### M3 — 설정 UI(프론트엔드) + 백엔드 배선 (2026-07-20, cycle_type=tdd)

신규 백엔드 라우터 `server/web/settings_api.py` (`SettingsDeps` + `build_settings_router`) — `create_app`에 `WebDeps.settings` 옵션 필드로 배선(정적 마운트 `/` 앞에 등록해 `/api/*` 미섀도). 4개 엔드포인트: `GET /api/settings`(M1 `resolve_effective_settings` 비민감 설정 + 프로바이더별 key-set 불리언 — **키 값 미반환**), `POST /api/settings`(M1 `save_user_settings` 검증·지속 — credential-like 키는 `_RECOGNISED_KEYS` 밖이라 미기록, 거부 정책 보존), `POST /api/keys`(M2 `set_api_key` write-only + `inject_key_for_provider` env 주입 REQ-007; `KeystoreUnavailableError`→명시 503 + 세션 폴백 제안 REQ-006a, 평문-디스크 폴백 0), `DELETE /api/keys/{provider}`(M2 `delete_api_key`). **OSC 송신 표면 0**(M1/M2 seam만 import; 소스 스캔 테스트로 강제 — AC-014 ③/SAFETY-1). 프론트엔드(`ui/src`, no-DOM 순수함수 테스트 관례): `settings.ts`(parse/build/validate/onboarding 순수함수) + `SettingsPanel.tsx`(마스킹 write-only 키 입력·OSC 포트·임포트 디렉터리·프로바이더 선택·저장소 미가용 시 세션 전용 재시도) + `OnboardingBanner.tsx`(비침습 배너, 강제 마법사 아님) + `App.tsx` 설정 토글 배선 + `styles.css`. `server/llm/config.py` env-only 주입·자격증명 거부, `/ws` 프로토콜, 안전 게이트는 PRESERVE.

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-003 (터미널 없이 키/포트/임포트 디렉터리 읽기·저장 → 재기동 후 비민감 설정 지속 + 키는 자격 증명 저장소에서 조회) | PASS | `.venv/bin/python -m pytest server/tests/test_web_settings_api.py -q --cov=server.web.settings_api` | `20 passed`; `server/web/settings_api.py 69 stmts, 100% cover` |
| — POST 지속 → 새 resolve(=재기동)가 지속값 확인 | PASS | `test_persists_and_survives_reload` | `1 passed` (console_port 8200 / receive_port 9200 / plugin_import_dir 지속) |
| — GET이 키 값 미반환(키 설정됨=true만) | PASS | `test_key_set_status_true_but_value_never_returned` | `1 passed` — 응답 텍스트에 fake 키 문자열 0건 (AC-DEPLOY-004 보호) |
| — credential-like 키 POST body 미지속 (거부 정책 보존) | PASS | `test_credential_key_in_body_is_not_persisted` | `1 passed` — 설정 파일에 `api_key`/키값 0건 |
| — 저장소 미가용 → 명시 503 + 세션 폴백 (REQ-006a) | PASS | `test_keystore_unavailable_returns_explicit_error_with_session_fallback` + `test_session_fallback_works_when_keystore_broken` | `2 passed` — 503 `keystore_unavailable`+`session_fallback`, 세션 경로 env 주입 성공, 디스크 기록 0 |
| — 키→env 주입 (REQ-DEPLOY-007) | PASS | `test_store_in_keystore_and_inject_env` | `1 passed` — `GEMINI_API_KEY`+`GOOGLE_API_KEY` env 주입, 응답에 키 미노출 |
| — create_app 배선(정적 마운트와 공존) | PASS | `test_settings_router_mounted_alongside_static_and_ws` | `1 passed` — `/api/settings` 200 + `/` 정적 200 + `/healthz` ok |
| — 프론트 순수함수(parse/build/validate/onboarding) | PASS | `cd ui && npm test` | `16 passed` (settings.test.ts); 총 `37 passed` (baseline 21 + 16) |

**Regression**: 백엔드 full suite `.venv/bin/python -m pytest server/tests/ -q` → `882 passed` (baseline 862 + 신규 20, 회귀 0). 프론트 `cd ui && npm test` → `37 passed` (baseline 21 + 16). **Lint/Build**: `ruff check server/` → 2 pre-existing baseline (safety/console.py:221,258 E501) only, NEW 0; 신규/수정 파일 `ruff format --check` clean; `cd ui && npm run build`(tsc typecheck + vite) → clean(41 modules). **Boundary(E6')**: `grep AskUserQuestion|mcp__askuser` 신규 백엔드 파일 → 0; **OSC 송신 표면 스캔** `settings_api.py`(`socket.socket`/`UdpSocket`/`pythonosc`/`SafetyGate`/`send_to_console`/`server.safety`) → 0 + `test_settings_api_module_has_no_console_send_path` CI 가드. **dist**: `ui/dist` gitignored → 미커밋(M6 재빌드).

**@MX tags added**: `server/web/settings_api.py` `build_settings_router` 위 `@MX:ANCHOR`(설정/키 REST 표면 = deploy-shell 유일 config/credential 진입점, `@MX:REASON` AC-014 ③ no-OSC-send 불변식 + `@MX:SPEC`) 1건 + `_provider_key_status` 위 `@MX:NOTE`(키는 boolean 도출용 transient read, 값 미반환 — AC-004) 1건.

**커밋**: `e70c365`(M3 구현 — 백엔드 라우터 + 프론트 순수함수/컴포넌트/App 배선, 9파일), `6ce9c7e`(M3 @MX 태그). `feat/app-deploy-file-import` 직접 커밋(원격 없음 — push/PR 없음).

### M4 — CopilotResponder provisioning (2026-07-20, cycle_type=tdd)

신규 백엔드 모듈 `server/deploy/provisioning.py`(파일시스템 전용 provisioning) + `server/web/provision_api.py`(`ProvisionDeps` + `build_provision_router`) — `create_app`에 `WebDeps.provision` 옵션 필드로 배선(M3 settings 라우터 패턴 미러; 정적 마운트 앞 등록). provisioning 모듈: `bundled_responder_dir()`(dev = `<repo>/console/lua`, frozen = `sys._MEIPASS/console/lua` — **M6 번들 스펙 obligation: `--add-data 'console/lua:console/lua'`** 모듈 docstring에 기록), `install_responder(import_dir)`(`copilot_responder.xml`+`copilot_responder.lua` 복사, 디렉터리 생성, 멱등 재설치), `responder_status()`, `responder_guide(receive_port)`(onPC 로드 4단계 + OSC 출력 포트 설정 안내 — 한국어). 2개 엔드포인트: `GET /api/provision/responder`(설치 상태 + 가이드), `POST /api/provision/responder`(M1 `resolve_effective_settings`에서 `plugin_import_dir`+`receive_port` 해석 → 번들 복사 → 가이드 반환; 실패 시 인간 친화적 한국어 500). **OSC 송신 표면 0**(M1 settings seam + provisioning 모듈만 import; 소스 스캔 CI 가드 2건 — AC-014 ③/SAFETY-1). 프론트엔드(`ui/src`, no-DOM 순수함수 관례): `provision.ts`(parse/status/install-summary 순수함수) + `ResponderGuide.tsx`(설치 버튼 + 상태 + onPC 로드/OSC 출력 포트 안내 — `SettingsPanel`에 섹션으로 배선) + `styles.css`(`.responder-steps`). **AC-017 안전 회귀**: 신규 `test_responder_import_gate.py` — 실제 `ConsoleLink`(file+Import) + in-process recording console로 앱 발행 `Import Plugin`이 단일 게이트(`deploy_plugin_source`) 경유 + 감사 로그 1:1 + 라이브 잠금 시 wire 송신 0건 증명. `pipeline.py`/`pack.py`/안전 게이트/`console.py`는 PRESERVE(테스트만 추가).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-006 (responder 플러그인 번들 포함 + 임포트 디렉터리 설치, 임시 디렉터리 대상) | PASS | `.venv/bin/python -m pytest server/tests/test_deploy_provisioning.py -q` | `12 passed` — 번들 dir에 `.xml`+`.lua` 존재 assert + temp import dir 복사(바이트 verbatim 일치) |
| — frozen 번들 경로가 `sys._MEIPASS/console/lua`로 해석 (FEAS-1) | PASS | `test_frozen_bundle_dir_resolves_under_meipass` | `1 passed` — `_MEIPASS` monkeypatch → `/frozen/app/console/lua` |
| AC-DEPLOY-007 (가이드 UI가 onPC 로드 + OSC 출력 포트 설정 안내 표시) | PASS | `test_guide_carries_the_receive_port_and_onpc_load_steps` + `cd ui && npm test`(provision.test.ts) | `1 passed`(백엔드 가이드 steps에 포트+OSC 포함) + `12 passed`(프론트 순수함수) |
| — API가 설정된 receive_port를 가이드에 반영 | PASS | `.venv/bin/python -m pytest server/tests/test_web_provision_api.py -q` | `7 passed` — GET/POST 설치·상태·create_app 배선·설치실패 500 |
| AC-DEPLOY-017 (앱 발행 Import Plugin 게이트 경유 + 감사 로그 1:1, SAFETY-3) | PASS | `.venv/bin/python -m pytest server/tests/test_responder_import_gate.py -q` | `3 passed` — ① Import Plugin 1건 wire 송신 + `kind="deploy"` 감사 1건(1:1) ② 라이브 잠금 시 wire 0건 + `blocked`(lock) ③ 미게이트 송신 0건 |

**Regression**: 백엔드 full suite `.venv/bin/python -m pytest server/tests/ -q` → `904 passed`(baseline 882 + 신규 22, 회귀 0). 프론트 `cd ui && npm test` → `49 passed`(baseline 37 + 12). **Coverage**: `server.deploy.provisioning` 100% + `server.web.provision_api` 100%(신규 모듈 ≥85% 충족). **Lint/Build**: `ruff check server/` → 2 pre-existing baseline(safety/console.py:221,258 E501)만, NEW 0; `cd ui && npm run build`(tsc+vite) → clean(43 modules). **Boundary(E6')**: `grep AskUserQuestion|mcp__askuser` 신규 파일 → 0; **OSC 송신 표면 스캔** provisioning 모듈 2건 → 0 + `test_provisioning_module_has_no_console_send_path`/`test_provision_api_module_has_no_console_send_path` CI 가드. **dist**: `ui/dist` gitignored → 미커밋(M6 재빌드).

**@MX tags added**: `server/web/provision_api.py` `build_provision_router` 위 `@MX:ANCHOR`(responder-provisioning REST 표면 = deploy-shell 유일 설치 진입점, `@MX:REASON` AC-014 ③ no-OSC-send 불변식 + `@MX:SPEC`) 1건.

**커밋**: `feat(SPEC-COPILOT-DEPLOY-001): M4 …`(본 커밋 — provisioning 모듈 + provision API + 프론트 가이드 + AC-017 게이트 테스트, 12파일). `feat/app-deploy-file-import` 직접 커밋(원격 없음 — push/PR 없음).

### M5 — health 상태 UI + 오류 UX (2026-07-20, cycle_type=tdd)

배포 셸은 MVP HealthMonitor 상태·REQ-MVP-044 오류 스크럽을 **그대로** 표면화한다 — M5는 신규 백엔드 모듈 0(기존 seam PRESERVE), 신규 코드는 **프론트 degraded-state 원인+조치 가이드 레이어** + DEPLOY-scoped 테스트 증거로 한정. 프론트(`ui/src`, no-DOM 순수함수 관례): `protocol.ts`에 `HEALTH_GUIDANCE` 맵 + `healthGuidance(health)` 순수함수 신설 — `console_offline`→"onPC 실행/OSC 입력 확인"(REQ-018), `responder_degraded`→"CopilotResponder onPC 로드 + onPC OSC 출력을 피드백 수신 포트로 설정"(REQ-019, M4 ResponderGuide 개념 재사용, 배너 요약형); `online`·미지 상태→null. `StatusBanner.tsx`는 기존 `healthLabel`(3종 상태 이미 매핑) 유지 + degraded 시 `.banner-guidance` 라인 렌더(스택 트레이스·raw SDK 0). `styles.css` `.banner-guidance` 추가. 키 부재/무효(REQ-020)는 M3 OnboardingBanner(설정 유도) + 기존 `korean_errors`/`error_event` 스크럽으로 **이미 충족** — provider-client 사용 시 auth SDK 오류가 세션의 `_report_error`→`classify_exception`을 경유해 한국어 auth 메시지("API 키 설정을 확인해 주세요")만 표면화, raw 원문은 감사 로그 전용. 신규 `test_deploy_health_ux.py`(DEPLOY-scoped 증거 4 tests): AC-008 전이 사이클(online→console_offline→responder_degraded→회복 online, `session.status_snapshot()` 경유) + AC-012 ③ 키 auth 스크럽(secret-bearing raw_detail → error_event에 secret/Traceback/x-api-key 0건 + 감사 로그에만 raw). **OSC 송신 표면 0**(변경 파일 raw socket/OSC/127.0.0.1 리터럴 0 — grep 확인). `HealthMonitor`/`SafetyGate`/`session.py` `_report_error`/`korean_errors`/status-push 경로는 PRESERVE(테스트+가이드 레이어만 추가).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-008 (health 3종 online/console_offline/responder_degraded 표면화 + 전이 즉시 반영) | PASS | `.venv/bin/python -m pytest server/tests/test_deploy_health_ux.py::TestHealthSurfacingTransitions -q` | `2 passed` — 전이 사이클 online→console_offline(executions_blocked True)→responder_degraded→회복 online(blocked False) 각 단계 `status_snapshot()["health"]` assert + snapshot이 status-push payload(v1 status event)임 확인 |
| — 프론트 라벨 매핑 3종 (healthLabel) | PASS | `cd ui && npm test`(protocol.test.ts healthLabel) | `53 passed` — online/console_offline/responder_degraded 3종 한국어 + 미지 상태 passthrough |
| AC-DEPLOY-012 ①② (console_offline 원인+조치 / responder 로딩·OSC 출력 안내 — 인간 친화 한국어, 스택 트레이스 0) | PASS | `cd ui && npm test`(protocol.test.ts healthGuidance) | `53 passed` — console_offline→onPC/OSC 안내, responder_degraded→CopilotResponder/OSC 안내, online/미지→null, 스택 마커(Traceback/Error/Exception/raise) 0건 |
| AC-DEPLOY-012 ③ (키 부재/무효 → 설정 유도 한국어 + raw SDK 원문 미노출) | PASS | `.venv/bin/python -m pytest server/tests/test_deploy_health_ux.py::TestKeyErrorScrubRoutesToSettings -q` | `2 passed` — auth ProviderError(secret raw_detail) → error_event message=한국어 auth("API 키 설정 확인")·kind=auth, 표면에 secret/Traceback/x-api-key 0건, 감사 로그에만 raw; 카탈로그 auth 메시지 SDK 어휘 0 |

**Regression**: 백엔드 full suite `.venv/bin/python -m pytest server/tests/ -q` → `908 passed`(baseline 904 + 신규 4, 회귀 0). 프론트 `cd ui && npm test` → `53 passed`(baseline 49 + 4). **Coverage**: M5 신규 백엔드 모듈 0(N/A) — 증거 대상 seam `server.safety.monitor` 94% / `server.web.korean_errors` 90%(둘 다 ≥85%). **Lint/Build**: `ruff check server/` → 2 pre-existing baseline(safety/console.py:221,258 E501)만, NEW 0; `cd ui && npm run build`(tsc+vite) → clean(43 modules). **Boundary(E6')**: `grep AskUserQuestion|mcp__askuser` 신규/변경 파일 → 0; **OSC 송신 표면 스캔** 변경 파일(protocol.ts·StatusBanner.tsx·test_deploy_health_ux.py) → 0(no new OSC-send surface — M5는 게이트 밖 UI/status/오류 메시지 전용). **dist**: `ui/dist` gitignored → 미커밋(M6 재빌드).

**@MX tags**: 없음 — `healthGuidance` fan_in <3(StatusBanner 단일 소비), 위험 패턴/고복잡도 없음 → ANCHOR/WARN 기준 미충족(over-tag 회피).

**커밋**: `feat(SPEC-COPILOT-DEPLOY-001): M5 …`(본 커밋 — 프론트 healthGuidance + StatusBanner 가이드 라인 + styles + DEPLOY-scoped health/error-UX 테스트, 5파일). `feat/app-deploy-file-import` 직접 커밋(원격 없음 — push/PR 없음).

### M6 — PyInstaller onedir 런처 (2026-07-20, cycle_type=tdd)

배포 셸 Stage-1 패키징 마일스톤. **Part 1(파이썬 코드, 커밋 `ab9e584`)**: 신규 `server/resources.py` `resource_base()` — frozen(`sys._MEIPASS`)/dev(프로젝트 루트) 단일 리졸버로 M4 provisioning의 `_MEIPASS` 패턴을 일반화, `serve.py`(ui/dist)·`config.py`(provider.toml)·`assembly.py`(rulebook assets)·`provisioning.py`(console/lua) 자산 경로 전부 경유(FEAS-1, research §A.4 — 구 `parents[2]` 두 사이트가 frozen 번들에서 깨지는 문제 해소). 신규 `server/web/launcher.py` — graceful **프로세스-트리** 종료(자식·손자 reap, AC-015 ①)·포트 점유 시 `PortInUseError` 명시 오류+재설정 안내(임의 포트 조용한 폴백 0, AC-015 ②)·`--self-check`(frozen keyring 왕복). `serve.py`에 `--self-check`/`--no-browser` + main 배선. keyring 시작 가드(research §B.3): `PYTHON_KEYRING_BACKEND` env 핀 + fail-closed 가드(백엔드 `__module__`가 `keyring.backends.macOS`가 아니면 기동 거부 — class `__name__`이 아니라 `__module__` 판별, 올바른 macOS 백엔드 class도 이름이 `Keyring`이므로; REQ-006a). **Part 2(패키징+빌드, 커밋 `3a183ea`)**: `packaging/GrandMA3-Copilot.spec`(research §D — `--collect-all keyring` + `keyring.backends.macOS/fail/null/chainer` hidden-imports + `--exclude-module keyrings.alt/cryptfile` + `--collect-submodules uvicorn` + `--collect-all google.genai/anthropic` + `ui/dist`·`console/lua`·`server/rulebook/assets`·`config/provider.toml` `--add-data`; 빌드 중 `server/safety/blacklist.yaml` 번들 누락(`RulesetError`) 발견 → `--add-data` 1줄 인라인 추가, Part 1 로직 미변경) + `entitlements.plist`(allow-jit/allow-unsigned-executable-memory/disable-library-validation) + `sign.sh`(inside-out, `--options runtime --timestamp`, `SIGN_IDENTITY=-` ad-hoc 기본, `notarytool`/`stapler`는 `DEVELOPER_ID` 존재 시에만 — 코드 변경 없이 전환) + `build.sh` + `README.md`. **arm64** 빌드; universal2·Windows x86_64·실제 Developer-ID 공증은 환경-게이트 N/A(spec.md v0.2.1 / AC-DEPLOY-009 이중 게이트).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-001~003 (번들 부팅 → 로컬 백엔드 → UI 서빙) | PASS | frozen launch `"$BIN" --no-browser --port 8799` 후 `GET http://127.0.0.1:8799/` | `responded=True http_status=200`, 번들 `ui/dist/index.html` 서빙 (단일 onedir 프로세스) |
| AC-DEPLOY-004/016 (frozen 번들 keyring 백엔드) | PASS (오케스트레이터 직접 재검증) | `"dist/GrandMA3 Copilot.app/Contents/MacOS/GrandMA3 Copilot" --self-check` (subprocess timeout 60) | `rc 0` — `self-check OK: macOS keyring backend + roundtrip verified` (FEAS-2 핵심: `--collect-all keyring` 성공, null/fail 폴백 0; 팝업 없이 통과) |
| AC-DEPLOY-015 ① (graceful 프로세스-트리 종료) | PASS | launch → `os.killpg(pgid, SIGTERM)` → scan | `exited rc=0`, 잔여 app pid `[]`(프로세스-트리 스캔), web/recv 포트 해제 |
| AC-DEPLOY-015 ② (포트 점유 → 조용한 폴백 금지) | PASS | 포트 8801 점유(listening) → launch `--port 8801` | `rc=2` 명시 오류(한국어 "이미 사용 중"+재설정 안내), 임의 포트 폴백 0, 잔여 pid `[]` |
| AC-DEPLOY-009 (서명 파이프라인 + ad-hoc dry-verify) | PASS(ad-hoc) / N/A(실제 cert) | `codesign --verify --deep --strict "$APP"` + `codesign -d --entitlements -` (오케스트레이터 재검증) | verify-exit 0 "valid on disk", entitlements 3종 임베드, `flags=0x10002(adhoc,runtime)`, `get-task-allow` 0; `DEVELOPER_ID` unset → 공증 env-gate N/A |

**Regression**: full suite `.venv/bin/python -m pytest server/tests/ -q` → `953 passed`(baseline 908 + 신규 45, 회귀 0; **오케스트레이터가 Part1·Part2 후 각각 직접 재실행 확인**). **Build**: PyInstaller 6.21.0, `.venv/bin/python -m PyInstaller --noconfirm --clean packaging/GrandMA3-Copilot.spec` → `Build complete!`, `dist/GrandMA3 Copilot.app`(arm64, `Contents/MacOS` 14.2MB exe). **Lint**: `ruff check` 변경/신규 파일 → `All checks passed!`. **dist/build**: 이미 gitignored(26-27줄) → 미커밋(`git ls-files`에 아티팩트 0).

**@MX tags added**: `server/resources.py` `resource_base` 위 `@MX:ANCHOR`(frozen/dev 유일 리졸버, `@MX:REASON` FEAS-1 — 분기 리졸버가 frozen 해석을 조용히 포크하면 번들 경로 붕괴 재발 + `@MX:SPEC`) 1건.

**커밋**: `ab9e584`(Part 1 — resource_base + launcher + keyring 가드 + 테스트, 10파일 1044+), `3a183ea`(Part 2 — `packaging/{*.spec,entry.py,entitlements.plist,sign.sh,build.sh,README.md}`, 6파일 464+). `feat/app-deploy-file-import` 직접 커밋(원격 없음 — push/PR 없음).

**잔여 리스크(M10 이관)**: `server/safety/audit.py` `DEFAULT_AUDIT_DIR = parents[1]/audit_logs`가 서명된 `.app`에서 `_MEIPASS`(읽기 전용) 아래로 해석 → 패키지 앱에서 **실제 조명 명령 실행 시 감사 로그 기록 실패** 가능(부팅은 lazy라 통과; M6 AC는 명령 실행 미검사로 통과). M1/M3 설정-경로 성격 = Part 1 로직 변경이라 M6에서 미수정, **M10(실제 명령 E2E)에서 사용자 쓰기 경로로 검증·수정**. universal2/Windows/실제 공증은 환경-게이트 N/A(빌드 호스트 arm64 전용·인증서 부재).

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F Phase 4 Mode Selection

Run scope: Stage-1 only (M1~M6). Depends_on gate: SPEC-COPILOT-MVP-001 in-progress → `--ignore-deps` override (user-approved, logged `.moai/logs/depends-on-override.log`). Phase-1 plan-audit gate on v0.2.0: PASS-WITH-DEBT ~0.87 (≥0.85, Stage-1 proceed).

Input parameters:
- tier: L
- scope: Stage-1 (M1~M6) — config layer + keyring adapter + settings UI + provisioning + health UI + PyInstaller onedir launcher across `server/` (Python) + `ui/` (TS/React) + packaging
- domain count: 3 (backend Python, frontend TS/React, packaging) — but coding-heavy, sequential-dependent milestones (M2 dep M1, M3 dep M1/M2, …)
- file language mix: Python + TS/React (Stage-1); Rust/Tauri deferred to Stage-2
- concurrency benefit: LOW (coding-heavy; per Anthropic coding-task parallelism caveat)

Mode evaluation:
| Mode | Selected | Rationale |
|------|----------|-----------|
| 1 trivial | no | multi-file, semantic |
| 2 background | no | write-heavy implementation, not read-only |
| 3 agent-team | no | RETIRED |
| 4 parallel | no | coding-heavy, milestones sequentially dependent — not research fan-out |
| 5 sub-agent | **YES** | coding-heavy multi-milestone → sequential manager-develop per milestone (TDD) |
| 6 workflow | no | not ≥30-file uniform mechanical transform; new-code implementation |

Decision: **sub-agent** (Mode 5). Progression: autonomous continuous (user-approved at Kickoff) — M1→M6 sequential, per-milestone report, stop only on blocker/decision. Methodology: TDD (cycle_type=tdd, new shell code). manager-develop commits directly to `feat/app-deploy-file-import` (no remote — no PR/push).
