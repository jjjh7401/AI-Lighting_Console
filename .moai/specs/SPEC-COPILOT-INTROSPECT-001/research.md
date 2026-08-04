# SPEC-COPILOT-INTROSPECT-001 — 조사 기록 (research)

status: draft (v0.1.0, 2026-08-03) · Tier L

**조사 범위**: base `origin/main` = `3176900` 트리 직접 판독 + 코디네이터 라이브 실측 인수. 본 세션에서 라이브 콘솔 접근은 없었으므로 **모든 콘솔 사실은 인수된 실측이거나 저장소 기록**이며, 본 세션이 새로 측정한 것은 없다.

**인용 규율**: 줄번호는 이 세션 기준이며 마일스톤 착수 직전 재실측한다. **심볼 앵커가 정본**이다. 아래 4개 파일은 워킹 트리와 base가 **바이트 동일**함을 `git diff --quiet 3176900 -- <path>`로 확인했다: `console/lua/copilot_responder.lua`, `console/lua/PROTOCOL.md`, `server/bridge/protocol.py`, `server/orchestrator/ports.py`.

---

## §1. 인수된 라이브 실측 (코디네이터, 2026-08-02, onPC 2.4.2 + 응답기 v1.5.0)

본 SPEC의 설계 전제다. **추측이 아니라 실측이며, 본 세션이 재측정하지 않았다.**

| # | 사실 | 함의 |
|---|---|---|
| 1 | Executor 핸들 `state` 회신 = `{"class":"Executor","name":"Sequence 80","sequenceNo":80,"childCount":0}` | 스냅샷 경로로는 실행 상태를 얻을 수 없다 |
| 2 | `prop`으로 후보 전수 시도 → 전부 `property not readable`. **본 문서가 이름까지 열거하는 후보는 21종**(현재 큐 8종 + 실행 상태 13종) | 이름 추측 전략의 한계 |
| 3 | 예외 ①: `Index` → `ok=true`, 값 `'function: 0x...'` | **판독 성공 ≠ 프로퍼티** — 메서드가 필드 네임스페이스에 섞여 있다 |
| 4 | 예외 ②: `Fader` → `ok=true`, 값 `'Master'`(페이더 **이름**) | **판독 성공 ≠ 유의미** — 이름과 상태는 다르다 |
| 5 | `prop DataPool/Sequences/80 CurrentCue` → 정지 `'Sequence 80.1'`, `Go+` 2회 후 `'Sequence 80.2'` | 재생을 **추적한다**. 채널은 Sequence 핸들에 있었다 |
| 6 | 같은 핸들 `CueNo` → 정지 `'1'`, 진행 후 빈 문자열 | 판독 가능한 값이 신뢰 불가일 수 있다 |
| 7 | 실행 여부·진행률·페이드 잔여시간의 소재는 **미확인** | 본 SPEC이 답을 만드는 것이 아니라 **답할 수단**을 만든다 |

