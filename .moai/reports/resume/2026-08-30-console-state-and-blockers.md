# 콘솔 실측 상태 + 막는 것 둘 — 2026-08-30

> 리드 세션 인계. **콘솔 쓰기 0** — 읽기와 preview 만.
> 기준 `origin/main` `5d31690`. onPC pid **38706**.

## 1. 채널 신뢰성 — 대조군 둘 다 통과 (이걸 먼저 세웠다)

    판독 채널  실재 경로 ok / 날조 경로 "path segment not found"     trustworthy
    쓰기 채널  ZZZNOTACOMMAND -> "Illegal object" (executed_ok 아님)  trustworthy

포트 점유는 응답을 뜻하지 않으므로 매번 이걸 먼저 쏜다.

## 2. ~~지금 콘솔은 grandMA3 **기본 쇼파일**이다~~ — **반증됨 (2026-08-30, t98+t105)**

> 🔴 **이 절의 표제 주장은 틀렸다.** 리그 장비 **80대가 이미 패치돼 있다.**
>
>     t105 판독   state Patch/Stages/1/Fixtures -> childCount 80, truncated true
>     t98 판독    preview skipped[fid=521].occupant
>                 = {"address":"3.1","name":"Robin LEDBeam 350 21",
>                    "fixture_type":"Robin LEDBeam 350"}
>
> 서로 다른 두 채널이 같은 결론을 냈다. 아래 표는 **프리셋·그룹 풀만** 본 것이고,
> 패치를 안 봤다. **개수와 이름만으로 쇼파일 정체를 판정하면 틀린다** — 그룹 5개의
> 이름(`Robin Esprite`·`Mac Aura XB` 등)은 MA3 기본값이 아니라 **우리 리그의
> 장비 종류에서 생성된 이름**일 수 있고, 실제로 그쪽이 맞다.
>
> 정확한 상태: **리그는 우리 것, 프리셋은 우리 것이 아닌 혼합 상태.**
> `preset-dim.csv` 는 `풀`·`쇼 하이`·`미드`·`로우`·`잔광`·`아웃` 6건(한글)인데
> 콘솔 딤 풀은 `Dim 10`~`Alt Half` 20건으로 **하나도 안 겹친다**(t105 실측).
> 그 20건이 MA3 기본값인지 제3의 출처인지는 **안 쟀다.**
>
> 아래 원문은 무엇을 잘못 읽었는지 남기려고 보존한다.

### (원문 — 반증됨)

이름을 읽어 확정했다(개수만 보고 판단하면 틀린다 — 리드가 한 번 틀렸다):

| 항목 | 값 | 정체 |
|---|---|---|
| 그룹 5 | `All Fixtures` · … · `Mac Aura XB` | **장비 종류별 기본 그룹** |
| 딤 프리셋 20 | `Dim 10` … `Slam Run` | **MA3 기본 프리셋** |
| 포지션 프리셋 20 | `Home` … | **MA3 기본 프리셋** |
| 시퀀스 1 | `Default`, 큐 2개 | 빈 쇼 |
| 픽스처 80 | (17개만 회신 — 절단) | — |
| 플러그인 5 | 슬롯1 `CopilotResponder` + 패치 플러그인 4 | **사본 얽힘 없음** |

RIG 팩 이름(`ALL`·`KEY`·`FOH`·`BACK`·`SIDE-L`)도 우리 프리셋 이름(`풀`·`쇼 하이`)도
**하나도 없다.** 지난주 t114 가 만든 슬롯 7 `쇼 하이`(85%)도 사라졌다.

**이건 오히려 좋은 조건이다** — 덮어쓸 감독 작업이 없으므로 리그를 처음부터 잡을 수 있다.

## 3. 막는 것 ① — 픽스처 타입이 콘솔 라이브러리에 없다

`lxseq_e2e --action preview` 실측:

    런 1개 · 계획 1대 · 건너뛴 행 **85건**
    skipped 원인 분포 (t98 재측정 2026-08-30, 전수):
        type_unresolved    54   콘솔 라이브러리에 없다        -> 감독 GUI 필요
        mode_unresolved    24   타입은 있고 모드 이름만 안 맞는다 -> 감독 불필요
        address_occupied    7   우리 장비가 이미 그 자리에 있다  -> 감독 불필요
    "콘솔 라이브러리에 없다 — 콘솔에서 타입 추가 후 재실행하라"

