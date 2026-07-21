# SPEC-COPILOT-DEPLOY-001 — 수용 기준 (acceptance)

> v0.2.0 (draft) — 기능이 검증된 MVP(SPEC-COPILOT-MVP-001)에 배포 셸을 씌우는 SPEC의 AC. 배포 형태(Stage 1 PyInstaller onedir / Stage 2 Tauri), 인앱 설정 + OS 자격 증명 저장, responder provisioning, health UI, 코드 서명·공증, 자동 업데이트, 오류 UX, 안전 불변식 보존을 검증한다. (plan-audit fold-in: AC-014 ③ 구체화, AC-016~018 신설, AC-004/009/011/015 강화)
> 검증 환경 주석: 서명·공증(AC-DEPLOY-009/010)은 코드 서명 인증서를 요구하므로 **환경-게이트 반자동**이다 — SPEC-COPILOT-MVP-001의 라이브 onPC gap 규율(인증서/콘솔 부재 시 explicit N/A, 확보 시 실행)을 동일 적용한다. ⛔ `[SCOPE-2026-07-22: DESCOPED — 이 검증 환경 주석은 무효. AC-009/010은 "인증서 확보 대기 환경-게이트"가 아니라 **close 조건 밖**이다. 대체 검증 = AC-DEPLOY-030(ad-hoc 전달 아티팩트, 인증서 불요)]`
> v0.3.0 라이브 E2E 하드닝 fold-in: §D.11에 결함 #2~#6에 대한 AC-DEPLOY-019~023 신설(provenance `copilot-live-demo-findings`). AC-019(#2 기동 시 키 주입)은 `build_runtime` 조립 수준 단위 테스트, AC-023(#6 OSC 수신 포트)은 라이브·하드웨어 부분을 deferred/manual N/A로 분리. 결함 #1은 commit `1d65375`에서 이미 수정(신규 AC 미앵커링).
> v0.4.0 Stage-2 M7 kickoff fold-in (+ plan-audit remediation D1–D10): §D.12에 M7(Tauri v2 셸 + Python sidecar) 수용 기준 **AC-DEPLOY-024~029** — Tauri 셸 기동(024), F5 sidecar↔UI Origin/token 핸드셰이크(025, REQ-002a/FEAS-9), 프로세스-트리 teardown 3경로 잔여 0(026, AC-015 ①② 확장, watchdog EOF-primary+bounded latency), SAFETY-2 교차언어 이중 스캔(027, AC-014 ③b/③c/③d 활성화 — Layer① `src-tauri/` 존재 게이트+`files_scanned>0`+필수 rogue 픽스처, Layer② 실제 설정 send_port+양성 관측), 키 커스터디 불변(028), **per-launch 토큰 비밀 유지(029 — D4c 신설)**. 각 AC는 env-gate를 명시(NOW=macOS arm64 dev/ad-hoc; AC-027 Layer①=M7.4 scaffold 이후, Layer②=NOW; universal2·Windows·실제 notarization=env-gate N/A). **M8/M9은 Stage-2-DEFERRED — 본 kickoff AC 미포함.** Stage-1 + 하드닝 AC(001~023)는 전부 불변 보존.

> **v0.5.0 배포 전제 축소 개정 (2026-07-22)**: 사용자 결정으로 ⛔ **DESCOPED** — AC-DEPLOY-009(macOS 서명·공증) / AC-DEPLOY-010(Windows Authenticode) / AC-DEPLOY-011(자동 업데이트) / AC-DEPLOY-018(updater 재시작 안전상태). ⏸️ **DEFERRED-WINDOWS** — AC-DEPLOY-013의 Windows 절(macOS arm64 절은 존속). 🆕 **신설** — **AC-DEPLOY-030**(ad-hoc 서명 `.app` → `.dmg` 전달 + 한국어 설치 안내, REQ-DEPLOY-014a). **어떤 AC도 삭제하지 않고** 제자리에 `[SCOPE-2026-07-22: …]` 마커를 부착했다(열거: `grep -rn "\[SCOPE-2026-07-22:" .moai/specs/SPEC-COPILOT-DEPLOY-001/`). 본 개정은 **스코프만** 변경하며 어떤 AC도 PASS로 표시하지 않는다.

## D. AC 매트릭스

### D.1 배포 형태 AC

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-001 | 단일 자체완결 아티팩트 실행 → 로컬 백엔드 기동 → 로컬 UI 표시 | 반자동: ① Stage 1 — 빌드된 onefile 실행 파일을 더블클릭(또는 실행) → 백엔드 프로세스 기동 + 기본 브라우저가 로컬 UI URL 오픈 확인; ② Stage 2 — Tauri 앱 실행 → 네이티브 창에 UI 로드 + 백엔드 sidecar 기동 확인. 자동: 백엔드가 `ui/dist` 정적 자산을 서빙함을 HTTP 응답으로 확인 | REQ-DEPLOY-001~003 |
| AC-DEPLOY-002 | 로컬 전용(local-only) — 원격 백엔드 미의존 | 자동(아키텍처): ① 백엔드 bind 주소가 `127.0.0.1`(비 0.0.0.0/공인)임을 확인 ② OSC 송수신이 localhost UDP임을 확인 ③ 소스 스캔 — 원격 클라우드 백엔드 엔드포인트 의존 0건(LLM API 제외). 반자동: 인터넷 차단(LLM API 제외) 상태에서도 UI·설정·health가 동작 | REQ-DEPLOY-004 |

### D.2 인앱 설정 + 보안 키 저장 AC

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-003 | 터미널 없이 설정(키/포트/임포트 디렉터리) 읽기·저장 | 자동/반자동: 설정 UI에서 GEMINI_API_KEY·(ANTHROPIC_API_KEY)·OSC 송신/수신 포트·플러그인 임포트 디렉터리를 입력·저장 → 재기동 후 비민감 설정 지속 + 키는 자격 증명 저장소에서 조회됨을 확인 | REQ-DEPLOY-005 |
| AC-DEPLOY-004 | API 키는 OS 자격 증명 저장소에만 — 평문 파일 0건 | 자동: ① 키 저장 어댑터가 macOS Keychain / Windows Credential Manager에 저장함을 (플랫폼별) 확인 ② **앱이 쓰는 모든 파일(설정·로그·캐시·감사 로그·크래시 덤프)을 스캔 → 저장한 키 문자열 0건** — 크래시 핸들러/예외 로거가 프로세스 env를 직렬화하지 않음(env 스크럽)을 assert(DECIDE-M6) ③ 프로바이더 클라이언트 기동 시 키가 백엔드 프로세스 env로만 주입되고 config 로더의 credential-like 키 거부가 유지됨을 assert ④ **자격 증명 저장소 미가용/잠금/거부 서브-검사는 AC-DEPLOY-016 참조** | REQ-DEPLOY-006~007 |
| AC-DEPLOY-005 | 비민감 설정은 사용자 config 경로 저장 + 자격 증명 미포함 | 자동: 저장된 사용자 config 파일 위치가 OS별 표준 경로이고, 내용에 자격 증명 키 0건(로더 거부 규칙 통과) 확인 | REQ-DEPLOY-008 |
| AC-DEPLOY-016 | 자격 증명 저장소 미가용/잠금/거부 시 평문 미저장 + 세션 한정 폴백 동작 | 자동: ① 저장소 미가용·잠금·접근 거부를 (mock/시뮬레이션) 재현 → **앱이 쓰는 어떤 파일에도 평문 키 문자열 0건**(정상경로 스캔이 건드리지 않는 실패 분기까지 커버) assert ② 명시적 오류 표면화 확인 ③ 세션 한정(in-memory) 키 입력으로 프로바이더 기동이 동작하고(env 주입), 세션 종료 시 키가 디스크에 남지 않음을 확인 | REQ-DEPLOY-006a |

