# t431 — 색 C2 사전 조사: grandMA3 젤 색견본(Book)을 프로그램으로 읽을 수 있나

- 카드: t431 (클래스 B), 레인 lane-1 · 브랜치 `WT-gel-book-probe` · 기준 origin/main `518a3813`
- 배경: `docs/proposals/2026-09-23-color-representation-expansion.md` §4 C2, `.moai/reports/t430/verdict.md`
- 판정: **PASS — 통로가 있다. 이미 배포된 응답기(1.6.5)의 읽기 동사만으로 젤 1,137장의 번호·이름·RGB 를 전부 읽을 수 있다.** 코드 수정 0, 콘솔 쓰기 0.
- 🔴 **C2 설계에 바로 걸리는 사실 두 가지**
  1. **슬롯 번호 ≠ 젤 번호.** `Gel "Lee".201` 은 Lee 201번이 아니라 **201번째 칸**을 가리킨다. 실측으로 201번째 칸은 Lee **604** "Full C_T Eight Five" 였다. 감독이 「L201」이라고 말하면 앱이 `KEY` 로 찾아 슬롯 번호로 바꿔야 한다.
  2. **「Rosco」라는 책은 없다.** 11권 중 Rosco 이름의 책이 없다. Rosco 번호처럼 보이는 키(`R01`, `R3410`)는 `Supergel`·`Cinegel` 책에 있다. 「R26」을 어느 책에서 찾을지는 C2 설계에서 정해야 한다(아래 §5).

## 1. 결론 표

| 알아낼 것 | 답 | 근거 |
|---|---|---|
| 콘솔에 젤 표가 있나 | 있다. `ShowData/GelPools` 아래 11권, 젤 1,137장 | 실측 run1·run6 |
| 젤 하나에 무엇이 들어 있나 | `KEY`(제조사 번호), `NAME`, `R`·`G`·`B`(0..1 실수), `COLOR`(RGBA 문자열) 등 25개 속성 | 실측 run2(introspect)·run3 |
| 프로그램으로 읽는 통로 | 응답기의 `state`(목록, `offset` 페이징) + `props`(한 번에 여러 속성) | 실측 run3·run4·run7 |
| 우리 서버에서 쓸 통로 | `server/safety/console.py` 의 `query_state(path, offset=)` · `query_properties(path, names)` — `server/design/rig_capability_read.py` 가 이미 같은 두 읽기로 리그를 판독한다 | 코드 판독(§4) |
| 젤을 무대에 적용하는 명령 | `At Gel "Lee"."Mauve"` / `At Gel 8.44` (공식 문서). **이번에는 쏘지 않았다** — 쓰기다 | 출처 3 |

## 2. 공식 문서 (WebSearch → WebFetch 로 직접 열어 확인)

