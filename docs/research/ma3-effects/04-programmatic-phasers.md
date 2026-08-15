# 04. 프로그래매틱 페이저 제어 — 명령줄 문법, Lua API, 이 저장소의 통합 경로

리서치 태스크 D. grandMA3 페이저(phaser)를 명령줄만으로 만드는 방법과 Lua 플러그인 API 표면을
조사하고, 이 저장소(`AI-Lighting_Console`)가 이미 갖춘 Lua/OSC 브리지 위에서 AI 코파일럿이
어떻게 페이저를 생성할 수 있는지 정리한다. **핵심 발견**: 이 저장소는 페이저 생성을 "연구 대상"이
아니라 이미 **측정하고 구현·검증까지 마친 기능**(`server/fx/`)으로 갖고 있다. 아래 1~2절은
외부 문서(MA Lighting 공식 매뉴얼·포럼)에서 확인한 문법이고, 3절은 리포지토리 안에서 실제로
동작하는 코드를 파일 경로와 함께 정리한 것이다.

---

## 1. 명령줄 페이저 쿠크북 (검증된 문법)

### 1.1 이 저장소가 이미 실측·검증한 문법 (1차 출처)

`server/rulebook/assets/v2.4.2/31_choreography_patterns.md`는 "Programming looks, cues &
effects" 섹션 전체가 **onPC 2.4.2에서 라이브로 검증됨**("Every pattern below was validated
live on onPC 2.4.2")이라고 명시한다. 페이저 관련 검증 문법은 다음과 같다(원문 그대로 인용).

**프로그래밍 목적지 전환 (모든 명령 앞에 1회)**

```
ChangeDestination Root
```

패치 직후 콘솔이 Patch 에디터에 머물러 있으면 `Fixture 11 Thru 19` 같은 선택 명령이
`"Illegal object"`를 반환한다. `Root`가 프로그래밍 컨텍스트다. (반대로 패치 플러그인은
`ChangeDestination`을 절대 호출하면 안 된다 — 대칭적 규칙.)

**픽스처 선택**

```
Fixture 11 Thru 19        # 범위, bare 키워드
Fixture 11 Thru           # open range
Fixture 11 + 12 + 13      # 리스트
Fixture 11 Thru 19 - 15   # 뺄셈
Group 11                  # 그룹 recall이 멤버를 선택
```

`Select Fixture ...` / `SelFix ...` 접두는 2.4.2에서 `"Illegal object"`를 반환했다 — bare
`Fixture ...` / `Group ...` 형만 쓸 것.

**값 지정**

```
Attribute 'Dimmer' At 80                       # percent, 또는 At Full / At 0
Attribute 'ColorRGB_R' At 100                  # 0-100, G/B 동일
Attribute 'Pan' At 20                          # percent
Attribute 'Pan' At Absolute Decimal8 145       # 정확한 DMX 조준값 (0-255)
Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 25   # ';'로 한 줄에 체인
```

`ClearAll`을 매 신규 Look 앞과 매 `Store` 뒤에 반드시 넣을 것 — 남은 프로그래머 값이 다음
캡처로 트랙되어 다음 큐를 조용히 오염시킨다.

**Look → Cue 저장**

```
ChangeDestination Root
ClearAll
Group 11
Attribute 'Dimmer' At 80 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 25
Store Sequence 11 Cue 1 'Warm Wash' CueFade 2
ClearAll
```

- 시퀀스는 첫 Store에서 자동 생성됨. 큐 추가: `Store Sequence 11 Cue 2 'Blue Wash' CueFade 2 /Merge`
- 큐 번호는 소수점 삽입 가능 (`1.5`, `1.55`)
- Store 플래그: `/Merge`(활성 속성만 추가), `/Overwrite`(파괴적 — safety gate가 사람 승인으로
  라우팅), `/Remove`(속성 제거), `/CueOnly`(다음 큐로의 트래킹 차단)

**페이저 (running effect) — 스텝 생성 → phase 스프레드 → speed 순**

```
ClearAll
Group 11
Attribute 'Pan' At Relative 30          # 베이스 조준값 위에 상대값을 얹음
Attribute 'Pan' At Phase 0 Thru 360     # phase를 선택 전체에 스프레드 => 웨이브
Attribute 'Pan' At Speed 60             # 속도 (Speed 창 단위: BPM/Hz/sec)
Store Sequence 12 Cue 1 'Pan Sweep'
ClearAll
```