### D.3 CopilotResponder provisioning AC

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-006 | responder 플러그인 번들 포함 + 임포트 디렉터리 설치 | 자동: ① 배포 아티팩트에 `copilot_responder.lua`(+임포트 XML)가 포함됨을 확인 ② 설치 동작 → 설정된 임포트 디렉터리에 플러그인 파일이 복사됨을 확인(임시 디렉터리 대상) | REQ-DEPLOY-009~010 |
| AC-DEPLOY-007 | responder 로드 + OSC 출력 포트 설정 안내 표시 | 반자동(UI): provisioning 후 가이드 UI가 onPC 플러그인 로드 절차 + onPC OSC 출력을 앱 피드백 수신 포트로 설정하라는 안내를 표시함을 확인 | REQ-DEPLOY-011 |
| AC-DEPLOY-017 | 앱이 발행하는 `Import Plugin` OSC 송신이 단일 안전 관문 통과 + 감사 로그 1:1 (SAFETY-3) | 자동: provisioning의 "deploy verb→file+Import" 경로에서 앱이 `Import Plugin` 콘솔 실행을 발행하면 ① 그 OSC 송신이 SPEC-COPILOT-MVP-001 단일 관문(REQ-MVP-029)을 경유함을 assert(게이트-pass 레코드에 등장) ② **게이트-pass 레코드 ↔ 감사 로그가 1:1로 대응**(앱 발행 Import Plugin 송신 건마다 감사 로그 항목 존재)을 assert ③ 파일 복사만 게이트 밖이고, 게이트 미경유 Import Plugin 송신 0건 | REQ-DEPLOY-011a, 024 |

### D.4 연결/상태 표시 AC

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-008 | health 상태(online/console_offline/responder_degraded) 표면화 + 전이 반영 | 자동/반자동: HealthMonitor 상태 전이(콘솔 무응답 → console_offline, responder 무응답 → responder_degraded, 회복 → online)를 시뮬레이션 → UI 배지가 각 상태를 즉시 반영함을 확인(기존 status 푸시 경로 재사용) | REQ-DEPLOY-012~013 |

### D.5 코드 서명·공증 AC — ⛔ DESCOPED (2026-07-22) / 대체 = AC-DEPLOY-030

> ⛔ `[SCOPE-2026-07-22: DESCOPED — AC-DEPLOY-009/010 두 행. 사용자 지시 "거창하게 mac OS 서명이나 공증 필요없어"(2026-07-22)로 서명·공증이 스코프 밖이 되어 **"환경-게이트 N/A(인증서 확보 대기)"에서 "close 조건 아님"으로 전환**된다. 두 행은 재개 대비 **원문 그대로 보존**한다. 대체 수용 기준 = 아래 **AC-DEPLOY-030**]`

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| **AC-DEPLOY-030** *(v0.5.0 신설 — AC-009 대체)* | ad-hoc 전달 아티팩트 — ad-hoc 서명 `.app`이 무결하게 봉인되고, drag-to-Applications `.dmg`로 패키징되며, quarantine 해제 절차를 담은 한국어 설치 안내가 동봉된다 | **반자동(NOW — 인증서/하드웨어 불요, macOS arm64)**: ① 빌드된 `GrandMA3 Copilot.app`에 대해 `codesign --verify --strict` **exit 0** 확인 + `codesign -dv`가 ad-hoc 서명(`flags=0x2(adhoc)`)임을 확인 ② `npm run shell:package`(→ `packaging/make_dmg.sh`)가 `dist/GrandMA3-Copilot-<version>.dmg`를 생성하고, 스크립트가 **입력 `.app`의 seal을 패키징 전에 재검증**함을 확인(미실링 입력이면 non-zero 종료) ③ `.dmg` 마운트 → `.app` 추출 → `codesign --verify --strict`가 여전히 exit 0(패키징이 seal을 손상시키지 않음) ④ 최종 사용자 안내 문서(`INSTALL.ko.md`)가 산출물과 함께 제공되고, quarantine 해제 두 경로(`xattr -dr com.apple.quarantine …` / 시스템 설정 → 개인정보 보호 및 보안 → "그래도 열기")를 포함함을 문서 검수. **명시적 비-기준**: `spctl --assess --type execute` **거부(exit 3)는 실패가 아니라 기대 결과**다 — 공증 부재의 알려진 귀결이며 통과를 요구하지 않는다. **env-gate N/A 없음** | REQ-DEPLOY-014a |
| AC-DEPLOY-009 ⛔ **DESCOPED** | macOS Developer ID 서명 + notarization | **환경-게이트 반자동**(Developer ID 인증서 요구): 대상은 **notarizable universal2(arm64+x86_64) .app/.dmg 컨테이너**(bare Mach-O 아님 — onedir 트리를 담음, FEAS-6). 서명·공증된 아티팩트에 대해 `spctl --assess --type execute`(또는 `codesign --verify` + notarytool 이력)로 Gatekeeper 통과 확인 + **stapling 검증**(`stapler validate`). 서명 파이프라인은 hardened runtime + entitlements plist(`com.apple.security.cs.*`) 포함(FEAS-3). 인증서 부재 환경에서는 서명 파이프라인 구성 존재 + explicit N/A 기록. ⚠️ **이중 환경-게이트**: 서명 인증서 부재(Developer ID)와 **별개로**, 대상 아키텍처 **universal2 자체**도 현재 arm64 전용 빌드 호스트에서는 환경-게이트다 — arm64 전용 CPython이라 universal2 미생성(universal2 CPython + `_pydantic_core`/`jiter` universal2 wheel 필요 — research.md §C.6). 즉 완전 검증에는 (a) 아키텍처 게이트(universal2 빌드 환경)와 (b) 인증서 게이트(Developer ID)가 **둘 다** 충족돼야 한다. arm64 서명 검증은 ad-hoc identity로 지금 dry-verify 가능(research.md §C.5) | REQ-DEPLOY-014 |
| AC-DEPLOY-010 ⛔ **DESCOPED** | Windows Authenticode 서명 | **환경-게이트 반자동**(Authenticode 인증서 요구): 서명된 인스톨러/실행 파일에 대해 `signtool verify /pa`로 서명 유효성 확인. 인증서 부재 환경에서는 서명 파이프라인 구성 존재 + explicit N/A 기록 | REQ-DEPLOY-015 |

### D.6 자동 업데이트 AC — ⛔ DESCOPED (2026-07-22)

> ⛔ `[SCOPE-2026-07-22: DESCOPED — AC-DEPLOY-011. 사용자가 자동 업데이트에서 **"빼기 · 수동 재배포"**를 선택(2026-07-22). 새 버전은 새 `.dmg`를 손으로 전달하므로 updater 흐름·서명 검증 차단 단위 테스트 모두 close 조건이 아니다. 원문 보존]`

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-011 ⛔ **DESCOPED** | 자동 업데이트 + 서명 검증 통과 아티팩트만 적용 | **자동(CI 상시, 수동 검증 불인정) — REQ-017 서명 검증-실패-차단 단위 테스트**: 서명 검증 실패 아티팩트 주입 → 적용 차단 + 현재 버전 유지를 자동 단위 테스트로 assert(TRACE-2 — updater 서명키는 코드서명 인증서와 무관하므로 인증서 부재 핑계 없음). **반자동(엔드투엔드 updater 흐름, Stage-2 마일스톤)**: ① Stage 2 — 업데이트 매니페스트에 신버전 제시 → 사용자 승인 → 서명 검증 통과 아티팩트만 적용(재기동) 확인 ② Stage 1 — 신버전 감지 시 알림(수동 재설치 안내) 표시 확인 | REQ-DEPLOY-016~017 |

