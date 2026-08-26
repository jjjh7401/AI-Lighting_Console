# t104 실기 — 페이징이 111개를 열었다. 다만 그중 21개는 안 읽힌다

판정: 닫는 조건 넷 충족 + 다섯째(열거≠판독) 측정 완료

측정 트리: .claude/worktrees/t104
브랜치: WT-introspect-paging
응답기: 1.6.1 -> 1.6.2 (배치 완료, 콘솔 회신으로 확인)
콘솔: grandMA3 onPC 2.4.2 · app_gma3 pid 78611 · UDP 8000 송신 / 9005 수신

## 1. 주장 (Claim)

1. 응답기 1.6.2 가 배치됐고 콘솔이 그 버전을 답한다. **재임포트로는 안 됐고,
   사람이 붙여넣어야 했다** — README §2.1 이 예고한 그대로다.
2. `introspect` 페이징이 실기에서 동작한다. `DataPool/PresetPools/1/2` 의
   프로퍼티 **138개 전부**가 열거된다(이전엔 27개).
3. **열거 138 ≠ 판독 138.** 실제로 값을 답하는 것은 **117개**이고 **21개**는
   `property not readable` 로 거절한다.
4. `PRESETMODE` 가 **판독된다.** t100 이 「이 채널로 못 읽는다」로 적어 둔 그
   질문에 후보 채널이 생겼다. 다만 **판별력은 미측정**이다 — 아래 §5 참조.

## 2. 증거 (Evidence)

### 2-1. 채널 신뢰성 — 배치 전후 각각 세웠다

응답기가 바뀌면 이전 대조군은 다른 프로그램에 대한 관측이므로 다시 쐈다.

    배치 전  날조 대조군  path segment not found: 'FixtureTypesZZZNotAThing'  (이유를 댄 거절)
             양성 대조군  Patch/Stages/1/Fixtures  childCount 86 · 회신 19 · truncated True
    배치 후  날조 대조군  같은 문면으로 다시 거절
             양성 대조군  childCount 86 · 회신 19 · truncated True  (동일)

날조 대조군이 **침묵이 아니라 이유를 대며** 거절했으므로 이후의 ok 가 증거다.

### 2-2. 배치 — 재임포트는 안 먹었다

    배치 전 콘솔 버전                          1.6.1
    설치된 osc_slot (덮어쓰기 전 판독)          2   <- 번들 기본값과 일치, 현장 설정 안 깨짐
    백업                                       copilot_responder.lua.bak-20260826-163328
                                               (체크섬이 원본과 일치)
    install_responder(osc_slot=2) 후 디스크     VERSION 1.6.2 · osc_slot = 2  (되읽어 확인)
    임포트 직전 콘솔 버전                       **1.6.1**   <- 풀이 자기 사본을 들고 있다
    Import Plugin 'copilot_responder' (게이트)  executed_ok "OK"
    임포트 직후 콘솔 버전                       **1.6.1**   <- OK 를 받고도 안 먹었다
    감독 붙여넣기(Option B) 후 콘솔 버전         **1.6.2**   PASS

🔴 **성공 메시지는 증거가 아니다.** `executed_ok "OK"` 를 받은 임포트가 실제로는
아무것도 안 바꿨다. `--expect-version` 이 없었으면 여기서 「배치 완료」라고 적고
넘어갔을 것이고, 이후 모든 측정이 1.6.1 에 대한 것이 됐을 것이다.

⚠️ **승인 통로는 한 번도 안 물어졌다** — `approval_requests` 가 빈 배열이었다.
게이트는 통과(screen)했으나 `Import Plugin` 을 위험 명령으로 분류하지 않은
것으로 보인다. 「승인받았다」고 적지 않는다. 이 분류가 옳은지는 **미측정**이다.

콘솔 화면(감독 제공)이 독립 채널로 같은 것을 확인했다 —
`copilot_responder v1.6.2` 와 `SendOSC 2` 가 콘솔 자신의 명령 이력에 찍혔다.

### 2-3. 페이징 — 창마다 offset 에코가 증가한다

무한 루프가 이 결함군의 실패 모양이라, 에코를 창마다 대조했다.

    창  요청 offset  에코 offset  받은 개수  truncated
    1        0           0          27        True
    2       27          27          29        True
    3       56          56          26        True
    4       82          82          26        True
    5      108         108          26        True
    6      134         134           4        False
    합계                            138

요청과 에코가 **여섯 창 전부 일치**했고 단조 증가했다. 창 폭이 27·29·26·26·26·4
로 **일정하지 않다** — 고정 보폭이었으면 이름을 건너뛰었을 것이다. 「받은 개수만큼
전진」이 옳았다.

    페이징 없이   fields 27 · total 138 · truncated True   <- 기준선 재현
    --all-pages   fields 138 · total 138 · truncated False · unique 138

### 2-4. 열거 ≠ 판독 — 138 중 117만 답한다

138개 이름 전부에 `prop` 을 쏘아 셌다. 전수는
`.moai/reports/t104/property-census.json` 에 있다.

    열거      138
    판독 가능 117
    판독 불가  21   (전부 "property not readable: <이름>")
    합계 검산 138 == 138

