# MA3 코파일럿 — 패치 자동화 · 좌표 판독 · 응답기 1.6.0 핸드오프 (2026-08-18)

> 이 세션은 실기(사용자 콘솔) 위에서 진행됐고, 모든 수치는 **실측**이다(추측 아님).
> 프리셋 기능은 이 워크트리에서 **의도적으로 취소**했다 — 아래 §7 참조.

## 0. 한 줄 요약
패치가 0건 생성되던 원인 3개(주소 폭 추측 · 목적지 조건 오해 · 이중 인용부호)를 걷어내
**앱이 패치를 직접 실행·검증**하게 만들고, 좌표 판독을 **25.6초 → 0.77초**로 줄였다
(응답기에 `props` 배치 판독 신설, 1.5.0 → **1.6.0**, 실기 배포 완료).

## 1. 실행 환경 / 기동 함정 (여기서 시간을 가장 많이 잃었다)
- 백엔드: 감독 프로세스 `copilot-web2` — `.venv/bin/python -m server.web --receive-port 9005`,
  cwd=이 저장소, ready=포트 8765, persist. `http://127.0.0.1:8765/healthz`.
- **백그라운드 `&`로 띄우면 SIGHUP으로 죽는다.** 반드시 감독 프로세스(hub start)로.
- **앱 번들이 두 개다. 혼동 금지**:
  - `dist/GrandMA3 Copilot.app` = PyInstaller **사이드카 페이로드**(백엔드만).
    `bash packaging/build.sh`가 만든다. `test_deploy_tauri_shell.py`가 이 레이아웃을 검사하므로
    여기에 Tauri 번들을 덮어쓰면 테스트가 깨진다(이 세션에서 실제로 깨뜨렸다).
  - `src-tauri/target/release/bundle/macos/GrandMA3 Copilot.app` = **UI 창**(사용자가 쓰는 것).
- **Tauri는 빌드 시점의 `ui/dist`를 앱에 굽는다.** UI 수정 후 `env -u CI npm run shell:build`
  없이는 구버전 화면이 뜬다. `CI=1` 환경변수가 tauri CLI와 충돌하므로 `env -u CI` 필수.
- **재기동 확인은 pid로 한다.** `osascript quit`은 PyInstaller 앱에 안 먹고,
  `pkill -f "python -m server.web"`은 frozen 바이너리에 안 걸린다. `/healthz`가 200이어도
  구버전 프로세스일 수 있다(이 세션에서 "고쳤는데 안 고쳐졌다"의 진짜 원인).
- **PyInstaller 재빌드 = 서명 신원 변경 → macOS 키체인 승인 프롬프트**가 뜨고 사이드카가
  `SecItemCopyMatching`에서 멈춘다(스택으로 확인). 화면의 «항상 허용»을 한 번 눌러야 한다.
  레포 venv 백엔드는 이 문제가 없다 — 개발 중에는 그쪽이 안전하다.

## 2. 콘솔 연동 (onPC 2.4.2.2)
- OSC: 콘솔 수신 8000 / 앱 수신 **9005**(콘솔 송신 row가 9005 고정 — 다른 포트로 리스너를
  띄우면 답이 안 온다. 실기 검증 스크립트는 반드시 9005를 쓰고, 그러려면 앱을 잠시 내려야 한다).
- 새 쇼는 `Backup > Save As`로 **`CopilotOscTemplate`에서 파생**시킬 것(OSC 설정·플러그인 상속).
  `New Show`로 시작하면 Interface 선택이 GUI 전용이라 앱이 스스로 복구할 수 없다.
- **인라인 Lua가 만능 우회로다**: `Lua "..."`를 `/copilot/cmd`로 보내면 응답기 없이도
  콘솔에서 실행된다(파일로 결과를 쓰면 회수 가능). 응답기 교체·진단 때 이 경로를 썼다.
  단 이중 인용부호는 못 쓴다 → Lua 긴 문자열 `[[...]]`. `[[[`는 렉서가 오해하므로 변수로 분리.
- `ConsoleLink.execute`는 **이중 인용부호를 담은 명령을 거부**한다(결과 캡처 래핑 불가).
  명령줄 인용은 전부 단일 인용부호로.