- 멀티스텝 색상/디머: 값 지정 → `Step 2` → 값 지정 → `Step 3` ...
- 사인 디머 커브: 2스텝, 각 스텝에 `At Accel -100` + `At Decel -100`
- 서클/발리후: Pan·Tilt 페이저를 같은 크기로 90° 위상차 —
  `Attribute 'Pan' At Phase 0` + `Attribute 'Tilt' At Phase 90` (0°/180°=대각선)
- 역방향: `Attribute 'Pan' At Phase 0 Thru -360`

**MAtricks — 선택 전체에 걸친 형태 부여**

```
Set Selection MAtricks 'PhaseFromX' 0
Set Selection MAtricks 'PhaseToX' 360   # X축 전체에 웨이브 1개; 자동 재계산
Set Selection MAtricks 'X' 2            # 매 2번째 픽스처에만 적용
Set Selection MAtricks 'XWings' 2       # 중앙 대칭 미러
Set Selection MAtricks 'XShuffle' 1234  # 시드 랜덤 순서 (같은 시드=같은 룩)
Reset Selection MAtricks                # 서브 선택 해제
```

재사용 가능한 설정 저장: `Store MAtricks 1` → `Label MAtricks 1 'Wave'` → 재호출 `Call MAtricks 1`.

**플레이백**

```
Assign Sequence 11 At Executor 191      # 시퀀스를 실행기 페이더/버튼에 바인딩
Go+ Executor 191                        # 다음 큐 (Go- 이전, Goto Cue 2 Sequence 11)
```

> 출처: `server/rulebook/assets/v2.4.2/31_choreography_patterns.md` (온라인 열람 불가, 로컬
> 저장소 자산 — 이 리포지토리의 AI 코파일럿이 실제로 시스템 프롬프트에 주입하는 문서다).

### 1.2 MA Lighting 공식 문서·포럼 확인 사항 (2차 출처, 교차검증)

외부 검색으로 위 문법과 정합성이 있는 근거를 확인했다. 페이저의 정확한 명세는 공식 Quick
Start Guide(GUI 중심)와 포럼 스레드에 흩어져 있어 **명령줄 전용 종합 레퍼런스는 존재하지
않는다** — 그래서 §1.1의 저장소 자체 검증 문서가 이 리포지토리에서는 더 신뢰도 높은 1차
출처다. 확인된 사항:

- **SpeedMaster 키워드**: 레이어 키워드로, 페이저가 각 속성에서 어떤 스피드 마스터에 속도를
  맞출지 정의한다. 문법: `Attribute "Pan" At SpeedMaster 1` (Attribute + At SpeedMaster N).
  스피드 마스터는 BPM/Hz/Seconds로 설정 가능. — [SpeedMaster Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_speedmaster.html)