🔴 **초판은 여기서 `skipped[*].kind = "type_unresolved"` 라고 적었다 — 틀렸다.**
표본 몇 건을 보고 `[*]` 를 썼다. 전수를 세면 원인이 셋이고, **31행(24+7)은
감독을 기다릴 필요가 없다.** 「전부」라고 쓸 때는 전부여야 한다.

    mode_unresolved 24행 상세 (FID 201~316, 전부 동일 사유):
        CSV 요구      "Martin MAC Aura XB"
        콘솔 실측 모드 Extended-Extended(25) / Extended-RAW(25) / Extended-RGB(25)
                      Standard-Extended(14) / Standard-RAW(14) / Standard-RGB(14)
        처방          --mode-overrides 로 재호출  ->  카드 t128

    address_occupied 7행 (FID 521~527, 유니버스 3):
        점유자        Robin LEDBeam 350 21 등 — **우리 장비다** (위 §2 반증)
        물음          기존 패치가 이미 CSV 의도를 만족하는가 -> 카드 t129

**남은 54행만이 감독 작업이다.** 아래 표는 그 54행에 관한 것이다.

| 콘솔에 있는 8종 | RIG 팩이 요구하는데 없는 것 |
|---|---|
| Robin Esprite · Robin Forte HP · Robin LEDBeam 350 · Robin Spiider · Xtylos · Sharpy Plus · Robin MMX Spot · Mac Aura XB | **ETC S4 LED S3 Lustr X8** · **Elation CUEPIX Blinder WW2** · **Martin Atomic 3000 LED** · **Look Unique 2.1** · **Robe MegaPointe** · Martin… |

🔴 **자동화 경로가 없다.** 픽스처 타입 라이브러리 추가는 콘솔 GUI 전용
(`Patch → Import Fixture Type`)이다. **감독 작업이다.**

## 4. 막는 것 ② — 응답기가 1.6.1 을 물고 있다

    디스크 (~/MALightingTechnology/.../copilot_responder.lua)  VERSION 1.6.2  osc_slot 2
    콘솔 (ping 회신)                                            **1.6.1**

t104 가 겪은 그 자리다 — **풀 캐싱**. `Import Plugin` 이 `executed_ok "OK"` 를 내도
콘솔은 옛 버전을 계속 답한다. **판정 기준은 콘솔이 답하는 version 이지 명령 결과가 아니다.**

결과: 프리셋 풀이 `childCount 20` 인데 19개만 회신(절단) → 임포트 하네스가
`pool_truncated` 로 **fail-closed**. 1.6.2 의 페이징이 이걸 푼다(t104 가 138개 열거 확인).

🔴 **처방은 「재배포」가 아니라 「얽힘 풀기」다** — t96 레인이 갈라 뒀다
(`.moai/reports/t96/pool-aliases.md`, main):

    배포된 파일  sha256 8c5b5def… = origin/main 내용 = **1.6.2**   디스크는 맞다
    주 체크아웃  6dbdbda6… = 1.6.0                                 그 갈래는 반증됐다
    백업 .bak-20260826-163328 = 1.6.1                              시간선이 닫힌다
    막는 것      **풀에 응답기 사본 셋** (슬롯 1 · 10 `#2` · 11 `_2`)

자기 자신을 지울 수 없어 앱의 자동 재배포가 별칭 스왑을 쓰는데(README §2.2), 그것이
중간에 멈추면 별칭을 **일부러 남긴다**. 그 잔해가 슬롯 10·11 이다.

**따라서 감독 작업은 「슬롯 10·11 을 GUI 에서 지운다」**이지 파일을 다시 배포하는 것이
아니다. 파일은 이미 1.6.2 다.

⚠️ **다만 그 사본 관측은 pid 78611 시절 값이다.** 지금은 38706 이고 쇼파일도
기본 쇼파일로 바뀌었다. 이 세션이 방금 `DataPool/Plugins` 를 다시 읽었고 —
**childCount 5, 슬롯 1 `CopilotResponder` · 2 `CopilotPatchRobinEsprite` ·
5 `CopilotPatchMacAuraXB`. 사본 얽힘이 없다.**

### 갈래 확정 (t96 레인 실측, 같은 순간의 두 관측)

    DataPool/Plugins  childCount 5 · truncated false · Responder 이름 슬롯 **1개뿐**
    ping              live version **1.6.1** · state PASS

**사본이 없는데 옛 버전을 답한다** → 원인은 별칭 잔해가 아니라 **순수 풀 캐싱**이다.
리드와 레인의 독립 판독이 childCount 5 로 일치했다. **처방은 재임포트다.**

### 슬롯 1 의 Lua 를 읽을 채널은 **없다** (셋이 함께 답한다)

    introspect DataPool/Plugins/1   class UserPlugin · 25/25 · truncated **false**
                                    = 절단이 아니라 **전수**다. LUA·SOURCE·CODE 류 필드 0개
    props (대조군 ZZZFAKE9 선행 → 거절 확인)
        NAME    "CopilotResponder"
        VERSION **"0.0.0.0"**   ← 🔴 미끼
        PATH    ""

