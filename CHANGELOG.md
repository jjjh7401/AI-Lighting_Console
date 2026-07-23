# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- **SPEC-COPILOT-EXECREF-001** — 안전 게이트가 `Executor`를 인식 가능한 참조 타입으로 처음 인정 (`status: in-progress` 유지 — 범위가 인식(S1)에 한정되고 실제 단일-press 복원(S2)은 후속 SPEC 대기이므로 아직 `completed`로 전환하지 않음). plan-audit **PASS-WITH-DEBT(score 0.92)** — iteration 3/3(retry cap 도달), 유일 blocker는 MP-2(AC 표 서식 관례) 하나뿐이며 감사자가 "genuine unresolved defect가 아니라 rubric 정합 문제"로 명시 판정, 사용자가 PASS-with-debt를 명시적으로 수용(AskUserQuestion).
  - **인식 확장**(`server/safety/classify.py`): `RECOGNIZED_REFERENCE_TYPES`에 `"Executor"` 추가(REQ-EXECREF-001/002/003). `server/tests/test_safety_corpus.py`의 FN 코퍼스 참조타입 축을 `classify.RECOGNIZED_REFERENCE_TYPES`에서 동적으로 순회하도록 리팩터(REQ-EXECREF-011) — 하드코딩 리터럴 0건, 향후 타입 추가가 코퍼스를 자동 확장.
  - **동작은 변하지 않았다 (핵심 정직성 고지)**: 이 SPEC은 익스큐터 타일을 누를 때마다 뜨는 승인 카드 1장 + 쇼파일 저장 1회의 원인 — 게이트가 `Executor`를 해석 가능한 참조로 인정하지 않는다는 점 — 을 진단하고 **인식만** 교정했다. **실제 사용자 경험은 이전과 완전히 동일하다**: 타일을 눌러도 여전히 승인 카드가 1장 뜨고, 여전히 SaveShow가 발화한다. M1 단독은 무행동 변화(no-op)임이 라이브 검증으로 확인됨(design.md §2.1, AC-EXECREF-008/013) — 보류 사유 문자열이 `"unverifiable reference: no recognizable target object"`에서 `"no body path mapping for 'Executor N'"`로 바뀌었을 뿐, `hold=True`/승인 카드 발생/SaveShow 발화는 모두 그대로다.
  - **왜 여기서 멈췄나 — S2(단일-press 복원) DESCOPED**: 승인 카드 없는 단일-press 발화라는 원래 목표를 실제로 달성하려면 콘솔 실행기의 "본문 경로"를 조회할 방법이 있어야 하는데, 2026-07-23 라이브 프로브(`.moai/state/verify/showui-m6-resume/5-probe-body.log`)가 이를 구조적으로 불가능하다고 결정적으로 확인(childCount 0/4, 기존 갭 재확인). 사용자 결정(AskUserQuestion, 2026-07-23)으로 S2를 완전 이연 — 실제 실행 시 승인 카드를 없애려면 `console/lua/copilot_responder.lua`(콘솔측 응답기)를 손대야 하는데, 본 SPEC은 의도적으로 그 파일을 건드리지 않는다. 후속 SPEC `SPEC-COPILOT-EXECBODY-001`(권고, research.md §5.3, 미생성)을 추천.
  - **테스트**: pytest **1723 passed**(+132, 기준선 HEAD `0576553`의 1591 대비), 신규 실패 0건 — 유일 실패는 기존 환경적 실패(onPC UDP 9005 점유) 그대로. 라이브 재검증(AC-EXECREF-013③, 실제 onPC 대상, M1 커밋 이후 사후 수행): `cleared=False`, 승인 카드 여전히 생성, 콘솔 송신 0건 — M1 이전과 관측 동일함을 확인.