## 3. 패치 — 갈림길은 "누가 실행하나"가 아니라 "명령 목적지가 어디인가"
**재실측 결과(앱의 실제 배포+실행 경로)**
| 조건 | 결과 |
|---|---|
| Patch 편집기 열림 + **서버 실행** | 60 → 62 **생성됨** |
| 목적지 Root + 서버 실행 | 0건 (AddFixtures뿐 아니라 `Remove`도 no-op) |
| `ChangeDestination Patch/Stages/1/Fixtures` | Failed |
| `ChangeDestination ShowData/Patch/...` | Failed |
| `cd Patch` | OK지만 무효 |
| `Menu Patch` | Not implemented |

→ 기존 모델("사람이 명령줄에 직접 타이핑해야 한다")은 목적지 조건을 발화 주체로 오인한 것.
서버는 목적지를 옮길 수 없으므로 조작자에게 남는 일은 **편집기를 열어 두는 것 하나**다.
목적지는 서버가 읽을 수도 없다(`GetFocus()`는 명령줄 위젯만 반환 — 실측).

**구현(`patch_fixtures`)**: 타입별 플러그인 이름(`CopilotPatch` + 타입 영숫자) → 배포 →
**앱이 `run_commands`(게이트 경유)로 실행** → 재조회 검증. 0건이면 "편집기를 열어 주세요"
카드 한 장(타이핑 요구 없음) → 앱이 재실행 → 재검증. 게이트가 막았으면 재시도하지 않고
게이트 판정을 그대로 올린다.
- **게이트 우회 금지**: 실행 포트의 유일한 호출자는 `run_commands`(AC-PRECHK-014 ②).
  직접 `execution_port.execute`를 부르면 라이브잠금·승인이 통째로 건너뛰어진다.
- 테스트 가짜가 실제 포트보다 넓으면 계약을 못 지킨다 — `ScriptedExec`에 `run([...])`이
  남아 있어 스위트 8,865개가 통과하면서 실기에서 AttributeError로 죽었다. 지금은
  `execute` 하나만 두고, 프로토콜 밖 접근을 즉시 실패시키는 StrictPort 가드가 있다.

## 4. 모드 폭(footprint)은 `TotalFootprint`가 진실
- `DMXChannels` 자식 개수는 **논리 채널 수**다. 16bit 채널(coarse+fine)이 주소 2칸을 먹으므로
  주소 계획에 쓰면 겹쳐서 콘솔이 전량 거부한다(사용자 실패의 직접 원인).
- 실측 대조(콘솔 UI "DMX Footprint"와 일치): Esprite Mode 1=**49** / Mode 2=**42**,
  LEDBeam 350 Mode 1=22·2=16·3=24, Sharpy Plus Mode 0=31, Xtylos Mode 0=30,
  Forte HP Mode 1=54·2=56, Spiider Mode 1=49 … (모델이 추측한 14·26은 전부 틀렸다).
- 판독기: `server/prechk/mode_read.py::read_type_mode_widths` — 모드 목록 + 모드별
  `TotalFootprint` 속성. `footprint.py`는 "state 전용"이 AC로 고정된 모듈이라 분리했다.
- 모드가 여럿이고 사용자가 지정하지 않았으면 **채널 수를 보여 주는 선택 카드**를 띄운다.
  `channels_per_fixture`는 모드 트리를 못 읽을 때만 쓰는 폴백이며 실측값이 항상 이긴다.

## 5. 픽스처 타입 이름 매칭 / GDTF·MVR
- `robe esprite` ↛ `Robin Esprite`였다(부분문자열 대조 실패) → "라이브러리에 없음"으로 오판,
  불필요한 GUI 절차를 안내. `server/vwx/librarywatch.py::candidate_names`로 **토큰 대조** 추가
  (`MIN_DISTINCTIVE_TOKEN=4`, 3자 조각은 라이브러리를 훑지 않음, 등기부 등록 + 양방향 대조군).
- 후보 1개면 **카드 없이** 진행(다음 모드 카드 제목에 콘솔 이름이 나오므로 두 번 묻지 않음),
  여럿이면 선택 카드(+"이 중에 없습니다" → 라이브러리 추가 경로).
- **GDTF/MVR 명령줄 임포트는 작동하지 않는다**(실측 4형태): 응답은 `Failed`이고,
  타입은 늘어나지만 **DMX 모드가 없는 빈 껍데기**만 남는다. MVR도 전부 `Failed`.
  → "MVR/GDTF 파일을 주겠다" 선택지는 **제거**했다(못 하는 일을 제안하면 안 된다).
  파일 배치까지는 앱이 할 수 있고(콘솔 Library 탭 Internal에 나타남), 쇼에 넣는 마지막
  한 번의 선택은 GUI 전용이다.