### D.7 오류 UX AC

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-012 | 3대 오류(콘솔 오프라인 / responder 미로드 / 키 부재·무효) 인간 친화적 한국어 안내 | 자동/반자동: ① console_offline 재현 → 스택 트레이스 아닌 원인+조치 한국어 안내 ② responder 미로드 재현 → 로딩·OSC 출력 설정 안내 ③ 키 부재/무효 재현 → 설정 UI 유도 메시지 + **raw SDK 오류 원문 문자열 미노출**(REQ-MVP-044 계승) — 각 케이스에서 스택 트레이스·raw 원문 0건 assert | REQ-DEPLOY-018~020 |

### D.8 크로스플랫폼·재현 가능 빌드 AC

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-013 ⏸️ **(Windows 절만 DEFERRED)** | ~~macOS+Windows~~ → **macOS(arm64)** 재현 가능 빌드 + 비공개 자원 미의존 | ① 반자동: 문서화된 빌드 절차만으로 macOS·Windows 각각에서 아티팩트 생성 성공 ⏸️ `[SCOPE-2026-07-22: DEFERRED-WINDOWS — **Windows 절만 이연**되고 macOS(arm64) 절은 그대로 close 조건으로 존속한다. 사용자 지시 "우선 윈도우는 제외하고". universal2/Intel도 arm64 전용 빌드 호스트 제약으로 이연 유지]` ② 자동: 의존성 핀 파일(uv.lock / ui/package-lock.json / Stage 2 Cargo·Tauri 락) 존재 ③ 문서 검수: 빌드 절차에 비공개 자원(수동 배포 번들·베타 신청) 의존 0건 *(v0.5.0: 서명 DESCOPED로 **유료 Apple Developer 멤버십조차 전제되지 않아 더 강하게 충족**)* | REQ-DEPLOY-021~022 |

### D.9 안전 불변식 보존 AC (핵심 회귀)

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-014 | 배포 셸이 안전 게이트 불변식을 보존 (우회 경로 신설 0) | **자동(CI 상시)**: 패키징된 셸을 감싼 구성에서 ① SPEC-COPILOT-MVP-001 단일 관문 아키텍처 테스트(AC-MVP-019) 유지 green ② 블랙리스트 명령 인간 승인 없이 미실행(AC-MVP-004) 회귀 green ③ **결정적 OSC 송신 표면 스캔(SAFETY-1/SAFETY-2, 구체화)**: (a) **정당한 OSC 송신 표면을 명명된 모듈/심볼 allowlist로 열거** — 오직 게이트의 send 함수만 합법적으로 송신하며, allowlist는 테스트 픽스처에 고정; (b) **스캔 메커니즘·패턴을 Python + Rust/Tauri 전 소스에 적용** — raw socket 생성(`socket.socket`/`std::net::UdpSocket` 등), 직접 OSC 모듈 import(`python-osc`/OSC 크레이트), `127.0.0.1`/콘솔 포트 리터럴 패턴을 grep/AST 스캔; (c) **패키지된 셸 E2E 중 콘솔 수신 포트에서 관측되는 "모든 OSC 송신"을 wire-level로 열거**하여 allowlist와 대조(Python import 검사에 불가시한 Rust/sidecar raw UDP까지 포착); (d) 설정 UI / provisioning / updater 경로에서 **미열거(allowlist 밖) 신규 모듈이 송신 표면에 진입하면 fail-closed**. **(M7 활성화)** ③의 (b) Rust/Tauri 소스 스캔 + (c) wire-level 열거 절은 Stage-1에서 N/A로 이연되었으나, **M7(Stage-2)에서 활성화**된다 — 구체적 이중 스캔(Rust deny-all 정적 + wire-level 싱크 fail-closed)은 **AC-DEPLOY-027**로 검증 | REQ-DEPLOY-023~024 |
| AC-DEPLOY-018 ⛔ **DESCOPED** ⛔ `[SCOPE-2026-07-22: DESCOPED — 자동 업데이트가 폐기되어 **updater 유발 재시작 경로 자체가 존재하지 않는다**. ⚠️ 이는 라이브 잠금·승인 게이트·감사 로그 불변식의 약화가 **아니다** — 그 불변식은 AC-DEPLOY-014(REQ-023/024)로 계속 CI 상시 강제된다]` | updater 재시작 시 안전상태 보존 (SAFETY-4, Stage-2 관련) | 자동/반자동: 자동 업데이트가 백엔드를 재시작하는 시나리오를 재현 → ① 재시작 후 **라이브 잠금(live-lock=ON)** 이 보존(또는 fail-safe로 재잠금)됨을 assert ② **대기 중 승인(pending-approval) 상태** 보존(또는 재잠금) 확인 ③ 재시작 경계를 가로질러 **감사 로그 연속성**(재시작 전후 로그 항목 단절/유실 0건) 확인 | REQ-DEPLOY-027 |

### D.10 앱 수명주기 AC

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-015 | graceful shutdown + 포트 사용 중 조용한 폴백 금지 | 자동/반자동: ① 앱 종료 → 백엔드(및 sidecar) 정상 종료 + 포트/OSC 리스너/타이머 정리. **검증은 부트로더 PID 하나가 아니라 process-TREE scan**(추출된 grandchild Python 프로세스까지 잔여 0건 — FEAS-5) + **crash/force-quit 종료 경로**(강제 종료 시에도 grandchild·포트 좀비 0건)까지 커버 ② **지정 OSC/웹 포트 선점 상태 재현 → 인간 친화적 오류 + 재설정 안내 표시 + 임의 포트 조용한 폴백 0건** 확인 | REQ-DEPLOY-025~026 |

### D.11 라이브 E2E 하드닝 AC (v0.3.0 fold-in — 실제 하드웨어+LLM+번들 결합 결함 #2~#6)