판독 불가 21개 전문:

    GUID · SCRIBBLE · APPEARANCE · PREVIEWCOPY · INITIALMATRICKS · INPUTFILTER
    OFFFADE · AUTOSTART · AUTOSTOP · AUTOFIX · AUTOSTOMP · SOFTLTP
    SWAPPROTECT · KILLPROTECT · USEEXECUTORTIME · OFFWHENOVERRIDDEN
    AUTOPREPOS · PRIORITY · PLAYBACKMASTER · OUTPUTFILTER · EXECUTORDISPLAYMODE

GUID 가 선례였고, 나머지 20개가 같은 계열임이 이번에 드러났다.

## 3. 기준선 귀속 (Baseline-attribution)

    대상 경로     DataPool/PresetPools/1/2  (딤 풀 슬롯 2, 이름 "쇼 하이")
    그 풀 상태    childCount 6 · 회신 6 · truncated False  (M4 가 넣은 6건 그대로)
    응답기        1.6.2 (콘솔 회신으로 확인, 파일 존재가 아니라)
    프로세스      app_gma3 78611 — 착수 시점에 다시 쟀다. 배차서의 pid 와 같았다

## 4. 미검증 (Gaps)

- **다른 클래스는 안 쟀다.** 117/21 분할은 `Preset` 클래스 한 오브젝트에 대한
  것이다. Group·Sequence·Fixture 가 같은 비율일 이유는 없다.
- **21개가 왜 안 읽히는지 모른다.** 이름만 셌고 원인(권한·타입·미구현)은 안 갈랐다.
- **`Import Plugin` 이 승인 통로를 안 거치는 것이 옳은 분류인지 미측정.**
- **페이징 상한을 안 쟀다.** 138 은 여섯 창에 들어왔다. 훨씬 큰 오브젝트에서
  창 수가 늘 때 멈춤 조건 넷이 여전히 사는지는 이 측정이 답하지 않는다.
- **절단 경계를 안 쟀다.** 창 폭이 26~29 로 흔들린 것은 페이로드 예산 때문으로
  보이지만, 그 예산값을 직접 재지 않았다.

## 5. 잔여 위험 (Residual-risk) 및 후속 카드에 넘기는 것

### 🔴 t100 — 「못 읽는다」가 뒤집힐 수 있다. 다만 판별력은 미측정

t100 은 되읽기 한계를 이렇게 적어 뒀다: 「그 프리셋이 정말 Universal 인가는
**이 채널로 못 읽는다**」. **`PRESETMODE` 가 판독된다.**

    슬롯  NAME     PRESETMODE  VALUESMODE  PRESETDATA  STOREDDATA  COUNT
      1   풀       Universal   Normal      (빈값)      (빈값)      0
      2   쇼 하이  Universal   Normal      (빈값)      (빈값)      0
      3   미드     Universal   Normal      (빈값)      (빈값)      0
      4   로우     Universal   Normal      (빈값)      (빈값)      0
      5   잔광     Universal   Normal      (빈값)      (빈값)      0
      6   아웃     Universal   Normal      (빈값)      (빈값)      0
    대조군: 없는 슬롯 99 -> "path segment not found: '99'" (지어내지 않는다)

⚠️ **이 여섯은 전부 `/Universal` **없이** 저장됐다**(M4 는 평문 `Store Preset 1.n`).
그런데 전부 `Universal` 을 답한다. 그러므로 **이 값은 이 표본에서 상수이고,
상수는 판별자가 될 수 없다.** 두 읽기가 남는다:

    (a) PRESETMODE 는 Store 플래그와 무관한 기본 모드를 답한다
    (b) /Universal 플래그가 무효이고 원래 전부 Universal 이다

여섯 표본이 전부 플래그 없이 저장된 것이라 (a)와 (b)를 **못 가른다.**
가르려면 `/Universal` 로 한 건 저장해 이 값이 변하는지 보면 된다 — 그게 t100 이다.

t100 에 넘길 것: **되읽기 채널이 생겼고 기준선이 이 표다.** 발사 후 PRESETMODE 가
같으면 그건 무정보이고, 다르면 그것이 답이다. t100 보고서의 「못 읽는다」 한 줄은
「읽히지만 이 표본에서 상수라 판별력 미측정」으로 정정돼야 한다.

### t105 — PRESETDATA 는 「안 읽힌다」가 아니라 「읽히는데 비었다」

`PRESETDATA` 와 `STOREDDATA` 는 판독 가능한 117 안에 있고 **빈 문자열**을 답한다.
`COUNT` 도 `0` 이다. 그런데 이 여섯 프리셋에는 M4 가 디머 값을 넣었다.

⚠️ **빈값을 부재의 증거로 읽지 마라.** t95 가 같은 형태를 이미 잡았다 — 내용이
있는 Group 도 이 채널로는 COUNT 0 을 답했다. t105 는 「값 이름이 없다」가 아니라
**「이 채널이 값을 안 노출한다」**를 재는 카드가 된다.

t114 가 육안으로 값을 확인하면 이 대조가 성립한다: 사람 눈에 값이 보이는데
PRESETDATA 가 빈값이면, 그것은 **채널의 한계**이지 프리셋의 상태가 아니다.