## 6. 좌표 판독 — 응답기 1.6.0 `props` 배치
- 원인: `prop`은 속성 1개당 왕복 1회, **실측 66.7 ms**. 80대 좌표 = 속성 320회 +
  슬롯 복구 조회 ~80회 ≈ **26초**, 그리고 이전 한도(240=60대)에서 전체-리그 요청이 전부 거절
  ("3D 좌표 응답이 … 조회 한도에 도달"). 200대는 ~1,000왕복 ≈ 67초로 한도를 올려도 답이 아니다.
- 신설 `props <id> <path> <startSlot> <count> <Name1,Name2,...>` →
  `rows:[{i, p:{name:value}}]`, `node.childCount`, 끝나면 `next` **부재**.
  풀 슬롯 기준 페이징(희소 풀에서 이웃 좌표를 읽는 사고 방지), 전송 한도(1900B) 초과 행은
  잘라내고 `next`로 이어받기. 문서: `console/lua/PROTOCOL.md` §4.7.
- 서버: `build_props_query` → `ConsoleLink.query_properties` → `tools.py`의 배치 우선 판독.
  **구버전 응답기·미배선 포트면 낱개 조회로 폴백**(기존 동작 그대로), 배치가 답한 픽스처는
  왕복 0회이므로 한도가 발화하지 않는다. 한도는 320(=80대)로 올렸고 이제 사실상 무의미.
- 실측: 80대 **0.77초**(80/80 complete), 페이지당 8행(이름 포함·퍼센트 인코딩 후 한도),
  200대 추정 ~25페이지 ≈ 1.7초.
- **응답기 교체 절차(위험 작업 — 이 순서를 지킬 것)**: ① 새 소스를 다른 이름
  (`CopilotResponderNext`)으로 임포트해 ping·props 응답 확인 → ② 비활성 중복본(`#2`,`#3`) 정리
  (이름 충돌 시 콘솔이 자동 개명해 링크가 끊긴다) → ③ **raw OSC**로 `Delete Plugin 1` +
  `Import Plugin 1 'copilot_responder'` (exec 래핑은 응답기를 거치므로 삭제 후엔 못 쓴다)
  → ④ `uv run python -m server.tools.responder_roundtrip --expect-version 1.6.0`.
  실패 시 복구는 콘솔 GUI 붙여넣기(README §2.1).

## 7. 프리셋 — 이 워크트리에서 취소함 (MAcopilotpos가 정본)
사용자 지시로 되돌렸다. 삭제: `server/presets/`, `test_presets_basic.py`,
`test_basic_preset_router.py`. `session.py`는 원복(단 §8의 상태 라벨 2개는 유지).
**다만 아래 실측·설계 지식은 MAcopilotpos 작업에 그대로 쓸 수 있다:**
- **의도 판별 버그**: `_BASIC_POSITIONS_REQUEST`가 `기본` → 16자 내 `포지션|프리셋` → 동작동사
  **순서**를 요구해서, "…프리셋 **기본설정**과…" 어순에 불매칭 → 핸들러 미발화 →
  모델이 손으로 Pan/Tilt 0 80줄만 냈다(프리뷰에 `Store Preset`이 없던 게 증거).
  처방: 순서 무관 lookahead 3개 + 동작동사에 `설정` 추가.
- **리그 공통 속성(실측)**: 6종 전원 `Dimmer`,`Pan`,`Tilt`,`ColorRGB_R/G/B`.
  `ColorRGB_W`는 LEDBeam 350·Spiider만, `CTO`는 Esprite·Forte·Xtylos만 →
  기본 프리셋은 RGB/Dimmer만 써야 타입마다 다른 색이 되지 않는다.
- **프리셋 풀 번호**: 1=Dimmer, 2=Position, 3=Gobo, 4=Color, 5=Beam, 6=Focus, 7=Control,
  8=Shapers, 9=Video, 21~23=All 1~3.
- **컬러 look은 값 라인을 공유한다**(`ColorRGB_R At 100`이 10종 중 6종에 등장).
  한 `run_commands` 번들에 몰면 중복제거가 뒤 look의 값을 접고 **빈 프로그래머에 Store**가
  나가며 콘솔은 ok를 답한다 → **look 하나당 별도 번들**. 참고: `dispatch(call)`에 컨텍스트를
  넘기지 않으면 `executed_ok`가 빈 집합이라 호출 간 접힘은 없다(핸들러 경로는 안전).