🔴 **`VERSION` 을 응답기 버전으로 읽지 마라.** MA3 의 **플러그인 메타데이터** 필드이고
Lua 안의 `CONFIG.VERSION`(1.6.1)과 **다른 층**이다. 이름이 같아 계기를 잘못 고르기 쉽다.
**구동 중인 코드의 버전을 답하는 채널은 여전히 `ping` 하나뿐이다.**

⚠️ `PATH` 가 빈 문자열인 것을 「경로가 없다」로 읽으면 안 된다 — t95 선례(내용 있는
오브젝트도 이 채널에서 0·빈값을 답한다). **필드가 비었다는 것과 원본이 없다는 것은
다른 진술이다.**

**결론: 감독 GUI 재임포트 말고는 확정할 길이 없다.**

## 5. 그래서 순서가 정해진다

    감독 GUI ①  픽스처 타입 8종 추가        -> 패치 85행이 풀린다
    감독 GUI ②  응답기 재임포트 (1.6.2)     -> 절단이 풀려 프리셋이 들어간다
    그다음      patch -> group -> preset    (임포트 경로 전부 있음)
    병렬 가능   fx·cue 어댑터 설계          (콘솔 무관 — 코드 작업)

`cue-ex.csv` 가 `COL.01`·`POS.03`·`FX.02` 를 참조하므로 **프리셋이 먼저 있어야
큐가 그것을 가리킬 수 있다.** 순서 의존이 문서에 박혀 있다.

## 6. 매핑표는 레인 판이 정본이다

리드와 레인이 **서로 모른 채 같은 조사**를 했고 **같은 결론**(`fx.csv`·`cue-ex.csv`
둘이 빈칸)에 도달했다 — 독립 재현이라 신뢰도가 올라간다.

**정본: `.moai/reports/t126/doc-tool-map.md`** (PR #179, main `5d31690`).
7폴더 31파일 전수 + `preset-pos` 부재가 결함이 아니라는 판정(REQ-LXSEQ3-002)까지 있다.
리드 판(PR #178)은 중복이라 닫았다.

## 7. 안 잰 것

- **픽스처 타입 추가 후 패치가 실제로 되는지** — 타입이 없어 preview 까지만
- 응답기 재임포트 후 페이징이 이 쇼파일에서도 되는지
- 그룹 임포트 preview (패치가 선행이라 아직 의미 없음)
- **fx·cue 어댑터의 설계** — 입구가 없다는 것까지만 쟀고 어떻게 만들지는 미착수

---

## 8. 재측정 회차 — 2026-08-30 리드 세션 (t98), 콘솔 쓰기 0

원문 §2·§3 을 반증한 회차다. 쏜 것 전부:

    responder_roundtrip --skip-exec --port 8000 --listen-port 9005
        ping   PASS   live version **1.6.1**  plugin=CopilotResponder
        state  PASS   DataPool/Plugins childCount 5 · truncated false

    lxseq_e2e --action preview  (--approve 없음 → 콘솔 쓰기 0)
        probe.live              Patch/FixtureTypes  child_count **8** · truncated false
        probe.fabricated_control Patch/FixtureTypesZZZNotAThing/9999  (날조 대조군 선행)
        summary                 런 1개 · 계획 1대 · 건너뛴 행 85건

### 두 막는 것의 현재 상태 — 둘 다 **아직 안 끝났다**

| 막는 것 | 판정 기준 | 실측값 | 상태 |
|---|---|---|---|
| ① 픽스처 타입 | `Patch/FixtureTypes` child_count | **8** (변화 없음) | 미완 — 54행이 여기 걸린다 |
| ② 응답기 재임포트 | `ping` 이 답하는 live version | **1.6.1** (1.6.2 아님) | 미완 |

**둘 다 「했는지 감독에게 묻는다」가 아니라 이 두 줄로 잰다.** 명령 결과(`executed_ok`)나
디스크 파일 버전은 판정 기준이 아니다 — §4 가 이미 그 함정을 적었다.

### 콘솔 점유 확인 (쏘기 전)

    lsof -nP -iUDP | grep -E ":8000|:9005"
        app_gma3 38706 만 바인드 · 레인 프로세스 0

⚠️ 이건 **그 순간의 값**이다. 프로브는 소켓을 잠깐만 열므로 「지금 없다」가 「곧 없다」를
뜻하지 않는다. 그래서 쏜 뒤 t105 레인에 통보했다.

### 안 잰 것 (이 회차)

- **54행의 타입 8종이 정확히 무엇인지 CSV 쪽 전수** — skipped 상세의 타입 필드를 안 폈다
- `mode_unresolved` 24행이 CSV 의 어느 채널폭을 요구하는지 — t128 이 답한다
- `address_occupied` 7행의 점유자 FID 가 CSV FID 와 같은지 — t129 가 답한다
- 응답기 재임포트 후 페이징이 이 쇼파일에서 되는지 (여전히 미측정)
