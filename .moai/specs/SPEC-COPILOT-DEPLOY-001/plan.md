# SPEC-COPILOT-DEPLOY-001 — 구현 계획 (plan)

> Tier L 구현 SPEC. 기능이 검증된 MVP(SPEC-COPILOT-MVP-001)에 **배포 셸**을 씌우는 작업 — 기능 변경 없음.
> 합의된 2단계: 패키징 **Stage 1 (PyInstaller onefile 런처)** → **Stage 2 (Tauri v2 데스크톱 앱)**.
> **"Phase" 용어 충돌 주의**: 프로젝트 레벨 Phase(0=EVAL, 1=MVP, 2=배포·제품화=본 SPEC)와 구분하기 위해, 본 SPEC 내부의 두 패키징 단계는 **"Stage 1/2"** 로 표기한다.

## A. 핵심 결정 사항 (변경 가능성 높은 순 — 먼저 검토)

> 데이터 모델·타입 인터페이스·UX 흐름 관련 결정을 먼저 배치하고, 기계적 패키징/서명 단계는 뒤로 둔다.

### A.0 산출물 범위 (Tier L vs 3-파일 요청 정합)
- 본 SPEC은 복잡도상 **Tier L**(멀티 스테이지 패키징 + 크로스플랫폼 + 서명/공증/자동 업데이트)이며, 형제 SPEC-COPILOT-MVP-001과 동일 Tier로 분류한다.
- **구현 착수 세션 스코핑 결정에 따라, plan-phase 산출물은 코어 3종(spec.md / plan.md / acceptance.md) + progress.md 스켈레톤으로 작성**되었다.
- ✅ **RESOLVED (F1)**: **최소 research.md를 M6 착수 전에 필수 작성**한다 — 최고 불확실 영역(FEAS-8)을 plan-phase에서 de-risk. 커버 항목: (a) PyInstaller **onedir** 네이티브 의존성 패키징(google-genai / anthropic / grpcio / keyring), (b) frozen 번들 내부 keyring 백엔드 발견(entry-point 메타데이터 strip 문제), (c) hardened runtime 하 macOS notarization 절차. **design.md는 별도 문서로 분리하지 않고 plan.md(§A 결정·§C 마일스톤·§D 리스크)에 접어 둔다** — 런처 프로세스 모델·sidecar 수명주기·자동 업데이트 시퀀스는 §A.4/§A.5/§C에 서술.

### A.0.1 이 kickoff의 스코프 = Stage-2 **M7-first** (v0.4.0 kickoff)

- **본 kickoff는 Stage-2를 M7만 착수 스코프로 확정한다** — Tauri v2 데스크톱 셸 + Python 백엔드 sidecar(§C M7 구현 계획). Stage-1(M1~M6 + M10) 및 v0.3.0 하드닝(M14~M18)은 **완료·synced**(progress.md §E.2~§E.4)로 불변 보존한다.
- **M8(자동 업데이트)·M9(코드 서명/공증)은 Stage-2-DEFERRED — 별도 kickoff**로 미룬다. §C의 M8/M9 마일스톤 행과 §F의 F6 이연 마커는 **불변으로 유지**하며, 본 kickoff에서 이들을 계획·구현하지 않는다.
- Stage-2 greenfield 확인: `src-tauri/`·`Cargo.toml` 부재(Rust/Tauri 코드 미존재) — M7은 신규 스캐폴드부터 시작한다.
- **문서 전용(plan-phase)**: 본 kickoff는 계획·수용 기준 작성만 수행한다 — 구현 코드·`src-tauri/` 프로젝트 생성·frontmatter `status` 전이 없음(`in-progress` 유지).