> **카운트 약칭 정리(2026-08-03, plan-audit review-2 D5 소인).** 인수 기록의 *"22종"*은 코디네이터의 **판독 횟수 약칭**이며, 이름까지 받아적힌 후보는 **21종(8+13)**이다. 차이 1건은 인계 시점에 이름이 기록되지 않았다 — 없는 이름을 복원하지 않고 열거된 것만 센다. `Index`·`Fader`(#3·#4)는 이 21종 **밖의 추가 판독 2건**이다. 다른 문서의 "22회/22종"은 이 약칭을 가리키며, 후보 집합의 크기 주장이 아니다.

**#3과 #4가 본 SPEC의 형상을 직접 규정했다.** 판독 성공이 세 가지 서로 다른 것을 뜻할 수 있다 — 진짜 프로퍼티, 메서드 포인터, 무관한 이름. 그래서 `introspect`가 **타입을 나르고**(#3을 값 해석 없이 갈라냄), `props`가 **값을 나른다**(#4/#6을 사람이 판정하게 함).

---

## §2. 오판의 저장소 흔적 — 본 SPEC의 직접적 동기

`server/web/cue_monitor.py`(base `3176900`)에 `@MX:ANCHOR`/`@MX:REASON`으로 기록되어 있다:

> `CURRENT_CUE_PROPERTY_CANDIDATES: tuple[str, ...] = ("CurrentCue",)`
>
> `@MX:REASON`: 이것은 **검증되지 않은 executor-handle 추측**(`("Cue",)`를 `Executor <n>`에 시도)을 대체했다 — 그 추측은 항상 실패했는데, **그런 프로퍼티가 없어서가 아니라 잘못된 오브젝트를 겨냥했기 때문**이다. 이 프로브를 실제로 반박하는 새 라이브 프로브 없이 executor 핸들 탐색으로 되돌리지 말 것.

같은 파일의 모듈 docstring이 더 명시적이다:

> *"이전의 executor-handle 프로브는 **잘못된 오브젝트**를 읽고 있었다 — 그 실패는 진짜였지만, 그것이 뒷받침한 '어떤 채널도 이 정보를 노출하지 않는다'는 결론은 진짜가 아니었다."*

**저장소가 이미 이 오판을 자각하고 주석으로 봉인해 두었다.** 본 SPEC은 그 봉인을 도구로 대체한다 — 주석은 다음 사람이 읽어야 작동하지만, 열거 동사는 읽지 않아도 작동한다.

---

## §3. 응답기 확장 지점 (코드 판독)

### §3.1 디스패치 — 가산 추가 지점

`console/lua/copilot_responder.lua` `M.handle_request`(~876-958행): `parsed.kind == "ping"` / `"state"` / `"prop"` / `"exec"` / `"deploy"` 연쇄 뒤 else로 `unknown request kind`. **정확 문자열 일치**이므로 `prop`/`props` 혼선은 구조적으로 불가능하다(design.md §2.4).

각 분기가 하는 일은 동일한 3단이다: rest 파싱 → 페이로드 빌더 호출 → `M.send_reply(주소, payload)`. 읽기 계열(`state`/`prop`)은 `CONFIG.state_address`, 실행 계열(`ping`/`exec`/`deploy`)은 `CONFIG.feedback_address`로 나간다. 신규 두 동사는 읽기 계열이다(REQ-INTROSPECT-010).

### §3.2 단일 판독의 2단 사다리

`M.safe_property`(~204-217행):

```lua
local ok, value = pcall(function() return handle:Get(property_name) end)
if ok and value ~= nil then return tostring(value) end
ok, value = pcall(function() return handle[property_name] end)
if ok and value ~= nil then return tostring(value) end
return nil, "property not readable: " .. property_name
```

**§1 #3의 메커니즘이 여기 있다**: `Get("Index")`가 nil을 돌려주고 `handle["Index"]`가 메서드를 돌려주면 `tostring()`이 `'function: 0x...'`가 된다. `props`는 이 함수를 **그대로 재사용**해야 한다 — 두 번째 판독기를 만들면 두 곳이 갈라진다(이 저장소의 반복 교훈).

다만 `props`는 타입을 나르므로 `tostring()` 이전의 **원본 Lua 타입**이 필요하다. M2가 `safe_property`를 감싸되 타입을 함께 돌려주는 얇은 래퍼를 두거나, 기존 함수를 가산 확장한다 — 어느 쪽이든 **기존 `prop` 경로의 반환 형상은 무변경**이어야 한다(REQ-INTROSPECT-012).

### §3.3 정합 집합 규율 — REQ-INTROSPECT-004의 직접 선례

`SLOT_PROBES`(~269-275행) + `M.probe_slots`(~314-335행). 주석이 규율을 직접 진술한다:

> *"Accepted only as a coherent SET: one value per child, each a positive integer, strictly increasing in listing order. A silent, 0-based, or unordered accessor fails that gate and is discarded WHOLE — a half-trusted numbering is exactly how a plausible wrong number gets out."*

그리고 `@MX:ANCHOR`(~242-252행)가 그 규율이 왜 존재하는지를 사고 기록으로 남겼다: 목록 위치를 주소로 내보낸 결과 1/5/7 풀에서 `Group 2 + 3`이 발화됐고, **콘솔은 `ChangeDestination Root`와 `ClearAll`이 이미 실행된 뒤에 오브젝트를 거절했다.**

**본 SPEC의 열거원 채택 게이트는 이 규율의 이식이다.** 반쯤 믿는 열거는 반쯤 믿는 numbering과 정확히 같은 종류의 결함이다.

### §3.4 예산 축소 루프 — 절단 신호의 선례

`M.build_snapshot` 말미(~634-639행):

```lua
while #M.encode_payload(payload) > CONFIG.max_payload and #items > 0 do
    table.remove(items)
    payload.truncated = true
end
```

**항목을 뒤에서 제거하고 신호를 세운다.** 실패 분기(~569-576행)도 M6c-4에서 같은 가드를 받았다 — 그 전까지 실패 회신은 경로를 **무제한으로** 에코해 예산을 넘길 수 있었고, `safe_truncate`(~545-557행)가 UTF-8 연속 바이트를 쪼개지 않는 축약을 담당한다.

`props`의 개별 값 축약은 `safe_truncate`를 **재사용**해야 한다.

### §3.5 예산 상수와 그 위험

`CONFIG`(~27-42행):

| 상수 | 값 | 주석이 기록한 근거 |
|---|---|---|
| `max_children` | 24 | UDP 페이로드 예산 |
| `max_payload` | 1900 | 2026-07-24 라이브 실측 — `cmd_keyword` 전송이 MA3 커맨드 라인 ~2048바이트 초과분을 **조용히 드롭**한다. `Cmd()`가 성공을 보고하므로 회신은 그냥 사라진다. 스윕: 2000 전달, 2100 드롭 |

재현자는 27개 매크로 풀 스냅샷이었고, 이전의 `max_payload = 4000` 아래에서 **모든 회신이 사라졌다.**

`server/tests/test_lua_responder_payload_budget.py`가 `MA3_COMMAND_LINE_LIMIT = 2048`로 산술을 **소스 수준에서** 고정한다(lupa 불필요). `props` 요청 예산도 같은 파일에서 같은 방식으로 고정하는 것이 자연스럽다.

### §3.6 무페이징 계약 (본 SPEC이 상속하되 확장하지 않는다)

`PROTOCOL.md` §4.2:

> *"**페이징은 없다.** 요청에 offset이 없고 회신에 cursor가 없으므로, `truncated:true` 목록은 이어받을 수 없다 — 같은 경로를 재조회하면 같은 첫 N개가 영원히 온다. 캡보다 큰 풀을 열거하려면 각 슬롯을 자기 경로로 조회하고(`<pool>/<n>`), 풀 조회의 `node.childCount`가 소진될 때까지 계속한다."*

**`introspect`에는 이 우회로의 등가물이 없다** — 이름을 모르면 `props`로 물을 수 없다. design.md §8이 이를 알려진 천장으로 기록한다.

---

## §4. 와이어 가산 추가의 선례

`PROTOCOL.md` 상단 Revision note 4건 전부가 동일한 형식을 따른다:

| 버전 | 변경 | 프로토콜 버전 |
|---|---|---|
| 1.5.0 | ADDITIVE `prop` 동사(§2) + `prop` 회신 kind(§4.6) + Cue 자식의 `cueNo` | **1 유지** |
| 1.3.0 | `send_reply`가 모든 전송 변형을 시도 | **1 유지** (와이어 무변경) |
| 1.2.0 | 스냅샷 `i`의 **의미** 변경(위치 → 실제 슬롯), 미확립 시 생략 | **1 유지** — "양방향 파싱 호환" 논거 명시 |
| 1.1.0 | ADDITIVE `deploy` 동사(§2) + `deploy` 회신 kind(§4.5) + ASSUMPTION-6 | **1 유지** |

**1.5.0이 본 SPEC의 정확한 형판이다**: 동사 추가 + kind 추가 + §6 ASSUMPTION 추가 + 버전 1 유지. 1.6.0은 그 형판을 두 동사로 반복한다.

`state` 회신의 `node.sequenceNo`(EXECBODY-001 M2)는 또 다른 형판 — **기존 kind에 필드를 가산**하며 *"두 리더 모두 keyed get을 쓴다"*를 호환 논거로 삼았다.

---

## §5. Python 측 소비 경로 (코드 판독)

### §5.1 요청 빌더 규율

`server/bridge/protocol.py`:

- `_validate_request_id` — `^[A-Za-z0-9._-]+$`
- `_validate_rest` — 비어 있지 않을 것, **큰따옴표 금지**(MA3 인용 플러그인 인자를 종료시킴), 단일 라인
- `build_prop_query` — 위 둘 + `property_name`에 공백 금지

**`props`의 이름 목록은 여기서 추가 검증을 받는다**: 콤마 구분, 개수 상한, 인코딩 후 길이 상한(REQ-INTROSPECT-016). 공백 포함 이름은 첫-토큰 파싱을 깨뜨리므로 **송신 전에 거부**한다 — 콘솔측 파싱 실패에 의존하지 않는다.

### §5.2 포트 → 게이트 → 링크

| 계층 | 심볼 | 본 SPEC이 하는 일 |
|---|---|---|
| 포트 | `server/orchestrator/ports.py` `PropertyQueryPort` | 같은 형식의 좁은 프로토콜 추가. docstring이 분리 근거를 이미 진술: *"소비자가 필요한 능력만 정확히 선언하게 한다"* |
| 게이트 | `server/safety/gate.py` `_query_property` + `_GateStatePort` | 같은 형식의 메서드 추가. **감사 1:1**(타임아웃도 이미 보낸 송신이므로 기록) |
| 링크 | `server/safety/console.py` `ConsoleLink.query_property` | 같은 id 상관·타임아웃 예산·예외 타입. docstring: *"응답기가 `prop`을 상태 주소로 답하고 `deliver`가 이미 그것을 받으므로 **신규 회신 채널이 생기지 않는다**"* — 본 SPEC도 동일 |

감사 주체 문자열은 현재 `f"{path} {property_name}"`이다. `props`의 등가물은 `경로 + 요청 이름들`이며 **값은 담지 않는다** — 이것이 민감정보 경계의 실제 집행 지점이다(REQ-INTROSPECT-018).

### §5.3 판독 실패를 포착하되 전파하지 않는 패턴

`server/prechk/query.py` `read_properties`의 docstring이 본 SPEC의 `props` 의미론을 이미 진술하고 있다:

> *"판독 실패는 **포착되지, 던져지지 않는다.** 하나의 판독 불가 프로퍼티가 판독 가능한 것들을 버리게 해서는 안 된다 — 첫 실패에서 중단하는 스윕은 하나의 나쁜 프로퍼티를 픽스처 하나의 소실로 바꾼다."*

그리고 `PropertyRead` docstring:

> *"`ok`는 '콘솔이 값으로 답했다'이지 '그 값이 쓸 만하다'가 아니다."*

**REQ-INTROSPECT-007은 이 문장을 목록 층위로 올린 것**이며, 새로운 규율이 아니라 기존 규율의 승계다.

`read_properties`는 또한 **중복을 collapse하고 순서를 보존**하며, **빈 이름 목록을 `ValueError`로 거부**한다(빈 결과는 모든 "판독 실패 0건" 단언을 공짜로 참으로 만들기 때문). `props`도 같아야 한다.

---

## §6. 툴 표면 (닫힌 집합)

`server/orchestrator/tools.py` `build_toolset` — base `3176900` 기준 `ToolDefinition(` 등재 **18건**:

`run_commands` · `query_state` · `deploy_plugin` · `get_rig_context` · `find_looks` · `instantiate_look` · `prepare_busking` · `prepare_songcue` · `precheck_patch` · `preshow_check` · `find_fx` · `instantiate_fx` · `find_scene` · `compile_scene` · `build_patch_sheet` · `build_cue_sheet` · `build_preset_list` · `plan_executor_layout`

본 SPEC은 **이 목록을 바꾸지 않는다**(REQ-INTROSPECT-024, 결정 D-4). v1 소비자는 개발자 CLI이며, 기존 `server/tools/` 4종(`responder_roundtrip.py` 등)이 그 자리의 선례다.

---

## §7. 열거 API에 대한 문서 조사 결과 — **부재**

`server/rulebook/assets/v2.4.2/` 5개 파일(`00_grammar.md`, `10_object_model.md`, `20_korean_terms.md`, `30_plugin_patterns.md`, `31_choreography_patterns.md`)에 대해:

- `Dump` / `PropertyCount` / `GetPropertyDisplayName` grep → **전건 0**
- `:Get(` / `Children()` / `Ptr(` grep → **전건 0**

**룰북은 핸들 접근자 API를 전혀 문서화하지 않는다.** 이 저장소가 아는 모든 핸들 접근자(`Get`·`GetClass`·`Children`·`Count`·`Ptr`·`Index`·`Object`)는 응답기의 pcall 방어 프로브 사다리와 그 위의 `PROTOCOL.md` §6 ASSUMPTION 목록에만 존재한다 — **"시도해 보고 되면 쓴다"가 이 프로젝트의 확립된 API 지식 획득 방식**이다.

따라서 ASSUMPTION-46(열거 가능성)에 대해 **문서로 답할 수 있는 경로가 없다.** M1 라이브 프로브가 첫 마일스톤인 이유가 이것이며, 이는 이 저장소의 교훈 *"정적 프로브가 답할 수 없는 것은 실사격만 답한다"*의 직접 적용이다.

---

## §8. 프로브 증거 채널의 선례

| 채널 | 선례 | 비용 |
|---|---|---|
| **OSC 직접 회신** | 응답기 자신이 `SendOSCMessage`를 플러그인 컨텍스트에서 호출한다(`M.send_reply`). 서버측은 `server/tools/responder_roundtrip.py`가 왕복 패턴을 확립 | 쇼파일 쓰기 **0** |
| `Store Macro` + 재조회 | PRECHK-001 M0가 라이브로 확립. **`Store Macro <m>.<line>`(라인 개체 생성)이 프로퍼티 설정에 선행해야 한다** — 순서를 어기면 `Illegal object`이며 이는 "문법 없음"이 아니라 "대상 없음"이었다 | 쇼파일 쓰기 발생. **`Delete`가 블랙리스트**라 툴로 지울 수 없어 사용자 GUI 삭제 필요(SCENE-001 M0가 시퀀스 7개를 남긴 선례) |
| `Printf` / `Echo` | **사용 불가** — grandMA3 GUI에서 출력이 보이지 않는다. 응답기의 `M.log`조차 이 때문에 짧은 평문으로 제한 | — |

**PRECHK-001이 남긴 방법론 교훈**이 M1 설계에 직접 적용된다: *"부정 프로브로는 '문법 없음'과 '대상 없음'이 갈리지 않았다 — 갈라낸 것은 **생성 프로브와 재조회**였다."* 열거 프로브도 같다: "열거원이 nil을 돌려줬다"만으로는 **열거 불가**와 **접근 경로 오류**가 갈리지 않으므로, §5.4의 교차 대조군(이미 판독 가능이 확인된 이름)이 그 판별을 담당한다.

---

## §9. 후속 SPEC 권고 (본 SPEC이 생성하지 않는다)

M7 산출물이 나온 뒤 판단할 사항이며, 여기서는 **후보만 기록**한다:

1. **재생 상태 기능 SPEC** — M7이 해당 필드를 발견한 경우에만 성립. 발견 실패도 유효한 입력이며, 그 경우 후속 SPEC은 "이 정보는 콘솔이 노출하지 않는다"를 확정 사실로 상속한다.
2. **`introspect` 오프셋 토큰** — M7에서 절단이 빈번하게 관측된 경우에만. **예측으로 미리 만들지 않는다.**
3. **LLM 툴 등재** — 민감정보 경계를 다시 판정해야 하는 별개 결정(design.md §6.3).
4. **거짓 양성 열거원 대응** — §5.4 게이트가 걸러내지 못하는 축(design.md §8-2). v1은 "열거 후 `props`로 재확인"이라는 운용 규율로 대신한다.