> provenance: `copilot-live-demo-findings`(2026-07-20 실제 onPC 2.4.2 + 실제 Gemini 라이브 데모). 결함 #1(`build_runtime` 라우터 미조립)은 commit `1d65375`에서 이미 수정되어 신규 AC를 앵커링하지 않는다. #2(AC-019)는 `build_runtime` 조립 수준의 단위 테스트로 검증 가능하며, #6(AC-023)은 라이브/하드웨어 부분을 deferred/manual 기준으로 분리한다.

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-019 | 기동 시 활성 프로바이더 키 주입 + 기설정 env 보존 + 저장소 미가용 시 세션 한정 폴백 (#2) | **자동(단위 — `build_runtime` 조립 수준)**: ① 활성 프로바이더가 시드된 키스토어 + **사전 설정 env 키 없음** 상태에서 `build_runtime`(프로바이더 클라이언트 생성 이전)이 그 프로바이더 키를 프로세스 env로 주입함을 assert ② **이미 설정된 env 키는 보존**(덮어쓰지 않음)됨을 assert ③ **저장소 미가용/잠금/거부** 시 REQ-DEPLOY-006a 세션 한정(in-memory) 폴백으로 동작하고 **평문 디스크 저장 0건**임을 assert(정상경로 스캔이 건드리지 않는 실패 분기 커버) ④ 회귀: 신규 인스턴스가 키 없이 기동해 "No API key"로 실패하지 않음(1d65375 이후 라우터 조립 전제) | REQ-DEPLOY-028 |
| AC-DEPLOY-020 | rig-context/프롬프트가 실제 풀 번호+이름을 명시 → 존재하지 않는 오브젝트 미선택 (#3) | **자동**: 풀 번호가 비연속인 rig(예: Group이 1,2,7만 존재)에 대해 ① `get_rig_context`/프롬프트 산출물이 각 오브젝트의 **실제 풀 번호와 이름**을 노출(위치 인덱스 단독 노출 아님)함을 assert ② 그 컨텍스트 기반 대상 선택이 **존재하는 풀 번호로 해소**되고 존재하지 않는 번호(예: `Group 3`)를 생성하지 않음을 assert. **반자동(LLM)**: 모호 지시가 존재하는 대상으로 해소됨을 확인(명시적 `Fixture 11 Thru 19`는 회귀 통과) | REQ-DEPLOY-029 |
| AC-DEPLOY-021 | 직전 생성 시퀀스/실행기 상태를 세션에 주입 → 후속 수정이 정확 대상 지향 + 재생성 선호 (#4) | **자동**: ① `Seq 71` / `Exec 201`에 룩을 생성한 뒤, 세션 컨텍스트에 **마지막 생성 대상 상태가 존재**함을 assert ② 후속 수정 지시("더 느리게")가 그 상태를 근거로 **`Seq 71`/`Exec 201`로 해소**(임의 `Seq 1`/`Exec 1` 아님)됨을 assert ③ 대상 상태가 존재할 때 **맹목적 수정보다 재생성 경로가 선택**됨을 assert | REQ-DEPLOY-030 |
| AC-DEPLOY-022 | Gemini 캐시 만료 시 재생성·재시도 + "No API key" 인증 오류 분류 (#5) | **자동(오류 주입)**: ① `403 PERMISSION_DENIED "CachedContent not found"`(및 404) 주입 → 앱이 **캐시를 재생성하여 재시도**하고 호출을 종단 실패로 종료하지 않음을 assert ② `"No API key"`(`ValueError`) 주입 → 오류 분류가 `unexpected`가 아닌 **인증(auth) 오류**로 분류됨을 assert(캐시/키 케이스가 분류기에 존재) | REQ-DEPLOY-031 |
| AC-DEPLOY-023 | OSC 수신 포트 `Address already in use` 시 동일 포트 재바인드·복구 + 조용한 드리프트 금지 (#6) | **자동(단위 — 포트 선점 시뮬레이션)**: ① 지정 수신 포트 선점(mock)으로 `Address already in use` 재현 → 앱이 **동일 지정 포트 재바인드**(소켓 재사용/재시도) 시도, **임의 포트 조용한 드리프트 0건**(REQ-DEPLOY-026 정합), 복구 불가 시 **인간 친화적 오류 + 재설정 안내 표시**를 assert(`server/bridge/osc.py` 수신 경로). **반자동/수동(라이브·하드웨어 — deferred N/A)**: 실제 onPC 비정상 종료 후 수신 포트 점유 상태에서 앱 재기동 복구는 **라이브 onPC 환경-게이트**(SPEC-COPILOT-MVP-001 라이브 gap 규율 동일 — 하드웨어 부재 시 explicit N/A, 확보 시 실행); 단위 커버리지가 불가한 왕복 복구는 수동 검증으로 분리 | REQ-DEPLOY-032 |

### D.12 Stage-2 M7 AC (v0.4.0 fold-in — Tauri v2 셸 + Python sidecar)

> 본 kickoff 착수 스코프 = **M7-first**. M8(자동 업데이트)·M9(코드 서명/공증)은 ~~Stage-2-DEFERRED~~ → ⛔ **DESCOPED (2026-07-22)** 로 **AC 미포함** — `[SCOPE-2026-07-22: DESCOPED — 이연이 아니라 폐기이므로 M8/M9 AC는 **앞으로도 신설되지 않는다**]`. 각 AC의 env-gate: buildable/verifiable **NOW = macOS arm64 + dev/ad-hoc 서명**; ~~**universal2 / Windows / 실제 notarization = env-gate N/A**(AC-DEPLOY-009/010 규율 동일)~~ → ⏸️⛔ `[SCOPE-2026-07-22: universal2·Windows = DEFERRED-WINDOWS/호스트 제약 이연, 실제 notarization = DESCOPED. 어느 쪽도 close를 블록하지 않는다]`. Tauri v2 동작 근거는 검증된 공식 문서 인용(sidecar/IPC/process-model/capabilities/shell — plan.md § M7 구현 계획).

| AC ID | 기준 | 검증 방법 | 연계 REQ |
|---|---|---|---|
| AC-DEPLOY-024 | Tauri v2 셸 기동 — sidecar spawn + 네이티브 창이 `ui/dist` 로드 + 트레이/연결 상태 표시 | **반자동(NOW: macOS arm64, dev/ad-hoc 서명)**: ① `tauri build`/`tauri dev` 실행 → PyInstaller onedir 백엔드가 **sidecar 프로세스로 spawn**됨 확인 ② 네이티브 창이 동일 `ui/dist/index.html`을 로드(M6 백엔드 재사용)하고 SPA HTTP 200 서빙 ③ 시스템 트레이 아이콘 + health 연결 상태 배지(online/console_offline/responder_degraded — M5 재사용) 표시. **자동**: Tauri capabilities가 sidecar-spawn 외 네트워크 플러그인 deny함을 정적 확인(AC-027 연계). **env-gate N/A**: universal2/Windows 셸 빌드·실제 notarization(AC-009/010 규율) = 적합 빌드 환경/인증서 확보 시 | REQ-DEPLOY-001, 002 |
| AC-DEPLOY-025 | F5 sidecar↔UI 핸드셰이크 — disallowed Origin OR 누락/오류 토큰 연결 REJECT, valid Origin+토큰 ACCEPT (FEAS-9 CSWSH 차단) | **자동(단위 — NOW, 하드웨어/인증서 불요)**: `/ws` accept 경로(`server/web/app.py:139` 이전 게이트)에 ① allowlist 밖 `Origin` → 연결 거부(accept 전 close) assert ② 유효 Origin + **누락 토큰** → 거부 assert ③ 유효 Origin + **오류 토큰** → 거부(상수-시간 비교 `hmac.compare_digest`) assert ④ 유효 Origin + **정확 per-launch 토큰** → accept assert ⑤ 프로토콜 v1/`messages.py`/`PROTOCOL.md` 불변 회귀(핸드셰이크가 메시지 스키마 미변경). **반자동(E2E — macOS arm64 dev)**: Tauri 창(허용 오리진 + 주입 토큰) 접속 성공 + 임의 브라우저 탭(비허용 오리진/무토큰) 접속 실패 확인. **env-gate N/A 없음** — 순수 로컬 단위/E2E로 지금 완전 검증 | REQ-DEPLOY-002a |
| AC-DEPLOY-026 | 프로세스-트리 teardown 잔여 0 (정상 종료 AND 백엔드 크래시 AND Tauri force-quit) + 웹/OSC 포트 해제 (Option C — AC-DEPLOY-015 ①② 확장) | **자동/반자동(macOS arm64 dev — NOW)**: ① **정상 종료** — Rust `RunEvent::Exit`가 process-group kill(Unix setsid/setpgid) → 프로세스-트리 스캔 잔여 pid 0 + 포트 해제 ② **백엔드 크래시** — sidecar 강제 kill 후 Rust 재수확 or launcher `terminate_process_tree`(`launcher.py:208`) 정리, 잔여 0 ③ **Tauri force-quit** — Unix force-quit 시 `RunEvent::Exit` 미발화 → 백엔드 parent-liveness **watchdog**가 self-reap: **PRIMARY = pipe/heartbeat EOF**(부모 사망 즉시 감지, 레이스 창 없음), **FALLBACK = `getppid()==1` 폴링(폴링 상한 ≤ 1s)**. **bounded max reap latency ≤ 1s** 이내에 grandchild(추출 Python) 잔여 pid 0 + 포트 해제됨을 assert(무한 레이스 창이 아니라 상한-결정적 스캔) ④ 재기동 `require_ports_available`(`launcher.py:162`) fail-closed(포트 점유 시 명시 오류 — AC-015 ②/REQ-026 정합). ⚠️ `CommandChild.kill()`은 부트로더 PID만 kill이므로 group kill 검증 필수. **env-gate N/A**: Windows Job Object(KILL_ON_JOB_CLOSE) 경로 = Windows 러너 확보 시(현 arm64 macOS 호스트 N/A) | REQ-DEPLOY-025 (+026 포트) |
| AC-DEPLOY-027 | SAFETY-2 교차언어 이중 스캔 — Layer①(Rust deny-all 정적) + Layer②(wire-level 싱크). 각 레이어의 검증 시점(env-gate)을 분리 명시하고, 두 레이어 모두 **vacuous-pass를 차단** (AC-DEPLOY-014 ③b/③c/③d 활성화) | **Layer ① Rust deny-all 정적 스캔 — 검증 시점 = M7.4 `src-tauri/` scaffold 이후(빈/부재 크레이트 트리에서는 fail-closed; scaffold 이전에는 vacuous-pass라 검증 불가)**: ① **`src-tauri/` 존재를 게이트 — 부재/빈 트리는 PASS가 아니라 FAIL(blocked)** 로 처리(0-file→0-violation 취급 금지) ② 스캔이 실제로 파일을 읽었음을 **`files_scanned > 0`으로 assert**(0이면 fail-closed) ③ `src-tauri/**/*.rs`+`Cargo.toml`/`Cargo.lock`을 **DENY-ALL(빈 allowlist)** 로 스캔 — `UdpSocket`/`std::net::`/`.bind|.connect|.send_to`/OSC 크레이트(rosc·nannou_osc)/`127.0.0.1`·콘솔 포트 리터럴; 매니페스트 스캔은 raw-socket/OSC 네트워킹 크레이트(전이 Cargo.lock 포함) 거부 ④ **MANDATORY CI 픽스처(산문 아님)**: rogue 크레이트/소켓 코드를 **양성 대조(positive-control) 고정 픽스처로 상시** → 스캔이 **fail**함을 assert, clean 트리는 **pass**. **Layer ② wire-level 싱크(패키지 E2E — NOW 검증 가능, loopback·하드웨어/인증서 불요)**: ① 싱크를 **하드코딩 기본(8000)이 아니라 E2E 실행의 실제 설정 send_port**(effective settings에서 읽은 값 — REQ-DEPLOY-005 사용자 설정 가능)에 바인드 ② 콘솔 수신 포트의 모든 datagram 기록 → 게이트 감사 "executed" 로그(`server/tests/test_deploy_safety_invariants.py`)와 **1:1 대조** ③ **양성 관측(positive-observation) assert — 정당한 게이트 송신이 싱크에서 실제로 관측됨(≥1 datagram 캡처+대조)** 을 요구(빈 캡처로 "미열거 송신 0"이 vacuous-충족되는 것 차단) ④ 미감사/미열거 송신자에 **fail-closed** + **synthetic rogue 패킷 주입 → 싱크가 flag** 증명. **공통**: Tauri v2 capabilities 모든 네트워크 플러그인 deny + `tauri-plugin-shell` sidecar-spawn만으로 스코프 확인. 호스트: `packaging/verify_packaged_e2e.py` 확장. **env-gate 요약: Layer①=M7.4 scaffold 이후, Layer②=NOW(loopback)** | REQ-DEPLOY-023~024 |
| AC-DEPLOY-028 | 키 커스터디 불변 — Python `keyring` 직접(Rust 비밀 미접촉) + 평문 디스크 0 보존 | **자동(단위 — NOW)**: ① **Rust/Tauri 소스에 자격 증명 저장소/키 접근 코드 0건** 정적 스캔 assert(Rust는 sidecar spawn/lifecycle만) ② Stage-1 키 경로(`inject_active_provider_key` `keystore.py:253`/`scrub_environ` `:298`) **무변경 회귀 green** ③ 앱이 쓰는 모든 파일에 키 문자열 0건(AC-004 스캔) + 저장소 미가용 시 세션 한정 폴백(AC-016) 유지. **전제/잔여(M9 이연)**: 서명된 sidecar의 OS keychain 도달성은 **M9(코드 서명) 검증 항목** — 서명된 sidecar가 keychain 불가하고 Tauri 호스트만 가능한 경우에 한해 키 커스터디 재검토(§A.2 F5' 잔여) | REQ-DEPLOY-006~007 (+006a) |
| AC-DEPLOY-029 | per-launch 토큰 비밀 유지 — 토큰이 커밋 가능한·평문 파일에 기록되지 않음 (D4 — AC-004 키-스캔과 병렬) | **자동(단위 — NOW, 하드웨어/인증서 불요)**: ① launcher가 생성한 per-launch 토큰이 **앱이 쓰는 모든 파일(설정·로그·캐시·`ui/dist` serve 산출물·크래시 덤프)에 0건**임을 자동 스캔(AC-DEPLOY-004 키-스캔과 동형 — 토큰 문자열 grep 0) ② **Stage-2 경로**: 토큰이 **Tauri IPC로만 웹뷰에 전달**되고 디스크 파일/미인증 loopback 엔드포인트로 노출되지 않음을 assert(**`index.html` 메타 주입 부재** 확인 — D4a 폐기 옵션) ③ **Stage-1 브라우저 모드**: 토큰은 심층방어이며 실질 CSWSH 차단자는 Origin allowlist임을 문서-정합으로 확인(토큰이 유일 방어축이라 주장하지 않음 — D4b). **env-gate N/A 없음** — 순수 로컬 스캔 | REQ-DEPLOY-002a |

## Given-When-Then 시나리오

### 시나리오 1 — 최초 실행 셋업 (fresh install → 첫 지시 성공)
- **Given** 조명 오퍼레이터가 콘솔 PC에 배포 아티팩트를 설치하고 onPC 2.4.2가 실행 중인 상태에서
- **When** 사용자가 앱을 실행하고 설정 UI에서 GEMINI_API_KEY를 입력·저장한 뒤 responder 설치 버튼을 눌러 안내대로 onPC에서 플러그인을 로드하고 OSC 출력을 앱 수신 포트로 설정하면
- **Then** 키는 OS 자격 증명 저장소에 저장되고(평문 파일 0건), health 배지가 `online`으로 전이하며, 사용자가 "보컬 그룹 만들어줘" 류 한국어 지시를 입력하면 코파일럿이 SPEC-COPILOT-MVP-001과 동일하게 명령을 생성·게이트 통과·실행하고 UI에 한국어 결과를 보고한다.

### 시나리오 2 — 키 부재/무효 오류 UX
- **Given** API 키가 설정되지 않았거나 무효한 상태에서
- **When** 사용자가 지시를 입력하거나 앱이 프로바이더 클라이언트를 기동하려 하면
- **Then** UI는 스택 트레이스나 raw SDK 오류 원문이 아닌 인간 친화적 한국어 메시지("API 키가 설정되지 않았습니다 — 설정에서 키를 입력해 주세요")를 표시하고 설정 UI로 유도하며, 원문 상세는 진단 로그에만 기록된다.

### 시나리오 3 — 콘솔 오프라인 (배포 형태에서의 health 표면화)
- **Given** 앱은 구동 중이나 onPC가 실행되지 않았거나 OSC 입력이 꺼진 상태에서
- **When** 앱이 하트비트/조회 타임아웃으로 `console_offline`을 감지하면
- **Then** UI 배지가 `console_offline`을 표시하고, 원인+조치("onPC 실행 및 OSC 입력 활성화 확인") 한국어 안내가 표시되며, 신규 실행성 명령은 차단된다(SPEC-COPILOT-MVP-001 장애 모드 동작이 패키징 셸에서 그대로 표면화).

### 시나리오 3b — responder 미로드 (responder_degraded) (TRACE-4)
- **Given** onPC는 실행 중이나 CopilotResponder Lua 플러그인이 로드되지 않았거나 responder가 무응답인 상태에서
- **When** 앱이 responder 무응답으로 `responder_degraded`를 감지하면
- **Then** UI 배지가 `responder_degraded`를 표시하고, responder 로딩 절차 + onPC OSC 출력 포트 설정 안내(REQ-DEPLOY-019) 한국어 메시지가 표시되며(스택 트레이스 미노출), 콘솔 피드백에 의존하는 명령은 SPEC-COPILOT-MVP-001 장애 모드 규율대로 처리된다(패키징 셸에서 동일 표면화).

### 시나리오 4 — 자동 업데이트 (Stage 2, 서명 검증) ⛔ **DESCOPED (2026-07-22)**

> ⛔ `[SCOPE-2026-07-22: DESCOPED — 사용자 선택 "빼기 · 수동 재배포". 아래 시나리오는 원문 보존이며 검증 대상이 아니다. 대체 = 아래 **시나리오 7**]`

- **Given** Tauri 데스크톱 앱(Stage 2)이 설치되고 신버전이 업데이트 매니페스트에 게시된 상태에서
- **When** 사용자가 업데이트 알림을 승인하면
- **Then** 앱은 아티팩트를 다운로드하여 서명(무결성) 검증을 수행하고, 검증 통과 시에만 업데이트를 적용·재기동하며, 검증 실패 시 적용을 차단하고 현재 버전을 유지한다.

### 시나리오 7 — ad-hoc 전달 + 최초 실행 (v0.5.0 신설 — 시나리오 4 대체)
- **Given** ad-hoc 서명된 `GrandMA3 Copilot.app`을 `.dmg`로 패키징(`npm run shell:package`)하고 `INSTALL.ko.md`와 함께 동료에게 전달한 상태에서
- **When** 동료가 `.dmg`를 열어 앱을 `/Applications`로 드래그한 뒤 실행하면
- **Then** 전달 경로가 quarantine을 붙이지 않았다면(`scp`/`rsync`/`git`/USB) 그대로 실행되고, quarantine이 붙었다면(브라우저·메일·AirDrop) macOS가 최초 실행을 차단하며 사용자는 `INSTALL.ko.md`의 두 경로(`xattr -dr com.apple.quarantine …` 또는 시스템 설정 → 개인정보 보호 및 보안 → "그래도 열기") 중 하나로 해제한 뒤 실행한다. 해제 이후 실행에서는 터미널 창·오류 팝업 없이 UI가 표시된다. 새 버전이 필요하면 **새 `.dmg`를 다시 전달**한다(자동 업데이트 없음).

### 시나리오 5 — 배포 셸의 안전 불변식 보존 (회귀)
- **Given** 패키징된 배포 형태(Stage 1 또는 2)로 구동된 상태에서
- **When** 사용자가 파괴적 결과를 유발하는 지시(예: "시퀀스 다 지워줘" → `Delete` 계열 블랙리스트 명령 생성)를 입력하면
- **Then** 배포 셸을 감쌌음에도 안전 게이트가 그대로 관문으로 작동하여 명령을 인간 승인 대기로 보류하고, 승인 전까지 OSC 송신이 0건이며, 설정 UI·responder provisioning·updater 어느 경로도 게이트를 우회해 콘솔로 명령을 보내지 않는다.

### 시나리오 6 — Stage-2 Tauri 셸 기동 + F5 핸드셰이크 (M7)
- **Given** macOS arm64에서 Tauri v2 데스크톱 앱(Stage-2, dev/ad-hoc 서명)이 설치되고 PyInstaller 백엔드를 sidecar로 번들한 상태에서
- **When** 사용자가 앱을 실행하면 Tauri가 sidecar(백엔드)를 process-group 리더로 spawn하고, 네이티브 창이 launcher-주입 per-launch 토큰을 지닌 채 `127.0.0.1` WebSocket `/ws`로 접속하며, 이후 사용자가 앱을 정상 종료하거나 강제 종료(force-quit)하면
- **Then** 네이티브 창이 동일 `ui/dist`를 로드하고 health 배지·트레이가 표시되며(AC-024); 허용 Origin+정확 토큰 연결만 accept되고 비허용 Origin이나 무효 토큰 연결은 거부되어 CSWSH가 차단되며(AC-025); 종료 시(정상/크래시/force-quit 3경로 모두) sidecar와 grandchild Python 프로세스-트리 잔여가 0이고 웹/OSC 포트가 해제되며(AC-026 — force-quit는 백엔드 watchdog self-reap); Rust/wire-level 교차언어 스캔이 셸의 콘솔 raw UDP 송신 표면 0을 fail-closed로 강제한다(AC-027). 키는 여전히 Python `keyring`으로만 커스터디되고 Rust는 비밀을 만지지 않는다(AC-028).

## 엣지 케이스

- **OS 자격 증명 저장소 미가용/잠금/거부**: 명시적 오류 안내 + 세션-한정(in-memory) 키 입력 폴백(평문 디스크 저장 금지) — 조용한 평문 폴백 0건 (REQ-DEPLOY-006a / AC-DEPLOY-016으로 앵커링).
- **자격 증명 저장소 접근 거부(사용자가 Keychain 접근 거부)**: 재시도/권한 안내.
- **OSC/웹 포트 선점(예: 8765/9000 사용 중)**: 재설정 안내 + 임의 포트 조용한 폴백 금지(REQ-DEPLOY-026).
- **플러그인 임포트 디렉터리 부재/쓰기 불가**: provisioning 실패 인간 친화적 안내(경로 재설정 유도).
- **macOS Gatekeeper quarantine (최초 실행)**: ⛔ `[SCOPE-2026-07-22: DESCOPED — 원문 "notarization으로 해소(REQ-DEPLOY-014); 미공증 아티팩트는 차단됨을 인지."]` **v0.5.0 대체**: 공증하지 않으므로 `spctl --assess` 거부는 영구적이며, quarantine이 붙는 전달 경로에서는 최초 실행 차단이 **기대 동작**이다. 해소는 사용자 측 해제 조작(`xattr -dr com.apple.quarantine …` / 시스템 설정 "그래도 열기")이며 그 절차 안내가 산출물의 일부다(REQ-DEPLOY-014a / AC-DEPLOY-030 / `INSTALL.ko.md`).
- **Windows SmartScreen 미확인 게시자**: ⏸️ `[SCOPE-2026-07-22: DEFERRED-WINDOWS — Windows 플랫폼 이연과 함께 이연. 아울러 Authenticode 서명 자체는 ⛔ DESCOPED이므로, Windows가 재개되더라도 이 항목은 서명이 아닌 다른 방식으로 다뤄야 한다]` 원문: 서명은 REQ-DEPLOY-015(`signtool verify /pa` 검증 가능), SmartScreen 완화는 평판 누적 의존(§C 제약 — OV는 즉시 미해소, EV만 즉시 신뢰 — FEAS-7).
- **자동 업데이트 적용 실패**: ⛔ `[SCOPE-2026-07-22: DESCOPED — 원문 "롤백/현재 버전 유지 + 사용자 통지(REQ-DEPLOY-017)". 자동 업데이트가 없으므로 이 엣지 케이스는 발생하지 않는다]`
- **손상된 `.dmg` 전달 (v0.5.0 신설)**: 전송 중 파일이 손상되면 macOS가 "손상되었기 때문에 열 수 없습니다"류 강한 경고를 낸다 — 재전달로 해소한다(`INSTALL.ko.md` "문제가 계속되면").
- **onPC OSC 출력 포트 드리프트**: 앱은 지정 수신 포트를 조용히 바꾸지 않고, 불일치 시 responder_degraded/오프라인으로 표면화(REQ-DEPLOY-026 + health UI).
- **Stage 2 sidecar 좀비 프로세스**: 앱 종료 시 sidecar 강제 종료·포트 정리(REQ-DEPLOY-025).

## REQ → AC 추적성 매트릭스 (고아 REQ 0건)

| REQ | AC | REQ | AC |
|---|---|---|---|
| REQ-DEPLOY-001~003 | AC-DEPLOY-001 | ⛔ REQ-DEPLOY-014 *(DESCOPED)* | ⛔ AC-DEPLOY-009 *(DESCOPED)* |
| REQ-DEPLOY-004 | AC-DEPLOY-002 | ⛔ REQ-DEPLOY-015 *(DESCOPED)* | ⛔ AC-DEPLOY-010 *(DESCOPED)* |
| REQ-DEPLOY-004a | AC-DEPLOY-002 | ⛔ REQ-DEPLOY-016~017 *(DESCOPED)* | ⛔ AC-DEPLOY-011 *(DESCOPED)* |
| REQ-DEPLOY-005 | AC-DEPLOY-003 | REQ-DEPLOY-018~020 | AC-DEPLOY-012 |
| REQ-DEPLOY-006~007 | AC-DEPLOY-004 | REQ-DEPLOY-021~022 ⏸️ *(021은 macOS arm64 한정 — Windows 절 DEFERRED)* | AC-DEPLOY-013 ⏸️ *(Windows 절 DEFERRED)* |
| REQ-DEPLOY-006a | AC-DEPLOY-016 | REQ-DEPLOY-023~024 | AC-DEPLOY-014 |
| REQ-DEPLOY-008 | AC-DEPLOY-005 | REQ-DEPLOY-011a, 024 | AC-DEPLOY-017 |
| REQ-DEPLOY-009~010 | AC-DEPLOY-006 | REQ-DEPLOY-025~026 | AC-DEPLOY-015 |
| REQ-DEPLOY-011 | AC-DEPLOY-007 | ⛔ REQ-DEPLOY-027 *(DESCOPED)* | ⛔ AC-DEPLOY-018 *(DESCOPED)* |
| REQ-DEPLOY-012~013 | AC-DEPLOY-008 | REQ-DEPLOY-028 | AC-DEPLOY-019 |
| 🆕 REQ-DEPLOY-014a *(v0.5.0)* | 🆕 AC-DEPLOY-030 *(v0.5.0)* | — | — |
| REQ-DEPLOY-029 | AC-DEPLOY-020 | REQ-DEPLOY-030 | AC-DEPLOY-021 |
| REQ-DEPLOY-031 | AC-DEPLOY-022 | REQ-DEPLOY-032 | AC-DEPLOY-023 |
| REQ-DEPLOY-001~002 | AC-DEPLOY-024 | REQ-DEPLOY-002a | AC-DEPLOY-025 |
| REQ-DEPLOY-025~026 | AC-DEPLOY-026 | REQ-DEPLOY-023~024 | AC-DEPLOY-027 |
| REQ-DEPLOY-006~007 | AC-DEPLOY-028 | REQ-DEPLOY-002a | AC-DEPLOY-029 |

> 신규 앵커 (v0.2.0 fold-in): REQ-004a(로컬 공존 [Ubiquitous] 분리)→AC-002, REQ-006a(자격 저장소 미가용 [Unwanted])→AC-016, REQ-011a(앱 발행 Import Plugin 게이트 경유)→AC-017, REQ-027(updater 재시작 안전상태 보존)→AC-018. 고아 REQ 0건 유지.
> 신규 앵커 (v0.3.0 라이브 E2E 하드닝 fold-in): REQ-028(#2 기동 시 활성 프로바이더 키 주입 [Event-driven])→AC-019, REQ-029(#3 rig-context 실제 풀 번호 명시 [State-driven])→AC-020, REQ-030(#4 마지막 생성 연출 상태 세션 주입 [State-driven])→AC-021, REQ-031(#5 Gemini 캐시 만료 재생성 + 키 오류 분류 [Unwanted])→AC-022, REQ-032(#6 OSC 수신 포트 재바인드 복구 [Unwanted])→AC-023. **결함 #1은 commit `1d65375`에서 이미 수정되어 신규 REQ/AC 미앵커링(이력 전용).** 고아 REQ 0건 유지.
> 신규 앵커 (v0.4.0 Stage-2 M7 kickoff fold-in + plan-audit remediation D1–D10): 신규 REQ-002a(sidecar↔UI Origin/token 핸드셰이크 [Event-driven] — FEAS-9)→**AC-025(핸드셰이크 reject/accept) + AC-029(토큰 비밀 유지 — D4c 신설)**; 기존 REQ 추가 AC 매핑 — REQ-001~002→AC-024(Tauri 셸 기동), REQ-025~026→AC-026(프로세스-트리 teardown Option C, AC-015 확장), REQ-023~024→AC-027(SAFETY-2 이중 스캔, AC-014 ③ 활성화), REQ-006~007→AC-028(키 커스터디 불변). REQ-002a는 유일한 신규 REQ이며 AC-025·AC-029로 앵커 — **고아 REQ 0건 유지**. M8/M9(REQ-016/017/027/014/015 등) 관련 AC(011/018/009/010)는 Stage-2-DEFERRED로 기존 상태 불변.
> 스코프 축소 (v0.5.0, 2026-07-22): ⛔ **DESCOPED 쌍 4건** — REQ-014→AC-009, REQ-015→AC-010, REQ-016~017→AC-011, REQ-027→AC-018 (행 삭제 없이 마커만 부착). ⏸️ **DEFERRED-WINDOWS** — REQ-021→AC-013의 Windows 절(macOS arm64 절은 존속). 🆕 **신규 앵커** — REQ-DEPLOY-014a(ad-hoc `.app`→`.dmg`+한국어 설치 안내 [Ubiquitous])→**AC-DEPLOY-030**. **고아 REQ 0건 유지** — DESCOPED된 REQ도 자신의 (DESCOPED된) AC를 그대로 보유하므로 매핑이 끊기지 않고, 신설 REQ-014a는 AC-030으로 앵커된다.

## 품질 게이트 (TRUST 5)

- **Tested**: 설정·config 저장 계층, 키 저장 어댑터(mock 가능), provisioning 복사, health 표면화, 포트 처리, 안전 불변식 회귀(AC-DEPLOY-014)는 자동 테스트 필수. ~~서명·공증·네이티브 창·자동 업데이트는 환경-게이트 반자동~~ → ⛔ `[SCOPE-2026-07-22: DESCOPED — 서명·공증·자동 업데이트 절. **네이티브 창(Tauri 셸)은 존속**하며 반자동 검증 대상이다(AC-DEPLOY-024). ad-hoc 전달 아티팩트(AC-DEPLOY-030)는 인증서 불요 반자동]`. 신규 셸 코드 커버리지 85%+ 목표. AC-DEPLOY-014는 CI 상시 실행.
- **Readable/Unified**: Python은 ruff 포맷/린트 통과, TS/React는 프로젝트 린트/프리티어, Stage 2 Rust(Tauri)는 clippy/rustfmt. 코드 주석 영어.
- **Secured**: API 키는 OS 자격 증명 저장소에만 저장(평문 커밋 파일 금지 — AC-DEPLOY-004); ⛔ `[SCOPE-2026-07-22: DESCOPED — 원문 중 "배포 아티팩트 서명·공증(REQ-DEPLOY-014/015); 자동 업데이트 서명 검증(REQ-DEPLOY-017)" 절. 대체로 ad-hoc 서명 seal 무결성(AC-DEPLOY-030 ①③)을 확인한다]`; per-launch 토큰 비밀 유지(AC-DEPLOY-029); 프로바이더 config 로더의 credential-like 키 거부 유지. **배포 셸이 안전 게이트를 우회하지 않음(AC-DEPLOY-014)이 최상위 보안 불변식** — 이 불변식은 v0.5.0 스코프 축소로 **전혀 약화되지 않는다**.
- **Trackable**: Conventional Commits, 마일스톤별 커밋 분리.

## Definition of Done

> **v0.5.0 개정 (2026-07-22)**: 아래 체크리스트에서 ⛔ DESCOPED 항목(AC-009/010/011/018)과 ⏸️ DEFERRED-WINDOWS 항목은 **close 조건에서 제외**된다. 항목은 삭제하지 않고 마커와 함께 남겨 감사 추적을 보존한다. **활성 close 조건 = AC-DEPLOY-001~008, 012~017, 019~030 (⛔ 009·010·011·018 제외; AC-013은 macOS arm64 절만)**.

- [ ] AC-DEPLOY-001 ~ AC-DEPLOY-023 전부 PASS (자동 테스트 증거 포함; ~~AC-DEPLOY-009/010은 서명 인증서 확보 시 환경-게이트 검증, 부재 시 explicit N/A + 파이프라인 구성 존재~~ ⛔ `[SCOPE-2026-07-22: DESCOPED — AC-009/010은 close 조건에서 **제외**. 조건부 N/A가 아니라 스코프 밖]`; ⛔ **AC-DEPLOY-011(자동 업데이트)·AC-DEPLOY-018(updater 재시작)도 제외**; AC-DEPLOY-013은 **macOS arm64 절만**(Windows 절 ⏸️ DEFERRED); AC-DEPLOY-023의 라이브·하드웨어 왕복 복구는 라이브 onPC 환경-게이트 N/A로 분리) — **Stage-1 + v0.3.0 하드닝: 완료·synced(불변)**
- [ ] 🆕 **AC-DEPLOY-030 PASS** — ad-hoc 전달 아티팩트(ad-hoc `.app` seal 무결 + `.dmg` 패키징 + 마운트 후 seal 유지 + 한국어 설치 안내 동봉). **인증서·하드웨어 불요로 지금 완전 검증 가능**. `spctl --assess` 거부는 기대 결과이며 통과를 요구하지 않는다 (REQ-DEPLOY-014a)
- [ ] **Stage-2 M7 — AC-DEPLOY-024~029 전부 PASS** (Tauri 셸 기동 024 / F5 핸드셰이크 025 / 프로세스-트리 teardown 3경로 026 / SAFETY-2 이중 스캔 027 / 키 커스터디 불변 028 / per-launch 토큰 비밀 029; env-gate — NOW=macOS arm64 dev/ad-hoc). **AC-025·028·029는 순수 로컬 자동으로 지금 완전 검증 가능; AC-027 Layer②(wire-level)=NOW, Layer①(Rust 정적 스캔)=M7.4 `src-tauri/` scaffold 이후(부재 트리 fail-closed)**. ⛔ `[SCOPE-2026-07-22: DESCOPED — 원문 후단 "⏸️ M8/M9(자동 업데이트·서명/공증)은 Stage-2-DEFERRED — 별도 kickoff에서 AC 신설·검증 (terminal `completed` close는 M7~M9 전부 완료 후)". **M8/M9은 폐기되었으므로 terminal close가 더 이상 이 둘을 기다리지 않는다** — 이것이 본 SPEC을 close 가능하게 만드는 핵심 변경이다]`
- [ ] 라이브 E2E 하드닝(v0.3.0, 결함 #2~#6) — 기동 시 활성 프로바이더 키 주입(AC-019, **구현 최우선**), rig-context 실제 풀 번호 명시(AC-020), 마지막 생성 연출 상태 세션 주입(AC-021), Gemini 캐시 만료 재생성 + 키 오류 분류(AC-022), OSC 수신 포트 재바인드 복구 단위 검증(AC-023) 전부 PASS; 결함 #1은 commit `1d65375`에서 이미 수정(회귀 유지)
- [ ] 안전 불변식 회귀(AC-DEPLOY-014) — 패키징된 셸에서 단일 관문·블랙리스트 승인 불변식 유지 + OSC 송신 표면 allowlist/wire-level 열거(Python+Rust) CI green ***(v0.5.0 스코프 축소로 전혀 약화되지 않는 최상위 보안 불변식)***
- [ ] API 키 평문 미유출(AC-DEPLOY-004) — 앱이 쓰는 모든 파일(크래시 덤프 포함)에 키 문자열 0건 자동 스캔 통과; 저장소 미가용 폴백(AC-DEPLOY-016) PASS
- [ ] 앱 발행 Import Plugin 게이트 경유 + 감사 로그 1:1(AC-DEPLOY-017) PASS; ~~updater 재시작 안전상태 보존(AC-DEPLOY-018) PASS(Stage-2)~~ ⛔ `[SCOPE-2026-07-22: DESCOPED — updater 부재로 해당 경로 없음]`
- [ ] Stage 1(PyInstaller **onedir**) + Stage 2(Tauri) 양 아티팩트가 재현 가능 빌드 절차로 생성됨 — **close 조건 대상 = macOS arm64 단일**(현재 호스트에서 지금 생성). ⏸️ `[SCOPE-2026-07-22: DEFERRED-WINDOWS — 원문 "universal2·Windows(x86_64)는 현재 빌드 호스트에서 환경-게이트 N/A(arm64 전용 CPython → universal2 unreachable; Windows 러너 부재 — research.md §C.6/§E-2), AC-DEPLOY-009/010 서명 env-gate와 동일 규율으로 적합한 빌드 환경 확보 시 생성(파이프라인은 코드 변경 없이 `PYI_TARGET_ARCH=universal2`/Windows 러너로 활성화)". Windows는 사용자 지시로 **이연**되고, universal2/Intel은 호스트 제약으로 이연 유지 — 어느 쪽도 close를 블록하지 않는다. 대조 앵커였던 AC-009/010 서명 env-gate는 DESCOPED되었으므로 "동일 규율" 참조는 더 이상 유효하지 않다]`
- [ ] REQ → AC 추적성 매트릭스 기준 고아 REQ 0건 유지 (REQ-004a/006a/011a/027/002a/**014a** 포함)
- [ ] plan.md §F 결정 원장 — **8 resolved(F1·F2·F3·F4·F5·F5'·F7·F8) + 3 배포 전제 축소 결정(F9·F10·F11, 2026-07-22) + 1 MOOT(F6), 미해소 오픈 결정 0건** ⛔ `[SCOPE-2026-07-22: 원문 "1 Stage-2-deferred(F6) … F6는 M8 별도 kickoff 이연" → F6은 M8 DESCOPED로 **MOOT**. F7은 F9로 대체. F5' 잔여(서명된 sidecar keychain 도달성)는 M9 DESCOPED로 트리거 소멸]`
- [ ] 기능 무변경 확인 — SPEC-COPILOT-MVP-001 백엔드 테스트 스위트 무변경 green 유지