- **스텝 편집**: `Group x At Preset x.y Step z` 형태로 특정 스텝에 프리셋 값을 배정할 수
  있으나, 폭(width)·트랜지션은 프로그래머로 끌어오지 않고는 직접 편집이 어렵다는 것이 포럼의
  중론. `Store preset 23.1 Thru 10 Step 2` 같은 시도는 스텝 1을 삭제하는 부작용이 보고됨 —
  따라서 스텝은 반드시 프로그래머 안에서(스텝을 만들면서) 채우는 것이 안전하고, 저장소가 §1.1
  방식(스텝을 프로그래머에서 순서대로 쌓은 뒤 통째로 Store)을 채택한 이유와 일치한다. —
  [Phaser related syntax](https://forum.malighting.com/forum/thread/68274-phaser-related-syntax/),
  [Set Cmd of a Cue](https://forum.malighting.com/forum/thread/7748-set-cmd-of-a-cue/)
- **MAtricks 명령줄**: `Set Selection MAtricks 'SpeedFromX' 10` 같은 `Set Selection MAtricks
  '<Property>' <Value>` 형태가 공식 매뉴얼에 등장 — §1.1의 `Set Selection MAtricks 'PhaseFromX' 0`
  등과 동일 계열. Grid 축 이동에는 `Grid 1/3`, 사각형 지정에는 `Grid 1/1 Thru 5/5` 같은 별도
  `Grid` 키워드가 있다(이 저장소 코드는 아직 Grid 셀렉션을 쓰지 않는다 — §3.4 참고). —
  [MAtricks and Shuffle](https://help.malighting.com/grandMA3/2.0/HTML/matricks.html),
  [Selection Grid Tool Bar](https://help.malighting.com/grandMA3/2.0/HTML/selection-grid-tool-bar.html)
- **버전 차이 주의**: 2026 시점 포럼 스레드(v1.7 기준, 2020년경)는 "페이저 폼/미러 타임을
  명령줄로 직접 바꾸는 옵션이 제한적"이라고 보고한다. §1.1의 검증은 v2.4.2 기준이므로 더
  최신이고 이 프로젝트의 타깃 버전(README.md: "Target console: grandMA3 onPC 2.4.2")과
  일치한다. — [GrandMA3 version 1.7 Change Phaser via cmd line](https://forum.malighting.com/forum/thread/7904-grandma3-version-1-7-change-phaser-via-cmd-line/)

### 1.3 명령줄로 페이저를 만들 때의 핵심 함정 (외부+내부 공통)

1. **스텝 최소 2개** — `Phase`/`Speed`/`Relative`는 "이미 존재하는" 페이저를 수정할 뿐, 스텝이
   1개뿐이면 페이저 자체가 생성되지 않는다(모든 라인이 `ok:true`를 반환하지만 무대는 정지 상태).
2. **`Attribute '<attr>' At Step <k>` 형은 무효** — 콘솔이 `ok:true`로 받아주지만 아무 효과가
   없다. 스텝은 반드시 독립된 `Step <k>` 라인 뒤에 값 라인이 와야 한다.
3. **저장된 페이저 큐는 기계적으로 읽을 수 없다** — `Cue -> Part(childCount 0)`로 빈 큐와
   구분되지 않고, `Phase`/`Speed` 속성도 read-back 시 "property not readable"로 나온다(§3.2).
   즉 페이저가 실제로 만들어졌는지는 **눈으로 확인하거나 사람이 관측하는 수밖에 없다.**

---

## 2. Lua 플러그인 API 표면 (페이저/프로그래머 조작 관련)

grandMA3 Lua 플러그인 API의 명령 실행 계열 함수(공식 API 레퍼런스 미러 기준):

| 함수 | 시그니처 | 동작 |
|---|---|---|
| `Cmd()` | `Cmd(string command[, light_userdata undo], ...): string result` | Lua 태스크 안에서 **동기** 실행 — 결과 문자열 반환, 실행 중 Lua 태스크를 블록 |
| `CmdIndirect()` | `CmdIndirect(string command[, undo[, target]]): nothing` | Main 태스크에서 **비동기** 실행 — Lua를 블록하지 않음 |
| `CmdIndirectWait()` | `CmdIndirectWait(string command[, undo[, target]]): nothing` | Main 태스크에서 **동기** 실행 — 뒤따르는 명령이 실행 완료를 기다림 |
| `CmdObj()` | `CmdObj(): light_userdata handle` | 커맨드라인 객체 핸들 반환 |
| `Selection()` / `SelectionFirst()` / `SelectionNext()` / `SelectionCount()` | — | 현재 선택(프로그래머 선택) 순회 |
| `Programmer()` / `ProgrammerPart()` | — | 프로그래머 핸들/파트 접근 |
| `SetVar()` / `GetVar()` | — | 플러그인 로컬 변수 |

이 표는 [grandma3.bambinito.net LUA Functions 레퍼런스](https://grandma3.bambinito.net/reference/v21/api/)
(비공식 미러, v2.1 기준)에서 확인한 시그니처다. `SetAttribute()`라는 이름의 전용 함수는 이
레퍼런스에 별도로 등장하지 않았다 — 속성 지정은 API 함수 호출이 아니라 **`Cmd()`로 명령줄
문자열(`Attribute 'Dimmer' At 80` 등)을 그대로 실행**하는 방식이 표준 경로로 보인다(§1의
모든 명령줄 문법이 곧 `Cmd()`의 인자가 된다). 공식 1차 문서는
[MA Lighting help — Plugins](https://help.malighting.com/grandMA3/2.3/HTML/plugins.html) 및
[MacTirney/GrandMA3-API-Documentation (GitHub)](https://github.com/MacTirney/GrandMA3-API-Documentation)에
더 폭넓게 정리되어 있으나 이번 조사에서는 표 형태로 직접 인용 가능한 페이지에 한해 인용했다 —
`SetAttribute` 계열 함수의 정확한 시그니처가 필요하면 이 두 출처를 추가로 확인할 것을 권장한다.

**중요 실측 사실 (이 저장소 §3에서 재확인)**: `Cmd()`는 **명령이 콘솔에서 거부돼도 Lua
예외를 던지지 않는다** — `pcall(Cmd, command)`가 성공(true)을 반환해도 명령 자체가 콘솔에서
실패했을 수 있다는 뜻이다(`console/lua/copilot_responder.lua:690-691`, `M.build_exec_result`).
이 저장소의 응답기는 이 문제 때문에 `Cmd()` 결과 분류에 `@MX:NOTE` 경고를 달아뒀다
(`copilot_responder.lua:674`, "Cmd() result classification is an assumption pending live
verification"). AI 코파일럿이 Lua로 페이저를 만들 때 반드시 감안해야 할 API 특성이다.

Sources:
- [SpeedMaster Keyword](https://help.malighting.com/grandMA3/2.0/HTML/keyword_speedmaster.html)
- [Phaser related syntax — MA Lighting Forum](https://forum.malighting.com/forum/thread/68274-phaser-related-syntax/)
- [Phaser basics — MA Lighting Forum](https://forum.malighting.com/forum/thread/68294-phaser-basics/)
- [GrandMA3 version 1.7 Change Phaser via cmd line](https://forum.malighting.com/forum/thread/7904-grandma3-version-1-7-change-phaser-via-cmd-line/)
- [Set Cmd of a Cue — MA Lighting Forum](https://forum.malighting.com/forum/thread/7748-set-cmd-of-a-cue/)
- [Phasers — grandMA3 Quick Start Guide 2.2](https://help.malighting.com/grandMA3/2.2/HTML/qsg_phasers.html)
- [MAtricks and Shuffle](https://help.malighting.com/grandMA3/2.0/HTML/matricks.html)
- [Selection Grid Tool Bar](https://help.malighting.com/grandMA3/2.0/HTML/selection-grid-tool-bar.html)
- [Create Grid Selection via cmd — MA Lighting Forum](https://forum.malighting.com/forum/thread/69262-create-grid-selection-via-cmd/)
- [Plugins — MA Lighting Help](https://help.malighting.com/grandMA3/2.3/HTML/plugins.html)
- [MacTirney/GrandMA3-API-Documentation (GitHub)](https://github.com/MacTirney/GrandMA3-API-Documentation)
- [grandma3.bambinito.net LUA Functions reference](https://grandma3.bambinito.net/reference/v21/api/)

---

## 3. 이 저장소의 통합 경로 — AI 코파일럿이 페이저를 어떻게 생성하는가

**결론 먼저**: 이 저장소는 "AI가 페이저를 만들게 하려면 무엇이 필요한가"를 아직 계획 중인
단계가 아니라, **이미 측정 → 스키마 설계 → 명령 빌더 → 안전 게이트 → MCP형 도구(`instantiate_fx`)
까지 구현하고 M0~M6 검증까지 마친 상태**다(`server/fx/` 패키지, SPEC-FXLIB-001 계열).
아래는 그 파이프라인을 실제 파일 경로로 추적한 것이다.

### 3.1 브리지 계층 — 서버가 콘솔에 어떻게 명령을 보내는가

- **OSC 왕복 프로토콜**: `console/lua/PROTOCOL.md` — 서버(`server/bridge/protocol.py`가 파이썬
  트윈)와 콘솔 상주 Lua 응답기(`console/lua/copilot_responder.lua`) 사이의 계약. 요청은
  `/copilot/cmd`로 `Plugin "CopilotResponder" "<verb> <request-id> [rest]"` 형태의 MA3 명령줄
  하나로 실려 간다. `exec` verb가 임의의 MA3 명령줄을 실행하는 통로다
  (`PROTOCOL.md` §2 "exec | exec <id> <ma3-command> | /copilot/feedback, kind=result").
- **콘솔측 실행**: `console/lua/copilot_responder.lua:690-691`의 `M.build_exec_result`가
  `pcall(Cmd, command)`로 요청받은 명령줄을 그대로 실행한다 — §2에서 정리한 `Cmd()` API가
  실제로 이렇게 쓰이고 있다.
- **OSC 설정 파일**: `console/osc/copilot_osc_row1_receive.xml` (수신), `copilot_osc_row2_send.xml`
  (송신) — onPC의 OSC 입출력 슬롯 매핑.

### 3.2 명령 생성 계층 — 서버가 어떤 명령줄 문자열을 만드는가

`server/fx/` 패키지가 §1.1의 검증된 페이저 문법을 **재사용 가능한 명령 빌더**로 캡슐화했다.

- **스키마** (`server/fx/schema.py`): `Fx` 데이터클래스가 패턴 종류(`sweep`/`wave`/`circle`/
  `diagonal`/`pulse`/`chase`), 스텝 시퀀스(`FxStep`/`StepValue`), 그리고 phase/speed/MAtricks
  같은 "이미 존재하는 페이저를 수정하는" 축을 분리해서 갖는다. `MIN_STEPS = 2`가 스키마
  레벨에서 강제된다(schema.py:66, `@MX:ANCHOR`) — §1.3 함정 1을 코드로 봉쇄한 것.
- **효과 라이브러리** (`server/fx/library/{dimmer,color,movement}.yaml`): 사전 정의된 페이저
  패턴들. `movement.yaml`에는 sweep/wave/circle/diagonal 4종이 Pan/Tilt 축으로 정의돼 있고,
  BPM 시드는 `server/rulebook/assets/v2.4.2/31_choreography_patterns.md`의 무드 표(웜/발라드
  10-20 BPM, 에너제틱/클럽 90-180 BPM)에서 가져온다.
- **명령 빌더** (`server/fx/instantiate.py`): `build_fx_bundle()`이 `Fx` 객체 하나를 실제 MA3
  명령줄 리스트로 변환한다. 번들 형태(instantiate.py:15-30 docstring)는 §1.1의 검증 문법과
  정확히 일치한다:
  ```
  ChangeDestination Root
  ClearAll
  Group <n>
  <step 1 값 라인들>          # Step 1 라인은 생략 (현재 스텝)
  Step 2
  <step 2 값 라인들>
  <phase 라인들>
  <speed 라인>
  [Set Selection MAtricks '<axis>' <v>]
  Store Sequence <n> Cue 1 '<label>'
  [Reset Selection MAtricks]
  ClearAll
  [Assign Sequence <n> At Executor <m>]
  ```
  - `_step_lines()` (instantiate.py:326-342): §1.3 함정 2(`At Step <k>` 금지형)를 정확히
    피해서 독립 `Step <k>` 라인을 생성한다.
  - `_phase_lines()` (instantiate.py:345-408): 패턴별 phase 분배 규칙(circle=90° 오프셋,
    단일 속성+phase_to=선택 전체 스프레드, 다속성=균등 분배)을 구현 — §1.1의 "circle/ballyhoo"
    문법과 "phase 0 thru 360" 웨이브 문법을 코드화한 것.
  - `_guard_collision()` (instantiate.py:432-456): 같은 번들 안에서 동일 명령 줄이 두 번
    나오면 저장이 조용히 실패하는 것(run_commands의 중복제거 때문)을 사전에 거부.
- **시퀀스 번호 측정** (`select_sequence_number()`, instantiate.py:218-254): 빈 시퀀스 번호를
  **콘솔에서 재조회한 값**으로만 정하고 절대 추측하지 않는다 — truncated listing이면 거부.

### 3.3 도구(툴) 계층 — LLM이 실제로 호출하는 인터페이스

`server/orchestrator/tools.py`가 LLM 툴 콜을 MA3 명령 실행으로 연결하는 단일 지점이다.

- `find_fx` (tools.py:3674, 등록: tools.py:6600/7492): 자연어 무드/설명으로 `server/fx/library/`
  에서 적합한 패턴을 검색 — 매칭 로직은 `server/fx/matching.py`.
- `instantiate_fx` (tools.py:3712-3870, 등록: 근처): **모델이 페이저를 만드는 유일한 진입점**
  (`@MX:ANCHOR` 주석, tools.py:3700 "the only model-reachable entry to the fx instantiation
  chain"). 흐름:
  1. `fx_id`(문자열)·`group`(리그에서 실측된 그룹 번호)·선택적 `sequence`/`executor`/`label`을
     인자로 받음.
  2. 리그를 **재조회**해서 `group`이 실제로 존재하는지, 시퀀스 풀이 잘렸는지 확인(추측 금지 —
     §3.2와 동일 원칙).
  3. `bind_fx()`가 §3.2의 `build_fx_bundle()`을 호출해 명령 리스트를 만듦.
  4. 그 명령 리스트를 **그대로 기존 `run_commands` 클로저에 재진입**시켜서 실행
     (tools.py:3845-3848) — `instantiate_fx`는 별도의 실행 경로를 갖지 않고, 안전 게이트
     (`gate.screen()`), 라이브 락, 중복 제거, 감사 로그를 모두 `run_commands`에서 상속받는다
     (README.md의 "SINGLE chokepoint" 원칙과 일치).
  5. 실행 결과에서 `report.succeeded`를 판정 — §1.3 함정 3(페이저가 저장됐는지 기계적으로
     읽을 수 없음) 때문에, "모든 라인이 `ok:true`"가 곧 "페이저가 만들어졌다"를 보장하지
     않는다는 사실을 코드 주석이 명시한다(tools.py:3859-3863, "A gate refusal carries
     per-command DECISIONS, not execution outcomes... Only a COMPLETE verdict is a success").
- `run_commands` (tools.py:1347 정의, 등록: tools.py 상단 리스트 line 207): 임의의 MA3 명령줄
  배치를 안전 게이트에 통과시켜 실행하는 범용 도구. `instantiate_fx`가 없던 시절에는 §1.1의
  페이저 문법을 LLM이 직접 명령줄 문자열로 조립해서 `run_commands`에 넘기는 것도 가능한
  경로였다 — 실제로 `31_choreography_patterns.md`의 페이저 섹션이 바로 그 "직접 조립" 경로를
  위한 프롬프트 자산이다. `instantiate_fx`는 그 위에 스키마 검증·중복 방지·시퀀스 번호 측정을
  얹은 더 안전한 상위 계층이다.

### 3.4 아직 다루지 않는 부분 (관측된 갭)

- **MAtricks Grid 셀렉션** (`Grid 1/3`, `Grid 1/1 Thru 5/5`)은 §1.2에서 확인했지만
  `server/fx/instantiate.py`는 `Group <n>` bare 선택만 만든다 — Grid 기반 서브 선택은 이
  파이프라인에 아직 없다.
  MAtricks 5축(`phase_from_x`/`phase_to_x`/`x`/`x_wings`/`x_shuffle`)만 지원(`schema.py:106-112`,
  `instantiate.py:99-105`).
- **`At Relative <n>`을 스텝 값으로 쓰는 것**은 명시적으로 미검증(`ASSUMPTION-40`)이라 v1은
  이를 아예 방출하지 않는다(`instantiate.py:307-314`, `RELATIVE_NOT_EMITTED`).
- **가속/감속 커브**(`At Accel`/`At Decel`)는 M0에서 `ok:true`+무효과로 관측되어 필드는
  정의돼 있지만 v1에서는 방출을 거부한다(`instantiate.py:315-323`, `GATED_AXIS_NOT_EMITTED`).
- **SpeedMaster 키워드**(§1.2, `Attribute 'Pan' At SpeedMaster 1`)는 이 저장소 어디에도
  구현되어 있지 않다 — `speed` 축은 `Attribute '<attr>' At Speed <bpm>`(고정 BPM 값)만
  방출하고, 외부 스피드 마스터에 종속시키는 경로는 없다. 여러 페이저를 한 번에 트랜지션하고
  싶다면 다음 확장 후보가 된다.

---

## 요약

| 질문 | 답 |
|---|---|
| 명령줄만으로 페이저를 만들 수 있는가? | 예 — `ChangeDestination Root` → `ClearAll` → `Group N` → 스텝별 값 → `Step 2` → 값 → `Phase`/`Speed` → `Store Sequence` (§1.1) |
| 이 문법이 검증됐는가? | 예 — 이 저장소 자체가 onPC 2.4.2에서 라이브 검증한 문서를 갖고 있다(`31_choreography_patterns.md`) |
| Lua API로 같은 걸 할 수 있는가? | 예 — `Cmd()`/`CmdIndirect()`/`CmdIndirectWait()`로 동일한 명령줄 문자열을 실행. 단 `Cmd()`는 콘솔측 실패를 Lua 예외로 던지지 않는다(§2) |
| 이 저장소는 이미 구현했는가? | 예 — `server/fx/schema.py` + `instantiate.py`(빌더) + `server/orchestrator/tools.py`의 `find_fx`/`instantiate_fx`(LLM 도구) + `run_commands`(단일 실행 경로, 안전 게이트) |
| 남은 갭은? | Grid 기반 서브 선택, `At Relative` 스텝 값, Accel/Decel 커브, SpeedMaster 키워드 (§3.4) |