- **SPEC-COPILOT-DEPLOY-001** — Stage-1 배포 가능한 arm64 macOS MVP 완료 (M1~M6 + M10, `status: in-progress` 유지 — Stage-2 M7~M9는 별도 kickoff로 이연되었으므로 아직 `completed`로 전환하지 않음).
  - **인앱 설정 + OS 자격 증명 저장**: `server/deploy/settings.py`(비민감 설정 — OSC 포트·플러그인 임포트 디렉터리·활성 프로바이더 — OS별 표준 사용자 config 경로 저장, 자격증명 유사 키 거부) + `server/deploy/keystore.py`(macOS Keychain/Windows Credential Manager 어댑터, 저장소 미가용/잠금/거부 시 평문 디스크 폴백 0 + 세션 한정 in-memory 폴백, 크래시/진단 덤프 env-scrub) + `server/web/settings_api.py`(`/api/settings`, `/api/keys` — 키 값은 절대 응답에 미포함) + `ui/src/components/SettingsPanel.tsx`.
  - **CopilotResponder provisioning**: `server/deploy/provisioning.py` + `server/web/provision_api.py`(`/api/provision/responder`) — 번들된 Lua responder(`console/lua/`)를 임포트 디렉터리로 설치 + onPC 로드/OSC 출력 포트 안내 UI(`ResponderGuide.tsx`); 앱이 직접 발행하는 `Import Plugin` 실행은 SPEC-COPILOT-MVP-001의 단일 안전 관문을 경유하고 감사 로그에 1:1 기록됨을 회귀 테스트로 증명(AC-DEPLOY-017).
  - **health/오류 UX**: 기존 HealthMonitor 3종 상태(online/console_offline/responder_degraded)에 원인+조치 한국어 안내 레이어(`healthGuidance`) 추가; 키 부재/무효는 기존 auth 오류 스크럽 경로로 raw SDK 원문 노출 없이 설정 UI로 유도.
  - **PyInstaller onedir 패키징**: `packaging/GrandMA3-Copilot.spec` + `entitlements.plist` + `sign.sh`(ad-hoc 기본, Developer ID 서명·notarization은 인증서 확보 시 코드 변경 없이 활성화) + `build.sh` — `dist/GrandMA3 Copilot.app`(arm64) 빌드 성공; `server/resources.py`가 frozen(`sys._MEIPASS`)/dev 자산 경로를 단일 리졸버로 통합.
  - **안전 불변식 보존 + local-only 검증**: 배포 셸을 감싼 구성에서도 단일 안전 관문 아키텍처·블랙리스트 승인 회귀·OSC 송신 표면 allowlist(fail-closed) 전부 green; `127.0.0.1` bind + localhost UDP + 원격 백엔드 미의존 + 오프라인 동작 확인.
  - **패키지 `.app` end-to-end 검증**: `packaging/verify_packaged_e2e.py` 8/8 PASS(기동→설정→provisioning→health→종료); 983 pytest + 기존 vitest 전부 green.
  - **환경-게이트 N/A**(이 빌드 호스트 한정, 코드 변경 없이 적합한 환경에서 활성화 가능): universal2(arm64+x86_64) 빌드, Windows x86_64 빌드, 실제 Developer-ID 서명·공증.
  - **Stage-2 이연**: Tauri v2 데스크톱 셸, Python 백엔드 sidecar 번들, 자동 업데이트, updater 재시작 안전상태 보존(M7~M9)은 별도 kickoff로 이연 — 본 항목은 Stage-1 배포 가능 MVP 마감만 반영한다.
  - **v0.3.0 라이브 E2E 하드닝(M14~M18, `status: in-progress` 유지)**: 2026-07-20 실제 grandMA3 onPC 2.4.2 + 실제 Gemini 라이브 데모에서 983-test 단위 스위트가 놓친 통합 결함 6건 중 5건(#2~#6)을 REQ-DEPLOY-028~032/AC-DEPLOY-019~023으로 fold-in 후 TDD 구현(결함 #1은 commit `1d65375`에서 이미 수정, 이력만 기록). 전체 스위트 `1017 passed`(983→1017, +34).
    - **M14 / #2 — 기동 시 활성 프로바이더 키 주입** (`server/web/serve.py` `build_runtime` + `server/deploy/keystore.py`): `build_runtime`이 OS 자격 증명 저장소의 활성 프로바이더 키를 프로바이더 클라이언트 생성 전에 프로세스 env로 주입; 기설정 env 키는 보존(덮어쓰지 않음); 저장소 미가용 시 REQ-DEPLOY-006a 세션 한정 폴백으로 강등. 신규 인스턴스가 "No API key"로 기동 실패하는 회귀를 봉쇄.
    - **M15 / #4 — 직전 생성 연출 상태 세션 추적**: 직전에 생성된 Seq/Exec를 세션에 캡처해 다음 턴에 주입 + "맹목적 수정보다 재생성" 유도 스티어를 추가, 후속 수정 지시가 엉뚱한 대상(예: `Seq 1`)이 아닌 방금 만든 대상으로 해소되도록 함.
    - **M16 / #5 — Gemini 캐시 만료 복구 + 키 오류 분류**: `403/404 "CachedContent not found"` 주입 시 캐시 재생성 후 1회 재시도; 키 누락 `ValueError`를 `unexpected`가 아닌 인증(auth) 오류로 분류.
    - **M17 / #3 — rig-context 실제 풀 번호 노출**: `get_rig_context`가 오브젝트마다 `{no, name}`을 방출해, 모델이 위치 인덱스가 아닌 실제(비연속 가능) 풀 번호를 참조하도록 함 — 존재하지 않는 오브젝트(예: `Group 3`) 생성 방지.
    - **M18 / #6 — OSC 수신 포트 동일-포트 재바인드 복구**: `SO_REUSEADDR` + 유한 재시도(포트 드리프트 없음, REQ-026)로 재바인드; 복구 불가 시 재설정 안내가 담긴 타입드 `ReceivePortInUseError`를 발생 — 이전에는 원시 크래시.
    - **테스트 인프라**: `server/tests/conftest.py`에 스위트 전역 in-memory keyring autouse fixture 추가 — M14가 실제 OS Keychain을 건드리지 않고 무인 `pytest` 실행을 복원.
    - **이연 항목**(진행 중 감사 추적, progress.md §E.4에 기록): (a) `#6` 앱 셸 안내 표시 — 브리지는 타입드 예외를 던지지만, `server/web`이 이를 잡아 표시하는 배선은 단일 OSC 관문 보안 불변식(AC-MVP-019, `server/web`의 `server.bridge` import 금지)과 상충해 보안 allowlist 결정 대기로 이연; (b) 5개 결함 전체의 라이브 onPC 재검증 — 단위 테스트가 배선을 증명하나 실하드웨어+실 Gemini 동작은 환경-게이트; (c) `console/lua/copilot_responder.lua:322`의 더 깊은 슬롯 정합성 — 진짜 갭 있는 rig에서 Lua 소스단 수정은 라이브-콘솔-게이트.
  - **v0.4.0 Stage-2 M7 — Tauri v2 데스크톱 셸(`status: in-progress` 유지, M8/M9 별도 kickoff 이연)**: Stage-1 PyInstaller onedir 백엔드를 sidecar로 재사용하는 네이티브 데스크톱 셸을 신규 구현(`src-tauri/`) — AC-DEPLOY-024~029 대응.
    - **M7.1 / AC-DEPLOY-025 — `/ws` Origin+per-launch-token 핸드셰이크** (`server/web/app.py`, `server/web/launcher.py`, `ui/src/useCopilotSocket.ts`): WebSocket `accept()` 이전에 Origin allowlist 대조 + `secrets.token_urlsafe` per-launch 토큰 상수-시간(`hmac.compare_digest`) 비교 게이트 삽입 — cross-site WebSocket hijacking(FEAS-9) 차단. 프로토콜 v1/`messages.py` 스키마 무변경.
    - **M7.2 / AC-DEPLOY-026 ③④ — 백엔드 parent-liveness watchdog** (`server/web/launcher.py`): Tauri force-quit 시(`RunEvent::Exit` 미발화) sidecar가 자기 그룹을 self-reap — PRIMARY(pipe/heartbeat EOF, 레이스 창 없음) + FALLBACK(`getppid()==1` 폴링, bounded ≤1s) 이중 트리거로 FEAS-5 Option C 백엔드 절반 완성.
    - **M7.3 / AC-DEPLOY-027 — SAFETY-2 교차언어 이중 스캔** (`server/tests/test_deploy_safety_invariants.py`, `packaging/verify_packaged_e2e.py`): Layer① `src-tauri/**/*.rs`+`Cargo.toml`/`Cargo.lock` deny-all 정적 스캔(부재/빈 트리 fail-closed, `files_scanned>0` assert) + Layer② 실제 설정 send_port wire-level 싱크(감사 로그 1:1 대조 + 양성 관측 assert + synthetic rogue 주입 증명) — 둘 다 vacuous-pass 차단 프루프 포함.
    - **M7.4a / AC-DEPLOY-024 — Tauri v2 셸 스캐폴드 + sidecar spawn** (`src-tauri/` 신규: `Cargo.toml`, `tauri.conf.json`, `src/main.rs`, `src/sidecar.rs`, `src/tray.rs`, `capabilities/default.json`): PyInstaller onedir 백엔드를 sidecar로 spawn, 네이티브 창이 동일 `ui/dist` 로드, 트레이+연결 상태 배지(M5 재사용), capabilities에서 sidecar-spawn 외 네트워크 플러그인 deny.
    - **M7.4b / AC-DEPLOY-025·026 ①② — Rust process-group kill + Stage-2 토큰 IPC** (`src-tauri/src/sidecar.rs`, `src-tauri/src/main.rs`): Unix setsid/setpgid 프로세스-그룹 kill을 authoritative teardown으로 배선(`RunEvent::Exit`), per-launch 토큰을 Tauri IPC로 웹뷰에 주입(디스크 미기록); 부수적으로 설정 영속화 부팅 수정(sidecar가 `settings.toml` 포트를 boot 시 실제로 준수) + 중복 로드 수정 + 허위 종료 다이얼로그 수정.
    - **M7.5 / AC-DEPLOY-027 Layer②** (`server/safety/console.py`, `server/safety/gate.py`, `packaging/wire_sink.py`): OSC 송신을 `DeploySend`/`ExecOutcome.sends`로 per-send 세분화해 wire-level 감사 1:1 대조 granularity를 1건 승인 의미론 보존한 채 완성.
    - **라이브 검증**: 패키지된 `.app`을 실제 grandMA3 onPC 2.4.2에 대해 실행 — health `online`, 백엔드가 설정된 UDP 9005에 바인드, 콘솔 피드백 왕복 확인. 이 라운드에서 발견·수정된 통합 결함(전부 수정 완료): sidecar 이름 해석 ENOENT, ready-line 레이스, declared-pid 신뢰 문제, 설정-무시-부팅(9000 바인드 vs 9005 설정), 문서 중복 로드, 종료 시 허위 "시작 실패" 다이얼로그, sidecar 부재 시 패닉(→ 가독 가능한 다이얼로그로 교체).
    - **환경-게이트 N/A**: Windows Job Object(KILL_ON_JOB_CLOSE) 경로, universal2 셸 빌드, 실제 notarization — 적합 환경 확보 시 코드 변경 없이 활성화.
    - **M8/M9 Stage-2-DEFERRED**: 자동 업데이트(M8)·코드 서명/공증(M9)은 본 kickoff 스코프 밖 — 별도 kickoff에서 AC 신설·검증. `status: in-progress` 유지.

- **SPEC-COPILOT-EVAL-001** — Phase 0 boardop 실사용 평가 및 격차 분석 완료 (문서 폴백 모드, REQ-EVAL-014). onPC 구동 실행 파일 미확보(베타 신청 대기)로 인해 문서·데모 영상 관찰 기반 평가로 전환(사용자 승인, AskUserQuestion 2026-07-16)하여 run-phase를 완결했다.
  - `.moai/project/research/boardop-eval-log.md` — 환경 기록(6종 중 5종 실측 + 1종 관찰 불가 명시) + 대표 시나리오 11종(S1~S10 + 파괴적 시나리오 S-D) 3태그 분류(관찰 기반 4 / 관찰 불가 7) 및 행별 근거 출처 인용.
  - `.moai/project/research/boardop-gap-analysis.md` — 4축(①한국어 UX ②안전장치 ③도구 커버리지 ④신뢰성) 전부 커버하는 격차 14건(Phase 1(MVP) 반영 11 / 보류 3 / 미반영 0) + FSL-1.1-Apache-2.0 라이선스 검토 결론(§3 — 내부 사용·평가 허용, 경쟁 제품 코드 재사용은 릴리스별 2년 제약, 아키텍처만 벤치마킹·clean-room 구현) + AC-EVAL-005 boardop 코드 미포함 4항목 이진 체크리스트 검수(§4, 전항목 0건).
  - AC-EVAL-001~006 전부 PASS(문서 폴백 경로), AC-EVAL-007(선택적 Claude/Gemini 비교)은 라이브 세션 미실행으로 평가 제외 — acceptance.md 기준 총 7개 AC 중 6개 평가·PASS, 1개 조건부 미평가.
  - amendment 이력: v0.2.0(LLM 듀얼 프로바이더 전략) → v0.3.0(문서 폴백 재조정, plan-audit delta FAIL 0.87) → v0.3.1(수정 후 delta re-audit PASS 0.95).

### Changed

- `.moai/project/tech.md` §5.1 — 단일 프로바이더(Anthropic 전용) 모델 전략 서술을 SPEC-COPILOT-MVP-001 REQ-MVP-038~041(프로바이더 교체 가능 추상화 계층, Claude/Gemini 듀얼 지원, 오류율 기반 기본 프로바이더 선정, 프로바이더별 캐싱) 반영으로 갱신하여 amended SPEC 상태와의 괴리를 해소.
