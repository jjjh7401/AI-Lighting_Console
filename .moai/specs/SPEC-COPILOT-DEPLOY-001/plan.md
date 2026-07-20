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

### A.1 설정·config 저장 모델 (데이터 모델 — 최우선 검토)
- 현재 비민감 설정은 리포 파일 `config/provider.toml`(active 프로바이더 + 모델 핀 + 캐시/폴백 파라미터)에 있고, OSC 포트/임포트 디렉터리는 `serve.py` CLI 인자다. 패키징된 앱은 **사용자 쓰기 가능 경로**에 설정을 저장해야 한다.
- ✅ **방향**: 비민감 설정을 OS별 표준 사용자 config 경로(macOS `~/Library/Application Support/GrandMA3 Copilot/`, Windows `%APPDATA%\GrandMA3 Copilot\`)에 저장. 번들된 `provider.toml`은 기본값(seed)으로만 사용하고, 사용자 설정이 이를 오버레이한다. (경로 앵커 = 번들 식별자 `com.grandma3copilot.app` / AppName "GrandMA3 Copilot")
- ✅ **RESOLVED (F2)**: 설정 파일 포맷 = **TOML**(기존 stdlib `tomllib` 로더 재사용, 의존성 0). 재사용 우세로 확정. **UI ↔ 백엔드 config 스키마 계약(필드·검증)은 M1에서 확정**한다(진짜 열린 항목).
- **불변**: 자격 증명은 이 설정 파일에 절대 포함하지 않는다 (로더의 credential-like 키 거부 제약 유지 — REQ-DEPLOY-007/008).

### A.2 보안 키 저장 백엔드 (Secured — 결정 필요)
- API 키를 OS 자격 증명 저장소에 저장·조회하는 계층 필요 (macOS Keychain / Windows Credential Manager).
- ✅ **RESOLVED (F3)**: **keyring 의존성 승인**. Python `keyring` 라이브러리 — macOS Keychain + Windows Credential Manager를 단일 인터페이스로 지원, 성숙·크로스플랫폼. **Stage 1 = Python 백엔드가 keyring에 직접 접근**. 단순성 사다리상 자체 구현보다 우세.
- ⏸️ **DEFERRED — Stage-2 kickoff**: `[NEEDS CLARIFICATION: Stage-1/Stage-2 공통 키 인터페이스 — Stage 2(Tauri)에서 Rust 측 OS 자격 증명 플러그인 경유 vs Python keyring 직접 접근 유지]` *(Stage-2-scoped)* — Stage 1은 이미 확정(Python 직접). 두 Stage 공통 키 인터페이스(키 조회 → 백엔드 env 주입) 확정은 Stage-2 kickoff에서 수행하며, Stage-1 run 진입을 블록하지 않는다.
- 키는 **런타임에만** 백엔드 프로세스 env(`GEMINI_API_KEY`/`ANTHROPIC_API_KEY`)로 주입하고 디스크 평문화하지 않는다.

### A.3 설정 UI 흐름 (UX — 변경 가능성 높음)
- 인앱 설정 화면: 프로바이더 키 입력(마스킹), OSC 콘솔 송신 포트·피드백 수신 포트, 플러그인 임포트 디렉터리, 활성 프로바이더 선택. 기존 React SPA(`ui/`)에 설정 화면 + 상태 표시를 추가한다.
- responder provisioning 가이드(플러그인 설치 버튼 + onPC 로드/ OSC 출력 포트 설정 안내)와 health 상태 배지도 UX의 일부.
- ✅ **RESOLVED (F4)**: 최초 실행(first-run) 온보딩 = **배너/배지 안내**(강제 설정 마법사 아님) — 키 미설정 시 비침습적 배너로 설정 UI를 유도한다. (실질 UX 포크지만 M1 블록 아님 — M3/M5에서 구현)

### A.4 Stage 2 셸 선택 — Tauri v2 (primary) vs Electron (대안)
- ✅ **결정됨(사전 합의)**: **Tauri v2** primary. 근거: 경량 번들(시스템 웹뷰), 네이티브 창/트레이/updater 플러그인, Rust sidecar 관리. **Electron은 대안으로만 문서화**(JS 전용 툴체인 선호 시, 번들 크기 증가 트레이드오프).
- Tauri sidecar로 PyInstaller 빌드 백엔드를 번들·기동/종료 관리. UI는 동일 `ui/dist`를 Tauri 창이 로드. (Tauri v2 primary vs Electron 대안은 사전 합의로 확정 — 위 ✅.)
- ⏸️ **DEFERRED — Stage-2 kickoff**: `[NEEDS CLARIFICATION: Stage 2 sidecar ↔ UI 통신 — 기존 WebSocket(127.0.0.1) 유지 vs Tauri IPC 병용]` *(Stage-2-scoped, M7만 블록 — Stage-1 run 진입 블록 아님)*. 결정 기준:
  - **최소 변경 축**: 기존 백엔드가 WebSocket 서버이므로 sidecar가 로컬 포트를 열고 Tauri 웹뷰가 접속하는 방식이 최소 변경. 포트 충돌·수명주기(REQ-DEPLOY-025/026)와 직결.
  - **보안/오리진 축 (FEAS-9 신규)**: `127.0.0.1` ws:// 제어 채널은 **same-origin 미강제** — 로컬 프로세스/브라우저 탭이 접속 가능한 cross-site WebSocket hijacking 공격면이다. 셸이 라이브 콘솔 제어 + 신규 자격 증명 표면을 앞단에 두므로 실질 공격면. **WS를 유지하면 origin/token 핸드셰이크가 필수**, 또는 **Tauri IPC(in-process)로 노출 자체를 제거**. AC-DEPLOY-014에 반영.

### A.5 자동 업데이트 메커니즘 (아키텍처 + 호스팅 — 결정 필요)
- Stage 2: Tauri updater 플러그인(서명된 업데이트 매니페스트 + 아티팩트, 서명 검증 후 적용 — REQ-DEPLOY-017). updater 재시작 시 안전상태 보존은 REQ-DEPLOY-027(SAFETY-4)로 앵커링.
- Stage 1: PyInstaller에는 내장 updater가 없음 → **버전 확인 + 알림(수동 재설치 안내)** 로 한정 (REQ-DEPLOY-016 capability gate).
- ⏸️ **DEFERRED — Stage-2 kickoff**: `[NEEDS CLARIFICATION: 업데이트 매니페스트·아티팩트 호스팅 위치 — GitHub Releases vs 자체 호스팅]` 및 `[NEEDS CLARIFICATION: Tauri updater 서명 키(별도, 코드 서명 인증서와 무관) 관리 주체]` *(Stage-2-scoped, M8만 블록 — Stage-1 run 진입 블록 아님, 2개 결정 번들)*.

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
- **선행 의존**: SPEC-COPILOT-MVP-001 완료가 전제 (`depends_on`). 라이브 onPC 잔여 gap(키 확보 후 왕복 측정 등)은 본 SPEC과 병렬 진행 가능하나 배포 검증(M10)에는 무관.
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
| **M7 — Tauri v2 셸 + 백엔드 sidecar** | Tauri 네이티브 창이 동일 `ui/dist` 로드, PyInstaller 백엔드를 sidecar로 번들·기동/종료 관리, 트레이 + 연결 상태. Electron 대안 문서화. **⚠️ (FEAS-5) sidecar 종료는 부트로더 PID 하나가 아니라 process-GROUP/tree 종료**(추출된 grandchild Python 프로세스 좀비/포트 점유 방지) + crash/force-quit 경로까지 정리. sidecar↔UI 통신 방식은 Stage-2 kickoff 결정(§A.4, FEAS-9 보안 축 포함) | M6 | REQ-DEPLOY-001, 002, 025 |
| **M8 — 자동 업데이트** | Tauri updater(버전 확인 → 다운로드 → 승인 후 적용) + 서명 검증 통과 아티팩트만 적용(실패 시 현재 버전 유지). **updater 재시작 시 라이브 잠금/승인 대기/감사 로그 연속성 보존(REQ-027, SAFETY-4)**. 매니페스트/아티팩트 호스팅·updater 서명 키는 Stage-2 kickoff 결정(§A.5) | M7 | REQ-DEPLOY-016(Stage2), 017, 027 |
| **M9 — 코드 서명·공증 + 재현 가능 크로스플랫폼 빌드 (HIGH-RISK)** | macOS Developer ID 서명 + notarization(**hardened runtime + entitlements plist(`com.apple.security.cs.*`) + stapling** — FEAS-3), Windows Authenticode 서명(`signtool verify /pa`). 문서화된 빌드 절차 + 의존성 핀(uv.lock/package-lock/Cargo·Tauri 락). 비공개 자원 의존 0. **데스크톱 배포 최고 난도 구간 — "기계적 마무리" 아님**(FEAS-4); 조기 스파이크(위)로 de-risk. 인증서 부재 시 파이프라인 구성 + AC-009/010 환경-게이트 N/A | M7 (Stage2 아티팩트), M6 (Stage1 아티팩트도 서명 대상), SPIKE(조기 검증) | REQ-DEPLOY-014, 015, 021, 022 |

### 통합 검증

| 마일스톤 | 내용 | 의존성 | 주요 REQ |
|---|---|---|---|
| **M10 — 배포 통합 검증** | 양 Stage·양 플랫폼(macOS/Windows) 아티팩트 기동·설정·provisioning·health·오류 UX E2E. **안전 불변식 회귀**: 패키징된 셸에서 SPEC-COPILOT-MVP-001 단일 관문/블랙리스트 승인/감사 로그 불변식이 유지됨을 자동 테스트로 확인(AC-DEPLOY-014). 서명/공증은 인증서 확보 후 환경-게이트 검증 | M1~M9 전체 | REQ-DEPLOY-023, 024 + 전 AC |

> 순서 비고: Stage 1(M1~M6)이 완성되면 그 자체로 배포 가능한 MVP 형태다. Stage 2(M7~M9)는 M6의 PyInstaller 백엔드를 sidecar로 재사용하므로 M6 이후 착수한다. **M9(서명·공증)는 Stage 1·2 양 아티팩트 모두에 적용되는 HIGH-RISK 구간이며, "기계적 마무리 단계"가 아니다** — 서명/공증 제약(entitlements/hardened runtime/stapling, HSM 키 보관, notarytool 크리덴셜)이 M6 패키징 형태·M7 sidecar 구조로 역류하므로, notarytool 왕복 1회를 확인하는 **조기 스파이크(SPIKE)를 M6~M7과 병행**한다(FEAS-4).

## D. 리스크

| 리스크 | 대응 |
|---|---|
| 코드 서명 인증서 미확보 → 서명/공증 게이트 검증 불가 | A.6 확정(서명 파이프라인만 작성); 게이트 통과 증거는 M10 환경-게이트 검증으로 분리(AC-DEPLOY-009/010은 환경-게이트). HIGH-RISK 구간이므로 조기 스파이크(SPIKE)로 notarytool 왕복 1회 de-risk(FEAS-4) |
| 배포 셸이 안전 게이트 우회 경로 신설 (보안 회귀) | REQ-DEPLOY-023/024 + AC-DEPLOY-014: 패키징 빌드에서 기존 단일 관문 아키텍처 테스트(AC-MVP-019) + 블랙리스트 승인(AC-MVP-004) 회귀를 CI 상시 실행 |
| **교차언어 OSC 송신 사각지대 (SAFETY-2)** | AC-MVP-019는 Python import 경계만 검사. 셸 신규 표면(Tauri Rust/sidecar 컨트롤러/updater/IPC)은 Python OSC 모듈을 import하지 않고도 `127.0.0.1:<console port>`로 raw UDP 송신 가능 → Python import 검사·소스 스캔 모두에 불가시. **대응**: AC-DEPLOY-014 ③를 Python+Rust/Tauri 전 언어 소스 스캔으로 확장 + "모든 OSC 송신"을 wire-level(콘솔 수신 포트 패킷 관측)로 열거 + 미열거 신규 모듈 fail-closed |
| API 키 평문 유출 (설정 파일/로그) | REQ-DEPLOY-006~008: OS 자격 증명 저장소만, 설정 파일 credential-like 키 거부 유지, AC-DEPLOY-004 자동 검증(어떤 기록 파일에도 키 문자열 0건) |
| **크래시 덤프/예외 로거의 env 직렬화 → API 키 디스크 평문화 (DECIDE-M6)** | REQ-007이 키를 백엔드 프로세스 env로 주입하므로, 크래시 핸들러가 프로세스 env를 직렬화하면 평문 키가 디스크에 기록됨 = AC-DEPLOY-004 위반 벡터. **대응**: 텔레메트리 없음(로컬 로그만) + 크래시 덤프/예외 로거에서 프로세스 env 스크럽; AC-DEPLOY-004 스캔 대상에 크래시 덤프 포함 |
| 자격 증명 저장소 미가용/잠금/거부 → 평문 폴백 유혹 | REQ-DEPLOY-006a: 명시적 오류 + 세션 한정(in-memory) 키 폴백, 평문 디스크 저장 금지; AC-DEPLOY-016 자동 검증 |
| OSC 포트 드리프트로 onPC 연결 단절 | REQ-DEPLOY-026: 포트 사용 중 시 조용한 폴백 금지 + 재설정 안내 |
| PyInstaller onedir 네이티브 의존성(google-genai/anthropic/grpcio/keyring) 번들 실패·기동 지연 | onedir 확정(FEAS-1). **keyring 백엔드 발견은 entry-point 메타데이터 의존인데 PyInstaller가 strip → frozen에서 null 백엔드로 조용히 폴백(핀만으로 해결 안 됨)** → `--collect-all keyring` + keyring 백엔드 hidden-imports 명시(FEAS-2); 키 어댑터 AC를 플랫폼별 frozen onedir 스모크 빌드 안에서 검증 |
| Tauri sidecar 프로세스 누수(종료 시 백엔드 좀비) | REQ-DEPLOY-025 + FEAS-5: **process-GROUP/tree 종료**(부트로더 PID만 kill 시 추출된 grandchild Python 좀비/포트 점유) + crash/force-quit 경로; AC-DEPLOY-015를 process-tree scan으로 강화 |
| macOS Gatekeeper quarantine / Windows SmartScreen로 최초 실행 차단 | REQ-DEPLOY-014/015 서명·공증; AC-DEPLOY-009/010 환경-게이트 검증(spctl/signtool). SmartScreen 완화는 평판 누적 의존(OV는 즉시 미해소, EV만 즉시 신뢰 — FEAS-7) |

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

### 2건 DEFERRED — Stage-2 kickoff (Stage-1 run 진입 블록 아님)

| # | 결정 | 스코프 | 비고 |
|---|---|---|---|
| F5 | Stage 2 sidecar↔UI 통신 (WebSocket 유지 vs Tauri IPC) | Stage-2, M7만 블록 | 결정 기준에 **보안/오리진 축(FEAS-9)** 추가 — `127.0.0.1` ws://는 same-origin 미강제(cross-site WebSocket hijacking) → WS 유지 시 origin/token 핸드셰이크 필수, 또는 Tauri IPC로 노출 제거. AC-DEPLOY-014 반영 |
| F6 | 업데이트 매니페스트/아티팩트 호스팅 + updater 서명 키 관리 | Stage-2, M8만 블록 | 2개 결정 번들 |
