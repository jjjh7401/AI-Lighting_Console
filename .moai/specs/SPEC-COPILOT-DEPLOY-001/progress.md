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

### Stage-2 M7 kickoff plan-phase authoring (v0.4.0, 2026-07-21)

`plan_status: audit-ready` (Stage-2 M7-first — 문서 전용 착수)

Stage-2를 **M7-first**로 착수하기 위한 계획·수용 기준을 확정했다(문서 전용 — 구현 코드·`src-tauri/` 생성 없음, `status: in-progress` 유지). 사전 확정 kickoff 결정 4건 반영: F5(sidecar↔UI = WebSocket 유지 + Origin allowlist + per-launch 토큰 핸드셰이크, FEAS-9 CSWSH 차단)·F5'(키 커스터디 = Python keyring 직접 유지)·teardown Option C(Rust process-group kill + 백엔드 parent-liveness watchdog, FEAS-5)·SAFETY-2 이중 스캔(Rust deny-all 정적 + wire-level 싱크). 신규 REQ-DEPLOY-002a([Event-driven] 핸드셰이크) 1건. AC-DEPLOY-024~029 신설(env-gate 명시: NOW=macOS arm64 dev/ad-hoc; AC-027 Layer①=M7.4 scaffold 이후·Layer②=NOW; universal2·Windows·실제 notarization=N/A). **M8(자동 업데이트)·M9(코드 서명/공증)은 Stage-2-DEFERRED** — 별도 kickoff. §F 결정 원장: 8 resolved(F5·F5' 추가) + 1 deferred(F6). **plan-audit remediation D1–D10 반영**(FAIL~0.74→교정): D1 NEEDS-CLARIFICATION→DEFERRED-M8, D2/D3 AC-027 vacuous-scan 차단, D4 토큰 누출-저항+AC-029, D5 M8 중복행 삭제, D6 depends_on 정합, D7 watchdog EOF-primary, D8 HISTORY 정렬, D9 앵커 수정, D10 REQ-002a 트림. 다음: Implementation Kickoff Approval 후 M7 run-phase 착수(§C M7 구현 계획 M7.1~M7.4).

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

### M10 — 배포 통합 검증 (2026-07-20, cycle_type=tdd)

Stage-1 마지막 마일스톤 — 패키징된 셸의 안전 불변식 보존 + local-only + 패키지 앱 E2E를 자동 검증. arm64 macOS 대상(universal2/Windows/실제 공증 = 환경-게이트 N/A). A→B/C→D 순차, 매 Part 후 오케스트레이터 직접 재검증.

**Part A — 런타임 쓰기 경로 이관 (커밋 `43f5447`)**: 확인된 결함 — `audit.py DEFAULT_AUDIT_DIR = parents[1]/audit_logs`가 서명된 `.app`에서 `_MEIPASS`(읽기 전용) 아래로 해석 → `AuditLog.mkdir`/`record` 실패(재현 `PermissionError`). 전수 조사: audit_logs가 **유일한** 쓰기-번들 경로(backup은 OSC `SaveShow` 경유 로컬 쓰기 0, resources.py는 읽기 전용). 수정: `settings.py`에 `user_data_dir`/`resolve_runtime_audit_dir`(M1 `user_config_dir` 패턴 재사용) 추가 + `bootstrap.build_console_stack`가 frozen 시 사용자 데이터 폴더로 배선 — **`audit.py` 안전 코드 미변경(0회)**. 특성화 테스트: dev 경로 동일, frozen은 `_MEIPASS` 밖 사용자 폴더 + record 왕복 성공.

**Part B/C — 안전 불변식 회귀 + local-only (커밋 `f4548aa`, 테스트 전용)**: AC-DEPLOY-014 ① 단일 관문(deploy-shell 8개 모듈 전부 `SafetyGate`만 경유) ② 블랙리스트 승인 회귀(Delete 승인 없이 미실행; 패키지 스택에선 백업 확인 실패 시 fail-safe block으로 더 보수적) ③ **OSC 송신 표면 allowlist + fail-closed**(허용 밖 모듈이 송신 경로 진입 시 테스트 붕괴 — 실제 rogue 모듈 실투입 → AssertionError → 제거로 라이브 증명). AC-DEPLOY-002 ① `127.0.0.1` bind ② localhost UDP ③ 원격 백엔드 0(LLM API 제외) ④ 오프라인 동작. 기존 3개 per-module 가드를 1개 allowlist 테스트로 통합. Rust/Tauri 소스 스캔·wire-level 열거 = Stage-2(M7~M9) N/A.

**Part D — 패키지 `.app` HTTP E2E + P0 결함 수정 (커밋 `1d65375`)**: ⚠️ **E2E가 P0 통합 결함 포착** — `serve.build_runtime`가 `WebDeps`에 `settings=`/`provision=`을 조립하지 않아 **설정·키·provisioning REST 표면(`/api/settings`·`/api/keys`·`/api/provision/responder`)이 실제 서버에 미마운트**(패키지 앱에서 404/405). M3/M4 라우터는 존재·단위검증됐으나 M6 serve 조립 의무의 라우터-배선 절반이 누락(--add-data 절반만 반영). **단위 테스트 980개가 전부 놓친 통합 결함을 E2E가 잡음.** 수정: `build_runtime`에 `SettingsDeps`+`ProvisionDeps` 조립(`serve.py` +12줄, 로직 무변경, 기존 검증 라우터 재사용 = D-NEW-1 in-scope cascade) + 배선 회귀 테스트.

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-014 ①②③ (안전 불변식 회귀) | PASS | `pytest server/tests/test_deploy_safety_invariants.py -q`(오케스트레이터 재실행) | `11 passed`; fail-closed는 rogue 모듈 실투입→AssertionError→제거 후 통과로 라이브 증명 |
| AC-DEPLOY-002 ①②③④ (local-only) | PASS | `pytest server/tests/test_deploy_local_only.py -q`(오케스트레이터 재실행) | `8 passed`; 127.0.0.1 bind·localhost UDP·원격 0·오프라인 동작 |
| AC-DEPLOY-004/016 (frozen 감사 경로 = 사용자 폴더) | PASS (오케스트레이터 직접) | 프리즈 앱 부팅 후 `ls "~/Library/Application Support/GrandMA3 Copilot/audit_logs"` | `audit-20260720.jsonl` 실제 기록(번들 밖) |
| AC-DEPLOY-001~003/005/006/007 (패키지 E2E: 기동→설정→provisioning→health) | PASS (오케스트레이터 직접 E2E) | `.venv/bin/python packaging/verify_packaged_e2e.py` | `RESULT: ALL PASS` — healthz 200·SPA 200·/api/settings 200(키값 미노출)·설정 사용자 폴더 기록·provisioning 설치·감사 사용자 경로 |
| AC-DEPLOY-015 ① (깨끗한 종료) | PASS (오케스트레이터 직접) | E2E Step 8 SIGTERM | `rc=0`, 프로세스-트리 잔여 0, 포트 해제 |

**Regression**: full suite `.venv/bin/python -m pytest server/tests/ -q` → `983 passed`(908→964(A)→980(B/C)→983(D), 회귀 0; 오케스트레이터가 각 Part 후 직접 재실행). **E2E**: `packaging/verify_packaged_e2e.py` → 8/8 PASS(오케스트레이터 직접 실행). **Build**: PyInstaller 6.21.0 재빌드 `dist/GrandMA3 Copilot.app`(arm64). **Lint**: `ruff check` clean.

**@MX tags added**: (M10) 신규 프로덕션 표면 최소 — resource_base 앵커(M6)에 흡수, 신규 ANCHOR/WARN 기준 미충족(over-tag 회피).

**커밋**: `43f5447`(A — 사용자 데이터 경로 해석기+배선, 3파일), `f4548aa`(B/C — 안전 불변식+local-only 회귀, 테스트 전용 5파일), `1d65375`(D — serve 라우터 배선 P0 수정 + 패키지 E2E 드라이버, 3파일). `feat/app-deploy-file-import` 직접 커밋(원격 없음 — push/PR 없음).

**환경-게이트 N/A**: universal2·Windows x86_64 빌드(arm64 전용 CPython), 실제 Developer-ID 공증(인증서 부재), Rust/Tauri OSC 소스 스캔·wire-level 열거·onPC 라이브 명령 왕복(Stage-2 또는 onPC 필요).

### M14~M18 — 라이브 E2E 하드닝 배치 (구현 2026-07-21, cycle_type=tdd) — ⚠️ 회고적 문서 backfill (2026-07-22)