- 값 라인은 항상 R·G·B 세 줄 모두(한 축만 쓰면 이전 값이 남아 색이 섞인다).
- `Store Preset`은 경고 없이 덮어쓴다 → 시작 번호는 항상 사용자에게 받는다.
- `Store`와 `Label`은 **별도 명령**(인라인 라벨 미적용, 2026-08-16 실측).

## 8. 콘솔 현재 상태 (다음 세션이 그대로 이어받는다)
- 응답기 **1.6.0**(슬롯 1). 중복본 `#2`,`#3`는 삭제됨.
- 플러그인 풀: 1=CopilotResponder, 4=CopilotPatchRobinEsprite, 5=CopilotPatchRobinLEDBeam350,
  6=CopilotPatchSharpyPlus, 7=CopilotPatchRobinMMXSpot, 8=CopilotPatchMacAuraXB.
- Stage 1 픽스처 **80대, FID 1~80 연속**. 픽스처 타입 6종.
  그룹 1=All Fixtures, 2=Robin Esprite, 3=Robin LEDBeam 350, 4=Sharpy Plus, 5=Mac Aura XB.
- **프리셋(내가 실기로 만든 것 — 중복 주의)**: Position 2.1~2.10(Home/Wall/Audience/Center/
  Vocal DSC/Fan Out/Fan In/Cross/Ring Out/Ring In), Color 4.1~4.10(Red…White),
  Dimmer 1.1~1.6(0~100%), All 1 풀 21.1~21.5 = 페이저 5종(Soft Wide Sweep / Relative Orbit
  Circle / Soft Rise Wave / Club Rgb Chase / Beat Pulse, `instantiate_fx` verdict=complete).
  MAcopilotpos 구현으로 다시 잡을 거면 먼저 비울지 결정해야 한다.
- 진단용 프로브(픽스처 FID 900~920, 임시 플러그인, 스테이징한 GDTF/MVR)는 **전부 정리했다**.

## 9. 커밋 상태
- 브랜치 `research/ma3-effects-phaser`. **미커밋**(사용자가 직접 커밋 예정).
- 테스트: 서버 **8,906 passed**(프리셋 취소 후), ruff format/check 통과.
- 변경 파일: `console/lua/{copilot_responder.lua,PROTOCOL.md}`,
  `server/bridge/protocol.py`, `server/safety/console.py`, `server/orchestrator/tools.py`,
  `server/prechk/{footprint.py,mode_read.py(신규)}`, `server/vwx/{librarywatch.py,stagedpatch.py}`,
  `server/web/{question.py,session.py,PROTOCOL.md}`,
  `ui/src/{protocol.ts,styles.css,components/QuestionCard.tsx,components/QuestionCard.test.tsx(신규)}`,
  테스트 신규 4(`test_librarywatch_matching`, `test_lua_responder_props`,
  `test_resolve_type_tool`, `test_spatial_batch_read`) + 기존 6 갱신.
- 제외: `.moai/*` 하네스 로그, `src/artifacts/`, `.claude/settings.local.json.lock`.
- **다른 워크트리 주의**: 콘솔 응답기는 이미 1.6.0이다. 이 커밋이 없는 워크트리에서 앱을
  돌려도 폴백으로 동작하지만 좌표 판독이 다시 26초대로 느려진다 → 함께 머지하는 편이 좋다.

## 10. 다음 작업
1. **"복합 설정"의 정의 확정** — 사용자에게 물어야 한다. 두 해석: ① All 타입 프리셋
   (위치+색+밝기를 한 칸에) ② 복합 페이저(서클+컬러 체이스 동시). 미결.
2. 위 변경 커밋 + MAcopilotpos 프리셋 작업과 병합(§6 응답기 버전 정합).
3. (개선) 배치 판독을 **컨테이너 열거까지** 대체 — 지금은 `state` 한 번 + 배치로 이름을
   가져오지만, `state`가 24행 한도라 큰 리그에서 첫 페이지만 쓰인다. `props`가 이름을
   실어 오므로 열거 자체를 배치로 대체하면 왕복이 더 준다.
4. (개선) 페이지당 8행은 퍼센트 인코딩 후 1900B 한도 때문 — 행 키를 짧게 하면(예: `n/f/x/y/z`)
   페이지당 행이 2배 이상 늘어난다. 프로토콜 변경이므로 응답기·서버·문서 동시 수정 필요.
5. 프리셋 캐논(이름·순서·색감)이 현장 관례와 맞는지 조명감독 확인 — `_COLOUR_CANON` 한 곳에서 고정.