1. [grandMA3 2.0 — Using the Color Picker](https://help.malighting.com/grandMA3/2.0/HTML/operate_color_picker.html)
   — "The swatch book is a library of gel colors from different manufacturers." Book 모드는 "using the Gel keyword" 로도 쓸 수 있다. 목록 보기 열은 Name·Key·Color.
2. [grandMA3 2.2 — Gels Pool](https://help.malighting.com/grandMA3/2.2/HTML/operate_gel_pool.html)
   — 젤 풀은 제조사·시리즈별로 나뉘고, 각 젤은 "Gel name, Key catalog number, Appearance" 를 가진다. "Manufacturer gel pools are locked by default" — 제조사 풀은 편집 불가, Custom 풀만 편집 가능.
3. [grandMA3 2.2 — Gel Keyword](https://help.malighting.com/grandMA3/2.2/HTML/keyword_gel.html)
   — 문법 `Gel ["Swatch_Name"."Gel_Name"]` · `Gel [Swatch_Number].[Gel_Number]`. 예: `At Gel "Lee"."Mauve"`, `At Gel 8.44`. **이 문서는 젤 값 읽기·`ShowData`·Lua 접근을 다루지 않는다.**
4. [MA Lighting Forum — Fixture At Gel "LEE".201 (BUG?)](https://forum.malighting.com/forum/thread/8946-fixture-at-gel-lee-201-bug/)
   — `Fixture X at Gel "LEE".201` 이 LEE 201 "Full CT Blue" 가 아닌 "FULL C_T Eight Five 604" 를 불렀다는 보고. 답변자는 `ShowData().GelPools` 를 Lua 로 읽어 `KEY` 순서로 재배열한 Custom 풀을 만드는 우회를 제시했다. **포럼 글이고 공식 문서가 아니다.** 우리 실측(§3 run4)이 같은 결과를 냈다.

**문서만으로 확인하지 못한 것**: 공식 매뉴얼에 젤 풀의 객체 경로(`ShowData/GelPools`)나 Lua 로 값을 읽는 방법은 나오지 않는다. 경로와 속성 이름은 **실측으로만** 확인했다(§3). 문서 판본은 2.0/2.2이고 콘솔은 onPC **2.4.2** 다(`ps`: `/Applications/grandMA3.app/Contents/MacOS/gma3_2.4.2/...`).

## 3. 실기 프로브 — 명령줄과 응답 원문

- 도구: `.moai/reports/t431/probe_t431.py` (이 카드에서 만든 증거 스크립트. `ping`·`state`·`introspect`·`props`·`prop` 만 보낸다. `exec`·`deploy` 경로는 없다)
- 실행: `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.venv/bin/python .moai/reports/t431/probe_t431.py <단계…>` (워크트리에 `.venv` 가 없어서 주 체크아웃의 venv 를 썼다)
- 포트: 송신 127.0.0.1:8000, 수신 9005 (`lsof -nP -iUDP` → `app_gma3 … UDP *:8000`, `UDP *:9005`)
- 원문 전체: `run1_controls_and_root.txt` ~ `run7_paging.txt` (같은 폴더)

### ① 응답기 버전 — 머지된 코드와 로드된 플러그인 대조

```
>>> ping
    wire: Plugin "CopilotResponder" "ping 72d52b2d"
<<< {"id": "72d52b2d", "kind": "pong", "plugin": "CopilotResponder", "proto": 1, "v": 1, "version": "1.6.5"}
```
main `console/lua/copilot_responder.lua:111` → `VERSION = "1.6.5"`. **일치.**

### ② 날조 대조군 → ③ 양성 대조 → 실제 경로 (run1)

```
>>> state:ShowData/GelPools/NoSuchBookT431
<<< {"error": "path segment not found: 'NoSuchBookT431' (in ShowData/GelPools/NoSuchBookT431)", ..., "ok": false, ...}

>>> state:DataPool                      (양성 대조 — 기존 코드가 늘 읽는 경로)
<<< {"children": [{"class": "Worlds", "i": 1, ...}, ... {"class": "Shapes", "i": 16, ...}], "node": {"childCount": 16, "class": "Pool", "enumeration": "ok", "name": "Default"}, "ok": true, ...}

>>> state:ShowData
<<< ... {"class": "GelPools", "i": 6, "name": "GelPools"} ... "node": {"childCount": 26, ...}, "ok": true, "truncated": true

>>> state:ShowData/GelPools
<<< {"children": [{"class": "GelPool", "i": 1, "name": "MA"}, {"class": "GelPool", "i": 2, "name": "Apollo"}, {"class": "GelPool", "i": 3, "name": "CalCol"}, {"class": "GelPool", "i": 4, "name": "Cinegel"}, {"class": "GelPool", "i": 5, "name": "Supergel"}, {"class": "GelPool", "i": 6, "name": "GamColor"}, {"class": "GelPool", "i": 7, "name": "Lee"}, {"class": "GelPool", "i": 8, "name": "PolyCol"}, {"class": "GelPool", "i": 9, "name": "Storaro"}, {"class": "GelPool", "i": 10, "name": "Zircon"}, {"class": "GelPool", "i": 11, "name": "Custom"}], "node": {"childCount": 11, "class": "GelPools", "enumeration": "ok", "name": "GelPools"}, "ok": true, "truncated": false, "v": 1}
```

거절은 `ok:false` + 사유 문자열로 온다. 양성 대조가 읽혔으므로 채널은 살아 있다. 실제 경로의 `ok:true` 는 침묵과 구분된다.

### 젤 하나의 모양 (run2, run3)

```
>>> introspect:ShowData/GelPools/Lee/1
<<< {"class": "Gel", "fields": [... {"n": "NO", "t": "UInt32"}, {"n": "NAME", "t": "String"}, ... {"n": "KEY", "t": "String"}, {"n": "COLOR", "t": "Custom"}, {"n": "R", "t": "Float"}, {"n": "G", "t": "Float"}, {"n": "B", "t": "Float"}], "ok": true, "total": 25, "truncated": false, ...}

>>> prop:ShowData/GelPools/Lee/1|NoSuchPropT431      (속성 날조 대조군)
<<< {"error": "property not readable: NoSuchPropT431", ..., "ok": false, ...}
>>> prop:ShowData/GelPools/Lee/1|NAME   <<< ... "value": "Rose Pink"
>>> prop:ShowData/GelPools/Lee/1|KEY    <<< ... "value": "2"
>>> prop:ShowData/GelPools/Lee/1|R      <<< ... "value": "1.0"
>>> prop:ShowData/GelPools/Lee/1|G      <<< ... "value": "0.47058799862862"
>>> prop:ShowData/GelPools/Lee/1|B      <<< ... "value": "0.86274498701096"
>>> prop:ShowData/GelPools/Lee/1|COLOR  <<< ... "value": "1.000000,0.470588,0.862745,1.000000"
>>> prop:ShowData/GelPools/Lee/1|NO     <<< ... "value": "1"
```

### 🔴 슬롯 번호 ≠ 젤 번호 (run4)

```
>>> props:ShowData/GelPools/Lee/201|NO,KEY,NAME,R,G,B
<<< {..., "reads": [{"n": "NO", "v": "201"}, {"n": "KEY", "v": "604"}, {"n": "NAME", "v": "Full C_T Eight Five"}, {"n": "R", "v": "1.0"}, {"n": "G", "v": "0.76078397035599"}, {"n": "B", "v": "0.58431398868561"}], "ok": true, ...}

>>> props:ShowData/GelPools/Lee/294|NO,KEY,NAME,R,G,B
<<< {..., "reads": [{"n": "NO", "v": "294"}, {"n": "KEY", "v": "821"}, {"n": "NAME", "v": "Zircon UV Blue Blocker"}, ...], "ok": true, ...}

>>> props:ShowData/GelPools/Lee/295|NO,KEY,NAME        (끝 다음 칸 — 대조)
<<< {"error": "path segment not found: '295' (in ShowData/GelPools/Lee/295)", ..., "ok": false, ...}
```

Lee 의 201번째 칸은 **Lee 604** 다. 포럼 보고(출처 4)와 같은 결과다. **젤 번호로 찾으려면 `KEY` 로 매칭해야 한다.** 슬롯 번호로 부르면 조용히 다른 색이 선다.

### 책별 젤 수 (run6 — `state` 의 `childCount`)

| 책 | 젤 수 | 첫 젤의 KEY · NAME |
|---|---|---|
| MA | 13 | (MA 기본색: White, Red, Orange …) |
| Apollo | 153 | `AP1050` · Soft Diffusion |
| CalCol | 33 | — |
| Cinegel | 241 | `R3410` · Roscosun 1/8 CTO |
| Supergel | 134 | `R01` · Light Bastard Amber |
| GamColor | 167 | — |
| Lee | 294 | `2` · Rose Pink |
| PolyCol | 80 | — |
| Storaro | 10 | — |
| Zircon | 12 | — |
| Custom | 0 | (비어 있음) |
| **합계** | **1,137** | |

🔴 **`COUNT` 속성은 젤 수가 아니다.** 11권 모두 `COUNT` = `1000` 이었다(run5). Lee 는 294장인데도 1000이다. 풀 용량으로 보인다. 젤 수는 `state` 의 `node.childCount` 로 세야 한다.

### 페이징 (run7)

```
>>> state:ShowData/GelPools/Lee@19
    wire: Plugin "CopilotResponder" "state e3b8a12e ShowData/GelPools/Lee offset=19"
<<< {"children": [{"class": "Gel", "i": 20, "name": "Light Pink"}, ...], "offset": 19 ...}
>>> state:ShowData/GelPools/Lee@285
<<< {"children": [{"class": "Gel", "i": 286, ...}, ..., {"class": "Gel", "i": 294, "name": "Zircon UV Blue Blocker"}], "node": {"childCount": 294, ...}, "offset": 285, "ok": true, "truncated": false, "v": 1}
```

## 4. 우리 코드의 기존 통로 (코드 판독 — 실측 아님)

- `server/safety/console.py:708` `query_state(path, *, offset=0)` · `:735` `query_property` · `:794` `query_properties(path, names)` — 이 카드의 프로브가 쓴 `state`·`prop`·`props` 와 같은 요청을 만든다(`build_state_query`·`build_prop_query`·`build_props_query`).
- `server/design/rig_capability_read.py:29` — 「읽기 전용. `query_state` · `query_property` · `query_properties` 뿐이다」. 기구 능력 판독이 이미 이 세 읽기만으로 돈다. **젤 판독기도 같은 포트로 만들 수 있다.**
- 서버·콘솔 코드에 `GelPool` 을 참조하는 곳은 **0건**이다(`grep -rln 'GelPool' server console | grep -v tests | wc -l` → `0`).
- 응답기에 새 동사는 필요 없다. 배포본 1.6.5 의 `state`(1.6.0+ 페이징)·`props`(1.6.1+)만 썼다.

## 5. C2 로 넘길 설계 재료

- **전체 판독 비용(추정, 안 쟀음)**: 목록 `state` 요청은 페이지당 최대 약 19장이다(Lee 첫 페이지 19장, 페이로드 예산에 따라 달라진다) → 1,137장이면 약 60회. 젤당 `props(KEY,NAME,R,G,B)` 1회면 1,137회다. 이번에 전체 판독은 **하지 않았다**. 쇼 파일마다 바뀌지 않는 공장 데이터라면 한 번 읽어 앱 안에 캐시하는 쪽이 자연스럽다.
- **값 축 변환**: 젤 `R/G/B` 는 0..1 실수, 앱 팔레트는 0..100 백분율이다(`server/design/color_names.py`). ×100 이 필요하다. 🔴 단위가 다른 양에 같은 상수를 빌리지 말 것.
- **젤 RGB 는 젤의 색이지 기구의 출력이 아니다.** 같은 젤 RGB 를 LED 기구에 넣었을 때 무대에 같은 색이 서는지는 C1/C3(색역) 문제다. 이 카드는 재지 않았다.
- **「L201」「R26」 해석 규칙은 정해지지 않았다.** Lee 는 KEY 가 숫자만(`2`, `604`, `821`), Rosco 계열은 `R` 접두(`R01`, `R3410`)다. `R26` 이 `Supergel` 의 `KEY=R26` 인지 `Cinegel` 인지(두 책 모두 `R` 접두를 쓴다) 확인하지 않았다. KEY 가 책 사이에서 겹치는지 전수로 세지 않았다.
- **적용 경로 두 갈래**: (가) 앱이 젤 RGB 를 읽어 기존 `ColorRGB_*` 줄로 낸다 — 쓰기 경로가 오늘과 같다. (나) `At Gel "<책>"."<이름>"` 으로 콘솔에 맡긴다 — 이름 형식은 공식 문서 문법이다. 번호 형식 `At Gel 7.201` 은 슬롯이라 위험하다. (나)의 이름 형식 동작은 **쏘지 않았다**.

## 6. 안 잰 것

- 젤 1,137장 전체 판독 (책별 수와 양 끝 칸만 읽었다)
- `KEY` 가 책 안·책 사이에서 유일한지
- `Supergel`·`Cinegel` 이 Rosco 제품군이라는 것 — 콘솔 데이터(`R` 접두 키, "Roscosun" 이름)로 추정했을 뿐 문서로 확인하지 않았다
- `At Gel …` 적용 명령 — 쓰기라서 쏘지 않았다
- 전체 판독에 걸리는 시간, 콘솔 부하
- 쇼 파일이나 콘솔 버전을 바꾸면 젤 풀 내용이 바뀌는지
- `COUNT=1000` 이 무엇인지(용량으로 추정)

## 7. 콘솔 접촉 기록

- 보낸 요청: `ping` 1 · `state` 21 · `introspect` 2 · `prop` 10 · `props` 17 — 전부 읽기 동사다. `exec`·`deploy` 0회. (셈: `cat run*.txt | grep -o '^>>> [a-z]*' | sort | uniq -c` → introspect 2 · prop 10 · props 17 · state 21. `ping` 은 파일로 남기지 않고 화면으로만 봤다 — 원문은 §3 ①)
- 콘솔 쓰기·Store·Assign·Delete 0회. 코드 수정 0 (추가한 파일은 이 폴더의 증거물뿐이다).