### A.1 설정·config 저장 모델 (데이터 모델 — 최우선 검토)
- 현재 비민감 설정은 리포 파일 `config/provider.toml`(active 프로바이더 + 모델 핀 + 캐시/폴백 파라미터)에 있고, OSC 포트/임포트 디렉터리는 `serve.py` CLI 인자다. 패키징된 앱은 **사용자 쓰기 가능 경로**에 설정을 저장해야 한다.
- ✅ **방향**: 비민감 설정을 OS별 표준 사용자 config 경로(macOS `~/Library/Application Support/GrandMA3 Copilot/`, Windows `%APPDATA%\GrandMA3 Copilot\`)에 저장. 번들된 `provider.toml`은 기본값(seed)으로만 사용하고, 사용자 설정이 이를 오버레이한다. (경로 앵커 = 번들 식별자 `com.grandma3copilot.app` / AppName "GrandMA3 Copilot")
- ✅ **RESOLVED (F2)**: 설정 파일 포맷 = **TOML**(기존 stdlib `tomllib` 로더 재사용, 의존성 0). 재사용 우세로 확정. **UI ↔ 백엔드 config 스키마 계약(필드·검증)은 M1에서 확정**한다(진짜 열린 항목).
- **불변**: 자격 증명은 이 설정 파일에 절대 포함하지 않는다 (로더의 credential-like 키 거부 제약 유지 — REQ-DEPLOY-007/008).

### A.2 보안 키 저장 백엔드 (Secured — 결정 필요)
- API 키를 OS 자격 증명 저장소에 저장·조회하는 계층 필요 (macOS Keychain / Windows Credential Manager).
- ✅ **RESOLVED (F3)**: **keyring 의존성 승인**. Python `keyring` 라이브러리 — macOS Keychain + Windows Credential Manager를 단일 인터페이스로 지원, 성숙·크로스플랫폼. **Stage 1 = Python 백엔드가 keyring에 직접 접근**. 단순성 사다리상 자체 구현보다 우세.
- ✅ **RESOLVED (F5' — Stage-2 M7 kickoff)**: **Stage 2에서도 Python `keyring`을 백엔드 sidecar가 직접 접근**한다 — Rust/Tauri는 비밀을 **절대 만지지 않고** sidecar의 spawn/수명주기 관리만 수행한다. 기존 `server/deploy/keystore.py` 경로를 **무변경 재사용**한다: `SERVICE_NAME = "com.grandma3copilot.app"`(`keystore.py:54`, ACL/identity 앵커), env 주입 `inject_key_for_provider`/`inject_active_provider_key`(`keystore.py:221`/`:253`), 평문-디스크 폴백 0(`SessionKeyStore`), fail-closed keyring 가드(`server/web/launcher.py:128`~ `PortInUseError` 이웃 부트 가드·`PINNED_KEYRING_BACKEND`), `scrub_environ`(`keystore.py:298`, DECIDE-M6). 근거: 두 Stage 단일 키 인터페이스 유지 → 드리프트 0, 감사되는 Python에 자격 표면 집중. **전제/잔여(M9 이연)**: 서명(M9) 후 **서명된 sidecar가 OS keychain에 도달 불가**하고 Tauri 호스트만 가능한 경우에 한해 키 커스터디를 재검토한다 — 이는 M9(코드 서명)로 이연된 검증 항목이며 M7을 블록하지 않는다.
- 키는 **런타임에만** 백엔드 프로세스 env(`GEMINI_API_KEY`/`ANTHROPIC_API_KEY`)로 주입하고 디스크 평문화하지 않는다.

### A.3 설정 UI 흐름 (UX — 변경 가능성 높음)
- 인앱 설정 화면: 프로바이더 키 입력(마스킹), OSC 콘솔 송신 포트·피드백 수신 포트, 플러그인 임포트 디렉터리, 활성 프로바이더 선택. 기존 React SPA(`ui/`)에 설정 화면 + 상태 표시를 추가한다.
- responder provisioning 가이드(플러그인 설치 버튼 + onPC 로드/ OSC 출력 포트 설정 안내)와 health 상태 배지도 UX의 일부.
- ✅ **RESOLVED (F4)**: 최초 실행(first-run) 온보딩 = **배너/배지 안내**(강제 설정 마법사 아님) — 키 미설정 시 비침습적 배너로 설정 UI를 유도한다. (실질 UX 포크지만 M1 블록 아님 — M3/M5에서 구현)

### A.4 Stage 2 셸 선택 — Tauri v2 (primary) vs Electron (대안)
- ✅ **결정됨(사전 합의)**: **Tauri v2** primary. 근거: 경량 번들(시스템 웹뷰), 네이티브 창/트레이/updater 플러그인, Rust sidecar 관리. **Electron은 대안으로만 문서화**(JS 전용 툴체인 선호 시, 번들 크기 증가 트레이드오프).
- Tauri sidecar로 PyInstaller 빌드 백엔드를 번들·기동/종료 관리. UI는 동일 `ui/dist`를 Tauri 창이 로드. (Tauri v2 primary vs Electron 대안은 사전 합의로 확정 — 위 ✅.)
- ✅ **RESOLVED (F5 — Stage-2 M7 kickoff)**: **기존 127.0.0.1 WebSocket을 유지하고 Origin-헤더 검증 + per-launch 토큰 핸드셰이크를 추가**한다. 메커니즘: 백엔드가 WebSocket 업그레이드 `Origin`을 allowlist(Tauri/커스텀 스킴 오리진 + Stage-1 localhost 브라우저 오리진)와 대조 **AND** launcher가 생성해 `ui/dist`에 serve 시점 주입한 unguessable per-launch 비밀 토큰을 `accept()`에서 상수-시간 비교로 요구한다(REQ-DEPLOY-002a로 앵커).
  - **근거(최소 변경 축)**: 백엔드는 WS 서버로 유지(프로토콜 v1 / `server/web/messages.py` / `ui/src/useCopilotSocket.ts` / `server/web/PROTOCOL.md` 불변), **단일 전송**이 Stage-1 브라우저 모드와 Stage-2 Tauri 모드를 모두 서빙, 제어 평면(단일 OSC 관문 포함)이 감사되는 Python에 유지된다.
  - **근거(보안/오리진 축 — FEAS-9 해소)**: 현재 `server/web/app.py:137`의 `@app.websocket("/ws")`가 `:139`에서 `accept()`를 origin/token/CORS 검사 **0**으로 수행하고(`127.0.0.1:8765` 바인드 — `serve.py:69-70`; UI 클라이언트 `ui/src/useCopilotSocket.ts:33-34`가 `ws://…/ws` 구성), same-origin 미강제라 로컬 프로세스/브라우저 탭이 접속 가능한 **cross-site WebSocket hijacking(CSWSH)** 공격면이다. origin/token 핸드셰이크가 이 구멍(FEAS-9)을 닫는다.
  - **잔여(residual)**: `127.0.0.1` loopback 리스너 자체는 존속 — LOCAL-ONLY 앱의 **심층방어**로 수용(Tauri IP(in-process) 전용화로 노출을 완전 제거하는 대안 대비, 단일-전송·최소-변경·감사-유지 이점이 우세). Tauri v2 capabilities에서 sidecar-spawn 외 네트워크 플러그인을 deny하여 보완(§C M7.3).
  - AC-DEPLOY-025(핸드셰이크 reject/accept) + AC-DEPLOY-014 ③(교차언어 OSC 스캔)에 반영.

### A.5 자동 업데이트 메커니즘 (아키텍처 + 호스팅 — 결정 필요)
- Stage 2: Tauri updater 플러그인(서명된 업데이트 매니페스트 + 아티팩트, 서명 검증 후 적용 — REQ-DEPLOY-017). updater 재시작 시 안전상태 보존은 REQ-DEPLOY-027(SAFETY-4)로 앵커링.
- Stage 1: PyInstaller에는 내장 updater가 없음 → **버전 확인 + 알림(수동 재설치 안내)** 로 한정 (REQ-DEPLOY-016 capability gate).
- ⏸️ **DEFERRED — Stage-2 kickoff**: `[DEFERRED-M8: 업데이트 매니페스트·아티팩트 호스팅 위치 — GitHub Releases vs 자체 호스팅, M8 kickoff에서 해소]` 및 `[DEFERRED-M8: Tauri updater 서명 키(별도, 코드 서명 인증서와 무관) 관리 주체 — M8 kickoff에서 해소]` *(Stage-2-scoped, M8만 블록 — M7 착수·Stage-1 run 진입 블록 아님, 2개 결정 번들)*. **본 M7 kickoff 스코프 아님** — 이 두 결정은 M8(자동 업데이트) 별도 kickoff에서 확정하며, M7 착수를 블록하지 않는다(비-reserved `[DEFERRED-M8: …]` 토큰으로 표기 — MP-7 clarification 게이트 대상 아님).

### A.6 코드 서명·공증 전제 (외부 의존성)
- macOS: Apple **Developer ID** 인증서 + notarization(notarytool). Windows: **Authenticode** 코드 서명 인증서(OV/EV).
- ✅ **RESOLVED (F7)**: 인증서 **미보유** → 서명/공증 **파이프라인 코드는 작성**하되, AC-DEPLOY-009/010은 인증서 확보 전까지 **환경-게이트 N/A**로 둔다. 인증서 조달·유형(OV vs EV)·CI 서명 자동화는 조기 확정이 바람직하나 Stage-1 run 진입을 블록하지 않는다(M10 환경-게이트).
- **서명 파이프라인이 반영해야 할 기술 사실 (FEAS-3/FEAS-7/DECIDE-M7)**:
  - **frozen Python 앱 공증 (FEAS-3)**: hardened runtime 필수 + entitlements plist(`com.apple.security.cs.allow-jit`, `...allow-unsigned-executable-memory`, `...disable-library-validation` 등 frozen 인터프리터에 필요한 항목) + **stapling**. keychain ACL이 코드서명 identity에 묶여 dev 빌드마다 재프롬프트되므로 M2/M3 keychain UX는 **서명된 dev 빌드**로 검증한다.
  - **Windows OV vs EV (FEAS-7)**: OV 인증서는 평판 누적 전 SmartScreen 미해소, 즉시 신뢰는 EV만. REQ-DEPLOY-015는 `signtool verify /pa` 검증 가능 서명을 성공 기준으로 함(SmartScreen 결과는 제약/전제).
  - **코드서명 키 보관 (FEAS-7/DECIDE-M7)**: 2023.6 이후 코드서명 키는 FIPS-140 하드웨어 토큰/클라우드 HSM 필수 → **파일 키 CI 서명 불가**. CI 서명은 클라우드 서명 서비스/HSM 경유로 설계.
  - **notarytool 크리덴셜 (DECIDE-M7)**: CI에서 notarization을 수행하려면 notarytool 크리덴셜(Apple ID app-specific password 또는 API key) 관리가 필요.

### A.7 PyInstaller onedir 번들 구성
- 번들 포함물: Python 백엔드(`server/`) + `ui/dist`(정적 자산) + `console/lua/*`(responder Lua/XML) + `config/provider.toml`(seed). 데이터 파일 경로는 PyInstaller `--add-data` + 런타임 `sys._MEIPASS` 리졸브(onedir에서도 유효).
- 더블클릭 실행 → 로컬 서버 기동 → 기본 브라우저 오픈(REQ-DEPLOY-002) → 종료 시 정리(REQ-DEPLOY-025).
- ✅ **RESOLVED (F8 / FEAS-1/FEAS-6/DECIDE-M13)**: **onedir로 확정**(두 플랫폼). 근거 3축 — (지연) onefile `_MEI` 추출 기동 지연 회피, (hardened-runtime 호환) onefile dylib 추출이 macOS hardened runtime/library-validation과 충돌해 공증 거부의 대표 원인, (Stage-2 sidecar 서명성) signed .app 내부 onefile sidecar 서명 난도 제거.
- **macOS 패키징 형태 (FEAS-6/DECIDE-M13)**: onedir 트리를 **notarizable .app/.dmg 컨테이너**에 담아 전달한다 — bare Mach-O는 더블클릭/공증(stapling)에 부적합. 
- **keyring 백엔드 수집 (FEAS-2)**: onedir라도 keyring 백엔드는 entry-point 메타데이터 의존이라 PyInstaller가 strip → frozen에서 null 백엔드로 조용히 폴백. M6 번들 스펙에 `--collect-all keyring` + keyring 백엔드 hidden-imports를 명시(핀만으로 해결 안 됨).

## B. 알려진 이슈 / 전제

- **기능 무변경 원칙**: 본 SPEC은 `server/` 백엔드 로직·안전 게이트·룰북을 변경하지 않는다. 신규 코드는 배포 셸(설정 계층, 키 저장 어댑터, 설정/상태 UI, 패키징 스펙, Tauri 프로젝트)에 한정한다. 백엔드에 대한 최소 수정(예: 설정 소스를 CLI 인자 → config 파일 우선순위로 확장)은 기존 178+ 테스트 무변경 green 유지를 조건으로 한다.
- **M7 백엔드 신규 코드 — 명시적·한정 예외**: M7은 두 건의 **신규 백엔드 코드**를 도입한다 — ① `/ws` 핸드셰이크(Origin allowlist + per-launch 토큰 검증, REQ-DEPLOY-002a), ② parent-liveness **watchdog**(Tauri 강제 종료 시 sidecar self-reap, FEAS-5 Option C). 이는 위 "기능 무변경 원칙"에 대한 **명시적이고 경계가 확정된 예외**로, FEAS-9(CSWSH 차단)·FEAS-5(sidecar 좀비 방지)로 정당화된다. 조건: (a) 기존 전체 테스트 스위트(`1017 passed`) 무변경 green 유지, (b) SPEC-COPILOT-MVP-001 안전 불변식(단일 관문·라이브 잠금·감사 로그) 불변 — 핸드셰이크·watchdog 어느 것도 OSC 송신 표면에 새 경로를 추가하지 않는다(AC-DEPLOY-014로 회귀 강제). 코파일럿 도구·LLM·룰북·안전 게이트 규칙은 여전히 불변이다.
- **선행 의존**: SPEC-COPILOT-MVP-001은 **기능 검증은 완료**되었으나 **프론트매터 `status: in-progress`** 상태다(라이브 onPC 잔여 gap로 terminal close 미완). 따라서 `depends_on` 게이트는 **Stage-1과 동일하게 `--ignore-deps` 오버라이드 경로(사용자 승인 + `.moai/logs/depends-on-override.log` 기록)** 를 사용한다 — M7 run-phase 진입 시 depends_on pre-flight가 미충족(MVP-001≠completed)을 보고하면 override로 진행(Stage-1 선례: progress.md §F). MVP-001 상태 전이는 본 SPEC 범위 아님. 라이브 onPC 잔여 gap은 본 SPEC과 병렬 진행 가능하나 배포 검증(M10)에는 무관.
- **OSC 포트 드리프트**: 프로젝트 이력상 onPC OSC 응답 포트 드리프트 관측 — REQ-DEPLOY-026(포트 사용 중 시 조용한 폴백 금지)의 직접 근거.
- **로컬 공존 HARD 제약**: 두 Stage 모두 127.0.0.1 바인딩 + 로컬 플러그인 파일시스템을 유지한다 (원격 백엔드 도입 금지).
- **크로스플랫폼 빌드 환경**: macOS 아티팩트는 macOS에서, Windows 아티팩트는 Windows에서 빌드/서명해야 한다 (네이티브 서명 툴체인 요구). CI 매트릭스(GitHub Actions macOS+Windows 러너) 사용 여부는 A.5/A.6 호스팅 결정과 연동.

## C. 마일스톤 (변경 가능성·의존성 순 — 설정/UX 우선, 서명/빌드 기계적 단계 후순위)

### 패키징 Stage 1 — PyInstaller onedir 로컬 런처 (MVP 배포 형태)

| 마일스톤 | 내용 | 의존성 | 주요 REQ |
|---|---|---|---|
| **M1 — 설정·config 저장 계층** | 사용자 config 경로(OS별) 설정 저장/로드 계층. 번들 `provider.toml`을 seed로, 사용자 설정이 오버레이. 비민감 설정(OSC 포트·임포트 디렉터리·활성 프로바이더)만 — 자격 증명 배제(로더 거부 제약 유지). 스키마·검증 확정(TOML) | 없음 | REQ-DEPLOY-008 |
| **M2 — 보안 키 저장 어댑터** | OS 자격 증명 저장소(Keychain/Credential Manager) 저장·조회 어댑터(keyring, Python 직접). 키 → 백엔드 env 주입, 디스크 평문화 0. 저장소 미가용/잠금/거부 시 명시적 오류 + 세션 한정(in-memory) 폴백(평문 폴백 금지 — REQ-006a). **⚠️ (FEAS-2) 키 어댑터 AC는 dev venv가 아니라 플랫폼별 frozen PyInstaller onedir 스모크 빌드 안에서 검증** — entry-point strip로 인한 null 백엔드 조용한 폴백을 조기 탐지 | M1 | REQ-DEPLOY-006, 006a, 007 |
| **M3 — 설정 UI (프론트엔드) + 백엔드 배선** | React 설정 화면(키 입력 마스킹, 포트, 임포트 디렉터리, 프로바이더 선택) + M1/M2 배선. 프로바이더 클라이언트 기동 시 키 주입 경로. first-run 배너 온보딩 | M1, M2 | REQ-DEPLOY-005 |
| **M4 — CopilotResponder provisioning** | Lua 플러그인(+XML) 번들 포함, 임포트 디렉터리로 파일 복사, onPC 로드 + OSC 출력 포트 설정 가이드 UI. 앱이 `Import Plugin` 콘솔 실행을 직접 발행하는 경우 단일 안전 관문 경유 + 감사 로그(REQ-011a) | M1, M3 | REQ-DEPLOY-009~011, 011a |
| **M5 — health 상태 UI + 오류 UX** | HealthMonitor 상태(online/console_offline/responder_degraded) 표면화 + 전이 반영. 3대 오류 UX(콘솔 오프라인 / responder 미로드 / 키 부재·무효) 인간 친화적 한국어 안내(스택 트레이스·raw SDK 원문 미노출) | M3 | REQ-DEPLOY-012, 013, 018~020 |
| **M6 — PyInstaller onedir 런처** | 백엔드 + `ui/dist` + Lua 자산 + seed config 번들, 더블클릭 → 서버 기동 → 브라우저 오픈, graceful shutdown + 포트 사용 중 안내(조용한 폴백 금지). Stage 1 버전 확인·알림(수동 재설치). **번들 스펙: `--collect-all keyring` + keyring 백엔드 hidden-imports(FEAS-2)**; macOS는 onedir 트리를 notarizable .app/.dmg 컨테이너에 담고 hardened runtime + entitlements plist + stapling(FEAS-3) | M1~M5 | REQ-DEPLOY-001~003, 004, 004a, 016(Stage1), 025, 026 |
| **SPIKE — 서명/공증 조기 스파이크 (M6~M7 병행, HIGH-RISK)** | (FEAS-4) 데스크톱 배포의 최고 난도 구간을 후순위로 미루지 않는다. 선택된 onedir/.app 형태에 대해 **notarytool 왕복 1회 성공**을 조기에 확인하는 스파이크 — 그 제약(entitlements/hardened runtime/stapling)이 M6 패키징 형태·M7 sidecar 구조로 역류하기 때문. 인증서 부재 시 파이프라인 구성 + N/A 기록 | M6(아티팩트 형태) | REQ-DEPLOY-014 (조기 de-risk) |

### 패키징 Stage 2 — Tauri v2 데스크톱 앱 (제품 형태)

| 마일스톤 | 내용 | 의존성 | 주요 REQ |
|---|---|---|---|
| **M7 — Tauri v2 셸 + 백엔드 sidecar** *(본 kickoff 착수 스코프)* | Tauri 네이티브 창이 동일 `ui/dist` 로드, PyInstaller 백엔드를 sidecar로 번들·기동/종료 관리, 트레이 + 연결 상태. Electron 대안 문서화. **F5 RESOLVED**: sidecar↔UI = 127.0.0.1 WebSocket 유지 + Origin allowlist + per-launch 토큰 핸드셰이크(§A.4, REQ-DEPLOY-002a). **teardown = Option C(FEAS-5)**: Rust가 authoritative process-group kill(Unix setsid/setpgid, Windows Job Object) + 백엔드 parent-liveness watchdog(force-quit self-reap). **SAFETY-2 이중 스캔 M7 활성화**: Rust deny-all 정적 스캔 + wire-level 싱크(§C M7.3). 상세 = **아래 § M7 구현 계획** | M6 | REQ-DEPLOY-001, 002, 002a, 025, 026 |
| **M8 — 자동 업데이트** *(Stage-2-DEFERRED — 별도 kickoff)* | Tauri updater(버전 확인 → 다운로드 → 승인 후 적용) + 서명 검증 통과 아티팩트만 적용(실패 시 현재 버전 유지). **updater 재시작 시 라이브 잠금/승인 대기/감사 로그 연속성 보존(REQ-027, SAFETY-4)**. 매니페스트/아티팩트 호스팅·updater 서명 키는 Stage-2 kickoff 결정(§A.5, F6). **⏸️ 본 M7 kickoff 스코프 아님 — 계획·구현하지 않음** | M7 | REQ-DEPLOY-016(Stage2), 017, 027 |
| **M9 — 코드 서명·공증 + 재현 가능 크로스플랫폼 빌드 (HIGH-RISK)** *(Stage-2-DEFERRED — 별도 kickoff)* | macOS Developer ID 서명 + notarization(**hardened runtime + entitlements plist(`com.apple.security.cs.*`) + stapling** — FEAS-3), Windows Authenticode 서명(`signtool verify /pa`). 문서화된 빌드 절차 + 의존성 핀(uv.lock/package-lock/Cargo·Tauri 락). 비공개 자원 의존 0. **데스크톱 배포 최고 난도 구간 — "기계적 마무리" 아님**(FEAS-4); 조기 스파이크(위)로 de-risk. 인증서 부재 시 파이프라인 구성 + AC-009/010 환경-게이트 N/A. **⏸️ 본 M7 kickoff 스코프 아님 — 계획·구현하지 않음**; 서명된 sidecar의 keychain 도달성(§A.2 F5' 잔여)은 M9 검증 항목 | M7 (Stage2 아티팩트), M6 (Stage1 아티팩트도 서명 대상), SPIKE(조기 검증) | REQ-DEPLOY-014, 015, 021, 022 |

> **M8/M9 Stage-2-DEFERRED 명시**: 본 kickoff는 **M7-first**만 착수한다(§A.0.1). M8(자동 업데이트)·M9(코드 서명/공증)은 별도 kickoff로 이연 상태를 유지하며, 위 두 행은 참조용으로 보존한다. §F의 F6(업데이트 호스팅·updater 서명 키)은 계속 Stage-2-deferred다.

### M7 구현 계획 (Stage-2 kickoff, v0.4.0 — 변경 가능성·의존성 순)

> 데이터-흐름/보안 계약(핸드셰이크·teardown)을 먼저, 기계적 셸 스캐폴드를 뒤로 배치한다. Tauri v2 동작 참조는 검증된 공식 문서를 인용한다: sidecar [v2.tauri.app/develop/sidecar](https://v2.tauri.app/develop/sidecar/), IPC [v2.tauri.app/concept/inter-process-communication](https://v2.tauri.app/concept/inter-process-communication/), 프로세스 모델 [v2.tauri.app/concept/process-model](https://v2.tauri.app/concept/process-model/), 보안/capabilities [v2.tauri.app/security/capabilities](https://v2.tauri.app/security/capabilities/), shell 플러그인 [v2.tauri.app/plugin/shell](https://v2.tauri.app/plugin/shell/).

#### M7.1 — sidecar↔UI 전송 핸드셰이크 (F5, 최고 변경가능성 — 신규 보안 데이터-흐름)

3-계층으로 분할한다 (프로토콜 v1 / `server/web/messages.py` / `server/web/PROTOCOL.md` 불변):

- **(백엔드)** `server/web/app.py`의 `@app.websocket("/ws")`(`app.py:137`) `accept()`(`:139`) **이전**에 게이트를 삽입: ① 업그레이드 `Origin` 헤더를 allowlist(Tauri/커스텀 스킴 오리진 + Stage-1 `http://127.0.0.1:<web port>` 브라우저 오리진)와 대조 ② `Sec-WebSocket-Protocol` 또는 최초 프레임/쿼리로 전달된 per-launch 토큰을 **상수-시간 비교**(`hmac.compare_digest`) ③ 둘 중 하나라도 실패 시 `accept()` 전에 거부(close code). @MX:ANCHOR 대상(신규 credential-adjacent 보안 경계).
- **(launcher — 토큰 생성 + 누출-저항 전달)** `server/web/launcher.py`가 기동 시 unguessable per-launch 비밀 토큰 생성(`secrets.token_urlsafe`) → 백엔드 프로세스 env/메모리로만 전달(디스크 평문화 0 — AC-004 규율 계승). **토큰을 UI로 전달하는 방식은 실행 모드별로 다르며, 위장-Origin 로컬 프로세스에 토큰이 새지 않도록 설계한다**:
  - **Stage-2 Tauri 모드 (누출-저항 경로)**: 토큰을 **Tauri IPC로 웹뷰 컨텍스트에 주입**(`invoke`/init-script 경유) — 디스크 파일 아님, 미인증 loopback 엔드포인트 아님. IPC는 Tauri 호스트↔자기 웹뷰 간 in-process 채널이라 타 로컬 프로세스가 읽을 수 없다. **`index.html` 메타 주입 옵션은 폐기**(디스크에 토큰을 기록해 "디스크 평문화 0"과 모순 + 로컬 프로세스 판독 가능). [IPC 근거: [v2.tauri.app/concept/inter-process-communication](https://v2.tauri.app/concept/inter-process-communication/)]
  - **Stage-1 브라우저 모드 (토큰 = 심층방어만)**: 브라우저에는 Tauri IPC가 없어 디스크 파일/loopback 엔드포인트 없이 토큰을 건넬 수 없다(둘 다 로컬 프로세스가 읽을 수 있어 위장-Origin 벡터를 못 막음). 따라서 **Stage-1에서 실질 CSWSH 차단자는 Origin allowlist**이고, 토큰은 **브라우저 벡터에 대한 심층방어**로만 취급한다(토큰이 실질 방어의 유일 축이라고 주장하지 않음). 이로써 plan §M7.1의 "디스크 평문화 0" 주장과 정합.
- **(UI)** `ui/src/useCopilotSocket.ts`(`:33-34`가 `ws://${host}/ws` 구성)가 모드별 경로로 받은 토큰(Stage-2=IPC 주입값, Stage-1=심층방어 토큰)을 연결에 포함. 스키마·이벤트 shape 무변경(핸드셰이크는 전송 계층 전용).

#### M7.2 — sidecar 수명주기 teardown (FEAS-5 Option C, belt-and-suspenders)

- **(Rust — authoritative)** Tauri가 sidecar를 프로세스-그룹/세션 리더로 spawn(Unix: `pre_exec` setsid/setpgid; Windows: KILL_ON_JOB_CLOSE Job Object). 정상 종료·백엔드 크래시 시 `RunEvent::Exit`에서 process-group kill. ⚠️ `CommandChild.kill()`은 부트로더 PID만 죽이고 grandchild(추출된 Python)를 남기므로 **group kill 필수**.
- **(백엔드 — self-reap watchdog, 신규 코드)** 기존 `server/web/launcher.py`의 `terminate_process_tree`(`launcher.py:208`)/`make_shutdown_handler`(`:254`) SIGTERM-first 트리 kill을 **유지**하고, **parent-liveness watchdog**를 추가해 Tauri가 사망/force-quit(Unix force-quit 시 `RunEvent::Exit` 미발화)해도 sidecar가 자기 그룹을 self-reap한다. **PRIMARY 트리거 = pipe/heartbeat EOF** — Tauri가 sidecar spawn 시 물려준 파이프(또는 하트비트 채널)의 EOF/close는 부모 사망 **즉시** 감지되므로(레이스 창 없음) 이것을 주 메커니즘으로 삼는다. **FALLBACK = `getppid()==1` 폴링** — 파이프가 없거나 실패한 환경을 위한 폴백이며, **폴링 주기 상한(bounded max reap latency ≤ 1s)** 을 명시해 잔여-0 스캔이 결정적이 되도록 한다(무한 레이스 창 제거). §B의 "M7 백엔드 신규 코드 — 명시적 예외"로 정당화(FEAS-5). @MX:ANCHOR 대상.
- **(fail-closed 넷)** 재기동 시 `require_ports_available`(`launcher.py:162`)의 `PortInUseError`가 조용한 포트 드리프트를 차단(REQ-DEPLOY-026 불변). 참조 모델: `packaging/verify_packaged_e2e.py`(이미 start_new_session + `killpg` 사용).

#### M7.3 — SAFETY-2 교차언어 이중 스캔 + Tauri capability 설정 (보안 회귀 배선)

- **(a) Rust deny-all 정적 스캔(CI 상시)**: `src-tauri/**/*.rs` + `Cargo.toml`/`Cargo.lock`을 **빈(deny-all) allowlist**로 스캔 — 마커 `UdpSocket`/`std::net::`/`.bind|.connect|.send_to`/OSC 크레이트(rosc·nannou_osc)/`127.0.0.1`·콘솔 포트 리터럴; 매니페스트 스캔은 raw-socket/OSC 네트워킹 크레이트(전이 Cargo.lock 포함) 거부. 근거: Tauri 셸의 합법 작업(sidecar spawn, `ui/dist` 로드, 창/트레이)은 콘솔로의 raw UDP가 **0** 필요.
- **(b) wire-level 패킷 싱크(패키지 E2E)**: 싱크를 **하드코딩 기본(8000)이 아니라 E2E 실행의 실제 설정 send_port**(effective settings에서 읽음 — send_port는 REQ-DEPLOY-005로 사용자 설정 가능, 기본값 `server/bridge/osc.py:105`=8000)에 바인드 → 모든 datagram 기록 → 게이트 감사 "executed" 로그(`server/tests/test_deploy_safety_invariants.py`)와 **1:1 대조**, 미감사/미열거 송신자에 **fail-closed**; **양성 관측(positive-observation) assert — 정당한 게이트 송신이 싱크에서 실제로 ≥1건 관측됨**(빈 캡처 vacuous-충족 차단) + synthetic rogue 패킷 주입으로 싱크가 flag함을 증명. 호스트: `packaging/verify_packaged_e2e.py` 확장(loopback — onPC 불요).
- **(c) Tauri v2 capabilities**: 모든 네트워크 플러그인 deny + `tauri-plugin-shell`을 **sidecar-spawn만으로 스코프**(보완적 하드닝). [v2.tauri.app/security/capabilities](https://v2.tauri.app/security/capabilities/) · [v2.tauri.app/plugin/shell](https://v2.tauri.app/plugin/shell/).
- 확장 대상: 기존 Python-전용 가드 — import-boundary `server/tests/test_architecture.py`(전 트리 import 스캔) + AST allowlist `server/tests/test_deploy_safety_invariants.py`(docstring이 Rust/wire-level 절을 Stage-2로 이연) — 를 M7에서 활성화. AC-DEPLOY-027 + AC-DEPLOY-014 ③b/③c/③d로 검증.

#### M7.4 — Tauri v2 셸 스캐폴드 + sidecar 번들 + 창 로드 + 트레이/상태 (기계적)

- 신규 `src-tauri/` 프로젝트 스캐폴드(greenfield — 현재 부재 확인). Tauri config에 sidecar로 M6 PyInstaller onedir 백엔드 번들·spawn([v2.tauri.app/develop/sidecar](https://v2.tauri.app/develop/sidecar/) · 프로세스 모델 [v2.tauri.app/concept/process-model](https://v2.tauri.app/concept/process-model/)).
- 네이티브 창이 동일 `ui/dist` 로드(M6 백엔드 재사용), 시스템 트레이 + 연결 상태(health 배지 재사용 — M5 `healthGuidance`/`StatusBanner`). Electron 대안은 문서화만(§A.4).

### 통합 검증

| 마일스톤 | 내용 | 의존성 | 주요 REQ |
|---|---|---|---|
| **M10 — 배포 통합 검증** | 양 Stage·양 플랫폼(macOS/Windows) 아티팩트 기동·설정·provisioning·health·오류 UX E2E. **안전 불변식 회귀**: 패키징된 셸에서 SPEC-COPILOT-MVP-001 단일 관문/블랙리스트 승인/감사 로그 불변식이 유지됨을 자동 테스트로 확인(AC-DEPLOY-014). 서명/공증은 인증서 확보 후 환경-게이트 검증 | M1~M9 전체 | REQ-DEPLOY-023, 024 + 전 AC |

> 순서 비고: Stage 1(M1~M6)이 완성되면 그 자체로 배포 가능한 MVP 형태다. Stage 2(M7~M9)는 M6의 PyInstaller 백엔드를 sidecar로 재사용하므로 M6 이후 착수한다. **M9(서명·공증)는 Stage 1·2 양 아티팩트 모두에 적용되는 HIGH-RISK 구간이며, "기계적 마무리 단계"가 아니다** — 서명/공증 제약(entitlements/hardened runtime/stapling, HSM 키 보관, notarytool 크리덴셜)이 M6 패키징 형태·M7 sidecar 구조로 역류하므로, notarytool 왕복 1회를 확인하는 **조기 스파이크(SPIKE)를 M6~M7과 병행**한다(FEAS-4).

### 패키징 Stage 1 — 라이브 E2E 하드닝 (v0.3.0 fold-in, mid-run)

> 실제 onPC 2.4.2 하드웨어 + 실제 Gemini 라이브 데모(2026-07-20)에서 **983-test 단위 스위트가 놓친 통합 결함 6건** 발견 — 하드웨어 + LLM + 패키지 번들 결합에서만 발현(단위 테스트 사각지대). provenance: 프로젝트 메모리 `copilot-live-demo-findings`. **기능 무변경 원칙(§B) 하의 셸/배선/프롬프트 정합 하드닝**이며 안전 게이트·룰북 규칙은 불변이다. 도메인 구분: #2·#6=deploy-shell, #3·#4·#5=LLM/orchestrator.
>
> **[이미 수정 — 기록 전용] 결함 #1**: 패키징된 앱의 `build_runtime`이 settings/provision 라우터를 조립하지 않아 `/api/*`가 미마운트(404/405)되던 결함 → **commit `1d65375`에서 수정 완료**. M14의 선행 전제(라우터 조립)이며, 신규 마일스톤을 앵커링하지 않는다.
>
> **마일스톤 순서 = 승인된 구현 진행 순서**: #2 최우선 → #4·#5 → #3·#6. 마일스톤 번호(M14~M18)는 이 진행 순서를 따르며, 기존 M1~M10 및 결정 ID(DECIDE-M13 등)와 충돌하지 않는다.

| 마일스톤 | 내용 | 의존성 | 주요 REQ/AC |
|---|---|---|---|
| **M14 — 기동 시 활성 프로바이더 키 주입 (#2, deploy-shell, 최우선)** | 기존 `inject_active_provider_key`(`server/deploy/keystore.py:253`)를 **`build_runtime`(`server/web/serve.py:124`)의 프로바이더 클라이언트 생성 이전 시점**에 배선하여 startup 주입을 구현. **이미 설정된 env 키는 보존**(덮어쓰지 않음), 저장소 미가용/잠금/거부 시 REQ-DEPLOY-006a 세션 한정 폴백(평문 미저장). 기존 주입 경로는 `POST /api/keys` 단독(`server/web/settings_api.py:146`)이라 신규 인스턴스가 키 없이 기동 → "No API key" 실패하던 결함 해소. **회귀 테스트 홈: `server/tests/test_web_serve.py`** | M6(패키징 형태), 결함 #1(1d65375 라우터 조립 선행) | REQ-DEPLOY-028 / AC-DEPLOY-019 |
| **M15 — 마지막 생성 연출 상태 세션 주입 (#4, LLM/orchestrator)** | 직전 생성 시퀀스/실행기 상태(예: `Seq 71`/`Exec 201`)를 세션 컨텍스트에 주입하여 후속 수정 지시가 정확 대상을 겨냥하도록 하고, **맹목적 수정보다 재생성(regeneration)을 선호**. 방금 만든 룩의 상태 미추적으로 후속 편집이 오대상(`Seq 1`/`Exec 1`)을 겨냥해 실패하던 결함 해소 | M14 | REQ-DEPLOY-030 / AC-DEPLOY-021 |
| **M16 — Gemini 캐시 만료 복구 + 오류 분류 (#5, LLM/orchestrator)** | Gemini 컨텍스트 캐시(rig/rulebook `CachedContent`) 만료 시 `403 PERMISSION_DENIED`/404 감지 → **캐시 재생성 후 재시도**(종단 실패 금지). 추가로 `"No API key"`(`ValueError`)를 `unexpected`가 아닌 **인증(auth) 오류로 분류**(오류 분류기에 캐시/키 케이스 추가) | M15 | REQ-DEPLOY-031 / AC-DEPLOY-022 |
| **M17 — rig-context 실제 풀 번호 명시 (#3, LLM/orchestrator)** | `get_rig_context`/프롬프트에 **실제 풀 번호(pool number)와 이름을 명시**하여 위치 인덱스와 실제 풀 번호의 혼동으로 존재하지 않는 오브젝트(예: `Group 3`) 선택 → "Illegal object" 실패를 제거. 명시적 대상(`Fixture 11 Thru 19`)은 회귀 통과 유지 | M16 | REQ-DEPLOY-029 / AC-DEPLOY-020 |
| **M18 — OSC 수신 포트 재바인드 복구 (#6, deploy-shell)** | 수신 포트 바인드(`server/bridge/osc.py` `_ReuseAddrOSCUDPServer(ThreadingOSCUDPServer)` `:61` + `_bind_receiver` `:228`; 재바인드 소진 시 `ReceivePortInUseError` `:241`)에 **동일 지정 포트 재바인드 전략**(SO_REUSEADDR 소켓 재사용/재시도) 도입 — 앱 비정상 종료 후 포트 점유로 `Address already in use` 재기동 실패를 복구. **임의 포트 조용한 드리프트 금지(REQ-DEPLOY-026 정합)**, 복구 불가 시 인간 친화적 오류 + 재설정 안내. **라이브·하드웨어 왕복 복구는 라이브 onPC 환경-게이트(deferred/manual N/A)** — 단위(포트 선점 시뮬레이션)만 자동 검증 | M17 | REQ-DEPLOY-032 / AC-DEPLOY-023 |

## D. 리스크

| 리스크 | 대응 |
|---|---|
| 코드 서명 인증서 미확보 → 서명/공증 게이트 검증 불가 | A.6 확정(서명 파이프라인만 작성); 게이트 통과 증거는 M10 환경-게이트 검증으로 분리(AC-DEPLOY-009/010은 환경-게이트). HIGH-RISK 구간이므로 조기 스파이크(SPIKE)로 notarytool 왕복 1회 de-risk(FEAS-4) |
| 배포 셸이 안전 게이트 우회 경로 신설 (보안 회귀) | REQ-DEPLOY-023/024 + AC-DEPLOY-014: 패키징 빌드에서 기존 단일 관문 아키텍처 테스트(AC-MVP-019) + 블랙리스트 승인(AC-MVP-004) 회귀를 CI 상시 실행 |
| **교차언어 OSC 송신 사각지대 (SAFETY-2) — M7 활성화** | AC-MVP-019는 Python import 경계만 검사. 셸 신규 표면(Tauri Rust/sidecar 컨트롤러/IPC)은 Python OSC 모듈을 import하지 않고도 `127.0.0.1:<console port>`로 raw UDP 송신 가능 → Python import 검사에 불가시. **대응(M7 활성화)**: AC-DEPLOY-014 ③의 Rust/Tauri 소스 스캔·wire-level 절(Stage-1에서 N/A 이연)을 **M7에서 활성화** — (a) `src-tauri/**/*.rs`+`Cargo.toml`/`Cargo.lock` **deny-all 정적 스캔**(raw socket/OSC 크레이트/포트 리터럴), (b) **실제 설정 send_port**(effective settings, 기본 `osc.py:105`=8000) **wire-level 싱크**로 "모든 OSC 송신" 열거 + 감사 "executed" 로그 1:1 대조 + **양성 관측(≥1건) assert** + 미열거 fail-closed + synthetic rogue 주입 증명, (c) Tauri capabilities 네트워크 플러그인 deny + shell을 sidecar-spawn만으로 스코프. AC-DEPLOY-027 신설. 확장 대상 가드: `test_architecture.py`(import 경계) + `test_deploy_safety_invariants.py`(AST allowlist) |
| **cross-site WebSocket hijacking (FEAS-9) — 신규 자격/제어 표면** | 현재 `server/web/app.py:137`의 `/ws` `accept()`(`:139`)가 origin/token/CORS 검사 0 → same-origin 미강제. 셸이 라이브 콘솔 제어 + 신규 자격 증명 표면을 앞단에 두므로 로컬 프로세스/브라우저 탭의 CSWSH가 실질 공격면. **대응(F5 RESOLVED)**: WS 유지 + Origin allowlist + per-launch 토큰 상수-시간 핸드셰이크(REQ-DEPLOY-002a, §A.4/§C M7.1). 잔여 loopback 리스너는 LOCAL-ONLY 심층방어로 수용 + Tauri capabilities로 보완. AC-DEPLOY-025 검증 |
| API 키 평문 유출 (설정 파일/로그) | REQ-DEPLOY-006~008: OS 자격 증명 저장소만, 설정 파일 credential-like 키 거부 유지, AC-DEPLOY-004 자동 검증(어떤 기록 파일에도 키 문자열 0건) |
| **크래시 덤프/예외 로거의 env 직렬화 → API 키 디스크 평문화 (DECIDE-M6)** | REQ-007이 키를 백엔드 프로세스 env로 주입하므로, 크래시 핸들러가 프로세스 env를 직렬화하면 평문 키가 디스크에 기록됨 = AC-DEPLOY-004 위반 벡터. **대응**: 텔레메트리 없음(로컬 로그만) + 크래시 덤프/예외 로거에서 프로세스 env 스크럽; AC-DEPLOY-004 스캔 대상에 크래시 덤프 포함 |
| 자격 증명 저장소 미가용/잠금/거부 → 평문 폴백 유혹 | REQ-DEPLOY-006a: 명시적 오류 + 세션 한정(in-memory) 키 폴백, 평문 디스크 저장 금지; AC-DEPLOY-016 자동 검증 |
| OSC 포트 드리프트로 onPC 연결 단절 | REQ-DEPLOY-026: 포트 사용 중 시 조용한 폴백 금지 + 재설정 안내 |
| PyInstaller onedir 네이티브 의존성(google-genai/anthropic/grpcio/keyring) 번들 실패·기동 지연 | onedir 확정(FEAS-1). **keyring 백엔드 발견은 entry-point 메타데이터 의존인데 PyInstaller가 strip → frozen에서 null 백엔드로 조용히 폴백(핀만으로 해결 안 됨)** → `--collect-all keyring` + keyring 백엔드 hidden-imports 명시(FEAS-2); 키 어댑터 AC를 플랫폼별 frozen onedir 스모크 빌드 안에서 검증 |
| Tauri sidecar 프로세스 누수(종료 시 백엔드 좀비) | REQ-DEPLOY-025 + **FEAS-5 Option C(belt-and-suspenders)**: Rust가 authoritative process-group kill(Unix setsid/setpgid, Windows KILL_ON_JOB_CLOSE Job Object) — 정상 종료·백엔드 크래시 담당; 백엔드는 `terminate_process_tree`(`launcher.py:208`) SIGTERM-first 트리 kill 유지 + **parent-liveness watchdog**(force-quit 시 self-reap — Unix force-quit는 `RunEvent::Exit` 미발화) 추가; 재기동 `require_ports_available`(`launcher.py:162`) fail-closed 넷. ⚠️ `CommandChild.kill()`은 부트로더 PID만 kill. AC-DEPLOY-026(정상/크래시/force-quit 3경로 잔여 0) — AC-015 ①② 확장 |
| **서명된 sidecar의 keychain 도달성 (M9 이연)** | M9(코드 서명) 후 서명·hardened runtime의 keychain ACL이 서명된 sidecar의 OS keychain 접근을 막고 Tauri 호스트만 가능해질 위험. **대응**: F5'(키 커스터디 = Python keyring 직접) 잔여 항목으로 기록 — **M9 검증 시** 서명된 sidecar가 keychain 도달 불가하고 Tauri 호스트만 가능한 경우에 **한해** 키 커스터디를 재검토(Rust 측 자격 플러그인 경유). M7을 블록하지 않음(§A.2 F5' 전제) |
| macOS Gatekeeper quarantine / Windows SmartScreen로 최초 실행 차단 | REQ-DEPLOY-014/015 서명·공증; AC-DEPLOY-009/010 환경-게이트 검증(spctl/signtool). SmartScreen 완화는 평판 누적 의존(OV는 즉시 미해소, EV만 즉시 신뢰 — FEAS-7) |
| **단위 스위트 사각지대 — 하드웨어+LLM+번들 결합 통합 결함 (v0.3.0 라이브 E2E 발견)** | 983-test 단위 스위트가 결함 #1~#6(라우터 미조립·startup 키 미주입·LLM 대상 매핑·캐시 만료·OSC 포트)을 모두 통과시킴 — 이 결함들은 실제 onPC + 실제 Gemini + 패키지 번들 결합에서만 발현. **대응**: (a) #2는 `build_runtime` **조립(assembly) 지점 회귀 테스트**(`server/tests/test_web_serve.py`)로 단위 재현(라우터 마운트·startup 키 주입), (b) 오류 분류/캐시 복구(#5)·대상 상태 주입(#4)·rig-context(#3)는 오류 주입·컨텍스트 assert로 단위화, (c) #6·서명/공증은 라이브·하드웨어 환경-게이트로 분리. provenance: `copilot-live-demo-findings` |

## E. 자가 검증 계획

- M10에서 acceptance.md의 AC 매트릭스 전 항목을 자동/반자동 테스트로 검증하고 증거(테스트 출력·서명 검증 로그)를 progress.md §E.2에 기록한다.
- **안전 불변식 회귀(AC-DEPLOY-014)** 는 CI에서 반복 실행 가능한 자동 테스트로 구현한다 — 패키징된 셸을 감싼 상태에서도 SPEC-COPILOT-MVP-001의 단일 관문/블랙리스트 승인 불변식이 유지됨을 확인(수동 검증 불인정).
- **키 평문 미유출(AC-DEPLOY-004)** 은 앱이 쓰는 모든 파일(설정·로그·캐시)에 API 키 문자열이 0건임을 자동 스캔한다.
- 서명·공증(AC-DEPLOY-009/010)은 인증서를 요구하므로 **환경-게이트 반자동 검증**(SPEC-COPILOT-MVP-001의 라이브 onPC gap과 동일 규율 — 인증서 부재 시 explicit N/A 기록, 확보 시 실행)으로 관리한다.

## F. 결정 요약 (plan-audit fold-in v0.2.0 반영)

Implementation Kickoff에서 해소된 결정 원장. **Stage-1 run 진입을 블록하는 오픈 항목 = 0.**

### 사전 확정 결정 (Kickoff 기록)

- **AppName / 번들 식별자**: "GrandMA3 Copilot" / `com.grandma3copilot.app` (config 경로·Keychain 서비스명·Tauri identifier·코드 서명 identity 앵커). ⚠️ "GrandMA3"는 MA Lighting 상표 → 공개 배포 전 중립적 리네이밍 가능성(번들 식별자는 코드서명 앵커이므로 조기 확정 권장) — DECIDE-M1.
- **대상/아키텍처**: macOS universal2(arm64+x86_64, min macOS 12) + Windows x86_64 — 두 플랫폼 지금 빌드·검증 — DECIDE-M2.

### 6건 RESOLVED

| # | 결정 | 값 | 근거 |
|---|---|---|---|
| F1 | Tier L 산출물 | ✅ 최소 research.md를 M6 전 필수, design.md는 plan.md에 접음 | §A.0 / FEAS-8 |
| F2 | 설정 파일 포맷 | ✅ TOML(stdlib tomllib 재사용). UI↔백엔드 스키마 계약은 M1 확정 | §A.1 |
| F3 | 키 저장 백엔드 | ✅ keyring 승인, Stage-1 = Python 직접 접근 (공통 인터페이스는 F5'로 Stage-2 이연) | §A.2 |
| F4 | first-run 온보딩 | ✅ 배너/배지 안내(강제 마법사 아님) | §A.3 |
| F7 | 코드 서명 조달 | ✅ 인증서 미보유 → 파이프라인만 작성, AC-009/010 환경-게이트 N/A. OV vs EV·HSM 키·notarytool 크리덴셜·hardened runtime/entitlements/stapling 사실 기록 | §A.6 / FEAS-3/7·DECIDE-M7 |
| F8 | onefile vs onedir | ✅ **onedir**(두 플랫폼); macOS는 notarizable .app/.dmg 컨테이너 | §A.7 / FEAS-1/6·DECIDE-M13 |

### Stage-2 M7 kickoff RESOLVED (2026-07-21, v0.4.0)

M7 착수를 위해 F5·F5'를 해소한다. **M7 착수 블록 오픈 결정 = 0.**

| # | 결정 | 값 | 근거 |
|---|---|---|---|
| F5 | Stage 2 sidecar↔UI 통신 | ✅ **127.0.0.1 WebSocket 유지 + Origin allowlist + per-launch 토큰 핸드셰이크**(REQ-DEPLOY-002a) — 프로토콜 v1 불변, 단일 전송이 브라우저/Tauri 양 모드 서빙, FEAS-9 CSWSH 차단. 잔여 loopback 리스너는 LOCAL-ONLY 심층방어 수용 | §A.4 / FEAS-9 |
| F5' | Stage-1/2 공통 키 인터페이스 (키 커스터디) | ✅ **Python `keyring` 백엔드 sidecar 직접 접근 유지** — Rust/Tauri는 비밀 미접촉(spawn/수명주기만). `keystore.py` 무변경 재사용. 잔여: 서명된 sidecar keychain 도달성은 M9 검증 항목 | §A.2 / DECIDE-M7(M9) |

### 1건 DEFERRED — Stage-2 kickoff (M8/M9 — 별도 kickoff)

| # | 결정 | 스코프 | 비고 |
|---|---|---|---|
| F6 | 업데이트 매니페스트/아티팩트 호스팅 + updater 서명 키 관리 | Stage-2, M8만 블록 | 2개 결정 번들. **본 M7 kickoff 스코프 아님** — M8(자동 업데이트) 별도 kickoff에서 해소 |
