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

_<pending run-phase M2~M6>_

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
