---
id: SPEC-COPILOT-DEPLOY-001
title: "Phase 2: 배포 가능한 앱 형태 — PyInstaller 로컬 런처 → Tauri 데스크톱 앱 (macOS/Windows)"
version: "0.3.0"
status: in-progress
created: 2026-07-20
updated: 2026-07-21
author: manager-spec
priority: P1
phase: "Phase 2 — 배포·제품화 (v1.0.0 target)"
module: "packaging/, server/, ui/"
lifecycle: spec-anchored
tags: "packaging, pyinstaller, tauri, desktop-app, code-signing, notarization, auto-update, keychain, credential-storage, settings-ui, cross-platform, macos, windows, deployment"
tier: L
depends_on: [SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-DEPLOY-001 — Phase 2: 배포 가능한 앱 형태 (PyInstaller 로컬 런처 → Tauri 데스크톱 앱)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-20 | manager-spec | 최초 작성 (draft). 기능이 검증된 MVP(SPEC-COPILOT-MVP-001)를 최종 사용자(조명 오퍼레이터)용 설치·배포 가능한 앱 형태로 전환하는 SPEC. 합의된 2단계(패키징 Stage 1 PyInstaller onefile 런처 → Stage 2 Tauri v2 데스크톱 앱, Electron은 대안 문서화) + 배포 셸이 만족해야 할 6대 크로스컷 요구(인앱 설정 UI + OS 자격 증명 저장, responder provisioning, health UI, 코드 서명·공증, 자동 업데이트, 오류 UX)를 GEARS 요구사항으로 정의. **핵심 HARD 제약**: onPC와 동일 머신 로컬 구동 — 순수 클라우드/SaaS 형태는 out of scope. 다음 세션 구현 대상. |
| 0.2.0 | 2026-07-20 | manager-spec | Plan-audit fold-in (PASS-WITH-DEBT ~0.79). AC-014 ③ 구체화(SAFETY-1: OSC 송신 표면 allowlist + 스캔 메커니즘/패턴 + Python·Rust 전 언어 + fail-closed + wire-level 열거), REQ-006a([Unwanted] 자격 저장소 미가용/잠금/거부 시 평문 금지·세션 한정 폴백 — GEARS-1/TRACE-3)·REQ-027([Event-driven] updater 재시작 시 라이브 잠금/승인 대기/감사 로그 보존 — SAFETY-4) 신설, REQ-004 "(또는 동일 LAN)" 삭제·[Unwanted]/[Ubiquitous] 분리(TRACE-1/GEARS-3), REQ-015 검증 가능 서명 행위로 재작성·SmartScreen를 §C 제약으로 이동(GEARS-2/FEAS-7), REQ-011↔024 Import Plugin 정합(SAFETY-3). 사전 확정 결정 반영: AppName "GrandMA3 Copilot"/번들 식별자 com.grandma3copilot.app, macOS universal2(min 12)+Windows x86_64, onedir(FEAS-1/6/M13), 서명 파이프라인만 작성(인증서 부재 N/A), TOML config, keyring Python 직접 접근, 배너 온보딩, MVP 포트 재사용, 텔레메트리 0·크래시 env-scrub. §F 재작성: 6 resolved + 2 Stage-2-deferred(F5 보안 축 추가, F6). 다음 세션 구현 대상. |
| 0.2.1 | 2026-07-20 | manager-spec | M6 착수 중 발견 사항 반영 (mid-run 기록, D-NEW-1). 빌드 호스트 CPython이 **arm64 전용**임이 확인되어 **universal2(arm64+x86_64) 및 Windows x86_64는 현재 빌드 호스트에서 환경-게이트 N/A**로 전환 — 서명 env-gate(§A.6 F7, AC-DEPLOY-009/010)와 **동일 규율**(research.md §C.6/§E-2). universal2는 universal2 CPython + `_pydantic_core`/`jiter` universal2 wheel이, Windows는 Windows 러너가 필요하며 현재 arm64 전용 호스트에 부재. **macOS arm64 아티팩트는 지금 빌드·검증**한다. 패키징 파이프라인은 **코드 변경 없이**(`PYI_TARGET_ARCH=universal2` env / Windows 러너) 두 대상을 활성화하므로, universal2/Windows는 **폐기가 아니라 적합한 빌드 환경으로 이연된 목표**다. 근본 결정(onedir·universal2·Windows 대상 자체)은 **불변** — §A 대상 아키텍처 서술 + acceptance.md DoD(Stage 1/2 빌드) + AC-DEPLOY-009 이중 게이트 명시만 수정. |
| 0.3.0 | 2026-07-20 | manager-spec | **라이브 E2E 하드닝 fold-in (mid-run, D-NEW-1 계열).** 실제 grandMA3 onPC 2.4.2 하드웨어 + 실제 Gemini 라이브 데모(2026-07-20)에서 **983-test 단위 스위트가 놓친 통합 결함 6건** 발견 — 이 결함들은 하드웨어 + LLM + 패키지 번들이 결합될 때만 발현하여 단위 테스트에 불가시했다. provenance: 프로젝트 메모리 `copilot-live-demo-findings`(라이브 데모 발견 6건 기록). **#1**(`build_runtime`이 settings/provision 라우터를 미조립 → `/api/*` 미마운트 404/405)은 이미 **commit `1d65375`에서 수정**되어 본 개정에서는 기록만 한다. **#2~#6은 신규 하드닝 스코프**로 GEARS 요구 5건(REQ-DEPLOY-028~032) + 수용 기준 5건(AC-DEPLOY-019~023) + Stage-1 Hardening 마일스톤(plan.md §C, M14~M18) 신설: **#2**(기동 시 활성 프로바이더 키 미주입 → 신규 인스턴스가 키 없이 기동해 "No API key" 실패, **구현 최우선**)→REQ-028/AC-019/M14, **#4**(직전 생성 연출 상태 미추적 → 후속 수정이 Seq 71/Exec 201 대신 오대상)→REQ-030/AC-021/M15, **#5**(Gemini CachedContent 만료 미복구 + "No API key" 오분류)→REQ-031/AC-022/M16, **#3**(LLM 그룹 매핑 부정확 → 존재하지 않는 Group 3 선택 "Illegal object")→REQ-029/AC-020/M17, **#6**(OSC 수신 포트 조율 취약 → 앱 사망 시 onPC가 포트 점유해 재기동 `Address already in use`)→REQ-032/AC-023/M18. 도메인 구분: #2·#6=deploy-shell, #3·#4·#5=LLM/orchestrator(모두 DEPLOY-001 Stage-1 하드닝 스코프). **status: in-progress 유지** — Stage-2(Tauri M7~M9)는 env-gate 이연 상태로 미변경. 0.2.0/0.2.1 mid-run fold-in 관례 계승. |

## A. 개요

본 SPEC은 grandMA3 AI 코파일럿을 **최종 사용자(조명 오퍼레이터)가 설치·실행할 수 있는 배포 가능한 앱 형태**로 전환하는 작업을 정의한다. 코파일럿의 **기능은 이미 SPEC-COPILOT-MVP-001에서 구현·검증**(패칭·큐 프로그래밍·페이저/루프 이펙트·컨셉→연출 라이브 E2E)되었으며, 본 SPEC은 그 위에 **배포 셸(distribution shell)** 을 씌운다 — 기능 변경이 아니라 형태(packaging) 부여다.

현재 상태: 앱은 패키징된 배포 형태가 없다. 소스에서 venv + `python -m server.web`(`server/web/serve.py`)로만 구동되며, LLM 키·포트·플러그인 디렉터리는 CLI 인자/환경 변수로 주입한다. 터미널 없이 실행할 수 없다.

### ⚠️ 핵심 HARD 제약 — 로컬 공존(local co-location)

[HARD] 앱은 onPC와 **동일 머신(same-machine)** 에서 로컬 구동되어야 한다. 근거는 아키텍처에 내재한다:

- **OSC는 localhost UDP**다 (`127.0.0.1` 송신 콘솔 포트 / 수신 피드백 포트) — 원격/타 머신 실행이면 UDP 왕복 지연·유실이 라이브 쇼 신뢰성을 파괴한다. `127.0.0.1` 전용 바인딩은 동일 머신 구동을 전제한다(AC-DEPLOY-002 검증).
- **플러그인 배포는 로컬 파일시스템 공유**에 의존한다 — 앱이 onPC 플러그인 라이브러리 폴더(`~/MALightingTechnology/gma3_library/datapools/plugins`)에 네이티브 XML을 쓰고 `Import Plugin`을 실행한다. 이 폴더는 콘솔 PC의 **로컬** 경로다 (원격 파일 전송 채널 없음).
- **라이브 쇼 제어는 저지연·고신뢰**가 필수다.

**따라서 순수 클라우드/SaaS 형태는 본 SPEC의 out of scope다** (§D). 배포 형태는 콘솔 PC에 로컬 설치되는 앱이다. (TRACE-1: 초안의 "동일 LAN" 허용 표현은 `127.0.0.1` localhost-UDP 아키텍처·로컬 파일시스템 공유·§D 원격 콘솔 제외와 모순이므로 삭제 — 동일 머신 전용으로 확정.)

### 사전 확정 사실 (합의된 접근 — 재질의 금지)

- **패키징 Stage 1 (MVP 형태): PyInstaller onefile 자체완결 로컬 런처.** Python 백엔드가 빌드된 프론트엔드(`ui/dist`)를 정적 자산으로 서빙하고, 더블클릭 실행 시 로컬 서버를 기동한 뒤 기본 브라우저를 로컬 UI로 연다. 가장 빠른 배포 아티팩트 경로 — 기존 Python 백엔드 + 웹 SPA를 실질적으로 무변경 재사용한다.
- **패키징 Stage 2 (제품 형태): Tauri v2 데스크톱 앱.** 동일 웹 프론트엔드를 네이티브 창에 래핑하고 PyInstaller로 빌드한 Python 백엔드를 sidecar 프로세스로 번들한다 (네이티브 창, 트레이, 연결 상태, 자동 업데이트). **Electron은 대안(JS 전용 툴체인 선호 시, 번들 크기 증가)** 으로 문서화하되 **Tauri가 권장 primary**다.
- **로컬 공존 HARD 제약** (위) 는 두 Stage 모두에 적용된다.
- **기능 무변경**: 코파일럿의 도구·LLM·안전 게이트·룰북은 SPEC-COPILOT-MVP-001에서 확정된 그대로다. 본 SPEC은 셸만 추가한다.
- **안전 불변식 보존**: 배포 셸은 SPEC-COPILOT-MVP-001의 안전 게이트 불변식(REQ-MVP-029 단일 관문, 라이브 잠금, 승인 게이트, 감사 로그)을 우회·약화하지 않는다.
- **대상 플랫폼: macOS + Windows** (Linux는 §D out of scope).

**Plan-audit fold-in (v0.2.0) 확정 결정 — Implementation Kickoff에서 해소됨:**

- **앱 정체성**: AppName = **"GrandMA3 Copilot"**, reverse-DNS 번들 식별자 = **`com.grandma3copilot.app`**. 이 번들 식별자는 config 경로·Keychain 서비스명·Tauri identifier·코드 서명 identity의 앵커다. ⚠️ **"GrandMA3"는 MA Lighting의 상표**이므로, 공개 배포 전 중립적 리네이밍이 필요할 수 있다 — 번들 식별자는 코드 서명 앵커이므로 리네이밍은 조기 확정이 바람직하다.
- **대상 아키텍처**: macOS **arm64** 아티팩트는 이 빌드 호스트에서 **지금 빌드·검증**한다. **universal2**(arm64 + x86_64, 최소 macOS 12) **및** Windows **x86_64**는 현재 빌드 호스트에서 **환경-게이트 N/A**로 둔다 — 이 호스트의 CPython이 **arm64 전용**이라 PyInstaller가 universal2를 emit할 수 없고(universal2 CPython + `_pydantic_core`·`jiter`의 universal2 wheel 필요), Windows 러너도 부재하기 때문이다(research.md §C.6·§E-2). 서명 env-gate(§A.6 F7)와 **동일 규율**로, **패키징 파이프라인 코드는 작성**하되 universal2/Windows 출력은 적합한 빌드 환경 확보 전까지 환경-게이트로 둔다. 파이프라인은 **코드 변경 없이**(`PYI_TARGET_ARCH=universal2` env / Windows 러너) 두 대상을 활성화한다. **조명 노트북 Intel 대응은 폐기가 아니라 이연** — universal2 대상은 유지되며 universal2/Windows 빌드 환경으로 연기된 목표다.
- **패키징 형태: onedir**(onefile 아님) — 두 플랫폼 모두. 근거: onefile `_MEI` dylib 추출이 macOS hardened runtime/library-validation과 충돌(공증 거부 대표 원인)하고, signed .app 내부 onefile sidecar 서명이 난해하다 (FEAS-1/FEAS-6/DECIDE-M13). macOS는 onedir 트리를 notarizable **.app/.dmg 컨테이너**에 담는다(bare Mach-O 아님).
- **코드 서명**: 인증서 미보유 → 서명/공증 **파이프라인 코드는 작성**하되, AC-DEPLOY-009/010은 인증서 확보 전까지 **환경-게이트 N/A**로 둔다. 인증서 유형 결정 사실은 §C·plan.md §A.6에 기록(OV vs EV, 2023.6+ 코드서명 키의 FIPS-140 하드웨어토큰/클라우드 HSM 필수, macOS notarytool 크리덴셜, hardened runtime + entitlements + stapling — FEAS-3/FEAS-7/DECIDE-M7).
- **설정 포맷: TOML**(기존 stdlib `tomllib` 로더 재사용, 의존성 0). UI↔백엔드 config 스키마 계약은 M1에서 확정.
- **키 저장: keyring 승인** — Stage 1은 **Python 백엔드가 keyring에 직접 접근**. Stage 1/2 공통 키 인터페이스는 Stage-2 kickoff로 **이연**.
- **최초 실행 온보딩: 배너/배지 안내**(강제 마법사 아님).
- **기본 OSC/웹 포트**: MVP `serve.py` 기본값 재사용(포트 드리프트 방지 — DECIDE-M9).
- **텔레메트리: 없음** — 로컬 로그만. 크래시 덤프/예외 로거는 **프로세스 env를 스크럽**한다(API 키의 디스크 평문 유출 방지 — DECIDE-M6, AC-DEPLOY-004 보호).

## B. 요구사항 (GEARS)

### B.1 배포 형태 (packaging form)

- **REQ-DEPLOY-001** [Ubiquitous] — The 배포 산출물 **shall** 터미널·venv 없이 실행 가능한 단일 자체완결 아티팩트로 최종 사용자에게 제공된다 (Stage 1: PyInstaller onefile 실행 파일; Stage 2: Tauri 네이티브 앱 번들/인스톨러).
- **REQ-DEPLOY-002** [Event-driven] — **When** 사용자가 앱을 실행하면, the 런처 **shall** 로컬 백엔드 서버를 기동하고 로컬 UI를 표시한다 (Stage 1: 로컬 서버 기동 후 기본 브라우저를 로컬 UI URL로 오픈; Stage 2: 네이티브 창에 UI 표시 + 백엔드 sidecar 기동).
- **REQ-DEPLOY-003** [Ubiquitous] — The 백엔드 **shall** 빌드된 프론트엔드(`ui/dist`)를 정적 자산으로 서빙한다 — 별도 개발 서버 없이 (기존 `serve.py --ui-dist` 경로 재사용).
- **REQ-DEPLOY-004** [Unwanted] — The 배포 형태 **shall not** 원격 클라우드/SaaS 백엔드 실행에 의존한다. (핵심 HARD 제약 — §A)
- **REQ-DEPLOY-004a** [Ubiquitous] — The 앱 **shall** onPC와 **동일 머신(same-machine)** 에서 로컬 구동되며, OSC는 `127.0.0.1` localhost UDP를, 플러그인 배포는 콘솔 PC의 로컬 파일시스템 경로를 사용한다. (TRACE-1: 초안의 "동일 LAN" 표현 삭제 — localhost-UDP·로컬 파일시스템 공유·§D 원격 콘솔 제외와 정합. GEARS-3: [Unwanted] 클라우드 미의존 절과 [Ubiquitous] 로컬 공존 절을 분리.)

### B.2 인앱 설정 UI + 보안 자격 증명 저장

- **REQ-DEPLOY-005** [Ubiquitous] — The 앱 **shall** 터미널 없이 `GEMINI_API_KEY`(및 `ANTHROPIC_API_KEY`), OSC 포트(콘솔 송신 포트·피드백 수신 포트), 플러그인 임포트 디렉터리를 읽고 저장하는 인앱 설정 UI를 제공한다.
- **REQ-DEPLOY-006** [Ubiquitous] — The API 키 **shall** OS 자격 증명 저장소(macOS Keychain / Windows Credential Manager)에 저장된다 — 커밋 가능한 평문 파일에 절대 저장하지 않는다. (Secured 제약)
- **REQ-DEPLOY-006a** [Unwanted] — **When** OS 자격 증명 저장소가 미가용·잠금·접근 거부 상태이면, the 앱 **shall not** API 키를 평문 디스크에 저장한다; 대신 명시적 오류를 표면화하고 세션 한정(in-memory) 키 입력을 제공한다. (평문 유출 최대 위험지점 방어 — GEARS-1/TRACE-3; 정상경로 스캔이 건드리지 않는 실패 분기를 REQ로 앵커링)
- **REQ-DEPLOY-007** [Event-driven] — **When** 앱이 LLM 프로바이더 클라이언트를 기동하면, the 앱 **shall** OS 자격 증명 저장소에서 API 키를 조회하여 백엔드 프로세스 환경 변수로만 주입한다 — 기존 프로바이더 config 로더의 credential-like 키 거부 제약(SPEC-COPILOT-MVP-001 Secured)을 그대로 유지한다.
- **REQ-DEPLOY-008** [Ubiquitous] — The 비민감 설정(OSC 포트, 플러그인 임포트 디렉터리, 활성 프로바이더 선택) **shall** OS별 표준 사용자 설정 경로(예: macOS `~/Library/Application Support/…`, Windows `%APPDATA%\…`)에 저장되며, 자격 증명은 포함하지 않는다.

### B.3 CopilotResponder provisioning

- **REQ-DEPLOY-009** [Ubiquitous] — The 앱 **shall** CopilotResponder Lua 플러그인(`console/lua/copilot_responder.lua` + 네이티브 임포트 XML)을 배포 아티팩트에 번들로 포함한다.
- **REQ-DEPLOY-010** [Event-driven] — **When** 사용자가 responder 설치를 요청하면, the 앱 **shall** 번들된 플러그인 파일을 onPC 플러그인 라이브러리 디렉터리(REQ-DEPLOY-005의 설정값)로 설치/복사한다.
- **REQ-DEPLOY-011** [Ubiquitous] — The 앱 **shall** 사용자가 onPC에서 플러그인을 로드하고 onPC OSC 출력을 앱의 피드백 수신 포트로 설정하도록 안내하는 가이드 UI를 제공한다.
- **REQ-DEPLOY-011a** [Event-driven] — **When** 앱이 (구현된 "deploy verb→file+Import" 메커니즘에 따라) provisioning의 일부로 `Import Plugin` 콘솔 실행을 **직접 발행**하면, the 앱 **shall** 그 실행을 SPEC-COPILOT-MVP-001의 **단일 안전 관문(REQ-MVP-029)을 경유**시키고 **감사 로그에 1:1로 기록**한다 — 파일시스템 복사만 게이트 밖에서 수행되고, 콘솔로 향하는 어떤 OSC 실행도 게이트를 우회하지 않는다. (SAFETY-3: REQ-011 "수동 로드" 서술 ↔ REQ-024 괄호 ↔ 실제 구현 불일치 해소)

### B.4 연결/상태 표시 (health UI)

- **REQ-DEPLOY-012** [State-driven] — **While** 앱이 구동 중인 동안, the UI **shall** 기존 HealthMonitor 상태(`online` / `console_offline` / `responder_degraded`)를 사용자에게 표면화한다.
- **REQ-DEPLOY-013** [Event-driven] — **When** health 상태가 전이되면, the UI **shall** 새 상태를 즉시 반영한다 (기존 heartbeat·status 푸시 경로 재사용).

### B.5 코드 서명 + 공증 (notarization)

- **REQ-DEPLOY-014** [Ubiquitous] — The macOS 배포 산출물 **shall** Developer ID로 서명·공증(notarization)되어, Gatekeeper에 의해 "미확인 개발자" 사유로 실행이 차단되지 않는다.
- **REQ-DEPLOY-015** [Ubiquitous] — The Windows 배포 산출물 **shall** 유효한 Authenticode 서명을 보유하며, 이는 `signtool verify /pa`로 검증 가능하다. (GEARS-2/FEAS-7: 초안의 "SmartScreen 경고 없이(또는 완화되어)"는 정의되지 않은 임계값이고 OV 서명으로는 달성 난망이므로 검증 가능한 서명 행위로 재작성. SmartScreen 결과 및 OV(평판 누적 전 미해소)-vs-EV(즉시 신뢰) 의존은 §C 제약/전제로 이동.)

### B.6 자동 업데이트

- **REQ-DEPLOY-016** [Capability gate] — **Where** 데스크톱 앱(Stage 2) 형태인 경우, the 앱 **shall** Tauri updater로 자동 업데이트(버전 확인 → 다운로드 → 사용자 승인 후 적용)를 제공한다. Stage 1(PyInstaller 런처)에서는 자동 업데이트를 **버전 확인 + 알림(수동 재설치 안내)** 로 한정한다 (명시적 트레이드오프).
- **REQ-DEPLOY-017** [Event-driven] — **When** 업데이트 아티팩트가 다운로드되면, the 앱 **shall** 서명(무결성) 검증을 통과한 아티팩트만 적용한다. 검증 실패 시 적용을 차단하고 현재 버전을 유지한다. (Secured)
- **REQ-DEPLOY-027** [Event-driven] *(Stage-2 관련)* — **When** 자동 업데이트가 백엔드를 재시작하면, the 앱 **shall** 라이브 잠금(live-lock=ON)과 대기 중 승인(pending-approval) 상태를 재시작 후에도 보존한다(또는 안전측으로 재잠금(fail-safe to locked))하고, 재시작 경계를 가로질러 **감사 로그 연속성**을 유지한다. (SAFETY-4: Stage-2 updater는 MVP persistent-server에 없던 백엔드 재시작 능력을 추가 — 재시작이 live-lock을 기본 unlocked로 초기화하면 활성 보호가 조용히 소실되므로 앵커링. REQ-DEPLOY-025의 정상 종료 정리와 별개로, updater 유발 재시작의 안전상태 지속성을 규정.)

### B.7 오류 UX (인간 친화적 안내)

- **REQ-DEPLOY-018** [Event-driven] — **When** 콘솔 오프라인(`console_offline`)이 감지되면, the UI **shall** 스택 트레이스가 아닌 인간 친화적 한국어 안내(원인 + 조치 — 예: "onPC가 실행 중인지, OSC 입력이 켜져 있는지 확인")를 표시한다.
- **REQ-DEPLOY-019** [Event-driven] — **When** CopilotResponder가 로드되지 않은 것으로 감지되면(`responder_degraded` 또는 responder 미응답), the UI **shall** responder 로딩 및 onPC OSC 출력 포트 설정을 안내한다.
- **REQ-DEPLOY-020** [Event-driven] — **When** API 키가 없거나 유효하지 않으면, the UI **shall** 설정 UI로 안내하는 인간 친화적 메시지를 표시한다 — raw SDK 오류 원문을 노출하지 않는다 (SPEC-COPILOT-MVP-001 REQ-MVP-044 오류 표면 정제의 계승·확장).

### B.8 크로스플랫폼 + 재현 가능 빌드

- **REQ-DEPLOY-021** [Ubiquitous] — The 빌드 파이프라인 **shall** macOS와 Windows 양 플랫폼용 배포 아티팩트를 재현 가능하게 생성한다 — 문서화된 빌드 절차 + 의존성 버전 핀(lockfile: `uv.lock` / `ui/package-lock.json` / Stage 2 Cargo/Tauri 락) 기준. (SPEC-COPILOT-MVP-001 REQ-MVP-043의 계승·확장)
- **REQ-DEPLOY-022** [Unwanted] — The 배포 아티팩트·빌드 절차 **shall not** 비공개 자원(수동 배포 번들, 베타 신청 등)에 의존한다.

### B.9 안전 불변식 보존 (배포 셸이 안전 게이트를 우회하지 않음)

- **REQ-DEPLOY-023** [Ubiquitous] — The 배포 셸(런처/데스크톱 래퍼/설정 UI/자동 업데이트) **shall** SPEC-COPILOT-MVP-001의 안전 게이트 불변식(REQ-MVP-029 단일 관문, 라이브 잠금, 승인 게이트, 감사 로그)을 우회하거나 약화시키지 않는다 — 배포 형태는 동일 백엔드를 감쌀 뿐 OSC 송신 표면에 새 경로를 추가하지 않는다.
- **REQ-DEPLOY-024** [Unwanted] — The 설정 UI·responder provisioning·자동 업데이트 경로 **shall not** 안전 게이트를 경유하지 않고 콘솔로 명령을 전송한다. (responder provisioning은 플러그인 파일의 로컬 파일시스템 복사와 — 앱이 `Import Plugin` 콘솔 실행을 직접 발행하는 경우 — REQ-DEPLOY-011a에 따라 단일 안전 관문 경유 + 감사 로그 기록을 수반한다. 파일 복사만 게이트 밖이고, 콘솔로 향하는 OSC 실행은 예외 없이 게이트를 경유한다.)

### B.10 앱 수명주기 (로컬 서버 프로세스 관리)

- **REQ-DEPLOY-025** [Event-driven] — **When** 사용자가 앱을 종료하면, the 앱 **shall** 로컬 백엔드 서버(및 Stage 2 sidecar 프로세스)를 정상 종료(graceful shutdown)하고 열린 포트·OSC 리스너·백그라운드 태스크(heartbeat/backup 타이머)를 정리한다.
- **REQ-DEPLOY-026** [Event-driven] — **When** 지정된 OSC 또는 웹 포트가 이미 사용 중이면, the 앱 **shall** 인간 친화적 오류 + 포트 재설정 안내를 표시하고, 임의의 다른 포트로 **조용히 폴백하지 않는다** (사용자가 onPC OSC 출력을 특정 포트로 맞추므로 — OSC 포트 드리프트 방지).

### B.11 라이브 E2E 하드닝 (v0.3.0 fold-in — 실제 하드웨어+LLM+패키지 번들 결합 결함)

> 실제 onPC 2.4.2 + 실제 Gemini 라이브 데모(2026-07-20)에서 983-test 단위 스위트가 놓친 통합 결함 6건 발견(provenance: `copilot-live-demo-findings`). #1(`build_runtime` 라우터 미조립 → `/api/*` 미마운트)은 commit `1d65375`에서 **이미 수정**되어 아래에 기록만 한다. #2~#6은 신규 하드닝 요구다. 도메인 구분: #2·#6=deploy-shell, #3·#4·#5=LLM/orchestrator (모두 DEPLOY-001 Stage-1 하드닝 스코프). 기능 무변경 원칙(§A) 하에서 **셸/배선/프롬프트 정합 수준의 하드닝**이며 코파일럿 도구·안전 게이트·룰북 규칙은 불변이다.
>
> **[이미 수정 — 기록 전용] 결함 #1** — 패키징된 앱의 `build_runtime`이 settings/provision 라우터를 조립하지 않아 `/api/*`가 미마운트(404/405)되던 결함. **commit `1d65375`에서 수정 완료** — 본 개정은 신규 요구를 앵커링하지 않고 이력만 남긴다.

- **REQ-DEPLOY-028** [Event-driven] *(#2 — deploy-shell, 구현 최우선)* — **When** 패키징된 앱이 기동하여 백엔드 런타임을 구성하면(LLM 프로바이더 클라이언트 생성 **이전**), the 앱 **shall** OS 자격 증명 저장소의 **활성 프로바이더 키를 백엔드 프로세스 env로 주입**한다 — 단, **이미 설정된 env 키는 보존**(덮어쓰지 않음)하고, 저장소 미가용·잠금·거부 상태에서는 REQ-DEPLOY-006a의 세션 한정(in-memory) 폴백을 따르며 평문 디스크 저장을 하지 않는다. (라이브 E2E 결함: 기존 키 주입 경로가 `POST /api/keys` 단독이라 **신규 인스턴스가 키 없이 기동 → "No API key" 실패**. REQ-DEPLOY-007의 "프로바이더 기동 시 조회·주입"을 **기동-시점(startup) 주입**으로 구체화·강화.)
- **REQ-DEPLOY-029** [State-driven] *(#3 — LLM/orchestrator)* — **While** LLM이 rig-context(`get_rig_context` 출력)를 근거로 대상 오브젝트(그룹 등)를 선택하는 동안, the 앱 **shall** rig-context/프롬프트에 **실제 풀 번호(pool number)와 이름을 명시**하여, 위치 인덱스(positional index)와 실제 풀 번호의 혼동으로 **존재하지 않는 오브젝트를 선택("Illegal object")하지 않도록** 한다. (라이브 E2E 결함: 모호한 지시가 존재하지 않는 `Group 3`을 선택해 "Illegal object" 실패 — 명시적 대상 `Fixture 11 Thru 19`는 성공.)
- **REQ-DEPLOY-030** [State-driven] *(#4 — LLM/orchestrator)* — **While** 직전에 생성된 연출(시퀀스/실행기)이 세션에 존재하는 동안, the 앱 **shall** 그 **마지막 생성 시퀀스/실행기 상태**(예: `Seq 71` / `Exec 201`)를 **세션 컨텍스트에 주입**하여, 후속 수정 지시("더 느리게")가 실제 대상이 아닌 임의 대상(`Seq 1..100` / `Exec 1`)을 겨냥하지 않도록 하고, **맹목적 수정(blind edit)보다 재생성(regeneration)을 선호**한다. (라이브 E2E 결함: 방금 만든 룩의 상태가 미추적되어 후속 편집이 오대상을 겨냥해 실패.)
- **REQ-DEPLOY-031** [Unwanted] *(#5 — LLM/orchestrator)* — **When** Gemini 컨텍스트 캐시(rig/rulebook `CachedContent`) 만료로 `403 PERMISSION_DENIED "CachedContent not found"`(또는 404)가 감지되면, the 앱 **shall not** 재생성 없이 호출을 그대로 실패시킨다; 대신 **캐시를 재생성하여 재시도**하고, `"No API key"`(`ValueError`)를 `unexpected`가 아닌 **인증(auth) 오류로 분류**한다(오류 분류에 캐시/키 케이스 추가). (라이브 E2E 결함: 캐시 만료가 복구 불가 실패로 표면화 + 키 부재가 `unexpected`로 오분류.)
- **REQ-DEPLOY-032** [Unwanted] *(#6 — deploy-shell)* — **When** 앱 비정상 종료 후 재기동 시 지정 OSC **수신 포트**(예: 9000/9005)가 여전히 점유되어 `Address already in use`가 감지되면, the 앱 **shall not** 조용히 실패하거나 임의 포트로 **조용히 드리프트한다**(REQ-DEPLOY-026 불변 — onPC가 특정 포트로 송신하므로); 대신 **동일 지정 포트에 대한 재바인드(rebind) 전략**(소켓 재사용/재시도 등)으로 복구를 시도하고, 복구 불가 시 인간 친화적 오류 + 포트 재설정 안내를 표시한다. (라이브 E2E 결함: 수신 포트 수동 동기화가 취약하고, 앱 사망 시 onPC가 포트를 점유한 채 재기동 실패.)

## C. 제약사항

- 대상 플랫폼은 macOS와 Windows다 (Linux는 §D out of scope). 콘솔측 Lua responder는 grandMA3 onPC가 지원하는 플랫폼 범위를 따른다.
- 백엔드는 SPEC-COPILOT-MVP-001에서 확정된 Python 3.11+ 스택(`uv` 의존성 관리, `python-osc`, `anthropic`/`google-genai`)을 그대로 패키징한다 — 백엔드 재구현은 없다.
- 프론트엔드는 기존 Vite + React + TypeScript(`ui/`) 빌드 산출물(`ui/dist`)을 재사용한다.
- API 키·자격 증명은 커밋 가능한 파일에 평문으로 저장하지 않는다 (OS 자격 증명 저장소만 — REQ-DEPLOY-006). 크래시 덤프/예외 로거는 프로세스 env를 스크럽하여 env 주입 키의 디스크 평문화를 방지한다 (DECIDE-M6).
- **패키징 형태는 두 플랫폼 모두 onedir로 확정**된다 (onefile 아님 — FEAS-1/FEAS-6/DECIDE-M13). macOS는 onedir 트리를 notarizable .app/.dmg 컨테이너에 담는다.
- 코드 서명·공증에는 외부 자격(Apple Developer ID 인증서, Windows Authenticode 인증서)이 전제된다 — 인증서 조달·비용은 구현 세션 착수 전 확정 필요. **인증서 미보유이므로 서명 파이프라인 코드는 작성하되 AC-DEPLOY-009/010은 환경-게이트 N/A**로 둔다.
- **Windows SmartScreen 전제/제약** (REQ-DEPLOY-015에서 이동 — GEARS-2/FEAS-7): SmartScreen "미확인 게시자" 완화는 서명 자체가 아니라 **평판 누적**에 의존한다 — **OV** 인증서는 초기에는 평판이 없어 경고가 즉시 해소되지 않고, 즉시 신뢰는 **EV** 인증서로만 얻는다. 따라서 REQ-DEPLOY-015는 SmartScreen 결과가 아니라 `signtool verify /pa` 검증 가능 서명을 성공 기준으로 삼는다.
- **코드 서명 인증서 유형·키 보관 제약** (FEAS-3/FEAS-7/DECIDE-M7): 2023.6 이후 발급 코드 서명 키는 FIPS-140 하드웨어 토큰/클라우드 HSM에 보관해야 하며 파일 키 CI 서명은 불가하다. macOS 공증은 hardened runtime + entitlements plist(`com.apple.security.cs.*`) + stapling + notarytool 크리덴셜을 요구한다.
- 로컬 공존 HARD 제약(§A — 동일 머신 전용, "동일 LAN" 표현 삭제)은 두 Stage 모두에 불변으로 적용된다.

## D. 제외 범위 (Exclusions)

다음 항목은 본 SPEC의 out of scope다.

### Out of Scope — 클라우드/SaaS 원격 실행 형태
- 순수 클라우드 호스팅·SaaS 원격 실행 형태는 배제된다. OSC localhost UDP, 로컬 플러그인 파일시스템 공유, 라이브 저지연 요건 때문에 앱은 콘솔 PC에 로컬 설치되어야 한다 (핵심 HARD 제약 — §A). 원격 콘솔 지원(별도 파일 전송 채널 필요)도 본 Phase 초과다.

### Out of Scope — 모바일 앱 / 웹 호스팅 배포
- iOS/Android 네이티브 앱, 웹으로 호스팅되는 원격 접속 형태는 본 SPEC 범위가 아니다.

### Out of Scope — Linux 배포
- Linux용 배포 아티팩트는 본 Phase에서 제외한다. 대상은 macOS + Windows다 (후속 Phase에서 검토 가능).

### Out of Scope — 코파일럿 기능 변경
- 새 도구, LLM 프로바이더/모델 변경, 안전 게이트 규칙 변경, 룰북 지식 변경 등 코파일럿 **기능**의 어떤 변경도 본 SPEC 범위가 아니다. 본 SPEC은 SPEC-COPILOT-MVP-001의 기능을 **형태만** 바꾼다.

### Out of Scope — onPC 자체 설치/번들
- grandMA3 onPC는 서드파티 소프트웨어다. 본 앱은 onPC와 **함께 설치**될 뿐 onPC를 번들·설치·자동 구성하지 않는다.

### Out of Scope — Electron primary 채택
- Electron은 JS 전용 툴체인 선호 시의 **대안으로만 문서화**한다 (번들 크기 증가 트레이드오프). Stage 2의 권장 primary는 Tauri v2다.

### Out of Scope — 팀/멀티유저·중앙 관리 배포
- MDM/그룹 정책 기반 대규모 배포, 중앙 라이선스/키 관리, 다중 오퍼레이터 계정 관리는 본 Phase 초과다 (단일 콘솔 PC 로컬 설치가 대상).