> ⚠️ **본 절은 회고적 backfill이며, 구현 당시의 실행 로그를 복원한 것이 아니다.** M14~M18(v0.3.0 라이브 E2E 하드닝, 결함 #2~#6, REQ-DEPLOY-028~032 / AC-DEPLOY-019~023)은 2026-07-21에 구현·커밋되고 §E.4에서 synced(`dcdb6f5`)되었으나 **§E.2에 증거 절이 없었다** — 기록은 §E.4 산문과 CHANGELOG.md뿐이었다. 아래 표는 2026-07-22 시점에 ① `grep -rn "AC-DEPLOY-0NN" server/ console/`로 **AC 앵커가 실재함을 확인**하고 ② 해당 테스트 파일을 **재실행해 현재 green임을 관측**한 결과다.
>
> **이 절이 주장하지 않는 것**: 구현 당시의 커버리지 수치, 당시의 회귀 delta, 당시의 @MX 태그 추가 내역, 마일스톤별 커밋 SHA. 그 값들은 관측되지 않았으므로 여기에 쓰지 않는다(당시 전체 스위트 `1017 passed`는 §E.4 v0.3.0 항목의 기록). 아래 테스트 수는 **2026-07-22 재실행 시점의 파일 전체 수**이며 M14~M18이 추가한 신규 건수가 아니다.

| 마일스톤 / AC | Status | Verification Command (2026-07-22 재실행) | Actual Output |
|----|--------|----------------------|---------------|
| **M14** — 기동 시 활성 프로바이더 키 주입 (#2) / AC-DEPLOY-019 | PASS (앵커 실재 + 재실행 green) | `grep -n "AC-DEPLOY-019" server/tests/test_web_serve.py` → 앵커 2건(`:416` 하네스 주석, `:516` 테스트 docstring); `pytest server/tests/test_web_serve.py -q` | `32 passed` — `build_runtime`가 프로바이더 클라이언트 생성 이전에 활성 프로바이더 키를 env로 주입, 기설정 env 보존, 저장소 미가용 시 세션 폴백 |
| **M15** — 마지막 생성 연출 상태 세션 주입 (#4) / AC-DEPLOY-021 | PASS (앵커 실재 + 재실행 green) | 앵커: `test_last_created.py:1`, `test_web_session.py:501`, `test_runner_self_correction.py:281`(③ 재생성 선호) + 구현 `server/orchestrator/last_created.py`; `pytest server/tests/test_last_created.py server/tests/test_web_session.py server/tests/test_runner_self_correction.py -q` | `10 passed` / `28 passed` / `16 passed` |
| **M16** — Gemini 캐시 만료 복구 + 오류 분류 (#5) / AC-DEPLOY-022 | PASS (앵커 실재 + 재실행 green) | 앵커: `test_gemini_adapter.py:214`(① TTL 만료), `:229`(① 404 절), `:485`(② No-API-key→auth), `test_web_errors.py:76`, `test_web_session.py:462` + 구현 `server/llm/gemini_adapter.py`; `pytest server/tests/test_gemini_adapter.py server/tests/test_web_errors.py -q` | `41 passed` / `26 passed` |
| **M17** — rig-context 실제 풀 번호 명시 (#3) / AC-DEPLOY-020 | PASS (앵커 실재 + 재실행 green) — ⚠️ **Python 절만**; Lua 소스단 근본 수정은 아래 **M17.1**에서 수행됨 | 앵커: `test_tools.py:57/:80/:316/:337`(비연속 풀 1,2,7 픽스처) + 구현 `server/orchestrator/tools.py`; `pytest server/tests/test_tools.py -q` | `23 passed` |
| **M18** — OSC 수신 포트 재바인드 복구 (#6) / AC-DEPLOY-023 | PASS (앵커 실재 + 재실행 green) — ⚠️ **브리지 단위 절만**; §E.4 이연 #1(앱 셸 안내 표시)은 아래 **M18.1**에서 닫힘 | 앵커: `test_osc_bridge.py:254`(선점 포트 → 재바인드 시도) + `:264`(라이브 절 deferred N/A 명시) + 구현 `server/bridge/osc.py`; `pytest server/tests/test_osc_bridge.py -q` | `22 passed` |

**backfill이 바꾸지 않는 것**: §E.4 v0.3.0 sync 항목의 **Deferred items 3건**(#6 앱 셸 안내 표시 / 라이브 onPC 재검증 #2~#6 / #3 심층 Lua 슬롯 정합성)은 그대로 유효하다. 그중 #1과 #3은 2026-07-22 배치(M18.1 / M17.1)에서 다뤄지며, **라이브 재검증(#2)은 여전히 미해소**다.

### M7.1 — sidecar↔UI 전송 핸드셰이크 (2026-07-21, cycle_type=tdd, Stage-2)

Stage-2 M7의 첫 하위 마일스톤 — F5(REQ-DEPLOY-002a) 3-계층 중 **백엔드 게이트 + launcher 토큰 생성 + UI 소비 seam**만 착수. M7.2(teardown)·M7.3(SAFETY-2 이중 스캔)·M7.4(Tauri 스캐폴드)는 미착수이며 `src-tauri/`는 생성하지 않았다.

**FEAS-9 해소**: 기존 `/ws`는 `accept()`를 origin/token/CORS 검사 **0**으로 수행 → 임의 로컬 프로세스·브라우저 탭이 라이브 콘솔 제어 채널에 접속 가능(CSWSH). 신규 `server/web/handshake.py`가 accept **이전**에 판정하고, 거부 시 accept 없이 close(1008) — 거부된 클라이언트는 ChatSession·게이트·콘솔에 도달하지 않는다.

**오리진 2-클래스 설계(plan §M7.1 정합)**: ① **Stage-2(Tauri) 오리진** = 토큰 **필수**(IPC라는 누출-저항 채널로 전달 가능) — 누락/불일치 거부. ② **Stage-1(loopback 브라우저) 오리진** = 토큰 **심층방어만**(브라우저엔 IPC가 없고 디스크/loopback 전달은 위장-Origin 벡터를 못 막음) — 부재는 허용, **오배치 토큰은 여전히 거부**. 이 비대칭이 "Stage-1 브라우저 모드 무중단" HARD 제약과 AC-DEPLOY-025 ②를 동시에 만족시키는 유일한 해석이다. 토큰 비교는 전 경로 `hmac.compare_digest`(상수-시간).

**토큰 전달**: `Sec-WebSocket-Protocol`(`copilot-token.<token>`) — 브라우저/웹뷰 `WebSocket` API가 설정할 수 있는 유일한 핸드셰이크 필드이며, 쿼리스트링과 달리 액세스 로그·Referer에 남지 않는다. 서버는 비밀이 아닌 `copilot.v1`을 선택해 에코(RFC 6455). 토큰은 env/메모리 전용 — `LAUNCH_TOKEN_ENV="COPILOT_LAUNCH_TOKEN"`은 이름에 `TOKEN`을 포함해 `keystore.scrub_environ`이 크래시 덤프에서 자동 리댁션(DECIDE-M6 벡터 계승). `index.html` 메타 주입은 **미도입**(D4a 폐기 준수).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-025 ①~⑤ (핸드셰이크 accept/reject 매트릭스) | PASS | `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest server/tests/test_web_handshake.py -q` | `29 passed, 1 warning in 1.31s` — ① 비허용 Origin 거부 ② Stage-2 토큰 누락 거부 ③ 오배치 토큰 거부(compare_digest) ④ 정확 토큰 accept ⑤ 프로토콜 v1 불변(gated/ungated status 이벤트 동일) |
| AC-DEPLOY-029 ①②③ (per-launch 토큰 비밀 유지) | PASS | 동일 실행 `TestLaunchTokenSecrecy` 5건 | 앱이 쓴 파일 전수 스캔 토큰 0건(거부+수락 왕복으로 감사파일 실제 생성 — 비-vacuous), `scrub_environ` 리댁션, `index.html` 메타 주입 부재, 매 launch 신규 43자 토큰 |
| AC-DEPLOY-014 (안전 불변식 — 신규 OSC 송신 경로 0) | PASS | `pytest server/tests/test_architecture.py test_deploy_safety_invariants.py test_deploy_local_only.py -q` | `23 passed`; `grep -rnE "^\s*(from\|import)\s+(server\.bridge\|pythonosc)" server/web/` → 매치 0 |

**Regression**: full suite `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest server/tests/ -q` → `1046 passed`(baseline 1017 + 신규 29, 회귀 **0**). UI `npm test` → `57 passed`(baseline 53 + 신규 4). `npm run build`(tsc+vite) → `✓ built in 313ms`. `ruff check server/` → `Found 2 errors`(둘 다 기존 baseline `server/safety/console.py:221/258` E501, **NEW 0**).

**@MX tags added**: `server/web/handshake.py` `evaluate_handshake`에 `@MX:ANCHOR`(+`@MX:REASON`/`@MX:SPEC`) — `/ws` 인가 경계이자 라이브 콘솔 제어 채널의 유일한 관문. Stage-1 토큰-선택 분기가 의도된 load-bearing 설계임을 REASON에 명시(제거 시 브라우저 모드 붕괴).

**M7.4 이연(명시)**: Windows Tauri 웹뷰 오리진(`tauri.localhost` 예약 TLD)은 AC-DEPLOY-002 `_LOOPBACK_HOSTS` 가드와 충돌하여 **allowlist에 미포함** — `handshake.py` 주석에 M7.4 필수 조치로 기록. 미조치 시 Windows Tauri 창이 `origin_not_allowed`로 거부된다. Stage-2 토큰의 Tauri IPC 주입(`__COPILOT_LAUNCH_TOKEN__` 설정)은 M7.4 스코프이며, 소비 측 seam은 본 마일스톤에서 완성.

**커밋**: `7573e60`(plan-phase 산출물 v0.4.0 fold-in, 문서 전용), M7.1 구현 커밋(아래 §E.3). `feat/app-deploy-file-import` 직접 커밋(원격 없음 — push/PR 없음).

### M7.2 — sidecar 수명주기 teardown / 백엔드 half (2026-07-21, cycle_type=tdd, Stage-2)

Stage-2 M7의 두 번째 하위 마일스톤 — teardown Option C(FEAS-5) 2-축 중 **백엔드 parent-liveness watchdog(self-reap)만** 착수. `src-tauri/` 미생성, Rust 코드 0줄.

**스코프 분할(명시)**: Option C의 **Rust authoritative half**(Unix `pre_exec` setsid/setpgid, Windows `KILL_ON_JOB_CLOSE` Job Object, `RunEvent::Exit` process-group kill)는 `src-tauri/` 스캐폴드 이전에는 존재할 수 없으므로 **M7.4로 이월**한다. 따라서 본 마일스톤이 검증하는 것은 **AC-DEPLOY-026 ③(Tauri force-quit → 백엔드 self-reap, 잔여 0)과 ④(재기동 `require_ports_available` fail-closed)** 뿐이며, **① 정상 종료·② 백엔드 크래시는 Rust half 부재로 DEFERRED-M7.4**다(미검증을 통과로 주장하지 않음).

**구현**: `server/web/launcher.py`에 `ParentLivenessWatchdog` + `install_parent_watchdog` 신설. **PRIMARY = pipe EOF** — 호스트가 자기 수명 동안 write end를 쥐고 있으므로 어떤 죽음(정상 종료·크래시·force-quit)이든 마지막 write end가 닫혀 read end가 **즉시** readable-at-EOF가 된다(레이스 창 0, 폴링 없음). 비어있지 않은 read는 하트비트로 해석. **FALLBACK = `getppid()` 폴링** — 파이프 미상속/fd 불량 시 `PARENT_POLL_INTERVAL_SECONDS = 0.25`(≤ `MAX_REAP_LATENCY_SECONDS = 1.0`, 생성자에서 강제) 주기로 init(pid 1) 재부모화를 감지. 트리거 시 **기존 `terminate_process_tree`를 그대로 재사용**해 자기 그룹을 SIGTERM→SIGKILL로 수확하므로, 자신에게도 도달하는 SIGTERM이 기존 `make_shutdown_handler`를 태워 **콘솔 스택 stop → 트리 수확 → exit 순서가 불변**이다(트리거만 신설, 순서 무변경).

**오탐 차단(설계상 중요)**: watchdog은 호스트가 스스로를 선언한 경우(`COPILOT_PARENT_PIPE_FD` / `COPILOT_PARENT_PID`)에만 무장한다. Stage-1 더블클릭 실행은 launchd(pid 1)가 부모일 수 있고 터미널 실행은 셸 종료로 고아가 될 수 있어, 무조건 무장하면 **정상 서버를 자살시킨다**. 미선언 launch는 `install_parent_watchdog` → `None`(완전 무영향).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-026 ③ (force-quit self-reap, 잔여 0 + 포트 해제) | PASS | `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest server/tests/test_web_launcher.py -q` | `43 passed in 7.4s` — `TestSidecarSelfReap` 2건이 실제 subprocess로 증명: ① pipe EOF(부모가 write end close) → sidecar+grandchild 잔여 0, web(TCP)/OSC(UDP) 포트 재바인드 가능 ② 파이프 없는 진짜 고아(부모 SIGKILL) → `getppid()` 폴백으로 동일 결과 |
| AC-DEPLOY-026 ③ (bounded max reap latency ≤ 1s) | PASS | 동일 실행 `TestWatchdogBounds` / `TestWatchdogPipeEOF` / `TestWatchdogGetppidFallback` | `PARENT_POLL_INTERVAL_SECONDS(0.25) ≤ MAX_REAP_LATENCY_SECONDS(1.0) ≤ 1.0` assert + 양 트리거의 실측 elapsed ≤ 1.0s assert + `poll_interval=5.0`/`0` 생성자 `ValueError`. 프로세스 레벨은 `_REAP_DEADLINE_SECONDS = 1.0 + 4.0`(감지 상한 + OS teardown)로 상한-결정적 스캔 |
| AC-DEPLOY-026 ④ (재기동 fail-closed) | PASS | 동일 실행 `TestSidecarSelfReap::test_pipe_eof_reaps_the_group_and_frees_the_ports` | sidecar 생존 중 `require_ports_available` → `PortInUseError` 발생(조용한 포트 드리프트 0), self-reap 후 동일 호출 통과 |
| AC-DEPLOY-026 ① 정상 종료 / ② 백엔드 크래시 | **DEFERRED-M7.4** → ✅ **이후 M7.4b에서 PASS** (아래 상호참조) | — | Rust `RunEvent::Exit` + setsid/Job Object 부재. 본 마일스톤에서 **검증 불가 → 주장하지 않음** |

> 📌 **이연 해소 상호참조 (2026-07-22 추가 — 위 행의 역사적 기록은 그대로 보존)**: 위 `DEFERRED-M7.4`는 **이미 닫혔다.** ① 정상 종료와 ② 백엔드 크래시는 **§E.2 M7.4b 절의 AC 표 첫 두 행에서 패키지 `.app` 증거와 함께 PASS**로 기록되어 있다(증거 파일 `.moai/state/verify/m74b/ac026-1-normal.txt` / `ac026-2-crash.txt`). Rust 구현은 `src-tauri/src/sidecar.rs`의 `reap_backend_group`(`:296`) + `libc::killpg` SIGTERM→SIGKILL(`:273`/`:284`) + `group_kill_target`(호스트 그룹 시그널 거부, `:222`)이며, `RunEvent::Exit` 배선은 `:440`이다. 소스 가드는 `server/tests/test_deploy_tauri_seams.py`(AC-DEPLOY-026 ①② 앵커 `:7`/`:66`/`:76`/`:103`/`:111`). Windows Job Object 절만 `PENDING-WINDOWS`로 잔존(`sidecar.rs:320`~`:325`). *"DEFERRED"를 grep한 독자가 미해소로 오독하지 않도록 추가한 전방 참조이며, 위 행의 원문은 수정하지 않았다.*
| AC-DEPLOY-014 (안전 불변식 — 신규 OSC 송신 경로 0) | PASS | `pytest server/tests/test_architecture.py server/tests/test_deploy_safety_invariants.py -q` | `15 passed in 6.15s`; `grep -rnE "^\s*(from\|import) server\.bridge" server/web/` → 매치 0(watchdog은 프로세스-시그널 전용) |

**Regression**: full suite → `1063 passed`(baseline 1046 + 신규 17, 회귀 **0**). UI `npm test` → `57 passed`(무변경), `npm run build` → `✓ built in 343ms`. `ruff check server/` → `Found 2 errors`(둘 다 기존 `server/safety/console.py:221/258` E501, **NEW 0**). 테스트 프로세스 누수 스캔(`ps | grep watchdog_child`) → 잔여 0.

**@MX tags added**: `server/web/launcher.py` `ParentLivenessWatchdog`에 `@MX:ANCHOR`(+`@MX:REASON`/`@MX:SPEC`) — 부모 신호 없이 이 프로세스 **그룹**을 무너뜨리는 유일한 경로. REASON에 양방향 위험(트리거 누락 → grandchild 포트 스쿼팅 / 오탐 무장 → 정상 서버 자살)을 명시.

**환경-게이트 N/A**: Windows Job Object 경로는 Windows 러너 확보 시(현 arm64 macOS 호스트) — 위장 검증 없음.

**커밋**: M7.2 구현 커밋 1건(`feat/app-deploy-file-import` 직접 커밋 — 원격 없음, push/PR 없음). 변경 파일: `server/web/launcher.py`, `server/web/serve.py`, `server/tests/test_web_launcher.py`, `server/tests/watchdog_child.py`(신규 테스트 헬퍼).

### M7.3 — SAFETY-2 교차언어 이중 스캔 (2026-07-21, cycle_type=tdd, Stage-2)

Stage-2 M7의 세 번째 하위 마일스톤 — Python-전용 가드(`test_architecture.py` import 경계 + `test_deploy_safety_invariants.py` AST allowlist)가 볼 수 없는 **Rust/wire 사각지대**를 닫는다. `src-tauri/` 미생성, Rust 소스 0줄(픽스처 제외 — 스캐폴드는 M7.4).

**신규 파일**: `packaging/rust_scan.py`(Layer ① deny-all 스캐너), `packaging/wire_sink.py`(Layer ② UDP 싱크 + 감사 대조), `server/tests/test_deploy_cross_language_scan.py`(24건), `server/tests/fixtures/rust_scan/{rogue,rogue_lock,rogue_capability,clean}/`(상시 CI 고정 픽스처). **배치 근거**: 두 모듈은 raw socket을 생성하므로 `server/` 아래 두면 기존 AST 송신-표면 allowlist와 충돌한다 → `packaging/`(배포 도구, 서버 프로덕션 코드 아님)에 둔다. 기존 두 가드는 **무변경**(약화 0, 병행 추가).

**Layer ① — Rust deny-all 정적 스캔**: `**/*.rs` + `Cargo.toml` + `Cargo.lock` + `capabilities/*.json`를 **빈(deny-all) allowlist**로 스캔. 마커 `UdpSocket`/`std::net::`/`.bind|.connect|.send_to`/OSC 크레이트/`127.0.0.1`·콘솔 포트(8000·9000) 리터럴. 주석은 **문자열 리터럴 인식 스트리퍼**로 제거(산문 disclaimer 오탐 방지 — Python AST 스캔과 동일 관용) 하되 `"http://127.0.0.1:8000"` 같이 **문자열 안에 숨은 마커는 계속 flag**(순진한 `//` 스트리퍼는 fail-OPEN). 매니페스트는 **2단 denylist**: OSC/raw-UDP 크레이트는 **전이 `Cargo.lock` 포함 어디서든** 거부, `socket2`/`mio`/`reqwest` 등은 **직접 의존일 때만** 거부(tokio/hyper가 이들을 정당하게 전이로 끌어오므로 lock에서 거부하면 M7.4에 통과 불가능한 게이트가 된다).

**Layer ② — wire-level 패킷 싱크**: 싱크를 **effective settings에서 해소한 실제 send_port**에 바인드(하드코딩 8000 아님 — 감사 결함 D3). 관측된 모든 datagram을 OSC 디코드 → responder verb/subject로 정규화 → 게이트 감사 `executed` 로그와 **1:1 다중집합 대조**. 방향은 의도적으로 비대칭: **관측O·감사X = 위반**(Rust sidecar raw UDP 우회가 정확히 이 형태), **감사O·관측X = 정상**(UDP 유실/전송 전 검증 실패는 우회가 아님).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-027 Layer ① ④ (MANDATORY 픽스처 — rogue FAIL / clean PASS) | PASS | `.venv/bin/python packaging/rust_scan.py server/tests/fixtures/rust_scan/{rogue,rogue_lock,rogue_capability,clean}` | rogue `FAIL — 3 file(s) scanned (rust=1, manifest=2, capability=0), 12 violation(s)`(exit=1) / rogue_lock `FAIL — 1 violation`(전이 `nannou_osc`, exit=1) / rogue_capability `FAIL — 2 violation`(`http:default`+`websocket:allow-connect`, exit=1) / clean `PASS — 4 file(s) scanned (rust=1, manifest=2, capability=1), 0 violation(s)`(exit=0) |
| AC-DEPLOY-027 Layer ① ①② (부재/빈 트리 = FAIL(blocked), `files_scanned > 0`) | PASS | `pytest server/tests/test_deploy_cross_language_scan.py -q` (`TestLayer1FailsClosedOnAnEmptyOrAbsentTree` 3건) | `23 passed, 1 skipped in 3.65s` — 부재 트리 `blocked=True, files_scanned=0, ok=False`; 빈 트리 동일; `target/`만 있는 트리도 blocked(빌드 산출물로 files_scanned 부풀리기 차단) |
| AC-DEPLOY-027 Layer ① ③ (실제 `src-tauri/` deny-all 게이트) | **PENDING-M7.4** | `.venv/bin/python packaging/rust_scan.py` | `BLOCKED (…/src-tauri does not exist — a deny-all scan of an absent tree is a FAIL (blocked), not a pass)` exit=1. **미검증을 통과로 주장하지 않음.** 활성화 조건 아래 참조 |
| AC-DEPLOY-027 Layer ② ① (싱크 = effective settings의 send_port, 8000 아님) | PASS | `pytest …::TestLayer2SinkBindsTheConfiguredPort` + 패키지 E2E Step 8 | 단위: `resolve_effective_settings(user_path=…)` → `console_port == sink.port != DEFAULT_CONSOLE_PORT`. 패키지: `sink bound to effective send_port 51703 (GET /api/settings console_port=51703; NOT the 8000 default)` |
| AC-DEPLOY-027 Layer ② ②③ (1:1 대조 + **양성 관측 ≥1**) | PASS | `.venv/bin/python packaging/verify_packaged_e2e.py` (Step 8) | `positive observation: 4 datagram(s) captured, 4 reconciled 1:1 against 4 gate 'executed' audit entries` / `verbs observed: ['exec', 'ping']` / `0 observed-but-unaudited senders`. 단위: 빈 캡처 `reconcile((), [])` → `positive_observation=False, ok=False`(vacuous 충족 차단) |
| AC-DEPLOY-027 Layer ② ④ (미감사 송신자 fail-closed + synthetic rogue flag) | PASS | 동일 실행 (`TestLayer2FailsClosedOnAnUnauditedSender` 2건 + E2E Step 8) | 단위: 게이트를 거치지 않은 `/copilot/cmd "Delete Sequence 5"` 주입 → `unaudited=1, ok=False`; 비-OSC 바이트열 → `verb="?"` → `ok=False`. 패키지: `synthetic rogue datagram injected off-gate -> FLAGGED (1 unaudited)` |
| AC-DEPLOY-027 공통 (Tauri capabilities 네트워크 플러그인 deny) | **부분 PASS(메커니즘) / PENDING-M7.4(실파일)** | `pytest …::TestLayer1CapabilityScan` | 스캐너가 `capabilities/*.json`을 읽어 `http:`/`websocket:`/`upload:`/`geolocation:` 권한을 flag함을 픽스처로 증명(rogue_capability FAIL, clean sidecar-scoped PASS). **실 capability 파일 작성은 M7.4** — `src-tauri/` 부재로 지금 작성 불가 |
| AC-DEPLOY-014 (안전 불변식 — 신규 OSC 송신 경로 0) | PASS | `pytest server/tests/test_architecture.py server/tests/test_deploy_safety_invariants.py -q` | `15 passed`(기존 가드 무변경·무약화). `ls -d src-tauri` → `No such file or directory`; `find . -name "*.rs"` → 픽스처 4건뿐 |
| 패키지 E2E 전체 (회귀) | PASS | `.venv/bin/python packaging/verify_packaged_e2e.py` | `RESULT: ALL PASS` — Step 1~9 전부 PASS(신규 Step 8 삽입, 기존 SIGTERM 단계는 Step 9로 번호 이동). 실 frozen `.app`, loopback, onPC 불요 |

**Regression**: full suite → `1086 passed, 1 skipped`(baseline 1063 + 신규 23 통과 + 1 PENDING-M7.4 skip, 회귀 **0**). UI `npx vitest run` → `57 passed`(무변경), `npm run build` → `✓ built in 330ms`. `ruff check server/ packaging/` → `Found 2 errors`(둘 다 기존 `server/safety/console.py:221/258` E501, **NEW 0**).

**RED 증명(mutation)**: 구현을 4회 인위적으로 무력화해 가드가 실제로 무는지 확인 — ① 부재-트리 `blocked=False`로 변조 → 2건 FAIL ② 양성-관측 요구 제거 → 1건 FAIL ③ 소스 마커/전이 denylist/capability denylist 비우기 → 4건 FAIL ④ 미감사 datagram을 matched로 처리 → 2건 FAIL. 원복 후 전건 green.

**@MX tags added**: `packaging/rust_scan.py` `scan_rust_source`·`scan_rust_tree`, `packaging/wire_sink.py` `reconcile`, `server/tests/test_deploy_cross_language_scan.py` `M74_PENDING_REASON` — 4건 모두 `@MX:ANCHOR` + `@MX:REASON` + `@MX:SPEC`.

**M7.4 의무(명시 이월)**:
1. **Layer ① 실트리 게이트 활성화** — `src-tauri/` 생성 즉시 `TestLayer1RealSrcTauriGate::test_real_tree_gate_state_is_accurate`(항상 실행, **자동 flip**)가 blocked-분기에서 deny-all 분기로 전환되고, `test_real_src_tauri_tree_passes_the_deny_all_scan`의 `skipif`가 자동 해제된다. **통과 조건**: `blocked=False` + `files_scanned>0` + `violations==()` + `capability_files_scanned>0`. 잊힘 방지를 위해 `PENDING-M7.4`를 grep 가능한 마커로 6곳에 고정.
2. **Tauri v2 capability 파일 작성** — `src-tauri/capabilities/default.json`에 **모든 네트워크 플러그인 deny**(`http:`/`websocket:`/`upload:`/`geolocation:` 권한 0건) + `tauri-plugin-shell`을 **sidecar spawn만으로 스코프**. `server/tests/fixtures/rust_scan/clean/capabilities/default.json`이 형태 참조.
3. **Rust 소스의 loopback/포트 리터럴 금지(설계 제약)** — deny-all은 `127.0.0.1`·8000·9000 리터럴도 위반으로 본다. Tauri 셸이 웹뷰에 웹 포트를 알려야 한다면 리터럴 하드코딩이 아니라 sidecar/IPC로 전달해야 한다(M7.1 토큰 주입 경로와 동일 축).
4. **Layer ② 1:1 회계의 알려진 예외** — `ConsoleLink._deploy_via_file_import`는 게이트 감사 `kind="deploy"` **1건** 아래에서 콘솔 왕복을 **여러 번**(state 조회·`Delete Plugin`·`Import Plugin`) 수행하므로, deploy를 포함하는 캡처는 datagram 수 > 감사 수가 된다. 우회는 아니지만(명령 문자열이 고정 리터럴, lock/health 재검사 적용) **회계 갭은 실재**하므로 `wire_sink.py` docstring에 기록했고 M7.4/후속에서 별도 판단이 필요하다.

**환경-게이트 N/A 없음(Layer ②)** — 순수 loopback으로 지금 완전 검증됨(실 frozen `.app` 위에서 실행). Layer ①의 실트리 절만 M7.4 게이트.

**커밋**: M7.3 구현 커밋 1건(`feat/app-deploy-file-import` 직접 커밋 — 원격 없음, push/PR 없음).

### M7.4a — Tauri v2 셸 스캐폴드 + sidecar spawn (2026-07-21, cycle_type=tdd, Stage-2)

Stage-2 M7의 네 번째 하위 마일스톤 전반부 — 본 저장소 **최초의 Rust 코드**. `src-tauri/` 스캐폴드 + M6 PyInstaller onedir 백엔드의 sidecar spawn + 네이티브 창(`ui/dist` 로드) + 트레이/health 배지 + deny-all capability. **M7.4b 이월**: Rust `RunEvent::Exit` authoritative group-kill(AC-026 ①②), 토큰 IPC 주입(AC-025 Stage-2 경로).

**신규 파일**: `src-tauri/{Cargo.toml,Cargo.lock,build.rs,tauri.conf.json,.gitignore}`, `src-tauri/src/{main.rs,sidecar.rs,tray.rs,startup_error.rs}`, `src-tauri/capabilities/default.json`, `src-tauri/icons/*`, `packaging/stage_sidecar.py`, `package.json`(+lock), `server/tests/test_deploy_tauri_shell.py`(37건), `server/tests/test_web_host_channel.py`(11건), `server/web/host_channel.py`.

**설계 — 백엔드 주소를 리터럴 없이 얻는 경로**: deny-all 스캔이 Rust에서 `127.0.0.1`·콘솔 포트 리터럴을 금지하므로(M7.3 이월 의무 #3) 셸은 백엔드 주소를 **컴파일 타임에 알 수 없다**. 백엔드가 **실제로 바인드된 뒤** stdout에 `@copilot:ready <url>` 한 줄을 출력하고(`server/web/host_channel.py`), Rust가 `CommandEvent::Stdout`에서 그 줄을 파싱해 창을 만든다. 동일 채널로 `@copilot:status <health>`(online/console_offline/responder_degraded — M5 게이트 진실)가 흘러 트레이 배지를 갱신한다. 셸의 인바운드 채널은 이 stdout **뿐**이며 소켓은 0개다.

**🔴 부모 선언(silent-failure trap)**: sidecar spawn이 `COPILOT_PARENT_PIPE_FD=0`(PRIMARY — 호스트가 수명 내내 쥐고 있는 stdin 파이프의 EOF, 레이스 창 없음) + `COPILOT_PARENT_PID`(FALLBACK)를 넘기지 않으면 M7.2 워치독이 **아무 신호 없이 미무장**된다. 리뷰가 아니라 **구조적 가드 테스트**로 고정: 선언 상수가 spawn 함수 **본문 안**에서 참조되는지까지 검사하고, 기대값을 `server/web/launcher.py`에서 **import**하므로 Python 쪽 이름을 바꾸면 조용히 무장 해제되는 대신 테스트가 깨진다. 가드 자체도 합성 positive/negative control 4건으로 검증(가드가 실패할 수 없으면 가드가 아니다).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-024 ① (sidecar spawn — **패키지 `.app`**) | PASS | `open "src-tauri/target/release/bundle/macos/GrandMA3 Copilot.app"` (더블클릭 등가, ppid=1/launchd) → 로그 `.moai/state/verify/m74a/09-double-click-launch.log` | `[shell] sidecar resolves to /…/GrandMA3 Copilot.app/Contents/MacOS/copilot-backend (exists: true)` / `[shell] backend sidecar spawned as pid 22408` / `ps`: `22408 22396 22408 …/Contents/MacOS/copilot-backend`(ppid=셸, **pgid=자기 pid → 세션 리더**) |
| AC-DEPLOY-024 ② (네이티브 창이 `ui/dist` 로드, SPA 200) | PASS | 동일 실행 | `[backend] INFO: 127.0.0.1:64290 - "GET / HTTP/1.1" 304` / `"GET /assets/index-Dpxz527G.js" 304` / `"GET /assets/index-Assl78sO.css" 304` / `"WebSocket /ws" [accepted]` / `"GET /api/settings HTTP/1.1" 200 OK` — 창이 백엔드가 서빙한 **동일 `ui/dist`** 를 실제로 로드하고 `/ws` 핸드셰이크까지 통과 |
| AC-DEPLOY-024 ③ (트레이 + health 연결 상태 배지) | PASS | `.venv/bin/python …/probe_bundle.py` → `.moai/state/verify/m74a/06-packaged-app-launch.log` | `windows: grandMA3, grandma3-copilot-shell,, GrandMA3 Copilot` / `menu bars: missing value, menu bar`(상태바 항목 존재). 배지 값은 M5 어휘 그대로(`tray.rs::health_label` — online/console_offline/responder_degraded) 이며 `@copilot:status` 라인으로 갱신 |
| AC-DEPLOY-024 자동 (capabilities가 sidecar-spawn 외 네트워크 플러그인 deny) | PASS | `pytest server/tests/test_deploy_tauri_shell.py::TestCapabilityDeniesNetworkPlugins -q` | `3 passed` — `default.json` 권한은 `core:default` + **스코프된** `shell:allow-execute`(`allow:[{name:"binaries/copilot-backend", sidecar:true, args:false}]`) 뿐; `http:`/`websocket:`/`upload:`/`geolocation:` 0건, `shell:allow-open` 금지 |
| **AC-DEPLOY-027 Layer ① ③ (실 `src-tauri/` deny-all — PENDING-M7.4 해제)** | **PASS** | `.venv/bin/python packaging/rust_scan.py` | `PASS — 8 file(s) scanned (rust=5, manifest=2, capability=1), 0 violation(s)` exit=0. **`files_scanned=8 > 0`, `capability_files_scanned=1 > 0`, 위반 0** |
| AC-DEPLOY-027 Layer ① 자동 flip (skip 소멸) | PASS | `pytest server/tests/test_deploy_cross_language_scan.py -q` | `24 passed`(직전 `23 passed, 1 skipped` → **skip 0**). `test_real_tree_gate_state_is_accurate`가 blocked-분기에서 deny-all 분기로 자동 전환, `test_real_src_tauri_tree_passes_the_deny_all_scan`의 `skipif` 자동 해제 |
| AC-DEPLOY-027 Layer ③ (capability 파일 실작성) | PASS | `pytest …::TestCapabilityDeniesNetworkPlugins` + `rust_scan.py` | 스캐너가 실제 `capabilities/default.json`을 읽고(`capability_files_scanned=1`) 위반 0. M7.3이 픽스처로만 증명하던 절이 실파일로 활성 |
| 🔴 부모 선언 가드 (spawn이 워치독을 무장시킴) | PASS | `pytest …::TestSidecarParentDeclaration ::TestParentDeclarationGuardDetectsItsOwnFailure -q` | `8 passed`. 실제 spawn 환경 직접 관측: `env COPILOT_PARENT_PIPE_FD: ['COPILOT_PARENT_PIPE_FD=0']`, `env COPILOT_PARENT_PID: ['COPILOT_PARENT_PID=14431']`(패키지 `.app` 실행 중 `ps -Ewwo`) |
| 부모 선언 **행동 증명**(패키지 아티팩트, force-quit) | PASS | `.venv/bin/python …/probe_forcequit.py` → `.moai/state/verify/m74a/07-packaged-forcequit.log` | 셸에 **SIGKILL**(=`RunEvent::Exit` 미발화 → Rust는 아무것도 못 함) → `backend pids after force-quit: [] (after 0.49s)` / `self-reaped: True` / `port 8765 still held: False`. **선언이 실제로 도달했을 때만 가능한 결과** |
| Rust 소스에 loopback/포트 리터럴 0 | PASS | `pytest …::TestShellHasNoBackendAddressLiteral -q` | `2 passed` — `*.rs` 전수에 `127.0.0.1`/`localhost`/`8765`/`8000`/`9000` 0건. 창 URL은 `READY_PREFIX` 파싱으로만 획득 |
| PENDING-WINDOWS (Windows origin 이연 유지) | PASS | `pytest …::TestWindowsOriginStaysDeferred -q` | `3 passed` — `TAURI_ORIGINS`에 `tauri.localhost` 없음, `server/web/handshake.py`에 grep 가능한 `PENDING-WINDOWS` 마커, `_LOOPBACK_HOSTS == {"127.0.0.1","localhost","::1"}`(**미확대**) |
| **패키지 번들 payload 회귀 가드**(dev-works/packaged-fails) | PASS | `pytest …::TestBundledSidecarCarriesItsRuntime -q` + 실 번들 positive/negative control | `7 passed`. **negative control**: 실 번들의 `Contents/Frameworks`를 치우고 동일 테스트 → `FAILED … stage_sidecar: no PyInstaller runtime payload in the bundle: …/Contents/Frameworks/base_library.zip — the sidecar would exit immediately on first launch`. 원복 후 `7 passed` |
| 오류 UX — spawn 실패가 panic이 아니라 안내 | PASS | `.venv/bin/python …/probe_broken.py` → `.moai/state/verify/m74a/08-error-ux.log` | 두 실패 형태 모두: `still alive after 20s = True` / `contains 'panicked': False` / `contains 'backtrace': False` / `contains 'What to try': True`. 로그: `[shell] GrandMA3 Copilot — backend did not start` + `1. Quit and relaunch… 2. …reinstall it. 3. Developer builds: run python packaging/stage_sidecar.py…` |
| 오류 UX 구조 가드 (setup hook이 `?`로 전파하지 않음) | PASS | `pytest …::TestAFailedSpawnIsReportedNotPanicked -q` | `3 passed` — `main.rs`에 `spawn_backend(handle)?` 부재 + `if let Err` 존재, `startup_error.rs`에 원인+다음 단계, 두 실패 경로 모두 `startup_error::report` 도달 |

**Regression**: `pytest server ui -q` → `1147 passed`(baseline `1086 passed, 1 skipped` → **skip 0**, 신규 61건, 회귀 **0**). `npx vitest run` → `57 passed`(무변경). `npm run build`(ui) → `✓ built in 334ms`. `ruff check server/ packaging/` → `Found 2 errors`(둘 다 기존 `server/safety/console.py:221/258` E501, **NEW 0**). `cargo build` → `Finished dev profile`(경고 0). `cargo clippy --all-targets` → 경고·오류 0. `npm run shell:build`(clean bundle) → exit 0 + `stage_sidecar: bundle OK`.

**런타임에서 잡은 결함 3건(정적 검토로는 안 보였음)**:
1. **ready 레이스** — `emit_ready`가 uvicorn 바인드 **전에** 출력되어 창이 connection-refused를 로드(관측됨). 셸은 소켓이 없어 재시도할 수 없으므로 준비 신호는 백엔드만 낼 수 있다 → `wait_until_serving`(포트가 실제로 점유될 때까지 대기) 후 announce. 3회 연속 재현으로 소멸 확인.
2. **sidecar 이름 해상도** — `tauri-plugin-shell`의 `relative_command_path`는 주어진 경로를 **실행 파일 디렉터리에 그대로 join**하고 타깃 트리플을 붙이지 않는다(플러그인 소스 `process/mod.rs:120-134`). 설정값 `binaries/copilot-backend`를 그대로 넘기면 `target/debug/binaries/…`를 찾아 ENOENT. Rust는 **베어 파일명**을 써야 한다 → `SIDECAR_NAME="copilot-backend"` / `SIDECAR_SCOPE_NAME="binaries/copilot-backend"`로 분리하고 두 철자를 가드 테스트로 고정.
3. **선언 pid 오신뢰** — 워치독이 선언된 부모 pid를 그대로 기대하면, 중간 프로세스가 끼는 순간 `ppid != expected`가 **첫 폴에서 참**이 되어 정상 백엔드를 수확한다. 선언은 무장 신호로만 쓰고 기대치는 **실제 부모**로 교차 검증. 같은 이유로 선언된 pipe fd가 실제 파이프인지 `is_liveness_pipe`로 검사(정규 파일/`/dev/null`은 즉시 EOF → 오수확).

**패키지 payload 메커니즘(가정 아님, 관측)**: Tauri `externalBin`은 **실행 파일 1개만** 번들에 넣는다. PyInstaller **onedir** 백엔드는 런타임 트리 없이는 부팅 못 하므로 dev는 녹색인데 패키지는 첫 spawn에서 죽는다(Stage-1 P0와 동일 부류). PyInstaller의 macOS `.app` 규약은 실행 파일이 `Contents/MacOS`에 있으면 런타임을 `Contents/Frameworks`에서 **평평하게** 찾는 것이며(실 `dist/GrandMA3 Copilot.app` 레이아웃과 일치), 이는 부트로더 자신의 출력으로 확인했다 — payload를 치운 A/B 테스트에서 `Failed to load Python shared library '…/GrandMA3 Copilot.app/Contents/Frameworks/libpython3.11.dylib'`. 따라서 `packaging/stage_sidecar.py --bundle <app>`이 런타임 트리를 `Contents/Frameworks`로 평평하게 복사하고 `--verify-bundle`이 이를 검증하며, `npm run shell:build`가 두 단계를 자동 실행한다. **`find <app> -name _internal`이 비는 것이 정상 형태**다(중첩 `_internal/`이 아니라 평평한 배치). 회귀 가드는 빌드된 번들이 있으면 항상 검사하고 없으면 skip(`PENDING-BUNDLE`)한다.

**@MX tags added**: `src-tauri/src/sidecar.rs::spawn_backend` — `@MX:ANCHOR` + `@MX:REASON` + `@MX:SPEC`(부모 선언 경계; 누락 시 무증상 실패).

**M7.4b 이월(명시)**:
1. **Rust authoritative group-kill** — `RunEvent::Exit`에서 `BackendProcess`(이미 managed state로 보관, `backend_pid()` 접근자 제공)를 프로세스 **그룹** kill. `CommandChild::kill()`은 sidecar pid만 죽인다. Windows Job Object(KILL_ON_JOB_CLOSE)는 러너 부재로 env-gate. → AC-026 ①②.
2. **토큰 IPC 주입** — 현재 창은 `http://127.0.0.1:<port>`(Stage-1 브라우저 오리진, 토큰 optional)를 로드한다. `tauri://localhost` + init-script/IPC 토큰 주입으로 옮기면 token-REQUIRED 경로가 된다. → AC-025 Stage-2 절.
3. **`.dmg` 타깃** — 현 `shell:build`는 `--bundles app`. payload 단계가 `.app` 생성 **후**에 돌아야 하므로 `.dmg`는 M9(서명·공증)에서 서명 파이프라인과 함께 다룬다.
4. **창 이중 로드 관측** — 로그에 `GET /` 2회 + `/ws` 다수가 보인다(창은 1개, 라벨 중복 오류 없음). 기능상 무해(멱등 GET)하나 원인 미규명 → M7.4b에서 확인.

**커밋**: M7.4a 구현 커밋 1건(`feat/app-deploy-file-import` 직접 커밋 — 원격 없음, push/PR 없음).

### M7.4b — Rust group-kill + Stage-2 토큰 IPC + 설정 정합 (2026-07-21, cycle_type=tdd, Stage-2)

M7.4a가 이월한 세 개의 교차언어 seam을 완성하고, 라이브 데모에서 잡힌 설정-vs-런타임 결함을 접었다. **신규 파일**: `server/tests/test_deploy_tauri_seams.py`(32건), `ui/src/launchContext.ts`. **수정**: `src-tauri/src/{sidecar.rs,main.rs}`, `src-tauri/Cargo.toml`(+lock: `libc` direct), `server/web/{app.py,launcher.py,serve.py}`, `ui/src/{useCopilotSocket.ts,components/*.tsx}`.

**설계 — 왜 `WebviewUrl::App`인가(관측 기반)**: M7.4a는 창이 `External(백엔드 URL)`을 로드해 오리진이 Stage-1 loopback이었고, 그래서 token-REQUIRED 분기가 실제 제품에서 절대 실행되지 않았다. M7.4b는 창을 **번들 앱**(`tauri://` 스킴, Stage-2 오리진)에서 로드하도록 옮겨 token-REQUIRED 분기를 실제 경로로 만든다. 대신 창이 더 이상 백엔드가 서빙하지 않으므로 SPA의 `/ws`·`/api/*`가 **교차-오리진**이 된다 → (a) 백엔드 base URL을 init-script로 주입(`__COPILOT_BACKEND_URL__`, `ui/src/launchContext.ts`가 소비, 상대경로 fetch를 절대경로로), (b) 핸드셰이크의 Stage-2 오리진에만 CORS 허용(와일드카드·자격증명 없음). 토큰은 호스트가 mint(`/dev/urandom` 64-hex)해 sidecar env + init-script 두 in-process 채널로만 전달(디스크 0, stdout 0 — AC-029).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| **AC-DEPLOY-026 ① (정상 종료 — 패키지 `.app`, group kill)** | PASS | 패키지 앱 실행 → `osascript -e 'tell application "GrandMA3 Copilot" to quit'`(메뉴/Cmd-Q 등가 → `RunEvent::Exit`) → `.moai/state/verify/m74b/ac026-1-normal.txt` | pre: `90362 90353 90362 …copilot-backend`(pgid=90362) + `8765 LISTEN` + `UDP 127.0.0.1:9005`. 종료 후: `[shell] reaping backend process group pgid 90362` → uvicorn `Shutting down`→`Finished server process` → **`RESIDUAL PIDS: 0`, `PORT 8765: FREE`, `OSC 9005: FREE`**. 로그가 `sidecar terminated`로 깨끗이 끝남 — **startup-error 다이얼로그 없음**(ready-flag 수정 확인) |
| **AC-DEPLOY-026 ② (백엔드 크래시 — 패키지 `.app`)** | PASS | 패키지 앱 실행 → `kill -9 <backend pid>`(하드 크래시) → Rust `CommandEvent::Terminated` 관측 → `.moai/state/verify/m74b/ac026-2-crash.txt` | `kill -9 93125` → `[shell] reaping backend process group pgid 93125` → `[backend] sidecar terminated: TerminatedPayload { code: None, signal: Some(9) }`(SIGKILL 확인). 크래시 후: `RESIDUAL backend pids: 0`, `GROUP 93125: empty (0 members)`, `8765: FREE`, `9005: FREE`. 셸은 살아있고 트레이 배지 STOPPED(크래시-후-서빙 → 정상, 다이얼로그 아님) |
| **AC-DEPLOY-025 Stage-2 경로 (라이브 패키지 백엔드 full matrix)** | PASS | `.venv/bin/python /tmp/ws_matrix.py <live token>` (백엔드 env에서 읽은 per-launch 토큰; `websockets` 실 클라이언트) → `.moai/state/verify/m74b/ac025-live-matrix.txt` | 5/5 `MATRIX PASS`: Stage-2 오리진(`tauri://localhost`)+**정확 토큰**→ACCEPT(첫 프레임 `{"type":"status","health":"online"}`); +누락 토큰→REJECT(HTTP 40x close); +오류 토큰→REJECT; disallowed 오리진(`evil.example`)→REJECT; Stage-1 브라우저 오리진+무토큰→ACCEPT(심층방어 분기 유지). 실 웹뷰가 `tauri://localhost`+토큰으로 접속함은 로그의 단일 `WebSocket /ws [accepted]` + `lsof`가 지목한 유일 클라이언트 `com.apple`(WebKit Networking, PID 90539)로 확인 |
| **설정-vs-런타임 정합 (라이브 결함 접기 — 패키지 검증)** | PASS | 사용자 `settings.toml`(`receive_port=9005`) 존재 상태로 패키지 앱 실행 → `lsof -a -p <backend> -iUDP` + `curl /api/settings` → `.moai/state/verify/m74b/settings-bind-check.txt` | 파일 `receive_port = 9005` → 백엔드 실제 바인드 **`UDP 127.0.0.1:9005`**(기본 9000 아님) → `/api/settings` 보고값 **`receive_port=9005`** → **바인드와 API가 구성상 일치**. onPC 출력이 9005이므로 health **`online`** 도달(코디네이터 성공 기준 충족). 회귀 테스트: `test_deploy_tauri_seams.py::TestPersistedSettingsDriveTheBoundPorts`(5건) — `stack.receive_port`(=`getsockname()`)로 실제 바인드 assert, 명시 플래그 우선·무파일 기본값·API-일치 포함 |
| **창 이중 로드 진단(M7.4a 잔여) — 근본원인 규명 + 수정** | PASS(수정됨) | 깨끗한 재launch → `.moai/state/verify/m74b/{live-run2.log,live2-clients.txt}` | **근본원인 2중**: (1) M7.4a는 앱 자신이 host-spawn에도 `open_app_browser`로 브라우저를 열었고, (2) 이전 실행이 남긴 stale Chrome 탭(고정 포트 8765 auto-reconnect). M7.4a 로그의 `GET / ×2 + /ws 다수`가 이 둘의 합. **수정 후 관측**: `GET /` **0회**(창이 `tauri://`에서 로드 → 백엔드 `GET /` 없음), `/ws` **정확히 1회**(웹뷰 단독), Chrome 연결 0. `serve.browser_open_enabled`가 host 선언 시 브라우저 억제(watchdog·detach와 동일 `launcher.host_declared` 술어 공유) |
| AC-DEPLOY-025/026 순수-단위 매트릭스 + seam 가드 | PASS | `pytest server/tests/test_deploy_tauri_seams.py -q` | `32 passed` — group-kill 소스 가드(killpg/SIGTERM<SIGKILL/own_pgid refusal/Terminated reap), 토큰 주입(동일 env·init-script·`WebviewUrl::App`·stdout 비밀 0), CORS(Stage-2만·자격증명 0·ungated 0), 브라우저 억제 3-소비자 정합 |
| Windows Job Object(KILL_ON_JOB_CLOSE) | N/A (env-gate) | — | Windows 러너 부재 → `reap_backend_group`의 `#[cfg(not(unix))]` 분기에 `PENDING-WINDOWS` 마커로 이연(핸드셰이크 origin 이연과 동형). 증거 위조 없음 |

**전체 스위트**: `pytest server/tests -q` → **`1179 passed`**(baseline 1147 + 신규 32, 회귀 **0**, 미설명 skip **0**; keyring null-backend 격리로 실행). `vitest` → `57 passed`. `npm run build`(ui) → `✓ built`. `cargo build` + `cargo clippy --all-targets` → 경고·오류 0. `packaging/rust_scan.py` → `PASS — 8 file(s), 0 violation(s)`(리터럴 0 유지 — 창 URL은 여전히 `@copilot:ready` stdout로만 획득). `ruff check server/` → `Found 2 errors`(둘 다 기존 `console.py:221/258` E501, **NEW 0**). M7.4a 번들 회귀 가드 `npm run shell:verify` → `bundle OK`.

**런타임에서 잡은 결함 1건(정적 검토로는 안 보였고, 첫 라이브 실행에서만 발현)**: 정상 종료 시 `RunEvent::Exit`가 백엔드를 SIGTERM→종료→`CommandEvent::Terminated` 발화. Terminated 분기는 "창이 없으면 startup 실패"라는 **live-window 검사**로 분기했는데, 종료 중엔 창이 이미 파괴되어 있어 **매 정상 종료마다 "backend did not start" 다이얼로그가 오발**됐다(첫 패키지 실행 로그에서 관측). 수정: "한 번이라도 ready URL을 냈는가"를 latch하는 `BackendReady`(AtomicBool)로 분기 — 서빙-후-종료(정상 종료·크래시)는 STOPPED 배지, ready 전 종료만 다이얼로그. 두 번째 패키지 실행에서 오발 소멸 확인.

**@MX tags added**: `sidecar.rs` — `mint_launch_token`(토큰 주입 경계), `group_kill_target`(호스트 그룹 시그널 거부 — 앱 자살 방지), `open_main_window`(Stage-2 오리진 경계) 각각 `@MX:ANCHOR`+`@MX:REASON`+`@MX:SPEC`. `_LOOPBACK_HOSTS`·`PENDING-WINDOWS`·핸드셰이크 무변경(가드 무약화).

**커밋**: M7.4b 구현 커밋 1건(`feat/app-deploy-file-import` 직접 커밋 — 원격 없음, push/PR 없음).

### M7.5 — deploy 경로 per-send 감사 granularity (2026-07-21, cycle_type=tdd, Stage-2)

M7.3이 명시 이월한 **Layer ② 1:1 회계의 알려진 예외**(이월 의무 #4)를 닫는다. 사용자 결정 **Option A**: 모든 콘솔 송신이 각자 감사 엔트리를 갖는다 — "every console send is audited 1:1" 불변식을 wire 수준에서 문자 그대로 복원.

**결함**: `ConsoleLink._deploy_via_file_import`는 콘솔 왕복 수 회(pool 조회·`Delete Plugin`·`Import Plugin`·확인 조회)를 게이트 감사 `kind="deploy"` **1건** 아래에서 수행 → deploy를 포함하는 wire 캡처는 datagram 수 > 감사 수가 되어 AC-027 Layer ② 대조가 정당한 deploy 트래픽을 "미감사 송신자"로 오탐.

**설계**: 콘솔 링크는 감사를 직접 쓰지 않는다(AuditLog 단일 기록 지점 `audit.py` **무변경**, 게이트 소유 유지). 대신 `deploy_plugin`이 왕복마다 `DeploySend`(kind/command/ok/detail/outcome) 레코드를 `ExecOutcome.sends`(additive 기본값 `()` — 기존 fake·호출부 무변경)로 **반환**하고, 유일한 감사 기록자인 게이트(`deploy_plugin_source`)가 각 레코드를 개별 `executed` 엔트리(`kind="state_query"|"command"`, 상관 필드 `deploy_of=<name>`)로 fan-out한 뒤 부모 `kind="deploy"` 요약 엔트리(`deploy_sends=N`)를 기록한다. file+Import 경로의 부모 엔트리는 wire datagram과 대응하지 않지만 이는 reconciler가 허용하는 **감사O·관측X 방향**(우회 아님). OSC deploy verb 폴백은 1송신=부모 1엔트리로 기존 그대로(`sends=()`). 상관은 `deploy_of` 이름 필드 + JSONL 순서(sub들이 부모에 선행)로 충분 — 합성 deploy-id 생성기는 두지 않음(단순성 사다리).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| (i) N 송신 → N 감사 엔트리 + 상관 | PASS | `pytest server/tests/test_responder_import_gate.py::TestPerSendDeployAuditGranularity server/tests/test_deploy_transport.py::TestFileImportPerSendRecords ::TestGatePerSendDeployAudit -v` | `8 passed` — fresh deploy `sends == [(state_query, DataPool/Plugins, ok), (command, Import Plugin 1 'CopilotResponder', ok), (state_query, …, ok)]`; redeploy는 `Delete Plugin 1` 포함 4건; 타임아웃 경로도 wire에 나간 2 datagram을 2 레코드로 기록(ok=False). 실제 JSONL(`.moai/state/verify/m75/10-audit-jsonl-sample.log`): sub 3건 각각 `"deploy_of": "CopilotResponder"` + 부모 `"kind": "deploy", "deploy_sends": 3` |
| (ii) deploy를 가로지르는 wire 대조 1:1·오탐 0 | PASS | `pytest server/tests/test_deploy_cross_language_scan.py::TestLayer2DeploySpanningCapture -v` (실 `build_console_stack` + effective-settings 포트의 실 UDP 싱크) | `2 passed` — deploy 관통 캡처 `observed>=2`(state+exec), `unaudited=()`, `positive_observation=True`, `ok=True`(**RED에서 동일 테스트가 `observed=2, matched=0, unaudited=2`로 실패했음** — `01-red.log`); off-gate rogue datagram은 deploy 캡처 중에도 여전히 `unaudited=1, ok=False` fail-closed |
| (iii) 단일 승인·게이트 clearance 무변경 | PASS | `pytest …::test_one_approval_still_covers_the_whole_deploy ::TestImportPluginTransitsTheGate ::TestGateDeploySurface -v` | `9 passed` — ScriptedReview **결정 1개**로 전체 deploy 성공(`deploy_review_approved` 정확 1건, 게이트 번들 `approved` 이벤트 0건 = per-send 승인 없음); live-lock/console-offline 차단·unconfirmed 마커·`kind="deploy"` 1건 회귀 테스트 전부 기존 그대로 green |

**Regression**: full suite → **`1189 passed`**(baseline 1179 + 신규 10, 회귀 **0**, skip 0; keyring null-backend 격리). `vitest` → `57 passed`. `rust_scan.py` → `PASS — 8 file(s), 0 violation(s)`. `ruff check server/ packaging/` → `Found 2 errors`(둘 다 기존 E501, 리팩터로 `console.py:289/:326`으로 행번호만 이동 — 원문 그대로 보존, **NEW 0**). cargo 무접촉.

**RED 증명**: 구현 전 신규 10건 중 9건 FAIL(`.moai/state/verify/m75/01-red.log`) — wire 테스트가 결함을 그대로 재현(`observed_count=3, audited_count=1, matched=0`). 나머지 1건(단일 승인)은 보존 불변식이므로 사전 green이 정상.

**수정 파일**: `server/safety/console.py`(DeploySend + ExecOutcome.sends + `_deploy_via_file_import` 분해: `_run_file_import`/`_deploy_query_state`/`_deploy_execute`), `server/safety/gate.py`(`deploy_plugin_source` fan-out), `packaging/wire_sink.py`(회계 caveat → CLOSED 갱신), 테스트 3파일(+10건). `server/safety/audit.py` **무변경**(제약 준수), `server/web`→`server.bridge` import 0 유지(AC-MVP-019 스캔 green — full suite 포함).

**@MX tags added**: `server/safety/console.py` `DeploySend` — `@MX:ANCHOR` + `@MX:REASON` + `@MX:SPEC`(per-send 레코드 계약: 레코드를 빠뜨린 왕복 = 오탐 "미감사 송신자").

**Gap/이연**: 패키지 `.app` E2E는 기존 dist가 구버전 서버 payload라 재빌드 전에는 본 변경을 실행하지 않음 — 검증은 실 스택(실 ConsoleLink + 실 UDP wire) 단위로 완결(scope의 "packaged-E2E or unit coverage" 중 unit 선택). 다음 패키징 시 Step 8은 무변경 통과 예상(E2E는 deploy를 수행하지 않음), deploy-관통 E2E 스텝 추가는 선택 과제.

**커밋**: M7.5 구현 커밋 1건(`feat/app-deploy-file-import` 직접 커밋 — 원격 없음, push/PR 없음).

### v0.5.0 스코프 축소 배치 (2026-07-22, cycle_type=tdd) — 5개 구현 단위

spec.md **v0.5.0**(2026-07-22 배포 전제 축소 — 서명·공증 DESCOPED / Windows DEFERRED / 자동 업데이트 DESCOPED / ad-hoc `.dmg` 직접 전달 신설) 직후 착수한 macOS 전용 하드닝 배치. plan.md v0.5.0은 본 배치에 **신규 마일스톤 번호를 신설하지 않았으므로**, 아래 5개 절은 각자가 확장·완결하는 기존 마일스톤의 하위 번호를 쓴다(M7.1~M7.5의 소수점 하위 마일스톤 관례 계승).

| 절 | 구현 단위 | 확장·완결 대상 | 연계 AC |
|---|---|---|---|
| **M17.1** | rig 풀 슬롯 교차언어 계약 (Lua↔Python) | M17(#3) + §E.4 v0.3.0 이연 #3 | AC-DEPLOY-020 |
| **M18.1** | OSC 수신 포트 3결함 (UDP preflight / 오류 표면화 / 셸 원인 전달) | M18(#6) + §E.4 v0.3.0 이연 #1 | AC-DEPLOY-023 (+ 026 오류 UX) |
| **M10.1** | Tauri `.app` ad-hoc 서명 실링 | M10 (배포 통합 검증) | AC-DEPLOY-030 ① |
| **M10.2** | `.dmg` 전달 아티팩트 + 한국어 설치 안내 | M10 | AC-DEPLOY-030 ②③④ |
| **M7.6** | AC-DEPLOY-028 ① 증거 (Rust 자격 저장소 미접촉 정적 스캔) | M7 (Stage-2) — 실재하던 M7 close 갭 | AC-DEPLOY-028 ① |

**테스트 수 궤적** (단위별 1회 full-suite, 명령 `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest server/tests/ -q`): baseline `1189` → M17.1 `1201`(+12) → M18.1 `1223`(+22) → M10.1 `1232`(+9) → M10.2 `1232`(문서·스크립트 전용, +0) → M7.6 `1256`(+24). **기존 테스트 삭제·약화 0건**(다섯 단위 전부).

⚠️ **본 배치 전체 커밋 상태: 미커밋.** 다섯 절 모두 작업 트리에만 존재하며 **어떤 절도 커밋 SHA를 주장하지 않는다**. `feat/app-deploy-file-import` HEAD는 여전히 `9ae9c7d`다.

#### M17.1 — rig 풀 슬롯 교차언어 계약 (2026-07-22, cycle_type=tdd)

§E.4 v0.3.0 이연 #3(“`copilot_responder.lua:322`가 루프 위치를 `i`로 방출; 갭 있는 라이브 rig에서는 진짜 풀 슬롯이 다를 수 있음”)의 **소스단 근본 수정**. M17은 Python 절(`_rig_object`가 슬롯을 노출)만 고쳤고, 슬롯 값을 **생산하는** Lua 절은 그대로였다.

**결함(교차언어 계약 위반)**: `console/lua/copilot_responder.lua` `build_snapshot`이 **루프 인덱스**를 `i`로 방출하는 한편 `server/orchestrator/tools.py:93` `_rig_object`는 `i`를 **실제 풀 슬롯**으로 문서화·소비했다. `M.safe_children`이 갭을 압축(`out[#out+1]`)하므로, 갭 있는 풀에서 LLM은 “그룹 1,2,3이 있다”고 통보받고 `Group 2 + 3`을 자신 있게 발행 → 콘솔 거부 → 자기수정 3회 소진 → **부분 실행**(`ChangeDestination Root` + `ClearAll`은 이미 나감). RED 재현 축약: `assert [1, 2, 3] == [1, 5, 7]`.

**수정(양쪽 절)**: 슬롯이 확립 가능하면 **실제 슬롯**을 방출하고, 확립 불가하면 **`i`를 아예 생략**해 `_rig_object`가 이름-전용 항목으로 degrade하도록 했다 — *fail honest, never fail confident*. responder `VERSION` 1.1.0 → 1.2.0, `console/lua/PROTOCOL.md`에 **ASSUMPTION-7** 기록.

**추적 중 발견된 두 번째(더 심각한) 결함**: `server/safety/console.py`가 동일한 `i`를 `Delete Plugin <slot>`의 **대상**으로 사용 → 갭 있는 풀에서 **무관한 플러그인을 삭제**할 수 있었다. 이제 목록 상 어느 플러그인이라도 슬롯 미보고 시 **fail closed**(`console.py:311`~`:324` — “cannot choose a free plugin slot”).

**변경 파일**: `console/lua/{copilot_responder.lua,PROTOCOL.md,copilot_responder.xml}`, `server/orchestrator/tools.py`, `server/safety/console.py` + 테스트 4파일.

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-020 ①② (rig-context가 실제 풀 번호 노출 + 미존재 오브젝트 미선택) — **Python 소비 절** | PASS | `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest server/tests/test_tools.py -q` | `23 passed` — 비연속 풀(1,2,7) 픽스처(`test_tools.py:80`)에서 `_rig_object`가 실제 슬롯 노출(`:316`), 갭 있는 rig가 `Group 3`을 만들지 않음(`:337`) |
| — **Lua 생산 절**(`build_snapshot`이 실제 슬롯 방출 / 미확립 시 `i` 생략) | PASS **(lupa 모의 콘솔 한정)** | `… -m pytest server/tests/test_lua_responder.py server/tests/test_responder_deploy.py -q` | `51 passed` — `test_gapped_pool_reports_real_slots_not_listing_positions`, `test_unestablished_slot_is_omitted_rather_than_faked`, `test_unknown_slot_reaches_the_llm_as_a_name_only_entry`, `test_self_reported_slot_wins_over_a_positional_ptr`, 밀집 풀 회귀 `test_dense_pool_still_reports_contiguous_slots` |
| — `Delete Plugin <slot>` 오대상 삭제 fail-closed (2차 결함) | PASS | `… -m pytest server/tests/test_deploy_transport.py -q` | `20 passed` — 슬롯 미보고 플러그인이 목록에 있으면 free-slot 선택 자체를 거부(예외 메시지에 미보고 건수 포함) |
| **실 grandMA3 onPC에서 슬롯이 실제로 확립되는가 (ASSUMPTION-7)** | 🔴 **PENDING LIVE VERIFICATION** | (미실행) | **주장하지 않음.** 위 세 행의 근거는 전부 `server/tests/lua_mock_env.py`의 **모의 콘솔**이다. 실 2.4.2에서 `Children()`/`Ptr(n)`이 사용 가능한 슬롯을 노출하는지는 **미검증**이며, 노출하지 않으면 responder는 (설계대로) 슬롯을 생략해 이름-전용으로 degrade한다 — 즉 라이브 실패 모드는 “틀린 슬롯”이 아니라 “슬롯 없음”이다. **필요한 온-하드웨어 검사**: onPC 2.4.2에서 **의도적으로 갭을 만든 풀**(예: Group 1, 5, 7만 존재)을 구성 → v1.2.0 responder 로드 → `get_rig_context` 1회 → 반환된 `groups` 항목의 `i` 값이 `[1, 5, 7]`인지(=슬롯 확립 성공) 또는 `i`가 **부재**한지(=degrade 경로) 확인. 두 결과 모두 계약 위반이 아니며, `[1, 2, 3]`이 나오면 수정 실패다 |

**Lint**: `.venv/bin/python -m ruff check server/ packaging/` → `Found 2 errors` — 둘 다 기존 baseline `server/safety/console.py` E501, **NEW 0**(리팩터로 행번호가 `:289`/`:326` → `:289`/`:343`으로 이동).

#### M18.1 — OSC 수신 포트 3결함 (2026-07-22, cycle_type=tdd)

M18(#6)이 브리지 단위에서 멈춰 있던 지점 + §E.4 v0.3.0 이연 #1(“`server/web`이 `ReceivePortInUseError`를 catch+display하는 배선 부재 — AC-MVP-019 import 경계와 충돌해 이연”)을 함께 닫는다.

**(a) TCP로 UDP를 재던 preflight**: `server/web/launcher.py` `probe_port_available`이 `SOCK_STREAM`(TCP)으로 바인드하는데 `serve.py`가 **UDP 수신 포트**를 그 함수에 넘기고 있었다 → 점유된 수신 포트가 preflight를 **통과**. 본 호스트에서 실측: 실 `_ReuseAddrOSCUDPServer`가 `127.0.0.1:63981`을 쥔 상태에서 **TCP 프로브는 FREE, UDP 프로브는 OCCUPIED(errno 48)**. 구현자가 함께 실측한 사실 — 정확히 같은 주소의 UDP 중복 바인드는 `SO_REUSEADDR`가 있어도 **실패**하지만, 와일드카드-vs-특정(0.0.0.0 vs 127.0.0.1) **불일치는 성공하며 거짓말을 한다**. 그래서 **UDP 프로브는 의도적으로 `SO_REUSEADDR`를 설정하지 않고**(TCP 프로브는 유지) 판정한다.

**(b) 오류가 사용자에게 도달하지 않던 경로**: `ReceivePortInUseError`가 `build_runtime()`을 **미포착 상태로 탈출**했고, 그 이중언어 `.guidance`는 `str()`로 도달 불가였다. 이제 **합성 루트**(`server/safety/bootstrap.py:143`~`:149` — 유일하게 bridge·web 양층에 의존하는 지점)에서 catch 후 `PortInUseError`로 **재raise**하고, `serve.py`가 이를 처리해 `main()`이 **exit 2**를 반환한다. `server/web` → `server.bridge` **import 0건 불변**(AC-MVP-019) — 브리지-로컬 타입이 합성 루트에서 launcher 타입으로 번역되므로 경계가 약화되지 않는다.

**(c) 셸이 모든 종료를 "runtime files missing"으로 오귀속**: `src-tauri/src/sidecar.rs`가 모든 `Terminated` 이벤트에 “runtime files are most likely missing or incomplete”를 **하드코딩**했다. 신설 `@copilot:error` 채널(`server/web/host_channel.py:45` `ERROR_PREFIX`)이 실제 원인을 실어 나르고, `sidecar.rs:495`가 이를 파싱한다 — 하드코딩 문구는 **폴백으로만** 잔존.

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| AC-DEPLOY-023 (수신 포트 선점 → 조용한 드리프트 0 + 인간 친화 안내) — **(a) UDP preflight** | PASS | `… -m pytest "server/tests/test_web_launcher.py::TestOscReceivePortIsProbedAsUdp" -q` | `7 passed` — `test_the_tcp_probe_is_blind_to_a_held_udp_receive_port`(결함 재현), `test_a_udp_probe_sees_the_held_receive_port`, `test_require_ports_available_rejects_an_occupied_receive_port`, `test_the_udp_probe_must_not_set_so_reuseaddr`(SO_REUSEADDR 미설정을 계약으로 고정), `test_port_zero_is_still_skipped_for_udp` |
| — **(b) 오류 표면화** (§E.4 이연 #1 해소) | PASS **(단위)** | `… -m pytest server/tests/test_web_serve.py -q` | `32 passed` — `ReceivePortInUseError`(`test_web_serve.py:216`~`:218`)가 `PortInUseError`로 번역되어 web 층에 도달, `serve.py:433`/`:449`가 포착해 `return 2`. import 경계 확인: `grep -rn "server.bridge" server/web/*.py` → 실코드 매치 0(`__init__.py` 산문 주석 1건뿐) |
| — **(c) 셸 원인 전달** (`@copilot:error`) | PASS | `… -m pytest server/tests/test_web_host_channel.py -q` + `.venv/bin/python packaging/rust_scan.py` + `cargo clippy --all-targets` | `15 passed`; `PASS — 8 file(s) scanned (rust=5, manifest=2, capability=1), 0 violation(s)`(exit 0); clippy `Finished dev profile`, 경고·오류 0 |
| **실 하드웨어 end-to-end 사슬** (force-quit → onPC가 포트 점유 → 재기동 → 셸이 포트 메시지 표시) | 🔴 **PENDING LIVE VERIFICATION** | (미실행) | **주장하지 않음.** 위 세 절은 각각 단위로 증명되었으나 **하나의 연속 시퀀스로 실행된 적이 없다**. **필요한 온-하드웨어 검사**: onPC 2.4.2가 앱의 수신 포트(현 사용자 설정 9005)로 OSC 출력 중인 상태에서 → 패키지 `.app`을 force-quit(SIGKILL) → onPC가 해당 UDP 포트를 계속 점유하게 두고 → `.app` 재기동 → **Tauri 셸 다이얼로그가 “runtime files missing”이 아니라 포트 점유 원인·재설정 안내를 표시**하고 백엔드가 exit 2로 종료하는지 확인. 현재 증거는 (a)(b)(c) 각각의 단위 관측뿐이다 |

**@MX tags**: `server/safety/bootstrap.py`에 `@MX:NOTE`(수신 포트 실패 번역 — 합성 루트가 브리지-로컬 타입을 launcher 타입으로 바꾸는 유일 지점) 1건.

#### M10.1 — Tauri `.app` ad-hoc 서명 실링 (2026-07-22, cycle_type=tdd)

AC-DEPLOY-030 ①(ad-hoc `.app` seal 무결)의 선행 조건. **BEFORE**: `codesign --verify --strict "src-tauri/target/release/bundle/macos/GrandMA3 Copilot.app"` → **exit 1**(“code has no resources but signature indicates they must be present”).

**정확한 근본 원인(초기 진단은 불완전했다 — 기록상 정정)**: 오케스트레이터의 최초 가설은 “서명 후 payload를 복사해 seal이 깨졌다”였으나 **불완전**했다. 실제로는 **(1) `Contents/_CodeSignature`가 아예 존재하지 않았다 — 번들은 한 번도 실링된 적이 없었다**, 그리고 **(2) 평평한 onedir payload는 구조적으로 서명 불가**했다: `codesign`은 `Contents/Frameworks` 아래를 전부 **중첩 코드**로 취급하는데, M7.4a의 payload 단계가 그 자리에 순수 데이터 디렉터리(`ui/`, `config/`, `console/`, `*.dist-info/`)를 넣었기 때문이다.

**수정**: PyInstaller 자신의 코드/데이터 분리 규약을 미러링 — Mach-O는 `Contents/Frameworks`, 데이터는 `Contents/Resources`, 상호 심링크. 이는 `dist/GrandMA3 Copilot.app`(M6 Stage-1 아티팩트)이 **이미 쓰고 있던 레이아웃**이다.

**ad-hoc 재실링을 `packaging/stage_sidecar.py --bundle` 안에 넣은 이유**: `package.json`에 4번째 단계로 추가하면 **떨어뜨릴 수 있는 링크를 하나 더 만드는 셈**이라 지금 고치려는 위험(payload가 seal 뒤에 복사되는 순서 함정)을 그대로 재생산한다. 따라서 payload→seal→verify를 **하나의 원자적 단계**로 묶었다. `packaging/sign.sh`는 **의도적으로 재사용하지 않았다** — 이 번들에서 실패하며, 그 hardened-runtime/entitlements 경로는 **공증**을 위해 존재하는데 공증은 v0.5.0에서 DESCOPED다.

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| **AC-DEPLOY-030 ①** (ad-hoc `.app` seal 무결 + ad-hoc임을 확인) | PASS (오케스트레이터 직접 재검증, 2026-07-22) | `codesign --verify --strict "src-tauri/target/release/bundle/macos/GrandMA3 Copilot.app"; codesign -dv "$APP"` | `verify_exit=0`; `Identifier=com.grandma3copilot.app`, `CodeDirectory v=20400 size=23184 flags=0x2(adhoc) hashes=718+3 location=embedded`, `TeamIdentifier=not set` |
| — 번들 payload/실링 회귀 가드 | PASS | `… -m pytest server/tests/test_deploy_tauri_shell.py server/tests/test_deploy_tauri_seams.py -q` | `76 passed` |
| — 재빌드가 stale 번들 사본을 갱신 | **부분 PASS — 4/5** | `find . -name copilot_responder.lua -not -path "./console/lua/*"` 각각을 원본과 `cmp`(2026-07-22 재실행) | **MATCH 4건**: `dist/GrandMA3 Copilot/_internal/…`, `dist/GrandMA3 Copilot.app/Contents/Resources/…`, `src-tauri/binaries/_internal/…`, `src-tauri/target/release/bundle/macos/GrandMA3 Copilot.app/Contents/Resources/…`. ⚠️ **DIFFER 1건**: `src-tauri/target/debug/_internal/console/lua/copilot_responder.lua` — 여전히 `VERSION = "1.1.0"`(M17.1 이전). **release 번들·배포 아티팩트는 전부 v1.2.0이고 stale 사본은 debug 빌드 스테이징 트리 하나뿐**이지만, `cargo`/`tauri dev` 디버그 실행은 이 사본을 집어 M17.1 이전 슬롯 동작을 재현할 수 있다 — **미해소 열린 항목** |
| **패키지 GUI 앱 실제 기동** | ⛔ **주장하지 않음 (미실행)** | — | 본 배치에서 실행한 것은 **실링된 번들의 `Contents/MacOS/copilot-backend --help` 뿐**이다. GUI 앱을 띄우지 않았으므로 창·트레이·라이브 동작에 대한 어떤 주장도 하지 않는다(M7.4a/M7.4b의 기존 라이브 증거는 **재실링 이전** 번들에 대한 것) |

#### M10.2 — `.dmg` 전달 아티팩트 + 한국어 설치 안내 (2026-07-22)

AC-DEPLOY-030 ②③④. 신규 `packaging/make_dmg.sh` + `npm run shell:package`(`package.json:13`)가 **이미 실링된 `.app`으로부터** `dist/GrandMA3-Copilot-0.4.0.dmg`(73M 번들 → 40M)를 만든다 — **`tauri build --bundles dmg` 경유는 의도적으로 배제**(M10.1이 고친 것과 동일한 순서 함정을 재현하므로).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| **AC-DEPLOY-030 ②** (`.dmg` 생성 + 미실링 입력 거부) | PASS (오케스트레이터 직접, 2026-07-22 재확인) | `npm run shell:package`; `ls -lh dist/*.dmg` | `dist/GrandMA3-Copilot-0.4.0.dmg` 40M (2026-07-21 23:45 생성) |
| **AC-DEPLOY-030 ③** (마운트→추출 후에도 seal 유지) | PASS (본 배치 오케스트레이터 검증 실행에 귀속) | 마운트 → `ditto` 추출 → `codesign --verify --strict`(추출 사본 대상) | 심링크 **27/27 보존**, 추출 사본 `codesign --verify --strict` **exit 0** |
| **AC-DEPLOY-030 ④** (한국어 설치 안내 동봉 + quarantine 해제 2경로) | PASS | `grep -n "xattr -dr com.apple.quarantine\|그래도 열기" INSTALL.ko.md` | `INSTALL.ko.md`(56행) — `:34` `xattr -dr com.apple.quarantine "/Applications/GrandMA3 Copilot.app"`, `:42` 시스템 설정 → 개인정보 보호 및 보안 → **"그래도 열기"**. quarantine을 붙이는/붙이지 않는 전달 경로 구분, macOS 15+에서 우클릭→열기가 더 이상 통하지 않는다는 사실 포함 |
| `spctl --assess --type execute` | **기대된 거부 — 결함 아님** | (본 배치 검증 실행) | **rejected, exit 3**. ad-hoc 서명 하에서 **영구적**이며 spec.md §A/§C·AC-DEPLOY-030의 “명시적 비-기준”대로 통과를 요구하지 않는다 |

`packaging/README.md`에 전체 재빌드 순서와 **순서 함정 경고**(payload를 seal 뒤에 복사하지 말 것)를 기록했다.

#### M7.6 — AC-DEPLOY-028 ① 증거 (2026-07-22, cycle_type=tdd)

**실재하던 M7 close 갭을 닫는다.** 본 단위 이전에 `grep -rn AC-DEPLOY-028`은 `acceptance.md` 밖에서 **0건**을 반환했다 — 테스트도, 증거 행도 없었다. 그런데 `acceptance.md:107`은 이 AC를 M7 close 조건으로 요구했고 스스로 “순수 로컬 자동으로 지금 완전 검증 가능”이라 분류했으며, **M7은 이미 synced로 선언된 상태였다**(§E.4 Stage-2 M7 sync).

**절 ①(Rust에 자격 저장소/키 접근 코드 0건)만이 진짜 미커버**였다 — `packaging/rust_scan.py`는 네트워크/OSC 마커만 갖고 있었다. 이제 **별도의 `credential` 불변식 클래스**를 추가했다: `keyring` / `keychain` / `Sec(Item|Keychain)\w*` / `security[_-]framework` / `keytar` / `wincred` / `Cred(Read|Write)\w*` / `secret[_-]service` + **전이 크레이트 거부**. `network` 클래스와 **분리 보고**된다.

**일반 비밀 어휘(`token`/`secret`/`password`)는 의도적으로 제외**했다 — 포함 시 정당한 launch-token 코드에서 오탐 ~30건이 발생했고, 유일한 탈출구가 **마커 집합을 무디게 만드는 것**이었기 때문이다. 마커는 좁게(자격 **저장소 API**만) 유지하고, `keyring`/`keychain`은 `\b` 없이 부분일치로 둔다(`open_keychain()` / `keyring_entry` 같은 식별자를 놓치지 않기 위해 — `rust_scan.py:97`).

절 ②③은 `server/tests/test_deploy_keystore.py`에서 **이미 green**이었고 **AC-DEPLOY-028 앵커만 부착**했다(로직·단언 무변경).

| AC | Status | Verification Command | Actual Output |
|----|--------|----------------------|---------------|
| **AC-DEPLOY-028 ①** (Rust/Tauri 소스에 자격 저장소 접근 0건 — 실트리) | PASS (오케스트레이터 직접 재실행, 2026-07-22) | `.venv/bin/python packaging/rust_scan.py` | `invariants: network (AC-DEPLOY-027 Layer ①), credential (AC-DEPLOY-028 ①)` / `PASS — 8 file(s) scanned (rust=5, manifest=2, capability=1), 0 violation(s)` (exit 0) — 헤더가 **두 불변식을 모두 명명** |
| — 비-vacuity 증명 ① (모든 마커가 발화 샘플 보유 + 역방향 가드) | PASS | `… -m pytest server/tests/test_deploy_cross_language_scan.py -q` | `50 passed` — `TestCredentialMarkerSetIsLive::test_marker_fires_on_a_canonical_sample`(파라미터화) + `test_every_declared_source_marker_has_a_sample`(샘플 없는 마커 = 실패) |
| — 비-vacuity 증명 ② (커밋된 양성 대조 픽스처) | PASS | 동일 실행 — `TestCredentialRogueFixtureIsFlagged` 3건 | `server/tests/fixtures/rust_scan/rogue_credential/`(`Cargo.toml`/`Cargo.lock`/`src/main.rs`) → **credential 8건 / network 0건**. `TestCredentialAndNetworkClassesAreDistinguishable` 2건이 두 클래스의 분리 보고를 고정 |
| — 비-vacuity 증명 ③ (실 8파일 형태 미러 + 주입 시 FAIL로 flip) | PASS | 동일 실행 — `TestRealSrcTauriCredentialGate` 3건 | `test_real_tree_credential_gate_state_is_accurate`(항상 실행), `test_real_src_tauri_tree_holds_zero_credential_access`, `test_real_tree_shape_with_an_injected_credential_read_is_flagged` — 실 8파일을 미러해 PASS 재현 후 `keyring::Entry::new(...)` **1행 주입 → FAIL로 전환**됨을 단언 |
| **AC-DEPLOY-028 ②③** (Stage-1 키 경로 무변경 + 세션 폴백 + 평문 0) | PASS (앵커 부착만, 로직 무변경) | `… -m pytest server/tests/test_deploy_keystore.py -q` | `38 passed` — 앵커: `:155`(② `inject_active_provider_key`), `:214`/`:266`(③ 저장소 미가용 + 파일 전수 스캔), `:328`(② `scrub_environ`) |

**@MX tags added**: `packaging/rust_scan.py` credential 마커 집합 위 `@MX:ANCHOR`(`:86`) — “이 프로젝트의 유일한 자격 저장소 정적 탐지기”이며 마커를 무디게 하면 조용히 vacuous해짐을 `@MX:REASON`에 명시.

## §E.3 Run-phase Audit-Ready Signal

`run_status: audit-ready` (Stage-1)
`run_complete_at: 2026-07-20`

**Stage-1 run-phase 완료** — M1~M6(설정·키 저장·설정 UI·responder provisioning·health/오류 UX·PyInstaller onedir 패키징) + M10(배포 통합 검증) 전 마일스톤 green. 전체 `983 passed` + 패키지 `.app` E2E 8/8 PASS(모두 오케스트레이터 직접 재검증). 프리즈 앱이 사용자 데이터 폴더에 실제 감사로그 기록 확인. AC 매트릭스 자동 검증 항목 전부 PASS. HEAD `1d65375`, `feat/app-deploy-file-import`(로컬 전용). **환경-게이트 N/A**(sync 시 명시): universal2·Windows x86_64·실제 Developer-ID 공증. **Stage-2(M7~M9 Tauri 셸+sidecar+자동업데이트)는 별도 kickoff** — 본 close는 Stage-1 배포 가능 MVP 형태 마감. 다음: `/moai sync SPEC-COPILOT-DEPLOY-001`(Stage-1 close).

### v0.5.0 스코프 축소 배치 run-phase 상태 (2026-07-22)

`run_status: **NOT audit-ready**`
`run_complete_at: —` (미도달)

M17.1 / M18.1 / M10.1 / M10.2 / M7.6 다섯 단위가 작업 트리에 랜딩했고 **전체 스위트 `1256 passed`**(오케스트레이터 직접 재실행, 명령 `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring .venv/bin/python -m pytest server/tests/ -q`, 로그 `.moai/state/verify/m19-progress/01-full-suite.log`, 실패 0·skip 0), `ruff check server/ packaging/` NEW 0, `packaging/rust_scan.py` PASS, `cargo clippy --all-targets` 경고 0, `.app` `codesign --verify --strict` exit 0이다. **그럼에도 본 배치는 audit-ready가 아니다** — 아래 3건 때문이다.

**미해소 항목 (audit-ready를 막는 것)**:

1. 🔴 **M17.1 라이브 미검증** — ASSUMPTION-7(실 grandMA3 `Children()`/`Ptr(n)`이 사용 가능한 슬롯을 노출하는가)이 **미검증**. 증거는 전부 `lua_mock_env.py` 모의 콘솔. 필요한 검사는 M17.1 절의 마지막 행에 명시.
2. 🔴 **M18.1 라이브 미검증** — force-quit → 포트 점유 → 재기동 → 셸 안내 표시의 **연속 사슬이 하드웨어에서 한 번도 실행된 적 없음**. 필요한 검사는 M18.1 절의 마지막 행에 명시.
3. 🟡 **알려진 flaky 테스트 (미해소 열린 항목)** — `server/tests/test_web_launcher.py::TestSidecarSelfReap::test_orphaned_sidecar_reaps_the_group_without_a_pipe`가 M10.1 작업 중 **full-suite 실행 1회에서 실패**했고, 재실행에서 통과했다. 2026-07-22 재확인: full suite `1256 passed`(해당 테스트 포함 green) + 격리 실행 **3/3 passed**(`1 passed in 0.34s / 0.43s / 0.42s`). **미화(cosmetic) 사안이 아니다** — 이 테스트는 sidecar self-reap 경로, 즉 **M18.1이 표면화하는 포트 점유 증상을 애초에 예방하는 메커니즘**을 검증한다. 간헐 실패의 근본 원인은 **미규명**이며(부하 하 타이밍 추정, 확인 안 됨) 본 배치에서 수정하지 않았다.

4. 🟡 **stale debug 스테이징 사본 1건 (본 기록 단위에서 새로 발견)** — `src-tauri/target/debug/_internal/console/lua/copilot_responder.lua`가 여전히 `VERSION = "1.1.0"`이다(M10.1 절 참조). release 번들·`dist/` 배포 아티팩트 4건은 전부 v1.2.0으로 갱신되었으나, `cargo`/`tauri dev` **디버그 실행 경로는 M17.1 이전 responder를 로드**해 고친 슬롯 결함을 재현할 수 있다. 라이브 재검증(항목 1)을 디버그 빌드로 수행하면 **잘못된 결론에 도달한다** — 라이브 검증은 반드시 release 번들로 하거나, 디버그 스테이징을 먼저 재생성해야 한다.

**커밋 상태**: 다섯 단위 전부 **미커밋**. 브랜치 `feat/app-deploy-file-import` HEAD = `9ae9c7d`(변동 없음). 원격 없음 — push/PR 없음.

## §E.4 Sync-phase Audit-Ready Signal

`sync_status: stage-1-synced` (**Stage-1 문서 동기화 — 이것은 terminal close가 아니다**)
`sync_complete_at: 2026-07-20`
`sync_commit_sha: aca6b8c`

CHANGELOG.md `[Unreleased]` 및 README.md가 Stage-1 배포 가능 arm64 macOS MVP(M1~M6 + M10)를 반영해 동기화되었다 — 인앱 설정+OS 자격 증명 저장, responder provisioning, health/오류 UX, PyInstaller onedir 패키징(빌드/실행 안내 포함), 안전 불변식 보존, 환경-게이트 N/A(universal2/Windows/실제 공증) 명시.

**중요**: 본 sync는 Stage-1 문서 동기화이며 **terminal close가 아니다**. Stage-2(M7~M9: Tauri 데스크톱 셸, Python 백엔드 sidecar 번들, 자동 업데이트, updater 재시작 안전상태 보존)가 아직 구현되지 않았으므로, SPEC frontmatter `status`는 **`in-progress`로 유지**된다(`implemented`/`completed`로 전환하지 않음 — verification-claim-integrity 원칙상 미완 마일스톤에 대한 완료 주장을 방지). `updated: 2026-07-20`으로 갱신.

terminal `completed` close(§E.4의 `in-progress → implemented → completed` merged 3-phase close)는 Stage-2(M7~M9) 구현 완료 후 별도 sync 세션에서 수행한다. 다음: Stage-2 kickoff(별도 SPEC 범위 확정) 또는 M7 착수.

### v0.3.0 라이브 E2E 하드닝 sync (2026-07-21, `status: in-progress` 유지)

`sync_status: stage-1-hardening-synced` (**여전히 Stage-1 문서 동기화 — terminal close 아님**)
`sync_complete_at: 2026-07-21`
`sync_commit_sha: dcdb6f5`

v0.3.0 라이브 E2E 하드닝 배치(결함 #2~#6, REQ-DEPLOY-028~032/AC-DEPLOY-019~023, milestones M14~M18)를 CHANGELOG.md `[Unreleased]`에 기록했다. 7개 배치 커밋(`3baadf1` 계획 fold-in, `66d1419` M14, `fe1a9d8` keyring conftest, `392f4b9` M15, `063b7ff` M16, `6152f80` M17, `3258090` M18) 전부 `feat/app-deploy-file-import` 브랜치에 반영됨. 전체 스위트 `1017 passed`(983→1017, +34 net). README.md는 이 배치로 인한 빌드/실행 절차 변경이 없어 미수정(패키징된 `.app` 빌드·구동 안내는 그대로 유효; 하드닝은 서버 내부 로직 변경).

**B12 self-test 결과**: (1) pre-emission grep `grep -c 'SPEC-COPILOT-DEPLOY-001' CHANGELOG.md` → 기존 항목 존재 확인 후 동일 SPEC 항목에 하위 불릿으로 추가(신규 중복 최상위 항목 없음); (2) AC count — acceptance.md AC-DEPLOY-019~023 5건이 CHANGELOG 항목의 M14~M18 5개 하위 불릿과 1:1 대응; (3) file path verification — `server/web/serve.py`(M14 build_runtime)·`server/deploy/keystore.py`, `server/tests/conftest.py`, `console/lua/copilot_responder.lua` 경로 확인됨(commit diff 기준; 상세 M15/M16 파일은 plan.md 범위 참조).

**Deferred items (honest audit trail, terminal close 시 재확인 필요)**:
1. **#6 앱 셸 안내 표시** — `server/bridge`가 `ReceivePortInUseError`(재설정 안내 포함)를 raise하나, `server/web`이 이를 catch+display하는 배선은 단일 OSC 관문 보안 불변식(AC-MVP-019 — `server/web`이 `server.bridge`를 import하지 않음)과 충돌 — 보안 allowlist 결정이 필요해 이연. AC-023의 자동화된 브리지-단위 스코프는 충족되었으나, end-to-end 표시는 미구현.
2. **라이브 onPC 재검증(#2~#6 전체)** — 단위 테스트는 배선/전달을 증명하나, 실하드웨어+실 Gemini 동작(TTL wire 메시지, 갭 있는 풀에서 라이브 재바인드, LLM이 스티어를 실제로 따르는지)은 하드웨어-env-gate(기존 DEPLOY-001 라이브 갭과 동일 규율).
3. **#3 심층 Lua 슬롯 정합성** — `console/lua/copilot_responder.lua:322`가 루프 위치를 `i`로 방출; 실제로 갭이 있는 라이브 rig에서는 진짜 풀 슬롯이 다를 수 있음. rig-context 포맷팅 자체는 정확하나, Lua 소스단 근본 수정은 라이브-콘솔-게이트.

**Frontmatter**: `updated: 2026-07-21`로 spec.md/plan.md/acceptance.md 프런트매터 갱신(본문 무변경); `status: in-progress` 유지(Stage-2 M7~M9 env-gate 이연 — 이 sync는 SPEC을 닫지 않음).

### Stage-2 M7 sync (2026-07-21, `status: in-progress` 유지 — terminal close 아님)

`sync_status: stage-2-m7-synced` (**Stage-2 M7 문서 동기화 — 여전히 terminal close 아님, M8/M9 Stage-2-DEFERRED**)
`sync_complete_at: 2026-07-21`
`sync_commit_sha: 7d878b9`

Stage-2 M7(Tauri v2 데스크톱 셸 — M7.1~M7.5, AC-DEPLOY-024~029)을 CHANGELOG.md `[Unreleased]`에 기록하고 README.md에 신규 "Native desktop shell — build & run" 섹션을 추가했다. M7 배치 커밋 6건(`7573e60` v0.4.0 kickoff plan fold-in + plan-audit 개선, `713da64` M7.1 `/ws` 핸드셰이크, `3cc0658` M7.2 parent-liveness watchdog, `e2814fe` M7.3 SAFETY-2 이중 스캔, `77a7308` M7.4a Tauri 셸 스캐폴드+sidecar spawn, `756cab4` M7.4b Rust group-kill+Stage-2 토큰 IPC, `858b0fd` M7.5 per-send 감사 세분화) 전부 `feat/app-deploy-file-import` 브랜치에 반영됨(원격 없음 — push/PR 없음). 전체 스위트 `1189 passed` + vitest `57 passed` + `rust_scan.py` PASS(오케스트레이터 직접 검증). 라이브 검증: 패키지된 `.app`을 실제 grandMA3 onPC 2.4.2 대상으로 사용자가 직접 구동 — health `online`, 백엔드가 설정된 UDP 9005에 바인드, 콘솔 피드백 왕복 확인(발견된 통합 결함 전부 수정: sidecar 이름 해석 ENOENT, ready-line 레이스, declared-pid 신뢰, 설정-무시-부팅, 문서 중복 로드, 허위 종료 다이얼로그, sidecar 부재 패닉).

**B12 self-test 결과**: (1) pre-emission grep `grep -c 'SPEC-COPILOT-DEPLOY-001' CHANGELOG.md` → 1(기존 항목 존재) — 동일 SPEC 항목에 신규 하위 불릿(`v0.4.0 Stage-2 M7`)으로 추가, 신규 최상위 항목 미생성; (2) AC count — acceptance.md `AC-DEPLOY-024~029` 6건이 CHANGELOG M7.1~M7.5 5개 하위 불릿(M7.4가 a/b로 분리되어 6건과 1:1 대응, M7.5는 027 Layer②로 재확인)과 대응; (3) file path verification — `server/web/app.py`, `server/web/launcher.py`, `server/web/messages.py`, `ui/src/useCopilotSocket.ts`, `server/tests/test_deploy_safety_invariants.py`, `packaging/verify_packaged_e2e.py`, `src-tauri/`(`Cargo.toml`, `tauri.conf.json`, `src/main.rs`, `src/sidecar.rs`, `src/tray.rs`, `capabilities/default.json`), `server/safety/console.py`, `server/safety/gate.py`, `packaging/wire_sink.py`, `packaging/stage_sidecar.py` 전부 `ls`로 실존 확인됨.

**이연 항목(M8/M9 Stage-2-DEFERRED, terminal close 시 별도 kickoff)**: 자동 업데이트(M8, 매니페스트/아티팩트 호스팅 + updater 서명 키 — F6 미해소), 코드 서명/공증(M9, 서명된 sidecar의 keychain 도달성 재검토 포함). `sync_commit_sha`는 본 커밋 이후 별도 백필 커밋으로 채운다(자기참조 해시 불가 — SHA placeholder backfill exemption per spec-frontmatter-schema.md).

**Frontmatter**: `updated: 2026-07-21`(변경 없음 — 이미 오늘 날짜) 유지; `status: in-progress` 유지(M8/M9 미구현 — verification-claim-integrity 원칙상 terminal completion 주장 금지).

## §F Phase 4 Mode Selection

Decision (all run scopes to date): **sub-agent** (Mode 5) — sequential `manager-develop` per milestone. Mode 5 was re-selected unchanged at every scope below; no scope has met the Mode 4 (parallel) or Mode 6 (workflow) entry conditions.

This section is a **per-run-scope log** — one entry per run scope entered. Entry 1 is the original Stage-1 record (preserved verbatim); entries 2 and 3 were backfilled on 2026-07-22 because the section had gone stale (it still read "Stage-1 only (M1~M6) / Rust·Tauri deferred to Stage-2" after the M7 run had already executed).

### Entry 3 — v0.5.0 스코프 축소 배치 (2026-07-22, 현재)

- **Run scope**: macOS 전용 하드닝 5개 단위 — M17.1(Lua↔Python rig 슬롯 계약) / M18.1(OSC 수신 포트 3결함) / M10.1(`.app` ad-hoc 실링) / M10.2(`.dmg` + 한국어 안내) / M7.6(AC-DEPLOY-028 ① 증거).
- **Scope 전제**: spec.md **v0.5.0**(2026-07-22) — 서명·공증 ⛔DESCOPED, 자동 업데이트 ⛔DESCOPED, Windows ⏸️DEFERRED, ad-hoc `.dmg` 직접 전달 🆕신설. 따라서 **M8·M9은 계획·구현 대상이 아니며**, 남은 경로는 M7 이후 곧바로 M10이다.
- **Input parameters**: tier L / 파일 언어 혼합 = Python + **Lua** + **Rust** + shell + 문서 / 도메인 3(백엔드 Python, 콘솔 Lua, 패키징·Rust 셸) / 단위 간 순차 의존(M10.2는 M10.1의 실링 산출물에 의존) / concurrency benefit LOW(coding-heavy).
- **Mode evaluation**: 1 trivial = no(다중 파일·의미 변경) / 2 background = no(write-heavy) / 3 agent-team = no(RETIRED) / 4 parallel = no(coding-heavy + 단위 순차 의존) / 5 sub-agent = **YES** / 6 workflow = no(≥30파일 균일 기계 변환 아님).
- **Decision**: **sub-agent** (Mode 5). 단위별 순차 `manager-develop`(cycle_type=tdd), 각 단위 후 오케스트레이터 직접 재검증(full suite 1회/단위). 본 progress.md 기록 단위 역시 동일 모드.
- **커밋 전략**: 다섯 단위 **전부 미커밋**(작업 트리 전용). 원격 없음 — push/PR 없음.

### Entry 2 — Stage-2 M7 (2026-07-21, backfill)

- **Run scope**: M7.1(핸드셰이크) → M7.2(watchdog) → M7.3(교차언어 이중 스캔) → M7.4a(Tauri 스캐폴드) → M7.4b(group-kill + 토큰 IPC) → M7.5(per-send 감사). **M8·M9은 당시 Stage-2-DEFERRED**(이후 v0.5.0에서 DESCOPED로 전환).
- **File language mix**: Python + TS/React + **Rust/Tauri**(본 저장소 최초 Rust — Entry 1의 "Rust/Tauri deferred to Stage-2"가 여기서 해소됨).
- **Decision**: **sub-agent** (Mode 5) — 하위 마일스톤 단위 순차 `manager-develop`(cycle_type=tdd). 근거는 Entry 1과 동일(coding-heavy + 하위 마일스톤 순차 의존: M7.4b는 M7.4a 스캐폴드에, M7.5는 M7.3 reconciler에 의존).
- **Progression**: 마일스톤별 보고 + 오케스트레이터 직접 재검증, blocker/결정 시에만 정지.

### Entry 1 — Stage-1 (2026-07-20, 원본 기록 — 수정하지 않음)

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
